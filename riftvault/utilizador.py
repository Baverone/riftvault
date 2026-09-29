"""QUEM é o dono dos dados desta sessão — a porta única (2026-09-29).

André, 2026-09-29: *"Amigos meus querem usar o site para organizar a coleccao
deles. Podes fazer com que mais pessoas possam organizar a coleccao deles
tambem usando o site?"*

Esta é a FUNDAÇÃO, não o produto: hoje `atual()` devolve sempre o André, e é
suposto devolver. O que ela vale é ser o ÚNICO sítio onde a pergunta se faz —
quando a autenticação chegar, muda-se aqui e mais lado nenhum. Ver
`docs/multi-utilizador.md`.

O MODELO, EM DUAS LINHAS
    Cada utilizador tem a SUA base de dados (`vault.db`), e toda a linha dela
    leva o `user_id` dele. O catálogo (`catalog.db`) e os preços (`prices.db`)
    são PARTILHADOS por todos — são o jogo e o mercado, não a coleção de
    ninguém. É isso que torna um utilizador novo barato: medido a 2026-09-29,
    a base de um utilizador com três cartas são **242 KB** (o schema e os
    índices), contra os **1,4 MB do catálogo** e os **745 KB dos preços** que
    ninguém volta a pagar.

PORQUE É QUE A SEPARAÇÃO É POR FICHEIRO E NÃO POR `WHERE user_id = ?`
    Duas razões medidas, as duas decisivas:

    1. O `data/vault.db` VAI PARA UM REPOSITÓRIO PÚBLICO, e é commitado
       automaticamente (a tarefa `riftvault-publicar`, de 30 em 30 minutos; 95
       commits até 2026-09-29). Pôr a coleção de um amigo lá dentro publicava-a
       — para sempre, porque o histórico do Git não se apaga. A coleção do
       André é dele e ele escolheu publicá-la; a do Miguel não é nossa para
       publicar. Com um ficheiro por pessoa, o dele continua no Git e os deles
       ficam em `data/users/<slug>/`, que está no `.gitignore`.

    2. São 134 statements de SQL em 19 módulos a tocar nas tabelas de dono
       (contado a 2026-09-29). Uma separação que depende de 134 `WHERE` bem
       lembrados falha em silêncio e falha do lado pior: um `WHERE` esquecido
       numa LEITURA mostra a coleção de um a outro. Com um ficheiro por pessoa
       a separação é FÍSICA — os dados do outro não estão sequer na ligação —
       e não há nada para esquecer.

ENTÃO PARA QUE SERVE A COLUNA `user_id`?
    Não é ela que separa — é o ficheiro. Ela faz três coisas, e nenhuma é
    decorativa:

      * cada linha diz de quem é, por isso uma base aberta como o utilizador
        errado é DETECTÁVEL. É o que o `db.connect` verifica (`guardar`), e é
        a rede que apanha um ficheiro trocado ou restaurado do backup errado;
      * a migração faz-se HOJE, com um utilizador e zero risco, em vez de uma
        noite com vinte pessoas a usar isto;
      * se um dia isto crescer para uma base só (Postgres, ou um `vault.db`
        partilhado), juntar os ficheiros passa a ser um `INSERT ... SELECT`
        sem ambiguidade. Falta aí mudar as PK para `(user_id, ...)` — está
        escrito no `docs/multi-utilizador.md`, não se finge que sai de graça.
"""

from __future__ import annotations

import contextlib
import contextvars
import os
import re
import sqlite3
from datetime import datetime, timezone

# O André. É o utilizador 1 porque foi o primeiro e porque é a coleção dele que
# está no `data/vault.db` de sempre — a migração não move uma linha de sítio.
ANDRE = 1
SLUG_ANDRE = "baverone"
NOME_ANDRE = "André"

# O slug é o subdomínio (`<slug>.rift.baverone.com`) e o nome da pasta. Por
# isso: minúsculas, dígitos e hífen, nunca a começar ou acabar em hífen. É a
# intersecção do que um DNS aceita com o que um nome de pasta aceita nos três
# sistemas — e é o que impede um slug de fugir da pasta (`..`, `/`, `C:`).
# Mínimo DOIS caracteres: um só é confundível com um engano de escrita num
# subdomínio, e a mensagem de erro promete «2 a 32» — o que se promete cumpre-se.
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,30}[a-z0-9]$")

# Nomes que não podem ser de ninguém: ou são caminhos que já existem, ou são
# subdomínios que vamos querer para o serviço.
RESERVADOS = frozenset({
    "www", "api", "admin", "app", "site", "static", "cdn", "img", "images",
    "mail", "ftp", "blog", "docs", "help", "support", "status", "test",
    "dev", "staging", "backups", "users", "user", "riftvault", "root",
    # O André, pelos dois nomes. O `baverone` já estava protegido de facto
    # pelo `UNIQUE` do slug dele; o `andre` não estava, e um amigo podia ficar
    # com `andre.rift.baverone.com` — apanhado pela sessão `riftbound-f3` a
    # 2026-09-29. A garantia fica aqui, que é a camada que manda.
    "andre", "baverone",
    # O que o serviço vai querer para si.
    "rift", "login", "logout", "conta", "contas", "registo", "ensaio", "u",
    "ns1", "ns2",
})


class SlugInvalido(ValueError):
    """O slug não serve como subdomínio nem como nome de pasta."""


class UtilizadorDesconhecido(LookupError):
    """Não há utilizador com esse id ou esse slug."""


class DonoErrado(RuntimeError):
    """A base tem linhas de outro dono — não é a base deste utilizador.

    Isto não acontece por acidente de programação: acontece quando alguém
    copia um ficheiro para a pasta errada, ou restaura um backup por cima de
    outro. Rebenta de propósito, em vez de servir a coleção errada a alguém.
    """


def validar_slug(slug: str) -> str:
    """O slug, normalizado, ou `SlugInvalido` com a razão escrita."""
    s = (slug or "").strip().lower()
    if not SLUG_RE.match(s):
        raise SlugInvalido(
            f"«{slug}» não serve: o slug é o subdomínio e o nome da pasta, "
            f"por isso só minúsculas, dígitos e hífen (2 a 32), sem começar "
            f"nem acabar em hífen.")
    if s in RESERVADOS:
        raise SlugInvalido(f"«{s}» está reservado ({', '.join(sorted(RESERVADOS))}).")
    return s


# ---------------------------------------------------------------------------
# A PORTA ÚNICA
# ---------------------------------------------------------------------------

# O utilizador DESTE FIO DE EXECUÇÃO. É um `ContextVar` e não uma variável
# global de propósito: o `serve` corre `threaded=True`, um pedido por thread, e
# uma global punha dois pedidos simultâneos a ver o dono um do outro — a pior
# avaria que este módulo podia ter. Cada thread (e cada tarefa async) tem o seu
# valor, e o valor de omissão é «ninguém definiu».
_SESSAO: contextvars.ContextVar[int | None] = contextvars.ContextVar(
    "riftvault_utilizador", default=None)


def atual() -> int:
    """O utilizador desta sessão. HOJE É SEMPRE O ANDRÉ, e é suposto.

    Não há autenticação nenhuma e não é esta corrida que a faz — o modo edição
    continua a ser só para a LAN, sem palavra-passe (ver o CLAUDE.md, «Sem
    autenticação»). O que existe é o SÍTIO onde a pergunta passa a ser feita:
    quando a sessão autenticada chegar, é ela que chama o `como()` no princípio
    do pedido, e todo o resto do código já vem por aqui.

    A ordem é: o que o `como()` puser neste fio > `RIFTVAULT_USER` > o André.

    `RIFTVAULT_USER` deixa correr o CLI e as medições como outro utilizador sem
    autenticação nenhuma — é uma variável do ambiente DELE, na máquina dele, do
    mesmo tipo do `RIFTVAULT_DATA` que já existe. **Não serve para o servidor**:
    é global ao processo e um servidor com threads punha todos os pedidos no
    mesmo dono. Quem serve pedidos usa o `como()`, ou passa o `user_id` ao
    `db.connect` de caminho.
    """
    do_fio = _SESSAO.get()
    if do_fio is not None:
        return do_fio
    bruto = os.environ.get("RIFTVAULT_USER")
    if not bruto:
        return ANDRE
    try:
        return int(bruto)
    except ValueError:
        raise UtilizadorDesconhecido(
            f"RIFTVAULT_USER={bruto!r} não é um id. É o número da tabela "
            f"`users` (o André é o {ANDRE}).") from None


@contextlib.contextmanager
def como(user_id: int):
    """Corre este bloco como aquele utilizador, SÓ NESTE FIO.

    É por aqui que a sessão autenticada vai entrar: o servidor abre um destes
    no princípio do pedido e tudo o que estiver lá dentro — incluindo o
    `db.connect()` sem argumentos — fica a falar com a base da pessoa certa.
    Repõe o que estava, mesmo que rebente a meio.
    """
    token = _SESSAO.set(int(user_id))
    try:
        yield int(user_id)
    finally:
        _SESSAO.reset(token)


# ---------------------------------------------------------------------------
# O REGISTO — quem existe. Vive FORA do Git.
# ---------------------------------------------------------------------------

def _agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def registo_db():
    """`data/users/registo.db` — o registo do serviço.

    NÃO é o `vault.db` do André, e a razão é a mesma que pôs cada coleção num
    ficheiro próprio: o `data/vault.db` está commitado num repositório PÚBLICO
    e é empurrado de 30 em 30 minutos. Com o registo lá dentro, registar um
    amigo publicava-lhe o nome e o slug no GitHub para sempre — mesmo que ele
    mantivesse a coleção privada. A pasta `data/users/` está no `.gitignore`.
    """
    from . import config
    return config.DATA_DIR / "users" / "registo.db"


def abrir_registo() -> sqlite3.Connection:
    """O registo, com a tabela criada e o André já lá dentro."""
    from . import config
    caminho = registo_db()
    caminho.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(caminho, timeout=15.0, isolation_level=None)
    con.row_factory = sqlite3.Row
    con.executescript((config.PKG / "users_schema.sql").read_text(encoding="utf-8"))
    semear(con)
    return con


def semear(con: sqlite3.Connection) -> None:
    """O André é o utilizador 1. Corre uma vez, ao abrir o registo.

    É a definição do sistema: há sempre pelo menos um utilizador, e é o dono do
    `data/vault.db` que já existia — por isso a migração não move uma linha de
    sítio. Idempotente: o `INSERT OR IGNORE` não mexe se já lá está, e mudar-lhe
    o nome à mão não se desfaz na abertura seguinte.
    """
    con.execute(
        "INSERT OR IGNORE INTO users (user_id, nome, slug, criado_em) "
        "VALUES (?,?,?,?)", (ANDRE, NOME_ANDRE, SLUG_ANDRE, _agora()))


def criar(nome: str, slug: str) -> dict:
    """Um utilizador novo, no registo. Devolve a linha.

    NÃO cria a base de dados dele — quem a cria é o `db.connect(user_id=...)`,
    na primeira vez que alguém a abre. São duas coisas separadas: o registo diz
    quem existe, o ficheiro é onde os dados dele vivem.
    """
    slug = validar_slug(slug)
    nome = (nome or "").strip() or slug
    con = abrir_registo()
    try:
        if por_slug(slug, obrigatorio=False, con=con):
            raise SlugInvalido(f"já há um utilizador com o slug «{slug}».")
        cur = con.execute(
            "INSERT INTO users (nome, slug, criado_em) VALUES (?,?,?)",
            (nome, slug, _agora()))
        return registo(int(cur.lastrowid), con=con)
    finally:
        con.close()


def registo(user_id: int | None = None,
            con: sqlite3.Connection | None = None) -> dict:
    """A linha do utilizador (por omissão o desta sessão).

    `con` é o registo já aberto, para quem está a fazer várias coisas seguidas;
    sem ele abre-se e fecha-se um. Nunca é o `vault.db` de ninguém.
    """
    uid = atual() if user_id is None else int(user_id)
    proprio = con is None
    con = con or abrir_registo()
    try:
        row = con.execute("SELECT * FROM users WHERE user_id = ?",
                          (uid,)).fetchone()
    finally:
        if proprio:
            con.close()
    if row is None:
        raise UtilizadorDesconhecido(f"não há utilizador com o id {uid}.")
    return dict(row)


def por_slug(slug: str, obrigatorio: bool = True,
             con: sqlite3.Connection | None = None) -> dict | None:
    proprio = con is None
    con = con or abrir_registo()
    try:
        row = con.execute("SELECT * FROM users WHERE slug = ?",
                          ((slug or "").strip().lower(),)).fetchone()
    finally:
        if proprio:
            con.close()
    if row is None and obrigatorio:
        raise UtilizadorDesconhecido(f"não há utilizador com o slug «{slug}».")
    return dict(row) if row else None


def apagar(user_id: int) -> dict:
    """Tira um utilizador do registo e apaga a pasta dele. Devolve o que foi.

    É a PRIMITIVA, não a política: não pergunta nada, não guarda cópia e não
    avisa ninguém. O «apagar a conta a pedido» — a confirmação, o backup antes,
    o que se responde a quem pede — constrói-se por cima disto.

    O ANDRÉ NÃO SE APAGA. A base dele é o `data/vault.db`, que é a coleção
    original e está no Git; apagá-la por um id trocado era a pior coisa que
    esta função podia fazer, e por isso nem é possível pedir.

    Só é barato assim por a separação ser por ficheiro: apagar uma conta é
    apagar uma pasta e uma linha, e não dezasseis `DELETE` que é preciso
    lembrar de escrever todos.
    """
    from . import config  # noqa: F401 — mantém o caminho coerente com `pasta`
    uid = int(user_id)
    if uid == ANDRE:
        raise SlugInvalido(
            "o utilizador 1 é o dono do `data/vault.db` (a coleção original, "
            "no Git) e não se apaga por aqui.")
    reg = registo(uid)
    alvo = pasta(reg["slug"])
    apagados = []
    if alvo.exists():
        for p in sorted(alvo.rglob("*"), reverse=True):
            (p.rmdir() if p.is_dir() else p.unlink())
            apagados.append(p.name)
        alvo.rmdir()
    con = abrir_registo()
    try:
        con.execute("DELETE FROM users WHERE user_id = ?", (uid,))
    finally:
        con.close()
    return {"user_id": uid, "slug": reg["slug"], "pasta": str(alvo),
            "ficheiros": len(apagados)}


def todos(con: sqlite3.Connection | None = None) -> list[dict]:
    proprio = con is None
    con = con or abrir_registo()
    try:
        return [dict(r) for r in con.execute(
            "SELECT * FROM users ORDER BY user_id")]
    finally:
        if proprio:
            con.close()


# ---------------------------------------------------------------------------
# O caminho dos dados de cada um
# ---------------------------------------------------------------------------

def pasta(slug: str):
    """Onde vivem os dados de um utilizador.

    O ANDRÉ FICA ONDE SEMPRE ESTEVE (`data/`): a migração não move um ficheiro,
    e por isso o `data/vault.db` que está no Git continua a ser o mesmo
    caminho, o mesmo backup e o mesmo histórico. Os outros vão para
    `data/users/<slug>/`, que está no `.gitignore` — a coleção deles não é
    nossa para publicar num repositório público.
    """
    from . import config
    if slug == SLUG_ANDRE:
        return config.DATA_DIR
    return config.DATA_DIR / "users" / validar_slug(slug)


def guardar(con: sqlite3.Connection, user_id: int, tabelas) -> None:
    """Carimba as linhas sem dono e RECUSA as de outro dono.

    Pergunta por DOIS sítios, e é preciso serem os dois:

      1. **a tabela `users` de dentro da base** — é a identidade do FICHEIRO, e
         é a resposta fiável. O `db._carimbar_dono` escreve-a em toda a ligação;
      2. **as linhas carimbadas** das tabelas de dono.

    Porque é que o (1) faz falta: **o carimbo é preguiçoso.** Esta função corre
    no `db.connect`, ou seja ANTES das escritas da sessão — uma linha escrita
    durante a sessão fica a `NULL` e só é carimbada na abertura seguinte. Uma
    base criada e nunca mais reaberta tem as linhas TODAS a `NULL`, e nesse
    estado o (2) sozinho não distingue ninguém: um ficheiro fresco de outra
    pessoa passava. Foi apanhado pela sessão `riftbound-2b` a 2026-09-29, com um
    teste que forjava um manifesto e via a recusa não acontecer.

    `NULL` continua a querer dizer «do dono deste ficheiro» — é um ficheiro por
    pessoa — e adopta-se, que é o que a migração faz com as 4 778 linhas do
    André. O que rebenta é OUTRO dono, explícito.

    TEM DE CORRER ANTES DO `_carimbar_dono`: se a linha desta sessão já lá
    estivesse, o (1) via duas e não sabia qual era a do ficheiro.
    """
    intrusos = []

    # 1. De quem é o FICHEIRO, segundo ele próprio.
    try:
        donos = [r["user_id"] for r in con.execute("SELECT user_id FROM users")]
    except sqlite3.OperationalError:
        donos = []              # base a meio da migração: ainda não há `users`
    if donos and user_id not in donos:
        intrusos.append("a base diz-se do utilizador "
                        + ", ".join(str(d) for d in sorted(donos)))

    # 2. E de quem são as linhas que lá estão.
    for t in tabelas:
        row = con.execute(
            f"SELECT user_id, COUNT(*) AS n FROM {t} "  # noqa: S608 — `t` é interno
            f"WHERE user_id IS NOT NULL AND user_id <> ? "
            f"GROUP BY user_id LIMIT 1", (user_id,)).fetchone()
        if row:
            intrusos.append(f"{t}: {row['n']} linha(s) do utilizador {row['user_id']}")

    if intrusos:
        raise DonoErrado(
            f"esta base tem dados de outro dono e foi aberta como o "
            f"utilizador {user_id} — " + "; ".join(intrusos) +
            ". Não se serviu nada: confirma que o ficheiro é o certo "
            "(um backup restaurado por cima do outro faz isto).")

    for t in tabelas:
        con.execute(f"UPDATE {t} SET user_id = ? WHERE user_id IS NULL",  # noqa: S608
                    (user_id,))

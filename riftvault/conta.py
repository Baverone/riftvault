"""EXPORTAR, IMPORTAR e APAGAR uma conta — sem tocar nas outras (2026-09-29).

Da ordem:
  *"Hoje o backup e o `vault.db` inteiro. Com cinco pessoas la dentro,
  restaurar um erro dele desfaz o mes dos outros."*
  *"Se isto nao existir ao dia 1, um dia ele vai fazer SQL a mao em dados
  vivos com um amigo a espera."*

As duas frases dizem a mesma coisa por dois lados: **a unidade do backup tem
de ser a PESSOA, não o ficheiro da casa toda.** Isto escreve-se antes de haver
gente lá dentro porque depois é tarde — a primeira vez que for preciso é
sempre com alguém à espera.

O QUE TORNA ISTO BARATO é a decisão da corrida anterior: **um ficheiro
`vault.db` por pessoa** (ver `riftvault/utilizador.py`). Exportar é empacotar
o ficheiro dela; importar é pôr o ficheiro dela de volta; apagar é apagar a
pasta dela e a linha do registo. Nenhuma das três precisa de tocar num byte
de outra pessoa, e é por isso que a prova sai fácil: `tests/test_conta.py`
fotografa o utilizador B — as linhas todas, o sha256 do ficheiro — e exige
que não mexa enquanto se exporta, restaura e apaga o A.

O QUE VAI NO PACOTE (um `.zip`, que é stdlib e abre em qualquer lado)

    manifesto.json          quem, quando, quantas linhas de cada tabela
    vault.db                a coleção dela, por `VACUUM INTO` (ver abaixo)
    riftvault_config.json   as preferências dela, se tiver ficheiro próprio
    decks/*.txt             as listas dela, se tiver pasta própria

O `VACUUM INTO` e não uma cópia do ficheiro: as bases estão em WAL, e copiar
o ficheiro podia apanhá-la a meio de uma transação — é a mesma razão do
`db.backup`, e é a diferença entre um backup e um backup que não abre.

O QUE **NÃO** VAI NO PACOTE, de propósito:

  * **CREDENCIAIS.** A `user_auth` e as sessões vivem no `data/auth.db`, fora
    do Git e fora daqui (decisão de 2026-09-29, com a sessão da autenticação).
    Um export é uma coisa que se manda por email; um token de identidade não
    é. Quando uma conta é apagada, **quem limpa a `user_auth` é o código da
    autenticação**, no mesmo passo em que chama o `apagar()` daqui — está
    combinado e está escrito no `docs/multi-utilizador.md`.
  * **o catálogo e os preços.** São partilhados, são o jogo e o mercado, e não
    são de ninguém. Um export com 2 MB de catálogo lá dentro era um export que
    ninguém manda.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from . import config, db, guarda, utilizador

#: A versão do formato. Um pacote de uma versão que não conhecemos recusa-se a
#: entrar, em vez de ser lido a metade.
FORMATO = "riftvault/conta/1"

NOME_MANIFESTO = "manifesto.json"
NOME_VAULT = "vault.db"
NOME_CONFIG = "riftvault_config.json"
PASTA_DECKS = "decks"


class PrecisaConfirmar(RuntimeError):
    """Uma operação que escreve por cima de dados exige `confirmar=True`.

    O mesmo padrão do `venda.vender`: quem chama tem de dizer que sabe o que
    está a fazer, e a interface tem onde perguntar.
    """


class PacoteInvalido(ValueError):
    """O `.zip` não é um export desta aplicação, ou está estragado."""


class NaoSeApaga(RuntimeError):
    """O utilizador 1 não se apaga por aqui — ver o `apagar()`."""


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def _config_de(slug: str) -> Path:
    """O ficheiro de preferências de um utilizador.

    O André usa o `riftvault_config.json` da raiz — o de sempre, com as regras
    que são dele (foils, binder, selado, decks, venda). Os outros teriam um
    `data/users/<slug>/riftvault_config.json` próprio. **Hoje esse ficheiro
    não existe para ninguém e a app ainda não o lê**: a separação do config em
    «regra do produto» e «preferência de cada um» é a fatia seguinte, e está
    descrita no `docs/multi-utilizador.md`. O export já o leva porque o dia em
    que ele existir não pode ser o dia em que os backups deixam de o guardar.
    """
    if slug == utilizador.SLUG_ANDRE:
        return config.CONFIG_PATH
    return utilizador.pasta(slug) / NOME_CONFIG


def _decks_de(slug: str) -> Path:
    if slug == utilizador.SLUG_ANDRE:
        return config.DECKS_DIR
    return utilizador.pasta(slug) / PASTA_DECKS


def _slug_de_um_pacote(slug: str) -> str:
    """O slug de um pacote a restaurar, validado como DEVE ser.

    O `utilizador.validar_slug` faz duas coisas: verifica a FORMA (minúsculas,
    dígitos e hífen — é o que impede um slug de fugir da pasta) e recusa os
    RESERVADOS. O segundo é para quem se REGISTA; aqui seria errado, e o caso
    que o mostra é o próprio André: `baverone` está reservado (de propósito,
    para ninguém o roubar) e sem isto não se conseguia restaurar a conta dele.

    Um slug que já EXISTE no registo entra como está — se é um utilizador, já
    passou pela porta certa. Um que não exista tem de passar pelas duas
    metades, porque restaurar um pacote não pode ser a maneira de contornar a
    lista de reservados.
    """
    s = (slug or "").strip().lower()
    if not utilizador.SLUG_RE.match(s):
        raise utilizador.SlugInvalido(
            f"«{slug}» não serve como nome de pasta — o pacote está estragado "
            f"ou foi mexido.")
    if utilizador.por_slug(s, obrigatorio=False):
        return s
    return utilizador.validar_slug(s)


def _so_deste_dono(con: sqlite3.Connection, user_id: int) -> None:
    """RECUSA uma base que não seja daquele dono. Não carimba nada.

    É a metade de leitura do `utilizador.guardar`, e existe à parte porque
    aqui a pergunta faz-se ANTES de o ficheiro ir para a pasta de alguém — e
    carimbar um pacote que estamos a recusar era o contrário do que se quer.
    É isto que impede restaurar o backup do A por cima do B.

    PERGUNTA-SE POR DOIS SÍTIOS, e o segundo não é redundância. **O carimbo
    das linhas é PREGUIÇOSO**: uma linha escrita durante uma sessão fica com
    `user_id` a NULL e só é carimbada na abertura SEGUINTE (é o
    `utilizador.guardar` a correr no `db.connect`). Um ficheiro criado e
    exportado sem nunca mais ser aberto tem as linhas todas a NULL — e NULL
    quer dizer «do dono deste ficheiro», o que não distingue ninguém.
    Descoberto a medir, a 2026-09-29.

    O que distingue sempre é a tabela `users` DE DENTRO da base, que o
    `db._carimbar_dono` escreve em toda a ligação. É ela a identidade do
    ficheiro; as linhas são a confirmação quando já estão carimbadas.
    """
    try:
        donos = [r[0] for r in con.execute("SELECT user_id FROM users")]
    except sqlite3.OperationalError:
        donos = []
    if donos and int(user_id) not in [int(d) for d in donos]:
        raise utilizador.DonoErrado(
            f"este pacote diz ser do utilizador {user_id}, mas a base lá "
            f"dentro identifica-se como sendo do "
            f"{', '.join(str(d) for d in donos)}. Não se escreveu nada: é um "
            f"backup de outra pessoa.")
    intrusos = []
    for t in db.TABELAS_DE_DONO:
        try:
            row = con.execute(
                f"SELECT user_id, COUNT(*) AS n FROM {t} "  # noqa: S608
                f"WHERE user_id IS NOT NULL AND user_id <> ? "
                f"GROUP BY user_id LIMIT 1", (user_id,)).fetchone()
        except sqlite3.OperationalError:
            continue
        if row:
            intrusos.append(f"{t}: {row[1]} linha(s) do utilizador {row[0]}")
    if intrusos:
        raise utilizador.DonoErrado(
            f"este pacote diz ser do utilizador {user_id} mas tem linhas de "
            f"outro — " + "; ".join(intrusos) +
            ". Não se escreveu nada: é um backup de outra pessoa.")


def _linhas(con: sqlite3.Connection) -> dict[str, int]:
    """Quantas linhas tem cada tabela de dono. É o que se diz a quem apaga."""
    fora = {}
    for t in db.TABELAS_DE_DONO:
        try:
            fora[t] = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]  # noqa: S608
        except sqlite3.OperationalError:
            fora[t] = 0
    return fora


# ---------------------------------------------------------------------------
# EXPORTAR
# ---------------------------------------------------------------------------

def exportar(slug: str, destino: Path | str | None = None) -> dict:
    """Um `.zip` com tudo o que é de um utilizador. Não escreve na base dele.

    `destino` pode ser uma pasta (o nome sai daqui) ou o caminho do ficheiro.
    Por omissão vai para `data/backups/`, que é onde já vivem os backups e
    está no `.gitignore` — um export de uma coleção de outra pessoa não vai
    para um repositório público por descuido nosso.
    """
    reg = utilizador.por_slug(slug)
    uid = reg["user_id"]
    origem = db.vault_de(uid)

    alvo = Path(destino) if destino else (config.DATA_DIR / "backups")
    if alvo.is_dir() or not alvo.suffix:
        alvo.mkdir(parents=True, exist_ok=True)
        alvo = alvo / (f"conta-{reg['slug']}-"
                       f"{datetime.now().strftime('%Y%m%d-%H%M%S')}.zip")
    alvo.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        copia = Path(tmp) / NOME_VAULT
        linhas: dict[str, int] = {}
        if origem.exists():
            con = db.abrir_vault(origem, uid, readonly=True)
            try:
                linhas = _linhas(con)
                # O `VACUUM INTO` anexa o destino por dentro, e o guarda
                # recusa `ATTACH` — ver `guarda.a_copiar`.
                with guarda.a_copiar(con):
                    con.execute("VACUUM main INTO ?", (str(copia),))
            finally:
                con.close()

        manifesto = {
            "formato": FORMATO,
            "quando": _agora(),
            "utilizador": {k: reg.get(k) for k in
                           ("user_id", "nome", "slug", "criado_em", "publico")},
            "linhas": linhas,
            "sha256_vault": _sha256(copia) if copia.exists() else None,
        }

        cfg = _config_de(reg["slug"])
        decks_dir = _decks_de(reg["slug"])
        with zipfile.ZipFile(alvo, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr(NOME_MANIFESTO,
                       json.dumps(manifesto, ensure_ascii=False, indent=1))
            if copia.exists():
                z.write(copia, NOME_VAULT)
            if cfg.exists():
                z.write(cfg, NOME_CONFIG)
            if decks_dir.is_dir():
                for txt in sorted(decks_dir.glob("*.txt")):
                    z.write(txt, f"{PASTA_DECKS}/{txt.name}")

    return {"ficheiro": alvo, "utilizador": reg, "linhas": linhas,
            "bytes": alvo.stat().st_size, "manifesto": manifesto}


# ---------------------------------------------------------------------------
# IMPORTAR
# ---------------------------------------------------------------------------

def ler_manifesto(ficheiro: Path | str) -> dict:
    """O manifesto de um pacote, sem lhe mexer. Para quem quer ver antes."""
    try:
        with zipfile.ZipFile(ficheiro) as z:
            m = json.loads(z.read(NOME_MANIFESTO).decode("utf-8"))
    except (OSError, KeyError, ValueError, zipfile.BadZipFile) as e:
        raise PacoteInvalido(f"não se lê o manifesto de {ficheiro}: {e}") from None
    if m.get("formato") != FORMATO:
        raise PacoteInvalido(
            f"o pacote diz ser «{m.get('formato')}» e isto lê «{FORMATO}».")
    return m


def importar(ficheiro: Path | str, confirmar: bool = False) -> dict:
    """Põe um utilizador de volta a partir de um `.zip`. Não toca nos outros.

    **ESCREVE POR CIMA DA BASE DELE**, por isso exige `confirmar=True` e faz
    backup do que lá estava antes — mesmo que o que lá esteja seja pior do que
    o que entra, a decisão de deitar fora é de quem restaura e não nossa.

    O que se verifica ANTES de escrever um byte:
      1. o pacote é desta aplicação e tem manifesto;
      2. o `vault.db` de dentro abre;
      3. **não tem linhas de outro dono** — é a mesma pergunta do
         `utilizador.guardar`, feita antes de o ficheiro ir para a pasta de
         alguém. É isto que impede restaurar o backup do A por cima do B;
      4. o sha256 bate com o manifesto.
    Só depois é que se mexe em disco, e o que se mexe é **uma pasta só**.

    Um utilizador que já não exista no registo é recriado a partir do
    manifesto (com o `user_id` dele, se estiver livre) — restaurar uma conta
    apagada é o caso normal de um restauro, não uma excepção.
    """
    ficheiro = Path(ficheiro)
    m = ler_manifesto(ficheiro)
    u = m["utilizador"]
    slug = _slug_de_um_pacote(u["slug"])
    uid = int(u["user_id"])
    if not confirmar:
        raise PrecisaConfirmar(
            f"importar «{slug}» escreve por cima da coleção dele "
            f"({m.get('linhas', {}).get('copies', 0)} linhas em `copies` no "
            f"pacote, de {m.get('quando')}). Chama com `confirmar=True`.")

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        with zipfile.ZipFile(ficheiro) as z:
            nomes = set(z.namelist())
            if NOME_VAULT not in nomes:
                raise PacoteInvalido("o pacote não traz `vault.db`.")
            z.extract(NOME_VAULT, tmp)
            for extra in (NOME_CONFIG,):
                if extra in nomes:
                    z.extract(extra, tmp)
            decks = [n for n in nomes if n.startswith(PASTA_DECKS + "/")
                     and n.endswith(".txt")]
            for n in decks:
                z.extract(n, tmp)

        entrada = tmp / NOME_VAULT
        if m.get("sha256_vault") and _sha256(entrada) != m["sha256_vault"]:
            raise PacoteInvalido(
                "o `vault.db` do pacote não bate com o sha256 do manifesto — "
                "está estragado ou foi mexido.")
        # De quem são as linhas que vêm lá dentro? Antes de isto ir para a
        # pasta de alguém.
        prova = db.abrir_vault(entrada, uid, readonly=True)
        try:
            _so_deste_dono(prova, uid)
            linhas = _linhas(prova)
        finally:
            prova.close()

        # Só a partir daqui é que se escreve.
        reg = utilizador.por_slug(slug, obrigatorio=False)
        if reg is None:
            # Restaurar uma conta APAGADA é o caso normal de um restauro, não
            # uma excepção. Repõe-se com o `user_id` do manifesto se ele
            # estiver livre — assim as linhas carimbadas lá dentro continuam
            # a bater certo com o registo.
            mestre = utilizador.abrir_registo()
            try:
                mestre.execute(
                    "INSERT INTO users (user_id, nome, slug, criado_em, publico) "
                    "VALUES (?,?,?,?,?)",
                    (uid, u.get("nome") or slug, slug,
                     u.get("criado_em") or _agora(),
                     u.get("publico") or "nada"))
            except sqlite3.IntegrityError:
                # o id já é de outra pessoa: entra com um id novo
                mestre.execute(
                    "INSERT INTO users (nome, slug, criado_em, publico) "
                    "VALUES (?,?,?,?)",
                    (u.get("nome") or slug, slug, u.get("criado_em") or _agora(),
                     u.get("publico") or "nada"))
            finally:
                mestre.close()
            reg = utilizador.por_slug(slug)
        uid = reg["user_id"]

        alvo = db.vault_de(uid)
        alvo.parent.mkdir(parents=True, exist_ok=True)
        anterior = None
        if alvo.exists():
            anterior = (config.DATA_DIR / "backups" /
                        f"antes-de-importar-{slug}-"
                        f"{datetime.now().strftime('%Y%m%d-%H%M%S')}.db")
            anterior.parent.mkdir(parents=True, exist_ok=True)
            con = db.abrir_vault(alvo, uid, readonly=True)
            try:
                with guarda.a_copiar(con):
                    con.execute("VACUUM main INTO ?", (str(anterior),))
            finally:
                con.close()
        # Tira o WAL do que estava lá: sem isto, um `-wal` antigo ao lado de um
        # ficheiro novo é uma base que não abre (ou que abre na versão errada).
        for sufixo in ("-wal", "-shm"):
            velho = alvo.with_name(alvo.name + sufixo)
            if velho.exists():
                velho.unlink()
        shutil.copy2(entrada, alvo)

        cfg_dentro = tmp / NOME_CONFIG
        cfg_alvo = _config_de(slug)
        if cfg_dentro.exists():
            cfg_alvo.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(cfg_dentro, cfg_alvo)
        decks_alvo = _decks_de(slug)
        for n in decks:
            decks_alvo.mkdir(parents=True, exist_ok=True)
            shutil.copy2(tmp / n, decks_alvo / Path(n).name)

    return {"utilizador": reg, "linhas": linhas, "ficheiro": alvo,
            "backup": anterior, "decks": len(decks),
            "config": cfg_alvo if (cfg_alvo.exists()) else None}


# ---------------------------------------------------------------------------
# APAGAR
# ---------------------------------------------------------------------------

def apagar(slug: str, confirmar: bool = False, com_backup: bool = True) -> dict:
    """Apaga um utilizador e tudo o que é dele. Nada mais.

    O QUE SAI: a base dele (`data/users/<slug>/vault.db`), a pasta inteira
    dele, e a linha na tabela `users` do registo.
    O QUE FICA, intacto: o `catalog.db`, o `prices.db`, e todos os outros
    utilizadores — ficheiro a ficheiro, byte a byte (há teste).

    **FAZ UM EXPORT ANTES**, por omissão, e diz onde ficou. Apagar uma conta é
    a operação que mais vezes se faz por engano, e a que menos se desfaz.

    O UTILIZADOR 1 NÃO SE APAGA POR AQUI, e não é timidez: a tabela `users` —
    o registo de quem existe — vive na base dele. Apagá-la não apaga uma
    conta, apaga o serviço. Se alguma vez for para acontecer, o registo tem de
    mudar de casa primeiro (está no `docs/multi-utilizador.md`).

    A `user_auth` e as sessões **não se tocam aqui**: vivem no `data/auth.db`,
    são do código da autenticação, e é ele que as limpa no mesmo passo em que
    chama isto. Combinado a 2026-09-29; está no documento.
    """
    reg = utilizador.por_slug(slug)
    uid = reg["user_id"]
    if uid == utilizador.ANDRE:
        raise NaoSeApaga(
            f"o utilizador {utilizador.ANDRE} («{reg['slug']}») não se apaga: "
            f"a base dele é o `data/vault.db`, a coleção original, que está no "
            f"Git. Apagá-lo por um id trocado era a pior coisa que isto podia "
            f"fazer, e por isso nem é possível pedir.")

    caminho = db.vault_de(uid)
    pasta = utilizador.pasta(reg["slug"])
    linhas: dict[str, int] = {}
    if caminho.exists():
        con = db.abrir_vault(caminho, uid, readonly=True)
        try:
            linhas = _linhas(con)
        finally:
            con.close()

    if not confirmar:
        raise PrecisaConfirmar(
            f"apagar «{reg['slug']}» tira {sum(linhas.values())} linhas em "
            f"{len([t for t, n in linhas.items() if n])} tabelas "
            f"({linhas.get('copies', 0)} em `copies`) e a pasta {pasta}. "
            f"Chama com `confirmar=True`.")

    backup = exportar(slug)["ficheiro"] if com_backup else None
    ficheiros = ([str(p.relative_to(pasta)) for p in sorted(pasta.rglob("*"))
                  if p.is_file()] if pasta.exists() else [])
    # A PRIMITIVA é do `utilizador.apagar` — apaga a pasta e a linha do
    # registo. Aqui é a POLÍTICA: a confirmação, o backup antes e a contagem.
    utilizador.apagar(uid)

    return {"utilizador": reg, "linhas": linhas, "total": sum(linhas.values()),
            "ficheiros": ficheiros, "pasta": pasta, "backup": backup}

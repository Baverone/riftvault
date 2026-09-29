"""O GUARDA: tocar numa tabela de dono sem dono REBENTA (2026-09-29).

André, na ordem desta corrida: *"quero que ESQUECER seja um ERRO, não uma
leitura silenciosa da tabela toda"*.

O QUE MUDOU NA PERGUNTA, E É PRECISO DIZÊ-LO
    A ordem foi escrita a contar com uma base de dados só, partilhada, filtrada
    por `WHERE user_id = ?` — e nesse modelo o erro clássico é um `WHERE`
    esquecido. **Não é esse o modelo que ficou.** A corrida anterior
    (`0-multi-utilizador-1`) mediu duas coisas que o mataram — o `data/vault.db`
    está num repositório PÚBLICO e é empurrado de 30 em 30 minutos, e são 134
    statements de SQL em 19 módulos a tocar nas tabelas de dono — e escolheu
    **um ficheiro `vault.db` por pessoa** (ver `riftvault/utilizador.py`). Com
    isso, um `WHERE` esquecido já não mostra nada de ninguém: os dados do outro
    não estão na ligação.

    Mas o modelo novo tem o SEU esquecimento, e é esse que isto guarda:

      * abrir a base **sem dizer de quem é** — ou pelo caminho fixo do
        ficheiro do André, que é o que o `db.py` guarda e mais ninguém pode
        usar (há teste). Hoje `utilizador.atual()` devolve
        sempre o André, por isso nunca acontece — mas no dia em que houver
        sessões autenticadas, `atual()` vai poder não saber quem é (ninguém
        entrou). Sem guarda, esse dia serve a coleção do André a um visitante
        anónimo, em silêncio. Com guarda, rebenta e diz qual foi a tabela;
      * **anexar a base de outra pessoa** à mesma ligação, que é a única maneira
        de dois donos partilharem um `SELECT`.

    As outras duas metades do isolamento não estão aqui porque não são de
    execução: a `utilizador.guardar` recusa uma base com linhas de outro dono
    (é o que apanha um ficheiro trocado ou um backup restaurado por cima do
    outro), e o `tests/test_isolamento.py` recusa que qualquer módulo abra um
    `sqlite3.connect` ou use o caminho fixo da base dele fora do `db.py` — que é por
    onde se chegaria ao ficheiro errado sem passar por aqui.

COMO
    O `sqlite3` tem um AUTORIZADOR: um callback que o SQLite chama **ao
    preparar** cada statement, uma vez por tabela tocada, e que pode recusar. É
    isso — não é um wrapper à volta do `execute`, que se contorna com um
    `cursor()`. Medido a 2026-09-29: **50 000 consultas em 48 ms armado contra
    49 ms desarmado**, ou seja custo nenhum (o SQLite chama-o na PREPARAÇÃO, e
    o Python guarda os statements preparados em cache).
"""

from __future__ import annotations

import contextlib
import sqlite3

# Os códigos do autorizador. O `sqlite3` expõe-os, mas escrevê-los aqui deixa
# ler o callback sem ir à documentação.
OK = sqlite3.SQLITE_OK
DENY = sqlite3.SQLITE_DENY


class SemDono(RuntimeError):
    """Uma tabela de dono, numa ligação que não sabe de quem é.

    Nunca acontece por uma consulta mal escrita: acontece quando alguém abre a
    base por fora do `db.connect()`, ou quando o dono da sessão é desconhecido.
    Rebenta de propósito — a alternativa é servir a coleção de alguém a quem
    não é dono dela, e isso não pode ser silencioso.
    """


class SoUmaBase(RuntimeError):
    """Tentou anexar outra base a uma ligação já ligada a um utilizador.

    É a única maneira de dois donos aparecerem no mesmo `SELECT`, e por isso é
    recusada. O catálogo e os preços anexam-se ANTES de armar o guarda — são
    partilhados e não são de ninguém.
    """


class Ligacao(sqlite3.Connection):
    """Uma ligação que sabe de quem são os dados que serve.

    `riftvault_user` a `None` quer dizer «não se sabe», e é o estado de
    partida: uma ligação nasce sem dono e só o `db.connect()` lho dá. É por
    isso que o guarda tem algum valor — se o valor por omissão fosse o André,
    esquecer-se dele era invisível.
    """

    riftvault_user: int | None = None
    #: a última tabela de dono recusada, para a mensagem dizer qual foi
    _ultima_tabela: str | None = None
    #: quantos blocos `a_copiar()` estão abertos — ver lá porquê
    _anexar_ok: int = 0

    def _traduzir(self, e: sqlite3.DatabaseError):
        """A recusa do SQLite, com a razão escrita em português."""
        if not _negado(e):
            return e
        if self._ultima_tabela:
            t, self._ultima_tabela = self._ultima_tabela, None
            return SemDono(
                f"a tabela `{t}` é de dono e esta ligação não sabe de quem: "
                f"abre a base pelo `db.connect()`, que é a porta única. "
                f"(Se o que querias era só o catálogo ou os preços, esses são "
                f"partilhados e não passam por aqui.)")
        return SoUmaBase(
            "esta ligação já está ligada a um utilizador e não pode anexar "
            "outra base — é a regra que impede dois donos no mesmo SELECT. "
            "O catálogo e os preços anexam-se antes de o guarda armar.")

    def execute(self, *a, **k):
        try:
            return super().execute(*a, **k)
        except sqlite3.DatabaseError as e:
            raise self._traduzir(e) from None

    def executemany(self, *a, **k):
        try:
            return super().executemany(*a, **k)
        except sqlite3.DatabaseError as e:
            raise self._traduzir(e) from None

    def executescript(self, *a, **k):
        try:
            return super().executescript(*a, **k)
        except sqlite3.DatabaseError as e:
            raise self._traduzir(e) from None


#: As três formas que o SQLite tem de dizer «o autorizador recusou». São
#: mesmo três e dependem do que se estava a fazer — medido a 2026-09-29:
#: `access to copies.qty is prohibited` numa leitura, `not authorized` numa
#: escrita ou num `ATTACH` escrito, `authorization denied` num `VACUUM INTO`
#: (que anexa por dentro).
_RECUSAS = ("not authorized", "prohibited", "authorization denied")


def _negado(e: BaseException) -> bool:
    m = str(e).lower()
    return any(r in m for r in _RECUSAS)


def armar(con: Ligacao, tabelas) -> None:
    """Arma o guarda numa ligação. Chamado pelo `db.connect()`, e só por ele.

    Depois disto a ligação **não pode anexar mais nenhuma base** — por isso o
    catálogo e os preços têm de já estar anexados. É a segunda metade do
    guarda: sem ela, um `ATTACH` do `vault.db` de outra pessoa punha as duas
    coleções ao alcance do mesmo `SELECT`.

    O autorizador não recebe o caminho do ficheiro no `ATTACH` (o SQLite passa
    `None` — verificado a 2026-09-29), por isso não dá para escolher quais
    deixar passar: recusam-se todos, e os que interessam já passaram.
    """
    alvo = frozenset(tabelas)

    def autorizar(accao, arg1, _arg2, base, _origem):
        if accao == sqlite3.SQLITE_ATTACH:
            return OK if con._anexar_ok else DENY
        # `arg1` é o nome da tabela nas acções de tabela e de coluna. Só o
        # `main` interessa: o `catalog` e o `prices` são partilhados.
        if base == "main" and arg1 in alvo and con.riftvault_user is None:
            con._ultima_tabela = arg1
            return DENY
        return OK

    con.set_authorizer(autorizar)


@contextlib.contextmanager
def a_copiar(con: Ligacao):
    """Abre a porta do `ATTACH`, só dentro do bloco. **Uso: o `db.backup`.**

    O `VACUUM <schema> INTO` — que é como esta casa faz todos os backups,
    porque as bases estão em WAL — **anexa o ficheiro de destino por dentro**,
    e por isso é recusado pelo guarda. Medido a 2026-09-29: o autorizador vê um
    `SQLITE_ATTACH` (24) e o `VACUUM` morre com «authorization denied». Sem
    esta porta, armar o guarda partia todas as migrações com backup e o
    `conta.exportar`.

    É um contador e não um booleano para blocos encaixados não se apagarem uns
    aos outros, e fecha mesmo que rebente lá dentro. **O bloco tem de ser
    curto e tem de viver no `db.py`**: lá dentro um `ATTACH` a sério também
    passa, e é esse o preço de o SQLite não dizer ao autorizador qual é o
    ficheiro que está a anexar (passa `None` — verificado).
    """
    # Tolerante de propósito: o `catalog_only()` devolve uma ligação sem
    # guarda nenhum (o catálogo é partilhado e não tem tabelas de dono), e o
    # `db.backup` é o mesmo para as duas.
    if not isinstance(con, Ligacao):
        yield con
        return
    con._anexar_ok += 1
    try:
        yield con
    finally:
        con._anexar_ok -= 1


def desarmar(con: sqlite3.Connection) -> None:
    """Tira o guarda. Existe para o `conta.py`, que precisa de anexar a base
    de um utilizador para a exportar ou importar — e faz isso numa ligação
    própria, nunca numa que esteja a servir alguém."""
    con.set_authorizer(None)

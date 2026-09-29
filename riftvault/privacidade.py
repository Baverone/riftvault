"""O QUE O PÚBLICO VÊ DE CADA UTILIZADOR (2026-09-29).

Da ordem: *"O site publico dele mostra hoje a coleccao inteira e o valor em
euros a quem tiver o link. Os amigos vao presumir que o deles e privado."*

TRÊS VALORES, e o campo é `users.publico`:

    "nada"          não se gera site nenhum para ele. É a OMISSÃO.
    "sem-valores"   gera a coleção, e nenhum euro em lado nenhum.
    "tudo"          como o site dele hoje.

PORQUE É QUE A OMISSÃO É `"nada"`
    Porque publicar a coleção de outra pessoa tem de ser um acto ESCOLHIDO, e
    não uma coisa que se herda de um valor por omissão. Uma página pública
    indexa-se no Google e fica em cache em sítios que não controlamos: na
    prática **não se despublica**. E o valor em euros de uma coleção, ao lado
    de um nome e de um subdomínio, é uma informação com consequências fora do
    ecrã.

    O ANDRÉ FICA EM `"tudo"`, e não é excepção nenhuma: é o que ele já
    escolheu e tem hoje. A migração escreve-lho, e por isso o site dele não
    muda um byte — que é a regra desta semana toda.

COMO É QUE `"sem-valores"` TIRA OS EUROS
    Uma regra só, aplicada ao payload inteiro antes de ser escrito: **uma
    chave cujo NOME fala de dinheiro e cujo VALOR é um número perde o valor**
    (fica `null`), e **uma string com `€` também**. Medido no site real a
    2026-09-29: 272 chaves distintas, das quais 31 falam de dinheiro, ~7 000
    ocorrências, e um único `€` em texto (o recibo da Venda).

    Não é uma lista de chaves escrita à mão, e é de propósito: uma lista
    fica velha na primeira vez que um payload ganha um campo novo, e fica
    velha em silêncio. Sendo uma REGRA, uma chave nova chamada `preco_x` é
    apanhada sozinha.

    São três regras e não uma, e a terceira nasceu de uma fuga a sério: um
    dicionário cujo NOME fala de dinheiro tem dinheiro lá dentro, tenham as
    chaves o nome que tiverem. O caso foi o `progress.value`, que é
    `{"owned": 213751, "full": 128087, "hidden_owned": 0, …}` — o valor da
    coleção em cêntimos, com três nomes que não dizem dinheiro nenhum. A
    regra do nome não lhe tocava.

    Quem o encontrou foi a SEGUNDA REDE, e é por isso que ela existe: no
    teste (`test_privacidade.py`) pegam-se em números que SÃO preços
    conhecidos — sentinelas inconfundíveis — e exige-se que não apareçam em
    lado nenhum do site `sem-valores`. A regra apanha o que tem nome; a
    sentinela apanha o que não tem. Uma quantia nova com um nome novo dá
    vermelho em vez de vazar.

    Os CONTADORES sobre preços (quantas cartas não têm oferta, quantas vão ao
    preço da foil) caem na regra e desaparecem também. Não é fuga nenhuma —
    é uma página sem preços, e uma nota a dizer «7 sem preço» numa página sem
    preços não diz nada a ninguém.
"""

from __future__ import annotations

import re
import sqlite3

#: Os três valores, do mais fechado para o mais aberto.
VALORES = ("nada", "sem-valores", "tudo")
OMISSAO = "nada"

# Uma palavra INTEIRA do nome da chave (separada por `_` ou nas pontas). É o
# que distingue `preco_cents` de uma chave que por acaso contenha as letras.
DINHEIRO = re.compile(
    r"(^|_)(cents?|price|prices|preco|precos|preço|preços|valor|valores|"
    r"value|eur|euro|euros|custo|trend)(_|$)", re.I)

# AS AMBÍGUAS, e porque é que não bastava o nome.
#
# `total` é uma quantia nas linhas das Faltas e da wantlist (`price` ×
# `missing`, em cêntimos) e é uma CONTAGEM em todo o resto — é o denominador
# dos níveis («910 de 928»), o tamanho de um bloco, o total de runas. O nome é
# o mesmo e o sentido é o contrário; tirá-lo sempre partia os cartões da
# Coleção, deixá-lo sempre publicava o preço de cada linha em falta.
#
# MEDIDO no site real a 2026-09-29, contexto a contexto: nas **820**
# ocorrências em que o `total` é dinheiro, o dicionário tem SEMPRE um `price`
# ao lado; nas **84** em que é contagem, NENHUMA tem. Por isso o gatilho é o
# `price` (e não o `cents`, que aparece nos níveis, onde o `total` é o
# denominador).
AMBIGUAS = frozenset({"total"})
GATILHO = re.compile(r"(^|_)(price|preco|preço)(_|$)", re.I)


class ValorInvalido(ValueError):
    """`users.publico` só aceita `nada`, `sem-valores` ou `tudo`."""


# ---------------------------------------------------------------------------
# A coluna
# ---------------------------------------------------------------------------

def migrar(con: sqlite3.Connection) -> bool:
    """A coluna `publico` numa `users` que já exista. Idempotente.

    O `CREATE TABLE IF NOT EXISTS` não acrescenta colunas, e a `users` pode já
    ter nascido sem esta (a fundação é de horas antes). Corre no registo e
    dentro de cada `vault.db`, pelos dois sítios que abrem a tabela.

    **No momento em que a coluna nasce, o ANDRÉ fica em `tudo`** — é o que ele
    já tem e escolheu, e a regra desta semana é que para ele nada muda. Todos
    os outros ficam na omissão, que é `nada`. Isto corre UMA vez: a partir daí
    a escolha é de quem a fizer, e não se desfaz na abertura seguinte.
    """
    try:
        cols = {r[1] for r in con.execute("PRAGMA table_info(users)")}
    except sqlite3.OperationalError:
        return False
    if not cols or "publico" in cols:
        return False
    from . import utilizador
    con.execute(f"ALTER TABLE users ADD COLUMN publico TEXT NOT NULL "
                f"DEFAULT '{OMISSAO}' "
                f"CHECK (publico IN ('nada', 'sem-valores', 'tudo'))")
    con.execute("UPDATE users SET publico = 'tudo' WHERE user_id = ?",
                (utilizador.ANDRE,))
    return True


def validar(valor: str) -> str:
    v = (valor or "").strip().lower()
    if v not in VALORES:
        raise ValorInvalido(
            f"«{valor}» não é uma escolha de privacidade: só "
            f"{', '.join(VALORES)} (a omissão é «{OMISSAO}», a mais fechada).")
    return v


def _no_registo(con):
    """O `con` dado, ou uma ligação ao REGISTO aberta e fechada por nós.

    **O `publico` é um campo do REGISTO** (`data/users/registo.db`), não da
    coleção: quem o lê — uma rota HTTP, o `build.py` — não tem motivo nenhum
    para ter a base de cartas de alguém aberta. Por isso `con=None` é o uso
    normal e não uma excepção. A cópia que viaja dentro de cada `vault.db` é
    descritiva (`db._carimbar_dono`); as decisões lêem-se aqui.
    """
    import contextlib
    from . import utilizador
    if con is not None:
        migrar(con)
        return contextlib.nullcontext(con)

    @contextlib.contextmanager
    def abrir():
        c = utilizador.abrir_registo()
        try:
            migrar(c)
            yield c
        finally:
            c.close()
    return abrir()


def de(con: sqlite3.Connection | None = None, user_id: int | None = None) -> str:
    """A escolha de um utilizador. A omissão é a mais fechada.

    `con` é uma ligação ao REGISTO, ou `None` para a abrirmos nós.

    Uma linha sem o campo preenchido (uma base a meio de uma migração) lê-se
    como `"nada"` — quando não se sabe, não se publica.
    """
    from . import utilizador
    uid = utilizador.atual() if user_id is None else int(user_id)
    with _no_registo(con) as c:
        row = c.execute("SELECT publico FROM users WHERE user_id = ?",
                        (uid,)).fetchone()
        if row is None:
            raise utilizador.UtilizadorDesconhecido(
                f"não há utilizador com o id {uid}.")
        valor = row["publico"] if not isinstance(row, tuple) else row[0]
    return validar(valor) if valor else OMISSAO


def definir(con: sqlite3.Connection | None = None, user_id: int | None = None,
            valor: str = "") -> str:
    """Grava a escolha NO REGISTO. Devolve o valor validado."""
    from . import utilizador
    uid = utilizador.atual() if user_id is None else int(user_id)
    v = validar(valor)
    with _no_registo(con) as c:
        c.execute("UPDATE users SET publico = ? WHERE user_id = ?", (v, uid))
    return v


def publica(modo: str) -> bool:
    """Gera-se site para este modo? Em `"nada"` não se gera nada."""
    return validar(modo) != "nada"


def esconde_valores(modo: str) -> bool:
    return validar(modo) == "sem-valores"


# ---------------------------------------------------------------------------
# O filtro
# ---------------------------------------------------------------------------

def _numero(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def e_dinheiro(chave: str, valor, vizinhas=()) -> bool:
    """Esta chave, com este valor, é uma quantia?

    O `bool` é um `int` em Python e tinha de ser excluído à mão: `foil_only`
    e `price_is_foil` são respostas de sim/não e não dizem quanto custa nada.

    `vizinhas` são as outras chaves do mesmo dicionário, e é o que decide as
    AMBÍGUAS — ver o comentário do `AMBIGUAS`.
    """
    if isinstance(valor, bool) or valor is None:
        return False
    if not isinstance(valor, (int, float)):
        return False
    if DINHEIRO.search(chave):
        return True
    return chave in AMBIGUAS and any(GATILHO.search(k) for k in vizinhas)


def limpar(obj, modo: str):
    """O payload sem uma única quantia, se o modo o pedir.

    Devolve estrutura NOVA — não mexe no que lhe deram, para o mesmo payload
    poder ser escrito em dois modos sem se estragar a si próprio.
    """
    if not esconde_valores(modo):
        return obj
    return _limpar(obj)


def _limpar(obj, chave: str = "", vizinhas=(), dentro: bool = False):
    """`dentro` = já estamos DENTRO de uma chave que fala de dinheiro.

    A TERCEIRA regra, e nasceu de uma fuga a sério: o `progress.value` é
    `{"owned": 213751, "full": 128087, "hidden_owned": 0, ...}` — **quantias
    todas**, com nomes que não dizem dinheiro nenhum. A regra do nome não as
    apanhava, e foi a rede B (os preços-sentinela) que as encontrou.
    Um dicionário chamado `value` contém valores; o que está lá dentro é
    dinheiro, tenha o nome que tiver.
    """
    if isinstance(obj, dict):
        irmas = tuple(obj)
        return {k: (None if (e_dinheiro(k, v, irmas)
                             or (dentro and _numero(v)))
                    else _limpar(v, k, irmas,
                                 dentro or bool(DINHEIRO.search(k))))
                for k, v in obj.items()}
    if isinstance(obj, list):
        # A chave de quem contém a lista vale para os elementos: uma
        # `"precos": [1, 2, 3]` é uma lista de quantias.
        return [None if (e_dinheiro(chave, v, vizinhas) or (dentro and _numero(v)))
                else _limpar(v, chave, vizinhas, dentro)
                for v in obj]
    if isinstance(obj, str) and "€" in obj:
        # O recibo da Venda é o caso real: um texto pronto a copiar com o
        # total lá dentro. Não se emenda um texto gerado — tira-se.
        return None
    return obj

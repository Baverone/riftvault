"""As abas que se ESCONDEM, por config (André, 2026-09-25).

Palavras dele: *"Tira a aba 'A mais', 'Por Deck' e 'Pimp Deck'"*.

**Esconder não é apagar.** O `a_mais.py` e o `faltas.py` ficam como estavam, as
rotas continuam a responder (`/api/a_mais.json`, `/api/compras.json`), o
`build` continua a escrever os dois ficheiros e a CLI continua a ter o
`riftvault a-mais`. O que sai é o BOTÃO — a entrada na barra lateral, a vista
no índice dos decks, o atalho do Início e a rota que lá levava. É a diferença
entre isto e a tabela de preços que ele mandou apagar a 2026-09-19: ali o
código saiu e recupera-se de um commit; aqui **repor uma aba é tirar o nome da
lista, mais nada**.

Uma pergunta, uma função: `escondidas(cfg)`. O `metrics.index_payload` leva o
resultado no `api/index.json` (nos dois modos, que é o que faz as abas sairem
também do site publicado) e o `app.js` lê de lá — não há segunda lista no
JavaScript.

**Não conta para nada.** Esconder uma aba é apresentação: nenhum número da
Coleção, dos decks, das Faltas, das Encomendas, do A mais ou da Venda muda por
causa disto, e `tests/test_abas.py` fotografa-os todos para o provar.
"""

from __future__ import annotations

import unicodedata

from . import config

SECCAO_CFG = "abas"
CHAVE = "escondidas"

# Uma SECÇÃO é um separador de topo (a barra lateral); uma VISTA é uma
# sub-vista dentro de uma secção — as listas de compra do separador Decks.
# Ele nomeou as três («A mais», «Por Deck», «Pimp Deck») sem distinguir, e
# aqui também não é preciso: esconde-se pelo id, seja do que for.
SECCAO = "seccao"
VISTA = "vista"

# O CATÁLOGO das abas, pela ordem em que aparecem na barra (`NAV`, no
# `app.js`). O `id` é o que se escreve no config — é a rota (`#a-mais`) e o id
# da vista (`pordeck`), os mesmos nomes que o JavaScript usa.
ABAS: list[dict] = [
    {"id": "inicio", "tipo": SECCAO, "label": "Início"},
    {"id": "colecao", "tipo": SECCAO, "label": "Coleção"},
    {"id": "faltas-edicao", "tipo": SECCAO, "label": "Faltas"},
    {"id": "a-mais", "tipo": SECCAO, "label": "A mais"},
    {"id": "decks", "tipo": SECCAO, "label": "Decks"},
    {"id": "staples", "tipo": VISTA, "dentro": "decks", "label": "Staples"},
    {"id": "pordeck", "tipo": VISTA, "dentro": "decks", "label": "Por deck"},
    {"id": "pimp", "tipo": VISTA, "dentro": "decks", "label": "Pimp decks"},
    {"id": "encomendas", "tipo": SECCAO, "label": "Encomendas"},
    {"id": "venda", "tipo": SECCAO, "label": "Venda"},
    {"id": "selado", "tipo": SECCAO, "label": "Produto Selado"},
]

IDS = [a["id"] for a in ABAS]


def _norm(texto: str) -> str:
    """`"Pimp Deck"` -> `"pimp-deck"`: sem acentos, minúsculas, e tudo o que
    não é letra nem número vira um hífen só."""
    sem_acentos = "".join(c for c in unicodedata.normalize("NFD", str(texto))
                          if unicodedata.category(c) != "Mn")
    saida, hifen = [], False
    for c in sem_acentos.casefold():
        if c.isalnum():
            saida.append(c)
            hifen = False
        elif saida and not hifen:
            saida.append("-")
            hifen = True
    return "".join(saida).strip("-")


def _aliases() -> dict[str, str]:
    """Como se escreve cada aba: o id, o rótulo que ele vê, e as palavras dele.

    É a mesma ideia do `metrics.PALAVRA_KIND` (`promo` -> `special`): ele
    nomeia as coisas como as lê no ecrã, e o config aceita-o. `Pimp Deck`,
    `Pimp decks` e `pimp` são a mesma aba.
    """
    mapa: dict[str, str] = {}
    for a in ABAS:
        mapa.setdefault(_norm(a["id"]), a["id"])
        mapa.setdefault(_norm(a["label"]), a["id"])
    # As palavras da ordem de 2026-09-25, no singular como ele as escreveu.
    mapa.setdefault("pimp-deck", "pimp")
    mapa.setdefault("por-decks", "pordeck")
    return mapa


def resolver(nome: str) -> str:
    """O id de uma aba a partir do que está escrito no config.

    Um nome desconhecido REBENTA, com a lista do que existe — é a regra das
    outras listas do config (`master_set.fora_da_percentagem`,
    `decks.versoes_especiais`). Uma aba mal escrita que fosse ignorada em
    silêncio deixava-o a olhar para um separador que mandou esconder.
    """
    ident = _aliases().get(_norm(nome))
    if ident is None:
        raise ValueError(
            f"{SECCAO_CFG}.{CHAVE}: aba desconhecida {nome!r} "
            f"(aceita {', '.join(IDS)})")
    return ident


def lista(cfg: dict | None = None) -> list[str]:
    """`abas.escondidas` tal como está escrita no config. Sem chave, vazia."""
    bruto = (cfg or config.load()).get(SECCAO_CFG) or {}
    if not isinstance(bruto, dict):
        raise ValueError(f"{SECCAO_CFG}: tem de ser um objecto com `{CHAVE}`")
    valores = bruto.get(CHAVE)
    if valores is None:
        return []
    if not isinstance(valores, (list, tuple)) or not all(isinstance(x, str) for x in valores):
        raise ValueError(f"{SECCAO_CFG}.{CHAVE}: tem de ser uma lista de nomes de abas")
    return [x for x in valores if x.strip()]


def escondidas(cfg: dict | None = None) -> frozenset[str]:
    """Os ids das abas escondidas. Sem a chave, nenhuma — é o que valia até
    2026-09-25 e o que um riftvault sem config mostra."""
    return frozenset(resolver(x) for x in lista(cfg))


def visivel(ident: str, cfg: dict | None = None) -> bool:
    return ident not in escondidas(cfg)


def visiveis(cfg: dict | None = None) -> list[str]:
    """Os ids das abas que se vêem, pela ordem da barra."""
    fora = escondidas(cfg)
    return [i for i in IDS if i not in fora]


def payload(cfg: dict | None = None) -> dict:
    """O que vai no `api/index.json`, e de onde o `app.js` lê.

    Vai nos DOIS modos, com o mesmo conteúdo: uma aba escondida sai do 8770 e
    do site publicado pela mesma linha de config. `catalogo` é só para a página
    e o CLI poderem escrever o rótulo de uma aba escondida sem o repetirem.
    """
    fora = escondidas(cfg)
    return {
        "escondidas": [i for i in IDS if i in fora],
        "visiveis": [i for i in IDS if i not in fora],
        "catalogo": [{"id": a["id"], "tipo": a["tipo"], "label": a["label"]} for a in ABAS],
    }


def rotulo(ident: str) -> str:
    for a in ABAS:
        if a["id"] == ident:
            return a["label"]
    return ident


def texto(cfg: dict | None = None) -> str:
    """Uma linha para o `riftvault stats`."""
    fora = escondidas(cfg)
    if not fora:
        return "Abas escondidas: nenhuma."
    nomes = ", ".join(f"{rotulo(i)} ({i})" for i in IDS if i in fora)
    return (f"Abas escondidas: {nomes} — só o botão; o cálculo e as rotas "
            f"continuam (`{SECCAO_CFG}.{CHAVE}` no riftvault_config.json).")

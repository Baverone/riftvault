"""«Produto Selado» (André, 2026-09-25): o que HÁ, o que TEM e o que NÃO TEM.

Palavras dele: *"faz uma lista, para acrescentar um separador que e 'Produto
Selado', em que vai tudo o que e produtos de coleccao do Riftbound, como
displays ou boxcase, ou duel decks, proving ground, etc etc, para eu saber o
que ha, o que tenho e o que nao tenho"*.

DE ONDE VEM A LISTA
    O catálogo da **RiftScribe não tem produto selado** — tem cartas, e só.
    Procurado na spec: não há endpoint nem campo de display, booster box ou
    deck. A fonte é o **CardTrader**, a mesma API v2 que já dá os preços, com
    o mesmo token.

    E a separação selado/single **não é um palpite meu**: o CardTrader tem uma
    tabela de CATEGORIAS por jogo (`GET /categories`), e as do Riftbound são
    treze, com nome:

        258 Riftbound Singles            <- as cartas (o `prices.SINGLES_CATEGORY`)
        259 Riftbound Booster Boxes      264 Riftbound Playmats
        260 Riftbound Boosters           265 Riftbound Albums
        261 Riftbound Bundles            266 Riftbound Sleeves
        262 Riftbound Starter Decks      267 Riftbound Deck Boxes
        263 Riftbound Box Sets & Displays 268 Riftbound Memorabilia and Gadgets
        283 Riftbound Complete Sets      284 Riftbound Oversized

    Cada blueprint traz o seu `category_id`. O `riftvault map` já usava a 258
    para ficar só com as cartas (*"booster boxes, playmats e afins"*, no
    comentário de 2026-08-31); aqui é o outro lado da mesma linha.

    **Por omissão entram seis categorias** (`selado.categorias`): 259, 260,
    261, 262, 263 e 283 — displays, boosters, bundles, decks, box sets/cases e
    conjuntos. Os PLAYMATS, as SLEEVES, as MOEDAS e as cartas OVERSIZED
    **ficam de fora**: não são produto selado, são acessórios de jogo, e ele
    nomeou *"displays ou boxcase, ou duel decks, proving ground"*. Não
    desaparecem em silêncio — o `scope.fora` conta-os por categoria e a página
    diz quantos são. Metê-los é acrescentar o número à lista do config.

OS ACESSÓRIOS DE COLEÇÃO TÊM SECÇÃO PRÓPRIA (2026-09-25)
    Os BINDERS (Albums, 265) e os DECK BOXES (267) são outra coisa: vendem-se
    selados, guardam-se, e o *Radiance: 9-Pocket Collector Binder* anda a
    33,99 € em loja portuguesa. Entram por `selado.acessorios`, numa **secção
    à parte** com contadores e valor próprios, e um filtro que os esconde.

    **NÃO contam para o produto selado** — nem no «o que há», nem no «tenho»,
    nem no «não tenho», nem no valor do selado; e o valor deles, como o do
    selado, nunca se soma ao da Coleção. São três totais separados, de
    propósito: misturá-los mudava um número que ele já conhece.

    Ficaram de fora, e são decisão explicada: as 48 playmats e as 31 sleeves
    (acessórios de jogo, não de coleção — e são 79 linhas a afogar 85), a
    memorabilia (268 — os standees acrílicos VÊM DENTRO do Proving Grounds
    Box Set, e contá-los à parte era contar o mesmo produto duas vezes) e as
    oversized (284 — são CARTAS grandes, não produto selado).

O QUE O CARDTRADER REPETE (2026-09-25)
    Quatro dos Trial Decks da Origins aparecem com DOIS blueprints cada, com
    o mesmo nome, a mesma edição, a mesma categoria e a versão vazia nos dois.
    Sondadas as ofertas dos oito: os antigos (330845..330848) têm **zero
    ofertas e nenhum `card_market_id`**; os novos (363136..363139) têm as
    ofertas todas (1 a 3 cada) e um id do Cardmarket cada. É **duplicação do
    catálogo deles**, não dois produtos — `selado.juntar_duplicados` (ligado)
    junta-os num só, e a linha diz que blueprint é que juntou. Não se junta às
    cegas: a chave é (edição, nome, versão, categoria), e por isso os «2024
    Trial Deck Set» e «2025 Trial Deck Set», que dizem o ano na versão,
    continuam a ser dois.

O QUE FICA EM DISCO
    `data/selado_catalogo.json` (committado) — o que a API devolveu, já
    arrumado, mais o preço de cada produto. É o CATÁLOGO: o que existe. Atualiza
    -se com `riftvault selado --sync`, que é um comando à mão — **o ritmo do
    `riftvault prices` diário não foi tocado**.

    `sealed_copies` (vault.db) — quantas ele tem de cada. Começa a ZERO.

    `selado.extra` (config) — os produtos que a API não tem, escritos à mão:
    `nome`, `edicao`, `tipo`, `data`, `preco_eur`, `conteudo` e `nota`. A
    lista da app é a da API MAIS estes.

    **São precisamente o que um catálogo de mercado não lista, porque quase
    não circula solto** (levantamento dele de 2026-09-25, em
    `ai-pc/work/riftbound-produto-selado.md`): os 7 displays de champion decks
    (4 decks iguais), os 2 displays de showdown (4 conjuntos), os cases de
    vaults e o do Proving Grounds, e os **Pre-Rift EVENT Kit** — 16 kits de
    jogador + 1 display, ~480 USD —, que são outro produto que o «Pre-Rift
    Kit» do CardTrader (o kit de UM jogador, ~40 USD) e por isso aparecem os
    dois, cada um com o seu `conteudo`.

    **Os MSRP dele são em DÓLARES e ficam no `conteudo`, não no preço.** O
    `preco_eur` fica vazio (a linha diz «—») porque não há taxa de câmbio
    validada em lado nenhum do riftvault, e inventar uma era escrever um
    número que ninguém mediu. Ficam contados no `sem_preco`.

O SELADO NÃO ENTRA NA COLEÇÃO
    Nem nos níveis, nem no denominador, nem no A mais, nem nas Faltas, nem nas
    wantlists, nem nos decks, nem no foil, nem nas cópias próprias, nem na
    Venda. As cópias vivem numa tabela à parte que mais nenhum módulo lê, e o
    VALOR do selado é um total próprio, **nunca somado ao valor da Coleção**.
    `tests/test_selado.py` fotografa tudo isso, mete e tira produto, e exige
    que fique igual — é a mesma defesa das cópias próprias (2026-09-21), do
    foil (2026-09-22) e da Venda (2026-09-25).

OS LINKS DE COMPRA (2026-09-25)
    Cada linha leva um link para o **Cardmarket** e outro para o
    **CardTrader** (*"Se possivel, mete link para compra no cardmarket e no
    cardtrader"*). Os templates vivem no bloco `mercados` do config, que é o
    mesmo que a Venda usa — `riftvault/mercados.py`, que explica o que está
    validado e o que não está.

    O do **CardTrader está validado**: o `blueprint_id` sozinho responde 200 e
    o site acrescenta-lhe o slug. O do **Cardmarket não pôde ser** (403 a
    pedidos automáticos, nem o `robots.txt` responde), e por isso quem não tem
    `cardmarket_id` leva **pesquisa pelo nome**, marcada como tal.

    Medido a 2026-09-25 no catálogo real, nos 98 produtos selados: **81 têm
    `blueprint_id`** e **52 têm `cardmarket_id`** — 29 ficam com pesquisa só
    no Cardmarket, e os 17 do `selado.extra` (que a API não tem) levam
    pesquisa nos dois. Nos 19 acessórios: 19 com `blueprint_id`, **nenhum**
    com `cardmarket_id` (o `--sync` ainda não passou por eles). O
    `payload.links` conta isto para a página o poder dizer.

POR SAIR
    Um produto de uma edição ainda por lançar (a Radiance sai a 2026-10-23)
    aparece marcado **«por sair»** e **não conta para o que falta**: ele não
    pode ter o que ainda não existe. As datas vêm do config
    (`selado.datas_por_edicao`, ditas por ele) — a API do CardTrader **não dá
    data de lançamento nenhuma** (uma expansão são quatro campos: `id`,
    `game_id`, `code`, `name`). Uma edição anunciada sem data exacta escreve-se
    em `selado.por_sair`.
"""

from __future__ import annotations

import json
import re
import sqlite3
import time
from datetime import date, datetime, timezone

from . import config, mercados

# As categorias do CardTrader, por nome, como elas vêm do `/categories`. Está
# aqui para o `payload` poder escrever o nome de uma categoria que ficou de
# fora sem ter de ir à API — e é o ficheiro do catálogo que manda, quando o
# tem (uma categoria nova aparece lá primeiro).
CATEGORIAS_CONHECIDAS = {
    258: "Riftbound Singles",
    259: "Riftbound Booster Boxes",
    260: "Riftbound Boosters",
    261: "Riftbound Bundles",
    262: "Riftbound Starter Decks",
    263: "Riftbound Box Sets & Displays",
    264: "Riftbound Playmats",
    265: "Riftbound Albums",
    266: "Riftbound Sleeves",
    267: "Riftbound Deck Boxes",
    268: "Riftbound Memorabilia and Gadgets",
    283: "Riftbound Complete Sets",
    284: "Riftbound Oversized",
}

DEFAULTS: dict = {
    # As categorias do CardTrader que contam como PRODUTO SELADO. Ver o
    # cabeçalho: os playmats, as sleeves, a memorabilia e as cartas oversized
    # ficam de fora, contadas em `scope.fora`. Meter uma é acrescentar o
    # número aqui.
    "categorias": [259, 260, 261, 262, 263, 283],
    # Os ACESSÓRIOS — binders (Albums, 265) e deck boxes (267) —, que entram
    # numa SECÇÃO PRÓPRIA e **não contam para o produto selado** (nem no «o
    # que há», nem no «tenho», nem no «não tenho», nem no valor do selado):
    # têm contadores e valor próprios, e um filtro que os esconde. Decisão de
    # 2026-09-25, a pedido dele — ver o cabeçalho. Lista vazia = nenhum
    # acessório, e todos voltam ao `scope.fora`.
    "acessorios": [265, 267],
    # O CardTrader tem, em quatro dos Trial Decks da Origins, DOIS blueprints
    # com o mesmo nome, a mesma edição, a mesma categoria e a mesma versão
    # (vazia). Medido a 2026-09-25 na API: os antigos (330845/846/847/848) têm
    # ZERO ofertas e nenhum `card_market_id`; os novos (363136..363139) têm as
    # ofertas todas e um id do Cardmarket cada. É duplicação do catálogo
    # deles, não dois produtos — junta-se, e a linha diz quais eram. `false`
    # mostra os dois.
    "juntar_duplicados": True,
    # A DATA DE SAÍDA de cada edição, por código do CardTrader em maiúsculas.
    # Vem DELE (2026-09-25) — a API não dá datas. Uma edição que não esteja
    # aqui fica sem data, e sem data não é «por sair».
    "datas_por_edicao": {
        "OGN": "2025-10-31",
        "SFD": "2026-02-13",
        "UNL": "2026-05-08",
        "VEN": "2026-07-31",
        "RAD": "2026-10-23",
    },
    # As edições ANUNCIADAS mas ainda sem data exacta (ele: *"depois Legacy
    # (LGC) e The Reckoning (REC) em 2027"*). Os produtos delas são «por
    # sair» na mesma, e por isso não contam para o que falta.
    "por_sair": ["LGC", "PG2", "REC"],
    # A ordem das edições no ecrã. O que não estiver aqui vem a seguir, por
    # código.
    "ordem_das_edicoes": ["OGN", "OGS", "SFD", "UNL", "VEN", "RAD", "LGC", "PG2", "REC"],
    # Produtos que a API não tem (regionais, promocionais, e o que quase não
    # circula solto — displays de decks, cases de vaults, kits de loja), à
    # mão. Cada um: `nome` (obrigatório), `edicao`, `tipo`, `data`,
    # `preco_eur`, `conteudo` (o que vem dentro) e `nota` (ressalvas).
    "extra": [],
}

# ---------------------------------------------------------------------------
# Os TIPOS, com as palavras dele
# ---------------------------------------------------------------------------

TIPOS: list[dict] = [
    {"id": "display", "label": "Display", "nota": "booster box"},
    {"id": "case", "label": "Case", "nota": "caixa de displays"},
    {"id": "caixa", "label": "Caixa", "nota": "box set, gift box"},
    {"id": "proving-grounds", "label": "Proving Grounds", "nota": "o produto de iniciação"},
    {"id": "deck", "label": "Deck", "nota": "champion, trial, showdown"},
    {"id": "bundle", "label": "Bundle", "nota": "vault, pre-rift kit"},
    {"id": "booster", "label": "Booster", "nota": "pacote solto"},
    {"id": "conjunto", "label": "Conjunto", "nota": "set de cartas vendido junto"},
    # Os dois da secção dos ACESSÓRIOS (2026-09-25). Estão no fim porque a
    # ordem desta lista é a ordem dentro de cada edição, e a secção deles vem
    # depois — mas têm nome próprio: «Outro» num binder não diz nada.
    {"id": "binder", "label": "Binder", "nota": "álbum de coleção"},
    {"id": "deck-box", "label": "Deck box", "nota": "caixa de deck"},
    {"id": "outro", "label": "Outro", "nota": ""},
]
TIPO_IDS = [t["id"] for t in TIPOS]
TIPO_LABEL = {t["id"]: t["label"] for t in TIPOS}

# A categoria decide o tipo, menos quando o NOME diz outra coisa — ver `tipo_de`.
CATEGORIA_TIPO = {259: "display", 260: "booster", 261: "bundle",
                  262: "deck", 263: "caixa", 283: "conjunto",
                  265: "binder", 267: "deck-box"}

_CASE = re.compile(r"\bcase\b", re.I)
_PG = re.compile(r"proving\s+grounds", re.I)


def tipo_de(nome: str, versao: str | None, categoria_id: int | None) -> str:
    """O tipo de um produto: a categoria do CardTrader, corrigida pelo nome.

    A categoria «Box Sets & Displays» (263) mete no mesmo saco o *Origins
    Booster Box Case* (seis displays), o *Origins: Proving Grounds* e a
    *Instant Match Box*. São três coisas diferentes para quem coleciona, e ele
    nomeou duas delas (*"boxcase"*, *"proving ground"*), por isso o nome manda:
    o que disser «case» é um case e o que disser «Proving Grounds» é isso.
    """
    texto = f"{nome or ''} {versao or ''}"
    if _PG.search(texto):
        return "proving-grounds"
    if _CASE.search(texto):
        return "case"
    return CATEGORIA_TIPO.get(categoria_id, "outro")


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


def opcoes(cfg: dict | None = None) -> dict:
    bruto = (cfg or config.load()).get("selado") or {}
    if not isinstance(bruto, dict):
        raise ValueError("selado: tem de ser um objecto")
    out = {**DEFAULTS, **{k: v for k, v in bruto.items() if not k.startswith("_")}}

    cats = out["categorias"]
    if not isinstance(cats, (list, tuple)) or not cats:
        raise ValueError("selado.categorias: tem de ser uma lista de ids do CardTrader, "
                         "e não pode estar vazia")
    try:
        cats = [int(c) for c in cats]
    except (TypeError, ValueError):
        raise ValueError("selado.categorias: os ids são números (259, 260, …)") from None
    # A 258 são as CARTAS. Deixá-la entrar aqui punha 1180 singles no separador
    # do selado — é erro de escrita, não uma escolha.
    from .prices import SINGLES_CATEGORY
    if SINGLES_CATEGORY in cats:
        raise ValueError(f"selado.categorias: a {SINGLES_CATEGORY} são as CARTAS "
                         f"(Riftbound Singles) — não é produto selado")
    out["categorias"] = cats

    acess = out.get("acessorios") or []
    if not isinstance(acess, (list, tuple)):
        raise ValueError("selado.acessorios: uma lista de ids do CardTrader "
                         "(vazia = nenhum acessório)")
    try:
        acess = [int(c) for c in acess]
    except (TypeError, ValueError):
        raise ValueError("selado.acessorios: os ids são números (265, 267, …)") from None
    if SINGLES_CATEGORY in acess:
        raise ValueError(f"selado.acessorios: a {SINGLES_CATEGORY} são as CARTAS "
                         f"(Riftbound Singles)")
    # As duas listas respondem a perguntas diferentes («é produto selado?» e
    # «é acessório de coleção?»), e uma categoria nas duas não tem resposta:
    # ou conta para o selado ou está na secção à parte.
    repetidas = sorted(set(acess) & set(cats))
    if repetidas:
        raise ValueError(f"selado.acessorios: {', '.join(str(c) for c in repetidas)} "
                         f"também está em selado.categorias — ou é produto selado, "
                         f"ou é acessório")
    out["acessorios"] = acess
    out["juntar_duplicados"] = bool(out.get("juntar_duplicados", True))

    datas = out["datas_por_edicao"] or {}
    if not isinstance(datas, dict):
        raise ValueError("selado.datas_por_edicao: um objecto {EDIÇÃO: 'AAAA-MM-DD'}")
    limpas = {}
    for k, v in datas.items():
        if v in (None, ""):
            continue
        try:
            date.fromisoformat(str(v))
        except ValueError:
            raise ValueError(f"selado.datas_por_edicao[{k}]: {v!r} não é uma data "
                             f"AAAA-MM-DD") from None
        limpas[str(k).upper()] = str(v)
    out["datas_por_edicao"] = limpas
    out["por_sair"] = [str(x).upper() for x in (out["por_sair"] or [])]
    out["ordem_das_edicoes"] = [str(x).upper() for x in (out["ordem_das_edicoes"] or [])]

    extra = out["extra"] or []
    if not isinstance(extra, (list, tuple)):
        raise ValueError("selado.extra: uma lista de produtos")
    out["extra"] = [_ler_extra(i, x) for i, x in enumerate(extra)]
    return out


def _ler_extra(i: int, x) -> dict:
    """Um produto escrito à mão no config. O `nome` é obrigatório; um `tipo`
    que não exista REBENTA, com a lista dos que há — é a regra das outras
    listas do config."""
    if not isinstance(x, dict):
        raise ValueError(f"selado.extra[{i}]: cada produto é um objecto com `nome`")
    nome = str(x.get("nome") or "").strip()
    if not nome:
        raise ValueError(f"selado.extra[{i}]: falta o `nome`")
    tipo = str(x.get("tipo") or "outro").strip().lower()
    if tipo not in TIPO_IDS:
        raise ValueError(f"selado.extra[{i}].tipo: {tipo!r} não existe "
                         f"(aceita {', '.join(TIPO_IDS)})")
    data = x.get("data")
    if data not in (None, ""):
        try:
            date.fromisoformat(str(data))
        except ValueError:
            raise ValueError(f"selado.extra[{i}].data: {data!r} não é AAAA-MM-DD") from None
    preco = x.get("preco_eur")
    if preco not in (None, ""):
        try:
            preco = round(float(preco) * 100)
        except (TypeError, ValueError):
            raise ValueError(f"selado.extra[{i}].preco_eur: {preco!r} não é um preço") from None
    else:
        preco = None
    return {"nome": nome, "edicao": str(x.get("edicao") or "").upper(),
            "tipo": tipo, "data": str(data) if data else None,
            "preco_cents": preco,
            # `conteudo` é o que vem DENTRO (4 decks iguais, 16 kits + 1
            # display, 12 vaults) — é por isso que estes produtos estão aqui:
            # não circulam soltos e o catálogo de mercado não os lista. A
            # `nota` fica para as RESSALVAS (uma fonte diz 4, outra 12), que
            # se lêem de outra maneira e não se podem confundir com o
            # conteúdo.
            "conteudo": str(x.get("conteudo") or "") or None,
            "nota": str(x.get("nota") or "") or None}


# ---------------------------------------------------------------------------
# O catálogo em disco
# ---------------------------------------------------------------------------


_VAZIO = {"generated_at": None, "fonte": "cardtrader", "produtos": [],
          "precos": {}, "categorias": {}, "expansoes": []}
# Lido uma vez por versão do ficheiro: a lista pede-se dezenas de vezes por
# payload (uma por produto, no nome da categoria) e reler 200 KB de JSON de
# cada vez era o ficheiro a ser lido 85 vezes para desenhar uma página.
_cache: tuple[str, float, dict] | None = None


def carregar() -> dict:
    """O `data/selado_catalogo.json`, ou um esqueleto vazio.

    Sem o ficheiro a secção mostra-se na mesma, vazia, a dizer que é preciso
    correr `riftvault selado --sync` — nunca rebenta a página por não haver
    catálogo.
    """
    global _cache
    caminho = config.SELADO_PATH
    if not caminho.exists():
        return dict(_VAZIO)
    chave = (str(caminho), caminho.stat().st_mtime_ns)
    if _cache and _cache[0] == chave[0] and _cache[1] == chave[1]:
        return _cache[2]
    dados = json.loads(caminho.read_text(encoding="utf-8"))
    for k, v in _VAZIO.items():
        if dados.get(k) is None:
            dados[k] = v if not isinstance(v, (list, dict)) else type(v)()
    _cache = (chave[0], chave[1], dados)
    return dados


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Quantas ele tem
# ---------------------------------------------------------------------------


class ProdutoDesconhecido(ValueError):
    pass


def tenho(con: sqlite3.Connection) -> dict[str, int]:
    return {r["product_id"]: r["qty"] for r in
            con.execute("SELECT product_id, qty FROM sealed_copies")}


def ajustar(con: sqlite3.Connection, product_id: str, delta: int = 1,
            cfg: dict | None = None, source: str = "web") -> dict:
    """Soma `delta` ao que ele tem de um produto. Nunca abaixo de zero.

    **Não toca no `copies` nem em conta nenhuma da Coleção** — escreve só na
    `sealed_copies`. Um produto que não esteja na lista (nem da API nem do
    config) é `ProdutoDesconhecido`: um id inventado não pode nascer aqui.
    """
    validos = {p["id"] for p in _crus(cfg)}
    if product_id not in validos:
        raise ProdutoDesconhecido(f"{product_id} não está na lista do produto selado")
    atual = tenho(con).get(product_id, 0)
    novo = max(0, atual + int(delta))
    if novo == 0:
        con.execute("DELETE FROM sealed_copies WHERE product_id = ?", (product_id,))
    else:
        con.execute(
            "INSERT INTO sealed_copies (product_id, qty, updated_at) VALUES (?,?,?) "
            "ON CONFLICT(product_id) DO UPDATE SET qty = excluded.qty, "
            "updated_at = excluded.updated_at", (product_id, novo, _now()))
    return {"product_id": product_id, "qty": novo, "applied": novo - atual,
            "source": source}


# ---------------------------------------------------------------------------
# A lista
# ---------------------------------------------------------------------------


def _slug(texto: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", str(texto).lower()).strip("-")
    return s or "produto"


def _nome_para_procurar(p: dict) -> str:
    """O termo dos links de PESQUISA: o nome do produto, com a versão atrás
    quando existe («Trial Deck Set», «2024 Trial Deck Set»).

    Não se lhe cola a edição — os nomes do CardTrader já a trazem à frente
    («Origins Booster Box»), e repeti-la só estreitava a pesquisa. As ASPAS
    saem (`Origins: "Jinx" Champion Deck Display`): são a convenção com que os
    nomes dos champion decks se escrevem, e numa caixa de pesquisa lêem-se
    como «frase exacta», que é o contrário do que se quer aqui.
    """
    return " ".join(x for x in (p.get("nome"), p.get("versao")) if x).replace('"', "").strip()


def _chave_duplicado(p: dict) -> tuple:
    """O que faz de dois blueprints o MESMO produto: a mesma edição, o mesmo
    nome, a mesma versão e a mesma categoria. Se algum destes diferir são
    produtos diferentes e não se juntam — é o caso dos «2024 Trial Deck Set» e
    «2025 Trial Deck Set», que dizem o ano na versão."""
    return (p["edicao"], p["nome"].strip().lower(),
            (p["versao"] or "").strip().lower(), p["categoria_id"])


def _vivo(p: dict) -> tuple:
    """Qual dos blueprints repetidos é o que o mercado usa, para ser ele o que
    fica. Por esta ordem: tem id do Cardmarket, tem preço, tem mais anúncios,
    e por fim o `blueprint_id` maior (o mais recente). Medido nos Trial Decks
    da Origins: os que ficam de fora têm ZERO ofertas."""
    return (bool(p["cardmarket_id"]), p["preco_cents"] is not None,
            p["n_listings"] or 0, p["blueprint_id"] or 0)


def _juntar_duplicados(lista: list[dict]) -> list[dict]:
    """Junta os blueprints repetidos do CardTrader num produto só.

    O que fica leva `duplicados` com os ids dos outros — a linha diz-os, para
    isto nunca ser uma carta a desaparecer em silêncio. O que ele tenha
    gravado num id que se juntou continua a contar (ver `itens`).
    """
    grupos: dict[tuple, list[dict]] = {}
    for p in lista:
        grupos.setdefault(_chave_duplicado(p), []).append(p)
    fica_por_chave = {}
    for chave, membros in grupos.items():
        fica, *resto = sorted(membros, key=_vivo, reverse=True)
        fica["duplicados"] = [{"id": o["id"], "blueprint_id": o["blueprint_id"],
                               "n_listings": o["n_listings"]} for o in resto]
        fica_por_chave[chave] = fica
    # Pela ordem do ficheiro, que é a da API — o `itens` é que ordena a sério.
    return [p for p in lista if fica_por_chave[_chave_duplicado(p)] is p]


def _crus(cfg: dict | None = None) -> list[dict]:
    """Os produtos EM ÂMBITO, da API e do config, sem as contagens dele.

    Leva o produto selado E os acessórios (`acessorio: True`), porque é a
    lista que decide que ids existem — o `ajustar` valida contra ela, e os
    `+`/`−` de um binder têm de funcionar como os de um display. Quem conta
    é que separa os dois.
    """
    op = opcoes(cfg)
    cats = set(op["categorias"])
    acess = set(op["acessorios"])
    dados = carregar()
    precos = dados.get("precos") or {}
    out: list[dict] = []
    for p in dados["produtos"]:
        cid = int(p.get("categoria_id") or 0)
        if cid not in cats and cid not in acess:
            continue
        bid = p["blueprint_id"]
        pr = precos.get(str(bid)) or precos.get(bid) or {}
        out.append({
            "id": f"ct-{bid}",
            "fonte": "cardtrader",
            "acessorio": cid in acess,
            "blueprint_id": bid,
            "nome": p.get("nome") or "",
            "versao": p.get("versao") or "",
            "categoria_id": p.get("categoria_id"),
            "edicao": (p.get("edicao") or "").upper(),
            "edicao_nome": p.get("edicao_nome") or "",
            "img": p.get("img"),
            "cardmarket_id": p.get("cardmarket_id"),
            "preco_cents": pr.get("cents"),
            "preco_dia": pr.get("day"),
            "n_listings": pr.get("n_listings"),
            "n_sellers": pr.get("n_sellers"),
            "conteudo": None,
            "nota": None,
            "duplicados": [],
            "tipo_forcado": None,
        })
    if op["juntar_duplicados"]:
        out = _juntar_duplicados(out)
    for x in op["extra"]:
        out.append({
            "id": f"cfg-{_slug(x['edicao'] + '-' + x['nome'])}",
            "fonte": "config",
            "acessorio": False,
            "blueprint_id": None,
            "nome": x["nome"], "versao": "",
            "categoria_id": None,
            "edicao": x["edicao"], "edicao_nome": "",
            "img": None, "cardmarket_id": None,
            "preco_cents": x["preco_cents"], "preco_dia": None,
            "n_listings": None, "n_sellers": None,
            "conteudo": x["conteudo"],
            "nota": x["nota"],
            "duplicados": [],
            "tipo_forcado": x["tipo"], "data_forcada": x["data"],
        })
    return out


def _ordem_edicao(code: str, op: dict) -> tuple:
    lista = op["ordem_das_edicoes"]
    return (lista.index(code), "") if code in lista else (len(lista), code)


def itens(con: sqlite3.Connection | None, cfg: dict | None = None,
          hoje: date | None = None) -> list[dict]:
    """A lista inteira, com o tipo, a data, o preço, quantas ele tem e os dois
    links de compra."""
    op = opcoes(cfg)
    op_links = mercados.opcoes(cfg)
    hoje = hoje or date.today()
    quantidades = tenho(con) if con is not None else {}
    saida: list[dict] = []
    for p in _crus(cfg):
        tipo = p.get("tipo_forcado") or tipo_de(p["nome"], p["versao"], p["categoria_id"])
        data = p.get("data_forcada") or op["datas_por_edicao"].get(p["edicao"])
        # «Por sair» por DATA (a Radiance, 2026-10-23) ou porque a edição está
        # anunciada sem data exacta (`selado.por_sair`).
        por_sair = bool(p["edicao"] in op["por_sair"]
                        or (data and date.fromisoformat(data) > hoje))
        # O que ele tenha gravado num blueprint que entretanto se juntou a
        # outro continua a contar: juntar duas linhas do catálogo do
        # CardTrader não pode apagar unidades dele.
        qty = quantidades.get(p["id"], 0) + sum(
            quantidades.get(d["id"], 0) for d in p.get("duplicados") or [])
        preco = p["preco_cents"]
        saida.append({
            **{k: v for k, v in p.items() if not k.endswith("_forcado")
               and k != "data_forcada"},
            "tipo": tipo,
            "tipo_label": TIPO_LABEL[tipo],
            "data": data,
            "por_sair": por_sair,
            "qty": qty,
            "tenho": qty > 0,
            "valor_cents": (preco or 0) * qty,
            "categoria": _nome_da_categoria(p["categoria_id"]),
            "edicao_label": p["edicao_nome"] or p["edicao"] or "—",
            # OS DOIS LINKS DE COMPRA (2026-09-25, a pedido dele). Directos
            # quando há id, PESQUISA pelo nome quando não há — nunca um link
            # montado com um id que não existe. O do CardTrader está
            # validado; o do Cardmarket não (403 a pedidos automáticos) — ver
            # `mercados.py`.
            "links": mercados.links(_nome_para_procurar(p),
                                    cardmarket_id=p["cardmarket_id"],
                                    blueprint_id=p["blueprint_id"],
                                    selado=True, op=op_links),
        })
    saida.sort(key=lambda x: (_ordem_edicao(x["edicao"], op),
                             TIPO_IDS.index(x["tipo"]), x["nome"].lower()))
    return saida


def _nome_da_categoria(cid) -> str | None:
    if cid is None:
        return None
    do_ficheiro = (carregar().get("categorias") or {})
    return (do_ficheiro.get(str(cid)) or do_ficheiro.get(cid)
            or CATEGORIAS_CONHECIDAS.get(int(cid))
            # Uma categoria que o `/categories` do Riftbound não traz (o
            # CardTrader tem categorias partilhadas entre jogos — hoje é uma
            # só, o dado da Instant Match Box). Diz-se o número em vez de se
            # inventar um nome.
            or f"sem nome no CardTrader ({cid})")


# ---------------------------------------------------------------------------
# Os três estados: o que HÁ, o que TEM, o que NÃO TEM
# ---------------------------------------------------------------------------


def contar(lista: list[dict]) -> dict:
    """Os contadores do topo.

    `falta` **não conta os «por sair»**: ele não pode ter o que ainda não
    saiu, e pôr a Radiance na lista do que lhe falta era medir outra coisa.
    """
    saiu = [x for x in lista if not x["por_sair"]]
    tem = [x for x in lista if x["qty"] > 0]
    # A percentagem é «dos que saíram», e por isso o numerador também: uma
    # pré-encomenda já entregue de um produto por sair conta no `tenho` (ele
    # tem-na) mas não nesta conta, senão dava mais de 100 %.
    tem_saiu = [x for x in saiu if x["qty"] > 0]
    return {
        "ha": len(lista),
        "saiu": len(saiu),
        "por_sair": len(lista) - len(saiu),
        "tenho": len(tem),
        "copias": sum(x["qty"] for x in lista),
        "falta": sum(1 for x in saiu if x["qty"] == 0),
        "pct": round(100 * len(tem_saiu) / len(saiu), 1) if saiu else 0.0,
        # O VALOR DO SELADO. É um total PRÓPRIO — nunca se soma ao valor da
        # Coleção, que conta cartas. Ver o cabeçalho.
        "valor_cents": sum(x["valor_cents"] for x in tem),
        "sem_preco": sum(1 for x in lista if x["preco_cents"] is None),
        "do_config": sum(1 for x in lista if x["fonte"] == "config"),
    }


def por_edicao(lista: list[dict], cfg: dict | None = None) -> list[dict]:
    op = opcoes(cfg)
    grupos: dict[str, dict] = {}
    for x in lista:
        g = grupos.setdefault(x["edicao"] or "—", {
            "set": x["edicao"] or "—", "label": x["edicao_label"], "items": []})
        g["items"].append(x)
    ordenados = sorted(grupos.values(),
                       key=lambda g: _ordem_edicao(g["set"], op))
    for g in ordenados:
        g["totals"] = contar(g["items"])
    return ordenados


def fora(cfg: dict | None = None) -> list[dict]:
    """O que o CardTrader tem e NÃO entra em lado nenhum: playmats, sleeves,
    memorabilia, oversized. Contados por categoria — nunca se apagam em
    silêncio. Os binders e os deck boxes SAÍRAM daqui a 2026-09-25: passaram a
    ter secção própria (`selado.acessorios`)."""
    op = opcoes(cfg)
    dentro = set(op["categorias"]) | set(op["acessorios"])
    from .prices import SINGLES_CATEGORY
    contagem: dict[int, int] = {}
    for p in carregar()["produtos"]:
        cid = int(p.get("categoria_id") or 0)
        if cid in dentro or cid == SINGLES_CATEGORY:
            continue
        contagem[cid] = contagem.get(cid, 0) + 1
    return [{"categoria_id": cid, "categoria": _nome_da_categoria(cid), "n": n}
            for cid, n in sorted(contagem.items())]


def contar_links(lista: list[dict]) -> dict:
    """Quantas linhas levam link DIRECTO e quantas caem na pesquisa, por
    mercado. A página diz o número em vez de deixar o utilizador descobrir,
    linha a linha, que metade dos links são pesquisas."""
    out = {}
    for mercado in ("cardmarket", "cardtrader"):
        directos = sum(1 for x in lista
                       if not (x["links"][mercado]["pesquisa"]))
        out[mercado] = {"directos": directos, "pesquisa": len(lista) - directos}
    # O do CardTrader foi VALIDADO a 2026-09-25 (o id sozinho responde 200 e o
    # site acrescenta o slug); o do Cardmarket não pôde ser (403). Ver
    # `mercados.py` — a página escreve esta diferença.
    out["cardmarket"]["validado"] = False
    out["cardtrader"]["validado"] = True
    return out


def payload(con: sqlite3.Connection, cfg: dict | None = None,
            editable: bool = True) -> dict:
    cfg = cfg or config.load()
    op = opcoes(cfg)
    lista = itens(con, cfg)
    # O PRODUTO SELADO e os ACESSÓRIOS contam-se à parte, e é essa a decisão
    # de 2026-09-25: um binder não é um display, e metê-lo no «o que há» do
    # selado mudava um número que ele já conhece. Duas listas, dois totais,
    # dois valores — e nenhum dos dois se soma ao valor da Coleção.
    selados = [x for x in lista if not x["acessorio"]]
    acess = [x for x in lista if x["acessorio"]]
    dados = carregar()
    return {
        "editable": editable,
        "generated_at": _now(),
        "catalogo_em": dados.get("generated_at"),
        "fonte": "CardTrader (api.cardtrader.com/api/v2)",
        "items": lista,
        "sets": por_edicao(selados, cfg),
        "totals": contar(selados),
        "links": contar_links(selados),
        "acessorios": {
            "sets": por_edicao(acess, cfg),
            "totals": contar(acess),
            "links": contar_links(acess),
            "categorias": [{"id": c, "nome": _nome_da_categoria(c)}
                           for c in op["acessorios"]],
        },
        "tipos": [t for t in TIPOS if any(x["tipo"] == t["id"] for x in lista)],
        "scope": {
            "categorias": [{"id": c, "nome": _nome_da_categoria(c)}
                           for c in op["categorias"]],
            "acessorios": op["acessorios"],
            "juntar_duplicados": op["juntar_duplicados"],
            "juntos": sum(len(x["duplicados"]) for x in lista),
            "fora": fora(cfg),
            "por_sair": op["por_sair"],
            "datas": op["datas_por_edicao"],
        },
    }


# ---------------------------------------------------------------------------
# `riftvault selado --sync`: ir buscar a lista ao CardTrader
# ---------------------------------------------------------------------------

# A regra do preço de um produto selado, e é DIFERENTE da das cartas.
#
# Medido a 2026-09-25 contra a API real (4 blueprints, 106 ofertas): uma oferta
# de selado **não tem `condition`** (vem `None` em todas — não há «Near Mint»
# de um display) e traz duas propriedades próprias:
#
#     properties_hash.sealed             (bool)  <- ainda está por abrir
#     properties_hash.riftbound_language ('en', 'zh-CN', 'fr', 'kr')
#
# Por isso: fora o graded, o vendedor de férias e o que não esteja em EUR;
# **`sealed: false` não conta** (é um produto já aberto, e aí o preço é outra
# coisa); e a língua segue o `precos.linguas` de sempre, porque na mesma caixa
# o chinês e o inglês têm preços muito diferentes — no *Origins Booster Box*
# eram 6 ofertas `zh-CN`, 3 `fr` e 51 `en`.
def _oferta_util(p: dict, linguas: frozenset[str]) -> bool:
    h = p.get("properties_hash") or {}
    return (not p.get("graded")
            and not p.get("on_vacation")
            and h.get("sealed") is not False
            and h.get("riftbound_language") in linguas
            and p.get("price_currency") == "EUR"
            and (p.get("price_cents") or 0) > 0)


def preco_do_selado(products: list[dict], linguas: frozenset[str]) -> dict:
    uteis = [p for p in products if _oferta_util(p, linguas)]
    if not uteis:
        return {"cents": None, "n_listings": 0, "n_sellers": 0, "n_copies": 0}
    vendedores = {(p.get("user") or {}).get("id") for p in uteis}
    vendedores.discard(None)
    return {"cents": min(p["price_cents"] for p in uteis),
            "n_listings": len(uteis), "n_sellers": len(vendedores),
            "n_copies": sum(int(p.get("quantity") or 1) for p in uteis)}


def sincronizar(ct=None, cfg: dict | None = None, log=print,
                com_precos: bool = True, intervalo: float = 1.0) -> dict:
    """Vai ao CardTrader buscar TODOS os blueprints que não são singles, por
    expansão do Riftbound, e escreve o `data/selado_catalogo.json`.

    **Guarda tudo o que não é single**, esteja ou não nas
    `selado.categorias` — assim mudar a lista do config não obriga a voltar à
    rede. Os PREÇOS é que só se vão buscar aos que estão em âmbito (um pedido
    por produto, resposta pequena); um produto que entre no âmbito depois fica
    sem preço até ao `--sync` seguinte, e a página diz quantos são.

    O ritmo é o do `riftvault prices`: um pedido de cada vez, `intervalo`
    segundos entre dois. É um comando À MÃO — não entra em tarefa nenhuma.
    """
    from .prices import CardTrader, RIFTBOUND_GAME_ID, SINGLES_CATEGORY, linguas

    cfg = cfg or config.load()
    op = opcoes(cfg)
    ct = ct or CardTrader()
    pedidos = 0

    cats_api = ct.get("/categories")
    cats_api = cats_api.get("array", cats_api) if isinstance(cats_api, dict) else cats_api
    pedidos += 1
    categorias = {str(c["id"]): c.get("name") for c in cats_api
                  if c.get("game_id") == RIFTBOUND_GAME_ID}
    log(f"  {len(categorias)} categorias do Riftbound no CardTrader")
    time.sleep(intervalo)

    exps = ct.expansions()
    pedidos += 1
    log(f"  {len(exps)} expansões")

    produtos: list[dict] = []
    expansoes: list[dict] = []
    for e in sorted(exps, key=lambda x: x["id"]):
        code = (e.get("code") or "").upper()
        nome_e = e.get("name_en") or e.get("name") or code
        expansoes.append({"id": e["id"], "code": code, "name": nome_e})
        time.sleep(intervalo)
        bps = ct.blueprints(e["id"])
        pedidos += 1
        nao_singles = [b for b in bps if b.get("category_id") != SINGLES_CATEGORY]
        for b in nao_singles:
            produtos.append({
                "blueprint_id": b["id"],
                "nome": b.get("name") or "",
                "versao": b.get("version") or "",
                "categoria_id": b.get("category_id"),
                "edicao": code, "edicao_nome": nome_e,
                "img": b.get("image_url"),
                "cardmarket_id": (b.get("card_market_ids") or [None])[0],
                "tcg_player_id": b.get("tcg_player_id"),
            })
        log(f"  {code or e['id']}: {len(bps)} blueprints, "
            f"{len(nao_singles)} não singles")

    precos: dict[str, dict] = {}
    if com_precos:
        ling = linguas(cfg)
        alvo = [p for p in produtos if p["categoria_id"] in set(op["categorias"])]
        hoje = date.today().isoformat()
        log(f"  preços de {len(alvo)} produtos em âmbito "
            f"(língua: {', '.join(sorted(ling))})…")
        for p in alvo:
            time.sleep(intervalo)
            d = ct.get("/marketplace/products", {"blueprint_id": p["blueprint_id"]})
            pedidos += 1
            bid = p["blueprint_id"]
            o = preco_do_selado(d.get(str(bid)) or d.get(bid) or [], ling)
            precos[str(bid)] = {**o, "currency": "EUR", "day": hoje}

    saida = {
        "generated_at": _now(),
        "fonte": "cardtrader",
        "game_id": RIFTBOUND_GAME_ID,
        "singles_category": SINGLES_CATEGORY,
        "pedidos": pedidos,
        "categorias": categorias,
        "expansoes": expansoes,
        "produtos": produtos,
        "precos": precos,
    }
    config.SELADO_PATH.parent.mkdir(parents=True, exist_ok=True)
    config.SELADO_PATH.write_text(
        json.dumps(saida, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return {"produtos": len(produtos), "precos": len(precos), "pedidos": pedidos,
            "caminho": str(config.SELADO_PATH),
            "sem_preco": sum(1 for v in precos.values() if v["cents"] is None)}


# ---------------------------------------------------------------------------
# Texto, para o CLI
# ---------------------------------------------------------------------------


def eur(cents: int | None) -> str:
    return "—" if cents is None else f"{cents / 100:.2f} €"


def _linhas_dos_grupos(sets: list[dict]) -> list[str]:
    linhas: list[str] = []
    for g in sets:
        gt = g["totals"]
        linhas.append("")
        linhas.append(f"-- {g['set']} {g['label']} — {gt['tenho']}/{gt['saiu']}"
                      + (f" (+{gt['por_sair']} por sair)" if gt["por_sair"] else ""))
        for x in g["items"]:
            marca = "x" if x["qty"] else ("." if x["por_sair"] else " ")
            linhas.append(
                f"  [{marca}] {x['qty']:>2}  {x['tipo_label']:<16} "
                f"{x['nome']}{(' · ' + x['versao']) if x['versao'] else ''}"
                f"  {eur(x['preco_cents'])}"
                f"{'  (por sair' + (' ' + x['data'] if x['data'] else '') + ')' if x['por_sair'] else ''}")
            if x.get("conteudo"):
                linhas.append(f"         dentro: {x['conteudo']}")
            if x.get("nota"):
                linhas.append(f"         nota: {x['nota']}")
            if x.get("duplicados"):
                linhas.append("         junta o blueprint "
                              + ", ".join(str(d["blueprint_id"]) for d in x["duplicados"])
                              + " do CardTrader (o mesmo produto)")
    return linhas


def texto(p: dict) -> str:
    t = p["totals"]
    linhas = [
        f"Produto selado: HÁ {t['ha']}  ·  TENHO {t['tenho']}  ·  NÃO TENHO "
        f"{t['falta']}  ·  por sair {t['por_sair']}",
        f"  {t['copias']} unidades · valor do selado {eur(t['valor_cents'])} "
        f"(à parte do valor da Coleção)",
    ]
    if t["sem_preco"]:
        linhas.append(f"  {t['sem_preco']} sem preço no CardTrader")
    linhas += _linhas_dos_grupos(p["sets"])
    ac = p.get("acessorios") or {}
    at = ac.get("totals") or {}
    if at.get("ha"):
        linhas.append("")
        linhas.append(f"== ACESSÓRIOS (secção à parte, NÃO contam para o produto "
                      f"selado): HÁ {at['ha']}  ·  TENHO {at['tenho']}  ·  NÃO TENHO "
                      f"{at['falta']}  ·  valor {eur(at['valor_cents'])}")
        linhas += _linhas_dos_grupos(ac.get("sets") or [])
    f = p["scope"]["fora"]
    if f:
        linhas.append("")
        linhas.append("Fora deste separador (não são produto selado nem acessório "
                      "de coleção): " + ", ".join(f"{x['n']} {x['categoria']}" for x in f))
    return "\n".join(linhas)

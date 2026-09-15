"""O separador «Quanto custa»: a tabela de preços do jogo, por edição.

André, 2026-09-15 (à tarde): *"o separador quanto custa **nao e para ter as
faltas!** e para passar a ter o top 5 comum mais cara, por cada set / o top 5
incomum mais cara por cada set / o top5 rara mais cara por cada set / o top5
mitica mais cara por cada set"*. E antes: *"apenas cartas versao ingles"*.

NÃO É UM PLANO DE COMPRAS. Até esta ordem o separador mostrava o que FALTAVA ao
master set, arrumado por raridade e preço — o entendimento errado. Aqui entram
**todas as cartas da edição, tenha ele ou não tenha**: uma carta de que ele já
tem as três cópias continua a ser das mais caras da edição e aparece. As
faltas continuam a viver onde são precisas — a wantlist do fim de cada edição
da Coleção (`a_subir.master_faltas`/`wantlist`) e as listas dos decks
(`faltas.py`) — e deixaram de ter separador próprio.

O QUE ENTRA
    A SEQUÊNCIA da edição — o bloco `master` da grelha (`metrics.e_master`), o
    mesmo que conta para a percentagem. Ele tirou as artes alternativas pelo
    nome (*"AltArt nao precisa fazer isto"*); as sobrenumeradas e as promos
    são, nas palavras dele de 2026-09-14, a mesma categoria (*"Alt Art,
    overnumbered, etc etc é puramente coleção"*) e saem pela mesma razão. Não
    é indiferente: no UNL e no VEN as sobrenumeradas têm raridade de jogo no
    catálogo (os Poros `UNL-220..225` são «comuns» a 100–285 €; as `VEN-189`
    Rogue Assassin e companhia são «raras» a 190–400 €) e com elas dentro os
    blocos das comuns e das raras dessas duas edições eram SÓ reimpressões
    de topo, sem uma carta da sequência à vista. No OGN e no SFD as mesmas
    reimpressões têm raridade `showcase` e nem cabiam nos quatro blocos —
    incluí-las era tratar as duas metades da mesma classe de maneira
    diferente. `quanto_custa.so_sequencia: false` mete a coleção extra (menos
    as artes alternativas) na tabela, se ele quiser ver os Poros aqui; a
    linha diz o bloco quando não é a sequência.

    Tokens, signatures e runas sem numeração continuam escondidos, como em
    todo o lado (`metrics.e_colecao`).

AS QUATRO RARIDADES
    Comum, incomum, rara e «mítica», por esta ordem — a dele. No catálogo da
    RiftScribe a raridade de topo chama-se `epic`; não há «mythic». A página
    escreve «míticas», mapeado a `epic` (`RARIDADES`/`ROTULOS`). A quinta
    raridade do catálogo, `showcase`, não é uma raridade de jogo — é o
    tratamento das reimpressões de topo do OGN e do SFD — e não cabe em nenhum
    dos quatro blocos: fica de fora e o rodapé diz quantas.

O TOPO
    `quanto_custa.top_por_raridade` (5) é o corte, por raridade e por edição.
    Nunca escrito no código. Ordem: preço unitário, do mais caro para o mais
    barato; desempate pelo número de coleção.

QUANTAS TEM
    Cada linha leva `have`/`target` — as cópias na Coleção (`locais.na_colecao`,
    a mesma conta do crachá da grelha) e o alvo. É informação, não filtro.

A LÍNGUA
    Os preços vêm do `catalog.price_latest`, que o `prices.sync_prices` só
    preenche com ofertas nas línguas de `precos.linguas` (`["en"]`). Não há
    segunda filtragem aqui: a RiftScribe não tem língua por impressão, e o
    filtro certo é na recolha, onde a língua existe.

Configura-se no `riftvault_config.json`, bloco "quanto_custa".
"""

from __future__ import annotations

import sqlite3

from . import config, locais, metrics

DEFAULTS: dict = {
    # As edições SEM botão. O OGS (Proving Grounds) fica de fora a pedido dele
    # (2026-09-15, de manhã: "para cada set (menos proving grounds) um botão"),
    # de quando isto eram faltas — agora que é uma tabela de preços a pergunta
    # está em aberto, e é dele. As outras nascem do catálogo.
    "sem_edicoes": ["OGS"],
    # Quantas se mostram por raridade, em cada edição.
    "top_por_raridade": 5,
    # Só a sequência da edição (o bloco `master`). A `false` entra também a
    # coleção extra menos as artes alternativas — as sobrenumeradas (os Poros
    # do UNL) e as promos. Ver o topo do ficheiro.
    "so_sequencia": True,
}

# Da mais comum para a mais rara — a ordem da frase dele. A quinta raridade do
# catálogo (`showcase`) não está aqui de propósito: ver o topo do ficheiro.
RARIDADES = ("common", "uncommon", "rare", "epic")

# A palavra dele para cada uma. «Mítica» é o `epic` da RiftScribe.
ROTULOS = {"common": "comuns", "uncommon": "incomuns", "rare": "raras",
           "epic": "míticas"}


def opcoes(cfg: dict | None = None) -> dict:
    cfg = cfg or config.load()
    bruto = cfg.get("quanto_custa") or {}
    return {**DEFAULTS, **{k: v for k, v in bruto.items() if not k.startswith("_")}}


def top(cfg: dict | None = None) -> int:
    """O corte por raridade. `0` mostra tudo; negativo rebenta."""
    n = opcoes(cfg).get("top_por_raridade")
    n = int(n) if n else 0
    if n < 0:
        raise ValueError(f"quanto_custa.top_por_raridade não pode ser negativo: {n}")
    return n


def edicoes(con: sqlite3.Connection, cfg: dict | None = None) -> dict:
    """As edições com botão, pela ordem dos separadores, e as que ficam sem ele.

    Lê o CATÁLOGO, não uma lista escrita à mão: uma edição nova ganha botão
    sozinha. As siglas comparam-se em maiúsculas para `ogs` valer `OGS`.
    """
    sem = {str(s).upper() for s in opcoes(cfg)["sem_edicoes"]}
    todas = [r[0] for r in con.execute("SELECT DISTINCT set_id FROM catalog.printings")]
    todas.sort(key=lambda s: (config.set_order(s), s))
    return {
        "sets": [{"set": s, "name": config.set_name(s)} for s in todas if s not in sem],
        "sem_edicoes": [s for s in todas if s in sem],
    }


def ambito(con: sqlite3.Connection, cfg: dict | None = None) -> tuple[list[dict], dict]:
    """As impressões da tabela, com preço e cópias, e o resumo do que ficou fora.

    Devolve `(itens, fora)`: `itens` são todas as impressões que entram (sem
    corte), `fora` conta as escondidas, as artes alternativas, o resto da
    coleção extra (com `so_sequencia`) e as de raridade fora das quatro —
    para a página dizer o que não está lá.
    """
    cfg = cfg or config.load()
    so_sequencia = bool(opcoes(cfg).get("so_sequencia", True))
    precos = {r["printing_id"]: r["price_cents"] for r in con.execute(
        "SELECT printing_id, price_cents FROM catalog.price_latest "
        "WHERE price_cents IS NOT NULL")}
    tenho = locais.na_colecao(con)
    itens: list[dict] = []
    fora = {"alt_art": 0, "escondidas": 0, "colecao_extra": {},
            "outras_raridades": {}, "sem_preco": 0, "so_sequencia": so_sequencia}
    for r in con.execute(
        "SELECT printing_id, set_id, collector_number, public_code, name, "
        "       variant_kind, variant_label, rarity, type, is_token "
        "FROM catalog.printings"
    ):
        if not metrics.e_colecao(r, cfg):
            fora["escondidas"] += 1
            continue
        if r["variant_kind"] == "alt_art":
            fora["alt_art"] += 1
            continue
        bloco = metrics.bloco(r, cfg)
        if so_sequencia and bloco != metrics.BLOCO_MASTER:
            # As sobrenumeradas e as promos, pelo nome do bloco da grelha.
            nome = metrics.BLOCO_CURTO.get(bloco, bloco)
            fora["colecao_extra"][nome] = fora["colecao_extra"].get(nome, 0) + 1
            continue
        rar = r["rarity"] or "?"
        if rar not in RARIDADES:
            fora["outras_raridades"][rar] = fora["outras_raridades"].get(rar, 0) + 1
            continue
        preco = precos.get(r["printing_id"])
        if preco is None:
            # Sem oferta não há preço para ordenar: não entra, e diz-se.
            fora["sem_preco"] += 1
            continue
        itens.append({
            "printing_id": r["printing_id"],
            "name": r["name"],
            "code": r["public_code"],
            "set": r["set_id"],
            "cn": r["collector_number"],
            "rarity": rar,
            "kind": r["variant_kind"],
            "label": r["variant_label"],
            # O bloco da grelha, só quando não é a sequência — é o que diz
            # «sobrenumerada» ou «promo» ao lado do nome.
            "block": None if bloco == metrics.BLOCO_MASTER else bloco,
            "block_label": None if bloco == metrics.BLOCO_MASTER
            else metrics.BLOCO_CURTO.get(bloco, bloco),
            "price": preco,
            "have": tenho.get(r["printing_id"], 0),
            "target": metrics.alvo(r, cfg),
        })
    return itens, fora


def tabela(con: sqlite3.Connection, cfg: dict | None = None) -> dict:
    """O separador inteiro: por edição com botão, por raridade, as `top` mais caras.

    Cada raridade leva `items` (as que se vêem), `n` (quantas há com preço
    nessa edição e raridade) e `hidden` (quantas o corte deixou de fora). Não
    há totais nem subtotais: não é uma lista de compra.
    """
    cfg = cfg or config.load()
    n_top = top(cfg)
    ed = edicoes(con, cfg)
    itens, fora = ambito(con, cfg)

    por_set: dict[str, dict[str, list[dict]]] = {}
    for x in itens:
        por_set.setdefault(x["set"], {}).setdefault(x["rarity"], []).append(x)

    sets = []
    for b in ed["sets"]:
        raridades = []
        for rar in RARIDADES:
            linhas = sorted(por_set.get(b["set"], {}).get(rar, []),
                            key=lambda x: (-x["price"], x["cn"], x["code"]))
            vistas = linhas[:n_top] if n_top else linhas
            raridades.append({
                "rarity": rar, "label": ROTULOS[rar],
                "n": len(linhas), "hidden": len(linhas) - len(vistas),
                "items": vistas,
            })
        sets.append({**b, "rarities": raridades,
                     "printings": sum(g["n"] for g in raridades)})

    return {
        "top": n_top,
        "rarity_order": list(RARIDADES),
        "labels": dict(ROTULOS),
        "sets": sets,
        "sem_edicoes": ed["sem_edicoes"],
        "scope": {
            "printings": len(itens),
            **fora,
        },
    }

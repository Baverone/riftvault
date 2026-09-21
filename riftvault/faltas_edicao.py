"""O separador «Faltas»: o que falta, por edição, em quatro blocos — cada um
com a sua wantlist.

André, 2026-09-15 (fim da tarde): *"quero agora fazer uma seccao de faltas /
quero as faltas por edicao e dividido em 3 partes / Masterset / Alt Art /
OverNumbered"*. E 2026-09-19: *"as wantlist das edicoes, quero 4 wantlist: 1
so para o master set, 1 so para as Alt.Art, 1 so para as Overnumbered, uma so
para as Promo (no caso SP)"* — as promos ganharam o quarto bloco, e cada bloco
a sua wantlist do Cardmarket (`wantlist`), separada das outras.

NÃO É O SEPARADOR QUE SE APAGOU HORAS ANTES. O antigo separador (o id
`faltas`, que ficou para o `faltas.py` dos decks) tinha as faltas do master
set arrumadas por raridade e ele mandou-as sair de lá porque passou a ser a
tabela de preços — apagada por sua vez a 2026-09-19 (ver o CLAUDE.md). Isto é
uma secção PRÓPRIA, com outra organização: por edição, e dentro de cada
edição os blocos pela ordem da Coleção.

NÃO É UM CÁLCULO NOVO. A carência é a mesma da wantlist do fim de cada edição
da Coleção (`a_subir.master_faltas`): o mesmo âmbito (`a_subir.masterset`),
os mesmos alvos (`metrics.alvo`), as mesmas cópias (`locais.na_colecao`, só o
que está nos binders de Coleção) e o mesmo pendente (`pending.open_qty`). O
que muda é a arrumação — e que aqui a coleção extra também se VÊ.

OS QUATRO BLOCOS
    `master`       — a sequência numerada da edição (`metrics.BLOCO_MASTER`),
                     alvo do tipo: Unit/Spell/Gear 3, Legend e Battlefield 1,
                     runas numeradas 3 (2026-09-15).
    `alt_art`      — as artes alternativas, pelo `variant_kind`. Inclui as
                     seis artes alternativas das runas do OGN, que a grelha
                     da Coleção arruma no bloco «runas especiais»: ele chamou
                     ao bloco «Alt Art», e uma `OGN-007a` é uma arte
                     alternativa. (Hoje estão retiradas de tudo, 2026-09-17,
                     e nem chegam ao âmbito.) Alvo de playset (2026-09-18).
    `overnumbered` — as sobrenumeradas (`metrics.BLOCO_OVER`), alvo 1
                     (`master_set.um_de_cada`, 2026-09-15).
    `special`      — as promos `VEN-SP` (2026-09-19), alvo 1 (`um_de_cada`,
                     desde o mesmo dia). De 2026-09-15 a 2026-09-19 ficaram
                     de fora do separador porque ele tinha nomeado três
                     blocos; a 19/09 nomeou-as.

    A ORDEM é a da Coleção — `master_set.ordem_dos_blocos`, lida por
    `metrics.ordem_dos_blocos` e cortada aos quatro ids de cima (`blocos`).
    Até 2026-09-19 este separador tinha uma ordem própria (master set, Alt
    Art, OverNumbered, a de 15/09); passou a ler a mesma lista que a grelha
    para ele mudar num sítio e mudar nos dois. Na mensagem de 19/09 ele
    enumerou «master set, Alt.Art, Overnumbered, Promo» — é a ordem de quem
    enumera, não um pedido de ordem diferente (fica no relatório).

    Tokens, signatures e runas sem numeração continuam escondidos
    (`metrics.e_colecao`), como em todo o lado; o que a página da Coleção
    mostre e não caiba em nenhum dos quatro (hoje nada) vai em `scope.fora`.

VER NÃO É COMPRAR — MAS CADA BLOCO TEM A SUA WANTLIST
    SÓ o master set entra nas listas de compra GERAIS — a wantlist do fim de
    cada edição da Coleção, a «Wantlist — tudo», o «A subir». É a frase dele
    de 15/09: *"sobrenumeradas não entram na wantlist, nem na % de coleção
    completa; apenas pedi para ser feito track de playset para eu saber
    exatamente quantas tenho"*. Cada bloco leva `in_lists`, lido do MESMO
    botão que manda nessas listas (`listas_de_compra.so_master_set`, via
    `a_subir.blocos_fora`).

    O que 19/09 acrescenta é OUTRA coisa: cada bloco tem a SUA wantlist do
    Cardmarket, própria do bloco, separada das outras — os itens já levam os
    campos do gerador (`market_name`, `v`, …) e o `wantlist()` escreve-a pelo
    `cardmarket.gerar`, o mesmo das outras listas. A wantlist da Alt Art
    existe porque ele a pediu; a «Wantlist — tudo» da Coleção NÃO cresce por
    isso (há teste) — acompanhar continua a não ser querer comprar em bloco.

O QUE VEM A CAMINHO CONTA
    Uma cópia encomendada e ainda não recebida (`pending`) não é falta por
    comprar. Cada item leva `have` (na Coleção), `pending` (a caminho, cortado
    ao que falta) e `missing` = o que ainda há a COMPRAR, `alvo − have −
    pending`. Uma carta toda coberta pelo pendente continua na lista, marcada
    — para ele ver que está a chegar —, mas com `missing` 0, e não soma aos
    totais de compra. Os totais de cada bloco (`copies`, `cents`) são só o que
    há a comprar; o pendente vai à parte (`pending_copies`).

    Por construção, o bloco `master` de cada edição pede EXACTAMENTE as cópias
    da wantlist dessa edição (`a_subir.master_faltas`) — há teste.
"""

from __future__ import annotations

import sqlite3

from . import a_subir, cardmarket, config, locais, metrics, pending

# O CATÁLOGO dos blocos deste separador, com o rótulo que ele lhes deu. A
# ordem NÃO é esta: é `blocos(cfg)`, que lê a lista partilhada com a grelha.
# O id da alt art é o `variant_kind`, porque «Alt Art» aqui inclui as artes
# alternativas das runas (ver o topo do ficheiro); os outros são os da grelha.
BLOCO_LABEL = {
    metrics.BLOCO_MASTER: "Master set",
    "alt_art": "Alt Art",
    metrics.BLOCO_OVER: "OverNumbered",
    "special": "Promos",
}
BLOCO_IDS = list(BLOCO_LABEL)


def blocos(cfg: dict | None = None) -> list[tuple[str, str]]:
    """Os quatro blocos, `(id, rótulo)`, pela ordem da Coleção.

    `metrics.ordem_dos_blocos` devolve TODOS os blocos da grelha; ficam os que
    este separador tem. O bloco «runas especiais» da grelha não existe aqui
    — as artes alternativas das runas são «Alt Art» —, por isso sai da lista
    sem deixar buraco.
    """
    ordem = [b for b in metrics.ordem_dos_blocos(cfg) if b in BLOCO_LABEL]
    return [(b, BLOCO_LABEL[b]) for b in ordem]


def bloco_das_faltas(printing, cfg: dict | None = None) -> str | None:
    """Em qual dos quatro blocos cai esta impressão; `None` se em nenhum.

    A arte alternativa decide-se pelo `variant_kind` — antes do bloco da
    grelha, que manda as das runas para «runas especiais». O resto é o bloco
    da grelha: `master`, `overnumbered` ou `special` (as promos, 2026-09-19).
    O que mais houver (`rune_promo`, uma variante nova) devolve `None` e a
    página diz que ficou de fora.
    """
    if printing["variant_kind"] == "alt_art":
        return "alt_art"
    b = metrics.bloco(printing, cfg)
    return b if b in BLOCO_LABEL else None


def em_falta(con: sqlite3.Connection, escopo: dict[str, dict]) -> dict[str, dict]:
    """Do âmbito, o que ele ainda não tem na Coleção — com o pendente à parte.

    O gémeo do `a_subir.em_falta`, com uma diferença: ali o pendente soma-se
    ao que ele tem e a carta desaparece; aqui fica visível, marcada. A conta
    do que há a COMPRAR é a mesma (`alvo − cópias − a caminho`), e é isso que
    o teste contra a wantlist fixa.
    """
    tenho = locais.na_colecao(con)
    a_caminho = pending.open_qty(con)
    out: dict[str, dict] = {}
    for pid, info in escopo.items():
        have = tenho.get(pid, 0)
        curto = info["target"] - have
        if curto <= 0:
            continue
        pend = min(a_caminho.get(pid, 0), curto)
        out[pid] = {**info, "have": have, "pending": pend,
                    "missing": curto - pend, "short": curto}
    return out


def _item(pid: str, info: dict, preco: int | None, mkt: dict) -> dict:
    total = (preco or 0) * info["missing"]
    return {
        "printing_id": pid, "name": info["name"],
        "code": info["public_code"], "set": info["set_id"],
        "cn": info["collector_number"],
        "kind": info["variant_kind"], "label": info["variant_label"],
        "rarity": info["base_rarity"] or "?",
        "landscape": (info["orientation"] or "").lower() == "landscape",
        "img": f"img/{pid}.webp",
        "cdn": info["image_medium"] or info["image_large"] or info["image_url"],
        "have": info["have"], "target": info["target"],
        "pending": info["pending"],
        # `missing` é o que há a COMPRAR; `short` é o que falta na caixa
        # (com o pendente ainda por chegar).
        "missing": info["missing"], "short": info["short"],
        "price": preco, "total": total,
        # Os campos do gerador do Cardmarket, os mesmos nomes da wantlist —
        # só o bloco `master` os usa, mas o item é um só.
        "market_name": mkt.get("name") if mkt.get("name") != info["name"] else None,
        "market_set": mkt.get("set"),
        "v": mkt.get("v"), "n_versions": mkt.get("n", 1),
        "foil_only": bool(mkt.get("foil_only")),
    }


def _soma(itens: list[dict]) -> dict:
    return {
        # Só o que há a comprar. Uma carta coberta pelo pendente não conta
        # aqui — está na lista para se ver que vem a caminho.
        "cards": sum(1 for x in itens if x["missing"] > 0),
        "copies": sum(x["missing"] for x in itens),
        "cents": sum(x["total"] for x in itens),
        "no_price": sum(1 for x in itens if x["missing"] > 0 and x["price"] is None),
        "pending_cards": sum(1 for x in itens if x["pending"] > 0),
        "pending_copies": sum(x["pending"] for x in itens),
        # Quantas impressões faltam na caixa, pendente incluído.
        "short_cards": len(itens),
    }


def payload(con: sqlite3.Connection, cfg: dict | None = None) -> dict:
    """O separador inteiro: por edição, os quatro blocos, cada um com o que falta.

    Todas as edições do catálogo, pela ordem dos separadores — o OGS entra: o
    «menos proving grounds» de 2026-09-15 foi pedido para a tabela de preços
    (apagada a 2026-09-19) e vale hoje só no «A mais» (`a_mais.sem_edicoes`).
    Cada edição leva sempre os quatro blocos, vazios ou não, e a soma dos
    quatro.
    """
    cfg = cfg or config.load()
    o = a_subir.opcoes(cfg)
    escopo = a_subir.masterset(con, cfg)
    # As exclusões da sequência (signatures, showcases — hoje tiram zero,
    # porque já estão escondidas), para o bloco `master` ser o MESMO da
    # wantlist. Sem `blocos`: a coleção extra é para se ver aqui, tire-a ou
    # não das listas de compra.
    escopo, _ = a_subir.excluir(escopo, {**o["excluir"], "blocos": []}, so_master=False)
    # O botão das listas de compra gerais, lido do mesmo sítio que as listas
    # o lêem. O master set entra sempre.
    fora_das_listas = set(a_subir.blocos_fora(o["excluir"], o["so_master_set"]))
    in_lists = {b: b == metrics.BLOCO_MASTER or b not in fora_das_listas
                for b in BLOCO_IDS}
    ordem = blocos(cfg)

    falta = em_falta(con, escopo)
    mercado = cardmarket.versoes(con)
    precos = metrics.prices_map(con)

    sets_ids = [r[0] for r in con.execute("SELECT DISTINCT set_id FROM catalog.printings")]
    sets_ids.sort(key=lambda s: (config.set_order(s), s))
    por_set: dict[str, dict[str, list[dict]]] = {s: {b: [] for b in BLOCO_IDS} for s in sets_ids}
    ambito: dict[str, dict[str, int]] = {s: {b: 0 for b in BLOCO_IDS} for s in sets_ids}
    fora: dict[str, int] = {}
    for pid, info in escopo.items():
        b = bloco_das_faltas(info, cfg)
        if b is None:
            nome = metrics.BLOCO_CURTO.get(info["block"], info["block"])
            fora[nome] = fora.get(nome, 0) + 1
            continue
        ambito[info["set_id"]][b] += 1
        if pid in falta:
            por_set[info["set_id"]][b].append(
                _item(pid, falta[pid], precos.get(pid), mercado.get(pid) or {}))

    sets = []
    for s in sets_ids:
        grupos = []
        for b, label in ordem:
            itens = sorted(por_set[s][b], key=lambda x: (x["cn"], x["code"]))
            grupos.append({
                "id": b, "label": label,
                # «playset» / «1 de cada», do mesmo config que dá o alvo.
                "target_label": metrics.alvo_do_bloco(b, cfg),
                "in_lists": in_lists[b],
                "scope": ambito[s][b],
                **_soma(itens),
                "items": itens,
                # A wantlist DESTE bloco, desta edição (2026-09-19): o texto
                # é o do `cardmarket.gerar`, o mesmo gerador das outras
                # listas; o `app.js` escreve o mesmo a partir dos `items`
                # (`cmLinha`) e há teste que compara os dois.
                "wantlist": _wantlist_do_bloco(itens),
            })
        todos = [x for g in grupos for x in g["items"]]
        sets.append({"set": s, "name": config.set_name(s),
                     # A soma dos quatro blocos — o que ele pediu no
                     # cabeçalho da edição — e, à parte, só o que entra nas
                     # listas de compra gerais.
                     **_soma(todos),
                     "lists": _soma([x for g in grupos if g["in_lists"] for x in g["items"]]),
                     "blocks": grupos})

    todos = [x for d in sets for g in d["blocks"] for x in g["items"]]
    nas_listas = [x for d in sets for g in d["blocks"] if g["in_lists"] for x in g["items"]]
    return {
        "blocks": [{"id": b, "label": label, "in_lists": in_lists[b]} for b, label in ordem],
        "so_master_set": bool(o["so_master_set"]),
        "rule": str(o["regra_falta"]),
        "totals": _soma(todos),
        # Só os blocos que entram nas listas de compra gerais: é este que bate
        # com a wantlist «tudo» da Coleção.
        "totals_lists": _soma(nas_listas),
        "sets": sets,
        "scope": {
            "printings": sum(ambito[s][b] for s in sets_ids for b in BLOCO_IDS),
            # O que está na página da Coleção mas não em nenhum dos quatro
            # blocos — hoje nada; uma variante nova cairia aqui. É o que a
            # página tem de dizer.
            "fora": fora,
        },
    }


def _wantlist_do_bloco(itens: list[dict]) -> dict:
    """O resumo da wantlist de um bloco: só o que há a COMPRAR (`missing > 0`).

    Uma carta toda coberta pelo pendente está na lista do bloco para se ver
    que vem a caminho, mas não vai para o Cardmarket — a wantlist da Coleção
    faz o mesmo. O texto não vai no payload (os `items` já lá estão e o
    cliente escreve-o); vai o que o cabeçalho diz.
    """
    w = cardmarket.gerar([x for x in itens if x["missing"] > 0])
    return {"lines": w["lines"], "copies": w["copies"], "cents": w["cents"],
            "foil": len(w["foil"])}


def wantlist(con: sqlite3.Connection, set_id: str, bloco: str,
             cfg: dict | None = None, com_codigo: bool = False) -> dict:
    """A wantlist de UM bloco de UMA edição, pronta a colar no Cardmarket.

    É a quarta pergunta da ordem de 2026-09-19 respondida em Python, para a
    CLI (`riftvault faltas --edicao OGN --bloco alt_art --cardmarket`) e para
    os testes. O bloco `master` dá exactamente o texto da wantlist dessa
    edição da Coleção (`a_subir.wantlist`) — há teste.
    """
    cfg = cfg or config.load()
    if bloco not in BLOCO_LABEL:
        raise ValueError(f"bloco desconhecido: {bloco!r}. Há: {', '.join(BLOCO_IDS)}")
    p = payload(con, cfg)
    d = next((s for s in p["sets"] if s["set"] == set_id), None)
    if d is None:
        raise ValueError(f"não há edição {set_id!r}")
    g = next(g for g in d["blocks"] if g["id"] == bloco)
    itens = [x for x in g["items"] if x["missing"] > 0]
    return {"set": set_id, "name": d["name"], "block": bloco, "label": g["label"],
            "in_lists": g["in_lists"], **cardmarket.gerar(itens, com_codigo),
            "items": itens}

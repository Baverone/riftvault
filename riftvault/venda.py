"""«Venda»: o que ele TEM e a sequência do master set não pede.

Palavras do André (2026-09-08): *"A Coleção é de master set. O resto
provavelmente vai para venda ou jogar nos decks seleccionados."*

Esta secção responde à segunda metade da frase. Pega no que ele tem e não
pertence à SEQUÊNCIA do master set (`metrics.bloco` != `master`) e parte em
duas:

  USADA NUM DECK   — a cópia está alocada a um deck da secção Decks. Fica.
  CANDIDATA A VENDA — nenhum deck a usa. É o que sobra.

O QUE A COLEÇÃO AINDA PEDE NÃO ENTRA (2026-09-08, tarde)
    Os blocos das runas especiais e das artes alternativas voltaram a contar,
    com alvo **1 de cada** — *"1 runa especial de cada para cada set; no fim 1
    alt art de cada"*. Por isso a venda passou a ser só o EXCEDENTE: uma alt
    art que ele tem uma vez é coleção, a sexta é venda. Os tokens, que
    continuam fora da coleção, sobram inteiros como antes.

    Era exatamente a tensão que estava anotada no CLAUDE.md ("a lista mostra a
    impressão inteira, não só o que passa do alvo"); a frase dele decidiu-a.

**Nada sai da base.** Isto é uma sugestão, não uma operação: não há botão de
vender, não se mexe no `copies` nem no `ops`. Ele copia a lista e decide.

QUEM DECIDE O QUE ESTÁ NUM DECK
    Três leituras, somadas: o `decks.printing_allocation` (o que está sleevado,
    lido dos locais), o `decks.binder_allocation` (o que os decks levam do
    binder Decks/Venda) e, desde 2026-09-11, o `decks.colecao_allocation` (o
    que levam da Coleção — *"se há na coleção o deck usa"*). As duas últimas
    escolhem **artes base primeiro**, de propósito, para as alternativas
    ficarem para venda; por isso uma arte alternativa só aparece alocada quando
    ele não tem cópias base que cheguem. É exatamente a resposta certa aqui:
    essa alt art está a ser jogada porque faz falta, e vendê-la partia o deck.

    «Usadas nos decks» é a SOMA do que os decks levam, não o máximo: dois decks
    a disputar a mesma cópia contam os dois, e a Coleção só sobra acima de
    `max(usadas, alvo)`.

    Uma impressão pode ficar meia e meia — 2 cópias num deck e 1 a mais. Nesse
    caso a linha aparece nas duas leituras e a quantidade a vender é só o
    excedente.

A LISTA É A DO CARDMARKET, com a ressalva óbvia: é o formato de *wantlist*
(`N Nome (V.n) (Edição)`), o mesmo do «A subir» e do «Master set», que é o que
ele pediu. **Não é o formato de importação de stock de vendedor** — esse não
foi validado e não se inventa aqui.
"""

from __future__ import annotations

import sqlite3

from . import cardmarket, config, decks, metrics


def excedente(con: sqlite3.Connection, cfg: dict | None = None,
              incluir_master: bool = False) -> list[dict]:
    """O que sobra, e DE ONDE (André, 2026-09-10).

    Desde que cada cópia tem um local, a venda tem duas origens e cada linha diz
    qual — *"venda = cópias no binder Decks/Venda que nenhum deck pede, mais o
    excedente da Coleção acima dos alvos, cada linha a dizer de onde vem"*:

      `from_binder`  — está no binder Decks/Venda e **nenhum deck a pede**. Ele
                       próprio a tirou da Coleção; se nenhum deck a quer, é
                       venda, seja qual for o bloco.
      `from_colecao` — está nos binders de coleção e passa do alvo
                       (`metrics.alvo`). É o excedente de 2026-09-08.

    **O que está DENTRO de um deck nunca aparece.** Não é candidata a nada: está
    sleevada e a jogar. Era o que o `max(usadas, alvo)` fazia por conta própria
    quando não havia locais; agora lê-se.

    `incluir_master=False` (omissão) tira a SEQUÊNCIA do master set **da origem
    Coleção**, que é o âmbito do `listar()` desde 2026-09-08: *"a sequência
    nunca entra na venda, por muitas cópias que ele tenha"*. A origem BINDER não
    tem esse corte, e de propósito: uma carta da sequência que ele tenha posto
    no binder Decks/Venda já não é coleção — foi ele que a tirou de lá.

    `incluir_master=True` traz a sequência da Coleção também — é o que a lista
    das comuns e incomuns precisa (André, 2026-09-10), porque as comuns vivem
    quase todas na sequência e uma quarta cópia de uma Unit de playset 3 não faz
    falta a ninguém. **Não é um critério novo de excedente**: é o mesmo, sem o
    corte de âmbito.
    """
    from . import locais

    cfg = cfg or config.load()

    try:
        alocacao = decks.printing_allocation(con)
        binder_usado = decks.binder_allocation(con)
        colecao_usada = decks.colecao_allocation(con)
    except sqlite3.OperationalError:
        alocacao, binder_usado, colecao_usada = {}, {}, {}   # sem tabelas de decks
    no_binder = locais.em(con, locais.BINDER)
    na_colecao = locais.na_colecao(con)
    mercado = cardmarket.versoes(con)
    precos = {r["printing_id"]: r["price_cents"] for r in con.execute(
        "SELECT printing_id, price_cents FROM catalog.price_latest "
        "WHERE price_cents IS NOT NULL")}

    itens: list[dict] = []
    for r in con.execute(
        "SELECT p.printing_id, p.set_id, p.collector_number, p.public_code, "
        "       p.name, p.variant_kind, p.variant_label, p.rarity, p.base_rarity, p.type, "
        "       p.is_token, p.orientation, p.api_sort, "
        "       p.image_medium, p.image_large, p.image_url, c.qty "
        "FROM copies c JOIN catalog.printings p ON p.printing_id = c.printing_id "
        "WHERE c.qty > 0 ORDER BY p.set_id, p.api_sort"
    ):
        pid = r["printing_id"]
        bloco = metrics.bloco(r, cfg)
        # Usada num deck = sleevada nele, ou a ser jogada a partir do binder
        # Decks/Venda ou da Coleção (2026-09-11: a Coleção monta decks). É a
        # SOMA do que os decks levam, não o máximo — dois decks a disputar a
        # mesma cópia contam os dois, senão vendia-se o que um deles usa.
        nos_decks = (alocacao.get(pid, []) + binder_usado.get(pid, [])
                     + colecao_usada.get(pid, []))
        usadas = sum(d["qty"] for d in nos_decks)

        # ORIGEM 1 — o binder Decks/Venda, menos o que os decks lhe pedem.
        do_binder = max(0, no_binder.get(pid, 0)
                        - sum(x["qty"] for x in binder_usado.get(pid, [])))

        # ORIGEM 2 — a Coleção, acima do alvo E do que os decks lhe usam:
        # `cópias − max(usadas nos decks, alvo)`. A mesma cópia serve a Coleção
        # e o deck, por isso é o máximo dos dois e não a soma. Zero nos blocos
        # que estão fora dela (tokens, signatures, sobrenumeradas, promos), que
        # a Coleção não pede; e zero na sequência quando o âmbito é o estreito
        # de 2026-09-08.
        alvo = metrics.alvo(r, cfg) if metrics.conta_bloco(bloco, cfg) else 0
        usadas_col = sum(x["qty"] for x in colecao_usada.get(pid, []))
        da_colecao = max(0, na_colecao.get(pid, 0) - max(usadas_col, alvo))
        if bloco == metrics.BLOCO_MASTER and not incluir_master:
            da_colecao = 0

        sobra = do_binder + da_colecao
        if sobra <= 0 and usadas <= 0:
            continue
        preco = precos.get(pid)
        mkt = mercado.get(r["printing_id"]) or {}
        itens.append({
            "printing_id": r["printing_id"],
            "name": r["name"], "code": r["public_code"],
            "set": r["set_id"], "set_name": config.set_name(r["set_id"]),
            "cn": r["collector_number"],
            "block": bloco,
            "target": alvo,
            "kind": r["variant_kind"], "label": r["variant_label"],
            "rarity": r["base_rarity"] or "?",
            # A raridade IMPRESSA, a par da raridade da base. As duas só
            # diferem nas seis runas de arte alternativa do OGN (base `common`,
            # impressa `showcase`), e o `comuns.py` exige as duas para nenhum
            # tratamento showcase entrar na lista das comuns.
            "printed_rarity": r["rarity"] or "?",
            "landscape": (r["orientation"] or "").lower() == "landscape",
            "img": f"img/{r['printing_id']}.webp",
            "cdn": r["image_medium"] or r["image_large"] or r["image_url"],
            "have": r["qty"],
            "in_decks": nos_decks, "used": usadas,
            # Quantas das usadas vêm da Coleção — o `listar` precisa disto para
            # não listar a sequência inteira como «dentro de um deck».
            "used_colecao": usadas_col,
            # DE ONDE vem cada cópia da linha (André, 2026-09-10). Somam o
            # `qty`; separam-se porque são duas decisões diferentes: tirar do
            # binder Decks/Venda é arrumação, tirar da Coleção é vender coleção.
            "from_binder": do_binder,
            "from_colecao": da_colecao,
            "in_colecao": na_colecao.get(pid, 0),
            "in_binder": no_binder.get(pid, 0),
            # `qty` é a quantidade DESTA linha: o que sobra depois dos decks.
            # É o que o gerador do Cardmarket lê (ver `cardmarket.linha`).
            "qty": sobra,
            "state": "deck" if usadas else "venda",
            "origem": ("binder" if do_binder and not da_colecao else
                       "colecao" if da_colecao and not do_binder else
                       "ambos" if sobra else "deck"),
            "price": preco,
            "total": (preco or 0) * sobra,
            "market_name": mkt.get("name") if mkt.get("name") != r["name"] else None,
            "market_set": mkt.get("set"),
            "v": mkt.get("v"), "n_versions": mkt.get("n", 1),
            "foil_only": bool(mkt.get("foil_only")),
        })

    return itens


def listar(con: sqlite3.Connection, cfg: dict | None = None) -> dict:
    """As impressões fora do master set que ele tem, e o que fazer com elas."""
    cfg = cfg or config.load()
    itens = excedente(con, cfg, incluir_master=False)

    # Só as que têm excedente é que se vendem; as que estão inteiras num deck
    # ficam à parte, para ele ver que não desapareceram — foram para um deck.
    # A sequência do master set só entra nessa lista se estiver sleevada ou no
    # binder Decks/Venda: desde 2026-09-11 os decks usam a Coleção inteira, e
    # listar aqui os 200 cartas da sequência que eles jogam era ruído — essa
    # informação vive na grelha da Coleção («Azir 3 · Kennen 2»).
    venda = [x for x in itens if x["qty"] > 0]
    nos_decks = [x for x in itens if x["used"] > 0
                 and (x["block"] != metrics.BLOCO_MASTER
                      or x["used"] > x["used_colecao"])]
    venda.sort(key=lambda x: (-(x["total"] or 0), x["set"], x["cn"]))

    blocos: dict[str, dict] = {}
    for x in venda:
        b = blocos.setdefault(x["block"], {"id": x["block"],
                                           "label": metrics.rotulo(x["block"], cfg),
                                           "printings": 0, "copies": 0, "cents": 0})
        b["printings"] += 1
        b["copies"] += x["qty"]
        b["cents"] += x["total"]

    # E o mesmo por ORIGEM, que é a leitura nova: quanto vem do binder
    # Decks/Venda (arrumação) e quanto vem da Coleção (vender coleção).
    origens = [
        {"id": "binder", "label": "Do binder Decks/Venda — nenhum deck as pede",
         "printings": sum(1 for x in venda if x["from_binder"]),
         "copies": sum(x["from_binder"] for x in venda),
         "cents": sum(x["from_binder"] * (x["price"] or 0) for x in venda)},
        {"id": "colecao", "label": "Da Coleção — acima do alvo",
         "printings": sum(1 for x in venda if x["from_colecao"]),
         "copies": sum(x["from_colecao"] for x in venda),
         "cents": sum(x["from_colecao"] * (x["price"] or 0) for x in venda)},
    ]

    return {
        "printings": len(venda),
        "copies": sum(x["qty"] for x in venda),
        "cents": sum(x["total"] for x in venda),
        "origins": [o for o in origens if o["copies"]],
        # Quantas não têm oferta no CardTrader: entram na lista, não no total.
        "no_price": sum(1 for x in venda if x["price"] is None),
        "in_decks": len(nos_decks),
        "in_decks_copies": sum(x["used"] for x in nos_decks),
        "blocks": [blocos[b] for b, _ in metrics.BLOCOS if b in blocos],
        "items": venda,
        "kept": sorted(nos_decks, key=lambda x: (x["set"], x["cn"])),
    }


def payload(con: sqlite3.Connection, editable: bool = True) -> dict:
    # A análise das comuns e incomuns (André, 2026-09-10) vai no MESMO ficheiro:
    # é a mesma página, e um segundo `api/*.json` obrigava a segunda visita ao
    # servidor para desenhar uma secção que está dobrada por omissão.
    from . import comuns
    from .metrics import _now
    return {"editable": editable, "generated_at": _now(), **listar(con),
            "comuns": comuns.analise(con)}

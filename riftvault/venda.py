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
    O `decks.printing_allocation` — a mesma função que põe "2× Ornn · 1 no
    binder" no tile da Coleção. Ela escolhe **artes base primeiro**, de
    propósito, para as alternativas ficarem no binder; por isso uma arte
    alternativa só aparece alocada quando ele não tem cópias base que cheguem.
    É exatamente a resposta certa aqui: essa alt art está a ser jogada porque
    faz falta, e vendê-la partia o deck.

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


def listar(con: sqlite3.Connection, cfg: dict | None = None) -> dict:
    """As impressões fora do master set que ele tem, e o que fazer com elas."""
    cfg = cfg or config.load()

    try:
        alocacao = decks.printing_allocation(con)
    except sqlite3.OperationalError:
        alocacao = {}               # base sem as tabelas dos decks ainda
    mercado = cardmarket.versoes(con)
    precos = {r["printing_id"]: r["price_cents"] for r in con.execute(
        "SELECT printing_id, price_cents FROM catalog.price_latest "
        "WHERE price_cents IS NOT NULL")}

    itens: list[dict] = []
    for r in con.execute(
        "SELECT p.printing_id, p.set_id, p.collector_number, p.public_code, "
        "       p.name, p.variant_kind, p.variant_label, p.base_rarity, p.type, "
        "       p.is_token, p.orientation, p.api_sort, "
        "       p.image_medium, p.image_large, p.image_url, c.qty "
        "FROM copies c JOIN catalog.printings p ON p.printing_id = c.printing_id "
        "WHERE c.qty > 0 ORDER BY p.set_id, p.api_sort"
    ):
        bloco = metrics.bloco(r, cfg)
        if bloco == metrics.BLOCO_MASTER:
            continue
        nos_decks = alocacao.get(r["printing_id"], [])
        usadas = sum(d["qty"] for d in nos_decks)
        # O que a coleção ainda pede fica: nos blocos que contam (runas
        # especiais e artes alternativas, 1 de cada desde 2026-09-08) só sobra
        # o que passa do alvo. Nos que não contam — os tokens — sobra tudo o
        # que os decks não usam, como antes. Era a tensão que o CLAUDE.md tinha
        # anotada, e a frase dele ("1 alt art de cada") resolveu-a: uma alt art
        # que ele tem uma vez é coleção, a sexta é venda.
        alvo = metrics.alvo(r, cfg) if metrics.conta_bloco(bloco, cfg) else 0
        sobra = r["qty"] - max(usadas, alvo)
        preco = precos.get(r["printing_id"])
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
            "landscape": (r["orientation"] or "").lower() == "landscape",
            "img": f"img/{r['printing_id']}.webp",
            "cdn": r["image_medium"] or r["image_large"] or r["image_url"],
            "have": r["qty"],
            "in_decks": nos_decks, "used": usadas,
            # `qty` é a quantidade DESTA linha: o que sobra depois dos decks.
            # É o que o gerador do Cardmarket lê (ver `cardmarket.linha`).
            "qty": sobra,
            "state": "deck" if usadas else "venda",
            "price": preco,
            "total": (preco or 0) * sobra,
            "market_name": mkt.get("name") if mkt.get("name") != r["name"] else None,
            "market_set": mkt.get("set"),
            "v": mkt.get("v"), "n_versions": mkt.get("n", 1),
            "foil_only": bool(mkt.get("foil_only")),
        })

    # Só as que têm excedente é que se vendem; as que estão inteiras num deck
    # ficam à parte, para ele ver que não desapareceram — foram para um deck.
    venda = [x for x in itens if x["qty"] > 0]
    nos_decks = [x for x in itens if x["used"] > 0]
    venda.sort(key=lambda x: (-(x["total"] or 0), x["set"], x["cn"]))

    blocos: dict[str, dict] = {}
    for x in venda:
        b = blocos.setdefault(x["block"], {"id": x["block"],
                                           "label": metrics.rotulo(x["block"], cfg),
                                           "printings": 0, "copies": 0, "cents": 0})
        b["printings"] += 1
        b["copies"] += x["qty"]
        b["cents"] += x["total"]

    return {
        "printings": len(venda),
        "copies": sum(x["qty"] for x in venda),
        "cents": sum(x["total"] for x in venda),
        # Quantas não têm oferta no CardTrader: entram na lista, não no total.
        "no_price": sum(1 for x in venda if x["price"] is None),
        "in_decks": len(nos_decks),
        "in_decks_copies": sum(x["used"] for x in nos_decks),
        "blocks": [blocos[b] for b, _ in metrics.BLOCOS if b in blocos],
        "items": venda,
        "kept": sorted(nos_decks, key=lambda x: (x["set"], x["cn"])),
    }


def payload(con: sqlite3.Connection, editable: bool = True) -> dict:
    from .metrics import _now
    return {"editable": editable, "generated_at": _now(), **listar(con)}

"""A secção "Faltas": o que comprar, e por que ordem.

Seis vistas da mesma pergunta:

  STAPLES    — cartas que faltam e que MAIS DO QUE UM deck pede. São as que
               rendem mais por euro: uma compra serve vários decks.
  POR DECK   — o que falta a cada deck, por edição. Desde 2026-09-11 cada deck
               é INDEPENDENTE: não desconta o que está noutro deck nem o que
               outro deck já manda comprar, e nas comuns e incomuns não desconta
               a Coleção. Sai do `decks.allocate`.
  A SUBIR    — o que falta do MASTER SET e está a subir de preço. Vive no
               `a_subir.py`: o âmbito é a métrica de master set, não os decks.
  MASTER SET — a lista completa do que falta ao master set, por edição e
               número, para comprar tudo de uma vez se lhe apetecer. Mesmo
               âmbito da anterior, sem o filtro de subida
               (`a_subir.master_faltas`).
  PIMP DECKS — as versões alteradas das cartas dos decks, também como lista de
               compras (ver `pimp`).
  A CAMINHO  — o que já comprou e ainda não chegou (ver `pending`).

A carência é GLOBAL, não por deck: soma-se o que todos os decks pedem de uma
carta e desconta-se o que ele tem. É diferente da alocação por prioridade, que
diz quem fica com o quê — aqui a pergunta é quanto falta comprar ao todo.
"""

from __future__ import annotations

import sqlite3

from . import a_subir, cardmarket, config, decks, metrics, pending


def _wanted(con: sqlite3.Connection) -> dict[str, dict]:
    """card_key -> {qty pedida ao todo, decks que a pedem}."""
    out: dict[str, dict] = {}
    for r in con.execute(
        "SELECT dc.card_key, dc.qty, d.deck_id, d.display_name, d.name, d.priority "
        "FROM deck_cards dc JOIN decks d ON d.deck_id = dc.deck_id"
    ):
        e = out.setdefault(r["card_key"], {"qty": 0, "decks": {}})
        e["qty"] += r["qty"]
        nome = r["display_name"] or r["name"]
        e["decks"][nome] = e["decks"].get(nome, 0) + r["qty"]
    return out



def _cheapest(con: sqlite3.Connection, keys: list[str]) -> dict[str, dict]:
    """card_key -> impressão base mais barata (onde se vai comprar)."""
    if not keys:
        return {}
    ordens = {s: config.set_order(s) for s in
              (r["set_id"] for r in con.execute("SELECT DISTINCT set_id FROM catalog.printings"))}
    ph = ",".join("?" * len(keys))
    best: dict[str, dict] = {}
    for r in con.execute(
        f"SELECT p.card_key, p.set_id, p.printing_id, p.public_code, p.orientation, "
        f"       p.image_medium, p.image_large, p.image_url, pl.price_cents, "
        f"       m.market_name, m.market_set, m.cardmarket_id "
        f"FROM catalog.printings p "
        f"LEFT JOIN catalog.price_latest pl ON pl.printing_id = p.printing_id "
        f"LEFT JOIN catalog.cardtrader_map m ON m.printing_id = p.printing_id "
        f"WHERE p.card_key IN ({ph}) AND p.variant_kind = 'base'", keys
    ):
        cand = {
            "set": r["set_id"], "id": r["printing_id"], "code": r["public_code"],
            "price": r["price_cents"],
            "landscape": (r["orientation"] or "").lower() == "landscape",
            "img": f"img/{r['printing_id']}.webp",
            "cdn": r["image_medium"] or r["image_large"] or r["image_url"],
            # Como o mercado escreve: "Darius - Trifarian", não
            # "Darius, Trifarian". É por aqui que a wantlist tem de sair.
            "market_name": r["market_name"],
            "market_set": r["market_set"],
            "cardmarket_id": r["cardmarket_id"],
        }
        atual = best.get(r["card_key"])
        rank = lambda c: (c["price"] is None, c["price"] if c["price"] is not None else 0,
                          ordens.get(c["set"], 999))
        if atual is None or rank(cand) < rank(atual):
            best[r["card_key"]] = cand
    return best


def shortfall(con: sqlite3.Connection) -> list[dict]:
    """O que falta comprar ao todo, com quantos decks pede cada carta."""
    pedido = _wanted(con)
    if not pedido:
        return []
    # O que já vem a caminho conta como tido: senão a lista mandava comprar
    # outra vez enquanto a encomenda não chega.
    tenho = decks.owned_by_card(con)
    for k, q in pending.open_by_card(con).items():
        tenho[k] = tenho.get(k, 0) + q
    nomes = {r["card_key"]: r["name"] for r in con.execute(
        "SELECT card_key, name FROM catalog.cards")}

    # TETO POR CARTA (decisão do André, 2026-09-01): não se compra mais do que
    # um playset da mesma carta, mesmo que a soma dos decks peça mais. Cinco
    # decks a pedir 3 Defy cada não são 15 Defy para comprar — são 3, e trocam-
    # se entre decks. É o mesmo alvo da métrica de playset jogável da Coleção,
    # por isso vale 3 nas Units/Spells/Gears, 12 nas Runas e 1 nos Legends e
    # Battlefields.
    tipos = {r["card_key"]: (r["type"], bool(r["is_token"])) for r in con.execute(
        "SELECT card_key, type, is_token FROM catalog.cards")}
    cfg = config.load()

    def teto(k: str) -> int:
        t, tok = tipos.get(k, (None, False))
        return metrics.playset_target(t, tok, cfg)

    # Tipos que esta secção não conta. As runas são baratas e compram-se a
    # granel; a 12 por deck enchiam os staples e escondiam o que interessa.
    # Continuam a contar na secção Decks e na Coleção.
    ignorar = set(cfg.get("faltas_ignorar_tipos", []))

    em_falta = {}
    for k, v in pedido.items():
        if tipos.get(k, (None, False))[0] in ignorar:
            continue
        alvo = min(v["qty"], teto(k))
        if alvo > tenho.get(k, 0):
            em_falta[k] = {**v, "alvo": alvo}
    onde = _cheapest(con, list(em_falta))

    out = []
    for k, v in em_falta.items():
        falta = v["alvo"] - tenho.get(k, 0)
        c = onde.get(k) or {}
        out.append({
            "card_key": k, "name": nomes.get(k, k),
            # `wanted` é o que os decks pedem ao todo; `target` é o teto.
            "wanted": v["qty"], "target": v["alvo"], "cap": teto(k),
            "have": tenho.get(k, 0), "missing": falta,
            "n_decks": len(v["decks"]),
            "decks": [{"deck": d, "qty": q} for d, q in
                      sorted(v["decks"].items(), key=lambda x: -x[1])],
            "price": c.get("price"),
            "total": (c.get("price") or 0) * falta,
            "set": c.get("set"), "code": c.get("code"),
            "img": c.get("img"), "cdn": c.get("cdn"),
            "landscape": c.get("landscape", False),
        })
    return out


def staples(con: sqlite3.Connection) -> list[dict]:
    """As que mais do que um deck pede. Comprar estas primeiro."""
    out = [x for x in shortfall(con) if x["n_decks"] >= 2]
    out.sort(key=lambda x: (-x["n_decks"], -x["missing"], -x["total"]))
    return out


def _tipos(con: sqlite3.Connection) -> dict[str, tuple]:
    return {r["card_key"]: (r["type"], bool(r["is_token"])) for r in con.execute(
        "SELECT card_key, type, is_token FROM catalog.cards")}


def _agrupar(con: sqlite3.Connection, falta: dict[str, int]) -> list[dict]:
    """{card_key: quantas comprar} -> lista por edição, com as cartas dentro.

    A edição escolhida é aquela onde a carta sai mais barata: é onde se compra.
    """
    if not falta:
        return []
    nomes = {r["card_key"]: r["name"] for r in con.execute(
        "SELECT card_key, name FROM catalog.cards")}
    onde = _cheapest(con, list(falta))

    # Em que outras edições existe a carta — dá-lhe alternativa se não
    # encontrar a versão mais barata.
    ph = ",".join("?" * len(falta))
    edicoes: dict[str, set] = {}
    for r in con.execute(
        f"SELECT card_key, set_id FROM catalog.printings "
        f"WHERE card_key IN ({ph}) AND variant_kind = 'base'", list(falta)
    ):
        edicoes.setdefault(r["card_key"], set()).add(r["set_id"])
    ordens = {s: config.set_order(s) for s in
              (r["set_id"] for r in con.execute("SELECT DISTINCT set_id FROM catalog.printings"))}

    versoes = cardmarket.versoes(con)
    # Todas as impressões de cada carta, para poder oferecer as alternativas.
    ph2 = ",".join("?" * len(falta))
    irmas: dict[str, list] = {}
    for r in con.execute(
        f"SELECT p.card_key, p.printing_id, p.set_id, m.market_name, m.market_set "
        f"FROM catalog.printings p "
        f"JOIN catalog.cardtrader_map m ON m.printing_id = p.printing_id "
        f"WHERE p.card_key IN ({ph2})", list(falta)
    ):
        irmas.setdefault(r["card_key"], []).append(r)

    por_set: dict[str, dict] = {}
    for k, n in falta.items():
        c = onde.get(k)
        if not c:
            continue

        # As versões da MESMA edição onde se vai comprar: base, arte
        # alternativa, showcase, signature. É o que ele quer ver lado a lado.
        alt = []
        for r in irmas.get(k, []):
            if r["set_id"] != c["set"] or r["printing_id"] == c["id"]:
                continue
            v = versoes.get(r["printing_id"])
            if not v:
                continue
            alt.append({"name": v.get("name") or r["market_name"],
                        "set": r["market_set"],
                        "v": v["v"], "n": v["n"], "label": v["label"],
                        "code": v["code"], "foil_only": v["foil_only"]})
        alt.sort(key=lambda x: x["v"])
        d = por_set.setdefault(c["set"], {"set": c["set"], "name": config.set_name(c["set"]),
                                          "cards": 0, "copies": 0, "cents": 0, "items": []})
        d["cards"] += 1
        d["copies"] += n
        d["cents"] += (c["price"] or 0) * n
        d["items"].append({
            "card_key": k, "name": nomes.get(k, k), "qty": n,
            "code": c["code"], "price": c["price"], "total": (c["price"] or 0) * n,
            "img": c["img"], "cdn": c["cdn"], "landscape": c["landscape"],
            "also": sorted(edicoes.get(k, set()) - {c["set"]}),
            "market_name": c.get("market_name"), "market_set": c.get("market_set"),
            "cardmarket_id": c.get("cardmarket_id"),
            "v": (versoes.get(c["id"]) or {}).get("v"),
            "n_versions": (versoes.get(c["id"]) or {}).get("n", 1),
            "foil_only": (versoes.get(c["id"]) or {}).get("foil_only", False),
            "outras_versoes": alt,
        })
    out = list(por_set.values())
    for d in out:
        d["items"].sort(key=lambda x: (-x["total"], x["name"]))
    out.sort(key=lambda d: (ordens.get(d["set"], 999), d["set"]))
    return out


def por_deck(con: sqlite3.Connection) -> list[dict]:
    """O que falta comprar a CADA deck. Desde 2026-09-11, deck a deck.

    *"Nos decks, quero que apresentes as faltas todas, cada deck será
    independente"* (André, 2026-09-11). Isto REVOGA a reserva partilhada de
    2026-09-01, em que o deck 2 não pedia o que o deck 1 já mandava comprar:
    agora cada deck pede o seu, e o que está noutro deck não lhe serve.

    A falta é a do `decks.allocate` — a mesma da página do deck e do tile —, e
    é ela que já sabe de locais e de raridades: o deck monta-se com o que está
    nele e no binder Decks/Venda, e nas comuns e incomuns a Coleção fica com as
    suas. **Uma pergunta, uma resposta**: a aba, a página do deck e a wantlist
    do Cardmarket contam todas o mesmo.

    O que vem a caminho continua a descontar, e distribui-se por PRIORIDADE —
    uma encomenda é uma cópia só, e o deck principal serve-se primeiro.
    """
    cfg = config.load()
    ignorar = set(cfg.get("faltas_ignorar_tipos", []))
    tipos = _tipos(con)
    alloc = decks.allocate(con)
    a_caminho = dict(pending.open_by_card(con))

    out = []
    for d in decks.decks_index(con):
        comprar: dict[str, int] = {}
        for k, q in alloc[d["id"]]["missing"].items():
            if tipos.get(k, (None, False))[0] in ignorar:
                continue
            vem = min(q, a_caminho.get(k, 0))
            a_caminho[k] = a_caminho.get(k, 0) - vem
            if q - vem > 0:
                comprar[k] = q - vem

        by_set = _agrupar(con, comprar)
        out.append({
            "id": d["id"], "name": d["name"], "priority": d["priority"],
            "have": d["have"], "wanted": d["wanted"],
            "cards": sum(len(g["items"]) for g in by_set),
            "copies": sum(g["copies"] for g in by_set),
            "cents": sum(g["cents"] for g in by_set),
            "by_set": by_set,
        })
    return out


def todos_juntos(con: sqlite3.Connection) -> dict:
    """E se ele quisesse os decks todos montados AO MESMO TEMPO?

    Aqui não há teto nem partilha: soma-se o que cada deck pede e desconta-se
    só o que ele tem. É o cenário de ter cópias a mais para não desmontar nada.
    """
    cfg = config.load()
    ignorar = set(cfg.get("faltas_ignorar_tipos", []))
    tipos = _tipos(con)
    tenho = dict(decks.owned_by_card(con))
    for k, q in pending.open_by_card(con).items():
        tenho[k] = tenho.get(k, 0) + q

    pedido: dict[str, int] = {}
    for k, v in _wanted(con).items():
        if tipos.get(k, (None, False))[0] in ignorar:
            continue
        pedido[k] = v["qty"]

    comprar = {k: q - tenho.get(k, 0) for k, q in pedido.items() if q > tenho.get(k, 0)}
    by_set = _agrupar(con, comprar)
    return {
        "cards": sum(len(g["items"]) for g in by_set),
        "copies": sum(g["copies"] for g in by_set),
        "cents": sum(g["cents"] for g in by_set),
        "by_set": by_set,
    }


def payload(con: sqlite3.Connection) -> dict:
    todas = shortfall(con)
    return {
        "staples": staples(con),
        "por_deck": por_deck(con),
        "todos_juntos": todos_juntos(con),
        "a_subir": a_subir.calcular(con),
        "master": a_subir.master_faltas(con),
        "pimp": pimp(con),
        "ignored_types": sorted(config.load().get("faltas_ignorar_tipos", [])),
        "pending": {**pending.totals(con), "items": pending.listar(con)},
        "totals": {
            "cards": len(todas),
            "copies": sum(x["missing"] for x in todas),
            "cents": sum(x["total"] for x in todas),
        },
    }


# ---------------------------------------------------------------------------
# Exportar para a wantlist do Cardmarket
# ---------------------------------------------------------------------------


def wantlist(grupos: list[dict], com_edicao: bool = True,
             com_versao: bool = True, com_variantes: bool = False) -> dict:
    """Texto para colar na wantlist do Cardmarket, a partir das listas dos decks.

    A linha é escrita pelo `cardmarket.linha`, o mesmo gerador das abas «A
    subir» e «Master set» — o formato vive num sítio só. Ver lá o porquê do
    formato e do foil.
    """
    linhas, foil = [], []

    def escreve(qtd, nome, v, n, edicao, ehfoil):
        linha = cardmarket.linha({
            "missing": qtd, "market_name": nome,
            "v": v if com_versao else None, "n_versions": n,
            "market_set": edicao if com_edicao else None,
        })
        linhas.append(linha)
        if ehfoil:
            foil.append(linha)

    for g in grupos:
        for it in g.get("items", []):
            escreve(it["qty"], it.get("market_name") or it["name"],
                    it.get("v"), it.get("n_versions", 1),
                    it.get("market_set"), it.get("foil_only"))
            if com_variantes:
                for a in it.get("outras_versoes", []):
                    escreve(it["qty"], a["name"], a["v"], a["n"],
                            a["set"], a["foil_only"])

    return {"text": "\n".join(linhas), "lines": len(linhas), "foil": foil}


# ---------------------------------------------------------------------------
# "Pimp decks": as versões alteradas das cartas que os decks usam
# ---------------------------------------------------------------------------


def pimp(con: sqlite3.Connection) -> dict:
    """Impressões alternativas das cartas usadas nos decks.

    "Versão alterada" = tudo o que não é a impressão canónica da carta: artes
    alternativas, reimpressões showcase (que têm número de coleção próprio) e
    promos. As signatures ficam de fora por omissão (`pimp_ignorar_tipos`).

    Devolve duas leituras dos mesmos dados: `by_set`, tudo junto por edição, e
    `by_deck`, uma lista por deck — porque a decisão de pimpar é por deck, e é
    a olhar para um deck de cada vez que ele decide o que vale a pena trocar.

    É LISTA DE COMPRAS (mudou a 2026-09-02, a pedido dele): desconta o que já
    tem e o que vem a caminho, por impressão, e a quantidade mostrada é só o
    que ainda falta comprar. As versões já completas saem da lista e contam em
    `done`.
    """
    quem = _wanted(con)
    if not quem:
        return {"cards": 0, "printings": 0, "cents": 0, "owned": 0,
                "by_set": [], "by_deck": [], "ignored": []}

    cfg = config.load()
    fora = set(cfg.get("pimp_ignorar_tipos", []))
    # Impressões concretas que ele nunca vai comprar — as sobrenumeradas de
    # topo, do género do `unl-238-219` (Baron Nashor a 2400 €). A carta
    # continua no Pimp pelas outras versões que tenha (ver `pimp_ignorar_impressoes`).
    fora_ids = set(cfg.get("pimp_ignorar_impressoes", []))
    tipos = _tipos(con)
    tenho_carta = decks.owned_by_card(con)
    ordens = {s: config.set_order(s) for s in
              (r["set_id"] for r in con.execute("SELECT DISTINCT set_id FROM catalog.printings"))}
    versoes = cardmarket.versoes(con)
    # O que já está tratado: o que tem na caixa mais o que vem a caminho.
    # Estas saem da lista — ele pediu para ver só o que ainda tem de comprar.
    copias = {r["printing_id"]: r["qty"] for r in
              con.execute("SELECT printing_id, qty FROM copies WHERE qty > 0")}
    for pid, q in pending.open_qty(con).items():
        copias[pid] = copias.get(pid, 0) + q
    mkt = {r["printing_id"]: r["market_set"] for r in
           con.execute("SELECT printing_id, market_set FROM catalog.cardtrader_map")}

    usados = list(quem)
    ph = ",".join("?" * len(usados))
    linhas = [dict(r) for r in con.execute(
        f"SELECT p.card_key, p.printing_id, p.set_id, p.api_sort, p.variant_kind, "
        f"       p.variant_label, p.public_code, p.orientation, p.name, "
        f"       p.image_medium, p.image_large, p.image_url, pl.price_cents "
        f"FROM catalog.printings p "
        f"LEFT JOIN catalog.price_latest pl ON pl.printing_id = p.printing_id "
        f"WHERE p.card_key IN ({ph})", usados)]

    por_carta: dict[str, list] = {}
    for r in linhas:
        por_carta.setdefault(r["card_key"], []).append(r)

    # As versões alteradas de cada carta, uma vez só.
    alt_de: dict[str, list] = {}
    for ck, lst in por_carta.items():
        lst.sort(key=lambda r: (ordens.get(r["set_id"], 999), r["api_sort"]))
        canonica = next((r for r in lst if r["variant_kind"] == "base"), lst[0])
        alt = [r for r in lst if r["printing_id"] != canonica["printing_id"]
               and r["variant_kind"] not in fora
               and r["printing_id"] not in fora_ids]
        if alt:
            alt_de[ck] = alt

    # Artes alternativas que só o CardTrader lista — as runas do SFD, UNL e
    # VEN. Ficam fora do catálogo (não contam para métricas nenhumas) mas
    # entram aqui, porque é o que o André quer pimpar quando o Legend do deck
    # é dessa edição.
    precos_mo = {r["printing_id"]: r["price_cents"] for r in con.execute(
        "SELECT printing_id, price_cents FROM catalog.price_latest")}
    for r in con.execute(
        "SELECT printing_id, set_id, collector_raw, market_name, market_set, "
        "       image_url, card_key, cardmarket_id "
        "FROM catalog.market_only "
        "WHERE card_key IS NOT NULL AND version LIKE '%Alternate Art%'"
    ):
        if r["card_key"] not in quem:
            continue
        alt_de.setdefault(r["card_key"], []).append({
            "card_key": r["card_key"], "printing_id": r["printing_id"],
            "set_id": r["set_id"], "api_sort": 9999,
            "variant_kind": "alt_art", "variant_label": "Arte alt.",
            # O CardTrader omite o 'a' na Calm Rune do SFD; a carta impressa
            # e a fatura levam-no, e é por aí que ele procura.
            "public_code": f"{r['set_id']}-{r['collector_raw']}"
                           + ("" if (r["collector_raw"] or "").lower().endswith("a") else "a"),
            "orientation": "portrait", "name": r["market_name"],
            "image_medium": None, "image_large": None,
            # Sem o `www.` o CardTrader responde 301; poupa-se um salto por
            # imagem, e evita-se um `<img>` a falhar se o cliente não seguir.
            "image_url": (r["image_url"] or "").replace(
                "https://cardtrader.com/", "https://www.cardtrader.com/") or None,
            "price_cents": precos_mo.get(r["printing_id"]),
            "market_only": True, "market_name": r["market_name"],
            "market_set": r["market_set"],
        })

    def montar(pedido: dict[str, int], preferir: str | None = None) -> dict:
        """{card_key: quantas o deck usa} -> estrutura por edição.

        `preferir` é a edição do Legend do deck: quando uma carta tem versão
        alterada nessa edição, mostra-se só essa. É o pedido do André para as
        runas — um deck cujo Legend é do SFD quer as runas alternativas do
        SFD, não as do OGN.

        HOJE ISTO NÃO MUDA NADA: a RiftScribe só tem runas no OGN e no VEN,
        e as artes alternativas delas só no OGN. As do SFD e do UNL existem
        (o CardTrader tem-nas) mas não estão no catálogo. Ver CLAUDE.md.
        """
        por_set: dict[str, dict] = {}
        cents = owned = feitas = 0
        for ck, qtd in pedido.items():
            opcoes = alt_de.get(ck, [])
            if preferir:
                mesma = [r for r in opcoes if r["set_id"] == preferir]
                if mesma:
                    opcoes = mesma
            for r in opcoes:
                v = versoes.get(r["printing_id"]) or {}
                tem = copias.get(r["printing_id"], 0)
                # Só interessa o que ainda falta comprar desta versão.
                falta = qtd - tem
                if falta <= 0:
                    feitas += 1
                    continue
                owned += 1 if tem else 0
                sub = (r["price_cents"] or 0) * falta
                cents += sub
                d = por_set.setdefault(r["set_id"], {
                    "set": r["set_id"], "name": config.set_name(r["set_id"]),
                    "printings": 0, "cents": 0, "items": []})
                d["printings"] += 1
                d["cents"] += sub
                d["items"].append({
                    "card_key": ck, "name": r["name"], "qty": falta,
                    "code": r["public_code"], "label": r["variant_label"],
                    "kind": r["variant_kind"],
                    "price": r["price_cents"], "total": sub,
                    "have": tem, "have_base": tenho_carta.get(ck, 0),
                    "landscape": (r["orientation"] or "").lower() == "landscape",
                    "img": None if r.get("market_only") else f"img/{r['printing_id']}.webp",
                    "cdn": r["image_medium"] or r["image_large"] or r["image_url"],
                    "market_only": bool(r.get("market_only")),
                    "market_name": r.get("market_name") or v.get("name"),
                    "market_set": r.get("market_set") or mkt.get(r["printing_id"]),
                    # As market_only não têm grupo para numerar; em Riftbound
                    # a arte alternativa é sempre a V.2 de 2 (medido nas 102
                    # que o catálogo tem).
                    "v": v.get("v", 2 if r.get("market_only") else None),
                    "n_versions": v.get("n", 2 if r.get("market_only") else 1),
                    "foil_only": v.get("foil_only", False),
                    "decks": sorted(quem.get(ck, {}).get("decks", {}).keys()),
                })
        out = sorted(por_set.values(), key=lambda d: (ordens.get(d["set"], 999), d["set"]))
        for d in out:
            d["items"].sort(key=lambda x: (-x["total"], x["name"]))
        return {
            "cards": len({it["card_key"] for d in out for it in d["items"]}),
            "printings": sum(d["printings"] for d in out),
            "cents": cents, "owned": owned, "done": feitas, "by_set": out,
        }

    def teto(ck: str, n: int) -> int:
        t, tok = tipos.get(ck, (None, False))
        return min(n, metrics.playset_target(t, tok, cfg)) or 1

    # Vista global: o que os decks pedem ao todo, com o teto de playset.
    geral = montar({ck: teto(ck, v["qty"]) for ck, v in quem.items() if ck in alt_de})

    # A edição do Legend de cada deck. Quando uma carta tem versão alterada em
    # várias edições, é a dessa que interessa — o deck é "de" uma edição.
    legend_set = {}
    for r in con.execute(
        "SELECT dc.deck_id, p.set_id FROM deck_cards dc "
        "JOIN catalog.cards c ON c.card_key = dc.card_key "
        "JOIN catalog.printings p ON p.printing_id = c.rep_printing_id "
        "WHERE dc.role = 'legend'"
    ):
        legend_set[r["deck_id"]] = r["set_id"]

    # Vista por deck: só o que aquele deck usa.
    por_deck = []
    for d in decks.decks_index(con):
        pedido = {}
        for r in con.execute(
            "SELECT card_key, SUM(qty) AS q FROM deck_cards WHERE deck_id = ? "
            "GROUP BY card_key", (d["id"],)
        ):
            if r["card_key"] in alt_de:
                pedido[r["card_key"]] = teto(r["card_key"], r["q"])
        por_deck.append({"id": d["id"], "name": d["name"], "priority": d["priority"],
                         "legend_set": legend_set.get(d["id"]),
                         **montar(pedido, legend_set.get(d["id"]))})

    return {**geral, "by_deck": por_deck, "ignored": sorted(fora)}

"""A secção "Faltas": o que comprar, e por que ordem.

Três vistas da mesma pergunta:

  STAPLES  — cartas que faltam e que MAIS DO QUE UM deck pede. São as que
             rendem mais por euro: uma compra serve vários decks.
  POR DECK — o que falta a cada deck, por edição.
  A SUBIR  — cartas em falta cujo preço subiu. Precisa de histórico: o
             `price_history` só ganha uma linha por dia em que o preço mude,
             por isso isto só diz alguma coisa depois de o `riftvault prices`
             correr algumas vezes.

A carência é GLOBAL, não por deck: soma-se o que todos os decks pedem de uma
carta e desconta-se o que ele tem. É diferente da alocação por prioridade, que
diz quem fica com o quê — aqui a pergunta é quanto falta comprar ao todo.
"""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from . import config, decks, metrics

# Abaixo disto o "subiu X%" é ruído de mercado, não um spike.
SPIKE_MIN_CENTS = 50
SPIKE_MIN_PCT = 15.0
SPIKE_DAYS = 30


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
    tenho = decks.owned_by_card(con)
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

    por_set: dict[str, dict] = {}
    for k, n in falta.items():
        c = onde.get(k)
        if not c:
            continue
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
        })
    out = list(por_set.values())
    for d in out:
        d["items"].sort(key=lambda x: (-x["total"], x["name"]))
    out.sort(key=lambda d: (ordens.get(d["set"], 999), d["set"]))
    return out


def por_deck(con: sqlite3.Connection) -> list[dict]:
    """O que falta comprar a CADA deck, descontando o que os anteriores já levam.

    Percorre-se por prioridade com uma reserva partilhada: o que ele tem, mais
    o que as listas dos decks anteriores já mandam comprar. Se o deck 1 já
    obriga a comprar 2 Defy, o deck 2 não pede mais nenhum — as cartas trocam-se
    entre decks, não se compram aos pares.

    Por isso a soma das abas é o custo REAL de montar os decks um de cada vez.
    A aba "todos juntos" (ver `todos_juntos`) responde à outra pergunta: quanto
    custaria tê-los montados ao mesmo tempo, com cópias para cada um.
    """
    cfg = config.load()
    ignorar = set(cfg.get("faltas_ignorar_tipos", []))
    tipos = _tipos(con)
    tenho = dict(decks.owned_by_card(con))

    def teto(k: str) -> int:
        t, tok = tipos.get(k, (None, False))
        return metrics.playset_target(t, tok, cfg)

    reserva = dict(tenho)          # o que já está disponível, incluindo compras
    out = []
    for d in decks.decks_index(con):
        pedido: dict[str, int] = {}
        for r in con.execute(
            "SELECT card_key, SUM(qty) AS q FROM deck_cards WHERE deck_id = ? "
            "GROUP BY card_key", (d["id"],)
        ):
            pedido[r["card_key"]] = r["q"]

        comprar: dict[str, int] = {}
        for k, q in pedido.items():
            if tipos.get(k, (None, False))[0] in ignorar:
                continue
            precisa = min(q, teto(k))
            em_mao = reserva.get(k, 0)
            if precisa > em_mao:
                comprar[k] = precisa - em_mao
                reserva[k] = precisa      # a compra passa a estar disponível

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
    tenho = decks.owned_by_card(con)

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


def spiking(con: sqlite3.Connection, days: int = SPIKE_DAYS,
            min_pct: float = SPIKE_MIN_PCT) -> dict:
    """Impressões cujo preço subiu na janela — **do Riftbound inteiro**.

    Não se limita à coleção nem aos decks (decisão do André, 2026-09-01): a
    ideia é apanhar cartas a valorizar antes de entrarem num deck. As que ele
    tem, ou de que precisa, vêm marcadas para saltarem à vista.

    Precisa de histórico. O `price_history` só grava quando o preço muda, por
    isso é normal haver vários dias gravados e nenhuma carta comparável — e
    nesse caso diz-se isso, em vez de inventar uma tendência.
    """
    desde = (date.today() - timedelta(days=days)).isoformat()
    dias = [r["day"] for r in con.execute(
        "SELECT DISTINCT day FROM prices.price_history ORDER BY day")]

    comparaveis = con.execute(
        "SELECT COUNT(*) AS n FROM (SELECT printing_id FROM prices.price_history "
        "WHERE day >= ? GROUP BY printing_id HAVING COUNT(DISTINCT day) > 1)",
        (desde,)).fetchone()["n"]
    base = {"days_recorded": len(dias), "first": dias[0] if dias else None,
            "comparable": comparaveis, "window_days": days, "min_pct": min_pct,
            "tracked": con.execute(
                "SELECT COUNT(DISTINCT printing_id) AS n FROM prices.price_history"
            ).fetchone()["n"]}
    if comparaveis == 0:
        return {**base, "ready": False, "items": []}

    preciso = {x["card_key"]: x["missing"] for x in shortfall(con)}
    tenho = {r["printing_id"]: r["qty"] for r in
             con.execute("SELECT printing_id, qty FROM copies WHERE qty > 0")}

    # Primeiro e último preço de cada impressão dentro da janela.
    linhas = con.execute(
        "SELECT h.printing_id, h.day, h.price_cents, p.card_key, p.name, "
        "       p.public_code, p.set_id, p.variant_label, p.orientation, "
        "       p.image_medium, p.image_large, p.image_url "
        "FROM prices.price_history h JOIN catalog.printings p "
        "ON p.printing_id = h.printing_id "
        "WHERE h.day >= ? ORDER BY h.printing_id, h.day", (desde,)).fetchall()

    janela: dict[str, dict] = {}
    for r in linhas:
        e = janela.get(r["printing_id"])
        if e is None:
            e = janela[r["printing_id"]] = {"row": r, "first": None, "last": None}
        if e["first"] is None:
            e["first"] = (r["day"], r["price_cents"])
        e["last"] = (r["day"], r["price_cents"])

    itens = []
    for pid, e in janela.items():
        antes, agora = e["first"][1], e["last"][1]
        if antes <= 0 or agora < SPIKE_MIN_CENTS:
            continue
        pct = (agora - antes) / antes * 100
        if pct < min_pct:
            continue
        r = e["row"]
        falta = preciso.get(r["card_key"], 0)
        itens.append({
            "printing_id": pid, "name": r["name"], "code": r["public_code"],
            "set": r["set_id"], "label": r["variant_label"],
            "landscape": (r["orientation"] or "").lower() == "landscape",
            "img": f"img/{pid}.webp",
            "cdn": r["image_medium"] or r["image_large"] or r["image_url"],
            "from_cents": antes, "to_cents": agora, "pct": round(pct, 1),
            "since": e["first"][0], "until": e["last"][0],
            "have": tenho.get(pid, 0),
            "missing": falta,
            # O que já custou esperar, nas cópias que ainda lhe faltam.
            "extra_cents": (agora - antes) * falta,
        })
    itens.sort(key=lambda i: (-i["pct"], -i["to_cents"]))
    return {**base, "ready": True, "items": itens}


def payload(con: sqlite3.Connection) -> dict:
    todas = shortfall(con)
    return {
        "staples": staples(con),
        "por_deck": por_deck(con),
        "todos_juntos": todos_juntos(con),
        "spiking": spiking(con),
        "ignored_types": sorted(config.load().get("faltas_ignorar_tipos", [])),
        "totals": {
            "cards": len(todas),
            "copies": sum(x["missing"] for x in todas),
            "cents": sum(x["total"] for x in todas),
        },
    }


# ---------------------------------------------------------------------------
# Exportar para a wantlist do Cardmarket
# ---------------------------------------------------------------------------


def wantlist(grupos: list[dict], com_edicao: bool = True) -> str:
    """Texto para colar na wantlist do Cardmarket: "3 Nome (Edição)".

    Usa o nome COMO O MERCADO O ESCREVE, não o da RiftScribe — lá é
    "Loose Cannon", no Cardmarket é "Jinx - Loose Cannon", e sem isso não
    casa nada. A edição vai junto porque 104 nomes existem em mais do que
    uma, e sem ela ficava ambíguo.

    NÃO VALIDADO contra o Cardmarket: o site responde 403 a pedidos
    automáticos e não há conta para experimentar. O formato "qtd nome
    (edição)" é o que a ajuda deles documenta. Ver CLAUDE.md.
    """
    linhas = []
    for g in grupos:
        for it in g.get("items", []):
            nome = it.get("market_name") or it["name"]
            if com_edicao and it.get("market_set"):
                linhas.append(f"{it['qty']} {nome} ({it['market_set']})")
            else:
                linhas.append(f"{it['qty']} {nome}")
    return "\n".join(linhas)

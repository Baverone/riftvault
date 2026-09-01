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
        f"       p.image_medium, p.image_large, p.image_url, pl.price_cents "
        f"FROM catalog.printings p "
        f"LEFT JOIN catalog.price_latest pl ON pl.printing_id = p.printing_id "
        f"WHERE p.card_key IN ({ph}) AND p.variant_kind = 'base'", keys
    ):
        cand = {
            "set": r["set_id"], "id": r["printing_id"], "code": r["public_code"],
            "price": r["price_cents"],
            "landscape": (r["orientation"] or "").lower() == "landscape",
            "img": f"img/{r['printing_id']}.webp",
            "cdn": r["image_medium"] or r["image_large"] or r["image_url"],
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

    em_falta = {}
    for k, v in pedido.items():
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


def por_deck(con: sqlite3.Connection) -> list[dict]:
    """O que falta a cada deck, por edição — a mesma conta da vista de decks."""
    out = []
    for d in decks.decks_index(con):
        out.append({**d, "by_set": decks.missing_by_set(con, d["id"])})
    return out


def spiking(con: sqlite3.Connection, days: int = SPIKE_DAYS,
            min_pct: float = SPIKE_MIN_PCT) -> dict:
    """Cartas em falta cujo preço subiu na janela. Precisa de histórico.

    O `price_history` só grava quando o preço muda, e só das impressões de
    interesse. Com um único dia gravado não há subida nenhuma para medir — e é
    isso que se diz, em vez de inventar uma tendência.
    """
    desde = (date.today() - timedelta(days=days)).isoformat()
    dias = [r["day"] for r in con.execute(
        "SELECT DISTINCT day FROM prices.price_history ORDER BY day")]

    # O que conta não é haver dois DIAS gravados, é haver alguma IMPRESSÃO com
    # duas leituras. O histórico só escreve quando o preço muda, por isso é
    # normal ter vários dias e nenhuma carta comparável — e "nada subiu" seria
    # mentira nesse caso: a verdade é que ainda não há com que comparar.
    comparaveis = con.execute(
        "SELECT COUNT(*) AS n FROM (SELECT printing_id FROM prices.price_history "
        "WHERE day >= ? GROUP BY printing_id HAVING COUNT(DISTINCT day) > 1)",
        (desde,)).fetchone()["n"]
    base = {"days_recorded": len(dias), "first": dias[0] if dias else None,
            "comparable": comparaveis, "window_days": days, "min_pct": min_pct}
    if comparaveis == 0:
        return {**base, "ready": False, "items": []}

    falta = {x["card_key"]: x for x in shortfall(con)}
    if not falta:
        return {**base, "ready": True, "items": []}

    # Primeiro e último preço de cada impressão dentro da janela.
    linhas = con.execute(
        "SELECT h.printing_id, h.day, h.price_cents, p.card_key "
        "FROM prices.price_history h JOIN catalog.printings p "
        "ON p.printing_id = h.printing_id "
        "WHERE h.day >= ? ORDER BY h.printing_id, h.day", (desde,)).fetchall()

    janela: dict[str, dict] = {}
    for r in linhas:
        e = janela.setdefault(r["printing_id"], {"card_key": r["card_key"],
                                                 "first": None, "last": None})
        if e["first"] is None:
            e["first"] = (r["day"], r["price_cents"])
        e["last"] = (r["day"], r["price_cents"])

    itens = []
    for pid, e in janela.items():
        x = falta.get(e["card_key"])
        if not x or e["first"] is None or e["last"] is None:
            continue
        antes, agora = e["first"][1], e["last"][1]
        if antes <= 0 or agora < SPIKE_MIN_CENTS:
            continue
        pct = (agora - antes) / antes * 100
        if pct < min_pct:
            continue
        itens.append({**x, "from_cents": antes, "to_cents": agora, "pct": round(pct, 1),
                      "since": e["first"][0], "until": e["last"][0],
                      "extra_cents": (agora - antes) * x["missing"]})
    itens.sort(key=lambda i: (-i["pct"], -i["extra_cents"]))
    return {**base, "ready": True, "items": itens}


def payload(con: sqlite3.Connection) -> dict:
    todas = shortfall(con)
    return {
        "staples": staples(con),
        "por_deck": por_deck(con),
        "spiking": spiking(con),
        "totals": {
            "cards": len(todas),
            "copies": sum(x["missing"] for x in todas),
            "cents": sum(x["total"] for x in todas),
        },
    }

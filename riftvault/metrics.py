"""As duas métricas de completude e os payloads que o frontend come.

  1) PLAYSET JOGÁVEL — alvo por CARTA LÓGICA (o nome). Qualquer impressão de
     qualquer edição conta. É a métrica de "consigo montar decks com isto".
  2) MASTER SET — alvo por IMPRESSÃO. É a métrica de colecionador.

São sempre calculadas e mostradas em paralelo. Nenhuma substitui a outra.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from . import config

# Ordem em que as variantes aparecem dentro do grupo, na grelha.
KIND_ORDER = {"base": 0, "alt_art": 1, "signature": 2,
              "rune_promo": 3, "special": 4, "token": 5, "unknown": 9}

RARITY_ORDER = ["common", "uncommon", "rare", "epic", "showcase"]


# --------------------------------------------------------------------------
# Alvos
# --------------------------------------------------------------------------


def playset_target(card_type: str | None, is_token: bool, cfg: dict | None = None) -> int:
    cfg = cfg or config.load()
    # Tokens: 1 de cada (decisão do André). Não são cartas de deck, mas contam
    # para a coleção estar completa, por isso entram nas duas métricas.
    if is_token:
        return int(cfg.get("token_target", 1))
    targets = cfg.get("playset_targets_by_type", {})
    return int(targets.get(card_type or "", targets.get("default", 3)))


def master_target(printing_id: str, kind: str, card_type: str | None, is_token: bool,
                  cfg: dict | None = None) -> int:
    cfg = cfg or config.load()
    override = cfg.get("master_target_overrides", {}).get(printing_id)
    if override is not None:
        return int(override)
    if is_token:
        return int(cfg.get("token_target", 1))
    by_variant = cfg.get("master_targets_by_variant", {})
    if kind == "base" and cfg.get("master_base_follows_type", True):
        # Senão uma Rune base pediria 3 em vez de 12, e um Legend pediria 3
        # em vez de 1. O alvo do master da base segue o alvo de jogo.
        return playset_target(card_type, is_token, cfg)
    if kind in set(cfg.get("master_variantes_playset", [])):
        # O André quer contagem de playset nas artes alternativas (2026-09-05):
        # se decide colecionar a alt art, quer as 3 na mesma, não uma. Isto é
        # só o alvo do tile — continuam fora da percentagem (`master_counts`).
        return playset_target(card_type, is_token, cfg)
    return int(by_variant.get(kind, 1))


def master_counts(kind: str, is_token: bool, cfg: dict | None = None) -> bool:
    """Esta impressão entra na PERCENTAGEM de set completo?

    É diferente do alvo: o alvo é o que aparece no tile ("0/1"), isto é o que
    entra no denominador. O André quer ver quantas artes alternativas lhe
    faltam, mas não quer que elas baixem a percentagem do set — são duas
    perguntas diferentes e passaram a ter dois campos.
    """
    cfg = cfg or config.load()
    if kind in set(cfg.get("master_ignorar_variantes", [])):
        return False
    return not is_token or int(cfg.get("token_target", 1)) > 0


# --------------------------------------------------------------------------
# Payloads
# --------------------------------------------------------------------------


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sets_payload(con: sqlite3.Connection) -> list[dict]:
    rows = con.execute(
        "SELECT set_id, COUNT(*) AS n FROM catalog.printings GROUP BY set_id"
    ).fetchall()
    out = [
        {"id": r["set_id"], "name": config.set_name(r["set_id"]),
         "order": config.set_order(r["set_id"]), "n_printings": r["n"]}
        for r in rows
    ]
    out.sort(key=lambda s: (s["order"], s["id"]))
    return out


def owned_by_card(con: sqlite3.Connection) -> dict[str, int]:
    """Cópias por carta lógica, somando TODAS as impressões de TODAS as edições."""
    rows = con.execute(
        "SELECT p.card_key AS k, SUM(c.qty) AS n FROM copies c "
        "JOIN catalog.printings p ON p.printing_id = c.printing_id "
        "WHERE c.qty > 0 GROUP BY p.card_key"
    ).fetchall()
    return {r["k"]: r["n"] for r in rows}


def prices_map(con: sqlite3.Connection) -> dict[str, int]:
    """printing_id -> preço em cêntimos. Vazio enquanto não houver `riftvault prices`."""
    try:
        rows = con.execute(
            "SELECT printing_id, price_cents FROM catalog.price_latest "
            "WHERE price_cents IS NOT NULL"
        ).fetchall()
    except sqlite3.OperationalError:
        return {}               # catálogo antigo, sem a tabela ainda
    return {r["printing_id"]: r["price_cents"] for r in rows}


def set_payload(con: sqlite3.Connection, set_id: str, editable: bool = True,
                image_mode: str = "local") -> dict:
    from . import decks

    cfg = config.load()
    qty = {r["printing_id"]: r["qty"] for r in con.execute("SELECT printing_id, qty FROM copies")}
    owned_cards = owned_by_card(con)
    price = prices_map(con)
    # Onde estão as cópias que não estão no binder: nos decks.
    try:
        nos_decks = decks.printing_allocation(con)
    except sqlite3.OperationalError:
        nos_decks = {}

    rows = con.execute(
        "SELECT * FROM catalog.printings WHERE set_id = ? ORDER BY api_sort", (set_id,)
    ).fetchall()

    groups: dict[str, dict] = {}
    for r in rows:
        g = groups.get(r["group_key"])
        if g is None:
            g = groups[r["group_key"]] = {
                "key": r["group_key"],
                "cn": r["collector_number"],
                "lane": r["lane"],
                "sort": r["api_sort"],
                "card_key": r["card_key"],
                "name": r["name"],
                "type": r["type"],
                "rarity": r["base_rarity"],
                # Custo de energia da impressão base — é por aqui que a grelha
                # ordena quando se escolhe "Custo".
                "energy": r["energy"],
                "faction": r["faction"],
                "is_token": bool(r["is_token"]),
                "printings": [],
            }
        g["printings"].append({
            "id": r["printing_id"],
            "code": r["public_code"],
            "kind": r["variant_kind"],
            "label": r["variant_label"],
            "name": r["name"],
            "rarity": r["rarity"],
            # Battlefields vêm 'landscape' — o tile tem de mudar de proporção.
            "landscape": (r["orientation"] or "").lower() == "landscape",
            "price": price.get(r["printing_id"]),   # cêntimos, ou None
            "in_decks": nos_decks.get(r["printing_id"], []),
            "qty": qty.get(r["printing_id"], 0),
            "target": master_target(r["printing_id"], r["variant_kind"], r["type"],
                                    bool(r["is_token"]), cfg),
            "counts": master_counts(r["variant_kind"], bool(r["is_token"]), cfg),
            "img": f"img/{r['printing_id']}.webp",
            "cdn": r["image_medium"] or r["image_large"] or r["image_url"],
            "banned": bool(r["is_banned"]),
            "sort": r["api_sort"],
        })

    ordered = sorted(groups.values(), key=lambda g: g["sort"])
    for g in ordered:
        g["printings"].sort(key=lambda p: (KIND_ORDER.get(p["kind"], 9), p["sort"]))
        for i, p in enumerate(g["printings"]):
            p["head"] = i == 0   # o tile que fica visível em "Só artes base"
        target = playset_target(g["type"], g["is_token"], cfg)
        g["playset"] = {"owned": owned_cards.get(g["card_key"], 0), "target": target}

    # ----- barras de progresso e contadores -----
    seen_cards: set[str] = set()
    play_done = play_total = 0
    for g in ordered:
        if g["playset"]["target"] <= 0 or g["card_key"] in seen_cards:
            continue
        seen_cards.add(g["card_key"])
        play_total += 1
        if g["playset"]["owned"] >= g["playset"]["target"]:
            play_done += 1

    master_done = master_total = 0
    by_rarity: dict[str, list[int]] = {}
    for g in ordered:
        for p in g["printings"]:
            if p["target"] <= 0 or not p["counts"]:
                continue
            master_total += 1
            complete = p["qty"] >= p["target"]
            master_done += 1 if complete else 0
            slot = by_rarity.setdefault(g["rarity"] or "?", [0, 0])
            slot[1] += 1
            slot[0] += 1 if complete else 0

    rarities = [
        {"rarity": k, "done": v[0], "total": v[1]}
        for k, v in sorted(by_rarity.items(),
                           key=lambda kv: (RARITY_ORDER.index(kv[0])
                                           if kv[0] in RARITY_ORDER else 99, kv[0]))
    ]

    # Valor do que tenho DESTA edição, e o que a edição inteira valeria se
    # estivesse completa segundo a métrica de master set.
    value_owned = value_full = 0
    for g in ordered:
        for p in g["printings"]:
            if p["price"] is None:
                continue
            value_owned += p["qty"] * p["price"]
            # "se estivesse completa" é sobre o SET: as variantes que não
            # entram na percentagem também não entram no preço dele.
            if p["counts"]:
                value_full += p["target"] * p["price"]

    return {
        "editable": editable,
        "image_mode": image_mode,
        "generated_at": _now(),
        "set": {"id": set_id, "name": config.set_name(set_id)},
        # A partir de que preço é que o valor aparece por cima da carta.
        "price_badge_min": int(cfg.get("price_badge_min_cents", 100)),
        "progress": {
            "playset": {"done": play_done, "total": play_total},
            "master": {"done": master_done, "total": master_total},
            "value": {"owned": value_owned, "full": value_full,
                      "currency": "EUR", "has_prices": bool(price)},
            "rarities": rarities,
        },
        "groups": ordered,
    }


def index_payload(con: sqlite3.Connection, editable: bool = True,
                  image_mode: str = "local") -> dict:
    from . import collection, prices

    try:
        value = prices.collection_value(con)
    except sqlite3.OperationalError:
        value = None            # ainda não correu `riftvault prices`

    return {
        "editable": editable,
        "image_mode": image_mode,
        "generated_at": _now(),
        "sets": sets_payload(con),
        "totals": collection.totals(con),
        "value": value,
    }

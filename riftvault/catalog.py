"""Constrói o catalog.db a partir da API da RiftScribe.

O trabalho todo desta camada é traduzir o que a API dá (uma lista plana de
entradas com um campo `variant`) para os dois grãos de que o site precisa:

  - IMPRESSÃO (printing) — uma entrada da API. É onde se contam as cópias.
  - CARTA LÓGICA (card)   — o nome. É onde se conta o playset jogável.

E, pelo meio, resolver as duas armadilhas documentadas no CLAUDE.md:
`(set_id, collector_number)` não é único, e a mesma carta reaparece com
números de coleção diferentes (até dentro da mesma edição).
"""

from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from datetime import datetime, timezone

from . import config, db, riftscribe

# --------------------------------------------------------------------------
# Derivações a partir do campo `variant`
# --------------------------------------------------------------------------

# Variantes que partilham a "lane" principal com a carta base, ou seja, que
# aparecem no mesmo tile-grupo da grelha.
MAIN_VARIANTS = {"", "a", "star"}

LANE_KINDS = {"t": "token", "r": "rune_promo", "sp": "special"}

LABELS = {
    "base": "Base",
    "alt_art": "Arte alt.",
    "signature": "Signature",
    "token": "Token",
    "rune_promo": "Runa promo",
    "special": "Promo",
    "unknown": "Variante ?",
}


def lane_of(variant: str) -> str:
    if variant in MAIN_VARIANTS:
        return "main"
    m = re.match(r"^([a-z]+)", variant or "")
    return m.group(1) if m else "other"


def kind_of(variant: str) -> str:
    if variant == "":
        return "base"
    if variant == "a":
        return "alt_art"
    if variant == "star":
        return "signature"
    return LANE_KINDS.get(lane_of(variant), "unknown")


def card_key_of(name: str) -> str:
    """Chave da carta lógica: o nome, normalizado.

    O número de coleção NÃO serve — ver ARMADILHA 2 no CLAUDE.md.
    """
    s = unicodedata.normalize("NFKC", name or "").strip().casefold()
    return re.sub(r"\s+", " ", s)


def aliases_of(row: dict) -> set[str]:
    """Formas de escrever uma impressão que o CLI e as decklists devem aceitar."""
    out: set[str] = set()
    pid = row["printing_id"]
    set_id = row["set_id"].lower()
    cn = row["collector_number"]
    variant = row["variant"]

    out.add(pid.lower())
    code = (row.get("public_code") or "").lower()
    if code:
        out.add(code)
        out.add(code.split("/")[0])  # 'ogn-007a/298' -> 'ogn-007a'

    if variant in MAIN_VARIANTS:
        suffixes = {"": [""], "a": ["a"], "star": ["-star", "*", "star"]}[variant]
        for suf in suffixes:
            out.add(f"{set_id}-{cn}{suf}")
            out.add(f"{set_id}-{cn:03d}{suf}")
    else:
        out.add(f"{set_id}-{variant}")

    return {a for a in out if a}


# --------------------------------------------------------------------------
# Sync
# --------------------------------------------------------------------------


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _to_row(api: dict, api_sort: int, cfg: dict) -> dict:
    variant = api.get("variant") or ""
    kind = kind_of(variant)
    lane = lane_of(variant)
    stats = api.get("stats") or {}
    key = card_key_of(api.get("name", ""))
    return {
        "printing_id": api["id"],
        "set_id": api["set_id"],
        "collector_number": api["collector_number"],
        "variant": variant,
        "lane": lane,
        "group_key": f"{api['set_id']}|{api['collector_number']}|{lane}",
        "variant_kind": kind,
        "variant_label": LABELS.get(kind, LABELS["unknown"]),
        "card_key": key,
        "public_code": api.get("public_code"),
        "name": api.get("name"),
        "rarity": api.get("rarity"),
        "base_rarity": api.get("rarity"),  # corrigido a seguir, pelo grupo
        "faction": api.get("faction"),
        "domains_json": json.dumps(api.get("domains") or [], ensure_ascii=False),
        "type": api.get("type"),
        "orientation": api.get("orientation"),
        "energy": stats.get("energy"),
        "might": stats.get("might"),
        "power": stats.get("power"),
        "is_banned": 1 if api.get("is_banned") else 0,
        "is_token": 1 if (kind == "token" or key in set(cfg.get("token_card_keys", []))) else 0,
        "description": api.get("description"),
        "flavor_text": api.get("flavor_text"),
        "artist": (api.get("art") or {}).get("artist"),
        "keywords_json": json.dumps(api.get("keywords") or [], ensure_ascii=False),
        "tags_json": json.dumps(api.get("tags") or [], ensure_ascii=False),
        "image_url": api.get("image"),
        "image_small": (api.get("image_thumb") or {}).get("small"),
        "image_medium": (api.get("image_thumb") or {}).get("medium"),
        "image_large": (api.get("image_thumb") or {}).get("large"),
        "image_path": None,
        "api_sort": api_sort,
        "fetched_at": _now(),
    }


_INSERT = """
INSERT INTO printings (
    printing_id, set_id, collector_number, variant, lane, group_key,
    variant_kind, variant_label, card_key, public_code, name, rarity,
    base_rarity, faction, domains_json, type, orientation, energy, might,
    power, is_banned, is_token, description, flavor_text, artist,
    keywords_json, tags_json, image_url, image_small, image_medium,
    image_large, image_path, api_sort, fetched_at
) VALUES (
    :printing_id, :set_id, :collector_number, :variant, :lane, :group_key,
    :variant_kind, :variant_label, :card_key, :public_code, :name, :rarity,
    :base_rarity, :faction, :domains_json, :type, :orientation, :energy,
    :might, :power, :is_banned, :is_token, :description, :flavor_text,
    :artist, :keywords_json, :tags_json, :image_url, :image_small,
    :image_medium, :image_large, :image_path, :api_sort, :fetched_at
)
ON CONFLICT(printing_id) DO UPDATE SET
    set_id=excluded.set_id, collector_number=excluded.collector_number,
    variant=excluded.variant, lane=excluded.lane, group_key=excluded.group_key,
    variant_kind=excluded.variant_kind, variant_label=excluded.variant_label,
    card_key=excluded.card_key, public_code=excluded.public_code,
    name=excluded.name, rarity=excluded.rarity, base_rarity=excluded.base_rarity,
    faction=excluded.faction, domains_json=excluded.domains_json,
    type=excluded.type, orientation=excluded.orientation, energy=excluded.energy,
    might=excluded.might, power=excluded.power, is_banned=excluded.is_banned,
    is_token=excluded.is_token, description=excluded.description,
    flavor_text=excluded.flavor_text, artist=excluded.artist,
    keywords_json=excluded.keywords_json, tags_json=excluded.tags_json,
    image_url=excluded.image_url, image_small=excluded.image_small,
    image_medium=excluded.image_medium, image_large=excluded.image_large,
    api_sort=excluded.api_sort, fetched_at=excluded.fetched_at
"""


def sync(set_ids: list[str] | None = None, delay: float = riftscribe.POLITE_DELAY,
         log=print) -> dict:
    """Descarrega o catálogo para o catalog.db. Devolve um resumo."""
    cfg = config.reload()
    con = db.catalog_only()

    discovered = riftscribe.list_sets()
    targets = [s for s in (set_ids or discovered) if s]
    unknown_variants: set[str] = set()
    counts: dict[str, int] = {}

    for set_id in targets:
        if set_id not in discovered:
            log(f"  ! {set_id} não aparece em /api/cards/filters — a saltar")
            continue
        log(f"  {set_id}: a descarregar...")
        rows = []
        for i, api in enumerate(riftscribe.iter_cards(set_id, delay=delay)):
            row = _to_row(api, i, cfg)
            if row["variant_kind"] == "unknown":
                unknown_variants.add(row["variant"])
            rows.append(row)

        # A raridade da VARIANTE não serve para contar: quase todas as artes
        # alternativas vêm como 'showcase'. Vale a raridade da base do grupo.
        base_rarity = {r["group_key"]: r["rarity"] for r in rows if r["variant_kind"] == "base"}
        for r in rows:
            r["base_rarity"] = base_rarity.get(r["group_key"], r["rarity"])

        con.execute("BEGIN")
        # Impressões que a API deixou de devolver saem do catálogo.
        if rows:
            placeholders = ",".join("?" * len(rows))
            con.execute(
                f"DELETE FROM printings WHERE set_id = ? AND printing_id NOT IN ({placeholders})",
                [set_id] + [r["printing_id"] for r in rows],
            )
        else:
            con.execute("DELETE FROM printings WHERE set_id = ?", (set_id,))
        con.executemany(_INSERT, rows)
        con.execute(
            "INSERT INTO sets (set_id, name, sort_order, n_printings, synced_at) "
            "VALUES (?,?,?,?,?) ON CONFLICT(set_id) DO UPDATE SET "
            "name=excluded.name, sort_order=excluded.sort_order, "
            "n_printings=excluded.n_printings, synced_at=excluded.synced_at",
            (set_id, config.set_name(set_id), config.set_order(set_id), len(rows), _now()),
        )
        con.execute("COMMIT")
        counts[set_id] = len(rows)
        log(f"  {set_id}: {len(rows)} impressões")

    rebuild_cards(con)
    rebuild_aliases(con)
    con.close()

    return {
        "sets": counts,
        "total": sum(counts.values()),
        "unknown_variants": sorted(unknown_variants),
    }


def rebuild_cards(con: sqlite3.Connection) -> int:
    """Reconstrói a tabela `cards` (a carta lógica) a partir das impressões."""
    cfg = config.load()
    forced_tokens = set(cfg.get("token_card_keys", []))
    orders = {s: config.set_order(s) for s in
              (r["set_id"] for r in con.execute("SELECT DISTINCT set_id FROM printings"))}

    rows = con.execute(
        "SELECT printing_id, card_key, name, type, faction, domains_json, "
        "       is_banned, is_token, variant_kind, set_id, collector_number "
        "FROM printings"
    ).fetchall()

    by_key: dict[str, list[sqlite3.Row]] = {}
    for r in rows:
        by_key.setdefault(r["card_key"], []).append(r)

    out = []
    for key, group in by_key.items():
        # Representante = a impressão base mais antiga (edição mais baixa,
        # depois número de coleção mais baixo). É a que dá o tipo e a imagem
        # que a vista de decks vai mostrar.
        def rank(r: sqlite3.Row):
            return (0 if r["variant_kind"] == "base" else 1,
                    orders.get(r["set_id"], 999), r["collector_number"])

        rep = min(group, key=rank)
        out.append((
            key, rep["name"], rep["type"], rep["faction"], rep["domains_json"],
            1 if any(r["is_banned"] for r in group) else 0,
            1 if (key in forced_tokens or any(r["is_token"] for r in group)) else 0,
            rep["printing_id"], len(group),
        ))

    con.execute("BEGIN")
    con.execute("DELETE FROM cards")
    con.executemany(
        "INSERT INTO cards (card_key, name, type, faction, domains_json, "
        "is_banned, is_token, rep_printing_id, n_printings) VALUES (?,?,?,?,?,?,?,?,?)",
        out,
    )
    # O flag de token é da carta lógica: propaga-se de volta às impressões,
    # senão o OGN-271 ("Recruit (DE)", token com número normal) pediria playset.
    con.execute(
        "UPDATE printings SET is_token = 1 WHERE card_key IN "
        "(SELECT card_key FROM cards WHERE is_token = 1)"
    )
    con.execute("COMMIT")
    return len(out)


def rebuild_aliases(con: sqlite3.Connection) -> int:
    rows = con.execute(
        "SELECT printing_id, set_id, collector_number, variant, public_code FROM printings"
    ).fetchall()
    pairs = []
    for r in rows:
        for alias in aliases_of(dict(r)):
            pairs.append((alias, r["printing_id"]))

    con.execute("BEGIN")
    con.execute("DELETE FROM printing_aliases")
    # INSERT OR IGNORE: um alias ambíguo fica com a primeira impressão. Só
    # acontece se a API alguma vez colidir códigos; o `id` completo é sempre
    # inequívoco e serve de escape.
    con.executemany("INSERT OR IGNORE INTO printing_aliases (alias, printing_id) VALUES (?,?)", pairs)
    con.execute("COMMIT")
    return len(pairs)


# --------------------------------------------------------------------------
# Cache local das imagens
# --------------------------------------------------------------------------


def image_filename(printing_id: str) -> str:
    return f"{printing_id}.webp"


def sync_images(set_ids: list[str] | None = None, log=print) -> dict:
    """Descarrega os thumbnails em falta para data/images/. É retomável."""
    cfg = config.load()
    size = cfg.get("image_size", "medium")
    col = {"small": "image_small", "medium": "image_medium", "large": "image_large"}[size]

    config.ensure_dirs()
    con = db.catalog_only()
    sql = f"SELECT printing_id, {col} AS url FROM printings WHERE {col} IS NOT NULL"
    params: tuple = ()
    if set_ids:
        sql += " AND set_id IN (%s)" % ",".join("?" * len(set_ids))
        params = tuple(set_ids)
    sql += " ORDER BY set_id, api_sort"

    rows = con.execute(sql, params).fetchall()
    got = skipped = failed = 0
    for i, r in enumerate(rows, 1):
        path = config.IMAGES_DIR / image_filename(r["printing_id"])
        if path.exists() and path.stat().st_size > 0:
            skipped += 1
            continue
        try:
            path.write_bytes(riftscribe.download(r["url"]))
            got += 1
        except riftscribe.RiftScribeError as exc:
            failed += 1
            log(f"  ! {r['printing_id']}: {exc}")
        if got and got % 50 == 0:
            log(f"  ... {i}/{len(rows)} ({got} novas)")

    con.execute("UPDATE printings SET image_path = printing_id || '.webp'")
    con.close()
    return {"downloaded": got, "cached": skipped, "failed": failed, "total": len(rows)}

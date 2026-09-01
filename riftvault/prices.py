"""Preços via CardTrader (API v2). Validado contra a API real a 2026-08-31.

A RiftScribe não tem preços nenhuns — procurado em toda a spec, não existe
campo nenhum de preço. O CardTrader tem Riftbound completo (`game_id` 22) e é
a mesma fonte já usada no mtgvault, com o mesmo token.

A PONTE
    O `collector_number` dos blueprints do CardTrader já traz o sufixo da
    variante: '007' base, '007a' arte alternativa, '299s' signature. Isso casa
    diretamente com (set_id, collector_number, variant) da RiftScribe, sem
    precisar de comparar nomes — o que é bom, porque os nomes são diferentes
    ("Jinx - Loose Cannon" no CardTrader, "Loose Cannon" na RiftScribe).

    Medido: 1179 das 1180 impressões casam (99,9%), sem ambiguidades. A única
    que falha é `VEN-T04 "Recruit (NX)"`, um token que o CardTrader não lista.
    O CardTrader tem ainda impressões que a RiftScribe ainda não tem (runas
    promo do SFD/UNL e as signatures do VEN); essas ficam de fora por não
    haver impressão nossa a que se agarrem.

O PREÇO
    Menor preço pedido em Near Mint ou Mint, inglês, sem graded/altered/signed,
    de vendedor que não esteja de férias. Tudo o que o CardTrader devolve para
    Riftbound está em EUR.

    Prefere-se a oferta NÃO foil; só se não houver nenhuma é que se usa a foil
    (fica marcado em `from_foil`). Como o riftvault não distingue acabamentos,
    é a escolha conservadora: nunca inflaciona a coleção com um preço de foil
    quando o mais provável é a carta ser normal.

ONDE FICA
    `catalog.price_latest` — preço atual das 1180 impressões. Descartável.
    `price_history` (vault.db) — só das impressões que o André TEM, e só
    quando o preço muda. O vault.db vai para o Git e cada commit guarda uma
    cópia inteira do ficheiro.
"""

from __future__ import annotations

import os
import sqlite3
import time
from datetime import date, datetime, timezone

import requests

from . import config, db

CT_BASE = "https://api.cardtrader.com/api/v2"
RIFTBOUND_GAME_ID = 22          # confirmado em /api/v2/games
SINGLES_CATEGORY = 258          # confirmado nos blueprints; o resto é selado

# Condições que contam como carta "boa". Fora disto o preço não é comparável.
OK_CONDITIONS = {"Mint", "Near Mint"}
LANGUAGE = "en"


class CardTraderError(RuntimeError):
    pass


class CardTrader:
    def __init__(self, token: str | None = None):
        # Limpar espaços e BOM: um token colado de um editor, ou passado por
        # pipe do PowerShell, vem com `﻿` à frente — e aí o `requests`
        # rebenta a codificar o header em latin-1, com uma mensagem que não
        # faz lembrar nada disto. Aconteceu no GitHub Actions.
        bruto = token or os.environ.get("CARDTRADER_TOKEN") or ""
        self.token = bruto.strip().lstrip("﻿").strip()
        if not self.token:
            raise CardTraderError(
                "Falta CARDTRADER_TOKEN no ambiente.\n"
                "  Cria um token nas definições do perfil em cardtrader.com e faz:\n"
                '    setx CARDTRADER_TOKEN "o-token"\n'
                "  (abre um terminal novo a seguir)"
            )
        self.s = requests.Session()
        self.s.headers.update({
            "Authorization": f"Bearer {self.token}",
            # SÓ ASCII. Um User-Agent com acentos leva 403 do CardTrader
            # (testado: "colecao" dá 200, "coleção" dá 403).
            "User-Agent": "riftvault/0.1 (personal collection manager)",
        })

    def get(self, path: str, params: dict | None = None):
        url = f"{CT_BASE}{path}"
        try:
            r = self.s.get(url, params=params, timeout=180)
        except requests.RequestException as exc:
            raise CardTraderError(f"falhou o pedido a {url}: {exc}") from exc
        if r.status_code == 401:
            raise CardTraderError("o CARDTRADER_TOKEN foi recusado (401). Gera outro.")
        if r.status_code != 200:
            raise CardTraderError(f"{url} devolveu HTTP {r.status_code}")
        return r.json()

    def expansions(self) -> list[dict]:
        data = self.get("/expansions")
        rows = data.get("array", data) if isinstance(data, dict) else data
        return [x for x in rows if x.get("game_id") == RIFTBOUND_GAME_ID]

    def blueprints(self, expansion_id: int) -> list[dict]:
        data = self.get("/blueprints/export", {"expansion_id": expansion_id})
        return data.get("array", data) if isinstance(data, dict) else data

    def marketplace(self, expansion_id: int) -> dict:
        # Devolve o mercado inteiro da expansão num pedido só (~45 MB no OGN).
        return self.get("/marketplace/products", {"expansion_id": expansion_id})


# ---------------------------------------------------------------------------
# Mapa RiftScribe <-> CardTrader
# ---------------------------------------------------------------------------

# 'star' na RiftScribe é o sufixo 's' no CardTrader.
_SUFFIX = {"": "", "a": "a", "star": "s"}


def _rs_key(collector_number: int, variant: str) -> str:
    """Chave de casamento a partir de uma impressão da RiftScribe."""
    if variant in _SUFFIX:
        return f"{collector_number:03d}{_SUFFIX[variant]}"
    return variant.lower()          # tokens/runas/promos: t04, r01, sp4


def _ct_key(raw) -> str | None:
    """Normaliza o collector_number do CardTrader: '7a' e '007a' dão o mesmo."""
    if raw is None:
        return None
    s = str(raw).strip().lower()
    if not s:
        return None
    digits = ""
    i = 0
    while i < len(s) and s[i].isdigit():
        digits += s[i]
        i += 1
    rest = s[i:].strip()
    if digits:
        return f"{int(digits):03d}{rest}"
    return s


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sync_map(ct: CardTrader | None = None, log=print) -> dict:
    """Constrói `cardtrader_map`. Reconstruível a qualquer momento."""
    ct = ct or CardTrader()
    con = db.catalog_only()

    # As expansões do CardTrader trazem `code` igual ao set_id da RiftScribe,
    # em minúsculas (ogn, ogs, sfd, unl, ven).
    by_code = {(x.get("code") or "").upper(): x for x in ct.expansions()}
    our_sets = [r["set_id"] for r in con.execute("SELECT DISTINCT set_id FROM printings")]

    pairs, missing, sem_exp = [], [], []
    for set_id in sorted(our_sets):
        exp = by_code.get(set_id)
        if not exp:
            sem_exp.append(set_id)
            log(f"  ! {set_id} não tem expansão correspondente no CardTrader")
            continue

        index: dict[str, int] = {}
        for b in ct.blueprints(exp["id"]):
            if b.get("category_id") != SINGLES_CATEGORY:
                continue            # booster boxes, playmats e afins
            k = _ct_key((b.get("fixed_properties") or {}).get("collector_number"))
            if k and k not in index:
                index[k] = b["id"]

        rows = con.execute(
            "SELECT printing_id, collector_number, variant, public_code, name "
            "FROM printings WHERE set_id = ?", (set_id,)
        ).fetchall()
        hit = 0
        for r in rows:
            bid = index.get(_rs_key(r["collector_number"], r["variant"]))
            if bid:
                pairs.append((r["printing_id"], bid, exp["id"], _now()))
                hit += 1
            else:
                missing.append((r["printing_id"], r["public_code"], r["name"]))
        log(f"  {set_id}: {hit}/{len(rows)} impressões mapeadas")
        time.sleep(0.5)             # a API permite 200/10s; não há pressa

    con.execute("BEGIN")
    con.execute("DELETE FROM cardtrader_map")
    con.executemany(
        "INSERT INTO cardtrader_map (printing_id, blueprint_id, expansion_id, mapped_at) "
        "VALUES (?,?,?,?)", pairs)
    con.execute("COMMIT")
    con.close()
    return {"mapped": len(pairs), "missing": missing, "sets_sem_expansao": sem_exp}


# ---------------------------------------------------------------------------
# Preços
# ---------------------------------------------------------------------------


def _usable(p: dict) -> bool:
    h = p.get("properties_hash") or {}
    return (not p.get("graded")
            and not p.get("on_vacation")
            and not h.get("altered")
            and not h.get("signed")
            and h.get("riftbound_language") == LANGUAGE
            and h.get("condition") in OK_CONDITIONS
            and p.get("price_currency") == "EUR"
            and (p.get("price_cents") or 0) > 0)


def lowest(products: list[dict]) -> tuple[int | None, bool, int]:
    """(preço em cêntimos, veio_de_foil, nº de ofertas utilizáveis)."""
    normal, foil = [], []
    for p in products:
        if not _usable(p):
            continue
        h = p.get("properties_hash") or {}
        (foil if h.get("riftbound_foil") else normal).append(p["price_cents"])
    if normal:
        return min(normal), False, len(normal) + len(foil)
    if foil:
        return min(foil), True, len(foil)
    return None, False, 0


def sync_prices(ct: CardTrader | None = None, log=print) -> dict:
    """Atualiza `price_latest` (todas) e `price_history` (só as que tenho)."""
    ct = ct or CardTrader()
    con = db.connect()
    today = date.today().isoformat()

    bp_to_printings: dict[int, list[str]] = {}
    exps: dict[int, set[int]] = {}
    for r in con.execute("SELECT printing_id, blueprint_id, expansion_id FROM catalog.cardtrader_map"):
        bp_to_printings.setdefault(r["blueprint_id"], []).append(r["printing_id"])
        exps.setdefault(r["expansion_id"], set()).add(r["blueprint_id"])
    if not bp_to_printings:
        con.close()
        raise CardTraderError("o mapa está vazio — corre primeiro `riftvault map`")

    # Impressões de interesse: as que ele TEM, mais as que os decks PEDEM.
    # Sem as segundas nunca haveria histórico das cartas que lhe faltam, e a
    # vista "a subir de preço" — que é sobre o que ainda vai comprar — ficava
    # sempre vazia. Continua longe das 1180: o vault.db vai para o Git.
    owned = {r["printing_id"] for r in con.execute(
        "SELECT printing_id FROM copies WHERE qty > 0 "
        "UNION "
        "SELECT p.printing_id FROM catalog.printings p "
        "WHERE p.variant_kind = 'base' AND p.card_key IN "
        "  (SELECT DISTINCT card_key FROM deck_cards)")}
    rows, sem_preco = [], 0

    for expansion_id in sorted(exps):
        log(f"  expansão {expansion_id}: a descarregar o mercado...")
        market = ct.marketplace(expansion_id)
        for bid in exps[expansion_id]:
            products = market.get(str(bid)) or market.get(bid) or []
            cents, from_foil, n = lowest(products)
            if cents is None:
                sem_preco += 1
            for pid in bp_to_printings[bid]:
                rows.append((pid, cents, "EUR", 1 if from_foil else 0, n, today, "cardtrader"))
        del market              # 45 MB por expansão; liberta antes da próxima
        log(f"  expansão {expansion_id}: {len(exps[expansion_id])} blueprints")
        time.sleep(1.0)

    con.execute("BEGIN")
    con.executemany(
        "INSERT INTO catalog.price_latest (printing_id, price_cents, currency, "
        "from_foil, n_listings, day, source) VALUES (?,?,?,?,?,?,?) "
        "ON CONFLICT(printing_id) DO UPDATE SET price_cents=excluded.price_cents, "
        "currency=excluded.currency, from_foil=excluded.from_foil, "
        "n_listings=excluded.n_listings, day=excluded.day, source=excluded.source",
        rows)

    # Histórico: só do que é meu, e só quando o valor muda face ao último
    # registo. Assim o vault.db não cresce em dias em que nada mexeu.
    gravadas = 0
    for pid, cents, cur, *_ in rows:
        if cents is None or pid not in owned:
            continue
        last = con.execute(
            "SELECT price_cents FROM prices.price_history WHERE printing_id = ? "
            "ORDER BY day DESC LIMIT 1", (pid,)).fetchone()
        if last and last["price_cents"] == cents:
            continue
        con.execute(
            "INSERT INTO prices.price_history (printing_id, day, price_cents, currency) "
            "VALUES (?,?,?,?) ON CONFLICT(printing_id, day) DO UPDATE SET "
            "price_cents=excluded.price_cents", (pid, today, cents, cur))
        gravadas += 1
    con.execute("COMMIT")

    val = collection_value(con)
    con.close()
    return {"printings": len(rows), "sem_preco": sem_preco,
            "historico_gravado": gravadas, "valor": val}


# ---------------------------------------------------------------------------
# Valor
# ---------------------------------------------------------------------------


def collection_value(con: sqlite3.Connection) -> dict:
    """Valor total da coleção: soma de quantidade x preço."""
    row = con.execute(
        "SELECT COALESCE(SUM(c.qty * p.price_cents), 0) AS cents, "
        "       COALESCE(SUM(CASE WHEN p.price_cents IS NULL THEN c.qty ELSE 0 END), 0) AS sem_preco, "
        "       COALESCE(SUM(c.qty), 0) AS copias, "
        # Quanto do total vem de cartas que o CardTrader só lista em foil. É
        # o número que diz se dá para confiar no total: como o riftvault não
        # distingue acabamentos, essas podem estar sobreavaliadas.
        "       COALESCE(SUM(CASE WHEN p.from_foil = 1 THEN c.qty * p.price_cents ELSE 0 END), 0) AS cents_foil, "
        "       COALESCE(SUM(CASE WHEN p.from_foil = 1 THEN c.qty ELSE 0 END), 0) AS copias_foil "
        "FROM copies c LEFT JOIN catalog.price_latest p ON p.printing_id = c.printing_id "
        "WHERE c.qty > 0"
    ).fetchone()
    day = con.execute("SELECT MAX(day) AS d FROM catalog.price_latest").fetchone()
    return {"cents": row["cents"] or 0, "currency": "EUR",
            "copias_sem_preco": row["sem_preco"] or 0, "copias": row["copias"] or 0,
            "cents_de_foil": row["cents_foil"] or 0, "copias_de_foil": row["copias_foil"] or 0,
            "day": day["d"] if day else None}


def value_by_set(con: sqlite3.Connection) -> dict[str, int]:
    rows = con.execute(
        "SELECT pr.set_id AS s, COALESCE(SUM(c.qty * p.price_cents), 0) AS cents "
        "FROM copies c "
        "JOIN catalog.printings pr ON pr.printing_id = c.printing_id "
        "LEFT JOIN catalog.price_latest p ON p.printing_id = c.printing_id "
        "WHERE c.qty > 0 GROUP BY pr.set_id"
    ).fetchall()
    return {r["s"]: r["cents"] or 0 for r in rows}


def top_value(con: sqlite3.Connection, limit: int = 15) -> list[dict]:
    rows = con.execute(
        "SELECT pr.public_code, pr.name, pr.variant_label, c.qty, p.price_cents, "
        "       c.qty * p.price_cents AS total, p.from_foil "
        "FROM copies c "
        "JOIN catalog.printings pr ON pr.printing_id = c.printing_id "
        "JOIN catalog.price_latest p ON p.printing_id = c.printing_id "
        "WHERE c.qty > 0 AND p.price_cents IS NOT NULL "
        "ORDER BY total DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def eur(cents: int | None) -> str:
    return "—" if cents is None else f"{cents / 100:.2f} €"

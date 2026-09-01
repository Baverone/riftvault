"""Encomendas a caminho.

Uma carta comprada mas ainda não recebida não está na coleção — mas também já
não é uma falta. Este módulo é a diferença entre as duas coisas: o `copies`
continua a medir o que está na caixa, e as faltas descontam o que vem a
caminho para ele não comprar duas vezes.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from . import collection


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def add(con: sqlite3.Connection, ref: str, qty: int,
        unit_cents: int | None = None, note: str | None = None) -> dict:
    """Regista uma compra a caminho. Valida a impressão como o resto do código."""
    printing_id = collection.resolve_printing(con, ref)
    cur = con.execute(
        "INSERT INTO pending (printing_id, qty, unit_cents, ordered_at, note) "
        "VALUES (?,?,?,?,?)", (printing_id, qty, unit_cents, _now(), note))
    return {"id": cur.lastrowid, "printing_id": printing_id, "qty": qty}


def open_qty(con: sqlite3.Connection) -> dict[str, int]:
    """printing_id -> quantas vêm a caminho e ainda não chegaram."""
    return {r["printing_id"]: r["q"] for r in con.execute(
        "SELECT printing_id, SUM(qty) AS q FROM pending "
        "WHERE arrived_at IS NULL GROUP BY printing_id")}


def open_by_card(con: sqlite3.Connection) -> dict[str, int]:
    """card_key -> quantas vêm a caminho. É o grão das faltas.

    Junta o catálogo e as `market_only` — ele comprou runas do SFD que a
    RiftScribe não tem, e essas contam na mesma.
    """
    out: dict[str, int] = {}
    for r in con.execute(
        "SELECT p.card_key AS k, SUM(pe.qty) AS q FROM pending pe "
        "JOIN catalog.printings p ON p.printing_id = pe.printing_id "
        "WHERE pe.arrived_at IS NULL GROUP BY p.card_key"
    ):
        out[r["k"]] = out.get(r["k"], 0) + r["q"]
    for r in con.execute(
        "SELECT m.card_key AS k, SUM(pe.qty) AS q FROM pending pe "
        "JOIN catalog.market_only m ON m.printing_id = pe.printing_id "
        "WHERE pe.arrived_at IS NULL AND m.card_key IS NOT NULL GROUP BY m.card_key"
    ):
        out[r["k"]] = out.get(r["k"], 0) + r["q"]
    return out


def listar(con: sqlite3.Connection, incluir_chegadas: bool = False) -> list[dict]:
    sql = (
        "SELECT pe.*, "
        "       COALESCE(p.name, m.market_name) AS name, "
        "       COALESCE(p.public_code, m.set_id || '-' || m.collector_raw) AS code, "
        "       COALESCE(p.set_id, m.set_id) AS set_id, "
        "       COALESCE(p.variant_label, 'Arte alt.') AS label, "
        "       (m.printing_id IS NOT NULL) AS market_only, "
        "       p.orientation, "
        # A imagem: do cache local quando a carta é do catálogo, do CardTrader
        # quando é `market_only` (as runas do SFD que ele comprou).
        "       CASE WHEN p.printing_id IS NULL THEN NULL "
        "            ELSE 'img/' || p.printing_id || '.webp' END AS img, "
        "       COALESCE(p.image_medium, p.image_large, p.image_url, m.image_url) AS cdn "
        "FROM pending pe "
        "LEFT JOIN catalog.printings p ON p.printing_id = pe.printing_id "
        "LEFT JOIN catalog.market_only m ON m.printing_id = pe.printing_id ")
    if not incluir_chegadas:
        sql += "WHERE pe.arrived_at IS NULL "
    sql += "ORDER BY COALESCE(p.set_id, m.set_id), name"
    out = []
    for r in con.execute(sql):
        d = dict(r)
        d["landscape"] = (d.pop("orientation", None) or "").lower() == "landscape"
        out.append(d)
    return out


def arrive(con: sqlite3.Connection, pending_id: int | None = None,
           source: str = "cli") -> list[dict]:
    """Marca como chegada e passa para a coleção.

    Sem `pending_id`, dá entrada em tudo o que está aberto. A entrada passa
    pelo `collection.adjust`, por isso fica no log e dá para desfazer.
    """
    sql = "SELECT * FROM pending WHERE arrived_at IS NULL"
    params: tuple = ()
    if pending_id:
        sql += " AND id = ?"
        params = (pending_id,)
    linhas = con.execute(sql, params).fetchall()

    feitas = []
    for r in linhas:
        res = collection.adjust(con, r["printing_id"], r["qty"], source=source)
        con.execute("UPDATE pending SET arrived_at = ? WHERE id = ?", (_now(), r["id"]))
        feitas.append({"id": r["id"], "printing_id": r["printing_id"],
                       "qty": r["qty"], "total": res["qty"]})
    return feitas


def totals(con: sqlite3.Connection) -> dict:
    r = con.execute(
        "SELECT COALESCE(SUM(qty),0) AS copias, COUNT(*) AS linhas, "
        "       COALESCE(SUM(qty * COALESCE(unit_cents,0)),0) AS cents "
        "FROM pending WHERE arrived_at IS NULL").fetchone()
    return {"copies": r["copias"], "lines": r["linhas"], "cents": r["cents"]}

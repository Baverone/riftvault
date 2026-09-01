"""Escrita na coleção: somar, subtrair, desfazer, histórico.

Regra central: **nunca se escreve um valor absoluto vindo do cliente**. O
cliente manda sempre um DELTA com um `request_id` único, e o servidor aplica
`qty = qty + delta` dentro de uma transação. É isto que garante as duas coisas
que o André pediu ao mesmo tempo:

  - cliques rápidos seguidos não perdem contagens (não há janela de debounce
    onde dois cliques colapsem num só);
  - um retry de rede não conta a dobrar (o `request_id` já está no log e a
    operação não se repete).
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone


class UnknownPrinting(LookupError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def resolve_printing(con: sqlite3.Connection, ref: str) -> str:
    """'OGN-100a', 'ogn-100a-298', 'OGN-301*', 'UNL-T03' -> printing_id.

    Valida contra o catálogo. Como não há FK entre bases de dados, é aqui que
    se garante que nunca entra na coleção uma impressão que não existe.
    """
    if not ref:
        raise UnknownPrinting("referência vazia")
    key = ref.strip().lower()

    row = con.execute(
        "SELECT printing_id FROM catalog.printings WHERE lower(printing_id) = ?", (key,)
    ).fetchone()
    if row:
        return row["printing_id"]

    row = con.execute(
        "SELECT printing_id FROM catalog.printing_aliases WHERE alias = ?", (key,)
    ).fetchone()
    if row:
        return row["printing_id"]

    raise UnknownPrinting(f"não encontrei nenhuma impressão para {ref!r}")


def get_qty(con: sqlite3.Connection, printing_id: str) -> int:
    row = con.execute("SELECT qty FROM copies WHERE printing_id = ?", (printing_id,)).fetchone()
    return row["qty"] if row else 0


def get_many(con: sqlite3.Connection) -> dict[str, int]:
    return {r["printing_id"]: r["qty"] for r in con.execute("SELECT printing_id, qty FROM copies")}


def adjust(con: sqlite3.Connection, ref: str, delta: int, source: str = "cli",
           request_id: str | None = None, _undo_of: int | None = None) -> dict:
    """Soma `delta` à impressão. Nunca desce abaixo de zero.

    Devolve {printing_id, qty, applied, op_id, duplicate}.
    """
    printing_id = resolve_printing(con, ref)

    if request_id:
        prev = con.execute(
            "SELECT id, qty_after, delta FROM ops WHERE request_id = ?", (request_id,)
        ).fetchone()
        if prev:
            # Já aplicámos este pedido. Devolve o mesmo resultado, sem repetir.
            return {"printing_id": printing_id, "qty": prev["qty_after"],
                    "applied": prev["delta"], "op_id": prev["id"], "duplicate": True}

    con.execute("BEGIN IMMEDIATE")
    try:
        current = get_qty(con, printing_id)
        applied = max(delta, -current)  # trava no zero
        new_qty = current + applied

        if applied == 0:
            con.execute("COMMIT")
            return {"printing_id": printing_id, "qty": current, "applied": 0,
                    "op_id": None, "duplicate": False}

        con.execute(
            "INSERT INTO copies (printing_id, qty, updated_at) VALUES (?,?,?) "
            "ON CONFLICT(printing_id) DO UPDATE SET qty = excluded.qty, "
            "updated_at = excluded.updated_at",
            (printing_id, new_qty, _now()),
        )
        cur = con.execute(
            "INSERT INTO ops (ts, printing_id, delta, qty_after, source, request_id, "
            "undone_at, undo_of) VALUES (?,?,?,?,?,?,?,?)",
            (_now(), printing_id, applied, new_qty, source, request_id,
             _now() if _undo_of else None, _undo_of),
        )
        op_id = cur.lastrowid
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise

    return {"printing_id": printing_id, "qty": new_qty, "applied": applied,
            "op_id": op_id, "duplicate": False}


def set_qty(con: sqlite3.Connection, ref: str, qty: int, source: str = "cli") -> dict:
    """Fixa a quantidade. Convertido para delta, para o log ficar coerente."""
    printing_id = resolve_printing(con, ref)
    return adjust(con, printing_id, qty - get_qty(con, printing_id), source=source)


def undo_op(con: sqlite3.Connection, op_id: int, source: str = "cli") -> dict | None:
    """Reverte uma operação concreta (é o que o toast do site usa)."""
    op = con.execute(
        "SELECT * FROM ops WHERE id = ? AND undone_at IS NULL", (op_id,)
    ).fetchone()
    if not op:
        return None

    res = adjust(con, op["printing_id"], -op["delta"], source=source, _undo_of=op["id"])
    con.execute("UPDATE ops SET undone_at = ? WHERE id = ?", (_now(), op["id"]))
    return {"undone_op": op["id"], **res}


def undo_last(con: sqlite3.Connection, source: str = "cli") -> dict | None:
    """Reverte a operação mais recente que ainda não foi revertida.

    Ignora as próprias operações de compensação, para que `undo` repetido ande
    para trás no histórico em vez de ficar a saltar entre as duas últimas.
    """
    op = con.execute(
        "SELECT id FROM ops WHERE undone_at IS NULL AND undo_of IS NULL ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if not op:
        return None
    return undo_op(con, op["id"], source=source)


def history(con: sqlite3.Connection, limit: int = 20) -> list[dict]:
    rows = con.execute(
        "SELECT o.id, o.ts, o.printing_id, o.delta, o.qty_after, o.source, "
        "       o.undone_at, o.undo_of, p.name, p.public_code, p.variant_label "
        "FROM ops o LEFT JOIN catalog.printings p ON p.printing_id = o.printing_id "
        "ORDER BY o.id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def totals(con: sqlite3.Connection) -> dict:
    row = con.execute(
        "SELECT COALESCE(SUM(qty),0) AS copies, COUNT(*) AS printings "
        "FROM copies WHERE qty > 0"
    ).fetchone()
    cards = con.execute(
        "SELECT COUNT(DISTINCT p.card_key) AS n FROM copies c "
        "JOIN catalog.printings p ON p.printing_id = c.printing_id WHERE c.qty > 0"
    ).fetchone()
    return {"copies": row["copies"], "printings": row["printings"], "cards": cards["n"]}

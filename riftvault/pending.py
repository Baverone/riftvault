"""Encomendas a caminho.

Uma carta comprada mas ainda não recebida não está na coleção — mas também já
não é uma falta. Este módulo é a diferença entre as duas coisas: o `copies`
continua a medir o que está na caixa, e as faltas descontam o que vem a
caminho para ele não comprar duas vezes.

OS `+`/`−` DOS DECKS (André, 2026-09-11): *"podes criar, nos decks, um botão de
+ e − que indique o que já está encomendado (comprado), mas que ainda não
chegou; assim consigo contigo organizar melhor as compras"*.

    É O MESMO MECANISMO, não um segundo. A tabela `pending` já existia (por
    impressão, uma linha por compra) e já descontava das faltas; o que faltava
    era escrever nela sem ser por Python. O `+` de uma carta num deck grava uma
    linha na impressão BASE mais barata dessa carta (`impressao_para_encomendar`
    — é onde ele a vai comprar, a mesma regra do «Falta comprar, por edição»);
    o `−` tira da linha aberta mais recente da carta, seja de que impressão
    for, e nunca vai abaixo de zero.

    A encomenda é da COLEÇÃO, não do deck: uma cópia encomendada serve o
    primeiro deck da prioridade que a peça, como qualquer outra cópia
    (`decks.allocate`, quarto monte `a_caminho`). O deck onde ele carregou no
    `+` fica só no rasto (`data/encomendas.log`), como origem do clique.

    «Chegou» passa a encomenda a cópia real pelo `collection.adjust` — fica no
    `ops`, dá para desfazer — e nunca dá entrada duas vezes: só apanha linhas
    com `arrived_at` a NULL.
"""

from __future__ import annotations

import csv
import io
import sqlite3
from datetime import datetime, timezone

from . import collection, config

# O rasto legível. Fica no `data/`, ao lado do `locais.log`, e é append-only.
LOG_NAME = "encomendas.log"
# O BOM escreve-se à mão na criação, pelo mesmo motivo do `locais.log`: o
# codec `utf-8-sig` punha um a cada `open(..., "a")`.
BOM = "﻿"


class SemEncomenda(Exception):
    """Um `−` sem nada a caminho dessa carta."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def add(con: sqlite3.Connection, ref: str, qty: int,
        unit_cents: int | None = None, note: str | None = None,
        source: str = "cli") -> dict:
    """Regista uma compra a caminho. Valida a impressão como o resto do código."""
    printing_id = collection.resolve_printing(con, ref)
    cur = con.execute(
        "INSERT INTO pending (printing_id, qty, unit_cents, ordered_at, note) "
        "VALUES (?,?,?,?,?)", (printing_id, qty, unit_cents, _now(), note))
    _log(con, [{"printing_id": printing_id, "qty": qty, "accao": "encomendar",
                "source": source, "nota": note}])
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


def _card_key(con: sqlite3.Connection, printing_id: str) -> str | None:
    row = con.execute(
        "SELECT card_key FROM catalog.printings WHERE printing_id = ?",
        (printing_id,)).fetchone()
    if row:
        return row["card_key"]
    row = con.execute(
        "SELECT card_key FROM catalog.market_only WHERE printing_id = ?",
        (printing_id,)).fetchone()
    return row["card_key"] if row else None


def impressao_para_encomendar(con: sqlite3.Connection,
                              card_keys) -> dict[str, dict]:
    """card_key -> a impressão em que o `+` grava a encomenda.

    A BASE MAIS BARATA, e sem preço a da edição mais antiga — é a regra do
    «Falta comprar, por edição» (`decks.missing_by_set`) e do `faltas._cheapest`:
    a impressão onde ele a vai comprar. Se um dia quiser encomendar outra
    versão, o `riftvault encomendas --mais OGN-045a` aceita qualquer código.
    """
    keys = list(dict.fromkeys(card_keys))
    if not keys:
        return {}
    ordens = {s: config.set_order(s) for s in
              (r["set_id"] for r in con.execute(
                  "SELECT DISTINCT set_id FROM catalog.printings"))}
    out: dict[str, dict] = {}
    ph = ",".join("?" * len(keys))
    for r in con.execute(
        f"SELECT p.card_key, p.printing_id, p.public_code, p.set_id, pl.price_cents "
        f"FROM catalog.printings p "
        f"LEFT JOIN catalog.price_latest pl ON pl.printing_id = p.printing_id "
        f"WHERE p.card_key IN ({ph}) AND p.variant_kind = 'base'", keys
    ):
        cand = {"id": r["printing_id"], "code": r["public_code"],
                "set": r["set_id"], "price": r["price_cents"]}
        rank = lambda c: (c["price"] is None,
                          c["price"] if c["price"] is not None else 0,
                          ordens.get(c["set"], 999), c["id"])
        atual = out.get(r["card_key"])
        if atual is None or rank(cand) < rank(atual):
            out[r["card_key"]] = cand
    return out


def encomendar(con: sqlite3.Connection, card_key: str | None = None,
               printing_id: str | None = None, qty: int = 1,
               source: str = "web", note: str | None = None) -> dict:
    """O `+`: mais `qty` cópias a caminho desta carta.

    Com `printing_id` grava nessa impressão; só com `card_key`, na base mais
    barata (`impressao_para_encomendar`). Devolve o que ficou aberto.
    """
    if qty <= 0:
        raise ValueError("a quantidade tem de ser positiva")
    if printing_id:
        printing_id = collection.resolve_printing(con, printing_id)
        card_key = _card_key(con, printing_id) or card_key
    else:
        if not card_key:
            raise ValueError("falta a carta")
        alvo = impressao_para_encomendar(con, [card_key]).get(card_key)
        if not alvo:
            raise collection.UnknownPrinting(
                f"não há impressão base de {card_key!r} no catálogo")
        printing_id = alvo["id"]
    con.execute("BEGIN IMMEDIATE")
    con.execute(
        "INSERT INTO pending (printing_id, qty, unit_cents, ordered_at, note) "
        "VALUES (?,?,?,?,?)", (printing_id, qty, None, _now(), note))
    con.execute("COMMIT")
    _log(con, [{"printing_id": printing_id, "qty": qty, "accao": "encomendar",
                "source": source, "nota": note}])
    return _estado(con, card_key, printing_id)


def anular(con: sqlite3.Connection, card_key: str | None = None,
           printing_id: str | None = None, qty: int = 1,
           source: str = "web") -> dict:
    """O `−`: menos `qty` a caminho. Tira das linhas abertas mais recentes.

    Com `printing_id` tira só dessa impressão; só com `card_key`, de qualquer
    impressão da carta. Nunca vai abaixo de zero: se não há nada aberto,
    `SemEncomenda`; se há menos do que `qty`, tira o que há e diz quanto.
    """
    if qty <= 0:
        raise ValueError("a quantidade tem de ser positiva")
    if printing_id:
        printing_id = collection.resolve_printing(con, printing_id)
        card_key = _card_key(con, printing_id) or card_key
        linhas = con.execute(
            "SELECT id, printing_id, qty FROM pending WHERE arrived_at IS NULL "
            "AND printing_id = ? ORDER BY id DESC", (printing_id,)).fetchall()
    else:
        if not card_key:
            raise ValueError("falta a carta")
        linhas = con.execute(
            "SELECT pe.id, pe.printing_id, pe.qty FROM pending pe "
            "LEFT JOIN catalog.printings p ON p.printing_id = pe.printing_id "
            "LEFT JOIN catalog.market_only m ON m.printing_id = pe.printing_id "
            "WHERE pe.arrived_at IS NULL AND COALESCE(p.card_key, m.card_key) = ? "
            "ORDER BY pe.id DESC", (card_key,)).fetchall()
    if not linhas:
        raise SemEncomenda(f"não há nada a caminho de {card_key or printing_id!r}")

    con.execute("BEGIN IMMEDIATE")
    falta, tiradas = qty, []
    for r in linhas:
        if falta <= 0:
            break
        tira = min(falta, r["qty"])
        if tira == r["qty"]:
            con.execute("DELETE FROM pending WHERE id = ?", (r["id"],))
        else:
            con.execute("UPDATE pending SET qty = qty - ? WHERE id = ?", (tira, r["id"]))
        falta -= tira
        tiradas.append({"printing_id": r["printing_id"], "qty": tira, "accao": "anular",
                        "source": source})
    con.execute("COMMIT")
    _log(con, tiradas)
    res = _estado(con, card_key, tiradas[-1]["printing_id"] if tiradas else printing_id)
    res["removed"] = qty - falta
    return res


def _estado(con: sqlite3.Connection, card_key: str | None, printing_id: str | None) -> dict:
    """O que ficou a caminho da carta e da impressão depois de um `+`/`−`."""
    return {
        "card_key": card_key, "printing_id": printing_id,
        "open_card": open_by_card(con).get(card_key, 0) if card_key else 0,
        "open_printing": open_qty(con).get(printing_id, 0) if printing_id else 0,
    }


def listar(con: sqlite3.Connection, incluir_chegadas: bool = False) -> list[dict]:
    sql = (
        "SELECT pe.*, "
        "       COALESCE(p.name, m.market_name) AS name, "
        "       COALESCE(p.public_code, m.set_id || '-' || m.collector_raw) AS code, "
        "       COALESCE(p.set_id, m.set_id) AS set_id, "
        "       COALESCE(p.card_key, m.card_key) AS card_key, "
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


def arrive(con: sqlite3.Connection, pending_id: int | list[int] | None = None,
           source: str = "cli", card_key: str | None = None) -> list[dict]:
    """Marca como chegada e passa para a coleção.

    Sem `pending_id` nem `card_key`, dá entrada em tudo o que está aberto; com
    `card_key`, em tudo o que está aberto dessa carta (o «Chegou» da linha do
    deck); com uma lista de ids, só nessas linhas (a tabela «Encomendas»). A
    entrada passa pelo `collection.adjust`, por isso fica no log e dá para
    desfazer. É idempotente por construção: só apanha linhas ainda sem
    `arrived_at`, e a segunda chamada não encontra nenhuma.
    """
    sql = ("SELECT pe.* FROM pending pe "
           "LEFT JOIN catalog.printings p ON p.printing_id = pe.printing_id "
           "LEFT JOIN catalog.market_only m ON m.printing_id = pe.printing_id "
           "WHERE pe.arrived_at IS NULL")
    params: tuple = ()
    if isinstance(pending_id, (list, tuple)):
        if not pending_id:
            return []
        sql += f" AND pe.id IN ({','.join('?' * len(pending_id))})"
        params = tuple(int(i) for i in pending_id)
    elif pending_id:
        sql += " AND pe.id = ?"
        params = (pending_id,)
    elif card_key:
        sql += " AND COALESCE(p.card_key, m.card_key) = ?"
        params = (card_key,)
    linhas = con.execute(sql + " ORDER BY pe.id", params).fetchall()

    feitas = []
    for r in linhas:
        res = collection.adjust(con, r["printing_id"], r["qty"], source=source)
        con.execute("UPDATE pending SET arrived_at = ? WHERE id = ?", (_now(), r["id"]))
        feitas.append({"id": r["id"], "printing_id": r["printing_id"],
                       "qty": r["qty"], "total": res["qty"]})
    _log(con, [{"printing_id": f["printing_id"], "qty": f["qty"], "accao": "chegou",
                "source": source} for f in feitas])
    return feitas


def totals(con: sqlite3.Connection) -> dict:
    r = con.execute(
        "SELECT COALESCE(SUM(qty),0) AS copias, COUNT(*) AS linhas, "
        "       COALESCE(SUM(qty * COALESCE(unit_cents,0)),0) AS cents "
        "FROM pending WHERE arrived_at IS NULL").fetchone()
    return {"copies": r["copias"], "lines": r["linhas"], "cents": r["cents"]}


# ---------------------------------------------------------------------------
# A lista «Encomendas»: o que está a caminho, para que deck vai, e o que ainda
# falta encomendar
# ---------------------------------------------------------------------------


def encomendas(con: sqlite3.Connection) -> dict:
    """Tudo o que está a caminho, por edição, com preço e destino; e o que
    ainda falta encomendar aos decks, por edição, com euros.

    É com isto que ele organiza as compras: `a_caminho` é o que já comprou
    (uma linha por impressão, as compras somadas), `para` diz que decks ficam
    com essas cópias na alocação por prioridade (`decks.allocate`, monte
    `a_caminho`), e `falta` é o `missing` dos decks DEPOIS das encomendas —
    a soma do «Falta comprar, por edição» de cada deck, que já as desconta.

    O preço é o de hoje no CardTrader, não o que ele pagou: o `+` do deck não
    sabe quanto custou (`unit_cents` fica a NULL). Quando o `unit_cents` existe
    (o `riftvault pending` antigo), vai em `paid` à parte.
    """
    from . import decks

    abertas = open_qty(con)
    itens = listar(con)
    precos = {r["printing_id"]: r["price_cents"] for r in con.execute(
        "SELECT printing_id, price_cents FROM catalog.price_latest "
        "WHERE price_cents IS NOT NULL")}
    ordens = {s: config.set_order(s) for s in
              (r["set_id"] for r in con.execute(
                  "SELECT DISTINCT set_id FROM catalog.printings"))}

    # Para que deck vai cada carta: o monte `a_caminho` da alocação, por
    # prioridade. É por carta lógica — a encomenda é da Coleção — e a lista
    # reparte-a pelas impressões pela ordem em que estão a caminho.
    # Por GRUPO de Legend, lido no líder (2026-09-11, noite): uma encomenda
    # para o LeBlanc é para o LeBlanc Baited Hook também, e o «para» diz os
    # dois nomes em vez de contar a cópia duas vezes.
    alloc = decks.allocate(con)
    para_carta: dict[str, list[dict]] = {}
    for d in decks.deck_rows(con):
        g = alloc[d["deck_id"]]["grupo"]
        if not g["lider"]:
            continue
        for ck, n in g["a_caminho"].items():
            para_carta.setdefault(ck, []).append(
                {"deck": g["rotulo"], "slug": d["name"],
                 "priority": d["priority"], "qty": n})

    por_impressao: dict[str, dict] = {}
    for it in itens:
        pid = it["printing_id"]
        e = por_impressao.get(pid)
        if e is None:
            e = por_impressao[pid] = {
                "printing_id": pid, "card_key": it["card_key"], "name": it["name"],
                "code": it["code"], "set": it["set_id"], "label": it["label"],
                "market_only": bool(it["market_only"]), "img": it["img"],
                "cdn": it["cdn"], "landscape": it["landscape"],
                "qty": 0, "price": precos.get(pid), "total": 0, "paid": 0,
                "ids": [], "notes": [],
            }
        e["qty"] += it["qty"]
        e["paid"] += (it["unit_cents"] or 0) * it["qty"]
        e["ids"].append(it["id"])
        if it["note"] and it["note"] not in e["notes"]:
            e["notes"].append(it["note"])
    sobra = {ck: list(v) for ck, v in para_carta.items()}
    for e in por_impressao.values():
        e["total"] = (e["price"] or 0) * e["qty"]
        # Que decks levam ESTAS cópias: consome-se a lista da carta pela ordem
        # de prioridade até esgotar a quantidade desta impressão.
        falta, dest = e["qty"], []
        for h in sobra.get(e["card_key"], []):
            if falta <= 0:
                break
            n = min(falta, h["qty"])
            if n:
                h["qty"] -= n
                falta -= n
                dest.append({"deck": h["deck"], "slug": h["slug"], "qty": n})
        e["para"] = dest
        # A caminho e nenhum deck a pede: fica na Coleção quando chegar.
        e["sem_deck"] = falta

    por_set: dict[str, dict] = {}
    for e in sorted(por_impressao.values(),
                    key=lambda x: (ordens.get(x["set"], 999), x["set"] or "",
                                   x["code"] or "")):
        d = por_set.setdefault(e["set"], {"set": e["set"], "name": config.set_name(e["set"]),
                                          "cards": 0, "copies": 0, "cents": 0,
                                          "paid": 0, "items": []})
        d["cards"] += 1
        d["copies"] += e["qty"]
        d["cents"] += e["total"]
        d["paid"] += e["paid"]
        d["items"].append(e)
    a_caminho = sorted(por_set.values(), key=lambda d: (ordens.get(d["set"], 999), d["set"] or ""))

    # O que AINDA falta encomendar: o «Falta comprar, por edição» de cada deck,
    # somado. Já desconta o que vem a caminho — é o `missing` da alocação.
    # Por grupo de Legend, uma vez: o que falta ao LeBlanc falta ao Baited
    # Hook, e é a mesma compra.
    falta_set: dict[str, dict] = {}
    for d in decks.deck_rows(con):
        g = alloc[d["deck_id"]]["grupo"]
        if not g["lider"]:
            continue
        for m in decks.missing_by_set(con, d["deck_id"], grupo=True):
            f = falta_set.setdefault(m["set"], {"set": m["set"], "name": m["name"],
                                                 "copies": 0, "cents": 0, "items": []})
            f["copies"] += m["copies"]
            f["cents"] += m["cents"]
            for it in m["items"]:
                f["items"].append({**it, "deck": g["rotulo"], "slug": d["name"]})
    falta = sorted(falta_set.values(), key=lambda d: (ordens.get(d["set"], 999), d["set"]))
    for f in falta:
        f["cards"] = len({it["card_key"] for it in f["items"]})
        f["items"].sort(key=lambda x: (-x["total"], x["name"]))

    return {
        "a_caminho": a_caminho,
        "totals": {
            "printings": len(por_impressao),
            "copies": sum(e["qty"] for e in por_impressao.values()),
            "cents": sum(e["total"] for e in por_impressao.values()),
            "paid": sum(e["paid"] for e in por_impressao.values()),
            "sem_preco": sum(1 for e in por_impressao.values() if e["price"] is None),
        },
        "falta": falta,
        "falta_totals": {
            "cards": len({it["card_key"] for f in falta for it in f["items"]}),
            "copies": sum(f["copies"] for f in falta),
            "cents": sum(f["cents"] for f in falta),
        },
    }


# ---------------------------------------------------------------------------
# Rasto
# ---------------------------------------------------------------------------


def _log(con: sqlite3.Connection, linhas: list[dict]) -> None:
    """Uma linha por movimento em `data/encomendas.log`. Nunca impede a escrita.

    É o gémeo do `locais.log`: se uma encomenda aparecer ou desaparecer sem
    linha aqui, é bug. Colunas: quando, impressão, código, nome, quantidade,
    acção (encomendar / anular / chegou), origem (web, cli, deck de onde veio o
    clique) e a nota.
    """
    if not linhas:
        return
    caminho = config.DATA_DIR / LOG_NAME
    novo = not caminho.exists()
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    if novo:
        w.writerow(["quando", "printing_id", "codigo", "nome", "quantidade",
                    "accao", "origem", "nota"])
    ts = _now()
    for x in linhas:
        d = _descrever(con, x["printing_id"])
        w.writerow([ts, x["printing_id"], d["code"] or "", d["name"] or "",
                    x["qty"], x["accao"], x.get("source") or "", x.get("nota") or ""])
    try:
        config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(caminho, "a", encoding="utf-8", newline="") as fh:
            if novo:
                fh.write(BOM)
            fh.write(buf.getvalue())
    except OSError:
        pass


def _descrever(con: sqlite3.Connection, printing_id: str) -> dict:
    row = con.execute(
        "SELECT public_code AS code, name FROM catalog.printings WHERE printing_id = ?",
        (printing_id,)).fetchone()
    if not row:
        row = con.execute(
            "SELECT set_id || '-' || collector_raw AS code, market_name AS name "
            "FROM catalog.market_only WHERE printing_id = ?", (printing_id,)).fetchone()
    return {"code": row["code"] if row else None, "name": row["name"] if row else None}

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

O SEPARADOR «ENCOMENDAS» (André, 2026-09-17): *"uma aba 'encomendas', em que
é igual à coleção, mas só tem de Raras para cima, e nas quais eu coloco o que
comprei (para não me perder), e assim que chegam, eu coloco lá que chegaram,
e acrescentas à coleção"* / *"e tiras esta funcionalidade dos decks"*.

    Os `+`/`−` saíram dos tiles dos decks e passaram a viver num separador
    próprio, que é a GRELHA DA COLEÇÃO (`grelha`: o `metrics.set_payload`
    tal e qual — as mesmas edições, blocos, tiles e ordem, tenha ele a carta
    ou não) cortada à raridade da base a partir de
    `encomendas.raridade_minima`, com o que vem a caminho por impressão
    (`ordered`) ao lado do que tem. O `+` grava NA IMPRESSÃO do tile — é ele
    que escolhe a versão que comprou —, o `−` tira dela, e o «Chegou» dá
    entrada dessa impressão (`arrive(printing_id=...)`). O registo é o mesmo
    de sempre, a `pending`: o «a caminho» dos decks, das Faltas e das
    wantlists lê daqui.
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

    Conta só o que pode SERVIR OS DECKS (`decks.Versoes.serve`): uma assinada
    ou uma runa em alt art (retirada, 2026-09-17) encomendada não conta para
    nada. É informação; quem desconta o pendente lugar a lugar (a versão
    especial da Legend/Champion não abate uma falta normal, nem o contrário)
    é a alocação, por impressão (`open_qty`).
    """
    from . import decks

    versoes = decks.versoes_dos_decks(con)
    out: dict[str, int] = {}
    for r in con.execute(
        "SELECT p.printing_id, p.card_key, p.card_key AS k, p.variant_kind, p.set_id, "
        "       SUM(pe.qty) AS q "
        "FROM pending pe "
        "JOIN catalog.printings p ON p.printing_id = pe.printing_id "
        "WHERE pe.arrived_at IS NULL GROUP BY p.printing_id"
    ):
        if versoes.serve(r):
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


def impressao_para_encomendar(con: sqlite3.Connection, card_keys,
                              especial: bool = False) -> dict[str, dict]:
    """card_key -> a impressão em que o `+` grava a encomenda.

    A NORMAL MAIS BARATA (a base, sem sobrenumeração; sem preço a da edição
    mais antiga) — ou, com `especial`, a VERSÃO ESPECIAL mais barata (alt
    art, sobrenumerada, promo), que é o que a Legend e o Champion jogam
    (2026-09-17, `decks.Versoes.compra`). É a regra do «Falta comprar, por
    edição» (`decks.missing_by_set`) e do `faltas._cheapest`: a impressão
    onde ele a vai comprar. Se um dia quiser encomendar outra versão, o
    `riftvault encomendas --mais OGN-045a` aceita qualquer código.
    """
    from . import decks

    keys = list(dict.fromkeys(card_keys))
    if not keys:
        return {}
    versoes = decks.versoes_dos_decks(con)
    out: dict[str, dict] = {}
    for ck in keys:
        pid = versoes.compra(ck, especial)
        if pid is None:
            continue
        i = versoes.info(pid)
        out[ck] = {"id": pid, "code": i["code"], "set": i["set"], "price": i["price"],
                   "especial": especial}
    return out


def encomendar(con: sqlite3.Connection, card_key: str | None = None,
               printing_id: str | None = None, qty: int = 1,
               source: str = "web", note: str | None = None,
               especial: bool = False) -> dict:
    """O `+`: mais `qty` cópias a caminho desta carta.

    Com `printing_id` grava nessa impressão; só com `card_key`, na normal
    mais barata — ou, com `especial`, na versão especial mais barata, que é o
    `+` da linha da Legend/Champion (`impressao_para_encomendar`). Devolve o
    que ficou aberto.
    """
    if qty <= 0:
        raise ValueError("a quantidade tem de ser positiva")
    if printing_id:
        printing_id = collection.resolve_printing(con, printing_id)
        card_key = _card_key(con, printing_id) or card_key
    else:
        if not card_key:
            raise ValueError("falta a carta")
        alvo = impressao_para_encomendar(con, [card_key], especial).get(card_key)
        if not alvo:
            raise collection.UnknownPrinting(
                f"não há impressão de {card_key!r} em que o deck compre"
                + (" a versão especial" if especial else ""))
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
           source: str = "web", especial: bool | None = None) -> dict:
    """O `−`: menos `qty` a caminho. Tira das linhas abertas mais recentes.

    Com `printing_id` tira só dessa impressão; só com `card_key`, de qualquer
    impressão da carta — ou, com `especial` `True`/`False`, só das versões
    especiais / só das normais (o `−` da linha da Legend/Champion não pode
    tirar a encomenda de uma cópia normal, nem o contrário; 2026-09-17).
    Nunca vai abaixo de zero: se não há nada aberto, `SemEncomenda`; se há
    menos do que `qty`, tira o que há e diz quanto.
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
            "SELECT pe.id, pe.printing_id, pe.qty, p.card_key FROM pending pe "
            "LEFT JOIN catalog.printings p ON p.printing_id = pe.printing_id "
            "LEFT JOIN catalog.market_only m ON m.printing_id = pe.printing_id "
            "WHERE pe.arrived_at IS NULL AND COALESCE(p.card_key, m.card_key) = ? "
            "ORDER BY pe.id DESC", (card_key,)).fetchall()
        if especial is not None:
            from . import decks

            versoes = decks.versoes_dos_decks(con)
            # Uma `market_only` (sem linha no catálogo) é sempre uma normal.
            linhas = [r for r in linhas
                      if (r["card_key"] is None and not especial)
                      or (r["card_key"] is not None and versoes.joga(r, especial=especial))]
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
           source: str = "cli", card_key: str | None = None,
           printing_id: str | None = None) -> list[dict]:
    """Marca como chegada e passa para a coleção.

    Sem `pending_id`, `card_key` nem `printing_id`, dá entrada em tudo o que
    está aberto (o «Chegou tudo»); com `printing_id`, em tudo o que está
    aberto dessa impressão (o «Chegou» do tile do separador «Encomendas»,
    2026-09-17); com `card_key`, em tudo o que está aberto dessa carta, seja
    de que impressão for; com uma lista de ids, só nessas linhas. A entrada
    passa pelo `collection.adjust`, por isso fica no log e dá para desfazer.
    É idempotente por construção: só apanha linhas ainda sem `arrived_at`, e
    a segunda chamada não encontra nenhuma.
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
    elif printing_id:
        sql += " AND pe.printing_id = ?"
        params = (collection.resolve_printing(con, printing_id),)
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
# O separador «Encomendas» (2026-09-17): a grelha da Coleção, de Rara para
# cima, com o que vem a caminho por impressão
# ---------------------------------------------------------------------------

# O que cada tile precisa. É o tile da Coleção (`tileHTML` no app.js) mais o
# `ordered`; o resto do `set_payload` (locais, `in_decks`, `sort`, `head`) não
# se lê aqui e ficava a pesar em cinco ficheiros que vão para o Git.
_CAMPOS_IMPRESSAO = ("id", "code", "kind", "label", "name", "rarity", "landscape",
                     "price", "qty", "qty_total", "target", "block", "img", "cdn")
_CAMPOS_GRUPO = ("key", "cn", "card_key", "name", "type", "rarity", "is_token",
                 "decks", "playset")


def raridade_minima(cfg: dict | None = None) -> str:
    cfg = cfg or config.load()
    return str((cfg.get("encomendas") or {}).get("raridade_minima") or "rare")


def raridades(cfg: dict | None = None) -> frozenset[str]:
    """As raridades que entram no separador: da `raridade_minima` para cima,
    na ordem do catálogo (`metrics.RARITY_ORDER`: common < uncommon < rare <
    epic < showcase). Uma raridade que o catálogo não conhece rebenta — como
    nas listas do `master_set`, um valor mal escrito não pode contar em
    silêncio."""
    from . import metrics

    minima = raridade_minima(cfg)
    if minima not in metrics.RARITY_ORDER:
        raise ValueError(
            f"encomendas.raridade_minima = {minima!r} não é uma raridade do catálogo "
            f"({', '.join(metrics.RARITY_ORDER)})")
    return frozenset(metrics.RARITY_ORDER[metrics.RARITY_ORDER.index(minima):])


def grelha(con: sqlite3.Connection, set_id: str, editable: bool = True,
           image_mode: str = "local", cfg: dict | None = None) -> dict:
    """A grelha de UMA edição para o separador «Encomendas».

    É o `metrics.set_payload` — os mesmos grupos, os mesmos blocos e a mesma
    ordem da Coleção, tenha ele a carta ou não — cortado pela raridade da
    BASE de cada carta (a mesma que a Coleção usa nos chips de raridade: a
    `showcase` de uma arte alternativa não muda a raridade da carta), com o
    que vem a caminho de cada impressão em `ordered`. O `qty` continua a ser
    o que está NA COLEÇÃO, como na grelha: encomendar não é ter.

    O que vier a caminho desta edição FORA da grelha — uma comum encomendada
    pela CLI, uma runa do CardTrader que a RiftScribe não tem — vai em
    `fora`, com nome e quantidade, para não haver encomenda que não se veja.
    """
    from . import metrics

    cfg = cfg or config.load()
    p = metrics.set_payload(con, set_id, editable=editable, image_mode=image_mode)
    abertas = open_qty(con)
    entram = raridades(cfg)

    groups: list[dict] = []
    na_grelha: set[str] = set()
    for g in p["groups"]:
        if (g["rarity"] or "") not in entram:
            continue
        prints = []
        for pr in g["printings"]:
            na_grelha.add(pr["id"])
            prints.append({**{k: pr[k] for k in _CAMPOS_IMPRESSAO},
                           "ordered": abertas.get(pr["id"], 0)})
        groups.append({**{k: g[k] for k in _CAMPOS_GRUPO}, "printings": prints})

    por_bloco: dict[str, list[int]] = {}
    for g in groups:
        for pr in g["printings"]:
            slot = por_bloco.setdefault(pr["block"], [0, 0, 0])
            slot[0] += 1
            slot[1] += pr["ordered"]
            slot[2] += 1 if pr["ordered"] else 0
    blocks = [
        {"id": b["id"], "label": b["label"], "short": b["short"], "counts": b["counts"],
         "printings": por_bloco[b["id"]][0], "ordered": por_bloco[b["id"]][1],
         "ordered_printings": por_bloco[b["id"]][2]}
        for b in p["blocks"] if b["id"] in por_bloco
    ]

    fora = [{"printing_id": it["printing_id"], "name": it["name"], "code": it["code"],
             "label": it["label"], "market_only": bool(it["market_only"]),
             "qty": it["qty"]}
            for it in listar(con)
            if it["set_id"] == set_id and it["printing_id"] not in na_grelha]
    # A mesma impressão pode ter várias linhas abertas: uma por compra.
    fora_por_pid: dict[str, dict] = {}
    for f in fora:
        e = fora_por_pid.get(f["printing_id"])
        if e is None:
            fora_por_pid[f["printing_id"]] = dict(f)
        else:
            e["qty"] += f["qty"]

    return {
        "editable": editable,
        "image_mode": image_mode,
        "generated_at": p["generated_at"],
        "set": p["set"],
        "price_badge_min": p["price_badge_min"],
        "rarity_min": raridade_minima(cfg),
        "rarities": [r for r in metrics.RARITY_ORDER if r in entram],
        "blocks": blocks,
        "groups": groups,
        "hidden_kinds": p["hidden_kinds"],
        "totals": {
            "cards": len(groups),
            "printings": sum(b["printings"] for b in blocks),
            "ordered": sum(b["ordered"] for b in blocks),
            "ordered_printings": sum(b["ordered_printings"] for b in blocks),
            # As impressões da página da Coleção que o corte tirou — para o
            # cabeçalho dizer «174 de 334».
            "printings_colecao": sum(len(g["printings"]) for g in p["groups"]),
        },
        "fora": sorted(fora_por_pid.values(), key=lambda x: (x["code"] or "", x["name"] or "")),
    }


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
        a = alloc[d["deck_id"]]
        g = a["grupo"]
        # Um deck DESMONTADO (2026-09-24) não recebe encomendas nem entra no
        # «falta encomendar»: não está a consumir nada.
        if not g["lider"] or not a["montado"]:
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
        a = alloc[d["deck_id"]]
        g = a["grupo"]
        if not g["lider"] or not a["montado"]:
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

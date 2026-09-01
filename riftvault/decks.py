"""Decks: leitura das listas, alocação por prioridade e validação.

A REGRA CENTRAL — ALOCAÇÃO POR PRIORIDADE
    Os decks têm uma ordem. Percorrem-se por essa ordem e cada um serve-se do
    que sobra: o deck 1 fica com as cartas que precisa, o deck 2 só recebe o
    que o deck 1 não levou. Uma carta que falte ao deck 2 por já estar noutro
    deck NÃO é o mesmo que uma carta que não se tem — a primeira diz onde está,
    a segunda vai para a lista de compras.

    É por isso que a alocação é global e não por deck: mudar a ordem muda quem
    fica com o quê.

FORMATO DAS LISTAS
    Secções com cabeçalho terminado em ':' (Legend, Champion, MainDeck,
    Battlefields, Rune Pool, Sideboard) e linhas "N Nome da Carta". Também
    aceita códigos, "3 OGN-045".
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from . import config

# Cabeçalhos aceites -> papel interno.
ROLES = {
    "legend": "legend",
    "champion": "champion",
    "maindeck": "main", "main deck": "main", "main": "main", "deck": "main",
    "battlefields": "battlefields", "battlefield": "battlefields",
    "rune pool": "runes", "runes": "runes", "rune": "runes",
    "sideboard": "sideboard", "side": "sideboard",
}

ROLE_LABEL = {
    "legend": "Legend", "champion": "Champion", "main": "Main deck",
    "battlefields": "Battlefields", "runes": "Runas", "sideboard": "Sideboard",
}
ROLE_ORDER = ["legend", "champion", "main", "battlefields", "runes", "sideboard"]

DEFAULT_RULES = {
    "main": 40,
    # Inferido das duas listas do André, que têm 39 no MainDeck + 1 Champion.
    # NÃO validado contra as regras oficiais — ver CLAUDE.md.
    "main_includes_champion": True,
    "runes": 12,
    "battlefields": 3,
    "max_copies": 3,
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def norm(name: str) -> str:
    s = unicodedata.normalize("NFKC", name or "").strip().casefold()
    return re.sub(r"\s+", " ", s)


# ---------------------------------------------------------------------------
# Leitura das listas
# ---------------------------------------------------------------------------


def parse(path: Path) -> dict:
    """Lê um .txt e devolve as linhas por papel, ainda sem resolver nomes."""
    text = path.read_text(encoding="utf-8")
    role, out = "main", []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("//"):
            continue
        if line.endswith(":"):
            head = norm(line[:-1])
            role = ROLES.get(head, head)
            continue
        m = re.match(r"^(\d+)\s*[xX]?\s+(.+?)\s*$", line)
        if m:
            out.append((role, int(m.group(1)), m.group(2)))

    # A lista é identificada pelo conteúdo, para reimportar não duplicar.
    body = "\n".join(f"{r}|{q}|{norm(n)}" for r, q, n in out)
    return {"path": str(path), "slug": path.stem, "lines": out,
            "content_hash": hashlib.sha256(body.encode()).hexdigest()[:16]}


def resolve(con: sqlite3.Connection, name: str, role: str) -> str | None:
    """Nome da lista -> card_key do catálogo. None se não casar."""
    k = norm(name)
    row = con.execute("SELECT card_key FROM catalog.cards WHERE card_key = ?", (k,)).fetchone()
    if row:
        return row["card_key"]

    # Código de impressão ("3 OGN-045").
    row = con.execute(
        "SELECT p.card_key FROM catalog.printing_aliases a "
        "JOIN catalog.printings p ON p.printing_id = a.printing_id WHERE a.alias = ?",
        (k,)).fetchone()
    if row:
        return row["card_key"]

    # As listas escrevem os Legends como "Azir, Emperor of the Sands", mas no
    # catálogo o Legend é só "Emperor of the Sands". Nenhum dos 49 Legends tem
    # vírgula no nome, por isso tirar o prefixo é seguro.
    alvo = k
    if "," in k:
        tail = norm(k.split(",", 1)[1])
        row = con.execute("SELECT card_key FROM catalog.cards WHERE card_key = ?",
                          (tail,)).fetchone()
        if row:
            return row["card_key"]
        alvo = tail

    # A RiftScribe põe sufixo nos Legends do OGS ("Wuju Bladesman - Starter")
    # para os distinguir. As listas escrevem o nome impresso, sem o sufixo.
    # Só se aceita quando há UMA carta a corresponder — senão era um palpite.
    cands = [r["card_key"] for r in con.execute(
        "SELECT card_key FROM catalog.cards WHERE card_key LIKE ?", (alvo + " - %",))]
    if len(cands) == 1:
        return cands[0]
    return None


def import_all(con: sqlite3.Connection, log=print) -> dict:
    """Lê decks/*.txt para as tabelas. Mantém a prioridade já definida."""
    files = sorted(config.DECKS_DIR.glob("*.txt"))
    seen, results = [], []

    # Prioridade já atribuída antes, por slug; decks novos vão para o fim.
    known = {r["path"]: r["priority"] for r in con.execute("SELECT path, priority FROM decks")}
    next_pri = max(list(known.values()) + [0]) + 1

    for path in files:
        d = parse(path)
        legend = champion = None
        rows, missing = [], []
        for role, qty, name in d["lines"]:
            ck = resolve(con, name, role)
            if ck is None:
                missing.append({"role": role, "qty": qty, "name": name})
                continue
            rows.append((role, ck, qty, name))
            if role == "legend" and legend is None:
                legend = name
            if role == "champion" and champion is None:
                champion = name

        # O separador chama-se pelo Legend + Champion, como o André pediu.
        display = " · ".join(x for x in (legend, champion) if x) or d["slug"]
        pri = known.get(str(path), next_pri)
        if str(path) not in known:
            next_pri += 1

        con.execute("BEGIN")
        con.execute(
            "INSERT INTO decks (name, path, content_hash, format, imported_at, "
            "priority, legend, champion, display_name, missing_json) "
            "VALUES (?,?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(name) DO UPDATE SET path=excluded.path, "
            "content_hash=excluded.content_hash, imported_at=excluded.imported_at, "
            "legend=excluded.legend, champion=excluded.champion, "
            "display_name=excluded.display_name, missing_json=excluded.missing_json",
            (d["slug"], str(path), d["content_hash"], "riftbound", _now(),
             pri, legend, champion, display, json.dumps(missing, ensure_ascii=False)))
        deck_id = con.execute("SELECT deck_id FROM decks WHERE name = ?",
                              (d["slug"],)).fetchone()["deck_id"]
        con.execute("DELETE FROM deck_cards WHERE deck_id = ?", (deck_id,))
        # Uma carta pode repetir-se no mesmo papel (raro, mas soma-se).
        agg: dict[tuple[str, str], list] = {}
        for role, ck, qty, raw in rows:
            slot = agg.setdefault((role, ck), [0, raw])
            slot[0] += qty
        con.executemany(
            "INSERT INTO deck_cards (deck_id, card_key, role, qty, raw_line) VALUES (?,?,?,?,?)",
            [(deck_id, ck, role, v[0], v[1]) for (role, ck), v in agg.items()])
        con.execute("COMMIT")

        seen.append(d["slug"])
        results.append({"slug": d["slug"], "display": display, "priority": pri,
                        "cards": len(rows), "missing": missing})
        log(f"  {display}  (prioridade {pri}, {len(rows)} linhas"
            + (f", {len(missing)} por casar" if missing else "") + ")")

    # Decks cujo ficheiro desapareceu saem — é assim que se apaga um deck.
    if seen:
        ph = ",".join("?" * len(seen))
        gone = [r["name"] for r in con.execute(
            f"SELECT name FROM decks WHERE name NOT IN ({ph})", seen)]
    else:
        gone = [r["name"] for r in con.execute("SELECT name FROM decks")]
    for name in gone:
        did = con.execute("SELECT deck_id FROM decks WHERE name = ?", (name,)).fetchone()["deck_id"]
        con.execute("DELETE FROM deck_cards WHERE deck_id = ?", (did,))
        con.execute("DELETE FROM decks WHERE deck_id = ?", (did,))
        log(f"  (removido: {name} — o ficheiro já não existe)")

    return {"decks": results, "removed": gone}


# ---------------------------------------------------------------------------
# Alocação por prioridade
# ---------------------------------------------------------------------------


def owned_by_card(con: sqlite3.Connection) -> dict[str, int]:
    return {r["k"]: r["n"] for r in con.execute(
        "SELECT p.card_key AS k, SUM(c.qty) AS n FROM copies c "
        "JOIN catalog.printings p ON p.printing_id = c.printing_id "
        "WHERE c.qty > 0 GROUP BY p.card_key")}


def owned_printings(con: sqlite3.Connection) -> dict[str, list[dict]]:
    """card_key -> impressões que tenho, para saber quais tirar da caixa."""
    out: dict[str, list[dict]] = {}
    for r in con.execute(
        "SELECT p.card_key AS k, p.printing_id, p.public_code, p.set_id, "
        "       p.variant_label, c.qty "
        "FROM copies c JOIN catalog.printings p ON p.printing_id = c.printing_id "
        "WHERE c.qty > 0 ORDER BY p.set_id, p.api_sort"
    ):
        out.setdefault(r["k"], []).append(
            {"id": r["printing_id"], "code": r["public_code"], "set": r["set_id"],
             "label": r["variant_label"], "qty": r["qty"]})
    return out


def printing_allocation(con: sqlite3.Connection) -> dict[str, list[dict]]:
    """printing_id -> [{deck, qty}]: que cópias FÍSICAS estão em cada deck.

    A alocação por prioridade é por carta lógica — diz "o Azir leva 3
    Brutalizer", não de que impressão. Aqui escolhe-se a impressão, e a regra é
    **artes base primeiro**: assim as alternativas e as signatures ficam no
    binder e o que sai para os decks são as cópias comuns.

    É isto que responde a "não encontro a carta no binder, onde está?".
    """
    alloc = allocate(con)

    livre: dict[str, int] = {}
    por_carta: dict[str, list[str]] = {}
    ordens = {s: config.set_order(s) for s in
              (r["set_id"] for r in con.execute("SELECT DISTINCT set_id FROM catalog.printings"))}
    rows = con.execute(
        "SELECT c.printing_id, c.qty, p.card_key, p.variant_kind, p.set_id, p.api_sort "
        "FROM copies c JOIN catalog.printings p ON p.printing_id = c.printing_id "
        "WHERE c.qty > 0").fetchall()
    for r in sorted(rows, key=lambda r: (0 if r["variant_kind"] == "base" else 1,
                                         ordens.get(r["set_id"], 999), r["api_sort"])):
        livre[r["printing_id"]] = r["qty"]
        por_carta.setdefault(r["card_key"], []).append(r["printing_id"])

    out: dict[str, list[dict]] = {}
    for d in deck_rows(con):
        nome = d["display_name"] or d["name"]
        for ck, n in alloc[d["deck_id"]]["alloc"].items():
            falta = n
            for pid in por_carta.get(ck, []):
                if falta <= 0:
                    break
                tira = min(falta, livre.get(pid, 0))
                if tira:
                    livre[pid] -= tira
                    falta -= tira
                    out.setdefault(pid, []).append({"deck": nome, "qty": tira,
                                                    "priority": d["priority"]})
    return out


def deck_rows(con: sqlite3.Connection) -> list[sqlite3.Row]:
    return con.execute(
        "SELECT deck_id, name, display_name, legend, champion, priority, "
        "       path, missing_json FROM decks ORDER BY priority, deck_id").fetchall()


def allocate(con: sqlite3.Connection) -> dict:
    """Distribui as cópias pelos decks, por ordem de prioridade.

    Devolve, por deck e por carta: quanto pede, quanto ficou alocado, quanto
    falta, e — quando falta por estar noutro deck — em que deck está.
    """
    pool = owned_by_card(con)
    decks = deck_rows(con)
    held: dict[str, list[dict]] = {}     # card_key -> decks que já a levaram
    out = {}

    for d in decks:
        # A alocação é por carta lógica, não por papel: uma carta que esteja no
        # main e no sideboard disputa o mesmo stock.
        need: dict[str, int] = {}
        for r in con.execute(
            "SELECT card_key, SUM(qty) AS q FROM deck_cards WHERE deck_id = ? "
            "GROUP BY card_key", (d["deck_id"],)
        ):
            need[r["card_key"]] = r["q"]

        alloc, shared, missing = {}, {}, {}
        for ck, qty in need.items():
            take = min(qty, pool.get(ck, 0))
            if take:
                pool[ck] = pool.get(ck, 0) - take
                alloc[ck] = take
                held.setdefault(ck, []).append(
                    {"deck": d["display_name"] or d["name"], "qty": take,
                     "priority": d["priority"]})
            falta = qty - take
            if falta:
                # Está noutro deck, ou não a tenho de todo?
                noutro = [h for h in held.get(ck, []) if h["deck"] != (d["display_name"] or d["name"])]
                if noutro:
                    shared[ck] = {"qty": falta, "em": noutro}
                else:
                    missing[ck] = falta
        out[d["deck_id"]] = {"alloc": alloc, "shared": shared, "missing": missing}

    return out


# ---------------------------------------------------------------------------
# Payloads
# ---------------------------------------------------------------------------


def missing_by_set(con: sqlite3.Connection, deck_id: int) -> list[dict]:
    """Cópias em falta neste deck, por edição onde as ir buscar.

    Cada carta é atribuída à edição onde sai **mais barata** — é a decisão
    prática, porque é onde ele a vai comprar. Uma carta que exista em mais do
    que uma edição fica contada só uma vez, na mais barata, e é assinalada em
    `multi` para o número não parecer mais firme do que é.

    Não inclui as que faltam por estarem noutro deck: essas não se compram.
    """
    falta = allocate(con)[deck_id]["missing"]
    if not falta:
        return []

    ordens = {s: config.set_order(s) for s in
              (r["set_id"] for r in con.execute("SELECT DISTINCT set_id FROM catalog.printings"))}
    nomes = {r["card_key"]: r["name"] for r in con.execute(
        "SELECT card_key, name FROM catalog.cards")}
    opcoes: dict[str, list[dict]] = {}
    ph = ",".join("?" * len(falta))
    for r in con.execute(
        f"SELECT p.card_key, p.set_id, p.printing_id, p.public_code, p.orientation, "
        f"       p.image_medium, p.image_large, p.image_url, pl.price_cents "
        f"FROM catalog.printings p "
        f"LEFT JOIN catalog.price_latest pl ON pl.printing_id = p.printing_id "
        f"WHERE p.card_key IN ({ph}) AND p.variant_kind = 'base'", list(falta)
    ):
        opcoes.setdefault(r["card_key"], []).append({
            "set": r["set_id"], "price": r["price_cents"], "id": r["printing_id"],
            "code": r["public_code"],
            "landscape": (r["orientation"] or "").lower() == "landscape",
            "cdn": r["image_medium"] or r["image_large"] or r["image_url"],
        })

    por_set: dict[str, dict] = {}
    for ck, n in falta.items():
        cands = opcoes.get(ck) or []
        if not cands:
            continue
        sets = {c["set"] for c in cands}
        # Mais barata primeiro; sem preço, a edição mais antiga.
        melhor = min(cands, key=lambda c: (c["price"] is None,
                                           c["price"] if c["price"] is not None else 0,
                                           ordens.get(c["set"], 999)))
        d = por_set.setdefault(melhor["set"], {"set": melhor["set"], "cards": 0,
                                               "copies": 0, "cents": 0, "multi": 0,
                                               "items": []})
        d["cards"] += 1
        d["copies"] += n
        d["cents"] += (melhor["price"] or 0) * n
        if len(sets) > 1:
            d["multi"] += 1
        d["items"].append({
            "card_key": ck, "name": nomes.get(ck, ck), "qty": n,
            "code": melhor["code"], "price": melhor["price"],
            "total": (melhor["price"] or 0) * n,
            "img": f"img/{melhor['id']}.webp", "cdn": melhor["cdn"],
            "landscape": melhor["landscape"],
            # Existe noutras edições — dá para a ires buscar a outro lado.
            "also": sorted(sets - {melhor["set"]}),
        })

    out = list(por_set.values())
    for d in out:
        d["name"] = config.set_name(d["set"])
        d["items"].sort(key=lambda x: (-x["total"], x["name"]))
    # Por ordem de lançamento, não por quantidade: é a mesma ordem dos
    # separadores das edições, e vem do `order` no riftvault_config.json.
    out.sort(key=lambda d: (config.set_order(d["set"]), d["set"]))
    return out


def rules() -> dict:
    r = dict(DEFAULT_RULES)
    r.update(config.load().get("deck_rules", {}))
    return r


def decks_index(con: sqlite3.Connection) -> list[dict]:
    alloc = allocate(con)
    out = []
    for d in deck_rows(con):
        a = alloc[d["deck_id"]]
        pedidas = con.execute(
            "SELECT COALESCE(SUM(qty),0) AS q FROM deck_cards WHERE deck_id = ?",
            (d["deck_id"],)).fetchone()["q"]
        tenho = sum(a["alloc"].values())
        out.append({
            "id": d["deck_id"], "slug": d["name"],
            "name": d["display_name"] or d["name"],
            "legend": d["legend"], "champion": d["champion"],
            "priority": d["priority"],
            "wanted": pedidas, "have": tenho,
            "missing": sum(a["missing"].values()),
            "shared": sum(v["qty"] for v in a["shared"].values()),
        })
    return out


def deck_payload(con: sqlite3.Connection, deck_id: int) -> dict | None:
    d = con.execute("SELECT * FROM decks WHERE deck_id = ?", (deck_id,)).fetchone()
    if not d:
        return None
    a = allocate(con)[deck_id]
    prints = owned_printings(con)
    names = {r["card_key"]: r for r in con.execute(
        "SELECT card_key, name, type, domains_json FROM catalog.cards")}

    # Imagem por carta: a impressão representativa do catálogo. Se ele tiver a
    # carta, vale mais mostrar a arte que tem em casa do que a canónica.
    arte = {r["card_key"]: r for r in con.execute(
        "SELECT c.card_key, p.printing_id, p.public_code, p.orientation, "
        "       p.image_medium, p.image_large, p.image_url "
        "FROM catalog.cards c JOIN catalog.printings p "
        "ON p.printing_id = c.rep_printing_id")}
    por_id = {r["printing_id"]: r for r in con.execute(
        "SELECT printing_id, public_code, orientation, image_medium, image_large, image_url "
        "FROM catalog.printings")}

    def imagem(card_key: str) -> dict:
        tenho = prints.get(card_key)
        r = por_id.get(tenho[0]["id"]) if tenho else arte.get(card_key)
        if not r:
            return {"img": None, "cdn": None, "landscape": False, "code": None}
        return {
            "img": f"img/{r['printing_id']}.webp",
            "cdn": r["image_medium"] or r["image_large"] or r["image_url"],
            "landscape": (r["orientation"] or "").lower() == "landscape",
            "code": r["public_code"],
        }

    # Quanto de cada carta já foi consumido por papéis anteriores deste deck:
    # a alocação é por carta, mas mostra-se por papel.
    usado: dict[str, int] = {}
    sections = []
    for role in ROLE_ORDER:
        rows = con.execute(
            "SELECT card_key, qty, raw_line FROM deck_cards WHERE deck_id = ? AND role = ? "
            "ORDER BY raw_line", (deck_id, role)).fetchall()
        if not rows:
            continue
        cards = []
        for r in rows:
            ck = r["card_key"]
            disponivel = max(0, a["alloc"].get(ck, 0) - usado.get(ck, 0))
            tenho = min(r["qty"], disponivel)
            usado[ck] = usado.get(ck, 0) + tenho
            falta = r["qty"] - tenho
            info = names.get(ck) or {}
            cards.append({
                "card_key": ck,
                "name": (info["name"] if info else r["raw_line"]),
                "raw": r["raw_line"],
                "type": info["type"] if info else None,
                "wanted": r["qty"], "have": tenho, "missing": falta,
                "shared": a["shared"].get(ck) if falta else None,
                "printings": prints.get(ck, []),
                **imagem(ck),
            })
        sections.append({"role": role, "label": ROLE_LABEL[role], "cards": cards,
                         "wanted": sum(c["wanted"] for c in cards),
                         "have": sum(c["have"] for c in cards)})

    return {
        "id": deck_id, "slug": d["name"], "name": d["display_name"] or d["name"],
        "legend": d["legend"], "champion": d["champion"], "priority": d["priority"],
        "sections": sections,
        "missing_by_set": missing_by_set(con, deck_id),
        "legality": legality(con, deck_id),
        "unresolved": json.loads(d["missing_json"] or "[]"),
    }


def legality(con: sqlite3.Connection, deck_id: int) -> dict:
    """Validação contra as regras do config. NÃO são as regras oficiais."""
    r = rules()
    counts = {row["role"]: row["q"] for row in con.execute(
        "SELECT role, COALESCE(SUM(qty),0) AS q FROM deck_cards WHERE deck_id = ? "
        "GROUP BY role", (deck_id,))}

    main = counts.get("main", 0) + (counts.get("champion", 0)
                                    if r["main_includes_champion"] else 0)
    excesso = [row["card_key"] for row in con.execute(
        "SELECT card_key, SUM(qty) AS q FROM deck_cards WHERE deck_id = ? "
        "AND role IN ('main','champion') GROUP BY card_key HAVING q > ?",
        (deck_id, r["max_copies"]))]

    # Identidade de domínio: o Legend manda.
    legend_dom = con.execute(
        "SELECT c.domains_json FROM deck_cards d JOIN catalog.cards c "
        "ON c.card_key = d.card_key WHERE d.deck_id = ? AND d.role = 'legend'",
        (deck_id,)).fetchone()
    dominios = set(json.loads(legend_dom["domains_json"])) if legend_dom else set()
    fora = []
    if dominios:
        for row in con.execute(
            "SELECT c.name, c.domains_json FROM deck_cards d "
            "JOIN catalog.cards c ON c.card_key = d.card_key "
            "WHERE d.deck_id = ? AND d.role IN ('main','champion','runes','sideboard')",
            (deck_id,)
        ):
            dom = set(json.loads(row["domains_json"] or "[]"))
            if dom and not dom <= dominios | {"Colorless"}:
                fora.append({"name": row["name"], "domains": sorted(dom)})

    return {
        "main": {"n": main, "alvo": r["main"], "ok": main == r["main"]},
        "runes": {"n": counts.get("runes", 0), "alvo": r["runes"],
                  "ok": counts.get("runes", 0) == r["runes"]},
        "battlefields": {"n": counts.get("battlefields", 0), "alvo": r["battlefields"],
                         "ok": counts.get("battlefields", 0) == r["battlefields"]},
        "max_copies": {"alvo": r["max_copies"], "excesso": excesso, "ok": not excesso},
        "dominios": {"legend": sorted(dominios), "fora": fora, "ok": not fora},
        "main_inclui_champion": r["main_includes_champion"],
    }


def set_order(con: sqlite3.Connection, ordered_ids: list[int]) -> None:
    """Reordena os decks. O primeiro da lista passa a ser o principal."""
    con.execute("BEGIN")
    for i, deck_id in enumerate(ordered_ids, start=1):
        con.execute("UPDATE decks SET priority = ? WHERE deck_id = ?", (i, deck_id))
    con.execute("COMMIT")


def shopping_list(con: sqlite3.Connection, deck_id: int | None = None) -> list[dict]:
    """O que falta comprar. Sem deck_id, junta todos os decks."""
    alloc = allocate(con)
    prices = {r["printing_id"]: r["price_cents"] for r in con.execute(
        "SELECT printing_id, price_cents FROM catalog.price_latest "
        "WHERE price_cents IS NOT NULL")}
    barato: dict[str, int] = {}
    for r in con.execute("SELECT card_key, printing_id FROM catalog.printings"):
        p = prices.get(r["printing_id"])
        if p is not None:
            k = r["card_key"]
            barato[k] = min(barato.get(k, p), p)

    names = {r["card_key"]: r["name"] for r in con.execute(
        "SELECT card_key, name FROM catalog.cards")}
    juntos: dict[str, int] = {}
    for d in deck_rows(con):
        if deck_id and d["deck_id"] != deck_id:
            continue
        for ck, q in alloc[d["deck_id"]]["missing"].items():
            juntos[ck] = max(juntos.get(ck, 0), q) if deck_id else juntos.get(ck, 0) + q

    return sorted(
        [{"card_key": ck, "name": names.get(ck, ck), "qty": q,
          "price_cents": barato.get(ck), "total_cents": (barato.get(ck) or 0) * q}
         for ck, q in juntos.items()],
        key=lambda x: -x["total_cents"])

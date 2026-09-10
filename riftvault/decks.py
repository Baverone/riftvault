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
    """card_key -> cópias FÍSICAS, de todos os locais.

    Continua a ser o total: é o "quantas destas cartas tenho ao todo" que o
    Pimp e a métrica de playset jogável perguntam. Quem quer saber o que está
    DISPONÍVEL para montar decks chama o `pool_dos_decks` — desde 2026-09-10
    são duas perguntas diferentes.
    """
    return {r["k"]: r["n"] for r in con.execute(
        "SELECT p.card_key AS k, SUM(c.qty) AS n FROM copies c "
        "JOIN catalog.printings p ON p.printing_id = c.printing_id "
        "WHERE c.qty > 0 GROUP BY p.card_key")}


def _por_carta(con: sqlite3.Connection, mapa: dict[str, int]) -> dict[str, int]:
    """{printing_id: qty} -> {card_key: qty}, somando as impressões."""
    chaves = {r["printing_id"]: r["card_key"] for r in con.execute(
        "SELECT printing_id, card_key FROM catalog.printings")}
    out: dict[str, int] = {}
    for pid, n in mapa.items():
        ck = chaves.get(pid)
        if ck:
            out[ck] = out.get(ck, 0) + n
    return out


def pool_dos_decks(con: sqlite3.Connection) -> dict:
    """O que está DISPONÍVEL para montar decks (André, 2026-09-10).

    *"As cartas dos decks ficam em decks, e haverá um Binder que será apenas e
    exclusivamente para Decks/Venda."* Os decks montam-se com duas coisas:

      `fixo[slug][card_key]` — o que já está sleevado NAQUELE deck. Não anda:
                               é daquele deck e de mais nenhum.
      `binder[card_key]`     — o binder Decks/Venda, que é o stock livre. É este
                               que se distribui por prioridade.

    A COLEÇÃO NÃO ENTRA. Uma cópia que esteja nos binders de coleção não se
    usa para montar um deck — é a metade da frase dele que dá nome a isto tudo.
    Ela aparece na mesma na página do deck, em `na_colecao`, para ele decidir se
    a move ou se compra outra.
    """
    from . import locais

    fixo = {slug: _por_carta(con, mapa) for slug, mapa in locais.por_deck(con).items()}
    return {
        "fixo": fixo,
        "binder": _por_carta(con, locais.em(con, locais.BINDER)),
        "colecao": _por_carta(con, locais.na_colecao(con)),
    }


def owned_printings(con: sqlite3.Connection,
                    locais_ok: set[str] | None = None) -> dict[str, list[dict]]:
    """card_key -> impressões que tenho, para saber quais tirar da caixa.

    `locais_ok` limita a resposta a locais concretos (ex.: só o deck e o binder
    Decks/Venda). Sem ele são as cópias todas, esteja onde estiverem.
    """
    from . import locais as locais_mod

    onde = locais_mod.por_local(con) if locais_ok is not None else {}
    out: dict[str, list[dict]] = {}
    for r in con.execute(
        "SELECT p.card_key AS k, p.printing_id, p.public_code, p.set_id, "
        "       p.variant_label, c.qty "
        "FROM copies c JOIN catalog.printings p ON p.printing_id = c.printing_id "
        "WHERE c.qty > 0 ORDER BY p.set_id, p.api_sort"
    ):
        qty = r["qty"]
        if locais_ok is not None:
            qty = sum(n for loc, n in (onde.get(r["printing_id"]) or {}).items()
                      if loc in locais_ok)
            if qty <= 0:
                continue
        out.setdefault(r["k"], []).append(
            {"id": r["printing_id"], "code": r["public_code"], "set": r["set_id"],
             "label": r["variant_label"], "qty": qty})
    return out


def printing_allocation(con: sqlite3.Connection) -> dict[str, list[dict]]:
    """printing_id -> [{deck, qty}]: que cópias FÍSICAS estão em cada deck.

    Desde 2026-09-10 isto **lê-se, não se adivinha**: o local de cada cópia está
    na `copy_locations` e é ele que responde. Antes era uma heurística (a
    alocação por prioridade, com artes base primeiro) porque não havia onde
    guardar a verdade; agora há, e a heurística passou a viver só na PROPOSTA
    que ele confirma (`locais.propor_deck`).

    É isto que responde a "não encontro a carta no binder, onde está?".
    """
    from . import locais

    nomes = locais.nomes_dos_decks(con)
    prios = {r["name"]: r["priority"] for r in deck_rows(con)}
    out: dict[str, list[dict]] = {}
    for slug, mapa in sorted(locais.por_deck(con).items(),
                             key=lambda kv: (prios.get(kv[0], 999), kv[0])):
        for pid, n in mapa.items():
            out.setdefault(pid, []).append(
                {"deck": nomes.get(slug) or slug, "slug": slug, "qty": n,
                 "priority": prios.get(slug, 999)})
    return out


def binder_allocation(con: sqlite3.Connection) -> dict[str, list[dict]]:
    """printing_id -> [{deck, qty}] das cópias do BINDER Decks/Venda que os
    decks pedem.

    A alocação é por carta lógica; aqui escolhe-se a impressão, com **artes base
    primeiro** — a mesma regra de sempre, e a certa: se ele tem a base e a alt
    art no binder e um deck só precisa de uma, é a base que vai jogar e a alt
    art que fica para venda.

    O que sobra depois disto é o que a Venda propõe: *cópias no binder que
    nenhum deck pede* (André, 2026-09-10).
    """
    from . import locais

    alloc = allocate(con)
    livre = locais.em(con, locais.BINDER)
    ordens = {s: config.set_order(s) for s in
              (r["set_id"] for r in con.execute(
                  "SELECT DISTINCT set_id FROM catalog.printings"))}
    por_carta: dict[str, list[str]] = {}
    for r in sorted(con.execute(
        "SELECT printing_id, card_key, variant_kind, set_id, api_sort "
        "FROM catalog.printings").fetchall(),
        key=lambda r: (0 if r["variant_kind"] == "base" else 1,
                       ordens.get(r["set_id"], 999), r["api_sort"])
    ):
        if livre.get(r["printing_id"], 0) > 0:
            por_carta.setdefault(r["card_key"], []).append(r["printing_id"])

    out: dict[str, list[dict]] = {}
    for d in deck_rows(con):
        nome = d["display_name"] or d["name"]
        for ck, n in alloc[d["deck_id"]]["no_binder"].items():
            falta = n
            for pid in por_carta.get(ck, []):
                if falta <= 0:
                    break
                tira = min(falta, livre.get(pid, 0))
                if tira:
                    livre[pid] -= tira
                    falta -= tira
                    out.setdefault(pid, []).append(
                        {"deck": nome, "slug": d["name"], "qty": tira,
                         "priority": d["priority"]})
    return out


def deck_rows(con: sqlite3.Connection) -> list[sqlite3.Row]:
    return con.execute(
        "SELECT deck_id, name, display_name, legend, champion, priority, "
        "       path, missing_json FROM decks ORDER BY priority, deck_id").fetchall()


def allocate(con: sqlite3.Connection) -> dict:
    """Distribui as cópias pelos decks, por ordem de prioridade.

    Desde 2026-09-10 há DOIS montes, e só eles (ver `pool_dos_decks`):

      1. o que já está sleevado NESTE deck (`no_deck`) — não anda, é dele;
      2. o binder Decks/Venda (`no_binder`) — o stock livre, distribuído por
         prioridade, exactamente como antes.

    **A Coleção não entra.** Uma cópia nos binders de coleção não monta deck
    nenhum; aparece em `na_colecao` para ele decidir se a move ou se compra
    outra — *"duplicado a comprar ou a decidir"*.

    Devolve, por deck e por carta: quanto ficou alocado (e de onde), quanto está
    noutro deck, quanto está na Coleção, quanto falta comprar, e o que está
    marcado neste deck mas o deck já não pede (`extra`).
    """
    p = pool_dos_decks(con)
    binder = dict(p["binder"])
    colecao = dict(p["colecao"])
    decks = deck_rows(con)
    held: dict[str, list[dict]] = {}     # card_key -> decks que já a levaram
    out = {}

    for d in decks:
        nome = d["display_name"] or d["name"]
        fixo = dict(p["fixo"].get(d["name"]) or {})
        # A alocação é por carta lógica, não por papel: uma carta que esteja no
        # main e no sideboard disputa o mesmo stock.
        need: dict[str, int] = {}
        for r in con.execute(
            "SELECT card_key, SUM(qty) AS q FROM deck_cards WHERE deck_id = ? "
            "GROUP BY card_key", (d["deck_id"],)
        ):
            need[r["card_key"]] = r["q"]

        alloc, no_deck, no_binder = {}, {}, {}
        shared, na_colecao, missing = {}, {}, {}
        for ck, qty in need.items():
            do_deck = min(qty, fixo.get(ck, 0))
            fixo[ck] = fixo.get(ck, 0) - do_deck
            do_binder = min(qty - do_deck, binder.get(ck, 0))
            binder[ck] = binder.get(ck, 0) - do_binder

            take = do_deck + do_binder
            if take:
                alloc[ck] = take
                if do_deck:
                    no_deck[ck] = do_deck
                if do_binder:
                    no_binder[ck] = do_binder
                held.setdefault(ck, []).append(
                    {"deck": nome, "qty": take, "priority": d["priority"],
                     "onde": "deck"})

            falta = qty - take
            if not falta:
                continue
            # Está na Coleção? Existe, mas é coleção — não monta o deck. Vai
            # para o balde próprio e CONSOME-SE, senão dois decks reclamavam a
            # mesma cópia; e entra no `held`, para o deck seguinte ver que ela
            # já está reservada em vez de a mandar comprar.
            tem = min(falta, colecao.get(ck, 0))
            if tem:
                colecao[ck] = colecao.get(ck, 0) - tem
                na_colecao[ck] = tem
                held.setdefault(ck, []).append(
                    {"deck": nome, "qty": tem, "priority": d["priority"],
                     "onde": "colecao"})
            resto = falta - tem
            if not resto:
                continue
            # Está noutro deck (ou reservada por ele)? É a leitura de sempre:
            # existe, mas está comprometida noutro sítio — não se compra.
            noutro = [h for h in held.get(ck, []) if h["deck"] != nome]
            if noutro:
                shared[ck] = {"qty": resto, "em": noutro}
            else:
                missing[ck] = resto

        # O que está marcado neste deck e o deck já não pede — a lista mudou,
        # a carta continua na caixa dele. Aparece para não desaparecer do ecrã.
        extra = {ck: n for ck, n in fixo.items() if n > 0}
        out[d["deck_id"]] = {"alloc": alloc, "no_deck": no_deck,
                             "no_binder": no_binder, "shared": shared,
                             "na_colecao": na_colecao, "missing": missing,
                             "extra": extra}

    return out


# ---------------------------------------------------------------------------
# Payloads
# ---------------------------------------------------------------------------


def missing_by_set(con: sqlite3.Connection, deck_id: int,
                   ignore_types: set[str] | None = None) -> list[dict]:
    """Cópias em falta neste deck, por edição onde as ir buscar.

    Cada carta é atribuída à edição onde sai **mais barata** — é a decisão
    prática, porque é onde ele a vai comprar. Uma carta que exista em mais do
    que uma edição fica contada só uma vez, na mais barata, e é assinalada em
    `multi` para o número não parecer mais firme do que é.

    Não inclui as que faltam por estarem noutro deck: essas não se compram.
    """
    falta = allocate(con)[deck_id]["missing"]
    if ignore_types:
        tipos = {r["card_key"]: r["type"] for r in con.execute(
            "SELECT card_key, type FROM catalog.cards")}
        falta = {k: v for k, v in falta.items() if tipos.get(k) not in ignore_types}
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
            # De onde vem o que está alocado, e o que existe mas não conta.
            "no_deck": sum(a["no_deck"].values()),
            "no_binder": sum(a["no_binder"].values()),
            "na_colecao": sum(a["na_colecao"].values()),
            "extra": sum(a["extra"].values()),
            "missing": sum(a["missing"].values()),
            "shared": sum(v["qty"] for v in a["shared"].values()),
        })
    return out


def deck_payload(con: sqlite3.Connection, deck_id: int) -> dict | None:
    d = con.execute("SELECT * FROM decks WHERE deck_id = ?", (deck_id,)).fetchone()
    if not d:
        return None
    from . import locais

    a = allocate(con)[deck_id]
    # As impressões que ESTE deck pode usar: as que estão nele e as do binder
    # Decks/Venda. As da Coleção não aparecem aqui de propósito — não são para
    # montar deck nenhum (André, 2026-09-10); vão em `na_colecao`.
    prints = owned_printings(con, {locais.deck_local(d["name"]), locais.BINDER})
    names = {r["card_key"]: r for r in con.execute(
        "SELECT card_key, name, type, domains_json FROM catalog.cards")}

    # Imagem por carta: a impressão representativa do catálogo. Se ele tiver a
    # carta, vale mais mostrar a arte que tem em casa do que a canónica.
    arte = {r["card_key"]: r for r in con.execute(
        "SELECT c.card_key, p.printing_id, p.public_code, p.set_id, p.orientation, "
        "       p.image_medium, p.image_large, p.image_url "
        "FROM catalog.cards c JOIN catalog.printings p "
        "ON p.printing_id = c.rep_printing_id")}
    por_id = {r["printing_id"]: r for r in con.execute(
        "SELECT printing_id, public_code, set_id, orientation, "
        "       image_medium, image_large, image_url FROM catalog.printings")}

    # Preço da impressão, para aparecer ao lado do código na lista do deck.
    precos = {r["printing_id"]: r["price_cents"] for r in con.execute(
        "SELECT printing_id, price_cents FROM catalog.price_latest "
        "WHERE price_cents IS NOT NULL")}

    def imagem(card_key: str) -> dict:
        tenho = prints.get(card_key)
        r = por_id.get(tenho[0]["id"]) if tenho else arte.get(card_key)
        if not r:
            return {"img": None, "cdn": None, "landscape": False,
                    "code": None, "set": None, "price": None}
        return {
            "img": f"img/{r['printing_id']}.webp",
            "cdn": r["image_medium"] or r["image_large"] or r["image_url"],
            "landscape": (r["orientation"] or "").lower() == "landscape",
            "code": r["public_code"],
            "set": r["set_id"],
            "price": precos.get(r["printing_id"]),
        }

    # Quanto de cada carta já foi consumido por papéis anteriores deste deck:
    # a alocação é por carta, mas mostra-se por papel.
    usado: dict[str, int] = {}
    usado_deck: dict[str, int] = {}
    usado_col: dict[str, int] = {}
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
            # De onde vem: já sleevada no deck, ou por ir buscar ao binder
            # Decks/Venda. São duas acções diferentes para ele.
            no_deck = min(tenho, max(0, a["no_deck"].get(ck, 0) - usado_deck.get(ck, 0)))
            usado_deck[ck] = usado_deck.get(ck, 0) + no_deck
            falta = r["qty"] - tenho
            # E o que existe mas está na COLEÇÃO: não conta para o deck, e é
            # decisão dele — mover ou comprar outra.
            na_col = min(falta, max(0, a["na_colecao"].get(ck, 0) - usado_col.get(ck, 0)))
            usado_col[ck] = usado_col.get(ck, 0) + na_col
            info = names.get(ck) or {}
            cards.append({
                "card_key": ck,
                "name": (info["name"] if info else r["raw_line"]),
                "raw": r["raw_line"],
                "type": info["type"] if info else None,
                "wanted": r["qty"], "have": tenho, "missing": falta,
                "no_deck": no_deck, "no_binder": tenho - no_deck,
                "na_colecao": na_col,
                "shared": a["shared"].get(ck) if falta else None,
                "printings": prints.get(ck, []),
                **imagem(ck),
            })
        sections.append({"role": role, "label": ROLE_LABEL[role], "cards": cards,
                         "wanted": sum(c["wanted"] for c in cards),
                         "have": sum(c["have"] for c in cards),
                         "no_deck": sum(c["no_deck"] for c in cards),
                         "no_binder": sum(c["no_binder"] for c in cards),
                         "na_colecao": sum(c["na_colecao"] for c in cards)})

    return {
        "id": deck_id, "slug": d["name"], "name": d["display_name"] or d["name"],
        "legend": d["legend"], "champion": d["champion"], "priority": d["priority"],
        "sections": sections,
        "missing_by_set": missing_by_set(con, deck_id),
        "legality": legality(con, deck_id),
        "unresolved": json.loads(d["missing_json"] or "[]"),
        # De onde vêm as cartas deste deck, e o que existe mas não conta
        # (André, 2026-09-10). O `extra` é o que está marcado neste deck e o
        # deck já não pede — a lista mudou, a carta continua na caixa.
        "locais": {
            "local": locais.deck_local(d["name"]),
            "no_deck": sum(a["no_deck"].values()),
            "no_binder": sum(a["no_binder"].values()),
            "na_colecao": sum(a["na_colecao"].values()),
            "extra": sum(a["extra"].values()),
            "missing": sum(a["missing"].values()),
        },
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
    # `or "[]"`: a coluna é anulável e um Legend sem domínios rebentava aqui a
    # secção Decks inteira. É a mesma guarda que o ciclo a seguir já fazia.
    # `or "[]"`: a coluna é anulável e um Legend sem domínios rebentava aqui a
    # secção Decks inteira. É a mesma guarda que o ciclo a seguir já fazia.
    dominios = set(json.loads(legend_dom["domains_json"] or "[]")) if legend_dom else set()
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

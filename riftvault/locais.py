"""Onde está cada cópia: Coleção, um deck, ou o binder Decks/Venda.

Palavras do André (2026-09-10): *"vou querer ter as cartas da coleção apenas
alocadas à coleção e as cartas dos decks apenas alocadas a Decks. Ou seja: a
coleção fica em Binders de coleção; as cartas dos decks ficam em decks, e haverá
um Binder que será apenas e exclusivamente para Decks/Venda — caso um deck seja
desfeito, as cartas ficam para outro deck ou nesse binder."*

TRÊS LOCAIS, E SÓ TRÊS

  `colecao`      — os binders de coleção. Pode haver vários binders físicos, mas
                   o local lógico é um só: é o que a percentagem de master set,
                   a contagem por níveis e as wantlists medem.
  `deck:<slug>`  — dentro de um dos `decks/*.txt`, sleevado. É desta cópia que o
                   deck se monta.
  `binder`       — o binder Decks/Venda. É o stock livre dos decks (e o que
                   nenhum deck pede é candidato a venda).

A COLEÇÃO NÃO SE GRAVA, CALCULA-SE
    A tabela `copy_locations` guarda **só** o que NÃO está na Coleção. A Coleção
    é `copies.qty − Σ(o resto)`. São duas coisas de uma vez:

      - a migração não escreve linha nenhuma. *"Onde não se sabe o local, fica
        Coleção por omissão"* é o que sai de graça de uma tabela vazia, e por
        isso a contagem de cópias antes e depois é a mesma por construção — não
        há um passo de cópia de dados que possa perder uma cópia pelo caminho.
      - o `copies` continua a ser a única verdade sobre QUANTAS cópias existem.
        O `+` e o `−` da grelha não têm de saber de locais: somam ao total, e o
        que sobe é a Coleção.

    O preço a pagar é a invariante `Σ(fora) <= total`, que é responsabilidade
    deste módulo — ver `ajustar_ao_total`, chamado pelo `collection.adjust`
    quando o total desce.

RASTO
    Toda a mudança de local deixa duas linhas: uma na `location_ops` (que é o
    que o `undo` lê) e outra em `data/locais.log`, um CSV que se abre no Excel.
    Se um dia uma cópia aparecer num deck sem linha no log, é bug — é a mesma
    defesa do `registos-caixas.csv` do mtgvault (2026-09-09).
"""

from __future__ import annotations

import csv
import io
import sqlite3
from datetime import datetime, timezone

from . import collection, config

COLECAO = "colecao"
BINDER = "binder"
DECK_PREFIX = "deck:"

# O ficheiro de rasto. Fica no `data/`, ao lado das bases, e é append-only.
LOG_NAME = "locais.log"

# Escrito à mão na criação do ficheiro, para o Excel do André abrir o CSV com os
# acentos certos. NÃO se usa o codec `utf-8-sig`: ele põe um BOM a cada
# `open(..., "a")`, e ao fim de meia dúzia de movimentos o ficheiro tinha BOMs a
# meio das linhas.
BOM = "﻿"

# Quando o total de cópias desce abaixo do que está alocado fora da Coleção,
# alguém tem de perder a cópia. Vai para aqui no rasto: não é um local, é o
# registo de que a cópia deixou de existir.
SAIU = "(saiu da coleção)"


class LocalInvalido(ValueError):
    pass


class SemCopias(ValueError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Nomes dos locais
# ---------------------------------------------------------------------------


def deck_local(slug: str) -> str:
    return f"{DECK_PREFIX}{slug.strip().lower()}"


def slug_do_deck(local: str) -> str | None:
    return local[len(DECK_PREFIX):] if local.startswith(DECK_PREFIX) else None


def normalizar(local: str, decks_conhecidos: set[str] | None = None) -> str:
    """Aceita como ele escreve e devolve o local canónico.

    `colecao`/`coleção`/`coleccao`, `binder`/`decks-venda`, `deck:azir` ou só
    `azir` quando `azir` é um deck conhecido. Um valor que não se reconheça
    REBENTA — é a mesma regra do `master_set.fora`: um local novo tem de
    aparecer, não de ser tratado como Coleção em silêncio.
    """
    if not local:
        raise LocalInvalido("falta o local")
    k = str(local).strip().lower().replace("ç", "c").replace("ã", "a").replace("é", "e")
    if k in ("colecao", "coleccao", "colecção", "col"):
        return COLECAO
    if k in ("binder", "decks-venda", "decks/venda", "deckvenda", "venda"):
        return BINDER
    if k.startswith(DECK_PREFIX):
        return deck_local(k[len(DECK_PREFIX):])
    if decks_conhecidos and k in decks_conhecidos:
        return deck_local(k)
    aceites = "colecao, binder, deck:<slug>"
    if decks_conhecidos:
        aceites += " (decks: " + ", ".join(sorted(decks_conhecidos)) + ")"
    raise LocalInvalido(f"local desconhecido: {local!r}. Aceita: {aceites}")


def rotulo(local: str, nomes: dict[str, str] | None = None) -> str:
    """O nome que ele lê no ecrã e na consola."""
    if local == COLECAO:
        return "Coleção"
    if local == BINDER:
        return "Binder Decks/Venda"
    slug = slug_do_deck(local)
    if slug is None:
        return local
    return "Deck " + ((nomes or {}).get(slug) or slug)


def nomes_dos_decks(con: sqlite3.Connection) -> dict[str, str]:
    """slug -> nome de mostrar («Azir · Brutalizer»), para os rótulos."""
    try:
        return {r["name"]: (r["display_name"] or r["name"])
                for r in con.execute("SELECT name, display_name FROM decks")}
    except sqlite3.OperationalError:
        return {}


def slugs(con: sqlite3.Connection) -> set[str]:
    try:
        return {r["name"] for r in con.execute("SELECT name FROM decks")}
    except sqlite3.OperationalError:
        return set()


# ---------------------------------------------------------------------------
# Leitura
# ---------------------------------------------------------------------------


def totais(con: sqlite3.Connection) -> dict[str, int]:
    """printing_id -> cópias FÍSICAS, de todos os locais. É o `copies`."""
    return {r["printing_id"]: r["qty"] for r in
            con.execute("SELECT printing_id, qty FROM copies WHERE qty > 0")}


def fora_da_colecao(con: sqlite3.Connection) -> dict[str, dict[str, int]]:
    """printing_id -> {local: qty} do que NÃO está na Coleção."""
    out: dict[str, dict[str, int]] = {}
    for r in con.execute(
        "SELECT printing_id, location, qty FROM copy_locations WHERE qty > 0"
    ):
        out.setdefault(r["printing_id"], {})[r["location"]] = r["qty"]
    return out


def na_colecao(con: sqlite3.Connection) -> dict[str, int]:
    """printing_id -> cópias que estão nos binders de COLEÇÃO.

    É esta a base de tudo o que mede a Coleção — a percentagem de master set, a
    contagem por níveis, as wantlists e o excedente. Uma cópia que esteja num
    deck deixa de contar aqui, mesmo sendo a mesma impressão: foi exactamente
    isso que ele pediu.
    """
    total = totais(con)
    for pid, locs in fora_da_colecao(con).items():
        total[pid] = max(0, total.get(pid, 0) - sum(locs.values()))
    return {pid: q for pid, q in total.items() if q > 0}


def por_local(con: sqlite3.Connection) -> dict[str, dict[str, int]]:
    """printing_id -> {local: qty}, com a Coleção já calculada."""
    fora = fora_da_colecao(con)
    out: dict[str, dict[str, int]] = {}
    for pid, total in totais(con).items():
        locs = dict(fora.get(pid) or {})
        resto = total - sum(locs.values())
        if resto > 0:
            locs[COLECAO] = resto
        if locs:
            out[pid] = locs
    return out


def em(con: sqlite3.Connection, local: str) -> dict[str, int]:
    """printing_id -> cópias NESTE local."""
    if local == COLECAO:
        return na_colecao(con)
    return {r["printing_id"]: r["qty"] for r in con.execute(
        "SELECT printing_id, qty FROM copy_locations WHERE location = ? AND qty > 0",
        (local,))}


def por_deck(con: sqlite3.Connection) -> dict[str, dict[str, int]]:
    """slug -> {printing_id: qty}: as cópias sleevadas em cada deck."""
    out: dict[str, dict[str, int]] = {}
    for r in con.execute(
        "SELECT printing_id, location, qty FROM copy_locations "
        "WHERE qty > 0 AND location LIKE ?", (DECK_PREFIX + "%",)
    ):
        slug = slug_do_deck(r["location"])
        if slug:
            out.setdefault(slug, {})[r["printing_id"]] = r["qty"]
    return out


def resumo(con: sqlite3.Connection) -> list[dict]:
    """Quantas cópias em cada local, para o `riftvault local` e a página."""
    nomes = nomes_dos_decks(con)
    contagem: dict[str, list[int]] = {}
    for locs in por_local(con).values():
        for loc, q in locs.items():
            slot = contagem.setdefault(loc, [0, 0])
            slot[0] += q
            slot[1] += 1
    ordem = {COLECAO: 0, BINDER: 2}
    return [{"local": loc, "label": rotulo(loc, nomes),
             "copies": v[0], "printings": v[1]}
            for loc, v in sorted(contagem.items(),
                                 key=lambda kv: (ordem.get(kv[0], 1), kv[0]))]


# ---------------------------------------------------------------------------
# Escrita
# ---------------------------------------------------------------------------


def _set_qty(con: sqlite3.Connection, printing_id: str, local: str, qty: int) -> None:
    """Fixa as cópias de uma impressão num local. A Coleção nunca se grava."""
    if local == COLECAO:
        return
    if qty <= 0:
        con.execute("DELETE FROM copy_locations WHERE printing_id = ? AND location = ?",
                    (printing_id, local))
        return
    con.execute(
        "INSERT INTO copy_locations (printing_id, location, qty, updated_at) "
        "VALUES (?,?,?,?) ON CONFLICT(printing_id, location) DO UPDATE SET "
        "qty = excluded.qty, updated_at = excluded.updated_at",
        (printing_id, local, qty, _now()))


def _qty_em(con: sqlite3.Connection, printing_id: str, local: str) -> int:
    if local == COLECAO:
        total = collection.get_qty(con, printing_id)
        fora = con.execute(
            "SELECT COALESCE(SUM(qty),0) AS n FROM copy_locations WHERE printing_id = ?",
            (printing_id,)).fetchone()["n"]
        return max(0, total - fora)
    row = con.execute(
        "SELECT qty FROM copy_locations WHERE printing_id = ? AND location = ?",
        (printing_id, local)).fetchone()
    return row["qty"] if row else 0


def _log(con: sqlite3.Connection, linhas: list[dict]) -> None:
    """Uma linha por movimento em `data/locais.log`. Nunca impede a escrita.

    O ficheiro é o rasto para ele: se uma cópia aparecer num deck sem linha
    aqui, é bug. É a lição do `registos-caixas.csv` do mtgvault — a defesa não é
    a intenção do código, é o registo de que ele passou.
    """
    if not linhas:
        return
    caminho = config.DATA_DIR / LOG_NAME
    nomes = nomes_dos_decks(con)
    novo = not caminho.exists()
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    if novo:
        w.writerow(["quando", "printing_id", "codigo", "nome", "quantidade",
                    "de", "para", "origem"])
    for x in linhas:
        w.writerow([x["ts"], x["printing_id"], x.get("code") or "", x.get("name") or "",
                    x["qty"], rotulo(x["de"], nomes) if x["de"] != SAIU else x["de"],
                    rotulo(x["para"], nomes) if x["para"] != SAIU else x["para"],
                    x.get("source") or ""])
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
        "SELECT public_code, name FROM catalog.printings WHERE printing_id = ?",
        (printing_id,)).fetchone()
    return {"code": row["public_code"] if row else None,
            "name": row["name"] if row else None}


def mover(con: sqlite3.Connection, ref: str, qty: int, de: str, para: str,
          source: str = "cli", request_id: str | None = None) -> dict:
    """Move `qty` cópias de um local para outro. É a única porta de escrita.

    Nada de valores absolutos vindos do cliente: como no `collection.adjust`, o
    que se manda é um MOVIMENTO, e o `request_id` é único — um retry de rede não
    move a dobrar.
    """
    printing_id = collection.resolve_printing(con, ref)
    qty = int(qty)
    if qty <= 0:
        raise SemCopias("a quantidade tem de ser 1 ou mais")
    conhecidos = slugs(con)
    de = normalizar(de, conhecidos)
    para = normalizar(para, conhecidos)
    if de == para:
        raise LocalInvalido(f"origem e destino são o mesmo local ({rotulo(de)})")

    if request_id:
        prev = con.execute(
            "SELECT id, qty, from_loc, to_loc FROM location_ops WHERE request_id = ?",
            (request_id,)).fetchone()
        if prev:
            return {"printing_id": printing_id, "qty": prev["qty"],
                    "de": prev["from_loc"], "para": prev["to_loc"],
                    "op_id": prev["id"], "duplicate": True}

    con.execute("BEGIN IMMEDIATE")
    try:
        disponivel = _qty_em(con, printing_id, de)
        if disponivel < qty:
            raise SemCopias(
                f"só há {disponivel} cópia(s) de {printing_id} em {rotulo(de)}, "
                f"pediste {qty}")
        _set_qty(con, printing_id, de, disponivel - qty)
        _set_qty(con, printing_id, para, _qty_em(con, printing_id, para) + qty)
        cur = con.execute(
            "INSERT INTO location_ops (ts, printing_id, qty, from_loc, to_loc, "
            "source, request_id) VALUES (?,?,?,?,?,?,?)",
            (_now(), printing_id, qty, de, para, source, request_id))
        op_id = cur.lastrowid
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise

    _log(con, [{"ts": _now(), "printing_id": printing_id, "qty": qty,
                "de": de, "para": para, "source": source,
                **_descrever(con, printing_id)}])
    return {"printing_id": printing_id, "qty": qty, "de": de, "para": para,
            "op_id": op_id, "duplicate": False}


def marcar(con: sqlite3.Connection, linhas: list[dict], para: str,
           de: str = COLECAO, source: str = "web") -> dict:
    """Move VÁRIAS linhas de uma vez — o «marcar tudo o que este deck usa».

    **Grava só o que vier na lista.** Nunca a lista que o riftvault calculou:
    a proposta é uma sugestão no ecrã, e o que fica registado é o que ele
    confirmou linha a linha. É a lição do mtgvault de 2026-09-09 — lá o
    registo gravou 65 linhas calculadas, incluindo duas cartas que ele tinha
    dito não ter.

    Uma lista vazia é um erro, não um sucesso silencioso: lista vazia e lista
    ausente querem dizer a mesma coisa — não há nada confirmado.
    """
    if not linhas:
        raise SemCopias("não marcaste nenhuma linha — não há nada para gravar")
    feitas, falhadas = [], []
    for linha in linhas:
        try:
            feitas.append(mover(con, linha["printing_id"], int(linha.get("qty", 1)),
                                linha.get("de") or de, para, source=source,
                                request_id=linha.get("request_id")))
        except (SemCopias, LocalInvalido, collection.UnknownPrinting) as exc:
            falhadas.append({"printing_id": linha.get("printing_id"), "erro": str(exc)})
    return {"movidas": feitas, "falhadas": falhadas,
            "copies": sum(x["qty"] for x in feitas)}


def desfazer_deck(con: sqlite3.Connection, slug: str, source: str = "cli") -> dict:
    """Desfaz um deck: tudo o que estava nele passa ao binder Decks/Venda.

    *"Caso um deck seja desfeito, as cartas ficam para outro deck ou nesse
    binder"* — a segunda metade é automática (vão para o binder) e a primeira
    passa a estar disponível sozinha, porque o binder é o stock livre dos decks.
    **Nunca voltam à Coleção**: quem as tirou de lá foi ele, e devolvê-las era
    inventar uma decisão que ele não tomou.
    """
    local = deck_local(slug)
    linhas = con.execute(
        "SELECT printing_id, qty FROM copy_locations WHERE location = ? AND qty > 0",
        (local,)).fetchall()
    feitas = [mover(con, r["printing_id"], r["qty"], local, BINDER, source=source)
              for r in linhas]
    return {"deck": slug, "printings": len(feitas),
            "copies": sum(x["qty"] for x in feitas), "movidas": feitas}


def undo_last(con: sqlite3.Connection, source: str = "cli") -> dict | None:
    """Desfaz o último movimento de local que ainda não foi desfeito."""
    op = con.execute(
        "SELECT * FROM location_ops WHERE undone_at IS NULL AND undo_of IS NULL "
        "ORDER BY id DESC LIMIT 1").fetchone()
    if not op:
        return None
    res = mover(con, op["printing_id"], op["qty"], op["to_loc"], op["from_loc"],
                source=source)
    # O `undo_of` vai na op de COMPENSAÇÃO (é ela que reverte); o `undone_at`
    # vai na original. Sem os dois, um `undo` repetido ficava a saltar entre as
    # duas últimas em vez de andar para trás no histórico.
    con.execute("UPDATE location_ops SET undo_of = ?, undone_at = ? WHERE id = ?",
                (op["id"], _now(), res["op_id"]))
    con.execute("UPDATE location_ops SET undone_at = ? WHERE id = ?",
                (_now(), op["id"]))
    return {"undone_op": op["id"], **res}


def ajustar_ao_total(con: sqlite3.Connection, printing_id: str,
                     source: str = "cli") -> list[dict]:
    """Mantém a invariante `Σ(fora da Coleção) <= total` quando o total desce.

    Um `−` na grelha tira uma cópia FÍSICA. Se ele tinha 3 cópias, 3 delas num
    deck, e tira uma, alguma tem de sair do deck — senão a Coleção ficava com
    contagem negativa e o riftvault passava a dizer que ele tem cartas que não
    tem.

    Tira-se primeiro do binder Decks/Venda e só depois dos decks (os decks
    últimos, porque uma carta sleevada é a que menos provavelmente desapareceu).
    Cada retirada deixa rasto: no `data/locais.log` aparece `-> (saiu da
    coleção)`, para não haver cópias a evaporar-se em silêncio.
    """
    total = collection.get_qty(con, printing_id)
    linhas = con.execute(
        "SELECT location, qty FROM copy_locations WHERE printing_id = ? AND qty > 0",
        (printing_id,)).fetchall()
    excesso = sum(r["qty"] for r in linhas) - total
    if excesso <= 0:
        return []

    # Binder primeiro, depois os decks por ordem alfabética — determinista.
    ordenadas = sorted(linhas, key=lambda r: (0 if r["location"] == BINDER else 1,
                                              r["location"]))
    tiradas = []
    for r in ordenadas:
        if excesso <= 0:
            break
        tira = min(excesso, r["qty"])
        _set_qty(con, printing_id, r["location"], r["qty"] - tira)
        con.execute(
            "INSERT INTO location_ops (ts, printing_id, qty, from_loc, to_loc, source) "
            "VALUES (?,?,?,?,?,?)",
            (_now(), printing_id, tira, r["location"], SAIU, source))
        tiradas.append({"local": r["location"], "qty": tira})
        excesso -= tira

    _log(con, [{"ts": _now(), "printing_id": printing_id, "qty": t["qty"],
                "de": t["local"], "para": SAIU, "source": source,
                **_descrever(con, printing_id)} for t in tiradas])
    return tiradas


# ---------------------------------------------------------------------------
# A proposta de marcação
# ---------------------------------------------------------------------------


def propor_deck(con: sqlite3.Connection, slug: str) -> dict:
    """O que este deck usaria se as cópias que estão na Coleção fossem para ele.

    É **só uma sugestão para o ecrã**: nada disto se grava. O que se grava é o
    que ele confirmar, linha a linha, pelo `marcar()`. A lista sai por carta e
    escolhe **artes base primeiro** (a mesma regra do `decks.printing_allocation`
    de sempre): as alternativas e as signatures ficam no binder de coleção.
    """
    from . import decks as decks_mod

    row = con.execute("SELECT deck_id FROM decks WHERE name = ?", (slug,)).fetchone()
    if not row:
        return {"deck": slug, "items": [], "erro": "não há deck com esse nome"}
    deck_id = row["deck_id"]

    pedidas: dict[str, int] = {r["card_key"]: r["q"] for r in con.execute(
        "SELECT card_key, SUM(qty) AS q FROM deck_cards WHERE deck_id = ? "
        "GROUP BY card_key", (deck_id,))}
    if not pedidas:
        return {"deck": slug, "items": []}

    ja_tem = em(con, deck_local(slug))
    colecao = na_colecao(con)
    card_key = {r["printing_id"]: r["card_key"] for r in con.execute(
        "SELECT printing_id, card_key FROM catalog.printings")}
    ordens = {s: config.set_order(s) for s in
              (r["set_id"] for r in con.execute(
                  "SELECT DISTINCT set_id FROM catalog.printings"))}

    por_carta: dict[str, list] = {}
    for r in con.execute(
        "SELECT printing_id, card_key, public_code, name, set_id, variant_kind, "
        "       variant_label, api_sort, orientation, image_medium, image_large, "
        "       image_url FROM catalog.printings"
    ):
        if r["card_key"] in pedidas and colecao.get(r["printing_id"], 0) > 0:
            por_carta.setdefault(r["card_key"], []).append(r)

    itens = []
    for ck, n in sorted(pedidas.items()):
        falta = n - sum(q for pid, q in ja_tem.items() if card_key.get(pid) == ck)
        if falta <= 0:
            continue
        cands = sorted(por_carta.get(ck, []),
                       key=lambda r: (0 if r["variant_kind"] == "base" else 1,
                                      ordens.get(r["set_id"], 999), r["api_sort"]))
        for r in cands:
            if falta <= 0:
                break
            tira = min(falta, colecao.get(r["printing_id"], 0))
            if tira <= 0:
                continue
            falta -= tira
            itens.append({
                "printing_id": r["printing_id"], "qty": tira,
                "card_key": ck, "name": r["name"], "code": r["public_code"],
                "set": r["set_id"], "label": r["variant_label"],
                "kind": r["variant_kind"],
                "na_colecao": colecao.get(r["printing_id"], 0),
                "landscape": (r["orientation"] or "").lower() == "landscape",
                "img": f"img/{r['printing_id']}.webp",
                "cdn": r["image_medium"] or r["image_large"] or r["image_url"],
            })
    return {"deck": slug, "de": COLECAO, "para": deck_local(slug),
            "items": itens, "copies": sum(x["qty"] for x in itens)}

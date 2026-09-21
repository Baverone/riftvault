"""As CÓPIAS PRÓPRIAS de cada deck (2026-09-21) — o local `proprio:<slug>`.

Palavras do André, ao acabar a experiência do pool próprio dessa manhã:
*"voltamos aos decks usarem a coleccao, mas cada deck precisa de ter as
cartas proprias; colocas em cada deck o + e - para eu dizer se afinal tenho
ou nao; estas copias que eu coloco nos decks nao sao para adicionar a
coleccao"*.

O MODELO, EM CINCO LINHAS
  1. OS DECKS USAM A COLEÇÃO, como desde 2026-09-11 (`decks.allocate`, por
     prioridade): a grelha diz «Azir 3», há o filtro «Em decks», as
     libertadas e o «para que deck» das Encomendas.
  2. CADA DECK PRECISA DAS SUAS PRÓPRIAS CARTAS. Os decks não partilham entre
     si: o que os seis precisam é a SOMA (main e sideboard somam dentro do
     mesmo deck; runas fora, `decks.cartas_nao_contadas`).
  3. CADA DECK TEM UM MONTE PRÓPRIO — as cópias que ele diz ter guardadas
     PARA AQUELE DECK —, no local `proprio:<slug>` da `copy_locations`
     (`locais.proprias`), separado do `deck:<slug>` (que marca onde está uma
     cópia da Coleção que o deck usa). Entram e saem por `ajustar` — os
     `+`/`−` de cada carta na página do deck, `riftvault proprias SLUG
     --mais/--menos` —, que escreve no `copies` E no local numa transação
     só, para a Coleção (`copies − Σ fora`) ficar exactamente onde estava.
  4. NÃO ENTRAM NA COLEÇÃO. Uma própria não conta para os níveis, o
     denominador, as Faltas, as wantlists, as Encomendas, o A mais
     (`locais.na_colecao` já a tira, por ser um local), NEM PARA O VALOR nem
     para o playset jogável (`locais.contadas`, `prices.copias_sql`).
     Decisão minha, anotada no CLAUDE.md: o valor é um número da página da
     Coleção, e um `+` num deck não pode mexer lá; o pool da manhã já fazia
     assim. Meter ou tirar uma própria não mexe um número da Coleção —
     `tests/test_copias_proprias.py` prova-o. São daquele deck e só daquele:
     não servem outro deck.
  5. SERVEM PRIMEIRO: o deck cobre-se com as próprias e só o que sobrar vai
     buscar à Coleção (antes do sleevado, do binder, da Coleção e do que vem a
     caminho — `decks.allocate`), por isso meter próprias LIBERTA cópias da
     Coleção que o deck usava. `faltam = precisa − próprias − o que a Coleção
     lhe alocou`.

SÓ VERSÕES BASE (`decks.so_base`, `true`): o `+` só aceita a base não
sobrenumerada — a Legend e o Champion incluídos —, e uma própria de outra
versão que lá esteja não serve (fica em `proprias_fora`, com o motivo). Com
`false` aceita-se qualquer versão que sirva o deck (`Versoes.serve`: nunca
assinada, nunca retirada).

A EXPERIÊNCIA DO POOL PRÓPRIO (a manhã de 2026-09-21) foi a primeira versão
deste ficheiro: um pool único, partilhado por todos os decks (máximo por
carta), fora da Coleção, com `decks.modo = "pool_proprio"`. Acabou com a
frase de cima; o pool estava vazio e a maquinaria (o `ajustar`, a rota, a
CLI, os tiles com `+`/`−`) passou a ser POR DECK.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from . import collection, decks, locais

# Os dois «locais» do rasto (`location_ops`, `data/locais.log`) para uma cópia
# que entra num deck vinda de fora do riftvault, ou que sai dele para fora —
# não são locais, como o `locais.SAIU` não é.
ENTROU = "(entrou como cópia própria)"
SAIU = "(saiu das cópias próprias)"


class NaoServe(ValueError):
    """A impressão não serve este deck — não é base (`so_base`), ou é assinada
    ou retirada. O `+` recusa em vez de a deixar lá sem servir."""


class DeckDesconhecido(ValueError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Leitura
# ---------------------------------------------------------------------------


def deck_por_slug(con: sqlite3.Connection, slug: str) -> sqlite3.Row:
    row = next((r for r in decks.deck_rows(con) if r["name"] == (slug or "").strip().lower()), None)
    if row is None:
        raise DeckDesconhecido(f"não há deck chamado {slug!r} "
                               f"(há: {', '.join(r['name'] for r in decks.deck_rows(con)) or 'nenhum'})")
    return row


def stock(con: sqlite3.Connection, slug: str) -> dict[str, int]:
    """printing_id -> cópias próprias DESTE deck."""
    return locais.proprias_de(con, slug)


def impressao_para(con: sqlite3.Connection, slug: str, ref: str) -> str:
    """A impressão em que o `+` de uma CARTA grava, quando `ref` é o nome ou
    o `card_key` e não um código: a base em que se compra (`Versoes.compra`)
    — ou, se o deck já tem próprias dessa carta, a impressão delas. Um código
    ou `printing_id` passa tal e qual (`collection.resolve_printing`)."""
    try:
        return collection.resolve_printing(con, ref)
    except collection.UnknownPrinting:
        pass
    ck = decks.resolve(con, ref, "main") or decks.norm(ref)
    versoes = decks.versoes_dos_decks(con)
    for pid, n in stock(con, slug).items():
        r = versoes.linha_de.get(pid)
        if r is not None and r["card_key"] == ck and n > 0:
            return pid
    pid = versoes.compra(ck)
    if pid is None:
        raise collection.UnknownPrinting(f"{ref!r}: não é código, id nem carta com versão base")
    return pid


def resumo(con: sqlite3.Connection) -> list[dict]:
    """Por deck: quantas próprias tem, quantas servem, quantas não, e o que
    ainda lhe falta — a linha do `riftvault proprias` sem deck."""
    idx = decks.decks_index(con)
    return [{"slug": d["slug"], "name": d["name"], "priority": d["priority"],
             "wanted": d["wanted"], "have": d["have"], "proprias": d["proprias"],
             "proprias_fora": d["proprias_fora"], "na_colecao": d["na_colecao"],
             "no_deck": d["no_deck"], "no_binder": d["no_binder"],
             "ordered": d["ordered"], "missing": d["missing"]} for d in idx]


# ---------------------------------------------------------------------------
# Escrita: entrar e sair das cópias próprias de um deck
# ---------------------------------------------------------------------------


def ajustar(con: sqlite3.Connection, slug: str, ref: str, delta: int,
            source: str = "web", request_id: str | None = None) -> dict:
    """Soma `delta` cópias de uma impressão às PRÓPRIAS do deck `slug` — no
    `copies` E no local `proprio:<slug>`, numa transação só, para a Coleção
    (`copies − Σ fora`) ficar exactamente onde estava. É a única porta de
    entrada e saída.

    Um `−` nunca vai abaixo de zero nas próprias do deck (não toca em cópias
    que estejam na Coleção ou noutro local). Um `request_id` repetido não
    aplica duas vezes (a `ops`, como no `collection.adjust`). Deixa rasto na
    `ops`, na `location_ops` (`(entrou como cópia própria)` -> proprio:<slug>,
    proprio:<slug> -> `(saiu das cópias próprias)`) e no `data/locais.log`.
    Uma impressão que não sirva o deck rebenta (`NaoServe`): com `so_base` só
    a base não sobrenumerada; nunca uma assinada nem uma retirada.

    Cuidado com o `riftvault undo` genérico: reverte a linha da `ops` (as
    cópias) e o `ajustar_ao_total` tira-as das próprias a seguir — um `+`
    desfaz-se bem; o undo de um `−` põe a cópia na Coleção, não nas próprias.
    Para tirar ou pôr próprias, é por aqui.
    """
    d = deck_por_slug(con, slug)
    local = locais.proprio_local(d["name"])
    pid = collection.resolve_printing(con, ref)
    delta = int(delta)
    r = con.execute("SELECT * FROM catalog.printings WHERE printing_id = ?", (pid,)).fetchone()
    versoes = decks.versoes_dos_decks(con)
    if r is None or not versoes.serve(r):
        raise NaoServe(f"{pid} não serve os decks — "
                       + ("só versões base (decks.so_base)" if decks.so_base()
                          else "nunca uma assinada nem uma retirada"))

    if request_id:
        prev = con.execute("SELECT id, delta FROM ops WHERE request_id = ?",
                           (request_id,)).fetchone()
        if prev:
            return {"deck": d["name"], "printing_id": pid,
                    "qty": locais._qty_em(con, pid, local),
                    "total": collection.get_qty(con, pid), "applied": prev["delta"],
                    "op_id": prev["id"], "duplicate": True}

    con.execute("BEGIN IMMEDIATE")
    try:
        total = collection.get_qty(con, pid)
        no_local = locais._qty_em(con, pid, local)
        applied = delta if delta > 0 else max(delta, -no_local)
        if applied == 0:
            con.execute("COMMIT")
            return {"deck": d["name"], "printing_id": pid, "qty": no_local, "total": total,
                    "applied": 0, "op_id": None, "duplicate": False}
        novo_total = total + applied
        con.execute(
            "INSERT INTO copies (printing_id, qty, updated_at) VALUES (?,?,?) "
            "ON CONFLICT(printing_id) DO UPDATE SET qty = excluded.qty, "
            "updated_at = excluded.updated_at", (pid, novo_total, _now()))
        cur = con.execute(
            "INSERT INTO ops (ts, printing_id, delta, qty_after, source, request_id) "
            "VALUES (?,?,?,?,?,?)", (_now(), pid, applied, novo_total, source, request_id))
        op_id = cur.lastrowid
        locais._set_qty(con, pid, local, no_local + applied)
        de, para = (ENTROU, local) if applied > 0 else (local, SAIU)
        con.execute(
            "INSERT INTO location_ops (ts, printing_id, qty, from_loc, to_loc, source) "
            "VALUES (?,?,?,?,?,?)", (_now(), pid, abs(applied), de, para, source))
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise

    locais._log(con, [{"ts": _now(), "printing_id": pid, "qty": abs(applied),
                       "de": de, "para": para, "source": source,
                       **locais._descrever(con, pid)}])
    return {"deck": d["name"], "printing_id": pid, "qty": no_local + applied,
            "total": novo_total, "applied": applied, "op_id": op_id, "duplicate": False}

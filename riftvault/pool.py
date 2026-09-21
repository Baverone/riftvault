"""O pool próprio dos decks — a EXPERIÊNCIA de 2026-09-21 (`decks.modo`).

Palavras do André: *"quero que a coleccao fique sempre imaculada, nada sai da
coleccao; os decks, todos partilham as mesmas cartas, mas nao usam
absolutamente nada da coleccao; so jogam com versoes base; vamos ver como
fica assim as coisas, para ter uma ideia"*.

É UMA EXPERIÊNCIA, ATRÁS DE UMA CHAVE: `decks.modo = "pool_proprio"` no
`riftvault_config.json`. Com `coleccao` (a omissão) nada deste módulo é lido e
tudo fica como estava — os decks servem-se da Coleção, a Legend e o Champion
em versão especial, alocação por prioridade (`decks.allocate`). Voltar atrás
é mudar a palavra; nada se apaga nem se reescreve na coleção.

O MODELO, EM CINCO LINHAS
  1. A COLEÇÃO FICA INTACTA. Nenhuma conta da Coleção sabe que há decks:
     níveis, Faltas, as quatro wantlists, o valor, as Encomendas e o A mais
     calculam-se como se não houvesse decks (`decks.uso_por_carta` vazio,
     `a_mais._usadas` vazio, as «libertadas» sem vista, o «para que deck» das
     Encomendas vazio). O A mais é o excedente verdadeiro face aos alvos.
  2. OS DECKS TÊM POOL PRÓPRIO. As cópias vivem no local `pool-decks`
     (`locais.POOL`, na `copy_locations`, como o binder e os `deck:`). O pool
     começa a ZERO e é ele que lá mete o que tiver (`ajustar`, os `+`/`−` da
     aba Decks, `riftvault pool --mais`). Uma cópia no pool nunca conta para
     a Coleção (`locais.na_colecao` já a tira; o valor e o playset jogável
     lêem `locais.contadas`) e vice-versa.
  3. OS DECKS PARTILHAM ENTRE SI. O pool precisa de ter, de cada carta, o
     MÁXIMO entre os decks — não a soma (`necessidades`). Dentro do MESMO
     deck main e sideboard somam (são cartas físicas distintas ao mesmo
     tempo; é o `decks._need` de sempre). As runas continuam fora de tudo
     (`decks.cartas_nao_contadas`).
  4. SÓ VERSÕES BASE. `variant_kind == "base"` e não sobrenumerada — a
     Legend e o Champion também (a regra de 2026-09-17 NÃO se aplica aqui).
     Sem alt art, sem sobrenumeradas, sem promos, sem assinadas. Uma carta
     sem versão base não se tapa com outra coisa: fica em `sem_base`, e a
     página diz quais (hoje nenhuma — medido a 2026-09-21).
  5. A ABA DECKS mostra o pool: o que precisa de ter, o que já tem, o que
     falta; e por deck, se o pool chega para o montar. A ordem dos decks é a
     do config (`decks.ordem`).

ONDE ISTO ENCAIXA. `decks.allocate` chama `alocacao` neste modo e devolve a
MESMA forma de sempre — por deck, com `grupo` —, para o `deck_payload`, o
`decks_index`, o `faltas.compras`, o `pending.encomendas` e o `a_mais` não
terem de saber do modo. Cada deck avalia-se SOZINHO contra o pool inteiro
(`alloc = min(pede, tem no pool)`), porque os decks partilham e não se
consomem uns aos outros; o `grupo` (com `lider` só no primeiro deck) traz o
resultado do pool — o máximo por carta —, que é o que se soma nos totais.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from . import cardmarket, collection, config, decks, locais, metrics

# Os dois «locais» do rasto (`location_ops`, `data/locais.log`) para uma cópia
# que entra no pool vinda de fora do riftvault, ou que sai dele para fora — não
# são locais, como o `locais.SAIU` não é.
ENTROU = "(entrou no pool)"
SAIU = "(saiu do pool)"


class NaoBase(ValueError):
    """Só versões base entram no pool — é a regra 4."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Leitura
# ---------------------------------------------------------------------------


def necessidades(con: sqlite3.Connection, cfg: dict | None = None) -> dict[str, dict]:
    """card_key -> {max, soma, decks: {slug: qty}}: o que os decks pedem.

    `max` é o que o pool precisa de ter (os decks partilham); `soma` é o que
    seria se os seis se montassem ao mesmo tempo — fica para se ver a
    diferença, não para se comprar. Runas fora (`decks.cartas_nao_contadas`).
    """
    cfg = cfg or config.load()
    fora = decks.cartas_nao_contadas(con, cfg)
    out: dict[str, dict] = {}
    for d in decks.deck_rows(con):
        for ck, q in decks._need(con, d["deck_id"], fora).items():
            e = out.setdefault(ck, {"max": 0, "soma": 0, "decks": {}})
            e["max"] = max(e["max"], q)
            e["soma"] += q
            e["decks"][d["name"]] = q
    return out


def stock(con: sqlite3.Connection) -> dict[str, int]:
    """printing_id -> cópias no pool."""
    return locais.no_pool(con)


def estado(con: sqlite3.Connection, cfg: dict | None = None) -> dict:
    """O pool inteiro, carta a carta: pede (máximo), tem, falta, e de que
    impressões; mais o que está no pool e não serve (`fora`) e as cartas
    sem versão base (`sem_base`).

    `have` conta só as impressões BASE da carta (`Versoes.normais_de`, que
    neste modo é só isso). Uma cópia no pool de outra versão, de uma carta
    que nenhum deck pede, ou de uma runa, não serve ninguém e fica em `fora`
    — diz-se, em vez de desaparecer.
    """
    cfg = cfg or config.load()
    versoes = decks.versoes_dos_decks(con, cfg)
    need = necessidades(con, cfg)
    no_pool = stock(con)
    cards: dict[str, dict] = {}
    usadas: set[str] = set()
    for ck, e in need.items():
        pids = versoes.normais_de(ck)
        printings = {pid: no_pool[pid] for pid in pids if no_pool.get(pid)}
        usadas.update(printings)
        have = sum(printings.values())
        cards[ck] = {**e, "need": e["max"], "have": have,
                     "missing": max(0, e["max"] - have),
                     "printings": printings, "sem_base": not pids}
    fora = []
    for pid, n in sorted(no_pool.items()):
        if pid in usadas:
            continue
        r = versoes.linha_de.get(pid)
        ck = r["card_key"] if r is not None else None
        if r is None:
            motivo = "fora do catálogo"
        elif ck not in need:
            motivo = "nenhum deck a pede"
        else:
            motivo = "não é versão base"
        fora.append({"printing_id": pid, "qty": n, "card_key": ck, "motivo": motivo})
    return {"cards": cards, "fora": fora,
            "sem_base": sorted(ck for ck, c in cards.items() if c["sem_base"]),
            "versoes": versoes}


def alocacao(con: sqlite3.Connection) -> dict:
    """O `decks.allocate` deste modo: a mesma forma, calculada contra o pool.

    Por deck: `alloc[ck] = min(o que este deck pede, o que o pool tem)` —
    cada deck avalia-se sozinho contra o pool inteiro —, `missing` é o
    resto, e `versoes_em` reparte o `alloc` pelas impressões do pool (todas
    «normal»). O `grupo` de todos os decks é o mesmo — o pool: `need` é o
    máximo por carta, `alloc` o que o pool cobre disso, `missing` o que
    falta comprar para o pool —, com `lider` só no primeiro deck, para quem
    soma pelos líderes contar o pool uma vez. `shared`, `a_caminho`, os três
    montes da Coleção, o lugar especial e as «outras» vêm vazios: não há.
    """
    est = estado(con)
    cards = est["cards"]
    rows = decks.deck_rows(con)
    nomes = [r["display_name"] or r["name"] for r in rows]
    slugs = [r["name"] for r in rows]
    vazio = lambda: {}

    def servidas(ck: str, n: int) -> list[dict]:
        out = []
        for pid, q in cards[ck]["printings"].items():
            if n <= 0:
                break
            take = min(n, q)
            out.append({"id": pid, "qty": take, "lugar": "normal"})
            n -= take
        return out

    pool_need = {ck: c["need"] for ck, c in cards.items()}
    pool_alloc = {ck: min(c["need"], c["have"]) for ck, c in cards.items() if min(c["need"], c["have"])}
    pool_missing = {ck: c["missing"] for ck, c in cards.items() if c["missing"]}
    pool_versoes = {ck: servidas(ck, n) for ck, n in pool_alloc.items()}
    grupo_base = {
        "alloc": pool_alloc, "no_deck": {}, "no_binder": {}, "na_colecao": {},
        "no_pool": dict(pool_alloc), "a_caminho": {},
        "missing": pool_missing, "shared": {}, "need": pool_need,
        # Os três montes da Coleção ficam vazios de propósito (quem os lê
        # soma-os); o que saiu do pool vai à parte.
        "impressoes": {"no_deck": {}, "no_binder": {}, "na_colecao": {}},
        "impressoes_pool": {x["id"]: x["qty"] for vs in pool_versoes.values() for x in vs},
        "need_especial": {}, "alloc_especial": {}, "a_caminho_especial": {},
        "missing_especial": {}, "especial_em": {}, "alloc_outras": {},
        "versoes_em": pool_versoes,
        "legend": "pool", "rotulo": "Pool dos decks", "membros": nomes,
        "slugs": slugs, "variantes": False,
    }

    fora = decks.cartas_nao_contadas(con)
    out = {}
    for i, d in enumerate(rows):
        nd = decks._need(con, d["deck_id"], fora)
        alloc, missing, versoes_em = {}, {}, {}
        for ck, qty in nd.items():
            take = min(qty, cards.get(ck, {}).get("have", 0))
            if take:
                alloc[ck] = take
                versoes_em[ck] = servidas(ck, take)
            if qty - take:
                missing[ck] = qty - take
        out[d["deck_id"]] = {
            "alloc": alloc, "no_deck": {}, "no_binder": {}, "na_colecao": {},
            "no_pool": dict(alloc), "a_caminho": {}, "missing": missing,
            "shared": {}, "extra": {}, "partilhada": {},
            "need_especial": {}, "alloc_especial": {}, "a_caminho_especial": {},
            "missing_especial": {}, "especial_em": {}, "alloc_outras": {},
            "versoes_em": versoes_em,
            "grupo": {**grupo_base, "lider": i == 0},
        }
    return out


# ---------------------------------------------------------------------------
# O payload da aba
# ---------------------------------------------------------------------------


def _mercado(con: sqlite3.Connection) -> dict[str, dict]:
    return cardmarket.versoes(con)


def payload(con: sqlite3.Connection, cfg: dict | None = None,
            editable: bool = True, image_mode: str = "local") -> dict:
    """A vista do pool para a aba Decks: cartas, por deck, o que não serve,
    as sem base, e o resumo da wantlist. Sem euros como argumento — o preço
    aparece só na linha, como no A mais."""
    cfg = cfg or config.load()
    est = estado(con, cfg)
    versoes = est["versoes"]
    mercado = _mercado(con)
    precos = metrics.prices_map(con)
    nomes = {r["card_key"]: r for r in con.execute(
        "SELECT card_key, name, type FROM catalog.cards")}
    linhas = {r["printing_id"]: r for r in con.execute(
        "SELECT printing_id, public_code, set_id, orientation, image_medium, "
        "       image_large, image_url, variant_label FROM catalog.printings")}
    rows = decks.deck_rows(con)
    rotulo = {r["name"]: (r["display_name"] or r["name"]) for r in rows}

    def imagem(pid: str | None) -> dict:
        r = linhas.get(pid) if pid else None
        if r is None:
            return {"img": None, "cdn": None, "landscape": False}
        return {"img": f"img/{pid}.webp",
                "cdn": r["image_medium"] or r["image_large"] or r["image_url"],
                "landscape": (r["orientation"] or "").lower() == "landscape"}

    cards = []
    for ck, c in est["cards"].items():
        info = nomes.get(ck)
        # A impressão em que se compra o que falta — a base mais barata — é
        # também a cara da carta; se ele tem alguma no pool, mostra-se essa.
        compra = versoes.compra(ck)
        cara = next(iter(c["printings"]), None) or compra
        i = versoes.info(compra)
        mkt = mercado.get(compra) or {}
        preco = precos.get(compra) if compra else None
        cards.append({
            "card_key": ck, "name": info["name"] if info else ck,
            "type": info["type"] if info else None,
            "need": c["need"], "soma": c["soma"], "have": c["have"], "missing": c["missing"],
            "decks": [{"slug": s, "deck": rotulo.get(s, s), "qty": q}
                      for s, q in sorted(c["decks"].items(),
                                         key=lambda kv: next(
                                             (n for n, r in enumerate(rows) if r["name"] == kv[0]), 99))],
            "printings": [{"id": pid, "code": linhas[pid]["public_code"] if pid in linhas else pid,
                           "set": linhas[pid]["set_id"] if pid in linhas else None, "qty": q}
                          for pid, q in c["printings"].items()],
            # Onde o `+` grava e onde se compra: a base mais barata.
            "compra": {"id": compra, "code": i["code"], "set": i["set"], "price": i["price"]},
            "bases": [versoes.info(pid)["code"] for pid in versoes.normais_de(ck)],
            "sem_base": c["sem_base"],
            **imagem(cara),
            # Os campos do gerador do Cardmarket, como nas outras listas.
            "code": i["code"], "set": i["set"], "price": preco,
            "total": (preco or 0) * c["missing"],
            "market_name": mkt.get("name") if mkt.get("name") != (info["name"] if info else ck) else None,
            "market_set": mkt.get("set"),
            "v": mkt.get("v"), "n_versions": mkt.get("n", 1),
            "foil_only": bool(mkt.get("foil_only")),
        })
    cards.sort(key=lambda x: x["name"].casefold())

    fora = decks.cartas_nao_contadas(con, cfg)
    por_deck = []
    for r in rows:
        nd = decks._need(con, r["deck_id"], fora)
        faltam = []
        tem = 0
        for ck, q in sorted(nd.items(), key=lambda kv: (nomes.get(kv[0]) or {"name": kv[0]})["name"].casefold()):
            have = est["cards"].get(ck, {}).get("have", 0)
            tem += min(q, have)
            if q - min(q, have):
                faltam.append({"card_key": ck, "name": (nomes.get(ck) or {"name": ck})["name"],
                               "qty": q - min(q, have)})
        por_deck.append({
            "id": r["deck_id"], "slug": r["name"], "name": rotulo[r["name"]],
            "priority": r["priority"], "wanted": sum(nd.values()), "have": tem,
            "missing": sum(x["qty"] for x in faltam), "ok": not faltam,
            "faltam": faltam,
        })

    fora_itens = []
    for x in est["fora"]:
        r = linhas.get(x["printing_id"])
        info = nomes.get(x["card_key"]) if x["card_key"] else None
        fora_itens.append({**x, "name": info["name"] if info else x["printing_id"],
                           "code": r["public_code"] if r else None,
                           "label": r["variant_label"] if r else None,
                           **imagem(x["printing_id"] if r else None)})

    w = cardmarket.gerar([x for x in cards if x["missing"] > 0])
    return {
        "editable": editable, "image_mode": image_mode, "generated_at": _now(),
        "modo": decks.modo(cfg), "local": locais.POOL,
        "totals": {
            "cards": len(cards),
            "need": sum(x["need"] for x in cards),
            "soma": sum(x["soma"] for x in cards),
            "have": sum(min(x["have"], x["need"]) for x in cards),
            "missing": sum(x["missing"] for x in cards),
            "missing_cards": sum(1 for x in cards if x["missing"]),
            "in_pool": sum(stock(con).values()),
            "fora": sum(x["qty"] for x in est["fora"]),
            "decks": len(rows), "decks_ok": sum(1 for d in por_deck if d["ok"]),
        },
        "cards": cards,
        "por_deck": por_deck,
        "fora": fora_itens,
        "sem_base": [(nomes.get(ck) or {"name": ck})["name"] for ck in est["sem_base"]],
        "wantlist": {"lines": w["lines"], "copies": w["copies"], "cents": w["cents"],
                     "foil": len(w["foil"])},
    }


def wantlist(con: sqlite3.Connection, cfg: dict | None = None,
             com_codigo: bool = False) -> dict:
    """O texto para o Cardmarket do que falta ao pool — o gerador único."""
    p = payload(con, cfg)
    itens = [x for x in p["cards"] if x["missing"] > 0]
    return {**cardmarket.gerar(itens, com_codigo), "items": itens}


# ---------------------------------------------------------------------------
# Escrita: entrar e sair do pool
# ---------------------------------------------------------------------------


def ajustar(con: sqlite3.Connection, ref: str, delta: int, source: str = "web",
            request_id: str | None = None) -> dict:
    """Soma `delta` cópias de uma impressão BASE ao pool — no `copies` E no
    local `pool-decks`, numa transação só, para a Coleção (`copies − Σ fora`)
    ficar exactamente onde estava. É a única porta de entrada e saída.

    Um `−` nunca vai abaixo de zero no pool (não toca em cópias que estejam
    na Coleção ou noutro local). Um `request_id` repetido não aplica duas
    vezes (a `ops`, como no `collection.adjust`). Deixa rasto na `ops`, na
    `location_ops` (`(entrou no pool)` -> pool, pool -> `(saiu do pool)`) e
    no `data/locais.log`. Uma impressão que não seja base rebenta
    (`NaoBase`): o pool é só base, e aceitá-la era deixá-la lá sem servir.

    Cuidado com o `riftvault undo` genérico: reverte a linha da `ops` (as
    cópias) e o `ajustar_ao_total` tira-as do pool a seguir — um `+` desfaz-se
    bem; o undo de um `−` põe a cópia na Coleção, não no pool. Para tirar ou
    pôr no pool, é por aqui.
    """
    pid = collection.resolve_printing(con, ref)
    delta = int(delta)
    r = con.execute("SELECT * FROM catalog.printings WHERE printing_id = ?", (pid,)).fetchone()
    if r is None or r["variant_kind"] != "base" or metrics.e_overnumbered(r):
        raise NaoBase(f"{pid} não é uma versão base — o pool é só base")

    if request_id:
        prev = con.execute("SELECT id, delta FROM ops WHERE request_id = ?",
                           (request_id,)).fetchone()
        if prev:
            return {"printing_id": pid, "qty": locais._qty_em(con, pid, locais.POOL),
                    "total": collection.get_qty(con, pid), "applied": prev["delta"],
                    "op_id": prev["id"], "duplicate": True}

    con.execute("BEGIN IMMEDIATE")
    try:
        total = collection.get_qty(con, pid)
        no_pool = locais._qty_em(con, pid, locais.POOL)
        applied = delta if delta > 0 else max(delta, -no_pool)
        if applied == 0:
            con.execute("COMMIT")
            return {"printing_id": pid, "qty": no_pool, "total": total,
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
        locais._set_qty(con, pid, locais.POOL, no_pool + applied)
        de, para = (ENTROU, locais.POOL) if applied > 0 else (locais.POOL, SAIU)
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
    return {"printing_id": pid, "qty": no_pool + applied, "total": novo_total,
            "applied": applied, "op_id": op_id, "duplicate": False}

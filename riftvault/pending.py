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

OS `+`/`-` NAS FALTAS (André, 2026-09-27): *"nas faltas, coloca o + e - para eu
indicar que ja encomendei, fica bem mais facil para eu visualizar assim"*.

    TERCEIRA CASA DOS MESMOS BOTÕES, e não um mecanismo novo: nasceram nos
    tiles dos decks (2026-09-11), mudaram-se para o separador «Encomendas»
    (2026-09-17, *"e tiras esta funcionalidade dos decks"*) e chegam hoje ao
    separador «Faltas», que é onde ele olha quando decide comprar. A tabela é
    a mesma, a rota é a mesma (`POST /api/encomenda`) e o número é UM SÓ: as
    Faltas e as Encomendas leem-no daqui as duas. Um segundo contador punha as
    duas vistas a divergir, e era esse o erro a evitar.

    A LINHA NÃO DESAPARECE depois do `+`. O pendente já descontava das faltas
    desde 2026-09-11, e uma falta que sumisse ao ser encomendada era o
    contrário do que ele pediu («fica bem mais fácil para eu visualizar»): o
    `faltas_edicao.em_falta` e o `faltas_foil.em_falta` guardam o `pending` à
    parte do `missing`, por isso a linha fica lá, marcada, a dizer as duas
    coisas — quanto falta e quantas vêm a caminho. O que sai é só a WANTLIST:
    o que vem a caminho não se compra outra vez.

O ACABAMENTO DA ENCOMENDA (`foil`, 2026-09-27)

    Metade do separador «Faltas» é de FOILS, e uma foil encomendada tem de
    entrar como foil: o `copies.qty` e o `copies.qty_foil` são duas contagens
    independentes desde 2026-09-26. A `pending` guardava a impressão e não o
    acabamento, e por isso ganhou a coluna `foil` (0/1, migração no
    `db._migrar_pending_foil`; as linhas que lá estavam ficaram a 0 — eram
    todas de normais, que era a única coisa que havia como encomendar).

    A partir daqui o acabamento acompanha a encomenda de ponta a ponta: o `+`
    grava-o, o `-` só tira de linhas do mesmo acabamento, o «Chegou» soma ao
    contador certo (`collection.adjust` nas normais, `foil.ajustar` nas foils)
    e as leituras separam-se — `open_qty()` dá as NORMAIS (é este o pendente
    que as faltas normais, as wantlists e os decks descontam) e
    `open_qty(foil=True)` dá as foils, que só a metade das foils lê.
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
        source: str = "cli", foil: bool = False) -> dict:
    """Regista uma compra a caminho. Valida a impressão como o resto do código."""
    printing_id = collection.resolve_printing(con, ref)
    cur = con.execute(
        "INSERT INTO pending (printing_id, qty, unit_cents, ordered_at, note, foil) "
        "VALUES (?,?,?,?,?,?)", (printing_id, qty, unit_cents, _now(), note,
                                 1 if foil else 0))
    _log(con, [{"printing_id": printing_id, "qty": qty, "accao": "encomendar",
                "source": source, "nota": note, "foil": foil}])
    return {"id": cur.lastrowid, "printing_id": printing_id, "qty": qty,
            "foil": bool(foil)}


def _filtro_foil(foil: bool | None, prefixo: str = "") -> str:
    """A cláusula do acabamento (2026-09-27), para ser escrita num sítio só.

    `False` são as NORMAIS — é a omissão de toda a gente, e é o que faz as
    faltas normais, as wantlists e os decks continuarem a ver exactamente o que
    viam antes de haver encomendas de foil. `True` são as foils; `None` são as
    duas (o «Chegou tudo», os totais, a lista da consola).
    """
    if foil is None:
        return ""
    return f" AND {prefixo}foil = {1 if foil else 0}"


def open_qty(con: sqlite3.Connection, foil: bool | None = False) -> dict[str, int]:
    """printing_id -> quantas vêm a caminho e ainda não chegaram.

    Por omissão só as NORMAIS. Uma foil a caminho não abate uma falta normal —
    são duas contagens diferentes da mesma impressão (2026-09-26) e cada metade
    do separador «Faltas» lê a sua.
    """
    return {r["printing_id"]: r["q"] for r in con.execute(
        "SELECT printing_id, SUM(qty) AS q FROM pending "
        "WHERE arrived_at IS NULL" + _filtro_foil(foil) + " GROUP BY printing_id")}


def open_by_card(con: sqlite3.Connection) -> dict[str, int]:
    """card_key -> quantas vêm a caminho. É o grão das faltas.

    Junta o catálogo e as `market_only` — ele comprou runas do SFD que a
    RiftScribe não tem, e essas contam na mesma.

    Conta só o que pode SERVIR OS DECKS (`decks.Versoes.serve`): uma assinada
    ou uma runa em alt art (retirada, 2026-09-17) encomendada não conta para
    nada. É informação; quem desconta o pendente lugar a lugar (a versão
    especial da Legend/Champion não abate uma falta normal, nem o contrário)
    é a alocação, por impressão (`open_qty`).

    SÓ AS NORMAIS (2026-09-27): um deck joga uma foil como joga uma normal,
    mas a alocação serve-se primeiro das normais (`decks.foils_nos_decks`,
    2026-09-26) e o monte dela é o `copies.qty`. Uma foil a caminho não é uma
    normal a caminho, e contá-la aqui era abater uma falta de deck com uma
    cópia que a alocação não vai encontrar.
    """
    from . import decks

    versoes = decks.versoes_dos_decks(con)
    out: dict[str, int] = {}
    for r in con.execute(
        "SELECT p.printing_id, p.card_key, p.card_key AS k, p.variant_kind, p.set_id, "
        "       SUM(pe.qty) AS q "
        "FROM pending pe "
        "JOIN catalog.printings p ON p.printing_id = pe.printing_id "
        "WHERE pe.arrived_at IS NULL AND pe.foil = 0 GROUP BY p.printing_id"
    ):
        if versoes.serve(r):
            out[r["k"]] = out.get(r["k"], 0) + r["q"]
    for r in con.execute(
        "SELECT m.card_key AS k, SUM(pe.qty) AS q FROM pending pe "
        "JOIN catalog.market_only m ON m.printing_id = pe.printing_id "
        "WHERE pe.arrived_at IS NULL AND pe.foil = 0 "
        "AND m.card_key IS NOT NULL GROUP BY m.card_key"
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
               especial: bool = False, foil: bool = False,
               cfg: dict | None = None) -> dict:
    """O `+`: mais `qty` cópias a caminho desta carta.

    Com `printing_id` grava nessa impressão; só com `card_key`, na normal
    mais barata — ou, com `especial`, na versão especial mais barata, que é o
    `+` da linha da Legend/Champion (`impressao_para_encomendar`). Devolve o
    que ficou aberto.

    Com `foil` a linha fica marcada como FOIL (2026-09-27): é o `+` da metade
    das foils do separador «Faltas», e quando chegar soma ao `copies.qty_foil`
    e não ao `qty`. Valida-se AQUI que a impressão tem contagem de foil
    (`foil.no_ambito`, o mesmo âmbito do contador do tile e da metade das
    faltas): marcar foil numa impressão sem contador era gravar uma encomenda
    que nenhuma página sabe mostrar.
    """
    from . import foil as foil_mod

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
    if foil:
        r = con.execute("SELECT * FROM catalog.printings WHERE printing_id = ?",
                        (printing_id,)).fetchone()
        if r is None or not foil_mod.no_ambito(r, cfg or config.load()):
            raise foil_mod.ForaDoAmbito(
                f"{printing_id} não tem contagem de foil — não se pode "
                f"encomendar uma foil dela")
    con.execute("BEGIN IMMEDIATE")
    con.execute(
        "INSERT INTO pending (printing_id, qty, unit_cents, ordered_at, note, foil) "
        "VALUES (?,?,?,?,?,?)",
        (printing_id, qty, None, _now(), note, 1 if foil else 0))
    con.execute("COMMIT")
    _log(con, [{"printing_id": printing_id, "qty": qty, "accao": "encomendar",
                "source": source, "nota": note, "foil": foil}])
    return _estado(con, card_key, printing_id, foil)


def anular(con: sqlite3.Connection, card_key: str | None = None,
           printing_id: str | None = None, qty: int = 1,
           source: str = "web", especial: bool | None = None,
           foil: bool | None = None) -> dict:
    """O `−`: menos `qty` a caminho. Tira das linhas abertas mais recentes.

    Com `printing_id` tira só dessa impressão; só com `card_key`, de qualquer
    impressão da carta — ou, com `especial` `True`/`False`, só das versões
    especiais / só das normais (o `−` da linha da Legend/Champion não pode
    tirar a encomenda de uma cópia normal, nem o contrário; 2026-09-17).
    Nunca vai abaixo de zero: se não há nada aberto, `SemEncomenda`; se há
    menos do que `qty`, tira o que há e diz quanto.

    `foil` é a mesma ideia para o ACABAMENTO (2026-09-27): `True` só tira
    linhas de foil, `False` só de normais, `None` (a omissão, que é o que a CLI
    antiga faz) tira de qualquer uma. O `−` de uma metade do separador «Faltas»
    não pode desfazer a encomenda da outra.

    **Só mexe em linhas por chegar** (`arrived_at IS NULL`), aqui e desde
    sempre: o que já entrou na coleção desfaz-se pelo `riftvault undo`, não por
    aqui.
    """
    if qty <= 0:
        raise ValueError("a quantidade tem de ser positiva")
    ffoil = _filtro_foil(foil, "pe.")
    if printing_id:
        printing_id = collection.resolve_printing(con, printing_id)
        card_key = _card_key(con, printing_id) or card_key
        linhas = con.execute(
            "SELECT pe.id, pe.printing_id, pe.qty FROM pending pe "
            "WHERE pe.arrived_at IS NULL AND pe.printing_id = ?" + ffoil +
            " ORDER BY pe.id DESC", (printing_id,)).fetchall()
    else:
        if not card_key:
            raise ValueError("falta a carta")
        linhas = con.execute(
            "SELECT pe.id, pe.printing_id, pe.qty, p.card_key FROM pending pe "
            "LEFT JOIN catalog.printings p ON p.printing_id = pe.printing_id "
            "LEFT JOIN catalog.market_only m ON m.printing_id = pe.printing_id "
            "WHERE pe.arrived_at IS NULL AND COALESCE(p.card_key, m.card_key) = ?"
            + ffoil + " ORDER BY pe.id DESC", (card_key,)).fetchall()
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
                        "source": source, "foil": foil})
    con.execute("COMMIT")
    _log(con, tiradas)
    res = _estado(con, card_key, tiradas[-1]["printing_id"] if tiradas else printing_id,
                  foil)
    res["removed"] = qty - falta
    return res


def _estado(con: sqlite3.Connection, card_key: str | None, printing_id: str | None,
            foil: bool | None = None) -> dict:
    """O que ficou a caminho da carta e da impressão depois de um `+`/`−`.

    `open_printing` é do MESMO acabamento do botão que foi carregado — é o
    número que o tile das Faltas escreve. `open_normal`/`open_foil` vão os dois
    a par, para quem precise dos dois sem segundo pedido (o tile do separador
    «Encomendas»). O `open_card` continua a ser só das normais: é o grão dos
    decks (ver o `open_by_card`).
    """
    normais = open_qty(con, foil=False)
    foils = open_qty(con, foil=True)
    aqui = (normais if not foil else foils) if foil is not None else None
    return {
        "card_key": card_key, "printing_id": printing_id,
        "foil": None if foil is None else bool(foil),
        "open_card": open_by_card(con).get(card_key, 0) if card_key else 0,
        "open_printing": (
            (aqui if aqui is not None
             else {k: normais.get(k, 0) + foils.get(k, 0)
                   for k in set(normais) | set(foils)}).get(printing_id, 0)
            if printing_id else 0),
        "open_normal": normais.get(printing_id, 0) if printing_id else 0,
        "open_foil": foils.get(printing_id, 0) if printing_id else 0,
    }


def listar(con: sqlite3.Connection, incluir_chegadas: bool = False,
           foil: bool | None = None) -> list[dict]:
    """As linhas a caminho. `foil` filtra o acabamento (omissão: as duas).

    O `foil` de cada linha vem no `pe.*` — quem mostra a lista tem de o dizer,
    senão uma foil a caminho lê-se como uma normal.
    """
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
    sql += "WHERE 1=1 " if incluir_chegadas else "WHERE pe.arrived_at IS NULL "
    sql += _filtro_foil(foil, "pe.") + " "
    sql += "ORDER BY COALESCE(p.set_id, m.set_id), name"
    out = []
    for r in con.execute(sql):
        d = dict(r)
        d["landscape"] = (d.pop("orientation", None) or "").lower() == "landscape"
        d["foil"] = bool(d.get("foil"))
        out.append(d)
    return out


def arrive(con: sqlite3.Connection, pending_id: int | list[int] | None = None,
           source: str = "cli", card_key: str | None = None,
           printing_id: str | None = None, foil: bool | None = None) -> list[dict]:
    """Marca como chegada e passa para a coleção.

    Sem `pending_id`, `card_key` nem `printing_id`, dá entrada em tudo o que
    está aberto (o «Chegou tudo»); com `printing_id`, em tudo o que está
    aberto dessa impressão (o «Chegou» do tile do separador «Encomendas»,
    2026-09-17); com `card_key`, em tudo o que está aberto dessa carta, seja
    de que impressão for; com uma lista de ids, só nessas linhas; com `foil`,
    só do acabamento pedido. É idempotente por construção: só apanha linhas
    ainda sem `arrived_at`, e a segunda chamada não encontra nenhuma.

    CADA LINHA ENTRA NO CONTADOR DELA (2026-09-27). Uma normal passa pelo
    `collection.adjust` — `copies.qty`, entrada no `ops`, `riftvault undo`
    —, e uma FOIL pelo `foil.ajustar`, que soma ao `copies.qty_foil` e deixa
    rasto na `foil_ops`. Fazer entrar uma foil como normal estragava-lhe a
    contagem, que são duas colunas independentes desde 2026-09-26.

    O desfazer é por isso diferente nas duas: uma normal desfaz-se com
    `riftvault undo` (a `ops`), uma foil com `riftvault foil REF --menos N`. O
    `foil.ajustar` corre aqui **sem validar o âmbito**: uma foil que ele já
    encomendou tem de poder chegar mesmo que o `foil.raridades` entretanto
    encolha — recusar a entrada era perder-lhe a cópia. Quem valida é o `+`.
    """
    from . import foil as foil_mod

    sql = ("SELECT pe.* FROM pending pe "
           "LEFT JOIN catalog.printings p ON p.printing_id = pe.printing_id "
           "LEFT JOIN catalog.market_only m ON m.printing_id = pe.printing_id "
           "WHERE pe.arrived_at IS NULL" + _filtro_foil(foil, "pe."))
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
        e_foil = bool(r["foil"])
        if e_foil:
            res = foil_mod.ajustar(con, r["printing_id"], r["qty"], source=source,
                                   validar=False)
            total = res["foil"]
        else:
            total = collection.adjust(con, r["printing_id"], r["qty"],
                                      source=source)["qty"]
        con.execute("UPDATE pending SET arrived_at = ? WHERE id = ?", (_now(), r["id"]))
        feitas.append({"id": r["id"], "printing_id": r["printing_id"],
                       "qty": r["qty"], "total": total, "foil": e_foil})
    _log(con, [{"printing_id": f["printing_id"], "qty": f["qty"], "accao": "chegou",
                "source": source, "foil": f["foil"]} for f in feitas])
    return feitas


def totals(con: sqlite3.Connection, foil: bool | None = None) -> dict:
    """O que está a caminho, ao todo. Sem `foil`, as duas contagens somadas —
    e `copies_foil` diz quanto disso é foil (2026-09-27), para o cabeçalho não
    ter de fazer um segundo pedido."""
    r = con.execute(
        "SELECT COALESCE(SUM(qty),0) AS copias, COUNT(*) AS linhas, "
        "       COALESCE(SUM(qty * COALESCE(unit_cents,0)),0) AS cents, "
        "       COALESCE(SUM(CASE WHEN foil = 1 THEN qty ELSE 0 END),0) AS foils "
        "FROM pending WHERE arrived_at IS NULL" + _filtro_foil(foil)).fetchone()
    return {"copies": r["copias"], "lines": r["linhas"], "cents": r["cents"],
            "copies_foil": r["foils"]}


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
    pela CLI, uma runa do CardTrader que a RiftScribe não tem, **e todas as
    foils** (o âmbito do foil é comuns e incomuns, e o corte aqui é de rara
    para cima) — vai em `fora`, com nome, acabamento e quantidade, para não
    haver encomenda que não se veja.
    """
    from . import metrics

    cfg = cfg or config.load()
    p = metrics.set_payload(con, set_id, editable=editable, image_mode=image_mode)
    abertas = open_qty(con)
    abertas_foil = open_qty(con, foil=True)
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
                           "ordered": abertas.get(pr["id"], 0),
                           # As foils a caminho desta impressão (2026-09-27).
                           # Hoje é sempre 0 aqui — o corte é de rara para cima
                           # e o foil só existe em comuns e incomuns —, mas o
                           # número é o mesmo da metade das foils das Faltas, e
                           # tem de aparecer se ele baixar a raridade mínima.
                           "ordered_foil": abertas_foil.get(pr["id"], 0)})
        groups.append({**{k: g[k] for k in _CAMPOS_GRUPO}, "printings": prints})

    por_bloco: dict[str, list[int]] = {}
    for g in groups:
        for pr in g["printings"]:
            slot = por_bloco.setdefault(pr["block"], [0, 0, 0, 0])
            slot[0] += 1
            slot[1] += pr["ordered"]
            slot[2] += 1 if (pr["ordered"] or pr["ordered_foil"]) else 0
            slot[3] += pr["ordered_foil"]
    blocks = [
        {"id": b["id"], "label": b["label"], "short": b["short"], "counts": b["counts"],
         "printings": por_bloco[b["id"]][0], "ordered": por_bloco[b["id"]][1],
         "ordered_printings": por_bloco[b["id"]][2],
         "ordered_foil": por_bloco[b["id"]][3]}
        for b in p["blocks"] if b["id"] in por_bloco
    ]

    fora = [{"printing_id": it["printing_id"], "name": it["name"], "code": it["code"],
             "label": it["label"], "market_only": bool(it["market_only"]),
             "foil": bool(it["foil"]), "qty": it["qty"]}
            for it in listar(con)
            if it["set_id"] == set_id and it["printing_id"] not in na_grelha]
    # A mesma impressão pode ter várias linhas abertas: uma por compra. O
    # ACABAMENTO faz parte da chave — uma normal e uma foil da mesma impressão
    # são duas linhas, com dois «Chegou», porque entram em contadores
    # diferentes.
    fora_por_pid: dict[tuple[str, bool], dict] = {}
    for f in fora:
        chave = (f["printing_id"], f["foil"])
        e = fora_por_pid.get(chave)
        if e is None:
            fora_por_pid[chave] = dict(f)
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
            "ordered_foil": sum(b["ordered_foil"] for b in blocks),
            "ordered_printings": sum(b["ordered_printings"] for b in blocks),
            # As impressões da página da Coleção que o corte tirou — para o
            # cabeçalho dizer «174 de 334».
            "printings_colecao": sum(len(g["printings"]) for g in p["groups"]),
        },
        "fora": sorted(fora_por_pid.values(),
                       key=lambda x: (x["code"] or "", x["name"] or "", x["foil"])),
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

    itens = listar(con)
    precos = {r["printing_id"]: r["price_cents"] for r in con.execute(
        "SELECT printing_id, price_cents FROM catalog.price_latest "
        "WHERE price_cents IS NOT NULL")}
    # Uma cópia FOIL vale o preço da foil (2026-09-26, à noite); sem oferta
    # foil cai para o da normal, que é o fallback de sempre.
    precos_foil = {r["printing_id"]: r["c"] for r in con.execute(
        "SELECT printing_id, COALESCE(price_foil_cents, "
        "       CASE WHEN from_foil = 1 THEN price_cents END) AS c "
        "FROM catalog.price_latest") if r["c"] is not None}
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

    # Uma linha por (impressão, ACABAMENTO): a normal e a foil da mesma carta
    # são duas compras, com dois preços e dois «Chegou» (2026-09-27).
    por_impressao: dict[tuple[str, bool], dict] = {}
    for it in itens:
        pid = it["printing_id"]
        e_foil = bool(it["foil"])
        chave = (pid, e_foil)
        e = por_impressao.get(chave)
        if e is None:
            e = por_impressao[chave] = {
                "printing_id": pid, "card_key": it["card_key"], "name": it["name"],
                "code": it["code"], "set": it["set_id"], "label": it["label"],
                "market_only": bool(it["market_only"]), "img": it["img"],
                "cdn": it["cdn"], "landscape": it["landscape"], "foil": e_foil,
                "qty": 0,
                "price": (precos_foil.get(pid) if e_foil else precos.get(pid)),
                "total": 0, "paid": 0, "ids": [], "notes": [],
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
        # de prioridade até esgotar a quantidade desta impressão. Uma FOIL não
        # entra: a alocação serve-se das normais (`open_by_card` já a saltou),
        # e por isso uma foil a caminho é sempre «para a Coleção».
        falta, dest = e["qty"], []
        for h in ([] if e["foil"] else sobra.get(e["card_key"], [])):
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
                                   x["code"] or "", x["foil"])):
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
            "printings": len({e["printing_id"] for e in por_impressao.values()}),
            "lines": len(por_impressao),
            "copies": sum(e["qty"] for e in por_impressao.values()),
            "copies_foil": sum(e["qty"] for e in por_impressao.values() if e["foil"]),
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
    """Uma linha por movimento no `encomendas.log` DE QUEM encomendou.
    Nunca impede a escrita.

    É o gémeo do `locais.log` — inclusive no caminho, que vem do
    `config.log_path(con, ...)` desde 2026-10-02 (antes era sempre a pasta do
    André, fosse quem fosse que estivesse a encomendar, e sem coluna de dono).
    E na promessa: se uma encomenda aparecer ou desaparecer sem
    linha aqui, é bug. Colunas: quando, impressão, código, nome, quantidade,
    acabamento (normal/foil, desde 2026-09-27), acção (encomendar / anular /
    chegou), origem (web, cli, deck de onde veio o clique) e a nota.

    A coluna do acabamento entra no FIM, e o cabeçalho só se escreve quando o
    ficheiro nasce: um log antigo continua a ler-se, com uma coluna a menos nas
    linhas velhas — que eram todas de normais.
    """
    if not linhas:
        return
    caminho = config.log_path(con, LOG_NAME)
    novo = not caminho.exists()
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    if novo:
        w.writerow(["quando", "printing_id", "codigo", "nome", "quantidade",
                    "accao", "origem", "nota", "acabamento"])
    ts = _now()
    for x in linhas:
        d = _descrever(con, x["printing_id"])
        acab = x.get("foil")
        w.writerow([ts, x["printing_id"], d["code"] or "", d["name"] or "",
                    x["qty"], x["accao"], x.get("source") or "", x.get("nota") or "",
                    "" if acab is None else ("foil" if acab else "normal")])
    try:
        caminho.parent.mkdir(parents=True, exist_ok=True)
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

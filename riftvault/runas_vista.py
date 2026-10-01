"""O bloco «Runas — 12 de cada» no fim da grelha da Coleção — O CONTADOR DELE.

André, 2026-09-19, de manhã: *"depois mete 12 runas de cada (nao contabilizes
para nada, e so para mim para contabilizar ali algumas coisas)"*. E à tarde,
ao pedir os botões: *"runas nao contabilizam nada, eu e que mexo nisso para
minha referencia, nao entram para decks, nao entram para coleccao, nada, so
para mim"*.

É UM CONTADOR, não uma categoria da Coleção — e desde a tarde de 19/09 o
número que o bloco mostra é DELE, não calculado: os `+`/`−` do bloco escrevem
na tabela `rune_counter` do vault.db e em mais lado nenhum. Nada aqui entra
no denominador (928), na percentagem, nos níveis, nas wantlists, no valor,
nas Faltas, no «A mais», nos decks nem no «tens N no playset completo» de
bloco nenhum; e nada daqui é lido por quem faz essas contas. Por isso vive
num módulo à parte, com URL próprio (`api/runas.json`), e NENHUM módulo de
contas o importa — `tests/test_runas_vista.py` lê o código-fonte e recusa a
importação, e mede que pôr os contadores todos a 99 ou a 0 não mexe em
número nenhum do resto. Quem o chama é só o `server`, o `build` e a CLI. É o
mesmo cuidado da montra «Promos» de 2026-09-18 (apagada nesse dia).

A SEMENTEIRA É UMA, NÃO É SINCRONIZAÇÃO. Começar a zero obrigava-o a carregar
74 vezes, por isso cada runa nasce com o que ele fisicamente tinha no momento
em que a linha foi criada (`semear`); a partir daí o número é dele e nunca
mais se recalcula a partir da coleção — uma linha a 0 é uma linha dele, não
uma linha por semear. Uma runa que apareça no catálogo mais tarde (edição
nova) semeia-se nessa altura, uma vez, pela mesma regra.

O QUE FICA AO LADO, EM LETRA PEQUENA — «na coleção: N» — é o que o bloco
calculava até aqui, e continua a calcular, só para ele comparar o que contou
à mão com o que o sistema sabe: **tudo o que ele fisicamente tem** de cada
runa, esteja onde estiver (Coleção, deck, binder) e seja que impressão for —
a base do OGN (a sequência), a arte alternativa do OGN (RETIRADA de tudo
desde 2026-09-17, `runas_especiais.retiradas`), a promo do VEN (escondida
desde 2026-09-15) e as do CardTrader que a RiftScribe não tem
(`market_only`: as `SFD-R02a` e companhia, que hoje nenhum sítio mostra).
Como isto contraria a retirada, o payload leva os DOIS números — `total` e
`sem_retiradas`. Não é contabilidade: é referência.

A REFERÊNCIA É DA EDIÇÃO ABERTA, desde 2026-10-01. André: *"A contagem das
runas Alt.Art é exclusiva para cada edição / vi que a contagem está a ser
partilhada por todas as edições"*. Até aqui o bloco somava num número só as
impressões das cinco edições e repetia-o em todas: na página do OGN a Calm
Rune dizia «na coleção: 21», e 12 dessas eram as `SFD-R02a`; na do UNL dizia
o mesmo 21 sem ele ter lá uma única runa. A arte alternativa de cada edição é
uma CARTA PRÓPRIA — é a regra da Coleção inteira (um alvo por impressão, um
bloco por edição) —, por isso `por_edicao` dá, para cada edição, as runas
dela, as origens dela e o total dela; o `runas`/`totals` do topo continua a
ser a soma, e é o que o separador «Todas» mostra. Continua a ser UM ficheiro
(`api/runas.json`): as seis runas são as mesmas em toda a parte, o que muda é
a impressão.

O CONTADOR NÃO SE PARTIU POR EDIÇÃO, e isso é decisão a tomar por ele: o
alvo dele é «12 de cada», que é o Rune Pool de um deck, e 12 × 6 × 4 edições
(288) não é uma coisa que se tenha nem se jogue. Os seis números que ele
contou à mão não têm edição nenhuma gravada e não se podem repartir sem os
inventar. Por isso o crachá é o mesmo nas quatro edições, e o cabeçalho
DIZ-LO em vez de o esconder.

«Runa» é o `runas_especiais.tipos`, a mesma definição da Coleção e dos
decks; o alvo (`runas_vista.alvo`, 12) é o número dele e não o do Rune Pool,
embora hoje coincidam.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from . import config, metrics

# O número que ele disse: «12 runas de cada». Só para a vista.
ALVO_OMISSAO = 12

# A frase que tem de estar no ecrã: o número é dele, os botões só mexem nele,
# e as 6 runas base do OGN já aparecem na sequência do master set (a 3) e
# voltam a aparecer aqui. Não é duplicação — é outra pergunta («quantas tenho
# na mão») — mas tem de se ler.
NOTA = ("o número é teu: os + e − mexem só nele e não contam para nada — nem "
        "coleção, nem decks, nem métricas, e é o mesmo em todas as edições. Ao "
        "lado, «nesta edição» é o que o site sabe que tens das impressões "
        "DESTA edição — a arte alternativa de cada edição é uma carta própria "
        "—, só para comparares. As runas base do OGN também estão na "
        "sequência do master set, em cima.")


class RunaDesconhecida(LookupError):
    """O `card_key` não é uma runa do catálogo — não há contador para ele."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def opcoes(cfg: dict | None = None) -> dict:
    cfg = cfg or config.load()
    out = {"alvo": ALVO_OMISSAO}
    out.update({k: v for k, v in (cfg.get("runas_vista") or {}).items()
                if not k.startswith("_")})
    return out


def alvo(cfg: dict | None = None) -> int:
    n = int(opcoes(cfg)["alvo"])
    if n <= 0:
        raise ValueError(f"runas_vista.alvo: tem de ser positivo, veio {n}")
    return n


def tipos(cfg: dict | None = None) -> tuple[str, ...]:
    """O que é uma runa — o `runas_especiais.tipos`, para não haver duas
    definições. Vazio (ninguém é runa) dá um bloco vazio, não um erro."""
    return tuple(metrics.opcoes_runa(cfg).get("tipos") or ())


def _qtys(con: sqlite3.Connection) -> dict[str, int]:
    return {r["printing_id"]: r["qty"] for r in con.execute("SELECT printing_id, qty FROM copies")}


def _na_colecao(con: sqlite3.Connection, cfg: dict) -> dict[str, dict]:
    """A referência «na coleção»: uma linha por runa (`card_key`) com tudo o
    que ele fisicamente tem dela, de todas as versões, e as origens.

    Cada origem diz a EDIÇÃO a que pertence e traz o tile dela — é com isso
    que o `por_edicao` responde por edição sem segunda consulta."""
    tps = tipos(cfg)
    qty = _qtys(con)

    runas: dict[str, dict] = {}   # card_key -> a linha
    if tps:
        marcas = ",".join("?" * len(tps))
        rows = con.execute(
            f"SELECT * FROM catalog.printings WHERE type IN ({marcas}) "
            "ORDER BY card_key, api_sort", tps).fetchall()
    else:
        rows = []
    for r in rows:
        ck = r["card_key"]
        linha = runas.get(ck)
        if linha is None:
            linha = runas[ck] = {
                "card_key": ck, "name": r["name"], "type": r["type"],
                # O tile sai do `_fechar`, da primeira impressão BASE do
                # conjunto; se não houver base, da primeira que aparecer.
                "code": None, "img": None, "cdn": None, "landscape": False,
                "origens": [], "total": 0, "sem_retiradas": 0, "_todas": [],
            }
        n = qty.get(r["printing_id"], 0)
        retirada = metrics.retirada(r, cfg)
        _somar(linha, {
            "id": r["printing_id"], "set_id": r["set_id"],
            "code": r["public_code"], "kind": r["variant_kind"],
            "label": _rotulo(r, cfg, retirada), "qty": n,
            "retirada": retirada, "escondida": metrics.escondida(r, cfg),
            "fora_do_catalogo": False,
            "base": r["variant_kind"] == "base",
            "img": f"img/{r['printing_id']}.webp",
            "cdn": r["image_medium"] or r["image_large"] or r["image_url"],
            "landscape": (r["orientation"] or "").lower() == "landscape",
        })

    # As runas que só o CardTrader lista (`market_only`): fora do catálogo,
    # não contam para métrica nenhuma em lado nenhum — mas estão na mão dele
    # (as 23 alt arts do SFD, medido a 2026-09-17). A arte alternativa
    # reconhece-se pela `version`, como no Pimp; é retirada como as do OGN.
    if runas:
        marcas = ",".join("?" * len(runas))
        mo = con.execute(
            f"SELECT printing_id, set_id, collector_raw, card_key, version, image_url "
            f"FROM catalog.market_only WHERE card_key IN ({marcas}) "
            "ORDER BY card_key, set_id, collector_raw", list(runas)).fetchall()
        for r in mo:
            n = qty.get(r["printing_id"], 0)
            linha = runas[r["card_key"]]
            alt = "alternate art" in (r["version"] or "").lower()
            retirada = alt and metrics.retirada(
                {"type": linha["type"], "variant_kind": "alt_art"}, cfg)
            # O CardTrader omite o `a` na Calm Rune do SFD; a carta impressa
            # leva-o (ver `faltas.pimp`).
            raw = r["collector_raw"] or ""
            codigo = f"{r['set_id']}-{raw}" + ("a" if alt and not raw.lower().endswith("a") else "")
            _somar(linha, {
                "id": r["printing_id"], "set_id": r["set_id"], "code": codigo,
                "kind": "alt_art" if alt else "base",
                "label": ("alt art (CardTrader, retirada)" if retirada
                          else "alt art (CardTrader)" if alt else "CardTrader"),
                "qty": n, "retirada": retirada, "escondida": False,
                "fora_do_catalogo": True,
                "base": not alt,
                # Fora do catálogo não há imagem em cache: só o CDN do
                # CardTrader, como no Pimp (`faltas.pimp`).
                "img": None, "cdn": r["image_url"], "landscape": False,
            })

    for linha in runas.values():
        _fechar(linha, linha["_todas"])
    return runas


def edicoes(referencia: dict[str, dict]) -> list[str]:
    """As edições que TÊM runas, pela ordem dos separadores da Coleção (a do
    config, pelo `set_order`). Uma edição sem runa nenhuma — o OGS — não
    entra, e por isso não ganha bloco: até 2026-10-01 ganhava, com as seis
    runas das outras edições."""
    sids = {o["set_id"] for linha in referencia.values() for o in linha["_todas"]}
    return sorted(sids, key=lambda s: (config.set_order(s), s))


def por_edicao(referencia: dict[str, dict]) -> dict[str, dict]:
    """Uma cópia da referência por edição: as runas dessa edição, as origens
    dessa edição e os totais dessa edição. A runa que a edição não tem não
    aparece — o `cards` dos totais é o das runas DELA."""
    out: dict[str, dict] = {}
    for sid in edicoes(referencia):
        linhas = {}
        for ck, linha in referencia.items():
            minhas = [o for o in linha["_todas"] if o["set_id"] == sid]
            if not minhas:
                continue
            nova = {k: v for k, v in linha.items() if k not in ("_todas", "origens")}
            nova["_todas"] = minhas
            _fechar(nova, minhas)
            linhas[ck] = nova
        out[sid] = linhas
    return out


# ---------------------------------------------------------------- o contador


def semear(con: sqlite3.Connection, cfg: dict | None = None,
           referencia: dict[str, dict] | None = None) -> dict[str, int]:
    """Cria a linha do contador de cada runa que ainda não a tem, com o que
    ele fisicamente tem dela HOJE (o `total` da referência). Devolve o que
    semeou (`card_key -> valor`); vazio quando não há nada por semear.

    É a única vez que o contador lê a coleção. Uma linha que já exista — a
    0, a 99, seja o que for — é dele e não se toca: por isso semear duas
    vezes seguidas semeia zero na segunda, e é isso que o distingue de uma
    sincronização.
    """
    cfg = cfg or config.load()
    if referencia is None:
        referencia = _na_colecao(con, cfg)
    if not referencia:
        return {}
    marcas = ",".join("?" * len(referencia))
    ja = {r["card_key"] for r in con.execute(
        f"SELECT card_key FROM rune_counter WHERE card_key IN ({marcas})",
        list(referencia))}
    novas = {ck: linha["total"] for ck, linha in referencia.items() if ck not in ja}
    if novas:
        agora = _now()
        con.executemany(
            "INSERT INTO rune_counter (card_key, qty, seeded_from, updated_at) "
            "VALUES (?,?,?,?)",
            [(ck, n, n, agora) for ck, n in novas.items()])
    return novas


def _contadores(con: sqlite3.Connection) -> dict[str, int]:
    return {r["card_key"]: r["qty"] for r in con.execute("SELECT card_key, qty FROM rune_counter")}


def ajustar(con: sqlite3.Connection, card_key: str, delta: int,
            cfg: dict | None = None) -> dict:
    """O `+`/`−` do bloco: `qty = qty + delta`, nunca abaixo de zero.

    Escreve SÓ na `rune_counter` — não no `copies`, não no `ops`, não no
    `pending`, não nos locais. Um `card_key` que não seja runa do catálogo
    rebenta (`RunaDesconhecida`): não há contador para o que não é runa. A
    runa que ainda não tenha linha é semeada primeiro, pela regra de sempre,
    e só depois ajustada — o `+` numa runa nova não a faz nascer a 1.
    """
    cfg = cfg or config.load()
    card_key = (card_key or "").strip().casefold()
    referencia = _na_colecao(con, cfg)
    if card_key not in referencia:
        raise RunaDesconhecida(f"{card_key!r} não é uma runa do catálogo")
    delta = int(delta)
    con.execute("BEGIN IMMEDIATE")
    try:
        semear(con, cfg, referencia)
        antes = con.execute("SELECT qty FROM rune_counter WHERE card_key = ?",
                            (card_key,)).fetchone()["qty"]
        # O chão é zero: um `−` a 0 fica a 0, sem erro — é um contador dele,
        # não uma encomenda por anular.
        depois = max(0, antes + delta)
        con.execute("UPDATE rune_counter SET qty = ?, updated_at = ? WHERE card_key = ?",
                    (depois, _now(), card_key))
        con.execute("COMMIT")
    except BaseException:
        con.execute("ROLLBACK")
        raise
    n_alvo = alvo(cfg)
    return {"card_key": card_key, "qty": depois, "delta": depois - antes,
            "name": referencia[card_key]["name"],
            "na_colecao": referencia[card_key]["total"],
            "totals": _totals(con, referencia, n_alvo),
            # O contador é o mesmo em todas as edições, mas o cabeçalho de
            # cada uma mostra-o: o servidor devolve os totais das duas vistas
            # para não haver uma segunda aritmética no cliente.
            "totals_por_edicao": {sid: _totals(con, linhas, n_alvo) for sid, linhas
                                  in por_edicao(referencia).items()}}


def _totals(con: sqlite3.Connection, referencia: dict, n_alvo: int) -> dict:
    cont = _contadores(con)
    return {
        "cards": len(referencia),
        "contador": sum(cont.get(ck, 0) for ck in referencia),
        "total": sum(x["total"] for x in referencia.values()),
        "sem_retiradas": sum(x["sem_retiradas"] for x in referencia.values()),
        "alvo": n_alvo * len(referencia),
    }


def payload(con: sqlite3.Connection, cfg: dict | None = None,
            image_mode: str = "local", editable: bool = False) -> dict:
    cfg = cfg or config.load()
    n_alvo = alvo(cfg)
    referencia = _na_colecao(con, cfg)
    # A sementeira acontece na primeira leitura que encontre uma runa sem
    # linha — é o único momento em que ler o bloco escreve, e escreve só na
    # tabela dele.
    semeadas = semear(con, cfg, referencia)
    cont = _contadores(con)

    def _itens(linhas: dict[str, dict]) -> list[dict]:
        out = []
        for linha in sorted(linhas.values(), key=lambda x: x["name"]):
            linha = {k: v for k, v in linha.items() if k != "_todas"}
            # O contador é o DELE e é o mesmo em todas as edições — ver o topo
            # do módulo: 12 de cada é o Rune Pool, não um alvo por edição.
            linha["contador"] = cont.get(linha["card_key"], 0)
            linha["target"] = n_alvo
            out.append(linha)
        return out

    return {
        "generated_at": _now(),
        "image_mode": image_mode,
        # Os `+`/`−` só no modo edição, como em toda a parte.
        "editable": editable,
        # A marca de que isto não conta para nada: o cliente e os testes lêem-na.
        "so_para_ver": True,
        "alvo": n_alvo,
        "nota": NOTA,
        # A soma das edições — é o que o separador «Todas» mostra.
        "runas": _itens(referencia),
        "semeadas": semeadas,
        "totals": _totals(con, referencia, n_alvo),
        # Uma entrada por edição COM runas (2026-10-01): as runas dela, as
        # origens dela e o total dela. O OGS não tem runas e não entra.
        "por_edicao": {sid: {"set_id": sid, "runas": _itens(linhas),
                             "totals": _totals(con, linhas, n_alvo)}
                       for sid, linhas in por_edicao(referencia).items()},
    }


def _somar(linha: dict, origem: dict) -> None:
    """Guarda a impressão. Os totais e o tile saem do `_fechar`, que é o mesmo
    para o conjunto inteiro e para a fatia de uma edição — uma conta só."""
    linha["_todas"].append(origem)


def _fechar(linha: dict, origens: list[dict]) -> None:
    """Os dois totais, o tile e a lista visível de um conjunto de impressões.

    O tile é a primeira impressão BASE do conjunto (no OGN a da sequência, no
    SFD a base do CardTrader); sem base nenhuma, a primeira que aparecer."""
    linha["total"] = sum(o["qty"] for o in origens)
    linha["sem_retiradas"] = sum(o["qty"] for o in origens if not o["retirada"])
    tile = next((o for o in origens if o["base"]), origens[0] if origens else None)
    linha.update({
        "code": tile["code"] if tile else None,
        "img": tile["img"] if tile else None,
        "cdn": tile["cdn"] if tile else None,
        "landscape": bool(tile and tile["landscape"]),
    })
    # Só as origens com cópias: é uma linha por baixo do tile, não uma lista
    # de tudo o que existe. A sequência primeiro, depois o que o site ainda
    # conta (a promo escondida), depois as retiradas e o CardTrader — pela
    # ordem em que o resto do site as lê.
    linha["origens"] = sorted(
        (o for o in origens if o["qty"] > 0),
        key=lambda o: (o["label"] != "sequência", o["retirada"],
                       o["fora_do_catalogo"], o["code"]))


def _rotulo(r, cfg: dict, retirada: bool) -> str:
    """A palavra para a origem, por baixo do tile: de onde vem cada cópia."""
    if retirada:
        return "alt art (retirada)"
    if metrics.escondida(r, cfg):
        return f"{r['variant_label'] or r['variant_kind']} (escondida)".lower()
    if metrics.e_master(r, cfg):
        return "sequência"
    return (r["variant_label"] or r["variant_kind"] or "").lower()

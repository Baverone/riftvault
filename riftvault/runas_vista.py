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

O CONTADOR É POR EDIÇÃO, E COMEÇOU A ZERO A 2026-10-03. André: *"Zera e
recontas por edicao"* — escolhido entre quatro hipóteses, depois de a 02/10 se
ter corrigido a referência «nesta edição» e de o contador ter ficado por
resolver. Até aí a chave era só o `card_key`: um número por runa, repetido nas
quatro páginas, porque as 14 que ele contou à mão não tinham edição gravada e
reparti-las era inventá-las. A chave é agora `(card_key, set_id)` e o número
de cada célula é o que ELE contar daquela edição.

ZERAR NÃO É APAGAR O RASTO. As seis linhas de antes estão na
`rune_counter_antes` (`arquivo`), com o `updated_at` de cada uma: o bloco
mostra-as em cima enquanto ele não dispensar o aviso (`dispensar`) e o
`riftvault runas` mostra-as sempre. Fora da base há a cópia de segurança em
`data/backups/rune_counter-antes-de-por-edicao-*.json` e o `.sql` ao lado.

NÃO HÁ SEMENTEIRA, e isso é o ponto desta mudança. Até 02/10 cada linha nascia
com o que ele fisicamente tinha dessa runa, para não ter de carregar 74 vezes;
agora isso era o contrário do que ele pediu — o número tem de ser o que ELE
conta, não o que a coleção calcula (no OGN a Calm Rune calculava 9 e ele tinha
contado 3). Uma linha só nasce de um `+`, uma runa sem linha lê-se 0, e por
isso **ler o bloco deixou de escrever na base**.

OS BOTÕES SÓ APARECEM NA PÁGINA DE UMA EDIÇÃO. Em «Todas» o crachá é a soma
das quatro e não há `+`/`−`: um clique ali não saberia a que edição somar, e
escolher uma por ele era inventar outra vez.

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

O ALVO É 12 POR RUNA E POR EDIÇÃO, e por isso o alvo de «Todas» são 288 (12 ×
6 runas × 4 edições). É a leitura literal de «12 de cada» agora que a célula é
por edição — uma edição fechada são 72, que é um Rune Pool que se pode montar
só com runas dela. O número de «Todas» é a soma das quatro e o cabeçalho
di-lo; se ele não quiser esse 288, é uma linha no `runas_vista.alvo` e é
decisão dele.

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
NOTA = ("o número é teu e é DESTA edição: os + e − mexem só nele e não contam "
        "para nada — nem coleção, nem decks, nem métricas. Ao lado, «nesta "
        "edição» é o que o site sabe que tens das impressões DESTA edição — a "
        "arte alternativa de cada edição é uma carta própria —, só para "
        "comparares. As runas base do OGN também estão na sequência do master "
        "set, em cima.")

#: O aviso que explica o zero, enquanto ele não o dispensar. Sem isto o bloco
#: a zero lia-se «não tens runas», que é o contrário do que se passa.
AVISO_ZERADO = (
    "O contador foi reposto a ZERO para passar a ser por edição — até aí era um "
    "número só, repetido nas quatro páginas. Reconta-as aqui, edição a edição; "
    "o que tinhas contado à mão fica ao lado para conferires.")

#: Em «Todas» não há onde somar um clique: o crachá é a soma das edições.
SOMA_SEM_BOTOES = ("este é a soma das edições — para contar, abre a edição")


class RunaDesconhecida(LookupError):
    """O `card_key` não é uma runa do catálogo — não há contador para ele."""


class EdicaoSemRuna(RunaDesconhecida):
    """A runa existe, mas não nessa edição — não há célula para contar.

    Subclasse da outra de propósito: quem apanha uma apanha as duas (é a mesma
    família, «não há contador para isso»), e a mensagem diz qual é o caso.
    """


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


def _contadores(con: sqlite3.Connection) -> dict[tuple[str, str], int]:
    """O contador dele, por `(card_key, set_id)`. Uma célula sem linha é 0 —
    não há sementeira desde 2026-10-03, e por isso ler não escreve."""
    return {(r["card_key"], r["set_id"]): r["qty"]
            for r in con.execute("SELECT card_key, set_id, qty FROM rune_counter")}


def arquivo(con: sqlite3.Connection) -> dict | None:
    """O rasto do contador de antes de 2026-10-03, ou `None` se não houver.

    São as linhas que a `rune_counter` tinha quando a chave era só o
    `card_key` — as 14 que ele contou à mão —, para ele conferir enquanto
    reconta. `dispensado_em` diz se o aviso já saiu do ecrã; o rasto fica na
    mesma, aqui e no `riftvault runas`.
    """
    try:
        linhas = [dict(r) for r in con.execute(
            "SELECT card_key, qty, seeded_from, updated_at, arquivado_em, "
            "dispensado_em FROM rune_counter_antes ORDER BY card_key")]
    except sqlite3.OperationalError:
        return None   # uma base anterior à migração (readonly, por exemplo)
    if not linhas:
        return None
    return {
        "linhas": linhas,
        "total": sum(r["qty"] for r in linhas),
        "cards": len(linhas),
        "arquivado_em": linhas[0]["arquivado_em"],
        # Uma só data: a migração arquivou-as todas de uma vez. Dispensar
        # dispensa o aviso inteiro, não uma linha.
        "dispensado_em": linhas[0]["dispensado_em"],
        "aviso": AVISO_ZERADO,
    }


def dispensar(con: sqlite3.Connection, voltar: bool = False) -> dict | None:
    """Tira (ou repõe) o aviso do zero no ecrã. **Não apaga o rasto**: marca a
    data, e as linhas ficam na tabela e no `riftvault runas`."""
    con.execute("UPDATE rune_counter_antes SET dispensado_em = ?",
                (None if voltar else _now(),))
    return arquivo(con)


def ajustar(con: sqlite3.Connection, card_key: str, set_id: str, delta: int,
            cfg: dict | None = None) -> dict:
    """O `+`/`−` de uma runa NUMA EDIÇÃO: `qty = qty + delta`, nunca abaixo de
    zero.

    Escreve SÓ na `rune_counter` — não no `copies`, não no `ops`, não no
    `pending`, não nos locais. Um `card_key` que não seja runa do catálogo
    rebenta (`RunaDesconhecida`); uma runa que exista mas não naquela edição
    rebenta também (`EdicaoSemRuna`) — não há célula para contar. A célula que
    ainda não tenha linha nasce AQUI, do primeiro `+`: não há sementeira, e um
    `−` numa célula a zero fica a zero.
    """
    cfg = cfg or config.load()
    card_key = (card_key or "").strip().casefold()
    set_id = (set_id or "").strip().upper()
    referencia = _na_colecao(con, cfg)
    if card_key not in referencia:
        raise RunaDesconhecida(f"{card_key!r} não é uma runa do catálogo")
    fatias = por_edicao(referencia)
    if set_id not in fatias:
        raise EdicaoSemRuna(
            f"{set_id!r} não tem runas — as que têm são "
            + ", ".join(sorted(fatias)))
    if card_key not in fatias[set_id]:
        raise EdicaoSemRuna(
            f"{referencia[card_key]['name']} não existe em {set_id}")
    delta = int(delta)
    con.execute("BEGIN IMMEDIATE")
    try:
        row = con.execute(
            "SELECT qty FROM rune_counter WHERE card_key = ? AND set_id = ?",
            (card_key, set_id)).fetchone()
        antes = row["qty"] if row else 0
        # O chão é zero: um `−` a 0 fica a 0, sem erro — é um contador dele,
        # não uma encomenda por anular.
        depois = max(0, antes + delta)
        con.execute(
            "INSERT INTO rune_counter (card_key, set_id, qty, updated_at) "
            "VALUES (?,?,?,?) ON CONFLICT(card_key, set_id) DO UPDATE SET "
            "qty = excluded.qty, updated_at = excluded.updated_at",
            (card_key, set_id, depois, _now()))
        con.execute("COMMIT")
    except BaseException:
        con.execute("ROLLBACK")
        raise
    n_alvo = alvo(cfg)
    return {"card_key": card_key, "set_id": set_id, "qty": depois,
            "delta": depois - antes,
            "name": referencia[card_key]["name"],
            "na_colecao": fatias[set_id][card_key]["total"],
            # Os totais das duas vistas vêm do servidor, para não haver uma
            # segunda aritmética no cliente: a soma e cada edição.
            "totals": _totals(con, referencia, n_alvo, None),
            "totals_por_edicao": {sid: _totals(con, linhas, n_alvo, sid)
                                  for sid, linhas in fatias.items()}}


def _celulas(referencia: dict) -> int:
    """Quantos pares (runa, edição) há nesta vista: 6 numa edição, 24 em
    «Todas». É o que o alvo multiplica — ver o `_totals`."""
    pares = {(ck, o["set_id"]) for ck, linha in referencia.items()
             for o in linha.get("_todas") or []}
    return len(pares) or len(referencia)


def _totals(con: sqlite3.Connection, referencia: dict, n_alvo: int,
            set_id: str | None) -> dict:
    """Os números de uma vista. `set_id=None` é a soma de todas as edições.

    O ALVO CONTA CÉLULAS, não runas: 12 por runa e por edição. Numa edição são
    6 × 12 = 72; em «Todas» são 24 × 12 = 288, que é a soma das quatro — se
    fosse 72 ali, a fracção lia-se ao contrário do número de cima.
    """
    cont = _contadores(con)
    if set_id is None:
        contador = sum(q for (ck, _), q in cont.items() if ck in referencia)
    else:
        contador = sum(cont.get((ck, set_id), 0) for ck in referencia)
    return {
        "cards": len(referencia),
        "celulas": _celulas(referencia),
        "contador": contador,
        "total": sum(x["total"] for x in referencia.values()),
        "sem_retiradas": sum(x["sem_retiradas"] for x in referencia.values()),
        "alvo": n_alvo * _celulas(referencia),
    }


def payload(con: sqlite3.Connection, cfg: dict | None = None,
            image_mode: str = "local", editable: bool = False) -> dict:
    cfg = cfg or config.load()
    n_alvo = alvo(cfg)
    referencia = _na_colecao(con, cfg)
    # LER NÃO ESCREVE, desde 2026-10-03: a sementeira foi-se com o contador
    # por edição (ver o topo do módulo). Uma célula sem linha lê-se 0.
    cont = _contadores(con)
    fatias = por_edicao(referencia)

    def _itens(linhas: dict[str, dict], sid: str | None) -> list[dict]:
        out = []
        for linha in sorted(linhas.values(), key=lambda x: x["name"]):
            ck = linha["card_key"]
            linha = {k: v for k, v in linha.items() if k != "_todas"}
            # O contador é o DELE e é DAQUELA EDIÇÃO. Em «Todas» (`sid` a
            # None) é a soma das quatro, e aí não há botões: um clique não
            # saberia a que edição somar.
            linha["contador"] = (
                cont.get((ck, sid), 0) if sid
                else sum(q for (k, _), q in cont.items() if k == ck))
            linha["target"] = n_alvo
            out.append(linha)
        return out

    return {
        "generated_at": _now(),
        "image_mode": image_mode,
        # Os `+`/`−` só no modo edição, como em toda a parte — e só na página
        # de UMA edição (o cliente vê o `set_id` da vista).
        "editable": editable,
        # A marca de que isto não conta para nada: o cliente e os testes lêem-na.
        "so_para_ver": True,
        "alvo": n_alvo,
        "nota": NOTA,
        "soma_sem_botoes": SOMA_SEM_BOTOES,
        # A soma das edições — é o que o separador «Todas» mostra.
        "runas": _itens(referencia, None),
        "totals": _totals(con, referencia, n_alvo, None),
        # O rasto do contador de antes de 03/10, para ele conferir enquanto
        # reconta. `None` só quando não há rasto nenhum (uma base criada depois
        # da migração nunca teve contador por runa); dispensar o aviso marca a
        # data e o rasto vem na mesma — é o cliente que decide se o mostra.
        "antes": arquivo(con),
        # Uma entrada por edição COM runas (2026-10-01): as runas dela, as
        # origens dela, o total dela e o CONTADOR dela. O OGS não tem runas.
        "por_edicao": {sid: {"set_id": sid, "runas": _itens(linhas, sid),
                             "totals": _totals(con, linhas, n_alvo, sid)}
                       for sid, linhas in fatias.items()},
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

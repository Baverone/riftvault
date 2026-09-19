"""O separador «A mais»: o que ele tem acima do alvo, e o que os decks libertaram.

André, 2026-09-17: *"agora cria um botao que e o 'a mais' onde vai todas as
cartas que estao listadas a mais ou que estavam num deck e deixaram de estar"*.

Duas famílias, no mesmo separador, em blocos separados e por edição:

  EXCEDENTE           — impressões de que ele tem MAIS cópias do que o alvo.
                        O alvo é o que o riftvault já usa, carta a carta
                        (`metrics.alvo`): o playset do tipo na sequência, 1
                        nas artes alternativas e sobrenumeradas (ou o que os
                        decks jogam, nas alt arts), 0 no que está escondido.
                        «tens 5, queres 3 -> 2 a mais».
  LIBERTADAS DOS DECKS — cartas que uma lista de deck pedia e deixou de pedir
                        (`uso_decks.libertadas`). O registo NASCEU nesta ordem
                        e começa vazio — ver o topo do `uso_decks.py`.

SÓ MOSTRA. Não mexe em alvo nenhum, em conta nenhuma, e não escreve. Não é a
Venda de 2026-09-08 (apagada a 2026-09-15 a pedido dele): não há preço de
venda, lista para vender nem texto do Cardmarket. O que se reaproveitou da
Venda foi a CONTA do excedente — a mesma frase, `cópias − max(usadas nos decks,
alvo)`, com as duas origens (binder Decks/Venda e Coleção) e o que está
sleevado num deck nunca a aparecer. O que ficou de fora: o «vender», os
totais em euros como argumento, as comuns e incomuns, o Cardmarket.

A CONTA DO EXCEDENTE, por impressão
    usadas         = o que os grupos de decks levam desta impressão, dos três
                     montes (`decks.allocate`, `grupo.impressoes`, lido no
                     líder — dois decks com a mesma Legend contam uma vez)
    do binder      = no binder Decks/Venda − o que os decks levam de lá
                     (nenhum deck a pede: é ele que a tirou da Coleção)
    da Coleção     = na Coleção − max(usadas da Coleção, alvo)
    a mais         = do binder + da Coleção

    A sequência do master set ENTRA (a quarta cópia de uma Unit é «a mais»);
    a Venda tirava-a por omissão porque a pergunta lá era outra. Uma versão
    especial que a Legend/Champion de um deck jogue conta nas «usadas»
    (2026-09-17) e por isso nunca sobra; o alvo dela é 1 e não sobe com os
    decks. O que está escondido (tokens,
    signatures, runas sem numeração) tem alvo 0 e sobra inteiro, marcado. O
    que está RETIRADO (as runas em alt art, 2026-09-17) nem aparece.

AS RUNAS NUNCA APARECEM (2026-09-17, à noite)
    André: *"no a mais nunca aparece Runas"*. Com `a_mais.sem_runas: true`
    (o default) uma runa (`runas_especiais.tipos`) não entra em NENHUM dos
    dois blocos — nem no excedente, esteja na sequência ou escondida, nem nas
    libertadas dos decks. É a mesma noite em que as runas saíram da contagem
    dos decks (`decks.contar_runas`): ele trata delas à mão e não as quer a
    fazer barulho aqui. `scope.runas` diz quantas linhas e cópias ficaram de
    fora por isso — a página e o CLI dizem-no em vez de esconder em silêncio.

Cartas só em inglês, como o resto: o catálogo da RiftScribe não tem outra
língua, e os preços (`precos.linguas`) já são só de ofertas em inglês. Os
preços aparecem só como informação da carta, não como total a vender.

Configura-se no `riftvault_config.json`, bloco "a_mais".
"""

from __future__ import annotations

import sqlite3

from . import config, decks, locais, metrics, uso_decks

DEFAULTS: dict = {
    # As edições SEM botão, como na tabela de preços que se apagou a
    # 2026-09-19 (o pedido é de 2026-09-15: "menos proving grounds"). Aqui a
    # edição sem botão continua a aparecer em «Todas» — um excedente que não
    # se vê é o contrário do que o separador é.
    "sem_edicoes": ["OGS"],
    # As runas ficam fora dos dois blocos (2026-09-17, à noite).
    "sem_runas": True,
}


def sem_runas(cfg: dict | None = None) -> bool:
    return bool(opcoes(cfg)["sem_runas"])


def _e_runa(r, cfg: dict) -> bool:
    """Esta linha (impressão ou carta, com `type`) é uma runa que fica de fora?"""
    return sem_runas(cfg) and metrics.e_runa(r, cfg)


def opcoes(cfg: dict | None = None) -> dict:
    cfg = cfg or config.load()
    bruto = cfg.get("a_mais") or {}
    return {**DEFAULTS, **{k: v for k, v in bruto.items() if not k.startswith("_")}}


def edicoes(con: sqlite3.Connection, cfg: dict | None = None) -> dict:
    """Todas as edições do catálogo pela ordem dos separadores, e quais têm botão."""
    sem = {str(s).upper() for s in opcoes(cfg)["sem_edicoes"]}
    todas = [r[0] for r in con.execute("SELECT DISTINCT set_id FROM catalog.printings")]
    todas.sort(key=lambda s: (config.set_order(s), s))
    return {"sets": todas, "sem_edicoes": [s for s in todas if s in sem]}


def _usadas(con: sqlite3.Connection) -> dict[str, dict]:
    """printing_id -> {no_deck, no_binder, na_colecao, decks}: o que os decks
    levam desta impressão, monte a monte, e quem a leva.

    Lê-se do `decks.allocate` uma vez só (a Venda chamava as três funções
    `*_allocation`, que são três alocações iguais). Pelo líder de cada grupo:
    os membros do mesmo grupo levam as mesmas cópias.
    """
    try:
        alloc = decks.allocate(con)
    except sqlite3.OperationalError:
        return {}
    out: dict[str, dict] = {}
    for a in alloc.values():
        g = a["grupo"]
        if not g["lider"]:
            continue
        for monte, mapa in g["impressoes"].items():
            for pid, n in mapa.items():
                u = out.setdefault(pid, {"no_deck": 0, "no_binder": 0, "na_colecao": 0,
                                         "decks": []})
                u[monte] += n
                u["decks"].append({"deck": g["rotulo"], "qty": n, "monte": monte})
    return out


def excedente(con: sqlite3.Connection, cfg: dict | None = None,
              todas: bool = False) -> list[dict]:
    """As impressões com cópias a mais, e quantas — a conta da Venda, sem a Venda.

    Sem as runas, com `sem_runas` (2026-09-17, à noite). `todas=True` devolve
    também as runas, marcadas `runa`, para quem quer contar o que ficou de
    fora (`payload`, `scope.runas`).
    """
    cfg = cfg or config.load()
    usadas = _usadas(con)
    no_binder = locais.em(con, locais.BINDER)
    na_colecao = locais.na_colecao(con)
    precos = metrics.prices_map(con)

    itens: list[dict] = []
    for r in con.execute(
        "SELECT p.*, c.qty FROM copies c "
        "JOIN catalog.printings p ON p.printing_id = c.printing_id "
        "WHERE c.qty > 0 ORDER BY p.set_id, p.api_sort"
    ):
        # Uma RETIRADA (a runa em alt art, 2026-09-17: *"nao incluas em
        # nada"*) não é excedente nem escondida: não existe. As 6 `OGN-042a`
        # dele ficam no `copies` e não aparecem aqui.
        if metrics.retirada(r, cfg):
            continue
        # Uma runa nunca aparece (*"no a mais nunca aparece Runas"*), esteja
        # na sequência ou escondida — fica só se quem chama pedir `todas`.
        runa = _e_runa(r, cfg)
        if runa and not todas:
            continue
        pid = r["printing_id"]
        u = usadas.get(pid) or {"no_deck": 0, "no_binder": 0, "na_colecao": 0, "decks": []}
        escondida = not metrics.e_colecao(r, cfg)
        # O alvo da página inteira — master set e coleção extra —; 0 no que
        # está escondido, que a Coleção não pede.
        alvo = 0 if escondida else metrics.alvo(r, cfg)
        do_binder = max(0, no_binder.get(pid, 0) - u["no_binder"])
        da_colecao = max(0, na_colecao.get(pid, 0) - max(u["na_colecao"], alvo))
        sobra = do_binder + da_colecao
        if sobra <= 0:
            continue
        bloco = metrics.bloco(r, cfg)
        preco = precos.get(pid)
        itens.append({
            "printing_id": pid,
            "name": r["name"], "code": r["public_code"],
            "set": r["set_id"], "cn": r["collector_number"],
            "kind": r["variant_kind"], "label": r["variant_label"],
            "rarity": r["base_rarity"] or "?",
            "landscape": (r["orientation"] or "").lower() == "landscape",
            "img": f"img/{pid}.webp",
            "cdn": r["image_medium"] or r["image_large"] or r["image_url"],
            "block": bloco,
            "block_label": metrics.BLOCO_CURTO.get(bloco, bloco),
            "hidden": escondida,
            "have": r["qty"], "target": alvo,
            "in_colecao": na_colecao.get(pid, 0),
            "in_binder": no_binder.get(pid, 0),
            "used": u["no_deck"] + u["no_binder"] + u["na_colecao"],
            "in_decks": u["decks"],
            "from_binder": do_binder, "from_colecao": da_colecao,
            # `extra` é o número do crachá: quantas estão a mais.
            "extra": sobra,
            "price": preco,
            "runa": runa,
        })
    return itens


def _impressao_da_carta(con: sqlite3.Connection, card_key: str) -> sqlite3.Row | None:
    """A impressão que representa uma carta lógica no ecrã: a que ele tem mais
    cópias, senão a base da edição mais antiga."""
    tidas = con.execute(
        "SELECT p.* FROM copies c JOIN catalog.printings p ON p.printing_id = c.printing_id "
        "WHERE p.card_key = ? AND c.qty > 0 ORDER BY c.qty DESC, p.api_sort", (card_key,)
    ).fetchall()
    if tidas:
        return tidas[0]
    todas = con.execute(
        "SELECT * FROM catalog.printings WHERE card_key = ?", (card_key,)).fetchall()
    if not todas:
        return None
    return sorted(todas, key=lambda r: (r["variant_kind"] != "base",
                                        config.set_order(r["set_id"]), r["api_sort"]))[0]


def libertadas(con: sqlite3.Connection, cfg: dict | None = None,
               todas: bool = False) -> list[dict]:
    """As cartas que uma lista pedia e deixou de pedir, com a carta no ecrã e o
    contexto de hoje: quantas ele tem e o que os outros decks ainda pedem.

    Sem as runas, com `sem_runas`: o registo (`deck_need_log`) continua a
    guardá-las — é o rasto do que as listas pedem —, só não se mostram.
    `todas=True` devolve-as, marcadas `runa`.
    """
    cfg = cfg or config.load()
    tenho = metrics.owned_by_card(con)
    pedido = uso_decks.pedido_atual(con)
    ainda: dict[str, list[dict]] = {}
    for (slug, ck), info in pedido.items():
        ainda.setdefault(ck, []).append({"slug": slug, "deck": info["deck"], "qty": info["qty"]})
    precos = metrics.prices_map(con)
    tipos = {r["card_key"]: r["type"] for r in con.execute(
        "SELECT card_key, type FROM catalog.cards")}
    out = []
    for x in uso_decks.libertadas(con):
        runa = _e_runa({"type": tipos.get(x["card_key"])}, cfg)
        if runa and not todas:
            continue
        r = _impressao_da_carta(con, x["card_key"])
        if r is None:
            continue
        pid = r["printing_id"]
        out.append({
            **x,
            "runa": runa,
            "printing_id": pid,
            "name": r["name"], "code": r["public_code"],
            "set": r["set_id"], "cn": r["collector_number"],
            "kind": r["variant_kind"], "label": r["variant_label"],
            "rarity": r["base_rarity"] or "?",
            "landscape": (r["orientation"] or "").lower() == "landscape",
            "img": f"img/{pid}.webp",
            "cdn": r["image_medium"] or r["image_large"] or r["image_url"],
            "have": tenho.get(x["card_key"], 0),
            # Os decks que HOJE ainda pedem a carta (o próprio incluído, se
            # ainda pedir algumas): libertada de um deck não é livre se outro
            # a joga.
            "still_wanted": sorted(ainda.get(x["card_key"], []),
                                   key=lambda d: (d["slug"] != x["slug"], d["slug"])),
            "price": precos.get(pid),
        })
    return out


def _soma(itens: list[dict], campo: str) -> dict:
    return {"cards": len(itens), "copies": sum(x[campo] for x in itens)}


def payload(con: sqlite3.Connection, cfg: dict | None = None) -> dict:
    """O separador inteiro: por edição, os dois blocos."""
    cfg = cfg or config.load()
    ed = edicoes(con, cfg)
    # Lê-se tudo uma vez e separa-se: o que se mostra, e as runas que ficaram
    # de fora — para o cabeçalho dizer quantas em vez de as apagar em silêncio.
    exc_todas = excedente(con, cfg, todas=True)
    lib_todas = libertadas(con, cfg, todas=True)
    exc = [x for x in exc_todas if not x["runa"]]
    lib = [x for x in lib_todas if not x["runa"]]
    runas_exc = [x for x in exc_todas if x["runa"]]
    runas_lib = [x for x in lib_todas if x["runa"]]

    sets = []
    for s in ed["sets"]:
        e = [x for x in exc if x["set"] == s]
        l_ = [x for x in lib if x["set"] == s]
        sets.append({
            "set": s, "name": config.set_name(s),
            "button": s not in ed["sem_edicoes"],
            "excedente": {**_soma(e, "extra"), "items": e},
            "libertadas": {**_soma(l_, "qty"), "items": l_},
        })
    return {
        "sets": sets,
        "sem_edicoes": ed["sem_edicoes"],
        "totals": {"excedente": _soma(exc, "extra"), "libertadas": _soma(lib, "qty")},
        # Desde quando há registo dos decks — é o que explica um bloco vazio.
        "history": uso_decks.resumo(con),
        "scope": {
            "hidden_cards": sum(1 for x in exc if x["hidden"]),
            "hidden_copies": sum(x["extra"] for x in exc if x["hidden"]),
            # As runas que ficaram de fora dos dois blocos (`sem_runas`).
            "sem_runas": sem_runas(cfg),
            "runas": {"excedente": _soma(runas_exc, "extra"),
                      "libertadas": _soma(runas_lib, "qty")},
        },
    }

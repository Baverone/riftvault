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
    a Venda tirava-a por omissão porque a pergunta lá era outra. O alvo de
    uma arte alternativa já leva o que os decks jogam (`procura`), por isso
    uma alt art que um deck use nunca sobra. O que está escondido (tokens,
    signatures, runas sem numeração) tem alvo 0 e sobra inteiro, marcado. O
    que está RETIRADO (as runas em alt art, 2026-09-17) nem aparece.

Cartas só em inglês, como o resto: o catálogo da RiftScribe não tem outra
língua, e os preços (`precos.linguas`) já são só de ofertas em inglês. Os
preços aparecem só como informação da carta, não como total a vender.

Configura-se no `riftvault_config.json`, bloco "a_mais".
"""

from __future__ import annotations

import sqlite3

from . import config, decks, locais, metrics, uso_decks

DEFAULTS: dict = {
    # As edições SEM botão, como no «Quanto custa» (2026-09-15: "menos proving
    # grounds"). Aqui a edição sem botão continua a aparecer em «Todas» — um
    # excedente que não se vê é o contrário do que o separador é.
    "sem_edicoes": ["OGS"],
}


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


def excedente(con: sqlite3.Connection, cfg: dict | None = None) -> list[dict]:
    """As impressões com cópias a mais, e quantas — a conta da Venda, sem a Venda."""
    cfg = cfg or config.load()
    usadas = _usadas(con)
    no_binder = locais.em(con, locais.BINDER)
    na_colecao = locais.na_colecao(con)
    procura = metrics.procura_dos_decks(con, cfg)
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
        pid = r["printing_id"]
        u = usadas.get(pid) or {"no_deck": 0, "no_binder": 0, "na_colecao": 0, "decks": []}
        escondida = not metrics.e_colecao(r, cfg)
        # O alvo da página inteira — master set e coleção extra —; 0 no que
        # está escondido, que a Coleção não pede.
        alvo = 0 if escondida else metrics.alvo(r, cfg, procura)
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


def libertadas(con: sqlite3.Connection, cfg: dict | None = None) -> list[dict]:
    """As cartas que uma lista pedia e deixou de pedir, com a carta no ecrã e o
    contexto de hoje: quantas ele tem e o que os outros decks ainda pedem."""
    cfg = cfg or config.load()
    tenho = metrics.owned_by_card(con)
    pedido = uso_decks.pedido_atual(con)
    ainda: dict[str, list[dict]] = {}
    for (slug, ck), info in pedido.items():
        ainda.setdefault(ck, []).append({"slug": slug, "deck": info["deck"], "qty": info["qty"]})
    precos = metrics.prices_map(con)
    out = []
    for x in uso_decks.libertadas(con):
        r = _impressao_da_carta(con, x["card_key"])
        if r is None:
            continue
        pid = r["printing_id"]
        out.append({
            **x,
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
    exc = excedente(con, cfg)
    lib = libertadas(con, cfg)

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
        },
    }

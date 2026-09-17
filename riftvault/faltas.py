"""As listas de compra dos DECKS: o que comprar, e por que ordem.

Três vistas da mesma pergunta, nas abas do separador Decks (desde 2026-09-15
à tarde; até lá viviam no separador «Faltas», que passou a ser a tabela de
preços «Quanto custa» — ver `quanto_custa.py`):

  STAPLES    — cartas que faltam e que MAIS DO QUE UM deck pede. São as que
               rendem mais por euro: uma compra serve vários decks.
  POR DECK   — o que falta a cada deck, por edição.
  PIMP DECKS — as versões alteradas das cartas dos decks, também como lista de
               compras (ver `pimp`).

As faltas do MASTER SET (a wantlist do fim de cada edição da Coleção) não
vivem aqui: são o `a_subir.master_faltas`/`wantlist`. O que vem a caminho é o
`pending` (a lista «Encomendas» do separador Decks).

A carência é GLOBAL, não por deck: soma-se o que todos os decks pedem de uma
carta e desconta-se o que ele tem. A alocação por prioridade diz quem fica com
o quê — aqui a pergunta é quanto falta comprar ao todo, e desde 2026-09-11 as
duas dão a mesma soma: *"os decks que precisem de cartas iguais, caso não haja
suficientes na coleção, ficam em falta e é necessário comprar"* (André). O
TETO POR CARTA de 2026-09-01 («cinco decks a pedir 3 Defy são 3, e trocam-se
entre decks») ficou revogado por essa frase — ver `shortfall`.
"""

from __future__ import annotations

import sqlite3

from . import cardmarket, config, decks, metrics, pending


def _wanted(con: sqlite3.Connection) -> dict[str, dict]:
    """card_key -> {qty pedida ao todo, decks que a pedem}.

    `decks` é {slug: {"deck": rótulo, "qty": n}}. A chave é o SLUG: pelo
    rótulo, dois decks com a mesma Legend e o mesmo Champion contavam como um
    só e a carta deixava de ser staple (2026-09-11).

    A `qty` soma por GRUPO de Legend, com o MÁXIMO dentro de cada grupo
    (2026-09-11, noite): os dois LeBlanc são duas listas do mesmo deck e
    pedem as mesmas cópias — *"o que encomendar para 1 deck, estou a encomendar
    para o outro também"*. `n_grupos` é quantos grupos a pedem, e é isso que
    faz uma staple: uma compra que serve DECKS DIFERENTES, não duas listas do
    mesmo.
    """
    grupo_de = {}
    for g in decks.grupos(con):
        for slug in g["slugs"]:
            grupo_de[slug] = g["legend"]
    # As runas não se contam nos decks (2026-09-17, à noite) — nem aqui, nem
    # no Pimp. O `faltas_ignorar_tipos` de 2026-09-01 já as tirava das abas;
    # agora nem chegam a ser pedidas.
    fora = decks.cartas_nao_contadas(con)
    out: dict[str, dict] = {}
    for r in con.execute(
        "SELECT dc.card_key, dc.qty, d.deck_id, d.display_name, d.name, d.priority "
        "FROM deck_cards dc JOIN decks d ON d.deck_id = dc.deck_id"
    ):
        if r["card_key"] in fora:
            continue
        e = out.setdefault(r["card_key"], {"qty": 0, "decks": {}, "grupos": {}})
        slot = e["decks"].setdefault(
            r["name"], {"deck": r["display_name"] or r["name"], "qty": 0})
        slot["qty"] += r["qty"]
        g = grupo_de.get(r["name"], r["name"])
        e["grupos"][g] = max(e["grupos"].get(g, 0), slot["qty"])
    for e in out.values():
        e["qty"] = sum(e["grupos"].values())
        e["n_grupos"] = len(e["grupos"])
    return out



def _cheapest(con: sqlite3.Connection, keys: list[str],
              especial: bool = False) -> dict[str, dict]:
    """card_key -> impressão mais barata em que se compra: a normal (a base,
    sem sobrenumeração) ou, com `especial`, a versão especial da
    Legend/Champion (`decks.Versoes.compra`, 2026-09-17)."""
    if not keys:
        return {}
    versoes = decks.versoes_dos_decks(con)
    escolha = {ck: versoes.compra(ck, especial) for ck in keys}
    pids = [pid for pid in escolha.values() if pid]
    if not pids:
        return {}
    ph = ",".join("?" * len(pids))
    linhas = {r["printing_id"]: r for r in con.execute(
        f"SELECT p.card_key, p.set_id, p.printing_id, p.public_code, p.orientation, "
        f"       p.variant_kind, p.image_medium, p.image_large, p.image_url, "
        f"       pl.price_cents, m.market_name, m.market_set, m.cardmarket_id "
        f"FROM catalog.printings p "
        f"LEFT JOIN catalog.price_latest pl ON pl.printing_id = p.printing_id "
        f"LEFT JOIN catalog.cardtrader_map m ON m.printing_id = p.printing_id "
        f"WHERE p.printing_id IN ({ph})", pids)}
    best: dict[str, dict] = {}
    for ck, pid in escolha.items():
        r = linhas.get(pid)
        if r is None:
            continue
        best[ck] = {
            "set": r["set_id"], "id": r["printing_id"], "code": r["public_code"],
            "price": r["price_cents"], "especial": especial,
            "alternativas": [x for x in versoes.alternativas(ck) if x["id"] != pid]
            if especial else [],
            "landscape": (r["orientation"] or "").lower() == "landscape",
            "img": f"img/{r['printing_id']}.webp",
            "cdn": r["image_medium"] or r["image_large"] or r["image_url"],
            # Como o mercado escreve: "Darius - Trifarian", não
            # "Darius, Trifarian". É por aqui que a wantlist tem de sair.
            "market_name": r["market_name"],
            "market_set": r["market_set"],
            "cardmarket_id": r["cardmarket_id"],
        }
    return best


def _falta_global(con: sqlite3.Connection) -> tuple[dict[str, int], dict[str, int]]:
    """O que falta comprar AO TODO, por carta: (total, do qual na versão especial).

    É a soma do `missing` dos grupos de Legend (lido no líder — os dois
    LeBlanc contam uma vez), que já desconta o que ele tem E o que vem a
    caminho, lugar a lugar. Desde 2026-09-17 a carência já não se conta por
    carta às cegas (pedido − cópias): uma Legend com 3 cópias base e nenhuma
    especial ainda compra a especial, e só a alocação sabe isso.
    """
    falta: dict[str, int] = {}
    falta_esp: dict[str, int] = {}
    for a in decks.allocate(con).values():
        g = a["grupo"]
        if not g["lider"]:
            continue
        for ck, n in g["missing"].items():
            falta[ck] = falta.get(ck, 0) + n
        for ck, n in g["missing_especial"].items():
            falta_esp[ck] = falta_esp.get(ck, 0) + n
    return falta, falta_esp


def shortfall(con: sqlite3.Connection) -> list[dict]:
    """O que falta comprar ao todo, com quantos decks pede cada carta.

    Uma entrada por carta, com o `missing` total; quando parte disso é a
    versão especial da Legend/Champion, `especial` diz quantas, em que
    impressão, a quanto e que alternativas havia (2026-09-17), e o `total`
    soma os dois preços.
    """
    pedido = _wanted(con)
    if not pedido:
        return []
    nomes = {r["card_key"]: r["name"] for r in con.execute(
        "SELECT card_key, name FROM catalog.cards")}

    # SEM TETO POR CARTA desde 2026-09-11. Havia um (decisão de 2026-09-01):
    # não se comprava mais do que um playset da mesma carta, porque «cinco
    # decks a pedir 3 Defy não são 15 Defy para comprar — são 3, e trocam-se
    # entre decks». A frase dele de hoje diz o contrário — *"os decks que
    # precisem de cartas iguais, caso não haja suficientes na coleção, ficam em
    # falta e é necessário comprar"* — e é ela que manda: a carência é a soma
    # do que os decks pedem menos o que ele tem. O `cap` continua no payload,
    # só como informação de quanto é o playset.
    tipos = {r["card_key"]: (r["type"], bool(r["is_token"])) for r in con.execute(
        "SELECT card_key, type, is_token FROM catalog.cards")}
    cfg = config.load()

    def playset(k: str) -> int:
        t, tok = tipos.get(k, (None, False))
        return metrics.playset_target(t, tok, cfg)

    # Tipos que esta secção não conta. As runas são baratas e compram-se a
    # granel; a 12 por deck enchiam os staples e escondiam o que interessa.
    # Continuam a contar na secção Decks e na Coleção.
    ignorar = set(cfg.get("faltas_ignorar_tipos", []))

    falta_total, falta_esp = _falta_global(con)
    em_falta = {k: v for k, v in pedido.items()
                if falta_total.get(k, 0) > 0
                and tipos.get(k, (None, False))[0] not in ignorar}
    onde = _cheapest(con, list(em_falta))
    onde_esp = _cheapest(con, [k for k in em_falta if falta_esp.get(k)], especial=True)

    out = []
    for k, v in em_falta.items():
        falta = falta_total[k]
        n_esp = min(falta, falta_esp.get(k, 0))
        c = onde.get(k) or {}
        e = onde_esp.get(k) or {}
        total = (c.get("price") or 0) * (falta - n_esp) + (e.get("price") or 0) * n_esp
        out.append({
            "card_key": k, "name": nomes.get(k, k),
            # `wanted` é o que os decks pedem ao todo, e é o alvo.
            "wanted": v["qty"], "target": v["qty"], "cap": playset(k),
            # O que já cobre o pedido: cópias que servem e o que vem a caminho.
            "have": max(0, v["qty"] - falta), "missing": falta,
            # Decks DIFERENTES (grupos de Legend), não listas: os dois LeBlanc
            # contam como um. A lista `decks` continua a mostrar as duas.
            "n_decks": v["n_grupos"],
            "decks": [{"deck": x["deck"], "slug": slug, "qty": x["qty"]}
                      for slug, x in sorted(v["decks"].items(),
                                            key=lambda kv: -kv[1]["qty"])],
            "price": c.get("price"),
            "total": total,
            "set": c.get("set"), "code": c.get("code"),
            "img": c.get("img"), "cdn": c.get("cdn"),
            "landscape": c.get("landscape", False),
            # A versão especial da Legend/Champion que falta (2026-09-17).
            "especial": ({"qty": n_esp, "code": e.get("code"), "set": e.get("set"),
                          "price": e.get("price"), "total": (e.get("price") or 0) * n_esp,
                          "alternativas": e.get("alternativas", [])}
                         if n_esp else None),
        })
    return out


def staples(con: sqlite3.Connection) -> list[dict]:
    """As que mais do que um deck pede. Comprar estas primeiro."""
    out = [x for x in shortfall(con) if x["n_decks"] >= 2]
    out.sort(key=lambda x: (-x["n_decks"], -x["missing"], -x["total"]))
    return out


def _tipos(con: sqlite3.Connection) -> dict[str, tuple]:
    return {r["card_key"]: (r["type"], bool(r["is_token"])) for r in con.execute(
        "SELECT card_key, type, is_token FROM catalog.cards")}


def _agrupar(con: sqlite3.Connection, falta: dict[str, int],
             falta_esp: dict[str, int] | None = None) -> list[dict]:
    """{card_key: quantas comprar} -> lista por edição, com as cartas dentro.

    A edição escolhida é aquela onde a carta sai mais barata: é onde se compra.
    `falta_esp` é a parte de `falta` que é a versão especial da
    Legend/Champion (2026-09-17): sai numa LINHA PRÓPRIA, marcada `especial`,
    na versão especial mais barata — para a wantlist do Cardmarket pedir
    «2× base + 1× alt art» e não «3× base».
    """
    if not falta:
        return []
    falta_esp = falta_esp or {}
    nomes = {r["card_key"]: r["name"] for r in con.execute(
        "SELECT card_key, name FROM catalog.cards")}
    onde = _cheapest(con, list(falta))
    onde_esp = _cheapest(con, [k for k in falta if falta_esp.get(k)], especial=True)

    # Em que outras edições existe a carta — dá-lhe alternativa se não
    # encontrar a versão mais barata.
    vs = decks.versoes_dos_decks(con)
    edicoes = {k: {vs.info(p)["set"] for p in vs.normais_de(k)} for k in falta}
    edicoes_esp = {k: {vs.info(p)["set"] for p in vs.especiais_de(k)} for k in falta}
    ordens = {s: config.set_order(s) for s in
              (r["set_id"] for r in con.execute("SELECT DISTINCT set_id FROM catalog.printings"))}

    versoes = cardmarket.versoes(con)
    # Todas as impressões de cada carta, para poder oferecer as alternativas.
    ph2 = ",".join("?" * len(falta))
    irmas: dict[str, list] = {}
    for r in con.execute(
        f"SELECT p.card_key, p.printing_id, p.set_id, m.market_name, m.market_set "
        f"FROM catalog.printings p "
        f"JOIN catalog.cardtrader_map m ON m.printing_id = p.printing_id "
        f"WHERE p.card_key IN ({ph2})", list(falta)
    ):
        irmas.setdefault(r["card_key"], []).append(r)

    por_set: dict[str, dict] = {}

    def linha(k: str, n: int, c: dict, especial: bool) -> None:
        # As versões da MESMA edição onde se vai comprar: base, arte
        # alternativa, showcase, signature. É o que ele quer ver lado a lado.
        alt = []
        for r in irmas.get(k, []):
            if r["set_id"] != c["set"] or r["printing_id"] == c["id"]:
                continue
            v = versoes.get(r["printing_id"])
            if not v:
                continue
            alt.append({"name": v.get("name") or r["market_name"],
                        "set": r["market_set"],
                        "v": v["v"], "n": v["n"], "label": v["label"],
                        "code": v["code"], "foil_only": v["foil_only"]})
        alt.sort(key=lambda x: x["v"])
        d = por_set.setdefault(c["set"], {"set": c["set"], "name": config.set_name(c["set"]),
                                          "cards": 0, "copies": 0, "cents": 0, "items": []})
        d["cards"] += 1
        d["copies"] += n
        d["cents"] += (c["price"] or 0) * n
        d["items"].append({
            "card_key": k, "name": nomes.get(k, k), "qty": n,
            "code": c["code"], "price": c["price"], "total": (c["price"] or 0) * n,
            "img": c["img"], "cdn": c["cdn"], "landscape": c["landscape"],
            "especial": especial,
            "alternativas": c.get("alternativas", []),
            "also": sorted((edicoes_esp if especial else edicoes).get(k, set()) - {c["set"]}),
            "market_name": c.get("market_name"), "market_set": c.get("market_set"),
            "cardmarket_id": c.get("cardmarket_id"),
            "v": (versoes.get(c["id"]) or {}).get("v"),
            "n_versions": (versoes.get(c["id"]) or {}).get("n", 1),
            "foil_only": (versoes.get(c["id"]) or {}).get("foil_only", False),
            "outras_versoes": alt,
        })

    for k, n in falta.items():
        n_esp = min(n, falta_esp.get(k, 0))
        if n_esp and onde_esp.get(k):
            linha(k, n_esp, onde_esp[k], True)
        if n - n_esp and onde.get(k):
            linha(k, n - n_esp, onde[k], False)
    out = list(por_set.values())
    for d in out:
        d["items"].sort(key=lambda x: (-x["total"], x["name"]))
    out.sort(key=lambda d: (ordens.get(d["set"], 999), d["set"]))
    return out


def por_deck(con: sqlite3.Connection) -> list[dict]:
    """O que falta comprar a CADA deck: o `missing` da alocação por prioridade.

    É a mesma resposta da secção Decks, de propósito — duas contas diferentes
    para «o que este deck tem de comprar» liam-se como erro. Desde 2026-09-11 o
    deck de baixo compra o que o de cima já usa (*"o próximo passa a marcar
    como faltas para comprar"*), por isso a soma das abas é o custo de ter os
    decks todos montados, e dá o mesmo que `todos_juntos`.

    Até essa data havia uma reserva partilhada e o teto do playset: se o deck 1
    já obrigava a comprar 2 Defy, o deck 2 não pedia mais nenhum, porque as
    cartas «trocavam-se entre decks». A frase dele revogou isso.

    O que vem a caminho conta como tido, como em toda a secção — desde
    2026-09-11 (tarde) é a própria alocação que o desconta (quarto monte,
    `a_caminho`), por isso aqui não se soma nada: somar outra vez contava a
    encomenda a dobrar.

    Desde a noite de 2026-09-11 a soma das abas JÁ NÃO é o total: dois decks
    com a mesma Legend mostram cada um a sua lista, mas pedem as mesmas cópias
    e o total conta-as uma vez (`grupo`). A aba diz-o.
    """
    cfg = config.load()
    ignorar = set(cfg.get("faltas_ignorar_tipos", []))
    tipos = _tipos(con)
    alloc = decks.allocate(con)

    out = []
    for d in decks.decks_index(con):
        comprar = {k: n for k, n in alloc[d["id"]]["missing"].items()
                   if tipos.get(k, (None, False))[0] not in ignorar}
        by_set = _agrupar(con, comprar, alloc[d["id"]]["missing_especial"])
        out.append({
            "id": d["id"], "name": d["name"], "priority": d["priority"],
            "have": d["have"], "wanted": d["wanted"],
            "cards": sum(len(g["items"]) for g in by_set),
            "copies": sum(g["copies"] for g in by_set),
            "cents": sum(g["cents"] for g in by_set),
            "by_set": by_set,
            "grupo": d["grupo"],
        })
    return out


def todos_juntos(con: sqlite3.Connection) -> dict:
    """Os decks todos montados AO MESMO TEMPO: soma-se o que cada deck pede e
    desconta-se o que ele tem.

    Desde 2026-09-11 é a regra dos decks — e por isso dá o mesmo total que a
    soma das abas do `por_deck`. Fica como está: é a vista de tudo junto, sem
    a partição por deck.
    """
    cfg = config.load()
    ignorar = set(cfg.get("faltas_ignorar_tipos", []))
    tipos = _tipos(con)
    # A soma do `missing` dos grupos (2026-09-17, `_falta_global`): é a mesma
    # conta que a soma das abas, lugar a lugar — a especial da Legend/Champion
    # à parte.
    falta, falta_esp = _falta_global(con)
    comprar = {k: n for k, n in falta.items()
               if tipos.get(k, (None, False))[0] not in ignorar}
    by_set = _agrupar(con, comprar, falta_esp)
    return {
        "cards": sum(len(g["items"]) for g in by_set),
        "copies": sum(g["copies"] for g in by_set),
        "cents": sum(g["cents"] for g in by_set),
        "by_set": by_set,
    }


def compras(con: sqlite3.Connection) -> dict:
    """As listas de compra dos DECKS: `api/compras.json`.

    É o que resta do `payload` que alimentava o separador «Faltas»/«Quanto
    custa» (`api/faltas.json`, apagado a 2026-09-15 à tarde — o separador
    passou a ser a tabela de preços, `quanto_custa.py`). O que aqui fica é o
    que as abas Staples, Por deck e Pimp decks do separador Decks lêem; a
    wantlist da Coleção tem ficheiro próprio (`api/wantlist.json`,
    `a_subir.master_faltas`) e a lista «A caminho» já vivia nas Encomendas
    (`api/encomendas.json`).
    """
    todas = shortfall(con)
    return {
        "staples": staples(con),
        "por_deck": por_deck(con),
        "todos_juntos": todos_juntos(con),
        "pimp": pimp(con),
        "ignored_types": sorted(config.load().get("faltas_ignorar_tipos", [])),
        "totals": {
            "cards": len(todas),
            "copies": sum(x["missing"] for x in todas),
            "cents": sum(x["total"] for x in todas),
        },
    }


# ---------------------------------------------------------------------------
# Exportar para a wantlist do Cardmarket
# ---------------------------------------------------------------------------


def wantlist(grupos: list[dict], com_edicao: bool = True,
             com_versao: bool = True, com_variantes: bool = False) -> dict:
    """Texto para colar na wantlist do Cardmarket, a partir das listas dos decks.

    A linha é escrita pelo `cardmarket.linha`, o mesmo gerador das abas «A
    subir» e «Master set» — o formato vive num sítio só. Ver lá o porquê do
    formato e do foil.
    """
    linhas, foil = [], []

    def escreve(qtd, nome, v, n, edicao, ehfoil):
        linha = cardmarket.linha({
            "missing": qtd, "market_name": nome,
            "v": v if com_versao else None, "n_versions": n,
            "market_set": edicao if com_edicao else None,
        })
        linhas.append(linha)
        if ehfoil:
            foil.append(linha)

    for g in grupos:
        for it in g.get("items", []):
            escreve(it["qty"], it.get("market_name") or it["name"],
                    it.get("v"), it.get("n_versions", 1),
                    it.get("market_set"), it.get("foil_only"))
            if com_variantes:
                for a in it.get("outras_versoes", []):
                    escreve(it["qty"], a["name"], a["v"], a["n"],
                            a["set"], a["foil_only"])

    return {"text": "\n".join(linhas), "lines": len(linhas), "foil": foil}


# ---------------------------------------------------------------------------
# "Pimp decks": as versões alteradas das cartas que os decks usam
# ---------------------------------------------------------------------------


def pimp(con: sqlite3.Connection) -> dict:
    """Impressões alternativas das cartas usadas nos decks.

    "Versão alterada" = tudo o que não é a impressão canónica da carta: artes
    alternativas, reimpressões showcase (que têm número de coleção próprio) e
    promos. As signatures ficam de fora por omissão (`pimp_ignorar_tipos`).

    Devolve duas leituras dos mesmos dados: `by_set`, tudo junto por edição, e
    `by_deck`, uma lista por deck — porque a decisão de pimpar é por deck, e é
    a olhar para um deck de cada vez que ele decide o que vale a pena trocar.

    É LISTA DE COMPRAS (mudou a 2026-09-02, a pedido dele): desconta o que já
    tem e o que vem a caminho, por impressão, e a quantidade mostrada é só o
    que ainda falta comprar. As versões já completas saem da lista e contam em
    `done`.
    """
    quem = _wanted(con)
    if not quem:
        return {"cards": 0, "printings": 0, "cents": 0, "owned": 0,
                "by_set": [], "by_deck": [], "ignored": []}

    cfg = config.load()
    fora = set(cfg.get("pimp_ignorar_tipos", []))
    # Impressões concretas que ele nunca vai comprar — as sobrenumeradas de
    # topo, do género do `unl-238-219` (Baron Nashor a 2400 €). A carta
    # continua no Pimp pelas outras versões que tenha (ver `pimp_ignorar_impressoes`).
    fora_ids = set(cfg.get("pimp_ignorar_impressoes", []))
    tipos = _tipos(con)
    # O «quantas tenho ao todo» — físico, de qualquer impressão. Não é o
    # `decks.owned_by_card`, que desde 2026-09-16 só conta o que o deck joga.
    tenho_carta = metrics.owned_by_card(con)
    ordens = {s: config.set_order(s) for s in
              (r["set_id"] for r in con.execute("SELECT DISTINCT set_id FROM catalog.printings"))}
    versoes = cardmarket.versoes(con)
    # O que já está tratado: o que tem na caixa mais o que vem a caminho.
    # Estas saem da lista — ele pediu para ver só o que ainda tem de comprar.
    copias = {r["printing_id"]: r["qty"] for r in
              con.execute("SELECT printing_id, qty FROM copies WHERE qty > 0")}
    for pid, q in pending.open_qty(con).items():
        copias[pid] = copias.get(pid, 0) + q
    mkt = {r["printing_id"]: r["market_set"] for r in
           con.execute("SELECT printing_id, market_set FROM catalog.cardtrader_map")}

    usados = list(quem)
    ph = ",".join("?" * len(usados))
    linhas = [dict(r) for r in con.execute(
        f"SELECT p.card_key, p.printing_id, p.set_id, p.api_sort, p.variant_kind, "
        f"       p.variant_label, p.public_code, p.orientation, p.name, p.type, "
        f"       p.image_medium, p.image_large, p.image_url, pl.price_cents "
        f"FROM catalog.printings p "
        f"LEFT JOIN catalog.price_latest pl ON pl.printing_id = p.printing_id "
        f"WHERE p.card_key IN ({ph})", usados)]

    por_carta: dict[str, list] = {}
    for r in linhas:
        por_carta.setdefault(r["card_key"], []).append(r)

    # As versões alteradas de cada carta, uma vez só. Uma RETIRADA — a runa em
    # alt art (2026-09-17: *"nao incluas em nada"*) — não é versão para pimpar:
    # os decks jogam a runa base.
    alt_de: dict[str, list] = {}
    for ck, lst in por_carta.items():
        lst.sort(key=lambda r: (ordens.get(r["set_id"], 999), r["api_sort"]))
        canonica = next((r for r in lst if r["variant_kind"] == "base"), lst[0])
        alt = [r for r in lst if r["printing_id"] != canonica["printing_id"]
               and r["variant_kind"] not in fora
               and r["printing_id"] not in fora_ids
               and not metrics.retirada(r, cfg)]
        if alt:
            alt_de[ck] = alt

    # Artes alternativas que só o CardTrader lista — as runas do SFD, UNL e
    # VEN. Ficam fora do catálogo (não contam para métricas nenhumas) e
    # entravam aqui, porque era o que o André queria pimpar quando o Legend
    # do deck é dessa edição. Desde 2026-09-17 uma runa em alt art está
    # retirada seja de que fonte for, por isso hoje este ciclo não acrescenta
    # nenhuma; fica para uma carta que não seja runa, se o CardTrader a tiver
    # e a RiftScribe não.
    precos_mo = {r["printing_id"]: r["price_cents"] for r in con.execute(
        "SELECT printing_id, price_cents FROM catalog.price_latest")}
    for r in con.execute(
        "SELECT printing_id, set_id, collector_raw, market_name, market_set, "
        "       image_url, card_key, cardmarket_id "
        "FROM catalog.market_only "
        "WHERE card_key IS NOT NULL AND version LIKE '%Alternate Art%'"
    ):
        if r["card_key"] not in quem:
            continue
        if metrics.retirada({"type": tipos.get(r["card_key"], (None,))[0],
                             "variant_kind": "alt_art"}, cfg):
            continue
        alt_de.setdefault(r["card_key"], []).append({
            "card_key": r["card_key"], "printing_id": r["printing_id"],
            "set_id": r["set_id"], "api_sort": 9999,
            "variant_kind": "alt_art", "variant_label": "Arte alt.",
            # O CardTrader omite o 'a' na Calm Rune do SFD; a carta impressa
            # e a fatura levam-no, e é por aí que ele procura.
            "public_code": f"{r['set_id']}-{r['collector_raw']}"
                           + ("" if (r["collector_raw"] or "").lower().endswith("a") else "a"),
            "orientation": "portrait", "name": r["market_name"],
            "image_medium": None, "image_large": None,
            # Sem o `www.` o CardTrader responde 301; poupa-se um salto por
            # imagem, e evita-se um `<img>` a falhar se o cliente não seguir.
            "image_url": (r["image_url"] or "").replace(
                "https://cardtrader.com/", "https://www.cardtrader.com/") or None,
            "price_cents": precos_mo.get(r["printing_id"]),
            "market_only": True, "market_name": r["market_name"],
            "market_set": r["market_set"],
        })

    def montar(pedido: dict[str, int], preferir: str | None = None) -> dict:
        """{card_key: quantas o deck usa} -> estrutura por edição.

        `preferir` é a edição do Legend do deck: quando uma carta tem versão
        alterada nessa edição, mostra-se só essa. É o pedido do André para as
        runas — um deck cujo Legend é do SFD quer as runas alternativas do
        SFD, não as do OGN.

        HOJE ISTO NÃO MUDA NADA: a RiftScribe só tem runas no OGN e no VEN,
        e as artes alternativas delas só no OGN. As do SFD e do UNL existem
        (o CardTrader tem-nas) mas não estão no catálogo. Ver CLAUDE.md.
        """
        por_set: dict[str, dict] = {}
        cents = owned = feitas = 0
        for ck, qtd in pedido.items():
            opcoes = alt_de.get(ck, [])
            if preferir:
                mesma = [r for r in opcoes if r["set_id"] == preferir]
                if mesma:
                    opcoes = mesma
            for r in opcoes:
                v = versoes.get(r["printing_id"]) or {}
                tem = copias.get(r["printing_id"], 0)
                # Só interessa o que ainda falta comprar desta versão.
                falta = qtd - tem
                if falta <= 0:
                    feitas += 1
                    continue
                owned += 1 if tem else 0
                sub = (r["price_cents"] or 0) * falta
                cents += sub
                d = por_set.setdefault(r["set_id"], {
                    "set": r["set_id"], "name": config.set_name(r["set_id"]),
                    "printings": 0, "cents": 0, "items": []})
                d["printings"] += 1
                d["cents"] += sub
                d["items"].append({
                    "card_key": ck, "name": r["name"], "qty": falta,
                    "code": r["public_code"], "label": r["variant_label"],
                    "kind": r["variant_kind"],
                    "price": r["price_cents"], "total": sub,
                    "have": tem, "have_base": tenho_carta.get(ck, 0),
                    "landscape": (r["orientation"] or "").lower() == "landscape",
                    "img": None if r.get("market_only") else f"img/{r['printing_id']}.webp",
                    "cdn": r["image_medium"] or r["image_large"] or r["image_url"],
                    "market_only": bool(r.get("market_only")),
                    "market_name": r.get("market_name") or v.get("name"),
                    "market_set": r.get("market_set") or mkt.get(r["printing_id"]),
                    # As market_only não têm grupo para numerar; em Riftbound
                    # a arte alternativa é sempre a V.2 de 2 (medido nas 102
                    # que o catálogo tem).
                    "v": v.get("v", 2 if r.get("market_only") else None),
                    "n_versions": v.get("n", 2 if r.get("market_only") else 1),
                    "foil_only": v.get("foil_only", False),
                    "decks": sorted(x["deck"] for x in
                                    quem.get(ck, {}).get("decks", {}).values()),
                })
        out = sorted(por_set.values(), key=lambda d: (ordens.get(d["set"], 999), d["set"]))
        for d in out:
            d["items"].sort(key=lambda x: (-x["total"], x["name"]))
        return {
            "cards": len({it["card_key"] for d in out for it in d["items"]}),
            "printings": sum(d["printings"] for d in out),
            "cents": cents, "owned": owned, "done": feitas, "by_set": out,
        }

    def teto(ck: str, n: int) -> int:
        t, tok = tipos.get(ck, (None, False))
        return min(n, metrics.playset_target(t, tok, cfg)) or 1

    # Vista global: o que os decks pedem ao todo, com o teto de playset.
    geral = montar({ck: teto(ck, v["qty"]) for ck, v in quem.items() if ck in alt_de})

    # A edição do Legend de cada deck. Quando uma carta tem versão alterada em
    # várias edições, é a dessa que interessa — o deck é "de" uma edição.
    legend_set = {}
    for r in con.execute(
        "SELECT dc.deck_id, p.set_id FROM deck_cards dc "
        "JOIN catalog.cards c ON c.card_key = dc.card_key "
        "JOIN catalog.printings p ON p.printing_id = c.rep_printing_id "
        "WHERE dc.role = 'legend'"
    ):
        legend_set[r["deck_id"]] = r["set_id"]

    # Vista por deck: só o que aquele deck usa.
    por_deck = []
    for d in decks.decks_index(con):
        # `alt_de` só tem cartas do `quem`, que já não leva runas.
        pedido = {ck: teto(ck, q) for ck, q in decks._need(con, d["id"]).items()
                  if ck in alt_de}
        por_deck.append({"id": d["id"], "name": d["name"], "priority": d["priority"],
                         "legend_set": legend_set.get(d["id"]),
                         **montar(pedido, legend_set.get(d["id"]))})

    return {**geral, "by_deck": por_deck, "ignored": sorted(fora)}

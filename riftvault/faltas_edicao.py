"""O separador «Faltas»: o que falta, por edição, em quatro blocos — cada um
com a sua wantlist.

André, 2026-09-15 (fim da tarde): *"quero agora fazer uma seccao de faltas /
quero as faltas por edicao e dividido em 3 partes / Masterset / Alt Art /
OverNumbered"*. E 2026-09-19: *"as wantlist das edicoes, quero 4 wantlist: 1
so para o master set, 1 so para as Alt.Art, 1 so para as Overnumbered, uma so
para as Promo (no caso SP)"* — as promos ganharam o quarto bloco, e cada bloco
a sua wantlist do Cardmarket (`wantlist`), separada das outras.

NÃO É O SEPARADOR QUE SE APAGOU HORAS ANTES. O antigo separador (o id
`faltas`, que ficou para o `faltas.py` dos decks) tinha as faltas do master
set arrumadas por raridade e ele mandou-as sair de lá porque passou a ser a
tabela de preços — apagada por sua vez a 2026-09-19 (ver o CLAUDE.md). Isto é
uma secção PRÓPRIA, com outra organização: por edição, e dentro de cada
edição os blocos pela ordem da Coleção.

NÃO É UM CÁLCULO NOVO. A carência é a mesma da wantlist do fim de cada edição
da Coleção (`a_subir.master_faltas`): o mesmo âmbito (`a_subir.masterset`),
os mesmos alvos (`metrics.alvo`), as mesmas cópias (`locais.na_colecao`, só o
que está nos binders de Coleção) e o mesmo pendente (`pending.open_qty`). O
que muda é a arrumação — e que aqui a coleção extra também se VÊ.

OS QUATRO BLOCOS
    `master`       — a sequência numerada da edição (`metrics.BLOCO_MASTER`),
                     alvo do tipo: Unit/Spell/Gear 3, Legend e Battlefield 1,
                     runas numeradas 3 (2026-09-15).
    `alt_art`      — as artes alternativas, pelo `variant_kind`. Inclui as
                     seis artes alternativas das runas do OGN, que a grelha
                     da Coleção arruma no bloco «runas especiais»: ele chamou
                     ao bloco «Alt Art», e uma `OGN-007a` é uma arte
                     alternativa. (Hoje estão retiradas de tudo, 2026-09-17,
                     e nem chegam ao âmbito.) Alvo de playset (2026-09-18).
    `overnumbered` — as sobrenumeradas (`metrics.BLOCO_OVER`), alvo 1
                     (`master_set.um_de_cada`, 2026-09-15).
    `special`      — as promos `VEN-SP` (2026-09-19), alvo 1 (`um_de_cada`,
                     desde o mesmo dia). De 2026-09-15 a 2026-09-19 ficaram
                     de fora do separador porque ele tinha nomeado três
                     blocos; a 19/09 nomeou-as.

    A ORDEM é a da Coleção — `master_set.ordem_dos_blocos`, lida por
    `metrics.ordem_dos_blocos` e cortada aos quatro ids de cima (`blocos`).
    Até 2026-09-19 este separador tinha uma ordem própria (master set, Alt
    Art, OverNumbered, a de 15/09); passou a ler a mesma lista que a grelha
    para ele mudar num sítio e mudar nos dois. Na mensagem de 19/09 ele
    enumerou «master set, Alt.Art, Overnumbered, Promo» — é a ordem de quem
    enumera, não um pedido de ordem diferente (fica no relatório).

    Tokens, signatures e runas sem numeração continuam escondidos
    (`metrics.e_colecao`), como em todo o lado; o que a página da Coleção
    mostre e não caiba em nenhum dos quatro (hoje nada) vai em `scope.fora`.

VER NÃO É COMPRAR — MAS CADA BLOCO TEM A SUA WANTLIST
    SÓ o master set entra nas listas de compra GERAIS — a wantlist do fim de
    cada edição da Coleção, a «Wantlist — tudo», o «A subir». É a frase dele
    de 15/09: *"sobrenumeradas não entram na wantlist, nem na % de coleção
    completa; apenas pedi para ser feito track de playset para eu saber
    exatamente quantas tenho"*. Cada bloco leva `in_lists`, lido do MESMO
    botão que manda nessas listas (`listas_de_compra.so_master_set`, via
    `a_subir.blocos_fora`).

    O que 19/09 acrescenta é OUTRA coisa: cada bloco tem a SUA wantlist do
    Cardmarket, própria do bloco, separada das outras — os itens já levam os
    campos do gerador (`market_name`, `v`, …) e o `wantlist()` escreve-a pelo
    `cardmarket.gerar`, o mesmo das outras listas. A wantlist da Alt Art
    existe porque ele a pediu; a «Wantlist — tudo» da Coleção NÃO cresce por
    isso (há teste) — acompanhar continua a não ser querer comprar em bloco.

O QUE VEM A CAMINHO CONTA
    Uma cópia encomendada e ainda não recebida (`pending`) não é falta por
    comprar. Cada item leva `have` (na Coleção), `pending` (a caminho, cortado
    ao que falta) e `missing` = o que ainda há a COMPRAR, `alvo − have −
    pending`. Uma carta toda coberta pelo pendente continua na lista, marcada
    — para ele ver que está a chegar —, mas com `missing` 0, e não soma aos
    totais de compra. Os totais de cada bloco (`copies`, `cents`) são só o que
    há a comprar; o pendente vai à parte (`pending_copies`).

    Por construção, o bloco `master` de cada edição pede EXACTAMENTE as cópias
    da wantlist dessa edição (`a_subir.master_faltas`) — há teste.

ESTE FICHEIRO É A METADE DAS NORMAIS (2026-09-27)
    O separador passou a ter duas metades à vista: as NORMAIS (estes quatro
    blocos) e as FOILS (*"quero as faltas separadas, as normais e as foils / as
    foils nao sao faltas, sao apenas complemento e indicativo"*). A metade das
    foils vive no `faltas_foil.py` e é ele que compõe as duas
    (`faltas_foil.payload_completo`) — deste ficheiro nada mudou a não ser o
    nome de duas funções, e é isso que prova que as faltas normais dão o mesmo
    número antes e depois.

    O `item()` e o `soma()` são PÚBLICOS desde então: são a forma de uma linha
    de falta e a soma de um bloco, e as duas metades usam a mesma (era `_item`
    e `_soma`). Um segundo par era uma segunda definição de «falta».

AS CAIXAS (2026-10-02)
    André: *"nas faltas, tens as faltas de masterset, mas gostava que tivesse
    uma caixa tambem para faltas de Overnumbered e outra caixa para faltas
    AltArt e uma caixa para as faltas de Vendetta (que era tudo). pode ser com
    sistema de botoes para nao ocupar muito espaco"*.

    O separador é POR EDIÇÃO: com «Todas» escolhido são cinco edições × quatro
    blocos, e portanto vinte listas do Cardmarket para percorrer. O que faltava
    era o corte ao contrário — **uma caixa que atravesse as edições**:

        OverNumbered   os 92 sobrenumerados das quatro edições, numa lista
        Alt Art        as 96 artes alternativas, numa lista
        Vendetta       o VEN INTEIRO, os quatro blocos numa lista

    «Tens as faltas de masterset» é verdade e explica porque é que estas três
    são as que faltavam: a lista do master set de todas as edições já existe —
    é a «Wantlist — tudo» do fim da Coleção (`a_subir.wantlist`). As outras
    três categorias nunca tiveram uma lista que não fosse por edição.

    NÃO É UM CÁLCULO NOVO, E NÃO HÁ UM SEGUNDO ITEM. Uma caixa é uma
    RE-ARRUMAÇÃO dos itens que o `payload` já calculou, e leva só a lista dos
    `printing_id` (`pids`) — nunca uma cópia da linha. É o que faz o `+` de «já
    encomendei» continuar a valer sem plumbing nenhum: o `feItem` do `app.js`
    mexe no ÚNICO objecto daquela impressão, e a caixa e o bloco da edição
    dizem o mesmo número por serem a mesma linha. Duas cópias divergiam no
    primeiro clique.

    AS CAIXAS SOBREPÕEM-SE, e é o que ele quer. Uma sobrenumerada do VEN está
    na caixa «OverNumbered» E na «Vendetta» («que era tudo») — dito-lhe, não
    objectou. Por isso **a soma das caixas não é o total do separador** e a
    página tem de o dizer, como a nota do «Todos juntos» dos decks diz desde
    2026-09-11.

    AS SIGNATURES: ELE NOMEOU-AS PARA A CAIXA DO VEN E SÃO ZERO. A caixa leva
    «master set, sobrenumeradas, alt art, signatures e promos» nas palavras
    dele. As signatures saíram da Coleção a 2026-09-09 e estão ESCONDIDAS
    (`master_set.escondidas` leva o `"*"`), por isso não chegam ao âmbito — e
    **o VEN não tem nenhuma no catálogo da RiftScribe** (medido a 02/10: 0 de
    228). Não se alargou o âmbito para apanhar zero cartas: fazê-lo era
    desfazer a decisão de 09/09 sem um caso. O que se fez foi CONTAR o que
    ficou de fora (`escondidas`, por `variant_kind`) e pô-lo no ecrã — hoje
    lê-se «7 escondidas: 6 runas sem numeração · 1 token», e uma signature nova
    apareceria ali pelo nome em vez de desaparecer em silêncio.

    AS FOILS TAMBÉM NÃO ENTRAM, pela mesma razão de serem outra pergunta: ele
    separou-as a 2026-09-27 (*"as foils nao sao faltas, sao apenas complemento
    e indicativo"*) e não as nomeou nesta. A metade das foils do VEN continua
    onde está, no separador da edição, e a caixa diz quantas são.

    QUAIS SÃO AS CAIXAS VIVE NO CONFIG — `faltas_edicao.caixas_blocos` e
    `caixas_edicoes` (ver `caixas_escolhidas`). Ele nomeou dois blocos e uma
    edição; uma edição nova que ele queira ver inteira é uma palavra na lista,
    não um `if` no código. Um bloco ou uma edição que não existam REBENTAM, com
    a lista do que há — a regra das outras listas do config.
"""

from __future__ import annotations

import sqlite3

from . import a_subir, cardmarket, config, locais, metrics, pending

# O CATÁLOGO dos blocos deste separador, com o rótulo que ele lhes deu. A
# ordem NÃO é esta: é `blocos(cfg)`, que lê a lista partilhada com a grelha.
# O id da alt art é o `variant_kind`, porque «Alt Art» aqui inclui as artes
# alternativas das runas (ver o topo do ficheiro); os outros são os da grelha.
BLOCO_LABEL = {
    metrics.BLOCO_MASTER: "Master set",
    "alt_art": "Alt Art",
    metrics.BLOCO_OVER: "OverNumbered",
    "special": "Promos",
}
BLOCO_IDS = list(BLOCO_LABEL)

# AS CAIXAS (2026-10-02, ver o topo do ficheiro). Quais são vem do config; isto
# são os defaults, as que ele nomeou. O `riftvault_config.json` e o
# `config.DEFAULTS` dizem o mesmo.
CAIXAS_DEFAULTS: dict = {
    "caixas_blocos": [metrics.BLOCO_OVER, "alt_art"],
    "caixas_edicoes": ["VEN"],
}
# O alvo de uma caixa de edição é o de cada bloco dela — não há um alvo por
# cima de tudo. A mesma frase do chip «Tudo» do painel da Coleção.
ALVO_MISTO = "cada bloco com o seu alvo"
# O sufixo do botão de uma caixa de edição — são as palavras dele, «que era
# tudo», e é o que a distingue do botão da edição ao lado.
TUDO = "tudo"


def opcoes(cfg: dict | None = None) -> dict:
    """O bloco `faltas_edicao` do config, com os defaults por baixo."""
    cfg = cfg if cfg is not None else config.load()
    return {**CAIXAS_DEFAULTS, **(cfg.get("faltas_edicao") or {})}


def caixas_escolhidas(cfg: dict | None = None,
                      sets_ids: list[str] | None = None) -> list[dict]:
    """As caixas a mostrar, pela ordem: primeiro os blocos, depois as edições.

    Os blocos saem pela ordem da Coleção (a mesma de `blocos`), para a fila dos
    botões seguir a ordem que ele já vê na grelha; as edições pela ordem dos
    separadores. Um id que não exista rebenta com a lista do que há — uma caixa
    mal escrita ignorada em silêncio deixava-o a olhar para uma fila de botões
    sem a que pediu.
    """
    o = opcoes(cfg)
    pedidos_b = list(dict.fromkeys(o["caixas_blocos"] or ()))
    pedidos_e = list(dict.fromkeys(o["caixas_edicoes"] or ()))
    for b in pedidos_b:
        if b not in BLOCO_LABEL:
            raise ValueError(
                f"faltas_edicao.caixas_blocos: bloco desconhecido: {b!r}. "
                f"Há: {', '.join(BLOCO_IDS)}")
    if sets_ids is not None:
        for s in pedidos_e:
            if s not in sets_ids:
                raise ValueError(
                    f"faltas_edicao.caixas_edicoes: não há edição {s!r}. "
                    f"Há: {', '.join(sets_ids)}")
    ordem_b = [b for b, _ in blocos(cfg) if b in pedidos_b]
    out = [{"id": f"bloco-{b}", "label": BLOCO_LABEL[b], "bloco": b, "set": None}
           for b in ordem_b]
    ordem_e = sorted(pedidos_e, key=lambda s: (config.set_order(s), s))
    # «VEN — tudo», não «VEN»: o separador já tem um botão «VEN» (a edição em
    # quatro blocos, com o master set na wantlist geral) e esta caixa é outra
    # coisa — a edição inteira numa lista. Dois botões com a mesma palavra ao
    # lado um do outro leem-se como um (é a lição do «principal» contra a
    # «prioridade 1», 2026-09-27). O nome é o do config, que para o VEN é o
    # CÓDIGO por decisão dele de 2026-08-31; ele chama-lhe «Vendetta» e o
    # sufixo é que diz o que a caixa tem.
    out += [{"id": f"edicao-{s}", "label": f"{config.set_name(s)} — {TUDO}",
             "bloco": None, "set": s} for s in ordem_e]
    return out


def escondidas_por_set(con: sqlite3.Connection,
                       cfg: dict | None = None) -> dict[str, dict[str, int]]:
    """Por edição, quantas impressões estão ESCONDIDAS e de que tipo.

    Quem está escondido (`metrics.escondida` — tokens, signatures, runas sem
    numeração, runas retiradas) não entra em página nenhuma, e por isso não
    entra na caixa de uma edição «inteira». Conta-se para a caixa poder DIZÊ-LO
    em vez de calar: ele nomeou as signatures para a caixa do VEN e elas são
    zero, e é esta contagem que o mostra pelo nome.
    """
    cfg = cfg if cfg is not None else config.load()
    out: dict[str, dict[str, int]] = {}
    for r in con.execute(
        "SELECT printing_id, set_id, collector_number, public_code, name, card_key, "
        "       variant_kind, variant_label, rarity, base_rarity, type, is_token "
        "FROM catalog.printings"
    ):
        if not metrics.escondida(r, cfg):
            continue
        kind = r["variant_kind"] or "base"
        por = out.setdefault(r["set_id"], {})
        por[kind] = por.get(kind, 0) + 1
    return out


def caixas(sets: list[dict], cfg: dict | None = None,
           escondidas: dict[str, dict[str, int]] | None = None) -> list[dict]:
    """As caixas, re-arrumando os itens que as edições já têm.

    Leva a MESMA forma de um bloco — `id`, `label`, `scope`, os campos do
    `soma`, `wantlist` — para o cliente desenhar as duas com a mesma função; o
    que a caixa NÃO leva é `items`, só os `pids` pela ordem em que se vêem (ver
    o topo do ficheiro: uma segunda cópia da linha divergia no primeiro `+`).
    """
    sets_ids = [d["set"] for d in sets]
    escondidas = escondidas if escondidas is not None else {}
    out = []
    for c in caixas_escolhidas(cfg, sets_ids):
        # As edições que a caixa atravessa, pela ordem dos separadores; e os
        # blocos de cada uma, pela ordem da Coleção. As duas ordens já estão
        # nos `sets`, por isso a caixa herda-as sem reordenar nada.
        dentro = [d for d in sets if c["set"] is None or d["set"] == c["set"]]
        grupos = [(d, g) for d in dentro for g in d["blocks"]
                  if c["bloco"] is None or g["id"] == c["bloco"]]
        # Uma edição que não tenha âmbito neste bloco (o OGS não tem
        # sobrenumeradas) não é uma edição que a caixa atravesse: ficava no
        # `sets` a dizer que contribui com nada.
        com_ambito = [d["set"] for d in dentro
                      if any(g["scope"] for e, g in grupos if e is d)]
        itens = [x for _, g in grupos for x in g["items"]]
        nas_listas = [x for _, g in grupos if g["in_lists"] for x in g["items"]]
        alvos = {metrics.alvo_do_bloco(g["id"], cfg) for _, g in grupos}
        caras = [x for x in itens if x["missing"] > 0 and x["price"] is not None]
        mais_cara = max(caras, key=lambda x: x["total"]) if caras else None
        out.append({
            **c,
            # Em palavras, o que a caixa junta — é o que o cabeçalho escreve.
            # «4 edições» e não «todas»: o OGS não tem sobrenumeradas, e
            # «todas» prometia uma edição que a caixa não atravessa.
            "escopo_label": (f"{len(com_ambito)} edições"
                             if c["set"] is None
                             else f"a edição inteira · {len(grupos)} blocos"),
            "target_label": alvos.pop() if len(alvos) == 1 else ALVO_MISTO,
            # Verdade só quando TUDO o que está na caixa entra nas listas de
            # compra gerais. Na caixa de uma edição é quase sempre falso e
            # mesmo assim parte dela entra (o master set) — é o `lists` que
            # diz quanto, para a página não prometer o que não é.
            "in_lists": bool(grupos) and all(g["in_lists"] for _, g in grupos),
            "lists": soma(nas_listas),
            "scope": sum(g["scope"] for _, g in grupos),
            "sets": com_ambito,
            "blocos": list(dict.fromkeys(g["id"] for _, g in grupos)),
            **soma(itens),
            "pids": [x["printing_id"] for x in itens],
            "wantlist": _wantlist_do_bloco(itens),
            # Um total de 6 660 € em 51 cópias não se lê sem isto: 2 100 € são
            # UMA carta (o `UNL-238` Baron Nashor, que ele disse a 2026-09-05
            # que nunca compraria). A linha mais cara fica à vista.
            "mais_cara": ({"code": mais_cara["code"], "name": mais_cara["name"],
                           "cents": mais_cara["total"]} if mais_cara else None),
            # O que a caixa não alcança, e porquê: o que está ESCONDIDO não
            # entra em página nenhuma (e é aqui que se vê que as signatures do
            # VEN são zero). A metade das FOILS é outra pergunta e também não
            # entra — quem a conta é o `faltas_foil.payload_completo`, que é o
            # único sítio onde as duas metades se conhecem.
            "escondidas": (escondidas.get(c["set"], {}) if c["set"] else {}),
        })
    return out


def blocos(cfg: dict | None = None) -> list[tuple[str, str]]:
    """Os quatro blocos, `(id, rótulo)`, pela ordem da Coleção.

    `metrics.ordem_dos_blocos` devolve TODOS os blocos da grelha; ficam os que
    este separador tem. O bloco «runas especiais» da grelha não existe aqui
    — as artes alternativas das runas são «Alt Art» —, por isso sai da lista
    sem deixar buraco.
    """
    ordem = [b for b in metrics.ordem_dos_blocos(cfg) if b in BLOCO_LABEL]
    return [(b, BLOCO_LABEL[b]) for b in ordem]


def bloco_das_faltas(printing, cfg: dict | None = None) -> str | None:
    """Em qual dos quatro blocos cai esta impressão; `None` se em nenhum.

    A arte alternativa decide-se pelo `variant_kind` — antes do bloco da
    grelha, que manda as das runas para «runas especiais». O resto é o bloco
    da grelha: `master`, `overnumbered` ou `special` (as promos, 2026-09-19).
    O que mais houver (`rune_promo`, uma variante nova) devolve `None` e a
    página diz que ficou de fora.
    """
    if printing["variant_kind"] == "alt_art":
        return "alt_art"
    b = metrics.bloco(printing, cfg)
    return b if b in BLOCO_LABEL else None


def em_falta(con: sqlite3.Connection, escopo: dict[str, dict]) -> dict[str, dict]:
    """Do âmbito, o que ele ainda não tem na Coleção — com o pendente à parte.

    O gémeo do `a_subir.em_falta`, com uma diferença: ali o pendente soma-se
    ao que ele tem e a carta desaparece; aqui fica visível, marcada. A conta
    do que há a COMPRAR é a mesma (`alvo − cópias − a caminho`), e é isso que
    o teste contra a wantlist fixa.
    """
    tenho = locais.na_colecao(con)
    a_caminho = pending.open_qty(con)
    out: dict[str, dict] = {}
    for pid, info in escopo.items():
        have = tenho.get(pid, 0)
        curto = info["target"] - have
        if curto <= 0:
            continue
        pend = min(a_caminho.get(pid, 0), curto)
        out[pid] = {**info, "have": have, "pending": pend,
                    "missing": curto - pend, "short": curto}
    return out


def item(pid: str, info: dict, preco: int | None, mkt: dict) -> dict:
    total = (preco or 0) * info["missing"]
    return {
        "printing_id": pid, "name": info["name"],
        "code": info["public_code"], "set": info["set_id"],
        "cn": info["collector_number"],
        "kind": info["variant_kind"], "label": info["variant_label"],
        "rarity": info["base_rarity"] or "?",
        "landscape": (info["orientation"] or "").lower() == "landscape",
        "img": f"img/{pid}.webp",
        "cdn": info["image_medium"] or info["image_large"] or info["image_url"],
        "have": info["have"], "target": info["target"],
        "pending": info["pending"],
        # `missing` é o que há a COMPRAR; `short` é o que falta na caixa
        # (com o pendente ainda por chegar).
        "missing": info["missing"], "short": info["short"],
        "price": preco, "total": total,
        # Os campos do gerador do Cardmarket, os mesmos nomes da wantlist —
        # só o bloco `master` os usa, mas o item é um só.
        "market_name": mkt.get("name") if mkt.get("name") != info["name"] else None,
        "market_set": mkt.get("set"),
        "v": mkt.get("v"), "n_versions": mkt.get("n", 1),
        "foil_only": bool(mkt.get("foil_only")),
    }


def soma(itens: list[dict]) -> dict:
    return {
        # Só o que há a comprar. Uma carta coberta pelo pendente não conta
        # aqui — está na lista para se ver que vem a caminho.
        "cards": sum(1 for x in itens if x["missing"] > 0),
        "copies": sum(x["missing"] for x in itens),
        "cents": sum(x["total"] for x in itens),
        "no_price": sum(1 for x in itens if x["missing"] > 0 and x["price"] is None),
        "pending_cards": sum(1 for x in itens if x["pending"] > 0),
        "pending_copies": sum(x["pending"] for x in itens),
        # Quantas impressões faltam na caixa, pendente incluído.
        "short_cards": len(itens),
    }


def payload(con: sqlite3.Connection, cfg: dict | None = None) -> dict:
    """O separador inteiro: por edição, os quatro blocos, cada um com o que falta.

    Todas as edições do catálogo, pela ordem dos separadores — o OGS entra: o
    «menos proving grounds» de 2026-09-15 foi pedido para a tabela de preços
    (apagada a 2026-09-19) e vale hoje só no «A mais» (`a_mais.sem_edicoes`).
    Cada edição leva sempre os quatro blocos, vazios ou não, e a soma dos
    quatro.
    """
    cfg = cfg or config.load()
    o = a_subir.opcoes(cfg)
    escopo = a_subir.masterset(con, cfg)
    # As exclusões da sequência (signatures, showcases — hoje tiram zero,
    # porque já estão escondidas), para o bloco `master` ser o MESMO da
    # wantlist. Sem `blocos`: a coleção extra é para se ver aqui, tire-a ou
    # não das listas de compra.
    escopo, _ = a_subir.excluir(escopo, {**o["excluir"], "blocos": []}, so_master=False)
    # O botão das listas de compra gerais, lido do mesmo sítio que as listas
    # o lêem. O master set entra sempre.
    fora_das_listas = set(a_subir.blocos_fora(o["excluir"], o["so_master_set"]))
    in_lists = {b: b == metrics.BLOCO_MASTER or b not in fora_das_listas
                for b in BLOCO_IDS}
    ordem = blocos(cfg)

    falta = em_falta(con, escopo)
    mercado = cardmarket.versoes(con)
    precos = metrics.prices_map(con)

    sets_ids = [r[0] for r in con.execute("SELECT DISTINCT set_id FROM catalog.printings")]
    sets_ids.sort(key=lambda s: (config.set_order(s), s))
    por_set: dict[str, dict[str, list[dict]]] = {s: {b: [] for b in BLOCO_IDS} for s in sets_ids}
    ambito: dict[str, dict[str, int]] = {s: {b: 0 for b in BLOCO_IDS} for s in sets_ids}
    fora: dict[str, int] = {}
    for pid, info in escopo.items():
        b = bloco_das_faltas(info, cfg)
        if b is None:
            nome = metrics.BLOCO_CURTO.get(info["block"], info["block"])
            fora[nome] = fora.get(nome, 0) + 1
            continue
        ambito[info["set_id"]][b] += 1
        if pid in falta:
            por_set[info["set_id"]][b].append(
                item(pid, falta[pid], precos.get(pid), mercado.get(pid) or {}))

    sets = []
    for s in sets_ids:
        grupos = []
        for b, label in ordem:
            itens = sorted(por_set[s][b], key=lambda x: (x["cn"], x["code"]))
            grupos.append({
                "id": b, "label": label,
                # «playset» / «1 de cada», do mesmo config que dá o alvo.
                "target_label": metrics.alvo_do_bloco(b, cfg),
                "in_lists": in_lists[b],
                "scope": ambito[s][b],
                **soma(itens),
                "items": itens,
                # A wantlist DESTE bloco, desta edição (2026-09-19): o texto
                # é o do `cardmarket.gerar`, o mesmo gerador das outras
                # listas; o `app.js` escreve o mesmo a partir dos `items`
                # (`cmLinha`) e há teste que compara os dois.
                "wantlist": _wantlist_do_bloco(itens),
            })
        todos = [x for g in grupos for x in g["items"]]
        sets.append({"set": s, "name": config.set_name(s),
                     # A soma dos quatro blocos — o que ele pediu no
                     # cabeçalho da edição — e, à parte, só o que entra nas
                     # listas de compra gerais.
                     **soma(todos),
                     "lists": soma([x for g in grupos if g["in_lists"] for x in g["items"]]),
                     "blocks": grupos})

    todos = [x for d in sets for g in d["blocks"] for x in g["items"]]
    nas_listas = [x for d in sets for g in d["blocks"] if g["in_lists"] for x in g["items"]]
    return {
        "blocks": [{"id": b, "label": label, "in_lists": in_lists[b]} for b, label in ordem],
        "so_master_set": bool(o["so_master_set"]),
        "rule": str(o["regra_falta"]),
        "totals": soma(todos),
        # Só os blocos que entram nas listas de compra gerais: é este que bate
        # com a wantlist «tudo» da Coleção.
        "totals_lists": soma(nas_listas),
        "sets": sets,
        # AS CAIXAS (2026-10-02): o mesmo que está em cima, cortado ao
        # contrário — por bloco e por edição, atravessando as edições. Chave
        # NOVA: nada do que está acima mexe por ela existir (há teste).
        "caixas": caixas(sets, cfg, escondidas_por_set(con, cfg)),
        "scope": {
            "printings": sum(ambito[s][b] for s in sets_ids for b in BLOCO_IDS),
            # O que está na página da Coleção mas não em nenhum dos quatro
            # blocos — hoje nada; uma variante nova cairia aqui. É o que a
            # página tem de dizer.
            "fora": fora,
        },
    }


def _wantlist_do_bloco(itens: list[dict]) -> dict:
    """O resumo da wantlist de um bloco: só o que há a COMPRAR (`missing > 0`).

    Uma carta toda coberta pelo pendente está na lista do bloco para se ver
    que vem a caminho, mas não vai para o Cardmarket — a wantlist da Coleção
    faz o mesmo. O texto não vai no payload (os `items` já lá estão e o
    cliente escreve-o); vai o que o cabeçalho diz.
    """
    w = cardmarket.gerar([x for x in itens if x["missing"] > 0])
    return {"lines": w["lines"], "copies": w["copies"], "cents": w["cents"],
            "foil": len(w["foil"])}


def wantlist(con: sqlite3.Connection, set_id: str, bloco: str,
             cfg: dict | None = None, com_codigo: bool = False) -> dict:
    """A wantlist de UM bloco de UMA edição, pronta a colar no Cardmarket.

    É a quarta pergunta da ordem de 2026-09-19 respondida em Python, para a
    CLI (`riftvault faltas --edicao OGN --bloco alt_art --cardmarket`) e para
    os testes. O bloco `master` dá exactamente o texto da wantlist dessa
    edição da Coleção (`a_subir.wantlist`) — há teste.
    """
    cfg = cfg or config.load()
    if bloco not in BLOCO_LABEL:
        raise ValueError(f"bloco desconhecido: {bloco!r}. Há: {', '.join(BLOCO_IDS)}")
    p = payload(con, cfg)
    d = next((s for s in p["sets"] if s["set"] == set_id), None)
    if d is None:
        raise ValueError(f"não há edição {set_id!r}")
    g = next(g for g in d["blocks"] if g["id"] == bloco)
    itens = [x for x in g["items"] if x["missing"] > 0]
    return {"set": set_id, "name": d["name"], "block": bloco, "label": g["label"],
            "in_lists": g["in_lists"], **cardmarket.gerar(itens, com_codigo),
            "items": itens}


def wantlist_caixa(con: sqlite3.Connection, caixa: str, cfg: dict | None = None,
                   com_codigo: bool = False) -> dict:
    """A wantlist de UMA caixa, pronta a colar no Cardmarket (2026-10-02).

    A quarta pergunta da ordem respondida em Python, para a CLI (`riftvault
    faltas --caixa bloco-overnumbered --cardmarket`) e para os testes. O texto
    sai do MESMO `cardmarket.gerar` das outras cinco listas; o que muda é só
    quais as linhas. Os `pids` da caixa resolvem-se contra os itens das edições
    — não há segunda cópia de uma linha de falta.
    """
    cfg = cfg or config.load()
    p = payload(con, cfg)
    c = next((x for x in p["caixas"] if x["id"] == caixa), None)
    if c is None:
        raise ValueError(f"não há caixa {caixa!r}. Há: "
                         f"{', '.join(x['id'] for x in p['caixas']) or '(nenhuma)'}")
    por_pid = {x["printing_id"]: x for d in p["sets"] for g in d["blocks"]
               for x in g["items"]}
    itens = [por_pid[pid] for pid in c["pids"]
             if por_pid[pid]["missing"] > 0]
    return {"caixa": caixa, "label": c["label"], "escopo": c["escopo_label"],
            "in_lists": c["in_lists"], **cardmarket.gerar(itens, com_codigo),
            "items": itens}

"""O DECK PRINCIPAL (2026-09-27): a wantlist dele, e o que acontece quando deixa de o ser.

Palavras do André: *"os decks quero uma coisa / **Deck Principal**: neste caso
LeBlanc / eu coloco + e - se tenho a carta no Deck / **a Colecao e soberana,
nao e para mexer** / todas as cartas do Deck sao Wantlist, as comuns e incomuns
em Foil, / caso eu ainda nao tenha marcado, usa da colecao mas aparece
indicado: / Na colecao aparece que esta a ser usado em X Deck / No deck aparece
algo do genero: X cartas em uso da colecao, ainda falta especifica para o deck
/ Se eu 'desfazer' o deck ou deixar de ser o principal, essas cartas passam a
venda (apenas se valerem pelo menos 0,50 euros)"*.

METADE DISTO JÁ EXISTIA, E NÃO SE CONSTRUIU NADA AO LADO
    As cópias próprias de cada deck são de 2026-09-21 (`proprias.py`): o local
    `proprio:<slug>`, os `+`/`−` em cada carta da página do deck, o não entrar
    na Coleção nem no valor, o servirem primeiro. O `deck:<slug>` que marca uma
    cópia da Coleção usada por um deck é de 2026-09-10, e o «Azir 3» da grelha
    (`decks.uso_por_carta`) é de 2026-09-11. Este módulo é só o que faltava:

      1. QUEM é o deck principal — `decks.principal`, um só, ligado ao
         `decks.montados` (o principal é sempre montado; ver o comentário lá);
      2. A WANTLIST DELE — o que falta para ser AUTO-SUFICIENTE, isto é, o que
         ainda não está no `proprio:<slug>`, com o acabamento que ele pediu;
      3. A DESPROMOÇÃO — o que vai para a Venda quando ele deixa de ser
         principal ou é desfeito.

A WANTLIST: `precisa − próprias`, e o ACABAMENTO manda no preço
    «Todas as cartas do Deck são Wantlist» é o deck inteiro menos o que ele já
    marcou com `+`: uma carta marcada SAI da lista. **Não desconta a Coleção**
    — é esse o ponto do pedido: se ainda não a marcou, o deck usa a da Coleção
    (e as duas indicações dizem-no), mas ela continua na wantlist porque o que
    se quer é o deck ficar com as suas.

    COMUNS E INCOMUNS EM FOIL, rara para cima a normal. O critério é o
    **`foil.no_ambito`** — exactamente as impressões que têm contador de foil
    no tile (base, não sobrenumerada, comum ou incomum, fora o OGS). Não se
    escreveu uma segunda definição de «isto quer-se em foil»: se ele alargar o
    `foil.raridades`, alarga aqui também. Em Riftbound de rara para cima a
    carta *é* a foil, e por isso não há acabamento a escolher.

    O preço de uma linha foil é o `price_foil_cents` (2026-09-26), com o
    fallback para o da normal **contado e dito** (`no_foil_price`) — o mesmo
    que a metade das foils das Faltas faz, e que faz do total um PISO. O texto
    do Cardmarket não leva marca de foil (lá é um filtro por entrada, regra de
    2026-09-01): as linhas foil vêm assinaladas para ele o ligar à mão.

    AS RUNAS FICAM DE FORA, como em todos os decks desde 2026-09-17 à noite
    (`decks.contar_runas: false`): *"nao facas contagem de runas nos decks,
    indica me so quantas sao e eu organizo isso sozinho a mao"*. A página diz
    quantas são.

A COLEÇÃO É SOBERANA — o empréstimo é de APRESENTAÇÃO
    Nada aqui mexe na Coleção. O que o deck usa da Coleção continua a ser o
    `decks.allocate` de sempre, que não move cópia nenhuma: os níveis, a
    percentagem, o denominador, o valor, as Faltas, as wantlists e o A mais dão
    exactamente os mesmos números com e sem deck principal
    (`tests/test_deck_principal.py` fotografa-os). O que muda é o que o ecrã
    DIZ: no tile da Coleção «em uso no deck X», e na página do deck «X cartas
    em uso da Coleção, ainda falta Y específica para o deck».

QUANDO DEIXA DE SER PRINCIPAL OU É DESFEITO: a Venda, a partir de 0,50 €
    As cópias PRÓPRIAS dele (as que ele marcou com `+`) passam a linhas da
    Venda, **só as que valham `decks.venda_minimo_cents`** (50 = 0,50 €). As
    emprestadas da Coleção não vão a lado nenhum — deixam simplesmente de estar
    emprestadas, porque o deck deixou de as pedir.

    TRÊS DECISÕES, tomadas e ditas (não vieram dele):

      (a) O PREÇO QUE DECIDE é o mesmo que a Venda mostra para aquela cópia —
          o Trend do Cardmarket se ele já o meteu, senão o do CardTrader — e
          para uma cópia que o deck queria em FOIL é o preço de foil
          (`venda.preco_de_referencia`, que é uma função só e é a que a linha
          da Venda mostra em `preco_criterio`). Senão o número no ecrã não
          batia com o critério que a pôs lá. Uma cópia SEM preço nenhum não
          chega ao mínimo e fica.
      (b) AS DE MENOS DE 0,50 € NÃO DESAPARECEM: continuam cópias próprias
          daquele deck, fora da Coleção e do valor, e a página diz quantas são
          e quanto valem ao todo (`proprias_por_valor`, que responde antes e
          depois — é com ela que ele vê o que vai acontecer antes de carregar).
      (c) ENTRAR NA VENDA NÃO É VENDER. A Venda é uma área de marcação
          (`sale_lines`) que não mexe em número nenhum; quem baixa cópias é o
          botão separado «marcar como vendidas». Por isso **nada sai do
          `proprio:<slug>`** com a despromoção: a cópia fica onde está e ganha
          uma linha marcada `deck:<slug>`, que a página mostra à parte e se
          tira de uma vez (`venda.limpar(origem=...)`).
"""

from __future__ import annotations

import sqlite3

from . import cardmarket, config, decks, foil, locais, metrics, venda

# Como se escreve a origem de uma linha da Venda que veio de um deck.
ORIGEM = "deck:"


def origem_de(slug: str) -> str:
    return f"{ORIGEM}{slug}"


# ---------------------------------------------------------------------------
# Quem é o deck principal
# ---------------------------------------------------------------------------


def estado(con: sqlite3.Connection, cfg: dict | None = None) -> dict:
    """`{nome, slug, name, nao_encontrado, montado, minimo_cents}`.

    `slug` a `None` quer dizer que não há deck principal — a chave não está
    escrita, ou o nome que lá está não casa com deck nenhum.
    """
    cfg = cfg or config.load()
    e = decks.principal_estado(con, cfg)
    return {**e, "montado": bool(e["slug"]),
            "minimo_cents": decks.venda_minimo_cents(cfg)}


def slug(con: sqlite3.Connection, cfg: dict | None = None) -> str | None:
    return decks.principal_slug(con, cfg or config.load())


def _deck_id(con: sqlite3.Connection, s: str) -> int:
    row = next((r for r in decks.deck_rows(con) if r["name"] == s), None)
    if row is None:
        raise decks.DeckDesconhecido(f"não há deck chamado {s!r}")
    return row["deck_id"]


# ---------------------------------------------------------------------------
# A wantlist do deck principal
# ---------------------------------------------------------------------------


def _linhas_do_catalogo(con: sqlite3.Connection, ids: set[str]) -> dict[str, sqlite3.Row]:
    if not ids:
        return {}
    ph = ",".join("?" * len(ids))
    return {r["printing_id"]: r for r in con.execute(
        f"SELECT * FROM catalog.printings WHERE printing_id IN ({ph})", tuple(ids))}


def itens(con: sqlite3.Connection, s: str, cfg: dict | None = None,
          alloc: dict | None = None) -> list[dict]:
    """A wantlist de UM deck: o que lhe falta para ser auto-suficiente.

    Uma linha por carta, na impressão em que se compra (`Versoes.compra` — a
    base mais barata). `missing = precisa − próprias`; uma carta toda marcada
    não aparece. As runas não entram (ver o topo).
    """
    cfg = cfg or config.load()
    did = _deck_id(con, s)
    fora = decks.cartas_nao_contadas(con, cfg)
    need = decks._need(con, did, fora)
    alloc = (alloc or decks.allocate(con))[did]
    versoes = decks.versoes_dos_decks(con, cfg)
    nomes = {r["card_key"]: r["name"] for r in con.execute(
        "SELECT card_key, name FROM catalog.cards")}
    mercado = cardmarket.versoes(con)
    precos = metrics.prices_map(con)
    precos_foil = metrics.precos_de_foil_map(con)

    compra = {ck: versoes.compra(ck) for ck in need}
    linhas = _linhas_do_catalogo(con, {p for p in compra.values() if p})

    out: list[dict] = []
    for ck, qty in need.items():
        falta = qty - alloc["proprias"].get(ck, 0)
        if falta <= 0:
            continue
        pid = compra.get(ck)
        r = linhas.get(pid) if pid else None
        # O ACABAMENTO: comuns e incomuns em foil, rara para cima a normal.
        # O critério é o do contador de foil do tile — uma resposta só.
        e_foil = bool(r is not None and foil.no_ambito(r, cfg))
        if e_foil:
            pf = precos_foil.get(pid)
            preco, de_foil = (pf, True) if pf is not None else (precos.get(pid), False)
        else:
            preco, de_foil = precos.get(pid), False
        mkt = mercado.get(pid) or {}
        out.append({
            "card_key": ck, "name": nomes.get(ck, ck),
            "printing_id": pid,
            "code": r["public_code"] if r is not None else None,
            "set": r["set_id"] if r is not None else None,
            "set_name": config.set_name(r["set_id"]) if r is not None else None,
            "cn": r["collector_number"] if r is not None else 0,
            "rarity": (r["base_rarity"] or r["rarity"]) if r is not None else None,
            "landscape": (r["orientation"] or "").lower() == "landscape"
                         if r is not None else False,
            "img": f"img/{pid}.webp" if pid else None,
            "cdn": (r["image_medium"] or r["image_large"] or r["image_url"])
                   if r is not None else None,
            "wanted": qty,
            "proprias": alloc["proprias"].get(ck, 0),
            # Quantas vêm emprestadas da Coleção AGORA — é informação: a linha
            # está na wantlist na mesma, porque o deck há-de ter as suas.
            "na_colecao": alloc["na_colecao"].get(ck, 0),
            "missing": falta,
            "foil": e_foil,
            "price": preco, "price_is_foil": de_foil,
            "total": (preco or 0) * falta,
            # Para o gerador do Cardmarket (o mesmo de sempre). `foil_only`
            # marca as linhas onde ele tem de ligar o filtro Foil à mão.
            "market_name": mkt.get("name"), "market_set": mkt.get("set"),
            "v": mkt.get("v"), "n_versions": mkt.get("n"),
            "foil_only": e_foil or bool(mkt.get("foil_only")),
        })
    out.sort(key=lambda x: (config.set_order(x["set"] or ""), x["set"] or "", x["cn"]))
    return out


def wantlist(con: sqlite3.Connection, cfg: dict | None = None,
             com_codigo: bool = False, s: str | None = None,
             alloc: dict | None = None) -> dict:
    """A wantlist do deck principal, pronta para o ecrã e para a CLI.

    Sem deck principal devolve-se a lista vazia com `slug: None` — não é erro,
    é o estado de quem ainda não escolheu.
    """
    cfg = cfg or config.load()
    e = estado(con, cfg)
    alvo = s or e["slug"]
    if not alvo:
        return {**e, "items": [], "totals": {"cards": 0, "copies": 0, "cents": 0,
                                             "foil_cards": 0, "foil_copies": 0,
                                             "no_foil_price": 0},
                "wantlist": {"lines": 0, "copies": 0, "cents": 0, "foil": 0, "text": ""},
                "runas": {"copies": 0, "cards": 0}}
    lista = itens(con, alvo, cfg, alloc)
    w = cardmarket.gerar(lista, com_codigo)
    did = _deck_id(con, alvo)
    fora = decks.cartas_nao_contadas(con, cfg)
    runas = [r for r in con.execute(
        "SELECT card_key, SUM(qty) AS q FROM deck_cards WHERE deck_id = ? "
        "GROUP BY card_key", (did,)) if r["card_key"] in fora]
    return {
        **e, "slug": alvo,
        "items": lista,
        "totals": {
            "cards": len(lista),
            "copies": sum(x["missing"] for x in lista),
            "cents": sum(x["total"] for x in lista),
            "foil_cards": sum(1 for x in lista if x["foil"]),
            "foil_copies": sum(x["missing"] for x in lista if x["foil"]),
            # As linhas foil que contam ao preço da NORMAL por não haver oferta
            # foil no CardTrader — o fallback que faz do total um piso.
            "no_foil_price": sum(1 for x in lista
                                 if x["foil"] and x["price"] is not None
                                 and not x["price_is_foil"]),
        },
        "wantlist": {"lines": w["lines"], "copies": w["copies"], "cents": w["cents"],
                     "foil": len(w["foil"]), "text": w["text"]},
        # As runas que a lista pede e que não se contam — ditas, nunca apagadas.
        "runas": {"copies": sum(r["q"] for r in runas), "cards": len(runas)},
    }


# ---------------------------------------------------------------------------
# As cópias próprias, e o que delas vai para a Venda
# ---------------------------------------------------------------------------


def proprias_por_valor(con: sqlite3.Connection, s: str,
                       cfg: dict | None = None) -> dict:
    """As cópias próprias de um deck, partidas pelo critério dos 0,50 €.

    `acima` são as que iriam para a Venda se ele deixasse de ser principal;
    `abaixo` as que FICAM próprias (decisão (b) do topo) — e são estas que a
    página conta e soma, para ele saber o que sobra.

    O preço é o `venda.preco_de_referencia`: o Trend dele se houver, senão o do
    CardTrader, e o da FOIL quando a carta é das que o deck quer em foil. Uma
    cópia sem preço nenhum fica em `abaixo` — não se manda vender o que não se
    sabe quanto vale.
    """
    cfg = cfg or config.load()
    minimo = decks.venda_minimo_cents(cfg)
    stock = locais.proprias_de(con, s)
    linhas = _linhas_do_catalogo(con, set(stock))
    tr = venda.trends(con)
    precos = metrics.prices_map(con)
    precos_foil = metrics.precos_de_foil_map(con)
    acima: list[dict] = []
    abaixo: list[dict] = []
    for pid, qty in sorted(stock.items()):
        if qty <= 0:
            continue
        r = linhas.get(pid)
        e_foil = bool(r is not None and foil.no_ambito(r, cfg))
        p = venda.preco_de_referencia(pid, foil=e_foil, tr=tr, precos=precos,
                                      precos_foil=precos_foil)
        item = {"printing_id": pid, "qty": qty,
                "name": r["name"] if r is not None else pid,
                "code": r["public_code"] if r is not None else None,
                "set": r["set_id"] if r is not None else None,
                "foil": e_foil, "cents": p["cents"], "fonte": p["fonte"],
                "total": (p["cents"] or 0) * qty}
        (acima if (p["cents"] or 0) >= minimo and p["cents"] is not None
         else abaixo).append(item)
    resumo = lambda lst: {  # noqa: E731
        "printings": len(lst), "copies": sum(x["qty"] for x in lst),
        "cents": sum(x["total"] for x in lst)}
    return {"minimo_cents": minimo, "acima": acima, "abaixo": abaixo,
            "totais": {"acima": resumo(acima), "abaixo": resumo(abaixo),
                       "todas": resumo(acima + abaixo)}}


def despromover(con: sqlite3.Connection, s: str, cfg: dict | None = None,
                source: str = "web") -> dict:
    """As cópias próprias de `s` que valham o mínimo passam a linhas da Venda.

    **Não move nada e não vende nada** (decisão (c) do topo): escreve linhas na
    `sale_lines` com `origem = deck:<slug>` e mais nada. As cópias continuam no
    `proprio:<slug>`, fora da Coleção e do valor, como estavam; as de menos de
    0,50 € nem linha ganham e a página di-lo.

    É idempotente no que interessa: chamar duas vezes some as cópias outra vez
    à mesma linha, por isso quem chama chama uma vez — as portas são o
    `definir` e o `montar`.
    """
    cfg = cfg or config.load()
    p = proprias_por_valor(con, s, cfg)
    origem = origem_de(s)
    for x in p["acima"]:
        venda.juntar(con, x["printing_id"], x["qty"], source=source, origem=origem)
    return {"slug": s, "origem": origem, **p,
            "para_a_venda": p["totais"]["acima"], "ficam": p["totais"]["abaixo"]}


# ---------------------------------------------------------------------------
# Escolher (e desmontar) o deck principal — as duas portas
# ---------------------------------------------------------------------------


def definir(con: sqlite3.Connection, s: str | None, cfg: dict | None = None,
            source: str = "web") -> dict:
    """Escolhe o deck principal (ou limpa, com `None`).

    O que SAI é despromovido: as cópias próprias dele que valham o mínimo vão
    para a Venda. Escolher o MESMO deck outra vez não faz nada — senão um
    clique repetido somava as cópias à Venda duas vezes.
    """
    cfg = cfg or config.load()
    antigo = decks.principal_slug(con, cfg)
    if antigo == s:
        return {"estado": estado(con, cfg), "despromovido": None, "movimento": None}
    decks.escrever_principal(con, s, cfg)
    cfg = config.load()
    mov = despromover(con, antigo, cfg, source=source) if antigo else None
    return {"estado": estado(con, cfg), "despromovido": antigo, "movimento": mov}


def montar(con: sqlite3.Connection, s: str, ligar: bool,
           cfg: dict | None = None, source: str = "web") -> dict:
    """Monta ou desmonta um deck — a porta do botão e da CLI.

    Desmontar o principal DESPROMOVE-O (o `decks.alternar_montado` limpa a
    chave) e, por isso, manda as cópias próprias dele que valham o mínimo para
    a Venda: é o *"se eu 'desfazer' o deck"* do pedido.
    """
    cfg = cfg or config.load()
    est = decks.alternar_montado(con, s, ligar, cfg)
    mov = None
    if est.get("despromovido"):
        mov = despromover(con, est["despromovido"], config.load(), source=source)
    return {"montados": est["montados"], "desmontados": est["desmontados"],
            "principal": estado(con, config.load()),
            "despromovido": est.get("despromovido"), "movimento": mov}


# ---------------------------------------------------------------------------
# Payload
# ---------------------------------------------------------------------------


def do_deck(con: sqlite3.Connection, s: str, alloc: dict | None = None,
            cfg: dict | None = None) -> dict:
    """O bloco que a página de um deck leva (`deck_payload["principal"]`).

    Vai em TODOS os decks, não só no principal: `e_principal` diz qual é, e o
    resto — as duas indicações e o que aconteceria à Venda — vale para
    qualquer um, que é o que lhe deixa ver o que vai acontecer ANTES de mudar.
    """
    cfg = cfg or config.load()
    e = estado(con, cfg)
    did = _deck_id(con, s)
    alloc = alloc or decks.allocate(con)
    a = alloc[did]
    w = wantlist(con, cfg, s=s, alloc=alloc)
    return {
        "e_principal": e["slug"] == s,
        "slug": e["slug"], "name": e["name"],
        # AS DUAS INDICAÇÕES (o pedido): quantas cópias vêm emprestadas da
        # Coleção e quanto ainda falta comprar só para este deck.
        "em_uso_da_colecao": sum(a["na_colecao"].values()),
        "cartas_da_colecao": sum(1 for n in a["na_colecao"].values() if n),
        "proprias": sum(a["proprias"].values()),
        "falta_proprias": w["totals"]["copies"],
        "falta_cartas": w["totals"]["cards"],
        "falta_cents": w["totals"]["cents"],
        "wantlist": w,
        # O que iria para a Venda e o que ficaria, se deixasse de ser principal.
        "venda": proprias_por_valor(con, s, cfg),
    }


def payload(con: sqlite3.Connection, cfg: dict | None = None,
            editable: bool = True) -> dict:
    cfg = cfg or config.load()
    w = wantlist(con, cfg)
    return {"editable": editable, **w,
            "venda": (proprias_por_valor(con, w["slug"], cfg) if w["slug"] else None)}

"""«O que vender»: as comuns e incomuns mais caras e as de oferta mais apertada.

Pergunta do André (2026-09-10): *"se puderes, vê no Cardmarket e CardTrader
quais as comuns e incomuns que costumam vender-se mais, e quais as mais caras,
para eu saber o que vender"*.

O QUE EXISTE, E O QUE NÃO EXISTE
    **Volume de vendas não existe em fonte pública nenhuma.** Confirmado a
    2026-09-10, da máquina dele: `cardmarket.com` responde **403** a pedidos
    automáticos (é o que o CLAUDE.md já dizia) e a API pública deles,
    `api.cardmarket.com/ws/v2.0`, responde **410 Gone**. O que resta ali seria
    uma app registada com chave própria — e a regra dele é *só a subscrição*,
    nada de chaves novas. Por isso **não há nada do Cardmarket nesta página**.

    Fica o CardTrader (`game_id` 22, confirmado hoje), que é a fonte de preços
    do riftvault desde 2026-08-31. O que ele dá por impressão é o lado da
    OFERTA: o preço mínimo pedido, quantos anúncios há, quantos vendedores
    distintos os põem e quantas cópias estão à venda ao todo.

    **Oferta não é procura.** Uma comum com trezentos anúncios a 11 cêntimos
    tem muita oferta; isso não diz que se venda — diz o contrário. Por isso
    esta página **não tem uma lista de "as que se vendem mais"**: tem duas
    coisas que se medem mesmo, e diz o que cada uma mede.

AS DUAS LISTAS
    **As mais caras** — preço de hoje, e só isso. É a metade da pergunta que
    tem resposta directa.

    **As mais procuradas** — pelo melhor sinal que há, que é o **preço relativo
    ao saldo da raridade**: quantas vezes acima da mediana da raridade é que o
    mercado está a pedir por ela. Uma comum a 4,91 € num mar de comuns a 11
    cêntimos é gente a pagar por ela, e é a coisa mais próxima de procura que
    se consegue medir sem volume de vendas. A subida do preço na janela entra
    como reforço (ver `procura`), e as três contagens da oferta aparecem ao
    lado como **liquidez** — não entram no valor, de propósito: mais oferta não
    é mais procura, e somá-la era inventar.

O QUE ELE TEM: O EXCEDENTE, PELA REGRA QUE JÁ EXISTIA
    A lista «O que vender» é o cruzamento das duas com o que ele tem a mais.
    **Excedente é o que nem a Coleção nem os decks pedem** — a conta do
    `venda.excedente`, a mesma da secção Venda. A única diferença é o âmbito:
    aqui a SEQUÊNCIA do master set entra também (`incluir_master=True`), porque
    as comuns vivem quase todas nela e uma quinta cópia de uma Unit de playset
    3 não faz falta a ninguém. Não há critério novo de excedente.

    **Nada sai da base**, como na Venda: isto é uma sugestão.

A RARIDADE É EXIGIDA NAS DUAS COLUNAS
    `rarity` (a impressa) **e** `base_rarity` (a do grupo) têm as duas de ser
    comum ou incomum. As seis runas de arte alternativa do OGN são o caso que
    isto apanha: a base é `common` mas a impressão é `showcase`, e o mercado
    paga-lhes o preço de showcase. Uma lista de comuns com tratamentos
    showcase lá dentro respondia a outra pergunta.
"""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from . import a_subir, cardmarket, config, metrics, venda

DEFAULTS: dict = {
    "raridades": ["common", "uncommon"],
    # Quantas linhas cada uma das duas listas mostra.
    "topo": 20,
    "janela_dias": 30,
    # A lista «Guardar»: excedente que hoje vale pouco mas está a subir. O
    # limiar de subida é o mesmo do «A subir» (10%), e o tecto de preço serve
    # para não repetir aqui o que já está na lista das caras.
    "guardar_subida_pct": 10.0,
    "guardar_ate_cents": 200,
}


def opcoes(cfg: dict | None = None) -> dict:
    cfg = cfg or config.load()
    out = dict(DEFAULTS)
    out.update({k: v for k, v in (cfg.get("comuns") or {}).items()
                if not k.startswith("_")})
    return out


def raridades(cfg: dict | None = None) -> tuple[str, ...]:
    return tuple(opcoes(cfg)["raridades"])


def e_comum(printing, cfg: dict | None = None) -> bool:
    """Comum ou incomum nas DUAS raridades — a impressa e a da base.

    Ver o cabeçalho: exigir as duas é o que impede as runas de arte alternativa
    do OGN (base `common`, impressa `showcase`) de entrarem numa lista que é
    sobre cartas de saldo.
    """
    rs = raridades(cfg)
    return ((metrics.campo(printing, "rarity") or "") in rs
            and (metrics.campo(printing, "base_rarity") or "") in rs)


# ---------------------------------------------------------------------------
# Preço, oferta e o sinal de procura
# ---------------------------------------------------------------------------


def medianas(con: sqlite3.Connection) -> dict[str, int]:
    """Preço mediano por raridade — o "saldo" contra o qual se mede o resto.

    É a `a_subir.medianas_por_raridade`, pela mesma função: uma segunda conta
    da mesma mediana era uma segunda resposta à mesma pergunta.
    """
    return a_subir.medianas_por_raridade(con)


def procura(preco_cents: int, mediana_cents: int, pct: float | None,
            pct_oferta: float | None = None) -> float:
    """O sinal de procura: três factores, nenhum deles vendas.

        procura = (preço ÷ mediana da raridade)
                  × (1 + max(0, Δ% do preço) ÷ 100)
                  × (1 + max(0, queda % dos anúncios) ÷ 100)

    **O que mede:**

      1. **Preço relativo** — quantas vezes acima do saldo da raridade é que o
         mercado pede por ela. Uma comum a 4,91 € num mar de comuns a 11
         cêntimos é gente a pagar por ela.
      2. **O preço a subir** na janela, do `price_history`.
      3. **Os anúncios a desaparecer** na janela, do `listings_history`. É o
         único dos três que fala de movimento: oferta a encolher com o preço a
         subir é gente a comprar. **Vale zero até haver dois dias de
         histórico** — a tabela começou a 2026-09-10, por isso hoje este factor
         está inerte e o valor é o dos dois primeiros.

    **O que NÃO mede:** vendas. Ninguém publica volume (ver o cabeçalho). Uma
    carta pode estar cara por ser difícil de aparecer e não por ser procurada, e
    isto não distingue as duas.

    Os dois últimos factores nunca descem o valor (`max(0, ...)`): uma carta a
    ficar mais barata, ou com mais anúncios, não é *menos* procurada que uma
    parada — é só mais barata, e o primeiro factor já conta isso.

    ATENÇÃO À LEITURA DE HOJE (2026-09-10): as medianas das duas raridades são
    as duas **11 cêntimos**, o mínimo do CardTrader. Com o mesmo denominador
    para todas, o preço relativo É o preço, e esta lista sai quase igual à das
    caras. Não é um erro de contagem: é o que o mercado das comuns de Riftbound
    tem para dizer hoje.
    """
    if mediana_cents <= 0:
        return 0.0
    return ((preco_cents / mediana_cents)
            * (1 + max(0.0, pct or 0.0) / 100)
            * (1 + max(0.0, -(pct_oferta or 0.0)) / 100))


def _series(con: sqlite3.Connection) -> dict[str, list[tuple[str, int]]]:
    series: dict[str, list[tuple[str, int]]] = {}
    for r in con.execute(
        "SELECT printing_id, day, price_cents FROM prices.price_history "
        "ORDER BY printing_id, day"
    ):
        series.setdefault(r["printing_id"], []).append((r["day"], r["price_cents"]))
    return series


def _series_oferta(con: sqlite3.Connection) -> dict[str, list[tuple[str, int]]]:
    """O mesmo, para o número de anúncios. Vazio até o `sync` correr duas vezes."""
    series: dict[str, list[tuple[str, int]]] = {}
    for r in con.execute(
        "SELECT printing_id, day, n_listings FROM prices.listings_history "
        "ORDER BY printing_id, day"
    ):
        series.setdefault(r["printing_id"], []).append((r["day"], r["n_listings"]))
    return series


# ---------------------------------------------------------------------------
# O universo: todas as comuns e incomuns do catálogo, com preço e oferta
# ---------------------------------------------------------------------------


def universo(con: sqlite3.Connection, cfg: dict | None = None,
             hoje: date | None = None) -> list[dict]:
    """Uma linha por impressão comum/incomum com preço, com tudo o que se sabe dela.

    Inclui as que ele não tem: a pergunta dele é sobre o mercado ("quais as
    comuns e incomuns mais caras"), não sobre a caixa. O `have` e o `surplus`
    dizem depois quais é que lhe tocam.
    """
    cfg = cfg or config.load()
    o = opcoes(cfg)
    hoje = hoje or date.today()
    limite = (hoje - timedelta(days=int(o["janela_dias"]))).isoformat()

    meds = medianas(con)
    series = _series(con)
    series_of = _series_oferta(con)
    mercado = cardmarket.versoes(con)
    tenho = {r["printing_id"]: r["qty"] for r in
             con.execute("SELECT printing_id, qty FROM copies WHERE qty > 0")}
    sobras = {x["printing_id"]: x for x in
              venda.excedente(con, cfg, incluir_master=True)}

    itens: list[dict] = []
    for r in con.execute(
        "SELECT p.printing_id, p.set_id, p.collector_number, p.public_code, p.name, "
        "       p.variant_kind, p.variant_label, p.rarity, p.base_rarity, p.type, "
        "       p.is_token, p.orientation, p.image_medium, p.image_large, p.image_url, "
        "       pl.price_cents, pl.from_foil, pl.n_listings, pl.n_sellers, pl.n_copies "
        "FROM catalog.printings p "
        "JOIN catalog.price_latest pl ON pl.printing_id = p.printing_id "
        "WHERE pl.price_cents IS NOT NULL"
    ):
        if not e_comum(r, cfg):
            continue
        preco = r["price_cents"]
        rar = r["base_rarity"] or "?"

        pct, desde, cobre = None, None, False
        serie = series.get(r["printing_id"])
        if serie:
            d0, antes, cobre = a_subir.ponto(serie, limite)
            if antes > 0:
                pct, desde = round((preco - antes) / antes * 100, 1), d0

        # A tendência dos anúncios, pelo mesmo `ponto()` do preço: o valor em
        # vigor no início da janela. Fica a None enquanto o histórico da oferta
        # tiver um dia só, que é o caso desde que a tabela nasceu — e a página
        # diz o número de dias, em vez de mostrar um zero que parece medido.
        pct_of = None
        serie_of = series_of.get(r["printing_id"])
        if serie_of and len(serie_of) > 1:
            _, antes_of, _ = a_subir.ponto(serie_of, limite)
            if antes_of > 0:
                pct_of = round((r["n_listings"] - antes_of) / antes_of * 100, 1)

        sobra = sobras.get(r["printing_id"]) or {}
        mkt = mercado.get(r["printing_id"]) or {}
        mediana = meds.get(rar) or preco
        itens.append({
            "printing_id": r["printing_id"],
            "name": r["name"], "code": r["public_code"],
            "set": r["set_id"], "set_name": config.set_name(r["set_id"]),
            "cn": r["collector_number"],
            "kind": r["variant_kind"], "label": r["variant_label"],
            "rarity": rar,
            "landscape": (r["orientation"] or "").lower() == "landscape",
            "img": f"img/{r['printing_id']}.webp",
            "cdn": r["image_medium"] or r["image_large"] or r["image_url"],
            "price": preco,
            "from_foil": bool(r["from_foil"]),
            # As três medidas da OFERTA. Ficam à parte do `demand` de propósito.
            "n_listings": r["n_listings"], "n_sellers": r["n_sellers"],
            "n_copies": r["n_copies"],
            "median": mediana,
            "rel": round(preco / mediana, 1) if mediana else None,
            "pct": pct, "since": desde, "full_window": cobre,
            # Negativo = há menos anúncios do que havia. É esse o sinal bom.
            "pct_listings": pct_of,
            "demand": round(procura(preco, mediana, pct, pct_of), 1),
            # O que está fora da Coleção (sobrenumeradas, tokens, ...) diz
            # porquê: é o caso dos Poros do UNL, que são comuns de raridade mas
            # reimpressões de topo de set — ver a ARMADILHA 2 do CLAUDE.md.
            "outside": metrics.fora_da_colecao(r, cfg),
            "have": tenho.get(r["printing_id"], 0),
            # `qty` é o excedente, e chama-se `qty` porque é o que o gerador do
            # Cardmarket lê nas listas de venda (ver `cardmarket.quantidade`).
            "qty": max(0, sobra.get("qty", 0)),
            "used": sobra.get("used", 0),
            "target": sobra.get("target", 0),
            "in_decks": sobra.get("in_decks", []),
            "total": preco * max(0, sobra.get("qty", 0)),
            "market_name": mkt.get("name") if mkt.get("name") != r["name"] else None,
            "market_set": mkt.get("set"),
            "v": mkt.get("v"), "n_versions": mkt.get("n", 1),
            "foil_only": bool(mkt.get("foil_only")),
        })
    return itens


# ---------------------------------------------------------------------------
# As listas
# ---------------------------------------------------------------------------


def caras(itens: list[dict], topo: int | None = None) -> list[dict]:
    """As mais caras: preço de hoje, desempate pelo sinal de procura."""
    ordenado = sorted(itens, key=lambda x: (-x["price"], -x["demand"], x["name"]))
    return ordenado[:topo] if topo else ordenado


def procuradas(itens: list[dict], topo: int | None = None) -> list[dict]:
    """As de sinal de procura mais alto — ver `procura` para o que isso mede."""
    ordenado = sorted(itens, key=lambda x: (-x["demand"], -x["price"], x["name"]))
    return ordenado[:topo] if topo else ordenado


def vender(itens: list[dict]) -> list[dict]:
    """O que ele tem a mais, por euros a receber.

    O cruzamento que ele pediu: excedente ∩ (as caras ∪ as procuradas). Sai
    ordenado pelo **total** — preço × cópias a mais — porque a pergunta é
    quanto é que rende, não qual é a carta mais cara.
    """
    return sorted([x for x in itens if x["qty"] > 0],
                  key=lambda x: (-x["total"], -x["price"], x["set"], x["cn"]))


def guardar(itens: list[dict], cfg: dict | None = None) -> list[dict]:
    """Excedente que hoje vale pouco mas está a subir — não vender já.

    O outro lado da mesma lista: o `guardar_ate_cents` tira as que já aparecem
    nas caras, e o `guardar_subida_pct` é o mesmo limiar do «A subir».
    """
    o = opcoes(cfg)
    tecto, minimo = int(o["guardar_ate_cents"]), float(o["guardar_subida_pct"])
    fica = [x for x in itens
            if x["qty"] > 0 and x["price"] <= tecto
            and x["pct"] is not None and x["pct"] >= minimo]
    return sorted(fica, key=lambda x: (-(x["pct"] or 0), -x["total"], x["name"]))


# ---------------------------------------------------------------------------
# O payload
# ---------------------------------------------------------------------------


def analise(con: sqlite3.Connection, cfg: dict | None = None,
            hoje: date | None = None) -> dict:
    """A secção inteira: as duas listas, o que vender e o que guardar."""
    cfg = cfg or config.load()
    o = opcoes(cfg)
    topo = int(o["topo"])
    itens = universo(con, cfg, hoje)

    a_vender = vender(itens)
    a_guardar = guardar(itens, cfg)

    dias = [r["day"] for r in con.execute(
        "SELECT DISTINCT day FROM prices.price_history ORDER BY day")]
    dias_oferta = [r["day"] for r in con.execute(
        "SELECT DISTINCT day FROM prices.listings_history ORDER BY day")]
    dia = con.execute("SELECT MAX(day) AS d FROM catalog.price_latest").fetchone()

    # Quantas comuns/incomuns há ao todo, com e sem preço — a diferença entre
    # "estas são as mais caras" e "estas são as mais caras das que têm oferta".
    total = sem_preco = 0
    for r in con.execute(
        "SELECT p.rarity, p.base_rarity, pl.price_cents FROM catalog.printings p "
        "LEFT JOIN catalog.price_latest pl ON pl.printing_id = p.printing_id"
    ):
        if not e_comum(r, cfg):
            continue
        total += 1
        if r["price_cents"] is None:
            sem_preco += 1

    return {
        "generated_at": metrics._now(),
        "rarities": list(raridades(cfg)),
        "day": dia["d"] if dia else None,
        "window_days": int(o["janela_dias"]),
        "top": topo,
        "universe": {"printings": total, "priced": total - sem_preco,
                     "no_price": sem_preco},
        "medians": medianas(con),
        "days_recorded": len(dias), "first_day": dias[0] if dias else None,
        # O histórico da oferta começou a 2026-09-10 e com um dia não dá para
        # tirar tendência nenhuma. A página diz o número em vez de fingir.
        "listings_days": len(dias_oferta),
        "listings_first": dias_oferta[0] if dias_oferta else None,
        # O que é que cada fonte deu, e o que não deu. Fica no payload para a
        # página o poder dizer, em vez de o utilizador ter de adivinhar.
        "sources": {
            "cardtrader": {"ok": True, "gives": ["preço mínimo", "anúncios",
                                                 "vendedores", "cópias à venda"]},
            "cardmarket": {"ok": False, "why": "403 no site e 410 na API pública "
                                               "(confirmado a 2026-09-10)"},
            "sales_volume": {"ok": False, "why": "nenhuma das duas publica volume "
                                                 "de vendas"},
        },
        "by_price": caras(itens, topo),
        "by_demand": procuradas(itens, topo),
        "sell": {
            # O `gerar` já traz `copies` e `cents` (as mesmas somas, pelo mesmo
            # gerador das outras listas); vem primeiro para o `printings` e os
            # `items` ficarem por cima sem ambiguidade.
            **cardmarket.gerar(a_vender),
            "printings": len(a_vender),
            "items": a_vender,
        },
        "keep": {
            "printings": len(a_guardar),
            "copies": sum(x["qty"] for x in a_guardar),
            "cents": sum(x["total"] for x in a_guardar),
            "items": a_guardar,
        },
    }

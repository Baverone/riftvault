"""Preços via CardTrader (API v2). Validado contra a API real a 2026-08-31.

A RiftScribe não tem preços nenhuns — procurado em toda a spec, não existe
campo nenhum de preço. O CardTrader tem Riftbound completo (`game_id` 22) e é
a mesma fonte já usada no mtgvault, com o mesmo token.

A PONTE
    O `collector_number` dos blueprints do CardTrader já traz o sufixo da
    variante: '007' base, '007a' arte alternativa, '299s' signature. Isso casa
    diretamente com (set_id, collector_number, variant) da RiftScribe, sem
    precisar de comparar nomes — o que é bom, porque os nomes são diferentes
    ("Jinx - Loose Cannon" no CardTrader, "Loose Cannon" na RiftScribe).

    Medido: 1179 das 1180 impressões casam (99,9%), sem ambiguidades. A única
    que falha é `VEN-T04 "Recruit (NX)"`, um token que o CardTrader não lista.
    O CardTrader tem ainda impressões que a RiftScribe ainda não tem (runas
    promo do SFD/UNL e as signatures do VEN); essas ficam de fora por não
    haver impressão nossa a que se agarrem.

O PREÇO
    Menor preço pedido em Near Mint ou Mint, inglês, sem graded/altered/signed,
    de vendedor que não esteja de férias. Tudo o que o CardTrader devolve para
    Riftbound está em EUR.

    Prefere-se a oferta NÃO foil; só se não houver nenhuma é que se usa a foil
    (fica marcado em `from_foil`). É a escolha conservadora para o preço da
    cópia NORMAL: nunca a inflaciona com um preço de foil.

    E DESDE 2026-09-26 GRAVA-SE TAMBÉM O PREÇO DA FOIL, à parte, em
    `price_foil_cents` — palavras dele: *"podes meter filtro no cardtrader e
    tirar o preco da foil mais barata?, para diferenciar os precos"*. Mesmos
    filtros, só a `riftbound_foil` muda. Uma cópia foil da coleção
    (`copies.qty_foil`) vale esse preço; só quando ele não existe é que cai para
    o da normal, e esse FALLBACK é contado e dito (`valor_dos_foils`). Antes
    disto as foils dele contavam todas ao preço da normal, o que no `data/` real
    era o chão do CardTrader (11 cêntimos) para 254 cópias.

ONDE FICA
    `catalog.price_latest` — preço atual das 1180 impressões. Descartável.
    `price_history` (prices.db) — de TODAS as impressões do catálogo, e só
    quando o preço muda (decisão do André, 2026-09-01: a vista "a subir" é
    sobre o Riftbound inteiro, para apanhar cartas a valorizar antes de
    entrarem num deck dele). Fica no prices.db, à parte do vault.db, para o
    robô do GitHub Actions poder fazer commit sem tocar na coleção.
"""

from __future__ import annotations

import os
import sqlite3
import time
from datetime import date, datetime, timezone

import requests

from . import config, db

CT_BASE = "https://api.cardtrader.com/api/v2"
RIFTBOUND_GAME_ID = 22          # confirmado em /api/v2/games
SINGLES_CATEGORY = 258          # confirmado nos blueprints; o resto é selado

# Condições que contam como carta "boa". Fora disto o preço não é comparável.
OK_CONDITIONS = {"Mint", "Near Mint"}
# A língua das ofertas que contam, quando o config não diz (André, 2026-09-15:
# "apenas cartas versao ingles"). Já era só inglês desde 2026-08-31, escrito
# aqui; passou a ler-se de `precos.linguas` para ficar à vista e mudar sem
# tocar no código. O CardTrader marca cada oferta com `riftbound_language`
# ('en', 'fr', 'zh-CN', ...); a RiftScribe não tem língua por impressão.
LANGUAGE = "en"


def linguas(cfg: dict | None = None) -> frozenset[str]:
    """As línguas cujas ofertas entram no preço (`precos.linguas`)."""
    cfg = cfg or config.load()
    lista = (cfg.get("precos") or {}).get("linguas")
    if lista is None:
        lista = [LANGUAGE]
    if not lista:
        raise ValueError("precos.linguas está vazio — nenhuma oferta entraria no preço")
    return frozenset(str(x) for x in lista)


class CardTraderError(RuntimeError):
    pass


class CardTrader:
    def __init__(self, token: str | None = None):
        # Limpar espaços e BOM: um token colado de um editor, ou passado por
        # pipe do PowerShell, vem com `﻿` à frente — e aí o `requests`
        # rebenta a codificar o header em latin-1, com uma mensagem que não
        # faz lembrar nada disto. Aconteceu no GitHub Actions.
        bruto = token or os.environ.get("CARDTRADER_TOKEN") or ""
        self.token = bruto.strip().lstrip("﻿").strip()
        if not self.token:
            raise CardTraderError(
                "Falta CARDTRADER_TOKEN no ambiente.\n"
                "  Cria um token nas definições do perfil em cardtrader.com e faz:\n"
                '    setx CARDTRADER_TOKEN "o-token"\n'
                "  (abre um terminal novo a seguir)"
            )
        self.s = requests.Session()
        self.s.headers.update({
            "Authorization": f"Bearer {self.token}",
            # SÓ ASCII. Um User-Agent com acentos leva 403 do CardTrader
            # (testado: "colecao" dá 200, "coleção" dá 403).
            "User-Agent": "riftvault/0.1 (personal collection manager)",
        })

    def get(self, path: str, params: dict | None = None):
        url = f"{CT_BASE}{path}"
        try:
            r = self.s.get(url, params=params, timeout=180)
        except requests.RequestException as exc:
            raise CardTraderError(f"falhou o pedido a {url}: {exc}") from exc
        if r.status_code == 401:
            raise CardTraderError("o CARDTRADER_TOKEN foi recusado (401). Gera outro.")
        if r.status_code != 200:
            raise CardTraderError(f"{url} devolveu HTTP {r.status_code}")
        return r.json()

    def expansions(self) -> list[dict]:
        data = self.get("/expansions")
        rows = data.get("array", data) if isinstance(data, dict) else data
        return [x for x in rows if x.get("game_id") == RIFTBOUND_GAME_ID]

    def blueprints(self, expansion_id: int) -> list[dict]:
        data = self.get("/blueprints/export", {"expansion_id": expansion_id})
        return data.get("array", data) if isinstance(data, dict) else data

    def marketplace(self, expansion_id: int) -> dict:
        # Devolve o mercado inteiro da expansão num pedido só (~45 MB no OGN).
        return self.get("/marketplace/products", {"expansion_id": expansion_id})


# ---------------------------------------------------------------------------
# Mapa RiftScribe <-> CardTrader
# ---------------------------------------------------------------------------

# 'star' na RiftScribe é o sufixo 's' no CardTrader.
_SUFFIX = {"": "", "a": "a", "star": "s"}


def _rs_key(collector_number: int, variant: str) -> str:
    """Chave de casamento a partir de uma impressão da RiftScribe."""
    if variant in _SUFFIX:
        return f"{collector_number:03d}{_SUFFIX[variant]}"
    return variant.lower()          # tokens/runas/promos: t04, r01, sp4


def _ct_key(raw) -> str | None:
    """Normaliza o collector_number do CardTrader: '7a' e '007a' dão o mesmo."""
    if raw is None:
        return None
    s = str(raw).strip().lower()
    if not s:
        return None
    digits = ""
    i = 0
    while i < len(s) and s[i].isdigit():
        digits += s[i]
        i += 1
    rest = s[i:].strip()
    if digits:
        return f"{int(digits):03d}{rest}"
    return s


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sync_map(ct: CardTrader | None = None, log=print) -> dict:
    """Constrói `cardtrader_map`. Reconstruível a qualquer momento."""
    ct = ct or CardTrader()
    con = db.catalog_only()

    # As expansões do CardTrader trazem `code` igual ao set_id da RiftScribe,
    # em minúsculas (ogn, ogs, sfd, unl, ven).
    by_code = {(x.get("code") or "").upper(): x for x in ct.expansions()}
    our_sets = [r["set_id"] for r in con.execute("SELECT DISTINCT set_id FROM printings")]

    pairs, missing, sem_exp, so_mercado = [], [], [], []
    for set_id in sorted(our_sets):
        exp = by_code.get(set_id)
        if not exp:
            sem_exp.append(set_id)
            log(f"  ! {set_id} não tem expansão correspondente no CardTrader")
            continue

        # `singles` guarda TUDO; o `index` é só para casar com as nossas
        # impressões. Não se pode deduplicar por número de coleção e ficar por
        # aí: o CardTrader escreve a Calm Rune alternativa do SFD com o mesmo
        # `R02` da base, e a segunda desaparecia — logo a runa que o deck do
        # Ornn quer, por o Legend dele ser do SFD.
        singles, index = [], {}
        for b in ct.blueprints(exp["id"]):
            if b.get("category_id") != SINGLES_CATEGORY:
                continue            # booster boxes, playmats e afins
            cm = b.get("card_market_ids") or []
            info = {"id": b["id"], "name": b.get("name"),
                    "cm": cm[0] if cm else None,
                    "raw_cn": (b.get("fixed_properties") or {}).get("collector_number"),
                    "version": b.get("version"),
                    "image": b.get("image_url")}
            singles.append(info)
            k = _ct_key(info["raw_cn"])
            # A base tem `version` vazio; se houver colisão, é ela que fica.
            if k and (k not in index or not (info["version"] or "")):
                index[k] = info

        rows = con.execute(
            "SELECT printing_id, collector_number, variant, public_code, name "
            "FROM printings WHERE set_id = ?", (set_id,)
        ).fetchall()
        hit, usados = 0, set()
        for r in rows:
            k = _rs_key(r["collector_number"], r["variant"])
            b = index.get(k)
            if b:
                usados.add(b["id"])
                pairs.append((r["printing_id"], b["id"], exp["id"], b["name"],
                              exp.get("name_en") or exp.get("name"), b["cm"], _now()))
                hit += 1
            else:
                missing.append((r["printing_id"], r["public_code"], r["name"]))

        # O que o CardTrader tem e nós não. Vai para `market_only`, fora do
        # catálogo — ver o comentário no catalog_schema.sql.
        for b in singles:
            if b["id"] in usados:
                continue
            so_mercado.append((f"ct-{b['id']}", b["id"], set_id, b["raw_cn"],
                               b["name"], exp.get("name_en") or exp.get("name"),
                               b["version"], b["cm"], b["image"], _now()))
        log(f"  {set_id}: {hit}/{len(rows)} impressões mapeadas")
        time.sleep(0.5)             # a API permite 200/10s; não há pressa

    con.execute("BEGIN")
    con.execute("DELETE FROM cardtrader_map")
    con.execute("DELETE FROM market_only")
    con.executemany(
        "INSERT INTO cardtrader_map (printing_id, blueprint_id, expansion_id, "
        "market_name, market_set, cardmarket_id, mapped_at) VALUES (?,?,?,?,?,?,?)", pairs)
    con.executemany(
        "INSERT INTO market_only (printing_id, blueprint_id, set_id, collector_raw, "
        "market_name, market_set, version, cardmarket_id, image_url, seen_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)", so_mercado)

    # Casar cada uma com a carta lógica: primeiro pelo número de coleção (as
    # signatures do VEN têm base nossa), depois pelo nome.
    con.execute(
        "UPDATE market_only SET card_key = ("
        "  SELECT p.card_key FROM printings p WHERE p.set_id = market_only.set_id "
        "  AND CAST(p.collector_number AS TEXT) = "
        "      CAST(CAST(REPLACE(REPLACE(market_only.collector_raw,'a',''),'s','') AS INTEGER) AS TEXT)"
        "  LIMIT 1) WHERE card_key IS NULL")
    con.execute(
        "UPDATE market_only SET card_key = ("
        "  SELECT c.card_key FROM cards c "
        "  WHERE c.card_key = lower(trim(market_only.market_name)) LIMIT 1)"
        " WHERE card_key IS NULL")
    # Aliases para as market_only, para o `riftvault add SFD-R02a` funcionar
    # como para qualquer outra impressão.
    #
    # O código impresso leva 'a' nas artes alternativas, mas o CardTrader
    # gravou a Calm Rune do SFD como 'R02' e não 'R02a'. Regista-se as duas
    # formas: a que eles têm e a que vem na fatura.
    al = []
    for r in con.execute(
        "SELECT printing_id, set_id, collector_raw, version FROM market_only "
        "WHERE collector_raw IS NOT NULL"
    ):
        base = f"{r['set_id']}-{r['collector_raw']}".lower()
        al.append((base, r["printing_id"]))
        if "alternate art" in (r["version"] or "").lower() and not base.endswith("a"):
            al.append((base + "a", r["printing_id"]))
    con.executemany(
        "INSERT OR IGNORE INTO printing_aliases (alias, printing_id) VALUES (?,?)", al)
    con.execute("COMMIT")
    casadas = con.execute(
        "SELECT COUNT(*) n FROM market_only WHERE card_key IS NOT NULL").fetchone()["n"]
    con.close()
    return {"mapped": len(pairs), "missing": missing, "sets_sem_expansao": sem_exp,
            "market_only": len(so_mercado), "market_only_casadas": casadas}


# ---------------------------------------------------------------------------
# Preços
# ---------------------------------------------------------------------------


def _usable(p: dict, aceites: frozenset[str] | None = None) -> bool:
    h = p.get("properties_hash") or {}
    return (not p.get("graded")
            and not p.get("on_vacation")
            and not h.get("altered")
            and not h.get("signed")
            and h.get("riftbound_language") in (aceites or linguas())
            and h.get("condition") in OK_CONDITIONS
            and p.get("price_currency") == "EUR"
            and (p.get("price_cents") or 0) > 0)


def oferta(products: list[dict], aceites: frozenset[str] | None = None) -> dict:
    """O que o mercado tem desta impressão: preço mínimo e TAMANHO da oferta.

    `aceites` são as línguas que contam (`linguas()` quando não vem): uma
    oferta noutra língua não entra no preço nem nas contagens — ele só compra
    inglês, e um preço de uma carta japonesa não é o preço que ele paga.

    Devolve `cents`, `from_foil`, `foil_cents` e quatro contagens que medem
    coisas diferentes:

      `n_listings` — quantas ofertas utilizáveis há (uma por anúncio).
      `n_sellers`  — quantos vendedores DISTINTOS as põem. Um vendedor com dez
                     cópias são dez listagens e um só vendedor; é este número
                     que diz se a oferta é de muita gente ou de um armazém.
      `n_copies`   — quantas cópias estão à venda ao todo (o `quantity` de cada
                     anúncio somado). É a oferta a sério.
      `n_listings_foil` — dos anúncios utilizáveis, quantos são FOIL.

    O PREÇO DA FOIL, À PARTE (2026-09-26: *"podes meter filtro no cardtrader e
    tirar o preco da foil mais barata?, para diferenciar os precos"*).
    `foil_cents` é o mínimo das ofertas FOIL, com **exactamente os mesmos
    filtros** das normais (o `_usable`: Mint/Near Mint, a língua do config, sem
    graded/signed/altered, vendedor presente, EUR) — só a `riftbound_foil` muda.
    `None` quando não há oferta foil nenhuma.

    A escolha do `cents`/`from_foil` NÃO mexeu com isto, de propósito: a lista
    das foils era deitada fora e agora guarda-se, mas quem decide o preço
    «normal» continua a ser a mesma linha. Uma impressão não pode mudar de preço
    por causa desta coluna nova, e há teste que compara as duas implementações
    sobre o mercado real.

    **Isto é OFERTA, não procura** (André, 2026-09-10: *"quais as comuns e
    incomuns que costumam vender-se mais"*). Nem o CardTrader nem o Cardmarket
    publicam volume de vendas — ver o cabeçalho do `comuns.py`. Guarda-se na
    mesma porque é o mais perto que há: uma carta com trezentas listagens a 11
    cêntimos não se vende, e sabê-lo poupa-lhe o trabalho.

    As contagens seguem o mesmo acabamento que o preço: quando não há oferta
    normal nenhuma e o preço vem da foil, contam-se só as foil. Contar as duas
    dava um número que não corresponde ao preço mostrado.
    """
    aceites = aceites or linguas()
    normal, foil = [], []
    for p in products:
        if not _usable(p, aceites):
            continue
        h = p.get("properties_hash") or {}
        (foil if h.get("riftbound_foil") else normal).append(p)

    # O preço da foil sai da lista das foils, sempre — mesmo quando é ela que
    # dá o preço «normal» (`from_foil`), e aí os dois números são o mesmo: a
    # única oferta que havia era foil. Guardar os dois faz a leitura do valor
    # ficar uniforme (uma cópia foil lê sempre o `price_foil_cents` quando ele
    # existe) em vez de ter de perguntar pelo `from_foil` primeiro.
    foil_cents = min((p["price_cents"] for p in foil), default=None)

    escolhidos, from_foil = (normal, False) if normal else (foil, True)
    if not escolhidos:
        return {"cents": None, "from_foil": False, "foil_cents": None,
                "n_listings": 0, "n_sellers": 0, "n_copies": 0,
                "n_listings_foil": 0}
    vendedores = {(p.get("user") or {}).get("id") for p in escolhidos}
    vendedores.discard(None)
    return {
        "cents": min(p["price_cents"] for p in escolhidos),
        "from_foil": from_foil,
        "foil_cents": foil_cents,
        "n_listings_foil": len(foil),
        # Quando o preço vem da foil, as normais não existem — mas quando vem
        # das normais, o total de anúncios inclui as foil, como sempre incluiu.
        "n_listings": len(normal) + len(foil) if normal else len(foil),
        "n_sellers": len(vendedores),
        "n_copies": sum(int(p.get("quantity") or 1) for p in escolhidos),
    }


def lowest(products: list[dict]) -> tuple[int | None, bool, int]:
    """(preço em cêntimos, veio_de_foil, nº de ofertas utilizáveis).

    A forma antiga do `oferta()`, mantida para quem só quer o preço.
    """
    o = oferta(products)
    return o["cents"], o["from_foil"], o["n_listings"]


def sync_prices(ct: CardTrader | None = None, log=print) -> dict:
    """Atualiza `price_latest` (todas) e `price_history` (só as que tenho)."""
    ct = ct or CardTrader()
    con = db.connect()
    today = date.today().isoformat()

    bp_to_printings: dict[int, list[str]] = {}
    exps: dict[int, set[int]] = {}
    for r in con.execute("SELECT printing_id, blueprint_id, expansion_id FROM catalog.cardtrader_map"):
        bp_to_printings.setdefault(r["blueprint_id"], []).append(r["printing_id"])
        exps.setdefault(r["expansion_id"], set()).add(r["blueprint_id"])

    # As `market_only` também levam preço: sem ele a aba Pimp mostrava-as sem
    # valor nenhum, que é metade da decisão. Vêm no mesmo payload da expansão.
    por_exp = {r["set_id"]: r["expansion_id"] for r in con.execute(
        "SELECT DISTINCT p.set_id, m.expansion_id FROM catalog.printings p "
        "JOIN catalog.cardtrader_map m ON m.printing_id = p.printing_id")}
    for r in con.execute("SELECT printing_id, blueprint_id, set_id FROM catalog.market_only"):
        bp_to_printings.setdefault(r["blueprint_id"], []).append(r["printing_id"])
        e = por_exp.get(r["set_id"])
        if e:
            exps.setdefault(e, set()).add(r["blueprint_id"])
    if not bp_to_printings:
        con.close()
        raise CardTraderError("o mapa está vazio — corre primeiro `riftvault map`")

    # Histórico de TODAS as impressões (decisão do André, 2026-09-01): a vista
    # "a subir de preço" é sobre o Riftbound inteiro, não só sobre a coleção —
    # serve para apanhar cartas a valorizar antes de entrarem num deck dele.
    #
    # O custo é contido porque só se grava quando o preço MUDA, e porque isto
    # vive no prices.db, um ficheiro pequeno e à parte do vault.db.
    catalogadas = {r["printing_id"] for r in con.execute(
        "SELECT printing_id FROM catalog.printings")}
    rows, sem_preco, com_foil = [], 0, 0
    aceites = linguas()
    log(f"  línguas que contam: {', '.join(sorted(aceites))}")

    for expansion_id in sorted(exps):
        log(f"  expansão {expansion_id}: a descarregar o mercado...")
        market = ct.marketplace(expansion_id)
        for bid in exps[expansion_id]:
            products = market.get(str(bid)) or market.get(bid) or []
            o = oferta(products, aceites)
            if o["cents"] is None:
                sem_preco += 1
            if o["foil_cents"] is not None:
                com_foil += 1
            for pid in bp_to_printings[bid]:
                rows.append((pid, o["cents"], "EUR", 1 if o["from_foil"] else 0,
                             o["n_listings"], o["n_sellers"], o["n_copies"],
                             today, "cardtrader",
                             o["foil_cents"], o["n_listings_foil"]))
        del market              # 45 MB por expansão; liberta antes da próxima
        log(f"  expansão {expansion_id}: {len(exps[expansion_id])} blueprints")
        time.sleep(1.0)

    con.execute("BEGIN")
    con.executemany(
        "INSERT INTO catalog.price_latest (printing_id, price_cents, currency, "
        "from_foil, n_listings, n_sellers, n_copies, day, source, "
        "price_foil_cents, n_listings_foil) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?) "
        "ON CONFLICT(printing_id) DO UPDATE SET price_cents=excluded.price_cents, "
        "currency=excluded.currency, from_foil=excluded.from_foil, "
        "n_listings=excluded.n_listings, n_sellers=excluded.n_sellers, "
        "n_copies=excluded.n_copies, day=excluded.day, source=excluded.source, "
        # O preço da foil actualiza-se como o outro, e um `NULL` novo APAGA o
        # antigo de propósito: se hoje não há oferta foil, o valor da cópia foil
        # tem de cair para o fallback contado em vez de ficar preso ao preço da
        # semana passada. É a mesma regra do `price_cents`.
        "price_foil_cents=excluded.price_foil_cents, "
        "n_listings_foil=excluded.n_listings_foil",
        rows)

    # Histórico: de tudo o que está no catálogo (as `market_only` ficam de
    # fora, não têm impressão nossa), e só quando o valor muda face ao último
    # registo. Assim o prices.db não cresce em dias em que nada mexeu.
    # O histórico continua a ser só do preço NORMAL (`price_history` tem uma
    # coluna de preço): o «A subir» mede a subida da carta que ele compra, e a
    # série da foil seria outra pergunta, que ele não fez.
    gravadas, gravadas_of = 0, 0
    for (pid, cents, cur, _foil, n_list, n_sell, n_cop,
         _day, _src, _foil_cents, _n_foil) in rows:
        if pid not in catalogadas:
            continue
        if cents is not None:
            last = con.execute(
                "SELECT price_cents FROM prices.price_history WHERE printing_id = ? "
                "ORDER BY day DESC LIMIT 1", (pid,)).fetchone()
            if not (last and last["price_cents"] == cents):
                con.execute(
                    "INSERT INTO prices.price_history (printing_id, day, price_cents, currency) "
                    "VALUES (?,?,?,?) ON CONFLICT(printing_id, day) DO UPDATE SET "
                    "price_cents=excluded.price_cents", (pid, today, cents, cur))
                gravadas += 1
        if _guardar_oferta(con, pid, today, n_list, n_sell, n_cop):
            gravadas_of += 1
    con.execute("COMMIT")

    val = collection_value(con)
    con.close()
    return {"printings": len(rows), "sem_preco": sem_preco,
            # Quantos BLUEPRINTS ficaram com preço de foil (2026-09-26). É por
            # blueprint e não por impressão porque é o que se mediu contra o
            # mercado; uma impressão nossa pode partilhar blueprint com outra.
            "com_preco_foil": com_foil,
            "historico_gravado": gravadas, "oferta_gravada": gravadas_of,
            "valor": val}


# Só se grava a oferta quando ela MEXE mesmo. O `prices.db` vai para o Git e
# cada commit guarda o ficheiro binário inteiro: gravar as ~1200 impressões
# todos os dias engordava-o sem dizer nada de novo, porque o número de anúncios
# oscila uma ou duas unidades por dia sozinho. Com o degrau abaixo fica só o
# que é sinal — uma carta a ser comprada perde listagens depressa.
OFERTA_DEGRAU_MIN = 3           # em anúncios
OFERTA_DEGRAU_PCT = 10.0        # ou em percentagem do último registo


def _guardar_oferta(con: sqlite3.Connection, pid: str, day: str,
                    n_listings: int, n_sellers: int, n_copies: int) -> bool:
    """Grava o tamanho da oferta em `listings_history`, se mudou o suficiente.

    O primeiro registo de cada impressão grava-se sempre — é a linha de base
    contra a qual as seguintes se comparam.
    """
    last = con.execute(
        "SELECT n_listings FROM prices.listings_history WHERE printing_id = ? "
        "ORDER BY day DESC LIMIT 1", (pid,)).fetchone()
    if last is not None:
        antes = last["n_listings"]
        delta = abs(n_listings - antes)
        if delta < max(OFERTA_DEGRAU_MIN, antes * OFERTA_DEGRAU_PCT / 100):
            return False
    con.execute(
        "INSERT INTO prices.listings_history (printing_id, day, n_listings, "
        "n_sellers, n_copies) VALUES (?,?,?,?,?) "
        "ON CONFLICT(printing_id, day) DO UPDATE SET n_listings=excluded.n_listings, "
        "n_sellers=excluded.n_sellers, n_copies=excluded.n_copies",
        (pid, day, n_listings, n_sellers, n_copies))
    return True


# ---------------------------------------------------------------------------
# Valor
# ---------------------------------------------------------------------------


def _sem_retiradas(con: sqlite3.Connection) -> tuple[str, list[str]]:
    """O pedaço de SQL que tira do `copies` o que não existe para o riftvault —
    as runas em alt art (`metrics.retirada`, 2026-09-17: *"nao incluas em
    nada"*, e o valor é «nada» também). (cláusula, parâmetros)."""
    from . import metrics

    ids = sorted(metrics.retiradas_ids(con))
    if not ids:
        return "", []
    return " AND c.printing_id NOT IN (" + ",".join("?" * len(ids)) + ")", ids


def copias_sql(con: sqlite3.Connection, cfg: dict | None = None) -> tuple[str, list]:
    """O `FROM` das cópias que a COLEÇÃO conta como suas, aliás `c`.

    É o `copies` menos as cópias PRÓPRIAS dos decks (`proprio:<slug>`,
    2026-09-21: *"estas copias que eu coloco nos decks nao sao para adicionar
    a coleccao"*) — o valor é da Coleção, e um `+` num deck não o pode mexer.
    O gémeo em Python, por impressão, é o `locais.contadas`. (fragmento,
    parâmetros) — os parâmetros vêm ANTES dos do `WHERE`.

    Dá TRÊS colunas, porque as cópias normais e as foil não valem o mesmo desde
    2026-09-26:

      `qty_normal`  as cópias normais (`copies.qty`) menos as próprias dos decks
      `qty_foil`    as cópias foil (`copies.qty_foil`) que contam — **zero** com
                    `foil.conta_para_valor` desligado. Os locais não se
                    descontam aqui: a `copy_locations` só conta normais.
      `qty`         a soma, que é «quantas cópias a Coleção conta». É esta que o
                    `collection.totals` lê, e é por isso que ela mantém o nome.

    Quem quiser o VALOR usa o `valor_sql`, nunca `qty * price_cents`: a cópia
    foil vale o `price_foil_cents`. A chave lê-se do config directamente, sem
    importar o `foil`, como no `locais._foils`.
    """
    from . import locais

    foil = ("COALESCE(c0.qty_foil, 0)" if (
        ((cfg or config.load()).get("foil") or {}).get("conta_para_valor", False))
        else "0")
    return (f"(SELECT c0.printing_id, "
            f"        c0.qty - COALESCE(cl.q, 0) AS qty_normal, "
            f"        {foil} AS qty_foil, "
            f"        c0.qty - COALESCE(cl.q, 0) + {foil} AS qty "
            " FROM copies c0 "
            " LEFT JOIN (SELECT printing_id, SUM(qty) AS q FROM copy_locations "
            "            WHERE location LIKE ? GROUP BY printing_id) cl "
            " ON cl.printing_id = c0.printing_id) c", [locais.PROPRIO_PREFIX + "%"])


def valor_sql(c: str = "c", p: str = "p") -> str:
    """O valor das cópias de uma impressão, em cêntimos — a ÚNICA definição.

    As normais ao `price_cents` e **as foil ao `price_foil_cents`**
    (2026-09-26). O `COALESCE` de dentro é o FALLBACK: sem oferta foil no
    CardTrader a cópia foil conta ao preço da normal, e essas cópias são
    contadas à parte no `valor_dos_foils` para o total se poder ler como um
    PISO. O `COALESCE` de fora deixa uma impressão sem preço valer zero em vez
    de anular a soma inteira.

    `c` é o alias do `copias_sql` e `p` o do `price_latest`.
    """
    return (f"(COALESCE({c}.qty_normal * {p}.price_cents, 0) "
            f" + COALESCE({c}.qty_foil * COALESCE({p}.price_foil_cents, "
            f"                                    {p}.price_cents), 0))")


def valor_das_copias(qty_normal: int, qty_foil: int, price_cents: int | None,
                     price_foil_cents: int | None) -> int:
    """O `valor_sql` em Python, por impressão — a mesma conta, em cêntimos.

    São precisas as duas porque o valor se calcula em dois sítios com formas
    diferentes: em SQL sobre a coleção inteira (`collection_value`) e em Python
    sobre o payload de uma edição (`metrics.set_payload`), que já tem os números
    na mão. O terceiro gémeo é o `valorDasCopias` do `app.js`, que recalcula no
    cliente a cada `+`/`−`. Há teste que corre os três sobre os mesmos casos.
    """
    preco_foil = price_foil_cents if price_foil_cents is not None else price_cents
    return ((qty_normal * price_cents if price_cents is not None else 0)
            + (qty_foil * preco_foil if preco_foil is not None else 0))


def collection_value(con: sqlite3.Connection) -> dict:
    """Valor total da coleção: as normais ao preço da normal, as foil ao preço
    da foil (2026-09-26) — sem as retiradas. Ver o `valor_sql`."""
    fonte, p_fonte = copias_sql(con)
    fora, params = _sem_retiradas(con)
    row = con.execute(
        f"SELECT COALESCE(SUM({valor_sql()}), 0) AS cents, "
        "       COALESCE(SUM(CASE WHEN p.price_cents IS NULL THEN c.qty ELSE 0 END), 0) AS sem_preco, "
        "       COALESCE(SUM(c.qty), 0) AS copias, "
        # Quanto do total vem de cartas que o CardTrader só lista em foil. É
        # o número que diz se dá para confiar no total: uma cópia NORMAL dessas
        # está avaliada a preço de foil, logo sobreavaliada. Conta só as
        # normais: desde 2026-09-26 as foil dessas impressões têm o preço certo
        # (o `price_foil_cents`, que ali é o mesmo número) e não são ressalva.
        "       COALESCE(SUM(CASE WHEN p.from_foil = 1 "
        "                    THEN c.qty_normal * p.price_cents ELSE 0 END), 0) AS cents_foil, "
        "       COALESCE(SUM(CASE WHEN p.from_foil = 1 THEN c.qty_normal ELSE 0 END), 0) AS copias_foil "
        f"FROM {fonte} LEFT JOIN catalog.price_latest p ON p.printing_id = c.printing_id "
        "WHERE c.qty > 0" + fora, [*p_fonte, *params]
    ).fetchone()
    day = con.execute("SELECT MAX(day) AS d FROM catalog.price_latest").fetchone()
    return {"cents": row["cents"] or 0, "currency": "EUR",
            "copias_sem_preco": row["sem_preco"] or 0, "copias": row["copias"] or 0,
            "cents_de_foil": row["cents_foil"] or 0, "copias_de_foil": row["copias_foil"] or 0,
            # Quanto do total vem das foils MARCADAS e ao preço de quê
            # (2026-09-26). Vai DENTRO do valor, e não à parte, para nenhuma
            # vista poder mostrar o total sem a ressalva: as que caem no
            # FALLBACK (preço da normal, por não haver oferta foil) fazem deste
            # número um PISO. `None` com o botão desligado. Ver o
            # `valor_dos_foils`.
            "foils": valor_dos_foils(con),
            "day": day["d"] if day else None}


def valor_dos_foils(con: sqlite3.Connection, cfg: dict | None = None) -> dict | None:
    """Quanto do valor vem das cópias FOIL, e AO PREÇO DE QUÊ (2026-09-26).

    Desde a tarde de 2026-09-26 há preço de foil a sério: o `price_foil_cents`,
    o mínimo das ofertas FOIL do CardTrader com os mesmos filtros das normais
    (*"podes meter filtro no cardtrader e tirar o preco da foil mais barata?,
    para diferenciar os precos"*). Uma cópia foil vale esse preço — e só quando
    ele não existe é que cai para o da normal. Esse FALLBACK é o que faz do
    total um PISO, e por isso conta-se e diz-se, em vez de ficar num comentário.

      `preco_de_foil`       {printings, copies, cents} — há `price_foil_cents`
                            (ou `from_foil`, que é o mesmo número): preço de
                            foil a sério, sem ressalva
      `ao_preco_da_normal`  {printings, copies, cents} — **o FALLBACK**: não há
                            oferta foil no CardTrader e a cópia conta ao preço
                            da normal. O valor real é mais alto (uma foil
                            raramente vale menos do que a normal)
      `sem_preco`           {printings, copies} — sem oferta nenhuma; não contam
      `copies`, `cents`     o total das foils no valor

    Quando o `from_foil` é 1 a impressão cai em `preco_de_foil` — e é o mesmo
    número do `price_cents`, porque a única oferta que havia era foil. Era esse
    o único caso «sem ressalva» até hoje; agora é o caso geral.

    `None` com `foil.conta_para_valor` desligado: não há foils no valor e não há
    nada a ressalvar.
    """
    if not ((cfg or config.load()).get("foil") or {}).get("conta_para_valor", False):
        return None
    fora, params = _sem_retiradas(con)
    # As foils de uma impressão RETIRADA não contam, como as normais dela.
    rows = con.execute(
        "SELECT c.qty_foil AS n, p.price_cents AS cents, "
        "       p.price_foil_cents AS foil_cents, COALESCE(p.from_foil, 0) AS ff "
        "FROM copies c LEFT JOIN catalog.price_latest p "
        "  ON p.printing_id = c.printing_id "
        "WHERE c.qty_foil > 0" + fora, params).fetchall()
    out = {k: {"printings": 0, "copies": 0, "cents": 0}
           for k in ("preco_de_foil", "ao_preco_da_normal")}
    out["sem_preco"] = {"printings": 0, "copies": 0}
    for r in rows:
        normal = r["cents"]
        # `from_foil = 1` diz que o `price_cents` JÁ é de foil — não havia oferta
        # normal nenhuma. Conta como preço de foil mesmo que o
        # `price_foil_cents` esteja vazio, que é o estado de um catálogo entre a
        # migração e o `riftvault prices` seguinte: o número é o mesmo, e chamar
        # àquilo «fallback» era dizer que o preço é da normal quando não é.
        se_foil = (r["foil_cents"] if r["foil_cents"] is not None
                   else (normal if r["ff"] else None))
        preco = se_foil if se_foil is not None else normal
        if preco is None:
            out["sem_preco"]["printings"] += 1
            out["sem_preco"]["copies"] += r["n"]
            continue
        slot = out["preco_de_foil"] if se_foil is not None else out["ao_preco_da_normal"]
        slot["printings"] += 1
        slot["copies"] += r["n"]
        slot["cents"] += r["n"] * preco
    out["copies"] = sum(r["n"] for r in rows)
    out["cents"] = out["preco_de_foil"]["cents"] + out["ao_preco_da_normal"]["cents"]
    return out


def value_by_set(con: sqlite3.Connection) -> dict[str, int]:
    fonte, p_fonte = copias_sql(con)
    fora, params = _sem_retiradas(con)
    rows = con.execute(
        f"SELECT pr.set_id AS s, COALESCE(SUM({valor_sql()}), 0) AS cents "
        f"FROM {fonte} "
        "JOIN catalog.printings pr ON pr.printing_id = c.printing_id "
        "LEFT JOIN catalog.price_latest p ON p.printing_id = c.printing_id "
        "WHERE c.qty > 0" + fora + " GROUP BY pr.set_id", [*p_fonte, *params]
    ).fetchall()
    return {r["s"]: r["cents"] or 0 for r in rows}


def top_value(con: sqlite3.Connection, limit: int = 15) -> list[dict]:
    fonte, p_fonte = copias_sql(con)
    fora, params = _sem_retiradas(con)
    rows = con.execute(
        "SELECT pr.public_code, pr.name, pr.variant_label, c.qty, p.price_cents, "
        # O total leva as foils ao preço delas (`valor_sql`), e as duas colunas
        # ao lado dizem porque é que a linha não é `qty × price_cents`.
        "       c.qty_normal, c.qty_foil, p.price_foil_cents, "
        f"       {valor_sql()} AS total, p.from_foil "
        f"FROM {fonte} "
        "JOIN catalog.printings pr ON pr.printing_id = c.printing_id "
        "JOIN catalog.price_latest p ON p.printing_id = c.printing_id "
        "WHERE c.qty > 0 AND p.price_cents IS NOT NULL" + fora +
        " ORDER BY total DESC LIMIT ?", [*p_fonte, *params, limit]).fetchall()
    return [dict(r) for r in rows]


def eur(cents: int | None) -> str:
    return "—" if cents is None else f"{cents / 100:.2f} €"

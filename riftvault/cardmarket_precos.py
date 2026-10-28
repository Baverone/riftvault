"""OS PREÇOS DO CARDMARKET, TODOS OS DIAS — e o que cada número É mesmo.

André, 2026-10-25: *"preciso que estejas constantemente a atulizar o Price
Trend do market, principalmente de Radiance, pois vou abrir muitos boosters e
vou vender cartas"*.

DUAS FONTES, cada uma pelo que tem de seu (medido a 2026-10-25)
    1. O **PRICE GUIDE OFICIAL DO CARDMARKET** — um ficheiro JSON que o próprio
       Cardmarket publica para download, gerado uma vez por dia (o de 25/10 diz
       `createdAt: 2026-10-25T02:47:35+0200`), um por jogo; o Riftbound é o jogo
       **22** (1862 produtos). Traz, por `idProduct`: `trend`, `low`, `avg1`,
       `avg7`, `avg30` e os mesmos com `-foil` (mais um `avg`, que a página não
       mostra). É ESTE o número que a página da carta chama «Price Trend». Não
       é a página do Cardmarket (essa tem o desafio anti-bot e não se toca por
       programa): é um ficheiro de download, um pedido por dia.
    2. A **API DA DOTGG** (`part=prices`, a mesma casa do catálogo da RAD) —
       serve para LIGAR cada impressão do riftvault ao `idProduct` do Cardmarket
       (`cmid`) e ao endereço da página (`cmurl`), e traz o preço do OUTRO
       mercado, em dólares (`price`/`foilPrice`).

O `cmPrice` DA DOTGG NÃO É O TREND — É A MÉDIA DE 1 DIA
    Comparados os 1633 `cmPrice` da dotgg com todos os campos do guia do mesmo
    dia: **1429 batem ao cêntimo com o `avg1`** (média de 1 dia) e só 190 com o
    `trend`; nos foils **1559 de 1577 batem com o `avg1-foil`**. Quando o
    `avg1` não existe, a dotgg cai para o `low` («From»: Angler Wyrm, RAD-113,
    1,75 €). E numa carta que só existe em foil o `cmPrice` é um número que a
    página nem mostra (Ambessa, VEN-196: dotgg 95,00 €; a página diz Trend
    60,61 €). Por isso o riftvault NÃO usa o `cmPrice` da dotgg para nada —
    lê o Trend do guia, e cada coluna diz o que é.

NUMA CARTA QUE SÓ EXISTE EM FOIL, O TREND DA PÁGINA É O DO FOIL
    As raras para cima só existem em foil, e o guia dá-lhes `trend: 0` no lado
    normal. A página mostra os números do foil (Angler Wyrm: 2,99 € =
    `trend-foil`; Ambessa: 60,61 € = `trend-foil`, e as três médias também
    batem). O `has_normal` da dotgg diz qual é o caso; é dele que sai o
    `preco_referencia` — o número que a página mostra.

Um zero do guia guarda-se como `NULL`: é «o Cardmarket não tem número», não
«vale zero».
"""

from __future__ import annotations

import json
import sqlite3
import urllib.request
from datetime import date, timedelta

from . import config

URL_GUIA = ("https://downloads.s3.cardmarket.com/productCatalog/priceGuide/"
            "price_guide_{jogo}.json")
JOGO_RIFTBOUND = 22
URL_DOTGG = "https://api.dotgg.gg/cgfw/getcards?game=riftbound&mode=indexed&part=prices"
USER_AGENT = "riftvault/1.0 (colecao pessoal; +github)"   # ASCII (ver o CardTrader)
TIMEOUT = 60

#: os seis campos do guia, pela ordem da página; cada um tem o gémeo `-foil`.
CAMPOS = ("trend", "low", "avg1", "avg7", "avg30")

#: (nome, dias para trás, folga) — a mesma regra do selado (2026-10-13): a
#: referência de «há 7 dias» é a medição mais recente entre 9 e 7 dias antes.
JANELAS = (("1d", 1, 1), ("7d", 7, 2))


class FonteFalhou(RuntimeError):
    pass


def _pedir(url: str, timeout: int = TIMEOUT) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                               "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # rede, HTTP, JSON partido — é tudo «a fonte falhou»
        raise FonteFalhou(f"{url}: {exc}") from exc


def buscar_guia(jogo: int = JOGO_RIFTBOUND) -> dict:
    corpo = _pedir(URL_GUIA.format(jogo=jogo))
    if not isinstance(corpo.get("priceGuides"), list) or not corpo.get("createdAt"):
        raise FonteFalhou("o price guide do Cardmarket não tem a forma medida "
                          "(priceGuides/createdAt)")
    return corpo


def buscar_dotgg() -> list[dict]:
    corpo = _pedir(URL_DOTGG)
    nomes, dados = corpo.get("names"), corpo.get("data")
    if not isinstance(nomes, list) or not isinstance(dados, list) or "cmid" not in nomes:
        raise FonteFalhou("a resposta de preços da dotgg não tem a forma medida")
    return [dict(zip(nomes, d)) for d in dados]


def _cents(v) -> int | None:
    """Euros (número ou texto) -> cêntimos. Zero e vazio são «não há número»."""
    if v is None or v == "":
        return None
    try:
        c = int(round(float(v) * 100))
    except (TypeError, ValueError):
        return None
    return c or None


def _impressao_de(gid: str, ids: set[str], aliases: dict[str, str]) -> str | None:
    g = (gid or "").lower()
    return g if g in ids else aliases.get(g)


def juntar(guia: dict, dotgg: list[dict] | None, con: sqlite3.Connection,
           ligacoes_antigas: dict[str, dict] | None = None) -> dict:
    """As linhas a gravar: UMA POR IMPRESSÃO do catálogo que se consiga ligar a
    um produto do guia.

    A ligação vem da dotgg (`cmid`). Sem a dotgg (a fonte falhou) usa-se a
    ligação gravada no último dia (`ligacoes_antigas`) — os preços do
    Cardmarket não ficam um dia por guardar porque a dotgg caiu. Quando duas
    linhas da dotgg caem na mesma impressão (medido: `OGN-279` e `OGN-279/298`)
    fica a que tem `cmid`."""
    ids = {r[0] for r in con.execute("SELECT printing_id FROM catalog.printings")}
    aliases = dict(con.execute("SELECT alias, printing_id FROM catalog.printing_aliases"))
    por_produto = {int(p["idProduct"]): p for p in guia["priceGuides"] if p.get("idProduct")}
    dia = str(guia["createdAt"])[:10]
    date.fromisoformat(dia)

    ligacoes: dict[str, dict] = {}
    sem_impressao = 0
    if dotgg is not None:
        for d in dotgg:
            pid = _impressao_de(d.get("id"), ids, aliases)
            if not pid:
                sem_impressao += 1
                continue
            antes = ligacoes.get(pid)
            if antes and antes.get("cm_product_id") and not d.get("cmid"):
                continue
            ligacoes[pid] = {
                "dotgg_id": d.get("id"),
                "cm_product_id": int(d["cmid"]) if d.get("cmid") else None,
                "cm_url": d.get("cmurl") or None,
                "has_normal": 1 if str(d.get("hasNormal")) == "1" else 0,
                "has_foil": 1 if str(d.get("hasFoil")) == "1" else 0,
                "outro_usd_cents": _cents(d.get("price")),
                "outro_usd_foil_cents": _cents(d.get("foilPrice")),
            }
        origem = "dotgg"
    else:
        ligacoes = {k: dict(v, outro_usd_cents=None, outro_usd_foil_cents=None)
                    for k, v in (ligacoes_antigas or {}).items()}
        origem = "ligacao-anterior"

    linhas, sem_produto, fora_do_guia = [], 0, 0
    for pid, lg in ligacoes.items():
        cm = lg.get("cm_product_id")
        if not cm:
            sem_produto += 1
            continue
        p = por_produto.get(cm)
        if p is None:
            fora_do_guia += 1
            continue
        ln = {"printing_id": pid, "day": dia, **lg,
              "guia_criado_em": str(guia["createdAt"]), "fonte": origem}
        for k in CAMPOS:
            ln[f"{k}_cents"] = _cents(p.get(k))
            ln[f"{k}_foil_cents"] = _cents(p.get(f"{k}-foil"))
        linhas.append(ln)
    return {"dia": dia, "linhas": linhas, "sem_impressao": sem_impressao,
            "sem_produto": sem_produto, "fora_do_guia": fora_do_guia,
            "origem_ligacao": origem}


#: o que vai para a linha DO DIA (só números) e o que vai para a LIGAÇÃO (o
#: que não muda de dia para dia). Ver o `prices_schema.sql`: separá-los é o que
#: impede o prices.db de crescer 320 KB por dia.
COLUNAS = (["printing_id", "day"]
           + [f"{k}_cents" for k in CAMPOS] + [f"{k}_foil_cents" for k in CAMPOS]
           + ["outro_usd_cents", "outro_usd_foil_cents"])
COLUNAS_LIGACAO = ["printing_id", "cm_product_id", "dotgg_id", "cm_url",
                   "has_normal", "has_foil"]


def gravar(con: sqlite3.Connection, linhas: list[dict], dia: str | None = None,
           guia_criado_em: str | None = None, origem: str | None = None) -> int:
    """Uma linha por impressão e por dia; um segundo `--sync` no mesmo dia
    substitui. A ligação reescreve-se (com os mesmos bytes quando nada mudou).
    Só toca no `prices.db`, numa transação só."""
    marcas = ",".join("?" * len(COLUNAS))
    marcas_l = ",".join("?" * len(COLUNAS_LIGACAO))
    con.execute("BEGIN IMMEDIATE")
    try:
        con.executemany(f"INSERT OR REPLACE INTO prices.cardmarket_price_history "
                        f"({','.join(COLUNAS)}) VALUES ({marcas})",
                        [[ln.get(c) for c in COLUNAS] for ln in linhas])
        con.executemany(f"INSERT OR REPLACE INTO prices.cardmarket_ligacao "
                        f"({','.join(COLUNAS_LIGACAO)}) VALUES ({marcas_l})",
                        [[ln.get(c) for c in COLUNAS_LIGACAO] for ln in linhas])
        if dia:
            con.execute("INSERT OR REPLACE INTO prices.cardmarket_dia "
                        "(day, guia_criado_em, origem_ligacao, linhas) VALUES (?,?,?,?)",
                        (dia, guia_criado_em, origem, len(linhas)))
    except BaseException:
        con.execute("ROLLBACK")
        raise
    con.execute("COMMIT")
    return len(linhas)


def ligacoes_gravadas(con: sqlite3.Connection) -> dict[str, dict]:
    """A ligação conhecida de cada impressão (a rede de segurança para um dia em
    que a dotgg não responda)."""
    return {r["printing_id"]: {k: r[k] for k in COLUNAS_LIGACAO if k != "printing_id"}
            for r in con.execute("SELECT * FROM prices.cardmarket_ligacao")}


def sincronizar(con: sqlite3.Connection, guia: dict | None = None,
                dotgg: list[dict] | None = None, sem_dotgg: bool = False,
                log=print) -> dict:
    """Busca as duas fontes (ou usa as dadas — os testes não vão à rede) e grava
    o dia. A dotgg pode falhar sem o dia se perder; o guia não — sem ele não há
    Trend nenhum, e é isso que se diz."""
    guia = guia if guia is not None else buscar_guia()
    aviso = None
    if dotgg is None and not sem_dotgg:
        try:
            dotgg = buscar_dotgg()
        except FonteFalhou as exc:
            aviso = f"a dotgg falhou ({exc}); usei a ligação gravada no último dia"
            dotgg = None
    res = juntar(guia, dotgg, con, None if dotgg is not None else ligacoes_gravadas(con))
    res["gravadas"] = gravar(con, res["linhas"], res["dia"], str(guia["createdAt"]),
                             res["origem_ligacao"])
    res["aviso"] = aviso
    if aviso:
        log("  ! " + aviso)
    return res


# ---------------------------------------------------------------------------
# LEITURA
# ---------------------------------------------------------------------------

def preco_referencia(ln: dict, foil: bool = False) -> int | None:
    """O número que a PÁGINA do Cardmarket chama «Price Trend».

    Uma carta que só existe em foil (`has_normal = 0`) mostra o trend do foil —
    e as cópias dela, que o riftvault conta como «normais» (`copies.qty` de uma
    rara), valem esse número. Com versão normal, a normal vale o trend e a foil
    o trend do foil."""
    if foil or not ln.get("has_normal"):
        return ln.get("trend_foil_cents")
    return ln.get("trend_cents")


def valor(ln: dict, qty_normal: int, qty_foil: int) -> int | None:
    """O valor das cópias de uma impressão pelo Trend. `None` se alguma cópia
    não tiver Trend — não se inventa (o total diz quantas ficaram de fora)."""
    total = 0
    for q, foil in ((qty_normal, False), (qty_foil, True)):
        if not q:
            continue
        p = preco_referencia(ln, foil)
        if p is None:
            return None
        total += q * p
    return total


def series(con: sqlite3.Connection) -> dict[str, list[dict]]:
    """A série de cada impressão, do dia mais antigo para o mais recente, com a
    ligação (o `has_normal`, o URL) em cada linha."""
    out: dict[str, list[dict]] = {}
    for r in con.execute("SELECT h.*, l.cm_product_id, l.dotgg_id, l.cm_url, "
                         "       COALESCE(l.has_normal, 0) AS has_normal, "
                         "       COALESCE(l.has_foil, 0) AS has_foil "
                         "FROM prices.cardmarket_price_history h "
                         "LEFT JOIN prices.cardmarket_ligacao l ON l.printing_id = h.printing_id "
                         "ORDER BY h.printing_id, h.day"):
        out.setdefault(r["printing_id"], []).append(dict(r))
    return out


def variacao(serie: list[dict], foil: bool = False) -> dict:
    """A variação do `preco_referencia` contra a medição de há 1 e 7 dias (com a
    folga do selado). Sem medição dentro da janela, a janela vem `None` — nunca
    se chama «7 dias» a uma diferença de quinze."""
    out = {nome: None for nome, _, _ in JANELAS}
    if not serie:
        return out
    agora = serie[-1]
    p_agora = preco_referencia(agora, foil)
    if p_agora is None:
        return out
    d_agora = date.fromisoformat(agora["day"])
    for nome, dias, folga in JANELAS:
        de, ate = d_agora - timedelta(days=dias + folga), d_agora - timedelta(days=dias)
        ref = [s for s in serie[:-1]
               if de <= date.fromisoformat(s["day"]) <= ate
               and preco_referencia(s, foil) is not None]
        if ref:
            p_ref = preco_referencia(ref[-1], foil)
            out[nome] = {"cents": p_agora - p_ref, "desde": ref[-1]["day"],
                         "pct": round(100.0 * (p_agora - p_ref) / p_ref, 1) if p_ref else None}
    return out


def ultimos(con: sqlite3.Connection) -> dict[str, dict]:
    """A última linha gravada de cada impressão."""
    return {pid: s[-1] for pid, s in series(con).items()}


def comparar_valor(con: sqlite3.Connection) -> dict:
    """O valor da Coleção pelo Trend do Cardmarket ao lado do do site (CardTrader),
    SOBRE AS MESMAS CÓPIAS: as que a Coleção conta (`prices.copias_sql` — sem as
    próprias dos decks nem o stock) e sem as retiradas. São mercados diferentes
    e a diferença diz-se em vez de se esconder."""
    from . import prices

    fonte, p_fonte = prices.copias_sql(con)
    fora, params = prices._sem_retiradas(con)
    ult = ultimos(con)
    total, copias, sem_trend, impressoes_sem = 0, 0, 0, 0
    for r in con.execute(f"SELECT c.printing_id, c.qty_normal, c.qty_foil FROM {fonte} "
                         f"WHERE c.qty > 0" + fora, [*p_fonte, *params]):
        q = (r["qty_normal"] or 0) + (r["qty_foil"] or 0)
        copias += q
        ln = ult.get(r["printing_id"])
        v = valor(ln, r["qty_normal"] or 0, r["qty_foil"] or 0) if ln else None
        if v is None:
            sem_trend += q
            impressoes_sem += 1
        else:
            total += v
    site = prices.collection_value(con)
    dia = max((ln["day"] for ln in ult.values()), default=None)
    return {"cm_cents": total, "ct_cents": site["cents"], "copias": copias,
            "copias_sem_trend": sem_trend, "impressoes_sem_trend": impressoes_sem,
            "dia_cm": dia, "dia_ct": site.get("day")}


def eur(cents: int | None) -> float | None:
    return None if cents is None else round(cents / 100.0, 2)

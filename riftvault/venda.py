"""«Venda» (2026-09-25): a conta de uma venda em curso, para mostrar a quem compra.

Palavras do André: *"quero que cries um separador que e: Venda. este separador
permite-me marcar as cartas que estou a vender no momento para apresentar a
conta a pessoa. **todos os precos tem que ser o Trend do Cardmarket!**"*.

NÃO É A VENDA DE 2026-09-08 (apagada a 2026-09-15). Aquela era uma SUGESTÃO —
o que sobra acima do alvo, calculado pelo riftvault — e essa pergunta vive hoje
no separador «A mais». Esta é outra: ele está à mesa com o comprador, marca o
que está a vender, e o ecrã dá a conta. A lista é dele, não é calculada.

O TREND DO CARDMARKET É METIDO POR ELE, E NÃO HÁ OUTRA MANEIRA
    A app NÃO TEM preços do Cardmarket e não há como os ter:

      * o `catalog.price_latest` é tudo do **CardTrader** (`source =
        'cardtrader'`) e é a OFERTA MAIS BARATA, não um Trend — são conceitos
        diferentes e trocá-los seria mentir num número que ele vai cobrar a
        alguém;
      * a API oficial do Cardmarket está **fechada a novas candidaturas**
        (confirmado em 2026-09-25 na página de ajuda deles), e o site responde
        403 a pedidos automáticos (está no CLAUDE.md desde 2026-08-31);
      * as APIs de terceiros que revendem o Trend são pagas, e a regra dele é
        *só a subscrição*;
      * fazer scraping ao Cardmarket está fora de questão.

    Por isso o preço de cada linha é um campo que ELE preenche, em euros, com
    o Trend que está a ver no Cardmarket — e a linha tem um link directo para
    a página da carta lá (`cardmarket_id`, que o `riftvault map` já recolhe do
    CardTrader: 1178 das 1179 impressões têm um). Os templates desses links
    mudaram-se a 2026-09-25 para o bloco `mercados` do config (ver
    `mercados.py`), porque o «Produto Selado» passou a precisar dos mesmos.

    O preço do CardTrader que a app já tem aparece ao lado, **rotulado como
    CardTrader e só como referência**. NUNCA entra na conta, nem como omissão
    de uma linha por preencher: uma linha sem Trend conta **zero** e o total
    diz quantas linhas estão por preencher. Substituir por outro preço era
    apresentar a conta errada a uma pessoa a sério.

    O Trend guarda-se POR IMPRESSÃO com a data (`cardmarket_trend`), para a
    venda seguinte já vir preenchida; passados `venda.trend_valido_dias` dias
    fica marcado como velho — **não se apaga**, porque um Trend de há duas
    semanas ainda é melhor ponto de partida do que um campo em branco.

MARCAR PARA VENDA NÃO TIRA NADA DE LADO NENHUM
    As linhas vivem numa tabela à parte (`sale_lines`) que mais nenhum módulo
    lê. Meter e tirar cartas da venda não mexe nos níveis, no denominador, nas
    Faltas, nas wantlists, no valor, no A mais, nos decks, no foil nem nas
    cópias próprias — `tests/test_venda.py` fotografa tudo isso, mete e tira
    linhas, e exige que fique igual. É a mesma defesa das cópias próprias
    (2026-09-21) e da contagem de foil (2026-09-22).

    Quem baixa as cópias é o botão SEPARADO «marcar como vendidas»
    (`vender()`), com confirmação, que passa pelo `collection.adjust` — logo
    fica na `ops` e dá para desfazer — e escreve uma linha por carta na
    `sale_log`. Nunca automático.

AVISA, NÃO BLOQUEIA
    Pôr à venda mais cópias do que tem, ou uma carta que um deck MONTADO está
    a usar (hoje só o LeBlanc Hook), dá aviso na linha e no cabeçalho. Ele é
    que sabe o que tem na mão — o riftvault não lhe pode recusar uma venda.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

from . import cardmarket, collection, config, mercados, metrics

DEFAULTS: dict = {
    # A partir de quantos dias é que um Trend guardado se marca como velho.
    # Não se apaga: um Trend de há duas semanas é melhor ponto de partida do
    # que um campo em branco — só se diz que está velho.
    "trend_valido_dias": 7,
    # OS DOIS LINKS DO CARDMARKET MUDARAM-SE PARA O BLOCO `mercados`
    # (2026-09-25, quando o «Produto Selado» passou a precisar deles também):
    # `mercados.cardmarket_url` e `mercados.cardmarket_busca`, em
    # `riftvault/mercados.py`. Um config que ainda os traga aqui continua a
    # valer — o `mercados.opcoes` lê-os. A ressalva é a mesma: o formato por
    # id NÃO ESTÁ VALIDADO (o site responde 403 a pedidos automáticos), e é
    # por isso que cada linha leva também o link de pesquisa.
}


class SemLinha(ValueError):
    """Não há essa carta na venda em curso — um `−` numa linha que não existe."""


class PrecisaConfirmar(ValueError):
    """O «marcar como vendidas» baixa cópias a sério. Não se faz sem confirmar."""


class VendaVazia(ValueError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def opcoes(cfg: dict | None = None) -> dict:
    bruto = (cfg or config.load()).get("venda") or {}
    out = {**DEFAULTS, **{k: v for k, v in bruto.items() if not k.startswith("_")}}
    dias = out["trend_valido_dias"]
    if not isinstance(dias, (int, float)) or dias <= 0:
        raise ValueError("venda.trend_valido_dias tem de ser um número de dias > 0")
    return out


# ---------------------------------------------------------------------------
# O Trend do Cardmarket — metido à mão, guardado por impressão
# ---------------------------------------------------------------------------


def trends(con: sqlite3.Connection) -> dict[str, sqlite3.Row]:
    return {r["printing_id"]: r for r in
            con.execute("SELECT * FROM cardmarket_trend")}


def trend_de(con: sqlite3.Connection, printing_id: str) -> sqlite3.Row | None:
    return con.execute("SELECT * FROM cardmarket_trend WHERE printing_id = ?",
                       (printing_id,)).fetchone()


def guardar_trend(con: sqlite3.Connection, ref: str, cents: int | None,
                  source: str = "web") -> dict:
    """Grava (ou apaga, com `None`) o Trend do Cardmarket de uma impressão.

    O valor é DELE — vem do campo da linha, em euros, convertido para cêntimos
    por quem chama. Nunca se escreve aqui um preço do CardTrader: são fontes
    diferentes e a conta é feita com esta.
    """
    pid = collection.resolve_printing(con, ref)
    if cents is None:
        con.execute("DELETE FROM cardmarket_trend WHERE printing_id = ?", (pid,))
        return {"printing_id": pid, "cents": None, "updated_at": None}
    cents = int(cents)
    if cents < 0:
        raise ValueError("o Trend não pode ser negativo")
    ts = _now()
    con.execute(
        "INSERT INTO cardmarket_trend (printing_id, cents, updated_at, source) "
        "VALUES (?,?,?,?) ON CONFLICT(printing_id) DO UPDATE SET "
        "cents = excluded.cents, updated_at = excluded.updated_at, "
        "source = excluded.source", (pid, cents, ts, source))
    return {"printing_id": pid, "cents": cents, "updated_at": ts}


def _velho(updated_at: str | None, dias: float) -> tuple[bool, int | None]:
    """(está velho?, há quantos dias foi metido)."""
    if not updated_at:
        return False, None
    try:
        quando = datetime.fromisoformat(updated_at)
    except ValueError:
        return False, None
    if quando.tzinfo is None:
        quando = quando.replace(tzinfo=timezone.utc)
    idade = datetime.now(timezone.utc) - quando
    return idade > timedelta(days=dias), max(0, idade.days)


# ---------------------------------------------------------------------------
# As linhas da venda em curso
# ---------------------------------------------------------------------------


def linhas(con: sqlite3.Connection) -> dict[str, int]:
    return {r["printing_id"]: r["qty"] for r in
            con.execute("SELECT printing_id, qty FROM sale_lines")}


def juntar(con: sqlite3.Connection, ref: str, delta: int = 1,
           source: str = "web") -> dict:
    """Soma `delta` cópias de uma impressão à venda em curso.

    Uma linha por impressão — ele escolhe a versão que está a vender. A zero,
    a linha sai. Um `−` numa carta que não está na venda é `SemLinha`.

    **Não mexe no `copies` nem em conta nenhuma**: isto é uma lista de
    intenção. Quem baixa as cópias é o `vender()`.
    """
    pid = collection.resolve_printing(con, ref)
    delta = int(delta)
    atual = linhas(con).get(pid, 0)
    if delta < 0 and atual == 0:
        raise SemLinha(f"{pid} não está na venda")
    novo = max(0, atual + delta)
    if novo == 0:
        con.execute("DELETE FROM sale_lines WHERE printing_id = ?", (pid,))
    else:
        con.execute(
            "INSERT INTO sale_lines (printing_id, qty, added_at) VALUES (?,?,?) "
            "ON CONFLICT(printing_id) DO UPDATE SET qty = excluded.qty",
            (pid, novo, _now()))
    return {"printing_id": pid, "qty": novo, "applied": novo - atual}


def limpar(con: sqlite3.Connection) -> int:
    """Esvazia a venda em curso. Os Trends guardados FICAM — são da carta, não
    desta venda."""
    n = con.execute("SELECT COUNT(*) AS n FROM sale_lines").fetchone()["n"]
    con.execute("DELETE FROM sale_lines")
    return n


# ---------------------------------------------------------------------------
# A lista e a conta
# ---------------------------------------------------------------------------


# Os links vivem no `mercados.py` desde 2026-09-25 — é a mesma pergunta do
# «Produto Selado», e tem de ter uma resposta só.


def itens(con: sqlite3.Connection, cfg: dict | None = None) -> list[dict]:
    """As linhas da venda, com tudo o que a página precisa de dizer.

    O `price` é o do CardTrader e vai **rotulado como referência**; a conta
    faz-se com o `trend`, que é dele. Uma linha sem Trend tem `trend: None` e
    `subtotal: 0`.
    """
    from . import decks, locais

    cfg = cfg or config.load()
    op = opcoes(cfg)
    op_links = mercados.opcoes(cfg)
    dias = op["trend_valido_dias"]
    atuais = linhas(con)
    if not atuais:
        return []

    tr = trends(con)
    precos = metrics.prices_map(con)
    mercado = cardmarket.versoes(con)
    # SÓ as normais (2026-09-26): o aviso de stock é sobre as cópias que o
    # «marcar como vendidas» vai baixar, e esse baixa o `copies.qty`. Com os
    # foils a contar para a Coleção (`foil.conta_para_coleccao`) dizer que ele
    # tem 6 quando tem 3 normais e 3 foil mandava-o vender o que não quer
    # vender — a mesma razão do `foil.entra_no_a_mais: false`.
    na_colecao = locais.na_colecao(con, com_foil=False)
    totais = collection.get_many(con)
    ids_cm = {r["printing_id"]: r["cardmarket_id"] for r in
              con.execute("SELECT printing_id, cardmarket_id FROM catalog.cardtrader_map")}
    # Os decks MONTADOS que usam a carta (2026-09-24: um desmontado não usa
    # nada). É o mesmo `uso_por_carta` da grelha da Coleção — não há segunda
    # resposta a «que deck usa esta carta».
    try:
        uso = decks.uso_por_carta(con)
    except sqlite3.OperationalError:
        uso = {}

    out: list[dict] = []
    for r in con.execute(
        "SELECT p.* FROM sale_lines s JOIN catalog.printings p "
        "ON p.printing_id = s.printing_id ORDER BY p.set_id, p.api_sort"
    ):
        pid = r["printing_id"]
        qty = atuais[pid]
        linha_tr = tr.get(pid)
        cents = linha_tr["cents"] if linha_tr else None
        velho, idade = _velho(linha_tr["updated_at"] if linha_tr else None, dias)
        mkt = mercado.get(pid) or {}
        nome_mercado = mkt.get("name") or r["name"]
        tem = totais.get(pid, 0)
        em_decks = [d["deck"] for d in uso.get(r["card_key"], [])]
        out.append({
            "printing_id": pid,
            "name": r["name"], "code": r["public_code"],
            "set": r["set_id"], "set_name": config.set_name(r["set_id"]),
            "cn": r["collector_number"],
            "kind": r["variant_kind"], "label": r["variant_label"],
            "rarity": r["base_rarity"] or "?",
            "landscape": (r["orientation"] or "").lower() == "landscape",
            "img": f"img/{pid}.webp",
            "cdn": r["image_medium"] or r["image_large"] or r["image_url"],
            "qty": qty,
            # O TREND, dele. É este e só este que entra na conta.
            "trend": cents,
            "trend_em": linha_tr["updated_at"] if linha_tr else None,
            "trend_velho": velho, "trend_dias": idade,
            "subtotal": (cents or 0) * qty,
            # O preço do CardTrader, SÓ COMO REFERÊNCIA. Nunca entra no total.
            "price": precos.get(pid),
            "market_name": nome_mercado,
            "market_set": mkt.get("set"),
            "cardmarket_id": ids_cm.get(pid),
            "url": mercados.cardmarket(nome_mercado, ids_cm.get(pid),
                                       op=op_links)["url"],
            "url_busca": mercados.cardmarket_busca(nome_mercado, op_links),
            # Avisos — marcam, não bloqueiam.
            "have": tem, "na_colecao": na_colecao.get(pid, 0),
            "a_mais_do_que_tens": max(0, qty - tem),
            "em_decks": em_decks,
        })
    return out


def procurar(con: sqlite3.Connection, q: str, limite: int = 20) -> list[dict]:
    """Impressões do catálogo cujo nome ou código casa com `q`.

    É como ele junta uma carta de uma edição que não tem aberta na Coleção — a
    grelha só tem uma edição de cada vez em memória, e a venda é de tudo. Vive
    no servidor (o site publicado não tem quem responda, e lá a venda é só de
    leitura).

    As que ele TEM aparecem primeiro: está com as cartas na mão.
    """
    q = (q or "").strip().lower()
    if len(q) < 2:
        return []
    tidas = collection.get_many(con)
    na_venda = linhas(con)
    like = f"%{q}%"
    rows = con.execute(
        "SELECT * FROM catalog.printings WHERE lower(name) LIKE ? "
        "OR lower(public_code) LIKE ? OR lower(printing_id) LIKE ? "
        "ORDER BY set_id, api_sort LIMIT 200", (like, like, like)).fetchall()
    rows.sort(key=lambda r: (-tidas.get(r["printing_id"], 0),
                             config.set_order(r["set_id"]), r["api_sort"]))
    return [{"printing_id": r["printing_id"], "name": r["name"],
             "code": r["public_code"], "set": r["set_id"],
             "set_name": config.set_name(r["set_id"]),
             "label": r["variant_label"],
             "have": tidas.get(r["printing_id"], 0),
             "na_venda": na_venda.get(r["printing_id"], 0)} for r in rows[:limite]]


def conta(lista: list[dict]) -> dict:
    """O total da venda. **Só as linhas com Trend contam.**

    Uma linha por preencher vale zero e aparece em `sem_trend` — nunca se
    substitui pelo preço do CardTrader nem por coisa nenhuma.
    """
    com = [x for x in lista if x["trend"] is not None]
    sem = [x for x in lista if x["trend"] is None]
    return {
        "lines": len(lista),
        "copies": sum(x["qty"] for x in lista),
        "cards": len({x["printing_id"] for x in lista}),
        "cents": sum(x["subtotal"] for x in com),
        "sem_trend": len(sem),
        "sem_trend_copies": sum(x["qty"] for x in sem),
        "trend_velho": sum(1 for x in com if x["trend_velho"]),
        "avisos_stock": sum(1 for x in lista if x["a_mais_do_que_tens"]),
        "em_decks": sum(1 for x in lista if x["em_decks"]),
    }


def texto(lista: list[dict], t: dict | None = None) -> str:
    """A conta em texto, para copiar e mostrar a quem compra.

    Uma linha por carta — quantidade, nome, edição, número, Trend unitário e
    subtotal — e o total no fim. As linhas sem Trend dizem-no pelo nome, em
    vez de aparecerem a 0,00 € como se fossem de graça.
    """
    t = t or conta(lista)
    eur = lambda c: f"{c / 100:,.2f} €".replace(",", " ").replace(".", ",")  # noqa: E731
    # «1 linhas» numa conta que se mostra a alguém lê-se como um contador
    # partido — é a mesma correcção de 2026-09-09 no site.
    plural = lambda n, um, muitos: f"{n} {um if n == 1 else muitos}"  # noqa: E731
    linhas_txt = []
    for x in lista:
        codigo = cardmarket.codigo(x["code"])
        nome = f"{x['qty']}x {x['name']} ({codigo})"
        if x["trend"] is None:
            linhas_txt.append(f"{nome} — sem Trend")
        else:
            linhas_txt.append(f"{nome} — {eur(x['trend'])} x {x['qty']} = "
                              f"{eur(x['subtotal'])}")
    linhas_txt.append("")
    linhas_txt.append(f"TOTAL: {eur(t['cents'])}  "
                      f"({plural(t['copies'], 'carta', 'cartas')}, "
                      f"{plural(t['lines'], 'linha', 'linhas')})")
    if t["sem_trend"]:
        linhas_txt.append(f"{plural(t['sem_trend'], 'linha', 'linhas')} sem Trend — "
                          f"{'não está' if t['sem_trend'] == 1 else 'não estão'} no total.")
    linhas_txt.append("Preços: Trend do Cardmarket.")
    return "\n".join(linhas_txt)


def payload(con: sqlite3.Connection, cfg: dict | None = None,
            editable: bool = True) -> dict:
    cfg = cfg or config.load()
    lista = itens(con, cfg)
    t = conta(lista)
    return {"editable": editable, "generated_at": _now(),
            "items": lista, "totals": t, "texto": texto(lista, t),
            "trend_valido_dias": opcoes(cfg)["trend_valido_dias"],
            "historico": historico(con, limit=5)}


# ---------------------------------------------------------------------------
# «Marcar como vendidas» — o único sítio que baixa cópias
# ---------------------------------------------------------------------------


def vender(con: sqlite3.Connection, confirmar: bool = False,
           source: str = "web", cfg: dict | None = None) -> dict:
    """Fecha a venda: baixa as cópias, escreve o registo, esvazia a lista.

    **Nunca é automático** — `confirmar=False` levanta `PrecisaConfirmar` sem
    tocar em nada. Cada linha passa pelo `collection.adjust` (portanto fica na
    `ops`, dá para desfazer, e o `locais.ajustar_ao_total` tira a cópia de
    onde ela estiver) e deixa uma linha na `sale_log` com o Trend que estava
    em vigor — a conta de uma venda antiga não muda quando o Trend mudar.

    Uma carta de que ele tenha menos cópias do que está a vender desce só o
    que há (o `adjust` trava no zero) e o resultado diz quanto faltou.
    """
    cfg = cfg or config.load()
    lista = itens(con, cfg)
    if not lista:
        raise VendaVazia("a venda está vazia")
    if not confirmar:
        raise PrecisaConfirmar(
            f"«marcar como vendidas» baixa {sum(x['qty'] for x in lista)} cópias "
            f"da coleção — confirma primeiro")

    sale_id = _now()
    feitas = []
    for x in lista:
        res = collection.adjust(con, x["printing_id"], -x["qty"], source=source)
        con.execute(
            "INSERT INTO sale_log (ts, sale_id, printing_id, qty, unit_cents, source) "
            "VALUES (?,?,?,?,?,?)",
            (_now(), sale_id, x["printing_id"], -res["applied"], x["trend"], source))
        feitas.append({"printing_id": x["printing_id"], "name": x["name"],
                       "code": x["code"], "qty": x["qty"],
                       "baixadas": -res["applied"],
                       "em_falta": x["qty"] + res["applied"],
                       "unit_cents": x["trend"], "qty_after": res["qty"],
                       "op_id": res["op_id"]})
    t = conta(lista)
    con.execute("DELETE FROM sale_lines")
    return {"sale_id": sale_id, "itens": feitas, "totals": t,
            "copies": sum(f["baixadas"] for f in feitas),
            "em_falta": sum(f["em_falta"] for f in feitas)}


def historico(con: sqlite3.Connection, limit: int = 10) -> list[dict]:
    """As últimas vendas fechadas, uma linha por venda."""
    return [dict(r) for r in con.execute(
        "SELECT sale_id, MIN(ts) AS ts, COUNT(*) AS lines, SUM(qty) AS copies, "
        "       SUM(COALESCE(unit_cents,0) * qty) AS cents, "
        "       SUM(CASE WHEN unit_cents IS NULL THEN 1 ELSE 0 END) AS sem_trend "
        "FROM sale_log GROUP BY sale_id ORDER BY ts DESC LIMIT ?", (limit,))]


def venda_do_log(con: sqlite3.Connection, sale_id: str) -> list[dict]:
    return [dict(r) for r in con.execute(
        "SELECT l.*, p.name, p.public_code FROM sale_log l "
        "LEFT JOIN catalog.printings p ON p.printing_id = l.printing_id "
        "WHERE l.sale_id = ? ORDER BY l.id", (sale_id,))]

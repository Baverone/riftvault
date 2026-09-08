"""A aba "A subir": o que ainda falta do master set e está a ficar mais caro.

Mudou a 2026-09-08, a pedido do André: *"confere todas as cartas de Riftbound
de masterset e as que subirem pelo menos 10% assinalas; na página ordenas por %
de um lado e por valor no outro; quando já tenho as cartas, deixas de seguir —
isto vai servir só para o que eu ainda não tenho."*

Antes seguia o Riftbound inteiro, incluindo o que ele já tinha, e limitava-se a
marcar as que lhe tocavam. Agora o que ele já tem sai da lista: a pergunta
passou a ser só *o que é que me está a fugir de preço antes de eu o comprar*.

ÂMBITO — "masterset"
    O "masterset" não é uma edição: no riftvault é a **métrica 2**, o alvo por
    IMPRESSÃO (ver `metrics.master_target` / `metrics.e_master`). O âmbito desta
    aba são exatamente as impressões que entram na percentagem de set completo
    da Coleção, nas cinco edições. Desde a segunda decisão de 2026-09-08 são os
    três blocos dela — a sequência do master set em playset, as runas especiais
    a 1 e as artes alternativas a 1 — e fica de fora o mesmo que fica fora da
    percentagem: os tokens (`master_set.fora`) e tudo o que tenha alvo 0. Assim
    a página mede a mesma coisa que as barras de progresso — seguir cartas que
    não contam para a coleção seria seguir outra coisa.

O QUE É "AINDA NÃO TENHO"
    A regra do master set, que é a mesma do filtro **Faltas** da grelha: a
    impressão conta enquanto `cópias + a caminho < alvo`. Uma Unit com 1 de 3
    ainda o obriga a comprar 2, por isso o preço dela ainda lhe interessa. O
    que vem a caminho conta como tido, como em toda a secção Faltas — senão a
    página mandava vigiar o que já está comprado.

    Põe-se `a_subir.regra_falta: "nenhuma"` para seguir só as que estão mesmo
    a zero cópias.

AS SIGNATURES E OS SHOWCASES FICAM DE FORA (André, 2026-09-08)
    *"No 'a subir', estás a pôr uma carta signed — não quero."* e, no mesmo
    dia, *"tira também os showcases"*. Nem umas nem outros entram nas listas de
    compra, tanto aqui como na lista completa do master set — são as duas
    listas para ele comprar, e o que ele não compra não tem lugar em nenhuma
    delas.

    **São dois critérios diferentes, e é por isso que a config tem dois
    campos.** A `signature` é um `variant_kind` — o sufixo `*` do código
    impresso. O `showcase` **não é**: é uma RARIDADE (`rarity`), e as 42 que
    saem daqui têm todas `variant_kind = base` — são as reimpressões showcase
    com número de coleção próprio (a ARMADILHA 2 do CLAUDE.md: `SFD-232/221`
    tem código de carta normal e raridade `showcase`). Filtrar showcases pelo
    tipo de impressão não apanharia nenhuma delas.

    `a_subir.excluir: {"tipos": ["signature"], "raridades": ["showcase"]}`.
    O `excluir_tipos` é o nome antigo e continua a ser lido (traduzido em
    `config._migrar_a_subir`, para haver uma leitura só do config).

    **As duas exclusões valem só na SEQUÊNCIA do master set** (`so_no_master`,
    ligado — ver `excluir`). Foram decididas de manhã, quando as artes
    alternativas estavam fora da coleção; à tarde ele pediu-as de volta, 1 de
    cada, e 54 das 102 têm raridade `showcase`. Deixá-las cair na exclusão
    apagava em silêncio a decisão nova.

    Isto é filtro DESTA página, não da métrica: o `metrics.e_master` não
    mexeu, por isso a percentagem de set completo da Coleção continua a contar
    as 36 signatures e os 42 showcases no denominador. A página diz sempre
    quantas impressões tirou **e por que critério** — uma lista que encolhe sem
    explicação parece um erro de contagem.

O PREÇO DE HÁ N DIAS
    O `price_history` só grava quando o preço MUDA. O preço em vigor no dia D
    é por isso o último registo com `day <= D`, e esse registo pode ser
    anterior à janela — comparar com o primeiro registo DENTRO da janela dava
    subidas a menos (era o que a versão antiga fazia).

    Quando não há registo nenhum antes do início da janela, usa-se o mais
    antigo que existe e marca-se `desde <data>`. O histórico ainda não cobre a
    janela e a página diz isso, em vez de fingir 30 dias.
"""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from . import cardmarket, config, metrics, pending

# Tudo isto se muda no `riftvault_config.json`, bloco "a_subir".
DEFAULTS: dict = {
    "janela_dias": 30,
    "janela_curta_dias": 7,
    "subida_minima_pct": 10.0,
    # Abaixo de 50 cêntimos um "+40%" são 20 cêntimos — é ruído do mercado, não
    # uma carta a valorizar. É o mesmo limiar da versão antiga desta aba.
    "preco_minimo_cents": 50,
    "regra_falta": "master",
    # O que não entra nas listas de compra (André, 2026-09-08: "estás a pôr uma
    # carta signed — não quero" e "tira também os showcases"). Dois campos
    # porque são duas perguntas: `tipos` é o `variant_kind` (o sufixo do código)
    # e `raridades` é a `rarity` da impressão — o showcase é raridade, não
    # variante. Não mexe na percentagem de master set, que continua a contá-las.
    # O `so_no_master` limita as duas exclusões à SEQUÊNCIA do master set — ver
    # `excluir()`.
    "excluir": {"tipos": ["signature"], "raridades": ["showcase"],
                "so_no_master": True},
    "urgencia": False,
    "urgencia_pesos": {"janela": 0.5, "curto": 1.0, "preco_relativo": 10.0},
    # NÃO VALIDADOS: nem a API da RiftScribe nem a do CardTrader dão o endereço
    # da página da carta, e daqui não houve rede para experimentar. São o
    # formato que se presume; se abrirem em 404, corrige-se aqui.
    "link_cardtrader": "https://www.cardtrader.com/cards/{blueprint_id}",
    "link_riftscribe": "https://riftscribe.gg/cards/{printing_id}",
}


def opcoes(cfg: dict | None = None) -> dict:
    cfg = cfg or config.load()
    out = dict(DEFAULTS)
    bruto = cfg.get("a_subir") or {}
    out.update({k: v for k, v in bruto.items() if not k.startswith("_")})
    # Os pesos são um dicionário dentro do dicionário: sem isto, mexer num peso
    # no config apagava os outros dois.
    pesos = dict(DEFAULTS["urgencia_pesos"])
    pesos.update(bruto.get("urgencia_pesos") or {})
    out["urgencia_pesos"] = pesos
    # O mesmo para o `excluir`: escrever só `{"raridades": []}` no config não
    # pode apagar em silêncio a exclusão das signatures.
    fora = dict(DEFAULTS["excluir"])
    fora.update(bruto.get("excluir") or {})
    out["excluir"] = fora
    return out


# ---------------------------------------------------------------------------
# Âmbito e carência
# ---------------------------------------------------------------------------


def masterset(con: sqlite3.Connection, cfg: dict | None = None) -> dict[str, dict]:
    """printing_id -> impressão, para as que contam para a coleção.

    O mesmo critério de `metrics.set_payload`, pela mesma função: alvo > 0 e
    `metrics.e_master`. Desde 2026-09-08 isso são os TRÊS blocos da Coleção —
    a sequência do master set em playset, as runas especiais a 1 e as artes
    alternativas a 1 — e deixa de fora os tokens. Cada impressão leva o `block`
    a que pertence, porque o `excluir()` a seguir pergunta por ele.
    """
    cfg = cfg or config.load()
    out: dict[str, dict] = {}
    for r in con.execute(
        "SELECT printing_id, set_id, collector_number, public_code, name, "
        "       variant_kind, variant_label, rarity, base_rarity, type, "
        "       is_token, orientation, image_medium, image_large, image_url "
        "FROM catalog.printings"
    ):
        alvo = metrics.master_target(r["printing_id"], r["variant_kind"], r["type"],
                                     bool(r["is_token"]), cfg)
        if alvo <= 0 or not metrics.e_master(r, cfg):
            continue
        out[r["printing_id"]] = {**dict(r), "target": alvo,
                                 "block": metrics.bloco(r, cfg)}
    return out


def criterios(fora) -> tuple[list[str], list[str]]:
    """`a_subir.excluir` -> (tipos, raridades), sem repetidos e pela ordem escrita.

    A ordem importa: é por ela que se atribui o motivo a cada impressão que sai.
    """
    fora = fora or {}
    tipos = list(dict.fromkeys(fora.get("tipos") or ()))
    raridades = list(dict.fromkeys(fora.get("raridades") or ()))
    return tipos, raridades


def excluir(escopo: dict[str, dict], fora) -> tuple[dict[str, dict], dict[str, dict]]:
    """Parte o âmbito em (o que fica, o que sai), por `variant_kind` E `rarity`.

    São dois critérios porque a `signature` é uma variante (o sufixo `*` do
    código) e o `showcase` é uma raridade — as 42 reimpressões showcase são
    `variant_kind = base` e nenhuma lista de variantes lhes tocava.

    **Só se aplicam à SEQUÊNCIA do master set** (`so_no_master`, ligado). As
    duas exclusões são de 2026-09-08 de manhã, quando as artes alternativas
    ainda estavam fora da coleção e as 42 que saíam eram todas reimpressões
    `variant_kind = base`. Na mesma tarde ele pediu-as de volta a 1 de cada —
    e 54 das 102 alt arts têm raridade `showcase`, por isso deixá-las cair
    aqui apagaria em silêncio a decisão nova. Os blocos das runas especiais e
    das artes alternativas são "1 de cada" e entram inteiros nas listas de
    compra. Põe-se `so_no_master: false` para as exclusões voltarem a valer em
    toda a coleção.

    Devolve as duas metades porque quem mostra tem de dizer quantas tirou: uma
    lista que encolhe sem explicação parece um erro de contagem. Cada impressão
    que sai leva o `excluded_by` — o PRIMEIRO critério que lhe bateu, tipos
    antes de raridades. É preciso escolher um: as 36 signatures também têm
    raridade `showcase`, e contá-las nos dois dava uma soma maior que o total.
    """
    tipos, raridades = criterios(fora)
    so_master = bool((fora or {}).get("so_no_master", True))
    ficam, saem = {}, {}
    for pid, v in escopo.items():
        if so_master and v.get("block", metrics.BLOCO_MASTER) != metrics.BLOCO_MASTER:
            ficam[pid] = v
        elif v["variant_kind"] in tipos:
            saem[pid] = {**v, "excluded_by": v["variant_kind"]}
        elif (v["rarity"] or "") in raridades:
            saem[pid] = {**v, "excluded_by": v["rarity"]}
        else:
            ficam[pid] = v
    return ficam, saem


def resumo_fora(saem: dict[str, dict], fora) -> dict:
    """O bloco que a página e o CLI mostram: quantas saíram, e por que critério."""
    tipos, raridades = criterios(fora)
    contagem: dict[str, int] = {}
    for v in saem.values():
        contagem[v["excluded_by"]] = contagem.get(v["excluded_by"], 0) + 1
    return {
        "excluded": len(saem),
        # `excluded_kinds` é o nome antigo e continua a ser só os tipos, para
        # não mudar o que já lê o payload.
        "excluded_kinds": sorted(tipos),
        "excluded_rarities": sorted(raridades),
        "excluded_by": [{"criterio": c, "n": contagem[c]}
                        for c in tipos + raridades if contagem.get(c)],
    }


def em_falta(con: sqlite3.Connection, escopo: dict[str, dict],
             regra: str = "master") -> dict[str, dict]:
    """Do âmbito, o que ele ainda não tem — com o que vem a caminho descontado.

    `regra`:
      "master"  — falta enquanto `cópias + a caminho < alvo` (o filtro Faltas).
      "nenhuma" — só as que estão a zero cópias.
    """
    tenho = {r["printing_id"]: r["qty"] for r in
             con.execute("SELECT printing_id, qty FROM copies WHERE qty > 0")}
    for pid, q in pending.open_qty(con).items():
        tenho[pid] = tenho.get(pid, 0) + q

    out: dict[str, dict] = {}
    for pid, info in escopo.items():
        n = tenho.get(pid, 0)
        falta = info["target"] - n if regra == "master" else (info["target"] if n == 0 else 0)
        if falta <= 0:
            continue
        out[pid] = {**info, "have": tenho.get(pid, 0), "missing": falta}
    return out


# ---------------------------------------------------------------------------
# Preços
# ---------------------------------------------------------------------------


def ponto(serie: list[tuple[str, int]], limite: str) -> tuple[str, int, bool]:
    """O preço em vigor em `limite`: (dia, cêntimos, cobre_a_janela).

    O último registo com `day <= limite`. Se o histórico só começa depois disso,
    devolve o mais antigo que existe e `False` — quem mostra tem de dizer
    "desde <data>", não inventar a janela toda.
    """
    anterior = None
    for dia, cents in serie:
        if dia > limite:
            break
        anterior = (dia, cents)
    if anterior:
        return anterior[0], anterior[1], True
    return serie[0][0], serie[0][1], False


def medianas_por_raridade(con: sqlite3.Connection) -> dict[str, int]:
    """Preço mediano de cada raridade — o denominador do "preço relativo".

    Pela raridade da BASE, como os contadores da Coleção: a `showcase` não é
    uma raridade de jogo, é um tratamento, e usá-la distorcia a mediana.
    """
    vals: dict[str, list[int]] = {}
    for r in con.execute(
        "SELECT p.base_rarity AS r, pl.price_cents AS c FROM catalog.printings p "
        "JOIN catalog.price_latest pl ON pl.printing_id = p.printing_id "
        "WHERE pl.price_cents IS NOT NULL"
    ):
        vals.setdefault(r["r"] or "?", []).append(r["c"])
    out = {}
    for k, v in vals.items():
        v.sort()
        meio = len(v) // 2
        out[k] = v[meio] if len(v) % 2 else (v[meio - 1] + v[meio]) // 2
    return out


# ---------------------------------------------------------------------------
# A vista
# ---------------------------------------------------------------------------


def calcular(con: sqlite3.Connection, hoje: date | None = None) -> dict:
    """A aba inteira: âmbito, carência, subidas e as duas ordenações."""
    cfg = config.load()
    o = opcoes(cfg)
    hoje = hoje or date.today()
    janela, curta = int(o["janela_dias"]), int(o["janela_curta_dias"])
    min_pct, min_cents = float(o["subida_minima_pct"]), int(o["preco_minimo_cents"])
    pesos = o["urgencia_pesos"]

    escopo, excluidas = excluir(masterset(con, cfg), o["excluir"])
    falta = em_falta(con, escopo, str(o["regra_falta"]))
    mercado = cardmarket.versoes(con)

    dias = [r["day"] for r in con.execute(
        "SELECT DISTINCT day FROM prices.price_history ORDER BY day")]
    precos = {r["printing_id"]: r["price_cents"] for r in con.execute(
        "SELECT printing_id, price_cents FROM catalog.price_latest "
        "WHERE price_cents IS NOT NULL")}
    blueprints = {r["printing_id"]: r["blueprint_id"] for r in con.execute(
        "SELECT printing_id, blueprint_id FROM catalog.cardtrader_map")}

    # O histórico inteiro, filtrado em Python: são poucas linhas (uma por
    # mudança de preço) e não há limite de variáveis de um `IN (?,?,...)` com
    # centenas de impressões.
    series: dict[str, list[tuple[str, int]]] = {}
    for r in con.execute(
        "SELECT printing_id, day, price_cents FROM prices.price_history "
        "ORDER BY printing_id, day"
    ):
        if r["printing_id"] in falta:
            series.setdefault(r["printing_id"], []).append((r["day"], r["price_cents"]))

    medianas = medianas_por_raridade(con)
    limite = (hoje - timedelta(days=janela)).isoformat()
    limite_curto = (hoje - timedelta(days=curta)).isoformat()

    comparaveis = 0
    itens = []
    for pid, info in falta.items():
        serie = series.get(pid)
        agora = precos.get(pid)
        if not serie or agora is None:
            continue
        comparaveis += 1
        if agora < min_cents:
            continue
        d0, antes, cobre = ponto(serie, limite)
        if antes <= 0:
            continue
        pct = (agora - antes) / antes * 100
        if pct < min_pct:
            continue
        d7, antes7, cobre7 = ponto(serie, limite_curto)
        pct7 = (agora - antes7) / antes7 * 100 if antes7 > 0 else None

        rar = info["base_rarity"] or "?"
        mediana = medianas.get(rar) or agora
        urgencia = (pct * float(pesos["janela"])
                    + (pct7 or 0.0) * float(pesos["curto"])
                    + (agora / mediana) * float(pesos["preco_relativo"]))

        mkt = mercado.get(pid) or {}
        itens.append({
            "printing_id": pid,
            "name": info["name"],
            "code": info["public_code"],
            "set": info["set_id"],
            "set_name": config.set_name(info["set_id"]),
            "cn": info["collector_number"],
            "kind": info["variant_kind"],
            "label": info["variant_label"],
            "rarity": rar,
            "landscape": (info["orientation"] or "").lower() == "landscape",
            "img": f"img/{pid}.webp",
            "cdn": info["image_medium"] or info["image_large"] or info["image_url"],
            "from_cents": antes, "to_cents": agora,
            "pct": round(pct, 1), "since": d0, "full_window": cobre,
            # A janela curta pode não ter ponto nenhum antes do limite; nesse
            # caso o `since` dela diz de quando é a leitura que se usou.
            "pct_short": None if pct7 is None else round(pct7, 1),
            "short_since": d7, "short_full": cobre7,
            "have": info["have"], "target": info["target"], "missing": info["missing"],
            # O que já custou esperar, nas cópias que ainda lhe faltam.
            "extra_cents": (agora - antes) * info["missing"],
            "buy_cents": agora * info["missing"],
            # Os campos que a lista do Cardmarket precisa. São os MESMOS nomes
            # que a lista do master set usa, para o gerador ser um só — em
            # Python (`cardmarket.linha`) e em JavaScript (`cmLinha`).
            "price": agora, "total": agora * info["missing"],
            # Só vai quando é MESMO diferente do nosso ("Darius - Trifarian" vs
            # "Darius, Trifarian"); o gerador cai no `name` quando falta.
            "market_name": mkt.get("name") if mkt.get("name") != info["name"] else None,
            "market_set": mkt.get("set"),
            "v": mkt.get("v"), "n_versions": mkt.get("n", 1),
            "foil_only": bool(mkt.get("foil_only")),
            "urgency": round(urgencia, 1),
            "url_cardtrader": (o["link_cardtrader"].format(blueprint_id=blueprints[pid])
                               if pid in blueprints and o.get("link_cardtrader") else None),
            "url_riftscribe": (o["link_riftscribe"].format(printing_id=pid)
                               if o.get("link_riftscribe") else None),
        })

    # As duas ordenações saem daqui, não do cliente: os critérios de desempate
    # ficam num sítio só e dá para os testar.
    itens.sort(key=lambda i: (-i["pct"], -i["to_cents"], i["name"]))
    for n, it in enumerate(itens, 1):
        it["rank_pct"] = n
    for n, it in enumerate(sorted(itens, key=lambda i: (-i["to_cents"], -i["pct"], i["name"])), 1):
        it["rank_valor"] = n

    raridades: dict[str, int] = {}
    for it in itens:
        raridades[it["rarity"]] = raridades.get(it["rarity"], 0) + 1

    return {
        "ready": comparaveis > 0,
        "window_days": janela, "short_days": curta,
        "min_pct": min_pct, "min_cents": min_cents,
        "rule": str(o["regra_falta"]),
        "scope": {
            "printings": len(escopo),
            "sets": sorted({v["set_id"] for v in escopo.values()}),
            # Quantas impressões o `excluir` tirou do master set, e por que
            # critério. A página diz os números — uma lista que encolhe sem
            # explicação parece um erro de contagem.
            **resumo_fora(excluidas, o["excluir"]),
        },
        # Quantas segue (em falta, dentro do âmbito) e de quantas há com que
        # comparar. A diferença é histórico que ainda não existe.
        "tracked": len(falta),
        "comparable": comparaveis,
        "days_recorded": len(dias), "first": dias[0] if dias else None,
        "urgencia": bool(o["urgencia"]),
        "pesos": pesos,
        "rarities": [{"rarity": k, "n": v} for k, v in
                     sorted(raridades.items(),
                            key=lambda kv: (metrics.RARITY_ORDER.index(kv[0])
                                            if kv[0] in metrics.RARITY_ORDER else 99, kv[0]))],
        "totals": {
            "cards": len(itens),
            "copies": sum(i["missing"] for i in itens),
            # O que custa comprar o que falta destas, ao preço de hoje.
            "cents": sum(i["buy_cents"] for i in itens),
            # E quanto disso é subida — o que custou não ter comprado antes.
            "extra_cents": sum(i["extra_cents"] for i in itens),
        },
        "items": itens,
    }


# ---------------------------------------------------------------------------
# A lista completa: tudo o que falta do master set
# ---------------------------------------------------------------------------


def master_faltas(con: sqlite3.Connection, cfg: dict | None = None) -> dict:
    """Tudo o que falta do master set, para ele comprar de uma vez se quiser.

    A aba «A subir» responde a "o que é que me está a fugir de preço"; esta
    responde a "e se eu quisesse fechar isto tudo". Mesmo âmbito, mesma regra de
    carência e as mesmas exclusões — só não há filtro de subida.

    Sai ordenada por EDIÇÃO e NÚMERO DE COLEÇÃO (pedido do André, 2026-09-08):
    é a ordem por que as cartas estão no binder e nas páginas de venda, não a do
    preço.

    Sem imagens de propósito: são centenas de linhas e o `faltas.json` é
    descarregado inteiro a cada visita.
    """
    cfg = cfg or config.load()
    o = opcoes(cfg)
    escopo, excluidas = excluir(masterset(con, cfg), o["excluir"])
    falta = em_falta(con, escopo, str(o["regra_falta"]))
    mercado = cardmarket.versoes(con)
    precos = {r["printing_id"]: r["price_cents"] for r in con.execute(
        "SELECT printing_id, price_cents FROM catalog.price_latest "
        "WHERE price_cents IS NOT NULL")}

    por_set: dict[str, dict] = {}
    for pid, info in falta.items():
        mkt = mercado.get(pid) or {}
        preco = precos.get(pid)
        d = por_set.setdefault(info["set_id"], {
            "set": info["set_id"], "name": config.set_name(info["set_id"]),
            "cards": 0, "copies": 0, "cents": 0, "items": []})
        # O nome de mercado só vai quando é MESMO diferente do nosso ("Darius -
        # Trifarian" vs "Darius, Trifarian"). São 695 linhas e o `faltas.json`
        # é descarregado inteiro a cada visita; o `cardmarket.linha` já cai no
        # `name` quando este falta.
        nome_mercado = mkt.get("name") if mkt.get("name") != info["name"] else None
        item = {
            "printing_id": pid, "name": info["name"],
            "code": info["public_code"], "set": info["set_id"],
            "cn": info["collector_number"],
            "kind": info["variant_kind"], "label": info["variant_label"],
            "rarity": info["base_rarity"] or "?",
            "have": info["have"], "target": info["target"],
            "missing": info["missing"],
            "price": preco, "total": (preco or 0) * info["missing"],
            # Os mesmos campos de mercado que os itens da aba «A subir», para o
            # gerador do Cardmarket ser um só.
            "market_name": nome_mercado, "market_set": mkt.get("set"),
            "v": mkt.get("v"), "n_versions": mkt.get("n", 1),
            "foil_only": bool(mkt.get("foil_only")),
            # Não há Δ nesta lista: não é sobre preço a subir.
            "pct": None,
        }
        d["items"].append(item)
        d["cards"] += 1
        d["copies"] += info["missing"]
        d["cents"] += item["total"]

    sets = sorted(por_set.values(), key=lambda d: (config.set_order(d["set"]), d["set"]))
    for d in sets:
        d["items"].sort(key=lambda x: (x["cn"], x["code"]))

    # Quantas não têm preço no CardTrader: o total é sobre as outras, e dizê-lo
    # é a diferença entre "custa isto" e "custa pelo menos isto".
    sem_preco = sum(1 for d in sets for x in d["items"] if x["price"] is None)
    return {
        "cards": sum(d["cards"] for d in sets),
        "copies": sum(d["copies"] for d in sets),
        "cents": sum(d["cents"] for d in sets),
        "no_price": sem_preco,
        "rule": str(o["regra_falta"]),
        "scope": {
            "printings": len(escopo),
            **resumo_fora(excluidas, o["excluir"]),
        },
        "sets": sets,
    }

"""A aba "A subir": o que ainda falta do master set e está a ficar mais caro.

Mudou a 2026-09-08, a pedido do André: *"confere todas as cartas de Riftbound
de masterset e as que subirem pelo menos 10% assinalas; na página ordenas por %
de um lado e por valor no outro; quando já tenho as cartas, deixas de seguir —
isto vai servir só para o que eu ainda não tenho."*

Antes seguia o Riftbound inteiro, incluindo o que ele já tinha, e limitava-se a
marcar as que lhe tocavam. Agora o que ele já tem sai da lista: a pergunta
passou a ser só *o que é que me está a fugir de preço antes de eu o comprar*.

ÂMBITO — SÓ O MASTER SET (2026-09-15)
    O "masterset" não é uma edição: no riftvault é a **métrica 2**, o alvo por
    IMPRESSÃO (ver `metrics.master_target`). As listas de compra — esta aba, a
    lista completa do «Master set», as wantlists do fim de cada edição e as
    por nível — são **só o bloco 1**, o que conta para a percentagem
    (`metrics.e_master`). André, 2026-09-15: *"mas sobrenumeradas não entram
    na wantlist, nem na % de coleção completa; apenas pedi para ser feito
    track de playset para eu saber exatamente quantas tenho"*.

    A coleção extra — as artes alternativas, as runas especiais, as
    sobrenumeradas, as promos — tem alvo de playset **para ele ver «tenho 1 de
    3» na grelha**, não porque queira comprar. Acompanhar não é querer comprar.
    Na noite de 2026-09-14 ela tinha entrado inteira nas listas (a leitura foi
    «um alvo sem lista de compra é um alvo sem maneira de o cumprir») e a
    wantlist passou de 3 337 € para 30 646 €, com 7 202 € em três Baron Nashor
    que ele disse a 2026-09-05 que nunca compraria. Fica de fora por
    `listas_de_compra.so_master_set` (ver `so_master_set`), e a página diz
    quantas impressões tirou e de que bloco.

    Continuam de fora, como sempre, o que está escondido
    (`master_set.escondidas`, os tokens e as signatures) e o que tenha alvo 0.

O QUE É "AINDA NÃO TENHO"
    A regra do master set, que é a mesma do filtro **Faltas** da grelha: a
    impressão conta enquanto `cópias + a caminho < alvo`. Uma Unit com 1 de 3
    ainda o obriga a comprar 2, por isso o preço dela ainda lhe interessa. O
    que vem a caminho conta como tido, como em toda a secção Faltas — senão a
    página mandava vigiar o que já está comprado.

    Põe-se `a_subir.regra_falta: "nenhuma"` para seguir só as que estão mesmo
    a zero cópias.

AS SIGNATURES JÁ NEM CHEGAM AQUI (André, 2026-09-09 e 2026-09-11)
    *"Das coleções tira as signatures, fazemos 1 Alt Art de cada mas as
    signature não."* As signatures estão ESCONDIDAS — `master_set.escondidas`
    leva o `"*"` — e por isso não estão no âmbito desta página: o `masterset`
    abaixo pergunta ao `metrics.e_colecao`. A exclusão que se segue continua a
    listá-las de propósito (é a mesma frase dele de 2026-09-08, e vale se um
    dia elas voltarem à página), mas hoje já não tira nenhuma — o `resumo_fora`
    conta o que saiu mesmo.

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
    apagava em silêncio a decisão nova. Hoje a sequência já não tem nenhuma
    impressão de raridade `showcase` (são todas sobrenumeradas, que estão no
    bloco delas) e as duas exclusões tiram zero — ficam para o caso de
    voltarem.

    **A coleção extra NÃO entra nas listas de compra** (2026-09-15, ver o
    ÂMBITO acima). O `a_subir.excluir.blocos` — a lista de blocos da grelha a
    tirar das listas — é de 2026-09-14 e continua a ser lido, mas com o
    `so_master_set` ligado já não tira nada que não estivesse fora: fica para
    quem desligue o botão e queira comprar só parte da coleção extra.

    Isto é filtro DESTA página, não da métrica: a percentagem de set completo
    não sabe destas listas. A página diz sempre quantas impressões tirou **e
    por que critério** — uma lista que encolhe sem explicação parece um erro
    de contagem.

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

from . import cardmarket, config, locais, metrics, pending

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
    # `excluir()`. O `blocos` tira blocos inteiros da grelha (`overnumbered`,
    # `alt_art`, …) das listas de compra — desde 2026-09-15 a coleção extra
    # inteira já sai pelo `listas_de_compra.so_master_set`, e isto só faz
    # diferença com esse botão desligado.
    "excluir": {"tipos": ["signature"], "raridades": ["showcase"],
                "so_no_master": True, "blocos": []},
    "urgencia": False,
    "urgencia_pesos": {"janela": 0.5, "curto": 1.0, "preco_relativo": 10.0},
    # NÃO VALIDADOS: nem a API da RiftScribe nem a do CardTrader dão o endereço
    # da página da carta, e daqui não houve rede para experimentar. São o
    # formato que se presume; se abrirem em 404, corrige-se aqui.
    "link_cardtrader": "https://www.cardtrader.com/cards/{blueprint_id}",
    "link_riftscribe": "https://riftscribe.gg/cards/{printing_id}",
}

# Bloco `listas_de_compra` do config — vale para TODAS as listas de compra
# (esta aba, o «Master set», as wantlists por edição e por nível), por isso não
# vive dentro do `a_subir.excluir`, que tem nome de uma aba só.
LISTAS_DEFAULTS: dict = {
    # André, 2026-09-15: "sobrenumeradas não entram na wantlist, nem na % de
    # coleção completa; apenas pedi para ser feito track de playset para eu
    # saber exatamente quantas tenho". Ligado, as listas são só o bloco 1.
    "so_master_set": True,
}


def so_master_set(cfg: dict | None = None) -> bool:
    """As listas de compra são só o master set (bloco 1)?

    É a frase dele de 2026-09-15: a coleção extra tem alvo de playset para ele
    VER quantas tem, não para comprar. Muda-se em
    `listas_de_compra.so_master_set`; sem ficheiro de config vale o mesmo, para
    um riftvault sem config não medir outra coisa.
    """
    cfg = cfg or config.load()
    bruto = cfg.get("listas_de_compra") or {}
    return bool(bruto.get("so_master_set", LISTAS_DEFAULTS["so_master_set"]))


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
    out["so_master_set"] = so_master_set(cfg)
    return out


# ---------------------------------------------------------------------------
# Âmbito e carência
# ---------------------------------------------------------------------------


def masterset(con: sqlite3.Connection, cfg: dict | None = None) -> dict[str, dict]:
    """printing_id -> impressão, para as que estão na página da Coleção.

    O mesmo critério de `metrics.set_payload`, pela mesma função: alvo > 0 e
    `metrics.e_colecao` — o master set E a coleção extra, sem as escondidas
    (tokens, signatures). Cada impressão leva o `block` a que pertence, porque
    é o `excluir()` a seguir que tira a coleção extra das listas
    (`so_master_set`, 2026-09-15) — sai daqui inteira para a página poder
    dizer quantas tirou e de que bloco.
    """
    cfg = cfg or config.load()
    out: dict[str, dict] = {}
    for r in con.execute(
        "SELECT printing_id, set_id, collector_number, public_code, name, "
        "       variant_kind, variant_label, rarity, base_rarity, type, "
        "       is_token, orientation, image_medium, image_large, image_url "
        "FROM catalog.printings"
    ):
        alvo = metrics.alvo(r, cfg)
        if alvo <= 0 or not metrics.e_colecao(r, cfg):
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


def blocos_fora(fora, so_master: bool | None = None) -> list[str]:
    """Os blocos da grelha que não entram nas listas de compra, pela ordem da grelha.

    Com o `so_master_set` ligado (2026-09-15, o default) é a coleção extra
    inteira — todos os blocos menos o master set —, e o `a_subir.excluir.blocos`
    de 2026-09-14 só acrescenta o que já lá está. Desligado, é só essa lista.
    Cada bloco conta como critério próprio no `resumo_fora`, para a página
    dizer «92 sobrenumeradas» e não um número sem nome.
    """
    if so_master is None:
        so_master = so_master_set()
    escritos = list(dict.fromkeys((fora or {}).get("blocos") or ()))
    if not so_master:
        return escritos
    todos = [b for b, _ in metrics.BLOCOS if b != metrics.BLOCO_MASTER]
    return todos + [b for b in escritos if b not in todos]


def excluir(escopo: dict[str, dict], fora,
            so_master: bool | None = None) -> tuple[dict[str, dict], dict[str, dict]]:
    """Parte o âmbito em (o que fica, o que sai): por BLOCO, `variant_kind` e `rarity`.

    **Primeiro o bloco** (2026-09-15): com `listas_de_compra.so_master_set`
    ligado — o default, e `so_master` a `None` lê-o do config — tudo o que não
    é o master set sai, com o bloco por motivo. É a frase dele: *"apenas pedi
    para ser feito track de playset para eu saber exatamente quantas tenho"*
    — a coleção extra acompanha-se na grelha, não se compra. Desligado, sai só
    o que estiver escrito em `a_subir.excluir.blocos`.

    Depois os dois critérios de 2026-09-08, porque a `signature` é uma
    variante (o sufixo `*` do código) e o `showcase` é uma raridade — as 42
    reimpressões showcase são `variant_kind = base` e nenhuma lista de
    variantes lhes tocava. **Só se aplicam à SEQUÊNCIA do master set**
    (`so_no_master`, ligado): foram decididos de manhã, quando as artes
    alternativas ainda estavam fora da coleção, e 54 das 102 alt arts têm
    raridade `showcase` — deixá-las cair aqui apagaria em silêncio a decisão da
    tarde. Hoje, com o bloco a sair primeiro, o `so_no_master` só faz
    diferença com o `so_master_set` desligado.

    Devolve as duas metades porque quem mostra tem de dizer quantas tirou: uma
    lista que encolhe sem explicação parece um erro de contagem. Cada impressão
    que sai leva o `excluded_by` — o PRIMEIRO critério que lhe bateu, blocos
    antes de tipos antes de raridades. É preciso escolher um: as 36 signatures
    também têm raridade `showcase`, e contá-las nos dois dava uma soma maior
    que o total.
    """
    tipos, raridades = criterios(fora)
    blocos = blocos_fora(fora, so_master)
    so_sequencia = bool((fora or {}).get("so_no_master", True))
    ficam, saem = {}, {}
    for pid, v in escopo.items():
        bloco = v.get("block", metrics.BLOCO_MASTER)
        if bloco in blocos:
            # Um bloco inteiro fora das listas: o motivo é o bloco, e a página
            # conta-o como tal («96 artes alternativas»).
            saem[pid] = {**v, "excluded_by": bloco}
        elif so_sequencia and bloco != metrics.BLOCO_MASTER:
            ficam[pid] = v
        elif v["variant_kind"] in tipos:
            saem[pid] = {**v, "excluded_by": v["variant_kind"]}
        elif (v["rarity"] or "") in raridades:
            saem[pid] = {**v, "excluded_by": v["rarity"]}
        else:
            ficam[pid] = v
    return ficam, saem


def resumo_fora(saem: dict[str, dict], fora, so_master: bool | None = None) -> dict:
    """O bloco que a página e o CLI mostram: quantas saíram, e por que critério.

    Os blocos levam o nome curto da grelha (`label`: «sobrenumeradas», «artes
    alternativas») a par do id — é o que ele lê no cabeçalho do bloco, e a
    página escreve o mesmo nome nos dois sítios.
    """
    if so_master is None:
        so_master = so_master_set()
    tipos, raridades = criterios(fora)
    blocos = blocos_fora(fora, so_master)
    contagem: dict[str, int] = {}
    for v in saem.values():
        contagem[v["excluded_by"]] = contagem.get(v["excluded_by"], 0) + 1
    return {
        "excluded": len(saem),
        # `excluded_kinds` é o nome antigo e continua a ser só os tipos, para
        # não mudar o que já lê o payload.
        "excluded_kinds": sorted(tipos),
        "excluded_rarities": sorted(raridades),
        # Só os blocos que tiraram alguma coisa: com o `so_master_set` a lista
        # é a grelha inteira e os vazios (tokens, signatures) não interessam.
        "excluded_blocks": sorted(b for b in blocos if contagem.get(b)),
        "so_master_set": bool(so_master),
        # Sem repetir nomes: o bloco `signature` da grelha e o tipo `signature`
        # do `excluir.tipos` escrevem-se igual, e listar o critério duas vezes
        # dava uma soma maior que o `excluded`.
        "excluded_by": [{"criterio": c, "n": contagem[c]}
                        for c in dict.fromkeys(blocos + tipos + raridades)
                        if contagem.get(c)],
        # O nome que a página escreve para cada bloco («sobrenumeradas», «artes
        # alternativas»): o mesmo do cabeçalho da grelha.
        "excluded_labels": {b: metrics.BLOCO_CURTO.get(b, b)
                            for b in blocos if contagem.get(b)},
    }


def em_falta(con: sqlite3.Connection, escopo: dict[str, dict],
             regra: str = "master", nivel: int | None = None) -> dict[str, dict]:
    """Do âmbito, o que ele ainda não tem — com o que vem a caminho descontado.

    `regra`:
      "master"  — falta enquanto `cópias + a caminho < alvo` (o filtro Faltas).
      "nenhuma" — só as que estão a zero cópias.

    `nivel` é o degrau da contagem por níveis (André, 2026-09-08): com `nivel=1`
    o alvo de cada impressão passa a `min(1, alvo)` — uma de cada —, com
    `nivel=2` a `min(2, alvo)`, e sem `nivel` fica o alvo inteiro (o playset da
    sequência). É o MESMO `min(k, alvo)` do `metrics.niveis`, para a wantlist do
    nível k pedir exactamente as cópias que essa contagem diz que faltam.

    O `target` que sai é o do nível — é o que a linha «tem 1 de 2» quer dizer —
    e o alvo inteiro vai no `full_target`, para não se perder.
    """
    # SÓ as cópias que estão nos binders de COLEÇÃO (André, 2026-09-10). As
    # listas de compra da Coleção medem a Coleção: uma cópia que está num deck
    # não fecha a página do binder, e por isso a impressão continua em falta.
    tenho = dict(locais.na_colecao(con))
    for pid, q in pending.open_qty(con).items():
        tenho[pid] = tenho.get(pid, 0) + q

    out: dict[str, dict] = {}
    for pid, info in escopo.items():
        n = tenho.get(pid, 0)
        alvo = min(int(nivel), info["target"]) if nivel else info["target"]
        falta = alvo - n if regra == "master" else (alvo if n == 0 else 0)
        if falta <= 0:
            continue
        out[pid] = {**info, "have": tenho.get(pid, 0), "missing": falta,
                    "target": alvo, "full_target": info["target"]}
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

    escopo, excluidas = excluir(masterset(con, cfg), o["excluir"], o["so_master_set"])
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
            # Quantas impressões o `excluir` tirou, e por que critério. A
            # página diz os números — uma lista que encolhe sem explicação
            # parece um erro de contagem.
            **resumo_fora(excluidas, o["excluir"], o["so_master_set"]),
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


def master_faltas(con: sqlite3.Connection, cfg: dict | None = None,
                  nivel: int | None = None) -> dict:
    """Tudo o que falta do master set, para ele comprar de uma vez se quiser.

    A aba «A subir» responde a "o que é que me está a fugir de preço"; esta
    responde a "e se eu quisesse fechar isto tudo". Mesmo âmbito, mesma regra de
    carência e as mesmas exclusões — só não há filtro de subida.

    Sai ordenada por EDIÇÃO e NÚMERO DE COLEÇÃO (pedido do André, 2026-09-08):
    é a ordem por que as cartas estão no binder e nas páginas de venda, não a do
    preço.

    `nivel` corta os alvos por `min(nivel, alvo)` — é a wantlist "até 1 de cada"
    e "até 2 de cada" da contagem por níveis. Sem ele é a lista inteira, com o
    playset na sequência, que é o que sempre foi.

    Sem imagens de propósito: são centenas de linhas e o `faltas.json` é
    descarregado inteiro a cada visita.
    """
    cfg = cfg or config.load()
    o = opcoes(cfg)
    escopo, excluidas = excluir(masterset(con, cfg), o["excluir"], o["so_master_set"])
    # O último degrau é o playset INTEIRO (`metrics.alvo_do_nivel`): pedir o
    # `--nivel 3` é pedir a lista de sempre, com as 12 da runa e não 3. Assim a
    # wantlist do degrau k continua a pedir exactamente as cópias que a
    # contagem do degrau k diz que faltam.
    if nivel is not None and int(nivel) >= metrics.niveis_max(con, cfg):
        nivel = None
    falta = em_falta(con, escopo, str(o["regra_falta"]), nivel)
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
            # O alvo inteiro, quando a lista vem cortada por nível: o `target`
            # é o do nível («tem 1 de 2») e este continua a dizer o playset.
            **({"full_target": info["full_target"]}
               if info.get("full_target") != info["target"] else {}),
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
        "level": nivel,
        "scope": {
            "printings": len(escopo),
            **resumo_fora(excluidas, o["excluir"], o["so_master_set"]),
        },
        "sets": sets,
        # Os botões do separador «Quanto custa» e a ordem das raridades: vêm
        # daqui para o browser não ter uma segunda lista de edições nem uma
        # segunda ordem. A lista em si não muda — é a mesma, arrumada de outra
        # maneira pelo `por_raridade` (e pelo gémeo `qcGrupos` do app.js).
        "quanto_custa": {**edicoes_quanto_custa(con, cfg),
                         "rarity_order": list(RARIDADES_POR_PRECO),
                         # O corte do topo (2026-09-15): o número e as raridades
                         # vêm do config, para o `qcGrupos` do app.js cortar
                         # igual ao `por_raridade`.
                         "top": top_por_raridade(cfg)["n"],
                         "top_rarities": sorted(top_por_raridade(cfg)["raridades"])},
    }


# ---------------------------------------------------------------------------
# «Quanto custa»: um botão por edição, por raridade, por preço (2026-09-15)
# ---------------------------------------------------------------------------
#
# André: "na aba faltas, renomeia para algo que seja apelativo a ter atenção ao
# preço" / "fazes novamente para cada set (menos proving grounds) um botão" /
# "depois metes para cada raridade, as cartas por ordem de preço".
#
# NÃO É UMA LISTA NOVA. É o `master_faltas` — o mesmo âmbito (só o master set),
# a mesma regra de carência, as mesmas exclusões, os mesmos itens — só arrumado
# de outra maneira: por edição escolhida, por raridade, e dentro da raridade
# por preço. A percentagem, a wantlist e o valor da coleção não sabem disto.

# Configura-se no `riftvault_config.json`, bloco "quanto_custa".
QUANTO_CUSTA_DEFAULTS: dict = {
    # As edições SEM botão. O OGS (Proving Grounds) fica de fora a pedido dele
    # (2026-09-15: "para cada set (menos proving grounds) um botão"). As outras
    # nascem do catálogo — uma edição nova ganha botão sozinha.
    "sem_edicoes": ["OGS"],
    # O TOPO de cada raridade (2026-09-15, à tarde: "em cada edicao o top5 de
    # mais caras de comuns, e top5 de incomuns, e top5 de Raras" / "miticas e
    # AltArt nao precisa fazer isto"). Nas raridades de `raridades_com_top`
    # mostram-se só as `top_por_raridade` mais caras; as épicas — a raridade de
    # topo no catálogo da RiftScribe, não há «mítica» — não estão na lista e
    # mostram-se todas. É SÓ o que se vê: os subtotais e o total contam tudo.
    "top_por_raridade": 5,
    "raridades_com_top": ["rare", "uncommon", "common"],
}

# Da mais rara para a mais comum. O separador existe para ele reparar no
# preço, e a raridade é o primeiro sinal dele: as épicas custam mais, e
# vêm primeiro pela mesma razão por que dentro de cada raridade o mais caro vem
# primeiro. O que não estiver aqui («?», ou uma raridade nova) vai para o fim.
RARIDADES_POR_PRECO = ("epic", "rare", "uncommon", "common")

# O rótulo do grupo das que não têm oferta no CardTrader. Não é uma raridade:
# é a gaveta do fim, para elas não desaparecerem nem fingirem que custam zero.
SEM_OFERTA = "sem_oferta"


def quanto_custa_opcoes(cfg: dict | None = None) -> dict:
    cfg = cfg or config.load()
    return {**QUANTO_CUSTA_DEFAULTS, **(cfg.get("quanto_custa") or {})}


def edicoes_quanto_custa(con: sqlite3.Connection, cfg: dict | None = None) -> dict:
    """As edições com botão, pela ordem dos separadores, e as que ficam sem ele.

    Lê o CATÁLOGO, não uma lista escrita à mão: são as edições que existem,
    menos as de `quanto_custa.sem_edicoes`. As siglas são comparadas em
    maiúsculas para `ogs` no config valer o mesmo que `OGS`.
    """
    sem = {str(s).upper() for s in quanto_custa_opcoes(cfg)["sem_edicoes"]}
    todas = [r[0] for r in con.execute(
        "SELECT DISTINCT set_id FROM catalog.printings")]
    todas.sort(key=lambda s: (config.set_order(s), s))
    return {
        "sets": [{"set": s, "name": config.set_name(s)} for s in todas if s not in sem],
        "sem_edicoes": [s for s in todas if s in sem],
    }


def top_por_raridade(cfg: dict | None = None) -> dict:
    """O corte do topo: `{"n": 5, "raridades": {"rare", "uncommon", "common"}}`.

    `n` a 0 (ou `None`) desliga o corte. As raridades comparam-se em
    minúsculas, como o catálogo as escreve.
    """
    o = quanto_custa_opcoes(cfg)
    n = o.get("top_por_raridade")
    n = int(n) if n else 0
    if n < 0:
        raise ValueError(f"quanto_custa.top_por_raridade não pode ser negativo: {n}")
    return {"n": n, "raridades": {str(r).lower() for r in (o.get("raridades_com_top") or [])}}


def por_raridade(itens: list[dict], ordem: str = "desc", top: dict | None = None) -> dict:
    """Arruma os itens do `master_faltas` por raridade e, dentro dela, por preço.

    `ordem` é `"desc"` (do mais caro para o mais barato — a omissão, porque o
    que o faz reparar no preço é ver primeiro o que custa dinheiro) ou `"asc"`
    (para ir buscar os baratos todos de uma vez). Inverte só a ordem DENTRO de
    cada raridade; a ordem das raridades entre si é fixa
    (`RARIDADES_POR_PRECO`), para os cabeçalhos ficarem sempre no mesmo sítio.

    O preço que ordena é o de CADA CARTA (`price`, o unitário), que é o número
    que ele lê; o desempate é o total da linha e depois o código, para a ordem
    ser a mesma em Python e no browser. Uma carta SEM preço não entra em
    raridade nenhuma: vai para um grupo próprio no fim (`SEM_OFERTA`), com
    subtotal a `None` — não conta como zero.

    `top` (ver `top_por_raridade`) é o corte de 2026-09-15: nas raridades que
    ele nomeou só se MOSTRAM as `n` mais caras. O grupo leva todas as linhas
    na mesma — `items` é a lista inteira, e é dela que saem o subtotal, o
    total e a wantlist —, mais `top_ids` (as que se vêem fechado) e `hidden`
    (quantas ficaram de fora e quanto somam), para o rodapé dizer o que
    cortou. Cortar sem dizer o que se cortou escondia-lhe dinheiro. Um grupo
    que caiba inteiro não leva corte nenhum.

    Devolve os grupos e os totais do que recebeu: `cents` é a soma dos
    subtotais, e cada subtotal a soma dos `total` das linhas do grupo.
    """
    if ordem not in ("desc", "asc"):
        raise ValueError(f"ordem desconhecida: {ordem!r} (desc ou asc)")
    grupos: dict[str | None, list[dict]] = {}
    for it in itens:
        chave = None if it.get("price") is None else (it.get("rarity") or "?")
        grupos.setdefault(chave, []).append(it)

    def posicao(r):
        return RARIDADES_POR_PRECO.index(r) if r in RARIDADES_POR_PRECO else len(RARIDADES_POR_PRECO)

    raridades = sorted((r for r in grupos if r is not None), key=lambda r: (posicao(r), r))
    sinal = -1 if ordem == "desc" else 1
    saida = []
    for r in raridades:
        linhas = sorted(grupos[r], key=lambda x: (sinal * x["price"], sinal * (x["total"] or 0),
                                                  x["set"], x["cn"], x["code"]))
        g = {
            "rarity": r,
            "cards": len(linhas),
            "copies": sum(x["missing"] for x in linhas),
            "cents": sum(x["total"] or 0 for x in linhas),
            "items": linhas,
        }
        n = top["n"] if top and r in top["raridades"] else 0
        if n and len(linhas) > n:
            # As mais caras são as mesmas seja qual for a ordem do ecrã: o
            # inversor muda como se lêem, não quais são.
            caras = sorted(linhas, key=lambda x: (-x["price"], -(x["total"] or 0),
                                                  x["set"], x["cn"], x["code"]))[:n]
            ids = {x["printing_id"] for x in caras}
            fora = [x for x in linhas if x["printing_id"] not in ids]
            g["top"] = n
            g["top_ids"] = [x["printing_id"] for x in linhas if x["printing_id"] in ids]
            g["hidden"] = {"cards": len(fora),
                           "copies": sum(x["missing"] for x in fora),
                           "cents": sum(x["total"] or 0 for x in fora)}
        saida.append(g)
    if None in grupos:
        linhas = sorted(grupos[None], key=lambda x: (x["set"], x["cn"], x["code"]))
        saida.append({
            "rarity": SEM_OFERTA,
            "cards": len(linhas),
            "copies": sum(x["missing"] for x in linhas),
            "cents": None,
            "items": linhas,
        })
    return {
        "order": ordem,
        "groups": saida,
        "cards": len(itens),
        "copies": sum(x["missing"] for x in itens),
        "cents": sum(g["cents"] or 0 for g in saida),
        "no_price": len(grupos.get(None, [])),
    }


def quanto_custa(con: sqlite3.Connection, cfg: dict | None = None,
                 set_id: str | None = None, ordem: str = "desc") -> dict:
    """O separador «Quanto custa» em Python: uma edição (ou tudo), por raridade,
    por preço. É o `master_faltas` cortado e arrumado — os itens são os mesmos.

    `set_id=None` é o botão «tudo»: as edições COM botão, todas juntas. O OGS
    não entra aí — ficou sem botão a pedido dele e «tudo» é o que os botões
    mostram; as cartas dele continuam na wantlist da Coleção. Pedir uma edição
    pelo nome devolve-a mesmo sem botão: é quem chama que está a perguntar por
    ela, e é assim que se mede o que o «tudo» deixa de fora.
    """
    cfg = cfg or config.load()
    p = master_faltas(con, cfg)
    botoes = {s["set"] for s in p["quanto_custa"]["sets"]}
    alvo = set_id.upper() if set_id else None
    escolhidas = [d for d in p["sets"]
                  if (d["set"] == alvo if alvo else d["set"] in botoes)]
    itens = [x for d in escolhidas for x in d["items"]]
    return {
        "set": alvo,
        "sets": p["quanto_custa"]["sets"],
        "sem_edicoes": p["quanto_custa"]["sem_edicoes"],
        "scope": p["scope"],
        **por_raridade(itens, ordem, top_por_raridade(cfg)),
    }


# ---------------------------------------------------------------------------
# A wantlist por edição
# ---------------------------------------------------------------------------


def wantlist(con: sqlite3.Connection, set_id: str | None = None,
             com_codigo: bool = False, cfg: dict | None = None,
             nivel: int | None = None) -> dict:
    """As faltas do master set no formato do Cardmarket, PARTIDAS POR EDIÇÃO.

    André, 2026-09-08: *"Quero também que no fim de cada edição me dês uma
    wantlist para eu colocar no Cardmarket."*

    **Não é uma lista nova.** É a do «Master set» (`master_faltas`), cortada por
    edição — mesmo âmbito (só o master set: a coleção extra acompanha-se, não
    se compra — 2026-09-15), mesmos alvos (o playset do tipo, runas numeradas
    incluídas — 2026-09-15), mesma regra de carência e as mesmas exclusões. As linhas saem do gerador
    único (`cardmarket.gerar`), que é o mesmo do «A subir», do «Master set», da
    Venda e das listas dos decks; o gémeo em JavaScript é o `cmLinha`. Uma
    segunda implementação era uma segunda resposta à mesma pergunta.

    `set_id=None` devolve todas as edições, pela ordem do config — é o bloco
    «Wantlist — tudo» do fim da página e o `riftvault wantlist --cardmarket` sem
    `--edicao`.

    Cada edição leva o seu `wantlist` (texto, linhas, cópias, cêntimos, foil) e
    no topo vai o mesmo para as edições escolhidas todas juntas. O total em
    euros fica SEMPRE fora do texto: uma linha de total colada na wantlist era
    importada como se fosse uma carta.

    `nivel` é o degrau da contagem por níveis (André, 2026-09-08): `1` dá a
    lista para ter **uma de cada**, `2` para ter **duas**, e sem ele a lista
    inteira, com o playset na sequência. Não é uma lista nova nem outros alvos —
    é o mesmo `metrics.master_target` cortado por `min(nivel, alvo)`, por isso
    as impressões de alvo 1 (Legends, Battlefields) saem iguais em todos
    os níveis, e o último degrau é o playset inteiro.
    """
    p = master_faltas(con, cfg, nivel)
    alvo = set_id.upper() if set_id else None
    sets = [d for d in p["sets"] if alvo is None or d["set"] == alvo]
    for d in sets:
        d["wantlist"] = cardmarket.gerar(d["items"], com_codigo)
    itens = [x for d in sets for x in d["items"]]
    return {
        "set": alvo,
        # O do `master_faltas`, não o pedido: `--nivel 3` é a lista de sempre
        # (`level: None`), e quem lê o payload tem de ver isso.
        "level": p["level"],
        "sets": sets,
        "items": itens,
        "no_price": sum(1 for x in itens if x["price"] is None),
        "rule": p["rule"],
        "scope": p["scope"],
        **cardmarket.gerar(itens, com_codigo),
    }

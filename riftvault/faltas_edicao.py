"""O separador «Faltas»: o que falta, por edição, em três blocos.

André, 2026-09-15 (fim da tarde): *"quero agora fazer uma seccao de faltas /
quero as faltas por edicao e dividido em 3 partes / Masterset / Alt Art /
OverNumbered"*.

NÃO É O SEPARADOR QUE SE APAGOU HORAS ANTES. O «Quanto custa» tinha as faltas
do master set arrumadas por raridade e ele mandou-as sair de lá porque aquele
separador passou a ser a tabela de preços. Isto é uma secção PRÓPRIA, com outra
organização: por edição, e dentro de cada edição três blocos pela ordem em que
ele os disse.

NÃO É UM CÁLCULO NOVO. A carência é a mesma da wantlist do fim de cada edição
da Coleção (`a_subir.master_faltas`): o mesmo âmbito (`a_subir.masterset`),
os mesmos alvos (`metrics.alvo`), as mesmas cópias (`locais.na_colecao`, só o
que está nos binders de Coleção) e o mesmo pendente (`pending.open_qty`). O
que muda é a arrumação — e que aqui a coleção extra também se VÊ.

OS TRÊS BLOCOS
    1. `master`       — a sequência numerada da edição (`metrics.BLOCO_MASTER`),
                        alvo do tipo: Unit/Spell/Gear 3, Legend e Battlefield
                        1, runas numeradas 3 (2026-09-15).
    2. `alt_art`      — as artes alternativas, pelo `variant_kind`. Inclui as
                        seis artes alternativas das runas do OGN, que a grelha
                        da Coleção arruma no bloco «runas especiais»: ele
                        nomeou três blocos e chamou-lhes «Alt Art», e uma
                        `OGN-007a` é uma arte alternativa. Alvo de playset.
    3. `overnumbered` — as sobrenumeradas (`metrics.BLOCO_OVER`), alvo 1
                        (`master_set.um_de_cada`, 2026-09-15).

    As promos `VEN-SP` NÃO estão na lista dele — nomeou três e não as nomeou.
    Ficam de fora do separador, contadas no `scope` para a página o dizer. É
    pergunta para ele, não decisão minha. Tokens, signatures e runas sem
    numeração continuam escondidos (`metrics.e_colecao`), como em todo o lado.

VER NÃO É COMPRAR
    Os três blocos aparecem com contagens e valores, mas SÓ o master set entra
    nas listas de compra — a wantlist «tudo», o texto do Cardmarket, o «A
    subir». É a frase dele da manhã: *"sobrenumeradas não entram na wantlist,
    nem na % de coleção completa; apenas pedi para ser feito track de playset
    para eu saber exatamente quantas tenho"*. Cada bloco leva `in_lists`, lido
    do MESMO botão que manda nas listas (`listas_de_compra.so_master_set`, via
    `a_subir.blocos_fora`): se um dia ele quiser as artes alternativas e as
    sobrenumeradas nas compras, é `so_master_set: false` no config — uma
    linha, e a página passa a dizê-lo sozinha.

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
"""

from __future__ import annotations

import sqlite3

from . import a_subir, cardmarket, config, locais, metrics, pending

# Os três blocos, pela ordem em que ele os disse. O id do primeiro e do
# terceiro são os da grelha; o do meio é o `variant_kind`, porque «Alt Art»
# aqui inclui as artes alternativas das runas (ver o topo do ficheiro).
BLOCOS = [
    (metrics.BLOCO_MASTER, "Master set"),
    ("alt_art", "Alt Art"),
    (metrics.BLOCO_OVER, "OverNumbered"),
]
BLOCO_IDS = [b for b, _ in BLOCOS]


def bloco_das_faltas(printing, cfg: dict | None = None) -> str | None:
    """Em qual dos três blocos cai esta impressão; `None` se em nenhum.

    A arte alternativa decide-se pelo `variant_kind` — antes do bloco da
    grelha, que manda as das runas para «runas especiais». O resto é o bloco
    da grelha: `master` ou `overnumbered`. As promos e o que mais houver
    (`special`, `rune_promo`, …) devolvem `None`.
    """
    if printing["variant_kind"] == "alt_art":
        return "alt_art"
    b = metrics.bloco(printing, cfg)
    return b if b in (metrics.BLOCO_MASTER, metrics.BLOCO_OVER) else None


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


def _item(pid: str, info: dict, preco: int | None, mkt: dict) -> dict:
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


def _soma(itens: list[dict]) -> dict:
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
    """O separador inteiro: por edição, os três blocos, cada um com o que falta.

    Todas as edições do catálogo, pela ordem dos separadores — o OGS entra: a
    exclusão do «Quanto custa» (`quanto_custa.sem_edicoes`) foi pedida para
    aquele separador. Cada edição leva sempre os três blocos, vazios ou não,
    e a soma dos três.
    """
    cfg = cfg or config.load()
    o = a_subir.opcoes(cfg)
    escopo = a_subir.masterset(con, cfg)
    # As exclusões da sequência (signatures, showcases — hoje tiram zero,
    # porque já estão escondidas), para o bloco `master` ser o MESMO da
    # wantlist. Sem `blocos`: a coleção extra é para se ver aqui, tire-a ou
    # não das listas de compra.
    escopo, _ = a_subir.excluir(escopo, {**o["excluir"], "blocos": []}, so_master=False)
    # O botão das listas de compra, lido do mesmo sítio que as listas o lêem.
    fora_das_listas = set(a_subir.blocos_fora(o["excluir"], o["so_master_set"]))
    in_lists = {
        metrics.BLOCO_MASTER: True,
        "alt_art": "alt_art" not in fora_das_listas,
        metrics.BLOCO_OVER: metrics.BLOCO_OVER not in fora_das_listas,
    }

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
                _item(pid, falta[pid], precos.get(pid), mercado.get(pid) or {}))

    sets = []
    for s in sets_ids:
        blocos = []
        for b, label in BLOCOS:
            itens = sorted(por_set[s][b], key=lambda x: (x["cn"], x["code"]))
            blocos.append({
                "id": b, "label": label,
                # «— playset» / «— 1 de cada», do mesmo config que dá o alvo.
                "target_label": metrics._sufixo_alvo(b, cfg).lstrip(" —"),
                "in_lists": in_lists[b],
                "scope": ambito[s][b],
                **_soma(itens),
                "items": itens,
            })
        todos = [x for g in blocos for x in g["items"]]
        sets.append({"set": s, "name": config.set_name(s),
                     # A soma dos três blocos — o que ele pediu no cabeçalho
                     # da edição — e, à parte, só o que entra nas compras.
                     **_soma(todos),
                     "lists": _soma([x for g in blocos if g["in_lists"] for x in g["items"]]),
                     "blocks": blocos})

    todos = [x for d in sets for g in d["blocks"] for x in g["items"]]
    nas_listas = [x for d in sets for g in d["blocks"] if g["in_lists"] for x in g["items"]]
    return {
        "blocks": [{"id": b, "label": label, "in_lists": in_lists[b]} for b, label in BLOCOS],
        "so_master_set": bool(o["so_master_set"]),
        "rule": str(o["regra_falta"]),
        "totals": _soma(todos),
        # Só os blocos que entram nas listas de compra: é este que bate com a
        # wantlist «tudo» e com o texto do Cardmarket.
        "totals_lists": _soma(nas_listas),
        "sets": sets,
        "scope": {
            "printings": sum(ambito[s][b] for s in sets_ids for b in BLOCO_IDS),
            # O que está na página da Coleção mas não em nenhum dos três blocos
            # — hoje só as promos. É o que a página tem de dizer.
            "fora": fora,
        },
    }

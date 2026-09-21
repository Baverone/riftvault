"""O painel do topo da Coleção — três cartões e dois quadros (2026-09-21).

O André escolheu o «layout H» para o topo da aba Coleção: por baixo dos
botões das edições e por cima da grelha, TRÊS CARTÕES lado a lado — «1 de
cada», «2 de cada», «playset» —, cada um com o «tenho/total» em grande, uma
barra fina e o «faltam N»; e por baixo DOIS QUADROS, «Raridade» e «Domínio»,
com uma linha por categoria e três mini-barras (uma por nível).

É a contagem por níveis de sempre (`metrics.niveis`, 2026-09-08), com quatro
diferenças que são desta ordem e ficam aqui, num módulo próprio, para não
mexer na regra da barra do master set:

  1. **As runas nunca entram** — nem no total, nem nos níveis, nem nos
     quadros (*"As RUNAS nunca entram em nada"*). A barra do master set
     continua a contar as 6 runas base do OGN a 3 (2026-09-15); o painel
     não. Por isso o «playset» do painel e a barra podem diferir em 6
     impressões no OGN, e o cabeçalho diz quantas ficaram de fora.
  2. **É por BLOCO da grelha**, não só o master set: ele escolhe no painel o
     bloco (master set, sobrenumeradas, artes alternativas, promos) e os
     três cartões e os dois quadros são sobre as impressões desse bloco. Nos
     blocos de alvo 1 (sobrenumeradas, promos) os três níveis coincidem —
     é o esperado, não uma excepção.
  3. **Conta CARTAS (impressões) que chegaram ao nível**, não cópias em
     falta: o cartão diz «167/197» e «faltam 30», e o 30 são impressões.
  4. Os três níveis são FIXOS — 1, `min(2, alvo)`, o alvo — porque é a
     definição da ordem (*"tres cartoes sempre visiveis"*); não são os
     `metrics.degraus`, que encolhem quando nada pede 3.

O que NÃO muda: o âmbito é o da grelha — as escondidas (`metrics.escondida`,
que já inclui as retiradas) ficam fora, o alvo é o `metrics.alvo`, a raridade
é a da BASE do grupo (`base_rarity`) e o «tenho» é o que está na Coleção
(`locais.na_colecao`), como na barra. Os nomes das categorias e a ordem das
linhas são as da maqueta dele (`layout-H-cartoes.html`).

Só lê. Não escreve no vault, não leva euros.
"""

from __future__ import annotations

import json
import sqlite3

from . import config, locais, metrics

# Os três níveis, pela ordem dos cartões. O alvo do nível k é
# `metrics.alvo_do_nivel(k, N_NIVEIS, alvo)`: 1, min(2, alvo), o alvo.
N_NIVEIS = 3
NIVEIS = [
    {"k": 1, "label": "1 de cada"},
    {"k": 2, "label": "2 de cada"},
    {"k": 3, "label": "playset"},
]

# As raridades, pela ordem do quadro (da mais comum para a mais rara, como na
# maqueta) e com o nome em português. Uma raridade que o catálogo traga e não
# esteja aqui aparece na mesma, no fim, com o nome que trouxer.
RARIDADES = [
    ("common", "Comuns"),
    ("uncommon", "Incomuns"),
    ("rare", "Raras"),
    ("epic", "Épicas"),
    ("showcase", "Showcase"),
]

# Os domínios, pela ordem da maqueta. O `Colorless` da RiftScribe é «sem
# domínio»; uma carta com dois domínios é «multi-domínio» — uma linha só,
# como ele a desenhou, e não uma linha por domínio, senão a soma das linhas
# passava o total do bloco. Um domínio novo aparece na mesma, antes dos dois
# últimos, com o nome que trouxer.
DOMINIOS = [
    ("fury", "Fury"),
    ("body", "Body"),
    ("calm", "Calm"),
    ("mind", "Mind"),
    ("chaos", "Chaos"),
    ("order", "Order"),
    ("none", "Sem domínio"),
    ("multi", "Multi-domínio"),
]
SEM_DOMINIO = "none"
MULTI_DOMINIO = "multi"
# O que a RiftScribe escreve nas cartas sem domínio.
DOMINIOS_VAZIOS = {"colorless", ""}

# «Todas» as edições — a chave do painel somado, ao lado das edições.
TODAS = "all"


def dominio(domains_json: str | None) -> str:
    """A chave da linha do quadro «Domínio» de uma carta, a partir do
    `domains_json` do catálogo (`["Fury"]`, `["Body", "Calm"]`, `["Colorless"]`)."""
    try:
        doms = json.loads(domains_json or "[]")
    except (TypeError, ValueError):
        doms = []
    doms = [str(d).strip().lower() for d in doms]
    doms = [d for d in doms if d not in DOMINIOS_VAZIOS]
    if not doms:
        return SEM_DOMINIO
    if len(set(doms)) > 1:
        return MULTI_DOMINIO
    return doms[0]


def marca(alvo: int, tem: int) -> list[int]:
    """`[1, n1, n2, n3]`: esta impressão conta (sempre 1) e, para cada nível,
    se já lá chegou. Uma impressão de alvo 1 chega aos três de uma vez."""
    return [1] + [1 if tem >= metrics.alvo_do_nivel(k, N_NIVEIS, alvo) else 0
                  for k in range(1, N_NIVEIS + 1)]


def _linhas(por: dict[str, list[int]], ordem: list[tuple[str, str]]) -> list[dict]:
    """As linhas de um quadro, pela ordem conhecida; o desconhecido vai para o
    fim (antes dos dois últimos no caso dos domínios — ver `_linhas_dominio`)."""
    conhecidas = [k for k, _ in ordem]
    rotulos = dict(ordem)
    chaves = [k for k in conhecidas if k in por]
    chaves += sorted(k for k in por if k not in conhecidas)
    return [{"id": k, "label": rotulos.get(k, k.capitalize()),
             "n": por[k][0], "levels": por[k][1:]} for k in chaves]


def _linhas_dominio(por: dict[str, list[int]]) -> list[dict]:
    # Um domínio novo (uma edição futura) entra antes de «Sem domínio» e
    # «Multi-domínio», que são as duas linhas de fecho.
    fixos = [(k, r) for k, r in DOMINIOS if k not in (SEM_DOMINIO, MULTI_DOMINIO)]
    novos = sorted(k for k in por if k not in dict(DOMINIOS))
    ordem = fixos + [(k, k.capitalize()) for k in novos] \
        + [(k, r) for k, r in DOMINIOS if k in (SEM_DOMINIO, MULTI_DOMINIO)]
    return _linhas(por, ordem)


def contar(itens) -> dict:
    """Os três cartões e os dois quadros de uma lista de
    `(alvo, tem, raridade, domínio)`.

      `n`       — impressões no âmbito (o denominador dos três cartões)
      `levels`  — quantas já chegaram a cada nível: `[n1, n2, n3]`
      `rarity`  — uma linha por raridade, com `n` e `levels` próprios
      `domain`  — idem, por domínio

    Por construção, `n1 >= n2 >= n3` (o alvo de cada nível não desce) e a
    soma do `n` das linhas de cada quadro é o `n` do total, nível a nível —
    cada impressão cai numa raridade e num domínio, e só num.
    """
    total = [0] * (N_NIVEIS + 1)
    por_rar: dict[str, list[int]] = {}
    por_dom: dict[str, list[int]] = {}
    for alvo, tem, rar, dom in itens:
        m = marca(alvo, tem)
        for slot in (total, por_rar.setdefault(rar, [0] * (N_NIVEIS + 1)),
                     por_dom.setdefault(dom, [0] * (N_NIVEIS + 1))):
            for i, v in enumerate(m):
                slot[i] += v
    return {
        "n": total[0],
        "levels": total[1:],
        "rarity": _linhas(por_rar, RARIDADES),
        "domain": _linhas_dominio(por_dom),
    }


def itens(con: sqlite3.Connection, cfg: dict | None = None):
    """`(set_id, bloco, alvo, tem, raridade, domínio)` de cada impressão que
    entra no painel — a grelha da Coleção (sem escondidas, com alvo), menos
    as runas. Devolve também quantas runas ficaram de fora, por edição."""
    cfg = cfg or config.load()
    qty = locais.na_colecao(con)
    fora: dict[str, int] = {}
    linhas = []
    for r in con.execute(
        "SELECT printing_id, set_id, collector_number, public_code, variant_kind, "
        "       type, is_token, base_rarity, rarity, domains_json "
        "FROM catalog.printings ORDER BY set_id, api_sort"
    ):
        # A regra da página: o que está escondido (tokens, signatures, as runas
        # sem numeração) e o que está retirado (as runas em alt art) não
        # aparece na grelha, e não aparece aqui. É a mesma função.
        if metrics.escondida(r, cfg):
            continue
        alvo = metrics.alvo(r, cfg)
        if alvo <= 0:
            continue
        if metrics.e_runa(r, cfg):
            fora[r["set_id"]] = fora.get(r["set_id"], 0) + 1
            continue
        linhas.append((r["set_id"], metrics.bloco(r, cfg), alvo,
                       qty.get(r["printing_id"], 0),
                       (r["base_rarity"] or r["rarity"] or "?").lower(),
                       dominio(r["domains_json"])))
    return linhas, fora


def payload(con: sqlite3.Connection, cfg: dict | None = None) -> dict:
    """O painel de cada edição e de «Todas» (`TODAS`), bloco a bloco.

      `levels`  — os três níveis, com o rótulo de cada cartão
      `blocks`  — os blocos que existem, pela ordem da grelha
                  (`master_set.ordem_dos_blocos`), com o rótulo e o alvo
      `rarities`, `domains` — a ordem e o nome das linhas dos dois quadros,
                  para o cliente (que recalcula a cada `+`/`−`) não ter uma
                  segunda cópia
      `sets`    — `{set_id: {bloco: contar(...)}}`, e a chave `all` com as
                  edições somadas (é uma soma: cada impressão conta uma vez)
      `runes_out` — quantas runas ficaram de fora, por edição e em `all`, para
                  o cabeçalho dizer porque é que o playset não bate com a barra
    """
    cfg = cfg or config.load()
    linhas, fora = itens(con, cfg)
    por: dict[str, dict[str, list]] = {}
    for sid, bid, alvo, tem, rar, dom in linhas:
        item = (alvo, tem, rar, dom)
        por.setdefault(sid, {}).setdefault(bid, []).append(item)
        por.setdefault(TODAS, {}).setdefault(bid, []).append(item)
    ordem = metrics.ordem_dos_blocos(cfg)
    presentes = {bid for d in por.values() for bid in d}
    blocks = [{"id": bid,
               "label": "Master set" if bid == metrics.BLOCO_MASTER
               else metrics.BLOCO_LABEL.get(bid, bid),
               "target": metrics.alvo_do_bloco(bid, cfg),
               "counts": metrics.conta_bloco(bid, cfg)}
              for bid in ordem if bid in presentes]
    sets = {sid: {bid: contar(d[bid]) for bid in ordem if bid in d}
            for sid, d in por.items()}
    fora[TODAS] = sum(fora.values())
    return {"levels": NIVEIS, "blocks": blocks,
            "rarities": [list(x) for x in RARIDADES],
            "domains": [list(x) for x in DOMINIOS],
            "sets": sets, "runes_out": fora}


def da_edicao(con: sqlite3.Connection, set_id: str, cfg: dict | None = None) -> dict:
    """O painel de UMA edição — o que vai em `progress.painel` do payload dela:
    `{blocks, runes_out}`, com os blocos como no `payload`."""
    p = payload(con, cfg)
    return {"blocks": p["sets"].get(set_id, {}),
            "runes_out": p["runes_out"].get(set_id, 0)}


def texto(p: dict, sets: list[dict]) -> str:
    """O painel em consola, para o `riftvault stats`: uma linha por edição e
    por bloco, com os três níveis em «tenho/total»."""
    linhas = []
    nomes = {s["id"]: s["name"] for s in sets}
    nomes[TODAS] = "TODAS"
    ordem = [s["id"] for s in sets if s["id"] in p["sets"]] + [TODAS]
    w = max(len(n) for n in nomes.values())
    cab = "  ".join(f"{lv['label']:>11}" for lv in p["levels"])
    for b in p["blocks"]:
        linhas.append(f"\n{b['label']} — {b['target']}:")
        linhas.append(f"{'edição':<{w}}  {cab}")
        for sid in ordem:
            c = p["sets"].get(sid, {}).get(b["id"])
            if not c:
                continue
            cel = "  ".join(f"{d:>5}/{c['n']:<5}" for d in c["levels"])
            linhas.append(f"{nomes.get(sid, sid):<{w}}  {cel}")
    runas = p["runes_out"].get(TODAS, 0)
    if runas:
        linhas.append(f"\n(as runas ficam fora do painel: {runas} impressões)")
    return "\n".join(linhas)

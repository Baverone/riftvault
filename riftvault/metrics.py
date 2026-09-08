"""As duas métricas de completude e os payloads que o frontend come.

  1) PLAYSET JOGÁVEL — alvo por CARTA LÓGICA (o nome). Qualquer impressão de
     qualquer edição conta. É a métrica de "consigo montar decks com isto".
  2) MASTER SET — alvo por IMPRESSÃO. É a métrica de colecionador, e desde
     2026-09-08 a Coleção são TRÊS BLOCOS por esta ordem (ver `BLOCOS`):

       1. a sequência do master set, em PLAYSET (o alvo do tipo da carta);
       2. as runas especiais, **1 de cada** e por edição;
       3. no fim, as artes alternativas, **1 de cada**.

     Os três contam para a percentagem; o que fica de fora (`master_set.fora`,
     hoje só os tokens `-T`) vai para blocos informativos no fim. Ver
     `e_master`, `bloco` e `conta_bloco`.

São sempre calculadas e mostradas em paralelo. Nenhuma substitui a outra.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from . import config

# Ordem em que as variantes aparecem dentro do grupo, na grelha.
KIND_ORDER = {"base": 0, "alt_art": 1, "signature": 2,
              "rune_promo": 3, "special": 4, "token": 5, "unknown": 9}

RARITY_ORDER = ["common", "uncommon", "rare", "epic", "showcase"]

# Os blocos da grelha, por esta ordem (André, 2026-09-08): *"master set playset
# todo seguido; 1 runa especial de cada para cada set; no fim 1 alt art de
# cada"*. Os três primeiros são a COLEÇÃO — contam para a percentagem; os
# outros são o que ficou fora dela (`master_set.fora`, hoje só os tokens).
#
# Há um bloco por variante, e não só para as que ele nomeou: assim quem
# acrescentar uma variante ao `master_set.fora` recebe um cabeçalho a dizer o
# que é, em vez do «outras». Os blocos vazios não aparecem.
BLOCO_MASTER = "master"
BLOCO_RUNA = "rune_special"
BLOCOS = [
    (BLOCO_MASTER, None),
    (BLOCO_RUNA, "Runas especiais — 1 de cada"),
    ("alt_art", "Artes alternativas — 1 de cada"),
    ("token", "Fora da coleção — tokens"),
    ("signature", "Fora da coleção — signatures"),
    ("rune_promo", "Fora da coleção — runas promo"),
    ("special", "Fora da coleção — promos especiais"),
    ("base", "Fora da coleção — impressões base"),
    ("outras", "Fora da coleção — outras"),
]
BLOCO_LABEL = dict(BLOCOS)

# O mesmo bloco muda de rótulo quando o `master_set.fora` o põe fora da coleção:
# a cauda das artes alternativas é «1 de cada» enquanto conta, e «fora» quando
# não conta. É o mesmo id nos dois casos — o que muda é o que se lê. Ver
# `rotulo()`.
BLOCO_LABEL_FORA = {"alt_art": "Fora da coleção — artes alternativas"}

# O nome curto de cada bloco, para os chips da percentagem por bloco. É o mesmo
# nos dois rótulos, por isso não se tira do `label` a golpes de expressão
# regular.
BLOCO_CURTO = {
    BLOCO_MASTER: "master set",
    BLOCO_RUNA: "runas especiais",
    "alt_art": "artes alternativas",
    "token": "tokens",
    "signature": "signatures",
    "rune_promo": "runas promo",
    "special": "promos especiais",
    "base": "impressões base",
    "outras": "outras",
}

# As «runas especiais» do bloco 2: uma impressão de runa que não seja a base.
# No catálogo de hoje são as artes alternativas do OGN e as runas promo do VEN
# (a RiftScribe não tem runas no SFD nem no UNL — ver "BURACO NO CATÁLOGO" no
# CLAUDE.md). Muda-se em `runas_especiais` no config.
RUNA_ESPECIAL: dict = {"tipos": ["Rune"], "excepto": ["base"], "alvo": 1}

# O sufixo do CÓDIGO IMPRESSO -> o `variant_kind` que ele dá no catálogo. É a
# escrita do André ("sigla-T", "a no fim"), e o `master_set.fora` aceita-a a par
# do nome da variante — as duas dizem a mesma coisa. Ver `kinds_fora`.
SUFIXO_KIND = {
    "-t": "token",          # UNL-T03
    "a": "alt_art",         # UNL-228a
    "*": "signature",       # OGN-299*
    "-r": "rune_promo",     # VEN-R01
    "-sp": "special",       # VEN-SP4
}

# Memo do `kinds_fora`: a lista do config não muda dentro de uma corrida, e a
# pergunta é feita uma vez por impressão (1180) por payload.
_FORA_MEMO: dict[tuple, frozenset] = {}


# --------------------------------------------------------------------------
# Alvos
# --------------------------------------------------------------------------


def campo(printing, nome: str, omissao=None):
    """Um campo da impressão, aceitando linha do SQLite, dicionário ou nem isso.

    O `bloco()` e o `e_master()` são chamados com linhas da `catalog.printings`
    mas também com dicionários mínimos (`{"variant_kind": ..., "is_token": 0}`).
    A `sqlite3.Row` levanta `IndexError` no que não existe e o `dict` levanta
    `KeyError`; aqui a falta de um campo é uma resposta, não um erro.
    """
    try:
        valor = printing[nome]
    except (KeyError, IndexError):
        return omissao
    return omissao if valor is None else valor


def opcoes_runa(cfg: dict | None = None) -> dict:
    """`runas_especiais` do config, por cima dos defaults do `RUNA_ESPECIAL`."""
    cfg = cfg or config.load()
    out = dict(RUNA_ESPECIAL)
    out.update({k: v for k, v in (cfg.get("runas_especiais") or {}).items()
                if not k.startswith("_")})
    return out


def e_runa_especial(printing, cfg: dict | None = None) -> bool:
    """Esta impressão é uma «runa especial» — o bloco 2 da Coleção?

    André, 2026-09-08: *"1 runa especial de cada para cada set"*. A runa base
    fica no bloco 1 e pede o playset (12); as outras impressões da runa — a
    arte alternativa e a promo — pedem **1** e vão para um bloco próprio, por
    edição, antes da cauda das artes alternativas.
    """
    o = opcoes_runa(cfg)
    tipos = o.get("tipos") or ()
    if campo(printing, "type") not in tipos:
        return False
    return campo(printing, "variant_kind") not in (o.get("excepto") or ())


def playset_target(card_type: str | None, is_token: bool, cfg: dict | None = None) -> int:
    cfg = cfg or config.load()
    # Tokens: 1 de cada (decisão do André). É o ALVO — desde 2026-09-08 os que
    # têm código `-T` já não entram na percentagem de master set (`e_master`),
    # mas o tile continua a dizer-lhe quantos lhe faltam.
    if is_token:
        return int(cfg.get("token_target", 1))
    targets = cfg.get("playset_targets_by_type", {})
    return int(targets.get(card_type or "", targets.get("default", 3)))


def master_target(printing_id: str, kind: str, card_type: str | None, is_token: bool,
                  cfg: dict | None = None) -> int:
    cfg = cfg or config.load()
    override = cfg.get("master_target_overrides", {}).get(printing_id)
    if override is not None:
        return int(override)
    if is_token:
        return int(cfg.get("token_target", 1))
    by_variant = cfg.get("master_targets_by_variant", {})
    if e_runa_especial({"type": card_type, "variant_kind": kind}, cfg):
        # *"1 runa especial de cada para cada set"* — antes do alvo da variante,
        # senão a arte alternativa de uma runa pedia o playset da runa (12).
        return int(opcoes_runa(cfg).get("alvo", 1))
    if kind == "base" and cfg.get("master_base_follows_type", True):
        # Senão uma Rune base pediria 3 em vez de 12, e um Legend pediria 3
        # em vez de 1. O alvo do master da base segue o alvo de jogo.
        return playset_target(card_type, is_token, cfg)
    if kind in set(cfg.get("master_variantes_playset", [])):
        # O André quer contagem de playset nas artes alternativas (2026-09-05):
        # se decide colecionar a alt art, quer as 3 na mesma, não uma. Isto é
        # só o alvo do tile — continuam fora da percentagem (`e_master`).
        return playset_target(card_type, is_token, cfg)
    return int(by_variant.get(kind, 1))


def kinds_fora(cfg: dict | None = None) -> frozenset[str]:
    """Os `variant_kind` que ficam FORA do master set, lidos do config.

    A lista vive em `master_set.fora` e escreve-se como o André fala — pelo
    sufixo do código impresso (`["-T", "a"]`) — ou pelo nome da variante
    (`["token", "alt_art"]`). São a mesma coisa; ver `SUFIXO_KIND`.

    Para tirar também as signatures da sequência acrescenta-se `"signature"`
    (ou `"*"`). **Hoje está desligado de propósito**: o André nomeou os `-T` e
    os `a`, não as signatures, e elas contam no denominador da percentagem.
    Ligar tira-as das duas coisas — é a mesma pergunta.

    Um valor que não se reconheça REBENTA, e de propósito: uma variante nova
    (um `b`? um `sp7`?) tem de aparecer, não de ser ignorada em silêncio —
    ver CLAUDE.md, "Superfícies NÃO validadas".
    """
    cfg = cfg or config.load()
    bruto = tuple((cfg.get("master_set") or {}).get("fora") or ())
    memo = _FORA_MEMO.get(bruto)
    if memo is not None:
        return memo
    kinds = set()
    for valor in bruto:
        chave = str(valor).strip().lower()
        if chave in SUFIXO_KIND:
            kinds.add(SUFIXO_KIND[chave])
        elif chave in KIND_ORDER:
            kinds.add(chave)
        else:
            aceites = ", ".join(sorted(set(SUFIXO_KIND) | set(KIND_ORDER)))
            raise ValueError(
                f"master_set.fora: nao reconheco {valor!r}. Aceita: {aceites}")
    _FORA_MEMO[bruto] = out = frozenset(kinds)
    return out


def e_master(printing, cfg: dict | None = None) -> bool:
    """Esta impressão faz parte da COLEÇÃO — isto é, conta para a percentagem?

    É a única resposta a esta pergunta em todo o riftvault: usam-na a métrica
    (o denominador da percentagem), a grelha da Coleção (a ordem dos blocos), a
    aba «A subir», a lista completa do master set e a lista de venda. Havia duas
    leituras a divergir — a percentagem ignorava as artes alternativas mas a
    grelha punha-as na sequência — e passou a haver uma.

    A REGRA É O CÓDIGO IMPRESSO (André, 2026-09-08): o que ele mandou tirar
    escreve-se pelo sufixo, e no catálogo lê-se pelo `variant_kind`, que é
    derivado do mesmo sufixo:

      `UNL-T03`   -> variant `t03` -> kind `token`
      `UNL-228a`  -> variant `a`   -> kind `alt_art`

    Muda-se em `master_set.fora`, hoje `["-T"]` — só os tokens. **As artes
    alternativas voltaram para dentro a 2026-09-08**, na segunda frase dele
    (*"no fim 1 alt art de cada"*): continuam a ser a cauda da grelha, num
    bloco próprio, mas agora contam com alvo 1. Ver `bloco` e `conta_bloco`.

    Não confundir com o ALVO (`master_target`): o alvo é o que o tile mostra
    ("6/12"), isto é o que entra no denominador. São duas perguntas diferentes
    e têm dois campos desde 2026-09-02.

    Aceita uma linha do `catalog.printings` ou qualquer dicionário com
    `variant_kind` e `is_token`.
    """
    cfg = cfg or config.load()
    if printing["variant_kind"] in kinds_fora(cfg):
        return False
    # Os tokens com número de coleção próprio (`OGN-271/298`, o Recruit) não têm
    # sufixo nenhum e por isso ficam: estão numerados dentro da edição.
    return not printing["is_token"] or int(cfg.get("token_target", 1)) > 0


def bloco(printing, cfg: dict | None = None) -> str:
    """Em que bloco da grelha é que esta impressão cai.

    A Coleção são três blocos seguidos (André, 2026-09-08): a sequência do
    master set em playset, depois as runas especiais a 1, depois as artes
    alternativas a 1. O que está fora da coleção vai para um bloco próprio a
    seguir a tudo — nunca intercalado. Ver `BLOCOS` para a ordem.
    """
    if not e_master(printing, cfg):
        kind = printing["variant_kind"]
        # Uma variante nova (um `b`? um `sp7`?) tem de cair num sítio visível em
        # vez de desaparecer — ver CLAUDE.md, "Superfícies não validadas".
        return kind if kind in BLOCO_LABEL else "outras"
    # A runa especial ganha à arte alternativa: a arte alternativa de uma runa é
    # das duas coisas, e ele pediu-a no bloco das runas ("1 runa especial de
    # cada para cada set"), antes da cauda das alt arts.
    if e_runa_especial(printing, cfg):
        return BLOCO_RUNA
    if printing["variant_kind"] == "alt_art":
        return "alt_art"
    return BLOCO_MASTER


def conta_bloco(bloco_id: str, cfg: dict | None = None) -> bool:
    """Este bloco entra na percentagem da Coleção?

    Os três blocos da coleção contam; os outros são o que o `master_set.fora`
    deixou de fora e existem só para ele ver que não desapareceram. O `alt_art`
    é o único id que aparece dos dois lados — é a cauda da coleção enquanto
    contar, e um bloco de fora quando o `master_set.fora` o levar.
    """
    if bloco_id in (BLOCO_MASTER, BLOCO_RUNA):
        return True
    return bloco_id == "alt_art" and "alt_art" not in kinds_fora(cfg)


def rotulo(bloco_id: str, cfg: dict | None = None) -> str | None:
    """O cabeçalho do bloco. `None` no primeiro: a sequência não leva título."""
    if not conta_bloco(bloco_id, cfg) and bloco_id in BLOCO_LABEL_FORA:
        return BLOCO_LABEL_FORA[bloco_id]
    return BLOCO_LABEL.get(bloco_id)


# --------------------------------------------------------------------------
# Payloads
# --------------------------------------------------------------------------


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sets_payload(con: sqlite3.Connection) -> list[dict]:
    rows = con.execute(
        "SELECT set_id, COUNT(*) AS n FROM catalog.printings GROUP BY set_id"
    ).fetchall()
    out = [
        {"id": r["set_id"], "name": config.set_name(r["set_id"]),
         "order": config.set_order(r["set_id"]), "n_printings": r["n"]}
        for r in rows
    ]
    out.sort(key=lambda s: (s["order"], s["id"]))
    return out


def owned_by_card(con: sqlite3.Connection) -> dict[str, int]:
    """Cópias por carta lógica, somando TODAS as impressões de TODAS as edições."""
    rows = con.execute(
        "SELECT p.card_key AS k, SUM(c.qty) AS n FROM copies c "
        "JOIN catalog.printings p ON p.printing_id = c.printing_id "
        "WHERE c.qty > 0 GROUP BY p.card_key"
    ).fetchall()
    return {r["k"]: r["n"] for r in rows}


def prices_map(con: sqlite3.Connection) -> dict[str, int]:
    """printing_id -> preço em cêntimos. Vazio enquanto não houver `riftvault prices`."""
    try:
        rows = con.execute(
            "SELECT printing_id, price_cents FROM catalog.price_latest "
            "WHERE price_cents IS NOT NULL"
        ).fetchall()
    except sqlite3.OperationalError:
        return {}               # catálogo antigo, sem a tabela ainda
    return {r["printing_id"]: r["price_cents"] for r in rows}


def set_payload(con: sqlite3.Connection, set_id: str, editable: bool = True,
                image_mode: str = "local") -> dict:
    from . import decks

    cfg = config.load()
    qty = {r["printing_id"]: r["qty"] for r in con.execute("SELECT printing_id, qty FROM copies")}
    owned_cards = owned_by_card(con)
    price = prices_map(con)
    # Onde estão as cópias que não estão no binder: nos decks.
    try:
        nos_decks = decks.printing_allocation(con)
    except sqlite3.OperationalError:
        nos_decks = {}

    rows = con.execute(
        "SELECT * FROM catalog.printings WHERE set_id = ? ORDER BY api_sort", (set_id,)
    ).fetchall()

    groups: dict[str, dict] = {}
    for r in rows:
        g = groups.get(r["group_key"])
        if g is None:
            g = groups[r["group_key"]] = {
                "key": r["group_key"],
                "cn": r["collector_number"],
                "lane": r["lane"],
                "sort": r["api_sort"],
                "card_key": r["card_key"],
                "name": r["name"],
                "type": r["type"],
                "rarity": r["base_rarity"],
                # Custo de energia da impressão base — é por aqui que a grelha
                # ordena quando se escolhe "Custo".
                "energy": r["energy"],
                "faction": r["faction"],
                "is_token": bool(r["is_token"]),
                "printings": [],
            }
        g["printings"].append({
            "id": r["printing_id"],
            "code": r["public_code"],
            "kind": r["variant_kind"],
            "label": r["variant_label"],
            "name": r["name"],
            "rarity": r["rarity"],
            # Battlefields vêm 'landscape' — o tile tem de mudar de proporção.
            "landscape": (r["orientation"] or "").lower() == "landscape",
            "price": price.get(r["printing_id"]),   # cêntimos, ou None
            "in_decks": nos_decks.get(r["printing_id"], []),
            "qty": qty.get(r["printing_id"], 0),
            "target": master_target(r["printing_id"], r["variant_kind"], r["type"],
                                    bool(r["is_token"]), cfg),
            # O bloco da grelha: `master`, `rune_special` ou `alt_art` dentro da
            # coleção, e um bloco próprio para o que ficou de fora. É o mesmo
            # campo que diz se entra na percentagem (ver `conta_bloco`).
            "block": bloco(r, cfg),
            "img": f"img/{r['printing_id']}.webp",
            "cdn": r["image_medium"] or r["image_large"] or r["image_url"],
            "banned": bool(r["is_banned"]),
            "sort": r["api_sort"],
        })

    ordered = sorted(groups.values(), key=lambda g: g["sort"])
    for g in ordered:
        g["printings"].sort(key=lambda p: (KIND_ORDER.get(p["kind"], 9), p["sort"]))
        for i, p in enumerate(g["printings"]):
            p["head"] = i == 0   # o tile que fica visível em "Só artes base"
        target = playset_target(g["type"], g["is_token"], cfg)
        g["playset"] = {"owned": owned_cards.get(g["card_key"], 0), "target": target}

    # ----- barras de progresso e contadores -----
    seen_cards: set[str] = set()
    play_done = play_total = 0
    for g in ordered:
        if g["playset"]["target"] <= 0 or g["card_key"] in seen_cards:
            continue
        seen_cards.add(g["card_key"])
        play_total += 1
        if g["playset"]["owned"] >= g["playset"]["target"]:
            play_done += 1

    master_done = master_total = 0
    by_rarity: dict[str, list[int]] = {}
    # TODOS os blocos têm contador próprio ("tens N de M"); os três da coleção
    # somam-se ainda na percentagem global, e os de fora não — é o ponto todo
    # de estarem fora.
    by_block: dict[str, list[int]] = {}
    for g in ordered:
        for p in g["printings"]:
            if p["target"] <= 0:
                continue
            complete = p["qty"] >= p["target"]
            slot = by_block.setdefault(p["block"], [0, 0])
            slot[1] += 1
            slot[0] += 1 if complete else 0
            if not conta_bloco(p["block"], cfg):
                continue
            master_total += 1
            master_done += 1 if complete else 0
            # Pela raridade da BASE do grupo, como sempre: a `showcase` não é
            # raridade de jogo. A soma dos chips é o denominador da barra.
            slot = by_rarity.setdefault(g["rarity"] or "?", [0, 0])
            slot[1] += 1
            slot[0] += 1 if complete else 0

    rarities = [
        {"rarity": k, "done": v[0], "total": v[1]}
        for k, v in sorted(by_rarity.items(),
                           key=lambda kv: (RARITY_ORDER.index(kv[0])
                                           if kv[0] in RARITY_ORDER else 99, kv[0]))
    ]

    # Valor do que tenho DESTA edição, e o que a edição inteira valeria se
    # estivesse completa segundo a métrica de master set.
    value_owned = value_full = 0
    for g in ordered:
        for p in g["printings"]:
            if p["price"] is None:
                continue
            value_owned += p["qty"] * p["price"]
            # "se estivesse completa" é sobre a COLEÇÃO: o que não entra na
            # percentagem também não entra no preço de a fechar. Desde
            # 2026-09-08 isso inclui 1 de cada runa especial e 1 de cada alt art.
            if conta_bloco(p["block"], cfg):
                value_full += p["target"] * p["price"]

    # Cada bloco leva o seu "tens N de M"; o `counts` diz quais é que se somam
    # na barra do master set. A percentagem global é a soma dos que contam.
    blocks = [
        {"id": bid, "label": rotulo(bid, cfg), "short": BLOCO_CURTO.get(bid, bid),
         "counts": conta_bloco(bid, cfg),
         "done": by_block[bid][0], "total": by_block[bid][1]}
        for bid, _ in BLOCOS if bid in by_block
    ]

    return {
        "editable": editable,
        "image_mode": image_mode,
        "generated_at": _now(),
        "set": {"id": set_id, "name": config.set_name(set_id)},
        # A partir de que preço é que o valor aparece por cima da carta.
        "price_badge_min": int(cfg.get("price_badge_min_cents", 100)),
        "progress": {
            "playset": {"done": play_done, "total": play_total},
            "master": {"done": master_done, "total": master_total},
            "value": {"owned": value_owned, "full": value_full,
                      "currency": "EUR", "has_prices": bool(price)},
            "rarities": rarities,
        },
        # A ordem dos blocos da grelha, e o rótulo de cada um. Vem do servidor
        # para o cliente não ter uma segunda cópia da regra.
        "blocks": blocks,
        "groups": ordered,
    }


def ordem_da_grelha(payload: dict) -> list[tuple[str, str]]:
    """(bloco, printing_id) pela ordem em que a grelha desenha os tiles.

    O `groups` do payload continua a vir por número de coleção — é a ordem da
    API e é a que a sequência do master set precisa. O que a grelha faz é
    percorrê-lo uma vez POR BLOCO: primeiro o master set inteiro, depois as
    runas especiais, depois as artes alternativas, e só no fim o que está fora
    da coleção (André, 2026-09-08). O `render()` do `app.js` faz exatamente
    estes dois ciclos; isto é a mesma ordem em Python, para dar para testar sem
    browser.
    """
    fora = []
    for b in payload.get("blocks") or [{"id": BLOCO_MASTER}]:
        for g in payload["groups"]:
            for p in g["printings"]:
                if p["block"] == b["id"]:
                    fora.append((b["id"], p["id"]))
    return fora


def index_payload(con: sqlite3.Connection, editable: bool = True,
                  image_mode: str = "local") -> dict:
    from . import collection, prices

    try:
        value = prices.collection_value(con)
    except sqlite3.OperationalError:
        value = None            # ainda não correu `riftvault prices`

    return {
        "editable": editable,
        "image_mode": image_mode,
        "generated_at": _now(),
        "sets": sets_payload(con),
        "totals": collection.totals(con),
        "value": value,
    }

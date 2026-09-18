"""A montra «Promos» da Coleção: as promos oficiais, com a foto da carta.

André, 2026-09-18: *"e essas que digo, de Nexus Night, eventos, bundles, etc"*
/ *"consegues averiguar e fazer um botao com essas, com foto da carta tambem,
assim consigo perceber se vou querer coleccionar tambem ou nao"*.

É UMA MONTRA, NÃO UMA META. O objectivo dele é VER o que existe para decidir
se vai atrás disto. Por isso:

- não conta para nada — nem percentagem, nem denominador, nem wantlist, nem
  «A mais», nem Faltas, nem valor da coleção;
- não tem alvo e não entra em lista de compra nenhuma;
- não é uma categoria nova ao lado de Alt Art / OverNumbered / SP. As 6
  `VEN-SP` que o catálogo já conhece continuam onde estão; quando uma carta
  desta lista também tem uma `VEN-SP` no catálogo, o item diz-o
  (`promo_catalogo`) — é a mesma carta vista de outro sítio.

A LISTA É DADOS, NÃO CÓDIGO. Vive em `data/promos_oficiais.json`
(`config.PROMOS_PATH`), versionada, para ele a corrigir à mão: é uma lista de
um site da comunidade (riftbound.gg), lida UMA vez a mão a 2026-09-18, e pode
ter erros. NÃO SE VOLTA A IR AO SITE — o `robots.txt` deles proíbe o
`anthropic-ai`. Nada aqui faz rede.

O CATÁLOGO NÃO CONHECE ESTAS PROMOS. A RiftScribe só tem 6 promos (as
`ven-sp1..sp6`); as 128 cartas desta lista existem lá como cartas NORMAIS. O
promo é uma impressão diferente da mesma carta, por isso a imagem da versão
normal serve para ele perceber QUE carta é — e a página diz claramente que a
foto é da versão normal, não da promo.

NUNCA SE ADIVINHA UM NOME (`casar`). Quatro casamentos, do mais forte para o
mais fraco, e cada um só vale quando dá UMA carta:

    1. `exacto`        — o nome é o `card_key` do catálogo (RiftScribe);
    2. `mercado`       — o nome é como o CardTrader escreve a carta
                         (`cardtrader_map.market_name`: «Lux - Crownguard» é a
                         «Lux, Crownguard»; «Master Yi - Honed» é a «Yi,
                         Honed»). Não é adivinha: é o nome REGISTADO da mesma
                         impressão noutra fonte;
    3. `sem separador` — igual a menos da vírgula/hífen dos subtítulos
                         («Riven Shattered» = «Riven, Shattered»);
    4. `cauda`         — «Campeão, Subtítulo» → só o subtítulo, e SÓ se a
                         carta for um Legend («Darius, Hand of Noxus» → «Hand
                         of Noxus»): é a regra das listas dos decks
                         (`decks.resolve`), onde nenhum Legend tem vírgula.

O que não casar vai para `nao_encontradas`, visível, com o número. Um nome
mal casado é pior do que um nome em falta.

TER A CARTA NÃO É TER O PROMO. O `vault.db` conta cópias por impressão do
catálogo, e o promo não é uma impressão do catálogo — não há maneira de ele
registar que tem a versão promo. Cada item diz quantas cópias ele tem DA
CARTA (todas as impressões, `tens` e `tens_por`), com a ressalva escrita na
página. Não se inventa um «tens 1/1».
"""

from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone

from . import catalog, config, metrics

# O que a página diz por baixo de cada foto. Vem daqui, e não do `app.js`,
# para o CLI e o site dizerem a mesma coisa.
AVISO_FOTO = ("A foto é da versão NORMAL da carta (a do catálogo da RiftScribe), "
              "não da promo — serve para se ver que carta é.")
AVISO_TER = ("«tens N» conta as cópias da CARTA que estão no vault, em qualquer "
             "versão do catálogo — não diz se alguma é a promo, porque o promo não "
             "é uma impressão do catálogo e não há onde o registar.")

# Cada casamento tem um nome, e é ele que vai no item (`via`) — para se ver na
# página e no CLI por que caminho é que a carta foi encontrada.
VIA_EXACTO, VIA_MERCADO, VIA_SEM_SEP, VIA_CAUDA = "exacto", "mercado", "sem separador", "cauda"
VIAS = (VIA_EXACTO, VIA_MERCADO, VIA_SEM_SEP, VIA_CAUDA)

_SEP = re.compile(r"\s*[-,]\s*")


class ListaInvalida(ValueError):
    """O ficheiro das promos não tem a forma esperada."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --------------------------------------------------------------------------
# A lista
# --------------------------------------------------------------------------


def carregar(caminho=None) -> dict:
    """Lê a lista do disco e valida a forma. Rebenta se faltar o essencial.

    Cada entrada tem de ter `categoria` e `nome`; `origem` e `nota` podem
    faltar (ficam vazios). A ordem do ficheiro é a ordem da página dentro de
    cada categoria — é ele que a escreve.
    """
    caminho = caminho or config.PROMOS_PATH
    try:
        bruto = json.loads(caminho.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ListaInvalida(f"não existe: {caminho}") from None
    except json.JSONDecodeError as e:
        raise ListaInvalida(f"{caminho}: JSON inválido — {e}") from None
    promos = bruto.get("promos")
    if not isinstance(promos, list):
        raise ListaInvalida(f"{caminho}: falta a lista `promos`")
    entradas = []
    for i, p in enumerate(promos):
        if not isinstance(p, dict) or not str(p.get("nome") or "").strip() \
                or not str(p.get("categoria") or "").strip():
            raise ListaInvalida(f"{caminho}: a entrada {i} não tem `categoria` e `nome`")
        entradas.append({
            "categoria": str(p["categoria"]).strip(),
            "origem": str(p.get("origem") or "").strip(),
            "nome": str(p["nome"]).strip(),
            "nota": str(p.get("nota") or "").strip(),
        })
    return {
        "fonte": str(bruto.get("fonte") or ""),
        "url": str(bruto.get("url") or ""),
        "lido_em": str(bruto.get("lido_em") or ""),
        "aviso": str(bruto.get("aviso") or ""),
        "ficheiro": str(caminho),
        "promos": entradas,
    }


# --------------------------------------------------------------------------
# O casamento com o catálogo
# --------------------------------------------------------------------------


def _norm(nome: str) -> str:
    return catalog.card_key_of(nome)


def _sem_sep(nome: str) -> str:
    """«Lux - Crownguard», «Lux, Crownguard» e «Lux Crownguard» dão o mesmo."""
    return re.sub(r"\s+", " ", _SEP.sub(" ", _norm(nome))).strip()


def _indices(con: sqlite3.Connection) -> dict:
    tipos = {r["card_key"]: r["type"] for r in con.execute(
        "SELECT card_key, type FROM catalog.cards")}
    mercado: dict[str, set[str]] = {}
    try:
        rows = con.execute(
            "SELECT m.market_name AS n, p.card_key AS k FROM catalog.cardtrader_map m "
            "JOIN catalog.printings p ON p.printing_id = m.printing_id "
            "WHERE m.market_name IS NOT NULL").fetchall()
    except sqlite3.OperationalError:
        rows = []                       # catálogo sem `riftvault map`
    for r in rows:
        mercado.setdefault(_norm(r["n"]), set()).add(r["k"])
    sem_sep: dict[str, list[str]] = {}
    for k in tipos:
        sem_sep.setdefault(_sem_sep(k), []).append(k)
    return {"tipos": tipos, "mercado": mercado, "sem_sep": sem_sep}


def _casar_um(nome: str, idx: dict) -> tuple[str, str] | None:
    k = _norm(nome)
    if k in idx["tipos"]:
        return k, VIA_EXACTO
    m = idx["mercado"].get(k) or set()
    if len(m) == 1:
        return next(iter(m)), VIA_MERCADO
    c = idx["sem_sep"].get(_sem_sep(nome)) or []
    if len(c) == 1:
        return c[0], VIA_SEM_SEP
    partes = _SEP.split(nome, maxsplit=1)
    if len(partes) == 2:
        c = idx["sem_sep"].get(_sem_sep(partes[1])) or []
        if len(c) == 1 and (idx["tipos"].get(c[0]) or "") == "Legend":
            return c[0], VIA_CAUDA
    return None


def casar(con: sqlite3.Connection, nomes) -> dict[str, tuple[str, str] | None]:
    """nome da lista -> (card_key, via), ou None quando não casa com UMA carta."""
    idx = _indices(con)
    return {n: _casar_um(n, idx) for n in nomes}


# --------------------------------------------------------------------------
# O payload
# --------------------------------------------------------------------------


def _referencia(con: sqlite3.Connection, card_key: str, cfg: dict) -> sqlite3.Row:
    """A impressão cuja foto se mostra: a BASE da edição mais antiga, sem
    sobrenumeração — a versão normal, que é o que a página diz que mostra."""
    rows = con.execute(
        "SELECT * FROM catalog.printings WHERE card_key = ? ORDER BY api_sort",
        (card_key,)).fetchall()
    rows.sort(key=lambda r: (config.set_order(r["set_id"]), r["set_id"], r["api_sort"]))
    for r in rows:
        if r["variant_kind"] == "base" and not metrics.e_overnumbered(r):
            return r
    return rows[0]


def _tens_por(con: sqlite3.Connection, cfg: dict) -> dict[str, list[dict]]:
    """card_key -> as impressões que ele tem, com quantas — menos as retiradas,
    como o `metrics.owned_by_card`."""
    out: dict[str, list[dict]] = {}
    for r in con.execute(
        "SELECT p.card_key, p.public_code, p.variant_kind, p.variant_label, p.type, "
        "p.api_sort, p.set_id, c.qty FROM copies c "
        "JOIN catalog.printings p ON p.printing_id = c.printing_id "
        "WHERE c.qty > 0 ORDER BY p.api_sort"
    ):
        if metrics.retirada(r, cfg):
            continue
        out.setdefault(r["card_key"], []).append(
            {"code": r["public_code"], "kind": r["variant_kind"],
             "label": r["variant_label"], "qty": r["qty"],
             "_ord": (config.set_order(r["set_id"]), r["set_id"], r["api_sort"])})
    for lst in out.values():
        lst.sort(key=lambda x: x.pop("_ord"))
    return out


def _promos_do_catalogo(con: sqlite3.Connection) -> dict[str, list[dict]]:
    """card_key -> as impressões `special` (as `VEN-SP`) que o catálogo já tem."""
    out: dict[str, list[dict]] = {}
    for r in con.execute(
        "SELECT p.card_key, p.printing_id, p.public_code, COALESCE(c.qty, 0) AS qty "
        "FROM catalog.printings p LEFT JOIN copies c ON c.printing_id = p.printing_id "
        "WHERE p.variant_kind = 'special' ORDER BY p.api_sort"
    ):
        out.setdefault(r["card_key"], []).append(
            {"id": r["printing_id"], "code": r["public_code"], "qty": r["qty"]})
    return out


def _slug(texto: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", _norm(texto)).strip("-")
    return s or "outro"


def payload(con: sqlite3.Connection, cfg: dict | None = None,
            image_mode: str = "local", caminho=None) -> dict:
    """A montra inteira: por categoria (as maiores primeiro), cada promo com a
    foto da versão normal, o que ele tem da carta, e a lista do que não casou.

    Não escreve nada e não lê alvos: não há `target`, `missing` nem euros —
    não é uma lista de compra.
    """
    cfg = cfg or config.load()
    lista = carregar(caminho)
    entradas = lista["promos"]
    nomes = sorted({p["nome"] for p in entradas})
    casadas = casar(con, nomes)
    tens_total = metrics.owned_by_card(con, cfg)
    tens_por = _tens_por(con, cfg)
    sp = _promos_do_catalogo(con)

    # Em que outras categorias/origens o mesmo nome aparece («Viktor - Leader»
    # está no evento de lançamento, no Arcane Box Set e na versão chinesa
    # dele): cada tile diz «também: …», para ele não julgar que é repetição.
    onde: dict[str, list[str]] = {}
    for p in entradas:
        rot = p["categoria"] + (f" ({p['origem']})" if p["origem"] and p["origem"] != "-" else "")
        onde.setdefault(p["nome"], []).append(rot)

    referencias: dict[str, sqlite3.Row] = {}
    categorias: dict[str, dict] = {}
    nao_encontradas: list[dict] = []
    for p in entradas:
        cat = categorias.get(p["categoria"])
        if cat is None:
            cat = categorias[p["categoria"]] = {
                "id": _slug(p["categoria"]), "label": p["categoria"],
                "entradas": 0, "cartas": set(), "nao_casadas": 0, "items": []}
        cat["entradas"] += 1
        cat["cartas"].add(p["nome"])
        casada = casadas.get(p["nome"])
        rot = p["categoria"] + (f" ({p['origem']})" if p["origem"] and p["origem"] != "-" else "")
        tambem = [x for x in onde[p["nome"]] if x != rot]
        if casada is None:
            # Fica SÓ na lista das não encontradas — não se inventa um tile
            # sem foto no meio da categoria.
            cat["nao_casadas"] += 1
            nao_encontradas.append({**p, "tambem": tambem})
            continue
        ck, via = casada
        r = referencias.get(ck)
        if r is None:
            r = referencias[ck] = _referencia(con, ck, cfg)
        cat["items"].append({
            **p, "card_key": ck, "via": via,
            "name": r["name"], "type": r["type"], "rarity": r["base_rarity"] or r["rarity"],
            "code": r["public_code"], "printing_id": r["printing_id"],
            "set": r["set_id"],
            "landscape": (r["orientation"] or "").lower() == "landscape",
            "img": f"img/{r['printing_id']}.webp",
            "cdn": r["image_medium"] or r["image_large"] or r["image_url"],
            "tens": tens_total.get(ck, 0),
            "tens_por": tens_por.get(ck, []),
            # As `VEN-SP` da mesma carta, se o catálogo as tiver — a mesma
            # carta vista de outro sítio, com o que ele tem delas.
            "promo_catalogo": sp.get(ck, []),
            "tambem": tambem,
        })

    # As categorias maiores primeiro (Nexus Night, Bundle, …); a empate, a
    # ordem em que aparecem no ficheiro. Dentro de cada uma, a ordem do
    # ficheiro — é ele que a escreve.
    ordem = list(categorias)
    cats = sorted(categorias.values(),
                  key=lambda c: (-c["entradas"], ordem.index(c["label"])))
    for c in cats:
        c["cartas"] = len(c["cartas"])

    casadas_ok = {n for n, v in casadas.items() if v is not None}
    return {
        "generated_at": _now(),
        "image_mode": image_mode,
        "fonte": {k: lista[k] for k in ("fonte", "url", "lido_em", "aviso", "ficheiro")},
        "avisos": {"foto": AVISO_FOTO, "ter": AVISO_TER},
        "totals": {
            "entradas": len(entradas),
            "cartas": len(nomes),
            "casadas": len(casadas_ok),
            "nao_casadas": len(nomes) - len(casadas_ok),
            # Cartas casadas de que ele tem pelo menos uma cópia (em qualquer
            # versão — ver `AVISO_TER`).
            "tens": sum(1 for n in casadas_ok if tens_total.get(casadas[n][0], 0) > 0),
            "por_via": {v: sum(1 for n in casadas_ok if casadas[n][1] == v) for v in VIAS},
        },
        "categorias": cats,
        "nao_encontradas": nao_encontradas,
    }

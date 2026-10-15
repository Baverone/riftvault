"""Constrói o catalog.db a partir da API da RiftScribe.

O trabalho todo desta camada é traduzir o que a API dá (uma lista plana de
entradas com um campo `variant`) para os dois grãos de que o site precisa:

  - IMPRESSÃO (printing) — uma entrada da API. É onde se contam as cópias.
  - CARTA LÓGICA (card)   — o nome. É onde se conta o playset jogável.

E, pelo meio, resolver as duas armadilhas documentadas no CLAUDE.md:
`(set_id, collector_number)` não é único, e a mesma carta reaparece com
números de coleção diferentes (até dentro da mesma edição).
"""

from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from datetime import datetime, timezone

from . import config, db, riftscribe

# --------------------------------------------------------------------------
# Derivações a partir do campo `variant`
# --------------------------------------------------------------------------

# Variantes que partilham a "lane" principal com a carta base, ou seja, que
# aparecem no mesmo tile-grupo da grelha.
MAIN_VARIANTS = {"", "a", "star"}

LANE_KINDS = {"t": "token", "r": "rune_promo", "sp": "special",
              # As promos de evento da dotgg (`RAD-038-P`, `RAD-038-P2`,
              # 2026-10-15): a RiftScribe não as tem em edição nenhuma. São a
              # promo, como as `sp`; a regra delas sai da raridade (`dotgg`).
              "p": "special"}

# Uma variante de série com um `a` no fim (`r01a`, a `RAD-R01A` da dotgg) é a
# ARTE ALTERNATIVA dessa série — é o mesmo sufixo do `OGN-007a`. Sem isto uma
# runa em alt art da Radiance era `rune_promo` e escapava à regra de 2026-09-17
# (*"deixa as runas Alt Art, nao incluas em nada"*), que pergunta pelo kind.
_SERIE_ALT = re.compile(r"^[a-z]+\d+a$")

LABELS = {
    "base": "Base",
    "alt_art": "Arte alt.",
    "special_alt": "Special Alt",
    "signature": "Signature",
    "token": "Token",
    "rune_promo": "Runa promo",
    "special": "Promo",
    "unknown": "Variante ?",
}


def lane_of(variant: str) -> str:
    if variant in MAIN_VARIANTS:
        return "main"
    m = re.match(r"^([a-z]+)", variant or "")
    return m.group(1) if m else "other"


def variantes_extra(cfg: dict | None = None) -> dict[str, str]:
    """`variantes_extra` do config: variante (ou o prefixo dela) -> kind.

    A PORTA PARA UMA VARIANTE NOVA (2026-10-15, a preparar a Radiance). A API
    da RiftScribe documenta só `''`, `a`, `star` e `tNN`; o que uma edição nova
    trouxer para as Special Alt (as K/DA) não se sabe — pode ser um `b`, um
    `ka`, outra coisa. Em vez de adivinhar no código, escreve-se aqui numa
    linha (`{"b": "special_alt"}`) e o sync seguinte classifica-as. Vazio hoje.
    Um kind que o riftvault não conheça REBENTA: ficava `unknown` em silêncio.
    """
    from . import metrics

    cfg = cfg if cfg is not None else config.load()
    bruto = cfg.get("variantes_extra") or {}
    out: dict[str, str] = {}
    for k, v in bruto.items():
        if str(k).startswith("_"):
            continue
        kind = str(v).strip().lower()
        if kind not in metrics.KIND_ORDER or kind == "unknown":
            raise ValueError(
                f"variantes_extra: {k!r} -> {v!r} não é um kind que o riftvault "
                f"conheça. Aceita: {', '.join(sorted(set(metrics.KIND_ORDER) - {'unknown'}))}")
        out[str(k).strip().lower()] = kind
    return out


def kind_of(variant: str, extra: dict[str, str] | None = None,
            set_id: str | None = None) -> str:
    """O `variant_kind` de uma variante.

    O `variantes_extra` aceita também `EDIÇÃO:variante` (`"RAD:sp": "special_alt"`),
    que só vale nessa edição e ganha às outras escritas — é o que deixa as SP de
    uma edição serem outra coisa sem mudar as `VEN-SP`, que são as mesmas letras.
    """
    if variant == "":
        return "base"
    if variant == "a":
        return "alt_art"
    if variant == "star":
        return "signature"
    extra = extra or {}
    v = (variant or "").lower()
    if set_id:
        s = set_id.lower()
        for chave in (f"{s}:{v}", f"{s}:{lane_of(variant)}"):
            if chave in extra:
                return extra[chave]
    # A variante inteira primeiro (`b`), depois o prefixo dela (`ka` de `ka1`).
    if v in extra:
        return extra[v]
    if lane_of(variant) in extra:
        return extra[lane_of(variant)]
    if _SERIE_ALT.match(v):
        return "alt_art"
    return LANE_KINDS.get(lane_of(variant), "unknown")


def card_key_of(name: str) -> str:
    """Chave da carta lógica: o nome, normalizado.

    O número de coleção NÃO serve — ver ARMADILHA 2 no CLAUDE.md.
    """
    s = unicodedata.normalize("NFKC", name or "").strip().casefold()
    return re.sub(r"\s+", " ", s)


def aliases_of(row: dict) -> set[str]:
    """Formas de escrever uma impressão que o CLI e as decklists devem aceitar."""
    out: set[str] = set()
    pid = row["printing_id"]
    set_id = row["set_id"].lower()
    cn = row["collector_number"]
    variant = row["variant"]

    out.add(pid.lower())
    code = (row.get("public_code") or "").lower()
    if code:
        out.add(code)
        out.add(code.split("/")[0])  # 'ogn-007a/298' -> 'ogn-007a'

    if variant in MAIN_VARIANTS:
        suffixes = {"": [""], "a": ["a"], "star": ["-star", "*", "star"]}[variant]
        for suf in suffixes:
            out.add(f"{set_id}-{cn}{suf}")
            out.add(f"{set_id}-{cn:03d}{suf}")
    elif lane_of(variant) == "p":
        # As promos de evento (`RAD-038-P`) não têm número de série próprio: são
        # a promo DAQUELA carta. Um `rad-p` sozinho servia a todas.
        out.add(f"{set_id}-{cn}-{variant}")
        out.add(f"{set_id}-{cn:03d}-{variant}")
    else:
        out.add(f"{set_id}-{variant}")

    return {a for a in out if a}


# --------------------------------------------------------------------------
# Sync
# --------------------------------------------------------------------------


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _to_row(api: dict, api_sort: int, cfg: dict) -> dict:
    variant = api.get("variant") or ""
    kind = kind_of(variant, variantes_extra(cfg), api.get("set_id"))
    lane = lane_of(variant)
    stats = api.get("stats") or {}
    key = card_key_of(api.get("name", ""))
    return {
        "printing_id": api["id"],
        "set_id": api["set_id"],
        "collector_number": api["collector_number"],
        "variant": variant,
        "lane": lane,
        "group_key": f"{api['set_id']}|{api['collector_number']}|{lane}",
        "variant_kind": kind,
        "variant_label": LABELS.get(kind, LABELS["unknown"]),
        "card_key": key,
        "public_code": api.get("public_code"),
        "name": api.get("name"),
        "rarity": api.get("rarity"),
        "base_rarity": api.get("rarity"),  # corrigido a seguir, pelo grupo
        "faction": api.get("faction"),
        "domains_json": json.dumps(api.get("domains") or [], ensure_ascii=False),
        "type": api.get("type"),
        "orientation": api.get("orientation"),
        "energy": stats.get("energy"),
        "might": stats.get("might"),
        "power": stats.get("power"),
        "is_banned": 1 if api.get("is_banned") else 0,
        "is_token": 1 if (kind == "token" or key in set(cfg.get("token_card_keys", []))) else 0,
        "description": api.get("description"),
        "flavor_text": api.get("flavor_text"),
        "artist": (api.get("art") or {}).get("artist"),
        "keywords_json": json.dumps(api.get("keywords") or [], ensure_ascii=False),
        "tags_json": json.dumps(api.get("tags") or [], ensure_ascii=False),
        "image_url": api.get("image"),
        "image_small": (api.get("image_thumb") or {}).get("small"),
        "image_medium": (api.get("image_thumb") or {}).get("medium"),
        "image_large": (api.get("image_thumb") or {}).get("large"),
        "image_path": None,
        "api_sort": api_sort,
        "fetched_at": _now(),
        "fonte": FONTE,
    }


#: De onde veio a linha (2026-10-15). A RiftScribe é a fonte do catálogo; a
#: dotgg (`dotgg.py`) só traz as edições que ela ainda não tem.
FONTE = "riftscribe"


_INSERT = """
INSERT INTO printings (
    printing_id, set_id, collector_number, variant, lane, group_key,
    variant_kind, variant_label, card_key, public_code, name, rarity,
    base_rarity, faction, domains_json, type, orientation, energy, might,
    power, is_banned, is_token, description, flavor_text, artist,
    keywords_json, tags_json, image_url, image_small, image_medium,
    image_large, image_path, api_sort, fetched_at, fonte
) VALUES (
    :printing_id, :set_id, :collector_number, :variant, :lane, :group_key,
    :variant_kind, :variant_label, :card_key, :public_code, :name, :rarity,
    :base_rarity, :faction, :domains_json, :type, :orientation, :energy,
    :might, :power, :is_banned, :is_token, :description, :flavor_text,
    :artist, :keywords_json, :tags_json, :image_url, :image_small,
    :image_medium, :image_large, :image_path, :api_sort, :fetched_at, :fonte
)
ON CONFLICT(printing_id) DO UPDATE SET
    set_id=excluded.set_id, collector_number=excluded.collector_number,
    variant=excluded.variant, lane=excluded.lane, group_key=excluded.group_key,
    variant_kind=excluded.variant_kind, variant_label=excluded.variant_label,
    card_key=excluded.card_key, public_code=excluded.public_code,
    name=excluded.name, rarity=excluded.rarity, base_rarity=excluded.base_rarity,
    faction=excluded.faction, domains_json=excluded.domains_json,
    type=excluded.type, orientation=excluded.orientation, energy=excluded.energy,
    might=excluded.might, power=excluded.power, is_banned=excluded.is_banned,
    is_token=excluded.is_token, description=excluded.description,
    flavor_text=excluded.flavor_text, artist=excluded.artist,
    keywords_json=excluded.keywords_json, tags_json=excluded.tags_json,
    image_url=excluded.image_url, image_small=excluded.image_small,
    image_medium=excluded.image_medium, image_large=excluded.image_large,
    api_sort=excluded.api_sort, fetched_at=excluded.fetched_at,
    fonte=excluded.fonte
"""


def sync(set_ids: list[str] | None = None, delay: float = riftscribe.POLITE_DELAY,
         log=print) -> dict:
    """Descarrega o catálogo para o catalog.db. Devolve um resumo."""
    cfg = config.reload()
    con = db.catalog_only()

    discovered = riftscribe.list_sets()
    targets = [s for s in (set_ids or discovered) if s]
    unknown_variants: set[str] = set()
    counts: dict[str, int] = {}
    vazias: list[str] = []

    for set_id in targets:
        if set_id not in discovered:
            log(f"  ! {set_id} não aparece em /api/cards/filters — a saltar")
            continue
        log(f"  {set_id}: a descarregar...")
        rows = []
        for i, api in enumerate(riftscribe.iter_cards(set_id, delay=delay)):
            row = _to_row(api, i, cfg)
            if row["variant_kind"] == "unknown":
                unknown_variants.add(row["variant"])
            rows.append(row)

        if not rows:
            # O /api/cards/filters anunciou esta edição e o /api/cards não
            # devolveu nada. Isso é uma falha da API, não uma edição vazia — a
            # RiftScribe nunca lista um set sem cartas. Apagar aqui as
            # impressões deitava fora o catálogo de uma edição inteira, e o
            # `build` a seguir publicava um site sem ela sem dar erro nenhum:
            # exatamente o modo de falha que não se quer, verde a fingir.
            vazias.append(set_id)
            log(f"  ! {set_id}: a API não devolveu nenhuma entrada — "
                f"catálogo mantido como estava")
            continue

        # A raridade da VARIANTE não serve para contar: quase todas as artes
        # alternativas vêm como 'showcase'. Vale a raridade da base do grupo.
        base_rarity = {r["group_key"]: r["rarity"] for r in rows if r["variant_kind"] == "base"}
        for r in rows:
            r["base_rarity"] = base_rarity.get(r["group_key"], r["rarity"])

        out = gravar_edicao(con, set_id, rows, FONTE)
        counts[set_id] = out["n"]
        log(f"  {set_id}: {len(rows)} impressões"
            + (f" ({out['reaproveitados']} já estavam no catálogo com outro id — "
               f"ficou o de lá)" if out["reaproveitados"] else ""))

    rebuild_cards(con)
    rebuild_aliases(con)
    con.close()

    return {
        "sets": counts,
        "total": sum(counts.values()),
        "unknown_variants": sorted(unknown_variants),
        "sets_vazias": vazias,
        # As edições que o config não nomeia (2026-10-15, a Radiance). ENTRAM
        # NA MESMA — o catálogo é que decide que edições há, não o config —,
        # com a omissão do `config.set_name`/`set_order`: o código como nome
        # (que é o que ele escolheu para todas menos o OGS, 2026-08-31) e
        # depois das conhecidas, por ordem alfabética. O sync NÃO escreve no
        # config: diz-se, para ele lhe dar nome ou ordem se quiser.
        "sets_novos": sorted(s for s in counts if s not in (cfg.get("sets") or {})),
    }


def _natural(r) -> tuple:
    """A impressão sem o id: o número e a variante, dentro da edição.

    É a mesma chave com que o `prices.sync_map` casa o CardTrader com a
    RiftScribe (número + sufixo), e é única em todas as edições do catálogo.
    """
    return (int(r["collector_number"]), str(r["variant"] or "").lower())


def _larga(r) -> tuple:
    """A segunda chave, para quando duas fontes escrevem a mesma variante de
    maneira diferente (`sp1` e `sp01`): o número, a família, a categoria e a
    carta. Só se usa se casar com UMA linha — duas é ambiguidade, e aí não se
    escolhe."""
    return (int(r["collector_number"]), lane_of(str(r["variant"] or "")),
            r["variant_kind"], r["card_key"])


def gravar_edicao(con: sqlite3.Connection, set_id: str, rows: list[dict],
                  fonte: str) -> dict:
    """Escreve as impressões de UMA edição, vindas de UMA fonte. Devolve a conta.

    **O `printing_id` QUE JÁ EXISTE FICA (2026-10-15).** A RiftScribe e a dotgg
    dão ids diferentes à mesma impressão (`rad-001-<tamanho>` contra `rad-001`)
    e a `copies` — de todos os utilizadores — guarda o id sem chave estrangeira.
    Antes disto o sync apagava o que a API deixou de devolver e inseria o novo:
    a impressão mudava de id e as cópias dele ficavam ÓRFÃS, sem erro nenhum.
    Agora a linha que chega procura a que já lá está pela impressão (número e
    variante; ou, se as fontes escreverem a variante de outra maneira, número,
    categoria e carta — só se casar com uma) e, se a achar, fica com o id DELA.
    Assim não há migração de ids em `vault.db` nenhum: as cópias do André, do
    Miguel, do Gonçalves e do Rafael não se tocam.

    **Cada fonte só apaga o que é seu.** A RiftScribe não tem as promos de
    evento que a dotgg tem; apagar «o que a API não devolveu» deitava-as fora.

    **A dotgg não escreve por cima da RiftScribe.** Uma linha que a RiftScribe
    já trouxe é dela: a dotgg só tapa o que ela não tem.
    """
    existentes = [dict(r) for r in con.execute(
        "SELECT printing_id, collector_number, variant, variant_kind, card_key, fonte "
        "FROM printings WHERE set_id = ?", (set_id,))]
    por_nat = {_natural(e): e for e in existentes}
    por_larga: dict[tuple, list[dict]] = {}
    for e in existentes:
        por_larga.setdefault(_larga(e), []).append(e)

    tomados: set[str] = set()
    reaproveitados = mantidas = 0
    escrever = []
    ids = []
    for r in rows:
        e = por_nat.get(_natural(r))
        if e is not None and e["printing_id"] in tomados:
            e = None
        if e is None:
            cands = [x for x in por_larga.get(_larga(r), []) if x["printing_id"] not in tomados]
            e = cands[0] if len(cands) == 1 else None
        if e is not None:
            tomados.add(e["printing_id"])
            if e["printing_id"] != r["printing_id"]:
                r = {**r, "printing_id": e["printing_id"]}
                reaproveitados += 1
            if fonte != FONTE and (e["fonte"] or FONTE) != fonte:
                # É da RiftScribe: fica como ela a escreveu.
                mantidas += 1
                ids.append(r["printing_id"])
                continue
        ids.append(r["printing_id"])
        escrever.append(r)

    con.execute("BEGIN")
    try:
        # Impressões que ESTA fonte deixou de devolver saem do catálogo.
        placeholders = ",".join("?" * len(ids))
        con.execute(
            f"DELETE FROM printings WHERE set_id = ? AND COALESCE(fonte, ?) = ? "
            f"AND printing_id NOT IN ({placeholders})",
            [set_id, FONTE, fonte] + ids,
        )
        con.executemany(_INSERT, escrever)
        n = con.execute("SELECT COUNT(*) FROM printings WHERE set_id = ?",
                        (set_id,)).fetchone()[0]
        con.execute(
            "INSERT INTO sets (set_id, name, sort_order, n_printings, synced_at) "
            "VALUES (?,?,?,?,?) ON CONFLICT(set_id) DO UPDATE SET "
            "name=excluded.name, sort_order=excluded.sort_order, "
            "n_printings=excluded.n_printings, synced_at=excluded.synced_at",
            (set_id, config.set_name(set_id), config.set_order(set_id), n, _now()),
        )
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    return {"n": n, "escritas": len(escrever), "reaproveitados": reaproveitados,
            "mantidas": mantidas}


def rebuild_cards(con: sqlite3.Connection) -> int:
    """Reconstrói a tabela `cards` (a carta lógica) a partir das impressões."""
    cfg = config.load()
    forced_tokens = set(cfg.get("token_card_keys", []))
    orders = {s: config.set_order(s) for s in
              (r["set_id"] for r in con.execute("SELECT DISTINCT set_id FROM printings"))}

    rows = con.execute(
        "SELECT printing_id, card_key, name, type, faction, domains_json, "
        "       is_banned, is_token, variant_kind, set_id, collector_number "
        "FROM printings"
    ).fetchall()

    by_key: dict[str, list[sqlite3.Row]] = {}
    for r in rows:
        by_key.setdefault(r["card_key"], []).append(r)

    out = []
    for key, group in by_key.items():
        # Representante = a impressão base mais antiga (edição mais baixa,
        # depois número de coleção mais baixo). É a que dá o tipo e a imagem
        # que a vista de decks vai mostrar.
        def rank(r: sqlite3.Row):
            return (0 if r["variant_kind"] == "base" else 1,
                    orders.get(r["set_id"], 999), r["collector_number"])

        rep = min(group, key=rank)
        out.append((
            key, rep["name"], rep["type"], rep["faction"], rep["domains_json"],
            1 if any(r["is_banned"] for r in group) else 0,
            1 if (key in forced_tokens or any(r["is_token"] for r in group)) else 0,
            rep["printing_id"], len(group),
        ))

    con.execute("BEGIN")
    con.execute("DELETE FROM cards")
    con.executemany(
        "INSERT INTO cards (card_key, name, type, faction, domains_json, "
        "is_banned, is_token, rep_printing_id, n_printings) VALUES (?,?,?,?,?,?,?,?,?)",
        out,
    )
    # O flag de token é da carta lógica: propaga-se de volta às impressões,
    # senão o OGN-271 ("Recruit (DE)", token com número normal) pediria playset.
    con.execute(
        "UPDATE printings SET is_token = 1 WHERE card_key IN "
        "(SELECT card_key FROM cards WHERE is_token = 1)"
    )
    con.execute("COMMIT")
    return len(out)


def rebuild_aliases(con: sqlite3.Connection) -> int:
    rows = con.execute(
        "SELECT printing_id, set_id, collector_number, variant, public_code FROM printings"
    ).fetchall()
    pairs = []
    for r in rows:
        for alias in aliases_of(dict(r)):
            pairs.append((alias, r["printing_id"]))

    con.execute("BEGIN")
    con.execute("DELETE FROM printing_aliases")
    # INSERT OR IGNORE: um alias ambíguo fica com a primeira impressão. Só
    # acontece se a API alguma vez colidir códigos; o `id` completo é sempre
    # inequívoco e serve de escape.
    con.executemany("INSERT OR IGNORE INTO printing_aliases (alias, printing_id) VALUES (?,?)", pairs)
    con.execute("COMMIT")
    return len(pairs)


# --------------------------------------------------------------------------
# Cache local das imagens
# --------------------------------------------------------------------------


def image_filename(printing_id: str) -> str:
    return f"{printing_id}.webp"


def sync_images(set_ids: list[str] | None = None, log=print) -> dict:
    """Descarrega os thumbnails em falta para data/images/. É retomável."""
    cfg = config.load()
    size = cfg.get("image_size", "medium")
    col = {"small": "image_small", "medium": "image_medium", "large": "image_large"}[size]

    config.ensure_dirs()
    con = db.catalog_only()
    sql = f"SELECT printing_id, {col} AS url FROM printings WHERE {col} IS NOT NULL"
    params: tuple = ()
    if set_ids:
        sql += " AND set_id IN (%s)" % ",".join("?" * len(set_ids))
        params = tuple(set_ids)
    sql += " ORDER BY set_id, api_sort"

    rows = con.execute(sql, params).fetchall()
    got = skipped = failed = 0
    for i, r in enumerate(rows, 1):
        path = config.IMAGES_DIR / image_filename(r["printing_id"])
        if path.exists() and path.stat().st_size > 0:
            skipped += 1
            continue
        try:
            path.write_bytes(riftscribe.download(r["url"]))
            got += 1
        except riftscribe.RiftScribeError as exc:
            failed += 1
            log(f"  ! {r['printing_id']}: {exc}")
        if got and got % 50 == 0:
            log(f"  ... {i}/{len(rows)} ({got} novas)")

    con.execute("UPDATE printings SET image_path = printing_id || '.webp'")
    con.close()
    return {"downloaded": got, "cached": skipped, "failed": failed, "total": len(rows)}

"""A SEGUNDA FONTE DO CATÁLOGO: a API do riftbound.gg (`api.dotgg.gg`), só para as
edições que a RiftScribe ainda não tem.

André, 2026-10-15, sobre a Radiance (sai a 23/10, e nesse dia não estava em
fonte nenhuma que o riftvault lesse): *"coloca agora essas, dia 23 apenas
confirmas se está tudo bem"* — e, sobre a regra de não ir ao riftbound.gg,
*"usa sempre que possivel"*. A regra caiu nesse dia, por decisão dele.

A RiftScribe CONTINUA A SER A FONTE das outras edições. Isto só traz as edições
escritas em `dotgg.edicoes` (hoje `["RAD"]`), e quando a RiftScribe publicar a
mesma edição o `catalog.sync` dela toma conta das linhas que reconhecer, SEM
mudar o `printing_id` (ver `catalog.gravar_edicao`) — é isso que mantém as
cópias que ele marcar entretanto agarradas à impressão certa.

A RESPOSTA DA DOTGG (medida a 2026-10-15): `{"names": [colunas], "data":
[[...], ...]}`, 1770 linhas de todas as edições, com `id` (`RAD-038`,
`RAD-038A`, `RAD-168-STAR`, `RAD-038-P`, `RAD-R01`, `RAD-R01A`, `RAD-T02`,
`RAD-SP1`), `name` (`Ahri - Confident`), `color`, `cost`, `might`, `power`,
`type`, `rarity` (`Common` … `Showcase`), `promo` (`"1"` = o símbolo de Promo)
e `image`. NÃO traz o denominador do código impresso nem o nome de artista.

Tudo o que aqui se traduz foi MEDIDO contra o catálogo da RiftScribe nas cinco
edições que as duas têm (2026-10-15): os nomes (`Ahri - Confident` -> `Ahri,
Confident` em 295 cartas; os Legends ficam só com o título, `Kai'Sa - Daughter
of the Void` -> `Daughter of the Void`, em 118), os domínios (a facção é o
primeiro da dotgg, os domínios por ordem alfabética), o `cost` é a `energy`, e
o `power` a 0 é «não tem» (a RiftScribe dá `None`).
"""

from __future__ import annotations

import json
import re
import urllib.request

from . import config

URL_CARTAS = "https://api.dotgg.gg/cgfw/getcards?game=riftbound&mode=indexed&part=cards"
# ASCII puro: com acentos há servidores que respondem 403 (ver o CardTrader).
USER_AGENT = "riftvault/1.0 (colecao pessoal; +github)"
TIMEOUT = 60

DEFAULTS = {"edicoes": ["RAD"], "tamanhos": {"RAD": 167}}

#: o `id` da dotgg partido: edição, número, sufixo. `RAD-001`, `RAD-001A`,
#: `RAD-168-STAR`, `RAD-038-P`, `RAD-038-P2`.
_ID_MAIN = re.compile(r"^([A-Z0-9]+)-(\d+)(A|-STAR|-P2|-P)?$")
#: as séries próprias, fora da numeração da edição: `RAD-R01`, `RAD-R01A`,
#: `RAD-T02`, `RAD-SP1`.
_ID_SERIE = re.compile(r"^([A-Z0-9]+)-(R|T|SP)(\d+)(A)?$")
#: o que vem a seguir ao nome numa promo de evento: «(Radiance December 2026
#: Summoner Skirmish Top 8 Promo)». Tira-se para a promo cair na MESMA carta
#: lógica da base — senão o «Ahri, Confident» ficava duas cartas.
_PARENTESE_FINAL = re.compile(r"\s*\([^()]*\)\s*$")


class DotggError(RuntimeError):
    pass


class IdDesconhecido(ValueError):
    """Um `id` que não segue nenhum dos padrões medidos — diz-se, não se adivinha."""


def opcoes(cfg: dict | None = None) -> dict:
    cfg = cfg if cfg is not None else config.load()
    out = dict(DEFAULTS)
    out.update({k: v for k, v in (cfg.get("dotgg") or {}).items() if not k.startswith("_")})
    return out


def edicoes(cfg: dict | None = None) -> list[str]:
    return [str(s).upper() for s in (opcoes(cfg).get("edicoes") or [])]


def tamanho(set_id: str, cfg: dict | None = None) -> int | None:
    """O último número da sequência da edição — o denominador que a dotgg não dá.

    É o que faz um número acima dele ser SOBRENUMERADO (`metrics.e_overnumbered`
    lê-o do `public_code`). Para a RAD é 167: medido na dotgg (1 a 167 sem
    buracos; do 168 ao 184 são todas Showcase — os nove Legends da edição e
    oito Units/Battlefield) e dito por ele. O número impresso no cartão não se sabe — o
    `public_code` que daqui sai é substituído pelo da RiftScribe quando ela
    publicar a edição.
    """
    v = (opcoes(cfg).get("tamanhos") or {}).get(set_id.upper())
    return int(v) if v else None


def buscar(timeout: int = TIMEOUT) -> list[dict]:
    """Um pedido só (1770 linhas, ~750 KB). Devolve as linhas como dicionários."""
    req = urllib.request.Request(URL_CARTAS, headers={"User-Agent": USER_AGENT,
                                                      "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                raise DotggError(f"{URL_CARTAS} devolveu HTTP {resp.status}")
            corpo = json.loads(resp.read().decode("utf-8"))
    except DotggError:
        raise
    except Exception as exc:  # rede, JSON partido — é tudo «a fonte falhou»
        raise DotggError(f"falhou o pedido à dotgg: {exc}") from exc
    return linhas(corpo)


def linhas(corpo: dict) -> list[dict]:
    """`{"names": [...], "data": [[...]]}` -> uma lista de dicionários."""
    nomes = corpo.get("names")
    dados = corpo.get("data")
    if not isinstance(nomes, list) or not isinstance(dados, list) or "id" not in nomes:
        raise DotggError("a resposta da dotgg não tem a forma medida (names/data/id)")
    return [dict(zip(nomes, d)) for d in dados]


def partir_id(gid: str) -> tuple[str, int, str]:
    """`RAD-038A` -> (`RAD`, 38, `a`) — a edição, o número e a VARIANTE.

    A variante escreve-se como a RiftScribe a escreve nas edições que já tem
    (medido): `''` base, `a` arte alternativa, `star` assinada, `r01`/`t02`/
    `sp1` as séries próprias (as runas, os tokens, as SP). As duas que a
    RiftScribe não tem em edição nenhuma ganham o nome mais curto que as
    distingue: `p`/`p2` as promos de evento (`RAD-038-P`) e `r01a` a runa em
    arte alternativa (`RAD-R01A`).
    """
    m = _ID_MAIN.match(gid or "")
    if m:
        sid, n, suf = m.groups()
        variante = {None: "", "A": "a", "-STAR": "star", "-P": "p", "-P2": "p2"}[suf]
        return sid, int(n), variante
    m = _ID_SERIE.match(gid or "")
    if m:
        sid, serie, n, alt = m.groups()
        largura = 1 if serie == "SP" else 2          # `ven-sp4`, `ven-r04`, `ven-t04`
        return sid, int(n), f"{serie.lower()}{int(n):0{largura}d}{'a' if alt else ''}"
    raise IdDesconhecido(f"id da dotgg que não segue nenhum padrão medido: {gid!r}")


def nome(linha: dict) -> str:
    """O nome à maneira da RiftScribe — é dele que sai a carta lógica.

    Medido nas 1180 impressões que as duas fontes têm: os Legends ficam só com
    o título (118), o resto troca o « - » por «, » (295), e um « // » (os
    tokens de duas faces) fica com a primeira face. As promos de evento perdem
    o parêntese do fim, para cair na carta da base.
    """
    n = (linha.get("name") or "").strip()
    if str(linha.get("promo") or "0") == "1":
        n = _PARENTESE_FINAL.sub("", n)
    if " // " in n:
        n = n.split(" // ", 1)[0]
    tipo = _tipo(linha)
    if tipo == "Legend" and " - " in n:
        return n.split(" - ", 1)[1].strip()
    return n.replace(" - ", ", ")


def _tipo(linha: dict) -> str | None:
    t = linha.get("type")
    if isinstance(t, list):
        return t[0] if t else None
    return t or None


def _int(v) -> int | None:
    if v is None or v == "":
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def para_linha(linha: dict, api_sort: int, cfg: dict) -> dict:
    """Uma linha da dotgg -> uma linha da `catalog.printings`, com a FORMA do
    `catalog._to_row` (as mesmas chaves, os mesmos significados)."""
    from . import catalog

    sid, cn, variante = partir_id(linha["id"])
    kind = catalog.kind_of(variante, catalog.variantes_extra(cfg), sid)
    lane = catalog.lane_of(variante)
    n = nome(linha)
    key = catalog.card_key_of(n)
    raridade = (linha.get("rarity") or "").strip().lower() or None
    promo = str(linha.get("promo") or "0") == "1"
    cores = [c for c in (linha.get("color") or []) if c]
    tam = tamanho(sid, cfg)

    # O CÓDIGO IMPRESSO. Na sequência leva o denominador (`RAD-001/167`): é dele
    # que o `metrics.e_overnumbered` lê que o 168 passa o tamanho. As séries
    # próprias e as promos ficam sem ele, como as `VEN-R01` da RiftScribe — são
    # numeradas fora da edição e nunca a podem passar.
    if lane == "main" and variante in ("", "a", "star") and tam:
        suf = {"": "", "a": "a", "star": "*"}[variante]
        codigo = f"{sid}-{cn:03d}{suf}/{tam}"
    elif lane in ("main", "p"):
        codigo = f"{sid}-{cn:03d}-{variante.upper()}"
    else:
        codigo = f"{sid}-{variante.upper()}"

    url = linha.get("image") or None
    return {
        # O id é o da dotgg em minúsculas. Fica para sempre: quando a RiftScribe
        # trouxer esta impressão com o id dela, quem fica é este (ver
        # `catalog.gravar_edicao`), porque é a ele que as cópias estão agarradas.
        "printing_id": linha["id"].lower(),
        "set_id": sid,
        "collector_number": cn,
        "variant": variante,
        "lane": lane,
        "group_key": f"{sid}|{cn}|{lane}",
        "variant_kind": kind,
        "variant_label": catalog.LABELS.get(kind, catalog.LABELS["unknown"]),
        "card_key": key,
        "public_code": codigo,
        "name": n,
        # O SÍMBOLO DE PROMO (`promo = "1"`) vai para a RARIDADE: é lá que a regra
        # dele de 2026-10-15 o procura (`master_set.raridades_promo`, *"se tiver
        # o simbolo de Promo na raridade"*). A raridade impressa ao lado (Rare)
        # fica na `base_rarity`, que é a que conta nos quadros.
        "rarity": "promo" if promo else raridade,
        "base_rarity": raridade,
        "faction": cores[0].lower() if cores else None,
        "domains_json": json.dumps(sorted(cores), ensure_ascii=False),
        "type": _tipo(linha),
        "orientation": "landscape" if _tipo(linha) == "Battlefield" else "portrait",
        "energy": _int(linha.get("cost")),
        "might": _int(linha.get("might")),
        "power": _int(linha.get("power")) or None,
        "is_banned": 1 if str(linha.get("banned") or "0") == "1" else 0,
        "is_token": 1 if (kind == "token" or key in set(cfg.get("token_card_keys", []))) else 0,
        "description": (linha.get("effect") or "").replace("<br />", "\n") or None,
        "flavor_text": linha.get("flavor") or None,
        "artist": None,                       # a dotgg não o dá
        "keywords_json": "[]",
        "tags_json": "[]",
        "image_url": url,
        "image_small": url,
        "image_medium": url,
        "image_large": url,
        "image_path": None,
        "api_sort": api_sort,
        "fetched_at": catalog._now(),
        "fonte": FONTE,
    }


FONTE = "dotgg"

#: Dentro da família principal, a ordem que a RiftScribe usa no OGN, SFD e UNL
#: (medido a 2026-10-15): a base, depois a arte alternativa, depois a assinada.
_ORDEM_MAIN = {"": 0, "a": 1, "star": 2}


def chave_de_ordem(r: dict) -> tuple:
    """A posição de uma impressão na edição: o NÚMERO, e dentro dele a variante.

    André, 2026-10-15, a olhar para a aba da Radiance: *"nao podes ordenar por
    numeraçao?"*. A dotgg devolve as cartas por ordem ALFABÉTICA de nome, e o
    `api_sort` saía dessa ordem — a RAD lia-se Ahri, Akali, Amateur… enquanto as
    outras cinco se leem pelo número.

    A ordem das variantes dentro do mesmo número segue a da RiftScribe, medida
    nas edições dela (não inventada): a família principal primeiro (`''`, `a`,
    `star` — OGN 30× base+alt, 12× base+assinada), e as séries próprias a seguir,
    por ordem do nome da variante (VEN: `''`, `r01`, `sp1`; e `''`, `r04`, `sp4`,
    `t04`; UNL/SFD: `''`, `t01`). As promos de evento (`p`, `p2`) a RiftScribe não
    as tem: são a promo DAQUELA carta, por isso ficam coladas à família principal,
    antes das séries. A runa em alt art (`r01a`) cai a seguir à `r01` sozinha.
    """
    v = str(r.get("variant") or "")
    lane = r.get("lane") or ""
    if v in _ORDEM_MAIN:
        dentro = (0, _ORDEM_MAIN[v], "")
    elif lane == "p":
        dentro = (1, 0, v)
    else:
        dentro = (2, 0, v)
    return (int(r["collector_number"]),) + dentro


def ordenar(rows: list[dict]) -> list[dict]:
    """As linhas de UMA edição pela ordem do número, com o `api_sort` 0..n-1."""
    out = sorted(rows, key=chave_de_ordem)
    for i, r in enumerate(out):
        r["api_sort"] = i
    return out


def sync(set_ids: list[str] | None = None, log=print, linhas_api: list[dict] | None = None) -> dict:
    """Traz as edições do `dotgg.edicoes` para o catálogo. Pode voltar a correr.

    `linhas_api` é para os testes (sem rede). As linhas de uma edição que a
    RiftScribe já trouxe NÃO são escritas por cima — a RiftScribe manda nas
    dela; a dotgg só tapa o que ela não tem.
    """
    from . import catalog, db

    cfg = config.reload()
    alvo = [s.upper() for s in (set_ids or edicoes(cfg))]
    fora = [s for s in alvo if s not in edicoes(cfg)]
    if fora:
        raise ValueError(f"{', '.join(fora)} não está em `dotgg.edicoes` — a dotgg só "
                         f"serve as edições que lá estão escritas; as outras são da RiftScribe.")
    todas = linhas_api if linhas_api is not None else buscar()
    con = db.catalog_only()
    res = {"sets": {}, "estranhos": [], "unknown_variants": [], "sets_vazias": [],
           "reaproveitados": 0, "da_riftscribe": 0}
    desconhecidas: set[str] = set()
    try:
        for sid in alvo:
            rows = []
            for i, ln in enumerate(l for l in todas if str(l.get("id", "")).upper().startswith(sid + "-")):
                try:
                    r = para_linha(ln, i, cfg)
                except IdDesconhecido as exc:
                    res["estranhos"].append(str(exc))
                    continue
                if r["set_id"] != sid:
                    continue
                if r["variant_kind"] == "unknown":
                    desconhecidas.add(r["variant"])
                rows.append(r)
            # O `api_sort` sai do NÚMERO, não da ordem de chegada (alfabética).
            # Isto só vale enquanto a edição for toda da dotgg: com linhas da
            # RiftScribe ao lado, quem dá a numeração é o `gravar_edicao`
            # (`catalog._arrumar_api_sort`, ronda de 2026-10-23), que mete as
            # da dotgg no sítio delas entre as da RiftScribe.
            rows = ordenar(rows)
            if not rows:
                res["sets_vazias"].append(sid)
                log(f"  ! {sid}: a dotgg não devolveu nenhuma carta — catálogo mantido")
                continue
            out = catalog.gravar_edicao(con, sid, rows, FONTE)
            res["sets"][sid] = out["n"]
            res["reaproveitados"] += out["reaproveitados"]
            res["da_riftscribe"] += out["mantidas"]
            log(f"  {sid}: {len(rows)} impressões da dotgg"
                + (f" ({out['mantidas']} já da RiftScribe, não se tocaram)" if out["mantidas"] else ""))
        catalog.rebuild_cards(con)
        catalog.rebuild_aliases(con)
    finally:
        con.close()
    res["unknown_variants"] = sorted(desconhecidas)
    res["total"] = sum(res["sets"].values())
    return res

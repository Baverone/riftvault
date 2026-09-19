"""O bloco «Runas — 12 de cada» no fim da grelha da Coleção — SÓ PARA ELE VER.

André, 2026-09-19: *"depois mete 12 runas de cada (nao contabilizes para
nada, e so para mim para contabilizar ali algumas coisas)"*.

É UMA VISTA, não uma categoria da Coleção. Nada aqui entra no denominador
(928), na percentagem, nos níveis, nas wantlists, no valor, nas Faltas, no «A
mais», nos decks nem no «tens N no playset completo» de bloco nenhum. Por
isso vive num módulo à parte, com URL próprio (`api/runas.json`), e NENHUM
módulo de contas o importa — `tests/test_runas_vista.py` lê o código-fonte
e recusa a importação. Quem o chama é só o `server`, o `build` e a CLI. É o
mesmo cuidado da montra «Promos» de 2026-09-18 (apagada nesse dia).

O QUE CONTA COMO «TENHO» — a leitura desta ordem, e é a única coisa nela que
contraria uma regra anterior: **tudo o que ele fisicamente tem** de cada
runa, esteja onde estiver (Coleção, deck, binder) e seja que impressão for —
a base do OGN (a sequência), a arte alternativa do OGN (RETIRADA de tudo
desde 2026-09-17, `runas_especiais.retiradas`), a promo do VEN (escondida
desde 2026-09-15) e as do CardTrader que a RiftScribe não tem
(`market_only`: as `SFD-R02a` e companhia, que hoje nenhum sítio mostra). Ele
quer saber quantas runas tem na mão para as organizar à mão, e uma runa em
Alt Art é uma runa na mão. Como isto contraria a retirada, o payload leva os
DOIS números — `total` e `sem_retiradas` — e o tile mostra o segundo quando
difere. Não se escolhe por ele.

«Runa» é o `runas_especiais.tipos`, a mesma definição da Coleção e dos
decks; o alvo (`runas_vista.alvo`, 12) é o número dele e não o do Rune Pool,
embora hoje coincidam.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from . import config, metrics

# O número que ele disse: «12 runas de cada». Só para a vista.
ALVO_OMISSAO = 12

# A frase que tem de estar no ecrã: as 6 runas base do OGN já aparecem na
# sequência do master set (a 3), e voltam a aparecer aqui. Não é duplicação —
# é outra pergunta («quantas tenho na mão») — mas tem de se ler.
NOTA = ("só para contares o que tens à mão — não conta para as métricas. As "
        "runas base do OGN também estão na sequência do master set, em cima; "
        "aqui somam-se TODAS as versões que tens, incluindo as que o resto do "
        "site não conta.")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def opcoes(cfg: dict | None = None) -> dict:
    cfg = cfg or config.load()
    out = {"alvo": ALVO_OMISSAO}
    out.update({k: v for k, v in (cfg.get("runas_vista") or {}).items()
                if not k.startswith("_")})
    return out


def alvo(cfg: dict | None = None) -> int:
    n = int(opcoes(cfg)["alvo"])
    if n <= 0:
        raise ValueError(f"runas_vista.alvo: tem de ser positivo, veio {n}")
    return n


def tipos(cfg: dict | None = None) -> tuple[str, ...]:
    """O que é uma runa — o `runas_especiais.tipos`, para não haver duas
    definições. Vazio (ninguém é runa) dá um bloco vazio, não um erro."""
    return tuple(metrics.opcoes_runa(cfg).get("tipos") or ())


def _qtys(con: sqlite3.Connection) -> dict[str, int]:
    return {r["printing_id"]: r["qty"] for r in con.execute("SELECT printing_id, qty FROM copies")}


def payload(con: sqlite3.Connection, cfg: dict | None = None,
            image_mode: str = "local") -> dict:
    cfg = cfg or config.load()
    tps = tipos(cfg)
    n_alvo = alvo(cfg)
    qty = _qtys(con)

    runas: dict[str, dict] = {}   # card_key -> a linha
    if tps:
        marcas = ",".join("?" * len(tps))
        rows = con.execute(
            f"SELECT * FROM catalog.printings WHERE type IN ({marcas}) "
            "ORDER BY card_key, api_sort", tps).fetchall()
    else:
        rows = []
    for r in rows:
        ck = r["card_key"]
        linha = runas.get(ck)
        if linha is None:
            linha = runas[ck] = {
                "card_key": ck, "name": r["name"], "type": r["type"],
                # A imagem e o código são os da primeira impressão BASE (a do
                # OGN); se não houver base, os da primeira que aparecer.
                "code": None, "img": None, "cdn": None, "landscape": False,
                "origens": [], "total": 0, "sem_retiradas": 0,
            }
        e_base = r["variant_kind"] == "base"
        if linha["code"] is None or (e_base and not linha.get("_base")):
            linha.update({
                "code": r["public_code"], "img": f"img/{r['printing_id']}.webp",
                "cdn": r["image_medium"] or r["image_large"] or r["image_url"],
                "landscape": (r["orientation"] or "").lower() == "landscape",
                "_base": e_base,
            })
        n = qty.get(r["printing_id"], 0)
        retirada = metrics.retirada(r, cfg)
        _somar(linha, n, retirada, {
            "id": r["printing_id"], "code": r["public_code"], "kind": r["variant_kind"],
            "label": _rotulo(r, cfg, retirada), "qty": n,
            "retirada": retirada, "escondida": metrics.escondida(r, cfg),
            "fora_do_catalogo": False,
        })

    # As runas que só o CardTrader lista (`market_only`): fora do catálogo,
    # não contam para métrica nenhuma em lado nenhum — mas estão na mão dele
    # (as 23 alt arts do SFD, medido a 2026-09-17). A arte alternativa
    # reconhece-se pela `version`, como no Pimp; é retirada como as do OGN.
    if runas:
        marcas = ",".join("?" * len(runas))
        mo = con.execute(
            f"SELECT printing_id, set_id, collector_raw, card_key, version "
            f"FROM catalog.market_only WHERE card_key IN ({marcas}) "
            "ORDER BY card_key, set_id, collector_raw", list(runas)).fetchall()
        for r in mo:
            n = qty.get(r["printing_id"], 0)
            linha = runas[r["card_key"]]
            alt = "alternate art" in (r["version"] or "").lower()
            retirada = alt and metrics.retirada(
                {"type": linha["type"], "variant_kind": "alt_art"}, cfg)
            # O CardTrader omite o `a` na Calm Rune do SFD; a carta impressa
            # leva-o (ver `faltas.pimp`).
            raw = r["collector_raw"] or ""
            codigo = f"{r['set_id']}-{raw}" + ("a" if alt and not raw.lower().endswith("a") else "")
            _somar(linha, n, retirada, {
                "id": r["printing_id"], "code": codigo,
                "kind": "alt_art" if alt else "base",
                "label": ("alt art (CardTrader, retirada)" if retirada
                          else "alt art (CardTrader)" if alt else "CardTrader"),
                "qty": n, "retirada": retirada, "escondida": False,
                "fora_do_catalogo": True,
            })

    itens = []
    for linha in sorted(runas.values(), key=lambda x: x["name"]):
        linha.pop("_base", None)
        # Só as origens com cópias: é uma linha por baixo do tile, não uma
        # lista de tudo o que existe. A sequência primeiro, depois o que o
        # site ainda conta (a promo escondida), depois as retiradas e o
        # CardTrader — pela ordem em que o resto do site as lê.
        linha["origens"] = sorted(
            (o for o in linha["origens"] if o["qty"] > 0),
            key=lambda o: (o["label"] != "sequência", o["retirada"],
                           o["fora_do_catalogo"], o["code"]))
        linha["target"] = n_alvo
        itens.append(linha)

    return {
        "generated_at": _now(),
        "image_mode": image_mode,
        # A marca de que isto é uma vista: o cliente e os testes lêem-na.
        "so_para_ver": True,
        "alvo": n_alvo,
        "nota": NOTA,
        "runas": itens,
        "totals": {
            "cards": len(itens),
            "total": sum(x["total"] for x in itens),
            "sem_retiradas": sum(x["sem_retiradas"] for x in itens),
            "alvo": n_alvo * len(itens),
        },
    }


def _somar(linha: dict, n: int, retirada: bool, origem: dict) -> None:
    linha["origens"].append(origem)
    linha["total"] += n
    if not retirada:
        linha["sem_retiradas"] += n


def _rotulo(r, cfg: dict, retirada: bool) -> str:
    """A palavra para a origem, por baixo do tile: de onde vem cada cópia."""
    if retirada:
        return "alt art (retirada)"
    if metrics.escondida(r, cfg):
        return f"{r['variant_label'] or r['variant_kind']} (escondida)".lower()
    if metrics.e_master(r, cfg):
        return "sequência"
    return (r["variant_label"] or r["variant_kind"] or "").lower()

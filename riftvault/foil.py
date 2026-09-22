"""Quantas das comuns e incomuns são FOIL (2026-09-22).

Palavras do André: *"para comuns e incomuns, coloca contagem para Foil e
Non-Foil, para todas as edicoes excepto Proving Grounds"*. «Proving Grounds»
é o OGS, por isso vale para o OGN, o SFD, o UNL e o VEN.

UMA VERDADE SÓ, NUNCA DUAS
    A contagem do foil é a coluna `copies.qty_foil` — quantas das cópias que
    ele tem daquela impressão são foil. **O não-foil NUNCA se grava**: é
    sempre `qty − qty_foil`, derivado na leitura. Se se guardassem os dois,
    mais cedo ou mais tarde deixavam de somar o total, e passava a haver duas
    respostas à mesma pergunta. É a mesma arquitectura da Coleção, que também
    não se grava (`locais.na_colecao`: é o `copies.qty` menos os outros
    locais).

    A base garante-o: `CHECK (qty_foil >= 0 AND qty_foil <= qty)`. E quando o
    total desce abaixo do que estava marcado como foil — um `−` na grelha —,
    o `qty_foil` desce com ele (`ao_descer`, chamado pelo `collection.adjust`
    e pelo `proprias.ajustar` dentro da mesma transação), com linha na
    `foil_ops`: uma cópia foil não se pode evaporar em silêncio.

ISTO NÃO É UM ACABAMENTO NOVO NO GRÃO DA COLEÇÃO
    A decisão de 2026-08-31 continua de pé: *"foil e normal contam como a
    mesma coisa"*, a chave do `copies` é só `(printing_id)`, e o alvo do
    master set é por impressão — qualquer cópia o cumpre. O `qty_foil` é uma
    REPARTIÇÃO do que ele já tem, para ele saber quantas são de cada; não
    entra em conta nenhuma. Marcar cópias como foil não mexe um único número:
    nem o total de cópias, nem os três níveis, nem o denominador, nem o A
    mais, nem as Faltas, nem as quatro wantlists por bloco, nem o valor, nem
    as Encomendas, nem os decks, nem a alocação. `tests/test_foil.py`
    fotografa tudo isso, mete e tira foils, e exige que fique igual.

O ÂMBITO, EM CONFIG (`foil.raridades`, `foil.edicoes_fora`)
    As impressões BASE (não sobrenumeradas) das raridades da lista, nas
    edições que não estiverem fora. Hoje: comuns e incomuns, fora o OGS —
    **512 impressões, 1376 cópias** no `data/` de 2026-09-22 (OGN 88/291 +
    84/132, SFD 60/180 + 63/165, UNL 60/180 + 63/166, VEN 48/144 + 46/118).
    Fora do âmbito não aparece contador nenhum, e a rota e a CLI recusam.

    «Base» e «não sobrenumerada» é a mesma pergunta que os decks fazem
    (`decks.Versoes`): a arte alternativa e a reimpressão de topo de set são
    outra impressão, com outro preço e outro mercado. A raridade é a IMPRESSA
    (`rarity`) — numa impressão base ela é, por construção, a da carta.

O TOTAL A QUE O FOIL SE COMPARA É O FÍSICO
    `qty_foil <= copies.qty`, o total de cópias, esteja a cópia na Coleção,
    num deck ou nas cópias próprias de um deck: uma carta não deixa de ser
    foil por estar sleevada. É o mesmo número que o tile já mostra em
    `qty_valor`/`qty_total`, e não o `qty` da Coleção, que é outra pergunta.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from . import config, metrics

# O que a página escreve por raridade. Uma raridade que ele ponha no config e
# não esteja aqui aparece na mesma, com o nome que trouxer.
RARIDADE_LABEL = {
    "common": "Comuns",
    "uncommon": "Incomuns",
    "rare": "Raras",
    "epic": "Épicas",
    "showcase": "Showcase",
}

# A chave do resumo com as edições todas somadas — a mesma do `painel.TODAS`.
TODAS = "all"


class ForaDoAmbito(ValueError):
    """Esta impressão não tem contagem de foil: não é base, é sobrenumerada,
    não é de uma das raridades do `foil.raridades`, ou é de uma edição do
    `foil.edicoes_fora`. Recusa-se em vez de gravar um número que a página
    não mostra."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# O âmbito
# ---------------------------------------------------------------------------


def opcoes(cfg: dict | None = None) -> tuple[frozenset[str], frozenset[str]]:
    """(raridades, edições de fora), lidas do config.

    Uma raridade que o catálogo não conhece REBENTA — é a regra das outras
    listas do config (`master_set.fora_da_percentagem`): um valor escrito à
    mão que não filtra nada tem de aparecer, não de ser ignorado em silêncio.
    A lista vazia também rebenta: sem raridades não há contagem nenhuma, e
    isso escreve-se desligando a secção, não com uma lista vazia.
    """
    bruto = (cfg or config.load()).get("foil") or {}
    raridades = [str(x).strip().lower() for x in (bruto.get("raridades") or [])]
    if not raridades:
        raise ValueError("foil.raridades está vazio — sem raridades não há "
                         f"contagem de foil. Aceita: {', '.join(metrics.RARITY_ORDER)}")
    for r in raridades:
        if r not in metrics.RARITY_ORDER:
            raise ValueError(f"foil.raridades: raridade desconhecida {r!r}. "
                             f"Aceita: {', '.join(metrics.RARITY_ORDER)}")
    fora = [str(x).strip().upper() for x in (bruto.get("edicoes_fora") or [])]
    return frozenset(raridades), frozenset(fora)


def raridades(cfg: dict | None = None) -> list[str]:
    """As raridades do âmbito, pela ordem do catálogo (`metrics.RARITY_ORDER`)."""
    rars, _ = opcoes(cfg)
    return [r for r in metrics.RARITY_ORDER if r in rars]


def no_ambito(printing, cfg: dict | None = None) -> bool:
    """Esta impressão tem contagem de foil?

    É a única resposta a esta pergunta: a grelha (o contador no tile), o
    resumo, a rota e a CLI perguntam todos aqui.
    """
    cfg = cfg or config.load()
    rars, fora = opcoes(cfg)
    if metrics.campo(printing, "set_id", "").upper() in fora:
        return False
    if metrics.campo(printing, "variant_kind", "unknown") != "base":
        return False
    if metrics.e_overnumbered(printing):
        return False
    rar = (metrics.campo(printing, "rarity", None)
           or metrics.campo(printing, "base_rarity", "") or "")
    return rar.lower() in rars


def ids_do_ambito(con: sqlite3.Connection, cfg: dict | None = None,
                  set_id: str | None = None) -> dict[str, sqlite3.Row]:
    """printing_id -> linha do catálogo, das impressões com contagem de foil."""
    cfg = cfg or config.load()
    where, args = ("WHERE set_id = ?", (set_id,)) if set_id else ("", ())
    return {r["printing_id"]: r for r in con.execute(
        "SELECT printing_id, set_id, collector_number, public_code, name, "
        "       variant_kind, rarity, base_rarity, api_sort "
        f"FROM catalog.printings {where} ORDER BY set_id, api_sort", args)
        if no_ambito(r, cfg)}


# ---------------------------------------------------------------------------
# Leitura
# ---------------------------------------------------------------------------


def qty_foil(con: sqlite3.Connection) -> dict[str, int]:
    """printing_id -> cópias foil. Só as que têm alguma."""
    return {r["printing_id"]: r["qty_foil"] for r in
            con.execute("SELECT printing_id, qty_foil FROM copies WHERE qty_foil > 0")}


def de(con: sqlite3.Connection, printing_id: str) -> int:
    row = con.execute("SELECT qty_foil FROM copies WHERE printing_id = ?",
                      (printing_id,)).fetchone()
    return row["qty_foil"] if row else 0


def _vazio() -> dict:
    return {"printings": 0, "copies": 0, "foil": 0, "normal": 0, "foil_printings": 0}


def _somar(slot: dict, copias: int, foil: int) -> None:
    slot["printings"] += 1
    slot["copies"] += copias
    slot["foil"] += foil
    slot["normal"] += copias - foil
    slot["foil_printings"] += 1 if foil > 0 else 0


def contar(itens) -> dict:
    """O resumo de uma lista de `(raridade, cópias, foil)`.

    `{printings, copies, foil, normal, foil_printings, rarity: [...]}` — o
    total e uma linha por raridade. `copies` é o TOTAL FÍSICO (o `copies.qty`)
    e `normal` é sempre `copies − foil`, nunca um número guardado.

    É o gémeo do `foilContar` do `app.js`, que recalcula o mesmo a cada
    `+`/`−`; há teste que corre os dois sobre os mesmos itens.
    """
    total = _vazio()
    por: dict[str, dict] = {}
    for rar, copias, foil in itens:
        rar = str(rar or "?").lower()
        _somar(total, copias, foil)
        _somar(por.setdefault(rar, _vazio()), copias, foil)
    ordem = [r for r in metrics.RARITY_ORDER if r in por]
    ordem += sorted(r for r in por if r not in metrics.RARITY_ORDER)
    total["rarity"] = [{"id": r, "label": RARIDADE_LABEL.get(r, r.capitalize()),
                        **por[r]} for r in ordem]
    return total


def itens(con: sqlite3.Connection, cfg: dict | None = None,
          set_id: str | None = None):
    """`(set_id, raridade, cópias, foil)` de cada impressão do âmbito."""
    cfg = cfg or config.load()
    totais = {r["printing_id"]: r["qty"] for r in
              con.execute("SELECT printing_id, qty FROM copies")}
    foils = qty_foil(con)
    return [(r["set_id"], (r["rarity"] or r["base_rarity"] or "?").lower(),
             totais.get(pid, 0), foils.get(pid, 0))
            for pid, r in ids_do_ambito(con, cfg, set_id).items()]


def resumo(con: sqlite3.Connection, cfg: dict | None = None,
           set_id: str | None = None) -> dict:
    """O resumo por edição e o de «Todas» (`TODAS`).

      `sets`        — `{set_id: contar(...)}`, mais a chave `all` (a soma)
      `raridades`   — os ids do âmbito, pela ordem do catálogo
      `labels`      — o nome de cada uma, para o cliente não ter segunda cópia
      `sem_edicoes` — as edições fora do âmbito, para a página o dizer
    """
    cfg = cfg or config.load()
    rars, fora = opcoes(cfg)
    por: dict[str, list] = {}
    for sid, rar, copias, foil in itens(con, cfg, set_id):
        item = (rar, copias, foil)
        por.setdefault(sid, []).append(item)
        por.setdefault(TODAS, []).append(item)
    return {"sets": {sid: contar(v) for sid, v in por.items()},
            "raridades": raridades(cfg),
            "labels": {r: RARIDADE_LABEL.get(r, r.capitalize()) for r in raridades(cfg)},
            "sem_edicoes": sorted(fora)}


def do_set(con: sqlite3.Connection, set_id: str, cfg: dict | None = None) -> dict | None:
    """O resumo de UMA edição — o que vai em `progress.foil` do payload dela.
    `None` quando a edição está fora do âmbito (o OGS), para a página não
    mostrar uma caixa vazia."""
    r = resumo(con, cfg, set_id=set_id)
    c = r["sets"].get(set_id)
    if not c:
        return None
    return {**c, "raridades": r["raridades"], "labels": r["labels"]}


# ---------------------------------------------------------------------------
# Escrita
# ---------------------------------------------------------------------------


def _registar(con: sqlite3.Connection, printing_id: str, delta: int,
              qty_after: int, source: str) -> None:
    con.execute("INSERT INTO foil_ops (ts, printing_id, delta, qty_after, source) "
                "VALUES (?,?,?,?,?)", (_now(), printing_id, delta, qty_after, source))


def ao_descer(con: sqlite3.Connection, printing_id: str, novo_total: int,
              source: str = "cli") -> int:
    """Corta o `qty_foil` ao novo total de cópias, e regista quanto caiu.

    Chama-se DENTRO da transação que baixa o `copies.qty` e ANTES de a
    escrever (`collection.adjust`, `proprias.ajustar`): baixar primeiro o
    `qty_foil` mantém o `CHECK (qty_foil <= qty)` verdadeiro a cada passo.

    Se ele tinha 3 cópias, 2 marcadas foil, e tira duas, ficam 1 cópia e 1
    foil — a cópia que desapareceu tinha de ser alguma, e o registo na
    `foil_ops` diz que foi uma foil. Devolve quantas desceram (0 quase
    sempre).
    """
    antes = de(con, printing_id)
    if antes <= max(0, novo_total):
        return 0
    novo = max(0, novo_total)
    con.execute("UPDATE copies SET qty_foil = ? WHERE printing_id = ?",
                (novo, printing_id))
    _registar(con, printing_id, novo - antes, novo, f"{source}:ajuste ao total")
    return antes - novo


def ajustar(con: sqlite3.Connection, ref: str, delta: int,
            source: str = "web", cfg: dict | None = None) -> dict:
    """Soma `delta` às cópias FOIL de uma impressão. Não mexe no total.

    É só uma repartição do que ele já tem: o `+` converte uma cópia que ele
    já tinha em foil, e trava no total (`min(delta, qty − qty_foil)`); o `−`
    trava no zero. **O `copies.qty` nunca mexe por aqui** — e por isso nenhuma
    conta do site mexe. Fora do âmbito rebenta (`ForaDoAmbito`).

    Deixa rasto na `foil_ops` (no vault.db, que vai para o Git), que é o
    registo a sério — como a `location_ops` é o dos locais.
    """
    from . import collection

    cfg = cfg or config.load()
    pid = collection.resolve_printing(con, ref)
    r = con.execute("SELECT * FROM catalog.printings WHERE printing_id = ?",
                    (pid,)).fetchone()
    if r is None or not no_ambito(r, cfg):
        raise ForaDoAmbito(
            f"{pid} não tem contagem de foil — só as impressões base, não "
            f"sobrenumeradas, de raridade {'/'.join(raridades(cfg))}, fora "
            f"{', '.join(sorted(opcoes(cfg)[1])) or 'nenhuma edição'}")
    delta = int(delta)

    con.execute("BEGIN IMMEDIATE")
    try:
        total = collection.get_qty(con, pid)
        atual = de(con, pid)
        novo = max(0, min(atual + delta, total))
        applied = novo - atual
        if applied:
            con.execute(
                "INSERT INTO copies (printing_id, qty, qty_foil, updated_at) "
                "VALUES (?,?,?,?) ON CONFLICT(printing_id) DO UPDATE SET "
                "qty_foil = excluded.qty_foil, updated_at = excluded.updated_at",
                (pid, total, novo, _now()))
            _registar(con, pid, applied, novo, source)
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise

    return {"printing_id": pid, "code": r["public_code"], "name": r["name"],
            "set": r["set_id"], "foil": novo, "normal": total - novo,
            "qty": total, "applied": applied}


def historico(con: sqlite3.Connection, limit: int = 20) -> list[dict]:
    return [dict(x) for x in con.execute(
        "SELECT f.*, p.public_code, p.name FROM foil_ops f "
        "LEFT JOIN catalog.printings p ON p.printing_id = f.printing_id "
        "ORDER BY f.id DESC LIMIT ?", (limit,))]


def texto(r: dict, sets: list[dict]) -> str:
    """O resumo em consola, para o `riftvault foil` e o `riftvault stats`."""
    nomes = {s["id"]: s["name"] for s in sets}
    nomes[TODAS] = "TODAS"
    ordem = [s["id"] for s in sets if s["id"] in r["sets"]] + [TODAS]
    w = max([len(nomes.get(s, s)) for s in ordem] + [6])
    linhas = [f"{'edição':<{w}}  {'impressões':>10}  {'cópias':>7}  "
              f"{'normais':>8}  {'foil':>6}  {'com foil':>8}"]
    for sid in ordem:
        c = r["sets"].get(sid)
        if not c:
            continue
        linhas.append(f"{nomes.get(sid, sid):<{w}}  {c['printings']:>10}  "
                      f"{c['copies']:>7}  {c['normal']:>8}  {c['foil']:>6}  "
                      f"{c['foil_printings']:>8}")
        for x in c["rarity"]:
            linhas.append(f"{'  · ' + x['label']:<{w}}  {x['printings']:>10}  "
                          f"{x['copies']:>7}  {x['normal']:>8}  {x['foil']:>6}  "
                          f"{x['foil_printings']:>8}")
    if r["sem_edicoes"]:
        linhas.append(f"\n(fora do âmbito: {', '.join(r['sem_edicoes'])})")
    return "\n".join(linhas)

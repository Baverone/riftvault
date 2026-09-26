"""Quantas comuns e incomuns ele tem em FOIL (2026-09-22, corrigido 2026-09-26).

Palavras do André: *"para comuns e incomuns, coloca contagem para Foil e
Non-Foil, para todas as edicoes excepto Proving Grounds"*. «Proving Grounds»
é o OGS, por isso vale para o OGN, o SFD, o UNL e o VEN.

O FOIL SOMA-SE AO NORMAL — SÃO DUAS CONTAGENS, NÃO UMA REPARTIÇÃO
    Palavras dele a 2026-09-26, a corrigir-nos: *"as foils quando eu marco é
    que tenho TAMBÉM foil, ou seja, normal + foil e não apenas 1, no caso
    daria 3+3"*.

        copies.qty       = as cópias NORMAIS
        copies.qty_foil  = as cópias FOIL
        total            = qty + qty_foil     (nunca se grava: é a soma)

    Com 3 normais e 3 foil ele tem **SEIS** cópias, não três. Os dois
    contadores são independentes: o `+` do foil não mexe no `qty`, e o `−` da
    grelha não mexe no `qty_foil`.

    Até 2026-09-26 o modelo era o CONTRÁRIO, e era erro nosso: o `qty` era o
    total, o `qty_foil` estava lá dentro (`CHECK (qty_foil <= qty)`), o
    não-foil era `qty − qty_foil`, e por isso o `+` do foil CONVERTIA uma
    cópia normal em foil em vez de acrescentar uma. O `ao_descer`, que cortava
    o foil quando o total descia, existia por causa desse tecto e foi-se com
    ele — as linhas `:ajuste ao total` que ficaram na `foil_ops` são desse
    tempo. Nenhum dado precisou de migrar: os números guardados já eram os
    certos para este modelo (verificação no CLAUDE.md), só o CHECK saiu.

    **`qty = 0` com `qty_foil > 0` é um estado legítimo** desde hoje — uma
    carta que ele só tenha em foil. A grelha mostra-a como carta que ele não
    tem (a Coleção conta o `qty`) com a linha «0 normais · 2 foil» ao lado.

O QUE O FOIL CONTA, DESDE 2026-09-26
    A decisão de 2026-08-31 continua de pé no GRÃO: *"foil e normal contam como
    a mesma coisa"*, a chave do `copies` é só `(printing_id)` e o alvo do master
    set é por impressão — o foil não é um acabamento no grão, é uma contagem à
    parte. O que mudou é que essa contagem **entra nas contas**: os dois botões
    dele estão ligados, e uma cópia foil vale como cópia da impressão para os
    níveis, o denominador, as Faltas, as wantlists e o valor.

    Os três sítios onde NÃO entra (e cada um pela sua razão, abaixo): o «A
    mais», o `propor_deck` e a Venda.

    AS DUAS PERGUNTAS ERAM DELE E ELE RESPONDEU-AS (2026-09-26): *"contam para
    o valor sim, e contabilizas tambem como parte do master set"*. As duas
    chaves estão a `true`, e a terceira nasceu com elas:

      `foil.conta_para_coleccao`  **true**. Os foils contam para os ALVOS da
                                  Coleção (os três níveis, o denominador, as
                                  Faltas, as wantlists): o que a impressão TEM
                                  é `qty + qty_foil`. Entram pelo
                                  `locais.na_colecao`, o funil único de
                                  «quantas cópias tem a Coleção».
      `foil.conta_para_valor`     **true**. Os foils contam para o VALOR, pelo
                                  `locais.contadas` e pelo `prices.copias_sql`,
                                  **AO PREÇO DA FOIL** — o `price_foil_cents`,
                                  que desde a tarde de 2026-09-26 é o mínimo das
                                  ofertas FOIL do CardTrader com os mesmos
                                  filtros das normais (*"podes meter filtro no
                                  cardtrader e tirar o preco da foil mais
                                  barata?"*). Só quando o CardTrader não tem
                                  oferta foil nenhuma é que a cópia cai para o
                                  preço da normal, e esse FALLBACK é contado e
                                  dito (`prices.valor_dos_foils`) — é ele que
                                  faz do total um **PISO**. Até essa tarde
                                  contavam TODAS ao preço da normal, que nas
                                  comuns era o chão do CardTrader.
      `foil.entra_no_a_mais`      **false**. Os foils NÃO entram no que sobra no
                                  «A mais»: com eles a contar, 3 normais + 3
                                  foil contra um alvo de 3 diriam «3 a mais para
                                  vender», e ele não vende os foils — são peça
                                  de coleção. O excedente conta primeiro as
                                  NORMAIS (`na_colecao(..., com_foil=False)`) e
                                  por isso o separador dá exactamente os mesmos
                                  números que dava antes. Ver o
                                  `a_mais.foil_no_excedente`.

    A MESMA CAUTELA em três sítios mais, pela mesma razão — contam cópias
    FÍSICAS de acabamento normal, não alvos: o `locais.propor_deck` (grava em
    `copy_locations`, que só conta normais), a **Venda** (o «marcar como
    vendidas» baixa o `copies.qty`) e os **decks**, que servem as normais
    primeiro (`decks.foils_nos_decks`).

    Os dois funis leem a chave DIRECTAMENTE do config, sem importar este
    módulo: é o que deixa o `locais` e o `prices` continuarem a não conhecer
    o foil, e o teste a poder provar que nenhum módulo de contas o importa.

O ÂMBITO, EM CONFIG (`foil.raridades`, `foil.edicoes_fora`)
    As impressões BASE (não sobrenumeradas) das raridades da lista, nas
    edições que não estiverem fora. Hoje: comuns e incomuns, fora o OGS —
    **512 impressões** no `data/` de 2026-09-22. Fora do âmbito não aparece
    contador nenhum, e a rota e a CLI recusam.

    «Base» e «não sobrenumerada» é a mesma pergunta que os decks fazem
    (`decks.Versoes`): a arte alternativa e a reimpressão de topo de set são
    outra impressão, com outro preço e outro mercado. A raridade é a IMPRESSA
    (`rarity`) — numa impressão base ela é, por construção, a da carta.

O CONTADOR DO FOIL NÃO TEM TECTO NATURAL
    Não há número nenhum na app que diga quantas foils ele pode ter — o foil
    não é uma fatia de nada. O `LIMITE` é só sanidade contra um dedo preso no
    `+`, e é o mesmo do CHECK da base.

    As NORMAIS a que o foil se compara na página são as FÍSICAS
    (`locais.totais`), esteja a cópia na Coleção, num deck ou nas cópias
    próprias dele: uma carta não deixa de ser normal por estar sleevada. Os
    locais (`copy_locations`) continuam a contar só as normais — onde está
    cada foil é pergunta que ele nunca fez.
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

# O tecto do contador de foil (2026-09-26). Não é um número de coleção nenhum:
# o foil deixou de ser uma fatia do total e não tem tecto natural. É sanidade
# contra um dedo preso no `+`, e é o mesmo do `CHECK` da base — se um dia
# mudar, muda nos dois sítios (e o `db._tirar_o_tecto_do_foil` também o
# escreve).
LIMITE = 9999


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


# ---------------------------------------------------------------------------
# As duas perguntas que são DELE (2026-09-26)
# ---------------------------------------------------------------------------
#
# Estas duas funções são a leitura de referência das chaves, para a CLI, a
# página e os testes. Os FUNIS (`locais.na_colecao`, `locais.contadas`,
# `prices.copias_sql`) leem a mesma chave do config directamente, com um
# helper próprio de uma linha, para não terem de importar este módulo — é o
# que mantém a fronteira (e o teste que a prova) de pé.


def conta_para_coleccao(cfg: dict | None = None) -> bool:
    """Os foils somam-se aos ALVOS da Coleção (níveis, denominador, Faltas,
    wantlists)? **SIM desde 2026-09-26** (*"contabilizas tambem como parte do
    master set"*): o que a impressão TEM é `qty + qty_foil`."""
    return bool(((cfg or config.load()).get("foil") or {})
                .get("conta_para_coleccao", False))


def entra_no_a_mais(cfg: dict | None = None) -> bool:
    """Os foils entram no que SOBRA, no «A mais»? **NÃO** (2026-09-26).

    Com os foils a contar para a Coleção, 3 normais + 3 foil contra um alvo de 3
    dariam «3 a mais para vender» — e ele não vende os foils, são peça de
    coleção. O excedente conta primeiro as NORMAIS. A leitura que o separador
    usa é o `a_mais.foil_no_excedente`, que lê a mesma chave.
    """
    return bool(((cfg or config.load()).get("foil") or {})
                .get("entra_no_a_mais", False))


def conta_para_valor(cfg: dict | None = None) -> bool:
    """Os foils somam-se ao VALOR? **SIM desde 2026-09-26** (*"contam para o
    valor sim"*). Omissão: não.

    Ao PREÇO DA FOIL (`price_latest.price_foil_cents`, o mínimo das ofertas foil
    do CardTrader), e só ao da normal quando não há oferta foil — o fallback que
    o `prices.valor_dos_foils` conta e que faz do total um piso.
    """
    return bool(((cfg or config.load()).get("foil") or {}).get("conta_para_valor", False))


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


def _somar(slot: dict, normal: int, foil: int) -> None:
    slot["printings"] += 1
    slot["normal"] += normal
    slot["foil"] += foil
    slot["copies"] += normal + foil
    slot["foil_printings"] += 1 if foil > 0 else 0


def contar(itens) -> dict:
    """O resumo de uma lista de `(raridade, normais, foil)`.

    `{printings, copies, foil, normal, foil_printings, rarity: [...]}` — o
    total e uma linha por raridade. `normal` e `foil` são as DUAS contagens
    guardadas, e `copies` é a SOMA delas (2026-09-26: *"normal + foil"*) —
    nunca um número guardado. Até essa data era ao contrário: o `copies` era o
    total guardado e o `normal` a subtracção.

    É o gémeo do `foilContar` do `app.js`, que recalcula o mesmo a cada
    `+`/`−`; há teste que corre os dois sobre os mesmos itens.
    """
    total = _vazio()
    por: dict[str, dict] = {}
    for rar, normal, foil in itens:
        rar = str(rar or "?").lower()
        _somar(total, normal, foil)
        _somar(por.setdefault(rar, _vazio()), normal, foil)
    ordem = [r for r in metrics.RARITY_ORDER if r in por]
    ordem += sorted(r for r in por if r not in metrics.RARITY_ORDER)
    total["rarity"] = [{"id": r, "label": RARIDADE_LABEL.get(r, r.capitalize()),
                        **por[r]} for r in ordem]
    return total


def itens(con: sqlite3.Connection, cfg: dict | None = None,
          set_id: str | None = None):
    """`(set_id, raridade, normais, foil)` de cada impressão do âmbito.

    As NORMAIS são as cópias físicas (`copies.qty`, todos os locais — uma
    cópia sleevada num deck não deixa de ser normal), e o FOIL é a outra
    contagem. O total é a soma, e faz-se no `contar`.
    """
    cfg = cfg or config.load()
    normais = {r["printing_id"]: r["qty"] for r in
               con.execute("SELECT printing_id, qty FROM copies")}
    foils = qty_foil(con)
    return [(r["set_id"], (r["rarity"] or r["base_rarity"] or "?").lower(),
             normais.get(pid, 0), foils.get(pid, 0))
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
    for sid, rar, normal, foil in itens(con, cfg, set_id):
        item = (rar, normal, foil)
        por.setdefault(sid, []).append(item)
        por.setdefault(TODAS, []).append(item)
    return {"sets": {sid: contar(v) for sid, v in por.items()},
            "raridades": raridades(cfg),
            "labels": {r: RARIDADE_LABEL.get(r, r.capitalize()) for r in raridades(cfg)},
            "sem_edicoes": sorted(fora),
            # O tecto do `+` e as duas perguntas dele, para o cliente não ter
            # segunda cópia de nenhuma das três.
            "limite": LIMITE,
            "conta_para_coleccao": conta_para_coleccao(cfg),
            "conta_para_valor": conta_para_valor(cfg),
            "entra_no_a_mais": entra_no_a_mais(cfg)}


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


def ajustar(con: sqlite3.Connection, ref: str, delta: int,
            source: str = "web", cfg: dict | None = None) -> dict:
    """Soma `delta` às cópias FOIL de uma impressão. Não mexe nas normais.

    São DUAS contagens independentes (2026-09-26): o `+` acrescenta uma foil
    às que ele já tinha — **não converte uma normal** —, e por isso o total da
    impressão SOBE. O `−` trava no zero; o `+` só trava no `LIMITE`, que é
    sanidade e não um número de coleção. **O `copies.qty` nunca mexe por
    aqui** — e por isso nenhuma conta do site mexe (com os dois botões dele
    desligados, que é a omissão). Fora do âmbito rebenta (`ForaDoAmbito`).

    Deixa rasto na `foil_ops` (no vault.db, que vai para o Git), que é o
    registo a sério — como a `location_ops` é o dos locais.

    Devolve `normal` (as cópias normais, que não mexeram), `foil` e `total` (a
    soma). **Não devolve `qty`**, de propósito: era o nome ambíguo que estava
    por baixo do erro do modelo antigo.
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
        normal = collection.get_qty(con, pid)
        atual = de(con, pid)
        novo = max(0, min(atual + delta, LIMITE))
        applied = novo - atual
        if applied:
            # A linha pode ainda não existir — uma carta que ele só tenha em
            # foil entra com `qty = 0`, que desde hoje é estado legítimo. O
            # `ON CONFLICT` mexe SÓ no `qty_foil`: as normais não são desta
            # pergunta.
            con.execute(
                "INSERT INTO copies (printing_id, qty, qty_foil, updated_at) "
                "VALUES (?,?,?,?) ON CONFLICT(printing_id) DO UPDATE SET "
                "qty_foil = excluded.qty_foil, updated_at = excluded.updated_at",
                (pid, normal, novo, _now()))
            _registar(con, pid, applied, novo, source)
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise

    return {"printing_id": pid, "code": r["public_code"], "name": r["name"],
            "set": r["set_id"], "foil": novo, "normal": normal,
            "total": normal + novo, "applied": applied,
            # Os dois preços (2026-09-26, à tarde), para o tile e a CLI
            # dizerem quanto vale uma foil desta impressão sem ir buscá-los
            # a outro lado. `price_foil` a `None` é o FALLBACK: a cópia foil
            # conta ao `price`.
            **_precos(con, pid)}


def _precos(con: sqlite3.Connection, pid: str) -> dict:
    """`{price, price_foil}` em cêntimos — o da normal e o da FOIL, ou `None`.

    Num catálogo sem a tabela (ou sem a coluna) dá os dois a `None`: a contagem
    de foil funciona sem preços, e é só isso que este módulo garante.
    """
    try:
        row = con.execute(
            "SELECT price_cents, "
            # A regra do `prices.valor_dos_foils`: com `from_foil` o preço da
            # normal JÁ é de foil, e é esse que a cópia foil vale.
            "       CASE WHEN price_foil_cents IS NOT NULL THEN price_foil_cents "
            "            WHEN from_foil = 1 THEN price_cents END AS foil "
            "FROM catalog.price_latest WHERE printing_id = ?", (pid,)).fetchone()
    except sqlite3.OperationalError:
        return {"price": None, "price_foil": None}
    return {"price": row["price_cents"] if row else None,
            "price_foil": row["foil"] if row else None}


def historico(con: sqlite3.Connection, limit: int = 20) -> list[dict]:
    return [dict(x) for x in con.execute(
        "SELECT f.*, p.public_code, p.name FROM foil_ops f "
        "LEFT JOIN catalog.printings p ON p.printing_id = f.printing_id "
        "ORDER BY f.id DESC LIMIT ?", (limit,))]


def _eur(cents: int) -> str:
    """Os euros de uma linha deste resumo. O `prices.eur` faz o mesmo, mas
    importá-lo aqui punha este módulo a conhecer o `prices` por causa de uma
    vírgula decimal."""
    return f"{cents / 100:.2f} €"


def _linha_do_valor(valor: dict | None) -> str:
    """O que as foils valem, e quantas caem no FALLBACK (2026-09-26, à tarde).

    Sem `valor` (quem chama não o tinha) diz-se só a regra. Com ele, os números:
    o preço de foil do CardTrader é o que manda, e as que não têm oferta foil
    contam ao preço da normal — é esse pedaço que faz do total um PISO.
    """
    if not valor or not valor.get("copies"):
        return ("no valor contam ao PREÇO DA FOIL do CardTrader; sem oferta foil "
                "caem para o preço da normal (`riftvault value` diz quantas).")
    pf, fb = valor["preco_de_foil"], valor["ao_preco_da_normal"]
    partes = [f"as tuas {valor['copies']} foils valem {_eur(valor['cents'])}"]
    if pf["copies"]:
        partes.append(f"{pf['copies']} a preço de FOIL ({_eur(pf['cents'])})")
    if fb["copies"]:
        partes.append(f"{fb['copies']} ao preço da NORMAL, por não haver oferta "
                      f"foil ({_eur(fb['cents'])}) — é um PISO")
    if valor["sem_preco"]["copies"]:
        partes.append(f"{valor['sem_preco']['copies']} sem preço, não contam")
    return "no valor: " + "; ".join(partes) + "."


def texto(r: dict, sets: list[dict], valor: dict | None = None) -> str:
    """O resumo em consola, para o `riftvault foil` e o `riftvault stats`.

    `valor` é o `prices.valor_dos_foils(con)`, quando quem chama o tem: o preço
    das foils diz-se onde a contagem delas aparece (2026-09-26, à tarde), com o
    FALLBACK marcado. Vem por parâmetro e não por import para este módulo
    continuar a não conhecer o `prices`.
    """
    nomes = {s["id"]: s["name"] for s in sets}
    nomes[TODAS] = "TODAS"
    ordem = [s["id"] for s in sets if s["id"] in r["sets"]] + [TODAS]
    w = max([len(nomes.get(s, s)) for s in ordem] + [6])
    linhas = [f"{'edição':<{w}}  {'impressões':>10}  {'normais':>8}  "
              f"{'foil':>6}  {'total':>7}  {'com foil':>8}"]
    for sid in ordem:
        c = r["sets"].get(sid)
        if not c:
            continue
        linhas.append(f"{nomes.get(sid, sid):<{w}}  {c['printings']:>10}  "
                      f"{c['normal']:>8}  {c['foil']:>6}  {c['copies']:>7}  "
                      f"{c['foil_printings']:>8}")
        for x in c["rarity"]:
            linhas.append(f"{'  · ' + x['label']:<{w}}  {x['printings']:>10}  "
                          f"{x['normal']:>8}  {x['foil']:>6}  {x['copies']:>7}  "
                          f"{x['foil_printings']:>8}")
    if r["sem_edicoes"]:
        linhas.append(f"\n(fora do âmbito: {', '.join(r['sem_edicoes'])})")
    # O total é a SOMA (2026-09-26), e as duas perguntas dele dizem-se sempre,
    # para nunca haver dúvida sobre o que é que este número está a mexer.
    linhas.append("\no total é normais + foil: as duas contagens são "
                  "independentes.")
    linhas.append(f"os foils {'CONTAM' if r.get('conta_para_coleccao') else 'não contam'}"
                  f" para os alvos da Coleção (foil.conta_para_coleccao) e "
                  f"{'CONTAM' if r.get('conta_para_valor') else 'não contam'}"
                  f" para o valor (foil.conta_para_valor).")
    if r.get("conta_para_valor"):
        linhas.append(_linha_do_valor(valor))
    if r.get("conta_para_coleccao") and not r.get("entra_no_a_mais"):
        linhas.append("no «A mais» NÃO entram no que sobra: o excedente conta primeiro "
                      "as normais (foil.entra_no_a_mais).")
    return "\n".join(linhas)

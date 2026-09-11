"""Decks: leitura das listas, alocação por prioridade e validação.

A REGRA CENTRAL — OS DECKS PARTILHAM A COLEÇÃO, E O QUE NÃO CHEGA COMPRA-SE
    Palavras do André (2026-09-11): *"Os decks podem usar cartas da coleção. Na
    coleção indica onde as cartas estão a ser usadas. Os decks que precisem de
    cartas iguais, caso não haja suficientes na coleção, ficam em falta e é
    necessário comprar!"* E, a confirmar: *"se há na coleção o deck usa; caso
    algum deck ou decks já estão a usar as cartas disponíveis na coleção, o
    próximo passa a marcar como faltas para comprar"*.

    Três regras, uma por frase:

      1. Uma cópia que exista CONTA para o deck, esteja na Coleção, sleevada no
         deck ou no binder Decks/Venda. A marcação de locais (`locais`) diz
         ONDE a cópia está; não desconta nada.
      2. Os decks têm uma ordem e percorrem-se por ela: o deck 1 fica com o que
         precisa, o deck 2 só recebe o que sobrou. Mudar a ordem muda quem fica
         com o quê — a alocação é global, não por deck.
      3. O que um deck não recebe é FALTA A COMPRAR desse deck, mesmo que as
         cópias existam e estejam noutro deck. «Está noutro deck» (`shared`)
         passou a ser informação — de onde vem a falta —, não um desconto.
         Até 2026-09-11 era o contrário («a primeira diz onde está, a segunda
         vai para a lista de compras»); a terceira frase dele revogou isso.

    Por carta lógica: procura_total = Σ(o que cada deck pede, todos os papéis
    incluindo o sideboard); a comprar = max(0, procura_total − cópias que
    existem), distribuída pelos decks de prioridade mais baixa.

DECKS COM A MESMA LEGEND SÃO O MESMO DECK FÍSICO — PARTILHAM, NÃO DISPUTAM
    Palavras do André (2026-09-11, à noite): *"deck com o mesmo Legend,
    partilham cartas. Os 2 decks de LeBlanc partilham as mesmas cartas, são só
    2 listas diferentes em algumas cartas. Então o que encomendar para 1 deck,
    estou a encomendar para o outro também."*

    Dois decks com a mesma Legend nunca se jogam ao mesmo tempo: são duas
    LISTAS do mesmo monte de cartas. Formam um GRUPO (`grupos`), e dentro do
    grupo a procura de cada carta é o MÁXIMO entre as listas, não a soma —
    LeBlanc pede 3 Hidden Blade e o Baited Hook pede 2, o grupo pede 3. O
    grupo serve-se da Coleção como um deck só, na prioridade do melhor
    colocado dos seus membros, e o que lhe falta é falta dos dois — a mesma
    carta, a mesma quantidade, contada UMA vez no total geral. Entre grupos
    diferentes (Ornn, Azir, Kennen, o grupo LeBlanc) fica a regra de cima:
    soma, disputa, o de baixo compra.

    Na página de cada deck a lista continua a ser a dele; uma carta que o
    irmão também pede diz «partilhada com …» (`partilhada`) e não conta como
    disputa. Quem soma totais lê o grupo pelo LÍDER (`grupo.lider`), senão
    conta os dois LeBlanc a dobrar — é o único cuidado que a camada pede a
    quem a consome.

FORMATO DAS LISTAS
    Secções com cabeçalho terminado em ':' (Legend, Champion, MainDeck,
    Battlefields, Rune Pool, Sideboard) e linhas "N Nome da Carta". Também
    aceita códigos, "3 OGN-045".

    Uma linha opcional "Nome: <texto>" (ou "Name:"), antes do Legend, dá o
    nome de mostrar ao deck. Sem ela o rótulo é "Legend · Champion", como
    sempre foi (2026-09-11: o segundo deck de LeBlanc tinha a mesma Legend e o
    mesmo Champion do primeiro e os dois liam-se igual).

A CHAVE DE UM DECK É O SLUG (o nome do ficheiro), NUNCA O RÓTULO
    O rótulo pode repetir-se — dois decks com a mesma Legend e o mesmo
    Champion — e a 2026-09-11 isso fundia-os: o `allocate` não via o primeiro
    LeBlanc como «outro deck» e mandava comprar o que já lá estava. Tudo o
    que precisa de distinguir decks compara `slug`; o `deck` (rótulo) é só
    para mostrar. Se mesmo assim dois rótulos coincidirem, o de prioridade
    mais baixa leva o slug entre parênteses (`rotulos`).
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from . import config

# Cabeçalhos aceites -> papel interno.
ROLES = {
    "legend": "legend",
    "champion": "champion",
    "maindeck": "main", "main deck": "main", "main": "main", "deck": "main",
    "battlefields": "battlefields", "battlefield": "battlefields",
    "rune pool": "runes", "runes": "runes", "rune": "runes",
    "sideboard": "sideboard", "side": "sideboard",
}

ROLE_LABEL = {
    "legend": "Legend", "champion": "Champion", "main": "Main deck",
    "battlefields": "Battlefields", "runes": "Runas", "sideboard": "Sideboard",
}
ROLE_ORDER = ["legend", "champion", "main", "battlefields", "runes", "sideboard"]

DEFAULT_RULES = {
    "main": 40,
    # Inferido das duas listas do André, que têm 39 no MainDeck + 1 Champion.
    # NÃO validado contra as regras oficiais — ver CLAUDE.md.
    "main_includes_champion": True,
    "runes": 12,
    "battlefields": 3,
    "max_copies": 3,
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def norm(name: str) -> str:
    s = unicodedata.normalize("NFKC", name or "").strip().casefold()
    return re.sub(r"\s+", " ", s)


# ---------------------------------------------------------------------------
# Leitura das listas
# ---------------------------------------------------------------------------


def parse(path: Path) -> dict:
    """Lê um .txt e devolve as linhas por papel, ainda sem resolver nomes."""
    text = path.read_text(encoding="utf-8")
    role, out, nome = "main", [], None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith("//"):
            continue
        # "Nome: LeBlanc Baited Hook" — o rótulo do deck, se ele o quiser
        # diferente do "Legend · Champion". Só a primeira conta.
        m = re.match(r"^(?:nome|name)\s*:\s*(.+?)\s*$", line, re.IGNORECASE)
        if m and nome is None:
            nome = m.group(1)
            continue
        if line.endswith(":"):
            head = norm(line[:-1])
            role = ROLES.get(head, head)
            continue
        m = re.match(r"^(\d+)\s*[xX]?\s+(.+?)\s*$", line)
        if m:
            out.append((role, int(m.group(1)), m.group(2)))

    # A lista é identificada pelo conteúdo, para reimportar não duplicar.
    body = "\n".join(f"{r}|{q}|{norm(n)}" for r, q, n in out)
    return {"path": str(path), "slug": path.stem, "lines": out, "nome": nome,
            "content_hash": hashlib.sha256(body.encode()).hexdigest()[:16]}


def rotulos(decks: list[tuple[str, int, str]]) -> dict[str, str]:
    """[(slug, prioridade, rótulo)] -> {slug: rótulo}, sem dois iguais.

    Dois ficheiros sem `Nome:` e com a mesma Legend e o mesmo Champion dão o
    mesmo rótulo. O de prioridade mais alta (número mais baixo) fica como
    está; os outros levam o slug entre parênteses, para se verem os dois em
    vez de um deles desaparecer atrás do outro.
    """
    out, vistos = {}, set()
    for slug, pri, rotulo in sorted(decks, key=lambda x: (x[1], x[0])):
        if rotulo in vistos:
            rotulo = f"{rotulo} ({slug})"
        vistos.add(rotulo)
        out[slug] = rotulo
    return out


def resolve(con: sqlite3.Connection, name: str, role: str) -> str | None:
    """Nome da lista -> card_key do catálogo. None se não casar."""
    k = norm(name)
    row = con.execute("SELECT card_key FROM catalog.cards WHERE card_key = ?", (k,)).fetchone()
    if row:
        return row["card_key"]

    # Código de impressão ("3 OGN-045").
    row = con.execute(
        "SELECT p.card_key FROM catalog.printing_aliases a "
        "JOIN catalog.printings p ON p.printing_id = a.printing_id WHERE a.alias = ?",
        (k,)).fetchone()
    if row:
        return row["card_key"]

    # As listas escrevem os Legends como "Azir, Emperor of the Sands", mas no
    # catálogo o Legend é só "Emperor of the Sands". Nenhum dos 49 Legends tem
    # vírgula no nome, por isso tirar o prefixo é seguro.
    alvo = k
    if "," in k:
        tail = norm(k.split(",", 1)[1])
        row = con.execute("SELECT card_key FROM catalog.cards WHERE card_key = ?",
                          (tail,)).fetchone()
        if row:
            return row["card_key"]
        alvo = tail

    # A RiftScribe põe sufixo nos Legends do OGS ("Wuju Bladesman - Starter")
    # para os distinguir. As listas escrevem o nome impresso, sem o sufixo.
    # Só se aceita quando há UMA carta a corresponder — senão era um palpite.
    cands = [r["card_key"] for r in con.execute(
        "SELECT card_key FROM catalog.cards WHERE card_key LIKE ?", (alvo + " - %",))]
    if len(cands) == 1:
        return cands[0]
    return None


def import_all(con: sqlite3.Connection, log=print) -> dict:
    """Lê decks/*.txt para as tabelas. Mantém a prioridade já definida."""
    files = sorted(config.DECKS_DIR.glob("*.txt"))
    seen, results = [], []

    # Prioridade já atribuída antes, por slug; decks novos vão para o fim.
    known = {r["path"]: r["priority"] for r in con.execute("SELECT path, priority FROM decks")}
    next_pri = max(list(known.values()) + [0]) + 1

    # Primeiro lêem-se todos, porque o rótulo de um deck depende dos outros:
    # dois com o mesmo "Legend · Champion" têm de sair distintos (`rotulos`).
    lidos = []
    for path in files:
        d = parse(path)
        legend = champion = None
        rows, missing = [], []
        for role, qty, name in d["lines"]:
            ck = resolve(con, name, role)
            if ck is None:
                missing.append({"role": role, "qty": qty, "name": name})
                continue
            rows.append((role, ck, qty, name))
            if role == "legend" and legend is None:
                legend = name
            if role == "champion" and champion is None:
                champion = name

        # O separador chama-se pelo Legend + Champion, como o André pediu —
        # a não ser que o ficheiro traga um `Nome:` (2026-09-11).
        display = (d["nome"]
                   or " · ".join(x for x in (legend, champion) if x)
                   or d["slug"])
        pri = known.get(str(path), next_pri)
        if str(path) not in known:
            next_pri += 1
        lidos.append((path, d, legend, champion, rows, missing, display, pri))

    nomes = rotulos([(d["slug"], pri, display)
                     for _, d, _, _, _, _, display, pri in lidos])

    for path, d, legend, champion, rows, missing, _, pri in lidos:
        display = nomes[d["slug"]]

        # Uma carta pode repetir-se no mesmo papel (raro, mas soma-se).
        agg: dict[tuple[str, str], list] = {}
        for role, ck, qty, raw in rows:
            slot = agg.setdefault((role, ck), [0, raw])
            slot[0] += qty
        cartas = sorted((ck, role, v[0], v[1]) for (role, ck), v in agg.items())

        # NÃO ESCREVER QUANDO NADA MUDOU (2026-09-10). O `imported_at` sozinho
        # fazia esta função reescrever o vault.db a CADA importação — e o
        # `build` importa sempre, antes de gerar os payloads. Com o site a ser
        # gerado de 30 em 30 minutos no PC, isso dava um vault.db "alterado"
        # (e um commit, e uma build do Pages) todas as meias horas sem o André
        # ter tocado em nada. Compara-se o resultado e só se escreve se ele
        # diferir — é a mesma regra do `riftvault build --se-mudou`.
        #
        # Compara-se tudo o que se ia gravar, não só o `content_hash` do
        # ficheiro: o que uma linha resolve depende também do CATÁLOGO, e uma
        # carta que ontem faltava e hoje existe tem de entrar sem o .txt mexer.
        igual = con.execute(
            "SELECT deck_id FROM decks WHERE name=? AND content_hash=? AND path=? "
            "AND legend IS ? AND champion IS ? AND display_name=? AND missing_json=?",
            (d["slug"], d["content_hash"], str(path), legend, champion, display,
             json.dumps(missing, ensure_ascii=False))).fetchone()
        if igual is not None:
            atuais = sorted(
                (r["card_key"], r["role"], r["qty"], r["raw_line"]) for r in
                con.execute("SELECT card_key, role, qty, raw_line FROM deck_cards "
                            "WHERE deck_id=?", (igual["deck_id"],)))
            if atuais == cartas:
                seen.append(d["slug"])
                results.append({"slug": d["slug"], "display": display,
                                "priority": pri, "cards": len(rows),
                                "missing": missing})
                log(f"  {display}  (sem alterações)")
                continue

        con.execute("BEGIN")
        con.execute(
            "INSERT INTO decks (name, path, content_hash, format, imported_at, "
            "priority, legend, champion, display_name, missing_json) "
            "VALUES (?,?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(name) DO UPDATE SET path=excluded.path, "
            "content_hash=excluded.content_hash, imported_at=excluded.imported_at, "
            "legend=excluded.legend, champion=excluded.champion, "
            "display_name=excluded.display_name, missing_json=excluded.missing_json",
            (d["slug"], str(path), d["content_hash"], "riftbound", _now(),
             pri, legend, champion, display, json.dumps(missing, ensure_ascii=False)))
        deck_id = con.execute("SELECT deck_id FROM decks WHERE name = ?",
                              (d["slug"],)).fetchone()["deck_id"]
        con.execute("DELETE FROM deck_cards WHERE deck_id = ?", (deck_id,))
        con.executemany(
            "INSERT INTO deck_cards (deck_id, card_key, role, qty, raw_line) VALUES (?,?,?,?,?)",
            [(deck_id, ck, role, qty, raw) for ck, role, qty, raw in cartas])
        con.execute("COMMIT")

        seen.append(d["slug"])
        results.append({"slug": d["slug"], "display": display, "priority": pri,
                        "cards": len(rows), "missing": missing})
        log(f"  {display}  (prioridade {pri}, {len(rows)} linhas"
            + (f", {len(missing)} por casar" if missing else "") + ")")

    # Decks cujo ficheiro desapareceu saem — é assim que se apaga um deck.
    if seen:
        ph = ",".join("?" * len(seen))
        gone = [r["name"] for r in con.execute(
            f"SELECT name FROM decks WHERE name NOT IN ({ph})", seen)]
    else:
        gone = [r["name"] for r in con.execute("SELECT name FROM decks")]
    for name in gone:
        did = con.execute("SELECT deck_id FROM decks WHERE name = ?", (name,)).fetchone()["deck_id"]
        con.execute("DELETE FROM deck_cards WHERE deck_id = ?", (did,))
        con.execute("DELETE FROM decks WHERE deck_id = ?", (did,))
        log(f"  (removido: {name} — o ficheiro já não existe)")

    return {"decks": results, "removed": gone}


# ---------------------------------------------------------------------------
# Alocação por prioridade
# ---------------------------------------------------------------------------


def owned_by_card(con: sqlite3.Connection) -> dict[str, int]:
    """card_key -> cópias FÍSICAS, de todos os locais.

    É o "quantas destas cartas tenho ao todo" que o Pimp e a métrica de playset
    jogável perguntam — e, desde 2026-09-11, é também o que os decks têm para se
    montar: a soma dos três montes do `pool_dos_decks`.
    """
    return {r["k"]: r["n"] for r in con.execute(
        "SELECT p.card_key AS k, SUM(c.qty) AS n FROM copies c "
        "JOIN catalog.printings p ON p.printing_id = c.printing_id "
        "WHERE c.qty > 0 GROUP BY p.card_key")}


def _por_carta(con: sqlite3.Connection, mapa: dict[str, int]) -> dict[str, int]:
    """{printing_id: qty} -> {card_key: qty}, somando as impressões."""
    chaves = {r["printing_id"]: r["card_key"] for r in con.execute(
        "SELECT printing_id, card_key FROM catalog.printings")}
    out: dict[str, int] = {}
    for pid, n in mapa.items():
        ck = chaves.get(pid)
        if ck:
            out[ck] = out.get(ck, 0) + n
    return out


def pool_dos_decks(con: sqlite3.Connection) -> dict:
    """Os três montes de onde um deck se monta, por carta lógica.

      `fixo[slug][card_key]` — o que já está sleevado NAQUELE deck. Não anda:
                               é daquele deck e de mais nenhum.
      `binder[card_key]`     — o binder Decks/Venda, o stock livre dos decks.
      `colecao[card_key]`    — os binders de coleção.

    Os dois últimos distribuem-se por prioridade, o binder primeiro. **A Coleção
    entra desde 2026-09-11** — *"se há na coleção o deck usa"* —; entre
    2026-09-10 e essa data não entrava, e o que lá estava aparecia como
    «duplicado a comprar ou a decidir». A cópia continua a contar para a
    percentagem de master set: é a mesma cópia a servir as duas coisas, que é o
    que ele pediu.
    """
    from . import locais

    fixo = {slug: _por_carta(con, mapa) for slug, mapa in locais.por_deck(con).items()}
    return {
        "fixo": fixo,
        "binder": _por_carta(con, locais.em(con, locais.BINDER)),
        "colecao": _por_carta(con, locais.na_colecao(con)),
    }


def owned_printings(con: sqlite3.Connection,
                    locais_ok: set[str] | None = None) -> dict[str, list[dict]]:
    """card_key -> impressões que tenho, para saber quais tirar da caixa.

    `locais_ok` limita a resposta a locais concretos (ex.: só o deck e o binder
    Decks/Venda). Sem ele são as cópias todas, esteja onde estiverem.
    """
    from . import locais as locais_mod

    onde = locais_mod.por_local(con) if locais_ok is not None else {}
    out: dict[str, list[dict]] = {}
    for r in con.execute(
        "SELECT p.card_key AS k, p.printing_id, p.public_code, p.set_id, "
        "       p.variant_label, c.qty "
        "FROM copies c JOIN catalog.printings p ON p.printing_id = c.printing_id "
        "WHERE c.qty > 0 ORDER BY p.set_id, p.api_sort"
    ):
        qty = r["qty"]
        if locais_ok is not None:
            qty = sum(n for loc, n in (onde.get(r["printing_id"]) or {}).items()
                      if loc in locais_ok)
            if qty <= 0:
                continue
        out.setdefault(r["k"], []).append(
            {"id": r["printing_id"], "code": r["public_code"], "set": r["set_id"],
             "label": r["variant_label"], "qty": qty})
    return out


def printing_allocation(con: sqlite3.Connection) -> dict[str, list[dict]]:
    """printing_id -> [{deck, qty}]: que cópias FÍSICAS estão em cada deck.

    Desde 2026-09-10 isto **lê-se, não se adivinha**: o local de cada cópia está
    na `copy_locations` e é ele que responde. Antes era uma heurística (a
    alocação por prioridade, com artes base primeiro) porque não havia onde
    guardar a verdade; agora há, e a heurística passou a viver só na PROPOSTA
    que ele confirma (`locais.propor_deck`).

    É isto que responde a "não encontro a carta no binder, onde está?".
    """
    from . import locais

    nomes = locais.nomes_dos_decks(con)
    prios = {r["name"]: r["priority"] for r in deck_rows(con)}
    out: dict[str, list[dict]] = {}
    for slug, mapa in sorted(locais.por_deck(con).items(),
                             key=lambda kv: (prios.get(kv[0], 999), kv[0])):
        for pid, n in mapa.items():
            out.setdefault(pid, []).append(
                {"deck": nomes.get(slug) or slug, "slug": slug, "qty": n,
                 "priority": prios.get(slug, 999)})
    return out


def binder_allocation(con: sqlite3.Connection) -> dict[str, list[dict]]:
    """printing_id -> [{deck, qty}] das cópias do BINDER Decks/Venda que os
    decks pedem.

    A alocação é por carta lógica; aqui escolhe-se a impressão, com **artes base
    primeiro** — a mesma regra de sempre, e a certa: se ele tem a base e a alt
    art no binder e um deck só precisa de uma, é a base que vai jogar e a alt
    art que fica para venda.

    O que sobra depois disto é o que a Venda propõe: *cópias no binder que
    nenhum deck pede* (André, 2026-09-10).
    """
    from . import locais

    return _por_impressao(con, "no_binder", locais.em(con, locais.BINDER))


def colecao_allocation(con: sqlite3.Connection) -> dict[str, list[dict]]:
    """printing_id -> [{deck, qty}] das cópias da COLEÇÃO que os decks usam.

    O gémeo do `binder_allocation` para o terceiro monte (2026-09-11): a
    Coleção monta decks, e a Venda precisa de saber que impressões da Coleção
    estão a ser jogadas para não as propor — *"cópias − max(usadas nos decks,
    alvo da coleção)"*, com «usadas» a ser a SOMA do que os decks levam, senão
    vendia-se uma cópia que dois decks disputam.
    """
    from . import locais

    return _por_impressao(con, "na_colecao", locais.na_colecao(con))


def _por_impressao(con: sqlite3.Connection, monte: str,
                   livre: dict[str, int]) -> dict[str, list[dict]]:
    """Distribui um monte da alocação (`no_binder` / `na_colecao`) pelas
    impressões concretas desse local, artes base primeiro."""
    alloc = allocate(con)
    livre = dict(livre)
    ordens = {s: config.set_order(s) for s in
              (r["set_id"] for r in con.execute(
                  "SELECT DISTINCT set_id FROM catalog.printings"))}
    por_carta: dict[str, list[str]] = {}
    for r in sorted(con.execute(
        "SELECT printing_id, card_key, variant_kind, set_id, api_sort "
        "FROM catalog.printings").fetchall(),
        key=lambda r: (0 if r["variant_kind"] == "base" else 1,
                       ordens.get(r["set_id"], 999), r["api_sort"])
    ):
        if livre.get(r["printing_id"], 0) > 0:
            por_carta.setdefault(r["card_key"], []).append(r["printing_id"])

    # Pelo GRUPO, lido no líder: dois decks com a mesma Legend levam as mesmas
    # cópias, e contá-las uma vez por membro punha a Venda a proteger o dobro.
    out: dict[str, list[dict]] = {}
    for d in deck_rows(con):
        a = alloc[d["deck_id"]]
        if not a["grupo"]["lider"]:
            continue
        for ck, n in a["grupo"][monte].items():
            falta = n
            for pid in por_carta.get(ck, []):
                if falta <= 0:
                    break
                tira = min(falta, livre.get(pid, 0))
                if tira:
                    livre[pid] -= tira
                    falta -= tira
                    out.setdefault(pid, []).append(
                        {"deck": a["grupo"]["rotulo"], "slug": d["name"], "qty": tira,
                         "priority": d["priority"]})
    return out


def deck_rows(con: sqlite3.Connection) -> list[sqlite3.Row]:
    return con.execute(
        "SELECT deck_id, name, display_name, legend, champion, priority, "
        "       path, missing_json FROM decks ORDER BY priority, deck_id").fetchall()


# Separador dos nomes no rótulo de um grupo com mais de um deck.
GRUPO_SEP = " ·· "


def grupos(con: sqlite3.Connection) -> list[dict]:
    """Os decks agrupados pela Legend, por ordem da melhor prioridade.

    A chave é o `card_key` da linha `Legend:` (não o texto, que pode vir com o
    prefixo «LeBlanc, » numa lista e sem ele na outra). Um deck sem Legend
    resolvida fica sozinho no seu grupo. Cada grupo: `legend`, `deck_ids`,
    `slugs`, `nomes` (rótulos), `lider` (o deck_id do membro de prioridade
    mais alta — é por ele que se somam totais), `priority`, `rotulo` (os nomes
    juntos por `GRUPO_SEP` quando são vários) e `variantes` (True se > 1).
    """
    legend_de = {r["deck_id"]: r["ck"] for r in con.execute(
        "SELECT deck_id, MIN(card_key) AS ck FROM deck_cards "
        "WHERE role = 'legend' GROUP BY deck_id")}
    por_legend: dict[str, dict] = {}
    for d in deck_rows(con):
        chave = legend_de.get(d["deck_id"]) or f"deck:{d['name']}"
        g = por_legend.setdefault(chave, {
            "legend": chave, "deck_ids": [], "slugs": [], "nomes": [],
            "lider": d["deck_id"], "priority": d["priority"]})
        g["deck_ids"].append(d["deck_id"])
        g["slugs"].append(d["name"])
        g["nomes"].append(d["display_name"] or d["name"])
    out = sorted(por_legend.values(), key=lambda g: (g["priority"], g["lider"]))
    for g in out:
        g["variantes"] = len(g["deck_ids"]) > 1
        g["rotulo"] = GRUPO_SEP.join(g["nomes"])
    return out


def grupo_de(con: sqlite3.Connection, deck_id: int) -> dict:
    return next(g for g in grupos(con) if deck_id in g["deck_ids"])


def _need(con: sqlite3.Connection, deck_id: int) -> dict[str, int]:
    """card_key -> quanto ESTE deck pede, todos os papéis somados."""
    return {r["card_key"]: r["q"] for r in con.execute(
        "SELECT card_key, SUM(qty) AS q FROM deck_cards WHERE deck_id = ? "
        "GROUP BY card_key", (deck_id,))}


def allocate(con: sqlite3.Connection) -> dict:
    """Distribui as cópias pelos decks, por ordem de prioridade.

    Cada deck serve-se de quatro montes, por esta ordem (ver `pool_dos_decks`):

      1. o que já está sleevado NESTE deck (`no_deck`) — não anda, é dele;
      2. o binder Decks/Venda (`no_binder`) — o stock livre dos decks;
      3. a Coleção (`na_colecao`) — *"se há na coleção o deck usa"* (André,
         2026-09-11);
      4. o que vem A CAMINHO (`a_caminho`) — comprado mas ainda não em casa
         (`pending`). Desde 2026-09-11 (tarde) é aqui que os `+`/`−` dos decks
         escrevem: *"o que já está encomendado (comprado), mas que ainda não
         chegou"*. Não é `have` — ele ainda não a tem na mão —, mas já não é
         para comprar. Até essa hora só a secção Faltas o descontava
         (`allocate(extra=...)`); agora desconta-se num sítio só, para o
         deck, o `stats`, o «Falta comprar, por edição» e as wantlists dizerem
         todos o mesmo número.

    Os montes 2, 3 e 4 consomem-se: o que o deck 1 leva, o deck 2 já não vê.
    **O que um deck não recebe nem tem a caminho é `missing` — falta a comprar
    — sempre.** Se as cópias existem mas estão comprometidas num deck de cima,
    `shared` diz onde (*"caso algum deck ou decks já estão a usar as cartas
    disponíveis na coleção, o próximo passa a marcar como faltas para
    comprar"*); é informação, e desde 2026-09-11 já não desconta nada do
    `missing`.

    Devolve, por deck e por carta: quanto ficou alocado e de onde, quanto vem
    a caminho para este deck, quanto falta comprar, quanto dessa falta existe
    noutro deck, e o que está marcado neste deck mas o deck já não pede
    (`extra`).

    A UNIDADE DA ALOCAÇÃO É O GRUPO DE LEGEND, NÃO O DECK (2026-09-11, noite).
    Decks com a mesma Legend são duas listas do mesmo deck físico e servem-se
    juntos: a procura do grupo é o máximo por carta entre as listas, e o
    resultado espalha-se depois por cada membro, cortado ao que ele pede. Cada
    entrada leva `grupo` — com o resultado ao nível do grupo (`missing`,
    `shared`, `a_caminho`, `no_binder`, `na_colecao`, `alloc`, `need`) e
    `lider` — e `partilhada`: por carta, os irmãos que também a pedem. Quem
    soma totais de todos os decks lê só as entradas com `grupo.lider`, senão
    conta o grupo uma vez por membro.
    """
    from . import pending

    p = pool_dos_decks(con)
    binder = dict(p["binder"])
    colecao = dict(p["colecao"])
    caminho = dict(pending.open_by_card(con))
    por_id = {d["deck_id"]: d for d in deck_rows(con)}
    held: dict[str, list[dict]] = {}     # card_key -> grupos que já a levaram
    out = {}

    for g in grupos(con):
        membros = [por_id[i] for i in g["deck_ids"]]
        needs = {d["deck_id"]: _need(con, d["deck_id"]) for d in membros}
        # A procura do grupo: o MÁXIMO entre as listas, carta a carta. A
        # alocação é por carta lógica, não por papel: uma carta que esteja no
        # main e no sideboard disputa o mesmo stock.
        need: dict[str, int] = {}
        for nd in needs.values():
            for ck, q in nd.items():
                need[ck] = max(need.get(ck, 0), q)
        # O que está sleevado em qualquer dos membros é do grupo: é o mesmo
        # deck físico com duas listas.
        fixo: dict[str, int] = {}
        for d in membros:
            for ck, n in (p["fixo"].get(d["name"]) or {}).items():
                fixo[ck] = fixo.get(ck, 0) + n

        alloc, no_deck, no_binder, na_colecao, a_caminho = {}, {}, {}, {}, {}
        shared, missing = {}, {}
        for ck, qty in need.items():
            do_deck = min(qty, fixo.get(ck, 0))
            fixo[ck] = fixo.get(ck, 0) - do_deck
            do_binder = min(qty - do_deck, binder.get(ck, 0))
            binder[ck] = binder.get(ck, 0) - do_binder
            da_colecao = min(qty - do_deck - do_binder, colecao.get(ck, 0))
            colecao[ck] = colecao.get(ck, 0) - da_colecao

            take = do_deck + do_binder + da_colecao
            if take:
                alloc[ck] = take
                if do_deck:
                    no_deck[ck] = do_deck
                if do_binder:
                    no_binder[ck] = do_binder
                if da_colecao:
                    na_colecao[ck] = da_colecao
                held.setdefault(ck, []).append(
                    {"deck": g["rotulo"], "slug": por_id[g["lider"]]["name"],
                     "grupo": g["legend"], "qty": take, "priority": g["priority"]})

            # O que vem a caminho serve o primeiro grupo que ainda a peça — é
            # uma cópia da Coleção como as outras, só que ainda não chegou.
            # Fica fora do `alloc`: o deck não a TEM, só já não a compra.
            encomendada = min(qty - take, caminho.get(ck, 0))
            caminho[ck] = caminho.get(ck, 0) - encomendada
            if encomendada:
                a_caminho[ck] = encomendada

            falta = qty - take - encomendada
            if not falta:
                continue
            missing[ck] = falta
            # Existe, mas está num grupo de cima? Fica escrito de onde vem a
            # falta — «-> 3x em Azir» — e compra-se na mesma. O irmão do
            # mesmo grupo nunca aparece aqui: partilha, não disputa.
            noutro = [h for h in held.get(ck, []) if h["grupo"] != g["legend"]]
            if noutro:
                shared[ck] = {"qty": min(falta, sum(h["qty"] for h in noutro)),
                              "em": noutro}

        resultado = {"alloc": alloc, "no_deck": no_deck, "no_binder": no_binder,
                     "na_colecao": na_colecao, "a_caminho": a_caminho,
                     "missing": missing, "shared": shared, "need": need}

        # Espalha-se pelos membros, cortado ao que CADA lista pede. As fontes
        # repartem-se pela mesma ordem (deck, binder, Coleção); o `missing` de
        # um membro é o máximo que o grupo ainda compra para aquela carta, e
        # por isso igual nos dois quando pedem a mesma quantidade.
        for d in membros:
            nd = needs[d["deck_id"]]
            m_alloc, m_deck, m_binder, m_col, m_cam, m_miss, m_shared = {}, {}, {}, {}, {}, {}, {}
            partilhada: dict[str, list[dict]] = {}
            for ck, qty in nd.items():
                take = min(qty, alloc.get(ck, 0))
                dd = min(take, no_deck.get(ck, 0))
                db = min(take - dd, no_binder.get(ck, 0))
                dc = take - dd - db
                enc = min(qty - take, a_caminho.get(ck, 0))
                falta = qty - take - enc
                if take:
                    m_alloc[ck] = take
                if dd:
                    m_deck[ck] = dd
                if db:
                    m_binder[ck] = db
                if dc:
                    m_col[ck] = dc
                if enc:
                    m_cam[ck] = enc
                if falta:
                    m_miss[ck] = falta
                    if ck in shared:
                        m_shared[ck] = {"qty": min(falta, shared[ck]["qty"]),
                                        "em": shared[ck]["em"]}
                irmaos = [{"deck": por_id[i]["display_name"] or por_id[i]["name"],
                           "slug": por_id[i]["name"], "qty": needs[i].get(ck, 0)}
                          for i in g["deck_ids"] if i != d["deck_id"] and needs[i].get(ck)]
                if irmaos:
                    partilhada[ck] = irmaos

            # O que está marcado NESTE deck e a lista dele já não pede — a
            # carta continua na caixa. Aparece para não desaparecer do ecrã.
            proprio = p["fixo"].get(d["name"]) or {}
            sobra = {ck: n - min(n, nd.get(ck, 0)) for ck, n in proprio.items()
                     if n - min(n, nd.get(ck, 0)) > 0}
            out[d["deck_id"]] = {
                "alloc": m_alloc, "no_deck": m_deck, "no_binder": m_binder,
                "na_colecao": m_col, "a_caminho": m_cam, "missing": m_miss,
                "shared": m_shared, "extra": sobra, "partilhada": partilhada,
                "grupo": {**resultado, "legend": g["legend"], "rotulo": g["rotulo"],
                          "membros": g["nomes"], "slugs": g["slugs"],
                          "variantes": g["variantes"],
                          "lider": d["deck_id"] == g["lider"]},
            }

    return out


def uso_por_carta(con: sqlite3.Connection) -> dict[str, list[dict]]:
    """card_key -> [{deck, slug, priority, wanted, have, missing}], por prioridade.

    É o que a Coleção mostra em cada carta — *"na coleção indica onde as cartas
    estão a ser usadas"* (André, 2026-09-11): «Azir 3 · Kennen 2 (faltam 2)».
    Só as cartas que algum deck pede aparecem.

    Uma entrada por GRUPO de Legend, não por deck (2026-09-11, noite): os dois
    LeBlanc pedem as mesmas cópias e listá-los aos dois era contar a dobrar. O
    `deck` é o rótulo dos membros que pedem a carta — «LeBlanc» se só um a
    pede, «LeBlanc ·· LeBlanc Baited Hook» se os dois —, `membros` lista-os, e
    `wanted`/`missing` são os do grupo (o máximo entre as listas).
    """
    alloc = allocate(con)
    por_slug = {d["name"]: d for d in deck_rows(con)}
    out: dict[str, list[dict]] = {}
    for d in deck_rows(con):
        a = alloc[d["deck_id"]]
        g = a["grupo"]
        if not g["lider"]:
            continue
        nomes = {por_slug[s]["deck_id"]: por_slug[s]["display_name"] or s
                 for s in g["slugs"]}
        pedem: dict[str, list[int]] = {}
        for i in nomes:
            for ck in _need(con, i):
                pedem.setdefault(ck, []).append(i)
        for ck, qty in g["need"].items():
            quem = [nomes[i] for i in pedem.get(ck, [])]
            out.setdefault(ck, []).append({
                "deck": GRUPO_SEP.join(quem) if quem else g["rotulo"],
                "membros": quem, "slug": d["name"],
                "priority": d["priority"], "wanted": qty,
                "have": g["alloc"].get(ck, 0), "ordered": g["a_caminho"].get(ck, 0),
                "missing": g["missing"].get(ck, 0),
            })
    return out


def resumo_das_faltas(con: sqlite3.Connection) -> dict:
    """O total a comprar para os decks, por cartas e cópias, com euros.

    É a linha do `riftvault stats` e a soma da tabela do `riftvault decks`: o
    `missing` de todos os decks, ao preço da impressão base mais barata. As
    `disputadas` são a parte dessa falta que existe noutro deck.

    Soma-se por GRUPO de Legend, lido no líder: o que falta aos dois LeBlanc é
    a mesma carta e conta uma vez (2026-09-11, noite).
    """
    alloc = {k: a["grupo"] for k, a in allocate(con).items() if a["grupo"]["lider"]}
    prices = {r["printing_id"]: r["price_cents"] for r in con.execute(
        "SELECT printing_id, price_cents FROM catalog.price_latest "
        "WHERE price_cents IS NOT NULL")}
    barato: dict[str, int] = {}
    for r in con.execute("SELECT card_key, printing_id FROM catalog.printings "
                         "WHERE variant_kind = 'base'"):
        p = prices.get(r["printing_id"])
        if p is not None:
            barato[r["card_key"]] = min(barato.get(r["card_key"], p), p)
    cartas: set[str] = set()
    copias = cents = disputadas = encomendadas = 0
    for a in alloc.values():
        for ck, n in a["missing"].items():
            cartas.add(ck)
            copias += n
            cents += (barato.get(ck) or 0) * n
        disputadas += sum(v["qty"] for v in a["shared"].values())
        encomendadas += sum(a["a_caminho"].values())
    return {"cards": len(cartas), "copies": copias, "cents": cents,
            "disputed": disputadas, "ordered": encomendadas}


# ---------------------------------------------------------------------------
# Payloads
# ---------------------------------------------------------------------------


def missing_by_set(con: sqlite3.Connection, deck_id: int,
                   ignore_types: set[str] | None = None,
                   grupo: bool = False) -> list[dict]:
    """Cópias em falta neste deck, por edição onde as ir buscar.

    Cada carta é atribuída à edição onde sai **mais barata** — é a decisão
    prática, porque é onde ele a vai comprar. Uma carta que exista em mais do
    que uma edição fica contada só uma vez, na mais barata, e é assinalada em
    `multi` para o número não parecer mais firme do que é.

    Inclui as que faltam por estarem noutro deck: desde 2026-09-11 também se
    compram — *"o próximo passa a marcar como faltas para comprar"*.

    `grupo=True` responde pelo GRUPO de Legend do deck (o máximo entre as
    listas dos irmãos) — é o que se soma quando se juntam os decks todos, para
    os dois LeBlanc não contarem a dobrar.
    """
    a = allocate(con)[deck_id]
    falta = a["grupo"]["missing"] if grupo else a["missing"]
    if ignore_types:
        tipos = {r["card_key"]: r["type"] for r in con.execute(
            "SELECT card_key, type FROM catalog.cards")}
        falta = {k: v for k, v in falta.items() if tipos.get(k) not in ignore_types}
    if not falta:
        return []

    ordens = {s: config.set_order(s) for s in
              (r["set_id"] for r in con.execute("SELECT DISTINCT set_id FROM catalog.printings"))}
    nomes = {r["card_key"]: r["name"] for r in con.execute(
        "SELECT card_key, name FROM catalog.cards")}
    opcoes: dict[str, list[dict]] = {}
    ph = ",".join("?" * len(falta))
    for r in con.execute(
        f"SELECT p.card_key, p.set_id, p.printing_id, p.public_code, p.orientation, "
        f"       p.image_medium, p.image_large, p.image_url, pl.price_cents "
        f"FROM catalog.printings p "
        f"LEFT JOIN catalog.price_latest pl ON pl.printing_id = p.printing_id "
        f"WHERE p.card_key IN ({ph}) AND p.variant_kind = 'base'", list(falta)
    ):
        opcoes.setdefault(r["card_key"], []).append({
            "set": r["set_id"], "price": r["price_cents"], "id": r["printing_id"],
            "code": r["public_code"],
            "landscape": (r["orientation"] or "").lower() == "landscape",
            "cdn": r["image_medium"] or r["image_large"] or r["image_url"],
        })

    por_set: dict[str, dict] = {}
    for ck, n in falta.items():
        cands = opcoes.get(ck) or []
        if not cands:
            continue
        sets = {c["set"] for c in cands}
        # Mais barata primeiro; sem preço, a edição mais antiga.
        melhor = min(cands, key=lambda c: (c["price"] is None,
                                           c["price"] if c["price"] is not None else 0,
                                           ordens.get(c["set"], 999)))
        d = por_set.setdefault(melhor["set"], {"set": melhor["set"], "cards": 0,
                                               "copies": 0, "cents": 0, "multi": 0,
                                               "items": []})
        d["cards"] += 1
        d["copies"] += n
        d["cents"] += (melhor["price"] or 0) * n
        if len(sets) > 1:
            d["multi"] += 1
        d["items"].append({
            "card_key": ck, "name": nomes.get(ck, ck), "qty": n,
            "code": melhor["code"], "price": melhor["price"],
            "total": (melhor["price"] or 0) * n,
            "img": f"img/{melhor['id']}.webp", "cdn": melhor["cdn"],
            "landscape": melhor["landscape"],
            # Existe noutras edições — dá para a ires buscar a outro lado.
            "also": sorted(sets - {melhor["set"]}),
        })

    out = list(por_set.values())
    for d in out:
        d["name"] = config.set_name(d["set"])
        d["items"].sort(key=lambda x: (-x["total"], x["name"]))
    # Por ordem de lançamento, não por quantidade: é a mesma ordem dos
    # separadores das edições, e vem do `order` no riftvault_config.json.
    out.sort(key=lambda d: (config.set_order(d["set"]), d["set"]))
    return out


def rules() -> dict:
    r = dict(DEFAULT_RULES)
    r.update(config.load().get("deck_rules", {}))
    return r


def decks_index(con: sqlite3.Connection) -> list[dict]:
    alloc = allocate(con)
    por_slug = {d["name"]: d["deck_id"] for d in deck_rows(con)}
    out = []
    for d in deck_rows(con):
        a = alloc[d["deck_id"]]
        pedidas = con.execute(
            "SELECT COALESCE(SUM(qty),0) AS q FROM deck_cards WHERE deck_id = ?",
            (d["deck_id"],)).fetchone()["q"]
        tenho = sum(a["alloc"].values())
        out.append({
            "id": d["deck_id"], "slug": d["name"],
            "name": d["display_name"] or d["name"],
            "legend": d["legend"], "champion": d["champion"],
            "priority": d["priority"],
            "wanted": pedidas, "have": tenho,
            # De onde vem o que está alocado — os três somam o `have`.
            "no_deck": sum(a["no_deck"].values()),
            "no_binder": sum(a["no_binder"].values()),
            "na_colecao": sum(a["na_colecao"].values()),
            "extra": sum(a["extra"].values()),
            # Comprado, ainda não em casa: não conta no `have`, já não conta
            # no `missing`.
            "ordered": sum(a["a_caminho"].values()),
            "missing": sum(a["missing"].values()),
            # A parte do `missing` que existe num deck de cima: disputada.
            "shared": sum(v["qty"] for v in a["shared"].values()),
            # O grupo de Legend a que pertence (2026-09-11, noite): os irmãos
            # partilham as cartas e o total geral conta o grupo uma vez, pelo
            # líder. `partilhadas` é quantas cópias desta lista o irmão também
            # pede — é o que explica porque é que a soma das linhas passa o
            # total.
            "grupo": {
                "legend": a["grupo"]["legend"], "rotulo": a["grupo"]["rotulo"],
                "membros": a["grupo"]["membros"], "slugs": a["grupo"]["slugs"],
                "variantes": a["grupo"]["variantes"], "lider": a["grupo"]["lider"],
                "irmaos": [n for n in a["grupo"]["membros"]
                           if n != (d["display_name"] or d["name"])],
                "missing": sum(a["grupo"]["missing"].values()),
                "partilhadas": sum(
                    min(n, max((alloc[por_slug[i["slug"]]]["missing"].get(ck, 0)
                                for i in a["partilhada"].get(ck, [])), default=0))
                    for ck, n in a["missing"].items()),
            },
        })
    return out


def deck_payload(con: sqlite3.Connection, deck_id: int) -> dict | None:
    d = con.execute("SELECT * FROM decks WHERE deck_id = ?", (deck_id,)).fetchone()
    if not d:
        return None
    from . import locais, pending

    a = allocate(con)[deck_id]
    # A impressão em que o `+` de cada linha grava a encomenda (a base mais
    # barata), para o ecrã dizer qual é antes de ele carregar.
    chaves = [r["card_key"] for r in con.execute(
        "SELECT DISTINCT card_key FROM deck_cards WHERE deck_id = ?", (deck_id,))]
    encomendar_em = pending.impressao_para_encomendar(con, chaves)
    # As impressões que ESTE deck pode usar: as que estão nele, as do binder
    # Decks/Venda e as da Coleção — os três montes (2026-09-11).
    prints = owned_printings(con, {locais.deck_local(d["name"]), locais.BINDER,
                                   locais.COLECAO})
    names = {r["card_key"]: r for r in con.execute(
        "SELECT card_key, name, type, domains_json FROM catalog.cards")}

    # Imagem por carta: a impressão representativa do catálogo. Se ele tiver a
    # carta, vale mais mostrar a arte que tem em casa do que a canónica.
    arte = {r["card_key"]: r for r in con.execute(
        "SELECT c.card_key, p.printing_id, p.public_code, p.set_id, p.orientation, "
        "       p.image_medium, p.image_large, p.image_url "
        "FROM catalog.cards c JOIN catalog.printings p "
        "ON p.printing_id = c.rep_printing_id")}
    por_id = {r["printing_id"]: r for r in con.execute(
        "SELECT printing_id, public_code, set_id, orientation, "
        "       image_medium, image_large, image_url FROM catalog.printings")}

    # Preço da impressão, para aparecer ao lado do código na lista do deck.
    precos = {r["printing_id"]: r["price_cents"] for r in con.execute(
        "SELECT printing_id, price_cents FROM catalog.price_latest "
        "WHERE price_cents IS NOT NULL")}

    def imagem(card_key: str) -> dict:
        tenho = prints.get(card_key)
        r = por_id.get(tenho[0]["id"]) if tenho else arte.get(card_key)
        if not r:
            return {"img": None, "cdn": None, "landscape": False,
                    "code": None, "set": None, "price": None}
        return {
            "img": f"img/{r['printing_id']}.webp",
            "cdn": r["image_medium"] or r["image_large"] or r["image_url"],
            "landscape": (r["orientation"] or "").lower() == "landscape",
            "code": r["public_code"],
            "set": r["set_id"],
            "price": precos.get(r["printing_id"]),
        }

    # Quanto de cada carta já foi consumido por papéis anteriores deste deck:
    # a alocação é por carta, mas mostra-se por papel.
    usado: dict[str, int] = {}
    usado_deck: dict[str, int] = {}
    usado_binder: dict[str, int] = {}
    usado_caminho: dict[str, int] = {}
    sections = []
    for role in ROLE_ORDER:
        rows = con.execute(
            "SELECT card_key, qty, raw_line FROM deck_cards WHERE deck_id = ? AND role = ? "
            "ORDER BY raw_line", (deck_id, role)).fetchall()
        if not rows:
            continue
        cards = []
        for r in rows:
            ck = r["card_key"]
            disponivel = max(0, a["alloc"].get(ck, 0) - usado.get(ck, 0))
            tenho = min(r["qty"], disponivel)
            usado[ck] = usado.get(ck, 0) + tenho
            # De onde vem o que tem: já sleevada no deck, por ir buscar ao
            # binder Decks/Venda, ou na Coleção. Os três somam o `have`; são
            # três sítios diferentes onde ele a vai encontrar.
            no_deck = min(tenho, max(0, a["no_deck"].get(ck, 0) - usado_deck.get(ck, 0)))
            usado_deck[ck] = usado_deck.get(ck, 0) + no_deck
            no_binder = min(tenho - no_deck,
                            max(0, a["no_binder"].get(ck, 0) - usado_binder.get(ck, 0)))
            usado_binder[ck] = usado_binder.get(ck, 0) + no_binder
            # O que vem a caminho para esta linha: depois do que tem, e pela
            # mesma ordem de papéis. Não é `have`, e já não é `missing`.
            encomendada = min(r["qty"] - tenho,
                              max(0, a["a_caminho"].get(ck, 0) - usado_caminho.get(ck, 0)))
            usado_caminho[ck] = usado_caminho.get(ck, 0) + encomendada
            falta = r["qty"] - tenho - encomendada
            info = names.get(ck) or {}
            alvo = encomendar_em.get(ck) or {}
            cards.append({
                "card_key": ck,
                "name": (info["name"] if info else r["raw_line"]),
                "raw": r["raw_line"],
                "type": info["type"] if info else None,
                "wanted": r["qty"], "have": tenho, "missing": falta,
                "ordered": encomendada,
                "no_deck": no_deck, "no_binder": no_binder,
                "na_colecao": tenho - no_deck - no_binder,
                # Onde o `+` grava a encomenda: a impressão base mais barata.
                "order_code": alvo.get("code"), "order_price": alvo.get("price"),
                # Onde está o que falta, quando existe num deck de cima.
                "shared": a["shared"].get(ck) if falta else None,
                # Os irmãos do grupo (mesma Legend) que também pedem esta
                # carta: partilham-na, não a disputam. É uma compra só.
                "partilhada": a["partilhada"].get(ck),
                "printings": prints.get(ck, []),
                **imagem(ck),
            })
        sections.append({"role": role, "label": ROLE_LABEL[role], "cards": cards,
                         "wanted": sum(c["wanted"] for c in cards),
                         "have": sum(c["have"] for c in cards),
                         "ordered": sum(c["ordered"] for c in cards),
                         "no_deck": sum(c["no_deck"] for c in cards),
                         "no_binder": sum(c["no_binder"] for c in cards),
                         "na_colecao": sum(c["na_colecao"] for c in cards)})

    return {
        "id": deck_id, "slug": d["name"], "name": d["display_name"] or d["name"],
        "legend": d["legend"], "champion": d["champion"], "priority": d["priority"],
        "sections": sections,
        "missing_by_set": missing_by_set(con, deck_id),
        "legality": legality(con, deck_id),
        "unresolved": json.loads(d["missing_json"] or "[]"),
        # O grupo de Legend (2026-09-11, noite): os irmãos com quem esta lista
        # partilha as cartas, e o que o grupo compra ao todo.
        "grupo": {
            "rotulo": a["grupo"]["rotulo"], "membros": a["grupo"]["membros"],
            "variantes": a["grupo"]["variantes"], "lider": a["grupo"]["lider"],
            "irmaos": [n for n in a["grupo"]["membros"]
                       if n != (d["display_name"] or d["name"])],
            "missing": sum(a["grupo"]["missing"].values()),
        },
        # De onde vêm as cartas deste deck (os três montes somam o `have`), o
        # que falta comprar e quanto dessa falta está noutro deck. O `extra` é
        # o que está marcado neste deck e o deck já não pede — a lista mudou, a
        # carta continua na caixa.
        "locais": {
            "local": locais.deck_local(d["name"]),
            "no_deck": sum(a["no_deck"].values()),
            "no_binder": sum(a["no_binder"].values()),
            "na_colecao": sum(a["na_colecao"].values()),
            "extra": sum(a["extra"].values()),
            "ordered": sum(a["a_caminho"].values()),
            "missing": sum(a["missing"].values()),
            "shared": sum(v["qty"] for v in a["shared"].values()),
        },
    }


def legality(con: sqlite3.Connection, deck_id: int) -> dict:
    """Validação contra as regras do config. NÃO são as regras oficiais."""
    r = rules()
    counts = {row["role"]: row["q"] for row in con.execute(
        "SELECT role, COALESCE(SUM(qty),0) AS q FROM deck_cards WHERE deck_id = ? "
        "GROUP BY role", (deck_id,))}

    main = counts.get("main", 0) + (counts.get("champion", 0)
                                    if r["main_includes_champion"] else 0)
    excesso = [row["card_key"] for row in con.execute(
        "SELECT card_key, SUM(qty) AS q FROM deck_cards WHERE deck_id = ? "
        "AND role IN ('main','champion') GROUP BY card_key HAVING q > ?",
        (deck_id, r["max_copies"]))]

    # Identidade de domínio: o Legend manda.
    legend_dom = con.execute(
        "SELECT c.domains_json FROM deck_cards d JOIN catalog.cards c "
        "ON c.card_key = d.card_key WHERE d.deck_id = ? AND d.role = 'legend'",
        (deck_id,)).fetchone()
    # `or "[]"`: a coluna é anulável e um Legend sem domínios rebentava aqui a
    # secção Decks inteira. É a mesma guarda que o ciclo a seguir já fazia.
    # `or "[]"`: a coluna é anulável e um Legend sem domínios rebentava aqui a
    # secção Decks inteira. É a mesma guarda que o ciclo a seguir já fazia.
    dominios = set(json.loads(legend_dom["domains_json"] or "[]")) if legend_dom else set()
    fora = []
    if dominios:
        for row in con.execute(
            "SELECT c.name, c.domains_json FROM deck_cards d "
            "JOIN catalog.cards c ON c.card_key = d.card_key "
            "WHERE d.deck_id = ? AND d.role IN ('main','champion','runes','sideboard')",
            (deck_id,)
        ):
            dom = set(json.loads(row["domains_json"] or "[]"))
            if dom and not dom <= dominios | {"Colorless"}:
                fora.append({"name": row["name"], "domains": sorted(dom)})

    return {
        "main": {"n": main, "alvo": r["main"], "ok": main == r["main"]},
        "runes": {"n": counts.get("runes", 0), "alvo": r["runes"],
                  "ok": counts.get("runes", 0) == r["runes"]},
        "battlefields": {"n": counts.get("battlefields", 0), "alvo": r["battlefields"],
                         "ok": counts.get("battlefields", 0) == r["battlefields"]},
        "max_copies": {"alvo": r["max_copies"], "excesso": excesso, "ok": not excesso},
        "dominios": {"legend": sorted(dominios), "fora": fora, "ok": not fora},
        "main_inclui_champion": r["main_includes_champion"],
    }


def set_order(con: sqlite3.Connection, ordered_ids: list[int]) -> None:
    """Reordena os decks. O primeiro da lista passa a ser o principal."""
    con.execute("BEGIN")
    for i, deck_id in enumerate(ordered_ids, start=1):
        con.execute("UPDATE decks SET priority = ? WHERE deck_id = ?", (i, deck_id))
    con.execute("COMMIT")


def shopping_list(con: sqlite3.Connection, deck_id: int | None = None) -> list[dict]:
    """O que falta comprar. Sem deck_id, junta todos os decks."""
    alloc = allocate(con)
    prices = {r["printing_id"]: r["price_cents"] for r in con.execute(
        "SELECT printing_id, price_cents FROM catalog.price_latest "
        "WHERE price_cents IS NOT NULL")}
    barato: dict[str, int] = {}
    for r in con.execute("SELECT card_key, printing_id FROM catalog.printings"):
        p = prices.get(r["printing_id"])
        if p is not None:
            k = r["card_key"]
            barato[k] = min(barato.get(k, p), p)

    names = {r["card_key"]: r["name"] for r in con.execute(
        "SELECT card_key, name FROM catalog.cards")}
    # Tudo junto soma-se por GRUPO de Legend, pelo líder — os irmãos pedem as
    # mesmas cópias (2026-09-11, noite).
    juntos: dict[str, int] = {}
    for d in deck_rows(con):
        a = alloc[d["deck_id"]]
        if deck_id and d["deck_id"] != deck_id:
            continue
        if not deck_id and not a["grupo"]["lider"]:
            continue
        falta = a["missing"] if deck_id else a["grupo"]["missing"]
        for ck, q in falta.items():
            juntos[ck] = juntos.get(ck, 0) + q

    return sorted(
        [{"card_key": ck, "name": names.get(ck, ck), "qty": q,
          "price_cents": barato.get(ck), "total_cents": (barato.get(ck) or 0) * q}
         for ck, q in juntos.items()],
        key=lambda x: -x["total_cents"])

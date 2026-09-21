"""O histórico do que cada deck PEDE — e as cartas que os decks libertaram.

André, 2026-09-17: *"agora cria um botao que e o 'a mais' onde vai todas as
cartas que estao listadas a mais ou que estavam num deck e deixaram de estar"*.

A segunda metade da frase precisa de MEMÓRIA, e o riftvault não a tinha. A
alocação aos decks (`decks.allocate`) é recalculada a cada leitura a partir dos
`decks/*.txt`; a `copy_locations` guarda só o que ele marca à mão (e está vazia
no vault.db real); a `ops` diz quantas cópias existem, não quem as pedia. Uma
carta que saísse de uma lista deixava de aparecer e mais nada. **Não se
adivinha o passado**: o registo começa aqui, vazio, e enche a partir da
primeira importação depois desta ordem. Antes disso o bloco «libertadas dos
decks» está vazio, e a página di-lo.

O QUE SE REGISTA É O PEDIDO, NÃO A ALOCAÇÃO
    «Estava num deck» = a lista do deck pedia-a. Registar a alocação era pior:
    ela desce quando ele vende uma cópia ou quando um deck de cima passa a
    levar a carta, e nenhuma dessas é «saiu do deck». O pedido só muda quando
    o `.txt` muda — ou quando o ficheiro desaparece, que é como se apaga um
    deck, e aí todas as cartas dele descem a 0.

ONDE SE ESCREVE
    No fim do `decks.import_all`, o único sítio por onde as listas entram —
    seja pelo servidor (`_reimport_if_changed`), pelo `build` ou pela CLI.
    Só escreve quando o pedido difere da última linha registada, por isso uma
    importação sem alterações não toca no vault.db (a mesma regra do
    `import_all` desde 2026-09-10). A tabela é a `deck_need_log` (vault.db,
    committada, sobrevive a tudo); o rasto legível para ele é o
    `data/decks.log`, escrito ao mesmo tempo, como o `locais.log`.

A PRIMEIRA CORRIDA É O PONTO DE PARTIDA
    Com a tabela vazia, tudo o que os decks pedem entra como `0 -> N`. Não é
    uma libertação (é uma subida) e por isso não aparece em lado nenhum — é só
    o chão a partir do qual as descidas passam a ter significado.
"""

from __future__ import annotations

import csv
import io
import sqlite3
from datetime import datetime, timezone

from . import config

LOG_NAME = "decks.log"
BOM = "﻿"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def pedido_atual(con: sqlite3.Connection) -> dict[tuple[str, str], dict]:
    """(slug, card_key) -> {qty, deck}: o que cada lista pede HOJE, todos os
    papéis somados — a mesma conta do `decks._need`."""
    out: dict[tuple[str, str], dict] = {}
    for r in con.execute(
        "SELECT d.name AS slug, COALESCE(d.display_name, d.name) AS deck, "
        "       c.card_key, SUM(c.qty) AS q "
        "FROM deck_cards c JOIN decks d ON d.deck_id = c.deck_id "
        "GROUP BY d.name, c.card_key"
    ):
        out[(r["slug"], r["card_key"])] = {"qty": r["q"], "deck": r["deck"]}
    return out


def estado(con: sqlite3.Connection) -> dict[tuple[str, str], dict]:
    """(slug, card_key) -> a última linha do registo: o que se sabia que o
    deck pedia. Vazio antes da primeira importação registada."""
    out: dict[tuple[str, str], dict] = {}
    for r in con.execute(
        "SELECT l.slug, l.deck, l.card_key, l.qty_before, l.qty_after, l.ts "
        "FROM deck_need_log l "
        "WHERE l.id = (SELECT MAX(id) FROM deck_need_log "
        "              WHERE slug = l.slug AND card_key = l.card_key)"
    ):
        out[(r["slug"], r["card_key"])] = dict(r)
    return out


def registar(con: sqlite3.Connection) -> list[dict]:
    """Compara o pedido de hoje com o último registado e escreve as diferenças.

    Devolve as linhas escritas (vazio quando nada mudou — e nesse caso não
    toca na base). Nunca impede a importação: um erro a escrever o CSV é
    engolido, como no `locais._log`; a tabela é a verdade.
    """
    agora = pedido_atual(con)
    antes = estado(con)
    ts = _now()
    linhas: list[dict] = []
    for chave in sorted(set(agora) | set(antes)):
        novo = agora.get(chave)
        velho = antes.get(chave)
        q_novo = novo["qty"] if novo else 0
        q_velho = velho["qty_after"] if velho else 0
        if q_novo == q_velho:
            continue
        linhas.append({
            "ts": ts, "slug": chave[0],
            # O rótulo de hoje se o deck existe; senão o último que se viu,
            # para o ecrã dizer «saiu do Akali» depois de o Akali ser apagado.
            "deck": (novo or velho)["deck"],
            "card_key": chave[1], "qty_before": q_velho, "qty_after": q_novo,
        })
    if not linhas:
        return []
    con.execute("BEGIN")
    con.executemany(
        "INSERT INTO deck_need_log (ts, slug, deck, card_key, qty_before, qty_after) "
        "VALUES (:ts, :slug, :deck, :card_key, :qty_before, :qty_after)", linhas)
    con.execute("COMMIT")
    _log(con, linhas)
    return linhas


def recomecar(con: sqlite3.Connection) -> int:
    """Apaga o registo e escreve o ponto de partida com o que os decks pedem
    HOJE (`0 -> N`, uma linha por (deck, carta)).

    André, 2026-09-21, ao trocar os decks todos: *"recalcula o deck_need_log
    a partir dos seis decks (não somes por cima do que lá estava)"*. Sem isto
    a troca ficava registada como descidas dos decks antigos por cima do
    histórico — dezenas de «libertadas» que não são cartas que ele deixou de
    jogar, são a lista velha. Depois disto as «libertadas» do A mais estão
    vazias até a próxima lista mudar. O `data/decks.log` (o CSV legível) fica
    com o rasto todo e leva as linhas de partida a seguir — é rasto, não
    verdade; a tabela é a verdade. Devolve quantas linhas de partida escreveu.
    """
    con.execute("BEGIN")
    con.execute("DELETE FROM deck_need_log")
    con.execute("COMMIT")
    return len(registar(con))


def _log(con: sqlite3.Connection, linhas: list[dict]) -> None:
    """Uma linha por mudança em `data/decks.log`, com o nome da carta."""
    nomes = {r["card_key"]: r["name"] for r in con.execute(
        "SELECT card_key, name FROM catalog.cards")}
    caminho = config.DATA_DIR / LOG_NAME
    novo = not caminho.exists()
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    if novo:
        w.writerow(["quando", "deck", "slug", "carta", "pedia", "passa_a_pedir"])
    for x in linhas:
        w.writerow([x["ts"], x["deck"], x["slug"], nomes.get(x["card_key"], x["card_key"]),
                    x["qty_before"], x["qty_after"]])
    try:
        config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(caminho, "a", encoding="utf-8", newline="") as fh:
            if novo:
                fh.write(BOM)
            fh.write(buf.getvalue())
    except OSError:
        pass


def libertadas(con: sqlite3.Connection) -> list[dict]:
    """As (deck, carta) cuja ÚLTIMA mudança foi uma descida: o que o deck pedia
    e deixou de pedir, e quando.

    Uma carta que o deck volte a pôr na lista tem uma subida por cima e sai
    daqui sozinha. `qty` é o que foi libertado (`qty_before − qty_after`);
    `still` é o que o mesmo deck ainda pede, se ainda pedir algum.
    """
    out = []
    for chave, r in estado(con).items():
        if r["qty_after"] >= r["qty_before"]:
            continue
        out.append({"slug": r["slug"], "deck": r["deck"], "card_key": r["card_key"],
                    "qty": r["qty_before"] - r["qty_after"], "still": r["qty_after"],
                    "ts": r["ts"]})
    out.sort(key=lambda x: (x["ts"], x["slug"], x["card_key"]), reverse=True)
    return out


def resumo(con: sqlite3.Connection) -> dict:
    """Desde quando há registo e quantas mudanças tem — para a página dizer
    «o registo começou a …» em vez de deixar o bloco vazio sem explicação."""
    r = con.execute("SELECT MIN(ts) AS desde, COUNT(*) AS n FROM deck_need_log").fetchone()
    return {"since": r["desde"], "events": r["n"]}

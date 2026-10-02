"""COLAR UMA DECKLIST (2026-10-02) — a porta pela janela do browser.

André, 2026-10-01: *"dos decks, tem que ser possivel colar o texto em copy
paste e gerar o deck, depois diz as cartas que tens e que nao tens"*. Até aqui
a única maneira de meter uma lista era pôr um `.txt` na pasta `decks/` à mão.

**NÃO HÁ LEITOR NOVO.** O texto colado entra pelo `decks.parse_texto`, que é o
mesmo que lê os `.txt`, e o deck nasce pelo `decks.import_all`, que é o mesmo
que importa os ficheiros. O que esta camada faz são três coisas que o ficheiro
não precisava:

  1. `prever()` — diz o que vai gravar ANTES de gravar: as linhas que casaram,
     as que não casaram, e a aritmética por papel. Uma lista com um nome que o
     catálogo não conhece **não pode virar um deck em silêncio**, e por isso
     `gravar()` sem `confirmar` recusa-a (`PrecisaConfirmar`, a mesma forma do
     `venda.vender`).
  2. `gravar()` — escreve o `.txt` na pasta DE QUEM colou
     (`config.decks_dir(con)`, que é por utilizador desde 2026-09-29) e
     reimporta. O ficheiro é o formato de sempre: o que ele colou continua a
     dar-se a ler, a versionar-se no Git (na pasta dele) e a abrir-se num
     editor — colar não é um caminho paralelo, é a mesma porta com outra
     entrada.
  3. o SLUG, que é o nome do ficheiro e a chave do deck em todo o lado
     (2026-09-11): sai do `Nome:`, ou da Legend quando ele não o escreveu.

A caixa vive só no modo EDIÇÃO (o 8770 / editar.baverone.com) — o site
publicado é de leitura e não tem onde gravar.
"""
from __future__ import annotations

import re
import sqlite3
import unicodedata
from pathlib import Path

from . import config, decks

#: Quanto texto se aceita de uma vez. Uma decklist são ~50 linhas; isto é
#: folgado para uma lista comentada e aperta antes de alguém colar um livro.
MAX_TEXTO = 20_000

#: O que o `.txt` leva à frente quando nasceu de uma colagem. É um comentário
#: (o `parse_texto` salta as linhas com `#`), e serve para quem abrir a pasta
#: saber de onde veio aquele ficheiro.
MARCA = "# colado na secção Decks"


class SemCartas(ValueError):
    """O texto não tem uma única linha `<quantidade> <nome>`."""


class PrecisaConfirmar(ValueError):
    """Há linhas que o catálogo não conhece — ver `prever()` antes de gravar."""


class NomeOcupado(ValueError):
    """Já existe um deck com este slug e ninguém disse para o substituir."""


def _slug(texto: str) -> str:
    """Nome de ficheiro a partir do nome do deck.

    Sem acentos, sem espaços, sem nada que saia da pasta: isto vira um caminho
    em disco, e o nome vem de uma caixa de texto. Um nome que não deixe letra
    nenhuma dá `deck`.
    """
    s = unicodedata.normalize("NFKD", texto or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s[:60] or "deck"


def nome_e_slug(con: sqlite3.Connection, lido: dict) -> tuple[str, str]:
    """O rótulo e o slug de uma lista lida: o `Nome:` se ele o escreveu, senão
    a Legend (que é como o resto da app já chama um deck sem `Nome:`)."""
    legend = next((n for role, _, n in lido["lines"] if role == "legend"), None)
    nome = lido["nome"] or legend or "Deck"
    return nome, _slug(nome)


def prever(con: sqlite3.Connection, texto: str, slug: str | None = None) -> dict:
    """O que esta colagem ia gravar — e NÃO grava nada.

    Devolve as linhas por papel (cada uma a dizer se casou com o catálogo), as
    que não casaram, a aritmética por papel e se o slug já está ocupado. É o
    ecrã que ele vê antes de carregar em «Gravar».
    """
    if texto is None or len(texto) > MAX_TEXTO:
        raise ValueError(f"o texto vai além de {MAX_TEXTO} caracteres")
    lido = decks.parse_texto(texto)
    if not lido["lines"]:
        raise SemCartas(
            "não há nenhuma linha no formato «3 Nome da carta». Cola a lista "
            "com as secções («MainDeck:», «Sideboard:», …) como ela sai do "
            "sítio onde a construíste.")

    nome, auto = nome_e_slug(con, lido)
    slug = _slug(slug) if slug else auto

    linhas, nao_casaram = [], []
    por_papel: dict[str, dict] = {}
    for role, qty, raw in lido["lines"]:
        ck = decks.resolve(con, raw, role)
        info = None
        if ck is not None:
            r = con.execute(
                "SELECT card_key, name, type FROM catalog.cards WHERE card_key = ?",
                (ck,)).fetchone()
            if r is not None:
                info = {"card_key": r["card_key"], "name": r["name"], "type": r["type"]}
        linha = {"role": role, "qty": qty, "raw": raw, "casou": ck is not None,
                 **(info or {"card_key": None, "name": None, "type": None})}
        linhas.append(linha)
        if ck is None:
            nao_casaram.append({"role": role, "qty": qty, "raw": raw})
        bloco = por_papel.setdefault(role, {"copias": 0, "cartas": 0, "faltam_ler": 0})
        bloco["copias"] += qty
        bloco["cartas"] += 1
        if ck is None:
            bloco["faltam_ler"] += qty

    regras = decks.rules()
    return {
        "nome": nome, "slug": slug, "linhas": linhas,
        "nao_casaram": nao_casaram,
        # A aritmética, pela ordem dos papéis — é o que ele confere de relance
        # («39 no main + 1 Champion = 40»).
        "por_papel": [{"role": r, "label": decks.ROLE_LABEL.get(r, r), **por_papel[r]}
                      for r in decks.ROLE_ORDER if r in por_papel]
                     + [{"role": r, "label": r, **v} for r, v in por_papel.items()
                        if r not in decks.ROLE_ORDER],
        "totais": {"copias": sum(q for _, q, _ in lido["lines"]),
                   "linhas": len(lido["lines"]),
                   "nao_casaram": len(nao_casaram)},
        "regras": {"main": regras.get("main"), "runes": regras.get("runes"),
                   "battlefields": regras.get("battlefields"),
                   "main_includes_champion": regras.get("main_includes_champion")},
        # Gravar por cima de um deck que já existe é apagar a lista dele: só
        # com `substituir`.
        "ocupado": _ficheiro(con, slug).exists(),
        "content_hash": lido["content_hash"],
    }


def _ficheiro(con: sqlite3.Connection, slug: str) -> Path:
    return config.decks_dir(con) / f"{slug}.txt"


def gravar(con: sqlite3.Connection, texto: str, slug: str | None = None, *,
           confirmar: bool = False, substituir: bool = False) -> dict:
    """Grava a colagem como `.txt` na pasta de quem colou e reimporta.

    `confirmar` é preciso quando alguma linha não casou com o catálogo — a
    `prever()` já disse quais. `substituir` é preciso quando o slug já existe.
    Devolve a previsão (o que ficou gravado) e o `deck_id` do deck.
    """
    aviso = prever(con, texto, slug)
    if aviso["nao_casaram"] and not confirmar:
        raise PrecisaConfirmar(
            f"{len(aviso['nao_casaram'])} linha(s) não casaram com o catálogo "
            f"({', '.join(x['raw'] for x in aviso['nao_casaram'][:3])}"
            f"{', …' if len(aviso['nao_casaram']) > 3 else ''}). Confirma para "
            f"gravar sem elas, ou corrige os nomes.")
    destino = _ficheiro(con, aviso["slug"])
    if destino.exists() and not substituir:
        raise NomeOcupado(
            f"já existe um deck «{aviso['slug']}». Confirma a substituição "
            f"para gravar a lista nova por cima da que lá está.")

    # O `Nome:` vai escrito, mesmo quando saiu da Legend: é ele que faz o
    # rótulo do separador não mudar se um dia a Legend da lista mudar.
    corpo = texto.replace("\r\n", "\n").replace("\r", "\n").strip("\n")
    if not re.search(r"^\s*(?:nome|name)\s*:", corpo, re.IGNORECASE | re.MULTILINE):
        corpo = f"Nome: {aviso['nome']}\n\n{corpo}"
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(f"{MARCA}\n{corpo}\n", encoding="utf-8")

    # O deck nasce pela porta de sempre — a que lê os ficheiros.
    decks.import_all(con, log=lambda *_: None)
    row = con.execute("SELECT deck_id FROM decks WHERE name = ?",
                      (aviso["slug"],)).fetchone()
    return {**aviso, "gravado": True, "path": str(destino),
            "deck_id": row["deck_id"] if row else None}


def apagar(con: sqlite3.Connection, slug: str, *, confirmar: bool = False) -> dict:
    """Apaga a lista de um deck — o `.txt` e as linhas da base.

    É o par do `gravar`: quem pode meter uma lista pela janela tem de poder
    tirá-la por lá, senão a única saída é ir à pasta à mão, que é exactamente o
    que esta secção veio resolver. **Apagar a lista não apaga cópias** — as
    cópias próprias do deck ficam gravadas no `proprio:<slug>`, fora da
    Coleção, como já acontecia a um deck cujo ficheiro desaparecia.
    """
    destino = _ficheiro(con, _slug(slug))
    if not destino.exists():
        raise decks.DeckDesconhecido(f"não há nenhuma lista «{slug}»")
    if not confirmar:
        raise PrecisaConfirmar(f"apagar a lista «{slug}» — confirma")
    destino.unlink()
    decks.import_all(con, log=lambda *_: None)
    return {"apagado": True, "slug": _slug(slug)}

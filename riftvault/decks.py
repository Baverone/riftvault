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

QUE VERSÃO JOGA CADA LUGAR (2026-09-17)
    A Legend e o Champion jogam UMA versão especial — Alt Art, sobrenumerada
    ou promo, nunca assinada (`Versoes.especiais`). Os outros lugares jogam a
    base (`Versoes.normais`) e, desde a tarde desse dia, o que a base não
    tapar completa-se com OUTRA versão que ele tenha (`Versoes.outras_de` —
    as mesmas especiais, nunca assinada nem retirada): *"caso um deck precise
    de uma carta, que não há versão disponível em normal, mas esteja
    disponível em Alt Art ou outra, usa, mas no deck separa as versões por
    Art"*. Só depois disso é falta, e a falta aponta à base. O alvo da
    Coleção não sobe por isto (a alt art continua a pedir 1). A página do
    deck reparte cada linha pelas impressões que a servem (`versoes_em`).

AS RUNAS NÃO SE CONTAM (2026-09-17, à noite)
    *"esquece as runas, nao facas contagem de runas nos decks, indica me so
    quantas sao e eu organizo isso sozinho a mao"*. O Rune Pool lê-se e
    mostra-se com as quantidades da lista, e a legalidade continua a dizer
    «runas 12/12»; mas uma runa (`runas_especiais.tipos`) não entra no `need`
    — sem tenho/faltam, sem alocação, sem disputa, sem compra, sem euros, e o
    «tenho X de N» conta só o resto (`decks_index.wanted`, com `runas` ao
    lado). `decks.contar_runas: true` volta a contá-las. Ver
    `cartas_nao_contadas`.

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

    # O rasto do que cada lista pede (2026-09-17, «A mais»): só escreve quando
    # o pedido mudou, por isso continua a valer a regra de não tocar no
    # vault.db numa importação sem alterações.
    from . import uso_decks
    mudancas = uso_decks.registar(con)
    if mudancas:
        log(f"  (registo dos decks: {len(mudancas)} mudanças no que as listas pedem)")

    return {"decks": results, "removed": gone, "need_changes": mudancas}


# ---------------------------------------------------------------------------
# Alocação por prioridade
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# O que os decks JOGAM: a versão normal — menos a Legend e o Champion (2026-09-17)
# ---------------------------------------------------------------------------
#
# André, 2026-09-17 («vamos voltar atras»): *"as Alt Art, Overnumbered e SP
# voltam a 1 de cada, mesmo que joguem nos decks"* e *"os decks apenas jogaram
# versoes normais, com excepcao da Legend e do Champion que serao Alt Art ou
# Overnumbered ou SP, mas nunca assinada"*.
#
# Isto reverte o «o deck joga em Alt Art sempre que existir» de 2026-09-16
# (que punha o alvo da alt art a subir ao que os decks pediam e obrigava a
# «3 normais e 3 Alt Art»). A regra que vale:
#
#   1. O alvo da coleção extra é o do config (`master_set.um_de_cada`: 1 nas
#      sobrenumeradas e nas promos; as artes alternativas voltaram ao playset
#      a 2026-09-18), ponto final — nunca sobe por causa dos decks
#      (`metrics.alvo` deixou de receber a procura).
#   2. Os decks jogam a impressão NORMAL (a base, sem sobrenumeração), com
#      duas excepções — a Legend e o Champion —, que jogam UMA versão
#      especial: Alt Art, sobrenumerada ou promo, qualquer delas serve.
#   3. Nunca uma assinada. A signature não serve deck nenhum, para nada.
#   4. As runas em alt art continuam RETIRADAS (`metrics.retirada`, a mesma
#      manhã): uma runa não é Legend nem Champion e os decks jogam a base.
#
# O que o André NÃO disse, e como se resolveu (dúvidas assinaladas no
# relatório, decididas com o supervisor):
#   (a) um Champion que a lista jogue mais do que uma vez: só UMA cópia é
#       especial, as restantes são normais — é a única leitura compatível com
#       «1 de cada mesmo que joguem nos decks»;
#   (b) uma carta com várias versões especiais: qualquer uma serve; se ele
#       tem uma, está satisfeito; se não tem nenhuma, a falta aponta à mais
#       barata e as outras ficam em `alternativas`.
#   Sem versão especial nenhuma no catálogo, a Legend/Champion joga a base e
#   não há falta — não se inventa uma compra impossível.
#
# Uma pergunta, uma resposta: `Versoes` (o objecto) sabe, por carta, que
# impressões servem um lugar NORMAL e que impressões servem um lugar ESPECIAL;
# `versoes_dos_decks` constrói-o a partir do catálogo e do config
# (`decks.versoes_especiais`); `papeis_especiais` diz que papéis da lista
# jogam a especial (`decks.so_normais_excepto`). A alocação (`allocate`)
# serve os dois lugares separadamente — o especial primeiro — e devolve, a
# par do `missing` total, o `missing_especial`: a parte que se compra numa
# versão especial. É a maquinaria de 2026-09-17 de manhã (a alocação a
# consumir os montes POR IMPRESSÃO) reaproveitada; o que saiu foi o
# `procura_dos_decks` e o «só a alt art serve».
PAPEIS_ESPECIAIS = "so_normais_excepto"
LISTA_ESPECIAIS = "versoes_especiais"
KIND_SIGNATURE = "signature"
# AS RUNAS SAEM DA CONTAGEM DOS DECKS (André, 2026-09-17, à noite): *"esquece
# as runas, nao facas contagem de runas nos decks, indica me so quantas sao e
# eu organizo isso sozinho a mao"*. Com `decks.contar_runas: false` (o
# default) o Rune Pool continua a ler-se e a mostrar-se com as quantidades da
# lista, mas uma runa não entra em `need`: não se aloca, não se disputa, não
# falta, não se compra, não se propõe. O «tenho X de N» conta só o resto
# (`decks_index`, `wanted` sem as runas, `runas` ao lado). «Runa» é o
# `runas_especiais.tipos` — a mesma definição da Coleção, onde as runas base
# do OGN continuam a 3 e a contar. Isto fecha a tensão entre «as runas em Alt
# Art saem de tudo» (`metrics.retirada`, que fica) e «o deck usa a versão que
# eu tiver» (`Versoes.outras_de`, que fica para o que não é runa).
CONTAR_RUNAS = "contar_runas"
# O nome de cada versão na vista do deck (`Versoes.rotulo`); a sobrenumerada
# decide-se pelo número, não pela variante.
ROTULO_VERSAO = {"base": "normal", "alt_art": "Alt Art", "special": "promo",
                 "rune_promo": "runa promo", "token": "token"}


def _opcoes_decks(cfg: dict | None = None) -> dict:
    cfg = cfg or config.load()
    return cfg.get("decks") or {}


def contar_runas(cfg: dict | None = None) -> bool:
    """Os decks contam as runas? `False` desde 2026-09-17 à noite."""
    return bool(_opcoes_decks(cfg).get(CONTAR_RUNAS, False))


def cartas_nao_contadas(con: sqlite3.Connection, cfg: dict | None = None) -> frozenset[str]:
    """As cartas que os decks NÃO contam — as runas, com `contar_runas: false`.

    Uma carta daqui fica fora do `need` de todos os decks: a lista continua a
    pedi-la (e a página diz quantas), mas não há tenho/faltam, alocação,
    disputa nem compra. Sem «runa» (`runas_especiais.tipos` vazio) ou com
    `contar_runas: true` o conjunto é vazio e tudo conta como sempre.
    """
    from . import metrics

    cfg = cfg or config.load()
    if contar_runas(cfg):
        return frozenset()
    tipos = tuple(metrics.opcoes_runa(cfg).get("tipos") or ())
    if not tipos:
        return frozenset()
    ph = ",".join("?" * len(tipos))
    return frozenset(r["card_key"] for r in con.execute(
        f"SELECT card_key FROM catalog.cards WHERE type IN ({ph})", tipos))


def papeis_especiais(cfg: dict | None = None) -> frozenset[str]:
    """Os papéis da lista (`ROLE_ORDER`) que jogam uma versão especial — hoje
    `legend` e `champion`. Um papel desconhecido rebenta, como as listas do
    `master_set`: um erro de escrita não pode passar a «nenhum»."""
    papeis = frozenset(_opcoes_decks(cfg).get(PAPEIS_ESPECIAIS) or ())
    estranhos = papeis - set(ROLE_ORDER)
    if estranhos:
        raise ValueError(f"decks.{PAPEIS_ESPECIAIS}: papel desconhecido "
                         f"{sorted(estranhos)} (aceita {ROLE_ORDER})")
    return papeis


def kinds_especiais(cfg: dict | None = None) -> tuple[frozenset[str], bool]:
    """O `decks.versoes_especiais` lido: (variantes, as sobrenumeradas também?).

    A signature nunca pode estar aqui — *"nunca assinada"* é regra, não
    config — e escrevê-la rebenta em vez de passar em silêncio.
    """
    from . import metrics

    kinds, over = metrics._ler_lista(f"decks.{LISTA_ESPECIAIS}",
                                     tuple(_opcoes_decks(cfg).get(LISTA_ESPECIAIS) or ()))
    if KIND_SIGNATURE in kinds:
        raise ValueError(f"decks.{LISTA_ESPECIAIS}: uma assinada nunca serve um "
                         f"deck (André, 2026-09-17: 'nunca assinada')")
    return kinds, over


class Versoes:
    """Que impressões servem os decks, por carta e por lugar.

    `normais[ck]` são as impressões que servem um lugar normal (a base, sem
    sobrenumeração — pela ordem do catálogo, edição mais antiga primeiro);
    `especiais[ck]` as que servem o lugar da Legend/Champion (alt art,
    sobrenumerada, promo — a mais barata primeiro, que é a que se compra).
    Uma signature ou uma retirada não está em lado nenhum. Uma carta sem
    impressão normal nenhuma (não acontece no catálogo de hoje) serve-se de
    qualquer não-assinada, para o deck nunca ficar impossível de montar.

    Desde 2026-09-17 (tarde) as `especiais` são também as OUTRAS que tapam um
    lugar normal quando a base não chega (`outras_de`): *"caso um deck precise
    de uma carta, que não há versão disponível em normal, mas esteja
    disponível em Alt Art ou outra, usa"*. É a mesma lista — o que serve a
    Legend serve um buraco do main —, só o LUGAR é outro, e a falta que sobrar
    compra-se sempre na base (`compra`).
    """

    def __init__(self, normais: dict[str, list[str]], especiais: dict[str, list[str]],
                 retiradas=(), papeis=(), linha_de: dict | None = None):
        self.normais = normais
        self.especiais = especiais
        self.retiradas = frozenset(retiradas)
        self.papeis = frozenset(papeis)
        # printing_id -> linha do catálogo (código, edição, preço), para quem
        # mostra a versão escolhida sem voltar à base de dados.
        self.linha_de = linha_de or {}

    def retirada(self, printing) -> bool:
        from . import metrics

        return metrics.campo(printing, "printing_id") in self.retiradas

    def tem_especial(self, ck: str) -> bool:
        return bool(self.especiais.get(ck))

    def normais_de(self, ck: str) -> list[str]:
        return self.normais.get(ck, [])

    def especiais_de(self, ck: str) -> list[str]:
        return self.especiais.get(ck, [])

    def outras_de(self, ck: str) -> list[str]:
        """As impressões que tapam um lugar NORMAL quando a base não chega: as
        mesmas versões especiais (alt art, sobrenumerada, promo), pela mesma
        ordem — a mais barata primeiro, para a mais cara ficar na Coleção."""
        return self.especiais_de(ck)

    def rotulo(self, pid: str | None) -> str:
        """Como a vista do deck chama a esta versão: «normal», «Alt Art»,
        «sobrenumerada», «promo» — as palavras dele."""
        from . import metrics

        r = self.linha_de.get(pid) if pid else None
        if r is None:
            return "?"
        if metrics.e_overnumbered(r):
            return "sobrenumerada"
        return ROTULO_VERSAO.get(r["variant_kind"], r["variant_kind"])

    def joga(self, printing, especial: bool = False) -> bool:
        """Esta impressão serve um lugar do deck — normal, ou o especial?"""
        pid = printing["printing_id"]
        ck = printing["card_key"]
        lista = self.especiais if especial else self.normais
        return pid in lista.get(ck, ())

    def serve(self, printing) -> bool:
        """Serve algum lugar de algum deck? (o «conta para os decks» cru)"""
        return self.joga(printing) or self.joga(printing, especial=True)

    def compra(self, ck: str, especial: bool = False) -> str | None:
        """A impressão em que se COMPRA o que falta a esta carta: a normal
        mais barata, ou — no lugar especial — a versão especial mais barata."""
        lista = self.especiais_de(ck) if especial else self.normais_de(ck)
        if not lista:
            return None
        if especial:
            return lista[0]
        return min(lista, key=lambda pid: self._preco_rank(pid))

    def _preco_rank(self, pid: str) -> tuple:
        r = self.linha_de.get(pid)
        preco = r["price_cents"] if r is not None else None
        return (preco is None, preco if preco is not None else 0,
                config.set_order(r["set_id"]) if r is not None else 999, pid)

    def info(self, pid: str | None) -> dict:
        r = self.linha_de.get(pid) if pid else None
        if r is None:
            return {"id": pid, "code": None, "set": None, "price": None, "kind": None}
        return {"id": pid, "code": r["public_code"], "set": r["set_id"],
                "price": r["price_cents"], "kind": r["variant_kind"]}

    def alternativas(self, ck: str) -> list[dict]:
        """As versões especiais desta carta, da mais barata para a mais cara —
        o que o relatório e a linha da falta mostram como alternativa."""
        return [self.info(pid) for pid in self.especiais_de(ck)]


def versoes_dos_decks(con: sqlite3.Connection, cfg: dict | None = None) -> Versoes:
    """Constrói o `Versoes` a partir do catálogo e do config.

    Normal = `variant_kind == "base"` e NÃO sobrenumerada (uma «300/298» é
    uma reimpressão de topo, que ele chama OverNumbered — versão especial).
    Especial = o que `decks.versoes_especiais` disser (alt art, sobrenumerada,
    promo). Signature e retiradas ficam de fora das duas listas.
    """
    from . import metrics

    cfg = cfg or config.load()
    retiradas = metrics.retiradas_ids(con, cfg)
    kinds, over = kinds_especiais(cfg)
    ordens = {s: config.set_order(s) for s in
              (r["set_id"] for r in con.execute(
                  "SELECT DISTINCT set_id FROM catalog.printings"))}
    linhas = con.execute(
        "SELECT p.printing_id, p.card_key, p.variant_kind, p.set_id, p.api_sort, "
        "       p.public_code, p.collector_number, pl.price_cents "
        "FROM catalog.printings p "
        "LEFT JOIN catalog.price_latest pl ON pl.printing_id = p.printing_id").fetchall()
    linha_de = {r["printing_id"]: r for r in linhas}
    normais: dict[str, list] = {}
    especiais: dict[str, list] = {}
    restantes: dict[str, list] = {}
    for r in linhas:
        if r["printing_id"] in retiradas or r["variant_kind"] == KIND_SIGNATURE:
            continue
        over_esta = metrics.e_overnumbered(r)
        if r["variant_kind"] in kinds or (over and over_esta):
            especiais.setdefault(r["card_key"], []).append(r)
        elif r["variant_kind"] == "base" and not over_esta:
            normais.setdefault(r["card_key"], []).append(r)
        else:
            restantes.setdefault(r["card_key"], []).append(r)
    # Sem impressão normal nenhuma, o lugar normal aceita o que houver de
    # não-assinado (as promo de runa `VEN-R`, por exemplo): um deck nunca pede
    # uma compra impossível.
    for ck, rs in restantes.items():
        if ck not in normais:
            normais[ck] = rs
    por_catalogo = lambda r: (ordens.get(r["set_id"], 999), r["api_sort"])
    por_preco = lambda r: (r["price_cents"] is None,
                           r["price_cents"] if r["price_cents"] is not None else 0,
                           ordens.get(r["set_id"], 999), r["api_sort"])
    return Versoes(
        {ck: [r["printing_id"] for r in sorted(rs, key=por_catalogo)]
         for ck, rs in normais.items()},
        {ck: [r["printing_id"] for r in sorted(rs, key=por_preco)]
         for ck, rs in especiais.items()},
        retiradas, papeis_especiais(cfg), linha_de)


def cartas_especiais(con: sqlite3.Connection, deck_id: int,
                     papeis=None) -> set[str]:
    """As cartas que ESTE deck joga numa versão especial: as das linhas cujo
    papel está em `decks.so_normais_excepto` (a Legend e o Champion)."""
    if papeis is None:
        papeis = papeis_especiais()
    if not papeis:
        return set()
    ph = ",".join("?" * len(papeis))
    return {r["card_key"] for r in con.execute(
        f"SELECT DISTINCT card_key FROM deck_cards WHERE deck_id = ? AND role IN ({ph})",
        (deck_id, *sorted(papeis)))}


def owned_by_card(con: sqlite3.Connection) -> dict[str, int]:
    """card_key -> cópias que podem SERVIR OS DECKS, de todos os locais.

    Conta as impressões que servem algum lugar — normal ou especial
    (`Versoes.serve`); nunca uma signature nem uma retirada. É informação
    (o `riftvault stats --usadas`); quem decide o que falta é a alocação,
    porque uma base nunca serve o lugar especial. O «quantas destas
    cartas tenho ao todo» (o playset jogável, o `have_base` do Pimp) é o
    `metrics.owned_by_card`, que soma tudo menos as retiradas.
    """
    versoes = versoes_dos_decks(con)
    # As runas não se contam nos decks (2026-09-17, à noite).
    nao_contadas = cartas_nao_contadas(con)
    out: dict[str, int] = {}
    for r in con.execute(
        "SELECT p.printing_id, p.card_key, c.qty FROM copies c "
        "JOIN catalog.printings p ON p.printing_id = c.printing_id WHERE c.qty > 0"
    ):
        if versoes.serve(r) and r["card_key"] not in nao_contadas:
            out[r["card_key"]] = out.get(r["card_key"], 0) + r["qty"]
    return out


def pool_dos_decks(con: sqlite3.Connection) -> dict:
    """Os três montes de onde um deck se monta, POR IMPRESSÃO.

      `fixo[slug][printing_id]` — o que já está sleevado NAQUELE deck. Não
                                  anda: é daquele deck e de mais nenhum.
      `binder[printing_id]`     — o binder Decks/Venda, o stock livre dos decks.
      `colecao[printing_id]`    — os binders de coleção.

    Os dois últimos distribuem-se por prioridade, o binder primeiro. **A Coleção
    entra desde 2026-09-11** — *"se há na coleção o deck usa"* —; entre
    2026-09-10 e essa data não entrava, e o que lá estava aparecia como
    «duplicado a comprar ou a decidir». A cópia continua a contar para a
    percentagem de master set: é a mesma cópia a servir as duas coisas, que é o
    que ele pediu.

    Até 2026-09-17 os montes vinham somados por carta lógica, já filtrados
    pelo que os decks jogam. Passaram a vir por impressão, crus: é o
    `allocate` que escolhe de que impressões cada lugar se serve
    (`Versoes.joga`), e uma impressão retirada ou assinada fica no monte sem
    ninguém a levar.
    """
    from . import locais

    return {
        "fixo": {slug: dict(mapa) for slug, mapa in locais.por_deck(con).items()},
        "binder": dict(locais.em(con, locais.BINDER)),
        "colecao": dict(locais.na_colecao(con)),
    }


def owned_printings(con: sqlite3.Connection,
                    locais_ok: set[str] | None = None) -> dict[str, list[dict]]:
    """card_key -> impressões que tenho, para saber quais tirar da caixa.

    `locais_ok` limita a resposta a locais concretos (ex.: só o deck e o binder
    Decks/Venda). Sem ele são as cópias todas, esteja onde estiverem.
    """
    from . import locais as locais_mod

    onde = locais_mod.por_local(con) if locais_ok is not None else {}
    versoes = versoes_dos_decks(con)
    out: dict[str, list[dict]] = {}
    for r in con.execute(
        "SELECT p.card_key, p.card_key AS k, p.printing_id, p.public_code, p.set_id, "
        "       p.variant_kind, p.variant_label, c.qty "
        "FROM copies c JOIN catalog.printings p ON p.printing_id = c.printing_id "
        "WHERE c.qty > 0 ORDER BY p.set_id, p.api_sort"
    ):
        # Uma assinada ou uma retirada não é uma cópia que o deck use.
        if not versoes.serve(r):
            continue
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
    """As impressões concretas de um monte da alocação (`no_binder` /
    `na_colecao`) que cada grupo levou.

    Desde 2026-09-17 a alocação consome os montes por impressão e regista o
    que tirou (`grupo.impressoes`), por isso aqui só se lê — `livre` fica na
    assinatura por quem já chamava assim. Pelo GRUPO, lido no líder: dois
    decks com a mesma Legend levam as mesmas cópias, e contá-las uma vez por
    membro punha a Venda a proteger o dobro.
    """
    alloc = allocate(con)
    out: dict[str, list[dict]] = {}
    for d in deck_rows(con):
        a = alloc[d["deck_id"]]
        if not a["grupo"]["lider"]:
            continue
        for pid, n in a["grupo"]["impressoes"].get(monte, {}).items():
            out.setdefault(pid, []).append(
                {"deck": a["grupo"]["rotulo"], "slug": d["name"], "qty": n,
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


def _need(con: sqlite3.Connection, deck_id: int,
          fora: frozenset[str] = frozenset()) -> dict[str, int]:
    """card_key -> quanto ESTE deck pede, todos os papéis somados.

    `fora` são as cartas que não se contam (`cartas_nao_contadas` — as
    runas): a lista pede-as, a contabilidade não as vê.
    """
    return {r["card_key"]: r["q"] for r in con.execute(
        "SELECT card_key, SUM(qty) AS q FROM deck_cards WHERE deck_id = ? "
        "GROUP BY card_key", (deck_id,)) if r["card_key"] not in fora}


def _cortar(entradas: list[dict], inicio: int, n: int) -> list[dict]:
    """As `n` cópias de `entradas` a partir da posição `inicio`, entrada a
    entrada, com a `qty` cortada — para repartir por papéis uma lista que a
    alocação fez por carta."""
    out: list[dict] = []
    pos = 0
    alvo = inicio + n
    for e in entradas:
        if pos >= alvo:
            break
        fim = pos + e["qty"]
        q = min(fim, alvo) - max(pos, inicio)
        if q > 0:
            out.append({**e, "qty": q})
        pos = fim
    return out


def _fatiar(servidas: list[dict], take_e: int, take_n: int) -> list[dict]:
    """A parte de `servidas` (as impressões que serviram uma carta ao grupo,
    por lugar) que cabe a UM membro: `take_e` do lugar especial e `take_n` do
    resto (normais primeiro, outras depois), pela ordem em que se serviram."""
    esp = [x for x in servidas if x["lugar"] == "especial"]
    resto = [x for x in servidas if x["lugar"] != "especial"]
    return _cortar(esp, 0, take_e) + _cortar(resto, 0, take_n)


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

    # Os montes vêm POR IMPRESSÃO (2026-09-17) e cada grupo serve-se só das
    # impressões que a regra lhe dá (`Versoes.joga`): as normais nos lugares
    # normais, uma especial no lugar da Legend/Champion; nunca uma assinada
    # nem uma retirada (ficam no monte e ninguém as leva).
    p = pool_dos_decks(con)
    versoes = versoes_dos_decks(con)
    linha_de = versoes.linha_de
    # As runas não se contam (2026-09-17, à noite): ficam fora do `need` e por
    # isso de tudo o que se segue — nem se alocam nem faltam.
    nao_contadas = cartas_nao_contadas(con)
    binder = dict(p["binder"])
    colecao = dict(p["colecao"])
    # O pendente por impressão; as `market_only` (sem linha no catálogo — as
    # runas do SFD que a RiftScribe não tem) contam por carta, para qualquer
    # deck, como sempre contaram.
    caminho = dict(pending.open_qty(con))
    caminho_fora: dict[str, int] = {}
    for r in con.execute(
        "SELECT m.card_key AS k, SUM(pe.qty) AS q FROM pending pe "
        "JOIN catalog.market_only m ON m.printing_id = pe.printing_id "
        "WHERE pe.arrived_at IS NULL AND m.card_key IS NOT NULL GROUP BY m.card_key"
    ):
        caminho_fora[r["k"]] = caminho_fora.get(r["k"], 0) + r["q"]
    por_id = {d["deck_id"]: d for d in deck_rows(con)}
    held: dict[str, list[dict]] = {}     # card_key -> grupos que já a levaram
    out = {}

    def tirar(monte: dict[str, int], pids: list[str], qty: int,
              *registos: dict[str, int] | None) -> int:
        """Tira até `qty` de `monte` pelas impressões `pids`, por ordem, e diz
        quanto tirou; cada `registo` guarda de que impressões."""
        tirado = 0
        for pid in pids:
            if tirado >= qty:
                break
            n = min(qty - tirado, monte.get(pid, 0))
            if n > 0:
                monte[pid] -= n
                tirado += n
                for registo in registos:
                    if registo is not None:
                        registo[pid] = registo.get(pid, 0) + n
        return tirado

    for g in grupos(con):
        membros = [por_id[i] for i in g["deck_ids"]]
        needs = {d["deck_id"]: _need(con, d["deck_id"], nao_contadas) for d in membros}
        # A procura do grupo: o MÁXIMO entre as listas, carta a carta. A
        # alocação é por carta lógica, não por papel: uma carta que esteja no
        # main e no sideboard disputa o mesmo stock.
        need: dict[str, int] = {}
        for nd in needs.values():
            for ck, q in nd.items():
                need[ck] = max(need.get(ck, 0), q)
        # As cartas que algum membro joga numa versão especial (a Legend e o
        # Champion) — e só as que TÊM versão especial no catálogo: sem ela a
        # carta joga-se na base e não há falta a inventar.
        especiais_de = {d["deck_id"]: cartas_especiais(con, d["deck_id"], versoes.papeis)
                        for d in membros}
        need_especial = {ck: 1 for ck in set().union(*especiais_de.values())
                         if ck in need and versoes.tem_especial(ck)}
        # O que está sleevado em qualquer dos membros é do grupo: é o mesmo
        # deck físico com duas listas.
        fixo: dict[str, int] = {}
        for d in membros:
            for pid, n in (p["fixo"].get(d["name"]) or {}).items():
                fixo[pid] = fixo.get(pid, 0) + n

        alloc, no_deck, no_binder, na_colecao, a_caminho = {}, {}, {}, {}, {}
        shared, missing = {}, {}
        alloc_especial, a_caminho_especial, missing_especial, especial_em = {}, {}, {}, {}
        alloc_outras, versoes_em = {}, {}
        impressoes = {"no_deck": {}, "no_binder": {}, "na_colecao": {}}

        def servir(pids: list[str], qty: int, reg: dict | None = None,
                   reg_cam: dict | None = None) -> tuple:
            """Serve `qty` cópias pelas impressões `pids`, pela ordem dos montes
            (deck, binder, Coleção) e depois pelo que vem a caminho. Devolve
            (do_deck, do_binder, da_colecao, encomendada); `reg` guarda de que
            impressões saíram as cópias físicas, `reg_cam` as que vêm a caminho."""
            dd = tirar(fixo, pids, qty, impressoes["no_deck"], reg)
            db = tirar(binder, pids, qty - dd, impressoes["no_binder"], reg)
            dc = tirar(colecao, pids, qty - dd - db, impressoes["na_colecao"], reg)
            # O que vem a caminho serve o primeiro grupo que ainda a peça — é
            # uma cópia da Coleção como as outras, só que ainda não chegou.
            # Fica fora do `alloc`: o deck não a TEM, só já não a compra.
            enc = tirar(caminho, pids, qty - dd - db - dc, reg_cam)
            return dd, db, dc, enc

        for ck, qty in need.items():
            # As impressões que ficaram a servir esta carta, pela ordem em que
            # se serviram: [{id, qty, lugar}], com `lugar` em `especial`
            # (a Legend/Champion), `normal` (a base) ou `outra` (uma versão
            # que tapou um buraco de base). É o que a página do deck reparte.
            servidas: list[dict] = []

            def anotar(reg: dict[str, int], lugar: str) -> None:
                for pid, n in reg.items():
                    servidas.append({"id": pid, "qty": n, "lugar": lugar})

            # O lugar ESPECIAL primeiro (a Legend/Champion): uma cópia, de
            # qualquer versão especial — a que ele tiver serve.
            n_esp = min(need_especial.get(ck, 0), qty)
            e_deck = e_binder = e_col = e_enc = 0
            if n_esp:
                pids_e = versoes.especiais_de(ck)
                reg_e: dict[str, int] = {}
                reg_e_cam: dict[str, int] = {}
                e_deck, e_binder, e_col, e_enc = servir(pids_e, n_esp, reg_e, reg_e_cam)
                anotar(reg_e, "especial")
                # Que versão especial ficou a servir: a que saiu dos montes ou
                # a que vem a caminho — para a página do deck dizer qual é.
                usada = list(reg_e) + list(reg_e_cam)
                if usada:
                    especial_em[ck] = usada[0]
                if e_deck + e_binder + e_col:
                    alloc_especial[ck] = e_deck + e_binder + e_col
                if e_enc:
                    a_caminho_especial[ck] = e_enc
                falta_e = n_esp - e_deck - e_binder - e_col - e_enc
                if falta_e:
                    missing_especial[ck] = falta_e

            # Os lugares NORMAIS: a base primeiro...
            reg_n: dict[str, int] = {}
            pids = versoes.normais_de(ck)
            do_deck, do_binder, da_colecao, encomendada = servir(pids, qty - n_esp, reg_n)
            anotar(reg_n, "normal")
            # ...e o que a base não tapar, com OUTRAS impressões que ele tenha
            # — Alt Art, sobrenumerada, promo; nunca assinada nem retirada
            # (André, 2026-09-17: *"caso um deck precise de uma carta, que não
            # há versão disponível em normal, mas esteja disponível em Alt Art
            # ou outra, usa"*). Só depois disto é que há falta a comprar, e a
            # falta continua a apontar à base. O alvo da Coleção não sabe
            # disto: a alt art continua a pedir 1, jogue ou não.
            resto = qty - n_esp - do_deck - do_binder - da_colecao - encomendada
            if resto > 0:
                reg_o: dict[str, int] = {}
                o_deck, o_binder, o_col, o_enc = servir(versoes.outras_de(ck), resto, reg_o)
                anotar(reg_o, "outra")
                if o_deck + o_binder + o_col:
                    alloc_outras[ck] = o_deck + o_binder + o_col
                do_deck += o_deck
                do_binder += o_binder
                da_colecao += o_col
                encomendada += o_enc
            if servidas:
                versoes_em[ck] = servidas
            do_deck += e_deck
            do_binder += e_binder
            da_colecao += e_col
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

            # As `market_only` a caminho contam por carta, só no lugar normal.
            encomendada += e_enc
            fora = min(qty - take - encomendada, caminho_fora.get(ck, 0))
            caminho_fora[ck] = caminho_fora.get(ck, 0) - fora
            encomendada += fora
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

        # O lugar especial vai à parte (`*_especial`): é a parte do `alloc`,
        # do `a_caminho` e do `missing` — que continuam a ser os totais — que
        # é a Legend/Champion numa versão especial. `especial_em` diz que
        # impressão ficou a servir esse lugar (ou vem a caminho para ele).
        # `alloc_outras` é a parte do `alloc` que tapou um lugar normal com
        # outra versão (2026-09-17, tarde), e `versoes_em` reparte o `alloc`
        # inteiro por impressão, para a vista do deck separar as artes.
        resultado = {"alloc": alloc, "no_deck": no_deck, "no_binder": no_binder,
                     "na_colecao": na_colecao, "a_caminho": a_caminho,
                     "missing": missing, "shared": shared, "need": need,
                     "impressoes": impressoes,
                     "need_especial": need_especial, "alloc_especial": alloc_especial,
                     "a_caminho_especial": a_caminho_especial,
                     "missing_especial": missing_especial, "especial_em": especial_em,
                     "alloc_outras": alloc_outras, "versoes_em": versoes_em}

        # Espalha-se pelos membros, cortado ao que CADA lista pede. As fontes
        # repartem-se pela mesma ordem (deck, binder, Coleção); o `missing` de
        # um membro é o máximo que o grupo ainda compra para aquela carta, e
        # por isso igual nos dois quando pedem a mesma quantidade. O lugar
        # especial só é do membro cuja lista o tem nesse papel.
        for d in membros:
            nd = needs[d["deck_id"]]
            m_alloc, m_deck, m_binder, m_col, m_cam, m_miss, m_shared = {}, {}, {}, {}, {}, {}, {}
            m_need_e, m_alloc_e, m_cam_e, m_miss_e = {}, {}, {}, {}
            m_alloc_o, m_versoes = {}, {}
            partilhada: dict[str, list[dict]] = {}
            for ck, qty in nd.items():
                n_esp = min(qty, need_especial.get(ck, 0)) if ck in especiais_de[d["deck_id"]] else 0
                if n_esp:
                    m_need_e[ck] = n_esp
                take_e = min(n_esp, alloc_especial.get(ck, 0))
                enc_e = min(n_esp - take_e, a_caminho_especial.get(ck, 0))
                falta_e = n_esp - take_e - enc_e
                resto = qty - n_esp
                take_n = min(resto, alloc.get(ck, 0) - alloc_especial.get(ck, 0))
                enc_n = min(resto - take_n, a_caminho.get(ck, 0) - a_caminho_especial.get(ck, 0))
                take = take_e + take_n
                enc = enc_e + enc_n
                dd = min(take, no_deck.get(ck, 0))
                db = min(take - dd, no_binder.get(ck, 0))
                dc = take - dd - db
                falta = qty - take - enc
                if take_e:
                    m_alloc_e[ck] = take_e
                if enc_e:
                    m_cam_e[ck] = enc_e
                if falta_e:
                    m_miss_e[ck] = falta_e
                # As impressões deste membro: as especiais cortadas ao lugar
                # especial dele, e as normais + outras cortadas ao resto — a
                # base serve-se primeiro, por isso as «outras» são as últimas
                # a entrar e as primeiras a sair quando a lista pede menos.
                fatias = _fatiar(versoes_em.get(ck, []), take_e, take_n)
                if fatias:
                    m_versoes[ck] = fatias
                outras = sum(x["qty"] for x in fatias if x["lugar"] == "outra")
                if outras:
                    m_alloc_o[ck] = outras
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
            proprio: dict[str, int] = {}
            for pid, n in (p["fixo"].get(d["name"]) or {}).items():
                r = linha_de.get(pid)
                # Uma runa sleevada no deck não é «a mais»: a lista pede-a, só
                # não se conta.
                if r is not None and versoes.serve(r) and r["card_key"] not in nao_contadas:
                    proprio[r["card_key"]] = proprio.get(r["card_key"], 0) + n
            sobra = {ck: n - min(n, nd.get(ck, 0)) for ck, n in proprio.items()
                     if n - min(n, nd.get(ck, 0)) > 0}
            out[d["deck_id"]] = {
                "alloc": m_alloc, "no_deck": m_deck, "no_binder": m_binder,
                "na_colecao": m_col, "a_caminho": m_cam, "missing": m_miss,
                "shared": m_shared, "extra": sobra, "partilhada": partilhada,
                "need_especial": m_need_e, "alloc_especial": m_alloc_e,
                "a_caminho_especial": m_cam_e, "missing_especial": m_miss_e,
                "especial_em": {ck: especial_em[ck] for ck in m_need_e if ck in especial_em},
                "alloc_outras": m_alloc_o, "versoes_em": m_versoes,
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
    fora = cartas_nao_contadas(con)
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
            for ck in _need(con, i, fora):
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
    # Ao preço da impressão em que se compra (`Versoes.compra`): a normal
    # mais barata, e a versão especial mais barata no lugar da Legend/Champion.
    versoes = versoes_dos_decks(con)
    barato = preco_de_compra(versoes)
    cartas: set[str] = set()
    copias = cents = disputadas = encomendadas = 0
    # Quantas das cópias em falta são a versão ESPECIAL da Legend/Champion —
    # o número que se quer ver à parte (2026-09-17).
    esp_cartas: set[str] = set()
    esp_copias = esp_cents = 0
    # E quantos lugares normais estão tapados por outra versão que ele tem —
    # faltas que deixaram de o ser a 2026-09-17 (tarde).
    outras_cartas: set[str] = set()
    outras_copias = 0
    for a in alloc.values():
        for ck, n in a["missing"].items():
            cartas.add(ck)
            copias += n
            n_esp = min(n, a["missing_especial"].get(ck, 0))
            cents += (barato(ck) or 0) * (n - n_esp)
            if n_esp:
                esp_cartas.add(ck)
                esp_copias += n_esp
                esp_cents += (barato(ck, especial=True) or 0) * n_esp
        for ck, n in a["alloc_outras"].items():
            outras_cartas.add(ck)
            outras_copias += n
        disputadas += sum(v["qty"] for v in a["shared"].values())
        encomendadas += sum(a["a_caminho"].values())
    cents += esp_cents
    return {"cards": len(cartas), "copies": copias, "cents": cents,
            "disputed": disputadas, "ordered": encomendadas,
            "especiais": {"cards": len(esp_cartas), "copies": esp_copias,
                          "cents": esp_cents},
            "outras": {"cards": len(outras_cartas), "copies": outras_copias}}


def preco_de_compra(versoes: Versoes):
    """`(card_key, especial) -> cêntimos` da impressão mais barata em que um
    deck compra a carta nesse lugar (`Versoes.compra`); `None` sem preço."""

    def preco(ck: str, especial: bool = False) -> int | None:
        return versoes.info(versoes.compra(ck, especial))["price"]

    return preco


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
    lado = a["grupo"] if grupo else a
    falta = lado["missing"]
    falta_esp = lado["missing_especial"]
    if ignore_types:
        tipos = {r["card_key"]: r["type"] for r in con.execute(
            "SELECT card_key, type FROM catalog.cards")}
        falta = {k: v for k, v in falta.items() if tipos.get(k) not in ignore_types}
    if not falta:
        return []

    nomes = {r["card_key"]: r["name"] for r in con.execute(
        "SELECT card_key, name FROM catalog.cards")}
    versoes = versoes_dos_decks(con)
    # A impressão em que se compra (`Versoes.compra`): a normal mais barata
    # nos lugares normais e, para a Legend/Champion, a versão especial mais
    # barata — numa LINHA PRÓPRIA, marcada `especial`, com as outras versões
    # especiais em `alternativas` (2026-09-17). Uma carta pode dar duas
    # linhas: «2× base» e «1× alt art».
    imagens = {r["printing_id"]: r for r in con.execute(
        "SELECT printing_id, orientation, image_medium, image_large, image_url "
        "FROM catalog.printings")}

    def linha(ck: str, n: int, especial: bool) -> dict | None:
        pid = versoes.compra(ck, especial)
        if pid is None:
            return None
        i = versoes.info(pid)
        r = imagens[pid]
        sets = {versoes.info(p)["set"] for p in
                (versoes.especiais_de(ck) if especial else versoes.normais_de(ck))}
        return {
            "card_key": ck, "name": nomes.get(ck, ck), "qty": n,
            "set": i["set"], "code": i["code"], "price": i["price"],
            "total": (i["price"] or 0) * n,
            "img": f"img/{pid}.webp",
            "cdn": r["image_medium"] or r["image_large"] or r["image_url"],
            "landscape": (r["orientation"] or "").lower() == "landscape",
            "especial": especial,
            "alternativas": [x for x in versoes.alternativas(ck) if x["id"] != pid]
            if especial else [],
            # Existe noutras edições — dá para a ires buscar a outro lado.
            "also": sorted(sets - {i["set"]}),
            "multi": len(sets) > 1,
        }

    por_set: dict[str, dict] = {}
    for ck, n in falta.items():
        n_esp = min(n, falta_esp.get(ck, 0))
        for it in (linha(ck, n_esp, True) if n_esp else None,
                   linha(ck, n - n_esp, False) if n - n_esp else None):
            if it is None:
                continue
            d = por_set.setdefault(it["set"], {"set": it["set"], "cards": 0,
                                               "copies": 0, "cents": 0, "multi": 0,
                                               "items": []})
            d["cards"] += 1
            d["copies"] += it["qty"]
            d["cents"] += it["total"]
            if it.pop("multi"):
                d["multi"] += 1
            d["items"].append(it)

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
    fora = cartas_nao_contadas(con)
    out = []
    for d in deck_rows(con):
        a = alloc[d["deck_id"]]
        # O «tenho X de N» conta só o que se conta: as runas saem do `wanted`
        # (2026-09-17, à noite) e vão à parte em `runas`, só como quantidade —
        # 54 de 54 num deck de 66, e «12 runas» ao lado. O denominador desce
        # de propósito: deixar o 66 dizia que faltavam 12.
        pedidas = runas = 0
        for r in con.execute(
            "SELECT card_key, SUM(qty) AS q FROM deck_cards WHERE deck_id = ? "
            "GROUP BY card_key", (d["deck_id"],)
        ):
            if r["card_key"] in fora:
                runas += r["q"]
            else:
                pedidas += r["q"]
        n_runas = sum(1 for ck in _need(con, d["deck_id"]) if ck in fora)
        tenho = sum(a["alloc"].values())
        out.append({
            "id": d["deck_id"], "slug": d["name"],
            "name": d["display_name"] or d["name"],
            "legend": d["legend"], "champion": d["champion"],
            "priority": d["priority"],
            "wanted": pedidas, "have": tenho,
            # As runas que a lista pede e NÃO se contam: cópias e cartas
            # distintas, para o ecrã dizer «12 runas (3 cartas), à mão».
            "runas": {"copies": runas, "cards": n_runas, "contadas": not fora},
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
            # O lugar da Legend/Champion numa versão especial (2026-09-17):
            # quantos pede, quantos tem, quantos vêm a caminho, quantos compra.
            "especial": {
                "wanted": sum(a["need_especial"].values()),
                "have": sum(a["alloc_especial"].values()),
                "ordered": sum(a["a_caminho_especial"].values()),
                "missing": sum(a["missing_especial"].values()),
            },
            # Lugares normais tapados por OUTRA versão (2026-09-17, tarde):
            # cópias que ele tem e que, sem esta regra, eram falta.
            "outras": sum(a["alloc_outras"].values()),
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
                "ordered": sum(a["grupo"]["a_caminho"].values()),
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
    # A impressão em que o `+` de cada linha grava a encomenda (a normal mais
    # barata; na Legend/Champion a versão especial mais barata), para o ecrã
    # dizer qual é antes de ele carregar.
    chaves = [r["card_key"] for r in con.execute(
        "SELECT DISTINCT card_key FROM deck_cards WHERE deck_id = ?", (deck_id,))]
    encomendar_em = pending.impressao_para_encomendar(con, chaves)
    encomendar_esp = pending.impressao_para_encomendar(con, list(a["need_especial"]),
                                                       especial=True)
    versoes = versoes_dos_decks(con)
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
    # O lugar especial (a Legend e o Champion, 2026-09-17) serve-se primeiro:
    # as linhas desses papéis vêm antes no `ROLE_ORDER`, e é UMA cópia por
    # carta — a segunda cópia de um Champion, no main, já é normal.
    usado_esp: dict[str, int] = {}
    usado_cam_esp: dict[str, int] = {}
    # As runas não se contam (2026-09-17, à noite): a linha fica na lista com
    # a quantidade que a lista pede — «indica me so quantas sao» — e mais
    # nada: sem tenho, sem falta, sem a caminho, sem preço, sem versões.
    fora = cartas_nao_contadas(con)
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
            if ck in fora:
                info = names.get(ck) or {}
                cards.append({
                    "card_key": ck,
                    "name": (info["name"] if info else r["raw_line"]),
                    "raw": r["raw_line"],
                    "type": info["type"] if info else None,
                    "wanted": r["qty"], "have": 0, "missing": 0, "ordered": 0,
                    "no_deck": 0, "no_binder": 0, "na_colecao": 0,
                    "contado": False,
                    "especial": None, "versoes": [], "outras": 0,
                    "order_code": None, "order_price": None, "order_especial": False,
                    "shared": None, "partilhada": None, "printings": [],
                    **{**imagem(ck), "price": None},
                })
                continue
            # Esta linha é o lugar especial? Só nos papéis do config, só se a
            # carta tiver versão especial, e só a primeira cópia.
            n_esp = 0
            if role in versoes.papeis and ck in a["need_especial"]:
                n_esp = min(r["qty"], max(0, a["need_especial"][ck] - usado_esp.get(ck, 0)))
            tenho_esp = min(n_esp, max(0, a["alloc_especial"].get(ck, 0) - usado_esp.get(ck, 0)))
            enc_esp = min(n_esp - tenho_esp,
                          max(0, a["a_caminho_especial"].get(ck, 0) - usado_cam_esp.get(ck, 0)))
            # Quantas especiais as linhas anteriores já levaram — o ponto de
            # partida desta na lista das impressões servidas.
            ini_esp = min(usado_esp.get(ck, 0), a["alloc_especial"].get(ck, 0))
            usado_esp[ck] = usado_esp.get(ck, 0) + n_esp
            usado_cam_esp[ck] = usado_cam_esp.get(ck, 0) + enc_esp
            falta_esp = n_esp - tenho_esp - enc_esp

            # O resto da linha são lugares normais: a base — e, se a base não
            # chegar, outra versão que ele tenha (2026-09-17, tarde).
            normais = r["qty"] - n_esp
            disponivel = max(0, a["alloc"].get(ck, 0) - a["alloc_especial"].get(ck, 0)
                             - usado.get(ck, 0))
            tenho = min(normais, disponivel) + tenho_esp
            ini_n = usado.get(ck, 0)
            usado[ck] = usado.get(ck, 0) + tenho - tenho_esp
            # As impressões que servem ESTA linha, repartidas por versão —
            # «2 normal (UNL-176) · 1 Alt Art (UNL-176a)». A alocação é por
            # carta; corta-se a lista dela ao que esta linha leva, pela ordem
            # dos papéis. Uma linha servida por uma impressão só leva uma
            # entrada, e a vista não a reparte.
            servidas = a["versoes_em"].get(ck, [])
            fatia = (_cortar([x for x in servidas if x["lugar"] == "especial"], ini_esp, tenho_esp)
                     + _cortar([x for x in servidas if x["lugar"] != "especial"],
                               ini_n, tenho - tenho_esp))
            versoes_linha = [{
                "id": x["id"], "code": versoes.info(x["id"])["code"],
                "kind": versoes.info(x["id"])["kind"], "label": versoes.rotulo(x["id"]),
                "qty": x["qty"], "lugar": x["lugar"],
            } for x in fatia]
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
            encomendada = min(normais - (tenho - tenho_esp),
                              max(0, a["a_caminho"].get(ck, 0) - a["a_caminho_especial"].get(ck, 0)
                                  - usado_caminho.get(ck, 0)))
            usado_caminho[ck] = usado_caminho.get(ck, 0) + encomendada
            encomendada += enc_esp
            falta = r["qty"] - tenho - encomendada
            info = names.get(ck) or {}
            # Onde o `+` grava a encomenda: a normal mais barata — ou, se o
            # que falta nesta linha é o lugar especial, a versão especial mais
            # barata.
            alvo = (encomendar_esp.get(ck) if falta_esp else encomendar_em.get(ck)) or {}
            especial = None
            if n_esp:
                em = a["especial_em"].get(ck)
                especial = {
                    "wanted": n_esp, "have": tenho_esp, "ordered": enc_esp,
                    "missing": falta_esp,
                    # A versão que serve (ou vem a caminho), e as que serviam.
                    **({"code": versoes.info(em)["code"], "id": em} if em
                       else {"code": alvo.get("code"), "id": alvo.get("id")}),
                    "alternativas": [x["code"] for x in versoes.alternativas(ck)
                                     if x["id"] != (em or alvo.get("id"))],
                }
            cards.append({
                "card_key": ck,
                "name": (info["name"] if info else r["raw_line"]),
                "raw": r["raw_line"],
                "type": info["type"] if info else None,
                "wanted": r["qty"], "have": tenho, "missing": falta,
                "ordered": encomendada,
                "no_deck": no_deck, "no_binder": no_binder,
                "na_colecao": tenho - no_deck - no_binder,
                "contado": True,
                # O lugar especial desta linha (a Legend/Champion), ou `None`.
                "especial": especial,
                # As impressões que servem esta linha, por versão, e quantas
                # cópias vieram de OUTRA versão por a base não chegar.
                "versoes": versoes_linha,
                "outras": sum(x["qty"] for x in versoes_linha if x["lugar"] == "outra"),
                # Onde o `+` grava a encomenda.
                "order_code": alvo.get("code"), "order_price": alvo.get("price"),
                "order_especial": bool(falta_esp),
                # Onde está o que falta, quando existe num deck de cima.
                "shared": a["shared"].get(ck) if falta else None,
                # Os irmãos do grupo (mesma Legend) que também pedem esta
                # carta: partilham-na, não a disputam. É uma compra só.
                "partilhada": a["partilhada"].get(ck),
                "printings": prints.get(ck, []),
                **imagem(ck),
            })
        # Os totais da secção são só do que se conta; `nao_contadas` diz
        # quantas cópias a lista pede e ficam de fora (o Rune Pool inteiro).
        contadas = [c for c in cards if c["contado"]]
        sections.append({"role": role, "label": ROLE_LABEL[role], "cards": cards,
                         "wanted": sum(c["wanted"] for c in contadas),
                         "have": sum(c["have"] for c in contadas),
                         "ordered": sum(c["ordered"] for c in contadas),
                         "no_deck": sum(c["no_deck"] for c in contadas),
                         "no_binder": sum(c["no_binder"] for c in contadas),
                         "na_colecao": sum(c["na_colecao"] for c in contadas),
                         "nao_contadas": sum(c["wanted"] for c in cards
                                             if not c["contado"])})

    return {
        "id": deck_id, "slug": d["name"], "name": d["display_name"] or d["name"],
        "legend": d["legend"], "champion": d["champion"], "priority": d["priority"],
        "sections": sections,
        # As runas que a lista pede e não se contam (2026-09-17, à noite): o
        # mesmo bloco do `decks_index`, para o cabeçalho dizer «12 runas».
        "runas": {"copies": sum(s["nao_contadas"] for s in sections),
                  "cards": len({c["card_key"] for s in sections for c in s["cards"]
                                if not c["contado"]}),
                  "contadas": not fora},
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
            # Lugares normais tapados por outra versão que ele tem.
            "outras": sum(a["alloc_outras"].values()),
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
    # Ao preço da impressão em que se compra (`Versoes.compra`); a versão
    # especial da Legend/Champion é uma linha à parte (2026-09-17).
    versoes = versoes_dos_decks(con)
    barato = preco_de_compra(versoes)

    names = {r["card_key"]: r["name"] for r in con.execute(
        "SELECT card_key, name FROM catalog.cards")}
    # Tudo junto soma-se por GRUPO de Legend, pelo líder — os irmãos pedem as
    # mesmas cópias (2026-09-11, noite).
    juntos: dict[tuple, int] = {}
    for d in deck_rows(con):
        a = alloc[d["deck_id"]]
        if deck_id and d["deck_id"] != deck_id:
            continue
        if not deck_id and not a["grupo"]["lider"]:
            continue
        lado = a if deck_id else a["grupo"]
        for ck, q in lado["missing"].items():
            n_esp = min(q, lado["missing_especial"].get(ck, 0))
            if n_esp:
                k = (ck, True, barato(ck, especial=True))
                juntos[k] = juntos.get(k, 0) + n_esp
            if q - n_esp:
                k = (ck, False, barato(ck))
                juntos[k] = juntos.get(k, 0) + q - n_esp

    return sorted(
        [{"card_key": ck, "name": names.get(ck, ck), "qty": q, "especial": esp,
          "code": versoes.info(versoes.compra(ck, esp))["code"],
          "price_cents": preco, "total_cents": (preco or 0) * q}
         for (ck, esp, preco), q in juntos.items()],
        key=lambda x: -x["total_cents"])

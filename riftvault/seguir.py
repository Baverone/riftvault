"""Seguir jogadores no Piltover Archive: os decks deles e o que FALTA ao André.

Palavras dele (2026-09-17): *"o @koko_lopez e um jogador muito bom, gostava de
seguir os decks que ele coloca e que vai atualizando"* / *"nao preciso que me
diga quanto custaria, mas sim o que falta"*. Por isso este módulo nunca fala
em euros: diz cartas e cópias.

O QUE SE LÊ, E DE ONDE — SÓ PÁGINAS, NUNCA A API
    O `robots.txt` do piltoverarchive.com permite as páginas públicas e proíbe
    `/api/`, `/admin/`, `/_next/` e `/static/`. A lista de decks de um perfil é
    carregada pelo browser através da API (tRPC) — que está vedada —, por isso
    o perfil em HTML só traz o deck em destaque e os TRÊS mais recentes (por
    data de CRIAÇÃO, não de edição: o «Kennen Post Ban», editado a 16/09, não
    estava lá a 17/09). Três páginas, todas HTML público, dão o que é preciso:

      1. `/users/<nome>` — o perfil: o handle, quantos decks públicos tem
         (`stats.publicDecks`), o deck em destaque e os últimos criados.
      2. `/decks?q=<nome>&page=N` — a listagem pública com pesquisa por texto.
         O `q` casa com o TÍTULO e com o AUTOR: com `q=koko_lopez` vieram 30
         decks, 17 dele (os 4 do perfil incluídos) e 13 de outros com «Koko
         Lopez» no título. Filtra-se pelo `userOwners[].handle`. É a única
         listagem dos decks de um autor que existe em HTML; o perfil diz 18 e
         a listagem deu 17 — o 18.º não aparece em página nenhuma que se
         possa ler, e a página diz-o em vez de fingir que são todos.
      3. `/decks/view/<id>` — a página do deck, com a lista de cartas.

    Os três são páginas Next.js: o que interessa vem no payload RSC, os
    `self.__next_f.push([1,"..."])` no fim do HTML, como JSON dentro de uma
    string de JavaScript. Lê-se DAÍ, não das classes do HTML: o JSON traz
    `editedAt`, `quantity` e o código impresso (`variantNumber`, «VEN-113»),
    e as classes são Tailwind, mudam a cada build. As marcas que se esperam
    estão em `MARCAS`; quando uma faltar, o parser REBENTA (`SiteMudou`) com o
    nome da marca e o ficheiro onde a página ficou guardada — nunca devolve
    uma lista vazia como se estivesse tudo bem, porque isso lia-se «não te
    falta nada».

EDUCAÇÃO
    Um pedido por segundo no máximo (`INTERVALO_MINIMO`, o config só pode
    ALARGAR), User-Agent que diz o que isto é, nada de contas nem de páginas
    privadas, e o `Cliente` recusa qualquer endereço debaixo dos prefixos que
    o `robots.txt` proíbe — mesmo que alguém lho peça. Só se vai buscar a
    página de um deck quando ele é NOVO ou o `editedAt` mudou; o resto vem do
    estado guardado (`estado.json`). O `riftdecks.com` está VEDADO pelo
    `robots.txt` deles ao ClaudeBot e ao anthropic-ai e não se toca.

O QUE CONTA COMO «TER» (decisões desta ordem — ver o relatório)
    - TUDO o que ele possui, incluindo as cópias que estão nos decks DELE: um
      deck de outra pessoa é hipotético, não disputa a Coleção com os dele.
    - Qualquer impressão que não seja assinada serve (`variant_kind !=
      "signature"`), e as runas em Alt Art retiradas (`metrics.retirada`)
      continuam a não existir. A regra da Legend e do Champion em versão
      especial é dos decks DELE (`decks.Versoes`) e não se aplica aqui.
    - O que está a caminho (`pending`) ainda não é dele e NÃO conta.
    - Main, battlefields, runas e sideboard somam por carta lógica, como no
      `decks.allocate` — a mesma carta no main e no sideboard pede as duas.
    - Nomes que não casam no catálogo NUNCA se adivinham: ficam em
      «não identificadas» e o deck diz em cima que a falta está incompleta.
"""

from __future__ import annotations

import json
import re
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from . import config, decks, metrics

BASE = "https://piltoverarchive.com"
USER_AGENT = "riftvault/1.0 (colecao pessoal; +https://github.com/baverone/riftvault)"
INTERVALO_MINIMO = 1.0    # segundos entre pedidos; o config só pode subir
TIMEOUT = 30
# O que o robots.txt deles proíbe (lido a 2026-09-17). Nunca se pede nada aqui.
PREFIXOS_VEDADOS = ("/api/", "/admin/", "/_next/", "/static/")
ESTADO_VERSAO = 1

# Os papéis da página do deck -> os nossos (`decks.ROLE_ORDER`). O `bench` é
# deles e não se sabe o que é (vinha vazio a 2026-09-17): lê-se, guarda-se,
# mas NÃO conta para a falta — adivinhar que é sideboard era inventar.
PAPEIS = {"champions": "champion", "battlefields": "battlefields", "runes": "runes",
          "maindeck": "main", "sideboard": "sideboard", "bench": "bench"}
PAPEIS_QUE_CONTAM = ("legend", "champion", "main", "battlefields", "runes", "sideboard")

# As marcas de cada página. Se uma faltar, o site mudou: `SiteMudou` diz qual.
# As de objecto (`"chave":{`) levam as chaves que o objecto tem de ter — há
# mais do que um `"deck":{` numa página, e é o que tem `legend` que interessa.
MARCAS = {
    "rsc": 'self.__next_f.push([1,"',
    "perfil": '"profile":{',
    "perfil.decks": '"decks":{"featured":',
    "listagem": '"currentFilters":{',
    "listagem.entrada": '{"id":"<uuid>","name":"',
    "deck": '"deck":{',
}
MARCAS_CHAVES = {"perfil": ("identity", "decks"), "deck": ("id", "legend", "maindeck")}

DEFAULTS = dict(config.DEFAULTS["seguir"])


class SeguirError(RuntimeError):
    """Rede, HTTP, ou um pedido que a educação não deixa fazer."""


class SiteMudou(SeguirError):
    """A página não tem a marca que se esperava — o HTML deles mudou."""


def opcoes(cfg: dict | None = None) -> dict:
    cfg = cfg or config.load()
    out = dict(DEFAULTS)
    out.update(cfg.get("seguir") or {})
    out["intervalo_segundos"] = max(INTERVALO_MINIMO, float(out.get("intervalo_segundos") or 0))
    out["max_paginas"] = max(1, int(out.get("max_paginas") or 1))
    out["jogadores"] = [str(j).strip().lstrip("@") for j in (out.get("jogadores") or []) if str(j).strip()]
    return out


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Rede
# ---------------------------------------------------------------------------


def url_perfil(nome: str) -> str:
    return f"{BASE}/users/{nome}"


def url_listagem(nome: str, pagina: int = 1) -> str:
    from urllib.parse import urlencode
    q = {"q": nome}
    if pagina > 1:
        q["page"] = str(pagina)
    return f"{BASE}/decks?{urlencode(q)}"


def url_deck(deck_id: str) -> str:
    return f"{BASE}/decks/view/{deck_id}"


def caminho_vedado(url: str) -> bool:
    from urllib.parse import urlsplit
    p = urlsplit(url)
    if p.netloc and p.netloc != "piltoverarchive.com":
        return True
    return any(p.path.startswith(x) for x in PREFIXOS_VEDADOS)


class Cliente:
    """Um pedido de cada vez, com pelo menos `intervalo` segundos entre dois.

    Guarda a última página de cada endereço em `pasta/paginas/`, para quando o
    parser rebentar haver o HTML à mão — é esse ficheiro que a mensagem do
    `SiteMudou` aponta, e é daí que sai a fixture seguinte.
    """

    def __init__(self, intervalo: float = INTERVALO_MINIMO, pasta: Path | None = None):
        import requests
        self.intervalo = max(INTERVALO_MINIMO, intervalo)
        self.pasta = pasta
        self._ultimo = 0.0
        self._session = requests.Session()
        # Só ASCII: há servidores que respondem 403 a acentos no User-Agent.
        self._session.headers.update({"User-Agent": USER_AGENT,
                                      "Accept": "text/html", "Accept-Language": "en"})
        self.pedidos = 0

    def __call__(self, url: str) -> str:
        import requests
        if caminho_vedado(url):
            raise SeguirError(f"recusado: {url} está debaixo de um prefixo que o robots.txt "
                              f"proíbe ({', '.join(PREFIXOS_VEDADOS)}) ou fora do site")
        espera = self.intervalo - (time.monotonic() - self._ultimo)
        if espera > 0:
            time.sleep(espera)
        try:
            resp = self._session.get(url, timeout=TIMEOUT)
        except requests.RequestException as exc:
            raise SeguirError(f"falhou o pedido a {url}: {exc}") from exc
        finally:
            self._ultimo = time.monotonic()
            self.pedidos += 1
        if resp.status_code != 200:
            raise SeguirError(f"{url} devolveu HTTP {resp.status_code}")
        html = resp.text
        guardar_pagina(self.pasta, url, html)
        return html


def nome_da_pagina(url: str) -> str:
    """Um nome de ficheiro para o HTML de um endereço: `users-koko_lopez.html`."""
    from urllib.parse import urlsplit
    p = urlsplit(url)
    base = re.sub(r"[^A-Za-z0-9_.-]+", "-", (p.path + ("-" + p.query if p.query else "")).strip("/"))
    return (base or "raiz") + ".html"


def guardar_pagina(pasta: Path | None, url: str, html: str) -> Path | None:
    if pasta is None:
        return None
    dest = Path(pasta) / "paginas" / nome_da_pagina(url)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(html, encoding="utf-8")
    return dest


# ---------------------------------------------------------------------------
# Parser — o payload RSC
# ---------------------------------------------------------------------------


def _rebentar(marca: str, onde: str, detalhe: str = "") -> SiteMudou:
    esperado = MARCAS.get(marca, marca)
    return SiteMudou(
        f"o HTML do Piltover Archive mudou: não encontrei a marca {marca!r} "
        f"({esperado!r}) em {onde}" + (f" — {detalhe}" if detalhe else "")
        + ". Não se lê nada desta página até o parser (`riftvault/seguir.py`) ser "
          "ajustado; a página ficou guardada em `data/seguir/paginas/`.")


def rsc_texto(html: str, onde: str = "a página") -> str:
    """O payload RSC inteiro: os `self.__next_f.push([1,"..."])` descodificados
    e colados. É uma string de JavaScript com JSON lá dentro; o `json.loads`
    de `"..."` faz a descodificação das escapes."""
    pedacos = [json.loads('"' + m.group(1) + '"') for m in
               re.finditer(r'self\.__next_f\.push\(\[1,"((?:[^"\\]|\\.)*)"\]\)', html)]
    if not pedacos:
        raise _rebentar("rsc", onde, "a página já não traz o payload RSC do Next.js")
    return "".join(pedacos)


def _objecto(texto: str, marca: str, onde: str) -> dict:
    """O primeiro objecto JSON a seguir à marca (`"chave":{`) que tenha as
    chaves de `MARCAS_CHAVES` — a marca pode aparecer mais do que uma vez."""
    esperado, chaves = MARCAS[marca], MARCAS_CHAVES.get(marca, ())
    dec = json.JSONDecoder()
    vistas, pos = 0, texto.find(esperado)
    while pos >= 0:
        vistas += 1
        try:
            obj, _ = dec.raw_decode(texto, pos + len(esperado) - 1)   # a chaveta
        except json.JSONDecodeError:
            obj = None
        if isinstance(obj, dict) and all(k in obj for k in chaves):
            return obj
        pos = texto.find(esperado, pos + 1)
    if vistas:
        raise _rebentar(marca, onde, f"a marca aparece {vistas}× mas nenhum objecto a seguir "
                                     f"tem {', '.join(chaves)}")
    raise _rebentar(marca, onde)


def _data(valor) -> str | None:
    """As datas vêm `"2026-09-03T14:54:22.251Z"` no perfil e `"$D2026-..."` na
    página do deck (o RSC marca os `Date` com `$D`)."""
    if not isinstance(valor, str) or not valor:
        return None
    return valor[2:] if valor.startswith("$D") else valor


def _entrada_de_deck(obj: dict) -> dict | None:
    """Uma entrada de listagem (perfil ou `/decks`) -> o que se guarda dela."""
    if not isinstance(obj, dict) or not obj.get("id") or "editedAt" not in obj:
        return None
    donos = [str(o.get("handle") or "").lower() for o in (obj.get("userOwners") or [])
             if isinstance(o, dict)]
    legend = obj.get("legend") or {}
    return {
        "id": obj["id"],
        "title": obj.get("name") or "",
        "url": url_deck(obj["id"]),
        "edited_at": _data(obj.get("editedAt")) or _data(obj.get("createdAt")),
        "created_at": _data(obj.get("createdAt")),
        "status": obj.get("status"),
        "handles": donos,
        "author": obj.get("authorName") or "",
        "legend": legend.get("name") if isinstance(legend, dict) else None,
        "legend_code": legend.get("variantNumber") if isinstance(legend, dict) else None,
    }


def ler_perfil(html: str, nome: str) -> dict:
    """`/users/<nome>` -> handle, nome de mostrar, decks públicos, e os decks
    que o HTML traz (o destaque e os últimos criados)."""
    onde = f"o perfil de {nome}"
    texto = rsc_texto(html, onde)
    perfil = _objecto(texto, "perfil", onde)
    ident = perfil.get("identity") or {}
    if not isinstance(ident, dict):
        raise _rebentar("perfil", onde, "o `profile.identity` já não é um objecto")
    handle = str(ident.get("username") or "").lower()
    if not handle:
        raise _rebentar("perfil", onde, "o objecto `profile.identity` não tem `username`")
    if handle != nome.lower():
        raise SeguirError(f"pedi o perfil de {nome!r} e a página é de {handle!r}")
    blocos = perfil.get("decks")
    if not isinstance(blocos, dict) or "featured" not in blocos or "latest" not in blocos:
        raise _rebentar("perfil.decks", onde, "o `profile.decks` já não tem `featured`/`latest`")
    vistos: dict[str, dict] = {}
    for obj in [blocos.get("featured")] + list(blocos.get("latest") or []):
        e = _entrada_de_deck(obj)
        if e is None:
            if obj is not None:
                raise _rebentar("perfil.decks", onde, "uma entrada de deck sem `id`/`editedAt`")
            continue
        vistos.setdefault(e["id"], e)
    # O «18 public» da barra de separadores vive noutro objecto do RSC
    # (`"stats":{"publicDecks":18,…}`); é a conta de honestidade — «a listagem
    # deu 17, o perfil diz 18». Sem ela a página diz que não sabe; não rebenta
    # porque não muda o que falta em cada deck.
    m = re.search(r'"publicDecks":(\d+)', texto)
    return {
        "handle": handle,
        "display": ident.get("displayName") or handle,
        "public_decks": int(m.group(1)) if m else None,
        "decks": list(vistos.values()),
    }


def ler_listagem(html: str, nome: str, pagina: int = 1) -> dict:
    """`/decks?q=<nome>&page=N` -> os decks DESSE handle nesta página, quantas
    entradas tinha ao todo, e a última página que os links de paginação
    anunciam. Zero entradas com a marca da listagem presente é «não há
    resultados», não é o site ter mudado."""
    onde = f"a listagem /decks?q={nome} (página {pagina})"
    texto = rsc_texto(html, onde)
    if MARCAS["listagem"] not in texto:
        raise _rebentar("listagem", onde)
    dec = json.JSONDecoder()
    entradas: dict[str, dict] = {}
    for m in re.finditer(r'\{"id":"[0-9a-f-]{36}","name":"', texto):
        try:
            obj, _ = dec.raw_decode(texto, m.start())
        except json.JSONDecodeError:
            continue
        e = _entrada_de_deck(obj)
        if e is not None and "userOwners" in obj:
            entradas.setdefault(e["id"], e)
    # A verificação cruzada que impede o «zero resultados» mudo: os decks que
    # o HTML LIGA (`href="/decks/view/<id>"`) têm de estar todos no que se leu
    # do RSC. Se a ordem das chaves mudar, o regex de cima deixa de casar e é
    # aqui que rebenta em vez de dizer «não há decks».
    ligados = set(re.findall(r'href="/decks/view/([0-9a-f-]{36})"', html))
    if ligados - set(entradas):
        raise _rebentar("listagem.entrada", onde,
                        f"o HTML liga {len(ligados)} decks e o RSC só deu {len(entradas)} entradas")
    alvo = nome.lower()
    meus = [e for e in entradas.values() if alvo in e["handles"]]
    # Os links de paginação não incluem a página em que se está: na última, o
    # maior link é a penúltima.
    paginas = [int(x) for x in re.findall(r'href="/decks\?[^"]*?page=(\d+)', html)]
    return {"decks": meus, "entradas": len(entradas),
            "ultima_pagina": max(paginas + [pagina])}


def ler_deck(html: str, deck_id: str | None = None) -> dict:
    """`/decks/view/<id>` -> título, autor, datas, Legend e a lista de cartas
    por papel, com o código impresso que o site escolheu (`variantNumber`)."""
    onde = f"a página do deck {deck_id or ''}".strip()
    texto = rsc_texto(html, onde)
    d = _objecto(texto, "deck", onde)
    if deck_id and d.get("id") != deck_id:
        raise SeguirError(f"pedi o deck {deck_id} e a página é do {d.get('id')!r}")
    faltam = [k for k in ("legend", *PAPEIS) if k not in d]
    if faltam:
        raise _rebentar("deck", onde, f"o objecto `deck` já não tem {', '.join(faltam)}")

    def carta(entrada: dict, papel: str) -> dict:
        c = entrada.get("card") or {}
        variantes = c.get("cardVariants") or []
        escolhida = next((v for v in variantes if v.get("id") == entrada.get("variantId")),
                         variantes[0] if variantes else {})
        return {"role": papel, "qty": int(entrada.get("quantity") or 0),
                "name": c.get("name") or "", "code": escolhida.get("variantNumber"),
                "type": c.get("type")}

    cartas: list[dict] = []
    legend = d.get("legend") or {}
    if legend:
        lc = legend.get("card") or {}
        cartas.append({"role": "legend", "qty": 1, "name": lc.get("name") or "",
                       "code": legend.get("variantNumber"), "type": lc.get("type") or "Legend"})
    for chave, papel in PAPEIS.items():
        for entrada in d.get(chave) or []:
            cartas.append(carta(entrada, papel))
    if not any(x["qty"] > 0 and x["name"] for x in cartas):
        raise _rebentar("deck", onde, "o objecto `deck` existe mas não tem uma carta com nome e quantidade")
    sem_nome = [x for x in cartas if not x["name"]]
    if sem_nome:
        raise _rebentar("deck", onde, f"{len(sem_nome)} entradas sem `card.name`")
    return {
        "id": d.get("id"),
        "title": d.get("name") or "",
        "url": url_deck(d.get("id") or ""),
        "author": d.get("authorName") or "",
        "status": d.get("status"),
        "edited_at": _data(d.get("editedAt")) or _data(d.get("createdAt")),
        "created_at": _data(d.get("createdAt")),
        "legend": (legend.get("card") or {}).get("name") if legend else None,
        "legend_code": legend.get("variantNumber") if legend else None,
        "cards": cartas,
    }


# ---------------------------------------------------------------------------
# Catálogo: nomes -> cartas lógicas, e o que ele tem
# ---------------------------------------------------------------------------


def resolver(con: sqlite3.Connection, name: str, code: str | None) -> tuple[str | None, str | None]:
    """(card_key, motivo). Pelo NOME primeiro (é a carta lógica), pelo código
    impresso se o nome não casar. Se os dois casarem em cartas DIFERENTES não
    se escolhe: é «não identificada» com a razão escrita."""
    por_nome = decks.resolve(con, name, "main") if name else None
    por_codigo = None
    if code:
        row = con.execute(
            "SELECT p.card_key FROM catalog.printing_aliases a "
            "JOIN catalog.printings p ON p.printing_id = a.printing_id WHERE a.alias = ?",
            (code.strip().lower().split("/")[0],)).fetchone()
        por_codigo = row["card_key"] if row else None
    if por_nome and por_codigo and por_nome != por_codigo:
        return None, f"o nome casa com «{por_nome}» e o código {code} com «{por_codigo}»"
    if por_nome:
        return por_nome, "nome"
    if por_codigo:
        return por_codigo, "código"
    return None, "nem o nome nem o código estão no catálogo"


def possuidas(con: sqlite3.Connection, cfg: dict | None = None) -> dict[str, int]:
    """card_key -> cópias que SERVEM um deck de outra pessoa: tudo o que ele
    tem, em qualquer local (Coleção, decks dele, binder), de qualquer
    impressão que não seja assinada nem retirada."""
    cfg = cfg or config.load()
    out: dict[str, int] = {}
    for r in con.execute(
        "SELECT p.card_key AS k, p.type, p.variant_kind, c.qty FROM copies c "
        "JOIN catalog.printings p ON p.printing_id = c.printing_id WHERE c.qty > 0"
    ):
        if r["variant_kind"] == "signature" or metrics.retirada(r, cfg):
            continue
        out[r["k"]] = out.get(r["k"], 0) + r["qty"]
    return out


def faltas_do_deck(con: sqlite3.Connection, cartas: list[dict],
                   tem: dict[str, int]) -> dict:
    """O que falta para montar ESTA lista com o que ele tem.

    Soma por carta lógica em todos os papéis que contam (`PAPEIS_QUE_CONTAM`);
    o `bench` fica de fora. As não identificadas vão à parte e NUNCA entram
    na conta — o deck diz que a falta está incompleta.
    """
    pedido: dict[str, dict] = {}
    nao_ident: list[dict] = []
    fora: list[dict] = []
    for x in cartas:
        if x["role"] not in PAPEIS_QUE_CONTAM:
            fora.append(x)
            continue
        ck, motivo = resolver(con, x["name"], x.get("code"))
        if ck is None:
            nao_ident.append({**x, "motivo": motivo})
            continue
        e = pedido.setdefault(ck, {"card_key": ck, "name": x["name"], "code": x.get("code"),
                                   "qty": 0, "roles": []})
        e["qty"] += x["qty"]
        if x["role"] not in e["roles"]:
            e["roles"].append(x["role"])
    linhas = []
    for ck, e in pedido.items():
        row = con.execute("SELECT name FROM catalog.cards WHERE card_key = ?", (ck,)).fetchone()
        have = tem.get(ck, 0)
        linhas.append({**e, "catalog_name": row["name"] if row else e["name"],
                       "have": have, "missing": max(0, e["qty"] - have)})
    linhas.sort(key=lambda l: (-l["missing"], l["catalog_name"].casefold()))
    faltam = [l for l in linhas if l["missing"] > 0]
    return {
        "cards": linhas,
        "missing": faltam,
        "missing_copies": sum(l["missing"] for l in faltam),
        "missing_cards": len(faltam),
        "wanted_copies": sum(l["qty"] for l in linhas),
        "unidentified": nao_ident,
        "unidentified_copies": sum(x["qty"] for x in nao_ident),
        "ignored": fora,
        "complete": not faltam and not nao_ident,
    }


# ---------------------------------------------------------------------------
# Estado
# ---------------------------------------------------------------------------


def caminho_estado(pasta: Path | None = None) -> Path:
    return Path(pasta or config.SEGUIR_DIR) / "estado.json"


def carregar_estado(pasta: Path | None = None) -> dict:
    p = caminho_estado(pasta)
    if not p.exists():
        return {"versao": ESTADO_VERSAO, "corrida_em": None, "jogadores": {}}
    est = json.loads(p.read_text(encoding="utf-8"))
    if est.get("versao") != ESTADO_VERSAO:
        raise SeguirError(f"{p} é da versão {est.get('versao')!r} e este código lê a "
                          f"{ESTADO_VERSAO}; apaga-o (perde-se só o «novo/actualizado» de uma corrida)")
    est.setdefault("jogadores", {})
    return est


def guardar_estado(est: dict, pasta: Path | None = None) -> Path:
    p = caminho_estado(pasta)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(est, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                 encoding="utf-8")
    return p


def classificar(anterior: dict | None, actual: dict) -> str:
    """novo | actualizado | igual, pelo `edited_at` da listagem contra o guardado.
    Um deck guardado sem cartas (uma corrida que morreu a meio) conta como
    novo: é preciso ir buscá-lo."""
    if anterior is None or not anterior.get("cards"):
        return "novo"
    if (anterior.get("edited_at") or "") != (actual.get("edited_at") or ""):
        return "actualizado"
    return "igual"


# ---------------------------------------------------------------------------
# A corrida
# ---------------------------------------------------------------------------


def listar_decks(nome: str, buscar: Callable[[str], str], max_paginas: int,
                 log=print) -> dict:
    """O perfil mais a listagem paginada, fundidos por id."""
    perfil = ler_perfil(buscar(url_perfil(nome)), nome)
    decks_vistos: dict[str, dict] = {d["id"]: d for d in perfil["decks"]}
    pagina, ultima, entradas = 1, 1, 0
    while pagina <= ultima and pagina <= max_paginas:
        lst = ler_listagem(buscar(url_listagem(nome, pagina)), nome, pagina)
        entradas += lst["entradas"]
        ultima = lst["ultima_pagina"]
        for d in lst["decks"]:
            decks_vistos.setdefault(d["id"], d)
        if lst["entradas"] == 0:
            break
        pagina += 1
    truncada = ultima > max_paginas
    if truncada:
        log(f"  aviso: a listagem de {nome} tem {ultima} páginas e só se leram "
            f"{max_paginas} (seguir.max_paginas) — podem faltar decks.")
    return {**perfil, "decks": list(decks_vistos.values()), "paginas_lidas": min(ultima, max_paginas),
            "paginas": ultima, "truncada": truncada, "entradas": entradas}


def seguir_jogador(con: sqlite3.Connection, nome: str, buscar: Callable[[str], str],
                   est: dict, *, max_paginas: int = 10, tem: dict[str, int] | None = None,
                   sem_rede: bool = False, pasta: Path | None = None, log=print) -> dict:
    """Uma corrida para um jogador. Escreve no `est` (e guarda-o a cada deck
    lido, para uma corrida que morra a meio não perder o que já leu)."""
    tem = possuidas(con) if tem is None else tem
    guardado = est["jogadores"].setdefault(nome.lower(), {"decks": {}})
    conhecidos: dict[str, dict] = guardado.get("decks") or {}
    agora = _agora()

    if sem_rede:
        listagem = {"handle": nome.lower(), "display": guardado.get("display") or nome,
                    "public_decks": guardado.get("public_decks"),
                    "decks": [{k: v for k, v in d.items() if k != "cards"} for d in conhecidos.values()],
                    "paginas": 0, "paginas_lidas": 0, "truncada": False, "entradas": 0}
    else:
        listagem = listar_decks(nome, buscar, max_paginas, log)
        guardado["display"] = listagem["display"]
        guardado["public_decks"] = listagem["public_decks"]
        guardado["visto_em"] = agora

    saida: list[dict] = []
    vistos_agora: set[str] = set()
    for d in sorted(listagem["decks"], key=lambda x: x.get("edited_at") or "", reverse=True):
        vistos_agora.add(d["id"])
        antes = conhecidos.get(d["id"])
        estado = classificar(antes, d)
        if sem_rede:
            # Sem rede não se vai buscar nada: o que não tem lista guardada
            # fica «por ler» — e o que tem, lê-se como está.
            estado = "por ler" if estado == "novo" else "igual"
        if estado in ("novo", "actualizado"):
            lido = ler_deck(buscar(url_deck(d["id"])), d["id"])
            registo = {**d, **{k: lido[k] for k in ("title", "edited_at", "created_at", "legend",
                                                    "legend_code", "cards", "author")},
                       "lido_em": agora, "ultima_mudanca": {"quando": agora, "o_que": estado},
                       "ausente_desde": None}
            if antes and antes.get("cards") and lido["cards"] == antes["cards"]:
                # O `editedAt` mexeu mas a lista é a mesma (mudou o título, a
                # descrição, …): não vale a pena dizer «actualizado».
                estado = "igual"
                registo["ultima_mudanca"] = antes.get("ultima_mudanca")
            conhecidos[d["id"]] = registo
            guardado["decks"] = conhecidos
            guardar_estado(est, pasta)
        else:
            registo = {**(antes or {}), **{k: v for k, v in d.items() if k != "cards" and v is not None},
                       "ausente_desde": None}
            conhecidos[d["id"]] = registo
        faltas = (faltas_do_deck(con, registo["cards"], tem) if registo.get("cards") else None)
        saida.append({**{k: registo.get(k) for k in ("id", "title", "url", "edited_at", "created_at",
                                                     "legend", "legend_code", "lido_em", "ultima_mudanca")},
                      "estado": estado, "faltas": faltas})

    ausentes = []
    for did, d in conhecidos.items():
        if did in vistos_agora or sem_rede:
            continue
        d.setdefault("ausente_desde", None)
        if d["ausente_desde"] is None:
            d["ausente_desde"] = agora
        ausentes.append({"id": did, "title": d.get("title"), "url": d.get("url"),
                         "ausente_desde": d["ausente_desde"]})
    guardado["decks"] = conhecidos
    est["corrida_em"] = agora
    guardar_estado(est, pasta)

    contagem = {k: sum(1 for s in saida if s["estado"] == k)
                for k in ("novo", "actualizado", "igual", "por ler")}
    return {
        "player": nome.lower(),
        "display": listagem["display"],
        "url": url_perfil(nome),
        "public_decks": listagem["public_decks"],
        "found": len(saida),
        "pages": listagem["paginas"],
        "pages_read": listagem["paginas_lidas"],
        "truncated": listagem["truncada"],
        "counts": contagem,
        "decks": saida,
        "gone": ausentes,
        "offline": sem_rede,
    }


def correr(con: sqlite3.Connection, buscar: Callable[[str], str], *, cfg: dict | None = None,
           jogadores: list[str] | None = None, sem_rede: bool = False,
           pasta: Path | None = None, log=print) -> dict:
    """Todos os jogadores do config (ou os pedidos). Devolve o payload que o
    CLI imprime — e que a parte 2 (o site) há-de servir tal e qual."""
    cfg = cfg or config.load()
    op = opcoes(cfg)
    nomes = [n.strip().lstrip("@") for n in (jogadores or op["jogadores"]) if n.strip()]
    est = carregar_estado(pasta)
    tem = possuidas(con, cfg)
    out = []
    for nome in nomes:
        log(f"{nome}: " + ("a ler o estado guardado" if sem_rede else "a ler o Piltover Archive…"))
        out.append(seguir_jogador(con, nome, buscar, est, max_paginas=op["max_paginas"], tem=tem,
                                  sem_rede=sem_rede, pasta=pasta, log=log))
    return {"generated_at": _agora(), "since": est.get("corrida_em"), "players": out,
            "config": {"jogadores": nomes, "intervalo_segundos": op["intervalo_segundos"],
                       "max_paginas": op["max_paginas"]}}


def cliente(cfg: dict | None = None, pasta: Path | None = None) -> Cliente:
    op = opcoes(cfg)
    return Cliente(op["intervalo_segundos"], pasta if pasta is not None else config.SEGUIR_DIR)


def sem_rede(url: str) -> str:
    """O `buscar` de quem não quer ir à rede: qualquer pedido é erro. Com
    `correr(..., sem_rede=True)` nunca chega a ser chamado; está aqui para o
    engano ser visível se chegar."""
    raise SeguirError(f"sem rede: não se pediu {url}")

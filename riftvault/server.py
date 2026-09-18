"""Modo edição: servidor local que serve o site e escreve no vault.db.

Faz bind em 0.0.0.0 e mostra o URL da rede local + QR ao arrancar, para o
André mexer nas cartas com o telemóvel na mão.

O frontend é exatamente o mesmo do modo publicado. A única diferença é o flag
`editable` no payload e a existência dos endpoints de escrita.
"""

from __future__ import annotations

import io
import re
import socket
import subprocess
import sys
from datetime import datetime, timezone

from flask import Flask, g, jsonify, redirect, request, send_from_directory

from . import (a_mais, a_subir, collection, config, db, decks, faltas, faltas_edicao,
               locais, metrics, pending, promos, quanto_custa)

app = Flask(__name__, static_folder=None)


def get_con():
    # Uma ligação por pedido: os objetos do sqlite3 não atravessam threads.
    if "con" not in g:
        g.con = db.connect()
    return g.con


@app.teardown_appcontext
def _close(_exc):
    con = g.pop("con", None)
    if con is not None:
        con.close()


# --------------------------------------------------------------------------
# Frontend (os mesmos ficheiros que o build estático copia)
# --------------------------------------------------------------------------


def _sem_cache(resp):
    """O modo edição serve sempre a versão fresca.

    Sem isto, o telemóvel fica com um `app.js` antigo em cache e a página
    parece partida depois de qualquer alteração ao código — carrega-se nos
    `+` e não acontece nada, sem erro nenhum à vista. As imagens continuam
    com cache longo; são o que pesa e nunca mudam.
    """
    resp.headers["Cache-Control"] = "no-store, must-revalidate"
    return resp


@app.get("/")
def index():
    return _sem_cache(send_from_directory(config.WEB_DIR, "index.html"))


@app.get("/<path:name>")
def web_asset(name: str):
    if (config.WEB_DIR / name).is_file():
        return _sem_cache(send_from_directory(config.WEB_DIR, name))
    return ("não encontrado", 404)


@app.get("/img/<path:name>")
def image(name: str):
    """Imagem do cache local; se ainda não foi descarregada, cai para o CDN."""
    path = config.IMAGES_DIR / name
    if path.is_file() and path.stat().st_size > 0:
        return send_from_directory(config.IMAGES_DIR, name, max_age=60 * 60 * 24 * 30)

    printing_id = name.rsplit(".", 1)[0]
    row = get_con().execute(
        "SELECT image_medium, image_large, image_url FROM catalog.printings "
        "WHERE printing_id = ?",
        (printing_id,),
    ).fetchone()
    url = row and (row["image_medium"] or row["image_large"] or row["image_url"])
    if url:
        return redirect(url, code=302)
    return ("sem imagem", 404)


# --------------------------------------------------------------------------
# API de leitura (mesmos URLs que o build estático gera como ficheiros)
# --------------------------------------------------------------------------


@app.get("/api/index.json")
def api_index():
    return jsonify(metrics.index_payload(get_con(), editable=True, image_mode="local"))


@app.get("/api/set/<set_id>.json")
def api_set(set_id: str):
    con = get_con()
    # A grelha da Coleção diz em que deck está cada cópia; sem isto essa linha
    # ficava presa às listas de quando o servidor arrancou, e só se atualizava
    # depois de alguém abrir a secção Decks.
    _reimport_if_changed(con)
    return jsonify(metrics.set_payload(con, set_id.upper(),
                                       editable=True, image_mode="local"))


@app.get("/api/history.json")
def api_history():
    limit = min(int(request.args.get("limit", 30)), 500)
    return jsonify({"ops": collection.history(get_con(), limit)})


@app.get("/api/decks.json")
def api_decks():
    con = get_con()
    _reimport_if_changed(con)
    return jsonify({"editable": True, "decks": decks.decks_index(con),
                    "rules": decks.rules()})


@app.get("/api/quanto_custa.json")
def api_quanto_custa():
    """O separador «Quanto custa»: a tabela de preços por edição e raridade
    (2026-09-15, à tarde). Não depende dos decks nem das faltas."""
    return jsonify(quanto_custa.tabela(get_con()))


@app.get("/api/faltas_edicao.json")
def api_faltas_edicao():
    """O separador «Faltas» (2026-09-15, fim da tarde): por edição, em três
    blocos — master set, alt art, sobrenumeradas. Lê os locais e o pendente,
    não os decks."""
    return jsonify(faltas_edicao.payload(get_con()))


@app.get("/api/a_mais.json")
def api_a_mais():
    """O separador «A mais» (2026-09-17): por edição, o excedente acima do alvo
    e as cartas que os decks libertaram. Relê as listas primeiro, porque o
    bloco das libertadas vive do registo que o `import_all` escreve."""
    con = get_con()
    _reimport_if_changed(con)
    return jsonify(a_mais.payload(con))


@app.get("/api/promos.json")
def api_promos():
    """A montra «Promos» da Coleção (2026-09-18): as promos oficiais da lista
    `data/promos_oficiais.json`, com a foto da versão normal de cada carta.
    Só mostra — não conta para nada. Um ficheiro em falta ou mal escrito dá
    404 com a razão, em vez de uma página vazia a parecer «não há promos»."""
    try:
        return jsonify(promos.payload(get_con(), image_mode="local"))
    except promos.ListaInvalida as e:
        return jsonify({"error": str(e)}), 404


@app.get("/api/wantlist.json")
def api_wantlist():
    """As faltas do master set, por edição — a wantlist do fim de cada edição
    da Coleção. Vivia dentro do `api/faltas.json` (chave `master`) até
    2026-09-15; o ficheiro foi apagado com o separador e esta lista, que é
    da Coleção, ficou com URL próprio."""
    con = get_con()
    _reimport_if_changed(con)
    return jsonify(a_subir.master_faltas(con))


@app.get("/api/compras.json")
def api_compras():
    """As listas de compra dos decks (Staples, Por deck, Pimp decks) — o resto
    do antigo `api/faltas.json`."""
    con = get_con()
    _reimport_if_changed(con)
    return jsonify(faltas.compras(con))


@app.get("/api/deck/<int:deck_id>.json")
def api_deck(deck_id: int):
    payload = decks.deck_payload(get_con(), deck_id)
    if not payload:
        return jsonify({"error": "deck não encontrado"}), 404
    return jsonify(payload)


@app.get("/api/encomendas.json")
def api_encomendas():
    """A lista «Encomendas»: o que está a caminho, para que deck vai, e o que
    ainda falta encomendar (André, 2026-09-11)."""
    con = get_con()
    _reimport_if_changed(con)
    return jsonify({"editable": True, **pending.encomendas(con)})


@app.get("/api/encomendas/<set_id>.json")
def api_encomendas_edicao(set_id: str):
    """A grelha de uma edição do separador «Encomendas» (2026-09-17): a da
    Coleção, de Rara para cima, com o que vem a caminho por impressão."""
    con = get_con()
    _reimport_if_changed(con)
    return jsonify(pending.grelha(con, set_id.upper(), editable=True, image_mode="local"))


@app.post("/api/pending/arrive")
def api_pending_arrive():
    """Confirma a chegada: passa do `pending` para a coleção.

    Sem `id`, `ids`, `printing_id` nem `card_key`, dá entrada em tudo o que
    está aberto (o «Chegou tudo»); com `printing_id`, no que está aberto
    dessa impressão (o «Chegou» do tile do separador «Encomendas»); com
    `card_key`, no que está aberto dessa carta; com `ids`, só nessas linhas.
    A entrada passa pelo `collection.adjust`, portanto fica no log e dá para
    desfazer. Idempotente: a segunda chamada não encontra nada e dá 404.
    """
    data = request.get_json(silent=True) or {}
    pid = data.get("id")
    ids = data.get("ids")
    con = get_con()
    alvo = [int(i) for i in ids] if isinstance(ids, list) else (int(pid) if pid else None)
    try:
        feitas = pending.arrive(con, alvo, source="web",
                                card_key=data.get("card_key") or None,
                                printing_id=data.get("printing_id") or None)
    except collection.UnknownPrinting as exc:
        return jsonify({"error": str(exc)}), 404
    if not feitas:
        return jsonify({"error": "não havia nada por chegar"}), 404
    return jsonify({"arrived": feitas, "pending": pending.totals(con)})


@app.post("/api/encomenda")
def api_encomenda():
    """Os `+`/`−` das encomendas: `{card_key | printing_id, delta, deck?}`.

    Nasceram nos tiles dos decks (André, 2026-09-11) e desde 2026-09-17 vivem
    no separador «Encomendas», que manda sempre a `printing_id` do tile —
    ele é que escolhe a versão que comprou. Por `card_key` continua a
    responder (a CLI, e a impressão normal mais barata da carta).

    `delta > 0` regista mais cópias a caminho; `delta < 0` tira das linhas
    abertas mais recentes, e nunca vai abaixo de zero — sem nada a caminho é
    400, com a razão escrita. O `deck` é só a origem do clique, para o rasto.
    """
    data = request.get_json(silent=True) or {}
    try:
        delta = int(data.get("delta", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "delta inválido"}), 400
    if delta == 0:
        return jsonify({"error": "delta é zero"}), 400
    if not data.get("card_key") and not data.get("printing_id"):
        return jsonify({"error": "falta card_key ou printing_id"}), 400
    origem = "web" + (f" deck:{data['deck']}" if data.get("deck") else "")
    # `especial` vem do `+`/`−` da linha da Legend/Champion (2026-09-17): a
    # encomenda grava-se na versão especial mais barata, e o `−` só tira de
    # uma especial. Sem a chave, o comportamento de sempre (a normal).
    especial = data.get("especial")
    con = get_con()
    try:
        if delta > 0:
            res = pending.encomendar(con, data.get("card_key"), data.get("printing_id"),
                                     delta, source=origem, especial=bool(especial))
        else:
            res = pending.anular(con, data.get("card_key"), data.get("printing_id"),
                                 -delta, source=origem,
                                 especial=None if especial is None else bool(especial))
    except pending.SemEncomenda as exc:
        return jsonify({"error": str(exc)}), 400
    except collection.UnknownPrinting as exc:
        return jsonify({"error": str(exc)}), 404
    res["pending"] = pending.totals(con)
    return jsonify(res)


# --------------------------------------------------------------------------
# Locais das cópias (André, 2026-09-10): Coleção, deck, binder Decks/Venda
# --------------------------------------------------------------------------


@app.get("/api/local.json")
def api_local():
    con = get_con()
    _reimport_if_changed(con)
    return jsonify({"editable": True, "locais": locais.resumo(con)})


@app.get("/api/local/propor/<slug>.json")
def api_local_propor(slug: str):
    """A PROPOSTA de marcação de um deck. Não escreve nada — é para o ecrã.

    O que se grava é o que ele confirmar linha a linha, pelo `/api/local/marcar`.
    """
    con = get_con()
    _reimport_if_changed(con)
    return jsonify(locais.propor_deck(con, slug))


@app.post("/api/local/mover")
def api_local_mover():
    data = request.get_json(silent=True) or {}
    if not data.get("printing_id"):
        return jsonify({"error": "falta printing_id"}), 400
    try:
        res = locais.mover(get_con(), data["printing_id"], int(data.get("qty", 1)),
                           data.get("de") or locais.COLECAO, data.get("para") or "",
                           source="web", request_id=data.get("request_id"))
    except (locais.LocalInvalido, locais.SemCopias) as exc:
        return jsonify({"error": str(exc)}), 400
    except collection.UnknownPrinting as exc:
        return jsonify({"error": str(exc)}), 404
    return jsonify(res)


@app.post("/api/local/marcar")
def api_local_marcar():
    """Marca VÁRIAS cópias de uma vez — mas só as que vierem na lista.

    Um pedido sem `linhas` é 400 com a razão escrita, e não escreve nada. Lista
    vazia e lista ausente são a mesma coisa: não há nada confirmado. É a defesa
    do mtgvault de 2026-09-09, onde o registo gravou uma alocação calculada
    inteira — incluindo cartas que ele tinha dito não ter.
    """
    data = request.get_json(silent=True) or {}
    linhas = data.get("linhas")
    if not isinstance(linhas, list) or not linhas:
        return jsonify({"error": "o marcador só grava as linhas que confirmaste; "
                                 "esta lista veio vazia"}), 400
    try:
        res = locais.marcar(get_con(), linhas, data.get("para") or "",
                            de=data.get("de") or locais.COLECAO, source="web")
    except (locais.LocalInvalido, locais.SemCopias) as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(res)


@app.post("/api/local/desfazer-deck")
def api_local_desfazer_deck():
    """Desfaz um deck: tudo o que estava nele passa ao binder Decks/Venda."""
    slug = (request.get_json(silent=True) or {}).get("slug")
    if not slug:
        return jsonify({"error": "falta o slug do deck"}), 400
    con = get_con()
    if not con.execute("SELECT 1 FROM decks WHERE name = ?", (slug,)).fetchone():
        return jsonify({"error": f"não há deck chamado {slug!r}"}), 404
    return jsonify(locais.desfazer_deck(con, slug, source="web"))


@app.post("/api/local/undo")
def api_local_undo():
    res = locais.undo_last(get_con(), source="web")
    if not res:
        return jsonify({"error": "não havia movimentos para desfazer"}), 404
    return jsonify(res)


@app.post("/api/decks/order")
def api_decks_order():
    """Reordena. O primeiro id da lista passa a ser o deck principal."""
    ids = (request.get_json(silent=True) or {}).get("ids")
    if not isinstance(ids, list) or not ids:
        return jsonify({"error": "falta a lista de ids"}), 400
    con = get_con()
    decks.set_order(con, [int(i) for i in ids])
    return jsonify({"decks": decks.decks_index(con)})


def _reimport_if_changed(con) -> None:
    """Relê os .txt quando algum mexeu — não obriga a reiniciar o servidor."""
    files = {str(p): p.stat().st_mtime for p in config.DECKS_DIR.glob("*.txt")}
    known = {r["path"]: r["imported_at"] for r in con.execute("SELECT path, imported_at FROM decks")}
    if set(files) != set(known):
        decks.import_all(con, log=lambda *_: None)
        return
    for path, mtime in files.items():
        ts = known.get(path)
        if not ts or datetime.fromtimestamp(mtime, timezone.utc) > datetime.fromisoformat(ts):
            decks.import_all(con, log=lambda *_: None)
            return


# --------------------------------------------------------------------------
# API de escrita (só existe no modo edição)
# --------------------------------------------------------------------------


@app.post("/api/adjust")
def api_adjust():
    data = request.get_json(silent=True) or {}
    printing_id = data.get("printing_id")
    request_id = data.get("request_id")
    try:
        delta = int(data.get("delta", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "delta inválido"}), 400
    if not printing_id:
        return jsonify({"error": "falta printing_id"}), 400
    if delta == 0:
        return jsonify({"error": "delta é zero"}), 400

    try:
        res = collection.adjust(get_con(), printing_id, delta,
                                source="web", request_id=request_id)
    except collection.UnknownPrinting as exc:
        return jsonify({"error": str(exc)}), 404

    res["playset"] = _playset_for(printing_id)
    res.update(_locais_de(printing_id))
    return jsonify(res)


@app.post("/api/undo")
def api_undo():
    data = request.get_json(silent=True) or {}
    op_id = data.get("op_id")
    con = get_con()
    res = collection.undo_op(con, int(op_id), source="web") if op_id \
        else collection.undo_last(con, source="web")
    if not res:
        return jsonify({"error": "não havia nada para desfazer"}), 404
    res["playset"] = _playset_for(res["printing_id"])
    res.update(_locais_de(res["printing_id"]))
    return jsonify(res)


def _locais_de(printing_id: str) -> dict:
    """Quantas desta impressão estão na COLEÇÃO, e onde estão as outras.

    O `qty` da resposta é o total físico — é o que o `copies` guarda. A grelha
    da Coleção mostra outra coisa desde 2026-09-10 (só as que estão nos binders
    de coleção), por isso o número dela vai à parte e não como `qty`: são duas
    perguntas e trocá-las era pôr a barra a contar cartas que estão em decks.
    """
    from . import locais
    con = get_con()
    onde = (locais.por_local(con)).get(printing_id) or {}
    nomes = locais.nomes_dos_decks(con)
    return {
        "qty_colecao": onde.get(locais.COLECAO, 0),
        "locations": [{"loc": loc, "label": locais.rotulo(loc, nomes), "qty": n}
                      for loc, n in sorted(onde.items(),
                                           key=lambda kv: (kv[0] != locais.COLECAO,
                                                           kv[0]))],
    }


def _playset_for(printing_id: str) -> dict | None:
    """Devolve o estado da métrica de playset da carta lógica desta impressão.

    O `+` num tile mexe na contagem de playset da carta inteira, que pode estar
    a ser mostrada noutros tiles (outras edições, outras artes). O cliente usa
    isto para atualizar todos de uma vez.
    """
    con = get_con()
    row = con.execute(
        "SELECT card_key, type, is_token FROM catalog.printings WHERE printing_id = ?",
        (printing_id,),
    ).fetchone()
    if not row:
        return None
    owned = con.execute(
        "SELECT COALESCE(SUM(c.qty),0) AS n FROM copies c "
        "JOIN catalog.printings p ON p.printing_id = c.printing_id "
        "WHERE p.card_key = ?",
        (row["card_key"],),
    ).fetchone()["n"]
    return {
        "card_key": row["card_key"],
        "owned": owned,
        "target": metrics.playset_target(row["type"], bool(row["is_token"])),
    }


# --------------------------------------------------------------------------
# Arranque
# --------------------------------------------------------------------------


def lan_ip() -> str:
    """IP da interface por onde sai o tráfego (não abre ligação nenhuma)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def lan_ips() -> list[str]:
    """TODOS os endereços locais, o da rota por omissão primeiro.

    Mostrar só um engana quando a máquina tem Ethernet e Wi-Fi em sub-redes
    diferentes: o `lan_ip()` devolve o da Ethernet, mas o telemóvel está no
    Wi-Fi e não chega lá. Aconteceu — o endereço mudou de rede sem aviso e o
    site pareceu ter ido abaixo.

    Nem o `getaddrinfo(gethostname())` nem sondar a tabela de rotas com um
    socket UDP encontram a interface Wi-Fi quando a Ethernet tem métrica
    melhor; ambos foram testados e devolvem só a Ethernet. Por isso pergunta-se
    ao sistema.
    """
    principal = lan_ip()
    todos = {principal}

    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            todos.add(info[4][0])
    except OSError:
        pass

    cmd = (["ipconfig"] if sys.platform == "win32"
           else ["ip", "-4", "-o", "addr", "show"])
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=5,
                             errors="replace").stdout
        for m in re.finditer(r"(\d{1,3}(?:\.\d{1,3}){3})", out):
            todos.add(m.group(1))
    except (OSError, subprocess.SubprocessError):
        pass

    # Fora: loopback, link-local, máscaras, difusões e o que não é privado.
    def util(ip: str) -> bool:
        p = ip.split(".")
        if p[0] == "127" or ip.startswith("169.254.") or p[-1] in ("0", "255"):
            return False
        return (p[0] == "10"
                or (p[0] == "172" and 16 <= int(p[1]) <= 31)
                or (p[0] == "192" and p[1] == "168"))

    return [principal] + sorted(x for x in todos if x != principal and util(x))


def ascii_qr(url: str) -> str:
    """QR em texto para apontar o telemóvel. Nunca deve impedir o arranque."""
    try:
        import qrcode
    except ImportError:
        return "  (instala `qrcode` para veres o QR aqui: py -m pip install qrcode)"
    try:
        qr = qrcode.QRCode(border=2)
        qr.add_data(url)
        qr.make(fit=True)
        buf = io.StringIO()
        qr.print_ascii(out=buf, invert=True)
        out = buf.getvalue()
        out.encode(getattr(sys.stdout, "encoding", None) or "utf-8")  # a consola aguenta?
        return out
    except Exception:
        return "  (a consola não mostra o QR; usa o URL acima)"


def serve(host: str = "0.0.0.0", port: int = 8770) -> None:
    con = db.connect()
    empty = db.catalog_is_empty(con)
    con.close()
    if empty:
        print("O catálogo está vazio. Corre primeiro:  riftvault sync\n")

    # Só o acesso local (2026-09-17: o Tailscale saiu do PC e da recomendação).
    # O endereço da LAN fica aqui, na consola dele — nunca em nada que vá para
    # o GitHub Pages.
    ips = lan_ips()
    lan = f"http://{ips[0]}:{port}/"

    print("=" * 60)
    print("  riftvault — MODO EDIÇÃO (escreve no vault.db)")
    print("=" * 60)
    print(f"  Neste PC:            http://localhost:{port}/")
    print(f"  Telemóvel (casa):    {lan}")
    for extra in ips[1:]:
        print(f"     ou:               http://{extra}:{port}/")
    if len(ips) > 1:
        print("     (redes diferentes — usa a que o telemóvel alcança)")
    print()
    print(ascii_qr(lan))
    print("  Sem palavra-passe: quem chegar ao URL pode escrever na coleção.")
    print("  Não abras este porto no router.")
    print("  Ctrl+C para parar.")
    print("=" * 60)

    app.run(host=host, port=port, threaded=True, debug=False, use_reloader=False)

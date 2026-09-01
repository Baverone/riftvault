"""Modo edição: servidor local que serve o site e escreve no vault.db.

Faz bind em 0.0.0.0 e mostra o URL da rede local + QR ao arrancar, para o
André mexer nas cartas com o telemóvel na mão.

O frontend é exatamente o mesmo do modo publicado. A única diferença é o flag
`editable` no payload e a existência dos endpoints de escrita.
"""

from __future__ import annotations

import io
import socket
import subprocess
import sys
from datetime import datetime, timezone

from flask import Flask, g, jsonify, redirect, request, send_from_directory

from . import collection, config, db, decks, faltas, metrics

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


@app.get("/")
def index():
    return send_from_directory(config.WEB_DIR, "index.html")


@app.get("/<path:name>")
def web_asset(name: str):
    if (config.WEB_DIR / name).is_file():
        return send_from_directory(config.WEB_DIR, name)
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
    return jsonify(metrics.set_payload(get_con(), set_id.upper(),
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


@app.get("/api/faltas.json")
def api_faltas():
    con = get_con()
    _reimport_if_changed(con)
    return jsonify(faltas.payload(con))


@app.get("/api/deck/<int:deck_id>.json")
def api_deck(deck_id: int):
    payload = decks.deck_payload(get_con(), deck_id)
    if not payload:
        return jsonify({"error": "deck não encontrado"}), 404
    return jsonify(payload)


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
    return jsonify(res)


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
    """IP desta máquina na rede local (não abre ligação nenhuma de facto)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def tailscale_ip() -> str | None:
    """Endereço na tailnet, se o Tailscale estiver a correr.

    É a forma recomendada de chegar ao servidor de fora de casa: rede privada
    entre os dispositivos do André, sem abrir nada à internet. Sem isto, o
    servidor ficaria acessível a qualquer pessoa — não há autenticação nenhuma.
    """
    try:
        out = subprocess.run(["tailscale", "ip", "-4"], capture_output=True,
                             text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    ip = (out.stdout or "").strip().splitlines()
    return ip[0].strip() if ip and ip[0].strip() else None


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

    lan = f"http://{lan_ip()}:{port}/"
    ts = tailscale_ip()
    # Fora de casa é o endereço da tailnet que serve; o da LAN não chega lá.
    url = f"http://{ts}:{port}/" if ts else lan

    print("=" * 60)
    print("  riftvault — MODO EDIÇÃO (escreve no vault.db)")
    print("=" * 60)
    print(f"  Neste PC:            http://localhost:{port}/")
    print(f"  Telemóvel (casa):    {lan}")
    if ts:
        print(f"  Telemóvel (qualquer rede): {url}   [Tailscale]")
    else:
        print("  Telemóvel (fora de casa): instala o Tailscale nos dois")
        print("                            aparelhos — tailscale.com/download")
    print()
    print(ascii_qr(url))
    print("  Sem palavra-passe: quem chegar ao URL pode escrever na coleção.")
    print("  Não abras este porto no router.")
    print("  Ctrl+C para parar.")
    print("=" * 60)

    app.run(host=host, port=port, threaded=True, debug=False, use_reloader=False)

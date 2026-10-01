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

from . import (a_mais, a_subir, collection, config, db, decks, faltas, faltas_foil,
               foil, locais, metrics, pending, principal, proprias, rotas_conta,
               runas_vista, selado, venda)

app = Flask(__name__, static_folder=None)


def get_con():
    """A base DESTE pedido — a do dono da sessão, e só a dele.

    Uma ligação por pedido: os objetos do sqlite3 não atravessam threads.

    O `user_id` vem do `g.riftvault_user`, que o `rotas_conta._antes` põe a
    partir do cookie. É EXPLÍCITO de propósito: com a porta das contas aberta,
    cada coleção é um ficheiro seu (`data/users/<slug>/vault.db`), e por isso não
    existe caminho de código que abra a base de outra pessoa — não é um `WHERE
    user_id` que se possa esquecer, é um ficheiro que não se chega a abrir.

    De CASA e sem sessão o `g.riftvault_user` é `None` e isto é o `db.connect()`
    de sempre: um dono só, o André, tudo como ontem.

    DE FORA E SEM SESSÃO REBENTA (2026-10-01), e é o segundo defeito desta
    correcção. O `db.connect(user_id=None)` cai no `utilizador.atual()`, que
    devolve **1** — ou seja, um GET anónimo pelo túnel abria a base DELE e
    servia-a sem a privacidade ser consultada uma única vez. A regra escrita no
    desenho («uma consulta sem dono deve rebentar») não se cumpria aqui porque
    o `connect` punha sempre um número.

    Quem responde a este caso é o guarda do `rotas_conta._antes`, com um 401
    antes de a rota correr. Isto é o cinto a par dos suspensórios: se um dia
    alguém acrescentar um caminho que escape ao guarda, não há leitura
    silenciosa da coleção dele — há uma excepção com o nome do problema.
    """
    if "con" not in g:
        uid = g.get("riftvault_user")
        if uid is None and not g.get("de_casa", True):
            raise rotas_conta.SemSessao(
                "este pedido vem de fora e não trouxe sessão: não há coleção "
                "nenhuma para abrir. Entra primeiro.")
        g.con = db.connect(user_id=uid)
    return g.con


@app.teardown_appcontext
def _close(_exc):
    con = g.pop("con", None)
    if con is not None:
        con.close()
    rotas_conta.fechar_auth()


# As rotas de entrada/registo/conta e o guarda que protege todas as outras. Uma
# linha, num ficheiro à parte: são 40 rotas escritas ao longo de um mês e
# enfiar-lhes autenticação por dentro era mexer em todas.
rotas_conta.ligar(app)


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


@app.get("/api/runas.json")
def api_runas():
    """O bloco «Runas — 12 de cada» no fim da grelha da Coleção (2026-09-19):
    o contador dele por runa, com a referência do que a coleção sabe ao lado
    — não conta para nada. Um URL só, para as cinco edições — as runas são
    as mesmas seis."""
    return jsonify(runas_vista.payload(get_con(), image_mode="local", editable=True))


@app.post("/api/runas/ajustar")
def api_runas_ajustar():
    """Os `+`/`−` do bloco das runas: `{card_key, delta}`.

    Mexe SÓ no contador dele (`rune_counter`) — nada de `copies`, `ops`,
    `pending` ou locais; nenhuma conta do site lê este número. Nunca vai
    abaixo de zero: um `−` a 0 devolve 0. Um `card_key` que não seja runa do
    catálogo é 404.
    """
    data = request.get_json(silent=True) or {}
    try:
        delta = int(data.get("delta", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "delta inválido"}), 400
    if delta == 0:
        return jsonify({"error": "delta é zero"}), 400
    if not data.get("card_key"):
        return jsonify({"error": "falta card_key"}), 400
    try:
        return jsonify(runas_vista.ajustar(get_con(), data["card_key"], delta))
    except runas_vista.RunaDesconhecida as exc:
        return jsonify({"error": str(exc)}), 404


@app.post("/api/foil/ajustar")
def api_foil_ajustar():
    """Os `+`/`−` do contador de FOIL de um tile (2026-09-22):
    `{printing_id, delta}`.

    Mexe SÓ na coluna `copies.qty_foil` — as cópias NORMAIS (`copies.qty`) não
    mexem, e por isso nenhuma conta do site mexe. O FOIL SOMA-SE às normais
    (2026-09-26), não é uma fatia delas: o `+` acrescenta uma foil e o total da
    impressão sobe. Trava em 0 e no `foil.LIMITE` (sanidade), sem erro. Uma
    impressão fora do âmbito (`foil.raridades`/`foil.edicoes_fora`) é 400; uma
    que não exista é 404.
    """
    data = request.get_json(silent=True) or {}
    try:
        delta = int(data.get("delta", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "delta inválido"}), 400
    if delta == 0:
        return jsonify({"error": "delta é zero"}), 400
    if not data.get("printing_id"):
        return jsonify({"error": "falta printing_id"}), 400
    try:
        return jsonify(foil.ajustar(get_con(), data["printing_id"], delta, source="web"))
    except collection.UnknownPrinting as exc:
        return jsonify({"error": str(exc)}), 404
    except foil.ForaDoAmbito as exc:
        return jsonify({"error": str(exc)}), 400


# --------------------------------------------------------------------------
# «Produto Selado» (2026-09-25): o que HÁ, o que TEM e o que NÃO TEM de
# displays, cases, decks, bundles e Proving Grounds. Ver `selado.py`.
# --------------------------------------------------------------------------


@app.get("/api/selado.json")
def api_selado():
    return jsonify(selado.payload(get_con(), editable=True))


@app.post("/api/selado/ajustar")
def api_selado_ajustar():
    """Os `+`/`−` de um produto selado: `{product_id, delta}`.

    Escreve SÓ na `sealed_copies` — o `copies`, a `ops`, os locais e o valor
    da Coleção não mexem, e nenhuma conta do site lê este número. Nunca vai
    abaixo de zero. Um produto que não esteja na lista (API + `selado.extra`)
    é 404.
    """
    data = request.get_json(silent=True) or {}
    try:
        delta = int(data.get("delta", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "delta inválido"}), 400
    if delta == 0:
        return jsonify({"error": "delta é zero"}), 400
    if not data.get("product_id"):
        return jsonify({"error": "falta product_id"}), 400
    con = get_con()
    try:
        selado.ajustar(con, data["product_id"], delta, source="web")
    except selado.ProdutoDesconhecido as exc:
        return jsonify({"error": str(exc)}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(selado.payload(con, editable=True))


@app.post("/api/selado/preco")
def api_selado_preco():
    """O preço do CARDMARKET de um produto selado, à mão: `{product_id, eur}`.

    O preço da aba vem do CardTrader, e há produtos sem oferta nenhuma lá — a
    linha lia «—», que se lê como «não existe». O Cardmarket responde 403 a
    pedidos automáticos, por isso o número é dele, como o Trend da Venda.

    Escreve SÓ na `sealed_price`: o `copies`, a `ops`, os locais e o valor da
    Coleção não mexem. `eur` vazio APAGA. Um produto fora da lista é 404.
    """
    data = request.get_json(silent=True) or {}
    if not data.get("product_id"):
        return jsonify({"error": "falta product_id"}), 400
    con = get_con()
    try:
        selado.definir_preco(con, data["product_id"], data.get("eur"),
                             source="web")
    except selado.ProdutoDesconhecido as exc:
        return jsonify({"error": str(exc)}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(selado.payload(con, editable=True))


# --------------------------------------------------------------------------
# «Venda» (2026-09-25): a conta de uma venda em curso, com o Trend do
# Cardmarket metido à mão. Ver `venda.py`.
# --------------------------------------------------------------------------


@app.get("/api/venda.json")
def api_venda():
    return jsonify(venda.payload(get_con(), editable=True))


@app.get("/api/venda/procurar")
def api_venda_procurar():
    """`?q=defy` -> impressões para juntar à venda, as que ele tem primeiro.

    Só existe no modo edição: no site publicado a venda é de leitura e não há
    quem responda. É a única maneira de juntar uma carta de uma edição que não
    está aberta na Coleção.
    """
    return jsonify({"items": venda.procurar(get_con(), request.args.get("q", ""))})


@app.post("/api/venda/linha")
def api_venda_linha():
    """Juntar ou tirar cópias da venda: `{printing_id, delta}`.

    **Não mexe no `copies` nem em conta nenhuma** — é uma lista de intenção. Um
    `−` numa carta que não está na venda é 400.
    """
    data = request.get_json(silent=True) or {}
    try:
        delta = int(data.get("delta", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "delta inválido"}), 400
    if delta == 0:
        return jsonify({"error": "delta é zero"}), 400
    if not data.get("printing_id"):
        return jsonify({"error": "falta printing_id"}), 400
    con = get_con()
    try:
        venda.juntar(con, data["printing_id"], delta, source="web")
    except collection.UnknownPrinting as exc:
        return jsonify({"error": str(exc)}), 404
    except venda.SemLinha as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(venda.payload(con, editable=True))


@app.post("/api/venda/trend")
def api_venda_trend():
    """O TREND DO CARDMARKET de uma impressão: `{printing_id, eur}`.

    É o número que ELE lê na página do Cardmarket e escreve na linha. `eur`
    vazio ou `null` apaga o Trend guardado. Nunca se grava aqui um preço do
    CardTrader — são fontes diferentes, e a conta é feita com esta.
    """
    data = request.get_json(silent=True) or {}
    if not data.get("printing_id"):
        return jsonify({"error": "falta printing_id"}), 400
    bruto = data.get("eur")
    if bruto is None or str(bruto).strip() == "":
        cents = None
    else:
        try:
            cents = round(float(str(bruto).replace(",", ".").replace("€", "").strip()) * 100)
        except (TypeError, ValueError):
            return jsonify({"error": f"não percebi o preço {bruto!r}"}), 400
    con = get_con()
    try:
        venda.guardar_trend(con, data["printing_id"], cents, source="web")
    except collection.UnknownPrinting as exc:
        return jsonify({"error": str(exc)}), 404
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(venda.payload(con, editable=True))


@app.post("/api/venda/limpar")
def api_venda_limpar():
    """Esvazia a venda em curso — ou só as linhas de uma `origem`.

    Com `{"origem": "deck:<slug>"}` tira de uma vez as que vieram de desfazer
    ou despromover um deck (2026-09-27) e deixa as que ele marcou à mão.
    """
    data = request.get_json(silent=True) or {}
    con = get_con()
    n = venda.limpar(con, origem=data.get("origem") or None)
    return jsonify({"limpas": n, **venda.payload(con, editable=True)})


@app.post("/api/venda/vender")
def api_venda_vender():
    """«Marcar como vendidas»: `{confirmar: true}`.

    É o ÚNICO sítio desta secção que baixa cópias, e não é automático — sem o
    `confirmar` devolve 409 com o número de cópias em jogo, para o ecrã pedir
    confirmação. Cada linha passa pelo `collection.adjust` (fica na `ops`, dá
    para desfazer) e escreve no `sale_log`.
    """
    data = request.get_json(silent=True) or {}
    con = get_con()
    try:
        res = venda.vender(con, confirmar=bool(data.get("confirmar")), source="web")
    except venda.PrecisaConfirmar as exc:
        return jsonify({"error": str(exc)}), 409
    except venda.VendaVazia as exc:
        return jsonify({"error": str(exc)}), 400
    # O resultado da venda vai numa chave própria: o `payload` traz o `totals`
    # da venda em curso, que a partir de agora está vazia.
    return jsonify({"vendida": res, **venda.payload(con, editable=True)})


@app.get("/api/history.json")
def api_history():
    limit = min(int(request.args.get("limit", 30)), 500)
    return jsonify({"ops": collection.history(get_con(), limit)})


@app.get("/api/decks.json")
def api_decks():
    con = get_con()
    _reimport_if_changed(con)
    # `decks.ordem` (2026-09-21): a lista do config manda na prioridade e o
    # cliente esconde os botões de reordenar quando ela existe. Aplica-se
    # também aqui, e não só na importação: uma lista mudada no config (e o
    # servidor relançado) tem de valer sem nenhum .txt ter mexido. Só escreve
    # quando difere.
    decks.aplicar_ordem(con, log=lambda *_: None)
    return jsonify({"editable": True, "decks": decks.decks_index(con),
                    "rules": decks.rules(), "ordem_fixa": decks.ordem_fixa(),
                    # Só versões base (2026-09-21): o cliente diz-o ao lado
                    # dos `+`/`−` das cópias próprias.
                    "so_base": decks.so_base(),
                    # A regra de raridade (2026-09-24): a partir de que
                    # raridade um deck se pode servir da Coleção sem aviso.
                    "raridade_colecao": decks.raridade_da_colecao(),
                    # O DECK PRINCIPAL (2026-09-27): quem é, e a partir de
                    # quanto uma cópia própria dele vai à Venda quando deixar
                    # de o ser.
                    "principal": principal.estado(con)})


@app.post("/api/decks/montar")
def api_decks_montar():
    """MONTAR/DESMONTAR um deck (2026-09-24): `{slug, montado}`.

    Escreve `decks.montados` no `riftvault_config.json` — *"o estado é do
    config, não só da base, para não se perder"* — e devolve o índice já
    recalculado. Um deck desmontado deixa de consumir a Coleção na hora.

    Passa pelo `principal.montar` (2026-09-27): desmontar o DECK PRINCIPAL
    despromove-o e manda as cópias próprias dele que valham o mínimo para a
    Venda — é o *"se eu 'desfazer' o deck"* do pedido. `movimento` diz o que
    foi e o que ficou; entrar na Venda não é vender.
    """
    data = request.get_json(silent=True) or {}
    if not data.get("slug"):
        return jsonify({"error": "falta o slug do deck"}), 400
    con = get_con()
    _reimport_if_changed(con)
    try:
        res = principal.montar(con, data["slug"], bool(data.get("montado")))
    except decks.DeckDesconhecido as exc:
        return jsonify({"error": str(exc)}), 404
    return jsonify({**res, "decks": decks.decks_index(con)})


@app.post("/api/decks/principal")
def api_decks_principal():
    """O DECK PRINCIPAL (2026-09-27): `{slug}` — ou `{slug: null}` para limpar.

    Escreve `decks.principal` no config (e garante o deck em `decks.montados`:
    o principal é sempre montado). O deck que SAI é despromovido — as cópias
    próprias dele que valham `decks.venda_minimo_cents` ganham uma linha na
    Venda, marcada com a origem. **Nada sai do `proprio:<slug>` e nada se
    vende**; as de menos de 0,50 € ficam, e o `movimento` diz quantas são.
    """
    data = request.get_json(silent=True) or {}
    con = get_con()
    _reimport_if_changed(con)
    try:
        res = principal.definir(con, data.get("slug") or None)
    except decks.DeckDesconhecido as exc:
        return jsonify({"error": str(exc)}), 404
    return jsonify({**res, "decks": decks.decks_index(con)})


@app.post("/api/proprias/ajustar")
def api_proprias_ajustar():
    """Os `+`/`−` das CÓPIAS PRÓPRIAS de um deck (2026-09-21):
    `{slug, printing_id, delta, request_id?}`.

    Escreve no `copies` E no local `proprio:<slug>` de uma vez — a Coleção
    fica exactamente onde estava. Só impressões que sirvam o deck (com
    `decks.so_base`, só a base; 400 se não for). Um `−` a zero devolve 0 sem
    erro. Deck desconhecido: 404.
    """
    data = request.get_json(silent=True) or {}
    try:
        delta = int(data.get("delta", 0))
    except (TypeError, ValueError):
        return jsonify({"error": "delta inválido"}), 400
    if delta == 0:
        return jsonify({"error": "delta é zero"}), 400
    if not data.get("printing_id"):
        return jsonify({"error": "falta printing_id"}), 400
    if not data.get("slug"):
        return jsonify({"error": "falta o slug do deck"}), 400
    con = get_con()
    _reimport_if_changed(con)
    try:
        res = proprias.ajustar(con, data["slug"], data["printing_id"], delta, source="web",
                               request_id=data.get("request_id"))
    except (collection.UnknownPrinting, proprias.DeckDesconhecido) as exc:
        return jsonify({"error": str(exc)}), 404
    except proprias.NaoServe as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(res)


@app.get("/api/faltas_edicao.json")
def api_faltas_edicao():
    """O separador «Faltas» (2026-09-15, fim da tarde): por edição, em DUAS
    METADES — as NORMAIS em quatro blocos (master set, sobrenumeradas, alt art,
    promos) e as FOILS à parte (2026-09-27, *"as foils nao sao faltas, sao
    apenas complemento e indicativo"*). Lê os locais, o pendente e a contagem
    de foil; não lê os decks. Quem compõe as duas metades é o
    `faltas_foil.payload_completo` — a das normais vem do
    `faltas_edicao.payload` tal e qual, e é isso que garante que os números
    delas não mexem."""
    return jsonify(faltas_foil.payload_completo(get_con()))


@app.get("/api/a_mais.json")
def api_a_mais():
    """O separador «A mais» (2026-09-17): por edição, o excedente acima do alvo
    e as cartas que os decks libertaram. Relê as listas primeiro, porque o
    bloco das libertadas vive do registo que o `import_all` escreve."""
    con = get_con()
    _reimport_if_changed(con)
    return jsonify(a_mais.payload(con))


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
    # `foil` (2026-09-27) escolhe o acabamento: sem a chave entram os dois, e
    # cada linha vai para o contador dela — uma foil para o `copies.qty_foil`.
    e_foil = data.get("foil")
    try:
        feitas = pending.arrive(con, alvo, source="web",
                                card_key=data.get("card_key") or None,
                                printing_id=data.get("printing_id") or None,
                                foil=None if e_foil is None else bool(e_foil))
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

    Desde 2026-09-27 responde também aos `+`/`−` do separador «Faltas», que é a
    terceira casa dos mesmos botões — a mesma rota e a mesma tabela, para o
    número ser UM SÓ nas duas vistas. O `foil` diz o acabamento: com `true` a
    encomenda é de uma cópia FOIL (o `+` da metade das foils) e quando chegar
    soma ao `copies.qty_foil`; no `−`, `true`/`false` só tiram de linhas do
    mesmo acabamento, e sem a chave tira-se de qualquer uma (é o que a CLI
    antiga faz).
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
    e_foil = data.get("foil")
    con = get_con()
    try:
        if delta > 0:
            res = pending.encomendar(con, data.get("card_key"), data.get("printing_id"),
                                     delta, source=origem, especial=bool(especial),
                                     foil=bool(e_foil))
        else:
            res = pending.anular(con, data.get("card_key"), data.get("printing_id"),
                                 -delta, source=origem,
                                 especial=None if especial is None else bool(especial),
                                 foil=None if e_foil is None else bool(e_foil))
    except pending.SemEncomenda as exc:
        return jsonify({"error": str(exc)}), 400
    except foil.ForaDoAmbito as exc:
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
    try:
        decks.set_order(con, [int(i) for i in ids])
    except decks.OrdemFixa as e:
        return jsonify({"error": str(e)}), 409
    return jsonify({"decks": decks.decks_index(con)})


def _reimport_if_changed(con) -> None:
    """Relê os .txt quando algum mexeu — não obriga a reiniciar o servidor."""
    files = {str(p): p.stat().st_mtime for p in config.decks_dir(con).glob("*.txt")}
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

    O `qty_colecao` sai do MESMO funil que a grelha (`locais.na_colecao`), e
    desde 2026-09-26 isso importa: com o `foil.conta_para_coleccao` ligado, o
    número da grelha é `normais + foils`. Tirá-lo do `por_local` — que conta
    só as normais, porque uma foil não tem local — fazia o crachá perder as
    foils no primeiro `+`/`−` (de «6/3» para «4/3» em vez de «7/3»).
    O `locations` continua a vir do `por_local`: onde estão as cópias é
    pergunta das NORMAIS.
    """
    from . import locais
    con = get_con()
    onde = (locais.por_local(con)).get(printing_id) or {}
    nomes = locais.nomes_dos_decks(con)
    return {
        "qty_colecao": locais.na_colecao(con).get(printing_id, 0),
        # As cópias FOIL desta impressão. São uma contagem à parte do `qty` — o
        # `−` da grelha não lhes toca (2026-09-26) — e o tile precisa delas para
        # escrever «3 normais · 3 foil = 6» e para saber se o `−` pode estar
        # ligado (o `qtyNormais` do `app.js`).
        "foil": collection.get_foil(con, printing_id),
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


def _recusar_user_fixo() -> None:
    """Com as contas abertas, o `RIFTVAULT_USER` no ambiente é uma armadilha.

    Essa variável é do CLI e das medições: fixa o `utilizador.atual()` para o
    PROCESSO inteiro. Num servidor `threaded` com contas abertas, isso punha
    TODOS os pedidos a escrever na coleção de uma pessoa só — a do valor da
    variável — por muito que cada um tenha entrado com a sua. Recusa-se a
    arrancar em vez de servir assim.
    """
    import os

    from . import multi

    if not os.environ.get("RIFTVAULT_USER"):
        return
    if not multi.aberto(config.load()):
        return
    raise SystemExit(
        "NÃO ARRANQUEI: as contas estão abertas e o RIFTVAULT_USER está "
        f"definido (={os.environ['RIFTVAULT_USER']}). Essa variável fixa o dono "
        "para o processo inteiro e faria todos os pedidos escrever na mesma "
        "coleção. Tira-a do ambiente e arranca outra vez.")


def _aviso_das_contas() -> list[str]:
    """As duas linhas do banner que dependem de a porta estar aberta."""
    from . import multi

    if not multi.aberto(config.load()):
        # A primeira linha vale para a REDE DE CASA, e só. A segunda é de
        # 2026-10-01: lida sozinha, a primeira dizia que o túnel estava escancarado
        # — e desde essa data não está, porque quem manda em «é preciso entrar?» é
        # a ORIGEM do pedido e não esta porta. Ver docs/origem-do-pedido.md.
        return ["  Sem palavra-passe: quem chegar ao URL pode escrever na coleção.",
                "  Isso é na REDE DE CASA. De fora (o túnel) entrar é sempre",
                "  obrigatório, mesmo para ver. Não abras este porto no router."]
    # Com contas, a rede de casa já não é fronteira: há coleções de outras
    # pessoas aqui dentro e a escrita exige entrar. Ver docs/contas-e-autenticacao.md.
    return ["  CONTAS ABERTAS: escrever exige entrar, e cada um só mexe na sua.",
            "  Quem só espreita não precisa deste PC — os sites públicos estão",
            "  no GitHub. Não abras este porto no router: o acesso de fora é",
            "  pelo túnel da Cloudflare."]


def serve(host: str = "0.0.0.0", port: int = 8770) -> None:
    _recusar_user_fixo()

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
    for linha in _aviso_das_contas():
        print(linha)
    print("  Ctrl+C para parar.")
    print("=" * 60)

    app.run(host=host, port=port, threaded=True, debug=False, use_reloader=False)

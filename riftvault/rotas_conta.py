"""As rotas de entrada, registo e conta — e o guarda que protege as outras.

Vive num ficheiro à parte e liga-se ao `server.py` com **uma linha**
(`rotas_conta.ligar(app)`). É de propósito: o `server.py` tem 937 linhas e 40
rotas escritas ao longo de um mês, e enfiar autenticação por dentro delas era
mexer em todas. Aqui há um `before_request` que passa à frente de todas, e um
blueprint com as que são novas.

O QUE O GUARDA FAZ, POR ORDEM
    1. resolve a sessão a partir do cookie (e adia-lhe a expiração);
    2. decide DE QUEM são os dados deste pedido (`g.riftvault_user`);
    3. num pedido que ESCREVE, exige sessão e exige CSRF;
    4. e é o `get_con()` do `server.py` que abre a base desse dono — e só dessa.

PORQUE É QUE ISTO É SEGURO POR CONSTRUÇÃO, E NÃO POR DISCIPLINA
    A `0-multi-utilizador-1` pôs cada coleção num FICHEIRO seu
    (`data/users/<slug>/vault.db`). O servidor só abre a base do `g.riftvault_user`,
    que num pedido de escrita é sempre o dono da sessão. Não existe caminho de
    código que abra a base de outra pessoa para escrever: não é um `WHERE
    user_id` que se pode esquecer, é um ficheiro que não se chega a abrir. As 20
    rotas de escrita herdam isto sem uma linha cada.

A DECISÃO DA LAN, E O QUE A DECIDIU (2026-09-29)
    Hoje o 8770 serve a rede de casa sem autenticação nenhuma, e está escrito
    no CLAUDE.md que «é aceitável na LAN». Com coleções de amigos lá dentro
    deixa de ser: o risco já não é só dele.

    Podia-se pensar em confiar no endereço de quem pede — «se vem de casa, é
    ele». **Não se pode, e a razão é concreta:** o túnel da Cloudflare corre
    `cloudflared tunnel run --url http://localhost:8770`, ou seja **todo o
    tráfego da internet chega ao Flask como `127.0.0.1`**. Uma regra que
    confiasse no loopback dava a identidade do André a qualquer visitante. Por
    isso **não há atalho por endereço, nem por loopback, nem por sub-rede** — em
    sítio nenhum deste ficheiro se lê o `remote_addr` para decidir quem é
    alguém.

    O que fica, e é simples de dizer:
      * porta FECHADA (`multi.aberto: false`, o de hoje): um dono só, sem
        autenticação, tudo exactamente como ontem. Não há dados de terceiros
        para proteger, e ele não fica fechado fora da sua própria app.
      * porta ABERTA: toda a escrita precisa de sessão e de CSRF, ele incluído.
        Entra uma vez com o Discord e a sessão dura 30 dias — é o mesmo que já
        faz com o telemóvel.
    E o `riftvault multi --verificar` **recusa abrir** enquanto a conta DELE não
    estiver ligada a um fornecedor: assim nunca se abre a porta com ele do lado
    de fora.
"""

from __future__ import annotations

import json
from urllib.parse import urlsplit

from flask import Blueprint, current_app, g, jsonify, redirect, request

from . import auth, config

bp = Blueprint("conta", __name__)

#: Os métodos que mudam alguma coisa. Um `GET` nunca escreve nesta app.
ESCREVE = frozenset({"POST", "PUT", "PATCH", "DELETE"})

#: Caminhos que têm de funcionar sem sessão de DONO, senão não há por onde
#: entrar. O `/api/conta/registar` está aqui porque é ele que CRIA o dono: no
#: momento em que corre, a sessão existe mas ainda não tem `user_id`, e o guarda
#: genérico recusava-a. Tem a protecção dele por dentro (exige a sessão
#: pré-registo e exige o CSRF) — ver `registar()`.
ABERTOS = ("/entrar", "/sair", "/api/conta.json", "/api/conta/registar")

#: Tecto do corpo de um pedido. Quase tudo o que a app manda é um `printing_id`
#: e um delta (~80 bytes), mas o `/api/local/marcar` manda uma LISTA de linhas —
#: marcar uma coleção inteira à mão são centenas de entradas, e 64 KB ficava
#: apertado. 256 KB é folgado para isso e continua a ser nada. Sem tecto nenhum,
#: um corpo de 2 GB é um ataque de uma linha.
CORPO_MAXIMO = 256 * 1024


# --------------------------------------------------------------------------
# Ligar ao servidor
# --------------------------------------------------------------------------


def ligar(app) -> None:
    """Uma linha no `server.py`. Põe o guarda e as rotas novas."""
    app.config.setdefault("MAX_CONTENT_LENGTH", CORPO_MAXIMO)
    app.register_blueprint(bp)
    app.before_request(_antes)
    app.after_request(_depois)


def _cfg() -> dict:
    return config.load()


def _porta_aberta() -> bool:
    from . import multi
    return multi.aberto(_cfg())


def _auth_con():
    """A ligação ao `auth.db`, uma por pedido."""
    if "auth_con" not in g:
        g.auth_con = auth.abrir()
    return g.auth_con


def fechar_auth(_exc=None) -> None:
    """Fecha o que este pedido abriu. Chamado pelo `teardown` do `server.py`."""
    con = g.pop("auth_con", None)
    if con is not None:
        con.close()
    # E devolve o `utilizador.atual()` ao que era neste fio (ver `_dono_do_fio`).
    ctx = g.pop("ctx_dono", None)
    if ctx is not None:
        ctx.__exit__(None, None, None)


def _dono_do_fio(uid: int | None) -> None:
    """Diz ao `utilizador.atual()` quem é o dono DESTE pedido.

    O `get_con()` já passa o `user_id` explícito, e é ele que manda. Isto é o
    cinto a par dos suspensórios: há código fundo que chama `db.connect()` sem
    argumentos, e sem isto cairia no utilizador 1. O `utilizador.como()` é um
    `ContextVar`, por isso vale só neste fio — com o servidor em `threaded=True`
    uma variável global punha dois pedidos simultâneos a ver o dono um do outro.
    """
    if uid is None:
        return
    from . import utilizador
    ctx = utilizador.como(uid)
    ctx.__enter__()
    g.ctx_dono = ctx


# --------------------------------------------------------------------------
# O guarda
# --------------------------------------------------------------------------


def _resposta(mensagem: str, codigo: int):
    """Um erro com a mensagem nas DUAS chaves, e é de propósito.

    O resto da app responde `{"error": …}` e os dezassete `fetch` do `app.js`
    lêem `res.error`. Se aqui só viesse `erro`, uma sessão que expirasse a meio
    de uma edição mostrava «HTTP 401» em vez da frase em português — o utilizador
    via um código e não o que fazer. Manda-se as duas até o cliente falar só uma.
    """
    return jsonify({"erro": mensagem, "error": mensagem}), codigo


def _antes():
    """Corre antes de TODAS as rotas, as antigas incluídas."""
    g.sessao = None
    g.riftvault_user = None
    g.somente_leitura = False

    if not _porta_aberta():
        # O de hoje: um dono só, sem autenticação. O `None` faz o
        # `db.connect(user_id=None)` cair no utilizador da sessão do processo,
        # que é o 1 — exactamente o comportamento de ontem.
        return None

    sid = request.cookies.get(auth.COOKIE)
    con = _auth_con()
    sess = auth.sessao(con, sid)
    if sess is not None:
        g.sessao = sess
        if sess.get("user_id"):
            g.riftvault_user = int(sess["user_id"])
            # Mexeu-se: a sessão dura enquanto se usa. O `visto_em` faz isto
            # escrever no máximo uma vez por hora — uma página da Coleção são
            # dezenas de pedidos e não vale um `UPDATE` cada.
            auth.tocar(con, sid, _cfg(), sess.get("visto_em"))

    # Um pedido pode nomear OUTRA pessoa — o site de leitura de um amigo. Aí os
    # dados são dele e a resposta é sempre só de leitura.
    alvo = _dono_pedido()
    if alvo is not None:
        g.riftvault_user = alvo["user_id"]
        g.somente_leitura = alvo["user_id"] != (
            g.sessao.get("user_id") if g.sessao else None)

    _dono_do_fio(g.riftvault_user)

    if request.method in ESCREVE:
        return _guardar_escrita()
    return None


def _guardar_escrita():
    """Um pedido que escreve: sessão, CSRF, e ser dono do que se escreve."""
    if request.path.startswith(ABERTOS):
        # As rotas de entrada têm a protecção delas (o `state` do OAuth).
        return None

    if g.sessao is None or not g.sessao.get("user_id"):
        return _resposta(
            "precisas de entrar para mexer na coleção.", 401)

    if not auth.csrf_valido(g.sessao, _csrf_enviado()):
        # Isto é o que impede outro site de fazer o browser dele escrever aqui.
        return _resposta(
            "o pedido não trazia a marca de segurança (CSRF). Recarrega a "
            "página e tenta outra vez.", 403)

    if g.somente_leitura:
        return _resposta(
            "esta coleção não é tua — aqui é só de leitura.", 403)

    return None


def _csrf_enviado() -> str | None:
    """O token vem num cabeçalho. Não vem num cookie, de propósito.

    Num cookie seria enviado pelo browser junto com o pedido falso, que é
    exactamente o que o CSRF tenta impedir. Num cabeçalho só o nosso JavaScript
    o pode pôr, porque só ele o leu do payload.
    """
    do_cabecalho = request.headers.get("X-CSRF-Token")
    if do_cabecalho:
        return do_cabecalho
    # No corpo também serve, para um `<form>` sem JavaScript poder escrever.
    if request.is_json:
        return (request.get_json(silent=True) or {}).get("csrf")
    return request.form.get("csrf")


def _dono_pedido() -> dict | None:
    """Este pedido nomeia outra pessoa? (`/u/<slug>/…` ou `<slug>.rift.…`)

    Devolve `None` quando é o pedido normal da app de edição, que é sempre
    sobre a coleção de quem entrou.
    """
    from . import utilizador

    slug = None
    partes = request.path.strip("/").split("/")
    if len(partes) >= 2 and partes[0] == "u":
        slug = partes[1]
    else:
        anfitriao = (request.host or "").split(":")[0].lower()
        base = str((_cfg().get("auth") or {}).get("base_publica") or "").lower()
        if base and anfitriao.endswith("." + base):
            slug = anfitriao[: -len(base) - 1]

    if not slug:
        return None
    try:
        u = utilizador.por_slug(auth.validar_slug(slug), obrigatorio=False)
    except ValueError:
        return None
    return u or None


def _depois(resp):
    """Cabeçalhos de segurança e a marca de «não indexes isto»."""
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("Referrer-Policy", "same-origin")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    # A app de EDIÇÃO nunca se indexa: é privada por natureza, e é o sítio onde
    # os endereços de entrada vivem.
    resp.headers.setdefault("X-Robots-Tag", "noindex, nofollow")
    return resp


def _por_https() -> bool:
    """Isto está a ser servido por HTTPS? (Contando com o túnel à frente.)"""
    return (request.scheme == "https"
            or request.headers.get("X-Forwarded-Proto", "").split(",")[0]
            .strip() == "https")


def por_cookie(resp, sid: str, cfg: dict | None = None):
    """Mete o cookie da sessão com as propriedades todas.

    `HttpOnly` — o JavaScript não lhe chega, por isso um XSS não o rouba.
    `SameSite=Lax` — não é `Strict` porque a volta do fornecedor de OAuth é uma
        navegação que vem de outro site; com `Strict` o cookie não seguia e a
        entrada nunca se concluía. `Lax` deixa passar a navegação de topo e
        continua a travar os pedidos de terceiros, que é o que o CSRF ataca.
    `Secure` — só quando isto está a ser servido por HTTPS. No 8770 em casa é
        `http://`, e um `Secure` ali fazia o browser descartar o cookie e a
        sessão nunca pegava.
    """
    resp.set_cookie(
        auth.COOKIE, sid,
        max_age=auth.sessao_dias(cfg) * 86400,
        httponly=True, samesite="Lax", secure=_por_https(), path="/")
    # O `nonce` da entrada já serviu: apaga-se, para não ficar a valer.
    resp.delete_cookie(auth.COOKIE_NONCE, path="/")
    return resp


# --------------------------------------------------------------------------
# Quem sou eu
# --------------------------------------------------------------------------


@bp.get("/api/conta.json")
def api_conta():
    """O estado da sessão. É daqui que o `app.js` sabe se pode mostrar os `+`."""
    from . import multi, privacidade, utilizador

    cfg = _cfg()
    aberto = multi.aberto(cfg)
    out = {
        "aberto": aberto,
        "entrado": False,
        "editavel": False,
        "provedores": [],
        "csrf": None,
        "utilizador": None,
    }
    if not aberto:
        # Fechado: um dono só. O `editavel` continua a ser o de sempre — é o
        # `server.py` que o põe no payload da Coleção; aqui diz-se o mesmo para
        # o cliente não ter de adivinhar.
        out["editavel"] = True
        return jsonify(out)

    out["provedores"] = auth.disponiveis(cfg)
    sess = g.get("sessao")
    if sess is None:
        return jsonify(out)

    out["csrf"] = sess.get("csrf")
    if not sess.get("user_id"):
        # Identificada, sem conta: é o registo que falta.
        out["registo_pendente"] = {
            "provedor": sess.get("provedor"),
            "nome": sess.get("nome"),
            "slug_sugerido": auth.limpar_slug(sess.get("nome") or ""),
        }
        return jsonify(out)

    u = utilizador.registo(int(sess["user_id"]))
    out["entrado"] = True
    out["editavel"] = not g.get("somente_leitura", False)
    out["utilizador"] = {
        "nome": u.get("nome"),
        "slug": u.get("slug"),
        "publico": privacidade.de(None, int(sess["user_id"])),
        "identidades": auth.identidades_de(_auth_con(), int(sess["user_id"])),
    }
    return jsonify(out)


# --------------------------------------------------------------------------
# Entrar
# --------------------------------------------------------------------------


def _redirect_uri(nome: str) -> str:
    """O endereço de volta. Tem de ser igual ao que está no fornecedor."""
    base = str((_cfg().get("auth") or {}).get("base_url") or "").rstrip("/")
    if not base:
        # Sem `base_url` usa-se o que o pedido diz — serve no 8770 e em ensaio.
        base = request.url_root.rstrip("/")
    return f"{base}/entrar/{nome}"


@bp.get("/entrar/<nome>")
def entrar(nome: str):
    """Manda o browser ao fornecedor, ou conclui a volta dele."""
    try:
        auth.exigir_porta_aberta(_cfg())
    except auth.PortaFechada as e:
        return _resposta(str(e), 403)

    con = _auth_con()
    chave = _chave_do_pedido()

    # O fornecedor LOCAL não anda pelo browser: entra-se de uma vez, com o
    # `sub` no endereço. Só existe em ensaio, e é o `multi.exigir_ensaio` de
    # dentro do `Local` que o garante — não uma condição escrita aqui.
    try:
        p = auth.provedor(nome)
    except auth.ProvedorDesconhecido as e:
        return _resposta(str(e), 400)
    if not p.redireciona:
        return _entrar_local(p, con, chave)

    # A volta traz `code` e `state`.
    if request.args.get("code") or request.args.get("state"):
        return _concluir(nome, con, chave)

    try:
        auth.exigir_folga(con, chave, _cfg())
        r = auth.comecar(con, nome, redirect_uri=_redirect_uri(nome),
                         destino=request.args.get("destino"), cfg=_cfg())
    except auth.DemasiadasTentativas as e:
        return _resposta(str(e), 429)
    except (auth.ProvedorDesconhecido, auth.ProvedorPorConfigurar) as e:
        return _resposta(str(e), 400)
    resp = redirect(r["url"], code=302)
    # O `nonce` ata esta entrada A ESTE browser (ver `auth.consumir_pedido`).
    # Dura o que o fluxo dura, e não mais.
    # O cookie dura MAIS do que o pedido de propósito: com o mesmo prazo, quem
    # demorasse 16 minutos perdia as duas coisas ao mesmo tempo e lia a
    # mensagem errada («não começou neste browser») em vez da certa («demorou
    # demasiado»). O que manda na validade é o registo no servidor.
    resp.set_cookie(auth.COOKIE_NONCE, r["nonce"],
                    max_age=auth.PEDIDO_MINUTOS * 60 * 4, httponly=True,
                    samesite="Lax", secure=_por_https(), path="/")
    return resp


def _entrar_local(p, con, chave: str):
    """A entrada de ensaio. Fora do ensaio o `p.identidade` rebenta, e é isso
    que a torna impossível em produção — não uma condição desta função."""
    try:
        auth.exigir_folga(con, chave, _cfg())
        ident = p.identidade(code=request.args.get("sub", ""))
    except auth.DemasiadasTentativas as e:
        return _resposta(str(e), 429)
    except Exception as e:
        # Apanha o `multi.SoEmEnsaio` também: fora do ensaio isto é 403.
        auth.registar_tentativa(con, chave, p.nome, False)
        return _resposta(str(e), 403)

    auth.registar_tentativa(con, chave, p.nome, True)
    user_id = auth.por_identidade(con, ident)
    nova = auth.criar_sessao(con, user_id=user_id, identidade=ident,
                             agente=request.headers.get("User-Agent"),
                             cfg=_cfg())
    resp = redirect(_destino_seguro(request.args.get("destino") or "/"), code=302)
    return por_cookie(resp, nova["sid"], _cfg())


def _chave_do_pedido() -> str:
    """A chave do tecto de tentativas.

    NÃO é uma decisão de identidade — é só um balde para contar pedidos. Por
    isso pode ser o endereço, que é falsificável: falsificá-lo dá mais baldes,
    não dá acesso a nada.
    """
    return (request.headers.get("CF-Connecting-IP")
            or request.remote_addr or "?")


def _concluir(nome: str, con, chave: str):
    erro = request.args.get("error")
    if erro:
        auth.registar_tentativa(con, chave, nome, False)
        return _resposta(f"o fornecedor recusou a entrada: {erro}", 400)

    try:
        auth.exigir_folga(con, chave, _cfg())
        pedido = auth.consumir_pedido(con, request.args.get("state", ""),
                                      request.cookies.get(auth.COOKIE_NONCE))
        if pedido["provedor"] != nome:
            raise auth.PedidoInvalido("esta entrada não corresponde ao fornecedor.")
        p = auth.provedor(nome)
        ident = p.identidade(code=request.args.get("code", ""),
                             verifier=pedido["verifier"],
                             redirect_uri=_redirect_uri(nome), cfg=_cfg())
    except auth.DemasiadasTentativas as e:
        return _resposta(str(e), 429)
    except auth.ErroDeAutenticacao as e:
        auth.registar_tentativa(con, chave, nome, False)
        return _resposta(str(e), 400)

    auth.registar_tentativa(con, chave, nome, True)
    user_id = auth.por_identidade(con, ident)
    nova = auth.criar_sessao(con, user_id=user_id, identidade=ident,
                            agente=request.headers.get("User-Agent"),
                            cfg=_cfg())
    if user_id is not None:
        auth.guardar_identidade(con, ident, user_id)

    destino = pedido.get("destino") or "/"
    resp = redirect(_destino_seguro(destino), code=302)
    return por_cookie(resp, nova["sid"], _cfg())


def _destino_seguro(destino: str) -> str:
    """Só caminhos deste site.

    Sem isto o `?destino=` era um redirecionamento aberto: um link nosso que
    despeja a pessoa noutro sítio, que é como se montam páginas de entrada
    falsas.
    """
    d = str(destino or "/")
    partido = urlsplit(d)
    if partido.scheme or partido.netloc or not d.startswith("/"):
        return "/"
    return d


@bp.post("/sair")
@bp.get("/sair")
def sair():
    sid = request.cookies.get(auth.COOKIE)
    if sid:
        auth.terminar(_auth_con(), sid)
    resp = redirect("/", code=302)
    resp.delete_cookie(auth.COOKIE, path="/")
    return resp


# --------------------------------------------------------------------------
# Registar
# --------------------------------------------------------------------------


@bp.post("/api/conta/registar")
def registar():
    """Cria a conta de quem já provou quem é e escolheu um nome de endereço."""
    from . import utilizador

    try:
        auth.exigir_porta_aberta(_cfg())
    except auth.PortaFechada as e:
        return _resposta(str(e), 403)

    sess = g.get("sessao")
    if sess is None or not sess.get("provedor"):
        return _resposta(
            "primeiro entra com o Discord ou o Google; depois escolhes o nome.", 401)
    if sess.get("user_id"):
        return _resposta("já tens conta.", 409)
    if not auth.csrf_valido(sess, _csrf_enviado()):
        return _resposta("o pedido não trazia a marca de segurança (CSRF).", 403)

    dados = request.get_json(silent=True) or {}
    try:
        slug = auth.exigir_slug(dados.get("slug", ""))
    except ValueError as e:
        return _resposta(str(e), 400)

    nome = str(dados.get("nome") or sess.get("nome") or slug).strip()[:60]
    try:
        u = utilizador.criar(nome, slug)
    except Exception as e:  # SlugInvalido e o que o registo levantar
        return _resposta(f"não foi possível criar a conta: {e}", 400)

    con = _auth_con()
    ident = auth.Identidade(sess["provedor"], sess["sub"], sess.get("nome") or "")
    auth.guardar_identidade(con, ident, int(u["user_id"]))
    # Rotação: o cookie do pré-registo não é o cookie da conta.
    nova = auth.ligar_conta(con, request.cookies.get(auth.COOKIE),
                            int(u["user_id"]), _cfg())
    resp = jsonify({"ok": True, "slug": u["slug"], "nome": u["nome"],
                    "csrf": nova["csrf"]})
    return por_cookie(resp, nova["sid"], _cfg())


# --------------------------------------------------------------------------
# A conta: privacidade, exportar, apagar
# --------------------------------------------------------------------------


def _meu() -> int:
    sess = g.get("sessao")
    if sess is None or not sess.get("user_id"):
        raise PermissionError("precisas de entrar.")
    return int(sess["user_id"])


@bp.post("/api/conta/privacidade")
def mudar_privacidade():
    from . import privacidade
    try:
        uid = _meu()
    except PermissionError as e:
        return _resposta(str(e), 401)
    valor = (request.get_json(silent=True) or {}).get("publico")
    try:
        novo = privacidade.definir(None, uid, valor)
    except Exception:
        return _resposta(
            f"«{valor}» não é uma opção — há {', '.join(privacidade.VALORES)}.", 400)
    return jsonify({"ok": True, "publico": novo})


@bp.post("/api/conta/exportar")
def exportar():
    """Os dados dele, num ficheiro, pelo caminho da app — sem SQL à mão."""
    from . import conta, utilizador
    try:
        uid = _meu()
    except PermissionError as e:
        return _resposta(str(e), 401)
    u = utilizador.registo(uid)
    try:
        r = conta.exportar(u["slug"])
    except Exception as e:
        return _resposta(f"não foi possível exportar: {e}", 500)
    return jsonify({"ok": True, "ficheiro": str(r.get("ficheiro")),
                    "linhas": r.get("linhas")})


@bp.post("/api/conta/apagar")
def apagar():
    """Apaga a conta dele e tudo o que é dele. Pede confirmação por escrito."""
    from . import conta, utilizador
    try:
        uid = _meu()
    except PermissionError as e:
        return _resposta(str(e), 401)

    dados = request.get_json(silent=True) or {}
    u = utilizador.registo(uid)
    # A confirmação é escrever o próprio nome do endereço: é o padrão que evita
    # um clique distraído apagar um mês de trabalho.
    if str(dados.get("confirmar") or "").strip().lower() != u["slug"]:
        return _resposta(
            f"para apagar, escreve «{u['slug']}» no campo de confirmação.", 400)

    try:
        r = conta.apagar(u["slug"], confirmar=True)
    except Exception as e:
        return _resposta(f"não foi possível apagar: {e}", 500)

    # As credenciais e as sessões são desta casa, e a limpeza também
    # (combinado com a `1-multi-guardas`, que não mexe numa tabela que não é
    # dela). Feito no MESMO passo, para não ficar uma identidade órfã a apontar
    # para um utilizador que já não existe.
    meu = auth.esquecer_identidades(_auth_con(), uid)

    resp = jsonify({"ok": True, "linhas": r.get("linhas"),
                    "ficheiros": [str(f) for f in (r.get("ficheiros") or [])],
                    "identidades": meu["identidades"], "sessoes": meu["sessoes"]})
    resp.delete_cookie(auth.COOKIE, path="/")
    return resp

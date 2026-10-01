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

QUEM MANDA NA AUTENTICAÇÃO É A ORIGEM, NÃO A PORTA (2026-10-01)
    **Isto é a correcção de um defeito que expunha dados**, encontrado por duas
    revisões independentes no mesmo sítio. Até aqui a regra era:

        porta FECHADA  ->  não há autenticação nenhuma
        porta ABERTA   ->  a escrita exige sessão

    Com o túnel vivo, a primeira linha é «escrita anónima na coleção dele a
    partir da internet». E não era um risco teórico: o `multi.aberto` vivia numa
    modificação por gravar, e um `git checkout` do config fechava a porta — ou
    seja, DESLIGAVA a autenticação — sozinho. Pior ainda, um pedido sem sessão
    caía no `db.connect(user_id=None)` -> `utilizador.atual()` -> **o André**, e
    por isso nenhuma leitura de fora passava pela privacidade dele.

    A regra nova, em três linhas:

      * **a PORTA** trava o OAuth, o registo e a publicação das páginas dos
        outros, e devolve à casa o escrever-sem-password. É isso e mais nada —
        **fechar deixou de desligar a autenticação**. (E nunca travou a entrada
        por password: com ela fechada, quem já tem conta entra e usa a sua
        coleção. É assim desde 2026-09-30 e foi medido a 01/10.)
      * **a ORIGEM** diz se é preciso entrar. Um pedido que não seja
        inequivocamente de casa (`origem.py`) exige sessão para **tudo**:
        leitura e escrita, com a porta aberta ou fechada. Só passam a casca da
        página e a porta de entrada (`DE_FORA_SEM_SESSAO`).
      * **de casa** fica exactamente como estava: com a porta fechada escreve-se
        sem password (o telemóvel na LAN, que ele usa todos os dias), e com a
        porta aberta a escrita exige sessão e CSRF, ele incluído.

    O «inequivocamente de casa» é um E de três condições e está explicado no
    `origem.py`: endereço da rede local **e** nenhum cabeçalho de intermediário
    **e** não pediu o anfitrião público. Forjar qualquer uma delas só pode
    TIRAR confiança, nunca dá-la.

    O QUE ISTO NÃO FAZ: não protege a LAN. Quem estiver na rede de casa com a
    porta fechada continua a escrever na coleção dele sem password — é a decisão
    dele, está no banner do `serve` («Sem palavra-passe: quem chegar ao URL pode
    escrever na coleção») e não é desta correcção mudá-la.

A PORTA NÃO É A FECHADURA DA ENTRADA (2026-09-30)
    Corrigido um BECO SEM SAÍDA. A porta fechada recusava também o
    `/api/conta/entrar` e nem resolvia a sessão — e como o `multi --verificar`
    exige que ele TROQUE a password temporária ANTES de abrir, e a troca se faz
    entrando no site, ficava um ciclo: não abria sem trocar e não trocava sem
    abrir.

    A regra passou a ser esta: **entrar funciona sempre**, e a porta decide
    apenas se a ESCRITA **de casa** exige sessão.
"""

from __future__ import annotations

import json
from urllib.parse import urlsplit

from flask import Blueprint, current_app, g, jsonify, redirect, request

from . import auth, config, origem

bp = Blueprint("conta", __name__)


class SemSessao(Exception):
    """Pediram a base de alguém sem haver alguém. Ver `server.get_con`.

    É a rede da `1-multi-guardas` («uma consulta sem dono deve rebentar») na
    camada que importa: o `db.connect(user_id=None)` cai no utilizador 1, e por
    isso um pedido de fora sem sessão abria a base DELE. O guarda do `_antes`
    responde 401 antes de chegar aqui; isto é para uma rota futura que alguém
    acrescente e se esqueça — em vez de servir a coleção dele, rebenta.
    """


#: Os métodos que mudam alguma coisa. Um `GET` nunca escreve nesta app.
ESCREVE = frozenset({"POST", "PUT", "PATCH", "DELETE"})

#: O dono do site — o André. É o `utilizador.ANDRE`, repetido aqui como
#: constante para este módulo não ter de importar nada só por causa de um 1.
DONO = 1

#: Caminhos que têm de funcionar sem sessão de DONO, senão não há por onde
#: entrar. O `/api/conta/entrar` é a entrada por password e tem a protecção
#: dele por dentro (o travão de tentativas e a exigência de JSON — ver
#: `entrar_com_senha`). O `/api/conta/registar` está aqui por história: hoje
#: recusa sempre (`REGISTO_ABERTO`), e continua na lista para responder o 403
#: com a razão em vez de um 401 que não explica nada.
ABERTOS = ("/entrar", "/sair", "/api/conta.json", "/api/conta/entrar",
           "/api/conta/registar")

#: O QUE SE SERVE A QUEM VEM DE FORA SEM SESSÃO — e é só isto (2026-10-01).
#:
#: A casca da página e a porta de entrada. Nem um payload de leitura, nem uma
#: imagem: `editar.baverone.com` é a aplicação de EDIÇÃO, e quem não entrou não
#: tem nada para ver aqui. As coleções que se podem ver sem entrar estão no site
#: ESTÁTICO, que o `build.py` gera já filtrado pela privacidade de cada um — ver
#: `_u_explica`.
#:
#: **É por isto que a privacidade fica respeitada sem uma linha de filtragem.**
#: A alternativa era filtrar dezassete rotas de leitura, e uma esquecida era uma
#: fuga; aqui não se serve nada, por isso não há nada para filtrar.
#:
#: A lista é LITERAL, e não «qualquer ficheiro que exista no `web/`»: um
#: ficheiro novo naquela pasta não pode passar a ser público em silêncio. Há
#: teste que compara as duas coisas e rebenta se alguém lá puser um quarto
#: ficheiro sem decidir o que fazer com ele.
DE_FORA_SEM_SESSAO = (
    "/", "/index.html", "/app.js", "/style.css",   # a casca
    "/sair", "/api/conta.json", "/api/conta/entrar", "/api/conta/registar",
)

#: Prefixos, a par da lista de cima: o `/entrar/<fornecedor>` e a volta dele.
DE_FORA_PREFIXOS = ("/entrar/",)

#: NÃO HÁ REGISTO ABERTO (2026-09-30). *"isto e uma coisa caseira, para usar
#: entre amigos"* — as contas nascem de um comando dele:
#:
#:     riftvault conta --criar <nome>
#:
#: A rota fica no código, a recusar, por duas razões: o 403 diz a quem chegar
#: lá o que fazer (pedir ao André), e a fatia que um dia quiser convites tem
#: onde encaixar. Mudar isto para `True` **não** é uma decisão de código — é
#: uma decisão dele, e por isso não é uma chave de config: uma chave num
#: ficheiro commitado está a um merge de distância de abrir o registo sem
#: ninguém ter decidido nada.
REGISTO_ABERTO = False

#: COM UMA PASSWORD TEMPORÁRIA NÃO SE FAZ NADA até ser trocada — *"Quem entra
#: com uma temporaria e OBRIGADO a trocar antes de fazer seja o que for"*.
#:
#: Bloqueia-se tudo o que é `/api/`, menos estes dois. O resto (o `index.html`,
#: o `app.js`, o CSS, as imagens) passa, senão não havia página onde mostrar o
#: formulário da troca; e o `/sair` também não é `/api/`, por isso quem desistir
#: pode sair.
#:
#: **Bloqueia as LEITURAS e não só as escritas**, de propósito: a temporária
#: andou pelo WhatsApp, e quem a apanhasse no caminho podia não escrever nada e
#: ler a coleção toda. Uma password que passou por uma aplicação de mensagens
#: vale para trocar a password, e mais nada.
#: O `/api/conta/entrar` está cá para não haver beco sem saída: quem tenha uma
#: sessão com temporária e queira entrar como outra pessoa tem de conseguir,
#: sem ter de descobrir o `/sair` primeiro.
COM_TEMPORARIA = ("/api/conta.json", "/api/conta/senha", "/api/conta/entrar")

#: ROTAS QUE ESCREVEM NO CONFIG PARTILHADO — e por isso são SÓ DO DONO.
#:
#: Isto é o furo que a separação por ficheiro não tapa, e vale a pena dizer
#: porquê. A `0-multi-utilizador-1` pôs cada coleção num `vault.db` seu, e por
#: isso nenhuma rota consegue escrever na BASE de outra pessoa. Mas duas rotas
#: não escrevem numa base: escrevem no `riftvault_config.json`, que é UM
#: ficheiro para todos —
#:
#:     POST /api/decks/montar     -> decks.alternar_montado  -> decks.montados
#:     POST /api/decks/principal  -> decks.escrever_principal -> decks.principal
#:
#: Um amigo autenticado a carregar em «Montar» escrevia o slug do deck DELE na
#: lista do André. Não é uma leitura indevida — é uma escrita cruzada, e escapa
#: por o config não ser uma base de dados.
#:
#: Ficam do dono até o config ser por utilizador (fase seguinte, ver
#: `docs/multi-utilizador.md`). É também a razão de o ESTADO dos decks ficar
#: fora desta fatia — ver `docs/contas-e-autenticacao.md`, «o que ficou de fora».
SO_DO_DONO = ("/api/decks/montar", "/api/decks/principal")

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
    _apanhar_config_partilhado(app)
    _apanhar_corpo_grande(app)
    _apanhar_sem_sessao(app)


def _apanhar_sem_sessao(app) -> None:
    """A `SemSessao` do `get_con()` vira 401 com a razão, e não um 500.

    Não devia chegar aqui — o `_so_a_porta_de_entrada` responde antes. Se
    chegar, é uma rota que escapou ao guarda, e o que se vê é «precisas de
    entrar» em vez de uma página de erro com um traço da pilha.
    """
    @app.errorhandler(SemSessao)
    def _traduzir(e):  # pragma: no cover - rede de segurança
        return _resposta(str(e), 401)


def _apanhar_config_partilhado(app) -> None:
    """A rede da `1-multi-guardas`, traduzida para uma resposta legível.

    Ela pôs um guarda dentro do `config.escrever_valor`: escrever no
    `riftvault_config.json` como outro utilizador rebenta, venha de onde vier
    (rota, CLI, teste). As duas rotas que o fazem já estão travadas antes, no
    `SO_DO_DONO`; isto é para uma rota FUTURA que alguém ligue ao config e se
    esqueça de a pôr lá — em vez de um 500 sem explicação, dá 403 com a razão.
    """
    from . import config as _config

    excepcao = getattr(_config, "ConfigPartilhado", None)
    if excepcao is None:
        return  # versão do config sem o guarda; nada a traduzir

    @app.errorhandler(excepcao)
    def _traduzir(e):  # pragma: no cover - rede de segurança
        return _resposta(
            "isto mexe numa configuração partilhada do site e por isso é só do "
            f"dono ({e}).", 403)


def _apanhar_corpo_grande(app) -> None:
    """Um corpo acima do tecto dá 413 com a razão, e não uma página de erro."""
    @app.errorhandler(413)
    def _grande(_e):
        return _resposta(
            f"o pedido é demasiado grande (o máximo é "
            f"{CORPO_MAXIMO // 1024} KB).", 413)


def _cfg() -> dict:
    return config.load()


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
    g.alvo_slug = None
    g.senha_temporaria = False

    cfg = _cfg()
    from . import multi
    aberto = multi.aberto(cfg)

    # DE ONDE VEM ISTO (2026-10-01). Primeiro de tudo, porque é o que decide se
    # é preciso entrar — e porque o `get_con()` do `server.py` lê o `de_casa`
    # para se recusar a abrir a base de alguém sem haver alguém.
    o = origem.do_pedido(request, cfg)
    g.de_casa = o["de_casa"]
    g.sinais_de_fora = o["sinais"]

    # A SESSÃO RESOLVE-SE NAS DUAS PORTAS (2026-09-30), e é o que tira o beco
    # descrito no topo: sem isto, quem entrasse com a password temporária com a
    # porta fechada não tinha `g.sessao` e o `/api/conta/senha` respondia
    # «precisas de entrar» a quem tinha acabado de entrar.
    #
    # SEM COOKIE nem se abre o `auth.db`: o caminho normal da porta fechada —
    # ele no 8770, sem nunca ter entrado — fica exactamente como ontem, sem um
    # ficheiro a mais aberto por pedido.
    sid = request.cookies.get(auth.COOKIE)
    con = _auth_con() if sid else None
    sess = auth.sessao(con, sid) if sid else None
    if sess is not None:
        g.sessao = sess
        if sess.get("user_id"):
            g.riftvault_user = int(sess["user_id"])
            # Mexeu-se: a sessão dura enquanto se usa. O `visto_em` faz isto
            # escrever no máximo uma vez por hora — uma página da Coleção são
            # dezenas de pedidos e não vale um `UPDATE` cada.
            auth.tocar(con, sid, _cfg(), sess.get("visto_em"))
            # Pergunta-se a CADA pedido, e não se guarda na sessão: assim a
            # troca da password liberta o site no pedido seguinte, sem ter de
            # entrar outra vez. É um SELECT por chave primária numa tabela com
            # tantas linhas quantos os amigos dele.
            g.senha_temporaria = auth.estado_senha(
                con, g.riftvault_user)["temporaria"]

    # Um pedido pode NOMEAR outra pessoa (`/u/<slug>/…`). Se nomear, marca-se —
    # mas **o `g.riftvault_user` NÃO muda**, e isso é a invariante que interessa:
    #
    #     este servidor nunca abre uma base que não seja a do dono da sessão.
    #
    # Não é «nunca escreve na de outro»: é nunca a ABRIR, nem para ler. Deixar o
    # alvo mandar no `g.riftvault_user` fazia o `get_con()` abrir a base de outra
    # pessoa num GET, e a única coisa que hoje o impedia de a devolver era não
    # haver rota que casasse — segurança por acidente. As leituras da coleção de
    # outro fazem-se no site ESTÁTICO (`rift.baverone.com/u/<slug>/`), que já sai
    # filtrado pela privacidade dele; ver `_u_explica`.
    if aberto:
        alvo = _dono_pedido()
        if alvo is not None:
            g.alvo_slug = alvo.get("slug")
            g.somente_leitura = alvo["user_id"] != (
                g.sessao.get("user_id") if g.sessao else None)

    _dono_do_fio(g.riftvault_user)

    travado = _trava_temporaria()
    if travado is not None:
        return travado

    # DE FORA E SEM SESSÃO: só a casca e a porta de entrada (2026-10-01).
    #
    # Isto vem ANTES do ramo da escrita de propósito: vale para as LEITURAS
    # também, e é o que fecha o segundo defeito — sem isto, um GET anónimo pelo
    # túnel caía na base do utilizador 1 e servia a coleção dele sem a
    # privacidade ser consultada uma única vez.
    barrado = _so_a_porta_de_entrada()
    if barrado is not None:
        return barrado

    if request.method in ESCREVE:
        # DE CASA, SEM SESSÃO E COM A PORTA FECHADA não se pede nada — é o de
        # ontem, ao byte, e é o telemóvel dele na rede de casa. O `g.de_casa`
        # desta linha é o que já não deixa isto valer para a internet.
        #
        # **Com** sessão o guarda corre inteiro nas duas portas: quem entrou tem
        # `csrf` e é dono do que escreve, e sem isto um amigo com conta criada
        # antes de abrir escrevia no config partilhado dele.
        if not aberto and g.sessao is None and g.de_casa:
            return None
        return _guardar_escrita()
    return None


def _entrou() -> bool:
    return bool(g.get("sessao") and g.sessao.get("user_id"))


def _so_a_porta_de_entrada():
    """Quem vem de fora sem sessão vê a página de entrada, e mais nada."""
    if g.de_casa or _entrou():
        return None
    caminho = request.path
    if caminho in DE_FORA_SEM_SESSAO or caminho.startswith(DE_FORA_PREFIXOS):
        return None
    return _resposta(
        "este endereço é a aplicação de edição do riftvault e de fora de casa "
        "pede sempre que entres — mesmo para ver. Entra com o teu nome e a tua "
        "password. As coleções que se vêem sem entrar estão no site publicado, "
        "e só as de quem as tornou públicas.", 401)


def _trava_temporaria():
    """Com a password temporária só se pode trocar a password. Ver `COM_TEMPORARIA`."""
    if not g.get("senha_temporaria"):
        return None
    caminho = request.path
    if not caminho.startswith("/api/") or caminho in COM_TEMPORARIA:
        return None
    return _resposta(
        "entraste com a password temporária que o André te deu. Escolhe uma "
        "password tua para poderes usar o site.", 403)


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

    if request.path in SO_DO_DONO and g.riftvault_user != DONO:
        # Escreve no config, que é um ficheiro para todos. Ver `SO_DO_DONO`.
        return _resposta(
            "montar e escolher o deck principal ainda são do dono do site: "
            "essa escolha vive num ficheiro de configuração partilhado e não "
            "na tua coleção. Os teus decks aparecem na mesma, e as cartas "
            "deles contam — o que não dá é marcá-los como montados.", 403)

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
    de_casa = bool(g.get("de_casa", True))
    out = {
        "aberto": aberto,
        "entrado": False,
        # DE ONDE VEIO ESTE PEDIDO (2026-10-01). Serve duas coisas: o `app.js`
        # precisa de saber se «não entrar» é uma opção (de fora não é), e ele
        # precisa de poder conferir, do telemóvel, se a rede de casa está a ser
        # reconhecida como tal. Os `sinais` dizem o NOME do que fez a decisão —
        # nunca o valor de um cabeçalho.
        "origem": "casa" if de_casa else "fora",
        "sinais": list(g.get("sinais_de_fora") or []),
        "exige_entrar": not de_casa,
        # Fechado, de casa e sem sessão: um dono só, e o `editavel` é o de
        # sempre — é o `server.py` que o põe no payload da Coleção; aqui diz-se
        # o mesmo para o cliente não ter de adivinhar. **De fora é `false`**
        # (2026-10-01): sem sessão não há nada editável nem sequer legível, e
        # dizer `true` punha os `+`/`−` à vista a dar 401 a cada clique.
        "editavel": not aberto and de_casa,
        # A entrada por PASSWORD está SEMPRE disponível (2026-09-30): não
        # precisa de configurar nada, e funciona com a porta fechada — é o que
        # lhe dá onde trocar a temporária antes de abrir (ver o topo). Os
        # `provedores` são o OAuth, que fica parado e só aparece configurado.
        "senha": True,
        "provedores": auth.disponiveis(cfg) if aberto else [],
        "registo_aberto": REGISTO_ABERTO,
        "senha_temporaria": False,
        "csrf": None,
        "utilizador": None,
    }
    sess = g.get("sessao")
    if sess is None:
        return jsonify(out)

    out["csrf"] = sess.get("csrf")
    if not sess.get("user_id"):
        # Identificada por um fornecedor, sem conta aqui. Com o registo fechado
        # (o de hoje) não há formulário para lhe mostrar: diz-se o que fazer.
        if not REGISTO_ABERTO:
            out["sem_conta"] = {
                "provedor": sess.get("provedor"),
                "nome": sess.get("nome"),
            }
            return jsonify(out)
        out["registo_pendente"] = {
            "provedor": sess.get("provedor"),
            "nome": sess.get("nome"),
            "slug_sugerido": auth.limpar_slug(sess.get("nome") or ""),
        }
        return jsonify(out)

    u = utilizador.registo(int(sess["user_id"]))
    out["entrado"] = True
    out["senha_temporaria"] = bool(g.get("senha_temporaria"))
    # Com a temporária o site está trancado (ver `_trava_temporaria`): dizer
    # `editavel: true` punha os `+`/`−` à vista a dar 403 a cada clique.
    out["editavel"] = (not g.get("somente_leitura", False)
                       and not out["senha_temporaria"])
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
    """Manda o browser ao fornecedor, ou conclui a volta dele.

    O `?ligar=<código>` é o caminho do PRIMEIRO utilizador e **funciona com a
    porta fechada**, de propósito: o André tem de poder ligar a conta dele antes
    de abrir, senão abria a porta e ficava do lado de fora da própria coleção. O
    código vem da consola (`riftvault multi --ligar`), é de uso único e expira —
    quem tem a consola do PC é o dono do PC, e isso prova mais do que qualquer
    verificação de endereço.
    """
    con = _auth_con()
    chave = _chave_do_pedido()
    convite = request.args.get("ligar")

    if not convite:
        try:
            auth.exigir_porta_aberta(_cfg())
        except auth.PortaFechada as e:
            return _resposta(str(e), 403)

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
        # O convite gasta-se AQUI, na ida: se ele desistir a meio, gasta-se um
        # código e corre-se o comando outra vez. O contrário — gastá-lo na volta
        # — deixava um código válido à espera no `auth.db`.
        liga_a = auth.usar_convite(con, convite) if convite else None
        r = auth.comecar(con, nome, redirect_uri=_redirect_uri(nome),
                         destino=request.args.get("destino"),
                         liga_a=liga_a, cfg=_cfg())
    except auth.DemasiadasTentativas as e:
        return _resposta(str(e), 429)
    except auth.PedidoInvalido as e:
        return _resposta(str(e), 400)
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
    # Uma entrada com CONVITE liga-se a uma conta que já existe em vez de
    # oferecer o registo. É o caminho do André: ele é o utilizador 1 e o slug
    # dele já é dele, por isso «registar-se» não fazia sentido nenhum.
    if user_id is None and pedido.get("liga_a"):
        user_id = int(pedido["liga_a"])
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


@bp.get("/u/<slug>/")
@bp.get("/u/<slug>/<path:resto>")
def _u_explica(slug: str, resto: str = ""):
    """`/u/<slug>/` NESTE servidor não serve a coleção de ninguém — e diz porquê.

    A coleção de outra pessoa lê-se no site ESTÁTICO, que o `build.py` gera já
    filtrado pela privacidade dela (`nada` não gera nada; `sem-valores` gera sem
    um euro). Servi-la daqui obrigava a repetir essa filtragem em dezassete
    rotas de leitura, e uma esquecida era uma fuga — a mesma lição dos dezassete
    `fetch` que passaram a ter uma função só.

    Sem esta rota o pedido caía no `/<path:name>` e dava um 404 seco, que se lê
    como «está partido». Assim o comportamento é escolhido e explicado.
    """
    return _resposta(
        f"a coleção de «{slug}» não se vê aqui: este endereço é a aplicação de "
        f"edição, e cada um só vê a sua. As coleções públicas estão no site "
        f"publicado, em /u/{slug}/ — e só aparecem lá se essa pessoa as tiver "
        f"tornado públicas.", 404)


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


@bp.post("/api/conta/entrar")
def entrar_com_senha():
    """Entrar com o nome e a password (2026-09-30).

    PROTECÇÕES, e cada uma tem uma razão:

    * **o travão de tentativas** — o do SÍTIO antes de gastar 130 ms de scrypt,
      o da CONTA só depois de a password sair errada. Ver «TRANCA-O-AMIGO» no
      `auth.py`: com o da conta à frente, quem soubesse o nome de um amigo
      trancava-o de fora;
    * **exige JSON**. Um `<form>` de outro site não consegue mandar
      `Content-Type: application/json`: o browser obriga a um pedido prévio de
      permissão (CORS preflight) que nós não respondemos. É o que impede o
      «login CSRF» — alguém levar o browser dele a entrar na conta de outra
      pessoa e a escrever a coleção dele para lá. Não se pode usar aqui a marca
      de CSRF de sempre: quem entra ainda não tem sessão e por isso não tem
      marca nenhuma;
    * **a mesma mensagem** para nome que não existe e password errada (ver
      `auth.entrar`).

    **FUNCIONA COM A PORTA FECHADA** (2026-09-30), e é o que tira o beco do topo
    deste ficheiro: o `multi --verificar` exige que ele troque a temporária
    ANTES de abrir, e a troca faz-se entrando. Não afrouxa nada — com a porta
    fechada a app já não tem autenticação, por isso entrar não dá acesso a nada
    que não estivesse dado; dá o sítio onde se troca a password. O travão de
    tentativas corre igual nas duas portas.
    """
    if not request.is_json:
        return _resposta(
            "este pedido tem de vir em JSON (é uma protecção: impede outro "
            "site de te fazer entrar aqui sem saberes).", 415)

    dados = request.get_json(silent=True) or {}
    con = _auth_con()
    try:
        quem = auth.entrar(con, dados.get("nome") or dados.get("slug") or "",
                           dados.get("senha") or "",
                           chave=_chave_do_pedido())
    except auth.TemDeEsperar as e:
        return _resposta(str(e), 429)
    except auth.ServidorOcupado as e:
        # 503 e NÃO 401: isto não é uma password errada, e dizer-lhe que era
        # mandava-o trocar uma password que está certa. Ver `VAGAS_DE_SCRYPT`.
        return _resposta(str(e), 503)
    except auth.ErroDeAutenticacao as e:
        return _resposta(str(e), 401)

    nova = auth.criar_sessao(con, user_id=quem["user_id"],
                             agente=request.headers.get("User-Agent"),
                             cfg=_cfg())
    resp = jsonify({"ok": True, "slug": quem["slug"], "nome": quem["nome"],
                    "senha_temporaria": quem["temporaria"],
                    "csrf": nova["csrf"]})
    return por_cookie(resp, nova["sid"], _cfg())


@bp.post("/api/conta/senha")
def mudar_senha():
    """Trocar a password. É a ÚNICA coisa que se pode fazer com uma temporária."""
    from . import senha as senha_mod, utilizador

    sess = g.get("sessao")
    if sess is None or not sess.get("user_id"):
        return _resposta("precisas de entrar para trocar a password.", 401)
    if not auth.csrf_valido(sess, _csrf_enviado()):
        return _resposta(
            "o pedido não trazia a marca de segurança (CSRF). Recarrega a "
            "página e tenta outra vez.", 403)

    uid = int(sess["user_id"])
    u = utilizador.registo(uid)
    dados = request.get_json(silent=True) or {}
    con = _auth_con()
    try:
        # O `chave` é o que liga esta rota ao TRAVÃO, e era o que faltava
        # (defeito de 2026-10-01): a falha era registada e nunca travada, por
        # isso quem tivesse uma sessão martelava a password actual sem limite —
        # e cada palpite custava 130 ms e 64 MiB. A política vive toda no
        # `auth.mudar_senha`, com o registo da falha incluído, para não haver
        # duas versões dela.
        auth.mudar_senha(con, uid, dados.get("atual") or "",
                         dados.get("nova") or "",
                         slug=u.get("slug") or "", nome=u.get("nome") or "",
                         chave=_chave_do_pedido())
    except auth.TemDeEsperar as e:
        return _resposta(str(e), 429)
    except auth.ServidorOcupado as e:
        return _resposta(str(e), 503)
    except auth.SenhaErrada as e:
        return _resposta(str(e), 403)
    except senha_mod.SenhaFraca as e:
        return _resposta(str(e), 400)
    except auth.ErroDeAutenticacao as e:
        return _resposta(str(e), 400)

    # SESSÃO NOVA a seguir a trocar a password, e a antiga apagada: se alguém
    # tinha o cookie dela (é a razão de estar a trocar), deixa de valer aqui.
    # As outras sessões dela vão-se todas — entrar outra vez no telemóvel é o
    # preço, e é o que se espera de uma troca de password.
    auth.terminar_todas(con, uid)
    nova = auth.criar_sessao(con, user_id=uid,
                             agente=request.headers.get("User-Agent"),
                             cfg=_cfg())
    resp = jsonify({"ok": True, "csrf": nova["csrf"]})
    return por_cookie(resp, nova["sid"], _cfg())


@bp.post("/api/conta/registar")
def registar():
    """NÃO HÁ REGISTO ABERTO (2026-09-30) — ver `REGISTO_ABERTO`.

    Fica a responder 403 com o que fazer. O corpo antigo (criar a conta a
    quem entrou por OAuth e escolheu um slug) está abaixo e continua a
    funcionar se alguém ligar o interruptor — não se apagou porque o OAuth
    também não se apagou, e sem isto uma pessoa que entre pelo Discord sem
    conta não tem caminho nenhum.
    """
    from . import utilizador

    if not REGISTO_ABERTO:
        return _resposta(
            "as contas não se criam aqui: é o André que as cria, uma a uma. "
            "Pede-lhe uma conta e ele dá-te o nome e uma password temporária.",
            403)

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

"""Identidade emprestada: entra-se com uma conta que já existe.

NUNCA SE GUARDA UMA PASSWORD. Não há campo, não há hash, não há «esqueci-me da
minha». Quem entra prova quem é a um fornecedor que já tem essa
responsabilidade (Google, Discord) e o riftvault fica só com um ponteiro
opaco. A decisão é de 2026-09-29 e está no `docs/contas-e-autenticacao.md`; a
razão curta é que guardar credenciais de amigos num PC de casa, num projeto
pessoal, é assumir um risco que não é preciso assumir.

ONDE VIVEM AS CREDENCIAIS, E PORQUE É QUE NÃO É NO `vault.db`
    `data/auth.db`, um ficheiro à parte e **no `.gitignore`**.

    O `data/vault.db` está commitado num repositório PÚBLICO
    (github.com/Baverone/riftvault) e é empurrado de 30 em 30 minutos pela
    `riftvault-publicar`. O `sub` que o Google ou o Discord dão é um
    identificador estável e único de uma PESSOA: não é uma password, mas posto
    ali ficava publicado para sempre, com histórico, e não se despublica um
    repositório com 95 commits. Por isso a `user_auth` e as `sessions` moram
    fora do Git, e a `users.auth_ref` fica VAZIA — nem um ponteiro opaco lá
    dentro (ver a nota da `utilizador.py`).

    Efeito lateral que também interessa: um `git clone` do repositório público
    não traz sessões de ninguém, e um `git checkout` de um commit antigo não
    ressuscita uma sessão expirada nem uma identidade apagada.

O QUE SE GUARDA DE CADA PESSOA, E MAIS NADA
    `provedor` ('google', 'discord'), `sub` (o id dela nesse fornecedor) e o
    `user_id` daqui. **Nenhum token do fornecedor é gravado** — o `access_token`
    serve para uma pergunta («quem és tu?») e é deitado fora no mesmo pedido.
    O nome só se usa para sugerir um slug no registo; não é credencial.

NÃO SE VERIFICA O `id_token` À MÃO, DE PROPÓSITO
    Validar a assinatura de um JWT exige JWKS, rotação de chaves e RSA, e é um
    dos sítios onde se escrevem falhas com facilidade (o `alg: none`, o `kid`
    não verificado, a expiração esquecida). Em vez disso pergunta-se ao
    fornecedor, por TLS, com o `access_token`: `userinfo` no Google e
    `users/@me` no Discord. Quem autentica a resposta é o TLS, que é a mesma
    garantia em que a troca do código já assenta, e não há criptografia nossa
    para correr mal.

O FORNECEDOR LOCAL SÓ EXISTE EM ENSAIO
    Há um terceiro fornecedor, `local`, que entra sem rede — é o que deixa os
    testes e a prova de ponta a ponta correrem sem falar com o Google. Ele
    **nunca funciona fora da base de ensaio**, e isso é garantido em três
    sítios independentes (`multi.exigir_ensaio` em cada método, a ausência da
    lista de disponíveis, e a própria rota). Ver `test_auth.py`.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import NamedTuple

from . import config

# --------------------------------------------------------------------------
# Constantes de política. Estão aqui, num sítio, para se poderem ler de uma vez.
# --------------------------------------------------------------------------

#: Dias que uma sessão dura sem se mexer nela. 30 é o compromisso: ele mexe na
#: coleção com o telemóvel na mão e não quer entrar a cada vez, e um mês é
#: pouco para um cookie roubado servir de chave permanente.
SESSAO_DIAS = 30

#: Um fluxo de entrada (o `state` a viajar até ao fornecedor e a voltar) tem de
#: se fechar em minutos. Não é para durar uma sessão: é para durar um clique.
PEDIDO_MINUTOS = 15

#: Tentativas de entrada por chave (IP) e por hora. Não é uma password que se
#: adivinha, mas sem tecto isto é um amplificador de pedidos ao Google à custa
#: do IP dele.
TENTATIVAS_POR_HORA = 20

#: Tamanho dos segredos. 32 bytes urlsafe dão 43 caracteres.
BYTES = 32

USER_AGENT = "riftvault/1.0 (colecao pessoal; +github)"  # ASCII puro — ver CLAUDE.md

#: Quanto tempo se espera por um fornecedor antes de desistir.
TIMEOUT = 15


class ErroDeAutenticacao(Exception):
    """Base de tudo o que corre mal a entrar. A mensagem é para se mostrar."""


class ProvedorDesconhecido(ErroDeAutenticacao):
    pass


class ProvedorPorConfigurar(ErroDeAutenticacao):
    """Falta o `client_id`/`client_secret` — e a app diz qual, não rebenta."""


class PedidoInvalido(ErroDeAutenticacao):
    """O `state` não existe, já foi usado, ou expirou."""


class DemasiadasTentativas(ErroDeAutenticacao):
    pass


class PortaFechada(ErroDeAutenticacao):
    """O `multi.aberto` está em `false`: não se entra nem se registra."""


# --------------------------------------------------------------------------
# O ficheiro. Fora do Git, e é o `.gitignore` que o garante.
# --------------------------------------------------------------------------

ESQUEMA = """
-- O mapa identidade -> utilizador. Uma linha por conta LIGADA: a mesma pessoa
-- pode entrar pelo Google e pelo Discord e cair no mesmo `user_id`.
--
-- NÃO GUARDA TOKENS. O `access_token` do fornecedor serve para uma pergunta e
-- morre no mesmo pedido; o que fica é o `sub`, que é o identificador estável
-- dela naquele fornecedor.
CREATE TABLE IF NOT EXISTS user_auth (
    provedor  TEXT    NOT NULL,
    sub       TEXT    NOT NULL,
    user_id   INTEGER NOT NULL,
    nome      TEXT,               -- o que o fornecedor deu, só para mostrar
    criado_em TEXT    NOT NULL,
    visto_em  TEXT,
    PRIMARY KEY (provedor, sub)
);

CREATE INDEX IF NOT EXISTS ix_user_auth_user ON user_auth(user_id);

-- As sessões. O que está na coluna é o SHA-256 do que está no cookie: quem
-- leia este ficheiro não fica com uma sessão utilizável, da mesma maneira que
-- ler uma tabela de hashes não dá a password.
--
-- `user_id` a NULL é uma sessão IDENTIFICADA MAS SEM CONTA: a pessoa provou
-- quem é ao fornecedor e ainda não escolheu o slug. É o estado em que o
-- registo acontece, e é por isso que o `provedor`/`sub` estão aqui. Ao criar a
-- conta o identificador do cookie é ROTADO — uma sessão pré-registo nunca se
-- torna uma sessão de dono com o mesmo valor no cookie.
CREATE TABLE IF NOT EXISTS sessions (
    sid_hash  TEXT    PRIMARY KEY,
    user_id   INTEGER,
    provedor  TEXT,
    sub       TEXT,
    nome      TEXT,
    csrf      TEXT    NOT NULL,
    criado_em TEXT    NOT NULL,
    visto_em  TEXT    NOT NULL,
    expira_em TEXT    NOT NULL,
    agente    TEXT
);

CREATE INDEX IF NOT EXISTS ix_sessions_user ON sessions(user_id);
CREATE INDEX IF NOT EXISTS ix_sessions_expira ON sessions(expira_em);

-- Os fluxos de entrada a meio caminho. O `state` é o que viaja até ao
-- fornecedor e volta, e é aqui que se prova que voltou o NOSSO: uma linha, uma
-- vez só (apaga-se ao usar), com prazo. Sem isto um terceiro podia fazer o
-- browser dele concluir uma entrada que ele não começou.
--
-- O `verifier` é o PKCE: o código que volta pelo browser só serve a quem tiver
-- este segredo, que nunca sai daqui.
-- O `nonce_hash` ata o pedido AO BROWSER que o começou, e é o que impede o
-- «login CSRF»: sem ele, alguém podia começar uma entrada, ficar com um `state`
-- válido, e depois levar outra pessoa a abrir o endereço de volta — o browser
-- dela acabava com uma sessão da conta DELE, e o que ela escrevesse a seguir ia
-- para a coleção dele. Guarda-se o SHA-256; o valor em claro vive num cookie
-- curto que só aquele browser tem.
-- O `liga_a` é o que resolve o problema do PRIMEIRO utilizador: o André já
-- existe (é o 1, com o slug `baverone`) e não se pode «registar», porque o slug
-- dele já é dele. Um pedido com `liga_a` preenchido não cria conta nenhuma —
-- LIGA a identidade a uma conta que já existe. Ver `criar_convite`.
CREATE TABLE IF NOT EXISTS auth_pedidos (
    state      TEXT    PRIMARY KEY,
    provedor   TEXT    NOT NULL,
    verifier   TEXT    NOT NULL,
    destino    TEXT,
    nonce_hash TEXT,
    liga_a     INTEGER,
    criado_em  TEXT    NOT NULL
);

-- CONVITES DE LIGAÇÃO. Um código de uso único, criado na CONSOLA
-- (`riftvault multi --ligar`), que autoriza a próxima entrada a ligar-se a uma
-- conta que já existe em vez de criar outra.
--
-- Quem tem a consola do PC é o dono do PC — e isso é uma prova de posse mais
-- forte do que qualquer verificação de endereço. É de propósito que não há
-- atalho por IP em lado nenhum deste módulo: o túnel da Cloudflare faz a
-- internet inteira chegar ao Flask como `127.0.0.1`, e uma regra que confiasse
-- no loopback dava a conta do André a qualquer visitante.
--
-- É também o que faz isto funcionar com a PORTA FECHADA: ele liga a conta
-- ANTES de abrir, e por isso nunca se abre a porta com ele do lado de fora.
CREATE TABLE IF NOT EXISTS auth_convites (
    token_hash TEXT    PRIMARY KEY,
    user_id    INTEGER NOT NULL,
    criado_em  TEXT    NOT NULL,
    usado_em   TEXT
);

-- As tentativas, para o tecto por hora. Guarda-se a chave (o IP) e não o que
-- se tentou.
CREATE TABLE IF NOT EXISTS auth_tentativas (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    ts       TEXT    NOT NULL,
    chave    TEXT    NOT NULL,
    provedor TEXT,
    ok       INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_tentativas_chave ON auth_tentativas(chave, ts);
"""


def caminho() -> Path:
    """O ficheiro das credenciais. Segue o `RIFTVAULT_DATA`, logo segue o ensaio."""
    return Path(os.environ.get("RIFTVAULT_AUTH", config.DATA_DIR / "auth.db"))


def abrir() -> sqlite3.Connection:
    """Abre (e cria) o `auth.db`. Sem catálogo nem preços anexados: aqui não há cartas."""
    p = caminho()
    p.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(p)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    con.executescript(ESQUEMA)
    _migrar(con)
    con.commit()
    return con


def _migrar(con: sqlite3.Connection) -> None:
    """Colunas que nasceram depois do ficheiro.

    O `CREATE TABLE IF NOT EXISTS` não acrescenta colunas a uma tabela que já
    exista — é a mesma armadilha do `db._migrar_price_latest`. Aqui não há dados
    de ninguém em risco (o `auth.db` é sessões e ponteiros), mas apagá-lo
    obrigava todos a entrar outra vez.
    """
    tem = {r["name"] for r in con.execute("PRAGMA table_info(auth_pedidos)")}
    if "liga_a" not in tem:
        con.execute("ALTER TABLE auth_pedidos ADD COLUMN liga_a INTEGER")


def _agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _mais(segundos: float) -> str:
    return (datetime.now(timezone.utc)
            + timedelta(seconds=segundos)).isoformat(timespec="seconds")


def _passou(quando: str) -> bool:
    try:
        return datetime.fromisoformat(quando) < datetime.now(timezone.utc)
    except ValueError:
        # Uma data ilegível conta como expirada: na dúvida, não se deixa entrar.
        return True


def _hash(valor: str) -> str:
    return hashlib.sha256(valor.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# Os fornecedores
# --------------------------------------------------------------------------


class Identidade(NamedTuple):
    """Quem o fornecedor diz que é. É tudo o que se leva dele."""

    provedor: str
    sub: str
    nome: str


def _pedir(url: str, *, dados: dict | None = None,
           token: str | None = None) -> dict:
    """Um pedido JSON ao fornecedor. Extraído para os testes o poderem trocar."""
    corpo = urllib.parse.urlencode(dados).encode() if dados else None
    cabecalhos = {"Accept": "application/json", "User-Agent": USER_AGENT}
    if token:
        cabecalhos["Authorization"] = f"Bearer {token}"
    if corpo is not None:
        cabecalhos["Content-Type"] = "application/x-www-form-urlencoded"
    pedido = urllib.request.Request(url, data=corpo, headers=cabecalhos)
    try:
        with urllib.request.urlopen(pedido, timeout=TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        # A mensagem do fornecedor ajuda a perceber um `client_secret` errado;
        # o corpo não leva segredos nossos.
        detalhe = e.read()[:400].decode("utf-8", "replace")
        raise ErroDeAutenticacao(
            f"o fornecedor respondeu {e.code} a {urllib.parse.urlsplit(url).netloc}: "
            f"{detalhe}") from e
    except (urllib.error.URLError, TimeoutError, ValueError) as e:
        raise ErroDeAutenticacao(
            f"não foi possível falar com {urllib.parse.urlsplit(url).netloc}: {e}") from e


class Provedor:
    """Um sítio onde a pessoa já tem conta.

    Subclasses preenchem os endereços e a leitura da identidade. O resto — o
    `state`, o PKCE, o que se guarda — é igual para todos e vive aqui.
    """

    nome = ""
    etiqueta = ""
    escopo = ""
    url_autorizar = ""
    url_token = ""
    url_quem = ""
    #: `false` no fornecedor local, que não anda pelo browser.
    redireciona = True

    # -- config -----------------------------------------------------------

    def _bloco(self, cfg: dict | None = None) -> dict:
        cfg = cfg if cfg is not None else config.load()
        return ((cfg.get("auth") or {}).get(self.nome) or {})

    def var_segredo(self) -> str:
        return f"RIFTVAULT_{self.nome.upper()}_SECRET"

    def segredo(self, cfg: dict | None = None) -> str:
        """O `client_secret`, DO AMBIENTE de preferência.

        É a regra desta casa e está escrita no `.gitignore`: *«Segredos: o
        CARDTRADER_TOKEN vive no ambiente, nunca em ficheiro»*. E aqui não é
        preciosismo — o `riftvault_config.json` **está commitado** (confirmado:
        `git ls-files riftvault_config.json`) num repositório PÚBLICO que é
        empurrado de 30 em 30 minutos. Um `client_secret` colado lá dentro ia
        para o GitHub no push seguinte e não se despublica: teria de ser
        revogado no Discord.

        Aceita-se o config como último recurso porque um segredo que funciona é
        melhor do que um utilizador trancado de fora — mas o `multi --verificar`
        avisa, com o comando para o tirar de lá.

        O `client_id` NÃO é segredo (viaja no endereço de autorização, à vista
        de quem entra) e vive no config sem problema.
        """
        do_ambiente = os.environ.get(self.var_segredo(), "").strip()
        if do_ambiente:
            return do_ambiente
        return str(self._bloco(cfg).get("client_secret") or "").strip()

    def segredo_no_config(self, cfg: dict | None = None) -> bool:
        """O segredo está no ficheiro (e não no ambiente)? — para o aviso."""
        return (not os.environ.get(self.var_segredo(), "").strip()
                and bool(str(self._bloco(cfg).get("client_secret") or "").strip()))

    def em_falta(self, cfg: dict | None = None) -> list[str]:
        """O que falta para este fornecedor servir. Lista vazia = pronto."""
        falta = []
        if not str(self._bloco(cfg).get("client_id") or "").strip():
            falta.append("client_id")
        if not self.segredo(cfg):
            falta.append("client_secret")
        return falta

    def configurado(self, cfg: dict | None = None) -> bool:
        return not self.em_falta(cfg)

    def exigir_configurado(self, cfg: dict | None = None) -> None:
        falta = self.em_falta(cfg)
        if falta:
            raise ProvedorPorConfigurar(
                f"o {self.etiqueta} ainda não está configurado: falta "
                f"{' e '.join(falta)} em `auth.{self.nome}` do "
                f"riftvault_config.json. Ver docs/abrir-a-porta.md.")

    # -- o fluxo ----------------------------------------------------------

    def url_de_entrada(self, *, client_id: str, redirect_uri: str,
                       state: str, desafio: str) -> str:
        campos = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": self.escopo,
            "state": state,
            # PKCE: o fornecedor guarda o desafio e só aceita a troca de quem
            # souber o `verifier`. É o que impede um código apanhado no
            # caminho de valer alguma coisa.
            "code_challenge": desafio,
            "code_challenge_method": "S256",
        }
        return self.url_autorizar + "?" + urllib.parse.urlencode(campos)

    def trocar(self, *, code: str, verifier: str, redirect_uri: str,
               cfg: dict | None = None) -> str:
        """O código que voltou pelo browser -> um `access_token`, que não se guarda."""
        b = self._bloco(cfg)
        resp = _pedir(self.url_token, dados={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": b.get("client_id", ""),
            # Pelo `segredo()`, que prefere o AMBIENTE — se isto lesse o config
            # direto, pôr o segredo na variável não servia de nada.
            "client_secret": self.segredo(cfg),
            "code_verifier": verifier,
        })
        token = resp.get("access_token")
        if not token:
            raise ErroDeAutenticacao(
                f"o {self.etiqueta} não devolveu um access_token")
        return token

    def quem(self, token: str) -> Identidade:  # pragma: no cover - subclasse
        raise NotImplementedError

    def identidade(self, *, code: str, verifier: str, redirect_uri: str,
                   cfg: dict | None = None) -> Identidade:
        self.exigir_configurado(cfg)
        return self.quem(self.trocar(code=code, verifier=verifier,
                                     redirect_uri=redirect_uri, cfg=cfg))


class Google(Provedor):
    nome = "google"
    etiqueta = "Google"
    # `openid profile` e mais nada. Não se pede o email: não faz falta para
    # saber quem é (o `sub` é que identifica) e é menos um dado de terceiros a
    # guardar num PC de casa.
    escopo = "openid profile"
    url_autorizar = "https://accounts.google.com/o/oauth2/v2/auth"
    url_token = "https://oauth2.googleapis.com/token"
    url_quem = "https://openidconnect.googleapis.com/v1/userinfo"

    def quem(self, token: str) -> Identidade:
        d = _pedir(self.url_quem, token=token)
        sub = str(d.get("sub") or "").strip()
        if not sub:
            raise ErroDeAutenticacao("o Google não disse quem era (sem `sub`)")
        return Identidade("google", sub, str(d.get("name") or "").strip())


class Discord(Provedor):
    nome = "discord"
    etiqueta = "Discord"
    # `identify` dá o id e o nome, e mais nada. Sem `email`, sem `guilds`.
    escopo = "identify"
    url_autorizar = "https://discord.com/oauth2/authorize"
    url_token = "https://discord.com/api/oauth2/token"
    url_quem = "https://discord.com/api/users/@me"

    def quem(self, token: str) -> Identidade:
        d = _pedir(self.url_quem, token=token)
        sub = str(d.get("id") or "").strip()
        if not sub:
            raise ErroDeAutenticacao("o Discord não disse quem era (sem `id`)")
        nome = str(d.get("global_name") or d.get("username") or "").strip()
        return Identidade("discord", sub, nome)


class Local(Provedor):
    """Entrar sem rede — SÓ na base de ensaio.

    Existe para os testes e para a prova de ponta a ponta poderem registar e
    editar sem falar com o Google. Fora do ensaio **não funciona**, e não é por
    convenção: cada método começa por `multi.exigir_ensaio`, que rebenta.

    Isto é deliberadamente independente do `multi.aberto`: mesmo com a porta
    aberta, o fornecedor local continua a não servir em produção. São duas
    perguntas diferentes e um `and` esquecido não abre esta.
    """

    nome = "local"
    etiqueta = "Entrada local (ensaio)"
    redireciona = False

    def _so_em_ensaio(self) -> None:
        from . import multi
        multi.exigir_ensaio("o fornecedor de autenticação local")

    def em_falta(self, cfg: dict | None = None) -> list[str]:
        # Não tem credenciais para faltar; o que lhe falta é o ensaio.
        from . import multi
        return [] if multi.ensaio() else ["RIFTVAULT_ENSAIO"]

    def url_de_entrada(self, **_kw) -> str:
        self._so_em_ensaio()
        raise ErroDeAutenticacao(
            "o fornecedor local não passa pelo browser: usa-se o `sub` direto")

    def trocar(self, **_kw) -> str:  # pragma: no cover - não há troca
        self._so_em_ensaio()
        raise ErroDeAutenticacao("o fornecedor local não troca códigos")

    def quem(self, token: str) -> Identidade:
        self._so_em_ensaio()
        return Identidade("local", str(token), str(token))

    def identidade(self, *, code: str, verifier: str = "",
                   redirect_uri: str = "", cfg: dict | None = None) -> Identidade:
        """No local o `code` É o `sub`: é a pessoa que se está a fingir."""
        self._so_em_ensaio()
        sub = str(code or "").strip()
        if not sub:
            raise ErroDeAutenticacao("falta dizer quem entra (`sub`)")
        return Identidade("local", sub, sub)


GOOGLE = Google()
DISCORD = Discord()
LOCAL = Local()

#: Pela ordem em que se mostram. O local fica no fim e só aparece em ensaio.
TODOS: tuple[Provedor, ...] = (GOOGLE, DISCORD, LOCAL)


def provedor(nome: str) -> Provedor:
    for p in TODOS:
        if p.nome == nome:
            return p
    raise ProvedorDesconhecido(
        f"fornecedor «{nome}» não existe; há "
        f"{', '.join(p.nome for p in TODOS)}")


def disponiveis(cfg: dict | None = None) -> list[dict]:
    """Os que dão para usar AGORA. Vazio é uma resposta legítima (é o de hoje).

    O local só entra em ensaio; os outros só entram configurados. Cada entrada
    diz o que lhe falta, para a página poder explicar em vez de não mostrar
    nada.
    """
    from . import multi
    fora = []
    for p in TODOS:
        if p is LOCAL and not multi.ensaio():
            continue
        fora.append({"nome": p.nome, "etiqueta": p.etiqueta,
                     "pronto": p.configurado(cfg),
                     "falta": p.em_falta(cfg)})
    return fora


def prontos(cfg: dict | None = None) -> list[dict]:
    return [p for p in disponiveis(cfg) if p["pronto"]]


# --------------------------------------------------------------------------
# PKCE
# --------------------------------------------------------------------------


def _b64(bruto: bytes) -> str:
    return base64.urlsafe_b64encode(bruto).decode().rstrip("=")


def par_pkce() -> tuple[str, str]:
    """(`verifier`, `desafio`). O primeiro fica no servidor, o segundo viaja."""
    verifier = _b64(secrets.token_bytes(BYTES))
    desafio = _b64(hashlib.sha256(verifier.encode("ascii")).digest())
    return verifier, desafio


# --------------------------------------------------------------------------
# O tecto de tentativas
# --------------------------------------------------------------------------


def tentativas_por_hora(cfg: dict | None = None) -> int:
    cfg = cfg if cfg is not None else config.load()
    valor = (cfg.get("auth") or {}).get("tentativas_por_hora", TENTATIVAS_POR_HORA)
    try:
        n = int(valor)
    except (TypeError, ValueError):
        raise ValueError(
            f"auth.tentativas_por_hora tem de ser um número, não {valor!r}")
    if n < 1:
        raise ValueError("auth.tentativas_por_hora tem de ser pelo menos 1")
    return n


def registar_tentativa(con: sqlite3.Connection, chave: str,
                       provedor_nome: str | None, ok: bool) -> None:
    con.execute("INSERT INTO auth_tentativas (ts, chave, provedor, ok) "
                "VALUES (?, ?, ?, ?)",
                (_agora(), chave or "?", provedor_nome, 1 if ok else 0))
    con.commit()


def tentativas_recentes(con: sqlite3.Connection, chave: str) -> int:
    desde = _mais(-3600)
    row = con.execute(
        "SELECT COUNT(*) AS n FROM auth_tentativas WHERE chave = ? AND ts >= ?",
        (chave or "?", desde)).fetchone()
    return int(row["n"])


def exigir_folga(con: sqlite3.Connection, chave: str,
                 cfg: dict | None = None) -> None:
    tecto = tentativas_por_hora(cfg)
    if tentativas_recentes(con, chave) >= tecto:
        raise DemasiadasTentativas(
            f"demasiadas tentativas de entrada ({tecto} na última hora). "
            f"Espera um pouco e tenta outra vez.")


# --------------------------------------------------------------------------
# Os pedidos a meio caminho
# --------------------------------------------------------------------------


#: O cookie curto que ata a entrada ao browser que a começou.
COOKIE_NONCE = "riftvault_entrada"


def comecar(con: sqlite3.Connection, nome: str, *, redirect_uri: str,
            destino: str | None = None, liga_a: int | None = None,
            cfg: dict | None = None) -> dict:
    """Prepara uma entrada: devolve o endereço e o `nonce` para o cookie.

    Com `liga_a`, esta entrada LIGA-SE a uma conta que já existe em vez de
    oferecer o registo — é o caminho do primeiro utilizador (ver `criar_convite`).
    """
    p = provedor(nome)
    p.exigir_configurado(cfg)
    verifier, desafio = par_pkce()
    state = secrets.token_urlsafe(BYTES)
    nonce = secrets.token_urlsafe(BYTES)
    con.execute("INSERT INTO auth_pedidos (state, provedor, verifier, destino, "
                "nonce_hash, liga_a, criado_em) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (state, p.nome, verifier, destino, _hash(nonce), liga_a, _agora()))
    con.commit()
    b = p._bloco(cfg)
    return {"state": state, "nonce": nonce,
            "url": p.url_de_entrada(client_id=b.get("client_id", ""),
                                    redirect_uri=redirect_uri, state=state,
                                    desafio=desafio)}


def consumir_pedido(con: sqlite3.Connection, state: str,
                    nonce: str | None = None) -> dict:
    """Levanta o pedido e APAGA-O. Um `state` serve uma vez e só uma.

    O `nonce` é o do cookie e tem de bater com o que se guardou. É o que impede
    o «login CSRF»: sem ele, quem começasse uma entrada podia levar outra pessoa
    a concluí-la, e o browser dela ficava com uma sessão da conta de quem
    começou — e o que ela escrevesse a seguir ia para a coleção dele.
    """
    row = con.execute("SELECT * FROM auth_pedidos WHERE state = ?",
                      (state or "",)).fetchone()
    if row is None:
        raise PedidoInvalido(
            "esta entrada não é válida (ou já foi usada). Tenta outra vez.")
    con.execute("DELETE FROM auth_pedidos WHERE state = ?", (state,))
    con.commit()
    # O PRAZO primeiro, e a ordem é por causa da MENSAGEM: quem demorou
    # vinte minutos a entrar também já perdeu o cookie, e dizer-lhe «não
    # começou neste browser» mandava-o procurar um problema que não tem. Os dois
    # recusam; o que muda é o que ele lê.
    if _passou((datetime.fromisoformat(row["criado_em"])
                + timedelta(minutes=PEDIDO_MINUTOS)).isoformat()):
        raise PedidoInvalido(
            f"esta entrada demorou mais de {PEDIDO_MINUTOS} minutos. "
            f"Tenta outra vez.")
    esperado = row["nonce_hash"]
    if esperado and not hmac.compare_digest(esperado, _hash(nonce or "")):
        raise PedidoInvalido(
            "esta entrada não começou neste browser. Volta ao início e entra "
            "outra vez.")
    return dict(row)


def limpar_pedidos(con: sqlite3.Connection) -> int:
    limite = _mais(-PEDIDO_MINUTOS * 60)
    cur = con.execute("DELETE FROM auth_pedidos WHERE criado_em < ?", (limite,))
    con.commit()
    return cur.rowcount


# --------------------------------------------------------------------------
# Convites de ligação — o caminho do PRIMEIRO utilizador
# --------------------------------------------------------------------------
#
# O André já existe: é o utilizador 1, com o slug `baverone`. Na primeira vez
# que entrasse com o Discord, o riftvault não o reconhecia (não há identidade
# ligada) e oferecia-lhe o REGISTO — e o registo pedia um slug que ele não podia
# escolher, porque o dele já é dele. Ficava a olhar para um formulário sem saída,
# e a coleção de um mês do outro lado.
#
# A saída é um código de uso único, criado na consola do PC dele.

CONVITE_MINUTOS = 30


def criar_convite(con: sqlite3.Connection, user_id: int) -> str:
    """Um código de uso único que liga a próxima entrada a esta conta.

    Devolve-o EM CLARO — é a única vez que existe; na base fica o SHA-256.
    """
    token = secrets.token_urlsafe(BYTES)
    con.execute("INSERT INTO auth_convites (token_hash, user_id, criado_em) "
                "VALUES (?, ?, ?)", (_hash(token), int(user_id), _agora()))
    con.commit()
    return token


def usar_convite(con: sqlite3.Connection, token: str) -> int:
    """Gasta o convite e devolve o `user_id`. Uma vez e só uma."""
    row = con.execute("SELECT * FROM auth_convites WHERE token_hash = ?",
                      (_hash(token or ""),)).fetchone()
    if row is None:
        raise PedidoInvalido(
            "este código de ligação não existe. Corre `riftvault multi --ligar` "
            "outra vez.")
    if row["usado_em"]:
        raise PedidoInvalido(
            "este código de ligação já foi usado. Corre `riftvault multi "
            "--ligar` outra vez.")
    if _passou((datetime.fromisoformat(row["criado_em"])
                + timedelta(minutes=CONVITE_MINUTOS)).isoformat()):
        con.execute("DELETE FROM auth_convites WHERE token_hash = ?",
                    (row["token_hash"],))
        con.commit()
        raise PedidoInvalido(
            f"este código de ligação passou dos {CONVITE_MINUTOS} minutos. "
            f"Corre `riftvault multi --ligar` outra vez.")
    con.execute("UPDATE auth_convites SET usado_em = ? WHERE token_hash = ?",
                (_agora(), row["token_hash"]))
    con.commit()
    return int(row["user_id"])


# --------------------------------------------------------------------------
# Sessões
# --------------------------------------------------------------------------

#: O nome do cookie. `__Host-` obriga o browser a exigir HTTPS e a não deixar
#: um subdomínio escrevê-lo — mas também proíbe `Domain`, e nós precisamos de
#: `Domain` para o cookie valer em `<nome>.rift.baverone.com`. Por isso fica o
#: nome simples e as propriedades postas à mão; ver `server.py`.
COOKIE = "riftvault_sessao"


def sessao_dias(cfg: dict | None = None) -> int:
    cfg = cfg if cfg is not None else config.load()
    valor = (cfg.get("auth") or {}).get("sessao_dias", SESSAO_DIAS)
    try:
        n = int(valor)
    except (TypeError, ValueError):
        raise ValueError(f"auth.sessao_dias tem de ser um número, não {valor!r}")
    if n < 1:
        raise ValueError("auth.sessao_dias tem de ser pelo menos 1")
    return n


def criar_sessao(con: sqlite3.Connection, *, user_id: int | None = None,
                 identidade: Identidade | None = None,
                 agente: str | None = None,
                 cfg: dict | None = None) -> dict:
    """Uma sessão nova. Devolve o `sid` EM CLARO — é a única vez que ele existe.

    `user_id` a `None` com `identidade` preenchida é a sessão pré-registo: a
    pessoa já provou quem é e ainda não tem conta.
    """
    sid = secrets.token_urlsafe(BYTES)
    csrf = secrets.token_urlsafe(BYTES)
    agora = _agora()
    # Uma sessão PRÉ-REGISTO (sem dono) vale uma hora, não trinta dias: é só o
    # tempo de escolher um nome. Quem entrou e desistiu não fica com um cookie
    # válido um mês, e as linhas de registos que nunca aconteceram desaparecem
    # sozinhas na primeira limpeza.
    prazo = (sessao_dias(cfg) * 86400) if user_id is not None else 3600
    con.execute(
        "INSERT INTO sessions (sid_hash, user_id, provedor, sub, nome, csrf, "
        "criado_em, visto_em, expira_em, agente) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (_hash(sid), user_id,
         identidade.provedor if identidade else None,
         identidade.sub if identidade else None,
         identidade.nome if identidade else None,
         csrf, agora, agora, _mais(prazo), (agente or "")[:200]))
    con.commit()
    return {"sid": sid, "csrf": csrf, "user_id": user_id}


def sessao(con: sqlite3.Connection, sid: str | None) -> dict | None:
    """A sessão daquele cookie, ou `None`. Uma expirada é apagada e vale `None`."""
    if not sid:
        return None
    row = con.execute("SELECT * FROM sessions WHERE sid_hash = ?",
                      (_hash(sid),)).fetchone()
    if row is None:
        return None
    if _passou(row["expira_em"]):
        con.execute("DELETE FROM sessions WHERE sid_hash = ?", (row["sid_hash"],))
        con.commit()
        return None
    return dict(row)


#: Só se adia a expiração se a última vez foi há mais do que isto.
TOCAR_CADA_S = 3600


def tocar(con: sqlite3.Connection, sid: str, cfg: dict | None = None,
          visto_em: str | None = None) -> bool:
    """Mexeu-se: adia a expiração. É o que faz a sessão durar enquanto se usa.

    **Só escreve uma vez por hora**, e isso é o ponto. Uma página da Coleção
    puxa o payload, o índice e dezenas de imagens; escrever na base a cada
    pedido punha o `auth.db` a levar centenas de `UPDATE` por minuto só para
    adiar uma data que faltam 30 dias para chegar. Com a folga de uma hora a
    sessão continua a durar enquanto se usa e o custo desaparece.

    Devolve `True` se escreveu, para dar para testar.
    """
    if visto_em:
        try:
            desde = (datetime.now(timezone.utc)
                     - datetime.fromisoformat(visto_em)).total_seconds()
        except ValueError:
            desde = TOCAR_CADA_S + 1  # data ilegível: reescreve-se
        if desde < TOCAR_CADA_S:
            return False
    con.execute("UPDATE sessions SET visto_em = ?, expira_em = ? WHERE sid_hash = ?",
                (_agora(), _mais(sessao_dias(cfg) * 86400), _hash(sid)))
    con.commit()
    return True


def ligar_conta(con: sqlite3.Connection, sid_antigo: str, user_id: int,
                cfg: dict | None = None) -> dict:
    """A sessão pré-registo passa a ser de um dono — COM IDENTIFICADOR NOVO.

    Rotação no login: o valor que andou pelo browser antes de haver conta não
    é o que passa a dar acesso à conta. Se alguém tivesse fixado aquele cookie,
    deixa de valer no instante em que a conta nasce.
    """
    antiga = sessao(con, sid_antigo)
    if antiga is None:
        raise PedidoInvalido("a sessão expirou a meio do registo. Entra outra vez.")
    ident = None
    if antiga.get("provedor") and antiga.get("sub"):
        ident = Identidade(antiga["provedor"], antiga["sub"], antiga.get("nome") or "")
    nova = criar_sessao(con, user_id=user_id, identidade=ident,
                        agente=antiga.get("agente"), cfg=cfg)
    con.execute("DELETE FROM sessions WHERE sid_hash = ?", (_hash(sid_antigo),))
    con.commit()
    return nova


def terminar(con: sqlite3.Connection, sid: str) -> None:
    con.execute("DELETE FROM sessions WHERE sid_hash = ?", (_hash(sid),))
    con.commit()


def terminar_todas(con: sqlite3.Connection, user_id: int) -> int:
    cur = con.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
    con.commit()
    return cur.rowcount


def limpar_expiradas(con: sqlite3.Connection) -> int:
    cur = con.execute("DELETE FROM sessions WHERE expira_em < ?", (_agora(),))
    con.commit()
    return cur.rowcount


# --------------------------------------------------------------------------
# CSRF
# --------------------------------------------------------------------------


def csrf_valido(sess: dict | None, enviado: str | None) -> bool:
    """Comparação em tempo constante. Sem sessão não há token válido nenhum."""
    if not sess or not enviado:
        return False
    return hmac.compare_digest(str(sess.get("csrf") or ""), str(enviado))


# --------------------------------------------------------------------------
# Entrar e registar
# --------------------------------------------------------------------------


def exigir_porta_aberta(cfg: dict | None = None) -> None:
    """A porta manda em tudo o que é identidade. Fechada, ninguém entra.

    É o `multi.aberto` da `1-multi-guardas`: uma leitura só, aqui, e não uma
    condição espalhada por cada rota.
    """
    from . import multi
    if not multi.aberto(cfg):
        raise PortaFechada(
            "as contas ainda não estão abertas. O André abre-as quando quiser "
            "(`riftvault multi --abrir`); até lá o riftvault é de um só dono.")


def por_identidade(con: sqlite3.Connection, ident: Identidade) -> int | None:
    row = con.execute(
        "SELECT user_id FROM user_auth WHERE provedor = ? AND sub = ?",
        (ident.provedor, ident.sub)).fetchone()
    return int(row["user_id"]) if row else None


def guardar_identidade(con: sqlite3.Connection, ident: Identidade,
                       user_id: int) -> None:
    """Liga a identidade a um utilizador. Idempotente."""
    agora = _agora()
    con.execute(
        "INSERT INTO user_auth (provedor, sub, user_id, nome, criado_em, visto_em) "
        "VALUES (?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(provedor, sub) DO UPDATE SET user_id = excluded.user_id, "
        "nome = excluded.nome, visto_em = excluded.visto_em",
        (ident.provedor, ident.sub, user_id, ident.nome, agora, agora))
    con.commit()


def identidades_de(con: sqlite3.Connection, user_id: int) -> list[dict]:
    """As contas ligadas àquele utilizador. **Sem o `sub`** — não é para mostrar."""
    return [{"provedor": r["provedor"], "nome": r["nome"],
             "criado_em": r["criado_em"], "visto_em": r["visto_em"]}
            for r in con.execute(
                "SELECT provedor, nome, criado_em, visto_em FROM user_auth "
                "WHERE user_id = ? ORDER BY criado_em", (user_id,))]


def esquecer_identidades(con: sqlite3.Connection, user_id: int) -> dict:
    """Apaga as credenciais e as sessões de um utilizador.

    Chamado ao apagar a conta, no mesmo passo do `conta.apagar`: a `user_auth`
    é desta casa e a limpeza também (combinado com a `1-multi-guardas`, que
    não mexe numa tabela que não é dela).
    """
    n_ident = con.execute("DELETE FROM user_auth WHERE user_id = ?",
                          (user_id,)).rowcount
    n_sess = con.execute("DELETE FROM sessions WHERE user_id = ?",
                         (user_id,)).rowcount
    con.commit()
    return {"identidades": n_ident, "sessoes": n_sess}


# --------------------------------------------------------------------------
# O slug do subdomínio
# --------------------------------------------------------------------------

#: Nomes que não se podem usar: são caminhos do serviço, hospedeiros que vão
#: existir, ou coisas que enganam quem lê o endereço.
RESERVADOS = frozenset({
    "www", "api", "admin", "administrator", "rift", "riftvault", "root",
    "static", "img", "images", "assets", "site", "docs", "doc", "help",
    "ajuda", "login", "logout", "entrar", "sair", "registo", "registar",
    "conta", "contas", "u", "user", "users", "utilizador", "utilizadores",
    "mail", "email", "smtp", "imap", "ns", "ns1", "ns2", "dns", "mx",
    "cdn", "cloud", "test", "teste", "ensaio", "dev", "staging", "beta",
    "status", "blog", "shop", "loja", "pay", "sec", "security", "abuse",
    "postmaster", "hostmaster", "webmaster", "support", "suporte", "app",
    "me", "null", "none", "undefined", "andre", "baverone",
})

# Dois caracteres no mínimo, 32 no máximo, e nem o primeiro nem o último é
# hífen. O meio é o único sítio onde o hífen entra — é a regra de um rótulo de
# DNS, e é ela que faz `<slug>.rift.baverone.com` ser um endereço legal.
_SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{0,30}[a-z0-9]$")


def limpar_slug(bruto: str) -> str:
    """Sugere um slug a partir de um nome. Só sugere — quem decide é a pessoa."""
    import unicodedata
    sem_acentos = "".join(
        c for c in unicodedata.normalize("NFKD", str(bruto or ""))
        if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9]+", "-", sem_acentos.lower()).strip("-")
    return s[:32].strip("-")


def validar_slug(slug: str) -> str:
    """As regras do subdomínio. Rebenta com a razão, em português.

    Não chama o `utilizador.validar_slug` (que é o da `0-multi-utilizador-1`):
    acrescenta-lhe as regras que são DESTA fatia — os nomes reservados e o
    comprimento de um rótulo de DNS. O `utilizador.criar` valida outra vez, e
    é bom que valide: duas verificações não fazem mal, uma esquecida faz.
    """
    s = str(slug or "").strip().lower()
    if not s:
        raise ValueError("falta escolher o nome do endereço.")
    if s != str(slug or "").strip():
        # Não se corrige em silêncio: o endereço é o que ele vai escrever.
        raise ValueError(
            f"o nome do endereço tem de ser em minúsculas — quiseste dizer «{s}»?")
    # Os reservados vêm ANTES das regras de forma, de propósito: `u` e `ns` são
    # reservados E curtos, e dizer-lhe «precisa de dois caracteres» mandava-o
    # tentar `uu` quando o problema era outro. A razão mais útil primeiro.
    if s in RESERVADOS:
        raise ValueError(
            f"«{s}» está reservado para o serviço — escolhe outro nome.")
    if len(s) > 32:
        raise ValueError("o nome do endereço não pode passar dos 32 caracteres.")
    if not _SLUG.match(s):
        raise ValueError(
            "o nome do endereço só pode ter letras sem acentos, números e "
            "hifens, e tem de começar e acabar por letra ou número "
            "(dois caracteres, no mínimo).")
    if "--" in s:
        # `xn--` é o prefixo dos domínios internacionalizados; um rótulo com
        # `--` na terceira e quarta posição é lido como punycode por alguns
        # resolvedores. Proibir o par é mais simples do que explicar.
        raise ValueError("o nome do endereço não pode ter dois hifens seguidos.")
    return s


def slug_livre(slug: str) -> bool:
    """Há alguém com este slug? (O `utilizador` é que sabe; aqui só se pergunta.)"""
    from . import utilizador
    return utilizador.por_slug(slug, obrigatorio=False) is None


def exigir_slug(slug: str) -> str:
    s = validar_slug(slug)
    if not slug_livre(s):
        raise ValueError(f"o endereço «{s}» já está a ser usado. Escolhe outro.")
    return s

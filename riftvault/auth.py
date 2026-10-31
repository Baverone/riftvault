"""Quem entra, e como: password própria (2026-09-30) ou conta emprestada.

**MUDOU A 2026-09-30, por ordem dele.** Este ficheiro nasceu a 29/09 a dizer
«NUNCA SE GUARDA UMA PASSWORD»; no dia seguinte o André pediu o contrário —
*"em vez de discord, nao era melhor a pessoa criar uma conta com usuario e
password e ficar guardado em base de dados??"* — e é o que está.

O QUE FICA DA FRASE ANTIGA, E É O QUE INTERESSA: **a password continua a não
se poder LER.** O que vai para a base é um hash de `scrypt` com sal por
pessoa, que não se inverte, e quem se esquecer não recebe a que tinha — recebe
uma NOVA, temporária, que é obrigado a trocar. Toda a criptografia disto vive
no `riftvault/senha.py`, com os parâmetros medidos e a razão escrita.

**DESDE 2026-10-31 AS PASSWORDS MORAM NO COFRE DE CONTAS**, partilhado com o
mtgvault (o pacote `contas`; `riftvault/cofre.py` diz onde está). O hash, o
travão das tentativas e a fila do scrypt foram para lá tal e qual, e o
`riftvault/senha.py` passou a ser um alias do `contas/senha.py`. Ficam aqui, no
`auth.db`, as sessões (que levam a GERAÇÃO da password, ver `sessao`), o
OAuth, os convites e o tecto do OAuth; a `user_senha` fica, sem uso, como
arquivo. Ver o bloco «AS PASSWORDS MORAM NO COFRE».

    riftvault conta --criar <nome>            cria e diz uma temporária
    riftvault conta <nome> --nova-password    diz outra (o «esqueci-me»)

**AS CONTAS NASCEM DE UM COMANDO DELE E DE MAIS NADA.** Não há registo aberto:
ver `rotas_conta.REGISTO_ABERTO`. É o que ele quer — *"isto e uma coisa
caseira, para usar entre amigos"*.

O OAUTH (Google e Discord) FICA, PARADO
    O código de 29/09 está inteiro e testado, e um dia pode servir. **Sem
    segredo configurado o botão não aparece** (`disponiveis`, campo `pronto`), e o
    `auth.discord.client_id` fica onde está. Não se apagou nada: ver o pedido
    de 2026-09-30, ponto 6.

ONDE VIVEM AS CREDENCIAIS, E PORQUE É QUE NÃO É NO `vault.db`
    `data/auth.db`, um ficheiro à parte e **no `.gitignore`**.

    Com passwords lá dentro isto passou de cuidado a essencial. O
    `data/vault.db` está commitado num repositório PÚBLICO
    (github.com/Baverone/riftvault) e é empurrado de 30 em 30 minutos pela
    `riftvault-publicar`: um hash de password ali ficava publicado para
    sempre, com histórico, à disposição de quem quisesse atacá-lo com todo o
    tempo do mundo. É a diferença entre «um atacante tem de me roubar o PC» e
    «qualquer pessoa faz `git clone`».

    Por isso a `user_senha`, a `user_auth` e as `sessions` moram fora do Git, e
    a `users.auth_ref` fica VAZIA — nem um ponteiro opaco lá dentro (ver a nota
    da `utilizador.py`).

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
import contextlib
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
    """Base de tudo o que corre mal a entrar. A mensagem é para se mostrar.

    Desde 2026-10-31 é também a base dos erros do cofre de contas (ver o
    `_cofre`). O `__slots__` vazio não é enfeite: é o que deixa pô-la por baixo
    do `ErroDeConta` do cofre, que nasceu como `Exception` — o Python só aceita
    trocar a base de uma classe por outra com a mesma forma por dentro.
    """

    __slots__ = ()


class ProvedorDesconhecido(ErroDeAutenticacao):
    pass


class ProvedorPorConfigurar(ErroDeAutenticacao):
    """Falta o `client_id`/`client_secret` — e a app diz qual, não rebenta."""


class PedidoInvalido(ErroDeAutenticacao):
    """O `state` não existe, já foi usado, ou expirou."""


class DemasiadasTentativas(ErroDeAutenticacao):
    pass


class PortaFechada(ErroDeAutenticacao):
    """O `multi.aberto` está em `false`.

    Trava o OAuth e o registo. **NÃO trava a entrada por password** desde
    2026-09-30, à tarde: ele tem de poder entrar para trocar a temporária antes
    de abrir.

    A justificação original dizia «com a porta fechada a app não tem
    autenticação nenhuma — deixar entrar não dá acesso a nada que não estivesse
    dado». **Isso deixou de ser verdade a 2026-10-01**, e é bom que tenha
    deixado: de fora de casa exige-se sessão para tudo, porta fechada incluída.
    O que fica de pé é o essencial — entrar tem de funcionar sempre, senão não
    há por onde trocar a password. Ver o topo do `rotas_conta.py` e
    `docs/origem-do-pedido.md`.
    """


# --------------------------------------------------------------------------
# O ficheiro. Fora do Git, e é o `.gitignore` que o garante.
# --------------------------------------------------------------------------

ESQUEMA = """
-- A PASSWORD DE CADA UM (2026-09-30). Uma linha por utilizador com password.
--
-- A coluna `hash` é o que o `senha.cifrar` devolve — `scrypt$n$r$p$sal$hash`,
-- que NÃO SE INVERTE. Não há nem pode haver uma coluna com a password: é a
-- única parte da ordem de 30/09 que não se fez à letra, e ele concordou
-- (*"pode ficar a tua sugestao de nova password, e melhor"*).
--
-- `temporaria = 1` é a password que ELE gerou e ditou: serve para entrar uma
-- vez e o guarda não deixa fazer mais nada até ser trocada
-- (`rotas_conta._trava_temporaria`). É o que faz uma password que andou pelo
-- WhatsApp ter o tempo de vida de um WhatsApp.
--
-- **É ARQUIVO DESDE 2026-10-31.** As passwords passaram para o cofre de contas
-- (ver o bloco «AS PASSWORDS MORAM NO COFRE»); ninguém lê nem escreve aqui. A
-- tabela fica para a migração se poder conferir e repetir, e só o apagar de uma
-- conta ainda lhe toca (`esquecer_identidades`).
CREATE TABLE IF NOT EXISTS user_senha (
    user_id    INTEGER PRIMARY KEY,
    hash       TEXT    NOT NULL,
    temporaria INTEGER NOT NULL DEFAULT 0,
    criado_em  TEXT    NOT NULL,
    mudado_em  TEXT
);

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
    agente    TEXT,
    geracao   INTEGER             -- a da password no cofre (2026-10-31)
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

-- As tentativas, para o travão. Guarda-se a chave (o IP), de quem se tentou
-- entrar, e se acertou — **nunca o que se escreveu**. Uma tabela de tentativas
-- com a password tentada é uma tabela de passwords com outro nome: quem se
-- engana escreve a password de outro sítio, e ficava ali.
--
-- O `user_id` é de 2026-09-30 e é o que deixa contar POR CONTA e não só por
-- endereço: com um travão só por endereço, quem tivesse muitos endereços
-- (qualquer pessoa com dados móveis) batia à vontade na conta de um amigo.
CREATE TABLE IF NOT EXISTS auth_tentativas (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    ts       TEXT    NOT NULL,
    chave    TEXT    NOT NULL,
    provedor TEXT,
    ok       INTEGER NOT NULL,
    user_id  INTEGER
);

CREATE INDEX IF NOT EXISTS ix_tentativas_chave ON auth_tentativas(chave, ts);
-- O índice do `user_id` NÃO PODE ESTAR AQUI, e foi medido: num `auth.db` de
-- ontem a tabela existe sem a coluna, o `CREATE TABLE IF NOT EXISTS` não a
-- acrescenta, e o `CREATE INDEX` por cima de uma coluna que não existe rebenta
-- ANTES de o `_migrar` ter a chance de a criar. Vive lá, que corre depois.
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
    # O travão por CONTA (2026-09-30). Um `auth.db` de ontem tem a tabela sem
    # esta coluna, e o `CREATE TABLE IF NOT EXISTS` não a acrescenta.
    tem = {r["name"] for r in con.execute("PRAGMA table_info(auth_tentativas)")}
    if "user_id" not in tem:
        con.execute("ALTER TABLE auth_tentativas ADD COLUMN user_id INTEGER")
    # O índice fica aqui e não no ESQUEMA, para os dois casos (base nova e base
    # de ontem) passarem pelo mesmo sítio — ver o comentário no ESQUEMA.
    con.execute("CREATE INDEX IF NOT EXISTS ix_tentativas_user "
                "ON auth_tentativas(user_id, ts)")
    # A GERAÇÃO da password com que a sessão nasceu (2026-10-31), para uma
    # mudança de password no cofre — feita aqui ou no mtgvault — matar as
    # sessões abertas antes. As linhas de ontem ficam a NULL, que vale 0: é a
    # geração de uma conta migrada, por isso não caem no dia da mudança.
    tem = {r["name"] for r in con.execute("PRAGMA table_info(sessions)")}
    if "geracao" not in tem:
        con.execute("ALTER TABLE sessions ADD COLUMN geracao INTEGER")


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


#: Tentativas que ficam na tabela. O tecto conta UMA HORA — tudo o que é mais
#: velho do que isto não serve para decidir nada e é lixo a crescer. Uma
#: semana deixa rasto suficiente para ele perceber que alguém andou a tentar.
TENTATIVAS_DIAS = 7


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
                       provedor_nome: str | None, ok: bool,
                       user_id: int | None = None) -> None:
    """Fica o QUE aconteceu, nunca o que se escreveu. Ver o comentário da tabela."""
    con.execute("INSERT INTO auth_tentativas (ts, chave, provedor, ok, user_id) "
                "VALUES (?, ?, ?, ?, ?)",
                (_agora(), chave or "?", provedor_nome, 1 if ok else 0,
                 int(user_id) if user_id else None))
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
# AS PASSWORDS MORAM NO COFRE DE CONTAS (2026-10-31)
# --------------------------------------------------------------------------
#
# Até 2026-10-31 este bloco tinha a password de cada um (a `user_senha`), o
# travão das tentativas e a fila do scrypt. Mudaram-se TAL E QUAL para o cofre
# partilhado com o mtgvault (`contas/cofre.py`, ver `riftvault/cofre.py` para
# onde ele está), porque as mesmas pessoas passam a entrar nos dois sites com o
# mesmo nome e a mesma password — e duas cópias do travão eram duas políticas.
# Os comentários longos (os números da escada, as medições do scrypt) foram
# com o código: é lá que se lêem.
#
# O QUE FICA AQUI: as funções de sempre, com as assinaturas de sempre (o `con`
# do `auth.db` continua a ser aceite, para nenhum chamador mudar), que abrem o
# cofre e delegam. E as razões que são DESTE site:
#
# «TRANCA-O-AMIGO» (2026-10-01). Os nomes do riftvault estão PÚBLICOS, em
# `rift.baverone.com/api/lista.json` — é o que torna o ataque possível: quem
# soubesse o nome de um amigo falhava de propósito e trancava-o de fora. A cura
# é a do cofre: o travão do SÍTIO corre antes do scrypt (protege o CPU e só
# tranca quem o enche); o da CONTA só depois de a password sair errada — quem
# acerta entra, sempre.
#
# O TRAVÃO DA PASSWORD CONTA SÓ PASSWORDS. Até aqui a `auth_tentativas` levava
# as falhas da password e as do OAuth na mesma tabela, e o travão do sítio
# contava as duas. Agora as da password vão para o cofre e as do OAuth ficam
# no `auth.db`, com o tecto delas (`exigir_folga`, 20 por hora): o OAuth está
# parado, e um tecto de pedidos ao Google não é um travão de palpites.
#
# OS ERROS SÃO OS DO COFRE (`auth.SenhaErrada is contas.cofre.SenhaErrada`), e
# as rotas continuam a apanhá-los com `except auth.ErroDeAutenticacao`: o
# `_cofre()` regista o `ErroDeAutenticacao` como base do `ErroDeConta` do
# cofre. É herança posta à mão, e é a que mexe menos — o cofre não pode saber
# do riftvault (o mtgvault usa-o também), e o import tem de ser preguiçoso (o
# `build` importa este ficheiro e não pode precisar do cofre).

#: Os nomes que o `auth` reexporta do cofre — os erros, os números do travão e
#: a fila do scrypt. Lêem-se como sempre (`auth.ESCADA`, `auth.TemDeEsperar`);
#: o `__getattr__` do módulo vai buscá-los ao cofre à primeira leitura.
_DO_COFRE = frozenset({
    "ErroDeConta", "SemConta", "SenhaErrada", "TemDeEsperar",
    "ServidorOcupado", "FALHAS_LIVRES_CONTA", "FALHAS_LIVRES_CHAVE",
    "ESCADA", "JANELA_S", "_espera", "_em_palavras", "VAGAS_DE_SCRYPT",
    "ESPERA_POR_VAGA_S", "_VAGAS", "_uma_vaga",
})

#: O site deste repositório, no cofre.
SITE = "rift"


def _cofre():
    """O `contas.cofre`, com os erros dele ligados aos daqui.

    A ligação refaz-se se faltar, e falta depois de um `importlib.reload` deste
    módulo (os testes fazem-no): o `ErroDeAutenticacao` passa a ser outra
    classe e o cofre ainda apontava para a antiga.
    """
    from . import cofre
    m = cofre.modulo()
    if ErroDeAutenticacao not in m.ErroDeConta.__mro__:
        m.ErroDeConta.__bases__ = (ErroDeAutenticacao,)
    return m


def __getattr__(nome: str):
    if nome in _DO_COFRE:
        return getattr(_cofre(), nome)
    raise AttributeError(f"o módulo {__name__!r} não tem {nome!r}")


@contextlib.contextmanager
def _no_cofre():
    """(o `contas.cofre`, uma ligação ao cofre), fechada à saída."""
    from . import cofre
    m = _cofre()
    cc = cofre.abrir()
    try:
        yield m, cc
    finally:
        cc.close()


def _garantir(m, cc: sqlite3.Connection, user_id: int) -> None:
    """A conta do utilizador no cofre, com o MESMO número e acesso a este site.

    O nome e o slug vêm do registo (`utilizador.registo`), que é quem sabe quem
    existe aqui. Se o cofre tiver aquele número com outro slug, o
    `garantir_conta` rebenta em vez de renomear — dois sítios a discordar sobre
    quem é o utilizador N é um erro a ver.
    """
    from . import utilizador
    u = utilizador.registo(int(user_id))
    m.garantir_conta(cc, int(user_id), u["slug"], u.get("nome") or u["slug"])
    m.dar_acesso(cc, int(user_id), SITE)


def travao_do_sitio(con: sqlite3.Connection, chave: str | None) -> None:
    """O travão do endereço, ANTES do scrypt. É o do cofre (ver o bloco)."""
    with _no_cofre() as (m, cc):
        m.travao_do_sitio(cc, chave)


def travao_da_conta(con: sqlite3.Connection, user_id: int | None, *,
                    ja_registada: bool = False) -> None:
    """O travão da conta, DEPOIS de a password falhar. É o do cofre."""
    with _no_cofre() as (m, cc):
        m.travao_da_conta(cc, user_id, ja_registada=ja_registada)


def definir_senha(con: sqlite3.Connection, user_id: int, nova: str, *,
                  temporaria: bool = False, validar: bool = True,
                  slug: str = "", nome: str = "") -> None:
    """Grava a password daquele utilizador NO COFRE. Substitui a que houver.

    Primeiro garante a conta no cofre (o mesmo número do registo) e o acesso a
    este site; depois é a `definir_password` do cofre, que sobe a geração — as
    sessões abertas com a password de antes deixam de valer (ver `sessao`).

    `validar=False` é só para a TEMPORÁRIA, que o código gera e que não tem de
    passar pelas regras de quem escolhe à mão.
    """
    with _no_cofre() as (m, cc):
        _garantir(m, cc, user_id)
        m.definir_password(cc, int(user_id), nova, temporaria=temporaria,
                           validar=validar, slug=slug, nome=nome)


def nova_temporaria(con: sqlite3.Connection, user_id: int) -> str:
    """Gera uma temporária, grava-a no cofre e DEVOLVE-A EM CLARO.

    É a única função do riftvault que devolve uma password, e é o «esqueci-me»
    dele: a password existe neste valor de retorno, aparece uma vez na consola,
    e em lado nenhum mais.
    """
    with _no_cofre() as (m, cc):
        _garantir(m, cc, user_id)
        return m.nova_temporaria(cc, int(user_id))


def estado_senha(con: sqlite3.Connection, user_id: int) -> dict:
    """Tem password? É temporária? — sem devolver o hash.

    As chaves são as de sempre; a `geracao` que o cofre também devolve fica de
    fora, porque quem lê isto (a CLI, o `multi --verificar`) não precisa dela.
    """
    with _no_cofre() as (m, cc):
        e = m.estado_password(cc, int(user_id))
    return {k: e[k] for k in ("tem", "temporaria", "criado_em", "mudado_em")}


def esquecer_senha(con: sqlite3.Connection, user_id: int) -> int:
    """Apaga a password no cofre (e sobe a geração). Devolve quantas apagou."""
    with _no_cofre() as (m, cc):
        return m.esquecer_password(cc, int(user_id))


def geracao_no_cofre(user_id: int) -> int:
    """A geração da password no cofre (0 se não há conta). Ver `sessao`."""
    with _no_cofre() as (m, cc):
        return m.geracao(cc, int(user_id))


def entrar(con: sqlite3.Connection, slug: str, senha_escrita: str, *,
           chave: str | None = None) -> dict:
    """O nome e a password -> o utilizador. Decide-o o cofre, com `site="rift"`.

    Devolve o que sempre devolveu (`user_id`, `slug`, `nome`, `temporaria`) e
    mais a `geracao` — a lida JUNTO com o hash que foi verificado, que é a que a
    sessão tem de levar (ver `rotas_conta.entrar_com_senha`). Ler a geração
    outra vez depois de entrar dava a quem entrou com a password velha a
    geração de uma reposição feita a meio.

    A mesma mensagem para «não existe», «sem acesso a este site» e «errada»; o
    travão do sítio antes do scrypt e o da conta depois — ver o bloco acima e a
    `entrar` do cofre.
    """
    with _no_cofre() as (m, cc):
        quem = m.entrar(cc, slug, senha_escrita, site=SITE, chave=chave)
    return {"user_id": int(quem["conta_id"]), "slug": quem["slug"],
            "nome": quem["nome"], "temporaria": bool(quem["temporaria"]),
            "geracao": int(quem["geracao"])}


def mudar_senha(con: sqlite3.Connection, user_id: int, atual: str,
                nova: str, *, slug: str = "", nome: str = "",
                chave: str | None = None) -> None:
    """Troca a password, exigindo a que está. Levanta `SenhaErrada`/`SenhaFraca`.

    EXIGE A ACTUAL mesmo tendo sessão (um computador deixado aberto no café não
    pode dar a conta a quem passar), e o travão é o MESMO da entrada — o
    defeito de 2026-10-01 era a rota registar a falha e nunca travar. Tudo isso
    vive na `mudar_password` do cofre, que também sobe a geração: as outras
    sessões desta conta deixam de valer, aqui e no mtgvault.
    """
    with _no_cofre() as (m, cc):
        m.mudar_password(cc, int(user_id), atual, nova, slug=slug, nome=nome,
                         chave=chave)


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
    # Um fluxo abandonado deixa uma linha na `auth_pedidos` que mais ninguém
    # vai buscar; varre-se aqui, que é onde ela nasce. Ver `limpar`.
    limpar(con)
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


def pedido_liga_a(con: sqlite3.Connection, state: str) -> int | None:
    """O `liga_a` de um pedido por consumir, SEM o gastar. `None` se não existe.

    Serve a porta fechada: na volta do fornecedor o `?ligar=` já não vem no
    endereço, e o que prova que a entrada nasceu de um convite da consola é o
    pedido guardado na ida. Só leitura — quem consome (e valida prazo e
    `nonce`) continua a ser o `consumir_pedido`.
    """
    row = con.execute("SELECT liga_a FROM auth_pedidos WHERE state = ?",
                      (state or "",)).fetchone()
    return int(row["liga_a"]) if row and row["liga_a"] else None


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
                 cfg: dict | None = None,
                 geracao: int | None = None) -> dict:
    """Uma sessão nova. Devolve o `sid` EM CLARO — é a única vez que ele existe.

    `user_id` a `None` com `identidade` preenchida é a sessão pré-registo: a
    pessoa já provou quem é e ainda não tem conta.

    Uma sessão com dono leva a GERAÇÃO da password (2026-10-31, ver `sessao`).
    Quem acabou de entrar passa a `geracao` que o `entrar` devolveu — a do hash
    que foi verificado; sem ela lê-se a de agora no cofre, que é o certo para
    quem não entrou por password (o OAuth, a sessão nova depois de uma troca).
    """
    # Uma entrada é o momento em que estas tabelas crescem, e é raro: varre-se
    # aqui. Ver `limpar`.
    limpar(con)
    sid = secrets.token_urlsafe(BYTES)
    csrf = secrets.token_urlsafe(BYTES)
    agora = _agora()
    # Uma sessão PRÉ-REGISTO (sem dono) vale uma hora, não trinta dias: é só o
    # tempo de escolher um nome. Quem entrou e desistiu não fica com um cookie
    # válido um mês, e as linhas de registos que nunca aconteceram desaparecem
    # sozinhas na primeira limpeza.
    prazo = (sessao_dias(cfg) * 86400) if user_id is not None else 3600
    if user_id is not None and geracao is None:
        geracao = geracao_no_cofre(user_id)
    con.execute(
        "INSERT INTO sessions (sid_hash, user_id, provedor, sub, nome, csrf, "
        "criado_em, visto_em, expira_em, agente, geracao) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (_hash(sid), user_id,
         identidade.provedor if identidade else None,
         identidade.sub if identidade else None,
         identidade.nome if identidade else None,
         csrf, agora, agora, _mais(prazo), (agente or "")[:200],
         int(geracao) if user_id is not None else None))
    con.commit()
    return {"sid": sid, "csrf": csrf, "user_id": user_id}


def sessao(con: sqlite3.Connection, sid: str | None) -> dict | None:
    """A sessão daquele cookie, ou `None`. Uma expirada é apagada e vale `None`.

    E uma de uma password que já não é a de hoje também (2026-10-31): se a
    geração guardada na sessão não for a do cofre, a password mudou depois de
    ela nascer — trocada aqui, no mtgvault, ou reposta pelo André — e a sessão
    morre como uma expirada. É o que dá sentido a «mudei a password porque ma
    viram»: as sessões de quem a viu vão-se com ela, nos dois sites.

    A geração NULL (as sessões de antes desta mudança) vale 0, que é a de uma
    conta migrada: não caem no dia da migração, e caem na primeira mudança de
    password depois dele, como as outras. Uma sessão sem dono (pré-registo) não
    tem password e não se mede.
    """
    if not sid:
        return None
    row = con.execute("SELECT * FROM sessions WHERE sid_hash = ?",
                      (_hash(sid),)).fetchone()
    if row is None:
        return None
    if _passou(row["expira_em"]) or (
            row["user_id"] is not None
            and int(row["geracao"] or 0) != geracao_no_cofre(row["user_id"])):
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
    """As sessões que já passaram do prazo. É o `ix_sessions_expira` a servir.

    A `sessao()` apaga a linha de quem TENTA usar uma sessão expirada — mas uma
    sessão que ninguém volta a tocar ficava na tabela para sempre, e uma pessoa
    que entre do telemóvel, do portátil e do PC do trabalho deixa três linhas
    mortas por mês. Não era um buraco; era lixo a crescer, e o índice para o
    limpar já cá estava desde o primeiro dia. Ver `limpar`.
    """
    cur = con.execute("DELETE FROM sessions WHERE expira_em < ?", (_agora(),))
    con.commit()
    return cur.rowcount


def limpar_tentativas(con: sqlite3.Connection) -> int:
    """As tentativas velhas. A janela do travão é uma hora; guardam-se 7 dias.

    As do OAuth estão aqui; as da password estão no cofre desde 2026-10-31, e
    varrem-se no mesmo passo — senão a tabela do cofre era a única das que
    crescem sem ninguém a varrer (ver `limpar`). Conta as duas.
    """
    limite = _mais(-TENTATIVAS_DIAS * 86400)
    cur = con.execute("DELETE FROM auth_tentativas WHERE ts < ?", (limite,))
    con.commit()
    with _no_cofre() as (m, cc):
        do_cofre = m.limpar_tentativas(cc)
    return cur.rowcount + do_cofre


def limpar_convites(con: sqlite3.Connection) -> int:
    """Os convites de ligação gastos, e os que passaram do prazo."""
    limite = _mais(-CONVITE_MINUTOS * 60)
    cur = con.execute(
        "DELETE FROM auth_convites WHERE usado_em IS NOT NULL OR criado_em < ?",
        (limite,))
    con.commit()
    return cur.rowcount


def limpar(con: sqlite3.Connection) -> dict:
    """Varre as quatro tabelas que CRESCEM. Devolve quantas linhas saíram.

    AS QUATRO SÃO A MESMA AVARIA, por isso é uma função só: sessões expiradas,
    pedidos de entrada abandonados, convites gastos e tentativas velhas. Nenhuma
    delas era apagada em lado nenhum — o `limpar_expiradas` e o `limpar_pedidos`
    existiam desde 2026-09-29 e **nunca eram chamados**.

    ONDE CORRE, E PORQUE AQUI: no `criar_sessao` e no `comecar`, que são os dois
    sítios onde estas tabelas crescem. São eventos RAROS (uma entrada por pessoa
    por mês) e por isso o custo é nenhum; e põe um tecto que se prova — depois
    de cada entrada não sobra uma única linha morta, logo a tabela nunca guarda
    mais do que o que apodreceu desde a última entrada. Uma tarefa agendada
    fazia o mesmo trabalho com mais peças e um sítio a mais para falhar.
    """
    return {
        "sessoes": limpar_expiradas(con),
        "pedidos": limpar_pedidos(con),
        "convites": limpar_convites(con),
        "tentativas": limpar_tentativas(con),
    }


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
    """Fechada, não se entra POR UM FORNECEDOR nem se registam contas.

    É o `multi.aberto` da `1-multi-guardas`: uma leitura só, aqui, e não uma
    condição espalhada por cada rota.

    **Não é «ninguém entra»**, como esta linha dizia: a entrada por PASSWORD
    não passa por aqui desde 2026-09-30, e com a porta fechada quem já tem
    conta entra e usa a sua coleção (medido a 2026-10-01). O que a porta trava
    é o OAuth, o registo e a publicação das páginas dos outros.
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
    # E A PASSWORD (2026-09-30). O `users.user_id` é `AUTOINCREMENT`, por isso
    # um id apagado não se reutiliza e ninguém herda a password de ninguém — o
    # que fica sem isto é um HASH ÓRFÃO a envelhecer num ficheiro que não vai
    # para o Git mas está no PC dele. Apagar a conta tem de apagar tudo o que é
    # da pessoa: é isso que se responde a quem pede para ser apagado.
    n_senha = con.execute("DELETE FROM user_senha WHERE user_id = ?",
                          (user_id,)).rowcount
    con.commit()
    # Desde 2026-10-31 a password está no COFRE, e a conta de lá pode ser de
    # dois sites. Tira-se o acesso a este; a password só se apaga se a conta
    # ficar sem site nenhum — apagar a coleção do riftvault não pode trancar a
    # pessoa fora do mtgvault. A linha da `user_senha` de cima é o arquivo de
    # antes da mudança (ver o ESQUEMA), e conta na mesma: também era um hash.
    n_senha += _esquecer_no_cofre(int(user_id))
    return {"identidades": n_ident, "sessoes": n_sess, "senhas": n_senha}


def _esquecer_no_cofre(user_id: int) -> int:
    """O lado do cofre do `esquecer_identidades`. Devolve as passwords apagadas."""
    with _no_cofre() as (m, cc):
        if m.por_id(cc, user_id) is None:
            return 0
        m.tirar_acesso(cc, user_id, SITE)
        if any(m.tem_acesso(cc, user_id, s) for s in m.SITES):
            return 0
        return m.esquecer_password(cc, user_id)


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

"""As contas: entrar, registar, e o guarda que protege as 20 rotas de escrita.

Fatia `2-multi-contas` (2026-09-29), a que veste a `0-multi-utilizador-1` e a
`1-multi-guardas`. O que se fixa aqui:

  1. o fornecedor LOCAL só funciona em ENSAIO — e é o que deixa os testes e a
     prova de ponta a ponta correrem sem falar com o Google;
  2. o COOKIE da sessão tem as propriedades todas, e o CSRF é exigido em
     **todas** as rotas que escrevem — percorrem-se as vinte;
  3. com a PORTA FECHADA não há registo, não há login à vista, e o site dele é
     byte a byte o de hoje;
  4. o `app.js` não tem um POST que fuja ao `cabecalhos()` — é o que impede
     alguém de acrescentar uma rota nova sem a marca de segurança;
  5. o `riftvault multi --verificar` recusa abrir com coisas em falta.

Tudo contra pastas temporárias (`tests.fixture.Vault`) e um config temporário:
o `data/` e o `riftvault_config.json` a sério nunca são tocados.
"""

from __future__ import annotations

import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ["RIFTVAULT_CONFIG"] = str(
    Path(tempfile.gettempdir()) / "riftvault-nao-existe.json")

from tests.fixture import REPO, Vault  # noqa: E402

APP_JS = REPO / "riftvault" / "web" / "app.js"
INDEX_HTML = REPO / "riftvault" / "web" / "index.html"

#: AS VINTE ROTAS DE ESCRITA do `server.py`. A lista é o ponto desta bateria:
#: uma rota nova que alguém acrescente e não ponha aqui fica de fora, e o
#: `test_a_lista_das_rotas_esta_completa` dá vermelho por isso.
ESCRITAS = [
    "/api/adjust", "/api/undo", "/api/foil/ajustar", "/api/runas/ajustar",
    "/api/encomenda", "/api/pending/arrive", "/api/selado/ajustar",
    "/api/selado/preco", "/api/venda/linha", "/api/venda/trend",
    "/api/venda/limpar", "/api/venda/vender", "/api/proprias/ajustar",
    "/api/decks/montar", "/api/decks/principal", "/api/decks/order",
    "/api/local/mover", "/api/local/marcar", "/api/local/desfazer-deck",
    "/api/local/undo",
]


class Base(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.close)
        os.environ["RIFTVAULT_AUTH"] = str(self.v.data / "auth.db")
        self.addCleanup(lambda: os.environ.pop("RIFTVAULT_AUTH", None))
        os.environ.pop("RIFTVAULT_ENSAIO", None)
        os.environ.pop("RIFTVAULT_USER", None)

        from riftvault import (abrir, auth, config, db, metrics, multi,
                              privacidade, rotas_conta, utilizador)
        for m in (config, db, utilizador, multi, privacidade, auth,
                  rotas_conta, abrir, metrics):
            importlib.reload(m)
        self.auth, self.multi, self.abrir = auth, multi, abrir
        self.utilizador, self.config, self.db = utilizador, config, db
        self.privacidade = privacidade
        self.cfg({})

    def cfg(self, extra: dict):
        caminho = self.v.root / "config.json"
        caminho.write_text(json.dumps(extra), encoding="utf-8")
        os.environ["RIFTVAULT_CONFIG"] = str(caminho)
        importlib.reload(self.config)
        self.config.load.cache_clear()

        def repor():
            os.environ["RIFTVAULT_CONFIG"] = str(
                Path(tempfile.gettempdir()) / "riftvault-nao-existe.json")
            importlib.reload(self.config)
            self.config.load.cache_clear()

        self.addCleanup(repor)

    def catalogo(self):
        con = self.v.connect()
        self.v.add_printing(con, "tst-001-100", "TST", 1, "Defy",
                            rarity="common", size=100)
        self.v.rebuild(con)
        return con

    def cliente(self, aberto: bool = True, **extra):
        """Um servidor de teste, com a porta aberta ou fechada."""
        self.cfg({"multi": {"aberto": aberto}, **extra})
        con = self.catalogo()
        con.close()
        from riftvault import server
        importlib.reload(server)
        server.app.testing = True
        return server.app.test_client()

    def ensaio(self, ligado: bool = True):
        """Liga/desliga a base de ensaio para este teste.

        O `config.ENSAIO` é uma CONSTANTE de módulo, lida na importação — pôr a
        variável de ambiente não chega, é preciso reimportar o `config`. É a
        mesma armadilha que o `tests.fixture.Vault` já documenta para os
        caminhos.

        Reimportar o `config` aqui é seguro: o `RIFTVAULT_DATA` do `Vault`
        ganha ao `data-ensaio/` por omissão, por isso a base continua a ser a
        pasta temporária deste teste e nunca o `data/` a sério (que o próprio
        `config` recusa em ensaio, à importação).
        """
        if ligado:
            os.environ["RIFTVAULT_ENSAIO"] = "1"
        else:
            os.environ.pop("RIFTVAULT_ENSAIO", None)

        def repor():
            os.environ.pop("RIFTVAULT_ENSAIO", None)
            importlib.reload(self.config)
            self.config.load.cache_clear()

        self.addCleanup(repor)
        importlib.reload(self.config)
        self.config.load.cache_clear()
        importlib.reload(self.multi)
        importlib.reload(self.auth)


# --------------------------------------------------------------------------
# 1. O FORNECEDOR LOCAL SÓ EXISTE EM ENSAIO
# --------------------------------------------------------------------------


class TestOLocalSoEmEnsaio(Base):
    """A pergunta 3 da checklist: está impedido de funcionar fora de ensaio?"""

    def test_fora_de_ensaio_a_identidade_rebenta(self):
        self.ensaio(False)
        with self.assertRaises(self.multi.SoEmEnsaio):
            self.auth.LOCAL.identidade(code="quem-quer-que-seja")

    def test_fora_de_ensaio_nao_aparece_na_lista(self):
        self.ensaio(False)
        nomes = [p["nome"] for p in self.auth.disponiveis({})]
        self.assertNotIn("local", nomes)

    def test_fora_de_ensaio_a_rota_recusa_com_403(self):
        self.ensaio(False)
        c = self.cliente(aberto=True)
        r = c.get("/entrar/local?sub=intruso")
        self.assertEqual(r.status_code, 403)
        self.assertNotIn("Set-Cookie", r.headers,
                         "não podia ter criado sessão nenhuma")

    def test_em_ensaio_funciona(self):
        self.ensaio(True)
        i = self.auth.LOCAL.identidade(code="amigo-a")
        self.assertEqual((i.provedor, i.sub), ("local", "amigo-a"))

    def test_em_ensaio_aparece_na_lista(self):
        self.ensaio(True)
        self.assertIn("local", [p["nome"] for p in self.auth.disponiveis({})])

    def test_a_porta_aberta_nao_o_liberta_fora_de_ensaio(self):
        """São duas perguntas diferentes: um `and` esquecido não abre esta."""
        self.ensaio(False)
        self.cfg({"multi": {"aberto": True}})
        with self.assertRaises(self.multi.SoEmEnsaio):
            self.auth.LOCAL.identidade(code="x")

    def test_o_guarda_esta_em_cada_metodo_e_nao_so_num(self):
        self.ensaio(False)
        for chamar in (lambda: self.auth.LOCAL.quem("x"),
                       lambda: self.auth.LOCAL.url_de_entrada(),
                       lambda: self.auth.LOCAL.identidade(code="x")):
            with self.assertRaises(self.multi.SoEmEnsaio):
                chamar()


# --------------------------------------------------------------------------
# 2. A PORTA FECHADA
# --------------------------------------------------------------------------


class TestPortaFechada(Base):
    """O de hoje: um dono só, e nem um sinal de que as contas existem."""

    def test_o_estado_diz_fechado_e_editavel(self):
        c = self.cliente(aberto=False)
        d = c.get("/api/conta.json").get_json()
        self.assertFalse(d["aberto"])
        self.assertTrue(d["editavel"], "ele continua a poder editar")
        self.assertEqual(d["provedores"], [], "nem se dizem os fornecedores")

    def test_nao_se_pode_registar(self):
        c = self.cliente(aberto=False)
        r = c.post("/api/conta/registar", json={"slug": "miguel"})
        self.assertIn(r.status_code, (401, 403))

    def test_nao_se_pode_entrar_por_fornecedor_nenhum(self):
        c = self.cliente(aberto=False)
        for nome in ("google", "discord", "local"):
            self.assertEqual(c.get(f"/entrar/{nome}").status_code, 403,
                             f"o {nome} tinha de recusar")

    def test_as_escritas_continuam_a_funcionar_SEM_sessao(self):
        """É o ponto: com a porta fechada nada muda para ele."""
        c = self.cliente(aberto=False)
        r = c.post("/api/adjust", json={"printing_id": "tst-001-100", "delta": 1})
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True)[:300])
        self.assertEqual(r.get_json()["qty"], 1)

    def test_nao_se_exige_csrf_com_a_porta_fechada(self):
        c = self.cliente(aberto=False)
        r = c.post("/api/adjust", json={"printing_id": "tst-001-100", "delta": 1})
        self.assertEqual(r.status_code, 200)

    def test_o_html_nao_mostra_login_nenhum(self):
        """*"nada de «em breve», nada de link de login a espreitar"*."""
        import re
        html = INDEX_HTML.read_text(encoding="utf-8")
        # O elemento existe, mas nasce `hidden` e só o JS o abre.
        self.assertIn('id="conta-zona"', html)
        self.assertIn("hidden", html.split('id="conta-zona"')[1][:60])
        # Os COMENTÁRIOS não contam: o comentário que explica esta decisão
        # escreve a palavra «login», e a primeira versão deste teste apanhava-se
        # a si própria. O que se mede é o que o browser MOSTRA.
        visivel = re.sub(r"<!--.*?-->", "", html, flags=re.S)
        for palavra in ("Entrar com", "em breve", "Criar conta", "login",
                        "Iniciar sessão"):
            self.assertNotIn(palavra, visivel,
                             f"«{palavra}» não pode aparecer no HTML visível")

    def test_o_js_nao_desenha_a_zona_com_a_porta_fechada(self):
        js = APP_JS.read_text(encoding="utf-8")
        trecho = js.split("function renderConta()")[1][:400]
        self.assertIn("!c.aberto", trecho)
        self.assertIn("hidden = true", trecho)


# --------------------------------------------------------------------------
# 3. AS VINTE ROTAS DE ESCRITA
# --------------------------------------------------------------------------


class TestAsRotasDeEscrita(Base):
    """A pergunta 7 da checklist: percorreste TODAS?"""

    def test_a_lista_das_rotas_esta_completa(self):
        """Se alguém acrescentar uma rota de escrita, esta bateria tem de a ver."""
        import re
        fonte = (REPO / "riftvault" / "server.py").read_text(encoding="utf-8")
        no_codigo = set(re.findall(r'@app\.post\("([^"]+)"\)', fonte))
        self.assertEqual(
            no_codigo - set(ESCRITAS), set(),
            "há rotas de escrita no server.py que esta bateria não percorre")
        self.assertEqual(len(ESCRITAS), 20)

    def test_sem_sessao_todas_recusam_com_401(self):
        c = self.cliente(aberto=True)
        maus = []
        for rota in ESCRITAS:
            r = c.post(rota, json={})
            if r.status_code != 401:
                maus.append(f"{rota} -> {r.status_code}")
        self.assertEqual(maus, [], "estas não pediram para entrar")

    def test_com_sessao_mas_sem_csrf_todas_recusam_com_403(self):
        self.ensaio(True)
        c = self.cliente(aberto=True)
        self._entrar(c, "amigo-a", "miguel")
        maus = []
        for rota in ESCRITAS:
            r = c.post(rota, json={})
            if r.status_code != 403:
                maus.append(f"{rota} -> {r.status_code}")
        self.assertEqual(maus, [], "estas aceitaram um pedido sem CSRF")

    def test_com_csrf_errado_todas_recusam(self):
        self.ensaio(True)
        c = self.cliente(aberto=True)
        self._entrar(c, "amigo-a", "miguel")
        maus = []
        for rota in ESCRITAS:
            r = c.post(rota, json={}, headers={"X-CSRF-Token": "nao-e-o-meu"})
            if r.status_code != 403:
                maus.append(f"{rota} -> {r.status_code}")
        self.assertEqual(maus, [])

    def test_com_csrf_certo_a_escrita_passa(self):
        """A prova pela negativa: o guarda não está simplesmente a dizer não a tudo."""
        self.ensaio(True)
        c = self.cliente(aberto=True)
        csrf = self._entrar(c, "amigo-a", "miguel")
        r = c.post("/api/adjust", json={"printing_id": "tst-001-100", "delta": 2},
                   headers={"X-CSRF-Token": csrf})
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True)[:400])
        self.assertEqual(r.get_json()["qty"], 2)

    def test_as_rotas_que_escrevem_no_CONFIG_sao_so_do_dono(self):
        """O furo que a separação por ficheiro NÃO tapa.

        Cada coleção é um `vault.db` seu, por isso nenhuma rota escreve na BASE
        de outro. Mas duas rotas não escrevem numa base — escrevem no
        `riftvault_config.json`, que é UM ficheiro para todos. Um amigo a
        carregar em «Montar» escrevia o slug do deck dele na lista do André.
        """
        from riftvault import rotas_conta
        self.ensaio(True)
        c = self.cliente(aberto=True)
        csrf = self._entrar(c, "amigo-a", "miguel")  # o amigo é o utilizador 2
        for rota in rotas_conta.SO_DO_DONO:
            r = c.post(rota, json={"slug": "x", "montado": True},
                       headers={"X-CSRF-Token": csrf})
            self.assertEqual(r.status_code, 403, f"{rota} deixou o amigo escrever")
            self.assertIn("dono do site", r.get_json()["erro"])

    def test_o_config_nao_mexeu_depois_da_tentativa(self):
        """A prova: não é só o código de resposta, é o ficheiro."""
        from riftvault import rotas_conta
        self.ensaio(True)
        c = self.cliente(aberto=True)
        caminho = Path(os.environ["RIFTVAULT_CONFIG"])
        antes = caminho.read_bytes()
        csrf = self._entrar(c, "amigo-a", "miguel")
        for rota in rotas_conta.SO_DO_DONO:
            c.post(rota, json={"slug": "x", "montado": True},
                   headers={"X-CSRF-Token": csrf})
        self.assertEqual(caminho.read_bytes(), antes,
                         "o config partilhado foi escrito por um amigo")

    def test_a_lista_do_dono_cobre_tudo_o_que_escreve_no_config(self):
        """Se alguém ligar outra rota ao `escrever_valor`, isto dá vermelho."""
        import re
        from riftvault import rotas_conta
        decks_py = (REPO / "riftvault" / "decks.py").read_text(encoding="utf-8")
        # As funções do `decks.py` que escrevem no config partilhado.
        escrevem = set()
        atual = None
        for linha in decks_py.splitlines():
            m = re.match(r"def (\w+)", linha)
            if m:
                atual = m.group(1)
            if "escrever_lista" in linha or "escrever_valor" in linha:
                escrevem.add(atual)
        # `apagar_todos` é só da CLI — não tem rota. As outras têm, e as rotas
        # delas têm de estar na lista.
        self.assertEqual(escrevem - {"apagar_todos"},
                         {"alternar_montado", "escrever_principal"},
                         "há uma função nova a escrever no config partilhado; "
                         "se ela tiver rota, põe-na no SO_DO_DONO")
        self.assertEqual(len(rotas_conta.SO_DO_DONO), 2)

    def _entrar(self, c, sub: str, slug: str) -> str:
        r = c.get(f"/entrar/local?sub={sub}")
        self.assertEqual(r.status_code, 302, r.get_data(as_text=True)[:300])
        d = c.get("/api/conta.json").get_json()
        csrf = d["csrf"]
        r = c.post("/api/conta/registar", json={"slug": slug},
                   headers={"X-CSRF-Token": csrf})
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True)[:400])
        return c.get("/api/conta.json").get_json()["csrf"]


# --------------------------------------------------------------------------
# 4. O COOKIE
# --------------------------------------------------------------------------


class TestOCookie(Base):
    """A pergunta 4 da checklist: que propriedades tem?"""

    def test_httponly_samesite_e_path(self):
        self.ensaio(True)
        c = self.cliente(aberto=True)
        r = c.get("/entrar/local?sub=amigo-a")
        bruto = r.headers.get("Set-Cookie", "")
        self.assertIn("HttpOnly", bruto)
        self.assertIn("SameSite=Lax", bruto)
        self.assertIn("Path=/", bruto)

    def test_sem_https_nao_leva_secure(self):
        """No 8770 é `http://`; um `Secure` ali fazia o browser descartá-lo."""
        self.ensaio(True)
        c = self.cliente(aberto=True)
        r = c.get("/entrar/local?sub=amigo-a")
        self.assertNotIn("Secure", r.headers.get("Set-Cookie", ""))

    def test_com_https_leva_secure(self):
        self.ensaio(True)
        c = self.cliente(aberto=True)
        r = c.get("/entrar/local?sub=amigo-a",
                  headers={"X-Forwarded-Proto": "https"})
        self.assertIn("Secure", r.headers.get("Set-Cookie", ""))

    def test_o_valor_do_cookie_nao_esta_na_base(self):
        self.ensaio(True)
        c = self.cliente(aberto=True)
        r = c.get("/entrar/local?sub=amigo-a")
        valor = r.headers["Set-Cookie"].split("=", 1)[1].split(";")[0]
        bruto = Path(os.environ["RIFTVAULT_AUTH"]).read_bytes()
        self.assertNotIn(valor.encode(), bruto)

    def test_sair_apaga_o_cookie(self):
        self.ensaio(True)
        c = self.cliente(aberto=True)
        c.get("/entrar/local?sub=amigo-a")
        r = c.get("/sair")
        self.assertIn("riftvault_sessao=;", r.headers.get("Set-Cookie", "")
                      .replace('""', ""))
        self.assertFalse(c.get("/api/conta.json").get_json()["entrado"])


# --------------------------------------------------------------------------
# 5. O REGISTO
# --------------------------------------------------------------------------


class TestRegisto(Base):
    def test_entrar_sem_conta_pede_o_slug(self):
        self.ensaio(True)
        c = self.cliente(aberto=True)
        c.get("/entrar/local?sub=amigo-a")
        d = c.get("/api/conta.json").get_json()
        self.assertFalse(d["entrado"])
        self.assertTrue(d["registo_pendente"])

    def test_o_slug_reservado_recusa_com_a_razao(self):
        self.ensaio(True)
        c = self.cliente(aberto=True)
        c.get("/entrar/local?sub=amigo-a")
        csrf = c.get("/api/conta.json").get_json()["csrf"]
        r = c.post("/api/conta/registar", json={"slug": "www"},
                   headers={"X-CSRF-Token": csrf})
        self.assertEqual(r.status_code, 400)
        self.assertIn("reservado", r.get_json()["erro"])

    def test_dois_nao_podem_ter_o_mesmo_slug(self):
        self.ensaio(True)
        c = self.cliente(aberto=True)
        c.get("/entrar/local?sub=amigo-a")
        csrf = c.get("/api/conta.json").get_json()["csrf"]
        c.post("/api/conta/registar", json={"slug": "miguel"},
               headers={"X-CSRF-Token": csrf})
        c.get("/sair")
        c.get("/entrar/local?sub=amigo-b")
        csrf2 = c.get("/api/conta.json").get_json()["csrf"]
        r = c.post("/api/conta/registar", json={"slug": "miguel"},
                   headers={"X-CSRF-Token": csrf2})
        self.assertEqual(r.status_code, 400)
        self.assertIn("já está a ser usado", r.get_json()["erro"])

    def test_o_registo_roda_o_cookie(self):
        """O valor que andou pelo browser antes de haver conta não dá acesso a ela."""
        self.ensaio(True)
        c = self.cliente(aberto=True)
        r1 = c.get("/entrar/local?sub=amigo-a")
        antes = r1.headers["Set-Cookie"].split("=", 1)[1].split(";")[0]
        csrf = c.get("/api/conta.json").get_json()["csrf"]
        r2 = c.post("/api/conta/registar", json={"slug": "miguel"},
                    headers={"X-CSRF-Token": csrf})
        depois = r2.headers["Set-Cookie"].split("=", 1)[1].split(";")[0]
        self.assertNotEqual(antes, depois)

    def test_a_colecao_nasce_privada(self):
        self.ensaio(True)
        c = self.cliente(aberto=True)
        c.get("/entrar/local?sub=amigo-a")
        csrf = c.get("/api/conta.json").get_json()["csrf"]
        c.post("/api/conta/registar", json={"slug": "miguel"},
               headers={"X-CSRF-Token": csrf})
        d = c.get("/api/conta.json").get_json()
        self.assertEqual(d["utilizador"]["publico"], "nada")

    def test_o_registo_sem_ter_entrado_recusa(self):
        self.ensaio(True)
        c = self.cliente(aberto=True)
        r = c.post("/api/conta/registar", json={"slug": "miguel"})
        self.assertEqual(r.status_code, 401)


# --------------------------------------------------------------------------
# 6. O `app.js` NÃO PODE TER UM POST SEM A MARCA
# --------------------------------------------------------------------------


class TestHigieneDoCliente(Base):
    def test_todo_o_post_passa_pelo_cabecalhos(self):
        """Dezassete POST e uma função. Um esquecido é uma rota sem protecção."""
        js = APP_JS.read_text(encoding="utf-8")
        self.assertIn("function cabecalhos()", js)
        self.assertNotIn("'Content-Type': 'application/json'", js.replace(
            "const h = { 'Content-Type': 'application/json' };", ""),
            "há um POST com os cabeçalhos escritos à mão — tem de usar cabecalhos()")

    def test_o_cabecalhos_mete_o_token(self):
        js = APP_JS.read_text(encoding="utf-8")
        trecho = js.split("function cabecalhos()")[1][:300]
        self.assertIn("X-CSRF-Token", trecho)

    def test_o_token_nao_vai_num_cookie(self):
        js = APP_JS.read_text(encoding="utf-8")
        self.assertNotIn("document.cookie", js)

    def test_o_editavel_e_meu_e_nao_so_do_indice(self):
        js = APP_JS.read_text(encoding="utf-8")
        self.assertIn("state.editable = !!state.index.editable && meu", js)

    def test_o_site_publicado_nao_pede_a_conta(self):
        """Lá não há rota: sem isto, cada visita deixava um 404 na consola."""
        js = APP_JS.read_text(encoding="utf-8")
        self.assertIn("state.index.editable\n    ? await getJSON('api/conta.json')",
                      js.replace("\r\n", "\n"))


# --------------------------------------------------------------------------
# 7. O `multi --verificar`
# --------------------------------------------------------------------------


class TestVerificar(Base):
    def test_sem_fornecedor_nao_deixa_abrir(self):
        self.cfg({"multi": {"aberto": False}})
        est = self.abrir.verificar()
        self.assertFalse(est["pode_abrir"])
        nomes = [p["nome"] for p in est["faltam"]]
        self.assertIn("Entrar sem password", nomes)

    def test_o_abrir_recusa_e_diz_o_que_falta(self):
        self.cfg({"multi": {"aberto": False}})
        with self.assertRaises(self.abrir.NaoEstaPronto) as e:
            self.abrir.abrir()
        self.assertIn("Entrar sem password", str(e.exception))

    def test_o_texto_e_em_portugues_e_diz_o_estado(self):
        self.cfg({"multi": {"aberto": False}})
        t = self.abrir.texto()
        self.assertIn("A porta das contas está FECHADA", t)
        self.assertIn("abrir-a-porta.md", t)

    def test_exige_que_ELE_consiga_entrar(self):
        """Abrir com ele de fora era trancá-lo fora da própria coleção."""
        self.cfg({"multi": {"aberto": False}, "auth": {
            "base_url": "https://editar.baverone.com",
            "discord": {"client_id": "a", "client_secret": "b"}}})
        est = self.abrir.verificar()
        nomes = [p["nome"] for p in est["faltam"]]
        self.assertIn("Tu consegues entrar", nomes)

    def test_com_tudo_no_sitio_deixa_abrir(self):
        self.cfg({"multi": {"aberto": False}, "auth": {
            "base_url": "https://editar.baverone.com",
            "discord": {"client_id": "a", "client_secret": "b"}}})
        con = self.auth.abrir()
        try:
            self.auth.guardar_identidade(
                con, self.auth.Identidade("discord", "o-andre", "André"), 1)
        finally:
            con.close()
        est = self.abrir.verificar()
        self.assertTrue(est["pode_abrir"],
                        [p["nome"] for p in est["faltam"]])

    def test_o_forcar_abre_mesmo_a_faltar(self):
        self.cfg({"multi": {"aberto": False}})
        r = self.abrir.abrir(forcar=True)
        self.assertTrue(r["aberto"])

    def test_fechar_volta_atras(self):
        self.cfg({"multi": {"aberto": True}})
        r = self.abrir.fechar()
        self.assertFalse(r["aberto"])
        self.assertTrue(r["mudou"])

    def test_recusa_abrir_em_ensaio(self):
        self.ensaio(True)
        self.cfg({"multi": {"aberto": False}})
        est = self.abrir.verificar()
        nomes = [p["nome"] for p in est["faltam"]]
        self.assertIn("Não estás em ensaio", nomes)


# --------------------------------------------------------------------------
# 8. A INVARIANTE: NUNCA SE ABRE A BASE DE OUTRO
# --------------------------------------------------------------------------


class TestNuncaAbreABaseDeOutro(Base):
    """Mais forte do que «não escreve na de outro»: nunca a ABRE, nem para ler."""

    def test_o_dono_do_pedido_vem_de_UM_sitio_so(self):
        """O `g.riftvault_user` é escrito num sítio: a sessão.

        Se alguém lhe voltar a atribuir a partir do caminho ou de um cabeçalho,
        este teste dá vermelho — e era assim que a base de outra pessoa se abria
        num GET.
        """
        import re
        fonte = (REPO / "riftvault" / "rotas_conta.py").read_text(encoding="utf-8")
        atribuicoes = re.findall(r"^\s*g\.riftvault_user\s*=\s*(.+)$", fonte,
                                 re.MULTILINE)
        self.assertEqual(len(atribuicoes), 2, atribuicoes)
        self.assertEqual(atribuicoes[0].strip(), "None")
        self.assertIn("sess[", atribuicoes[1], "só a sessão manda no dono")

    def test_ler_a_pasta_de_outro_nao_serve_dados_e_explica(self):
        self.ensaio(True)
        c = self.cliente(aberto=True)
        r = c.get("/u/miguel/api/set/OGN.json")
        self.assertEqual(r.status_code, 404)
        self.assertIn("só vê a sua", r.get_json()["erro"])
        self.assertNotIn("groups", r.get_data(as_text=True))

    def test_escrever_na_pasta_de_outro_da_403_do_GUARDA(self):
        """403 e não 404: prova que o guarda recusou, não que a rota falta."""
        self.ensaio(True)
        c = self.cliente(aberto=True)
        csrf = self._entrar(c, "amigo-a", "miguel")
        c.get("/sair")
        csrf2 = self._entrar(c, "amigo-b", "joao")
        r = c.post("/u/miguel/api/adjust",
                   json={"printing_id": "tst-001-100", "delta": 1},
                   headers={"X-CSRF-Token": csrf2})
        self.assertEqual(r.status_code, 403)
        self.assertIn("não é tua", r.get_json()["erro"])

    def _entrar(self, c, sub: str, slug: str) -> str:
        c.get(f"/entrar/local?sub={sub}")
        csrf = c.get("/api/conta.json").get_json()["csrf"]
        c.post("/api/conta/registar", json={"slug": slug},
               headers={"X-CSRF-Token": csrf})
        return c.get("/api/conta.json").get_json()["csrf"]


# --------------------------------------------------------------------------
# 9. «NÃO INDEXES ISTO»
# --------------------------------------------------------------------------


class TestNoIndex(Base):
    """Uma página da coleção de um amigo indexada não se desfaz."""

    def test_a_app_de_edicao_sai_sempre_com_noindex(self):
        c = self.cliente(aberto=False)
        r = c.get("/api/conta.json")
        self.assertIn("noindex", r.headers.get("X-Robots-Tag", ""))

    def test_a_etiqueta_entra_no_head(self):
        html = "<html><head><title>x</title></head><body></body></html>"
        saida = self.abrir.marcar_html(html)
        self.assertIn('name="robots"', saida)
        self.assertIn("noindex", saida)
        self.assertLess(saida.index("robots"), saida.index("<body>"))

    def test_marcar_duas_vezes_nao_duplica(self):
        html = "<html><head></head><body></body></html>"
        uma = self.abrir.marcar_html(html)
        self.assertEqual(uma, self.abrir.marcar_html(uma))

    def test_sem_head_nao_devolve_a_pagina_sem_marca(self):
        saida = self.abrir.marcar_html("<p>nada</p>")
        self.assertIn("noindex", saida)

    def test_o_robots_txt_fecha_tudo(self):
        t = self.abrir.robots_txt()
        self.assertIn("User-agent: *", t)
        self.assertIn("Disallow: /", t)

    def test_so_a_pagina_DELE_e_indexavel(self):
        """E a dele é-o SEMPRE — está publicada e indexada desde o início.

        A primeira versão desta regra exigia também a porta aberta, e com ela
        fechada (o estado de hoje) metia `noindex` no site DELE: uma correcção
        de segurança que despublicava o site do próprio dono.
        """
        f = self.abrir.publico_indexavel
        self.assertTrue(f(dono=True))
        self.assertFalse(f(dono=False), "a de um amigo, nunca — até ele dizer")

    def test_o_build_marca_a_pagina_de_um_amigo_e_nao_a_dele(self):
        """Prova com os TRÊS valores da privacidade, no disco."""
        from riftvault import build
        con = self.catalogo()
        con.close()
        self.utilizador.criar("Miguel", "miguel")
        mig = self.utilizador.por_slug("miguel")["user_id"]

        # A DELE: sem marca nenhuma, com qualquer modo.
        dele = self.v.root / "site-dele"
        build.build(dele, log=lambda *_: None)
        html = (dele / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("noindex", html, "o site dele não se marca")
        self.assertFalse((dele / "robots.txt").exists())

        # A DE UM AMIGO: marcada nos dois sítios, nos dois modos que geram.
        for modo in ("tudo", "sem-valores"):
            self.privacidade.definir(None, mig, modo)
            fora = self.v.root / f"site-{modo}"
            build.build(fora, log=lambda *_: None, user_id=mig)
            h = (fora / "index.html").read_text(encoding="utf-8")
            self.assertIn("noindex", h, f"«{modo}» tinha de sair com noindex")
            self.assertIn("Disallow: /",
                          (fora / "robots.txt").read_text(encoding="utf-8"))

        # `nada`: não se gera página nenhuma (é a regra da 1-multi-guardas).
        self.privacidade.definir(None, mig, "nada")
        nada = self.v.root / "site-nada"
        build.build(nada, log=lambda *_: None, user_id=mig)
        self.assertFalse((nada / "index.html").exists(),
                         "com «nada» não se publica nada dele")

    def test_os_tres_valores_da_privacidade_sao_os_do_2b(self):
        """Uma verdade só: os valores vêm do módulo dela, não de uma cópia."""
        self.assertEqual(set(self.privacidade.VALORES),
                         {"nada", "sem-valores", "tudo"})
        self.assertEqual(self.privacidade.OMISSAO, "nada")


# --------------------------------------------------------------------------
# 9. O `nonce` DA ENTRADA (login CSRF)
# --------------------------------------------------------------------------


class TestNonceDaEntrada(Base):
    def test_comecar_uma_entrada_poe_o_cookie(self):
        c = self.cliente(aberto=True, auth={
            "discord": {"client_id": "a", "client_secret": "b"}})
        r = c.get("/entrar/discord")
        self.assertEqual(r.status_code, 302)
        self.assertIn(self.auth.COOKIE_NONCE, r.headers.get("Set-Cookie", ""))
        self.assertIn("HttpOnly", r.headers.get("Set-Cookie", ""))

    def test_o_nonce_nao_vai_no_endereco_do_fornecedor(self):
        c = self.cliente(aberto=True, auth={
            "discord": {"client_id": "a", "client_secret": "b"}})
        r = c.get("/entrar/discord")
        bruto = r.headers["Set-Cookie"]
        valor = bruto.split("=", 1)[1].split(";")[0]
        self.assertNotIn(valor, r.headers.get("Location", ""))

    def test_uma_volta_sem_o_cookie_recusa(self):
        """O ataque: outro começa a entrada e leva a vítima a concluí-la."""
        self.ensaio(True)
        c = self.cliente(aberto=True, auth={
            "discord": {"client_id": "a", "client_secret": "b"}})
        con = self.auth.abrir()
        try:
            r = self.auth.comecar(con, "discord",
                                  redirect_uri="http://x/entrar/discord",
                                  cfg=self.config.load())
        finally:
            con.close()
        # A vítima abre o endereço de volta sem nunca ter começado nada.
        resp = c.get(f"/entrar/discord?code=abc&state={r['state']}")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("browser", resp.get_json()["erro"])
        self.assertNotIn(self.auth.COOKIE, resp.headers.get("Set-Cookie", ""))


# --------------------------------------------------------------------------
# 10. O GUARDA DO `RIFTVAULT_USER`
# --------------------------------------------------------------------------


class TestUserFixo(Base):
    def test_com_a_porta_aberta_recusa_servir(self):
        """A variável fixa o dono para o PROCESSO: num servidor era um desastre."""
        self.cfg({"multi": {"aberto": True}})
        os.environ["RIFTVAULT_USER"] = "2"
        self.addCleanup(lambda: os.environ.pop("RIFTVAULT_USER", None))
        from riftvault import server
        importlib.reload(server)
        with self.assertRaises(SystemExit) as e:
            server._recusar_user_fixo()
        self.assertIn("RIFTVAULT_USER", str(e.exception))

    def test_com_a_porta_fechada_deixa_passar(self):
        """Fechado é um dono só: a variável continua a servir as medições."""
        self.cfg({"multi": {"aberto": False}})
        os.environ["RIFTVAULT_USER"] = "1"
        self.addCleanup(lambda: os.environ.pop("RIFTVAULT_USER", None))
        from riftvault import server
        importlib.reload(server)
        server._recusar_user_fixo()  # não rebenta


if __name__ == "__main__":
    unittest.main(verbosity=2)

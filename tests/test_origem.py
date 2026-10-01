"""DE ONDE VEM O PEDIDO decide se é preciso entrar (2026-10-01).

Esta bateria é a prova dos DOIS defeitos que duas revisões independentes
encontraram no mesmo sítio, e que tinham a mesma raiz: a app perguntava à PORTA
DAS CONTAS se era preciso autenticação, em vez de perguntar a quem estava a
bater.

  1. **«fechar» desligava a autenticação.** O `_antes` tinha
     `if not aberto and g.sessao is None: return None` — ou seja, com a porta
     fechada qualquer escrita passava SEM sessão e SEM CSRF. Com o túnel vivo
     (`editar.baverone.com`, medido a correr a 2026-10-01) isso era escrita
     anónima na coleção dele a partir da internet, e bastava um `git checkout`
     do config para a porta fechar sozinha.

  2. **um pedido sem sessão caía na base do utilizador 1.** O mesmo caminho:
     `get_con()` com `riftvault_user=None` -> `db.connect(user_id=None)` ->
     `utilizador.atual()` -> **o André**. A privacidade dele nunca era
     consultada, e por isso no dia em que a pusesse em «nada» o
     `editar.baverone.com/api/index.json` continuava a dar tudo a quem lá
     fosse.

O QUE SE EXIGE AQUI, e é a checklist dele:

  * escrita anónima recusada **com a porta fechada E com a porta aberta**;
  * leitura anónima de fora não devolve dados — varrendo as rotas TODAS, não
    uma amostra, para uma rota futura não escapar;
  * a privacidade respeitada: com `publico: nada` continua a não sair nada;
  * **e o uso dele em casa intacto** — telemóvel na LAN, porta fechada, sem
    password, a escrever como ontem. É a parte que não se pode partir.

Contra pastas temporárias e um config temporário: o `data/` e o
`riftvault_config.json` a sério nunca são tocados. O `Base` é o da
`test_senhas` — a mesma casa, para não haver duas montagens do servidor a
divergir.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from riftvault import origem  # noqa: E402
from tests.fixture import REPO  # noqa: E402
from tests.test_senhas import Base  # noqa: E402

APP_JS = REPO / "riftvault" / "web" / "app.js"
WEB_DIR = REPO / "riftvault" / "web"

SENHA_BOA = "o-meu-gato-dorme-muito"

#: UM PEDIDO QUE CHEGA PELO TÚNEL, com os cabeçalhos REAIS.
#:
#: O `cloudflared` corre NESTA máquina, por isso o par TCP é o loopback — era
#: exactamente isso que fazia parecer que não havia nada para distinguir. O que
#: o distingue são os cabeçalhos da Cloudflare e o anfitrião público.
#:
#: Estes oito cabeçalhos **foram medidos** a 2026-10-01 contra o
#: `editar.baverone.com` a sério, e o `Host` chega inteiro (a Cloudflare NÃO o
#: reescreve). São NOVE sinais ao todo, e cada um basta sozinho. Ver
#: `docs/origem-do-pedido.md`.
PELO_TUNEL = {
    "headers": {"CF-Connecting-IP": "203.0.113.9",
                "CF-Ray": "a43a120ced5e691c-LIS",
                "CF-IPCountry": "PT",
                "CF-Visitor": '{"scheme":"https"}',
                "CF-Warp-Tag-Id": "x",
                "CDN-Loop": "cloudflare; loops=1",
                "X-Forwarded-For": "203.0.113.9",
                "X-Forwarded-Proto": "https",
                "Host": "editar.baverone.com"},
    "environ_base": {"REMOTE_ADDR": "127.0.0.1"},
}

#: E um pedido directo da internet, sem intermediário nenhum (se um dia houver
#: um porto aberto no router).
DA_RUA = {"environ_base": {"REMOTE_ADDR": "203.0.113.9"}}

#: Os dois sítios de onde ele usa isto: o PC e o telemóvel na rede de casa.
DO_PC = {"environ_base": {"REMOTE_ADDR": "127.0.0.1"}}
DO_TELEMOVEL = {"environ_base": {"REMOTE_ADDR": "192.168.1.74"},
                "headers": {"Host": "192.168.1.90:8770"}}


# --------------------------------------------------------------------------
# 1. A REGRA, sem Flask
# --------------------------------------------------------------------------


class TestARegra(unittest.TestCase):
    """Pergunta 2 da checklist: em que sinal se confia, e porque não se forja."""

    def c(self, endereco, cabecalhos=None, anfitriao="", publico=""):
        return origem.classificar(endereco, cabecalhos or {}, anfitriao, publico)

    def test_o_telemovel_na_rede_de_casa_e_de_casa(self):
        """E é o sinal mais forte que há: o par TCP não se escolhe.

        O túnel não consegue produzir um `192.168.1.x` — ele fala com o
        `localhost`. Por isso este caso não precisa de cabeçalho nenhum.
        """
        self.assertTrue(self.c("192.168.1.74")["de_casa"])
        self.assertTrue(self.c("10.0.0.5")["de_casa"])
        self.assertTrue(self.c("172.16.3.9")["de_casa"])

    def test_o_browser_dele_no_proprio_PC_e_de_casa(self):
        self.assertTrue(self.c("127.0.0.1")["de_casa"])
        self.assertTrue(self.c("::1")["de_casa"])
        self.assertTrue(self.c("::ffff:127.0.0.1")["de_casa"],
                        "é o mesmo loopback escrito à maneira do IPv6")

    def test_um_endereco_da_internet_nao_e_de_casa(self):
        r = self.c("203.0.113.9")
        self.assertFalse(r["de_casa"])
        self.assertTrue(r["sinais"])

    def test_o_is_private_do_python_NAO_serve_para_isto(self):
        """A primeira versão usava-o, e a bateria apanhou-a.

        Para o Python, `203.0.113.9` É privado: ele marca assim as gamas de
        documentação e a `240.0.0.0/4`. Nenhuma é a rede de casa — e, pior, o
        que ele entende por «privado» já mudou entre versões (o CGNAT
        `100.64.0.0/10` era privado e neste Python não é). Por isso as gamas
        escrevem-se uma a uma.
        """
        import ipaddress
        for texto in ("203.0.113.9", "198.51.100.4", "192.0.2.7", "240.1.2.3"):
            with self.subTest(texto):
                self.assertTrue(ipaddress.ip_address(texto).is_private,
                                "se isto mudar no Python, o teste perdeu o ponto")
                self.assertFalse(origem.endereco_de_casa(texto),
                                 f"{texto} não é a rede de casa")
        # E o CGNAT, que depende da versão, não é de casa de qualquer maneira.
        self.assertFalse(origem.endereco_de_casa("100.64.3.9"))

    def test_sem_endereco_NAO_se_presume_casa(self):
        """Fail-closed: um WSGI sem `REMOTE_ADDR` não ganha confiança."""
        self.assertFalse(self.c(None)["de_casa"])
        self.assertFalse(self.c("")["de_casa"])
        self.assertFalse(self.c("isto-não-é-um-ip")["de_casa"])

    def test_o_LOOPBACK_SOZINHO_nao_chega_quando_ha_um_intermediario(self):
        """É o caso do túnel, e é a razão de isto existir."""
        r = self.c("127.0.0.1", {"CF-Connecting-IP": "203.0.113.9"})
        self.assertFalse(r["de_casa"])
        self.assertIn("CF-Connecting-IP", " ".join(r["sinais"]))

    def test_o_anfitriao_publico_sozinho_tambem_chega(self):
        """Se um dia o túnel não puser cabeçalho nenhum, fica esta pista."""
        r = self.c("127.0.0.1", {}, "editar.baverone.com", "editar.baverone.com")
        self.assertFalse(r["de_casa"])
        r2 = self.c("127.0.0.1", {}, "editar.baverone.com:443", "editar.baverone.com")
        self.assertFalse(r2["de_casa"], "o porto no Host não pode salvar isto")

    def test_e_um_E_e_nunca_um_OU(self):
        """Para ser de casa tem de passar os TRÊS. Um a falhar basta."""
        bom = dict(endereco="127.0.0.1", cabecalhos={}, anfitriao="localhost:8770",
                   publico="editar.baverone.com")
        self.assertTrue(origem.classificar(**bom)["de_casa"])
        for mudanca in ({"endereco": "8.8.8.8"},
                        {"cabecalhos": {"X-Forwarded-For": "1.2.3.4"}},
                        {"anfitriao": "editar.baverone.com"}):
            with self.subTest(**mudanca):
                self.assertFalse(origem.classificar(**{**bom, **mudanca})["de_casa"])

    def test_forjar_um_cabecalho_so_pode_TIRAR_confianca(self):
        """A direcção do erro é a que interessa.

        Quem estiver na rede de casa e mandar um `CF-Connecting-IP` inventado
        consegue uma coisa só: passar a precisar de password. Não há cabeçalho
        nenhum que GANHE confiança — a confiança vem da ausência deles.
        """
        for nome in origem.CABECALHOS_DE_INTERMEDIARIO:
            with self.subTest(nome):
                r = self.c("192.168.1.74", {nome: "inventado"})
                self.assertFalse(r["de_casa"])

    def test_os_NOVE_sinais_medidos_bastam_cada_um_SOZINHO(self):
        """Isto ata a regra à medição de 2026-10-01 contra o túnel a sério.

        Oito cabeçalhos + o anfitrião. Se amanhã a Cloudflare deixar de pôr
        sete deles, o oitavo chega; se deixar de pôr os oito, chega o nome. Era
        esta redundância que faltava para a regra não depender de uma coisa só.
        """
        medidos = ("CF-Connecting-IP", "CF-Ray", "CF-IPCountry", "CF-Visitor",
                   "CF-Warp-Tag-Id", "CDN-Loop", "X-Forwarded-For",
                   "X-Forwarded-Proto")
        for nome in medidos:
            with self.subTest(nome):
                self.assertIn(nome, origem.CABECALHOS_DE_INTERMEDIARIO)
                r = self.c("127.0.0.1", {nome: "x"}, "localhost:8770",
                           "editar.baverone.com")
                self.assertFalse(r["de_casa"], f"{nome} sozinho tem de bastar")
        # O nono: o anfitrião público, sem um cabeçalho que seja.
        self.assertFalse(self.c("127.0.0.1", {}, "editar.baverone.com",
                                "editar.baverone.com")["de_casa"])

    def test_a_lista_de_cabecalhos_nao_e_so_da_cloudflare(self):
        """O dia em que ele trocar de túnel não pode ser o dia em que isto
        deixa de funcionar em silêncio."""
        nomes = {n.lower() for n in origem.CABECALHOS_DE_INTERMEDIARIO}
        for esperado in ("cf-connecting-ip", "x-forwarded-for",
                         "x-forwarded-proto", "forwarded", "x-real-ip",
                         "true-client-ip", "via", "cdn-loop"):
            self.assertIn(esperado, nomes)

    def test_sem_base_url_escrito_a_pista_do_anfitriao_nao_existe(self):
        """E não rebenta: ficam as outras duas."""
        self.assertEqual(origem.anfitriao_publico({}), "")
        self.assertEqual(origem.anfitriao_publico(None), "")
        self.assertEqual(
            origem.anfitriao_publico({"auth": {"base_url": "https://X.com/"}}),
            "x.com")
        self.assertTrue(self.c("127.0.0.1", {}, "editar.baverone.com", "")["de_casa"])

    def test_os_sinais_nunca_levam_o_VALOR_de_um_cabecalho(self):
        """Eles vão para o `api/conta.json`, que se serve sem sessão."""
        r = self.c("127.0.0.1", {"CF-Connecting-IP": "203.0.113.77",
                                 "X-Forwarded-For": "segredo"})
        texto = origem.porque(r["sinais"])
        self.assertIn("CF-Connecting-IP", texto)
        self.assertNotIn("203.0.113.77", texto)
        self.assertNotIn("segredo", texto)


# --------------------------------------------------------------------------
# 2. ESCRITA ANÓNIMA — o primeiro defeito
# --------------------------------------------------------------------------


class TestEscritaAnonima(Base):
    """Pergunta 3: que código devolve, com a porta aberta e fechada."""

    ESCRITAS = (
        ("/api/adjust", {"printing_id": "tst-001-100", "delta": 1}),
        ("/api/foil/ajustar", {"printing_id": "tst-001-100", "delta": 1}),
        ("/api/encomenda", {"printing_id": "tst-001-100", "delta": 1}),
        ("/api/undo", {}),
        ("/api/decks/montar", {"slug": "x", "montado": True}),
        ("/api/decks/principal", {"slug": "x"}),
        ("/api/venda/linha", {"printing_id": "tst-001-100", "delta": 1}),
        ("/api/local/marcar", {"linhas": []}),
        ("/api/conta/privacidade", {"publico": "tudo"}),
        ("/api/conta/apagar", {"confirmar": "baverone"}),
    )

    def _recusa(self, aberto: bool, de_onde: dict):
        c = self.cliente(aberto=aberto)
        for caminho, corpo in self.ESCRITAS:
            with self.subTest(porta="aberta" if aberto else "fechada",
                              rota=caminho):
                r = c.post(caminho, json=corpo, **de_onde)
                self.assertEqual(
                    r.status_code, 401,
                    f"{caminho} devia recusar: {r.get_data(as_text=True)[:200]}")

    def test_pelo_tunel_com_a_porta_FECHADA(self):
        """O defeito 1, à letra: era isto que passava."""
        self._recusa(False, PELO_TUNEL)

    def test_pelo_tunel_com_a_porta_ABERTA(self):
        self._recusa(True, PELO_TUNEL)

    def test_da_rua_com_a_porta_FECHADA(self):
        self._recusa(False, DA_RUA)

    def test_da_rua_com_a_porta_ABERTA(self):
        self._recusa(True, DA_RUA)

    def test_de_casa_com_a_porta_ABERTA_tambem_recusa(self):
        """Isto já era assim, e não se afrouxou: a porta aberta exige sessão
        em casa também, ele incluído."""
        c = self.cliente(aberto=True)
        r = c.post("/api/adjust", json={"printing_id": "tst-001-100", "delta": 1},
                   **DO_PC)
        self.assertEqual(r.status_code, 401)

    def test_a_escrita_anonima_de_fora_NAO_MEXEU_NA_COLECAO(self):
        """O código de estado não chega: o que interessa é que não escreveu."""
        c = self.cliente(aberto=False)
        con = self.v.connect()
        antes = con.execute("SELECT COALESCE(SUM(qty), 0) FROM copies").fetchone()[0]
        n_ops = con.execute("SELECT COUNT(*) FROM ops").fetchone()[0]
        con.close()

        for _ in range(5):
            c.post("/api/adjust", json={"printing_id": "tst-001-100", "delta": 1},
                   **PELO_TUNEL)

        con = self.v.connect()
        try:
            self.assertEqual(
                con.execute("SELECT COALESCE(SUM(qty), 0) FROM copies").fetchone()[0],
                antes)
            self.assertEqual(
                con.execute("SELECT COUNT(*) FROM ops").fetchone()[0], n_ops)
        finally:
            con.close()


# --------------------------------------------------------------------------
# 3. LEITURA ANÓNIMA — o segundo defeito
# --------------------------------------------------------------------------


class TestLeituraAnonima(Base):
    """Pergunta 4: o que devolve agora, e a privacidade é respeitada."""

    def _rotas_de_leitura(self, c) -> list[str]:
        """As rotas GET do `/api/` que não têm parâmetros, do próprio url_map.

        Varre-se o mapa e não uma lista escrita à mão: uma rota de leitura
        acrescentada amanhã entra neste teste sozinha.
        """
        from riftvault import server
        fora = set(self.rotas_conta.DE_FORA_SEM_SESSAO)
        return sorted(
            str(r.rule) for r in server.app.url_map.iter_rules()
            if "GET" in (r.methods or ()) and str(r.rule).startswith("/api/")
            and "<" not in str(r.rule) and str(r.rule) not in fora)

    def test_nenhuma_rota_de_leitura_responde_de_fora_sem_sessao(self):
        c = self.cliente(aberto=False)
        rotas = self._rotas_de_leitura(c)
        self.assertGreater(len(rotas), 8, "o varrimento não encontrou rotas")
        for rota in rotas:
            with self.subTest(rota=rota):
                r = c.get(rota, **PELO_TUNEL)
                self.assertEqual(r.status_code, 401,
                                 f"{rota} serviu dados a quem não entrou")

    def test_nem_com_a_porta_aberta(self):
        c = self.cliente(aberto=True)
        for rota in self._rotas_de_leitura(c):
            with self.subTest(rota=rota):
                self.assertEqual(c.get(rota, **PELO_TUNEL).status_code, 401)

    def test_as_imagens_tambem_nao(self):
        """Passam pelo `get_con()`, e por isso nunca podiam servir-se sem dono."""
        c = self.cliente(aberto=False)
        self.assertEqual(c.get("/img/tst-001-100.webp", **PELO_TUNEL).status_code,
                         401)

    def test_a_coleccao_de_outro_nao_se_ve_aqui_de_fora(self):
        c = self.cliente(aberto=True)
        self.utilizador.criar("Miguel", "miguel")
        self.assertEqual(c.get("/u/miguel/", **PELO_TUNEL).status_code, 401)

    def test_a_PRIVACIDADE_dele_fica_respeitada_por_construcao(self):
        """O defeito 2 em uma frase: o `publico` dele nunca era consultado.

        Com a correcção não há nada para filtrar — não se serve nada. É a mesma
        decisão do `_u_explica`: filtrar dezassete rotas de leitura era deixar
        uma esquecida a vazar.
        """
        from riftvault import privacidade
        c = self.cliente(aberto=True)
        for valor in ("nada", "sem-valores", "tudo"):
            privacidade.definir(None, 1, valor)
            with self.subTest(publico=valor):
                r = c.get("/api/index.json", **PELO_TUNEL)
                self.assertEqual(r.status_code, 401)
                corpo = r.get_data(as_text=True)
                self.assertNotIn("totals", corpo)
                self.assertNotIn("generated_at", corpo)

    def test_o_get_con_rebenta_em_vez_de_abrir_a_base_do_utilizador_1(self):
        """A rede por baixo do guarda: a camada onde o defeito 2 vivia.

        Prova pela NEGATIVA — se o `g.de_casa` disser casa, o `connect` volta a
        dar a base dele. É isso que mostra que é o sinal da origem que decide, e
        não um acaso.
        """
        from flask import g

        from riftvault import server
        self.cliente(aberto=True)
        with server.app.test_request_context("/api/index.json"):
            g.riftvault_user = None
            g.de_casa = False
            with self.assertRaises(self.rotas_conta.SemSessao):
                server.get_con()
        with server.app.test_request_context("/api/index.json"):
            g.riftvault_user = None
            g.de_casa = True
            con = server.get_con()
            self.assertEqual(con.riftvault_user, 1)
            con.close()


# --------------------------------------------------------------------------
# 4. A PORTA DE ENTRADA continua aberta a quem vem de fora
# --------------------------------------------------------------------------


class TestAPortaDeEntrada(Base):
    """Barrar tudo sem deixar por onde entrar era o beco de 30/09 outra vez."""

    def test_a_casca_e_a_entrada_passam(self):
        c = self.cliente(aberto=False)
        for caminho in ("/", "/app.js", "/style.css", "/api/conta.json"):
            with self.subTest(caminho=caminho):
                self.assertEqual(c.get(caminho, **PELO_TUNEL).status_code, 200)

    def test_entrar_por_HTTP_de_fora_com_a_porta_fechada(self):
        """De ponta a ponta: entra, e a partir daí lê e escreve."""
        c = self.cliente(aberto=False)
        self.com_senha("baverone2", SENHA_BOA)
        r = c.post("/api/conta/entrar", json={"nome": "baverone2",
                                              "senha": SENHA_BOA}, **PELO_TUNEL)
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True)[:300])
        csrf = r.get_json()["csrf"]

        self.assertEqual(c.get("/api/index.json", **PELO_TUNEL).status_code, 200)
        w = c.post("/api/adjust",
                   json={"printing_id": "tst-001-100", "delta": 1, "csrf": csrf},
                   **PELO_TUNEL)
        self.assertEqual(w.status_code, 200, w.get_data(as_text=True)[:300])

    def test_entrado_de_fora_ainda_exige_CSRF(self):
        c = self.cliente(aberto=False)
        self.com_senha("baverone2", SENHA_BOA)
        c.post("/api/conta/entrar", json={"nome": "baverone2",
                                          "senha": SENHA_BOA}, **PELO_TUNEL)
        r = c.post("/api/adjust", json={"printing_id": "tst-001-100", "delta": 1},
                   **PELO_TUNEL)
        self.assertEqual(r.status_code, 403)

    def test_sair_funciona_de_fora(self):
        c = self.cliente(aberto=False)
        self.assertIn(c.get("/sair", **PELO_TUNEL).status_code, (302, 200))

    def test_com_a_porta_FECHADA_quem_ja_tem_conta_entra_e_usa(self):
        """As mensagens do `--fechar` dizem isto, por isso tem de estar fixado.

        A primeira escrita desta correcção dizia o contrário («os teus amigos
        deixam de entrar») e foi medida a dar 200. A entrada por password não
        passa pela porta desde 30/09, e cada um escreve na coleção DELE.
        """
        c = self.cliente(aberto=False)
        self.com_senha("amiga", SENHA_BOA)
        csrf = self.entrar(c, "amiga", SENHA_BOA)
        d = c.get("/api/conta.json").get_json()
        self.assertTrue(d["entrado"])
        self.assertEqual(d["utilizador"]["slug"], "amiga")
        r = c.post("/api/adjust",
                   json={"printing_id": "tst-001-100", "delta": 1, "csrf": csrf})
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True)[:300])

    def test_a_lista_cobre_os_ficheiros_TODOS_do_web(self):
        """Um ficheiro novo no `web/` não pode passar a público em silêncio."""
        na_lista = set(self.rotas_conta.DE_FORA_SEM_SESSAO)
        for f in sorted(WEB_DIR.iterdir()):
            if f.is_file():
                self.assertIn(
                    "/" + f.name, na_lista,
                    f"o {f.name} está no web/ mas não na DE_FORA_SEM_SESSAO: "
                    f"decide se é público e põe-no lá, ou tira-o da pasta")

    def test_a_lista_nao_tem_rotas_de_dados(self):
        """A rede do outro lado: ninguém põe lá um payload por distração."""
        for caminho in self.rotas_conta.DE_FORA_SEM_SESSAO:
            if caminho.startswith("/api/"):
                self.assertTrue(
                    caminho.startswith("/api/conta"),
                    f"{caminho} não é da conta — não pode servir-se sem sessão")


# --------------------------------------------------------------------------
# 5. O USO DELE EM CASA — a parte que não se pode partir
# --------------------------------------------------------------------------


class TestOUsoEmCasa(Base):
    """Pergunta 5: em casa continua a funcionar sem password?"""

    def _escreve_sem_password(self, de_onde: dict):
        c = self.cliente(aberto=False)
        r = c.post("/api/adjust", json={"printing_id": "tst-001-100", "delta": 1},
                   **de_onde)
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True)[:300])
        return r.get_json()

    def test_do_PC_escreve_sem_password_com_a_porta_fechada(self):
        self.assertEqual(self._escreve_sem_password(DO_PC)["qty"], 1)

    def test_do_TELEMOVEL_na_rede_de_casa_escreve_sem_password(self):
        """É o que ele usa todos os dias, e era o risco desta correcção."""
        self.assertEqual(self._escreve_sem_password(DO_TELEMOVEL)["qty"], 1)

    def test_em_casa_LE_sem_password(self):
        c = self.cliente(aberto=False)
        for de_onde in (DO_PC, DO_TELEMOVEL):
            with self.subTest(de=de_onde["environ_base"]["REMOTE_ADDR"]):
                r = c.get("/api/index.json", **de_onde)
                self.assertEqual(r.status_code, 200)
                self.assertTrue(r.get_json().get("editable"))

    def test_em_casa_o_conta_json_diz_que_e_de_casa(self):
        c = self.cliente(aberto=False)
        d = c.get("/api/conta.json", **DO_TELEMOVEL).get_json()
        self.assertEqual(d["origem"], "casa")
        self.assertEqual(d["sinais"], [])
        self.assertFalse(d["exige_entrar"])
        self.assertTrue(d["editavel"], "em casa ele edita sem entrar")

    def test_de_fora_o_conta_json_diz_porque(self):
        c = self.cliente(aberto=False)
        d = c.get("/api/conta.json", **PELO_TUNEL).get_json()
        self.assertEqual(d["origem"], "fora")
        self.assertTrue(d["exige_entrar"])
        self.assertFalse(d["editavel"], "de fora não há nada editável sem entrar")
        self.assertTrue(d["sinais"], "tem de dizer o que decidiu")
        self.assertNotIn("203.0.113.9", " ".join(d["sinais"]),
                         "os sinais não levam valores de cabeçalhos")

    def test_o_vigia_do_8770_continua_a_passar(self):
        """O `riftvault-serve` faz `GET /` de minuto a minuto, do loopback."""
        c = self.cliente(aberto=False)
        self.assertEqual(c.get("/", **DO_PC).status_code, 200)


# --------------------------------------------------------------------------
# 6. AS MENSAGENS DIZEM A VERDADE
# --------------------------------------------------------------------------


class TestAsMensagens(Base):
    """Pergunta 6. Uma frase que descreve a porta como inofensiva, num sítio
    que punha a autenticação abaixo, é parte do defeito."""

    def test_a_docstring_do_fechar_ja_nao_diz_que_so_deixa_de_se_entrar(self):
        """A frase antiga pode estar lá CITADA, a dizer que era falsa — o que
        não pode é ser a promessa da função. Olha-se para a primeira linha, que
        é o que alguém lê ao passar o rato por cima."""
        from riftvault import abrir
        doc = abrir.fechar.__doc__ or ""
        primeira = doc.splitlines()[0]
        self.assertNotIn("Ninguém perde nada", primeira)
        self.assertNotIn("só deixa de se entrar", primeira)
        self.assertIn("ERA FALSO", doc, "tem de dizer que a antiga era falsa")
        self.assertIn("ORIGEM", doc)
        self.assertIn("aberta ou fechada", doc)

    def test_o_fechar_diz_que_de_fora_continua_a_pedir(self):
        """O que conta é o que ele VÊ, não o comentário que explica o defeito —
        a lição do `test_conta_fechada`: tiram-se os comentários primeiro."""
        import re
        fonte = (REPO / "riftvault" / "cli.py").read_text(encoding="utf-8")
        trecho = fonte.split("if args.fechar:")[1][:1600]
        self.assertIn("de FORA de casa entrar continua a ser obrigatório",
                      trecho)
        codigo = "\n".join(l.split("#")[0] for l in trecho.splitlines())
        self.assertNotIn("só deixa de se entrar", codigo)
        self.assertNotIn("Ninguém perde nada", codigo)

    def test_nenhuma_mensagem_diz_que_fechar_impede_de_entrar(self):
        """A asneira ao contrário, que esta ordem quase cometeu.

        Fechar não impede quem já tem conta de entrar — está medido e há teste
        de comportamento acima. As frases não podem prometer o que não fazem,
        nem a mais nem a menos.
        """
        import re
        for ficheiro in ("cli.py", "auth.py", "abrir.py"):
            fonte = (REPO / "riftvault" / ficheiro).read_text(encoding="utf-8")
            # Tiram-se comentários e docstrings: eles explicam o erro antigo.
            codigo = re.sub(r'"""[\s\S]*?"""', "", fonte)
            codigo = "\n".join(l.split("#")[0] for l in codigo.splitlines())
            for frase in ("deixam de entrar", "ninguém entra",
                          "ainda não consegue"):
                with self.subTest(ficheiro=ficheiro, frase=frase):
                    self.assertNotIn(frase, codigo)

    def test_o_abrir_avisa_que_a_escrita_passa_a_pedir_sessao(self):
        fonte = (REPO / "riftvault" / "cli.py").read_text(encoding="utf-8")
        trecho = fonte.split("if args.abrir:")[1][:700]
        self.assertIn("pedir que entres", trecho)

    def test_o_verificar_diz_a_regra_da_origem(self):
        from riftvault import abrir
        texto = abrir.texto(cfg={"multi": {"aberto": False}})
        self.assertIn("fora de casa", texto.lower())

    def test_o_ecra_barrado_diz_onde_esta_o_formulario_TAMBEM_no_telemovel(self):
        """Da fotografia a 375 px, não do código.

        Ali a barra do lado está atrás do ☰ Menu — o formulário ESTÁ lá (o
        `mostrarSeTrancado` esconde só o `#sidenav`, não a `<aside>` inteira),
        mas a frase «o formulário está na barra do lado» mandava-o procurar uma
        coisa que não se vê. Vinha assim desde 30/09, no ecrã da temporária.
        """
        js = APP_JS.read_text(encoding="utf-8")
        self.assertIn("ONDE_ESTA_O_FORMULARIO", js)
        self.assertIn("☰ Menu", js, "tem de dizer o sítio do telemóvel")
        fn = js.split("async function mostrarSeTrancado()")[1][:2600]
        self.assertIn("ONDE_ESTA_O_FORMULARIO", fn,
                      "os dois ecrãs dizem a mesma frase, de um sítio só")

    def test_o_app_js_desenha_a_entrada_quando_e_barrado_de_fora(self):
        js = APP_JS.read_text(encoding="utf-8")
        fn = js.split("async function mostrarSeTrancado()")[1][:2400]
        self.assertIn("exige_entrar", fn,
                      "sem isto, de fora lia-se «Falhou a carregar: HTTP 401»")
        self.assertIn("renderConta()", fn)


# --------------------------------------------------------------------------
# 7. A FRONTEIRA
# --------------------------------------------------------------------------


class TestAFronteira(Base):
    """Uma pergunta, um sítio."""

    def test_so_o_rotas_conta_decide_a_origem(self):
        """Senão havia duas leituras a divergir, como no `_porta_aberta`."""
        for nome in ("server", "build", "metrics", "collection", "db",
                     "privacidade", "utilizador", "auth", "abrir"):
            fonte = (REPO / "riftvault" / f"{nome}.py").read_text(encoding="utf-8")
            with self.subTest(modulo=nome):
                self.assertNotIn("import origem", fonte)
                self.assertNotIn("origem.classificar", fonte)

    def test_a_porta_ja_nao_decide_sozinha_a_escrita(self):
        """O defeito 1, lido no ficheiro: a linha tinha de ganhar o `de_casa`."""
        fonte = (REPO / "riftvault" / "rotas_conta.py").read_text(encoding="utf-8")
        self.assertNotIn("if not aberto and g.sessao is None:\n            return None",
                         fonte)
        self.assertIn("if not aberto and g.sessao is None and g.de_casa:", fonte)

    def test_o_de_casa_e_posto_antes_de_tudo(self):
        """O `get_con()` lê-o; se fosse posto depois, lia o valor por omissão."""
        fonte = (REPO / "riftvault" / "rotas_conta.py").read_text(encoding="utf-8")
        corpo = fonte.split("def _antes():")[1].split("\ndef ")[0]
        self.assertLess(corpo.index("g.de_casa ="), corpo.index("request.cookies"))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

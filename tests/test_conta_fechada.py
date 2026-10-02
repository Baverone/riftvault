"""O BECO DA PORTA FECHADA, fechado (2026-09-30, à tarde).

Ordem dele: a caixa de «Entrar» estava escondida enquanto `multi.aberto` fosse
`false` — e o `multi --verificar` exige que ele TROQUE a password temporária
ANTES de abrir, sendo que a troca só se faz entrando no site. Não abria sem
trocar e não trocava sem abrir.

A CAUSA foi ler mal a frase dele. Ele disse *"Quero apenas apresentar quando
tiver tudo"* e o que isso quer dizer é **um link de login no SITE PUBLICADO**;
no 8770, que é a casa dele, esconder a entrada não serve ninguém.

O QUE ESTA BATERIA FIXA

  1. **o critério novo** — esconde-se no ESTÁTICO, não com a porta fechada — e
     que ele não é uma bandeira nova: é o `index.editable`, que o servidor põe
     a `true` e o `build` a `false`, e que já decidia se se pergunta pelo
     `api/conta.json`;
  2. **no servidor, com a porta FECHADA, a entrada funciona** — provado por
     HTTP, do `api/conta.json` até ao cookie;
  3. **no estático não aparece nada** — o site gerado não tem `api/conta.json`,
     diz `editable: false`, e o HTML visível não fala de contas;
  4. **a troca da temporária com a porta fechada**, de ponta a ponta;
  5. **o SEGUNDO beco**, que a ordem não nomeou e que existia com a porta
     ABERTA também: o `_trava_temporaria` responde 403 a tudo o que é `/api/`,
     o `api/index.json` é a primeira coisa que o `boot()` pede, e o ecrã da
     troca nunca chegava a ser desenhado;
  6. **o `--definir-password`** — a rede de segurança pela consola: aceita,
     recusa as fracas, não mostra o que se escreve, e a temporária deixa de
     servir;
  7. **e o que NÃO mudou**: com a porta fechada e sem sessão, escrever não pede
     nada. É a promessa de «tudo exactamente como ontem».

Contra pastas temporárias e um config temporário: o `data/` e o
`riftvault_config.json` a sério nunca são tocados. O `Base` é o da
`test_senhas` — a mesma casa, para não haver duas montagens do servidor a
divergir.
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.fixture import REPO  # noqa: E402
from tests.test_senhas import Base  # noqa: E402

APP_JS = REPO / "riftvault" / "web" / "app.js"
INDEX_HTML = REPO / "riftvault" / "web" / "index.html"
CSS = REPO / "riftvault" / "web" / "style.css"

SENHA_BOA = "o-meu-gato-dorme-muito"


# --------------------------------------------------------------------------
# 1. O CRITÉRIO NOVO
# --------------------------------------------------------------------------


class TestOCriterio(Base):
    """Onde vive, e que não é uma bandeira nova."""

    def test_o_render_esconde_por_FALTA_DE_RESPOSTA_e_nao_pela_porta(self):
        js = APP_JS.read_text(encoding="utf-8")
        trecho = js.split("function renderConta()")[1][:400]
        self.assertIn("if (!c) {", trecho)
        self.assertIn("hidden = true", trecho)
        self.assertNotIn(
            "!c.aberto", trecho,
            "a porta não pode voltar a decidir isto — era exactamente o beco")

    def test_a_bandeira_diz_se_isto_e_o_SERVIDOR(self):
        """ERA O `index.editable` ATÉ 2026-10-02, e este teste dizia-o.

        Não se inventou uma bandeira em 30/09: usou-se a que já existia para
        não pedir o `api/conta.json` no estático (e não deixar um 404 na
        consola). Só que essa respondia a DUAS perguntas de uma vez — «posso
        escrever?» e «isto é o servidor?» —, e por isso o `editable` não podia
        dizer a verdade: com a porta aberta um leitor anónimo não pode
        escrever, e se o campo dissesse `false` esta caixa desaparecia. Era o
        beco de hoje por outro caminho. Ver `tests/test_achados_346.py` (§4).
        """
        js = APP_JS.read_text(encoding="utf-8")
        self.assertIn("state.conta = state.index.servidor", js)
        self.assertIn("api/conta.json", js)

    def test_o_servidor_diz_editable_true_e_o_build_false(self):
        """As duas pontas da bandeira, medidas — uma por HTTP, outra no disco."""
        from riftvault import build
        c = self.cliente(aberto=False)
        self.assertTrue(c.get("/api/index.json").get_json()["editable"])

        fora = self.v.root / "site-bandeira"
        build.build(fora, log=lambda *_: None)
        import json
        d = json.loads((fora / "api" / "index.json").read_text(encoding="utf-8"))
        self.assertFalse(d["editable"])

    def test_os_comentarios_do_html_e_do_css_dizem_o_criterio_de_hoje(self):
        """Estes dois explicavam a regra antiga, e era ela que enganava."""
        for caminho in (INDEX_HTML, CSS):
            texto = caminho.read_text(encoding="utf-8")
            bloco = texto[max(0, texto.find("conta-zona") - 700):
                          texto.find("conta-zona") + 300]
            self.assertIn("PUBLICADO", bloco.upper(),
                          f"{caminho.name} tem de dizer que é do estático")


# --------------------------------------------------------------------------
# 2. NO SERVIDOR, COM A PORTA FECHADA, A ENTRADA APARECE E FUNCIONA
# --------------------------------------------------------------------------


class TestNoServidorAEntradaAparece(Base):

    def test_o_api_conta_responde_com_a_porta_fechada(self):
        """É o que faz `state.conta` deixar de ser `null` — e a caixa aparecer."""
        c = self.cliente(aberto=False)
        r = c.get("/api/conta.json")
        self.assertEqual(r.status_code, 200)
        d = r.get_json()
        self.assertFalse(d["aberto"], "a porta continua fechada")
        self.assertFalse(d["entrado"])
        self.assertTrue(d["senha"], "há por onde entrar")
        self.assertTrue(d["editavel"], "e ele continua a poder editar sem entrar")

    def test_a_caixa_de_entrada_e_a_que_se_desenha(self):
        """A condição do ecrã 4, lida no ficheiro, com o estado real do servidor.

        Não há browser aqui, por isso prova-se a corrente: o servidor responde
        (teste acima), `state.conta` fica com esse objecto, o `renderConta` só
        se cala com `!c`, e com `!c.entrado` desenha o formulário com os dois
        campos e o botão.
        """
        c = self.cliente(aberto=False)
        d = c.get("/api/conta.json").get_json()
        self.assertTrue(bool(d), "o payload tem de ser truthy (é o `!c`)")
        self.assertFalse(d["entrado"], "o ecrã 4 é o do `!c.entrado`")

        js = APP_JS.read_text(encoding="utf-8")
        ecra = js.split("if (!c.entrado) {")[1][:2400]
        for peca in ('id="en-nome"', 'id="en-senha"', 'id="en-ok"'):
            self.assertIn(peca, ecra, f"falta o {peca} na caixa de entrada")

    def test_com_a_porta_fechada_a_caixa_diz_que_as_contas_nao_estao_abertas(self):
        """Aparece, mas não mente: os amigos ainda não entram.

        A 2026-10-01 passaram a ser TRÊS casos e não dois: de fora de casa é
        preciso entrar, com a porta aberta ou fechada, e a frase antiga («não
        precisas de entrar para usar o site») era mentira nesse caso. O que o
        teste exige continua a ser o mesmo — que o texto distinga os estados em
        vez de dizer um deles sempre.
        """
        js = APP_JS.read_text(encoding="utf-8")
        ecra = js.split("if (!c.entrado) {")[1][:2400]
        self.assertIn("c.exige_entrar", ecra,
                      "de fora de casa a nota tem de dizer que é preciso entrar")
        self.assertIn("!c.aberto", ecra,
                      "o ecrã 4 tem de distinguir as duas portas no TEXTO")
        self.assertIn("ainda não estão abertas", ecra)
        self.assertIn("Em casa não precisas de entrar", ecra)

    def test_entrar_por_HTTP_com_a_porta_fechada(self):
        """A prova que interessa: a mesma chamada que o botão faz."""
        c = self.cliente(aberto=False)
        self.com_senha("baverone2", SENHA_BOA)
        r = c.post("/api/conta/entrar",
                   json={"nome": "baverone2", "senha": SENHA_BOA})
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True)[:400])
        d = c.get("/api/conta.json").get_json()
        self.assertTrue(d["entrado"])
        self.assertEqual(d["utilizador"]["slug"], "baverone2")
        self.assertTrue(d["csrf"], "sem CSRF não se podia trocar a password")

    def test_a_sessao_resolve_se_com_a_porta_fechada(self):
        """Era o que faltava: sem `g.sessao` o `/api/conta/senha` dava 401 a
        quem tinha acabado de entrar."""
        c = self.cliente(aberto=False)
        self.com_senha("miguel", SENHA_BOA)
        self.entrar(c, "miguel", SENHA_BOA)
        self.assertTrue(c.get("/api/conta.json").get_json()["entrado"])

    def test_o_travao_de_tentativas_vale_nas_duas_portas(self):
        """Deixar entrar não podia significar deixar adivinhar à vontade."""
        c = self.cliente(aberto=False)
        self.com_senha("miguel", SENHA_BOA)
        vistos = set()
        for _ in range(9):
            r = c.post("/api/conta/entrar",
                       json={"nome": "miguel", "senha": "nao-e-esta-pois"})
            vistos.add(r.status_code)
        self.assertIn(429, vistos, "o travão tinha de aparecer")


# --------------------------------------------------------------------------
# 3. NO ESTÁTICO NÃO APARECE NADA
# --------------------------------------------------------------------------


class TestNoEstaticoNaoApareceNada(Base):
    """*"Quero apenas apresentar quando tiver tudo"* — é ISTO que ele disse."""

    def sitio(self):
        from riftvault import build
        con = self.catalogo()
        con.close()
        fora = self.v.root / "site-publicado"
        build.build(fora, log=lambda *_: None)
        return fora

    def test_o_site_gerado_nao_tem_api_conta_json(self):
        fora = self.sitio()
        self.assertFalse((fora / "api" / "conta.json").exists(),
                         "o estático não tem rota nem ficheiro de conta")

    def test_o_site_gerado_diz_editable_false_e_por_isso_nao_pergunta(self):
        import json
        fora = self.sitio()
        d = json.loads((fora / "api" / "index.json").read_text(encoding="utf-8"))
        self.assertFalse(d["editable"])
        js = (fora / "app.js").read_text(encoding="utf-8")
        self.assertIn("state.conta = state.index.editable", js,
                      "é esta linha que não pergunta no estático")

    def test_o_html_publicado_nao_fala_de_contas(self):
        """O elemento existe e nasce `hidden`; o texto visível não diz nada."""
        fora = self.sitio()
        html = (fora / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="conta-zona"', html)
        self.assertIn("hidden", html.split('id="conta-zona"')[1][:60])
        visivel = re.sub(r"<!--.*?-->", "", html, flags=re.S)
        for palavra in ("Entrar com", "em breve", "Criar conta", "login",
                        "Iniciar sessão", "Password", "Utilizador"):
            self.assertNotIn(palavra, visivel,
                             f"«{palavra}» não pode aparecer no site publicado")

    def test_o_estatico_e_o_MESMO_com_a_porta_aberta_ou_fechada(self):
        """A porta não pode mexer num byte do que se publica.

        É a outra metade da decisão: o critério passou para «é o estático?», e
        por isso o site gerado deixou de depender do `multi.aberto`.
        """
        import json
        from riftvault import build
        con = self.catalogo()
        con.close()
        saidas = {}
        for aberto in (False, True):
            self.cfg({"multi": {"aberto": aberto}})
            fora = self.v.root / f"site-{aberto}"
            build.build(fora, log=lambda *_: None)
            saidas[aberto] = {
                p.relative_to(fora).as_posix(): p.read_bytes()
                for p in sorted(fora.rglob("*")) if p.is_file()
            }
        self.assertEqual(sorted(saidas[False]), sorted(saidas[True]),
                         "os mesmos ficheiros")
        for nome in saidas[False]:
            if nome.endswith(".json"):
                # O relógio (`generated_at`) muda a cada geração — é a regra do
                # `build.mesmo_conteudo` de 2026-09-10.
                a = json.loads(saidas[False][nome].decode("utf-8"))
                b = json.loads(saidas[True][nome].decode("utf-8"))
                for d in (a, b):
                    if isinstance(d, dict):
                        d.pop("generated_at", None)
                self.assertEqual(a, b, f"{nome} mudou com a porta")
            else:
                self.assertEqual(saidas[False][nome], saidas[True][nome],
                                 f"{nome} mudou com a porta")


# --------------------------------------------------------------------------
# 4. A TROCA DA TEMPORÁRIA COM A PORTA FECHADA
# --------------------------------------------------------------------------


class TestTrocarATemporariaComAPortaFechada(Base):
    """De ponta a ponta, por HTTP. É o que ele tem de conseguir fazer AGORA."""

    def test_o_percurso_inteiro(self):
        c = self.cliente(aberto=False)
        _uid, temporaria = self.conta_nova("baverone2", "Andre")

        # 1. entra com a temporária (a porta está FECHADA)
        r = c.post("/api/conta/entrar",
                   json={"nome": "baverone2", "senha": temporaria})
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True)[:400])
        self.assertTrue(r.get_json()["senha_temporaria"])

        # 2. o site está trancado, e o `api/conta.json` é o que passa a trava
        self.assertEqual(c.get("/api/index.json").status_code, 403)
        d = c.get("/api/conta.json").get_json()
        self.assertEqual(c.get("/api/conta.json").status_code, 200)
        self.assertTrue(d["entrado"])
        self.assertTrue(d["senha_temporaria"])
        self.assertFalse(d["editavel"], "com a temporária não se edita")

        # 3. troca
        r = c.post("/api/conta/senha",
                   json={"atual": temporaria, "nova": SENHA_BOA},
                   headers={"X-CSRF-Token": d["csrf"]})
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True)[:400])

        # 4. o site abre
        self.assertEqual(c.get("/api/index.json").status_code, 200)
        d2 = c.get("/api/conta.json").get_json()
        self.assertFalse(d2["senha_temporaria"])
        self.assertTrue(d2["editavel"])

    def test_a_temporaria_deixa_de_servir_depois_da_troca(self):
        c = self.cliente(aberto=False)
        _uid, temporaria = self.conta_nova("miguel")
        r = c.post("/api/conta/entrar",
                   json={"nome": "miguel", "senha": temporaria})
        csrf = c.get("/api/conta.json").get_json()["csrf"]
        c.post("/api/conta/senha", json={"atual": temporaria, "nova": SENHA_BOA},
               headers={"X-CSRF-Token": csrf})

        c2 = self.cliente(aberto=False)
        self.assertEqual(
            c2.post("/api/conta/entrar",
                    json={"nome": "miguel", "senha": temporaria}).status_code,
            401, "a temporária tinha de morrer")
        self.assertEqual(
            c2.post("/api/conta/entrar",
                    json={"nome": "miguel", "senha": SENHA_BOA}).status_code, 200)

    def test_uma_password_fraca_e_recusada_tambem_aqui(self):
        """As regras não afrouxam por a porta estar fechada."""
        c = self.cliente(aberto=False)
        _uid, temporaria = self.conta_nova("miguel")
        c.post("/api/conta/entrar", json={"nome": "miguel", "senha": temporaria})
        csrf = c.get("/api/conta.json").get_json()["csrf"]
        r = c.post("/api/conta/senha", json={"atual": temporaria, "nova": "curta"},
                   headers={"X-CSRF-Token": csrf})
        self.assertEqual(r.status_code, 400)
        self.assertIn("10", r.get_json()["erro"])

    def test_sair_e_sempre_possivel(self):
        """Senão a trava era uma armadilha: quem desistir tem de poder sair."""
        c = self.cliente(aberto=False)
        _uid, temporaria = self.conta_nova("miguel")
        c.post("/api/conta/entrar", json={"nome": "miguel", "senha": temporaria})
        self.assertEqual(c.get("/api/index.json").status_code, 403)
        c.get("/sair")
        self.assertEqual(c.get("/api/index.json").status_code, 200,
                         "sem sessão volta a ser o de ontem")


# --------------------------------------------------------------------------
# 5. O SEGUNDO BECO: o ecrã da troca nunca chegava a ser desenhado
# --------------------------------------------------------------------------


class TestOSegundoBeco(Base):
    """Existia com a porta ABERTA também, e ninguém o tinha visto.

    O `_trava_temporaria` responde 403 a tudo o que é `/api/`; o `boot()` pede
    o `api/index.json` na primeira linha e morria ali. O ecrã da troca — a
    ÚNICA coisa que se pode fazer com uma temporária — nunca era desenhado, e
    o que se lia era «Falhou a carregar: HTTP 403».
    """

    def test_o_index_json_e_barrado_e_o_conta_json_nao(self):
        for aberto in (False, True):
            with self.subTest(aberto=aberto):
                c = self.cliente(aberto=aberto)
                _uid, tmp = self.conta_nova(f"m{int(aberto)}")
                c.post("/api/conta/entrar",
                       json={"nome": f"m{int(aberto)}", "senha": tmp})
                self.assertEqual(c.get("/api/index.json").status_code, 403)
                self.assertEqual(c.get("/api/conta.json").status_code, 200)

    def test_o_boot_apanha_o_403_e_desenha_a_troca(self):
        js = APP_JS.read_text(encoding="utf-8")
        boot = js.split("async function boot()")[1][:900]
        self.assertIn("mostrarSeTrancado", boot,
                      "o `boot()` tem de tratar o índice barrado")
        # E a função não decide nada por si: pergunta ao servidor.
        fn = js.split("async function mostrarSeTrancado()")[1][:1400]
        self.assertIn("api/conta.json", fn)
        self.assertIn("senha_temporaria", fn)
        self.assertIn("renderConta()", fn)

    def test_o_ecra_trancado_diz_o_que_se_passa_FORA_das_seccoes(self):
        """Apanhado na fotografia, não no código.

        A primeira versão escrevia a frase no `#grid`, que vive dentro de uma
        `<section hidden>` — o `boot()` nunca chegou à parte que abre uma. O que
        se via era um ecrã preto ao lado do formulário.
        """
        js = APP_JS.read_text(encoding="utf-8")
        fn = js.split("async function mostrarSeTrancado()")[1][:2400]
        self.assertIn("#pg-titulo", fn, "a frase tem de ir para o cabeçalho")
        # O QUE CONTA É O CÓDIGO, NÃO O COMENTÁRIO (2026-09-30). A primeira
        # versão deste teste procurava «#grid» no texto todo e apanhava a
        # própria explicação de porque é que o `#grid` não serve — dava a
        # documentação como defeito. Tiram-se os comentários primeiro.
        import re as _re
        codigo = _re.sub(r"/\*.*?\*/", "", fn, flags=_re.S)
        codigo = "\n".join(l.split("//")[0] for l in codigo.splitlines())
        self.assertNotIn("#grid", codigo,
                         "o #grid está dentro de uma secção hidden")

    def test_o_ecra_trancado_nao_desenha_a_NAVEGACAO(self):
        """Também da fotografia: mostrava as três abas escondidas.

        As `abas.escondidas` (2026-09-25) vêm no `api/index.json`, que está
        barrado — e sem elas o `renderNav()` desenha tudo, incluindo o «A mais»,
        o «Por deck» e o «Pimp decks» que ele mandou tirar.
        """
        js = APP_JS.read_text(encoding="utf-8")
        fn = js.split("async function mostrarSeTrancado()")[1][:1400]
        self.assertNotIn("renderNav()", fn)
        self.assertIn("#sidenav", fn)

    def test_um_erro_que_NAO_e_a_trava_continua_a_dizer_o_que_e(self):
        """A rede não pode engolir o «corre o riftvault sync»."""
        js = APP_JS.read_text(encoding="utf-8")
        boot = js.split("async function boot()")[1][:900]
        self.assertIn("throw err", boot,
                      "sem sessão trancada, o erro original tem de subir")
        fn = js.split("async function mostrarSeTrancado()")[1][:700]
        self.assertIn("return false", fn)


# --------------------------------------------------------------------------
# 6. A REDE DE SEGURANÇA: `riftvault conta <slug> --definir-password`
# --------------------------------------------------------------------------


class TestDefinirPasswordPelaConsola(Base):
    """Para nunca mais haver um beco destes: a troca sem browser."""

    def correr(self, *argv, escritas=("", "")):
        """Corre a CLI com o `getpass` substituído. Devolve (código, saída)."""
        import getpass
        import io
        import contextlib
        from riftvault import cli

        pedidas = []

        def falso(prompt=""):
            pedidas.append(prompt)
            return escritas[len(pedidas) - 1]

        real = getpass.getpass
        getpass.getpass = falso
        saida = io.StringIO()
        try:
            with contextlib.redirect_stdout(saida), \
                    contextlib.redirect_stderr(saida):
                codigo = cli.main(list(argv))
        finally:
            getpass.getpass = real
        return codigo, saida.getvalue(), pedidas

    def test_define_a_password_e_a_temporaria_deixa_de_servir(self):
        c = self.cliente(aberto=False)
        _uid, temporaria = self.conta_nova("miguel")
        codigo, saida, pedidas = self.correr(
            "conta", "miguel", "--definir-password",
            escritas=(SENHA_BOA, SENHA_BOA))
        self.assertEqual(codigo, 0, saida)
        self.assertEqual(len(pedidas), 2, "tem de perguntar DUAS vezes")

        c2 = self.cliente(aberto=False)
        self.assertEqual(
            c2.post("/api/conta/entrar",
                    json={"nome": "miguel", "senha": SENHA_BOA}).status_code,
            200, "a escolhida tem de servir")
        self.assertEqual(
            c2.post("/api/conta/entrar",
                    json={"nome": "miguel", "senha": temporaria}).status_code,
            401, "a temporária tinha de morrer")
        _ = c

    def test_deixa_de_ser_temporaria_e_por_isso_nao_tranca_o_site(self):
        self.conta_nova("miguel")
        self.correr("conta", "miguel", "--definir-password",
                    escritas=(SENHA_BOA, SENHA_BOA))
        con = self.auth.abrir()
        try:
            e = self.auth.estado_senha(con, self.utilizador.por_slug("miguel")["user_id"])
        finally:
            con.close()
        self.assertTrue(e["tem"])
        self.assertFalse(e["temporaria"], "escolhida não é ditada")

        c = self.cliente(aberto=False)
        self.entrar(c, "miguel", SENHA_BOA)
        self.assertEqual(c.get("/api/index.json").status_code, 200,
                         "o site tem de estar aberto a quem escolheu a sua")

    def test_as_duas_diferentes_nao_gravam_nada(self):
        self.com_senha("miguel", SENHA_BOA)
        codigo, saida, _ = self.correr(
            "conta", "miguel", "--definir-password",
            escritas=(SENHA_BOA, "outra-coisa-qualquer"))
        self.assertEqual(codigo, 1)
        self.assertIn("não são iguais", saida)
        c = self.cliente(aberto=False)
        self.assertEqual(
            c.post("/api/conta/entrar",
                   json={"nome": "miguel", "senha": SENHA_BOA}).status_code,
            200, "a que estava não podia ter mudado")

    def test_recusa_as_FRACAS_com_as_regras_do_site(self):
        """As mesmas regras, e é o ponto: não há uma porta mais frouxa."""
        from riftvault import senha as senha_mod
        self.com_senha("miguel", SENHA_BOA)
        casos = [
            ("curta", "10 caracteres"),
            ("password123", "mais usadas"),
            ("o-miguel-anda-a-pe", "o teu nome"),
            ("aaaaaaaaaaaa", "mesmo caractere"),
            ("  mesmo-assim-longa  ", "espaço"),
        ]
        for fraca, pedaco in casos:
            with self.subTest(fraca=fraca):
                codigo, saida, _ = self.correr(
                    "conta", "miguel", "--definir-password",
                    escritas=(fraca, fraca))
                self.assertEqual(codigo, 1, f"«{fraca}» tinha de ser recusada")
                self.assertIn(pedaco, saida)
        # E a razão é a do módulo, não uma cópia.
        with self.assertRaises(senha_mod.SenhaFraca):
            senha_mod.validar("curta")

    def test_nao_mostra_a_password_nem_a_escreve_em_lado_nenhum(self):
        """O `getpass` não a mostra; e ela não pode sair na saída do comando."""
        self.conta_nova("miguel")
        codigo, saida, _ = self.correr(
            "conta", "miguel", "--definir-password",
            escritas=(SENHA_BOA, SENHA_BOA))
        self.assertEqual(codigo, 0, saida)
        self.assertNotIn(SENHA_BOA, saida,
                         "a password escolhida não pode aparecer no ecrã")
        # E o comando usa o `getpass`, não um `input()` nem um argumento.
        fonte = (REPO / "riftvault" / "cli.py").read_text(encoding="utf-8")
        fn = fonte.split("def _perguntar_password(")[1][:1600]
        self.assertIn("getpass.getpass", fn)
        self.assertNotIn("input(", fn)
        self.assertNotIn("--password ", fonte,
                         "nunca um argumento: ia para o histórico da consola")

    def test_um_slug_que_nao_existe_diz_o_que_e(self):
        codigo, saida, pedidas = self.correr(
            "conta", "naoexiste", "--definir-password",
            escritas=(SENHA_BOA, SENHA_BOA))
        self.assertEqual(codigo, 1)
        self.assertEqual(pedidas, [], "nem chega a perguntar a password")

    def test_sem_slug_diz_como_se_escreve(self):
        codigo, saida, _ = self.correr("conta", "--definir-password")
        self.assertEqual(codigo, 1)
        self.assertIn("--definir-password", saida)

    def test_fecha_as_sessoes_abertas_dela(self):
        """Como a troca pelo site: se ele está a fazer isto, alguém pode ter
        tido a password."""
        c = self.cliente(aberto=False)
        self.com_senha("miguel", SENHA_BOA)
        self.entrar(c, "miguel", SENHA_BOA)
        self.assertTrue(c.get("/api/conta.json").get_json()["entrado"])
        self.correr("conta", "miguel", "--definir-password",
                    escritas=("outra-frase-comprida", "outra-frase-comprida"))
        self.assertFalse(c.get("/api/conta.json").get_json()["entrado"],
                         "a sessão antiga tinha de cair")

    def test_esta_na_ajuda_e_no_abrir(self):
        fonte = (REPO / "riftvault" / "cli.py").read_text(encoding="utf-8")
        self.assertIn('"--definir-password"', fonte)
        # E o `multi --verificar` passou a apontar para cá, que é o comando que
        # resolve o passo dele num só.
        self.assertIn("--definir-password",
                      (REPO / "riftvault" / "abrir.py").read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# 7. O QUE NÃO MUDOU
# --------------------------------------------------------------------------


class TestTudoComoOntem(Base):
    """Com a porta fechada e SEM SESSÃO, escrever não pede nada."""

    def test_escreve_sem_sessao_e_sem_csrf(self):
        c = self.cliente(aberto=False)
        r = c.post("/api/adjust", json={"printing_id": "tst-001-100", "delta": 1})
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True)[:300])
        self.assertEqual(r.get_json()["qty"], 1)

    def test_sem_cookie_nem_se_abre_o_auth_db(self):
        """O caminho normal dele fica ao byte: um pedido, um ficheiro a menos.

        Mede-se pelo código, que é onde a decisão está — o `auth.db` só se abre
        quando há cookie.
        """
        fonte = (REPO / "riftvault" / "rotas_conta.py").read_text(encoding="utf-8")
        antes = fonte.split("def _antes()")[1][:1800]
        self.assertIn("_auth_con() if sid else None", antes)

    def test_com_a_porta_fechada_MAS_com_sessao_o_guarda_corre(self):
        """Estritamente mais seguro do que ontem, e é preciso: ele já pode criar
        a conta de um amigo com a porta fechada (`riftvault conta --criar`), e
        sem isto esse amigo escrevia no config partilhado dele."""
        c = self.cliente(aberto=False)
        self.com_senha("miguel", SENHA_BOA)
        self.entrar(c, "miguel", SENHA_BOA)
        # Sem a marca de CSRF, agora que há sessão, a escrita recusa.
        r = c.post("/api/adjust", json={"printing_id": "tst-001-100", "delta": 1})
        self.assertEqual(r.status_code, 403, r.get_data(as_text=True)[:300])
        # E as duas rotas do config partilhado são só do dono.
        r = c.post("/api/decks/montar", json={"slug": "x", "montado": True},
                   headers={"X-CSRF-Token":
                            c.get("/api/conta.json").get_json()["csrf"]})
        self.assertEqual(r.status_code, 403)

    def test_com_a_porta_fechada_nao_se_registra_ninguem(self):
        c = self.cliente(aberto=False)
        r = c.post("/api/conta/registar", json={"slug": "miguel"})
        self.assertIn(r.status_code, (401, 403))

    def test_o_oauth_continua_a_exigir_a_porta_aberta(self):
        """Só a PASSWORD passou a valer com a porta fechada."""
        c = self.cliente(aberto=False)
        for nome in ("google", "discord", "local"):
            self.assertEqual(c.get(f"/entrar/{nome}").status_code, 403, nome)


if __name__ == "__main__":
    unittest.main(verbosity=2)

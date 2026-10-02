"""Os achados 3, 4 e 6 do `docs/varrimento-2026-10-01.md`, fechados (2026-10-02).

Três defeitos que a suite de 2 403 testes deixava passar — e §8 do varrimento
diz porquê: faltavam exactamente estes testes.

  **3. O `multi --verificar` PRESUMIA.** Dois passos marcados `[TEU]` («a conta
     na Cloudflare», «os nameservers + o túnel»), como se faltassem fazer,
     quando estavam feitos desde 29/09 e eram verificáveis — medido ao vivo no
     varrimento e outra vez a 02/10: serviço `RUNNING`, e o
     `editar.baverone.com/api/conta.json` a responder **200 com nove sinais de
     «fora»**. E era o passo com risco declarado («o rift.baverone.com não pode
     cair»). Hoje é UM passo que PERGUNTA, e `ok=None` quer dizer «não sei».

  **4. O PAYLOAD CONTRADIZIA-SE.** Quinze `editable=True` fixos no `server.py`
     contra o `editavel` do `/api/conta.json`. Medido no mesmo pedido anónimo,
     com a porta aberta: o `conta.json` dizia `false` e **oito payloads diziam
     `true`**. Hoje uma resposta só — `rotas_conta.editavel()`.

  **6. O `conta.apagar` DEIXAVA O HASH DA PASSWORD ATRÁS.** Os dois chamadores
     reais limpavam-no; o terceiro é que pagava. Hoje limpa a primitiva.

  **E o `.nojekyll` da raiz**, que não é da varredura: desde que a lista tomou
     a raiz, o `build._gerar` escreve-o em `u/baverone/` e **ninguém** o escreve
     na raiz — só sobrevivia por estar COMMITADO. Medido a 02/10 numa geração
     contra uma cópia do `data/` real: a raiz saía com `api/`, `index.html` e
     `u/`, e mais nada.

CONTRA PASTAS TEMPORÁRIAS E UM CONFIG TEMPORÁRIO — o `data/` e o
`riftvault_config.json` a sério nunca são tocados, e **nenhum teste daqui vai à
rede**: a medição do túnel injecta-se (ver o `abrir.verificar(medir=...)`), que
é metade da razão de ela ser injectável.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.fixture import REPO  # noqa: E402
from tests.test_senhas import Base  # noqa: E402

APP_JS = REPO / "riftvault" / "web" / "app.js"
SENHA_BOA = "o-meu-gato-dorme-muito"

#: Um pedido que chega pelo túnel, como ele chega a sério. Nove sinais medidos
#: a 2026-10-01 contra o túnel vivo; aqui basta um para a origem ser «fora».
DE_FORA = {"CF-Connecting-IP": "203.0.113.9", "CF-Ray": "abc-LIS",
           "X-Forwarded-For": "203.0.113.9"}


# ==========================================================================
# ACHADO 3 — A VERIFICAÇÃO MEDE, E «NÃO SEI» NÃO É «FALTA»
# ==========================================================================


def medicao(**campos):
    """Uma medição forjada, para a bateria não ir à rede."""
    base = {"respondeu": True, "codigo": 200, "origem": "fora",
            "sinais": ["a", "b", "c"], "url": "https://x/api/conta.json"}
    base.update(campos)
    return lambda _base: base


class TestOTunelMedeSe(Base):
    """O passo dele deixou de ser presumido."""

    CFG = {"auth": {"base_url": "https://editar.baverone.com"}}

    def passo(self, medir=None, extra=None):
        self.cfg({**self.CFG, **(extra or {})})
        est = self.abrir.verificar(self.config.load(), medir=medir)
        achados = [p for p in est["passos"]
                   if p["nome"] == self.abrir.NOME_DO_TUNEL]
        self.assertEqual(len(achados), 1,
                         [p["nome"] for p in est["passos"]])
        return achados[0], est

    def test_tunel_vivo_da_OK_e_diz_que_os_passos_nao_se_repetem(self):
        p, _ = self.passo(medicao())
        self.assertIs(p["ok"], True)
        self.assertIn("MEDIDO", p["diz"])
        self.assertIn("3 sinais", p["diz"])
        self.assertIn("não têm de se repetir", p["diz"])

    def test_um_sinal_so_escreve_se_no_singular(self):
        p, _ = self.passo(medicao(sinais=["um"]))
        self.assertIn("1 sinal de", p["diz"])

    def test_SEM_REDE_a_resposta_e_NAO_SEI_e_nunca_FALTA(self):
        """A diferença entre não medir e medir mal — era medir mal que lá estava."""
        p, _ = self.passo(medicao(respondeu=False, erro="URLError: sem rede"))
        self.assertIsNone(p["ok"], "sem rede não se pode dizer que falta")
        self.assertIn("não consegui perguntar", p["diz"])
        self.assertIn("sem rede", p["diz"].lower())

    def test_sem_medicao_pedida_tambem_e_NAO_SEI(self):
        p, _ = self.passo(None)
        self.assertIsNone(p["ok"])
        self.assertIn("não medi", p["diz"])

    def test_sem_endereco_escrito_nao_ha_nada_para_medir(self):
        self.cfg({})
        est = self.abrir.verificar(self.config.load(),
                                   medir=medicao())
        p = [x for x in est["passos"] if x["nome"] == self.abrir.NOME_DO_TUNEL][0]
        self.assertIsNone(p["ok"])
        self.assertIn("auth.base_url", p["diz"])

    def test_um_codigo_que_nao_e_200_e_FALTA_a_dizer_o_codigo(self):
        """530 da Cloudflare: o DNS resolve e o túnel está em baixo."""
        p, _ = self.passo(medicao(codigo=530, origem=None, sinais=[]))
        self.assertIs(p["ok"], False)
        self.assertIn("530", p["diz"])

    def test_responder_200_sem_ser_o_riftvault_e_FALTA(self):
        p, _ = self.passo(medicao(erro="respondeu, mas o que veio não é o "
                                       "riftvault", origem=None, sinais=[]))
        self.assertIs(p["ok"], False)
        self.assertIn("outra coisa", p["diz"])

    def test_a_app_dizer_que_o_pedido_veio_DE_CASA_e_FALTA(self):
        """O endereço público não está a passar por túnel nenhum."""
        p, _ = self.passo(medicao(origem="casa", sinais=[]))
        self.assertIs(p["ok"], False)
        self.assertIn("de CASA", p["diz"])
        self.assertIn("configuração errada", p["diz"])

    def test_os_dois_PASSOS_dele_continuam_escritos_quando_da_vermelho(self):
        """Deixou de se presumir se estão FEITOS, não de dizer quais são."""
        p, _ = self.passo(medicao(codigo=502, origem=None, sinais=[]))
        self.assertIn("PASSOS 1 e 2", p["como"])
        self.assertIn("abrir-a-porta.md", p["como"])
        self.assertIn("Cloudflared", p["como"],
                      "quando dá vermelho tem de dizer o que olhar aqui")

    def test_o_passo_do_tunel_NAO_trava_o_abrir(self):
        """Nem com vermelho, nem com «não sei» — ver `abrir._medido`.

        O `--abrir` recusa pelos passos que o deixam de FORA da própria coleção.
        Abrir com o túnel em baixo não perde nada: os amigos não chegam lá. E
        travar por um `ok=None` era não deixar abrir num avião.
        """
        self.com_senha("baverone-ja-existe", SENHA_BOA)  # não é ele; só ruído
        con = self.auth.abrir()
        try:
            self.auth.definir_senha(con, 1, SENHA_BOA, temporaria=False)
        finally:
            con.close()
        for medir in (None, medicao(codigo=530, origem=None, sinais=[])):
            _p, est = self.passo(medir)
            self.assertTrue(est["pode_abrir"],
                            [x["nome"] for x in est["faltam"]])

    def test_nenhum_passo_diz_TEU_e_o_None_le_se_NAO_SEI(self):
        p, est = self.passo(None)
        texto = self.abrir.texto(est)
        self.assertNotIn("TEU", texto)
        self.assertIn("NÃO SEI", texto)

    def test_a_medicao_e_INJECTAVEL_e_por_omissao_nao_ha_rede(self):
        """Uma biblioteca que vá à rede nas costas de quem a chama fica a ver
        se um `urlopen` estoura o prazo — e o `verificar` é chamado pelo
        `--abrir` e por esta bateria inteira."""
        fonte = (REPO / "riftvault" / "abrir.py").read_text(encoding="utf-8")
        assinatura = fonte.split("def verificar(")[1].split(")")[0]
        self.assertIn("medir=None", assinatura.replace(" ", ""))
        # E quem PEDE a medição é o comando que um humano corre.
        cli = (REPO / "riftvault" / "cli.py").read_text(encoding="utf-8")
        self.assertIn("medir=porta.perguntar_ao_tunel", cli)

    def test_o_prober_pergunta_ao_conta_json_que_passa_de_fora(self):
        """É a única rota que diz `origem`/`sinais` E que passa sem sessão
        vindo de fora. Qualquer outra dava 401, e aí não se distinguia «o
        túnel está em baixo» de «o túnel está vivo e pediu password»."""
        fonte = (REPO / "riftvault" / "abrir.py").read_text(encoding="utf-8")
        trecho = fonte.split("def perguntar_ao_tunel(")[1][:2500]
        self.assertIn("/api/conta.json", trecho)
        self.assertIn("/api/conta.json", self.rotas_conta.DE_FORA_SEM_SESSAO)

    def test_o_prober_nunca_levanta_devolve_o_nao_sei(self):
        """Sem rede tem de ser um resultado, não uma excepção a subir."""
        r = self.abrir.perguntar_ao_tunel(
            "https://nao-existe-isto-mesmo.invalid", espera=1.0)
        self.assertFalse(r["respondeu"])
        self.assertTrue(r["erro"])

    def test_o_user_agent_e_ASCII_puro(self):
        """A regra desta casa desde 2026-08-31: com acentos dá 403."""
        self.abrir.USER_AGENT.encode("ascii")
        self.assertNotIn("Mozilla", self.abrir.USER_AGENT,
                         "nunca se finge ser um browser")


class TestOTunelMedidoDePONTA_A_PONTA(Base):
    """O prober contra o SERVIDOR a sério, sem sair da máquina.

    É a prova de que a leitura que ele faz da resposta é a certa: levanta-se o
    `riftvault serve` em memória, forja-se um pedido com os cabeçalhos do túnel,
    e o `origem`/`sinais` que o prober lê é o que a app escreveu.
    """

    def test_a_app_responde_fora_com_os_sinais_e_o_prober_leria_isso(self):
        c = self.cliente(aberto=True)
        d = c.get("/api/conta.json", headers=DE_FORA).get_json()
        self.assertEqual(d["origem"], "fora")
        self.assertTrue(d["sinais"])
        # O prober só lê estes dois campos da resposta.
        p = self.abrir._tunel(
            {"auth": {"base_url": "https://editar.baverone.com"}},
            lambda _b: {"respondeu": True, "codigo": 200,
                        "origem": d["origem"], "sinais": d["sinais"]})
        self.assertIs(p["ok"], True)

    def test_de_casa_a_app_diz_casa_e_o_passo_da_vermelho(self):
        c = self.cliente(aberto=True)
        d = c.get("/api/conta.json").get_json()
        self.assertEqual(d["origem"], "casa")
        p = self.abrir._tunel(
            {"auth": {"base_url": "https://editar.baverone.com"}},
            lambda _b: {"respondeu": True, "codigo": 200,
                        "origem": d["origem"], "sinais": d["sinais"]})
        self.assertIs(p["ok"], False,
                      "o endereço público a responder «casa» é configuração "
                      "errada, e tem de se dizer")


# ==========================================================================
# ACHADO 4 — UMA RESPOSTA SÓ A «PODES ESCREVER?»
# ==========================================================================


class TestOPayloadNaoSeContradiz(Base):
    """O `editable` de cada payload e o `editavel` do `conta.json`.

    Media-se no varrimento: mesmo pedido, mesmo minuto, `editavel: false` numa
    resposta e `editable: true` em oito. Aqui varrem-se TODAS as rotas de
    leitura que o `url_map` tiver — não uma amostra —, para uma rota nova não
    poder nascer a mentir.
    """

    ROTAS = ["/api/index.json", "/api/decks.json", "/api/set/TST.json",
             "/api/runas.json", "/api/venda.json", "/api/selado.json",
             "/api/encomendas.json", "/api/encomendas/TST.json"]

    def payloads_com_editable(self, c, **kw):
        """Todas as respostas de leitura que trazem o campo, e o valor dele."""
        out = {}
        for rota in self.ROTAS:
            r = c.get(rota, **kw)
            if r.status_code != 200:
                continue
            d = r.get_json(silent=True)
            if isinstance(d, dict) and "editable" in d:
                out[rota] = d["editable"]
        return out

    def test_porta_ABERTA_e_anonimo_de_casa_ninguem_diz_true(self):
        """O defeito, ao contrário: era aqui que os oito diziam `true`."""
        c = self.cliente(aberto=True)
        conta = c.get("/api/conta.json").get_json()
        self.assertFalse(conta["editavel"])
        vistos = self.payloads_com_editable(c)
        self.assertTrue(vistos, "nenhuma rota trouxe o campo — teste cego")
        for rota, valor in vistos.items():
            self.assertEqual(valor, conta["editavel"],
                             f"{rota} contradiz o /api/conta.json")

    def test_porta_FECHADA_e_de_casa_e_tudo_true_como_SEMPRE_FOI(self):
        """A promessa de «o uso dele em casa fica igual» — e é a que importa:
        fazer o campo honesto não podia pôr a Coleção dele em leitura."""
        c = self.cliente(aberto=False)
        conta = c.get("/api/conta.json").get_json()
        self.assertTrue(conta["editavel"])
        vistos = self.payloads_com_editable(c)
        self.assertTrue(vistos)
        for rota, valor in vistos.items():
            self.assertTrue(valor, f"{rota} ficou em leitura e não devia")

    def test_DE_FORA_sem_sessao_nem_se_chega_aos_payloads(self):
        """A regra da ORIGEM (2026-10-01) responde antes: 401 em tudo."""
        c = self.cliente(aberto=False)
        for rota in self.ROTAS:
            self.assertEqual(c.get(rota, headers=DE_FORA).status_code, 401,
                             rota)
        self.assertFalse(
            c.get("/api/conta.json", headers=DE_FORA).get_json()["editavel"])

    def test_ENTRADO_na_sua_coleccao_pode_escrever_e_o_payload_diz(self):
        c = self.cliente(aberto=True)
        con = self.auth.abrir()
        try:
            self.auth.definir_senha(con, 1, SENHA_BOA, temporaria=False)
        finally:
            con.close()
        self.entrar(c, "baverone", SENHA_BOA)
        conta = c.get("/api/conta.json").get_json()
        self.assertTrue(conta["editavel"])
        for rota, valor in self.payloads_com_editable(c).items():
            self.assertTrue(valor, rota)

    def test_com_a_TEMPORARIA_ninguem_diz_true(self):
        """Com ela o site está trancado: `+`/`−` à vista eram 403 por clique."""
        c = self.cliente(aberto=True)
        _uid, tmp = self.conta_nova("zeteste")
        c.post("/api/conta/entrar", json={"nome": "zeteste", "senha": tmp})
        self.assertTrue(c.get("/api/conta.json").get_json()["senha_temporaria"])
        self.assertFalse(c.get("/api/conta.json").get_json()["editavel"])
        # A trava responde 403 a tudo o que é `/api/`, por isso não há payload
        # nenhum para contradizer — e é essa a invariante a fixar.
        for rota in self.ROTAS:
            self.assertIn(c.get(rota).status_code, (401, 403), rota)

    def test_ha_UMA_definicao_e_o_server_nao_tem_mais_nenhum_True_fixo(self):
        fonte = (REPO / "riftvault" / "server.py").read_text(encoding="utf-8")
        self.assertNotIn("editable=True", fonte)
        self.assertNotIn('"editable": True', fonte)
        self.assertIn("rotas_conta.editavel()", fonte)
        # E a regra vive onde está o `g` que a decide, não aqui.
        rc = (REPO / "riftvault" / "rotas_conta.py").read_text(encoding="utf-8")
        self.assertIn("def editavel()", rc)

    def test_o_api_conta_usa_a_MESMA_funcao_e_nao_repete_a_regra(self):
        rc = (REPO / "riftvault" / "rotas_conta.py").read_text(encoding="utf-8")
        rota = rc.split("def api_conta(")[1].split("\ndef ")[0]
        self.assertIn('"editavel": editavel()', rota)
        self.assertNotIn("not aberto and de_casa", rota,
                         "a regra tem de estar escrita uma vez só")


class TestServidorNaoEEditable(Base):
    """As duas perguntas que o `editable` respondia de uma vez.

    Era isto que impedia o campo de dizer a verdade: o `boot()` usava-o para
    decidir se vale a pena pedir o `api/conta.json`, e com a porta aberta um
    leitor anónimo tem `editable: false` **e** tem de ver a caixa de «Entrar».
    Com um campo só, torná-lo honesto escondia a entrada — o beco de 30/09 por
    outro caminho.
    """

    def test_o_boot_pede_o_conta_json_pelo_SERVIDOR_e_nao_pelo_editable(self):
        js = APP_JS.read_text(encoding="utf-8")
        self.assertIn("state.conta = state.index.servidor", js)
        self.assertNotIn("state.conta = state.index.editable", js)

    def test_o_servidor_diz_servidor_true_mesmo_a_quem_nao_pode_escrever(self):
        c = self.cliente(aberto=True)
        d = c.get("/api/index.json").get_json()
        self.assertTrue(d["servidor"], "sem isto a caixa de Entrar desaparecia")
        self.assertFalse(d["editable"])

    def test_o_build_diz_servidor_false(self):
        from riftvault import build
        fora = self.v.root / "site-servidor"
        build.build(fora, log=lambda *_: None)
        d = json.loads((fora / "api" / "index.json").read_text(encoding="utf-8"))
        self.assertFalse(d["servidor"])
        self.assertFalse(d["editable"])

    def test_a_omissao_do_campo_le_se_como_NAO_E_O_SERVIDOR(self):
        """Um ficheiro gerado por uma versão antiga não pode passar por
        servidor — e é por isso que a omissão é `False`."""
        from riftvault import metrics
        con = self.catalogo()
        try:
            self.assertFalse(metrics.index_payload(con)["servidor"])
        finally:
            con.close()

    def test_a_caixa_de_entrar_continua_a_aparecer_a_quem_tem_de_entrar(self):
        """De ponta a ponta: o que o `boot()` lê é o que decide o ecrã."""
        c = self.cliente(aberto=True)
        idx = c.get("/api/index.json").get_json()
        self.assertTrue(idx["servidor"])          # => o boot() pergunta
        conta = c.get("/api/conta.json").get_json()
        self.assertEqual(c.get("/api/conta.json").status_code, 200)
        self.assertFalse(conta["editavel"])       # => a página é de leitura
        self.assertTrue(conta["senha"])           # => e há por onde entrar


# ==========================================================================
# ACHADO 6 — APAGAR A CONTA APAGA A PASSWORD
# ==========================================================================


class TestApagarNaoDeixaNadaNoAuthDb(Base):
    """Por CADA caminho de apagar, varre-se o `auth.db` à procura do id.

    Hoje não havia hash órfão por um caminho real — os dois chamadores
    lembravam-se, e o `users.user_id` é `AUTOINCREMENT`, por isso ninguém herda
    a password de ninguém. O defeito era confiar na MEMÓRIA de quem chama, com o
    terceiro chamador a pagar.
    """

    TABELAS = ("user_auth", "sessions", "user_senha")

    def preparar(self, slug="zeteste"):
        uid = self.com_senha(slug, SENHA_BOA)
        con = self.auth.abrir()
        try:
            self.auth.ligar_identidade(con, uid, "discord", f"sub-{slug}") \
                if hasattr(self.auth, "ligar_identidade") else None
        finally:
            con.close()
        self.assertTrue(self.rastos(uid), "não semeou nada — teste cego")
        return uid

    def rastos(self, uid: int) -> dict:
        con = self.auth.abrir()
        try:
            out = {}
            for t in self.TABELAS:
                try:
                    n = con.execute(
                        f"SELECT COUNT(*) FROM {t} WHERE user_id = ?",
                        (uid,)).fetchone()[0]
                except Exception:
                    n = 0
                if n:
                    out[t] = n
            return out
        finally:
            con.close()

    # -- o defeito, pela PRIMITIVA (era aqui que ficava) -------------------

    def test_pela_BIBLIOTECA_nao_fica_nada(self):
        from riftvault import conta
        uid = self.preparar()
        r = conta.apagar("zeteste", confirmar=True, com_backup=False)
        self.assertEqual(self.rastos(uid), {},
                         "o hash da password ficou atrás")
        self.assertIn("auth", r, "e tem de DIZER o que limpou")

    def test_pela_CLI_nao_fica_nada(self):
        from riftvault import cli
        uid = self.preparar()
        self.assertEqual(
            cli.main(["conta", "zeteste", "--apagar", "--sim"]), 0)
        self.assertEqual(self.rastos(uid), {})

    def test_pela_ROTA_nao_fica_nada(self):
        c = self.cliente(aberto=True)
        uid = self.preparar()
        csrf = self.entrar(c, "zeteste", SENHA_BOA)
        r = c.post("/api/conta/apagar", json={"confirmar": "zeteste"},
                   headers={"X-CSRF-Token": csrf})
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True)[:300])
        self.assertEqual(self.rastos(uid), {})

    def test_PROVA_PELA_NEGATIVA_o_varrimento_sabe_encontrar(self):
        """Um varrimento que nunca ache nada vale zero."""
        uid = self.preparar("outro")
        self.assertIn("user_senha", self.rastos(uid))

    # -- a forma, não só o resultado --------------------------------------

    def test_a_contagem_vai_no_resultado_e_os_chamadores_leem_dali(self):
        """Não se limpa duas vezes: a primitiva limpa e DIZ, e quem chama lê."""
        from riftvault import conta
        self.preparar()
        r = conta.apagar("zeteste", confirmar=True, com_backup=False)
        self.assertEqual(r["auth"]["senhas"], 1)
        for ficheiro in ("cli.py", "rotas_conta.py"):
            fonte = (REPO / "riftvault" / ficheiro).read_text(encoding="utf-8")
            self.assertNotIn("auth.esquecer_identidades(", fonte,
                             f"o {ficheiro} ainda limpa por fora — é a "
                             f"disciplina duplicada que o §6 descreve")

    def test_a_casa_continua_a_ser_a_do_auth_e_so_a_chamada_mudou(self):
        """A `user_auth` é da casa da autenticação; o que mudou é QUEM manda."""
        fonte = (REPO / "riftvault" / "conta.py").read_text(encoding="utf-8")
        self.assertIn("auth.esquecer_identidades", fonte)
        # Só o CORPO: a docstring fala das duas coisas e noutra ordem.
        apagar = fonte.split("def apagar(")[1].split("\ndef ")[0]
        corpo = apagar.split('"""')[2]
        self.assertLess(corpo.index("utilizador.apagar(uid)"),
                        corpo.index("esquecer_identidades"),
                        "é DEPOIS do apagar: se o apagar falhasse, limpar a "
                        "password primeiro deixava uma conta VIVA sem entrada")

    def test_o_utilizador_1_continua_a_nao_se_apagar_por_aqui(self):
        from riftvault import conta
        with self.assertRaises(conta.NaoSeApaga):
            conta.apagar("baverone", confirmar=True)


# ==========================================================================
# E O `.nojekyll` DA RAIZ
# ==========================================================================


class TestONojekyllDaRaiz(Base):
    """Sem ele o GitHub Pages ignora pastas começadas por `_`.

    O da raiz só sobrevivia por estar COMMITADO: desde que a lista tomou a raiz,
    o `build._gerar` escreve-o na pasta que gera, que é `u/baverone/`. Uma
    geração num clone limpo não o criava — medido a 2026-10-02.
    """

    def publicos(self):
        """Dois públicos: é o que faz a lista tomar a raiz."""
        self.cfg({"multi": {"aberto": True}})
        from riftvault import privacidade
        u = self.utilizador.criar("Amigo", "amigo")
        privacidade.definir(user_id=int(u["user_id"]), valor="tudo")
        privacidade.definir(user_id=self.utilizador.ANDRE, valor="tudo")
        con = self.catalogo()
        con.close()

    def test_com_a_LISTA_na_raiz_o_nojekyll_nasce_la(self):
        from riftvault import build, lista
        self.publicos()
        fora = self.v.root / "site-lista"
        build.build_todos(fora, log=lambda *_: None)
        self.assertTrue((fora / "index.html").exists())
        self.assertTrue(lista.na_raiz(lista.publicas(self.config.load())),
                        "sem a lista na raiz este teste não mede nada")
        self.assertTrue(
            (fora / ".nojekyll").exists(),
            "o .nojekyll da raiz só existia por estar commitado")

    def test_e_continua_a_nascer_na_pasta_de_cada_um(self):
        from riftvault import build
        self.publicos()
        fora = self.v.root / "site-cada"
        build.build_todos(fora, log=lambda *_: None)
        for slug in ("baverone", "amigo"):
            self.assertTrue((fora / "u" / slug / ".nojekyll").exists(), slug)

    def test_com_UMA_coleccao_publica_a_raiz_e_a_dele_e_tem_o_seu(self):
        """Quem o escreve aí é o `build._gerar`, como sempre."""
        from riftvault import build
        self.cfg({"multi": {"aberto": False}})
        con = self.catalogo()
        con.close()
        fora = self.v.root / "site-um"
        build.build_todos(fora, log=lambda *_: None)
        self.assertTrue((fora / ".nojekyll").exists())

    def test_o_limpar_raiz_nao_lhe_toca(self):
        """É uma lista ESCRITA: na raiz há coisas que não são nossas para
        apagar (o CNAME do domínio, o `img/` de uma corrida local)."""
        from riftvault import lista
        self.assertNotIn(".nojekyll", lista.RESTOS_DA_RAIZ)
        self.assertNotIn("CNAME", lista.RESTOS_DA_RAIZ)

    def test_quem_o_escreve_e_o_escrever_da_lista(self):
        fonte = (REPO / "riftvault" / "lista.py").read_text(encoding="utf-8")
        escrever = fonte.split("def escrever(")[1].split("\ndef ")[0]
        self.assertIn(".nojekyll", escrever)


if __name__ == "__main__":
    unittest.main()

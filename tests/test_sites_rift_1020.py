"""As correcções da auditoria dos sites de 2026-10-20 (secção rift).

Pedido do André: *"corrige tudo o que for relacionado com o site baverone.com e
os subsites do mtg e rift e tibia"*. A lista vem do
`ai-pc/work/auditoria-sites-1020/relatorio.md` (R1 a R10, mais o «Extra» que o
supervisor viu no Chrome). Um teste (ou mais) por defeito, escrito ANTES da
correcção e visto a chumbar contra o código de 20/10 de manhã.

Os testes de interface correm as funções VERDADEIRAS do `app.js` no node,
extraídas pelo nome (a lição do `test_mais_ate_ao_alvo`); os do catálogo leem o
`data/selado_catalogo.json` commitado; e os do site geram-no numa pasta
temporária, nunca no `data/` a sério.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

from riftvault import build, collection, db, lista, privacidade, utilizador
from tests import fixture
from tests.fixture import REPO

WEB = REPO / "riftvault" / "web"
JS = (WEB / "app.js").read_text(encoding="utf-8")
HTML = (WEB / "index.html").read_text(encoding="utf-8")
CSS = (WEB / "style.css").read_text(encoding="utf-8")
CATALOGO = json.loads((REPO / "data" / "selado_catalogo.json").read_text(encoding="utf-8"))
NODE = shutil.which("node")


def funcao(nome: str) -> str:
    m = re.search(r"^(?:async )?function " + re.escape(nome) + r"\(", JS, re.M)
    if not m:
        raise AssertionError(f"o app.js não tem a função {nome}")
    i = JS.index("{", m.end())
    nivel = 0
    for j in range(i, len(JS)):
        if JS[j] == "{":
            nivel += 1
        elif JS[j] == "}":
            nivel -= 1
            if nivel == 0:
                return JS[m.start():j + 1]
    raise AssertionError(f"chavetas por fechar em {nome}")


def constante(nome: str) -> str:
    m = re.search(r"^const " + re.escape(nome) + r"\b.*?;\s*$", JS, re.M | re.S)
    if not m:
        raise AssertionError(f"o app.js não tem {nome}")
    return m.group(0)


def node(codigo: str):
    if not NODE:
        raise unittest.SkipTest("sem node nesta máquina")
    r = subprocess.run([NODE, "-e", codigo], capture_output=True, text=True,
                       encoding="utf-8", timeout=60)
    if r.returncode:
        raise AssertionError(r.stderr[-2000:])
    return json.loads(r.stdout)


BASE_JS = (funcao("escapeHTML") + "\n" + funcao("escapeAttr") + "\n"
           + "const TODAS = 'all';\n")


def produto(bid: int) -> dict:
    return next(p for p in CATALOGO["produtos"] if p["blueprint_id"] == bid)


# ---------------------------------------------------------------------------
# R1 · a imagem do 408707 dava 404, e o gerador guardava-a na mesma
# ---------------------------------------------------------------------------

class TestR1Imagem(unittest.TestCase):

    def test_o_408707_tem_a_imagem_actual_do_cardtrader(self):
        """Lida da API a 2026-10-20: o ficheiro passou a chamar-se «radiance»."""
        img = produto(408707)["img"]
        self.assertNotIn("vendetta", img)
        self.assertIn("preview_408707-radiance-nexus-night-promo-booster-radiance.jpg", img)

    def test_a_linha_sem_imagem_cai_para_o_marcador_e_nao_para_um_buraco(self):
        """O `onerror` tirava a imagem e deixava o quadrado vazio."""
        f = funcao("slLinha")
        self.assertNotIn('onerror="this.remove()"', f)
        depois = f.split("onerror", 1)[1] if "onerror" in f else ""
        self.assertIn("semimg", depois)
        self.assertRegex(f, r"semImg = `<span class=\"sl-semimg\">")


class TestR1Gerador(unittest.TestCase):
    """O `selado.sincronizar` verifica cada imagem e guarda `null` (o marcador)
    quando ela não responde 200 — nunca se fala com a rede aqui."""

    def setUp(self):
        fixture.config_decks_sem_alt_art(self)
        self.v = fixture.Vault()
        self.addCleanup(self.v.close)
        from riftvault import selado
        self.selado = selado

    def ct(self):
        class CTFalso:
            def get(self, path, params=None):
                if path == "/categories":
                    return [{"id": 259, "name": "Riftbound Booster Boxes", "game_id": 22}]
                return {}

            def expansions(self):
                return [{"id": 1, "code": "zzz", "name": "Zeta"}]

            def blueprints(self, expansion_id):
                return [{"id": 77, "name": "Zeta Booster Box", "category_id": 259,
                         "image_url": "https://x/boa.jpg"},
                        {"id": 78, "name": "Zeta Bundle", "category_id": 259,
                         "image_url": "https://x/morta.jpg"}]
        return CTFalso()

    def test_uma_imagem_que_nao_responde_200_nao_se_guarda(self):
        pedidos = []

        def sonda(url):
            pedidos.append(url)
            return 404 if "morta" in url else 200

        self.selado.sincronizar(ct=self.ct(), log=lambda *a: None, intervalo=0,
                                com_precos=False, sonda_imagem=sonda)
        self.selado._cache = None
        por = {p["blueprint_id"]: p for p in self.selado.carregar()["produtos"]}
        self.assertEqual(por[77]["img"], "https://x/boa.jpg")
        self.assertIsNone(por[78]["img"], "um 404 não se guarda")
        self.assertEqual(por[78].get("img_falhou"), "https://x/morta.jpg")
        self.assertEqual(sorted(pedidos), ["https://x/boa.jpg", "https://x/morta.jpg"])


# ---------------------------------------------------------------------------
# R2 · o nome dizia Vendetta e o CardTrader diz Radiance
# ---------------------------------------------------------------------------

class TestR2Nome(unittest.TestCase):

    def test_o_408707_e_o_da_radiance(self):
        """A API a 2026-10-20: expansão 4522 (RAD), nome «Radiance | …»,
        `card_market_ids` [917622]. O link estava certo; o catálogo é que
        estava velho."""
        p = produto(408707)
        self.assertEqual(p["nome"], "Radiance | Nexus Night Promo Booster")
        self.assertEqual(p["edicao"], "RAD")
        self.assertEqual(p["edicao_nome"], "Radiance")
        self.assertEqual(p["cardmarket_id"], 917622)

    def test_nenhum_produto_tem_o_nome_de_outra_edicao_a_frente(self):
        """«Edição | produto» com uma edição que não é a da expansão. As três
        da API que não batem à letra não são erro (o OGN vive nas «Promos» do
        CardTrader, e os T1 escrevem a edição por extenso)."""
        nomes = {e["code"]: e["name"] for e in CATALOGO["expansoes"]}
        conhecidos = set(nomes.values())
        maus = []
        for p in CATALOGO["produtos"]:
            pref = p["nome"].split(" | ")[0] if " | " in p["nome"] else None
            if p["edicao"] == "PROMO-RIFT":      # as «Promos» de todas as edições
                continue
            if pref in conhecidos and pref != nomes.get(p["edicao"]):
                maus.append((p["blueprint_id"], p["nome"], p["edicao"]))
        self.assertEqual(maus, [])


# ---------------------------------------------------------------------------
# R3 · a faixa mandava correr o riftvault serve no PC
# ---------------------------------------------------------------------------

class TestR3Faixa(unittest.TestCase):

    def faixa(self, dono, servidor=False):
        return node(BASE_JS + funcao("faixaPublicada")
                    + f"\nconsole.log(JSON.stringify(faixaPublicada({json.dumps(dono)}, {json.dumps(servidor)})));")

    def test_o_html_nao_tem_instrucoes_do_pc(self):
        self.assertNotIn("riftvault serve", HTML)

    def test_na_colecao_de_um_amigo_diz_de_quem_e_e_onde_se_edita(self):
        t = self.faixa({"slug": "miguel", "nome": "Miguel Valente", "andre": False})
        self.assertIn("Miguel Valente", t)
        self.assertIn("https://editar.baverone.com", t)
        self.assertNotIn("riftvault serve", t)

    def test_na_dele_tambem_aponta_ao_editar(self):
        t = self.faixa({"slug": "baverone", "nome": "André", "andre": True})
        self.assertIn("https://editar.baverone.com", t)
        self.assertNotIn("riftvault serve", t)

    def test_um_indice_sem_dono_nao_rebenta(self):
        t = self.faixa(None)
        self.assertIn("https://editar.baverone.com", t)


# ---------------------------------------------------------------------------
# R4 e R5 · os textos falavam do André na coleção de outra pessoa
# ---------------------------------------------------------------------------

class TestR4R5Textos(unittest.TestCase):

    def test_nenhum_sub_ro_fala_na_terceira_pessoa(self):
        for m in re.finditer(r"sub_ro:\s*((?:'[^']*'\s*\+?\s*)+)", JS):
            self.assertNotRegex(m.group(1), r"\bele\b|\bdele\b", m.group(1)[:80])

    def test_o_selado_nao_diz_dele(self):
        self.assertNotIn("selado dele", funcao("renderSelado"))

    def test_o_contador_das_runas_nao_e_dele(self):
        self.assertNotIn("é o contador dele", JS)

    def test_a_venda_so_de_leitura_nao_diz_metido_por_ti(self):
        """O cabeçalho da Venda dizia «metido por ti» também na cópia
        publicada; o `sub_ro` já dizia «metido à mão»."""
        f = funcao("renderVenda")
        self.assertNotIn("Trend do Cardmarket, metido por ti</span>", f)

    def quem(self, dono):
        return node(BASE_JS + "const state = { index: { dono: " + json.dumps(dono) + " } };\n"
                    + funcao("donoEAndre") + "\n" + funcao("quemTirou")
                    + "\nconsole.log(JSON.stringify(quemTirou()));")

    def test_as_exclusoes_sao_por_ti_so_na_colecao_do_andre(self):
        self.assertIn("por ti", self.quem({"slug": "baverone", "nome": "André", "andre": True}))

    def test_na_de_um_amigo_as_exclusoes_dizem_que_sao_do_site(self):
        t = self.quem({"slug": "miguel", "nome": "Miguel", "andre": False})
        self.assertNotIn("por ti", t)
        self.assertNotIn("tiraste", t)
        self.assertIn("todas as coleções", t)

    def test_o_cabecalho_do_selado_usa_o_quem_tirou(self):
        f = funcao("renderSelado")
        self.assertNotIn("produtos tirados'}\n      por ti", f)
        self.assertIn("quemTirou()", f)
        self.assertNotIn("<b>tiraste</b>", funcao("slForaTexto"))


class TestDonoNoIndice(unittest.TestCase):
    """O índice publicado diz de quem é a coleção — é daí que a faixa e os
    textos sabem. E a coleção de cada um aponta para a lista (R7)."""

    def setUp(self):
        fixture.config_decks_sem_alt_art(self)
        self.v = fixture.Vault()
        self.addCleanup(self.v.close)
        con = self.v.connect()
        self.v.add_printing(con, "tst-001-100", "TST", 1, "Defy")
        self.v.rebuild(con)
        collection.adjust(con, "tst-001-100", 3, source="test")
        con.close()
        privacidade.definir(None, utilizador.ANDRE, "tudo")
        u = utilizador.criar("Miguel Valente", "miguel")
        con = db.connect(user_id=u["user_id"])
        collection.adjust(con, "tst-001-100", 1, source="test")
        con.close()
        privacidade.definir(None, u["user_id"], "tudo")
        self.out = self.v.root / "site"
        build.build_todos(self.out, log=lambda *_: None, cfg={"multi": {"aberto": True}})

    def indice(self, slug):
        return json.loads((self.out / "u" / slug / "api" / "index.json")
                          .read_text(encoding="utf-8"))

    def test_o_indice_de_um_amigo_diz_quem_e(self):
        d = self.indice("miguel")["dono"]
        self.assertEqual(d, {"slug": "miguel", "nome": "Miguel Valente", "andre": False})

    def test_o_dele_diz_que_e_ele(self):
        self.assertTrue(self.indice("baverone")["dono"]["andre"])

    def test_cada_colecao_sabe_onde_esta_a_lista(self):
        self.assertEqual(self.indice("miguel")["lista"], "../../")
        self.assertEqual(self.indice("baverone")["lista"], "../../")

    def test_r6_a_lista_tem_caminho_para_baverone(self):
        raiz = (self.out / "index.html").read_text(encoding="utf-8")
        self.assertIn('href="https://baverone.com"', raiz)


# ---------------------------------------------------------------------------
# R6 e R7 · os caminhos entre a lista, as coleções e baverone.com
# ---------------------------------------------------------------------------

class TestR7LinkParaALista(unittest.TestCase):

    def test_o_html_tem_o_sitio_do_link_e_o_app_preenche_o(self):
        self.assertIn('id="link-lista"', HTML)
        self.assertIn("link-lista", JS)
        self.assertIn("state.index.lista", JS)

    def test_r6_o_html_da_lista_leva_o_link(self):
        dados = {"coleccoes": [], "dele": None, "gerado_em": "x"}
        try:
            h = lista.html(dados)
        except Exception:
            h = lista.html({**dados, "dele": {"slug": "baverone", "caminho": "u/baverone/"}})
        self.assertIn('href="https://baverone.com"', h)


# ---------------------------------------------------------------------------
# R8 · a pesquisa do Selado com o estilo do tema
# ---------------------------------------------------------------------------

class TestR8Pesquisa(unittest.TestCase):

    def regra(self, seletor):
        for m in re.finditer(r"([^{}]+)\{([^}]*)\}", CSS):
            if seletor in [s.strip() for s in m.group(1).split(",")]:
                return m.group(2)
        return ""

    def test_as_tres_pesquisas_tem_fundo_e_cor_do_tema(self):
        for sel in ("#search", "#enc-search", '#sl-filtros input[type="search"]'):
            r = self.regra(sel)
            self.assertIn("background", r, sel)
            self.assertIn("color", r, sel)
            self.assertIn("border", r, sel)


# ---------------------------------------------------------------------------
# R9 · «#wl-edicao» num separador novo abria a última secção guardada
# ---------------------------------------------------------------------------

class TestR9Ancoras(unittest.TestCase):

    def seccao(self, nome):
        return node(constante("ANCORAS") + "\n" + funcao("seccaoDaAncora")
                    + f"\nconsole.log(JSON.stringify(seccaoDaAncora({json.dumps(nome)})));")

    def test_wl_edicao_e_da_colecao(self):
        self.assertEqual(self.seccao("wl-edicao"), "colecao")
        self.assertEqual(self.seccao("wl-tudo"), "colecao")

    def test_uma_rota_nao_e_ancora(self):
        self.assertIsNone(self.seccao("venda"))

    def test_todas_as_ancoras_do_app_sao_rotas_ou_estao_na_tabela(self):
        seccoes = set(re.search(r"const SECCOES = \[([^\]]*)\]", JS).group(1)
                      .replace("'", "").replace(" ", "").split(","))
        tabela = set(re.findall(r"'([a-z-]+)':", constante("ANCORAS")))
        for h in re.findall(r'href="#([a-z][a-z-]*)"', JS):
            self.assertTrue(h in seccoes or h in tabela, h)

    def test_o_arranque_e_o_hashchange_usam_a_tabela(self):
        self.assertIn("seccaoDaAncora", funcao("boot"))


# ---------------------------------------------------------------------------
# R10 · rótulos acessíveis
# ---------------------------------------------------------------------------

class TestR10Rotulos(unittest.TestCase):

    def test_as_pesquisas_do_html_tem_rotulo(self):
        for i in ("search", "enc-search"):
            m = re.search(r'<input id="' + i + r'"[^>]*>', HTML)
            self.assertIn("aria-label=", m.group(0), i)

    def test_a_pesquisa_do_selado_tem_rotulo(self):
        m = re.search(r'<input id="sl-q"[^>]*>', JS, re.S)
        self.assertIn("aria-label=", m.group(0))

    def test_as_caixas_das_listas_tem_rotulo(self):
        caixas = re.findall(r"<textarea[^>]*>", JS)
        self.assertGreaterEqual(len(caixas), 5)
        for c in caixas:
            self.assertIn("aria-label=", c, c)


# ---------------------------------------------------------------------------
# Extra · quem chega pela primeira vez vê «Todas»
# ---------------------------------------------------------------------------

class TestExtraEdicaoInicial(unittest.TestCase):

    SETS = [{"id": "OGN"}, {"id": "SFD"}, {"id": "RAD"}]

    def inicial(self, guardada, sets=None):
        return node("const TODAS = 'all';\n" + funcao("edicaoInicial")
                    + f"\nconsole.log(JSON.stringify(edicaoInicial({json.dumps(guardada)}, "
                    + json.dumps(sets if sets is not None else self.SETS) + ")));")

    def test_sem_escolha_guardada_abre_em_todas(self):
        self.assertEqual(self.inicial(None), "all")

    def test_a_escolha_guardada_continua_a_valer(self):
        self.assertEqual(self.inicial("RAD"), "RAD")
        self.assertEqual(self.inicial("all"), "all")

    def test_uma_escolha_que_ja_nao_existe_abre_em_todas(self):
        self.assertEqual(self.inicial("XXX"), "all")

    def test_com_uma_edicao_so_abre_nela(self):
        self.assertEqual(self.inicial(None, [{"id": "OGN"}]), "OGN")

    def test_o_arranque_usa_a_funcao(self):
        self.assertIn("edicaoInicial(", funcao("boot"))


if __name__ == "__main__":
    unittest.main()

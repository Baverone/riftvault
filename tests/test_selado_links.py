"""Os links de compra do «Produto Selado» (André, 2026-09-25).

Palavras dele: *"Se possivel, mete link para compra no cardmarket e no
cardtrader"*.

O que se fixa:
  1. cada linha leva DOIS links, um por mercado, e cada um diz se é a página
     do produto ou uma PESQUISA;
  2. com id → link directo; sem id → pesquisa pelo nome, nunca um endereço
     montado com um id que não existe;
  3. os templates vêm do bloco `mercados` do config — um só para os dois
     separadores —, e um config escrito antes de hoje (com as duas chaves no
     `venda`) continua a valer;
  4. um template sem `{id}`/`{q}` rebenta;
  5. a Venda continua a dar os mesmos dois links de sempre, agora por esta
     porta;
  6. o `payload.links` conta quantos são directos e quantos são pesquisa;
  7. isto NÃO mexe em número nenhum da Coleção (a mesma fotografia do
     `test_selado`, por referência);
  8. a página: os dois `<a>`, o `target="_blank"`, o `rel` com `noopener`, o
     CSS que os deixa caber a 375 px, e o config real.

Contra pastas temporárias e config temporário; **não se fala com a rede**.
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests import test_selado as _sel  # noqa: E402
from tests.test_selado import APP_JS, CSS, Base  # noqa: E402

REPO = Path(__file__).resolve().parent.parent


class TestOsLinksDeCadaLinha(Base):

    def lista(self, **kw):
        if kw:
            self.cfg_selado(kw)
        return {x["id"]: x for x in self.selado.itens(self.con())}

    def test_cada_linha_leva_os_dois_mercados(self):
        for x in self.lista().values():
            self.assertIn("cardmarket", x["links"], x["nome"])
            self.assertIn("cardtrader", x["links"], x["nome"])
            for l in x["links"].values():
                self.assertTrue(l["url"].startswith("https://"), x["nome"])
                self.assertIn("pesquisa", l)

    def test_com_id_vai_directo(self):
        x = self.lista()["ct-101"]           # tem cardmarket_id 900001
        self.assertEqual(x["links"]["cardmarket"],
                         {"url": "https://www.cardmarket.com/en/Riftbound/Products"
                                 "?idProduct=900001", "pesquisa": False})
        self.assertEqual(x["links"]["cardtrader"],
                         {"url": "https://www.cardtrader.com/en/cards/101",
                          "pesquisa": False})

    def test_sem_cardmarket_id_cai_na_pesquisa_so_nesse_mercado(self):
        x = self.lista()["ct-105"]           # Teste Vault, sem cardmarket_id
        self.assertTrue(x["links"]["cardmarket"]["pesquisa"])
        self.assertIn("searchString=Teste%20Vault", x["links"]["cardmarket"]["url"])
        # O CardTrader tem-no: continua directo.
        self.assertFalse(x["links"]["cardtrader"]["pesquisa"])
        self.assertTrue(x["links"]["cardtrader"]["url"].endswith("/cards/105"))

    def test_o_produto_do_config_leva_pesquisa_nos_dois(self):
        """Os 17 do `selado.extra` não existem em mercado nenhum como linha —
        é por isso que estão escritos à mão."""
        self.cfg_selado({"extra": [{"nome": "Teste Vault Bundle Case",
                                    "edicao": "TST", "tipo": "case"}]})
        x = [i for i in self.selado.itens(self.con()) if i["fonte"] == "config"][0]
        self.assertIsNone(x["blueprint_id"])
        self.assertTrue(x["links"]["cardmarket"]["pesquisa"])
        self.assertTrue(x["links"]["cardtrader"]["pesquisa"])
        self.assertIn("q=Teste%20Vault%20Bundle%20Case", x["links"]["cardtrader"]["url"])

    def test_nunca_se_monta_um_link_com_um_id_que_nao_existe(self):
        for x in self.lista().values():
            cm, ct = x["links"]["cardmarket"], x["links"]["cardtrader"]
            self.assertEqual(bool(x["cardmarket_id"]), not cm["pesquisa"], x["nome"])
            self.assertEqual(bool(x["blueprint_id"]), not ct["pesquisa"], x["nome"])
            if cm["pesquisa"]:
                self.assertNotIn("idProduct", cm["url"], x["nome"])
            if ct["pesquisa"]:
                self.assertNotIn("/cards/", ct["url"], x["nome"])

    def test_a_versao_entra_no_termo_de_pesquisa(self):
        x = self.lista()["ct-102"]           # «Teste Booster Box Case» + «x6 Booster Boxes»
        self.assertIn(quote("Teste Booster Box Case x6 Booster Boxes", safe=""),
                      x["links"]["cardmarket"]["url"])

    def test_as_aspas_saem_do_termo_de_pesquisa(self):
        """`Teste: "Jinx" Champion Deck` — as aspas são a convenção do nome e
        numa caixa de pesquisa lêem-se como «frase exacta»."""
        x = self.lista()["ct-104"]
        self.assertNotIn("%22", x["links"]["cardmarket"]["url"])
        self.assertIn("Jinx", x["links"]["cardmarket"]["url"])

    def test_o_termo_vai_codificado(self):
        for x in self.lista().values():
            for l in x["links"].values():
                self.assertNotIn(" ", l["url"], x["nome"])

    def test_os_acessorios_tambem_levam_links(self):
        self.cfg_selado({"acessorios": [264, 266]})
        acess = [x for x in self.selado.itens(self.con()) if x["acessorio"]]
        self.assertTrue(acess)
        for x in acess:
            self.assertFalse(x["links"]["cardtrader"]["pesquisa"], x["nome"])

    def test_ler_os_links_nao_escreve(self):
        con = self.catalogo()
        antes = con.execute("SELECT COUNT(*) AS n FROM ops").fetchone()["n"]
        self.selado.payload(con)
        self.assertEqual(con.execute("SELECT COUNT(*) AS n FROM ops").fetchone()["n"],
                         antes)


class TestOsTemplatesVemDoConfig(Base):

    def com(self, mercados: dict, venda: dict | None = None):
        extra = {"mercados": mercados}
        if venda is not None:
            extra["venda"] = venda
        self.cfg_selado({}, extra)
        return {x["id"]: x for x in self.selado.itens(self.con())}

    def test_a_chave_manda(self):
        x = self.com({"cardmarket_url_selado": "https://exemplo/cm/{id}",
                      "cardtrader_url": "https://exemplo/ct/{id}"})["ct-101"]
        self.assertEqual(x["links"]["cardmarket"]["url"], "https://exemplo/cm/900001")
        self.assertEqual(x["links"]["cardtrader"]["url"], "https://exemplo/ct/101")

    def test_a_pesquisa_tambem(self):
        x = self.com({"cardtrader_busca": "https://exemplo/procurar?t={q}"})["ct-105"]
        self.assertTrue(x["links"]["cardmarket"]["pesquisa"])
        x = self.com({"cardtrader_busca": "https://exemplo/procurar?t={q}"})
        cfg_x = [i for i in x.values() if not i["blueprint_id"]]
        self.assertFalse(cfg_x)      # sem `extra`, todos têm blueprint

    def test_o_selado_tem_template_proprio_e_nao_e_o_das_cartas(self):
        """Um display não é um «Single» — se fossem a mesma chave, mudar uma
        mudava a outra."""
        from riftvault import mercados
        op = mercados.opcoes(self.config.load())
        self.assertNotEqual(op["cardmarket_url"], op["cardmarket_url_selado"])
        self.assertNotIn("Singles", op["cardmarket_url_selado"])

    def test_um_template_sem_o_campo_rebenta(self):
        from riftvault import mercados
        for chave, mau in (("cardmarket_url", "https://exemplo/sem-campo"),
                           ("cardtrader_url", "https://exemplo/{q}"),
                           ("cardmarket_busca", "https://exemplo/{id}"),
                           ("cardtrader_busca", "https://exemplo/nada")):
            with self.assertRaises(ValueError) as e:
                mercados.opcoes({"mercados": {chave: mau}})
            self.assertIn(chave, str(e.exception))

    def test_um_config_antigo_com_as_chaves_no_venda_continua_a_valer(self):
        """Viveram no bloco `venda` desde a tarde de 2026-09-25. Movê-las não
        pode partir um config que ele já tinha escrito."""
        from riftvault import mercados
        op = mercados.opcoes({"venda": {"cardmarket_url": "https://velho/{id}",
                                        "cardmarket_busca": "https://velho/q={q}"}})
        self.assertEqual(op["cardmarket_url"], "https://velho/{id}")
        self.assertEqual(op["cardmarket_busca"], "https://velho/q={q}")
        # As do CardTrader vêm dos defaults, como tem de ser.
        self.assertIn("cardtrader.com", op["cardtrader_url"])

    def test_com_as_duas_escritas_ganha_a_nova(self):
        from riftvault import mercados
        op = mercados.opcoes({"venda": {"cardmarket_url": "https://velho/{id}"},
                              "mercados": {"cardmarket_url": "https://novo/{id}"}})
        self.assertEqual(op["cardmarket_url"], "https://novo/{id}")

    def test_sem_bloco_nenhum_sao_os_defaults(self):
        from riftvault import mercados
        self.assertEqual(mercados.opcoes({}), mercados.DEFAULTS)


class TestAVendaContinuaIgual(Base):
    """Os links da Venda mudaram de casa, não de forma."""

    def carta(self):
        con = self.catalogo()
        con.execute("INSERT INTO catalog.cardtrader_map "
                    "(printing_id, blueprint_id, cardmarket_id, market_name, market_set) "
                    "VALUES (?,?,?,?,?)",
                    ("tst-002-100", 4242, 845712, "Brutalizer", "Teste"))
        return con

    def test_a_carta_com_id_vai_directo(self):
        con = self.carta()
        self.venda.juntar(con, "TST-002", 1, source="test")
        x = self.venda.itens(con)[0]
        self.assertIn("Products/Singles?idProduct=845712", x["url"])
        self.assertIn("searchString=Brutalizer", x["url_busca"])

    def test_a_carta_sem_id_cai_na_pesquisa(self):
        con = self.catalogo()
        self.venda.juntar(con, "TST-001", 1, source="test")
        x = self.venda.itens(con)[0]
        self.assertIsNone(x["cardmarket_id"])
        self.assertIn("searchString=Defy", x["url"])

    def test_o_template_antigo_no_bloco_venda_ainda_manda(self):
        con = self.carta()
        self.cfg_selado({}, {"venda": {"trend_valido_dias": 7,
                                       "cardmarket_url": "https://exemplo/{id}"}})
        self.venda.juntar(con, "TST-002", 1, source="test")
        self.assertEqual(self.venda.itens(con)[0]["url"], "https://exemplo/845712")


class TestOPayloadConta(Base):

    def test_diz_quantos_sao_directos_e_quantos_pesquisa(self):
        p = self.selado.payload(self.con())
        L = p["links"]
        n = len([x for x in p["items"] if not x["acessorio"]])
        self.assertEqual(L["cardmarket"]["directos"] + L["cardmarket"]["pesquisa"], n)
        self.assertEqual(L["cardtrader"]["directos"], n)   # todos têm blueprint
        self.assertEqual(L["cardmarket"]["directos"], 1)   # só o ct-101 tem id

    def test_diz_o_que_esta_validado_e_o_que_nao(self):
        """O do CardTrader foi medido (200 com o id sozinho, 404 num id
        inventado); o do Cardmarket não pôde ser (403). A página escreve a
        diferença, por isso o payload tem de a trazer."""
        L = self.selado.payload(self.con())["links"]
        self.assertTrue(L["cardtrader"]["validado"])
        self.assertFalse(L["cardmarket"]["validado"])

    def test_os_acessorios_contam_a_parte(self):
        self.cfg_selado({"acessorios": [264, 266]})
        p = self.selado.payload(self.con())
        self.assertEqual(p["acessorios"]["links"]["cardtrader"]["directos"],
                         len([x for x in p["items"] if x["acessorio"]]))


class TestNaoMexeNaColecao(Base):
    """A defesa de sempre: um link não pode mexer num número da Coleção."""

    fotografia = _sel.TestNaoEntraNaColecao.fotografia

    def test_nada_mexe(self):
        con = self.catalogo()
        antes = json.dumps(self.fotografia(con), sort_keys=True, default=str)
        p = self.selado.payload(con)
        self.assertTrue(p["items"][0]["links"]["cardtrader"]["url"])
        self.cfg_selado({}, {"mercados": {"cardtrader_url": "https://outro/{id}"}})
        self.selado.payload(con)
        self.assertEqual(
            json.dumps(self.fotografia(con), sort_keys=True, default=str), antes,
            "os links mexeram num número da Coleção")

    def test_a_fotografia_nao_e_de_zeros(self):
        f = self.fotografia(self.catalogo())
        self.assertGreater(f["valor"]["cents"], 0)
        self.assertTrue(f["grelha"])

    def test_nenhum_modulo_de_contas_monta_links_de_mercado(self):
        """O `mercados` é das PÁGINAS (selado e venda). Se um módulo de contas
        o importar, é sinal de que um link entrou numa conta."""
        for nome in ("a_mais", "faltas", "faltas_edicao", "uso_decks", "decks",
                     "locais", "pending", "painel", "foil", "metrics", "proprias",
                     "collection"):
            fonte = (REPO / "riftvault" / f"{nome}.py").read_text(encoding="utf-8")
            self.assertNotIn("import mercados", fonte, nome)


class TestOConfigReal(unittest.TestCase):
    """O `riftvault_config.json` a sério — lido, nunca escrito."""

    def setUp(self):
        self.cfg = json.loads((REPO / "riftvault_config.json").read_text(encoding="utf-8"))

    def test_o_bloco_mercados_existe_e_tem_os_cinco(self):
        m = self.cfg["mercados"]
        for k in ("cardmarket_url", "cardmarket_url_selado", "cardmarket_busca",
                  "cardtrader_url", "cardtrader_busca"):
            self.assertIn(k, m)

    def test_o_do_cardtrader_e_o_validado(self):
        """`/en/cards/<id>` — o `/en/` faz falta: sem ele a página abre em
        italiano (medido a 2026-09-25)."""
        self.assertEqual(self.cfg["mercados"]["cardtrader_url"],
                         "https://www.cardtrader.com/en/cards/{id}")
        self.assertIn("/en/search?q={q}", self.cfg["mercados"]["cardtrader_busca"])

    def test_o_venda_ja_nao_tem_os_links(self):
        self.assertEqual(set(self.cfg["venda"]), {"trend_valido_dias"})

    def test_a_nota_diz_o_que_esta_validado_e_o_que_nao(self):
        nota = self.cfg["_mercados_nota"]
        self.assertIn("403", nota)
        self.assertIn("VALIDADO", nota)

    def test_o_default_do_a_subir_tambem_leva_o_en(self):
        from riftvault import a_subir
        self.assertEqual(a_subir.DEFAULTS["link_cardtrader"],
                         "https://www.cardtrader.com/en/cards/{blueprint_id}")


class TestAPagina(unittest.TestCase):

    def setUp(self):
        self.js = APP_JS.read_text(encoding="utf-8")
        self.css = CSS.read_text(encoding="utf-8")

    def test_a_linha_desenha_os_dois_links(self):
        self.assertIn("slLinks", self.js)
        i = self.js.index("function slLinks(x)")
        troco = self.js[i:i + 1200]
        self.assertIn("Cardmarket", troco)
        self.assertIn("CardTrader", troco)

    def test_abrem_em_separador_novo_e_com_noopener(self):
        i = self.js.index("function slLinks(x)")
        troco = self.js[i:i + 1200]
        self.assertIn('target="_blank"', troco)
        self.assertIn("noopener", troco)

    def test_o_que_e_pesquisa_diz_que_e(self):
        i = self.js.index("function slLinks(x)")
        troco = self.js[i:i + 1200]
        self.assertIn("pesquisa", troco)
        self.assertIn("procurar", troco)

    def test_o_endereco_nao_se_monta_no_cliente(self):
        """Os templates são do config e vêm no payload — montar o URL no
        JavaScript era uma segunda resposta à mesma pergunta."""
        i = self.js.index("function slLinks(x)")
        troco = self.js[i:i + 1200]
        self.assertNotIn("cardmarket.com", troco)
        self.assertNotIn("cardtrader.com", troco)

    def test_o_cabecalho_diz_quantos_sao_pesquisa(self):
        self.assertIn("slLinksNota", self.js)
        i = self.js.index("function slLinksNota")
        self.assertIn("403", self.js[i:i + 900])

    def test_o_css_deixa_os_links_caber_no_telemovel(self):
        i = self.css.index(".sl-links {")
        troco = self.css[i:i + 400]
        self.assertIn("flex-wrap: wrap", troco)
        self.assertIn("font-size: 12px", troco)

    def test_o_alvo_do_dedo_tem_altura(self):
        i = self.css.index(".sl-links a {")
        self.assertIn("min-height: 28px", self.css[i:i + 200])

    def test_a_ajuda_explica_a_diferenca_entre_os_dois(self):
        i = self.js.index("'selado': {")
        troco = self.js[i:i + 4000]
        self.assertIn("link de compra", troco)
        self.assertIn("403", troco)


if __name__ == "__main__":
    unittest.main()

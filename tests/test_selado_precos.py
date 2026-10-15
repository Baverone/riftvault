"""O selado a 2026-10-13: fora os Vault (por PADRÃO), e o preço guardado
todos os dias, com a variação a separar o PREÇO do INVENTÁRIO.

Palavras dele: *"nao quero Vault"*. E a ordem: o `--sync` reescrevia o
`data/selado_catalogo.json` e o preço de ontem perdia-se — os blueprints do
selado tinham ZERO linhas de histórico.

O que se fixa:
  1. `selado.excluidos_padrao`: um padrão tira o que existe E o que o próximo
     `--sync` trouxer; casa com o nome INTEIRO (ou a versão), nunca um pedaço;
     um padrão que não apanhe nada REBENTA, com os parecidos — a regra dos
     nomes; e os Bundles que ele tem ficam (a categoria 261 não se tirou);
  2. `prices.sealed_price_history`: uma linha por blueprint e por dia, no dia
     que o catálogo diz, com os três números da oferta; o backfill nunca
     escreve por cima; é uma tabela À PARTE do `price_history` das cartas; e
     não toca na Coleção;
  3. a variação: por janela, só com referência dentro da folga (nunca se chama
     «semana» a quinze dias); é o preço de UMA unidade; e o efeito do PREÇO no
     que ele tem não muda quando ele compra — o inventário diz-se à parte.

Contra pastas temporárias e um config temporário, como o `test_selado`.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.fixture import SEM_CONFIG  # noqa: E402

from tests.fixture import REPO  # noqa: E402
from tests.test_selado import CATALOGO, Base, TestNaoEntraNaColecao  # noqa: E402

APP_JS = (REPO / "riftvault" / "web" / "app.js").read_text(encoding="utf-8")
CSS = (REPO / "riftvault" / "web" / "style.css").read_text(encoding="utf-8")
CONFIG_REAL = json.loads((REPO / "riftvault_config.json").read_text(encoding="utf-8"))


def catalogo_com(*produtos, precos=None, dia=None, quando=None):
    """O catálogo de brincar com produtos a mais e/ou preços de outro dia."""
    c = json.loads(json.dumps(CATALOGO))
    c["produtos"] += list(produtos)
    if precos is not None:
        c["precos"] = precos
    if dia is not None:
        for v in c["precos"].values():
            v["day"] = dia
    if quando is not None:
        c["generated_at"] = quando
    return c


def preco(cents, dia, n=5):
    return {"cents": cents, "currency": "EUR", "day": dia,
            "n_listings": n, "n_sellers": n, "n_copies": n * 2}


def produto(bid, nome, cat=261, versao=""):
    return {"blueprint_id": bid, "nome": nome, "versao": versao, "categoria_id": cat,
            "edicao": "TST", "edicao_nome": "Teste", "img": None, "cardmarket_id": None}


# ---------------------------------------------------------------------------
# 1. Os padrões
# ---------------------------------------------------------------------------


class TestOsPadroes(Base):

    def ids(self, cfg=None):
        return {x["id"] for x in self.selado.itens(None, cfg)}

    def test_um_padrao_tira_o_vault(self):
        self.assertIn("ct-105", self.ids())
        self.cfg_selado({"excluidos_padrao": ["*Vault"]})
        self.assertNotIn("ct-105", self.ids())
        ex = self.selado.excluidos()
        self.assertEqual([(x["id"], x["por"]) for x in ex], [("ct-105", "padrão *Vault")])

    def test_o_vault_que_ainda_nao_existe_sai_sozinho(self):
        """É a razão de ser do padrão: o próximo `--sync` traz a «The Reckoning
        Vault» e ninguém a escreve."""
        self.cfg_selado({"excluidos_padrao": ["*Vault"]})
        self.escrever_catalogo(catalogo_com(produto(301, "The Reckoning Vault")))
        self.assertNotIn("ct-301", self.ids())
        self.assertNotIn("ct-105", self.ids())

    def test_casa_o_nome_inteiro_nunca_um_pedaco(self):
        self.cfg_selado({"excluidos_padrao": ["*Vault"]})
        self.escrever_catalogo(catalogo_com(produto(302, "Teste Vault Bundle Case", 263)))
        self.assertIn("ct-302", self.ids())

    def test_sem_maiusculas(self):
        self.cfg_selado({"excluidos_padrao": ["*VAULT"]})
        self.assertNotIn("ct-105", self.ids())

    def test_casa_tambem_a_versao(self):
        """O marcador de língua do CardTrader está muitas vezes na VERSÃO
        («Chinese Exclusive»)."""
        self.cfg_selado({"excluidos_padrao": ["*Chinese*"]})
        self.escrever_catalogo(catalogo_com(
            produto(303, "Teste Promo Pack", 260, versao="Chinese Exclusive")))
        self.assertNotIn("ct-303", self.ids())

    def test_um_padrao_que_nao_apanha_nada_rebenta_com_os_parecidos(self):
        self.cfg_selado({"excluidos_padrao": ["*Valt"]})
        with self.assertRaises(ValueError) as e:
            self.ids()
        self.assertIn("não apanha nenhum produto", str(e.exception))
        self.assertIn("Teste Vault", str(e.exception))

    def test_sem_curinga_e_um_nome_e_rebenta(self):
        self.cfg_selado({"excluidos_padrao": ["Teste Vault"]})
        with self.assertRaises(ValueError) as e:
            self.selado.opcoes()
        self.assertIn("selado.excluidos", str(e.exception))

    def test_um_padrao_largo_demais_rebenta(self):
        for p in ("*", "*a*", "??"):
            self.cfg_selado({"excluidos_padrao": [p]})
            with self.assertRaises(ValueError, msg=p):
                self.selado.opcoes()

    def test_sem_catalogo_nao_rebenta(self):
        """A regra do `tolerante`: sem `--sync` a app não sabe se o padrão
        apanharia alguma coisa."""
        self.cfg_selado({"excluidos_padrao": ["*Vault"]})
        self.escrever_catalogo({**CATALOGO, "produtos": [], "precos": {}})
        self.assertEqual(self.selado.itens(None), [])

    def test_o_nome_ganha_ao_padrao(self):
        self.cfg_selado({"excluidos": ["Teste Vault"], "excluidos_padrao": ["*Vault"]})
        self.assertEqual([x["por"] for x in self.selado.excluidos()], ["nome"])

    def test_sem_padroes_nada_muda(self):
        self.assertEqual(self.selado.DEFAULTS["excluidos_padrao"], [])
        self.assertIn("ct-105", self.ids())

    def test_repor_e_tirar_o_padrao(self):
        self.cfg_selado({"excluidos_padrao": ["*Vault"]})
        self.assertNotIn("ct-105", self.ids())
        self.cfg_selado({"excluidos_padrao": []})
        self.assertIn("ct-105", self.ids())


class TestOConfigReal(unittest.TestCase):
    """A ordem contra o config e o catálogo REAIS (2026-10-13)."""

    @classmethod
    def setUpClass(cls):
        if not (REPO / "data" / "selado_catalogo.json").exists():
            raise unittest.SkipTest("sem catálogo em disco")
        import importlib
        os.environ["RIFTVAULT_CONFIG"] = str(REPO / "riftvault_config.json")
        from riftvault import config, selado
        importlib.reload(config)
        config.load.cache_clear()
        importlib.reload(selado)
        cls.selado = selado
        cls.cat = json.loads((REPO / "data" / "selado_catalogo.json").read_text(encoding="utf-8"))
        cls.nomes = {x["nome"] for x in selado.itens(None, CONFIG_REAL)}

    @classmethod
    def tearDownClass(cls):
        import importlib
        import tempfile
        from riftvault import config
        os.environ["RIFTVAULT_CONFIG"] = SEM_CONFIG
        importlib.reload(config)
        config.load.cache_clear()

    def test_os_quatro_vault_sairam(self):
        for n in ("Unleashed Vault", "Vendetta Vault", "Radiance Vault", "Legacy Vault"):
            self.assertNotIn(n, self.nomes, n)

    def test_sairam_pelo_padrao_e_nao_por_nome(self):
        self.assertIn("*Vault", CONFIG_REAL["selado"]["excluidos_padrao"])
        for n in ("Unleashed Vault", "Vendetta Vault", "Radiance Vault", "Legacy Vault"):
            self.assertNotIn(n, CONFIG_REAL["selado"]["excluidos"], n)

    def test_a_categoria_261_ficou_e_os_bundles_dele_tambem(self):
        self.assertIn(261, CONFIG_REAL["selado"]["categorias"])
        for n in ("Lunar Revel 2026 Bundle", "Riftbound Worlds Bundle 2025",
                  "Gift of the Rift Bundle"):
            self.assertIn(n, self.nomes, n)

    def test_a_reckoning_vault_de_amanha_sai_sozinha(self):
        import importlib
        c = json.loads(json.dumps(self.cat))
        c["produtos"].append({"blueprint_id": 999001, "nome": "The Reckoning Vault",
                              "versao": "", "categoria_id": 261, "edicao": "REC",
                              "edicao_nome": "The Reckoning", "img": None,
                              "cardmarket_id": None})
        caminho = Path(os.environ.get("TMP", ".")) / "rv-selado-reckoning.json"
        caminho.write_text(json.dumps(c), encoding="utf-8")
        self.addCleanup(caminho.unlink)
        os.environ["RIFTVAULT_SELADO"] = str(caminho)
        from riftvault import config
        importlib.reload(config)
        importlib.reload(self.selado)
        try:
            nomes = {x["nome"] for x in self.selado.itens(None, CONFIG_REAL)}
        finally:
            del os.environ["RIFTVAULT_SELADO"]
            importlib.reload(config)
            importlib.reload(self.selado)
        self.assertNotIn("The Reckoning Vault", nomes)
        self.assertIn("The Reckoning Booster Box", nomes)

    def test_a_caixa_chinesa_de_13_10_saiu_pela_regra_da_lingua(self):
        """O `_selado_so_ingles` avisava que um `--sync` trazia um produto com
        marcador sozinho — e trouxe. Hoje sai pelo padrão `*Chinese*`."""
        self.assertIn("*Chinese*", CONFIG_REAL["selado"]["excluidos_padrao"])
        self.assertTrue(all("chinese" not in n.lower() for n in self.nomes))

    def test_a_nota_tem_a_data_e_as_palavras_dele(self):
        nota = CONFIG_REAL["_selado_vault"]
        self.assertIn("2026-10-13", nota)
        self.assertIn("nao quero Vault", nota)


# ---------------------------------------------------------------------------
# 2. O histórico
# ---------------------------------------------------------------------------


class TestOHistorico(Base):

    def linhas(self, con):
        return [dict(r) for r in con.execute(
            "SELECT * FROM prices.sealed_price_history ORDER BY blueprint_id, day")]

    def test_grava_uma_linha_por_blueprint_no_dia_do_catalogo(self):
        con = self.con()
        h = self.selado.gravar_historico(con)
        self.assertEqual(h["linhas"], len(CATALOGO["precos"]))
        self.assertEqual(h["dias"], ["2026-09-25"])     # o dia do catálogo, não hoje
        ls = {r["blueprint_id"]: r for r in self.linhas(con)}
        self.assertEqual(ls[101]["price_cents"], 16064)
        self.assertEqual((ls[101]["n_listings"], ls[101]["n_sellers"], ls[101]["n_copies"]),
                         (51, 30, 80))

    def test_sem_oferta_e_uma_medicao_e_grava_se(self):
        con = self.con()
        h = self.selado.gravar_historico(con)
        self.assertEqual(h["sem_preco"], 1)
        ls = {r["blueprint_id"]: r for r in self.linhas(con)}
        self.assertIsNone(ls[103]["price_cents"])
        self.assertEqual(ls[103]["n_listings"], 0)

    def test_um_segundo_sync_no_mesmo_dia_substitui(self):
        con = self.con()
        self.selado.gravar_historico(con)
        c = catalogo_com()
        c["precos"]["101"]["cents"] = 15000
        self.selado.gravar_historico(con, c)
        ls = [r for r in self.linhas(con) if r["blueprint_id"] == 101]
        self.assertEqual([(r["day"], r["price_cents"]) for r in ls], [("2026-09-25", 15000)])

    def test_o_backfill_nunca_escreve_por_cima(self):
        con = self.con()
        self.selado.gravar_historico(con)
        c = catalogo_com()
        c["precos"]["101"]["cents"] = 1
        h = self.selado.gravar_historico(con, c, fonte="backfill:x", substituir=False)
        self.assertEqual(h["linhas"], 0)
        ls = [r for r in self.linhas(con) if r["blueprint_id"] == 101]
        self.assertEqual(ls[0]["price_cents"], 16064)
        self.assertEqual(ls[0]["fonte"], "sync")

    def test_dias_diferentes_ficam_lado_a_lado(self):
        con = self.con()
        self.selado.gravar_historico(con)
        self.selado.gravar_historico(con, catalogo_com(dia="2026-09-26"))
        dias = [r["day"] for r in self.linhas(con) if r["blueprint_id"] == 101]
        self.assertEqual(dias, ["2026-09-25", "2026-09-26"])

    def test_e_uma_tabela_a_parte_do_price_history_das_cartas(self):
        """O `price_history` é por `printing_id` de CARTA; um blueprint de
        display lá dentro era uma carta que não existe."""
        con = self.catalogo()
        antes = con.execute("SELECT COUNT(*) FROM prices.price_history").fetchone()[0]
        self.selado.gravar_historico(con)
        self.assertEqual(con.execute("SELECT COUNT(*) FROM prices.price_history").fetchone()[0],
                         antes)
        self.assertIsNone(con.execute(
            "SELECT 1 FROM main.sqlite_master WHERE name='sealed_price_history'").fetchone(),
            "o histórico do selado vive no prices.db, não no vault.db")

    def test_um_dia_mal_escrito_rebenta(self):
        con = self.con()
        with self.assertRaises(ValueError):
            self.selado.gravar_historico(con, catalogo_com(dia="13/10/2026"))

    def test_a_cli_guarda_um_catalogo_antigo_como_backfill(self):
        from riftvault import cli
        caminho = self.v.root / "antigo.json"
        caminho.write_text(json.dumps(catalogo_com(dia="2026-09-20")), encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()) as out, \
                contextlib.redirect_stderr(io.StringIO()):
            cli.main(["selado", "--guardar-precos", str(caminho), "--origem", "git:abc"])
        self.assertIn("histórico do selado", out.getvalue())
        con = self.con()
        fontes = {r["fonte"] for r in self.linhas(con)}
        self.assertEqual(fontes, {"backfill:git:abc"})


class TestOHistoricoNaoEntraNaColecao(TestNaoEntraNaColecao):
    """A fotografia do `test_selado`, por referência: gravar o histórico e
    ler a variação não mexe em número nenhum da Coleção."""

    def test_gravar_o_historico_nao_mexe_em_numero_nenhum(self):
        con = self.catalogo()
        antes = self.fotografia(con)
        self.selado.gravar_historico(con)
        self.selado.gravar_historico(con, catalogo_com(dia="2026-09-26"))
        self.selado.payload(con)
        self.assertEqual(self.fotografia(con), antes)


# ---------------------------------------------------------------------------
# 3. A variação
# ---------------------------------------------------------------------------


def serie(*pares):
    return [{"day": d, "price_cents": c, "n_listings": 5, "n_sellers": 5, "n_copies": 10}
            for d, c in pares]


class TestAVariacao(unittest.TestCase):

    def setUp(self):
        from riftvault import selado
        self.selado = selado

    def janela(self, v, nome):
        return next(j for j in v["janelas"] if j["janela"] == nome)

    def test_dia_semana_e_mes_com_referencia(self):
        v = self.selado.variacao(serie(("2026-09-13", 10000), ("2026-10-06", 11000),
                                       ("2026-10-12", 11500), ("2026-10-13", 12000)))
        self.assertEqual(self.janela(v, "dia")["delta_cents"], 500)
        self.assertEqual(self.janela(v, "semana")["delta_cents"], 1000)
        self.assertEqual(self.janela(v, "mes")["delta_cents"], 2000)
        self.assertEqual(self.janela(v, "mes")["pct"], 20.0)
        self.assertEqual(v["desde"]["de_dia"], "2026-09-13")

    def test_fora_da_folga_nao_ha_referencia(self):
        """O caso de 2026-10-13: a medição anterior é de 28/09. Chamar
        «semana» a quinze dias era o gráfico que mente."""
        v = self.selado.variacao(serie(("2026-09-28", 10000), ("2026-10-13", 12000)))
        for nome in ("dia", "semana", "mes"):
            self.assertTrue(self.janela(v, nome).get("falta"), nome)
        self.assertEqual(v["desde"]["delta_cents"], 2000)
        self.assertEqual(v["desde"]["dias"], 15)

    def test_a_folga_aceita_um_dia_falhado(self):
        v = self.selado.variacao(serie(("2026-10-11", 10000), ("2026-10-13", 10100)))
        self.assertEqual(self.janela(v, "dia")["delta_cents"], 100)
        self.assertEqual(self.janela(v, "dia")["de_dia"], "2026-10-11")

    def test_sem_preco_agora_nao_ha_variacao(self):
        v = self.selado.variacao(serie(("2026-10-12", 10000), ("2026-10-13", None)))
        self.assertTrue(self.janela(v, "dia").get("falta"))

    def test_uma_referencia_sem_preco_nao_serve(self):
        v = self.selado.variacao(serie(("2026-10-12", None), ("2026-10-13", 10000)))
        self.assertTrue(self.janela(v, "dia").get("falta"))
        self.assertIsNone(v["desde"])

    def test_sem_serie_nao_ha_nada(self):
        self.assertIsNone(self.selado.variacao([]))


class TestPrecoContraInventario(Base):
    """A diferença entre um gráfico honesto e um que mente: uma COMPRA sobe o
    valor do selado sem nenhum preço ter mexido. As duas coisas não se somam."""

    def ef(self, con, nome):
        p = self.selado.payload(con)
        return next(j for j in p["historico"]["efeito_preco"]["janelas"] if j["janela"] == nome), p

    def dois_dias(self, con, cents_ontem, cents_hoje):
        c1 = catalogo_com(precos={"101": preco(cents_ontem, "2026-10-12")},
                          quando="2026-10-12T10:00:00+00:00")
        c2 = catalogo_com(precos={"101": preco(cents_hoje, "2026-10-13")},
                          quando="2026-10-13T10:00:00+00:00")
        self.selado.gravar_historico(con, c1)
        self.selado.gravar_historico(con, c2)
        self.escrever_catalogo(c2)

    def test_comprar_sobe_o_valor_e_nao_mexe_no_efeito_do_preco(self):
        con = self.con()
        self.dois_dias(con, 16000, 16000)           # o preço NÃO mexeu
        self.selado.ajustar(con, "ct-101", 1, source="test")
        e1, p1 = self.ef(con, "dia")
        self.selado.ajustar(con, "ct-101", 1, source="test")   # compra outro
        e2, p2 = self.ef(con, "dia")
        self.assertGreater(p2["totals"]["valor_cents"], p1["totals"]["valor_cents"])
        self.assertEqual((e1["cents"], e2["cents"]), (0, 0))

    def test_o_preco_a_mexer_conta_com_as_quantidades_de_hoje(self):
        con = self.con()
        self.dois_dias(con, 16000, 16500)
        self.selado.ajustar(con, "ct-101", 3, source="test")
        e, _ = self.ef(con, "dia")
        self.assertEqual(e["cents"], 3 * 500)
        self.assertEqual(e["produtos"], 1)

    def test_a_linha_e_o_preco_de_uma_unidade(self):
        con = self.con()
        self.dois_dias(con, 16000, 16500)
        self.selado.ajustar(con, "ct-101", 3, source="test")
        x = next(i for i in self.selado.payload(con)["items"] if i["id"] == "ct-101")
        dia = next(j for j in x["variacao"]["janelas"] if j["janela"] == "dia")
        self.assertEqual(dia["delta_cents"], 500)

    def test_o_que_tem_sem_referencia_e_contado_e_nao_escondido(self):
        con = self.con()
        self.dois_dias(con, 16000, 16500)
        self.selado.ajustar(con, "ct-101", 1, source="test")
        self.selado.ajustar(con, "ct-102", 1, source="test")   # sem série
        e, p = self.ef(con, "dia")
        self.assertEqual((e["cents"], e["produtos"], e["sem_referencia"]), (500, 1, 1))
        self.assertIn("não se mede", p["historico"]["efeito_preco"]["inventario"])

    def test_sem_historico_a_pagina_diz_que_nao_ha(self):
        con = self.con()
        p = self.selado.payload(con)
        self.assertEqual(p["historico"]["dias"], 0)
        self.assertIn("ainda nenhum dia", self.selado.texto(p))

    def test_uma_ligacao_sem_a_tabela_nao_rebenta(self):
        con = self.con()
        con.execute("DROP TABLE prices.sealed_price_history")
        p = self.selado.payload(con)
        self.assertEqual(p["historico"]["dias"], 0)
        self.assertTrue(all(x["variacao"] is None for x in p["items"]))


class TestAPagina(unittest.TestCase):

    def test_a_linha_mostra_a_variacao(self):
        self.assertIn("slVariacao(x.variacao)", APP_JS)

    def test_o_cabecalho_separa_o_preco_do_inventario(self):
        self.assertIn("slHistoricoNota(p.historico)", APP_JS)
        self.assertIn("só pelo PREÇO", APP_JS)
        self.assertIn("O inventário não entra", APP_JS)

    def test_a_janela_sem_medicao_diz_porque(self):
        self.assertIn("Sem medição entre", APP_JS)

    def test_a_variacao_envolve_e_nao_corre_para_o_lado(self):
        i = CSS.index(".sl-vars")
        bloco = CSS[i:CSS.index("}", i)]
        self.assertIn("flex-wrap: wrap", bloco)
        self.assertNotIn("nowrap", CSS[i:CSS.index(".sl-marcas", i)])

    def test_os_tirados_dizem_por_que_padrao(self):
        self.assertIn("selado.excluidos_padrao", APP_JS)
        self.assertIn("pelo ${escapeHTML(x.por)}", APP_JS)


if __name__ == "__main__":
    unittest.main()

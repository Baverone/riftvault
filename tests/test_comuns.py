"""«O que vender»: as comuns e incomuns caras e o excedente delas.

Pergunta do André (2026-09-10): *"vê no Cardmarket e CardTrader quais as comuns
e incomuns que costumam vender-se mais, e quais as mais caras, para eu saber o
que vender"*.

O que estes testes fixam:

  * **a raridade** — nenhuma rara, épica ou showcase entra, e o tratamento
    showcase de uma comum também não;
  * **o excedente** — nunca toca no que a Coleção ou um deck pedem, e é a mesma
    conta da secção Venda, só com outro âmbito;
  * **a ordem** — «O que vender» sai por euros a receber;
  * **o formato do Cardmarket** — pelo gerador único, tal e qual;
  * **o sync do CardTrader** — contra uma amostra REAL gravada
    (`tests/fixtures/cardtrader-ogs-market.json`, 120 produtos do OGS), sem
    rede nenhuma no teste.
"""

from __future__ import annotations

import importlib
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.fixture import Vault

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "cardtrader-ogs-market.json"


class Base(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.close)
        from riftvault import cardmarket, comuns, metrics, venda
        importlib.reload(metrics)
        importlib.reload(venda)
        importlib.reload(comuns)
        self.comuns, self.venda, self.cardmarket = comuns, venda, cardmarket

    def catalogo(self):
        """Uma comum de playset, uma incomum, uma rara, um token e um showcase.

        Os preços são escolhidos para a mediana das comuns dar 20 cêntimos: é
        contra ela que o sinal de procura se mede.
        """
        con = self.v.connect()
        add = self.v.add_printing
        add(con, "tst-001-100", "TST", 1, "Defy", api_sort=1, rarity="common")
        add(con, "tst-002-100", "TST", 2, "Charm", api_sort=2, rarity="common")
        add(con, "tst-003-100", "TST", 3, "Salvage", api_sort=3, rarity="uncommon")
        add(con, "tst-004-100", "TST", 4, "Nine-Tailed Fox", api_sort=4, rarity="rare")
        add(con, "tst-005-100", "TST", 5, "Lonely Poro", api_sort=5, rarity="common")
        # O caso que obriga a exigir as DUAS raridades: base comum, impressão
        # showcase — são as seis runas de arte alternativa do OGN.
        add(con, "tst-001a-100", "TST", 1, "Defy", variant="a", kind="alt_art",
            api_sort=6, rarity="showcase", base_rarity="common")
        add(con, "tst-t01-100", "TST", 6, "Sprite", variant="t01", kind="token",
            api_sort=7, rarity="common")
        self.v.rebuild(con)
        for pid, cents in (("tst-001-100", 20), ("tst-002-100", 20),
                           ("tst-003-100", 300), ("tst-004-100", 9000),
                           ("tst-005-100", 5000), ("tst-001a-100", 400),
                           ("tst-t01-100", 20)):
            con.execute("INSERT INTO catalog.price_latest (printing_id, price_cents, "
                        "n_listings, n_sellers, n_copies) VALUES (?,?,?,?,?)",
                        (pid, cents, 50, 30, 90))
        return con

    def universo(self, con):
        return {x["printing_id"]: x for x in self.comuns.universo(con)}


# ---------------------------------------------------------------------------


class TestRaridade(Base):
    def test_so_entram_comuns_e_incomuns(self):
        con = self.catalogo()
        u = self.universo(con)
        self.assertIn("tst-001-100", u)                  # common
        self.assertIn("tst-003-100", u)                  # uncommon
        self.assertNotIn("tst-004-100", u)               # rare
        self.assertTrue(all(x["rarity"] in ("common", "uncommon")
                            for x in u.values()))
        con.close()

    def test_o_tratamento_showcase_de_uma_comum_fica_de_fora(self):
        """As DUAS raridades têm de ser comuns: a impressa e a da base.

        A `tst-001a` tem base `common` e impressão `showcase` — é a forma das
        seis runas de arte alternativa do OGN. O mercado paga-lhes preço de
        showcase, e numa lista de cartas de saldo isso responde a outra
        pergunta.
        """
        con = self.catalogo()
        self.assertNotIn("tst-001a-100", self.universo(con))
        con.close()

    def test_nenhuma_lista_leva_raridade_que_nao_seja_dessas(self):
        con = self.catalogo()
        a = self.comuns.analise(con)
        for chave in ("by_price", "by_demand"):
            for x in a[chave]:
                self.assertIn(x["rarity"], a["rarities"], chave)
        for x in a["sell"]["items"] + a["keep"]["items"]:
            self.assertIn(x["rarity"], a["rarities"])
        con.close()

    def test_a_lista_de_raridades_vem_do_config(self):
        con = self.catalogo()
        self.assertEqual(self.comuns.raridades({}), ("common", "uncommon"))
        self.assertEqual(self.comuns.raridades({"comuns": {"raridades": ["rare"]}}),
                         ("rare",))
        cfg = {**self.v.config.load(), "comuns": {"raridades": ["rare"]}}
        u = {x["printing_id"] for x in self.comuns.universo(con, cfg)}
        self.assertEqual(u, {"tst-004-100"})
        con.close()


class TestExcedente(Base):
    """O que a Coleção ou um deck pedem NUNCA aparece como excedente."""

    def test_o_playset_da_colecao_fica__so_a_quarta_copia_sobra(self):
        from riftvault import collection
        con = self.catalogo()
        collection.adjust(con, "tst-001-100", 3, source="test")   # o playset
        self.assertEqual(self.comuns.analise(con)["sell"]["items"], [])

        collection.adjust(con, "tst-001-100", 2, source="test")   # 5 no total
        s = self.comuns.analise(con)["sell"]
        self.assertEqual([(x["code"], x["qty"]) for x in s["items"]],
                         [("TST-001", 2)])
        con.close()

    def test_o_que_um_deck_usa_nao_entra(self):
        from riftvault import collection, decks
        con = self.catalogo()
        collection.adjust(con, "tst-002-100", 6, source="test")
        self.v.write_deck("azir", "Legend:\n1 Nine-Tailed Fox\n\nMainDeck:\n3 Charm\n")
        decks.import_all(con)

        # Tem 6, a coleção pede 3 e o deck usa 3 — `max(3, 3)` = 3, sobram 3.
        s = self.comuns.analise(con)["sell"]
        self.assertEqual([(x["code"], x["qty"]) for x in s["items"]],
                         [("TST-002", 3)])

        # Com o deck a pedir mais do que a coleção, é o deck que manda.
        self.v.write_deck("azir", "Legend:\n1 Nine-Tailed Fox\n\nMainDeck:\n"
                                  "3 Charm\n3 Defy\n")
        decks.import_all(con)
        collection.adjust(con, "tst-001-100", 4, source="test")
        por_id = {x["printing_id"]: x for x in self.comuns.analise(con)["sell"]["items"]}
        self.assertEqual(por_id["tst-001-100"]["qty"], 1)   # 4 - max(3 deck, 3 alvo)
        con.close()

    def test_e_a_mesma_conta_da_seccao_venda__so_muda_o_ambito(self):
        """Um token está fora da Coleção nos dois âmbitos e sobra inteiro."""
        from riftvault import collection
        con = self.catalogo()
        collection.adjust(con, "tst-t01-100", 4, source="test")
        collection.adjust(con, "tst-001-100", 5, source="test")

        fora = {x["printing_id"]: x["qty"]
                for x in self.venda.excedente(con, incluir_master=False)
                if x["qty"] > 0}
        tudo = {x["printing_id"]: x["qty"]
                for x in self.venda.excedente(con, incluir_master=True)
                if x["qty"] > 0}
        self.assertEqual(fora, {"tst-t01-100": 4})
        self.assertEqual(tudo, {"tst-t01-100": 4, "tst-001-100": 2})
        # A secção Venda não mexeu: continua a ser o âmbito estreito.
        self.assertEqual([x["printing_id"] for x in self.venda.listar(con)["items"]],
                         ["tst-t01-100"])
        con.close()

    def test_quem_nao_tem_nada_nao_aparece_para_venda(self):
        con = self.catalogo()
        a = self.comuns.analise(con)
        self.assertEqual(a["sell"]["items"], [])
        self.assertEqual(a["sell"]["cents"], 0)
        # Mas continua nas listas do mercado: a pergunta dele é sobre preços.
        self.assertTrue(a["by_price"])
        con.close()

    def test_nada_sai_da_base(self):
        from riftvault import collection
        con = self.catalogo()
        collection.adjust(con, "tst-001-100", 9, source="test")
        antes = [tuple(r) for r in con.execute(
            "SELECT printing_id, qty FROM copies ORDER BY printing_id")]
        n_ops = con.execute("SELECT COUNT(*) n FROM ops").fetchone()["n"]
        self.comuns.analise(con)
        self.assertEqual([tuple(r) for r in con.execute(
            "SELECT printing_id, qty FROM copies ORDER BY printing_id")], antes)
        self.assertEqual(con.execute("SELECT COUNT(*) n FROM ops").fetchone()["n"],
                         n_ops)
        con.close()


class TestOrdem(Base):
    def test_o_que_vender_sai_por_euros_a_receber(self):
        """Por total (preço × cópias), não pela carta mais cara."""
        from riftvault import collection
        con = self.catalogo()
        collection.adjust(con, "tst-001-100", 13, source="test")   # 10 a 20c = 2,00 €
        collection.adjust(con, "tst-003-100", 4, source="test")    # 1 a 3,00 € = 3,00 €
        itens = self.comuns.analise(con)["sell"]["items"]
        self.assertEqual([(x["code"], x["total"]) for x in itens],
                         [("TST-003", 300), ("TST-001", 200)])
        con.close()

    def test_as_mais_caras_saem_por_preco(self):
        con = self.catalogo()
        precos = [x["price"] for x in self.comuns.analise(con)["by_price"]]
        self.assertEqual(precos, sorted(precos, reverse=True))
        self.assertEqual(self.comuns.analise(con)["by_price"][0]["code"], "TST-005")
        con.close()

    def test_o_topo_corta_as_duas_listas(self):
        con = self.catalogo()
        cfg = {**self.v.config.load(), "comuns": {"topo": 2}}
        a = self.comuns.analise(con, cfg)
        self.assertEqual(len(a["by_price"]), 2)
        self.assertEqual(len(a["by_demand"]), 2)
        con.close()


class TestProcura(Base):
    """O sinal de procura: o que ele é, e o que não é."""

    def test_e_o_preco_a_dividir_pela_mediana_da_raridade(self):
        self.assertEqual(self.comuns.procura(400, 20, None), 20.0)
        self.assertEqual(self.comuns.procura(20, 20, None), 1.0)

    def test_a_subida_do_preco_reforca__a_descida_nao_penaliza(self):
        self.assertAlmostEqual(self.comuns.procura(400, 20, 50.0), 30.0)
        # Uma carta a descer não é MENOS procurada que uma parada: o preço, que
        # é o primeiro factor, já conta a descida.
        self.assertEqual(self.comuns.procura(400, 20, -50.0),
                         self.comuns.procura(400, 20, 0.0))

    def test_a_queda_dos_anuncios_reforca__o_crescimento_nao_penaliza(self):
        """O único factor que fala de movimento — e vale zero sem histórico."""
        self.assertAlmostEqual(self.comuns.procura(400, 20, None, -50.0), 30.0)
        self.assertEqual(self.comuns.procura(400, 20, None, +50.0),
                         self.comuns.procura(400, 20, None, None))

    def test_sem_historico_da_oferta_o_factor_nao_conta(self):
        con = self.catalogo()
        a = self.comuns.analise(con)
        self.assertEqual(a["listings_days"], 0)
        for x in a["by_demand"]:
            self.assertIsNone(x["pct_listings"])
        con.close()

    def test_com_dois_dias_de_oferta_a_queda_ja_conta(self):
        con = self.catalogo()
        con.execute("INSERT INTO prices.listings_history (printing_id, day, "
                    "n_listings, n_sellers, n_copies) VALUES ('tst-001-100','2026-09-01',100,60,200)")
        con.execute("INSERT INTO prices.listings_history (printing_id, day, "
                    "n_listings, n_sellers, n_copies) VALUES ('tst-001-100','2026-09-10',50,30,90)")
        import datetime
        u = {x["printing_id"]: x for x in
             self.comuns.universo(con, None, datetime.date(2026, 9, 10))}
        self.assertEqual(u["tst-001-100"]["pct_listings"], -50.0)
        # 20/20 (mediana) x 1 x 1,5 = 1,5
        self.assertAlmostEqual(u["tst-001-100"]["demand"], 1.5)
        self.assertEqual(self.comuns.analise(con)["listings_days"], 2)
        con.close()

    def test_a_pagina_diz_que_nao_ha_volume_de_vendas(self):
        con = self.catalogo()
        f = self.comuns.analise(con)["sources"]
        self.assertFalse(f["sales_volume"]["ok"])
        self.assertFalse(f["cardmarket"]["ok"])
        self.assertTrue(f["cardtrader"]["ok"])
        con.close()


class TestGuardar(Base):
    def test_barato_e_a_subir_vai_para_guardar(self):
        from riftvault import collection
        con = self.catalogo()
        collection.adjust(con, "tst-001-100", 5, source="test")
        con.execute("INSERT INTO prices.price_history (printing_id, day, price_cents) "
                    "VALUES ('tst-001-100','2026-09-01',10)")   # 10c -> 20c = +100%
        import datetime
        itens = self.comuns.universo(con, None, datetime.date(2026, 9, 10))
        g = self.comuns.guardar(itens)
        self.assertEqual([(x["code"], x["pct"]) for x in g], [("TST-001", 100.0)])
        con.close()

    def test_o_que_ja_esta_caro_nao_entra_no_guardar(self):
        """O tecto existe para não repetir aqui o que já está nas caras."""
        from riftvault import collection
        con = self.catalogo()
        collection.adjust(con, "tst-005-100", 5, source="test")   # 50,00 €
        con.execute("INSERT INTO prices.price_history (printing_id, day, price_cents) "
                    "VALUES ('tst-005-100','2026-09-01',1000)")
        import datetime
        itens = self.comuns.universo(con, None, datetime.date(2026, 9, 10))
        self.assertEqual(self.comuns.guardar(itens), [])
        con.close()


class TestCardmarket(Base):
    def test_o_formato_e_o_mesmo_das_outras_listas(self):
        from riftvault import collection
        con = self.catalogo()
        collection.adjust(con, "tst-001-100", 5, source="test")
        con.execute("INSERT INTO catalog.cardtrader_map (printing_id, blueprint_id, "
                    "market_name, market_set) VALUES ('tst-001-100', 1, 'Defy', 'Test Set')")
        s = self.comuns.analise(con)["sell"]
        self.assertEqual(s["text"], "2 Defy (Test Set)")
        self.assertEqual(s["lines"], 1)
        self.assertEqual(s["copies"], 2)
        con.close()

    def test_a_quantidade_da_linha_e_o_excedente__nao_o_que_tem(self):
        from riftvault import collection
        con = self.catalogo()
        collection.adjust(con, "tst-001-100", 7, source="test")
        item = self.comuns.analise(con)["sell"]["items"][0]
        self.assertEqual(item["have"], 7)
        self.assertEqual(self.cardmarket.quantidade(item), 4)
        self.assertTrue(self.cardmarket.linha(item).startswith("4 Defy"))
        con.close()


class TestOferta(Base):
    """`prices.oferta`, contra a amostra REAL gravada. Sem rede."""

    def amostra(self) -> dict:
        return json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_a_fixture_existe_e_tem_produtos_a_serio(self):
        d = self.amostra()
        self.assertEqual(len(d), 3)
        self.assertTrue(all(len(v) == 40 for v in d.values()))

    def test_conta_anuncios_vendedores_e_copias(self):
        from riftvault import prices
        d = self.amostra()
        o = prices.oferta(d["344333"])
        self.assertEqual(o["cents"], 82)
        self.assertFalse(o["from_foil"])
        # 33 dos 40 são utilizáveis: os outros são Moderately Played e afins.
        self.assertEqual(o["n_listings"], 33)
        self.assertEqual(o["n_sellers"], 32)     # um vendedor tem dois anúncios
        self.assertEqual(o["n_copies"], 122)     # o `quantity` de cada um somado
        self.assertLessEqual(o["n_sellers"], o["n_listings"])
        self.assertGreaterEqual(o["n_copies"], o["n_listings"])

    def test_a_forma_antiga_continua_a_responder(self):
        from riftvault import prices
        d = self.amostra()
        self.assertEqual(prices.lowest(d["344333"]),
                         (82, False, 33))

    def test_condicao_lingua_e_ferias_continuam_a_cortar(self):
        from riftvault import prices
        bom = {"price_cents": 100, "price_currency": "EUR", "quantity": 1,
               "graded": False, "on_vacation": False, "user": {"id": 1},
               "properties_hash": {"condition": "Near Mint", "riftbound_language": "en",
                                   "altered": False, "signed": False}}
        self.assertEqual(prices.oferta([bom])["n_listings"], 1)
        for mau in ({"on_vacation": True}, {"graded": True},
                    {"properties_hash": {**bom["properties_hash"],
                                         "condition": "Played"}},
                    {"properties_hash": {**bom["properties_hash"],
                                         "riftbound_language": "de"}}):
            o = prices.oferta([{**bom, **mau}])
            self.assertIsNone(o["cents"])
            self.assertEqual(o["n_copies"], 0)

    def test_so_foil__as_contagens_seguem_o_acabamento_do_preco(self):
        from riftvault import prices
        base = {"price_cents": 500, "price_currency": "EUR", "quantity": 3,
                "graded": False, "on_vacation": False, "user": {"id": 7},
                "properties_hash": {"condition": "Mint", "riftbound_language": "en",
                                    "altered": False, "signed": False,
                                    "riftbound_foil": True}}
        o = prices.oferta([base, {**base, "user": {"id": 8}}])
        self.assertTrue(o["from_foil"])
        self.assertEqual(o["n_listings"], 2)
        self.assertEqual(o["n_sellers"], 2)
        self.assertEqual(o["n_copies"], 6)

    def test_sem_ofertas_nenhumas(self):
        from riftvault import prices
        self.assertEqual(prices.oferta([]),
                         {"cents": None, "from_foil": False, "n_listings": 0,
                          "n_sellers": 0, "n_copies": 0})


class TestHistoricoDaOferta(Base):
    """`listings_history`: só grava quando a oferta mexe mesmo."""

    def test_o_primeiro_registo_grava_sempre(self):
        from riftvault import prices
        con = self.catalogo()
        self.assertTrue(prices._guardar_oferta(con, "tst-001-100", "2026-09-10",
                                               100, 60, 200))
        self.assertEqual(con.execute(
            "SELECT COUNT(*) n FROM prices.listings_history").fetchone()["n"], 1)
        con.close()

    def test_uma_oscilacao_pequena_nao_grava(self):
        """O prices.db vai para o Git e cada commit guarda-o inteiro."""
        from riftvault import prices
        con = self.catalogo()
        prices._guardar_oferta(con, "tst-001-100", "2026-09-10", 100, 60, 200)
        # 100 -> 105: menos de 10% e menos que o degrau de 3 em percentagem.
        self.assertFalse(prices._guardar_oferta(con, "tst-001-100", "2026-09-11",
                                                105, 60, 200))
        self.assertEqual(con.execute(
            "SELECT COUNT(*) n FROM prices.listings_history").fetchone()["n"], 1)
        con.close()

    def test_uma_mudanca_a_serio_grava(self):
        from riftvault import prices
        con = self.catalogo()
        prices._guardar_oferta(con, "tst-001-100", "2026-09-10", 100, 60, 200)
        self.assertTrue(prices._guardar_oferta(con, "tst-001-100", "2026-09-11",
                                               80, 50, 150))
        linhas = [tuple(r) for r in con.execute(
            "SELECT day, n_listings, n_sellers, n_copies FROM prices.listings_history "
            "WHERE printing_id = 'tst-001-100' ORDER BY day")]
        self.assertEqual(linhas, [("2026-09-10", 100, 60, 200),
                                  ("2026-09-11", 80, 50, 150)])
        con.close()

    def test_nas_cartas_de_poucos_anuncios_manda_o_degrau_minimo(self):
        """Com 4 anúncios, 10% é 0,4 — sem o mínimo gravava-se todos os dias."""
        from riftvault import prices
        con = self.catalogo()
        prices._guardar_oferta(con, "tst-005-100", "2026-09-10", 4, 4, 4)
        self.assertFalse(prices._guardar_oferta(con, "tst-005-100", "2026-09-11",
                                                6, 6, 6))
        self.assertTrue(prices._guardar_oferta(con, "tst-005-100", "2026-09-12",
                                               8, 8, 8))
        con.close()


class TestPayload(Base):
    def test_a_analise_vai_no_payload_da_venda(self):
        con = self.catalogo()
        p = self.venda.payload(con, editable=False)
        self.assertIn("comuns", p)
        self.assertIn("by_price", p["comuns"])
        # E a Venda de sempre continua lá, com os mesmos campos.
        for k in ("printings", "copies", "cents", "items", "kept", "blocks"):
            self.assertIn(k, p)
        con.close()

    def test_o_universo_diz_quantas_ficaram_sem_preco(self):
        con = self.catalogo()
        con.execute("DELETE FROM catalog.price_latest WHERE printing_id = 'tst-002-100'")
        u = self.comuns.analise(con)["universe"]
        self.assertEqual(u["printings"], u["priced"] + u["no_price"])
        self.assertEqual(u["no_price"], 1)
        con.close()


if __name__ == "__main__":
    unittest.main()

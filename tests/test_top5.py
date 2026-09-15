"""«Quanto custa»: só inglês, por edição, e o top 5 por raridade (2026-09-15).

André: *"apenas cartas versao ingles"* / *"no quanto custa, quero as mais
caras por edicao, nao por deck, e quero em cada edicao o top5 de mais caras de
comuns, e top5 de incomuns, e top5 de Raras"* / *"miticas e AltArt nao precisa
fazer isto"*.

O que se fixa aqui: uma oferta noutra língua não entra no preço; com sete
comuns só as cinco mais caras se MOSTRAM e o rodapé diz «mais 2» com a soma
certa; as épicas aparecem todas; o subtotal e o total contam as sete, não as
cinco; mudar o `top_por_raridade` muda o corte; e o separador não tem
agrupamento por deck.

Tudo contra cópias descartáveis (`tests.fixture.Vault`) e um config temporário
(`RIFTVAULT_CONFIG`): nunca o `data/` nem o `riftvault_config.json` reais.
"""

from __future__ import annotations

import importlib
import json
import os
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.fixture import REPO, Vault


def oferta_ct(cents, lingua="en", **extra):
    """Uma oferta do CardTrader como a API a devolve, reduzida ao que se lê."""
    props = {"riftbound_language": lingua, "condition": "Near Mint",
             "riftbound_foil": False, **extra}
    return {"price_cents": cents, "price_currency": "EUR", "quantity": 1,
            "graded": False, "on_vacation": False, "user": {"id": cents},
            "properties_hash": props}


class Base(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.close)
        from riftvault import a_subir, cardmarket, config, prices
        importlib.reload(cardmarket)
        importlib.reload(a_subir)
        importlib.reload(prices)
        self.a_subir = a_subir
        self.prices = prices
        self.config = config

    def com_config(self, extra: dict):
        caminho = self.v.root / "config.json"
        caminho.write_text(json.dumps(extra), encoding="utf-8")
        os.environ["RIFTVAULT_CONFIG"] = str(caminho)
        importlib.reload(self.config)
        self.config.load.cache_clear()

        def repor():
            os.environ.pop("RIFTVAULT_CONFIG", None)
            importlib.reload(self.config)
            self.config.load.cache_clear()

        self.addCleanup(repor)


class TestSoIngles(Base):
    """Uma oferta que não seja em inglês não entra no preço."""

    def test_oferta_noutra_lingua_nao_entra(self):
        self.com_config({"precos": {"linguas": ["en"]}})
        o = self.prices.oferta([oferta_ct(50, "ja"), oferta_ct(80, "de"), oferta_ct(120, "en")])
        self.assertEqual(o["cents"], 120)
        self.assertEqual(o["n_listings"], 1)
        self.assertEqual(o["n_sellers"], 1)

    def test_so_ofertas_noutra_lingua_e_sem_preco(self):
        self.com_config({"precos": {"linguas": ["en"]}})
        o = self.prices.oferta([oferta_ct(50, "fr"), oferta_ct(60, "zh-CN")])
        self.assertIsNone(o["cents"])
        self.assertEqual(o["n_listings"], 0)

    def test_a_lista_do_config_manda(self):
        # É o config que decide, não uma constante: com o francês aceite a
        # oferta francesa mais barata passa a ser o preço.
        self.com_config({"precos": {"linguas": ["en", "fr"]}})
        o = self.prices.oferta([oferta_ct(50, "fr"), oferta_ct(120, "en")])
        self.assertEqual(o["cents"], 50)

    def test_sem_config_e_ingles(self):
        self.assertEqual(self.prices.linguas({}), frozenset({"en"}))

    def test_lista_vazia_rebenta(self):
        with self.assertRaises(ValueError):
            self.prices.linguas({"precos": {"linguas": []}})

    def test_config_real_diz_so_ingles(self):
        # O ficheiro dele: se alguém lá puser outra língua, este teste diz.
        raw = json.loads((REPO / "riftvault_config.json").read_text(encoding="utf-8"))
        self.assertEqual(raw["precos"]["linguas"], ["en"])


class ComCatalogo(Base):
    """Uma edição com sete comuns, três incomuns, seis raras e três épicas."""

    PRECOS_COMUNS = [11, 700, 40, 300, 120, 90, 55]      # fora de ordem, de propósito

    def preco(self, con, pid, cents):
        con.execute("INSERT INTO catalog.price_latest (printing_id, price_cents, "
                    "from_foil) VALUES (?,?,0)", (pid, cents))

    def montar(self, top=5, raridades=("rare", "uncommon", "common")):
        self.com_config({
            "sets": {"AAA": {"name": "Alfa", "order": 1}},
            "quanto_custa": {"sem_edicoes": [], "top_por_raridade": top,
                             "raridades_com_top": list(raridades)},
        })
        con = self.v.connect()
        self.addCleanup(con.close)
        add = self.v.add_printing
        n = 0
        for i, c in enumerate(self.PRECOS_COMUNS, 1):
            n += 1
            add(con, f"aaa-c{i}", "AAA", n, f"Comum {i}", rarity="common")
            self.preco(con, f"aaa-c{i}", c)
        for i, c in enumerate([200, 30, 500], 1):
            n += 1
            add(con, f"aaa-u{i}", "AAA", n, f"Incomum {i}", rarity="uncommon")
            self.preco(con, f"aaa-u{i}", c)
        for i, c in enumerate([900, 100, 1500, 250, 800, 60], 1):
            n += 1
            add(con, f"aaa-r{i}", "AAA", n, f"Rara {i}", rarity="rare")
            self.preco(con, f"aaa-r{i}", c)
        for i, c in enumerate([5000, 300, 9000], 1):
            n += 1
            add(con, f"aaa-e{i}", "AAA", n, f"Epica {i}", rarity="epic")
            self.preco(con, f"aaa-e{i}", c)
        self.v.rebuild(con)
        con.commit()
        return con

    @staticmethod
    def grupo(q, raridade):
        return next(g for g in q["groups"] if g["rarity"] == raridade)

    @staticmethod
    def vistos(g):
        ids = set(g.get("top_ids") or [x["printing_id"] for x in g["items"]])
        return [x["printing_id"] for x in g["items"] if x["printing_id"] in ids]


class TestTop5(ComCatalogo):
    def test_so_as_cinco_comuns_mais_caras_se_veem(self):
        con = self.montar()
        q = self.a_subir.quanto_custa(con, set_id="AAA")
        g = self.grupo(q, "common")
        # As cinco mais caras, do mais caro para o mais barato: 700, 300, 120, 90, 55.
        self.assertEqual(self.vistos(g), ["aaa-c2", "aaa-c4", "aaa-c5", "aaa-c6", "aaa-c7"])
        self.assertEqual(g["top"], 5)
        self.assertEqual(len(g["items"]), 7)            # a lista inteira continua lá

    def test_rodape_diz_mais_2_e_a_soma_certa(self):
        con = self.montar()
        g = self.grupo(self.a_subir.quanto_custa(con, set_id="AAA"), "common")
        # Ficam de fora a de 40 e a de 11 — 3 cópias cada (Unit, playset 3).
        self.assertEqual(g["hidden"], {"cards": 2, "copies": 6, "cents": 3 * 40 + 3 * 11})

    def test_o_subtotal_conta_as_sete_nao_as_cinco(self):
        con = self.montar()
        g = self.grupo(self.a_subir.quanto_custa(con, set_id="AAA"), "common")
        self.assertEqual(g["cards"], 7)
        self.assertEqual(g["copies"], 21)
        self.assertEqual(g["cents"], 3 * sum(self.PRECOS_COMUNS))
        # E o que se vê mais o que se esconde é o subtotal, sem sobra.
        vistos = [x for x in g["items"] if x["printing_id"] in g["top_ids"]]
        self.assertEqual(sum(x["total"] for x in vistos) + g["hidden"]["cents"], g["cents"])

    def test_o_total_do_separador_conta_tudo(self):
        con = self.montar()
        q = self.a_subir.quanto_custa(con, set_id="AAA")
        todos = self.a_subir.master_faltas(con)
        # O mesmo número que a lista do «Master set», que não sabe do corte.
        self.assertEqual(q["cents"], todos["cents"])
        self.assertEqual(q["copies"], todos["copies"])
        self.assertEqual(q["cents"], sum(g["cents"] for g in q["groups"]))
        # E é maior do que a soma do que se vê — o corte esconde dinheiro só do ecrã.
        visivel = sum(x["total"] for g in q["groups"] for x in g["items"]
                      if x["printing_id"] in set(g.get("top_ids") or [x["printing_id"]]))
        self.assertLess(visivel, q["cents"])

    def test_as_epicas_aparecem_todas(self):
        con = self.montar()
        g = self.grupo(self.a_subir.quanto_custa(con, set_id="AAA"), "epic")
        self.assertNotIn("top_ids", g)
        self.assertNotIn("hidden", g)
        self.assertEqual(len(self.vistos(g)), 3)

    def test_um_grupo_que_caiba_nao_leva_corte(self):
        con = self.montar()
        # Três incomuns cabem em cinco: nada a esconder, nada a dizer.
        g = self.grupo(self.a_subir.quanto_custa(con, set_id="AAA"), "uncommon")
        self.assertNotIn("top_ids", g)
        self.assertNotIn("hidden", g)

    def test_o_corte_vem_do_config(self):
        con = self.montar(top=3)
        q = self.a_subir.quanto_custa(con, set_id="AAA")
        self.assertEqual(self.vistos(self.grupo(q, "common")), ["aaa-c2", "aaa-c4", "aaa-c5"])
        self.assertEqual(self.grupo(q, "common")["hidden"]["cards"], 4)
        self.assertEqual(self.grupo(q, "rare")["hidden"]["cards"], 3)
        self.assertEqual(self.vistos(self.grupo(q, "uncommon")), ["aaa-u3", "aaa-u1", "aaa-u2"])

    def test_zero_desliga_o_corte(self):
        con = self.montar(top=0)
        q = self.a_subir.quanto_custa(con, set_id="AAA")
        self.assertTrue(all("top_ids" not in g for g in q["groups"]))

    def test_as_raridades_com_top_vem_do_config(self):
        con = self.montar(top=2, raridades=("epic",))
        q = self.a_subir.quanto_custa(con, set_id="AAA")
        self.assertEqual(self.vistos(self.grupo(q, "epic")), ["aaa-e3", "aaa-e1"])
        self.assertNotIn("top_ids", self.grupo(q, "common"))

    def test_o_inversor_mostra_as_mesmas_cinco_ao_contrario(self):
        con = self.montar()
        g = self.grupo(self.a_subir.quanto_custa(con, set_id="AAA", ordem="asc"), "common")
        self.assertEqual(self.vistos(g), ["aaa-c7", "aaa-c6", "aaa-c5", "aaa-c4", "aaa-c2"])
        self.assertEqual(g["hidden"]["cards"], 2)

    def test_o_payload_leva_o_corte_para_o_browser(self):
        con = self.montar(top=4)
        p = self.a_subir.master_faltas(con)
        self.assertEqual(p["quanto_custa"]["top"], 4)
        self.assertEqual(p["quanto_custa"]["top_rarities"], ["common", "rare", "uncommon"])


class TestPorEdicaoNaoPorDeck(unittest.TestCase):
    """O separador «Quanto custa» não tem abas por deck; elas vivem nos Decks."""

    def setUp(self):
        self.js = (REPO / "riftvault" / "web" / "app.js").read_text(encoding="utf-8")

    def bloco(self, nome):
        m = re.search(nome + r" = \[(.*?)\];", self.js, re.S)
        self.assertIsNotNone(m, nome)
        return re.findall(r"id: '([a-z]+)'", m.group(1))

    def test_quanto_custa_so_tem_abas_por_edicao(self):
        ids = self.bloco("FALTA_TABS")
        self.assertEqual(ids, ["master", "spike", "caminho"])
        for por_deck in ("staples", "pordeck", "deck", "pimp"):
            self.assertNotIn(por_deck, ids)

    def test_as_abas_por_deck_vivem_nos_decks(self):
        self.assertEqual(self.bloco("DECK_FALTA_TABS"), ["staples", "pordeck", "pimp"])
        # E o separador Decks desenha-as mesmo.
        self.assertIn("for (const t of DECK_FALTA_TABS)", self.js)
        self.assertIn("loadDeckFaltas(t.id)", self.js)

    def test_o_python_nao_agrupa_por_deck(self):
        # O `quanto_custa` só sabe de edições e raridades.
        from riftvault import a_subir
        import inspect
        fonte = inspect.getsource(a_subir.quanto_custa) + inspect.getsource(a_subir.por_raridade)
        self.assertNotIn("deck", fonte.lower().replace("decks/venda", ""))


if __name__ == "__main__":
    unittest.main()

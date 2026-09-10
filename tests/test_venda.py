"""«Venda»: o que ele tem a mais da sequência do master set e não está a jogar.

*"A Coleção é de master set. O resto provavelmente vai para venda ou jogar nos
decks seleccionados"* (André, 2026-09-08).

Na mesma tarde ele pediu *"1 alt art de cada"*, e a venda passou a ser só o
EXCEDENTE do que a coleção pede: a primeira arte alternativa é coleção, a
segunda é venda.
"""

from __future__ import annotations

import importlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.fixture import Vault


class Base(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.close)
        from riftvault import cardmarket, metrics, venda
        importlib.reload(metrics)
        importlib.reload(venda)
        self.venda, self.cardmarket = venda, cardmarket

    def catalogo(self):
        con = self.v.connect()
        self.v.add_printing(con, "tst-001-100", "TST", 1, "Defy", api_sort=1)
        self.v.add_printing(con, "tst-001a-100", "TST", 1, "Defy",
                            variant="a", kind="alt_art", api_sort=2)
        self.v.add_printing(con, "tst-002-100", "TST", 2, "Brutalizer", api_sort=3)
        self.v.add_printing(con, "tst-002a-100", "TST", 2, "Brutalizer",
                            variant="a", kind="alt_art", api_sort=4)
        self.v.add_printing(con, "tst-t01-100", "TST", 3, "Sprite",
                            variant="t01", kind="token", api_sort=5)
        self.v.rebuild(con)
        for pid, cents in (("tst-001a-100", 2000), ("tst-002a-100", 500),
                           ("tst-t01-100", 100)):
            con.execute("INSERT INTO catalog.price_latest (printing_id, price_cents) "
                        "VALUES (?,?)", (pid, cents))
        return con


class TestAmbito(Base):
    def test_so_entra_o_que_a_sequencia_do_master_set_nao_pede(self):
        from riftvault import collection
        con = self.catalogo()
        collection.adjust(con, "tst-001-100", 9, source="test")    # base, a mais
        collection.adjust(con, "tst-001a-100", 2, source="test")   # 1 é coleção
        collection.adjust(con, "tst-t01-100", 2, source="test")

        ids = [x["printing_id"] for x in self.venda.listar(con)["items"]]
        # A base fica de fora por muitas que ele tenha: é master set.
        self.assertNotIn("tst-001-100", ids)
        self.assertEqual(sorted(ids), ["tst-001a-100", "tst-t01-100"])
        con.close()

    def test_a_primeira_alt_art_e_colecao__a_segunda_e_venda(self):
        """*"no fim 1 alt art de cada"*: o alvo guarda-se antes de vender."""
        from riftvault import collection
        con = self.catalogo()
        collection.adjust(con, "tst-001a-100", 1, source="test")
        self.assertEqual(self.venda.listar(con)["items"], [])

        collection.adjust(con, "tst-001a-100", 1, source="test")   # a segunda
        v = self.venda.listar(con)
        self.assertEqual([x["printing_id"] for x in v["items"]], ["tst-001a-100"])
        self.assertEqual(v["items"][0]["have"], 2)
        self.assertEqual(v["items"][0]["target"], 1)
        self.assertEqual(v["items"][0]["qty"], 1)
        con.close()

    def test_o_token_esta_fora_da_colecao__sobra_inteiro(self):
        """Os `-T` não contam para a percentagem: não há alvo a guardar."""
        from riftvault import collection
        con = self.catalogo()
        collection.adjust(con, "tst-t01-100", 2, source="test")

        item = self.venda.listar(con)["items"][0]
        self.assertEqual(item["printing_id"], "tst-t01-100")
        self.assertEqual((item["target"], item["qty"]), (0, 2))
        con.close()

    def test_o_que_nao_tem_nao_aparece(self):
        con = self.catalogo()
        self.assertEqual(self.venda.listar(con)["items"], [])
        con.close()

    def test_soma_e_ordem_pelo_valor(self):
        from riftvault import collection
        con = self.catalogo()
        collection.adjust(con, "tst-001a-100", 2, source="test")   # sobra 1: 20,00 €
        collection.adjust(con, "tst-002a-100", 3, source="test")   # sobram 2: 10,00 €
        v = self.venda.listar(con)

        self.assertEqual(v["printings"], 2)
        self.assertEqual(v["copies"], 3)
        self.assertEqual(v["cents"], 2000 + 1000)
        self.assertEqual([x["printing_id"] for x in v["items"]],
                         ["tst-001a-100", "tst-002a-100"])
        con.close()

    def test_blocos_separam_tokens_de_artes_alternativas(self):
        from riftvault import collection
        con = self.catalogo()
        collection.adjust(con, "tst-001a-100", 2, source="test")
        collection.adjust(con, "tst-t01-100", 2, source="test")

        blocos = {b["id"]: b for b in self.venda.listar(con)["blocks"]}
        self.assertEqual(blocos["token"]["copies"], 2)
        self.assertEqual(blocos["alt_art"]["copies"], 1)
        con.close()

    def test_sem_preco_entra_na_lista_mas_nao_no_total(self):
        from riftvault import collection
        con = self.catalogo()
        con.execute("DELETE FROM catalog.price_latest WHERE printing_id = 'tst-001a-100'")
        collection.adjust(con, "tst-001a-100", 3, source="test")

        v = self.venda.listar(con)
        self.assertEqual(v["printings"], 1)
        self.assertEqual(v["no_price"], 1)
        self.assertEqual(v["cents"], 0)
        con.close()


class TestDecks(Base):
    """Uma cópia que está num deck não é candidata a venda.

    Desde 2026-09-10 «estar num deck» é um FACTO gravado, não uma dedução: o
    André marca a cópia como estando no deck (`locais.mover`) e é isso que a
    venda lê. Antes a alocação por prioridade adivinhava-o a partir das listas —
    por isso estes casos passaram a marcar as cópias primeiro.
    """

    def montar(self, lista: str):
        from riftvault import collection, decks
        con = self.catalogo()
        self.v.write_deck("azir", lista)
        decks.import_all(con, log=lambda *_: None)
        return con, collection, decks

    def test_alt_art_marcada_no_deck_sai_da_lista(self):
        from riftvault import locais
        con, collection, _ = self.montar(
            "Legend:\n1 Emperor of the Sands\nMainDeck:\n3 Defy\n")
        # Só tem a arte alternativa, e marcou-a como estando no deck.
        collection.adjust(con, "tst-001a-100", 3, source="test")
        locais.mover(con, "tst-001a-100", 3, locais.COLECAO,
                     locais.deck_local("azir"), source="test")

        v = self.venda.listar(con)
        self.assertEqual(v["items"], [])
        self.assertEqual(v["in_decks"], 1)
        self.assertEqual(v["in_decks_copies"], 3)
        self.assertEqual(v["kept"][0]["state"], "deck")
        con.close()

    def test_a_base_serve_primeiro__a_alt_art_do_binder_sobra(self):
        """No binder Decks/Venda, o deck leva a base e a alternativa sobra."""
        from riftvault import locais
        con, collection, _ = self.montar(
            "Legend:\n1 Emperor of the Sands\nMainDeck:\n3 Defy\n")
        collection.adjust(con, "tst-001-100", 3, source="test")
        collection.adjust(con, "tst-001a-100", 3, source="test")
        for pid in ("tst-001-100", "tst-001a-100"):
            locais.mover(con, pid, 3, locais.COLECAO, locais.BINDER, source="test")

        v = self.venda.listar(con)
        # A base está no binder e o deck pede 3: fica toda comprometida. A alt
        # art não é precisa e sai inteira — vem do binder, não da Coleção.
        item = next(x for x in v["items"] if x["printing_id"] == "tst-001a-100")
        self.assertEqual(item["from_binder"], 3)
        self.assertEqual(item["from_colecao"], 0)
        self.assertEqual(item["origem"], "binder")
        self.assertNotIn("tst-001-100", [x["printing_id"] for x in v["items"]])
        con.close()

    def test_so_o_excedente_e_que_se_vende(self):
        """4 cópias: 2 no deck, 2 na Coleção que só pede 1 — vende-se 1."""
        from riftvault import locais
        con, collection, _ = self.montar(
            "Legend:\n1 Emperor of the Sands\nMainDeck:\n2 Defy\n")
        collection.adjust(con, "tst-001a-100", 4, source="test")
        locais.mover(con, "tst-001a-100", 2, locais.COLECAO,
                     locais.deck_local("azir"), source="test")

        v = self.venda.listar(con)
        item = v["items"][0]
        self.assertEqual(item["have"], 4)
        self.assertEqual(item["used"], 2)          # as do deck nunca se vendem
        self.assertEqual(item["in_colecao"], 2)
        self.assertEqual(item["from_colecao"], 1)  # o alvo da alt art é 1
        self.assertEqual(item["qty"], 1)
        self.assertEqual(item["state"], "deck")    # está num deck E sobra
        self.assertEqual(v["copies"], 1)
        con.close()

    def test_a_colecao_fica_com_a_dela(self):
        """3 cópias, 2 no deck: a que fica na Coleção é o alvo e não se vende."""
        from riftvault import locais
        con, collection, _ = self.montar(
            "Legend:\n1 Emperor of the Sands\nMainDeck:\n2 Defy\n")
        collection.adjust(con, "tst-001a-100", 3, source="test")
        locais.mover(con, "tst-001a-100", 2, locais.COLECAO,
                     locais.deck_local("azir"), source="test")

        v = self.venda.listar(con)
        self.assertEqual(v["items"], [])
        self.assertEqual(v["in_decks_copies"], 2)
        con.close()

    def test_nao_mexe_na_colecao(self):
        con, collection, _ = self.montar(
            "Legend:\n1 Emperor of the Sands\nMainDeck:\n3 Defy\n")
        collection.adjust(con, "tst-001a-100", 2, source="test")
        antes = con.execute("SELECT printing_id, qty FROM copies").fetchall()

        self.venda.listar(con)
        depois = con.execute("SELECT printing_id, qty FROM copies").fetchall()
        self.assertEqual([tuple(r) for r in antes], [tuple(r) for r in depois])
        self.assertEqual(con.execute("SELECT COUNT(*) FROM ops").fetchone()[0], 1)
        con.close()


class TestLista(Base):
    """A lista sai pelo mesmo gerador das de compra."""

    def test_a_quantidade_da_linha_e_o_excedente(self):
        from riftvault import collection
        con = self.catalogo()
        collection.adjust(con, "tst-001a-100", 3, source="test")   # 1 é coleção

        itens = self.venda.listar(con)["items"]
        res = self.cardmarket.gerar(itens)
        self.assertEqual(res["copies"], 2)
        self.assertTrue(res["text"].startswith("2 Defy"))
        con.close()

    def test_com_codigo(self):
        from riftvault import collection
        con = self.catalogo()
        collection.adjust(con, "tst-001a-100", 2, source="test")

        itens = self.venda.listar(con)["items"]
        self.assertEqual(self.cardmarket.linha(itens[0], com_codigo=True),
                         "1 Defy [TST-001a]")
        con.close()

    def test_csv_leva_a_mesma_quantidade(self):
        from riftvault import collection
        con = self.catalogo()
        collection.adjust(con, "tst-002a-100", 4, source="test")   # 1 é coleção

        linhas = self.cardmarket.csv_texto(self.venda.listar(con)["items"]).splitlines()
        self.assertEqual(linhas[0].split(",")[0], "quantidade")
        self.assertTrue(linhas[1].startswith("3,Brutalizer,TST-002a"))
        con.close()

    def test_as_listas_de_compra_continuam_a_usar_missing(self):
        """O gerador é o mesmo: `missing` nas de compra, `qty` na de venda."""
        self.assertEqual(self.cardmarket.linha({"missing": 3, "name": "Defy"}),
                         "3 Defy")
        self.assertEqual(self.cardmarket.linha({"qty": 2, "name": "Defy"}),
                         "2 Defy")
        # Se vierem os dois, manda o das listas de compra.
        self.assertEqual(self.cardmarket.linha({"missing": 3, "qty": 9, "name": "Defy"}),
                         "3 Defy")


if __name__ == "__main__":
    unittest.main()

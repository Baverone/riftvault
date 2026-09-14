"""«Muda tudo para playset» (André, 2026-09-14).

Um critério só: tudo o que está DENTRO da Coleção pede o playset do seu tipo
(`playset_targets_by_type`) — Unit/Spell/Gear 3, Rune 12, Legend e Battlefield
1. O que está em `master_set.fora` (tokens, signatures, sobrenumeradas, promos)
NÃO mudou: alvo 1, fora da percentagem.

Corre contra cópias (`tests.fixture.Vault`): o config real só é LIDO, nunca
escrito — a lição de 11/09.
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
        from riftvault import metrics, venda
        importlib.reload(metrics)
        importlib.reload(venda)
        self.metrics, self.venda = metrics, venda

    def edicao(self):
        """Uma de cada coisa: os três blocos de dentro e as quatro saídas."""
        con = self.v.connect()
        v = self.v
        v.add_printing(con, "tst-001-100", "TST", 1, "Defy", size=100, api_sort=1)
        v.add_printing(con, "tst-001a-100", "TST", 1, "Defy", variant="a",
                       kind="alt_art", rarity="showcase", size=100, api_sort=2)
        v.add_printing(con, "tst-001-star-100", "TST", 1, "Defy", variant="star",
                       kind="signature", rarity="showcase", size=100, api_sort=3)
        v.add_printing(con, "tst-002-100", "TST", 2, "Fury Rune",
                       card_type="Rune", size=100, api_sort=4)
        v.add_printing(con, "tst-002a-100", "TST", 2, "Fury Rune",
                       card_type="Rune", variant="a", kind="alt_art", size=100,
                       api_sort=5)
        v.add_printing(con, "tst-r01", "TST", 1, "Body Rune", card_type="Rune",
                       variant="r01", kind="rune_promo", lane="r",
                       codigo="TST-R01", api_sort=6)
        v.add_printing(con, "tst-003-100", "TST", 3, "Um Campo",
                       card_type="Battlefield", size=100, api_sort=7)
        v.add_printing(con, "tst-004-100", "TST", 4, "Um Legend",
                       card_type="Legend", size=100, api_sort=8)
        v.add_printing(con, "tst-t01-100", "TST", 5, "Recruit", variant="t01",
                       kind="token", lane="t", codigo="TST-T01", api_sort=9)
        v.add_printing(con, "tst-101-100", "TST", 101, "Defy", size=100,
                       api_sort=10)                                # sobrenumerada
        v.add_printing(con, "tst-sp1-006", "TST", 1, "Uma Promo", variant="sp1",
                       kind="special", lane="sp", codigo="TST-SP1/006",
                       api_sort=11)
        v.rebuild(con)
        return con

    def alvos(self, con) -> dict[str, int]:
        rows = con.execute("SELECT * FROM catalog.printings").fetchall()
        return {r["printing_id"]: self.metrics.alvo(r) for r in rows}


class TestAlvos(Base):
    def test_dentro_da_colecao_e_o_playset_do_tipo(self):
        con = self.edicao()
        a = self.alvos(con)
        self.assertEqual(a["tst-001-100"], 3)      # Unit base
        self.assertEqual(a["tst-001a-100"], 3)     # alt art de Unit: 3, era 1
        self.assertEqual(a["tst-002-100"], 12)     # runa base: 12, era 1
        self.assertEqual(a["tst-002a-100"], 12)    # runa especial: 12, era 1
        self.assertEqual(a["tst-r01"], 12)         # runa promo: 12, era 1
        self.assertEqual(a["tst-003-100"], 1)      # Battlefield: o playset É 1
        self.assertEqual(a["tst-004-100"], 1)      # Legend: idem
        con.close()

    def test_fora_da_colecao_fica_a_1_e_fora_da_percentagem(self):
        con = self.edicao()
        a = self.alvos(con)
        rows = {r["printing_id"]: r for r in con.execute("SELECT * FROM catalog.printings")}
        for pid in ("tst-001-star-100", "tst-t01-100", "tst-101-100", "tst-sp1-006"):
            self.assertEqual(a[pid], 1, pid)
            self.assertFalse(self.metrics.e_master(rows[pid]), pid)
            self.assertFalse(self.metrics.conta_bloco(self.metrics.bloco(rows[pid])), pid)
        con.close()

    def test_o_alvo_e_o_do_playset_jogavel(self):
        """Um critério só: o alvo do master é o `playset_target` do tipo."""
        con = self.edicao()
        a = self.alvos(con)
        for pid, tipo in (("tst-001a-100", "Unit"), ("tst-002-100", "Rune"),
                          ("tst-002a-100", "Rune"), ("tst-003-100", "Battlefield")):
            self.assertEqual(a[pid], self.metrics.playset_target(tipo, False), pid)
        con.close()

    def test_o_denominador_nao_mexe(self):
        """São as mesmas impressões a contar; o que cresce são as cópias."""
        con = self.edicao()
        p = self.metrics.set_payload(con, "TST")["progress"]
        # 7 dentro (Unit, alt art, runa, runa alt, runa promo, Battlefield, Legend)
        self.assertEqual(p["levels"][-1]["total"], 7)
        self.assertEqual(p["levels"][-1]["missing"], 3 + 3 + 12 + 12 + 12 + 1 + 1)
        con.close()


class TestVenda(Base):
    def test_o_excedente_desce_quando_o_alvo_sobe(self):
        """Duas alt arts eram 1 a vender; com alvo 3 já não sobra nenhuma."""
        from riftvault import collection
        con = self.edicao()
        collection.adjust(con, "tst-001a-100", 2, source="test")
        self.assertEqual(self.venda.listar(con)["items"], [])
        collection.adjust(con, "tst-001a-100", 2, source="test")   # 4: sobra 1
        v = self.venda.listar(con)
        self.assertEqual([(x["printing_id"], x["qty"]) for x in v["items"]],
                         [("tst-001a-100", 1)])
        con.close()

    def test_a_runa_especial_so_sobra_acima_de_12(self):
        from riftvault import collection
        con = self.edicao()
        collection.adjust(con, "tst-002a-100", 12, source="test")
        self.assertEqual(self.venda.listar(con)["items"], [])
        collection.adjust(con, "tst-002a-100", 1, source="test")
        self.assertEqual([x["qty"] for x in self.venda.listar(con)["items"]], [1])
        con.close()


if __name__ == "__main__":
    unittest.main()

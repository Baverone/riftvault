"""O «tens N de M» dos blocos da coleção extra (2026-09-15).

Fotografias do André: o bloco «Coleção — promos — playset» dizia «tens 0 de
6» com o `VEN-SP4` e o `VEN-SP5` a cores e com o crachá «1/3». O número
estava certo — contava PLAYSETS COMPLETOS, e desde 2026-09-14 a coleção extra
pede playset — mas a etiqueta lia-se como «não tens nenhuma». O cabeçalho
passou a dizer as duas coisas: quantas impressões tem (pelo menos uma cópia) e
quantas estão no playset completo. O payload leva `owned`, `done` e
`max_target` por bloco; o `app.js` recalcula o mesmo a partir do estado local.

Corre contra cópias (`tests.fixture.Vault`); o config real só é lido.
"""

from __future__ import annotations

import importlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.fixture import Vault


class TestContadorDoBloco(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.close)
        from riftvault import metrics
        importlib.reload(metrics)
        self.metrics = metrics

    def edicao(self):
        """Seis promos (alvo 3) e duas runas especiais (alvo 1)."""
        con = self.v.connect()
        v = self.v
        v.add_printing(con, "tst-001-100", "TST", 1, "Uma Unit", size=100, api_sort=1)
        for i in range(1, 7):
            v.add_printing(con, f"tst-sp{i}-006", "TST", i, f"Promo {i}",
                           variant=f"sp{i}", kind="special", lane="sp",
                           codigo=f"TST-SP{i}/006", api_sort=10 + i)
        v.add_printing(con, "tst-002-100", "TST", 2, "Fury Rune",
                       card_type="Rune", size=100, api_sort=2)
        v.add_printing(con, "tst-002a-100", "TST", 2, "Fury Rune",
                       card_type="Rune", variant="a", kind="alt_art", size=100,
                       api_sort=3)
        v.add_printing(con, "tst-r01", "TST", 1, "Body Rune", card_type="Rune",
                       variant="r01", kind="rune_promo", lane="r",
                       codigo="TST-R01", api_sort=4)
        v.rebuild(con)
        return con

    def blocos(self, con) -> dict:
        p = self.metrics.set_payload(con, "TST")
        return {b["id"]: b for b in p["blocks"]}

    def test_duas_a_uma_copia_e_quatro_a_zero_le_se_tens_2_de_6(self):
        """A fotografia: nenhum playset completo, mas duas impressões na caixa."""
        from riftvault import collection
        con = self.edicao()
        collection.adjust(con, "tst-sp4-006", 1, source="test")
        collection.adjust(con, "tst-sp5-006", 1, source="test")
        b = self.blocos(con)["special"]
        self.assertEqual((b["owned"], b["done"], b["total"]), (2, 0, 6))
        self.assertEqual(b["max_target"], 3)
        self.assertFalse(b["counts"])
        con.close()

    def test_um_playset_completo_conta_nas_duas(self):
        from riftvault import collection
        con = self.edicao()
        collection.adjust(con, "tst-sp1-006", 3, source="test")
        collection.adjust(con, "tst-sp2-006", 2, source="test")
        b = self.blocos(con)["special"]
        self.assertEqual((b["owned"], b["done"], b["total"]), (2, 1, 6))
        con.close()

    def test_num_bloco_de_alvo_1_os_dois_numeros_sao_o_mesmo(self):
        """As runas especiais pedem 1: ter uma é ter o alvo — e o cabeçalho
        não precisa de dizer duas vezes a mesma coisa (`max_target` 1)."""
        from riftvault import collection
        con = self.edicao()
        collection.adjust(con, "tst-r01", 4, source="test")
        b = self.blocos(con)["rune_special"]
        self.assertEqual((b["owned"], b["done"], b["total"]), (1, 1, 2))
        self.assertEqual(b["max_target"], 1)
        con.close()

    def test_o_master_set_leva_as_mesmas_contas(self):
        from riftvault import collection
        con = self.edicao()
        collection.adjust(con, "tst-001-100", 1, source="test")
        b = self.blocos(con)["master"]
        # A Unit (1 de 3) e a runa base (0 de 1).
        self.assertEqual((b["owned"], b["done"], b["total"]), (1, 0, 2))
        self.assertEqual(b["max_target"], 3)
        self.assertTrue(b["counts"])
        con.close()


if __name__ == "__main__":
    unittest.main()

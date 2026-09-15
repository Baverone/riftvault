"""O «tens N de M» dos blocos da coleção extra (2026-09-15).

Fotografias do André: o bloco «Coleção — promos — playset» dizia «tens 0 de
6» com o `VEN-SP4` e o `VEN-SP5` a cores e com o crachá «1/3». O número
estava certo — contava PLAYSETS COMPLETOS, e desde 2026-09-14 a coleção extra
pede playset — mas a etiqueta lia-se como «não tens nenhuma». O cabeçalho
passou a dizer as duas coisas: quantas impressões tem (pelo menos uma cópia) e
quantas estão no playset completo. O payload leva `owned`, `done` e
`max_target` por bloco; o `app.js` recalcula o mesmo a partir do estado local.

Horas depois as promos voltaram a alvo 1 (*"overnumbered e promos (SP)
voltamos a 1 de cada"*), por isso o bloco que aqui faz de «pede playset» são
as artes alternativas — a fotografia dele lê-se hoje nesse bloco. O das
promos ficou como caso de alvo 1, ao lado das runas especiais.

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
        """Seis artes alternativas (alvo 3), seis promos (alvo 1) e uma runa
        especial (alvo 3 desde 2026-09-15)."""
        con = self.v.connect()
        v = self.v
        v.add_printing(con, "tst-001-100", "TST", 1, "Uma Unit", size=100, api_sort=1)
        for i in range(1, 7):
            v.add_printing(con, f"tst-sp{i}-006", "TST", i, f"Promo {i}",
                           variant=f"sp{i}", kind="special", lane="sp",
                           codigo=f"TST-SP{i}/006", api_sort=10 + i)
            v.add_printing(con, f"tst-{i + 10:03d}a-100", "TST", i + 10,
                           f"Unit {i}", variant="a", kind="alt_art",
                           rarity="showcase", size=100, api_sort=20 + i)
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
        collection.adjust(con, "tst-014a-100", 1, source="test")
        collection.adjust(con, "tst-015a-100", 1, source="test")
        b = self.blocos(con)["alt_art"]
        self.assertEqual((b["owned"], b["done"], b["total"]), (2, 0, 6))
        self.assertEqual(b["max_target"], 3)
        self.assertFalse(b["counts"])
        con.close()

    def test_um_playset_completo_conta_nas_duas(self):
        from riftvault import collection
        con = self.edicao()
        collection.adjust(con, "tst-011a-100", 3, source="test")
        collection.adjust(con, "tst-012a-100", 2, source="test")
        b = self.blocos(con)["alt_art"]
        self.assertEqual((b["owned"], b["done"], b["total"]), (2, 1, 6))
        con.close()

    def test_as_promos_a_1_de_cada_dizem_tens_2_de_6_e_e_verdade(self):
        """A mesma fotografia, depois de *"promos (SP) voltamos a 1 de cada"*:
        as duas promos a uma cópia ESTÃO completas, `owned` e `done` são o
        mesmo número e o `max_target` 1 poupa o cabeçalho ao «no playset
        completo». Uma segunda cópia não altera nenhuma das contas."""
        from riftvault import collection
        con = self.edicao()
        collection.adjust(con, "tst-sp4-006", 1, source="test")
        collection.adjust(con, "tst-sp5-006", 2, source="test")
        b = self.blocos(con)["special"]
        self.assertEqual((b["owned"], b["done"], b["total"]), (2, 2, 6))
        self.assertEqual(b["max_target"], 1)
        self.assertFalse(b["counts"])
        self.assertEqual(b["label"], "Coleção — promos — 1 de cada")
        con.close()

    def test_as_runas_especiais_pedem_3_como_a_base(self):
        """A arte alternativa da runa numerada pede 3 desde 2026-09-15 (*"as
        runas que estao no masterset […] vamos ate 3 como as outras cartas"*):
        com uma cópia está na caixa mas não completa; com quatro está completa
        e o cabeçalho leva o «no playset completo» (`max_target` 3). Até esse
        dia pedia 1 e os dois números eram o mesmo.

        Só a arte alternativa da runa (numerada) enche o bloco; a promo
        `TST-R01` está escondida desde 2026-09-15 e nem entra na conta."""
        from riftvault import collection
        con = self.edicao()
        collection.adjust(con, "tst-002a-100", 1, source="test")
        collection.adjust(con, "tst-r01", 4, source="test")
        b = self.blocos(con)["rune_special"]
        self.assertEqual((b["owned"], b["done"], b["total"]), (1, 0, 1))
        self.assertEqual(b["max_target"], 3)
        collection.adjust(con, "tst-002a-100", 3, source="test")
        b = self.blocos(con)["rune_special"]
        self.assertEqual((b["owned"], b["done"], b["total"]), (1, 1, 1))
        con.close()

    def test_o_master_set_leva_as_mesmas_contas(self):
        from riftvault import collection
        con = self.edicao()
        collection.adjust(con, "tst-001-100", 1, source="test")
        b = self.blocos(con)["master"]
        # A Unit (1 de 3) e a runa base (0 de 3).
        self.assertEqual((b["owned"], b["done"], b["total"]), (1, 0, 2))
        self.assertEqual(b["max_target"], 3)
        self.assertTrue(b["counts"])
        con.close()


if __name__ == "__main__":
    unittest.main()

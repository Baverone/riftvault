"""Regras de deck: validação de legalidade e alocação por prioridade."""

from __future__ import annotations

import importlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.fixture import Vault


class TestLegalidade(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.close)

    def test_legend_sem_dominios_nao_rebenta_a_seccao(self):
        """`domains_json` é anulável. Um NULL rebentava o deck_payload todo.

        O ciclo que valida as cartas do main já fazia `or "[]"`; a linha do
        Legend não fazia, e a excepção subia até ao servidor — a secção Decks
        ficava em branco, sem dizer porquê.
        """
        from riftvault import collection, decks
        importlib.reload(decks)

        con = self.v.connect()
        self.v.add_printing(con, "tst-001-100", "TST", 1, "Sem Dominio",
                            card_type="Legend", domains=None)
        self.v.add_printing(con, "tst-002-100", "TST", 2, "Brutalizer")
        self.v.rebuild(con)
        collection.adjust(con, "tst-001-100", 1, source="test")

        self.v.write_deck("nulo", "Legend:\n1 Sem Dominio\n\nMainDeck:\n3 Brutalizer\n")
        decks.import_all(con, log=lambda *_: None)
        deck_id = con.execute("SELECT deck_id FROM decks WHERE name='nulo'").fetchone()[0]

        payload = decks.deck_payload(con, deck_id)
        self.assertEqual(payload["legality"]["dominios"]["legend"], [])
        # Sem domínios no Legend não há identidade para violar.
        self.assertTrue(payload["legality"]["dominios"]["ok"])
        con.close()


if __name__ == "__main__":
    unittest.main()

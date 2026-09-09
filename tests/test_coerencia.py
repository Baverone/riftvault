"""Coerência entre o que a Coleção CONTA e o que a Coleção manda COMPRAR.

Revisão de 2026-09-09. No cabeçalho de cada edição há dois números quase
encostados: o chip do playset da contagem por níveis («faltam 383») e a linha
da wantlist («360 cópias a comprar»). São perguntas diferentes — a contagem é a
métrica e a lista é de compra — mas vistos lado a lado sem explicação liam-se
como um erro de contagem, e por isso a linha passou a dizer a diferença.

O que se fixa aqui é o que essa frase promete:

  1. a lista de compra NUNCA pede mais cópias do que a contagem diz que faltam;
  2. a diferença vem só de duas coisas — as exclusões das listas de compra
     (signatures e showcases) e o que já vem a caminho;
  3. sem nenhuma delas, os dois números são o MESMO.

Se um dia divergirem por outro motivo, é a frase no ecrã que passa a mentir.
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
        from riftvault import a_subir, cardmarket, config, metrics
        importlib.reload(cardmarket)
        importlib.reload(a_subir)
        self.a_subir = a_subir
        self.metrics = metrics
        self.config = config

    def preco(self, con, pid, cents):
        con.execute("INSERT INTO catalog.price_latest (printing_id, price_cents, "
                    "from_foil) VALUES (?,?,0)", (pid, cents))

    def montar(self, com_excluidas=True):
        """Uma edição com uma Unit, um Legend e uma arte alternativa.

        Com `com_excluidas`, junta as duas que as listas de compra deixam de
        fora: uma signature (variante) e uma reimpressão de raridade showcase
        (raridade). As duas contam na percentagem e não na lista de compra —
        é exactamente a diferença que a linha do ecrã explica.
        """
        con = self.v.connect()
        self.v.add_printing(con, "tst-001-100", "TST", 1, "Uma Unit")
        self.v.add_printing(con, "tst-002-100", "TST", 2, "Um Legend",
                            card_type="Legend")
        self.v.add_printing(con, "tst-003a-100", "TST", 3, "Uma alt",
                            variant="a", kind="alt_art", rarity="epic")
        self.preco(con, "tst-001-100", 100)
        self.preco(con, "tst-002-100", 500)
        self.preco(con, "tst-003a-100", 900)
        if com_excluidas:
            self.v.add_printing(con, "tst-004-star-100", "TST", 4, "Uma signature",
                                variant="star", kind="signature", rarity="showcase")
            self.v.add_printing(con, "tst-005-100", "TST", 5, "Uma showcase",
                                rarity="showcase")
            self.preco(con, "tst-004-star-100", 20000)
            self.preco(con, "tst-005-100", 8000)
        self.v.rebuild(con)
        return con

    def faltam_no_playset(self, con):
        """As cópias que o último degrau da contagem diz que faltam."""
        return self.metrics.set_payload(con, "TST")["progress"]["levels"][-1]["missing"]

    def a_comprar(self, con):
        """As cópias que a wantlist da edição pede."""
        return self.a_subir.wantlist(con, "TST")["copies"]


class TestAListaNuncaPedeMaisDoQueAContagem(Base):

    def test_com_exclusoes_e_pendente(self):
        from riftvault import collection, pending
        con = self.montar()
        collection.adjust(con, "tst-001-100", 1, source="test")
        pending.add(con, "tst-002-100", 1)
        self.assertLessEqual(self.a_comprar(con), self.faltam_no_playset(con))
        con.close()

    def test_a_diferenca_sao_as_exclusoes_e_o_que_vem_a_caminho(self):
        from riftvault import pending
        con = self.montar()
        pending.add(con, "tst-001-100", 2)
        # showcase 3 (o playset da Unit) = 3 cópias excluídas das listas de
        # compra, mais as 2 que já vêm a caminho. A signature não entra na
        # conta de nenhum dos lados desde 2026-09-09: saiu da coleção.
        self.assertEqual(self.faltam_no_playset(con) - self.a_comprar(con), 3 + 2)
        con.close()

    def test_sem_exclusoes_nem_pendente_sao_o_mesmo_numero(self):
        con = self.montar(com_excluidas=False)
        self.assertEqual(self.a_comprar(con), self.faltam_no_playset(con))
        con.close()

    def test_a_contagem_conta_o_que_a_lista_de_compra_exclui(self):
        """A métrica não sabe do `a_subir.excluir` — e não pode passar a saber.

        A reimpressão showcase conta na barra e não se compra. A signature já
        não faz nem uma coisa nem outra: saiu da coleção a 2026-09-09, e isso é
        outra decisão — a que o `master_set.fora` responde.
        """
        con = self.montar()
        p = self.metrics.set_payload(con, "TST")
        contadas = {pr["id"] for g in p["groups"] for pr in g["printings"]
                    if self.metrics.conta_bloco(pr["block"])}
        self.assertIn("tst-005-100", contadas)
        self.assertNotIn("tst-004-star-100", contadas)
        # E nenhuma delas aparece na lista de compra.
        na_lista = {x["printing_id"] for x in self.a_subir.wantlist(con, "TST")["items"]}
        self.assertNotIn("tst-004-star-100", na_lista)
        self.assertNotIn("tst-005-100", na_lista)
        con.close()


if __name__ == "__main__":
    unittest.main()

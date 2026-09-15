"""Três blocos (André, 2026-09-14, à noite):

    «quero masterset com playset
     runas 1 de cada
     Alt Art, overnumbered, etc etc mete Playset na contagem
     mas só quero % de completo para masterset!
     o que é Alt Art e Overnumbered, etc etc é puramente coleção»

  1. MASTER SET — a sequência da edição. Alvo = playset do tipo, runas 1.
     Só isto conta para a percentagem e para os níveis.
  2. COLEÇÃO EXTRA — artes alternativas, runas especiais, sobrenumeradas,
     promos. Mesmo alvo. Aparecem, compram-se, vendem-se acima do alvo, NÃO
     contam para a percentagem.
  3. ESCONDIDAS — tokens e signatures. Não aparecem.

Corre contra cópias (`tests.fixture.Vault`): o config real só é LIDO, nunca
escrito — a lição de 11/09. Este ficheiro substituiu o `test_tudo_playset.py`,
que fixava a decisão da tarde desse dia («muda tudo para playset»).
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
        from riftvault import a_subir, metrics
        importlib.reload(metrics)
        importlib.reload(a_subir)
        self.metrics, self.a_subir = metrics, a_subir

    def edicao(self):
        """Uma de cada coisa: master set, coleção extra e escondidas."""
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

    MASTER = ["tst-001-100", "tst-002-100", "tst-003-100", "tst-004-100"]
    EXTRA = ["tst-001a-100", "tst-002a-100", "tst-r01", "tst-101-100", "tst-sp1-006"]
    ESCONDIDAS = ["tst-001-star-100", "tst-t01-100"]

    def linhas(self, con) -> dict:
        return {r["printing_id"]: r for r in con.execute("SELECT * FROM catalog.printings")}

    def alvos(self, con) -> dict[str, int]:
        return {pid: self.metrics.alvo(r) for pid, r in self.linhas(con).items()}


class TestAlvos(Base):
    def test_uma_unit_base_pede_3_e_conta(self):
        con = self.edicao()
        r = self.linhas(con)["tst-001-100"]
        self.assertEqual(self.metrics.alvo(r), 3)
        self.assertTrue(self.metrics.e_master(r))
        con.close()

    def test_uma_alt_art_de_unit_pede_3_e_nao_conta(self):
        con = self.edicao()
        r = self.linhas(con)["tst-001a-100"]
        self.assertEqual(self.metrics.alvo(r), 3)
        self.assertFalse(self.metrics.e_master(r))
        self.assertTrue(self.metrics.e_colecao(r))
        con.close()

    def test_uma_sobrenumerada_pede_3_e_nao_conta(self):
        con = self.edicao()
        r = self.linhas(con)["tst-101-100"]
        self.assertEqual(self.metrics.alvo(r), 3)
        self.assertFalse(self.metrics.e_master(r))
        self.assertTrue(self.metrics.e_colecao(r))
        self.assertEqual(self.metrics.bloco(r), "overnumbered")
        con.close()

    def test_uma_promo_pede_3_e_nao_conta(self):
        con = self.edicao()
        r = self.linhas(con)["tst-sp1-006"]
        self.assertEqual(self.metrics.alvo(r), 3)
        self.assertFalse(self.metrics.e_master(r))
        self.assertTrue(self.metrics.e_colecao(r))
        con.close()

    def test_a_runa_base_pede_1_e_conta(self):
        con = self.edicao()
        r = self.linhas(con)["tst-002-100"]
        self.assertEqual(self.metrics.alvo(r), 1)
        self.assertTrue(self.metrics.e_master(r))
        con.close()

    def test_a_runa_especial_pede_1_e_nao_conta(self):
        con = self.edicao()
        for pid in ("tst-002a-100", "tst-r01"):
            with self.subTest(pid=pid):
                r = self.linhas(con)[pid]
                self.assertEqual(self.metrics.alvo(r), 1)
                self.assertFalse(self.metrics.e_master(r))
                self.assertEqual(self.metrics.bloco(r), "rune_special")
        con.close()

    def test_o_legend_e_o_battlefield_pedem_1_que_e_o_playset_deles(self):
        con = self.edicao()
        a = self.alvos(con)
        self.assertEqual((a["tst-003-100"], a["tst-004-100"]), (1, 1))
        con.close()

    def test_o_alvo_e_o_mesmo_dentro_e_fora_da_percentagem(self):
        """*"Alt Art, overnumbered, etc etc mete Playset na contagem"*."""
        con = self.edicao()
        a = self.alvos(con)
        self.assertEqual(a["tst-001-100"], a["tst-001a-100"])
        self.assertEqual(a["tst-001-100"], a["tst-101-100"])
        self.assertEqual(a["tst-002-100"], a["tst-002a-100"])
        con.close()


class TestEscondidas(Base):
    def test_a_signature_e_o_token_nao_aparecem(self):
        con = self.edicao()
        p = self.metrics.set_payload(con, "TST")
        ids = {pr["id"] for g in p["groups"] for pr in g["printings"]}
        for pid in self.ESCONDIDAS:
            self.assertNotIn(pid, ids, pid)
        for pid in self.MASTER + self.EXTRA:
            self.assertIn(pid, ids, pid)
        con.close()

    def test_nem_no_separador_nem_nas_listas_de_compra(self):
        con = self.edicao()
        n = {s["id"]: s["n_printings"] for s in self.metrics.sets_payload(con)}
        self.assertEqual(n["TST"], len(self.MASTER) + len(self.EXTRA))
        escopo = self.a_subir.masterset(con)
        self.assertEqual(sorted(escopo), sorted(self.MASTER + self.EXTRA))
        con.close()


class TestPercentagem(Base):
    def test_o_denominador_e_so_o_master_set(self):
        con = self.edicao()
        p = self.metrics.set_payload(con, "TST")
        self.assertEqual(p["progress"]["master"]["total"], len(self.MASTER))
        blocos = {b["id"]: b for b in p["blocks"]}
        self.assertEqual([b["id"] for b in p["blocks"]],
                         ["master", "rune_special", "alt_art", "overnumbered", "special"])
        self.assertEqual([b["counts"] for b in p["blocks"]],
                         [True, False, False, False, False])
        self.assertEqual(blocos["alt_art"]["total"], 1)
        self.assertEqual(blocos["overnumbered"]["total"], 1)
        con.close()

    def test_a_percentagem_da_o_mesmo_com_e_sem_o_bloco_2(self):
        """Encher a coleção extra não mexe na barra nem nos níveis."""
        from riftvault import collection
        con = self.edicao()
        antes = self.metrics.set_payload(con, "TST")["progress"]
        for pid in self.EXTRA:
            collection.adjust(con, pid, 3, source="test")
        depois = self.metrics.set_payload(con, "TST")["progress"]
        self.assertEqual(antes["master"], depois["master"])
        self.assertEqual(antes["levels"], depois["levels"])
        # E os níveis medem só o master set: 3 + 1 + 1 + 1 cópias em falta.
        self.assertEqual(depois["levels"][-1]["total"], len(self.MASTER))
        self.assertEqual(depois["levels"][-1]["missing"], 3 + 1 + 1 + 1)
        con.close()

    def test_o_ultimo_nivel_e_a_barra(self):
        from riftvault import collection
        con = self.edicao()
        collection.adjust(con, "tst-001-100", 3, source="test")
        collection.adjust(con, "tst-002-100", 1, source="test")
        p = self.metrics.set_payload(con, "TST")["progress"]
        self.assertEqual(p["master"]["done"], 2)
        self.assertEqual(p["levels"][-1]["done"], 2)
        self.assertEqual(p["levels"][-1]["pct"], 50.0)
        niv = self.metrics.niveis_payload(con)
        self.assertEqual(niv["by_set"]["TST"][-1]["done"], 2)
        self.assertEqual(niv["max"], 3)
        con.close()


class TestListasDeCompra(Base):
    def test_a_colecao_extra_entra_a_playset(self):
        con = self.edicao()
        itens = {x["printing_id"]: x
                 for s in self.a_subir.master_faltas(con)["sets"] for x in s["items"]}
        self.assertEqual(sorted(itens), sorted(self.MASTER + self.EXTRA))
        self.assertEqual(itens["tst-001a-100"]["missing"], 3)
        self.assertEqual(itens["tst-101-100"]["missing"], 3)
        self.assertEqual(itens["tst-sp1-006"]["missing"], 3)
        self.assertEqual(itens["tst-002a-100"]["missing"], 1)
        self.assertEqual(itens["tst-002-100"]["missing"], 1)
        con.close()

    def test_a_wantlist_por_nivel_corta_a_colecao_extra_como_o_resto(self):
        con = self.edicao()
        w = self.a_subir.wantlist(con, "TST", nivel=1)
        por_pid = {x["printing_id"]: x["missing"] for x in w["items"]}
        self.assertEqual(por_pid["tst-101-100"], 1)
        self.assertEqual(por_pid["tst-001-100"], 1)
        con.close()


if __name__ == "__main__":
    unittest.main()

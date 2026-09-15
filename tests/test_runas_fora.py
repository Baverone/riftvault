"""As runas sem numeração de master set saem da Coleção (André, 2026-09-15).

    «Tira as Runas de aparecerem»
    «Saiem as runas todas e deixam de contar para masterset»
    «menos as que tem numeração de masterset»

O critério é a NUMERAÇÃO, não o tipo:

  - runa COM numeração de master set (`TST-002/100`, e a arte alternativa
    dela, `TST-002a/100`) — fica exactamente como estava: a base na sequência
    do master set, a alt art no bloco das runas especiais, a base a contar
    para a percentagem e para as listas de compra. (O alvo era 1 nesta ordem;
    passou a 3 nessa mesma tarde — *"vamos ate 3 como as outras cartas"* —,
    ver `test_runas_3.py`. Aqui fica só o que esta ordem decidiu: o bloco.)
  - runa SEM numeração (`TST-R01`, código sem `/tamanho`) — escondida, como os
    tokens e as signatures: não aparece na grelha, em bloco nenhum, no
    separador, em wantlist nenhuma nem no «A subir», e não conta para a
    percentagem. As cópias continuam no `copies` e no valor.

No config é o `-R` a passar de `master_set.fora_da_percentagem` para
`master_set.escondidas`. Corre contra cópias (`tests.fixture.Vault`); o config
real só é LIDO — o teste fixa o que ele diz hoje.
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

    RUNA_BASE = "tst-002-100"       # TST-002/100 — numerada, sequência
    RUNA_ALT = "tst-002a-100"       # TST-002a/100 — numerada, runas especiais
    RUNA_PROMO = "tst-r01"          # TST-R01 — sem numeração: escondida
    UNIT = "tst-001-100"

    def edicao(self):
        con = self.v.connect()
        v = self.v
        v.add_printing(con, self.UNIT, "TST", 1, "Defy", size=100, api_sort=1)
        v.add_printing(con, self.RUNA_BASE, "TST", 2, "Fury Rune",
                       card_type="Rune", size=100, api_sort=2)
        v.add_printing(con, self.RUNA_ALT, "TST", 2, "Fury Rune",
                       card_type="Rune", variant="a", kind="alt_art", size=100,
                       api_sort=3)
        v.add_printing(con, self.RUNA_PROMO, "TST", 1, "Body Rune", card_type="Rune",
                       variant="r01", kind="rune_promo", lane="r",
                       codigo="TST-R01", api_sort=4)
        v.rebuild(con)
        return con

    def linha(self, con, pid):
        return con.execute("SELECT * FROM catalog.printings WHERE printing_id = ?",
                           (pid,)).fetchone()

    def ids_na_grelha(self, con) -> set[str]:
        p = self.metrics.set_payload(con, "TST")
        return {pr["id"] for g in p["groups"] for pr in g["printings"]}


class TestConfig(Base):
    def test_o_R_esta_nas_escondidas_e_nao_na_colecao_extra(self):
        self.assertIn("rune_promo", self.metrics.kinds_escondidas())
        # A arte alternativa continua a ser coleção extra (aparece, não conta).
        self.assertIn("alt_art", self.metrics.kinds_fora())
        self.assertNotIn("alt_art", self.metrics.kinds_escondidas())

    def test_um_valor_desconhecido_continua_a_rebentar(self):
        from riftvault import config
        cfg = {**config.load(), "master_set": {"escondidas": ["-R", "-Q"]}}
        with self.assertRaises(ValueError):
            self.metrics.kinds_escondidas(cfg)


class TestRunaSemNumeracao(Base):
    def test_nao_aparece_na_grelha_nem_em_bloco_nenhum(self):
        from riftvault import collection
        con = self.edicao()
        collection.adjust(con, self.RUNA_PROMO, 2, source="test")
        self.assertTrue(self.metrics.escondida(self.linha(con, self.RUNA_PROMO)))
        self.assertNotIn(self.RUNA_PROMO, self.ids_na_grelha(con))
        p = self.metrics.set_payload(con, "TST")
        # Só a alt art enche o bloco das runas especiais; nem «rune_promo» nem
        # «runas especiais» com a promo lá dentro.
        self.assertNotIn("rune_promo", [b["id"] for b in p["blocks"]])
        blocos = {b["id"]: b for b in p["blocks"]}
        self.assertEqual(blocos["rune_special"]["total"], 1)
        self.assertIn("rune_promo", p["hidden_kinds"])
        con.close()

    def test_nem_no_separador(self):
        con = self.edicao()
        n = {s["id"]: s["n_printings"] for s in self.metrics.sets_payload(con)}
        self.assertEqual(n["TST"], 3)
        con.close()

    def test_nem_no_denominador_nem_nos_niveis(self):
        con = self.edicao()
        p = self.metrics.set_payload(con, "TST")
        # A Unit e a runa base: só isso conta.
        self.assertEqual(p["progress"]["master"]["total"], 2)
        self.assertEqual(p["progress"]["levels"][-1]["total"], 2)
        self.assertFalse(self.metrics.e_master(self.linha(con, self.RUNA_PROMO)))
        con.close()

    def test_nem_em_wantlist_nenhuma_nem_no_a_subir(self):
        con = self.edicao()
        for nivel in (None, 1, 2, 3):
            for sid in (None, "TST"):
                with self.subTest(nivel=nivel, set_id=sid):
                    w = self.a_subir.wantlist(con, sid, nivel=nivel)
                    self.assertNotIn(self.RUNA_PROMO,
                                     {x["printing_id"] for x in w["items"]})
                    self.assertNotIn("Body Rune", w["text"])
        self.assertNotIn(self.RUNA_PROMO, self.a_subir.masterset(con))
        faltas = {x["printing_id"] for s in self.a_subir.master_faltas(con)["sets"]
                  for x in s["items"]}
        self.assertNotIn(self.RUNA_PROMO, faltas)
        subir = {x["printing_id"] for x in self.a_subir.calcular(con).get("items", [])}
        self.assertNotIn(self.RUNA_PROMO, subir)
        con.close()

    def test_continua_no_copies_e_no_valor(self):
        from riftvault import collection
        con = self.edicao()
        collection.adjust(con, self.RUNA_PROMO, 2, source="test")
        con.execute("INSERT INTO catalog.price_latest (printing_id, price_cents, day) "
                    "VALUES (?, 150, '2026-09-15')", (self.RUNA_PROMO,))
        con.commit()
        qty = con.execute("SELECT qty FROM copies WHERE printing_id = ?",
                          (self.RUNA_PROMO,)).fetchone()[0]
        self.assertEqual(qty, 2)
        p = self.metrics.set_payload(con, "TST")
        self.assertEqual(p["progress"]["value"]["owned"], 300)
        from riftvault import prices
        self.assertEqual(prices.collection_value(con)["cents"], 300)
        con.close()


class TestRunaComNumeracao(Base):
    def test_a_base_fica_na_sequencia_e_conta(self):
        con = self.edicao()
        r = self.linha(con, self.RUNA_BASE)
        self.assertEqual(self.metrics.bloco(r), "master")
        self.assertTrue(self.metrics.e_master(r))
        self.assertFalse(self.metrics.escondida(r))
        self.assertIn(self.RUNA_BASE, self.ids_na_grelha(con))
        con.close()

    def test_a_base_continua_nas_listas_de_compra(self):
        con = self.edicao()
        for nivel in (None, 1, 2, 3):
            with self.subTest(nivel=nivel):
                w = self.a_subir.wantlist(con, "TST", nivel=nivel)
                por_pid = {x["printing_id"]: x["missing"] for x in w["items"]}
                # A runa numerada pede o mesmo que a Unit (3 desde 2026-09-15).
                self.assertEqual(por_pid[self.RUNA_BASE], por_pid[self.UNIT])
                self.assertEqual(por_pid[self.UNIT], min(nivel or 3, 3))
        con.close()

    def test_a_arte_alternativa_fica_nas_runas_especiais_como_estava(self):
        con = self.edicao()
        r = self.linha(con, self.RUNA_ALT)
        self.assertEqual(self.metrics.bloco(r), "rune_special")
        self.assertFalse(self.metrics.e_master(r))
        self.assertFalse(self.metrics.escondida(r))
        self.assertIn(self.RUNA_ALT, self.ids_na_grelha(con))
        con.close()

    def test_a_unit_base_continua_em_tudo(self):
        con = self.edicao()
        r = self.linha(con, self.UNIT)
        self.assertEqual((self.metrics.bloco(r), self.metrics.alvo(r)), ("master", 3))
        self.assertTrue(self.metrics.e_master(r))
        self.assertIn(self.UNIT, self.a_subir.masterset(con))
        con.close()


class TestVoltarAtras(Base):
    def test_tirar_o_R_das_escondidas_poe_a_promo_de_volta(self):
        """Uma linha de config, e a runa promo volta ao bloco das especiais."""
        from riftvault import config
        cfg = {**config.load(),
               "master_set": {"fora_da_percentagem": ["a", "-R", "overnumbered", "promo"],
                              "escondidas": ["-T", "*"]}}
        con = self.edicao()
        r = self.linha(con, self.RUNA_PROMO)
        self.assertFalse(self.metrics.escondida(r, cfg))
        self.assertEqual(self.metrics.bloco(r, cfg), "rune_special")
        self.assertFalse(self.metrics.e_master(r, cfg))
        con.close()


if __name__ == "__main__":
    unittest.main()

"""As sobrenumeradas e as promos voltam a 1 de cada (André, 2026-09-15):

    «overnumbered e promos (SP) voltamos a 1 de cada»
    «se eu tiver mais adiciono na mesma»

Dois blocos da coleção extra deixam de pedir o playset do tipo e passam a
pedir **1** — `master_set.um_de_cada`, a terceira lista do `master_set`, com
a gramática das outras duas. A segunda frase manda na leitura do número: 1 é
o que ele quer TER, não um tecto. Uma segunda cópia aparece, conta no valor
e nada a marca como a mais.

O que NÃO muda, e este ficheiro fixa: continuam fora da percentagem e de
todas as listas de compra; as artes alternativas ficam a playset (pediram 1
de 2026-09-16 a 2026-09-18 — *"muda novamente: Alt Art para playset,
overnumbered continua 1 de cada"* —, e é o `um_de_cada` que o diz); as runas
ficam onde a ordem das runas as deixou.

**As promos andaram**: playset a 09-14, 1 a 09-15, playset durante 2026-09-18
(*"as promos SP podes meter 3 de cada"* — o `promo` saiu da lista) e **1 outra
vez desde 2026-09-19** (*"as Promo passam a 1 de cada ao inves de playset"*
— o `promo` voltou). O teste da promo fixa o 1 e que tirar o `promo` da lista
a volta a pôr ao playset.

Corre contra cópias (`tests.fixture.Vault`): o config real só é LIDO, nunca
escrito. Os testes que mudam o config passam um dicionário, não tocam no
ficheiro.
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

    OVER = "tst-101-100"       # a «101/100», sobrenumerada
    PROMO = "tst-sp1-006"      # a `TST-SP1/006`
    ALT = "tst-001a-100"       # arte alternativa de Unit — fica a playset
    RUNA_ALT = "tst-002a-100"  # arte alternativa de runa — 1, pela regra das runas
    BASE = "tst-001-100"       # a Unit da sequência — 3

    def edicao(self):
        """Uma Unit com arte alternativa e reimpressão sobrenumerada, uma runa
        com arte alternativa, um Legend sobrenumerado e uma promo."""
        con = self.v.connect()
        v = self.v
        v.add_printing(con, self.BASE, "TST", 1, "Defy", size=100, api_sort=1)
        v.add_printing(con, self.ALT, "TST", 1, "Defy", variant="a",
                       kind="alt_art", rarity="showcase", size=100, api_sort=2)
        v.add_printing(con, "tst-002-100", "TST", 2, "Fury Rune",
                       card_type="Rune", size=100, api_sort=3)
        v.add_printing(con, self.RUNA_ALT, "TST", 2, "Fury Rune",
                       card_type="Rune", variant="a", kind="alt_art", size=100,
                       api_sort=4)
        v.add_printing(con, "tst-003-100", "TST", 3, "Um Legend",
                       card_type="Legend", size=100, api_sort=5)
        v.add_printing(con, self.OVER, "TST", 101, "Defy", rarity="showcase",
                       size=100, api_sort=6)
        v.add_printing(con, "tst-102-100", "TST", 102, "Um Legend",
                       card_type="Legend", rarity="showcase", size=100, api_sort=7)
        v.add_printing(con, self.PROMO, "TST", 1, "Uma Promo", variant="sp1",
                       kind="special", lane="sp", codigo="TST-SP1/006",
                       rarity="epic", api_sort=8)
        v.rebuild(con)
        return con

    def linhas(self, con) -> dict:
        return {r["printing_id"]: r for r in con.execute("SELECT * FROM catalog.printings")}

    def tiles(self, con) -> tuple[dict, dict]:
        p = self.metrics.set_payload(con, "TST")
        return p, {pr["id"]: pr for g in p["groups"] for pr in g["printings"]}

    def preco(self, con, pid: str, cents: int):
        con.execute("INSERT OR REPLACE INTO catalog.price_latest "
                    "(printing_id, price_cents, day) VALUES (?, ?, 'hoje')",
                    (pid, cents))


class TestAlvo(Base):
    def test_a_sobrenumerada_pede_1(self):
        con = self.edicao()
        r = self.linhas(con)[self.OVER]
        self.assertTrue(self.metrics.e_um_de_cada(r))
        self.assertEqual(self.metrics.alvo(r), 1)
        # Uma Unit igual, na sequência, continua a pedir 3 — é só o número
        # que passa o tamanho da edição que a põe a 1.
        self.assertEqual(self.metrics.alvo(self.linhas(con)[self.BASE]), 3)
        con.close()

    def test_a_promo_pede_1_desde_2026_09_19(self):
        """Pediu 1 de 2026-09-15 a 2026-09-18, o playset durante 2026-09-18
        (*"as promos SP podes meter 3 de cada"*) e 1 outra vez desde
        2026-09-19 (*"as Promo passam a 1 de cada ao inves de playset"*). É a
        lista que manda: tirar o `promo` do `um_de_cada` volta a pô-la ao
        playset — não há número cravado."""
        from riftvault import config
        con = self.edicao()
        r = self.linhas(con)[self.PROMO]
        self.assertTrue(self.metrics.e_um_de_cada(r))
        self.assertEqual(self.metrics.alvo(r), 1)
        cfg = config.load()
        self.assertIn("promo", cfg["master_set"]["um_de_cada"])
        c = {**cfg, "master_set": {**cfg["master_set"], "um_de_cada": ["overnumbered"]}}
        self.assertFalse(self.metrics.e_um_de_cada(r, c))
        self.assertEqual(self.metrics.alvo(r, c), 3)
        self.assertEqual(self.metrics.rotulo("special", c), "Coleção — promos — playset")
        con.close()

    def test_a_arte_alternativa_pede_o_playset_desde_2026_09_18(self):
        """Ficou a playset a 09-15 porque ele não a nomeou; a 09-16 nomeou-a
        (*"Alt Art e Overnumbered e assim quero apenas 1 de cada"*) e pediu 1;
        a 09-18 voltou atrás: *"muda novamente: Alt Art para playset,
        overnumbered continua 1 de cada"*. É a lista do config que o diz — o
        `a` saiu do `um_de_cada` —, e escrevê-lo lá volta a pô-la a 1."""
        from riftvault import config
        con = self.edicao()
        r = self.linhas(con)[self.ALT]
        self.assertFalse(self.metrics.e_um_de_cada(r))
        self.assertEqual(self.metrics.alvo(r), 3)
        cfg = config.load()
        self.assertNotIn("a", cfg["master_set"]["um_de_cada"])
        c = {**cfg, "master_set": {**cfg["master_set"],
                                   "um_de_cada": ["a", "overnumbered", "promo"]}}
        self.assertEqual(self.metrics.alvo(r, c), 1)
        self.assertEqual(self.metrics.rotulo("alt_art", c),
                         "Coleção — artes alternativas — 1 de cada")
        con.close()

    def test_as_runas_base_nao_sao_um_de_cada(self):
        """O `um_de_cada` não toca na runa BASE: pede o do tipo — 3 desde a
        ordem seguinte do mesmo dia (`test_runas_3.py`). A arte alternativa da
        runa está RETIRADA desde 2026-09-17 (`test_runas_alt_fora.py`): não
        aparece na página, seja qual for o alvo que o `um_de_cada` lhe desse."""
        con = self.edicao()
        a = {pid: self.metrics.alvo(r) for pid, r in self.linhas(con).items()}
        self.assertEqual(a["tst-002-100"], 3)
        self.assertFalse(self.metrics.e_um_de_cada(self.linhas(con)["tst-002-100"]))
        self.assertTrue(self.metrics.retirada(self.linhas(con)[self.RUNA_ALT]))
        self.assertTrue(self.metrics.escondida(self.linhas(con)[self.RUNA_ALT]))
        con.close()

    def test_um_legend_sobrenumerado_ja_pedia_1_e_continua(self):
        con = self.edicao()
        self.assertEqual(self.metrics.alvo(self.linhas(con)["tst-102-100"]), 1)
        con.close()

    def test_o_cabecalho_dos_dois_blocos_diz_1_de_cada(self):
        self.assertEqual(self.metrics.rotulo("overnumbered"),
                         "Coleção — sobrenumeradas — 1 de cada")
        # O das promos disse «playset» só durante 2026-09-18.
        self.assertEqual(self.metrics.rotulo("special"), "Coleção — promos — 1 de cada")
        # E o das artes alternativas diz «playset» desde 2026-09-18 (disse «1
        # de cada» de 2026-09-16 a 2026-09-18) — só isso: o alvo não sobe com
        # os decks (`test_voltar_1.py`).
        self.assertEqual(self.metrics.rotulo("alt_art"),
                         "Coleção — artes alternativas — playset")

    def test_sem_a_lista_no_config_voltam_ao_playset(self):
        """`um_de_cada` é só o alvo: tirá-la do config é o mundo de 09-14."""
        from riftvault import config
        cfg = config.load()
        ms = {k: v for k, v in cfg["master_set"].items() if k != "um_de_cada"}
        cfg = {**cfg, "master_set": ms}
        con = self.edicao()
        r = self.linhas(con)
        self.assertEqual(self.metrics.alvo(r[self.OVER], cfg), 3)
        self.assertEqual(self.metrics.alvo(r[self.PROMO], cfg), 3)
        self.assertEqual(self.metrics.rotulo("special", cfg), "Coleção — promos — playset")
        # … e o bloco e a percentagem não sabem da lista, num caso e no outro.
        self.assertEqual(self.metrics.bloco(r[self.OVER], cfg), "overnumbered")
        self.assertFalse(self.metrics.e_master(r[self.PROMO], cfg))
        con.close()

    def test_a_lista_aceita_a_gramatica_das_outras_e_rebenta_no_resto(self):
        from riftvault import config
        cfg = config.load()
        con = self.edicao()
        r = self.linhas(con)
        for escrita in (["-SP"], ["special"], ["promo"]):
            with self.subTest(escrita=escrita):
                c = {**cfg, "master_set": {**cfg["master_set"], "um_de_cada": escrita}}
                self.assertEqual(self.metrics.alvo(r[self.PROMO], c), 1)
                self.assertEqual(self.metrics.alvo(r[self.OVER], c), 3)
        c = {**cfg, "master_set": {**cfg["master_set"], "um_de_cada": ["sp7"]}}
        with self.assertRaises(ValueError):
            self.metrics.alvo(r[self.PROMO], c)
        con.close()

    def test_sem_a_linha_do_catalogo_so_a_variante_responde(self):
        """Os quatro escalares chegam para a promo; a sobrenumerada precisa do
        código impresso, e sem ele a resposta é o playset."""
        self.assertEqual(self.metrics.master_target("x", "special", "Unit", False), 1)
        self.assertEqual(self.metrics.master_target("x", "base", "Unit", False), 3)


class TestUmaCopiaEDuas(Base):
    """*"se eu tiver mais adiciono na mesma"* — ter mais do que 1 não é erro."""

    def test_com_uma_copia_esta_completa(self):
        from riftvault import collection
        con = self.edicao()
        collection.adjust(con, self.OVER, 1, source="test")
        collection.adjust(con, self.PROMO, 1, source="test")
        p, t = self.tiles(con)
        for pid in (self.OVER, self.PROMO):
            self.assertEqual((t[pid]["qty"], t[pid]["target"]), (1, 1), pid)
            self.assertGreaterEqual(t[pid]["qty"], t[pid]["target"])
        blocos = {b["id"]: b for b in p["blocks"]}
        # As duas sobrenumeradas: a Unit (1/1) e o Legend (0/1).
        self.assertEqual((blocos["overnumbered"]["owned"], blocos["overnumbered"]["done"],
                          blocos["overnumbered"]["total"]), (1, 1, 2))
        self.assertEqual((blocos["special"]["owned"], blocos["special"]["done"],
                          blocos["special"]["total"]), (1, 1, 1))
        # Com alvo 1 o cabeçalho não precisa da segunda conta.
        self.assertEqual(blocos["overnumbered"]["max_target"], 1)
        self.assertEqual(blocos["special"]["max_target"], 1)
        con.close()

    def test_com_duas_copias_continua_a_aparecer_e_nada_a_marca_como_a_mais(self):
        from riftvault import collection
        con = self.edicao()
        self.preco(con, self.OVER, 1000)
        self.preco(con, self.PROMO, 500)
        collection.adjust(con, self.OVER, 1, source="test")
        collection.adjust(con, self.PROMO, 1, source="test")
        p1, t1 = self.tiles(con)
        collection.adjust(con, self.OVER, 1, source="test")
        collection.adjust(con, self.PROMO, 1, source="test")
        p2, t2 = self.tiles(con)
        for pid in (self.OVER, self.PROMO):
            # O tile está lá, com «2/1»: é o mesmo tile de antes, com o mesmo
            # conjunto de campos — não ganhou nenhuma marca de excesso.
            self.assertEqual((t2[pid]["qty"], t2[pid]["target"]), (2, 1), pid)
            self.assertEqual(set(t2[pid]), set(t1[pid]), pid)
            self.assertEqual(t2[pid]["block"], t1[pid]["block"])
        # O bloco conta exactamente o mesmo que com uma cópia.
        b1 = {b["id"]: b for b in p1["blocks"]}
        b2 = {b["id"]: b for b in p2["blocks"]}
        self.assertEqual(b2["overnumbered"], b1["overnumbered"])
        self.assertEqual(b2["special"], b1["special"])
        # E a segunda cópia vale: 2 × 10 € + 2 × 5 €.
        self.assertEqual(p1["progress"]["value"]["owned"], 1500)
        self.assertEqual(p2["progress"]["value"]["owned"], 3000)
        # O «se estivesse completa» não as leva num caso nem no outro — não
        # são master set.
        self.assertEqual(p2["progress"]["value"]["full"], p1["progress"]["value"]["full"])
        con.close()

    def test_o_valor_da_colecao_leva_as_duas_copias(self):
        """O `riftvault value` lê o `copies` inteiro, sem olhar ao alvo."""
        from riftvault import collection, prices
        con = self.edicao()
        self.preco(con, self.PROMO, 500)
        collection.adjust(con, self.PROMO, 3, source="test")
        self.assertEqual(prices.collection_value(con)["cents"], 1500)
        con.close()


class TestForaDasContas(Base):
    """Baixar o alvo não as traz de volta à percentagem nem às compras."""

    def test_nao_contam_para_a_percentagem_com_zero_uma_ou_duas(self):
        from riftvault import collection
        con = self.edicao()
        r = self.linhas(con)
        self.assertFalse(self.metrics.e_master(r[self.OVER]))
        self.assertFalse(self.metrics.e_master(r[self.PROMO]))
        for n in (1, 1):
            collection.adjust(con, self.OVER, n, source="test")
            collection.adjust(con, self.PROMO, n, source="test")
            p, _ = self.tiles(con)
            # O master set são a Unit, a runa e o Legend: 0 de 3, sempre.
            self.assertEqual(p["progress"]["master"], {"done": 0, "total": 3})
            self.assertEqual(p["progress"]["levels"][-1]["total"], 3)
            self.assertEqual(p["progress"]["levels"][-1]["done"], 0)
        blocos = {b["id"]: b for b in p["blocks"]}
        self.assertFalse(blocos["overnumbered"]["counts"])
        self.assertFalse(blocos["special"]["counts"])
        con.close()

    def test_nao_entram_em_lista_de_compra_nenhuma(self):
        """Com zero cópias — que é quando uma lista as pediria."""
        con = self.edicao()
        extra = {self.OVER, self.PROMO, "tst-102-100"}
        # A lista «Master set» e a wantlist da edição / de tudo / por nível.
        mf = {x["printing_id"] for s in self.a_subir.master_faltas(con)["sets"]
              for x in s["items"]}
        self.assertFalse(mf & extra, mf & extra)
        for set_id in ("TST", None):
            for nivel in (None, 1, 2, 3):
                with self.subTest(set_id=set_id, nivel=nivel):
                    w = self.a_subir.wantlist(con, set_id, nivel=nivel)
                    pids = {x["printing_id"] for x in w["items"]}
                    self.assertFalse(pids & extra, pids & extra)
                    self.assertNotIn("Uma Promo", w["text"])
                    self.assertNotIn("TST-101", w["text"])
        # A «A subir» parte do mesmo âmbito.
        seguidas = {x["printing_id"] for x in self.a_subir.calcular(con).get("items", [])}
        self.assertFalse(seguidas & extra, seguidas & extra)
        # E a página diz que as tirou por BLOCO, não por alvo.
        scope = self.a_subir.master_faltas(con)["scope"]
        self.assertIn("overnumbered", scope["excluded_blocks"])
        self.assertIn("special", scope["excluded_blocks"])
        con.close()


if __name__ == "__main__":
    unittest.main()

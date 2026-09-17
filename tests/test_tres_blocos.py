"""Três blocos (André, 2026-09-14, à noite):

    «quero masterset com playset
     runas 1 de cada
     Alt Art, overnumbered, etc etc mete Playset na contagem
     mas só quero % de completo para masterset!
     o que é Alt Art e Overnumbered, etc etc é puramente coleção»

  1. MASTER SET — a sequência da edição. Alvo = playset do tipo — runas
     incluídas desde 2026-09-15 (*"vamos ate 3 como as outras cartas"*, ver
     `test_runas_3.py`; o «runas 1 de cada» desta frase foi revogado).
     Só isto conta para a percentagem e para os níveis.
  2. COLEÇÃO EXTRA — artes alternativas, runas especiais, sobrenumeradas,
     promos. O «mete Playset» foi revogado às fatias: sobrenumeradas e promos
     a 1 de cada a 2026-09-15 (`test_alvo_1.py`), artes alternativas (runas
     incluídas) a 2026-09-16 (*"Alt Art e Overnumbered e assim quero apenas 1
     de cada"*, `test_altart_decks.py` — sobe ao que os decks pedem). Aparecem
     na grelha com «tenho N de alvo», vendem-se
     acima do alvo, NÃO contam para a percentagem e — desde 2026-09-15 — NÃO
     entram em lista de compra nenhuma: *"sobrenumeradas não entram na
     wantlist, nem na % de coleção completa; apenas pedi para ser feito track
     de playset para eu saber exatamente quantas tenho"*. Acompanhar não é
     querer comprar (`listas_de_compra.so_master_set`).
  3. ESCONDIDAS — tokens e signatures. Não aparecem.

Corre contra cópias (`tests.fixture.Vault`): o config real só é LIDO, nunca
escrito — a lição de 11/09. Este ficheiro substituiu o `test_tudo_playset.py`,
que fixava a decisão da tarde desse dia («muda tudo para playset»).
"""

from __future__ import annotations

import importlib
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.fixture import Vault

SEM_RETIRADAS = {"runas_especiais": {"tipos": ["Rune"], "excepto": ["base"],
                                     "retiradas": []}}


class Base(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.close)
        from riftvault import a_subir, config, metrics
        importlib.reload(metrics)
        importlib.reload(a_subir)
        self.metrics, self.a_subir = metrics, a_subir
        self.config = config
        # Estes testes descrevem os três blocos com a arte alternativa da runa
        # no bloco das runas especiais — o mecanismo continua a existir, mas
        # desde 2026-09-17 à tarde essa alt art está RETIRADA de tudo
        # (`runas_especiais.retiradas: ["a"]`, `test_runas_alt_fora.py`) e o
        # bloco fica vazio no catálogo real. Aqui desliga-se a retirada para
        # o bloco continuar testável, como no `test_masterset.py`.
        self.com_config(SEM_RETIRADAS)

    def com_config(self, extra: dict):
        import os
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
    EXTRA = ["tst-001a-100", "tst-002a-100", "tst-101-100", "tst-sp1-006"]
    # A runa promo `TST-R01` (sem numeração de master set) está escondida desde
    # 2026-09-15 — ver `test_runas_fora.py`.
    ESCONDIDAS = ["tst-001-star-100", "tst-t01-100", "tst-r01"]

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

    def test_uma_alt_art_de_unit_pede_1_e_nao_conta(self):
        """Pediu 3 de 2026-09-14 à noite até 2026-09-16 (*"Alt Art e
        Overnumbered e assim quero apenas 1 de cada"*); sobe ao que os decks
        pedem, e aqui nenhum a pede — ver `test_altart_decks.py`."""
        con = self.edicao()
        r = self.linhas(con)["tst-001a-100"]
        self.assertEqual(self.metrics.alvo(r), 1)
        self.assertFalse(self.metrics.e_master(r))
        self.assertTrue(self.metrics.e_colecao(r))
        con.close()

    def test_uma_sobrenumerada_pede_1_e_nao_conta(self):
        """Pediu 3 de 2026-09-14 à noite até 2026-09-15 (*"overnumbered e
        promos (SP) voltamos a 1 de cada"*) — ver `test_alvo_1.py`."""
        con = self.edicao()
        r = self.linhas(con)["tst-101-100"]
        self.assertEqual(self.metrics.alvo(r), 1)
        self.assertFalse(self.metrics.e_master(r))
        self.assertTrue(self.metrics.e_colecao(r))
        self.assertEqual(self.metrics.bloco(r), "overnumbered")
        con.close()

    def test_uma_promo_pede_1_e_nao_conta(self):
        con = self.edicao()
        r = self.linhas(con)["tst-sp1-006"]
        self.assertEqual(self.metrics.alvo(r), 1)
        self.assertFalse(self.metrics.e_master(r))
        self.assertTrue(self.metrics.e_colecao(r))
        con.close()

    def test_a_runa_base_pede_3_e_conta(self):
        con = self.edicao()
        r = self.linhas(con)["tst-002-100"]
        self.assertEqual(self.metrics.alvo(r), 3)
        self.assertTrue(self.metrics.e_master(r))
        con.close()

    def test_a_runa_especial_pede_1_e_nao_conta(self):
        """A runa especial é a arte alternativa da runa: 1 de cada desde
        2026-09-16, como qualquer alt art (o 3 é da runa BASE, `test_runas_3`)."""
        con = self.edicao()
        r = self.linhas(con)["tst-002a-100"]
        self.assertEqual(self.metrics.alvo(r), 1)
        self.assertFalse(self.metrics.e_master(r))
        self.assertEqual(self.metrics.bloco(r), "rune_special")
        # A runa promo, sem numeração, já não é runa especial: está escondida.
        r = self.linhas(con)["tst-r01"]
        self.assertTrue(self.metrics.escondida(r))
        self.assertFalse(self.metrics.e_master(r))
        con.close()

    def test_o_legend_e_o_battlefield_pedem_1_que_e_o_playset_deles(self):
        con = self.edicao()
        a = self.alvos(con)
        self.assertEqual((a["tst-003-100"], a["tst-004-100"]), (1, 1))
        con.close()

    def test_a_colecao_extra_pede_1_e_o_master_set_o_playset(self):
        """*"Alt Art, overnumbered, etc etc mete Playset na contagem"*
        (2026-09-14) foi revogado às fatias: as sobrenumeradas e as promos a
        2026-09-15 (`test_alvo_1.py`), as artes alternativas a 2026-09-16
        (`test_altart_decks.py`). Hoje a coleção extra pede toda 1 de cada e o
        master set continua a pedir o playset — dois conjuntos separados."""
        con = self.edicao()
        a = self.alvos(con)
        self.assertEqual((a["tst-001-100"], a["tst-002-100"]), (3, 3))
        self.assertEqual((a["tst-001a-100"], a["tst-002a-100"], a["tst-101-100"],
                          a["tst-sp1-006"]), (1, 1, 1, 1))
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
        # E os níveis medem só o master set: 3 + 3 + 1 + 1 cópias em falta (a
        # Unit e a runa a 3, o Battlefield e o Legend a 1).
        self.assertEqual(depois["levels"][-1]["total"], len(self.MASTER))
        self.assertEqual(depois["levels"][-1]["missing"], 3 + 3 + 1 + 1)
        con.close()

    def test_o_ultimo_nivel_e_a_barra(self):
        from riftvault import collection
        con = self.edicao()
        collection.adjust(con, "tst-001-100", 3, source="test")
        collection.adjust(con, "tst-002-100", 3, source="test")
        p = self.metrics.set_payload(con, "TST")["progress"]
        self.assertEqual(p["master"]["done"], 2)
        self.assertEqual(p["levels"][-1]["done"], 2)
        self.assertEqual(p["levels"][-1]["pct"], 50.0)
        niv = self.metrics.niveis_payload(con)
        self.assertEqual(niv["by_set"]["TST"][-1]["done"], 2)
        self.assertEqual(niv["max"], 3)
        con.close()


class TestListasDeCompra(Base):
    """As listas de compra são SÓ o master set (André, 2026-09-15).

    A coleção extra tem alvo de playset para ele VER quantas tem, não para
    comprar. Até à noite de 2026-09-14 entrava inteira nas listas e a wantlist
    passou de 3 337 € para 30 646 €; este ficheiro descrevia esse mundo.
    """

    def test_a_colecao_extra_nao_entra_na_lista_do_master_set(self):
        con = self.edicao()
        p = self.a_subir.master_faltas(con)
        itens = {x["printing_id"]: x for s in p["sets"] for x in s["items"]}
        self.assertEqual(sorted(itens), sorted(self.MASTER))
        # O master set continua a pedir o playset do tipo — runas incluídas.
        self.assertEqual(itens["tst-001-100"]["missing"], 3)
        self.assertEqual(itens["tst-002-100"]["missing"], 3)
        self.assertEqual(itens["tst-003-100"]["missing"], 1)
        self.assertEqual(itens["tst-004-100"]["missing"], 1)
        # E a página diz o que tirou, e de que bloco — uma lista que encolhe
        # sem explicação parece um erro de contagem.
        self.assertTrue(p["scope"]["so_master_set"])
        self.assertEqual(p["scope"]["printings"], len(self.MASTER))
        por_bloco = {x["criterio"]: x["n"] for x in p["scope"]["excluded_by"]}
        self.assertEqual(por_bloco, {"rune_special": 1, "alt_art": 1,
                                     "overnumbered": 1, "special": 1})
        self.assertEqual(sorted(p["scope"]["excluded_blocks"]),
                         ["alt_art", "overnumbered", "rune_special", "special"])
        con.close()

    def test_a_colecao_extra_continua_na_grelha_com_o_alvo_dela(self):
        """*"apenas pedi para ser feito track"*: a coleção extra continua na
        grelha com o alvo dela — 1 de cada em todos os blocos desde 2026-09-16
        (a sobrenumerada desde 2026-09-15) —, e com zero cópias continua a não
        ser para comprar."""
        from riftvault import collection
        con = self.edicao()
        collection.adjust(con, "tst-001a-100", 1, source="test")
        p = self.metrics.set_payload(con, "TST")
        tiles = {pr["id"]: pr for g in p["groups"] for pr in g["printings"]}
        self.assertEqual((tiles["tst-001a-100"]["qty"], tiles["tst-001a-100"]["target"]), (1, 1))
        self.assertEqual((tiles["tst-101-100"]["qty"], tiles["tst-101-100"]["target"]), (0, 1))
        self.assertEqual(tiles["tst-002a-100"]["target"], 1)
        # … e mesmo com 1 de 1 (a alt art) ou 0 de 1 (a sobrenumerada), nada
        # disto é para comprar.
        faltas = {x["printing_id"] for s in self.a_subir.master_faltas(con)["sets"]
                  for x in s["items"]}
        self.assertNotIn("tst-001a-100", faltas)
        self.assertNotIn("tst-101-100", faltas)
        con.close()

    def test_nem_na_wantlist_da_edicao_nem_por_nivel(self):
        con = self.edicao()
        for nivel in (None, 1, 2, 3):
            with self.subTest(nivel=nivel):
                w = self.a_subir.wantlist(con, "TST", nivel=nivel)
                por_pid = {x["printing_id"]: x["missing"] for x in w["items"]}
                self.assertEqual(sorted(por_pid), sorted(self.MASTER))
                # A Unit e a runa seguem o degrau; as de alvo 1 saem iguais
                # em todos.
                self.assertEqual(por_pid["tst-001-100"], min(nivel or 3, 3))
                self.assertEqual(por_pid["tst-002-100"], min(nivel or 3, 3))
                self.assertEqual(por_pid["tst-004-100"], 1)
                for pid in self.EXTRA:
                    self.assertNotIn(pid, w["text"], pid)
        con.close()

    def test_nem_no_a_subir(self):
        """O «A subir» parte do mesmo âmbito: a coleção extra não é seguida."""
        con = self.edicao()
        p = self.a_subir.calcular(con)
        self.assertTrue(p["scope"]["so_master_set"])
        self.assertEqual(p["scope"]["printings"], len(self.MASTER))
        seguidas = {x["printing_id"] for x in p.get("items", [])}
        for pid in self.EXTRA:
            self.assertNotIn(pid, seguidas, pid)
        con.close()

    def test_desligar_o_botao_volta_a_por_a_colecao_extra_nas_listas(self):
        """`listas_de_compra.so_master_set: false` é o mundo de 2026-09-14."""
        from riftvault import config
        cfg = config.load()
        cfg = {**cfg, "listas_de_compra": {"so_master_set": False}}
        con = self.edicao()
        p = self.a_subir.master_faltas(con, cfg)
        itens = {x["printing_id"]: x for s in p["sets"] for x in s["items"]}
        self.assertEqual(sorted(itens), sorted(self.MASTER + self.EXTRA))
        # Com o alvo de cada bloco: a sobrenumerada e a promo pedem 1
        # (2026-09-15), a alt art de Unit e a runa especial também (2026-09-16).
        self.assertEqual(itens["tst-001a-100"]["missing"], 1)
        self.assertEqual(itens["tst-101-100"]["missing"], 1)
        self.assertEqual(itens["tst-sp1-006"]["missing"], 1)
        self.assertEqual(itens["tst-002a-100"]["missing"], 1)
        self.assertFalse(p["scope"]["so_master_set"])
        con.close()


if __name__ == "__main__":
    unittest.main()

"""As runas com numeração de master set pedem 3, como qualquer outra carta.

Palavras do André (2026-09-15, à tarde): *"as runas que estao no masterset
(acho que e so origin) vamos ate 3 como as outras cartas"*. Revoga o «runas 1
de cada» (2026-09-08, reafirmado a 2026-09-14 à noite): o ramo que dava 1 às
runas saiu do `metrics.master_target`, e o alvo delas passou a ser o do tipo —
`master_targets_by_type.Rune: 3` por cima do `playset_targets_by_type.Rune:
12`, que continua a ser o que os decks jogam (`metrics.alvo_do_tipo`).

O critério continua a ser a NUMERAÇÃO (ordem `runas-fora`, `test_runas_fora`):
a base `OGN-007/298` fica na sequência e conta; a arte alternativa
`OGN-007a/298` fica no bloco «runas especiais», coleção extra; a promo
`VEN-R01`, sem `/tamanho`, está escondida e não pede nada a ninguém.

**Desde 2026-09-16 a arte alternativa da runa pede 1, não 3** — é uma arte
alternativa, e *"Alt Art e Overnumbered e assim quero apenas 1 de cada"*
(`master_set.um_de_cada` leva o `a`, runas incluídas; `test_altart_decks`).
O 3 desta ordem ficou para a runa BASE, a que está no master set — que foi a
que ele nomeou (*"as runas que estao no masterset"*).

Corre contra um catálogo de brincar — nunca contra o `data/` real.
"""

from __future__ import annotations

import importlib
import json
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.fixture import Vault


class Base(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.close)
        from riftvault import a_subir, config, metrics
        importlib.reload(metrics)
        importlib.reload(a_subir)
        self.metrics, self.a_subir, self.config = metrics, a_subir, config

    def com_config(self, extra: dict):
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
        """Uma Unit, uma runa base numerada, a arte alternativa dela e uma
        runa promo sem numeração — as três formas que as runas têm no
        catálogo real (OGN-007, OGN-007a, VEN-R01)."""
        con = self.v.connect()
        v = self.v
        v.add_printing(con, "tst-001-100", "TST", 1, "Uma Unit", size=100)
        v.add_printing(con, "tst-007-100", "TST", 7, "Fury Rune",
                       card_type="Rune", size=100)
        v.add_printing(con, "tst-007a-100", "TST", 7, "Fury Rune",
                       card_type="Rune", variant="a", kind="alt_art",
                       rarity="showcase", base_rarity="common", size=100)
        v.add_printing(con, "tst-r01", "TST", 1, "Body Rune", card_type="Rune",
                       variant="r01", kind="rune_promo", lane="r", codigo="TST-R01")
        v.rebuild(con)
        return con

    def tiles(self, con) -> dict:
        p = self.metrics.set_payload(con, "TST")
        return {pr["id"]: pr for grp in p["groups"] for pr in grp["printings"]}


class TestOAlvo(Base):
    def test_a_runa_numerada_pede_3_e_a_arte_alternativa_nao_esta(self):
        con = self.edicao()
        t = self.tiles(con)
        self.assertEqual(t["tst-007-100"]["target"], 3)
        # A Unit ao lado pede o mesmo: a runa deixou de ser caso especial.
        self.assertEqual(t["tst-001-100"]["target"], 3)
        # A arte alternativa da runa está retirada de tudo (2026-09-17 à
        # tarde, `test_runas_alt_fora.py`): não tem alvo porque não está.
        self.assertNotIn("tst-007a-100", t)
        con.close()

    def test_o_bloco_nao_mudou_so_o_alvo(self):
        """A ordem `runas-fora` decidiu o BLOCO; esta decidiu o ALVO."""
        con = self.edicao()
        t = self.tiles(con)
        self.assertEqual(t["tst-007-100"]["block"], "master")
        self.assertNotIn("tst-007a-100", t)  # retirada (2026-09-17)
        self.assertNotIn("tst-r01", t)      # escondida: nem chega à grelha
        con.close()

    def test_o_playset_jogavel_continua_12(self):
        """Colecionar e jogar são duas perguntas: `master_targets_by_type` só
        mexe na segunda métrica; os decks continuam a pedir as 12."""
        self.assertEqual(self.metrics.playset_target("Rune", False), 12)
        self.assertEqual(self.metrics.alvo_do_tipo("Rune", False), 3)

    def test_o_alvo_1_do_runas_especiais_deixou_de_ser_lido(self):
        """Um config de antes de 2026-09-15 com `runas_especiais.alvo: 1` não
        põe a runa a 1 — o campo deixou de existir para o código."""
        self.com_config({"runas_especiais": {"tipos": ["Rune"], "excepto": ["base"],
                                             "alvo": 1}})
        self.assertEqual(self.metrics.master_target("x", "base", "Rune", False), 3)
        # A arte alternativa pede 1 pelo `um_de_cada` (2026-09-16), não por este
        # campo: sem o `a` nessa lista voltava aos 3 do tipo.
        self.assertEqual(self.metrics.master_target("x", "alt_art", "Rune", False), 1)
        self.com_config({"runas_especiais": {"tipos": ["Rune"], "excepto": ["base"],
                                             "alvo": 1},
                         "master_set": {"um_de_cada": ["overnumbered", "promo"]}})
        self.assertEqual(self.metrics.master_target("x", "alt_art", "Rune", False), 3)

    def test_sem_master_targets_by_type_a_runa_cai_no_playset_jogavel(self):
        """É a única tabela que separa as duas perguntas: sem ela, colecionar
        uma runa passa a ser ter as 12 que se jogam."""
        self.com_config({"master_targets_by_type": {}})
        self.assertEqual(self.metrics.master_target("x", "base", "Rune", False), 12)


class TestAsContas(Base):
    def test_a_percentagem_e_os_niveis_pedem_3_a_runa_da_sequencia(self):
        """Uma runa com uma cópia deixou de estar completa: entra no numerador
        só no nível 1. O denominador NÃO mexe — conta impressões, não cópias."""
        from riftvault import collection
        con = self.edicao()
        collection.adjust(con, "tst-007-100", 1, source="test")
        p = self.metrics.set_payload(con, "TST")["progress"]
        self.assertEqual((p["master"]["done"], p["master"]["total"]), (0, 2))
        self.assertEqual([lv["done"] for lv in p["levels"]], [1, 0, 0])
        self.assertEqual([lv["missing"] for lv in p["levels"]], [1, 3, 5])
        con.close()

    def test_a_wantlist_pede_as_que_faltam_ate_3(self):
        """As runas numeradas entram na lista do master set como qualquer outra
        carta — o `faltas_ignorar_tipos` é das abas dos DECKS e não lhes
        toca aqui."""
        from riftvault import collection
        con = self.edicao()
        collection.adjust(con, "tst-007-100", 1, source="test")
        p = self.a_subir.wantlist(con, "TST")
        alvos = {x["printing_id"]: (x["target"], x["missing"]) for x in p["items"]}
        self.assertEqual(alvos["tst-007-100"], (3, 2))
        # A arte alternativa é coleção extra: acompanha-se, não se compra.
        self.assertNotIn("tst-007a-100", alvos)
        self.assertNotIn("tst-r01", alvos)
        con.close()

    def test_o_bloco_das_runas_especiais_ficou_vazio(self):
        """A arte alternativa da runa enchia este bloco; desde 2026-09-17 à
        tarde está retirada de tudo e o bloco, vazio, não aparece — mesmo
        com uma cópia dela na caixa."""
        from riftvault import collection
        con = self.edicao()
        collection.adjust(con, "tst-007a-100", 1, source="test")
        b = {b["id"]: b for b in self.metrics.set_payload(con, "TST")["blocks"]}
        self.assertNotIn("rune_special", b)
        con.close()


if __name__ == "__main__":
    unittest.main()

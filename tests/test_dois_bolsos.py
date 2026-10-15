"""OS DOIS BOLSOS, com as decisões dele (André, 2026-10-13).

A regra dele: *«Coleção é Coleção e não mexe, tudo tem que lá estar / Deck é
Deck / tudo o que eu marcar que tenho no deck, deve ser tratado como à parte,
caso o deck deixe de jogar, essas cartas ficaram guardadas para outro deck que
as possa usar mais tarde»*. Mediu-se (docs/dois-bolsos-2026-10-13.md) e ele
decidiu:

  DECISÃO 1 — «duas percentagens lado a lado». O master set NÃO muda (continua
  em não-foil); ao lado nasce o «master set foil» (`foil.master_set_foil`,
  `index.levels_foil`), com as comuns e incomuns contadas em foil, alvo 3. O
  alvo das foils (tile, metade das foils das Faltas) passa a ser o mesmo: Rune
  3, já não 12.

  DECISÃO 2 — «épicas podem vir da Coleção». Abaixo do patamar
  (`coleccao_so_a_partir_de`) um deck só vê da Coleção o que passa do alvo
  (`decks.abaixo_do_patamar: so_o_excedente`); o resto é próprio, do stock ou
  falta. Das épicas para cima, Coleção como sempre.

  E O BOLSO COMUM — desmontar (ou apagar a lista) manda as próprias e as
  sleevadas para o STOCK DOS DECKS (o binder), nunca para a Coleção, onde
  servem outro deck; o stock não conta para o valor.

Tudo contra pastas temporárias e um config temporário.
"""

from __future__ import annotations

import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ["RIFTVAULT_CONFIG"] = str(Path(tempfile.gettempdir()) / "riftvault-nao-existe.json")

from tests.fixture import REPO, Vault  # noqa: E402

# Azir: Legend épica, 4 Defy (rara), 2 Salvage (comum), 1 Hidden Blade (incomum).
AZIR = ("Nome: Azir\n\nLegend:\n1 Emperor of the Sands\n\n"
        "MainDeck:\n4 Defy\n2 Salvage\n1 Hidden Blade\n")
# Ornn: outra Legend, pede 2 Defy.
ORNN = ("Nome: Ornn\n\nLegend:\n1 Fire Below the Mountain\n\nMainDeck:\n2 Defy\n")


class Base(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.close)
        from riftvault import (a_mais, colar, collection, config, decks, faltas_foil,
                               foil, locais, metrics, prices, principal, proprias)
        for m in (locais, metrics, prices, decks, proprias, foil, faltas_foil, a_mais,
                  principal, colar):
            importlib.reload(m)
        self.config, self.decks, self.locais, self.metrics = config, decks, locais, metrics
        self.prices, self.proprias, self.foil, self.collection = prices, proprias, foil, collection
        self.principal, self.colar, self.faltas_foil = principal, colar, faltas_foil
        self.cfg({})

    def cfg(self, decks_extra: dict, extra: dict | None = None):
        caminho = self.v.root / "config.json"
        caminho.write_text(json.dumps({
            "decks": {"so_base": False, "so_normais_excepto": [],
                      "versoes_especiais": ["a", "overnumbered", "promo"],
                      "coleccao_so_a_partir_de": "epic",
                      "abaixo_do_patamar": "so_o_excedente",
                      "modo": "coleccao", **decks_extra},
            "foil": {"raridades": ["common", "uncommon"], "edicoes_fora": ["OGS"],
                     "conta_para_coleccao": False, "conta_para_valor": True},
            **(extra or {})}, ensure_ascii=False), encoding="utf-8")
        os.environ["RIFTVAULT_CONFIG"] = str(caminho)
        importlib.reload(self.config)
        self.config.load.cache_clear()

        def repor():
            os.environ["RIFTVAULT_CONFIG"] = str(
                Path(tempfile.gettempdir()) / "riftvault-nao-existe.json")
            importlib.reload(self.config)
            self.config.load.cache_clear()

        self.addCleanup(repor)

    def catalogo(self, decks=("azir",), defy=5):
        """Defy rara (Coleção `defy`, alvo 3), Salvage comum (6), Hidden Blade
        incomum (3), Fury Rune (comum, 1), as duas Legends épicas (1 cada)."""
        con = self.v.connect()
        v = self.v
        v.add_printing(con, "tst-001-100", "TST", 1, "Defy", rarity="rare", size=100)
        v.add_printing(con, "tst-003-100", "TST", 3, "Emperor of the Sands",
                       card_type="Legend", rarity="epic", size=100)
        v.add_printing(con, "tst-004-100", "TST", 4, "Salvage", rarity="common", size=100)
        v.add_printing(con, "tst-005-100", "TST", 5, "Hidden Blade", rarity="uncommon", size=100)
        v.add_printing(con, "tst-006-100", "TST", 6, "Fury Rune", card_type="Rune", size=100)
        v.add_printing(con, "tst-007-100", "TST", 7, "Fire Below the Mountain",
                       card_type="Legend", rarity="epic", size=100)
        v.rebuild(con)
        for pid, cents, foil in (("tst-001-100", 150, None), ("tst-003-100", 1000, None),
                                 ("tst-004-100", 20, 90), ("tst-005-100", 300, 700),
                                 ("tst-006-100", 11, 40), ("tst-007-100", 500, None)):
            con.execute("INSERT INTO catalog.price_latest (printing_id, price_cents, "
                        "price_foil_cents) VALUES (?,?,?)", (pid, cents, foil))
        for pid, n in (("tst-001-100", defy), ("tst-004-100", 6), ("tst-005-100", 3),
                       ("tst-006-100", 1), ("tst-003-100", 1), ("tst-007-100", 1)):
            self.collection.adjust(con, pid, n, source="test")
        for slug, texto in (("azir", AZIR), ("ornn", ORNN)):
            if slug in decks:
                self.v.write_deck(slug, texto)
        self.decks.import_all(con, log=lambda *_: None)
        self.addCleanup(con.close)
        return con

    def entrada(self, con, slug):
        did = con.execute("SELECT deck_id FROM decks WHERE name = ?", (slug,)).fetchone()[0]
        return self.decks.allocate(con)[did]


# ---------------------------------------------------------------------------
# DECISÃO 2 — até às raras, nunca da Coleção (só o excedente)
# ---------------------------------------------------------------------------


class TestAteAsRaras(Base):
    def test_a_rara_so_usa_o_que_passa_do_alvo(self):
        # 5 Defy na Coleção, alvo 3: o deck vê 2. Pede 4 → faltam 2.
        a = self.entrada(self.catalogo(), "azir")
        self.assertEqual(a["na_colecao"].get("defy"), 2)
        self.assertEqual(a["missing"].get("defy"), 2)

    def test_prova_pela_negativa_com_marca_a_colecao_inteira_serve(self):
        self.cfg({"abaixo_do_patamar": "marca"})
        a = self.entrada(self.catalogo(), "azir")
        self.assertEqual(a["na_colecao"].get("defy"), 4)
        self.assertNotIn("defy", a["missing"])
        # ...e o aviso de 2026-09-24 diz que vieram de baixo do patamar.
        self.assertEqual(a["aviso_colecao"].get("defy"), 4)

    def test_sem_excedente_a_rara_e_toda_falta(self):
        a = self.entrada(self.catalogo(defy=3), "azir")
        self.assertNotIn("defy", a["na_colecao"])
        self.assertEqual(a["missing"].get("defy"), 4)

    def test_comum_e_incomum_tambem_so_o_excedente(self):
        a = self.entrada(self.catalogo(), "azir")
        # Salvage 6, alvo 3: vê 3, pede 2 → servido. Hidden Blade 3, alvo 3:
        # vê 0, pede 1 → falta.
        self.assertEqual(a["na_colecao"].get("salvage"), 2)
        self.assertEqual(a["missing"].get("hidden blade"), 1)

    def test_a_epica_continua_a_vir_da_colecao(self):
        # A Legend tem 1 cópia e alvo 1 — excedente zero —, e serve na mesma.
        a = self.entrada(self.catalogo(), "azir")
        self.assertEqual(a["na_colecao"].get("emperor of the sands"), 1)
        self.assertNotIn("emperor of the sands", a["missing"])

    def test_o_aviso_vem_vazio_quando_bloqueia(self):
        a = self.entrada(self.catalogo(), "azir")
        self.assertEqual(a["aviso_colecao"], {})

    def test_as_proprias_servem_primeiro(self):
        con = self.catalogo(defy=3)
        self.proprias.ajustar(con, "azir", "tst-001-100", 4, source="test")
        a = self.entrada(con, "azir")
        self.assertNotIn("defy", a["missing"])
        self.assertEqual(a["proprias"].get("defy"), 4)

    def test_o_patamar_vem_do_config(self):
        # Com o patamar na `rare`, a Defy volta a vir da Coleção inteira.
        self.cfg({"coleccao_so_a_partir_de": "rare"})
        a = self.entrada(self.catalogo(), "azir")
        self.assertEqual(a["na_colecao"].get("defy"), 4)

    def _a_mais_defy(self, con):
        from riftvault import a_mais
        importlib.reload(a_mais)
        itens = a_mais.excedente(con, self.config.load())
        return next((x["extra"] for x in itens if x["printing_id"] == "tst-001-100"), 0)

    def test_o_a_mais_nao_oferece_o_que_o_deck_joga(self):
        # 5 Defy, alvo 3, o Azir (montado) leva as 2 que passam do alvo: não
        # sobra nenhuma. Sem a correcção dizia «2 a mais» com as duas no deck.
        self.cfg({"montados": ["Azir"]})
        con = self.catalogo()
        self.assertEqual(self._a_mais_defy(con), 0)

    def test_o_a_mais_sem_deck_continua_a_dar_o_excedente(self):
        self.cfg({"montados": []})
        con = self.catalogo()
        self.assertEqual(self._a_mais_defy(con), 2)

    def test_valor_desconhecido_rebenta(self):
        self.cfg({"abaixo_do_patamar": "bloqueia-tudo"})
        with self.assertRaises(ValueError):
            self.decks.abaixo_do_patamar()

    def test_nao_mexe_em_numero_nenhum_da_colecao(self):
        con = self.catalogo()
        self.cfg({"abaixo_do_patamar": "marca"})
        antes = (self.metrics.niveis_payload(con), self.locais.na_colecao(con),
                 self.prices.collection_value(con)["cents"])
        self.cfg({"abaixo_do_patamar": "so_o_excedente"})
        self.decks.allocate(con)
        depois = (self.metrics.niveis_payload(con), self.locais.na_colecao(con),
                  self.prices.collection_value(con)["cents"])
        self.assertEqual(antes, depois)


class TestOConfig(unittest.TestCase):
    def test_o_config_dele_bloqueia_a_partir_da_epica(self):
        c = json.loads((REPO / "riftvault_config.json").read_text(encoding="utf-8"))
        self.assertEqual(c["decks"]["abaixo_do_patamar"], "so_o_excedente")
        self.assertEqual(c["decks"]["coleccao_so_a_partir_de"], "epic")

    def test_a_omissao_continua_a_marcar(self):
        from riftvault import config
        self.assertEqual(config.DEFAULTS["decks"]["abaixo_do_patamar"], "marca")

    def test_as_notas_contam_a_decisao_com_a_data_e_as_palavras(self):
        c = json.loads((REPO / "riftvault_config.json").read_text(encoding="utf-8"))
        n = c["_decks_dois_bolsos_nota"]
        for frase in ("2026-10-13", "Coleção é Coleção e não mexe",
                      "épicas podem vir da Coleção", "duas percentagens lado a lado"):
            self.assertIn(frase, n)
        self.assertIn("2026-10-13", c["_decks_raridade_nota"][:120])
        self.assertIn("2026-10-13", c["_foil_master_set_foil_nota"])
        # O alvo das foils voltou ao playset a 2026-10-15 (decisão dele): as
        # duas notas dizem-no, com a frase dele, e já não abrem com o «Rune 3».
        for k in ("_foil_master_set_foil_nota", "_faltas_foil_nota", "_foil_nota"):
            self.assertIn("2026-10-15", c[k], k)
            self.assertIn("as runas são 12", c[k], k)
        self.assertNotIn("Rune 12 -> Rune 3", c["_faltas_foil_nota"])
        self.assertTrue(c["_foil_nota"].startswith("A contagem de FOIL"))
        self.assertTrue(c["_faltas_foil_nota"].startswith("AS FALTAS EM DUAS METADES"))


# ---------------------------------------------------------------------------
# O BOLSO COMUM — desmontar devolve ao stock dos decks
# ---------------------------------------------------------------------------


class TestStockDosDecks(Base):
    def setUp(self):
        super().setUp()
        self.cfg({"montados": ["Azir", "Ornn"]})
        self.con = self.catalogo(decks=("azir", "ornn"), defy=3)
        self.proprias.ajustar(self.con, "azir", "tst-001-100", 2, source="test")

    def test_desmontar_manda_as_proprias_para_o_stock(self):
        copies = self.con.execute("SELECT * FROM copies ORDER BY 1").fetchall()
        res = self.principal.montar(self.con, "azir", False, source="test")
        self.assertEqual(res["ao_stock"]["copies"], 2)
        self.assertEqual(self.locais.proprias_de(self.con, "azir"), {})
        self.assertEqual(self.locais.em(self.con, self.locais.BINDER), {"tst-001-100": 2})
        # Nada entrou nem saiu do `copies`, e a Coleção não ganhou nada.
        self.assertEqual([tuple(r) for r in copies],
                         [tuple(r) for r in self.con.execute(
                             "SELECT * FROM copies ORDER BY 1").fetchall()])
        self.assertEqual(self.locais.na_colecao(self.con).get("tst-001-100"), 3)

    def test_o_stock_serve_outro_deck(self):
        # Antes: o Ornn não tem Defy (3 na Coleção, alvo 3, as 2 próprias são do Azir).
        self.assertEqual(self.entrada(self.con, "ornn")["missing"].get("defy"), 2)
        self.principal.montar(self.con, "azir", False, source="test")
        o = self.entrada(self.con, "ornn")
        self.assertNotIn("defy", o["missing"])
        self.assertEqual(o["no_binder"].get("defy"), 2)

    def test_o_stock_nao_conta_para_o_valor(self):
        # As 2 próprias não contam; passá-las ao binder pela porta de sempre
        # (`locais.mover`) não as pode fazer passar a valer.
        antes = self.prices.collection_value(self.con)["cents"]
        self.locais.mover(self.con, "tst-001-100", 2, "proprio:azir", "binder")
        self.assertEqual(self.prices.collection_value(self.con)["cents"], antes)
        self.assertEqual(self.locais.contadas(self.con).get("tst-001-100"), 3)

    def test_montar_nao_mexe_no_stock(self):
        self.principal.montar(self.con, "azir", True, source="test")
        self.assertEqual(self.locais.proprias_de(self.con, "azir"), {"tst-001-100": 2})

    def test_as_sleevadas_tambem_vao(self):
        self.locais.mover(self.con, "tst-004-100", 2, "colecao", "deck:azir")
        self.principal.montar(self.con, "azir", False, source="test")
        self.assertEqual(self.locais.em(self.con, self.locais.BINDER).get("tst-004-100"), 2)
        self.assertEqual(self.locais.por_deck(self.con), {})

    def test_apagar_a_lista_tambem_devolve(self):
        res = self.colar.apagar(self.con, "azir", confirmar=True)
        self.assertEqual(res["ao_stock"]["copies"], 2)
        self.assertEqual(self.locais.em(self.con, self.locais.BINDER), {"tst-001-100": 2})

    def test_rasto_na_location_ops(self):
        self.principal.montar(self.con, "azir", False, source="test")
        r = self.con.execute("SELECT from_loc, to_loc, qty FROM location_ops "
                             "ORDER BY id DESC LIMIT 1").fetchone()
        self.assertEqual(tuple(r), ("proprio:azir", "binder", 2))


# ---------------------------------------------------------------------------
# DECISÃO 1 — o master set foil, ao lado
# ---------------------------------------------------------------------------


class TestMasterSetFoil(Base):
    def test_o_master_set_nao_muda_com_foils(self):
        con = self.catalogo(decks=())
        antes = self.metrics.niveis_payload(con)
        self.foil.ajustar(con, "tst-004-100", 3, source="test")
        self.assertEqual(self.metrics.niveis_payload(con), antes)

    def test_as_comuns_contam_em_foil_no_segundo(self):
        con = self.catalogo(decks=())
        play = self.foil.master_set_foil(con)["levels"][-1]
        # 6 impressões: Defy (rara, 3 normais) e as Legends contam como no
        # master set; Salvage, Hidden Blade e a runa contam FOILS (zero).
        self.assertEqual((play["done"], play["total"]), (3, 6))
        self.foil.ajustar(con, "tst-004-100", 3, source="test")
        play = self.foil.master_set_foil(con)["levels"][-1]
        self.assertEqual(play["done"], 4)

    def test_mesmo_denominador_do_master_set(self):
        con = self.catalogo(decks=())
        self.assertEqual(self.foil.master_set_foil(con)["levels"][-1]["total"],
                         self.metrics.niveis_payload(con)["levels"][-1]["total"])
        self.assertEqual(self.foil.master_set_foil(con)["foil_scope"], 3)

    def test_o_preco_e_o_da_foil(self):
        con = self.catalogo(decks=())
        um = self.foil.master_set_foil(con)["levels"][0]
        # Faltam 1 Salvage (0,90), 1 Hidden Blade (7,00) e 1 runa (0,40) em foil.
        self.assertEqual(um["cents"], 90 + 700 + 40)

    def test_a_runa_pede_12_em_foil_e_3_na_coleccao(self):
        """TRAVA (André, 2026-10-15): «não, as runas são 12, então esquece o
        que eu disse, deixa como está» — e «Põe o 12 de volta e mais nada».

        De 13/10 a 15/10 o alvo em foil foi «alinhado» com o da Coleção (3)
        para o número e a wantlist baterem. ELE NÃO O PEDIU. Os dois alvos
        ficam na MESMA asserção para ninguém os voltar a alinhar sem ele: a
        mesma runa base pede 12 em foil e 3 na Coleção.
        """
        con = self.catalogo(decks=())
        r = con.execute("SELECT * FROM catalog.printings WHERE printing_id = 'tst-006-100'").fetchone()
        self.assertEqual((self.foil.alvo(r), self.metrics.alvo(r)), (12, 3),
                         "foil = playset do tipo (12); Coleção = 3 — NÃO alinhar")
        # O número e a sua wantlist continuam com o mesmo alvo — o playset.
        self.assertEqual(self.faltas_foil.alvo(r), self.foil.alvo(r))
        self.assertEqual(self.faltas_foil.escopo(con)["tst-006-100"]["target"], 12)
        # E o cartão «master set foil» pede as 12 no último degrau.
        play = self.foil.master_set_foil(con)["levels"][-1]
        self.assertEqual(self.foil.master_set_foil(con)["max"], 3,
                         "os degraus continuam três; o último pede o alvo inteiro")
        um = self.foil.master_set_foil(con)["levels"][0]
        self.assertEqual(play["missing"] - um["missing"], (3 - 1) + (3 - 1) + (12 - 1))

    def test_vai_no_indice_ao_lado_do_master_set(self):
        con = self.catalogo(decks=())
        ix = self.metrics.index_payload(con)
        self.assertIn("levels", ix)
        self.assertIn("levels_foil", ix)
        self.assertEqual(ix["levels_foil"]["levels"],
                         self.foil.master_set_foil(con)["levels"])


class TestInterface(unittest.TestCase):
    JS = (REPO / "riftvault" / "web" / "app.js").read_text(encoding="utf-8")

    def test_o_inicio_mostra_os_dois(self):
        self.assertIn("'Master set · playset'", self.JS)
        self.assertIn("'Master set foil · playset'", self.JS)
        self.assertIn("ix.levels_foil", self.JS)

    def test_a_pagina_do_deck_diz_a_regra(self):
        self.assertIn("p.abaixo_do_patamar === 'so_o_excedente'", self.JS)
        self.assertIn("stock dos decks", self.JS)

    def test_a_ajuda_diz_runa_12_outra_vez(self):
        # 2026-10-15: voltou ao playset, e a ajuda e o cartão dizem-no.
        self.assertIn("foil (numa runa, 12", self.JS)
        self.assertNotIn("(alvo 3), o resto como no master set", self.JS)


if __name__ == "__main__":
    unittest.main()

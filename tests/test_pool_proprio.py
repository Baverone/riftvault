"""A experiência do pool próprio dos decks (André, 2026-09-21, `decks.modo`).

Palavras dele: *"quero que a coleccao fique sempre imaculada, nada sai da
coleccao; os decks, todos partilham as mesmas cartas, mas nao usam
absolutamente nada da coleccao; so jogam com versoes base; vamos ver como fica
assim as coisas, para ter uma ideia"*. É uma EXPERIÊNCIA, atrás de UMA chave
(`decks.modo = "pool_proprio"`; `coleccao` é tudo como estava).

O que se fixa:
  1. a aritmética — o pool precisa do MÁXIMO por carta entre os decks, main e
     sideboard SOMAM dentro do mesmo deck, as runas ficam fora;
  2. só versões base — a Legend e o Champion também; a alt art no pool não
     serve e é dita; uma carta sem base é dita;
  3. entrar e sair do pool escreve no `copies` E no local de uma vez, e a
     Coleção (`na_colecao`) não mexe; `−` nunca abaixo de zero; retry não
     conta a dobrar; só base;
  4. a Coleção INTACTA — com o modo ligado, os níveis, a wantlist, o valor, as
     Faltas, o A mais e as Encomendas dão EXACTAMENTE o mesmo que dariam sem
     decks nenhuns; o pool não conta para nada disso;
  5. reversível — voltar a `coleccao` repõe os números de hoje ao exemplar;
  6. as rotas, o build, a CLI e o `app.js`.

Tudo contra pastas temporárias (`tests.fixture.Vault`) e um config temporário
(`RIFTVAULT_CONFIG`): o `data/` e o `riftvault_config.json` a sério nunca são
tocados.
"""

from __future__ import annotations

import argparse
import contextlib
import importlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ["RIFTVAULT_CONFIG"] = str(Path(tempfile.gettempdir()) / "riftvault-nao-existe.json")

from tests.fixture import REPO, Vault  # noqa: E402

DECKS_HOJE = {"so_normais_excepto": ["legend", "champion"],
              "versoes_especiais": ["a", "overnumbered", "promo"]}

# Deck A: Defy 3 no main + 1 no sideboard = 4 (somam); Salvage 2; Hidden Blade 1.
AZIR = ("Nome: Azir\n\nLegend:\n1 Emperor of the Sands\n\nChampion:\n1 Brutalizer\n\n"
        "MainDeck:\n3 Defy\n2 Salvage\n\nRune Pool:\n3 Fury Rune\n\n"
        "Sideboard:\n1 Defy\n1 Hidden Blade\n")
# Deck B (outra Legend — não é um grupo de Legend): Defy 2; Salvage 3; Hidden Blade 2.
ORNN = ("Nome: Ornn\n\nLegend:\n1 Fire Below the Mountain\n\n"
        "MainDeck:\n2 Defy\n3 Salvage\n2 Hidden Blade\n\nRune Pool:\n3 Fury Rune\n")


class Base(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.close)
        from riftvault import (a_mais, a_subir, collection, config, decks, faltas,
                               faltas_edicao, locais, metrics, pending, pool, prices)
        for m in (locais, metrics, decks, pool, a_subir, faltas_edicao, a_mais,
                  pending, faltas, prices):
            importlib.reload(m)
        self.config, self.decks, self.pool, self.locais = config, decks, pool, locais
        self.metrics, self.a_subir, self.faltas_edicao = metrics, a_subir, faltas_edicao
        self.a_mais, self.pending, self.faltas, self.prices = a_mais, pending, faltas, prices
        self.collection = collection
        self.modo("coleccao")

    def modo(self, modo: str, extra: dict | None = None):
        """Escreve o config temporário com o modo pedido e relê-o."""
        caminho = self.v.root / "config.json"
        caminho.write_text(json.dumps({"decks": {**DECKS_HOJE, "modo": modo},
                                       **(extra or {})}), encoding="utf-8")
        os.environ["RIFTVAULT_CONFIG"] = str(caminho)
        importlib.reload(self.config)
        self.config.load.cache_clear()

        def repor():
            os.environ["RIFTVAULT_CONFIG"] = str(
                Path(tempfile.gettempdir()) / "riftvault-nao-existe.json")
            importlib.reload(self.config)
            self.config.load.cache_clear()

        self.addCleanup(repor)

    def catalogo(self, decks=("azir", "ornn")):
        """Uma edição: Defy (base + alt art), Brutalizer, Emperor (base +
        sobrenumerada), Salvage, Hidden Blade (base + alt art), Fury Rune, e
        Nine-Tailed Fox SÓ em sobrenumerada. Na Coleção: 3 Defy, 5 Salvage,
        1 Emperor, 1 Hidden Blade alt art."""
        con = self.v.connect()
        v = self.v
        v.add_printing(con, "tst-001-100", "TST", 1, "Defy", rarity="rare", size=100)
        v.add_printing(con, "tst-001a-100", "TST", 1, "Defy", variant="a", kind="alt_art",
                       rarity="showcase", base_rarity="rare", size=100)
        v.add_printing(con, "tst-002-100", "TST", 2, "Brutalizer", size=100)
        v.add_printing(con, "tst-003-100", "TST", 3, "Emperor of the Sands",
                       card_type="Legend", rarity="epic", size=100)
        v.add_printing(con, "tst-004-100", "TST", 4, "Salvage", size=100)
        v.add_printing(con, "tst-005-100", "TST", 5, "Hidden Blade", size=100)
        v.add_printing(con, "tst-005a-100", "TST", 5, "Hidden Blade", variant="a",
                       kind="alt_art", rarity="showcase", size=100)
        v.add_printing(con, "tst-006-100", "TST", 6, "Fury Rune", card_type="Rune", size=100)
        v.add_printing(con, "tst-007-100", "TST", 7, "Fire Below the Mountain",
                       card_type="Legend", rarity="epic", size=100)
        v.add_printing(con, "tst-101-100", "TST", 101, "Emperor of the Sands",
                       card_type="Legend", rarity="showcase", size=100)
        v.add_printing(con, "tst-102-100", "TST", 102, "Nine-Tailed Fox",
                       rarity="showcase", size=100)
        v.rebuild(con)
        for pid, cents in (("tst-001-100", 150), ("tst-001a-100", 2000),
                           ("tst-002-100", 11), ("tst-003-100", 1000),
                           ("tst-004-100", 20), ("tst-005-100", 300),
                           ("tst-005a-100", 900), ("tst-006-100", 11),
                           ("tst-007-100", 500),
                           ("tst-101-100", 8000), ("tst-102-100", 30000)):
            con.execute("INSERT INTO catalog.price_latest (printing_id, price_cents) "
                        "VALUES (?,?)", (pid, cents))
        self.collection.adjust(con, "tst-001-100", 3, source="test")
        self.collection.adjust(con, "tst-004-100", 5, source="test")
        self.collection.adjust(con, "tst-003-100", 1, source="test")
        self.collection.adjust(con, "tst-005a-100", 1, source="test")
        if "azir" in decks:
            self.v.write_deck("azir", AZIR)
        if "ornn" in decks:
            self.v.write_deck("ornn", ORNN)
        self.decks.import_all(con, log=lambda *_: None)
        self.addCleanup(con.close)
        return con

    def fotografia(self, con) -> dict:
        """Tudo o que é da COLEÇÃO, para comparar entre cenários.

        `numeros` são as contas que os decks nunca deviam mexer (níveis,
        wantlist, valor, grelha, Faltas, Encomendas); `com_decks` é o que, no
        modo de sempre, os decks alteram na vista da Coleção (o «Azir 3» da
        grelha, o desconto do A mais, as libertadas, o «para» das Encomendas)
        e que no modo do pool tem de vir vazio.
        """
        cfg = self.config.load()
        sp = self.metrics.set_payload(con, "TST")
        am = self.a_mais.payload(con, cfg)
        fe = self.faltas_edicao.payload(con, cfg)
        enc = self.pending.encomendas(con)
        return {
            "numeros": {
                "niveis": [(l["k"], l["done"], l["total"], l["missing"], l["cents"])
                           for l in self.metrics.niveis_payload(con, cfg)["levels"]],
                "wantlist": {k: self.a_subir.wantlist(con, cfg=cfg)[k]
                             for k in ("text", "lines", "copies", "cents")},
                "valor": self.prices.collection_value(con)["cents"],
                "valor_copias": self.prices.collection_value(con)["copias"],
                "totais": self.collection.totals(con),
                "grelha": [(p["id"], p["qty"], p["target"], p["qty_valor"])
                           for g in sp["groups"] for p in g["printings"]],
                "playset": {g["card_key"]: g["playset"] for g in sp["groups"]},
                "value_owned": sp["progress"]["value"]["owned"],
                "master": sp["progress"]["master"],
                "faltas": (fe["totals"], fe["totals_lists"]),
                "encomendas": enc["totals"],
            },
            "com_decks": {
                "a_mais": {s["set"]: [(x["printing_id"], x["extra"], x["have"], x["used"])
                                      for x in s["excedente"]["items"]] for s in am["sets"]},
                "libertadas": am["totals"]["libertadas"],
                "encomendas_decks": (enc["falta_totals"], enc["falta"]),
                "usos": {g["card_key"]: g["decks"] for g in sp["groups"] if g["decks"]},
            },
        }


# ---------------------------------------------------------------------------


class TestAritmetica(Base):
    """1. O máximo entre decks; main + sideboard somam; runas fora."""

    def test_o_pool_precisa_do_maximo_entre_os_decks_nao_da_soma(self):
        self.modo("pool_proprio")
        con = self.catalogo()
        need = self.pool.necessidades(con)
        # Defy: Azir 3 + 1 (sideboard) = 4, Ornn 2 -> o pool precisa de 4, a soma era 6.
        self.assertEqual(need["defy"]["max"], 4)
        self.assertEqual(need["defy"]["soma"], 6)
        self.assertEqual(need["defy"]["decks"], {"azir": 4, "ornn": 2})
        # Salvage: 2 e 3 -> 3 (soma 5); Hidden Blade: 1 e 2 -> 2 (soma 3).
        self.assertEqual((need["salvage"]["max"], need["salvage"]["soma"]), (3, 5))
        self.assertEqual((need["hidden blade"]["max"], need["hidden blade"]["soma"]), (2, 3))
        # Cada Legend é de um deck só; o Champion só do Azir: 1.
        self.assertEqual(need["emperor of the sands"], {"max": 1, "soma": 1, "decks": {"azir": 1}})
        self.assertEqual(need["fire below the mountain"]["max"], 1)
        self.assertEqual(need["brutalizer"]["max"], 1)
        # As runas ficam fora de tudo.
        self.assertNotIn("fury rune", need)
        p = self.pool.payload(con)
        self.assertEqual(p["totals"]["need"], 4 + 3 + 2 + 1 + 1 + 1)
        self.assertEqual(p["totals"]["soma"], 6 + 5 + 3 + 1 + 1 + 1)
        self.assertEqual(p["totals"]["cards"], 6)
        # Cada deck pede o que a lista dele pede, sem runas.
        self.assertEqual({d["slug"]: d["wanted"] for d in p["por_deck"]},
                         {"azir": 4 + 2 + 1 + 1 + 1, "ornn": 2 + 3 + 2 + 1})

    def test_o_pool_comeca_a_zero_e_cada_deck_avalia_se_contra_o_pool_inteiro(self):
        self.modo("pool_proprio")
        con = self.catalogo()
        p = self.pool.payload(con)
        self.assertEqual(p["totals"]["have"], 0, "o pool começa a zero — a Coleção não entra")
        self.assertEqual(p["totals"]["missing"], p["totals"]["need"])
        self.assertTrue(all(d["have"] == 0 for d in p["por_deck"]))
        # Mete 3 Defy no pool: os DOIS decks vêem-nas (partilham, não se consomem).
        self.pool.ajustar(con, "tst-001-100", 3, source="test")
        p = self.pool.payload(con)
        defy = next(c for c in p["cards"] if c["card_key"] == "defy")
        self.assertEqual((defy["have"], defy["missing"]), (3, 1))
        alloc = self.decks.allocate(con)
        por_slug = {r["name"]: alloc[r["deck_id"]] for r in self.decks.deck_rows(con)}
        self.assertEqual(por_slug["azir"]["alloc"]["defy"], 3)
        self.assertEqual(por_slug["azir"]["missing"]["defy"], 1)
        self.assertEqual(por_slug["ornn"]["alloc"]["defy"], 2, "o Ornn pede 2 e o pool tem 3: chega")
        self.assertNotIn("defy", por_slug["ornn"]["missing"])
        # O total geral conta o pool UMA vez (pelo líder): falta 1 Defy, não 1 + 0.
        rf = self.decks.resumo_das_faltas(con)
        self.assertEqual(rf["copies"], p["totals"]["missing"])
        self.assertEqual(rf["disputed"], 0)
        self.assertEqual(rf["ordered"], 0)
        # Por deck: o Ornn ainda não fecha (faltam Salvage 3, Hidden Blade 2, a Legend).
        ornn = next(d for d in p["por_deck"] if d["slug"] == "ornn")
        self.assertFalse(ornn["ok"])
        self.assertEqual(ornn["have"], 2)
        self.assertEqual(ornn["missing"], 3 + 2 + 1)


class TestSoBase(Base):
    """2. Só versões base — a Legend e o Champion também."""

    def test_a_legend_e_o_champion_jogam_a_base_e_nao_ha_lugar_especial(self):
        self.modo("pool_proprio")
        con = self.catalogo()
        versoes = self.decks.versoes_dos_decks(con)
        self.assertEqual(versoes.especiais, {})
        self.assertEqual(versoes.papeis, frozenset())
        self.assertEqual(versoes.normais_de("emperor of the sands"), ["tst-003-100"])
        self.assertEqual(versoes.compra("emperor of the sands"), "tst-003-100")
        # A sobrenumerada da Legend no pool não serve a Legend.
        alloc = self.decks.allocate(con)
        for a in alloc.values():
            self.assertEqual(a["need_especial"], {})
            self.assertEqual(a["missing_especial"], {})
        azir = next(r for r in self.decks.deck_rows(con) if r["name"] == "azir")
        p = self.decks.deck_payload(con, azir["deck_id"])
        legend = next(c for s in p["sections"] if s["role"] == "legend" for c in s["cards"])
        self.assertIsNone(legend["especial"])
        self.assertEqual(legend["order_code"], "TST-003/100")

    def test_uma_alt_art_no_pool_nao_serve_e_e_dita(self):
        self.modo("pool_proprio")
        con = self.catalogo()
        # Mete a alt art pela porta de trás (o `ajustar` recusa-a): move-se.
        self.locais.mover(con, "tst-005a-100", 1, "colecao", "pool", source="test")
        p = self.pool.payload(con)
        hb = next(c for c in p["cards"] if c["card_key"] == "hidden blade")
        self.assertEqual(hb["have"], 0, "a alt art não conta")
        self.assertEqual([x["printing_id"] for x in p["fora"]], ["tst-005a-100"])
        self.assertEqual(p["fora"][0]["motivo"], "não é versão base")
        self.assertEqual(p["totals"]["fora"], 1)
        with self.assertRaises(self.pool.NaoBase):
            self.pool.ajustar(con, "tst-005a-100", 1, source="test")
        with self.assertRaises(self.pool.NaoBase):
            self.pool.ajustar(con, "tst-101-100", 1, source="test")

    def test_uma_carta_sem_versao_base_e_dita(self):
        self.modo("pool_proprio")
        con = self.catalogo(decks=("azir",))
        self.v.write_deck("kennen", "Nome: Kennen\n\nLegend:\n1 Emperor of the Sands\n\n"
                                    "MainDeck:\n2 Nine-Tailed Fox\n")
        self.decks.import_all(con, log=lambda *_: None)
        p = self.pool.payload(con)
        self.assertEqual(p["sem_base"], ["Nine-Tailed Fox"])
        fox = next(c for c in p["cards"] if c["card_key"] == "nine-tailed fox")
        self.assertTrue(fox["sem_base"])
        self.assertEqual(fox["compra"]["id"], None)
        self.assertEqual((fox["need"], fox["have"], fox["missing"]), (2, 0, 2))
        # E não se tapa com a sobrenumerada: nem no modo de sempre isso
        # aconteceria aqui; no pool não há «outras».
        alloc = self.decks.allocate(con)
        kennen = next(r for r in self.decks.deck_rows(con) if r["name"] == "kennen")
        self.assertEqual(alloc[kennen["deck_id"]]["missing"]["nine-tailed fox"], 2)


class TestEntrarESair(Base):
    """3. `ajustar`: no `copies` E no local, de uma vez; a Coleção não mexe."""

    def test_mais_e_menos_nao_mexem_na_colecao(self):
        self.modo("pool_proprio")
        con = self.catalogo()
        antes = self.locais.na_colecao(con)
        r = self.pool.ajustar(con, "tst-001-100", 2, source="test")
        self.assertEqual((r["applied"], r["qty"], r["total"]), (2, 2, 5))
        self.assertEqual(self.collection.get_qty(con, "tst-001-100"), 5)
        self.assertEqual(self.locais.no_pool(con), {"tst-001-100": 2})
        self.assertEqual(self.locais.na_colecao(con), antes, "a Coleção fica onde estava")
        # O `−` tira do pool e do `copies`; nunca abaixo de zero no pool.
        r = self.pool.ajustar(con, "tst-001-100", -5, source="test")
        self.assertEqual((r["applied"], r["qty"], r["total"]), (-2, 0, 3))
        self.assertEqual(self.locais.no_pool(con), {})
        self.assertEqual(self.locais.na_colecao(con), antes)
        r = self.pool.ajustar(con, "tst-001-100", -1, source="test")
        self.assertEqual(r["applied"], 0)
        # Uma carta que ele não tem na Coleção entra na mesma — o pool é dele.
        r = self.pool.ajustar(con, "TST-002", 1, source="test")
        self.assertEqual((r["qty"], r["total"]), (1, 1))
        self.assertNotIn("tst-002-100", self.locais.na_colecao(con))

    def test_retry_com_o_mesmo_request_id_nao_conta_a_dobrar(self):
        self.modo("pool_proprio")
        con = self.catalogo()
        a = self.pool.ajustar(con, "tst-001-100", 1, source="test", request_id="r1")
        b = self.pool.ajustar(con, "tst-001-100", 1, source="test", request_id="r1")
        self.assertFalse(a["duplicate"])
        self.assertTrue(b["duplicate"])
        self.assertEqual(self.locais.no_pool(con), {"tst-001-100": 1})

    def test_deixa_rasto_na_ops_na_location_ops_e_no_log(self):
        self.modo("pool_proprio")
        con = self.catalogo()
        n_ops = con.execute("SELECT COUNT(*) AS n FROM ops").fetchone()["n"]
        self.pool.ajustar(con, "tst-001-100", 2, source="test")
        self.pool.ajustar(con, "tst-001-100", -1, source="test")
        self.assertEqual(con.execute("SELECT COUNT(*) AS n FROM ops").fetchone()["n"], n_ops + 2)
        movs = [(r["from_loc"], r["to_loc"], r["qty"]) for r in con.execute(
            "SELECT from_loc, to_loc, qty FROM location_ops ORDER BY id")]
        self.assertEqual(movs, [(self.pool.ENTROU, "pool-decks", 2),
                                ("pool-decks", self.pool.SAIU, 1)])
        log = (self.v.data / "locais.log").read_text(encoding="utf-8")
        self.assertIn("Pool dos decks", log)
        self.assertIn("(entrou no pool)", log)

    def test_o_local_aparece_no_resumo_e_no_tile_com_o_nome_certo(self):
        self.modo("pool_proprio")
        con = self.catalogo()
        self.pool.ajustar(con, "tst-001-100", 2, source="test")
        self.assertEqual(self.locais.rotulo("pool-decks"), "Pool dos decks")
        self.assertEqual(self.locais.normalizar("pool"), "pool-decks")
        resumo = {r["local"]: r["copies"] for r in self.locais.resumo(con)}
        self.assertEqual(resumo["pool-decks"], 2)
        sp = self.metrics.set_payload(con, "TST")
        defy = next(p for g in sp["groups"] for p in g["printings"] if p["id"] == "tst-001-100")
        self.assertEqual(defy["qty"], 3, "a badge é a Coleção")
        self.assertEqual(defy["qty_total"], 5)
        self.assertEqual(defy["qty_valor"], 3, "o valor não conta o pool")
        self.assertIn({"loc": "pool-decks", "label": "Pool dos decks", "qty": 2}, defy["locations"])


class TestColecaoIntacta(Base):
    """4. Com o modo ligado, a Coleção não sabe que há decks."""

    def test_da_exactamente_o_mesmo_que_sem_decks_nenhuns(self):
        self.modo("pool_proprio")
        con = self.catalogo()
        self.pool.ajustar(con, "tst-001-100", 2, source="test")
        self.pool.ajustar(con, "tst-004-100", 1, source="test")
        com_decks = self.fotografia(con)
        for f in self.v.decks_dir.glob("*.txt"):
            f.unlink()
        self.decks.import_all(con, log=lambda *_: None)
        self.assertEqual(self.decks.deck_rows(con), [])
        sem_decks = self.fotografia(con)
        self.assertEqual(com_decks, sem_decks)
        # E o que se fixa por dentro: nenhum uso de decks na grelha, nada
        # libertado, nada «para» deck nas Encomendas, nada usado no A mais.
        cd = com_decks["com_decks"]
        self.assertEqual(cd["usos"], {})
        self.assertEqual(cd["libertadas"], {"cards": 0, "copies": 0})
        self.assertEqual(cd["encomendas_decks"][0], {"cards": 0, "copies": 0, "cents": 0})
        self.assertTrue(all(u == 0 for itens in cd["a_mais"].values() for _, _, _, u in itens))
        self.assertTrue(any(cd["a_mais"].values()), "o excedente verdadeiro está lá (as 2 Salvage)")

    def test_o_pool_nao_conta_para_a_colecao_nem_para_o_valor(self):
        self.modo("pool_proprio")
        con = self.catalogo()
        antes = self.fotografia(con)
        self.pool.ajustar(con, "tst-001-100", 2, source="test")
        self.pool.ajustar(con, "tst-002-100", 3, source="test")
        depois = self.fotografia(con)
        self.assertEqual(antes, depois, "meter 5 cópias no pool não mexe em NADA da Coleção")
        self.assertEqual(self.metrics.owned_by_card(con)["defy"], 3, "o playset jogável não vê o pool")
        self.assertNotIn("brutalizer", self.metrics.owned_by_card(con))
        # Só o `copies` cresceu.
        self.assertEqual(self.collection.get_qty(con, "tst-002-100"), 3)

    def test_o_a_mais_e_o_excedente_verdadeiro_face_aos_alvos(self):
        # Salvage: 5 na Coleção, alvo 3, os decks pedem 2 + 3 = 5.
        self.modo("coleccao")
        con = self.catalogo()
        am = self.a_mais.payload(con)
        salv = [x for s in am["sets"] for x in s["excedente"]["items"] if x["printing_id"] == "tst-004-100"]
        self.assertEqual(salv, [], "no modo de sempre os decks levam as 5 e nada sobra")
        self.assertEqual(am["modo"], "coleccao")
        self.modo("pool_proprio")
        am = self.a_mais.payload(con)
        salv = [x for s in am["sets"] for x in s["excedente"]["items"] if x["printing_id"] == "tst-004-100"]
        self.assertEqual(len(salv), 1)
        self.assertEqual((salv[0]["extra"], salv[0]["have"], salv[0]["used"]), (2, 5, 0))
        self.assertEqual(am["modo"], "pool_proprio")
        self.assertEqual(am["totals"]["libertadas"], {"cards": 0, "copies": 0})

    def test_a_grelha_nao_diz_que_decks_usam_a_carta(self):
        self.modo("coleccao")
        con = self.catalogo()
        sp = self.metrics.set_payload(con, "TST")
        self.assertTrue(any(g["decks"] for g in sp["groups"]))
        self.modo("pool_proprio")
        sp = self.metrics.set_payload(con, "TST")
        self.assertFalse(any(g["decks"] for g in sp["groups"]))
        self.assertEqual(self.decks.uso_por_carta(con), {})
        self.assertEqual(self.metrics.index_payload(con)["modo_decks"], "pool_proprio")
        # E o «Marcar o que este deck usa» não propõe nada.
        self.assertEqual(self.locais.propor_deck(con, "azir")["items"], [])


class TestReversivel(Base):
    """5. Voltar a `coleccao` repõe os números de hoje ao exemplar."""

    def test_voltar_atras_e_so_mudar_a_chave(self):
        self.modo("coleccao")
        con = self.catalogo()
        hoje = self.fotografia(con)
        alloc_hoje = {k: (a["alloc"], a["missing"], a["na_colecao"]) for k, a in self.decks.allocate(con).items()}
        self.assertTrue(any(a["na_colecao"] for a in self.decks.allocate(con).values()),
                        "no modo de sempre os decks servem-se da Coleção")
        self.assertTrue(hoje["com_decks"]["usos"], "e a grelha diz quem as usa")
        self.modo("pool_proprio")
        pool = self.fotografia(con)
        self.assertEqual(pool["numeros"], hoje["numeros"],
                         "com o pool vazio os NÚMEROS da Coleção são os de hoje")
        # O que muda de propósito: a vista deixa de ver os decks (o A mais
        # sobe para o excedente verdadeiro — as 2 Salvage).
        self.assertEqual(pool["com_decks"]["usos"], {})
        self.assertNotEqual(pool["com_decks"]["a_mais"], hoje["com_decks"]["a_mais"])
        for a in self.decks.allocate(con).values():
            self.assertEqual(a["na_colecao"], {})
            self.assertEqual(a["alloc"], {}, "o pool está a zero: os decks não têm nada")
        self.modo("coleccao")
        self.assertEqual(self.fotografia(con), hoje, "voltar atrás repõe tudo ao exemplar")
        self.assertEqual({k: (a["alloc"], a["missing"], a["na_colecao"])
                          for k, a in self.decks.allocate(con).items()}, alloc_hoje)

    def test_modo_desconhecido_rebenta(self):
        self.modo("pool")
        with self.assertRaises(ValueError):
            self.decks.modo()
        self.modo("coleccao")
        self.assertEqual(self.decks.modo(), "coleccao")
        self.assertFalse(self.decks.pool_proprio())

    def test_sem_a_chave_e_coleccao(self):
        os.environ["RIFTVAULT_CONFIG"] = str(Path(tempfile.gettempdir()) / "riftvault-nao-existe.json")
        importlib.reload(self.config)
        self.config.load.cache_clear()
        self.assertEqual(self.decks.modo(), "coleccao")
        self.assertEqual(self.config.DEFAULTS["decks"]["modo"], "coleccao")


class TestRotasBuildCLI(Base):
    """6. As rotas, o site publicado, a CLI."""

    def test_as_rotas_respondem_e_o_ajustar_recusa_o_que_nao_e_base(self):
        self.modo("pool_proprio")
        con = self.catalogo()
        con.close()
        from riftvault import server
        importlib.reload(server)
        app = server.app
        app.testing = True
        with app.test_client() as c:
            d = c.get("/api/decks.json").get_json()
            self.assertEqual(d["modo"], "pool_proprio")
            p = c.get("/api/pool.json").get_json()
            self.assertTrue(p["editable"])
            self.assertEqual(p["totals"]["have"], 0)
            r = c.post("/api/pool/ajustar", json={"printing_id": "tst-001-100", "delta": 2})
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.get_json()["qty"], 2)
            r = c.post("/api/pool/ajustar", json={"printing_id": "tst-001a-100", "delta": 1})
            self.assertEqual(r.status_code, 400, "a alt art não entra no pool")
            r = c.post("/api/pool/ajustar", json={"printing_id": "nao-existe", "delta": 1})
            self.assertEqual(r.status_code, 404)
            r = c.post("/api/pool/ajustar", json={"printing_id": "tst-001-100", "delta": 0})
            self.assertEqual(r.status_code, 400)
            p = c.get("/api/pool.json").get_json()
            self.assertEqual(p["totals"]["have"], 2)
            # A Coleção não mexeu.
            g = c.get("/api/set/TST.json").get_json()
            defy = next(x for grp in g["groups"] for x in grp["printings"] if x["id"] == "tst-001-100")
            self.assertEqual(defy["qty"], 3)
            self.assertEqual(g["groups"][0]["decks"], [])
            self.assertEqual(c.get("/api/index.json").get_json()["modo_decks"], "pool_proprio")

    def test_o_site_publicado_leva_o_pool_sem_controlos(self):
        self.modo("pool_proprio")
        con = self.catalogo()
        self.pool.ajustar(con, "tst-001-100", 1, source="test")
        con.close()
        from riftvault import build
        importlib.reload(build)
        out = self.v.root / "site"
        build.build(out, log=lambda *_: None)
        f = out / "api" / "pool.json"
        self.assertTrue(f.exists(), "falta api/pool.json no site")
        p = json.loads(f.read_text(encoding="utf-8"))
        self.assertFalse(p["editable"])
        self.assertEqual(p["totals"]["have"], 1)
        d = json.loads((out / "api" / "decks.json").read_text(encoding="utf-8"))
        self.assertEqual(d["modo"], "pool_proprio")

    def test_a_cli_mete_e_tira_e_escreve_a_wantlist(self):
        self.modo("pool_proprio")
        con = self.catalogo()
        con.close()
        from riftvault import cli
        importlib.reload(cli)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = cli.main(["pool", "--mais", "TST-001", "2"])
        self.assertEqual(rc, 0)
        self.assertIn("2 no pool", out.getvalue())
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            cli.main(["pool"])
        self.assertIn("Pool dos decks", out.getvalue())
        self.assertIn("Defy", out.getvalue())
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            cli.main(["pool", "--cardmarket"])
        self.assertIn("2 Defy", out.getvalue(), "faltam 2 Defy ao pool (4 − 2)")
        self.assertNotIn("€", out.getvalue(), "o total fica fora do texto")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            cli.main(["decks"])
        self.assertIn("pool_proprio", out.getvalue())
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            rc = cli.main(["pool", "--mais", "TST-001a"])
        self.assertEqual(rc, 1, "a alt art é recusada")
        con = self.v.connect()
        self.assertEqual(self.locais.no_pool(con), {"tst-001-100": 2})
        con.close()

    def test_a_wantlist_do_pool_e_o_gerador_unico(self):
        self.modo("pool_proprio")
        con = self.catalogo()
        w = self.pool.wantlist(con)
        self.assertEqual(w["copies"], 12)
        self.assertEqual(w["lines"], 6)
        self.assertIn("4 Defy", w["text"])
        from riftvault import cardmarket
        self.assertEqual(w["text"], "\n".join(cardmarket.linha(x) for x in w["items"]))


class TestFrontend(unittest.TestCase):
    """O `app.js` pede o pool, tem a aba, esconde as abas de compra e o
    filtro «Em decks» no modo do pool; o `index.html` não precisou de mexer."""

    def setUp(self):
        self.js = (REPO / "riftvault" / "web" / "app.js").read_text(encoding="utf-8")

    def test_a_aba_do_pool(self):
        for s in ("api/pool.json", "api/pool/ajustar", "Pool dos decks", "pool_proprio",
                  "function renderPool", "function poolAjustar", "POOL_TAB"):
            self.assertIn(s, self.js, s)

    def test_as_abas_de_compra_e_o_filtro_em_decks_saem_no_modo_do_pool(self):
        self.assertIn("decksPool() ? [] : DECK_FALTA_TABS", self.js)
        self.assertIn('data-state="indeck"', self.js)
        self.assertIn("modo_decks", self.js)
        self.assertIn("renderAMaisPool", self.js)


if __name__ == "__main__":
    unittest.main()

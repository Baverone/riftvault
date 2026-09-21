"""As CÓPIAS PRÓPRIAS de cada deck (André, 2026-09-21, `proprias.py`).

Palavras dele: *"voltamos aos decks usarem a coleccao, mas cada deck precisa
de ter as cartas proprias; colocas em cada deck o + e - para eu dizer se
afinal tenho ou nao; estas copias que eu coloco nos decks nao sao para
adicionar a coleccao"*. Acaba a experiência do pool próprio dessa manhã.

O que se fixa:
  1. os decks voltam a usar a Coleção (a grelha diz «Azir 3», o filtro, as
     libertadas, o «para» das Encomendas); NÃO partilham entre si — a SOMA,
     não o máximo; main e sideboard somam; runas fora;
  2. só versões base (`decks.so_base`), a Legend e o Champion incluídos; a
     regra de 2026-09-17 não volta só por o modo ser `coleccao`; `false`
     sozinho = qualquer versão não assinada serve;
  3. as próprias: `ajustar` escreve no `copies` E no local `proprio:<slug>`
     de uma vez; `−` nunca abaixo de zero; retry não dobra; recusa o que não
     serve; deck desconhecido rebenta;
  4. servem PRIMEIRO e libertam a Coleção; `faltam = precisa − próprias − o
     que a Coleção alocou`; são só daquele deck; as que não servem dizem-se;
  5. NÃO ENTRAM NA COLEÇÃO: meter e tirar próprias não mexe um número —
     níveis, denominador, wantlists, Faltas, Encomendas, valor, playset
     jogável, grelha, A mais; a decisão do valor;
  6. `pool_proprio` rebenta; as rotas, o build, a CLI e o `app.js`.

Tudo contra pastas temporárias (`tests.fixture.Vault`) e um config temporário
(`RIFTVAULT_CONFIG`): o `data/` e o `riftvault_config.json` a sério nunca são
tocados.
"""

from __future__ import annotations

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
                               faltas_edicao, locais, metrics, pending, prices, proprias)
        for m in (locais, metrics, decks, proprias, a_subir, faltas_edicao, a_mais,
                  pending, faltas, prices):
            importlib.reload(m)
        self.config, self.decks, self.proprias, self.locais = config, decks, proprias, locais
        self.metrics, self.a_subir, self.faltas_edicao = metrics, a_subir, faltas_edicao
        self.a_mais, self.pending, self.faltas, self.prices = a_mais, pending, faltas, prices
        self.collection = collection
        self.cfg_decks({})

    def cfg_decks(self, decks_extra: dict, extra: dict | None = None):
        """Escreve o config temporário com o bloco `decks` de hoje (os defaults
        do código) mais o que o teste quiser, e relê-o."""
        caminho = self.v.root / "config.json"
        caminho.write_text(json.dumps({"decks": {"so_base": True, "so_normais_excepto": [],
                                                 "versoes_especiais": ["a", "overnumbered", "promo"],
                                                 "modo": "coleccao", **decks_extra},
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

    def por_slug(self, con) -> dict:
        alloc = self.decks.allocate(con)
        return {r["name"]: alloc[r["deck_id"]] for r in self.decks.deck_rows(con)}

    def deck_id(self, con, slug) -> int:
        return next(r["deck_id"] for r in self.decks.deck_rows(con) if r["name"] == slug)

    def fotografia(self, con) -> dict:
        """Tudo o que é NÚMERO DA COLEÇÃO, para comparar antes e depois de
        mexer nas cópias próprias: níveis, denominador, wantlist, valor,
        totais, grelha (qty, alvo, o que vale), playset jogável, barra,
        Faltas, Encomendas, e no A mais o `have` e o `extra` de cada item."""
        cfg = self.config.load()
        sp = self.metrics.set_payload(con, "TST")
        fe = self.faltas_edicao.payload(con, cfg)
        enc = self.pending.encomendas(con)
        am = self.a_mais.payload(con, cfg)
        return {
            "niveis": [(l["k"], l["done"], l["total"], l["missing"], l["cents"])
                       for l in self.metrics.niveis_payload(con, cfg)["levels"]],
            "wantlist": {k: self.a_subir.wantlist(con, cfg=cfg)[k]
                         for k in ("text", "lines", "copies", "cents")},
            "valor": self.prices.collection_value(con)["cents"],
            "valor_copias": self.prices.collection_value(con)["copias"],
            "valor_por_set": self.prices.value_by_set(con),
            "top": self.prices.top_value(con),
            "totais": self.collection.totals(con),
            "grelha": [(p["id"], p["qty"], p["target"], p["qty_valor"])
                       for g in sp["groups"] for p in g["printings"]],
            "playset": {g["card_key"]: g["playset"] for g in sp["groups"]},
            "owned_by_card": self.metrics.owned_by_card(con),
            "value_owned": sp["progress"]["value"]["owned"],
            "master": sp["progress"]["master"],
            "painel": sp["progress"]["painel"],
            "faltas": (fe["totals"], fe["totals_lists"],
                       [(s["set"], b["id"], b["cards"], b["copies"], b["cents"])
                        for s in fe["sets"] for b in s["blocks"]]),
            "encomendas": enc["totals"],
            "a_mais": {s["set"]: [(x["printing_id"], x["extra"], x["have"])
                                  for x in s["excedente"]["items"]] for s in am["sets"]},
        }


# ---------------------------------------------------------------------------


class TestOsDecksUsamAColecaoESomam(Base):
    """1. A Coleção volta a servir os decks; a SOMA, não o máximo; runas fora."""

    def test_o_que_os_decks_precisam_e_a_soma(self):
        con = self.catalogo()
        ps = self.por_slug(con)
        # Defy: Azir 3 + 1 (sideboard somam) = 4; Ornn 2 — precisam de 6 ao
        # todo, não de 4 (o máximo era o pool). A Coleção tem 3.
        self.assertEqual(ps["azir"]["grupo"]["need"]["defy"], 4)
        self.assertEqual(ps["ornn"]["grupo"]["need"]["defy"], 2)
        self.assertEqual(sum(a["grupo"]["need"]["defy"] for a in ps.values()), 6)
        # O Azir (prioridade 1) leva as 3 da Coleção e falta-lhe 1; o Ornn não
        # recebe nenhuma e falta-lhe 2 — disputadas, e compram-se na mesma.
        self.assertEqual(ps["azir"]["alloc"]["defy"], 3)
        self.assertEqual(ps["azir"]["na_colecao"]["defy"], 3)
        self.assertEqual(ps["azir"]["missing"]["defy"], 1)
        self.assertNotIn("defy", ps["ornn"]["alloc"])
        self.assertEqual(ps["ornn"]["missing"]["defy"], 2)
        self.assertEqual(ps["ornn"]["shared"]["defy"]["qty"], 2)
        # Salvage: 2 + 3 = 5, a Coleção tem 5 — chega para os dois.
        self.assertEqual((ps["azir"]["alloc"]["salvage"], ps["ornn"]["alloc"]["salvage"]), (2, 3))
        # Total a comprar: Defy 1 + 2, Hidden Blade 1 + 2 (a alt art não
        # serve), Brutalizer 1, Fire Below 1 = 8 cópias de 4 cartas.
        rf = self.decks.resumo_das_faltas(con)
        self.assertEqual((rf["copies"], rf["cards"], rf["disputed"]), (8, 4, 2))
        # As runas ficam fora de tudo.
        for a in ps.values():
            self.assertNotIn("fury rune", a["grupo"]["need"])
        idx = {d["slug"]: d for d in self.decks.decks_index(con)}
        self.assertEqual((idx["azir"]["wanted"], idx["ornn"]["wanted"]), (9, 8))
        self.assertEqual(idx["azir"]["runas"]["copies"], 3)

    def test_a_colecao_volta_a_saber_dos_decks(self):
        con = self.catalogo()
        uso = self.decks.uso_por_carta(con)
        self.assertEqual([(u["deck"], u["wanted"], u["have"], u["missing"]) for u in uso["defy"]],
                         [("Azir", 4, 3, 1), ("Ornn", 2, 0, 2)])
        sp = self.metrics.set_payload(con, "TST")
        self.assertTrue(any(g["decks"] for g in sp["groups"]), "a grelha diz «Azir 4»")
        # O A mais desconta o que os decks usam (as 5 Salvage estão todas em uso).
        am = self.a_mais.payload(con)
        self.assertEqual([x for s in am["sets"] for x in s["excedente"]["items"]
                          if x["printing_id"] == "tst-004-100"], [])
        # E o «Marcar o que este deck usa» propõe as da Coleção.
        self.assertTrue(self.locais.propor_deck(con, "azir")["items"])


class TestSoBase(Base):
    """2. Só versões base — a Legend e o Champion incluídos (`decks.so_base`)."""

    def test_so_base_e_a_omissao_e_a_regra_de_17_09_nao_volta(self):
        self.assertTrue(self.config.DEFAULTS["decks"]["so_base"])
        self.assertEqual(self.config.DEFAULTS["decks"]["so_normais_excepto"], [])
        con = self.catalogo()
        self.assertTrue(self.decks.so_base())
        versoes = self.decks.versoes_dos_decks(con)
        self.assertEqual(versoes.especiais, {})
        self.assertEqual(versoes.papeis, frozenset())
        self.assertEqual(versoes.normais_de("emperor of the sands"), ["tst-003-100"])
        self.assertEqual(versoes.compra("emperor of the sands"), "tst-003-100")
        ps = self.por_slug(con)
        for a in ps.values():
            self.assertEqual(a["need_especial"], {})
            self.assertEqual(a["missing_especial"], {})
        # A alt art da Hidden Blade na Coleção NÃO serve o Azir: falta 1.
        self.assertEqual(ps["azir"]["missing"]["hidden blade"], 1)
        self.assertEqual(ps["azir"]["alloc_outras"], {})
        p = self.decks.deck_payload(con, self.deck_id(con, "azir"))
        self.assertTrue(p["so_base"])
        legend = next(c for s in p["sections"] if s["role"] == "legend" for c in s["cards"])
        self.assertIsNone(legend["especial"])
        self.assertEqual(legend["order_code"], "TST-003/100")
        self.assertEqual(legend["have"], 1, "a Legend joga a base que ele tem")

    def test_mesmo_com_os_papeis_escritos_so_base_manda(self):
        self.cfg_decks({"so_normais_excepto": ["legend", "champion"]})
        con = self.catalogo()
        versoes = self.decks.versoes_dos_decks(con)
        self.assertEqual(versoes.papeis, frozenset())
        self.assertEqual(versoes.especiais, {})
        ps = self.por_slug(con)
        self.assertEqual(ps["azir"]["need_especial"], {})
        self.assertEqual(ps["azir"]["alloc"]["emperor of the sands"], 1)

    def test_desligar_so_base_sozinho_da_qualquer_versao(self):
        # Só a chave `so_base` muda; `so_normais_excepto` fica vazio (o de hoje).
        self.cfg_decks({"so_base": False})
        con = self.catalogo()
        self.assertFalse(self.decks.so_base())
        ps = self.por_slug(con)
        # A alt art da Hidden Blade passa a tapar o lugar do Azir (a diferença
        # do «36 de 18» do André: 1x Vi, Peacekeeper em UNL-176a).
        self.assertNotIn("hidden blade", ps["azir"]["missing"])
        self.assertEqual(ps["azir"]["alloc_outras"]["hidden blade"], 1)
        # E a Legend continua na base — sem papéis, não há lugar especial.
        self.assertEqual(ps["azir"]["need_especial"], {})
        rf = self.decks.resumo_das_faltas(con)
        self.assertEqual((rf["copies"], rf["cards"]), (7, 4))

    def test_com_so_base_false_e_os_papeis_a_regra_de_17_09_volta(self):
        self.cfg_decks({"so_base": False, "so_normais_excepto": ["legend", "champion"]})
        con = self.catalogo()
        ps = self.por_slug(con)
        # A Legend do Azir pede a sobrenumerada, que ele não tem.
        self.assertEqual(ps["azir"]["need_especial"], {"emperor of the sands": 1})
        self.assertEqual(ps["azir"]["missing_especial"], {"emperor of the sands": 1})


class TestEntrarESair(Base):
    """3. `ajustar`: no `copies` E no local `proprio:<slug>`, de uma vez."""

    def test_mais_e_menos_nao_mexem_na_colecao(self):
        con = self.catalogo()
        antes = self.locais.na_colecao(con)
        r = self.proprias.ajustar(con, "azir", "tst-001-100", 2, source="test")
        self.assertEqual((r["deck"], r["applied"], r["qty"], r["total"]), ("azir", 2, 2, 5))
        self.assertEqual(self.collection.get_qty(con, "tst-001-100"), 5)
        self.assertEqual(self.locais.proprias(con), {"azir": {"tst-001-100": 2}})
        self.assertEqual(self.locais.proprias_de(con, "azir"), {"tst-001-100": 2})
        self.assertEqual(self.locais.na_colecao(con), antes, "a Coleção fica onde estava")
        # O `−` tira das próprias e do `copies`; nunca abaixo de zero.
        r = self.proprias.ajustar(con, "azir", "tst-001-100", -5, source="test")
        self.assertEqual((r["applied"], r["qty"], r["total"]), (-2, 0, 3))
        self.assertEqual(self.locais.proprias(con), {})
        self.assertEqual(self.locais.na_colecao(con), antes)
        r = self.proprias.ajustar(con, "azir", "tst-001-100", -1, source="test")
        self.assertEqual(r["applied"], 0)
        # Uma carta que ele não tem na Coleção entra na mesma — é do deck.
        r = self.proprias.ajustar(con, "azir", "TST-002", 1, source="test")
        self.assertEqual((r["qty"], r["total"]), (1, 1))
        self.assertNotIn("tst-002-100", self.locais.na_colecao(con))

    def test_retry_com_o_mesmo_request_id_nao_conta_a_dobrar(self):
        con = self.catalogo()
        a = self.proprias.ajustar(con, "azir", "tst-001-100", 1, source="test", request_id="r1")
        b = self.proprias.ajustar(con, "azir", "tst-001-100", 1, source="test", request_id="r1")
        self.assertFalse(a["duplicate"])
        self.assertTrue(b["duplicate"])
        self.assertEqual(self.locais.proprias_de(con, "azir"), {"tst-001-100": 1})

    def test_recusa_o_que_nao_serve_e_o_deck_desconhecido(self):
        con = self.catalogo()
        with self.assertRaises(self.proprias.NaoServe):
            self.proprias.ajustar(con, "azir", "tst-001a-100", 1, source="test")
        with self.assertRaises(self.proprias.NaoServe):
            self.proprias.ajustar(con, "azir", "tst-101-100", 1, source="test")
        with self.assertRaises(self.proprias.DeckDesconhecido):
            self.proprias.ajustar(con, "kennen", "tst-001-100", 1, source="test")
        self.assertEqual(self.locais.proprias(con), {})
        # Com `so_base: false` a alt art já serve — e entra.
        self.cfg_decks({"so_base": False})
        r = self.proprias.ajustar(con, "azir", "tst-001a-100", 1, source="test")
        self.assertEqual(r["qty"], 1)

    def test_deixa_rasto_na_ops_na_location_ops_e_no_log(self):
        con = self.catalogo()
        n_ops = con.execute("SELECT COUNT(*) AS n FROM ops").fetchone()["n"]
        self.proprias.ajustar(con, "azir", "tst-001-100", 2, source="test")
        self.proprias.ajustar(con, "azir", "tst-001-100", -1, source="test")
        self.assertEqual(con.execute("SELECT COUNT(*) AS n FROM ops").fetchone()["n"], n_ops + 2)
        movs = [(r["from_loc"], r["to_loc"], r["qty"]) for r in con.execute(
            "SELECT from_loc, to_loc, qty FROM location_ops ORDER BY id")]
        self.assertEqual(movs, [(self.proprias.ENTROU, "proprio:azir", 2),
                                ("proprio:azir", self.proprias.SAIU, 1)])
        log = (self.v.data / "locais.log").read_text(encoding="utf-8")
        self.assertIn("Cópias próprias do deck Azir", log)
        self.assertIn("(entrou como cópia própria)", log)

    def test_o_local_aparece_no_resumo_e_no_tile_com_o_nome_certo(self):
        con = self.catalogo()
        self.proprias.ajustar(con, "azir", "tst-001-100", 2, source="test")
        self.assertEqual(self.locais.rotulo("proprio:azir", {"azir": "Azir"}),
                         "Cópias próprias do deck Azir")
        self.assertEqual(self.locais.normalizar("proprio:Azir"), "proprio:azir")
        resumo = {r["local"]: r["copies"] for r in self.locais.resumo(con)}
        self.assertEqual(resumo["proprio:azir"], 2)
        sp = self.metrics.set_payload(con, "TST")
        defy = next(p for g in sp["groups"] for p in g["printings"] if p["id"] == "tst-001-100")
        self.assertEqual(defy["qty"], 3, "a badge é a Coleção")
        self.assertEqual(defy["qty_total"], 5)
        self.assertEqual(defy["qty_valor"], 3, "o valor não conta as próprias")
        self.assertIn({"loc": "proprio:azir", "label": "Cópias próprias do deck Azir", "qty": 2},
                      defy["locations"])

    def test_um_menos_na_grelha_alem_da_colecao_tira_das_proprias(self):
        con = self.catalogo()
        # O Brutalizer só existe como própria do Azir: copies 1, Coleção 0.
        self.proprias.ajustar(con, "azir", "tst-002-100", 1, source="test")
        self.collection.adjust(con, "tst-002-100", -1, source="test")
        self.assertEqual(self.collection.get_qty(con, "tst-002-100"), 0)
        self.assertEqual(self.locais.proprias_de(con, "azir"), {})


class TestServemPrimeiroESoAoDeck(Base):
    """4. As próprias servem antes da Coleção, libertam-na, e são só daquele deck."""

    def test_as_proprias_servem_primeiro_e_libertam_a_colecao(self):
        con = self.catalogo()
        antes = self.por_slug(con)
        self.assertEqual((antes["azir"]["na_colecao"]["defy"], antes["ornn"]["missing"]["defy"]), (3, 2))
        # O Azir diz que tem 3 Defy guardadas para ele.
        self.proprias.ajustar(con, "azir", "tst-001-100", 3, source="test")
        ps = self.por_slug(con)
        azir, ornn = ps["azir"], ps["ornn"]
        # Azir: 3 próprias + 1 da Coleção (a do sideboard) = 4; falta 0.
        self.assertEqual(azir["proprias"]["defy"], 3)
        self.assertEqual(azir["alloc"]["defy"], 4)
        self.assertEqual(azir["na_colecao"]["defy"], 1)
        self.assertNotIn("defy", azir["missing"])
        # A Coleção ficou com 2 livres: o Ornn leva-as e deixa de faltar.
        self.assertEqual(ornn["na_colecao"]["defy"], 2)
        self.assertNotIn("defy", ornn["missing"])
        self.assertEqual(ornn["shared"], {})
        # faltam(deck) = precisa − próprias − o que a Coleção alocou.
        idx = {d["slug"]: d for d in self.decks.decks_index(con)}
        for slug in ("azir", "ornn"):
            d = idx[slug]
            self.assertEqual(d["missing"], d["wanted"] - d["proprias"]
                             - (d["no_deck"] + d["no_binder"] + d["na_colecao"]) - d["ordered"])
        self.assertEqual((idx["azir"]["proprias"], idx["ornn"]["proprias"]), (3, 0))
        rf = self.decks.resumo_das_faltas(con)
        self.assertEqual((rf["copies"], rf["disputed"]), (8 - 1 - 2, 0))
        # A grelha diz que o Azir pede 1 à Coleção (mais 3 próprias) e o Ornn 2.
        uso = self.decks.uso_por_carta(con)["defy"]
        self.assertEqual([(u["deck"], u["wanted"], u["have"], u["proprias"]) for u in uso],
                         [("Azir", 1, 1, 3), ("Ornn", 2, 2, 0)])

    def test_as_proprias_de_um_deck_nao_servem_outro(self):
        con = self.catalogo()
        self.proprias.ajustar(con, "ornn", "tst-001-100", 2, source="test")
        ps = self.por_slug(con)
        # O Ornn cobre-se com as suas; o Azir continua a levar as 3 da Coleção
        # e a faltar-lhe 1 — as do Ornn não são dele.
        self.assertEqual((ps["ornn"]["proprias"]["defy"], ps["ornn"]["alloc"]["defy"]), (2, 2))
        self.assertNotIn("defy", ps["ornn"]["missing"])
        self.assertEqual(ps["azir"]["alloc"]["defy"], 3)
        self.assertEqual(ps["azir"]["missing"]["defy"], 1)
        self.assertEqual(ps["azir"]["proprias"], {})
        # Uma carta toda coberta por próprias deixa de aparecer na grelha
        # como uso da Coleção — o Ornn não pede Defy à Coleção.
        uso = self.decks.uso_por_carta(con)["defy"]
        self.assertEqual([u["deck"] for u in uso], ["Azir"])

    def test_as_que_nao_servem_dizem_se_com_o_motivo(self):
        con = self.catalogo()
        # 5 Defy próprias do Azir: a lista pede 4 -> 1 acima; Brutalizer
        # próprio do Ornn: a lista não o pede; a alt art pela porta de trás.
        self.proprias.ajustar(con, "azir", "tst-001-100", 5, source="test")
        self.proprias.ajustar(con, "ornn", "tst-002-100", 1, source="test")
        self.locais.mover(con, "tst-005a-100", 1, "colecao", "proprio:azir", source="test")
        ps = self.por_slug(con)
        self.assertEqual(ps["azir"]["proprias"]["defy"], 4)
        self.assertEqual(ps["azir"]["proprias_fora"]["tst-001-100"],
                         {"qty": 1, "card_key": "defy", "motivo": "acima do que a lista pede"})
        self.assertEqual(ps["azir"]["proprias_fora"]["tst-005a-100"]["motivo"], "não é versão base")
        self.assertEqual(ps["azir"]["missing"]["hidden blade"], 1, "a alt art própria não tapa")
        self.assertEqual(ps["ornn"]["proprias_fora"]["tst-002-100"]["motivo"], "a lista não a pede")
        p = self.decks.deck_payload(con, self.deck_id(con, "azir"))
        self.assertEqual(sorted(x["printing_id"] for x in p["proprias_fora"]),
                         ["tst-001-100", "tst-005a-100"])
        self.assertEqual(p["locais"]["proprias_fora"], 2)
        self.assertEqual(p["locais"]["proprias"], 4)
        # Uma runa própria não é «fora» — a lista pede-a, só não se conta.
        self.proprias.ajustar(con, "azir", "tst-006-100", 2, source="test")
        ps = self.por_slug(con)
        self.assertNotIn("tst-006-100", ps["azir"]["proprias_fora"])
        self.assertNotIn("fury rune", ps["azir"]["proprias"])

    def test_a_pagina_do_deck_reparte_as_proprias_por_linha(self):
        con = self.catalogo()
        self.proprias.ajustar(con, "azir", "tst-001-100", 3, source="test")
        p = self.decks.deck_payload(con, self.deck_id(con, "azir"))
        main = next(s for s in p["sections"] if s["role"] == "main")
        side = next(s for s in p["sections"] if s["role"] == "sideboard")
        defy_m = next(c for c in main["cards"] if c["card_key"] == "defy")
        defy_s = next(c for c in side["cards"] if c["card_key"] == "defy")
        # As 3 do main são as próprias; a do sideboard vem da Coleção.
        self.assertEqual((defy_m["have"], defy_m["proprias"], defy_m["na_colecao"]), (3, 3, 0))
        self.assertEqual((defy_s["have"], defy_s["proprias"], defy_s["na_colecao"]), (1, 0, 1))
        self.assertEqual(defy_m["propria_compra"], {"id": "tst-001-100", "code": "TST-001/100"})
        self.assertEqual(defy_m["proprias_em"], [{"id": "tst-001-100", "code": "TST-001/100", "qty": 3}])
        self.assertTrue(all(x.get("propria") for x in defy_m["versoes"]))
        self.assertEqual(main["proprias"], 3)
        self.assertEqual(p["locais"]["proprias"], 3)
        self.assertEqual(p["local_proprias"], "proprio:azir")
        # A Legend sem próprias: o `+` grava na base.
        legend = next(c for s in p["sections"] if s["role"] == "legend" for c in s["cards"])
        self.assertEqual(legend["propria_compra"]["id"], "tst-003-100")
        self.assertEqual(legend["proprias_em"], [])
        # E a proposta de marcação já não propõe as 3 Defy tapadas.
        prop = self.locais.propor_deck(con, "azir")
        self.assertEqual(sum(x["qty"] for x in prop["items"] if x["card_key"] == "defy"), 1)

    def test_o_mais_por_nome_grava_na_base_em_que_se_compra(self):
        con = self.catalogo()
        self.assertEqual(self.proprias.impressao_para(con, "azir", "Defy"), "tst-001-100")
        self.assertEqual(self.proprias.impressao_para(con, "azir", "TST-001"), "tst-001-100")
        with self.assertRaises(self.collection.UnknownPrinting):
            self.proprias.impressao_para(con, "azir", "carta que não existe")


class TestNaoEntramNaColecao(Base):
    """5. Meter e tirar próprias não mexe UM número da Coleção."""

    def test_meter_e_tirar_proprias_nao_mexe_em_numero_nenhum_da_colecao(self):
        con = self.catalogo()
        antes = self.fotografia(con)
        # Uma carta que a Coleção tem (Defy), uma que não tem (Brutalizer), a
        # Legend, e em dois decks.
        self.proprias.ajustar(con, "azir", "tst-001-100", 3, source="test")
        self.proprias.ajustar(con, "azir", "tst-002-100", 2, source="test")
        self.proprias.ajustar(con, "azir", "tst-003-100", 1, source="test")
        self.proprias.ajustar(con, "ornn", "tst-001-100", 2, source="test")
        self.proprias.ajustar(con, "ornn", "tst-005-100", 2, source="test")
        durante = self.fotografia(con)
        self.assertEqual(durante, antes, "10 próprias em dois decks e NADA da Coleção mexeu")
        self.assertEqual(self.metrics.owned_by_card(con)["defy"], 3, "o playset jogável não as vê")
        self.assertNotIn("brutalizer", self.metrics.owned_by_card(con))
        self.assertEqual(self.metrics.owned_by_card(con)["hidden blade"], 1, "só a alt art da Coleção")
        # O `copies` cresceu (são físicas) e a alocação mudou (é o objectivo).
        self.assertEqual(self.collection.get_qty(con, "tst-001-100"), 8)
        # Ficam a faltar 1 Hidden Blade ao Azir (a alt art não serve) e a
        # Legend do Ornn: 8 − Defy (1 + 2) − Hidden Blade do Ornn 2 − Brutalizer 1.
        self.assertEqual(self.decks.resumo_das_faltas(con)["copies"], 8 - 1 - 2 - 2 - 1)
        self.proprias.ajustar(con, "azir", "tst-001-100", -3, source="test")
        self.proprias.ajustar(con, "ornn", "tst-005-100", -1, source="test")
        self.assertEqual(self.fotografia(con), antes, "tirar também não mexe")

    def test_as_proprias_nao_sao_excedente_nem_valem(self):
        con = self.catalogo()
        # 9 Defy próprias (a Coleção tem 3, alvo 3): nem uma aparece no A mais,
        # e o valor continua a ser o das 3 da Coleção.
        valor = self.prices.collection_value(con)["cents"]
        self.proprias.ajustar(con, "azir", "tst-001-100", 9, source="test")
        am = self.a_mais.payload(con)
        defy = [x for s in am["sets"] for x in s["excedente"]["items"] if x["printing_id"] == "tst-001-100"]
        self.assertEqual(defy, [])
        self.assertEqual(self.prices.collection_value(con)["cents"], valor)
        self.assertEqual(self.locais.contadas(con)["tst-001-100"], 3)
        self.assertEqual(self.collection.totals(con)["copies"], 3 + 5 + 1 + 1)

    def test_libertar_a_colecao_e_visivel_no_a_mais_pela_regra_de_sempre(self):
        # A ÚNICA coisa da página da Coleção que pode mexer, e não por contar
        # as próprias: o A mais é `cópias − max(usadas nos decks, alvo)`
        # (2026-09-17), e as próprias fazem descer as «usadas». Salvage: 5 na
        # Coleção, alvo 3, os decks usam 5 -> nada a mais; o Ornn com 3
        # próprias usa 0 da Coleção -> usadas 2 -> a mais 5 − 3 = 2.
        con = self.catalogo()
        am = self.a_mais.payload(con)
        self.assertEqual([x for s in am["sets"] for x in s["excedente"]["items"]
                          if x["printing_id"] == "tst-004-100"], [])
        self.proprias.ajustar(con, "ornn", "tst-004-100", 3, source="test")
        am = self.a_mais.payload(con)
        salv = [x for s in am["sets"] for x in s["excedente"]["items"] if x["printing_id"] == "tst-004-100"]
        self.assertEqual((salv[0]["extra"], salv[0]["have"], salv[0]["used"]), (2, 5, 2))
        # O `have` é o da Coleção (5) — as 3 próprias não estão lá dentro.


class TestOModo(Base):
    """6. `pool_proprio` acabou e rebenta; sem chave é `coleccao`."""

    def test_pool_proprio_rebenta_com_a_razao(self):
        self.cfg_decks({"modo": "pool_proprio"})
        with self.assertRaises(ValueError) as cm:
            self.decks.modo()
        self.assertIn("acabou", str(cm.exception))
        with self.assertRaises(ValueError):
            self.decks.so_base()
        self.cfg_decks({"modo": "pool"})
        with self.assertRaises(ValueError):
            self.decks.modo()
        self.cfg_decks({})
        self.assertEqual(self.decks.modo(), "coleccao")
        self.assertFalse(hasattr(self.decks, "pool_proprio"))
        self.assertFalse(hasattr(self.locais, "POOL"))

    def test_sem_a_chave_e_coleccao_e_so_base(self):
        os.environ["RIFTVAULT_CONFIG"] = str(Path(tempfile.gettempdir()) / "riftvault-nao-existe.json")
        importlib.reload(self.config)
        self.config.load.cache_clear()
        self.assertEqual(self.decks.modo(), "coleccao")
        self.assertTrue(self.decks.so_base())
        self.assertEqual(self.config.DEFAULTS["decks"]["modo"], "coleccao")

    def test_o_config_real_diz_coleccao_e_so_base(self):
        cfg = json.loads((REPO / "riftvault_config.json").read_text(encoding="utf-8"))
        self.assertEqual(cfg["decks"]["modo"], "coleccao")
        self.assertTrue(cfg["decks"]["so_base"])
        self.assertEqual(cfg["decks"]["so_normais_excepto"], [])


class TestRotasBuildCLI(Base):
    """As rotas, o site publicado, a CLI, o `app.js`."""

    def test_as_rotas_respondem_e_recusam_o_que_nao_serve(self):
        con = self.catalogo()
        con.close()
        from riftvault import server
        importlib.reload(server)
        app = server.app
        app.testing = True
        with app.test_client() as c:
            d = c.get("/api/decks.json").get_json()
            self.assertTrue(d["so_base"])
            self.assertNotIn("modo", d)
            self.assertEqual(c.get("/api/pool.json").status_code, 404, "o pool acabou")
            r = c.post("/api/proprias/ajustar",
                       json={"slug": "azir", "printing_id": "tst-001-100", "delta": 2})
            self.assertEqual(r.status_code, 200)
            self.assertEqual((r.get_json()["deck"], r.get_json()["qty"]), ("azir", 2))
            r = c.post("/api/proprias/ajustar",
                       json={"slug": "azir", "printing_id": "tst-001a-100", "delta": 1})
            self.assertEqual(r.status_code, 400, "a alt art não serve com so_base")
            r = c.post("/api/proprias/ajustar",
                       json={"slug": "kennen", "printing_id": "tst-001-100", "delta": 1})
            self.assertEqual(r.status_code, 404)
            r = c.post("/api/proprias/ajustar",
                       json={"slug": "azir", "printing_id": "nao-existe", "delta": 1})
            self.assertEqual(r.status_code, 404)
            r = c.post("/api/proprias/ajustar", json={"printing_id": "tst-001-100", "delta": 1})
            self.assertEqual(r.status_code, 400, "falta o slug")
            r = c.post("/api/proprias/ajustar",
                       json={"slug": "azir", "printing_id": "tst-001-100", "delta": 0})
            self.assertEqual(r.status_code, 400)
            azir = next(x for x in d["decks"] if x["slug"] == "azir")
            p = c.get(f"/api/deck/{azir['id']}.json").get_json()
            self.assertEqual(p["locais"]["proprias"], 2)
            # A Coleção não mexeu; a grelha diz que o Azir pede menos.
            g = c.get("/api/set/TST.json").get_json()
            defy = next(x for grp in g["groups"] for x in grp["printings"] if x["id"] == "tst-001-100")
            self.assertEqual(defy["qty"], 3)
            uso = next(grp["decks"] for grp in g["groups"] if grp["card_key"] == "defy")
            self.assertEqual([(u["deck"], u["wanted"], u["proprias"]) for u in uso],
                             [("Azir", 2, 2), ("Ornn", 2, 0)])
            self.assertNotIn("modo_decks", c.get("/api/index.json").get_json())

    def test_o_site_publicado_leva_as_proprias_sem_controlos(self):
        con = self.catalogo()
        self.proprias.ajustar(con, "azir", "tst-001-100", 1, source="test")
        con.close()
        from riftvault import build
        importlib.reload(build)
        out = self.v.root / "site"
        build.build(out, log=lambda *_: None)
        self.assertFalse((out / "api" / "pool.json").exists(), "o pool acabou")
        d = json.loads((out / "api" / "decks.json").read_text(encoding="utf-8"))
        self.assertTrue(d["so_base"])
        self.assertFalse(d["editable"])
        azir = next(x for x in d["decks"] if x["slug"] == "azir")
        self.assertEqual(azir["proprias"], 1)
        p = json.loads((out / "api" / "deck" / f"{azir['id']}.json").read_text(encoding="utf-8"))
        self.assertEqual(p["locais"]["proprias"], 1)

    def test_a_cli_mete_tira_e_lista(self):
        con = self.catalogo()
        con.close()
        from riftvault import cli
        importlib.reload(cli)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = cli.main(["proprias", "azir", "--mais", "TST-001", "2"])
        self.assertEqual(rc, 0)
        self.assertIn("2 próprias do deck azir", out.getvalue())
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = cli.main(["proprias", "azir", "--mais", "Brutalizer"])
        self.assertEqual(rc, 0, "por nome grava na base em que se compra")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            cli.main(["proprias"])
        self.assertIn("Azir", out.getvalue())
        self.assertIn("próprias", out.getvalue())
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            cli.main(["proprias", "azir"])
        self.assertIn("Defy", out.getvalue())
        self.assertIn("próprias 3", out.getvalue())
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            cli.main(["decks"])
        self.assertIn("próprias", out.getvalue())
        self.assertNotIn("pool", out.getvalue().lower().replace("rune pool", ""))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            cli.main(["deck", "azir"])
        self.assertIn("próprias 3", out.getvalue())
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            rc = cli.main(["proprias", "azir", "--mais", "TST-001a"])
        self.assertEqual(rc, 1, "a alt art é recusada")
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            rc = cli.main(["proprias", "--mais", "TST-001"])
        self.assertEqual(rc, 1, "sem o slug não há onde gravar")
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            rc = cli.main(["proprias", "azir", "--menos", "TST-001", "5"])
        self.assertEqual(rc, 0)
        con = self.v.connect()
        self.assertEqual(self.locais.proprias_de(con, "azir"), {"tst-002-100": 1})
        con.close()


class TestFrontend(unittest.TestCase):
    """O `app.js` tem os `+`/`−` das próprias em cada carta do deck e já não
    tem a aba do pool; o `index.html` não precisou de mexer."""

    def setUp(self):
        self.js = (REPO / "riftvault" / "web" / "app.js").read_text(encoding="utf-8")
        self.css = (REPO / "riftvault" / "web" / "style.css").read_text(encoding="utf-8")

    def test_os_mais_e_menos_das_proprias(self):
        for s in ("api/proprias/ajustar", "function propriasBotoes", "function propriasAjustar",
                  "steppers proprias", "propria_compra", "proprias_em", "propriaForaTile",
                  "proprias_fora", "so_base"):
            self.assertIn(s, self.js, s)
        self.assertIn("${propriasBotoes(c)}", self.js, "os botões estão no tile do deck")
        self.assertIn(".steppers.proprias", self.css)

    def test_o_pool_saiu_do_frontend(self):
        limpo = self.js.lower().replace("rune pool", "").replace("«pool\n  // dos decks» (a experiência", "")
        for s in ("api/pool", "pool_tab", "renderpool", "poolajustar", "renderamaispool",
                  "modo_decks", "decks_pool", "pool_proprio"):
            self.assertNotIn(s, limpo, s)
        self.assertNotIn("steppers.pool", self.css)


if __name__ == "__main__":
    unittest.main()

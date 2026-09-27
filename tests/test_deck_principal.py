"""O DECK PRINCIPAL (André, 2026-09-27, `principal.py`).

Palavras dele: *"os decks quero uma coisa / Deck Principal: neste caso LeBlanc
/ eu coloco + e - se tenho a carta no Deck / **a Colecao e soberana, nao e para
mexer** / todas as cartas do Deck sao Wantlist, as comuns e incomuns em Foil, /
caso eu ainda nao tenha marcado, usa da colecao mas aparece indicado: / Na
colecao aparece que esta a ser usado em X Deck / No deck aparece algo do
genero: X cartas em uso da colecao, ainda falta especifica para o deck / Se eu
'desfazer' o deck ou deixar de ser o principal, essas cartas passam a venda
(apenas se valerem pelo menos 0,50 euros)"*.

O que se fixa:
  1. `decks.principal` — um só; a relação com `montados` (o principal é sempre
     montado; desmontar despromove); sem chave não há principal; um nome que
     não casa avisa e não rebenta;
  2. a WANTLIST: `precisa − próprias`, uma carta marcada com `+` SAI; as
     comuns e incomuns em FOIL ao preço de foil (com o fallback contado), rara
     para cima a normal; as runas de fora; o texto pelo gerador único;
  3. as DUAS INDICAÇÕES: o tile da Coleção diz «em uso no deck X», a página do
     deck diz quantas vêm da Coleção e quantas faltam;
  4. A COLEÇÃO NÃO MUDA UM NÚMERO com um empréstimo — a fotografia de sempre;
  5. a DESPROMOÇÃO: só as de >= 0,50 € vão à Venda, as de menos CONTINUAM
     próprias, nada sai do `proprio:<slug>`, a linha diz de onde veio e
     tira-se de uma vez; o preço do critério é o que a Venda mostra;
  6. as rotas, o `build`, a CLI, o `app.js` e a nota do config.

Tudo contra pastas temporárias (`tests.fixture.Vault`) e um config temporário
(`RIFTVAULT_CONFIG`): o `data/` e o `riftvault_config.json` a sério nunca são
tocados.
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

# O deck principal de brincar: 3 Defy (comum -> foil), 1 Brutalizer (incomum
# -> foil), 1 Emperor (Legend, epic -> normal), 2 Salvage (rara -> normal), e
# 3 runas, que não se contam.
AZIR = ("Nome: Azir\n\nLegend:\n1 Emperor of the Sands\n\nChampion:\n1 Brutalizer\n\n"
        "MainDeck:\n3 Defy\n2 Salvage\n\nRune Pool:\n3 Fury Rune\n")
ORNN = ("Nome: Ornn\n\nLegend:\n1 Fire Below the Mountain\n\nMainDeck:\n2 Defy\n")


class Base(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.close)
        from riftvault import (a_mais, a_subir, collection, config, decks, faltas,
                               faltas_edicao, faltas_foil, foil, locais, metrics,
                               pending, prices, principal, proprias, venda)
        for m in (locais, metrics, decks, proprias, a_subir, faltas_edicao, a_mais,
                  pending, faltas, prices, foil, faltas_foil, venda, principal):
            importlib.reload(m)
        self.config, self.decks, self.proprias, self.locais = config, decks, proprias, locais
        self.metrics, self.a_subir, self.faltas_edicao = metrics, a_subir, faltas_edicao
        self.a_mais, self.pending, self.faltas, self.prices = a_mais, pending, faltas, prices
        self.collection, self.foil, self.faltas_foil = collection, foil, faltas_foil
        self.venda, self.principal = venda, principal
        self.cfg_decks({})

    def cfg_decks(self, decks_extra: dict, extra: dict | None = None):
        caminho = self.v.root / "config.json"
        caminho.write_text(json.dumps({"decks": {
            "so_base": True, "so_normais_excepto": [],
            "versoes_especiais": ["a", "overnumbered", "promo"],
            "modo": "coleccao", "montados": ["Azir", "Ornn"], **decks_extra},
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

    def catalogo(self, principal="Azir", decks=("azir", "ornn")):
        """Uma edição com uma carta de cada raridade que interessa.

        Defy comum (11 c, foil 502), Brutalizer incomum (20 c, SEM preço de
        foil — é o fallback), Emperor Legend epic (10 €), Salvage rara (3 €),
        Fury Rune (runa). Na Coleção: 3 Defy, 5 Salvage, 1 Emperor.
        """
        self.cfg_decks({"principal": principal} if principal else {})
        con = self.v.connect()
        v = self.v
        v.add_printing(con, "tst-001-100", "TST", 1, "Defy", rarity="common", size=100)
        v.add_printing(con, "tst-002-100", "TST", 2, "Brutalizer",
                       rarity="uncommon", size=100)
        v.add_printing(con, "tst-003-100", "TST", 3, "Emperor of the Sands",
                       card_type="Legend", rarity="epic", size=100)
        v.add_printing(con, "tst-004-100", "TST", 4, "Salvage", rarity="rare", size=100)
        v.add_printing(con, "tst-006-100", "TST", 6, "Fury Rune",
                       card_type="Rune", size=100)
        v.add_printing(con, "tst-007-100", "TST", 7, "Fire Below the Mountain",
                       card_type="Legend", rarity="epic", size=100)
        v.rebuild(con)
        for pid, c, cf in (("tst-001-100", 11, 502), ("tst-002-100", 20, None),
                           ("tst-003-100", 1000, None), ("tst-004-100", 300, None),
                           ("tst-006-100", 11, 90), ("tst-007-100", 500, None)):
            con.execute("INSERT INTO catalog.price_latest (printing_id, price_cents, "
                        "price_foil_cents) VALUES (?,?,?)", (pid, c, cf))
        self.collection.adjust(con, "tst-001-100", 3, source="t")
        self.collection.adjust(con, "tst-004-100", 5, source="t")
        self.collection.adjust(con, "tst-003-100", 1, source="t")
        if "azir" in decks:
            self.v.write_deck("azir", AZIR)
        if "ornn" in decks:
            self.v.write_deck("ornn", ORNN)
        self.decks.import_all(con, log=lambda *_: None)
        self.addCleanup(con.close)
        return con

    def fotografia(self, con) -> dict:
        """Tudo o que é NÚMERO DA COLEÇÃO — a mesma do `test_copias_proprias`,
        para não haver duas definições de «a Coleção não mexeu»."""
        cfg = self.config.load()
        sp = self.metrics.set_payload(con, "TST")
        fe = self.faltas_foil.payload_completo(con, cfg)
        am = self.a_mais.payload(con, cfg)
        return {
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
            "master": sp["progress"]["master"],
            "painel": sp["progress"]["painel"],
            "faltas": (fe["totals"], fe["totals_lists"],
                       [(s["set"], b["id"], b["cards"], b["copies"], b["cents"])
                        for s in fe["sets"] for b in s["blocks"]]),
            # A metade das FOILS e a quinta wantlist, que também não podem
            # mexer (ponto 5 da ordem).
            "faltas_foil": (fe["foil"]["totals"],
                            [(s["set"], s["foil"]["cards"], s["foil"]["copies"],
                              s["foil"]["cents"],
                              s["foil"]["wantlist"]["lines"],
                              s["foil"]["wantlist"]["copies"],
                              s["foil"]["wantlist"]["cents"])
                             for s in fe["sets"] if s.get("foil")]),
            "encomendas": self.pending.encomendas(con)["totals"],
            "a_mais": {s["set"]: [(x["printing_id"], x["extra"], x["have"])
                                  for x in s["excedente"]["items"]] for s in am["sets"]},
            "copies": sorted(tuple(r) for r in con.execute(
                "SELECT printing_id, qty, qty_foil FROM copies")),
        }

    def deck_id(self, con, slug) -> int:
        return next(r["deck_id"] for r in self.decks.deck_rows(con) if r["name"] == slug)

    def wl(self, con) -> dict:
        return self.principal.wantlist(con)


# ---------------------------------------------------------------------------


class TestAChave(Base):
    """1. `decks.principal`, e a relação com o `montados`."""

    def test_o_principal_e_um_so_e_le_se_pelo_nome_ou_pelo_slug(self):
        con = self.catalogo(principal="Azir")
        self.assertEqual(self.principal.estado(con)["slug"], "azir")
        self.cfg_decks({"principal": "azir"})
        self.assertEqual(self.principal.estado(con)["slug"], "azir")

    def test_sem_chave_nao_ha_deck_principal(self):
        con = self.catalogo(principal=None)
        e = self.principal.estado(con)
        self.assertIsNone(e["slug"])
        self.assertIsNone(e["nome"])
        # E sem principal não há wantlist nem despromoção a disparar.
        self.assertEqual(self.wl(con)["items"], [])

    def test_um_nome_que_nao_casa_avisa_e_nao_rebenta(self):
        con = self.catalogo(principal="Deck Que Nao Existe")
        e = self.principal.estado(con)
        self.assertIsNone(e["slug"])
        self.assertEqual(e["nao_encontrado"], "Deck Que Nao Existe")

    def test_a_chave_mal_escrita_rebenta(self):
        self.catalogo()
        self.cfg_decks({"principal": ["azir"]})
        with self.assertRaises(ValueError):
            self.decks.principal_nome()

    def test_o_principal_conta_sempre_como_montado(self):
        con = self.catalogo(principal="Azir")
        # A lista dos montados não o nomeia...
        self.cfg_decks({"principal": "Azir", "montados": ["Ornn"]})
        est = self.decks.montados_estado(con)
        self.assertIn("azir", est["montados"])
        self.assertTrue(est["principal_implicito"])
        # ... e ele consome a Coleção na mesma.
        self.assertIn("defy", self.decks.uso_por_carta(con))

    def test_escolher_escreve_tambem_nos_montados(self):
        con = self.catalogo(principal=None)
        self.cfg_decks({"montados": ["Ornn"]})
        self.principal.definir(con, "azir", source="t")
        bruto = json.loads((self.v.root / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(bruto["decks"]["principal"], "Azir")
        self.assertIn("Azir", bruto["decks"]["montados"])

    def test_desmontar_o_principal_despromove_o(self):
        con = self.catalogo(principal="Azir")
        res = self.principal.montar(con, "azir", False, source="t")
        self.assertEqual(res["despromovido"], "azir")
        self.assertIsNone(self.principal.estado(con)["slug"])
        # E desmontar é mesmo desmontar: sem isto, o «o principal conta como
        # montado» voltava a montá-lo e o clique não fazia nada.
        self.assertIn("azir", self.decks.montados_estado(con)["desmontados"])

    def test_desmontar_um_deck_que_nao_e_o_principal_nao_despromove(self):
        con = self.catalogo(principal="Azir")
        res = self.principal.montar(con, "ornn", False, source="t")
        self.assertIsNone(res["despromovido"])
        self.assertEqual(self.principal.estado(con)["slug"], "azir")

    def test_o_config_real_tem_a_chave_e_o_minimo(self):
        raw = json.loads((REPO / "riftvault_config.json").read_text(encoding="utf-8"))
        self.assertEqual(raw["decks"]["principal"], "LeBlanc Hook")
        self.assertEqual(raw["decks"]["venda_minimo_cents"], 50)
        # O principal tem de estar montado — as duas chaves a dizerem o mesmo.
        self.assertIn("LeBlanc Hook", raw["decks"]["montados"])

    def test_a_nota_do_config_diz_a_frase_a_data_e_as_tres_decisoes(self):
        raw = (REPO / "riftvault_config.json").read_text(encoding="utf-8")
        nota = json.loads(raw)["_decks_principal_nota"]
        venda_nota = json.loads(raw)["_decks_venda_minimo_nota"]
        self.assertIn("2026-09-27", nota)
        self.assertIn("Deck Principal: neste caso LeBlanc", nota)
        self.assertIn("montados", nota)
        self.assertIn("foil", nota.lower())
        for pedaco in ("0,50", "preço", "continuam cópias próprias",
                       "ENTRAR NA VENDA NÃO É VENDER"):
            self.assertIn(pedaco, venda_nota)

    def test_o_minimo_vem_do_config_e_um_valor_mau_rebenta(self):
        self.catalogo()
        self.assertEqual(self.decks.venda_minimo_cents(), 50)
        self.cfg_decks({"venda_minimo_cents": 250})
        self.assertEqual(self.decks.venda_minimo_cents(), 250)
        self.cfg_decks({"venda_minimo_cents": "meio euro"})
        with self.assertRaises(ValueError):
            self.decks.venda_minimo_cents()


class TestAWantlist(Base):
    """2. `precisa − próprias`, e o acabamento."""

    def test_todas_as_cartas_do_deck_sao_wantlist(self):
        con = self.catalogo()
        w = self.wl(con)
        # 3 Defy + 1 Brutalizer + 1 Emperor + 2 Salvage = 7 cópias de 4 cartas.
        # A Coleção tem 3 Defy, 1 Emperor e 2 Salvage a servir o deck, e isso
        # NÃO desconta: o que se quer é o deck ter as suas.
        self.assertEqual((w["totals"]["cards"], w["totals"]["copies"]), (4, 7))
        self.assertEqual({x["card_key"]: x["missing"] for x in w["items"]},
                         {"defy": 3, "brutalizer": 1, "emperor of the sands": 1,
                          "salvage": 2})

    def test_uma_carta_marcada_com_mais_sai_da_wantlist(self):
        con = self.catalogo()
        self.proprias.ajustar(con, "azir", "tst-002-100", 1, source="t")
        w = self.wl(con)
        self.assertNotIn("brutalizer", {x["card_key"] for x in w["items"]})
        self.assertEqual((w["totals"]["cards"], w["totals"]["copies"]), (3, 6))
        # Marcada em parte, a linha fica com o que falta.
        self.proprias.ajustar(con, "azir", "tst-001-100", 2, source="t")
        w = self.wl(con)
        self.assertEqual([x["missing"] for x in w["items"] if x["card_key"] == "defy"], [1])
        # Marcadas todas, a wantlist esvazia-se.
        self.proprias.ajustar(con, "azir", "tst-001-100", 1, source="t")
        self.proprias.ajustar(con, "azir", "tst-003-100", 1, source="t")
        self.proprias.ajustar(con, "azir", "tst-004-100", 2, source="t")
        self.assertEqual(self.wl(con)["items"], [])

    def test_comuns_e_incomuns_em_foil_rara_para_cima_a_normal(self):
        con = self.catalogo()
        por = {x["card_key"]: x for x in self.wl(con)["items"]}
        self.assertTrue(por["defy"]["foil"])          # comum
        self.assertTrue(por["brutalizer"]["foil"])    # incomum
        self.assertFalse(por["salvage"]["foil"])      # rara
        self.assertFalse(por["emperor of the sands"]["foil"])   # epic

    def test_o_acabamento_e_o_mesmo_criterio_do_contador_do_tile(self):
        con = self.catalogo()
        cfg = self.config.load()
        ambito = set(self.foil.ids_do_ambito(con, cfg))
        for x in self.wl(con)["items"]:
            self.assertEqual(x["foil"], x["printing_id"] in ambito, x["name"])
        # E anda com o config: sem as comuns no âmbito, o Defy passa a normal.
        self.cfg_decks({"principal": "Azir"}, extra={"foil": {"raridades": ["uncommon"]}})
        por = {x["card_key"]: x for x in self.wl(con)["items"]}
        self.assertFalse(por["defy"]["foil"])
        self.assertTrue(por["brutalizer"]["foil"])

    def test_a_linha_foil_conta_ao_preco_da_foil(self):
        con = self.catalogo()
        por = {x["card_key"]: x for x in self.wl(con)["items"]}
        # Defy: 11 c em normal, 502 em foil -> 3 x 502.
        self.assertEqual((por["defy"]["price"], por["defy"]["price_is_foil"]), (502, True))
        self.assertEqual(por["defy"]["total"], 3 * 502)
        # Salvage é rara: o preço da normal.
        self.assertEqual((por["salvage"]["price"], por["salvage"]["price_is_foil"]),
                         (300, False))

    def test_sem_oferta_foil_conta_ao_preco_da_normal_e_diz_se(self):
        con = self.catalogo()
        w = self.wl(con)
        por = {x["card_key"]: x for x in w["items"]}
        # Brutalizer quer-se em foil e o CardTrader não a tem em foil.
        self.assertTrue(por["brutalizer"]["foil"])
        self.assertFalse(por["brutalizer"]["price_is_foil"])
        self.assertEqual(por["brutalizer"]["price"], 20)
        self.assertEqual(w["totals"]["no_foil_price"], 1)

    def test_o_total_e_a_soma_das_linhas(self):
        con = self.catalogo()
        w = self.wl(con)
        self.assertEqual(w["totals"]["cents"], sum(x["total"] for x in w["items"]))
        self.assertEqual(w["totals"]["cents"], 3 * 502 + 20 + 1000 + 2 * 300)

    def test_as_runas_ficam_de_fora_e_dizem_se(self):
        con = self.catalogo()
        w = self.wl(con)
        self.assertNotIn("fury rune", {x["card_key"] for x in w["items"]})
        self.assertEqual((w["runas"]["copies"], w["runas"]["cards"]), (3, 1))

    def test_o_texto_sai_do_gerador_unico(self):
        from riftvault import cardmarket

        con = self.catalogo()
        w = self.wl(con)
        self.assertEqual(w["wantlist"]["text"],
                         cardmarket.gerar(w["items"])["text"])
        self.assertEqual(w["wantlist"]["copies"], w["totals"]["copies"])

    def test_o_deck_desmontado_tem_wantlist_na_mesma(self):
        """A wantlist é `precisa − próprias` e não olha à Coleção: um deck
        desmontado precisa das mesmas cartas."""
        con = self.catalogo()
        antes = self.wl(con)["totals"]
        self.cfg_decks({"principal": "Azir", "montados": []})
        self.assertEqual(self.wl(con)["totals"], antes)


class TestAsDuasIndicacoes(Base):
    """3. Na Coleção e na página do deck."""

    def test_o_tile_da_colecao_diz_que_esta_em_uso_no_deck_principal(self):
        con = self.catalogo()
        uso = self.decks.uso_por_carta(con)
        self.assertEqual([(u["deck"], u["principal"]) for u in uso["defy"]],
                         [("Azir", True), ("Ornn", False)])

    def test_sem_principal_nenhuma_entrada_e_principal(self):
        con = self.catalogo(principal=None)
        uso = self.decks.uso_por_carta(con)
        self.assertFalse(any(u["principal"] for lst in uso.values() for u in lst))

    def test_a_pagina_do_deck_diz_quantas_vem_da_colecao_e_quantas_faltam(self):
        con = self.catalogo()
        p = self.decks.deck_payload(con, self.deck_id(con, "azir"))["principal"]
        self.assertTrue(p["e_principal"])
        # 3 Defy + 1 Emperor + 2 Salvage vêm da Coleção; faltam 7 próprias.
        self.assertEqual(p["em_uso_da_colecao"], 6)
        self.assertEqual(p["cartas_da_colecao"], 3)
        self.assertEqual(p["falta_proprias"], 7)
        self.assertEqual(p["falta_cartas"], 4)

    def test_marcar_uma_propria_baixa_as_duas_metades(self):
        con = self.batida()
        p = self.decks.deck_payload(con, self.deck_id(con, "azir"))["principal"]
        # Com 3 Defy próprias, o deck deixa de pedir Defy à Coleção.
        self.assertEqual(p["em_uso_da_colecao"], 3)     # 1 Emperor + 2 Salvage
        self.assertEqual(p["falta_proprias"], 4)
        self.assertEqual(p["proprias"], 3)

    def batida(self):
        con = self.catalogo()
        self.proprias.ajustar(con, "azir", "tst-001-100", 3, source="t")
        return con

    def test_o_bloco_vai_em_todos_os_decks_com_e_principal_a_dizer_qual(self):
        con = self.catalogo()
        outro = self.decks.deck_payload(con, self.deck_id(con, "ornn"))["principal"]
        self.assertFalse(outro["e_principal"])
        self.assertEqual(outro["slug"], "azir")
        # E traz o que aconteceria à Venda, para ele ver antes de mudar.
        self.assertIn("venda", outro)


class TestAColecaoESoberana(Base):
    """4. Um empréstimo não mexe num número da Coleção."""

    def test_nada_muda_com_e_sem_deck_principal(self):
        con = self.catalogo(principal=None)
        antes = self.fotografia(con)
        self.cfg_decks({"principal": "Azir"})
        self.assertEqual(self.principal.estado(con)["slug"], "azir")
        self.assertEqual(self.fotografia(con), antes)

    def test_a_fotografia_nao_e_de_zeros(self):
        con = self.catalogo()
        f = self.fotografia(con)
        self.assertTrue(f["valor"] > 0 and f["totais"]["copies"] > 0)
        self.assertTrue(any(n for _, _, _, n, _ in f["niveis"]))
        self.assertTrue(f["grelha"])

    def test_ler_a_wantlist_do_principal_nao_escreve(self):
        con = self.catalogo()
        antes = self.fotografia(con)
        self.wl(con)
        self.principal.proprias_por_valor(con, "azir")
        self.decks.deck_payload(con, self.deck_id(con, "azir"))
        self.assertEqual(self.fotografia(con), antes)

    def test_trocar_de_deck_principal_nao_mexe_na_colecao(self):
        con = self.catalogo()
        antes = self.fotografia(con)
        self.principal.definir(con, "ornn", source="t")
        self.assertEqual(self.fotografia(con), antes)

    def test_a_despromocao_nao_mexe_na_colecao(self):
        con = self.catalogo()
        self.proprias.ajustar(con, "azir", "tst-001-100", 2, source="t")
        antes = self.fotografia(con)
        self.principal.definir(con, None, source="t")
        self.assertEqual(self.fotografia(con), antes)


class TestADespromocao(Base):
    """5. O que vai para a Venda, e o que fica."""

    def com_proprias(self):
        """Duas próprias: um Defy (foil, 5,02 €) e um Brutalizer (0,20 €)."""
        con = self.catalogo()
        self.proprias.ajustar(con, "azir", "tst-001-100", 1, source="t")
        self.proprias.ajustar(con, "azir", "tst-002-100", 1, source="t")
        return con

    def test_so_as_de_meio_euro_para_cima_vao_a_venda(self):
        con = self.com_proprias()
        res = self.principal.definir(con, "ornn", source="t")
        mov = res["movimento"]
        self.assertEqual(mov["para_a_venda"], {"printings": 1, "copies": 1, "cents": 502})
        self.assertEqual(self.venda.linhas(con), {"tst-001-100": 1})

    def test_as_de_menos_de_meio_euro_continuam_proprias(self):
        con = self.com_proprias()
        self.principal.definir(con, "ornn", source="t")
        # Não foram para a Venda...
        self.assertNotIn("tst-002-100", self.venda.linhas(con))
        # ... e continuam a ser cópias próprias do deck, fora da Coleção.
        self.assertEqual(self.locais.proprias_de(con, "azir"),
                         {"tst-001-100": 1, "tst-002-100": 1})

    def test_a_pagina_diz_quantas_ficam_e_quanto_valem(self):
        con = self.com_proprias()
        pv = self.principal.proprias_por_valor(con, "azir")
        self.assertEqual(pv["totais"]["acima"], {"printings": 1, "copies": 1, "cents": 502})
        self.assertEqual(pv["totais"]["abaixo"], {"printings": 1, "copies": 1, "cents": 20})
        self.assertEqual(pv["minimo_cents"], 50)

    def test_nada_sai_do_proprio_do_deck(self):
        """Entrar na Venda NÃO é vender (decisão (c))."""
        con = self.com_proprias()
        antes = self.locais.proprias_de(con, "azir")
        copias = sorted(tuple(r) for r in con.execute(
            "SELECT printing_id, qty, qty_foil FROM copies"))
        self.principal.definir(con, None, source="t")
        self.assertEqual(self.locais.proprias_de(con, "azir"), antes)
        self.assertEqual(sorted(tuple(r) for r in con.execute(
            "SELECT printing_id, qty, qty_foil FROM copies")), copias)

    def test_o_preco_do_criterio_e_o_que_a_venda_mostra(self):
        con = self.com_proprias()
        self.principal.definir(con, None, source="t")
        linha = next(x for x in self.venda.itens(con) if x["printing_id"] == "tst-001-100")
        self.assertEqual(linha["preco_criterio"], 502)
        self.assertTrue(linha["criterio_foil"])
        self.assertEqual(linha["criterio_fonte"], "cardtrader-foil")

    def test_o_trend_dele_ganha_ao_cardtrader_no_criterio(self):
        con = self.catalogo()
        # Uma incomum a 0,20 € no CardTrader ficaria de fora; com o Trend dele
        # a 1,50 € vai — o critério é o preço que a Venda mostra.
        self.proprias.ajustar(con, "azir", "tst-002-100", 1, source="t")
        self.venda.guardar_trend(con, "tst-002-100", 150, source="t")
        pv = self.principal.proprias_por_valor(con, "azir")
        self.assertEqual([(x["printing_id"], x["fonte"]) for x in pv["acima"]],
                         [("tst-002-100", "trend")])

    def test_uma_copia_sem_preco_nenhum_fica(self):
        con = self.catalogo()
        con.execute("DELETE FROM catalog.price_latest WHERE printing_id = 'tst-001-100'")
        self.proprias.ajustar(con, "azir", "tst-001-100", 1, source="t")
        pv = self.principal.proprias_por_valor(con, "azir")
        self.assertEqual(pv["acima"], [])
        self.assertEqual([x["printing_id"] for x in pv["abaixo"]], ["tst-001-100"])

    def test_o_minimo_do_config_manda(self):
        con = self.com_proprias()
        self.cfg_decks({"principal": "Azir", "venda_minimo_cents": 100000})
        pv = self.principal.proprias_por_valor(con, "azir")
        self.assertEqual(pv["acima"], [])
        self.assertEqual(pv["totais"]["abaixo"]["copies"], 2)

    def test_desfazer_o_deck_manda_o_mesmo_para_a_venda(self):
        """*"Se eu 'desfazer' o deck ou deixar de ser o principal"* — os dois."""
        con = self.com_proprias()
        res = self.principal.montar(con, "azir", False, source="t")
        self.assertEqual(res["movimento"]["para_a_venda"]["copies"], 1)
        self.assertEqual(self.venda.linhas(con), {"tst-001-100": 1})

    def test_a_linha_diz_de_onde_veio_e_tira_se_de_uma_vez(self):
        con = self.com_proprias()
        # Uma linha marcada À MÃO antes, para provar que o «tirar as do deck»
        # não a leva.
        self.venda.juntar(con, "tst-004-100", 2, source="t")
        self.principal.definir(con, None, source="t")
        por = {x["printing_id"]: x for x in self.venda.itens(con)}
        self.assertEqual(por["tst-001-100"]["origem"], "deck:azir")
        self.assertEqual(por["tst-001-100"]["origem_deck"], "Azir")
        self.assertIsNone(por["tst-004-100"]["origem"])
        self.assertEqual(self.venda.limpar(con, origem="deck:azir"), 1)
        self.assertEqual(self.venda.linhas(con), {"tst-004-100": 2})

    def test_a_conta_da_venda_agrupa_as_origens(self):
        con = self.com_proprias()
        self.principal.definir(con, None, source="t")
        t = self.venda.conta(self.venda.itens(con))
        self.assertEqual(t["origens"], [{"origem": "deck:azir", "deck": "Azir",
                                         "slug": "azir", "lines": 1, "copies": 1,
                                         "cents": 502}])

    def test_uma_linha_que_ele_ja_tinha_marcado_continua_a_ser_dele(self):
        con = self.com_proprias()
        self.venda.juntar(con, "tst-001-100", 1, source="t")   # à mão, antes
        self.principal.definir(con, None, source="t")
        por = {x["printing_id"]: x for x in self.venda.itens(con)}
        self.assertEqual(por["tst-001-100"]["qty"], 2)
        # A origem não se reescreve: o «tirar as do deck» não pode levar a dele.
        self.assertIsNone(por["tst-001-100"]["origem"])

    def test_escolher_o_mesmo_deck_outra_vez_nao_faz_nada(self):
        con = self.com_proprias()
        self.principal.definir(con, "azir", source="t")
        self.assertEqual(self.venda.linhas(con), {})

    def test_as_emprestadas_da_colecao_nao_vao_a_lado_nenhum(self):
        """O deck usava 3 Defy da Coleção e não tinha nenhuma própria delas:
        ao despromover, a Venda fica vazia e a Coleção intacta."""
        con = self.catalogo()
        antes = self.fotografia(con)
        self.principal.definir(con, None, source="t")
        self.assertEqual(self.venda.linhas(con), {})
        self.assertEqual(self.fotografia(con), antes)

    def test_a_coluna_origem_existe_no_schema(self):
        con = self.catalogo()
        cols = {r[1] for r in con.execute("PRAGMA table_info(sale_lines)")}
        self.assertIn("origem", cols)

    def test_a_migracao_da_origem_corre_numa_base_antiga(self):
        from riftvault import db

        con = self.catalogo()
        con.execute("DROP TABLE sale_lines")
        con.execute("CREATE TABLE sale_lines (printing_id TEXT PRIMARY KEY, "
                    "qty INTEGER NOT NULL CHECK (qty > 0), added_at TEXT NOT NULL)")
        con.execute("INSERT INTO sale_lines VALUES ('tst-001-100', 2, 'x')")
        db._migrar_sale_lines_origem(con)
        cols = {r[1] for r in con.execute("PRAGMA table_info(sale_lines)")}
        self.assertIn("origem", cols)
        # A linha que já lá estava fica a NULL — foi ele que a marcou.
        self.assertEqual(self.venda.origens(con), {"tst-001-100": None})
        db._migrar_sale_lines_origem(con)   # idempotente


class TestAsPortas(Base):
    """6. As rotas, o `build`, a CLI, o `app.js`."""

    def test_as_rotas(self):
        from riftvault import server

        con = self.catalogo()
        self.proprias.ajustar(con, "azir", "tst-001-100", 1, source="t")
        cli = server.app.test_client()
        r = cli.get("/api/decks.json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["principal"]["slug"], "azir")
        self.assertTrue(next(d for d in r.get_json()["decks"]
                             if d["slug"] == "azir")["principal"])

        r = cli.post("/api/decks/principal", json={"slug": "ornn"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["despromovido"], "azir")
        self.assertEqual(r.get_json()["movimento"]["para_a_venda"]["copies"], 1)

        r = cli.post("/api/decks/principal", json={"slug": "nao-existe"})
        self.assertEqual(r.status_code, 404)

        r = cli.post("/api/venda/limpar", json={"origem": "deck:azir"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["limpas"], 1)

        r = cli.post("/api/decks/principal", json={"slug": None})
        self.assertEqual(r.status_code, 200)
        self.assertIsNone(r.get_json()["estado"]["slug"])

    def test_o_build_leva_o_principal_e_a_wantlist(self):
        from riftvault import build

        con = self.catalogo()
        con.close()
        out = self.v.root / "site"
        build.build(out, log=lambda *_: None)
        idx = json.loads((out / "api" / "decks.json").read_text(encoding="utf-8"))
        self.assertEqual(idx["principal"]["slug"], "azir")
        did = next(d["id"] for d in idx["decks"] if d["slug"] == "azir")
        p = json.loads((out / "api" / "deck" / f"{did}.json").read_text(encoding="utf-8"))
        self.assertTrue(p["principal"]["e_principal"])
        self.assertEqual(p["principal"]["wantlist"]["totals"]["copies"], 7)

    def test_a_cli(self):
        import contextlib
        import io

        from riftvault import cli

        con = self.catalogo()
        self.proprias.ajustar(con, "azir", "tst-002-100", 1, source="t")
        con.close()
        saida = io.StringIO()
        with contextlib.redirect_stdout(saida), contextlib.redirect_stderr(saida):
            self.assertEqual(cli.main(["principal"]), 0)
        txt = saida.getvalue()
        self.assertIn("DECK PRINCIPAL: Azir", txt)
        self.assertIn("foil", txt)
        self.assertIn("auto-suficiente", txt)
        # E o `--definir` despromove, dizendo as duas metades.
        saida = io.StringIO()
        with contextlib.redirect_stdout(saida), contextlib.redirect_stderr(saida):
            self.assertEqual(cli.main(["principal", "--definir", "ornn"]), 0)
        txt = saida.getvalue()
        self.assertIn("deck principal: Ornn", txt)
        self.assertIn("Ficam 1", txt)
        self.assertIn("NÃO é vender", txt)

    def test_o_app_js_e_o_css(self):
        js = (REPO / "riftvault" / "web" / "app.js").read_text(encoding="utf-8")
        css = (REPO / "riftvault" / "web" / "style.css").read_text(encoding="utf-8")
        # As duas indicações.
        self.assertIn("em uso no deck", js)
        self.assertIn("cartas em uso", js)
        # A wantlist e o gerador único.
        self.assertIn("principalWantlist", js)
        self.assertIn("cmLigar('pri'", js)
        # O botão, e a palavra «principal» já não é a prioridade 1.
        self.assertIn("tornar-principal", js)
        self.assertIn("Passar a prioridade 1", js)
        self.assertNotIn(">principal</span>", js)
        # A Venda diz de onde vieram e tira-as de uma vez.
        self.assertIn("vdOrigens", js)
        self.assertIn("vdLimparOrigem", js)
        self.assertIn("não é vender", js)
        # A tabela vira cartões a 559 px — nada de scroll lateral.
        self.assertIn(".pri-tabela", css)
        self.assertNotIn("tabela-rolo", js)


if __name__ == "__main__":
    unittest.main()

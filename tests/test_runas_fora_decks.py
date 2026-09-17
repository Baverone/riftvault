"""As runas saem da contagem dos decks (2026-09-17, à noite).

Palavras do André:
    *"esquece as runas, nao facas contagem de runas nos decks, indica me so
    quantas sao e eu organizo isso sozinho a mao"*
e, logo a seguir:
    *"no a mais nunca aparece Runas"*

A regra (`decks.contar_runas: false`, `a_mais.sem_runas: true`):
  1. O Rune Pool continua a LER-SE e a MOSTRAR-SE com as quantidades da lista
     («9 Calm Rune, 3 Order Rune»), e a legalidade continua a dizer «runas
     12/12» — ele quer ver quantas são.
  2. DEIXA DE HAVER CONTABILIDADE: uma runa não entra no `need` de deck
     nenhum — sem tenho/faltam, sem alocação da Coleção, sem disputa, sem
     falta a comprar, sem a caminho, sem euros, sem proposta de marcação, sem
     Pimp; a grelha da Coleção deixa de dizer «Azir 9» numa runa.
  3. O «tenho X de N» do deck conta só o que se conta (7 de 7 num deck de 19)
     e diz ao lado quantas runas há. O denominador desce de propósito: deixar
     o 19 dizia que faltavam 12.
  4. No «A mais» as runas não aparecem em NENHUM dos dois blocos — nem no
     excedente (esteja a runa na sequência ou escondida), nem nas libertadas
     — e o `scope.runas` diz quantas ficaram de fora.
  5. A Coleção NÃO mexe: a runa base continua a 3 no master set, a contar para
     a percentagem e para a wantlist. As runas em Alt Art continuam retiradas.
  6. `contar_runas: true` volta a contar como antes; `sem_runas: false` volta
     a mostrá-las no «A mais».

Tudo contra cópias descartáveis (`tests.fixture.Vault`) e um config temporário
(`RIFTVAULT_CONFIG`): nunca o `data/` nem o `riftvault_config.json` reais.
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

DEFY, BRUT, EMP = "tst-001-100", "tst-002-100", "tst-003-100"
CALM, CALM_A, ORDER, PROMO = "tst-007-100", "tst-007a-100", "tst-008-100", "tst-r01"

AZIR = ("Legend:\n1 Emperor of the Sands\n\nMainDeck:\n3 Defy\n3 Brutalizer\n\n"
        "Rune Pool:\n9 Calm Rune\n3 Order Rune\n")
AZIR_SEM_ORDER = ("Legend:\n1 Emperor of the Sands\n\nMainDeck:\n3 Defy\n3 Brutalizer\n\n"
                  "Rune Pool:\n9 Calm Rune\n")
ORNN = "Legend:\n1 Forge Master\n\nMainDeck:\n3 Defy\n\nRune Pool:\n12 Calm Rune\n"

PRECOS = {DEFY: 100, BRUT: 50, EMP: 1000, CALM: 11, CALM_A: 500, ORDER: 11, PROMO: 12,
          "tst-005-100": 1000}


class Base(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.close)
        from riftvault import (a_mais, a_subir, collection, config, decks, faltas,
                               locais, metrics, pending, uso_decks)
        for m in (metrics, locais, pending, decks, faltas, a_subir, uso_decks, a_mais):
            importlib.reload(m)
        self.a_mais, self.a_subir, self.collection = a_mais, a_subir, collection
        self.config, self.decks, self.locais = config, decks, locais
        self.metrics, self.uso, self.faltas, self.pending = metrics, uso_decks, faltas, pending

    def com_config(self, extra: dict):
        caminho = self.v.root / "config.json"
        caminho.write_text(json.dumps(extra), encoding="utf-8")
        os.environ["RIFTVAULT_CONFIG"] = str(caminho)
        importlib.reload(self.config)
        self.config.load.cache_clear()

        def repor():
            os.environ["RIFTVAULT_CONFIG"] = str(
                Path(tempfile.gettempdir()) / "riftvault-nao-existe.json")
            importlib.reload(self.config)
            self.config.load.cache_clear()

        self.addCleanup(repor)

    def montar(self, extra: dict | None = None, decks: dict | None = None,
               copias: dict | None = None):
        """Uma edição TST (100 nominais): Defy, Brutalizer, dois Legends, a
        Calm Rune (base + alt art retirada), a Order Rune, e uma runa promo
        sem numeração (escondida, como as `VEN-R`)."""
        self.com_config({
            "sets": {"TST": {"name": "Teste", "order": 1}},
            **(extra or {}),
        })
        con = self.v.connect()
        self.addCleanup(con.close)
        add = self.v.add_printing
        add(con, DEFY, "TST", 1, "Defy", size=100)
        add(con, BRUT, "TST", 2, "Brutalizer", size=100)
        add(con, EMP, "TST", 3, "Emperor of the Sands", card_type="Legend", size=100)
        add(con, "tst-005-100", "TST", 5, "Forge Master", card_type="Legend", size=100)
        add(con, CALM, "TST", 7, "Calm Rune", card_type="Rune", size=100)
        add(con, CALM_A, "TST", 7, "Calm Rune", card_type="Rune", variant="a",
            kind="alt_art", rarity="showcase", base_rarity="common", size=100)
        add(con, ORDER, "TST", 8, "Order Rune", card_type="Rune", size=100)
        add(con, PROMO, "TST", 1, "Chaos Rune", card_type="Rune", variant="r01",
            kind="rune_promo", lane="r", codigo="TST-R01")
        for pid, c in PRECOS.items():
            con.execute("INSERT INTO catalog.price_latest (printing_id, price_cents, "
                        "from_foil) VALUES (?,?,0)", (pid, c))
        self.v.rebuild(con)
        con.commit()
        for pid, n in (copias or {}).items():
            self.collection.adjust(con, pid, n, source="test")
        for slug, texto in (decks if decks is not None else {"azir": AZIR}).items():
            self.v.write_deck(slug, texto)
        self.decks.import_all(con, log=lambda *_: None)
        return con

    def ter(self, con, pid, n):
        self.collection.adjust(con, pid, n, source="test")

    def idx(self, con) -> dict:
        return {d["slug"]: d for d in self.decks.decks_index(con)}

    def aloc(self, con, slug="azir") -> dict:
        return self.decks.allocate(con)[self.idx(con)[slug]["id"]]

    def payload(self, con, slug="azir") -> dict:
        return self.decks.deck_payload(con, self.idx(con)[slug]["id"])

    def seccao(self, p, role) -> dict:
        return next(s for s in p["sections"] if s["role"] == role)


class TestORunePoolLeSeEMostraSe(Base):
    """1: quantas são, e mais nada."""

    def test_a_lista_diz_quantas_runas_pede(self):
        con = self.montar()
        p = self.payload(con)
        s = self.seccao(p, "runes")
        self.assertEqual([(c["name"], c["wanted"], c["contado"]) for c in s["cards"]],
                         [("Calm Rune", 9, False), ("Order Rune", 3, False)])
        # A secção soma só o que se conta (nada) e diz quantas ficam de fora.
        self.assertEqual((s["wanted"], s["have"], s["nao_contadas"]), (0, 0, 12))
        self.assertEqual(p["runas"], {"copies": 12, "cards": 2, "contadas": False})
        # As outras secções contam como sempre.
        m = self.seccao(p, "main")
        self.assertEqual((m["wanted"], m["nao_contadas"]), (6, 0))
        self.assertTrue(all(c["contado"] for c in m["cards"]))

    def test_a_linha_da_runa_nao_tem_tenho_falta_preco_nem_versoes(self):
        con = self.montar(copias={CALM: 4, ORDER: 1})
        c = next(x for x in self.seccao(self.payload(con), "runes")["cards"]
                 if x["card_key"] == "calm rune")
        self.assertEqual((c["have"], c["missing"], c["ordered"], c["na_colecao"]), (0, 0, 0, 0))
        self.assertEqual((c["price"], c["versoes"], c["outras"], c["printings"]), (None, [], 0, []))
        self.assertEqual((c["especial"], c["shared"], c["order_code"]), (None, None, None))
        # Mas continua a ser a carta, com a imagem e o código.
        self.assertEqual((c["name"], c["type"], c["code"]), ("Calm Rune", "Rune", "TST-007/100"))

    def test_a_legalidade_continua_a_contar_as_runas(self):
        con = self.montar()
        L = self.payload(con)["legality"]
        self.assertEqual((L["runes"]["n"], L["runes"]["alvo"], L["runes"]["ok"]), (12, 12, True))
        self.v.write_deck("azir", AZIR_SEM_ORDER)
        self.decks.import_all(con, log=lambda *_: None)
        L = self.payload(con)["legality"]
        self.assertEqual((L["runes"]["n"], L["runes"]["ok"]), (9, False))


class TestSemContabilidade(Base):
    """2: nem tenho, nem falta, nem alocação, nem disputa, nem compra."""

    def test_a_runa_nao_entra_no_need_nem_falta_com_zero_copias(self):
        con = self.montar()
        a = self.aloc(con)
        for chave in ("need", "alloc", "missing", "shared", "a_caminho", "versoes_em"):
            self.assertNotIn("calm rune", a["grupo"][chave], chave)
            self.assertNotIn("order rune", a["grupo"][chave], chave)
        self.assertNotIn("calm rune", a["missing"])
        # O resto falta como sempre: 3 Defy, 3 Brutalizer, a Legend.
        self.assertEqual(a["missing"], {"defy": 3, "brutalizer": 3, "emperor of the sands": 1})

    def test_com_copias_na_colecao_nao_se_aloca_nem_se_diz_onde(self):
        con = self.montar(copias={CALM: 9, ORDER: 3})
        a = self.aloc(con)
        self.assertNotIn("calm rune", a["alloc"])
        self.assertNotIn("calm rune", a["na_colecao"])
        self.assertEqual(a["grupo"]["impressoes"]["na_colecao"], {})
        # A grelha da Coleção não diz «Azir 9» na runa.
        self.assertNotIn("calm rune", self.decks.uso_por_carta(con))
        p = self.metrics.set_payload(con, "TST")
        runa = next(g for g in p["groups"] if g["name"] == "Calm Rune")
        self.assertFalse(runa.get("decks"))
        self.assertNotIn("calm rune", self.decks.owned_by_card(con))

    def test_dois_decks_nao_disputam_runas(self):
        con = self.montar(decks={"azir": AZIR, "ornn": ORNN}, copias={CALM: 9})
        azir, ornn = self.aloc(con, "azir"), self.aloc(con, "ornn")
        self.assertNotIn("calm rune", ornn["missing"])
        self.assertNotIn("calm rune", ornn["shared"])
        self.assertNotIn("calm rune", azir["alloc"])
        # As faltas dos decks e as compras não têm runas.
        # O Azir compra 7 (Legend, 3 Defy, 3 Brutalizer), o Ornn 4 (Legend, 3 Defy).
        tot = self.decks.resumo_das_faltas(con)
        self.assertEqual((tot["copies"], tot["cards"]), (7 + 4, 4))
        self.assertNotIn("calm rune", [x["card_key"] for x in self.decks.shopping_list(con)])
        for d in self.decks.missing_by_set(con, self.idx(con)["ornn"]["id"]):
            self.assertNotIn("calm rune", [x["card_key"] for x in d["items"]])

    def test_uma_encomenda_de_runa_nao_e_a_caminho_de_deck_nenhum(self):
        con = self.montar()
        self.pending.add(con, CALM, 9, source="test")
        a = self.aloc(con)
        self.assertNotIn("calm rune", a["a_caminho"])
        self.assertEqual(self.idx(con)["azir"]["ordered"], 0)
        # A encomenda existe na mesma — é da Coleção, não do deck.
        self.assertEqual(self.pending.open_qty(con).get(CALM), 9)

    def test_as_abas_dos_decks_nao_tem_runas(self):
        con = self.montar(decks={"azir": AZIR, "ornn": ORNN})
        comp = self.faltas.compras(con)
        texto = json.dumps(comp, ensure_ascii=False)
        self.assertNotIn("Calm Rune", texto)
        self.assertNotIn("Order Rune", texto)
        self.assertEqual(comp["totals"]["copies"], 7 + 4)
        self.assertNotIn("calm rune", self.faltas._wanted(con))
        # Com o `faltas_ignorar_tipos` vazio dá o mesmo: já nem chegam a ser pedidas.
        self.com_config({"sets": {"TST": {"name": "Teste", "order": 1}},
                         "faltas_ignorar_tipos": []})
        self.assertNotIn("calm rune", self.faltas._wanted(con))
        self.assertNotIn("Calm Rune", json.dumps(self.faltas.compras(con), ensure_ascii=False))

    def test_a_proposta_de_marcacao_nao_propoe_runas(self):
        con = self.montar(copias={CALM: 9, DEFY: 3})
        prop = self.locais.propor_deck(con, "azir")
        ids = [x["printing_id"] for x in prop["items"]]
        self.assertIn(DEFY, ids)
        self.assertNotIn(CALM, ids)

    def test_uma_runa_sleevada_no_deck_nao_e_a_mais_nesse_deck(self):
        con = self.montar(copias={CALM: 9})
        self.locais.marcar(con, [{"printing_id": CALM, "qty": 9}],
                           self.locais.deck_local("azir"), source="test")
        a = self.aloc(con)
        self.assertEqual(a["extra"], {})
        self.assertEqual(self.idx(con)["azir"]["extra"], 0)

    def test_o_pimp_nao_oferece_versoes_de_runa(self):
        # Sem a retirada, a alt art da Calm Rune era versão a pimpar; sem
        # contagem de runas nos decks, a runa nem é pedida.
        con = self.montar(extra={"runas_especiais": {"tipos": ["Rune"], "excepto": ["base"],
                                                     "retiradas": []}})
        pm = json.dumps(self.faltas.pimp(con), ensure_ascii=False)
        self.assertNotIn(CALM_A, pm)
        self.assertNotIn("Calm Rune", pm)


class TestOTenhoXDeN(Base):
    """3: o denominador desce, as runas dizem-se ao lado."""

    def test_o_wanted_do_deck_e_sem_as_runas_e_as_runas_vao_ao_lado(self):
        con = self.montar(copias={DEFY: 3, BRUT: 3, EMP: 1, CALM: 9, ORDER: 3})
        d = self.idx(con)["azir"]
        self.assertEqual((d["have"], d["wanted"], d["missing"]), (7, 7, 0))
        self.assertEqual(d["runas"], {"copies": 12, "cards": 2, "contadas": False})

    def test_sem_runas_na_lista_nao_ha_nada_a_dizer(self):
        con = self.montar(decks={"azir": "Legend:\n1 Emperor of the Sands\n\nMainDeck:\n3 Defy\n"})
        d = self.idx(con)["azir"]
        self.assertEqual((d["wanted"], d["runas"]["copies"]), (4, 0))
        p = self.payload(con)
        self.assertEqual(p["runas"]["copies"], 0)
        self.assertTrue(all(s["nao_contadas"] == 0 for s in p["sections"]))


class TestAMais(Base):
    """4: nunca aparecem, e diz-se quantas ficaram de fora."""

    def test_a_runa_da_sequencia_acima_do_alvo_nao_aparece_e_conta_se_no_scope(self):
        con = self.montar(copias={CALM: 8, ORDER: 3})
        exc = self.a_mais.excedente(con)
        self.assertEqual([x["printing_id"] for x in exc], [])
        p = self.a_mais.payload(con)
        self.assertEqual(p["totals"]["excedente"], {"cards": 0, "copies": 0})
        # 8 − max(0 usadas, alvo 3) = 5 a mais numa impressão, fora por ser runa.
        self.assertTrue(p["scope"]["sem_runas"])
        self.assertEqual(p["scope"]["runas"]["excedente"], {"cards": 1, "copies": 5})
        # Com `todas` vê-se, marcada.
        (x,) = self.a_mais.excedente(con, todas=True)
        self.assertEqual((x["printing_id"], x["extra"], x["runa"]), (CALM, 5, True))

    def test_a_runa_escondida_tambem_nao_aparece(self):
        con = self.montar(copias={PROMO: 2})
        self.assertEqual(self.a_mais.excedente(con), [])
        p = self.a_mais.payload(con)
        self.assertEqual(p["scope"]["hidden_copies"], 0)
        self.assertEqual(p["scope"]["runas"]["excedente"], {"cards": 1, "copies": 2})

    def test_o_que_nao_e_runa_continua_a_aparecer(self):
        con = self.montar(copias={BRUT: 5, CALM: 8})
        (x,) = self.a_mais.excedente(con)
        self.assertEqual((x["printing_id"], x["extra"], x["runa"]), (BRUT, 2, False))

    def test_uma_runa_libertada_dos_decks_nao_aparece_e_conta_se(self):
        con = self.montar(copias={ORDER: 3})
        self.v.write_deck("azir", AZIR_SEM_ORDER)
        self.decks.import_all(con, log=lambda *_: None)
        # O registo guarda a descida (é o rasto das listas), a página não a mostra.
        self.assertEqual([x["card_key"] for x in self.uso.libertadas(con)], ["order rune"])
        self.assertEqual(self.a_mais.libertadas(con), [])
        p = self.a_mais.payload(con)
        self.assertEqual(p["totals"]["libertadas"], {"cards": 0, "copies": 0})
        self.assertEqual(p["scope"]["runas"]["libertadas"], {"cards": 1, "copies": 3})
        (x,) = self.a_mais.libertadas(con, todas=True)
        self.assertEqual((x["card_key"], x["qty"], x["runa"]), ("order rune", 3, True))

    def test_uma_carta_libertada_que_nao_e_runa_continua_a_aparecer(self):
        con = self.montar()
        self.v.write_deck("azir", "Legend:\n1 Emperor of the Sands\n\nMainDeck:\n3 Defy\n\n"
                                  "Rune Pool:\n9 Calm Rune\n3 Order Rune\n")
        self.decks.import_all(con, log=lambda *_: None)
        (x,) = self.a_mais.libertadas(con)
        self.assertEqual((x["card_key"], x["qty"], x["runa"]), ("brutalizer", 3, False))

    def test_sem_runas_false_volta_a_mostra_las(self):
        con = self.montar(extra={"a_mais": {"sem_edicoes": [], "sem_runas": False}},
                          copias={CALM: 8})
        (x,) = self.a_mais.excedente(con)
        # As runas não se contam nos decks, por isso as 9 do Azir não prendem
        # nenhuma: 8 − max(0, 3) = 5 a mais.
        self.assertEqual((x["printing_id"], x["extra"]), (CALM, 5))
        p = self.a_mais.payload(con)
        self.assertFalse(p["scope"]["sem_runas"])
        self.assertEqual(p["scope"]["runas"]["excedente"], {"cards": 0, "copies": 0})
        self.assertEqual(p["totals"]["excedente"], {"cards": 1, "copies": 5})

    def test_os_dois_efeitos_separados__soltar_as_runas_e_tira_las(self):
        """Os dois efeitos da noite, em sentidos contrários: com as runas a
        contar, o Azir prendia as 8 (9 pedidas) e nada sobrava; sem contar,
        sobram 5 — e sem as mostrar, sobra 0. Cada passo à vez."""
        copias = {CALM: 8}
        con = self.montar(extra={"decks": {"contar_runas": True},
                                 "a_mais": {"sem_edicoes": [], "sem_runas": False}},
                          copias=copias)
        self.assertEqual(self.a_mais.excedente(con), [])
        con.close()
        self.v = Vault()
        self.addCleanup(self.v.close)
        con = self.montar(extra={"decks": {"contar_runas": False},
                                 "a_mais": {"sem_edicoes": [], "sem_runas": False}},
                          copias=copias)
        self.assertEqual([(x["printing_id"], x["extra"]) for x in self.a_mais.excedente(con)],
                         [(CALM, 5)])
        con.close()
        self.v = Vault()
        self.addCleanup(self.v.close)
        con = self.montar(copias=copias)
        self.assertEqual(self.a_mais.excedente(con), [])
        self.assertEqual(self.a_mais.payload(con)["scope"]["runas"]["excedente"],
                         {"cards": 1, "copies": 5})


class TestAColecaoNaoMexe(Base):
    """5: master set, denominador, wantlist, valor — iguais com e sem."""

    def invariantes(self, con) -> tuple:
        from riftvault import prices
        importlib.reload(prices)
        niv = self.metrics.niveis_payload(con)["levels"]
        w = self.a_subir.wantlist(con)
        tiles = {pr["id"]: pr for g in self.metrics.set_payload(con, "TST")["groups"]
                 for pr in g["printings"]}
        return (tuple((lv["done"], lv["total"], lv["missing"]) for lv in niv),
                (w["lines"], w["copies"], w["cents"]),
                {x["printing_id"]: x["missing"] for x in w["items"]},
                (tiles[CALM]["block"], tiles[CALM]["target"], tiles[CALM]["qty"]),
                prices.collection_value(con)["cents"])

    def test_iguais_com_as_runas_a_contar_e_sem(self):
        copias = {CALM: 1, ORDER: 3, DEFY: 2, CALM_A: 6}
        con = self.montar(copias=copias)
        sem = self.invariantes(con)
        con.close()
        self.v = Vault()
        self.addCleanup(self.v.close)
        con = self.montar(extra={"decks": {"contar_runas": True}}, copias=copias)
        com = self.invariantes(con)
        self.assertEqual(sem, com)
        # E dizem o que têm de dizer: a runa base a 3 na sequência, 1 tida, 2
        # na wantlist; a alt art retirada em lado nenhum.
        self.assertEqual(sem[3], ("master", 3, 1))
        self.assertEqual(sem[2].get(CALM), 2)
        self.assertNotIn(CALM_A, sem[2])

    def test_a_percentagem_e_a_wantlist_nao_sabem_dos_decks(self):
        con = self.montar(copias={CALM: 1})
        antes = self.invariantes(con)
        self.v.write_deck("azir", "Legend:\n1 Emperor of the Sands\n\nMainDeck:\n3 Defy\n")
        self.decks.import_all(con, log=lambda *_: None)
        self.assertEqual(antes, self.invariantes(con))


class TestConfig(Base):
    """6: os botões, os defaults, e o que o site e a CLI escrevem."""

    def test_contar_runas_true_volta_a_contar(self):
        con = self.montar(extra={"decks": {"contar_runas": True}}, copias={CALM: 4})
        a = self.aloc(con)
        self.assertEqual((a["alloc"]["calm rune"], a["missing"]["calm rune"]), (4, 5))
        self.assertEqual(a["missing"]["order rune"], 3)
        d = self.idx(con)["azir"]
        self.assertEqual((d["wanted"], d["runas"]), (19, {"copies": 0, "cards": 0, "contadas": True}))
        p = self.payload(con)
        s = self.seccao(p, "runes")
        self.assertEqual((s["wanted"], s["have"], s["nao_contadas"]), (12, 4, 0))
        self.assertTrue(all(c["contado"] for c in s["cards"]))
        self.assertEqual(p["runas"]["contadas"], True)

    def test_sem_runa_no_config_nao_ha_nada_a_tirar(self):
        # `runas_especiais.tipos: []` — não há «runa»; conta-se tudo.
        con = self.montar(extra={"runas_especiais": {"tipos": [], "excepto": ["base"],
                                                     "retiradas": []}})
        self.assertEqual(self.decks.cartas_nao_contadas(con), frozenset())
        self.assertEqual(self.aloc(con)["missing"]["calm rune"], 9)

    def test_os_defaults_e_o_config_real(self):
        self.assertIs(self.config.DEFAULTS["decks"]["contar_runas"], False)
        self.assertIs(self.config.DEFAULTS["a_mais"]["sem_runas"], True)
        real = json.loads((REPO / "riftvault_config.json").read_text(encoding="utf-8"))
        self.assertIs(real["decks"]["contar_runas"], False)
        self.assertIs(real["a_mais"]["sem_runas"], True)
        # A Coleção não mexeu: as runas base continuam a 3.
        self.assertEqual(real["master_targets_by_type"]["Rune"], 3)
        self.assertEqual(real["runas_especiais"]["retiradas"], ["a"])

    def test_o_site_e_a_cli_dizem_quantas_sao_e_nao_contam(self):
        app = (REPO / "riftvault" / "web" / "app.js").read_text(encoding="utf-8")
        self.assertIn("c.contado === false", app)
        self.assertIn("runasCurto", app)
        self.assertIn("organizas à mão", app)
        cli = (REPO / "riftvault" / "cli.py").read_text(encoding="utf-8")
        self.assertIn("não se contam", cli)

    def test_nao_escreve(self):
        con = self.montar(copias={CALM: 8})
        ops = con.execute("SELECT COUNT(*) FROM ops").fetchone()[0]
        self.decks.allocate(con)
        self.payload(con)
        self.a_mais.payload(con)
        self.faltas.compras(con)
        self.assertEqual(con.execute("SELECT COUNT(*) FROM ops").fetchone()[0], ops)
        self.assertEqual(con.execute("SELECT qty FROM copies WHERE printing_id = ?",
                                     (CALM,)).fetchone()["qty"], 8)


if __name__ == "__main__":
    unittest.main()

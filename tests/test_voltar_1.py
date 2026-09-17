"""«Vamos voltar atrás» (2026-09-17): alvo 1 sempre, e os decks jogam a versão
normal — menos a Legend e o Champion, que jogam uma versão especial.

Palavras do André:
    *"as Alt Art, Overnumbered e SP voltam a 1 de cada, mesmo que joguem nos
    decks"*
    *"os decks apenas jogaram versoes normais, com excepcao da Legend e do
    Champion que serao Alt Art ou Overnumbered ou SP, mas nunca assinada"*

A regra, por extenso:
  1. o alvo de uma Alt Art, sobrenumerada ou promo é 1 — e NÃO sobe por
     causa dos decks (reverte o `max(1, procura)` de 2026-09-16);
  2. os decks jogam a impressão normal (a base, sem sobrenumeração): a cópia
     base da Coleção serve o deck, mesmo que a carta tenha Alt Art — e, desde
     a tarde de 2026-09-17, o que a base não tapar completa-se com outra
     versão que ele tenha, antes de ser falta (`test_versoes_deck.py`);
  3. a Legend e o Champion jogam UMA versão especial — Alt Art, sobrenumerada
     ou promo, qualquer delas serve; sem nenhuma, a falta aponta à mais
     barata e as outras ficam em `alternativas`;
  4. nunca uma assinada;
  5. (a) um Champion jogado mais do que uma vez: só UMA cópia é especial;
  6. sem versão especial no catálogo, a Legend/Champion joga a base e não há
     falta;
  7. a percentagem, o denominador e a wantlist do master set não mexem.

Tudo contra pastas temporárias (`tests.fixture.Vault`) e um config PRÓPRIO: o
`data/` e o `riftvault_config.json` a sério nunca são tocados.
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

CONFIG = Path(tempfile.gettempdir()) / "riftvault-voltar-1.json"


def escrever_config(papeis=("legend", "champion"),
                    especiais=("a", "overnumbered", "promo")) -> None:
    """O config desta ordem. Os defaults do `config.DEFAULTS` já dizem isto;
    escreve-se na mesma para o teste não depender do ficheiro real."""
    CONFIG.write_text(json.dumps({
        "master_set": {"fora_da_percentagem": ["a", "overnumbered", "promo"],
                       "escondidas": ["-T", "*", "-R"],
                       "um_de_cada": ["a", "overnumbered", "promo"]},
        "decks": {"so_normais_excepto": list(papeis),
                  "versoes_especiais": list(especiais)},
        "listas_de_compra": {"so_master_set": True},
    }), encoding="utf-8")
    os.environ["RIFTVAULT_CONFIG"] = str(CONFIG)


escrever_config()

from tests.fixture import Vault  # noqa: E402

# O Azir: Legend com alt art e signature; Champion com sobrenumerada e promo,
# jogado 3 vezes (1 no Champion + 2 no main); 3 Defy (tem alt art) e 3
# Brutalizer (só base).
AZIR = ("Legend:\n1 Emperor of the Sands\n\nChampion:\n1 Sovereign\n\n"
        "MainDeck:\n3 Defy\n3 Brutalizer\n2 Sovereign\n")
# A MESMA Legend, outra lista: partilha, não disputa.
AZIR_B = "Nome: Azir B\nLegend:\n1 Emperor of the Sands\n\nMainDeck:\n2 Defy\n"
# OUTRA Legend, sem versão especial nenhuma; o mesmo Champion do Azir.
ORNN = "Legend:\n1 Forge Master\n\nChampion:\n1 Sovereign\n\nMainDeck:\n2 Defy\n"

EMP, EMP_A, EMP_STAR = "tst-003-100", "tst-003a-100", "tst-003-star-100"
SOV, SOV_OVER, SOV_SP = "tst-004-100", "tst-102-100", "tst-sp1-006"
DEFY, DEFY_A, DEFY_OVER = "tst-001-100", "tst-001a-100", "tst-101-100"


class Base(unittest.TestCase):
    def setUp(self):
        escrever_config()
        self.addCleanup(lambda: os.environ.pop("RIFTVAULT_CONFIG", None))
        self.v = Vault()
        self.addCleanup(self.v.close)
        from riftvault import a_subir, decks, faltas, faltas_edicao, locais, metrics, pending
        for m in (metrics, locais, decks, pending, faltas, a_subir, faltas_edicao):
            importlib.reload(m)
        self.metrics, self.decks, self.faltas = metrics, decks, faltas
        self.a_subir, self.fe, self.pending, self.locais = a_subir, faltas_edicao, pending, locais

    def recarregar(self):
        from riftvault import config
        config.load.cache_clear()

    def catalogo(self, copias: dict | None = None, decks: dict | None = None):
        """Uma edição de 100 cartas, com preços; `copias` é {printing_id: n}."""
        from riftvault import collection
        con = self.v.connect()
        add = self.v.add_printing
        add(con, DEFY, "TST", 1, "Defy", size=100)
        add(con, DEFY_A, "TST", 1, "Defy", variant="a", kind="alt_art",
            rarity="showcase", base_rarity="common", size=100)
        add(con, "tst-002-100", "TST", 2, "Brutalizer", size=100)
        add(con, EMP, "TST", 3, "Emperor of the Sands", card_type="Legend", size=100)
        add(con, EMP_A, "TST", 3, "Emperor of the Sands", variant="a", kind="alt_art",
            card_type="Legend", rarity="showcase", base_rarity="epic", size=100)
        add(con, EMP_STAR, "TST", 3, "Emperor of the Sands", variant="star",
            kind="signature", card_type="Legend", rarity="showcase",
            base_rarity="epic", size=100, codigo="TST-003*/100")
        add(con, SOV, "TST", 4, "Sovereign", size=100)
        add(con, "tst-005-100", "TST", 5, "Forge Master", card_type="Legend", size=100)
        # Sobrenumeradas: a 101 (um Defy) e a 102 (um Sovereign) de um set de 100.
        add(con, DEFY_OVER, "TST", 101, "Defy", size=100, rarity="showcase", api_sort=101)
        add(con, SOV_OVER, "TST", 102, "Sovereign", size=100, rarity="showcase", api_sort=102)
        # A promo do Sovereign: a 1 de uma série de 6, fora da numeração.
        add(con, SOV_SP, "TST", 1, "Sovereign", variant="sp1", kind="special",
            lane="sp", codigo="TST-SP1/006", api_sort=201)
        self.v.rebuild(con)
        for pid, cents in ((DEFY, 150), (DEFY_A, 2000), (DEFY_OVER, 5000),
                           ("tst-002-100", 50), (EMP, 1000), (EMP_A, 3000),
                           (EMP_STAR, 9000), (SOV, 200), (SOV_OVER, 4000),
                           (SOV_SP, 700), ("tst-005-100", 1000)):
            con.execute("INSERT INTO catalog.price_latest (printing_id, price_cents) "
                        "VALUES (?,?)", (pid, cents))
        for pid, n in (copias or {}).items():
            collection.adjust(con, pid, n, source="test")
        for slug, texto in (decks if decks is not None else {"azir": AZIR}).items():
            self.v.write_deck(slug, texto)
        self.decks.import_all(con, log=lambda *_: None)
        return con

    # A coleção «normal» do Azir: tudo o que o deck pede, em base.
    BASE_DO_AZIR = {DEFY: 3, "tst-002-100": 3, EMP: 1, SOV: 3}

    def alvos(self, con) -> dict[str, int]:
        p = self.metrics.set_payload(con, "TST")
        return {pr["id"]: pr["target"] for g in p["groups"] for pr in g["printings"]}

    def idx(self, con) -> dict:
        return {d["slug"]: d for d in self.decks.decks_index(con)}

    def aloc(self, con, slug: str) -> dict:
        return self.decks.allocate(con)[self.idx(con)[slug]["id"]]

    def linha(self, con, slug: str, role: str, nome: str) -> dict:
        p = self.decks.deck_payload(con, self.idx(con)[slug]["id"])
        s = next(s for s in p["sections"] if s["role"] == role)
        return next(c for c in s["cards"] if c["name"] == nome)


# ---------------------------------------------------------------------------


class TestAlvoUmSempre(Base):
    """Regra 1: o alvo é 1 e não sobe por causa dos decks."""

    def test_alt_art_sobrenumerada_e_promo_pedem_1_com_o_deck_a_joga_las(self):
        con = self.catalogo()
        a = self.alvos(con)
        # O Azir joga 3 Defy e 3 Sovereign; mesmo assim as versões especiais
        # pedem 1, e a base pede o playset.
        self.assertEqual((a[DEFY], a[DEFY_A], a[DEFY_OVER]), (3, 1, 1))
        self.assertEqual((a[SOV], a[SOV_OVER], a[SOV_SP]), (3, 1, 1))
        self.assertEqual((a[EMP], a[EMP_A]), (1, 1))
        con.close()

    def test_o_alvo_nao_recebe_a_procura_dos_decks(self):
        """O parâmetro saiu: o `alvo` responde só com a linha e o config."""
        import inspect
        self.assertNotIn("procura", inspect.signature(self.metrics.alvo).parameters)
        self.assertFalse(hasattr(self.metrics, "procura_dos_decks"))
        self.assertFalse(hasattr(self.decks, "procura_dos_decks"))

    def test_o_cabecalho_do_bloco_diz_so_1_de_cada(self):
        con = self.catalogo()
        p = self.metrics.set_payload(con, "TST")
        rotulos = {b["id"]: b["label"] for b in p["blocks"]}
        self.assertEqual(rotulos["alt_art"], "Coleção — artes alternativas — 1 de cada")
        con.close()


class TestOsDecksJogamABase(Base):
    """Regra 2: a cópia base serve o deck, mesmo com Alt Art no catálogo."""

    def test_tres_defy_base_na_colecao_servem_o_deck(self):
        con = self.catalogo(copias=self.BASE_DO_AZIR)
        a = self.aloc(con, "azir")
        self.assertNotIn("defy", a["missing"])
        self.assertEqual(a["na_colecao"]["defy"], 3)
        # E a Alt Art do Defy fica a 0/1, sem falta para o deck.
        p = self.metrics.set_payload(con, "TST")
        tile = {pr["id"]: pr for g in p["groups"] for pr in g["printings"]}[DEFY_A]
        self.assertEqual((tile["qty"], tile["target"]), (0, 1))
        con.close()

    def test_uma_alt_art_do_defy_tapa_o_que_a_base_nao_chega(self):
        """Ele tem 2 Defy base e 1 Defy Alt Art: até à tarde de 2026-09-17 o
        deck ficava a faltar 1 base; desde então a alt art tapa o buraco
        (*"esteja disponível em Alt Art ou outra, usa"*) e a linha reparte-se
        por versão — ver `test_versoes_deck.py`."""
        con = self.catalogo(copias={**self.BASE_DO_AZIR, DEFY: 2, DEFY_A: 1})
        a = self.aloc(con, "azir")
        self.assertNotIn("defy", a["missing"])
        self.assertEqual(a["alloc_outras"].get("defy"), 1)
        self.assertEqual([(x["id"], x["qty"], x["lugar"]) for x in a["versoes_em"]["defy"]],
                         [(DEFY, 2, "normal"), (DEFY_A, 1, "outra")])
        # Sem Alt Art nenhuma, a falta continua a apontar à base.
        con.close()
        con = self.catalogo(copias={**self.BASE_DO_AZIR, DEFY: 2})
        a = self.aloc(con, "azir")
        self.assertEqual(a["missing"].get("defy"), 1)
        self.assertNotIn("defy", a["missing_especial"])
        item = next(x for d in self.decks.missing_by_set(con, self.idx(con)["azir"]["id"])
                    for x in d["items"] if x["card_key"] == "defy")
        self.assertEqual((item["code"], item["qty"], item["especial"]), ("TST-001/100", 1, False))
        con.close()

    def test_uma_sobrenumerada_tapa_um_lugar_normal_depois_da_base(self):
        """A «101/100» é OverNumbered — versão especial; serve o main só
        quando a base não chega (2026-09-17, tarde), e a base serve-se
        primeiro."""
        con = self.catalogo(copias={**self.BASE_DO_AZIR, DEFY: 2, DEFY_OVER: 1})
        a = self.aloc(con, "azir")
        self.assertNotIn("defy", a["missing"])
        self.assertEqual(a["versoes_em"]["defy"][0], {"id": DEFY, "qty": 2, "lugar": "normal"})
        self.assertEqual(a["versoes_em"]["defy"][1], {"id": DEFY_OVER, "qty": 1, "lugar": "outra"})
        con.close()


class TestLegendEChampionJogamEspecial(Base):
    """Regra 3: a Legend e o Champion pedem UMA versão especial."""

    def test_a_legend_base_nao_chega__falta_a_alt_art(self):
        con = self.catalogo(copias=self.BASE_DO_AZIR)
        a = self.aloc(con, "azir")
        self.assertEqual(a["missing"].get("emperor of the sands"), 1)
        self.assertEqual(a["missing_especial"].get("emperor of the sands"), 1)
        self.assertEqual(a["need_especial"].get("emperor of the sands"), 1)
        l = self.linha(con, "azir", "legend", "Emperor of the Sands")
        self.assertEqual((l["have"], l["missing"]), (0, 1))
        self.assertEqual((l["especial"]["code"], l["especial"]["missing"]), ("TST-003a/100", 1))
        self.assertEqual((l["order_code"], l["order_especial"]), ("TST-003a/100", True))
        con.close()

    def test_com_a_alt_art_da_legend_esta_servido__sem_base_sequer(self):
        con = self.catalogo(copias={**self.BASE_DO_AZIR, EMP: 0, EMP_A: 1})
        a = self.aloc(con, "azir")
        self.assertNotIn("emperor of the sands", a["missing"])
        self.assertEqual(a["alloc_especial"].get("emperor of the sands"), 1)
        self.assertEqual(a["especial_em"].get("emperor of the sands"), EMP_A)
        l = self.linha(con, "azir", "legend", "Emperor of the Sands")
        self.assertEqual((l["have"], l["missing"], l["especial"]["code"]), (1, 0, "TST-003a/100"))
        con.close()

    def test_o_champion_com_tres_bases_falta_uma_especial__a_mais_barata(self):
        """3 Sovereign base: os dois lugares normais estão servidos, o lugar
        do Champion não. Compra-se a promo (7 €), não a sobrenumerada (40 €),
        e a sobrenumerada fica como alternativa (dúvida (b))."""
        con = self.catalogo(copias=self.BASE_DO_AZIR)
        a = self.aloc(con, "azir")
        self.assertEqual((a["missing"]["sovereign"], a["missing_especial"]["sovereign"]), (1, 1))
        self.assertEqual(a["alloc"]["sovereign"], 2)
        item = next(x for d in self.decks.missing_by_set(con, self.idx(con)["azir"]["id"])
                    for x in d["items"] if x["card_key"] == "sovereign")
        self.assertEqual((item["code"], item["qty"], item["price"], item["especial"]),
                         ("TST-SP1/006", 1, 700, True))
        self.assertEqual([x["code"] for x in item["alternativas"]], ["TST-102/100"])
        con.close()

    def test_qualquer_versao_especial_serve__a_sobrenumerada_tambem(self):
        con = self.catalogo(copias={**self.BASE_DO_AZIR, SOV: 2, SOV_OVER: 1})
        a = self.aloc(con, "azir")
        self.assertNotIn("sovereign", a["missing"])
        self.assertEqual(a["especial_em"]["sovereign"], SOV_OVER)
        con.close()

    def test_a_promo_serve_o_champion(self):
        con = self.catalogo(copias={**self.BASE_DO_AZIR, SOV: 2, SOV_SP: 1})
        self.assertNotIn("sovereign", self.aloc(con, "azir")["missing"])
        con.close()

    def test_a_pagina_do_deck_poe_a_especial_no_champion_e_as_normais_no_main(self):
        con = self.catalogo(copias={**self.BASE_DO_AZIR, SOV: 2, SOV_SP: 1})
        ch = self.linha(con, "azir", "champion", "Sovereign")
        self.assertEqual((ch["wanted"], ch["have"], ch["missing"]), (1, 1, 0))
        self.assertEqual(ch["especial"]["code"], "TST-SP1/006")
        mn = self.linha(con, "azir", "main", "Sovereign")
        self.assertEqual((mn["wanted"], mn["have"], mn["missing"], mn["especial"]), (2, 2, 0, None))
        con.close()


class TestNuncaAssinada(Base):
    """Regra 4."""

    def test_a_signature_da_legend_nao_serve(self):
        con = self.catalogo(copias={**self.BASE_DO_AZIR, EMP_STAR: 1})
        a = self.aloc(con, "azir")
        self.assertEqual(a["missing_especial"].get("emperor of the sands"), 1)
        self.assertNotIn(EMP_STAR, a["grupo"]["impressoes"]["na_colecao"])
        con.close()

    def test_a_signature_nunca_e_a_versao_a_comprar(self):
        con = self.catalogo(copias=self.BASE_DO_AZIR)
        vs = self.decks.versoes_dos_decks(con)
        self.assertNotIn(EMP_STAR, vs.especiais_de("emperor of the sands"))
        self.assertNotIn(EMP_STAR, vs.normais_de("emperor of the sands"))
        con.close()

    def test_escrever_a_signature_no_config_rebenta(self):
        escrever_config(especiais=("a", "*"))
        self.recarregar()
        con = self.catalogo()
        with self.assertRaises(ValueError):
            self.decks.versoes_dos_decks(con)
        con.close()


class TestUmaSoEspecial(Base):
    """Regra 5, a dúvida (a): o Champion jogado 3 vezes tem 1 especial + 2 normais."""

    def test_duas_especiais_e_nenhuma_base__uma_e_o_champion_a_outra_tapa_o_main(self):
        """A promo (a mais barata) serve o lugar do Champion; a sobrenumerada
        tapa um dos dois lugares normais (2026-09-17, tarde) e falta 1 base."""
        con = self.catalogo(copias={**self.BASE_DO_AZIR, SOV: 0, SOV_SP: 1, SOV_OVER: 1})
        a = self.aloc(con, "azir")
        self.assertEqual(a["missing"]["sovereign"], 1)
        self.assertNotIn("sovereign", a["missing_especial"])
        self.assertEqual(a["alloc_especial"]["sovereign"], 1)
        self.assertEqual(a["alloc_outras"]["sovereign"], 1)
        self.assertEqual([(x["id"], x["lugar"]) for x in a["versoes_em"]["sovereign"]],
                         [(SOV_SP, "especial"), (SOV_OVER, "outra")])
        item = next(x for d in self.decks.missing_by_set(con, self.idx(con)["azir"]["id"])
                    for x in d["items"] if x["card_key"] == "sovereign")
        self.assertEqual((item["code"], item["qty"], item["especial"]), ("TST-004/100", 1, False))
        con.close()

    def test_a_falta_de_um_champion_sem_nada_e_1_especial_mais_2_normais(self):
        con = self.catalogo(copias={**self.BASE_DO_AZIR, SOV: 0})
        a = self.aloc(con, "azir")
        self.assertEqual((a["missing"]["sovereign"], a["missing_especial"]["sovereign"]), (3, 1))
        # Duas linhas no «Falta comprar, por edição»: 1× promo, 2× base.
        itens = [(x["code"], x["qty"], x["especial"])
                 for d in self.decks.missing_by_set(con, self.idx(con)["azir"]["id"])
                 for x in d["items"] if x["card_key"] == "sovereign"]
        self.assertEqual(sorted(itens), [("TST-004/100", 2, False), ("TST-SP1/006", 1, True)])
        r = self.decks.resumo_das_faltas(con)
        self.assertEqual((r["copies"], r["cents"]), (3 + 1, 2 * 200 + 700 + 3000))
        self.assertEqual(r["especiais"], {"cards": 2, "copies": 2, "cents": 3700})
        con.close()


class TestSemVersaoEspecialJogaABase(Base):
    """Regra 6: o Forge Master só existe em base — joga-a e não há falta."""

    def test_forge_master_base_serve_a_legend(self):
        con = self.catalogo(copias={"tst-005-100": 1, DEFY: 2, SOV: 3, SOV_SP: 1},
                            decks={"ornn": ORNN})
        a = self.aloc(con, "ornn")
        self.assertNotIn("forge master", a["missing"])
        self.assertEqual(a["need_especial"], {"sovereign": 1})
        l = self.linha(con, "ornn", "legend", "Forge Master")
        self.assertEqual((l["have"], l["missing"], l["especial"]), (1, 0, None))
        con.close()


class TestGrupos(Base):
    """Mesma Legend: uma especial; Legends diferentes com o mesmo Champion: soma."""

    def test_duas_listas_da_mesma_legend_pedem_uma_especial(self):
        con = self.catalogo(copias=self.BASE_DO_AZIR, decks={"azir": AZIR, "azir-b": AZIR_B})
        r = self.decks.resumo_das_faltas(con)
        self.assertEqual(r["especiais"]["copies"], 2)  # a Legend e o Champion, uma vez
        con.close()

    def test_dois_decks_com_o_mesmo_champion_disputam_a_especial(self):
        con = self.catalogo(copias={**self.BASE_DO_AZIR, SOV_SP: 1, "tst-005-100": 1},
                            decks={"azir": AZIR, "ornn": ORNN})
        azir, ornn = self.aloc(con, "azir"), self.aloc(con, "ornn")
        self.assertNotIn("sovereign", azir["missing"])
        self.assertEqual(ornn["missing_especial"].get("sovereign"), 1)
        self.assertIn("sovereign", ornn["shared"])
        con.close()


class TestCompras(Base):
    """Staples, Todos juntos, o `+` das encomendas e a proposta de marcação."""

    def test_o_shortfall_diz_a_especial_a_parte(self):
        con = self.catalogo(copias=self.BASE_DO_AZIR)
        sf = {x["card_key"]: x for x in self.faltas.shortfall(con)}
        e = sf["emperor of the sands"]
        self.assertEqual((e["missing"], e["total"]), (1, 3000))
        self.assertEqual((e["especial"]["qty"], e["especial"]["code"]), (1, "TST-003a/100"))
        s = sf["sovereign"]
        self.assertEqual((s["missing"], s["especial"]["code"], s["total"]), (1, "TST-SP1/006", 700))
        self.assertNotIn("defy", sf)
        con.close()

    def test_todos_juntos_e_o_cardmarket_pedem_a_versao_certa(self):
        con = self.catalogo(copias={**self.BASE_DO_AZIR, SOV: 0})
        tj = self.faltas.todos_juntos(con)
        itens = {(x["card_key"], x["especial"]): x for d in tj["by_set"] for x in d["items"]}
        self.assertEqual(itens[("sovereign", True)]["qty"], 1)
        self.assertEqual(itens[("sovereign", False)]["qty"], 2)
        self.assertEqual(tj["copies"], 4)
        w = self.faltas.wantlist(tj["by_set"], com_edicao=False, com_versao=False)
        self.assertEqual(w["lines"], 3)
        con.close()

    def test_o_mais_da_legend_encomenda_a_alt_art_e_o_do_main_a_base(self):
        con = self.catalogo(copias={**self.BASE_DO_AZIR, SOV: 0})
        self.assertEqual(self.pending.impressao_para_encomendar(
            con, ["emperor of the sands"], especial=True)["emperor of the sands"]["id"], EMP_A)
        self.assertEqual(self.pending.impressao_para_encomendar(
            con, ["sovereign"])["sovereign"]["id"], SOV)
        self.pending.encomendar(con, "emperor of the sands", especial=True, source="test")
        a = self.aloc(con, "azir")
        self.assertNotIn("emperor of the sands", a["missing"])
        self.assertEqual(a["a_caminho_especial"]["emperor of the sands"], 1)
        # Uma base a caminho não cobre o lugar especial; uma promo cobre.
        self.pending.encomendar(con, "sovereign", source="test")
        self.assertEqual(self.aloc(con, "azir")["missing_especial"]["sovereign"], 1)
        self.pending.encomendar(con, "sovereign", especial=True, source="test")
        self.assertEqual(self.aloc(con, "azir")["missing_especial"], {})
        # O `−` da linha do Champion só tira a especial.
        res = self.pending.anular(con, "sovereign", especial=True, source="test")
        self.assertEqual(res["printing_id"], SOV_SP)
        con.close()

    def test_a_proposta_de_marcacao_leva_a_especial_para_a_legend_e_a_base_para_o_main(self):
        con = self.catalogo(copias={**self.BASE_DO_AZIR, EMP_A: 1, SOV_SP: 1})
        prop = {(x["printing_id"]): x["qty"] for x in self.locais.propor_deck(con, "azir")["items"]}
        self.assertEqual(prop[EMP_A], 1)
        self.assertNotIn(EMP, prop)
        self.assertEqual((prop[SOV_SP], prop[SOV]), (1, 2))
        self.assertEqual(prop[DEFY], 3)
        con.close()


class TestConfig(Base):
    def test_sem_papeis_especiais_tudo_joga_a_base(self):
        escrever_config(papeis=())
        self.recarregar()
        con = self.catalogo(copias=self.BASE_DO_AZIR)
        a = self.aloc(con, "azir")
        self.assertEqual((a["missing"], a["need_especial"]), ({}, {}))
        con.close()

    def test_um_papel_desconhecido_rebenta(self):
        escrever_config(papeis=("legend", "comandante"))
        self.recarregar()
        con = self.catalogo()
        with self.assertRaises(ValueError):
            self.decks.allocate(con)
        con.close()

    def test_so_alt_art_como_especial(self):
        """Com `versoes_especiais: ["a"]` a promo e a sobrenumerada deixam de
        servir o Champion — e sem alt art de Sovereign ele joga a base."""
        escrever_config(especiais=("a",))
        self.recarregar()
        con = self.catalogo(copias=self.BASE_DO_AZIR)
        a = self.aloc(con, "azir")
        self.assertEqual(a["need_especial"], {"emperor of the sands": 1})
        self.assertNotIn("sovereign", a["missing"])
        con.close()


class TestOMasterSetNaoMexe(Base):
    """Regra 7."""

    def medir(self, con) -> tuple:
        niv = self.metrics.niveis_payload(con)
        w = self.a_subir.wantlist(con)
        p = self.metrics.set_payload(con, "TST")["progress"]["master"]
        return ([(n["done"], n["total"], n["missing"]) for n in niv["levels"]],
                (w["copies"], w["cents"], sorted(x["printing_id"] for x in w["items"])),
                (p["done"], p["total"]))

    def test_com_e_sem_decks_o_master_set_le_se_igual(self):
        copias = {**self.BASE_DO_AZIR, DEFY: 2, DEFY_A: 1}
        con = self.catalogo(copias=copias)
        com = self.medir(con)
        con.close()
        self.v = Vault()
        self.addCleanup(self.v.close)
        con = self.catalogo(copias=copias, decks={})
        sem = self.medir(con)
        con.close()
        self.assertEqual(com, sem)
        # A wantlist nunca pede a versão especial da Legend, por muito que o
        # deck a peça (`listas_de_compra.so_master_set`).
        self.assertNotIn(EMP_A, com[1][2])
        self.assertIn(DEFY, com[1][2])

    def test_o_bloco_alt_art_do_faltas_nao_conta_a_procura_dos_decks(self):
        con = self.catalogo(copias=self.BASE_DO_AZIR)
        p = self.fe.payload(con)
        s = next(s for s in p["sets"] if s["set"] == "TST")
        b = next(b for b in s["blocks"] if b["id"] == "alt_art")
        alvos = {x["printing_id"]: x["target"] for x in b["items"]}
        self.assertEqual(alvos, {DEFY_A: 1, EMP_A: 1})
        con.close()


if __name__ == "__main__":
    unittest.main()

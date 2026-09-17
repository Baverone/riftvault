"""As runas dos decks em Alt Art DA EDIÇÃO DA LEGEND (2026-09-17).

Palavras do André, em resposta ao relatório do `altart-decks`:
    *"sim, as runas dos Decks em Alt Art da edicao da Legend"*

A regra, por extenso (`decks.runas_alt_art_da_edicao_da_legend`):
  1. a Legend do deck define a edição de referência (`decks.edicao_da_legend`);
  2. as runas do deck pedem a arte alternativa DESSA edição — a alt art de
     outra edição não serve e não se compra;
  3. uma runa sem alt art nessa edição cai para a BASE (a base da Coleção
     serve o deck, como a 2026-09-11) — não vai buscar a alt art de outra
     edição;
  4. só as runas mudam: o resto do deck joga alt art de qualquer edição
     (2026-09-16);
  5. dois decks de edições diferentes jogam a mesma runa em impressões
     diferentes e não disputam as mesmas cópias;
  6. o alvo da alt art de uma runa na Coleção sobe só com os decks cuja
     Legend é dessa edição;
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

CONFIG = Path(tempfile.gettempdir()) / "riftvault-runas-legend.json"


def escrever_config(por_edicao: bool = True) -> None:
    CONFIG.write_text(json.dumps({
        "master_set": {"fora_da_percentagem": ["a", "overnumbered", "promo"],
                       "escondidas": ["-T", "*", "-R"],
                       "um_de_cada": ["a", "overnumbered", "promo"]},
        "decks": {"jogam_alt_art": True,
                  "runas_alt_art_da_edicao_da_legend": por_edicao},
        "runas_especiais": {"tipos": ["Rune"], "excepto": ["base"]},
        "listas_de_compra": {"so_master_set": True},
    }), encoding="utf-8")
    os.environ["RIFTVAULT_CONFIG"] = str(CONFIG)


escrever_config()

from tests.fixture import Vault  # noqa: E402

# Legend da edição AAA: 4 Calm Rune (alt art em AAA e em BBB), 4 Order Rune
# (sem alt art), 4 Mind Rune (alt art só em BBB), 3 Defy (Unit, alt art nas duas).
AZIR = ("Legend:\n1 Emperor of the Sands\n\nMainDeck:\n3 Defy\n\n"
        "Rune Pool:\n4 Calm Rune\n4 Order Rune\n4 Mind Rune\n")
# Legend da edição BBB: 2 Calm Rune.
ORNN = "Legend:\n1 Forge Master\n\nRune Pool:\n2 Calm Rune\n"

PRECOS = {"aaa-001-100": 10, "aaa-001a-100": 500, "bbb-001-100": 12,
          "bbb-001a-100": 300, "aaa-002-100": 10, "bbb-006-100": 11,
          "bbb-006a-100": 400, "aaa-004-100": 150, "aaa-004a-100": 2000,
          "bbb-004a-100": 1500, "aaa-003-100": 1000, "bbb-005-100": 1000}


class Base(unittest.TestCase):
    def setUp(self):
        escrever_config()
        self.addCleanup(lambda: os.environ.pop("RIFTVAULT_CONFIG", None))
        self.v = Vault()
        self.addCleanup(self.v.close)
        from riftvault import a_subir, decks, faltas, locais, metrics, pending
        for m in (metrics, locais, decks, pending, faltas, a_subir):
            importlib.reload(m)
        self.metrics, self.decks, self.faltas = metrics, decks, faltas
        self.a_subir, self.pending, self.locais = a_subir, pending, locais

    def recarregar(self):
        from riftvault import config
        config.load.cache_clear()

    def catalogo(self, copias: dict[str, int] | None = None,
                 decks: dict | None = None):
        from riftvault import collection
        con = self.v.connect()
        add = self.v.add_printing
        # AAA
        add(con, "aaa-001-100", "AAA", 1, "Calm Rune", card_type="Rune", size=100)
        add(con, "aaa-001a-100", "AAA", 1, "Calm Rune", card_type="Rune", variant="a",
            kind="alt_art", rarity="showcase", base_rarity="common", size=100)
        add(con, "aaa-002-100", "AAA", 2, "Order Rune", card_type="Rune", size=100)
        add(con, "aaa-003-100", "AAA", 3, "Emperor of the Sands", card_type="Legend", size=100)
        add(con, "aaa-004-100", "AAA", 4, "Defy", size=100)
        add(con, "aaa-004a-100", "AAA", 4, "Defy", variant="a", kind="alt_art",
            rarity="showcase", base_rarity="common", size=100)
        # BBB
        add(con, "bbb-001-100", "BBB", 1, "Calm Rune", card_type="Rune", size=100)
        add(con, "bbb-001a-100", "BBB", 1, "Calm Rune", card_type="Rune", variant="a",
            kind="alt_art", rarity="showcase", base_rarity="common", size=100)
        add(con, "bbb-004a-100", "BBB", 4, "Defy", variant="a", kind="alt_art",
            rarity="showcase", base_rarity="common", size=100)
        add(con, "bbb-005-100", "BBB", 5, "Forge Master", card_type="Legend", size=100)
        add(con, "bbb-006-100", "BBB", 6, "Mind Rune", card_type="Rune", size=100)
        add(con, "bbb-006a-100", "BBB", 6, "Mind Rune", card_type="Rune", variant="a",
            kind="alt_art", rarity="showcase", base_rarity="common", size=100)
        self.v.rebuild(con)
        for pid, cents in PRECOS.items():
            con.execute("INSERT INTO catalog.price_latest (printing_id, price_cents) "
                        "VALUES (?,?)", (pid, cents))
        for pid, n in (copias or {}).items():
            collection.adjust(con, pid, n, source="test")
        for slug, texto in (decks if decks is not None else
                            {"azir": AZIR, "ornn": ORNN}).items():
            self.v.write_deck(slug, texto)
        self.decks.import_all(con, log=lambda *_: None)
        return con

    def idx(self, con) -> dict:
        return {d["slug"]: d for d in self.decks.decks_index(con)}

    def falta_de(self, con, slug: str) -> dict[str, int]:
        return self.decks.allocate(con)[self.idx(con)[slug]["id"]]["missing"]

    def alvos(self, con, set_id: str) -> dict[str, int]:
        p = self.metrics.set_payload(con, set_id)
        return {pr["id"]: pr["target"] for g in p["groups"] for pr in g["printings"]}


class TestAEdicaoDaLegend(Base):
    """Regra 1: a Legend diz a edição."""

    def test_a_edicao_e_a_da_legend(self):
        con = self.catalogo()
        self.assertEqual(self.decks.edicao_do_deck(con, "azir"), "AAA")
        self.assertEqual(self.decks.edicao_do_deck(con, "ornn"), "BBB")
        self.assertEqual({g["legend"]: g["edicao"] for g in self.decks.grupos(con)},
                         {"emperor of the sands": "AAA", "forge master": "BBB"})
        con.close()

    def test_sem_legend_nao_ha_edicao_e_a_runa_cai_para_a_base(self):
        con = self.catalogo(copias={"aaa-001-100": 4},
                            decks={"solto": "Rune Pool:\n4 Calm Rune\n"})
        self.assertIsNone(self.decks.edicao_do_deck(con, "solto"))
        self.assertEqual(self.falta_de(con, "solto"), {})
        con.close()


class TestARunaEDaEdicao(Base):
    """Regras 2 e 5: a alt art da edição da Legend, e só essa."""

    def test_a_alt_art_da_edicao_da_legend_serve(self):
        con = self.catalogo(copias={"aaa-001a-100": 4, "bbb-001a-100": 2})
        self.assertNotIn("calm rune", self.falta_de(con, "azir"))
        self.assertNotIn("calm rune", self.falta_de(con, "ornn"))
        con.close()

    def test_a_alt_art_de_outra_edicao_nao_serve__nem_a_base(self):
        for pid in ("bbb-001a-100", "aaa-001-100", "bbb-001-100"):
            with self.subTest(copia=pid):
                self.v = Vault()
                self.addCleanup(self.v.close)
                con = self.catalogo(copias={pid: 4})
                self.assertEqual(self.falta_de(con, "azir").get("calm rune"), 4)
                con.close()

    def test_dois_decks_de_edicoes_diferentes_nao_disputam(self):
        """O Ornn (BBB) pede 2 Calm Rune e há 2 `bbb-001a`: são dele, mesmo
        com o Azir (prioridade 1) a pedir 4 Calm Rune — o Azir quer a `aaa-001a`."""
        con = self.catalogo(copias={"bbb-001a-100": 2})
        self.assertEqual(self.falta_de(con, "azir").get("calm rune"), 4)
        self.assertNotIn("calm rune", self.falta_de(con, "ornn"))
        # E a falta do Azir não está «noutro deck»: são impressões diferentes.
        a = self.decks.allocate(con)[self.idx(con)["azir"]["id"]]
        self.assertNotIn("calm rune", a["shared"])
        con.close()

    def test_compra_se_a_alt_art_da_edicao_da_legend(self):
        con = self.catalogo()
        azir, ornn = self.idx(con)["azir"]["id"], self.idx(con)["ornn"]["id"]
        item = {x["card_key"]: x for d in self.decks.missing_by_set(con, azir)
                for x in d["items"]}["calm rune"]
        self.assertEqual((item["code"], item["qty"], item["price"], item["alt_art"]),
                         ("AAA-001a/100", 4, 500, True))
        item = {x["card_key"]: x for d in self.decks.missing_by_set(con, ornn)
                for x in d["items"]}["calm rune"]
        self.assertEqual((item["code"], item["price"], item["alt_art"]),
                         ("BBB-001a/100", 300, True))
        self.assertEqual(self.pending.impressao_para_encomendar(
            con, ["calm rune"], "BBB")["calm rune"]["id"], "bbb-001a-100")
        self.assertEqual(self.pending.impressao_para_encomendar(
            con, ["calm rune"], "AAA")["calm rune"]["id"], "aaa-001a-100")
        # A lista de compras de todos os decks: duas linhas de Calm Rune, ao
        # preço de cada impressão.
        linhas = sorted((x["qty"], x["price_cents"]) for x in
                        self.decks.shopping_list(con) if x["card_key"] == "calm rune")
        self.assertEqual(linhas, [(2, 300), (4, 500)])
        con.close()

    def test_uma_encomenda_da_alt_art_de_outra_edicao_nao_abate_a_falta(self):
        con = self.catalogo()
        self.pending.add(con, "bbb-001a-100", 2, source="test")
        self.assertEqual(self.falta_de(con, "azir").get("calm rune"), 4)
        self.assertNotIn("calm rune", self.falta_de(con, "ornn"))
        con.close()

    def test_a_proposta_de_marcacao_so_tira_a_alt_art_da_edicao(self):
        con = self.catalogo(copias={"aaa-001a-100": 4, "bbb-001a-100": 4,
                                    "aaa-001-100": 4})
        prop = self.locais.propor_deck(con, "azir")
        self.assertEqual([(x["printing_id"], x["qty"]) for x in prop["items"]
                          if x["card_key"] == "calm rune"], [("aaa-001a-100", 4)])
        con.close()


class TestSemAltArtNaEdicaoCaiParaABase(Base):
    """Regra 3: o Mind Rune só tem alt art em BBB; o Azir (AAA) pede a base."""

    def test_a_base_serve_e_a_alt_art_de_outra_edicao_nao(self):
        con = self.catalogo(copias={"bbb-006-100": 4})
        self.assertNotIn("mind rune", self.falta_de(con, "azir"))
        con.close()
        self.v = Vault()
        self.addCleanup(self.v.close)
        con = self.catalogo(copias={"bbb-006a-100": 4})
        self.assertEqual(self.falta_de(con, "azir").get("mind rune"), 4)
        con.close()

    def test_compra_se_a_base(self):
        con = self.catalogo()
        azir = self.idx(con)["azir"]["id"]
        itens = {x["card_key"]: x for d in self.decks.missing_by_set(con, azir)
                 for x in d["items"]}
        self.assertEqual((itens["mind rune"]["code"], itens["mind rune"]["alt_art"]),
                         ("BBB-006/100", False))
        # E a runa sem alt art em lado nenhum continua como sempre: a base.
        self.assertEqual((itens["order rune"]["code"], itens["order rune"]["alt_art"]),
                         ("AAA-002/100", False))
        r = self.decks.resumo_das_faltas(con)
        # Alt art em falta: 4 Calm Rune (AAA) + 2 Calm Rune (BBB) + 3 Defy.
        self.assertEqual(r["alt_art"]["copies"], 9)
        self.assertEqual(r["alt_art"]["cents"], 4 * 500 + 2 * 300 + 3 * 1500)
        con.close()


class TestSoAsRunasMudam(Base):
    """Regra 4: o Defy joga alt art de qualquer edição."""

    def test_a_alt_art_de_outra_edicao_serve_uma_unit(self):
        con = self.catalogo(copias={"bbb-004a-100": 3})
        self.assertNotIn("defy", self.falta_de(con, "azir"))
        con.close()


class TestOAlvoNaColecao(Base):
    """Regra 6: a alt art da runa sobe só com a edição da Legend."""

    def test_a_procura_vem_por_edicao_nas_runas(self):
        con = self.catalogo()
        self.assertEqual(self.metrics.procura_dos_decks(con),
                         {"calm rune": {"AAA": 4, "BBB": 2}, "defy": 3})
        a = self.alvos(con, "AAA")
        b = self.alvos(con, "BBB")
        self.assertEqual((a["aaa-001a-100"], b["bbb-001a-100"]), (4, 2))
        # O Mind Rune só tem alt art em BBB e nenhum deck de BBB o joga: 1.
        self.assertEqual(b["bbb-006a-100"], 1)
        # O Defy: 3, em qualquer das duas edições.
        self.assertEqual((a["aaa-004a-100"], b["bbb-004a-100"]), (3, 3))
        con.close()


class TestDesligado(Base):
    """`runas_alt_art_da_edicao_da_legend: false` é 2026-09-16: qualquer alt art."""

    def test_sem_a_regra_a_alt_art_de_outra_edicao_serve(self):
        escrever_config(por_edicao=False)
        self.recarregar()
        con = self.catalogo(copias={"bbb-001a-100": 4})
        self.assertNotIn("calm rune", self.falta_de(con, "azir"))
        self.assertEqual(self.metrics.procura_dos_decks(con)["calm rune"], 6)
        con.close()

    def test_o_default_e_ligado(self):
        from riftvault import config
        self.assertTrue(config.DEFAULTS["decks"]["runas_alt_art_da_edicao_da_legend"])


class TestOMasterSetNaoMexe(Base):
    """Regra 7."""

    def medir(self, con) -> tuple:
        niv = self.metrics.niveis_payload(con)
        w = self.a_subir.wantlist(con)
        return ([(n["done"], n["total"], n["missing"]) for n in niv["levels"]],
                (w["copies"], w["cents"], sorted(x["printing_id"] for x in w["items"])))

    def test_com_e_sem_a_regra_o_master_set_le_se_igual(self):
        copias = {"aaa-001-100": 2, "aaa-001a-100": 1, "bbb-001a-100": 1}
        con = self.catalogo(copias=copias)
        com = self.medir(con)
        con.close()
        escrever_config(por_edicao=False)
        self.recarregar()
        self.v = Vault()
        self.addCleanup(self.v.close)
        con = self.catalogo(copias=copias)
        sem = self.medir(con)
        con.close()
        self.assertEqual(com, sem)
        self.assertNotIn("aaa-001a-100", com[1][2])
        self.assertIn("aaa-001-100", com[1][2])


if __name__ == "__main__":
    unittest.main()

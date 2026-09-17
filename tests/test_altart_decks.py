"""Alt Art e sobrenumeradas a 1 de cada; os decks jogam em Alt Art (2026-09-16).

Palavras do André:
    *"vamos fazer uma organizacao diferente / Alt Art e Overnumbered e assim
    quero apenas 1 de cada / se jogar num deck, acrescentas as necessarias para
    o deck, e o deck joga com Alt Art"*
    *"se o deck joga 3, vou ter que ter 3 normais e 3 Alt Art"*
    e a Alt Art vale *"sempre que existir Alt Art"*.

A regra, por extenso:
  1. uma arte alternativa que nenhum deck use pede 1;
  2. uma carta que um deck jogue N vezes e que TENHA arte alternativa: o alvo
     da arte alternativa sobe a N, e o master set continua a pedir o playset
     da base — seis cópias, dois conjuntos; a cópia base NÃO serve o deck;
  3. dois decks com a mesma Legend são duas listas do mesmo deck: o máximo,
     não a soma;
  4. uma carta SEM arte alternativa: nada muda, a cópia da Coleção serve o
     deck (a partilha de 2026-09-11);
  5. uma sobrenumerada pede 1, com ou sem deck;
  6. a percentagem, o denominador e a wantlist do master set não mexem.

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

CONFIG = Path(tempfile.gettempdir()) / "riftvault-altart-decks.json"


def escrever_config(jogam_alt_art: bool = True) -> None:
    """O config desta ordem: `um_de_cada` com o "a" e os decks em Alt Art.

    Os defaults do `config.DEFAULTS` já dizem isto; escreve-se na mesma para o
    teste não depender do ficheiro real nem do que os defaults vierem a ser.
    """
    CONFIG.write_text(json.dumps({
        "master_set": {"fora_da_percentagem": ["a", "overnumbered", "promo"],
                       "escondidas": ["-T", "*", "-R"],
                       "um_de_cada": ["a", "overnumbered", "promo"]},
        "decks": {"jogam_alt_art": jogam_alt_art},
        "listas_de_compra": {"so_master_set": True},
    }), encoding="utf-8")
    os.environ["RIFTVAULT_CONFIG"] = str(CONFIG)


escrever_config()

from tests.fixture import Vault  # noqa: E402

# O Azir joga 3 Defy (tem arte alternativa) e 3 Brutalizer (não tem).
AZIR = "Legend:\n1 Emperor of the Sands\n\nMainDeck:\n3 Defy\n3 Brutalizer\n"
# A MESMA Legend, outra lista: 2 Defy. Partilha, não disputa.
AZIR_B = "Nome: Azir B\nLegend:\n1 Emperor of the Sands\n\nMainDeck:\n2 Defy\n"
# OUTRA Legend: disputa as mesmas cópias.
ORNN = ("Legend:\n1 Forge Master\n\nMainDeck:\n2 Defy\n")


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

    def catalogo(self, defy: int = 3, defy_alt: int = 0, over: int = 0,
                 decks: dict | None = None):
        """Uma edição: Defy (base + alt art), Brutalizer (só base), um Legend,
        uma sobrenumerada. `defy`/`defy_alt`/`over` são cópias na Coleção."""
        from riftvault import collection
        con = self.v.connect()
        self.v.add_printing(con, "tst-001-100", "TST", 1, "Defy", size=100)
        self.v.add_printing(con, "tst-001a-100", "TST", 1, "Defy",
                            variant="a", kind="alt_art", rarity="showcase",
                            base_rarity="common", size=100)
        self.v.add_printing(con, "tst-002-100", "TST", 2, "Brutalizer", size=100)
        self.v.add_printing(con, "tst-003-100", "TST", 3, "Emperor of the Sands",
                            card_type="Legend", size=100)
        self.v.add_printing(con, "tst-005-100", "TST", 5, "Forge Master",
                            card_type="Legend", size=100)
        # Sobrenumerada: a 101 de um set de 100, da mesma carta que o Defy.
        self.v.add_printing(con, "tst-101-100", "TST", 101, "Defy", size=100,
                            rarity="showcase", api_sort=101)
        self.v.rebuild(con)
        for pid, cents in (("tst-001-100", 150), ("tst-001a-100", 2000),
                           ("tst-002-100", 50), ("tst-003-100", 1000),
                           ("tst-005-100", 1000), ("tst-101-100", 5000)):
            con.execute("INSERT INTO catalog.price_latest (printing_id, price_cents) "
                        "VALUES (?,?)", (pid, cents))
        for pid, n in (("tst-001-100", defy), ("tst-001a-100", defy_alt),
                       ("tst-101-100", over), ("tst-002-100", 3), ("tst-003-100", 1)):
            if n:
                collection.adjust(con, pid, n, source="test")
        for slug, texto in (decks if decks is not None else {"azir": AZIR}).items():
            self.v.write_deck(slug, texto)
        self.decks.import_all(con, log=lambda *_: None)
        return con

    def alvos(self, con) -> dict[str, int]:
        p = self.metrics.set_payload(con, "TST")
        return {pr["id"]: pr["target"] for g in p["groups"] for pr in g["printings"]}

    def tile(self, con, pid: str) -> dict:
        p = self.metrics.set_payload(con, "TST")
        return {pr["id"]: pr for g in p["groups"] for pr in g["printings"]}[pid]

    def idx(self, con) -> dict:
        return {d["slug"]: d for d in self.decks.decks_index(con)}

    def falta_de(self, con, slug: str) -> dict[str, int]:
        deck_id = self.idx(con)[slug]["id"]
        return self.decks.allocate(con)[deck_id]["missing"]

    def bloco_faltas(self, con, bloco: str) -> dict:
        p = self.fe.payload(con)
        s = next(s for s in p["sets"] if s["set"] == "TST")
        return next(b for b in s["blocks"] if b["id"] == bloco)


# ---------------------------------------------------------------------------


class TestUmDeCada(Base):
    """Regra 1 e 5: sem deck, a Alt Art e a sobrenumerada pedem 1."""

    def test_uma_alt_art_que_nenhum_deck_usa_pede_1(self):
        con = self.catalogo(decks={})
        self.assertEqual(self.alvos(con)["tst-001a-100"], 1)
        self.assertEqual(self.metrics.procura_dos_decks(con), {})
        con.close()

    def test_com_1_copia_esta_completa_e_nao_aparece_nas_faltas(self):
        con = self.catalogo(decks={}, defy_alt=1)
        t = self.tile(con, "tst-001a-100")
        self.assertEqual((t["qty"], t["target"]), (1, 1))
        b = self.bloco_faltas(con, "alt_art")
        self.assertEqual([x["printing_id"] for x in b["items"]], [])
        self.assertEqual((b["cards"], b["copies"]), (0, 0))
        con.close()

    def test_a_sobrenumerada_pede_1_com_ou_sem_deck(self):
        for decks in ({}, {"azir": AZIR}):
            with self.subTest(decks=sorted(decks)):
                self.v = Vault()
                self.addCleanup(self.v.close)
                con = self.catalogo(decks=decks)
                # O Azir joga 3 Defy, e a sobrenumerada É um Defy: mesmo assim
                # pede 1 — é a arte alternativa que os decks jogam, não esta.
                self.assertEqual(self.alvos(con)["tst-101-100"], 1)
                b = self.bloco_faltas(con, "overnumbered")
                self.assertEqual([(x["printing_id"], x["target"]) for x in b["items"]],
                                 [("tst-101-100", 1)])
                con.close()


class TestODeckJogaEmAltArt(Base):
    """Regra 2: *"se o deck joga 3, vou ter que ter 3 normais e 3 Alt Art"*."""

    def test_o_alvo_da_alt_art_sobe_a_3_e_o_master_set_continua_3(self):
        con = self.catalogo()
        a = self.alvos(con)
        self.assertEqual((a["tst-001-100"], a["tst-001a-100"]), (3, 3))
        self.assertEqual(self.metrics.procura_dos_decks(con), {"defy": 3})
        con.close()

    def test_sao_seis_copias_e_a_base_nao_abate_a_falta_da_alt_art(self):
        """Ele tem 3 Defy base na Coleção. O master set está completo (3/3) e
        a Alt Art está a 0/3 — o deck não recebe nenhuma das três bases."""
        con = self.catalogo(defy=3)
        t = self.tile(con, "tst-001-100")
        self.assertEqual((t["qty"], t["target"]), (3, 3))
        t = self.tile(con, "tst-001a-100")
        self.assertEqual((t["qty"], t["target"]), (0, 3))
        self.assertEqual(self.falta_de(con, "azir"), {"defy": 3},
                         "as três bases da Coleção não servem o deck")
        azir = self.idx(con)["azir"]
        self.assertEqual((azir["have"], azir["wanted"], azir["missing"]), (4, 7, 3))
        # O separador Faltas diz o mesmo no bloco Alt Art: faltam 3 de 3.
        b = self.bloco_faltas(con, "alt_art")
        x = next(x for x in b["items"] if x["printing_id"] == "tst-001a-100")
        self.assertEqual((x["have"], x["target"], x["missing"]), (0, 3, 3))
        con.close()

    def test_a_alt_art_na_colecao_serve_o_deck_e_conta_para_o_alvo_dela(self):
        """A mesma cópia da Alt Art é o «1 de cada» e a que o deck joga."""
        con = self.catalogo(defy=3, defy_alt=2)
        self.assertEqual(self.falta_de(con, "azir"), {"defy": 1})
        t = self.tile(con, "tst-001a-100")
        self.assertEqual((t["qty"], t["target"]), (2, 3))
        # A grelha diz que o Azir usa 2 e lhe falta 1.
        uso = self.decks.uso_por_carta(con)["defy"][0]
        self.assertEqual((uso["have"], uso["missing"]), (2, 1))
        con.close()

    def test_o_que_falta_compra_se_na_alt_art(self):
        """O «Falta comprar, por edição», o `+` das encomendas e as abas dos
        decks apontam à arte alternativa — ao preço dela."""
        con = self.catalogo(defy=3)
        deck_id = self.idx(con)["azir"]["id"]
        por_set = self.decks.missing_by_set(con, deck_id)
        item = next(x for d in por_set for x in d["items"] if x["card_key"] == "defy")
        self.assertEqual((item["code"], item["qty"], item["price"], item["alt_art"]),
                         ("TST-001a/100", 3, 2000, True))
        self.assertEqual(self.pending.impressao_para_encomendar(con, ["defy"])["defy"]["id"],
                         "tst-001a-100")
        sf = {x["card_key"]: x for x in self.faltas.shortfall(con)}
        self.assertEqual((sf["defy"]["code"], sf["defy"]["missing"], sf["defy"]["alt_art"]),
                         ("TST-001a/100", 3, True))
        r = self.decks.resumo_das_faltas(con)
        self.assertEqual((r["copies"], r["cents"]), (3, 6000))
        self.assertEqual(r["alt_art"], {"cards": 1, "copies": 3, "cents": 6000})
        con.close()

    def test_uma_base_a_caminho_nao_abate_a_falta_do_deck__uma_alt_art_sim(self):
        con = self.catalogo(defy=0)
        self.pending.add(con, "tst-001-100", 3, source="test")
        self.assertEqual(self.falta_de(con, "azir"), {"defy": 3})
        self.pending.add(con, "tst-001a-100", 2, source="test")
        self.assertEqual(self.falta_de(con, "azir"), {"defy": 1})
        con.close()

    def test_a_proposta_de_marcacao_nunca_tira_a_base_da_colecao(self):
        con = self.catalogo(defy=3, defy_alt=1)
        prop = self.locais.propor_deck(con, "azir")
        self.assertEqual([(x["printing_id"], x["qty"]) for x in prop["items"]
                          if x["card_key"] == "defy"], [("tst-001a-100", 1)])
        con.close()

    def test_sem_a_regra_o_teste_dos_seis_fica_vermelho(self):
        """`decks.jogam_alt_art: false` é 2026-09-11: a base serve o deck e a
        Alt Art fica a 1. É a prova de que o teste acima podia falhar."""
        escrever_config(jogam_alt_art=False)
        self.recarregar()
        con = self.catalogo(defy=3)
        a = self.alvos(con)
        self.assertEqual((a["tst-001-100"], a["tst-001a-100"]), (3, 1))
        self.assertEqual(self.falta_de(con, "azir"), {})
        self.assertEqual(self.metrics.procura_dos_decks(con), {})
        con.close()


class TestMesmaLegend(Base):
    """Regra 3: 3 e 2 dão 3, não 5."""

    def test_dois_decks_com_a_mesma_legend_dao_o_maximo(self):
        con = self.catalogo(decks={"azir": AZIR, "azir-b": AZIR_B})
        self.assertEqual(self.metrics.procura_dos_decks(con), {"defy": 3})
        self.assertEqual(self.alvos(con)["tst-001a-100"], 3)
        con.close()

    def test_duas_legends_diferentes_somam__disputam_as_mesmas_copias(self):
        """A conta da alocação de 2026-09-11: o Ornn compra o que o Azir já
        usa. O alvo da Alt Art diz o mesmo número — 3 + 2."""
        con = self.catalogo(decks={"azir": AZIR, "ornn": ORNN}, defy_alt=3)
        self.assertEqual(self.metrics.procura_dos_decks(con), {"defy": 5})
        self.assertEqual(self.alvos(con)["tst-001a-100"], 5)
        self.assertEqual(self.falta_de(con, "azir"), {})
        self.assertEqual(self.falta_de(con, "ornn"), {"defy": 2, "forge master": 1})
        con.close()


class TestSemAltArtNadaMuda(Base):
    """Regra 4: o Brutalizer não tem arte alternativa — a Coleção serve-o."""

    def test_a_copia_da_colecao_continua_a_servir_o_deck(self):
        con = self.catalogo()
        self.assertNotIn("brutalizer", self.falta_de(con, "azir"))
        azir = self.idx(con)["azir"]
        # 3 Brutalizer + 1 Legend da Coleção; os 3 Defy não.
        self.assertEqual(azir["na_colecao"], 4)
        self.assertEqual(self.alvos(con)["tst-002-100"], 3)
        deck_id = azir["id"]
        p = self.decks.deck_payload(con, deck_id)
        bru = next(c for s in p["sections"] for c in s["cards"] if c["name"] == "Brutalizer")
        self.assertEqual((bru["have"], bru["na_colecao"], bru["missing"]), (3, 3, 0))
        self.assertEqual(bru["order_code"], "TST-002/100")
        con.close()

    def test_a_regra_pode_ignorar_tipos_inteiros(self):
        """`decks.alt_art_ignorar_tipos` — para as runas, se ele não as
        quiser em Alt Art nos decks (pergunta em aberto)."""
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        cfg["decks"]["alt_art_ignorar_tipos"] = ["Unit"]
        CONFIG.write_text(json.dumps(cfg), encoding="utf-8")
        self.recarregar()
        con = self.catalogo(defy=3)
        self.assertEqual(self.decks.cartas_com_alt_art(con), frozenset())
        self.assertEqual(self.falta_de(con, "azir"), {})
        self.assertEqual(self.alvos(con)["tst-001a-100"], 1)
        con.close()


class TestOMasterSetNaoMexe(Base):
    """Regra 6: percentagem, denominador e wantlist iguais com e sem a regra."""

    def medir(self, con) -> tuple:
        niv = self.metrics.niveis_payload(con)
        w = self.a_subir.wantlist(con)
        p = self.metrics.set_payload(con, "TST")["progress"]["master"]
        return ([(n["done"], n["total"], n["missing"]) for n in niv["levels"]],
                (w["copies"], w["cents"], sorted(x["printing_id"] for x in w["items"])),
                (p["done"], p["total"]))

    def test_com_e_sem_a_regra_o_master_set_le_se_igual(self):
        con = self.catalogo(defy=2, defy_alt=1)
        com = self.medir(con)
        con.close()
        escrever_config(jogam_alt_art=False)
        self.recarregar()
        self.v = Vault()
        self.addCleanup(self.v.close)
        con = self.catalogo(defy=2, defy_alt=1)
        sem = self.medir(con)
        con.close()
        self.assertEqual(com, sem)
        # E a wantlist nunca pede a arte alternativa, por muito que o deck a
        # peça (`listas_de_compra.so_master_set`).
        self.assertNotIn("tst-001a-100", com[1][2])
        self.assertIn("tst-001-100", com[1][2])

    def test_a_alt_art_nao_conta_para_a_percentagem_nem_a_6_de_6(self):
        con = self.catalogo(defy=3, defy_alt=3)
        p = self.metrics.set_payload(con, "TST")
        # A percentagem conta a Unit, o Brutalizer e o Legend (não o Forge
        # Master, a zero): 3 de 4 impressões na sequência.
        self.assertEqual((p["progress"]["master"]["done"], p["progress"]["master"]["total"]),
                         (3, 4))
        self.assertFalse(self.metrics.conta_bloco("alt_art"))
        con.close()


if __name__ == "__main__":
    unittest.main()

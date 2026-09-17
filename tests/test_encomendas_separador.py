"""O separador «Encomendas» (André, 2026-09-17).

Palavras dele:
    *"que cries uma aba 'encomendas', em que é igual à coleção, mas só tem de
    Raras para cima, e nas quais eu coloco o que comprei (para não me
    perder), e assim que chegam, eu coloco lá que chegaram, e acrescentas à
    coleção"* / *"e tiras esta funcionalidade dos decks"*.

O que se fixa: a grelha é a da Coleção cortada à raridade da base a partir
de `encomendas.raridade_minima` (tenha ele a carta ou não, mesma ordem,
mesmos blocos); o `+`/`−` grava e tira por impressão; o «Chegou» de uma
impressão dá entrada só dela; encomendar NÃO conta para a Coleção (barra,
níveis, valor, grelha) até chegar; o que vem a caminho fora da grelha é dito;
o site publicado leva a grelha sem controlos; e os tiles dos decks ficaram
sem os botões mas com a informação.

Tudo contra pastas temporárias (`tests.fixture.Vault`) e um config que não
existe: o `data/` e o `riftvault_config.json` a sério nunca são tocados.
"""

from __future__ import annotations

import importlib
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.fixture import REPO, Vault, config_decks_sem_alt_art  # noqa: E402

config_decks_sem_alt_art()

AZIR = "Legend:\n1 Emperor of the Sands\n\nMainDeck:\n3 Defy\n"


def _config(caso, extra: dict) -> None:
    """Um config temporário com o bloco `decks` de hoje mais o que o teste
    quiser. Antes do `Vault`, que é quem recarrega o `config`."""
    caminho = Path(tempfile.gettempdir()) / f"riftvault-enc-{os.getpid()}.json"
    caminho.write_text(json.dumps({
        "decks": {"so_normais_excepto": ["legend", "champion"],
                  "versoes_especiais": ["a", "overnumbered", "promo"]},
        **extra}), encoding="utf-8")
    os.environ["RIFTVAULT_CONFIG"] = str(caminho)
    caso.addCleanup(lambda: os.environ.pop("RIFTVAULT_CONFIG", None))
    # O `Vault` do setUp já recarregou o config com o ficheiro anterior; o
    # caminho é uma constante de módulo e a leitura está em cache.
    from riftvault import config
    importlib.reload(config)
    config.load.cache_clear()


class Base(unittest.TestCase):
    def setUp(self):
        config_decks_sem_alt_art(self)
        self.v = Vault()
        self.addCleanup(self.v.close)
        from riftvault import a_subir, decks, faltas_edicao, metrics, pending, prices
        for m in (metrics, pending, decks, a_subir, faltas_edicao, prices):
            importlib.reload(m)
        self.metrics, self.pending, self.decks = metrics, pending, decks
        self.a_subir, self.faltas_edicao, self.prices = a_subir, faltas_edicao, prices

    def catalogo(self):
        """Uma edição com as quatro raridades, uma alt art de uma rara e uma
        sobrenumerada showcase; ele tem 1 Defy e as 3 Brutalizer."""
        from riftvault import collection
        con = self.v.connect()
        v = self.v
        v.add_printing(con, "tst-001-100", "TST", 1, "Defy", rarity="rare", size=100)
        v.add_printing(con, "tst-001a-100", "TST", 1, "Defy", variant="a", kind="alt_art",
                       rarity="showcase", base_rarity="rare", size=100)
        v.add_printing(con, "tst-002-100", "TST", 2, "Brutalizer", rarity="common", size=100)
        v.add_printing(con, "tst-003-100", "TST", 3, "Emperor of the Sands",
                       card_type="Legend", rarity="epic", size=100)
        v.add_printing(con, "tst-004-100", "TST", 4, "Salvage", rarity="uncommon", size=100)
        v.add_printing(con, "tst-101-100", "TST", 101, "Emperor of the Sands",
                       card_type="Legend", rarity="showcase", size=100)
        v.rebuild(con)
        for pid, cents in (("tst-001-100", 150), ("tst-001a-100", 2000),
                           ("tst-002-100", 11), ("tst-003-100", 1000),
                           ("tst-004-100", 20), ("tst-101-100", 8000)):
            con.execute("INSERT INTO catalog.price_latest (printing_id, price_cents) "
                        "VALUES (?,?)", (pid, cents))
        collection.adjust(con, "tst-001-100", 1, source="test")
        collection.adjust(con, "tst-002-100", 3, source="test")
        v.write_deck("azir", AZIR)
        self.decks.import_all(con, log=lambda *_: None)
        return con

    def grelha(self, con, **kw):
        return self.pending.grelha(con, "TST", **kw)

    @staticmethod
    def ids(g):
        return [p["id"] for grupo in g["groups"] for p in grupo["printings"]]


# ---------------------------------------------------------------------------


class TestCorte(Base):
    """«Igual à coleção, mas só de Raras para cima»."""

    def test_e_a_grelha_da_colecao_cortada_a_rara_para_cima(self):
        con = self.catalogo()
        g = self.grelha(con)
        # A rara (e a alt art dela, que é do mesmo grupo), a mítica e a
        # showcase sobrenumerada; a comum e a incomum ficam de fora — TENHA
        # ele a carta ou não (as Brutalizer completas são comuns e não entram;
        # a Defy incompleta é rara e entra).
        self.assertEqual(self.ids(g), ["tst-001-100", "tst-001a-100", "tst-003-100",
                                       "tst-101-100"])
        self.assertEqual(g["rarity_min"], "rare")
        self.assertEqual(g["rarities"], ["rare", "epic", "showcase"])
        self.assertEqual(g["totals"], {"cards": 3, "printings": 4, "ordered": 0,
                                       "ordered_printings": 0, "printings_colecao": 6})
        con.close()

    def test_a_mesma_ordem_e_os_mesmos_blocos_da_colecao(self):
        con = self.catalogo()
        col = self.metrics.set_payload(con, "TST")
        g = self.grelha(con)
        ordem_col = [pid for _, pid in self.metrics.ordem_da_grelha(col)]
        ordem_enc = [pid for _, pid in self.metrics.ordem_da_grelha(g)]
        self.assertEqual(ordem_enc, [pid for pid in ordem_col if pid in set(ordem_enc)],
                         "a ordem é a da Coleção, só com menos tiles")
        self.assertEqual([b["id"] for b in g["blocks"]],
                         [b["id"] for b in col["blocks"] if b["id"] in {"master", "alt_art",
                                                                        "overnumbered"}])
        # E cada tile traz o que o tile da Coleção traz: o `qty` é o da
        # Coleção, o alvo, o bloco, o preço, a imagem.
        col_p = {p["id"]: p for gr in col["groups"] for p in gr["printings"]}
        for gr in g["groups"]:
            for p in gr["printings"]:
                for k in ("qty", "target", "block", "price", "img", "code", "label"):
                    self.assertEqual(p[k], col_p[p["id"]][k], (p["id"], k))
        con.close()

    def test_a_raridade_e_a_da_base_nao_a_da_impressao(self):
        """A alt art da Defy é `showcase` impressa, mas a carta é rara: entra
        pela base, e com `raridade_minima: epic` sai com ela."""
        _config(self, {"encomendas": {"raridade_minima": "epic"}})
        con = self.catalogo()
        g = self.grelha(con)
        self.assertEqual(self.ids(g), ["tst-003-100", "tst-101-100"])
        self.assertEqual(g["rarities"], ["epic", "showcase"])
        con.close()

    def test_a_raridade_minima_vem_do_config(self):
        _config(self, {"encomendas": {"raridade_minima": "common"}})
        con = self.catalogo()
        self.assertEqual(len(self.ids(self.grelha(con))), 6, "com 'common' é a Coleção inteira")
        con.close()

    def test_uma_raridade_desconhecida_rebenta(self):
        _config(self, {"encomendas": {"raridade_minima": "mythic"}})
        con = self.catalogo()
        with self.assertRaises(ValueError):
            self.grelha(con)
        con.close()


class TestMaisMenosChegou(Base):
    """Os controlos são POR IMPRESSÃO: ele escolhe a versão que comprou."""

    def test_o_mais_grava_na_impressao_do_tile(self):
        con = self.catalogo()
        self.pending.encomendar(con, printing_id="tst-001a-100", qty=2, source="test")
        por_id = {p["id"]: p for gr in self.grelha(con)["groups"] for p in gr["printings"]}
        self.assertEqual(por_id["tst-001a-100"]["ordered"], 2)
        self.assertEqual(por_id["tst-001-100"]["ordered"], 0, "a base não leva a encomenda da alt art")
        g = self.grelha(con)
        self.assertEqual((g["totals"]["ordered"], g["totals"]["ordered_printings"]), (2, 1))
        bloco = {b["id"]: b for b in g["blocks"]}
        self.assertEqual((bloco["alt_art"]["ordered"], bloco["master"]["ordered"]), (2, 0))
        con.close()

    def test_o_menos_tira_so_dessa_impressao_e_nunca_abaixo_de_zero(self):
        con = self.catalogo()
        self.pending.encomendar(con, printing_id="tst-001-100", qty=1, source="test")
        self.pending.encomendar(con, printing_id="tst-001a-100", qty=1, source="test")
        with self.assertRaises(self.pending.SemEncomenda):
            self.pending.anular(con, printing_id="tst-003-100", qty=1, source="test")
        res = self.pending.anular(con, printing_id="tst-001a-100", qty=5, source="test")
        self.assertEqual((res["removed"], res["open_printing"]), (1, 0))
        self.assertEqual(self.pending.open_qty(con), {"tst-001-100": 1})
        con.close()

    def test_chegou_de_uma_impressao_da_entrada_so_dela(self):
        from riftvault import locais
        con = self.catalogo()
        self.pending.encomendar(con, printing_id="tst-001-100", qty=2, source="test")
        self.pending.encomendar(con, printing_id="tst-001a-100", qty=1, source="test")
        feitas = self.pending.arrive(con, printing_id="tst-001-100", source="test")
        self.assertEqual([(f["printing_id"], f["qty"], f["total"]) for f in feitas],
                         [("tst-001-100", 2, 3)])
        self.assertEqual(self.pending.open_qty(con), {"tst-001a-100": 1}, "a alt art continua a caminho")
        self.assertEqual(locais.na_colecao(con)["tst-001-100"], 3, "entrou na Coleção")
        por_id = {p["id"]: p for gr in self.grelha(con)["groups"] for p in gr["printings"]}
        self.assertEqual((por_id["tst-001-100"]["qty"], por_id["tst-001-100"]["ordered"]), (3, 0))
        # Segunda vez: nada, e não soma outra vez.
        self.assertEqual(self.pending.arrive(con, printing_id="tst-001-100", source="test"), [])
        self.assertEqual(locais.na_colecao(con)["tst-001-100"], 3)
        con.close()

    def test_o_que_vem_a_caminho_fora_da_grelha_e_dito(self):
        """Uma comum encomendada pela CLI não aparece nos tiles — mas não
        pode desaparecer: vai no `fora`, e o «Chegou tudo» dá-lhe entrada."""
        from riftvault import locais
        con = self.catalogo()
        self.pending.add(con, "tst-002-100", 2, source="test")
        self.pending.add(con, "tst-002-100", 1, source="test")
        self.pending.encomendar(con, printing_id="tst-001-100", qty=1, source="test")
        g = self.grelha(con)
        self.assertEqual(g["totals"]["ordered"], 1, "só o que está na grelha")
        self.assertEqual(g["fora"], [{"printing_id": "tst-002-100", "name": "Brutalizer",
                                      "code": "TST-002/100", "label": "base",
                                      "market_only": False, "qty": 3}])
        self.pending.arrive(con, source="test")
        self.assertEqual(self.grelha(con)["fora"], [])
        self.assertEqual(locais.na_colecao(con)["tst-002-100"], 6)
        con.close()


class TestEncomendarNaoETer(Base):
    """A prova pedida: encomendar não conta para a coleção até chegar."""

    def test_nada_mexe_ate_ao_chegou(self):
        con = self.catalogo()

        def foto():
            p = self.metrics.set_payload(con, "TST")
            niv = self.metrics.niveis_payload(con)
            wl = self.a_subir.wantlist(con)
            fe = self.faltas_edicao.payload(con)
            return {
                "grelha_qty": {pr["id"]: pr["qty"] for g in p["groups"] for pr in g["printings"]},
                "master": p["progress"]["master"],
                "valor": p["progress"]["value"]["owned"],
                "niveis": [(l["done"], l["total"], l["missing"]) for l in niv["levels"]],
                "denominador": niv["levels"][0]["total"],
                "wantlist": (wl["lines"], wl["copies"], wl["cents"]),
                # O separador Faltas conta o que há a COMPRAR e diz o que vem
                # a caminho à parte (2026-09-15) — é lista de compra, desconta.
                "faltas_a_caminho": fe["totals"]["pending_copies"],
                "faltas_a_comprar": (fe["totals_lists"]["copies"], fe["totals_lists"]["cents"]),
                "decks": self.decks.resumo_das_faltas(con)["copies"],
            }

        antes = foto()
        self.assertEqual(antes["grelha_qty"]["tst-001-100"], 1)
        self.assertEqual(antes["wantlist"][1], 2 + 1 + 3, "2 Defy + o Legend + 3 Salvage")
        self.assertEqual(antes["decks"], 3, "o azir pede 3 Defy e tem 1, e a Legend")
        self.pending.encomendar(con, printing_id="tst-001-100", qty=2, source="test")
        self.pending.encomendar(con, printing_id="tst-003-100", qty=1, source="test")
        durante = foto()
        # O que MEDE a coleção não mexe: grelha, barra, valor, níveis,
        # denominador.
        for k in ("grelha_qty", "master", "valor", "niveis", "denominador"):
            self.assertEqual(durante[k], antes[k], f"{k} mexeu com uma encomenda")
        # O que é LISTA DE COMPRA desconta o que vem a caminho: fica a Salvage.
        self.assertEqual(durante["wantlist"][1], 3)
        self.assertEqual(durante["faltas_a_comprar"], (3, 3 * 20))
        self.assertEqual((antes["faltas_a_caminho"], durante["faltas_a_caminho"]), (0, 3))
        # Aos decks só as 2 Defy abatem: a Legend joga a versão ESPECIAL
        # (2026-09-17) e a que vem a caminho é a base — fica 1 a comprar.
        self.assertEqual(durante["decks"], 1)
        # Chegou: aí sim, tudo entra.
        self.pending.arrive(con, source="test")
        depois = foto()
        self.assertEqual(depois["grelha_qty"]["tst-001-100"], 3)
        self.assertEqual(depois["master"]["done"], antes["master"]["done"] + 2)
        self.assertEqual(depois["valor"], antes["valor"] + 2 * 150 + 1000)
        self.assertEqual(depois["wantlist"][1], 3)
        self.assertEqual(depois["denominador"], antes["denominador"])
        con.close()

    def test_a_grelha_nao_escreve(self):
        con = self.catalogo()
        self.pending.encomendar(con, printing_id="tst-001-100", qty=1, source="test")
        antes = (con.execute("SELECT * FROM copies ORDER BY printing_id").fetchall(),
                 con.execute("SELECT * FROM pending ORDER BY id").fetchall(),
                 con.execute("SELECT COUNT(*) FROM ops").fetchone()[0])
        self.grelha(con)
        self.grelha(con, editable=False, image_mode="remote")
        depois = (con.execute("SELECT * FROM copies ORDER BY printing_id").fetchall(),
                  con.execute("SELECT * FROM pending ORDER BY id").fetchall(),
                  con.execute("SELECT COUNT(*) FROM ops").fetchone()[0])
        self.assertEqual([tuple(r) for r in antes[0]], [tuple(r) for r in depois[0]])
        self.assertEqual([tuple(r) for r in antes[1]], [tuple(r) for r in depois[1]])
        self.assertEqual(antes[2], depois[2])
        con.close()


class TestRotasEBuild(Base):
    """O servidor responde, o site publicado leva a grelha sem controlos."""

    def test_as_rotas(self):
        from riftvault import server
        con = self.catalogo()
        con.close()
        app = server.app
        app.testing = True
        with app.test_client() as c:
            g = c.get("/api/encomendas/tst.json").get_json()
            self.assertTrue(g["editable"])
            self.assertEqual(g["totals"]["printings"], 4)
            # O `+` do tile manda a impressão.
            r = c.post("/api/encomenda", json={"printing_id": "tst-001a-100", "delta": 2})
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.get_json()["open_printing"], 2)
            r = c.post("/api/encomenda", json={"printing_id": "tst-001a-100", "delta": -1})
            self.assertEqual(r.get_json()["open_printing"], 1)
            r = c.post("/api/encomenda", json={"printing_id": "tst-003-100", "delta": -1})
            self.assertEqual(r.status_code, 400, "sem nada a caminho, não vai abaixo de zero")
            # O «Chegou» do tile manda a impressão; a segunda vez é 404.
            r = c.post("/api/pending/arrive", json={"printing_id": "tst-001a-100"})
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.get_json()["arrived"][0]["qty"], 1)
            self.assertEqual(c.post("/api/pending/arrive",
                                    json={"printing_id": "tst-001a-100"}).status_code, 404)
            self.assertEqual(c.post("/api/pending/arrive",
                                    json={"printing_id": "nao-existe"}).status_code, 404)
            g = c.get("/api/encomendas/TST.json").get_json()
            por_id = {p["id"]: p for gr in g["groups"] for p in gr["printings"]}
            self.assertEqual((por_id["tst-001a-100"]["qty"], por_id["tst-001a-100"]["ordered"]), (1, 0))
            # A lista antiga continua a responder (a CLI lê-a).
            self.assertEqual(c.get("/api/encomendas.json").get_json()["totals"]["copies"], 0)

    def test_o_build_gera_a_grelha_por_edicao_sem_controlos(self):
        from riftvault import build
        con = self.catalogo()
        self.pending.encomendar(con, printing_id="tst-001-100", qty=1, source="test")
        con.close()
        out = self.v.root / "site"
        build.build(out, log=lambda *_: None)
        f = out / "api" / "encomendas" / "TST.json"
        self.assertTrue(f.exists(), "falta api/encomendas/TST.json no site")
        g = json.loads(f.read_text(encoding="utf-8"))
        self.assertFalse(g["editable"], "o site publicado não pode trazer os +/- ligados")
        self.assertEqual(g["totals"]["ordered"], 1, "mas mostra o que vem a caminho")
        self.assertTrue((out / "api" / "encomendas.json").exists())


class TestFrontend(unittest.TestCase):
    """O `index.html`/`app.js`: o separador existe, os decks ficaram sem os
    controlos mas com a informação."""

    def setUp(self):
        self.js = (REPO / "riftvault" / "web" / "app.js").read_text(encoding="utf-8")
        self.html = (REPO / "riftvault" / "web" / "index.html").read_text(encoding="utf-8")

    def test_o_separador_existe_e_pede_a_grelha_por_edicao(self):
        self.assertIn('data-section="encomendas"', self.html)
        self.assertIn('id="encomendas"', self.html)
        self.assertRegex(self.js, r"SECCOES = \[[^\]]*'encomendas'")
        self.assertIn("api/encomendas/${", self.js)
        self.assertIn("'api/encomendas.json'", self.js)

    def test_os_tiles_dos_decks_ficaram_sem_os_controlos(self):
        m = re.search(r"function deckTile\(c\) \{(.*?)\n\}\n", self.js, re.S)
        corpo = m.group(1)
        self.assertNotIn("data-enc=", corpo, "o +/- da encomenda ainda está no tile do deck")
        self.assertNotIn("data-chegou", corpo, "o «Chegou» ainda está no tile do deck")
        self.assertIn("a caminho", corpo, "a informação «N a caminho» tem de ficar")
        # E não há nenhum «Chegou» nem `+`/`−` de encomenda a escrever no #deck-body.
        self.assertNotRegex(self.js, r"#deck-body[^\n]*data-chegou")
        self.assertNotRegex(self.js, r"#deck-body[^\n]*steppers\.enc")

    def test_o_separador_decks_ja_nao_tem_a_aba_encomendas(self):
        self.assertNotIn("state.deckId === 'encomendas'", self.js)
        self.assertNotIn("state.prefs.deck === 'encomendas'", self.js)


if __name__ == "__main__":
    unittest.main()

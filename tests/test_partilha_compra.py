"""Os decks partilham a Coleção; o que dois decks disputam compra-se (2026-09-11).

Palavras do André:
    *"Os decks podem usar cartas da coleção. Na coleção indica onde as cartas
    estão a ser usadas. Os decks que precisem de cartas iguais, caso não haja
    suficientes na coleção, ficam em falta e é necessário comprar!"*
    *"se há na coleção o deck usa; caso algum deck ou decks já estão a usar as
    cartas disponíveis na coleção, o próximo passa a marcar como faltas para
    comprar"*

Tudo contra pastas temporárias (`tests.fixture.Vault`) e um config que não
existe: o `data/` e o `riftvault_config.json` a sério nunca são tocados.
"""

from __future__ import annotations

import contextlib
import importlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Antes do `Vault`, que é quem recarrega o `config` com as variáveis postas.
os.environ["RIFTVAULT_CONFIG"] = str(Path(tempfile.gettempdir()) / "riftvault-nao-existe.json")

from tests.fixture import Vault  # noqa: E402

AZIR = "Legend:\n1 Emperor of the Sands\n\nMainDeck:\n3 Defy\n3 Brutalizer\n"
# O mesmo Legend, outro Champion, para os rótulos saírem diferentes.
ORNN = ("Legend:\n1 Emperor of the Sands\n\nChampion:\n1 Spirit Blade\n\n"
        "MainDeck:\n2 Defy\n")


class Base(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.close)
        from riftvault import decks, faltas, locais, metrics, venda
        for m in (metrics, locais, decks, faltas, venda):
            importlib.reload(m)
        self.decks, self.faltas, self.locais = decks, faltas, locais
        self.metrics, self.venda = metrics, venda

    def catalogo(self, defy: int = 3, precos: bool = True):
        """Uma edição pequena com `defy` cópias de Defy na Coleção."""
        from riftvault import collection
        con = self.v.connect()
        self.v.add_printing(con, "tst-001-100", "TST", 1, "Defy", size=100)
        self.v.add_printing(con, "tst-001a-100", "TST", 1, "Defy",
                            variant="a", kind="alt_art", size=100)
        self.v.add_printing(con, "tst-002-100", "TST", 2, "Brutalizer", size=100)
        self.v.add_printing(con, "tst-003-100", "TST", 3, "Emperor of the Sands",
                            card_type="Legend", size=100)
        self.v.add_printing(con, "tst-004-100", "TST", 4, "Spirit Blade", size=100)
        self.v.rebuild(con)
        if precos:
            for pid, cents in (("tst-001-100", 150), ("tst-001a-100", 2000),
                               ("tst-002-100", 50), ("tst-003-100", 1000),
                               ("tst-004-100", 700)):
                con.execute("INSERT INTO catalog.price_latest (printing_id, price_cents) "
                            "VALUES (?,?)", (pid, cents))
        for pid, n in (("tst-001-100", defy), ("tst-002-100", 3), ("tst-003-100", 1)):
            if n:
                collection.adjust(con, pid, n, source="test")
        self.v.write_deck("azir", AZIR)
        self.v.write_deck("ornn", ORNN)
        self.decks.import_all(con, log=lambda *_: None)
        return con

    def idx(self, con) -> dict:
        return {d["slug"]: d for d in self.decks.decks_index(con)}

    def carta(self, con, slug: str, nome: str) -> dict:
        deck_id = self.idx(con)[slug]["id"]
        p = self.decks.deck_payload(con, deck_id)
        return next(c for s in p["sections"] for c in s["cards"] if c["name"] == nome)


# ---------------------------------------------------------------------------


class TestColecaoConta(Base):
    """«Se há na coleção o deck usa.»"""

    def test_o_deck_monta_se_com_a_colecao(self):
        con = self.catalogo()
        azir = self.idx(con)["azir"]
        self.assertEqual((azir["have"], azir["wanted"]), (7, 7))
        self.assertEqual(azir["na_colecao"], 7, "as 7 vêm da Coleção")
        self.assertEqual(azir["missing"], 0)
        con.close()

    def test_a_carta_diz_de_onde_vem(self):
        con = self.catalogo()
        defy = self.carta(con, "azir", "Defy")
        self.assertEqual(defy["have"], 3)
        self.assertEqual(defy["na_colecao"], 3)
        self.assertEqual((defy["no_deck"], defy["no_binder"]), (0, 0))
        con.close()

    def test_marcar_o_local_e_informacao__nao_desconta(self):
        """Mover a cópia para o deck ou para o binder muda só de onde vem."""
        con = self.catalogo()
        self.locais.mover(con, "tst-001-100", 2, self.locais.COLECAO,
                          self.locais.deck_local("azir"), source="test")
        self.locais.mover(con, "tst-002-100", 1, self.locais.COLECAO,
                          self.locais.BINDER, source="test")
        azir = self.idx(con)["azir"]
        self.assertEqual(azir["have"], 7, "tem o mesmo")
        self.assertEqual(azir["missing"], 0)
        self.assertEqual((azir["no_deck"], azir["no_binder"], azir["na_colecao"]),
                         (2, 1, 4))
        con.close()

    def test_a_colecao_continua_a_contar_para_o_master_set(self):
        """A mesma cópia serve a barra e o deck: a percentagem não desce."""
        con = self.catalogo()
        antes = self.metrics.set_payload(con, "TST")["progress"]["master"]
        self.assertEqual(antes["done"], 3)      # Defy 3/3, Brutalizer 3/3, Legend 1/1
        self.assertEqual(self.idx(con)["azir"]["have"], 7)
        con.close()


class TestDisputaCompraSe(Base):
    """«Caso algum deck já esteja a usar as cartas, o próximo marca falta.»"""

    def test_com_colecao_insuficiente_o_de_baixo_compra(self):
        con = self.catalogo(defy=3)       # o azir pede 3, o ornn pede 2
        idx = self.idx(con)
        self.assertEqual(idx["azir"]["missing"], 0)
        # O ornn não recebe Defy nenhuma (o azir levou as 3) nem o Legend (o
        # azir levou o único), e não tem a Spirit Blade: 4 a comprar, das quais
        # 3 disputadas com o azir.
        self.assertEqual(idx["ornn"]["missing"], 4)
        self.assertEqual(idx["ornn"]["shared"], 3)
        defy = self.carta(con, "ornn", "Defy")
        self.assertEqual((defy["have"], defy["missing"]), (0, 2))
        self.assertEqual([(h["slug"], h["qty"]) for h in defy["shared"]["em"]],
                         [("azir", 3)], "e diz onde estão")
        con.close()

    def test_a_falta_disputada_tem_euros(self):
        con = self.catalogo(defy=3)
        p = self.decks.deck_payload(con, self.idx(con)["ornn"]["id"])
        por_set = {m["set"]: m for m in p["missing_by_set"]}
        self.assertEqual(por_set["TST"]["copies"], 4)
        # 2 Defy a 1,50 € + 1 Legend a 10,00 € + 1 Spirit Blade a 7,00 €.
        self.assertEqual(por_set["TST"]["cents"], 2 * 150 + 1000 + 700)
        lista = {x["name"]: x for x in self.decks.shopping_list(con)}
        self.assertEqual(lista["Defy"]["qty"], 2)
        self.assertEqual(lista["Defy"]["total_cents"], 300)
        tot = self.decks.resumo_das_faltas(con)
        self.assertEqual((tot["copies"], tot["cents"], tot["disputed"]),
                         (4, 2000, 3))
        con.close()

    def test_com_colecao_suficiente_ninguem_compra(self):
        con = self.catalogo(defy=5)
        idx = self.idx(con)
        self.assertEqual(idx["azir"]["missing"], 0)
        defy = self.carta(con, "ornn", "Defy")
        self.assertEqual((defy["have"], defy["missing"]), (2, 0))
        self.assertIsNone(defy["shared"])
        # Ficam o Legend (só há 1, e o azir levou-o) e a Spirit Blade.
        self.assertEqual(idx["ornn"]["missing"], 2)
        self.assertEqual(idx["ornn"]["shared"], 1)
        con.close()

    def test_a_disputa_parcial_compra_so_o_que_falta(self):
        con = self.catalogo(defy=4)       # o azir leva 3, sobra 1 para o ornn
        defy = self.carta(con, "ornn", "Defy")
        self.assertEqual((defy["have"], defy["missing"]), (1, 1))
        self.assertEqual(defy["shared"]["qty"], 1)
        con.close()

    def test_a_prioridade_decide_quem_compra(self):
        con = self.catalogo(defy=3)
        rows = {r["name"]: r["deck_id"] for r in self.decks.deck_rows(con)}
        self.decks.set_order(con, [rows["ornn"], rows["azir"]])
        idx = self.idx(con)
        self.assertEqual(self.carta(con, "ornn", "Defy")["missing"], 0)
        self.assertEqual(self.carta(con, "azir", "Defy")["missing"], 2)
        self.assertEqual(idx["azir"]["shared"], 3, "2 Defy + o Legend, agora no ornn")
        self.assertEqual(idx["ornn"]["missing"], 1, "a Spirit Blade")
        con.close()

    def test_o_sideboard_conta_na_procura_como_o_main(self):
        """Regra do sideboard, fixada: soma-se à procura da carta lógica e
        disputa o mesmo stock que o main — não é uma cópia à parte."""
        con = self.catalogo(defy=3)
        self.v.write_deck("azir", AZIR + "\nSideboard:\n1 Defy\n")
        self.decks.import_all(con, log=lambda *_: None)
        defy = [c for s in self.decks.deck_payload(con, self.idx(con)["azir"]["id"])
                ["sections"] for c in s["cards"] if c["name"] == "Defy"]
        self.assertEqual([(c["wanted"], c["have"], c["missing"]) for c in defy],
                         [(3, 3, 0), (1, 0, 1)], "o main serve-se primeiro")
        self.assertEqual(self.idx(con)["azir"]["missing"], 1)
        con.close()


class TestSeccaoFaltas(Base):
    """As abas dos decks dão a mesma soma que a secção Decks."""

    def test_por_deck_e_o_missing_da_alocacao(self):
        con = self.catalogo(defy=3)
        por_deck = {d["name"]: d for d in self.faltas.por_deck(con)}
        idx = self.idx(con)
        for slug in ("azir", "ornn"):
            self.assertEqual(por_deck[idx[slug]["name"]]["copies"], idx[slug]["missing"])
        tj = self.faltas.todos_juntos(con)
        self.assertEqual(tj["copies"], sum(d["copies"] for d in por_deck.values()))
        self.assertEqual(tj["cents"], sum(d["cents"] for d in por_deck.values()))
        con.close()

    def test_sem_teto__o_que_dois_decks_disputam_e_carencia(self):
        """Até 2026-09-11 havia o teto do playset (3 Defy no total). Agora a
        carência é a soma: 5 pedidas, 3 na Coleção, 2 a comprar."""
        con = self.catalogo(defy=3)
        falta = {x["name"]: x for x in self.faltas.shortfall(con)}
        self.assertEqual(falta["Defy"]["wanted"], 5)
        self.assertEqual(falta["Defy"]["missing"], 2)
        self.assertEqual(falta["Defy"]["n_decks"], 2)
        self.assertIn("Defy", {x["name"] for x in self.faltas.staples(con)})
        con.close()

    def test_o_que_vem_a_caminho_conta_como_tido(self):
        from riftvault import pending
        con = self.catalogo(defy=3)
        pending.add(con, "tst-001-100", 2)
        por_deck = {d["name"]: d for d in self.faltas.por_deck(con)}
        ornn = por_deck[self.idx(con)["ornn"]["name"]]
        self.assertEqual(ornn["copies"], 2, "o Legend e a Spirit Blade; as Defy vêm a caminho")
        self.assertNotIn("Defy", [it["name"] for g in ornn["by_set"] for it in g["items"]])
        con.close()


class TestColecaoDizOndeEUsada(Base):
    """«Na coleção indica onde as cartas estão a ser usadas.»"""

    def test_o_grupo_lista_os_decks_por_prioridade(self):
        con = self.catalogo(defy=3)
        grupos = {g["card_key"]: g for g in self.metrics.set_payload(con, "TST")["groups"]}
        uso = grupos["defy"]["decks"]
        self.assertEqual([(u["slug"], u["wanted"], u["have"], u["missing"]) for u in uso],
                         [("azir", 3, 3, 0), ("ornn", 2, 0, 2)])
        self.assertEqual(grupos["spirit blade"]["decks"],
                         [{"deck": uso[1]["deck"], "slug": "ornn", "priority": 2,
                           "wanted": 1, "have": 0, "ordered": 0, "missing": 1}])
        self.assertEqual(grupos["brutalizer"]["decks"][0]["slug"], "azir")
        con.close()

    def test_sem_decks_nao_ha_uso(self):
        con = self.catalogo()
        for p in (self.v.decks_dir / "azir.txt", self.v.decks_dir / "ornn.txt"):
            p.unlink()
        self.decks.import_all(con, log=lambda *_: None)
        grupos = self.metrics.set_payload(con, "TST")["groups"]
        self.assertTrue(all(g["decks"] == [] for g in grupos))
        con.close()

    def test_o_stats_lista_as_usadas(self):
        from riftvault import cli
        self.catalogo(defy=3).close()
        importlib.reload(cli)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cli.main(["stats", "--usadas"])
        self.assertEqual(code, 0)
        texto = out.getvalue()
        self.assertIn("Decks: falta comprar 4 cópias de 3 cartas · 20.00 €", texto)
        self.assertIn("3 disputadas", texto)
        self.assertRegex(texto, r"Defy\s+3\s+Emperor of the Sands 3 · Emperor of the Sands 2 \(faltam 2\)")


class TestVendaNaoVendeDisputadas(Base):
    """O excedente é cópias − max(usadas nos decks, alvo) — usadas é a SOMA."""

    def test_uma_copia_que_dois_decks_disputam_nao_se_vende(self):
        # 4 Defy na Coleção, alvo 3: sem decks, sobrava 1. Com o azir a levar 3
        # e o ornn 1, as 4 estão em uso — nada sobra. Com o MÁXIMO das procuras
        # (3) em vez da soma (4), a quarta ia à venda: é isso que se fixa.
        con = self.catalogo(defy=4)
        largo = {x["printing_id"]: x for x in self.venda.excedente(con, incluir_master=True)}
        defy = largo["tst-001-100"]
        self.assertEqual(defy["used"], 4)
        self.assertEqual(defy["from_colecao"], 0)
        self.assertEqual(defy["qty"], 0)
        con.close()

    def test_acima_do_que_os_decks_usam_e_do_alvo_sobra(self):
        con = self.catalogo(defy=6)       # alvo 3, usadas 5 -> sobra 1
        largo = {x["printing_id"]: x for x in self.venda.excedente(con, incluir_master=True)}
        self.assertEqual(largo["tst-001-100"]["used"], 5)
        self.assertEqual(largo["tst-001-100"]["qty"], 1)
        con.close()

    def test_a_alt_art_na_colecao_que_um_deck_joga_nao_se_vende(self):
        """Só tem a arte alternativa: o deck joga com ela e ela não sobra."""
        from riftvault import collection
        con = self.catalogo(defy=0)
        # O azir pede 3 e o ornn 2: as 5 estão em uso, e o alvo da alt art é 1.
        collection.adjust(con, "tst-001a-100", 5, source="test")
        v = self.venda.listar(con)
        self.assertEqual([x["printing_id"] for x in v["items"]], [])
        self.assertEqual(v["in_decks_copies"], 5)
        # Uma sexta cópia já sobra: max(5 usadas, 1 alvo) = 5.
        collection.adjust(con, "tst-001a-100", 1, source="test")
        v = self.venda.listar(con)
        self.assertEqual([(x["printing_id"], x["qty"]) for x in v["items"]],
                         [("tst-001a-100", 1)])
        con.close()

    def test_a_sequencia_que_os_decks_jogam_nao_e_listada_como_dentro_de_um_deck(self):
        """A lista «em uso nos decks» da Venda não repete a sequência inteira."""
        con = self.catalogo(defy=3)
        v = self.venda.listar(con)
        self.assertEqual(v["kept"], [])
        con.close()

    def test_nao_mexe_na_base(self):
        con = self.catalogo(defy=4)
        antes = con.execute("SELECT printing_id, qty FROM copies ORDER BY 1").fetchall()
        self.venda.excedente(con, incluir_master=True)
        self.decks.allocate(con)
        depois = con.execute("SELECT printing_id, qty FROM copies ORDER BY 1").fetchall()
        self.assertEqual([tuple(r) for r in antes], [tuple(r) for r in depois])
        self.assertEqual(con.execute("SELECT COUNT(*) FROM copy_locations").fetchone()[0], 0)
        con.close()


if __name__ == "__main__":
    unittest.main()

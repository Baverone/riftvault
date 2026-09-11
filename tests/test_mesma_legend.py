"""Decks com a MESMA Legend partilham cartas — não disputam (2026-09-11, noite).

Palavras do André:
    *"deck com o mesmo Legend, partilham cartas. Os 2 decks de LeBlanc
    partilham as mesmas cartas, são só 2 listas diferentes em algumas cartas.
    Então o que encomendar para 1 deck, estou a encomendar para o outro
    também."*

A regra: decks com a mesma Legend são variantes do mesmo deck físico. Formam
um grupo; a procura do grupo é o MÁXIMO por carta entre as listas; o grupo
serve-se da Coleção como um deck só; o que lhe falta é falta dos dois e conta
UMA vez no total. Entre grupos diferentes mantém-se a regra da tarde: soma,
disputa, o de baixo compra.

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

# Dois LeBlanc: a mesma Legend, listas diferentes em algumas cartas.
LEBLANC = ("Legend:\n1 Deceiver\n\nMainDeck:\n3 Hidden Blade\n3 Defy\n")
BAITED = ("Nome: LeBlanc Baited Hook\n\nLegend:\n1 Deceiver\n\n"
          "MainDeck:\n2 Hidden Blade\n3 Baited Hook\n")
# Outra Legend: disputa com o grupo LeBlanc como sempre.
ORNN = ("Legend:\n1 Forge Master\n\nMainDeck:\n3 Defy\n")


class Base(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.close)
        from riftvault import decks, faltas, locais, metrics, pending, venda
        for m in (metrics, locais, decks, faltas, pending, venda):
            importlib.reload(m)
        self.decks, self.faltas, self.locais = decks, faltas, locais
        self.metrics, self.pending, self.venda = metrics, pending, venda

    def catalogo(self, hidden: int = 2, defy: int = 3, ornn: bool = False):
        from riftvault import collection
        con = self.v.connect()
        self.v.add_printing(con, "tst-001-100", "TST", 1, "Hidden Blade", size=100)
        self.v.add_printing(con, "tst-002-100", "TST", 2, "Defy", size=100)
        self.v.add_printing(con, "tst-003-100", "TST", 3, "Baited Hook", size=100)
        self.v.add_printing(con, "tst-004-100", "TST", 4, "Deceiver",
                            card_type="Legend", size=100)
        self.v.add_printing(con, "tst-005-100", "TST", 5, "Forge Master",
                            card_type="Legend", size=100)
        self.v.rebuild(con)
        for pid, cents in (("tst-001-100", 200), ("tst-002-100", 150),
                           ("tst-003-100", 400), ("tst-004-100", 1000),
                           ("tst-005-100", 1000)):
            con.execute("INSERT INTO catalog.price_latest (printing_id, price_cents) "
                        "VALUES (?,?)", (pid, cents))
        for pid, n in (("tst-001-100", hidden), ("tst-002-100", defy),
                       ("tst-004-100", 1)):
            if n:
                collection.adjust(con, pid, n, source="test")
        self.v.write_deck("leblanc", LEBLANC)
        self.v.write_deck("leblanc-baited-hook", BAITED)
        if ornn:
            self.v.write_deck("ornn", ORNN)
        self.decks.import_all(con, log=lambda *_: None)
        # O `import_all` numera pela ordem dos ficheiros («leblanc-baited-hook»
        # vem antes de «leblanc»); aqui o LeBlanc é o principal, como no real.
        ids = {r["name"]: r["deck_id"] for r in self.decks.deck_rows(con)}
        self.decks.set_order(con, [ids[s] for s in ("leblanc", "leblanc-baited-hook", "ornn")
                                   if s in ids])
        return con

    def idx(self, con) -> dict:
        return {d["slug"]: d for d in self.decks.decks_index(con)}

    def carta(self, con, slug: str, nome: str) -> dict:
        p = self.decks.deck_payload(con, self.idx(con)[slug]["id"])
        return next(c for s in p["sections"] for c in s["cards"] if c["name"] == nome)


# ---------------------------------------------------------------------------


class TestGrupo(Base):
    def test_a_mesma_legend_faz_um_grupo(self):
        con = self.catalogo(ornn=True)
        gs = self.decks.grupos(con)
        self.assertEqual([sorted(g["slugs"]) for g in gs],
                         [["leblanc", "leblanc-baited-hook"], ["ornn"]])
        lb = gs[0]
        self.assertTrue(lb["variantes"])
        self.assertEqual(lb["rotulo"], "Deceiver ·· LeBlanc Baited Hook")
        self.assertEqual(lb["lider"], self.idx(con)["leblanc"]["id"], "o de prioridade mais alta")
        self.assertFalse(gs[1]["variantes"])
        con.close()

    def test_a_procura_do_grupo_e_o_maximo_por_carta(self):
        """3 Hidden Blade + 2 = o grupo pede 3, não 5; Baited Hook só está no
        segundo e o grupo pede 3."""
        con = self.catalogo(hidden=2)
        a = self.decks.allocate(con)
        g = a[self.idx(con)["leblanc"]["id"]]["grupo"]
        self.assertEqual(g["need"], {"hidden blade": 3, "defy": 3, "baited hook": 3,
                                     "deceiver": 1})
        # Tem 2 Hidden Blade: o grupo compra 1 (e não 3).
        self.assertEqual(g["missing"], {"hidden blade": 1, "baited hook": 3})
        con.close()

    def test_o_missing_e_igual_nos_dois_e_o_total_conta_uma_vez(self):
        con = self.catalogo(hidden=1)
        idx = self.idx(con)
        # Os dois pedem Hidden Blade (3 e 2), há 1: o LeBlanc compra 2, o
        # Baited Hook 1 — cada lista corta ao que pede — mas a compra é uma.
        lb = self.carta(con, "leblanc", "Hidden Blade")
        bh = self.carta(con, "leblanc-baited-hook", "Hidden Blade")
        self.assertEqual((lb["have"], lb["missing"]), (1, 2))
        self.assertEqual((bh["have"], bh["missing"]), (1, 1))
        self.assertIsNone(lb["shared"], "o irmão não é disputa")
        self.assertEqual([x["slug"] for x in lb["partilhada"]], ["leblanc-baited-hook"])
        self.assertEqual(lb["partilhada"][0]["qty"], 2)
        # O Baited Hook só o segundo pede: 3 a comprar, e só ele mostra.
        self.assertEqual(self.carta(con, "leblanc-baited-hook", "Baited Hook")["missing"], 3)
        self.assertEqual(idx["leblanc"]["missing"], 2)
        self.assertEqual(idx["leblanc-baited-hook"]["missing"], 4)
        # O total conta o grupo uma vez: 2 Hidden Blade + 3 Baited Hook = 5.
        tot = self.decks.resumo_das_faltas(con)
        self.assertEqual((tot["copies"], tot["cards"], tot["disputed"]), (5, 2, 0))
        self.assertEqual(tot["cents"], 2 * 200 + 3 * 400)
        self.assertEqual(idx["leblanc"]["grupo"]["missing"], 5)
        self.assertEqual(idx["leblanc-baited-hook"]["grupo"]["missing"], 5)
        self.assertEqual(idx["leblanc"]["grupo"]["irmaos"], ["LeBlanc Baited Hook"])
        # A lista de compras de tudo é a mesma conta.
        lista = {x["name"]: x["qty"] for x in self.decks.shopping_list(con)}
        self.assertEqual(lista, {"Hidden Blade": 2, "Baited Hook": 3})
        con.close()

    def test_quando_pedem_o_mesmo_o_missing_e_identico(self):
        con = self.catalogo(defy=1)
        self.assertEqual(self.carta(con, "leblanc", "Defy")["missing"], 2)
        self.v.write_deck("leblanc-baited-hook", BAITED + "3 Defy\n")
        self.decks.import_all(con, log=lambda *_: None)
        self.assertEqual(self.carta(con, "leblanc", "Defy")["missing"], 2)
        self.assertEqual(self.carta(con, "leblanc-baited-hook", "Defy")["missing"], 2)
        self.assertEqual(self.decks.resumo_das_faltas(con)["copies"],
                         2 + 1 + 3, "2 Defy + 1 Hidden Blade + 3 Baited Hook, uma vez")
        con.close()

    def test_um_mais_num_deck_baixa_a_falta_dos_dois(self):
        """«O que encomendar para 1 deck, estou a encomendar para o outro
        também.»"""
        con = self.catalogo(hidden=1)
        self.pending.encomendar(con, card_key="hidden blade", qty=1,
                                source="deck:leblanc-baited-hook")
        lb = self.carta(con, "leblanc", "Hidden Blade")
        bh = self.carta(con, "leblanc-baited-hook", "Hidden Blade")
        self.assertEqual((lb["ordered"], lb["missing"]), (1, 1))
        self.assertEqual((bh["ordered"], bh["missing"]), (1, 0))
        idx = self.idx(con)
        self.assertEqual(idx["leblanc"]["grupo"]["missing"], 1 + 3)
        # A lista Encomendas diz «para» o grupo, uma vez.
        e = self.pending.encomendas(con)
        it = e["a_caminho"][0]["items"][0]
        self.assertEqual(it["para"], [{"deck": "Deceiver ·· LeBlanc Baited Hook",
                                       "slug": "leblanc", "qty": 1}])
        self.assertEqual(e["falta_totals"]["copies"], 4)
        con.close()


class TestEntreGrupos(Base):
    """Legends diferentes continuam a somar e a disputar."""

    def test_legends_diferentes_somam_e_disputam(self):
        con = self.catalogo(defy=3, ornn=True)
        idx = self.idx(con)
        # O grupo LeBlanc (prioridade 1) leva as 3 Defy; o Ornn compra 3,
        # disputadas.
        self.assertEqual(self.carta(con, "leblanc", "Defy")["missing"], 0)
        ornn_defy = self.carta(con, "ornn", "Defy")
        self.assertEqual(ornn_defy["missing"], 3)
        self.assertEqual(ornn_defy["shared"]["qty"], 3)
        self.assertEqual([h["deck"] for h in ornn_defy["shared"]["em"]],
                         ["Deceiver ·· LeBlanc Baited Hook"])
        self.assertEqual(idx["ornn"]["shared"], 3)
        falta = {x["name"]: x for x in self.faltas.shortfall(con)}
        self.assertEqual(falta["Defy"]["wanted"], 6, "3 do grupo + 3 do Ornn")
        self.assertEqual(falta["Defy"]["n_decks"], 2)
        con.close()

    def test_a_staple_e_de_grupos_diferentes__nao_de_duas_listas(self):
        con = self.catalogo(hidden=0)
        falta = {x["name"]: x for x in self.faltas.shortfall(con)}
        self.assertEqual(falta["Hidden Blade"]["wanted"], 3)
        self.assertEqual(falta["Hidden Blade"]["n_decks"], 1)
        self.assertEqual({d["slug"] for d in falta["Hidden Blade"]["decks"]},
                         {"leblanc", "leblanc-baited-hook"}, "mas mostra as duas listas")
        self.assertEqual(self.faltas.staples(con), [])
        con.close()

    def test_a_seccao_faltas_conta_o_grupo_uma_vez(self):
        con = self.catalogo(hidden=1, ornn=True)
        tj = self.faltas.todos_juntos(con)
        # Hidden Blade 3−1 = 2, Baited Hook 3, Defy 6−3 = 3, Forge Master 1.
        self.assertEqual(tj["copies"], 2 + 3 + 3 + 1)
        self.assertEqual(self.decks.resumo_das_faltas(con)["copies"], tj["copies"])
        por_deck = {d["name"]: d for d in self.faltas.por_deck(con)}
        self.assertTrue(por_deck["Deceiver"]["grupo"]["variantes"])
        self.assertEqual(por_deck["LeBlanc Baited Hook"]["grupo"]["irmaos"], ["Deceiver"])
        con.close()


class TestColecaoEVenda(Base):
    def test_a_colecao_mostra_o_grupo_sem_duplicar(self):
        con = self.catalogo(hidden=1)
        uso = self.decks.uso_por_carta(con)
        self.assertEqual(len(uso["hidden blade"]), 1, "uma entrada, não duas")
        u = uso["hidden blade"][0]
        self.assertEqual(u["deck"], "Deceiver ·· LeBlanc Baited Hook")
        self.assertEqual(u["membros"], ["Deceiver", "LeBlanc Baited Hook"])
        self.assertEqual((u["wanted"], u["have"], u["missing"]), (3, 1, 2))
        # Só o segundo pede Baited Hook: é ele que aparece.
        self.assertEqual(uso["baited hook"][0]["deck"], "LeBlanc Baited Hook")
        self.assertEqual(uso["baited hook"][0]["membros"], ["LeBlanc Baited Hook"])
        grupos = {g["card_key"]: g for g in self.metrics.set_payload(con, "TST")["groups"]}
        self.assertEqual(len(grupos["hidden blade"]["decks"]), 1)
        con.close()

    def test_o_stats_usadas_diz_o_grupo(self):
        from riftvault import cli
        self.catalogo(hidden=1).close()
        importlib.reload(cli)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(cli.main(["stats", "--usadas"]), 0)
        texto = out.getvalue()
        self.assertRegex(texto, r"Hidden Blade\s+1\s+Deceiver ·· LeBlanc Baited Hook 3 \(faltam 2\)")
        con = self.v.connect()
        con.close()

    def test_a_venda_conta_as_copias_do_grupo_uma_vez(self):
        """4 Hidden Blade na Coleção, o grupo usa 3: sobra 1 — não 4−6 < 0."""
        con = self.catalogo(hidden=4)
        usadas = self.decks.colecao_allocation(con)
        self.assertEqual(usadas["tst-001-100"],
                         [{"deck": "Deceiver ·· LeBlanc Baited Hook", "slug": "leblanc",
                           "qty": 3, "priority": 1}])
        con.close()

    def test_o_deck_diz_o_grupo(self):
        con = self.catalogo()
        p = self.decks.deck_payload(con, self.idx(con)["leblanc-baited-hook"]["id"])
        self.assertEqual(p["grupo"]["irmaos"], ["Deceiver"])
        self.assertFalse(p["grupo"]["lider"])
        self.assertTrue(p["grupo"]["variantes"])
        con.close()


if __name__ == "__main__":
    unittest.main()

"""Os `+`/`−` das encomendas nos decks (André, 2026-09-11).

Palavras dele:
    *"podes criar, nos decks, um botão de + e − que indique o que já está
    encomendado (comprado), mas que ainda não chegou; assim consigo contigo
    organizar melhor as compras"*

O mecanismo é a tabela `pending` que já existia; o que se fixa aqui é que os
`+`/`−` sobem e descem sem ir abaixo de zero, que o `missing` do deck desconta
a encomenda, que a encomenda serve o deck de prioridade mais alta, que «Chegou»
soma à Coleção e limpa a encomenda, que a lista agrupa por edição e soma certo,
e que a Coleção e o deck vêem o mesmo número.

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
ORNN = ("Legend:\n1 Emperor of the Sands\n\nChampion:\n1 Spirit Blade\n\n"
        "MainDeck:\n2 Defy\n")


class Base(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.close)
        from riftvault import a_subir, decks, faltas, locais, metrics, pending
        for m in (metrics, locais, pending, decks, faltas, a_subir):
            importlib.reload(m)
        self.decks, self.faltas, self.pending = decks, faltas, pending
        self.metrics, self.a_subir = metrics, a_subir

    def catalogo(self, defy: int = 3):
        """Uma edição pequena; o azir pede 3 Defy, o ornn 2, há `defy` na Coleção."""
        from riftvault import collection
        con = self.v.connect()
        self.v.add_printing(con, "tst-001-100", "TST", 1, "Defy", size=100)
        self.v.add_printing(con, "tst-001a-100", "TST", 1, "Defy",
                            variant="a", kind="alt_art", size=100)
        self.v.add_printing(con, "tst-002-100", "TST", 2, "Brutalizer", size=100)
        self.v.add_printing(con, "tst-003-100", "TST", 3, "Emperor of the Sands",
                            card_type="Legend", size=100)
        self.v.add_printing(con, "tst-004-100", "TST", 4, "Spirit Blade", size=100)
        # A mesma Defy noutra edição, mais cara: o `+` tem de ir para a barata.
        self.v.add_printing(con, "tsu-010-050", "TSU", 10, "Defy", size=50)
        self.v.rebuild(con)
        for pid, cents in (("tst-001-100", 150), ("tst-001a-100", 2000),
                           ("tst-002-100", 50), ("tst-003-100", 1000),
                           ("tst-004-100", 700), ("tsu-010-050", 300)):
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


class TestMaisEMenos(Base):
    """Os botões sobem e descem, e nunca vão abaixo de zero."""

    def test_o_mais_grava_na_impressao_base_mais_barata(self):
        con = self.catalogo()
        res = self.pending.encomendar(con, card_key="defy", qty=1, source="test")
        self.assertEqual(res["printing_id"], "tst-001-100", "a base a 1,50 €, não a TSU a 3 €")
        self.assertEqual(res["open_card"], 1)
        self.assertEqual(self.pending.open_by_card(con), {"defy": 1})
        con.close()

    def test_o_mais_e_o_menos_sobem_e_descem(self):
        con = self.catalogo()
        self.pending.encomendar(con, card_key="defy", qty=1, source="test")
        self.pending.encomendar(con, card_key="defy", qty=1, source="test")
        self.assertEqual(self.pending.open_by_card(con)["defy"], 2)
        res = self.pending.anular(con, card_key="defy", qty=1, source="test")
        self.assertEqual(res["open_card"], 1)
        self.assertEqual(res["removed"], 1)
        self.pending.anular(con, card_key="defy", qty=1, source="test")
        self.assertEqual(self.pending.open_by_card(con), {}, "a zero, sem linha nenhuma")
        con.close()

    def test_o_menos_nao_vai_abaixo_de_zero(self):
        con = self.catalogo()
        with self.assertRaises(self.pending.SemEncomenda):
            self.pending.anular(con, card_key="defy", qty=1, source="test")
        self.pending.encomendar(con, card_key="defy", qty=1, source="test")
        # Pede 3, há 1: tira a que há e diz quantas tirou.
        res = self.pending.anular(con, card_key="defy", qty=3, source="test")
        self.assertEqual(res["removed"], 1)
        self.assertEqual(res["open_card"], 0)
        with self.assertRaises(self.pending.SemEncomenda):
            self.pending.anular(con, card_key="defy", qty=1, source="test")
        con.close()

    def test_o_menos_tira_da_carta_seja_de_que_impressao_for(self):
        """Uma encomenda antiga na arte alternativa também é da carta."""
        con = self.catalogo()
        self.pending.add(con, "tst-001a-100", 1, source="test")
        res = self.pending.anular(con, card_key="defy", qty=1, source="test")
        self.assertEqual(res["printing_id"], "tst-001a-100")
        self.assertEqual(self.pending.open_by_card(con), {})
        con.close()

    def test_deixa_rasto_no_log(self):
        con = self.catalogo()
        self.pending.encomendar(con, card_key="defy", qty=2, source="web deck:ornn")
        self.pending.anular(con, card_key="defy", qty=1, source="test")
        log = (self.v.data / "encomendas.log").read_text(encoding="utf-8")
        linhas = [l for l in log.splitlines() if l and not l.startswith("﻿quando")]
        self.assertEqual(len(linhas), 2)
        self.assertIn(",tst-001-100,TST-001/100,Defy,2,encomendar,web deck:ornn,", linhas[0])
        self.assertIn(",1,anular,test,", linhas[1])
        con.close()


class TestDescontaDoDeck(Base):
    """O que está encomendado já não é para comprar — e não é tido."""

    def test_o_missing_do_deck_desconta_a_encomenda(self):
        con = self.catalogo(defy=3)      # o ornn não recebe Defy nenhuma
        antes = self.idx(con)["ornn"]
        self.assertEqual((antes["missing"], antes["ordered"]), (4, 0))
        self.pending.encomendar(con, card_key="defy", qty=2, source="test")
        depois = self.idx(con)["ornn"]
        self.assertEqual((depois["missing"], depois["ordered"]), (2, 2))
        self.assertEqual(depois["have"], antes["have"], "a caminho não é tido")
        defy = self.carta(con, "ornn", "Defy")
        self.assertEqual((defy["wanted"], defy["have"], defy["ordered"], defy["missing"]),
                         (2, 0, 2, 0))
        self.assertEqual(defy["order_code"], "TST-001/100")
        con.close()

    def test_o_falta_comprar_por_edicao_e_o_stats_descontam(self):
        con = self.catalogo(defy=3)
        self.pending.encomendar(con, card_key="defy", qty=2, source="test")
        ornn = self.idx(con)["ornn"]["id"]
        por_set = self.decks.missing_by_set(con, ornn)
        nomes = [it["name"] for g in por_set for it in g["items"]]
        self.assertNotIn("Defy", nomes)
        self.assertEqual(sum(g["copies"] for g in por_set), 2, "o Legend e a Spirit Blade")
        tot = self.decks.resumo_das_faltas(con)
        self.assertEqual((tot["copies"], tot["ordered"]), (2, 2))
        self.assertEqual(tot["cents"], 1000 + 700)
        con.close()

    def test_a_seccao_faltas_da_o_mesmo_numero_e_nao_conta_a_dobrar(self):
        """A secção Faltas descontava o pendente por conta própria; agora é a
        alocação que o faz, e a soma tem de continuar a ser uma só."""
        con = self.catalogo(defy=3)
        self.pending.encomendar(con, card_key="defy", qty=2, source="test")
        por_deck = {d["name"]: d for d in self.faltas.por_deck(con)}
        idx = self.idx(con)
        self.assertEqual(por_deck[idx["ornn"]["name"]]["copies"], 2)
        self.assertEqual(por_deck[idx["azir"]["name"]]["copies"], 0)
        tj = self.faltas.todos_juntos(con)
        self.assertEqual(tj["copies"], 2)
        # A wantlist do deck sai sem a Defy.
        texto = self.faltas.wantlist(por_deck[idx["ornn"]["name"]]["by_set"])["text"]
        self.assertNotIn("Defy", texto)
        con.close()

    def test_a_encomenda_serve_o_deck_de_prioridade_mais_alta(self):
        """Sem Defy na Coleção, 1 a caminho: é o azir (prioridade 1) que a leva."""
        con = self.catalogo(defy=0)
        self.pending.encomendar(con, card_key="defy", qty=1, source="test")
        idx = self.idx(con)
        self.assertEqual((idx["azir"]["ordered"], idx["ornn"]["ordered"]), (1, 0))
        self.assertEqual(self.carta(con, "azir", "Defy")["missing"], 2)
        self.assertEqual(self.carta(con, "ornn", "Defy")["missing"], 2)
        # Trocar a ordem troca quem a leva.
        self.decks.set_order(con, [idx["ornn"]["id"], idx["azir"]["id"]])
        idx = self.idx(con)
        self.assertEqual((idx["azir"]["ordered"], idx["ornn"]["ordered"]), (0, 1))
        con.close()

    def test_a_mais_do_que_os_decks_pedem_nao_conta_para_deck_nenhum(self):
        con = self.catalogo(defy=3)
        self.pending.encomendar(con, card_key="defy", qty=5, source="test")
        idx = self.idx(con)
        self.assertEqual(idx["ornn"]["ordered"], 2, "só o que o deck pede")
        self.assertEqual(idx["ornn"]["missing"], 2)
        e = self.pending.encomendas(con)
        it = e["a_caminho"][0]["items"][0]
        self.assertEqual(it["qty"], 5)
        self.assertEqual(it["para"], [{"deck": idx["ornn"]["name"], "slug": "ornn", "qty": 2}])
        self.assertEqual(it["sem_deck"], 3)
        con.close()


class TestChegou(Base):
    """«Chegou» soma à Coleção e limpa a encomenda. Idempotente."""

    def test_chegou_da_carta(self):
        from riftvault import collection
        con = self.catalogo(defy=3)
        self.pending.encomendar(con, card_key="defy", qty=2, source="test")
        feitas = self.pending.arrive(con, source="test", card_key="defy")
        self.assertEqual([(f["printing_id"], f["qty"], f["total"]) for f in feitas],
                         [("tst-001-100", 2, 5)])
        self.assertEqual(self.pending.open_by_card(con), {})
        self.assertEqual(self.decks.owned_by_card(con)["defy"], 5)
        ornn = self.idx(con)["ornn"]
        # As 2 Defy passaram a tidas (o azir leva 3 das 5); o Legend e a
        # Spirit Blade continuam a faltar.
        self.assertEqual((ornn["ordered"], ornn["missing"], ornn["have"]), (0, 2, 2))
        # Segunda vez: não há nada, e não soma outra vez.
        self.assertEqual(self.pending.arrive(con, source="test", card_key="defy"), [])
        self.assertEqual(self.decks.owned_by_card(con)["defy"], 5)
        # Passou pelo `ops`: dá para desfazer.
        self.assertIsNotNone(collection.undo_last(con, source="test"))
        self.assertEqual(self.decks.owned_by_card(con)["defy"], 3)
        con.close()

    def test_chegou_por_ids_so_toca_nessas_linhas(self):
        con = self.catalogo(defy=3)
        a = self.pending.add(con, "tst-001-100", 1, source="test")
        b = self.pending.add(con, "tst-004-100", 1, source="test")
        feitas = self.pending.arrive(con, [a["id"]], source="test")
        self.assertEqual([f["id"] for f in feitas], [a["id"]])
        self.assertEqual(self.pending.open_qty(con), {"tst-004-100": 1})
        self.assertEqual(self.pending.arrive(con, [], source="test"), [])
        self.assertEqual(self.pending.open_qty(con), {"tst-004-100": 1})
        self.assertEqual([f["id"] for f in self.pending.arrive(con, source="test")], [b["id"]])
        con.close()

    def test_o_menos_reverte_uma_encomenda_antes_de_chegar(self):
        con = self.catalogo(defy=3)
        self.pending.encomendar(con, card_key="defy", qty=1, source="test")
        self.pending.anular(con, card_key="defy", qty=1, source="test")
        self.assertEqual(self.pending.arrive(con, source="test", card_key="defy"), [])
        self.assertEqual(self.decks.owned_by_card(con)["defy"], 3, "nada entrou")
        con.close()


class TestLista(Base):
    """A lista «Encomendas» agrupa por edição e soma certo."""

    def test_agrupa_por_edicao_e_soma(self):
        con = self.catalogo(defy=3)
        self.pending.encomendar(con, card_key="defy", qty=2, source="test")
        self.pending.encomendar(con, printing_id="tsu-010-050", qty=1, source="test")
        self.pending.add(con, "tst-004-100", 1, unit_cents=600, source="test")
        e = self.pending.encomendas(con)
        self.assertEqual([g["set"] for g in e["a_caminho"]], ["TST", "TSU"])
        tst = e["a_caminho"][0]
        self.assertEqual((tst["copies"], tst["cards"], tst["cents"]), (3, 2, 2 * 150 + 700))
        self.assertEqual(tst["paid"], 600)
        tsu = e["a_caminho"][1]
        self.assertEqual((tsu["copies"], tsu["cents"]), (1, 300))
        t = e["totals"]
        self.assertEqual((t["copies"], t["printings"], t["cents"], t["paid"]),
                         (4, 3, 300 + 700 + 300, 600))
        self.assertEqual(t["copies"], sum(g["copies"] for g in e["a_caminho"]))
        self.assertEqual(t["cents"], sum(g["cents"] for g in e["a_caminho"]))
        con.close()

    def test_diz_para_que_deck_vai_cada_copia(self):
        con = self.catalogo(defy=0)
        self.pending.encomendar(con, card_key="defy", qty=4, source="test")
        e = self.pending.encomendas(con)
        it = e["a_caminho"][0]["items"][0]
        idx = self.idx(con)
        self.assertEqual(it["para"], [
            {"deck": idx["azir"]["name"], "slug": "azir", "qty": 3},
            {"deck": idx["ornn"]["name"], "slug": "ornn", "qty": 1}])
        self.assertEqual(it["sem_deck"], 0)
        con.close()

    def test_falta_encomendar_e_o_missing_depois_das_encomendas(self):
        con = self.catalogo(defy=3)
        antes = self.pending.encomendas(con)["falta_totals"]
        self.assertEqual((antes["copies"], antes["cents"]), (4, 2 * 150 + 1000 + 700))
        self.pending.encomendar(con, card_key="defy", qty=2, source="test")
        e = self.pending.encomendas(con)
        f = e["falta_totals"]
        self.assertEqual((f["copies"], f["cards"], f["cents"]), (2, 2, 1700))
        self.assertEqual(f["copies"], sum(g["copies"] for g in e["falta"]))
        self.assertEqual(f["cents"], sum(g["cents"] for g in e["falta"]))
        self.assertEqual(sorted(it["name"] for g in e["falta"] for it in g["items"]),
                         ["Emperor of the Sands", "Spirit Blade"])
        self.assertTrue(all(it["deck"] == self.idx(con)["ornn"]["name"]
                            for g in e["falta"] for it in g["items"]))
        con.close()

    def test_sem_nada_a_caminho(self):
        con = self.catalogo(defy=3)
        e = self.pending.encomendas(con)
        self.assertEqual(e["a_caminho"], [])
        self.assertEqual(e["totals"]["copies"], 0)
        self.assertEqual(e["falta_totals"]["copies"], 4)
        con.close()

    def test_o_cli_lista_e_mexe(self):
        from riftvault import cli
        self.catalogo(defy=3).close()
        importlib.reload(cli)

        def corre(*argv):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = cli.main(list(argv))
            return code, out.getvalue()

        code, txt = corre("encomendas", "--mais", "Defy", "2")
        self.assertEqual(code, 0)
        self.assertIn("+2  Defy [TST-001/100 · base]  -> 2 a caminho", txt)
        code, txt = corre("encomendas")
        self.assertEqual(code, 0)
        self.assertIn("A caminho: 2 cópias · 1 impressões · 3.00 €", txt)
        self.assertIn("Falta encomendar: 2 cópias de 2 cartas · 17.00 €", txt)
        code, txt = corre("encomendas", "--menos", "TST-001", "1")
        self.assertIn("-1  Defy", txt)
        code, txt = corre("decks")
        self.assertIn("a caminho", txt)
        self.assertRegex(txt, r"1 já a caminho")
        code, txt = corre("encomendas", "--chegou", "Defy")
        self.assertEqual(code, 0)
        self.assertIn("1 linhas deram entrada", txt)
        code, txt = corre("encomendas")
        self.assertIn("Nada a caminho.", txt)


class TestColecaoEDeckVeemOMesmo(Base):
    """A Coleção (`regra_falta: 'master'`, por impressão) e o deck (por carta)
    descontam a MESMA encomenda, e ninguém a conta duas vezes."""

    def test_a_wantlist_da_colecao_desconta_o_mais_do_deck(self):
        con = self.catalogo(defy=1)      # falta 2 ao master set, falta 4 aos decks
        wl_antes = {x["printing_id"]: x for x in self.a_subir.wantlist(con)["items"]}
        self.assertEqual(wl_antes["tst-001-100"]["missing"], 2)
        self.pending.encomendar(con, card_key="defy", qty=2, source="test")
        wl = {x["printing_id"]: x for x in self.a_subir.wantlist(con)["items"]}
        self.assertNotIn("tst-001-100", wl, "a Coleção deixa de a pedir")
        idx = self.idx(con)
        self.assertEqual(idx["azir"]["ordered"] + idx["ornn"]["ordered"], 2,
                         "os decks vêem as mesmas 2")
        self.assertEqual(self.pending.open_by_card(con)["defy"], 2, "e são 2, não 4")
        con.close()

    def test_a_barra_da_colecao_nao_mexe_ate_chegar(self):
        con = self.catalogo(defy=1)
        antes = self.metrics.set_payload(con, "TST")["progress"]["master"]
        self.pending.encomendar(con, card_key="defy", qty=2, source="test")
        depois = self.metrics.set_payload(con, "TST")["progress"]["master"]
        self.assertEqual(antes["done"], depois["done"], "a caminho não está na caixa")
        self.pending.arrive(con, source="test", card_key="defy")
        chegou = self.metrics.set_payload(con, "TST")["progress"]["master"]
        self.assertEqual(chegou["done"], antes["done"] + 1, "Defy passou a 3/3")
        con.close()

    def test_a_grelha_da_colecao_diz_o_a_caminho_do_deck(self):
        con = self.catalogo(defy=3)
        self.pending.encomendar(con, card_key="defy", qty=1, source="test")
        grupos = {g["card_key"]: g for g in self.metrics.set_payload(con, "TST")["groups"]}
        uso = {u["slug"]: u for u in grupos["defy"]["decks"]}
        self.assertEqual((uso["ornn"]["ordered"], uso["ornn"]["missing"]), (1, 1))
        self.assertEqual(self.carta(con, "ornn", "Defy")["ordered"], 1)
        con.close()


if __name__ == "__main__":
    unittest.main()

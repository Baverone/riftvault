"""Binders de coleção, decks, e o binder Decks/Venda (André, 2026-09-10).

*"Vou querer ter as cartas da coleção apenas alocadas à coleção e as cartas dos
decks apenas alocadas a Decks. Ou seja: a coleção fica em Binders de coleção; as
cartas dos decks ficam em decks, e haverá um Binder que será apenas e
exclusivamente para Decks/Venda — caso um deck seja desfeito, as cartas ficam
para outro deck ou nesse binder."*

Cada regra dessa frase tem aqui um caso que parte se ela for apagada.
"""

from __future__ import annotations

import csv
import importlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.fixture import Vault

DECK_AZIR = """Legend:
1 Emperor of the Sands

MainDeck:
3 Defy
3 Brutalizer
"""


class Base(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.close)
        from riftvault import a_subir, decks, locais, metrics, venda
        for m in (metrics, decks, locais, a_subir, venda):
            importlib.reload(m)
        self.locais, self.decks, self.metrics = locais, decks, metrics
        self.venda, self.a_subir = venda, a_subir

    def catalogo(self, com_deck: bool = True):
        """Uma edição pequena, a coleção lá dentro e (opcional) um deck."""
        from riftvault import collection
        con = self.v.connect()
        self.v.add_printing(con, "tst-001-100", "TST", 1, "Defy", size=100)
        self.v.add_printing(con, "tst-001a-100", "TST", 1, "Defy",
                            variant="a", kind="alt_art", size=100)
        self.v.add_printing(con, "tst-002-100", "TST", 2, "Brutalizer", size=100)
        self.v.add_printing(con, "tst-003-100", "TST", 3, "Emperor of the Sands",
                            card_type="Legend", size=100)
        # Uma carta que nenhum deck pede — é dela que se faz a venda.
        self.v.add_printing(con, "tst-004-100", "TST", 4, "Spirit Blade", size=100)
        self.v.rebuild(con)
        for pid, n in (("tst-001-100", 4), ("tst-002-100", 3), ("tst-003-100", 1)):
            collection.adjust(con, pid, n, source="test")
        if com_deck:
            self.v.write_deck("azir", DECK_AZIR)
            self.decks.import_all(con, log=lambda *_: None)
        return con

    def total_de_copias(self, con) -> int:
        return con.execute("SELECT COALESCE(SUM(qty),0) FROM copies").fetchone()[0]


# ---------------------------------------------------------------------------


class TestMigracao(Base):
    """Onde não se sabe o local, fica Coleção — e não se perde nenhuma cópia."""

    def test_por_omissao_esta_tudo_na_colecao(self):
        con = self.catalogo(com_deck=False)
        self.assertEqual(
            con.execute("SELECT COUNT(*) FROM copy_locations").fetchone()[0], 0,
            "a migração não escreve linha nenhuma: a Coleção calcula-se")
        self.assertEqual(self.locais.na_colecao(con), self.locais.totais(con))
        con.close()

    def test_a_contagem_antes_e_depois_e_a_mesma(self):
        con = self.catalogo()
        antes = self.total_de_copias(con)
        soma_antes = sum(self.locais.na_colecao(con).values())

        self.locais.mover(con, "tst-001-100", 3, self.locais.COLECAO,
                          self.locais.deck_local("azir"), source="test")
        self.locais.mover(con, "tst-002-100", 1, self.locais.COLECAO,
                          self.locais.BINDER, source="test")

        depois = self.total_de_copias(con)
        soma_depois = sum(v for locs in self.locais.por_local(con).values()
                          for v in locs.values())
        self.assertEqual(antes, depois, "mover não pode criar nem destruir cópias")
        self.assertEqual(soma_antes, soma_depois)
        con.close()

    def test_e_idempotente__correr_o_schema_outra_vez_nao_mexe(self):
        from riftvault import db
        con = self.catalogo()
        self.locais.mover(con, "tst-001-100", 2, self.locais.COLECAO,
                          self.locais.BINDER, source="test")
        antes = con.execute(
            "SELECT printing_id, location, qty FROM copy_locations "
            "ORDER BY printing_id").fetchall()
        con.close()

        con = db.connect()          # volta a aplicar o schema.sql
        depois = con.execute(
            "SELECT printing_id, location, qty FROM copy_locations "
            "ORDER BY printing_id").fetchall()
        self.assertEqual([tuple(r) for r in antes], [tuple(r) for r in depois])
        con.close()


class TestColecaoNaoVeDecks(Base):
    """A Coleção só conta cópias com local = Coleção."""

    def test_a_percentagem_desce_quando_a_copia_vai_para_um_deck(self):
        con = self.catalogo()
        antes = self.metrics.set_payload(con, "TST")["progress"]["master"]
        self.assertEqual(antes["done"], 3)     # Defy 4/3, Brutalizer 3/3, Legend 1/1

        self.locais.mover(con, "tst-002-100", 3, self.locais.COLECAO,
                          self.locais.deck_local("azir"), source="test")
        depois = self.metrics.set_payload(con, "TST")["progress"]["master"]
        self.assertEqual(depois["done"], 2, "o Brutalizer saiu da Coleção")
        self.assertEqual(depois["total"], antes["total"], "o denominador não mexe")
        con.close()

    def test_o_tile_diz_o_que_a_colecao_tem_e_onde_estao_as_outras(self):
        con = self.catalogo()
        self.locais.mover(con, "tst-001-100", 3, self.locais.COLECAO,
                          self.locais.deck_local("azir"), source="test")
        p = self._printing(con, "tst-001-100")
        self.assertEqual(p["qty"], 1, "só 1 ficou na Coleção")
        self.assertEqual(p["qty_total"], 4, "mas ele tem 4")
        self.assertEqual({x["loc"]: x["qty"] for x in p["locations"]},
                         {"colecao": 1, "deck:azir": 3})
        self.assertEqual([x["qty"] for x in p["in_decks"]], [3])
        con.close()

    def test_a_wantlist_volta_a_pedir_o_que_foi_para_o_deck(self):
        """Se a cópia saiu da Coleção, a Coleção volta a pedi-la."""
        con = self.catalogo()
        antes = self.a_subir.master_faltas(con)["copies"]
        self.locais.mover(con, "tst-002-100", 3, self.locais.COLECAO,
                          self.locais.deck_local("azir"), source="test")
        depois = self.a_subir.master_faltas(con)["copies"]
        self.assertEqual(depois - antes, 3)
        con.close()

    def test_os_niveis_tambem_so_contam_a_colecao(self):
        con = self.catalogo()
        antes = self.metrics.niveis_payload(con)["levels"]
        self.locais.mover(con, "tst-002-100", 3, self.locais.COLECAO,
                          self.locais.BINDER, source="test")
        depois = self.metrics.niveis_payload(con)["levels"]
        self.assertEqual(antes[0]["missing"] + 1, depois[0]["missing"])
        self.assertEqual(antes[-1]["missing"] + 3, depois[-1]["missing"])
        con.close()

    def _printing(self, con, pid):
        for g in self.metrics.set_payload(con, "TST")["groups"]:
            for p in g["printings"]:
                if p["id"] == pid:
                    return p
        self.fail(f"{pid} não apareceu no payload")


class TestDecksNaoTiramDaColecao(Base):
    """Os decks montam-se com os três locais — e a Coleção CONTA (2026-09-11).

    Entre 2026-09-10 e 2026-09-11 só contavam o deck e o binder Decks/Venda, e
    o que estava na Coleção era «duplicado a comprar ou a decidir». A frase
    dele *"se há na coleção o deck usa"* mudou isso; os locais ficam como
    informação de onde a cópia está. A regra nova vive em
    `test_partilha_compra.py`; aqui fica o que os locais continuam a dizer.
    """

    def test_com_tudo_na_colecao_o_deck_esta_montado(self):
        con = self.catalogo()
        d = self.decks.decks_index(con)[0]
        self.assertEqual(d["have"], 7, "a Coleção monta decks (2026-09-11)")
        self.assertEqual(d["na_colecao"], 7, "e é de lá que as 7 vêm")
        self.assertEqual(d["missing"], 0)
        con.close()

    def test_marcadas_no_deck_contam_para_o_deck(self):
        con = self.catalogo()
        self.locais.mover(con, "tst-001-100", 3, self.locais.COLECAO,
                          self.locais.deck_local("azir"), source="test")
        d = self.decks.decks_index(con)[0]
        self.assertEqual(d["no_deck"], 3)
        self.assertEqual(d["no_binder"], 0)
        self.assertEqual(d["na_colecao"], 4, "as outras 4 vêm da Coleção")
        self.assertEqual(d["have"], 7, "os três locais somam o que tem")
        con.close()

    def test_o_binder_e_o_stock_livre_dos_decks(self):
        con = self.catalogo()
        self.locais.mover(con, "tst-002-100", 3, self.locais.COLECAO,
                          self.locais.BINDER, source="test")
        d = self.decks.decks_index(con)[0]
        self.assertEqual(d["no_binder"], 3, "o binder Decks/Venda serve os decks")
        self.assertEqual(d["no_deck"], 0)
        con.close()

    def test_o_binder_e_a_colecao_distribuem_se_por_prioridade(self):
        con = self.catalogo()
        # Champion diferente, senão os dois decks chamam-se «Emperor of the
        # Sands» e o «está noutro deck» compara-os pelo nome de mostrar.
        self.v.write_deck("ornn", "Legend:\n1 Emperor of the Sands\n"
                                  "Champion:\n1 Spirit Blade\n"
                                  "MainDeck:\n3 Brutalizer\n")
        self.decks.import_all(con, log=lambda *_: None)
        self.locais.mover(con, "tst-002-100", 3, self.locais.COLECAO,
                          self.locais.BINDER, source="test")

        idx = {d["slug"]: d for d in self.decks.decks_index(con)}
        self.assertEqual(idx["azir"]["no_binder"], 3)
        self.assertEqual(idx["ornn"]["no_binder"], 0)
        # 3 Brutalizer (o azir levou-as do binder) + 1 Legend (o azir levou-a
        # da Coleção) + 1 Spirit Blade que não existe: 5 a comprar, das quais
        # 4 existem num deck de cima — disputadas.
        self.assertEqual(idx["ornn"]["missing"], 5)
        self.assertEqual(idx["ornn"]["shared"], 4)
        con.close()

    def test_a_pagina_do_deck_diz_de_onde_vem_cada_copia(self):
        con = self.catalogo()
        self.locais.mover(con, "tst-001-100", 2, self.locais.COLECAO,
                          self.locais.deck_local("azir"), source="test")
        self.locais.mover(con, "tst-001-100", 1, self.locais.COLECAO,
                          self.locais.BINDER, source="test")
        p = self.decks.deck_payload(con, 1)
        defy = next(c for s in p["sections"] for c in s["cards"] if c["name"] == "Defy")
        self.assertEqual((defy["no_deck"], defy["no_binder"], defy["na_colecao"]),
                         (2, 1, 0), "o deck e o binder servem antes da Coleção")
        # O Brutalizer está todo na Coleção: conta, e diz de onde vem.
        brut = next(c for s in p["sections"] for c in s["cards"]
                    if c["name"] == "Brutalizer")
        self.assertEqual(brut["have"], 3)
        self.assertEqual(brut["na_colecao"], 3)
        self.assertEqual(p["locais"]["na_colecao"], 4)  # 3 Brutalizer + 1 Legend
        self.assertEqual(p["locais"]["missing"], 0)
        con.close()

    def test_o_que_nao_existe_em_lado_nenhum_e_que_se_compra(self):
        con = self.catalogo()
        self.v.write_deck("azir", DECK_AZIR.replace("3 Defy", "3 Defy\n2 Sprite"))
        # "Sprite" não existe no catálogo: fica em `unresolved`, não em missing.
        self.decks.import_all(con, log=lambda *_: None)
        d = self.decks.decks_index(con)[0]
        self.assertEqual(d["missing"], 0)
        # Agora uma que existe e ele não tem: o Legend passa a pedir 2.
        self.v.write_deck("azir", "Legend:\n1 Emperor of the Sands\n"
                                  "MainDeck:\n3 Defy\n2 Emperor of the Sands\n")
        self.decks.import_all(con, log=lambda *_: None)
        d = self.decks.decks_index(con)[0]
        self.assertEqual(d["na_colecao"], 4, "3 Defy + 1 Legend vêm da Coleção")
        self.assertEqual(d["missing"], 2, "as outras 2 do Legend não existem")
        self.assertEqual(d["shared"], 0, "e não estão em deck nenhum")
        con.close()


class TestDesfazerDeck(Base):
    """Caso um deck seja desfeito, as cartas ficam nesse binder."""

    def test_tudo_o_que_estava_no_deck_passa_ao_binder(self):
        con = self.catalogo()
        self.locais.mover(con, "tst-001-100", 3, self.locais.COLECAO,
                          self.locais.deck_local("azir"), source="test")
        self.locais.mover(con, "tst-003-100", 1, self.locais.COLECAO,
                          self.locais.deck_local("azir"), source="test")

        res = self.locais.desfazer_deck(con, "azir", source="test")
        self.assertEqual(res["copies"], 4)
        self.assertEqual(self.locais.em(con, self.locais.deck_local("azir")), {})
        self.assertEqual(self.locais.em(con, self.locais.BINDER),
                         {"tst-001-100": 3, "tst-003-100": 1})
        con.close()

    def test_nao_volta_a_colecao(self):
        """Quem as tirou da Coleção foi ele; devolvê-las era inventar."""
        con = self.catalogo()
        self.locais.mover(con, "tst-001-100", 3, self.locais.COLECAO,
                          self.locais.deck_local("azir"), source="test")
        antes = self.locais.na_colecao(con).get("tst-001-100", 0)
        self.locais.desfazer_deck(con, "azir", source="test")
        self.assertEqual(self.locais.na_colecao(con).get("tst-001-100", 0), antes)
        con.close()

    def test_ficam_disponiveis_para_outro_deck(self):
        con = self.catalogo()
        self.v.write_deck("ornn", "Legend:\n1 Emperor of the Sands\n"
                                  "MainDeck:\n3 Defy\n")
        self.decks.import_all(con, log=lambda *_: None)
        self.locais.mover(con, "tst-001-100", 3, self.locais.COLECAO,
                          self.locais.deck_local("azir"), source="test")
        # Enquanto está no azir, o ornn não lhe toca.
        idx = {d["slug"]: d for d in self.decks.decks_index(con)}
        self.assertEqual(idx["ornn"]["no_binder"], 0)

        self.locais.desfazer_deck(con, "azir", source="test")
        idx = {d["slug"]: d for d in self.decks.decks_index(con)}
        self.assertEqual(idx["azir"]["no_binder"], 3, "o azir volta a servir-se")
        con.close()

    def test_desfazer_um_deck_vazio_nao_faz_nada(self):
        con = self.catalogo()
        res = self.locais.desfazer_deck(con, "azir", source="test")
        self.assertEqual(res["copies"], 0)
        self.assertEqual(
            con.execute("SELECT COUNT(*) FROM location_ops").fetchone()[0], 0)
        con.close()


class TestVendaPorOrigem(Base):
    """A venda diz de onde vem cada cópia."""

    def test_o_que_esta_no_binder_e_nenhum_deck_pede(self):
        con = self.catalogo()
        # A Spirit Blade não está em deck nenhum e ele mandou-a para o binder.
        from riftvault import collection
        collection.adjust(con, "tst-004-100", 2, source="test")
        self.locais.mover(con, "tst-004-100", 2, self.locais.COLECAO,
                          self.locais.BINDER, source="test")

        v = self.venda.listar(con)
        item = next(x for x in v["items"] if x["printing_id"] == "tst-004-100")
        self.assertEqual(item["from_binder"], 2)
        self.assertEqual(item["from_colecao"], 0)
        self.assertEqual(item["origem"], "binder")
        self.assertEqual([o["id"] for o in v["origins"]], ["binder"])
        con.close()

    def test_a_sequencia_do_master_set_vende_se_quando_esta_no_binder(self):
        """Ele próprio a tirou da Coleção — já não é coleção."""
        con = self.catalogo()
        self.locais.mover(con, "tst-002-100", 3, self.locais.COLECAO,
                          self.locais.BINDER, source="test")
        self.v.write_deck("azir", "Legend:\n1 Emperor of the Sands\n"
                                  "MainDeck:\n3 Defy\n")
        self.decks.import_all(con, log=lambda *_: None)

        v = self.venda.listar(con)
        item = next(x for x in v["items"] if x["printing_id"] == "tst-002-100")
        self.assertEqual(item["block"], "master")
        self.assertEqual(item["from_binder"], 3)
        con.close()

    def test_a_sequencia_na_colecao_nunca_entra(self):
        """A decisão de 2026-09-08 fica de pé: a sequência não se vende."""
        con = self.catalogo()      # tem 4 Defy base (alvo 3) na Coleção
        v = self.venda.listar(con)
        self.assertEqual([x["printing_id"] for x in v["items"]], [])
        # Mas com o âmbito largo (as comuns e incomuns) aparece o excedente.
        largo = self.venda.excedente(con, incluir_master=True)
        item = next(x for x in largo if x["printing_id"] == "tst-001-100")
        self.assertEqual(item["from_colecao"], 1)
        con.close()

    def test_o_que_esta_dentro_de_um_deck_nunca_se_vende(self):
        con = self.catalogo()
        from riftvault import collection
        collection.adjust(con, "tst-001a-100", 3, source="test")
        self.locais.mover(con, "tst-001a-100", 3, self.locais.COLECAO,
                          self.locais.deck_local("azir"), source="test")
        v = self.venda.listar(con)
        self.assertEqual(v["items"], [])
        self.assertEqual(v["in_decks_copies"], 3)
        con.close()

    def test_nao_mexe_na_base(self):
        con = self.catalogo()
        self.locais.mover(con, "tst-001-100", 2, self.locais.COLECAO,
                          self.locais.BINDER, source="test")
        antes = con.execute("SELECT printing_id, location, qty FROM copy_locations "
                            "ORDER BY printing_id").fetchall()
        self.venda.listar(con)
        depois = con.execute("SELECT printing_id, location, qty FROM copy_locations "
                             "ORDER BY printing_id").fetchall()
        self.assertEqual([tuple(r) for r in antes], [tuple(r) for r in depois])
        con.close()


class TestMarcacao(Base):
    """A proposta é do vault; o que se grava é o que ele confirma."""

    def test_a_proposta_nao_grava_nada(self):
        con = self.catalogo()
        p = self.locais.propor_deck(con, "azir")
        self.assertEqual(p["copies"], 7)       # 3 Defy + 3 Brutalizer + 1 Legend
        self.assertEqual(
            con.execute("SELECT COUNT(*) FROM copy_locations").fetchone()[0], 0)
        con.close()

    def test_a_proposta_escolhe_artes_base_primeiro(self):
        con = self.catalogo()
        from riftvault import collection
        collection.adjust(con, "tst-001a-100", 3, source="test")
        p = self.locais.propor_deck(con, "azir")
        defy = [x for x in p["items"] if x["card_key"] == "defy"]
        self.assertEqual([x["printing_id"] for x in defy], ["tst-001-100"])
        con.close()

    def test_grava_so_as_linhas_confirmadas(self):
        con = self.catalogo()
        p = self.locais.propor_deck(con, "azir")
        uma = [x for x in p["items"] if x["printing_id"] == "tst-001-100"]
        res = self.locais.marcar(con, [{"printing_id": x["printing_id"], "qty": x["qty"]}
                                       for x in uma],
                                 self.locais.deck_local("azir"), source="test")
        self.assertEqual(res["copies"], 3)
        # As outras 4 da proposta continuam na Coleção.
        self.assertEqual(self.locais.na_colecao(con)["tst-002-100"], 3)
        self.assertEqual(self.locais.na_colecao(con)["tst-003-100"], 1)
        con.close()

    def test_uma_lista_vazia_rebenta_e_nao_grava(self):
        con = self.catalogo()
        with self.assertRaises(self.locais.SemCopias):
            self.locais.marcar(con, [], self.locais.deck_local("azir"))
        self.assertEqual(
            con.execute("SELECT COUNT(*) FROM copy_locations").fetchone()[0], 0)
        con.close()

    def test_nao_se_movem_copias_que_nao_ha(self):
        con = self.catalogo()
        with self.assertRaises(self.locais.SemCopias):
            self.locais.mover(con, "tst-003-100", 2, self.locais.COLECAO,
                              self.locais.BINDER, source="test")
        self.assertEqual(
            con.execute("SELECT COUNT(*) FROM copy_locations").fetchone()[0], 0)
        con.close()

    def test_um_local_desconhecido_rebenta(self):
        con = self.catalogo()
        with self.assertRaises(self.locais.LocalInvalido):
            self.locais.mover(con, "tst-001-100", 1, self.locais.COLECAO, "gaveta")
        con.close()

    def test_o_mesmo_request_id_nao_move_a_dobrar(self):
        con = self.catalogo()
        for _ in range(3):
            self.locais.mover(con, "tst-001-100", 1, self.locais.COLECAO,
                              self.locais.BINDER, source="test", request_id="r1")
        self.assertEqual(self.locais.em(con, self.locais.BINDER), {"tst-001-100": 1})
        con.close()

    def test_o_rasto_fica_no_locais_log(self):
        con = self.catalogo()
        self.locais.mover(con, "tst-001-100", 2, self.locais.COLECAO,
                          self.locais.deck_local("azir"), source="test")
        caminho = self.v.data / self.locais.LOG_NAME
        self.assertTrue(caminho.exists(), "sem rasto no data/locais.log")
        linhas = list(csv.DictReader(caminho.read_text(encoding="utf-8-sig")
                                     .splitlines()))
        self.assertEqual(len(linhas), 1)
        self.assertEqual(linhas[0]["printing_id"], "tst-001-100")
        self.assertEqual(linhas[0]["quantidade"], "2")
        self.assertEqual(linhas[0]["de"], "Coleção")
        self.assertTrue(linhas[0]["para"].startswith("Deck "))
        con.close()

    def test_o_log_leva_um_bom_so__nao_um_por_linha(self):
        """O `utf-8-sig` em modo append punha um BOM a cada escrita."""
        con = self.catalogo()
        for pid in ("tst-001-100", "tst-002-100"):
            self.locais.mover(con, pid, 1, self.locais.COLECAO,
                              self.locais.BINDER, source="test")
        bruto = (self.v.data / self.locais.LOG_NAME).read_text(encoding="utf-8")
        self.assertEqual(bruto.count("﻿"), 1)
        linhas = list(csv.DictReader(bruto.lstrip("﻿").splitlines()))
        self.assertEqual([x["printing_id"] for x in linhas],
                         ["tst-001-100", "tst-002-100"])
        con.close()

    def test_undo_devolve_a_copia_ao_sitio(self):
        con = self.catalogo()
        self.locais.mover(con, "tst-001-100", 2, self.locais.COLECAO,
                          self.locais.BINDER, source="test")
        res = self.locais.undo_last(con, source="test")
        self.assertIsNotNone(res)
        self.assertEqual(self.locais.em(con, self.locais.BINDER), {})
        self.assertEqual(self.locais.na_colecao(con)["tst-001-100"], 4)
        # Segundo undo: já não há nada por desfazer (o de compensação não conta).
        self.assertIsNone(self.locais.undo_last(con, source="test"))
        con.close()


class TestInvariante(Base):
    """`Σ(fora da Coleção) <= total`, mesmo quando ele tira cópias."""

    def test_tirar_uma_copia_que_esta_toda_num_deck_tira_a_do_deck(self):
        from riftvault import collection
        con = self.catalogo()
        self.locais.mover(con, "tst-002-100", 3, self.locais.COLECAO,
                          self.locais.deck_local("azir"), source="test")
        self.assertEqual(self.locais.na_colecao(con).get("tst-002-100", 0), 0)

        collection.adjust(con, "tst-002-100", -1, source="test")
        self.assertEqual(self.locais.em(con, self.locais.deck_local("azir")),
                         {"tst-002-100": 2})
        self.assertEqual(self.locais.na_colecao(con).get("tst-002-100", 0), 0)
        con.close()

    def test_tira_primeiro_do_binder(self):
        from riftvault import collection
        con = self.catalogo()
        self.locais.mover(con, "tst-001-100", 2, self.locais.COLECAO,
                          self.locais.deck_local("azir"), source="test")
        self.locais.mover(con, "tst-001-100", 2, self.locais.COLECAO,
                          self.locais.BINDER, source="test")
        collection.adjust(con, "tst-001-100", -1, source="test")
        self.assertEqual(self.locais.em(con, self.locais.BINDER), {"tst-001-100": 1})
        self.assertEqual(self.locais.em(con, self.locais.deck_local("azir")),
                         {"tst-001-100": 2})
        con.close()

    def test_a_saida_deixa_rasto(self):
        from riftvault import collection
        con = self.catalogo()
        self.locais.mover(con, "tst-002-100", 3, self.locais.COLECAO,
                          self.locais.BINDER, source="test")
        collection.adjust(con, "tst-002-100", -2, source="test")
        linhas = list(csv.DictReader(
            (self.v.data / self.locais.LOG_NAME).read_text(encoding="utf-8-sig")
            .splitlines()))
        self.assertEqual(linhas[-1]["para"], self.locais.SAIU)
        self.assertEqual(linhas[-1]["quantidade"], "2")
        con.close()

    def test_a_colecao_nunca_fica_negativa(self):
        from riftvault import collection
        con = self.catalogo()
        self.locais.mover(con, "tst-001-100", 4, self.locais.COLECAO,
                          self.locais.BINDER, source="test")
        collection.adjust(con, "tst-001-100", -4, source="test")
        self.assertEqual(self.locais.na_colecao(con).get("tst-001-100", 0), 0)
        self.assertEqual(self.locais.em(con, self.locais.BINDER), {})
        con.close()


class TestModoEdicao(Base):
    """Os endpoints de escrita do `riftvault serve`."""

    def cliente(self, con):
        from riftvault import server
        importlib.reload(server)
        con.close()
        server.app.config["TESTING"] = True
        return server.app.test_client()

    def test_marcar_sem_lista_e_400_e_nao_escreve(self):
        con = self.catalogo()
        c = self.cliente(con)
        r = c.post("/api/local/marcar", json={"para": "deck:azir", "linhas": []})
        self.assertEqual(r.status_code, 400)
        self.assertIn("confirmaste", r.get_json()["error"])
        r = c.post("/api/local/marcar", json={"para": "deck:azir"})
        self.assertEqual(r.status_code, 400)

        con = self.v.connect()
        self.assertEqual(
            con.execute("SELECT COUNT(*) FROM copy_locations").fetchone()[0], 0)
        con.close()

    def test_marcar_grava_so_as_linhas_que_vieram(self):
        con = self.catalogo()
        c = self.cliente(con)
        r = c.post("/api/local/marcar", json={
            "para": "deck:azir", "de": "colecao",
            "linhas": [{"printing_id": "tst-001-100", "qty": 2}]})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["copies"], 2)

        con = self.v.connect()
        self.assertEqual(self.locais.em(con, "deck:azir"), {"tst-001-100": 2})
        self.assertEqual(self.locais.na_colecao(con)["tst-001-100"], 2)
        con.close()

    def test_a_proposta_nao_escreve(self):
        con = self.catalogo()
        c = self.cliente(con)
        r = c.get("/api/local/propor/azir.json")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.get_json()["items"])
        con = self.v.connect()
        self.assertEqual(
            con.execute("SELECT COUNT(*) FROM copy_locations").fetchone()[0], 0)
        con.close()

    def test_desfazer_um_deck_que_nao_existe_e_404(self):
        con = self.catalogo()
        c = self.cliente(con)
        self.assertEqual(
            c.post("/api/local/desfazer-deck", json={"slug": "xpto"}).status_code, 404)

    def test_o_adjust_responde_com_o_numero_da_colecao(self):
        con = self.catalogo()
        self.locais.mover(con, "tst-001-100", 3, self.locais.COLECAO,
                          self.locais.deck_local("azir"), source="test")
        c = self.cliente(con)
        res = c.post("/api/adjust", json={"printing_id": "tst-001-100",
                                          "delta": 1}).get_json()
        self.assertEqual(res["qty"], 5, "o total físico")
        self.assertEqual(res["qty_colecao"], 2, "o que a Coleção conta")
        self.assertEqual({x["loc"]: x["qty"] for x in res["locations"]},
                         {"colecao": 2, "deck:azir": 3})


class TestCLI(Base):
    """`riftvault local` — os dois passos, e o desfazer."""

    def correr(self, *argv):
        import contextlib
        import io
        from riftvault import cli
        importlib.reload(cli)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_o_resumo_diz_que_esta_tudo_na_colecao(self):
        self.catalogo().close()
        code, out, _ = self.correr("local")
        self.assertEqual(code, 0)
        self.assertIn("Coleção", out)
        self.assertIn("por omissão está tudo na Coleção", out)

    def test_propor_nao_grava_e_marcar_grava(self):
        self.catalogo().close()
        code, out, _ = self.correr("local", "--deck", "azir", "--propor")
        self.assertEqual(code, 0)
        self.assertIn("Nada disto foi gravado", out)
        con = self.v.connect()
        self.assertEqual(
            con.execute("SELECT COUNT(*) FROM copy_locations").fetchone()[0], 0)
        con.close()

        code, out, _ = self.correr("local", "--deck", "azir", "--marcar",
                                   "tst-001-100:3")
        self.assertEqual(code, 0)
        self.assertIn("3 cópias marcadas", out)
        con = self.v.connect()
        self.assertEqual(self.locais.em(con, "deck:azir"), {"tst-001-100": 3})
        con.close()

    def test_mover_e_desfazer_deck(self):
        self.catalogo().close()
        code, out, _ = self.correr("local", "tst-002-100", "3",
                                   "--para", "deck:azir")
        self.assertEqual(code, 0)
        self.assertIn("Coleção -> Deck", out)

        code, out, _ = self.correr("local", "--desfazer-deck", "azir")
        self.assertEqual(code, 0)
        self.assertIn("passaram ao binder Decks/Venda", out)
        con = self.v.connect()
        self.assertEqual(self.locais.em(con, self.locais.BINDER),
                         {"tst-002-100": 3})
        con.close()

    def test_o_deck_diz_de_onde_vem_o_que_tem(self):
        self.catalogo().close()
        code, out, _ = self.correr("deck", "azir")
        self.assertEqual(code, 0)
        self.assertIn("na Coleção 7", out)
        self.assertIn("a comprar 0", out)
        self.assertNotIn("duplicado", out, "a Coleção conta desde 2026-09-11")

    def test_o_undo_devolve_a_copia(self):
        self.catalogo().close()
        self.correr("local", "tst-001-100", "2", "--para", "binder")
        code, out, _ = self.correr("local", "--undo")
        self.assertEqual(code, 0)
        con = self.v.connect()
        self.assertEqual(self.locais.em(con, self.locais.BINDER), {})
        con.close()


class TestNomes(Base):
    """A escrita dos locais é a dele, e um valor novo rebenta."""

    def test_as_escritas_aceites(self):
        con = self.catalogo()
        n = self.locais.normalizar
        self.assertEqual(n("colecao"), "colecao")
        self.assertEqual(n("Coleção"), "colecao")
        self.assertEqual(n("binder"), "binder")
        self.assertEqual(n("Decks/Venda"), "binder")
        self.assertEqual(n("deck:azir"), "deck:azir")
        self.assertEqual(n("azir", {"azir"}), "deck:azir")
        with self.assertRaises(self.locais.LocalInvalido):
            n("azir")           # sem saber que é um deck, não se adivinha
        con.close()

    def test_os_rotulos(self):
        self.assertEqual(self.locais.rotulo("colecao"), "Coleção")
        self.assertEqual(self.locais.rotulo("binder"), "Binder Decks/Venda")
        self.assertEqual(self.locais.rotulo("deck:azir"), "Deck azir")
        self.assertEqual(self.locais.rotulo("deck:azir", {"azir": "Azir · Brutalizer"}),
                         "Deck Azir · Brutalizer")


if __name__ == "__main__":
    unittest.main()

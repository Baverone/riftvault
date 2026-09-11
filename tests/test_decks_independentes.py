"""Decks independentes e a Coleção com prioridade (André, 2026-09-11).

*"Nos decks, quero que apresentes as faltas todas, cada deck será independente.
A coleção terá obrigatoriamente que ter as cartas também e terá sempre
prioridade. Então se a coleção está a usar as cartas, o deck irá precisar de
pedir as cartas também, e se o deck depois precisar, também será necessário
comprar. Isto apenas é válido para comuns, incomuns."*

São duas regras numa frase, e cada uma tem aqui um caso que parte se ela for
apagada:

  INDEPENDÊNCIA — o que está noutro deck não monta este. Diz-se onde está
                  (`shared`), mas a falta é a mesma. Vale para TODAS as
                  raridades.
  COLEÇÃO PRIMEIRO — nas comuns e incomuns a cópia dos binders de coleção não
                  existe para o deck: nem monta, nem se lê «na Coleção — mover
                  ou comprar». Nas raras e acima fica como estava (2026-09-10).
"""

from __future__ import annotations

import importlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.fixture import Vault

# Um deck que pede uma comum, uma rara e o Legend.
DECK_AZIR = """Legend:
1 Emperor of the Sands

MainDeck:
3 Defy
3 Brutalizer
"""

# Segundo deck, com Champion próprio para o nome de mostrar não colidir.
DECK_ORNN = """Legend:
1 Emperor of the Sands

Champion:
1 Spirit Blade

MainDeck:
3 Defy
3 Brutalizer
"""


class Base(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.close)
        from riftvault import decks, faltas, locais, metrics, venda
        for m in (metrics, decks, locais, faltas, venda):
            importlib.reload(m)
        self.decks, self.locais, self.faltas, self.venda = decks, locais, faltas, venda

    def catalogo(self, decks_txt=(("azir", DECK_AZIR),)):
        """Duas comuns, uma rara e um Legend raro; tudo na Coleção."""
        from riftvault import collection
        con = self.v.connect()
        # `Defy` é COMUM: é nela que a regra nova se vê.
        self.v.add_printing(con, "tst-001-100", "TST", 1, "Defy", size=100,
                            rarity="common")
        # `Brutalizer` é RARA: mantém a leitura de 2026-09-10.
        self.v.add_printing(con, "tst-002-100", "TST", 2, "Brutalizer", size=100,
                            rarity="rare")
        self.v.add_printing(con, "tst-003-100", "TST", 3, "Emperor of the Sands",
                            card_type="Legend", size=100, rarity="rare")
        self.v.add_printing(con, "tst-004-100", "TST", 4, "Spirit Blade", size=100,
                            rarity="uncommon")
        self.v.rebuild(con)
        for pid, n in (("tst-001-100", 3), ("tst-002-100", 3),
                       ("tst-003-100", 1), ("tst-004-100", 1)):
            collection.adjust(con, pid, n, source="test")
        for slug, txt in decks_txt:
            self.v.write_deck(slug, txt)
        self.decks.import_all(con, log=lambda *_: None)
        return con

    def carta(self, con, deck_id, nome):
        p = self.decks.deck_payload(con, deck_id)
        return next(c for s in p["sections"] for c in s["cards"] if c["name"] == nome)


# ---------------------------------------------------------------------------


class TestColecaoFicaComAsComuns(Base):
    """Nas comuns e incomuns a Coleção tem prioridade — o deck compra as suas."""

    def test_uma_comum_na_colecao_nao_serve_o_deck_e_vai_a_comprar(self):
        con = self.catalogo()
        defy = self.carta(con, 1, "Defy")
        self.assertEqual(defy["have"], 0, "a Coleção não monta o deck")
        self.assertEqual(defy["na_colecao"], 0,
                         "nem sequer se lê «na Coleção»: para o deck não existe")
        self.assertEqual(defy["missing"], 3, "compra-se")
        con.close()

    def test_nao_diz_que_nao_tem_o_que_tem__diz_que_a_colecao_fica_com_ela(self):
        """«não tenho» seria mentira: ele tem 3 Defy no binder de coleção."""
        con = self.catalogo()
        defy = self.carta(con, 1, "Defy")
        self.assertEqual(defy["colecao_fica"], 3)
        self.assertEqual(defy["missing"], 3, "e compra na mesma: não desconta")
        d = self.decks.decks_index(con)[0]
        self.assertEqual(d["colecao_fica"], 3)
        con.close()

    def test_uma_rara_na_colecao_le_se_na_colecao__mover_ou_comprar(self):
        con = self.catalogo()
        brut = self.carta(con, 1, "Brutalizer")
        self.assertEqual(brut["have"], 0)
        self.assertEqual(brut["na_colecao"], 3, "é a leitura de 2026-09-10")
        self.assertEqual(brut["missing"], 3)
        con.close()

    def test_a_colecao_nao_perde_as_comuns_quando_um_deck_as_pede(self):
        """A cópia continua na Coleção — a regra é de leitura, não de mudança."""
        con = self.catalogo()
        antes = self.locais.na_colecao(con)
        self.decks.allocate(con)
        self.assertEqual(self.locais.na_colecao(con), antes)
        self.assertEqual(antes.get("tst-001-100"), 3)
        con.close()

    def test_uma_comum_no_binder_serve_o_deck(self):
        con = self.catalogo()
        self.locais.mover(con, "tst-001-100", 3, self.locais.COLECAO,
                          self.locais.BINDER, source="test")
        defy = self.carta(con, 1, "Defy")
        self.assertEqual(defy["no_binder"], 3, "o binder Decks/Venda monta decks")
        self.assertEqual(defy["missing"], 0)
        con.close()

    def test_uma_comum_ja_sleevada_no_deck_serve_o_deck(self):
        con = self.catalogo()
        self.locais.mover(con, "tst-001-100", 3, self.locais.COLECAO,
                          self.locais.deck_local("azir"), source="test")
        defy = self.carta(con, 1, "Defy")
        self.assertEqual(defy["no_deck"], 3)
        self.assertEqual(defy["missing"], 0)
        con.close()

    def test_o_excedente_da_colecao_tambem_nao_serve(self):
        """Ter 5 de uma comum de playset 3 não dá 2 ao deck: é comprar.

        É a outra face do que a Venda faz — o excedente é dela, e é por isso
        que a mesma cópia pode estar «a vender» e o deck estar a comprar.
        """
        from riftvault import collection
        con = self.catalogo()
        collection.adjust(con, "tst-001-100", 2, source="test")   # 5 na Coleção
        defy = self.carta(con, 1, "Defy")
        self.assertEqual(defy["missing"], 3)
        self.assertEqual(defy["na_colecao"], 0)
        con.close()

    def test_desligar_a_regra_devolve_a_leitura_antiga(self):
        """`decks_colecao_primeiro: []` e a comum volta a ser «na Coleção».

        O config de teste é um ficheiro NOVO, na pasta descartável, e o
        `CONFIG_PATH` volta ao que era no fim. **O fixture não isola o
        `riftvault_config.json` do repositório** — escrever nele (ou apagá-lo)
        estraga o do André. Aconteceu a 2026-09-11, ao escrever este teste.
        """
        con = self.catalogo()
        cfg = self.v.config
        tmp = self.v.root / "config-sem-a-regra.json"
        tmp.write_text('{"decks_colecao_primeiro": []}', encoding="utf-8")
        antigo = cfg.CONFIG_PATH
        cfg.CONFIG_PATH = tmp
        cfg.reload()
        try:
            defy = self.carta(con, 1, "Defy")
            self.assertEqual(defy["na_colecao"], 3)
        finally:
            cfg.CONFIG_PATH = antigo
            cfg.reload()
        con.close()


class TestRaridadeDaCarta(Base):
    """A raridade é a da impressão CANÓNICA, não a da reimpressão showcase."""

    def test_a_reimpressao_showcase_nao_torna_a_comum_rara(self):
        con = self.catalogo()
        # A mesma carta lógica reimpressa com número próprio e raridade
        # showcase — a ARMADILHA 2 do CLAUDE.md.
        self.v.add_printing(con, "tst-120-100", "TST", 120, "Defy", size=100,
                            rarity="showcase", api_sort=120)
        self.v.rebuild(con)
        self.assertEqual(self.decks.raridade_por_carta(con)["defy"], "common")
        con.close()

    def test_sem_raridade_conhecida_trata_se_como_rara(self):
        """Uma carta por classificar não pode mudar de regra em silêncio."""
        con = self.catalogo()
        con.execute("UPDATE catalog.printings SET rarity=NULL, base_rarity=NULL "
                    "WHERE printing_id='tst-001-100'")
        self.assertNotIn("defy", self.decks.raridade_por_carta(con))
        defy = self.carta(con, 1, "Defy")
        self.assertEqual(defy["na_colecao"], 3, "sem raridade, é a leitura das raras")
        con.close()


class TestDecksIndependentes(Base):
    """O que está noutro deck não monta este — diz onde está, e compra-se."""

    def test_uma_comum_noutro_deck_nao_serve_e_compra_se(self):
        con = self.catalogo((("azir", DECK_AZIR), ("ornn", DECK_ORNN)))
        self.locais.mover(con, "tst-001-100", 3, self.locais.COLECAO,
                          self.locais.deck_local("azir"), source="test")
        idx = {d["slug"]: d for d in self.decks.decks_index(con)}
        defy = self.carta(con, idx["ornn"]["id"], "Defy")
        self.assertEqual(defy["have"], 0)
        self.assertEqual(defy["missing"], 3, "o ornn compra as dele")
        self.assertEqual(defy["shared"]["em"][0]["deck"].split(" · ")[0],
                         "Emperor of the Sands")
        con.close()

    def test_o_binder_continua_a_distribuir_se_por_prioridade(self):
        """O stock livre é um só: o deck 1 serve-se, o deck 2 compra."""
        con = self.catalogo((("azir", DECK_AZIR), ("ornn", DECK_ORNN)))
        self.locais.mover(con, "tst-001-100", 3, self.locais.COLECAO,
                          self.locais.BINDER, source="test")
        idx = {d["slug"]: d for d in self.decks.decks_index(con)}
        self.assertEqual(idx["azir"]["no_binder"], 3)
        self.assertEqual(idx["ornn"]["no_binder"], 0)
        self.assertEqual(self.carta(con, idx["ornn"]["id"], "Defy")["missing"], 3)
        con.close()

    def test_a_falta_e_a_mesma_com_ou_sem_o_outro_deck(self):
        """A prova da independência: acrescentar um deck não muda o outro."""
        con = self.catalogo()
        so_um = self.decks.decks_index(con)[0]["missing"]
        self.v.write_deck("ornn", DECK_ORNN)
        self.decks.import_all(con, log=lambda *_: None)
        idx = {d["slug"]: d for d in self.decks.decks_index(con)}
        self.assertEqual(idx["azir"]["missing"], so_um)
        # E o segundo pede o seu por inteiro: 3 Defy + 3 Brutalizer + 1 Legend
        # (a Spirit Blade está na Coleção e é incomum, por isso também se compra).
        self.assertEqual(idx["ornn"]["missing"], 8)
        con.close()

    def test_a_lista_de_compra_do_deck_leva_as_faltas_todas(self):
        con = self.catalogo((("azir", DECK_AZIR), ("ornn", DECK_ORNN)))
        idx = {d["slug"]: d for d in self.decks.decks_index(con)}
        copias = sum(g["copies"] for g in
                     self.decks.missing_by_set(con, idx["ornn"]["id"]))
        self.assertEqual(copias, idx["ornn"]["missing"])
        con.close()


class TestFaltasPorDeck(Base):
    """A aba «Por deck» e a wantlist contam o mesmo que a página do deck."""

    def test_cada_deck_pede_o_seu(self):
        con = self.catalogo((("azir", DECK_AZIR), ("ornn", DECK_ORNN)))
        por_deck = {d["name"]: d for d in self.faltas.por_deck(con)}
        idx = {d["name"]: d for d in self.decks.decks_index(con)}
        for nome, d in por_deck.items():
            self.assertEqual(d["copies"], idx[nome]["missing"],
                             f"{nome}: a aba tem de contar o mesmo que o deck")
        con.close()

    def test_o_que_vem_a_caminho_desconta__por_prioridade(self):
        """Uma encomenda é uma cópia só: serve o deck principal, não os dois."""
        from riftvault import pending
        con = self.catalogo((("azir", DECK_AZIR), ("ornn", DECK_ORNN)))
        pending.add(con, "tst-001-100", 3)
        por_deck = {d["name"]: d for d in self.faltas.por_deck(con)}
        idx = {d["slug"]: d for d in self.decks.decks_index(con)}
        nome_azir = idx["azir"]["name"]
        nome_ornn = idx["ornn"]["name"]
        self.assertEqual(por_deck[nome_azir]["copies"],
                         idx["azir"]["missing"] - 3)
        self.assertEqual(por_deck[nome_ornn]["copies"], idx["ornn"]["missing"])
        con.close()

    def test_a_wantlist_do_deck_tem_uma_linha_por_carta_em_falta(self):
        con = self.catalogo()
        d = self.faltas.por_deck(con)[0]
        wl = self.faltas.wantlist(d["by_set"])
        self.assertEqual(wl["lines"], d["cards"])
        self.assertIn("3 Defy", wl["text"])
        con.close()


class TestVendaCoerente(Base):
    """A Venda e as faltas dos decks não se contradizem."""

    def test_uma_comum_do_binder_que_um_deck_pede_nao_e_excedente(self):
        con = self.catalogo()
        self.locais.mover(con, "tst-001-100", 3, self.locais.COLECAO,
                          self.locais.BINDER, source="test")
        itens = {x["printing_id"]: x for x in self.venda.listar(con)["items"]}
        self.assertNotIn("tst-001-100", itens,
                         "o deck está a usá-las: não se vendem")
        con.close()

    def test_a_comum_da_colecao_acima_do_alvo_continua_a_ser_excedente(self):
        """E o deck compra-a na mesma — é a consequência da regra dele.

        A mesma cópia pode ler-se «a vender» (é da Coleção, acima do alvo) e o
        deck estar a comprar outra. Não é contradição: é o preço de a Coleção
        ter prioridade. Fica medido, para não passar despercebido.
        """
        from riftvault import collection
        con = self.catalogo()
        collection.adjust(con, "tst-001-100", 3, source="test")   # 6, alvo 3
        # A sequência do master set só entra na venda com o âmbito largo.
        sobra = {x["printing_id"]: x for x in
                 self.venda.excedente(con, incluir_master=True)}
        self.assertEqual(sobra["tst-001-100"]["from_colecao"], 3)
        self.assertEqual(self.carta(con, 1, "Defy")["missing"], 3)
        con.close()

    def test_nada_sai_da_base(self):
        con = self.catalogo()
        antes = con.execute("SELECT COALESCE(SUM(qty),0) FROM copies").fetchone()[0]
        self.venda.listar(con)
        self.decks.allocate(con)
        self.faltas.por_deck(con)
        self.assertEqual(
            con.execute("SELECT COALESCE(SUM(qty),0) FROM copies").fetchone()[0],
            antes)
        con.close()


if __name__ == "__main__":
    unittest.main(verbosity=1)

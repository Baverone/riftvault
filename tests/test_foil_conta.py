# -*- coding: utf-8 -*-
"""O FOIL CONTA: para o valor e para o master set (André, 2026-09-26).

Resposta dele às duas perguntas que ficaram em aberto de manhã, quando o foil
passou a somar-se ao normal: *"contam para o valor sim, e contabilizas tambem
como parte do master set"*. As duas chaves passaram a `true`, e a terceira
nasceu com elas.

O que este ficheiro fixa:

  1. AS TRÊS CHAVES  — `conta_para_coleccao` e `conta_para_valor` a `true`,
     `entra_no_a_mais` a `false`, no config real e no `config.DEFAULTS`.
  2. PARA O MASTER SET  — o que a impressão TEM passa a ser `qty + qty_foil`:
     os três níveis, o denominador, a grelha, as Faltas e as wantlists.
  3. PARA O VALOR  — ao PREÇO DA NORMAL, porque não há preço de foil no
     catálogo. O `prices.valor_dos_foils` separa as que levam ressalva (o valor
     é um piso) das que já têm preço de foil (`from_foil`), e conta-as.
  4. NO «A MAIS» OS FOILS NÃO ENTRAM NO QUE SOBRA  — a consequência que ele
     decidiu: 3 normais + 3 foil contra um alvo de 3 não são «3 a mais para
     vender». O excedente conta primeiro as normais; `scope.foil` diz quantas
     ficaram de fora.
  5. NOS DECKS AS NORMAIS SERVEM PRIMEIRO  — um deck joga foil ou normal, mas
     não se lhe tira um foil havendo normal. `decks.foils_nos_decks` diz
     quantas e de quem.
  6. AS TRÊS CAUTELAS DO MESMO TIPO  — o `propor_deck` (grava em
     `copy_locations`, que só conta normais), a Venda (o «marcar como vendidas»
     baixa o `copies.qty`) e o `−` da grelha.
  7. A FRONTEIRA CONTINUA DE PÉ  — nenhum módulo de contas importa o `foil`, e
     a coluna do foil só se lê nos dois funis.
  8. A INTERFACE DIZ  — que os foils estão contados ao preço da normal.

Corre contra pastas temporárias e um config temporário — nunca contra o
`data/` nem o `riftvault_config.json` reais.
"""
from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.fixture import REPO, Vault  # noqa: E402

APP = REPO / "riftvault" / "web" / "app.js"
CSS = REPO / "riftvault" / "web" / "style.css"


class Base(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.close)
        from riftvault import (a_mais, a_subir, collection, config, db, decks,
                               faltas, faltas_edicao, foil, locais, metrics,
                               painel, pending, prices, proprias, venda)
        for m in (locais, metrics, foil, painel, decks, proprias, a_subir,
                  faltas_edicao, a_mais, pending, faltas, prices, venda):
            importlib.reload(m)
        self.config, self.db, self.foil, self.locais = config, db, foil, locais
        self.metrics, self.painel, self.decks = metrics, painel, decks
        self.a_subir, self.faltas_edicao, self.a_mais = a_subir, faltas_edicao, a_mais
        self.pending, self.faltas, self.prices = pending, faltas, prices
        self.collection, self.proprias, self.venda = collection, proprias, venda
        # A omissão dos testes: os dois botões LIGADOS, que é o que ele mandou.
        self.cfg_foil({"conta_para_coleccao": True, "conta_para_valor": True,
                       "entra_no_a_mais": False})

    def cfg_foil(self, foil_extra: dict, extra: dict | None = None):
        caminho = self.v.root / "config.json"
        caminho.write_text(json.dumps({
            "foil": {"raridades": ["common", "uncommon"], "edicoes_fora": ["OGS"],
                     **foil_extra},
            # Os decks jogam só a base (2026-09-21), como no config real.
            "decks": {"so_base": True, "so_normais_excepto": [],
                      "contar_runas": False},
            **(extra or {})}), encoding="utf-8")
        os.environ["RIFTVAULT_CONFIG"] = str(caminho)
        importlib.reload(self.config)
        self.config.load.cache_clear()

        def repor():
            os.environ["RIFTVAULT_CONFIG"] = str(
                Path(tempfile.gettempdir()) / "riftvault-nao-existe.json")
            importlib.reload(self.config)
            self.config.load.cache_clear()

        self.addCleanup(repor)

    def catalogo(self, precos=True):
        """A edição TST: uma comum a 3 cópias (playset feito), uma incomum a 1,
        uma comum a 0, uma rara (fora do âmbito do foil) e um Legend.

        Preços: a comum 11 cêntimos (o mínimo do CardTrader), a incomum 25.
        A `tst-005-100` tem `from_foil = 1`: o CardTrader só a lista em foil.
        """
        con = self.v.connect()
        v = self.v
        v.add_printing(con, "tst-001-100", "TST", 1, "Defy", rarity="common", size=100)
        v.add_printing(con, "tst-002-100", "TST", 2, "Scout", rarity="uncommon", size=100)
        v.add_printing(con, "tst-003-100", "TST", 3, "Brutalizer", rarity="rare", size=100)
        v.add_printing(con, "tst-004-100", "TST", 4, "Emperor of the Sands",
                       card_type="Legend", rarity="epic", size=100)
        v.add_printing(con, "tst-005-100", "TST", 5, "Sabotage", rarity="common", size=100)
        v.rebuild(con)
        if precos:
            for pid, cents, ff in (("tst-001-100", 11, 0), ("tst-002-100", 25, 0),
                                   ("tst-003-100", 900, 0), ("tst-004-100", 4000, 0),
                                   ("tst-005-100", 100, 1)):
                con.execute("INSERT INTO catalog.price_latest "
                            "(printing_id, price_cents, from_foil) VALUES (?,?,?)",
                            (pid, cents, ff))
        for pid, n in (("tst-001-100", 3), ("tst-002-100", 1), ("tst-003-100", 1)):
            self.collection.adjust(con, pid, n, source="test")
        self.addCleanup(con.close)
        return con

    # -- atalhos ------------------------------------------------------------
    def tile(self, con, pid, set_id="TST"):
        for g in self.metrics.set_payload(con, set_id)["groups"]:
            for p in g["printings"]:
                if p["id"] == pid:
                    return p
        self.fail(f"{pid} não está na grelha")

    def niveis(self, con):
        n = self.metrics.niveis_payload(con, self.config.load())
        return [(l["k"], l["done"], l["total"], l["missing"]) for l in n["levels"]]


# ---------------------------------------------------------------------------
# 1. As três chaves
# ---------------------------------------------------------------------------


class TestAsTresChaves(Base):
    def test_o_config_real_tem_as_duas_a_true_e_a_do_a_mais_a_false(self):
        cfg = json.loads((REPO / "riftvault_config.json").read_text(encoding="utf-8"))
        self.assertIs(cfg["foil"]["conta_para_coleccao"], True)
        self.assertIs(cfg["foil"]["conta_para_valor"], True)
        self.assertIs(cfg["foil"]["entra_no_a_mais"], False)

    def test_os_defaults_dizem_o_mesmo(self):
        """Um riftvault sem ficheiro de config mede o que ele decidiu, não o de
        antes — a regra do `"*"` das signatures (2026-09-09)."""
        d = self.config.DEFAULTS["foil"]
        self.assertIs(d["conta_para_coleccao"], True)
        self.assertIs(d["conta_para_valor"], True)
        self.assertIs(d["entra_no_a_mais"], False)

    def test_as_tres_leituras_de_referencia(self):
        self.assertTrue(self.foil.conta_para_coleccao())
        self.assertTrue(self.foil.conta_para_valor())
        self.assertFalse(self.foil.entra_no_a_mais())
        self.assertFalse(self.a_mais.foil_no_excedente())

    def test_sem_a_chave_do_a_mais_e_false(self):
        """A omissão é NÃO entrar no que sobra: um config antigo não pode
        começar a sugerir a venda dos foils."""
        self.assertFalse(self.foil.entra_no_a_mais({}))
        self.assertFalse(self.foil.entra_no_a_mais({"foil": {}}))
        self.assertFalse(self.a_mais.foil_no_excedente({"foil": {}}))

    def test_o_resumo_do_foil_diz_o_estado_das_tres(self):
        con = self.catalogo()
        r = self.foil.resumo(con)
        self.assertTrue(r["conta_para_coleccao"])
        self.assertTrue(r["conta_para_valor"])
        self.assertFalse(r["entra_no_a_mais"])
        t = self.foil.texto(r, [{"id": "TST", "name": "TST"}])
        self.assertIn("CONTAM", t)
        self.assertIn("AO PREÇO DA NORMAL", t)
        self.assertIn("PISO", t)
        self.assertIn("NÃO entram no que sobra", t)


# ---------------------------------------------------------------------------
# 2. Para o MASTER SET: o que a impressão tem é `qty + qty_foil`
# ---------------------------------------------------------------------------


class TestContaParaAColeccao(Base):
    def test_o_tile_diz_normais_mais_foil(self):
        con = self.catalogo()
        self.assertEqual(self.tile(con, "tst-001-100")["qty"], 3)
        self.foil.ajustar(con, "tst-001-100", 3, source="test")
        t = self.tile(con, "tst-001-100")
        self.assertEqual(t["qty"], 6, "3 normais + 3 foil = 6 cópias")
        self.assertEqual(t["qty_total"], 3, "as NORMAIS físicas não mexeram")
        self.assertEqual(t["foil"], 3)

    def test_uma_foil_fecha_o_playset(self):
        """A `tst-002-100` tem 1 normal de um alvo de 3. Duas foils fecham-no."""
        con = self.catalogo()
        self.assertEqual(self.tile(con, "tst-002-100")["qty"], 1)
        antes = self.niveis(con)
        self.foil.ajustar(con, "tst-002-100", 2, source="test")
        self.assertEqual(self.tile(con, "tst-002-100")["qty"], 3)
        depois = self.niveis(con)
        # Sobe no nível 2 e no 3; no 1 já estava feita.
        self.assertEqual([d for _, d, _, _ in antes][0],
                         [d for _, d, _, _ in depois][0], "o nível 1 não mexe")
        self.assertEqual([d for _, d, _, _ in depois][1],
                         [d for _, d, _, _ in antes][1] + 1, "sobe no nível 2")
        self.assertEqual([d for _, d, _, _ in depois][2],
                         [d for _, d, _, _ in antes][2] + 1, "e no playset")

    def test_uma_carta_so_em_foil_passa_a_contar(self):
        """0 normais + 2 foil: a Coleção passa a ter 2 cópias dela, e o nível 1
        conta-a. Era impossível antes de 2026-09-26 (o foil era uma fatia)."""
        con = self.catalogo()
        self.assertEqual(self.tile(con, "tst-005-100")["qty"], 0)
        n1_antes = self.niveis(con)[0][1]
        self.foil.ajustar(con, "tst-005-100", 2, source="test")
        t = self.tile(con, "tst-005-100")
        self.assertEqual((t["qty"], t["qty_total"], t["foil"]), (2, 0, 2))
        self.assertEqual(self.niveis(con)[0][1], n1_antes + 1)

    def test_o_denominador_nao_mexe(self):
        """Os foils são CÓPIAS, não impressões: o denominador é do catálogo."""
        con = self.catalogo()
        antes = self.niveis(con)[0][2]
        self.foil.ajustar(con, "tst-001-100", 9, source="test")
        self.foil.ajustar(con, "tst-005-100", 4, source="test")
        self.assertEqual(self.niveis(con)[0][2], antes)

    def test_as_faltas_e_a_wantlist_descontam_as_foils(self):
        con = self.catalogo()
        cfg = self.config.load()
        antes = self.a_subir.wantlist(con, cfg=cfg)
        # A `tst-002-100` falta 2 (tem 1 de 3). Duas foils e deixa de faltar.
        self.assertIn("Scout", antes["text"])
        self.foil.ajustar(con, "tst-002-100", 2, source="test")
        depois = self.a_subir.wantlist(con, cfg=cfg)
        self.assertNotIn("Scout", depois["text"], "coberta por foils")
        self.assertEqual(depois["copies"], antes["copies"] - 2)
        fe = self.faltas_edicao.payload(con, cfg)
        cks = [c["code"] for s in fe["sets"] for b in s["blocks"] for c in b["items"]]
        self.assertFalse([c for c in cks if c.startswith("TST-002")])

    def test_desligar_a_chave_volta_a_ignorar_as_foils(self):
        con = self.catalogo()
        self.foil.ajustar(con, "tst-001-100", 3, source="test")
        self.assertEqual(self.tile(con, "tst-001-100")["qty"], 6)
        self.cfg_foil({"conta_para_coleccao": False, "conta_para_valor": True})
        self.assertEqual(self.tile(con, "tst-001-100")["qty"], 3,
                         "com a chave desligada a Coleção só conta as normais")

    def test_as_foils_de_uma_retirada_nao_contam(self):
        """Uma runa em Alt Art é RETIRADA (2026-09-17): *"nao incluas em nada"*.
        As foils dela seguem a regra dela, não a do foil."""
        con = self.v.connect()
        self.v.add_printing(con, "tst-007-100", "TST", 7, "Fury Rune",
                            card_type="Rune", rarity="common", size=100)
        self.v.add_printing(con, "tst-007a-100", "TST", 7, "Fury Rune", variant="a",
                            kind="alt_art", card_type="Rune", rarity="showcase",
                            base_rarity="common", size=100)
        self.v.rebuild(con)
        self.addCleanup(con.close)
        self.cfg_foil({"conta_para_coleccao": True, "conta_para_valor": True},
                      {"runas_especiais": {"tipos": ["Rune"], "excepto": ["base"],
                                           "retiradas": ["a"]}})
        self.collection.adjust(con, "tst-007a-100", 1, source="test")
        # A retirada não está na grelha, com ou sem foil.
        ids = [p["id"] for g in self.metrics.set_payload(con, "TST")["groups"]
               for p in g["printings"]]
        self.assertNotIn("tst-007a-100", ids)


# ---------------------------------------------------------------------------
# 3. Para o VALOR, ao preço da normal
# ---------------------------------------------------------------------------


class TestContaParaOValor(Base):
    def test_o_valor_sobe_ao_preco_da_normal(self):
        con = self.catalogo()
        antes = self.prices.collection_value(con)
        # 3 foils da comum a 11 cêntimos = 33.
        self.foil.ajustar(con, "tst-001-100", 3, source="test")
        depois = self.prices.collection_value(con)
        self.assertEqual(depois["cents"] - antes["cents"], 33)
        self.assertEqual(depois["copias"] - antes["copias"], 3)

    def test_a_repartição_diz_quantas_levam_ressalva(self):
        con = self.catalogo()
        self.foil.ajustar(con, "tst-001-100", 3, source="test")   # preço normal
        self.foil.ajustar(con, "tst-002-100", 2, source="test")   # preço normal
        self.foil.ajustar(con, "tst-005-100", 4, source="test")   # from_foil = 1
        f = self.prices.valor_dos_foils(con)
        self.assertEqual(f["copies"], 9)
        n, pf = f["ao_preco_da_normal"], f["preco_de_foil"]
        self.assertEqual((n["printings"], n["copies"]), (2, 5))
        self.assertEqual(n["cents"], 3 * 11 + 2 * 25)
        self.assertEqual((pf["printings"], pf["copies"]), (1, 4),
                         "a que o CardTrader só lista em foil já tem preço de foil")
        self.assertEqual(pf["cents"], 4 * 100)
        self.assertEqual(f["cents"], n["cents"] + pf["cents"])
        self.assertEqual(f["sem_preco"], {"printings": 0, "copies": 0})

    def test_uma_foil_sem_preco_nao_conta_e_diz_se(self):
        con = self.catalogo(precos=False)
        con.execute("INSERT INTO catalog.price_latest (printing_id, price_cents) "
                    "VALUES ('tst-001-100', 11)")
        self.foil.ajustar(con, "tst-001-100", 1, source="test")
        self.foil.ajustar(con, "tst-002-100", 3, source="test")   # sem preço
        f = self.prices.valor_dos_foils(con)
        self.assertEqual(f["sem_preco"], {"printings": 1, "copies": 3})
        self.assertEqual(f["copies"], 4)
        self.assertEqual(f["cents"], 11, "só a que tem preço conta")

    def test_a_repartição_vai_dentro_do_valor(self):
        """Nenhuma vista pode mostrar o total sem a ressalva: o `foils` vem
        DENTRO do `collection_value`, não à parte."""
        con = self.catalogo()
        self.foil.ajustar(con, "tst-001-100", 2, source="test")
        v = self.prices.collection_value(con)
        self.assertIsNotNone(v["foils"])
        self.assertEqual(v["foils"]["copies"], 2)
        idx = self.metrics.index_payload(con)
        self.assertEqual(idx["value"]["foils"]["copies"], 2)

    def test_com_a_chave_desligada_nao_ha_reparticao_nem_valor(self):
        con = self.catalogo()
        self.foil.ajustar(con, "tst-001-100", 3, source="test")
        antes = self.prices.collection_value(con)["cents"]
        self.cfg_foil({"conta_para_coleccao": True, "conta_para_valor": False})
        v = self.prices.collection_value(con)
        self.assertIsNone(v["foils"], "sem foils no valor não há nada a ressalvar")
        self.assertEqual(v["cents"], antes - 33)

    def test_os_dois_botoes_sao_separados(self):
        """Ligar um não liga o outro — há teste porque é a forma de ele voltar
        atrás em metade da decisão sem mexer na outra."""
        con = self.catalogo()
        self.foil.ajustar(con, "tst-002-100", 2, source="test")
        self.cfg_foil({"conta_para_coleccao": True, "conta_para_valor": False})
        self.assertEqual(self.tile(con, "tst-002-100")["qty"], 3, "conta na Coleção")
        self.assertIsNone(self.prices.valor_dos_foils(con), "e não no valor")
        self.cfg_foil({"conta_para_coleccao": False, "conta_para_valor": True})
        self.assertEqual(self.tile(con, "tst-002-100")["qty"], 1, "não conta na Coleção")
        self.assertEqual(self.prices.valor_dos_foils(con)["copies"], 2, "e conta no valor")


# ---------------------------------------------------------------------------
# 4. No «A mais», os foils NÃO entram no que sobra
# ---------------------------------------------------------------------------


class TestOAMaisNaoVendeOsFoils(Base):
    def test_tres_normais_e_tres_foil_com_alvo_tres_nao_sao_a_mais(self):
        """O caso que ele nomeou, à letra."""
        con = self.catalogo()
        self.foil.ajustar(con, "tst-001-100", 3, source="test")
        # A Coleção diz 6 de 3...
        self.assertEqual(self.tile(con, "tst-001-100")["qty"], 6)
        # ... e o «A mais» não diz nada.
        itens = self.a_mais.excedente(con, self.config.load())
        self.assertNotIn("tst-001-100", [x["printing_id"] for x in itens])

    def test_o_excedente_e_exactamente_o_mesmo_com_e_sem_foils(self):
        con = self.catalogo()
        cfg = self.config.load()
        # Uma cópia normal a mais, para o excedente não ser vazio.
        self.collection.adjust(con, "tst-001-100", 2, source="test")   # 5 normais
        antes = [(x["printing_id"], x["extra"], x["have"])
                 for x in self.a_mais.excedente(con, cfg)]
        self.assertTrue(antes, "a fotografia não pode ser de zeros")
        self.foil.ajustar(con, "tst-001-100", 4, source="test")
        self.foil.ajustar(con, "tst-002-100", 5, source="test")
        depois = [(x["printing_id"], x["extra"], x["have"])
                  for x in self.a_mais.excedente(con, cfg)]
        self.assertEqual(depois, antes, "9 foils e o que sobra é o mesmo")

    def test_o_excedente_conta_primeiro_as_normais(self):
        """5 normais de um alvo de 3 são 2 a mais — com foils ou sem elas."""
        con = self.catalogo()
        self.collection.adjust(con, "tst-001-100", 2, source="test")   # 5 normais
        self.foil.ajustar(con, "tst-001-100", 3, source="test")
        x = [i for i in self.a_mais.excedente(con, self.config.load())
             if i["printing_id"] == "tst-001-100"][0]
        self.assertEqual(x["extra"], 2)
        self.assertEqual(x["foil"], 3, "diz-se que as 3 foils ficaram de fora")

    def test_o_scope_diz_quantas_ficaram_de_fora(self):
        con = self.catalogo()
        p = self.a_mais.payload(con, self.config.load())
        self.assertEqual(p["scope"]["foil"], {"copies": 0, "printings": 0})
        self.foil.ajustar(con, "tst-001-100", 3, source="test")
        self.foil.ajustar(con, "tst-002-100", 2, source="test")
        p = self.a_mais.payload(con, self.config.load())
        self.assertFalse(p["scope"]["foil_no_excedente"])
        self.assertEqual(p["scope"]["foil"], {"copies": 5, "printings": 2},
                         "TODAS as foils que a Coleção conta, não só as dos tiles")

    def test_com_a_chave_a_true_passariam_a_ser_a_mais(self):
        """A prova pela negativa: se a regra dele não existisse, o separador
        mandava-o vender os foils."""
        con = self.catalogo()
        self.foil.ajustar(con, "tst-001-100", 3, source="test")
        self.cfg_foil({"conta_para_coleccao": True, "conta_para_valor": True,
                       "entra_no_a_mais": True})
        itens = self.a_mais.excedente(con, self.config.load())
        x = [i for i in itens if i["printing_id"] == "tst-001-100"]
        self.assertTrue(x, "com a chave ligada aparece")
        self.assertEqual(x[0]["extra"], 3)
        p = self.a_mais.payload(con, self.config.load())
        self.assertTrue(p["scope"]["foil_no_excedente"])
        self.assertEqual(p["scope"]["foil"], {"copies": 0, "printings": 0},
                         "com a chave ligada não há nada a ressalvar")

    def test_o_have_do_tile_nao_conta_as_foils(self):
        """O `have` é o número do tile ao lado do «a mais»: com as foils lá
        dentro lia-se «tens 9/3 · 2 a mais», que é ilegível."""
        con = self.catalogo()
        self.collection.adjust(con, "tst-001-100", 2, source="test")
        self.foil.ajustar(con, "tst-001-100", 4, source="test")
        x = [i for i in self.a_mais.excedente(con, self.config.load())
             if i["printing_id"] == "tst-001-100"][0]
        self.assertEqual(x["have"], 5)
        self.assertEqual(x["target"], 3)
        self.assertEqual(x["extra"], 2)


# ---------------------------------------------------------------------------
# 5. Nos decks, as NORMAIS servem primeiro
# ---------------------------------------------------------------------------


class TestOsDecks(Base):
    def deck(self, con, texto="Nome: Ornn\n\nLegend:\n1 Emperor of the Sands\n\n"
                              "MainDeck:\n3 Defy\n"):
        self.v.write_deck("ornn", texto)
        self.decks.import_all(con, log=lambda *_: None)
        return con.execute("SELECT deck_id FROM decks").fetchone()["deck_id"]

    def test_com_normais_a_mais_que_baste_nenhum_deck_leva_foil(self):
        con = self.catalogo()
        self.foil.ajustar(con, "tst-001-100", 3, source="test")
        did = self.deck(con)
        f = self.decks.foils_nos_decks(con)
        self.assertEqual(f["copies"], 0, "há 3 normais e o deck pede 3")
        p = self.decks.deck_payload(con, did)
        self.assertEqual(p["foil_na_colecao"], 0)

    def test_sem_normais_que_bastem_o_deck_serve_se_de_foil_e_diz_se(self):
        """*"um deck joga a carta, foil ou normal, tanto faz"* — mas o ecrã tem
        de dizer que a cópia que ele vai buscar é uma foil."""
        con = self.catalogo()
        self.collection.adjust(con, "tst-001-100", -2, source="test")   # 1 normal
        self.foil.ajustar(con, "tst-001-100", 2, source="test")         # + 2 foil
        did = self.deck(con)
        p = self.decks.deck_payload(con, did)
        linha = [c for s in p["sections"] for c in s["cards"]
                 if c["card_key"] == "defy"][0]
        self.assertEqual(linha["missing"], 0, "as 3 cópias existem")
        self.assertEqual(linha["na_colecao"], 3)
        self.assertEqual(linha["foil_na_colecao"], 2,
                         "1 normal serviu primeiro; 2 vieram das foils")
        self.assertEqual(p["foil_na_colecao"], 2)
        self.assertEqual(p["foil_cartas"], 1)
        f = self.decks.foils_nos_decks(con)
        self.assertEqual(f["copies"], 2)
        self.assertEqual(f["por_deck"]["ornn"]["defy"], 2)
        self.assertEqual(f["por_impressao"]["tst-001-100"]["foil"], 2)

    def test_a_foil_e_a_ULTIMA_a_sair(self):
        """Com 2 normais e 5 foils, um deck que pede 3 leva as 2 normais e UMA
        foil — não três foils."""
        con = self.catalogo()
        self.collection.adjust(con, "tst-001-100", -1, source="test")   # 2 normais
        self.foil.ajustar(con, "tst-001-100", 5, source="test")
        self.deck(con)
        self.assertEqual(self.decks.foils_nos_decks(con)["copies"], 1)

    def test_entre_decks_a_foil_calha_ao_de_prioridade_MAIS_BAIXA(self):
        """O de cima leva as normais — é a ordem em que ele monta.

        2 normais + 4 foils; dois decks a pedir 2 cada. O de prioridade mais
        alta leva as 2 normais e ZERO foils; o de baixo leva as 2 dele todas em
        foil. Quem é o de cima lê-se da tabela, não se adivinha pelo nome.
        """
        con = self.catalogo()
        self.collection.adjust(con, "tst-001-100", -1, source="test")   # 2 normais
        self.foil.ajustar(con, "tst-001-100", 4, source="test")         # + 4 foil
        self.v.write_deck("ornn", "Nome: Ornn\n\nLegend:\n1 Emperor of the Sands\n\n"
                                  "MainDeck:\n2 Defy\n")
        self.v.write_deck("azir", "Nome: Azir\n\nLegend:\n1 Brutalizer\n\n"
                                  "MainDeck:\n2 Defy\n")
        self.decks.import_all(con, log=lambda *_: None)
        ordem = [r["name"] for r in con.execute(
            "SELECT name FROM decks ORDER BY priority, deck_id")]
        primeiro, segundo = ordem[0], ordem[1]
        f = self.decks.foils_nos_decks(con)
        self.assertNotIn(primeiro, f["por_deck"],
                         f"{primeiro} é o de cima: leva as 2 normais")
        self.assertEqual(f["por_deck"][segundo]["defy"], 2,
                         f"{segundo} é o de baixo: fica com as foils")

    def test_um_deck_desmontado_nao_leva_foil_nenhuma(self):
        """Desmontado não consome nada (2026-09-24), foil incluída."""
        con = self.catalogo()
        self.collection.adjust(con, "tst-001-100", -2, source="test")
        self.foil.ajustar(con, "tst-001-100", 2, source="test")
        self.deck(con)
        self.cfg_foil({"conta_para_coleccao": True, "conta_para_valor": True,
                       "entra_no_a_mais": False},
                      {"decks": {"so_base": True, "so_normais_excepto": [],
                                 "contar_runas": False, "montados": []}})
        self.assertEqual(self.decks.foils_nos_decks(con)["copies"], 0)

    def test_com_a_chave_desligada_os_decks_nao_veem_foil(self):
        con = self.catalogo()
        self.collection.adjust(con, "tst-001-100", -2, source="test")
        self.foil.ajustar(con, "tst-001-100", 2, source="test")
        did = self.deck(con)
        self.assertEqual(self.decks.foils_nos_decks(con)["copies"], 2)
        self.cfg_foil({"conta_para_coleccao": False, "conta_para_valor": True})
        self.assertEqual(self.decks.foils_nos_decks(con)["copies"], 0)
        p = self.decks.deck_payload(con, did)
        linha = [c for s in p["sections"] for c in s["cards"]
                 if c["card_key"] == "defy"][0]
        self.assertEqual(linha["missing"], 2, "sem os foils faltam 2")


# ---------------------------------------------------------------------------
# 6. As três cautelas do mesmo tipo
# ---------------------------------------------------------------------------


class TestAsCautelas(Base):
    def test_o_propor_deck_nunca_propoe_uma_foil(self):
        """A proposta grava em `copy_locations`, que conta NORMAIS: propor uma
        foil era mandar marcar uma normal que não existe."""
        con = self.catalogo()
        self.collection.adjust(con, "tst-001-100", -2, source="test")   # 1 normal
        self.foil.ajustar(con, "tst-001-100", 5, source="test")
        self.v.write_deck("ornn", "Nome: Ornn\n\nLegend:\n1 Emperor of the Sands\n\n"
                                  "MainDeck:\n3 Defy\n")
        self.decks.import_all(con, log=lambda *_: None)
        p = self.locais.propor_deck(con, "ornn")
        n = sum(i["qty"] for i in p["items"] if i["printing_id"] == "tst-001-100")
        self.assertEqual(n, 1, "só a normal que existe")

    def test_a_venda_avisa_pelo_stock_de_NORMAIS(self):
        """O «marcar como vendidas» baixa o `copies.qty`: o aviso de stock tem
        de ser sobre as normais, senão manda-o vender o que não quer vender."""
        con = self.catalogo()
        self.foil.ajustar(con, "tst-001-100", 5, source="test")
        self.venda.juntar(con, "tst-001-100", 4, source="test")
        lista = self.venda.itens(con, self.config.load())
        linha = [x for x in lista if x["printing_id"] == "tst-001-100"][0]
        self.assertEqual(linha["na_colecao"], 3, "as 3 normais, não 8")
        self.assertTrue(linha["a_mais_do_que_tens"],
                        "4 à venda e 3 normais na Coleção: avisa")
        self.assertEqual(self.venda.conta(lista)["avisos_stock"], 1)

    def test_o_menos_da_grelha_nao_mexe_nas_foils(self):
        con = self.catalogo()
        self.foil.ajustar(con, "tst-001-100", 3, source="test")
        self.collection.adjust(con, "tst-001-100", -3, source="test")
        r = con.execute("SELECT qty, qty_foil FROM copies WHERE printing_id = "
                        "'tst-001-100'").fetchone()
        self.assertEqual((r["qty"], r["qty_foil"]), (0, 3),
                         "baixar as normais a zero não corta uma foil")
        self.assertEqual(self.tile(con, "tst-001-100")["qty"], 3,
                         "a Coleção continua a contar as 3 foils")

    def test_o_menos_do_tile_desliga_com_zero_normais(self):
        """No cliente: o `−` baixa as NORMAIS, por isso desliga-se pelo
        `qtyNormais` e não pelo `qty` (que traz foils por cima)."""
        js = APP.read_text(encoding="utf-8")
        self.assertIn("function qtyNormais(pid)", js)
        self.assertIn("qtyNormais(p.id) <= 0 ? 'disabled' : ''", js)
        self.assertIn("el.querySelector('.step.minus').disabled = qtyNormais(pid) <= 0",
                      js)


# ---------------------------------------------------------------------------
# 7. A fronteira
# ---------------------------------------------------------------------------


class TestAFronteira(Base):
    def test_nenhum_modulo_de_contas_importa_o_foil(self):
        proibidos = ["a_subir", "faltas", "faltas_edicao", "a_mais", "uso_decks",
                     "decks", "locais", "pending", "prices", "painel", "runas_vista",
                     "cardmarket", "seguir", "catalog", "venda"]
        for nome in proibidos:
            fonte = (REPO / "riftvault" / f"{nome}.py").read_text(encoding="utf-8")
            self.assertNotIn("import foil", fonte, nome)
            self.assertNotIn("from .foil", fonte, nome)

    def test_a_coluna_do_foil_so_se_le_nos_dois_funis(self):
        """O `a_mais` e o `decks` passaram a saber que há foils — mas pelo
        `locais`, nunca pela coluna. É o que impede o foil de entrar numa conta
        por um caminho que ninguém vê."""
        coluna = "qty" + "_foil"
        for nome in ("a_mais", "decks", "a_subir", "faltas", "faltas_edicao",
                     "uso_decks", "pending", "painel", "runas_vista", "venda"):
            fonte = (REPO / "riftvault" / f"{nome}.py").read_text(encoding="utf-8")
            self.assertNotIn(coluna, fonte, nome)
        for nome, chave in (("locais", "conta_para_coleccao"),
                            ("prices", "conta_para_valor")):
            fonte = (REPO / "riftvault" / f"{nome}.py").read_text(encoding="utf-8")
            self.assertIn(coluna, fonte, nome)
            self.assertIn(chave, fonte, nome)

    def test_o_com_foil_false_e_a_porta_dos_tres_sitios(self):
        for nome in ("a_mais", "venda"):
            fonte = (REPO / "riftvault" / f"{nome}.py").read_text(encoding="utf-8")
            self.assertIn("com_foil", fonte, nome)
        fonte = (REPO / "riftvault" / "locais.py").read_text(encoding="utf-8")
        self.assertIn("com_foil: bool = True", fonte)
        self.assertIn("na_colecao(con, com_foil=False)", fonte,
                      "o propor_deck pede as normais")

    def test_a_omissao_dos_funis_conta_as_foils(self):
        """Quem chamar `na_colecao`/`contadas` sem dizer nada tem as foils
        dentro — é o que ele decidiu. `com_foil=False` é a excepção, e é
        explícita em cada sítio."""
        con = self.catalogo()
        self.foil.ajustar(con, "tst-001-100", 2, source="test")
        self.assertEqual(self.locais.na_colecao(con)["tst-001-100"], 5)
        self.assertEqual(self.locais.contadas(con)["tst-001-100"], 5)
        self.assertEqual(
            self.locais.na_colecao(con, com_foil=False)["tst-001-100"], 3)
        self.assertEqual(
            self.locais.contadas(con, com_foil=False)["tst-001-100"], 3)
        self.assertEqual(self.locais.totais(con)["tst-001-100"], 3,
                         "os `totais` são sempre as normais")


# ---------------------------------------------------------------------------
# 8. A interface diz
# ---------------------------------------------------------------------------


class TestAInterfaceDiz(Base):
    def test_o_app_js_diz_que_os_foils_contam_ao_preco_da_normal(self):
        js = APP.read_text(encoding="utf-8")
        self.assertIn("function foilNotaValor", js)
        self.assertIn("ao preço da versão\n    normal", js.replace("\r", ""))
        self.assertIn("piso", js)
        # Nos três sítios onde o valor aparece.
        self.assertIn("foilNotaValor(true)", js, "a barra do valor da Coleção")
        self.assertRegex(js, r"As cópias próprias dos decks não contam\. \$\{foilNotaValor\(\)\}",
                         "o cartão do Início")
        self.assertIn("cat.conta_para_valor ? foilNotaValor() : ''", js,
                      "o resumo do foil")

    def test_o_app_js_separa_o_caso_from_foil(self):
        js = APP.read_text(encoding="utf-8")
        self.assertIn("preco_de_foil", js)
        self.assertIn("já têm preço de foil", js)

    def test_o_app_js_diz_que_os_foils_nao_entram_no_a_mais(self):
        js = APP.read_text(encoding="utf-8")
        self.assertIn("foil_no_excedente", js)
        self.assertIn("não entram no que sobra", js)

    def test_o_tile_do_foil_diz_o_que_as_chaves_mandam(self):
        js = APP.read_text(encoding="utf-8")
        self.assertIn("function foilContamTxt", js)
        self.assertNotIn("As duas contagens são independentes e não contam para os "
                         "alvos nem para o valor", js,
                         "a frase velha mentiria com as chaves ligadas")

    def test_um_mais_de_foil_mexe_no_cracha_e_nas_barras(self):
        js = APP.read_text(encoding="utf-8")
        self.assertIn("function foilAplicarLocal", js)
        self.assertIn("foilAplicarLocal(pid, novo - antes)", js)
        self.assertIn("refreshTiles(pid, ck)", js)

    def test_a_tabela_de_montagem_do_deck_diz_as_foils(self):
        js = APP.read_text(encoding="utf-8")
        self.assertIn("foil_na_colecao", js)
        self.assertIn("em foil", js)
        self.assertIn("normais servem primeiro", js)

    def test_o_css_tem_as_classes_novas(self):
        css = CSS.read_text(encoding="utf-8")
        for c in (".fo-piso", ".m-foil", ".onde.fo-fora"):
            self.assertIn(c, css, c)

    def test_o_cli_do_valor_diz_a_ressalva(self):
        fonte = (REPO / "riftvault" / "cli.py").read_text(encoding="utf-8")
        self.assertIn("AO PREÇO DA NORMAL", fonte)
        self.assertIn("PISO", fonte)
        self.assertIn("sem ressalva", fonte)


# ---------------------------------------------------------------------------
# 9. O gémeo em JavaScript e o payload
# ---------------------------------------------------------------------------


class TestOPayload(Base):
    def test_o_payload_da_edicao_leva_as_chaves(self):
        con = self.catalogo()
        f = self.metrics.set_payload(con, "TST")["progress"]["foil"]
        self.assertTrue(f["printings"])
        idx = self.metrics.index_payload(con)
        self.assertTrue(idx["foil"]["conta_para_coleccao"])
        self.assertTrue(idx["foil"]["conta_para_valor"])
        self.assertFalse(idx["foil"]["entra_no_a_mais"])

    def test_ler_nao_escreve(self):
        con = self.catalogo()
        cfg = self.config.load()
        antes = [con.execute(f"SELECT COUNT(*) AS n FROM {t}").fetchone()["n"]
                 for t in ("copies", "ops", "foil_ops", "copy_locations")]
        self.a_mais.payload(con, cfg)
        self.prices.valor_dos_foils(con, cfg)
        self.prices.collection_value(con)
        self.metrics.index_payload(con)
        depois = [con.execute(f"SELECT COUNT(*) AS n FROM {t}").fetchone()["n"]
                  for t in ("copies", "ops", "foil_ops", "copy_locations")]
        self.assertEqual(antes, depois)


if __name__ == "__main__":
    unittest.main(verbosity=2)

# -*- coding: utf-8 -*-
"""O PREÇO DA FOIL, à parte (André, 2026-09-26, à tarde).

Palavras dele: *"podes meter filtro no cardtrader e tirar o preco da foil mais
barata?, para diferenciar os precos"*. De manhã os foils passaram a contar para
o valor, mas ao preço da NORMAL — e no `data/` real isso punha 254 cópias foil
todas a 11 cêntimos, o chão do CardTrader para uma comum.

O que este ficheiro fixa:

  1. A COLUNA E A MIGRAÇÃO  — `price_foil_cents` e `n_listings_foil` na
     `price_latest`, com backup do catálogo; por `connect` e por
     `catalog_only`; idempotente.
  2. O `oferta()`  — o mínimo das ofertas FOIL com os MESMOS filtros das
     normais, e `n_listings_foil`.
  3. O PREÇO NORMAL NÃO MEXEU  — o `cents` e o `from_foil` são, oferta por
     oferta, os mesmos que a implementação de antes dava. Contra o mercado REAL
     do OGS (`tests/fixtures/cardtrader-ogs-market.json`) e contra casos
     gerados.
  4. O VALOR  — uma cópia foil vale o `price_foil_cents`; sem ele cai para o da
     normal, e esse FALLBACK é contado (`valor_dos_foils`) e não escondido.
  5. OS TRÊS GÉMEOS DA CONTA  — o SQL (`valor_sql`), o Python
     (`valor_das_copias`) e o JavaScript (`valorDasCopias`) dão o mesmo.
  6. O QUE NÃO MEXEU  — o `copies` (nem `qty` nem `qty_foil`), o «A mais», os
     alvos, os níveis e as wantlists.
  7. OS DOCSTRINGS  — os que diziam «não há preço de foil no catálogo» e «hoje
     está desligado» não podem voltar.
  8. A INTERFACE  — o preço da foil aparece onde a contagem dela aparece, com o
     fallback marcado.

Corre contra pastas temporárias e um config temporário — nunca contra o `data/`
nem o `riftvault_config.json` reais.
"""
from __future__ import annotations

import importlib
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

os.environ["RIFTVAULT_CONFIG"] = str(
    Path(tempfile.gettempdir()) / "riftvault-nao-existe.json")

from tests.fixture import REPO, Vault  # noqa: E402

APP = REPO / "riftvault" / "web" / "app.js"
CSS = REPO / "riftvault" / "web" / "style.css"
MERCADO_OGS = REPO / "tests" / "fixtures" / "cardtrader-ogs-market.json"


def of(cents, *, foil=False, lingua="en", cond="Near Mint", vendedor=None,
       qtd=1, **extra):
    """Uma oferta do CardTrader como a API a devolve, reduzida ao que se lê."""
    props = {"riftbound_language": lingua, "condition": cond,
             "riftbound_foil": foil, "altered": False, "signed": False, **extra}
    return {"price_cents": cents, "price_currency": "EUR", "quantity": qtd,
            "graded": False, "on_vacation": False,
            "user": {"id": vendedor if vendedor is not None else cents},
            "properties_hash": props}


# ---------------------------------------------------------------------------
# A implementação de ANTES do `oferta()`, palavra por palavra, para provar que
# o preço NORMAL não mexeu. Não é uma paráfrase: é o corpo que estava no
# `prices.py` antes desta ordem, com a lista das foils a ser deitada fora.
# ---------------------------------------------------------------------------


def oferta_como_era(products, aceites, usable):
    normal, foil = [], []
    for p in products:
        if not usable(p, aceites):
            continue
        h = p.get("properties_hash") or {}
        (foil if h.get("riftbound_foil") else normal).append(p)

    escolhidos, from_foil = (normal, False) if normal else (foil, True)
    if not escolhidos:
        return {"cents": None, "from_foil": False,
                "n_listings": 0, "n_sellers": 0, "n_copies": 0}
    vendedores = {(p.get("user") or {}).get("id") for p in escolhidos}
    vendedores.discard(None)
    return {
        "cents": min(p["price_cents"] for p in escolhidos),
        "from_foil": from_foil,
        "n_listings": len(normal) + len(foil) if normal else len(foil),
        "n_sellers": len(vendedores),
        "n_copies": sum(int(p.get("quantity") or 1) for p in escolhidos),
    }


class Base(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.close)
        from riftvault import (a_mais, collection, config, db, foil, locais,
                               metrics, prices)
        for m in (locais, metrics, foil, a_mais, prices):
            importlib.reload(m)
        self.config, self.db, self.foil, self.locais = config, db, foil, locais
        self.metrics, self.prices, self.a_mais = metrics, prices, a_mais
        self.collection = collection
        self.cfg_foil({"conta_para_coleccao": True, "conta_para_valor": True,
                       "entra_no_a_mais": False})

    def cfg_foil(self, foil_extra: dict, extra: dict | None = None):
        caminho = self.v.root / "config.json"
        caminho.write_text(json.dumps({
            "foil": {"raridades": ["common", "uncommon"], "edicoes_fora": ["OGS"],
                     **foil_extra},
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

    def catalogo(self):
        """A edição TST, com os DOIS preços.

          `tst-001-100`  comum, 3 normais. normal 11, **foil 150**
          `tst-002-100`  incomum, 1 normal. normal 25, **sem oferta foil**
          `tst-003-100`  rara (fora do âmbito do foil), 1 normal. normal 900
          `tst-005-100`  comum, 0 normais. `from_foil = 1`, normal 100 (que já é
                         um preço de foil), sem `price_foil_cents` gravado
        """
        con = self.v.connect()
        v = self.v
        v.add_printing(con, "tst-001-100", "TST", 1, "Defy", rarity="common", size=100)
        v.add_printing(con, "tst-002-100", "TST", 2, "Scout", rarity="uncommon", size=100)
        v.add_printing(con, "tst-003-100", "TST", 3, "Brutalizer", rarity="rare", size=100)
        v.add_printing(con, "tst-005-100", "TST", 5, "Sabotage", rarity="common", size=100)
        v.rebuild(con)
        for pid, cents, ff, foil_cents in (
                ("tst-001-100", 11, 0, 150), ("tst-002-100", 25, 0, None),
                ("tst-003-100", 900, 0, None), ("tst-005-100", 100, 1, None)):
            con.execute("INSERT INTO catalog.price_latest (printing_id, price_cents, "
                        "from_foil, price_foil_cents) VALUES (?,?,?,?)",
                        (pid, cents, ff, foil_cents))
        for pid, n in (("tst-001-100", 3), ("tst-002-100", 1), ("tst-003-100", 1)):
            self.collection.adjust(con, pid, n, source="test")
        self.addCleanup(con.close)
        return con

    def tile(self, con, pid, set_id="TST"):
        for g in self.metrics.set_payload(con, set_id)["groups"]:
            for p in g["printings"]:
                if p["id"] == pid:
                    return p
        self.fail(f"{pid} não está na grelha")

    def copias(self, con):
        return sorted(tuple(r) for r in con.execute(
            "SELECT printing_id, qty, qty_foil FROM copies"))


# ---------------------------------------------------------------------------
# 1. A coluna e a migração
# ---------------------------------------------------------------------------


class TestAColuna(Base):
    def test_uma_base_de_raiz_ja_traz_as_duas_colunas(self):
        con = self.v.connect()
        self.addCleanup(con.close)
        cols = {r[1] for r in con.execute("PRAGMA catalog.table_info(price_latest)")}
        self.assertIn("price_foil_cents", cols)
        self.assertIn("n_listings_foil", cols)

    def test_a_coluna_nasce_vazia(self):
        """Depois da migração ninguém tem preço de foil: enche-se no
        `riftvault prices` seguinte, e até lá vale o fallback."""
        con = self.catalogo()
        n = con.execute("SELECT COUNT(*) n FROM catalog.price_latest "
                        "WHERE price_foil_cents IS NOT NULL").fetchone()["n"]
        self.assertEqual(n, 1, "só a que o teste gravou de propósito")

    def _catalogo_antigo(self) -> Path:
        """Um catalog.db com a `price_latest` COMO ERA — sem as duas colunas."""
        caminho = self.v.data / "catalog.db"
        con = sqlite3.connect(caminho)
        con.execute("CREATE TABLE price_latest (printing_id TEXT PRIMARY KEY, "
                    "price_cents INTEGER, currency TEXT NOT NULL DEFAULT 'EUR', "
                    "from_foil INTEGER NOT NULL DEFAULT 0, "
                    "n_listings INTEGER NOT NULL DEFAULT 0, day TEXT, "
                    "source TEXT NOT NULL DEFAULT 'cardtrader')")
        con.execute("INSERT INTO price_latest (printing_id, price_cents, from_foil) "
                    "VALUES ('tst-001-100', 11, 0)")
        con.commit()
        con.close()
        return caminho

    def test_um_catalogo_antigo_ganha_as_colunas_e_leva_backup(self):
        self._catalogo_antigo()
        con = self.v.connect()
        self.addCleanup(con.close)
        cols = {r[1] for r in con.execute("PRAGMA catalog.table_info(price_latest)")}
        for c in ("price_foil_cents", "n_listings_foil", "n_sellers", "n_copies"):
            self.assertIn(c, cols)
        backups = list((self.v.data / "backups").glob("catalog-antes-do-preco-do-foil-*.db"))
        self.assertTrue(backups, "a migração do catálogo tem de deixar backup")
        # E o backup é um SQLite a sério, com a linha que lá estava.
        b = sqlite3.connect(backups[0])
        self.addCleanup(b.close)
        self.assertEqual(
            b.execute("SELECT price_cents FROM price_latest").fetchone()[0], 11)

    def test_a_migracao_nao_perde_o_que_estava_gravado(self):
        self._catalogo_antigo()
        con = self.v.connect()
        self.addCleanup(con.close)
        r = con.execute("SELECT price_cents, price_foil_cents FROM "
                        "catalog.price_latest WHERE printing_id='tst-001-100'").fetchone()
        self.assertEqual(r["price_cents"], 11)
        self.assertIsNone(r["price_foil_cents"], "nasce vazia")

    def test_a_migracao_e_idempotente(self):
        self._catalogo_antigo()
        con = self.v.connect()
        con.close()
        quantos = len(list((self.v.data / "backups").glob("catalog-*.db")))
        con = self.v.connect()
        self.addCleanup(con.close)
        self.assertEqual(len(list((self.v.data / "backups").glob("catalog-*.db"))),
                         quantos, "a segunda ligação não volta a migrar")

    def test_o_catalog_only_tambem_migra(self):
        """O `riftvault map` abre só o catálogo, com ele como base principal: se
        essa porta não migrasse, ficava a olhar para colunas que não existem."""
        self._catalogo_antigo()
        con = self.db.catalog_only()
        self.addCleanup(con.close)
        cols = {r[1] for r in con.execute("PRAGMA table_info(price_latest)")}
        self.assertIn("price_foil_cents", cols)
        self.assertIn("n_listings_foil", cols)


# ---------------------------------------------------------------------------
# 2. O `oferta()`: o mínimo das foils, com os mesmos filtros
# ---------------------------------------------------------------------------


class TestAOferta(Base):
    def test_o_preco_da_foil_e_o_minimo_das_foils(self):
        o = self.prices.oferta([of(100), of(500, foil=True), of(300, foil=True)])
        self.assertEqual(o["cents"], 100, "a normal continua a mandar no preço normal")
        self.assertEqual(o["foil_cents"], 300)
        self.assertEqual(o["n_listings_foil"], 2)

    def test_sem_oferta_foil_o_preco_da_foil_e_none(self):
        o = self.prices.oferta([of(100), of(120)])
        self.assertIsNone(o["foil_cents"])
        self.assertEqual(o["n_listings_foil"], 0)

    def test_sem_oferta_nenhuma_os_dois_sao_none(self):
        o = self.prices.oferta([])
        self.assertIsNone(o["cents"])
        self.assertIsNone(o["foil_cents"])
        self.assertEqual(o["n_listings_foil"], 0)

    def test_so_foil_o_preco_e_o_dela_nos_dois_campos(self):
        """`from_foil`: não havia normal nenhuma. O `cents` é o da foil, e o
        `foil_cents` é o mesmo número — é a mesma oferta."""
        o = self.prices.oferta([of(300, foil=True), of(500, foil=True)])
        self.assertEqual((o["cents"], o["foil_cents"]), (300, 300))
        self.assertTrue(o["from_foil"])
        self.assertEqual(o["n_listings_foil"], 2)

    # -- os MESMOS filtros das normais, um a um ----------------------------
    def test_a_foil_em_ma_condicao_nao_entra(self):
        o = self.prices.oferta([of(100), of(10, foil=True, cond="Moderately Played"),
                                of(400, foil=True)])
        self.assertEqual(o["foil_cents"], 400)
        self.assertEqual(o["n_listings_foil"], 1)

    def test_a_foil_noutra_lingua_nao_entra(self):
        o = self.prices.oferta([of(100), of(10, foil=True, lingua="ja"),
                                of(400, foil=True)])
        self.assertEqual(o["foil_cents"], 400)

    def test_a_foil_assinada_alterada_ou_graded_nao_entra(self):
        graded = of(5, foil=True)
        graded["graded"] = True
        ferias = of(6, foil=True)
        ferias["on_vacation"] = True
        moeda = of(7, foil=True)
        moeda["price_currency"] = "USD"
        o = self.prices.oferta([of(100), of(8, foil=True, signed=True),
                                of(9, foil=True, altered=True), graded, ferias, moeda,
                                of(400, foil=True)])
        self.assertEqual(o["foil_cents"], 400, "nenhuma das seis pode entrar")
        self.assertEqual(o["n_listings_foil"], 1)

    def test_a_lingua_do_config_vale_para_a_foil_tambem(self):
        self.cfg_foil({}, {"precos": {"linguas": ["en", "fr"]}})
        importlib.reload(self.prices)
        o = self.prices.oferta([of(100), of(50, foil=True, lingua="fr"),
                                of(400, foil=True)])
        self.assertEqual(o["foil_cents"], 50, "o francês passou a contar")

    def test_mint_conta_como_near_mint(self):
        o = self.prices.oferta([of(100), of(400, foil=True, cond="Mint")])
        self.assertEqual(o["foil_cents"], 400)


# ---------------------------------------------------------------------------
# 3. O PREÇO NORMAL NÃO MEXEU (o ponto 3 da ordem)
# ---------------------------------------------------------------------------


class TestONormalNaoMexeu(Base):
    def _comparar(self, products):
        aceites = self.prices.linguas()
        novo = self.prices.oferta(products, aceites)
        velho = oferta_como_era(products, aceites, self.prices._usable)
        for campo in ("cents", "from_foil", "n_listings", "n_sellers", "n_copies"):
            self.assertEqual(novo[campo], velho[campo],
                             f"{campo} mudou — o preço normal tem de ficar igual")

    def test_contra_o_mercado_real_do_ogs(self):
        """O snapshot real do CardTrader (3 blueprints, 2026-08-31): o preço
        normal é o mesmo de antes em todos, e o da foil aparece onde há oferta
        foil. O `344333` é o caso a sério — normal **82** cêntimos, foil
        **171**: mais do dobro. Era ele que estava a contar a 82."""
        mercado = json.loads(MERCADO_OGS.read_text(encoding="utf-8"))
        self.assertEqual(len(mercado), 3, "a fixture do mercado do OGS mudou")
        com_foil = {}
        for bid, products in mercado.items():
            self._comparar(products)
            o = self.prices.oferta(products)
            if o["foil_cents"] is not None:
                com_foil[bid] = (o["cents"], o["foil_cents"], o["n_listings_foil"])
        self.assertEqual(com_foil, {"344333": (82, 171, 1)})

    def test_contra_o_mercado_real_com_foils_metidas_por_cima(self):
        """A mesma fixture, com uma foil barata acrescentada a cada blueprint:
        o preço NORMAL não pode mexer, e o da foil aparece."""
        mercado = json.loads(MERCADO_OGS.read_text(encoding="utf-8"))
        for bid, products in mercado.items():
            com_foil = products + [of(3, foil=True, vendedor=999999)]
            self._comparar(com_foil)
            o = self.prices.oferta(com_foil)
            self.assertEqual(o["foil_cents"], 3)

    def test_contra_casos_gerados(self):
        """Todas as combinações que interessam: com e sem normal, com e sem
        foil, com inutilizáveis pelo meio."""
        mp = of(1, cond="Moderately Played")
        ja = of(2, lingua="ja")
        casos = [
            [], [mp], [ja], [mp, ja],
            [of(100)], [of(100), of(90)],
            [of(50, foil=True)], [of(50, foil=True), of(70, foil=True)],
            [of(100), of(50, foil=True)],
            [of(100), of(50, foil=True), mp, ja],
            [of(100, qtd=3), of(50, foil=True, qtd=2)],
            [of(100, vendedor=1), of(110, vendedor=1), of(50, foil=True, vendedor=1)],
            [mp, of(50, foil=True)],
            [of(5, foil=True, cond="Poor"), of(100)],
        ]
        for c in casos:
            with self.subTest(n=len(c)):
                self._comparar(c)

    def test_o_from_foil_continua_a_significar_o_mesmo(self):
        """1 quando NÃO havia oferta normal — não «tem oferta foil»."""
        self.assertFalse(self.prices.oferta([of(100), of(50, foil=True)])["from_foil"])
        self.assertTrue(self.prices.oferta([of(50, foil=True)])["from_foil"])


# ---------------------------------------------------------------------------
# 4. O valor: a foil ao preço da foil, e o fallback contado
# ---------------------------------------------------------------------------


class TestOValor(Base):
    def test_a_copia_foil_vale_o_preco_da_foil(self):
        con = self.catalogo()
        antes = self.prices.collection_value(con)["cents"]
        self.foil.ajustar(con, "tst-001-100", 2, source="test")
        depois = self.prices.collection_value(con)["cents"]
        self.assertEqual(depois - antes, 2 * 150,
                         "duas foils a 1,50 €, não a 11 cêntimos")

    def test_sem_preco_de_foil_cai_para_o_da_normal(self):
        con = self.catalogo()
        antes = self.prices.collection_value(con)["cents"]
        self.foil.ajustar(con, "tst-002-100", 2, source="test")
        depois = self.prices.collection_value(con)["cents"]
        self.assertEqual(depois - antes, 2 * 25, "o fallback é o preço da normal")

    def test_o_fallback_e_contado_e_separado(self):
        con = self.catalogo()
        self.foil.ajustar(con, "tst-001-100", 2, source="test")   # tem preço de foil
        self.foil.ajustar(con, "tst-002-100", 3, source="test")   # fallback
        f = self.prices.valor_dos_foils(con)
        self.assertEqual(f["copies"], 5)
        self.assertEqual((f["preco_de_foil"]["printings"],
                          f["preco_de_foil"]["copies"],
                          f["preco_de_foil"]["cents"]), (1, 2, 2 * 150))
        self.assertEqual((f["ao_preco_da_normal"]["printings"],
                          f["ao_preco_da_normal"]["copies"],
                          f["ao_preco_da_normal"]["cents"]), (1, 3, 3 * 25))
        self.assertEqual(f["cents"], 2 * 150 + 3 * 25)
        self.assertEqual(f["sem_preco"], {"printings": 0, "copies": 0})

    def test_o_from_foil_sem_coluna_gravada_nao_e_fallback(self):
        """O `price_cents` de uma `from_foil` JÁ é de foil: chamar-lhe fallback
        era dizer que é o preço da normal, e não é."""
        con = self.catalogo()
        self.foil.ajustar(con, "tst-005-100", 2, source="test")
        f = self.prices.valor_dos_foils(con)
        self.assertEqual(f["preco_de_foil"]["copies"], 2)
        self.assertEqual(f["ao_preco_da_normal"]["copies"], 0)
        self.assertEqual(f["cents"], 2 * 100)

    def test_uma_foil_sem_preco_nenhum_nao_conta(self):
        con = self.catalogo()
        con.execute("DELETE FROM catalog.price_latest WHERE printing_id='tst-002-100'")
        self.foil.ajustar(con, "tst-002-100", 3, source="test")
        f = self.prices.valor_dos_foils(con)
        self.assertEqual(f["sem_preco"], {"printings": 1, "copies": 3})
        self.assertEqual(f["cents"], 0)

    def test_a_ressalva_vai_dentro_do_valor(self):
        con = self.catalogo()
        self.foil.ajustar(con, "tst-002-100", 1, source="test")
        v = self.prices.collection_value(con)
        self.assertEqual(v["foils"]["ao_preco_da_normal"]["copies"], 1)
        idx = self.metrics.index_payload(con)
        self.assertEqual(idx["value"]["foils"]["ao_preco_da_normal"]["copies"], 1)

    def test_o_valor_por_edicao_usa_o_preco_da_foil(self):
        con = self.catalogo()
        antes = self.prices.value_by_set(con)["TST"]
        self.foil.ajustar(con, "tst-001-100", 2, source="test")
        self.assertEqual(self.prices.value_by_set(con)["TST"] - antes, 2 * 150)

    def test_o_top_diz_as_duas_metades(self):
        con = self.catalogo()
        self.foil.ajustar(con, "tst-001-100", 2, source="test")
        linha = [r for r in self.prices.top_value(con, 20)
                 if r["public_code"].endswith("001/100")][0]
        self.assertEqual((linha["qty_normal"], linha["qty_foil"]), (3, 2))
        self.assertEqual(linha["price_foil_cents"], 150)
        self.assertEqual(linha["total"], 3 * 11 + 2 * 150)

    def test_a_barra_da_edicao_bate_com_a_conta(self):
        con = self.catalogo()
        self.foil.ajustar(con, "tst-001-100", 2, source="test")
        p = self.metrics.set_payload(con, "TST")["progress"]["value"]
        # 3×11 (Defy) + 2×150 (as foils dela) + 1×25 (Scout) + 1×900 (Brutalizer)
        self.assertEqual(p["owned"], 3 * 11 + 2 * 150 + 25 + 900)

    def test_com_a_chave_do_valor_desligada_a_foil_nao_vale(self):
        con = self.catalogo()
        antes = self.prices.collection_value(con)["cents"]
        self.cfg_foil({"conta_para_coleccao": True, "conta_para_valor": False})
        self.foil.ajustar(con, "tst-001-100", 3, source="test")
        self.assertEqual(self.prices.collection_value(con)["cents"], antes)
        self.assertIsNone(self.prices.valor_dos_foils(con))

    def test_a_foil_de_uma_retirada_nao_conta(self):
        """Uma runa em alt art não existe para o riftvault — nem a foil dela."""
        con = self.v.connect()
        self.addCleanup(con.close)
        self.v.add_printing(con, "tst-007-100", "TST", 7, "Fury Rune",
                            card_type="Rune", rarity="common", size=100)
        self.v.add_printing(con, "tst-007a-100", "TST", 7, "Fury Rune", variant="a",
                            kind="alt_art", card_type="Rune", rarity="showcase",
                            base_rarity="common", size=100)
        self.v.rebuild(con)
        self.cfg_foil({"conta_para_coleccao": True, "conta_para_valor": True},
                      {"runas_especiais": {"tipos": ["Rune"], "excepto": ["base"],
                                           "retiradas": ["a"]}})
        con.execute("INSERT INTO catalog.price_latest (printing_id, price_cents, "
                    "price_foil_cents) VALUES ('tst-007a-100', 500, 900)")
        con.execute("INSERT INTO copies (printing_id, qty, qty_foil, updated_at) "
                    "VALUES ('tst-007a-100', 1, 2, '2026-09-26')")
        self.assertEqual(self.prices.collection_value(con)["cents"], 0)
        self.assertEqual(self.prices.valor_dos_foils(con)["copies"], 0)


# ---------------------------------------------------------------------------
# 5. Os três gémeos da conta
# ---------------------------------------------------------------------------


CASOS_GEMEOS = [
    # (qty_normal, qty_foil, price_cents, price_foil_cents, esperado)
    (3, 0, 11, 150, 33),
    (3, 2, 11, 150, 33 + 300),
    (0, 2, 11, 150, 300),
    (3, 2, 11, None, 33 + 22),       # fallback: a foil ao preço da normal
    (0, 3, None, None, 0),           # sem preço nenhum
    (2, 0, None, None, 0),
    (1, 1, 900, 900, 1800),
    (5, 4, 100, 25, 500 + 100),      # a foil mais barata que a normal: é o que há
]


class TestOsTresGemeos(Base):
    def test_o_python(self):
        for qn, qf, p, pf, esperado in CASOS_GEMEOS:
            with self.subTest(qn=qn, qf=qf):
                self.assertEqual(self.prices.valor_das_copias(qn, qf, p, pf), esperado)

    def test_o_sql(self):
        con = self.v.connect()
        self.addCleanup(con.close)
        for i, (qn, qf, p, pf, esperado) in enumerate(CASOS_GEMEOS):
            with self.subTest(qn=qn, qf=qf):
                sql = ("SELECT " + self.prices.valor_sql("c", "p") + " AS v "
                       "FROM (SELECT ? AS qty_normal, ? AS qty_foil) c, "
                       "     (SELECT ? AS price_cents, ? AS price_foil_cents) p")
                got = con.execute(sql, (qn, qf, p, pf)).fetchone()["v"]
                self.assertEqual(got, esperado)

    def test_o_javascript(self):
        """O `valorDasCopias` do `app.js` — corrido no node, se houver."""
        if not _tem_node():
            self.skipTest("node não está instalado")
        js = APP.read_text(encoding="utf-8")
        corpo = _extrair(js, "function valorDasCopias", "\n}")
        prog = """
        %s
        const casos = %s;
        const saida = casos.map(([qn, qf, p, pf]) => {
          state = { index: { foil: { conta_para_valor: true } },
                    valNorm: new Map([['x', qn]]), foil: new Map([['x', qf]]),
                    precoFoil: new Map(pf == null ? [] : [['x', pf]]) };
          return p == null ? 0 : valorDasCopias('x', p);
        });
        console.log(JSON.stringify(saida));
        """ % (corpo, json.dumps([[c[0], c[1], c[2], c[3]] for c in CASOS_GEMEOS]))
        prog = "let state;\n" + prog
        out = subprocess.run([_node(), "-e", prog], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(json.loads(out.stdout), [c[4] for c in CASOS_GEMEOS])

    def test_o_cliente_conta_as_normais_do_valor_e_nao_as_da_colecao(self):
        """Uma cópia num deck vale na mesma (o valor é do que ele TEM), e por
        isso o cliente lê o `qty_valor`, não o `qty` da Coleção: era esse que
        estava aqui e punha a barra a dizer menos do que o servidor."""
        js = APP.read_text(encoding="utf-8")
        self.assertIn("state.valNorm.get(pid)", js)
        self.assertNotIn("owned += (state.qty.get(p.id) || 0) * p.price", js)


def _node() -> str:
    return "node"


def _tem_node() -> bool:
    try:
        subprocess.run([_node(), "--version"], capture_output=True, timeout=20)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def _extrair(js: str, inicio: str, fim: str) -> str:
    i = js.index(inicio)
    j = js.index(fim, i) + len(fim)
    return js[i:j]


# ---------------------------------------------------------------------------
# 6. O que NÃO mexeu
# ---------------------------------------------------------------------------


class TestNaoMexe(Base):
    def test_o_copies_nao_se_toca(self):
        """Nem a migração, nem o preço de foil, nem ler o valor: as duas
        colunas de cópias são dele e ninguém aqui lhes mexe."""
        con = self.catalogo()
        antes = self.copias(con)
        self.prices.collection_value(con)
        self.prices.valor_dos_foils(con)
        self.prices.value_by_set(con)
        self.prices.top_value(con)
        self.metrics.set_payload(con, "TST")
        self.metrics.index_payload(con)
        con.execute("UPDATE catalog.price_latest SET price_foil_cents = 999")
        self.prices.collection_value(con)
        self.assertEqual(self.copias(con), antes)

    def test_o_preco_da_foil_nao_mexe_nos_alvos(self):
        con = self.catalogo()
        def fotografia():
            p = self.metrics.set_payload(con, "TST")
            n = self.metrics.niveis_payload(con, self.config.load())
            return (p["progress"]["master"], [(l["k"], l["done"], l["missing"])
                                              for l in n["levels"]],
                    [(t["id"], t["qty"], t["target"]) for g in p["groups"]
                     for t in g["printings"]])
        self.foil.ajustar(con, "tst-001-100", 2, source="test")
        antes = fotografia()
        con.execute("UPDATE catalog.price_latest SET price_foil_cents = 9999")
        self.assertEqual(fotografia(), antes,
                         "o preço não pode mexer no que a impressão TEM")

    def test_o_a_mais_nao_mexe(self):
        """`foil.entra_no_a_mais` continua `false`: o preço da foil não pode
        fazer nascer excedente nenhum."""
        con = self.catalogo()
        def foto():
            p = self.a_mais.payload(con)
            return (p["totals"]["excedente"],
                    [(i["id"], i["extra"], i["have"]) for s in p["sets"]
                     for i in s["excedente"]["items"]])
        antes = foto()
        self.foil.ajustar(con, "tst-001-100", 5, source="test")
        con.execute("UPDATE catalog.price_latest SET price_foil_cents = 9999")
        self.assertEqual(foto(), antes,
                         "os foils não entram no que sobra, com preço ou sem ele")

    def test_o_historico_continua_a_ser_so_do_preco_normal(self):
        """A série do «A subir» é a da carta que ele compra. Uma coluna de preço
        de foil no histórico era outra pergunta, que ele não fez."""
        con = self.v.connect()
        self.addCleanup(con.close)
        cols = {r[1] for r in con.execute("PRAGMA prices.table_info(price_history)")}
        self.assertNotIn("price_foil_cents", cols)


# ---------------------------------------------------------------------------
# 7. Os docstrings que mentiam
# ---------------------------------------------------------------------------


class TestOsDocstrings(unittest.TestCase):
    def fonte(self, nome):
        return (REPO / "riftvault" / nome).read_text(encoding="utf-8")

    def test_o_prices_nao_diz_que_nao_ha_preco_de_foil(self):
        p = self.fonte("prices.py")
        self.assertNotIn("não há preço de foil no catálogo", p)
        self.assertNotIn("hoje está desligado", p)

    def test_o_prices_descreve_a_coluna_nova(self):
        p = self.fonte("prices.py")
        self.assertIn("price_foil_cents", p)
        self.assertIn("foil_cents", p)
        self.assertIn("valor_sql", p)

    def test_o_copias_sql_descreve_as_tres_colunas(self):
        doc = __import__("riftvault.prices", fromlist=["x"]).copias_sql.__doc__
        for c in ("qty_normal", "qty_foil", "valor_sql"):
            self.assertIn(c, doc)

    def test_os_outros_modulos_tambem_nao(self):
        """A mesma frase estava no `foil.py`, no `locais.py`, no `config.py` e
        no CSS: ou se corrige em todos, ou fica a mentir no que sobrar."""
        for nome in ("foil.py", "locais.py", "config.py"):
            self.assertNotIn("não há preço de foil no catálogo", self.fonte(nome),
                             f"{nome} continua a dizer que não há preço de foil")
        self.assertNotIn("não há preço de foil no", CSS.read_text(encoding="utf-8"))

    def test_o_app_js_tambem_nao(self):
        js = APP.read_text(encoding="utf-8")
        self.assertNotIn("não há preço de foil no catálogo", js)
        self.assertNotIn("o valor contam só as normais", js)


# ---------------------------------------------------------------------------
# 8. A interface
# ---------------------------------------------------------------------------


class TestAInterface(Base):
    def test_o_tile_leva_o_preco_da_foil(self):
        con = self.catalogo()
        self.assertEqual(self.tile(con, "tst-001-100")["price_foil"], 150)
        self.assertIsNone(self.tile(con, "tst-002-100")["price_foil"],
                          "sem oferta foil não há preço de foil")

    def test_o_tile_leva_as_duas_metades_do_valor(self):
        con = self.catalogo()
        self.foil.ajustar(con, "tst-001-100", 2, source="test")
        t = self.tile(con, "tst-001-100")
        self.assertEqual(t["qty_valor"], 5, "3 normais + 2 foil contam para o valor")
        self.assertEqual(t["qty_valor_foil"], 2)

    def test_o_from_foil_conta_como_preco_de_foil_no_tile(self):
        con = self.catalogo()
        self.assertEqual(self.tile(con, "tst-005-100")["price_foil"], 100)

    def test_o_app_js_mostra_o_preco_e_marca_o_fallback(self):
        js = APP.read_text(encoding="utf-8")
        self.assertIn("function foilPrecoTxt", js)
        self.assertIn("state.precoFoil", js)
        self.assertIn("foil ao preço da normal", js)
        self.assertIn("fo-preco", js)
        self.assertIn("foilPrecoTxt(pid)", js)

    def test_o_css_tem_a_classe_do_preco(self):
        css = CSS.read_text(encoding="utf-8")
        self.assertIn(".foil-linha .fo-preco", css)
        self.assertIn(".foil-linha .fo-piso", css)
        # Linha própria, com a largura toda: ao lado dos `+`/`−` a frase do
        # fallback saía a uma palavra por linha a 375 px.
        self.assertIn("flex: 0 0 100%", css)
        self.assertIn("flex-wrap: wrap", css)

    def test_o_cli_do_foil_diz_os_dois_precos(self):
        fonte = (REPO / "riftvault" / "cli.py").read_text(encoding="utf-8")
        self.assertIn("_precos_foil", fonte)
        self.assertIn("uma foil conta ao preço da ", fonte)

    def test_o_ajustar_devolve_os_dois_precos(self):
        con = self.catalogo()
        r = self.foil.ajustar(con, "tst-001-100", 1, source="test")
        self.assertEqual((r["price"], r["price_foil"]), (11, 150))
        r2 = self.foil.ajustar(con, "tst-002-100", 1, source="test")
        self.assertEqual((r2["price"], r2["price_foil"]), (25, None))

    def test_o_resumo_do_foil_diz_o_fallback(self):
        con = self.catalogo()
        self.foil.ajustar(con, "tst-001-100", 2, source="test")
        self.foil.ajustar(con, "tst-002-100", 3, source="test")
        t = self.foil.texto(self.foil.resumo(con), [{"id": "TST", "name": "TST"}],
                            self.prices.valor_dos_foils(con))
        self.assertIn("a preço de FOIL", t)
        self.assertIn("ao preço da NORMAL", t)
        self.assertIn("PISO", t)

    def test_o_resumo_sem_foils_diz_so_a_regra(self):
        con = self.catalogo()
        t = self.foil.texto(self.foil.resumo(con), [{"id": "TST", "name": "TST"}],
                            self.prices.valor_dos_foils(con))
        self.assertIn("PREÇO DA FOIL", t)


# ---------------------------------------------------------------------------
# 9. O `sync_prices` grava as duas colunas
# ---------------------------------------------------------------------------


class CTFalso:
    """Um CardTrader de brincar: uma expansão, dois blueprints."""

    def __init__(self, mercado):
        self.mercado = mercado

    def marketplace(self, expansion_id):
        return self.mercado


class TestOSync(Base):
    def test_o_sync_grava_o_preco_da_foil(self):
        con = self.catalogo()
        con.execute("INSERT INTO catalog.cardtrader_map (printing_id, blueprint_id, "
                    "expansion_id) VALUES ('tst-001-100', 111, 9), "
                    "('tst-002-100', 222, 9)")
        con.commit()
        con.close()
        mercado = {
            "111": [of(100), of(440, foil=True), of(700, foil=True)],
            "222": [of(200)],
        }
        r = self.prices.sync_prices(CTFalso(mercado), log=lambda *a: None)
        self.assertEqual(r["com_preco_foil"], 1)
        con = self.v.connect()
        self.addCleanup(con.close)
        linhas = {x["printing_id"]: x for x in con.execute(
            "SELECT printing_id, price_cents, price_foil_cents, n_listings_foil "
            "FROM catalog.price_latest")}
        a = linhas["tst-001-100"]
        self.assertEqual((a["price_cents"], a["price_foil_cents"],
                          a["n_listings_foil"]), (100, 440, 2))
        b = linhas["tst-002-100"]
        self.assertEqual((b["price_cents"], b["price_foil_cents"],
                          b["n_listings_foil"]), (200, None, 0))

    def test_um_preco_de_foil_que_desaparece_apaga_se(self):
        """Se hoje não há oferta foil, a cópia tem de cair para o fallback
        CONTADO e não ficar presa ao preço da semana passada."""
        con = self.catalogo()
        con.execute("INSERT INTO catalog.cardtrader_map (printing_id, blueprint_id, "
                    "expansion_id) VALUES ('tst-001-100', 111, 9)")
        con.commit()
        con.close()
        self.prices.sync_prices(CTFalso({"111": [of(100)]}), log=lambda *a: None)
        con = self.v.connect()
        self.addCleanup(con.close)
        r = con.execute("SELECT price_foil_cents FROM catalog.price_latest "
                        "WHERE printing_id='tst-001-100'").fetchone()
        self.assertIsNone(r["price_foil_cents"])

    def test_o_sync_nao_mexe_nas_copias(self):
        con = self.catalogo()
        con.execute("INSERT INTO catalog.cardtrader_map (printing_id, blueprint_id, "
                    "expansion_id) VALUES ('tst-001-100', 111, 9)")
        con.commit()
        antes = self.copias(con)
        con.close()
        self.prices.sync_prices(CTFalso({"111": [of(100), of(440, foil=True)]}),
                                log=lambda *a: None)
        con = self.v.connect()
        self.addCleanup(con.close)
        self.assertEqual(self.copias(con), antes)


if __name__ == "__main__":
    unittest.main()

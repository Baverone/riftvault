"""O separador «Venda» (André, 2026-09-25).

Palavras dele: *"quero que cries um separador que e: Venda. este separador
permite-me marcar as cartas que estou a vender no momento para apresentar a
conta a pessoa. todos os precos tem que ser o Trend do Cardmarket!"*.

O que se fixa:
  1. a LISTA em curso: juntar, tirar, limpar, uma linha por impressão;
  2. o PREÇO: a conta é feita SÓ com o Trend que ele mete à mão — o do
     CardTrader nunca entra, nem como omissão de uma linha vazia; o Trend
     guarda-se por impressão com a data e marca-se como velho;
  3. o LINK para o Cardmarket, por linha (id do `cardtrader_map`, ou a
     pesquisa pelo nome de mercado quando não há id);
  4. MARCAR PARA VENDA NÃO MEXE EM NADA: uma fotografia de tudo o que é número
     do site, antes e depois de meter e tirar linhas;
  5. «marcar como vendidas»: separado, com confirmação, com registo, e a
     baixar as cópias pelo caminho de sempre (a `ops`, portanto com undo);
  6. os AVISOS (mais cópias do que tem, carta num deck montado) marcam e não
     bloqueiam;
  7. a rota, o site publicado (só leitura), a CLI e o `app.js`.

Tudo contra pastas temporárias (`tests.fixture.Vault`) e um config temporário
(`RIFTVAULT_CONFIG`): o `data/` e o `riftvault_config.json` a sério nunca são
tocados.
"""

from __future__ import annotations

import contextlib
import importlib
import io
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ["RIFTVAULT_CONFIG"] = str(Path(tempfile.gettempdir()) / "riftvault-nao-existe.json")

from tests.fixture import REPO, Vault  # noqa: E402

APP_JS = REPO / "riftvault" / "web" / "app.js"


class Base(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.close)
        from riftvault import (a_mais, a_subir, collection, config, db, decks, faltas,
                               faltas_edicao, foil, locais, metrics, painel, pending,
                               prices, proprias, venda)
        for m in (locais, metrics, foil, painel, decks, proprias, a_subir,
                  faltas_edicao, a_mais, pending, faltas, prices, venda):
            importlib.reload(m)
        self.config, self.db, self.venda, self.locais = config, db, venda, locais
        self.metrics, self.painel, self.decks = metrics, painel, decks
        self.a_subir, self.faltas_edicao, self.a_mais = a_subir, faltas_edicao, a_mais
        self.pending, self.faltas, self.prices = pending, faltas, prices
        self.collection, self.foil = collection, foil
        self.cfg_venda({})

    def cfg_venda(self, extra_venda: dict, extra: dict | None = None):
        caminho = self.v.root / "config.json"
        caminho.write_text(json.dumps({
            "venda": {**self.venda.DEFAULTS, **extra_venda},
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
        """Uma edição com uma comum, uma rara, um Legend, uma alt art e um
        token sem `cardmarket_id`. Na Coleção: 3 Defy, 2 Brutalizer, 1 Legend,
        1 alt art, 2 tokens."""
        con = self.v.connect()
        v = self.v
        v.add_printing(con, "tst-001-100", "TST", 1, "Defy", rarity="common", size=100)
        v.add_printing(con, "tst-001a-100", "TST", 1, "Defy", variant="a", kind="alt_art",
                       rarity="showcase", base_rarity="common", size=100)
        v.add_printing(con, "tst-002-100", "TST", 2, "Brutalizer", rarity="rare", size=100)
        v.add_printing(con, "tst-003-100", "TST", 3, "Emperor of the Sands",
                       card_type="Legend", rarity="epic", size=100)
        v.add_printing(con, "tst-t01", "TST", 1, "Recruit", variant="t01", kind="token",
                       lane="t", rarity="common", codigo="TST-T01")
        v.rebuild(con)
        for pid, cents in (("tst-001-100", 111), ("tst-001a-100", 500),
                           ("tst-002-100", 900), ("tst-003-100", 4000),
                           ("tst-t01", 11)):
            con.execute("INSERT INTO catalog.price_latest (printing_id, price_cents) "
                        "VALUES (?,?)", (pid, cents))
        # O `riftvault map`: nome de mercado e o id do Cardmarket. O token fica
        # SEM id, que é o caso real do `UNL-T04` Buff.
        for pid, nome, cm in (("tst-001-100", "Defy", 845712),
                              ("tst-001a-100", "Defy", 845713),
                              ("tst-002-100", "Brutalizer", 845714),
                              ("tst-003-100", "Azir - Emperor of the Sands", 845715),
                              ("tst-t01", "Recruit", None)):
            con.execute("INSERT INTO catalog.cardtrader_map (printing_id, blueprint_id, "
                        "market_name, market_set, cardmarket_id) VALUES (?,?,?,?,?)",
                        (pid, hash(pid) % 100000, nome, "Test Set", cm))
        for pid, n in (("tst-001-100", 3), ("tst-001a-100", 1), ("tst-002-100", 2),
                       ("tst-003-100", 1), ("tst-t01", 2)):
            self.collection.adjust(con, pid, n, source="test")
        self.addCleanup(con.close)
        return con

    def com_deck(self, con, montados=None):
        """Um deck que joga o Defy e o Legend. `montados=[]` desmonta-o."""
        self.v.write_deck("azir", "Nome: Azir\n\nLegend:\n1 Emperor of the Sands\n\n"
                                  "MainDeck:\n3 Defy\n")
        if montados is not None:
            self.cfg_venda({}, {"decks": {"montados": montados}})
        self.decks.import_all(con, log=lambda *_: None)


# ---------------------------------------------------------------------------


class TestAListaEmCurso(Base):
    """1. Juntar, tirar, limpar."""

    def test_juntar_e_tirar(self):
        con = self.catalogo()
        self.assertEqual(self.venda.itens(con), [])
        self.venda.juntar(con, "TST-001", 2, source="test")
        self.assertEqual(self.venda.linhas(con), {"tst-001-100": 2})
        # Juntar outra vez SOMA na mesma linha — uma linha por impressão.
        self.venda.juntar(con, "tst-001-100", 1, source="test")
        self.assertEqual(self.venda.linhas(con), {"tst-001-100": 3})
        self.venda.juntar(con, "TST-001", -1, source="test")
        self.assertEqual(self.venda.linhas(con), {"tst-001-100": 2})
        # A zero, a linha sai.
        self.venda.juntar(con, "TST-001", -9, source="test")
        self.assertEqual(self.venda.linhas(con), {})

    def test_as_versoes_sao_linhas_diferentes(self):
        """Ele escolhe a versão que tem na mão: a base e a alt art são duas
        linhas, com dois Trends e dois preços."""
        con = self.catalogo()
        self.venda.juntar(con, "tst-001-100", 1, source="test")
        self.venda.juntar(con, "tst-001a-100", 1, source="test")
        self.assertEqual(len(self.venda.itens(con)), 2)

    def test_tirar_do_que_nao_esta_na_venda_rebenta(self):
        con = self.catalogo()
        with self.assertRaises(self.venda.SemLinha):
            self.venda.juntar(con, "TST-002", -1, source="test")

    def test_limpar_esvazia_e_os_trends_ficam(self):
        con = self.catalogo()
        self.venda.juntar(con, "TST-001", 2, source="test")
        self.venda.guardar_trend(con, "TST-001", 1250, source="test")
        self.assertEqual(self.venda.limpar(con), 1)
        self.assertEqual(self.venda.itens(con), [])
        # O Trend é da CARTA, não desta venda: a venda seguinte vem preenchida.
        self.venda.juntar(con, "TST-001", 1, source="test")
        self.assertEqual(self.venda.itens(con)[0]["trend"], 1250)

    def test_a_procura_encontra_por_nome_e_por_codigo(self):
        con = self.catalogo()
        self.venda.juntar(con, "tst-001-100", 1, source="test")
        ids = [x["printing_id"] for x in self.venda.procurar(con, "defy")]
        self.assertIn("tst-001-100", ids)
        self.assertIn("tst-001a-100", ids)
        self.assertEqual([x["printing_id"] for x in self.venda.procurar(con, "TST-002")],
                         ["tst-002-100"])
        self.assertEqual(self.venda.procurar(con, "d"), [], "uma letra não procura")
        # Diz o que ele tem e o que já está na venda.
        achou = next(x for x in self.venda.procurar(con, "defy")
                     if x["printing_id"] == "tst-001-100")
        self.assertEqual((achou["have"], achou["na_venda"]), (3, 1))


class TestOPrecoEOTrend(Base):
    """2. A conta é feita SÓ com o Trend metido à mão."""

    def test_o_cardtrader_nunca_entra_na_conta(self):
        con = self.catalogo()
        self.venda.juntar(con, "TST-002", 2, source="test")   # CardTrader: 9,00 €
        lista = self.venda.itens(con)
        t = self.venda.conta(lista)
        self.assertEqual(lista[0]["price"], 900, "o preço do CardTrader mostra-se")
        self.assertIsNone(lista[0]["trend"])
        self.assertEqual(lista[0]["subtotal"], 0)
        self.assertEqual(t["cents"], 0, "SEM Trend o total é ZERO, não 2 × 9,00 €")
        self.assertEqual((t["sem_trend"], t["sem_trend_copies"]), (1, 2))
        # E com o Trend metido, é o Trend que manda — não o do CardTrader.
        self.venda.guardar_trend(con, "TST-002", 1500, source="test")
        t = self.venda.conta(self.venda.itens(con))
        self.assertEqual(t["cents"], 3000)
        self.assertEqual(t["sem_trend"], 0)

    def test_o_total_e_a_soma_dos_subtotais_com_trend(self):
        con = self.catalogo()
        self.venda.juntar(con, "TST-001", 3, source="test")
        self.venda.juntar(con, "TST-002", 1, source="test")
        self.venda.juntar(con, "TST-003", 1, source="test")
        self.venda.guardar_trend(con, "TST-001", 120, source="test")
        self.venda.guardar_trend(con, "TST-003", 4550, source="test")
        lista = self.venda.itens(con)
        t = self.venda.conta(lista)
        self.assertEqual(t["cents"], 3 * 120 + 4550)
        self.assertEqual((t["lines"], t["copies"]), (3, 5))
        self.assertEqual(t["sem_trend"], 1, "o Brutalizer ficou por preencher")

    def test_o_trend_guarda_se_com_a_data_e_fica_velho(self):
        con = self.catalogo()
        self.venda.juntar(con, "TST-001", 1, source="test")
        self.venda.guardar_trend(con, "TST-001", 999, source="test")
        x = self.venda.itens(con)[0]
        self.assertEqual(x["trend"], 999)
        self.assertFalse(x["trend_velho"])
        self.assertTrue(x["trend_em"])
        # Envelhecido à mão: passados mais dias do que o config aceita.
        velho = (datetime.now(timezone.utc) - timedelta(days=9)).isoformat(timespec="seconds")
        con.execute("UPDATE cardmarket_trend SET updated_at = ?", (velho,))
        x = self.venda.itens(con)[0]
        self.assertTrue(x["trend_velho"])
        self.assertEqual(x["trend_dias"], 9)
        self.assertEqual(x["trend"], 999, "velho NÃO é apagado")
        self.assertEqual(self.venda.conta([x])["trend_velho"], 1)
        # O prazo vem do config.
        self.cfg_venda({"trend_valido_dias": 30})
        self.assertFalse(self.venda.itens(con)[0]["trend_velho"])

    def test_apagar_o_trend_e_recusar_um_negativo(self):
        con = self.catalogo()
        self.venda.juntar(con, "TST-001", 1, source="test")
        self.venda.guardar_trend(con, "TST-001", 500, source="test")
        self.venda.guardar_trend(con, "TST-001", None, source="test")
        self.assertIsNone(self.venda.itens(con)[0]["trend"])
        with self.assertRaises(ValueError):
            self.venda.guardar_trend(con, "TST-001", -1, source="test")

    def test_o_texto_da_conta_diz_as_linhas_sem_trend(self):
        con = self.catalogo()
        self.venda.juntar(con, "TST-001", 2, source="test")
        self.venda.juntar(con, "TST-002", 1, source="test")
        self.venda.guardar_trend(con, "TST-001", 250, source="test")
        txt = self.venda.texto(self.venda.itens(con))
        self.assertIn("2x Defy", txt)
        self.assertIn("5,00", txt, "2 × 2,50 €")
        self.assertIn("sem Trend", txt)
        self.assertIn("TOTAL: 5,00 €", txt)
        self.assertIn("Trend do Cardmarket", txt)
        # O preço do CardTrader (9,00 € do Brutalizer) não aparece em lado nenhum.
        self.assertNotIn("9,00", txt)

    def test_o_payload_diz_de_onde_vem_cada_preco(self):
        con = self.catalogo()
        self.venda.juntar(con, "TST-002", 1, source="test")
        p = self.venda.payload(con)
        self.assertIn("trend", p["items"][0])
        self.assertIn("price", p["items"][0])
        self.assertEqual(p["totals"]["cents"], 0)
        self.assertEqual(p["trend_valido_dias"], 7)


class TestOLinkDoCardmarket(Base):
    """3. Cada linha leva o link da carta no Cardmarket."""

    def test_usa_o_cardmarket_id_quando_existe(self):
        con = self.catalogo()
        self.venda.juntar(con, "TST-001", 1, source="test")
        x = self.venda.itens(con)[0]
        self.assertEqual(x["cardmarket_id"], 845712)
        self.assertIn("845712", x["url"])
        self.assertIn("cardmarket.com", x["url"])

    def test_sem_id_cai_na_pesquisa_pelo_nome_de_mercado(self):
        con = self.catalogo()
        self.venda.juntar(con, "TST-T01", 1, source="test")
        x = self.venda.itens(con)[0]
        self.assertIsNone(x["cardmarket_id"])
        self.assertIn("searchString=Recruit", x["url"])

    def test_o_nome_e_o_do_mercado_e_vai_codificado(self):
        con = self.catalogo()
        self.venda.juntar(con, "TST-003", 1, source="test")
        x = self.venda.itens(con)[0]
        self.assertEqual(x["market_name"], "Azir - Emperor of the Sands")
        self.assertIn("Azir%20-%20Emperor", x["url_busca"])
        self.assertNotIn(" ", x["url_busca"])

    def test_o_template_vem_do_config(self):
        con = self.catalogo()
        self.cfg_venda({"cardmarket_url": "https://exemplo/{id}"})
        self.venda.juntar(con, "TST-001", 1, source="test")
        self.assertEqual(self.venda.itens(con)[0]["url"], "https://exemplo/845712")


class TestNaoMexeEmNadaDaColecao(Base):
    """4. Marcar cartas para venda não pode alterar UM ÚNICO número."""

    def fotografia(self, con) -> dict:
        """Tudo o que é número do site: níveis, denominador, as três barras, o
        painel, as wantlists, o valor, os totais, a grelha, o playset jogável,
        as Faltas, as Encomendas, o A mais, os decks, o foil e o `copies`."""
        cfg = self.config.load()
        sp = self.metrics.set_payload(con, "TST")
        idx = self.metrics.index_payload(con)
        fe = self.faltas_edicao.payload(con, cfg)
        am = self.a_mais.payload(con, cfg)
        return {
            "niveis": [(l["k"], l["done"], l["total"], l["missing"], l["cents"])
                       for l in self.metrics.niveis_payload(con, cfg)["levels"]],
            "wantlist": {k: self.a_subir.wantlist(con, cfg=cfg)[k]
                         for k in ("text", "lines", "copies", "cents")},
            "valor": self.prices.collection_value(con)["cents"],
            "valor_copias": self.prices.collection_value(con)["copias"],
            "valor_por_set": self.prices.value_by_set(con),
            "totais": self.collection.totals(con),
            "grelha": [(p["id"], p["qty"], p["qty_total"], p["qty_valor"], p["target"],
                        p["block"], p["foil"], p["foil_ok"])
                       for g in sp["groups"] for p in g["printings"]],
            "playset": {g["card_key"]: g["playset"] for g in sp["groups"]},
            "owned_by_card": self.metrics.owned_by_card(con),
            "barras": (sp["progress"]["playset"], sp["progress"]["master"],
                       sp["progress"]["value"], sp["progress"]["rarities"]),
            "painel": sp["progress"]["painel"],
            "painel_geral": idx["painel"],
            "blocos": sp["blocks"],
            "faltas": (fe["totals"], fe["totals_lists"],
                       [(s["set"], b["id"], b["cards"], b["copies"], b["cents"])
                        for s in fe["sets"] for b in s["blocks"]]),
            "encomendas": self.pending.encomendas(con)["totals"],
            "a_mais": {s["set"]: [(x["printing_id"], x["extra"], x["have"])
                                  for x in s["excedente"]["items"]] for s in am["sets"]},
            "decks": self.decks.resumo_das_faltas(con),
            "uso": self.decks.uso_por_carta(con),
            "copies": sorted((r["printing_id"], r["qty"], r["qty_foil"]) for r in
                             con.execute("SELECT printing_id, qty, qty_foil FROM copies")),
            "locais": self.locais.resumo(con),
        }

    def test_meter_e_tirar_da_venda_nao_mexe_em_numero_nenhum(self):
        con = self.catalogo()
        self.com_deck(con)
        antes = self.fotografia(con)

        self.venda.juntar(con, "TST-001", 3, source="test")
        self.venda.juntar(con, "TST-002", 2, source="test")
        self.venda.juntar(con, "TST-003", 1, source="test")
        self.assertEqual(self.fotografia(con), antes,
                         "6 cópias marcadas para venda e NADA mexeu")
        # Com Trends metidos também não: o Trend é um preço dele, não um valor
        # da coleção (o valor continua a ser o do CardTrader).
        self.venda.guardar_trend(con, "TST-001", 9999, source="test")
        self.venda.guardar_trend(con, "TST-002", 8888, source="test")
        self.assertEqual(self.fotografia(con), antes,
                         "o Trend não mexe no valor da coleção")
        # E a tirar.
        self.venda.juntar(con, "TST-001", -3, source="test")
        self.venda.limpar(con)
        self.assertEqual(self.fotografia(con), antes)

    def test_nem_o_copies_nem_o_ops_nem_os_locais(self):
        con = self.catalogo()
        qty = sorted((r["printing_id"], r["qty"]) for r in
                     con.execute("SELECT printing_id, qty FROM copies"))
        ops = con.execute("SELECT COUNT(*) AS n FROM ops").fetchone()["n"]
        locs = con.execute("SELECT COUNT(*) AS n FROM copy_locations").fetchone()["n"]
        pend = con.execute("SELECT COUNT(*) AS n FROM pending").fetchone()["n"]
        self.venda.juntar(con, "TST-001", 2, source="test")
        self.venda.guardar_trend(con, "TST-001", 100, source="test")
        self.assertEqual(sorted((r["printing_id"], r["qty"]) for r in
                                con.execute("SELECT printing_id, qty FROM copies")), qty)
        self.assertEqual(con.execute("SELECT COUNT(*) AS n FROM ops").fetchone()["n"], ops)
        self.assertEqual(con.execute("SELECT COUNT(*) AS n FROM copy_locations"
                                     ).fetchone()["n"], locs)
        self.assertEqual(con.execute("SELECT COUNT(*) AS n FROM pending").fetchone()["n"],
                         pend)

    def test_ler_a_venda_nao_escreve(self):
        con = self.catalogo()
        self.venda.juntar(con, "TST-001", 1, source="test")
        antes = con.execute("SELECT COUNT(*) AS n FROM sale_log").fetchone()["n"]
        self.venda.payload(con)
        self.venda.itens(con)
        self.venda.procurar(con, "defy")
        self.assertEqual(con.execute("SELECT COUNT(*) AS n FROM sale_log").fetchone()["n"],
                         antes)
        self.assertEqual(self.venda.linhas(con), {"tst-001-100": 1})

    def test_nenhum_modulo_de_contas_importa_a_venda(self):
        """Só o `server`, o `build` e a `cli` a chamam. Se um módulo de contas
        passar a lê-la, é sinal de que a venda entrou numa conta — e não pode."""
        proibidos = ["a_subir", "faltas", "faltas_edicao", "a_mais", "uso_decks",
                     "decks", "locais", "pending", "prices", "painel", "runas_vista",
                     "cardmarket", "seguir", "catalog", "metrics", "collection",
                     "proprias", "foil"]
        for nome in proibidos:
            fonte = (REPO / "riftvault" / f"{nome}.py").read_text(encoding="utf-8")
            self.assertNotIn("import venda", fonte, nome)
            self.assertNotIn("from .venda", fonte, nome)
            self.assertNotIn("sale_lines", fonte, nome)
            self.assertNotIn("cardmarket_trend", fonte, nome)


class TestMarcarComoVendidas(Base):
    """5. O botão separado — com confirmação, com registo, e com undo."""

    def test_sem_confirmar_nao_mexe_em_nada(self):
        con = self.catalogo()
        self.venda.juntar(con, "TST-001", 2, source="test")
        with self.assertRaises(self.venda.PrecisaConfirmar):
            self.venda.vender(con, source="test")
        self.assertEqual(self.collection.get_qty(con, "tst-001-100"), 3)
        self.assertEqual(self.venda.linhas(con), {"tst-001-100": 2})
        self.assertEqual(con.execute("SELECT COUNT(*) AS n FROM sale_log").fetchone()["n"], 0)

    def test_vender_baixa_as_copias_e_esvazia_a_lista(self):
        con = self.catalogo()
        self.venda.juntar(con, "TST-001", 2, source="test")
        self.venda.juntar(con, "TST-002", 1, source="test")
        self.venda.guardar_trend(con, "TST-001", 250, source="test")
        res = self.venda.vender(con, confirmar=True, source="test")
        self.assertEqual(self.collection.get_qty(con, "tst-001-100"), 1)
        self.assertEqual(self.collection.get_qty(con, "tst-002-100"), 1)
        self.assertEqual(self.venda.linhas(con), {}, "a venda fica vazia")
        self.assertEqual(res["copies"], 3)
        self.assertEqual(res["totals"]["cents"], 500)

    def test_o_registo_guarda_o_trend_da_altura(self):
        con = self.catalogo()
        self.venda.juntar(con, "TST-001", 2, source="test")
        self.venda.guardar_trend(con, "TST-001", 250, source="test")
        res = self.venda.vender(con, confirmar=True, source="test")
        linhas = self.venda.venda_do_log(con, res["sale_id"])
        self.assertEqual(len(linhas), 1)
        self.assertEqual((linhas[0]["qty"], linhas[0]["unit_cents"]), (2, 250))
        # Mudar o Trend hoje não muda a conta da venda de ontem.
        self.venda.guardar_trend(con, "TST-001", 9999, source="test")
        self.assertEqual(self.venda.venda_do_log(con, res["sale_id"])[0]["unit_cents"], 250)
        h = self.venda.historico(con)
        self.assertEqual((h[0]["copies"], h[0]["cents"]), (2, 500))

    def test_fica_na_ops_e_da_para_desfazer(self):
        con = self.catalogo()
        self.venda.juntar(con, "TST-001", 2, source="test")
        self.venda.vender(con, confirmar=True, source="test")
        op = con.execute("SELECT * FROM ops ORDER BY id DESC LIMIT 1").fetchone()
        self.assertEqual((op["delta"], op["source"]), (-2, "test"))
        self.collection.undo_last(con, source="test")
        self.assertEqual(self.collection.get_qty(con, "tst-001-100"), 3,
                         "o desfazer de sempre repõe as cópias")

    def test_vender_mais_do_que_tem_baixa_o_que_ha_e_diz_quanto_faltou(self):
        con = self.catalogo()
        self.venda.juntar(con, "TST-003", 3, source="test")    # tem 1
        res = self.venda.vender(con, confirmar=True, source="test")
        self.assertEqual(self.collection.get_qty(con, "tst-003-100"), 0)
        self.assertEqual(res["copies"], 1)
        self.assertEqual(res["em_falta"], 2)

    def test_vender_uma_venda_vazia_rebenta(self):
        con = self.catalogo()
        with self.assertRaises(self.venda.VendaVazia):
            self.venda.vender(con, confirmar=True, source="test")

    def test_depois_de_vender_a_colecao_desceu(self):
        """A única maneira de a Venda mexer na Coleção — e é explícita."""
        con = self.catalogo()
        antes = self.prices.collection_value(con)["cents"]
        self.venda.juntar(con, "TST-002", 1, source="test")
        self.venda.vender(con, confirmar=True, source="test")
        self.assertEqual(self.prices.collection_value(con)["cents"], antes - 900)


class TestOsAvisos(Base):
    """6. Avisa, não bloqueia."""

    def test_vender_mais_do_que_tem_avisa_e_deixa(self):
        con = self.catalogo()
        self.venda.juntar(con, "TST-003", 3, source="test")    # tem 1
        x = self.venda.itens(con)[0]
        self.assertEqual((x["have"], x["a_mais_do_que_tens"]), (1, 2))
        self.assertEqual(self.venda.conta([x])["avisos_stock"], 1)
        self.assertEqual(self.venda.linhas(con), {"tst-003-100": 3}, "não bloqueou")

    def test_a_carta_de_um_deck_montado_avisa(self):
        con = self.catalogo()
        self.com_deck(con, montados=["Azir"])
        self.venda.juntar(con, "TST-001", 1, source="test")
        x = self.venda.itens(con)[0]
        self.assertTrue(x["em_decks"], "o Defy está no deck montado")
        self.assertEqual(self.venda.conta([x])["em_decks"], 1)

    def test_um_deck_desmontado_nao_avisa(self):
        """Um deck desmontado não está a usar cópia nenhuma (2026-09-24)."""
        con = self.catalogo()
        self.com_deck(con, montados=[])
        self.venda.juntar(con, "TST-001", 1, source="test")
        self.assertEqual(self.venda.itens(con)[0]["em_decks"], [])


class TestRotaBuildCLI(Base):
    """7. As rotas, o site publicado, a CLI e o frontend."""

    def test_as_rotas(self):
        con = self.catalogo()
        con.close()
        from riftvault import server
        importlib.reload(server)
        server.app.testing = True
        with server.app.test_client() as c:
            self.assertEqual(c.get("/api/venda.json").get_json()["totals"]["lines"], 0)
            r = c.post("/api/venda/linha", json={"printing_id": "tst-001-100", "delta": 2})
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.get_json()["totals"]["copies"], 2)
            # O Trend vem em euros, com vírgula ou ponto.
            r = c.post("/api/venda/trend", json={"printing_id": "tst-001-100", "eur": "12,50"})
            self.assertEqual(r.get_json()["items"][0]["trend"], 1250)
            self.assertEqual(r.get_json()["totals"]["cents"], 2500)
            r = c.post("/api/venda/trend", json={"printing_id": "tst-001-100", "eur": ""})
            self.assertIsNone(r.get_json()["items"][0]["trend"])
            self.assertEqual(r.get_json()["totals"]["cents"], 0, "sem Trend, ZERO")
            self.assertEqual(c.post("/api/venda/trend",
                                    json={"printing_id": "tst-001-100", "eur": "abc"}
                                    ).status_code, 400)
            self.assertEqual(c.post("/api/venda/linha",
                                    json={"printing_id": "nao-existe", "delta": 1}
                                    ).status_code, 404)
            self.assertEqual(c.post("/api/venda/linha",
                                    json={"printing_id": "tst-002-100", "delta": -1}
                                    ).status_code, 400)
            self.assertEqual(c.post("/api/venda/linha",
                                    json={"printing_id": "tst-001-100", "delta": 0}
                                    ).status_code, 400)
            hits = c.get("/api/venda/procurar?q=defy").get_json()["items"]
            self.assertIn("tst-001-100", [x["printing_id"] for x in hits])
            # «marcar como vendidas» RECUSA sem confirmação, e não mexe.
            r = c.post("/api/venda/vender", json={})
            self.assertEqual(r.status_code, 409)
            self.assertEqual(c.get("/api/venda.json").get_json()["totals"]["copies"], 2)
            r = c.post("/api/venda/vender", json={"confirmar": True})
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.get_json()["vendida"]["copies"], 2)
            self.assertEqual(r.get_json()["totals"]["lines"], 0)
            g = c.get("/api/set/TST.json").get_json()
            tile = next(p for grp in g["groups"] for p in grp["printings"]
                        if p["id"] == "tst-001-100")
            self.assertEqual(tile["qty"], 1, "as cópias desceram, e só agora")
            c.post("/api/venda/linha", json={"printing_id": "tst-001-100", "delta": 1})
            self.assertEqual(c.post("/api/venda/limpar", json={}).get_json()["limpas"], 1)

    def test_o_site_publicado_leva_a_venda_e_nao_leva_controlos(self):
        con = self.catalogo()
        self.venda.juntar(con, "TST-001", 2, source="test")
        self.venda.guardar_trend(con, "TST-001", 300, source="test")
        con.close()
        from riftvault import build
        importlib.reload(build)
        saida = self.v.root / "site"
        build.build(saida, log=lambda *_: None)
        p = json.loads((saida / "api" / "venda.json").read_text(encoding="utf-8"))
        self.assertFalse(p["editable"])
        self.assertEqual(p["totals"]["cents"], 600)
        js = (saida / "app.js").read_text(encoding="utf-8")
        self.assertIn("function renderVenda", js)

    def test_a_cli(self):
        con = self.catalogo()
        con.close()
        from riftvault import cli
        importlib.reload(cli)

        def correr(argv, esperado=0):
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                self.assertEqual(cli.main(argv), esperado, err.getvalue())
            return out.getvalue(), err.getvalue()

        out, _ = correr(["venda"])
        self.assertIn("Não há nada na venda", out)
        out, _ = correr(["venda", "--juntar", "TST-001", "2"])
        self.assertIn("Defy", out)
        self.assertIn("por meter", out, "diz que falta o Trend")
        out, err = correr(["venda"])
        self.assertIn("TOTAL: 0.00 €", out)
        self.assertIn("FALTAM 1 linha sem Trend", err)
        out, _ = correr(["venda", "--trend", "TST-001", "12,50"])
        self.assertIn("12.50", out)
        self.assertIn("TOTAL: 25.00 €", out)
        # `--vender` sem `--sim` não mexe.
        _, err = correr(["venda", "--vender"], esperado=1)
        self.assertIn("confirma", err.lower())
        out, _ = correr(["venda", "--vender", "--sim"])
        self.assertIn("venda fechada", out)
        out, _ = correr(["venda"])
        self.assertIn("Não há nada na venda", out)

    def test_o_app_js_e_o_html_desenham_a_venda(self):
        js = APP_JS.read_text(encoding="utf-8")
        for f in ("function renderVenda", "function vdLinha", "function renderVdConta",
                  "function venderDaGrelha", "async function vdTrend"):
            self.assertIn(f, js)
        self.assertIn("'venda'", js)
        self.assertIn("api/venda/trend", js)
        self.assertIn("api/venda/vender", js)
        # O botão de vender pede confirmação ANTES de chamar a rota.
        troço = js[js.index("$('#vd-vender').onclick"):js.index("/* O que o `a_subir")]
        self.assertIn("confirm(", troço)
        self.assertIn("confirmar: true", troço)
        # A linha nunca usa o preço do CardTrader como Trend.
        linha = js[js.index("function vdLinha"):js.index("function vdLigarLinhas")]
        self.assertIn("CardTrader, só referência", linha)
        self.assertNotIn("x.trend || x.price", linha)
        html = (REPO / "riftvault" / "web" / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="sec-venda"', html)
        css = (REPO / "riftvault" / "web" / "style.css").read_text(encoding="utf-8")
        self.assertIn(".vd-linha", css)
        self.assertIn(".vd-tab", css)

    def test_a_conta_cabe_no_telemovel(self):
        """A 375 px a tabela de seis colunas vira cartões — é onde ele vai
        estar, com o comprador à frente."""
        css = (REPO / "riftvault" / "web" / "style.css").read_text(encoding="utf-8")
        i = css.index(".vd-tab thead { display: none; }")
        # A regra está dentro de um @media de telemóvel.
        antes = css[:i]
        self.assertIn("@media (max-width: 559px)", antes[antes.rindex("@media"):])
        self.assertIn(".vd-tab td::before { content: attr(data-l)", css)
        # Nada nesta secção corre para o lado.
        troço = css[css.index('/* ================================================================= «VENDA»'):]
        self.assertNotIn("overflow-x: auto", troço.split("TELEMÓVEL")[0])


if __name__ == "__main__":
    unittest.main()

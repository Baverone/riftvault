"""O separador «Produto Selado» (André, 2026-09-25).

Palavras dele: *"faz uma lista, para acrescentar um separador que e 'Produto
Selado', em que vai tudo o que e produtos de coleccao do Riftbound, como
displays ou boxcase, ou duel decks, proving ground, etc etc, para eu saber o
que ha, o que tenho e o que nao tenho"*.

O que se fixa:
  1. a LISTA e a sua fonte: as CATEGORIAS do CardTrader decidem o que é selado
     e o que é single (a 258 são as cartas); os acessórios ficam de fora e são
     contados, nunca apagados em silêncio;
  2. o TIPO de cada produto — display, case, caixa, Proving Grounds, deck,
     bundle, booster, conjunto —, pela categoria e corrigido pelo nome;
  3. os TRÊS ESTADOS: o que há, o que tem, o que não tem, com os contadores e
     o filtro;
  4. POR SAIR: um produto de uma edição que ainda não saiu aparece marcado e
     **não conta para o que falta**;
  5. os `+`/`−`: sobem, descem, travam em zero, e um produto inventado rebenta;
  6. **O SELADO NÃO ENTRA NA COLEÇÃO**: uma fotografia de tudo o que é número
     do site, antes e depois de meter e tirar produto — e o VALOR do selado é
     um total próprio, que não vai parar ao valor da Coleção;
  7. a chave `selado.extra` do config, para acrescentar à mão;
  8. a rota, o site publicado (só leitura), a CLI, o `app.js`/`index.html`/CSS
     e o respeito pelo `abas.escondidas`.

Tudo contra pastas temporárias (`tests.fixture.Vault`) e um config temporário
(`RIFTVAULT_CONFIG`): o `data/` e o `riftvault_config.json` a sério nunca são
tocados, e **não se fala com a rede** — o catálogo do CardTrader é escrito à
mão em cada teste.
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
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ["RIFTVAULT_CONFIG"] = str(Path(tempfile.gettempdir()) / "riftvault-nao-existe.json")

from tests.fixture import REPO, Vault  # noqa: E402

APP_JS = REPO / "riftvault" / "web" / "app.js"
INDEX = REPO / "riftvault" / "web" / "index.html"
CSS = REPO / "riftvault" / "web" / "style.css"

# Um catálogo do CardTrader de brincar, com a mesma forma do real: as seis
# categorias de selado que contam, duas de acessórios que não contam, e uma
# edição por sair.
CATALOGO = {
    "generated_at": "2026-09-25T10:00:00+00:00",
    "fonte": "cardtrader",
    "categorias": {"258": "Riftbound Singles", "259": "Riftbound Booster Boxes",
                   "260": "Riftbound Boosters", "261": "Riftbound Bundles",
                   "262": "Riftbound Starter Decks",
                   "263": "Riftbound Box Sets & Displays",
                   "264": "Riftbound Playmats", "266": "Riftbound Sleeves",
                   "283": "Riftbound Complete Sets"},
    "expansoes": [{"id": 1, "code": "TST", "name": "Teste"},
                  {"id": 2, "code": "FUT", "name": "Futuro"}],
    "produtos": [
        {"blueprint_id": 101, "nome": "Teste Booster Box", "versao": "",
         "categoria_id": 259, "edicao": "TST", "edicao_nome": "Teste",
         "img": "https://cardtrader.com/x.jpg", "cardmarket_id": 900001},
        {"blueprint_id": 102, "nome": "Teste Booster Box Case",
         "versao": "x6 Booster Boxes", "categoria_id": 263, "edicao": "TST",
         "edicao_nome": "Teste", "img": None, "cardmarket_id": None},
        {"blueprint_id": 103, "nome": "Teste: Proving Grounds", "versao": "",
         "categoria_id": 263, "edicao": "TST", "edicao_nome": "Teste",
         "img": None, "cardmarket_id": None},
        {"blueprint_id": 104, "nome": 'Teste: "Jinx" Champion Deck', "versao": "",
         "categoria_id": 262, "edicao": "TST", "edicao_nome": "Teste",
         "img": None, "cardmarket_id": None},
        {"blueprint_id": 105, "nome": "Teste Vault", "versao": "",
         "categoria_id": 261, "edicao": "TST", "edicao_nome": "Teste",
         "img": None, "cardmarket_id": None},
        {"blueprint_id": 106, "nome": "Teste Booster", "versao": "",
         "categoria_id": 260, "edicao": "TST", "edicao_nome": "Teste",
         "img": None, "cardmarket_id": None},
        {"blueprint_id": 107, "nome": "Teste: Poro Scene Set", "versao": "6 Card Set",
         "categoria_id": 283, "edicao": "TST", "edicao_nome": "Teste",
         "img": None, "cardmarket_id": None},
        # Acessórios — NÃO são produto selado.
        {"blueprint_id": 108, "nome": "Teste: Ahri Art Playmat", "versao": "",
         "categoria_id": 264, "edicao": "TST", "edicao_nome": "Teste",
         "img": None, "cardmarket_id": None},
        {"blueprint_id": 109, "nome": "Teste: Ahri Art Sleeves", "versao": "100 Sleeves",
         "categoria_id": 266, "edicao": "TST", "edicao_nome": "Teste",
         "img": None, "cardmarket_id": None},
        {"blueprint_id": 110, "nome": "Teste: Jinx Art Sleeves", "versao": "100 Sleeves",
         "categoria_id": 266, "edicao": "TST", "edicao_nome": "Teste",
         "img": None, "cardmarket_id": None},
        # A edição por sair.
        {"blueprint_id": 201, "nome": "Futuro Booster Box", "versao": "",
         "categoria_id": 259, "edicao": "FUT", "edicao_nome": "Futuro",
         "img": None, "cardmarket_id": None},
        {"blueprint_id": 202, "nome": "Futuro Booster", "versao": "",
         "categoria_id": 260, "edicao": "FUT", "edicao_nome": "Futuro",
         "img": None, "cardmarket_id": None},
    ],
    "precos": {
        "101": {"cents": 16064, "currency": "EUR", "day": "2026-09-25",
                "n_listings": 51, "n_sellers": 30, "n_copies": 80},
        "102": {"cents": 114064, "currency": "EUR", "day": "2026-09-25",
                "n_listings": 3, "n_sellers": 3, "n_copies": 3},
        "104": {"cents": 3251, "currency": "EUR", "day": "2026-09-25",
                "n_listings": 9, "n_sellers": 8, "n_copies": 12},
        "103": {"cents": None, "currency": "EUR", "day": "2026-09-25",
                "n_listings": 0, "n_sellers": 0, "n_copies": 0},
        "201": {"cents": 13418, "currency": "EUR", "day": "2026-09-25",
                "n_listings": 2, "n_sellers": 2, "n_copies": 2},
    },
}

# Datas: a TST já saiu, a FUT sai daqui a um ano.
DATAS = {"TST": "2025-01-31", "FUT": f"{date.today().year + 1}-05-01"}


class Base(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.close)
        from riftvault import (a_mais, a_subir, collection, config, db, decks, faltas,
                               faltas_edicao, foil, locais, metrics, painel, pending,
                               prices, proprias, selado, venda)
        for m in (locais, metrics, foil, painel, decks, proprias, a_subir,
                  faltas_edicao, a_mais, pending, faltas, prices, venda, selado):
            importlib.reload(m)
        self.config, self.db, self.selado, self.locais = config, db, selado, locais
        self.metrics, self.painel, self.decks = metrics, painel, decks
        self.a_subir, self.faltas_edicao, self.a_mais = a_subir, faltas_edicao, a_mais
        self.pending, self.faltas, self.prices = pending, faltas, prices
        self.collection, self.foil, self.venda = collection, foil, venda
        self.cfg_selado({})
        self.escrever_catalogo(CATALOGO)

    # -- config e catálogo ------------------------------------------------

    def cfg_selado(self, extra_selado: dict, extra: dict | None = None):
        caminho = self.v.root / "config.json"
        caminho.write_text(json.dumps({
            "selado": {**self.selado.DEFAULTS, "datas_por_edicao": DATAS,
                       "por_sair": [], "ordem_das_edicoes": ["TST", "FUT"],
                       **extra_selado},
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

    def escrever_catalogo(self, dados: dict):
        self.config.SELADO_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.config.SELADO_PATH.write_text(json.dumps(dados, ensure_ascii=False),
                                           encoding="utf-8")
        self.selado._cache = None       # a cache é por mtime; num teste é instantâneo

    # -- o catálogo de CARTAS, para a fotografia ---------------------------

    def catalogo(self):
        """Uma edição com uma comum, uma rara, um Legend, uma alt art e um
        token. Na Coleção: 3 Defy, 2 Brutalizer, 1 Legend, 1 alt art."""
        con = self.v.connect()
        v = self.v
        v.add_printing(con, "tst-001-100", "TST", 1, "Defy", rarity="common", size=100)
        v.add_printing(con, "tst-001a-100", "TST", 1, "Defy", variant="a", kind="alt_art",
                       rarity="showcase", base_rarity="common", size=100)
        v.add_printing(con, "tst-002-100", "TST", 2, "Brutalizer", rarity="rare", size=100)
        v.add_printing(con, "tst-003-100", "TST", 3, "Emperor of the Sands",
                       card_type="Legend", rarity="epic", size=100)
        v.rebuild(con)
        for pid, cents in (("tst-001-100", 111), ("tst-001a-100", 500),
                           ("tst-002-100", 900), ("tst-003-100", 4000)):
            con.execute("INSERT INTO catalog.price_latest (printing_id, price_cents) "
                        "VALUES (?,?)", (pid, cents))
        for pid, n in (("tst-001-100", 3), ("tst-001a-100", 1), ("tst-002-100", 2),
                       ("tst-003-100", 1)):
            self.collection.adjust(con, pid, n, source="test")
        self.addCleanup(con.close)
        return con

    def con(self):
        con = self.v.connect()
        self.addCleanup(con.close)
        return con

    def por_id(self, lista, pid):
        for x in lista:
            if x["id"] == pid:
                return x
        raise AssertionError(f"{pid} não está na lista: {[x['id'] for x in lista]}")


# ---------------------------------------------------------------------------
# 1. A LISTA, e de onde vem
# ---------------------------------------------------------------------------


class TestAListaEAFonte(Base):

    def test_a_separacao_selado_single_e_a_categoria_do_cardtrader(self):
        """A 258 são as CARTAS; o produto selado são as outras categorias. Não
        é um palpite: é a tabela `GET /categories` deles."""
        from riftvault.prices import SINGLES_CATEGORY
        self.assertEqual(SINGLES_CATEGORY, 258)
        ids = {x["id"] for x in self.selado.itens(self.con())}
        self.assertEqual(ids, {f"ct-{b}" for b in
                               (101, 102, 103, 104, 105, 106, 107, 201, 202)})

    def test_os_acessorios_ficam_de_fora_e_sao_contados(self):
        """Playmats e sleeves não são produto selado — mas a página diz quantos
        são, em vez de os apagar em silêncio."""
        lista = self.selado.itens(self.con())
        self.assertFalse([x for x in lista if "Playmat" in x["nome"]])
        self.assertEqual(self.selado.fora(),
                         [{"categoria_id": 264, "categoria": "Riftbound Playmats", "n": 1},
                          {"categoria_id": 266, "categoria": "Riftbound Sleeves", "n": 2}])

    def test_meter_os_playmats_e_uma_linha_de_config(self):
        self.cfg_selado({"categorias": [259, 264]})
        nomes = {x["nome"] for x in self.selado.itens(self.con())}
        self.assertIn("Teste: Ahri Art Playmat", nomes)
        self.assertNotIn("Teste Booster", nomes, "a 260 saiu da lista")

    def test_escrever_a_categoria_das_cartas_rebenta(self):
        self.cfg_selado({"categorias": [258, 259]})
        with self.assertRaises(ValueError) as e:
            self.selado.itens(self.con())
        self.assertIn("258", str(e.exception))

    def test_a_lista_de_categorias_vazia_rebenta(self):
        self.cfg_selado({"categorias": []})
        with self.assertRaises(ValueError):
            self.selado.itens(self.con())

    def test_sem_ficheiro_nenhum_a_lista_e_vazia_e_nao_rebenta(self):
        self.config.SELADO_PATH.unlink()
        self.selado._cache = None
        p = self.selado.payload(self.con())
        self.assertEqual(p["items"], [])
        self.assertEqual(p["totals"]["ha"], 0)

    def test_a_ordem_e_a_do_config_depois_o_tipo_e_o_nome(self):
        lista = self.selado.itens(self.con())
        self.assertEqual([x["edicao"] for x in lista],
                         ["TST"] * 7 + ["FUT"] * 2)
        self.assertEqual([x["tipo"] for x in lista][:7],
                         ["display", "case", "proving-grounds", "deck",
                          "bundle", "booster", "conjunto"])

    def test_o_preco_vem_do_ficheiro_e_diz_quantos_nao_tem(self):
        lista = self.selado.itens(self.con())
        self.assertEqual(self.por_id(lista, "ct-101")["preco_cents"], 16064)
        self.assertIsNone(self.por_id(lista, "ct-103")["preco_cents"])
        # 103 tem linha com `cents: None`; 105, 106, 107 e 202 nem linha têm.
        self.assertEqual(self.selado.contar(lista)["sem_preco"], 5)


# ---------------------------------------------------------------------------
# 2. O TIPO
# ---------------------------------------------------------------------------


class TestOsTipos(Base):

    def test_a_categoria_decide(self):
        t = self.selado.tipo_de
        self.assertEqual(t("Origins Booster Box", "", 259), "display")
        self.assertEqual(t("Origins Booster", "", 260), "booster")
        self.assertEqual(t("Unleashed Vault", "", 261), "bundle")
        self.assertEqual(t('Origins: "Jinx" Champion Deck', "", 262), "deck")
        self.assertEqual(t("Arcane Box Set", "6 Card Set", 263), "caixa")
        self.assertEqual(t("Arcane Complete Set", "", 283), "conjunto")

    def test_o_nome_corrige_a_categoria_nas_duas_que_ele_nomeou(self):
        """*"displays ou boxcase, ou duel decks, proving ground"* — o case e o
        Proving Grounds vivem os dois na categoria 263, e são coisas
        diferentes para quem coleciona."""
        t = self.selado.tipo_de
        self.assertEqual(t("Origins Booster Box Case", "x6 Booster Boxes", 263), "case")
        self.assertEqual(t("2025 Trial Deck Case", "x4 Trial Decks", 263), "case")
        self.assertEqual(t("Origins: Proving Grounds", "", 263), "proving-grounds")
        self.assertEqual(t("Legacy: Proving Grounds", "", 263), "proving-grounds")

    def test_uma_categoria_que_nao_se_conheca_e_outro(self):
        self.assertEqual(self.selado.tipo_de("Coisa nova", "", 999), "outro")
        self.assertEqual(self.selado.tipo_de("Coisa nova", "", None), "outro")

    def test_o_duel_deck_e_um_deck(self):
        """Ele chamou-lhes *"duel decks"*; no CardTrader são «Showdown Deck»,
        na categoria dos Starter Decks."""
        self.assertEqual(
            self.selado.tipo_de('Vendetta: "Zed vs Shen" Showdown Deck', "", 262), "deck")

    def test_o_payload_so_traz_os_tipos_que_existem(self):
        tipos = [t["id"] for t in self.selado.payload(self.con())["tipos"]]
        self.assertEqual(tipos, ["display", "case", "proving-grounds",
                                 "deck", "bundle", "booster", "conjunto"],
                         "só os que a lista tem, e pela ordem do catálogo")


# ---------------------------------------------------------------------------
# 3. OS TRÊS ESTADOS
# ---------------------------------------------------------------------------


class TestOsTresEstados(Base):

    def test_comeca_tudo_a_zero(self):
        t = self.selado.payload(self.con())["totals"]
        self.assertEqual((t["ha"], t["tenho"], t["copias"]), (9, 0, 0))
        self.assertEqual(t["valor_cents"], 0)

    def test_ha_tenho_nao_tenho(self):
        con = self.con()
        self.selado.ajustar(con, "ct-101", 2, source="test")
        self.selado.ajustar(con, "ct-104", 1, source="test")
        t = self.selado.payload(con)["totals"]
        self.assertEqual(t["ha"], 9, "o que HÁ é a lista toda")
        self.assertEqual(t["saiu"], 7, "dois são de uma edição por sair")
        self.assertEqual(t["tenho"], 2, "dois produtos diferentes")
        self.assertEqual(t["copias"], 3, "três unidades ao todo")
        self.assertEqual(t["falta"], 5, "7 saíram, tem 2")
        self.assertEqual(t["pct"], 28.6)

    def test_o_que_falta_nao_conta_os_por_sair(self):
        t = self.selado.payload(self.con())["totals"]
        self.assertEqual(t["falta"], 7, "os 2 da FUT não contam como falta")
        self.assertEqual(t["por_sair"], 2)
        self.assertEqual(t["falta"] + t["tenho"], t["saiu"])

    def test_por_edicao_soma_ao_total(self):
        con = self.con()
        self.selado.ajustar(con, "ct-101", 1, source="test")
        p = self.selado.payload(con)
        self.assertEqual([g["set"] for g in p["sets"]], ["TST", "FUT"])
        self.assertEqual(sum(g["totals"]["ha"] for g in p["sets"]), p["totals"]["ha"])
        self.assertEqual(sum(g["totals"]["tenho"] for g in p["sets"]),
                         p["totals"]["tenho"])
        self.assertEqual(sum(g["totals"]["falta"] for g in p["sets"]),
                         p["totals"]["falta"])

    def test_o_payload_diz_o_que_e_preciso_para_o_filtro(self):
        con = self.con()
        self.selado.ajustar(con, "ct-101", 1, source="test")
        lista = self.selado.payload(con)["items"]
        tem = self.por_id(lista, "ct-101")
        self.assertTrue(tem["tenho"])
        self.assertFalse(tem["por_sair"])
        self.assertFalse(self.por_id(lista, "ct-104")["tenho"])
        self.assertTrue(self.por_id(lista, "ct-201")["por_sair"])


# ---------------------------------------------------------------------------
# 4. POR SAIR
# ---------------------------------------------------------------------------


class TestPorSair(Base):

    def test_data_no_futuro_e_por_sair(self):
        lista = self.selado.itens(self.con())
        x = self.por_id(lista, "ct-201")
        self.assertTrue(x["por_sair"])
        self.assertEqual(x["data"], DATAS["FUT"])

    def test_data_no_passado_nao_e(self):
        self.assertFalse(self.por_id(self.selado.itens(self.con()), "ct-101")["por_sair"])

    def test_a_data_de_hoje_nao_e_por_sair(self):
        self.cfg_selado({"datas_por_edicao": {**DATAS, "TST": date.today().isoformat()}})
        self.assertFalse(self.por_id(self.selado.itens(self.con()), "ct-101")["por_sair"],
                         "sai hoje: já saiu")

    def test_edicao_anunciada_sem_data_tambem_e_por_sair(self):
        """*"depois Legacy (LGC) e The Reckoning (REC) em 2027"* — anunciadas,
        sem data exacta."""
        self.cfg_selado({"datas_por_edicao": {"TST": "2025-01-31"}, "por_sair": ["FUT"]})
        x = self.por_id(self.selado.itens(self.con()), "ct-201")
        self.assertTrue(x["por_sair"])
        self.assertIsNone(x["data"])

    def test_sem_data_e_sem_lista_nao_e_por_sair(self):
        self.cfg_selado({"datas_por_edicao": {}, "por_sair": []})
        self.assertFalse(any(x["por_sair"] for x in self.selado.itens(self.con())))

    def test_uma_data_mal_escrita_rebenta(self):
        self.cfg_selado({"datas_por_edicao": {"TST": "31/01/2025"}})
        with self.assertRaises(ValueError) as e:
            self.selado.itens(self.con())
        self.assertIn("AAAA-MM-DD", str(e.exception))

    def test_os_por_sair_contam_no_ha_mas_nao_na_falta(self):
        t = self.selado.contar(self.selado.itens(self.con()))
        self.assertEqual(t["ha"], 9)
        self.assertEqual(t["saiu"], 7)
        self.assertEqual(t["falta"], 7)

    def test_mesmo_tendo_um_por_sair_ele_conta_como_tido(self):
        """Uma pré-encomenda já entregue: ele mete o número e o produto conta
        como tido, mesmo marcado «por sair»."""
        con = self.con()
        self.selado.ajustar(con, "ct-201", 1, source="test")
        t = self.selado.payload(con)["totals"]
        self.assertEqual(t["tenho"], 1)
        self.assertEqual(t["falta"], 7, "e a falta não mexe")
        self.assertEqual(t["pct"], 0.0,
                         "a percentagem é «dos que saíram» e este não saiu")


# ---------------------------------------------------------------------------
# 5. OS `+` E `−`
# ---------------------------------------------------------------------------


class TestOsBotoes(Base):

    def test_sobe_e_desce(self):
        con = self.con()
        self.assertEqual(self.selado.ajustar(con, "ct-101", 3, source="test")["qty"], 3)
        self.assertEqual(self.selado.ajustar(con, "ct-101", -1, source="test")["qty"], 2)
        self.assertEqual(self.selado.tenho(con), {"ct-101": 2})

    def test_nunca_abaixo_de_zero_e_sem_erro(self):
        con = self.con()
        r = self.selado.ajustar(con, "ct-101", -5, source="test")
        self.assertEqual((r["qty"], r["applied"]), (0, 0))
        self.assertEqual(self.selado.tenho(con), {})

    def test_a_zero_a_linha_sai_da_tabela(self):
        con = self.con()
        self.selado.ajustar(con, "ct-101", 1, source="test")
        self.selado.ajustar(con, "ct-101", -1, source="test")
        self.assertEqual(con.execute("SELECT COUNT(*) AS n FROM sealed_copies"
                                     ).fetchone()["n"], 0)

    def test_um_produto_inventado_rebenta(self):
        with self.assertRaises(self.selado.ProdutoDesconhecido):
            self.selado.ajustar(self.con(), "ct-999999", 1, source="test")

    def test_um_produto_que_saiu_do_ambito_deixa_de_aceitar(self):
        """Com a 259 fora das categorias, o `ct-101` já não existe para a app —
        e um `+` nele é recusado em vez de gravar um id órfão."""
        self.cfg_selado({"categorias": [260]})
        with self.assertRaises(self.selado.ProdutoDesconhecido):
            self.selado.ajustar(self.con(), "ct-101", 1, source="test")

    def test_o_valor_do_selado_e_quantidade_vezes_preco(self):
        con = self.con()
        self.selado.ajustar(con, "ct-101", 2, source="test")      # 160,64 € cada
        self.selado.ajustar(con, "ct-104", 1, source="test")      # 32,51 €
        self.assertEqual(self.selado.payload(con)["totals"]["valor_cents"],
                         2 * 16064 + 3251)

    def test_um_produto_sem_preco_vale_zero_e_nao_rebenta(self):
        con = self.con()
        self.selado.ajustar(con, "ct-103", 1, source="test")
        self.assertEqual(self.selado.payload(con)["totals"]["valor_cents"], 0)


# ---------------------------------------------------------------------------
# 6. O SELADO NÃO ENTRA NA COLEÇÃO
# ---------------------------------------------------------------------------


class TestNaoEntraNaColecao(Base):
    """A ordem: *"O SELADO NAO ENTRA NA COLECCAO. Nem niveis, nem denominador,
    nem A mais, nem Faltas, nem as wantlists, nem decks, nem foil, nem
    proprias, nem Venda."*"""

    def fotografia(self, con) -> dict:
        cfg = self.config.load()
        sp = self.metrics.set_payload(con, "TST")
        idx = self.metrics.index_payload(con)
        fe = self.faltas_edicao.payload(con, cfg)
        am = self.a_mais.payload(con, cfg)
        return {
            "niveis": [(l["k"], l["done"], l["total"], l["missing"], l["cents"])
                       for l in self.metrics.niveis_payload(con, cfg)["levels"]],
            "denominador": idx["sets"],
            "wantlist": {k: self.a_subir.wantlist(con, cfg=cfg)[k]
                         for k in ("text", "lines", "copies", "cents")},
            "valor": self.prices.collection_value(con),
            "valor_por_set": self.prices.value_by_set(con),
            "totais": self.collection.totals(con),
            "grelha": [(p["id"], p["qty"], p["qty_total"], p["qty_valor"], p["target"],
                        p["block"], p["foil"], p["foil_ok"])
                       for g in sp["groups"] for p in g["printings"]],
            "playset": {g["card_key"]: g["playset"] for g in sp["groups"]},
            "owned_by_card": self.metrics.owned_by_card(con),
            "barras": (sp["progress"]["playset"], sp["progress"]["master"],
                       sp["progress"]["value"]),
            "painel": sp["progress"]["painel"],
            "painel_geral": idx["painel"],
            "foil_resumo": (sp["progress"]["foil"], idx["foil"]),
            "blocos": sp["blocks"],
            "faltas": (fe["totals"], fe["totals_lists"],
                       [(s["set"], b["id"], b["cards"], b["copies"], b["cents"])
                        for s in fe["sets"] for b in s["blocks"]]),
            "encomendas": self.pending.encomendas(con)["totals"],
            "a_mais": {s["set"]: [(x["printing_id"], x["extra"], x["have"])
                                  for x in s["excedente"]["items"]] for s in am["sets"]},
            "decks": self.decks.resumo_das_faltas(con),
            "uso": self.decks.uso_por_carta(con),
            "venda": self.venda.payload(con, cfg)["totals"],
            "copies": sorted((r["printing_id"], r["qty"], r["qty_foil"]) for r in
                             con.execute("SELECT printing_id, qty, qty_foil FROM copies")),
            "locais": self.locais.resumo(con),
            "ops": con.execute("SELECT COUNT(*) AS n FROM ops").fetchone()["n"],
        }

    def test_a_fotografia_nao_e_de_zeros(self):
        """Um teste de igualdade sobre nada não prova nada."""
        f = self.fotografia(self.catalogo())
        self.assertGreater(f["valor"]["cents"], 0)
        self.assertTrue(f["denominador"], "as edições do índice")
        self.assertTrue(f["copies"])

    def test_meter_e_tirar_produto_selado_nao_mexe_em_numero_nenhum(self):
        con = self.catalogo()
        antes = self.fotografia(con)

        self.selado.ajustar(con, "ct-101", 3, source="test")   # 3 displays, 481,92 €
        self.selado.ajustar(con, "ct-102", 1, source="test")   # 1 case, 1140,64 €
        self.selado.ajustar(con, "ct-201", 2, source="test")   # 2 por sair
        self.assertEqual(self.selado.payload(con)["totals"]["copias"], 6)
        self.assertEqual(self.fotografia(con), antes,
                         "6 unidades de selado e NADA da Coleção mexeu")

        self.selado.ajustar(con, "ct-101", -3, source="test")
        self.selado.ajustar(con, "ct-102", -1, source="test")
        self.selado.ajustar(con, "ct-201", -2, source="test")
        self.assertEqual(self.fotografia(con), antes)

    def test_o_valor_do_selado_nao_vai_para_o_valor_da_colecao(self):
        con = self.catalogo()
        antes = self.prices.collection_value(con)["cents"]
        self.selado.ajustar(con, "ct-102", 1, source="test")    # 1 140,64 €
        p = self.selado.payload(con)
        self.assertEqual(p["totals"]["valor_cents"], 114064)
        self.assertEqual(self.prices.collection_value(con)["cents"], antes,
                         "uma caixa por abrir não é uma carta no binder")
        self.assertNotIn("selado", self.metrics.index_payload(con).get("value", {}))

    def test_nem_o_copies_nem_o_ops_nem_os_locais(self):
        con = self.catalogo()
        qty = sorted((r["printing_id"], r["qty"]) for r in
                     con.execute("SELECT printing_id, qty FROM copies"))
        ops = con.execute("SELECT COUNT(*) AS n FROM ops").fetchone()["n"]
        locs = con.execute("SELECT COUNT(*) AS n FROM copy_locations").fetchone()["n"]
        self.selado.ajustar(con, "ct-101", 4, source="test")
        self.assertEqual(sorted((r["printing_id"], r["qty"]) for r in
                                con.execute("SELECT printing_id, qty FROM copies")), qty)
        self.assertEqual(con.execute("SELECT COUNT(*) AS n FROM ops").fetchone()["n"], ops)
        self.assertEqual(con.execute("SELECT COUNT(*) AS n FROM copy_locations"
                                     ).fetchone()["n"], locs)

    def test_ler_a_lista_nao_escreve(self):
        con = self.catalogo()
        antes = con.execute("SELECT COUNT(*) AS n FROM sealed_copies").fetchone()["n"]
        self.selado.payload(con)
        self.selado.itens(con)
        self.assertEqual(con.execute("SELECT COUNT(*) AS n FROM sealed_copies"
                                     ).fetchone()["n"], antes)

    def test_nenhum_modulo_de_contas_importa_o_selado(self):
        """Só o `server`, o `build` e a `cli` o chamam. Se um módulo de contas
        passar a lê-lo, é sinal de que o selado entrou numa conta da Coleção —
        e não pode."""
        proibidos = ["a_subir", "faltas", "faltas_edicao", "a_mais", "uso_decks",
                     "decks", "locais", "pending", "prices", "painel", "runas_vista",
                     "cardmarket", "seguir", "catalog", "metrics", "collection",
                     "proprias", "foil", "venda", "abas"]
        for nome in proibidos:
            fonte = (REPO / "riftvault" / f"{nome}.py").read_text(encoding="utf-8")
            self.assertNotIn("import selado", fonte, nome)
            self.assertNotIn("from .selado", fonte, nome)
            self.assertNotIn("sealed_copies", fonte, nome)
            self.assertNotIn("selado_catalogo", fonte, nome)


# ---------------------------------------------------------------------------
# 7. A chave do config para acrescentar à mão
# ---------------------------------------------------------------------------


class TestProdutosDoConfig(Base):

    EXTRA = {"nome": "Caixa de lançamento (Portugal)", "edicao": "TST",
             "tipo": "caixa", "data": "2025-11-02", "preco_eur": 42.5,
             "nota": "só na loja"}

    def test_um_produto_a_mao_entra_na_lista(self):
        self.cfg_selado({"extra": [self.EXTRA]})
        lista = self.selado.itens(self.con())
        x = [y for y in lista if y["fonte"] == "config"]
        self.assertEqual(len(x), 1)
        x = x[0]
        self.assertEqual(x["nome"], "Caixa de lançamento (Portugal)")
        self.assertEqual((x["tipo"], x["edicao"], x["data"]), ("caixa", "TST", "2025-11-02"))
        self.assertEqual(x["preco_cents"], 4250)
        self.assertFalse(x["por_sair"])
        self.assertEqual(self.selado.contar(lista)["ha"], 10)
        self.assertEqual(self.selado.contar(lista)["do_config"], 1)

    def test_da_para_contar_quantos_tem_dele(self):
        self.cfg_selado({"extra": [self.EXTRA]})
        con = self.con()
        pid = [y["id"] for y in self.selado.itens(con) if y["fonte"] == "config"][0]
        self.selado.ajustar(con, pid, 2, source="test")
        t = self.selado.payload(con)["totals"]
        self.assertEqual((t["tenho"], t["copias"], t["valor_cents"]), (1, 2, 8500))

    def test_tirar_do_config_tira_da_lista(self):
        self.cfg_selado({"extra": [self.EXTRA]})
        self.assertEqual(self.selado.contar(self.selado.itens(self.con()))["ha"], 10)
        self.cfg_selado({"extra": []})
        self.assertEqual(self.selado.contar(self.selado.itens(self.con()))["ha"], 9)

    def test_um_tipo_que_nao_existe_rebenta(self):
        self.cfg_selado({"extra": [{"nome": "X", "tipo": "caixote"}]})
        with self.assertRaises(ValueError) as e:
            self.selado.itens(self.con())
        self.assertIn("caixote", str(e.exception))

    def test_sem_nome_rebenta(self):
        self.cfg_selado({"extra": [{"edicao": "TST"}]})
        with self.assertRaises(ValueError):
            self.selado.itens(self.con())

    def test_sem_tipo_e_outro_e_sem_preco_nao_rebenta(self):
        self.cfg_selado({"extra": [{"nome": "Coisa", "edicao": "TST"}]})
        x = [y for y in self.selado.itens(self.con()) if y["fonte"] == "config"][0]
        self.assertEqual(x["tipo"], "outro")
        self.assertIsNone(x["preco_cents"])


# ---------------------------------------------------------------------------
# 8. O preço do selado, e o `--sync` (sem rede)
# ---------------------------------------------------------------------------


class TestOPrecoDoSelado(Base):
    """A regra é DIFERENTE da das cartas, e está medida contra a API real
    (2026-09-25): uma oferta de selado não tem `condition` nenhuma e traz
    `properties_hash.sealed`."""

    def oferta(self, **kw):
        base = {"price_cents": 1000, "price_currency": "EUR", "quantity": 1,
                "graded": False, "on_vacation": False,
                "properties_hash": {"sealed": True, "riftbound_language": "en"},
                "user": {"id": 1}}
        base["properties_hash"] = {**base["properties_hash"],
                                   **kw.pop("properties_hash", {})}
        base.update(kw)
        return base

    def test_o_mais_barato_em_ingles(self):
        o = self.selado.preco_do_selado([
            self.oferta(price_cents=6995,
                        properties_hash={"riftbound_language": "zh-CN"}),
            self.oferta(price_cents=11564),
            self.oferta(price_cents=16064, user={"id": 2}),
        ], frozenset({"en"}))
        self.assertEqual(o["cents"], 11564, "a chinesa não conta")
        self.assertEqual((o["n_listings"], o["n_sellers"]), (2, 2))

    def test_um_produto_ja_aberto_nao_conta(self):
        """`sealed: false` é um produto por abrir que já não está por abrir — e
        aí o preço é outra coisa."""
        o = self.selado.preco_do_selado([
            self.oferta(price_cents=500, properties_hash={"sealed": False}),
            self.oferta(price_cents=4214),
        ], frozenset({"en"}))
        self.assertEqual(o["cents"], 4214)

    def test_sem_a_propriedade_sealed_conta_na_mesma(self):
        o = self.selado.preco_do_selado(
            [self.oferta(properties_hash={"sealed": None})], frozenset({"en"}))
        self.assertEqual(o["cents"], 1000)

    def test_graded_ferias_e_outra_moeda_ficam_de_fora(self):
        for kw in ({"graded": True}, {"on_vacation": True},
                   {"price_currency": "USD"}, {"price_cents": 0}):
            o = self.selado.preco_do_selado([self.oferta(**kw)], frozenset({"en"}))
            self.assertIsNone(o["cents"], kw)

    def test_sem_oferta_nenhuma_o_preco_e_none(self):
        o = self.selado.preco_do_selado([], frozenset({"en"}))
        self.assertEqual(o, {"cents": None, "n_listings": 0, "n_sellers": 0,
                             "n_copies": 0})

    def test_o_sync_escreve_o_ficheiro_e_nao_toca_na_colecao(self):
        """Com um CardTrader de brincar — nunca se fala com a rede nos testes."""
        con = self.catalogo()
        antes = sorted((r["printing_id"], r["qty"]) for r in
                       con.execute("SELECT printing_id, qty FROM copies"))

        class CTFalso:
            def get(self, path, params=None):
                if path == "/categories":
                    return [{"id": 259, "name": "Riftbound Booster Boxes", "game_id": 22},
                            {"id": 258, "name": "Riftbound Singles", "game_id": 22},
                            {"id": 7, "name": "Magic Singles", "game_id": 1}]
                return {"77": [{"price_cents": 9900, "price_currency": "EUR",
                                "quantity": 1, "graded": False, "on_vacation": False,
                                "properties_hash": {"sealed": True,
                                                    "riftbound_language": "en"},
                                "user": {"id": 5}}]}

            def expansions(self):
                return [{"id": 1, "code": "zzz", "name": "Zeta"}]

            def blueprints(self, expansion_id):
                return [{"id": 77, "name": "Zeta Booster Box", "version": "",
                         "category_id": 259, "image_url": "u", "card_market_ids": [1]},
                        {"id": 78, "name": "Zeta Card", "category_id": 258}]

        r = self.selado.sincronizar(ct=CTFalso(), log=lambda *a: None, intervalo=0)
        self.assertEqual(r["produtos"], 1, "o single não entra no ficheiro")
        self.assertEqual(r["precos"], 1)
        self.selado._cache = None
        dados = self.selado.carregar()
        self.assertEqual(dados["produtos"][0]["nome"], "Zeta Booster Box")
        self.assertEqual(dados["produtos"][0]["edicao"], "ZZZ")
        self.assertEqual(dados["precos"]["77"]["cents"], 9900)
        self.assertEqual(dados["categorias"], {"259": "Riftbound Booster Boxes",
                                               "258": "Riftbound Singles"})
        self.assertEqual(sorted((r2["printing_id"], r2["qty"]) for r2 in
                                con.execute("SELECT printing_id, qty FROM copies")),
                         antes, "o sync não toca na coleção")


# ---------------------------------------------------------------------------
# 9. A rota, o site publicado, a CLI e a página
# ---------------------------------------------------------------------------


class TestRotasEPagina(Base):

    def cliente(self):
        from riftvault import server
        importlib.reload(server)
        server.app.config["TESTING"] = True
        return server.app.test_client()

    def test_a_rota_responde_e_os_botoes_ajustam(self):
        self.catalogo()
        c = self.cliente()
        r = c.get("/api/selado.json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["totals"]["ha"], 9)
        self.assertTrue(r.get_json()["editable"])

        r = c.post("/api/selado/ajustar", json={"product_id": "ct-101", "delta": 2})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["totals"]["copias"], 2)

    def test_a_rota_recusa_o_que_nao_existe(self):
        self.catalogo()
        c = self.cliente()
        self.assertEqual(c.post("/api/selado/ajustar",
                                json={"product_id": "ct-9", "delta": 1}).status_code, 404)
        self.assertEqual(c.post("/api/selado/ajustar",
                                json={"delta": 1}).status_code, 400)
        self.assertEqual(c.post("/api/selado/ajustar",
                                json={"product_id": "ct-101", "delta": 0}).status_code, 400)

    def test_o_site_publicado_e_so_de_leitura(self):
        from riftvault import build
        importlib.reload(build)
        con = self.catalogo()
        self.selado.ajustar(con, "ct-101", 1, source="test")
        out = self.v.root / "site"
        with contextlib.redirect_stdout(io.StringIO()):
            build.build(out)
        p = json.loads((out / "api" / "selado.json").read_text(encoding="utf-8"))
        self.assertFalse(p["editable"])
        self.assertEqual(p["totals"]["tenho"], 1)

    def test_a_cli_lista_e_ajusta(self):
        from riftvault import cli
        importlib.reload(cli)
        self.catalogo()
        saida = io.StringIO()
        with contextlib.redirect_stdout(saida), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(["selado", "--mais", "ct-101", "2"]), 0)
        texto = saida.getvalue()
        self.assertIn("ct-101: +2 -> 2", texto)
        self.assertIn("TENHO 1", texto)
        self.assertIn("Display", texto)

    def test_a_cli_recusa_um_produto_inventado(self):
        from riftvault import cli
        importlib.reload(cli)
        self.catalogo()
        with contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(["selado", "--mais", "ct-0"]), 1)

    def test_a_seccao_existe_na_pagina(self):
        html = INDEX.read_text(encoding="utf-8")
        self.assertIn('id="sec-selado"', html)
        for ident in ("sl-head", "sl-filtros", "sl-body"):
            self.assertIn(f'id="{ident}"', html)
        js = APP_JS.read_text(encoding="utf-8")
        self.assertIn("'selado'", js)
        self.assertIn("api/selado.json", js)
        self.assertIn("api/selado/ajustar", js)
        self.assertIn("function renderSelado", js)

    def test_o_valor_do_selado_esta_escrito_como_a_parte(self):
        js = APP_JS.read_text(encoding="utf-8")
        self.assertIn("à parte do valor da Coleção", js)

    def test_e_usavel_a_375px(self):
        """Cada linha parte-se a 375 px — as três colunas não cabem num
        telemóvel, que é onde isto vai ser usado."""
        css = CSS.read_text(encoding="utf-8")
        self.assertIn(".sl-linha", css)
        movel = css.split("@media (max-width: 559px)")
        self.assertTrue(any(".sl-linha" in bloco for bloco in movel[1:]),
                        "falta a regra da linha a 375 px")
        self.assertIn(".sl-nums { grid-template-columns: repeat(2", css)

    def test_a_aba_esconde_se_por_config(self):
        from riftvault import abas
        importlib.reload(abas)
        self.assertIn("selado", abas.IDS)
        self.assertEqual(abas.resolver("Produto Selado"), "selado")
        self.cfg_selado({}, {"abas": {"escondidas": ["selado"]}})
        importlib.reload(abas)
        self.assertIn("selado", abas.escondidas())
        con = self.catalogo()
        ix = self.metrics.index_payload(con)
        self.assertIn("selado", ix["abas"]["escondidas"])
        self.assertNotIn("selado", ix["abas"]["visiveis"])

    def test_esconder_a_aba_nao_apaga_o_calculo(self):
        """Esconder não é apagar — a rota continua a responder, como no «A
        mais» (2026-09-25)."""
        self.cfg_selado({}, {"abas": {"escondidas": ["selado"]}})
        self.catalogo()
        r = self.cliente().get("/api/selado.json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["totals"]["ha"], 9)


if __name__ == "__main__":
    unittest.main()

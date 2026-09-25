"""As abas ESCONDIDAS por config (André, 2026-09-25).

Palavras dele: *"Tira a aba 'A mais', 'Por Deck' e 'Pimp Deck'"*.

O que se fixa:
  1. o CONFIG: `abas.escondidas`, os nomes que casam (o id e as palavras dele),
     um nome desconhecido a rebentar, e **repor = tirar o nome da lista**;
  2. as abas saem da BARRA e das VISTAS, nos dois modos — a lista vai no
     `api/index.json`, que o site publicado também traz;
  3. o CÁLCULO E AS ROTAS FICAM: o «A mais» continua a ser calculado, o
     `api/a_mais.json` e o `api/compras.json` continuam a ser gerados e
     servidos, e o `riftvault a-mais` continua a responder;
  4. **NENHUM NÚMERO MUDA**: uma fotografia de tudo o que é número do site —
     níveis, denominador, wantlists, valor, Faltas, Encomendas, A mais, decks
     e Venda — com as abas à vista, escondidas e repostas;
  5. o `app.js`: a barra, o índice dos decks, os atalhos do Início, as rotas e
     os textos que nomeiam as abas.

Tudo contra pastas temporárias (`tests.fixture.Vault`) e um config temporário
(`RIFTVAULT_CONFIG`): o `data/` e o `riftvault_config.json` a sério nunca são
tocados.
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

os.environ["RIFTVAULT_CONFIG"] = str(Path(tempfile.gettempdir()) / "riftvault-nao-existe.json")

from tests.fixture import REPO, Vault  # noqa: E402

APP_JS = (REPO / "riftvault" / "web" / "app.js").read_text(encoding="utf-8")
CONFIG_REAL = json.loads((REPO / "riftvault_config.json").read_text(encoding="utf-8"))


class Base(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.close)
        from riftvault import (a_mais, a_subir, abas, collection, config, db, decks,
                               faltas, faltas_edicao, foil, locais, metrics, painel,
                               pending, prices, proprias, venda)
        for m in (locais, metrics, foil, painel, decks, proprias, a_subir,
                  faltas_edicao, a_mais, pending, faltas, prices, venda, abas):
            importlib.reload(m)
        self.abas, self.config, self.db = abas, config, db
        self.metrics, self.decks, self.a_subir = metrics, decks, a_subir
        self.faltas_edicao, self.a_mais, self.faltas = faltas_edicao, a_mais, faltas
        self.pending, self.prices, self.collection = pending, prices, collection
        self.venda, self.painel, self.foil = venda, painel, foil
        self.escrever_config([])

    def escrever_config(self, escondidas, extra: dict | None = None):
        """Um config temporário só com o bloco `abas` (mais o que o teste
        quiser). Devolve o `cfg` já relido."""
        caminho = self.v.root / "config.json"
        caminho.write_text(json.dumps({"abas": {"escondidas": list(escondidas)},
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
        return self.config.load()

    def catalogo(self):
        """Uma edição com o que basta para todas as contas do site mexerem:
        uma comum a playset, uma incomum, uma rara, um Legend, uma alt art e
        uma sobrenumerada."""
        con = self.v.connect()
        v = self.v
        v.add_printing(con, "tst-001-100", "TST", 1, "Defy", rarity="common", size=100)
        v.add_printing(con, "tst-001a-100", "TST", 1, "Defy", variant="a", kind="alt_art",
                       rarity="showcase", base_rarity="common", size=100)
        v.add_printing(con, "tst-002-100", "TST", 2, "Scout", rarity="uncommon", size=100)
        v.add_printing(con, "tst-003-100", "TST", 3, "Brutalizer", rarity="rare", size=100)
        v.add_printing(con, "tst-004-100", "TST", 4, "Emperor of the Sands",
                       card_type="Legend", rarity="epic", size=100)
        v.add_printing(con, "tst-005-100", "TST", 5, "Fire Below the Mountain",
                       card_type="Legend", rarity="epic", size=100)
        v.add_printing(con, "tst-101-100", "TST", 101, "Lonely Poro", rarity="rare",
                       size=100)
        v.rebuild(con)
        for pid, cents in (("tst-001-100", 110), ("tst-001a-100", 500),
                           ("tst-002-100", 250), ("tst-003-100", 900),
                           ("tst-004-100", 4000), ("tst-005-100", 3000),
                           ("tst-101-100", 20000)):
            con.execute("INSERT INTO catalog.price_latest (printing_id, price_cents) "
                        "VALUES (?,?)", (pid, cents))
        # 6 Scout com alvo 3 e os decks a levarem 2: sobram 3, para o «A mais»
        # ter conteúdo — um bloco vazio não provava que não mexeu.
        for pid, n in (("tst-001-100", 4), ("tst-002-100", 6), ("tst-003-100", 1),
                       ("tst-004-100", 1), ("tst-001a-100", 1)):
            self.collection.adjust(con, pid, n, source="test")
        return con

    def com_decks(self):
        """O catálogo, dois decks e uma encomenda a caminho — para as
        Encomendas, o A mais e as listas de compra terem conteúdo."""
        self.v.write_deck("azir", "Nome: Azir\n\nLegend:\n1 Emperor of the Sands\n\n"
                                  "MainDeck:\n3 Defy\n2 Scout\n1 Brutalizer\n")
        # Legends DIFERENTES de propósito: dois decks com a mesma Legend são um
        # grupo e partilham as cartas (2026-09-11), e aí a falta dava zero — um
        # caso de teste sem falta nenhuma não provava nada.
        self.v.write_deck("ornn", "Nome: Ornn\n\nLegend:\n1 Fire Below the Mountain\n\n"
                                  "MainDeck:\n3 Defy\n1 Brutalizer\n")
        con = self.catalogo()
        self.decks.import_all(con, log=lambda *_: None)
        self.pending.encomendar(con, printing_id="tst-003-100", qty=1, source="test")
        return con


# ======================================================== 1. o config

class TestOConfig(Base):

    def test_sem_a_chave_nao_ha_aba_nenhuma_escondida(self):
        """É o que valia até 2026-09-25, e o que um riftvault sem config
        mostra."""
        caminho = self.v.root / "sem-abas.json"
        caminho.write_text(json.dumps({"sets": {}}), encoding="utf-8")
        os.environ["RIFTVAULT_CONFIG"] = str(caminho)
        importlib.reload(self.config)
        self.config.load.cache_clear()
        cfg = self.config.load()
        self.assertEqual(self.abas.escondidas(cfg), frozenset())
        self.assertEqual(self.abas.visiveis(cfg), self.abas.IDS)

    def test_a_lista_do_config_manda(self):
        cfg = self.escrever_config(["a-mais", "pordeck", "pimp"])
        self.assertEqual(self.abas.escondidas(cfg), frozenset({"a-mais", "pordeck", "pimp"}))
        self.assertEqual(self.abas.visiveis(cfg),
                         ["inicio", "colecao", "faltas-edicao", "decks", "staples",
                          "encomendas", "venda"])

    def test_os_nomes_dele_casam_com_os_ids(self):
        """Ele escreveu «A mais», «Por Deck» e «Pimp Deck» — e é como as lê no
        ecrã. É a mesma ideia do `metrics.PALAVRA_KIND`."""
        for escrito, ident in (("A mais", "a-mais"), ("a-mais", "a-mais"),
                               ("Por Deck", "pordeck"), ("por deck", "pordeck"),
                               ("pordeck", "pordeck"), ("Pimp Deck", "pimp"),
                               ("Pimp decks", "pimp"), ("pimp", "pimp"),
                               ("Início", "inicio"), ("inicio", "inicio"),
                               ("Faltas", "faltas-edicao"), ("Coleção", "colecao")):
            self.assertEqual(self.abas.resolver(escrito), ident, escrito)

    def test_uma_aba_desconhecida_rebenta_com_a_lista_do_que_existe(self):
        """Ignorá-la em silêncio deixava-o a olhar para um separador que
        mandou esconder."""
        cfg = self.escrever_config(["Pool dos decks"])
        with self.assertRaises(ValueError) as e:
            self.abas.escondidas(cfg)
        self.assertIn("Pool dos decks", str(e.exception))
        self.assertIn("a-mais", str(e.exception))
        self.assertIn("pordeck", str(e.exception))

    def test_uma_lista_mal_escrita_rebenta(self):
        cfg = self.escrever_config([])
        cfg = {**cfg, "abas": {"escondidas": "a-mais"}}
        with self.assertRaises(ValueError):
            self.abas.escondidas(cfg)
        with self.assertRaises(ValueError):
            self.abas.escondidas({**cfg, "abas": ["a-mais"]})

    def test_a_lista_vazia_e_a_omissao_dizem_o_mesmo(self):
        self.assertEqual(self.abas.escondidas(self.escrever_config([])), frozenset())

    def test_repor_uma_aba_e_tirar_o_nome_da_lista_e_mais_nada(self):
        """A promessa da ordem, à letra."""
        cfg = self.escrever_config(["a-mais", "pordeck", "pimp"])
        self.assertNotIn("a-mais", self.abas.visiveis(cfg))
        # Tira-se o «A mais» da lista. Nada mais muda no config.
        cfg = self.escrever_config(["pordeck", "pimp"])
        self.assertIn("a-mais", self.abas.visiveis(cfg))
        self.assertTrue(self.abas.visivel("a-mais", cfg))
        # E a lista vazia repõe as três.
        cfg = self.escrever_config([])
        self.assertEqual(self.abas.visiveis(cfg), self.abas.IDS)

    def test_o_config_real_esconde_as_tres_que_ele_pediu(self):
        """O `riftvault_config.json` a sério — é o que ele vai ver."""
        self.assertEqual(CONFIG_REAL["abas"]["escondidas"], ["a-mais", "pordeck", "pimp"])

    def test_o_default_nao_esconde_nada(self):
        self.assertEqual(self.config.DEFAULTS["abas"], {"escondidas": []})

    def test_o_catalogo_das_abas_cobre_as_seccoes_e_as_vistas_do_app_js(self):
        """Uma aba que exista no site e não esteja aqui não se podia esconder;
        uma que esteja aqui e não exista no site era um nome que não faz
        nada."""
        seccoes = re.findall(r"'([a-z-]+)'",
                             re.search(r"const SECCOES = \[(.*?)\];", APP_JS).group(1))
        vistas = re.findall(r"id: '(\w+)'",
                            re.search(r"const DECK_FALTA_TABS = \[(.*?)\n\];",
                                      APP_JS, re.S).group(1))
        do_modulo = {a["id"] for a in self.abas.ABAS}
        self.assertEqual(do_modulo, set(seccoes) | set(vistas))
        self.assertEqual([a["id"] for a in self.abas.ABAS if a["tipo"] == self.abas.VISTA],
                         vistas)


# ======================================================== 2. o payload

class TestOPayload(Base):

    def test_o_index_leva_as_escondidas_e_as_visiveis(self):
        cfg = self.escrever_config(["a-mais", "pordeck", "pimp"])
        con = self.catalogo()
        idx = self.metrics.index_payload(con, cfg=cfg)
        self.assertEqual(idx["abas"]["escondidas"], ["a-mais", "pordeck", "pimp"])
        self.assertNotIn("a-mais", idx["abas"]["visiveis"])
        self.assertIn("decks", idx["abas"]["visiveis"])
        # O catálogo leva o rótulo, para a página não repetir os nomes.
        self.assertIn({"id": "a-mais", "tipo": "seccao", "label": "A mais"},
                      idx["abas"]["catalogo"])

    def test_o_servidor_leva_a_lista_e_continua_a_servir_o_a_mais(self):
        cfg = self.escrever_config(["a-mais", "pordeck", "pimp"])
        con = self.com_decks()
        con.close()
        from riftvault import server
        importlib.reload(server)
        server.app.testing = True
        with server.app.test_client() as c:
            idx = c.get("/api/index.json").get_json()
            self.assertEqual(idx["abas"]["escondidas"], ["a-mais", "pordeck", "pimp"])
            # AS ROTAS FICAM: esconder a aba não apaga o cálculo.
            am = c.get("/api/a_mais.json")
            self.assertEqual(am.status_code, 200)
            self.assertIn("sets", am.get_json())
            co = c.get("/api/compras.json")
            self.assertEqual(co.status_code, 200)
            self.assertIn("por_deck", co.get_json())
            self.assertIn("pimp", co.get_json())
        del cfg

    def test_o_site_publicado_leva_a_mesma_lista_e_os_mesmos_ficheiros(self):
        """A mesma linha de config tira a aba do 8770 e do site publicado — e
        o `api/a_mais.json` continua a ser escrito."""
        self.escrever_config(["a-mais", "pordeck", "pimp"])
        con = self.com_decks()
        con.close()
        from riftvault import build
        importlib.reload(build)
        saida = self.v.root / "site"
        build.build(saida, log=lambda *_: None)
        idx = json.loads((saida / "api" / "index.json").read_text(encoding="utf-8"))
        self.assertFalse(idx["editable"])
        self.assertEqual(idx["abas"]["escondidas"], ["a-mais", "pordeck", "pimp"])
        for nome in ("a_mais.json", "compras.json", "wantlist.json", "faltas_edicao.json"):
            self.assertTrue((saida / "api" / nome).exists(), nome)
        am = json.loads((saida / "api" / "a_mais.json").read_text(encoding="utf-8"))
        self.assertIn("sets", am)

    def test_o_a_mais_continua_a_ser_calculado_com_a_aba_escondida(self):
        """Item a item: esconder o separador não mexe no que ele diria."""
        cfg = self.escrever_config([])
        con = self.com_decks()
        antes = self.a_mais.payload(con, cfg)
        cfg = self.escrever_config(["a-mais", "pordeck", "pimp"])
        depois = self.a_mais.payload(con, cfg)
        self.assertEqual(depois["totals"], antes["totals"])
        self.assertEqual([(s["set"], [(x["printing_id"], x["extra"]) for x in
                                      s["excedente"]["items"]]) for s in depois["sets"]],
                         [(s["set"], [(x["printing_id"], x["extra"]) for x in
                                      s["excedente"]["items"]]) for s in antes["sets"]])
        self.assertTrue(antes["totals"]["excedente"]["copies"] > 0,
                        "o caso de teste tem de ter excedente, senão não prova nada")

    def test_as_listas_de_compra_dos_decks_continuam_a_ser_calculadas(self):
        cfg = self.escrever_config([])
        con = self.com_decks()
        antes = self.faltas.compras(con)
        self.escrever_config(["a-mais", "pordeck", "pimp"])
        self.assertEqual(self.faltas.compras(con), antes)
        del cfg

    def test_ler_as_abas_nao_escreve_na_base(self):
        cfg = self.escrever_config(["a-mais"])
        con = self.catalogo()
        ops = con.execute("SELECT COUNT(*) AS n FROM ops").fetchone()["n"]
        qty = sorted((r["printing_id"], r["qty"]) for r in
                     con.execute("SELECT printing_id, qty FROM copies"))
        self.abas.payload(cfg)
        self.metrics.index_payload(con, cfg=cfg)
        self.assertEqual(con.execute("SELECT COUNT(*) AS n FROM ops").fetchone()["n"], ops)
        self.assertEqual(sorted((r["printing_id"], r["qty"]) for r in
                                con.execute("SELECT printing_id, qty FROM copies")), qty)


# ======================================================== 3. não mexe em nada

class TestNaoMexeEmNumeroNenhum(Base):
    """*"Nenhum numero de nenhuma outra aba pode mudar por causa disto."*

    A mesma defesa do `test_foil` (2026-09-22) e do `test_copias_proprias`
    (2026-09-21): fotografa-se tudo o que é número do site, esconde-se as
    abas, repõem-se, e exige-se igualdade.
    """

    def fotografia(self, con, cfg) -> dict:
        sp = self.metrics.set_payload(con, "TST")
        idx = self.metrics.index_payload(con, cfg=cfg)
        fe = self.faltas_edicao.payload(con, cfg)
        am = self.a_mais.payload(con, cfg)
        vd = self.venda.payload(con, cfg)
        return {
            "niveis": [(l["k"], l["done"], l["total"], l["missing"], l["cents"])
                       for l in self.metrics.niveis_payload(con, cfg)["levels"]],
            "denominador": sp["progress"]["master"],
            "wantlist": {k: self.a_subir.wantlist(con, cfg=cfg)[k]
                         for k in ("text", "lines", "copies", "cents")},
            "wantlist_edicao": {k: self.a_subir.wantlist(con, "TST", cfg=cfg)[k]
                                for k in ("text", "lines", "copies", "cents")},
            "valor": self.prices.collection_value(con),
            "valor_por_set": self.prices.value_by_set(con),
            "totais": self.collection.totals(con),
            "grelha": [(p["id"], p["qty"], p["qty_total"], p["qty_valor"], p["target"],
                        p["block"]) for g in sp["groups"] for p in g["printings"]],
            "barras": (sp["progress"]["playset"], sp["progress"]["value"],
                       sp["progress"]["rarities"]),
            "painel": sp["progress"]["painel"],
            "painel_geral": idx["painel"],
            "foil": idx["foil"],
            "blocos": sp["blocks"],
            "sets": idx["sets"],
            "faltas": (fe["totals"], fe["totals_lists"],
                       [(s["set"], b["id"], b["cards"], b["copies"], b["cents"],
                         b["wantlist"]) for s in fe["sets"] for b in s["blocks"]]),
            "encomendas": self.pending.encomendas(con)["totals"],
            "a_mais": {s["set"]: [(x["printing_id"], x["extra"], x["have"])
                                  for x in s["excedente"]["items"]] for s in am["sets"]},
            "a_mais_totais": am["totals"],
            "decks": self.decks.resumo_das_faltas(con),
            "decks_index": [(d["slug"], d["have"], d["wanted"], d["missing"])
                            for d in self.decks.decks_index(con)],
            "compras": self.faltas.compras(con),
            # Sem o `generated_at`, que muda a cada leitura.
            "venda": (vd["totals"], [(x["printing_id"], x["qty"]) for x in vd["items"]]),
            "copies": sorted((r["printing_id"], r["qty"]) for r in
                             con.execute("SELECT printing_id, qty FROM copies")),
        }

    def test_esconder_e_repor_as_abas_nao_mexe_em_numero_nenhum(self):
        cfg = self.escrever_config([])
        con = self.com_decks()
        # Uma venda em curso, para a Venda também entrar na fotografia.
        self.venda.juntar(con, "tst-003-100", 1)
        self.venda.guardar_trend(con, "tst-003-100", 950, source="test")
        antes = self.fotografia(con, cfg)

        cfg = self.escrever_config(["a-mais", "pordeck", "pimp"])
        self.assertEqual(self.fotografia(con, cfg), antes,
                         "três abas escondidas e NADA mexeu")

        # Todas escondidas, que é o caso extremo.
        cfg = self.escrever_config(list(self.abas.IDS))
        self.assertEqual(self.fotografia(con, cfg), antes,
                         "com o site inteiro sem botões os números são os mesmos")

        # E repostas: tirar os nomes da lista devolve exactamente o que havia.
        cfg = self.escrever_config([])
        self.assertEqual(self.fotografia(con, cfg), antes, "repor também não mexe")

    def test_os_numeros_do_caso_de_teste_nao_sao_todos_zero(self):
        """Uma fotografia de zeros era igual a si mesma e não provava nada."""
        cfg = self.escrever_config([])
        con = self.com_decks()
        self.venda.juntar(con, "tst-003-100", 1)
        self.venda.guardar_trend(con, "tst-003-100", 950, source="test")
        f = self.fotografia(con, cfg)
        self.assertGreater(f["valor"]["cents"], 0)
        self.assertGreater(f["wantlist"]["copies"], 0)
        self.assertGreater(f["faltas"][0]["copies"], 0)
        self.assertGreater(f["encomendas"]["copies"], 0)
        self.assertGreater(f["decks"]["copies"], 0)
        self.assertGreater(f["a_mais_totais"]["excedente"]["copies"], 0)
        self.assertGreater(f["venda"][0]["cents"], 0)
        self.assertGreater(f["niveis"][0][1], 0)

    def test_nenhum_modulo_de_contas_importa_o_abas(self):
        """Só o `metrics.index_payload` (para o pôr no payload), o servidor, o
        build e a CLI. Se um módulo de contas o passar a ler, é sinal de que
        esconder uma aba entrou numa conta — e não pode."""
        proibidos = ["a_subir", "faltas", "faltas_edicao", "a_mais", "uso_decks",
                     "decks", "locais", "pending", "prices", "painel", "runas_vista",
                     "cardmarket", "seguir", "catalog", "collection", "venda", "foil",
                     "proprias"]
        for nome in proibidos:
            fonte = (REPO / "riftvault" / f"{nome}.py").read_text(encoding="utf-8")
            self.assertNotIn("import abas", fonte, nome)
            self.assertNotIn("from . import abas", fonte, nome)

    def test_o_a_mais_e_o_faltas_continuam_a_existir_inteiros(self):
        """Esconder não é apagar: os módulos, o CLI e as funções ficam."""
        for nome in ("a_mais", "faltas"):
            self.assertTrue((REPO / "riftvault" / f"{nome}.py").exists(), nome)
        cli = (REPO / "riftvault" / "cli.py").read_text(encoding="utf-8")
        self.assertIn('"a-mais"', cli)
        for fn in ("excedente", "libertadas", "payload"):
            self.assertTrue(hasattr(self.a_mais, fn), fn)
        for fn in ("staples", "por_deck", "pimp", "compras"):
            self.assertTrue(hasattr(self.faltas, fn), fn)


# ======================================================== 4. o app.js

class TestOAppJs(unittest.TestCase):
    """A barra, o índice dos decks, os atalhos e as rotas — lidos do ficheiro."""

    def corpo(self, nome: str, palavra: str = "function") -> str:
        m = re.search(r"%s %s\([^)]*\) \{(.*?)\n\}\n" % (palavra, nome), APP_JS, re.S)
        self.assertIsNotNone(m, f"não há {nome}()")
        return m.group(1)

    def test_a_lista_vem_do_servidor_e_nao_ha_segunda_no_javascript(self):
        """Se o `app.js` tivesse a lista dele, esconder uma aba passava a ser
        duas edições — e o site publicado ficava com a de ontem."""
        self.assertIn("state.escondidas = new Set((state.index.abas || {}).escondidas || [])",
                      APP_JS)
        self.assertNotIn("'a-mais', 'pordeck'", APP_JS)

    def test_a_barra_lateral_salta_as_escondidas(self):
        corpo = self.corpo("renderNav")
        self.assertIn("abaVisivel(abaDoItem(it))", corpo)
        # Um grupo que fique vazio não deixa o cabeçalho dele sozinho.
        self.assertIn("if (!itens.length) continue;", corpo)

    def test_a_barra_so_se_desenha_depois_de_saber_quais_sao(self):
        """Desenhá-la antes do índice mostrava por um instante uma aba que ele
        mandou tirar."""
        boot = self.corpo("boot", "async function")
        i_idx = boot.index("state.escondidas =")
        i_nav = boot.index("renderNav()")
        self.assertLess(i_idx, i_nav, "o renderNav() tem de vir depois da lista")
        # E se o índice falhar, a barra desenha-se na mesma.
        self.assertIn("try { renderNav(); } catch (_) {}", APP_JS)

    def test_uma_seccao_escondida_e_uma_rota_que_nao_existe(self):
        self.assertIn("function seccaoValida(name) {", APP_JS)
        self.assertIn("SECCOES.includes(name) && abaVisivel(name)", APP_JS)
        self.assertIn("if (!seccaoValida(name)) name = seccaoInicial();", APP_JS)
        self.assertIn("if (seccaoValida(h.sec)) showSection(h.sec, h.sub, { url: false });",
                      APP_JS)
        # E a secção continua escondida no DOM: o ciclo é sobre as SECCOES todas.
        self.assertIn("for (const s of SECCOES) $('#sec-' + s).hidden = s !== name;", APP_JS)

    def test_as_vistas_dos_decks_saem_do_indice_e_do_select(self):
        """As duas listas do separador Decks saem da MESMA função, que já
        filtra — o `<select>` do telemóvel não podia ter uma aba a mais."""
        self.assertIn("return DECK_FALTA_TABS.filter(t => abaVisivel(t.id));", APP_JS)
        self.assertIn("const listas = deckFaltaTabs().map(t => ({", APP_JS)
        # Não sobrou nenhuma leitura da lista completa nas rotas.
        self.assertNotIn("DECK_FALTA_IDS", APP_JS)

    def test_uma_vista_escondida_nao_abre_nem_pela_rota_nem_pela_preferencia(self):
        self.assertIn("if (deckFaltaIds().includes(sub)) {", APP_JS)
        corpo = self.corpo("loadDecks", "async function")
        self.assertIn("const ids = deckFaltaIds();", corpo)
        self.assertIn("if (ids.includes(first)) await loadDeckFaltas(first);", corpo)

    def test_o_atalho_do_inicio_de_uma_aba_escondida_nao_aparece(self):
        self.assertIn("atalhos.filter(([sec]) => abaVisivel(sec))", APP_JS)

    def test_os_textos_nao_mandam_a_uma_aba_que_saiu(self):
        """A ajuda dos Decks descrevia as três listas de compra e o cabeçalho
        das Staples mandava ir ao «Por deck»."""
        self.assertIn("function ajudaListasDeCompra() {", APP_JS)
        self.assertIn("deckFaltaIds().map(id => frases[id])", APP_JS)
        self.assertIn("abaVisivel('pordeck')", APP_JS)
        # A ajuda dos Decks é a única que é função, e o cabeçalho sabe disso.
        self.assertIn("typeof p.ajuda === 'function' ? p.ajuda() : p.ajuda", APP_JS)

    def test_as_funcoes_de_desenho_das_escondidas_ficam(self):
        """Esconder não é apagar — o «Por deck» e o «Pimp» continuam inteiros,
        e voltam a desenhar-se assim que o nome sair da lista."""
        for fn in ("renderPorDeck", "renderPimp", "renderAMais", "loadAMais"):
            self.assertIn(f"function {fn}(", APP_JS, fn)
        self.assertIn("'a-mais'", APP_JS)


if __name__ == "__main__":
    unittest.main()

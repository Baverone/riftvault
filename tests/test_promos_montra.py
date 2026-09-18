"""A montra «Promos» da Coleção (2026-09-18).

André: *"e essas que digo, de Nexus Night, eventos, bundles, etc / consegues
averiguar e fazer um botao com essas, com foto da carta tambem, assim consigo
perceber se vou querer coleccionar tambem ou nao"*.

O que se fixa aqui: a lista lê-se do disco e rebenta quando não presta; o
casamento dos nomes é exacto, pelo nome do mercado, sem o separador do
subtítulo, ou pela cauda de um Legend — e NUNCA adivinha (ambíguo ou
desconhecido fica por encontrar, com o número à vista); a foto é da versão
normal da edição mais antiga (nem alt art nem sobrenumerada) e o item diz-o;
«tens N» conta as cópias da carta em qualquer versão, com a ressalva; a `VEN-SP`
da mesma carta aparece como a mesma carta vista de outro sítio; as categorias
vêm por tamanho; o mesmo nome em duas categorias diz «também»; a montra não
tem alvo, falta nem euros, não escreve, e NADA mexe — percentagem, níveis,
wantlist, «A mais», valor, falta dos decks — com ou sem ela; a rota, o `build`
e o site.

Tudo contra cópias descartáveis (`tests.fixture.Vault`), um config temporário
e uma lista de brincar (`RIFTVAULT_PROMOS`): nunca o `data/` nem a lista real —
ele vai corrigi-la à mão, e um teste preso a ela partia a cada correcção.
"""

from __future__ import annotations

import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ["RIFTVAULT_CONFIG"] = str(Path(tempfile.gettempdir()) / "riftvault-nao-existe.json")

from tests.fixture import REPO, Vault  # noqa: E402

LISTA = [
    {"categoria": "Nexus Night", "origem": "Teste", "nome": "Defy", "nota": ""},
    {"categoria": "Nexus Night", "origem": "Teste", "nome": "Riven Shattered", "nota": ""},
    {"categoria": "Nexus Night", "origem": "Outra", "nome": "Lux - Crownguard", "nota": "Campeao"},
    {"categoria": "Bundle", "origem": "Worlds", "nome": "Darius, Hand of Noxus", "nota": ""},
    {"categoria": "Bundle", "origem": "Worlds", "nome": "Defy", "nota": "no bundle"},
    {"categoria": "Judge", "origem": "-", "nome": "K'Sante Courageous", "nota": ""},
    {"categoria": "Judge", "origem": "-", "nome": "Foo, Defy", "nota": ""},
    {"categoria": "Judge", "origem": "-", "nome": "Sol Star", "nota": ""},
]
AZIR = "Legend:\n1 Hand of Noxus\n\nMainDeck:\n3 Defy\n3 Brutalizer\n"


class Base(unittest.TestCase):
    def setUp(self):
        # A lista de brincar tem de estar apontada ANTES do `Vault`, que é
        # quem recarrega o `config` (o caminho é uma constante de módulo).
        self.lista = Path(tempfile.mkdtemp(prefix="riftvault-promos-")) / "promos.json"
        self.escrever_lista(LISTA)
        os.environ["RIFTVAULT_PROMOS"] = str(self.lista)
        self.addCleanup(lambda: os.environ.pop("RIFTVAULT_PROMOS", None))
        self.v = Vault()
        self.addCleanup(self.v.close)
        from riftvault import (a_mais, a_subir, collection, config, decks, faltas,
                               locais, metrics, pending, prices, promos, uso_decks)
        for m in (metrics, locais, pending, decks, faltas, a_subir, uso_decks, a_mais,
                  prices, promos):
            importlib.reload(m)
        self.promos, self.a_mais, self.a_subir = promos, a_mais, a_subir
        self.collection, self.config, self.decks = collection, config, decks
        self.metrics, self.prices = metrics, prices

    def escrever_lista(self, promos, **cabeca):
        self.lista.write_text(json.dumps({
            "fonte": "site de brincar", "url": "https://example.invalid/promos",
            "lido_em": "2026-09-18", "aviso": "lista de brincar", "promos": promos,
            **cabeca}), encoding="utf-8")

    def com_config(self, extra: dict):
        caminho = self.v.root / "config.json"
        caminho.write_text(json.dumps(extra), encoding="utf-8")
        os.environ["RIFTVAULT_CONFIG"] = str(caminho)
        importlib.reload(self.config)
        self.config.load.cache_clear()

        def repor():
            os.environ["RIFTVAULT_CONFIG"] = str(
                Path(tempfile.gettempdir()) / "riftvault-nao-existe.json")
            importlib.reload(self.config)
            self.config.load.cache_clear()

        self.addCleanup(repor)

    def montar(self, decks: dict | None = None):
        """Uma edição TST (100 nominais) e uma OGS (order 2): Defy (base, alt
        art e sobrenumerada), Riven, dois Legends, Lux (base em TST e em OGS,
        e a promo `TST-SP1` do catálogo), Brutalizer, e um par ambíguo."""
        self.com_config({"sets": {"TST": {"name": "Teste", "order": 1},
                                  "OGS": {"name": "Starters", "order": 2}}})
        con = self.v.connect()
        self.addCleanup(con.close)
        add = self.v.add_printing
        add(con, "tst-001-100", "TST", 1, "Defy", size=100)
        add(con, "tst-001a-100", "TST", 1, "Defy", variant="a", kind="alt_art",
            rarity="showcase", base_rarity="common", size=100)
        add(con, "tst-002-100", "TST", 2, "Riven, Shattered", rarity="rare", size=100)
        add(con, "tst-003-100", "TST", 3, "Hand of Noxus", card_type="Legend", size=100)
        add(con, "tst-004-100", "TST", 4, "Lux, Crownguard", rarity="epic", size=100)
        add(con, "tst-005-100", "TST", 5, "Brutalizer", size=100)
        add(con, "tst-006-100", "TST", 6, "Sol, Star", size=100)
        add(con, "tst-007-100", "TST", 7, "Sol - Star", size=100)
        add(con, "tst-008-100", "TST", 8, "Emperor of the Sands", card_type="Legend", size=100)
        add(con, "tst-101-100", "TST", 101, "Defy", size=100, api_sort=101)
        add(con, "tst-sp1", "TST", 1, "Lux, Crownguard", variant="sp1", kind="special",
            rarity="epic", lane="sp", codigo="TST-SP1/002", api_sort=200)
        add(con, "ogs-001", "OGS", 1, "Lux, Crownguard", rarity="epic", size=5)
        add(con, "ogs-002", "OGS", 2, "Hand of Noxus", card_type="Legend", size=5)
        con.execute("INSERT INTO catalog.cardtrader_map (printing_id, blueprint_id, "
                    "market_name) VALUES ('tst-004-100', 1, 'Lux - Crownguard')")
        con.execute("INSERT INTO catalog.cardtrader_map (printing_id, blueprint_id, "
                    "market_name) VALUES ('ogs-001', 2, 'Lux - Crownguard')")
        for pid, c in (("tst-001-100", 100), ("tst-001a-100", 2000), ("tst-002-100", 500),
                       ("tst-003-100", 1000), ("tst-004-100", 3000), ("tst-005-100", 50),
                       ("tst-101-100", 9000), ("tst-sp1", 8000), ("ogs-001", 40)):
            con.execute("INSERT INTO catalog.price_latest (printing_id, price_cents, "
                        "from_foil) VALUES (?,?,0)", (pid, c))
        self.v.rebuild(con)
        con.commit()
        for slug, texto in (decks or {}).items():
            self.v.write_deck(slug, texto)
        self.decks.import_all(con, log=lambda *_: None)
        return con

    def ter(self, con, pid, n):
        self.collection.adjust(con, pid, n, source="test")

    def item(self, p, categoria, nome):
        cat = next(c for c in p["categorias"] if c["label"] == categoria)
        return next(x for x in cat["items"] if x["nome"] == nome)


class TestALista(Base):
    def test_le_a_lista_e_guarda_a_fonte(self):
        lst = self.promos.carregar()
        self.assertEqual(len(lst["promos"]), 8)
        self.assertEqual(lst["fonte"], "site de brincar")
        self.assertEqual(lst["lido_em"], "2026-09-18")
        self.assertEqual(lst["ficheiro"], str(self.lista))
        self.assertEqual(lst["promos"][2],
                         {"categoria": "Nexus Night", "origem": "Outra",
                          "nome": "Lux - Crownguard", "nota": "Campeao"})

    def test_origem_e_nota_podem_faltar(self):
        self.escrever_lista([{"categoria": "X", "nome": "Defy"}])
        self.assertEqual(self.promos.carregar()["promos"],
                         [{"categoria": "X", "origem": "", "nome": "Defy", "nota": ""}])

    def test_sem_ficheiro_ou_sem_nome_rebenta(self):
        self.lista.unlink()
        with self.assertRaises(self.promos.ListaInvalida):
            self.promos.carregar()
        self.escrever_lista([{"categoria": "X", "nome": " "}])
        with self.assertRaises(self.promos.ListaInvalida):
            self.promos.carregar()
        self.lista.write_text("{", encoding="utf-8")
        with self.assertRaises(self.promos.ListaInvalida):
            self.promos.carregar()
        self.lista.write_text(json.dumps({"promos": "nada"}), encoding="utf-8")
        with self.assertRaises(self.promos.ListaInvalida):
            self.promos.carregar()

    def test_a_lista_real_do_repositorio_le_se(self):
        """A que ele corrige à mão: só se fixa a FORMA (lê-se e tem entradas),
        nunca o conteúdo."""
        lst = self.promos.carregar(REPO / "data" / "promos_oficiais.json")
        self.assertGreater(len(lst["promos"]), 0)
        self.assertTrue(lst["url"].startswith("https://"))
        self.assertIn("robots", lst["aviso"])


class TestOCasamento(Base):
    def casar(self, con, *nomes):
        return self.promos.casar(con, nomes)

    def test_exacto(self):
        con = self.montar()
        self.assertEqual(self.casar(con, "Defy")["Defy"], ("defy", "exacto"))
        self.assertEqual(self.casar(con, "  defy ")["  defy "], ("defy", "exacto"))

    def test_pelo_nome_do_mercado(self):
        """«Lux - Crownguard» é como o CardTrader escreve a «Lux, Crownguard»:
        duas impressões com esse nome, a MESMA carta — casa."""
        con = self.montar()
        self.assertEqual(self.casar(con, "Lux - Crownguard")["Lux - Crownguard"],
                         ("lux, crownguard", "mercado"))

    def test_nome_do_mercado_em_duas_cartas_nao_casa(self):
        con = self.montar()
        con.execute("INSERT INTO catalog.cardtrader_map (printing_id, blueprint_id, "
                    "market_name) VALUES ('tst-005-100', 3, 'Lux - Crownguard')")
        # ... a menos que outro casamento o resolva: aqui o «sem separador»
        # ainda dá a Lux, e é esse que vale.
        self.assertEqual(self.casar(con, "Lux - Crownguard")["Lux - Crownguard"],
                         ("lux, crownguard", "sem separador"))
        con.execute("INSERT INTO catalog.cardtrader_map (printing_id, blueprint_id, "
                    "market_name) VALUES ('tst-002-100', 4, 'Bla - Ble')")
        con.execute("INSERT INTO catalog.cardtrader_map (printing_id, blueprint_id, "
                    "market_name) VALUES ('tst-003-100', 5, 'Bla - Ble')")
        self.assertIsNone(self.casar(con, "Bla - Ble")["Bla - Ble"])

    def test_sem_o_separador_do_subtitulo(self):
        con = self.montar()
        self.assertEqual(self.casar(con, "Riven Shattered")["Riven Shattered"],
                         ("riven, shattered", "sem separador"))
        self.assertEqual(self.casar(con, "Riven - Shattered")["Riven - Shattered"],
                         ("riven, shattered", "sem separador"))

    def test_sem_separador_ambiguo_nao_casa(self):
        """«Sol, Star» e «Sol - Star» são duas cartas: «Sol Star» não escolhe."""
        con = self.montar()
        self.assertIsNone(self.casar(con, "Sol Star")["Sol Star"])

    def test_a_cauda_so_num_legend(self):
        con = self.montar()
        self.assertEqual(self.casar(con, "Darius, Hand of Noxus")["Darius, Hand of Noxus"],
                         ("hand of noxus", "cauda"))
        self.assertEqual(self.casar(con, "Darius - Hand of Noxus")["Darius - Hand of Noxus"],
                         ("hand of noxus", "cauda"))
        # A Defy é uma Unit: «Foo, Defy» não é a regra do Campeão e não casa.
        self.assertIsNone(self.casar(con, "Foo, Defy")["Foo, Defy"])

    def test_desconhecido_nao_casa_nem_por_aproximacao(self):
        con = self.montar()
        r = self.casar(con, "K'Sante Courageous", "Def", "Defyy", "Riven")
        self.assertEqual(list(r.values()), [None, None, None, None])


class TestOPayload(Base):
    def test_as_categorias_vem_por_tamanho_e_o_resto_pela_ordem_do_ficheiro(self):
        con = self.montar()
        p = self.promos.payload(con)
        # Nexus Night 3, Judge 3 (a empate, a que aparece primeiro), Bundle 2.
        self.assertEqual([(c["label"], c["entradas"], c["cartas"], c["nao_casadas"])
                          for c in p["categorias"]],
                         [("Nexus Night", 3, 3, 0), ("Judge", 3, 3, 3), ("Bundle", 2, 2, 0)])
        self.assertEqual([x["nome"] for x in p["categorias"][0]["items"]],
                         ["Defy", "Riven Shattered", "Lux - Crownguard"])
        self.assertEqual(p["categorias"][0]["id"], "nexus-night")

    def test_a_foto_e_da_versao_normal_da_edicao_mais_antiga(self):
        con = self.montar()
        p = self.promos.payload(con)
        x = self.item(p, "Nexus Night", "Defy")
        # Nem a alt art (`tst-001a`) nem a sobrenumerada (`tst-101`).
        self.assertEqual((x["printing_id"], x["code"], x["set"]),
                         ("tst-001-100", "TST-001/100", "TST"))
        self.assertEqual(x["img"], "img/tst-001-100.webp")
        self.assertEqual((x["name"], x["type"], x["rarity"]), ("Defy", "Unit", "common"))
        # A Lux existe em TST (order 1) e em OGS (order 2): a foto é a de TST.
        self.assertEqual(self.item(p, "Nexus Night", "Lux - Crownguard")["printing_id"],
                         "tst-004-100")
        # O Legend pela cauda leva a foto do Legend.
        self.assertEqual(self.item(p, "Bundle", "Darius, Hand of Noxus")["code"], "TST-003/100")
        self.assertIn("versão NORMAL", p["avisos"]["foto"])

    def test_tens_conta_a_carta_em_qualquer_versao_com_a_ressalva(self):
        con = self.montar()
        self.ter(con, "tst-001-100", 2)
        self.ter(con, "tst-001a-100", 1)
        self.ter(con, "tst-101-100", 1)
        p = self.promos.payload(con)
        x = self.item(p, "Nexus Night", "Defy")
        self.assertEqual(x["tens"], 4)
        self.assertEqual([(y["code"], y["kind"], y["qty"]) for y in x["tens_por"]],
                         [("TST-001/100", "base", 2), ("TST-001a/100", "alt_art", 1),
                          ("TST-101/100", "base", 1)])
        self.assertEqual(self.item(p, "Nexus Night", "Riven Shattered")["tens"], 0)
        self.assertIn("não diz se alguma é a promo", p["avisos"]["ter"])
        # O total: cartas casadas de que tem pelo menos uma (a Defy, uma vez).
        self.assertEqual(p["totals"]["tens"], 1)

    def test_a_promo_do_catalogo_e_a_mesma_carta_vista_de_outro_sitio(self):
        con = self.montar()
        self.ter(con, "tst-sp1", 1)
        p = self.promos.payload(con)
        x = self.item(p, "Nexus Night", "Lux - Crownguard")
        self.assertEqual(x["promo_catalogo"], [{"id": "tst-sp1", "code": "TST-SP1/002", "qty": 1}])
        self.assertEqual(x["tens"], 1)
        self.assertEqual(self.item(p, "Nexus Night", "Defy")["promo_catalogo"], [])

    def test_o_mesmo_nome_em_duas_categorias_diz_tambem(self):
        con = self.montar()
        p = self.promos.payload(con)
        self.assertEqual(self.item(p, "Nexus Night", "Defy")["tambem"], ["Bundle (Worlds)"])
        self.assertEqual(self.item(p, "Bundle", "Defy")["tambem"], ["Nexus Night (Teste)"])
        self.assertEqual(self.item(p, "Bundle", "Defy")["nota"], "no bundle")
        self.assertEqual(self.item(p, "Nexus Night", "Riven Shattered")["tambem"], [])

    def test_as_nao_encontradas_ficam_a_vista_com_o_numero(self):
        con = self.montar()
        p = self.promos.payload(con)
        self.assertEqual([(x["nome"], x["categoria"]) for x in p["nao_encontradas"]],
                         [("K'Sante Courageous", "Judge"), ("Foo, Defy", "Judge"),
                          ("Sol Star", "Judge")])
        self.assertEqual(p["totals"], {
            "entradas": 8, "cartas": 7, "casadas": 4, "nao_casadas": 3, "tens": 0,
            "por_via": {"exacto": 1, "mercado": 1, "sem separador": 1, "cauda": 1}})
        # Não há tile sem foto no meio de uma categoria.
        self.assertEqual(next(c for c in p["categorias"] if c["label"] == "Judge")["items"], [])

    def test_sem_alvo_sem_falta_sem_euros(self):
        con = self.montar()
        p = self.promos.payload(con)
        texto = json.dumps(p, ensure_ascii=False)
        for chave in ('"target"', '"missing"', '"price"', '"cents"', '"total"', "€"):
            self.assertNotIn(chave, texto)

    def test_a_lista_vazia_da_uma_montra_vazia(self):
        con = self.montar()
        self.escrever_lista([])
        p = self.promos.payload(con)
        self.assertEqual((p["categorias"], p["nao_encontradas"], p["totals"]["entradas"]),
                         ([], [], 0))


class TestNadaMexe(Base):
    """A montra não conta para nada: os números da Coleção, das listas, do «A
    mais», do valor e dos decks são os mesmos antes e depois de a pedir — e
    ela não escreve."""

    def fotografia(self, con):
        sp = self.metrics.set_payload(con, "TST")
        wl = self.a_subir.master_faltas(con)
        am = self.a_mais.payload(con)
        return {
            "progress": sp["progress"], "blocks": sp["blocks"],
            "n_groups": len(sp["groups"]),
            "levels": self.metrics.niveis_payload(con),
            "wantlist": ((wl["cards"], wl["copies"], wl["cents"], wl["scope"]),
                         [(x["printing_id"], x["missing"]) for d in wl["sets"] for x in d["items"]]),
            "a_mais": am["totals"],
            "value": self.prices.collection_value(con),
            "decks": self.decks.resumo_das_faltas(con),
            "copies": con.execute("SELECT COUNT(*), COALESCE(SUM(qty), 0) FROM copies").fetchone()[:],
            "ops": con.execute("SELECT COUNT(*) FROM ops").fetchone()[0],
        }

    def test_antes_e_depois_iguais_e_nao_escreve(self):
        con = self.montar(decks={"azir": AZIR})
        self.ter(con, "tst-001-100", 2)
        self.ter(con, "tst-001a-100", 1)
        self.ter(con, "tst-004-100", 3)
        self.ter(con, "tst-sp1", 1)
        antes = self.fotografia(con)
        p = self.promos.payload(con)
        self.assertGreater(p["totals"]["casadas"], 0)
        depois = self.fotografia(con)
        self.assertEqual(antes, depois)
        # E a montra em si não altera o que a Coleção diz sobre a mesma carta.
        self.assertEqual(depois["progress"]["master"]["total"], antes["progress"]["master"]["total"])

    def test_ninguem_le_a_montra(self):
        """Prova estrutural: nenhum módulo das contas importa o `promos` — a
        percentagem, as listas, o «A mais», as Faltas e os decks não a conhecem."""
        import re
        for nome in ("metrics", "a_subir", "a_mais", "faltas", "faltas_edicao", "decks",
                     "quanto_custa", "pending", "locais", "prices", "collection"):
            src = (REPO / "riftvault" / f"{nome}.py").read_text(encoding="utf-8")
            importados = " ".join(re.findall(r"from \. import \(([^)]*)\)", src)
                                  + re.findall(r"from \. import ([^(\n]*)", src)
                                  + re.findall(r"^import (.*)$", src, re.M))
            self.assertNotRegex(importados, r"\bpromos\b", f"{nome}.py importa o promos")
            self.assertNotIn("promos.payload", src, f"{nome}.py lê a montra")


class TestRotasEBuild(Base):
    def test_a_rota_responde_e_sem_lista_da_404_com_a_razao(self):
        con = self.montar()
        con.close()
        from riftvault import server
        importlib.reload(server)
        app = server.app
        app.config["TESTING"] = True
        c = app.test_client()
        r = c.get("/api/promos.json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["totals"]["casadas"], 4)
        self.lista.unlink()
        r = c.get("/api/promos.json")
        self.assertEqual(r.status_code, 404)
        self.assertIn("não existe", r.get_json()["error"])

    def test_o_build_escreve_o_ficheiro(self):
        con = self.montar()
        con.close()
        from riftvault import build
        importlib.reload(build)
        out = self.v.root / "site"
        build._gerar(out, log=lambda *_: None, imagens=False)
        f = out / "api" / "promos.json"
        self.assertTrue(f.exists())
        p = json.loads(f.read_text(encoding="utf-8"))
        self.assertEqual([c["label"] for c in p["categorias"]], ["Nexus Night", "Judge", "Bundle"])
        self.assertEqual(p["image_mode"], "remote")

    def test_o_site_tem_o_botao_dentro_da_colecao(self):
        html = (REPO / "riftvault" / "web" / "index.html").read_text(encoding="utf-8")
        js = (REPO / "riftvault" / "web" / "app.js").read_text(encoding="utf-8")
        css = (REPO / "riftvault" / "web" / "style.css").read_text(encoding="utf-8")
        # Dentro da secção Coleção, não um separador de topo.
        self.assertNotIn('data-section="promos"', html)
        self.assertLess(html.index('<section id="colecao">'), html.index('id="promos"'))
        self.assertLess(html.index('id="promos"'), html.index('<section id="decks"'))
        self.assertIn("api/promos.json", js)
        self.assertIn("function loadPromos", js)
        self.assertIn("function prTile", js)
        self.assertIn("#colecao.promos-on", css)
        # Sem controlos de compra nem alvos na montra.
        inicio = js.index("MONTRA «PROMOS»")
        fim = js.index("SECÇÃO DECKS")
        for proibido in ("cmLigar", "cardmarket", "faltam ${", "eur(", "target"):
            self.assertNotIn(proibido, js[inicio:fim], proibido)

    def test_a_lista_real_esta_versionada(self):
        """A lista vive no repositório e não no .gitignore — é ele que a corrige."""
        self.assertTrue((REPO / "data" / "promos_oficiais.json").exists())
        gi = (REPO / ".gitignore").read_text(encoding="utf-8")
        self.assertNotIn("promos_oficiais", gi)


if __name__ == "__main__":
    unittest.main()

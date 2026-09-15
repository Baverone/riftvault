"""«Quanto custa»: a tabela de preços, não as faltas (2026-09-15, à tarde).

André: *"o separador quanto custa nao e para ter as faltas! e para passar a
ter o top 5 comum mais cara, por cada set / o top 5 incomum mais cara por cada
set / o top5 rara mais cara por cada set / o top5 mitica mais cara por cada
set"*. E antes: *"apenas cartas versao ingles"*.

O que se fixa aqui: numa edição com oito comuns de preços diferentes aparecem
as CINCO mais caras, por ordem decrescente; uma carta que ele já tem completa
aparece na mesma (é a prova de que deixou de ser as faltas); as quatro
raridades têm o seu bloco, e «mítica» é o `epic` do catálogo; uma arte
alternativa NÃO aparece; mudar o `top_por_raridade` para 3 muda o corte; a
tabela não escreve nada e não mexe na wantlist nem na percentagem; e a
wantlist, as faltas dos decks e as Encomendas continuam a responder depois de o
`faltas.payload`/`api/faltas.json` terem saído. Mais a língua das ofertas.

Tudo contra cópias descartáveis (`tests.fixture.Vault`) e um config temporário
(`RIFTVAULT_CONFIG`): nunca o `data/` nem o `riftvault_config.json` reais.
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

# Antes do `Vault`, que é quem recarrega o `config` com as variáveis postas:
# sem isto o config real do repositório era lido pelos testes sem `com_config`.
os.environ["RIFTVAULT_CONFIG"] = str(Path(tempfile.gettempdir()) / "riftvault-nao-existe.json")

from tests.fixture import REPO, Vault  # noqa: E402


def oferta_ct(cents, lingua="en", **extra):
    """Uma oferta do CardTrader como a API a devolve, reduzida ao que se lê."""
    props = {"riftbound_language": lingua, "condition": "Near Mint",
             "riftbound_foil": False, **extra}
    return {"price_cents": cents, "price_currency": "EUR", "quantity": 1,
            "graded": False, "on_vacation": False, "user": {"id": cents},
            "properties_hash": props}


class Base(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.close)
        from riftvault import (a_subir, cardmarket, config, decks, faltas, locais,
                               metrics, pending, prices, quanto_custa)
        for m in (metrics, locais, pending, decks, faltas, cardmarket, a_subir,
                  prices, quanto_custa):
            importlib.reload(m)
        self.a_subir, self.prices, self.config = a_subir, prices, config
        self.decks, self.faltas, self.pending = decks, faltas, pending
        self.metrics, self.qc = metrics, quanto_custa

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


class TestSoIngles(Base):
    """Uma oferta que não seja em inglês não entra no preço."""

    def test_oferta_noutra_lingua_nao_entra(self):
        self.com_config({"precos": {"linguas": ["en"]}})
        o = self.prices.oferta([oferta_ct(50, "ja"), oferta_ct(80, "de"), oferta_ct(120, "en")])
        self.assertEqual(o["cents"], 120)
        self.assertEqual(o["n_listings"], 1)
        self.assertEqual(o["n_sellers"], 1)

    def test_so_ofertas_noutra_lingua_e_sem_preco(self):
        self.com_config({"precos": {"linguas": ["en"]}})
        o = self.prices.oferta([oferta_ct(50, "fr"), oferta_ct(60, "zh-CN")])
        self.assertIsNone(o["cents"])
        self.assertEqual(o["n_listings"], 0)

    def test_a_lista_do_config_manda(self):
        # É o config que decide, não uma constante: com o francês aceite a
        # oferta francesa mais barata passa a ser o preço.
        self.com_config({"precos": {"linguas": ["en", "fr"]}})
        o = self.prices.oferta([oferta_ct(50, "fr"), oferta_ct(120, "en")])
        self.assertEqual(o["cents"], 50)

    def test_sem_config_e_ingles(self):
        self.assertEqual(self.prices.linguas({}), frozenset({"en"}))

    def test_lista_vazia_rebenta(self):
        with self.assertRaises(ValueError):
            self.prices.linguas({"precos": {"linguas": []}})

    def test_config_real_diz_so_ingles(self):
        # O ficheiro dele: se alguém lá puser outra língua, este teste diz.
        raw = json.loads((REPO / "riftvault_config.json").read_text(encoding="utf-8"))
        self.assertEqual(raw["precos"]["linguas"], ["en"])


class ComCatalogo(Base):
    """Uma edição com oito comuns, três incomuns, seis raras e três épicas, mais
    uma arte alternativa cara e uma edição de starters sem botão."""

    PRECOS_COMUNS = [11, 700, 40, 300, 120, 90, 55, 210]      # fora de ordem, de propósito

    def preco(self, con, pid, cents):
        con.execute("INSERT INTO catalog.price_latest (printing_id, price_cents, "
                    "from_foil) VALUES (?,?,0)", (pid, cents))

    def montar(self, top=5, sem_edicoes=("OGS",), extra: dict | None = None):
        self.com_config({
            "sets": {"AAA": {"name": "Alfa", "order": 1}, "OGS": {"name": "Starters", "order": 2}},
            "quanto_custa": {"sem_edicoes": list(sem_edicoes), "top_por_raridade": top},
            **(extra or {}),
        })
        con = self.v.connect()
        self.addCleanup(con.close)
        add = self.v.add_printing
        n = 0
        for i, c in enumerate(self.PRECOS_COMUNS, 1):
            n += 1
            add(con, f"aaa-c{i}", "AAA", n, f"Comum {i}", rarity="common", size=30)
            self.preco(con, f"aaa-c{i}", c)
        for i, c in enumerate([200, 30, 500], 1):
            n += 1
            add(con, f"aaa-u{i}", "AAA", n, f"Incomum {i}", rarity="uncommon", size=30)
            self.preco(con, f"aaa-u{i}", c)
        for i, c in enumerate([900, 100, 1500, 250, 800, 60], 1):
            n += 1
            add(con, f"aaa-r{i}", "AAA", n, f"Rara {i}", rarity="rare", size=30)
            self.preco(con, f"aaa-r{i}", c)
        for i, c in enumerate([5000, 300, 9000], 1):
            n += 1
            add(con, f"aaa-e{i}", "AAA", n, f"Epica {i}", rarity="epic", size=30)
            self.preco(con, f"aaa-e{i}", c)
        # A arte alternativa da comum mais cara, ainda mais cara: não entra.
        add(con, "aaa-c2a", "AAA", 2, "Comum 2", variant="a", kind="alt_art",
            rarity="showcase", base_rarity="common", size=30)
        self.preco(con, "aaa-c2a", 99999)
        # Uma edição sem botão, com uma comum caríssima que não pode aparecer.
        add(con, "ogs-001", "OGS", 1, "Starter Comum", rarity="common", size=5)
        self.preco(con, "ogs-001", 77777)
        self.v.rebuild(con)
        con.commit()
        return con

    @staticmethod
    def edicao(t, set_id):
        return next(s for s in t["sets"] if s["set"] == set_id)

    @classmethod
    def bloco(cls, t, set_id, raridade):
        return next(g for g in cls.edicao(t, set_id)["rarities"] if g["rarity"] == raridade)

    @classmethod
    def ids(cls, t, set_id, raridade):
        return [x["printing_id"] for x in cls.bloco(t, set_id, raridade)["items"]]


class TestTop5(ComCatalogo):
    def test_as_cinco_comuns_mais_caras_por_ordem_decrescente(self):
        con = self.montar()
        t = self.qc.tabela(con)
        # 700, 300, 210, 120, 90 — as outras três (55, 40, 11) ficam de fora.
        self.assertEqual(self.ids(t, "AAA", "common"),
                         ["aaa-c2", "aaa-c4", "aaa-c8", "aaa-c5", "aaa-c6"])
        precos = [x["price"] for x in self.bloco(t, "AAA", "common")["items"]]
        self.assertEqual(precos, sorted(precos, reverse=True))
        g = self.bloco(t, "AAA", "common")
        self.assertEqual((g["n"], g["hidden"]), (8, 3))

    def test_uma_carta_que_ele_ja_tem_completa_aparece_na_mesma(self):
        # A prova de que deixou de ser as faltas: com as três cópias da comum
        # mais cara na Coleção, ela continua no topo — e a linha diz que tem.
        from riftvault import collection
        con = self.montar()
        collection.adjust(con, "aaa-c2", 3, source="test")
        t = self.qc.tabela(con)
        self.assertEqual(self.ids(t, "AAA", "common")[0], "aaa-c2")
        topo = self.bloco(t, "AAA", "common")["items"][0]
        self.assertEqual((topo["have"], topo["target"]), (3, 3))
        # E a lista é a MESMA com ou sem cópias: ter não filtra.
        collection.adjust(con, "aaa-c2", -3, source="test")
        self.assertEqual(self.ids(t, "AAA", "common"),
                         self.ids(self.qc.tabela(con), "AAA", "common"))

    def test_as_quatro_raridades_tem_bloco_e_mitica_e_o_epic(self):
        con = self.montar()
        t = self.qc.tabela(con)
        e = self.edicao(t, "AAA")
        self.assertEqual([g["rarity"] for g in e["rarities"]],
                         ["common", "uncommon", "rare", "epic"])
        self.assertEqual([g["label"] for g in e["rarities"]],
                         ["comuns", "incomuns", "raras", "míticas"])
        self.assertEqual(self.ids(t, "AAA", "uncommon"), ["aaa-u3", "aaa-u1", "aaa-u2"])
        self.assertEqual(self.ids(t, "AAA", "rare"),
                         ["aaa-r3", "aaa-r1", "aaa-r5", "aaa-r4", "aaa-r2"])
        self.assertEqual(self.ids(t, "AAA", "epic"), ["aaa-e3", "aaa-e1", "aaa-e2"])
        # Um bloco que caiba inteiro não esconde nada.
        self.assertEqual(self.bloco(t, "AAA", "epic")["hidden"], 0)

    def test_uma_arte_alternativa_nao_aparece(self):
        con = self.montar()
        t = self.qc.tabela(con)
        todos = [x["printing_id"] for s in t["sets"] for g in s["rarities"] for x in g["items"]]
        self.assertNotIn("aaa-c2a", todos)
        self.assertEqual(t["scope"]["alt_art"], 1)

    def test_top_3_muda_o_corte(self):
        con = self.montar(top=3)
        t = self.qc.tabela(con)
        self.assertEqual(t["top"], 3)
        self.assertEqual(self.ids(t, "AAA", "common"), ["aaa-c2", "aaa-c4", "aaa-c8"])
        self.assertEqual(self.bloco(t, "AAA", "common")["hidden"], 5)
        self.assertEqual(self.ids(t, "AAA", "epic"), ["aaa-e3", "aaa-e1", "aaa-e2"])

    def test_top_0_mostra_tudo_e_negativo_rebenta(self):
        con = self.montar(top=0)
        t = self.qc.tabela(con)
        self.assertEqual(len(self.ids(t, "AAA", "common")), 8)
        self.com_config({"quanto_custa": {"top_por_raridade": -1}})
        with self.assertRaises(ValueError):
            self.qc.top()

    def test_o_cinco_vem_do_config_e_nao_do_codigo(self):
        con = self.montar(top=2)
        self.assertEqual(len(self.ids(self.qc.tabela(con), "AAA", "common")), 2)
        self.assertEqual(self.qc.DEFAULTS["top_por_raridade"], 5)
        self.assertEqual(self.config.DEFAULTS["quanto_custa"]["top_por_raridade"], 5)

    def test_a_edicao_sem_botao_fica_de_fora_e_e_dita(self):
        con = self.montar()
        t = self.qc.tabela(con)
        self.assertEqual([s["set"] for s in t["sets"]], ["AAA"])
        self.assertEqual(t["sem_edicoes"], ["OGS"])
        # É o config que decide: sem a lista, o OGS ganha botão.
        self.com_config({"sets": {"AAA": {"name": "Alfa", "order": 1},
                                  "OGS": {"name": "Starters", "order": 2}},
                         "quanto_custa": {"sem_edicoes": [], "top_por_raridade": 5}})
        t2 = self.qc.tabela(con)
        self.assertEqual([s["set"] for s in t2["sets"]], ["AAA", "OGS"])
        self.assertEqual(self.ids(t2, "OGS", "common"), ["ogs-001"])

    def test_escondidas_e_colecao_extra_nao_entram(self):
        con = self.montar()
        add = self.v.add_printing
        add(con, "aaa-t01", "AAA", 1, "Token", variant="t01", kind="token",
            lane="t", rarity="common", codigo="AAA-T01")
        self.preco(con, "aaa-t01", 5000)
        # Uma sobrenumerada (31 num set de 30) com raridade de jogo, como os
        # Poros do UNL: é coleção extra, e com `so_sequencia` fica de fora.
        add(con, "aaa-over", "AAA", 31, "Poro Caro", rarity="common", size=30)
        self.preco(con, "aaa-over", 30000)
        self.v.rebuild(con)
        con.commit()
        t = self.qc.tabela(con)
        todos = {x["printing_id"] for s in t["sets"] for g in s["rarities"] for x in g["items"]}
        self.assertNotIn("aaa-t01", todos)
        self.assertNotIn("aaa-over", todos)
        self.assertEqual(t["scope"]["colecao_extra"], {"sobrenumeradas": 1})
        # E a `false` entra, com o bloco escrito na linha.
        self.com_config({"sets": {"AAA": {"name": "Alfa", "order": 1}},
                         "quanto_custa": {"sem_edicoes": [], "top_por_raridade": 5,
                                          "so_sequencia": False}})
        topo = self.bloco(self.qc.tabela(con), "AAA", "common")["items"][0]
        self.assertEqual((topo["printing_id"], topo["block_label"]), ("aaa-over", "sobrenumeradas"))

    def test_sem_preco_nao_entra_e_e_contada(self):
        con = self.montar()
        self.v.add_printing(con, "aaa-x", "AAA", 25, "Sem Oferta", rarity="rare", size=30)
        self.v.rebuild(con)
        con.commit()
        t = self.qc.tabela(con)
        self.assertNotIn("aaa-x", self.ids(t, "AAA", "rare"))
        self.assertEqual(t["scope"]["sem_preco"], 1)


class TestNaoMexeNoResto(ComCatalogo):
    """A tabela é apresentação: não escreve, e a wantlist e a percentagem não
    sabem dela."""

    def assinatura(self, con):
        w = self.a_subir.wantlist(con)
        nv = self.metrics.niveis_payload(con)
        return (w["lines"], w["copies"], w["cents"],
                json.dumps(nv, sort_keys=True))

    def test_a_tabela_nao_escreve_nem_muda_wantlist_ou_percentagem(self):
        from riftvault import collection
        con = self.montar()
        collection.adjust(con, "aaa-c2", 3, source="test")
        collection.adjust(con, "aaa-e3", 1, source="test")
        antes = self.assinatura(con)
        ops = con.execute("SELECT COUNT(*) FROM ops").fetchone()[0]
        copias = con.execute("SELECT SUM(qty) FROM copies").fetchone()[0]
        self.qc.tabela(con)
        self.qc.tabela(con)
        self.assertEqual(self.assinatura(con), antes)
        self.assertEqual(con.execute("SELECT COUNT(*) FROM ops").fetchone()[0], ops)
        self.assertEqual(con.execute("SELECT SUM(qty) FROM copies").fetchone()[0], copias)

    def test_a_wantlist_e_as_faltas_e_a_tabela_sao_perguntas_diferentes(self):
        # A comum mais cara está completa: sai da wantlist e fica na tabela.
        from riftvault import collection
        con = self.montar()
        collection.adjust(con, "aaa-c2", 3, source="test")
        na_wantlist = {x["printing_id"] for x in self.a_subir.wantlist(con)["items"]}
        self.assertNotIn("aaa-c2", na_wantlist)
        self.assertIn("aaa-c3", na_wantlist)
        self.assertEqual(self.ids(self.qc.tabela(con), "AAA", "common")[0], "aaa-c2")


AZIR = "Legend:\n1 Emperor of the Sands\n\nMainDeck:\n3 Defy\n"


class TestOQueFicouContinuaAResponder(Base):
    """Depois de o `faltas.payload`/`api/faltas.json` saírem, a wantlist da
    Coleção, as faltas dos decks e as Encomendas continuam a funcionar."""

    def catalogo(self):
        from riftvault import collection
        self.com_config({"sets": {"TST": {"name": "Teste", "order": 1}}})
        con = self.v.connect()
        self.addCleanup(con.close)
        self.v.add_printing(con, "tst-001-100", "TST", 1, "Defy", size=100)
        self.v.add_printing(con, "tst-002-100", "TST", 2, "Emperor of the Sands",
                            card_type="Legend", size=100)
        self.v.rebuild(con)
        for pid, cents in (("tst-001-100", 150), ("tst-002-100", 1000)):
            con.execute("INSERT INTO catalog.price_latest (printing_id, price_cents) "
                        "VALUES (?,?)", (pid, cents))
        collection.adjust(con, "tst-001-100", 1, source="test")
        self.v.write_deck("azir", AZIR)
        self.decks.import_all(con, log=lambda *_: None)
        return con

    def test_o_payload_do_separador_saiu(self):
        self.assertFalse(hasattr(self.faltas, "payload"),
                         "o faltas.payload era só do separador apagado")
        for nome in ("quanto_custa", "por_raridade", "edicoes_quanto_custa", "top_por_raridade"):
            self.assertFalse(hasattr(self.a_subir, nome), f"a_subir.{nome} era só do separador")

    def test_a_wantlist_da_colecao_responde(self):
        con = self.catalogo()
        w = self.a_subir.wantlist(con, "TST")
        # Falta 2 Defy (tem 1 de 3) e 1 Legend: 3 cópias, 2 × 1,50 + 10,00.
        self.assertEqual((w["lines"], w["copies"], w["cents"]), (2, 3, 2 * 150 + 1000))
        self.assertIn("Defy", w["text"])
        # E o `master_faltas` — o `api/wantlist.json` — é a mesma lista.
        m = self.a_subir.master_faltas(con)
        self.assertEqual((m["copies"], m["cents"]), (3, 2 * 150 + 1000))
        self.assertNotIn("quanto_custa", m)

    def test_as_faltas_dos_decks_respondem(self):
        con = self.catalogo()
        c = self.faltas.compras(con)
        self.assertEqual(set(c), {"staples", "por_deck", "todos_juntos", "pimp",
                                  "ignored_types", "totals"})
        # O azir pede 3 Defy e o Legend; ele tem 1 Defy: faltam 2 Defy + 1 Legend.
        self.assertEqual((c["totals"]["cards"], c["totals"]["copies"]), (2, 3))
        self.assertEqual(c["por_deck"][0]["copies"], 3)
        self.assertEqual(self.decks.resumo_das_faltas(con)["copies"], 3)
        # A wantlist dos decks no CLI passa por aqui.
        texto = self.faltas.wantlist(c["por_deck"][0]["by_set"])["text"]
        self.assertIn("2 Defy", texto)

    def test_as_encomendas_respondem_e_descontam(self):
        con = self.catalogo()
        self.pending.encomendar(con, card_key="defy", qty=2, source="test")
        e = self.pending.encomendas(con)
        self.assertEqual(e["totals"]["copies"], 2)
        self.assertEqual(e["falta_totals"]["copies"], 1,
                         "as 2 Defy a caminho fecham essa falta; fica só o Legend")
        # A wantlist da Coleção também desconta o que vem a caminho.
        w = self.a_subir.wantlist(con, "TST")
        self.assertEqual(w["copies"], 1, "só o Legend")
        # E o «Chegou» continua a dar entrada na Coleção.
        self.pending.arrive(con, None, source="test")
        self.assertEqual(self.pending.encomendas(con)["totals"]["copies"], 0)
        self.assertEqual(con.execute("SELECT qty FROM copies WHERE printing_id='tst-001-100'")
                         .fetchone()[0], 3)

    def test_o_servidor_tem_as_rotas_novas_e_nao_a_velha(self):
        from riftvault import server
        con = self.catalogo()
        con.close()
        app = server.app
        app.testing = True
        with app.test_client() as c:
            self.assertEqual(c.get("/api/faltas.json").status_code, 404)
            w = c.get("/api/wantlist.json")
            self.assertEqual(w.status_code, 200)
            self.assertEqual(w.get_json()["copies"], 3)
            self.assertEqual(c.get("/api/compras.json").get_json()["totals"]["copies"], 3)
            q = c.get("/api/quanto_custa.json").get_json()
            self.assertEqual([s["set"] for s in q["sets"]], ["TST"])
            self.assertEqual(c.get("/api/encomendas.json").get_json()["totals"]["copies"], 0)


class TestFrontend(unittest.TestCase):
    """O `app.js` lê os ficheiros novos e já não pede o `faltas.json`."""

    def setUp(self):
        self.js = (REPO / "riftvault" / "web" / "app.js").read_text(encoding="utf-8")

    def test_nao_pede_o_faltas_json(self):
        self.assertNotIn("'api/faltas.json'", self.js)
        for url in ("api/wantlist.json", "api/compras.json", "api/quanto_custa.json",
                    "api/encomendas.json"):
            self.assertIn(f"'{url}'", self.js, url)

    def test_as_abas_por_deck_vivem_nos_decks(self):
        m = re.search(r"DECK_FALTA_TABS = \[(.*?)\];", self.js, re.S)
        self.assertEqual(re.findall(r"id: '([a-z]+)'", m.group(1)), ["staples", "pordeck", "pimp"])
        self.assertIn("loadDeckFaltas(t.id)", self.js)
        # E o separador «Quanto custa» não tem abas de faltas nenhumas.
        self.assertNotRegex(self.js, r"(?<!DECK_)FALTA_TABS = \[")
        self.assertNotIn("renderMasterFaltas", self.js)
        self.assertIn("renderQuantoCusta", self.js)


if __name__ == "__main__":
    unittest.main()

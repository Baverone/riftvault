"""O separador «A mais» (2026-09-17): o excedente e as libertadas dos decks.

André: *"agora cria um botao que e o 'a mais' onde vai todas as cartas que
estao listadas a mais ou que estavam num deck e deixaram de estar"*.

O que se fixa aqui: uma Unit com 5 de 3 tem 2 a mais e com 3 não aparece; uma
arte alternativa e uma sobrenumerada com 2 de 1 têm 1 a mais; um token
escondido tem alvo 0 e sobra inteiro, marcado; o que os decks levam nunca é a
mais (`cópias − max(usadas, alvo)`); o que está no binder Decks/Venda e nenhum
deck pede é a mais; o que está sleevado num deck nunca aparece; a arte
alternativa que um deck joga sobe o alvo e não sobra; o registo do que os
decks pedem nasce vazio, a primeira importação é o ponto de partida (nada
libertado), tirar uma carta da lista liberta-a, baixar 3 -> 1 liberta 2,
voltar a pô-la tira-a da lista, apagar o deck liberta tudo com o rótulo, uma
importação sem mudanças não escreve; o payload não escreve nem mexe nos
níveis, na wantlist ou na falta dos decks; o OGS fica sem botão mas aparece;
a rota, o `build` e o site.

Tudo contra cópias descartáveis (`tests.fixture.Vault`) e um config temporário
(`RIFTVAULT_CONFIG`): nunca o `data/` nem o `riftvault_config.json` reais.
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

AZIR = "Legend:\n1 Emperor of the Sands\n\nMainDeck:\n3 Defy\n3 Brutalizer\n"
ORNN = "Legend:\n1 Forge Master\n\nMainDeck:\n3 Defy\n"


class Base(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.close)
        from riftvault import (a_mais, a_subir, collection, config, decks, faltas,
                               locais, metrics, pending, uso_decks)
        for m in (metrics, locais, pending, decks, faltas, a_subir, uso_decks, a_mais):
            importlib.reload(m)
        self.a_mais, self.a_subir, self.collection = a_mais, a_subir, collection
        self.config, self.decks, self.locais = config, decks, locais
        self.metrics, self.uso = metrics, uso_decks

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

    def montar(self, extra: dict | None = None, decks: dict | None = None):
        """Uma edição TST (100 nominais): Defy (base + alt art), Brutalizer,
        dois Legends, uma sobrenumerada, um token; e uma edição OGS."""
        self.com_config({
            "sets": {"TST": {"name": "Teste", "order": 1}, "OGS": {"name": "Starters", "order": 2}},
            **(extra or {}),
        })
        con = self.v.connect()
        self.addCleanup(con.close)
        add = self.v.add_printing
        add(con, "tst-001-100", "TST", 1, "Defy", size=100)
        add(con, "tst-001a-100", "TST", 1, "Defy", variant="a", kind="alt_art",
            rarity="showcase", base_rarity="common", size=100)
        add(con, "tst-002-100", "TST", 2, "Brutalizer", size=100)
        add(con, "tst-003-100", "TST", 3, "Emperor of the Sands", card_type="Legend", size=100)
        add(con, "tst-005-100", "TST", 5, "Forge Master", card_type="Legend", size=100)
        add(con, "tst-101-100", "TST", 101, "Sobre", rarity="rare", size=100, api_sort=101)
        add(con, "tst-t01", "TST", 1, "Token", variant="t01", kind="token",
            lane="t", codigo="TST-T01")
        add(con, "ogs-001", "OGS", 1, "Starter Um", size=5)
        for pid, c in (("tst-001-100", 100), ("tst-001a-100", 2000), ("tst-002-100", 50),
                       ("tst-003-100", 1000), ("tst-005-100", 1000), ("tst-101-100", 5000),
                       ("tst-t01", 5), ("ogs-001", 50)):
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

    def exc(self, con, pid):
        return next((x for x in self.a_mais.excedente(con) if x["printing_id"] == pid), None)

    def edicao(self, p, set_id):
        return next(s for s in p["sets"] if s["set"] == set_id)


class TestExcedente(Base):
    def test_unit_com_5_de_3_tem_2_a_mais_e_com_3_nao_aparece(self):
        con = self.montar()
        self.ter(con, "tst-002-100", 5)
        x = self.exc(con, "tst-002-100")
        self.assertEqual((x["have"], x["target"], x["extra"]), (5, 3, 2))
        self.assertEqual((x["from_colecao"], x["from_binder"]), (2, 0))
        self.assertFalse(x["hidden"])
        self.assertEqual(x["price"], 50)
        self.ter(con, "tst-002-100", -2)
        self.assertIsNone(self.exc(con, "tst-002-100"))

    def test_alt_art_e_sobrenumerada_com_2_de_1_tem_1_a_mais(self):
        con = self.montar()
        self.ter(con, "tst-001a-100", 2)
        self.ter(con, "tst-101-100", 2)
        a, o = self.exc(con, "tst-001a-100"), self.exc(con, "tst-101-100")
        self.assertEqual((a["target"], a["extra"]), (1, 1))
        self.assertEqual((o["target"], o["extra"]), (1, 1))
        self.assertEqual(o["block"], self.metrics.BLOCO_OVER)

    def test_escondida_tem_alvo_0_e_sobra_inteira_marcada(self):
        con = self.montar()
        self.ter(con, "tst-t01", 1)
        x = self.exc(con, "tst-t01")
        self.assertEqual((x["target"], x["extra"], x["hidden"]), (0, 1, True))
        p = self.a_mais.payload(con)
        self.assertEqual(p["scope"], {"hidden_cards": 1, "hidden_copies": 1})

    def test_o_que_os_decks_levam_nunca_e_a_mais(self):
        # Dois decks de Legends diferentes pedem 3 Brutalizer cada… só o Azir
        # pede Brutalizer aqui: 3 usadas, alvo 3, 5 cópias -> 2 a mais.
        con = self.montar(decks={"azir": AZIR})
        self.ter(con, "tst-002-100", 5)
        self.ter(con, "tst-003-100", 1)
        x = self.exc(con, "tst-002-100")
        self.assertEqual((x["used"], x["extra"]), (3, 2))
        self.assertEqual(x["in_decks"][0]["qty"], 3)

    def test_dois_grupos_a_pedir_a_mesma_carta_somam(self):
        # Dois grupos a pedir 3 Brutalizer cada usam 6: com 7 sobra 1, com 6 nada.
        con = self.montar(decks={"azir": AZIR,
                                 "ornn": "Legend:\n1 Forge Master\n\nMainDeck:\n3 Brutalizer\n"})
        self.ter(con, "tst-002-100", 7)
        x = self.exc(con, "tst-002-100")
        self.assertEqual((x["used"], x["target"], x["extra"]), (6, 3, 1))
        self.ter(con, "tst-002-100", -1)
        self.assertIsNone(self.exc(con, "tst-002-100"))

    def test_o_binder_que_nenhum_deck_pede_e_a_mais_e_o_sleevado_nunca(self):
        con = self.montar(decks={"azir": AZIR})
        self.ter(con, "tst-002-100", 4)
        self.ter(con, "tst-003-100", 1)
        # Uma para o binder Decks/Venda: o Azir leva-a de lá (o binder serve
        # primeiro), e a Coleção fica com 3 — nada a mais no binder, e 3 − max(2, 3) = 0.
        self.locais.mover(con, "tst-002-100", 1, self.locais.COLECAO, self.locais.BINDER,
                          source="test")
        self.assertIsNone(self.exc(con, "tst-002-100"))
        # Sem deck nenhum a pedi-la, a do binder é a mais, e diz de onde vem.
        (self.v.decks_dir / "azir.txt").unlink()
        self.decks.import_all(con, log=lambda *_: None)
        x = self.exc(con, "tst-002-100")
        self.assertEqual((x["from_binder"], x["from_colecao"], x["extra"]), (1, 0, 1))
        # Sleevada num deck: nunca aparece, mesmo que o deck já não a peça.
        self.v.write_deck("azir", AZIR)
        self.decks.import_all(con, log=lambda *_: None)
        self.locais.mover(con, "tst-002-100", 1, self.locais.BINDER, "deck:azir", source="test")
        self.ter(con, "tst-002-100", 2)     # 6 físicas: 1 no deck, 5 na Coleção
        x = self.exc(con, "tst-002-100")
        # O deck leva a sleevada + 2 da Coleção; a Coleção tem 5 − max(2, 3) = 2 a mais.
        self.assertEqual((x["from_binder"], x["from_colecao"], x["extra"]), (0, 2, 2))

    def test_a_alt_art_de_uma_carta_do_main_sobra_acima_de_1_mesmo_com_deck(self):
        """O main joga a base (2026-09-17, «voltar atrás»): o alvo da Alt Art
        é 1 e não sobe com o deck, e as 3 alt arts do Defy dão 2 a mais — o
        deck não as usa. (De 16/09 a 17/09 o deck jogava-as e nada sobrava.)"""
        con = self.montar(decks={"azir": AZIR})
        self.ter(con, "tst-001a-100", 3)
        self.ter(con, "tst-003-100", 1)
        x = self.exc(con, "tst-001a-100")
        self.assertEqual((x["target"], x["used"], x["extra"]), (1, 0, 2))
        (self.v.decks_dir / "azir.txt").unlink()
        self.decks.import_all(con, log=lambda *_: None)
        x = self.exc(con, "tst-001a-100")
        self.assertEqual((x["target"], x["extra"]), (1, 2))


class TestLibertadas(Base):
    def lib(self, con):
        return self.a_mais.libertadas(con)

    def test_o_registo_nasce_vazio_e_a_primeira_importacao_nao_liberta_nada(self):
        con = self.montar()
        self.assertEqual(self.uso.resumo(con), {"since": None, "events": 0})
        self.v.write_deck("azir", AZIR)
        self.decks.import_all(con, log=lambda *_: None)
        self.assertEqual(self.uso.resumo(con)["events"], 3)     # Legend, Defy, Brutalizer
        self.assertEqual(self.lib(con), [])
        # Uma importação sem mudanças não escreve.
        self.decks.import_all(con, log=lambda *_: None)
        self.assertEqual(self.uso.resumo(con)["events"], 3)

    def test_tirar_uma_carta_da_lista_liberta_a_e_voltar_a_po_la_tira_a(self):
        con = self.montar(decks={"azir": AZIR})
        self.ter(con, "tst-002-100", 2)
        self.v.write_deck("azir", "Legend:\n1 Emperor of the Sands\n\nMainDeck:\n3 Defy\n")
        self.decks.import_all(con, log=lambda *_: None)
        lib = self.lib(con)
        self.assertEqual(len(lib), 1)
        x = lib[0]
        self.assertEqual((x["card_key"], x["qty"], x["still"], x["slug"]), ("brutalizer", 3, 0, "azir"))
        self.assertEqual((x["printing_id"], x["have"], x["still_wanted"]), ("tst-002-100", 2, []))
        self.assertTrue(x["ts"].startswith("20"))
        p = self.a_mais.payload(con)
        self.assertEqual(self.edicao(p, "TST")["libertadas"]["copies"], 3)
        self.assertEqual(p["totals"]["libertadas"], {"cards": 1, "copies": 3})
        self.v.write_deck("azir", AZIR)
        self.decks.import_all(con, log=lambda *_: None)
        self.assertEqual(self.lib(con), [])

    def test_baixar_de_3_para_1_liberta_2_e_diz_quem_ainda_a_pede(self):
        con = self.montar(decks={"azir": AZIR, "ornn": ORNN})
        self.v.write_deck("azir", "Legend:\n1 Emperor of the Sands\n\nMainDeck:\n1 Defy\n3 Brutalizer\n")
        self.decks.import_all(con, log=lambda *_: None)
        (x,) = self.lib(con)
        self.assertEqual((x["card_key"], x["qty"], x["still"]), ("defy", 2, 1))
        self.assertEqual([(d["slug"], d["qty"]) for d in x["still_wanted"]],
                         [("azir", 1), ("ornn", 3)])

    def test_apagar_o_deck_liberta_tudo_com_o_rotulo(self):
        con = self.montar(decks={"azir": AZIR})
        (self.v.decks_dir / "azir.txt").unlink()
        self.decks.import_all(con, log=lambda *_: None)
        lib = self.lib(con)
        self.assertEqual(sorted(x["card_key"] for x in lib),
                         ["brutalizer", "defy", "emperor of the sands"])
        for x in lib:
            self.assertEqual(x["deck"], "Emperor of the Sands")
            self.assertEqual(x["still"], 0)
        self.assertEqual(self.uso.pedido_atual(con), {})
        # O CSV legível acompanha a tabela.
        log = (self.v.data / "decks.log").read_text(encoding="utf-8-sig")
        self.assertIn("Brutalizer", log)
        self.assertIn(",3,0", log)


class TestNaoMexe(Base):
    def test_o_payload_nao_escreve_e_nao_mexe_nos_invariantes(self):
        con = self.montar(decks={"azir": AZIR})
        self.ter(con, "tst-002-100", 5)
        self.ter(con, "tst-001-100", 1)
        ops = con.execute("SELECT COUNT(*) FROM ops").fetchone()[0]
        eventos = self.uso.resumo(con)["events"]
        niveis = self.metrics.niveis_payload(con)
        wl = self.a_subir.wantlist(con)["text"]
        falta = self.decks.resumo_das_faltas(con)
        valor = con.execute("SELECT SUM(qty) FROM copies").fetchone()[0]
        self.a_mais.payload(con)
        self.assertEqual(con.execute("SELECT COUNT(*) FROM ops").fetchone()[0], ops)
        self.assertEqual(self.uso.resumo(con)["events"], eventos)
        self.assertEqual(self.metrics.niveis_payload(con), niveis)
        self.assertEqual(self.a_subir.wantlist(con)["text"], wl)
        self.assertEqual(self.decks.resumo_das_faltas(con), falta)
        self.assertEqual(con.execute("SELECT SUM(qty) FROM copies").fetchone()[0], valor)
        # E a alocação dos decks não vê o excedente como coisa nenhuma: o
        # Brutalizer a mais não desconta nem soma à falta — que é 2 Defy (a
        # base serve, 2026-09-17; ele tem 1) e o Legend (só existe em base).
        self.assertEqual(falta["copies"], 3)

    def test_o_ogs_fica_sem_botao_mas_aparece_em_todas(self):
        con = self.montar()
        self.ter(con, "ogs-001", 4)
        p = self.a_mais.payload(con)
        self.assertEqual([(s["set"], s["button"]) for s in p["sets"]],
                         [("TST", True), ("OGS", False)])
        self.assertEqual(p["sem_edicoes"], ["OGS"])
        self.assertEqual(self.edicao(p, "OGS")["excedente"]["copies"], 1)
        # A lista é de config; vazia dá botão a todas.
        self.com_config({"sets": {"TST": {"name": "Teste", "order": 1}},
                         "a_mais": {"sem_edicoes": []}})
        p = self.a_mais.payload(con)
        self.assertTrue(all(s["button"] for s in p["sets"]))


class TestRotasEBuild(Base):
    def test_a_rota_responde(self):
        con = self.montar(decks={"azir": AZIR})
        self.ter(con, "tst-002-100", 4)
        con.close()
        from riftvault import server
        importlib.reload(server)
        app = server.app
        app.config["TESTING"] = True
        c = app.test_client()
        r = c.get("/api/a_mais.json")
        self.assertEqual(r.status_code, 200)
        p = r.get_json()
        self.assertEqual(p["totals"]["excedente"]["copies"], 1)
        self.assertEqual(c.get("/api/faltas_edicao.json").status_code, 200)

    def test_o_build_escreve_o_ficheiro(self):
        con = self.montar()
        con.close()
        from riftvault import build
        importlib.reload(build)
        out = self.v.root / "site"
        build._gerar(out, log=lambda *_: None, imagens=False)
        f = out / "api" / "a_mais.json"
        self.assertTrue(f.exists())
        p = json.loads(f.read_text(encoding="utf-8"))
        self.assertEqual([s["set"] for s in p["sets"]], ["TST", "OGS"])

    def test_o_site_tem_o_separador(self):
        html = (REPO / "riftvault" / "web" / "index.html").read_text(encoding="utf-8")
        js = (REPO / "riftvault" / "web" / "app.js").read_text(encoding="utf-8")
        self.assertIn('data-section="a-mais"', html)
        self.assertIn('id="am-body"', html)
        self.assertIn("api/a_mais.json", js)
        self.assertIn("'a-mais'", js)
        # Não é a Venda: sem botões do Cardmarket nem totais a vender.
        inicio = js.index("«A MAIS»")
        fim = js.index("function amLibTile")
        self.assertNotIn("cmLigar", js[inicio:fim])
        self.assertNotIn("cardmarket", js[inicio:fim].lower())
        self.assertNotIn("api/venda", js)


if __name__ == "__main__":
    unittest.main()

"""O separador «Faltas» (2026-09-15, fim da tarde): por edição, três blocos.

André: *"quero agora fazer uma seccao de faltas / quero as faltas por edicao e
dividido em 3 partes / Masterset / Alt Art / OverNumbered"*.

O que se fixa aqui: cada edição tem os três blocos, pela ordem dele; uma carta
do master set com 1 de 3 aparece a faltar 2; uma sobrenumerada com 1 cópia NÃO
aparece (alvo 1, está completa) e com 0 aparece a faltar 1; uma arte
alternativa com 1 de 3 aparece a faltar 2; uma carta que vem a caminho aparece
marcada e NÃO conta no que falta comprar; a wantlist e o texto do Cardmarket
continuam a trazer SÓ o master set; os totais de cada bloco somam ao total da
edição e as edições ao total; as promos ficam de fora e a página é avisada; o
`listas_de_compra.so_master_set` a `false` é a linha que mete os outros dois
blocos nas compras; o payload não escreve; o OGS entra; as rotas e o `build`
respondem.

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


class Base(unittest.TestCase):
    """Uma edição AAA (30 cartas nominais) com sequência, arte alternativa,
    sobrenumeradas, uma promo e um token; e uma edição OGS de starters."""

    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.close)
        from riftvault import (a_subir, cardmarket, collection, config, decks, faltas,
                               faltas_edicao, locais, metrics, pending)
        for m in (metrics, locais, pending, decks, faltas, cardmarket, a_subir,
                  faltas_edicao):
            importlib.reload(m)
        self.a_subir, self.config, self.collection = a_subir, config, collection
        self.pending, self.fe, self.metrics = pending, faltas_edicao, metrics

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

    def preco(self, con, pid, cents):
        con.execute("INSERT INTO catalog.price_latest (printing_id, price_cents, "
                    "from_foil) VALUES (?,?,0)", (pid, cents))

    def montar(self, extra: dict | None = None):
        self.com_config({
            "sets": {"AAA": {"name": "Alfa", "order": 1}, "OGS": {"name": "Starters", "order": 2}},
            **(extra or {}),
        })
        con = self.v.connect()
        self.addCleanup(con.close)
        add = self.v.add_printing
        # A sequência: três Units, um Legend.
        add(con, "aaa-001", "AAA", 1, "Unidade Um", size=30)
        add(con, "aaa-002", "AAA", 2, "Unidade Dois", size=30)
        add(con, "aaa-003", "AAA", 3, "Unidade Tres", size=30)
        add(con, "aaa-004", "AAA", 4, "Lenda", card_type="Legend", size=30)
        # A arte alternativa da primeira.
        add(con, "aaa-001a", "AAA", 1, "Unidade Um", variant="a", kind="alt_art",
            rarity="showcase", base_rarity="common", size=30)
        # Duas sobrenumeradas (31 e 32 num set de 30).
        add(con, "aaa-031", "AAA", 31, "Sobre Um", rarity="rare", size=30)
        add(con, "aaa-032", "AAA", 32, "Sobre Dois", rarity="rare", size=30)
        # Uma promo e um token: fora do separador / escondido.
        add(con, "aaa-sp1", "AAA", 1, "Promo Um", variant="sp1", kind="special",
            lane="sp", rarity="epic", codigo="AAA-SP1/002")
        add(con, "aaa-t01", "AAA", 1, "Token", variant="t01", kind="token",
            lane="t", codigo="AAA-T01")
        # Os starters.
        add(con, "ogs-001", "OGS", 1, "Starter Um", size=5)
        for pid, c in (("aaa-001", 100), ("aaa-002", 200), ("aaa-003", 300),
                       ("aaa-004", 1000), ("aaa-001a", 5000), ("aaa-031", 20000),
                       ("aaa-032", 30000), ("aaa-sp1", 9999), ("aaa-t01", 5),
                       ("ogs-001", 50)):
            self.preco(con, pid, c)
        self.v.rebuild(con)
        con.commit()
        return con

    @staticmethod
    def edicao(p, set_id):
        return next(s for s in p["sets"] if s["set"] == set_id)

    @classmethod
    def bloco(cls, p, set_id, bid):
        return next(g for g in cls.edicao(p, set_id)["blocks"] if g["id"] == bid)

    @classmethod
    def item(cls, p, set_id, bid, pid):
        return next((x for x in cls.bloco(p, set_id, bid)["items"]
                     if x["printing_id"] == pid), None)


class TestTresBlocos(Base):
    def test_cada_edicao_tem_os_tres_blocos_pela_ordem_dele(self):
        con = self.montar()
        p = self.fe.payload(con)
        self.assertEqual([s["set"] for s in p["sets"]], ["AAA", "OGS"])
        for s in p["sets"]:
            self.assertEqual([g["id"] for g in s["blocks"]],
                             ["master", "alt_art", "overnumbered"])
            self.assertEqual([g["label"] for g in s["blocks"]],
                             ["Master set", "Alt Art", "OverNumbered"])
        # O OGS entra — a exclusão do «Quanto custa» é só daquele separador.
        self.assertEqual(self.bloco(p, "OGS", "master")["copies"], 3)
        self.assertEqual(self.bloco(p, "OGS", "alt_art")["scope"], 0)

    def test_master_set_com_1_de_3_falta_2(self):
        con = self.montar()
        self.collection.adjust(con, "aaa-001", 1, source="test")
        x = self.item(self.fe.payload(con), "AAA", "master", "aaa-001")
        self.assertEqual((x["have"], x["target"], x["missing"], x["pending"]), (1, 3, 2, 0))
        self.assertEqual(x["total"], 200)
        # Com as três, sai da lista.
        self.collection.adjust(con, "aaa-001", 2, source="test")
        self.assertIsNone(self.item(self.fe.payload(con), "AAA", "master", "aaa-001"))

    def test_sobrenumerada_com_1_esta_completa_e_com_0_falta_1(self):
        con = self.montar()
        self.collection.adjust(con, "aaa-031", 1, source="test")
        p = self.fe.payload(con)
        self.assertIsNone(self.item(p, "AAA", "overnumbered", "aaa-031"))
        x = self.item(p, "AAA", "overnumbered", "aaa-032")
        self.assertEqual((x["have"], x["target"], x["missing"]), (0, 1, 1))
        g = self.bloco(p, "AAA", "overnumbered")
        self.assertEqual((g["cards"], g["copies"], g["cents"], g["scope"]), (1, 1, 30000, 2))
        self.assertEqual(g["target_label"], "1 de cada")
        # Uma segunda cópia não a põe em lado nenhum ("se eu tiver mais
        # adiciono na mesma").
        self.collection.adjust(con, "aaa-031", 1, source="test")
        self.assertIsNone(self.item(self.fe.payload(con), "AAA", "overnumbered", "aaa-031"))

    def test_arte_alternativa_com_0_de_1_falta_1_e_com_1_esta_completa(self):
        """1 de cada desde 2026-09-16 (*"Alt Art e Overnumbered e assim quero
        apenas 1 de cada"*) — e desde 2026-09-17 os decks não lhe acrescentam
        nada (`test_voltar_1.py`)."""
        con = self.montar()
        p = self.fe.payload(con)
        x = self.item(p, "AAA", "alt_art", "aaa-001a")
        self.assertEqual((x["have"], x["target"], x["missing"]), (0, 1, 1))
        self.assertEqual(self.bloco(p, "AAA", "alt_art")["target_label"], "1 de cada")
        # E não está no bloco do master set, mesmo tendo o número da base.
        self.assertIsNone(self.item(p, "AAA", "master", "aaa-001a"))
        self.collection.adjust(con, "aaa-001a", 1, source="test")
        self.assertIsNone(self.item(self.fe.payload(con), "AAA", "alt_art", "aaa-001a"))

    def test_a_arte_alternativa_de_uma_runa_nao_aparece(self):
        # Até 2026-09-17 à tarde era «Alt Art» aqui (e «runas especiais» na
        # grelha); desde então está RETIRADA de tudo (*"deixa as runas Alt
        # Art, nao incluas em nada"*, `test_runas_alt_fora.py`). A base fica.
        con = self.montar()
        self.v.add_printing(con, "aaa-005", "AAA", 5, "Runa", card_type="Rune", size=30)
        self.v.add_printing(con, "aaa-005a", "AAA", 5, "Runa", variant="a",
                            kind="alt_art", card_type="Rune", size=30)
        self.v.rebuild(con)
        p = self.fe.payload(con)
        self.assertIsNone(self.item(p, "AAA", "alt_art", "aaa-005a"))
        self.assertIsNotNone(self.item(p, "AAA", "master", "aaa-005"))


class TestACaminho(Base):
    def test_a_caminho_aparece_marcada_e_nao_conta(self):
        con = self.montar()
        self.collection.adjust(con, "aaa-002", 1, source="test")
        self.pending.add(con, "aaa-002", 2, source="test")      # cobre as 2 que faltam
        self.pending.add(con, "aaa-003", 1, source="test")      # cobre 1 de 3
        p = self.fe.payload(con)
        coberta = self.item(p, "AAA", "master", "aaa-002")
        self.assertEqual((coberta["have"], coberta["pending"], coberta["missing"],
                          coberta["short"]), (1, 2, 0, 2))
        self.assertEqual(coberta["total"], 0)
        parcial = self.item(p, "AAA", "master", "aaa-003")
        self.assertEqual((parcial["pending"], parcial["missing"]), (1, 2))
        self.assertEqual(parcial["total"], 600)
        g = self.bloco(p, "AAA", "master")
        # `cards`/`copies`/`cents` são só o que há a comprar: a coberta não
        # conta; a parcial conta as 2 que ainda faltam.
        self.assertEqual(g["pending_copies"], 3)
        self.assertEqual(g["pending_cards"], 2)
        self.assertNotIn("aaa-002", [x["printing_id"] for x in g["items"] if x["missing"] > 0])
        # 001: 3 × 100; 003: 2 × 300; 004: 1 × 1000. A 002 vale zero.
        self.assertEqual((g["cards"], g["copies"], g["cents"]), (3, 6, 1900))
        self.assertEqual(g["short_cards"], 4)

    def test_pendente_alem_do_alvo_nao_conta_a_mais(self):
        con = self.montar()
        self.pending.add(con, "aaa-004", 5, source="test")     # Legend, alvo 1
        x = self.item(self.fe.payload(con), "AAA", "master", "aaa-004")
        self.assertEqual((x["pending"], x["missing"]), (1, 0))


class TestSoOMasterSetSeCompra(Base):
    def test_a_wantlist_e_o_cardmarket_trazem_so_o_master_set(self):
        con = self.montar()
        # A alt art a 0 de 1 (2026-09-16): é ela que faz a diferença dos
        # totais, abaixo.
        p = self.fe.payload(con)
        self.assertEqual([b["in_lists"] for b in p["blocks"]], [True, False, False])
        self.assertTrue(p["so_master_set"])
        # A wantlist (a mesma da Coleção) só tem o master set — e pede
        # EXACTAMENTE as cópias do bloco `master` de cada edição.
        w = self.a_subir.wantlist(con)
        ids = {x["printing_id"] for x in w["items"]}
        self.assertEqual(ids, {"aaa-001", "aaa-002", "aaa-003", "aaa-004", "ogs-001"})
        for d in w["sets"]:
            g = self.bloco(p, d["set"], "master")
            self.assertEqual((d["cards"], d["copies"], d["cents"]),
                             (g["cards"], g["copies"], g["cents"]))
        self.assertEqual((w["copies"], w["cents"]),
                         (p["totals_lists"]["copies"], p["totals_lists"]["cents"]))
        # O texto do Cardmarket não fala das outras.
        self.assertNotIn("Sobre", w["text"])
        self.assertIn("Unidade Um", w["text"])
        # Mas o separador vê-as, com valor: é a diferença entre os dois totais.
        self.assertGreater(p["totals"]["cents"], p["totals_lists"]["cents"])
        self.assertEqual(p["totals"]["cents"] - p["totals_lists"]["cents"],
                         1 * 5000 + 20000 + 30000)

    def test_a_linha_de_config_que_os_mete_nas_compras(self):
        con = self.montar({"listas_de_compra": {"so_master_set": False}})
        p = self.fe.payload(con)
        self.assertEqual([b["in_lists"] for b in p["blocks"]], [True, True, True])
        self.assertFalse(p["so_master_set"])
        self.assertEqual(p["totals_lists"], p["totals"])
        # E a wantlist passa a trazê-las, pelo MESMO botão.
        ids = {x["printing_id"] for x in self.a_subir.wantlist(con)["items"]}
        self.assertIn("aaa-031", ids)
        self.assertIn("aaa-001a", ids)


class TestTotais(Base):
    def test_os_blocos_somam_a_edicao_e_as_edicoes_ao_total(self):
        con = self.montar()
        self.collection.adjust(con, "aaa-001", 1, source="test")
        self.pending.add(con, "aaa-003", 1, source="test")
        p = self.fe.payload(con)
        for s in p["sets"]:
            for k in ("cards", "copies", "cents", "pending_copies", "pending_cards",
                      "short_cards", "no_price"):
                self.assertEqual(s[k], sum(g[k] for g in s["blocks"]), (s["set"], k))
                self.assertEqual(s["lists"][k],
                                 sum(g[k] for g in s["blocks"] if g["in_lists"]), (s["set"], k))
        for k in ("cards", "copies", "cents", "pending_copies"):
            self.assertEqual(p["totals"][k], sum(s[k] for s in p["sets"]), k)
            self.assertEqual(p["totals_lists"][k], sum(s["lists"][k] for s in p["sets"]), k)
        # Os números concretos, para o teste poder falhar: AAA master
        # 2×100 + 3×200 + 2×300 + 1×1000 = 2400 (a 003 tem 1 a caminho); alt
        # 1×5000 (1 de cada desde 2026-09-16); over 20000 + 30000.
        aaa = self.edicao(p, "AAA")
        self.assertEqual(aaa["cents"], 2400 + 5000 + 50000)
        self.assertEqual(aaa["copies"], 8 + 1 + 2)
        self.assertEqual(aaa["pending_copies"], 1)

    def test_sem_preco_entra_na_lista_e_e_contada(self):
        con = self.montar()
        con.execute("DELETE FROM catalog.price_latest WHERE printing_id = 'aaa-002'")
        p = self.fe.payload(con)
        x = self.item(p, "AAA", "master", "aaa-002")
        self.assertIsNone(x["price"])
        self.assertEqual(x["total"], 0)
        self.assertEqual(self.bloco(p, "AAA", "master")["no_price"], 1)


class TestForaDoSeparador(Base):
    def test_promos_e_escondidas_ficam_de_fora_e_diz_se(self):
        con = self.montar()
        p = self.fe.payload(con)
        todos = [x["printing_id"] for s in p["sets"] for g in s["blocks"] for x in g["items"]]
        self.assertNotIn("aaa-sp1", todos)
        self.assertNotIn("aaa-t01", todos)
        self.assertEqual(p["scope"]["fora"], {"promos": 1})
        # Escondida não é «fora do separador»: nem chega ao âmbito.
        self.assertEqual(p["scope"]["printings"], 4 + 1 + 2 + 1)

    def test_nao_escreve(self):
        con = self.montar()
        antes = con.execute("SELECT COUNT(*) FROM ops").fetchone()[0]
        copias = con.execute("SELECT COALESCE(SUM(qty), 0) FROM copies").fetchone()[0]
        self.fe.payload(con)
        self.assertEqual(con.execute("SELECT COUNT(*) FROM ops").fetchone()[0], antes)
        self.assertEqual(con.execute("SELECT COALESCE(SUM(qty), 0) FROM copies").fetchone()[0],
                         copias)

    def test_nao_mexe_na_percentagem_nem_na_wantlist(self):
        con = self.montar()
        self.collection.adjust(con, "aaa-001", 3, source="test")
        niveis_antes = self.metrics.niveis_payload(con)
        w_antes = self.a_subir.wantlist(con)["text"]
        self.fe.payload(con)
        self.assertEqual(self.metrics.niveis_payload(con), niveis_antes)
        self.assertEqual(self.a_subir.wantlist(con)["text"], w_antes)


class TestRotasEBuild(Base):
    def test_a_rota_responde_e_a_do_quanto_custa_continua(self):
        con = self.montar()
        con.close()
        from riftvault import server
        importlib.reload(server)
        app = server.app
        app.config["TESTING"] = True
        c = app.test_client()
        r = c.get("/api/faltas_edicao.json")
        self.assertEqual(r.status_code, 200)
        p = r.get_json()
        self.assertEqual([b["id"] for b in p["blocks"]], ["master", "alt_art", "overnumbered"])
        self.assertEqual(c.get("/api/quanto_custa.json").status_code, 200)
        self.assertEqual(c.get("/api/wantlist.json").status_code, 200)

    def test_o_build_escreve_o_ficheiro(self):
        con = self.montar()
        con.close()
        from riftvault import build
        importlib.reload(build)
        out = self.v.root / "site"
        build._gerar(out, log=lambda *_: None, imagens=False)
        f = out / "api" / "faltas_edicao.json"
        self.assertTrue(f.exists())
        p = json.loads(f.read_text(encoding="utf-8"))
        self.assertEqual([s["set"] for s in p["sets"]], ["AAA", "OGS"])

    def test_o_site_tem_o_separador(self):
        html = (REPO / "riftvault" / "web" / "index.html").read_text(encoding="utf-8")
        js = (REPO / "riftvault" / "web" / "app.js").read_text(encoding="utf-8")
        self.assertIn('data-section="faltas-edicao"', html)
        self.assertIn('id="fe-body"', html)
        self.assertIn("api/faltas_edicao.json", js)
        # O «Quanto custa» não foi tocado: continua a ser a tabela de preços.
        self.assertIn("api/quanto_custa.json", js)
        self.assertNotIn("getJSON('api/faltas.json')", js)


if __name__ == "__main__":
    unittest.main()

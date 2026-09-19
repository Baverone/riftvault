"""O bloco «Runas — 12 de cada» no fim da Coleção (André, 2026-09-19).

Palavras dele: *"depois mete 12 runas de cada (nao contabilizes para nada, e
so para mim para contabilizar ali algumas coisas)"*.

O que se fixa: as runas do catálogo, uma linha cada, alvo 12; «tenho» é TUDO
o que ele fisicamente tem — a base, a alt art retirada, a promo escondida,
as do CardTrader, esteja onde estiver — com o número sem as retiradas ao
lado; a runa base aparece no master set E aqui, e a nota di-lo; e, acima de
tudo, que ISTO NÃO CONTA PARA NADA: nenhum módulo de contas o importa, o
payload da edição não o traz, mudar o alvo não mexe em número nenhum, e o
`payload` não escreve.

Tudo contra pastas temporárias (`tests.fixture.Vault`) e um config que não
existe: o `data/` e o `riftvault_config.json` a sério nunca são tocados.
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

from tests.fixture import REPO, Vault, config_decks_sem_alt_art  # noqa: E402

config_decks_sem_alt_art()

# Os módulos que fazem CONTAS — percentagem, níveis, wantlists, valor,
# faltas, A mais, decks, encomendas, quanto custa — e por isso não podem
# saber que a vista existe. Quem a chama é só o servidor, o build e a CLI.
# (O `config.py` guarda o `runas_vista.alvo` como guarda tudo o resto; não
# faz contas e não entra na lista.)
MODULOS_DE_CONTAS = ["metrics", "a_subir", "faltas", "faltas_edicao", "a_mais",
                     "uso_decks", "decks", "locais", "pending", "prices",
                     "collection", "quanto_custa", "cardmarket", "seguir",
                     "catalog", "db"]


def _config(caso, extra: dict) -> None:
    caminho = Path(tempfile.gettempdir()) / f"riftvault-runas-vista-{os.getpid()}.json"
    caminho.write_text(json.dumps({
        "decks": {"so_normais_excepto": ["legend", "champion"],
                  "versoes_especiais": ["a", "overnumbered", "promo"]},
        **extra}), encoding="utf-8")
    os.environ["RIFTVAULT_CONFIG"] = str(caminho)
    caso.addCleanup(lambda: os.environ.pop("RIFTVAULT_CONFIG", None))
    from riftvault import config
    importlib.reload(config)
    config.load.cache_clear()


class Base(unittest.TestCase):
    def setUp(self):
        config_decks_sem_alt_art(self)
        self.v = Vault()
        self.addCleanup(self.v.close)
        from riftvault import a_mais, a_subir, faltas_edicao, metrics, runas_vista
        for m in (metrics, a_subir, faltas_edicao, a_mais, runas_vista):
            importlib.reload(m)
        self.metrics, self.rv = metrics, runas_vista
        self.a_subir, self.faltas_edicao, self.a_mais = a_subir, faltas_edicao, a_mais

    def catalogo(self):
        """Duas runas e uma Unit. Da Calm Rune há a base do OGN (sequência),
        a alt art (retirada), a promo do VEN (escondida) e duas do CardTrader
        (`market_only`: uma base do SFD e a alt art do SFD, esta com o `a`
        omitido como o CardTrader faz)."""
        from riftvault import collection
        con = self.v.connect()
        v = self.v
        v.add_printing(con, "ogn-001-100", "OGN", 1, "Defy", size=100)
        v.add_printing(con, "ogn-042-100", "OGN", 42, "Calm Rune", card_type="Rune",
                       size=100)
        v.add_printing(con, "ogn-042a-100", "OGN", 42, "Calm Rune", card_type="Rune",
                       variant="a", kind="alt_art", rarity="showcase", size=100)
        v.add_printing(con, "ogn-007-100", "OGN", 7, "Fury Rune", card_type="Rune",
                       size=100)
        v.add_printing(con, "ven-r02", "VEN", 2, "Calm Rune", card_type="Rune",
                       variant="r02", kind="rune_promo", lane="r", codigo="VEN-R02")
        v.rebuild(con)
        for pid, ck, raw, version in (("ct-1", "calm rune", "R02", "SFD"),
                                      ("ct-2", "calm rune", "R02", "SFD | Alternate Art")):
            con.execute(
                "INSERT INTO catalog.market_only (printing_id, blueprint_id, set_id, "
                "collector_raw, card_key, market_name, market_set, version) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (pid, int(pid[3:]), "SFD", raw, ck, "Calm Rune", "Spiritforged", version))
        for pid, cents in (("ogn-001-100", 150), ("ogn-042-100", 11),
                           ("ogn-042a-100", 500), ("ogn-007-100", 11), ("ven-r02", 12)):
            con.execute("INSERT INTO catalog.price_latest (printing_id, price_cents) "
                        "VALUES (?,?)", (pid, cents))
        collection.adjust(con, "ogn-001-100", 3, source="test")
        collection.adjust(con, "ogn-042-100", 9, source="test")    # sequência
        collection.adjust(con, "ogn-042a-100", 6, source="test")   # retirada
        collection.adjust(con, "ven-r02", 1, source="test")        # escondida
        collection.adjust(con, "ct-1", 2, source="test")           # CardTrader, base
        collection.adjust(con, "ct-2", 12, source="test")          # CardTrader, alt art
        collection.adjust(con, "ogn-007-100", 1, source="test")
        return con

    def runa(self, p, nome):
        return next(x for x in p["runas"] if x["name"] == nome)


class TestOQueConta(Base):
    """«Tenho» é tudo o que ele fisicamente tem, de todas as versões."""

    def test_uma_linha_por_runa_com_alvo_12(self):
        con = self.catalogo()
        p = self.rv.payload(con)
        self.assertEqual([x["name"] for x in p["runas"]], ["Calm Rune", "Fury Rune"])
        self.assertEqual([x["target"] for x in p["runas"]], [12, 12])
        self.assertEqual(p["alvo"], 12)
        self.assertTrue(p["so_para_ver"])
        con.close()

    def test_soma_todas_as_versoes_e_diz_o_numero_sem_as_retiradas(self):
        con = self.catalogo()
        calm = self.runa(self.rv.payload(con), "Calm Rune")
        # 9 base + 6 alt art (retirada) + 1 promo (escondida) + 2 + 12 CardTrader.
        self.assertEqual(calm["total"], 30)
        # Sem as retiradas: saem a alt art do OGN e a do CardTrader.
        self.assertEqual(calm["sem_retiradas"], 12)
        origens = {o["code"]: o for o in calm["origens"]}
        self.assertEqual(origens["OGN-042/100"]["qty"], 9)
        self.assertEqual(origens["OGN-042/100"]["label"], "sequência")
        self.assertTrue(origens["OGN-042a/100"]["retirada"])
        self.assertEqual(origens["OGN-042a/100"]["label"], "alt art (retirada)")
        self.assertTrue(origens["VEN-R02"]["escondida"])
        self.assertFalse(origens["VEN-R02"]["retirada"])
        # A alt art do CardTrader leva o `a` que o CardTrader omite (2026-09-01).
        self.assertTrue(origens["SFD-R02a"]["retirada"])
        self.assertTrue(origens["SFD-R02a"]["fora_do_catalogo"])
        self.assertEqual(origens["SFD-R02"]["qty"], 2)
        self.assertFalse(origens["SFD-R02"]["retirada"])
        con.close()

    def test_a_runa_so_com_a_base_tem_os_dois_numeros_iguais(self):
        con = self.catalogo()
        fury = self.runa(self.rv.payload(con), "Fury Rune")
        self.assertEqual((fury["total"], fury["sem_retiradas"]), (1, 1))
        # Só as origens com cópias aparecem: a alt art a 0 não faz a lista crescer.
        self.assertEqual([o["code"] for o in fury["origens"]], ["OGN-007/100"])
        con.close()

    def test_conta_o_que_esta_num_deck_ou_no_binder(self):
        """É o que ele tem NA MÃO, esteja onde estiver — não é a Coleção."""
        from riftvault import locais
        con = self.catalogo()
        locais.mover(con, "ogn-042-100", 4, locais.COLECAO, locais.BINDER, source="test")
        calm = self.runa(self.rv.payload(con), "Calm Rune")
        self.assertEqual(calm["total"], 30)
        con.close()

    def test_os_totais_somam_as_runas(self):
        con = self.catalogo()
        t = self.rv.payload(con)["totals"]
        self.assertEqual(t, {"cards": 2, "total": 31, "sem_retiradas": 13, "alvo": 24})
        con.close()

    def test_o_tile_leva_a_imagem_da_base(self):
        con = self.catalogo()
        calm = self.runa(self.rv.payload(con), "Calm Rune")
        self.assertEqual(calm["img"], "img/ogn-042-100.webp")
        self.assertEqual(calm["code"], "OGN-042/100")
        con.close()

    def test_sem_retirada_no_config_os_dois_numeros_sao_iguais(self):
        _config(self, {"runas_especiais": {"tipos": ["Rune"], "excepto": ["base"],
                                           "retiradas": []}})
        con = self.catalogo()
        calm = self.runa(self.rv.payload(con), "Calm Rune")
        self.assertEqual((calm["total"], calm["sem_retiradas"]), (30, 30))
        con.close()

    def test_o_alvo_vem_do_config_e_zero_rebenta(self):
        _config(self, {"runas_vista": {"alvo": 5}})
        con = self.catalogo()
        p = self.rv.payload(con)
        self.assertEqual(p["alvo"], 5)
        self.assertEqual([x["target"] for x in p["runas"]], [5, 5])
        self.assertEqual(p["totals"]["alvo"], 10)
        con.close()
        _config(self, {"runas_vista": {"alvo": 0}})
        with self.assertRaises(ValueError):
            self.rv.alvo()

    def test_sem_tipo_de_runa_o_bloco_e_vazio(self):
        _config(self, {"runas_especiais": {"tipos": []}})
        con = self.catalogo()
        p = self.rv.payload(con)
        self.assertEqual(p["runas"], [])
        self.assertEqual(p["totals"]["cards"], 0)
        con.close()


class TestADuplicacaoEstaEscrita(Base):
    """A runa base do OGN aparece no master set E neste bloco — e diz-se."""

    def test_a_base_esta_nos_dois_sitios(self):
        con = self.catalogo()
        col = self.metrics.set_payload(con, "OGN")
        na_grelha = {p["id"]: p for g in col["groups"] for p in g["printings"]}
        self.assertEqual(na_grelha["ogn-042-100"]["block"], "master")
        self.assertEqual(na_grelha["ogn-042-100"]["target"], 3)     # a 3 no master set
        calm = self.runa(self.rv.payload(con), "Calm Rune")
        self.assertEqual(calm["target"], 12)                          # a 12 aqui
        self.assertIn("ogn-042-100", [o["id"] for o in calm["origens"]])
        con.close()

    def test_a_nota_diz_que_nao_conta_e_fala_da_sequencia(self):
        con = self.catalogo()
        nota = self.rv.payload(con)["nota"]
        self.assertIn("não conta para as métricas", nota)
        self.assertIn("sequência do master set", nota)
        con.close()


class TestNaoContaParaNada(Base):
    """A prova: nenhum módulo de contas o importa; o payload da edição não o
    traz; mudar o alvo não mexe em número nenhum; e não escreve."""

    def test_nenhum_modulo_de_contas_importa_a_vista(self):
        pasta = REPO / "riftvault"
        for nome in MODULOS_DE_CONTAS:
            src = (pasta / f"{nome}.py").read_text(encoding="utf-8")
            self.assertFalse("runas_vista" in src,
                             f"{nome}.py conhece a vista das runas — e não pode")
        # Quem a chama é quem serve páginas e ficheiros.
        for nome in ("server", "build", "cli"):
            src = (pasta / f"{nome}.py").read_text(encoding="utf-8")
            self.assertIn("runas_vista", src)

    def test_o_payload_da_edicao_nao_traz_a_vista(self):
        con = self.catalogo()
        col = self.metrics.set_payload(con, "OGN")
        self.assertNotIn("runas", json.dumps(list(col.keys())))
        ids = [b["id"] for b in col["blocks"]]
        self.assertNotIn("runas", ids)
        self.assertNotIn("runas_vista", ids)
        # A Encomendas é a mesma grelha e também não a traz.
        from riftvault import pending
        self.assertNotIn("runas", pending.grelha(con, "OGN"))
        con.close()

    def test_mudar_o_alvo_nao_mexe_em_numero_nenhum(self):
        """Com o alvo a 12 e a 1, tudo o que conta dá o mesmo."""
        def tudo(con):
            return json.dumps({
                "set": self.metrics.set_payload(con, "OGN")["progress"],
                "index": {k: v for k, v in self.metrics.index_payload(con).items()
                          if k != "generated_at"},
                "niveis": self.metrics.niveis_payload(con),
                "wantlist": {k: self.a_subir.master_faltas(con)[k]
                             for k in ("cards", "copies", "cents")},
                "faltas": self.faltas_edicao.payload(con)["totals"],
                "a_mais": self.a_mais.payload(con)["totals"],
            }, sort_keys=True, default=str)

        _config(self, {"runas_vista": {"alvo": 12}})
        con = self.catalogo()
        a = tudo(con)
        con.close()
        _config(self, {"runas_vista": {"alvo": 1}})
        con = self.v.connect()
        b = tudo(con)
        con.close()
        self.assertEqual(a, b)

    def test_a_vista_nao_escreve_nem_leva_euros(self):
        con = self.catalogo()
        antes = con.execute("SELECT printing_id, qty FROM copies ORDER BY 1").fetchall()
        ops = con.execute("SELECT COUNT(*) FROM ops").fetchone()[0]
        p = self.rv.payload(con)
        depois = con.execute("SELECT printing_id, qty FROM copies ORDER BY 1").fetchall()
        self.assertEqual([tuple(r) for r in antes], [tuple(r) for r in depois])
        self.assertEqual(con.execute("SELECT COUNT(*) FROM ops").fetchone()[0], ops)
        texto = json.dumps(p, ensure_ascii=False)
        self.assertNotIn("cents", texto)
        self.assertNotIn("price", texto)
        self.assertNotIn("€", texto)
        con.close()

    def test_o_denominador_e_o_valor_nao_levam_a_vista(self):
        """As 6 cópias retiradas e as 14 do CardTrader que o bloco soma
        continuam fora do valor e da percentagem, como antes."""
        from riftvault import prices
        con = self.catalogo()
        prog = self.metrics.set_payload(con, "OGN")["progress"]
        self.assertEqual(prog["master"]["total"], 3)   # Defy, Calm Rune, Fury Rune
        # 3 × 1,50 + 9 × 0,11 + 1 × 0,11 + a promo escondida a 0,12 = 5,72 € —
        # sem a alt art retirada (6 × 5 €) e sem nada do CardTrader (sem preço).
        self.assertEqual(prices.collection_value(con)["cents"], 572)
        con.close()


class TestRotasEBuild(Base):
    def test_a_rota(self):
        from riftvault import server
        con = self.catalogo()
        con.close()
        app = server.app
        app.testing = True
        with app.test_client() as c:
            p = c.get("/api/runas.json").get_json()
            self.assertEqual(p["totals"]["total"], 31)
            self.assertTrue(p["so_para_ver"])

    def test_o_build_escreve_o_ficheiro(self):
        from riftvault import build
        con = self.catalogo()
        con.close()
        out = self.v.root / "site"
        build.build(out, log=lambda *_: None)
        f = out / "api" / "runas.json"
        self.assertTrue(f.exists(), "falta api/runas.json no site")
        p = json.loads(f.read_text(encoding="utf-8"))
        self.assertEqual(p["totals"]["total"], 31)
        # E o payload da edição publicada continua sem a vista.
        col = json.loads((out / "api" / "set" / "OGN.json").read_text(encoding="utf-8"))
        self.assertNotIn("runas", col)


class TestFrontend(unittest.TestCase):
    def test_o_site_pede_o_ficheiro_e_diz_que_nao_conta(self):
        html = (REPO / "riftvault" / "web" / "index.html").read_text(encoding="utf-8")
        js = (REPO / "riftvault" / "web" / "app.js").read_text(encoding="utf-8")
        self.assertIn('id="runas-vista"', html)
        self.assertIn("api/runas.json", js)
        # O `state.runas` só é lido pela vista: a barra, os níveis e o valor
        # (`renderProgress`) não o conhecem.
        corpo = re.search(r"function renderProgress\(\) \{(.*?)\n\}\n", js, re.S).group(1)
        self.assertNotIn("state.runas", corpo)
        corpo = re.search(r"function render\(\) \{(.*?)\n\}\n", js, re.S).group(1)
        self.assertNotIn("state.runas", corpo)


if __name__ == "__main__":
    unittest.main()

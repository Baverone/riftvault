"""O bloco «Runas — 12 de cada» no fim da Coleção (André, 2026-09-19).

Palavras dele, de manhã: *"depois mete 12 runas de cada (nao contabilizes
para nada, e so para mim para contabilizar ali algumas coisas)"*; à tarde, ao
pedir os `+`/`−`: *"runas nao contabilizam nada, eu e que mexo nisso para
minha referencia, nao entram para decks, nao entram para coleccao, nada, so
para mim"*.

O que se fixa: as runas do catálogo, uma linha cada, alvo 12; o número do
bloco é o CONTADOR DELE (`rune_counter`), semeado uma vez com o que tinha na
mão e nunca mais recalculado; os `+`/`−` mexem só nele, nunca abaixo de 0;
a referência «na coleção» é TUDO o que ele fisicamente tem — a base, a alt
art retirada, a promo escondida, as do CardTrader, esteja onde estiver — com
o número sem as retiradas ao lado; a runa base aparece no master set E aqui,
e a nota di-lo; e, acima de tudo, que ISTO NÃO CONTA PARA NADA: nenhum
módulo de contas o importa, o payload da edição não o traz, mudar o alvo ou
pôr os contadores todos a 99 ou a 0 não mexe em número nenhum, e o `payload`
só escreve na tabela dele (a sementeira).

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
# faltas, A mais, decks, encomendas — e por isso não podem saber que a
# vista existe. Quem a chama é só o servidor, o build e a CLI. (O `config.py`
# guarda o `runas_vista.alvo` como guarda tudo o resto; não faz contas e não
# entra na lista.)
MODULOS_DE_CONTAS = ["metrics", "a_subir", "faltas", "faltas_edicao", "a_mais",
                     "uso_decks", "decks", "locais", "pending", "prices",
                     "collection", "cardmarket", "seguir", "catalog", "db"]


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
        # O contador acabou de ser semeado com o «na coleção», por isso são iguais.
        self.assertEqual(t, {"cards": 2, "contador": 31, "total": 31,
                             "sem_retiradas": 13, "alvo": 24})
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

    def test_a_nota_diz_que_e_dele_que_nao_conta_e_fala_da_sequencia(self):
        con = self.catalogo()
        nota = self.rv.payload(con)["nota"]
        self.assertIn("o número é teu", nota)
        self.assertIn("não contam para nada", nota)
        self.assertIn("sequência do master set", nota)
        con.close()


class TestOContadorEDele(Base):
    """O número do bloco é dele: semeado uma vez com o que tinha na mão, e a
    partir daí só os `+`/`−` lhe mexem — nunca a coleção, nunca abaixo de 0."""

    def contador(self, con):
        return {r["card_key"]: r["qty"] for r in
                con.execute("SELECT card_key, qty FROM rune_counter ORDER BY 1")}

    def test_semeia_uma_vez_com_o_que_tem_na_mao(self):
        con = self.catalogo()
        self.assertEqual(self.contador(con), {})          # antes de alguém ler
        p = self.rv.payload(con)
        # A sementeira é o `total` — todas as versões, incluindo as retiradas
        # e as do CardTrader —, não o `sem_retiradas`.
        self.assertEqual(p["semeadas"], {"calm rune": 30, "fury rune": 1})
        self.assertEqual(self.contador(con), {"calm rune": 30, "fury rune": 1})
        self.assertEqual([x["contador"] for x in p["runas"]], [30, 1])
        # A segunda leitura não semeia nada.
        self.assertEqual(self.rv.payload(con)["semeadas"], {})
        self.assertEqual(self.rv.semear(con), {})
        con.close()

    def test_a_colecao_a_mexer_nao_mexe_no_contador(self):
        """Não é sincronização: depois da sementeira, um `+` na grelha muda a
        referência «na coleção» e deixa o contador onde ele o pôs."""
        from riftvault import collection
        con = self.catalogo()
        self.rv.payload(con)
        collection.adjust(con, "ogn-042-100", 5, source="test")
        collection.adjust(con, "ogn-007-100", -1, source="test")
        calm = self.runa(self.rv.payload(con), "Calm Rune")
        fury = self.runa(self.rv.payload(con), "Fury Rune")
        self.assertEqual((calm["contador"], calm["total"]), (30, 35))
        self.assertEqual((fury["contador"], fury["total"]), (1, 0))
        con.close()

    def test_mais_e_menos_mexem_so_no_contador_e_o_chao_e_zero(self):
        con = self.catalogo()
        r = self.rv.ajustar(con, "fury rune", 3)
        self.assertEqual((r["qty"], r["delta"], r["na_colecao"]), (4, 3, 1))
        self.assertEqual(r["totals"]["contador"], 34)
        r = self.rv.ajustar(con, "Fury Rune", -10)       # o nome também serve
        self.assertEqual((r["qty"], r["delta"]), (0, -4))
        r = self.rv.ajustar(con, "fury rune", -1)        # a 0 fica a 0, sem erro
        self.assertEqual((r["qty"], r["delta"]), (0, 0))
        self.assertEqual(self.contador(con)["fury rune"], 0)
        self.assertGreaterEqual(
            con.execute("SELECT MIN(qty) FROM rune_counter").fetchone()[0], 0)
        # A linha a 0 é dele: uma leitura a seguir não a volta a semear.
        self.assertEqual(self.runa(self.rv.payload(con), "Fury Rune")["contador"], 0)
        con.close()

    def test_o_mais_numa_runa_por_semear_semeia_primeiro(self):
        """O `+` numa runa nova não a faz nascer a 1: nasce com o que ele tem
        e depois soma."""
        con = self.catalogo()
        r = self.rv.ajustar(con, "calm rune", 1)
        self.assertEqual(r["qty"], 31)
        con.close()

    def test_o_que_nao_e_runa_nao_tem_contador(self):
        con = self.catalogo()
        with self.assertRaises(self.rv.RunaDesconhecida):
            self.rv.ajustar(con, "defy", 1)
        with self.assertRaises(self.rv.RunaDesconhecida):
            self.rv.ajustar(con, "", 1)
        self.assertEqual(self.contador(con), {})
        con.close()

    def test_ajustar_escreve_so_na_tabela_dele(self):
        """Nem `copies`, nem `ops`, nem `pending`, nem locais."""
        con = self.catalogo()
        def resto():
            return [con.execute(f"SELECT * FROM {t} ORDER BY 1").fetchall()
                    for t in ("copies", "ops", "pending", "copy_locations", "location_ops")]
        antes = [[tuple(r) for r in t] for t in resto()]
        self.rv.ajustar(con, "calm rune", 7)
        self.rv.ajustar(con, "calm rune", -40)
        self.assertEqual([[tuple(r) for r in t] for t in resto()], antes)
        con.close()

    def test_mexer_nos_contadores_nao_mexe_em_numero_nenhum(self):
        """A prova medida, não a olho: com os contadores semeados, todos a
        99 e todos a 0, tudo o que conta dá o mesmo — grelha, barra, índice,
        níveis, wantlist, valor, Faltas, A mais, decks, Encomendas."""
        from riftvault import decks, pending, prices

        def tudo(con):
            col = self.metrics.set_payload(con, "OGN")
            return json.dumps({
                "grelha": [(g["card_key"], [(p["id"], p["qty"], p["target"], p["block"])
                                            for p in g["printings"]]) for g in col["groups"]],
                "blocos": col["blocks"],
                "progress": col["progress"],
                "index": {k: v for k, v in self.metrics.index_payload(con).items()
                          if k != "generated_at"},
                "niveis": self.metrics.niveis_payload(con),
                "wantlist": {k: self.a_subir.master_faltas(con)[k]
                             for k in ("cards", "copies", "cents")},
                "valor": prices.collection_value(con),
                "faltas": self.faltas_edicao.payload(con)["totals"],
                "a_mais": self.a_mais.payload(con)["totals"],
                "decks": decks.resumo_das_faltas(con),
                "encomendas": pending.grelha(con, "OGN")["groups"],
                "copies": [tuple(r) for r in con.execute(
                    "SELECT printing_id, qty FROM copies ORDER BY 1")],
            }, sort_keys=True, default=str)

        con = self.catalogo()
        self.rv.payload(con)                              # semeia
        semeado = tudo(con)
        for ck in ("calm rune", "fury rune"):
            self.rv.ajustar(con, ck, 99 - self.contador(con)[ck])
        self.assertEqual(set(self.contador(con).values()), {99})
        self.assertEqual(tudo(con), semeado, "pôr os contadores a 99 mexeu em contas")
        for ck in ("calm rune", "fury rune"):
            self.rv.ajustar(con, ck, -99)
        self.assertEqual(set(self.contador(con).values()), {0})
        self.assertEqual(tudo(con), semeado, "pôr os contadores a 0 mexeu em contas")
        con.close()

    def test_a_referencia_na_colecao_e_a_de_sempre(self):
        """Com o contador a 0, o `total`/`sem_retiradas`/`origens` são os
        mesmos — a referência não segue o contador."""
        con = self.catalogo()
        antes = self.runa(self.rv.payload(con), "Calm Rune")
        self.rv.ajustar(con, "calm rune", -100)
        depois = self.runa(self.rv.payload(con), "Calm Rune")
        for k in ("total", "sem_retiradas", "origens"):
            self.assertEqual(depois[k], antes[k])
        self.assertEqual((antes["contador"], depois["contador"]), (30, 0))
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

    def test_a_vista_nao_escreve_na_colecao_nem_leva_euros(self):
        """A única escrita da leitura é a sementeira, na tabela dele."""
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
            self.assertEqual(p["totals"]["contador"], 31)
            self.assertTrue(p["so_para_ver"])
            self.assertTrue(p["editable"])            # no 8770 há `+`/`−`

    def test_a_rota_de_escrita_mexe_so_no_contador(self):
        from riftvault import server
        con = self.catalogo()
        copias = con.execute("SELECT SUM(qty) FROM copies").fetchone()[0]
        con.close()
        app = server.app
        app.testing = True
        with app.test_client() as c:
            r = c.post("/api/runas/ajustar", json={"card_key": "fury rune", "delta": 2})
            self.assertEqual(r.status_code, 200)
            self.assertEqual((r.get_json()["qty"], r.get_json()["totals"]["contador"]), (3, 33))
            r = c.post("/api/runas/ajustar", json={"card_key": "fury rune", "delta": -9})
            self.assertEqual(r.get_json()["qty"], 0)   # o chão
            self.assertEqual(c.post("/api/runas/ajustar",
                                    json={"card_key": "defy", "delta": 1}).status_code, 404)
            self.assertEqual(c.post("/api/runas/ajustar",
                                    json={"card_key": "fury rune", "delta": 0}).status_code, 400)
            self.assertEqual(c.post("/api/runas/ajustar", json={"delta": 1}).status_code, 400)
            self.assertEqual(c.get("/api/runas.json").get_json()["totals"]["contador"], 30)
        con = self.v.connect()
        self.assertEqual(con.execute("SELECT SUM(qty) FROM copies").fetchone()[0], copias)
        con.close()

    def test_o_build_escreve_o_ficheiro_so_de_leitura(self):
        from riftvault import build
        con = self.catalogo()
        con.close()
        out = self.v.root / "site"
        build.build(out, log=lambda *_: None)
        f = out / "api" / "runas.json"
        self.assertTrue(f.exists(), "falta api/runas.json no site")
        p = json.loads(f.read_text(encoding="utf-8"))
        self.assertEqual(p["totals"]["total"], 31)
        self.assertEqual(p["totals"]["contador"], 31)
        self.assertFalse(p["editable"])              # publicado: sem `+`/`−`
        # E o payload da edição publicada continua sem a vista.
        col = json.loads((out / "api" / "set" / "OGN.json").read_text(encoding="utf-8"))
        self.assertNotIn("runas", col)

    def test_a_cli_mexe_so_no_contador(self):
        import contextlib
        import io
        from riftvault import cli
        con = self.catalogo()
        con.close()
        saida = io.StringIO()
        with contextlib.redirect_stdout(saida), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(["runas", "--mais", "Fury Rune", "--n", "4"]), 0)
            self.assertEqual(cli.main(["runas", "--menos", "Calm Rune"]), 0)
            self.assertEqual(cli.main(["runas"]), 0)
        texto = saida.getvalue()
        self.assertIn("Fury Rune: 5 (na coleção: 1)", texto)
        self.assertIn("Calm Rune: 29 (na coleção: 30)", texto)
        self.assertIn("contador: 34 de 24", texto)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(["runas", "--mais", "Defy"]), 1)


class TestFrontend(unittest.TestCase):
    def setUp(self):
        self.html = (REPO / "riftvault" / "web" / "index.html").read_text(encoding="utf-8")
        self.js = (REPO / "riftvault" / "web" / "app.js").read_text(encoding="utf-8")

    def test_o_site_pede_o_ficheiro_e_diz_que_nao_conta(self):
        html, js = self.html, self.js
        self.assertIn('id="runas-vista"', html)
        self.assertIn("api/runas.json", js)
        # O `state.runas` só é lido pela vista: a barra, os níveis e o valor
        # (`renderProgress`) não o conhecem.
        corpo = re.search(r"function renderProgress\(\) \{(.*?)\n\}\n", js, re.S).group(1)
        self.assertNotIn("state.runas", corpo)
        corpo = re.search(r"function render\(\) \{(.*?)\n\}\n", js, re.S).group(1)
        self.assertNotIn("state.runas", corpo)

    def test_o_tile_tem_os_botoes_do_contador_e_a_referencia(self):
        """Os `+`/`−` são `.steppers` — a classe que o `body.readonly`
        esconde no site publicado —, mandam ao `api/runas/ajustar` e a linha
        de baixo é a referência «na coleção»."""
        js = self.js
        tile = re.search(r"function runaTile\(x\) \{(.*?)\n\}\n", js, re.S).group(1)
        self.assertIn('class="steppers runa"', tile)
        self.assertIn('data-runa-delta="-1"', tile)
        self.assertIn('data-runa-delta="1"', tile)
        self.assertIn("const n = runaContador(x)", tile)       # o crachá é o dele
        self.assertIn("${n}/${x.target}", tile)
        self.assertIn("na coleção: <b>${x.total}</b>", tile)
        # Os botões pedem o `editable` do payload (o build escreve `false`; um
        # servidor antigo não o traz — e aí não há botões).
        self.assertIn("state.runas.editable", tile)
        ajustar = re.search(r"async function runaAjustar\(ck, delta\) \{(.*?)\n\}\n", js, re.S).group(1)
        self.assertIn("api/runas/ajustar", ajustar)
        self.assertIn("if (!state.editable", ajustar)
        # E não toca em nada que não seja o bloco: nem `api/adjust`, nem as
        # encomendas, nem marca listas como velhas.
        for proibido in ("api/adjust", "api/encomenda", "wlDesatualizar", "encMarcaVelhos",
                         "state.qty", "state.colecaoVelha"):
            self.assertNotIn(proibido, ajustar)
        css = (REPO / "riftvault" / "web" / "style.css").read_text(encoding="utf-8")
        self.assertIn("body.readonly .steppers { display: none; }", css)


if __name__ == "__main__":
    unittest.main()

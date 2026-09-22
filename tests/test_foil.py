"""A contagem de FOIL e NÃO-FOIL das comuns e incomuns (André, 2026-09-22).

Palavras dele: *"para comuns e incomuns, coloca contagem para Foil e
Non-Foil, para todas as edicoes excepto Proving Grounds"*. «Proving Grounds»
é o OGS.

O que se fixa:
  1. os DADOS: a coluna `copies.qty_foil` com `CHECK (qty_foil <= qty)`, a
     migração idempotente com backup, e o não-foil NUNCA gravado (é sempre
     `qty − qty_foil`); quando o `qty` desce abaixo do `qty_foil`, o foil
     desce com ele e fica linha na `foil_ops`;
  2. o ÂMBITO, em config (`foil.raridades`, `foil.edicoes_fora`): as
     impressões BASE, não sobrenumeradas, dessas raridades, nessas edições —
     e nada mais tem contador;
  3. o FOIL NÃO MEXE EM NADA: uma fotografia de tudo o que é número do site,
     antes e depois de meter e tirar foils;
  4. o contador no tile (payload `foil`/`foil_ok`), travado em 0..qty, sem
     mexer no total;
  5. o RESUMO por edição e em «Todas», e o gémeo em JavaScript;
  6. a CLI, a rota e o site publicado.

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
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
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
                               prices, proprias)
        for m in (locais, metrics, foil, painel, decks, proprias, a_subir,
                  faltas_edicao, a_mais, pending, faltas, prices):
            importlib.reload(m)
        self.config, self.db, self.foil, self.locais = config, db, foil, locais
        self.metrics, self.painel, self.decks = metrics, painel, decks
        self.a_subir, self.faltas_edicao, self.a_mais = a_subir, faltas_edicao, a_mais
        self.pending, self.faltas, self.prices = pending, faltas, prices
        self.collection, self.proprias = collection, proprias
        self.cfg_foil({})

    def cfg_foil(self, extra_foil: dict, extra: dict | None = None):
        """O config temporário com o bloco `foil` de hoje mais o que o teste
        quiser."""
        caminho = self.v.root / "config.json"
        caminho.write_text(json.dumps({
            "foil": {"raridades": ["common", "uncommon"], "edicoes_fora": ["OGS"],
                     **extra_foil},
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
        """Duas edições: a TST (com comuns, incomuns, raras, uma alt art, uma
        sobrenumerada e um token) e a OGS (fora do âmbito).

        Na Coleção: 3 Defy (comum), 2 Scout (incomum), 1 Brutalizer (rara),
        2 da alt art, 1 da sobrenumerada, 2 da comum do OGS.
        """
        con = self.v.connect()
        v = self.v
        v.add_printing(con, "tst-001-100", "TST", 1, "Defy", rarity="common", size=100)
        v.add_printing(con, "tst-001a-100", "TST", 1, "Defy", variant="a", kind="alt_art",
                       rarity="showcase", base_rarity="common", size=100)
        v.add_printing(con, "tst-002-100", "TST", 2, "Scout", rarity="uncommon", size=100)
        v.add_printing(con, "tst-003-100", "TST", 3, "Brutalizer", rarity="rare", size=100)
        v.add_printing(con, "tst-004-100", "TST", 4, "Emperor of the Sands",
                       card_type="Legend", rarity="epic", size=100)
        # Sobrenumerada (a 101 de um set de 100), e de raridade comum: é o caso
        # dos Poros do UNL — fica de fora à mesma, porque não é a base.
        v.add_printing(con, "tst-101-100", "TST", 101, "Lonely Poro", rarity="common",
                       size=100)
        v.add_printing(con, "tst-t01", "TST", 1, "Recruit", variant="t01", kind="token",
                       lane="t", rarity="common", codigo="TST-T01")
        v.add_printing(con, "ogs-001-024", "OGS", 1, "Starter Scout", rarity="common",
                       size=24)
        v.rebuild(con)
        for pid, cents in (("tst-001-100", 11), ("tst-001a-100", 500),
                           ("tst-002-100", 25), ("tst-003-100", 900),
                           ("tst-004-100", 4000), ("tst-101-100", 20000),
                           ("ogs-001-024", 11)):
            con.execute("INSERT INTO catalog.price_latest (printing_id, price_cents) "
                        "VALUES (?,?)", (pid, cents))
        for pid, n in (("tst-001-100", 3), ("tst-002-100", 2), ("tst-003-100", 1),
                       ("tst-001a-100", 2), ("tst-101-100", 1), ("ogs-001-024", 2)):
            self.collection.adjust(con, pid, n, source="test")
        self.addCleanup(con.close)
        return con


# ---------------------------------------------------------------------------


class TestOsDados(Base):
    """1. A coluna, o CHECK, a migração com backup, e o não-foil derivado."""

    def test_a_coluna_existe_com_o_check(self):
        con = self.catalogo()
        cols = {r[1]: r for r in con.execute("PRAGMA table_info(copies)")}
        self.assertIn("qty_foil", cols)
        sql = con.execute("SELECT sql FROM sqlite_master WHERE name='copies'").fetchone()[0]
        self.assertIn("qty_foil <= qty", sql.replace("\n", " "))
        # A base recusa um foil maior que o total, aconteça o que acontecer.
        with self.assertRaises(sqlite3.IntegrityError):
            con.execute("UPDATE copies SET qty_foil = 9 WHERE printing_id = 'tst-001-100'")
        with self.assertRaises(sqlite3.IntegrityError):
            con.execute("UPDATE copies SET qty_foil = -1 WHERE printing_id = 'tst-001-100'")

    def test_o_nao_foil_nunca_se_grava(self):
        """Há UMA coluna, não duas: o normal é sempre `qty − qty_foil`."""
        con = self.catalogo()
        cols = {r[1] for r in con.execute("PRAGMA table_info(copies)")}
        self.assertNotIn("qty_normal", cols)
        self.assertNotIn("qty_nao_foil", cols)
        self.foil.ajustar(con, "tst-001-100", 2, source="test")
        r = con.execute("SELECT qty, qty_foil FROM copies WHERE printing_id='tst-001-100'").fetchone()
        self.assertEqual((r["qty"], r["qty_foil"]), (3, 2))
        item = self.foil.ajustar(con, "tst-001-100", 0, source="test")
        self.assertEqual((item["foil"], item["normal"], item["qty"]), (2, 1, 3))
        self.assertNotIn("qty_normal", " ".join(
            x[0] or "" for x in con.execute("SELECT sql FROM sqlite_master")))

    def test_a_migracao_acrescenta_a_coluna_e_faz_backup(self):
        """Uma base ANTIGA (sem a coluna) ganha-a na primeira ligação, com
        backup antes — e correr outra vez não faz nada."""
        caminho = self.v.data / "antiga.db"
        velha = sqlite3.connect(caminho)
        velha.execute("CREATE TABLE copies (printing_id TEXT PRIMARY KEY, "
                      "qty INTEGER NOT NULL CHECK (qty >= 0), updated_at TEXT NOT NULL)")
        velha.execute("INSERT INTO copies VALUES ('tst-001-100', 3, 'x')")
        velha.commit()
        velha.close()
        os.environ["RIFTVAULT_DB"] = str(caminho)
        importlib.reload(self.config)
        self.config.load.cache_clear()
        importlib.reload(self.db)
        self.addCleanup(lambda: os.environ.__setitem__(
            "RIFTVAULT_DB", str(self.v.data / "vault.db")))

        con = self.db.connect()
        cols = {r[1] for r in con.execute("PRAGMA table_info(copies)")}
        self.assertIn("qty_foil", cols, "a migração acrescentou a coluna")
        # As cópias que lá estavam ficaram como estavam, e a zero de foil.
        r = con.execute("SELECT qty, qty_foil FROM copies").fetchone()
        self.assertEqual((r["qty"], r["qty_foil"]), (3, 0))
        backups = sorted((self.v.data / "backups").glob("vault-antes-do-foil-*.db"))
        self.assertEqual(len(backups), 1, "fez backup antes de mexer no `copies`")
        # O backup é uma base a sério, com as cópias de antes e SEM a coluna.
        b = sqlite3.connect(backups[0])
        self.assertEqual(b.execute("SELECT qty FROM copies").fetchone()[0], 3)
        self.assertNotIn("qty_foil", {x[1] for x in b.execute("PRAGMA table_info(copies)")})
        b.close()
        con.close()
        # Idempotente: a segunda ligação não volta a migrar nem a fazer backup.
        con = self.db.connect()
        self.assertEqual(len(sorted((self.v.data / "backups").glob("*.db"))), 1)
        con.close()

    def test_se_o_total_desce_o_foil_desce_com_ele_e_fica_registo(self):
        con = self.catalogo()
        self.foil.ajustar(con, "tst-001-100", 3, source="test")   # 3 de 3 foil
        self.collection.adjust(con, "tst-001-100", -2, source="test")
        r = con.execute("SELECT qty, qty_foil FROM copies WHERE printing_id='tst-001-100'").fetchone()
        self.assertEqual((r["qty"], r["qty_foil"]), (1, 1), "o foil desceu com o total")
        linhas = [dict(x) for x in con.execute(
            "SELECT * FROM foil_ops WHERE printing_id='tst-001-100' ORDER BY id")]
        self.assertEqual(len(linhas), 2)
        self.assertEqual((linhas[-1]["delta"], linhas[-1]["qty_after"]), (-2, 1))
        self.assertIn("ajuste ao total", linhas[-1]["source"])
        # Até ao fim: sem cópias, sem foil.
        self.collection.adjust(con, "tst-001-100", -1, source="test")
        r = con.execute("SELECT qty, qty_foil FROM copies WHERE printing_id='tst-001-100'").fetchone()
        self.assertEqual((r["qty"], r["qty_foil"]), (0, 0))

    def test_um_menos_que_nao_chega_ao_foil_nao_lhe_toca(self):
        con = self.catalogo()
        self.foil.ajustar(con, "tst-001-100", 1, source="test")
        antes = len(list(con.execute("SELECT 1 FROM foil_ops")))
        self.collection.adjust(con, "tst-001-100", -1, source="test")   # 3 -> 2, foil 1
        r = con.execute("SELECT qty, qty_foil FROM copies WHERE printing_id='tst-001-100'").fetchone()
        self.assertEqual((r["qty"], r["qty_foil"]), (2, 1))
        self.assertEqual(len(list(con.execute("SELECT 1 FROM foil_ops"))), antes,
                         "não houve nada a registar")

    def test_as_proprias_de_um_deck_tambem_cortam_o_foil(self):
        """O outro sítio que baixa o `copies.qty` (`proprias.ajustar`)."""
        self.v.write_deck("azir", "Nome: Azir\n\nLegend:\n1 Emperor of the Sands\n\n"
                                  "MainDeck:\n3 Defy\n")
        con = self.catalogo()
        self.decks.import_all(con, log=lambda *_: None)
        self.proprias.ajustar(con, "azir", "tst-001-100", 2, source="test")   # total 5
        self.foil.ajustar(con, "tst-001-100", 5, source="test")
        self.proprias.ajustar(con, "azir", "tst-001-100", -2, source="test")  # total 3
        r = con.execute("SELECT qty, qty_foil FROM copies WHERE printing_id='tst-001-100'").fetchone()
        self.assertEqual((r["qty"], r["qty_foil"]), (3, 3))


class TestOAmbito(Base):
    """2. Base, não sobrenumerada, raridade da lista, edição fora da lista."""

    def test_so_as_comuns_e_incomuns_base_tem_contador(self):
        con = self.catalogo()
        amb = set(self.foil.ids_do_ambito(con))
        self.assertEqual(amb, {"tst-001-100", "tst-002-100"})
        # e o porquê de cada uma que fica de fora
        fora = {"tst-001a-100": "é alt art", "tst-003-100": "é rara",
                "tst-004-100": "é épica", "tst-101-100": "é sobrenumerada",
                "tst-t01": "é token", "ogs-001-024": "é do OGS"}
        for pid, porque in fora.items():
            self.assertNotIn(pid, amb, porque)

    def test_o_ogs_fica_todo_de_fora(self):
        con = self.catalogo()
        self.assertEqual(self.foil.ids_do_ambito(con, set_id="OGS"), {})
        self.assertIsNone(self.foil.do_set(con, "OGS"))
        self.assertNotIn("OGS", self.foil.resumo(con)["sets"])
        self.assertEqual(self.foil.resumo(con)["sem_edicoes"], ["OGS"])

    def test_a_lista_de_edicoes_manda(self):
        con = self.catalogo()
        self.cfg_foil({"edicoes_fora": []})
        self.assertIn("ogs-001-024", self.foil.ids_do_ambito(con))
        self.cfg_foil({"edicoes_fora": ["OGS", "TST"]})
        self.assertEqual(self.foil.ids_do_ambito(con), {})

    def test_a_lista_de_raridades_manda(self):
        con = self.catalogo()
        self.cfg_foil({"raridades": ["rare"]})
        self.assertEqual(set(self.foil.ids_do_ambito(con)), {"tst-003-100"})
        self.cfg_foil({"raridades": ["common", "uncommon", "rare", "epic"]})
        self.assertEqual(set(self.foil.ids_do_ambito(con)),
                         {"tst-001-100", "tst-002-100", "tst-003-100", "tst-004-100"})

    def test_raridade_desconhecida_rebenta_e_lista_vazia_tambem(self):
        self.cfg_foil({"raridades": ["mitica"]})
        with self.assertRaises(ValueError) as cm:
            self.foil.opcoes()
        self.assertIn("mitica", str(cm.exception))
        self.cfg_foil({"raridades": []})
        with self.assertRaises(ValueError):
            self.foil.opcoes()

    def test_fora_do_ambito_o_ajustar_recusa(self):
        con = self.catalogo()
        for pid in ("tst-001a-100", "tst-003-100", "tst-101-100", "ogs-001-024"):
            with self.assertRaises(self.foil.ForaDoAmbito, msg=pid):
                self.foil.ajustar(con, pid, 1, source="test")
        from riftvault import collection
        with self.assertRaises(collection.UnknownPrinting):
            self.foil.ajustar(con, "nao-existe", 1, source="test")

    def test_o_config_real_diz_comuns_e_incomuns_fora_o_ogs(self):
        cfg = json.loads((REPO / "riftvault_config.json").read_text(encoding="utf-8"))
        self.assertEqual(cfg["foil"]["raridades"], ["common", "uncommon"])
        self.assertEqual(cfg["foil"]["edicoes_fora"], ["OGS"])
        self.assertEqual(self.config.DEFAULTS["foil"],
                         {"raridades": ["common", "uncommon"], "edicoes_fora": ["OGS"]})


class TestNaoMexeEmNadaDoQueJaExiste(Base):
    """3. Marcar cópias como foil não pode alterar UM ÚNICO número."""

    def fotografia(self, con) -> dict:
        """Tudo o que é número do site: níveis, denominador, as três barras,
        o painel, as wantlists, o valor (total, por edição, top), os totais,
        a grelha (qty, alvo, o que vale), o playset jogável, as Faltas (os
        quatro blocos por edição), as Encomendas, o A mais e os decks."""
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
            "top": self.prices.top_value(con),
            "totais": self.collection.totals(con),
            "grelha": [(p["id"], p["qty"], p["qty_total"], p["qty_valor"], p["target"],
                        p["block"]) for g in sp["groups"] for p in g["printings"]],
            "playset": {g["card_key"]: g["playset"] for g in sp["groups"]},
            "owned_by_card": self.metrics.owned_by_card(con),
            "barras": (sp["progress"]["playset"], sp["progress"]["master"],
                       sp["progress"]["value"], sp["progress"]["rarities"]),
            "painel": sp["progress"]["painel"],
            "painel_geral": idx["painel"],
            "blocos": sp["blocks"],
            "sets": idx["sets"],
            "faltas": (fe["totals"], fe["totals_lists"],
                       [(s["set"], b["id"], b["cards"], b["copies"], b["cents"])
                        for s in fe["sets"] for b in s["blocks"]]),
            "encomendas": self.pending.encomendas(con)["totals"],
            "a_mais": {s["set"]: [(x["printing_id"], x["extra"], x["have"])
                                  for x in s["excedente"]["items"]] for s in am["sets"]},
            "decks": self.decks.resumo_das_faltas(con),
            "copies": sorted((r["printing_id"], r["qty"]) for r in
                             con.execute("SELECT printing_id, qty FROM copies")),
        }

    def test_meter_e_tirar_foils_nao_mexe_em_numero_nenhum(self):
        self.v.write_deck("azir", "Nome: Azir\n\nLegend:\n1 Emperor of the Sands\n\n"
                                  "MainDeck:\n3 Defy\n3 Scout\n")
        con = self.catalogo()
        self.decks.import_all(con, log=lambda *_: None)
        antes = self.fotografia(con)

        # Tudo o que dá: 3 de 3 Defy e 2 de 2 Scout.
        self.foil.ajustar(con, "tst-001-100", 3, source="test")
        self.foil.ajustar(con, "tst-002-100", 2, source="test")
        self.assertEqual(self.fotografia(con), antes,
                         "5 cópias marcadas como foil e NADA mexeu")
        # Metade: nem a repartição parcial mexe.
        self.foil.ajustar(con, "tst-001-100", -2, source="test")
        self.assertEqual(self.fotografia(con), antes)
        # E de volta a zero.
        self.foil.ajustar(con, "tst-001-100", -9, source="test")
        self.foil.ajustar(con, "tst-002-100", -9, source="test")
        self.assertEqual(self.fotografia(con), antes, "tirar também não mexe")
        self.assertEqual(self.foil.de(con, "tst-001-100"), 0)

    def test_o_ajustar_nao_escreve_no_copies_nem_no_ops(self):
        con = self.catalogo()
        qty = sorted((r["printing_id"], r["qty"]) for r in
                     con.execute("SELECT printing_id, qty FROM copies"))
        ops = con.execute("SELECT COUNT(*) AS n FROM ops").fetchone()["n"]
        locs = con.execute("SELECT COUNT(*) AS n FROM copy_locations").fetchone()["n"]
        pend = con.execute("SELECT COUNT(*) AS n FROM pending").fetchone()["n"]
        self.foil.ajustar(con, "tst-001-100", 2, source="test")
        self.assertEqual(sorted((r["printing_id"], r["qty"]) for r in
                                con.execute("SELECT printing_id, qty FROM copies")), qty)
        self.assertEqual(con.execute("SELECT COUNT(*) AS n FROM ops").fetchone()["n"], ops)
        self.assertEqual(con.execute("SELECT COUNT(*) AS n FROM copy_locations").fetchone()["n"], locs)
        self.assertEqual(con.execute("SELECT COUNT(*) AS n FROM pending").fetchone()["n"], pend)

    def test_ler_o_resumo_nao_escreve(self):
        con = self.catalogo()
        antes = con.execute("SELECT COUNT(*) AS n FROM foil_ops").fetchone()["n"]
        self.foil.resumo(con)
        self.foil.do_set(con, "TST")
        self.metrics.set_payload(con, "TST")
        self.assertEqual(con.execute("SELECT COUNT(*) AS n FROM foil_ops").fetchone()["n"], antes)

    def test_nenhum_modulo_de_contas_importa_o_foil_para_contar(self):
        """Só o `collection`/`proprias` (para o corte) e a apresentação. Se um
        módulo de contas passar a lê-lo, é sinal de que o foil entrou numa
        conta — e não pode."""
        proibidos = ["a_subir", "faltas", "faltas_edicao", "a_mais", "uso_decks",
                     "decks", "locais", "pending", "prices", "painel", "runas_vista",
                     "cardmarket", "seguir", "catalog"]
        for nome in proibidos:
            fonte = (REPO / "riftvault" / f"{nome}.py").read_text(encoding="utf-8")
            self.assertNotIn("import foil", fonte, nome)
            self.assertNotIn("from .foil", fonte, nome)
            self.assertNotIn("qty_foil", fonte, nome)


class TestOContadorNoTile(Base):
    """4. O payload do tile, e os limites 0..qty."""

    def test_o_payload_diz_quem_tem_contador_e_quantas_sao_foil(self):
        con = self.catalogo()
        self.foil.ajustar(con, "tst-001-100", 2, source="test")
        sp = self.metrics.set_payload(con, "TST")
        tiles = {p["id"]: p for g in sp["groups"] for p in g["printings"]}
        self.assertTrue(tiles["tst-001-100"]["foil_ok"])
        self.assertEqual(tiles["tst-001-100"]["foil"], 2)
        self.assertEqual(tiles["tst-001-100"]["qty_total"], 3, "o tecto é o total físico")
        self.assertTrue(tiles["tst-002-100"]["foil_ok"])
        self.assertEqual(tiles["tst-002-100"]["foil"], 0)
        for pid in ("tst-001a-100", "tst-003-100", "tst-004-100", "tst-101-100"):
            self.assertFalse(tiles[pid]["foil_ok"], pid)
        ogs = self.metrics.set_payload(con, "OGS")
        self.assertFalse(next(p for g in ogs["groups"] for p in g["printings"])["foil_ok"])

    def test_trava_em_zero_e_no_total(self):
        con = self.catalogo()
        r = self.foil.ajustar(con, "tst-001-100", 99, source="test")
        self.assertEqual((r["foil"], r["normal"], r["applied"]), (3, 0, 3))
        r = self.foil.ajustar(con, "tst-001-100", 1, source="test")
        self.assertEqual((r["foil"], r["applied"]), (3, 0), "já estão todas")
        r = self.foil.ajustar(con, "tst-001-100", -99, source="test")
        self.assertEqual((r["foil"], r["normal"], r["applied"]), (0, 3, -3))
        r = self.foil.ajustar(con, "tst-001-100", -1, source="test")
        self.assertEqual((r["foil"], r["applied"]), (0, 0))

    def test_uma_impressao_sem_copias_nao_marca_nada(self):
        con = self.catalogo()
        r = self.foil.ajustar(con, "tst-002-100", 1, source="test")
        self.assertEqual(r["foil"], 1)
        self.collection.adjust(con, "tst-002-100", -2, source="test")
        r = self.foil.ajustar(con, "tst-002-100", 5, source="test")
        self.assertEqual((r["qty"], r["foil"], r["applied"]), (0, 0, 0))

    def test_o_tile_conta_as_copias_de_todos_os_locais(self):
        """Uma cópia sleevada num deck não deixa de ser foil."""
        self.v.write_deck("azir", "Nome: Azir\n\nLegend:\n1 Emperor of the Sands\n\n"
                                  "MainDeck:\n3 Defy\n")
        con = self.catalogo()
        self.decks.import_all(con, log=lambda *_: None)
        self.locais.mover(con, "tst-001-100", 2, "colecao", "deck:azir", source="test")
        r = self.foil.ajustar(con, "tst-001-100", 3, source="test")
        self.assertEqual((r["qty"], r["foil"]), (3, 3))
        sp = self.metrics.set_payload(con, "TST")
        tile = next(p for g in sp["groups"] for p in g["printings"]
                    if p["id"] == "tst-001-100")
        self.assertEqual((tile["qty"], tile["qty_total"], tile["foil"]), (1, 3, 3),
                         "a grelha mostra 1 na Coleção, mas as 3 cópias são foil")


class TestOResumo(Base):
    """5. O resumo por edição e em «Todas», e o gémeo em JavaScript."""

    def test_os_numeros_de_arranque(self):
        con = self.catalogo()
        r = self.foil.resumo(con)
        tst = r["sets"]["TST"]
        # 2 impressões (Defy comum ×3, Scout incomum ×2), 5 cópias, 0 foil.
        self.assertEqual((tst["printings"], tst["copies"], tst["foil"], tst["normal"]),
                         (2, 5, 0, 5))
        self.assertEqual(tst["foil_printings"], 0)
        self.assertEqual([(x["id"], x["printings"], x["copies"], x["normal"], x["foil"])
                          for x in tst["rarity"]],
                         [("common", 1, 3, 3, 0), ("uncommon", 1, 2, 2, 0)])
        self.assertEqual(r["sets"][self.foil.TODAS], tst, "só há uma edição no âmbito")
        self.assertEqual(r["raridades"], ["common", "uncommon"])
        self.assertEqual(r["labels"], {"common": "Comuns", "uncommon": "Incomuns"})

    def test_o_resumo_anda_com_as_marcacoes(self):
        con = self.catalogo()
        self.foil.ajustar(con, "tst-001-100", 2, source="test")
        self.foil.ajustar(con, "tst-002-100", 2, source="test")
        tst = self.foil.resumo(con)["sets"]["TST"]
        self.assertEqual((tst["copies"], tst["normal"], tst["foil"]), (5, 1, 4))
        self.assertEqual(tst["foil_printings"], 2)
        com = next(x for x in tst["rarity"] if x["id"] == "common")
        inc = next(x for x in tst["rarity"] if x["id"] == "uncommon")
        self.assertEqual((com["normal"], com["foil"]), (1, 2))
        self.assertEqual((inc["normal"], inc["foil"]), (0, 2))
        # O normal + o foil é sempre as cópias, por construção.
        self.assertEqual(com["normal"] + com["foil"], com["copies"])
        self.assertEqual(tst["normal"] + tst["foil"], tst["copies"])

    def test_as_raridades_somam_o_total_e_as_edicoes_somam_o_todas(self):
        con = self.catalogo()
        self.cfg_foil({"edicoes_fora": []})       # com o OGS dentro, duas edições
        self.foil.ajustar(con, "tst-001-100", 1, source="test")
        self.foil.ajustar(con, "ogs-001-024", 2, source="test")
        r = self.foil.resumo(con)
        todas = r["sets"][self.foil.TODAS]
        for campo in ("printings", "copies", "foil", "normal", "foil_printings"):
            self.assertEqual(todas[campo],
                             r["sets"]["TST"][campo] + r["sets"]["OGS"][campo], campo)
            self.assertEqual(todas[campo], sum(x[campo] for x in todas["rarity"]), campo)
        self.assertEqual((todas["copies"], todas["foil"], todas["normal"]), (7, 3, 4))

    def test_o_resumo_chega_a_edicao_e_ao_index(self):
        con = self.catalogo()
        self.foil.ajustar(con, "tst-001-100", 1, source="test")
        sp = self.metrics.set_payload(con, "TST")["progress"]["foil"]
        self.assertEqual((sp["copies"], sp["foil"]), (5, 1))
        self.assertEqual(sp["raridades"], ["common", "uncommon"])
        self.assertIsNone(self.metrics.set_payload(con, "OGS")["progress"]["foil"])
        idx = self.metrics.index_payload(con)["foil"]
        self.assertEqual(idx["sets"]["TST"]["foil"], 1)
        self.assertEqual(idx["sets"][self.foil.TODAS]["foil"], 1)
        self.assertEqual(idx["sem_edicoes"], ["OGS"])

    def test_o_resumo_nao_leva_euros(self):
        con = self.catalogo()
        texto = json.dumps(self.foil.resumo(con))
        for palavra in ("cents", "price", "eur", "€"):
            self.assertNotIn(palavra, texto.lower())

    def test_o_gemeo_em_javascript_da_o_mesmo(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("sem node")
        js = APP_JS.read_text(encoding="utf-8")
        m = re.search(r"/\* @foil-puro:inicio.*?\*/(.*?)/\* @foil-puro:fim \*/", js, re.S)
        self.assertIsNotNone(m, "o troço puro do foil tem de estar marcado no app.js")
        itens = [("common", 3, 0), ("common", 4, 4), ("uncommon", 2, 1),
                 ("uncommon", 0, 0), ("rare", 5, 2), ("mitica", 1, 1),
                 ("common", 7, 3)]
        esperado = self.foil.contar(itens)
        harness = m.group(1) + """
const e = JSON.parse(require('node:fs').readFileSync(0, 'utf8'));
const itens = e.itens.map(([rarity, copies, foil]) => ({rarity, copies, foil}));
process.stdout.write(JSON.stringify(foilContar(itens, e.labels)));
"""
        r = subprocess.run([node, "-e", harness],
                           input=json.dumps({"itens": itens,
                                             "labels": self.foil.RARIDADE_LABEL}),
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), esperado)


class TestRotaBuildCLI(Base):
    """6. A rota, o site publicado, a CLI e o `app.js`."""

    def test_a_rota_ajusta_e_recusa_o_que_esta_fora(self):
        con = self.catalogo()
        con.close()
        from riftvault import server
        importlib.reload(server)
        server.app.testing = True
        with server.app.test_client() as c:
            r = c.post("/api/foil/ajustar", json={"printing_id": "tst-001-100", "delta": 2})
            self.assertEqual(r.status_code, 200)
            self.assertEqual((r.get_json()["foil"], r.get_json()["normal"]), (2, 1))
            r = c.post("/api/foil/ajustar", json={"printing_id": "tst-001-100", "delta": -99})
            self.assertEqual(r.get_json()["foil"], 0, "trava em zero sem erro")
            r = c.post("/api/foil/ajustar", json={"printing_id": "tst-003-100", "delta": 1})
            self.assertEqual(r.status_code, 400, "a rara está fora do âmbito")
            r = c.post("/api/foil/ajustar", json={"printing_id": "ogs-001-024", "delta": 1})
            self.assertEqual(r.status_code, 400, "o OGS está fora")
            r = c.post("/api/foil/ajustar", json={"printing_id": "nao-existe", "delta": 1})
            self.assertEqual(r.status_code, 404)
            r = c.post("/api/foil/ajustar", json={"printing_id": "tst-001-100", "delta": 0})
            self.assertEqual(r.status_code, 400)
            r = c.post("/api/foil/ajustar", json={"delta": 1})
            self.assertEqual(r.status_code, 400)
            # O `/api/adjust` diz o foil de volta, para o tile o poder cortar.
            c.post("/api/foil/ajustar", json={"printing_id": "tst-001-100", "delta": 3})
            res = c.post("/api/adjust", json={"printing_id": "tst-001-100", "delta": -2}).get_json()
            self.assertEqual((res["qty"], res["foil"]), (1, 1))
            g = c.get("/api/set/TST.json").get_json()
            tile = next(p for grp in g["groups"] for p in grp["printings"]
                        if p["id"] == "tst-001-100")
            self.assertEqual((tile["foil"], tile["foil_ok"]), (1, True))
            self.assertEqual(c.get("/api/index.json").get_json()["foil"]["sem_edicoes"],
                             ["OGS"])

    def test_o_site_publicado_leva_o_resumo_e_nao_leva_controlos(self):
        con = self.catalogo()
        self.foil.ajustar(con, "tst-001-100", 1, source="test")
        con.close()
        from riftvault import build
        importlib.reload(build)
        saida = self.v.root / "site"
        build.build(saida, log=lambda *_: None)
        sp = json.loads((saida / "api" / "set" / "TST.json").read_text(encoding="utf-8"))
        self.assertFalse(sp["editable"])
        self.assertEqual(sp["progress"]["foil"]["foil"], 1)
        tile = next(p for g in sp["groups"] for p in g["printings"]
                    if p["id"] == "tst-001-100")
        self.assertEqual((tile["foil"], tile["foil_ok"]), (1, True))
        idx = json.loads((saida / "api" / "index.json").read_text(encoding="utf-8"))
        self.assertEqual(idx["foil"]["sets"][self.foil.TODAS]["foil"], 1)
        css = (saida / "style.css").read_text(encoding="utf-8")
        self.assertIn("body.readonly .steppers { display: none; }", css)

    def test_a_cli_mostra_o_resumo_e_mexe(self):
        con = self.catalogo()
        con.close()
        from riftvault import cli
        importlib.reload(cli)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(cli.main(["foil"]), 0)
        self.assertIn("Comuns", out.getvalue())
        self.assertIn("normais", out.getvalue())
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(["foil", "TST-001", "--mais", "2"]), 0)
        self.assertIn("1 normais · 2 foil", out.getvalue())
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(["foil", "TST-001"]), 0)
        self.assertIn("1 normais · 2 foil", out.getvalue())
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(["foil", "TST-001", "--menos", "2"]), 0)
        self.assertIn("3 normais · 0 foil", out.getvalue())
        # Fora do âmbito e sem REF: erro, com a razão.
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            self.assertEqual(cli.main(["foil", "TST-003", "--mais"]), 1)
        self.assertIn("contagem de foil", err.getvalue())
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            self.assertEqual(cli.main(["foil", "--mais", "1"]), 1)
        self.assertIn("precisam da impressão", err.getvalue())

    def test_o_app_js_e_o_html_desenham_o_contador_e_o_resumo(self):
        js = APP_JS.read_text(encoding="utf-8")
        self.assertIn("function foilLinha", js)
        self.assertIn("function foilAjustar", js)
        self.assertIn("function renderFoilResumo", js)
        self.assertIn("api/foil/ajustar", js)
        self.assertIn("data-foil", js)
        # O contador do foil nunca manda um `+` de cópias.
        troço = js[js.index("async function foilAjustar"):js.index("function refreshFoil")]
        self.assertNotIn("api/adjust", troço)
        html = (REPO / "riftvault" / "web" / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="foil-resumo"', html)
        css = (REPO / "riftvault" / "web" / "style.css").read_text(encoding="utf-8")
        self.assertIn(".foil-linha", css)
        self.assertIn(".steppers.foil", css)


if __name__ == "__main__":
    unittest.main()

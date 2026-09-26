"""A contagem de FOIL e NÃO-FOIL das comuns e incomuns (André, 2026-09-22),
com o FOIL A SOMAR-SE às normais (André, 2026-09-26).

Palavras dele: *"para comuns e incomuns, coloca contagem para Foil e
Non-Foil, para todas as edicoes excepto Proving Grounds"* («Proving Grounds» é
o OGS) e, a corrigir-nos, *"as foils quando eu marco é que tenho TAMBÉM foil,
ou seja, normal + foil e não apenas 1, no caso daria 3+3"*.

O que se fixa:
  1. os DADOS: a coluna `copies.qty_foil` **sem** o tecto do `qty` (só
     `>= 0` e o limite de sanidade), as duas migrações idempotentes com
     backup, e o total NUNCA gravado (é sempre `qty + qty_foil`);
  2. AS DUAS CONTAGENS SÃO INDEPENDENTES: o `+` do foil não mexe nas normais
     e o `−` da grelha (ou das próprias) não mexe nas foils; `qty = 0` com
     `qty_foil > 0` é estado legítimo;
  3. o ÂMBITO, em config (`foil.raridades`, `foil.edicoes_fora`): as
     impressões BASE, não sobrenumeradas, dessas raridades, nessas edições —
     e nada mais tem contador;
  4. o FOIL NÃO MEXE EM NADA: uma fotografia de tudo o que é número do site,
     antes e depois de meter e tirar foils;
  5. as DUAS PERGUNTAS DELE em config (`foil.conta_para_coleccao`,
     `foil.conta_para_valor`), as duas a `false` — e o que mudaria com `true`;
  6. o contador no tile (payload `foil`/`foil_ok`), travado em 0 e no limite;
  7. o RESUMO por edição e em «Todas», e o gémeo em JavaScript;
  8. a CLI, a rota e o site publicado.

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
    """1. A coluna, o CHECK sem o tecto do `qty`, e as duas migrações."""

    def test_a_coluna_existe_e_o_check_ja_nao_tem_o_tecto_do_qty(self):
        con = self.catalogo()
        cols = {r[1]: r for r in con.execute("PRAGMA table_info(copies)")}
        self.assertIn("qty_foil", cols)
        sql = con.execute("SELECT sql FROM sqlite_master WHERE name='copies'").fetchone()[0]
        sql = sql.replace("\n", " ")
        self.assertNotIn("qty_foil <= qty", sql,
                         "o tecto do modelo antigo (o foil como fatia do total) saiu")
        self.assertIn("qty_foil >= 0", sql)
        # Mais foils do que normais é estado legítimo desde 2026-09-26.
        con.execute("UPDATE copies SET qty_foil = 9 WHERE printing_id = 'tst-001-100'")
        r = con.execute("SELECT qty, qty_foil FROM copies "
                        "WHERE printing_id='tst-001-100'").fetchone()
        self.assertEqual((r["qty"], r["qty_foil"]), (3, 9))
        # Negativo continua a ser recusado pela base.
        with self.assertRaises(sqlite3.IntegrityError):
            con.execute("UPDATE copies SET qty_foil = -1 WHERE printing_id = 'tst-001-100'")
        # E o tecto de sanidade também.
        with self.assertRaises(sqlite3.IntegrityError):
            con.execute("UPDATE copies SET qty_foil = ? WHERE printing_id = 'tst-001-100'",
                        (self.foil.LIMITE + 1,))

    def test_o_total_nunca_se_grava_e_e_a_soma(self):
        """Há DUAS colunas — as normais e as foils — e o total é a soma."""
        con = self.catalogo()
        cols = {r[1] for r in con.execute("PRAGMA table_info(copies)")}
        self.assertNotIn("qty_normal", cols)
        self.assertNotIn("qty_total", cols)
        self.foil.ajustar(con, "tst-001-100", 2, source="test")
        r = con.execute("SELECT qty, qty_foil FROM copies "
                        "WHERE printing_id='tst-001-100'").fetchone()
        self.assertEqual((r["qty"], r["qty_foil"]), (3, 2), "as normais não mexeram")
        item = self.foil.ajustar(con, "tst-001-100", 0, source="test")
        self.assertEqual((item["normal"], item["foil"], item["total"]), (3, 2, 5))
        # O `qty` ambíguo saiu do resultado: era o nome que estava por baixo do
        # erro do modelo antigo.
        self.assertNotIn("qty", item)
        self.assertNotIn("qty_total", " ".join(
            x[0] or "" for x in con.execute("SELECT sql FROM sqlite_master")))

    def test_tres_normais_mais_tres_foil_dao_seis(self):
        """A frase dele, à letra: *"no caso daria 3+3"*."""
        con = self.catalogo()
        r = self.foil.ajustar(con, "tst-001-100", 3, source="test")
        self.assertEqual((r["normal"], r["foil"], r["total"]), (3, 3, 6))
        tst = self.foil.resumo(con)["sets"]["TST"]
        com = next(x for x in tst["rarity"] if x["id"] == "common")
        self.assertEqual((com["normal"], com["foil"], com["copies"]), (3, 3, 6))

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
        # A coluna nasce JÁ sem o tecto do `qty`: a base que migra de uma sem
        # coluna nenhuma não passa pelo modelo errado.
        sql = con.execute("SELECT sql FROM sqlite_master "
                          "WHERE name='copies'").fetchone()[0].replace("\n", " ")
        self.assertNotIn("qty_foil <= qty", sql)
        con.close()
        # Idempotente: a segunda ligação não volta a migrar nem a fazer backup.
        con = self.db.connect()
        self.assertEqual(len(sorted((self.v.data / "backups").glob("*.db"))), 1)
        con.close()

    def test_a_migracao_de_2026_09_26_tira_o_tecto_e_nao_mexe_nos_numeros(self):
        """Uma base com o CHECK ANTIGO (`qty_foil <= qty`) perde-o na primeira
        ligação, com backup — e os números ficam TODOS como estavam.

        É o caso do `data/` real: os `qty`/`qty_foil` guardados já eram os
        certos para o modelo novo (as normais que ele tinha e as foils que
        marcou por cima), por isso a migração é só de schema.
        """
        caminho = self.v.data / "com-tecto.db"
        velha = sqlite3.connect(caminho)
        velha.execute("CREATE TABLE copies (printing_id TEXT PRIMARY KEY, "
                      "qty INTEGER NOT NULL CHECK (qty >= 0), "
                      "updated_at TEXT NOT NULL, "
                      "qty_foil INTEGER NOT NULL DEFAULT 0 "
                      "  CHECK (qty_foil >= 0 AND qty_foil <= qty))")
        # Os 15 casos do `data/` real, em miniatura: 3 normais e 3 foil.
        velha.execute("INSERT INTO copies VALUES ('tst-001-100', 3, 'x', 3)")
        velha.execute("INSERT INTO copies VALUES ('tst-002-100', 2, 'y', 1)")
        velha.commit()
        velha.close()
        os.environ["RIFTVAULT_DB"] = str(caminho)
        importlib.reload(self.config)
        self.config.load.cache_clear()
        importlib.reload(self.db)
        self.addCleanup(lambda: os.environ.__setitem__(
            "RIFTVAULT_DB", str(self.v.data / "vault.db")))

        con = self.db.connect()
        sql = con.execute("SELECT sql FROM sqlite_master "
                          "WHERE name='copies'").fetchone()[0].replace("\n", " ")
        self.assertNotIn("qty_foil <= qty", sql, "o tecto saiu")
        self.assertIn("qty_foil >= 0", sql)
        # NENHUM NÚMERO MEXEU — é o que faz esta migração não ter risco.
        self.assertEqual(
            sorted((r["printing_id"], r["qty"], r["qty_foil"]) for r in
                   con.execute("SELECT printing_id, qty, qty_foil FROM copies")),
            [("tst-001-100", 3, 3), ("tst-002-100", 2, 1)])
        # A PK sobreviveu ao RENAME (era o risco de refazer a tabela).
        with self.assertRaises(sqlite3.IntegrityError):
            con.execute("INSERT INTO copies VALUES ('tst-001-100', 1, 'z', 0)")
        # E agora o foil pode passar as normais.
        con.execute("UPDATE copies SET qty_foil = 9 WHERE printing_id='tst-002-100'")
        backups = sorted((self.v.data / "backups").glob("vault-antes-do-foil-somar-*.db"))
        self.assertEqual(len(backups), 1, "fez backup antes de refazer o `copies`")
        b = sqlite3.connect(backups[0])
        self.assertIn("qty_foil <= qty",
                      b.execute("SELECT sql FROM sqlite_master WHERE name='copies'")
                      .fetchone()[0].replace("\n", " "), "o backup é de ANTES")
        self.assertEqual(b.execute("SELECT SUM(qty_foil) FROM copies").fetchone()[0], 4)
        b.close()
        con.close()
        # Idempotente: a segunda ligação já não encontra o CHECK antigo.
        con = self.db.connect()
        self.assertEqual(len(sorted((self.v.data / "backups").glob("*.db"))), 1,
                         "não volta a migrar nem a fazer backup")
        con.close()


class TestAsDuasContagensSaoIndependentes(Base):
    """2. O `+` do foil não mexe nas normais, e o `−` das normais não mexe nas
    foils (André, 2026-09-26). Era exactamente o contrário até essa data."""

    def test_um_menos_na_grelha_nao_leva_o_foil_com_ele(self):
        con = self.catalogo()
        self.foil.ajustar(con, "tst-001-100", 3, source="test")   # 3 normais + 3 foil
        antes = len(list(con.execute("SELECT 1 FROM foil_ops")))
        self.collection.adjust(con, "tst-001-100", -2, source="test")
        r = con.execute("SELECT qty, qty_foil FROM copies "
                        "WHERE printing_id='tst-001-100'").fetchone()
        self.assertEqual((r["qty"], r["qty_foil"]), (1, 3),
                         "tirou 2 NORMAIS; as 3 foils ficaram")
        self.assertEqual(len(list(con.execute("SELECT 1 FROM foil_ops"))), antes,
                         "e não houve nada a registar na foil_ops")
        # Até ao fim: sem normais, as foils ficam.
        self.collection.adjust(con, "tst-001-100", -9, source="test")
        r = con.execute("SELECT qty, qty_foil FROM copies "
                        "WHERE printing_id='tst-001-100'").fetchone()
        self.assertEqual((r["qty"], r["qty_foil"]), (0, 3))

    def test_zero_normais_com_foil_e_estado_legitimo(self):
        """Uma carta que ele SÓ tenha em foil — impossível até 2026-09-26."""
        con = self.catalogo()
        self.collection.adjust(con, "tst-002-100", -9, source="test")   # 0 normais
        r = self.foil.ajustar(con, "tst-002-100", 2, source="test")
        self.assertEqual((r["normal"], r["foil"], r["total"]), (0, 2, 2))
        linha = con.execute("SELECT qty, qty_foil FROM copies "
                            "WHERE printing_id='tst-002-100'").fetchone()
        self.assertEqual((linha["qty"], linha["qty_foil"]), (0, 2))
        # A Coleção continua a contar as NORMAIS: para ela, ele não a tem.
        sp = self.metrics.set_payload(con, "TST")
        tile = next(p for g in sp["groups"] for p in g["printings"]
                    if p["id"] == "tst-002-100")
        self.assertEqual((tile["qty"], tile["qty_total"], tile["foil"]), (0, 0, 2))
        self.assertTrue(tile["foil_ok"], "e continua a ter contador")
        # E o resumo di-lo.
        tst = self.foil.resumo(con)["sets"]["TST"]
        inc = next(x for x in tst["rarity"] if x["id"] == "uncommon")
        self.assertEqual((inc["normal"], inc["foil"], inc["copies"]), (0, 2, 2))

    def test_uma_impressao_que_nem_esta_no_copies_pode_levar_foil(self):
        """Uma carta que ele nunca meteu na Coleção: a linha nasce com
        `qty = 0` e a foil entra na mesma."""
        con = self.catalogo()
        con.execute("DELETE FROM copies WHERE printing_id='tst-001-100'")
        self.assertIsNone(con.execute("SELECT 1 FROM copies WHERE "
                                      "printing_id='tst-001-100'").fetchone())
        r = self.foil.ajustar(con, "tst-001-100", 1, source="test")
        self.assertEqual((r["normal"], r["foil"], r["total"]), (0, 1, 1))
        linha = con.execute("SELECT qty, qty_foil FROM copies "
                            "WHERE printing_id='tst-001-100'").fetchone()
        self.assertEqual((linha["qty"], linha["qty_foil"]), (0, 1))

    def test_as_proprias_de_um_deck_tambem_nao_mexem_no_foil(self):
        """O outro sítio que baixa o `copies.qty` (`proprias.ajustar`)."""
        self.v.write_deck("azir", "Nome: Azir\n\nLegend:\n1 Emperor of the Sands\n\n"
                                  "MainDeck:\n3 Defy\n")
        con = self.catalogo()
        self.decks.import_all(con, log=lambda *_: None)
        self.proprias.ajustar(con, "azir", "tst-001-100", 2, source="test")   # 5 normais
        self.foil.ajustar(con, "tst-001-100", 5, source="test")
        self.proprias.ajustar(con, "azir", "tst-001-100", -2, source="test")  # 3 normais
        r = con.execute("SELECT qty, qty_foil FROM copies "
                        "WHERE printing_id='tst-001-100'").fetchone()
        self.assertEqual((r["qty"], r["qty_foil"]), (3, 5), "as 5 foils ficaram")

    def test_o_foil_nao_escreve_no_ops_nem_nos_locais(self):
        con = self.catalogo()
        ops = con.execute("SELECT COUNT(*) AS n FROM ops").fetchone()["n"]
        locs = con.execute("SELECT COUNT(*) AS n FROM copy_locations").fetchone()["n"]
        self.foil.ajustar(con, "tst-001-100", 9, source="test")
        self.assertEqual(con.execute("SELECT COUNT(*) AS n FROM ops").fetchone()["n"], ops)
        self.assertEqual(con.execute("SELECT COUNT(*) AS n FROM copy_locations")
                         .fetchone()["n"], locs,
                         "os locais contam as normais — onde está cada foil "
                         "é pergunta que ele nunca fez")


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
        """O âmbito (22/09) e as TRÊS chaves de hoje.

        As duas primeiras nasceram a `false` a 2026-09-26 de manhã e ele
        respondeu-as na mesma tarde — *"contam para o valor sim, e contabilizas
        tambem como parte do master set"* —, com a terceira a impedir que os
        foils apareçam como excedente no «A mais».
        """
        cfg = json.loads((REPO / "riftvault_config.json").read_text(encoding="utf-8"))
        self.assertEqual(cfg["foil"]["raridades"], ["common", "uncommon"])
        self.assertEqual(cfg["foil"]["edicoes_fora"], ["OGS"])
        self.assertIs(cfg["foil"]["conta_para_coleccao"], True)
        self.assertIs(cfg["foil"]["conta_para_valor"], True)
        self.assertIs(cfg["foil"]["entra_no_a_mais"], False)
        self.assertEqual(self.config.DEFAULTS["foil"],
                         {"raridades": ["common", "uncommon"], "edicoes_fora": ["OGS"],
                          "conta_para_coleccao": True, "conta_para_valor": True,
                          "entra_no_a_mais": False})


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

        self.foil.ajustar(con, "tst-001-100", 3, source="test")
        self.foil.ajustar(con, "tst-002-100", 2, source="test")
        self.assertEqual(self.fotografia(con), antes,
                         "5 foils acrescentadas e NADA mexeu")
        # MAIS foils do que normais — impossível até 2026-09-26, e continua a
        # não mexer em nada.
        self.foil.ajustar(con, "tst-001-100", 20, source="test")
        self.assertEqual(self.fotografia(con), antes,
                         "23 foils com 3 normais e NADA mexeu")
        self.foil.ajustar(con, "tst-001-100", -2, source="test")
        self.assertEqual(self.fotografia(con), antes)
        # E de volta a zero.
        self.foil.ajustar(con, "tst-001-100", -999, source="test")
        self.foil.ajustar(con, "tst-002-100", -999, source="test")
        self.assertEqual(self.fotografia(con), antes, "tirar também não mexe")
        self.assertEqual(self.foil.de(con, "tst-001-100"), 0)

    def test_uma_carta_so_em_foil_nao_mexe_em_numero_nenhum(self):
        """O estado novo (0 normais, foil > 0) também tem de ser invisível às
        contas com os dois botões dele desligados."""
        con = self.catalogo()
        antes = self.fotografia(con)
        self.collection.adjust(con, "tst-001-100", -3, source="test")   # 0 normais
        meio = self.fotografia(con)
        self.assertNotEqual(meio, antes, "tirar as NORMAIS mexe, claro")
        self.foil.ajustar(con, "tst-001-100", 5, source="test")
        self.assertEqual(self.fotografia(con), meio,
                         "meter 5 foils numa carta sem normais não mexe em nada")
        self.collection.adjust(con, "tst-001-100", 3, source="test")
        self.assertEqual(self.fotografia(con), antes,
                         "e repor as normais devolve tudo ao sítio, com as foils lá")
        self.assertEqual(self.foil.de(con, "tst-001-100"), 5)

    def test_a_fotografia_nao_e_de_zeros(self):
        """Se a fotografia medisse tudo a zero, os testes acima passavam sem
        provar nada."""
        con = self.catalogo()
        f = self.fotografia(con)
        self.assertGreater(f["valor"], 0)
        self.assertGreater(f["valor_copias"], 0)
        self.assertTrue(any(n for _, n in f["copies"]))
        self.assertTrue(any(d for _, d, _, _, _ in f["niveis"]))
        self.assertGreater(f["wantlist"]["copies"], 0)

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

    def test_nenhum_modulo_de_contas_importa_o_foil(self):
        """Nenhum módulo de contas conhece o `foil`. Os dois funis dos botões
        dele (`locais`, `prices`) leem a chave do config directamente, de
        propósito: é o que mantém esta fronteira de pé."""
        proibidos = ["a_subir", "faltas", "faltas_edicao", "a_mais", "uso_decks",
                     "decks", "locais", "pending", "prices", "painel", "runas_vista",
                     "cardmarket", "seguir", "catalog"]
        for nome in proibidos:
            fonte = (REPO / "riftvault" / f"{nome}.py").read_text(encoding="utf-8")
            self.assertNotIn("import foil", fonte, nome)
            self.assertNotIn("from .foil", fonte, nome)

    def test_so_os_dois_funis_dos_botoes_dele_mencionam_o_qty_foil(self):
        """O `qty_foil` só pode aparecer onde os botões o mandam entrar — e
        nesses, sempre atrás da chave de config. Se aparecer noutro módulo de
        contas, é sinal de que o foil entrou numa conta por acidente."""
        funis = {"locais": "conta_para_coleccao", "prices": "conta_para_valor"}
        proibidos = ["a_subir", "faltas", "faltas_edicao", "a_mais", "uso_decks",
                     "decks", "pending", "painel", "runas_vista", "cardmarket",
                     "seguir", "catalog"]
        for nome in proibidos:
            fonte = (REPO / "riftvault" / f"{nome}.py").read_text(encoding="utf-8")
            self.assertNotIn("qty_foil", fonte, nome)
        for nome, chave in funis.items():
            fonte = (REPO / "riftvault" / f"{nome}.py").read_text(encoding="utf-8")
            self.assertIn("qty_foil", fonte, nome)
            self.assertIn(chave, fonte, f"{nome} lê a chave do botão")


class TestAsDuasPerguntasDele(Base):
    """5. `foil.conta_para_coleccao` e `foil.conta_para_valor` — as duas a
    `false` (o que vale hoje), e o que muda com cada uma a `true`."""

    def test_por_omissao_os_dois_botoes_estao_desligados(self):
        self.assertFalse(self.foil.conta_para_coleccao())
        self.assertFalse(self.foil.conta_para_valor())
        # E sem o bloco `foil` no config também — a omissão é `false`.
        self.assertFalse(self.foil.conta_para_coleccao({}))
        self.assertFalse(self.foil.conta_para_valor({"foil": {}}))

    def test_o_resumo_e_a_cli_dizem_em_que_estado_estao(self):
        con = self.catalogo()
        r = self.foil.resumo(con)
        self.assertIs(r["conta_para_coleccao"], False)
        self.assertIs(r["conta_para_valor"], False)
        texto = self.foil.texto(r, [{"id": "TST", "name": "TST"}])
        self.assertIn("não contam", texto)
        self.cfg_foil({"conta_para_coleccao": True})
        texto = self.foil.texto(self.foil.resumo(con), [{"id": "TST", "name": "TST"}])
        self.assertIn("CONTAM", texto)

    def test_conta_para_coleccao_ligado_sobe_os_niveis_e_desce_a_wantlist(self):
        """3 Defy (alvo 3, já completo) e 2 Scout (alvo 3, falta 1). Uma foil
        de Scout fecha o playset dela quando o botão está ligado."""
        con = self.catalogo()
        cfg = self.config.load()
        nivel = lambda: [(l["k"], l["done"], l["missing"])
                         for l in self.metrics.niveis_payload(con, cfg)["levels"]]
        self.foil.ajustar(con, "tst-002-100", 1, source="test")   # 2 normais + 1 foil
        antes = nivel()
        wl_antes = self.a_subir.wantlist(con, cfg=cfg)["copies"]

        self.cfg_foil({"conta_para_coleccao": True})
        cfg = self.config.load()
        depois = nivel()
        self.assertNotEqual(depois, antes, "ligado, a foil conta para o alvo")
        # A Scout passa a ter 3 e fecha o playset: uma impressão a mais feita e
        # uma cópia a menos a faltar no nível 3.
        k3_antes = next(d for k, d, _ in antes if k == 3)
        k3_depois = next(d for k, d, _ in depois if k == 3)
        self.assertEqual(k3_depois, k3_antes + 1)
        self.assertEqual(self.a_subir.wantlist(con, cfg=cfg)["copies"], wl_antes - 1)
        # E o VALOR não mexe: são botões separados.
        self.cfg_foil({"conta_para_coleccao": True})
        v_com = self.prices.collection_value(con)["copias"]
        self.cfg_foil({})
        self.assertEqual(self.prices.collection_value(con)["copias"], v_com,
                         "o botão da Coleção não mexe no valor")

    def test_conta_para_valor_ligado_soma_as_foils_ao_preco_da_normal(self):
        con = self.catalogo()
        antes = self.prices.collection_value(con)
        self.foil.ajustar(con, "tst-001-100", 2, source="test")   # a 11 cêntimos
        self.assertEqual(self.prices.collection_value(con), antes,
                         "desligado (hoje), não mexe")

        self.cfg_foil({"conta_para_valor": True})
        depois = self.prices.collection_value(con)
        self.assertEqual(depois["copias"], antes["copias"] + 2)
        self.assertEqual(depois["cents"], antes["cents"] + 2 * 11,
                         "ao preço da normal — não há preço de foil no catálogo")
        # Por edição e no playset jogável também. (O `defy` conta a base ×3 e
        # a arte alternativa ×2; com o botão ligado somam-se-lhe as 2 foils.)
        self.assertEqual(self.prices.value_by_set(con)["TST"],
                         depois["cents"] - 2 * 11, "o OGS fica fora desta edição")
        self.assertEqual(self.metrics.owned_by_card(con)["defy"], 3 + 2 + 2)
        # E os NÍVEIS não mexem: são botões separados.
        cfg = self.config.load()
        self.assertEqual(
            [(l["k"], l["done"]) for l in self.metrics.niveis_payload(con, cfg)["levels"]],
            [(l["k"], l["done"]) for l in self.metrics.niveis_payload(
                con, {**cfg, "foil": {**cfg["foil"], "conta_para_valor": False}})["levels"]])

    def test_uma_carta_so_em_foil_entra_no_valor_com_o_botao_ligado(self):
        """O caso que o `WHERE c.qty > 0` do `owned_by_card` deixava cair."""
        con = self.catalogo()
        self.collection.adjust(con, "tst-001-100", -3, source="test")   # 0 normais
        self.foil.ajustar(con, "tst-001-100", 4, source="test")
        # O `defy` continua a contar as 2 cópias da arte alternativa, que tem a
        # mesma carta lógica; o que não conta é a base, que está a 0 normais.
        self.assertEqual(self.metrics.owned_by_card(con)["defy"], 2)
        copias = self.prices.collection_value(con)["copias"]
        self.cfg_foil({"conta_para_valor": True})
        self.assertEqual(self.metrics.owned_by_card(con)["defy"], 2 + 4)
        self.assertEqual(self.prices.collection_value(con)["copias"], copias + 4,
                         "a carta só em foil entra, apesar do `qty = 0`")

    def test_desligar_os_botoes_repoe_os_numeros_ao_certo(self):
        """Ligar e desligar tem de ser reversível — é config, não dados."""
        con = self.catalogo()
        # A Scout está a 2 de 3: uma foil fecha-lhe o playset com o botão da
        # Coleção ligado, e é isso que faz os níveis mexerem. (Na Defy, que já
        # está a 3 de 3, o botão da Coleção não mudava número nenhum.)
        self.foil.ajustar(con, "tst-002-100", 1, source="test")
        foto = lambda: (self.prices.collection_value(con)["cents"],
                        [(l["k"], l["done"]) for l in
                         self.metrics.niveis_payload(con, self.config.load())["levels"]])
        antes = foto()
        for extra in ({"conta_para_coleccao": True}, {"conta_para_valor": True},
                      {"conta_para_coleccao": True, "conta_para_valor": True}):
            self.cfg_foil(extra)
            self.assertNotEqual(foto(), antes, f"{extra} muda alguma coisa")
        self.cfg_foil({})
        self.assertEqual(foto(), antes, "desligados, tudo como estava")


class TestOContadorNoTile(Base):
    """6. O payload do tile, e os limites 0..LIMITE."""

    def test_o_payload_diz_quem_tem_contador_e_quantas_sao_foil(self):
        con = self.catalogo()
        self.foil.ajustar(con, "tst-001-100", 2, source="test")
        sp = self.metrics.set_payload(con, "TST")
        tiles = {p["id"]: p for g in sp["groups"] for p in g["printings"]}
        self.assertTrue(tiles["tst-001-100"]["foil_ok"])
        self.assertEqual(tiles["tst-001-100"]["foil"], 2)
        self.assertEqual(tiles["tst-001-100"]["qty_total"], 3,
                         "o `qty_total` são as NORMAIS físicas; o total é 3+2")
        self.assertTrue(tiles["tst-002-100"]["foil_ok"])
        self.assertEqual(tiles["tst-002-100"]["foil"], 0)
        for pid in ("tst-001a-100", "tst-003-100", "tst-004-100", "tst-101-100"):
            self.assertFalse(tiles[pid]["foil_ok"], pid)
        ogs = self.metrics.set_payload(con, "OGS")
        self.assertFalse(next(p for g in ogs["groups"] for p in g["printings"])["foil_ok"])

    def test_trava_em_zero_e_no_limite_de_sanidade(self):
        """O `+` já não trava no `qty` — o foil não é uma fatia de nada."""
        con = self.catalogo()
        r = self.foil.ajustar(con, "tst-001-100", 5, source="test")
        self.assertEqual((r["normal"], r["foil"], r["total"], r["applied"]),
                         (3, 5, 8, 5), "5 foils com 3 normais: o total sobe para 8")
        r = self.foil.ajustar(con, "tst-001-100", 10 ** 9, source="test")
        self.assertEqual(r["foil"], self.foil.LIMITE, "trava no limite de sanidade")
        r = self.foil.ajustar(con, "tst-001-100", 1, source="test")
        self.assertEqual(r["applied"], 0, "e não passa dele, sem erro")
        r = self.foil.ajustar(con, "tst-001-100", -(10 ** 9), source="test")
        self.assertEqual((r["normal"], r["foil"], r["applied"]),
                         (3, 0, -self.foil.LIMITE))
        r = self.foil.ajustar(con, "tst-001-100", -1, source="test")
        self.assertEqual((r["foil"], r["applied"]), (0, 0), "trava em zero")

    def test_o_payload_leva_o_limite_para_o_cliente_nao_ter_segunda_copia(self):
        con = self.catalogo()
        self.assertEqual(self.foil.resumo(con)["limite"], self.foil.LIMITE)
        self.assertEqual(self.metrics.index_payload(con)["foil"]["limite"],
                         self.foil.LIMITE)

    def test_o_tile_conta_as_normais_de_todos_os_locais(self):
        """Uma cópia sleevada num deck não deixa de ser normal."""
        self.v.write_deck("azir", "Nome: Azir\n\nLegend:\n1 Emperor of the Sands\n\n"
                                  "MainDeck:\n3 Defy\n")
        con = self.catalogo()
        self.decks.import_all(con, log=lambda *_: None)
        self.locais.mover(con, "tst-001-100", 2, "colecao", "deck:azir", source="test")
        r = self.foil.ajustar(con, "tst-001-100", 3, source="test")
        self.assertEqual((r["normal"], r["foil"], r["total"]), (3, 3, 6))
        sp = self.metrics.set_payload(con, "TST")
        tile = next(p for g in sp["groups"] for p in g["printings"]
                    if p["id"] == "tst-001-100")
        self.assertEqual((tile["qty"], tile["qty_total"], tile["foil"]), (1, 3, 3),
                         "1 normal na Coleção, 3 normais ao todo, mais 3 foils")


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
        # 3 normais + 2 foil, 2 normais + 2 foil: 5 normais, 4 foils, 9 cópias.
        self.assertEqual((tst["normal"], tst["foil"], tst["copies"]), (5, 4, 9))
        self.assertEqual(tst["foil_printings"], 2)
        com = next(x for x in tst["rarity"] if x["id"] == "common")
        inc = next(x for x in tst["rarity"] if x["id"] == "uncommon")
        self.assertEqual((com["normal"], com["foil"]), (3, 2))
        self.assertEqual((inc["normal"], inc["foil"]), (2, 2))
        # O `copies` é sempre a SOMA das duas contagens, por construção.
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
        # normais 3 + 2 + 2 = 7, foils 1 + 2 = 3, cópias 10.
        self.assertEqual((todas["normal"], todas["foil"], todas["copies"]), (7, 3, 10))

    def test_o_resumo_chega_a_edicao_e_ao_index(self):
        con = self.catalogo()
        self.foil.ajustar(con, "tst-001-100", 1, source="test")
        sp = self.metrics.set_payload(con, "TST")["progress"]["foil"]
        self.assertEqual((sp["normal"], sp["foil"], sp["copies"]), (5, 1, 6))
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
        # (raridade, NORMAIS, foil) — incluindo o caso novo: 0 normais e foil.
        itens = [("common", 3, 0), ("common", 4, 4), ("uncommon", 2, 1),
                 ("uncommon", 0, 0), ("uncommon", 0, 2), ("rare", 5, 2),
                 ("mitica", 1, 1), ("common", 7, 3)]
        esperado = self.foil.contar(itens)
        harness = m.group(1) + """
const e = JSON.parse(require('node:fs').readFileSync(0, 'utf8'));
const itens = e.itens.map(([rarity, normal, foil]) => ({rarity, normal, foil}));
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
            j = r.get_json()
            self.assertEqual((j["normal"], j["foil"], j["total"]), (3, 2, 5),
                             "as normais não mexeram e o total é a soma")
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
            # O `/api/adjust` diz o foil de volta — informação para o tile, que
            # NÃO mexeu: tirar 2 normais deixa as 3 foils onde estavam.
            c.post("/api/foil/ajustar", json={"printing_id": "tst-001-100", "delta": 3})
            res = c.post("/api/adjust", json={"printing_id": "tst-001-100", "delta": -2}).get_json()
            self.assertEqual((res["qty"], res["foil"]), (1, 3))
            g = c.get("/api/set/TST.json").get_json()
            tile = next(p for grp in g["groups"] for p in grp["printings"]
                        if p["id"] == "tst-001-100")
            self.assertEqual((tile["foil"], tile["foil_ok"], tile["qty_total"]),
                             (3, True, 1))
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
        self.assertIn("3 normais · 2 foil = 5 cópias", out.getvalue())
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(["foil", "TST-001"]), 0)
        self.assertIn("3 normais · 2 foil = 5 cópias", out.getvalue())
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(["foil", "TST-001", "--menos", "2"]), 0)
        self.assertIn("3 normais · 0 foil = 3 cópias", out.getvalue())
        # O `--mais` além das normais é legítimo desde 2026-09-26.
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(["foil", "TST-001", "--mais", "7"]), 0)
        self.assertIn("3 normais · 7 foil = 10 cópias", out.getvalue())
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
        # O contador do foil nunca manda um `+` de cópias normais.
        troço = js[js.index("async function foilAjustar"):js.index("function refreshFoil")]
        self.assertNotIn("api/adjust", troço)
        # E o `+`/`−` da grelha já não corta o foil (era o modelo antigo).
        applyl = js[js.index("function applyLocal"):js.index("function applyLocal") + 900]
        self.assertNotIn("state.foil.set", applyl,
                         "um `−` nas normais não pode mexer nas foils")
        # O tecto do `+` vem do servidor, não de um número escrito no cliente.
        self.assertIn("function foilLimite", js)
        self.assertIn("state.index?.foil?.limite", js)
        html = (REPO / "riftvault" / "web" / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="foil-resumo"', html)
        css = (REPO / "riftvault" / "web" / "style.css").read_text(encoding="utf-8")
        self.assertIn(".foil-linha", css)
        self.assertIn(".steppers.foil", css)


if __name__ == "__main__":
    unittest.main()

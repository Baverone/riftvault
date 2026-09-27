"""Os `+`/`−` de «já encomendei» nas FALTAS (André, 2026-09-27).

Palavras dele: *"nas faltas, coloca o + e - para eu indicar que ja encomendei,
fica bem mais facil para eu visualizar assim"*.

O que se fixa:
  1. NÃO HÁ CONTADOR NOVO — é a `pending` e a rota `/api/encomenda` que já
     existiam desde 2026-09-11, e o número é UM SÓ: as Faltas e as Encomendas
     leem-no do mesmo sítio;
  2. **A LINHA NÃO DESAPARECE** depois do `+` — é o pedido dele, e o pendente
     já descontava das faltas desde 2026-09-11. Fica visível, a dizer quanto
     falta E quantas vêm a caminho; o que sai é só a wantlist;
  3. o ACABAMENTO: a coluna `pending.foil` (0/1), com migração e backup; o `+`
     numa foil grava foil, e o «Chegou» dela soma ao `copies.qty_foil` e **não**
     ao `qty` — marcar uma foil e ela entrar como normal estragava-lhe a
     coleção;
  4. o `−` nunca desce abaixo de zero e só mexe em linhas por chegar;
  5. a FRONTEIRA: uma foil a caminho não abate uma falta NORMAL, nem o
     contrário — são dois pendentes da mesma impressão;
  6. a rota, a CLI, o `app.js` e o CSS. O «Chegou» **não** foi para as Faltas:
     continua só no separador «Encomendas» (2026-09-17).

Tudo contra pastas temporárias (`tests.fixture.Vault`) e um config temporário
(`RIFTVAULT_CONFIG`): o `data/` e o `riftvault_config.json` a sério nunca são
tocados.
"""

from __future__ import annotations

import importlib
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
CSS = REPO / "riftvault" / "web" / "style.css"
SCHEMA = REPO / "riftvault" / "schema.sql"


class Base(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.close)
        from riftvault import (a_subir, cardmarket, collection, config, db, decks,
                               faltas_edicao, faltas_foil, foil, locais, metrics, pending)
        for m in (locais, metrics, foil, decks, a_subir, faltas_edicao, faltas_foil,
                  pending):
            importlib.reload(m)
        self.config, self.db, self.foil, self.locais = config, db, foil, locais
        self.metrics, self.decks, self.collection = metrics, decks, collection
        self.a_subir, self.faltas_edicao = a_subir, faltas_edicao
        self.faltas_foil, self.pending, self.cardmarket = faltas_foil, pending, cardmarket
        self.escrever_config()

    def escrever_config(self, extra: dict | None = None):
        caminho = self.v.root / "config.json"
        caminho.write_text(json.dumps({
            "foil": {"raridades": ["common", "uncommon"], "edicoes_fora": ["OGS"],
                     "conta_para_coleccao": True, "conta_para_valor": True,
                     "entra_no_a_mais": False},
            "playset_targets_by_type": {"Unit": 3, "Spell": 3, "Gear": 3,
                                        "Battlefield": 1, "Legend": 1, "Rune": 12,
                                        "default": 3},
            "master_targets_by_type": {"Rune": 3},
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

    # -- catálogo -----------------------------------------------------------

    def catalogo(self):
        """Uma edição TST com um caso de cada.

        Nas duas metades (base, comum/incomum — âmbito do foil):
          `tst-001` Defy    Unit comum     1 normal · 0 foil  -> falta 2 e 3 foil
          `tst-002` Scout   Unit incomum   3 normais · 1 foil -> só falta em foil
        Só nas normais (fora do âmbito do foil):
          `tst-003` Brutalizer  Unit rara   0 normais        -> falta 3
          `tst-001a` Defy alt art           0 cópias         -> bloco Alt Art
        """
        con = self.v.connect()
        v = self.v
        v.add_printing(con, "tst-001-100", "TST", 1, "Defy", rarity="common", size=100)
        v.add_printing(con, "tst-001a-100", "TST", 1, "Defy", variant="a", kind="alt_art",
                       rarity="showcase", base_rarity="common", size=100)
        v.add_printing(con, "tst-002-100", "TST", 2, "Scout", rarity="uncommon", size=100)
        v.add_printing(con, "tst-003-100", "TST", 3, "Brutalizer", rarity="rare", size=100)
        v.rebuild(con)
        for pid, cents, foil_cents in (("tst-001-100", 11, 502),
                                       ("tst-001a-100", 500, None),
                                       ("tst-002-100", 25, 90),
                                       ("tst-003-100", 900, None)):
            con.execute("INSERT INTO catalog.price_latest "
                        "(printing_id, price_cents, price_foil_cents) VALUES (?,?,?)",
                        (pid, cents, foil_cents))
        for pid, n in (("tst-001-100", 1), ("tst-002-100", 3)):
            self.collection.adjust(con, pid, n, source="test")
        self.foil.ajustar(con, "tst-002-100", 1, source="test")
        self.addCleanup(con.close)
        return con

    # -- atalhos ------------------------------------------------------------

    def normais(self, con, pid, sid="TST"):
        """A linha de uma impressão na metade das NORMAIS (qualquer bloco)."""
        p = self.faltas_edicao.payload(con)
        d = next(s for s in p["sets"] if s["set"] == sid)
        for g in d["blocks"]:
            for x in g["items"]:
                if x["printing_id"] == pid:
                    return x
        return None

    def foils(self, con, pid, sid="TST"):
        """A linha de uma impressão na metade das FOILS."""
        d = self.faltas_foil.bloco(con)["sets"].get(sid) or {"items": []}
        return next((x for x in d["items"] if x["printing_id"] == pid), None)

    def copias(self, con, pid):
        r = con.execute("SELECT qty, qty_foil FROM copies WHERE printing_id = ?",
                        (pid,)).fetchone()
        return (r["qty"], r["qty_foil"]) if r else (0, 0)


# ---------------------------------------------------------------------------
# 1. É O MESMO MECANISMO — não há contador novo
# ---------------------------------------------------------------------------


class TestOMesmoMecanismo(Base):
    def test_o_mais_escreve_na_pending_que_ja_existia(self):
        con = self.catalogo()
        self.pending.encomendar(con, printing_id="tst-001-100", qty=2, source="test")
        linhas = con.execute("SELECT printing_id, qty, foil, arrived_at "
                             "FROM pending").fetchall()
        self.assertEqual([tuple(r) for r in linhas], [("tst-001-100", 2, 0, None)])

    def test_nao_ha_tabela_nova_nenhuma(self):
        """Um contador próprio das Faltas punha as duas vistas a divergir."""
        con = self.catalogo()
        antes = {r[0] for r in con.execute(
            "SELECT name FROM main.sqlite_master WHERE type='table'")}
        self.pending.encomendar(con, printing_id="tst-001-100", qty=1, source="test")
        depois = {r[0] for r in con.execute(
            "SELECT name FROM main.sqlite_master WHERE type='table'")}
        self.assertEqual(antes, depois)

    def test_uma_so_verdade_faltas_e_encomendas_dizem_o_mesmo(self):
        """O número do tile das Faltas é o mesmo do separador «Encomendas»."""
        con = self.catalogo()
        self.pending.encomendar(con, printing_id="tst-003-100", qty=2, source="test")
        self.assertEqual(self.normais(con, "tst-003-100")["pending"], 2)
        self.assertEqual(self.pending.open_qty(con)["tst-003-100"], 2)
        self.assertEqual(self.pending.grelha(con, "TST")["totals"]["ordered"], 2)
        self.assertEqual(self.pending.totals(con)["copies"], 2)
        e = self.pending.encomendas(con)
        self.assertEqual(e["totals"]["copies"], 2)

    def test_o_mais_grava_na_impressao_do_tile_nao_na_carta(self):
        """Nas Faltas cada linha É uma impressão — a alt art é a alt art."""
        con = self.catalogo()
        self.pending.encomendar(con, printing_id="tst-001a-100", qty=1, source="test")
        self.assertEqual(self.normais(con, "tst-001a-100")["pending"], 1)
        self.assertEqual(self.normais(con, "tst-001-100")["pending"], 0)


# ---------------------------------------------------------------------------
# 2. A LINHA NÃO DESAPARECE — o ponto do pedido
# ---------------------------------------------------------------------------


class TestALinhaFica(Base):
    def test_a_linha_continua_visivel_e_diz_as_duas_coisas(self):
        """Faltam 3, encomenda 1: a linha fica, com «faltam 2 · 1 a caminho»."""
        con = self.catalogo()
        x = self.normais(con, "tst-003-100")
        self.assertEqual((x["have"], x["target"], x["missing"], x["pending"]),
                         (0, 3, 3, 0))
        self.pending.encomendar(con, printing_id="tst-003-100", qty=1, source="test")
        x = self.normais(con, "tst-003-100")
        self.assertIsNotNone(x, "a linha NÃO pode desaparecer depois do +")
        self.assertEqual(x["missing"], 2)
        self.assertEqual(x["pending"], 1)
        self.assertEqual(x["short"], 3, "o que falta na caixa não mexe")

    def test_mesmo_com_a_encomenda_a_cobrir_tudo_a_linha_fica(self):
        """O caso que interessa: encomendar TUDO o que falta. É aqui que a
        linha sumia se o pendente entrasse no `have`."""
        con = self.catalogo()
        self.pending.encomendar(con, printing_id="tst-003-100", qty=3, source="test")
        x = self.normais(con, "tst-003-100")
        self.assertIsNotNone(x, "a linha tem de ficar mesmo coberta")
        self.assertEqual((x["missing"], x["pending"], x["short"]), (0, 3, 3))
        # ... e ela conta como «a caminho», não como falta.
        p = self.faltas_edicao.payload(con)
        d = next(s for s in p["sets"] if s["set"] == "TST")
        g = next(g for g in d["blocks"] if g["id"] == "master")
        self.assertIn("tst-003-100", [i["printing_id"] for i in g["items"]])
        self.assertEqual(g["pending_copies"], 3)

    def test_o_mesmo_nas_FOILS(self):
        """A metade das foils tem de se portar igual — ele vai marcar foils lá."""
        con = self.catalogo()
        x = self.foils(con, "tst-001-100")
        self.assertEqual((x["have"], x["target"], x["missing"], x["pending"]),
                         (0, 3, 3, 0))
        self.pending.encomendar(con, printing_id="tst-001-100", qty=3,
                                source="test", foil=True)
        x = self.foils(con, "tst-001-100")
        self.assertIsNotNone(x, "a linha de foil NÃO pode desaparecer")
        self.assertEqual((x["missing"], x["pending"], x["short"]), (0, 3, 3))

    def test_o_que_sai_e_so_a_wantlist(self):
        """A linha fica no tile e sai da lista de compra — não se compra duas
        vezes. É a mesma regra das quatro wantlists de 2026-09-19."""
        con = self.catalogo()
        w = self.faltas_edicao.wantlist(con, "TST", "master")
        self.assertIn("tst-003-100", [x["printing_id"] for x in w["items"]])
        self.pending.encomendar(con, printing_id="tst-003-100", qty=3, source="test")
        w = self.faltas_edicao.wantlist(con, "TST", "master")
        self.assertNotIn("tst-003-100", [x["printing_id"] for x in w["items"]])
        self.assertIsNotNone(self.normais(con, "tst-003-100"), "mas fica no tile")

    def test_o_que_sai_e_so_a_wantlist_tambem_nas_foils(self):
        con = self.catalogo()
        w = self.faltas_foil.wantlist(con, "TST")
        self.assertIn("tst-001-100", [x["printing_id"] for x in w["items"]])
        self.pending.encomendar(con, printing_id="tst-001-100", qty=3,
                                source="test", foil=True)
        w = self.faltas_foil.wantlist(con, "TST")
        self.assertNotIn("tst-001-100", [x["printing_id"] for x in w["items"]])
        self.assertIsNotNone(self.foils(con, "tst-001-100"), "mas fica no tile")

    def test_o_pendente_acima_do_que_falta_nao_conta_a_mais(self):
        con = self.catalogo()
        self.pending.encomendar(con, printing_id="tst-003-100", qty=9, source="test")
        x = self.normais(con, "tst-003-100")
        self.assertEqual((x["missing"], x["pending"], x["short"]), (0, 3, 3))


# ---------------------------------------------------------------------------
# 3. O ACABAMENTO: a coluna `foil` da `pending`
# ---------------------------------------------------------------------------


class TestAColunaFoil(Base):
    def test_a_coluna_esta_no_schema_com_o_check(self):
        con = self.catalogo()
        cols = {r[1]: r for r in con.execute("PRAGMA table_info(pending)")}
        self.assertIn("foil", cols)
        sql = con.execute("SELECT sql FROM main.sqlite_master WHERE type='table' "
                          "AND name='pending'").fetchone()[0]
        self.assertIn("foil IN (0, 1)", sql.replace("\n", " "))
        self.assertIn("foil", SCHEMA.read_text(encoding="utf-8"))
        with self.assertRaises(sqlite3.IntegrityError):
            con.execute("INSERT INTO pending (printing_id, qty, ordered_at, foil) "
                        "VALUES ('tst-001-100', 1, '2026-09-27', 5)")

    def test_a_migracao_de_uma_base_antiga_poe_tudo_a_zero_e_leva_backup(self):
        """As linhas que já lá estavam eram TODAS de normais: até 2026-09-27
        não havia outra maneira de encomendar."""
        con = self.catalogo()
        # Uma `pending` como era antes de hoje, com duas linhas lá dentro.
        con.execute("DROP TABLE pending")
        con.execute("CREATE TABLE pending (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                    "printing_id TEXT NOT NULL, qty INTEGER NOT NULL CHECK (qty > 0), "
                    "unit_cents INTEGER, ordered_at TEXT NOT NULL, note TEXT, "
                    "arrived_at TEXT)")
        con.execute("INSERT INTO pending (printing_id, qty, ordered_at) "
                    "VALUES ('tst-001-100', 2, '2026-09-20')")
        con.execute("INSERT INTO pending (printing_id, qty, ordered_at, arrived_at) "
                    "VALUES ('tst-003-100', 1, '2026-09-20', '2026-09-21')")
        self.assertNotIn("foil", {r[1] for r in con.execute("PRAGMA table_info(pending)")})
        backups = self.v.root / "data" / "backups"
        antes = len(list(backups.glob("*.db"))) if backups.exists() else 0

        self.db._migrar_pending_foil(con)
        self.assertIn("foil", {r[1] for r in con.execute("PRAGMA table_info(pending)")})
        self.assertEqual([tuple(r) for r in con.execute(
            "SELECT printing_id, qty, foil FROM pending ORDER BY id")],
            [("tst-001-100", 2, 0), ("tst-003-100", 1, 0)])
        self.assertEqual(len(list(backups.glob("*antes-do-pendente-foil*.db"))), 1,
                         "a migração mexe na coleção: leva backup")
        self.assertGreater(len(list(backups.glob("*.db"))), antes)
        # Idempotente: a segunda chamada não faz nada nem outro backup.
        self.db._migrar_pending_foil(con)
        self.assertEqual(len(list(backups.glob("*antes-do-pendente-foil*.db"))), 1)

    def test_o_mais_numa_foil_grava_foil(self):
        con = self.catalogo()
        self.pending.encomendar(con, printing_id="tst-001-100", qty=2,
                                source="test", foil=True)
        self.assertEqual([tuple(r) for r in con.execute(
            "SELECT printing_id, qty, foil FROM pending")], [("tst-001-100", 2, 1)])

    def test_uma_foil_e_uma_normal_da_mesma_impressao_sao_duas_linhas(self):
        con = self.catalogo()
        self.pending.encomendar(con, printing_id="tst-001-100", qty=2, source="test")
        self.pending.encomendar(con, printing_id="tst-001-100", qty=1,
                                source="test", foil=True)
        self.assertEqual(self.pending.open_qty(con)["tst-001-100"], 2)
        self.assertEqual(self.pending.open_qty(con, foil=True)["tst-001-100"], 1)
        self.assertEqual(self.pending.open_qty(con, foil=None)["tst-001-100"], 3)

    def test_nao_se_pode_encomendar_foil_de_uma_impressao_sem_contador(self):
        """A rara não tem contagem de foil: gravar lá uma encomenda de foil era
        gravar o que nenhuma página sabe mostrar."""
        con = self.catalogo()
        with self.assertRaises(self.foil.ForaDoAmbito):
            self.pending.encomendar(con, printing_id="tst-003-100", qty=1,
                                    source="test", foil=True)
        self.assertEqual(con.execute("SELECT COUNT(*) FROM pending").fetchone()[0], 0)


class TestOChegou(Base):
    def test_uma_foil_que_chega_soma_ao_qty_foil_e_nao_ao_qty(self):
        """O erro a não cometer: se marcar uma foil e ela entrar como normal,
        estraga-lhe a coleção."""
        con = self.catalogo()
        self.assertEqual(self.copias(con, "tst-001-100"), (1, 0))
        self.pending.encomendar(con, printing_id="tst-001-100", qty=2,
                                source="test", foil=True)
        feitas = self.pending.arrive(con, source="test")
        self.assertEqual([f["foil"] for f in feitas], [True])
        self.assertEqual(self.copias(con, "tst-001-100"), (1, 2),
                         "as NORMAIS não mexeram; as foils subiram 2")
        # E deixa rasto no registo do foil, que é onde o desfazer vive.
        self.assertEqual(con.execute(
            "SELECT delta, qty_after FROM foil_ops WHERE printing_id = 'tst-001-100' "
            "ORDER BY id DESC LIMIT 1").fetchone()[0], 2)

    def test_uma_normal_que_chega_continua_a_somar_ao_qty(self):
        con = self.catalogo()
        self.pending.encomendar(con, printing_id="tst-001-100", qty=2, source="test")
        feitas = self.pending.arrive(con, source="test")
        self.assertEqual([f["foil"] for f in feitas], [False])
        self.assertEqual(self.copias(con, "tst-001-100"), (3, 0))
        # A entrada de uma normal fica na `ops`, e por isso dá para desfazer.
        self.assertTrue(con.execute(
            "SELECT 1 FROM ops WHERE printing_id = 'tst-001-100' AND delta = 2"
        ).fetchone())

    def test_as_duas_juntas_cada_uma_no_seu_contador(self):
        con = self.catalogo()
        self.pending.encomendar(con, printing_id="tst-001-100", qty=2, source="test")
        self.pending.encomendar(con, printing_id="tst-001-100", qty=3,
                                source="test", foil=True)
        self.pending.arrive(con, source="test")
        self.assertEqual(self.copias(con, "tst-001-100"), (3, 3))

    def test_o_chegou_pode_pedir_so_um_acabamento(self):
        con = self.catalogo()
        self.pending.encomendar(con, printing_id="tst-001-100", qty=2, source="test")
        self.pending.encomendar(con, printing_id="tst-001-100", qty=3,
                                source="test", foil=True)
        self.pending.arrive(con, source="test", printing_id="tst-001-100", foil=True)
        self.assertEqual(self.copias(con, "tst-001-100"), (1, 3))
        self.assertEqual(self.pending.open_qty(con)["tst-001-100"], 2,
                         "a normal continua a caminho")

    def test_uma_foil_fora_do_ambito_chega_na_mesma(self):
        """Ele encolheu o `foil.raridades` depois de encomendar: recusar a
        entrada era perder-lhe a cópia. Quem valida é o `+`."""
        con = self.catalogo()
        self.pending.encomendar(con, printing_id="tst-002-100", qty=1,
                                source="test", foil=True)
        self.escrever_config({"foil": {"raridades": ["common"],
                                       "edicoes_fora": ["OGS"],
                                       "conta_para_coleccao": True,
                                       "conta_para_valor": True}})
        self.pending.arrive(con, source="test")
        self.assertEqual(self.copias(con, "tst-002-100"), (3, 2))


# ---------------------------------------------------------------------------
# 4. O `−`
# ---------------------------------------------------------------------------


class TestOMenos(Base):
    def test_nunca_desce_abaixo_de_zero(self):
        con = self.catalogo()
        with self.assertRaises(self.pending.SemEncomenda):
            self.pending.anular(con, printing_id="tst-001-100", qty=1, source="test")
        self.pending.encomendar(con, printing_id="tst-001-100", qty=1, source="test")
        res = self.pending.anular(con, printing_id="tst-001-100", qty=5, source="test")
        self.assertEqual(res["removed"], 1)
        self.assertEqual(res["open_printing"], 0)
        self.assertEqual(con.execute("SELECT COUNT(*) FROM pending").fetchone()[0], 0)

    def test_so_mexe_em_linhas_por_chegar(self):
        """O que já entrou na coleção desfaz-se pelo `undo`, não por aqui."""
        con = self.catalogo()
        self.pending.encomendar(con, printing_id="tst-001-100", qty=2, source="test")
        self.pending.arrive(con, source="test")
        chegadas = con.execute("SELECT id, qty, arrived_at FROM pending").fetchall()
        with self.assertRaises(self.pending.SemEncomenda):
            self.pending.anular(con, printing_id="tst-001-100", qty=1, source="test")
        self.assertEqual([tuple(r) for r in con.execute(
            "SELECT id, qty, arrived_at FROM pending")],
            [tuple(r) for r in chegadas], "a linha chegada não se tocou")
        self.assertEqual(self.copias(con, "tst-001-100"), (3, 0))

    def test_o_menos_de_uma_metade_nao_desfaz_a_outra(self):
        con = self.catalogo()
        self.pending.encomendar(con, printing_id="tst-001-100", qty=2, source="test")
        self.pending.encomendar(con, printing_id="tst-001-100", qty=2,
                                source="test", foil=True)
        self.pending.anular(con, printing_id="tst-001-100", qty=2, source="test",
                            foil=True)
        self.assertEqual(self.pending.open_qty(con)["tst-001-100"], 2)
        self.assertEqual(self.pending.open_qty(con, foil=True).get("tst-001-100", 0), 0)
        with self.assertRaises(self.pending.SemEncomenda):
            self.pending.anular(con, printing_id="tst-001-100", qty=1, source="test",
                                foil=True)

    def test_sem_acabamento_tira_de_qualquer_uma(self):
        """A omissão é a de sempre — é o que a CLI antiga faz."""
        con = self.catalogo()
        self.pending.encomendar(con, printing_id="tst-001-100", qty=1,
                                source="test", foil=True)
        res = self.pending.anular(con, printing_id="tst-001-100", qty=1, source="test")
        self.assertEqual(res["removed"], 1)


# ---------------------------------------------------------------------------
# 5. A FRONTEIRA entre as duas metades
# ---------------------------------------------------------------------------


class TestAFronteira(Base):
    def test_uma_foil_a_caminho_nao_abate_uma_falta_normal(self):
        con = self.catalogo()
        antes = self.faltas_edicao.payload(con)
        self.pending.encomendar(con, printing_id="tst-001-100", qty=3,
                                source="test", foil=True)
        self.assertEqual(self.faltas_edicao.payload(con), antes,
                         "a metade das normais não mexe com uma foil a caminho")

    def test_uma_normal_a_caminho_nao_abate_uma_falta_de_foil(self):
        con = self.catalogo()
        antes = self.faltas_foil.bloco(con)
        self.pending.encomendar(con, printing_id="tst-001-100", qty=3, source="test")
        self.assertEqual(self.faltas_foil.bloco(con), antes)

    def test_a_mesma_impressao_pode_estar_nas_duas_metades(self):
        """A `tst-001` falta em normal (1 de 3) E em foil (0 de 3): são duas
        linhas, cada uma com o seu `+`."""
        con = self.catalogo()
        self.assertIsNotNone(self.normais(con, "tst-001-100"))
        self.assertIsNotNone(self.foils(con, "tst-001-100"))
        self.pending.encomendar(con, printing_id="tst-001-100", qty=1, source="test")
        self.assertEqual(self.normais(con, "tst-001-100")["pending"], 1)
        self.assertEqual(self.foils(con, "tst-001-100")["pending"], 0)

    def test_o_open_by_card_nao_conta_as_foils(self):
        """É o grão dos decks: a alocação serve-se das NORMAIS, e uma foil a
        caminho não é uma normal a caminho."""
        con = self.catalogo()
        self.pending.encomendar(con, printing_id="tst-001-100", qty=2,
                                source="test", foil=True)
        self.assertEqual(self.pending.open_by_card(con), {})
        self.pending.encomendar(con, printing_id="tst-001-100", qty=1, source="test")
        self.assertEqual(sum(self.pending.open_by_card(con).values()), 1)

    def test_o_open_qty_por_omissao_e_so_das_normais(self):
        con = self.catalogo()
        self.pending.encomendar(con, printing_id="tst-001-100", qty=4,
                                source="test", foil=True)
        self.assertEqual(self.pending.open_qty(con), {})

    def test_o_pending_nao_escreve_no_qty_foil_a_mao(self):
        """Quem escreve a coluna é o `foil.ajustar` — é o que mantém o rasto na
        `foil_ops` e a conta num sítio só."""
        fonte = (REPO / "riftvault" / "pending.py").read_text(encoding="utf-8")
        self.assertNotIn("UPDATE copies", fonte)
        self.assertNotIn("INSERT INTO copies", fonte)
        self.assertIn("foil_mod.ajustar", fonte)


# ---------------------------------------------------------------------------
# 6. O separador «Encomendas» vê o mesmo
# ---------------------------------------------------------------------------


class TestNasEncomendas(Base):
    def test_uma_foil_a_caminho_aparece_no_fora_marcada(self):
        """O corte é de rara para cima e as foils são todas comuns e incomuns:
        aparecem SEMPRE no «fora da grelha», nunca num tile — mas aparecem."""
        con = self.catalogo()
        self.pending.encomendar(con, printing_id="tst-001-100", qty=2,
                                source="test", foil=True)
        g = self.pending.grelha(con, "TST")
        fora = g["fora"]
        self.assertEqual([(x["printing_id"], x["foil"], x["qty"]) for x in fora],
                         [("tst-001-100", True, 2)])
        self.assertEqual(g["totals"]["ordered"], 0, "não é uma normal a caminho")

    def test_a_normal_e_a_foil_da_mesma_impressao_sao_duas_linhas_do_fora(self):
        con = self.catalogo()
        self.pending.encomendar(con, printing_id="tst-001-100", qty=2, source="test")
        self.pending.encomendar(con, printing_id="tst-001-100", qty=1,
                                source="test", foil=True)
        fora = self.pending.grelha(con, "TST")["fora"]
        self.assertEqual(sorted((x["foil"], x["qty"]) for x in fora),
                         [(False, 2), (True, 1)])

    def test_a_lista_das_encomendas_separa_os_acabamentos_e_o_preco(self):
        con = self.catalogo()
        self.pending.encomendar(con, printing_id="tst-002-100", qty=1, source="test")
        self.pending.encomendar(con, printing_id="tst-002-100", qty=2,
                                source="test", foil=True)
        e = self.pending.encomendas(con)
        itens = e["a_caminho"][0]["items"]
        self.assertEqual(sorted((x["foil"], x["qty"], x["price"]) for x in itens),
                         [(False, 1, 25), (True, 2, 90)])
        self.assertEqual(e["totals"]["copies"], 3)
        self.assertEqual(e["totals"]["copies_foil"], 2)
        self.assertEqual(e["totals"]["printings"], 1, "é a mesma impressão")

    def test_uma_foil_a_caminho_nunca_e_para_um_deck(self):
        """A alocação serve-se das normais; uma foil a caminho fica para a
        Coleção quando chegar."""
        con = self.catalogo()
        self.pending.encomendar(con, printing_id="tst-001-100", qty=2,
                                source="test", foil=True)
        e = self.pending.encomendas(con)
        x = e["a_caminho"][0]["items"][0]
        self.assertEqual(x["para"], [])
        self.assertEqual(x["sem_deck"], 2)


# ---------------------------------------------------------------------------
# 7. Ler não escreve
# ---------------------------------------------------------------------------


class TestLerNaoEscreve(Base):
    def test_ver_as_faltas_nao_cria_encomendas(self):
        con = self.catalogo()
        self.faltas_foil.payload_completo(con)
        self.faltas_foil.payload_completo(con)
        self.assertEqual(con.execute("SELECT COUNT(*) FROM pending").fetchone()[0], 0)
        self.assertEqual(self.copias(con, "tst-001-100"), (1, 0))


# ---------------------------------------------------------------------------
# 8. A rota, a CLI, o `app.js` e o CSS
# ---------------------------------------------------------------------------


class TestRotaCLIEcra(Base):
    def test_a_rota_encomenda_aceita_o_acabamento(self):
        con = self.catalogo()
        con.close()
        from riftvault import server
        importlib.reload(server)
        server.app.testing = True
        with server.app.test_client() as c:
            r = c.post("/api/encomenda", json={"printing_id": "tst-001-100",
                                               "delta": 2, "foil": True})
            self.assertEqual(r.status_code, 200)
            j = r.get_json()
            self.assertEqual((j["open_printing"], j["open_foil"], j["open_normal"]),
                             (2, 2, 0))
            # O `−` da metade das foils não pode tirar uma normal.
            r = c.post("/api/encomenda", json={"printing_id": "tst-001-100",
                                               "delta": 1, "foil": False})
            self.assertEqual(r.get_json()["open_printing"], 1)
            r = c.post("/api/encomenda", json={"printing_id": "tst-001-100",
                                               "delta": -1, "foil": True})
            self.assertEqual(r.get_json()["open_foil"], 1)
            self.assertEqual(r.get_json()["open_normal"], 1)
            # Fora do âmbito do foil: 400, com a razão escrita.
            r = c.post("/api/encomenda", json={"printing_id": "tst-003-100",
                                               "delta": 1, "foil": True})
            self.assertEqual(r.status_code, 400)
            self.assertIn("contagem de foil", r.get_json()["error"])

    def test_a_rota_do_chegou_aceita_o_acabamento(self):
        con = self.catalogo()
        self.pending.encomendar(con, printing_id="tst-001-100", qty=2,
                                source="test", foil=True)
        con.close()
        from riftvault import server
        importlib.reload(server)
        server.app.testing = True
        with server.app.test_client() as c:
            r = c.post("/api/pending/arrive", json={"printing_id": "tst-001-100",
                                                    "foil": True})
            self.assertEqual(r.status_code, 200)
            self.assertTrue(r.get_json()["arrived"][0]["foil"])
        con = self.v.connect()
        self.assertEqual(self.copias(con, "tst-001-100"), (1, 2))
        con.close()

    def test_a_cli_tem_o_foil_e_mexe_no_contador_certo(self):
        con = self.catalogo()
        con.close()
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        r = subprocess.run([sys.executable, "-X", "utf8", "-m", "riftvault",
                            "encomendas", "--mais", "tst-001-100", "2", "--foil"],
                           cwd=str(REPO), capture_output=True, text=True,
                           encoding="utf-8", env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("foil", r.stdout.lower())
        r = subprocess.run([sys.executable, "-X", "utf8", "-m", "riftvault",
                            "encomendas", "--chegou", "tst-001-100"],
                           cwd=str(REPO), capture_output=True, text=True,
                           encoding="utf-8", env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        con = self.v.connect()
        self.assertEqual(self.copias(con, "tst-001-100"), (1, 2))
        con.close()

    def test_o_app_js_poe_os_botoes_nos_tiles_das_faltas(self):
        js = APP_JS.read_text(encoding="utf-8")
        self.assertIn("data-fe-pid", js)
        self.assertIn("data-fe-foil", js)
        self.assertIn("function feAjustar", js)
        self.assertIn("function ligarFeEnc", js)
        # Os botões chamam a rota QUE JÁ EXISTIA, com o acabamento.
        m = re.search(r"async function feAjustar[\s\S]*?\n}\n", js)
        self.assertIsNotNone(m)
        self.assertIn("'api/encomenda'", m.group(0))
        self.assertIn("foil: !!foil", m.group(0))

    def test_o_chegou_nao_foi_para_as_faltas(self):
        """Ele só pediu o `+` e o `−`; o «Chegou» continua nas Encomendas."""
        js = APP_JS.read_text(encoding="utf-8")
        m = re.search(r"function feTile\([\s\S]*?\n}\n", js)
        self.assertIsNotNone(m)
        self.assertNotIn("chegou", m.group(0).lower())
        m = re.search(r"function feEncHTML\([\s\S]*?\n}\n", js)
        self.assertNotIn("chegou", m.group(0).lower())

    def test_a_linha_encomendada_leva_marca_no_ecra(self):
        js = APP_JS.read_text(encoding="utf-8")
        self.assertIn("fe-enc", js)
        css = CSS.read_text(encoding="utf-8")
        self.assertIn(".dtile.fe-enc", css)
        self.assertIn(".fe-enc-bot", css)

    def test_o_gemeo_em_javascript_da_a_mesma_soma(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("sem node")
        js = APP_JS.read_text(encoding="utf-8")
        m = re.search(r"/\* @fe-soma:inicio.*?\*/(.*?)/\* @fe-soma:fim \*/", js, re.S)
        self.assertIsNotNone(m, "o troço puro da soma tem de estar marcado no app.js")
        itens = [
            {"missing": 3, "pending": 0, "total": 300, "price": 100},
            {"missing": 0, "pending": 2, "total": 0, "price": 100},
            {"missing": 1, "pending": 1, "total": 50, "price": 50},
            {"missing": 2, "pending": 0, "total": 0, "price": None},
        ]
        harness = m.group(1) + """
const itens = JSON.parse(require('node:fs').readFileSync(0, 'utf8'));
process.stdout.write(JSON.stringify(feSoma(itens)));
"""
        r = subprocess.run([node, "-e", harness], input=json.dumps(itens),
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), self.faltas_edicao.soma(itens))


if __name__ == "__main__":
    unittest.main(verbosity=2)

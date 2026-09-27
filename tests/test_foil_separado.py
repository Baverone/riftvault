# -*- coding: utf-8 -*-
"""DUAS CONTAGENS SEPARADAS: as normais em cima, as foils em baixo (2026-09-27).

Palavras dele, a corrigir-nos: *"quero que haja 2 contagens separadas / a de
normais e de foils / verifiquei ontem que a contagem sobe com as foils e a
impressao que fica e que eu tenho as cartas todas, e quando me falta normais
nao consigo perceber automaticamente que falta / quero que a contagem na carta
seja a de non-foil e a de baixo seja a foil, as coisas separadas"*.

O ERRO ERA NOSSO. A 2026-09-26 ele disse *"contabilizas tambem como parte do
master set"*, ligámos o `foil.conta_para_coleccao`, medimos que não mudava nível
nenhum e dissemos-lho — era verdade nesse minuto, porque só tinha foils onde já
tinha o playset. Marcou mais 193 foils e deixou de ser verdade: **47 impressões
liam-se «3/3» com as normais a 2/3, a esconder 48 cópias normais em falta**.

O que este ficheiro fixa:

  1. O CASO DELE  — 2 normais de um playset de 3 com 1 foil aparece
     **INCOMPLETA**: no tile, nos níveis, nas Faltas e na wantlist. É o teste
     que fica vermelho se alguém voltar a somar.
  2. O TILE  — o crachá é as NORMAIS contra o alvo da Coleção, e a linha de
     baixo é o FOIL contra o `foil.alvo`. Nunca somadas, e a separação não
     depende de chave nenhuma.
  3. O ÂMBITO DA LINHA  — só as impressões com contador (`foil.no_ambito`): de
     rara para cima não há linha de foil nenhuma.
  4. O ALVO DE FOIL  — o `metrics.playset_target`, num sítio só (`foil.alvo`), o
     MESMO da metade das foils do separador Faltas: Rune 12, Battlefield 1.
  5. O VALOR NÃO MUDOU  — o `conta_para_valor` fica a `true` e é outra pergunta.
  6. OS DOIS `+`/`−`  — cada um no seu contador, e um não mexe no outro.
  7. A METADE DAS FOILS DAS FALTAS E A 5.ª WANTLIST  — ficam como estavam.
  8. O CONFIG  — a chave, o default e a nota.
  9. A INTERFACE  — o `app.js` e o CSS.

Corre contra pastas temporárias e um config temporário: o `data/` e o
`riftvault_config.json` reais nunca são tocados.
"""
from __future__ import annotations

import contextlib
import importlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.fixture import REPO, Vault  # noqa: E402

APP = REPO / "riftvault" / "web" / "app.js"
CSS = REPO / "riftvault" / "web" / "style.css"
CONFIG_REAL = REPO / "riftvault_config.json"


class Base(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.close)
        from riftvault import (a_subir, collection, config, db, faltas_edicao,
                              faltas_foil, foil, locais, metrics, painel,
                              pending, prices)
        for m in (locais, metrics, foil, painel, a_subir, faltas_edicao,
                  faltas_foil, pending, prices):
            importlib.reload(m)
        self.config, self.db, self.foil, self.locais = config, db, foil, locais
        self.metrics, self.painel, self.a_subir = metrics, painel, a_subir
        self.faltas_edicao, self.faltas_foil = faltas_edicao, faltas_foil
        self.prices, self.collection = prices, collection
        # A omissão dos testes é a do config REAL de hoje: a Coleção conta as
        # NORMAIS, o valor conta as foils.
        self.cfg_foil({"conta_para_coleccao": False, "conta_para_valor": True,
                       "entra_no_a_mais": False})

    def cfg_foil(self, foil_extra: dict, extra: dict | None = None):
        caminho = self.v.root / "config.json"
        caminho.write_text(json.dumps({
            "foil": {"raridades": ["common", "uncommon"], "edicoes_fora": ["OGS"],
                     **foil_extra},
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
        """A edição TST, feita à imagem do caso dele.

          `tst-001-100`  comum, **2 normais** de um playset de 3 — a que ele não
                         conseguia ver que lhe faltava
          `tst-002-100`  incomum, 3 normais (playset feito)
          `tst-003-100`  RARA — fora do âmbito do foil, não leva linha
          `tst-004-100`  Battlefield comum (alvo de playset 1)
          `tst-005-100`  Rune comum (alvo de playset 12, alvo de coleção 3)
          `ogs-001-024`  o OGS, fora do âmbito por edição
        """
        con = self.v.connect()
        v = self.v
        v.add_printing(con, "tst-001-100", "TST", 1, "Defy", rarity="common", size=100)
        v.add_printing(con, "tst-002-100", "TST", 2, "Scout", rarity="uncommon", size=100)
        v.add_printing(con, "tst-003-100", "TST", 3, "Brutalizer", rarity="rare", size=100)
        v.add_printing(con, "tst-004-100", "TST", 4, "Noxus", card_type="Battlefield",
                       rarity="common", size=100)
        v.add_printing(con, "tst-005-100", "TST", 5, "Order Rune", card_type="Rune",
                       rarity="common", size=100)
        v.add_printing(con, "ogs-001-024", "OGS", 1, "Starter Scout", rarity="common",
                       size=24)
        v.rebuild(con)
        for pid, cents in (("tst-001-100", 11), ("tst-002-100", 25),
                           ("tst-003-100", 900), ("tst-004-100", 30),
                           ("tst-005-100", 11), ("ogs-001-024", 11)):
            con.execute("INSERT INTO catalog.price_latest (printing_id, price_cents) "
                        "VALUES (?,?)", (pid, cents))
        # O caso dele: 2 normais de 3, e uma foil por cima.
        for pid, n in (("tst-001-100", 2), ("tst-002-100", 3), ("tst-003-100", 1)):
            self.collection.adjust(con, pid, n, source="test")
        self.foil.ajustar(con, "tst-001-100", 1, source="test")
        self.addCleanup(con.close)
        return con

    # -- atalhos ------------------------------------------------------------
    def tile(self, con, pid, set_id="TST"):
        for g in self.metrics.set_payload(con, set_id)["groups"]:
            for p in g["printings"]:
                if p["id"] == pid:
                    return p
        self.fail(f"{pid} não está na grelha")

    def niveis(self, con):
        n = self.metrics.niveis_payload(con, self.config.load())
        return [(x["k"], x["done"], x["total"], x["missing"]) for x in n["levels"]]

    def em_falta(self, con):
        """printing_id -> cópias a comprar, na metade das NORMAIS das Faltas."""
        p = self.faltas_edicao.payload(con, self.config.load())
        out = {}
        for d in p["sets"]:
            for b in d["blocks"]:
                for x in b["items"]:
                    out[x["printing_id"]] = x["missing"]
        return out


# ---------------------------------------------------------------------------
# 1. O CASO DELE: 2 normais + 1 foil aparece INCOMPLETA
# ---------------------------------------------------------------------------


class TestOCasoDele(Base):
    """O teste que esta ordem existe para escrever.

    *"quando me falta normais nao consigo perceber automaticamente que falta"*.
    Uma impressão com 2 normais de um playset de 3 e 1 foil tem de aparecer
    incompleta em todos os sítios onde a Coleção se mede.
    """

    def test_o_tile_diz_2_de_3_e_nao_3_de_3(self):
        con = self.catalogo()
        t = self.tile(con, "tst-001-100")
        self.assertEqual(t["qty"], 2, "o crachá é as NORMAIS")
        self.assertEqual(t["target"], 3)
        self.assertLess(t["qty"], t["target"], "tem de se ler como INCOMPLETA")
        # A outra contagem está lá, à parte, com o alvo dela.
        self.assertEqual(t["foil"], 1)
        self.assertEqual(t["foil_target"], 3)
        self.assertTrue(t["foil_ok"])

    def test_o_nivel_do_playset_nao_a_conta_como_feita(self):
        """É a conta das 47/48 do `data/` real, em pequeno: ligar a chave ganha
        UMA impressão feita e perde UMA cópia em falta — a `001`."""
        con = self.catalogo()
        sem = dict((k, (done, missing)) for k, done, _t, missing in self.niveis(con))
        self.cfg_foil({"conta_para_coleccao": True, "conta_para_valor": True})
        com = dict((k, (done, missing)) for k, done, _t, missing in self.niveis(con))
        self.assertEqual(com[3][0] - sem[3][0], 1, "a `001` passava a contar feita")
        self.assertEqual(sem[3][1] - com[3][1], 1, "e a cópia normal desaparecia")
        # E os níveis 1 e 2 não mexem: ela já tinha 2 normais.
        self.assertEqual(sem[1], com[1])
        self.assertEqual(sem[2], com[2])

    def test_ela_esta_nas_faltas_e_na_wantlist(self):
        con = self.catalogo()
        falta = self.em_falta(con)
        self.assertEqual(falta.get("tst-001-100"), 1,
                         "falta 1 cópia NORMAL para o playset")
        w = self.a_subir.wantlist(con)
        ids = {x["printing_id"] for x in w["items"]}
        self.assertIn("tst-001-100", ids, "tem de estar na wantlist a comprar")

    def test_A_PROVA_PELA_NEGATIVA_somar_esconde_a_falta(self):
        """Com o `conta_para_coleccao` ligado — o que estava mal — a MESMA
        impressão lê-se «3/3», sai das Faltas e sai da wantlist.

        É este par de testes que impede a volta atrás em silêncio.
        """
        con = self.catalogo()
        self.cfg_foil({"conta_para_coleccao": True, "conta_para_valor": True})
        t = self.tile(con, "tst-001-100")
        self.assertEqual(t["qty"], 3)
        self.assertEqual(t["qty"], t["target"], "é isto que lhe escondia a falta")
        self.assertNotIn("tst-001-100", self.em_falta(con))
        ids = {x["printing_id"] for x in self.a_subir.wantlist(con)["items"]}
        self.assertNotIn("tst-001-100", ids)

    def test_a_foil_sozinha_nao_faz_a_carta_aparecer_como_tida(self):
        """Uma carta que ele SÓ tenha em foil (0 normais) continua a contar zero
        na Coleção — e isso é estado legítimo desde 2026-09-26."""
        con = self.catalogo()
        self.foil.ajustar(con, "tst-004-100", 2, source="test")
        t = self.tile(con, "tst-004-100")
        self.assertEqual((t["qty"], t["target"]), (0, 1))
        self.assertEqual((t["foil"], t["foil_target"]), (2, 1))
        self.assertEqual(self.em_falta(con).get("tst-004-100"), 1)

    def test_o_aviso_da_metade_das_foils_continua_a_apanhar_o_caso(self):
        """O `aviso_normais` (2026-09-27, de manhã) foi feito exactamente para
        este caso e continua a valer — só que agora o tile já o diz sozinho."""
        con = self.catalogo()
        aviso = self.faltas_foil.aviso_normais(con)
        self.assertEqual([x["printing_id"] for x in aviso], ["tst-001-100"])
        self.assertEqual((aviso[0]["normais"], aviso[0]["target"], aviso[0]["foil"]),
                         (2, 3, 1))


# ---------------------------------------------------------------------------
# 2. O TILE: duas contagens, nunca somadas
# ---------------------------------------------------------------------------


class TestOTile(Base):
    def test_o_payload_leva_as_tres_chaves_do_foil(self):
        con = self.catalogo()
        t = self.tile(con, "tst-002-100")
        for chave in ("foil", "foil_ok", "foil_target"):
            self.assertIn(chave, t)

    def test_o_crachá_e_a_linha_sao_numeros_diferentes(self):
        """Com 3 normais e 5 foils, o crachá diz 3/3 e a linha diz 5/3 — nunca
        8 em sítio nenhum."""
        con = self.catalogo()
        self.foil.ajustar(con, "tst-002-100", 5, source="test")
        t = self.tile(con, "tst-002-100")
        self.assertEqual((t["qty"], t["target"]), (3, 3))
        self.assertEqual((t["foil"], t["foil_target"]), (5, 3))
        self.assertNotEqual(t["qty"], 8)

    def test_a_separacao_do_tile_nao_depende_das_chaves(self):
        """O `foil` e o `foil_target` vêm no payload com as chaves ligadas ou
        desligadas: a linha de baixo é estrutural."""
        con = self.catalogo()
        for chaves in ({"conta_para_coleccao": False, "conta_para_valor": False},
                       {"conta_para_coleccao": True, "conta_para_valor": True}):
            self.cfg_foil(chaves)
            t = self.tile(con, "tst-001-100")
            self.assertEqual((t["foil"], t["foil_target"]), (1, 3), chaves)

    def test_ter_mais_foils_do_que_o_alvo_e_legitimo(self):
        """O alvo é um alvo, não um tecto: 4 foils de um playset de 3 lêem-se
        «4/3», como o crachá das normais já fazia."""
        con = self.catalogo()
        self.foil.ajustar(con, "tst-002-100", 4, source="test")
        t = self.tile(con, "tst-002-100")
        self.assertEqual((t["foil"], t["foil_target"]), (4, 3))


# ---------------------------------------------------------------------------
# 3. O ÂMBITO DA LINHA DE FOIL
# ---------------------------------------------------------------------------


class TestOAmbitoDaLinha(Base):
    def test_de_rara_para_cima_nao_ha_linha_de_foil(self):
        """Em Riftbound a carta normal de uma rara É a foil: um «0/3 foil» ali
        era mentira."""
        con = self.catalogo()
        t = self.tile(con, "tst-003-100")
        self.assertFalse(t["foil_ok"])
        self.assertEqual(t["foil_target"], 0)

    def test_o_ogs_fica_todo_de_fora(self):
        con = self.catalogo()
        t = self.tile(con, "ogs-001-024", set_id="OGS")
        self.assertFalse(t["foil_ok"])
        self.assertEqual(t["foil_target"], 0)

    def test_o_ambito_da_linha_e_o_do_contador_e_o_da_metade_das_foils(self):
        """Uma pergunta, uma resposta: o `foil.no_ambito`."""
        con = self.catalogo()
        do_tile = {p["id"] for g in self.metrics.set_payload(con, "TST")["groups"]
                   for p in g["printings"] if p["foil_ok"]}
        do_contador = set(self.foil.ids_do_ambito(con, self.config.load(), "TST"))
        da_metade = {pid for pid, i in self.faltas_foil.escopo(con).items()
                     if i["set_id"] == "TST"}
        self.assertEqual(do_tile, do_contador)
        self.assertEqual(do_tile, da_metade)

    def test_o_ambito_muda_com_o_config(self):
        con = self.catalogo()
        self.cfg_foil({"raridades": ["rare"]})
        self.assertTrue(self.tile(con, "tst-003-100")["foil_ok"])
        self.assertFalse(self.tile(con, "tst-001-100")["foil_ok"])


# ---------------------------------------------------------------------------
# 4. O ALVO DE FOIL
# ---------------------------------------------------------------------------


class TestOAlvoDeFoil(Base):
    def test_e_o_playset_do_tipo(self):
        con = self.catalogo()
        self.assertEqual(self.tile(con, "tst-001-100")["foil_target"], 3)   # Unit
        self.assertEqual(self.tile(con, "tst-004-100")["foil_target"], 1)   # Battlefield
        self.assertEqual(self.tile(con, "tst-005-100")["foil_target"], 12)  # Rune

    def test_na_runa_o_alvo_de_foil_nao_e_o_alvo_da_coleccao(self):
        """A única divergência entre as duas contagens, e diz-se em voz alta: a
        runa base pede 3 na Coleção (`master_targets_by_type`, 2026-09-15) e 12
        em foil (o playset jogável)."""
        con = self.catalogo()
        self.cfg_foil({}, extra={"master_targets_by_type": {"Rune": 3}})
        t = self.tile(con, "tst-005-100")
        self.assertEqual(t["target"], 3)
        self.assertEqual(t["foil_target"], 12)

    def test_vem_da_tabela_do_config(self):
        con = self.catalogo()
        self.cfg_foil({}, extra={"playset_targets_by_type": {
            "Unit": 4, "Battlefield": 2, "Rune": 6, "default": 3}})
        self.assertEqual(self.tile(con, "tst-001-100")["foil_target"], 4)
        self.assertEqual(self.tile(con, "tst-004-100")["foil_target"], 2)
        self.assertEqual(self.tile(con, "tst-005-100")["foil_target"], 6)

    def test_e_o_MESMO_alvo_da_metade_das_foils(self):
        con = self.catalogo()
        esc = self.faltas_foil.escopo(con)
        for g in self.metrics.set_payload(con, "TST")["groups"]:
            for p in g["printings"]:
                if p["foil_ok"]:
                    self.assertEqual(p["foil_target"], esc[p["id"]]["target"], p["id"])

    def test_ha_uma_resposta_so_e_o_faltas_foil_delega(self):
        ff = (REPO / "riftvault" / "faltas_foil.py").read_text(encoding="utf-8")
        fo = (REPO / "riftvault" / "foil.py").read_text(encoding="utf-8")
        self.assertIn("metrics.playset_target(", fo)
        self.assertIn("return foil.alvo(", ff)
        self.assertNotIn("metrics.playset_target(", ff)
        # E o `metrics` não escreve um alvo de foil à mão: pergunta ao `foil`.
        me = (REPO / "riftvault" / "metrics.py").read_text(encoding="utf-8")
        self.assertIn("foil.alvo(", me)

    def test_o_ids_do_ambito_traz_o_type_e_o_is_token(self):
        """Sem eles o `metrics.campo` devolvia `None` e o alvo saía errado EM
        SILÊNCIO — que é o que esta casa não faz."""
        con = self.catalogo()
        for r in self.foil.ids_do_ambito(con, self.config.load()).values():
            self.assertIsNotNone(r["type"])
            self.assertEqual(self.foil.alvo(r), self.foil.alvo(dict(r)))


# ---------------------------------------------------------------------------
# 5. O VALOR NÃO MUDOU
# ---------------------------------------------------------------------------


class TestOValor(Base):
    def test_o_valor_e_o_mesmo_com_a_chave_da_coleccao_ligada_ou_nao(self):
        """Duas perguntas, duas chaves: mexer na da Coleção não pode mexer no
        valor."""
        con = self.catalogo()
        antes = self.prices.collection_value(con)["cents"]
        self.cfg_foil({"conta_para_coleccao": True, "conta_para_valor": True})
        self.assertEqual(self.prices.collection_value(con)["cents"], antes)

    def test_as_foils_continuam_a_contar_para_o_valor(self):
        con = self.catalogo()
        com = self.prices.collection_value(con)["cents"]
        self.cfg_foil({"conta_para_coleccao": False, "conta_para_valor": False})
        sem = self.prices.collection_value(con)["cents"]
        self.assertGreater(com, sem, "a foil da `001` vale 11 cêntimos")
        self.assertEqual(com - sem, 11)

    def test_a_leitura_de_referencia_das_chaves(self):
        self.assertFalse(self.foil.conta_para_coleccao())
        self.assertTrue(self.foil.conta_para_valor())
        self.assertFalse(self.foil.entra_no_a_mais())


# ---------------------------------------------------------------------------
# 6. OS DOIS `+`/`−`
# ---------------------------------------------------------------------------


class TestOsDoisContadores(Base):
    def test_o_mais_do_foil_nao_mexe_nas_normais(self):
        con = self.catalogo()
        self.foil.ajustar(con, "tst-002-100", 2, source="test")
        r = con.execute("SELECT qty, qty_foil FROM copies WHERE printing_id=?",
                        ("tst-002-100",)).fetchone()
        self.assertEqual((r["qty"], r["qty_foil"]), (3, 2))
        self.assertEqual(self.tile(con, "tst-002-100")["qty"], 3)

    def test_o_menos_das_normais_nao_mexe_nas_foils(self):
        con = self.catalogo()
        self.collection.adjust(con, "tst-001-100", -2, source="test")
        r = con.execute("SELECT qty, qty_foil FROM copies WHERE printing_id=?",
                        ("tst-001-100",)).fetchone()
        self.assertEqual((r["qty"], r["qty_foil"]), (0, 1))

    def test_o_menos_do_foil_trava_no_zero(self):
        con = self.catalogo()
        r = self.foil.ajustar(con, "tst-001-100", -9, source="test")
        self.assertEqual(r["foil"], 0)
        self.assertEqual(r["normal"], 2, "as normais não mexeram")

    def test_o_ajustar_devolve_o_alvo_de_foil(self):
        """Para a CLI e o tile dizerem «foil M/T» a partir do mesmo número."""
        con = self.catalogo()
        r = self.foil.ajustar(con, "tst-005-100", 1, source="test")
        self.assertEqual((r["foil"], r["foil_target"]), (1, 12))

    def test_a_cli_diz_as_duas_contagens_separadas_e_o_alvo(self):
        con = self.catalogo()
        con.close()
        from riftvault import cli
        importlib.reload(cli)
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(["foil", "TST-001"]), 0)
        self.assertIn("2 normais · foil 1/3", out.getvalue())
        self.assertNotIn("= 3 cópias", out.getvalue(),
                         "o total somado saiu da linha: era ele que escondia a falta")


# ---------------------------------------------------------------------------
# 7. A METADE DAS FOILS DAS FALTAS E A 5.ª WANTLIST FICAM COMO ESTAVAM
# ---------------------------------------------------------------------------


class TestAMetadeDasFoils(Base):
    def test_o_bloco_das_foils_nao_muda_com_a_chave(self):
        con = self.catalogo()
        antes = self.faltas_foil.bloco(con)
        self.cfg_foil({"conta_para_coleccao": True, "conta_para_valor": True})
        depois = self.faltas_foil.bloco(con)
        self.assertEqual(antes["totals"], depois["totals"])
        self.assertEqual(antes["scope"], depois["scope"])
        self.assertEqual([x["printing_id"] for x in antes["sets"]["TST"]["items"]],
                         [x["printing_id"] for x in depois["sets"]["TST"]["items"]])

    def test_a_quinta_wantlist_continua_a_existir_e_a_ser_so_das_foils(self):
        con = self.catalogo()
        w = self.faltas_foil.wantlist(con, "TST")
        self.assertEqual(w["block"], "foil")
        self.assertFalse(w["in_lists"])
        self.assertTrue(all(x["foil"] for x in w["items"]))
        # E o que lhe falta em foil na `001` são 2 (tem 1 de 3) — outro número
        # que o da metade das normais (1 cópia normal).
        por = {x["printing_id"]: x["missing"] for x in w["items"]}
        self.assertEqual(por["tst-001-100"], 2)
        self.assertEqual(self.em_falta(con)["tst-001-100"], 1)

    def test_as_foils_continuam_fora_da_contagem_de_faltas_das_normais(self):
        con = self.catalogo()
        p = self.faltas_foil.payload_completo(con)
        ids = {b["id"] for d in p["sets"] for b in d["blocks"]}
        self.assertNotIn("foil", ids, "a metade das foils não é um dos blocos")
        self.assertEqual(p["totals"],
                         self.faltas_edicao.payload(con, self.config.load())["totals"])


# ---------------------------------------------------------------------------
# 8. O CONFIG
# ---------------------------------------------------------------------------


class TestOConfig(Base):
    def test_a_chave_no_config_real_e_no_default(self):
        cfg = json.loads(CONFIG_REAL.read_text(encoding="utf-8"))
        self.assertIs(cfg["foil"]["conta_para_coleccao"], False)
        self.assertIs(cfg["foil"]["conta_para_valor"], True)
        self.assertIs(self.config.DEFAULTS["foil"]["conta_para_coleccao"], False)
        self.assertIs(self.config.DEFAULTS["foil"]["conta_para_valor"], True)

    def test_sem_a_chave_as_foils_nao_contam_para_a_coleccao(self):
        """A omissão é a resposta segura: um riftvault sem config não pode
        esconder faltas."""
        con = self.catalogo()
        self.cfg_foil({})
        self.assertEqual(self.tile(con, "tst-001-100")["qty"], 2)

    def test_a_nota_diz_a_frase_dele_os_numeros_e_o_porque(self):
        cfg = json.loads(CONFIG_REAL.read_text(encoding="utf-8"))
        nota = cfg["_foil_nota"]
        for pedaco in ("2 contagens separadas", "non-foil", "2026-09-27",
                       "47 impressões", "48 cópias", "HÁBITO DE MARCAÇÃO",
                       "conta_para_valor", "7 802,52 €", "foil.alvo"):
            self.assertIn(pedaco, nota, pedaco)

    def test_a_nota_diz_que_o_valor_nao_mudou(self):
        cfg = json.loads(CONFIG_REAL.read_text(encoding="utf-8"))
        self.assertIn("O VALOR NÃO MUDOU", cfg["_foil_nota"])


# ---------------------------------------------------------------------------
# 9. A INTERFACE
# ---------------------------------------------------------------------------


class TestAInterface(Base):
    def test_o_app_js_le_o_alvo_de_foil_e_escreve_foil_M_de_T(self):
        js = APP.read_text(encoding="utf-8")
        self.assertIn("foilAlvo", js)
        self.assertIn("pr.foil_target", js)
        self.assertIn("foil <b class=\"fo\">", js)

    def test_o_app_js_ja_nao_soma_as_duas_contagens_no_tile(self):
        """A linha dizia «2 normais · 1 foil = 3». Era a soma que escondia a
        falta, e não pode voltar."""
        js = APP.read_text(encoding="utf-8")
        linha = js.split("function foilLinha(")[1].split("\n}")[0]
        self.assertNotIn("normais ·", linha)
        self.assertNotIn("norm + f", linha)

    def test_os_dois_steppers_continuam_no_tile(self):
        js = APP.read_text(encoding="utf-8")
        self.assertIn('data-act="1"', js)      # o `+` das normais
        self.assertIn('data-foil="1"', js)     # o `+` das foils
        self.assertIn('data-act="-1"', js)
        self.assertIn('data-foil="-1"', js)
        self.assertIn("api/foil/ajustar", js)

    def test_o_css_separa_a_linha_de_foil_a_vista(self):
        css = CSS.read_text(encoding="utf-8")
        bloco = css.split(".foil-linha {")[1].split("}")[0]
        self.assertIn("border-top", bloco)
        self.assertIn(".foil-linha.is-done", css)

    def test_a_ajuda_da_coleccao_ja_nao_diz_que_as_foils_contam_para_os_alvos(self):
        js = APP.read_text(encoding="utf-8")
        self.assertIn("duas contagens separadas", js)
        self.assertNotIn("São independentes e somam-se: 3 normais e 3", js)

    def test_a_LINHA_RENDERIZADA_no_node_diz_foil_1_de_3_e_nao_soma(self):
        """Corre o `foilLinha` do `app.js` a sério, no node, com o caso dele.

        Não é um `assertIn` no ficheiro: é o HTML que sai. O que se exige é que a
        linha diga a contagem de FOIL contra o alvo dela e que o número das
        normais (2) e o total somado (3) **não apareçam lá** — é a soma que lhe
        escondia a falta.
        """
        node = shutil.which("node")
        if not node:
            self.skipTest("sem node")
        js = APP.read_text(encoding="utf-8")
        # As três funções de que a linha precisa, e a própria.
        trechos = []
        for nome in ("function foilLimite(", "function foilLinha(",
                     "function foilPrecoTxt(", "function foilContamTxt("):
            i = js.index(nome)
            trechos.append(js[i:js.index("\n}", i) + 2])
        harness = "\n".join(trechos) + """
const state = {
  editable: true,
  foilOk: new Set(['p']),
  foil: new Map([['p', 1]]),
  foilAlvo: new Map([['p', 3]]),
  preco: new Map(), precoFoil: new Map(),
  index: { foil: { limite: 9999, conta_para_coleccao: false, conta_para_valor: true } },
};
function eur(c) { return (c / 100).toFixed(2) + ' \\u20ac'; }
process.stdout.write(foilLinha('p'));
"""
        r = subprocess.run([node, "-e", harness], capture_output=True, text=True,
                           encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)
        html = r.stdout
        self.assertIn("foil", html)
        self.assertIn(">1<", html, "o que ele TEM em foil")
        self.assertIn("/3", html, "o alvo de foil, ao lado")
        # O TEXTO QUE SE VÊ, sem o `title` (que explica a separação e pode — e
        # deve — nomear as normais) e sem os `aria-label` dos botões.
        visivel = re.sub(r'\s(?:title|aria-label)="[^"]*"', "", html)
        self.assertNotIn("normais", visivel, "as normais estão no crachá, não aqui")
        self.assertNotIn("= 3", visivel, "o total somado saiu")
        self.assertNotIn(">2<", visivel, "o número das normais não aparece na linha")
        # E os dois botões continuam lá.
        self.assertIn('data-foil="1"', html)
        self.assertIn('data-foil="-1"', html)


if __name__ == "__main__":
    unittest.main()

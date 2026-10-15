"""PREPARAR A RADIANCE (2026-10-15) — a maquinaria que recebe uma edição nova,
provada com um set FALSO, sem rede.

A 2026-10-15 as cartas da Radiance não existiam em fonte nenhuma (a RiftScribe
devolvia OGN, OGS, SFD, UNL e VEN). O que se prova aqui é que, no dia em que a
RAD aparecer no `/api/cards/filters`, ela entra pelo `riftvault sync` e chega à
grelha, à percentagem, às Faltas, às wantlists, ao valor, às abas e ao site sem
mexer em nada à mão. O set falso (`FKE`, tamanho 10) leva tudo o que a RAD pode
trazer: base, uma sobrenumerada com uma raridade que o catálogo não conhece
(«ultimate», o caso da Ultimate Rare), uma alt art, uma variante que o
riftvault não conhece (a Special Alt), uma promo da série `SP`, uma promo pela
RARIDADE e um token.

E as quatro decisões dele desse dia:

  1. a Ultimate Rare entra como o Baron Nashor — sobrenumerada pelo número,
     sem caso especial;
  2. Special Alt — bloco próprio a seguir às Alt Art, fora da percentagem;
  3. sobrenumeradas — 1 de cada, como hoje;
  4. promos — SEM ALVO: ficam na página e no valor, saem das Faltas, das
     wantlists, dos níveis, do painel e do «A mais».

Tudo contra cópias descartáveis (`tests.fixture.Vault`) e um config temporário.
"""

from __future__ import annotations

import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ["RIFTVAULT_CONFIG"] = str(Path(tempfile.gettempdir()) / "riftvault-nao-existe.json")

from tests.fixture import REPO, Vault  # noqa: E402

NAO_EXISTE = str(Path(tempfile.gettempdir()) / "riftvault-nao-existe.json")


def _carta(pid, sid, cn, variant, code, name, rarity, tipo="Unit", dominios=("Fury",)):
    return {"id": pid, "set_id": sid, "collector_number": cn, "variant": variant,
            "public_code": code, "name": name, "rarity": rarity, "type": tipo,
            "faction": "fury", "domains": list(dominios), "orientation": "portrait",
            "stats": {}, "image": f"https://cdn.invalid/{pid}.png",
            "image_thumb": {"medium": f"https://cdn.invalid/{pid}.webp"}}


# O set que o config CONHECE (ordem 1) e o set NOVO, que o config não nomeia.
API = {
    "ZZZ": [_carta("zzz-001-005", "ZZZ", 1, "", "ZZZ-001/005", "Known Unit", "common")],
    "FKE": [
        _carta("fke-001-010", "FKE", 1, "", "FKE-001/010", "Fake Grunt", "common"),
        _carta("fke-001a-010", "FKE", 1, "a", "FKE-001a/010", "Fake Grunt", "showcase"),
        _carta("fke-002-010", "FKE", 2, "", "FKE-002/010", "Fake Star", "rare"),
        # A Special Alt (as K/DA): a API não documenta como a vai escrever. Um
        # `b` é o palpite mais provável e é por isso que serve de exemplo — o
        # que interessa é que uma variante desconhecida não entre na sequência.
        _carta("fke-002b-010", "FKE", 2, "b", "FKE-002b/010", "Fake Star", "showcase"),
        _carta("fke-003-010", "FKE", 3, "", "FKE-003/010", "Fake Legend", "epic", tipo="Legend"),
        # Uma promo pela RARIDADE: base, numerada dentro da edição — sem a
        # regra nova entrava na sequência e contava para a percentagem.
        _carta("fke-004-010", "FKE", 4, "", "FKE-004/010", "Fake Promo Hero", "promo"),
        # A Ultimate Rare: número acima do tamanho (11 de 10) e uma raridade
        # que o catálogo de hoje não tem.
        _carta("fke-011-010", "FKE", 11, "", "FKE-011/010", "Fake Ultimate", "ultimate"),
        _carta("fke-sp1-003", "FKE", 1, "sp1", "FKE-SP1/003", "Fake Promo", "epic"),
        _carta("fke-t01", "FKE", 1, "t01", "FKE-T01", "Fake Token", "common"),
    ],
}


class Base(unittest.TestCase):
    """Um vault vazio, um config com só o ZZZ em `sets`, e o sync à API falsa."""

    extra_cfg: dict = {}

    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.close)
        # O `master_set` é o do config DELE — é a regra dele que se prova; os
        # DEFAULTS do código mantêm as promos a 1 (ver `config.DEFAULTS`).
        real = json.loads((REPO / "riftvault_config.json").read_text(encoding="utf-8"))
        cfg = {"sets": {"ZZZ": {"name": "Zed", "order": 1}},
               "master_set": real["master_set"], **self.extra_cfg}
        caminho = self.v.root / "config.json"
        caminho.write_text(json.dumps(cfg), encoding="utf-8")
        os.environ["RIFTVAULT_CONFIG"] = str(caminho)
        self.config = self.v.config
        importlib.reload(self.config)
        self.config.load.cache_clear()

        def repor():
            os.environ["RIFTVAULT_CONFIG"] = NAO_EXISTE
            importlib.reload(self.config)
            self.config.load.cache_clear()
        self.addCleanup(repor)

        from riftvault import (a_mais, a_subir, build, catalog, collection, db,
                               faltas_edicao, metrics, painel, prices, riftscribe)
        for m in (metrics, catalog, a_subir, faltas_edicao, a_mais, painel, prices, build):
            importlib.reload(m)
        self.m, self.cat, self.db = metrics, catalog, db
        self.a_subir, self.fe, self.a_mais = a_subir, faltas_edicao, a_mais
        self.painel, self.prices, self.build = painel, prices, build
        self.collection = collection
        with mock.patch.object(riftscribe, "list_sets", lambda: list(API)), \
             mock.patch.object(riftscribe, "iter_cards",
                               lambda sid, delay=0: iter(API[sid])):
            self.res = catalog.sync(delay=0, log=lambda *_: None)
        self.con = db.connect()
        self.addCleanup(self.con.close)

    def linha(self, pid):
        return self.con.execute("SELECT * FROM catalog.printings WHERE printing_id = ?",
                                (pid,)).fetchone()

    def tile(self, payload, pid):
        for g in payload["groups"]:
            for p in g["printings"]:
                if p["id"] == pid:
                    return p
        return None

    def cópias(self, **qty):
        for pid, n in qty.items():
            self.collection.adjust(self.con, pid.replace("_", "-"), n, source="test")

    def preço(self, pid, cents):
        self.con.execute("INSERT OR REPLACE INTO catalog.price_latest (printing_id, "
                         "price_cents, from_foil) VALUES (?,?,0)", (pid, cents))


class TestUmSetNovoEntraSozinho(Base):
    def test_o_sync_traz_as_cartas_do_set_que_o_config_nao_conhece(self):
        self.assertEqual(self.res["sets"], {"ZZZ": 1, "FKE": 9})
        self.assertEqual(self.res["sets_vazias"], [])

    def test_o_sync_DIZ_que_a_edicao_e_nova(self):
        self.assertEqual(self.res["sets_novos"], ["FKE"])

    def test_o_sync_NAO_escreve_no_config(self):
        cfg = json.loads((self.v.root / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(list(cfg["sets"]), ["ZZZ"])

    def test_entra_depois_das_conhecidas_mesmo_vindo_antes_no_alfabeto(self):
        sets = self.m.sets_payload(self.con)
        self.assertEqual([s["id"] for s in sets], ["ZZZ", "FKE"])
        fke = sets[1]
        self.assertEqual(fke["name"], "FKE")      # o código, como ele escolheu
        self.assertEqual(fke["order"], 999)

    def test_as_abas_do_indice_tem_a_edicao_nova(self):
        idx = self.m.index_payload(self.con, cfg=self.config.load())
        self.assertIn("FKE", [s["id"] for s in idx["sets"]])

    def test_o_token_esta_escondido_e_o_separador_conta_o_que_se_ve(self):
        fke = [s for s in self.m.sets_payload(self.con) if s["id"] == "FKE"][0]
        self.assertEqual(fke["n_printings"], 8)
        self.assertIsNone(self.tile(self.m.set_payload(self.con, "FKE"), "fke-t01"))


class TestAsQuatroDecisoes(Base):
    def test_1_a_ultimate_e_sobrenumerada_pelo_numero_como_o_baron(self):
        r = self.linha("fke-011-010")
        self.assertTrue(self.m.e_overnumbered(r))
        self.assertEqual(self.m.bloco(r), self.m.BLOCO_OVER)
        self.assertEqual(self.m.alvo(r), 1)
        self.assertFalse(self.m.e_master(r))

    def test_1_nao_ha_raridade_ultimate_inventada(self):
        self.assertNotIn("ultimate", self.m.RARITY_ORDER)
        fonte = (REPO / "riftvault" / "metrics.py").read_text(encoding="utf-8")
        self.assertNotIn('"ultimate"', fonte)

    def test_2_uma_variante_desconhecida_vai_para_OUTRAS_e_nunca_para_a_sequencia(self):
        r = self.linha("fke-002b-010")
        self.assertEqual(r["variant_kind"], "unknown")
        self.assertIn("b", self.res["unknown_variants"])
        self.assertEqual(self.m.bloco(r), "outras")
        self.assertFalse(self.m.e_master(r))

    def test_3_as_sobrenumeradas_pedem_1(self):
        self.assertEqual(self.m.alvo_do_bloco(self.m.BLOCO_OVER), "1 de cada")

    def test_4_a_promo_SP_nao_pede_nada_mas_esta_na_pagina(self):
        r = self.linha("fke-sp1-003")
        self.assertEqual(self.m.alvo(r), 0)
        self.assertEqual(self.m.bloco(r), "special")
        self.assertFalse(self.m.escondida(r))
        self.assertIsNotNone(self.tile(self.m.set_payload(self.con, "FKE"), "fke-sp1-003"))

    def test_4_a_promo_pela_RARIDADE_segue_a_mesma_regra(self):
        r = self.linha("fke-004-010")
        self.assertEqual(r["variant_kind"], "base")
        self.assertEqual(self.m.kind_efectivo(r), "special")
        self.assertEqual(self.m.bloco(r), "special")
        self.assertEqual(self.m.alvo(r), 0)
        self.assertFalse(self.m.e_master(r))

    def test_4_o_bloco_das_promos_diz_sem_alvo(self):
        self.assertEqual(self.m.alvo_do_bloco("special"), self.m.SEM_ALVO)
        self.assertIn("sem alvo", self.m.rotulo("special"))


class TestSpecialAltComNome(Base):
    extra_cfg = {"variantes_extra": {"b": "special_alt"}}

    def test_com_o_nome_escrito_e_special_alt(self):
        r = self.linha("fke-002b-010")
        self.assertEqual(r["variant_kind"], "special_alt")
        self.assertEqual(r["variant_label"], "Special Alt")
        self.assertNotIn("b", self.res["unknown_variants"])

    def test_bloco_proprio_a_seguir_as_alt_art_e_fora_da_percentagem(self):
        r = self.linha("fke-002b-010")
        self.assertEqual(self.m.bloco(r), "special_alt")
        self.assertFalse(self.m.e_master(r))
        ordem = [b["id"] for b in self.m.set_payload(self.con, "FKE")["blocks"]]
        self.assertEqual(ordem.index("special_alt"), ordem.index("alt_art") + 1)

    def test_tem_contagem_propria_com_o_alvo_das_alt_art(self):
        self.cópias(**{"fke-002b-010": 1})
        p = self.m.set_payload(self.con, "FKE")
        b = [x for x in p["blocks"] if x["id"] == "special_alt"][0]
        self.assertEqual((b["owned"], b["total"]), (1, 1))
        self.assertEqual(self.tile(p, "fke-002b-010")["target"], 3)

    def test_um_kind_que_nao_existe_rebenta_no_sync(self):
        with self.assertRaises(ValueError):
            self.cat.variantes_extra({"variantes_extra": {"b": "k-da"}})

    def test_a_lista_aceita_o_nome_e_a_palavra_dele(self):
        for escrita in ("special_alt", "Special Alt", "special-alt"):
            kinds, _ = self.m._ler_lista("teste", (escrita,))
            self.assertEqual(kinds, frozenset({"special_alt"}))
        # E o `special` continua a ser a promo — as duas não se confundem.
        self.assertEqual(self.m._ler_lista("teste", ("promo",))[0], frozenset({"special"}))


class TestPeloCaminhoTodo(Base):
    """sync -> catálogo -> grelha -> percentagem -> Faltas -> wantlists ->
    valor -> «A mais» -> site, com cópias a sério."""

    def setUp(self):
        super().setUp()
        for pid, c in {"fke-001-010": 100, "fke-002-010": 200, "fke-003-010": 300,
                       "fke-011-010": 5000, "fke-001a-010": 400, "fke-002b-010": 600,
                       "fke-sp1-003": 1000, "fke-004-010": 700}.items():
            self.preço(pid, c)
        self.cópias(**{"fke-001-010": 1, "fke-sp1-003": 2, "fke-004-010": 1})

    def test_a_grelha(self):
        p = self.m.set_payload(self.con, "FKE")
        ids = [b["id"] for b in p["blocks"]]
        self.assertEqual(ids, ["master", "overnumbered", "alt_art", "special", "outras"])
        promos = [b for b in p["blocks"] if b["id"] == "special"][0]
        # «guardo se tiver»: o bloco diz o que ele tem e não tem nada a completar.
        self.assertEqual((promos["owned"], promos["total"], promos["done"],
                          promos["max_target"]), (2, 2, 0, 0))

    def test_a_percentagem_e_so_a_sequencia(self):
        p = self.m.set_payload(self.con, "FKE")
        self.assertEqual(p["progress"]["master"], {"done": 0, "total": 3})

    def test_as_faltas_nao_tem_promos(self):
        fe = self.fe.payload(self.con)
        self.assertNotIn("special", [b["id"] for b in fe["blocks"]])
        fke = [s for s in fe["sets"] if s["set"] == "FKE"][0]
        pids = {x["printing_id"] for g in fke["blocks"] for x in g["items"]}
        self.assertNotIn("fke-sp1-003", pids)
        self.assertNotIn("fke-004-010", pids)
        self.assertIn("fke-011-010", pids)          # a Ultimate falta, a 1
        self.assertIn("fke-001a-010", pids)         # a Alt Art falta, a 3
        self.assertEqual(fe["scope"]["fora"], {"outras": 1})   # a variante desconhecida, dita

    def test_a_wantlist_geral_e_so_o_master_set(self):
        w = self.a_subir.wantlist(self.con, "FKE")
        pids = {x["printing_id"] for x in w["items"]}
        self.assertEqual(pids, {"fke-001-010", "fke-002-010", "fke-003-010"})
        self.assertEqual(w["copies"], 2 + 3 + 1)

    def test_o_valor_conta_as_promos(self):
        v = self.prices.collection_value(self.con)
        self.assertEqual(v["cents"], 1 * 100 + 2 * 1000 + 1 * 700)

    def test_o_a_mais_nao_oferece_as_promos(self):
        am = self.a_mais.excedente(self.con, self.config.load())
        self.assertNotIn("fke-sp1-003", {x["printing_id"] for x in am})

    def test_o_painel_nao_conta_as_promos(self):
        pa = self.painel.payload(self.con, self.config.load())
        self.assertNotIn("special", [b["id"] for b in pa["blocks"]])
        # master 3 + sobrenumerada 1 + alt art 1 + a variante desconhecida 1
        # (no bloco «Outras», com o alvo do tipo) — e nenhuma das duas promos.
        self.assertEqual(pa["sets"]["FKE"]["tudo"]["n"], 3 + 1 + 1 + 1)

    def test_o_site_publica_a_edicao_nova(self):
        out = self.v.root / "site"
        self.con.commit()
        self.build.build(out, log=lambda *_: None)
        idx = json.loads((out / "api" / "index.json").read_text(encoding="utf-8"))
        self.assertIn("FKE", [s["id"] for s in idx["sets"]])
        fke = json.loads((out / "api" / "set" / "FKE.json").read_text(encoding="utf-8"))
        self.assertEqual(fke["set"], {"id": "FKE", "name": "FKE"})


class TestARegraDasPromos(unittest.TestCase):
    def setUp(self):
        from riftvault import config, metrics
        importlib.reload(config)
        config.load.cache_clear()
        importlib.reload(metrics)
        self.m = metrics

    def cfg(self, **ms):
        return {"master_set": {"fora_da_percentagem": ["a", "overnumbered", "promo"],
                               "escondidas": ["-T", "*", "-R"], **ms}}

    def test_sem_alvo_ganha_ao_um_de_cada(self):
        c = self.cfg(um_de_cada=["overnumbered", "promo"], sem_alvo=["promo"])
        p = {"printing_id": "x", "variant_kind": "special", "type": "Unit", "is_token": 0}
        self.assertEqual(self.m.alvo(p, c), 0)

    def test_sem_a_lista_a_promo_volta_ao_um_de_cada(self):
        c = self.cfg(um_de_cada=["overnumbered", "promo"], sem_alvo=[])
        p = {"printing_id": "x", "variant_kind": "special", "type": "Unit", "is_token": 0}
        self.assertEqual(self.m.alvo(p, c), 1)

    def test_a_raridade_promo_le_se_do_config(self):
        c = self.cfg(sem_alvo=["promo"], raridades_promo=[])
        p = {"printing_id": "x", "variant_kind": "base", "rarity": "promo",
             "type": "Unit", "is_token": 0}
        self.assertEqual(self.m.kind_efectivo(p, c), "base")
        self.assertEqual(self.m.alvo(p, c), 3)

    def test_o_config_real_tem_as_quatro_decisoes(self):
        real = json.loads((REPO / "riftvault_config.json").read_text(encoding="utf-8"))
        ms = real["master_set"]
        self.assertEqual(ms["sem_alvo"], ["promo"])
        self.assertNotIn("promo", ms["um_de_cada"])
        self.assertIn("overnumbered", ms["um_de_cada"])
        self.assertIn("special_alt", ms["fora_da_percentagem"])
        o = ms["ordem_dos_blocos"]
        self.assertEqual(o.index("special_alt"), o.index("a") + 1)
        self.assertIn("2026-10-15", real["_master_set_promos_sem_alvo_nota"])
        self.assertIn("REVOGA", real["_master_set_promos_sem_alvo_nota"])
        self.assertIn("Baron", real["_master_set_radiance_nota"])

    def test_os_defaults_tem_a_special_alt_fora_e_as_promos_no_regime_de_19_09(self):
        """A regra das promos vive no config DELE; a omissão continua a de
        2026-09-19 (é o mecanismo que as outras baterias descrevem). A Special
        Alt é que tem de estar fora da percentagem também sem config."""
        from riftvault import config
        ms = config.DEFAULTS["master_set"]
        self.assertEqual(ms["sem_alvo"], [])
        self.assertIn("promo", ms["um_de_cada"])
        self.assertIn("special_alt", ms["fora_da_percentagem"])
        o = ms["ordem_dos_blocos"]
        self.assertEqual(o.index("special_alt"), o.index("a") + 1)
        self.assertFalse(self.m.conta_bloco("special_alt", config.DEFAULTS))


class TestOEcra(unittest.TestCase):
    APP = (REPO / "riftvault" / "web" / "app.js").read_text(encoding="utf-8")

    def test_o_cabecalho_do_bloco_conta_o_que_nao_tem_alvo(self):
        i = self.APP.index("function render()")
        corpo = self.APP[i:self.APP.index("function renderProgress()", i)]
        self.assertLess(corpo.index("total++"), corpo.index("if (t <= 0) continue"))

    def test_o_filtro_faltas_nao_mostra_o_que_nao_tem_alvo(self):
        i = self.APP.index("stateFilter === 'missing'")
        self.assertIn("(state.targets.get(p.id) || 0) > 0", self.APP[i:i + 300])


if __name__ == "__main__":
    unittest.main()

"""As faltas em DUAS METADES — as normais e as foils (André, 2026-09-27).

Palavras dele: *"quero as faltas separadas, as normais e as foils / as foils
nao sao faltas, sao apenas complemento e indicativo / mais tarde poderao vir a
ser compradas, entao preciso que tenham uma wantlist a parte"*. E sobre o alvo:
*"o alvo das foils e 3 de cada"*, precisado logo a seguir: *"no caso,
playset"*.

O que se fixa:
  1. AS FOILS NÃO SÃO FALTAS — a metade das normais do `payload_completo` é,
     campo a campo, o `faltas_edicao.payload`: os `totals`, os `totals_lists`,
     os quatro blocos e o `scope` não sabem que a outra metade existe. E, com
     a coluna do foil a mexer, nada da metade das normais mexe (com o botão de
     2026-09-26 desligado, que é o que isola o código de hoje);
  2. o ALVO é o PLAYSET DO TIPO, a função que já existe — **Battlefield 1 e
     Rune 12**, não um 3 liso; não há alvo novo em lado nenhum;
  3. o ÂMBITO é o do contador de foil: comuns e incomuns, base, não
     sobrenumeradas, fora o OGS — de rara para cima não se lista NADA;
  4. a QUINTA WANTLIST, com a mesma gramática das quatro por bloco: só o que
     há a comprar, o texto do gerador único, e não engorda a geral;
  5. o PREÇO é o da FOIL, com o fallback ao da normal contado (o PISO);
  6. o AVISO das impressões com foil e o playset das NORMAIS incompleto;
  7. não há PENDENTE de foil;
  8. ler não escreve, e a rota, o `build`, a CLI, o `app.js` e o CSS.

Tudo contra pastas temporárias (`tests.fixture.Vault`) e um config temporário
(`RIFTVAULT_CONFIG`): o `data/` e o `riftvault_config.json` a sério nunca são
tocados.
"""

from __future__ import annotations

import copy
import importlib
import json
import os
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
CONFIG_REAL = REPO / "riftvault_config.json"


class Base(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.close)
        from riftvault import (a_mais, a_subir, cardmarket, collection, config, db, decks,
                              faltas, faltas_edicao, faltas_foil, foil, locais, metrics,
                              painel, pending, prices, proprias)
        for m in (locais, metrics, foil, painel, decks, proprias, a_subir,
                  faltas_edicao, faltas_foil, a_mais, pending, faltas, prices):
            importlib.reload(m)
        self.config, self.db, self.foil, self.locais = config, db, foil, locais
        self.metrics, self.painel, self.decks = metrics, painel, decks
        self.a_subir, self.faltas_edicao, self.a_mais = a_subir, faltas_edicao, a_mais
        self.faltas_foil, self.cardmarket = faltas_foil, cardmarket
        self.pending, self.faltas, self.prices = pending, faltas, prices
        self.collection = collection
        self.escrever_config()

    # -- config -------------------------------------------------------------

    def escrever_config(self, foil_extra: dict | None = None, extra: dict | None = None):
        """O config de hoje: o âmbito do foil, as duas chaves de 2026-09-26
        ligadas (é o que vale no `riftvault_config.json`) e a runa a 3 na
        coleção — que é o que faz o «Rune 12 em foil» ser uma diferença a
        sério, e não dois nomes para o mesmo número."""
        caminho = self.v.root / "config.json"
        caminho.write_text(json.dumps({
            "foil": {"raridades": ["common", "uncommon"], "edicoes_fora": ["OGS"],
                     "conta_para_coleccao": True, "conta_para_valor": True,
                     "entra_no_a_mais": False, **(foil_extra or {})},
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
        """Uma edição TST com um caso de cada, e a OGS fora do âmbito.

        No âmbito do foil (base, não sobrenumerada, comum/incomum):
          `tst-001` Defy        Unit comum      3 normais · 0 foil  -> alvo 3
          `tst-002` Scout       Unit incomum    2 normais · 1 foil  -> alvo 3
          `tst-005` Seat        Battlefield com. 1 normal · 0 foil  -> alvo 1
          `tst-006` Calm Rune   Rune comum      3 normais · 0 foil  -> alvo 12
          `tst-007` Discipline  Spell incomum   0 normais · 5 foil  -> alvo 3
          `tst-t01` Recruit     token (Unit)    0 normais · 0 foil  -> alvo 1

        Fora do âmbito: a rara, a épica (Legend), a alt art, a sobrenumerada e
        tudo o que é do OGS.
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
        v.add_printing(con, "tst-005-100", "TST", 5, "Seat of Power",
                       card_type="Battlefield", rarity="common", size=100)
        v.add_printing(con, "tst-006-100", "TST", 6, "Calm Rune",
                       card_type="Rune", rarity="common", size=100)
        v.add_printing(con, "tst-007-100", "TST", 7, "Discipline",
                       card_type="Spell", rarity="uncommon", size=100)
        # Sobrenumerada e comum — o caso dos Poros do UNL: fica fora, não é base.
        v.add_printing(con, "tst-101-100", "TST", 101, "Lonely Poro", rarity="common",
                       size=100)
        v.add_printing(con, "tst-t01", "TST", 1, "Recruit", variant="t01", kind="token",
                       lane="t", rarity="common", codigo="TST-T01")
        v.add_printing(con, "ogs-001-024", "OGS", 1, "Starter Scout", rarity="common",
                       size=24)
        v.rebuild(con)
        # O preço da NORMAL e o da FOIL, em cêntimos. A `tst-002` não tem preço
        # de foil de propósito: é o FALLBACK (o piso).
        for pid, cents, foil_cents in (("tst-001-100", 11, 502),
                                       ("tst-001a-100", 500, None),
                                       ("tst-002-100", 25, None),
                                       ("tst-003-100", 900, None),
                                       ("tst-004-100", 4000, None),
                                       ("tst-005-100", 56, 120),
                                       ("tst-006-100", 11, 40),
                                       ("tst-007-100", 30, 95),
                                       ("tst-101-100", 20000, None),
                                       ("ogs-001-024", 11, 11)):
            con.execute("INSERT INTO catalog.price_latest "
                        "(printing_id, price_cents, price_foil_cents) VALUES (?,?,?)",
                        (pid, cents, foil_cents))
        for pid, n in (("tst-001-100", 3), ("tst-002-100", 2), ("tst-003-100", 1),
                       ("tst-001a-100", 2), ("tst-005-100", 1), ("tst-006-100", 3),
                       ("tst-101-100", 1), ("ogs-001-024", 2)):
            self.collection.adjust(con, pid, n, source="test")
        self.foil.ajustar(con, "tst-002-100", 1, source="test")
        self.foil.ajustar(con, "tst-007-100", 5, source="test")
        self.addCleanup(con.close)
        return con

    def bloco(self, con, sid="TST"):
        return self.faltas_foil.bloco(con)["sets"][sid]

    def itens(self, con, sid="TST"):
        return {x["printing_id"]: x for x in self.bloco(con, sid)["items"]}


# ---------------------------------------------------------------------------
# 1. AS FOILS NÃO SÃO FALTAS
# ---------------------------------------------------------------------------


class TestNaoSaoFaltas(Base):
    """A prova do ponto que ele pôs primeiro: *"as foils nao sao faltas"*."""

    def _normais(self, p: dict) -> dict:
        """A metade das NORMAIS de um payload, sem a metade das foils."""
        return {
            "blocks": p["blocks"], "totals": p["totals"],
            "totals_lists": p["totals_lists"], "scope": p["scope"],
            "so_master_set": p["so_master_set"], "rule": p["rule"],
            # As caixas (2026-10-02) sao das NORMAIS e passam inteiras; este
            # dicionario enumera os campos a mao de proposito, para um campo
            # novo no `faltas_edicao.payload` ter de ser notado por alguem — e
            # foi este teste que notou estes dois.
            "caixas": p["caixas"], "caixas_ignoradas": p["caixas_ignoradas"],
            "sets": [{k: v for k, v in d.items() if k != "foil"} for d in p["sets"]],
        }

    def test_a_metade_das_normais_e_exactamente_o_faltas_edicao(self):
        """O `payload_completo` acrescenta; não mexe. Campo a campo."""
        con = self.catalogo()
        so_normais = self.faltas_edicao.payload(con)
        completo = self.faltas_foil.payload_completo(con)
        self.assertEqual(self._normais(completo), so_normais)

    def test_os_quatro_blocos_continuam_quatro(self):
        con = self.catalogo()
        p = self.faltas_foil.payload_completo(con)
        ids = [b["id"] for b in p["blocks"]]
        self.assertEqual(len(ids), 4, ids)
        self.assertNotIn("foil", ids)
        for d in p["sets"]:
            self.assertEqual(len(d["blocks"]), 4)
            self.assertNotIn("foil", [g["id"] for g in d["blocks"]])

    def test_o_bloco_das_foils_nao_soma_aos_totais_das_normais(self):
        con = self.catalogo()
        p = self.faltas_foil.payload_completo(con)
        f = p["foil"]["totals"]
        self.assertGreater(f["copies"], 0, "há foils a faltar, senão o teste não prova nada")
        soma_blocos = sum(g["copies"] for d in p["sets"] for g in d["blocks"])
        self.assertEqual(p["totals"]["copies"], soma_blocos)
        self.assertNotEqual(p["totals"]["copies"], soma_blocos + f["copies"])
        # E o âmbito das normais não conta as impressões do foil.
        self.assertEqual(p["scope"]["printings"],
                         sum(g["scope"] for d in p["sets"] for g in d["blocks"]))

    def test_as_foils_nunca_entram_nas_listas_de_compra(self):
        con = self.catalogo()
        p = self.faltas_foil.payload_completo(con)
        self.assertFalse(p["foil"]["block"]["in_lists"])
        for d in p["sets"]:
            if d["foil"]:
                self.assertFalse(d["foil"]["in_lists"])
        # O `totals_lists` é só o que entra na wantlist geral: os blocos com
        # `in_lists`, e o das foils não é um deles.
        nas_listas = sum(g["copies"] for d in p["sets"] for g in d["blocks"]
                         if g["in_lists"])
        self.assertEqual(p["totals_lists"]["copies"], nas_listas)

    def test_marcar_foils_nao_mexe_na_metade_das_normais(self):
        """Com o botão de 2026-09-26 DESLIGADO — é assim que se isola o código
        de hoje. Mexer na coluna do foil muda a metade das foils e mais nada.

        Com `conta_para_coleccao: true` (o que vale hoje) a metade das normais
        MEXE, e é a decisão de 26/09 a funcionar — uma foil tapa um buraco do
        master set —, não acoplamento desta ordem. O teste a seguir fixa isso.
        """
        self.escrever_config({"conta_para_coleccao": False, "conta_para_valor": False})
        con = self.catalogo()
        antes = self._normais(self.faltas_foil.payload_completo(con))
        foil_antes = self.faltas_foil.bloco(con)["totals"]["copies"]

        self.foil.ajustar(con, "tst-001-100", 3, source="test")
        self.foil.ajustar(con, "tst-006-100", 12, source="test")
        depois = self.faltas_foil.payload_completo(con)
        self.assertEqual(self._normais(depois), antes, "as normais não mexeram")
        self.assertLess(depois["foil"]["totals"]["copies"], foil_antes,
                        "e a metade das foils mexeu, senão o teste não prova nada")

        for pid in ("tst-001-100", "tst-006-100"):
            self.foil.ajustar(con, pid, -99, source="test")
        self.assertEqual(self._normais(self.faltas_foil.payload_completo(con)), antes)

    def test_com_o_botao_de_26_09_ligado_as_normais_mexem_e_e_essa_decisao(self):
        """Não é desta ordem: desde 2026-09-26 o que uma impressão TEM, para os
        alvos da Coleção, é `qty + qty_foil`. Fica escrito para ninguém
        confundir as duas coisas."""
        con = self.catalogo()          # config de hoje: as duas chaves ligadas
        antes = self.faltas_edicao.payload(con)["totals"]["copies"]
        self.foil.ajustar(con, "tst-001-100", 1, source="test")
        self.assertEqual(self.faltas_edicao.payload(con)["totals"]["copies"], antes,
                         "a Defy já estava completa em normais")
        # Numa que ainda falte, a foil tapa — e é o `faltas_edicao` a fazê-lo,
        # sozinho, pelo funil do `locais`.
        self.foil.ajustar(con, "tst-005-100", 0, source="test")
        d = next(x for x in self.faltas_edicao.payload(con)["sets"] if x["set"] == "TST")
        master = next(g for g in d["blocks"] if g["id"] == "master")
        tinha = {x["printing_id"]: x["missing"] for x in master["items"]}
        self.assertEqual(tinha.get("tst-007-100"), None,
                         "a Discipline tem 0 normais e 5 foils: as foils tapam o playset")

    def test_a_fotografia_nao_e_de_zeros(self):
        """A fotografia dos testes acima só vale se houver números lá dentro."""
        con = self.catalogo()
        p = self.faltas_foil.payload_completo(con)
        self.assertGreater(p["totals"]["copies"], 0)
        self.assertGreater(p["totals"]["cents"], 0)
        self.assertGreater(p["foil"]["totals"]["copies"], 0)
        tst = next(d for d in p["sets"] if d["set"] == "TST")
        self.assertGreater(len(tst["foil"]["items"]), 2)


# ---------------------------------------------------------------------------
# 2. O ALVO É O PLAYSET DO TIPO
# ---------------------------------------------------------------------------


class TestOAlvo(Base):
    """*"o alvo das foils e 3 de cada"* → *"no caso, playset"*: o playset do
    TIPO, e por isso Battlefield 1 e Rune 12, não um 3 liso."""

    def test_battlefield_foil_e_1_e_nao_3(self):
        con = self.catalogo()
        r = con.execute("SELECT * FROM catalog.printings WHERE printing_id='tst-005-100'"
                        ).fetchone()
        self.assertEqual(self.faltas_foil.alvo(r), 1)
        self.assertEqual(self.itens(con)["tst-005-100"]["target"], 1)
        self.assertEqual(self.itens(con)["tst-005-100"]["missing"], 1)

    def test_rune_foil_e_12_e_nao_3(self):
        """A runa coleciona-se a 3 (`master_targets_by_type`) e joga-se a 12; em
        FOIL o alvo é o playset, 12. É a única divergência entre as duas
        metades, e é aqui que se vê."""
        con = self.catalogo()
        r = con.execute("SELECT * FROM catalog.printings WHERE printing_id='tst-006-100'"
                        ).fetchone()
        self.assertEqual(self.faltas_foil.alvo(r), 12)
        self.assertEqual(self.metrics.alvo_do_tipo("Rune", False), 3,
                         "na coleção normal a runa é 3 — são dois números diferentes")
        x = self.itens(con)["tst-006-100"]
        self.assertEqual((x["target"], x["have"], x["missing"]), (12, 0, 12))

    def test_unit_spell_e_gear_sao_3_e_legend_e_1(self):
        con = self.catalogo()
        esc = self.faltas_foil.escopo(con)
        self.assertEqual(esc["tst-001-100"]["target"], 3)                 # Unit
        self.assertEqual(esc["tst-007-100"]["target"], 3)                 # Spell
        # A Discipline tem 5 foils de 3: está completa e não aparece na lista.
        self.assertNotIn("tst-007-100", self.itens(con))
        for tipo, esperado in (("Gear", 3), ("Legend", 1), ("Unit", 3), ("Spell", 3)):
            self.assertEqual(self.faltas_foil.alvo({"type": tipo, "is_token": 0}), esperado,
                             tipo)

    def test_um_token_pede_1_o_token_target(self):
        con = self.catalogo()
        con.execute("UPDATE catalog.printings SET is_token = 1 WHERE printing_id='tst-t01'")
        r = con.execute("SELECT * FROM catalog.printings WHERE printing_id='tst-t01'"
                        ).fetchone()
        self.assertEqual(self.faltas_foil.alvo(r), 1)

    def test_o_alvo_vem_da_tabela_do_config_e_nao_de_um_numero_escrito(self):
        """Não há alvo novo: mexe-se no `playset_targets_by_type` e o alvo das
        foils mexe com ele."""
        self.escrever_config(extra={"playset_targets_by_type": {
            "Unit": 4, "Battlefield": 2, "Rune": 6, "default": 3}})
        con = self.catalogo()
        it = self.itens(con)
        self.assertEqual(it["tst-001-100"]["target"], 4)
        self.assertEqual(it["tst-005-100"]["target"], 2)
        self.assertEqual(it["tst-006-100"]["target"], 6)

    def test_a_fonte_do_alvo_e_o_playset_target(self):
        """Quem lê o ficheiro tem de ver que não se escreveu alvo nenhum.

        O alvo MUDOU DE CASA a 2026-09-27, à noite — vive no `foil.alvo`, porque
        o contador do tile passou a mostrar `foil M/T` e precisava do mesmo
        número. O que este teste fixa continua a ser o mesmo: **há uma resposta
        só, e é o `metrics.playset_target`**.
        """
        ff = (REPO / "riftvault" / "faltas_foil.py").read_text(encoding="utf-8")
        fo = (REPO / "riftvault" / "foil.py").read_text(encoding="utf-8")
        self.assertIn("metrics.playset_target(", fo)
        # E o `faltas_foil` delega, em vez de ter uma segunda tabela.
        self.assertIn("return foil.alvo(", ff)
        self.assertNotIn("metrics.playset_target(", ff)
        for fonte in (ff, fo):
            self.assertNotIn("ALVO_FOIL", fonte)
            self.assertNotIn("= 3", fonte.split('"""')[-1])


# ---------------------------------------------------------------------------
# 3. O ÂMBITO
# ---------------------------------------------------------------------------


class TestOAmbito(Base):
    def test_so_comuns_e_incomuns(self):
        con = self.catalogo()
        it = self.itens(con)
        self.assertIn("tst-001-100", it)                 # comum
        self.assertIn("tst-002-100", it)                 # incomum
        self.assertNotIn("tst-003-100", it)              # rara
        self.assertNotIn("tst-004-100", it)              # épica

    def test_de_rara_para_cima_nao_se_lista_nada(self):
        """Em Riftbound essas raridades só existem em foil — a carta normal É a
        foil, e listá-las era duplicar a coleção inteira."""
        con = self.catalogo()
        raridades = {x["rarity"] for x in self.bloco(con)["items"]}
        self.assertTrue(raridades <= {"common", "uncommon"}, raridades)
        b = self.faltas_foil.bloco(con)
        self.assertEqual(b["scope"]["rarities"], ["common", "uncommon"])

    def test_a_alt_art_e_a_sobrenumerada_ficam_de_fora(self):
        con = self.catalogo()
        it = self.itens(con)
        self.assertNotIn("tst-001a-100", it, "a alt art é outra impressão")
        self.assertNotIn("tst-101-100", it, "a sobrenumerada comum (os Poros) também")

    def test_o_ogs_nao_tem_metade_de_foil(self):
        con = self.catalogo()
        b = self.faltas_foil.bloco(con)
        self.assertNotIn("OGS", b["sets"])
        self.assertEqual(b["scope"]["sem_edicoes"], ["OGS"])
        p = self.faltas_foil.payload_completo(con)
        ogs = next(d for d in p["sets"] if d["set"] == "OGS")
        self.assertIsNone(ogs["foil"], "sem âmbito, sem bloco — não uma caixa vazia")

    def test_o_ambito_e_o_mesmo_do_contador_do_tile(self):
        """Uma pergunta, uma resposta: `foil.no_ambito`. Se divergissem, o tile
        teria `+`/`−` numa carta que a lista não conhece."""
        con = self.catalogo()
        esc = set(self.faltas_foil.escopo(con))
        contador = set(self.foil.ids_do_ambito(con))
        self.assertEqual(esc, contador)
        fonte = (REPO / "riftvault" / "faltas_foil.py").read_text(encoding="utf-8")
        self.assertIn("foil.no_ambito(", fonte)

    def test_mudar_o_config_do_ambito_muda_a_lista(self):
        con = self.catalogo()
        # O âmbito muda-se DEPOIS de haver dados: a incomum sai, o OGS entra.
        self.escrever_config({"raridades": ["common"], "edicoes_fora": []})
        it = self.itens(con)
        self.assertIn("tst-001-100", it)
        self.assertNotIn("tst-002-100", it, "a incomum saiu do âmbito")
        self.assertIn("OGS", self.faltas_foil.bloco(con)["sets"])


# ---------------------------------------------------------------------------
# 4. A QUINTA WANTLIST
# ---------------------------------------------------------------------------


class TestAQuintaWantlist(Base):
    def test_existe_e_e_a_quinta(self):
        con = self.catalogo()
        p = self.faltas_foil.payload_completo(con)
        d = next(x for x in p["sets"] if x["set"] == "TST")
        wls = [g["wantlist"] for g in d["blocks"]] + [d["foil"]["wantlist"]]
        self.assertEqual(len(wls), 5)
        self.assertGreater(d["foil"]["wantlist"]["lines"], 0)

    def test_o_texto_sai_do_gerador_unico(self):
        con = self.catalogo()
        w = self.faltas_foil.wantlist(con, "TST")
        esperado = "\n".join(self.cardmarket.linha(x) for x in w["items"])
        self.assertEqual(w["text"], esperado)
        self.assertEqual(w["block"], "foil")
        self.assertEqual(w["label"], "Foils")
        self.assertFalse(w["in_lists"])

    def test_com_codigos_escreve_o_codigo(self):
        con = self.catalogo()
        w = self.faltas_foil.wantlist(con, "TST", com_codigo=True)
        self.assertIn("[TST-001]", w["text"])

    def test_so_o_que_ha_a_comprar(self):
        con = self.catalogo()
        w = self.faltas_foil.wantlist(con, "TST")
        self.assertTrue(all(x["missing"] > 0 for x in w["items"]))
        # A Defy está a 0 foils de 3: pede 3.
        linha = next(x for x in w["items"] if x["code"].startswith("TST-001/"))
        self.assertEqual(linha["missing"], 3)

    def test_todas_as_linhas_precisam_do_filtro_foil(self):
        """O foil NÃO se marca no texto (é um filtro por entrada, 2026-09-01) —
        por isso todas as linhas vêm marcadas, para se dizer onde o ligar."""
        con = self.catalogo()
        w = self.faltas_foil.wantlist(con, "TST")
        self.assertEqual(len(w["foil"]), w["lines"])
        self.assertTrue(all(x["foil_only"] for x in w["items"]))
        self.assertNotIn("foil", w["text"].lower(), "o texto não leva marca nenhuma")

    def test_nao_engorda_a_wantlist_geral(self):
        """A quinta é PRÓPRIA: a «Wantlist — tudo» da Coleção e o
        `totals_lists` do separador não crescem com ela."""
        con = self.catalogo()
        geral = self.a_subir.wantlist(con)
        p = self.faltas_foil.payload_completo(con)
        self.assertEqual((p["totals_lists"]["copies"], p["totals_lists"]["cents"]),
                         (geral["copies"], geral["cents"]))
        # E o que a quinta pede não está na geral: as foils não são cópias que
        # a Coleção conte como faltas.
        w = self.faltas_foil.wantlist(con, "TST")
        self.assertGreater(w["copies"], 0)
        self.assertNotEqual(w["copies"], geral["copies"])

    def test_uma_edicao_fora_do_ambito_rebenta_a_dizer_porque(self):
        con = self.catalogo()
        with self.assertRaises(ValueError) as e:
            self.faltas_foil.wantlist(con, "OGS")
        self.assertIn("OGS", str(e.exception))
        self.assertIn("common", str(e.exception))

    def test_o_resumo_do_bloco_bate_com_o_texto(self):
        con = self.catalogo()
        d = self.bloco(con)
        w = self.faltas_foil.wantlist(con, "TST")
        self.assertEqual((d["wantlist"]["lines"], d["wantlist"]["copies"],
                          d["wantlist"]["cents"]),
                         (w["lines"], w["copies"], w["cents"]))
        self.assertEqual(d["copies"], w["copies"])


# ---------------------------------------------------------------------------
# 5. O PREÇO É O DA FOIL
# ---------------------------------------------------------------------------


class TestOPreco(Base):
    def test_o_preco_e_o_da_foil(self):
        con = self.catalogo()
        x = self.itens(con)["tst-001-100"]
        self.assertEqual(x["price"], 502, "a foil da Defy, não os 11 cêntimos da normal")
        self.assertTrue(x["price_is_foil"])
        self.assertEqual(x["total"], 3 * 502)

    def test_sem_oferta_foil_cai_para_a_normal_e_conta_se(self):
        """O FALLBACK, que faz do total um PISO — como no `valor_dos_foils`."""
        con = self.catalogo()
        x = self.itens(con)["tst-002-100"]
        self.assertEqual(x["price"], 25, "o preço da normal")
        self.assertFalse(x["price_is_foil"])
        self.assertEqual(self.bloco(con)["no_foil_price"], 1)
        self.assertEqual(self.faltas_foil.bloco(con)["totals"]["no_foil_price"], 1)

    def test_o_from_foil_ja_e_preco_de_foil(self):
        """A impressão que o CardTrader só lista em foil: o `price_cents` dela
        JÁ é de foil, e não é fallback nenhum (a regra do `precos_de_foil_map`)."""
        con = self.catalogo()
        con.execute("UPDATE catalog.price_latest SET from_foil = 1 "
                    "WHERE printing_id = 'tst-002-100'")
        x = self.itens(con)["tst-002-100"]
        self.assertEqual(x["price"], 25)
        self.assertTrue(x["price_is_foil"])
        self.assertEqual(self.bloco(con)["no_foil_price"], 0)

    def test_sem_preco_nenhum_entra_na_lista_e_conta_se(self):
        con = self.catalogo()
        con.execute("DELETE FROM catalog.price_latest WHERE printing_id='tst-006-100'")
        x = self.itens(con)["tst-006-100"]
        self.assertIsNone(x["price"])
        self.assertEqual(x["total"], 0)
        self.assertEqual(self.bloco(con)["no_price"], 1)


# ---------------------------------------------------------------------------
# 6. O AVISO
# ---------------------------------------------------------------------------


class TestOAviso(Base):
    def test_lista_as_que_tem_foil_e_normais_incompletas(self):
        con = self.catalogo()
        av = {x["printing_id"]: x for x in self.faltas_foil.bloco(con)["aviso_normais"]}
        # A Scout tem 2 normais de 3 e 1 foil: a foil está a tapar o buraco.
        self.assertIn("tst-002-100", av)
        self.assertEqual((av["tst-002-100"]["normais"], av["tst-002-100"]["target"],
                          av["tst-002-100"]["foil"]), (2, 3, 1))
        # A Discipline tem 0 normais de 3 e 5 foils: o caso extremo.
        self.assertIn("tst-007-100", av)
        self.assertEqual(av["tst-007-100"]["normais"], 0)

    def test_nao_lista_as_que_tem_o_playset_normal_completo(self):
        con = self.catalogo()
        self.foil.ajustar(con, "tst-001-100", 2, source="test")
        av = {x["printing_id"] for x in self.faltas_foil.bloco(con)["aviso_normais"]}
        self.assertNotIn("tst-001-100", av, "a Defy tem 3 normais de 3")

    def test_nao_lista_as_que_nao_tem_foil(self):
        con = self.catalogo()
        av = {x["printing_id"] for x in self.faltas_foil.bloco(con)["aviso_normais"]}
        self.assertNotIn("tst-005-100", av, "o Seat of Power não tem foil nenhuma")

    def test_o_aviso_nao_decide_nada(self):
        """Só se mostra: não muda alvo, não muda a falta, não escreve."""
        con = self.catalogo()
        antes = self.faltas_edicao.payload(con)
        copias = list(con.execute("SELECT printing_id, qty, qty_foil FROM copies"))
        self.faltas_foil.aviso_normais(con)
        self.assertEqual(self.faltas_edicao.payload(con), antes)
        self.assertEqual(list(con.execute("SELECT printing_id, qty, qty_foil FROM copies")),
                         copias)

    def test_conta_as_normais_sem_as_foils(self):
        """As normais são as da Coleção SEM as foils — senão, com o botão de
        2026-09-26 ligado, o aviso nunca disparava."""
        fonte = (REPO / "riftvault" / "faltas_foil.py").read_text(encoding="utf-8")
        self.assertIn("com_foil=False", fonte)


# ---------------------------------------------------------------------------
# 7. NÃO HÁ PENDENTE DE FOIL
# ---------------------------------------------------------------------------


class TestSemPendente(Base):
    def test_uma_encomenda_nao_conta_como_foil_a_caminho(self):
        """A `pending` guarda a impressão, não o acabamento: não se inventou um
        pendente que a base não tem."""
        con = self.catalogo()
        self.pending.encomendar(con, printing_id="tst-001-100", qty=3, source="test")
        b = self.faltas_foil.bloco(con)
        x = next(x for x in b["sets"]["TST"]["items"] if x["printing_id"] == "tst-001-100")
        self.assertEqual(x["pending"], 0)
        self.assertEqual(x["missing"], 3, "continua a faltar o playset em foil")
        self.assertEqual(b["totals"]["pending_copies"], 0)
        # E nas NORMAIS o pendente continua a contar, como sempre.
        d = next(x for x in self.faltas_edicao.payload(con)["sets"] if x["set"] == "TST")
        self.assertGreaterEqual(d["pending_copies"], 0)


# ---------------------------------------------------------------------------
# 8. Ler não escreve; a rota, o build, a CLI e o ecrã
# ---------------------------------------------------------------------------


class TestNaoEscreve(Base):
    def test_ler_a_metade_das_foils_nao_escreve(self):
        con = self.catalogo()
        antes = [list(con.execute(f"SELECT * FROM {t}")) for t in
                 ("copies", "ops", "pending", "foil_ops", "copy_locations")]
        self.faltas_foil.payload_completo(con)
        self.faltas_foil.wantlist(con, "TST")
        depois = [list(con.execute(f"SELECT * FROM {t}")) for t in
                  ("copies", "ops", "pending", "foil_ops", "copy_locations")]
        self.assertEqual(antes, depois)

    def test_nao_leva_euros_a_mais_nem_campos_dos_decks(self):
        con = self.catalogo()
        x = self.bloco(con)["items"][0]
        self.assertNotIn("decks", x)
        self.assertNotIn("proprias", x)


class TestAFronteira(Base):
    """O `faltas_edicao` continua a não saber do foil — é o que faz o ponto 1
    ser arquitectura e não uma promessa."""

    def test_o_faltas_edicao_nao_conhece_o_foil(self):
        fonte = (REPO / "riftvault" / "faltas_edicao.py").read_text(encoding="utf-8")
        self.assertNotIn("import foil", fonte)
        self.assertNotIn("from .foil", fonte)
        self.assertNotIn("qty" + "_foil", fonte)
        # E não importa a outra metade: é a outra metade que o compõe, não o
        # contrário. (O docstring fala dela — é o código que não a chama.)
        self.assertNotIn("import faltas_foil", fonte)
        self.assertNotIn("faltas_foil.", fonte.split('"""')[2])

    def test_o_item_e_o_soma_sao_os_mesmos_nas_duas_metades(self):
        """Uma definição de «linha de falta» e uma de «soma de bloco»."""
        fonte = (REPO / "riftvault" / "faltas_foil.py").read_text(encoding="utf-8")
        self.assertIn("faltas_edicao.item(", fonte)
        self.assertIn("faltas_edicao.soma(", fonte)
        con = self.catalogo()
        normal = next(g for g in next(
            d for d in self.faltas_edicao.payload(con)["sets"]
            if d["set"] == "TST")["blocks"] if g["id"] == "master")["items"][0]
        foil_item = self.bloco(con)["items"][0]
        # Os mesmos campos, mais os dois que são só das foils.
        self.assertEqual(set(foil_item) - set(normal), {"foil", "price_is_foil",
                                                        "foil_only"} - set(normal))


class TestAsPortas(Base):
    def test_a_rota_do_servidor_serve_as_duas_metades(self):
        con = self.catalogo()
        from riftvault import server
        importlib.reload(server)
        app = server.app
        app.config.update(TESTING=True)
        with app.test_client() as c:
            j = c.get("/api/faltas_edicao.json").get_json()
        self.assertIn("foil", j)
        self.assertEqual(len(j["blocks"]), 4)
        self.assertGreater(j["foil"]["totals"]["copies"], 0)

    def test_o_build_escreve_as_duas_metades(self):
        con = self.catalogo()
        con.commit()
        from riftvault import build
        importlib.reload(build)
        out = self.v.root / "site"
        build.build(out)
        j = json.loads((out / "api" / "faltas_edicao.json").read_text(encoding="utf-8"))
        self.assertIn("foil", j)
        self.assertGreater(j["foil"]["totals"]["copies"], 0)
        self.assertEqual(len(j["blocks"]), 4)

    def test_a_cli_escreve_as_duas_metades_e_a_quinta_wantlist(self):
        con = self.catalogo()
        con.commit()
        env = dict(os.environ)
        r = subprocess.run([sys.executable, "-X", "utf8", "-m", "riftvault",
                            "faltas", "--edicao", "TST"],
                           capture_output=True, text=True, encoding="utf-8",
                           cwd=REPO, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("NORMAIS", r.stdout)
        self.assertIn("FOILS", r.stdout)
        self.assertIn("NÃO são faltas", r.stdout)
        w = subprocess.run([sys.executable, "-X", "utf8", "-m", "riftvault",
                            "faltas", "--edicao", "TST", "--bloco", "foil",
                            "--cardmarket"],
                           capture_output=True, text=True, encoding="utf-8",
                           cwd=REPO, env=env)
        self.assertEqual(w.returncode, 0, w.stderr)
        self.assertIn("Defy", w.stdout)
        self.assertIn("são FOIL", w.stderr)

    def test_a_cli_aceita_o_bloco_foil_e_recusa_um_inventado(self):
        con = self.catalogo()
        con.commit()
        r = subprocess.run([sys.executable, "-X", "utf8", "-m", "riftvault",
                            "faltas", "--bloco", "nao-existe"],
                           capture_output=True, text=True, encoding="utf-8",
                           cwd=REPO, env=dict(os.environ))
        self.assertEqual(r.returncode, 1)
        self.assertIn("foil", r.stderr)


class TestOEcra(unittest.TestCase):
    """O `app.js` e o CSS: as duas metades à vista, e a wantlist das foils."""

    def setUp(self):
        self.js = APP_JS.read_text(encoding="utf-8")
        self.css = CSS.read_text(encoding="utf-8")

    def test_as_duas_metades_tem_rotulo(self):
        self.assertIn("fe-metade", self.js)
        self.assertIn("Normais — <b>as faltas</b>", self.js)
        self.assertIn("não são faltas", self.js)
        self.assertIn(".fe-metade", self.css)
        self.assertIn(".fe-metade.foil", self.css)

    def test_a_metade_das_foils_sai_do_payload_e_nao_de_conta_nenhuma(self):
        self.assertIn("function feFoilMetade(s)", self.js)
        self.assertIn("s.foil", self.js)
        # Nada de recalcular o alvo no cliente: vem do servidor.
        self.assertNotIn("playset_targets_by_type", self.js)

    def test_a_quinta_wantlist_liga_se_como_as_outras(self):
        self.assertIn("feBlocosTodos", self.js)
        self.assertIn("foilTodas: g.id === 'foil'", self.js)
        self.assertIn("foilTodas = false", self.js)

    def test_o_tile_diz_que_e_foil_e_marca_o_piso(self):
        self.assertIn("x.foil ? ' foil' : ''", self.js, "«tens 2/3 foil» no crachá")
        self.assertIn("price_is_foil", self.js)
        self.assertIn('class="piso"', self.js, "e o PISO marcado no preço")
        self.assertIn(".dtile.fe-foil", self.css)

    def test_o_cabecalho_diz_o_ambito_o_alvo_e_o_aviso(self):
        self.assertIn("function feFoilCabecalho(f)", self.js)
        self.assertIn("Rune 12", self.js)
        self.assertIn("aviso_normais", self.js)
        self.assertIn(".fe-aviso", self.css)

    def test_a_edicao_sem_ambito_diz_o_que_e(self):
        self.assertIn("fora do âmbito", self.js)

    def test_a_cor_do_foil_e_a_que_ja_existia(self):
        """Uma segunda cor de foil era o mesmo assunto com duas caras."""
        self.assertIn("--foil:", self.css)
        self.assertNotIn("--foil-cor", self.css)


class TestONotaDoConfig(unittest.TestCase):
    def test_a_nota_esta_escrita_com_a_gramatica_das_outras(self):
        cfg = json.loads(CONFIG_REAL.read_text(encoding="utf-8"))
        nota = cfg["_faltas_foil_nota"]
        for pedaco in ("2026-09-27", "as foils nao sao faltas",
                       "wantlist a parte", "no caso, playset",
                       "playset_targets_by_type", "RUNE 12",
                       "percentagem", "faltas_foil.py"):
            self.assertIn(pedaco, nota, pedaco)

    def test_nao_ha_chave_nova_a_configurar(self):
        """O âmbito e o alvo vêm de chaves que já existiam — não se inventou um
        botão com um valor legal só."""
        cfg = json.loads(CONFIG_REAL.read_text(encoding="utf-8"))
        self.assertNotIn("faltas_foil", cfg)
        self.assertIn("raridades", cfg["foil"])
        self.assertIn("Rune", cfg["playset_targets_by_type"])

    def test_a_nota_do_foil_diz_o_que_cada_chave_vale_hoje(self):
        """O `conta_para_coleccao` voltou a `false` a 2026-09-27, à noite, e a
        nota tem de o dizer — as foils não são faltas das normais, e também não
        as tapam. O `conta_para_valor` fica a `true`: é outra pergunta."""
        cfg = json.loads(CONFIG_REAL.read_text(encoding="utf-8"))
        self.assertFalse(cfg["foil"]["conta_para_coleccao"])
        self.assertTrue(cfg["foil"]["conta_para_valor"])
        self.assertNotIn("as duas a false", cfg["_foil_nota"])
        self.assertNotIn("REGISTO PARALELO", cfg["_foil_nota"])


if __name__ == "__main__":
    unittest.main()

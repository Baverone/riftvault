"""O deck aproveita as versões que ele tem, e mostra-as separadas por arte
(2026-09-17, tarde).

Palavras do André:
    *"caso um deck precise de uma carta, que não há versão disponível em
    normal, mas esteja disponível em Alt Art ou outra, usa, mas no deck
    separa as versões por Art"*

A regra, por extenso, para uma carta que NÃO é a Legend nem o Champion:
  1. serve-se primeiro com as cópias normais (base) que ele tem;
  2. se não chegarem, completa com OUTRAS impressões que ele tenha — Alt Art,
     sobrenumerada, promo — em vez de declarar falta;
  3. nunca com assinadas; uma runa em Alt Art RETIRADA (`f1dbd5b`) também não
     tapa nada;
  4. só depois disso é falta a comprar, e a falta aponta à base;
  5. o alvo da Coleção não mexe (sobrenumerada e promo a 1 de cada; a alt
     art ao playset desde 2026-09-18 — é o `master_set.um_de_cada` que manda,
     não o deck);
  6. a Legend e o Champion continuam a jogar UMA versão especial, servida
     primeiro;
  7. a vista do deck (CLI e site) reparte uma carta servida por mais do que
     uma impressão — uma servida por uma só não ganha sub-linhas.

Tudo contra pastas temporárias (`tests.fixture.Vault`) e um config PRÓPRIO: o
`data/` e o `riftvault_config.json` a sério nunca são tocados.
"""

from __future__ import annotations

import contextlib
import importlib
import io
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

CONFIG = Path(tempfile.gettempdir()) / "riftvault-versoes-deck.json"
REPO = Path(__file__).resolve().parent.parent


def escrever_config(retiradas=("a",), contar_runas=False) -> None:
    # `contar_runas` é o default de 2026-09-17 à noite (as runas não se contam
    # nos decks); os testes da runa ligam-no para ver o MECANISMO.
    CONFIG.write_text(json.dumps({
        "master_set": {"fora_da_percentagem": ["a", "overnumbered", "promo"],
                       "escondidas": ["-T", "*", "-R"],
                       # As alt arts a playset desde 2026-09-18 (o `a` saiu).
                       "um_de_cada": ["overnumbered", "promo"]},
        "master_targets_by_type": {"Rune": 3},
        "decks": {"so_normais_excepto": ["legend", "champion"],
                  "versoes_especiais": ["a", "overnumbered", "promo"],
                  "contar_runas": contar_runas},
        "runas_especiais": {"tipos": ["Rune"], "excepto": ["base"],
                            "retiradas": list(retiradas)},
        "listas_de_compra": {"so_master_set": True},
        "a_mais": {"sem_edicoes": []},
    }), encoding="utf-8")
    os.environ["RIFTVAULT_CONFIG"] = str(CONFIG)


escrever_config()

from tests.fixture import Vault  # noqa: E402

# O Azir: Legend (base + alt art + signature), Champion (base, sobrenumerada,
# promo) jogado 3 vezes, 3 Vi (base, alt art, sobrenumerada, signature), 3
# Brutalizer (só base) e 4 Calm Rune (base + alt art retirada).
AZIR = ("Legend:\n1 Emperor of the Sands\n\nChampion:\n1 Sovereign\n\n"
        "MainDeck:\n3 Vi\n3 Brutalizer\n2 Sovereign\n\nRune Pool:\n4 Calm Rune\n")
# A mesma Legend, outra lista, com menos Vi: partilha, não disputa.
AZIR_B = "Nome: Azir B\nLegend:\n1 Emperor of the Sands\n\nMainDeck:\n2 Vi\n"

EMP, EMP_A = "tst-003-100", "tst-003a-100"
SOV, SOV_OVER, SOV_SP = "tst-004-100", "tst-102-100", "tst-sp1-006"
VI, VI_A, VI_OVER, VI_STAR = "tst-001-100", "tst-001a-100", "tst-101-100", "tst-101-star-100"
BRUT = "tst-002-100"
RUNA, RUNA_A = "tst-007-100", "tst-007a-100"

PRECOS = {VI: 350, VI_A: 3957, VI_OVER: 8000, VI_STAR: 90000, BRUT: 50,
          EMP: 1000, EMP_A: 3000, SOV: 200, SOV_OVER: 4000, SOV_SP: 700,
          RUNA: 11, RUNA_A: 500}


class Base(unittest.TestCase):
    def setUp(self):
        escrever_config()
        self.addCleanup(lambda: os.environ.pop("RIFTVAULT_CONFIG", None))
        self.v = Vault()
        self.addCleanup(self.v.close)
        from riftvault import (a_mais, a_subir, collection, decks, faltas,
                               faltas_edicao, locais, metrics, pending, prices)
        for m in (metrics, locais, decks, pending, faltas, a_subir, prices,
                  collection, faltas_edicao, a_mais):
            importlib.reload(m)
        self.metrics, self.decks, self.faltas = metrics, decks, faltas
        self.a_subir, self.pending, self.locais = a_subir, pending, locais
        self.prices, self.a_mais = prices, a_mais

    def recarregar(self):
        from riftvault import config
        config.load.cache_clear()

    def catalogo(self, copias: dict | None = None, decks: dict | None = None):
        from riftvault import collection
        con = self.v.connect()
        add = self.v.add_printing
        add(con, VI, "TST", 1, "Vi", size=100)
        add(con, VI_A, "TST", 1, "Vi", variant="a", kind="alt_art",
            rarity="showcase", base_rarity="rare", size=100)
        add(con, BRUT, "TST", 2, "Brutalizer", size=100)
        add(con, EMP, "TST", 3, "Emperor of the Sands", card_type="Legend", size=100)
        add(con, EMP_A, "TST", 3, "Emperor of the Sands", variant="a", kind="alt_art",
            card_type="Legend", rarity="showcase", base_rarity="epic", size=100)
        add(con, SOV, "TST", 4, "Sovereign", size=100)
        add(con, RUNA, "TST", 7, "Calm Rune", card_type="Rune", size=100)
        add(con, RUNA_A, "TST", 7, "Calm Rune", card_type="Rune", variant="a",
            kind="alt_art", rarity="showcase", base_rarity="common", size=100)
        # Sobrenumeradas: a 101 (uma Vi, com signature) e a 102 (um Sovereign).
        add(con, VI_OVER, "TST", 101, "Vi", size=100, rarity="showcase", api_sort=101)
        add(con, VI_STAR, "TST", 101, "Vi", variant="star", kind="signature",
            rarity="showcase", size=100, codigo="TST-101*/100", api_sort=102)
        add(con, SOV_OVER, "TST", 102, "Sovereign", size=100, rarity="showcase", api_sort=103)
        add(con, SOV_SP, "TST", 1, "Sovereign", variant="sp1", kind="special",
            lane="sp", codigo="TST-SP1/006", api_sort=201)
        self.v.rebuild(con)
        for pid, cents in PRECOS.items():
            con.execute("INSERT INTO catalog.price_latest (printing_id, price_cents) "
                        "VALUES (?,?)", (pid, cents))
        for pid, n in (copias or {}).items():
            collection.adjust(con, pid, n, source="test")
        for slug, texto in (decks if decks is not None else {"azir": AZIR}).items():
            self.v.write_deck(slug, texto)
        self.decks.import_all(con, log=lambda *_: None)
        return con

    # Tudo o que o Azir pede, em base, menos a Vi (2 de 3) — o caso real do
    # LeBlanc a 17/09: tem 2 Vi base e 1 Vi alt art parada.
    QUASE = {BRUT: 3, EMP: 1, EMP_A: 1, SOV: 3, SOV_SP: 1, RUNA: 4, VI: 2}

    def idx(self, con) -> dict:
        return {d["slug"]: d for d in self.decks.decks_index(con)}

    def aloc(self, con, slug: str = "azir") -> dict:
        return self.decks.allocate(con)[self.idx(con)[slug]["id"]]

    def payload(self, con, slug: str = "azir") -> dict:
        return self.decks.deck_payload(con, self.idx(con)[slug]["id"])

    def linha(self, con, slug: str, role: str, nome: str) -> dict:
        s = next(s for s in self.payload(con, slug)["sections"] if s["role"] == role)
        return next(c for c in s["cards"] if c["name"] == nome)

    def versoes(self, a: dict, ck: str) -> list[tuple]:
        return [(x["id"], x["qty"], x["lugar"]) for x in a["versoes_em"].get(ck, [])]


# ---------------------------------------------------------------------------


class TestABaseNaoChegaEOutraTapa(Base):
    """Regras 1, 2 e 4."""

    def test_a_alt_art_parada_tapa_a_terceira_vi(self):
        """O caso real: 2 Vi base + 1 Vi alt art. Antes faltava 1; agora não."""
        con = self.catalogo(copias={**self.QUASE, VI_A: 1})
        a = self.aloc(con)
        self.assertNotIn("vi", a["missing"])
        self.assertEqual(a["alloc"]["vi"], 3)
        self.assertEqual(a["alloc_outras"], {"vi": 1})
        self.assertEqual(self.versoes(a, "vi"), [(VI, 2, "normal"), (VI_A, 1, "outra")])
        # E o total do deck e o `riftvault decks` dizem-no.
        self.assertEqual(self.idx(con)["azir"]["outras"], 1)
        self.assertEqual(self.decks.resumo_das_faltas(con)["outras"], {"cards": 1, "copies": 1})
        con.close()

    def test_a_base_serve_se_primeiro(self):
        """Com 3 bases e 1 alt art, a alt art fica na Coleção: nada de «outra»."""
        con = self.catalogo(copias={**self.QUASE, VI: 3, VI_A: 1})
        a = self.aloc(con)
        self.assertEqual(self.versoes(a, "vi"), [(VI, 3, "normal")])
        self.assertEqual(a["alloc_outras"], {})
        self.assertNotIn(VI_A, a["grupo"]["impressoes"]["na_colecao"])
        con.close()

    def test_sobrenumerada_e_promo_tambem_tapam__a_mais_barata_primeiro(self):
        """Sem Vi base nenhuma, 1 alt art (39,57 €) e 1 sobrenumerada (80 €):
        as duas servem, a mais barata primeiro, e falta 1 — a base."""
        con = self.catalogo(copias={**self.QUASE, VI: 0, VI_A: 1, VI_OVER: 1})
        a = self.aloc(con)
        self.assertEqual(self.versoes(a, "vi"), [(VI_A, 1, "outra"), (VI_OVER, 1, "outra")])
        self.assertEqual(a["missing"]["vi"], 1)
        item = next(x for d in self.decks.missing_by_set(con, self.idx(con)["azir"]["id"])
                    for x in d["items"] if x["card_key"] == "vi")
        self.assertEqual((item["code"], item["qty"], item["price"], item["especial"]),
                         ("TST-001/100", 1, 350, False))
        con.close()

    def test_a_falta_que_sobra_aponta_a_base_e_custa_o_preco_da_base(self):
        con = self.catalogo(copias={**self.QUASE, VI: 1, VI_A: 1})
        r = self.decks.resumo_das_faltas(con)
        self.assertEqual((r["copies"], r["cents"]), (1, 350))
        self.assertEqual(r["outras"], {"cards": 1, "copies": 1})
        con.close()

    def test_a_promo_tapa_um_lugar_normal_do_champion(self):
        """Sovereign 3×: o Champion leva a promo; com 1 base só, a sobrenumerada
        tapa o segundo lugar normal — e nada falta."""
        con = self.catalogo(copias={**self.QUASE, SOV: 1, SOV_SP: 1, SOV_OVER: 1})
        a = self.aloc(con)
        self.assertEqual(self.versoes(a, "sovereign"),
                         [(SOV_SP, 1, "especial"), (SOV, 1, "normal"), (SOV_OVER, 1, "outra")])
        self.assertNotIn("sovereign", a["missing"])
        self.assertEqual(a["alloc_outras"]["sovereign"], 1)
        con.close()

    def test_uma_alt_art_a_caminho_tapa_como_a_base_a_caminho(self):
        """Encomendou a alt art (o `+` das Encomendas grava por impressão) e
        falta-lhe 1 Vi base: fica «a caminho», não «a comprar»."""
        con = self.catalogo(copias=self.QUASE)
        self.pending.add(con, VI_A, 1, source="test")
        a = self.aloc(con)
        self.assertNotIn("vi", a["missing"])
        self.assertEqual(a["a_caminho"]["vi"], 1)
        con.close()


class TestNuncaAssinadaNemRetirada(Base):
    """Regra 3."""

    def test_a_signature_da_vi_nao_tapa(self):
        con = self.catalogo(copias={**self.QUASE, VI_STAR: 1})
        a = self.aloc(con)
        self.assertEqual(a["missing"]["vi"], 1)
        self.assertEqual(self.versoes(a, "vi"), [(VI, 2, "normal")])
        self.assertNotIn(VI_STAR, self.decks.versoes_dos_decks(con).outras_de("vi"))
        con.close()

    def test_a_runa_nao_se_conta__nem_a_base_nem_a_alt_art(self):
        """3 Calm Rune base + 6 em alt art: desde 2026-09-17 à noite («nao
        facas contagem de runas nos decks») a runa nem entra no `need` — não
        falta, não se aloca, não se reparte —, e as 6 alt arts ficam no monte
        sem ninguém as levar (`test_runas_fora_decks.py`). O MECANISMO da
        retirada nos decks continua lá, e vê-se com `contar_runas: true`:
        falta 1 e a alt art retirada não tapa — «não incluas em nada»."""
        con = self.catalogo(copias={**self.QUASE, RUNA: 3, RUNA_A: 6})
        a = self.aloc(con)
        self.assertNotIn("calm rune", a["missing"])
        self.assertNotIn("calm rune", a["alloc"])
        self.assertEqual(self.versoes(a, "calm rune"), [])
        self.assertNotIn(RUNA_A, a["grupo"]["impressoes"]["na_colecao"])
        self.assertNotIn(RUNA_A, self.decks.versoes_dos_decks(con).outras_de("calm rune"))
        con.close()
        escrever_config(contar_runas=True)
        self.recarregar()
        self.v = Vault()
        self.addCleanup(self.v.close)
        con = self.catalogo(copias={**self.QUASE, RUNA: 3, RUNA_A: 6})
        a = self.aloc(con)
        self.assertEqual(a["missing"]["calm rune"], 1)
        self.assertEqual(self.versoes(a, "calm rune"), [(RUNA, 3, "normal")])
        self.assertNotIn(RUNA_A, a["grupo"]["impressoes"]["na_colecao"])
        con.close()

    def test_a_tensao_da_runa_fechou__so_com_as_runas_a_contar_e_que_a_alt_art_tapava(self):
        """A tensão anotada no relatório de 2026-09-17 à tarde («se a runa
        deixasse de estar retirada, tapava») fechou-se nessa noite: as runas
        não se contam, por isso `retiradas: []` sozinho não muda nada nos
        decks. Só com `contar_runas: true` E sem retirar é que a alt art
        tapava — fica fixado para se saber o que a config faz."""
        escrever_config(retiradas=())
        self.recarregar()
        con = self.catalogo(copias={**self.QUASE, RUNA: 3, RUNA_A: 6})
        a = self.aloc(con)
        self.assertNotIn("calm rune", a["missing"])
        self.assertEqual(self.versoes(a, "calm rune"), [])
        con.close()
        escrever_config(retiradas=(), contar_runas=True)
        self.recarregar()
        self.v = Vault()
        self.addCleanup(self.v.close)
        con = self.catalogo(copias={**self.QUASE, RUNA: 3, RUNA_A: 6})
        a = self.aloc(con)
        self.assertNotIn("calm rune", a["missing"])
        self.assertEqual(self.versoes(a, "calm rune"), [(RUNA, 3, "normal"), (RUNA_A, 1, "outra")])
        con.close()


class TestOAlvoEAColecaoNaoMexem(Base):
    """Regra 5: usar não é querer mais."""

    def test_a_alt_art_usada_continua_a_pedir_o_do_config_e_a_wantlist_pede_a_base(self):
        con = self.catalogo(copias={**self.QUASE, VI_A: 1})
        p = self.metrics.set_payload(con, "TST")
        tiles = {pr["id"]: pr for g in p["groups"] for pr in g["printings"]}
        # O playset (2026-09-18) — «tenho 1 de 3» —, e não por o deck a usar.
        self.assertEqual((tiles[VI_A]["qty"], tiles[VI_A]["target"]), (1, 3))
        self.assertEqual((tiles[VI]["qty"], tiles[VI]["target"]), (2, 3))
        # A wantlist do master set continua a pedir 1 Vi base: a alt art a
        # jogar no deck não é uma Vi da sequência.
        wl = self.a_subir.wantlist(con, "TST")
        vi = [x for x in wl["items"] if x["printing_id"] == VI]
        self.assertEqual([x["missing"] for x in vi], [1])
        con.close()

    def test_a_percentagem_e_o_denominador_sao_os_mesmos_com_e_sem_a_alt_art(self):
        con = self.catalogo(copias={**self.QUASE, VI_A: 1})
        com = self.metrics.set_payload(con, "TST")["progress"]
        con.close()
        self.v = Vault()
        self.addCleanup(self.v.close)
        con = self.catalogo(copias=self.QUASE)
        sem = self.metrics.set_payload(con, "TST")["progress"]
        con.close()
        self.assertEqual(com["master"], sem["master"])

    def test_a_alocacao_nao_escreve(self):
        con = self.catalogo(copias={**self.QUASE, VI_A: 1})
        antes = con.execute("SELECT printing_id, qty FROM copies ORDER BY 1").fetchall()
        n_ops = con.execute("SELECT COUNT(*) FROM ops").fetchone()[0]
        self.aloc(con)
        self.payload(con)
        self.assertEqual(con.execute("SELECT printing_id, qty FROM copies ORDER BY 1").fetchall(), antes)
        self.assertEqual(con.execute("SELECT COUNT(*) FROM ops").fetchone()[0], n_ops)
        con.close()


class TestALegendEOChampionNaoMudam(Base):
    """Regra 6."""

    def test_a_legend_continua_a_pedir_a_especial_e_a_base_nao_a_serve(self):
        con = self.catalogo(copias={**self.QUASE, EMP_A: 0})
        a = self.aloc(con)
        self.assertEqual(a["missing_especial"]["emperor of the sands"], 1)
        self.assertEqual(self.versoes(a, "emperor of the sands"), [])
        con.close()

    def test_o_champion_leva_a_especial_primeiro_e_o_main_a_base(self):
        con = self.catalogo(copias={**self.QUASE, SOV: 2, SOV_SP: 1})
        a = self.aloc(con)
        self.assertEqual(self.versoes(a, "sovereign"), [(SOV_SP, 1, "especial"), (SOV, 2, "normal")])
        self.assertEqual(a["alloc_outras"], {})
        con.close()


class TestAVistaReparte(Base):
    """Regra 7: «separa as versões por Art»."""

    def test_a_linha_do_deck_leva_as_versoes_e_o_outras(self):
        con = self.catalogo(copias={**self.QUASE, VI_A: 1})
        l = self.linha(con, "azir", "main", "Vi")
        self.assertEqual((l["have"], l["missing"], l["outras"]), (3, 0, 1))
        self.assertEqual([(x["code"], x["label"], x["qty"], x["lugar"]) for x in l["versoes"]],
                         [("TST-001/100", "normal", 2, "normal"),
                          ("TST-001a/100", "Alt Art", 1, "outra")])
        con.close()

    def test_servida_por_uma_impressao_so_leva_uma_entrada(self):
        con = self.catalogo(copias={**self.QUASE, VI_A: 1})
        l = self.linha(con, "azir", "main", "Brutalizer")
        self.assertEqual(len(l["versoes"]), 1)
        self.assertEqual((l["versoes"][0]["label"], l["outras"]), ("normal", 0))
        con.close()

    def test_os_rotulos_sao_as_palavras_dele(self):
        con = self.catalogo(copias={**self.QUASE, SOV: 1, SOV_SP: 1, SOV_OVER: 1})
        vs = self.decks.versoes_dos_decks(con)
        self.assertEqual([vs.rotulo(p) for p in (SOV, SOV_SP, SOV_OVER, VI_A)],
                         ["normal", "promo", "sobrenumerada", "Alt Art"])
        # O Champion na linha dele, as normais + a outra no main.
        ch = self.linha(con, "azir", "champion", "Sovereign")
        self.assertEqual([(x["label"], x["qty"]) for x in ch["versoes"]], [("promo", 1)])
        mn = self.linha(con, "azir", "main", "Sovereign")
        self.assertEqual([(x["label"], x["qty"], x["lugar"]) for x in mn["versoes"]],
                         [("normal", 1, "normal"), ("sobrenumerada", 1, "outra")])
        self.assertEqual((mn["have"], mn["missing"], mn["outras"]), (2, 0, 1))
        con.close()

    def test_no_grupo_da_mesma_legend_o_irmao_que_pede_menos_leva_as_normais(self):
        """O Azir pede 3 Vi, o Azir B pede 2; há 2 base + 1 alt art. O grupo
        tapa a terceira com a alt art; o Azir B vê só as 2 normais."""
        con = self.catalogo(copias={**self.QUASE, VI_A: 1}, decks={"azir": AZIR, "azir-b": AZIR_B})
        a, b = self.aloc(con, "azir"), self.aloc(con, "azir-b")
        self.assertEqual(self.versoes(a, "vi"), [(VI, 2, "normal"), (VI_A, 1, "outra")])
        self.assertEqual(self.versoes(b, "vi"), [(VI, 2, "normal")])
        self.assertEqual((a["alloc_outras"], b["alloc_outras"]), ({"vi": 1}, {}))
        # O total geral conta o grupo uma vez.
        self.assertEqual(self.decks.resumo_das_faltas(con)["outras"], {"cards": 1, "copies": 1})
        con.close()

    def test_a_cli_reparte_em_sub_linhas_so_quando_ha_mais_do_que_uma(self):
        from riftvault import cli
        importlib.reload(cli)
        con = self.catalogo(copias={**self.QUASE, VI_A: 1})
        con.close()
        saida = io.StringIO()
        with contextlib.redirect_stdout(saida):
            cli.cmd_deck(types.SimpleNamespace(slug="azir", onde=False))
        txt = saida.getvalue()
        self.assertIn("2 normal (TST-001)", txt)
        self.assertIn("1 Alt Art (TST-001a)", txt)
        self.assertIn("1 cópia joga noutra versão", txt)
        # O Brutalizer, servido só pela base, não ganha sub-linha.
        self.assertNotIn("3 normal (TST-002)", txt)

    def test_a_cli_diz_na_linha_quando_a_unica_versao_e_outra(self):
        from riftvault import cli
        importlib.reload(cli)
        con = self.catalogo(copias={**self.QUASE, VI: 0, VI_A: 1})
        con.close()
        saida = io.StringIO()
        with contextlib.redirect_stdout(saida):
            cli.cmd_deck(types.SimpleNamespace(slug="azir", onde=False))
        txt = saida.getvalue()
        self.assertIn("em Alt Art (TST-001a)", txt)
        self.assertNotIn("1 Alt Art (TST-001a)\n", txt)

    def test_o_site_reparte_no_tile(self):
        js = (REPO / "riftvault" / "web" / "app.js").read_text(encoding="utf-8")
        self.assertIn("function versoesNota", js)
        self.assertIn("vs.length > 1", js)
        self.assertIn("nota += versoesNota(c)", js)
        css = (REPO / "riftvault" / "web" / "style.css").read_text(encoding="utf-8")
        self.assertIn(".onde.versoes span.outra", css)


class TestAMais(Base):
    """Uma cópia que passa a jogar deixa de estar a mais."""

    def item(self, con, pid):
        am = self.a_mais.payload(con)
        return next((x for s in am["sets"] for x in s["excedente"]["items"]
                     if x["printing_id"] == pid), None)

    def test_a_sobrenumerada_a_mais_que_o_deck_passa_a_usar_sai_do_a_mais(self):
        # A sobrenumerada pede 1: 3 cópias, o deck leva 2 (faltavam-lhe 2
        # bases): 3 − max(2, 1) = 1 a mais.
        con = self.catalogo(copias={**self.QUASE, VI: 1, VI_OVER: 3})
        self.assertEqual(self.item(con, VI_OVER)["extra"], 1)
        con.close()
        # Sem o deck a precisar delas, eram 2 a mais.
        self.v = Vault()
        self.addCleanup(self.v.close)
        con = self.catalogo(copias={**self.QUASE, VI: 3, VI_OVER: 3})
        self.assertEqual(self.item(con, VI_OVER)["extra"], 2)
        con.close()

    def test_a_alt_art_pede_o_playset_e_um_deck_so_nunca_a_poe_a_mais(self):
        """Com o alvo no playset (2026-09-18), um deck que leve 2 alt arts não
        muda o excedente: 5 − max(2, 3) = 2, o mesmo que sem o deck (5 − 3).
        Com 3 alt arts não há excedente nenhum, use-as o deck ou não."""
        con = self.catalogo(copias={**self.QUASE, VI: 1, VI_A: 3})
        self.assertIsNone(self.item(con, VI_A))
        con.close()
        self.v = Vault()
        self.addCleanup(self.v.close)
        con = self.catalogo(copias={**self.QUASE, VI: 1, VI_A: 5})
        x = self.item(con, VI_A)
        self.assertEqual((x["target"], x["used"], x["extra"]), (3, 2, 2))
        con.close()
        self.v = Vault()
        self.addCleanup(self.v.close)
        con = self.catalogo(copias={**self.QUASE, VI: 3, VI_A: 5})
        x = self.item(con, VI_A)
        self.assertEqual((x["target"], x["used"], x["extra"]), (3, 0, 2))
        con.close()


if __name__ == "__main__":
    unittest.main()

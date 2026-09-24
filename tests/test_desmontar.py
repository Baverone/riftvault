"""DECK MONTADO OU DESMONTADO, e a REGRA DE RARIDADE (André, 2026-09-24).

Palavras dele: *"vamos desmontar os decks todos com excepcao da LeBlanc, vou
colocar tudo nos binders das edicoes e depois voltar a montar deck a deck e
assim conseguir perceber o que tenho e nao tenho. tal como dito antes, o que
tiver a mais dos decks fica exclusivo para o deck e nao entra na coleccao. vou
tentar ao maximo que cartas de raridade Rara para baixo fiquem alocadas
exclusivamente a coleccao e as repetidas exclusivamente aos decks, para nao ter
que mexer na coleccao. apenas miticas para acima devo ter que usar as da
coleccao"*.

O que este ficheiro fixa:

  1. `decks.montados` — sem a chave, TODOS montados; a lista vazia é «nenhum»;
     casa pelo slug e pelo `Nome:`; um nome sem deck avisa e não rebenta;
  2. **A COLEÇÃO COM DECKS DESMONTADOS DÁ EXACTAMENTE OS MESMOS NÚMEROS QUE
     DARIA SE ESSES DECKS NÃO EXISTISSEM** — é a fotografia, e é a promessa
     que a ordem faz. A única diferença permitida são as «libertadas» do A
     mais: apagar um `.txt` liberta as cartas dele, desmontar não;
  3. um desmontado não aparece na grelha como uso, não entra na falta a
     comprar, nas Staples, no «para» das Encomendas nem no excedente; a
     proposta de marcação recusa-o;
  4. a lista dele continua a ver-se, e a página mostra a SIMULAÇÃO de o montar
     a seguir aos montados — que não consome (dois desmontados podem contar a
     mesma cópia);
  5. montar volta a consumir, na hora;
  6. `alternar_montado` escreve o config (e só a chave dele), pelo botão e
     pela CLI;
  7. a regra de raridade MARCA e não bloqueia: a alocação é exactamente a
     mesma, e sai um aviso por carta e um contador por deck; epic e showcase
     não avisam; `null` desliga; uma raridade que não existe rebenta;
  8. as rotas, o `build` e o `app.js`.

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
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ["RIFTVAULT_CONFIG"] = str(Path(tempfile.gettempdir()) / "riftvault-nao-existe.json")

from tests.fixture import REPO, Vault  # noqa: E402

# Azir: Legend épica, Champion raro, 3 Defy (rare) + 2 Salvage (common) no
# main, 1 Defy e 1 Hidden Blade (uncommon) no sideboard, 3 runas.
AZIR = ("Nome: Azir\n\nLegend:\n1 Emperor of the Sands\n\nChampion:\n1 Brutalizer\n\n"
        "MainDeck:\n3 Defy\n2 Salvage\n\nRune Pool:\n3 Fury Rune\n\n"
        "Sideboard:\n1 Defy\n1 Hidden Blade\n")
# Ornn: outra Legend (não é um grupo), pede as mesmas cartas.
ORNN = ("Nome: Ornn\n\nLegend:\n1 Fire Below the Mountain\n\n"
        "MainDeck:\n2 Defy\n3 Salvage\n2 Hidden Blade\n\nRune Pool:\n3 Fury Rune\n")


class Base(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.close)
        from riftvault import (a_mais, a_subir, collection, config, decks, faltas,
                               faltas_edicao, locais, metrics, painel, pending, prices,
                               proprias)
        for m in (locais, metrics, painel, decks, proprias, a_subir, faltas_edicao,
                  a_mais, pending, faltas, prices):
            importlib.reload(m)
        self.config, self.decks, self.proprias, self.locais = config, decks, proprias, locais
        self.metrics, self.a_subir, self.faltas_edicao = metrics, a_subir, faltas_edicao
        self.a_mais, self.pending, self.faltas, self.prices = a_mais, pending, faltas, prices
        self.collection, self.painel = collection, painel
        self.cfg_decks({})

    def cfg_decks(self, decks_extra: dict, extra: dict | None = None):
        """O config temporário com o bloco `decks` de hoje mais o que o teste
        quiser, e relê-o. Sem `montados`: todos montados."""
        caminho = self.v.root / "config.json"
        caminho.write_text(json.dumps({"decks": {"so_base": True, "so_normais_excepto": [],
                                                 "versoes_especiais": ["a", "overnumbered", "promo"],
                                                 "coleccao_so_a_partir_de": "epic",
                                                 "modo": "coleccao", **decks_extra},
                                       **(extra or {})}, ensure_ascii=False),
                           encoding="utf-8")
        os.environ["RIFTVAULT_CONFIG"] = str(caminho)
        importlib.reload(self.config)
        self.config.load.cache_clear()

        def repor():
            os.environ["RIFTVAULT_CONFIG"] = str(
                Path(tempfile.gettempdir()) / "riftvault-nao-existe.json")
            importlib.reload(self.config)
            self.config.load.cache_clear()

        self.addCleanup(repor)
        return caminho

    def catalogo(self, decks=("azir", "ornn")):
        """Uma edição com raridades a sério: Defy rara, Salvage comum, Hidden
        Blade incomum, Brutalizer raro, as duas Legends épicas. Na Coleção: 5
        Defy, 6 Salvage, 3 Hidden Blade, 2 Brutalizer, 1 de cada Legend."""
        con = self.v.connect()
        v = self.v
        v.add_printing(con, "tst-001-100", "TST", 1, "Defy", rarity="rare", size=100)
        v.add_printing(con, "tst-001a-100", "TST", 1, "Defy", variant="a", kind="alt_art",
                       rarity="showcase", base_rarity="rare", size=100)
        v.add_printing(con, "tst-002-100", "TST", 2, "Brutalizer", rarity="rare", size=100)
        v.add_printing(con, "tst-003-100", "TST", 3, "Emperor of the Sands",
                       card_type="Legend", rarity="epic", size=100)
        v.add_printing(con, "tst-004-100", "TST", 4, "Salvage", rarity="common", size=100)
        v.add_printing(con, "tst-005-100", "TST", 5, "Hidden Blade", rarity="uncommon", size=100)
        v.add_printing(con, "tst-006-100", "TST", 6, "Fury Rune", card_type="Rune", size=100)
        v.add_printing(con, "tst-007-100", "TST", 7, "Fire Below the Mountain",
                       card_type="Legend", rarity="epic", size=100)
        v.rebuild(con)
        for pid, cents in (("tst-001-100", 150), ("tst-001a-100", 2000),
                           ("tst-002-100", 80), ("tst-003-100", 1000),
                           ("tst-004-100", 20), ("tst-005-100", 300),
                           ("tst-006-100", 11), ("tst-007-100", 500)):
            con.execute("INSERT INTO catalog.price_latest (printing_id, price_cents) "
                        "VALUES (?,?)", (pid, cents))
        for pid, n in (("tst-001-100", 5), ("tst-004-100", 6), ("tst-005-100", 3),
                       ("tst-002-100", 2), ("tst-003-100", 1), ("tst-007-100", 1)):
            self.collection.adjust(con, pid, n, source="test")
        for slug, texto in (("azir", AZIR), ("ornn", ORNN)):
            if slug in decks:
                self.v.write_deck(slug, texto)
        self.decks.import_all(con, log=lambda *_: None)
        self.addCleanup(con.close)
        return con

    def reimportar(self, con):
        self.decks.import_all(con, log=lambda *_: None)

    def por_slug(self, con) -> dict:
        alloc = self.decks.allocate(con)
        return {r["name"]: alloc[r["deck_id"]] for r in self.decks.deck_rows(con)}

    def deck_id(self, con, slug) -> int:
        return next(r["deck_id"] for r in self.decks.deck_rows(con) if r["name"] == slug)

    def fotografia(self, con) -> dict:
        """Tudo o que é NÚMERO DA COLEÇÃO. É esta que tem de ser igual com o
        deck desmontado e sem o deck."""
        cfg = self.config.load()
        sp = self.metrics.set_payload(con, "TST")
        fe = self.faltas_edicao.payload(con, cfg)
        enc = self.pending.encomendas(con)
        am = self.a_mais.payload(con, cfg)
        return {
            "niveis": [(l["k"], l["done"], l["total"], l["missing"], l["cents"])
                       for l in self.metrics.niveis_payload(con, cfg)["levels"]],
            "wantlist": {k: self.a_subir.wantlist(con, cfg=cfg)[k]
                         for k in ("text", "lines", "copies", "cents")},
            "valor": self.prices.collection_value(con)["cents"],
            "valor_copias": self.prices.collection_value(con)["copias"],
            "totais": self.collection.totals(con),
            "grelha": [(p["id"], p["qty"], p["target"], p["qty_valor"])
                       for g in sp["groups"] for p in g["printings"]],
            "usos": {g["card_key"]: g.get("decks") for g in sp["groups"]},
            "master": sp["progress"]["master"],
            "painel": sp["progress"]["painel"],
            "faltas": (fe["totals"], fe["totals_lists"]),
            "encomendas": (enc["totals"], [(f["set"], f["copies"]) for f in enc["falta"]]),
            "excedente": {s["set"]: [(x["printing_id"], x["extra"], x["have"], x["used"])
                                     for x in s["excedente"]["items"]] for s in am["sets"]},
        }


# ---------------------------------------------------------------------------


class TestAChave(Base):
    """1. `decks.montados`: sem chave todos; vazia nenhum; slug ou `Nome:`."""

    def test_sem_a_chave_estao_todos_montados(self):
        con = self.catalogo()
        self.assertEqual(self.decks.montados_lista(), None)
        self.assertEqual(self.decks.montados(con), frozenset({"azir", "ornn"}))
        self.assertTrue(all(a["montado"] for a in self.decks.allocate(con).values()))

    def test_a_lista_vazia_e_nenhum_montado(self):
        self.cfg_decks({"montados": []})
        con = self.catalogo()
        self.assertEqual(self.decks.montados(con), frozenset())
        self.assertFalse(any(a["montado"] for a in self.decks.allocate(con).values()))

    def test_casa_pelo_slug_e_pelo_nome(self):
        con = self.catalogo()
        for escrito in ("azir", "Azir", "  AZIR  "):
            self.cfg_decks({"montados": [escrito]})
            self.assertEqual(self.decks.montados(con), frozenset({"azir"}),
                             f"{escrito!r} tinha de casar")

    def test_um_nome_sem_deck_avisa_e_nao_rebenta(self):
        self.cfg_decks({"montados": ["azir", "não existe"]})
        con = self.catalogo()
        est = self.decks.montados_estado(con)
        self.assertEqual(est["montados"], ["azir"])
        self.assertEqual(est["desmontados"], ["ornn"])
        self.assertEqual(est["nao_encontrados"], ["não existe"])

    def test_uma_lista_mal_escrita_rebenta(self):
        self.cfg_decks({"montados": "azir"})
        with self.assertRaises(ValueError):
            self.decks.montados_lista()


class TestAColecaoNaoMexe(Base):
    """2. A promessa da ordem: com o deck desmontado, a Coleção dá os mesmos
    números que daria se o deck não existisse."""

    def test_desmontado_da_o_mesmo_que_nao_existir(self):
        # Com o Ornn desmontado…
        self.cfg_decks({"montados": ["azir"]})
        con = self.catalogo()
        desmontado = self.fotografia(con)
        # …e agora sem o ficheiro do Ornn de todo.
        (self.v.decks_dir / "ornn.txt").unlink()
        self.cfg_decks({})              # sem lista: o que resta está montado
        self.reimportar(con)
        sem_ele = self.fotografia(con)
        self.assertEqual(desmontado, sem_ele,
                         "a Coleção com o Ornn desmontado tem de dar o mesmo que sem o Ornn")

    def test_desmontar_nao_gera_libertadas(self):
        """A diferença que apagar o `.txt` FAZ e desmontar não: as libertadas.
        É o ponto da ordem — ele quer voltar a montar, não perder o registo."""
        con = self.catalogo()
        self.cfg_decks({"montados": ["azir"]})
        am = self.a_mais.payload(con, self.config.load())
        self.assertEqual(am["totals"]["libertadas"]["copies"], 0)
        # Apagar o ficheiro, sim, liberta.
        (self.v.decks_dir / "ornn.txt").unlink()
        self.reimportar(con)
        am = self.a_mais.payload(con, self.config.load())
        self.assertGreater(am["totals"]["libertadas"]["copies"], 0)

    def test_o_excedente_sobe_porque_o_deck_deixou_de_consumir(self):
        # Salvage: 6 na Coleção, alvo 3, os dois decks pedem 5 -> nada a mais.
        con = self.catalogo()
        def sobra(pid):
            am = self.a_mais.payload(con, self.config.load())
            x = [i for s in am["sets"] for i in s["excedente"]["items"]
                 if i["printing_id"] == pid]
            return x[0]["extra"] if x else 0
        self.assertEqual(sobra("tst-004-100"), 1)      # 6 − max(5 usadas, 3)
        self.cfg_decks({"montados": []})               # nenhum montado
        self.assertEqual(sobra("tst-004-100"), 3)      # 6 − 3 de alvo


class TestNaoConsomeNada(Base):
    """3. Um desmontado não aparece em lado nenhum que some decks."""

    def test_nao_aparece_na_grelha_como_uso(self):
        con = self.catalogo()
        self.assertIn("ornn", {h["slug"] for v in self.decks.uso_por_carta(con).values()
                               for h in v})
        self.cfg_decks({"montados": ["azir"]})
        uso = self.decks.uso_por_carta(con)
        self.assertNotIn("ornn", {h["slug"] for v in uso.values() for h in v})
        self.assertIn("azir", {h["slug"] for v in uso.values() for h in v})

    def test_nao_entra_na_falta_a_comprar_nem_nas_staples(self):
        con = self.catalogo()
        antes = self.decks.resumo_das_faltas(con)["copies"]
        self.cfg_decks({"montados": ["azir"]})
        depois = self.decks.resumo_das_faltas(con)["copies"]
        self.assertLess(depois, antes)
        # Com um deck só, nada é staple (uma staple é de DOIS decks).
        self.assertEqual(self.faltas.staples(con), [])
        self.assertNotIn("ornn", {s for c in self.faltas._wanted(con).values()
                                  for s in c["decks"]})

    def test_nao_entra_no_para_das_encomendas(self):
        con = self.catalogo()
        self.pending.encomendar(con, printing_id="tst-005-100", qty=2, source="test")
        self.cfg_decks({"montados": ["azir"]})
        enc = self.pending.encomendas(con)
        destinos = {d["slug"] for g in enc["a_caminho"] for it in g["items"]
                    for d in it["para"]}
        self.assertNotIn("ornn", destinos)
        falta = {it["slug"] for f in enc["falta"] for it in f["items"]}
        self.assertNotIn("ornn", falta)

    def test_a_proposta_de_marcacao_recusa_um_desmontado(self):
        con = self.catalogo()
        self.cfg_decks({"montados": ["azir"]})
        p = self.locais.propor_deck(con, "ornn")
        self.assertEqual(p["items"], [])
        self.assertIn("desmontado", p["erro"])
        self.assertTrue(self.locais.propor_deck(con, "azir")["items"])


class TestASimulacao(Base):
    """4. A lista continua a ver-se, e diz o que sairia da Coleção."""

    def test_a_pagina_continua_a_mostrar_a_lista_e_o_que_precisaria(self):
        self.cfg_decks({"montados": ["azir"]})
        con = self.catalogo()
        p = self.decks.deck_payload(con, self.deck_id(con, "ornn"))
        self.assertFalse(p["montado"])
        cartas = {c["name"]: c for s in p["sections"] for c in s["cards"]}
        # A lista continua toda lá, com as quantidades dela.
        self.assertEqual(cartas["Salvage"]["wanted"], 3)
        # O Azir (montado) leva 2 das 6 Salvage; sobram 4 e o Ornn pede 3.
        self.assertEqual(cartas["Salvage"]["na_colecao"], 3)
        self.assertEqual(cartas["Salvage"]["missing"], 0)
        # Defy: 5 na Coleção, o Azir montado leva 4 — ao Ornn sobra 1 e falta 1.
        self.assertEqual((cartas["Defy"]["wanted"], cartas["Defy"]["na_colecao"],
                          cartas["Defy"]["missing"]), (2, 1, 1))

    def test_dois_desmontados_podem_contar_a_mesma_copia(self):
        """A simulação não consome: cada desmontado vê o mesmo que sobrou."""
        self.cfg_decks({"montados": []})
        con = self.catalogo()
        ps = self.por_slug(con)
        # Defy: 5 na Coleção; o Azir pede 4 e o Ornn 2. Montados, o Azir leva
        # 4 e o Ornn 1 (e falta-lhe 1). Desmontados, cada um vê as 5.
        self.assertEqual(ps["azir"]["na_colecao"]["defy"], 4)
        self.assertEqual(ps["ornn"]["na_colecao"]["defy"], 2)
        self.assertEqual(ps["ornn"]["missing"].get("defy", 0), 0)
        self.cfg_decks({})
        ps = self.por_slug(con)
        self.assertEqual(ps["azir"]["na_colecao"]["defy"], 4)
        self.assertEqual(ps["ornn"]["na_colecao"]["defy"], 1)
        self.assertEqual(ps["ornn"]["missing"]["defy"], 1)

    def test_a_simulacao_ve_o_que_os_montados_deixaram(self):
        self.cfg_decks({"montados": ["azir"]})
        con = self.catalogo()
        ps = self.por_slug(con)
        # O Azir leva 4 das 5 Defy; ao Ornn (desmontado) sobra 1, falta 1.
        self.assertEqual(ps["ornn"]["na_colecao"]["defy"], 1)
        self.assertEqual(ps["ornn"]["missing"]["defy"], 1)

    def test_as_proprias_do_desmontado_servem_na_mesma(self):
        """As próprias não são da Coleção: servem montado ou desmontado."""
        self.cfg_decks({"montados": ["azir"]})
        con = self.catalogo()
        self.proprias.ajustar(con, "ornn", "tst-004-100", 3, source="test")
        ps = self.por_slug(con)
        self.assertEqual(ps["ornn"]["proprias"]["salvage"], 3)
        self.assertEqual(ps["ornn"]["missing"].get("salvage", 0), 0)


class TestMontarOutraVez(Base):
    """5./6. Montar volta a consumir; o botão e a CLI escrevem o config."""

    def test_montar_volta_a_consumir(self):
        self.cfg_decks({"montados": ["azir"]})
        con = self.catalogo()
        self.assertNotIn("ornn", {h["slug"] for v in self.decks.uso_por_carta(con).values()
                                  for h in v})
        self.decks.alternar_montado(con, "ornn", True)
        self.assertIn("ornn", {h["slug"] for v in self.decks.uso_por_carta(con).values()
                               for h in v})

    def test_alternar_escreve_o_config_e_so_a_chave_dele(self):
        caminho = self.cfg_decks({"montados": ["Azir", "Ornn"]},
                                 extra={"token_target": 1, "_nota": "fica"})
        con = self.catalogo()
        self.decks.alternar_montado(con, "ornn", False)
        raw = json.loads(caminho.read_text(encoding="utf-8"))
        self.assertEqual(raw["decks"]["montados"], ["Azir"])
        self.assertEqual(raw["decks"]["so_base"], True)
        self.assertEqual(raw["token_target"], 1)
        self.assertEqual(raw["_nota"], "fica")
        self.assertEqual(self.decks.montados(con), frozenset({"azir"}))

    def test_desmontar_o_ultimo_escreve_a_lista_vazia(self):
        caminho = self.cfg_decks({"montados": ["Azir"]})
        con = self.catalogo()
        self.decks.alternar_montado(con, "azir", False)
        raw = json.loads(caminho.read_text(encoding="utf-8"))
        self.assertEqual(raw["decks"]["montados"], [])
        self.assertEqual(self.decks.montados(con), frozenset())

    def test_sem_lista_desmontar_um_escreve_os_outros(self):
        caminho = self.cfg_decks({})
        con = self.catalogo()
        self.decks.alternar_montado(con, "ornn", False)
        raw = json.loads(caminho.read_text(encoding="utf-8"))
        self.assertEqual(raw["decks"]["montados"], ["Azir"])

    def test_um_deck_que_nao_existe_rebenta(self):
        con = self.catalogo()
        with self.assertRaises(self.decks.DeckDesconhecido):
            self.decks.alternar_montado(con, "não-existe", False)

    def test_o_config_a_serio_nao_perde_o_feitio(self):
        """O ficheiro dele é escrito à mão, com objectos numa linha e `_notas`
        pelo meio: escrever a chave não pode reformatar o resto."""
        caminho = self.v.root / "mao.json"
        original = ('{\n  "_leia-me": "olá",\n  "sets": {\n'
                    '    "TST": { "name": "TST", "order": 1 }\n  },\n'
                    '  "decks": {\n    "so_base": true,\n'
                    '    "ordem": ["Azir", "Ornn"]\n  },\n'
                    '  "_decks_nota": "uma nota longa"\n}\n')
        caminho.write_text(original, encoding="utf-8")
        os.environ["RIFTVAULT_CONFIG"] = str(caminho)
        importlib.reload(self.config)
        self.config.load.cache_clear()
        self.config.escrever_lista("decks", "montados", ["Azir"])
        novo = caminho.read_text(encoding="utf-8")
        self.assertIn('"TST": { "name": "TST", "order": 1 }', novo)
        self.assertIn('"_decks_nota": "uma nota longa"', novo)
        self.assertIn('"montados": ["Azir"]', novo)
        self.assertEqual(json.loads(novo)["decks"]["ordem"], ["Azir", "Ornn"])
        # E outra vez por cima: troca o valor, não duplica a chave.
        self.config.escrever_lista("decks", "montados", [])
        novo = caminho.read_text(encoding="utf-8")
        self.assertEqual(novo.count('"montados"'), 1)
        self.assertEqual(json.loads(novo)["decks"]["montados"], [])


class TestARegraDeRaridade(Base):
    """7. Marca, não bloqueia."""

    def test_avisa_o_que_esta_abaixo_do_patamar_e_cala_o_resto(self):
        con = self.catalogo()
        ps = self.por_slug(con)
        aviso = ps["azir"]["aviso_colecao"]
        # Da Coleção o Azir leva 4 Defy (rare), 2 Salvage (common), 1 Hidden
        # Blade (uncommon), 1 Brutalizer (rare) e 1 Emperor (epic).
        self.assertEqual(aviso.get("defy"), 4)
        self.assertEqual(aviso.get("salvage"), 2)
        self.assertEqual(aviso.get("hidden blade"), 1)
        self.assertEqual(aviso.get("brutalizer"), 1)
        self.assertNotIn("emperor of the sands", aviso, "a épica pode vir da Coleção")

    def test_nao_bloqueia_nada(self):
        """A alocação com o aviso ligado e com ele desligado é a MESMA."""
        con = self.catalogo()
        def sem_aviso(alloc):
            return {k: {c: v for c, v in a.items() if c != "aviso_colecao"}
                    for k, a in alloc.items()}
        com = sem_aviso(self.decks.allocate(con))
        self.cfg_decks({"coleccao_so_a_partir_de": None})
        sem = sem_aviso(self.decks.allocate(con))
        self.assertEqual(com, sem)
        self.assertFalse(any(a["aviso_colecao"] for a in self.decks.allocate(con).values()))

    def test_o_patamar_vem_do_config(self):
        con = self.catalogo()
        self.cfg_decks({"coleccao_so_a_partir_de": "rare"})
        aviso = self.por_slug(con)["azir"]["aviso_colecao"]
        self.assertNotIn("defy", aviso, "a rara passa a poder vir da Coleção")
        self.assertEqual(aviso.get("salvage"), 2)
        self.assertEqual(self.decks.raridades_da_colecao(),
                         frozenset({"rare", "epic", "showcase"}))

    def test_uma_raridade_que_nao_existe_rebenta(self):
        self.cfg_decks({"coleccao_so_a_partir_de": "mitica"})
        with self.assertRaises(ValueError) as cm:
            self.decks.raridade_da_colecao()
        self.assertIn("mítica", str(cm.exception))

    def test_as_proprias_tiram_o_aviso(self):
        con = self.catalogo()
        self.assertEqual(self.por_slug(con)["azir"]["aviso_colecao"].get("defy"), 4)
        self.proprias.ajustar(con, "azir", "tst-001-100", 4, source="test")
        self.assertNotIn("defy", self.por_slug(con)["azir"]["aviso_colecao"])

    def test_a_raridade_e_a_da_base_nao_a_da_arte_alternativa(self):
        con = self.catalogo()
        # A Defy alt art é `showcase` impressa e `rare` de base: é uma rara.
        self.assertEqual(self.decks.raridade_por_carta(con)["defy"], "rare")

    def test_o_contador_do_deck_e_a_soma_e_esta_no_payload(self):
        con = self.catalogo()
        p = self.decks.deck_payload(con, self.deck_id(con, "azir"))
        self.assertEqual(p["aviso_colecao"], 4 + 2 + 1 + 1)
        self.assertEqual(p["raridade_colecao"], "epic")
        cartas = {c["name"]: c for s in p["sections"] for c in s["cards"]}
        self.assertEqual(cartas["Salvage"]["aviso"], 2)
        self.assertEqual(cartas["Salvage"]["rarity"], "common")
        self.assertEqual(cartas["Emperor of the Sands"]["aviso"], 0)
        # A soma dos avisos das linhas é o contador do deck.
        self.assertEqual(sum(c["aviso"] for s in p["sections"] for c in s["cards"]),
                         p["aviso_colecao"])
        idx = {d["slug"]: d for d in self.decks.decks_index(con)}
        self.assertEqual(idx["azir"]["aviso_colecao"], p["aviso_colecao"])

    def test_uma_runa_nunca_avisa(self):
        """As runas não se contam nos decks: não tiram nada da Coleção."""
        con = self.catalogo()
        for a in self.decks.allocate(con).values():
            self.assertNotIn("fury rune", a["aviso_colecao"])


class TestRotasBuildCLI(Base):
    """8. As rotas, o `build`, a CLI e o `app.js`."""

    def test_a_rota_monta_desmonta_e_recusa(self):
        con = self.catalogo()
        self.cfg_decks({"montados": ["azir"]})
        from riftvault import server
        importlib.reload(server)
        cli = server.app.test_client()
        r = cli.post("/api/decks/montar", json={"slug": "ornn", "montado": True})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(sorted(r.get_json()["montados"]), ["azir", "ornn"])
        r = cli.post("/api/decks/montar", json={"slug": "ornn", "montado": False})
        self.assertEqual(r.get_json()["desmontados"], ["ornn"])
        self.assertEqual(cli.post("/api/decks/montar", json={}).status_code, 400)
        self.assertEqual(cli.post("/api/decks/montar",
                                  json={"slug": "xpto", "montado": True}).status_code, 404)
        d = cli.get("/api/decks.json").get_json()
        self.assertEqual({x["slug"]: x["montado"] for x in d["decks"]},
                         {"azir": True, "ornn": False})
        self.assertEqual(d["raridade_colecao"], "epic")

    def test_o_site_publicado_leva_o_estado_e_nao_o_botao(self):
        con = self.catalogo()
        self.cfg_decks({"montados": ["azir"]})
        from riftvault import build
        importlib.reload(build)
        out = self.v.root / "site"
        build.build(out, log=lambda *_: None)
        d = json.loads((out / "api" / "decks.json").read_text(encoding="utf-8"))
        self.assertFalse(d["editable"])
        self.assertEqual({x["slug"]: x["montado"] for x in d["decks"]},
                         {"azir": True, "ornn": False})
        js = (REPO / "riftvault" / "web" / "app.js").read_text(encoding="utf-8")
        # O botão só se desenha no modo edição.
        self.assertIn("state.editable ? `<button class=\"btn ", js)
        self.assertIn("api/decks/montar", js)

    def test_a_cli_monta_e_desmonta(self):
        con = self.catalogo()
        caminho = self.cfg_decks({"montados": ["azir", "ornn"]})
        from riftvault import cli as cli_mod
        importlib.reload(cli_mod)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cli_mod.main(["decks", "--desmontar", "ornn"])
        self.assertIn("desmontado", buf.getvalue())
        self.assertIn("DESMONTADO", buf.getvalue())
        # O que já lá estava fica como ELE o escreveu (aqui o slug); o que
        # entra de novo entra pelo `Nome:`.
        self.assertEqual(json.loads(caminho.read_text(encoding="utf-8"))["decks"]["montados"],
                         ["azir"])
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cli_mod.main(["decks", "--montar", "ornn"])
        self.assertEqual(json.loads(caminho.read_text(encoding="utf-8"))["decks"]["montados"],
                         ["azir", "Ornn"])

    def test_a_cli_do_deck_escreve_a_montagem(self):
        con = self.catalogo()
        self.cfg_decks({"montados": ["azir"]})
        from riftvault import cli as cli_mod
        importlib.reload(cli_mod)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cli_mod.main(["deck", "ornn"])
        texto = buf.getvalue()
        self.assertIn("DESMONTADO", texto)
        self.assertIn("Montagem", texto)
        self.assertIn("simulação", texto)
        self.assertIn("próprias", texto)

    def test_o_app_js_tem_a_vista_de_montagem_e_o_aviso(self):
        js = (REPO / "riftvault" / "web" / "app.js").read_text(encoding="utf-8")
        self.assertIn("function montagemHTML", js)
        self.assertIn("mont-tab", js)
        self.assertIn("c.aviso", js)
        css = (REPO / "riftvault" / "web" / "style.css").read_text(encoding="utf-8")
        # A tabela tem de virar cartão no telemóvel: ele monta com o telemóvel
        # na mão.
        self.assertIn(".mont-tab", css)
        self.assertRegex(css, r"@media \(max-width: 559px\)[^}]*\{[\s\S]{0,900}?\.mont-tab")
        self.assertIn("--warn", css)


if __name__ == "__main__":
    unittest.main(verbosity=1)

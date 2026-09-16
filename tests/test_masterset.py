"""A Coleção em três categorias: classificação, ordem e percentagens.

Decisão do André (2026-09-08, de manhã): *"as cartas que forem 'sigla-T' ou 'a'
no fim (de arte alternativa) não as quero na sequência do master set; quero-as
ordenadas depois do master set. A Coleção é de master set."*

E a que manda hoje (2026-09-14, à noite): *"quero masterset com playset /
runas 1 de cada / Alt Art, overnumbered, etc etc mete Playset na contagem /
mas só quero % de completo para masterset! / o que é Alt Art e Overnumbered,
etc etc é puramente coleção"*. Só o master set conta para a percentagem; a
coleção extra aparece a playset sem contar; os tokens e as signatures não
aparecem. A regra inteira, medida de ponta a ponta, está no
`test_tres_blocos.py`; aqui fica a mecânica dos blocos e do config.

O «runas 1 de cada» dessa frase foi revogado a 2026-09-15 (*"as runas que
estao no masterset […] vamos ate 3 como as outras cartas"*) — ver
`test_runas_3.py`.
"""

from __future__ import annotations

import importlib
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.fixture import Vault


class Base(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.close)
        from riftvault import a_subir, config, metrics
        importlib.reload(metrics)
        importlib.reload(a_subir)
        self.metrics, self.a_subir = metrics, a_subir
        self.config = config

    def com_config(self, extra: dict):
        import os
        caminho = self.v.root / "config.json"
        caminho.write_text(json.dumps(extra), encoding="utf-8")
        os.environ["RIFTVAULT_CONFIG"] = str(caminho)
        importlib.reload(self.config)
        self.config.load.cache_clear()

        def repor():
            os.environ.pop("RIFTVAULT_CONFIG", None)
            importlib.reload(self.config)
            self.config.load.cache_clear()

        self.addCleanup(repor)

    def edicao(self, com_runas: bool = False):
        """Uma base, a arte alternativa dela, uma signature e um token.

        Com `com_runas`, mais uma runa base e a arte alternativa dela — que é
        o bloco das runas especiais, "1 runa especial de cada".
        """
        con = self.v.connect()
        self.v.add_printing(con, "tst-001-100", "TST", 1, "Defy", api_sort=1)
        self.v.add_printing(con, "tst-001a-100", "TST", 1, "Defy",
                            variant="a", kind="alt_art", rarity="showcase", api_sort=2)
        self.v.add_printing(con, "tst-002-100", "TST", 2, "Brutalizer", api_sort=3)
        # O token vem intercalado a meio (é o que o `api_sort` da RiftScribe faz)
        # justamente para o teste da ordem ter alguma coisa que corrigir.
        self.v.add_printing(con, "tst-t01-100", "TST", 3, "Sprite",
                            variant="t01", kind="token", api_sort=4)
        self.v.add_printing(con, "tst-003-star-100", "TST", 4, "Unforgiven",
                            variant="star", kind="signature", api_sort=5)
        if com_runas:
            self.v.add_printing(con, "tst-005-100", "TST", 5, "Fury Rune",
                                card_type="Rune", api_sort=6)
            self.v.add_printing(con, "tst-005a-100", "TST", 5, "Fury Rune",
                                card_type="Rune", variant="a", kind="alt_art",
                                rarity="showcase", api_sort=7)
            self.v.add_printing(con, "tst-r01-100", "TST", 6, "Calm Rune",
                                card_type="Rune", variant="r01", kind="rune_promo",
                                api_sort=8)
        self.v.rebuild(con)
        return con


class TestClassificacao(Base):
    """Só a base conta; as variantes são coleção extra; `-T` e `*` não aparecem."""

    def test_so_a_base_conta_para_a_percentagem(self):
        casos = {
            "base": True,
            "signature": False,      # `OGN-299*` — escondida
            "rune_promo": False,     # `VEN-R01` — escondida desde 2026-09-15
            "special": False,        # `VEN-SP4` — promos, coleção extra
            "alt_art": False,        # `UNL-228a` — coleção extra
            "token": False,          # `UNL-T03` — escondido
        }
        for kind, esperado in casos.items():
            with self.subTest(kind=kind):
                self.assertIs(self.metrics.e_master(
                    {"variant_kind": kind, "is_token": 0}), esperado)

    def test_o_que_esta_na_pagina_e_tudo_menos_o_escondido(self):
        # A runa promo (`VEN-R01`, sem numeração de master set) está escondida
        # desde 2026-09-15 — ver `test_runas_fora.py`.
        casos = {"base": True, "alt_art": True, "rune_promo": False, "special": True,
                 "signature": False, "token": False}
        for kind, esperado in casos.items():
            with self.subTest(kind=kind):
                self.assertIs(self.metrics.e_colecao(
                    {"variant_kind": kind, "is_token": 0}), esperado)
                self.assertIs(self.metrics.escondida(
                    {"variant_kind": kind, "is_token": 0}), not esperado)

    def test_os_blocos(self):
        self.assertEqual(self.metrics.bloco({"variant_kind": "base", "is_token": 0}),
                         "master")
        self.assertEqual(self.metrics.bloco({"variant_kind": "alt_art", "is_token": 0}),
                         "alt_art")
        self.assertEqual(self.metrics.bloco({"variant_kind": "special", "is_token": 0}),
                         "special")
        self.assertEqual(self.metrics.bloco({"variant_kind": "token", "is_token": 1}),
                         "token")

    def test_a_runa_que_nao_e_base_vai_para_o_bloco_das_runas(self):
        """*"1 runa especial de cada para cada set"* — antes da cauda das alt arts.

        Desde 2026-09-15 só a arte alternativa (numerada) cai aqui: a runa
        promo, sem numeração de master set, está escondida e o escondido ganha
        ao bloco das runas — como a signature, abaixo."""
        self.assertEqual(self.metrics.bloco(
            {"variant_kind": "alt_art", "is_token": 0, "type": "Rune"}),
            "rune_special")
        self.assertEqual(self.metrics.bloco(
            {"variant_kind": "rune_promo", "is_token": 0, "type": "Rune"}),
            "rune_promo")
        self.assertTrue(self.metrics.escondida(
            {"variant_kind": "rune_promo", "is_token": 0, "type": "Rune"}))
        # A runa BASE fica na sequência.
        self.assertEqual(self.metrics.bloco(
            {"variant_kind": "base", "is_token": 0, "type": "Rune"}), "master")

    def test_a_signature_de_runa_nao_aparece_como_as_outras(self):
        """Não existe nenhuma hoje, mas a ordem é clara: o escondido ganha ao
        bloco das runas."""
        self.assertEqual(self.metrics.bloco(
            {"variant_kind": "signature", "is_token": 0, "type": "Rune"}),
            "signature")
        self.assertTrue(self.metrics.escondida(
            {"variant_kind": "signature", "is_token": 0, "type": "Rune"}))

    def test_so_conta_para_a_percentagem_o_bloco_master(self):
        self.assertTrue(self.metrics.conta_bloco("master"))
        for bloco in ("rune_special", "alt_art", "overnumbered", "special",
                      "token", "signature"):
            with self.subTest(bloco=bloco):
                self.assertFalse(self.metrics.conta_bloco(bloco))

    def test_variante_desconhecida_cai_num_bloco_visivel(self):
        """Um `b` ou um `sp7` novos não podem desaparecer da grelha."""
        self.com_config({"master_set": {"fora_da_percentagem": ["unknown"]}})
        self.assertEqual(self.metrics.bloco({"variant_kind": "unknown", "is_token": 0}),
                         "outras")

    def test_config_manda__listas_vazias_poem_ate_os_tokens_a_contar(self):
        self.com_config({"master_set": {"fora_da_percentagem": [], "escondidas": []}})
        self.assertEqual(self.metrics.bloco({"variant_kind": "token", "is_token": 1}),
                         "master")
        self.assertTrue(self.metrics.e_master({"variant_kind": "token", "is_token": 1}))

    def test_tirar_o_a_da_lista_poe_a_cauda_a_contar(self):
        """O «1 alt art de cada» de 2026-09-08 fica a uma linha de config."""
        self.com_config({"master_set": {"fora_da_percentagem": ["overnumbered"]}})
        self.assertTrue(self.metrics.e_master(
            {"variant_kind": "alt_art", "is_token": 0}))
        self.assertTrue(self.metrics.conta_bloco("alt_art"))
        self.assertNotIn("Coleção", self.metrics.rotulo("alt_art"))

    def test_o_rotulo_dos_blocos_de_fora_diz_colecao_e_o_alvo(self):
        """É a palavra dele — *"é puramente coleção"* — e o alvo que pedem."""
        # «1 de cada» desde 2026-09-16, mais o que os decks jogam — o bloco das
        # runas especiais é feito de artes alternativas e diz o mesmo.
        self.assertEqual(self.metrics.rotulo("alt_art"),
                         "Coleção — artes alternativas — 1 de cada, ou o que os decks jogam")
        self.assertEqual(self.metrics.rotulo("rune_special"),
                         "Coleção — runas especiais — 1 de cada, ou o que os decks jogam")
        # «1 de cada» desde 2026-09-15 (`master_set.um_de_cada`).
        self.assertEqual(self.metrics.rotulo("overnumbered"),
                         "Coleção — sobrenumeradas — 1 de cada")
        self.assertIsNone(self.metrics.rotulo("master"))


class TestConfigDasListas(Base):
    """As duas listas do `master_set` escrevem-se pelos sufixos, como ele fala."""

    def test_os_defaults_dao_os_kinds_certos(self):
        self.assertEqual(self.metrics.kinds_fora(),
                         frozenset({"alt_art", "rune_promo", "special",
                                    "token", "signature"}))
        self.assertEqual(self.metrics.kinds_escondidas(),
                         frozenset({"token", "signature", "rune_promo"}))
        self.assertTrue(self.metrics.fora_overnumbered())

    def test_o_escondido_esta_fora_da_percentagem_por_construcao(self):
        self.com_config({"master_set": {"fora_da_percentagem": [],
                                        "escondidas": ["*"]}})
        self.assertEqual(self.metrics.kinds_fora(), frozenset({"signature"}))
        self.assertFalse(self.metrics.e_master(
            {"variant_kind": "signature", "is_token": 0}))

    def test_sufixo_e_nome_da_variante_dizem_o_mesmo(self):
        self.com_config({"master_set": {"fora_da_percentagem": ["-T", "a"]}})
        por_sufixo = self.metrics.kinds_fora()
        self.com_config({"master_set": {"fora_da_percentagem": ["token", "alt_art"]}})
        self.assertEqual(por_sufixo, self.metrics.kinds_fora())

    def test_maiusculas_e_espacos_nao_contam(self):
        self.com_config({"master_set": {"escondidas": [" -t ", "A"]}})
        self.assertEqual(self.metrics.kinds_escondidas(),
                         frozenset({"token", "alt_art"}))

    def test_valor_desconhecido_rebenta_em_vez_de_ser_ignorado(self):
        """Uma variante nova tem de aparecer, não de sumir em silêncio."""
        for lista in ("fora_da_percentagem", "escondidas"):
            with self.subTest(lista=lista):
                self.com_config({"master_set": {lista: ["-T", "b"]}})
                with self.assertRaises(ValueError) as erro:
                    self.metrics.kinds_fora()
                self.assertIn("'b'", str(erro.exception))
                self.assertIn(lista, str(erro.exception))

    def test_o_nome_antigo_fora_continua_a_mandar(self):
        """Um config de 2026-09-08 a 2026-09-14 vale o que valia: fora da
        percentagem, mas na página — não esconde nada."""
        self.com_config({"master_set": {"fora": ["-T", "*"]}})
        self.assertEqual(self.metrics.kinds_fora(), frozenset({"token", "signature"}))
        self.assertEqual(self.metrics.kinds_escondidas(), frozenset())
        self.assertFalse(self.metrics.escondida({"variant_kind": "token", "is_token": 1}))

    def test_o_nome_mais_antigo_ainda_continua_a_mandar(self):
        """Um config escrito antes de 2026-09-08 não muda de comportamento."""
        self.com_config({"master_ignorar_variantes": ["alt_art"]})
        self.assertEqual(self.metrics.kinds_fora(), frozenset({"alt_art"}))
        self.assertTrue(self.metrics.e_master({"variant_kind": "token", "is_token": 1}))

    def test_com_os_dois_nomes_ganha_o_novo(self):
        self.com_config({"master_set": {"fora": ["-T"],
                                        "fora_da_percentagem": ["a"]}})
        self.assertEqual(self.metrics.kinds_fora(), frozenset({"alt_art"}))


class TestAlvos(Base):
    """UMA regra: o `um_de_cada` 1 (sobrenumeradas e promos, desde 2026-09-15),
    o resto o alvo de coleção do tipo — em todos os blocos. As runas deixaram
    de ser caso especial a 2026-09-15 (*"vamos ate 3 como as outras cartas"*);
    a regra inteira está no `test_runas_3.py`."""

    def test_a_runa_pede_3_base_ou_promo(self):
        """A arte alternativa da runa é uma arte alternativa: 1 desde
        2026-09-16 (`test_a_arte_alternativa_pede_1`)."""
        for kind in ("base", "rune_promo", "signature"):
            with self.subTest(kind=kind):
                self.assertEqual(
                    self.metrics.master_target("x", kind, "Rune", False), 3)

    def test_as_outras_cartas_pedem_o_playset_do_tipo_na_base_e_na_signature(self):
        for kind in ("base", "signature"):
            with self.subTest(kind=kind):
                self.assertEqual(self.metrics.master_target("x", kind, "Unit", False), 3)
                self.assertEqual(self.metrics.master_target("x", kind, "Legend", False), 1)
                self.assertEqual(
                    self.metrics.master_target("x", kind, "Battlefield", False), 1)

    def test_a_arte_alternativa_pede_1(self):
        """*"Alt Art e Overnumbered e assim quero apenas 1 de cada"* (2026-09-16),
        runas incluídas. O que os decks lhe acrescentam é o `alvo()` com a
        procura — `test_altart_decks.py`."""
        for tipo in ("Unit", "Rune", "Legend"):
            with self.subTest(tipo=tipo):
                self.assertEqual(self.metrics.master_target("x", "alt_art", tipo, False), 1)

    def test_a_promo_pede_1(self):
        """*"overnumbered e promos (SP) voltamos a 1 de cada"* — `test_alvo_1.py`."""
        self.assertEqual(self.metrics.master_target("x", "special", "Unit", False), 1)

    def test_o_token_pede_o_token_target(self):
        self.assertEqual(self.metrics.master_target("x", "token", None, True), 1)

    def test_o_playset_jogavel_da_runa_continua_12(self):
        """Colecionar e jogar são duas perguntas: os decks pedem as 12 na mesma."""
        self.assertEqual(self.metrics.playset_target("Rune", False), 12)

    def test_os_botoes_antigos_deixaram_de_ser_lidos(self):
        """`master_targets_by_variant` e companhia não fazem nada — um config
        velho com eles não muda o alvo."""
        self.com_config({"master_targets_by_variant": {"alt_art": 3, "base": 3},
                         "master_variantes_playset": ["alt_art"],
                         "master_base_follows_type": False})
        self.assertEqual(self.metrics.master_target("x", "alt_art", "Unit", False), 1)
        self.assertEqual(self.metrics.master_target("x", "base", "Legend", False), 1)

    def test_o_override_por_impressao_continua_a_ganhar(self):
        self.com_config({"master_target_overrides": {"tst-005-100": 12}})
        self.assertEqual(self.metrics.master_target("tst-005-100", "base", "Rune", False), 12)

    def test_desligar_o_bloco_das_runas_nao_mexe_no_alvo(self):
        """`tipos: []` desfaz o BLOCO; o alvo já não vem daqui."""
        self.com_config({"runas_especiais": {"tipos": []}})
        self.assertEqual(self.metrics.master_target("x", "base", "Rune", False), 3)

    def test_o_alvo_antigo_das_runas_deixou_de_ser_lido(self):
        """Um config de 2026-09-08 a 2026-09-15 com `alvo` (1 ou `"playset"`)
        não muda nada: a excepção saiu do código."""
        for alvo in (1, "playset", 12):
            with self.subTest(alvo=alvo):
                self.com_config({"runas_especiais": {"tipos": ["Rune"],
                                                     "excepto": ["base"],
                                                     "alvo": alvo}})
                # A arte alternativa pede 1 (2026-09-16), venha o que vier
                # no `alvo` velho; a base pede 3.
                self.assertEqual(
                    self.metrics.master_target("x", "alt_art", "Rune", False), 1)
                self.assertEqual(
                    self.metrics.master_target("x", "base", "Rune", False), 3)

    def test_o_alvo_da_runa_base_segue_a_percentagem_e_o_valor(self):
        """Uma cópia não fecha o tile — são precisas as 3, e a barra sabe."""
        from riftvault import collection
        con = self.edicao(com_runas=True)
        con.execute("INSERT INTO catalog.price_latest (printing_id, price_cents) "
                    "VALUES ('tst-005-100', 100)")
        p = self.metrics.set_payload(con, "TST")
        self.assertEqual(p["progress"]["master"]["done"], 0)
        # "se estivesse completa" também: 3 cópias da runa.
        self.assertEqual(p["progress"]["value"]["full"], 300)
        collection.adjust(con, "tst-005-100", 1, source="test")
        p = self.metrics.set_payload(con, "TST")
        self.assertEqual(p["progress"]["master"]["done"], 0)
        collection.adjust(con, "tst-005-100", 2, source="test")
        p = self.metrics.set_payload(con, "TST")
        self.assertEqual(p["progress"]["master"]["done"], 1)
        con.close()


class TestRunasEspeciais(Base):
    """`runas_especiais` — o critério do bloco das runas, escrito no config."""

    def test_o_default_e_runa_que_nao_seja_base_sem_alvo(self):
        o = self.metrics.opcoes_runa()
        self.assertEqual((o["tipos"], o["excepto"]), (["Rune"], ["base"]))
        self.assertNotIn("alvo", o)

    def test_o_rotulo_do_bloco_diz_1_de_cada(self):
        """O cabeçalho lê o mesmo alvo que o tile — 1, o das artes
        alternativas de que o bloco é feito (2026-09-16), mais os decks."""
        self.assertEqual(self.metrics.rotulo("rune_special"),
                         "Coleção — runas especiais — 1 de cada, ou o que os decks jogam")

    def test_lista_vazia_desliga_o_bloco(self):
        """Sem runas especiais, a alt art da runa volta para a cauda das alt arts."""
        self.com_config({"runas_especiais": {"tipos": []}})
        self.assertEqual(self.metrics.bloco(
            {"variant_kind": "alt_art", "is_token": 0, "type": "Rune"}), "alt_art")

    def test_uma_impressao_sem_tipo_nao_rebenta(self):
        """`UNL-T04` vem com `type: null` da API — e a grelha tem de o desenhar."""
        self.assertFalse(self.metrics.e_runa_especial(
            {"variant_kind": "token", "is_token": 1, "type": None}))
        self.assertEqual(self.metrics.bloco({"variant_kind": "base", "is_token": 0}),
                         "master")


class TestEscondidas(Base):
    """*"Nunca vou colocar nenhuma, não vale a pena estarem lá"* (2026-09-11).

    O `"*"` e o `"-T"` do `master_set.escondidas` tiram as signatures e os
    tokens da página inteira: nem grelha, nem separador, nem listas. O que
    ele tenha continua no vault.
    """

    def test_a_signature_e_o_token_nao_vao_para_a_grelha(self):
        con = self.edicao()
        p = self.metrics.set_payload(con, "TST")
        self.assertEqual([b["id"] for b in p["blocks"]], ["master", "alt_art"])
        ids = {pr["id"] for g in p["groups"] for pr in g["printings"]}
        self.assertNotIn("tst-003-star-100", ids)
        self.assertNotIn("tst-t01-100", ids)
        self.assertEqual(p["hidden_kinds"], ["rune_promo", "signature", "token"])
        con.close()

    def test_o_separador_conta_so_o_que_esta_na_pagina(self):
        con = self.edicao()
        n = {s["id"]: s["n_printings"] for s in self.metrics.sets_payload(con)}
        self.assertEqual(n["TST"], 3)
        con.close()

    def test_o_que_ele_tem_de_escondido_continua_a_valer(self):
        from riftvault import collection
        con = self.edicao()
        collection.adjust(con, "tst-003-star-100", 1, source="test")
        con.execute("INSERT INTO catalog.price_latest (printing_id, price_cents) "
                    "VALUES ('tst-003-star-100', 5000)")
        val = self.metrics.set_payload(con, "TST")["progress"]["value"]
        self.assertEqual(val["owned"], 5000)
        self.assertEqual(val["full"], 0)   # não é coisa que se feche
        con.close()

    def test_tirar_o_asterisco_das_escondidas_poe_as_signatures_de_volta(self):
        """A decisão fica a uma linha de config de distância, como as outras."""
        self.com_config({"master_set": {"fora_da_percentagem": ["a", "*"],
                                        "escondidas": ["-T"]}})
        con = self.edicao()
        p = self.metrics.set_payload(con, "TST")
        self.assertEqual([b["id"] for b in p["blocks"]],
                         ["master", "alt_art", "signature"])
        self.assertEqual(p["blocks"][2]["label"], "Coleção — signatures — playset")
        self.assertEqual(p["progress"]["master"]["total"], 2)
        con.close()


class TestOrdem(Base):
    """Primeiro a sequência do master set, depois os blocos. Nunca intercalados."""

    def test_o_payload_marca_o_bloco_de_cada_impressao(self):
        con = self.edicao()
        p = self.metrics.set_payload(con, "TST")
        blocos = {pr["id"]: pr["block"] for g in p["groups"] for pr in g["printings"]}
        self.assertEqual(blocos, {"tst-001-100": "master", "tst-002-100": "master",
                                  "tst-001a-100": "alt_art"})
        con.close()

    def test_a_ordem_dos_blocos_e_master_runas_alt_art(self):
        con = self.edicao(com_runas=True)
        p = self.metrics.set_payload(con, "TST")
        self.assertEqual([b["id"] for b in p["blocks"]],
                         ["master", "rune_special", "alt_art"])
        # O primeiro não leva rótulo: é a sequência normal, sem cabeçalho.
        self.assertIsNone(p["blocks"][0]["label"])
        self.assertEqual(p["blocks"][1]["label"],
                         "Coleção — runas especiais — 1 de cada, ou o que os decks jogam")
        self.assertEqual(p["blocks"][2]["label"],
                         "Coleção — artes alternativas — 1 de cada, ou o que os decks jogam")
        # E o payload diz quais é que contam para a percentagem: só o primeiro.
        self.assertEqual([b["counts"] for b in p["blocks"]], [True, False, False])
        con.close()

    def test_o_bloco_das_runas_leva_a_alt_art_deixa_a_base_e_esconde_a_promo(self):
        """Desde 2026-09-15 a runa promo (sem numeração) nem aparece."""
        con = self.edicao(com_runas=True)
        p = self.metrics.set_payload(con, "TST")
        blocos = {pr["id"]: pr["block"] for g in p["groups"] for pr in g["printings"]}
        self.assertEqual(blocos["tst-005-100"], "master")        # runa base
        self.assertEqual(blocos["tst-005a-100"], "rune_special")
        self.assertNotIn("tst-r01-100", blocos)
        con.close()

    def test_a_sequencia_do_master_sai_por_numero_de_colecao(self):
        """Sem nada de fora pelo meio — é isso que ele pediu."""
        con = self.edicao()
        p = self.metrics.set_payload(con, "TST")
        seq = [pr["code"] for g in p["groups"] for pr in g["printings"]
               if pr["block"] == "master"]
        self.assertEqual(seq, ["TST-001", "TST-002"])
        con.close()

    def test_a_ordem_da_grelha_nao_intercala(self):
        con = self.edicao(com_runas=True)
        ordem = self.metrics.ordem_da_grelha(self.metrics.set_payload(con, "TST"))
        self.assertEqual(ordem, [
            ("master", "tst-001-100"),
            ("master", "tst-002-100"),
            ("master", "tst-005-100"),
            ("rune_special", "tst-005a-100"),
            ("alt_art", "tst-001a-100"),
        ])
        con.close()

    def test_um_bloco_vazio_nao_aparece(self):
        con = self.v.connect()
        self.v.add_printing(con, "tst-001-100", "TST", 1, "Defy")
        self.v.rebuild(con)
        p = self.metrics.set_payload(con, "TST")
        self.assertEqual([b["id"] for b in p["blocks"]], ["master"])
        con.close()


class TestPercentagem(Base):
    """A barra é só o master set; a coleção extra tem conta própria."""

    def test_denominador_e_so_a_sequencia(self):
        con = self.edicao(com_runas=True)
        prog = self.metrics.set_payload(con, "TST")["progress"]["master"]
        # 2 bases + a runa base. A alt art da Unit, a alt art da runa e a
        # promo são coleção extra; o token e a signature não aparecem.
        self.assertEqual(prog["total"], 3)
        con.close()

    def test_cada_bloco_tem_contador_proprio_e_diz_se_conta(self):
        from riftvault import collection
        con = self.edicao()
        collection.adjust(con, "tst-001a-100", 3, source="test")    # alt art completa
        p = self.metrics.set_payload(con, "TST")
        blocos = {b["id"]: b for b in p["blocks"]}
        self.assertEqual((blocos["alt_art"]["done"], blocos["alt_art"]["total"]), (1, 1))
        self.assertFalse(blocos["alt_art"]["counts"])
        # A alt art completa não mexe na percentagem.
        self.assertEqual(p["progress"]["master"]["done"], 0)
        con.close()

    def test_a_soma_dos_blocos_que_contam_e_a_barra(self):
        con = self.edicao(com_runas=True)
        p = self.metrics.set_payload(con, "TST")
        soma = sum(b["total"] for b in p["blocks"] if b["counts"])
        self.assertEqual(soma, p["progress"]["master"]["total"])
        # E os chips por raridade medem o mesmo denominador.
        self.assertEqual(sum(r["total"] for r in p["progress"]["rarities"]), soma)
        con.close()

    def test_os_alvos_de_cada_bloco(self):
        """Playset na sequência, runas incluídas (2026-09-15); 1 de cada nas
        artes alternativas (2026-09-16) — sem decks a pedi-las."""
        con = self.edicao(com_runas=True)
        p = self.metrics.set_payload(con, "TST")
        alvos = {pr["id"]: pr["target"] for g in p["groups"] for pr in g["printings"]}
        self.assertEqual(alvos["tst-001-100"], 3)    # Unit base: playset
        self.assertEqual(alvos["tst-005-100"], 3)    # Rune base: 3, como as outras
        self.assertEqual(alvos["tst-005a-100"], 1)   # runa especial: é alt art, 1
        self.assertNotIn("tst-r01-100", alvos)       # runa promo: escondida
        self.assertEqual(alvos["tst-001a-100"], 1)   # alt art de Unit: 1 de cada
        con.close()

    def test_valor_se_estivesse_completa_e_so_o_master_set(self):
        con = self.edicao()
        for pid in ("tst-001-100", "tst-001a-100", "tst-t01-100"):
            con.execute("INSERT INTO catalog.price_latest (printing_id, price_cents) "
                        "VALUES (?, 100)", (pid,))
        val = self.metrics.set_payload(con, "TST")["progress"]["value"]
        # 3 cópias da base, a 1,00 €. A alt art é coleção extra; o token não aparece.
        self.assertEqual(val["full"], 300)
        con.close()


class TestListasDeCompra(Base):
    """O `masterset` é a página inteira (sem o escondido); as LISTAS são só o
    bloco 1 — a coleção extra acompanha-se, não se compra (André, 2026-09-15).
    O grosso está em `test_extra_so_track.py`; aqui fica a mecânica do `excluir`."""

    def test_o_ambito_e_a_pagina_menos_o_escondido(self):
        """Sem os tokens, as signatures e — desde 2026-09-15 — a runa promo."""
        con = self.edicao(com_runas=True)
        escopo = self.a_subir.masterset(con)
        self.assertEqual(sorted(escopo), [
            "tst-001-100", "tst-001a-100", "tst-002-100",
            "tst-005-100", "tst-005a-100"])
        self.assertNotIn("tst-t01-100", escopo)
        self.assertNotIn("tst-003-star-100", escopo)
        self.assertNotIn("tst-r01-100", escopo)
        con.close()

    def test_a_lista_e_so_o_master_set(self):
        """A alt art e as runas especiais têm alvo na grelha, não na lista."""
        con = self.edicao(com_runas=True)
        p = self.a_subir.master_faltas(con)
        itens = {x["printing_id"]: x for s in p["sets"] for x in s["items"]}
        self.assertEqual(sorted(itens), ["tst-001-100", "tst-002-100", "tst-005-100"])
        # A runa base pede as 3 desde 2026-09-15, como a Unit.
        self.assertEqual(itens["tst-005-100"]["missing"], 3)
        self.assertEqual(p["scope"]["excluded"], 2)
        self.assertTrue(p["scope"]["so_master_set"])
        con.close()

    def test_a_colecao_extra_sai_com_o_bloco_por_motivo(self):
        con = self.edicao(com_runas=True)
        escopo, saem = self.a_subir.excluir(
            self.a_subir.masterset(con), self.a_subir.opcoes()["excluir"])
        self.assertNotIn("tst-001a-100", escopo)
        self.assertEqual(saem["tst-001a-100"]["excluded_by"], "alt_art")
        self.assertEqual(saem["tst-005a-100"]["excluded_by"], "rune_special")
        # A signature e a runa promo já nem chegam aqui: estão escondidas.
        for pid in ("tst-003-star-100", "tst-r01-100"):
            self.assertNotIn(pid, escopo)
            self.assertNotIn(pid, saem)
        resumo = self.a_subir.resumo_fora(saem, self.a_subir.opcoes()["excluir"])
        self.assertEqual(resumo["excluded"], 2)
        # Pela ordem da grelha, com o nome do cabeçalho para a página escrever.
        self.assertEqual(resumo["excluded_by"],
                         [{"criterio": "rune_special", "n": 1},
                          {"criterio": "alt_art", "n": 1}])
        self.assertEqual(resumo["excluded_labels"],
                         {"rune_special": "runas especiais", "alt_art": "artes alternativas"})
        con.close()

    def test_desligado_o_showcase_da_cauda_nao_cai_na_exclusao_da_sequencia(self):
        """Com o `so_master_set` desligado (o mundo de 2026-09-14), a alt art de
        raridade `showcase` fica na mesma: é outro bloco (`so_no_master`)."""
        con = self.edicao()
        escopo, saem = self.a_subir.excluir(
            self.a_subir.masterset(con), self.a_subir.opcoes()["excluir"], so_master=False)
        self.assertIn("tst-001a-100", escopo)
        self.assertNotIn("tst-003-star-100", escopo)
        self.assertNotIn("tst-003-star-100", saem)
        con.close()

    def test_desligar_o_so_no_master_poe_a_cauda_debaixo_das_exclusoes(self):
        con = self.edicao()
        _, saem = self.a_subir.excluir(
            self.a_subir.masterset(con),
            {"tipos": ["signature"], "raridades": ["showcase"], "so_no_master": False},
            so_master=False)
        self.assertIn("tst-001a-100", saem)
        self.assertEqual(saem["tst-001a-100"]["excluded_by"], "showcase")
        con.close()

    def test_desligado_um_bloco_inteiro_pode_sair_das_listas(self):
        """`excluir.blocos` — com o `so_master_set` desligado, tira só o que se escrever."""
        con = self.edicao(com_runas=True)
        fora = {"blocos": ["alt_art", "rune_special"]}
        ficam, saem = self.a_subir.excluir(self.a_subir.masterset(con), fora, so_master=False)
        self.assertNotIn("tst-001a-100", ficam)
        self.assertEqual(saem["tst-001a-100"]["excluded_by"], "alt_art")
        self.assertEqual(saem["tst-005a-100"]["excluded_by"], "rune_special")
        self.assertIn("tst-001-100", ficam)
        resumo = self.a_subir.resumo_fora(saem, fora, so_master=False)
        self.assertEqual(resumo["excluded"], 2)
        self.assertFalse(resumo["so_master_set"])
        self.assertEqual(resumo["excluded_by"],
                         [{"criterio": "alt_art", "n": 1},
                          {"criterio": "rune_special", "n": 1}])
        con.close()


if __name__ == "__main__":
    unittest.main()

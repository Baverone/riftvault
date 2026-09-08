"""A Coleção em três blocos: classificação, ordem e percentagens.

Decisão do André (2026-09-08, de manhã): *"as cartas que forem 'sigla-T' ou 'a'
no fim (de arte alternativa) não as quero na sequência do master set; quero-as
ordenadas depois do master set. A Coleção é de master set."*

E à tarde, o que estes testes medem: *"master set playset todo seguido; 1 runa
especial de cada para cada set; no fim 1 alt art de cada."* As artes
alternativas voltaram para dentro da percentagem, com alvo 1, sem saírem da
cauda da grelha; os tokens continuam fora.
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
        from riftvault import a_subir, config, metrics, venda
        importlib.reload(metrics)
        importlib.reload(a_subir)
        importlib.reload(venda)
        self.metrics, self.a_subir, self.venda = metrics, a_subir, venda
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

        Com `com_runas`, mais uma runa base (playset 12) e a arte alternativa
        dela — que é o bloco 2, "1 runa especial de cada".
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
    """Só o `-T` fica fora da coleção; o resto conta, em três blocos."""

    def test_so_o_token_fica_fora_da_colecao(self):
        casos = {
            "base": True,
            "signature": True,       # `OGN-299*` — ele não a nomeou
            "rune_promo": True,      # `VEN-R01`
            "special": True,         # `VEN-SP4`
            "alt_art": True,         # `UNL-228a` — 1 de cada, na cauda
            "token": False,          # `UNL-T03`
        }
        for kind, esperado in casos.items():
            with self.subTest(kind=kind):
                self.assertIs(self.metrics.e_master(
                    {"variant_kind": kind, "is_token": 0}), esperado)

    def test_os_tres_blocos_da_colecao_e_o_bloco_de_fora(self):
        self.assertEqual(self.metrics.bloco({"variant_kind": "base", "is_token": 0}),
                         "master")
        self.assertEqual(self.metrics.bloco({"variant_kind": "alt_art", "is_token": 0}),
                         "alt_art")
        self.assertEqual(self.metrics.bloco({"variant_kind": "token", "is_token": 1}),
                         "token")

    def test_a_runa_que_nao_e_base_vai_para_o_bloco_das_runas(self):
        """*"1 runa especial de cada para cada set"* — antes da cauda das alt arts."""
        for kind in ("alt_art", "rune_promo", "signature"):
            with self.subTest(kind=kind):
                self.assertEqual(self.metrics.bloco(
                    {"variant_kind": kind, "is_token": 0, "type": "Rune"}),
                    "rune_special")
        # A runa BASE fica na sequência: é ela que leva o playset (12).
        self.assertEqual(self.metrics.bloco(
            {"variant_kind": "base", "is_token": 0, "type": "Rune"}), "master")

    def test_so_conta_para_a_percentagem_o_que_esta_na_colecao(self):
        for bloco in ("master", "rune_special", "alt_art"):
            with self.subTest(bloco=bloco):
                self.assertTrue(self.metrics.conta_bloco(bloco))
        self.assertFalse(self.metrics.conta_bloco("token"))

    def test_variante_desconhecida_cai_num_bloco_visivel(self):
        """Um `b` ou um `sp7` novos não podem desaparecer da grelha."""
        self.com_config({"master_set": {"fora": ["unknown"]}})
        self.assertEqual(self.metrics.bloco({"variant_kind": "unknown", "is_token": 0}),
                         "outras")

    def test_config_manda__lista_vazia_poe_ate_os_tokens_a_contar(self):
        self.com_config({"master_set": {"fora": []}})
        self.assertEqual(self.metrics.bloco({"variant_kind": "token", "is_token": 1}),
                         "master")

    def test_por_o_a_de_volta_no_fora_tira_a_cauda_da_percentagem(self):
        """A decisão de manhã continua a uma linha de config de distância."""
        self.com_config({"master_set": {"fora": ["-T", "a"]}})
        self.assertFalse(self.metrics.e_master(
            {"variant_kind": "alt_art", "is_token": 0}))
        self.assertFalse(self.metrics.conta_bloco("alt_art"))
        self.assertIn("Fora", self.metrics.rotulo("alt_art"))


class TestConfigDosSufixos(Base):
    """`master_set.fora` escreve-se pelos sufixos do código, como o André fala."""

    def test_os_sufixos_do_default_dao_os_kinds_certos(self):
        self.assertEqual(self.metrics.kinds_fora(), frozenset({"token"}))

    def test_sufixo_e_nome_da_variante_dizem_o_mesmo(self):
        self.com_config({"master_set": {"fora": ["-T", "a"]}})
        por_sufixo = self.metrics.kinds_fora()
        self.com_config({"master_set": {"fora": ["token", "alt_art"]}})
        self.assertEqual(por_sufixo, self.metrics.kinds_fora())

    def test_maiusculas_e_espacos_nao_contam(self):
        self.com_config({"master_set": {"fora": [" -t ", "A"]}})
        self.assertEqual(self.metrics.kinds_fora(), frozenset({"token", "alt_art"}))

    def test_valor_desconhecido_rebenta_em_vez_de_ser_ignorado(self):
        """Uma variante nova tem de aparecer, não de sumir em silêncio."""
        self.com_config({"master_set": {"fora": ["-T", "b"]}})
        with self.assertRaises(ValueError) as erro:
            self.metrics.kinds_fora()
        self.assertIn("'b'", str(erro.exception))

    def test_nome_antigo_da_lista_continua_a_mandar(self):
        """Um config escrito antes de 2026-09-08 não muda de comportamento."""
        self.com_config({"master_ignorar_variantes": ["alt_art"]})
        self.assertEqual(self.metrics.kinds_fora(), frozenset({"alt_art"}))
        self.assertTrue(self.metrics.e_master({"variant_kind": "token", "is_token": 1}))

    def test_com_os_dois_nomes_ganha_o_novo(self):
        self.com_config({"master_ignorar_variantes": ["alt_art"],
                         "master_set": {"fora": ["-T"]}})
        self.assertEqual(self.metrics.kinds_fora(), frozenset({"token"}))


class TestRunasEspeciais(Base):
    """`runas_especiais` — o critério do bloco 2, escrito no config."""

    def test_o_default_e_runa_que_nao_seja_base(self):
        o = self.metrics.opcoes_runa()
        self.assertEqual((o["tipos"], o["excepto"], o["alvo"]), (["Rune"], ["base"], 1))

    def test_o_alvo_do_bloco_muda_no_config(self):
        self.com_config({"runas_especiais": {"tipos": ["Rune"], "excepto": ["base"],
                                             "alvo": 3}})
        self.assertEqual(
            self.metrics.master_target("x", "alt_art", "Rune", False), 3)

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


class TestSignaturesPreparadas(Base):
    """`"*"` no `master_set.fora` tira as signatures. DESLIGADO à espera dele."""

    def test_por_omissao_a_signature_esta_no_master_set(self):
        con = self.edicao()
        p = self.metrics.set_payload(con, "TST")
        blocos = {pr["id"]: pr["block"] for g in p["groups"] for pr in g["printings"]}
        self.assertEqual(blocos["tst-003-star-100"], "master")
        # 4 impressões na percentagem: 2 bases, a signature e a alt art (a 1).
        self.assertEqual(p["progress"]["master"]["total"], 4)
        con.close()

    def test_ligar_manda_a_signature_para_um_bloco_no_fim(self):
        self.com_config({"master_set": {"fora": ["-T", "*"]}})
        con = self.edicao()
        p = self.metrics.set_payload(con, "TST")
        self.assertEqual([b["id"] for b in p["blocks"]],
                         ["master", "alt_art", "token", "signature"])
        # E leva rótulo próprio, não cai no «outras».
        self.assertIn("signature", p["blocks"][3]["label"])
        ordem = self.metrics.ordem_da_grelha(p)
        self.assertEqual(ordem[-1], ("signature", "tst-003-star-100"))
        con.close()

    def test_ligar_tira_a_signature_da_percentagem(self):
        """É a mesma pergunta: sair da coleção é sair do denominador."""
        self.com_config({"master_set": {"fora": ["-T", "*"]}})
        con = self.edicao()
        p = self.metrics.set_payload(con, "TST")
        self.assertEqual(p["progress"]["master"]["total"], 3)   # eram 4
        con.close()


class TestOrdem(Base):
    """Primeiro a sequência do master set, depois os blocos. Nunca intercalados."""

    def test_o_payload_marca_o_bloco_de_cada_impressao(self):
        con = self.edicao()
        p = self.metrics.set_payload(con, "TST")
        blocos = {pr["id"]: pr["block"] for g in p["groups"] for pr in g["printings"]}
        self.assertEqual(blocos["tst-001-100"], "master")
        self.assertEqual(blocos["tst-002-100"], "master")
        self.assertEqual(blocos["tst-003-star-100"], "master")
        self.assertEqual(blocos["tst-001a-100"], "alt_art")
        self.assertEqual(blocos["tst-t01-100"], "token")
        con.close()

    def test_a_ordem_dos_blocos_e_master_runas_alt_art_e_so_depois_o_de_fora(self):
        con = self.edicao(com_runas=True)
        p = self.metrics.set_payload(con, "TST")
        self.assertEqual([b["id"] for b in p["blocks"]],
                         ["master", "rune_special", "alt_art", "token"])
        # O primeiro não leva rótulo: é a sequência normal, sem cabeçalho.
        self.assertIsNone(p["blocks"][0]["label"])
        self.assertIn("Runas especiais", p["blocks"][1]["label"])
        self.assertIn("Artes alternativas", p["blocks"][2]["label"])
        self.assertIn("tokens", p["blocks"][3]["label"])
        # E o payload diz quais é que contam para a percentagem.
        self.assertEqual([b["counts"] for b in p["blocks"]],
                         [True, True, True, False])
        con.close()

    def test_o_bloco_das_runas_leva_as_duas_especiais_e_deixa_a_base(self):
        con = self.edicao(com_runas=True)
        p = self.metrics.set_payload(con, "TST")
        blocos = {pr["id"]: pr["block"] for g in p["groups"] for pr in g["printings"]}
        self.assertEqual(blocos["tst-005-100"], "master")        # runa base
        self.assertEqual(blocos["tst-005a-100"], "rune_special")
        self.assertEqual(blocos["tst-r01-100"], "rune_special")
        con.close()

    def test_a_sequencia_do_master_sai_por_numero_de_colecao(self):
        """Sem nada de fora pelo meio — é isso que ele pediu."""
        con = self.edicao()
        p = self.metrics.set_payload(con, "TST")
        seq = [pr["code"] for g in p["groups"] for pr in g["printings"]
               if pr["block"] == "master"]
        self.assertEqual(seq, ["TST-001", "TST-002", "TST-004star"])
        con.close()

    def test_a_ordem_da_grelha_nao_intercala(self):
        """O token vem no meio pelo `api_sort` e tem de sair para o fim."""
        con = self.edicao(com_runas=True)
        ordem = self.metrics.ordem_da_grelha(self.metrics.set_payload(con, "TST"))
        self.assertEqual(ordem, [
            ("master", "tst-001-100"),
            ("master", "tst-002-100"),
            ("master", "tst-003-star-100"),
            ("master", "tst-005-100"),
            ("rune_special", "tst-005a-100"),
            ("rune_special", "tst-r01-100"),
            ("alt_art", "tst-001a-100"),
            ("token", "tst-t01-100"),
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
    """A barra soma os três blocos da coleção; o de fora tem conta própria."""

    def test_denominador_conta_os_tres_blocos_e_ignora_o_token(self):
        con = self.edicao(com_runas=True)
        prog = self.metrics.set_payload(con, "TST")["progress"]["master"]
        # 8 impressões: 3 bases + signature + runa base (master), a alt art da
        # runa e a promo (runas especiais), a alt art da Unit. O token fica fora.
        self.assertEqual(prog["total"], 7)
        con.close()

    def test_cada_bloco_tem_contador_proprio_e_diz_se_conta(self):
        from riftvault import collection
        con = self.edicao()
        collection.adjust(con, "tst-t01-100", 1, source="test")     # token completo
        collection.adjust(con, "tst-001a-100", 1, source="test")    # alt art completa
        p = self.metrics.set_payload(con, "TST")
        blocos = {b["id"]: b for b in p["blocks"]}
        self.assertEqual((blocos["token"]["done"], blocos["token"]["total"]), (1, 1))
        self.assertEqual((blocos["alt_art"]["done"], blocos["alt_art"]["total"]), (1, 1))
        self.assertFalse(blocos["token"]["counts"])
        self.assertTrue(blocos["alt_art"]["counts"])
        # A alt art conta na percentagem; o token, não.
        self.assertEqual(p["progress"]["master"]["done"], 1)
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
        """Bloco 1 em playset; runas especiais e alt arts a 1."""
        con = self.edicao(com_runas=True)
        p = self.metrics.set_payload(con, "TST")
        alvos = {pr["id"]: pr["target"] for g in p["groups"] for pr in g["printings"]}
        self.assertEqual(alvos["tst-001-100"], 3)    # Unit base: playset
        self.assertEqual(alvos["tst-005-100"], 12)   # Rune base: playset da runa
        self.assertEqual(alvos["tst-005a-100"], 1)   # runa especial
        self.assertEqual(alvos["tst-r01-100"], 1)    # runa especial
        self.assertEqual(alvos["tst-001a-100"], 1)   # "1 alt art de cada"
        self.assertEqual(alvos["tst-t01-100"], 1)    # token_target
        con.close()

    def test_valor_se_estivesse_completa_conta_a_cauda_e_ignora_o_token(self):
        con = self.edicao()
        for pid in ("tst-001-100", "tst-001a-100", "tst-t01-100"):
            con.execute("INSERT INTO catalog.price_latest (printing_id, price_cents) "
                        "VALUES (?, 100)", (pid,))
        val = self.metrics.set_payload(con, "TST")["progress"]["value"]
        # 3 cópias da base + 1 da arte alternativa, a 1,00 €. O token fica fora.
        self.assertEqual(val["full"], 400)
        con.close()


class TestListasDeCompra(Base):
    """O que está fora da coleção não se compra; a cauda passou a comprar-se."""

    def test_o_ambito_e_a_colecao_inteira_menos_os_tokens(self):
        con = self.edicao(com_runas=True)
        escopo = self.a_subir.masterset(con)
        self.assertEqual(sorted(escopo), [
            "tst-001-100", "tst-001a-100", "tst-002-100", "tst-003-star-100",
            "tst-005-100", "tst-005a-100", "tst-r01-100"])
        self.assertNotIn("tst-t01-100", escopo)
        con.close()

    def test_faltam_1_de_cada_alt_art_e_1_de_cada_runa_especial(self):
        """*"faltam N"* passou a incluir a cauda, e a 1 — não ao playset."""
        con = self.edicao(com_runas=True)
        itens = {x["printing_id"]: x
                 for s in self.a_subir.master_faltas(con)["sets"] for x in s["items"]}
        self.assertEqual(itens["tst-001a-100"]["missing"], 1)
        self.assertEqual(itens["tst-005a-100"]["missing"], 1)
        self.assertEqual(itens["tst-r01-100"]["missing"], 1)
        self.assertEqual(itens["tst-005-100"]["missing"], 12)   # a runa base
        self.assertNotIn("tst-t01-100", itens)
        con.close()

    def test_o_showcase_da_cauda_nao_cai_na_exclusao_da_sequencia(self):
        """A alt art tem raridade `showcase` e fica na mesma: é outro bloco."""
        con = self.edicao()
        escopo, saem = self.a_subir.excluir(
            self.a_subir.masterset(con), self.a_subir.opcoes()["excluir"])
        self.assertIn("tst-001a-100", escopo)
        # A signature, essa, está na sequência e sai.
        self.assertIn("tst-003-star-100", saem)
        con.close()

    def test_desligar_o_so_no_master_poe_a_cauda_debaixo_das_exclusoes(self):
        con = self.edicao()
        _, saem = self.a_subir.excluir(
            self.a_subir.masterset(con),
            {"tipos": ["signature"], "raridades": ["showcase"], "so_no_master": False})
        self.assertIn("tst-001a-100", saem)
        con.close()


if __name__ == "__main__":
    unittest.main()

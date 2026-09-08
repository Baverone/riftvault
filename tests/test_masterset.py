"""A Coleção é o master set: classificação, ordem em blocos e percentagens.

Decisão do André (2026-09-08): *"as cartas que forem 'sigla-T' ou 'a' no fim
(de arte alternativa) não as quero na sequência do master set; quero-as
ordenadas depois do master set. A Coleção é de master set."*
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

    def edicao(self):
        """Uma edição com uma base, a arte alternativa dela, uma signature e um token."""
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
        self.v.rebuild(con)
        return con


class TestClassificacao(Base):
    """`-T` no código e número acabado em `a` ficam fora; o resto fica."""

    def test_alt_art_e_token_fora__base_signature_e_promos_dentro(self):
        casos = {
            "base": True,
            "signature": True,       # `OGN-299*` — ele não a nomeou
            "rune_promo": True,      # `VEN-R01`
            "special": True,         # `VEN-SP4`
            "alt_art": False,        # `UNL-228a`
            "token": False,          # `UNL-T03`
        }
        for kind, esperado in casos.items():
            with self.subTest(kind=kind):
                self.assertIs(self.metrics.e_master(
                    {"variant_kind": kind, "is_token": 0}), esperado)

    def test_o_bloco_sai_da_mesma_regra(self):
        self.assertEqual(self.metrics.bloco({"variant_kind": "base", "is_token": 0}),
                         "master")
        self.assertEqual(self.metrics.bloco({"variant_kind": "token", "is_token": 1}),
                         "token")
        self.assertEqual(self.metrics.bloco({"variant_kind": "alt_art", "is_token": 0}),
                         "alt_art")

    def test_variante_desconhecida_cai_num_bloco_visivel(self):
        """Um `b` ou um `sp7` novos não podem desaparecer da grelha."""
        self.com_config({"master_ignorar_variantes": ["unknown"]})
        self.assertEqual(self.metrics.bloco({"variant_kind": "unknown", "is_token": 0}),
                         "outras")

    def test_config_manda__lista_vazia_poe_todos_no_master(self):
        self.com_config({"master_ignorar_variantes": []})
        self.assertTrue(self.metrics.e_master(
            {"variant_kind": "alt_art", "is_token": 0}))
        self.assertEqual(self.metrics.bloco({"variant_kind": "token", "is_token": 1}),
                         "master")


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

    def test_a_ordem_dos_blocos_e_master_token_alt_art(self):
        con = self.edicao()
        p = self.metrics.set_payload(con, "TST")
        self.assertEqual([b["id"] for b in p["blocks"]], ["master", "token", "alt_art"])
        # O primeiro não leva rótulo: é a sequência normal, sem cabeçalho.
        self.assertIsNone(p["blocks"][0]["label"])
        self.assertIn("tokens", p["blocks"][1]["label"])
        self.assertIn("artes alternativas", p["blocks"][2]["label"])
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
        con = self.edicao()
        ordem = self.metrics.ordem_da_grelha(self.metrics.set_payload(con, "TST"))
        self.assertEqual(ordem, [
            ("master", "tst-001-100"),
            ("master", "tst-002-100"),
            ("master", "tst-003-star-100"),
            ("token", "tst-t01-100"),
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
    """As barras medem só o master set — e os blocos de fora têm conta própria."""

    def test_denominador_ignora_alt_art_e_token(self):
        con = self.edicao()
        prog = self.metrics.set_payload(con, "TST")["progress"]["master"]
        # 5 impressões, 3 no master set (base, base, signature).
        self.assertEqual(prog["total"], 3)
        con.close()

    def test_o_bloco_de_fora_tem_contador_proprio(self):
        """"tens N de M" — sem entrar na percentagem."""
        from riftvault import collection
        con = self.edicao()
        collection.adjust(con, "tst-t01-100", 1, source="test")     # token completo
        p = self.metrics.set_payload(con, "TST")
        blocos = {b["id"]: b for b in p["blocks"]}
        self.assertEqual((blocos["token"]["done"], blocos["token"]["total"]), (1, 1))
        self.assertEqual((blocos["alt_art"]["done"], blocos["alt_art"]["total"]), (0, 1))
        # E a percentagem não mexeu com o token completo.
        self.assertEqual(p["progress"]["master"]["done"], 0)
        con.close()

    def test_o_alvo_das_de_fora_continua_a_aparecer(self):
        """ALVO e CONTA são campos diferentes (2026-09-02). O tile mostra 0/3."""
        con = self.edicao()
        p = self.metrics.set_payload(con, "TST")
        alvos = {pr["id"]: pr["target"] for g in p["groups"] for pr in g["printings"]}
        self.assertEqual(alvos["tst-001a-100"], 3)   # segue o playset da Unit
        self.assertEqual(alvos["tst-t01-100"], 1)    # token_target
        con.close()

    def test_valor_se_estivesse_completa_ignora_as_de_fora(self):
        con = self.edicao()
        for pid in ("tst-001-100", "tst-001a-100", "tst-t01-100"):
            con.execute("INSERT INTO catalog.price_latest (printing_id, price_cents) "
                        "VALUES (?, 100)", (pid,))
        val = self.metrics.set_payload(con, "TST")["progress"]["value"]
        # Só a base tem preço dentro do master set: 3 cópias x 1,00 €.
        self.assertEqual(val["full"], 300)
        con.close()


class TestListasDeCompra(Base):
    """O que está fora do master set não se compra."""

    def test_a_subir_e_master_faltas_nao_veem_as_de_fora(self):
        con = self.edicao()
        escopo = self.a_subir.masterset(con)
        self.assertEqual(sorted(escopo), ["tst-001-100", "tst-002-100",
                                          "tst-003-star-100"])
        m = self.a_subir.master_faltas(con)
        ids = [x["printing_id"] for s in m["sets"] for x in s["items"]]
        self.assertNotIn("tst-001a-100", ids)
        self.assertNotIn("tst-t01-100", ids)
        con.close()


if __name__ == "__main__":
    unittest.main()

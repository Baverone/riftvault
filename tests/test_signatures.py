"""As signatures fora da Coleção — a regra inteira, num sítio só.

André, 2026-09-09: *"no riftvault, das coleções tira as signatures, fazemos 1
Alt Art de cada mas as signature não"*.

E 2026-09-11: *"podes tirar as signatures da coleção, nunca vou colocar
nenhuma, não vale a pena estarem lá"*.

A regra numa frase: **uma impressão de signature (o `*` do código impresso,
`variant_kind = "signature"`) está ESCONDIDA** — não entra na sequência do
master set, não entra em bloco nenhum da grelha, não entra no denominador da
percentagem nem nas contagens por níveis nem nas listas de compra. O que ele
tenha continua no vault, no valor e na Venda.

**Um ponto de verdade só:** `metrics.escondida`, pela lista
`master_set.escondidas` (o `"*"` traduz-se para `variant_kind = "signature"`
em `metrics.SUFIXO_KIND`), que o `e_master` lê por construção. É o mesmo
critério que o `a_subir.excluir` já usava para as tirar das listas de compra —
não há segunda definição de "isto é uma signature".

Estes testes valem por todos os consumidores da regra: a Coleção (blocos e
percentagem), a contagem por níveis, as wantlists (por edição e por nível) e o
«A subir». Se um dia um deles passar a responder sozinho, é aqui que se vê.
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
        """Uma Unit base, a alt art dela, uma runa base, a alt art da runa —
        e uma signature de cada uma das três coisas, para se ver que nenhuma
        delas escapa por um bloco diferente."""
        con = self.v.connect()
        self.v.add_printing(con, "tst-001-100", "TST", 1, "Defy", api_sort=1)
        self.v.add_printing(con, "tst-001a-100", "TST", 1, "Defy", variant="a",
                            kind="alt_art", rarity="showcase", api_sort=2)
        self.v.add_printing(con, "tst-001-star-100", "TST", 1, "Defy",
                            variant="star", kind="signature", rarity="showcase",
                            api_sort=3)
        self.v.add_printing(con, "tst-005-100", "TST", 5, "Fury Rune",
                            card_type="Rune", api_sort=4)
        self.v.add_printing(con, "tst-005a-100", "TST", 5, "Fury Rune",
                            card_type="Rune", variant="a", kind="alt_art",
                            api_sort=5)
        # A signature de uma RUNA é as duas coisas; a saída ganha ao bloco 2.
        self.v.add_printing(con, "tst-005-star-100", "TST", 5, "Fury Rune",
                            card_type="Rune", variant="star", kind="signature",
                            api_sort=6)
        self.v.rebuild(con)
        con.execute("INSERT INTO catalog.price_latest (printing_id, price_cents) "
                    "VALUES ('tst-001-star-100', 200000)")
        return con

    def blocos(self, con):
        p = self.metrics.set_payload(con, "TST")
        return {pr["id"]: pr["block"] for g in p["groups"] for pr in g["printings"]}


class TestARegra(Base):
    """Uma pergunta, uma função: `metrics.e_master`."""

    def test_a_signature_nao_faz_parte_da_colecao(self):
        self.assertFalse(self.metrics.e_master(
            {"variant_kind": "signature", "is_token": 0}))

    def test_o_criterio_e_o_mesmo_das_listas_de_compra(self):
        """O `*` do config é o `variant_kind` que o `a_subir.excluir` já usava.

        Se um dia a tradução do sufixo mudar, isto parte — que é o ponto: são a
        mesma coisa escrita de duas maneiras, não duas regras.
        """
        self.assertEqual(self.metrics.SUFIXO_KIND["*"], "signature")
        self.assertIn("signature", self.metrics.kinds_fora())
        tipos, _ = self.a_subir.criterios(self.a_subir.opcoes()["excluir"])
        self.assertIn("signature", tipos)

    def test_esta_escondida(self):
        self.assertTrue(self.metrics.escondida(
            {"variant_kind": "signature", "is_token": 0}))
        self.assertIn("signature", self.metrics.kinds_escondidas())


class TestColecao(Base):
    """Nem na sequência, nem nas runas especiais, nem em bloco nenhum."""

    def test_nao_vai_para_a_grelha(self):
        con = self.edicao()
        self.assertNotIn("tst-001-star-100", self.blocos(con))
        con.close()

    def test_a_signature_de_uma_runa_tambem_sai(self):
        """A runa especial ganha à alt art, mas o escondido ganha às duas."""
        con = self.edicao()
        b = self.blocos(con)
        self.assertEqual(b["tst-005a-100"], "rune_special")
        self.assertNotIn("tst-005-star-100", b)
        con.close()

    def test_nao_ha_bloco_de_signatures_e_a_barra_e_so_a_sequencia(self):
        con = self.edicao()
        p = self.metrics.set_payload(con, "TST")
        self.assertNotIn("signature", [b["id"] for b in p["blocks"]])
        self.assertEqual(p["hidden_kinds"], ["signature", "token"])
        # A barra são as duas da sequência: base e runa base.
        self.assertEqual(p["progress"]["master"]["total"], 2)
        self.assertEqual(sum(b["total"] for b in p["blocks"] if b["counts"]),
                         p["progress"]["master"]["total"])
        con.close()

    def test_a_que_ele_tem_continua_a_valer(self):
        """Sai da página, não da caixa nem do valor."""
        from riftvault import collection
        con = self.edicao()
        collection.adjust(con, "tst-001-star-100", 1, source="test")
        p = self.metrics.set_payload(con, "TST")
        self.assertEqual(p["progress"]["value"]["owned"], 200000)
        # E não entra no "se estivesse completa": 2000 € de signature não são
        # preço de fechar a coleção.
        self.assertEqual(p["progress"]["value"]["full"], 0)
        con.close()


class TestContagemPorNiveis(Base):
    """Os degraus 1/2/3 medem o mesmo âmbito da barra — sem signatures."""

    def test_o_ambito_dos_niveis_nao_leva_signatures(self):
        """São as 2 da barra: base e runa base."""
        con = self.edicao()
        self.assertEqual(len(self.metrics.itens_da_colecao(con)), 2)
        n = self.metrics.niveis_payload(con)
        self.assertEqual(n["levels"][0]["total"], 2)
        self.assertEqual(n["by_set"]["TST"][0]["total"], 2)
        con.close()

    def test_o_ultimo_degrau_continua_a_ser_a_barra(self):
        """A promessa da contagem por níveis, com as signatures fora."""
        from riftvault import collection
        con = self.edicao()
        collection.adjust(con, "tst-001-100", 3, source="test")
        p = self.metrics.set_payload(con, "TST")
        prog = p["progress"]
        self.assertEqual(prog["levels"][-1]["done"], prog["master"]["done"])
        self.assertEqual(prog["levels"][-1]["total"], prog["master"]["total"])
        con.close()


class TestListasDeCompra(Base):
    """«A subir», «Master set» e as wantlists da Coleção — todas pelo âmbito."""

    def test_o_ambito_do_a_subir_nao_leva_signatures(self):
        con = self.edicao()
        escopo = self.a_subir.masterset(con)
        self.assertNotIn("tst-001-star-100", escopo)
        self.assertNotIn("tst-005-star-100", escopo)
        self.assertEqual(len(escopo), 4)
        con.close()

    def test_a_lista_do_master_set_nao_leva_signatures(self):
        con = self.edicao()
        m = self.a_subir.master_faltas(con)
        pids = [x["printing_id"] for s in m["sets"] for x in s["items"]]
        self.assertNotIn("tst-001-star-100", pids)
        self.assertNotIn("tst-005-star-100", pids)
        # E não são contadas como "excluídas": nunca estiveram no âmbito. O que
        # a página conta como excluído são as duas alt arts — a coleção extra,
        # que desde 2026-09-15 fica fora das listas (`so_master_set`) —, e
        # nenhuma pelo critério `signature`.
        self.assertEqual(m["scope"]["excluded"], 2)
        self.assertEqual({x["criterio"]: x["n"] for x in m["scope"]["excluded_by"]},
                         {"alt_art": 1, "rune_special": 1})
        self.assertEqual(pids, ["tst-001-100", "tst-005-100"])
        con.close()

    def test_a_wantlist_da_edicao_nao_leva_signatures__em_nenhum_nivel(self):
        con = self.edicao()
        for nivel in (1, 2, None):
            with self.subTest(nivel=nivel):
                p = self.a_subir.wantlist(con, "TST", nivel=nivel)
                self.assertNotIn("tst-001-star-100",
                                 [x["printing_id"] for x in p["items"]])
                self.assertNotIn("Defy (V.3)", p["text"])
        con.close()


class TestVenda(Base):
    """A consequência que ele não pediu — e que hoje não tem efeito nenhum.

    O âmbito da Venda é "não é o bloco `master`", e as signatures passaram a
    estar nesse caso: uma que ele tenha e nenhum deck use aparece como candidata
    a venda, como já acontecia com os tokens. **É pergunta para ele** — hoje ele
    não tem signature nenhuma na caixa (medido a 2026-09-09), por isso a lista
    não mexeu; fica fixado para não mudar sem se dar por isso.
    """

    def test_uma_signature_que_ele_tenha_aparece_como_candidata(self):
        from riftvault import collection
        con = self.edicao()
        collection.adjust(con, "tst-001-star-100", 1, source="test")
        itens = {x["printing_id"]: x for x in self.venda.listar(con)["items"]}
        self.assertIn("tst-001-star-100", itens)
        self.assertEqual(itens["tst-001-star-100"]["qty"], 1)
        self.assertEqual(itens["tst-001-star-100"]["block"], "signature")
        con.close()


class TestVoltarAtras(Base):
    """Tirar o `*` do config põe tudo como estava — é uma linha, como sempre."""

    def test_sem_o_asterisco_a_signature_volta_a_todos_os_sitios(self):
        self.com_config({"master_set": {"fora_da_percentagem": [],
                                        "escondidas": ["-T"]}})
        con = self.edicao()
        self.assertTrue(self.metrics.e_master(
            {"variant_kind": "signature", "is_token": 0}))
        self.assertEqual(self.blocos(con)["tst-001-star-100"], "master")
        self.assertEqual(
            self.metrics.set_payload(con, "TST")["progress"]["master"]["total"], 6)
        # E aí voltam a sair das listas de compra pelo `a_subir.excluir`, que é
        # a decisão de 2026-09-08 e continua de pé.
        m = self.a_subir.master_faltas(con)
        pids = [x["printing_id"] for s in m["sets"] for x in s["items"]]
        self.assertNotIn("tst-001-star-100", pids)
        self.assertNotIn("tst-005-star-100", pids)
        # A da sequência sai pelo TIPO `signature`. A signature da RUNA volta
        # para o bloco das runas especiais, onde o `so_no_master` não a
        # excluía — era exactamente a confusão que a saída resolve —, e hoje
        # sai com o bloco inteiro, como as duas alt arts: a coleção extra não
        # entra nas listas (`so_master_set`, 2026-09-15). Cada uma conta uma
        # vez, e a soma dos critérios é o total.
        por_criterio = {x["criterio"]: x["n"] for x in m["scope"]["excluded_by"]}
        self.assertEqual(por_criterio, {"signature": 1, "rune_special": 2, "alt_art": 1})
        self.assertEqual(m["scope"]["excluded"], 4)
        self.assertEqual(sum(por_criterio.values()), m["scope"]["excluded"])
        self.assertEqual(pids, ["tst-001-100", "tst-005-100"])
        con.close()

    def test_so_fora_da_percentagem_poe_as_num_bloco_visivel(self):
        """O meio-termo de 2026-09-09: fora da barra, mas na grelha."""
        self.com_config({"master_set": {"fora_da_percentagem": ["*"],
                                        "escondidas": ["-T"]}})
        con = self.edicao()
        b = self.blocos(con)
        self.assertEqual(b["tst-001-star-100"], "signature")
        p = self.metrics.set_payload(con, "TST")
        blocos = {b["id"]: b for b in p["blocks"]}
        self.assertFalse(blocos["signature"]["counts"])
        self.assertEqual(blocos["signature"]["label"], "Coleção — signatures — playset")
        # A signature da RUNA cai no bloco das runas especiais (a runa especial
        # ganha à variante), e é por isso que esse bloco deixa de contar: uma
        # variante que está fora da percentagem pode lá cair, e o `conta_bloco`
        # não deixa que conte por esse caminho. A barra fica com a base, a alt
        # art dela e a runa base — 3, e não 4: a alt art da runa vai com o
        # bloco. É o preço de pôr as signatures a meio caminho.
        self.assertEqual(b["tst-005-star-100"], "rune_special")
        self.assertFalse(blocos["rune_special"]["counts"])
        self.assertEqual(p["progress"]["master"]["total"], 3)
        con.close()


if __name__ == "__main__":
    unittest.main()

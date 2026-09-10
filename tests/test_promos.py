"""As promos `VEN-SP` fora da Coleção — a regra inteira, num sítio só.

André, 2026-09-10: *"no riftvault, Vendetta, deparei-me com as VEN-SP (promos).
Quero que as promos fiquem também à parte, tal como as signature e as
overnumbered"*.

A regra numa frase: **uma impressão promo (`variant_kind = "special"`, o sufixo
`-SP` do código impresso) não faz parte da Coleção** — não entra na sequência do
master set, nem no bloco das runas especiais, nem no bloco das artes
alternativas, nem no denominador da percentagem, nem nas contagens por níveis,
nem nas listas de compra. Continua na grelha, num bloco próprio no fim
(«Fora da coleção — promos») e com alvo 1, para a que ele TEM continuar visível.

**Não são as runas promo.** As `VEN-R01..R06` são `rune_promo` e ficam dentro da
Coleção, no bloco das runas especiais — é a decisão dele de 2026-09-08 (*"1 runa
especial de cada para cada set"*), e no VEN são elas que enchem esse bloco. Ele
nomeou as `VEN-SP`.

**Um ponto de verdade só:** `metrics.fora_da_colecao`, pela mesma lista
`master_set.fora`, que ganhou a palavra `"promo"`. O `e_master` (a percentagem),
o `bloco` (a grelha) e o âmbito das listas de compra perguntam todos à mesma
função — é a arquitetura das signatures (2026-09-09) e das sobrenumeradas
(2026-09-10), para a terceira categoria.

Estes testes valem por todos os consumidores da regra: a Coleção (blocos e
percentagem), a contagem por níveis, as wantlists (por edição e por nível), o
«A subir», a lista do «Master set» e a Venda. Se um dia um deles passar a
responder sozinho, é aqui que se vê.
"""

from __future__ import annotations

import importlib
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.fixture import Vault

# O tamanho nominal da edição de brincar, e o da série das promos — como no
# catálogo real, onde o VEN tem 166 cartas e as promos são `VEN-SPn/006`.
TAMANHO = 100
PROMOS = 6


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
        """Uma edição com as três coisas que esta regra tem de separar.

        A promo `TST-SP4/006`, que sai; a runa promo `TST-R01`, que fica (é a
        outra decisão dele); e a Unit base que PARTILHA o número de coleção com
        a promo — a ARMADILHA 1 do CLAUDE.md, e a razão de as lanes existirem.
        """
        con = self.v.connect()
        add = self.v.add_printing
        add(con, "tst-004-100", "TST", 4, "Dune Surfer", api_sort=1, size=TAMANHO)
        add(con, "tst-004a-100", "TST", 4, "Dune Surfer", variant="a",
            kind="alt_art", api_sort=2, size=TAMANHO)
        add(con, "tst-005-100", "TST", 5, "Fury Rune", card_type="Rune",
            api_sort=3, size=TAMANHO)
        # As duas do VEN que se parecem e não são a mesma coisa: a promo (sai) e
        # a runa promo (fica, no bloco das runas especiais).
        add(con, "tst-sp4-006", "TST", 4, "Sett, Brawler", variant="sp4",
            kind="special", lane="sp", rarity="epic", api_sort=4,
            codigo=f"TST-SP4/{PROMOS:03d}")
        add(con, "tst-r01", "TST", 1, "Calm Rune", card_type="Rune",
            variant="r01", kind="rune_promo", lane="r", api_sort=5,
            codigo="TST-R01")
        self.v.rebuild(con)
        con.execute("INSERT INTO catalog.price_latest (printing_id, price_cents) "
                    "VALUES ('tst-sp4-006', 1625)")
        return con

    # A que sai, e as quatro que ficam.
    FORA = ("tst-sp4-006",)
    DENTRO = ("tst-004-100", "tst-004a-100", "tst-005-100", "tst-r01")

    def blocos(self, con):
        p = self.metrics.set_payload(con, "TST")
        return {pr["id"]: pr["block"] for g in p["groups"] for pr in g["printings"]}


class TestOCriterio(Base):
    """A promo é uma VARIANTE — o `-SP` do código, o `special` do catálogo."""

    def test_a_palavra_dele_traduz_se_para_a_variante(self):
        self.assertEqual(self.metrics.PALAVRA_KIND["promo"], "special")
        # E é o mesmo kind que o sufixo do código impresso já dava.
        self.assertEqual(self.metrics.SUFIXO_KIND["-sp"], "special")

    def test_as_tres_escritas_dizem_o_mesmo(self):
        """`promo`, `-SP` e `special` — a palavra dele, o sufixo e o nome interno."""
        vistas = []
        for escrita in ("promo", "-SP", "special"):
            self.com_config({"master_set": {"fora": [escrita]}})
            vistas.append(self.metrics.kinds_fora())
        self.assertEqual(vistas, [frozenset({"special"})] * 3)

    def test_a_promo_nao_e_sobrenumerada__por_isso_precisava_de_regra_propria(self):
        """`VEN-SP4/006` é a 4 de uma série de 6: o critério de ontem não lhe toca."""
        promo = {"public_code": "VEN-SP4/006", "collector_number": 4}
        self.assertEqual(self.metrics.tamanho_do_set(promo), PROMOS)
        self.assertFalse(self.metrics.e_overnumbered(promo))

    def test_a_lista_do_config_ja_traz_a_palavra(self):
        self.assertIn("special", self.metrics.kinds_fora())
        # E continua a levar as outras duas decisões: é a mesma lista.
        self.assertIn("signature", self.metrics.kinds_fora())
        self.assertTrue(self.metrics.fora_overnumbered())

    def test_um_valor_desconhecido_continua_a_rebentar(self):
        """Ponto 6 das "Superfícies não validadas": um sufixo novo tem de dar erro."""
        self.com_config({"master_set": {"fora": ["promo", "sp7"]}})
        with self.assertRaises(ValueError) as erro:
            self.metrics.kinds_fora()
        # E a mensagem oferece a palavra nova a quem se engana a escrevê-la.
        self.assertIn("promo", str(erro.exception))


class TestARunaPromoFica(Base):
    """A outra decisão dele, de 2026-09-08, não foi apagada por esta."""

    def test_a_runa_promo_continua_dentro_da_colecao(self):
        con = self.edicao()
        self.assertTrue(self.metrics.e_master(
            {"variant_kind": "rune_promo", "is_token": 0, "type": "Rune"}))
        self.assertEqual(self.blocos(con)["tst-r01"], "rune_special")
        con.close()

    def test_tirar_as_promos_nao_tira_as_runas_promo(self):
        """São dois `variant_kind` diferentes e duas entradas diferentes da lista."""
        self.assertNotIn("rune_promo", self.metrics.kinds_fora())

    def test_quem_as_quiser_fora_escreve_o_R(self):
        """Existe, e é uma linha — mas tira-as também da percentagem."""
        self.com_config({"master_set": {"fora": ["promo", "-R"]}})
        self.assertEqual(self.metrics.kinds_fora(),
                         frozenset({"special", "rune_promo"}))


class TestColecao(Base):
    """Nem na sequência, nem nas runas especiais, nem nas artes alternativas."""

    def test_a_promo_nao_faz_parte_da_colecao(self):
        self.assertFalse(self.metrics.e_master(
            {"variant_kind": "special", "is_token": 0}))

    def test_vai_para_um_bloco_proprio_no_fim(self):
        con = self.edicao()
        self.assertEqual(self.blocos(con)["tst-sp4-006"], "special")
        self.assertIn("promos", self.metrics.rotulo("special"))
        con.close()

    def test_a_unit_que_partilha_o_numero_fica_onde_estava(self):
        """ARMADILHA 1: a `TST-004` e a `TST-SP4` têm o mesmo número, não a mesma lane."""
        con = self.edicao()
        b = self.blocos(con)
        self.assertEqual(b["tst-004-100"], "master")
        self.assertEqual(b["tst-004a-100"], "alt_art")
        con.close()

    def test_o_alvo_da_promo_e_1(self):
        """Uma Unit base pediria 3; fora da coleção pede 1, como as signatures."""
        con = self.edicao()
        tiles = {pr["id"]: pr for g in self.metrics.set_payload(con, "TST")["groups"]
                 for pr in g["printings"]}
        self.assertEqual(tiles["tst-sp4-006"]["target"], 1)
        self.assertEqual(tiles["tst-004-100"]["target"], 3)
        con.close()

    def test_o_bloco_nao_conta_para_a_percentagem(self):
        con = self.edicao()
        p = self.metrics.set_payload(con, "TST")
        blocos = {b["id"]: b for b in p["blocks"]}
        self.assertFalse(blocos["special"]["counts"])
        self.assertEqual(blocos["special"]["total"], 1)
        self.assertEqual(p["progress"]["master"]["total"], len(self.DENTRO))
        self.assertEqual(sum(b["total"] for b in p["blocks"] if b["counts"]),
                         p["progress"]["master"]["total"])
        con.close()

    def test_a_que_ele_tem_continua_visivel_e_contada_no_bloco(self):
        """Sai da conta da coleção, não da grelha nem da caixa."""
        from riftvault import collection
        con = self.edicao()
        collection.adjust(con, "tst-sp4-006", 1, source="test")
        p = self.metrics.set_payload(con, "TST")
        tiles = {pr["id"]: pr for g in p["groups"] for pr in g["printings"]}
        self.assertEqual(tiles["tst-sp4-006"]["qty"], 1)
        blocos = {b["id"]: b for b in p["blocks"]}
        self.assertEqual((blocos["special"]["done"], blocos["special"]["total"]),
                         (1, 1))
        # E não entra no "se estivesse completa": não é preço de fechar a coleção.
        self.assertEqual(p["progress"]["value"]["full"], 0)
        # Mas continua a valer no que ele TEM — a caixa é a caixa.
        self.assertEqual(p["progress"]["value"]["owned"], 1625)
        con.close()

    def test_a_ordem_da_grelha_poe_o_bloco_depois_da_colecao(self):
        con = self.edicao()
        ordem = self.metrics.ordem_da_grelha(self.metrics.set_payload(con, "TST"))
        blocos = [b for b, _ in ordem]
        self.assertEqual(blocos[-1], "special")
        self.assertLess(max(i for i, b in enumerate(blocos)
                            if self.metrics.conta_bloco(b)),
                        blocos.index("special"))
        con.close()


class TestContagemPorNiveis(Base):
    """Os degraus 1/2/3 medem o mesmo âmbito da barra — sem promos."""

    def test_o_ambito_dos_niveis_nao_leva_promos(self):
        con = self.edicao()
        self.assertEqual(len(self.metrics.itens_da_colecao(con)), len(self.DENTRO))
        n = self.metrics.niveis_payload(con)
        self.assertEqual(n["levels"][0]["total"], len(self.DENTRO))
        self.assertEqual(n["by_set"]["TST"][0]["total"], len(self.DENTRO))
        con.close()

    def test_o_ultimo_degrau_continua_a_ser_a_barra(self):
        """A promessa da contagem por níveis, com as promos fora."""
        from riftvault import collection
        con = self.edicao()
        collection.adjust(con, "tst-004-100", 3, source="test")
        prog = self.metrics.set_payload(con, "TST")["progress"]
        self.assertEqual(prog["levels"][-1]["done"], prog["master"]["done"])
        self.assertEqual(prog["levels"][-1]["total"], prog["master"]["total"])
        con.close()

    def test_os_euros_da_promo_saem_do_custo_de_fechar(self):
        con = self.edicao()
        for nivel in self.metrics.niveis_payload(con)["levels"]:
            with self.subTest(k=nivel["k"]):
                self.assertEqual(nivel["cents"], 0)
        con.close()


class TestPartilhaComOASubir(Base):
    """As listas de compra excluem pelo MESMO critério — não têm cópia da regra."""

    def test_o_ambito_do_a_subir_e_exactamente_o_que_o_e_master_deixa_passar(self):
        """A partilha, fixada: uma função responde às duas páginas.

        Se um dia o `a_subir` passar a calcular o seu próprio âmbito, isto
        parte — que é o ponto.
        """
        con = self.edicao()
        escopo = set(self.a_subir.masterset(con))
        pela_metrica = {r["printing_id"] for r in
                        con.execute("SELECT * FROM catalog.printings")
                        if self.metrics.e_master(r)}
        self.assertEqual(escopo, pela_metrica)
        self.assertEqual(escopo, set(self.DENTRO))
        con.close()

    def test_nenhuma_promo_entra_em_lista_de_compra_nenhuma(self):
        """A rede de segurança: se uma entrar por algum lado, isto apanha-a.

        São os cinco consumidores da regra — o âmbito do «A subir», a lista do
        «Master set», e as wantlists nos três degraus.
        """
        con = self.edicao()
        ambitos = {"a_subir": set(self.a_subir.masterset(con))}
        m = self.a_subir.master_faltas(con)
        ambitos["master_faltas"] = {x["printing_id"]
                                    for s in m["sets"] for x in s["items"]}
        for nivel in (1, 2, None):
            p = self.a_subir.wantlist(con, "TST", nivel=nivel)
            ambitos[f"wantlist:{nivel}"] = {x["printing_id"] for x in p["items"]}
        for nome, pids in ambitos.items():
            with self.subTest(consumidor=nome):
                self.assertEqual(pids & set(self.FORA), set())
        con.close()

    def test_a_runa_promo_continua_a_poder_entrar_nas_listas(self):
        """O reverso: tirar as promos não tirou nada mais das listas de compra."""
        con = self.edicao()
        self.assertIn("tst-r01", set(self.a_subir.masterset(con)))
        con.close()

    def test_nao_sao_contadas_como_excluidas__nunca_estiveram_no_ambito(self):
        """A página diz quantas TIROU; estas saem antes, com a coleção."""
        con = self.edicao()
        self.assertEqual(self.a_subir.master_faltas(con)["scope"]["excluded"], 0)
        con.close()


class TestVenda(Base):
    """A consequência que ele não pediu — a mesma das signatures e das de ontem.

    O âmbito da Venda é "não é o bloco `master`", e as promos passaram a estar
    nesse caso: a que ele tem e nenhum deck usa aparece como candidata a venda.
    **É pergunta para ele** — hoje é 1 impressão no `vault.db` real (`VEN-SP5`
    Ezreal, Prodigy, 18,87 €). Fica fixado para não mudar sem se dar por isso.
    """

    def test_uma_promo_que_ele_tenha_aparece_como_candidata(self):
        from riftvault import collection
        con = self.edicao()
        collection.adjust(con, "tst-sp4-006", 1, source="test")
        itens = {x["printing_id"]: x for x in self.venda.listar(con)["items"]}
        self.assertIn("tst-sp4-006", itens)
        self.assertEqual(itens["tst-sp4-006"]["qty"], 1)
        self.assertEqual(itens["tst-sp4-006"]["block"], "special")
        con.close()


class TestVoltarAtras(Base):
    """Tirar o `promo` do config põe tudo como estava — uma linha."""

    def test_sem_a_palavra_a_promo_volta_a_todos_os_sitios(self):
        self.com_config({"master_set": {"fora": ["-T", "*", "overnumbered"]}})
        con = self.edicao()
        self.assertNotIn("special", self.metrics.kinds_fora())
        self.assertEqual(self.blocos(con)["tst-sp4-006"], "master")
        self.assertEqual(
            self.metrics.set_payload(con, "TST")["progress"]["master"]["total"],
            len(self.DENTRO) + 1)
        self.assertIn("tst-sp4-006", set(self.a_subir.masterset(con)))
        con.close()


if __name__ == "__main__":
    unittest.main()

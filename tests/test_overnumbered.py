"""As sobrenumeradas fora da Coleção — a regra inteira, num sítio só.

André, 2026-09-10: *"no riftvault, também não quero para a coleção as
overnumbered"*.

A regra numa frase: **uma impressão cujo número de coleccionador passa o
tamanho da edição (as «300/298») não faz parte da Coleção** — não entra na
sequência do master set, nem no bloco das runas especiais, nem no bloco das
artes alternativas, nem no denominador da percentagem, nem nas contagens por
níveis, nem nas listas de compra. Continua na grelha, num bloco próprio no fim
e com alvo 1, para as que ele TENHA continuarem visíveis e contadas.

**O critério é o CÓDIGO IMPRESSO**, como todas as decisões dele sobre a
Coleção: o `public_code` traz o número E o tamanho da edição (`OGN-299*/298`),
por isso o tamanho não é um número escrito à mão nem uma segunda consulta.

**Um ponto de verdade só:** `metrics.fora_da_colecao`, pela lista
`master_set.fora`, que passou a levar `"overnumbered"` a par dos sufixos. O
`e_master` (a percentagem), o `bloco` (a grelha) e o âmbito do «A subir»
perguntam todos à mesma função — é a mesma arquitetura das signatures
(2026-09-09), para outra categoria.

Estes testes valem por todos os consumidores da regra: a Coleção (blocos e
percentagem), a contagem por níveis, as wantlists (por edição e por nível), o
«A subir» e a lista do «Master set». Se um dia um deles passar a responder
sozinho, é aqui que se vê.
"""

from __future__ import annotations

import importlib
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.fixture import Vault

# O tamanho nominal da edição de brincar: tudo acima de 100 é sobrenumerado.
TAMANHO = 100


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
        """Uma edição de 100 com as quatro coisas que a regra tem de separar.

        Dentro do tamanho: a Unit base, a alt art dela, a runa base e a alt art
        da runa. Acima dele: a reimpressão showcase de topo de set, a signature
        que se lhe agarra e a alt art de uma runa — para se ver que a saída
        ganha ao bloco das runas especiais e que a signature NÃO muda de bloco.
        """
        con = self.v.connect()
        add = self.v.add_printing
        add(con, "tst-001-100", "TST", 1, "Defy", api_sort=1, size=TAMANHO)
        add(con, "tst-001a-100", "TST", 1, "Defy", variant="a", kind="alt_art",
            rarity="showcase", api_sort=2, size=TAMANHO)
        add(con, "tst-005-100", "TST", 5, "Fury Rune", card_type="Rune",
            api_sort=3, size=TAMANHO)
        add(con, "tst-005a-100", "TST", 5, "Fury Rune", card_type="Rune",
            variant="a", kind="alt_art", api_sort=4, size=TAMANHO)
        # Acima do tamanho da edição: a ARMADILHA 2 do CLAUDE.md — a mesma carta
        # lógica reaparece na mesma edição com número de coleção próprio.
        add(con, "tst-101-100", "TST", 101, "Defy", rarity="showcase",
            api_sort=5, size=TAMANHO)
        add(con, "tst-101-star-100", "TST", 101, "Defy", variant="star",
            kind="signature", rarity="showcase", api_sort=6, size=TAMANHO)
        add(con, "tst-105a-100", "TST", 105, "Fury Rune", card_type="Rune",
            variant="a", kind="alt_art", api_sort=7, size=TAMANHO)
        self.v.rebuild(con)
        con.execute("INSERT INTO catalog.price_latest (printing_id, price_cents) "
                    "VALUES ('tst-101-100', 200000)")
        return con

    # As três que saem por serem sobrenumeradas, e as quatro que ficam.
    ACIMA = ("tst-101-100", "tst-101-star-100", "tst-105a-100")
    DENTRO = ("tst-001-100", "tst-001a-100", "tst-005-100", "tst-005a-100")

    def blocos(self, con):
        p = self.metrics.set_payload(con, "TST")
        return {pr["id"]: pr["block"] for g in p["groups"] for pr in g["printings"]}


class TestOCriterio(Base):
    """O tamanho da edição vem do código impresso, não de um número à mão."""

    def test_o_tamanho_do_set_le_se_no_denominador_do_codigo(self):
        self.assertEqual(
            self.metrics.tamanho_do_set({"public_code": "OGN-299/298"}), 298)

    def test_acima_do_tamanho_e_sobrenumerada(self):
        self.assertTrue(self.metrics.e_overnumbered(
            {"public_code": "OGN-299/298", "collector_number": 299}))
        self.assertFalse(self.metrics.e_overnumbered(
            {"public_code": "OGN-298/298", "collector_number": 298}))

    def test_um_codigo_sem_denominador_nunca_e_sobrenumerado(self):
        """Os tokens `-T` e as runas promo `VEN-R01` não trazem tamanho nenhum.

        São numeradas numa série própria, fora da numeração da edição, e por
        isso não a podem passar. São 16 no catálogo real.
        """
        self.assertIsNone(self.metrics.tamanho_do_set({"public_code": "VEN-R01"}))
        self.assertFalse(self.metrics.e_overnumbered(
            {"public_code": "VEN-R01", "collector_number": 1}))

    def test_uma_serie_propria_com_tamanho_proprio_tambem_nao(self):
        """`VEN-SP4/006` é a 4 de uma série de 6 — o código diz que série é."""
        self.assertFalse(self.metrics.e_overnumbered(
            {"public_code": "VEN-SP4/006", "collector_number": 4}))

    def test_sem_codigo_nenhum_a_resposta_e_nao(self):
        """O `e_master` é chamado com dicionários mínimos em meio riftvault."""
        self.assertFalse(self.metrics.e_overnumbered({"variant_kind": "base"}))


class TestARegra(Base):
    """Uma pergunta, uma função: `metrics.fora_da_colecao`."""

    def test_a_sobrenumerada_nao_faz_parte_da_colecao(self):
        self.assertFalse(self.metrics.e_master(
            {"variant_kind": "base", "is_token": 0,
             "public_code": "TST-101/100", "collector_number": 101}))

    def test_a_lista_do_config_e_a_mesma_dos_sufixos(self):
        self.assertTrue(self.metrics.fora_overnumbered())
        self.assertEqual(self.metrics.FORA_OVERNUMBERED, "overnumbered")
        # E continua a levar as signatures: são duas entradas da mesma lista.
        self.assertIn("signature", self.metrics.kinds_fora())

    def test_um_valor_desconhecido_continua_a_rebentar(self):
        """Ponto 6 das "Superfícies não validadas": um sufixo novo tem de dar erro."""
        self.com_config({"master_set": {"fora": ["overnumbered", "b"]}})
        with self.assertRaises(ValueError):
            self.metrics.kinds_fora()

    def test_o_alvo_da_sobrenumerada_e_1(self):
        """Uma Unit base pediria 3; fora da coleção pede 1, como as signatures."""
        con = self.edicao()
        tiles = {pr["id"]: pr for g in self.metrics.set_payload(con, "TST")["groups"]
                 for pr in g["printings"]}
        self.assertEqual(tiles["tst-101-100"]["target"], 1)
        # E a que ficou dentro continua com o playset do tipo.
        self.assertEqual(tiles["tst-001-100"]["target"], 3)
        con.close()


class TestColecao(Base):
    """Nem na sequência, nem nas runas especiais, nem nas artes alternativas."""

    def test_vai_para_um_bloco_proprio_no_fim(self):
        con = self.edicao()
        self.assertEqual(self.blocos(con)["tst-101-100"], "overnumbered")
        con.close()

    def test_a_alt_art_de_uma_runa_sobrenumerada_tambem_sai(self):
        """A saída ganha ao bloco 2 — a runa especial só vale dentro da coleção."""
        con = self.edicao()
        b = self.blocos(con)
        self.assertEqual(b["tst-005a-100"], "rune_special")
        self.assertEqual(b["tst-105a-100"], "overnumbered")
        con.close()

    def test_a_signature_fica_no_bloco_das_signatures(self):
        """Todas as signatures são sobrenumeradas, e mesmo assim não mudam de bloco.

        A ordem dos critérios em `fora_da_colecao` é variante primeiro, número
        depois: o que tirou as signatures foi a frase de 2026-09-09, e mudá-las
        de cabeçalho agora era apagar essa decisão do ecrã.
        """
        con = self.edicao()
        self.assertEqual(self.blocos(con)["tst-101-star-100"], "signature")
        con.close()

    def test_o_bloco_nao_conta_para_a_percentagem(self):
        con = self.edicao()
        p = self.metrics.set_payload(con, "TST")
        blocos = {b["id"]: b for b in p["blocks"]}
        self.assertFalse(blocos["overnumbered"]["counts"])
        self.assertEqual(blocos["overnumbered"]["total"], 2)
        # A barra são as quatro de dentro: base, alt art, runa base, runa esp.
        self.assertEqual(p["progress"]["master"]["total"], len(self.DENTRO))
        self.assertEqual(sum(b["total"] for b in p["blocks"] if b["counts"]),
                         p["progress"]["master"]["total"])
        con.close()

    def test_a_que_ele_tem_continua_visivel_e_contada_no_bloco(self):
        """Sai da conta da coleção, não da grelha nem da caixa."""
        from riftvault import collection
        con = self.edicao()
        collection.adjust(con, "tst-101-100", 1, source="test")
        p = self.metrics.set_payload(con, "TST")
        tiles = {pr["id"]: pr for g in p["groups"] for pr in g["printings"]}
        self.assertEqual(tiles["tst-101-100"]["qty"], 1)
        blocos = {b["id"]: b for b in p["blocks"]}
        self.assertEqual((blocos["overnumbered"]["done"],
                          blocos["overnumbered"]["total"]), (1, 2))
        # E não entra no "se estivesse completa": 2000 € de reimpressão de topo
        # não são preço de fechar a coleção.
        self.assertEqual(p["progress"]["value"]["full"], 0)
        con.close()

    def test_a_ordem_da_grelha_poe_o_bloco_depois_da_colecao(self):
        con = self.edicao()
        ordem = self.metrics.ordem_da_grelha(self.metrics.set_payload(con, "TST"))
        blocos = [b for b, _ in ordem]
        # As duas sobrenumeradas são as últimas da grelha, e nada da coleção
        # aparece depois delas — nunca intercaladas, como os outros blocos.
        self.assertEqual(blocos[-2:], ["overnumbered", "overnumbered"])
        self.assertLess(max(i for i, b in enumerate(blocos)
                            if self.metrics.conta_bloco(b)),
                        min(i for i, b in enumerate(blocos) if b == "overnumbered"))
        con.close()


class TestContagemPorNiveis(Base):
    """Os degraus 1/2/3 medem o mesmo âmbito da barra — sem sobrenumeradas."""

    def test_o_ambito_dos_niveis_nao_leva_sobrenumeradas(self):
        con = self.edicao()
        self.assertEqual(len(self.metrics.itens_da_colecao(con)), len(self.DENTRO))
        n = self.metrics.niveis_payload(con)
        self.assertEqual(n["levels"][0]["total"], len(self.DENTRO))
        self.assertEqual(n["by_set"]["TST"][0]["total"], len(self.DENTRO))
        con.close()

    def test_o_ultimo_degrau_continua_a_ser_a_barra(self):
        """A promessa da contagem por níveis, com as sobrenumeradas fora."""
        from riftvault import collection
        con = self.edicao()
        collection.adjust(con, "tst-001-100", 3, source="test")
        prog = self.metrics.set_payload(con, "TST")["progress"]
        self.assertEqual(prog["levels"][-1]["done"], prog["master"]["done"])
        self.assertEqual(prog["levels"][-1]["total"], prog["master"]["total"])
        con.close()

    def test_os_2000_euros_da_sobrenumerada_saem_do_custo_de_fechar(self):
        con = self.edicao()
        for nivel in self.metrics.niveis_payload(con)["levels"]:
            with self.subTest(k=nivel["k"]):
                self.assertEqual(nivel["cents"], 0)
        con.close()


class TestPartilhaComOASubir(Base):
    """O «a subir» exclui pelo MESMO critério — não tem uma cópia da regra."""

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

    def test_nenhuma_sobrenumerada_entra_em_lista_de_compra_nenhuma(self):
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
                self.assertEqual(pids & set(self.ACIMA), set())
        con.close()

    def test_nao_sao_contadas_como_excluidas__nunca_estiveram_no_ambito(self):
        """A página diz quantas TIROU; estas saem antes, com a coleção."""
        con = self.edicao()
        self.assertEqual(self.a_subir.master_faltas(con)["scope"]["excluded"], 0)
        con.close()


class TestVenda(Base):
    """A consequência que ele não pediu — a mesma das signatures, 2026-09-09.

    O âmbito da Venda é "não é o bloco `master`", e as sobrenumeradas passaram a
    estar nesse caso: uma que ele tenha e nenhum deck use aparece como candidata
    a venda. **É pergunta para ele** — hoje são 5 impressões no `vault.db` real.
    Fica fixado para não mudar sem se dar por isso.
    """

    def test_uma_sobrenumerada_que_ele_tenha_aparece_como_candidata(self):
        from riftvault import collection
        con = self.edicao()
        collection.adjust(con, "tst-101-100", 1, source="test")
        itens = {x["printing_id"]: x for x in self.venda.listar(con)["items"]}
        self.assertIn("tst-101-100", itens)
        self.assertEqual(itens["tst-101-100"]["qty"], 1)
        self.assertEqual(itens["tst-101-100"]["block"], "overnumbered")
        con.close()


class TestVoltarAtras(Base):
    """Tirar o `overnumbered` do config põe tudo como estava — uma linha."""

    def test_sem_a_palavra_a_sobrenumerada_volta_a_todos_os_sitios(self):
        self.com_config({"master_set": {"fora": ["-T", "*"]}})
        con = self.edicao()
        self.assertFalse(self.metrics.fora_overnumbered())
        b = self.blocos(con)
        self.assertEqual(b["tst-101-100"], "master")
        self.assertEqual(b["tst-105a-100"], "rune_special")
        # A signature continua fora: é a outra decisão, e é outra entrada.
        self.assertEqual(b["tst-101-star-100"], "signature")
        self.assertEqual(
            self.metrics.set_payload(con, "TST")["progress"]["master"]["total"], 6)
        con.close()


if __name__ == "__main__":
    unittest.main()

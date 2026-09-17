"""As sobrenumeradas: coleção extra — a regra inteira, num sítio só.

André, 2026-09-10: *"no riftvault, também não quero para a coleção as
overnumbered"*. E 2026-09-14, à noite: *"Alt Art, overnumbered, etc etc mete
Playset na contagem / mas só quero % de completo para masterset! / o que é Alt
Art e Overnumbered, etc etc é puramente coleção"*.

A regra numa frase: **uma impressão cujo número de coleccionador passa o
tamanho da edição (as «300/298») é COLEÇÃO EXTRA** — aparece na grelha num
bloco próprio e pede o playset do tipo, mas NÃO entra na sequência do master set, no denominador da percentagem, nas
contagens por níveis **nem nas listas de compra** (2026-09-15: *"sobrenumeradas
não entram na wantlist, nem na % de coleção completa; apenas pedi para ser
feito track de playset para eu saber exatamente quantas tenho"*). Até
2026-09-14 nem tinha alvo a sério (1); a frase dessa noite trouxe-a para a
coleção sem a pôr a contar, e por um dia entrou nas listas — a de 15/09
tirou-a de lá.

**O critério é o CÓDIGO IMPRESSO**, como todas as decisões dele sobre a
Coleção: o `public_code` traz o número E o tamanho da edição (`OGN-299*/298`),
por isso o tamanho não é um número escrito à mão nem uma segunda consulta.

**Um ponto de verdade só:** `metrics.fora_do_master`, pela lista
`master_set.fora_da_percentagem`, que leva `"overnumbered"` a par dos sufixos.
O `e_master` (a percentagem), o `bloco` (a grelha) e o âmbito das listas de
compra (`e_colecao`) perguntam todos às mesmas funções.

Estes testes valem por todos os consumidores da regra: a Coleção (blocos e
percentagem), a contagem por níveis, as wantlists (por edição e por nível), o
«A subir» e a lista do «Master set». Se um dia um deles passar a
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

# O tamanho nominal da edição de brincar: tudo acima de 100 é sobrenumerado.
TAMANHO = 100


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

    def edicao(self):
        """Uma edição de 100 com as quatro coisas que a regra tem de separar.

        Dentro do tamanho: a Unit base, a alt art dela, a runa base e a alt art
        da runa. Acima dele: a reimpressão showcase de topo de set, a signature
        que se lhe agarra e a alt art de uma runa — para se ver que a
        sobrenumerada é coleção extra a playset, que a signature continua
        escondida, e que a alt art de runa sobrenumerada cai no bloco das runas
        especiais (é coleção extra por qualquer dos dois motivos, e a runa
        especial ganha à arte alternativa).
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

    # O master set (conta), a coleção extra (aparece, não conta), a escondida
    # e as retiradas (as alt arts das runas, 2026-09-17: nem aparecem).
    MASTER = ("tst-001-100", "tst-005-100")
    EXTRA = ("tst-001a-100", "tst-101-100")
    ESCONDIDAS = ("tst-101-star-100",)
    RETIRADAS = ("tst-005a-100", "tst-105a-100")
    # A que está acima do tamanho E na página.
    ACIMA = ("tst-101-100",)

    def blocos(self, con):
        p = self.metrics.set_payload(con, "TST")
        return {pr["id"]: pr["block"] for g in p["groups"] for pr in g["printings"]}

    def linhas(self, con):
        return {r["printing_id"]: r for r in con.execute("SELECT * FROM catalog.printings")}


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
    """Uma pergunta, uma função: `metrics.fora_do_master`."""

    def test_a_sobrenumerada_nao_conta_mas_e_colecao(self):
        linha = {"variant_kind": "base", "is_token": 0,
                 "public_code": "TST-101/100", "collector_number": 101}
        self.assertFalse(self.metrics.e_master(linha))
        self.assertTrue(self.metrics.e_colecao(linha))
        self.assertFalse(self.metrics.escondida(linha))

    def test_a_lista_do_config_e_a_mesma_dos_sufixos(self):
        self.assertTrue(self.metrics.fora_overnumbered())
        self.assertEqual(self.metrics.FORA_OVERNUMBERED, "overnumbered")
        # E a mesma gramática serve as duas listas: as signatures, que estão
        # escondidas, também não contam — o `kinds_fora` junta as duas.
        self.assertIn("signature", self.metrics.kinds_fora())
        self.assertIn("signature", self.metrics.kinds_escondidas())

    def test_um_valor_desconhecido_continua_a_rebentar(self):
        """Ponto 6 das "Superfícies não validadas": um sufixo novo tem de dar erro."""
        self.com_config({"master_set": {"fora_da_percentagem": ["overnumbered", "b"]}})
        with self.assertRaises(ValueError):
            self.metrics.kinds_fora()

    def test_o_alvo_da_sobrenumerada_e_1_e_o_da_base_e_o_playset(self):
        """*"overnumbered e promos (SP) voltamos a 1 de cada"* (2026-09-15): a
        sobrenumerada pede 1; a Unit da sequência continua a pedir 3. Foi o
        playset do tipo de 2026-09-14 (*"mete Playset na contagem"*) até esse
        dia — ver `test_alvo_1.py`."""
        con = self.edicao()
        tiles = {pr["id"]: pr for g in self.metrics.set_payload(con, "TST")["groups"]
                 for pr in g["printings"]}
        self.assertEqual(tiles["tst-101-100"]["target"], 1)
        self.assertEqual(tiles["tst-001-100"]["target"], 3)
        # A runa sobrenumerada em alt art está retirada (2026-09-17): não
        # tem alvo porque não está na página.
        self.assertNotIn("tst-105a-100", tiles)
        con.close()


class TestColecao(Base):
    """Na grelha, num bloco próprio; fora da sequência e da percentagem."""

    def test_vai_para_um_bloco_proprio(self):
        con = self.edicao()
        self.assertEqual(self.blocos(con)["tst-101-100"], "overnumbered")
        self.assertEqual(self.metrics.rotulo("overnumbered"),
                         "Coleção — sobrenumeradas — 1 de cada")   # 2026-09-15
        con.close()

    def test_a_alt_art_de_uma_runa_sobrenumerada_esta_retirada(self):
        """Ficou no bloco das runas especiais (coleção extra pelos dois
        motivos) até 2026-09-17 à tarde; desde então a alt art de uma runa
        está retirada de tudo, sobrenumerada ou não (`test_runas_alt_fora`).
        """
        con = self.edicao()
        b = self.blocos(con)
        self.assertNotIn("tst-005a-100", b)
        self.assertNotIn("tst-105a-100", b)
        for pid in ("tst-005a-100", "tst-105a-100"):
            self.assertTrue(self.metrics.retirada(self.linhas(con)[pid]))
            self.assertFalse(self.metrics.e_master(self.linhas(con)[pid]))
        con.close()

    def test_a_signature_continua_escondida_e_nao_muda_de_motivo(self):
        """Todas as signatures são sobrenumeradas, e mesmo assim são «signature».

        A ordem dos critérios em `fora_do_master` é variante primeiro, número
        depois: o que as tirou foi a frase de 2026-09-09, e o `bloco` continua
        a dizer o motivo certo mesmo não a pondo na grelha.
        """
        con = self.edicao()
        self.assertNotIn("tst-101-star-100", self.blocos(con))
        self.assertEqual(self.metrics.bloco(self.linhas(con)["tst-101-star-100"]),
                         "signature")
        con.close()

    def test_o_bloco_nao_conta_para_a_percentagem(self):
        con = self.edicao()
        p = self.metrics.set_payload(con, "TST")
        blocos = {b["id"]: b for b in p["blocks"]}
        self.assertFalse(blocos["overnumbered"]["counts"])
        self.assertEqual(blocos["overnumbered"]["total"], 1)
        # A barra são as duas da sequência: base e runa base.
        self.assertEqual(p["progress"]["master"]["total"], len(self.MASTER))
        self.assertEqual(sum(b["total"] for b in p["blocks"] if b["counts"]),
                         p["progress"]["master"]["total"])
        con.close()

    def test_a_que_ele_tem_continua_visivel_e_contada_no_bloco(self):
        """Sai da conta da percentagem, não da grelha nem da caixa."""
        from riftvault import collection
        con = self.edicao()
        collection.adjust(con, "tst-101-100", 3, source="test")
        p = self.metrics.set_payload(con, "TST")
        tiles = {pr["id"]: pr for g in p["groups"] for pr in g["printings"]}
        self.assertEqual(tiles["tst-101-100"]["qty"], 3)
        blocos = {b["id"]: b for b in p["blocks"]}
        self.assertEqual((blocos["overnumbered"]["done"],
                          blocos["overnumbered"]["total"]), (1, 1))
        # Vale o que ele tem, e não entra no "se estivesse completa": 2000 € de
        # reimpressão de topo não são preço de fechar o master set.
        self.assertEqual(p["progress"]["value"]["owned"], 3 * 200000)
        self.assertEqual(p["progress"]["value"]["full"], 0)
        con.close()

    def test_a_ordem_da_grelha_poe_o_bloco_depois_do_master_set(self):
        con = self.edicao()
        ordem = self.metrics.ordem_da_grelha(self.metrics.set_payload(con, "TST"))
        blocos = [b for b, _ in ordem]
        # A sobrenumerada é a última da grelha, e nada que conte aparece
        # depois dela — nunca intercaladas, como os outros blocos.
        self.assertEqual(blocos[-1], "overnumbered")
        self.assertLess(max(i for i, b in enumerate(blocos)
                            if self.metrics.conta_bloco(b)),
                        blocos.index("overnumbered"))
        con.close()


class TestContagemPorNiveis(Base):
    """Os degraus 1/2/3 medem o mesmo âmbito da barra — só o master set."""

    def test_o_ambito_dos_niveis_nao_leva_sobrenumeradas(self):
        con = self.edicao()
        self.assertEqual(len(self.metrics.itens_da_colecao(con)), len(self.MASTER))
        n = self.metrics.niveis_payload(con)
        self.assertEqual(n["levels"][0]["total"], len(self.MASTER))
        self.assertEqual(n["by_set"]["TST"][0]["total"], len(self.MASTER))
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


class TestListasDeCompra(Base):
    """As listas de compra NÃO levam a coleção extra (2026-09-15) — e dizem-no.

    O grosso está em `test_extra_so_track.py`; aqui fica o que é próprio das
    sobrenumeradas: o motivo com que saem e os 2000 € que deixam de pesar.
    """

    def test_o_ambito_da_pagina_e_exactamente_o_que_o_e_colecao_deixa_passar(self):
        """A partilha, fixada: uma função responde a todas as páginas.

        O `masterset` é a página inteira — é o `excluir` que tira o bloco 2
        das listas, para poder dizer quantas tirou. Se um dia o `a_subir`
        passar a calcular o seu próprio âmbito, isto parte — que é o ponto.
        """
        con = self.edicao()
        escopo = set(self.a_subir.masterset(con))
        pela_metrica = {r["printing_id"] for r in
                        con.execute("SELECT * FROM catalog.printings")
                        if self.metrics.e_colecao(r)}
        self.assertEqual(escopo, pela_metrica)
        self.assertEqual(escopo, set(self.MASTER + self.EXTRA))
        self.assertEqual(escopo & set(self.RETIRADAS), set())
        con.close()

    def test_a_sobrenumerada_nao_entra_em_lista_de_compra_nenhuma(self):
        """Os cinco consumidores — «A subir», «Master set», wantlists nos três
        degraus — não a pedem; a signature também não; o master set sim."""
        con = self.edicao()
        escopo, _ = self.a_subir.excluir(self.a_subir.masterset(con),
                                         self.a_subir.opcoes()["excluir"])
        ambitos = {"a_subir": set(escopo)}
        m = self.a_subir.master_faltas(con)
        itens = {x["printing_id"]: x for s in m["sets"] for x in s["items"]}
        ambitos["master_faltas"] = set(itens)
        for nivel in (1, 2, None):
            p = self.a_subir.wantlist(con, "TST", nivel=nivel)
            ambitos[f"wantlist:{nivel}"] = {x["printing_id"] for x in p["items"]}
        for nome, pids in ambitos.items():
            with self.subTest(consumidor=nome):
                self.assertEqual(pids & set(self.EXTRA), set())
                self.assertEqual(pids & set(self.ESCONDIDAS), set())
                self.assertEqual(pids & set(self.MASTER), set(self.MASTER))
        # Os 2000 € da sobrenumerada não pesam na lista.
        self.assertEqual(m["cents"], 0)
        con.close()

    def test_sai_com_o_motivo_sobrenumerada_e_a_alt_art_com_o_dela(self):
        """A página diz quantas TIROU e de que bloco; a signature nunca chega,
        nem as alt arts das runas (retiradas, 2026-09-17)."""
        con = self.edicao()
        m = self.a_subir.master_faltas(con)
        self.assertEqual(m["scope"]["excluded"], len(self.EXTRA))
        self.assertTrue(m["scope"]["so_master_set"])
        motivos = {c["criterio"]: c["n"] for c in m["scope"]["excluded_by"]}
        self.assertEqual(motivos, {"overnumbered": 1, "alt_art": 1})
        self.assertEqual(m["scope"]["excluded_labels"]["overnumbered"], "sobrenumeradas")
        con.close()

    def test_desligado_o_botao_de_2026_09_14_tira_so_o_que_se_escrever(self):
        """`listas_de_compra.so_master_set: false` + `a_subir.excluir.blocos`.

        É o mundo de um dia (2026-09-14, à noite): a coleção extra nas listas,
        e um botão para tirar blocos à escolha. Continua a ser lido.
        """
        self.com_config({"listas_de_compra": {"so_master_set": False},
                         "a_subir": {"excluir": {"blocos": ["overnumbered"]}}})
        con = self.edicao()
        m = self.a_subir.master_faltas(con)
        pids = {x["printing_id"] for s in m["sets"] for x in s["items"]}
        self.assertNotIn("tst-101-100", pids)
        # A alt art da runa sobrenumerada não volta por aqui: está retirada
        # de tudo (2026-09-17), e isto é só o botão das listas.
        self.assertNotIn("tst-105a-100", pids)
        self.assertIn("tst-001a-100", pids)
        self.assertEqual(m["scope"]["excluded"], 1)
        self.assertFalse(m["scope"]["so_master_set"])
        self.assertEqual(m["scope"]["excluded_by"],
                         [{"criterio": "overnumbered", "n": 1}])
        con.close()


class TestVoltarAtras(Base):
    """Tirar o `overnumbered` do config põe-nas na sequência — uma linha."""

    def test_sem_a_palavra_a_sobrenumerada_volta_ao_master_set(self):
        self.com_config({"master_set": {"fora_da_percentagem": ["a", "-R", "promo"],
                                        "escondidas": ["-T", "*"]}})
        con = self.edicao()
        self.assertFalse(self.metrics.fora_overnumbered())
        b = self.blocos(con)
        self.assertEqual(b["tst-101-100"], "master")
        # A alt art da runa não volta: é a lista das retiradas, não esta.
        self.assertNotIn("tst-105a-100", b)
        # A signature continua escondida: é a outra lista.
        self.assertNotIn("tst-101-star-100", b)
        # A barra passa a contar as três da sequência: base, runa base e a
        # sobrenumerada, que volta a ser master set.
        self.assertEqual(
            self.metrics.set_payload(con, "TST")["progress"]["master"]["total"], 3)
        con.close()

    def test_o_nome_antigo_da_lista_continua_a_ser_lido(self):
        """`master_set.fora` (2026-09-08 a 2026-09-14) vale como `fora_da_percentagem`."""
        self.com_config({"master_set": {"fora": ["-T", "*"]}})
        con = self.edicao()
        self.assertFalse(self.metrics.fora_overnumbered())
        self.assertEqual(self.blocos(con)["tst-101-100"], "master")
        con.close()


if __name__ == "__main__":
    unittest.main()

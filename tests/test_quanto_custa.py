"""O separador «Quanto custa» (chamava-se «Faltas» até 2026-09-15).

André, 2026-09-15: *"na aba faltas, renomeia para algo que seja apelativo a ter
atenção ao preço"* / *"fazes novamente para cada set (menos proving grounds) um
botão"* / *"depois metes para cada raridade, as cartas por ordem de preço"*.

O que se fixa aqui: um botão por edição do CATÁLOGO e nenhum para o OGS;
escolher uma edição mostra só cartas dela e «tudo» é o que os botões mostram;
dentro de cada raridade os preços vêm do mais caro para o mais barato e o
inversor põe-nos ao contrário; uma carta sem preço vai para o fim e não conta
como zero; os subtotais somam ao total; a coleção extra continua fora; e a
lista é a MESMA do «Master set» — só a arrumação muda.

Tudo contra cópias descartáveis (`tests.fixture.Vault`) e um config temporário
(`RIFTVAULT_CONFIG`): nunca o `data/` nem o `riftvault_config.json` reais.
"""

from __future__ import annotations

import importlib
import json
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.fixture import Vault


class Base(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.close)
        from riftvault import a_subir, cardmarket, config
        importlib.reload(cardmarket)
        importlib.reload(a_subir)
        self.a_subir = a_subir
        self.config = config

    def com_config(self, extra: dict):
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

    def preco(self, con, pid, cents):
        con.execute("INSERT INTO catalog.price_latest (printing_id, price_cents, "
                    "from_foil) VALUES (?,?,0)", (pid, cents))

    def montar(self):
        """Três edições: duas com botão (AAA, BBB) e o OGS, sem ele.

        Em AAA há duas épicas, duas raras, uma incomum, uma comum e uma épica
        SEM preço; e uma arte alternativa com preço alto, que é coleção extra e
        não pode aparecer. Em BBB e no OGS uma carta cada. Nada está na
        coleção, por isso falta tudo ao playset.
        """
        self.com_config({
            "sets": {"AAA": {"name": "Alfa", "order": 1},
                     "OGS": {"name": "OGS (Proving Grounds)", "order": 2},
                     "BBB": {"name": "Beta", "order": 3}},
            "quanto_custa": {"sem_edicoes": ["OGS"]},
        })
        con = self.v.connect()
        self.addCleanup(con.close)
        add = self.v.add_printing
        add(con, "aaa-001", "AAA", 1, "Epica Cara", rarity="epic")
        add(con, "aaa-002", "AAA", 2, "Epica Barata", rarity="epic")
        add(con, "aaa-003", "AAA", 3, "Rara Cara", rarity="rare")
        add(con, "aaa-004", "AAA", 4, "Rara Barata", rarity="rare")
        add(con, "aaa-005", "AAA", 5, "Incomum", rarity="uncommon")
        add(con, "aaa-006", "AAA", 6, "Comum", rarity="common")
        add(con, "aaa-007", "AAA", 7, "Epica Sem Oferta", rarity="epic")
        add(con, "aaa-001a", "AAA", 1, "Epica Cara", variant="a", kind="alt_art",
            rarity="showcase", base_rarity="epic")
        add(con, "bbb-001", "BBB", 1, "Beta Rara", rarity="rare")
        add(con, "ogs-001", "OGS", 1, "Starter", rarity="common")
        self.v.rebuild(con)
        # Preços fora de ordem de propósito: a ordem por número de coleção
        # (a do «Master set») NÃO é a ordem por preço, senão o teste passava
        # com a ordenação apagada.
        self.preco(con, "aaa-001", 500)
        self.preco(con, "aaa-002", 5000)
        self.preco(con, "aaa-003", 100)
        self.preco(con, "aaa-004", 900)
        self.preco(con, "aaa-005", 40)
        self.preco(con, "aaa-006", 11)
        self.preco(con, "aaa-001a", 99999)
        self.preco(con, "bbb-001", 300)
        self.preco(con, "ogs-001", 20)
        con.commit()
        return con

    @staticmethod
    def codigos(grupo):
        return [x["code"].split("/")[0] for x in grupo["items"]]

    @staticmethod
    def grupo(q, raridade):
        return next(g for g in q["groups"] if g["rarity"] == raridade)


class TestBotoes(Base):
    """Um botão por edição do catálogo; nenhum para o OGS."""

    def test_um_botao_por_edicao_menos_ogs(self):
        con = self.montar()
        b = self.a_subir.edicoes_quanto_custa(con)
        self.assertEqual([s["set"] for s in b["sets"]], ["AAA", "BBB"])
        self.assertEqual([s["name"] for s in b["sets"]], ["Alfa", "Beta"])
        self.assertEqual(b["sem_edicoes"], ["OGS"])

    def test_edicao_nova_ganha_botao_sozinha(self):
        con = self.montar()
        # Uma edição que não está no config vai para o fim, e tem botão.
        self.v.add_printing(con, "ccc-001", "CCC", 1, "Nova", rarity="common")
        self.v.rebuild(con)
        con.commit()
        b = self.a_subir.edicoes_quanto_custa(con)
        self.assertEqual([s["set"] for s in b["sets"]], ["AAA", "BBB", "CCC"])

    def test_sigla_no_config_em_minusculas_vale_o_mesmo(self):
        con = self.montar()
        cfg = {**self.config.load(), "quanto_custa": {"sem_edicoes": ["ogs", "bbb"]}}
        b = self.a_subir.edicoes_quanto_custa(con, cfg)
        self.assertEqual([s["set"] for s in b["sets"]], ["AAA"])
        self.assertEqual(b["sem_edicoes"], ["OGS", "BBB"])

    def test_sem_config_o_ogs_fica_de_fora_na_mesma(self):
        # O default do `config.DEFAULTS` tem de dizer o mesmo que o ficheiro.
        self.assertEqual(self.config.DEFAULTS["quanto_custa"]["sem_edicoes"], ["OGS"])
        con = self.montar()
        cfg = {k: v for k, v in self.config.load().items() if k != "quanto_custa"}
        b = self.a_subir.edicoes_quanto_custa(con, cfg)
        self.assertEqual(b["sem_edicoes"], ["OGS"])

    def test_os_botoes_vao_no_payload_do_master_set(self):
        con = self.montar()
        m = self.a_subir.master_faltas(con)
        self.assertEqual([s["set"] for s in m["quanto_custa"]["sets"]], ["AAA", "BBB"])
        self.assertEqual(m["quanto_custa"]["sem_edicoes"], ["OGS"])
        self.assertEqual(m["quanto_custa"]["rarity_order"],
                         ["epic", "rare", "uncommon", "common"])


class TestEscolherEdicao(Base):
    """Escolher uma edição mostra só cartas dela; «tudo» é o que os botões mostram."""

    def test_uma_edicao_so_tem_cartas_dela(self):
        con = self.montar()
        q = self.a_subir.quanto_custa(con, set_id="AAA")
        self.assertEqual(q["set"], "AAA")
        self.assertTrue(q["cards"] > 0)
        for g in q["groups"]:
            self.assertEqual({x["set"] for x in g["items"]}, {"AAA"})

    def test_outra_edicao_so_tem_as_dela(self):
        con = self.montar()
        q = self.a_subir.quanto_custa(con, set_id="bbb")
        self.assertEqual(q["set"], "BBB")
        self.assertEqual([self.codigos(g) for g in q["groups"]], [["BBB-001"]])

    def test_tudo_e_as_edicoes_com_botao_sem_o_ogs(self):
        con = self.montar()
        q = self.a_subir.quanto_custa(con)
        sets = {x["set"] for g in q["groups"] for x in g["items"]}
        self.assertEqual(sets, {"AAA", "BBB"})
        self.assertNotIn("OGS", sets)
        # E o OGS não desapareceu da lista de compra: pedido pelo nome, está lá.
        ogs = self.a_subir.quanto_custa(con, set_id="OGS")
        self.assertEqual([self.codigos(g) for g in ogs["groups"]], [["OGS-001"]])


class TestOrdemPorPreco(Base):
    """Por raridade, e dentro da raridade por preço; o inversor troca a ordem."""

    def test_raridades_da_mais_rara_para_a_mais_comum(self):
        con = self.montar()
        q = self.a_subir.quanto_custa(con, set_id="AAA")
        self.assertEqual([g["rarity"] for g in q["groups"]],
                         ["epic", "rare", "uncommon", "common", self.a_subir.SEM_OFERTA])

    def test_dentro_da_raridade_do_mais_caro_para_o_mais_barato(self):
        con = self.montar()
        q = self.a_subir.quanto_custa(con, set_id="AAA")
        self.assertEqual(q["order"], "desc")
        # A 002 custa 50 € e a 001 custa 5 €: por número seria 001, 002.
        self.assertEqual(self.codigos(self.grupo(q, "epic")), ["AAA-002", "AAA-001"])
        self.assertEqual(self.codigos(self.grupo(q, "rare")), ["AAA-004", "AAA-003"])
        for g in q["groups"]:
            precos = [x["price"] for x in g["items"] if x["price"] is not None]
            self.assertEqual(precos, sorted(precos, reverse=True), g["rarity"])

    def test_o_inversor_poe_do_mais_barato_para_o_mais_caro(self):
        con = self.montar()
        q = self.a_subir.quanto_custa(con, set_id="AAA", ordem="asc")
        self.assertEqual(q["order"], "asc")
        self.assertEqual(self.codigos(self.grupo(q, "epic")), ["AAA-001", "AAA-002"])
        self.assertEqual(self.codigos(self.grupo(q, "rare")), ["AAA-003", "AAA-004"])
        # A ordem das raridades não se inverte: os cabeçalhos ficam no sítio.
        self.assertEqual([g["rarity"] for g in q["groups"]],
                         ["epic", "rare", "uncommon", "common", self.a_subir.SEM_OFERTA])

    def test_ordem_desconhecida_rebenta(self):
        con = self.montar()
        with self.assertRaises(ValueError):
            self.a_subir.quanto_custa(con, set_id="AAA", ordem="random")

    def test_ordena_pelo_preco_unitario_nao_pelo_total(self):
        # Uma Legend (alvo 1) a 6 € e uma Unit (alvo 3) a 4 €: o total da Unit
        # (12 €) é maior, mas o número que ele lê é o da carta — a Legend vem
        # primeiro.
        self.com_config({"sets": {"AAA": {"name": "Alfa", "order": 1}}})
        con = self.v.connect()
        self.addCleanup(con.close)
        self.v.add_printing(con, "aaa-001", "AAA", 1, "Unit", rarity="epic")
        self.v.add_printing(con, "aaa-002", "AAA", 2, "Legend", rarity="epic",
                            card_type="Legend")
        self.v.rebuild(con)
        self.preco(con, "aaa-001", 400)
        self.preco(con, "aaa-002", 600)
        con.commit()
        q = self.a_subir.quanto_custa(con, set_id="AAA")
        g = self.grupo(q, "epic")
        self.assertEqual(self.codigos(g), ["AAA-002", "AAA-001"])
        self.assertEqual([x["total"] for x in g["items"]], [600, 1200])

    def test_raridade_desconhecida_vai_para_o_fim_mas_antes_das_sem_oferta(self):
        itens = [
            {"code": "X-1", "set": "X", "cn": 1, "rarity": "?", "price": 10, "total": 10, "missing": 1},
            {"code": "X-2", "set": "X", "cn": 2, "rarity": "common", "price": 10, "total": 10, "missing": 1},
            {"code": "X-3", "set": "X", "cn": 3, "rarity": "epic", "price": None, "total": 0, "missing": 1},
        ]
        r = self.a_subir.por_raridade(itens)
        self.assertEqual([g["rarity"] for g in r["groups"]],
                         ["common", "?", self.a_subir.SEM_OFERTA])


class TestSemPreco(Base):
    """Uma carta sem oferta aparece no fim e não conta como zero."""

    def test_vai_para_o_grupo_do_fim(self):
        con = self.montar()
        q = self.a_subir.quanto_custa(con, set_id="AAA")
        ultimo = q["groups"][-1]
        self.assertEqual(ultimo["rarity"], self.a_subir.SEM_OFERTA)
        self.assertEqual(self.codigos(ultimo), ["AAA-007"])
        self.assertIsNone(ultimo["cents"])
        self.assertEqual(q["no_price"], 1)
        # Não está no grupo das épicas, que é a raridade dela.
        self.assertNotIn("AAA-007", self.codigos(self.grupo(q, "epic")))

    def test_o_total_nao_a_conta_como_zero_nem_a_esconde(self):
        con = self.montar()
        q = self.a_subir.quanto_custa(con, set_id="AAA")
        # As cartas contam (7), as cópias contam, o dinheiro é só das com preço.
        self.assertEqual(q["cards"], 7)
        self.assertEqual(q["copies"], sum(g["copies"] for g in q["groups"]))
        com_preco = sum(g["cents"] for g in q["groups"] if g["cents"] is not None)
        self.assertEqual(q["cents"], com_preco)


class TestSubtotais(Base):
    """Os subtotais por raridade somam ao total, e o total é o do «Master set»."""

    def test_subtotais_somam_ao_total(self):
        con = self.montar()
        for set_id in ("AAA", "BBB", None):
            q = self.a_subir.quanto_custa(con, set_id=set_id)
            self.assertEqual(q["cents"], sum(g["cents"] or 0 for g in q["groups"]), set_id)
            for g in q["groups"]:
                self.assertEqual(g["cards"], len(g["items"]))
                self.assertEqual(g["copies"], sum(x["missing"] for x in g["items"]))
                if g["cents"] is not None:
                    self.assertEqual(g["cents"], sum(x["total"] for x in g["items"]))

    def test_subtotais_com_os_numeros_da_fixture(self):
        con = self.montar()
        q = self.a_subir.quanto_custa(con, set_id="AAA")
        # Units, alvo 3, nada na coleção: 3 cópias de cada.
        self.assertEqual(self.grupo(q, "epic")["cents"], 3 * (5000 + 500))
        self.assertEqual(self.grupo(q, "rare")["cents"], 3 * (900 + 100))
        self.assertEqual(self.grupo(q, "uncommon")["cents"], 3 * 40)
        self.assertEqual(self.grupo(q, "common")["cents"], 3 * 11)
        self.assertEqual(q["cents"], 3 * (5000 + 500 + 900 + 100 + 40 + 11))

    def test_e_a_mesma_lista_do_master_set(self):
        con = self.montar()
        m = self.a_subir.master_faltas(con)
        for d in m["sets"]:
            q = self.a_subir.quanto_custa(con, set_id=d["set"])
            self.assertEqual(q["cards"], d["cards"], d["set"])
            self.assertEqual(q["copies"], d["copies"], d["set"])
            self.assertEqual(q["cents"], d["cents"], d["set"])
            self.assertEqual(sorted(x["printing_id"] for g in q["groups"] for x in g["items"]),
                             sorted(x["printing_id"] for x in d["items"]))
        # E o «tudo» mais o OGS pedido pelo nome dão o master set inteiro.
        tudo = self.a_subir.quanto_custa(con)
        ogs = self.a_subir.quanto_custa(con, set_id="OGS")
        self.assertEqual(tudo["cents"] + ogs["cents"], m["cents"])
        self.assertEqual(tudo["copies"] + ogs["copies"], m["copies"])


class TestColecaoExtra(Base):
    """A coleção extra continua fora: é só apresentação."""

    def test_a_arte_alternativa_nao_aparece(self):
        con = self.montar()
        for set_id in ("AAA", None):
            q = self.a_subir.quanto_custa(con, set_id=set_id)
            pids = [x["printing_id"] for g in q["groups"] for x in g["items"]]
            self.assertNotIn("aaa-001a", pids)
            # Custava 999,99 €: se entrasse, o total dava por ela.
            self.assertLess(q["cents"], 99999)

    def test_nao_escreve_na_base(self):
        con = self.montar()
        antes = con.execute("SELECT COUNT(*) FROM copies").fetchone()[0]
        self.a_subir.quanto_custa(con)
        self.a_subir.quanto_custa(con, set_id="AAA", ordem="asc")
        self.assertEqual(con.execute("SELECT COUNT(*) FROM copies").fetchone()[0], antes)
        self.assertEqual(con.execute("SELECT COUNT(*) FROM ops").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()

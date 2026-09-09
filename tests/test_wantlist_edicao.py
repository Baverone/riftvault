"""A wantlist do Cardmarket no fim de cada edição.

André, 2026-09-08: *"Quero também que no fim de cada edição me dês uma wantlist
para eu colocar no Cardmarket."*

O que se fixa aqui: que há uma wantlist POR EDIÇÃO com as faltas dessa edição e
só dessa; que os alvos são os dos três blocos da Coleção (playset na sequência,
1 nas runas, 1 nas runas especiais, 1 nas artes alternativas); que as linhas
saem do gerador único e não de uma segunda implementação; e que os totais batem
certo — por edição e no conjunto — sem nunca entrarem no texto.
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
        from riftvault import a_subir, cardmarket, config, metrics
        importlib.reload(cardmarket)
        importlib.reload(a_subir)
        self.a_subir = a_subir
        self.cardmarket = cardmarket
        self.metrics = metrics
        self.config = config

    def preco(self, con, pid, cents, foil=0):
        con.execute("INSERT INTO catalog.price_latest (printing_id, price_cents, "
                    "from_foil) VALUES (?,?,?)", (pid, cents, foil))

    def mercado(self, con, pid, nome, edicao, blueprint=1):
        con.execute("INSERT INTO catalog.cardtrader_map (printing_id, blueprint_id, "
                    "market_name, market_set) VALUES (?,?,?,?)",
                    (pid, blueprint, nome, edicao))

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


class TestUmaListaPorEdicao(Base):
    """Duas edições, e cada uma leva só o que é seu."""

    def montar(self):
        self.com_config({"sets": {"AAA": {"name": "Alfa", "order": 1},
                                  "ZZZ": {"name": "Zeta", "order": 2}}})
        con = self.v.connect()
        self.v.add_printing(con, "aaa-001-100", "AAA", 1, "Alfa um")
        self.v.add_printing(con, "aaa-002-100", "AAA", 2, "Alfa dois")
        self.v.add_printing(con, "zzz-001-100", "ZZZ", 1, "Zeta um")
        self.v.rebuild(con)
        for pid, cents in (("aaa-001-100", 100), ("aaa-002-100", 200),
                           ("zzz-001-100", 500)):
            self.preco(con, pid, cents)
        return con

    def test_cada_edicao_leva_so_as_faltas_dela(self):
        con = self.montar()
        p = self.a_subir.wantlist(con, "AAA")
        self.assertEqual([d["set"] for d in p["sets"]], ["AAA"])
        self.assertEqual([x["name"] for x in p["items"]], ["Alfa um", "Alfa dois"])
        self.assertNotIn("Zeta um", p["text"])
        con.close()

    def test_sem_edicao_saem_todas_pela_ordem_do_config(self):
        con = self.montar()
        p = self.a_subir.wantlist(con)
        self.assertEqual([d["set"] for d in p["sets"]], ["AAA", "ZZZ"])
        # E a lista de todas é a concatenação das duas, por essa ordem.
        aaa = self.a_subir.wantlist(con, "AAA")["text"]
        zzz = self.a_subir.wantlist(con, "ZZZ")["text"]
        self.assertEqual(p["text"], aaa + "\n" + zzz)
        con.close()

    def test_minusculas_valem_na_edicao(self):
        con = self.montar()
        self.assertEqual(self.a_subir.wantlist(con, "aaa")["set"], "AAA")
        con.close()

    def test_edicao_que_nao_existe_da_lista_vazia(self):
        """Sem inventar: nem uma edição fantasma, nem uma lista errada."""
        con = self.montar()
        p = self.a_subir.wantlist(con, "XXX")
        self.assertEqual((p["sets"], p["items"], p["text"], p["lines"]),
                         ([], [], "", 0))
        con.close()

    def test_a_ordem_dentro_da_edicao_e_o_numero_de_colecao(self):
        """Ordem do binder, não do preço."""
        con = self.montar()
        con.execute("UPDATE catalog.price_latest SET price_cents = 9000 "
                    "WHERE printing_id = 'aaa-002-100'")
        p = self.a_subir.wantlist(con, "AAA")
        self.assertEqual([x["cn"] for x in p["items"]], [1, 2])
        con.close()

    def test_o_que_ja_esta_completo_nao_aparece(self):
        from riftvault import collection
        con = self.montar()
        collection.adjust(con, "aaa-001-100", 3, source="test")
        p = self.a_subir.wantlist(con, "AAA")
        self.assertEqual([x["name"] for x in p["items"]], ["Alfa dois"])
        con.close()

    def test_uma_edicao_sem_faltas_desaparece_da_lista_de_todas(self):
        from riftvault import collection
        con = self.montar()
        collection.adjust(con, "zzz-001-100", 3, source="test")
        p = self.a_subir.wantlist(con)
        self.assertEqual([d["set"] for d in p["sets"]], ["AAA"])
        con.close()


class TestAlvosDosTresBlocos(Base):
    """Os alvos são os da Coleção — a wantlist não tem alvos próprios.

    Playset na sequência (Unit 3, Legend 1), **1** na runa base, **1** na runa
    especial e **1** na arte alternativa. Ver `metrics.master_target`.
    """

    def montar(self):
        con = self.v.connect()
        self.v.add_printing(con, "tst-001-100", "TST", 1, "Uma Unit")
        self.v.add_printing(con, "tst-002-100", "TST", 2, "Um Legend",
                            card_type="Legend")
        self.v.add_printing(con, "tst-003-100", "TST", 3, "Fury Rune",
                            card_type="Rune")
        self.v.add_printing(con, "tst-003a-100", "TST", 3, "Fury Rune",
                            variant="a", kind="alt_art", card_type="Rune",
                            rarity="epic")
        self.v.add_printing(con, "tst-004-100", "TST", 4, "Uma Unit alt",
                            variant="a", kind="alt_art", rarity="epic")
        self.v.rebuild(con)
        return con

    def test_os_alvos(self):
        con = self.montar()
        p = self.a_subir.wantlist(con, "TST")
        alvos = {x["printing_id"]: (x["target"], x["missing"]) for x in p["items"]}
        self.assertEqual(alvos, {
            "tst-001-100": (3, 3),          # Unit na sequência: playset
            "tst-002-100": (1, 1),          # Legend na sequência: 1
            "tst-003-100": (1, 1),          # runa base: 1, não 12
            "tst-003a-100": (1, 1),         # runa especial: 1
            "tst-004-100": (1, 1),          # arte alternativa: 1
        })
        con.close()

    def test_a_runa_pede_1_e_nao_o_playset_de_12(self):
        """Colecionar e jogar são perguntas diferentes: o Rune Pool continua 12."""
        con = self.montar()
        p = self.a_subir.wantlist(con, "TST")
        runa = next(x for x in p["items"] if x["printing_id"] == "tst-003-100")
        self.assertEqual(runa["target"], 1)
        self.assertEqual(self.metrics.playset_target("Rune", False), 12)
        con.close()

    def test_os_tokens_ficam_fora(self):
        """Estão fora da coleção (`master_set.fora`), logo fora da wantlist."""
        con = self.montar()
        self.v.add_printing(con, "tst-t01-100", "TST", 90, "Recruit",
                            variant="t01", kind="token")
        self.v.rebuild(con)
        p = self.a_subir.wantlist(con, "TST")
        self.assertNotIn("tst-t01-100", [x["printing_id"] for x in p["items"]])
        con.close()

    def test_conta_o_que_vem_a_caminho_como_tido(self):
        from riftvault import collection, pending
        con = self.montar()
        collection.adjust(con, "tst-001-100", 1, source="test")
        pending.add(con, "tst-001-100", 1)
        p = self.a_subir.wantlist(con, "TST")
        it = next(x for x in p["items"] if x["printing_id"] == "tst-001-100")
        self.assertEqual((it["have"], it["target"], it["missing"]), (2, 3, 1))
        con.close()


class TestFormatoDasLinhas(Base):
    """`N Nome (V.n) (Edição)` — e sai do MESMO gerador, não de outro."""

    def montar(self):
        con = self.v.connect()
        self.v.add_printing(con, "tst-002-100", "TST", 2, "Loose Cannon")
        self.v.add_printing(con, "tst-002a-100", "TST", 2, "Loose Cannon",
                            variant="a", kind="alt_art", rarity="epic")
        self.v.rebuild(con)
        self.mercado(con, "tst-002-100", "Jinx - Loose Cannon", "Unleashed", 11)
        self.mercado(con, "tst-002a-100", "Jinx - Loose Cannon", "Unleashed", 12)
        self.preco(con, "tst-002-100", 250)
        self.preco(con, "tst-002a-100", 1000)
        return con

    def test_o_texto_e_o_do_gerador_unico(self):
        con = self.montar()
        p = self.a_subir.wantlist(con, "TST")
        self.assertEqual(p["text"].splitlines(), [
            "3 Jinx - Loose Cannon (V.1) (Unleashed)",
            "1 Jinx - Loose Cannon (V.2) (Unleashed)",
        ])
        # Linha a linha, é exactamente o `cardmarket.linha` — se um dia
        # divergirem, é porque alguém escreveu um segundo formato.
        self.assertEqual(p["text"],
                         "\n".join(self.cardmarket.linha(x) for x in p["items"]))
        con.close()

    def test_com_codigo(self):
        con = self.montar()
        p = self.a_subir.wantlist(con, "TST", com_codigo=True)
        self.assertEqual(p["text"].splitlines(),
                         ["3 Jinx - Loose Cannon [TST-002]",
                          "1 Jinx - Loose Cannon [TST-002a]"])
        con.close()

    def test_sem_par_no_mercado_usa_o_nome_do_catalogo(self):
        con = self.v.connect()
        self.v.add_printing(con, "tst-009-100", "TST", 9, "Sem Par")
        self.v.rebuild(con)
        p = self.a_subir.wantlist(con, "TST")
        self.assertEqual(p["text"], "3 Sem Par")
        con.close()

    def test_as_so_de_foil_saem_assinaladas_fora_do_texto(self):
        con = self.montar()
        con.execute("UPDATE catalog.price_latest SET from_foil = 1 "
                    "WHERE printing_id = 'tst-002-100'")
        p = self.a_subir.wantlist(con, "TST")
        self.assertEqual(p["foil"], ["3 Jinx - Loose Cannon (V.1) (Unleashed)"])
        # O foil é um filtro POR ENTRADA na interface deles — não se escreve
        # na linha, e não se inventa sintaxe nenhuma.
        self.assertNotIn("foil", p["text"].lower())
        con.close()


class TestTotais(Base):
    def montar(self):
        self.com_config({"sets": {"AAA": {"name": "Alfa", "order": 1},
                                  "ZZZ": {"name": "Zeta", "order": 2}}})
        con = self.v.connect()
        self.v.add_printing(con, "aaa-001-100", "AAA", 1, "Alfa um")
        self.v.add_printing(con, "zzz-001-100", "ZZZ", 1, "Zeta um",
                            card_type="Legend")
        self.v.rebuild(con)
        self.preco(con, "aaa-001-100", 100)      # 3 em falta × 1,00 €
        self.preco(con, "zzz-001-100", 500)      # 1 em falta × 5,00 €
        return con

    def test_o_total_e_a_soma_das_edicoes(self):
        con = self.montar()
        p = self.a_subir.wantlist(con)
        self.assertEqual(p["cents"], 300 + 500)
        self.assertEqual(p["copies"], 4)
        self.assertEqual(p["lines"], 2)
        self.assertEqual(sum(d["wantlist"]["cents"] for d in p["sets"]), p["cents"])
        self.assertEqual(sum(d["wantlist"]["copies"] for d in p["sets"]), p["copies"])
        con.close()

    def test_cada_edicao_leva_o_seu_total(self):
        con = self.montar()
        p = self.a_subir.wantlist(con)
        por_set = {d["set"]: d["wantlist"] for d in p["sets"]}
        self.assertEqual(por_set["AAA"]["cents"], 300)
        self.assertEqual(por_set["ZZZ"]["cents"], 500)
        # O `cents` do grupo já existia para a aba «Master set»: é o mesmo
        # número, não uma segunda conta.
        self.assertEqual([d["cents"] for d in p["sets"]],
                         [d["wantlist"]["cents"] for d in p["sets"]])
        con.close()

    def test_o_total_nunca_vai_no_texto(self):
        """Uma linha de total colada na wantlist era importada como carta."""
        con = self.montar()
        p = self.a_subir.wantlist(con)
        self.assertEqual(p["lines"], len(p["text"].splitlines()))
        self.assertNotIn("€", p["text"])
        for d in p["sets"]:
            self.assertNotIn("€", d["wantlist"]["text"])
        con.close()

    def test_sem_preco_entra_na_lista_mas_nao_no_total(self):
        con = self.montar()
        self.v.add_printing(con, "aaa-002-100", "AAA", 2, "Sem preço")
        self.v.rebuild(con)
        p = self.a_subir.wantlist(con, "AAA")
        self.assertEqual(p["no_price"], 1)
        self.assertEqual(p["cents"], 300)
        self.assertIn("Sem preço", p["text"])
        con.close()


class TestExclusoes(Base):
    """As mesmas das outras duas listas de compra — e a métrica não mexe."""

    def montar(self):
        con = self.v.connect()
        self.v.add_printing(con, "tst-002-100", "TST", 2, "Sett, Brawler")
        self.v.add_printing(con, "tst-232-100", "TST", 232, "Sett, Brawler",
                            rarity="showcase")
        self.v.add_printing(con, "tst-232-star-100", "TST", 232, "Sett, Brawler",
                            variant="star", kind="signature", rarity="showcase")
        self.v.rebuild(con)
        return con

    def test_signatures_e_showcases_ficam_de_fora(self):
        con = self.montar()
        p = self.a_subir.wantlist(con, "TST")
        self.assertEqual([x["printing_id"] for x in p["items"]], ["tst-002-100"])
        # E diz-se quantas saíram, por critério: uma lista que encolhe sem
        # explicação parece um erro de contagem. Desde 2026-09-09 a signature
        # já nem chega às exclusões — saiu da coleção, que é o âmbito.
        self.assertEqual(p["scope"]["excluded"], 1)
        self.assertEqual(p["scope"]["excluded_by"],
                         [{"criterio": "showcase", "n": 1}])
        con.close()

    def test_a_percentagem_de_master_set_so_mexe_com_a_signature(self):
        """O filtro das listas não mexe na barra; o `master_set.fora` mexe.

        A reimpressão showcase sai da wantlist e continua no denominador; a
        signature saiu dos dois, por decisão dele a 2026-09-09.
        """
        con = self.montar()
        prog = self.metrics.set_payload(con, "TST")["progress"]["master"]
        self.assertEqual(prog["total"], 2)
        con.close()

    def test_a_alt_art_entra_na_mesma_apesar_da_raridade_showcase(self):
        """`so_no_master`: a exclusão é da SEQUÊNCIA, não dos outros blocos.

        54 das 102 artes alternativas reais têm raridade `showcase`; deixá-las
        cair aqui apagava em silêncio o «no fim 1 alt art de cada».
        """
        con = self.montar()
        self.v.add_printing(con, "tst-002a-100", "TST", 2, "Sett, Brawler",
                            variant="a", kind="alt_art", rarity="showcase")
        self.v.rebuild(con)
        p = self.a_subir.wantlist(con, "TST")
        self.assertIn("tst-002a-100", [x["printing_id"] for x in p["items"]])
        con.close()


class TestMesmaListaDaAbaMasterSet(Base):
    """A wantlist por edição não é uma lista nova — é a do «Master set»."""

    def test_os_itens_sao_os_mesmos_e_pela_mesma_ordem(self):
        con = self.v.connect()
        self.v.add_printing(con, "tst-001-100", "TST", 1, "Um")
        self.v.add_printing(con, "tst-002-100", "TST", 2, "Dois",
                            card_type="Legend")
        self.v.add_printing(con, "tst-003-100", "TST", 3, "Três",
                            card_type="Rune")
        self.v.rebuild(con)
        self.preco(con, "tst-001-100", 100)

        m = self.a_subir.master_faltas(con)
        p = self.a_subir.wantlist(con)
        self.assertEqual([x["printing_id"] for d in m["sets"] for x in d["items"]],
                         [x["printing_id"] for x in p["items"]])
        self.assertEqual((m["cards"], m["copies"], m["cents"]),
                         (p["lines"], p["copies"], p["cents"]))
        con.close()

    def test_nao_escreve_na_base(self):
        """É uma sugestão de compra: nada sai nem entra no `copies`."""
        from riftvault import collection
        con = self.v.connect()
        self.v.add_printing(con, "tst-001-100", "TST", 1, "Um")
        self.v.rebuild(con)
        collection.adjust(con, "tst-001-100", 1, source="test")
        antes = con.execute("SELECT printing_id, qty FROM copies").fetchall()
        self.a_subir.wantlist(con)
        depois = con.execute("SELECT printing_id, qty FROM copies").fetchall()
        self.assertEqual([tuple(r) for r in antes], [tuple(r) for r in depois])
        con.close()


if __name__ == "__main__":
    unittest.main()

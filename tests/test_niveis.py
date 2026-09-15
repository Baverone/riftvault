"""A contagem por níveis do master set: 1 de cada, 2 de cada, o playset.

André, 2026-09-08: *"Para a coleção de master set, gostava que fizesses também
uma contagem: quantas cartas faltam para ter 1 de cada, quantas faltam para ter
2 de cada, quantas faltam para ter o playset de cada — do género 1/3 Z % · 2/3
X % · 3/3 Y %."*

O que se fixa aqui: que o alvo do nível k é `min(k, alvo)` — e por isso uma
impressão de alvo 1 (Legend, Battlefield, e desde 2026-09-14 à noite as runas,
*"runas 1 de cada"*) só pode faltar no nível 1 — e que o ÚLTIMO degrau é o
playset inteiro (a função aguenta um alvo de 12, se as runas voltarem a
segui-lo); que o denominador é o mesmo em todos os níveis, que é o da barra do
master set — **só o bloco 1**: a coleção extra (artes alternativas, runas
especiais, sobrenumeradas, promos) não entra, *"só quero % de completo para
masterset!"* —, e que por isso a percentagem do último nível dá EXACTAMENTE a
da barra; que a soma das edições é o global; e que a wantlist por nível pede
exactamente as cópias que a contagem desse nível diz que faltam — pelo mesmo
gerador, sem uma segunda lista. A coleção extra não entra na wantlist em
degrau nenhum (2026-09-15, `listas_de_compra.so_master_set`: acompanha-se na
grelha, não se compra).
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

    def preco(self, con, pid, cents):
        con.execute("INSERT INTO catalog.price_latest (printing_id, price_cents, "
                    "from_foil) VALUES (?,?,0)", (pid, cents))

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


class TestAConta(Base):
    """A função sozinha, com alvos 3 e 1 — que são os do master set real."""

    def test_o_alvo_do_nivel_e_min_k_alvo(self):
        # Uma Unit (alvo 3) sem nenhuma, e um Legend (alvo 1) sem nenhum.
        ls = self.metrics.niveis([(3, 0, 100), (1, 0, 500)])
        self.assertEqual([lv["k"] for lv in ls], [1, 2, 3])
        self.assertEqual([lv["missing"] for lv in ls], [2, 3, 4])
        # No nível 1 falta 1 de cada; no 2 falta a segunda da Unit (o Legend já
        # está no máximo dele); no 3 a terceira.
        self.assertEqual([lv["cents"] for lv in ls], [600, 700, 800])

    def test_a_impressao_de_alvo_1_so_pode_faltar_no_nivel_1(self):
        """Tem o Legend, não tem a Unit: do nível 2 em diante o Legend está feito."""
        ls = self.metrics.niveis([(3, 0, 0), (1, 1, 0)])
        self.assertEqual([lv["done"] for lv in ls], [1, 1, 1])
        self.assertEqual([lv["missing"] for lv in ls], [1, 2, 3])

    def test_o_denominador_e_o_mesmo_em_todos_os_niveis(self):
        """Senão as percentagens não eram comparáveis entre si."""
        ls = self.metrics.niveis([(3, 0, 0), (1, 0, 0), (3, 3, 0)])
        self.assertEqual([lv["total"] for lv in ls], [3, 3, 3])

    def test_as_percentagens(self):
        # 4 impressões: uma completa (3/3), uma com 2, uma com 1, uma a zero.
        ls = self.metrics.niveis([(3, 3, 0), (3, 2, 0), (3, 1, 0), (3, 0, 0)])
        self.assertEqual([lv["done"] for lv in ls], [3, 2, 1])
        self.assertEqual([lv["pct"] for lv in ls], [75.0, 50.0, 25.0])

    def test_os_degraus_sao_o_maior_alvo_ate_ao_playset_comum(self):
        self.assertEqual(len(self.metrics.niveis([(1, 0, 0)])), 1)
        self.assertEqual(len(self.metrics.niveis([(1, 0, 0), (3, 0, 0)])), 3)
        # E dá para pedir mais, para todas as edições mostrarem os mesmos.
        self.assertEqual(len(self.metrics.niveis([(1, 0, 0)], 3)), 3)
        # Um alvo de 12 (as runas, se `runas_especiais.tipos` for `[]`) NÃO
        # faz 12 degraus: do 4.º ao 12.º só as runas mexiam. Ficam os 3 do
        # playset comum, e o último pede as 12.
        self.assertEqual(len(self.metrics.niveis([(3, 0, 0), (12, 0, 0)])), 3)

    def test_o_ultimo_degrau_e_o_playset_inteiro(self):
        """*"1 de cada, 2 de cada, o playset de cada"* — a função pede o alvo
        inteiro no último degrau, seja ele 3 ou 12 (hoje as runas pedem 1, mas
        a regra da função não depende disso)."""
        ls = self.metrics.niveis([(3, 0, 100), (12, 0, 10)])
        self.assertEqual([lv["missing"] for lv in ls], [2, 4, 15])
        self.assertEqual([lv["cents"] for lv in ls], [110, 220, 420])
        # Com 3 cópias da runa, o «2/3» está feito e o «playset» não.
        ls = self.metrics.niveis([(12, 3, 0)])
        self.assertEqual([lv["done"] for lv in ls], [1, 1, 0])

    def test_sem_preco_conta_a_carta_e_nao_o_euro(self):
        ls = self.metrics.niveis([(3, 0, None)])
        self.assertEqual([lv["missing"] for lv in ls], [1, 2, 3])
        self.assertEqual([lv["cents"] for lv in ls], [0, 0, 0])

    def test_alvo_zero_fica_de_fora(self):
        """O que não tem alvo não está no âmbito — nem no numerador nem no de baixo."""
        self.assertEqual(self.metrics.niveis([(0, 0, 100)]), [])


class TestNoPayloadDaEdicao(Base):
    """Os mesmos números, mas vindos do catálogo — e a bater com a barra."""

    def montar(self):
        con = self.v.connect()
        self.v.add_printing(con, "tst-001-100", "TST", 1, "Uma Unit")
        self.v.add_printing(con, "tst-002-100", "TST", 2, "Outra Unit")
        self.v.add_printing(con, "tst-003-100", "TST", 3, "Um Legend",
                            card_type="Legend")
        self.v.add_printing(con, "tst-004-100", "TST", 4, "Fury Rune",
                            card_type="Rune")
        self.v.add_printing(con, "tst-005a-100", "TST", 5, "Uma Unit alt",
                            variant="a", kind="alt_art", rarity="epic")
        self.v.rebuild(con)
        from riftvault import collection
        collection.adjust(con, "tst-001-100", 3, source="test")   # completa
        collection.adjust(con, "tst-002-100", 1, source="test")   # falta 2
        collection.adjust(con, "tst-004-100", 1, source="test")   # runa: completa (1)
        return con

    def test_os_tres_niveis(self):
        con = self.montar()
        ls = self.metrics.set_payload(con, "TST")["progress"]["levels"]
        # 4 impressões no âmbito: 2 Units (alvo 3), 1 Legend (1), 1 runa (1).
        # A arte alternativa é coleção extra e fica de fora dos níveis, como
        # fica da barra.
        self.assertEqual([lv["total"] for lv in ls], [4, 4, 4])
        # Nível 1: tem a Unit completa, a outra com 1 e a runa — falta o
        # Legend. Nível 2 e playset: a Unit completa e a runa (alvo 1, já não
        # lhe pedem mais); à outra Unit falta a segunda e depois a terceira.
        self.assertEqual([lv["done"] for lv in ls], [3, 2, 2])
        self.assertEqual([lv["missing"] for lv in ls], [1, 2, 3])
        con.close()

    def test_a_colecao_extra_nao_entra_nos_niveis(self):
        """Encher a alt art não mexe em degrau nenhum — é «puramente coleção»."""
        from riftvault import collection
        con = self.montar()
        antes = self.metrics.set_payload(con, "TST")["progress"]["levels"]
        collection.adjust(con, "tst-005a-100", 3, source="test")
        depois = self.metrics.set_payload(con, "TST")["progress"]["levels"]
        self.assertEqual(antes, depois)
        con.close()

    def test_o_ultimo_nivel_e_a_barra_do_master_set(self):
        """A conta é a mesma, por degraus: se divergir, é âmbito a divergir."""
        con = self.montar()
        prog = self.metrics.set_payload(con, "TST")["progress"]
        ultimo = prog["levels"][-1]
        self.assertEqual((ultimo["done"], ultimo["total"]),
                         (prog["master"]["done"], prog["master"]["total"]))
        con.close()

    def test_os_tokens_ficam_de_fora_como_na_barra(self):
        con = self.montar()
        self.v.add_printing(con, "tst-t01-100", "TST", 90, "Recruit",
                            variant="t01", kind="token")
        self.v.rebuild(con)
        ls = self.metrics.set_payload(con, "TST")["progress"]["levels"]
        self.assertEqual([lv["total"] for lv in ls], [4, 4, 4])
        con.close()

    def test_conta_copias_e_nao_o_que_vem_a_caminho(self):
        """É a regra da Coleção: a barra não mexe enquanto a encomenda vem."""
        from riftvault import pending
        con = self.montar()
        antes = self.metrics.set_payload(con, "TST")["progress"]["levels"]
        pending.add(con, "tst-002-100", 2)
        depois = self.metrics.set_payload(con, "TST")["progress"]["levels"]
        self.assertEqual(antes, depois)
        con.close()

    def test_o_preco_e_o_das_copias_que_faltam_nesse_nivel(self):
        con = self.montar()
        self.preco(con, "tst-002-100", 100)      # faltam 2
        self.preco(con, "tst-003-100", 1000)     # falta 1 (Legend)
        ls = self.metrics.set_payload(con, "TST")["progress"]["levels"]
        self.assertEqual([lv["cents"] for lv in ls], [1000, 1100, 1200])
        con.close()


class TestGlobalEPorEdicao(Base):
    """Por edição soma ao global — é o que deixa o cliente trocar uma delas."""

    def montar(self):
        self.com_config({"sets": {"AAA": {"name": "Alfa", "order": 1},
                                  "ZZZ": {"name": "Zeta", "order": 2}}})
        con = self.v.connect()
        self.v.add_printing(con, "aaa-001-100", "AAA", 1, "Alfa um")
        self.v.add_printing(con, "aaa-002-100", "AAA", 2, "Alfa dois",
                            card_type="Legend")
        self.v.add_printing(con, "zzz-001-100", "ZZZ", 1, "Zeta um")
        self.v.rebuild(con)
        from riftvault import collection
        collection.adjust(con, "aaa-001-100", 2, source="test")
        self.preco(con, "aaa-001-100", 100)
        self.preco(con, "zzz-001-100", 200)
        return con

    def test_a_soma_das_edicoes_e_o_global(self):
        con = self.montar()
        p = self.metrics.niveis_payload(con)
        for campo in ("done", "total", "missing", "cents"):
            for i, lv in enumerate(p["levels"]):
                self.assertEqual(
                    lv[campo], sum(ls[i][campo] for ls in p["by_set"].values()),
                    f"{campo} no nível {i + 1}")
        con.close()

    def test_todas_as_edicoes_tem_os_mesmos_degraus(self):
        """O ZZZ só tem Units e o AAA tem um Legend: os degraus são do catálogo."""
        con = self.montar()
        p = self.metrics.niveis_payload(con)
        self.assertEqual(p["max"], 3)
        self.assertEqual({s: len(ls) for s, ls in p["by_set"].items()},
                         {"AAA": 3, "ZZZ": 3})
        con.close()

    def test_bate_certo_com_o_payload_de_cada_edicao(self):
        con = self.montar()
        p = self.metrics.niveis_payload(con)
        for sid in ("AAA", "ZZZ"):
            self.assertEqual(p["by_set"][sid],
                             self.metrics.set_payload(con, sid)["progress"]["levels"])
        con.close()

    def test_o_index_leva_a_contagem(self):
        con = self.montar()
        idx = self.metrics.index_payload(con)
        self.assertEqual(idx["levels"]["max"], 3)
        self.assertEqual(sorted(idx["levels"]["by_set"]), ["AAA", "ZZZ"])
        con.close()


class TestWantlistPorNivel(Base):
    """A lista de cada degrau — mesmo gerador, alvos cortados por `min(k, alvo)`."""

    def montar(self):
        con = self.v.connect()
        self.v.add_printing(con, "tst-001-100", "TST", 1, "Uma Unit")
        self.v.add_printing(con, "tst-002-100", "TST", 2, "Um Legend",
                            card_type="Legend")
        self.v.add_printing(con, "tst-003a-100", "TST", 3, "Uma alt",
                            variant="a", kind="alt_art", rarity="epic")
        self.v.rebuild(con)
        self.preco(con, "tst-001-100", 100)
        self.preco(con, "tst-002-100", 500)
        self.preco(con, "tst-003a-100", 900)
        return con

    def test_o_nivel_1_pede_uma_de_cada(self):
        """Só do master set: a alt art (coleção extra) não entra em nível
        nenhum — acompanha-se na grelha, não se compra (2026-09-15)."""
        con = self.montar()
        p = self.a_subir.wantlist(con, "TST", nivel=1)
        self.assertEqual({x["printing_id"]: x["missing"] for x in p["items"]},
                         {"tst-001-100": 1, "tst-002-100": 1})
        self.assertEqual(p["copies"], 2)
        self.assertEqual(p["cents"], 100 + 500)
        con.close()

    def test_o_nivel_2_so_muda_as_que_tem_playset(self):
        con = self.montar()
        p = self.a_subir.wantlist(con, "TST", nivel=2)
        self.assertEqual({x["printing_id"]: x["missing"] for x in p["items"]},
                         {"tst-001-100": 2, "tst-002-100": 1})
        con.close()

    def test_sem_nivel_e_a_lista_de_sempre(self):
        con = self.montar()
        cheia = self.a_subir.wantlist(con, "TST")
        alto = self.a_subir.wantlist(con, "TST", nivel=3)
        self.assertEqual(cheia["text"], alto["text"])
        self.assertEqual(cheia["copies"], 4)     # 3 + 1; a alt art fica de fora
        con.close()

    def test_a_runa_pede_1_em_todos_os_degraus(self):
        """*"runas 1 de cada"* (2026-09-14, à noite): a runa é de alvo 1, como
        um Legend — sai igual em todos os níveis e sem `full_target`. O último
        degrau (`--nivel 3`) continua a ser a lista de sempre."""
        con = self.montar()
        self.v.add_printing(con, "tst-004-100", "TST", 4, "Fury Rune",
                            card_type="Rune")
        self.v.rebuild(con)
        self.assertEqual(self.metrics.niveis_max(con), 3)
        alto = self.a_subir.wantlist(con, "TST", nivel=3)
        runa = next(x for x in alto["items"] if x["printing_id"] == "tst-004-100")
        self.assertEqual(runa["missing"], 1)
        self.assertIsNone(alto["level"])
        for k in (1, 2):
            p = self.a_subir.wantlist(con, "TST", nivel=k)
            runa = next(x for x in p["items"] if x["printing_id"] == "tst-004-100")
            self.assertEqual((runa["target"], runa["missing"]), (1, 1), f"nível {k}")
            self.assertNotIn("full_target", runa)
        con.close()

    def so_master(self, con, itens):
        """Os itens da lista que são do bloco 1 — o âmbito da contagem."""
        linhas = {r["printing_id"]: r for r in con.execute("SELECT * FROM catalog.printings")}
        return [x for x in itens
                if self.metrics.bloco(linhas[x["printing_id"]]) == self.metrics.BLOCO_MASTER]

    def test_a_lista_do_nivel_pede_o_que_a_contagem_do_nivel_diz(self):
        """As duas respostas à mesma pergunta têm de dar o mesmo número.

        Desde 2026-09-15 a lista é só o master set, como a contagem
        (`listas_de_compra.so_master_set`): a coleção extra (a alt art) não
        entra em nenhum degrau — *"apenas pedi para ser feito track de playset
        para eu saber exatamente quantas tenho"*. Na noite de 14/09 entrava ao
        mesmo degrau e era a diferença entre os dois números; durou uma noite.
        """
        from riftvault import collection
        con = self.montar()
        collection.adjust(con, "tst-001-100", 1, source="test")
        ls = self.metrics.set_payload(con, "TST")["progress"]["levels"]
        for lv in ls:
            p = self.a_subir.wantlist(con, "TST", nivel=lv["k"])
            master = self.so_master(con, p["items"])
            self.assertEqual(sum(x["missing"] for x in master), lv["missing"],
                             f"nível {lv['k']}")
            self.assertEqual(sum(x["total"] for x in master), lv["cents"],
                             f"nível {lv['k']}")
            extra = [x for x in p["items"] if x not in master]
            self.assertEqual(extra, [], f"nível {lv['k']}")
            self.assertNotIn("tst-003a-100", p["text"], f"nível {lv['k']}")
            # A página diz que a tirou, e de que bloco.
            self.assertTrue(p["scope"]["so_master_set"])
            self.assertIn("alt_art", p["scope"]["excluded_blocks"])
        con.close()

    def test_o_alvo_que_sai_e_o_do_nivel_e_o_inteiro_nao_se_perde(self):
        con = self.montar()
        p = self.a_subir.wantlist(con, "TST", nivel=1)
        it = next(x for x in p["items"] if x["printing_id"] == "tst-001-100")
        self.assertEqual((it["target"], it["full_target"]), (1, 3))
        # A de alvo 1 (o Legend) sai igual em todos os níveis, e sem `full_target`.
        leg = next(x for x in p["items"] if x["printing_id"] == "tst-002-100")
        self.assertEqual(leg["target"], 1)
        self.assertNotIn("full_target", leg)
        con.close()

    def test_o_que_ja_tem_ate_ao_nivel_sai_da_lista(self):
        from riftvault import collection
        con = self.montar()
        collection.adjust(con, "tst-001-100", 1, source="test")
        p = self.a_subir.wantlist(con, "TST", nivel=1)
        self.assertNotIn("tst-001-100", [x["printing_id"] for x in p["items"]])
        con.close()

    def test_o_que_vem_a_caminho_conta_como_tido(self):
        from riftvault import pending
        con = self.montar()
        pending.add(con, "tst-001-100", 1)
        p = self.a_subir.wantlist(con, "TST", nivel=1)
        self.assertNotIn("tst-001-100", [x["printing_id"] for x in p["items"]])
        con.close()

    def test_o_texto_continua_a_sair_do_gerador_unico(self):
        con = self.montar()
        p = self.a_subir.wantlist(con, "TST", nivel=2)
        self.assertEqual(p["text"],
                         "\n".join(self.cardmarket.linha(x) for x in p["items"]))
        self.assertNotIn("€", p["text"])
        con.close()

    def test_a_lista_do_nivel_esta_contida_na_de_cima(self):
        """Comprar por degraus nunca pode pedir uma carta que o degrau seguinte
        não peça — senão não eram degraus da mesma lista."""
        con = self.montar()
        cima = {x["printing_id"] for x in self.a_subir.wantlist(con, "TST")["items"]}
        for k in (1, 2):
            baixo = {x["printing_id"] for x in
                     self.a_subir.wantlist(con, "TST", nivel=k)["items"]}
            self.assertTrue(baixo <= cima, f"nível {k}")
        con.close()

    def test_o_nivel_nao_mexe_na_contagem_da_barra(self):
        """A wantlist é uma vista; a métrica não se mexe por causa dela."""
        con = self.montar()
        antes = self.metrics.set_payload(con, "TST")["progress"]["master"]
        self.a_subir.wantlist(con, "TST", nivel=1)
        self.assertEqual(antes,
                         self.metrics.set_payload(con, "TST")["progress"]["master"])
        con.close()


class TestOsNiveisSaoSoOMasterSet(Base):
    """As runas especiais e as artes alternativas NÃO entram em degrau nenhum.

    São coleção extra (2026-09-14, à noite: *"só quero % de completo para
    masterset!"*): aparecem na grelha nos blocos delas, mas a contagem por
    níveis é a barra em degraus, e a barra é só a sequência.
    """

    def test_a_runa_especial_e_a_alt_art_ficam_fora_de_todos_os_niveis(self):
        con = self.v.connect()
        self.v.add_printing(con, "tst-001-100", "TST", 1, "Uma Unit")
        self.v.add_printing(con, "tst-002-100", "TST", 2, "Fury Rune",
                            card_type="Rune")
        self.v.add_printing(con, "tst-002a-100", "TST", 2, "Fury Rune",
                            variant="a", kind="alt_art", card_type="Rune",
                            rarity="epic")
        self.v.add_printing(con, "tst-003a-100", "TST", 3, "Uma alt",
                            variant="a", kind="alt_art", rarity="epic")
        self.v.rebuild(con)
        p = self.metrics.set_payload(con, "TST")
        blocos = {b["id"]: b["counts"] for b in p["blocks"]}
        self.assertEqual(blocos, {"master": True, "rune_special": False,
                                  "alt_art": False})
        ls = p["progress"]["levels"]
        # Só a Unit base e a runa base: as outras duas estão nos blocos que
        # não contam.
        self.assertEqual([lv["total"] for lv in ls], [2, 2, 2])
        # Nada em casa: no nível 1 faltam as 2, no 2 a segunda da Unit (a runa
        # é de alvo 1), e no playset a terceira.
        self.assertEqual([lv["missing"] for lv in ls], [2, 3, 4])
        con.close()


class TestNoSitePublicado(Base):
    """A contagem vai nos ficheiros estáticos — o site publicado é o mesmo."""

    def test_o_build_leva_os_niveis_no_index_e_em_cada_edicao(self):
        import importlib
        from tests.fixture import catalogo_simples
        catalogo_simples(self.v)
        from riftvault import build, decks, metrics, server
        for m in (metrics, decks, build, server):
            importlib.reload(m)
        out = self.v.root / "site"
        build.build(out, log=lambda *_: None)

        idx = json.loads((out / "api" / "index.json").read_text(encoding="utf-8"))
        self.assertEqual(idx["levels"]["max"], 3)
        self.assertEqual(len(idx["levels"]["by_set"]["TST"]), 3)

        p = json.loads((out / "api" / "set" / "TST.json").read_text(encoding="utf-8"))
        ls = p["progress"]["levels"]
        self.assertEqual(idx["levels"]["by_set"]["TST"], ls)
        # O catálogo de brincar tem 2 Units com 3 cópias e um Legend com 1:
        # está tudo completo nos três níveis.
        self.assertEqual([lv["missing"] for lv in ls], [0, 0, 0])
        self.assertEqual(ls[-1]["done"], p["progress"]["master"]["done"])


if __name__ == "__main__":
    unittest.main()

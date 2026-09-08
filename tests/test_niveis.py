"""A contagem por níveis do master set: 1 de cada, 2 de cada, o playset.

André, 2026-09-08: *"Para a coleção de master set, gostava que fizesses também
uma contagem: quantas cartas faltam para ter 1 de cada, quantas faltam para ter
2 de cada, quantas faltam para ter o playset de cada — do género 1/3 Z % · 2/3
X % · 3/3 Y %."*

O que se fixa aqui: que o alvo do nível k é `min(k, alvo)` — e por isso uma
impressão de alvo 1 (runa, Legend, arte alternativa) só pode faltar no nível 1;
que o denominador é o mesmo em todos os níveis, que é o da barra do master set,
e que por isso a percentagem do último nível dá EXACTAMENTE a da barra; que a
soma das edições é o global; e que a wantlist por nível pede exactamente as
cópias que a contagem desse nível diz que faltam — pelo mesmo gerador, sem uma
segunda lista.
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

    def test_os_degraus_sao_o_maior_alvo(self):
        self.assertEqual(len(self.metrics.niveis([(1, 0, 0)])), 1)
        self.assertEqual(len(self.metrics.niveis([(1, 0, 0), (3, 0, 0)])), 3)
        # E dá para pedir mais, para todas as edições mostrarem os mesmos.
        self.assertEqual(len(self.metrics.niveis([(1, 0, 0)], 3)), 3)

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
        collection.adjust(con, "tst-004-100", 1, source="test")   # runa: 1 chega
        return con

    def test_os_tres_niveis(self):
        con = self.montar()
        ls = self.metrics.set_payload(con, "TST")["progress"]["levels"]
        # 5 impressões no âmbito: 3 Units (alvo 3, 3, 1 para a alt art),
        # 1 Legend (1), 1 runa (1).
        self.assertEqual([lv["total"] for lv in ls], [5, 5, 5])
        # Nível 1: tem a Unit completa, a outra com 1 e a runa — faltam o
        # Legend e a arte alternativa.
        self.assertEqual([lv["done"] for lv in ls], [3, 2, 2])
        self.assertEqual([lv["missing"] for lv in ls], [2, 3, 4])
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
        self.assertEqual([lv["total"] for lv in ls], [5, 5, 5])
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
        con = self.montar()
        p = self.a_subir.wantlist(con, "TST", nivel=1)
        self.assertEqual({x["printing_id"]: x["missing"] for x in p["items"]},
                         {"tst-001-100": 1, "tst-002-100": 1, "tst-003a-100": 1})
        self.assertEqual(p["copies"], 3)
        self.assertEqual(p["cents"], 100 + 500 + 900)
        con.close()

    def test_o_nivel_2_so_muda_as_que_tem_playset(self):
        con = self.montar()
        p = self.a_subir.wantlist(con, "TST", nivel=2)
        self.assertEqual({x["printing_id"]: x["missing"] for x in p["items"]},
                         {"tst-001-100": 2, "tst-002-100": 1, "tst-003a-100": 1})
        con.close()

    def test_sem_nivel_e_a_lista_de_sempre(self):
        con = self.montar()
        cheia = self.a_subir.wantlist(con, "TST")
        alto = self.a_subir.wantlist(con, "TST", nivel=3)
        self.assertEqual(cheia["text"], alto["text"])
        self.assertEqual(cheia["copies"], 5)     # 3 + 1 + 1
        con.close()

    def test_a_lista_do_nivel_pede_o_que_a_contagem_do_nivel_diz(self):
        """As duas respostas à mesma pergunta têm de dar o mesmo número."""
        from riftvault import collection
        con = self.montar()
        collection.adjust(con, "tst-001-100", 1, source="test")
        ls = self.metrics.set_payload(con, "TST")["progress"]["levels"]
        for lv in ls:
            p = self.a_subir.wantlist(con, "TST", nivel=lv["k"])
            self.assertEqual(p["copies"], lv["missing"], f"nível {lv['k']}")
            self.assertEqual(p["cents"], lv["cents"], f"nível {lv['k']}")
        con.close()

    def test_o_alvo_que_sai_e_o_do_nivel_e_o_inteiro_nao_se_perde(self):
        con = self.montar()
        p = self.a_subir.wantlist(con, "TST", nivel=1)
        it = next(x for x in p["items"] if x["printing_id"] == "tst-001-100")
        self.assertEqual((it["target"], it["full_target"]), (1, 3))
        # A de alvo 1 sai igual em todos os níveis, e sem `full_target`.
        alt = next(x for x in p["items"] if x["printing_id"] == "tst-003a-100")
        self.assertEqual(alt["target"], 1)
        self.assertNotIn("full_target", alt)
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


class TestOsNiveisSaoOsDaContagemDeCadaBloco(Base):
    """As runas especiais e as artes alternativas entram — no nível 1.

    Ficam no âmbito porque contam para a barra (são dois dos três blocos da
    Coleção); e como o alvo delas é 1, `min(k, alvo)` nunca lhes pede mais.
    """

    def test_a_runa_especial_e_a_alt_art_contam_so_no_nivel_1(self):
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
        blocos = {b["id"] for b in p["blocks"]}
        self.assertEqual(blocos, {"master", "rune_special", "alt_art"})
        ls = p["progress"]["levels"]
        self.assertEqual([lv["total"] for lv in ls], [4, 4, 4])
        # Nada em casa: no nível 1 faltam as 4; do 2 em diante só a Unit sobe.
        self.assertEqual([lv["missing"] for lv in ls], [4, 5, 6])
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

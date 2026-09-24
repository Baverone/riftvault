"""O painel do topo da Coleção — três cartões e dois quadros (2026-09-21).

O André escolheu o «layout H»: por baixo das edições e por cima da grelha,
«1 de cada», «2 de cada», «playset» em tenho/total, e por baixo os quadros
Raridade e Domínio, uma linha por categoria com os três níveis.

O que se fixa aqui, por aritmética e contra um catálogo de brincar:

  - nível 1 >= nível 2 >= nível 3, no total e em TODAS as categorias dos dois
    quadros, em TODAS as edições e em «Todas»;
  - a soma das linhas por raridade É o total do bloco, nível a nível — e o
    mesmo para os domínios;
  - «Todas» é a soma das edições;
  - as runas nunca entram (nem no total, nem nos níveis, nem nos quadros), e
    o payload diz quantas ficaram de fora;
  - as escondidas e as retiradas seguem a regra da grelha (`metrics.escondida`);
  - o bloco escolhido é o da grelha (`metrics.bloco`), com o alvo do
    `metrics.alvo` — nos blocos de alvo 1 os três níveis coincidem;
  - é só leitura, sem euros;
  - o gémeo em JavaScript (`painelContar` no app.js) dá o mesmo que o Python
    sobre os mesmos itens (corre no node, se houver).
"""

from __future__ import annotations

import importlib
import json
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.fixture import REPO, Vault

APP_JS = REPO / "riftvault" / "web" / "app.js"


class Base(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.close)
        from riftvault import metrics, painel
        importlib.reload(painel)
        self.metrics = metrics
        self.painel = painel

    def com_config(self, extra: dict):
        import os
        from riftvault import config
        caminho = self.v.root / "config.json"
        caminho.write_text(json.dumps(extra), encoding="utf-8")
        os.environ["RIFTVAULT_CONFIG"] = str(caminho)
        importlib.reload(config)
        config.load.cache_clear()

        def repor():
            os.environ.pop("RIFTVAULT_CONFIG", None)
            importlib.reload(config)
            config.load.cache_clear()

        self.addCleanup(repor)

    def montar(self):
        """Duas edições com Units, Legends, uma runa, uma alt art, uma
        sobrenumerada, uma promo, um token e uma signature — e cópias a
        vários níveis, para os três níveis não coincidirem."""
        self.com_config({"sets": {"AAA": {"name": "Alfa", "order": 1},
                                  "ZZZ": {"name": "Zeta", "order": 2}}})
        con = self.v.connect()
        add = self.v.add_printing
        # AAA
        add(con, "aaa-001-100", "AAA", 1, "Fury Unit", rarity="common", domains=("Fury",), size=100)
        add(con, "aaa-002-100", "AAA", 2, "Body Unit", rarity="uncommon", domains=("Body",), size=100)
        add(con, "aaa-003-100", "AAA", 3, "Mixed Unit", rarity="rare", domains=("Body", "Calm"), size=100)
        add(con, "aaa-004-100", "AAA", 4, "Grey Gear", card_type="Gear", rarity="epic",
            domains=("Colorless",), size=100)
        add(con, "aaa-005-100", "AAA", 5, "A Legend", card_type="Legend", rarity="epic",
            domains=("Mind",), size=100)
        add(con, "aaa-006-100", "AAA", 6, "Fury Rune", card_type="Rune", rarity="common",
            domains=("Fury",), size=100)
        add(con, "aaa-006a-100", "AAA", 6, "Fury Rune", variant="a", kind="alt_art",
            card_type="Rune", rarity="showcase", base_rarity="common", domains=("Fury",), size=100)
        add(con, "aaa-001a-100", "AAA", 1, "Fury Unit", variant="a", kind="alt_art",
            rarity="showcase", base_rarity="common", domains=("Fury",), size=100)
        add(con, "aaa-101-100", "AAA", 101, "Fury Unit", rarity="showcase", domains=("Fury",), size=100)
        add(con, "aaa-t01-100", "AAA", 90, "Recruit", variant="t01", kind="token", lane="t",
            domains=None)
        add(con, "aaa-102s-100", "AAA", 102, "A Legend", variant="star", kind="signature",
            rarity="showcase", domains=("Mind",), size=100)
        # ZZZ
        add(con, "zzz-001-050", "ZZZ", 1, "Order Spell", card_type="Spell", rarity="common",
            domains=("Order",), size=50)
        add(con, "zzz-002-050", "ZZZ", 2, "Chaos Battlefield", card_type="Battlefield",
            rarity="rare", domains=("Chaos",), size=50)
        add(con, "zzz-sp1-006", "ZZZ", 1, "Promo Unit", variant="sp1", kind="special", lane="sp",
            rarity="epic", domains=("Calm",), codigo="ZZZ-SP1/006")
        self.v.rebuild(con)
        from riftvault import collection
        adj = lambda pid, n: collection.adjust(con, pid, n, source="test")  # noqa: E731
        adj("aaa-001-100", 3)     # completa
        adj("aaa-002-100", 2)     # nível 2, não playset
        adj("aaa-003-100", 1)     # só nível 1
        adj("aaa-005-100", 1)     # Legend completo (alvo 1)
        adj("aaa-006-100", 3)     # a runa — não pode contar
        adj("aaa-006a-100", 2)    # a runa em alt art — retirada
        adj("aaa-001a-100", 1)    # alt art, 1 de 3
        adj("aaa-101-100", 2)     # sobrenumerada, «2/1»
        adj("aaa-t01-100", 4)     # token escondido
        adj("zzz-001-050", 3)
        adj("zzz-sp1-006", 1)
        return con


class TestAConta(Base):
    """`painel.contar` sozinho — a definição dos três níveis."""

    def test_os_tres_niveis(self):
        c = self.painel.contar([
            (3, 3, "common", "fury"),   # playset
            (3, 2, "common", "fury"),   # 2 de cada
            (3, 1, "rare", "body"),     # 1 de cada
            (3, 0, "rare", "body"),     # nada
            (1, 1, "epic", "mind"),     # Legend: os três de uma vez
        ])
        self.assertEqual(c["n"], 5)
        self.assertEqual(c["levels"], [4, 3, 2])

    def test_o_alvo_1_coincide_nos_tres(self):
        for tem in (0, 1, 2):
            c = self.painel.contar([(1, tem, "epic", "mind")])
            self.assertEqual(len(set(c["levels"])), 1, tem)
        self.assertEqual(self.painel.contar([(1, 0, "epic", "mind")])["levels"], [0, 0, 0])
        self.assertEqual(self.painel.contar([(1, 2, "epic", "mind")])["levels"], [1, 1, 1])

    def test_o_nivel_2_e_min_2_alvo_e_o_3_e_o_alvo(self):
        # Um alvo de 12: com 2 cópias está no nível 2, não no playset.
        self.assertEqual(self.painel.contar([(12, 2, "c", "fury")])["levels"], [1, 1, 0])
        self.assertEqual(self.painel.contar([(12, 12, "c", "fury")])["levels"], [1, 1, 1])

    def test_conta_cartas_nao_copias(self):
        c = self.painel.contar([(3, 0, "common", "fury"), (3, 1, "common", "fury")])
        self.assertEqual(c["n"], 2)
        self.assertEqual(c["levels"], [1, 0, 0])

    def test_as_linhas_vem_pela_ordem_da_maqueta_com_nomes_em_portugues(self):
        c = self.painel.contar([
            (3, 3, "epic", "order"), (3, 3, "common", "multi"), (3, 3, "rare", "none"),
            (3, 3, "uncommon", "fury"), (3, 3, "common", "body"),
        ])
        self.assertEqual([r["id"] for r in c["rarity"]], ["common", "uncommon", "rare", "epic"])
        self.assertEqual([r["label"] for r in c["rarity"]], ["Comuns", "Incomuns", "Raras", "Épicas"])
        self.assertEqual([d["id"] for d in c["domain"]], ["fury", "body", "order", "none", "multi"])
        self.assertEqual([d["label"] for d in c["domain"]],
                         ["Fury", "Body", "Order", "Sem domínio", "Multi-domínio"])

    def test_uma_categoria_nova_aparece_na_mesma(self):
        """Um domínio ou uma raridade que o catálogo traga de novo não
        desaparece: entra com o nome que trouxer — o domínio antes das duas
        linhas de fecho, a raridade no fim."""
        c = self.painel.contar([(3, 1, "mythic", "void"), (3, 1, "common", "multi")])
        self.assertEqual([r["id"] for r in c["rarity"]], ["common", "mythic"])
        self.assertEqual(c["rarity"][1]["label"], "Mythic")
        self.assertEqual([d["id"] for d in c["domain"]], ["void", "multi"])

    def test_vazio(self):
        self.assertEqual(self.painel.contar([]),
                         {"n": 0, "levels": [0, 0, 0], "rarity": [], "domain": []})


class TestDominio(Base):
    def test_um_dominio(self):
        self.assertEqual(self.painel.dominio('["Fury"]'), "fury")

    def test_dois_dominios_e_multi(self):
        self.assertEqual(self.painel.dominio('["Body", "Calm"]'), "multi")

    def test_colorless_e_sem_dominio(self):
        self.assertEqual(self.painel.dominio('["Colorless"]'), "none")
        self.assertEqual(self.painel.dominio("[]"), "none")
        self.assertEqual(self.painel.dominio(None), "none")
        self.assertEqual(self.painel.dominio("não é json"), "none")


class TestAritmetica(Base):
    """As invariantes, em todas as edições, em «Todas» e em todos os blocos."""

    def blocos(self, p):
        for sid, blocos in p["sets"].items():
            for bid, c in blocos.items():
                yield sid, bid, c

    def test_nivel1_maior_ou_igual_nivel2_maior_ou_igual_nivel3(self):
        con = self.montar()
        p = self.painel.payload(con)
        vistos = 0
        for sid, bid, c in self.blocos(p):
            for linha in [c] + c["rarity"] + c["domain"]:
                n1, n2, n3 = linha["levels"]
                self.assertGreaterEqual(linha["n"], n1, (sid, bid, linha))
                self.assertGreaterEqual(n1, n2, (sid, bid, linha))
                self.assertGreaterEqual(n2, n3, (sid, bid, linha))
                vistos += 1
        self.assertGreater(vistos, 20)
        con.close()

    def test_a_soma_das_raridades_e_o_total_do_bloco_e_os_dominios_tambem(self):
        con = self.montar()
        p = self.painel.payload(con)
        for sid, bid, c in self.blocos(p):
            for quadro in ("rarity", "domain"):
                linhas = c[quadro]
                self.assertEqual(sum(l["n"] for l in linhas), c["n"], (sid, bid, quadro))
                for i in range(3):
                    self.assertEqual(sum(l["levels"][i] for l in linhas), c["levels"][i],
                                     (sid, bid, quadro, i))
        con.close()

    def test_todas_e_a_soma_das_edicoes(self):
        con = self.montar()
        p = self.painel.payload(con)
        todas = p["sets"][self.painel.TODAS]
        edicoes = [b for s, b in p["sets"].items() if s != self.painel.TODAS]
        self.assertEqual(len(edicoes), 2)
        for bid, c in todas.items():
            partes = [b[bid] for b in edicoes if bid in b]
            self.assertEqual(c["n"], sum(x["n"] for x in partes), bid)
            for i in range(3):
                self.assertEqual(c["levels"][i], sum(x["levels"][i] for x in partes), (bid, i))
            for quadro in ("rarity", "domain"):
                for linha in c[quadro]:
                    soma = [x for b in partes for x in b[quadro] if x["id"] == linha["id"]]
                    self.assertEqual(linha["n"], sum(x["n"] for x in soma), (bid, linha["id"]))
        con.close()

    def test_os_niveis_nao_sao_percentagens(self):
        con = self.montar()
        p = self.painel.payload(con)
        for _, _, c in self.blocos(p):
            for v in c["levels"]:
                self.assertIsInstance(v, int)
                self.assertLessEqual(v, c["n"])
        con.close()


class TestTudo(Base):
    """O chip «Tudo» (2026-09-21): todos os blocos de UMA edição somados, cada
    impressão com o alvo do SEU bloco. Não confundir com «Todas» (edições)."""

    def soma(self, blocos, quadro=None):
        """A soma dos blocos (sem o «tudo»), nível a nível — no total ou numa
        das linhas de um quadro."""
        partes = [c for bid, c in blocos.items() if bid != self.painel.TUDO]
        if quadro is None:
            return {"n": sum(c["n"] for c in partes),
                    "levels": [sum(c["levels"][i] for c in partes) for i in range(3)]}
        por: dict[str, dict] = {}
        for c in partes:
            for l in c[quadro]:
                acc = por.setdefault(l["id"], {"n": 0, "levels": [0, 0, 0]})
                acc["n"] += l["n"]
                acc["levels"] = [a + b for a, b in zip(acc["levels"], l["levels"])]
        return por

    def test_o_tudo_esta_em_cada_edicao_e_no_fim_da_fila(self):
        con = self.montar()
        p = self.painel.payload(con)
        self.assertEqual(p["blocks"][-1]["id"], self.painel.TUDO)
        self.assertEqual(p["blocks"][-1]["label"], "Tudo")
        self.assertIsNone(p["blocks"][-1]["counts"])   # não é um bloco da grelha
        for sid in ("AAA", "ZZZ", self.painel.TODAS):
            self.assertIn(self.painel.TUDO, p["sets"][sid], sid)
            self.assertEqual(list(p["sets"][sid])[-1], self.painel.TUDO, sid)
        # O master set continua a ser o primeiro — o que abre por omissão.
        self.assertEqual(p["blocks"][0]["id"], "master")
        con.close()

    def test_o_tudo_de_uma_edicao_e_a_soma_dos_blocos_nivel_a_nivel(self):
        con = self.montar()
        p = self.painel.payload(con)
        for sid in ("AAA", "ZZZ"):
            blocos = p["sets"][sid]
            tudo = blocos[self.painel.TUDO]
            esperado = self.soma(blocos)
            self.assertEqual(tudo["n"], esperado["n"], sid)
            self.assertEqual(tudo["levels"], esperado["levels"], sid)
            for quadro in ("rarity", "domain"):
                por = self.soma(blocos, quadro)
                self.assertEqual({l["id"]: {"n": l["n"], "levels": l["levels"]}
                                  for l in tudo[quadro]}, por, (sid, quadro))
        # E com os números escritos: AAA master [4,3,2] de 5 + sobrenumerada
        # [1,1,1] de 1 (tem 2, alvo 1) + alt art [1,0,0] de 3 (tem 1).
        tudo = p["sets"]["AAA"][self.painel.TUDO]
        self.assertEqual(tudo["n"], 7)
        self.assertEqual(tudo["levels"], [6, 4, 3])
        con.close()

    def test_cada_bloco_entra_com_o_seu_alvo_nao_ha_alvo_unico(self):
        """A sobrenumerada (alvo 1, tem 2) está no playset dentro do «Tudo»;
        se o «Tudo» pusesse o playset da sequência (3) por cima de tudo, ela
        ficava fora do playset e o total dava [6, 4, 2] em vez de [6, 4, 3]."""
        con = self.montar()
        tudo = self.painel.payload(con)["sets"]["AAA"][self.painel.TUDO]
        self.assertEqual(tudo["levels"], [6, 4, 3])
        # A prova pela negativa: o mesmo conjunto com alvo 3 em tudo.
        itens = [(3, 3, "c", "fury"), (3, 2, "u", "body"), (3, 1, "r", "multi"),
                 (3, 0, "e", "none"), (1, 1, "e", "mind"),      # o master
                 (3, 2, "showcase", "fury"),                   # a sobrenumerada, a 3
                 (3, 1, "c", "fury")]                          # a alt art
        self.assertEqual(self.painel.contar(itens)["levels"], [6, 4, 2])
        # E com a promo do ZZZ (alvo 1, tem 1): completa no «Tudo».
        zzz = self.painel.payload(con)["sets"]["ZZZ"][self.painel.TUDO]
        self.assertEqual(zzz["n"], 3)              # Spell 3/3, Battlefield 0/1, promo 1/1
        self.assertEqual(zzz["levels"], [2, 2, 2])
        con.close()

    def test_as_raridades_e_os_dominios_somam_o_total_do_tudo(self):
        con = self.montar()
        p = self.painel.payload(con)
        for sid in ("AAA", "ZZZ", self.painel.TODAS):
            tudo = p["sets"][sid][self.painel.TUDO]
            for quadro in ("rarity", "domain"):
                self.assertEqual(sum(l["n"] for l in tudo[quadro]), tudo["n"], (sid, quadro))
                for i in range(3):
                    self.assertEqual(sum(l["levels"][i] for l in tudo[quadro]),
                                     tudo["levels"][i], (sid, quadro, i))
        con.close()

    def test_o_tudo_de_todas_e_a_soma_do_tudo_das_edicoes(self):
        con = self.montar()
        p = self.painel.payload(con)
        edicoes = [b[self.painel.TUDO] for s, b in p["sets"].items() if s != self.painel.TODAS]
        self.assertEqual(len(edicoes), 2)
        tudo = p["sets"][self.painel.TODAS][self.painel.TUDO]
        self.assertEqual(tudo["n"], sum(x["n"] for x in edicoes))
        self.assertEqual(tudo["levels"], [sum(x["levels"][i] for x in edicoes) for i in range(3)])
        for quadro in ("rarity", "domain"):
            for linha in tudo[quadro]:
                partes = [x for e in edicoes for x in e[quadro] if x["id"] == linha["id"]]
                self.assertEqual(linha["n"], sum(x["n"] for x in partes), (quadro, linha["id"]))
                self.assertEqual(linha["levels"],
                                 [sum(x["levels"][i] for x in partes) for i in range(3)],
                                 (quadro, linha["id"]))
        self.assertEqual(tudo["n"], 10)
        self.assertEqual(tudo["levels"], [8, 6, 5])
        con.close()

    def test_as_runas_ficam_fora_do_tudo(self):
        con = self.montar()
        p = self.painel.payload(con)
        tudo = p["sets"]["AAA"][self.painel.TUDO]
        # 7 impressões: a runa base (tem 3) e a runa alt art (retirada) não estão.
        self.assertEqual(tudo["n"], 7)
        self.assertEqual(sum(l["n"] for l in tudo["domain"] if l["id"] == "fury"), 3)
        from riftvault import collection
        collection.adjust(con, "aaa-006-100", 9, source="test")
        self.assertEqual(self.painel.payload(con)["sets"]["AAA"][self.painel.TUDO], tudo)
        con.close()

    def test_o_tudo_chega_a_edicao_ao_index_e_ao_texto(self):
        con = self.montar()
        p = self.painel.payload(con)
        s = self.metrics.set_payload(con, "AAA")
        self.assertEqual(s["progress"]["painel"]["blocks"][self.painel.TUDO],
                         p["sets"]["AAA"][self.painel.TUDO])
        self.assertIn(self.painel.TUDO, self.metrics.index_payload(con)["painel"]["sets"]["AAA"])
        t = self.painel.texto(p, self.metrics.sets_payload(con))
        self.assertIn("Tudo — cada bloco com o seu alvo", t)
        self.assertIn("6/7", t)
        con.close()

    def test_o_app_js_tem_o_chip_no_fim_e_abre_no_master_set(self):
        js = APP_JS.read_text(encoding="utf-8")
        self.assertIn("const TUDO = 'tudo'", js)
        self.assertIn("[...ids, TUDO]", js)                       # no fim da fila
        self.assertIn("bloco !== TUDO", js)                       # sem filtro de bloco
        self.assertIn("painelBloco: 'master'", js)                # a omissão


class TestOAmbito(Base):
    """Quem entra e quem não entra: a regra da grelha, menos as runas."""

    def master(self, p, sid="AAA"):
        return p["sets"][sid]["master"]

    def test_as_runas_nunca_entram(self):
        con = self.montar()
        p = self.painel.payload(con)
        m = self.master(p)
        # AAA master: 3 Units + Gear + Legend = 5 (a runa base ficou de fora;
        # a sobrenumerada é outro bloco; a runa alt art está retirada).
        self.assertEqual(m["n"], 5)
        self.assertEqual(sum(l["n"] for l in m["domain"] if l["id"] == "fury"), 1)
        self.assertEqual(p["runes_out"]["AAA"], 1)
        self.assertEqual(p["runes_out"][self.painel.TODAS], 1)
        # Encher a runa não mexe em nada.
        from riftvault import collection
        collection.adjust(con, "aaa-006-100", 9, source="test")
        self.assertEqual(self.painel.payload(con)["sets"], p["sets"])
        con.close()

    def test_os_tres_niveis_do_master_de_AAA(self):
        con = self.montar()
        m = self.master(self.painel.payload(con))
        # Fury Unit 3/3, Body Unit 2/3, Mixed 1/3, Gear 0/3, Legend 1/1.
        self.assertEqual(m["levels"], [4, 3, 2])
        raridade = {l["id"]: l for l in m["rarity"]}
        self.assertEqual(raridade["common"]["levels"], [1, 1, 1])
        self.assertEqual(raridade["uncommon"]["levels"], [1, 1, 0])
        self.assertEqual(raridade["rare"]["levels"], [1, 0, 0])
        self.assertEqual(raridade["epic"]["levels"], [1, 1, 1])   # o Legend; o Gear a 0
        self.assertEqual(raridade["epic"]["n"], 2)
        dominio = {l["id"]: l for l in m["domain"]}
        self.assertEqual(dominio["multi"]["levels"], [1, 0, 0])
        self.assertEqual(dominio["none"]["n"], 1)
        self.assertEqual([l["id"] for l in m["domain"]], ["fury", "body", "mind", "none", "multi"])
        con.close()

    def test_as_escondidas_e_as_retiradas_seguem_a_regra_da_grelha(self):
        con = self.montar()
        p = self.painel.payload(con)
        ids = {bid for blocos in p["sets"].values() for bid in blocos}
        self.assertNotIn("token", ids)
        self.assertNotIn("signature", ids)
        self.assertNotIn(self.metrics.BLOCO_RUNA, ids)   # a runa alt art está retirada
        # A mesma pergunta que a grelha faz: o que o `set_payload` mostra é o
        # que o painel conta, impressão a impressão.
        grelha = self.metrics.set_payload(con, "AAA")
        na_grelha = {(pr["block"]) for g in grelha["groups"] for pr in g["printings"]
                     if pr["target"] > 0 and not g["rune"]}
        # O «Tudo» não é um bloco da grelha — é a soma dos que lá estão.
        self.assertEqual(na_grelha, set(p["sets"]["AAA"]) - {self.painel.TUDO})
        self.assertNotIn(self.painel.TUDO, {b["id"] for b in grelha["blocks"]})
        con.close()

    def test_o_bloco_e_o_da_grelha_e_o_alvo_1_coincide(self):
        con = self.montar()
        p = self.painel.payload(con)
        over = p["sets"]["AAA"]["overnumbered"]
        self.assertEqual(over["n"], 1)
        self.assertEqual(over["levels"], [1, 1, 1])      # tem 2, alvo 1
        promo = p["sets"]["ZZZ"]["special"]
        self.assertEqual(promo["levels"], [1, 1, 1])
        alt = p["sets"]["AAA"]["alt_art"]
        self.assertEqual(alt["levels"], [1, 0, 0])       # 1 de 3
        self.assertEqual([b["id"] for b in p["blocks"]],
                         ["master", "overnumbered", "alt_art", "special", "tudo"])
        self.assertEqual({b["id"]: b["target"] for b in p["blocks"]},
                         {"master": "playset", "overnumbered": "1 de cada",
                          "alt_art": "playset", "special": "1 de cada",
                          "tudo": "cada bloco com o seu alvo"})
        con.close()

    def test_a_raridade_e_a_da_base(self):
        """A alt art tem raridade impressa `showcase`; o quadro usa a da base."""
        con = self.montar()
        alt = self.painel.payload(con)["sets"]["AAA"]["alt_art"]
        self.assertEqual([l["id"] for l in alt["rarity"]], ["common"])
        con.close()

    def test_conta_o_que_esta_na_colecao_e_nao_o_que_vem_a_caminho(self):
        from riftvault import pending
        con = self.montar()
        antes = self.painel.payload(con)["sets"]
        pending.add(con, "aaa-004-100", 3)
        self.assertEqual(self.painel.payload(con)["sets"], antes)
        con.close()

    def test_a_ordem_dos_blocos_e_a_do_config(self):
        con = self.montar()
        # O `master_set` do config substitui o dos defaults inteiro (o `load`
        # junta só ao nível de cima), por isso vai completo.
        self.com_config({"sets": {"AAA": {"name": "Alfa", "order": 1},
                                  "ZZZ": {"name": "Zeta", "order": 2}},
                         "master_set": {**self.v.config.DEFAULTS["master_set"],
                                        "ordem_dos_blocos": ["master", "a", "promo", "overnumbered"]}})
        p = self.painel.payload(con)
        # A ordem do config manda nos blocos; o «Tudo» fica sempre no fim.
        self.assertEqual([b["id"] for b in p["blocks"]],
                         ["master", "alt_art", "special", "overnumbered", "tudo"])
        for sid in ("AAA", "ZZZ", self.painel.TODAS):
            self.assertEqual(list(p["sets"][sid])[-1], self.painel.TUDO, sid)
        con.close()


class TestNosPayloads(Base):
    def test_a_edicao_leva_o_painel_e_o_index_o_de_todas(self):
        con = self.montar()
        p = self.painel.payload(con)
        s = self.metrics.set_payload(con, "AAA")
        self.assertEqual(s["progress"]["painel"]["blocks"], p["sets"]["AAA"])
        self.assertEqual(s["progress"]["painel"]["runes_out"], 1)
        idx = self.metrics.index_payload(con)
        self.assertEqual(idx["painel"], p)
        self.assertIn(self.painel.TODAS, idx["painel"]["sets"])
        self.assertEqual(idx["painel"]["rarities"][0], ["common", "Comuns"])
        con.close()

    def test_os_grupos_levam_o_dominio_e_se_e_runa(self):
        con = self.montar()
        s = self.metrics.set_payload(con, "AAA")
        por_nome = {g["name"]: g for g in s["groups"]}
        self.assertEqual(por_nome["Mixed Unit"]["domain"], "multi")
        self.assertEqual(por_nome["Grey Gear"]["domain"], "none")
        self.assertTrue(por_nome["Fury Rune"]["rune"])
        self.assertFalse(por_nome["Fury Unit"]["rune"])
        con.close()

    def test_nao_escreve_nem_leva_euros(self):
        con = self.montar()
        antes = con.execute("SELECT COUNT(*) FROM ops").fetchone()[0]
        copias = con.execute("SELECT printing_id, qty FROM copies ORDER BY 1").fetchall()
        p = self.painel.payload(con)
        self.assertEqual(con.execute("SELECT COUNT(*) FROM ops").fetchone()[0], antes)
        self.assertEqual(con.execute("SELECT printing_id, qty FROM copies ORDER BY 1").fetchall(),
                         copias)
        texto = json.dumps(p, ensure_ascii=False)
        self.assertNotIn("cents", texto)
        self.assertNotIn("€", texto)
        con.close()

    def test_o_texto_da_consola(self):
        con = self.montar()
        p = self.painel.payload(con)
        t = self.painel.texto(p, self.metrics.sets_payload(con))
        self.assertIn("Master set — playset", t)
        self.assertIn("TODAS", t)
        self.assertIn("4/5", t)
        self.assertIn("runas ficam fora", t)
        con.close()

    def test_o_build_leva_o_painel(self):
        con = self.montar()
        con.close()
        from riftvault import build, decks, metrics, server
        for m in (metrics, decks, build, server):
            importlib.reload(m)
        out = self.v.root / "site"
        build.build(out, log=lambda *_: None)
        idx = json.loads((out / "api" / "index.json").read_text(encoding="utf-8"))
        s = json.loads((out / "api" / "set" / "AAA.json").read_text(encoding="utf-8"))
        self.assertEqual(idx["painel"]["sets"]["AAA"], s["progress"]["painel"]["blocks"])
        self.assertIn(self.painel.TODAS, idx["painel"]["sets"])


class TestOSite(Base):
    """O `app.js` e o `index.html` têm o painel, e o gémeo dá o mesmo."""

    def test_o_html_tem_o_painel_por_cima_da_grelha(self):
        html = (REPO / "riftvault" / "web" / "index.html").read_text(encoding="utf-8")
        self.assertLess(html.index('id="painel"'), html.index('id="progress"'))
        self.assertLess(html.index('id="painel"'), html.index('id="grid"'))
        # Os chips antigos dos níveis e das raridades saíram.
        self.assertNotIn('id="master-niveis"', html)
        self.assertNotIn('id="rarities"', html)

    def test_a_paleta_esta_em_variaveis_no_topo(self):
        """A paleta vive no `:root`, não espalhada pelas regras.

        Os VALORES mudaram no rebrand de 2026-09-24 (o painel era o único
        bloco do site ainda em azul, e a cor do projeto é o roxo #a77bff); o
        que este teste defende é a regra que não mudou — quem quiser mudar a
        cor muda num sítio só.
        """
        css = (REPO / "riftvault" / "web" / "style.css").read_text(encoding="utf-8")
        raiz = css[css.index(":root {"):css.index("}", css.index(":root {"))]
        for var, cor in (("--bg", "#07080d"), ("--card", "#12151f"), ("--ink", "#eef0f6"),
                         ("--muted", "#8c93a8"), ("--accent", "#a77bff"),
                         ("--h-card", "var(--card)"), ("--h-text", "var(--ink)"),
                         ("--lvl-1", "#5b43a0"), ("--lvl-2", "#8a63e0"), ("--lvl-3", "#c3a6ff")):
            self.assertIn(f"{var}: {cor}", raiz, var)
        # E as cores não aparecem espalhadas pelas regras.
        resto = css[css.index("}", css.index(":root {")):]
        for cor in ("#a77bff", "#5b43a0", "#8a63e0", "#c3a6ff", "#12151f"):
            self.assertNotIn(cor, resto, cor)
        self.assertIn("@media (max-width: 699px)", css)

    def test_o_app_js_desenha_e_deixa_as_runas_de_fora(self):
        js = APP_JS.read_text(encoding="utf-8")
        self.assertIn("function renderPainel", js)
        self.assertIn("function painelContar", js)
        self.assertIn("if (g.rune) { runas++; continue; }", js)
        self.assertIn("painelBloco", js)
        self.assertIn("const TODAS = 'all'", js)
        self.assertNotIn("function renderNiveis", js)

    def test_o_gemeo_em_javascript_da_o_mesmo(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("sem node")
        js = APP_JS.read_text(encoding="utf-8")
        m = re.search(r"/\* @painel-puro:inicio.*?\*/(.*?)/\* @painel-puro:fim \*/", js, re.S)
        self.assertIsNotNone(m, "o troço puro do painel tem de estar marcado no app.js")
        itens = [
            (3, 3, "common", "fury"), (3, 2, "common", "fury"), (3, 1, "rare", "body"),
            (3, 0, "rare", "body"), (1, 1, "epic", "mind"), (1, 0, "epic", "none"),
            (3, 2, "uncommon", "multi"), (12, 2, "common", "order"), (3, 3, "mythic", "void"),
            (3, 1, "showcase", "calm"), (3, 1, "common", "chaos"),
        ]
        esperado = self.painel.contar(itens)
        harness = m.group(1) + """
const entrada = JSON.parse(require('node:fs').readFileSync(0, 'utf8'));
const itens = entrada.itens.map(([alvo, tem, rarity, domain]) => ({alvo, tem, rarity, domain}));
process.stdout.write(JSON.stringify(painelContar(itens, entrada.cat)));
"""
        cat = {"rarities": [list(x) for x in self.painel.RARIDADES],
               "domains": [list(x) for x in self.painel.DOMINIOS]}
        # `encoding="utf-8"` explícito (24/09/2026): o node escreve UTF-8, e sem
        # isto o Python decodia-o na codificação local da consola do Windows —
        # «Épicas» chegava «Ã‰picas» e o gémeo parecia discordar do original.
        r = subprocess.run([node, "-e", harness], input=json.dumps({"itens": itens, "cat": cat}),
                           capture_output=True, text=True, encoding="utf-8", timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), esperado)


if __name__ == "__main__":
    unittest.main()

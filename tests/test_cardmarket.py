"""As listas para o Cardmarket, e o que fica fora das listas de compra.

Três decisões do André a 2026-09-08:

  1. *"No 'a subir', estás a pôr uma carta signed — não quero."*
  2. *"No riftvault, 'a subir', tira também os showcases."*
  3. *"No final dá-me uma lista para o Cardmarket para eu conseguir comprar
     as coisas."*

O que se testa aqui: que as signatures e os showcases saem das listas mas NÃO
da percentagem de master set, que os dois são critérios diferentes (variante
contra raridade), que a quantidade de cada linha é o que falta (não o alvo nem
o que ele tem), o formato das duas variantes de linha, e o CSV com cabeçalho.
"""

from __future__ import annotations

import csv
import importlib
import io
import json
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.fixture import Vault

HOJE = date(2026, 9, 8)


def dia(n: int) -> str:
    return (HOJE - timedelta(days=n)).isoformat()


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

    # -- utilitários -------------------------------------------------------

    def preco(self, con, pid, cents, foil=0):
        con.execute("INSERT INTO catalog.price_latest (printing_id, price_cents, "
                    "from_foil) VALUES (?,?,?)", (pid, cents, foil))

    def historico(self, con, pid, pontos):
        for d, c in pontos.items():
            con.execute("INSERT INTO prices.price_history (printing_id, day, "
                        "price_cents) VALUES (?,?,?)", (pid, d, c))

    def mercado(self, con, pid, nome, edicao="Unleashed", blueprint=1):
        """O par no CardTrader — é daqui que sai o nome que o Cardmarket usa."""
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


class TestSignaturesFora(Base):
    """A signature sai das listas de compra — e, desde 2026-09-09, da coleção.

    A ordem dele de 2026-09-08 era só sobre as listas ("estás a pôr uma carta
    signed — não quero"); a de 2026-09-09 tirou-as da Coleção inteira, e por
    isso elas já nem chegam ao `excluir()`. As duas decisões vivem em sítios
    diferentes de propósito: se um dia voltarem à coleção, continuam a não ser
    para comprar.
    """

    def montar(self):
        con = self.v.connect()
        # Mesmo número de coleção: a base e a signature são o mesmo grupo, que
        # é como o Cardmarket as numera (V.1 e V.2).
        self.v.add_printing(con, "tst-002-100", "TST", 2, "Aphelios")
        self.v.add_printing(con, "tst-002-star-100", "TST", 2, "Aphelios",
                            variant="star", kind="signature", rarity="showcase")
        self.v.rebuild(con)
        for pid, p0, p1 in (("tst-002-100", 1000, 2000),
                            ("tst-002-star-100", 50000, 200000)):
            self.historico(con, pid, {dia(40): p0, dia(2): p1})
            self.preco(con, pid, p1)
        return con

    def test_a_signature_nao_entra_no_a_subir(self):
        con = self.montar()
        p = self.a_subir.calcular(con, hoje=HOJE)
        self.assertEqual([i["printing_id"] for i in p["items"]], ["tst-002-100"])
        # Já não sai pela exclusão: sai antes, com a coleção. O âmbito da página
        # é a coleção, e a signature deixou de estar lá.
        self.assertEqual(p["scope"]["printings"], 1)
        self.assertEqual(p["scope"]["excluded"], 0)
        con.close()

    def test_a_signature_nao_entra_na_lista_do_master_set(self):
        con = self.montar()
        m = self.a_subir.master_faltas(con)
        codigos = [x["printing_id"] for s in m["sets"] for x in s["items"]]
        self.assertEqual(codigos, ["tst-002-100"])
        self.assertEqual(m["scope"]["excluded"], 0)
        con.close()

    def test_a_signature_saiu_tambem_da_percentagem_de_set(self):
        """2026-09-09: *"das coleções tira as signatures"*. Sai das duas."""
        con = self.montar()
        self.assertFalse(self.metrics.e_master(
            {"variant_kind": "signature", "is_token": 0}))
        # O ALVO não mexeu — o tile continua a dizer-lhe 0/1 no bloco de fora.
        alvo = self.metrics.master_target("tst-002-star-100", "signature", "Unit", False)
        self.assertEqual(alvo, 1)
        prog = self.metrics.set_payload(con, "TST")["progress"]["master"]
        self.assertEqual(prog["total"], 1)      # só a base
        con.close()

    def test_lista_vazia_no_config_traz_a_signature_de_volta(self):
        """O nome ANTIGO da lista, e a valer o que valia.

        `excluir_tipos: []` é um ficheiro escrito antes de 2026-09-08: não
        excluía raridade nenhuma, por isso a migração não lhe pode acrescentar
        os showcases — e a signature, que é de raridade showcase, volta.

        O `master_set.fora` vai sem o `*` de propósito: este teste é sobre a
        migração do nome antigo da exclusão, não sobre a decisão de 2026-09-09.
        """
        self.com_config({"a_subir": {"excluir_tipos": []},
                         "master_set": {"fora": ["-T"]}})
        con = self.montar()
        p = self.a_subir.calcular(con, hoje=HOJE)
        self.assertEqual(sorted(i["printing_id"] for i in p["items"]),
                         ["tst-002-100", "tst-002-star-100"])
        self.assertEqual(p["scope"]["excluded"], 0)
        con.close()


class TestShowcasesFora(Base):
    """André, 2026-09-08: *"no 'a subir', tira também os showcases"*.

    O showcase é uma RARIDADE, não uma variante: a `tst-232-100` é a
    reimpressão showcase com número de coleção próprio (a `SFD-232/221` do
    catálogo real), `variant_kind = base`. Uma lista de variantes não lhe tocava
    — é por isso que o `excluir` tem dois campos.
    """

    def montar(self):
        con = self.v.connect()
        self.v.add_printing(con, "tst-002-100", "TST", 2, "Sett, Brawler")
        # A reimpressão showcase: código de carta normal, raridade showcase.
        self.v.add_printing(con, "tst-232-100", "TST", 232, "Sett, Brawler",
                            rarity="showcase")
        self.v.add_printing(con, "tst-232-star-100", "TST", 232, "Sett, Brawler",
                            variant="star", kind="signature", rarity="showcase")
        self.v.rebuild(con)
        for pid, p0, p1 in (("tst-002-100", 1000, 2000),
                            ("tst-232-100", 4000, 8000),
                            ("tst-232-star-100", 50000, 200000)):
            self.historico(con, pid, {dia(40): p0, dia(2): p1})
            self.preco(con, pid, p1)
        return con

    def test_a_reimpressao_showcase_nao_entra_no_a_subir(self):
        con = self.montar()
        p = self.a_subir.calcular(con, hoje=HOJE)
        self.assertEqual([i["printing_id"] for i in p["items"]], ["tst-002-100"])
        con.close()

    def test_a_reimpressao_showcase_nao_entra_na_lista_do_master_set(self):
        con = self.montar()
        m = self.a_subir.master_faltas(con)
        codigos = [x["printing_id"] for s in m["sets"] for x in s["items"]]
        self.assertEqual(codigos, ["tst-002-100"])
        con.close()

    def test_a_pagina_diz_quantas_tirou_por_criterio(self):
        """Hoje só sai a reimpressão showcase: a signature saiu com a coleção.

        Os dois critérios continuam configurados, e o resumo conta o que saiu
        MESMO — é o que a página escreve, e desde 2026-09-09 diz «1 showcase»
        em vez de «1 signature + 1 showcase».
        """
        con = self.montar()
        fora = self.a_subir.calcular(con, hoje=HOJE)["scope"]
        self.assertEqual(fora["excluded"], 1)
        self.assertEqual(fora["excluded_by"], [{"criterio": "showcase", "n": 1}])
        self.assertEqual(sum(c["n"] for c in fora["excluded_by"]), fora["excluded"])
        self.assertEqual(fora["excluded_kinds"], ["signature"])
        self.assertEqual(fora["excluded_rarities"], ["showcase"])
        con.close()

    def test_com_as_signatures_de_volta_conta_se_uma_vez_por_criterio(self):
        """A signature é das duas coisas — conta-se uma vez, pelo tipo.

        Sem isto a soma dos critérios dava 3 numa lista que tirou 2 impressões.
        Fixa-se com o `master_set.fora` sem o `*`, que é o mundo em que a
        signature ainda chega às exclusões.
        """
        self.com_config({"master_set": {"fora": ["-T"]}})
        con = self.montar()
        fora = self.a_subir.calcular(con, hoje=HOJE)["scope"]
        self.assertEqual(fora["excluded"], 2)
        self.assertEqual(fora["excluded_by"], [{"criterio": "signature", "n": 1},
                                               {"criterio": "showcase", "n": 1}])
        self.assertEqual(sum(c["n"] for c in fora["excluded_by"]), fora["excluded"])
        con.close()

    def test_o_showcase_continua_a_contar_para_a_percentagem_de_set(self):
        """O filtro é da página. A barra da Coleção não pode mexer.

        A signature já não está no denominador, mas por outra decisão (a de
        2026-09-09) e por outro caminho — o `master_set.fora`, não este filtro.
        """
        con = self.montar()
        prog = self.metrics.set_payload(con, "TST")["progress"]["master"]
        self.assertEqual(prog["total"], 2)   # base + showcase
        self.assertEqual(self.a_subir.calcular(con, hoje=HOJE)["scope"]["printings"], 1)
        con.close()

    def test_o_nome_antigo_da_lista_nao_tira_os_showcases(self):
        """Migração: `excluir_tipos` vale o que valia — só tipos."""
        self.com_config({"a_subir": {"excluir_tipos": ["signature"]}})
        self.assertEqual(self.config.load()["a_subir"]["excluir"],
                         {"tipos": ["signature"], "raridades": []})
        con = self.montar()
        p = self.a_subir.calcular(con, hoje=HOJE)
        self.assertEqual(sorted(i["printing_id"] for i in p["items"]),
                         ["tst-002-100", "tst-232-100"])
        con.close()

    def test_o_nome_novo_ganha_ao_antigo(self):
        """Um ficheiro com os dois usa o novo — é o que lá está escrito hoje."""
        self.com_config({"a_subir": {"excluir_tipos": [],
                                     "excluir": {"raridades": ["showcase"]}}})
        con = self.montar()
        p = self.a_subir.calcular(con, hoje=HOJE)
        # `tipos` não foi escrito: mantém o default (signature), como os pesos
        # da urgência — mexer num campo não apaga o outro.
        self.assertEqual([i["printing_id"] for i in p["items"]], ["tst-002-100"])
        con.close()

    def test_listas_vazias_trazem_tudo_de_volta(self):
        # Com o `*` fora da lista da coleção, senão a signature não voltava —
        # são dois filtros, e este teste é sobre o das listas de compra.
        self.com_config({"a_subir": {"excluir": {"tipos": [], "raridades": []}},
                         "master_set": {"fora": ["-T"]}})
        con = self.montar()
        p = self.a_subir.calcular(con, hoje=HOJE)
        self.assertEqual(len(p["items"]), 3)
        self.assertEqual(p["scope"]["excluded"], 0)
        self.assertEqual(p["scope"]["excluded_by"], [])
        con.close()


class TestLinhas(Base):
    """O formato: `N Nome (V.n) (Edição)` e `N Nome [CÓDIGO]`."""

    def montar(self):
        con = self.v.connect()
        self.v.add_printing(con, "tst-002-100", "TST", 2, "Loose Cannon")
        self.v.add_printing(con, "tst-002a-100", "TST", 2, "Loose Cannon",
                            variant="a", kind="alt_art", rarity="showcase")
        self.v.rebuild(con)
        # O mercado escreve os nomes de outra maneira — é esse que tem de sair.
        self.mercado(con, "tst-002-100", "Jinx - Loose Cannon", blueprint=11)
        self.mercado(con, "tst-002a-100", "Jinx - Loose Cannon", blueprint=12)
        self.preco(con, "tst-002-100", 250)
        return con

    def test_quantidade_nome_versao_e_edicao(self):
        con = self.montar()
        m = self.a_subir.master_faltas(con)
        it = next(x for s in m["sets"] for x in s["items"]
                  if x["printing_id"] == "tst-002-100")
        # Duas impressões partilham o número de coleção, logo há V.1 e V.2.
        self.assertEqual(self.cardmarket.linha(it),
                         "3 Jinx - Loose Cannon (V.1) (Unleashed)")
        con.close()

    def test_com_codigo(self):
        con = self.montar()
        m = self.a_subir.master_faltas(con)
        it = next(x for s in m["sets"] for x in s["items"]
                  if x["printing_id"] == "tst-002-100")
        # Os [ ] não são sintaxe do Cardmarket: é para desambiguar à mão.
        self.assertEqual(self.cardmarket.linha(it, com_codigo=True),
                         "3 Jinx - Loose Cannon [TST-002]")
        con.close()

    def test_sem_par_no_mercado_usa_o_nome_do_catalogo(self):
        """Sem `cardtrader_map` não há nome de mercado nem versão — e não se
        inventa nenhum dos dois."""
        con = self.v.connect()
        self.v.add_printing(con, "tst-009-100", "TST", 9, "Sem Par")
        self.v.rebuild(con)
        m = self.a_subir.master_faltas(con)
        it = m["sets"][0]["items"][0]
        self.assertEqual(self.cardmarket.linha(it), "3 Sem Par")
        con.close()

    def test_a_quantidade_e_o_que_falta_nao_o_alvo(self):
        from riftvault import collection, pending
        con = self.montar()
        collection.adjust(con, "tst-002-100", 1, source="test")
        pending.add(con, "tst-002-100", 1)      # a caminho conta como tido

        m = self.a_subir.master_faltas(con)
        it = next(x for s in m["sets"] for x in s["items"]
                  if x["printing_id"] == "tst-002-100")
        # `have` é o que conta como tido — a cópia na caixa mais a que vem a
        # caminho — como em toda a secção Faltas.
        self.assertEqual((it["have"], it["target"], it["missing"]), (2, 3, 1))
        self.assertTrue(self.cardmarket.linha(it).startswith("1 "))
        con.close()

    def test_o_total_nao_vai_no_texto(self):
        con = self.montar()
        m = self.a_subir.master_faltas(con)
        itens = [x for s in m["sets"] for x in s["items"]]
        res = self.cardmarket.gerar(itens)
        self.assertEqual(res["lines"], len(res["text"].splitlines()))
        self.assertNotIn("€", res["text"])
        # O total vem à parte, para quem mostra o pôr fora da caixa de texto.
        self.assertEqual(res["cents"], sum(x["total"] for x in itens))
        con.close()

    def test_as_so_de_foil_saem_assinaladas(self):
        con = self.montar()
        con.execute("UPDATE catalog.price_latest SET from_foil = 1 "
                    "WHERE printing_id = 'tst-002-100'")
        m = self.a_subir.master_faltas(con)
        itens = [x for s in m["sets"] for x in s["items"]]
        res = self.cardmarket.gerar(itens)
        # O foil não se marca na linha — é um filtro por entrada, na interface
        # deles. Vem à parte para ele saber onde o ligar.
        self.assertEqual(res["foil"], ["3 Jinx - Loose Cannon (V.1) (Unleashed)"])
        con.close()


class TestCSV(Base):
    def test_cabecalho_e_colunas(self):
        con = self.v.connect()
        self.v.add_printing(con, "tst-002-100", "TST", 2, "Bloodharbor Ripper",
                            rarity="epic")
        self.v.rebuild(con)
        self.mercado(con, "tst-002-100", "Bloodharbor Ripper", edicao="Unleashed")
        self.historico(con, "tst-002-100", {dia(40): 1000, dia(2): 2000})
        self.preco(con, "tst-002-100", 2000)

        itens = self.a_subir.calcular(con, hoje=HOJE)["items"]
        linhas = list(csv.reader(io.StringIO(self.cardmarket.csv_texto(itens))))
        self.assertEqual(linhas[0], self.cardmarket.CABECALHO_CSV)
        self.assertEqual(linhas[1], ["3", "Bloodharbor Ripper", "TST-002",
                                     "Unleashed", "epic", "20.00", "100.0", "60.00"])
        con.close()

    def test_a_lista_do_master_set_nao_tem_delta(self):
        """Não é sobre preço a subir: a coluna fica vazia, não a zero."""
        con = self.v.connect()
        self.v.add_printing(con, "tst-002-100", "TST", 2, "Sem Delta")
        self.v.rebuild(con)
        self.preco(con, "tst-002-100", 500)

        itens = [x for s in self.a_subir.master_faltas(con)["sets"] for x in s["items"]]
        linhas = list(csv.reader(io.StringIO(self.cardmarket.csv_texto(itens))))
        self.assertEqual(linhas[1][6], "")
        con.close()


class TestListaDoMasterSet(Base):
    def test_ordena_por_edicao_e_numero(self):
        """Ordem do binder, não do preço (pedido do André)."""
        self.com_config({"sets": {"AAA": {"order": 1}, "ZZZ": {"order": 2}}})
        con = self.v.connect()
        self.v.add_printing(con, "zzz-001-100", "ZZZ", 1, "Zeta")
        self.v.add_printing(con, "aaa-010-100", "AAA", 10, "Alfa dez")
        self.v.add_printing(con, "aaa-002-100", "AAA", 2, "Alfa dois")
        self.v.rebuild(con)
        # Preços ao contrário da ordem pedida, para o teste não passar por acaso.
        self.preco(con, "zzz-001-100", 9000)
        self.preco(con, "aaa-010-100", 100)
        self.preco(con, "aaa-002-100", 50)

        m = self.a_subir.master_faltas(con)
        self.assertEqual([s["set"] for s in m["sets"]], ["AAA", "ZZZ"])
        self.assertEqual([x["cn"] for x in m["sets"][0]["items"]], [2, 10])
        con.close()

    def test_o_que_ja_esta_completo_nao_aparece(self):
        from riftvault import collection
        con = self.v.connect()
        self.v.add_printing(con, "tst-001-100", "TST", 1, "Feita")
        self.v.add_printing(con, "tst-002-100", "TST", 2, "Por fazer")
        self.v.rebuild(con)
        collection.adjust(con, "tst-001-100", 3, source="test")

        m = self.a_subir.master_faltas(con)
        self.assertEqual([x["name"] for s in m["sets"] for x in s["items"]],
                         ["Por fazer"])
        self.assertEqual(m["copies"], 3)
        con.close()

    def test_conta_as_que_nao_tem_preco_a_parte(self):
        """Sem oferta no CardTrader entram na lista, mas não no total."""
        con = self.v.connect()
        self.v.add_printing(con, "tst-001-100", "TST", 1, "Com preço")
        self.v.add_printing(con, "tst-002-100", "TST", 2, "Sem preço")
        self.v.rebuild(con)
        self.preco(con, "tst-001-100", 100)

        m = self.a_subir.master_faltas(con)
        self.assertEqual(m["no_price"], 1)
        self.assertEqual(m["cents"], 300)
        con.close()


if __name__ == "__main__":
    unittest.main()

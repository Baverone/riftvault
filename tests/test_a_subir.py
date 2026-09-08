"""A aba "A subir": âmbito do master set, carência, Δ% e as duas ordenações."""

from __future__ import annotations

import importlib
import json
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.fixture import Vault

HOJE = date(2026, 9, 8)


def dia(n: int) -> str:
    """A data de há `n` dias, no formato do `price_history`."""
    return (HOJE - timedelta(days=n)).isoformat()


class Base(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.close)
        from riftvault import a_subir, config
        importlib.reload(a_subir)
        self.a_subir = a_subir
        self.config = config

    # -- utilitários ------------------------------------------------------

    def preco(self, con, pid: str, cents: int):
        con.execute("INSERT INTO catalog.price_latest (printing_id, price_cents) "
                    "VALUES (?,?)", (pid, cents))

    def historico(self, con, pid: str, pontos: dict[str, int]):
        for d, c in pontos.items():
            con.execute("INSERT INTO prices.price_history (printing_id, day, price_cents) "
                        "VALUES (?,?,?)", (pid, d, c))

    def com_config(self, extra: dict):
        """Corre o resto do teste com um `riftvault_config.json` à medida.

        O `config` guarda o caminho numa constante de módulo lida na
        importação, por isso não chega pôr a variável de ambiente.
        """
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


class TestAmbito(Base):
    """O "masterset" é a métrica 2, não uma edição."""

    def test_alt_art_fica_de_fora_e_a_base_e_o_token_ficam(self):
        con = self.v.connect()
        self.v.add_printing(con, "tst-001-100", "TST", 1, "Defy")
        self.v.add_printing(con, "tst-001a-100", "TST", 1, "Defy",
                            variant="a", kind="alt_art")
        self.v.add_printing(con, "tst-t01-100", "TST", 90, "Sprite",
                            variant="t01", kind="token")
        self.v.rebuild(con)

        escopo = self.a_subir.masterset(con)
        self.assertIn("tst-001-100", escopo)
        self.assertIn("tst-t01-100", escopo)
        # `master_ignorar_variantes: ["alt_art"]` — as artes alternativas não
        # contam para a percentagem de set completo, logo também não se seguem.
        self.assertNotIn("tst-001a-100", escopo)
        # O alvo é o do master set: uma Unit base segue o playset do tipo.
        self.assertEqual(escopo["tst-001-100"]["target"], 3)
        con.close()


class TestNaoTenho(Base):
    """Enquanto faltarem cópias para o alvo do master set, segue-se."""

    def montar(self):
        con = self.v.connect()
        self.v.add_printing(con, "tst-001-100", "TST", 1, "Defy")
        self.v.add_printing(con, "tst-002-100", "TST", 2, "Brutalizer")
        self.v.rebuild(con)
        return con

    def test_completa_sai_parcial_fica(self):
        from riftvault import collection
        con = self.montar()
        collection.adjust(con, "tst-001-100", 3, source="test")   # completa
        collection.adjust(con, "tst-002-100", 1, source="test")   # 1 de 3

        falta = self.a_subir.em_falta(con, self.a_subir.masterset(con))
        self.assertNotIn("tst-001-100", falta)
        self.assertEqual(falta["tst-002-100"]["missing"], 2)
        self.assertEqual(falta["tst-002-100"]["have"], 1)
        con.close()

    def test_regra_nenhuma_so_conta_as_que_estao_a_zero(self):
        from riftvault import collection
        con = self.montar()
        collection.adjust(con, "tst-002-100", 1, source="test")

        falta = self.a_subir.em_falta(con, self.a_subir.masterset(con), regra="nenhuma")
        self.assertNotIn("tst-002-100", falta)
        self.assertIn("tst-001-100", falta)
        con.close()

    def test_o_que_vem_a_caminho_conta_como_tido(self):
        from riftvault import pending
        con = self.montar()
        pending.add(con, "tst-001-100", 3)

        falta = self.a_subir.em_falta(con, self.a_subir.masterset(con))
        # Já está comprada: não faz sentido continuar a vigiar-lhe o preço.
        self.assertNotIn("tst-001-100", falta)
        con.close()


class TestVariacao(Base):
    def montar(self):
        con = self.v.connect()
        self.v.add_printing(con, "tst-001-100", "TST", 1, "Defy")
        self.v.rebuild(con)
        return con

    def test_usa_o_preco_em_vigor_no_inicio_da_janela(self):
        """O ponto de comparação pode ser ANTERIOR à janela.

        O `price_history` só grava quando o preço muda. Uma carta que valia
        1,00 € há 90 dias e subiu para 2,00 € há 3 dias tem um único registo
        dentro da janela — comparar com ele dava 0%. O que interessa é o preço
        que estava em vigor no início da janela.
        """
        con = self.montar()
        self.historico(con, "tst-001-100", {dia(90): 100, dia(3): 200})
        self.preco(con, "tst-001-100", 200)

        p = self.a_subir.calcular(con, hoje=HOJE)
        it = p["items"][0]
        self.assertEqual(it["from_cents"], 100)
        self.assertEqual(it["to_cents"], 200)
        self.assertEqual(it["pct"], 100.0)
        self.assertTrue(it["full_window"])
        self.assertEqual(it["since"], dia(90))
        con.close()

    def test_sem_historico_que_cubra_a_janela_marca_desde(self):
        con = self.montar()
        self.historico(con, "tst-001-100", {dia(5): 100, dia(1): 150})
        self.preco(con, "tst-001-100", 150)

        p = self.a_subir.calcular(con, hoje=HOJE)
        it = p["items"][0]
        self.assertFalse(it["full_window"])
        self.assertEqual(it["since"], dia(5))     # o ponto mais antigo que há
        self.assertEqual(it["pct"], 50.0)
        con.close()

    def test_coluna_de_7_dias(self):
        con = self.montar()
        self.historico(con, "tst-001-100", {dia(40): 100, dia(9): 180, dia(2): 200})
        self.preco(con, "tst-001-100", 200)

        it = self.a_subir.calcular(con, hoje=HOJE)["items"][0]
        self.assertEqual(it["pct"], 100.0)          # 30 dias: 100 -> 200
        # Há 7 dias já valia 180 (o registo de há 9 dias ainda estava em vigor).
        self.assertEqual(it["pct_short"], 11.1)
        self.assertTrue(it["short_full"])
        con.close()

    def test_abaixo_do_limiar_nao_aparece(self):
        con = self.montar()
        self.historico(con, "tst-001-100", {dia(40): 100, dia(2): 105})
        self.preco(con, "tst-001-100", 105)

        p = self.a_subir.calcular(con, hoje=HOJE)
        self.assertTrue(p["ready"])        # há com que comparar...
        self.assertEqual(p["items"], [])   # ...mas 5% não chega aos 10%
        con.close()

    def test_sem_historico_nenhum_nao_inventa_tendencia(self):
        con = self.montar()
        self.preco(con, "tst-001-100", 500)

        p = self.a_subir.calcular(con, hoje=HOJE)
        self.assertFalse(p["ready"])
        self.assertEqual(p["items"], [])
        self.assertEqual(p["tracked"], 1)
        con.close()


class TestOrdemEUrgencia(Base):
    def montar(self):
        con = self.v.connect()
        # Uma que dispara mas vale pouco; outra cara que sobe menos.
        self.v.add_printing(con, "tst-001-100", "TST", 1, "Barata")
        self.v.add_printing(con, "tst-002-100", "TST", 2, "Cara")
        self.v.rebuild(con)
        self.historico(con, "tst-001-100", {dia(40): 100, dia(2): 300})   # +200%
        self.preco(con, "tst-001-100", 300)
        self.historico(con, "tst-002-100", {dia(40): 5000, dia(2): 6000})  # +20%
        self.preco(con, "tst-002-100", 6000)
        return con

    def test_as_duas_ordens(self):
        con = self.montar()
        p = self.a_subir.calcular(con, hoje=HOJE)
        por_pct = sorted(p["items"], key=lambda i: i["rank_pct"])
        por_valor = sorted(p["items"], key=lambda i: i["rank_valor"])
        self.assertEqual([i["name"] for i in por_pct], ["Barata", "Cara"])
        self.assertEqual([i["name"] for i in por_valor], ["Cara", "Barata"])
        # A lista chega já na ordem da aba por omissão (por %).
        self.assertEqual([i["name"] for i in p["items"]], ["Barata", "Cara"])
        con.close()

    def test_deixa_de_seguir_quando_a_carta_entra_na_colecao(self):
        from riftvault import collection
        con = self.montar()
        self.assertIn("Barata", [i["name"] for i in
                                 self.a_subir.calcular(con, hoje=HOJE)["items"]])

        collection.adjust(con, "tst-001-100", 3, source="test")   # playset feito
        p = self.a_subir.calcular(con, hoje=HOJE)
        self.assertNotIn("Barata", [i["name"] for i in p["items"]])
        self.assertEqual([i["name"] for i in p["items"]], ["Cara"])
        con.close()

    def test_urgencia_vem_desligada(self):
        con = self.montar()
        p = self.a_subir.calcular(con, hoje=HOJE)
        # Calculada na mesma — o que está desligado é a coluna.
        self.assertFalse(p["urgencia"])
        self.assertTrue(all("urgency" in i for i in p["items"]))
        con.close()

    def test_urgencia_liga_se_pelo_config(self):
        self.com_config({"a_subir": {"urgencia": True,
                                     "urgencia_pesos": {"janela": 1.0}}})
        con = self.montar()
        p = self.a_subir.calcular(con, hoje=HOJE)
        self.assertTrue(p["urgencia"])
        # Mexer num peso não apaga os outros dois.
        self.assertEqual(p["pesos"], {"janela": 1.0, "curto": 1.0,
                                      "preco_relativo": 10.0})
        con.close()


if __name__ == "__main__":
    unittest.main()

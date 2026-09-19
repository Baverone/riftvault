"""As runas em Alt Art saem de tudo (2026-09-17, à tarde).

Palavras do André, depois de ver que a regra «alt art da edição da Legend»
deixou as runas em alt art a zero:
    *"deixa as runas Alt Art, nao incluas em nada"*

A regra (`metrics.retirada`, `runas_especiais.retiradas`): uma runa em arte
alternativa DEIXA DE EXISTIR para o riftvault. Não aparece
  1. na Coleção (nem como tida, nem como falta) nem no «N impressões»;
  2. no denominador do master set nem em percentagem nenhuma;
  3. em wantlist nenhuma;
  4. no separador Faltas (em nenhum dos blocos);
  5. no «A mais» (nem como excedente, nem escondida);
  6. no valor da coleção, nos totais nem no playset jogável;
  7. nos decks — não a pedem, não se servem dela, não a compram, não a
     encomendam, não a propõem: jogam a runa BASE. E no Pimp.
(Havia um ponto sobre a tabela de preços, apagada com o separador dela a
2026-09-19.)
O que NÃO muda: a runa base da sequência continua a 3; as artes alternativas
das cartas que não são runas continuam a 1 na Coleção e a servir os decks.
As cópias não saem do `copies` — ninguém as lê.

Tudo contra pastas temporárias (`tests.fixture.Vault`) e um config PRÓPRIO: o
`data/` e o `riftvault_config.json` a sério nunca são tocados.
"""

from __future__ import annotations

import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

CONFIG = Path(tempfile.gettempdir()) / "riftvault-runas-alt-fora.json"


def escrever_config(retiradas=("a",), tipos=("Rune",),
                    papeis=("legend", "champion"),
                    contar_runas=False, sem_runas=True) -> None:
    # `contar_runas`/`sem_runas` são os defaults de 2026-09-17 à noite (as
    # runas não se contam nos decks nem aparecem no «A mais»); os testes do
    # MECANISMO da retirada nos decks ligam a contagem para o poderem ver.
    CONFIG.write_text(json.dumps({
        "master_set": {"fora_da_percentagem": ["a", "overnumbered", "promo"],
                       "escondidas": ["-T", "*", "-R"],
                       # As alt arts a playset desde 2026-09-18 (o `a` saiu);
                       # as promos a 1 desde 2026-09-19 (o `promo` voltou).
                       "um_de_cada": ["overnumbered", "promo"]},
        "master_targets_by_type": {"Rune": 3},
        "decks": {"so_normais_excepto": list(papeis),
                  "versoes_especiais": ["a", "overnumbered", "promo"],
                  "contar_runas": contar_runas},
        "runas_especiais": {"tipos": list(tipos), "excepto": ["base"],
                            "retiradas": list(retiradas)},
        "listas_de_compra": {"so_master_set": True},
        "a_mais": {"sem_edicoes": [], "sem_runas": sem_runas},
    }), encoding="utf-8")
    os.environ["RIFTVAULT_CONFIG"] = str(CONFIG)


escrever_config()

from tests.fixture import Vault  # noqa: E402

# Legend da edição AAA: 4 Calm Rune (com alt art em AAA), 4 Order Rune (sem
# alt art), 3 Defy (Unit, com alt art).
AZIR = ("Legend:\n1 Emperor of the Sands\n\nMainDeck:\n3 Defy\n\n"
        "Rune Pool:\n4 Calm Rune\n4 Order Rune\n")

PRECOS = {"aaa-001-100": 10, "aaa-001a-100": 500, "aaa-002-100": 10,
          "aaa-003-100": 1000, "aaa-004-100": 150, "aaa-004a-100": 2000}

RUNA_ALT = "aaa-001a-100"


class Base(unittest.TestCase):
    def setUp(self):
        escrever_config()
        self.addCleanup(lambda: os.environ.pop("RIFTVAULT_CONFIG", None))
        self.v = Vault()
        self.addCleanup(self.v.close)
        from riftvault import (a_mais, a_subir, collection, decks, faltas,
                               faltas_edicao, locais, metrics, pending, prices)
        for m in (metrics, locais, decks, pending, faltas, a_subir, prices,
                  collection, faltas_edicao, a_mais):
            importlib.reload(m)
        self.metrics, self.decks, self.faltas = metrics, decks, faltas
        self.a_subir, self.pending, self.locais = a_subir, pending, locais
        self.prices, self.collection = prices, collection
        self.faltas_edicao, self.a_mais = faltas_edicao, a_mais

    def recarregar(self):
        from riftvault import config
        config.load.cache_clear()

    def catalogo(self, copias: dict[str, int] | None = None, decks: dict | None = None):
        from riftvault import collection
        con = self.v.connect()
        add = self.v.add_printing
        add(con, "aaa-001-100", "AAA", 1, "Calm Rune", card_type="Rune", size=100)
        add(con, RUNA_ALT, "AAA", 1, "Calm Rune", card_type="Rune", variant="a",
            kind="alt_art", rarity="showcase", base_rarity="common", size=100)
        add(con, "aaa-002-100", "AAA", 2, "Order Rune", card_type="Rune", size=100)
        add(con, "aaa-003-100", "AAA", 3, "Emperor of the Sands", card_type="Legend", size=100)
        add(con, "aaa-004-100", "AAA", 4, "Defy", size=100)
        add(con, "aaa-004a-100", "AAA", 4, "Defy", variant="a", kind="alt_art",
            rarity="showcase", base_rarity="common", size=100)
        self.v.rebuild(con)
        for pid, cents in PRECOS.items():
            con.execute("INSERT INTO catalog.price_latest (printing_id, price_cents) "
                        "VALUES (?,?)", (pid, cents))
        for pid, n in (copias or {}).items():
            collection.adjust(con, pid, n, source="test")
        for slug, texto in (decks if decks is not None else {"azir": AZIR}).items():
            self.v.write_deck(slug, texto)
        self.decks.import_all(con, log=lambda *_: None)
        return con

    def idx(self, con) -> dict:
        return {d["slug"]: d for d in self.decks.decks_index(con)}

    def falta_de(self, con, slug: str) -> dict[str, int]:
        return self.decks.allocate(con)[self.idx(con)[slug]["id"]]["missing"]

    def tiles(self, con, set_id: str = "AAA") -> dict[str, dict]:
        p = self.metrics.set_payload(con, set_id)
        return {pr["id"]: pr for g in p["groups"] for pr in g["printings"]}


# As 6 cópias do caso real: ele tem 6 `OGN-042a` (Calm Rune em alt art).
SEIS = {RUNA_ALT: 6}


class TestAColecao(Base):
    """1 e 2: não aparece na grelha, no separador, nem conta."""

    def test_e_retirada_e_escondida(self):
        con = self.catalogo()
        r = con.execute("SELECT * FROM catalog.printings WHERE printing_id = ?",
                        (RUNA_ALT,)).fetchone()
        self.assertTrue(self.metrics.retirada(r))
        self.assertTrue(self.metrics.escondida(r))
        self.assertFalse(self.metrics.e_colecao(r))
        self.assertFalse(self.metrics.e_master(r))
        # A base e a alt art de uma Unit não são retiradas.
        for pid in ("aaa-001-100", "aaa-004a-100"):
            r = con.execute("SELECT * FROM catalog.printings WHERE printing_id = ?",
                            (pid,)).fetchone()
            self.assertFalse(self.metrics.retirada(r), pid)
        con.close()

    def test_nao_esta_na_grelha_mesmo_com_seis_copias(self):
        con = self.catalogo(copias=SEIS)
        p = self.metrics.set_payload(con, "AAA")
        self.assertNotIn(RUNA_ALT, self.tiles(con))
        self.assertNotIn(self.metrics.BLOCO_RUNA, [b["id"] for b in p["blocks"]])
        # A base continua na sequência, a 3.
        self.assertEqual((self.tiles(con)["aaa-001-100"]["block"],
                          self.tiles(con)["aaa-001-100"]["target"]), ("master", 3))
        # E o separador não a conta: 5 impressões na página, não 6.
        self.assertEqual(self.metrics.sets_payload(con)[0]["n_printings"], 5)
        con.close()

    def test_o_denominador_e_os_niveis_nao_mexem(self):
        con = self.catalogo(copias={**SEIS, "aaa-001-100": 1})
        com = self.metrics.niveis_payload(con)["levels"]
        con.close()
        escrever_config(retiradas=())
        self.recarregar()
        self.v = Vault()
        self.addCleanup(self.v.close)
        con = self.catalogo(copias={**SEIS, "aaa-001-100": 1})
        sem = self.metrics.niveis_payload(con)["levels"]
        # Com a alt art da runa no bloco das runas especiais (sem retirar), a
        # runa aparece — mas a percentagem já não a contava: 5 impressões.
        self.assertIn(RUNA_ALT, self.tiles(con))
        con.close()
        self.assertEqual(com, sem)
        # A sequência: Calm Rune, Order Rune, a Legend e o Defy.
        self.assertEqual(com[-1]["total"], 4)


class TestAsListas(Base):
    """3 e 4: wantlist e Faltas."""

    def test_nao_entra_na_wantlist_nem_a_muda(self):
        con = self.catalogo(copias={"aaa-001-100": 1})
        w = self.a_subir.wantlist(con)
        self.assertNotIn(RUNA_ALT, [x["printing_id"] for x in w["items"]])
        # A base pede as 3: falta 2.
        self.assertEqual({x["printing_id"]: x["missing"] for x in w["items"]}
                         .get("aaa-001-100"), 2)
        con.close()

    def test_nao_entra_no_separador_faltas(self):
        con = self.catalogo()
        fe = json.dumps(self.faltas_edicao.payload(con), ensure_ascii=False)
        self.assertNotIn(RUNA_ALT, fe)
        # A alt art do Defy continua lá (bloco alt art, 1 em falta).
        self.assertIn("aaa-004a-100", fe)
        con.close()


class TestAMaisEOValor(Base):
    """5 e 6: nem no «A mais», nem no valor, nem no playset jogável."""

    def test_as_seis_copias_nao_sao_excedente_nem_escondidas(self):
        con = self.catalogo(copias=SEIS)
        am = self.a_mais.payload(con)
        self.assertNotIn(RUNA_ALT, json.dumps(am, ensure_ascii=False))
        self.assertEqual(am["totals"]["excedente"], {"cards": 0, "copies": 0})
        self.assertEqual((am["scope"]["hidden_cards"], am["scope"]["hidden_copies"]), (0, 0))
        # Uma retirada não é uma runa «fora do A mais»: não conta nem aí.
        self.assertEqual(am["scope"]["runas"]["excedente"], {"cards": 0, "copies": 0})
        con.close()
        # Sem retirar — e com as runas a contar nos decks e a aparecer no «A
        # mais», que deixaram de ser o default a 2026-09-17 à noite —, as
        # mesmas 6 cópias dão 2 a mais: o alvo da alt art é 1 e não sobe com o
        # que o Azir joga (2026-09-17, «voltar atrás»), mas desde a tarde desse
        # dia o Azir, sem Calm Rune base, TAPA as 4 do Rune Pool com as alt
        # arts — e uma cópia em uso não é a mais (`cópias − max(usadas, alvo)`
        # = 6 − 4). É o que aconteceria às runas dele se deixassem de estar
        # retiradas E voltassem a contar.
        escrever_config(retiradas=(), contar_runas=True, sem_runas=False)
        self.recarregar()
        self.v = Vault()
        self.addCleanup(self.v.close)
        con = self.catalogo(copias=SEIS)
        self.assertEqual(self.a_mais.payload(con)["totals"]["excedente"],
                         {"cards": 1, "copies": 2})
        self.assertNotIn("calm rune", self.falta_de(con, "azir"))
        con.close()

    def test_nao_conta_no_valor_nem_nos_totais(self):
        con = self.catalogo(copias={**SEIS, "aaa-004-100": 2})
        v = self.prices.collection_value(con)
        self.assertEqual((v["cents"], v["copias"]), (2 * 150, 2))
        self.assertEqual(self.prices.value_by_set(con), {"AAA": 300})
        self.assertEqual([x["public_code"] for x in self.prices.top_value(con)],
                         ["AAA-004/100"])
        self.assertEqual(self.collection.totals(con),
                         {"copies": 2, "printings": 1, "cards": 1})
        # E o valor da edição na Coleção diz o mesmo número.
        self.assertEqual(self.metrics.set_payload(con, "AAA")["progress"]["value"]["owned"],
                         300)
        con.close()

    def test_nao_conta_no_playset_jogavel(self):
        con = self.catalogo(copias={**SEIS, "aaa-001-100": 2})
        self.assertEqual(self.metrics.owned_by_card(con).get("calm rune"), 2)
        self.assertEqual(self.tiles(con)["aaa-001-100"]["qty"], 2)
        con.close()


class TestOsDecks(Base):
    """7: os decks jogam a runa base; a alt art não serve, não se compra, não
    se propõe, não se encomenda. E não está no Pimp.

    Desde 2026-09-17 à noite as runas NEM SE CONTAM nos decks
    (`decks.contar_runas: false`, `test_runas_fora_decks.py`) — a runa não
    falta nem se compra, seja base ou alt art. Estes testes são do MECANISMO
    da retirada nos decks e ligam a contagem (`contar_runas: true`) para o
    verem: se um dia as runas voltarem a contar, a retirada continua a valer.
    """

    def setUp(self):
        super().setUp()
        escrever_config(contar_runas=True)
        self.recarregar()

    def test_a_alt_art_nao_serve_e_a_base_serve(self):
        con = self.catalogo(copias=SEIS)
        self.assertEqual(self.falta_de(con, "azir").get("calm rune"), 4)
        self.assertEqual(self.decks.owned_by_card(con).get("calm rune"), None)
        con.close()
        self.v = Vault()
        self.addCleanup(self.v.close)
        con = self.catalogo(copias={"aaa-001-100": 4})
        self.assertNotIn("calm rune", self.falta_de(con, "azir"))
        con.close()

    def test_compra_se_a_base_e_encomenda_se_a_base(self):
        con = self.catalogo()
        azir = self.idx(con)["azir"]["id"]
        item = {x["card_key"]: x for d in self.decks.missing_by_set(con, azir)
                for x in d["items"]}["calm rune"]
        self.assertEqual((item["code"], item["qty"], item["price"], item["especial"]),
                         ("AAA-001/100", 4, 10, False))
        self.assertEqual(self.pending.impressao_para_encomendar(
            con, ["calm rune"])["calm rune"]["id"], "aaa-001-100")
        linhas = [(x["qty"], x["price_cents"]) for x in self.decks.shopping_list(con)
                  if x["card_key"] == "calm rune"]
        self.assertEqual(linhas, [(4, 10)])
        r = self.decks.resumo_das_faltas(con)
        # Nada se compra em versão especial: a Legend deste catálogo só existe
        # em base, e o Defy é main — joga-se e compra-se na base (2026-09-17).
        self.assertEqual(r["especiais"], {"cards": 0, "copies": 0, "cents": 0})
        # 4 Calm Rune + 4 Order Rune a 0,10 €, 3 Defy base a 1,50 €, a Legend.
        self.assertEqual(r["cents"], 8 * 10 + 3 * 150 + 1000)
        con.close()

    def test_uma_encomenda_da_alt_art_nao_abate_e_a_proposta_nao_a_tira(self):
        con = self.catalogo(copias=SEIS)
        self.pending.add(con, RUNA_ALT, 4, source="test")
        self.assertEqual(self.falta_de(con, "azir").get("calm rune"), 4)
        prop = self.locais.propor_deck(con, "azir")
        self.assertNotIn(RUNA_ALT, [x["printing_id"] for x in prop["items"]])
        con.close()

    def test_nao_esta_no_pimp(self):
        con = self.catalogo()
        pm = json.dumps(self.faltas.pimp(con), ensure_ascii=False)
        self.assertNotIn(RUNA_ALT, pm)
        self.assertIn("aaa-004a-100", pm)
        con.close()

    def test_as_outras_alt_arts_nao_sao_retiradas__o_main_joga_a_base_e_elas_tapam(self):
        """A alt art do Defy continua a existir (alvo do playset desde
        2026-09-18, aparece na grelha); o main joga a base primeiro
        (2026-09-17) e, desde a tarde desse dia, as alt arts tapam o que a
        base não chega — as 3 alt arts sozinhas servem o Defy
        (`test_versoes_deck.py`). A runa em alt art, retirada, NÃO tapa nada:
        é a diferença entre «retirada» e «outra versão»."""
        con = self.catalogo(copias={"aaa-004a-100": 3, "aaa-004-100": 3})
        a = self.decks.allocate(con)[self.idx(con)["azir"]["id"]]
        self.assertNotIn("defy", a["missing"])
        self.assertNotIn("defy", a["alloc_outras"])
        self.assertEqual(self.tiles(con)["aaa-004a-100"]["target"], 3)
        con.close()
        self.v = Vault()
        self.addCleanup(self.v.close)
        con = self.catalogo(copias={"aaa-004a-100": 3, RUNA_ALT: 6})
        a = self.decks.allocate(con)[self.idx(con)["azir"]["id"]]
        self.assertNotIn("defy", a["missing"])
        self.assertEqual(a["alloc_outras"].get("defy"), 3)
        self.assertEqual(a["missing"].get("calm rune"), 4)
        con.close()

    def test_com_os_decks_todos_na_base_continua_retirada(self):
        escrever_config(papeis=(), contar_runas=True)
        self.recarregar()
        con = self.catalogo(copias=SEIS)
        self.assertEqual(self.falta_de(con, "azir").get("calm rune"), 4)
        self.assertNotIn(RUNA_ALT, self.tiles(con))
        con.close()


class TestConfig(Base):
    def test_o_default_e_a_e_a_regra_da_legend_deixou_de_existir(self):
        from riftvault import config
        self.assertEqual(config.DEFAULTS["runas_especiais"]["retiradas"], ["a"])
        self.assertNotIn("runas_alt_art_da_edicao_da_legend", config.DEFAULTS["decks"])
        for nome in ("edicao_da_legend", "edicao_do_deck", "QUALQUER",
                     "runas_da_edicao_da_legend"):
            self.assertFalse(hasattr(self.decks, nome), nome)
        real = json.loads((Path(__file__).resolve().parent.parent
                           / "riftvault_config.json").read_text(encoding="utf-8"))
        self.assertEqual(real["runas_especiais"]["retiradas"], ["a"])
        self.assertNotIn("runas_alt_art_da_edicao_da_legend", real["decks"])

    def test_sem_runa_nao_ha_retirada(self):
        escrever_config(tipos=())
        self.recarregar()
        con = self.catalogo(copias=SEIS)
        self.assertIn(RUNA_ALT, self.tiles(con))
        con.close()

    def test_um_valor_desconhecido_rebenta(self):
        escrever_config(retiradas=("b",))
        self.recarregar()
        con = self.catalogo()
        with self.assertRaises(ValueError):
            self.metrics.set_payload(con, "AAA")
        con.close()

    def test_nao_escreve(self):
        con = self.catalogo(copias=SEIS)
        self.metrics.set_payload(con, "AAA")
        self.a_mais.payload(con)
        self.decks.allocate(con)
        self.assertEqual(con.execute("SELECT qty FROM copies WHERE printing_id = ?",
                                     (RUNA_ALT,)).fetchone()["qty"], 6)
        con.close()


if __name__ == "__main__":
    unittest.main()

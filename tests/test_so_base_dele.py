"""O `decks.so_base` virou para A REGRA DELE (2026-10-03).

Palavras dele, ditas duas vezes:

    *"usa o que esta na coleccao, sendo foil ou nao, sendo Alt Art ou nao,
    sendo Overnumbered ou nao. Se nao houver versao normal, ele avisa que sao
    X normais e X Alt Art / Overnumbered ou o que quer que seja"* (2026-10-01)

    *"caso um deck precise de uma carta, que nao ha versao disponivel em
    normal, mas esteja disponivel em Alt Art ou outra, usa, mas no deck
    separa as versoes por Art"* (2026-09-17)

De 2026-09-21 a 2026-10-03 o config dizia `so_base: true`, que é o contrário:
uma carta que ele TEM em Alt Art aparecia como falta A COMPRAR. O mecanismo
que faz a regra dele já existia desde 2026-09-17 (`Versoes.outras_de`,
`versoes_em`, o `versoesNota`/`tapadaNota` do `app.js`) — o que esta ordem
mudou foi o INTERRUPTOR, nos três sítios que o respondiam (o ficheiro de
config, o `config.DEFAULTS` e a omissão do `decks.so_base()`), para não haver
duas respostas à mesma pergunta.

O que se fixa aqui, por essa ordem:
  1. a regra, pelas palavras dele — a base primeiro, a outra arte a tapar o
     que ela não cobre, nunca uma assinada, nunca uma runa retirada, e a
     falta que sobra compra-se na BASE;
  2. as versões SEPARADAS POR ARTE na página do deck, com o número de cada
     («3 — 1 normal, 2 Alt Art») e no CLI;
  3. o ALVO DA COLEÇÃO não sobe por isto (uma alt art continua a pedir o que
     o `master_set.um_de_cada` disser, joguem os decks ou não);
  4. a fotografia: a Coleção não mexe um número — com a prova pela negativa
     ao lado, senão uma fotografia de zeros passava sempre;
  5. o interruptor: o config real, o `DEFAULTS`, a omissão, e `true` a voltar
     ao que era (o mecanismo continua testável nos dois sentidos).

Tudo contra pastas temporárias (`tests.fixture.Vault`) e um config PRÓPRIO: o
`data/` e o `riftvault_config.json` a sério nunca são tocados.
"""

from __future__ import annotations

import contextlib
import importlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

CONFIG = Path(tempfile.gettempdir()) / "riftvault-so-base-dele.json"
REPO = Path(__file__).resolve().parent.parent


def escrever_config(so_base: bool = False, papeis=(), retiradas=("a",)) -> None:
    """O bloco `decks` DE HOJE: `so_base: false` e `so_normais_excepto` VAZIO.

    Os dois juntos são a regra dele: todos os lugares (a Legend e o Champion
    incluídos) jogam a base e completam com outra arte que ele tenha. A regra
    de 2026-09-17 sobre a Legend/Champion jogarem UMA versão especial depende
    da segunda lista e continua desligada.
    """
    CONFIG.write_text(json.dumps({
        "master_set": {"fora_da_percentagem": ["a", "overnumbered", "promo"],
                       "escondidas": ["-T", "*", "-R"],
                       # As alt arts ao playset (2026-09-18); as promos e as
                       # sobrenumeradas a 1 de cada (2026-09-19).
                       "um_de_cada": ["overnumbered", "promo"]},
        "master_targets_by_type": {"Rune": 3},
        "decks": {"so_base": so_base,
                  "so_normais_excepto": list(papeis),
                  "versoes_especiais": ["a", "overnumbered", "promo"],
                  "contar_runas": False},
        "runas_especiais": {"tipos": ["Rune"], "excepto": ["base"],
                            "retiradas": list(retiradas)},
        "listas_de_compra": {"so_master_set": True},
        "a_mais": {"sem_edicoes": []},
    }), encoding="utf-8")
    os.environ["RIFTVAULT_CONFIG"] = str(CONFIG)


escrever_config()

from tests.fixture import Vault  # noqa: E402

# Um deck com uma carta em três artes (Vi: base, alt art, sobrenumerada,
# signature), uma carta só em base (Brutalizer), a Legend, o Champion e runas.
DECK = ("Nome: Leona\nLegend:\n1 Emperor of the Sands\n\nChampion:\n1 Sovereign\n\n"
        "MainDeck:\n3 Vi\n3 Brutalizer\n\nRune Pool:\n4 Calm Rune\n")

EMP, EMP_A = "tst-003-100", "tst-003a-100"
SOV, SOV_OVER = "tst-004-100", "tst-102-100"
VI, VI_A, VI_OVER, VI_STAR = "tst-001-100", "tst-001a-100", "tst-101-100", "tst-101-star-100"
BRUT = "tst-002-100"
RUNA, RUNA_A = "tst-007-100", "tst-007a-100"

PRECOS = {VI: 350, VI_A: 3957, VI_OVER: 8000, VI_STAR: 90000, BRUT: 50,
          EMP: 1000, EMP_A: 3000, SOV: 200, SOV_OVER: 4000, RUNA: 11, RUNA_A: 500}


class Base(unittest.TestCase):
    def setUp(self):
        escrever_config()
        self.addCleanup(lambda: os.environ.pop("RIFTVAULT_CONFIG", None))
        self.v = Vault()
        self.addCleanup(self.v.close)
        from riftvault import (a_mais, a_subir, collection, config, decks, faltas,
                               faltas_edicao, locais, metrics, pending, prices)
        for m in (metrics, locais, decks, pending, faltas, a_subir, prices,
                  collection, faltas_edicao, a_mais):
            importlib.reload(m)
        self.metrics, self.decks, self.faltas = metrics, decks, faltas
        self.a_subir, self.pending, self.locais = a_subir, pending, locais
        self.prices, self.a_mais, self.config = prices, a_mais, config
        self.collection, self.faltas_edicao = collection, faltas_edicao

    def recarregar(self, **kw):
        escrever_config(**kw)
        self.config.load.cache_clear()

    def catalogo(self, copias: dict | None = None, lista: str = DECK):
        from riftvault import collection
        con = self.v.connect()
        add = self.v.add_printing
        add(con, VI, "TST", 1, "Vi", size=100)
        add(con, VI_A, "TST", 1, "Vi", variant="a", kind="alt_art",
            rarity="showcase", base_rarity="rare", size=100)
        add(con, BRUT, "TST", 2, "Brutalizer", size=100)
        add(con, EMP, "TST", 3, "Emperor of the Sands", card_type="Legend", size=100)
        add(con, EMP_A, "TST", 3, "Emperor of the Sands", variant="a", kind="alt_art",
            card_type="Legend", rarity="showcase", base_rarity="epic", size=100)
        add(con, SOV, "TST", 4, "Sovereign", size=100)
        add(con, RUNA, "TST", 7, "Calm Rune", card_type="Rune", size=100)
        add(con, RUNA_A, "TST", 7, "Calm Rune", card_type="Rune", variant="a",
            kind="alt_art", rarity="showcase", base_rarity="common", size=100)
        add(con, VI_OVER, "TST", 101, "Vi", size=100, rarity="showcase", api_sort=101)
        add(con, VI_STAR, "TST", 101, "Vi", variant="star", kind="signature",
            rarity="showcase", size=100, codigo="TST-101*/100", api_sort=102)
        add(con, SOV_OVER, "TST", 102, "Sovereign", size=100, rarity="showcase",
            api_sort=103)
        self.v.rebuild(con)
        for pid, cents in PRECOS.items():
            con.execute("INSERT INTO catalog.price_latest (printing_id, price_cents) "
                        "VALUES (?,?)", (pid, cents))
        for pid, n in (copias or {}).items():
            collection.adjust(con, pid, n, source="test")
        self.v.write_deck("leona", lista)
        self.decks.import_all(con, log=lambda *_: None)
        return con

    # Tudo o que o deck pede em base, MENOS a terceira Vi — o caso dele: tem 2
    # Vi base e uma Vi em Alt Art parada na Coleção.
    QUASE = {BRUT: 3, EMP: 1, SOV: 1, RUNA: 4, VI: 2}

    def idx(self, con) -> dict:
        return {d["slug"]: d for d in self.decks.decks_index(con)}

    def aloc(self, con, slug: str = "leona") -> dict:
        return self.decks.allocate(con)[self.idx(con)[slug]["id"]]

    def payload(self, con, slug: str = "leona") -> dict:
        return self.decks.deck_payload(con, self.idx(con)[slug]["id"])

    def linha(self, con, nome: str, role: str = "main", slug: str = "leona") -> dict:
        s = next(s for s in self.payload(con, slug)["sections"] if s["role"] == role)
        return next(c for c in s["cards"] if c["name"] == nome)

    def versoes(self, a: dict, ck: str) -> list[tuple]:
        return [(x["id"], x["qty"], x["lugar"]) for x in a["versoes_em"].get(ck, [])]

    def fotografia(self, con) -> dict:
        """Tudo o que é NÚMERO DA COLEÇÃO. É a mesma lista do
        `test_copias_proprias` (níveis, denominador, wantlist, valor, totais,
        grelha, playset jogável, barra, Faltas, Encomendas, A mais), mais os
        ALVOS impressão a impressão — é por eles que se vê que o alvo de uma
        alt art não sobe por o deck a jogar."""
        cfg = self.config.load()
        sp = self.metrics.set_payload(con, "TST")
        fe = self.faltas_edicao.payload(con, cfg)
        am = self.a_mais.payload(con, cfg)
        return {
            "niveis": [(l["k"], l["done"], l["total"], l["missing"], l["cents"])
                       for l in self.metrics.niveis_payload(con, cfg)["levels"]],
            "wantlist": {k: self.a_subir.wantlist(con, cfg=cfg)[k]
                         for k in ("text", "lines", "copies", "cents")},
            "valor": self.prices.collection_value(con)["cents"],
            "valor_copias": self.prices.collection_value(con)["copias"],
            "totais": self.collection.totals(con),
            "grelha": [(p["id"], p["qty"], p["target"], p["qty_valor"])
                       for g in sp["groups"] for p in g["printings"]],
            "playset": {g["card_key"]: g["playset"] for g in sp["groups"]},
            "master": sp["progress"]["master"],
            "painel": sp["progress"]["painel"],
            "faltas": (fe["totals"], fe["totals_lists"]),
            "encomendas": self.pending.encomendas(con)["totals"],
            "a_mais": {s["set"]: [(x["printing_id"], x["extra"], x["have"])
                                  for x in s["excedente"]["items"]] for s in am["sets"]},
        }

    def cli(self, *argv) -> str:
        from riftvault import cli
        importlib.reload(cli)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            with contextlib.suppress(SystemExit):
                cli.main(list(argv))
        return buf.getvalue()


# ---------------------------------------------------------------------------


class TestARegraDele(Base):
    """1. *"usa o que esta na coleccao, sendo Alt Art ou nao, sendo
    Overnumbered ou nao"* — e a base primeiro."""

    def test_a_alt_art_parada_tapa_a_terceira_e_nao_e_falta(self):
        """O caso dele: 2 Vi base + 1 Vi em Alt Art. Com `so_base: true` isto
        era «falta 1 Vi a comprar»; hoje o deck usa a que ele tem."""
        con = self.catalogo(copias={**self.QUASE, VI_A: 1})
        a = self.aloc(con)
        self.assertEqual(a["missing"].get("vi", 0), 0,
                         "a Vi em Alt Art que ele TEM não pode ser falta a comprar")
        self.assertEqual(a["alloc"]["vi"], 3)
        self.assertEqual(a["alloc_outras"]["vi"], 1, "uma cópia veio de outra arte")
        self.assertEqual(self.versoes(a, "vi"),
                         [(VI, 2, "normal"), (VI_A, 1, "outra")],
                         "a BASE primeiro, e só o que ela não tapa vem da outra arte")

    def test_com_so_base_ligado_a_mesma_coleccao_pedia_para_comprar(self):
        """A prova pela negativa: é o interruptor que faz a diferença."""
        self.recarregar(so_base=True)
        con = self.catalogo(copias={**self.QUASE, VI_A: 1})
        a = self.aloc(con)
        self.assertEqual(a["missing"]["vi"], 1,
                         "era isto que estava mal: mandava comprar o que ele tem")
        self.assertEqual(a["alloc_outras"], {})

    def test_a_sobrenumerada_tambem_tapa(self):
        """*"sendo Overnumbered ou nao"* — é a mesma lista."""
        con = self.catalogo(copias={**self.QUASE, VI_OVER: 1})
        a = self.aloc(con)
        self.assertEqual(a["missing"].get("vi", 0), 0)
        self.assertEqual(self.versoes(a, "vi"),
                         [(VI, 2, "normal"), (VI_OVER, 1, "outra")])

    def test_a_assinada_NUNCA_tapa(self):
        """*"nunca assinada"* é regra, não config."""
        con = self.catalogo(copias={**self.QUASE, VI_STAR: 3})
        a = self.aloc(con)
        self.assertEqual(a["missing"]["vi"], 1, "a signature não serve o deck")
        self.assertEqual(self.versoes(a, "vi"), [(VI, 2, "normal")])

    def test_a_runa_em_alt_art_RETIRADA_nao_tapa(self):
        """As runas em Alt Art estão retiradas de tudo desde 2026-09-17, e o
        `so_base` a `false` não as traz de volta. (Com as runas fora da
        contagem dos decks a runa nem chega a pedir nada — o que se fixa é
        que a retirada não entra nas versões que servem.)"""
        con = self.catalogo(copias={**self.QUASE, RUNA_A: 4})
        versoes = self.decks.versoes_dos_decks(con)
        self.assertNotIn(RUNA_A, versoes.normais_de("calm rune"))
        self.assertNotIn(RUNA_A, versoes.outras_de("calm rune"))

    def test_a_falta_que_sobra_compra_se_na_BASE(self):
        """Ele tem 2 Vi base e nada mais: falta 1, e a linha aponta à base
        (que é a mais barata e a que ele quer jogar)."""
        con = self.catalogo(copias=self.QUASE)
        a = self.aloc(con)
        self.assertEqual(a["missing"]["vi"], 1)
        self.assertEqual(self.decks.versoes_dos_decks(con).compra("vi"), VI)
        self.assertEqual(self.linha(con, "Vi")["order_code"], "TST-001/100")

    def test_a_LEGEND_e_o_CHAMPION_jogam_a_base_e_tapam_com_outra_arte(self):
        """A lista `so_normais_excepto` está VAZIA: a regra de 2026-09-17 (a
        Legend numa versão ESPECIAL) continua desligada e não volta só por
        esta chave ir a `false`. O que a Legend faz é o que faz uma carta
        qualquer — base primeiro, outra arte a tapar."""
        con = self.catalogo(copias={BRUT: 3, SOV: 1, RUNA: 4, VI: 3, EMP_A: 1})
        a = self.aloc(con)
        self.assertEqual(a["need_especial"], {}, "não há lugar especial nenhum")
        self.assertEqual(a["missing"].get("emperor of the sands", 0), 0,
                         "a Legend em Alt Art que ele tem serve")
        self.assertEqual(self.versoes(a, "emperor of the sands"),
                         [(EMP_A, 1, "outra")])
        self.assertIsNone(self.payload(con)["sections"][0]["cards"][0]["especial"])


class TestSeparaAsVersoesPorArte(Base):
    """2. *"no deck separa as versoes por Art"* — com o número de cada."""

    def test_a_linha_reparte_se_pelas_impressoes_que_a_servem(self):
        con = self.catalogo(copias={**self.QUASE, VI_A: 1})
        c = self.linha(con, "Vi")
        self.assertEqual(c["have"], 3)
        self.assertEqual(c["outras"], 1)
        self.assertEqual([(v["id"], v["qty"], v["lugar"], v["label"]) for v in c["versoes"]],
                         [(VI, 2, "normal", "normal"), (VI_A, 1, "outra", "Alt Art")])

    def test_o_rotulo_de_cada_arte_sao_as_palavras_dele(self):
        con = self.catalogo(copias={**self.QUASE, VI_OVER: 1})
        v = self.decks.versoes_dos_decks(con)
        self.assertEqual(v.rotulo(VI), "normal")
        self.assertEqual(v.rotulo(VI_A), "Alt Art")
        self.assertEqual(v.rotulo(VI_OVER), "sobrenumerada")

    def test_tres_de_uma_carta_em_duas_artes_leem_se_1_normal_2_alt_art(self):
        """A frase que ele pediu — «3 — 1 normal, 2 Alt Art»."""
        con = self.catalogo(copias={BRUT: 3, EMP: 1, SOV: 1, RUNA: 4,
                                    VI: 1, VI_A: 2})
        c = self.linha(con, "Vi")
        self.assertEqual(c["have"], 3)
        por_arte = {}
        for v in c["versoes"]:
            k = "normal" if v["lugar"] != "outra" else v["label"]
            por_arte[k] = por_arte.get(k, 0) + v["qty"]
        self.assertEqual(por_arte, {"normal": 1, "Alt Art": 2})

    def test_o_app_js_escreve_a_conta_por_arte_e_a_regra_nova(self):
        js = (REPO / "riftvault" / "web" / "app.js").read_text(encoding="utf-8")
        self.assertIn("function tapadaNota", js)
        self.assertIn("function versoesNota", js)
        # A nota da página do deck diz a regra que está em vigor, nos dois
        # sentidos: com `so_base` desligado não pode ficar calada.
        self.assertIn("o que está na Coleção, seja que arte for", js)
        self.assertIn("Só <b>versões base</b>", js)

    def test_a_vista_do_deck_no_CLI_diz_as_versoes(self):
        self.catalogo(copias={**self.QUASE, VI_A: 1})
        saida = self.cli("deck", "leona")
        self.assertIn("Alt Art", saida)
        self.assertNotIn("[só versões base]", saida)


class TestOAlvoDaColeccaoNaoSobe(Base):
    """3. *"vamos voltar atras"* (2026-09-17): o alvo da Coleção nunca sobe
    por causa dos decks. Uma alt art pede o que o `master_set.um_de_cada`
    disser — hoje o playset —, jogue-a o deck ou não."""

    def test_a_alt_art_que_o_deck_joga_pede_o_mesmo_de_sempre(self):
        con = self.catalogo(copias={**self.QUASE, VI_A: 1})
        sp = self.metrics.set_payload(con, "TST")
        alvos = {p["id"]: p["target"] for g in sp["groups"] for p in g["printings"]}
        self.assertEqual(alvos[VI_A], 3, "a alt art ao playset (2026-09-18)")
        self.assertEqual(alvos[VI_OVER], 1, "a sobrenumerada a 1 de cada")
        self.assertEqual(alvos[EMP_A], 1, "uma Legend em alt art pede 1")

    def test_o_alvo_e_o_mesmo_com_o_interruptor_de_um_lado_e_do_outro(self):
        con = self.catalogo(copias={**self.QUASE, VI_A: 1})
        com = {p["id"]: p["target"]
               for g in self.metrics.set_payload(con, "TST")["groups"]
               for p in g["printings"]}
        self.recarregar(so_base=True)
        sem = {p["id"]: p["target"]
               for g in self.metrics.set_payload(con, "TST")["groups"]
               for p in g["printings"]}
        self.assertEqual(com, sem)

    def test_a_alt_art_que_o_deck_joga_continua_a_poder_estar_a_mais(self):
        """Quatro alt arts com alvo 3: a quarta é excedente, e o deck a jogar
        uma não muda esse número — o `a_mais` conta `cópias − max(usadas,
        alvo)`, e é o ALVO que manda aqui."""
        con = self.catalogo(copias={**self.QUASE, VI_A: 4})
        itens = {x["printing_id"]: x["extra"] for s in
                 self.a_mais.payload(con, self.config.load())["sets"]
                 for x in s["excedente"]["items"]}
        self.assertEqual(itens.get(VI_A), 1)


class TestAColeccaoNaoMexe(Base):
    """4. A fotografia: virar o interruptor é uma decisão dos DECKS. Nenhum
    número da Coleção pode mexer com ele."""

    COPIAS = {BRUT: 3, EMP: 1, EMP_A: 1, SOV: 1, SOV_OVER: 1, RUNA: 4,
              RUNA_A: 2, VI: 2, VI_A: 2, VI_OVER: 1, VI_STAR: 1}

    def test_a_coleccao_e_a_mesma_com_so_base_ligado_e_desligado(self):
        con = self.catalogo(copias=self.COPIAS)
        desligado = self.fotografia(con)
        self.recarregar(so_base=True)
        ligado = self.fotografia(con)
        self.assertEqual(desligado, ligado)

    def test_a_fotografia_nao_e_de_zeros(self):
        """Uma fotografia que não detecte nada passava sempre."""
        con = self.catalogo(copias=self.COPIAS)
        antes = self.fotografia(con)
        self.collection.adjust(con, VI, 1, source="test")
        self.assertNotEqual(antes, self.fotografia(con))
        self.assertTrue(antes["valor"] > 0 and antes["totais"]["copies"] > 0)

    def test_os_decks_e_que_mexem_e_mexem(self):
        """A outra metade da prova pela negativa: o interruptor TEM de mudar
        alguma coisa, senão o teste de cima não prova nada."""
        con = self.catalogo(copias=self.COPIAS)
        a_desligado = self.aloc(con)
        self.recarregar(so_base=True)
        a_ligado = self.aloc(con)
        self.assertNotEqual(a_desligado["alloc_outras"], a_ligado["alloc_outras"])
        self.assertEqual(a_ligado["missing"]["vi"], 1)
        self.assertEqual(a_desligado["missing"].get("vi", 0), 0)

    def test_o_copies_nao_se_toca(self):
        con = self.catalogo(copias=self.COPIAS)
        tabela = lambda: sorted(map(tuple, con.execute(
            "SELECT printing_id, qty, qty_foil FROM copies ORDER BY printing_id")))
        antes = tabela()
        self.decks.allocate(con)
        self.recarregar(so_base=True)
        self.decks.allocate(con)
        self.assertEqual(antes, tabela())


class TestOInterruptor(Base):
    """5. Os três sítios que respondiam à mesma pergunta dizem todos o mesmo."""

    def test_o_config_REAL_diz_false(self):
        real = json.loads((REPO / "riftvault_config.json").read_text(encoding="utf-8"))
        self.assertIs(real["decks"]["so_base"], False)
        self.assertEqual(real["decks"]["so_normais_excepto"], [],
                         "a regra de 2026-09-17 continua desligada")
        nota = real["_decks_so_base_nota"]
        self.assertIn("sendo Alt Art ou nao", nota)
        self.assertIn("2026-10-03", nota)

    def test_o_DEFAULTS_diz_false(self):
        self.assertIs(self.config.DEFAULTS["decks"]["so_base"], False)
        self.assertEqual(self.config.DEFAULTS["decks"]["so_normais_excepto"], [])

    def test_a_omissao_e_false_um_riftvault_sem_a_chave_usa_o_que_ha(self):
        """Sem a chave escrita, a app não pode mandar comprar o que ele tem."""
        self.assertIs(self.decks.so_base({"decks": {}}), False)
        self.assertIs(self.decks.so_base({}), False)

    def test_true_volta_a_ser_so_a_base_o_mecanismo_fica_testavel(self):
        self.recarregar(so_base=True)
        con = self.catalogo(copias={**self.QUASE, VI_A: 1})
        v = self.decks.versoes_dos_decks(con)
        self.assertEqual(v.especiais, {})
        self.assertEqual(v.outras_de("vi"), [])
        self.assertTrue(self.payload(con)["so_base"])

    def test_um_modo_que_nao_existe_rebenta_de_caminho(self):
        with self.assertRaises(ValueError):
            self.decks.so_base({"decks": {"modo": "pool_proprio"}})

    def test_a_chave_do_CONFIG_e_lida_num_sitio_so(self):
        """Quem quer saber se os decks jogam só a base pergunta ao
        `decks.so_base()`; ninguém vai ao config buscar a chave por fora —
        era assim que nasciam duas respostas à mesma pergunta. (Escrever
        `"so_base": decks.so_base()` num payload é outra coisa: é a resposta
        a passar para o ecrã, e o `build.py` e o `decks.py` fazem-no.)"""
        self.assertEqual(self.decks.SO_BASE, "so_base")
        fora = []
        for py in (REPO / "riftvault").glob("*.py"):
            if py.name == "decks.py":
                continue
            for n, linha in enumerate(py.read_text(encoding="utf-8").splitlines(), 1):
                if linha.lstrip().startswith("#"):
                    continue
                if "SO_BASE" in linha or "_opcoes_decks" in linha:
                    fora.append(f"{py.name}:{n}")
        self.assertEqual(fora, [], "o config lê-se pelo `decks.so_base()`")


if __name__ == "__main__":
    unittest.main()

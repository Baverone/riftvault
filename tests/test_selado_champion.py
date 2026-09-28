"""Tirar os CHAMPION DECK todos do «Produto Selado» (André, 2026-09-26).

Palavras dele: *"retira os Champion Deck todos"*.

NÃO HÁ MECANISMO NOVO, pela terceira vez: é a mesma `selado.excluidos` das
duas ordens de 25/09 (22 → 32 → **43**), e a aba passa de 66 para **55**.

1. OS 11 QUE SAEM, pelo nome exacto, todos da categoria 262
   OGN Jinx/Viktor/Lee Sin · SFD Rumble/Fiora · UNL Vi/Vex ·
   LGC Ashe/Tryndamere/Lux/Garen. (O «Origins: Champion Deck Set» já saíra a
   25/09, por «compram-se à unidade».)

2. O QUE **NÃO** SAI, e é onde é fácil enganar-se
   - os 2 **SHOWDOWN DECK** (Vendetta «Zed vs Shen», Radiance «Evelynn vs
     Seraphine»): são outra linha de produto e ele nomeou o Champion Deck;
   - os 7 **CHAMPION DECK DISPLAY** da `selado.extra`, cujo nome CONTÉM o dos
     que saem. É a prova do «o nome é EXACTO, nunca um pedaço»: se o critério
     fosse um pedaço do nome, os displays iam atrás. Ele nunca os nomeou, e o
     padrão dele ao longo do dia foi tratar a unidade e o display como linhas
     separadas.

3. A LISTA INTEIRA CASA — o guarda que faltava
   A ordem trazia um bug reportado (dois «Trial Deck Set Set» visíveis por o
   nome não bater) que **não existia**: o `_resolver_excluidos` casa pelo nome
   LIMPO e pelo BRUTO, os dois estão fora desde 25/09 e o
   `test_selado_tirar2` já o fixava. O que faltava era a pergunta geral —
   *«há entradas na lista que não estão a tirar nada?»* —, e é isso que o
   `TestNenhumaExclusaoMorta` responde, para a lista INTEIRA e não para os
   nomes de uma ordem. Hoje são zero.

E, por cima, a defesa de sempre: **nada disto mexe num número da Coleção** — a
fotografia do `test_selado`, por referência, para não haver duas definições de
«número da Coleção».
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

from tests.test_selado import CATALOGO, Base  # noqa: E402
from tests.test_selado import TestNaoEntraNaColecao as _Foto  # noqa: E402

REPO = Path(__file__).resolve().parent.parent

# OS ONZE, tal como ficam escritos no `riftvault_config.json`.
OS_ONZE = [
    'Origins: "Jinx" Champion Deck',
    'Origins: "Viktor" Champion Deck',
    'Origins: "Lee Sin" Champion Deck',
    'Spiritforged: "Rumble" Champion Deck',
    'Spiritforged: "Fiora" Champion Deck',
    'Unleashed: "Vi" Champion Deck',
    'Unleashed: "Vex" Champion Deck',
    'Legacy: "Ashe" Champion Deck',
    'Legacy: "Tryndamere" Champion Deck',
    'Legacy: "Lux" Champion Deck',
    'Legacy: "Garen" Champion Deck',
]

# Os 7 displays da `selado.extra` que TÊM DE FICAR — cada um com o nome de um
# dos de cima lá dentro.
OS_SETE_DISPLAYS = [
    'Origins: "Jinx" Champion Deck Display',
    'Origins: "Viktor" Champion Deck Display',
    'Origins: "Lee Sin" Champion Deck Display',
    'Spiritforged: "Rumble" Champion Deck Display',
    'Spiritforged: "Fiora" Champion Deck Display',
    'Unleashed: "Vi" Champion Deck Display',
    'Unleashed: "Vex" Champion Deck Display',
]

# Os 2 showdown decks do CardTrader que TÊM DE FICAR.
OS_DOIS_SHOWDOWN = [
    'Vendetta: "Zed vs Shen" Showdown Deck',
    'Radiance: "Evelynn vs Seraphine" Showdown Deck',
]

# O catálogo de brincar do `test_selado` já tem um champion deck (o `ct-104`,
# «Teste: "Jinx" Champion Deck»); junta-se-lhe o DISPLAY dele — que tem o nome
# do outro lá dentro, e é o par que esta ordem separa — e um showdown deck.
DECK = 'Teste: "Jinx" Champion Deck'
DISPLAY = 'Teste: "Jinx" Champion Deck Display'
SHOWDOWN = 'Teste: "Zed vs Shen" Showdown Deck'

CAT = json.loads(json.dumps(CATALOGO))
CAT["produtos"] += [
    {"blueprint_id": 702, "nome": DISPLAY, "versao": "",
     "categoria_id": 263, "edicao": "TST", "edicao_nome": "Teste",
     "img": None, "cardmarket_id": None},
    {"blueprint_id": 703, "nome": SHOWDOWN, "versao": "",
     "categoria_id": 262, "edicao": "TST", "edicao_nome": "Teste",
     "img": None, "cardmarket_id": None},
]
CAT["precos"]["702"] = {"cents": 9000, "currency": "EUR", "day": "2026-09-26",
                        "n_listings": 1, "n_sellers": 1, "n_copies": 1}
CAT["precos"]["703"] = {"cents": 3000, "currency": "EUR", "day": "2026-09-26",
                        "n_listings": 2, "n_sellers": 2, "n_copies": 2}


class ChampionBase(Base):
    def setUp(self):
        super().setUp()
        self.escrever_catalogo(CAT)

    def payload(self, excluidos=None, **kw):
        self.cfg_selado({
            **({"excluidos": excluidos} if excluidos is not None else {}), **kw})
        return self.selado.payload(self.con())

    def nomes(self, **kw):
        return [x["nome"] for x in self.payload(**kw)["items"] if not x["acessorio"]]


# ---------------------------------------------------------------------------
# 1. O mecanismo: o champion deck sai, o display dele fica
# ---------------------------------------------------------------------------


class TestOChampionDeckSaiEODisplayFica(ChampionBase):
    def test_sem_a_lista_estao_os_tres(self):
        nomes = self.nomes()
        for n in (DECK, DISPLAY, SHOWDOWN):
            self.assertIn(n, nomes)

    def test_tirar_o_deck_nao_leva_o_display(self):
        """O NOME É EXACTO, NUNCA UM PEDAÇO — é a razão de os 7 displays
        ficarem quando os 11 decks saem."""
        nomes = self.nomes(excluidos=[DECK])
        self.assertNotIn(DECK, nomes)
        self.assertIn(DISPLAY, nomes)

    def test_tirar_o_deck_nao_leva_o_showdown(self):
        self.assertIn(SHOWDOWN, self.nomes(excluidos=[DECK]))

    def test_sai_dos_contadores(self):
        antes = self.payload(excluidos=[])
        depois = self.payload(excluidos=[DECK])
        self.assertEqual(depois["totals"]["ha"], antes["totals"]["ha"] - 1)
        self.assertEqual(depois["totals"]["falta"], antes["totals"]["falta"] - 1)

    def test_o_scope_di_lo(self):
        pay = self.payload(excluidos=[DECK])
        self.assertEqual([x["nome"] for x in pay["scope"]["excluidos"]], [DECK])

    def test_repor_e_tirar_o_nome_da_lista(self):
        com = self.payload(excluidos=[DECK])["totals"]["ha"]
        sem = self.payload(excluidos=[])["totals"]["ha"]
        self.assertEqual(sem, com + 1)

    def test_a_unidade_gravada_num_excluido_nao_se_apaga(self):
        """Tirar da aba não apaga o que ele tinha marcado: volta a contar
        quando o nome sair da lista."""
        con = self.con()
        self.selado.ajustar(con, "ct-104", 1, source="test")
        self.assertEqual(self.selado.payload(con)["totals"]["tenho"], 1)
        self.cfg_selado({"excluidos": [DECK]})
        self.assertEqual(self.selado.payload(con)["totals"]["tenho"], 0)
        self.cfg_selado({"excluidos": []})
        pay = self.selado.payload(con)
        self.assertEqual(pay["totals"]["tenho"], 1)
        self.assertEqual(self.por_id(pay["items"], "ct-104")["qty"], 1)

    def test_um_mais_num_excluido_recusa(self):
        self.cfg_selado({"excluidos": [DECK]})
        with self.assertRaises(self.selado.ProdutoExcluido):
            self.selado.ajustar(self.con(), "ct-104", 1, source="test")

    def test_o_catalogo_em_disco_fica_intacto(self):
        antes = self.config.SELADO_PATH.read_bytes()
        self.payload(excluidos=[DECK])
        self.assertEqual(self.config.SELADO_PATH.read_bytes(), antes)


# ---------------------------------------------------------------------------
# 2. Os onze contra o CONFIG do repo
# ---------------------------------------------------------------------------


class TestOConfigReal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sel = json.loads(
            (REPO / "riftvault_config.json").read_text(encoding="utf-8"))["selado"]
        cls.cfg_todo = json.loads(
            (REPO / "riftvault_config.json").read_text(encoding="utf-8"))

    def arquivados(self) -> list[dict]:
        """O `selado.extra` mais o `_selado_extra_arquivado`: o `extra` ficou
        vazio a 2026-09-28 e os 17 objectos passaram para o arquivo —
        **esvaziar não é apagar**, e o que aqui se pergunta é o que se SABE
        sobre eles, não onde a aba os mostra."""
        return (self.sel["extra"]
                + (self.cfg_todo.get("_selado_extra_arquivado") or {}).get(
                    "produtos", []))

    def test_a_lista_tem_49_sem_repetidos(self):
        """22 (25/09, manhã) + 10 (25/09, noite) + 11 Champion Deck (26/09)
        + 7 sem mercado (26/09, ver `test_selado_sem_mercado`) − 2 que
        voltaram + 1 chinês (28/09, `test_selado_ingles`)."""
        self.assertEqual(len(self.sel["excluidos"]), 49)
        self.assertEqual(len(set(self.sel["excluidos"])), 49)

    def test_os_onze_estao_la(self):
        for n in OS_ONZE:
            self.assertIn(n, self.sel["excluidos"], n)

    def test_as_32_das_ordens_anteriores_continuam_la(self):
        """Acrescentar não é reescrever. (Menos o «Unleashed Sleeved Booster»,
        que **voltou** a 2026-09-28 — o Cardmarket revelou-lhe oferta a 13,00 €
        e ele é inglês; ver `test_selado_ingles`.)"""
        for n in ("Origins Booster", "Origins Sleeved Booster", "Origins Slim Booster",
                  "Spiritforged Booster", "Spiritforged Slim Booster",
                  "Unleashed Booster",
                  "Unleashed Slim Booster", "Vendetta Booster", "Radiance Booster",
                  "Radiance Sleeved Booster", "Legacy Booster",
                  "The Reckoning Booster", "Origins Slim Booster Box",
                  "Spiritforged Slim Booster Box", "Unleashed Slim Booster Box",
                  "Origins: Champion Deck Set", "Spiritforged Bulk Runes",
                  "Spiritforged Pre-Rift Kit", "Unleashed Pre-Rift Kit",
                  "Vendetta Pre-Rift Kit", "Radiance Pre-Rift Kit",
                  "Unleashed: Poro Scene Set", "Arcane Complete Set",
                  "Origins: Jinx Trial Deck", "Origins: Viktor Trial Deck",
                  "Origins: Volibear Trial Deck", "Origins: Yasuo Trial Deck",
                  "2024 Trial Deck Set", "2025 Trial Deck Set",
                  "2024 Trial Deck Case", "2025 Trial Deck Case"):
            self.assertIn(n, self.sel["excluidos"], n)

    def test_os_sete_displays_nao_foram_parar_a_lista(self):
        for n in OS_SETE_DISPLAYS:
            self.assertNotIn(n, self.sel["excluidos"], n)

    def test_os_dois_showdown_nao_foram_parar_a_lista(self):
        for n in OS_DOIS_SHOWDOWN:
            self.assertNotIn(n, self.sel["excluidos"], n)

    def test_os_sete_displays_continuam_conhecidos(self):
        """Ficaram por ESTA ordem — o deck sai, o display dele não. Saíram da
        aba a 2026-09-28, por não terem página própria em mercado nenhum, e o
        que se sabe deles está no `_selado_extra_arquivado`: o que saiu foi a
        presença, não o conhecimento."""
        nomes = [x["nome"] for x in self.arquivados()]
        for n in OS_SETE_DISPLAYS:
            self.assertIn(n, nomes, n)
        champion = [n for n in nomes if "Champion Deck Display" in n]
        self.assertEqual(len(champion), 7)

    def test_os_dois_showdown_display_continuam_conhecidos(self):
        nomes = [x["nome"] for x in self.arquivados()]
        showdown = [n for n in nomes if "Showdown Decks Display" in n]
        self.assertEqual(len(showdown), 2)

    def test_os_nomes_dobrados_nao_se_escreveram(self):
        """O bug reportado não existia: o bruto («… Set Set») casa pelo nome
        limpo, e escrevê-lo também era uma segunda linha para o mesmo produto
        — que passaria a REBENTAR no dia em que o CardTrader corrigisse o
        nome. Ver `TestOsTrialDeckSetJaEstavamFora`."""
        for n in ("2024 Trial Deck Set Set", "2025 Trial Deck Set Set"):
            self.assertNotIn(n, self.sel["excluidos"], n)


# ---------------------------------------------------------------------------
# 3. Os onze contra o CATÁLOGO REAL — é aqui que se prova o que ele vai ver
# ---------------------------------------------------------------------------


class RealBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ["RIFTVAULT_CONFIG"] = str(REPO / "riftvault_config.json")
        from riftvault import config, selado
        importlib.reload(config)
        config.load.cache_clear()
        importlib.reload(selado)
        cls.selado, cls.config = selado, config
        cls.cfg = config.load()
        cls.lista = selado.itens(None, cls.cfg)
        cls.nomes = {x["nome"] for x in cls.lista}
        cls.tirados = {x["nome"]: x for x in selado.excluidos(cls.cfg)}
        cls.crus = {p["id"]: p for p in selado._crus(cls.cfg, com_excluidos=True)}

    @classmethod
    def tearDownClass(cls):
        os.environ["RIFTVAULT_CONFIG"] = str(
            Path(tempfile.gettempdir()) / "riftvault-nao-existe.json")
        importlib.reload(cls.config)
        cls.config.load.cache_clear()


class TestOsOnzeContraOCatalogoReal(RealBase):
    def test_cada_um_dos_onze_casa_com_um_produto(self):
        for n in OS_ONZE:
            self.assertIn(n, self.tirados, f"{n} não casou com nenhum produto")

    def test_os_onze_sairam_da_aba(self):
        for n in OS_ONZE:
            self.assertNotIn(n, self.nomes, f"{n} tinha de ter saído")

    def test_os_onze_sao_todos_da_categoria_262(self):
        for n in OS_ONZE:
            self.assertEqual(self.crus[self.tirados[n]["id"]]["categoria_id"], 262, n)

    def test_nao_ficou_nenhum_champion_deck_do_cardtrader(self):
        """Na aba só podem sobrar os 7 displays, que vêm do config."""
        maus = sorted(x["nome"] for x in self.lista
                      if "champion deck" in x["nome"].lower()
                      and x["fonte"] != "config")
        self.assertEqual(maus, [])

    def test_os_sete_displays_nao_sairam_por_esta_ordem(self):
        """A prova de «o nome é EXACTO»: o nome de cada um dos 11 está
        literalmente DENTRO do nome do display dele, e os displays não foram
        atrás. Saíram da aba a 28/09, por outra porta — nunca pela lista.

        (A aba já não os mostra, por isso a pergunta faz-se ao config.)"""
        arq = json.loads(
            (REPO / "riftvault_config.json").read_text(encoding="utf-8"))
        for n in OS_SETE_DISPLAYS:
            self.assertNotIn(n, arq["selado"]["excluidos"], n)
        self.assertEqual(len(OS_SETE_DISPLAYS), 7)

    def test_ficam_os_dois_showdown_deck(self):
        ficam = sorted(x["nome"] for x in self.lista
                       if "showdown deck" in x["nome"].lower()
                       and "display" not in x["nome"].lower())
        self.assertEqual(ficam, sorted(OS_DOIS_SHOWDOWN))

    def test_os_dois_showdown_display_nao_sairam_por_esta_ordem(self):
        arq = json.loads(
            (REPO / "riftvault_config.json").read_text(encoding="utf-8"))
        nomes = [x["nome"] for x in arq["_selado_extra_arquivado"]["produtos"]]
        showdown = [n for n in nomes if "Showdown Decks Display" in n]
        self.assertEqual(len(showdown), 2)
        for n in showdown:
            self.assertNotIn(n, arq["selado"]["excluidos"])

    def test_a_aba_fica_com_32_selados(self):
        """Os 11 desta ordem levaram-na de 66 a 55; os 7 sem mercado, na mesma
        noite, a 48 (ver `test_selado_sem_mercado`); e a 28/09 os 17 do
        `selado.extra`, menos os 2 que voltaram e o chinês que saiu, a 32
        (`test_selado_ingles`)."""
        selados = [x for x in self.lista if not x["acessorio"]]
        self.assertEqual(len(selados), 32,
                         "98 − 22 − 10 − 11 − 7 − 17 − 1 + 2")

    def test_por_edicao_depois_dos_onze(self):
        """Os números que ele vai ver, edição a edição. Desta ordem mexem
        quatro: OGN 8→5, SFD 8→6, UNL 10→8, LGC 6→2; a OP, a PROMO-RIFT e a
        T1S mexeram com os 7 sem mercado, a seguir."""
        por = {}
        for x in self.lista:
            if not x["acessorio"]:
                por[x["edicao"]] = por.get(x["edicao"], 0) + 1
        self.assertEqual(por, {"OGN": 2, "OGS": 1, "SFD": 3, "UNL": 5, "VEN": 5,
                               "RAD": 4, "LGC": 2, "PG2": 1, "REC": 1, "ARC": 1,
                               "PROMO-RIFT": 6, "T1S": 1})
        self.assertEqual(sum(por.values()), 32)

    def test_a_legacy_fica_so_com_os_por_sair_que_nao_sao_champion(self):
        """Eram 6: saem os 4 Champion Deck."""
        lgc = sorted(x["nome"] for x in self.lista if x["edicao"] == "LGC")
        self.assertEqual(len(lgc), 2)
        for n in lgc:
            self.assertNotIn("champion deck", n.lower())

    def test_saem_exactamente_49_e_cada_nome_casa_com_um(self):
        ex = self.selado.excluidos(self.cfg)
        self.assertEqual(len(ex), 49)
        self.assertEqual(len({x["id"] for x in ex}), 49)

    def test_ler_nao_escreve(self):
        antes = (REPO / "data" / "selado_catalogo.json").read_bytes()
        self.selado.itens(None, self.cfg)
        self.assertEqual((REPO / "data" / "selado_catalogo.json").read_bytes(), antes)


# ---------------------------------------------------------------------------
# 4. Nenhuma exclusão morta — o guarda que faltava
# ---------------------------------------------------------------------------


class TestNenhumaExclusaoMorta(RealBase):
    """*«Há mais nomes na `selado.excluidos` que não casam com nada?»*

    Uma entrada que não casa não está a esconder produto nenhum: ou é um erro
    de escrita, ou é um produto que o CardTrader tirou do catálogo. O
    `_resolver_excluidos` rebenta nesse caso — mas só quando alguém lhe pede o
    payload, e o `tolerante` cala-o quando não há catálogo em disco. Este
    teste faz a pergunta de frente, para a lista INTEIRA.
    """

    def test_todas_as_entradas_casam_com_um_produto(self):
        self.assertEqual(len(self.tirados), len(self.cfg["selado"]["excluidos"]))

    def test_nenhuma_entrada_fica_por_casar(self):
        por_nome = {}
        for p in self.crus.values():
            for n in (p["nome"], p.get("nome_bruto")):
                if n:
                    por_nome.setdefault(self.selado._chave_nome(n), []).append(p)
        mortas = [e for e in self.cfg["selado"]["excluidos"]
                  if e not in self.crus
                  and not por_nome.get(self.selado._chave_nome(e))]
        self.assertEqual(mortas, [], "exclusões que não estão a tirar nada")

    def test_nenhuma_entrada_e_ambigua(self):
        por_nome = {}
        for p in self.crus.values():
            for n in (p["nome"], p.get("nome_bruto")):
                if n:
                    por_nome.setdefault(self.selado._chave_nome(n), []).append(p)
        for e in self.cfg["selado"]["excluidos"]:
            ids = {p["id"] for p in por_nome.get(self.selado._chave_nome(e), [])}
            if e not in self.crus:
                self.assertEqual(len(ids), 1, f"{e!r} casa com {sorted(ids)}")

    def test_uma_entrada_morta_rebenta(self):
        """A prova pela negativa: se o guarda não valesse nada, isto passava."""
        cfg = json.loads(json.dumps(self.cfg))
        cfg["selado"]["excluidos"] = list(cfg["selado"]["excluidos"]) + ["Nao Existe Isto"]
        with self.assertRaises(ValueError):
            self.selado.itens(None, cfg)


class TestOsTrialDeckSetJaEstavamFora(RealBase):
    """O bug reportado a 26/09 («dois Trial Deck Set visíveis por o nome não
    bater») NÃO EXISTE: o catálogo escreve-os com a palavra dobrada e a lista
    escreve o nome limpo, mas o `_resolver_excluidos` casa pelas DUAS. Estão
    fora desde 25/09. Fica aqui a prova, pela forma exacta em que ele o
    perguntou."""

    def test_o_catalogo_escreve_os_nomes_dobrados(self):
        for pid, bruto in (("ct-383046", "2024 Trial Deck Set Set"),
                           ("ct-383045", "2025 Trial Deck Set Set")):
            self.assertEqual(self.crus[pid]["nome_bruto"], bruto)

    def test_a_lista_escreve_o_nome_limpo(self):
        for n in ("2024 Trial Deck Set", "2025 Trial Deck Set"):
            self.assertIn(n, self.cfg["selado"]["excluidos"])

    def test_e_mesmo_assim_casam_e_estao_fora(self):
        self.assertEqual(self.tirados["2024 Trial Deck Set"]["id"], "ct-383046")
        self.assertEqual(self.tirados["2025 Trial Deck Set"]["id"], "ct-383045")

    def test_nao_estao_visiveis_na_aba(self):
        maus = sorted(n for n in self.nomes if "trial deck" in n.lower())
        self.assertEqual(maus, [])


# ---------------------------------------------------------------------------
# 5. A fotografia — nada da Coleção mexe
# ---------------------------------------------------------------------------


class TestNaoMexeEmNadaDaColecao(ChampionBase):
    """A MESMA fotografia do `test_selado`, por referência: não há duas
    definições de «número da Coleção»."""

    fotografia = _Foto.fotografia

    def test_tirar_os_champion_deck_nao_mexe_em_nada(self):
        con = self.catalogo()
        self.cfg_selado({})
        antes = self.fotografia(con)
        self.selado.ajustar(con, "ct-703", 2, source="test")   # o showdown, que fica
        self.cfg_selado({"excluidos": [DECK]})
        self.assertEqual(self.fotografia(con), antes)
        self.cfg_selado({"excluidos": []})        # e repor também não
        self.assertEqual(self.fotografia(con), antes)

    def test_a_fotografia_nao_e_de_zeros(self):
        """Um teste de igualdade sobre nada não prova nada."""
        f = self.fotografia(self.catalogo())
        self.assertGreater(f["valor"]["cents"], 0)
        self.assertTrue(f["denominador"])
        self.assertTrue(f["copies"])


if __name__ == "__main__":
    unittest.main()

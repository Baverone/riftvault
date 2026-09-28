"""Tirar mais dois grupos do «Produto Selado», e desligar os acessórios
(André, 2026-09-25, à noite — a segunda ordem do mesmo dia).

Depois de ver a lista com os 22 já fora, ele mandou tirar mais 10 e desligar a
secção dos acessórios inteira. NÃO HÁ MECANISMO NOVO: é a mesma
`selado.excluidos` da ordem anterior (22 → 32) e a `selado.acessorios` a ficar
VAZIA. Este ficheiro fixa as três coisas que a ordem exige.

1. OS 10 QUE SAEM, pelo nome exacto
   - os 2 «Card Set» da categoria «Riftbound Complete Sets» (283) — são
     conjuntos de CARTAS, não produto selado: «Unleashed: Poro Scene Set» e
     «Arcane Complete Set». Com eles, a categoria fica VAZIA na aba;
   - os 8 TRIAL DECK, todos na PROMO-RIFT: os 4 «Origins: X Trial Deck»
     (Jinx, Viktor, Volibear, Yasuo), os 2 «Trial Deck Set» e os 2 «Trial
     Deck Case».

   Escreve-se o nome LIMPO («2024 Trial Deck Set»), que é o que está no ecrã
   desde a ordem anterior; o bruto do CardTrader («… Set Set») casa na mesma.

2. O QUE **NÃO** SAI, e é onde é fácil enganar-se
   Os nomes parecem-se, mas **não sai nada de «Box Sets & Displays» por ser
   dessa categoria**: ficam o «Arcane Box Set» (a caixa de coleccionador), o
   «Arcane Chinese Promo Set», o «The T1 Worlds Champion | Signature Edition
   Box Set», o «Origins: Proving Grounds Box Set Case», o «Origins: Instant
   Match Box 2025» e a «Secret Garden Bundle Box». O critério é o NOME de cada
   um dos 10, nunca a categoria nem um pedaço do nome.

   A EXCEPÇÃO, dita à letra na ordem: os dois «Trial Deck Case» são da 263 e
   SAEM na mesma — ele nomeou-os um a um no grupo dos Trial Deck. O que a
   ordem proíbe é tirar a categoria 263 em bloco, não estes dois.

3. OS ACESSÓRIOS DESLIGADOS — `selado.acessorios: []`
   Esvazia-se a lista; **não se apaga nem a chave nem o código da secção**. As
   19 linhas (10 binders + 9 deck boxes) desaparecem da página, e as duas
   categorias voltam ao `fora`, contadas. REPOR É ESCREVER OS NÚMEROS OUTRA
   VEZ — e há teste que o faz.

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

from tests.test_selado import APP_JS, CATALOGO, Base  # noqa: E402
from tests.test_selado import TestNaoEntraNaColecao as _Foto  # noqa: E402

REPO = Path(__file__).resolve().parent.parent

# OS DEZ, tal como ficam escritos no `riftvault_config.json`.
OS_DOIS_CARD_SET = ["Unleashed: Poro Scene Set", "Arcane Complete Set"]
OS_OITO_TRIAL_DECK = [
    "Origins: Jinx Trial Deck", "Origins: Viktor Trial Deck",
    "Origins: Volibear Trial Deck", "Origins: Yasuo Trial Deck",
    "2024 Trial Deck Set", "2025 Trial Deck Set",
    "2024 Trial Deck Case", "2025 Trial Deck Case",
]
OS_DEZ = OS_DOIS_CARD_SET + OS_OITO_TRIAL_DECK

# O QUE FICA, um a um — os nomes que se parecem com os de cima. O que interessa
# aqui é que ESTA ordem não lhes tocou.
TEM_DE_FICAR = [
    "Arcane Box Set",
    "The T1 Worlds Champion | Signature Edition Box Set",
    "Secret Garden Bundle Box",
]
# Ficaram por esta ordem e saíram por OUTRAS, depois — continuam a não ser dos
# 10, que é o que este ficheiro fixa. O «Arcane Chinese Promo Set» saiu a
# 2026-09-28, pela regra da língua (*"nao quero nada que nao seja impressao
# Inglesa"*); o «Origins: Proving Grounds Box Set Case» era um dos 17 do
# `selado.extra`, que saíram da aba no mesmo dia por não terem página própria.
FICARAM_AQUI_SAIRAM_DEPOIS = [
    "Arcane Chinese Promo Set",
    "Origins: Proving Grounds Box Set Case",
]

# O «Origins: Instant Match Box 2025» estava nesta lista — ele não o nomeou
# nesta ordem e ficou. Saiu HORAS DEPOIS, na dos 7 sem mercado (sem
# `cardmarket_id` e zero ofertas no CardTrader — ver `test_selado_sem_mercado`),
# e por isso deixou de poder ser o exemplo de «parecido que fica». O que este
# ficheiro prova continua de pé pelos outros cinco: tira-se por NOME, nunca
# por categoria.
SAIU_DEPOIS = "Origins: Instant Match Box 2025"

# O catálogo de brincar do `test_selado`, mais um binder e um deck box (as duas
# categorias de acessório que esta ordem desliga) e um segundo «Complete Set».
CAT = json.loads(json.dumps(CATALOGO))
CAT["categorias"]["265"] = "Riftbound Albums"
CAT["categorias"]["267"] = "Riftbound Deck Boxes"
CAT["produtos"] += [
    {"blueprint_id": 601, "nome": '9-Pocket "Teste" Binder', "versao": "",
     "categoria_id": 265, "edicao": "TST", "edicao_nome": "Teste",
     "img": None, "cardmarket_id": None},
    {"blueprint_id": 602, "nome": '"Teste" Deck Box', "versao": "",
     "categoria_id": 267, "edicao": "TST", "edicao_nome": "Teste",
     "img": None, "cardmarket_id": None},
    {"blueprint_id": 603, "nome": "Teste Complete Set", "versao": "6 Card Set",
     "categoria_id": 283, "edicao": "TST", "edicao_nome": "Teste",
     "img": None, "cardmarket_id": None},
    # Um par para o «o nome é exacto»: o «Teste Trial Deck Case» sai e o
    # «Teste Trial Deck Case Display» fica.
    {"blueprint_id": 604, "nome": "Teste Trial Deck Case", "versao": "",
     "categoria_id": 263, "edicao": "TST", "edicao_nome": "Teste",
     "img": None, "cardmarket_id": None},
    {"blueprint_id": 605, "nome": "Teste Trial Deck Case Display", "versao": "",
     "categoria_id": 263, "edicao": "TST", "edicao_nome": "Teste",
     "img": None, "cardmarket_id": None},
]
CAT["precos"]["601"] = {"cents": 3399, "currency": "EUR", "day": "2026-09-25",
                        "n_listings": 4, "n_sellers": 4, "n_copies": 4}
CAT["precos"]["602"] = {"cents": 1200, "currency": "EUR", "day": "2026-09-25",
                        "n_listings": 2, "n_sellers": 2, "n_copies": 2}
CAT["precos"]["603"] = {"cents": 5000, "currency": "EUR", "day": "2026-09-25",
                        "n_listings": 1, "n_sellers": 1, "n_copies": 1}

ACESSORIOS = [265, 267]


class Tirar2Base(Base):
    def setUp(self):
        super().setUp()
        self.escrever_catalogo(CAT)

    def payload(self, excluidos=None, acessorios=ACESSORIOS, **kw):
        self.cfg_selado({
            **({"excluidos": excluidos} if excluidos is not None else {}),
            "acessorios": acessorios, **kw})
        return self.selado.payload(self.con())

    def selados(self, **kw):
        return [x for x in self.payload(**kw)["items"] if not x["acessorio"]]

    def nomes(self, **kw):
        return [x["nome"] for x in self.selados(**kw)]


# ---------------------------------------------------------------------------
# 1. Os dez, contra o catálogo REAL
# ---------------------------------------------------------------------------


class TestOsDezContraOCatalogoReal(unittest.TestCase):
    """Os 10 nomes contra o `data/selado_catalogo.json` e o config do repo.

    É aqui que se prova que ele vai ver o que pediu: cada nome casa com UM
    produto, os 6 parecidos ficam, e a categoria «Complete Sets» fica vazia.
    """

    @classmethod
    def setUpClass(cls):
        os.environ["RIFTVAULT_CONFIG"] = str(REPO / "riftvault_config.json")
        from riftvault import config, selado
        importlib.reload(config)
        config.load.cache_clear()
        importlib.reload(selado)
        cls.selado, cls.config = selado, config
        cls.cfg = config.load()
        cls.op = selado.opcoes(cls.cfg)
        cls.lista = selado.itens(None, cls.cfg)
        cls.nomes = {x["nome"] for x in cls.lista}
        cls.tirados = {x["nome"]: x for x in selado.excluidos(cls.cfg)}
        # O `excluidos()` não leva a categoria (é o que a página mostra); para
        # a pergunta «de que categoria saiu cada um» olha-se para os crus.
        cls.crus = {p["id"]: p for p in selado._crus(cls.cfg, com_excluidos=True)}

    def categoria(self, nome):
        """De que categoria saiu um produto.

        Os da 262 (os decks) não chegam ao `_crus` desde 2026-09-28 — a
        categoria saiu das `selado.categorias` e é ela que os tira agora —, por
        isso a pergunta cai para o CATÁLOGO EM DISCO, que os tem todos.
        """
        pid = self.tirados.get(nome, {}).get("id")
        if pid and pid in self.crus:
            return self.crus[pid]["categoria_id"]
        return self.em_disco(nome)["categoria_id"]

    def em_disco(self, nome):
        cat = json.loads(
            (REPO / "data" / "selado_catalogo.json").read_text(encoding="utf-8"))
        for p in cat["produtos"]:
            if self.selado.nome_limpo(p["nome"]) == nome:
                return p
        raise AssertionError(f"{nome!r} não está no catálogo em disco")

    @classmethod
    def tearDownClass(cls):
        os.environ["RIFTVAULT_CONFIG"] = str(
            Path(tempfile.gettempdir()) / "riftvault-nao-existe.json")
        importlib.reload(cls.config)
        cls.config.load.cache_clear()

    def test_cada_um_dos_dez_existe_e_esta_fora(self):
        """Os 2 «Card Set» e os 2 «Trial Deck Case» continuam a sair pelo NOME;
        os 6 Trial Deck da 262 saem desde 2026-09-28 pela CATEGORIA, e por isso
        os nomes deles já não estão na lista — estão no
        `_selado_decks_arquivado`. Todos existem no catálogo e nenhum está na
        aba, que é o que interessa."""
        arq = json.loads(
            (REPO / "riftvault_config.json").read_text(encoding="utf-8"))
        guardados = (arq["_selado_decks_arquivado"]["de_2026_09_25"]
                     + arq["_selado_decks_arquivado"]["de_2026_09_26"])
        for n in OS_DEZ:
            self.em_disco(n)                       # existe no catálogo
            self.assertNotIn(n, self.nomes, n)     # e não está na aba
            self.assertTrue(n in self.tirados or n in guardados,
                            f"{n} saiu sem ficar registado em lado nenhum")

    def test_os_dez_sairam_da_aba(self):
        for n in OS_DEZ:
            self.assertNotIn(n, self.nomes, f"{n} tinha de ter saído")

    def test_os_dois_card_set_sao_a_categoria_283(self):
        """«Complete Sets» — e são só estes dois."""
        for n in OS_DOIS_CARD_SET:
            self.assertEqual(self.categoria(n), 283, n)
        todos_283 = [p for p in self.selado._crus(self.cfg, com_excluidos=True)
                     if p["categoria_id"] == 283]
        self.assertEqual(sorted(p["nome"] for p in todos_283),
                         sorted(OS_DOIS_CARD_SET))

    def test_a_categoria_complete_sets_fica_vazia_na_aba(self):
        self.assertEqual([x for x in self.lista if x["categoria_id"] == 283], [])

    def test_os_oito_trial_deck_sao_todos_da_promo_rift(self):
        for n in OS_OITO_TRIAL_DECK:
            edicao = (self.tirados[n]["edicao"] if n in self.tirados
                      else (self.em_disco(n).get("edicao") or "").upper())
            self.assertEqual(edicao, "PROMO-RIFT", n)

    def test_os_quatro_origins_trial_deck_sao_os_blueprints_vivos(self):
        """Os 330845..330848 são duplicados dos 3631xx (o `juntar_duplicados`
        junta-os, e as ofertas dizem qual é o vivo).

        Desde 2026-09-28 os seis da 262 já não passam pelo `excluidos`, por
        isso a pergunta faz-se ao catálogo: os pares continuam lá, e o vivo
        continua a ser o 3631xx."""
        for q, vivo, morto in (("Jinx", 363136, 330845), ("Viktor", 363137, 330846),
                               ("Volibear", 363138, 330848), ("Yasuo", 363139, 330847)):
            nome = f"Origins: {q} Trial Deck"
            ids = sorted(p["blueprint_id"] for p in self.todos_em_disco(nome))
            self.assertEqual(ids, sorted([vivo, morto]), nome)

    def todos_em_disco(self, nome):
        cat = json.loads(
            (REPO / "data" / "selado_catalogo.json").read_text(encoding="utf-8"))
        return [p for p in cat["produtos"]
                if self.selado.nome_limpo(p["nome"]) == nome]

    def test_o_nome_limpo_e_o_que_casa_nos_trial_deck_set(self):
        """No catálogo estão «2024 Trial Deck Set Set»; escreve-se o limpo — e
        é esse que foi para o `_selado_decks_arquivado` a 2026-09-28."""
        self.assertEqual(self.em_disco("2024 Trial Deck Set")["blueprint_id"], 383046)
        self.assertEqual(self.em_disco("2025 Trial Deck Set")["blueprint_id"], 383045)
        arq = json.loads(
            (REPO / "riftvault_config.json").read_text(encoding="utf-8"))
        for n in ("2024 Trial Deck Set", "2025 Trial Deck Set"):
            self.assertIn(n, arq["_selado_decks_arquivado"]["de_2026_09_25"])

    def test_nao_ficou_nenhum_trial_deck_na_aba(self):
        maus = [n for n in self.nomes if "trial deck" in n.lower()]
        self.assertEqual(maus, [])

    def test_os_parecidos_ficam(self):
        """A parte da ordem em que é fácil enganar-se — um a um."""
        for n in TEM_DE_FICAR:
            self.assertIn(n, self.nomes, f"{n} tinha de ficar")

    def test_os_que_sairam_depois_nao_sairam_por_esta_ordem(self):
        """Já não estão na aba, mas não é esta a ordem que os tirou — e é isso
        que este ficheiro guarda."""
        for n in FICARAM_AQUI_SAIRAM_DEPOIS:
            self.assertNotIn(n, OS_DEZ)

    def test_nao_saiu_nada_de_box_sets_por_ser_dessa_categoria(self):
        """Destes 10, da 263 saem exactamente os dois «Trial Deck Case» — que
        ele nomeou um a um. É a diferença entre tirar por NOME e tirar a
        categoria: a 263 tem 15 produtos e ficam lá 12.

        (O terceiro que falta à conta é a «Spiritforged Bulk Runes», também da
        263 — mas essa saiu na ordem ANTERIOR, e não é desta.)
        """
        meus_da_263 = sorted(n for n in OS_DEZ if self.categoria(n) == 263)
        self.assertEqual(meus_da_263,
                         ["2024 Trial Deck Case", "2025 Trial Deck Case"])
        # E os que ele nomeou para ficar, todos da 263, continuam lá. (O
        # «Arcane Chinese Promo Set», que também é da 263, saiu a 28/09 pela
        # regra da língua — não por ser desta categoria.)
        for n in ("Arcane Box Set",
                  "The T1 Worlds Champion | Signature Edition Box Set",
                  "Secret Garden Bundle Box"):
            self.assertIn(n, self.nomes, n)
        # E o que saiu da 263 não saiu por ser da 263: o `SAIU_DEPOIS` foi-se
        # na ordem seguinte, por não ter mercado em lado nenhum.
        self.assertNotIn(SAIU_DEPOIS, OS_DEZ)

    def test_a_aba_fica_com_30_selados(self):
        """Estes 10 levaram-na de 76 a 66; os 11 Champion Deck a 55, os 7 sem
        mercado a 48, a 28/09 os 17 do `selado.extra` (menos os 2 que voltaram
        e o chinês que saiu) a 32, e nessa noite os 2 Showdown Deck, com a
        categoria 262, a **30**. Ver `test_selado_champion`,
        `test_selado_sem_mercado`, `test_selado_ingles` e
        `test_selado_sem_decks`."""
        selados = [x for x in self.lista if not x["acessorio"]]
        self.assertEqual(len(selados), 30, "98 − 22 − 10 − 11 − 7 − 17 − 1 + 2 − 2")

    def test_por_edicao_depois_dos_dez(self):
        """Os números que ele vai ver, edição a edição (a 2026-09-28, à noite)."""
        por = {}
        for x in self.lista:
            if not x["acessorio"]:
                por[x["edicao"]] = por.get(x["edicao"], 0) + 1
        self.assertEqual(por, {"OGN": 2, "OGS": 1, "SFD": 3, "UNL": 5, "VEN": 4,
                               "RAD": 3, "LGC": 2, "PG2": 1, "REC": 1, "ARC": 1,
                               "PROMO-RIFT": 6, "T1S": 1})
        self.assertEqual(sum(por.values()), 30)

    def test_a_promo_rift_fica_com_seis(self):
        """Eram 18: saíram os 8 Trial Deck desta ordem, e depois os 5 sem
        mercado (o Promo Pack, o Arcane Promo Pack, o Immersive, o Replacement
        Card Booster e o Instant Match Box). O **Replacement Card Booster
        voltou** a 28/09, quando o Cardmarket lhe revelou oferta a 35,00 €."""
        pr = [x["nome"] for x in self.lista if x["edicao"] == "PROMO-RIFT"]
        self.assertEqual(sorted(pr), [
            "Gift of the Rift Bundle", "Lunar Revel 2026 Bundle",
            "Origins | Nexus Night Promo Booster", "Replacement Card Booster",
            "Riftbound Worlds Bundle 2025", "Secret Garden Bundle Box"])

    def test_a_arc_fica_com_uma(self):
        """Eram 3: saiu o «Arcane Complete Set» por esta ordem e ficavam a
        caixa e o promo set; o promo set saiu a 28/09, por ser chinês."""
        arc = sorted(x["nome"] for x in self.lista if x["edicao"] == "ARC")
        self.assertEqual(arc, ["Arcane Box Set"])

    def test_os_acessorios_nao_dao_linha_nenhuma(self):
        self.assertEqual([x for x in self.lista if x["acessorio"]], [])

    def test_as_duas_categorias_de_acessorio_voltaram_ao_fora(self):
        """Contadas, nunca apagadas em silêncio."""
        fora = {f["categoria_id"]: f["n"] for f in self.selado.fora(self.cfg)}
        self.assertEqual(fora.get(265), 10, "os binders")
        self.assertEqual(fora.get(267), 9, "os deck boxes")

    def test_ler_nao_escreve(self):
        antes = (REPO / "data" / "selado_catalogo.json").read_bytes()
        self.selado.payload(None, self.cfg, editable=False)
        self.assertEqual((REPO / "data" / "selado_catalogo.json").read_bytes(), antes)


# ---------------------------------------------------------------------------
# 2. O config real
# ---------------------------------------------------------------------------


class TestOConfigReal(unittest.TestCase):
    """Lê o `riftvault_config.json` do repo. Não abre base nenhuma."""

    @classmethod
    def setUpClass(cls):
        cls.sel = json.loads(
            (REPO / "riftvault_config.json").read_text(encoding="utf-8"))["selado"]

    def test_a_lista_tem_31_sem_repetidos(self):
        """22 (25/09, manhã) + 10 (25/09, noite) + 11 Champion Deck (26/09)
        + 7 sem mercado (26/09) − 2 que voltaram + 1 chinês (28/09) = 49;
        **menos os 18 decks que ficaram redundantes** na noite de 28/09, quando
        a categoria 262 saiu (`test_selado_sem_decks`)."""
        self.assertEqual(len(self.sel["excluidos"]), 31)
        self.assertEqual(len(set(self.sel["excluidos"])), 31)

    def test_os_dez_continuam_fora_pela_lista_ou_pelo_arquivo(self):
        """Dos 10 desta ordem, os 4 que NÃO são da 262 (os 2 «Card Set» e os 2
        «Trial Deck Case») continuam na lista; os 6 Trial Deck da 262 passaram
        para o `_selado_decks_arquivado` a 28/09, por redundantes."""
        arq = json.loads(
            (REPO / "riftvault_config.json").read_text(encoding="utf-8"))
        guardados = arq["_selado_decks_arquivado"]["de_2026_09_25"]
        na_lista = [n for n in OS_DEZ if n in self.sel["excluidos"]]
        no_arquivo = [n for n in OS_DEZ if n in guardados]
        self.assertEqual(sorted(na_lista),
                         sorted(OS_DOIS_CARD_SET
                                + ["2024 Trial Deck Case", "2025 Trial Deck Case"]))
        self.assertEqual(len(no_arquivo), 6)
        self.assertEqual(sorted(na_lista + no_arquivo), sorted(OS_DEZ))

    def test_os_22_da_ordem_anterior_continuam_la(self):
        """Acrescentar não é reescrever: a lista dele de manhã fica inteira."""
        # O «Unleashed Sleeved Booster» era um dos 22 e **VOLTOU** a 2026-09-28,
        # quando o Cardmarket lhe revelou oferta a 13,00 € — é inglês, e
        # «sleeved» é embalagem, não língua. Saiu desta lista por isso.
        for n in ("Origins Booster", "Origins Sleeved Booster", "Origins Slim Booster",
                  "Spiritforged Booster", "Spiritforged Slim Booster",
                  "Unleashed Booster",
                  "Unleashed Slim Booster", "Vendetta Booster", "Radiance Booster",
                  "Radiance Sleeved Booster", "Legacy Booster",
                  "The Reckoning Booster", "Origins Slim Booster Box",
                  "Spiritforged Slim Booster Box", "Unleashed Slim Booster Box",
                  "Spiritforged Bulk Runes",
                  "Spiritforged Pre-Rift Kit", "Unleashed Pre-Rift Kit",
                  "Vendetta Pre-Rift Kit", "Radiance Pre-Rift Kit"):
            self.assertIn(n, self.sel["excluidos"])
        # O «Origins: Champion Deck Set» era o vigésimo segundo e saiu da lista
        # a 2026-09-28 por ser da 262 — a decisão dele («compram-se à unidade»)
        # está no `_selado_decks_arquivado`.
        arq = json.loads(
            (REPO / "riftvault_config.json").read_text(encoding="utf-8"))
        self.assertIn("Origins: Champion Deck Set",
                      arq["_selado_decks_arquivado"]["de_2026_09_25"])

    def test_nenhum_dos_que_ficam_foi_parar_a_lista(self):
        for n in TEM_DE_FICAR:
            self.assertNotIn(n, self.sel["excluidos"])

    def test_o_que_saiu_depois_saiu_por_outra_razao(self):
        """O `SAIU_DEPOIS` está hoje na lista, mas não por esta ordem: não é
        um dos 10, e a sua entrada veio da dos 7 sem mercado."""
        self.assertNotIn(SAIU_DEPOIS, OS_DEZ)
        self.assertIn(SAIU_DEPOIS, self.sel["excluidos"])

    def test_os_acessorios_estao_vazios_e_a_chave_ficou(self):
        """Esvaziar, não apagar — é o que deixa repor sem mexer em código."""
        self.assertIn("acessorios", self.sel)
        self.assertEqual(self.sel["acessorios"], [])

    def test_a_283_continua_em_categorias(self):
        """O ponto desta ordem: os dois «Card Set» saíram por NOME, e a 283 fica
        — se um «Complete Set» novo aparecer, ele vê-o. (A 262 é outra história:
        saiu a 2026-09-28, e aí a decisão foi mesmo tirar a categoria —
        `test_selado_sem_decks`.)"""
        self.assertIn(283, self.sel["categorias"])
        self.assertEqual(self.sel["categorias"], [259, 260, 261, 263, 283])


# ---------------------------------------------------------------------------
# 3. Os acessórios desligados, e repor
# ---------------------------------------------------------------------------


class TestOsAcessoriosDesligados(Tirar2Base):

    def test_com_a_lista_vazia_nao_ha_acessorios(self):
        p = self.payload(acessorios=[])
        self.assertEqual([x for x in p["items"] if x["acessorio"]], [])
        self.assertEqual(p["acessorios"]["totals"]["ha"], 0)
        self.assertEqual(p["acessorios"]["sets"], [])
        self.assertEqual(p["acessorios"]["categorias"], [])

    def test_o_selado_nao_mexe_quando_os_acessorios_saem(self):
        """Eles já não contavam para o selado; tirá-los não podia mexer lá."""
        com = self.payload(acessorios=ACESSORIOS)["totals"]
        sem = self.payload(acessorios=[])["totals"]
        self.assertEqual(com, sem)

    def test_as_categorias_voltam_ao_fora_contadas(self):
        fora_com = {f["categoria_id"]: f["n"] for f in
                    self.selado_fora(ACESSORIOS)}
        fora_sem = {f["categoria_id"]: f["n"] for f in self.selado_fora([])}
        self.assertNotIn(265, fora_com)
        self.assertEqual(fora_sem.get(265), 1)
        self.assertEqual(fora_sem.get(267), 1)

    def selado_fora(self, acessorios):
        self.cfg_selado({"acessorios": acessorios})
        return self.selado.fora()

    def test_repor_e_escrever_os_numeros_outra_vez(self):
        self.assertEqual(self.payload(acessorios=[])["acessorios"]["totals"]["ha"], 0)
        de_volta = self.payload(acessorios=ACESSORIOS)
        nomes = [x["nome"] for x in de_volta["items"] if x["acessorio"]]
        self.assertEqual(sorted(nomes), ['"Teste" Deck Box', '9-Pocket "Teste" Binder'])
        self.assertEqual(de_volta["acessorios"]["totals"]["ha"], 2)

    def test_a_unidade_gravada_num_acessorio_nao_se_apaga(self):
        """Desligar a lista não é apagar o que ele tinha contado: volta ao
        repor, como o `selado.excluidos`."""
        self.cfg_selado({"acessorios": ACESSORIOS})
        con = self.con()
        self.selado.ajustar(con, "ct-601", 2, source="test")
        self.cfg_selado({"acessorios": []})
        self.assertEqual([x for x in self.selado.itens(con) if x["acessorio"]], [])
        self.cfg_selado({"acessorios": ACESSORIOS})
        volta = [x for x in self.selado.itens(con) if x["id"] == "ct-601"]
        self.assertEqual(volta[0]["qty"], 2)

    def test_o_codigo_da_seccao_ficou(self):
        """Esvaziar a lista não apaga a secção: o `app.js` continua a saber
        desenhá-la, e é isso que faz de repor uma linha de config."""
        js = APP_JS.read_text(encoding="utf-8")
        self.assertIn("sl-acess-cab", js)
        self.assertIn("p.acessorios", js)

    def test_a_seccao_so_se_desenha_quando_ha_acessorios(self):
        """Com a lista vazia não pode aparecer um cabeçalho «Acessórios» com
        zero linhas, nem o botão de filtro."""
        js = APP_JS.read_text(encoding="utf-8")
        self.assertIn("ac.totals.ha", js)
        self.assertIn("at.ha ?", js)


# ---------------------------------------------------------------------------
# 4. Repor um dos dez é tirar o nome da lista
# ---------------------------------------------------------------------------


class TestReporESoTirarDaLista(Tirar2Base):

    def test_o_card_set_volta_ao_tirar_o_nome(self):
        self.assertNotIn("Teste: Poro Scene Set",
                         self.nomes(excluidos=["Teste: Poro Scene Set"]))
        self.assertIn("Teste: Poro Scene Set", self.nomes(excluidos=[]))

    def test_o_catalogo_em_disco_fica_intacto(self):
        antes = self.config.SELADO_PATH.read_bytes()
        self.payload(excluidos=["Teste: Poro Scene Set", "Teste Trial Deck Case"])
        self.assertEqual(self.config.SELADO_PATH.read_bytes(), antes)

    def test_o_nome_e_exacto_e_nao_um_pedaco(self):
        """O «Teste Trial Deck Case» sai; o «… Case Display» fica."""
        nomes = self.nomes(excluidos=["Teste Trial Deck Case"])
        self.assertNotIn("Teste Trial Deck Case", nomes)
        self.assertIn("Teste Trial Deck Case Display", nomes)

    def test_os_dois_card_set_saem_sem_a_categoria_sair(self):
        """Tiram-se os produtos, não a 283: um «Complete Set» novo aparece."""
        nomes = self.nomes(excluidos=["Teste: Poro Scene Set", "Teste Complete Set"])
        self.assertNotIn("Teste: Poro Scene Set", nomes)
        self.assertNotIn("Teste Complete Set", nomes)
        self.assertIn(283, self.selado.opcoes(self.config.load())["categorias"])

    def test_o_scope_diz_quais_sairam(self):
        p = self.payload(excluidos=["Teste: Poro Scene Set"])
        ex = p["scope"]["excluidos"]
        self.assertEqual([x["nome"] for x in ex], ["Teste: Poro Scene Set"])
        self.assertEqual(ex[0]["edicao"], "TST")

    def test_um_nome_que_nao_case_rebenta(self):
        with self.assertRaises(ValueError) as e:
            self.payload(excluidos=["Trial Deck Que Nao Existe"])
        self.assertIn("Trial Deck Que Nao Existe", str(e.exception))


# ---------------------------------------------------------------------------
# 5. A FOTOGRAFIA: nada disto mexe num número da Coleção
# ---------------------------------------------------------------------------


class TestNaoMexeNaColecao(Tirar2Base):
    """A defesa de sempre — a das cópias próprias (21/09), a do foil (22/09), a
    da Venda (25/09) e a da ordem anterior. Tirar produtos e desligar os
    acessórios é APRESENTAÇÃO: a Coleção tem de dar exactamente o mesmo."""

    # A MESMA fotografia do `test_selado`, por referência: uma segunda cópia
    # dela era uma segunda definição de «número da Coleção».
    fotografia = _Foto.fotografia

    def test_a_fotografia_nao_e_de_zeros(self):
        """Um teste de igualdade sobre nada não prova nada."""
        f = self.fotografia(self.catalogo())
        self.assertGreater(f["valor"]["cents"], 0)
        self.assertTrue(f["denominador"])
        self.assertTrue(f["copies"])

    def test_tirar_os_dez_e_desligar_os_acessorios_nao_mexe_em_nada(self):
        con = self.catalogo()
        self.cfg_selado({"acessorios": ACESSORIOS, "excluidos": []})
        self.selado.ajustar(con, "ct-107", 1, source="test")   # um «Complete Set»
        self.selado.ajustar(con, "ct-601", 2, source="test")   # dois binders
        antes = self.fotografia(con)

        self.cfg_selado({"acessorios": [],
                         "excluidos": ["Teste: Poro Scene Set",
                                       "Teste Trial Deck Case"]})
        self.assertEqual(self.fotografia(con), antes)

        self.cfg_selado({"acessorios": ACESSORIOS, "excluidos": []})
        self.assertEqual(self.fotografia(con), antes)

    def test_o_valor_do_selado_continua_a_nao_se_somar_ao_da_colecao(self):
        con = self.catalogo()
        self.cfg_selado({"acessorios": [], "excluidos": OS_DEZ[:0]})
        valor = self.prices.collection_value(con)["cents"]
        self.selado.ajustar(con, "ct-101", 3, source="test")
        self.assertEqual(self.prices.collection_value(con)["cents"], valor)


if __name__ == "__main__":
    unittest.main(verbosity=2)

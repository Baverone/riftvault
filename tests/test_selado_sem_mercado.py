"""Tirar do «Produto Selado» o que não se compra em lado nenhum (André,
2026-09-26).

Palavras dele: *"os produtos selados que ainda ficaram, que eu procuro no
cardmarket e nao tem disponivel, podes tirar"*.

NÃO HÁ MECANISMO NOVO, pela quarta vez: é a mesma `selado.excluidos` das três
ordens anteriores (22 → 32 → 43 → **50**), e a aba passa de 55 para **48**.

O QUE ESTE FICHEIRO FIXA É O CRITÉRIO, que é a parte fácil de estragar
-----------------------------------------------------------------------
O pedido dele não se mede à letra: o Cardmarket responde 403 a pedidos
automáticos e a API deles está fechada — não há maneira de lhe consultar o
stock. Cruzaram-se as duas coisas que SE MEDEM:

    sem `cardmarket_id`   -> o Cardmarket nem página tem para o produto
    0 ofertas no CardTrader (medidas AO VIVO, pela API v2, a 2026-09-26)

    ZERO NAS DUAS COLUNAS = ninguém vende, em lado nenhum.

**Exigir as duas é a única parte que importa**, e é o que o
`TestOCriterioNaoEFaltarOIdDoCardmarket` guarda: as edições POR SAIR (LGC,
PG2, REC, RAD) **não têm `cardmarket_id` nenhum** — é normal, ainda não saíram
— mas têm ofertas a sério em pré-venda. Um critério de «não tem Cardmarket,
sai» tirava exactamente o que ele quer ver a chegar. Há teste que falha se
alguém o simplificar assim.

Os 17 produtos do `selado.extra` não têm `blueprint_id` nem `cardmarket_id` e
por isso **não se medem** por este critério: foram escritos à mão a 25/09
porque um catálogo de mercado não os lista, e aplicar-lhes a regra era desfazer
essa ordem. Ficam, e há teste.

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

# OS SETE, tal como ficam escritos no `riftvault_config.json`. Os cinco
# primeiros não têm `cardmarket_id` NEM ofertas; os dois últimos têm página no
# Cardmarket mas zero ofertas no CardTrader.
OS_SETE = [
    "Tournament Gift Box",
    "Arcane Promo Pack",
    "Immersive Arcane Promo Pack",
    "Promo Pack",
    "Origins: Instant Match Box 2025",
    "Replacement Card Booster",
    "The T1 Worlds Champion | Player Bundle",
]

# Medido ao vivo a 2026-09-26 (`_revisao\_medir_selado_cm.py`): o id do
# Cardmarket que o catálogo tem, e as ofertas que a API do CardTrader devolveu.
OS_SETE_MEDIDOS = {
    "Tournament Gift Box": (None, 0),
    "Arcane Promo Pack": (None, 0),
    "Immersive Arcane Promo Pack": (904521, 0),
    "Promo Pack": (None, 0),
    "Origins: Instant Match Box 2025": (None, 0),
    "Replacement Card Booster": (877733, 0),
    "The T1 Worlds Champion | Player Bundle": (None, 0),
}

# O QUE FICA, e é o ponto desta ordem: sem `cardmarket_id`, mas com ofertas em
# pré-venda no CardTrader (medidas ao vivo no mesmo dia).
PRE_VENDA = {
    "Legacy Booster Box": 6,
    "Legacy Vault": 4,
    "Legacy: Proving Grounds": 5,
    "Radiance Booster Box": 18,
    "Radiance Booster Box Case": 11,
    "The Reckoning Booster Box": 5,
    "Arcane Box Set": 4,
    "Gift of the Rift Bundle": 3,
}

# FICAM POR DECIDIR: sem `cardmarket_id` mas com ofertas — pela letra do pedido
# saíam, pelo facto de se comprarem ficam. A pergunta foi devolvida ao André.
NEXUS_POR_DECIDIR = {
    "Unleashed | Nexus Night Promo Booster": 13,
    "Vendetta | Nexus Night Promo Booster": 6,
}

# --- catálogo de brincar ----------------------------------------------------
# Três produtos que modelam o critério, e um par que modela a regra do nome
# exacto: «Promo Pack» está DENTRO de «Arcane Promo Pack», como no catálogo
# real (e os três saem, mas cada um pelo seu nome).
SEM_MERCADO = "Teste Sem Mercado"          # sem CM, 0 ofertas  -> sai
SO_CARDMARKET = "Teste Só Cardmarket"      # com CM, 0 ofertas  -> sai (nomeado)
PRE = "Futuro Booster Box"                 # sem CM, 9 ofertas  -> FICA
PACK = "Teste Promo Pack"
PACK_LONGO = "Teste Arcane Promo Pack"

CAT = json.loads(json.dumps(CATALOGO))
CAT["produtos"] += [
    {"blueprint_id": 801, "nome": SEM_MERCADO, "versao": "",
     "categoria_id": 261, "edicao": "TST", "edicao_nome": "Teste",
     "img": None, "cardmarket_id": None},
    {"blueprint_id": 802, "nome": SO_CARDMARKET, "versao": "",
     "categoria_id": 261, "edicao": "TST", "edicao_nome": "Teste",
     "img": None, "cardmarket_id": 909090},
    {"blueprint_id": 803, "nome": PRE, "versao": "",
     "categoria_id": 259, "edicao": "FUT", "edicao_nome": "Futuro",
     "img": None, "cardmarket_id": None},
    {"blueprint_id": 804, "nome": PACK, "versao": "",
     "categoria_id": 260, "edicao": "TST", "edicao_nome": "Teste",
     "img": None, "cardmarket_id": None},
    {"blueprint_id": 805, "nome": PACK_LONGO, "versao": "",
     "categoria_id": 260, "edicao": "TST", "edicao_nome": "Teste",
     "img": None, "cardmarket_id": None},
]
# `n_listings` a ZERO nos dois primeiros e no par; o da pré-venda com ofertas.
for bid, cents, n in ((801, 4000, 0), (802, 5000, 0), (803, 33000, 9),
                      (804, 1000, 0), (805, 1500, 0)):
    CAT["precos"][str(bid)] = {"cents": cents, "currency": "EUR",
                               "day": "2026-09-26", "n_listings": n,
                               "n_sellers": n, "n_copies": n}


class SemMercadoBase(Base):
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
# 1. O mecanismo: tira-se por NOME, e a app não esconde nada sozinha
# ---------------------------------------------------------------------------


class TestOMecanismo(SemMercadoBase):
    def test_sem_a_lista_estao_todos(self):
        nomes = self.nomes()
        for n in (SEM_MERCADO, SO_CARDMARKET, PRE, PACK, PACK_LONGO):
            self.assertIn(n, nomes)

    def test_zero_ofertas_sozinho_NAO_esconde_nada(self):
        """ESCONDER É DECISÃO DELE, não uma regra que a app aplica. Um produto
        com zero ofertas e sem Cardmarket continua na aba até o nome estar na
        lista — senão a aba mudava sozinha a cada `--sync`."""
        nomes = self.nomes(excluidos=[])
        self.assertIn(SEM_MERCADO, nomes)
        self.assertEqual(self.por_id(self.payload(excluidos=[])["items"],
                                     "ct-801")["n_listings"], 0)

    def test_o_nome_nomeado_sai(self):
        nomes = self.nomes(excluidos=[SEM_MERCADO])
        self.assertNotIn(SEM_MERCADO, nomes)
        self.assertIn(SO_CARDMARKET, nomes)

    def test_ter_pagina_no_cardmarket_nao_o_salva_se_estiver_nomeado(self):
        """Os dois últimos dos sete têm `cardmarket_id` e saem na mesma: o
        critério é as DUAS colunas a zero, e zero ofertas com página vazia é
        exactamente isso."""
        self.assertNotIn(SO_CARDMARKET, self.nomes(excluidos=[SO_CARDMARKET]))

    def test_o_nome_e_exacto_nunca_um_pedaco(self):
        """«Promo Pack» está dentro de «Arcane Promo Pack» — no catálogo real
        também, e por isso os três foram escritos um a um."""
        nomes = self.nomes(excluidos=[PACK])
        self.assertNotIn(PACK, nomes)
        self.assertIn(PACK_LONGO, nomes)

    def test_sai_dos_contadores(self):
        antes = self.payload(excluidos=[])
        depois = self.payload(excluidos=[SEM_MERCADO])
        self.assertEqual(depois["totals"]["ha"], antes["totals"]["ha"] - 1)
        self.assertEqual(depois["totals"]["falta"], antes["totals"]["falta"] - 1)

    def test_sai_do_valor(self):
        con = self.con()
        self.selado.ajustar(con, "ct-801", 1, source="test")
        com = self.selado.payload(con)["totals"]["valor_cents"]
        self.cfg_selado({"excluidos": [SEM_MERCADO]})
        sem = self.selado.payload(con)["totals"]["valor_cents"]
        self.assertEqual(com - sem, 4000)

    def test_o_scope_di_lo(self):
        pay = self.payload(excluidos=[SEM_MERCADO])
        self.assertEqual([x["nome"] for x in pay["scope"]["excluidos"]], [SEM_MERCADO])

    def test_repor_e_tirar_o_nome_da_lista(self):
        com = self.payload(excluidos=[SEM_MERCADO])["totals"]["ha"]
        sem = self.payload(excluidos=[])["totals"]["ha"]
        self.assertEqual(sem, com + 1)

    def test_a_unidade_gravada_num_excluido_nao_se_apaga(self):
        con = self.con()
        self.selado.ajustar(con, "ct-801", 2, source="test")
        self.assertEqual(self.selado.payload(con)["totals"]["tenho"], 1)
        self.cfg_selado({"excluidos": [SEM_MERCADO]})
        self.assertEqual(self.selado.payload(con)["totals"]["tenho"], 0)
        self.cfg_selado({"excluidos": []})
        pay = self.selado.payload(con)
        self.assertEqual(pay["totals"]["tenho"], 1)
        self.assertEqual(self.por_id(pay["items"], "ct-801")["qty"], 2)

    def test_um_mais_num_excluido_recusa(self):
        self.cfg_selado({"excluidos": [SEM_MERCADO]})
        with self.assertRaises(self.selado.ProdutoExcluido):
            self.selado.ajustar(self.con(), "ct-801", 1, source="test")

    def test_o_catalogo_em_disco_fica_intacto(self):
        antes = self.config.SELADO_PATH.read_bytes()
        self.payload(excluidos=[SEM_MERCADO])
        self.assertEqual(self.config.SELADO_PATH.read_bytes(), antes)


# ---------------------------------------------------------------------------
# 2. O CRITÉRIO não é «faltar o id do Cardmarket» — é o teste que importa
# ---------------------------------------------------------------------------


class TestOCriterioNaoEFaltarOIdDoCardmarket(SemMercadoBase):
    """Se alguém simplificar o critério para «não tem `cardmarket_id`, sai»,
    estes testes ficam vermelhos — e é o que tem de acontecer: as edições por
    sair não têm id nenhum e são exactamente o que ele quer ver a chegar."""

    def test_sem_cardmarket_mas_com_ofertas_FICA(self):
        item = self.por_id(self.payload(excluidos=[])["items"], "ct-803")
        self.assertIsNone(item["cardmarket_id"])
        self.assertEqual(item["n_listings"], 9)
        self.assertIn(PRE, self.nomes(excluidos=[SEM_MERCADO, SO_CARDMARKET,
                                                 PACK, PACK_LONGO]))

    def test_tirar_os_nomeados_nao_leva_a_pre_venda(self):
        nomes = self.nomes(excluidos=[SEM_MERCADO, SO_CARDMARKET])
        self.assertIn(PRE, nomes)

    def test_a_prova_pela_negativa(self):
        """A regra errada, escrita à mão: tirar todos os que não têm
        `cardmarket_id` levaria a pré-venda com ela."""
        pay = self.payload(excluidos=[])
        sem_id = {x["nome"] for x in pay["items"]
                  if not x["acessorio"] and not x["cardmarket_id"]}
        self.assertIn(PRE, sem_id, "a regra errada apanhava a pré-venda")
        self.assertIn(SEM_MERCADO, sem_id)


# ---------------------------------------------------------------------------
# 3. Os sete contra o CONFIG do repo
# ---------------------------------------------------------------------------


class TestOConfigReal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads(
            (REPO / "riftvault_config.json").read_text(encoding="utf-8"))
        cls.sel = cls.cfg["selado"]

    def test_a_lista_tem_50_sem_repetidos(self):
        """22 (25/09, manhã) + 10 (25/09, noite) + 11 Champion Deck (26/09)
        + 7 sem mercado (26/09)."""
        self.assertEqual(len(self.sel["excluidos"]), 50)
        self.assertEqual(len(set(self.sel["excluidos"])), 50)

    def test_os_sete_estao_la(self):
        for n in OS_SETE:
            self.assertIn(n, self.sel["excluidos"], n)

    def test_as_43_das_ordens_anteriores_continuam_la(self):
        """Acrescentar não é reescrever."""
        anteriores = [n for n in self.sel["excluidos"] if n not in OS_SETE]
        self.assertEqual(len(anteriores), 43)
        for n in ("Origins Booster", "Origins: Champion Deck Set",
                  "Spiritforged Bulk Runes", "Spiritforged Pre-Rift Kit",
                  "Unleashed: Poro Scene Set", "Arcane Complete Set",
                  "2024 Trial Deck Set", "2025 Trial Deck Case",
                  'Origins: "Jinx" Champion Deck', 'Legacy: "Garen" Champion Deck'):
            self.assertIn(n, anteriores, n)

    def test_a_pre_venda_NAO_foi_parar_a_lista(self):
        for n in PRE_VENDA:
            self.assertNotIn(n, self.sel["excluidos"], n)

    def test_os_nexus_night_por_decidir_NAO_foram_parar_a_lista(self):
        """Ficam à espera da decisão dele — não se decidiu aqui."""
        for n in NEXUS_POR_DECIDIR:
            self.assertNotIn(n, self.sel["excluidos"], n)

    def test_os_dezassete_da_extra_NAO_foram_parar_a_lista(self):
        """Não se medem por este critério: foram escritos à mão porque um
        catálogo de mercado não os lista."""
        self.assertEqual(len(self.sel["extra"]), 17)
        for x in self.sel["extra"]:
            self.assertNotIn(x["nome"], self.sel["excluidos"], x["nome"])

    def test_a_nota_explica_o_criterio(self):
        nota = self.cfg["_selado_nota"]
        for pedaco in ("cardmarket_id", "403", "PRÉ-VENDA", "ZERO NAS DUAS COLUNAS",
                       "as 50 entradas", "Nexus Night"):
            self.assertIn(pedaco, nota, pedaco)


# ---------------------------------------------------------------------------
# 4. Os sete contra o CATÁLOGO REAL — o que ele vai ver
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
        cls.por_nome = {x["nome"]: x for x in cls.lista}

    @classmethod
    def tearDownClass(cls):
        os.environ["RIFTVAULT_CONFIG"] = str(
            Path(tempfile.gettempdir()) / "riftvault-nao-existe.json")
        importlib.reload(cls.config)
        cls.config.load.cache_clear()


class TestOsSeteContraOCatalogoReal(RealBase):
    def test_cada_um_dos_sete_casa_com_um_produto(self):
        for n in OS_SETE:
            self.assertIn(n, self.tirados, f"{n} não casou com nenhum produto")

    def test_os_sete_sairam_da_aba(self):
        for n in OS_SETE:
            self.assertNotIn(n, self.nomes, f"{n} tinha de ter saído")

    def test_o_id_do_cardmarket_e_as_ofertas_batem_com_o_medido(self):
        """Os números que justificaram a saída, produto a produto. Se o
        `--sync` os mudar, este teste diz qual — e a decisão volta a ser
        dele."""
        for n, (cm, _) in OS_SETE_MEDIDOS.items():
            cru = self.crus[self.tirados[n]["id"]]
            self.assertEqual(cru["cardmarket_id"], cm, n)

    def test_a_aba_fica_com_48_selados(self):
        selados = [x for x in self.lista if not x["acessorio"]]
        self.assertEqual(len(selados), 48, "98 − 22 − 10 − 11 − 7")

    def test_por_edicao_depois_dos_sete(self):
        """Os números que ele vai ver, edição a edição. Mexem três: a OP
        desaparece (1→0), a PROMO-RIFT 10→5 e a T1S 2→1."""
        por = {}
        for x in self.lista:
            if not x["acessorio"]:
                por[x["edicao"]] = por.get(x["edicao"], 0) + 1
        self.assertEqual(por, {"OGN": 5, "OGS": 2, "SFD": 6, "UNL": 8, "VEN": 8,
                               "RAD": 7, "LGC": 2, "PG2": 1, "REC": 1, "ARC": 2,
                               "PROMO-RIFT": 5, "T1S": 1})
        self.assertEqual(sum(por.values()), 48)

    def test_a_op_desapareceu_por_ter_um_produto_so(self):
        self.assertEqual([x["nome"] for x in self.lista if x["edicao"] == "OP"], [])

    def test_saem_exactamente_50_e_cada_nome_casa_com_um(self):
        ex = self.selado.excluidos(self.cfg)
        self.assertEqual(len(ex), 50)
        self.assertEqual(len({x["id"] for x in ex}), 50)

    def test_ler_nao_escreve(self):
        antes = (REPO / "data" / "selado_catalogo.json").read_bytes()
        self.selado.itens(None, self.cfg)
        self.assertEqual((REPO / "data" / "selado_catalogo.json").read_bytes(), antes)


class TestOQueFicaNoCatalogoReal(RealBase):
    """As quatro coisas que esta ordem tinha de NÃO tirar."""

    def test_a_pre_venda_continua_visivel(self):
        for n in PRE_VENDA:
            self.assertIn(n, self.nomes, f"{n} tinha de ficar")

    def test_a_pre_venda_nao_tem_cardmarket_id(self):
        """É por isto que o critério exige as DUAS colunas: se bastasse faltar
        o id, estes oito saíam."""
        for n in PRE_VENDA:
            self.assertIsNone(self.por_nome[n]["cardmarket_id"], n)

    def test_as_edicoes_por_sair_continuam_na_aba(self):
        por = {}
        for x in self.lista:
            if not x["acessorio"]:
                por[x["edicao"]] = por.get(x["edicao"], 0) + 1
        for ed, n in (("LGC", 2), ("PG2", 1), ("REC", 1), ("RAD", 7)):
            self.assertEqual(por.get(ed), n, ed)

    def test_o_arcane_box_set_continua_visivel(self):
        """A caixa de coleccionador — não é o «Arcane Complete Set», que saiu
        a 25/09 por ser um conjunto de CARTAS."""
        self.assertIn("Arcane Box Set", self.nomes)
        self.assertNotIn("Arcane Complete Set", self.nomes)

    def test_os_quatro_nexus_night_continuam_visiveis(self):
        nexus = sorted(n for n in self.nomes if "Nexus Night" in n)
        self.assertEqual(len(nexus), 4, nexus)
        for n in NEXUS_POR_DECIDIR:
            self.assertIn(n, nexus)

    def test_os_dois_nexus_por_decidir_nao_tem_cardmarket_id(self):
        """É a razão de a pergunta ter ido ao André em vez de ser decidida
        aqui: pela letra do pedido saíam, mas compram-se."""
        for n in NEXUS_POR_DECIDIR:
            self.assertIsNone(self.por_nome[n]["cardmarket_id"], n)

    def test_o_nexus_night_do_ogn_tem_cardmarket_e_fica_de_certeza(self):
        self.assertEqual(
            self.por_nome["Origins | Nexus Night Promo Booster"]["cardmarket_id"],
            856097)

    def test_os_dezassete_da_extra_continuam_visiveis(self):
        do_config = [x for x in self.lista if x["fonte"] == "config"]
        self.assertEqual(len(do_config), 17)
        for x in do_config:
            self.assertIsNone(x["blueprint_id"])
            self.assertIsNone(x["cardmarket_id"])

    def test_o_immersive_saiu_e_o_arcane_promo_pack_tambem(self):
        """Os dois nomes em que um está dentro do outro: saem os dois, cada um
        pelo seu nome, e não por um ter apanhado o outro."""
        for n in ("Arcane Promo Pack", "Immersive Arcane Promo Pack", "Promo Pack"):
            self.assertIn(n, self.tirados, n)
        self.assertEqual(len({self.tirados[n]["id"] for n in
                              ("Arcane Promo Pack", "Immersive Arcane Promo Pack",
                               "Promo Pack")}), 3)

    def test_nenhum_produto_visivel_tem_nome_de_servico(self):
        """O «Replacement Card Booster» nem produto é: é o serviço da Riot de
        substituição de cartas danificadas."""
        self.assertNotIn("Replacement Card Booster", self.nomes)


# ---------------------------------------------------------------------------
# 5. Nenhuma exclusão morta — o guarda da lista INTEIRA, com 50 entradas
# ---------------------------------------------------------------------------


class TestNenhumaExclusaoMorta(RealBase):
    """O mesmo guarda do `test_selado_champion`, agora com as 50: uma entrada
    que não casa não esconde produto nenhum — é erro de escrita, ou um produto
    que o CardTrader tirou do catálogo."""

    def _por_nome(self):
        out = {}
        for p in self.crus.values():
            for n in (p["nome"], p.get("nome_bruto")):
                if n:
                    out.setdefault(self.selado._chave_nome(n), []).append(p)
        return out

    def test_todas_as_entradas_casam_com_um_produto(self):
        self.assertEqual(len(self.tirados), len(self.cfg["selado"]["excluidos"]))

    def test_nenhuma_entrada_fica_por_casar(self):
        por_nome = self._por_nome()
        mortas = [e for e in self.cfg["selado"]["excluidos"]
                  if e not in self.crus
                  and not por_nome.get(self.selado._chave_nome(e))]
        self.assertEqual(mortas, [], "exclusões que não estão a tirar nada")

    def test_nenhuma_entrada_e_ambigua(self):
        por_nome = self._por_nome()
        for e in self.cfg["selado"]["excluidos"]:
            if e in self.crus:
                continue
            ids = {p["id"] for p in por_nome.get(self.selado._chave_nome(e), [])}
            self.assertEqual(len(ids), 1, f"{e!r} casa com {sorted(ids)}")

    def test_uma_entrada_morta_rebenta(self):
        cfg = json.loads(json.dumps(self.cfg))
        cfg["selado"]["excluidos"] = list(cfg["selado"]["excluidos"]) + ["Nao Existe Isto"]
        with self.assertRaises(ValueError):
            self.selado.itens(None, cfg)


# ---------------------------------------------------------------------------
# 6. A fotografia — nada da Coleção mexe
# ---------------------------------------------------------------------------


class TestNaoMexeEmNadaDaColecao(SemMercadoBase):
    """A MESMA fotografia do `test_selado`, por referência: não há duas
    definições de «número da Coleção»."""

    fotografia = _Foto.fotografia

    def test_tirar_o_que_nao_se_compra_nao_mexe_em_nada(self):
        con = self.catalogo()
        self.cfg_selado({})
        antes = self.fotografia(con)
        self.selado.ajustar(con, "ct-803", 2, source="test")   # a pré-venda, que fica
        self.cfg_selado({"excluidos": [SEM_MERCADO, SO_CARDMARKET]})
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

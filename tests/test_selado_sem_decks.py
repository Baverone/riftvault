"""Nada em forma de DECK entra no Produto Selado; e o «—» passa a dizer o que
se passa (André, 2026-09-28).

Palavras dele: *"verifica novamente os produtos selados, ainda estao la
champions decks que nao tem disponiveis / e nao quero 'decks' para
colecionar"*.

A PRIMEIRA METADE DA QUEIXA NÃO BATIA CERTO, e isso fica fixado aqui
---------------------------------------------------------------------
Não havia Champion Deck nenhum na aba — saíram a 25 e 26/09. O que lá estava
com «Deck» no nome eram os DOIS SHOWDOWN DECK, e esses **têm oferta** (58 e 9
anúncios no CardTrader). Ele juntou duas queixas numa:

  - «champions decks que não têm disponíveis» -> não existiam;
  - «não quero decks para colecionar»          -> é esta que tem efeito.

O que se fixa
-------------
1. **A REGRA É A CATEGORIA, NÃO UMA LISTA DE NOMES.** A 262 «Riftbound Starter
   Decks» saiu das `selado.categorias`, e com ela sai tudo o que o CardTrader
   classifica como deck — hoje e no lançamento que vier. Uma lista de
   `excluidos` só apanha o que já existe: há teste que mete um Champion Deck
   NOVO no catálogo e exige que ele não apareça sem ninguém escrever o nome.
2. **Zero mecanismo novo para isso.** É o `_crus` a filtrar por `categoria_id`,
   como sempre fez. Há teste que o prova pela negativa.
3. **A decisão de 25 e 26/09 não se perdeu.** Os 18 nomes que ficaram
   redundantes saíram do `selado.excluidos` e estão em `_selado_decks_arquivado`
   no config, com a data e a razão, como os 17 do `_selado_extra_arquivado`.
4. **Nada em forma de deck na aba, por via nenhuma** — nem por nome, nem por
   tipo, nem pelo `selado.extra`. Medido contra o config e o catálogo REAIS,
   pela função da app.
5. **O «—» deixou de ser mudo.** Era um traço seco que se lia «este produto não
   existe»; passa a dizer que **o CardTrader não tem oferta e que a app não lê
   o Cardmarket** (403). E o preço de lá tem agora um sítio para ele o
   escrever, como o Trend da Venda: a `sealed_price`.
6. E, por cima, a defesa de sempre: **nada disto mexe num número da Coleção**,
   pela fotografia do `test_selado`, por referência.

Tudo contra pastas temporárias e um config temporário, menos os testes que
dizem «REAL» no nome, que lêem o `riftvault_config.json` e o
`data/selado_catalogo.json` do repositório — sem os escrever.
"""

from __future__ import annotations

import contextlib
import copy
import io
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.test_selado import CATALOGO, Base  # noqa: E402
from tests.test_selado import TestNaoEntraNaColecao as _Foto  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
CONFIG_REAL = json.loads((REPO / "riftvault_config.json").read_text(encoding="utf-8"))
CATALOGO_REAL = REPO / "data" / "selado_catalogo.json"

APP_JS = REPO / "riftvault" / "web" / "app.js"
CSS = REPO / "riftvault" / "web" / "style.css"
SCHEMA = REPO / "riftvault" / "schema.sql"
CLI = REPO / "riftvault" / "cli.py"
SERVER = REPO / "riftvault" / "server.py"

DECKS = 262   # «Riftbound Starter Decks» no CardTrader

# Os 18 nomes que ficaram redundantes quando a 262 saiu. Medidos a 2026-09-28
# contra o catálogo real: são todos da 262, e por isso a regra tira-os sozinha.
ARQUIVADOS_25 = [
    "Origins: Champion Deck Set",
    "Origins: Jinx Trial Deck", "Origins: Viktor Trial Deck",
    "Origins: Volibear Trial Deck", "Origins: Yasuo Trial Deck",
    "2024 Trial Deck Set", "2025 Trial Deck Set",
]
ARQUIVADOS_26 = [
    'Origins: "Jinx" Champion Deck', 'Origins: "Viktor" Champion Deck',
    'Origins: "Lee Sin" Champion Deck',
    'Spiritforged: "Rumble" Champion Deck', 'Spiritforged: "Fiora" Champion Deck',
    'Unleashed: "Vi" Champion Deck', 'Unleashed: "Vex" Champion Deck',
    'Legacy: "Ashe" Champion Deck', 'Legacy: "Tryndamere" Champion Deck',
    'Legacy: "Lux" Champion Deck', 'Legacy: "Garen" Champion Deck',
]

# Os dois que SAÍRAM MESMO da aba com esta ordem (os outros 18 já estavam fora
# por nome). Têm oferta — e é por isso que a primeira metade da queixa dele não
# batia certo.
SHOWDOWN = ['Vendetta: "Zed vs Shen" Showdown Deck',
            'Radiance: "Evelynn vs Seraphine" Showdown Deck']

# Os dois «Trial Deck Case» são da 263 e a regra NÃO os apanha: continuam a
# sair pelo nome. É o limite da regra, e diz-se em vez de se esconder.
CASES_QUE_FICAM_NO_EXCLUIDOS = ["2024 Trial Deck Case", "2025 Trial Deck Case"]


def sem_decks(cats: list[int]) -> list[int]:
    return [c for c in cats if c != DECKS]


class Sem262(Base):
    """A aba com a 262 fora, contra o catálogo de brincar do `test_selado`."""

    def setUp(self):
        super().setUp()
        self.cfg_selado({"categorias": sem_decks(self.selado.DEFAULTS["categorias"])})
        self._con = None

    @property
    def ligacao(self):
        if self._con is None:
            self._con = self.con()
        return self._con

    def aba(self, con=None):
        return self.selado.itens(con if con is not None else self.ligacao)


# ---------------------------------------------------------------------------
# 1. A regra: a categoria, não os nomes
# ---------------------------------------------------------------------------


class TestARegraEACategoria(Sem262):
    def test_o_champion_deck_do_catalogo_nao_aparece(self):
        nomes = [x["nome"] for x in self.aba()]
        self.assertNotIn('Teste: "Jinx" Champion Deck', nomes)

    def test_e_com_a_262_dentro_aparece(self):
        """A prova pela negativa: é MESMO a categoria que o tira."""
        self.cfg_selado({})          # DEFAULTS, com a 262
        nomes = [x["nome"] for x in self.aba()]
        self.assertIn('Teste: "Jinx" Champion Deck', nomes)

    def test_um_champion_deck_NOVO_nao_precisa_de_ser_escrito(self):
        """É a diferença entre a regra e a lista de nomes: um produto que ainda
        não existe. Uma lista de `excluidos` falhava aqui."""
        cat = copy.deepcopy(CATALOGO)
        cat["produtos"].append(
            {"blueprint_id": 999, "nome": 'Teste: "Lux" Champion Deck', "versao": "",
             "categoria_id": DECKS, "edicao": "TST", "edicao_nome": "Teste",
             "img": None, "cardmarket_id": 123456})
        cat["precos"]["999"] = {"cents": 1999, "currency": "EUR",
                                "day": "2026-09-28", "n_listings": 7,
                                "n_sellers": 5, "n_copies": 9}
        self.escrever_catalogo(cat)
        nomes = [x["nome"] for x in self.aba()]
        self.assertNotIn('Teste: "Lux" Champion Deck', nomes)
        # e nada foi escrito no config para isso acontecer
        op = self.selado.opcoes()
        self.assertEqual(op["excluidos"], [])

    def test_o_tipo_deck_desaparece_da_aba(self):
        self.assertEqual([x for x in self.aba() if x["tipo"] == "deck"], [])

    def test_e_o_tipo_deck_sai_dos_tipos_do_payload(self):
        p = self.selado.payload(self.ligacao)
        self.assertNotIn("deck", [t["id"] for t in p["tipos"]])

    def test_nao_ha_mecanismo_novo(self):
        """O filtro continua a ser o `_crus` a comparar a categoria — não
        nasceu função nenhuma, nem um segundo sítio a decidir o que entra.

        Não se varre a prosa: o `selado.py` nomeia Champion Deck e Trial Deck
        em comentários e docstrings (a história das decisões, e os exemplos do
        `nome_limpo`), e isso é documentação, não um filtro. A prova de que a
        regra é a categoria é o `test_um_champion_deck_NOVO_…`, que mete um
        produto que ninguém nomeou e exige que ele não apareça.
        """
        fonte = (REPO / "riftvault" / "selado.py").read_text(encoding="utf-8")
        self.assertIn("if cid not in cats and cid not in acess:", fonte,
                      "o filtro por categoria saiu do `_crus`")
        self.assertEqual(fonte.count("if cid not in cats"), 1,
                         "há um segundo sítio a decidir o que entra na aba")

    def test_a_262_continua_a_poder_voltar(self):
        """Repor é escrever 262 outra vez."""
        self.cfg_selado({"categorias": [259, 260, 261, 262, 263, 283]})
        self.assertIn('Teste: "Jinx" Champion Deck', [x["nome"] for x in self.aba()])

    def test_as_outras_categorias_nao_mexem(self):
        cats = {x["categoria_id"] for x in self.aba()}
        self.assertEqual(cats, {259, 260, 261, 263, 283})

    def test_a_262_vai_parar_ao_fora_MARCADA(self):
        """Uma categoria que ele TIROU não é o mesmo que uma que nunca contou.

        Aparece no `fora` — nunca desaparece em silêncio — mas com
        `tirada: True`, senão a página dizia que os Starter Decks «não são
        produto selado nem acessório de coleção», o que é FALSO: são produto
        selado, e foi ele que os tirou. Foi um defeito a sério, visto na
        fotografia da página antes do merge."""
        por_cat = {x["categoria_id"]: x for x in self.selado.fora()}
        self.assertIn(DECKS, por_cat)
        self.assertEqual(por_cat[DECKS]["n"], 1)   # o Champion Deck do catálogo falso
        self.assertTrue(por_cat[DECKS]["tirada"])

    def test_as_que_nunca_contaram_nao_vem_marcadas(self):
        """Playmats e sleeves: essas nunca foram produto selado."""
        por_cat = {x["categoria_id"]: x for x in self.selado.fora()}
        for cid in (264, 266):
            self.assertIn(cid, por_cat)
            self.assertFalse(por_cat[cid]["tirada"], cid)

    def test_com_a_262_dentro_nada_vem_marcado(self):
        self.cfg_selado({})
        self.assertEqual([x for x in self.selado.fora() if x["tirada"]], [])

    def test_o_texto_da_pagina_e_do_cli_separam_os_dois_casos(self):
        p = self.selado.payload(self.ligacao)
        txt = self.selado.texto(p)
        self.assertIn("não são produto selado nem acessório", txt)
        self.assertIn("Produto selado que TIRASTE", txt)
        js = (REPO / "riftvault" / "web" / "app.js").read_text(encoding="utf-8")
        self.assertIn("slForaTexto", js)
        self.assertIn("que <b>tiraste</b>", js)

    def test_uma_unidade_gravada_num_deck_nao_se_apaga_e_volta(self):
        """Esconder não é apagar, como sempre: a `sealed_copies` fica."""
        self.cfg_selado({})                      # com a 262
        self.selado.ajustar(self.ligacao, "ct-104", 2)
        self.ligacao.commit()
        self.cfg_selado({"categorias": sem_decks(self.selado.DEFAULTS["categorias"])})
        self.assertEqual([x for x in self.aba() if x["id"] == "ct-104"], [])
        self.assertEqual(self.selado.tenho(self.ligacao).get("ct-104"), 2)
        self.cfg_selado({})
        x = [y for y in self.aba() if y["id"] == "ct-104"][0]
        self.assertEqual(x["qty"], 2)

    def test_o_mais_num_deck_recusa(self):
        with self.assertRaises(self.selado.ProdutoDesconhecido):
            self.selado.ajustar(self.ligacao, "ct-104", 1)

    def test_o_catalogo_em_disco_fica_intacto(self):
        antes = self.config.SELADO_PATH.read_text(encoding="utf-8")
        self.selado.payload(self.ligacao)
        self.assertEqual(self.config.SELADO_PATH.read_text(encoding="utf-8"), antes)

    def test_o_selado_extra_pode_na_mesma_ter_um_deck(self):
        """A regra é do catálogo do CardTrader. O `selado.extra` é escrito à
        MÃO por ele — se lá puser um deck, é porque o quer. Fica dito."""
        self.cfg_selado({
            "categorias": sem_decks(self.selado.DEFAULTS["categorias"]),
            "extra": [{"nome": "Um deck à mão", "edicao": "TST", "tipo": "deck"}]})
        self.assertIn("Um deck à mão", [x["nome"] for x in self.aba()])


# ---------------------------------------------------------------------------
# 2. Contra o config e o catálogo REAIS
# ---------------------------------------------------------------------------


class TestOConfigReal(unittest.TestCase):
    def setUp(self):
        self.selado_cfg = CONFIG_REAL["selado"]

    def test_a_262_saiu_das_categorias(self):
        self.assertNotIn(DECKS, self.selado_cfg["categorias"])

    def test_as_outras_cinco_ficaram(self):
        self.assertEqual(self.selado_cfg["categorias"], [259, 260, 261, 263, 283])

    def test_os_18_sairam_do_excluidos(self):
        excl = self.selado_cfg["excluidos"]
        for nome in ARQUIVADOS_25 + ARQUIVADOS_26:
            self.assertNotIn(nome, excl, f"{nome} é redundante com a 262 fora")

    def test_e_estao_arquivados_com_a_data_e_a_razao(self):
        arq = CONFIG_REAL["_selado_decks_arquivado"]
        self.assertEqual(arq["de_2026_09_25"], ARQUIVADOS_25)
        self.assertEqual(arq["de_2026_09_26"], ARQUIVADOS_26)
        porque = arq["_porque"].lower()
        for pedaco in ("2026-09-25", "2026-09-26", "262", "redundante"):
            self.assertIn(pedaco, porque)

    def test_sao_18(self):
        arq = CONFIG_REAL["_selado_decks_arquivado"]
        self.assertEqual(len(arq["de_2026_09_25"]) + len(arq["de_2026_09_26"]), 18)

    def test_os_trial_deck_case_FICAM_no_excluidos(self):
        """São da 263 e a regra não os apanha — é o limite dela."""
        for nome in CASES_QUE_FICAM_NO_EXCLUIDOS:
            self.assertIn(nome, self.selado_cfg["excluidos"])

    def test_a_nota_da_regra_existe_e_diz_o_que_a_regra_NAO_apanha(self):
        nota = CONFIG_REAL["_selado_sem_decks"].lower()
        self.assertIn("262", nota)
        self.assertIn("categoria", nota)
        # tem de dizer que os Showdown Deck tinham oferta — a queixa dele não
        # batia certo e isso não se pode calar
        self.assertIn("showdown", nota)
        self.assertIn("trial deck case", nota)

    def test_o_excluidos_encolheu_de_49_para_31(self):
        self.assertEqual(len(self.selado_cfg["excluidos"]), 31)

    def test_as_decisoes_anteriores_ficaram_inteiras(self):
        """Os nomes das ordens de 25, 26 e 28/09 que NÃO são decks continuam lá
        — esta ordem não pode ter levado nada à boleia."""
        excl = self.selado_cfg["excluidos"]
        for nome in ("Origins Booster", "Origins Slim Booster Box",
                     "Spiritforged Bulk Runes", "Spiritforged Pre-Rift Kit",
                     "Arcane Complete Set", "Arcane Chinese Promo Set",
                     "Tournament Gift Box", "Promo Pack",
                     "The T1 Worlds Champion | Player Bundle"):
            self.assertIn(nome, excl)

    def test_o_extra_arquivado_de_28_09_nao_foi_tocado(self):
        self.assertEqual(len(CONFIG_REAL["_selado_extra_arquivado"]["produtos"]), 17)


@unittest.skipUnless(CATALOGO_REAL.exists(), "sem catálogo em disco")
class TestOCatalogoReal(unittest.TestCase):
    """Contra o `data/selado_catalogo.json` e o config REAIS, sem os escrever.

    É o teste que responde à pergunta do André: sobrou algum deck?
    """

    @classmethod
    def setUpClass(cls):
        from riftvault import selado
        cls.selado = selado
        cls.cat = json.loads(CATALOGO_REAL.read_text(encoding="utf-8"))
        cls.lista = selado.itens(None, CONFIG_REAL)

    def test_nada_em_forma_de_deck_na_aba_REAL(self):
        """Por TIPO e por NOME, e por qualquer via (catálogo, `extra`)."""
        por_tipo = [x["nome"] for x in self.lista if x["tipo"] == "deck"]
        self.assertEqual(por_tipo, [], f"tipo deck na aba: {por_tipo}")
        por_nome = [x["nome"] for x in self.lista
                    if "deck" in x["nome"].lower()
                    and "deck box" not in x["nome"].lower()]
        self.assertEqual(por_nome, [], f"«deck» no nome: {por_nome}")

    def test_nenhum_produto_da_262_chega_a_aba(self):
        ids262 = {f"ct-{p['blueprint_id']}" for p in self.cat["produtos"]
                  if int(p.get("categoria_id") or 0) == DECKS}
        self.assertTrue(ids262, "o catálogo real tem de ter produtos na 262")
        na_aba = ids262 & {x["id"] for x in self.lista}
        self.assertEqual(na_aba, set())

    def test_os_dois_showdown_deck_sao_os_que_saem_MESMO(self):
        """Os outros 18 já estavam fora por nome. Estes dois é que a regra
        tirou — e TINHAM oferta, que é o que desmente a queixa."""
        precos = self.cat.get("precos") or {}
        for nome in SHOWDOWN:
            p = [x for x in self.cat["produtos"]
                 if self.selado.nome_limpo(x["nome"]) == nome]
            self.assertEqual(len(p), 1, nome)
            pr = precos.get(str(p[0]["blueprint_id"])) or {}
            self.assertIsNotNone(pr.get("cents"), f"{nome} devia ter preço")
            self.assertGreater(pr.get("n_listings") or 0, 0,
                               f"{nome} devia ter anúncios")

    def test_nao_havia_champion_deck_nenhum_na_aba_ANTES_desta_ordem(self):
        """A primeira metade da queixa dele. Com a 262 DENTRO (o de antes) e o
        `excluidos` de antes, nenhum Champion Deck aparecia."""
        antes = json.loads(json.dumps(CONFIG_REAL))
        antes["selado"]["categorias"] = [259, 260, 261, 262, 263, 283]
        antes["selado"]["excluidos"] = (
            list(antes["selado"]["excluidos"]) + ARQUIVADOS_25 + ARQUIVADOS_26)
        lista = self.selado.itens(None, antes)
        champs = [x["nome"] for x in lista if "champion deck" in x["nome"].lower()]
        self.assertEqual(champs, [])
        # ... e o que lá estava com «Deck» no nome eram os dois Showdown
        com_deck = sorted(x["nome"] for x in lista if "deck" in x["nome"].lower())
        self.assertEqual(com_deck, sorted(SHOWDOWN))

    def test_as_31_entradas_do_excluidos_continuam_a_casar(self):
        """Nenhuma exclusão morta depois de tirar as 18 — o guarda de 26/09,
        outra vez, para a lista nova."""
        todos = self.selado._crus(CONFIG_REAL, com_excluidos=True)
        for nome in CONFIG_REAL["selado"]["excluidos"]:
            alvo = self.selado._resolver_excluidos(todos, [nome])
            self.assertEqual(len(alvo), 1, f"{nome!r} não casa com um produto só")

    def test_a_aba_real_tem_30_produtos(self):
        self.assertEqual(len(self.lista), 30)

    def test_nenhuma_entrada_do_excluidos_serve_para_tirar_um_deck(self):
        """A regra é a categoria, e prova-se por aqui: se alguma entrada do
        `selado.excluidos` ainda estivesse a tirar um produto da 262, a lista
        de nomes é que estaria a fazer o trabalho — e o próximo Champion Deck
        voltava a aparecer."""
        todos = self.selado._crus(CONFIG_REAL, com_excluidos=True)
        por_id = {p["id"]: p for p in todos}
        for nome in CONFIG_REAL["selado"]["excluidos"]:
            for pid in self.selado._resolver_excluidos(todos, [nome]):
                self.assertNotEqual(
                    por_id[pid].get("categoria_id"), DECKS,
                    f"{nome!r} está a tirar um produto da 262 — isso é a regra")


# ---------------------------------------------------------------------------
# 3. O «—» deixou de ser mudo, e o preço do Cardmarket à mão
# ---------------------------------------------------------------------------


class TestOPrecoDoCardmarket(Sem262):
    ALVO = "ct-103"        # «Teste: Proving Grounds», sem oferta no CardTrader

    def item(self, pid, con=None):
        return {x["id"]: x for x in self.aba(con)}[pid]

    def test_sem_preco_nenhum_a_linha_diz_o_que_se_passa(self):
        x = self.item(self.ALVO)
        self.assertIsNone(x["preco_mostrado_cents"])
        self.assertIsNone(x["preco_fonte"])
        # e o texto do CLI di-lo, em vez de um traço seco
        linha = self.selado._marca_do_preco(x)
        self.assertIn("sem oferta no CardTrader", linha)
        self.assertIn("não lê o Cardmarket", linha)

    def test_gravar_o_preco_do_cardmarket(self):
        self.selado.definir_preco(self.ligacao, self.ALVO, "13,00")
        x = self.item(self.ALVO)
        self.assertEqual(x["preco_cm_cents"], 1300)
        self.assertEqual(x["preco_mostrado_cents"], 1300)
        self.assertEqual(x["preco_fonte"], "cardmarket")
        self.assertIsNone(x["preco_cents"], "o do CardTrader continua a não existir")

    def test_aceita_virgula_e_ponto(self):
        for texto, cents in (("13,00", 1300), ("13.00", 1300), ("7", 700),
                             ("0,50", 50)):
            self.selado.definir_preco(self.ligacao, self.ALVO, texto)
            self.assertEqual(self.item(self.ALVO)["preco_cm_cents"], cents, texto)

    def test_apagar(self):
        self.selado.definir_preco(self.ligacao, self.ALVO, "13,00")
        self.selado.definir_preco(self.ligacao, self.ALVO, None)
        x = self.item(self.ALVO)
        self.assertIsNone(x["preco_cm_cents"])
        self.assertIsNone(x["preco_mostrado_cents"])

    def test_o_do_cardtrader_GANHA_quando_existe(self):
        """É o medido. O do Cardmarket tapa o buraco, não substitui o número
        que já lá estava — senão esta ordem mexia num preço que ele conhece."""
        self.selado.definir_preco(self.ligacao, "ct-101", "999,00")
        x = self.item("ct-101")
        self.assertEqual(x["preco_cents"], 16064)
        self.assertEqual(x["preco_mostrado_cents"], 16064)
        self.assertEqual(x["preco_fonte"], "cardtrader")
        self.assertEqual(x["preco_cm_cents"], 99900, "mas mostra-se na mesma")

    def test_o_valor_do_selado_conta_o_preco_a_mao(self):
        self.selado.ajustar(self.ligacao, self.ALVO, 2)
        antes = self.selado.contar(self.aba())["valor_cents"]
        self.selado.definir_preco(self.ligacao, self.ALVO, "13,00")
        depois = self.selado.contar(self.aba())["valor_cents"]
        self.assertEqual(depois - antes, 2600)

    def test_e_nao_conta_o_que_ele_nao_tem(self):
        antes = self.selado.contar(self.aba())["valor_cents"]
        self.selado.definir_preco(self.ligacao, self.ALVO, "13,00")
        self.assertEqual(self.selado.contar(self.aba())["valor_cents"], antes)

    def test_os_contadores(self):
        t0 = self.selado.contar(self.aba())
        self.assertEqual(t0["preco_a_mao"], 0)
        sem0, semct0 = t0["sem_preco"], t0["sem_cardtrader"]
        self.selado.definir_preco(self.ligacao, self.ALVO, "13,00")
        t1 = self.selado.contar(self.aba())
        self.assertEqual(t1["preco_a_mao"], 1)
        self.assertEqual(t1["sem_preco"], sem0 - 1, "deixou de estar sem preço")
        self.assertEqual(t1["sem_cardtrader"], semct0,
                         "mas o CardTrader continua a não o ter")

    def test_recusa_um_produto_que_nao_esta_na_aba(self):
        with self.assertRaises(self.selado.ProdutoDesconhecido):
            self.selado.definir_preco(self.ligacao, "ct-104", "10")   # deck
        with self.assertRaises(self.selado.ProdutoDesconhecido):
            self.selado.definir_preco(self.ligacao, "ct-999999", "10")

    def test_recusa_um_produto_excluido_com_a_razao(self):
        self.cfg_selado({"categorias": sem_decks(self.selado.DEFAULTS["categorias"]),
                         "excluidos": ["Teste Booster"]})
        with self.assertRaises(self.selado.ProdutoExcluido) as ctx:
            self.selado.definir_preco(self.ligacao, "ct-106", "10")
        self.assertIn("tira o nome da lista", str(ctx.exception))

    def test_recusa_um_preco_que_nao_e_preco(self):
        for mau in ("abc", "1,2,3", "--"):
            with self.assertRaises(ValueError):
                self.selado.definir_preco(self.ligacao, self.ALVO, mau)

    def test_recusa_um_preco_negativo(self):
        with self.assertRaises(ValueError):
            self.selado.definir_preco(self.ligacao, self.ALVO, "-5")

    def test_guarda_a_data_e_a_origem(self):
        self.selado.definir_preco(self.ligacao, self.ALVO, "13,00", source="cli")
        r = self.ligacao.execute("SELECT * FROM sealed_price").fetchone()
        self.assertEqual(r["source"], "cli")
        self.assertTrue(r["updated_at"])
        self.assertEqual(self.item(self.ALVO)["preco_cm_dia"], r["updated_at"][:10])

    def test_escreve_SO_na_sealed_price(self):
        """Não toca no `copies`, na `ops`, nos locais nem na `sealed_copies`."""
        def foto():
            c = self.ligacao
            return (
                c.execute("SELECT COUNT(*) FROM copies").fetchone()[0],
                c.execute("SELECT COALESCE(SUM(qty),0) FROM copies").fetchone()[0],
                c.execute("SELECT COUNT(*) FROM ops").fetchone()[0],
                c.execute("SELECT COUNT(*) FROM copy_locations").fetchone()[0],
                c.execute("SELECT COUNT(*) FROM sealed_copies").fetchone()[0],
            )
        antes = foto()
        self.selado.definir_preco(self.ligacao, self.ALVO, "13,00")
        self.selado.definir_preco(self.ligacao, "ct-101", "1,00")
        self.assertEqual(foto(), antes)

    def test_o_payload_diz_que_o_preco_vem_do_cardtrader_e_porque(self):
        p = self.selado.payload(self.ligacao)
        pr = p["scope"]["precos"]
        self.assertEqual(pr["fonte"], "CardTrader")
        self.assertTrue(pr["cardmarket_a_mao"])
        self.assertIn("403", pr["porque"])

    def test_a_tabela_esta_no_schema_e_nao_toca_na_coleccao(self):
        sql = SCHEMA.read_text(encoding="utf-8")
        self.assertIn("CREATE TABLE IF NOT EXISTS sealed_price", sql)
        self.assertIn("product_id TEXT    PRIMARY KEY", sql)
        self.assertIn("cents >= 0", sql)

    def test_nenhum_modulo_de_contas_le_a_sealed_price(self):
        """Como a `sealed_copies`: o selado não entra na Coleção."""
        for nome in ("metrics", "a_subir", "faltas", "faltas_edicao", "a_mais",
                     "uso_decks", "decks", "locais", "pending", "prices",
                     "painel", "runas_vista", "cardmarket", "collection",
                     "foil", "proprias", "venda", "principal", "catalog"):
            f = REPO / "riftvault" / f"{nome}.py"
            if not f.exists():
                continue
            fonte = f.read_text(encoding="utf-8")
            self.assertNotIn("sealed_price", fonte,
                             f"{nome}.py lê a sealed_price — o selado não entra "
                             f"na Coleção")


class TestAInterface(unittest.TestCase):
    def setUp(self):
        self.js = APP_JS.read_text(encoding="utf-8")
        self.css = CSS.read_text(encoding="utf-8")

    def test_o_traco_seco_desapareceu(self):
        self.assertNotIn("x.preco_cents != null ? eur(x.preco_cents) : '—'", self.js)

    def test_a_linha_diz_sem_oferta_no_cardtrader(self):
        self.assertIn("sem oferta", self.js)
        self.assertIn("a app não lê o Cardmarket", self.js)

    def test_ha_campo_para_o_preco_do_cardmarket(self):
        self.assertIn("sl-cm-in", self.js)
        self.assertIn("api/selado/preco", self.js)
        self.assertIn(".sl-cm input", self.css)

    def test_o_campo_so_aparece_em_modo_edicao(self):
        i = self.js.index("function slPreco(")
        self.assertIn("state.editable", self.js[i:i + 1400])

    def test_grava_ao_sair_do_campo_e_nao_a_cada_tecla(self):
        """Senão cada dígito era um pedido e um redesenho da lista inteira."""
        i = self.js.rindex("sl-cm-in")          # a LIGAÇÃO, não o `<input>`
        troco = self.js[i:i + 900]
        self.assertIn("onchange", troco)
        self.assertNotIn("oninput", troco)

    def test_o_cabecalho_explica_o_403(self):
        i = self.js.index("sem oferta no <b>CardTrader</b>")
        self.assertIn("403", self.js[i:i + 400])

    def test_a_frase_do_sem_preco_pode_partir_se_a_375(self):
        """A lição de 22/09: `nowrap` numa frase longa manda-a para fora do
        ecrã. A `.sl-preco.vazio` não pode ter um."""
        i = self.css.index(".sl-preco.vazio")
        self.assertNotIn("nowrap", self.css[i:i + 300])


class TestARotaEACLI(unittest.TestCase):
    def test_a_rota_existe(self):
        fonte = SERVER.read_text(encoding="utf-8")
        self.assertIn('@app.post("/api/selado/preco")', fonte)
        self.assertIn("definir_preco", fonte)

    def test_a_cli_tem_preco(self):
        fonte = CLI.read_text(encoding="utf-8")
        self.assertIn('"--preco"', fonte)
        self.assertIn("definir_preco", fonte)
        self.assertIn("[--preco ID [EUROS]]", fonte)


class TestACLICorre(Sem262):
    def correr(self, *args):
        from riftvault import cli
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = cli.main(list(args))
        return rc, out.getvalue(), err.getvalue()

    def test_o_texto_do_cli_nao_diz_so_um_traco(self):
        p = self.selado.payload(self.ligacao)
        txt = self.selado.texto(p)
        self.assertIn("sem oferta no CardTrader", txt)
        self.assertIn("escreve-se à mão", txt)

    def test_o_cli_grava_o_preco(self):
        rc, out, err = self.correr("selado", "--preco", "ct-103", "13,00")
        self.assertEqual(rc, 0, err)
        self.assertIn("13.00", out)
        self.assertEqual(
            self.ligacao.execute("SELECT cents FROM sealed_price WHERE product_id='ct-103'")
            .fetchone()[0], 1300)

    def test_o_cli_apaga_o_preco(self):
        self.selado.definir_preco(self.ligacao, "ct-103", "13,00")
        self.ligacao.commit()
        rc, out, err = self.correr("selado", "--preco", "ct-103")
        self.assertEqual(rc, 0, err)
        self.assertIn("apagado", out)
        self.assertEqual(
            self.ligacao.execute("SELECT COUNT(*) FROM sealed_price").fetchone()[0], 0)

    def test_o_cli_recusa_um_deck(self):
        rc, out, err = self.correr("selado", "--preco", "ct-104", "13,00")
        self.assertEqual(rc, 1)
        self.assertIn("não está na lista", err)


# ---------------------------------------------------------------------------
# 4. A defesa de sempre: a Coleção não mexe
# ---------------------------------------------------------------------------


class TestNaoMexeNaColecao(_Foto):
    """A MESMA fotografia do `test_selado`, por referência — não há uma segunda
    definição de «número da Coleção» —, agora com a 262 fora e com preços do
    Cardmarket metidos à mão."""

    def setUp(self):
        super().setUp()
        self.cfg_selado({"categorias": sem_decks(self.selado.DEFAULTS["categorias"])})

    def test_tirar_os_decks_e_meter_precos_nao_mexe_em_nada(self):
        con = self.catalogo()
        antes = self.fotografia(con)
        self.selado.ajustar(con, "ct-101", 3, source="test")
        self.selado.definir_preco(con, "ct-103", "13,00", source="test")
        self.selado.definir_preco(con, "ct-101", "999,00", source="test")
        con.commit()
        self.assertEqual(self.fotografia(con), antes)
        self.selado.ajustar(con, "ct-101", -3, source="test")
        self.selado.definir_preco(con, "ct-103", None, source="test")
        self.selado.definir_preco(con, "ct-101", None, source="test")
        con.commit()
        self.assertEqual(self.fotografia(con), antes)

    def test_a_fotografia_nao_e_de_zeros(self):
        """Uma fotografia vazia era igual a si mesma e não provava nada."""
        f = self.fotografia(self.catalogo())
        self.assertTrue(f["grelha"])
        self.assertTrue(f["copies"])
        self.assertGreater(f["valor"]["cents"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

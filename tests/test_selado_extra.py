"""O que FALTAVA ao «Produto Selado», e as duas decisões (André, 2026-09-25).

Três coisas, e um teste por cada:

1. OS 17 PRODUTOS DO `selado.extra`
   O catálogo do CardTrader não tem o que quase não circula solto: os displays
   de champion decks (4 decks iguais), os de showdown (4 conjuntos), os cases
   de vaults e o do Proving Grounds, e os **Pre-Rift EVENT Kit** (16 kits de
   jogador + 1 display), que são OUTRO produto que o «Pre-Rift Kit» de UM
   jogador que o CardTrader tem. Entram pela chave que já existia para isso,
   cada um com o seu `conteudo`. Os MSRP são em dólares e ficam no conteúdo,
   nunca no preço — não há câmbio validado no riftvault.

2. OS ACESSÓRIOS NUMA SECÇÃO À PARTE (`selado.acessorios`)
   Binders (265) e deck boxes (267) entram, mas **não contam** para o produto
   selado: têm contadores e valor próprios e um filtro que os esconde. As
   playmats, as sleeves, a memorabilia e as oversized continuam de fora,
   contadas.

3. O CARDTRADER REPETE BLUEPRINTS (`selado.juntar_duplicados`)
   Quatro dos Trial Decks da Origins têm dois blueprints cada, com o mesmo
   nome, a mesma edição, a mesma categoria e a versão vazia. Juntam-se num só
   — e não às cegas: a chave leva a VERSÃO, por isso os «2024 Trial Deck Set»
   e «2025 Trial Deck Set» continuam a ser dois.

E, por cima de tudo, a defesa de sempre: **nada disto mexe num número da
Coleção**. A fotografia está no fim.
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests import test_selado as _sel  # noqa: E402
from tests.test_selado import APP_JS, CATALOGO, CSS, Base  # noqa: E402

# A classe da fotografia NÃO se importa pelo nome: o `unittest` descobre os
# TestCase do espaço de nomes do módulo e corria-a outra vez aqui.

REPO = Path(__file__).resolve().parent.parent

# O mesmo catálogo de brincar do `test_selado`, mais um binder, um deck box e
# um par de blueprints repetidos (o mesmo produto duas vezes, como os Trial
# Decks da Origins) e um par que NÃO é repetido (a versão diz o ano).
CAT = json.loads(json.dumps(CATALOGO))
CAT["categorias"]["265"] = "Riftbound Albums"
CAT["categorias"]["267"] = "Riftbound Deck Boxes"
CAT["produtos"] += [
    {"blueprint_id": 301, "nome": "Teste: 9-Pocket Collector Binder", "versao": "",
     "categoria_id": 265, "edicao": "TST", "edicao_nome": "Teste",
     "img": None, "cardmarket_id": 900301},
    {"blueprint_id": 302, "nome": "Teste Classic Deck Box", "versao": "",
     "categoria_id": 267, "edicao": "TST", "edicao_nome": "Teste",
     "img": None, "cardmarket_id": None},
    # O par repetido: o velho sem ofertas nem Cardmarket, o novo com os dois.
    {"blueprint_id": 401, "nome": "Teste: Jinx Trial Deck", "versao": "",
     "categoria_id": 262, "edicao": "TST", "edicao_nome": "Teste",
     "img": None, "cardmarket_id": None},
    {"blueprint_id": 402, "nome": "Teste: Jinx Trial Deck", "versao": "",
     "categoria_id": 262, "edicao": "TST", "edicao_nome": "Teste",
     "img": None, "cardmarket_id": 900402},
    # Dois produtos MESMO diferentes, que só a versão distingue.
    {"blueprint_id": 411, "nome": "Teste Trial Deck Set", "versao": "©2024",
     "categoria_id": 262, "edicao": "TST", "edicao_nome": "Teste",
     "img": None, "cardmarket_id": None},
    {"blueprint_id": 412, "nome": "Teste Trial Deck Set", "versao": "©2025",
     "categoria_id": 262, "edicao": "TST", "edicao_nome": "Teste",
     "img": None, "cardmarket_id": None},
]
CAT["precos"]["301"] = {"cents": 3399, "currency": "EUR", "day": "2026-09-25",
                        "n_listings": 4, "n_sellers": 4, "n_copies": 5}
CAT["precos"]["402"] = {"cents": 10064, "currency": "EUR", "day": "2026-09-25",
                        "n_listings": 3, "n_sellers": 3, "n_copies": 3}

# Os produtos do `selado.extra`, com a mesma forma dos 17 reais.
EXTRA = [
    {"nome": 'Teste: "Jinx" Champion Deck Display', "edicao": "TST",
     "tipo": "display", "data": "2025-01-31",
     "conteudo": "4 decks iguais · MSRP 79,96 USD"},
    {"nome": "Teste Vault Bundle Case", "edicao": "TST", "tipo": "case",
     "data": "2025-01-31", "conteudo": "12 vaults",
     "nota": "DÚVIDA: as fontes divergem — umas dizem 12 vaults, outras 4."},
    {"nome": "Teste Pre-Rift EVENT Kit", "edicao": "TST", "tipo": "bundle",
     "data": "2025-01-31", "conteudo": "16 kits de jogador + 1 display · MSRP 480 USD",
     "nota": "Não é o «Teste Pre-Rift Kit», que é o kit de UM jogador."},
]


class ExtraBase(Base):
    def setUp(self):
        super().setUp()
        self.escrever_catalogo(CAT)


# ---------------------------------------------------------------------------
# 1. Os produtos do `selado.extra`
# ---------------------------------------------------------------------------


class TestOsProdutosAMao(ExtraBase):

    def lista(self, **kw):
        self.cfg_selado({"extra": EXTRA, **kw})
        return self.selado.itens(self.con())

    def test_entram_na_lista_com_o_conteudo(self):
        display = self.por_id(self.lista(), "cfg-tst-teste-jinx-champion-deck-display")
        self.assertEqual(display["tipo"], "display")
        self.assertEqual(display["conteudo"], "4 decks iguais · MSRP 79,96 USD")
        self.assertEqual(display["data"], "2025-01-31")
        self.assertFalse(display["por_sair"])
        self.assertEqual(display["fonte"], "config")

    def test_o_msrp_em_dolares_nao_vira_preco(self):
        """Não há câmbio validado no riftvault — o MSRP fica no conteúdo e a
        linha diz «—», contada no `sem_preco`."""
        display = self.por_id(self.lista(), "cfg-tst-teste-jinx-champion-deck-display")
        self.assertIsNone(display["preco_cents"])
        self.assertEqual(display["valor_cents"], 0)
        self.assertIn("USD", display["conteudo"])

    def test_o_conteudo_e_a_nota_sao_campos_diferentes(self):
        """O conteúdo é o que vem dentro; a nota é a ressalva. Um «12 vaults»
        com uma fonte a dizer 4 tem de se ler como dúvida, não como facto."""
        case = self.por_id(self.lista(), "cfg-tst-teste-vault-bundle-case")
        self.assertEqual(case["conteudo"], "12 vaults")
        self.assertIn("DÚVIDA", case["nota"])
        self.assertNotIn("DÚVIDA", case["conteudo"])

    def test_um_produto_sem_conteudo_nao_rebenta(self):
        self.cfg_selado({"extra": [{"nome": "So o nome", "edicao": "TST"}]})
        x = self.por_id(self.selado.itens(self.con()), "cfg-tst-so-o-nome")
        self.assertIsNone(x["conteudo"])
        self.assertIsNone(x["nota"])

    def test_o_event_kit_e_o_kit_de_um_jogador_sao_dois_produtos(self):
        """O CardTrader só tem o kit de UM jogador; o EVENT Kit são 16 kits +
        um display. São produtos diferentes e aparecem os dois."""
        self.escrever_catalogo({**CAT, "produtos": CAT["produtos"] + [
            {"blueprint_id": 303, "nome": "Teste Pre-Rift Kit", "versao": "",
             "categoria_id": 261, "edicao": "TST", "edicao_nome": "Teste",
             "img": None, "cardmarket_id": None}]})
        nomes = [x["nome"] for x in self.lista()]
        self.assertIn("Teste Pre-Rift Kit", nomes)
        self.assertIn("Teste Pre-Rift EVENT Kit", nomes)
        kit = self.por_id(self.lista(), "ct-303")
        evento = self.por_id(self.lista(), "cfg-tst-teste-pre-rift-event-kit")
        self.assertIsNone(kit["conteudo"])
        self.assertIn("16 kits", evento["conteudo"])
        self.assertIn("UM jogador", evento["nota"])

    def test_os_extras_contam_no_do_config(self):
        p = self.selado.payload(self.con())
        self.assertEqual(p["totals"]["do_config"], 0)
        self.cfg_selado({"extra": EXTRA})
        p = self.selado.payload(self.con())
        self.assertEqual(p["totals"]["do_config"], 3)

    def test_tirar_um_do_config_tira_o_da_lista(self):
        self.assertEqual(len([x for x in self.lista() if x["fonte"] == "config"]), 3)
        self.cfg_selado({"extra": EXTRA[:1]})
        self.assertEqual(
            len([x for x in self.selado.itens(self.con()) if x["fonte"] == "config"]), 1)

    def test_os_botoes_funcionam_num_produto_do_config(self):
        con = self.con()
        self.cfg_selado({"extra": EXTRA})
        pid = "cfg-tst-teste-vault-bundle-case"
        self.selado.ajustar(con, pid, 2)
        self.assertEqual(self.por_id(self.selado.itens(con), pid)["qty"], 2)


# ---------------------------------------------------------------------------
# 2. Os acessórios, numa secção à parte
# ---------------------------------------------------------------------------


class TestOsAcessorios(ExtraBase):

    def test_entram_marcados_como_acessorio(self):
        lista = self.selado.itens(self.con())
        self.assertTrue(self.por_id(lista, "ct-301")["acessorio"])
        self.assertTrue(self.por_id(lista, "ct-302")["acessorio"])
        self.assertFalse(self.por_id(lista, "ct-101")["acessorio"])

    def test_nao_contam_para_o_produto_selado(self):
        """É a decisão: um binder não é um display. Os números do selado têm
        de ser os mesmos com a lista de acessórios cheia ou vazia."""
        p = self.selado.payload(self.con())
        com = dict(p["totals"])
        self.cfg_selado({"acessorios": []})
        sem = dict(self.selado.payload(self.con())["totals"])
        self.assertEqual(com, sem)

    def test_tem_contadores_e_valor_proprios(self):
        con = self.con()
        self.selado.ajustar(con, "ct-301", 1)
        p = self.selado.payload(con)
        at = p["acessorios"]["totals"]
        self.assertEqual(at["ha"], 2)
        self.assertEqual(at["tenho"], 1)
        self.assertEqual(at["falta"], 1)
        self.assertEqual(at["valor_cents"], 3399)
        # E o valor do SELADO não o apanha.
        self.assertEqual(p["totals"]["valor_cents"], 0)

    def test_o_valor_dos_acessorios_nao_se_soma_ao_do_selado(self):
        con = self.con()
        self.selado.ajustar(con, "ct-301", 1)    # binder, 33,99 €
        self.selado.ajustar(con, "ct-101", 1)    # booster box, 160,64 €
        p = self.selado.payload(con)
        self.assertEqual(p["totals"]["valor_cents"], 16064)
        self.assertEqual(p["acessorios"]["totals"]["valor_cents"], 3399)

    def test_os_botoes_funcionam_num_acessorio(self):
        con = self.con()
        self.selado.ajustar(con, "ct-301", 3)
        self.assertEqual(self.por_id(self.selado.itens(con), "ct-301")["qty"], 3)
        self.selado.ajustar(con, "ct-301", -5)
        self.assertEqual(self.por_id(self.selado.itens(con), "ct-301")["qty"], 0)

    def test_sairam_do_fora_e_voltam_la_com_a_lista_vazia(self):
        fora = {x["categoria_id"]: x["n"] for x in self.selado.fora()}
        self.assertNotIn(265, fora)
        self.assertNotIn(267, fora)
        self.cfg_selado({"acessorios": []})
        fora = {x["categoria_id"]: x["n"] for x in self.selado.fora()}
        self.assertEqual(fora[265], 1)
        self.assertEqual(fora[267], 1)
        self.assertEqual(self.selado.payload(self.con())["acessorios"]["totals"]["ha"], 0)

    def test_as_playmats_e_as_sleeves_continuam_fora(self):
        """Ficaram de fora de propósito: são acessórios de JOGO, e no catálogo
        real são 79 linhas a afogar as do selado."""
        fora = {x["categoria_id"]: x["n"] for x in self.selado.fora()}
        self.assertEqual(fora[264], 1)
        self.assertEqual(fora[266], 2)

    def test_os_por_sair_valem_tambem_nos_acessorios(self):
        self.escrever_catalogo({**CAT, "produtos": CAT["produtos"] + [
            {"blueprint_id": 304, "nome": "Futuro Binder", "versao": "",
             "categoria_id": 265, "edicao": "FUT", "edicao_nome": "Futuro",
             "img": None, "cardmarket_id": None}]})
        at = self.selado.payload(self.con())["acessorios"]["totals"]
        self.assertEqual(at["ha"], 3)
        self.assertEqual(at["por_sair"], 1)
        self.assertEqual(at["falta"], 2)      # o por sair não conta na falta

    def test_uma_categoria_nas_duas_listas_rebenta(self):
        self.cfg_selado({"acessorios": [265, 262]})
        with self.assertRaises(ValueError) as e:
            self.selado.opcoes()
        self.assertIn("262", str(e.exception))

    def test_as_cartas_nos_acessorios_rebentam(self):
        self.cfg_selado({"acessorios": [258]})
        with self.assertRaises(ValueError) as e:
            self.selado.opcoes()
        self.assertIn("258", str(e.exception))

    def test_uma_lista_mal_escrita_rebenta(self):
        self.cfg_selado({"acessorios": ["binders"]})
        with self.assertRaises(ValueError):
            self.selado.opcoes()

    def test_tem_tipo_proprio_e_nao_outro(self):
        """«Outro» num binder não diz nada — a secção tem os seus dois tipos."""
        lista = self.selado.itens(self.con())
        self.assertEqual(self.por_id(lista, "ct-301")["tipo"], "binder")
        self.assertEqual(self.por_id(lista, "ct-301")["tipo_label"], "Binder")
        self.assertEqual(self.por_id(lista, "ct-302")["tipo"], "deck-box")
        self.assertEqual(self.por_id(lista, "ct-302")["tipo_label"], "Deck box")

    def test_o_payload_diz_o_que_e_preciso_para_a_seccao(self):
        p = self.selado.payload(self.con())
        self.assertEqual(p["scope"]["acessorios"], [265, 267])
        self.assertEqual([c["id"] for c in p["acessorios"]["categorias"]], [265, 267])
        self.assertTrue(p["acessorios"]["sets"])
        # O `items` traz tudo (é a lista de ids que o `ajustar` valida).
        self.assertIn("ct-301", [x["id"] for x in p["items"]])
        self.assertNotIn("ct-301", [x["id"] for g in p["sets"] for x in g["items"]])

    def test_o_cli_escreve_a_seccao_a_parte(self):
        texto = self.selado.texto(self.selado.payload(self.con()))
        self.assertIn("ACESSÓRIOS", texto)
        self.assertIn("NÃO contam para o produto selado", texto)


# ---------------------------------------------------------------------------
# 3. Os blueprints repetidos do CardTrader
# ---------------------------------------------------------------------------


class TestOsDuplicados(ExtraBase):

    def test_junta_os_dois_blueprints_do_mesmo_produto(self):
        ids = [x["id"] for x in self.selado.itens(self.con())]
        self.assertIn("ct-402", ids)
        self.assertNotIn("ct-401", ids)

    def test_fica_o_que_o_mercado_usa(self):
        """O que fica é o que tem id do Cardmarket e ofertas — medido nos
        Trial Decks reais: os que saem têm ZERO ofertas."""
        x = self.por_id(self.selado.itens(self.con()), "ct-402")
        self.assertEqual(x["cardmarket_id"], 900402)
        self.assertEqual(x["preco_cents"], 10064)
        self.assertEqual([d["blueprint_id"] for d in x["duplicados"]], [401])

    def test_nao_junta_as_cegas_a_versao_conta(self):
        """Os «2024 Trial Deck Set» e «2025 Trial Deck Set» têm o mesmo nome e
        são dois produtos: o ano está na versão."""
        ids = [x["id"] for x in self.selado.itens(self.con())]
        self.assertIn("ct-411", ids)
        self.assertIn("ct-412", ids)

    def test_desligar_mostra_os_dois(self):
        self.cfg_selado({"juntar_duplicados": False})
        ids = [x["id"] for x in self.selado.itens(self.con())]
        self.assertIn("ct-401", ids)
        self.assertIn("ct-402", ids)
        self.assertEqual(
            self.por_id(self.selado.itens(self.con()), "ct-402")["duplicados"], [])

    def test_o_que_ele_tinha_gravado_no_outro_continua_a_contar(self):
        """Juntar duas linhas do catálogo deles não pode apagar unidades
        dele."""
        con = self.con()
        self.cfg_selado({"juntar_duplicados": False})
        self.selado.ajustar(con, "ct-401", 2)
        self.cfg_selado({"juntar_duplicados": True})
        self.assertEqual(self.por_id(self.selado.itens(con), "ct-402")["qty"], 2)

    def test_juntar_baixa_o_que_ha_em_um(self):
        antes = self.selado.payload(self.con())["totals"]["ha"]
        self.cfg_selado({"juntar_duplicados": False})
        depois = self.selado.payload(self.con())["totals"]["ha"]
        self.assertEqual(depois, antes + 1)

    def test_o_payload_e_o_cli_dizem_quantos_juntou(self):
        p = self.selado.payload(self.con())
        self.assertEqual(p["scope"]["juntos"], 1)
        self.assertTrue(p["scope"]["juntar_duplicados"])
        self.assertIn("junta o blueprint 401", self.selado.texto(p))

    def test_um_produto_juntado_nao_e_um_id_valido(self):
        with self.assertRaises(self.selado.ProdutoDesconhecido):
            self.selado.ajustar(self.con(), "ct-401", 1)


# ---------------------------------------------------------------------------
# 4. O config a sério
# ---------------------------------------------------------------------------


class TestOConfigReal(unittest.TestCase):
    """Os 17 produtos, a data do Proving Grounds e as duas listas, no
    `riftvault_config.json` do repositório."""

    def setUp(self):
        self.cfg = json.loads((REPO / "riftvault_config.json").read_text(encoding="utf-8"))
        self.sel = self.cfg["selado"]

    def test_o_proving_grounds_tem_data(self):
        """Ficou sem data porque ele não a deu; é da era da Origins."""
        self.assertEqual(self.sel["datas_por_edicao"]["OGS"], "2025-10-31")

    def test_os_acessorios_estao_desligados(self):
        """Entraram a 2026-09-25 de manhã (binders 265 e deck boxes 267) e
        SAÍRAM à noite, no mesmo dia: *«Tira os acessórios todos — binders,
        sleeves e deck boxes»*. A lista fica VAZIA, não se apaga: repor é
        escrever os números outra vez. O código da secção também ficou."""
        self.assertEqual(self.sel["acessorios"], [])

    def test_os_dezassete_produtos(self):
        self.assertEqual(len(self.sel["extra"]), 17)

    def test_os_sete_displays_de_champion_decks(self):
        nomes = [x["nome"] for x in self.sel["extra"]
                 if "Champion Deck Display" in x["nome"]]
        self.assertEqual(len(nomes), 7)
        for quem in ("Jinx", "Viktor", "Lee Sin", "Rumble", "Fiora", "Vi", "Vex"):
            self.assertTrue(any(f'"{quem}"' in n for n in nomes), quem)
        for x in self.sel["extra"]:
            if "Champion Deck Display" in x["nome"]:
                self.assertEqual(x["tipo"], "display")
                self.assertIn("4 decks iguais", x["conteudo"])

    def test_os_dois_displays_de_showdown(self):
        showdown = [x for x in self.sel["extra"] if "Showdown" in x["nome"]]
        self.assertEqual([x["edicao"] for x in showdown], ["VEN", "RAD"])
        for x in showdown:
            self.assertEqual(x["tipo"], "display")
            self.assertIn("4 conjuntos", x["conteudo"])

    def test_os_quatro_cases(self):
        cases = [x for x in self.sel["extra"] if x["tipo"] == "case"]
        self.assertEqual(sorted(x["edicao"] for x in cases),
                         ["OGS", "RAD", "UNL", "VEN"])
        for x in cases:
            if x["edicao"] == "OGS":
                self.assertIn("6 caixas", x["conteudo"])
            else:
                self.assertIn("12 vaults", x["conteudo"])

    def test_a_duvida_do_case_da_unleashed_esta_escrita(self):
        """Uma fonte diz 4 vaults, outra 12. Fica 12 e a dúvida ao lado — não
        se inventa."""
        unl = next(x for x in self.sel["extra"]
                   if x["nome"] == "Unleashed Vault Bundle Case")
        self.assertIn("12 vaults", unl["conteudo"])
        self.assertIn("4", unl["nota"])
        self.assertIn("confirmar", unl["nota"].lower())

    def test_os_quatro_pre_rift_event_kits(self):
        kits = [x for x in self.sel["extra"] if "EVENT Kit" in x["nome"]]
        self.assertEqual(sorted(x["edicao"] for x in kits),
                         ["RAD", "SFD", "UNL", "VEN"])
        for x in kits:
            self.assertEqual(x["tipo"], "bundle")
            self.assertIn("16 kits de jogador + 1 display", x["conteudo"])
            # A nota tem de dizer que NÃO é o kit de um jogador do CardTrader,
            # senão lêem-se como o mesmo produto.
            self.assertIn("UM jogador", x["nota"])

    def test_nenhum_extra_leva_preco_em_euros(self):
        """Os MSRP dele são em dólares e ficam no conteúdo."""
        for x in self.sel["extra"]:
            self.assertIsNone(x.get("preco_eur"), x["nome"])

    def test_o_config_real_le_se(self):
        from riftvault import selado
        op = selado.opcoes(self.cfg)
        self.assertEqual(len(op["extra"]), 17)
        self.assertEqual(op["acessorios"], [])
        self.assertTrue(op["juntar_duplicados"])


# ---------------------------------------------------------------------------
# 5. A FOTOGRAFIA: nada disto mexe num número da Coleção
# ---------------------------------------------------------------------------


class TestNaoMexeNaColecao(ExtraBase):
    """A defesa de sempre — a das cópias próprias (21/09), a do foil (22/09) e
    a da Venda (25/09). Com os extras, com os acessórios e com os duplicados
    juntos, e com unidades gravadas em todos eles, a Coleção tem de dar
    exactamente o mesmo."""

    # A MESMA fotografia do `test_selado` — níveis, denominador, wantlist,
    # valor, totais, grelha, playset, barras, painel, foil, blocos, Faltas,
    # Encomendas, A mais, decks, uso, Venda, `copies`, locais e `ops`. Uma
    # segunda definição de «o que é um número da Coleção» era uma segunda
    # resposta à mesma pergunta.
    fotografia = _sel.TestNaoEntraNaColecao.fotografia

    def test_nada_mexe(self):
        con = self.catalogo()
        self.cfg_selado({"extra": EXTRA})
        antes = json.dumps(self.fotografia(con), sort_keys=True, default=str)

        for pid, n in (("ct-101", 2), ("ct-301", 1), ("ct-302", 3), ("ct-402", 1),
                       ("cfg-tst-teste-vault-bundle-case", 4)):
            self.selado.ajustar(con, pid, n)
        p = self.selado.payload(con)
        self.assertEqual(p["totals"]["copias"], 7)          # 2 + 1 + 4
        self.assertEqual(p["acessorios"]["totals"]["copias"], 4)
        self.assertEqual(
            json.dumps(self.fotografia(con), sort_keys=True, default=str), antes,
            "meter produto selado, acessórios ou extras mexeu na Coleção")

        for pid, n in (("ct-101", -2), ("ct-301", -1), ("ct-302", -3), ("ct-402", -1),
                       ("cfg-tst-teste-vault-bundle-case", -4)):
            self.selado.ajustar(con, pid, n)
        self.assertEqual(
            json.dumps(self.fotografia(con), sort_keys=True, default=str), antes)

    def test_a_fotografia_nao_e_de_zeros(self):
        """Senão o teste de cima passava com tudo apagado."""
        con = self.catalogo()
        f = self.fotografia(con)
        self.assertGreater(f["valor"]["cents"], 0)
        self.assertTrue(f["denominador"])
        self.assertTrue(f["grelha"])

    def test_nenhum_modulo_de_contas_sabe_dos_acessorios(self):
        """O `selado` continua a ser lido só pelo `server`, o `build` e a
        `cli` — se um módulo de contas o importar, o selado entrou numa
        conta."""
        for nome in ("a_mais", "a_subir", "faltas", "faltas_edicao", "uso_decks",
                     "decks", "locais", "pending", "prices", "painel", "foil",
                     "metrics", "proprias", "venda", "cardmarket", "catalog"):
            fonte = (REPO / "riftvault" / f"{nome}.py").read_text(encoding="utf-8")
            self.assertNotIn("sealed_copies", fonte, nome)
            self.assertNotIn("import selado", fonte, nome)


# ---------------------------------------------------------------------------
# 6. A página
# ---------------------------------------------------------------------------


class TestAPagina(unittest.TestCase):

    def setUp(self):
        self.js = APP_JS.read_text(encoding="utf-8")
        self.css = CSS.read_text(encoding="utf-8")

    def test_a_seccao_dos_acessorios_desenha_se(self):
        self.assertIn("sl-acess-cab", self.js)
        self.assertIn("p.acessorios", self.js)
        self.assertIn(".sl-acess-cab", self.css)

    def test_ha_um_botao_que_a_esconde(self):
        self.assertIn("sl-acess", self.js)
        self.assertIn("selAcess", self.js)
        # Começa à vista.
        self.assertIn("selAcess: true", self.js)

    def test_o_cabecalho_diz_que_os_acessorios_nao_contam(self):
        i = self.js.index("sl-acess-cab")
        troco = self.js[i:i + 400]
        self.assertIn("não contam", troco)

    def test_o_subtitulo_do_cabecalho_nao_e_capitalizado(self):
        """O `.section-head` capitaliza cada palavra, e o subtítulo é uma
        frase — sem isto lia-se «Binders E Deck Boxes — Não Contam Para O
        Produto Selado»."""
        i = self.css.index(".sl-acess-cab small")
        self.assertIn("text-transform: none", self.css[i:i + 200])

    def test_o_conteudo_e_a_nota_sao_marcas_diferentes(self):
        self.assertIn("sl-marca dentro", self.js)
        self.assertIn("sl-marca nota", self.js)
        self.assertIn(".sl-marca.dentro", self.css)
        self.assertIn(".sl-marca.nota", self.css)

    def test_a_linha_diz_que_blueprints_juntou(self):
        self.assertIn("x.duplicados", self.js)
        self.assertIn("sl-marca dup", self.js)

    def test_a_ajuda_explica_as_duas_decisoes(self):
        i = self.js.index("'selado': {")
        troco = self.js[i:i + 3200]
        self.assertIn("binders e os deck boxes", troco)
        self.assertIn("dois blueprints para o mesmo produto", troco)
        self.assertIn("MSRP são em dólares", troco)


if __name__ == "__main__":
    unittest.main()

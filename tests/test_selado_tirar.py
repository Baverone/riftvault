"""Tirar produtos do «Produto Selado» por config (André, 2026-09-25).

Ele viu a lista dos 98 e mandou fora 22: os 13 BOOSTERS SOLTOS, as 3 SLIM
BOOSTER BOX, o «Origins: Champion Deck Set» (*"compram-se à unidade"*), as
«Spiritforged Bulk Runes» e os 4 PRE-RIFT KIT de UM jogador.

DUAS COISAS, E UM BLOCO DE TESTES POR CADA

1. `selado.excluidos` — ESCONDER NÃO É APAGAR
   A mesma ideia do `abas.escondidas`: o `data/selado_catalogo.json` fica
   intacto e **repor é tirar o nome da lista**. Os excluídos saem da aba, dos
   contadores, da percentagem e do total, nos dois modos. O nome é EXACTO — é
   isso que faz o «Pre-Rift Kit» sair e o «Pre-Rift EVENT Kit» ficar — e um
   nome que não case REBENTA, porque um nome mal escrito ignorado em silêncio
   deixava-o a olhar para um produto que mandou tirar.

2. O NOME DOBRADO DO CATÁLOGO
   O CardTrader escreve «2024 Trial Deck Set **Set**». `nome_limpo` junta a
   palavra repetida; é apresentação e o `id` não muda.

E, por cima, a defesa de sempre: **nada disto mexe num número da Coleção** — a
fotografia do `test_selado`, por referência, para não haver duas definições de
«número da Coleção».
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

REPO = Path(__file__).resolve().parent.parent

# O catálogo de brincar do `test_selado`, mais o que esta ordem obriga a ter:
# um par «X» / «X EVENT Kit» (o nome de um está DENTRO do outro), um par
# «Booster» / «| Nexus Night Promo Booster», e um nome com palavra dobrada.
CAT = json.loads(json.dumps(CATALOGO))
CAT["produtos"] += [
    {"blueprint_id": 501, "nome": "Teste Pre-Rift Kit", "versao": "",
     "categoria_id": 261, "edicao": "TST", "edicao_nome": "Teste",
     "img": None, "cardmarket_id": 900501},
    {"blueprint_id": 502, "nome": "Teste | Nexus Night Promo Booster", "versao": "",
     "categoria_id": 260, "edicao": "TST", "edicao_nome": "Teste",
     "img": None, "cardmarket_id": None},
    {"blueprint_id": 503, "nome": "Teste Slim Booster Box", "versao": "",
     "categoria_id": 259, "edicao": "TST", "edicao_nome": "Teste",
     "img": None, "cardmarket_id": None},
    {"blueprint_id": 504, "nome": "2024 Teste Deck Set Set", "versao": "©2024",
     "categoria_id": 262, "edicao": "TST", "edicao_nome": "Teste",
     "img": None, "cardmarket_id": None},
]
CAT["precos"]["501"] = {"cents": 4000, "currency": "EUR", "day": "2026-09-25",
                        "n_listings": 2, "n_sellers": 2, "n_copies": 2}
CAT["precos"]["503"] = {"cents": 9000, "currency": "EUR", "day": "2026-09-25",
                        "n_listings": 5, "n_sellers": 5, "n_copies": 6}

# O «EVENT Kit» vem do config, como os 4 reais.
EVENT_KIT = {"nome": "Teste Pre-Rift EVENT Kit", "edicao": "TST", "tipo": "bundle",
             "data": "2025-01-31",
             "conteudo": "16 kits de jogador + 1 display · MSRP 480 USD",
             "nota": "Não é o «Teste Pre-Rift Kit», que é o kit de UM jogador."}


class TirarBase(Base):
    def setUp(self):
        super().setUp()
        self.escrever_catalogo(CAT)

    def lista(self, excluidos=None, **kw):
        self.cfg_selado({"extra": [EVENT_KIT],
                         **({"excluidos": excluidos} if excluidos is not None else {}),
                         **kw})
        return [x for x in self.selado.itens(self.con()) if not x["acessorio"]]

    def nomes(self, *a, **kw):
        return [x["nome"] for x in self.lista(*a, **kw)]


# ---------------------------------------------------------------------------
# 1. A chave, e a gramática dela
# ---------------------------------------------------------------------------


class TestAChave(TirarBase):

    def test_sem_a_chave_nada_sai(self):
        """A omissão é a lista vazia: um riftvault sem a chave mostra tudo."""
        self.assertEqual(self.selado.DEFAULTS["excluidos"], [])
        self.cfg_selado({"extra": [EVENT_KIT]})
        sem_chave = [x["id"] for x in self.selado.itens(self.con())]
        self.assertEqual(sem_chave, [x["id"] for x in self.lista([])])
        self.assertEqual(self.selado.payload(self.con())["scope"]["excluidos"], [])

    def test_o_nome_tira_o_produto(self):
        antes = self.nomes()
        self.assertIn("Teste Booster", antes)
        depois = self.nomes(["Teste Booster"])
        self.assertNotIn("Teste Booster", depois)
        self.assertEqual(len(depois), len(antes) - 1)

    def test_o_id_tambem_serve(self):
        self.assertNotIn("Teste Booster", self.nomes(["ct-106"]))

    def test_o_nome_e_exacto_e_nao_um_pedaco(self):
        """A regra que mais importa: «Teste Pre-Rift Kit» é o kit de UM
        jogador, e o «Teste Pre-Rift EVENT Kit» tem de FICAR."""
        depois = self.nomes(["Teste Pre-Rift Kit"])
        self.assertNotIn("Teste Pre-Rift Kit", depois)
        self.assertIn("Teste Pre-Rift EVENT Kit", depois)

    def test_o_booster_sai_sem_levar_o_promo_booster(self):
        depois = self.nomes(["Teste Booster"])
        self.assertNotIn("Teste Booster", depois)
        self.assertIn("Teste | Nexus Night Promo Booster", depois)
        self.assertIn("Teste Booster Box", depois)
        self.assertIn("Teste Booster Box Case", depois)

    def test_a_slim_booster_box_sai_sem_levar_a_booster_box(self):
        depois = self.nomes(["Teste Slim Booster Box"])
        self.assertNotIn("Teste Slim Booster Box", depois)
        self.assertIn("Teste Booster Box", depois)

    def test_maiusculas_e_espacos_a_mais_nao_contam(self):
        self.assertNotIn("Teste Booster", self.nomes(["  teste   BOOSTER "]))

    def test_um_nome_que_nao_case_rebenta(self):
        with self.assertRaises(ValueError) as e:
            self.nomes(["Teste Bosoter"])
        self.assertIn("Teste Bosoter", str(e.exception))

    def test_a_mensagem_diz_os_parecidos(self):
        with self.assertRaises(ValueError) as e:
            self.nomes(["Teste Bostr"])
        self.assertIn("Teste Booster", str(e.exception))

    def test_uma_entrada_que_nao_e_texto_rebenta(self):
        for mau in (123, None, "", "   "):
            with self.assertRaises(ValueError):
                self.nomes([mau])

    def test_a_lista_mal_escrita_rebenta(self):
        with self.assertRaises(ValueError):
            self.nomes("Teste Booster")           # uma string, não uma lista

    def test_um_nome_que_case_com_dois_produtos_rebenta_e_diz_os_ids(self):
        """Hoje nenhum dos 117 nomes se repete, mas a regra tem de existir:
        adivinhar qual dos dois era tirar o produto errado."""
        cat = json.loads(json.dumps(CAT))
        cat["produtos"] += [
            {"blueprint_id": 601, "nome": "Teste Repetido", "versao": "A",
             "categoria_id": 261, "edicao": "TST", "edicao_nome": "Teste",
             "img": None, "cardmarket_id": None},
            {"blueprint_id": 602, "nome": "Teste Repetido", "versao": "B",
             "categoria_id": 261, "edicao": "TST", "edicao_nome": "Teste",
             "img": None, "cardmarket_id": None}]
        self.escrever_catalogo(cat)
        with self.assertRaises(ValueError) as e:
            self.nomes(["Teste Repetido"])
        self.assertIn("ct-601", str(e.exception))
        self.assertIn("ct-602", str(e.exception))
        # E com o id escolhe-se um sem rebentar.
        nomes = self.nomes(["ct-601"])
        self.assertEqual(sum(1 for n in nomes if n == "Teste Repetido"), 1)

    def test_um_produto_do_config_tambem_se_pode_tirar(self):
        self.assertNotIn("Teste Pre-Rift EVENT Kit",
                         self.nomes(["Teste Pre-Rift EVENT Kit"]))

    def test_um_acessorio_tambem_se_pode_tirar(self):
        self.escrever_catalogo({**CAT, "produtos": CAT["produtos"] + [
            {"blueprint_id": 701, "nome": "Teste Binder", "versao": "",
             "categoria_id": 265, "edicao": "TST", "edicao_nome": "Teste",
             "img": None, "cardmarket_id": None}]})
        self.cfg_selado({"acessorios": [265]})
        self.assertIn("ct-701", [x["id"] for x in self.selado.itens(self.con())])
        self.cfg_selado({"acessorios": [265], "excluidos": ["Teste Binder"]})
        self.assertNotIn("ct-701", [x["id"] for x in self.selado.itens(self.con())])

    def test_sem_catalogo_em_disco_nao_rebenta(self):
        """Sem o ficheiro a secção mostra-se vazia (ou só com os `extra`), a
        dizer que é preciso sincronizar — não rebenta por um nome do CardTrader
        não poder casar contra nada. É o caso do `build` num `data/` limpo."""
        self.config.SELADO_PATH.unlink()
        self.selado._cache = None
        self.cfg_selado({"excluidos": ["Teste Booster"]})
        self.assertEqual(self.selado.itens(self.con()), [])
        # E um `extra` continua a poder ser tirado, porque esse a app conhece.
        self.cfg_selado({"extra": [EVENT_KIT], "excluidos": ["Teste Booster"]})
        self.assertEqual([x["id"] for x in self.selado.itens(self.con())],
                         ["cfg-tst-teste-pre-rift-event-kit"])
        self.cfg_selado({"extra": [EVENT_KIT],
                         "excluidos": ["Teste Pre-Rift EVENT Kit"]})
        self.assertEqual(self.selado.itens(self.con()), [])

    def test_um_nome_ambiguo_rebenta_mesmo_sem_catalogo(self):
        """A tolerância é só para o nome que não casa com NADA: escolher um de
        dois tirava o produto errado."""
        self.config.SELADO_PATH.unlink()
        self.selado._cache = None
        self.cfg_selado({"extra": [EVENT_KIT, {**EVENT_KIT, "edicao": "FUT"}],
                         "excluidos": ["Teste Pre-Rift EVENT Kit"]})
        with self.assertRaises(ValueError) as e:
            self.selado.itens(self.con())
        self.assertIn("casa com 2 produtos", str(e.exception))


# ---------------------------------------------------------------------------
# 2. Saem da aba, dos contadores e do total — e REPOR é tirar da lista
# ---------------------------------------------------------------------------


class TestSaemDeTudo(TirarBase):

    def test_saem_dos_contadores_e_da_percentagem(self):
        con = self.con()
        self.cfg_selado({"extra": [EVENT_KIT]})
        antes = self.selado.payload(con)["totals"]
        self.cfg_selado({"extra": [EVENT_KIT],
                         "excluidos": ["Teste Booster", "Teste Slim Booster Box"]})
        depois = self.selado.payload(con)["totals"]
        self.assertEqual(depois["ha"], antes["ha"] - 2)
        self.assertEqual(depois["saiu"], antes["saiu"] - 2)
        self.assertEqual(depois["falta"], antes["falta"] - 2)

    def test_saem_do_valor_do_selado(self):
        """Uma unidade gravada num produto excluído não pode somar ao total do
        que está no ecrã."""
        con = self.con()
        self.cfg_selado({"extra": [EVENT_KIT]})
        self.selado.ajustar(con, "ct-503", 2)          # 2 × 90,00 €
        self.selado.ajustar(con, "ct-101", 1)          # 1 × 160,64 €
        self.assertEqual(self.selado.payload(con)["totals"]["valor_cents"],
                         2 * 9000 + 16064)
        self.cfg_selado({"extra": [EVENT_KIT], "excluidos": ["Teste Slim Booster Box"]})
        t = self.selado.payload(con)["totals"]
        self.assertEqual(t["valor_cents"], 16064)
        self.assertEqual(t["copias"], 1)
        self.assertEqual(t["tenho"], 1)

    def test_a_unidade_gravada_nao_se_apaga_e_volta_ao_repor(self):
        """ESCONDER NÃO É APAGAR: a `sealed_copies` fica como estava."""
        con = self.con()
        self.cfg_selado({"extra": [EVENT_KIT]})
        self.selado.ajustar(con, "ct-503", 2)
        self.cfg_selado({"extra": [EVENT_KIT], "excluidos": ["Teste Slim Booster Box"]})
        self.selado.payload(con)
        self.assertEqual(self.selado.tenho(con).get("ct-503"), 2,
                         "a contagem dele continua gravada")
        self.cfg_selado({"extra": [EVENT_KIT]})
        self.assertEqual(self.por_id(self.selado.itens(con), "ct-503")["qty"], 2)

    def test_repor_e_so_tirar_o_nome_da_lista(self):
        con = self.con()
        self.cfg_selado({"extra": [EVENT_KIT]})
        alvo = json.dumps(self.selado.payload(con), sort_keys=True, default=str)
        self.cfg_selado({"extra": [EVENT_KIT], "excluidos": [
            "Teste Booster", "Teste Slim Booster Box", "Teste Pre-Rift Kit",
            "Teste Vault", "ct-107"]})
        p = self.selado.payload(con)
        self.assertEqual(len(p["scope"]["excluidos"]), 5)
        self.cfg_selado({"extra": [EVENT_KIT], "excluidos": []})
        self.assertEqual(json.dumps(self.selado.payload(con), sort_keys=True,
                                    default=str).replace(
                             self.selado.payload(con)["generated_at"], ""),
                         alvo.replace(json.loads(alvo)["generated_at"], ""),
                         "tirar os nomes da lista repõe o payload inteiro")

    def test_o_catalogo_em_disco_fica_intacto(self):
        antes = self.config.SELADO_PATH.read_bytes()
        self.cfg_selado({"excluidos": ["Teste Booster", "Teste Vault"]})
        self.selado.payload(self.con())
        self.assertEqual(self.config.SELADO_PATH.read_bytes(), antes)

    def test_o_scope_diz_quais_sairam(self):
        """Nada desaparece em silêncio."""
        self.cfg_selado({"excluidos": ["Teste Booster", "ct-105"]})
        ex = self.selado.payload(self.con())["scope"]["excluidos"]
        self.assertEqual({x["id"] for x in ex}, {"ct-106", "ct-105"})
        por_id = {x["id"]: x for x in ex}
        self.assertEqual(por_id["ct-106"]["nome"], "Teste Booster")
        self.assertEqual(por_id["ct-106"]["tipo"], "booster")
        self.assertEqual(por_id["ct-106"]["tipo_label"], "Booster")
        self.assertEqual(por_id["ct-106"]["edicao"], "TST")

    def test_os_botoes_recusam_um_excluido_e_dizem_como_repor(self):
        con = self.con()
        self.cfg_selado({"excluidos": ["Teste Booster"]})
        with self.assertRaises(self.selado.ProdutoExcluido) as e:
            self.selado.ajustar(con, "ct-106", 1)
        self.assertIn("selado.excluidos", str(e.exception))
        # É subclasse do desconhecido: quem tratava um, trata os dois.
        self.assertIsInstance(e.exception, self.selado.ProdutoDesconhecido)
        with self.assertRaises(self.selado.ProdutoDesconhecido):
            self.selado.ajustar(con, "ct-999999", 1)

    def test_ler_nao_escreve(self):
        con = self.con()
        self.cfg_selado({"excluidos": ["Teste Booster"]})
        self.selado.payload(con)
        self.selado.itens(con)
        self.selado.excluidos()
        self.assertEqual(self.selado.tenho(con), {})

    def test_o_site_publicado_tambem_os_esconde(self):
        """A mesma linha de config tira o produto do 8770 e do site gerado."""
        con = self.con()
        self.cfg_selado({"excluidos": ["Teste Booster"]})
        for editable in (True, False):
            p = self.selado.payload(con, editable=editable)
            self.assertNotIn("ct-106", [x["id"] for x in p["items"]])
            self.assertEqual(len(p["scope"]["excluidos"]), 1)

    def test_o_cli_diz_quais_foram_tirados(self):
        self.cfg_selado({"excluidos": ["Teste Booster"]})
        t = self.selado.texto(self.selado.payload(self.con()))
        self.assertIn("selado.excluidos", t)
        self.assertIn("Teste Booster", t)
        self.assertIn("intacto", t)


# ---------------------------------------------------------------------------
# 3. Os 22 do config REAL — e os que têm de ficar
# ---------------------------------------------------------------------------


class TestOConfigReal(unittest.TestCase):
    """Lê o `riftvault_config.json` do repo. Não abre base nenhuma."""

    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads((REPO / "riftvault_config.json").read_text(encoding="utf-8"))
        cls.excl = cls.cfg["selado"]["excluidos"]

    def test_a_chave_existe_e_tem_22(self):
        self.assertEqual(len(self.excl), 22)
        self.assertEqual(len(set(self.excl)), 22, "sem repetidos")

    def test_os_13_boosters_soltos(self):
        for n in ("Origins Booster", "Origins Sleeved Booster", "Origins Slim Booster",
                  "Spiritforged Booster", "Spiritforged Slim Booster",
                  "Unleashed Booster", "Unleashed Sleeved Booster",
                  "Unleashed Slim Booster", "Vendetta Booster", "Radiance Booster",
                  "Radiance Sleeved Booster", "Legacy Booster",
                  "The Reckoning Booster"):
            self.assertIn(n, self.excl)

    def test_as_3_slim_booster_box_o_deck_set_e_as_bulk_runes(self):
        for n in ("Origins Slim Booster Box", "Spiritforged Slim Booster Box",
                  "Unleashed Slim Booster Box", "Origins: Champion Deck Set",
                  "Spiritforged Bulk Runes"):
            self.assertIn(n, self.excl)

    def test_os_4_pre_rift_kit_de_um_jogador(self):
        for e in ("Spiritforged", "Unleashed", "Vendetta", "Radiance"):
            self.assertIn(f"{e} Pre-Rift Kit", self.excl)

    def test_os_4_pre_rift_event_kit_ficam(self):
        """O de 16 kits + 1 display, que ele acabou de acrescentar. Só sai o de
        um jogador."""
        for e in ("Spiritforged", "Unleashed", "Vendetta", "Radiance"):
            self.assertNotIn(f"{e} Pre-Rift EVENT Kit", self.excl)
        nomes = [x["nome"] for x in self.cfg["selado"]["extra"]]
        self.assertEqual(sum(1 for n in nomes if "Pre-Rift EVENT Kit" in n), 4)

    def test_os_displays_de_decks_ficam(self):
        """Os 7 de champion e os 2 de showdown. O que saiu foi o «Champion Deck
        Set» da Origins, que é outro produto."""
        nomes = [x["nome"] for x in self.cfg["selado"]["extra"]]
        displays = [n for n in nomes if "Deck Display" in n or "Decks Display" in n]
        self.assertEqual(len(displays), 9)
        for n in displays:
            self.assertNotIn(n, self.excl)

    def test_nada_de_nexus_night_de_trial_deck_nem_de_promo_pack_saiu(self):
        for pedaco in ("Nexus Night", "Trial Deck", "Promo Pack",
                       "Replacement Card Booster"):
            maus = [n for n in self.excl if pedaco.lower() in n.lower()]
            self.assertEqual(maus, [], f"{pedaco} não era para sair")

    def test_nem_as_booster_box_normais_os_cases_os_vaults_ou_o_proving_grounds(self):
        for n in self.excl:
            baixo = n.lower()
            self.assertNotIn("booster box case", baixo)
            self.assertNotIn("vault", baixo)
            self.assertNotIn("proving grounds", baixo)
            if baixo.endswith("booster box"):
                self.assertTrue(baixo.endswith("slim booster box"),
                                f"{n} não é uma slim booster box")


class TestOs22ContraOCatalogoReal(unittest.TestCase):
    """Os 22 nomes contra o `data/selado_catalogo.json` do repo: cada um casa
    com UM produto, e nenhum casa com os que têm de ficar."""

    @classmethod
    def setUpClass(cls):
        os.environ["RIFTVAULT_CONFIG"] = str(REPO / "riftvault_config.json")
        import importlib
        from riftvault import config, selado
        importlib.reload(config)
        config.load.cache_clear()
        importlib.reload(selado)
        cls.selado, cls.config = selado, config
        cls.cfg = config.load()
        cls.op = selado.opcoes(cls.cfg)

    @classmethod
    def tearDownClass(cls):
        import importlib
        import tempfile
        os.environ["RIFTVAULT_CONFIG"] = str(
            Path(tempfile.gettempdir()) / "riftvault-nao-existe.json")
        importlib.reload(cls.config)
        cls.config.load.cache_clear()

    def test_saem_exactamente_22_e_cada_nome_casa_com_um(self):
        ex = self.selado.excluidos(self.cfg)
        self.assertEqual(len(ex), 22)
        self.assertEqual(len({x["id"] for x in ex}), 22)

    def test_a_aba_fica_com_76_selados(self):
        lista = [x for x in self.selado.itens(None, self.cfg) if not x["acessorio"]]
        self.assertEqual(len(lista), 76, "98 − 22")

    def test_os_19_acessorios_nao_mexeram(self):
        lista = [x for x in self.selado.itens(None, self.cfg) if x["acessorio"]]
        self.assertEqual(len(lista), 19)

    def test_os_que_tem_de_ficar_ficam(self):
        nomes = {x["nome"] for x in self.selado.itens(None, self.cfg)}
        for n in ("Spiritforged Pre-Rift EVENT Kit", "Unleashed Pre-Rift EVENT Kit",
                  "Vendetta Pre-Rift EVENT Kit", "Radiance Pre-Rift EVENT Kit",
                  'Origins: "Jinx" Champion Deck Display',
                  'Vendetta: "Zed vs Shen" Showdown Decks Display',
                  'Radiance: "Evelynn vs Seraphine" Showdown Decks Display',
                  "Origins | Nexus Night Promo Booster",
                  "Spiritforged | Nexus Night Promo Booster",
                  "Unleashed | Nexus Night Promo Booster",
                  "Vendetta | Nexus Night Promo Booster",
                  "Arcane Promo Pack", "Immersive Arcane Promo Pack", "Promo Pack",
                  "Replacement Card Booster",
                  "2024 Trial Deck Set", "2025 Trial Deck Set",
                  "Origins Booster Box", "Spiritforged Booster Box",
                  "Unleashed Booster Box", "Vendetta Booster Box",
                  "Radiance Booster Box", "Legacy Booster Box",
                  "The Reckoning Booster Box",
                  "Origins Booster Box Case", "Unleashed Vault Bundle Case",
                  "Unleashed Vault", "Vendetta Vault", "Radiance Vault",
                  "Legacy Vault", "Origins: Proving Grounds",
                  "Legacy: Proving Grounds",
                  "Origins: Proving Grounds Box Set Case"):
            self.assertIn(n, nomes, f"{n} tinha de ficar")

    def test_os_9_displays_de_decks_continuam_na_lista(self):
        nomes = [x["nome"] for x in self.selado.itens(None, self.cfg)]
        self.assertEqual(
            sum(1 for n in nomes if "Deck Display" in n or "Decks Display" in n), 9)

    def test_o_nome_dobrado_do_catalogo_real_mexe_em_dois(self):
        """Os dois «Trial Deck Set Set» do CardTrader, e mais nenhum dos 117."""
        mexidos = [p for p in self.selado._crus(self.cfg, com_excluidos=True)
                   if p.get("nome_bruto") and p["nome_bruto"] != p["nome"]]
        self.assertEqual(sorted(p["id"] for p in mexidos),
                         ["ct-383045", "ct-383046"])
        self.assertEqual(sorted(p["nome"] for p in mexidos),
                         ["2024 Trial Deck Set", "2025 Trial Deck Set"])

    def test_os_dois_trial_deck_set_continuam_a_ser_dois(self):
        """A junção de duplicados leva a VERSÃO na chave, e os nomes limpos são
        iguais — sem a versão juntavam-se e um deles desaparecia."""
        ids = [x["id"] for x in self.selado.itens(None, self.cfg)]
        self.assertIn("ct-383045", ids)
        self.assertIn("ct-383046", ids)

    def test_por_edicao_depois_de_tirar(self):
        """Os números que ele vai ver, edição a edição."""
        lista = [x for x in self.selado.itens(None, self.cfg) if not x["acessorio"]]
        por = {}
        for x in lista:
            por[x["edicao"]] = por.get(x["edicao"], 0) + 1
        self.assertEqual(por, {"OGN": 8, "OGS": 2, "SFD": 8, "UNL": 11, "VEN": 8,
                               "RAD": 7, "LGC": 6, "PG2": 1, "REC": 1, "ARC": 3,
                               "OP": 1, "PROMO-RIFT": 18, "T1S": 2})
        self.assertEqual(sum(por.values()), 76)


# ---------------------------------------------------------------------------
# 4. O nome dobrado do catálogo
# ---------------------------------------------------------------------------


class TestONomeDobrado(TirarBase):

    def test_junta_a_palavra_repetida(self):
        self.assertEqual(self.selado.nome_limpo("2024 Trial Deck Set Set"),
                         "2024 Trial Deck Set")
        self.assertEqual(self.selado.nome_limpo("2025 Trial Deck Set Set"),
                         "2025 Trial Deck Set")

    def test_nao_mexe_num_nome_normal(self):
        for n in ("Origins Booster Box", "Teste: Proving Grounds",
                  'Origins: "Jinx" Champion Deck', "Unleashed Vault Bundle Case",
                  "Spiritforged | Nexus Night Promo Booster"):
            self.assertEqual(self.selado.nome_limpo(n), n)

    def test_o_id_nao_muda(self):
        """A correcção é de APRESENTAÇÃO: o id vem do `blueprint_id`."""
        x = self.por_id(self.lista(), "ct-504")
        self.assertEqual(x["nome"], "2024 Teste Deck Set")
        self.assertEqual(x["blueprint_id"], 504)

    def test_o_nome_bruto_fica_no_item(self):
        x = self.por_id(self.lista(), "ct-504")
        self.assertEqual(x["nome_bruto"], "2024 Teste Deck Set Set")

    def test_as_duas_escritas_casam_no_excluidos(self):
        """Ele pode escrever o nome que vê no ecrã ou o do catálogo."""
        for escrita in ("2024 Teste Deck Set", "2024 Teste Deck Set Set"):
            self.assertNotIn("ct-504", [x["id"] for x in self.lista([escrita])])

    def test_a_juncao_de_duplicados_continua_a_distinguir_pela_versao(self):
        """Com os nomes limpos, «2024 Teste Deck Set» e um «2025» continuam a
        ser dois — a chave leva a versão."""
        cat = json.loads(json.dumps(CAT))
        cat["produtos"].append(
            {"blueprint_id": 505, "nome": "2025 Teste Deck Set Set", "versao": "©2025",
             "categoria_id": 262, "edicao": "TST", "edicao_nome": "Teste",
             "img": None, "cardmarket_id": None})
        self.escrever_catalogo(cat)
        ids = [x["id"] for x in self.lista()]
        self.assertIn("ct-504", ids)
        self.assertIn("ct-505", ids)


# ---------------------------------------------------------------------------
# 5. NADA DISTO MEXE NA COLEÇÃO
# ---------------------------------------------------------------------------


class TestNaoMexeNaColecao(TirarBase):
    """A MESMA fotografia do `test_selado` — níveis, denominador, wantlist,
    valor, totais, grelha, playset, barras, painel, foil, blocos, Faltas,
    Encomendas, A mais, decks, uso, Venda, `copies`, locais e `ops` — por
    referência, para não haver duas definições de «número da Coleção»."""

    fotografia = _sel.TestNaoEntraNaColecao.fotografia

    def test_a_fotografia_nao_e_de_zeros(self):
        f = self.fotografia(self.catalogo())
        self.assertGreater(f["valor"]["cents"], 0)
        self.assertTrue(f["denominador"])
        self.assertTrue(f["copies"])

    def test_tirar_produtos_por_config_nao_mexe_em_numero_nenhum(self):
        con = self.catalogo()
        self.cfg_selado({"extra": [EVENT_KIT]})
        antes = json.dumps(self.fotografia(con), sort_keys=True, default=str)

        # Com unidades gravadas, para o caso não ser trivial.
        self.selado.ajustar(con, "ct-106", 2)
        self.selado.ajustar(con, "ct-503", 1)
        self.assertEqual(
            json.dumps(self.fotografia(con), sort_keys=True, default=str), antes)

        self.cfg_selado({"extra": [EVENT_KIT], "excluidos": [
            "Teste Booster", "Teste Slim Booster Box", "Teste Pre-Rift Kit",
            "Teste Pre-Rift EVENT Kit"]})
        self.assertEqual(
            json.dumps(self.fotografia(con), sort_keys=True, default=str), antes,
            "tirar produtos do selado não mexe num número da Coleção")

        self.cfg_selado({"extra": [EVENT_KIT], "excluidos": []})
        self.assertEqual(
            json.dumps(self.fotografia(con), sort_keys=True, default=str), antes)

    def test_nenhum_modulo_de_contas_conhece_o_excluidos(self):
        """A chave é do selado, e o selado não entra em conta nenhuma."""
        for nome in ("metrics", "a_subir", "faltas", "faltas_edicao", "a_mais",
                     "uso_decks", "decks", "locais", "pending", "prices", "painel",
                     "runas_vista", "cardmarket", "collection", "foil", "proprias",
                     "venda", "catalog", "abas"):
            texto = (REPO / "riftvault" / f"{nome}.py").read_text(encoding="utf-8")
            self.assertNotIn("excluidos", texto, f"{nome}.py não conhece a chave")
            self.assertNotIn("sealed_copies", texto)


# ---------------------------------------------------------------------------
# 6. A página
# ---------------------------------------------------------------------------


class TestAPagina(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.js = APP_JS.read_text(encoding="utf-8")
        cls.css = CSS.read_text(encoding="utf-8")

    def test_o_cabecalho_diz_quantos_foram_tirados(self):
        self.assertIn("scope.excluidos", self.js)
        self.assertIn("sl-tirados", self.js)
        i = self.js.index("sl-tirados")
        troco = self.js[i:i + 900]
        self.assertIn("tirado", troco)
        self.assertIn("não contam", troco)

    def test_diz_que_nada_foi_apagado_e_como_repor(self):
        i = self.js.index("sl-tirados")
        troco = self.js[i:i + 900]
        self.assertIn("Nada foi apagado", troco)
        self.assertIn("tirar o nome da lista", troco)
        self.assertIn("selado.excluidos", troco)

    def test_lista_quais_sairam_com_a_edicao_e_o_tipo(self):
        i = self.js.index("sl-tirados-lista")
        troco = self.js[i:i + 400]
        self.assertIn("x.nome", troco)
        self.assertIn("x.edicao", troco)
        self.assertIn("x.tipo_label", troco)
        self.assertIn("escapeHTML", troco)

    def test_vem_dobrado_num_details(self):
        """São 22 linhas: a resposta curta é o número."""
        i = self.js.index("sl-tirados")
        self.assertIn("<details", self.js[max(0, i - 40):i + 20])
        self.assertIn(".sl-tirados", self.css)
        self.assertIn(".sl-tirados-lista", self.css)

    def test_a_ajuda_explica_a_chave(self):
        i = self.js.index("'selado': {")
        troco = self.js[i:i + 4200]
        self.assertIn("selado.excluidos", troco)
        self.assertIn("Esconder não é apagar", troco)


if __name__ == "__main__":
    unittest.main()

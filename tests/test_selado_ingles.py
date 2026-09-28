"""Só impressão inglesa, e sai da aba quem não tem página própria (André,
2026-09-28).

TRÊS ORDENS DO MESMO DIA, e as duas primeiras usam mecanismos que já existiam
------------------------------------------------------------------------------
a) *"Repor so os 5 novos"* — dos que tinham saído a 26/09 por não terem oferta
   em lado nenhum, voltam os que o **Cardmarket** revelou terem-na. É tirar
   nomes do `selado.excluidos`, que é onde «repor» sempre foi tirar o nome.

b) *"nao quero nada que nao seja impressao Inglesa"* — REGRA NOVA e geral, mas
   **sem mecanismo novo**: aplica-se à mão, pelo mesmo `selado.excluidos`.
   Não há campo de língua nos blueprints — o marcador está no `nome`
   («Arcane Chinese Promo Set»), na `versao` («Chinese Exclusive») ou no
   rótulo do Cardmarket («(Chinese, Slim)»).

c) *"Tira os que nao tem pagina propria"* — os 17 do `selado.extra` saem da
   aba, e a lista fica vazia. **Esvaziar não é apagar**, como nos acessórios a
   25/09: os objectos ficam inteiros no `_selado_extra_arquivado` do config e
   repor é copiá-los de volta.

O QUE ESTE FICHEIRO FIXA, e é a parte fácil de estragar
------------------------------------------------------
1. **Formato não é língua.** «Slim», «Jumbo» e «Sleeved» são embalagens. Se
   alguém escrever uma regra automática por palavras, o *Unleashed Sleeved
   Booster* — que voltou HOJE por ser inglês — sai outra vez. Há teste.
2. **A regra não se aplica sozinha.** A app não esconde nada por adivinhar a
   língua; esconder é decisão dele, escrita no config. Senão a aba mudava a
   cada `--sync`.
3. **O conhecimento dos 17 não se perde.** Há teste que lê o config REAL e
   exige os 17 objectos completos no arquivo, com o `conteudo` e as `nota`s —
   e que repor os faz voltar tal e qual.
4. E, por cima, a defesa de sempre: **nada disto mexe num número da Coleção**,
   pela fotografia do `test_selado`, por referência.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.test_selado import CATALOGO, Base  # noqa: E402
from tests.test_selado import TestNaoEntraNaColecao as _Foto  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
CONFIG_REAL = json.loads((REPO / "riftvault_config.json").read_text(encoding="utf-8"))

# --- o que a ordem de hoje mexeu, tal como fica escrito no config -----------

# (a) Saíram do `selado.excluidos` — voltam à aba. O Cardmarket revelou-lhes
#     oferta e os dois são impressão inglesa.
VOLTARAM = {
    "Unleashed Sleeved Booster": "13,00 EUR no Cardmarket",
    "Replacement Card Booster": "35,00 EUR no Cardmarket",
}

# (b) Entrou no `selado.excluidos` — sai da aba pela língua.
SAIU_PELA_LINGUA = "Arcane Chinese Promo Set"

# Os três que o Cardmarket revelou terem oferta e MESMO ASSIM ficam fora, pela
# regra da língua. Os dois primeiros o próprio supervisor cortou; o terceiro
# foi medido aqui: o blueprint 408687 tem `versao: "Chinese Exclusive"` no
# catálogo do CardTrader, a mesma string dos outros dois «Promo Pack», que
# estão fora. É a única coisa da ordem que não se fez como estava escrita, e a
# razão está no `docs/selado-dois-mercados-20260928.md`.
FICAM_FORA_PELA_LINGUA = {
    "Unleashed Slim Booster": "Unleashed Booster (Chinese, Slim)",
    "Unleashed Slim Booster Box": "Unleashed Booster Box (Chinese, Slim)",
    "Immersive Arcane Promo Pack": "versao 'Chinese Exclusive' no CardTrader",
}

# (c) Os 17 que saíram da aba e ficaram arquivados.
OS_17 = [
    'Origins: "Jinx" Champion Deck Display',
    'Origins: "Viktor" Champion Deck Display',
    'Origins: "Lee Sin" Champion Deck Display',
    'Spiritforged: "Rumble" Champion Deck Display',
    'Spiritforged: "Fiora" Champion Deck Display',
    'Unleashed: "Vi" Champion Deck Display',
    'Unleashed: "Vex" Champion Deck Display',
    'Vendetta: "Zed vs Shen" Showdown Decks Display',
    'Radiance: "Evelynn vs Seraphine" Showdown Decks Display',
    "Origins: Proving Grounds Box Set Case",
    "Unleashed Vault Bundle Case",
    "Vendetta Vault Bundle Case",
    "Radiance Vault Bundle Case",
    "Spiritforged Pre-Rift EVENT Kit",
    "Unleashed Pre-Rift EVENT Kit",
    "Vendetta Pre-Rift EVENT Kit",
    "Radiance Pre-Rift EVENT Kit",
]

# --- catálogo de brincar ----------------------------------------------------
# O par que modela a armadilha: um produto chinês e um SLEEVED, que se parecem
# num filtro por palavras e são coisas diferentes.
CHINES = "Teste Chinese Promo Set"
CHINES_VERSAO = "Teste Immersive Pack"      # a língua vem na VERSÃO
SLEEVED = "Teste Sleeved Booster"           # embalagem, não língua — FICA
INGLES = "Teste Box Set"                    # o irmão inglês do chinês — FICA

CAT = json.loads(json.dumps(CATALOGO))
CAT["produtos"] += [
    {"blueprint_id": 901, "nome": CHINES, "versao": "",
     "categoria_id": 263, "edicao": "TST", "edicao_nome": "Teste",
     "img": None, "cardmarket_id": 111},
    {"blueprint_id": 902, "nome": CHINES_VERSAO, "versao": "Chinese Exclusive",
     "categoria_id": 260, "edicao": "TST", "edicao_nome": "Teste",
     "img": None, "cardmarket_id": 222},
    {"blueprint_id": 903, "nome": SLEEVED, "versao": "",
     "categoria_id": 260, "edicao": "TST", "edicao_nome": "Teste",
     "img": None, "cardmarket_id": None},
    {"blueprint_id": 904, "nome": INGLES, "versao": "",
     "categoria_id": 263, "edicao": "TST", "edicao_nome": "Teste",
     "img": None, "cardmarket_id": 444},
]
for bid, cents in ((901, 149900), (902, 8000), (903, 1300), (904, 45000)):
    CAT["precos"][str(bid)] = {"cents": cents, "currency": "EUR",
                               "day": "2026-09-28", "n_listings": 1,
                               "n_sellers": 1, "n_copies": 1}

EXTRA_TESTE = [
    {"nome": "Teste Champion Deck Display", "edicao": "TST", "tipo": "display",
     "conteudo": "4 decks iguais", "nota": "DÚVIDA: por confirmar."},
    {"nome": "Teste Vault Bundle Case", "edicao": "TST", "tipo": "case",
     "conteudo": "12 vaults"},
]


class InglesBase(Base):
    def setUp(self):
        super().setUp()
        self.escrever_catalogo(CAT)

    def payload(self, **kw):
        self.cfg_selado(kw)
        return self.selado.payload(self.con())

    def nomes(self, **kw):
        return [x["nome"] for x in self.payload(**kw)["items"] if not x["acessorio"]]


# ---------------------------------------------------------------------------
# 1. A regra da língua: tira-se pelo nome, e a app não adivinha
# ---------------------------------------------------------------------------


class TestARegraDaLingua(InglesBase):
    def test_sem_a_lista_estao_todos(self):
        nomes = self.nomes(excluidos=[])
        for n in (CHINES, CHINES_VERSAO, SLEEVED, INGLES):
            self.assertIn(n, nomes)

    def test_a_app_NAO_adivinha_a_lingua(self):
        """Esconder é decisão DELE. Um produto com «Chinese» no nome continua
        na aba até o nome estar no `selado.excluidos` — senão a aba mudava
        sozinha a cada `--sync`, e ninguém saberia porquê."""
        self.assertIn(CHINES, self.nomes(excluidos=[]))
        self.assertIn(CHINES_VERSAO, self.nomes(excluidos=[]))

    def test_o_chines_nomeado_sai(self):
        nomes = self.nomes(excluidos=[CHINES])
        self.assertNotIn(CHINES, nomes)
        self.assertIn(INGLES, nomes)

    def test_FORMATO_NAO_E_LINGUA_o_sleeved_fica(self):
        """A armadilha desta ordem. «Slim», «Jumbo» e «Sleeved» são embalagens:
        o *Unleashed Sleeved Booster* VOLTOU hoje por ser inglês. Um filtro
        automático por palavras deitava-o fora outra vez."""
        nomes = self.nomes(excluidos=[CHINES, CHINES_VERSAO])
        self.assertIn(SLEEVED, nomes)

    def test_o_irmao_ingles_fica(self):
        """«Arcane Box Set» fica; «Arcane Box Set (Chinese)» é outro produto."""
        self.assertIn(INGLES, self.nomes(excluidos=[CHINES]))

    def test_a_lingua_na_versao_tambem_e_lingua(self):
        """O marcador pode estar na `versao` e não no nome — é o caso dos três
        «Promo Pack» («Chinese Exclusive»). Tira-se pelo NOME na mesma."""
        p = self.por_id(self.payload(excluidos=[])["items"], "ct-902")
        self.assertEqual(p["versao"], "Chinese Exclusive")
        self.assertNotIn(CHINES_VERSAO, self.nomes(excluidos=[CHINES_VERSAO]))

    def test_sai_dos_contadores_e_do_valor(self):
        con = self.con()
        self.selado.ajustar(con, "ct-901", 1, source="test")
        com = self.selado.payload(con)["totals"]
        self.cfg_selado({"excluidos": [CHINES]})
        sem = self.selado.payload(con)["totals"]
        self.assertEqual(com["ha"] - sem["ha"], 1)
        self.assertEqual(com["valor_cents"] - sem["valor_cents"], 149900)

    def test_repor_e_tirar_o_nome_da_lista(self):
        com = self.payload(excluidos=[CHINES])
        sem = self.payload(excluidos=[])
        self.assertNotIn(CHINES, [x["nome"] for x in com["items"]])
        self.assertIn(CHINES, [x["nome"] for x in sem["items"]])

    def test_o_catalogo_em_disco_fica_intacto(self):
        self.payload(excluidos=[CHINES])
        dados = json.loads(self.config.SELADO_PATH.read_text(encoding="utf-8"))
        self.assertIn(CHINES, [p["nome"] for p in dados["produtos"]])


# ---------------------------------------------------------------------------
# 2. O `selado.extra` VAZIO: a aba perde-os, o config guarda-os
# ---------------------------------------------------------------------------


class TestOExtraVazio(InglesBase):
    def test_com_extra_aparecem(self):
        nomes = self.nomes(excluidos=[], extra=EXTRA_TESTE)
        for x in EXTRA_TESTE:
            self.assertIn(x["nome"], nomes)

    def test_a_lista_vazia_tira_os_todos(self):
        nomes = self.nomes(excluidos=[], extra=[])
        for x in EXTRA_TESTE:
            self.assertNotIn(x["nome"], nomes)

    def test_esvaziar_nao_mexe_nos_do_cardtrader(self):
        com = self.payload(excluidos=[], extra=EXTRA_TESTE)
        sem = self.payload(excluidos=[], extra=[])
        ct_com = [x["id"] for x in com["items"] if x["fonte"] == "cardtrader"]
        ct_sem = [x["id"] for x in sem["items"] if x["fonte"] == "cardtrader"]
        self.assertEqual(ct_com, ct_sem)
        self.assertEqual(sem["totals"]["do_config"], 0)
        self.assertEqual(com["totals"]["do_config"], len(EXTRA_TESTE))

    def test_repor_e_copiar_de_volta(self):
        """A prova de que arquivar chega: pôr os objectos outra vez no
        `selado.extra` devolve a aba ao que era, campo a campo."""
        antes = self.payload(excluidos=[], extra=EXTRA_TESTE)["items"]
        self.payload(excluidos=[], extra=[])
        depois = self.payload(excluidos=[], extra=EXTRA_TESTE)["items"]
        limpo = lambda ls: [{k: v for k, v in x.items() if k != "links"} for x in ls]
        self.assertEqual(limpo(antes), limpo(depois))

    def test_a_unidade_gravada_num_extra_nao_se_apaga(self):
        """Ele tinha-os todos a zero a 28/09, mas a regra é a mesma dos
        excluídos: esvaziar a lista não pode apagar contagem nenhuma."""
        con = self.con()
        self.cfg_selado({"excluidos": [], "extra": EXTRA_TESTE})
        pid = [x["id"] for x in self.selado.payload(con)["items"]
               if x["fonte"] == "config"][0]
        self.selado.ajustar(con, pid, 2, source="test")
        self.cfg_selado({"excluidos": [], "extra": []})
        self.assertEqual(self.selado.payload(con)["totals"]["copias"], 0)
        self.cfg_selado({"excluidos": [], "extra": EXTRA_TESTE})
        self.assertEqual(self.por_id(self.selado.payload(con)["items"], pid)["qty"], 2)

    def test_o_conteudo_e_a_nota_sobrevivem_a_ida_e_volta(self):
        it = self.payload(excluidos=[], extra=EXTRA_TESTE)["items"]
        p = [x for x in it if x["nome"] == EXTRA_TESTE[0]["nome"]][0]
        self.assertEqual(p["conteudo"], "4 decks iguais")
        self.assertEqual(p["nota"], "DÚVIDA: por confirmar.")


# ---------------------------------------------------------------------------
# 3. O CONFIG REAL — é aqui que a ordem dele fica fixada
# ---------------------------------------------------------------------------


class TestOConfigReal(unittest.TestCase):
    def setUp(self):
        self.sel = CONFIG_REAL["selado"]
        self.excl = self.sel["excluidos"]

    def test_o_extra_esta_vazio(self):
        self.assertEqual(self.sel["extra"], [])

    def test_os_17_ficaram_arquivados_inteiros(self):
        arq = CONFIG_REAL["_selado_extra_arquivado"]
        nomes = [p["nome"] for p in arq["produtos"]]
        self.assertEqual(len(nomes), 17)
        for n in OS_17:
            self.assertIn(n, nomes)

    def test_o_arquivo_guarda_os_campos_todos(self):
        """O que sai é a PRESENÇA na aba, não o conhecimento: nome, edição,
        tipo, data e conteúdo em todos, e as ressalvas onde as havia."""
        prods = CONFIG_REAL["_selado_extra_arquivado"]["produtos"]
        for p in prods:
            for campo in ("nome", "edicao", "tipo", "data", "conteudo"):
                self.assertTrue(p.get(campo), f"{p.get('nome')}: falta {campo}")
        com_nota = [p for p in prods if p.get("nota")]
        self.assertEqual(len(com_nota), 5, "4 EVENT Kit + a dúvida dos vaults")
        duvida = [p for p in prods if p["nome"] == "Unleashed Vault Bundle Case"][0]
        self.assertIn("DÚVIDA", duvida["nota"], "a ressalva dos 4 ou 12 vaults")

    def test_o_arquivo_diz_a_data_a_frase_dele_e_a_razao(self):
        porque = CONFIG_REAL["_selado_extra_arquivado"]["_porque"]
        self.assertIn("2026-09-28", porque)
        self.assertIn("Tira os que nao tem pagina propria", porque)
        self.assertIn("REPOR", porque.upper())

    def test_os_dois_voltaram_a_aba(self):
        for n in VOLTARAM:
            self.assertNotIn(n, self.excl, f"{n} devia ter voltado à aba")

    def test_o_chines_saiu(self):
        self.assertIn(SAIU_PELA_LINGUA, self.excl)

    def test_os_tres_da_lingua_continuam_fora(self):
        for n in FICAM_FORA_PELA_LINGUA:
            self.assertIn(n, self.excl, f"{n} é impressão não-inglesa")

    def test_a_nota_da_lingua_tem_a_frase_dele_e_a_data(self):
        nota = CONFIG_REAL["_selado_so_ingles"]
        self.assertIn("2026-09-28", nota)
        self.assertIn("nao quero nada que nao seja impressao Inglesa", nota)
        self.assertIn("--sync", nota)

    def test_a_nota_da_lingua_avisa_que_formato_nao_e_lingua(self):
        nota = CONFIG_REAL["_selado_so_ingles"]
        self.assertIn("Sleeved", nota)
        self.assertIn("embalagem", nota.lower())

    def test_sem_repetidos_na_lista(self):
        self.assertEqual(len(self.excl), len(set(self.excl)))

    def test_as_ordens_anteriores_ficam_inteiras(self):
        """O que ele mandou tirar nas ordens anteriores não pode sair por engano
        nesta.

        Os que são DECKS saíram desta lista horas depois, na noite de 28/09,
        quando a categoria 262 passou a tirá-los sozinha — e a decisão ficou no
        `_selado_decks_arquivado`. Ver `test_selado_sem_decks`."""
        for n in ("Spiritforged Bulk Runes",
                  "Spiritforged Pre-Rift Kit", "Unleashed: Poro Scene Set",
                  "Tournament Gift Box",
                  "The T1 Worlds Champion | Player Bundle"):
            self.assertIn(n, self.excl)
        arq = CONFIG_REAL["_selado_decks_arquivado"]
        guardados = arq["de_2026_09_25"] + arq["de_2026_09_26"]
        for n in ('Origins: "Jinx" Champion Deck', 'Legacy: "Garen" Champion Deck',
                  "Origins: Champion Deck Set", "2024 Trial Deck Set"):
            self.assertNotIn(n, self.excl, n)
            self.assertIn(n, guardados, n)

    def test_o_default_nao_esconde_nem_inventa(self):
        """Um riftvault sem config não tem lista de exclusões nem extras: a
        decisão é dele, não da app."""
        sys.path.insert(0, str(REPO))
        from riftvault import config as _cfg
        self.assertEqual(_cfg.DEFAULTS["selado"]["extra"], [])
        self.assertEqual(_cfg.DEFAULTS["selado"].get("excluidos", []), [])


# ---------------------------------------------------------------------------
# 4. Contra o CATÁLOGO REAL: os números da aba
# ---------------------------------------------------------------------------


class TestOCatalogoReal(unittest.TestCase):
    """Corre contra o `data/selado_catalogo.json` do repositório, que é
    committado e só de leitura. Sem ele, salta."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(REPO))
        from riftvault import selado
        cls.selado = selado
        if not (REPO / "data" / "selado_catalogo.json").exists():
            raise unittest.SkipTest("sem catálogo em disco")
        cls.lista = selado.itens(None, CONFIG_REAL)
        cls.crus = selado._crus(CONFIG_REAL, com_excluidos=True)

    def test_a_aba_tem_30_produtos(self):
        """Eram 32 depois destas três ordens; ficaram **30** nessa mesma noite,
        quando os 2 Showdown Deck saíram com a categoria 262
        (`test_selado_sem_decks`)."""
        self.assertEqual(len([x for x in self.lista if not x["acessorio"]]), 30)

    def test_nenhum_vem_do_config(self):
        self.assertEqual([x["nome"] for x in self.lista if x["fonte"] == "config"], [])

    def test_os_dois_que_voltaram_estao_la(self):
        nomes = [x["nome"] for x in self.lista]
        for n in VOLTARAM:
            self.assertIn(n, nomes)

    def test_o_chines_nao_esta_la(self):
        self.assertNotIn(SAIU_PELA_LINGUA, [x["nome"] for x in self.lista])

    def test_nenhum_produto_da_aba_tem_marcador_de_lingua(self):
        """A varredura que a ordem pediu: dos 48 de ontem, só o «Arcane Chinese
        Promo Set» tinha marcador. Se um `--sync` trouxer outro, este teste
        dá vermelho e alguém tem de decidir — que é o que se quer."""
        import re
        marcador = re.compile(r"chin|japan|korea|\bkr\b|\bzh\b|french|german|"
                              r"spanish|italian", re.I)
        maus = [x["nome"] for x in self.lista
                if marcador.search(x["nome"] + " " + (x["versao"] or ""))]
        self.assertEqual(maus, [], f"marcador de língua na aba: {maus}")

    def test_o_sleeved_fica_e_e_ingles(self):
        """O contraponto do teste de cima, no catálogo real: o nome tem
        «Sleeved» e não é língua nenhuma."""
        self.assertIn("Unleashed Sleeved Booster", [x["nome"] for x in self.lista])

    def test_cada_nome_da_lista_casa_com_UM_produto(self):
        """Nenhuma exclusão morta e nenhuma ambígua — o guarda de 26/09, agora
        com 49 entradas."""
        for entrada in CONFIG_REAL["selado"]["excluidos"]:
            ids = self.selado._resolver_excluidos(self.crus, [entrada])
            self.assertEqual(len(ids), 1, f"{entrada!r} casou com {len(ids)}")

    def test_uma_entrada_inventada_rebenta(self):
        with self.assertRaises(ValueError):
            self.selado._resolver_excluidos(self.crus, ["Produto Que Nao Existe"])

    def test_o_immersive_diz_chinese_exclusive_no_catalogo(self):
        """A medição que travou a reposição dele. Se um `--sync` mudar a versão
        deste blueprint, este teste dá vermelho e a decisão volta à mesa."""
        p = [x for x in self.crus if x["blueprint_id"] == 408687]
        if not p:
            self.skipTest("o blueprint saiu do catálogo")
        self.assertEqual(p[0]["versao"], "Chinese Exclusive")
        self.assertTrue(p[0]["excluido"])


# ---------------------------------------------------------------------------
# 5. A COLEÇÃO NÃO MEXE — a fotografia do `test_selado`, por referência
# ---------------------------------------------------------------------------


class TestNaoMexeNaColecao(_Foto):
    """A MESMA fotografia do `test_selado`, para não haver duas definições de
    «número da Coleção». Aqui mete-se e tira-se pelas três ordens de hoje."""

    def setUp(self):
        super().setUp()
        self.escrever_catalogo(CAT)

    def test_a_lingua_e_o_extra_nao_mexem_em_numero_nenhum(self):
        con = self.catalogo()
        self.cfg_selado({"excluidos": [], "extra": EXTRA_TESTE})
        antes = self.fotografia(con)
        self.selado.ajustar(con, "ct-901", 2, source="test")
        self.cfg_selado({"excluidos": [CHINES, CHINES_VERSAO], "extra": []})
        self.assertEqual(self.fotografia(con), antes)
        self.cfg_selado({"excluidos": [], "extra": EXTRA_TESTE})
        self.selado.ajustar(con, "ct-901", -2, source="test")
        self.assertEqual(self.fotografia(con), antes)

    def test_a_fotografia_nao_e_de_zeros(self):
        """Uma fotografia vazia era igual a si mesma e não provava nada."""
        f = self.fotografia(self.catalogo())
        self.assertTrue(f["grelha"])
        self.assertTrue(f["copies"])
        self.assertGreater(f["valor"]["cents"], 0)


if __name__ == "__main__":
    unittest.main()

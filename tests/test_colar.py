"""COLAR UMA DECKLIST (2026-10-02).

André, 2026-10-01: *"dos decks, tem que ser possivel colar o texto em copy
paste e gerar o deck, depois diz as cartas que tens e que nao tens, com imagem
com cor e sem cor"*.

O que estes testes fixam, por classes:

  * `TestUmLeitorSo` — o texto colado e o `.txt` entram pelo MESMO leitor, e a
    LISTA REAL que ele colou dá o mesmo deck pelas duas portas. Um segundo
    leitor divergia do primeiro no dia em que o formato mudasse.
  * `TestPreverNaoGrava` — a previsão não escreve nada: nem ficheiro, nem
    tabela, nem cópia.
  * `TestNaoEmSilencio` — uma linha que o catálogo não conhece não pode virar
    um deck sem ele saber.
  * `TestEdicoes` / `TestComQueSeTapou` — a regra das versões dele.
  * `TestACor` — a imagem a cores quando tem, a cinzento quando não tem.
  * `TestAColecaoNaoMexe` — colar uma lista não mexe num número da Coleção.

Correm contra pastas temporárias e um catálogo de brincar: nunca contra o
`data/` a sério. Os NÚMEROS da lista real (4 cópias em falta) medem-se contra o
`data/` no `_revisao\\_prova_colar.py` — aqui prova-se o MECANISMO, lá os
números.
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

#: Um caminho que não existe: o `config` cai nos `DEFAULTS`, que é o que estes
#: testes querem medir. Põe-se em CADA `setUp` e não só aqui, porque um teste
#: que escreva o seu config (`config_decks_sem_alt_art`) LIMPA a variável no
#: fim — e sem ela os testes seguintes liam o `riftvault_config.json` A SÉRIO,
#: onde `multi.aberto` é `true`: as rotas passavam a pedir sessão e davam 401.
SEM_CONFIG = str(Path(tempfile.gettempdir()) / "riftvault-nao-existe.json")

from tests.fixture import REPO, Vault  # noqa: E402

#: A lista REAL que ele colou (2026-10-01), versionada em `decks/`.
LISTA_REAL = REPO / "decks" / "leona-radiant-dawn.txt"


class Base(unittest.TestCase):
    def setUp(self):
        os.environ["RIFTVAULT_CONFIG"] = SEM_CONFIG
        self.addCleanup(lambda: os.environ.pop("RIFTVAULT_CONFIG", None))
        self.v = Vault()
        self.addCleanup(self.v.close)
        self.config = self.v.config

    # Um catálogo com as cartas da lista real, para as duas portas poderem
    # resolver os nomes sem precisar do catálogo a sério.
    def catalogo(self, *, cartas=None, copias=None, duas_edicoes=False):
        con = self.v.connect()
        nomes = cartas if cartas is not None else self._nomes_da_lista_real()
        for i, (nome, tipo) in enumerate(nomes, start=1):
            self.v.add_printing(con, f"tst-{i:03d}-100", "TST", i, nome, card_type=tipo)
            if duas_edicoes:
                self.v.add_printing(con, f"ts2-{i:03d}-100", "TS2", i, nome,
                                    card_type=tipo)
        self.v.rebuild(con)
        from riftvault import collection
        for pid, qty in (copias or {}).items():
            collection.adjust(con, pid, qty, source="test")
        return con

    @staticmethod
    def _cartas(payload):
        """As linhas de um `deck_payload`, achatadas (vêm por secção)."""
        return [c for s in payload["sections"] for c in s["cards"]]

    def _nomes_da_lista_real(self):
        """Os nomes da lista real, com um tipo plausível por papel."""
        from riftvault import decks
        lido = decks.parse(LISTA_REAL)
        tipo = {"legend": "Legend", "champion": "Unit", "main": "Unit",
                "battlefields": "Battlefield", "runes": "Rune", "sideboard": "Unit"}
        vistos, out = set(), []
        for role, _, nome in lido["lines"]:
            if nome.strip().casefold() in vistos:
                continue
            vistos.add(nome.strip().casefold())
            out.append((nome, tipo[role]))
        return out


class TestUmLeitorSo(Base):
    """O texto colado e o `.txt` entram pelo MESMO leitor."""

    def test_o_parse_do_ficheiro_chama_o_parse_do_texto(self):
        from riftvault import decks
        texto = LISTA_REAL.read_text(encoding="utf-8")
        a = decks.parse(LISTA_REAL)
        b = decks.parse_texto(texto, slug="leona-radiant-dawn")
        self.assertEqual(a["lines"], b["lines"])
        self.assertEqual(a["nome"], b["nome"])
        self.assertEqual(a["content_hash"], b["content_hash"],
                         "o ficheiro e o texto têm de dar o mesmo hash")

    def test_so_ha_um_leitor_no_codigo(self):
        """O `colar.py` não pode ter uma segunda gramática de decklist."""
        fonte = (REPO / "riftvault" / "colar.py").read_text(encoding="utf-8")
        self.assertIn("decks.parse_texto", fonte)
        for suspeito in ("ROLES", "endswith(\":\")", "^(\\d+)"):
            self.assertNotIn(suspeito, fonte,
                             "o colar não pode reimplementar o leitor")

    def test_a_LISTA_REAL_pelas_duas_portas_da_o_MESMO_deck(self):
        """A prova que a ordem pediu: a lista dele colada == a lista dele em
        ficheiro. Mesmas cartas, mesmas quantidades, mesmo que falta."""
        from riftvault import colar, decks
        texto = LISTA_REAL.read_text(encoding="utf-8")

        # (a) pela pasta, como ele fez à mão a 2026-10-01
        con = self.catalogo()
        self.v.write_deck("leona-radiant-dawn", texto)
        decks.import_all(con, log=lambda *_: None)
        pelo_ficheiro = self._fotografia(con)
        con.close()

        # (b) pela caixa de colar, numa instalação limpa
        self.v.close()
        self.v = Vault()
        self.addCleanup(self.v.close)
        con = self.catalogo()
        colar.gravar(con, texto)
        pela_caixa = self._fotografia(con)

        self.assertEqual(pelo_ficheiro, pela_caixa)
        # E não é uma fotografia de nada: a lista tem 66 cópias.
        self.assertEqual(sum(q for _, q in pela_caixa["cartas"]), 66)
        con.close()

    def _fotografia(self, con):
        from riftvault import decks
        d = decks.deck_rows(con)[0]
        cartas = sorted((r["card_key"], r["qty"]) for r in con.execute(
            "SELECT card_key, qty FROM deck_cards WHERE deck_id = ?", (d["deck_id"],)))
        p = decks.deck_payload(con, d["deck_id"])
        return {"nome": d["display_name"], "cartas": cartas,
                "falta": sorted((c["card_key"], c["missing"])
                                for c in self._cartas(p) if c["missing"])}

    def test_o_ficheiro_gravado_e_legivel_e_reimportavel(self):
        """O que a caixa grava é o formato de sempre: dá-se a ler, a versionar
        e a abrir num editor. Colar não é um caminho paralelo."""
        from riftvault import colar, decks
        con = self.catalogo()
        colar.gravar(con, LISTA_REAL.read_text(encoding="utf-8"))
        em_disco = list(self.v.decks_dir.glob("*.txt"))
        self.assertEqual(len(em_disco), 1)
        texto = em_disco[0].read_text(encoding="utf-8")
        self.assertIn("Nome: Leona Radiant Dawn", texto)
        self.assertIn(colar.MARCA, texto, "diz de onde veio o ficheiro")
        # E relê-se: as mesmas linhas da lista original.
        self.assertEqual(decks.parse(em_disco[0])["lines"],
                         decks.parse(LISTA_REAL)["lines"])
        con.close()


class TestPreverNaoGrava(Base):
    """A previsão mostra e NÃO escreve."""

    def test_prever_nao_escreve_ficheiro_nem_tabela_nem_copia(self):
        from riftvault import colar
        con = self.catalogo(copias={"tst-001-100": 3})
        antes = {
            "ficheiros": sorted(p.name for p in self.v.decks_dir.glob("*")),
            "decks": con.execute("SELECT COUNT(*) c FROM decks").fetchone()["c"],
            "cartas": con.execute("SELECT COUNT(*) c FROM deck_cards").fetchone()["c"],
            "copies": sorted(tuple(r) for r in con.execute(
                "SELECT printing_id, qty, qty_foil FROM copies")),
            "ops": con.execute("SELECT COUNT(*) c FROM ops").fetchone()["c"],
        }
        p = colar.prever(con, LISTA_REAL.read_text(encoding="utf-8"))
        self.assertTrue(p["linhas"], "e mesmo assim respondeu")
        depois = {
            "ficheiros": sorted(x.name for x in self.v.decks_dir.glob("*")),
            "decks": con.execute("SELECT COUNT(*) c FROM decks").fetchone()["c"],
            "cartas": con.execute("SELECT COUNT(*) c FROM deck_cards").fetchone()["c"],
            "copies": sorted(tuple(r) for r in con.execute(
                "SELECT printing_id, qty, qty_foil FROM copies")),
            "ops": con.execute("SELECT COUNT(*) c FROM ops").fetchone()["c"],
        }
        self.assertEqual(antes, depois)
        con.close()

    def test_a_aritmetica_que_ele_confere(self):
        from riftvault import colar
        con = self.catalogo()
        p = colar.prever(con, LISTA_REAL.read_text(encoding="utf-8"))
        por = {b["role"]: b for b in p["por_papel"]}
        self.assertEqual(por["main"]["copias"], 39)
        self.assertEqual(por["champion"]["copias"], 1)
        self.assertEqual(por["battlefields"]["copias"], 3)
        self.assertEqual(por["runes"]["copias"], 12)
        self.assertEqual(por["sideboard"]["copias"], 10)
        # 1 Legend + 1 Champion + 39 main + 3 battlefields + 12 runas + 10
        # sideboard = 66 cópias.
        self.assertEqual(p["totais"]["copias"], 66)
        # A regra do main conta o Champion (`main_includes_champion`):
        # 39 + 1 = 40, que é exactamente o que as listas dele fazem.
        self.assertEqual(por["main"]["copias"] + por["champion"]["copias"], 40)
        self.assertEqual(p["regras"]["main"], 40)
        self.assertTrue(p["regras"]["main_includes_champion"])
        con.close()

    def test_o_nome_e_o_slug_saem_do_Nome_ou_da_Legend(self):
        from riftvault import colar
        con = self.catalogo(cartas=[("Leona, Radiant Dawn", "Legend")])
        p = colar.prever(con, "Nome: O Meu Deck Ótimo!\n\nLegend:\n1 Leona, Radiant Dawn\n")
        self.assertEqual((p["nome"], p["slug"]), ("O Meu Deck Ótimo!", "o-meu-deck-otimo"))
        # Sem `Nome:`, é a Legend — como o resto da app já faz.
        p = colar.prever(con, "Legend:\n1 Leona, Radiant Dawn\n")
        self.assertEqual(p["slug"], "leona-radiant-dawn")
        con.close()

    def test_o_slug_nunca_sai_da_pasta(self):
        """O nome vem de uma caixa de texto e vira um caminho em disco."""
        from riftvault import colar
        for mau in ("../../etc/passwd", "..\\..\\x", "/absoluto", "C:\\Windows",
                    "....", "a/b/c"):
            s = colar._slug(mau)
            self.assertNotIn("/", s)
            self.assertNotIn("\\", s)
            self.assertNotIn("..", s)
            self.assertTrue(s)

    def test_texto_sem_cartas_rebenta_com_a_razao(self):
        from riftvault import colar
        con = self.catalogo()
        with self.assertRaises(colar.SemCartas) as e:
            colar.prever(con, "olá\nisto não é uma decklist\n")
        self.assertIn("3 Nome da carta", str(e.exception))
        with self.assertRaises(colar.SemCartas):
            colar.prever(con, "")
        con.close()

    def test_texto_enorme_recusa_se(self):
        from riftvault import colar
        con = self.catalogo()
        with self.assertRaises(ValueError):
            colar.prever(con, "1 Defy\n" * 100_000)
        con.close()


class TestNaoEmSilencio(Base):
    """Uma lista com um nome que o catálogo não conhece."""

    def test_as_linhas_que_nao_casam_dizem_se_e_travam_o_gravar(self):
        from riftvault import colar
        con = self.catalogo(cartas=[("Defy", "Unit")])
        texto = "MainDeck:\n3 Defy\n2 Carta Que Nao Existe\n"
        p = colar.prever(con, texto)
        self.assertEqual(len(p["nao_casaram"]), 1)
        self.assertEqual(p["nao_casaram"][0]["raw"], "Carta Que Nao Existe")
        self.assertEqual(p["totais"]["nao_casaram"], 1)
        # Gravar sem confirmar recusa — e não escreve nada.
        with self.assertRaises(colar.PrecisaConfirmar) as e:
            colar.gravar(con, texto)
        self.assertIn("Carta Que Nao Existe", str(e.exception))
        self.assertEqual(list(self.v.decks_dir.glob("*.txt")), [])
        # Com `confirmar`, grava — sem a linha que não casou.
        r = colar.gravar(con, texto, confirmar=True)
        self.assertTrue(r["gravado"])
        cks = [x["card_key"] for x in con.execute(
            "SELECT card_key FROM deck_cards")]
        self.assertEqual(cks, ["defy"])
        con.close()

    def test_a_linha_casada_diz_o_nome_do_CATALOGO(self):
        """O que ele vê na previsão é o nome do catálogo, não o que colou — é
        assim que se percebe que casou com a carta certa."""
        from riftvault import colar
        con = self.catalogo(cartas=[("Leona, Radiant Dawn", "Legend")])
        p = colar.prever(con, "Legend:\n1 Leona, Radiant Dawn\n")
        self.assertTrue(p["linhas"][0]["casou"])
        self.assertEqual(p["linhas"][0]["type"], "Legend")
        self.assertIsNotNone(p["linhas"][0]["card_key"])
        con.close()

    def test_gravar_por_cima_de_um_deck_pede_confirmacao(self):
        from riftvault import colar
        con = self.catalogo(cartas=[("Defy", "Unit")])
        colar.gravar(con, "Nome: X\nMainDeck:\n1 Defy\n")
        with self.assertRaises(colar.NomeOcupado):
            colar.gravar(con, "Nome: X\nMainDeck:\n3 Defy\n")
        self.assertTrue(colar.prever(con, "Nome: X\nMainDeck:\n3 Defy\n")["ocupado"])
        r = colar.gravar(con, "Nome: X\nMainDeck:\n3 Defy\n", substituir=True)
        self.assertTrue(r["gravado"])
        self.assertEqual(con.execute("SELECT qty FROM deck_cards").fetchone()["qty"], 3)
        self.assertEqual(con.execute("SELECT COUNT(*) c FROM decks").fetchone()["c"], 1,
                         "substituir não cria um segundo deck")
        con.close()

    def test_apagar_a_lista_nao_apaga_copias(self):
        from riftvault import colar, locais
        con = self.catalogo(cartas=[("Defy", "Unit")], copias={"tst-001-100": 3})
        colar.gravar(con, "Nome: X\nMainDeck:\n1 Defy\n")
        from riftvault import proprias
        proprias.ajustar(con, "x", "tst-001-100", 2)
        antes = sorted(tuple(r) for r in con.execute(
            "SELECT printing_id, qty FROM copies"))
        with self.assertRaises(colar.PrecisaConfirmar):
            colar.apagar(con, "x")
        colar.apagar(con, "x", confirmar=True)
        self.assertEqual(con.execute("SELECT COUNT(*) c FROM decks").fetchone()["c"], 0)
        self.assertEqual(sorted(tuple(r) for r in con.execute(
            "SELECT printing_id, qty FROM copies")), antes)
        self.assertTrue(locais.proprias(con).get("x"),
                        "as cópias próprias ficam gravadas")
        con.close()


class TestEdicoes(Base):
    """*"se houver em duas edicoes diferentes, conta as 2, seleciona a que
    cobrir o numero necessario, caso nao consiga, indica que e x de uma edicao e
    x de outra"* (André, 2026-10-01)."""

    def test_a_edicao_que_cobre_sozinha_vem_a_frente(self):
        from riftvault import decks
        # 1 cópia na edição antiga, 3 na nova; o pedido são 3.
        pids = ["a", "b"]
        sets = {"a": "OGN", "b": "UNL"}
        self.assertEqual(
            decks.por_cobertura(pids, 3, {"a": 1, "b": 3}, sets), ["b", "a"],
            "o UNL cobre sozinho as 3 — é por ele que se começa")

    def test_quando_nenhuma_cobre_a_ordem_nao_muda(self):
        """E aí é a PÁGINA que diz «x de uma edição e x de outra»."""
        from riftvault import decks
        sets = {"a": "OGN", "b": "UNL"}
        self.assertEqual(
            decks.por_cobertura(["a", "b"], 3, {"a": 1, "b": 1}, sets), ["a", "b"])

    def test_a_ordem_do_catalogo_e_o_desempate(self):
        from riftvault import decks
        sets = {"a": "OGN", "b": "UNL"}
        self.assertEqual(
            decks.por_cobertura(["a", "b"], 3, {"a": 3, "b": 3}, sets), ["a", "b"],
            "cobrindo as duas, fica a mais antiga — não se mexe no que já era")

    def test_uma_copia_so_ou_uma_edicao_so_nao_mexe_em_nada(self):
        from riftvault import decks
        sets = {"a": "OGN", "b": "UNL"}
        self.assertEqual(decks.por_cobertura(["a", "b"], 1, {"a": 1, "b": 9}, sets),
                         ["a", "b"], "com uma cópia não há repartição possível")
        self.assertEqual(decks.por_cobertura(["a"], 3, {"a": 1}, sets), ["a"])

    def test_a_unidade_e_a_EDICAO_e_nao_a_impressao(self):
        """Duas impressões da mesma edição somam-se: juntas cobrem."""
        from riftvault import decks
        sets = {"a": "OGN", "b": "OGN", "c": "UNL"}
        self.assertEqual(
            decks.por_cobertura(["c", "a", "b"], 3, {"a": 2, "b": 1, "c": 1}, sets),
            ["a", "b", "c"], "as duas do OGN cobrem as 3; a do UNL não")

    def test_o_deck_serve_se_da_edicao_que_cobre(self):
        """Na alocação a sério, e não só na função."""
        from riftvault import collection, decks
        con = self.catalogo(cartas=[("Defy", "Unit")], duas_edicoes=True)
        collection.adjust(con, "tst-001-100", 1, source="test")   # TST: 1
        collection.adjust(con, "ts2-001-100", 3, source="test")   # TS2: 3
        self.v.write_deck("x", "Nome: X\nMainDeck:\n3 Defy\n")
        decks.import_all(con, log=lambda *_: None)
        c = self._cartas(decks.deck_payload(con, decks.deck_rows(con)[0]["deck_id"]))[0]
        self.assertEqual(c["have"], 3)
        sets = {v["set"] for v in c["versoes"]}
        self.assertEqual(sets, {"TS2"},
                         "as 3 saem todas do TS2, que as cobria sozinho")
        con.close()

    def test_a_versao_leva_a_EDICAO_no_payload(self):
        """É com ela que a página escreve «2 de OGN + 1 de UNL»."""
        from riftvault import collection, decks
        con = self.catalogo(cartas=[("Defy", "Unit")], duas_edicoes=True)
        collection.adjust(con, "tst-001-100", 2, source="test")
        collection.adjust(con, "ts2-001-100", 1, source="test")
        self.v.write_deck("x", "Nome: X\nMainDeck:\n3 Defy\n")
        decks.import_all(con, log=lambda *_: None)
        c = self._cartas(decks.deck_payload(con, decks.deck_rows(con)[0]["deck_id"]))[0]
        por = {v["set"]: v["qty"] for v in c["versoes"]}
        self.assertEqual(por, {"TST": 2, "TS2": 1},
                         "nenhuma cobria sozinha: reparte-se, e diz-se como")
        con.close()

    def test_o_app_js_escreve_as_duas_edicoes_e_o_que_tapou(self):
        js = (REPO / "riftvault" / "web" / "app.js").read_text(encoding="utf-8")
        self.assertIn("function edicoesNota", js)
        self.assertIn("function tapadaNota", js)
        self.assertIn("de ${escapeHTML(s)}", js)
        self.assertIn("edicoesNota(c)", js)


class TestComQueSeTapou(Base):
    """*"Se nao houver versao normal, ele avisa que sao X normais e X Alt Art /
    Overnumbered ou o que quer que seja"*.

    O MECANISMO já existia (2026-09-17, `Versoes.outras_de`) e o
    `decks.so_base: true` desliga-o. Estes testes fixam as duas pontas: o que
    acontece com ele ligado, e que o config de HOJE o tem desligado — para
    ninguém o virar sem ser ele a decidir.
    """

    def test_o_config_de_HOJE_tem_so_base_LIGADO(self):
        cfg = json.loads((REPO / "riftvault_config.json").read_text(encoding="utf-8"))
        self.assertTrue(cfg["decks"]["so_base"],
                        "mudar isto é decisão do André, não nossa")

    def test_com_so_base_a_alt_art_NAO_tapa(self):
        from riftvault import collection, decks
        con = self._com_alt_art()
        collection.adjust(con, "tst-001-100", 1, source="test")
        collection.adjust(con, "tst-001a-100", 2, source="test")
        self.v.write_deck("x", "Nome: X\nMainDeck:\n3 Defy\n")
        decks.import_all(con, log=lambda *_: None)
        c = self._cartas(decks.deck_payload(con, decks.deck_rows(con)[0]["deck_id"]))[0]
        self.assertEqual((c["have"], c["missing"], c["outras"]), (1, 2, 0))
        con.close()

    def test_sem_so_base_a_alt_art_tapa_e_a_pagina_di_lo(self):
        from tests.fixture import config_decks_sem_alt_art
        config_decks_sem_alt_art(self)
        self.v.close()
        self.v = Vault()
        self.addCleanup(self.v.close)
        from riftvault import collection, decks
        con = self._com_alt_art()
        collection.adjust(con, "tst-001-100", 1, source="test")
        collection.adjust(con, "tst-001a-100", 2, source="test")
        self.v.write_deck("x", "Nome: X\nMainDeck:\n3 Defy\n")
        decks.import_all(con, log=lambda *_: None)
        c = self._cartas(decks.deck_payload(con, decks.deck_rows(con)[0]["deck_id"]))[0]
        self.assertEqual((c["have"], c["missing"]), (3, 0))
        self.assertEqual(c["outras"], 2, "2 cópias vieram de outra versão")
        rotulos = {v["label"]: v["qty"] for v in c["versoes"]}
        self.assertEqual(rotulos, {"normal": 1, "Alt Art": 2},
                         "«1 normal, 2 Alt Art» — as palavras dele")
        con.close()

    def _com_alt_art(self):
        con = self.v.connect()
        self.v.add_printing(con, "tst-001-100", "TST", 1, "Defy")
        self.v.add_printing(con, "tst-001a-100", "TST", 1, "Defy", variant="a",
                            kind="alt_art", rarity="showcase", base_rarity="common")
        self.v.rebuild(con)
        return con


class TestACor(Base):
    """*"com imagem com cor e sem cor"* — a cores quando tem, a cinzento quando
    não tem. Faz-se em CSS, não se geram imagens novas."""

    def test_o_tile_marca_sem_cor_quando_nao_tem_nenhuma(self):
        js = (REPO / "riftvault" / "web" / "app.js").read_text(encoding="utf-8")
        self.assertIn("const semCor = !c.have ? ' sem-cor' : '';", js)
        self.assertIn("${semCor}", js)

    def test_e_cinzento_por_CSS_e_nao_por_imagem_nova(self):
        css = (REPO / "riftvault" / "web" / "style.css").read_text(encoding="utf-8")
        self.assertIn(".dtile .art.sem-cor img", css)
        self.assertIn("filter: grayscale(1)", css)

    def test_o_crachá_e_a_moldura_ficam_a_cores(self):
        """A cinzento é a ARTE. O «2/3» e a cor da moldura são a informação."""
        css = (REPO / "riftvault" / "web" / "style.css").read_text(encoding="utf-8")
        regra = css[css.index(".dtile .art.sem-cor img"):][:200]
        self.assertNotIn(".badge", regra)
        self.assertNotIn(".need", regra)


class TestAColecaoNaoMexe(Base):
    """Colar uma lista não mexe num número da Coleção.

    É a defesa das cópias próprias (2026-09-21), do foil (22/09) e da Venda
    (25/09), para a porta nova. Um deck novo MUDA o que está em uso e o que
    falta comprar — isso é o ponto dele —, mas não pode mexer nos ALVOS, no
    denominador, nos níveis, no valor nem numa cópia.
    """

    def _foto(self, con):
        from riftvault import metrics, prices
        cfg = self.config.load()
        return {
            "niveis": metrics.niveis_payload(con, cfg),
            "copies": sorted(tuple(r) for r in con.execute(
                "SELECT printing_id, qty, qty_foil FROM copies")),
            "valor": prices.collection_value(con)["cents"],
            "ops": con.execute("SELECT COUNT(*) c FROM ops").fetchone()["c"],
            "locais": sorted(tuple(r) for r in con.execute(
                "SELECT printing_id, location, qty FROM copy_locations")),
        }

    def test_colar_e_apagar_nao_mexem_em_numero_nenhum(self):
        from riftvault import colar
        con = self.catalogo(copias={"tst-001-100": 3, "tst-002-100": 2})
        antes = self._foto(con)
        colar.gravar(con, LISTA_REAL.read_text(encoding="utf-8"))
        self.assertEqual(self._foto(con), antes, "gravar não mexeu")
        colar.apagar(con, "leona-radiant-dawn", confirmar=True)
        self.assertEqual(self._foto(con), antes, "apagar também não")
        con.close()

    def test_a_fotografia_nao_e_de_zeros(self):
        """Prova pela negativa: ela SABE detectar uma mudança."""
        from riftvault import collection
        con = self.catalogo(copias={"tst-001-100": 3})
        antes = self._foto(con)
        collection.adjust(con, "tst-002-100", 1, source="test")
        self.assertNotEqual(self._foto(con), antes)
        con.close()


class TestRotasECLI(Base):
    """As rotas, e o site publicado que não as tem."""

    def test_as_tres_rotas_respondem(self):
        con = self.catalogo(cartas=[("Defy", "Unit")])
        con.close()
        from riftvault import server
        importlib.reload(server)
        server.app.testing = True
        with server.app.test_client() as c:
            texto = "Nome: X\nMainDeck:\n3 Defy\n"
            r = c.post("/api/decks/prever", json={"texto": texto})
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.get_json()["slug"], "x")
            self.assertEqual(r.get_json()["totais"]["copias"], 3)

            r = c.post("/api/decks/prever", json={"texto": "nada"})
            self.assertEqual(r.status_code, 400)
            self.assertIn("error", r.get_json())

            r = c.post("/api/decks/colar", json={"texto": texto})
            self.assertEqual(r.status_code, 200)
            self.assertTrue(r.get_json()["gravado"])
            self.assertTrue(r.get_json()["decks"], "devolve o índice refeito")

            # Segunda vez, sem `substituir`: 409 e diz o que falta.
            r = c.post("/api/decks/colar", json={"texto": texto})
            self.assertEqual(r.status_code, 409)
            self.assertEqual(r.get_json()["precisa"], "substituir")

            # Uma linha que não casa: 409 a pedir `confirmar`.
            r = c.post("/api/decks/colar",
                       json={"texto": "Nome: Y\nMainDeck:\n1 Nao Existe\n"})
            self.assertEqual(r.status_code, 409)
            self.assertEqual(r.get_json()["precisa"], "confirmar")

            r = c.post("/api/decks/apagar", json={"slug": "x"})
            self.assertEqual(r.status_code, 409)
            r = c.post("/api/decks/apagar", json={"slug": "x", "confirmar": True})
            self.assertEqual(r.status_code, 200)
            r = c.post("/api/decks/apagar", json={"slug": "nao-ha", "confirmar": True})
            self.assertEqual(r.status_code, 404)

    def test_o_gravar_nao_substitui_a_cegas(self):
        """O `substituir` sai da PREVISÃO, não é `true` fixo: um deck que
        tenha nascido entre o «Ler» e o «Gravar» faz o servidor dar 409 em vez
        de ser escrito por cima sem perguntar."""
        js = (REPO / "riftvault" / "web" / "app.js").read_text(encoding="utf-8")
        i = js.index("async function colarGravar")
        corpo = js[i:js.index("\n}\n", i)]
        self.assertIn("substituir: !!e.ocupado", corpo)
        self.assertNotIn("substituir: true", corpo)

    def test_as_frases_do_cabecalho_nao_sao_capitalizadas(self):
        """O `.section-head` é `text-transform: capitalize` e só o `<span>`
        está isento. Com `<small>` lia-se «Vai Gravar-Se Como Leona-Radiant-
        Dawn.Txt» — a mesma avaria do Produto Selado (2026-09-25). Apanhada na
        FOTOGRAFIA, não no código."""
        js = (REPO / "riftvault" / "web" / "app.js").read_text(encoding="utf-8")
        i = js.index("Colar uma lista</h2>")
        self.assertIn("<span>copy-paste", js[i:i + 200])
        j = js.index("<h3>${escapeHTML(p.nome)}</h3>")
        self.assertIn("<span>vai gravar-se", js[j:j + 200])
        css = (REPO / "riftvault" / "web" / "style.css").read_text(encoding="utf-8")
        i = css.index(".section-head span")
        self.assertIn("text-transform: none", css[i:i + 160])

    def test_o_botao_de_apagar_a_lista_existe_e_chama_a_rota(self):
        """O par da caixa: quem mete uma lista pela janela tira-a por lá.
        Era a última coisa que ainda obrigava a ir à pasta à mão."""
        js = (REPO / "riftvault" / "web" / "app.js").read_text(encoding="utf-8")
        self.assertIn("data-act=\"apagar-lista\"", js)
        self.assertIn("if (act === 'apagar-lista') return apagarLista();", js)
        i = js.index("async function apagarLista")
        corpo = js[i:js.index("\n}\n", i)]
        self.assertIn("api/decks/apagar", corpo)
        self.assertIn("confirm(", corpo, "apagar pede confirmação")
        self.assertIn("cabecalhos()", corpo)
        self.assertIn("NÃO se apagam", corpo, "e diz que as cópias ficam")

    def test_a_caixa_so_existe_no_modo_edicao(self):
        js = (REPO / "riftvault" / "web" / "app.js").read_text(encoding="utf-8")
        self.assertIn("const entrar = state.editable ? [{", js)
        self.assertIn("COLAR_ID", js)

    def test_os_POST_passam_pelos_cabecalhos_comuns(self):
        """A regra de 2026-09-29: um POST sem o CSRF do `cabecalhos()` é uma
        rota sem protecção."""
        js = (REPO / "riftvault" / "web" / "app.js").read_text(encoding="utf-8")
        for rota in ("api/decks/prever", "api/decks/colar"):
            i = js.index(rota)
            self.assertIn("cabecalhos()", js[max(0, i - 300):i + 300],
                          f"o POST a {rota} tem de levar os cabeçalhos")

    def test_a_CLI_mostra_sem_gravar_e_grava_com_gravar(self):
        """O gémeo da caixa, na consola — e pela MESMA porta."""
        import contextlib
        import io
        con = self.catalogo(cartas=[("Defy", "Unit")])
        con.close()
        lista = self.v.root / "lista.txt"
        lista.write_text("Nome: X\nMainDeck:\n3 Defy\n", encoding="utf-8")
        from riftvault import cli
        importlib.reload(cli)

        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(["colar", str(lista)]), 0)
        self.assertIn("x.txt", out.getvalue())
        self.assertEqual(list(self.v.decks_dir.glob("*.txt")), [],
                         "sem --gravar não grava")

        with contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(["colar", str(lista), "--gravar"]), 0)
        self.assertEqual([p.name for p in self.v.decks_dir.glob("*.txt")], ["x.txt"])

        # Uma linha que não casa: sai 1 e diz o que fazer.
        lista.write_text("Nome: Y\nMainDeck:\n1 Nao Existe\n", encoding="utf-8")
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            self.assertEqual(cli.main(["colar", str(lista), "--gravar"]), 1)
        self.assertIn("--confirmar", err.getvalue())

    def test_a_frase_do_sem_decks_e_a_MESMA_nos_dois_sitios(self):
        """E passou a dizer a porta nova (2026-10-02)."""
        from riftvault import decks
        js = (REPO / "riftvault" / "web" / "app.js").read_text(encoding="utf-8")
        self.assertIn(decks.SEM_DECKS, js)
        for pedaco in ("Cola a lista na secção Decks", "decks/"):
            self.assertIn(pedaco, decks.SEM_DECKS_COMO)
            self.assertIn(pedaco, js)


class TestOCR(Base):
    """A LEITURA POR IMAGEM, que NÃO se fez — e porquê.

    André, 2026-10-01: *"quero que, para introduzir uma decklist, a seccao de
    decks seja possivel ler 2 tipos: Imagem / TxT introduzido"*. Medido a
    2026-10-02 na máquina dele: **não há OCR instalado** — nem `pytesseract`,
    nem `tesseract` no PATH, nem `easyocr`, `paddleocr` ou
    `rapidocr_onnxruntime`. Há `PIL` e `numpy`, que abrem uma imagem e não
    lêem texto nenhum dela.

    A regra da casa é não instalar nada por iniciativa própria, por isso a
    metade da imagem fica por fazer e está DITA em vez de meio-feita. Este
    teste existe para o dia em que alguém instalar um OCR: aí falha, e é o
    sinal de que a segunda metade pode ser construída.
    """

    def test_nao_ha_OCR_instalado_e_por_isso_a_imagem_ficou_por_fazer(self):
        import importlib.util
        import shutil
        achados = [m for m in ("pytesseract", "easyocr", "paddleocr",
                               "rapidocr_onnxruntime")
                   if importlib.util.find_spec(m) is not None]
        achados += [x for x in ("tesseract",) if shutil.which(x)]
        self.assertEqual(
            achados, [],
            "apareceu um OCR na máquina: a leitura por IMAGEM já se pode "
            "fazer. O critério é o dele — só entra o que casa EXACTAMENTE com "
            "o catálogo, e diz-se quantas linhas não conseguiu ler.")


if __name__ == "__main__":
    unittest.main()

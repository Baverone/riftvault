"""APAGAR OS DECKS TODOS, e ZERO DECKS como estado normal (André, 2026-09-28).

Palavras dele: *"apaga os decks todos, vamos atualizar com as listas novas
posteriormente"* — houve um torneio grande e as listas vão ser substituídas
pelas melhores de cada Legend que saírem de lá.

O que este ficheiro fixa:

  1. `decks.apagar_todos` apaga as QUATRO coisas — os `decks/*.txt` (arquivados
     primeiro), as linhas da `decks` e da `deck_cards`, o `deck_need_log` e o
     estado no config (`montados`, `principal`, `ordem`);
  2. **AS REGRAS DO CONFIG NÃO SE TOCAM** (`so_base`, `venda_minimo_cents`,
     `coleccao_so_a_partir_de`, `modo`, `versoes_especiais`, `contar_runas`):
     são decisões dele e as listas novas vão querer as mesmas;
  3. **A COLEÇÃO NÃO MUDA UM NÚMERO** — é a fotografia, e é a promessa que a
     ordem faz. A `copies` fica byte a byte igual;
  4. a REGRA DA VENDA de 2026-09-27 é honrada: as cópias próprias do deck
     PRINCIPAL que valham `venda_minimo_cents` ganham linha na Venda, as de
     menos ficam, e **nada sai do `proprio:<slug>`** — entrar na Venda não é
     vender. Sem cópias próprias (o caso de hoje) a `sale_lines` não ganha
     linha nenhuma;
  5. as cópias próprias **não se apagam**: ficam gravadas, fora da Coleção e
     do valor, como já acontecia a um deck cujo `.txt` desaparecia;
  6. **ZERO DECKS É UM ESTADO NORMAL** e nada rebenta: os payloads, as duas
     metades das Faltas, a wantlist, o painel, o `build`, a CLI e as rotas;
  7. onde a lista fica vazia há uma FRASE, não um vazio mudo — e é a MESMA na
     consola e no site (`decks.SEM_DECKS`, `SEM_DECKS_COMO` ↔ `app.js`);
  8. o cartão «Decks montados» do Início não pode dizer «0 de 0 · estão todos
     completos», que era o que dizia.

Tudo contra pastas temporárias (`tests.fixture.Vault`) e um config temporário
(`RIFTVAULT_CONFIG`): o `data/` e o `riftvault_config.json` a sério nunca são
tocados.
"""

from __future__ import annotations

import contextlib
import hashlib
import importlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ["RIFTVAULT_CONFIG"] = str(Path(tempfile.gettempdir()) / "riftvault-nao-existe.json")

from tests.fixture import REPO, Vault  # noqa: E402

AZIR = ("Nome: Azir\n\nLegend:\n1 Emperor of the Sands\n\nChampion:\n1 Brutalizer\n\n"
        "MainDeck:\n3 Defy\n2 Salvage\n\nRune Pool:\n3 Fury Rune\n\n"
        "Sideboard:\n1 Defy\n1 Hidden Blade\n")
ORNN = ("Nome: Ornn\n\nLegend:\n1 Fire Below the Mountain\n\n"
        "MainDeck:\n2 Defy\n3 Salvage\n2 Hidden Blade\n\nRune Pool:\n3 Fury Rune\n")

APP_JS = (REPO / "riftvault" / "web" / "app.js").read_text(encoding="utf-8")
CSS = (REPO / "riftvault" / "web" / "style.css").read_text(encoding="utf-8")
CLI_PY = (REPO / "riftvault" / "cli.py").read_text(encoding="utf-8")


class Base(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.close)
        from riftvault import (a_mais, a_subir, build, collection, config, db, decks,
                               faltas, faltas_edicao, faltas_foil, foil, locais, metrics,
                               painel, pending, prices, principal, proprias, uso_decks,
                               venda)
        for m in (locais, metrics, painel, decks, proprias, a_subir, faltas_edicao,
                  faltas_foil, foil, a_mais, pending, faltas, prices, venda, principal,
                  uso_decks, build):
            importlib.reload(m)
        self.config, self.decks, self.proprias, self.locais = config, decks, proprias, locais
        self.metrics, self.a_subir, self.faltas_edicao = metrics, a_subir, faltas_edicao
        self.a_mais, self.pending, self.faltas, self.prices = a_mais, pending, faltas, prices
        self.collection, self.painel, self.venda = collection, painel, venda
        self.principal, self.uso_decks, self.build = principal, uso_decks, build
        self.faltas_foil, self.foil, self.db = faltas_foil, foil, db
        self.cfg_decks({})

    def cfg_decks(self, decks_extra: dict, extra: dict | None = None):
        """O config temporário com as REGRAS de hoje mais o que o teste quiser."""
        caminho = self.v.root / "config.json"
        caminho.write_text(json.dumps({"decks": {
            "so_base": True, "so_normais_excepto": [],
            "versoes_especiais": ["a", "overnumbered", "promo"],
            "coleccao_so_a_partir_de": "epic", "modo": "coleccao",
            "contar_runas": False, "venda_minimo_cents": 50, **decks_extra},
            **(extra or {})}, ensure_ascii=False), encoding="utf-8")
        os.environ["RIFTVAULT_CONFIG"] = str(caminho)
        importlib.reload(self.config)
        self.config.load.cache_clear()

        def repor():
            os.environ["RIFTVAULT_CONFIG"] = str(
                Path(tempfile.gettempdir()) / "riftvault-nao-existe.json")
            importlib.reload(self.config)
            self.config.load.cache_clear()

        self.addCleanup(repor)
        return caminho

    def catalogo(self, decks=("azir", "ornn")):
        con = self.v.connect()
        v = self.v
        v.add_printing(con, "tst-001-100", "TST", 1, "Defy", rarity="rare", size=100)
        v.add_printing(con, "tst-002-100", "TST", 2, "Brutalizer", rarity="rare", size=100)
        v.add_printing(con, "tst-003-100", "TST", 3, "Emperor of the Sands",
                       card_type="Legend", rarity="epic", size=100)
        v.add_printing(con, "tst-004-100", "TST", 4, "Salvage", rarity="common", size=100)
        v.add_printing(con, "tst-005-100", "TST", 5, "Hidden Blade", rarity="uncommon", size=100)
        v.add_printing(con, "tst-006-100", "TST", 6, "Fury Rune", card_type="Rune", size=100)
        v.add_printing(con, "tst-007-100", "TST", 7, "Fire Below the Mountain",
                       card_type="Legend", rarity="epic", size=100)
        v.rebuild(con)
        for pid, cents in (("tst-001-100", 150), ("tst-002-100", 80),
                           ("tst-003-100", 1000), ("tst-004-100", 20),
                           ("tst-005-100", 300), ("tst-006-100", 11),
                           ("tst-007-100", 500)):
            con.execute("INSERT INTO catalog.price_latest (printing_id, price_cents) "
                        "VALUES (?,?)", (pid, cents))
        for pid, n in (("tst-001-100", 5), ("tst-004-100", 6), ("tst-005-100", 3),
                       ("tst-002-100", 2), ("tst-003-100", 1), ("tst-007-100", 1)):
            self.collection.adjust(con, pid, n, source="test")
        for slug, texto in (("azir", AZIR), ("ornn", ORNN)):
            if slug in decks:
                self.v.write_deck(slug, texto)
        self.decks.import_all(con, log=lambda *_: None)
        self.addCleanup(con.close)
        return con

    def apagar(self, con, **kw):
        return self.decks.apagar_todos(con, log=lambda *_: None, **kw)

    # -- a fotografia -----------------------------------------------------

    def sha_copies(self, con) -> str:
        rows = con.execute("SELECT printing_id, qty, qty_foil FROM copies "
                           "ORDER BY printing_id").fetchall()
        return hashlib.sha256(
            "\n".join(f"{r[0]}|{r[1]}|{r[2]}" for r in rows).encode()).hexdigest()

    def fotografia(self, con) -> dict:
        """Tudo o que é NÚMERO DA COLEÇÃO. Tem de ser igual antes e depois."""
        cfg = self.config.load()
        sp = self.metrics.set_payload(con, "TST")
        ff = self.faltas_foil.payload_completo(con, cfg)
        return {
            "niveis": [(l["k"], l["done"], l["total"], l["missing"], l["cents"])
                       for l in self.metrics.niveis_payload(con, cfg)["levels"]],
            "wantlist": {k: self.a_subir.wantlist(con, cfg=cfg)[k]
                         for k in ("text", "lines", "copies", "cents")},
            "valor": self.prices.collection_value(con)["cents"],
            "valor_copias": self.prices.collection_value(con)["copias"],
            "totais": self.collection.totals(con),
            "grelha": [(p["id"], p["qty"], p["target"], p["qty_valor"],
                        p.get("foil"), p.get("qty_total"))
                       for g in sp["groups"] for p in g["printings"]],
            "master": sp["progress"]["master"],
            "painel": sp["progress"]["painel"],
            "foil": sp["progress"].get("foil"),
            "faltas": (ff["totals"], ff["totals_lists"]),
            "faltas_foil": (ff.get("foil") or {}).get("totals"),
            "encomendas": self.pending.encomendas(con)["totals"],
            "copies": self.sha_copies(con),
        }


# ---------------------------------------------------------------------------


class TestApagaAsQuatroCoisas(Base):
    """1. As listas, as linhas, o registo e o estado no config."""

    def test_apaga_os_txt_e_arquiva_os_primeiro(self):
        con = self.catalogo()
        self.assertEqual(len(list(self.v.decks_dir.glob("*.txt"))), 2)
        res = self.apagar(con)
        self.assertEqual(list(self.v.decks_dir.glob("*.txt")), [])
        self.assertEqual(sorted(res["apagados"]), ["azir.txt", "ornn.txt"])
        arq = Path(res["arquivo"])
        self.assertTrue(arq.is_dir(), "tinha de haver pasta de arquivo")
        self.assertEqual(sorted(p.name for p in arq.glob("*.txt")),
                         ["azir.txt", "ornn.txt"])
        # O arquivo é BYTE A BYTE a lista que se apagou.
        self.assertEqual((arq / "azir.txt").read_text(encoding="utf-8"), AZIR)

    def test_sem_arquivar_nao_escreve_pasta_nenhuma(self):
        con = self.catalogo()
        res = self.apagar(con, arquivar=False)
        self.assertIsNone(res["arquivo"])
        self.assertEqual(list(self.v.decks_dir.glob("*.txt")), [])

    def test_apaga_as_linhas_das_duas_tabelas(self):
        con = self.catalogo()
        self.assertTrue(con.execute("SELECT COUNT(*) FROM decks").fetchone()[0])
        self.assertTrue(con.execute("SELECT COUNT(*) FROM deck_cards").fetchone()[0])
        res = self.apagar(con)
        self.assertEqual(con.execute("SELECT COUNT(*) FROM decks").fetchone()[0], 0)
        self.assertEqual(con.execute("SELECT COUNT(*) FROM deck_cards").fetchone()[0], 0)
        self.assertEqual(sorted(res["removidos"]), ["azir", "ornn"])

    def test_recomeca_o_registo_em_vez_de_o_encher_de_descidas(self):
        """Sem isto, as listas velhas ficavam registadas como uma descida a 0
        por carta — e o «A mais» lê isso como cartas que ele deixou de jogar
        (a lição de 2026-09-21)."""
        con = self.catalogo()
        self.assertTrue(con.execute("SELECT COUNT(*) FROM deck_need_log").fetchone()[0])
        res = self.apagar(con)
        self.assertEqual(con.execute("SELECT COUNT(*) FROM deck_need_log").fetchone()[0], 0)
        self.assertEqual(res["registo"], 0)
        # E por isso as «libertadas» do A mais ficam VAZIAS — se o registo
        # ficasse com as descidas, elas diziam que ele deixou de jogar tudo.
        am = self.a_mais.payload(con, self.config.load())
        self.assertEqual(am["totals"]["libertadas"]["cards"], 0)
        self.assertEqual(am["totals"]["libertadas"]["copies"], 0)

    def test_limpa_o_estado_do_config(self):
        self.cfg_decks({"montados": ["Azir"], "principal": "Azir",
                        "ordem": ["Azir", "Ornn"]})
        con = self.catalogo()
        self.apagar(con)
        cfg = self.config.load()
        self.assertEqual(cfg["decks"]["montados"], [])
        self.assertIsNone(cfg["decks"]["principal"])
        self.assertEqual(cfg["decks"]["ordem"], [])

    def test_sem_decks_nao_ha_nada_para_apagar_e_nao_rebenta(self):
        con = self.catalogo(decks=())
        res = self.apagar(con)
        self.assertEqual(res["decks"], [])
        self.assertEqual(res["apagados"], [])


class TestAsRegrasNaoSeTocam(Base):
    """2. As regras são decisões dele — as listas novas vão querer as mesmas."""

    REGRAS = ("so_base", "venda_minimo_cents", "coleccao_so_a_partir_de",
              "modo", "versoes_especiais", "contar_runas")

    def test_as_seis_regras_ficam_como_estavam(self):
        self.cfg_decks({"montados": ["Azir"], "principal": "Azir",
                        "ordem": ["Azir", "Ornn"]})
        con = self.catalogo()
        antes = {k: self.config.load()["decks"].get(k) for k in self.REGRAS}
        self.apagar(con)
        depois = {k: self.config.load()["decks"].get(k) for k in self.REGRAS}
        self.assertEqual(antes, depois)
        # E não são todas `None` — senão o teste passava sem provar nada.
        self.assertTrue(any(v is not None for v in antes.values()))

    def test_o_bloco_decks_so_perde_as_tres_chaves_de_estado(self):
        self.cfg_decks({"montados": ["Azir"], "principal": "Azir",
                        "ordem": ["Azir", "Ornn"]})
        con = self.catalogo()
        antes = dict(self.config.load()["decks"])
        self.apagar(con)
        depois = dict(self.config.load()["decks"])
        mudou = {k for k in set(antes) | set(depois) if antes.get(k) != depois.get(k)}
        self.assertEqual(mudou, {"montados", "principal", "ordem"})


class TestAColecaoNaoMudaUmNumero(Base):
    """3. A promessa da ordem, fotografada."""

    def test_apagar_os_decks_nao_mexe_em_numero_nenhum_da_colecao(self):
        self.cfg_decks({"montados": ["Azir"], "principal": "Azir",
                        "ordem": ["Azir", "Ornn"]})
        con = self.catalogo()
        antes = self.fotografia(con)
        self.apagar(con)
        depois = self.fotografia(con)
        for chave in antes:
            self.assertEqual(antes[chave], depois[chave],
                             f"{chave} mexeu ao apagar os decks")

    def test_a_fotografia_nao_e_de_zeros(self):
        """Senão o teste acima passava com tudo vazio."""
        con = self.catalogo()
        f = self.fotografia(con)
        self.assertTrue(f["valor"] > 0)
        self.assertTrue(f["totais"]["copies"] > 0)
        self.assertTrue(f["grelha"])
        self.assertTrue(any(l[1] for l in f["niveis"]))

    def test_a_copies_fica_byte_a_byte_igual(self):
        con = self.catalogo()
        antes = self.sha_copies(con)
        n_ops = con.execute("SELECT COUNT(*) FROM ops").fetchone()[0]
        self.apagar(con)
        self.assertEqual(self.sha_copies(con), antes)
        self.assertEqual(con.execute("SELECT COUNT(*) FROM ops").fetchone()[0], n_ops,
                         "apagar decks não pode escrever na `ops`")

    def test_o_uso_na_grelha_desaparece_porque_nao_ha_decks(self):
        """A única coisa que MUDA na grelha é o «em uso no deck X» — e isso não
        é um número da Coleção, é a informação de que um deck a estava a usar."""
        con = self.catalogo()
        usos = self.decks.uso_por_carta(con)
        self.assertTrue(usos, "os decks tinham de estar a usar alguma coisa")
        self.apagar(con)
        self.assertEqual(self.decks.uso_por_carta(con), {})


class TestAVendaEAsProprias(Base):
    """4 e 5. A regra dos 0,50 € e as cópias próprias que ficam."""

    def test_sem_proprias_a_venda_nao_ganha_linha_nenhuma(self):
        """O caso de hoje: ele não tem nenhuma cópia própria marcada."""
        self.cfg_decks({"principal": "Azir"})
        con = self.catalogo()
        self.assertEqual(self.locais.proprias(con), {})
        antes = con.execute("SELECT COUNT(*) FROM sale_lines").fetchone()[0]
        res = self.apagar(con)
        self.assertEqual(con.execute("SELECT COUNT(*) FROM sale_lines").fetchone()[0],
                         antes)
        self.assertEqual(res["proprias"], {})

    def test_as_proprias_do_principal_acima_do_minimo_vao_a_venda(self):
        self.cfg_decks({"principal": "Azir"})
        con = self.catalogo()
        # 1 Defy (1,50 €, acima) e 1 Salvage (0,20 €, abaixo) próprias do Azir.
        self.proprias.ajustar(con, "azir", "tst-001-100", 1, source="test")
        self.proprias.ajustar(con, "azir", "tst-004-100", 1, source="test")
        self.apagar(con)
        linhas = {r["printing_id"]: r for r in con.execute(
            "SELECT printing_id, qty, origem FROM sale_lines")}
        self.assertIn("tst-001-100", linhas, "a de 1,50 € tinha de ir à Venda")
        self.assertNotIn("tst-004-100", linhas, "a de 0,20 € fica")
        self.assertEqual(linhas["tst-001-100"]["origem"], "deck:azir")

    def test_entrar_na_venda_nao_e_vender_nada_sai_do_proprio(self):
        self.cfg_decks({"principal": "Azir"})
        con = self.catalogo()
        self.proprias.ajustar(con, "azir", "tst-001-100", 1, source="test")
        antes = self.sha_copies(con)
        self.apagar(con)
        self.assertEqual(self.sha_copies(con), antes, "a Venda não vende")
        self.assertEqual(self.locais.proprias_de(con, "azir"), {"tst-001-100": 1},
                         "a cópia continua no proprio:azir")

    def test_as_proprias_nao_se_apagam_e_dizem_se(self):
        con = self.catalogo()
        self.proprias.ajustar(con, "ornn", "tst-001-100", 2, source="test")
        res = self.apagar(con)
        self.assertEqual(res["proprias"], {"ornn": 2})
        self.assertEqual(self.locais.proprias_de(con, "ornn"), {"tst-001-100": 2})

    def test_as_proprias_continuam_fora_da_colecao_e_do_valor(self):
        con = self.catalogo()
        self.proprias.ajustar(con, "ornn", "tst-001-100", 2, source="test")
        antes = self.fotografia(con)
        self.apagar(con)
        for chave in antes:
            self.assertEqual(antes[chave], self.fotografia(con)[chave], chave)

    def test_o_que_estava_sleevado_vai_para_o_binder_nunca_para_a_colecao(self):
        con = self.catalogo()
        self.locais.marcar(con, [{"printing_id": "tst-001-100", "qty": 1}],
                           self.locais.deck_local("azir"), source="test")
        na_colecao = self.locais.na_colecao(con).get("tst-001-100")
        self.apagar(con)
        por_local = {l["local"]: l for l in self.locais.resumo(con)}
        self.assertIn(self.locais.BINDER, por_local)
        self.assertEqual(self.locais.na_colecao(con).get("tst-001-100"), na_colecao,
                         "nada volta à Coleção — quem as tirou de lá foi ele")


class TestZeroDecksNaoRebenta(Base):
    """6. Zero decks é um estado normal."""

    def payloads(self, con):
        cfg = self.config.load()
        return {
            "allocate": self.decks.allocate(con),
            "index": self.decks.decks_index(con),
            "resumo": self.decks.resumo_das_faltas(con),
            "uso": self.decks.uso_por_carta(con),
            "shopping": self.decks.shopping_list(con),
            "foils": self.decks.foils_nos_decks(con, cfg),
            "montados": self.decks.montados_estado(con),
            "principal": self.principal.payload(con, cfg),
            "principal_wl": self.principal.wantlist(con, cfg),
            "compras": self.faltas.compras(con),
            "painel": self.painel.payload(con, cfg),
            "index_payload": self.metrics.index_payload(con, cfg),
            "set": self.metrics.set_payload(con, "TST"),
            "faltas": self.faltas_foil.payload_completo(con, cfg),
            "wantlist": self.a_subir.wantlist(con, cfg=cfg),
            "a_mais": self.a_mais.payload(con, cfg),
            "encomendas": self.pending.encomendas(con),
        }

    def test_os_payloads_todos_respondem(self):
        con = self.catalogo()
        self.apagar(con)
        for nome, valor in self.payloads(con).items():
            self.assertIsNotNone(valor, f"{nome} devolveu None")

    def test_o_deck_payload_de_um_id_que_ja_nao_existe_devolve_none(self):
        con = self.catalogo()
        did = next(r["deck_id"] for r in self.decks.deck_rows(con))
        self.apagar(con)
        self.assertIsNone(self.decks.deck_payload(con, did))

    def test_a_falta_a_comprar_aos_decks_fica_a_zero(self):
        con = self.catalogo()
        self.apagar(con)
        r = self.decks.resumo_das_faltas(con)
        self.assertEqual((r["copies"], r["cards"], r["cents"]), (0, 0, 0))

    def test_nao_ha_principal_nem_wantlist_dele(self):
        self.cfg_decks({"principal": "Azir"})
        con = self.catalogo()
        self.apagar(con)
        self.assertIsNone(self.decks.principal_slug(con))
        self.assertIsNone(self.principal.wantlist(con)["slug"])

    def test_o_build_gera_o_site_inteiro(self):
        con = self.catalogo()
        self.apagar(con)
        out = self.v.root / "site"
        self.build.build(out, log=lambda *_: None)
        d = json.loads((out / "api" / "decks.json").read_text(encoding="utf-8"))
        self.assertEqual(d["decks"], [])
        self.assertIsNone((d.get("principal") or {}).get("slug"))
        # Nenhum payload de deck órfão ficou para trás.
        self.assertFalse(list((out / "api").glob("deck/*.json")))
        # E o resto do site saiu na mesma.
        for nome in ("index.json", "wantlist.json", "faltas_edicao.json"):
            self.assertTrue((out / "api" / nome).exists(), nome)

    def test_as_rotas_respondem(self):
        con = self.catalogo()
        self.apagar(con)
        from riftvault import server
        importlib.reload(server)
        server.app.config["TESTING"] = True
        c = server.app.test_client()
        for url in ("/api/index.json", "/api/decks.json", "/api/compras.json",
                    "/api/faltas_edicao.json", "/api/set/TST.json",
                    "/api/a_mais.json", "/api/encomendas.json", "/"):
            self.assertEqual(c.get(url).status_code, 200, url)

    def test_a_cli_dos_decks_responde(self):
        con = self.catalogo()
        self.apagar(con)
        from riftvault import cli
        importlib.reload(cli)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            self.assertEqual(cli.main(["decks"]), 0)
            self.assertEqual(cli.main(["stats"]), 0)
            self.assertEqual(cli.main(["wantlist"]), 0)
            self.assertEqual(cli.main(["principal"]), 0)
        self.assertIn(self.decks.SEM_DECKS, buf.getvalue())


class TestAFraseEmVezDoVazioMudo(Base):
    """7 e 8. Onde a lista fica vazia há uma frase, e é a MESMA nos dois sítios."""

    def test_a_frase_e_a_mesma_na_consola_e_no_site(self):
        self.assertIn(f"const SEM_DECKS = '{self.decks.SEM_DECKS}'", APP_JS)
        self.assertIn(f"const SEM_DECKS_COMO = '{self.decks.SEM_DECKS_COMO}'", APP_JS)

    def test_a_frase_nao_crava_o_torneio_de_hoje(self):
        """Hoje é verdade e no mês que vem não: o que não muda é o estado e
        como sair dele."""
        for texto in (self.decks.SEM_DECKS, self.decks.SEM_DECKS_COMO):
            self.assertNotIn("torneio", texto.casefold())
        self.assertNotIn("torneio", APP_JS.casefold())
        self.assertNotIn("torneio", CLI_PY.casefold())

    def test_a_tabela_da_cli_nao_imprime_so_os_titulos(self):
        con = self.catalogo()
        self.apagar(con)
        from riftvault import cli
        importlib.reload(cli)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cli.main(["decks"])
        saida = buf.getvalue()
        self.assertIn(self.decks.SEM_DECKS, saida)
        self.assertNotIn("disputadas", saida, "a fila dos títulos não se imprime sozinha")

    def test_a_wantlist_dos_decks_nao_da_uma_linha_em_branco_muda(self):
        """O stdout tem de ficar COLÁVEL — a explicação vai para o stderr."""
        con = self.catalogo()
        self.apagar(con)
        from riftvault import cli
        importlib.reload(cli)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            cli.main(["wantlist"])
        self.assertEqual(out.getvalue().strip(), "", "o stdout tem de ficar colável")
        self.assertIn(self.decks.SEM_DECKS, err.getvalue())

    def test_a_dica_do_principal_nao_nomeia_um_deck_que_nao_existe(self):
        con = self.catalogo()
        self.apagar(con)
        from riftvault import cli
        importlib.reload(cli)
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            cli.main(["principal"])
        self.assertNotIn("leblanc-hook", err.getvalue(),
                         "a dica cravava um deck que pode já não existir")
        self.assertIn(self.decks.SEM_DECKS, err.getvalue())

    def test_o_cartao_do_inicio_nao_pode_dizer_que_estao_todos_completos(self):
        """Com `decks = []` o cartão dizia «0 de 0 · estão todos completos»."""
        i = APP_JS.index("'Decks montados'")
        trecho = APP_JS[max(0, i - 1200):i + 600]
        self.assertIn("decks && !decks.length", trecho,
                      "faltava o caso de ZERO decks, antes do `decks.length`")
        # E o caso de zero vem ANTES do que conta `cheios`/`decks.length`.
        self.assertLess(trecho.index("decks && !decks.length"),
                        trecho.index("const cheios"))
        self.assertIn("SEM_DECKS", trecho)

    def test_a_lista_do_inicio_diz_porque_esta_vazia(self):
        i = APP_JS.rindex("#inicio-decks")
        self.assertIn("SEM_DECKS", APP_JS[max(0, i - 400):i + 400])

    def test_o_indice_dos_decks_diz_porque_esta_vazio(self):
        """E a frase entra na LISTA PARTILHADA — senão o `<select>` do
        telemóvel ficava sem ela, que é a divergência que o `itensDoIndice`
        existe para evitar (a regra de 24/09, fixada no `test_casca`)."""
        i = APP_JS.index("function itensDoIndice")
        trecho = APP_JS[i:APP_JS.index("function renderDeckTabs")]
        self.assertIn("state.decks && !state.decks.length", trecho)
        self.assertIn("SEM_DECKS", trecho)
        self.assertIn("vazio: true", trecho)
        # Os dois renderizadores tratam-na, cada um à sua maneira.
        corpo = APP_JS[APP_JS.index("function renderDeckTabs"):]
        corpo = corpo[:corpo.index("\n}\n")]
        self.assertIn("vidx-vazio", corpo)
        self.assertIn("o.disabled = true", corpo)
        self.assertIn(".vidx .vidx-vazio", CSS)
        # E continua a NÃO ler o `state.decks` — é o guarda do `test_casca`.
        self.assertNotIn("state.decks", corpo)

    def test_a_pagina_do_deck_vazia_diz_que_a_colecao_nao_perdeu_nada(self):
        i = APP_JS.index("async function loadDecks")
        trecho = APP_JS[i:i + 1400]
        self.assertIn("SEM_DECKS", trecho)
        self.assertIn("mesmos números", trecho)


class TestACli(Base):
    """O `--apagar-todos`: pede confirmação, e o `--sim` faz."""

    def test_sem_sim_nao_apaga_nada(self):
        con = self.catalogo()
        from riftvault import cli
        importlib.reload(cli)
        with contextlib.redirect_stdout(io.StringIO()), \
             contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(["decks", "--apagar-todos"]), 1)
        self.assertEqual(len(list(self.v.decks_dir.glob("*.txt"))), 2)
        self.assertTrue(con.execute("SELECT COUNT(*) FROM decks").fetchone()[0])

    def test_com_sim_apaga(self):
        con = self.catalogo()
        from riftvault import cli
        importlib.reload(cli)
        with contextlib.redirect_stdout(io.StringIO()), \
             contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(["decks", "--apagar-todos", "--sim"]), 0)
        self.assertEqual(list(self.v.decks_dir.glob("*.txt")), [])
        self.assertEqual(con.execute("SELECT COUNT(*) FROM decks").fetchone()[0], 0)

    def test_faz_backup_do_vault_antes_de_mexer(self):
        self.catalogo()
        from riftvault import cli
        importlib.reload(cli)
        with contextlib.redirect_stdout(io.StringIO()), \
             contextlib.redirect_stderr(io.StringIO()):
            cli.main(["decks", "--apagar-todos", "--sim"])
        bks = list((self.v.data / "backups").glob("vault-antes-de-apagar-os-decks-*.db"))
        self.assertEqual(len(bks), 1, "faltou o backup do vault.db")

    def test_a_opcao_esta_documentada(self):
        self.assertIn("--apagar-todos", CLI_PY)
        self.assertIn("As REGRAS ficam", CLI_PY)


if __name__ == "__main__":
    unittest.main()

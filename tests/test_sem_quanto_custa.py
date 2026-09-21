"""O separador «Quanto custa» foi APAGADO (André, 2026-09-19: *"podes apagar o
botao do 'Quanto custa'"*).

Era a tabela de preços do jogo — por edição, o top 5 mais caras de comuns,
incomuns, raras e míticas, tenha ele ou não (2026-09-15, à tarde; nasceu do
antigo separador «Faltas»). Nunca contou para nada. O que se fixa aqui:

  1. o módulo, a rota, o ficheiro do `build`, o comando da CLI, a chave de
     config e o separador no site DESAPARECERAM — e não há rasto do nome no
     código-fonte (este ficheiro é o único que o pode dizer);
  2. o que tinha nascido da mesma partição do `faltas.json` (2026-09-15) —
     a wantlist da Coleção, as listas de compra dos decks, as Encomendas — e
     o separador Faltas continuam a responder.

Os testes da parte 2 vieram do `test_top5.py` (apagado com o separador); os
da língua das ofertas, que também lá viviam, foram para o
`test_precos_ingles.py`. Tudo contra cópias descartáveis (`tests.fixture.Vault`)
e um config temporário: nunca o `data/` nem o `riftvault_config.json` reais.
"""

from __future__ import annotations

import contextlib
import importlib
import io
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ["RIFTVAULT_CONFIG"] = str(Path(tempfile.gettempdir()) / "riftvault-nao-existe.json")

from tests.fixture import REPO, Vault  # noqa: E402

# As três escritas do nome que o código usava: o módulo/a chave/a rota, o
# estado do `app.js`, e o rótulo do botão.
NOMES = ("quanto_custa", "quantoCusta", "Quanto custa", "quanto-custa")


class Base(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.close)
        from riftvault import (a_subir, cardmarket, config, decks, faltas,
                               faltas_edicao, locais, metrics, pending, prices)
        for m in (metrics, locais, pending, decks, faltas, cardmarket, a_subir,
                  prices, faltas_edicao):
            importlib.reload(m)
        self.a_subir, self.prices, self.config = a_subir, prices, config
        self.decks, self.faltas, self.pending = decks, faltas, pending
        self.metrics, self.faltas_edicao = metrics, faltas_edicao

    def com_config(self, extra: dict):
        caminho = self.v.root / "config.json"
        caminho.write_text(json.dumps(extra), encoding="utf-8")
        os.environ["RIFTVAULT_CONFIG"] = str(caminho)
        importlib.reload(self.config)
        self.config.load.cache_clear()

        def repor():
            os.environ["RIFTVAULT_CONFIG"] = str(
                Path(tempfile.gettempdir()) / "riftvault-nao-existe.json")
            importlib.reload(self.config)
            self.config.load.cache_clear()

        self.addCleanup(repor)


AZIR = "Legend:\n1 Emperor of the Sands\n\nMainDeck:\n3 Defy\n"


class ComCatalogo(Base):
    """Uma edição com duas cartas, uma delas com 1 cópia, e um deck."""

    def catalogo(self):
        from riftvault import collection
        self.com_config({"sets": {"TST": {"name": "Teste", "order": 1}}})
        con = self.v.connect()
        self.addCleanup(con.close)
        self.v.add_printing(con, "tst-001-100", "TST", 1, "Defy", size=100)
        self.v.add_printing(con, "tst-002-100", "TST", 2, "Emperor of the Sands",
                            card_type="Legend", size=100)
        self.v.rebuild(con)
        for pid, cents in (("tst-001-100", 150), ("tst-002-100", 1000)):
            con.execute("INSERT INTO catalog.price_latest (printing_id, price_cents) "
                        "VALUES (?,?)", (pid, cents))
        collection.adjust(con, "tst-001-100", 1, source="test")
        self.v.write_deck("azir", AZIR)
        self.decks.import_all(con, log=lambda *_: None)
        return con


class TestSaiuTudo(ComCatalogo):
    """1: o módulo, a rota, o build, a CLI, a config e o site."""

    def test_o_modulo_nao_existe(self):
        with self.assertRaises(ModuleNotFoundError):
            importlib.import_module("riftvault.quanto_custa")
        self.assertFalse((REPO / "riftvault" / "quanto_custa.py").exists())

    def test_a_rota_da_404_e_as_outras_respondem(self):
        from riftvault import server
        con = self.catalogo()
        con.close()
        importlib.reload(server)
        app = server.app
        app.testing = True
        with app.test_client() as c:
            self.assertEqual(c.get("/api/quanto_custa.json").status_code, 404)
            # E o `faltas.json` de antes de 2026-09-15 continua a não existir.
            self.assertEqual(c.get("/api/faltas.json").status_code, 404)
            for rota in ("/api/wantlist.json", "/api/compras.json",
                         "/api/faltas_edicao.json", "/api/encomendas.json",
                         "/api/a_mais.json"):
                self.assertEqual(c.get(rota).status_code, 200, rota)

    def test_o_build_nao_escreve_o_ficheiro_e_escreve_os_outros(self):
        from riftvault import build
        con = self.catalogo()
        con.close()
        importlib.reload(build)
        out = self.v.root / "site"
        build._gerar(out, log=lambda *_: None, imagens=False)
        self.assertFalse((out / "api" / "quanto_custa.json").exists(),
                         "o separador foi apagado e o build ainda gera o ficheiro dele")
        for nome in ("api/wantlist.json", "api/compras.json", "api/faltas_edicao.json",
                     "api/a_mais.json", "api/encomendas.json"):
            self.assertTrue((out / nome).exists(), f"falta {nome} no site")

    def test_a_cli_nao_tem_o_comando(self):
        from riftvault import cli
        erro = io.StringIO()
        with contextlib.redirect_stderr(erro), self.assertRaises(SystemExit) as cm:
            cli.main(["quanto-custa"])
        self.assertEqual(cm.exception.code, 2, "o argparse tinha de recusar o comando")
        self.assertIn("invalid choice", erro.getvalue())
        # A ajuda não o lista.
        ajuda = io.StringIO()
        with contextlib.redirect_stdout(ajuda), self.assertRaises(SystemExit):
            cli.main(["--help"])
        self.assertNotIn("quanto-custa", ajuda.getvalue())

    def test_a_config_nao_tem_a_chave(self):
        self.assertNotIn("quanto_custa", self.config.DEFAULTS)
        raw = json.loads((REPO / "riftvault_config.json").read_text(encoding="utf-8"))
        self.assertFalse([k for k in raw if "quanto_custa" in k],
                         "a chave (ou a nota dela) ainda está no riftvault_config.json")
        # Um config antigo que ainda a traga não rebenta: é ignorada.
        self.com_config({"quanto_custa": {"sem_edicoes": ["OGS"], "top_por_raridade": 5}})
        self.assertEqual(self.config.load().get("quanto_custa"),
                         {"sem_edicoes": ["OGS"], "top_por_raridade": 5})

    def test_o_site_nao_tem_o_separador(self):
        web = REPO / "riftvault" / "web"
        html = (web / "index.html").read_text(encoding="utf-8")
        js = (web / "app.js").read_text(encoding="utf-8")
        css = (web / "style.css").read_text(encoding="utf-8")
        self.assertNotIn('data-section="faltas"', html)
        self.assertNotIn('id="falta-tabs"', html)
        self.assertNotIn('<section id="faltas"', html)
        # Os separadores que ficam, pela ordem.
        self.assertEqual(re.findall(r'data-section="([a-z-]+)"', html),
                         ["colecao", "decks", "faltas-edicao", "a-mais", "encomendas"])
        m = re.search(r"const SECCOES = \[(.*?)\];", js)
        self.assertEqual(re.findall(r"'([a-z-]+)'", m.group(1)),
                         ["colecao", "decks", "faltas-edicao", "a-mais", "encomendas"])
        for nome in ("renderQuantoCusta", "loadQuantoCusta", "renderQcTabs", "qcLinha",
                     "'api/quanto_custa.json'", "#falta-tabs", "#falta-body", "qcSet"):
            self.assertNotIn(nome, js, nome)
        for cls in (".qc-", ".mf-"):
            self.assertNotIn(cls, css, cls)

    def test_nao_ha_rasto_do_nome_no_codigo(self):
        # O único ficheiro que pode dizer o nome é este.
        ficheiros = [*(REPO / "riftvault").rglob("*.py"), *(REPO / "riftvault" / "web").iterdir(),
                     REPO / "riftvault_config.json",
                     *(p for p in (REPO / "tests").glob("*.py") if p.name != Path(__file__).name)]
        with_rasto = []
        for f in ficheiros:
            if not f.is_file():
                continue
            texto = f.read_text(encoding="utf-8")
            for nome in NOMES:
                if nome in texto:
                    with_rasto.append(f"{f.relative_to(REPO)}: {nome}")
        self.assertEqual(with_rasto, [])


class TestOQueFicouContinuaAResponder(ComCatalogo):
    """2: a wantlist da Coleção, as faltas dos decks, as Encomendas e o
    separador Faltas não sabiam da tabela e continuam iguais."""

    def test_o_payload_do_separador_antigo_continua_fora(self):
        # O `faltas.payload` era do separador de antes de 2026-09-15; as vistas
        # por raridade eram da manhã desse dia. Nada disto voltou.
        self.assertFalse(hasattr(self.faltas, "payload"))
        for nome in ("por_raridade", "edicoes_quanto_custa", "top_por_raridade"):
            self.assertFalse(hasattr(self.a_subir, nome), f"a_subir.{nome}")

    def test_a_wantlist_da_colecao_responde(self):
        con = self.catalogo()
        w = self.a_subir.wantlist(con, "TST")
        # Falta 2 Defy (tem 1 de 3) e 1 Legend: 3 cópias, 2 × 1,50 + 10,00.
        self.assertEqual((w["lines"], w["copies"], w["cents"]), (2, 3, 2 * 150 + 1000))
        self.assertIn("Defy", w["text"])
        m = self.a_subir.master_faltas(con)
        self.assertEqual((m["copies"], m["cents"]), (3, 2 * 150 + 1000))

    def test_as_faltas_dos_decks_respondem(self):
        con = self.catalogo()
        c = self.faltas.compras(con)
        self.assertEqual(set(c), {"staples", "por_deck", "todos_juntos", "pimp",
                                  "ignored_types", "totals"})
        self.assertEqual((c["totals"]["cards"], c["totals"]["copies"]), (2, 3))
        self.assertEqual(c["por_deck"][0]["copies"], 3)
        self.assertEqual(self.decks.resumo_das_faltas(con)["copies"], 3)
        texto = self.faltas.wantlist(c["por_deck"][0]["by_set"])["text"]
        self.assertIn("2 Defy", texto)

    def test_as_encomendas_respondem_e_descontam(self):
        con = self.catalogo()
        self.pending.encomendar(con, card_key="defy", qty=2, source="test")
        e = self.pending.encomendas(con)
        self.assertEqual(e["totals"]["copies"], 2)
        self.assertEqual(e["falta_totals"]["copies"], 1,
                         "as 2 Defy a caminho fecham essa falta; fica só o Legend")
        w = self.a_subir.wantlist(con, "TST")
        self.assertEqual(w["copies"], 1, "só o Legend")
        self.pending.arrive(con, None, source="test")
        self.assertEqual(self.pending.encomendas(con)["totals"]["copies"], 0)
        self.assertEqual(con.execute("SELECT qty FROM copies WHERE printing_id='tst-001-100'")
                         .fetchone()[0], 3)

    def test_o_separador_faltas_responde_com_os_quatro_blocos(self):
        con = self.catalogo()
        p = self.faltas_edicao.payload(con)
        self.assertEqual([b["id"] for b in p["blocks"]],
                         ["master", "overnumbered", "alt_art", "special"])
        self.assertEqual(p["totals_lists"]["copies"], 3)


class TestFrontend(unittest.TestCase):
    """O `app.js` lê os ficheiros que ficaram e já não pede os que saíram."""

    def setUp(self):
        self.js = (REPO / "riftvault" / "web" / "app.js").read_text(encoding="utf-8")

    def test_pede_os_ficheiros_que_ficaram(self):
        self.assertNotIn("'api/faltas.json'", self.js)
        for url in ("api/wantlist.json", "api/compras.json", "api/faltas_edicao.json",
                    "api/a_mais.json", "api/encomendas.json"):
            self.assertIn(f"'{url}'", self.js, url)

    def test_as_abas_por_deck_vivem_nos_decks(self):
        m = re.search(r"DECK_FALTA_TABS = \[(.*?)\];", self.js, re.S)
        self.assertEqual(re.findall(r"id: '([a-z]+)'", m.group(1)), ["staples", "pordeck", "pimp"])
        self.assertIn("loadDeckFaltas(t.id)", self.js)
        self.assertNotRegex(self.js, r"(?<!DECK_)FALTA_TABS = \[")
        self.assertNotIn("renderMasterFaltas", self.js)


if __name__ == "__main__":
    unittest.main()

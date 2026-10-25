"""Os bugs da revisão completa de 2026-10-25 — um caso por bug.

Os do `app.js` correm as funções VERDADEIRAS no node, com um `state` e um `$`
de brincar (como o `test_mais_ate_ao_alvo.py`); os do Python correm contra
pastas temporárias (`tests/fixture.py`), nunca contra o `data/` a sério.
"""
import json
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.fixture import REPO  # noqa: E402

APP = REPO / "riftvault" / "web" / "app.js"
JS = APP.read_text(encoding="utf-8")


def funcao(nome: str) -> str:
    m = re.search(r"^(?:async )?function " + re.escape(nome) + r"\(", JS, re.M)
    if not m:
        raise AssertionError(f"o app.js não tem a função {nome}")
    i = JS.index("{", m.end())
    nivel = 0
    for j in range(i, len(JS)):
        if JS[j] == "{":
            nivel += 1
        elif JS[j] == "}":
            nivel -= 1
            if nivel == 0:
                return JS[m.start():j + 1]
    raise AssertionError(f"chavetas por fechar em {nome}")


# Um `$` que devolve elementos de brincar, guardados por seletor, e as funções
# que o `abrirSubVista` chama a registar o que lhes pediram.
PRELUDIO = r"""
const chamadas = [];
const els = {};
function $(s) { return els[s] || (els[s] = { innerHTML: '', children: [] }); }
function escapeHTML(s) { return String(s); }
function toast() {}
function savePrefs() {}
const TODAS = 'all';
const state = { prefs: { feSet: 'all' }, index: { sets: [] }, enc: {}, deckId: null };
for (const n of ['renderInicio', 'loadSet', 'renderFeTabs', 'renderFaltasEdicao',
                 'renderAmTabs', 'renderAMais', 'loadVenda', 'loadSelado']) {
  globalThis[n] = (...a) => { chamadas.push(n); return Promise.resolve(); };
}
for (const n of ['carregarInicio', 'loadFaltasEdicao', 'loadDecks', 'loadAMais',
                 'loadEncomendas']) {
  globalThis[n] = (...a) => { chamadas.push(n); return Promise.resolve(); };
}
function abrirDeckOuLista(s) { chamadas.push('abrirDeckOuLista'); }
function feSetValido(s) { return s === 'all'; }
function amSetValido() { return false; }
"""


def correr(corpo: str):
    node = shutil.which("node")
    if not node:
        raise unittest.SkipTest("sem node")
    codigo = PRELUDIO + "\n" + funcao("abrirSubVista") + "\n" + corpo
    r = subprocess.run([node, "-e", codigo], capture_output=True, text=True,
                       encoding="utf-8", timeout=60)
    if r.returncode != 0:
        raise AssertionError(r.stderr)
    return json.loads(r.stdout)


class TestFaltasDepoisDoInicio(unittest.TestCase):
    """Bug 1: o Início traz o `api/faltas_edicao.json` para o cartão dele e não
    o desenha; ao ir às Faltas, o `abrirSubVista` via o payload em memória e
    não desenhava nada — a página abria em branco (visto no site público)."""

    def test_payload_do_inicio_sem_desenho_e_desenhado(self):
        r = correr("""
          state.faltasEdicao = { sets: [], caixas: [] };   // trazido pelo Início
          abrirSubVista('faltas-edicao', '');
          console.log(JSON.stringify(chamadas));""")
        self.assertIn("renderFeTabs", r)
        self.assertIn("renderFaltasEdicao", r)

    def test_ja_desenhado_nao_redesenha(self):
        r = correr("""
          state.faltasEdicao = { sets: [], caixas: [] };
          $('#fe-tabs').children = [1, 2];                 // já desenhado
          abrirSubVista('faltas-edicao', '');
          console.log(JSON.stringify(chamadas));""")
        self.assertEqual(r, [])

    def test_o_inicio_liga_as_caixas(self):
        # sem `feLigarCaixas` as caixas não têm `items` e o `renderFeCaixa`
        # rebenta em `c.items.length`
        self.assertIn("feLigarCaixas()", funcao("carregarInicio"))


class TestDeckDepoisDeUmaEncomenda(unittest.TestCase):
    """Bug 2: uma encomenda (ou «marcar como vendidas») põe `state.decks =
    null` e deixa o `deckId`; ao voltar aos Decks nada se relia e o
    `renderDeck` rebentava em `state.decks.find`."""

    def test_decks_velhos_relem_se(self):
        r = correr("""
          state.deckId = 7; state.decks = null;
          abrirSubVista('decks', '');
          console.log(JSON.stringify(chamadas));""")
        self.assertIn("loadDecks", r)

    def test_decks_em_memoria_nao_relem(self):
        r = correr("""
          state.deckId = 7; state.decks = [{ id: 7, slug: 'x' }];
          abrirSubVista('decks', '');
          console.log(JSON.stringify(chamadas));""")
        self.assertNotIn("loadDecks", r)

    def test_render_deck_e_load_deck_aguentam_decks_nulos(self):
        self.assertIn("(state.decks || []).find", funcao("renderDeck"))
        self.assertIn("await garanteDecks()", funcao("loadDeck"))


if __name__ == "__main__":
    unittest.main()

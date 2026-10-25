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


def correr_js(prelude: str, nomes, corpo: str):
    node = shutil.which("node")
    if not node:
        raise unittest.SkipTest("sem node")
    codigo = prelude + "\n" + "\n".join(funcao(n) for n in nomes) + "\n" + corpo
    r = subprocess.run([node, "-e", codigo], capture_output=True, text=True,
                       encoding="utf-8", timeout=60)
    if r.returncode != 0:
        raise AssertionError(r.stderr)
    return json.loads(r.stdout)


class TestHashPartido(unittest.TestCase):
    """Bug 3: `#colecao%` fazia o `decodeURIComponent` rebentar dentro do
    `lerHash`, e o arranque morria em «Falhou a carregar»."""

    def test_percent_partido_nao_rebenta(self):
        r = correr_js("const location = { hash: '#colecao%' };", ["lerHash"],
                      "console.log(JSON.stringify(lerHash()));")
        self.assertEqual(r["sec"], "colecao%")

    def test_hash_normal_continua(self):
        r = correr_js("const location = { hash: '#faltas-edicao/OGN' };", ["lerHash"],
                      "console.log(JSON.stringify(lerHash()));")
        self.assertEqual(r, {"sec": "faltas-edicao", "sub": "OGN"})


# O `wireKeyboard` com um documento de brincar: a grelha da Coleção tem UM
# tile; os tiles escondidos das Encomendas existem noutro sítio do DOM.
TECLADO = r"""
const escritas = [];
let ouvinte = null;
const tileGrelha = { dataset: { pid: 'ogn-001' }, querySelector: () => null,
                     getBoundingClientRect: () => ({ top: 0, left: 0, width: 10, height: 10 }) };
const tileEnc = { dataset: { pid: 'sfd-099' }, querySelector: () => null,
                  getBoundingClientRect: () => ({ top: 0, left: 20, width: 10, height: 10 }) };
const document = {
  addEventListener: (ev, fn) => { ouvinte = fn; },
  querySelectorAll: (s) => s === '.tile' ? [tileGrelha, tileEnc] : [],
};
const els = { '#sec-colecao': { hidden: false },
              '#grid': { querySelectorAll: (s) => s === '.tile' ? [tileGrelha] : [] } };
function $(s) { return els[s]; }
const state = { focus: -1 };
function setFocus(i) { state.focus = i; }
function adjust(pid, d) { escritas.push([pid, d]); }
function maisTeclaDupla() {}
function tecla(key, extra = {}) {
  const alvo = { matches: (s) => !!extra.campo && s.split(',').map(x => x.trim()).includes(extra.campo) };
  ouvinte({ key, target: alvo, preventDefault() {}, ...extra });
}
"""


class TestTeclado(unittest.TestCase):
    """Bug 4: a seta passava para os tiles escondidos das Encomendas e o `+`
    escrevia numa carta fora do ecrã; Ctrl+`+` (zoom do browser) também
    somava uma cópia; e a seta num `<select>` era engolida."""

    def test_seta_fica_na_grelha(self):
        r = correr_js(TECLADO, ["wireKeyboard"], """
          wireKeyboard();
          tecla('ArrowRight'); tecla('ArrowRight'); tecla('+');
          console.log(JSON.stringify(escritas));""")
        self.assertEqual(r, [["ogn-001", 1]])

    def test_ctrl_mais_e_zoom(self):
        r = correr_js(TECLADO, ["wireKeyboard"], """
          wireKeyboard();
          tecla('ArrowRight'); tecla('+', { ctrlKey: true }); tecla('=', { metaKey: true });
          console.log(JSON.stringify(escritas));""")
        self.assertEqual(r, [])

    def test_select_nao_e_engolido(self):
        r = correr_js(TECLADO, ["wireKeyboard"], """
          wireKeyboard();
          tecla('ArrowDown', { campo: 'select' });
          console.log(JSON.stringify(state.focus));""")
        self.assertEqual(r, -1)


class TestEncomendasForaDeOrdem(unittest.TestCase):
    """Bug 5: OGN e logo SFD — a resposta lenta da OGN desenhava-se debaixo do
    separador SFD e enchia o `state.enc` com os números da OGN."""

    def test_resposta_velha_e_ignorada(self):
        r = correr_js(r"""
          const desenhos = [];
          const resolver = {};
          function getJSON(u) { return new Promise(res => { resolver[u] = res; }); }
          const els = {}; function $(s) { return els[s] || (els[s] = {}); }
          function savePrefs() {} function escreverHash() {} function edicaoAberta() { return null; }
          function renderEncTabs() {} function renderEncomendas() { desenhos.push(state.enc.payload.set); }
          const state = { prefs: { section: 'encomendas' }, index: { sets: [{ id: 'OGN' }, { id: 'SFD' }] },
                          enc: { resumo: {}, ordered: new Map(), qty: new Map() } };
        """, ["loadEncomendas"], """
          (async () => {
            const a = loadEncomendas('OGN'); const b = loadEncomendas('SFD');
            resolver['api/encomendas/SFD.json']({ set: 'SFD', groups: [] }); await b;
            resolver['api/encomendas/OGN.json']({ set: 'OGN', groups: [] }); await a;
            console.log(JSON.stringify({ desenhos, payload: state.enc.payload.set }));
          })();""")
        self.assertEqual(r, {"desenhos": ["SFD"], "payload": "SFD"})


if __name__ == "__main__":
    unittest.main()

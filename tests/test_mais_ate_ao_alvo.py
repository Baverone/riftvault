"""O «+» sai do tile quando a carta chega ao alvo, e volta com um gesto
deliberado (André, 2026-10-15).

*"quero acrescentar mais 1 pormenor / quando chega ao playset, que retires o
"+""* — e, escolhido numa caixa, *"Desaparece, e volta com gesto deliberado"*;
na pergunta de ONDE, *"Também a linha do foil"* (lido como o crachá E a linha
do foil).

É interface: nenhum `.py` mudou. Por isso os testes correm as funções
VERDADEIRAS do `app.js` no node (extraídas pelo nome, não copiadas), com um
`state` de brincar — e o caso das runas lê os alvos do payload do servidor,
para a asserção ser sobre os números que o tile recebe de facto.
"""
from __future__ import annotations

import importlib
import json
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.fixture import REPO, Vault  # noqa: E402

APP = REPO / "riftvault" / "web" / "app.js"
CSS = REPO / "riftvault" / "web" / "style.css"
JS = APP.read_text(encoding="utf-8")


def funcao(nome: str) -> str:
    """O texto inteiro de `function nome(...) { ... }` do `app.js`, pelas
    chavetas (as dos `${}` dos templates também fecham, por isso conta bem)."""
    m = re.search(r"^(?:async )?function " + re.escape(nome) + r"\(", JS, re.M)
    if not m:
        raise AssertionError(f"o app.js não tem a função {nome}")
    i = JS.index("{", m.end())
    nivel = 0
    for j in range(i, len(JS)):
        c = JS[j]
        if c == "{":
            nivel += 1
        elif c == "}":
            nivel -= 1
            if nivel == 0:
                return JS[m.start():j + 1]
    raise AssertionError(f"chavetas por fechar em {nome}")


def constante(nome: str) -> str:
    m = re.search(r"^(?:const|let) " + re.escape(nome) + r"\b[^\n]*", JS, re.M)
    if not m:
        raise AssertionError(f"o app.js não tem {nome}")
    return m.group(0)


FUNCOES = ["escapeHTML", "escapeAttr", "foilLimite", "maisChegou", "maisNormalHTML",
           "maisFoilHTML", "maisDispara", "maisAviso", "wireMaisExtra",
           "maisCliqueExtra", "maisTeclaDupla", "foilLinha", "foilPrecoTxt",
           "foilContamTxt"]

# Um `state` de brincar, um `toast` e um `adjust`/`foilAjustar` que só registam,
# e um relógio controlado (setTimeout/Date.now) para o gesto.
PRELUDIO = r"""
const chamadas = [];
const toasts = [];
let AGORA = 1_000_000;
Date.now = () => AGORA;
const timers = [];
globalThis.setTimeout = (fn, ms) => { const t = { fn, em: AGORA + ms, vivo: true }; timers.push(t); return t; };
globalThis.clearTimeout = (t) => { if (t) t.vivo = false; };
function avancar(ms) {
  AGORA += ms;
  for (const t of timers) if (t.vivo && t.em <= AGORA) { t.vivo = false; t.fn(); }
}
const navigator = {};
function toast(msg) { toasts.push(msg); }
function adjust(pid, d) { chamadas.push(['adjust', pid, d]); }
function foilAjustar(pid, d) { chamadas.push(['foilAjustar', pid, d]); }
const state = {
  meta: new Map(), qty: new Map(), targets: new Map(),
  foil: new Map(), foilAlvo: new Map(), foilOk: new Set(),
  editable: true, index: { foil: { limite: 9999 } },
  precoFoil: new Map(), preco: new Map(),
};
// Um botão de brincar: o que o `closest`, o `dataset` e o `classList` precisam.
function botao(html, pid) {
  const ds = {};
  for (const [, k, v] of html.matchAll(/data-([a-z-]+)="([^"]*)"/g)) ds[k] = v;
  const cls = new Set();
  const tile = { dataset: { pid } };
  return {
    dataset: ds, disabled: /\sdisabled/.test(html),
    classList: { add: c => cls.add(c), remove: c => cls.delete(c), has: c => cls.has(c) },
    closest: (s) => s === '.tile' ? tile : (s === '.step[data-extra]' && ds.extra ? null : null),
  };
}
// Uma `raiz` que guarda os ouvintes, para o `wireMaisExtra` se ligar a ela.
function raiz() {
  const ouv = {};
  return {
    ouv,
    addEventListener: (ev, fn) => { (ouv[ev] = ouv[ev] || []).push(fn); },
    emitir(ev, alvo, extra = {}) {
      const e = { target: { closest: () => alvo }, button: 0, preventDefault() { this.dp = true; }, ...extra };
      if (ev === 'pointerleave') e.target = alvo;
      for (const fn of ouv[ev] || []) fn(e);
      return e;
    },
  };
}
"""


def correr(corpo: str, entrada: dict | None = None):
    node = shutil.which("node")
    if not node:
        raise unittest.SkipTest("sem node")
    codigo = (PRELUDIO + "\n" + constante("MAIS_LONGO_MS") + "\n"
              + constante("maisGestoEm") + "\n" + constante("maisTeclado") + "\n"
              + "\n".join(funcao(n) for n in FUNCOES) + "\n"
              + "const E = " + json.dumps(entrada or {}) + ";\n" + corpo)
    r = subprocess.run([node, "-e", codigo], capture_output=True, text=True,
                       encoding="utf-8", timeout=60)
    if r.returncode != 0:
        raise AssertionError(r.stderr)
    return json.loads(r.stdout)


# ---------------------------------------------------------------------------
# 1. O «+» sai no alvo, e não antes
# ---------------------------------------------------------------------------


class TestOMaisSaiNoAlvo(unittest.TestCase):
    CORPO = r"""
const out = {};
for (const [q, t] of E.casos) {
  state.qty.set('p', q); state.targets.set('p', t);
  out[q + '/' + t] = maisNormalHTML('p');
}
process.stdout.write(JSON.stringify(out));
"""

    def test_o_crachá_antes_no_e_depois_do_alvo(self):
        r = correr(self.CORPO, {"casos": [[0, 3], [2, 3], [3, 3], [4, 3], [0, 1], [1, 1]]})
        for chave in ("0/3", "2/3", "0/1"):
            self.assertNotIn("data-extra", r[chave], f"{chave}: ainda não chegou")
            self.assertRegex(r[chave], r">\+</button>")
        for chave in ("3/3", "4/3", "1/1"):
            self.assertIn('data-extra="1"', r[chave], f"{chave}: chegou ao alvo")
            self.assertIn("+ extra", r[chave])
            self.assertNotRegex(r[chave], r">\+</button>", "o «+» sai, não fica apagado")

    def test_sem_alvo_o_mais_fica_sempre(self):
        r = correr(self.CORPO, {"casos": [[0, 0], [5, 0]]})
        for html in r.values():
            self.assertNotIn("data-extra", html)

    def test_a_linha_do_foil_para_no_alvo_dela(self):
        r = correr(r"""
const out = {};
for (const [f, t] of E.casos) out[f + '/' + t] = maisFoilHTML('p', f, t);
process.stdout.write(JSON.stringify(out));
""", {"casos": [[2, 3], [3, 3], [11, 12], [12, 12]]})
        self.assertNotIn("data-extra", r["2/3"])
        self.assertNotIn("data-extra", r["11/12"])
        self.assertIn('data-extra="1"', r["3/3"])
        self.assertIn('data-extra="1"', r["12/12"])
        self.assertIn('data-foil="1"', r["12/12"], "o mesmo delta do «+» do foil")

    def test_no_limite_do_foil_o_mais_continua_desligado(self):
        r = correr(r"""
state.index.foil.limite = 5;
process.stdout.write(JSON.stringify(maisFoilHTML('p', 5, 3)));
""")
        self.assertIn("disabled", r)


# ---------------------------------------------------------------------------
# 2. As runas: 3 no crachá, 12 no foil — com os alvos que o servidor manda
# ---------------------------------------------------------------------------


class TestAsRunas(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.close)
        from riftvault import collection, config, foil, metrics
        for m in (config, foil, metrics):
            importlib.reload(m)
        config.load.cache_clear()
        self.collection, self.foil, self.metrics = collection, foil, metrics
        con = self.v.connect()
        self.addCleanup(con.close)
        self.v.add_printing(con, "tst-005-100", "TST", 5, "Order Rune",
                            card_type="Rune", rarity="common", size=100)
        self.v.add_printing(con, "tst-003-100", "TST", 3, "Brutalizer",
                            rarity="rare", size=100)
        self.v.rebuild(con)
        self.collection.adjust(con, "tst-005-100", 3, source="test")
        self.foil.ajustar(con, "tst-005-100", 3, source="test")
        self.collection.adjust(con, "tst-003-100", 3, source="test")
        self.con = con

    def tile(self, pid):
        for g in self.metrics.set_payload(self.con, "TST")["groups"]:
            for p in g["printings"]:
                if p["id"] == pid:
                    return p
        self.fail(pid)

    def test_3_normais_e_3_foils_de_uma_runa(self):
        t = self.tile("tst-005-100")
        r = correr(r"""
state.qty.set('r', E.qty); state.targets.set('r', E.target);
const f = maisFoilHTML('r', E.foil, E.foil_target);
process.stdout.write(JSON.stringify([
  maisNormalHTML('r').includes('data-extra'), f.includes('data-extra')]));
""", t)
        # Numa asserção só: o crachá pede 3 (e chegou), o foil pede 12 (e não).
        self.assertEqual(((t["qty"], t["target"]), (t["foil"], t["foil_target"]), r),
                         ((3, 3), (3, 12), [True, False]))

    def test_uma_rara_nao_tem_linha_de_foil_nenhuma(self):
        t = self.tile("tst-003-100")
        self.assertFalse(t["foil_ok"])
        self.assertEqual((t["qty"], t["target"]), (3, 3))
        r = correr(r"""
state.qty.set('x', E.qty); state.targets.set('x', E.target);
// foilOk vazio: é o que o `loadSet` faz com `foil_ok: false`.
process.stdout.write(JSON.stringify([foilLinha('x'), maisNormalHTML('x')]));
""", t)
        self.assertEqual(r[0], "", "sem linha de foil — nem «+», nem «+ extra»")
        self.assertIn("data-extra", r[1], "3 de 3: o crachá chegou ao alvo")


# ---------------------------------------------------------------------------
# 3. O «+ extra» escreve o MESMO que o «+», e só com o gesto
# ---------------------------------------------------------------------------


class TestOGesto(unittest.TestCase):
    def test_carregar_sem_largar_escreve_o_mesmo_que_o_mais(self):
        r = correr(r"""
state.qty.set('p', 3); state.targets.set('p', 3);
state.foil.set('p', 3); state.foilAlvo.set('p', 3);
const extra = botao(maisNormalHTML('p'), 'p');
const fextra = botao(maisFoilHTML('p', 3, 3), 'p');
const R = raiz(); wireMaisExtra(R);
R.emitir('pointerdown', extra); avancar(MAIS_LONGO_MS);
R.emitir('pointerdown', fextra); avancar(MAIS_LONGO_MS);
// O mesmo que o clique no «+» de sempre faz (o `else` do `wireControls`):
const normal = [];
state.qty.set('p', 2);
const mais = botao(maisNormalHTML('p'), 'p');
normal.push(['adjust', 'p', Number(mais.dataset.act)]);
normal.push(['foilAjustar', 'p', Number(botao(maisFoilHTML('p', 2, 3), 'p').dataset.foil)]);
process.stdout.write(JSON.stringify({ chamadas, normal }));
""")
        self.assertEqual(r["chamadas"], r["normal"])
        self.assertEqual(r["chamadas"], [["adjust", "p", 1], ["foilAjustar", "p", 1]])

    def test_um_toque_curto_nao_escreve_e_diz_porque(self):
        r = correr(r"""
state.qty.set('p', 3); state.targets.set('p', 3);
const extra = botao(maisNormalHTML('p'), 'p');
const R = raiz(); wireMaisExtra(R);
R.emitir('pointerdown', extra); avancar(MAIS_LONGO_MS - 200);
R.emitir('pointerup', extra); avancar(1000);
maisCliqueExtra(extra, { detail: 1 });
process.stdout.write(JSON.stringify({ chamadas, toasts }));
""")
        self.assertEqual(r["chamadas"], [])
        self.assertEqual(len(r["toasts"]), 1)
        self.assertIn("sem largar", r["toasts"][0])

    def test_o_clique_de_largar_o_gesto_nao_avisa_nem_escreve_outra_vez(self):
        r = correr(r"""
state.qty.set('p', 3); state.targets.set('p', 3);
const extra = botao(maisNormalHTML('p'), 'p');
const R = raiz(); wireMaisExtra(R);
R.emitir('pointerdown', extra); avancar(MAIS_LONGO_MS);
R.emitir('pointerup', extra);
maisCliqueExtra(extra, { detail: 1 });
process.stdout.write(JSON.stringify({ chamadas, toasts }));
""")
        self.assertEqual(r["chamadas"], [["adjust", "p", 1]], "uma cópia, não duas")
        self.assertEqual(r["toasts"], [])

    def test_arrastar_o_dedo_cancela(self):
        r = correr(r"""
state.qty.set('p', 3); state.targets.set('p', 3);
const extra = botao(maisNormalHTML('p'), 'p');
const R = raiz(); wireMaisExtra(R);
R.emitir('pointerdown', extra); avancar(100);
R.emitir('pointercancel', extra); avancar(1000);
process.stdout.write(JSON.stringify(chamadas));
""")
        self.assertEqual(r, [])

    def test_o_menu_de_contexto_do_telemovel_nao_abre(self):
        r = correr(r"""
state.qty.set('p', 3); state.targets.set('p', 3);
const extra = botao(maisNormalHTML('p'), 'p');
const R = raiz(); wireMaisExtra(R);
process.stdout.write(JSON.stringify(!!R.emitir('contextmenu', extra).dp));
""")
        self.assertTrue(r)

    def test_no_teclado_e_carregar_duas_vezes(self):
        r = correr(r"""
state.qty.set('p', 3); state.targets.set('p', 3);
const extra = botao(maisNormalHTML('p'), 'p');
AGORA += 5000;
maisCliqueExtra(extra, { detail: 0 });       // a primeira só avisa
const depois1 = chamadas.length;
avancar(300);
maisCliqueExtra(extra, { detail: 0 });       // a segunda escreve
avancar(5000);
maisCliqueExtra(extra, { detail: 0 });       // passado o prazo, volta a avisar
process.stdout.write(JSON.stringify({ depois1, chamadas, toasts: toasts.length }));
""")
        self.assertEqual(r["depois1"], 0)
        self.assertEqual(r["chamadas"], [["adjust", "p", 1]])
        self.assertEqual(r["toasts"], 2)


# ---------------------------------------------------------------------------
# 4. O «−» nunca sai, e o resto da ligação
# ---------------------------------------------------------------------------


class TestOMenosEALigacao(unittest.TestCase):
    def test_o_menos_do_cracha_nao_depende_do_alvo(self):
        corpo = funcao("tileHTML")
        self.assertIn('data-act="-1"', corpo)
        self.assertIn("maisNormalHTML(p.id)", corpo)
        self.assertNotIn("-1", funcao("maisNormalHTML"), "o «−» não passa por aqui")

    def test_o_menos_do_foil_fica_com_o_foil_acima_do_alvo(self):
        r = correr(r"""
state.foilOk.add('p'); state.foil.set('p', 5); state.foilAlvo.set('p', 3);
process.stdout.write(JSON.stringify(foilLinha('p')));
""")
        self.assertIn('data-foil="-1"', r)
        self.assertIn('data-extra="1"', r)

    def test_o_refresh_troca_o_mais_quando_o_cracha_muda(self):
        corpo = funcao("refreshTiles")
        self.assertIn("maisNormalHTML(pid)", corpo)
        self.assertIn(".step.minus", corpo)

    def test_o_clique_no_extra_nao_vai_ao_adjust(self):
        ligar = funcao("wireControls")
        i_extra = ligar.index("btn.dataset.extra")
        i_adjust = ligar.index("adjust(tile.dataset.pid")
        self.assertLess(i_extra, i_adjust, "o «+ extra» é apanhado antes do «+»")
        self.assertIn("wireMaisExtra($('#grid'))", ligar)

    def test_a_tecla_mais_no_alvo_e_o_extra(self):
        teclado = funcao("wireKeyboard")
        self.assertIn("maisTeclaDupla", teclado)

    def test_a_ajuda_diz_porque(self):
        self.assertIn("«+ extra»", JS)
        self.assertIn("carrega nele sem largar", JS)

    def test_o_css_enche_no_mesmo_tempo_do_gesto(self):
        css = CSS.read_text(encoding="utf-8")
        self.assertIn(".step.extra", css)
        self.assertIn("-webkit-touch-callout: none", css)
        ms = int(re.search(r"MAIS_LONGO_MS = (\d+)", JS).group(1))
        m = re.search(r"\.step\.extra\.a-segurar \{[^}]*background-position ([\d.]+)s", css)
        self.assertIsNotNone(m)
        self.assertEqual(round(float(m.group(1)) * 1000), ms)

    def test_e_so_o_tile_da_colecao(self):
        """Ele não escolheu o Selado, as cópias próprias, as Encomendas, as
        Faltas nem o contador das runas: os `+` deles não mudam."""
        for marca in ('data-sl="1"', 'data-enc="1"', 'data-fe-d="1"', 'data-vd="1"',
                      'data-runa-delta="1"'):
            linha = next(l for l in JS.splitlines() if marca in l)
            self.assertIn('class="step plus"', linha)
            self.assertNotIn("extra", linha)


# ---------------------------------------------------------------------------
# 5. Nenhum número muda: o servidor aceita a cópia a mais como sempre
# ---------------------------------------------------------------------------


class TestNenhumNumeroMuda(unittest.TestCase):
    def test_uma_copia_a_mais_entra_como_sempre_e_o_a_mais_ve_a(self):
        v = Vault()
        self.addCleanup(v.close)
        from riftvault import a_mais, collection, config, metrics
        for m in (config, metrics, a_mais):
            importlib.reload(m)
        config.load.cache_clear()
        con = v.connect()
        self.addCleanup(con.close)
        v.add_printing(con, "tst-001-100", "TST", 1, "Defy", rarity="common", size=100)
        v.rebuild(con)
        collection.adjust(con, "tst-001-100", 3, source="test")
        res = collection.adjust(con, "tst-001-100", 1, source="test")   # o «+ extra»
        self.assertEqual(res["qty"], 4)
        p = next(p for g in metrics.set_payload(con, "TST")["groups"]
                 for p in g["printings"] if p["id"] == "tst-001-100")
        self.assertEqual((p["qty"], p["target"]), (4, 3))
        itens = a_mais.excedente(con)
        extra = {x["printing_id"]: x["extra"] for x in itens}
        self.assertEqual(extra.get("tst-001-100"), 1)

    def test_nenhum_modulo_python_sabe_do_extra(self):
        for py in (REPO / "riftvault").glob("*.py"):
            texto = py.read_text(encoding="utf-8")
            self.assertNotIn("data-extra", texto, py.name)
            self.assertNotIn("maisChegou", texto, py.name)


if __name__ == "__main__":
    unittest.main()

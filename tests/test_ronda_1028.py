"""Ronda da manhã de 2026-10-28 — só bugs, um caso (ou mais) por achado.

1. O «desfazer» dos locais desfazia um movimento ANTIGO: o filtro que salta as
   linhas de rasto (`(entrou como cópia própria)`, `(saiu da coleção)`) escolhia
   o último movimento entre locais mesmo que depois dele houvesse uma acção mais
   recente sobre a mesma carta — e no caso do `−` na grelha o `mover` rebentava
   em `SemCopias` e o `/api/local/undo` dava 500.
2. O «Chegou» gravava o `arrived_at` (autocommit) ANTES de somar as cópias: se o
   processo morresse entre as duas, a encomenda ficava «chegada» e as cópias
   nunca entravam.
3. O `imgFallback` trocava QUALQUER `<img>` dos contentores ligados pelo
   marcador com o nome — incluindo a miniatura da proposta de marcação, que
   ficava com «sem imagem» sem estilo — e o marcador num tile sem cópias não
   ficava escurecido como a arte.

Tudo contra pastas temporárias (`tests/fixture.py`); o JS corre a função
VERDADEIRA do `app.js` no node.
"""
from __future__ import annotations

import importlib
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.fixture import REPO, SEM_CONFIG, Vault  # noqa: E402
from tests.test_mais_ate_ao_alvo import funcao  # noqa: E402

CSS = (REPO / "riftvault" / "web" / "style.css").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. O desfazer dos locais
# ---------------------------------------------------------------------------


class _Locais(unittest.TestCase):
    def setUp(self):
        os.environ["RIFTVAULT_CONFIG"] = SEM_CONFIG
        self.v = Vault()
        self.addCleanup(self.v.close)
        from riftvault import collection, locais, proprias
        for m in (collection, locais, proprias):
            importlib.reload(m)
        self.collection, self.locais, self.proprias = collection, locais, proprias
        con = self.v.connect()
        self.v.add_printing(con, "tst-002-100", "TST", 2, "Brutalizer", rarity="rare", size=100)
        self.v.add_printing(con, "tst-003-100", "TST", 3, "Defy", rarity="common", size=100)
        self.v.rebuild(con)
        self.con = con

    def binder(self, pid):
        return self.locais.por_local(self.con).get(pid, {}).get(self.locais.BINDER, 0)

    def foto(self):
        return (self.con.execute("SELECT * FROM location_ops ORDER BY id").fetchall(),
                self.con.execute("SELECT * FROM copy_locations ORDER BY printing_id, location")
                .fetchall(),
                self.con.execute("SELECT * FROM copies ORDER BY printing_id").fetchall())

    def rasto_proprio(self, pid):
        # o rasto que o `proprias.ajustar` deixa (um `+` numa cópia própria)
        self.con.execute(
            "INSERT INTO location_ops (ts, printing_id, qty, from_loc, to_loc, source) "
            "VALUES ('2026-10-28T00:00:00Z', ?, 1, ?, 'proprio:x', 'web')",
            (pid, self.proprias.ENTROU))


class TestDesfazerSoOQueEOUltimo(_Locais):
    def test_cenario_A_propria_depois_do_movimento_recusa_sem_mexer(self):
        self.collection.adjust(self.con, "tst-002-100", 3, source="test")
        self.locais.mover(self.con, "tst-002-100", 1, self.locais.COLECAO,
                          self.locais.BINDER, source="test")
        self.rasto_proprio("tst-002-100")
        antes = self.foto()
        with self.assertRaises(self.locais.NaoDesfazivel) as ctx:
            self.locais.undo_last(self.con, source="test")
        self.assertEqual(self.foto(), antes, "a recusa não pode mexer em nada")
        self.assertEqual(self.binder("tst-002-100"), 1)
        msg = str(ctx.exception)
        self.assertIn("tst-002-100", msg)
        self.assertIn("não mexi", msg.lower())

    def test_cenario_B_menos_na_grelha_tirou_do_binder_recusa_e_nao_rebenta(self):
        self.collection.adjust(self.con, "tst-002-100", 1, source="test")
        self.locais.mover(self.con, "tst-002-100", 1, self.locais.COLECAO,
                          self.locais.BINDER, source="test")
        # o `−` na grelha: o total desce a 0 e o `ajustar_ao_total` tira-a do binder
        self.collection.adjust(self.con, "tst-002-100", -1, source="test")
        self.assertEqual(self.binder("tst-002-100"), 0)
        antes = self.foto()
        with self.assertRaises(self.locais.NaoDesfazivel):
            self.locais.undo_last(self.con, source="test")
        self.assertEqual(self.foto(), antes)

    def test_rasto_de_OUTRA_carta_nao_impede_o_desfazer(self):
        self.collection.adjust(self.con, "tst-002-100", 3, source="test")
        self.locais.mover(self.con, "tst-002-100", 1, self.locais.COLECAO,
                          self.locais.BINDER, source="test")
        self.rasto_proprio("tst-003-100")
        res = self.locais.undo_last(self.con, source="test")
        self.assertIsNotNone(res)
        self.assertEqual(self.binder("tst-002-100"), 0)

    def test_o_ultimo_movimento_continua_a_desfazer_se(self):
        self.collection.adjust(self.con, "tst-002-100", 3, source="test")
        self.locais.mover(self.con, "tst-002-100", 2, self.locais.COLECAO,
                          self.locais.BINDER, source="test")
        self.assertIsNotNone(self.locais.undo_last(self.con, source="test"))
        self.assertEqual(self.binder("tst-002-100"), 0)
        self.assertIsNone(self.locais.undo_last(self.con, source="test"))

    def test_movimento_ja_desfeito_depois_nao_bloqueia(self):
        # mover X, mover X outra vez, desfazer o segundo: o primeiro desfaz-se
        self.collection.adjust(self.con, "tst-002-100", 3, source="test")
        self.locais.mover(self.con, "tst-002-100", 1, self.locais.COLECAO,
                          self.locais.BINDER, source="test")
        self.locais.mover(self.con, "tst-002-100", 1, self.locais.COLECAO,
                          self.locais.BINDER, source="test")
        self.locais.undo_last(self.con, source="test")
        self.locais.undo_last(self.con, source="test")
        self.assertEqual(self.binder("tst-002-100"), 0)


class TestRotaDoDesfazerNuncaDa500(_Locais):
    def setUp(self):
        super().setUp()
        from riftvault import rotas_conta, server
        importlib.reload(rotas_conta)
        importlib.reload(server)
        server.app.testing = True
        self.c = server.app.test_client()

    def test_cenario_B_pela_rota(self):
        self.collection.adjust(self.con, "tst-002-100", 1, source="test")
        self.locais.mover(self.con, "tst-002-100", 1, self.locais.COLECAO,
                          self.locais.BINDER, source="test")
        self.collection.adjust(self.con, "tst-002-100", -1, source="test")
        for _ in range(2):   # e não fica a dar 500 de cada vez que se tenta
            r = self.c.post("/api/local/undo", data="{}", content_type="application/json")
            self.assertEqual(r.status_code, 409, r.get_data(as_text=True)[:300])
            self.assertIn("error", r.get_json())

    def test_sem_nada_continua_404(self):
        r = self.c.post("/api/local/undo", data="{}", content_type="application/json")
        self.assertEqual(r.status_code, 404)


# ---------------------------------------------------------------------------
# 2. O «Chegou» numa transacção só
# ---------------------------------------------------------------------------


class _Chegou(unittest.TestCase):
    def setUp(self):
        os.environ["RIFTVAULT_CONFIG"] = SEM_CONFIG
        self.v = Vault()
        self.addCleanup(self.v.close)
        from riftvault import collection, foil, pending
        for m in (collection, foil, pending):
            importlib.reload(m)
        self.collection, self.foil, self.pending = collection, foil, pending
        con = self.v.connect()
        self.v.add_printing(con, "tst-002-100", "TST", 2, "Brutalizer", rarity="rare", size=100)
        self.v.add_printing(con, "tst-003-100", "TST", 3, "Defy", rarity="common", size=100)
        self.v.rebuild(con)
        self.con = con

    def estado(self, pid):
        pe = self.con.execute("SELECT arrived_at FROM pending WHERE printing_id = ?",
                              (pid,)).fetchone()
        c = self.con.execute("SELECT qty, qty_foil FROM copies WHERE printing_id = ?",
                             (pid,)).fetchone()
        return (pe["arrived_at"] if pe else "sem linha",
                (c["qty"], c["qty_foil"]) if c else (0, 0))


class TestChegouNumaTransaccao(_Chegou):
    def test_a_marca_nao_fica_gravada_antes_das_copias(self):
        self.pending.add(self.con, "tst-002-100", 2)
        original = self.collection.adjust
        vista = []
        outra = self.v.connect()
        self.addCleanup(outra.close)

        def espreita(con, *a, **k):
            vista.append(outra.execute(
                "SELECT arrived_at FROM pending WHERE printing_id = 'tst-002-100'")
                .fetchone()["arrived_at"])
            return original(con, *a, **k)

        self.pending.collection.adjust = espreita
        self.addCleanup(setattr, self.pending.collection, "adjust", original)
        self.pending.arrive(self.con, source="test")
        self.assertEqual(vista, [None],
                         "o arrived_at já estava gravado antes de as cópias entrarem")
        chegou, (qty, _) = self.estado("tst-002-100")
        self.assertIsNotNone(chegou)
        self.assertEqual(qty, 2)

    def test_processo_que_morre_a_meio_nao_perde_a_encomenda(self):
        # KeyboardInterrupt não é Exception: é o mais perto de o processo morrer
        # que se faz num teste (o `except Exception` de antes não o apanhava).
        self.pending.add(self.con, "tst-002-100", 2)
        original = self.collection.adjust

        def morre(con, *a, **k):
            raise KeyboardInterrupt

        self.pending.collection.adjust = morre
        self.addCleanup(setattr, self.pending.collection, "adjust", original)
        with self.assertRaises(KeyboardInterrupt):
            self.pending.arrive(self.con, source="test")
        self.assertEqual(self.estado("tst-002-100"), (None, (0, 0)))
        self.assertFalse(self.con.in_transaction)
        self.pending.collection.adjust = original
        self.pending.arrive(self.con, source="test")
        self.assertEqual(self.estado("tst-002-100")[1], (2, 0))

    def test_foil_que_falha_a_meio_volta_tudo_atras(self):
        self.pending.add(self.con, "tst-003-100", 2, foil=True)
        original = self.foil._registar

        def falha(*a, **k):
            raise RuntimeError("disco cheio")

        self.foil._registar = falha
        self.addCleanup(setattr, self.foil, "_registar", original)
        with self.assertRaises(RuntimeError):
            self.pending.arrive(self.con, source="test")
        self.assertEqual(self.estado("tst-003-100"), (None, (0, 0)))
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM foil_ops").fetchone()[0], 0)
        self.foil._registar = original
        self.pending.arrive(self.con, source="test")
        self.assertEqual(self.estado("tst-003-100")[1], (0, 2))

    def test_foil_que_morre_a_meio_nao_perde_a_encomenda(self):
        self.pending.add(self.con, "tst-003-100", 1, foil=True)
        original = self.foil._registar

        def morre(*a, **k):
            raise KeyboardInterrupt

        self.foil._registar = morre
        self.addCleanup(setattr, self.foil, "_registar", original)
        with self.assertRaises(KeyboardInterrupt):
            self.pending.arrive(self.con, source="test")
        self.assertEqual(self.estado("tst-003-100"), (None, (0, 0)))

    def test_duas_linhas_a_segunda_falha_a_primeira_fica(self):
        # uma transacção POR LINHA: uma falha na segunda não desfaz a primeira
        self.pending.add(self.con, "tst-002-100", 1)
        self.pending.add(self.con, "tst-003-100", 1)
        original = self.collection.adjust

        def so_a_segunda(con, ref, *a, **k):
            if ref == "tst-003-100":
                raise RuntimeError("falhou")
            return original(con, ref, *a, **k)

        self.pending.collection.adjust = so_a_segunda
        self.addCleanup(setattr, self.pending.collection, "adjust", original)
        with self.assertRaises(RuntimeError):
            self.pending.arrive(self.con, source="test")
        self.assertEqual(self.estado("tst-002-100")[1], (1, 0))
        self.assertIsNotNone(self.estado("tst-002-100")[0])
        self.assertEqual(self.estado("tst-003-100"), (None, (0, 0)))

    def test_adjust_e_foil_continuam_a_funcionar_sozinhos(self):
        self.assertEqual(self.collection.adjust(self.con, "tst-002-100", 2)["qty"], 2)
        self.assertFalse(self.con.in_transaction)
        self.assertEqual(self.foil.ajustar(self.con, "tst-003-100", 1, validar=False)["foil"], 1)
        self.assertFalse(self.con.in_transaction)


class TestChegouComDoisToquesEmParalelo(_Chegou):
    """A corrida a sério, com o segundo «Chegou» noutra thread e noutra ligação:
    tem de esperar pelo primeiro e não somar outra vez."""

    def test_o_segundo_toque_espera_e_nao_soma(self):
        self.pending.add(self.con, "tst-002-100", 2)
        original = self.collection.adjust
        erros = []

        def segundo():
            try:
                c2 = self.v.connect()   # outra ligação, aberta NESTA thread
                try:
                    self.pending.arrive(c2, source="test")
                finally:
                    c2.close()
            except Exception as exc:   # noqa: BLE001
                erros.append(exc)

        t = threading.Thread(target=segundo)
        arrancou = []

        def com_corrida(con, *a, **k):
            if not arrancou and threading.current_thread() is threading.main_thread():
                arrancou.append(1)
                t.start()
                t.join(1.0)   # dá-lhe tempo: se não houvesse trinco, somava já
            return original(con, *a, **k)

        self.pending.collection.adjust = com_corrida
        self.addCleanup(setattr, self.pending.collection, "adjust", original)
        self.pending.arrive(self.con, source="test")
        t.join(20)
        self.assertFalse(erros, erros)
        self.assertEqual(self.estado("tst-002-100")[1], (2, 0),
                         "a mesma encomenda entrou duas vezes")


# ---------------------------------------------------------------------------
# 3. Imagens falhadas fora dos tiles
# ---------------------------------------------------------------------------

PRELUDIO = r"""
function el(tag, attrs = {}) {
  const n = {
    tagName: tag.toUpperCase(), dataset: {}, attrs: {}, children: [], parent: null,
    textContent: '', className: '', src: '',
    classList: { add(c) { n.className = (n.className + ' ' + c).trim(); } },
    get isConnected() { let p = this; while (p.parent) p = p.parent; return p.raiz === true; },
    setAttribute(k, v) { this.attrs[k] = String(v); },
    getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; },
    appendChild(c) { c.parent = this; this.children.push(c); return c; },
    closest(sel) {
      const cls = sel.replace(/^\./, '');
      for (let p = this; p; p = p.parent)
        if ((' ' + p.className + ' ').includes(' ' + cls + ' ')) return p;
      return null;
    },
    replaceWith(c) {
      const i = this.parent.children.indexOf(this);
      c.parent = this.parent; this.parent.children[i] = c; this.parent = null;
    },
  };
  for (const [k, v] of Object.entries(attrs)) {
    if (k.startsWith('data-')) n.dataset[k.slice(5)] = v; else n.attrs[k] = v;
  }
  return n;
}
const document = { createElement: el };
"""


def correr(corpo: str):
    node = shutil.which("node")
    if not node:
        raise unittest.SkipTest("sem node")
    codigo = PRELUDIO + "\n" + funcao("imgFallback") + "\n" + corpo
    r = subprocess.run([node, "-e", codigo], capture_output=True, text=True,
                       encoding="utf-8", timeout=60)
    if r.returncode != 0:
        raise AssertionError(r.stderr)
    return json.loads(r.stdout)


class TestImagemForaDaArte(unittest.TestCase):
    def test_a_miniatura_da_proposta_nao_vira_marcador(self):
        r = correr("""
          const doc = el('body'); doc.raiz = true;
          const zona = doc.appendChild(el('div')); zona.className = 'propor-zona';
          const lab = zona.appendChild(el('label')); lab.className = 'propor-item';
          const img = lab.appendChild(el('img', { alt: '' }));
          const pn = lab.appendChild(el('span')); pn.className = 'pn';
          imgFallback({ target: img });
          console.log(JSON.stringify(lab.children.map(c => [c.tagName, c.className])));
        """)
        self.assertEqual(r[0][0], "IMG", "a miniatura foi trocada por um marcador sem estilo")
        self.assertIn("img-sem", r[0][1])
        self.assertEqual(r[1], ["SPAN", "pn"])

    def test_dentro_da_arte_continua_o_marcador_com_o_nome(self):
        r = correr("""
          const doc = el('body'); doc.raiz = true;
          const tile = doc.appendChild(el('div')); tile.className = 'tile none';
          const art = tile.appendChild(el('div')); art.className = 'art';
          const img = art.appendChild(el('img', { alt: 'Defy' }));
          imgFallback({ target: img });
          console.log(JSON.stringify(art.children.map(c => [c.tagName, c.className, c.textContent])));
        """)
        self.assertEqual(r[0], ["SPAN", "img-falhou", "Defy"])

    def test_o_css_esconde_a_miniatura_sem_lhe_tirar_o_lugar(self):
        self.assertRegex(CSS, r"\.img-sem\s*\{[^}]*visibility:\s*hidden")

    def test_o_marcador_escurece_quando_nao_tens_a_carta(self):
        # as quatro maneiras de a arte dizer «não tens»: tile da Coleção sem
        # cópias, tile do deck sem cor, que falta ou que está noutro deck
        for sel in (r"\.tile\.none \.art \.img-falhou",
                    r"\.dtile \.art\.sem-cor \.img-falhou",
                    r"\.dtile\.gone \.art \.img-falhou",
                    r"\.dtile\.shared \.art \.img-falhou"):
            self.assertRegex(CSS, sel)
        m = re.search(r"\.tile\.none \.art \.img-falhou[^{]*\{([^}]*)\}", CSS)
        self.assertRegex(m.group(1), r"opacity")


if __name__ == "__main__":
    unittest.main()

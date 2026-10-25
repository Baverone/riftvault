"""A imagem que falha nas DUAS fontes dá lugar a um marcador com o nome
(2026-10-25).

O `imgFallback` do `app.js` trocava a imagem local pelo CDN (ou o contrário no
site publicado) e, se a segunda também falhasse, deixava um ícone partido sem
nome — num tile só com o crachá não se sabia que carta era. Agora, esgotadas
as fontes, a `<img>` é trocada por um `<span class="img-falhou">` com o nome, e
só ela: o crachá, o preço, os botões e o tile ficam onde estavam.

Os testes correm a função VERDADEIRA do `app.js` no node (extraída pelo nome),
com um DOM de brincar.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.fixture import REPO  # noqa: E402
from tests.test_mais_ate_ao_alvo import funcao  # noqa: E402

CSS = (REPO / "riftvault" / "web" / "style.css").read_text(encoding="utf-8")

# Um DOM mínimo: uma `.art` com a `<img>` e os irmãos (crachá, preço), dentro de
# um tile com um botão. `replaceWith` troca o filho no pai, como o browser.
PRELUDIO = r"""
function el(tag, attrs = {}) {
  const n = {
    tagName: tag.toUpperCase(), dataset: {}, attrs: {}, children: [], parent: null,
    textContent: '', className: '', src: '',
    get isConnected() { let p = this; while (p.parent) p = p.parent; return p.raiz === true; },
    setAttribute(k, v) { this.attrs[k] = String(v); },
    getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; },
    appendChild(c) { c.parent = this; this.children.push(c); return c; },
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
function montar(imgAttrs) {
  const doc = el('body'); doc.raiz = true;
  const tile = doc.appendChild(el('div'));
  tile.className = 'tile';
  const art = tile.appendChild(el('div')); art.className = 'art';
  const img = art.appendChild(el('img', imgAttrs));
  img.src = imgAttrs.src || '';
  const badge = art.appendChild(el('span')); badge.className = 'badge'; badge.textContent = '2/3';
  const btn = tile.appendChild(el('button')); btn.className = 'step';
  return { doc, tile, art, img, badge, btn };
}
function resumo(d) {
  return {
    filhos: d.art.children.map(c => ({ tag: c.tagName, cls: c.className,
      texto: c.textContent, src: c.src, aria: c.getAttribute('aria-label'),
      role: c.getAttribute('role'), fb: c.dataset.fallback ?? null })),
    badge_no_sitio: d.art.children.includes(d.badge),
    botao_no_sitio: d.tile.children.includes(d.btn),
  };
}
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


class TestImgFallback(unittest.TestCase):
    def test_primeira_falha_passa_para_a_alternativa_valida(self):
        r = correr("""
          const d = montar({ src: '/img/a.webp', alt: 'Ahri, Confident',
                             'data-fallback': 'https://cdn/a.webp' });
          imgFallback({ target: d.img });
          console.log(JSON.stringify(resumo(d)));
        """)
        img = r["filhos"][0]
        self.assertEqual(img["tag"], "IMG", "com alternativa a imagem fica")
        self.assertEqual(img["src"], "https://cdn/a.webp")
        self.assertIsNone(img["fb"], "a alternativa gasta-se: não se tenta duas vezes")
        self.assertTrue(r["badge_no_sitio"] and r["botao_no_sitio"])

    def test_dupla_falha_poe_o_marcador_com_o_nome(self):
        r = correr("""
          const d = montar({ src: '/img/a.webp', alt: 'Ahri, Confident',
                             'data-fallback': 'https://cdn/a.webp' });
          imgFallback({ target: d.img });   // a local falhou
          imgFallback({ target: d.img });   // o CDN também
          console.log(JSON.stringify(resumo(d)));
        """)
        marca = r["filhos"][0]
        self.assertEqual(marca["tag"], "SPAN")
        self.assertEqual(marca["cls"], "img-falhou")
        self.assertEqual(marca["texto"], "Ahri, Confident")
        self.assertEqual(marca["role"], "img")
        self.assertIn("Ahri, Confident", marca["aria"])
        # A interação fica: só a <img> foi trocada.
        self.assertEqual(len(r["filhos"]), 2)
        self.assertEqual(r["filhos"][1]["cls"], "badge")
        self.assertTrue(r["badge_no_sitio"] and r["botao_no_sitio"])

    def test_sem_alternativa_uma_falha_basta(self):
        r = correr("""
          const d = montar({ src: '/img/a.webp', alt: 'Defy' });
          imgFallback({ target: d.img });
          console.log(JSON.stringify(resumo(d)));
        """)
        self.assertEqual(r["filhos"][0]["cls"], "img-falhou")
        self.assertEqual(r["filhos"][0]["texto"], "Defy")

    def test_sem_nome_diz_sem_imagem_e_o_nome_e_texto_nao_html(self):
        r = correr("""
          const a = montar({ src: 'x' });
          imgFallback({ target: a.img });
          const b = montar({ src: 'x', alt: '<b>Mau</b>' });
          imgFallback({ target: b.img });
          console.log(JSON.stringify([resumo(a), resumo(b)]))
        """)
        self.assertEqual(r[0]["filhos"][0]["texto"], "sem imagem")
        # textContent, não innerHTML: o nome não se interpreta.
        self.assertEqual(r[1]["filhos"][0]["texto"], "<b>Mau</b>")

    def test_ignora_o_que_nao_e_imagem_e_a_imagem_ja_fora_da_pagina(self):
        r = correr("""
          imgFallback({ target: { tagName: 'SCRIPT', dataset: {} } });
          imgFallback({ target: null });
          const d = montar({ src: 'x', alt: 'Defy' });
          d.art.children.splice(0, 1); d.img.parent = null;   // tirada do DOM
          imgFallback({ target: d.img });
          console.log(JSON.stringify(resumo(d)));
        """)
        self.assertEqual([f["cls"] for f in r["filhos"]], ["badge"])

    def test_o_css_desenha_o_marcador_dentro_da_arte(self):
        self.assertIn(".art .img-falhou", CSS)


if __name__ == "__main__":
    unittest.main()

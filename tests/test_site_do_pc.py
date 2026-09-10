"""O site é gerado no PC, e só se reescreve quando muda mesmo (2026-09-10).

A 10/09 o `riftscribe.gg` esteve em baixo a tarde inteira e todas as builds do
Pages morreram no passo «Descarregar o catálogo» — o site ficou parado na
versão da manhã. A geração passou para o PC e a pasta `site/` passou a ir no
Git; o workflow só a publica.

O que estes testes fixam:

  1. o `--se-mudou` NÃO reescreve o site quando nada mudou — senão a tarefa que
     corre de 30 em 30 minutos commitava e gastava uma build do Pages a cada
     corrida, para sempre. O relógio (`generated_at`) muda a cada geração e não
     é conteúdo;
  2. mas reescreve mesmo quando uma cópia muda — que é a única coisa que
     interessa;
  3. o site gerado tem tudo o que o Pages precisa de servir sem rede nenhuma.
"""

from __future__ import annotations

import importlib
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.fixture import Vault, catalogo_simples


class TestSiteDoPC(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        catalogo_simples(self.v)
        self.addCleanup(self.v.close)
        self.out = self.v.root / "site"

    def _build(self, **kw):
        from riftvault import build, decks, metrics, server
        for m in (metrics, decks, build, server):
            importlib.reload(m)
        return build.build(self.out, log=lambda *_: None, **kw)

    def _assinatura(self):
        """Nome -> conteúdo dos ficheiros do site, para ver o que foi tocado."""
        return {p.relative_to(self.out).as_posix(): p.read_bytes()
                for p in self.out.rglob("*") if p.is_file()}

    # -- 1. sem mudanças, não se mexe -------------------------------------
    def test_se_mudou_nao_reescreve_quando_o_conteudo_e_o_mesmo(self):
        self._build()
        antes = self._assinatura()
        res = self._build(so_se_mudou=True)
        self.assertFalse(res["mudou"], "disse que mudou sem nada ter mudado")
        self.assertEqual(antes, self._assinatura(),
                         "reescreveu o site sem conteúdo novo — isto dava uma "
                         "build do Pages de 30 em 30 minutos")

    def test_a_pasta_de_prova_nao_fica_para_tras(self):
        self._build()
        self._build(so_se_mudou=True)
        self.assertFalse((self.v.root / "site-prova").exists(),
                         "a pasta de prova ficou no disco — ia parar ao git status")

    # -- 2. com uma cópia a mais, reescreve -------------------------------
    def test_uma_copia_a_mais_reescreve_o_site(self):
        from riftvault import collection, db
        self._build()
        antes = self._assinatura()

        con = db.connect()
        collection.adjust(con, "tst-002-100", 1, source="test")
        con.close()

        res = self._build(so_se_mudou=True)
        self.assertTrue(res["mudou"], "a colecção mudou e o site não foi refeito")
        self.assertNotEqual(antes, self._assinatura(),
                            "o site ficou byte a byte igual depois de a colecção mudar")
        payload = json.loads((self.out / "api" / "set" / "TST.json").read_text(
            encoding="utf-8"))
        qtds = {p["id"]: p["qty"] for g in payload["groups"] for p in g["printings"]}
        self.assertEqual(qtds["tst-002-100"], 4)

    # -- 3. o Pages consegue servir isto sozinho --------------------------
    def test_o_site_traz_tudo_o_que_o_pages_serve(self):
        self._build()
        for nome in ("index.html", "app.js", "style.css", ".nojekyll",
                     "api/index.json", "api/set/TST.json", "api/decks.json",
                     "api/faltas.json", "api/venda.json"):
            self.assertTrue((self.out / nome).exists(), f"falta {nome} no site")
        index = json.loads((self.out / "api" / "index.json").read_text(
            encoding="utf-8"))
        self.assertFalse(index["editable"],
                         "o site publicado não pode trazer os +/- ligados")
        self.assertTrue(index.get("generated_at"),
                        "sem `generated_at` ninguém consegue verificar de fora "
                        "se o site publicado é o que foi gerado no PC")

    def test_um_payload_orfao_desaparece(self):
        """Uma edição que saia do catálogo tem de sair do site.

        E não é só arrumação: um ficheiro que estivesse de um lado e não do
        outro fazia o `--se-mudou` ver diferença em todas as corridas.
        """
        self._build()
        orfao = self.out / "api" / "set" / "ZZZ.json"
        orfao.write_text("{}", encoding="utf-8")
        self.assertTrue(self._build(so_se_mudou=True)["mudou"])
        self.assertFalse(orfao.exists(), "o payload órfão ficou no site")
        self.assertFalse(self._build(so_se_mudou=True)["mudou"],
                         "depois de limpo, devia voltar a estar em dia")


if __name__ == "__main__":
    unittest.main()

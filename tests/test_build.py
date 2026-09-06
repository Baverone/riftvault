"""O build tem de reler as listas ANTES de gerar os payloads da Coleção.

O `in_decks` de cada tile ("2× Ornn · 1 no binder") sai da alocação, que lê as
tabelas do vault.db. Como o vault.db vem do Git com os decks de quando o André
correu o riftvault em casa, gerar a Coleção antes do `import_all` publicava um
site em que a secção Decks já não tinha a carta e a Coleção ainda dizia que ela
estava lá — as duas metades da mesma página a discordar.
"""

from __future__ import annotations

import importlib
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.fixture import Vault, catalogo_simples


DECK = """Legend:
1 Emperor of the Sands

MainDeck:
3 Defy
3 Brutalizer
"""

DECK_SEM_DEFY = """Legend:
1 Emperor of the Sands

MainDeck:
3 Brutalizer
"""


class TestBuildReleDecks(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        catalogo_simples(self.v)
        self.addCleanup(self.v.close)

    def _build(self):
        from riftvault import build, decks, metrics, server
        for m in (metrics, decks, build, server):
            importlib.reload(m)
        out = self.v.root / "site"
        build.build(out, log=lambda *_: None)
        return out

    def _in_decks(self, out: Path, printing_id: str):
        payload = json.loads((out / "api" / "set" / "TST.json").read_text(encoding="utf-8"))
        for g in payload["groups"]:
            for p in g["printings"]:
                if p["id"] == printing_id:
                    return p["in_decks"]
        self.fail(f"{printing_id} não apareceu no payload")

    def test_coleccao_e_decks_concordam_depois_de_editar_a_lista(self):
        # Duas publicações com a lista completa: a segunda já parte de um
        # vault.db com os decks lá dentro, como o que vem do Git.
        self.v.write_deck("azir", DECK)
        self._build()
        out = self._build()
        self.assertTrue(self._in_decks(out, "tst-001-100"),
                        "o Defy devia aparecer alocado ao deck")

        # O André tira o Defy da lista e volta a publicar.
        self.v.write_deck("azir", DECK_SEM_DEFY)
        out = self._build()

        deck = json.loads((out / "api" / "deck" / "1.json").read_text(encoding="utf-8"))
        nomes = {c["name"] for s in deck["sections"] for c in s["cards"]}
        self.assertNotIn("Defy", nomes, "o payload do deck já não devia ter o Defy")

        self.assertEqual(
            self._in_decks(out, "tst-001-100"), [],
            "a Coleção continuou a dizer que o Defy está num deck que já não o usa")


if __name__ == "__main__":
    unittest.main()

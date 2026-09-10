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
        """A Coleção diz onde a cópia ESTÁ, e a lista do deck é outra coisa.

        Desde 2026-09-10 o `in_decks` do tile lê-se da `copy_locations` — é um
        facto que o André marcou —, já não é deduzido da lista do deck. Por
        isso a cópia continua no deck depois de a lista mudar: ela está mesmo
        lá dentro. O que o build tem de garantir é que RELÊ as listas antes de
        gerar os payloads da Coleção, senão a secção Decks e a Coleção do MESMO
        site falavam de listas diferentes.
        """
        from riftvault import db, locais
        self.v.write_deck("azir", DECK)
        self._build()

        con = db.connect()
        locais.mover(con, "tst-001-100", 3, locais.COLECAO,
                     locais.deck_local("azir"), source="test")
        con.close()

        out = self._build()
        self.assertEqual([x["qty"] for x in self._in_decks(out, "tst-001-100")], [3],
                         "o Defy devia aparecer marcado no deck")

        # O André tira o Defy da lista e volta a publicar.
        self.v.write_deck("azir", DECK_SEM_DEFY)
        out = self._build()

        deck = json.loads((out / "api" / "deck" / "1.json").read_text(encoding="utf-8"))
        nomes = {c["name"] for s in deck["sections"] for c in s["cards"]}
        self.assertNotIn("Defy", nomes, "o payload do deck já não devia ter o Defy")

        # A cópia continua fisicamente na caixa do deck — e o deck diz que tem
        # 3 cópias a mais que já não pede. É o `extra`.
        self.assertEqual([x["qty"] for x in self._in_decks(out, "tst-001-100")], [3])
        self.assertEqual(deck["locais"]["extra"], 3)


if __name__ == "__main__":
    unittest.main()

"""O sync não pode apagar uma edição só porque a API veio vazia.

A API é a única fonte do catálogo, mas uma resposta vazia com HTTP 200 é uma
falha dela, não uma edição sem cartas. Se o sync apagasse as impressões, o
`build` a seguir publicava um site sem essa edição e sem dar erro — e as barras
de progresso e o master set passavam a medir outra coisa.

Sem rede: o cliente da RiftScribe é substituído por funções que devolvem o que
o teste quiser.
"""

from __future__ import annotations

import importlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.fixture import Vault


def carta(printing_id, cn, name, set_id="TST"):
    return {"id": printing_id, "set_id": set_id, "collector_number": cn,
            "variant": "", "public_code": f"{set_id}-{cn:03d}", "name": name,
            "rarity": "common", "faction": "order", "domains": ["Order"],
            "type": "Unit", "orientation": "portrait", "stats": {}, "image": None,
            "image_thumb": {}}


class TestSyncVazio(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.close)
        from riftvault import catalog, riftscribe
        importlib.reload(catalog)
        self.catalog, self.riftscribe = catalog, riftscribe

        self._orig = (riftscribe.list_sets, riftscribe.iter_cards)
        self.addCleanup(self._repor)
        riftscribe.list_sets = lambda: ["TST"]

    def _repor(self):
        self.riftscribe.list_sets, self.riftscribe.iter_cards = self._orig

    def _paginas(self, entradas):
        self.riftscribe.iter_cards = lambda set_id, delay=0: iter(entradas)

    def test_edicao_vazia_nao_apaga_o_catalogo_e_da_erro(self):
        self._paginas([carta("tst-001-100", 1, "Defy"),
                       carta("tst-002-100", 2, "Brutalizer")])
        res = self.catalog.sync(delay=0.0, log=lambda *_: None)
        self.assertEqual(res["total"], 2)
        self.assertEqual(res["sets_vazias"], [])

        # Agora a API responde 200 sem uma única entrada.
        self._paginas([])
        res = self.catalog.sync(delay=0.0, log=lambda *_: None)
        self.assertEqual(res["sets_vazias"], ["TST"],
                         "a edição vazia tinha de ser assinalada")

        con = self.v.connect()
        n = con.execute("SELECT COUNT(*) FROM catalog.printings "
                        "WHERE set_id='TST'").fetchone()[0]
        con.close()
        self.assertEqual(n, 2, "o catálogo da edição não podia ter sido apagado")

    def test_impressao_que_saiu_da_api_continua_a_sair_do_catalogo(self):
        """A limpeza normal tem de continuar a funcionar: só o caso vazio muda."""
        self._paginas([carta("tst-001-100", 1, "Defy"),
                       carta("tst-002-100", 2, "Brutalizer")])
        self.catalog.sync(delay=0.0, log=lambda *_: None)

        self._paginas([carta("tst-001-100", 1, "Defy")])
        res = self.catalog.sync(delay=0.0, log=lambda *_: None)
        self.assertEqual(res["sets_vazias"], [])

        con = self.v.connect()
        ids = [r[0] for r in con.execute(
            "SELECT printing_id FROM catalog.printings WHERE set_id='TST'")]
        con.close()
        self.assertEqual(ids, ["tst-001-100"])


if __name__ == "__main__":
    unittest.main()

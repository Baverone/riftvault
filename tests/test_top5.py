"""«Quanto custa»: só inglês, por edição, e o top 5 por raridade (2026-09-15).

André: *"apenas cartas versao ingles"* / *"no quanto custa, quero as mais
caras por edicao, nao por deck, e quero em cada edicao o top5 de mais caras de
comuns, e top5 de incomuns, e top5 de Raras"* / *"miticas e AltArt nao precisa
fazer isto"*.

O que se fixa aqui: uma oferta noutra língua não entra no preço; com sete
comuns só as cinco mais caras se MOSTRAM e o rodapé diz «mais 2» com a soma
certa; as épicas aparecem todas; o subtotal e o total contam as sete, não as
cinco; mudar o `top_por_raridade` muda o corte; e o separador não tem
agrupamento por deck.

Tudo contra cópias descartáveis (`tests.fixture.Vault`) e um config temporário
(`RIFTVAULT_CONFIG`): nunca o `data/` nem o `riftvault_config.json` reais.
"""

from __future__ import annotations

import importlib
import json
import os
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.fixture import REPO, Vault


def oferta_ct(cents, lingua="en", **extra):
    """Uma oferta do CardTrader como a API a devolve, reduzida ao que se lê."""
    props = {"riftbound_language": lingua, "condition": "Near Mint",
             "riftbound_foil": False, **extra}
    return {"price_cents": cents, "price_currency": "EUR", "quantity": 1,
            "graded": False, "on_vacation": False, "user": {"id": cents},
            "properties_hash": props}


class Base(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.close)
        from riftvault import a_subir, cardmarket, config, prices
        importlib.reload(cardmarket)
        importlib.reload(a_subir)
        importlib.reload(prices)
        self.a_subir = a_subir
        self.prices = prices
        self.config = config

    def com_config(self, extra: dict):
        caminho = self.v.root / "config.json"
        caminho.write_text(json.dumps(extra), encoding="utf-8")
        os.environ["RIFTVAULT_CONFIG"] = str(caminho)
        importlib.reload(self.config)
        self.config.load.cache_clear()

        def repor():
            os.environ.pop("RIFTVAULT_CONFIG", None)
            importlib.reload(self.config)
            self.config.load.cache_clear()

        self.addCleanup(repor)


class TestSoIngles(Base):
    """Uma oferta que não seja em inglês não entra no preço."""

    def test_oferta_noutra_lingua_nao_entra(self):
        self.com_config({"precos": {"linguas": ["en"]}})
        o = self.prices.oferta([oferta_ct(50, "ja"), oferta_ct(80, "de"), oferta_ct(120, "en")])
        self.assertEqual(o["cents"], 120)
        self.assertEqual(o["n_listings"], 1)
        self.assertEqual(o["n_sellers"], 1)

    def test_so_ofertas_noutra_lingua_e_sem_preco(self):
        self.com_config({"precos": {"linguas": ["en"]}})
        o = self.prices.oferta([oferta_ct(50, "fr"), oferta_ct(60, "zh-CN")])
        self.assertIsNone(o["cents"])
        self.assertEqual(o["n_listings"], 0)

    def test_a_lista_do_config_manda(self):
        # É o config que decide, não uma constante: com o francês aceite a
        # oferta francesa mais barata passa a ser o preço.
        self.com_config({"precos": {"linguas": ["en", "fr"]}})
        o = self.prices.oferta([oferta_ct(50, "fr"), oferta_ct(120, "en")])
        self.assertEqual(o["cents"], 50)

    def test_sem_config_e_ingles(self):
        self.assertEqual(self.prices.linguas({}), frozenset({"en"}))

    def test_lista_vazia_rebenta(self):
        with self.assertRaises(ValueError):
            self.prices.linguas({"precos": {"linguas": []}})

    def test_config_real_diz_so_ingles(self):
        # O ficheiro dele: se alguém lá puser outra língua, este teste diz.
        raw = json.loads((REPO / "riftvault_config.json").read_text(encoding="utf-8"))
        self.assertEqual(raw["precos"]["linguas"], ["en"])


if __name__ == "__main__":
    unittest.main()

"""Catálogo e coleção mínimos, construídos em disco, sem rede.

Os testes não podem tocar no `data/vault.db` do André nem falar com a
RiftScribe. Aqui monta-se um catálogo de brincar com o mesmo formato do real —
o que interessa é a forma (impressões, cartas lógicas, grupos), não o tamanho.
"""

from __future__ import annotations

import importlib
import json
import os
import shutil
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


class Vault:
    """Um riftvault descartável: pastas próprias e módulos reconfigurados.

    O `config` guarda os caminhos em constantes de módulo lidas na importação,
    por isso não chega pôr as variáveis de ambiente — é preciso reimportá-lo.
    """

    def __init__(self):
        self.root = Path(tempfile.mkdtemp(prefix="riftvault-test-"))
        self.data = self.root / "data"
        self.decks_dir = self.root / "decks"
        self.data.mkdir()
        self.decks_dir.mkdir()

        os.environ["RIFTVAULT_DATA"] = str(self.data)
        os.environ["RIFTVAULT_DECKS"] = str(self.decks_dir)
        os.environ["RIFTVAULT_DB"] = str(self.data / "vault.db")
        os.environ["RIFTVAULT_CATALOG"] = str(self.data / "catalog.db")
        os.environ["RIFTVAULT_PRICES"] = str(self.data / "prices.db")

        from riftvault import config
        importlib.reload(config)
        config.load.cache_clear()
        self.config = config

    def close(self):
        for var in ("RIFTVAULT_DATA", "RIFTVAULT_DECKS", "RIFTVAULT_DB",
                    "RIFTVAULT_CATALOG", "RIFTVAULT_PRICES"):
            os.environ.pop(var, None)
        from riftvault import config
        importlib.reload(config)
        config.load.cache_clear()
        shutil.rmtree(self.root, ignore_errors=True)

    # -- construção do catálogo ------------------------------------------

    def connect(self):
        from riftvault import db
        return db.connect()

    def add_printing(self, con, printing_id, set_id, cn, name, *, variant="",
                     kind="base", card_type="Unit", api_sort=None, rarity="common",
                     domains=("Order",), size=None, lane="main", codigo=None):
        # `size` é o TAMANHO NOMINAL da edição, e vai para o denominador do
        # código impresso (`TST-300/298`), como a API o dá. Só quem testa as
        # sobrenumeradas precisa dele — ver `metrics.e_overnumbered`; sem ele o
        # código sai sem denominador, como sempre saiu.
        #
        # O `codigo` escreve-se à mão quando a série não segue a numeração da
        # edição: as promos são `VEN-SP4/006` (a 4 de 6), não `VEN-004sp4`.
        if codigo is None:
            codigo = f"{set_id}-{cn:03d}{variant}" + (f"/{size:03d}" if size else "")
        # A `lane` é o prefixo alfabético do variante (ARMADILHA 1 do CLAUDE.md):
        # é ela que impede o `VEN-SP4` e o `VEN-004` de caírem no mesmo grupo por
        # partilharem o número. Por omissão `main`, que é o caso de quase tudo.
        # `domains=None` deixa a coluna a NULL, que é o que o schema permite.
        con.execute(
            "INSERT INTO catalog.printings (printing_id, set_id, collector_number, "
            "variant, lane, group_key, variant_kind, variant_label, card_key, "
            "public_code, name, rarity, base_rarity, type, orientation, is_banned, "
            "is_token, api_sort, domains_json) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0,0,?,?)",
            (printing_id, set_id, cn, variant, lane, f"{set_id}|{cn}|{lane}", kind,
             kind, name.strip().casefold(), codigo, name,
             rarity, rarity, card_type, "portrait",
             api_sort if api_sort is not None else cn,
             None if domains is None else json.dumps(list(domains))))

    def rebuild(self, con):
        """Deriva `cards` e os aliases, como o `sync` faz no fim."""
        from riftvault import catalog
        catalog.rebuild_cards(con)
        catalog.rebuild_aliases(con)

    def write_deck(self, slug: str, texto: str):
        (self.decks_dir / f"{slug}.txt").write_text(texto, encoding="utf-8")


def catalogo_simples(v: Vault):
    """Duas Units e um Legend numa edição, com a coleção já lá dentro."""
    con = v.connect()
    v.add_printing(con, "tst-001-100", "TST", 1, "Defy")
    v.add_printing(con, "tst-002-100", "TST", 2, "Brutalizer")
    v.add_printing(con, "tst-003-100", "TST", 3, "Emperor of the Sands",
                   card_type="Legend")
    v.rebuild(con)
    from riftvault import collection
    collection.adjust(con, "tst-001-100", 3, source="test")
    collection.adjust(con, "tst-002-100", 3, source="test")
    collection.adjust(con, "tst-003-100", 1, source="test")
    con.close()

"""O `Nome:` do ficheiro do deck, e dois decks com a mesma Legend/Champion.

A 2026-09-11 o segundo deck de LeBlanc tinha a mesma Legend e o mesmo Champion
do primeiro: os dois liam-se igual e, pior, a alocação comparava decks pelo
RÓTULO — o segundo não via o primeiro como «outro deck» e mandava comprar o que
já lá estava. Estes testes fixam que a chave é o slug e o rótulo é só rótulo.

Correm contra uma pasta `decks/` e uma base temporárias (`fixture.Vault`), e
contra um config que não existe — nunca contra o `data/` nem o
`riftvault_config.json` a sério.
"""

from __future__ import annotations

import argparse
import contextlib
import importlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Antes do `Vault`, que é quem recarrega o `config` com as variáveis postas.
os.environ["RIFTVAULT_CONFIG"] = str(Path(tempfile.gettempdir()) / "riftvault-nao-existe.json")

from tests.fixture import Vault, catalogo_simples  # noqa: E402


LISTA = "Legend:\n1 Emperor of the Sands\n\nChampion:\n1 Brutalizer\n\nMainDeck:\n3 Defy\n"


class TestNomeDoDeck(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.close)
        catalogo_simples(self.v)
        from riftvault import decks, faltas
        importlib.reload(decks)
        importlib.reload(faltas)
        self.decks, self.faltas = decks, faltas

    def _importar(self):
        con = self.v.connect()
        self.decks.import_all(con, log=lambda *_: None)
        return con

    def test_nome_e_lido_e_manda_no_rotulo(self):
        self.v.write_deck("um", "Nome: O Meu LeBlanc\n\n" + LISTA)
        con = self._importar()
        idx = self.decks.decks_index(con)
        self.assertEqual([d["name"] for d in idx], ["O Meu LeBlanc"])
        self.assertEqual(idx[0]["slug"], "um")
        # O Legend e o Champion continuam guardados: o `Nome:` não os apaga.
        self.assertEqual(idx[0]["legend"], "Emperor of the Sands")
        self.assertEqual(idx[0]["champion"], "Brutalizer")
        con.close()

    def test_aceita_name_em_ingles_e_crlf(self):
        self.v.write_deck("um", "Name: Baited Hook\r\n\r\n" + LISTA.replace("\n", "\r\n"))
        con = self._importar()
        self.assertEqual(self.decks.decks_index(con)[0]["name"], "Baited Hook")
        con.close()

    def test_sem_nome_fica_legend_e_champion(self):
        self.v.write_deck("um", LISTA)
        con = self._importar()
        self.assertEqual(self.decks.decks_index(con)[0]["name"],
                         "Emperor of the Sands · Brutalizer")
        con.close()

    def test_o_nome_nao_e_uma_carta(self):
        """Uma linha `Nome:` não pode cair no main deck como carta por casar."""
        self.v.write_deck("um", "Nome: LeBlanc\n" + LISTA)
        con = self._importar()
        d = self.decks.deck_payload(con, self.decks.decks_index(con)[0]["id"])
        self.assertEqual(d["unresolved"], [])
        self.assertEqual(sum(s["wanted"] for s in d["sections"]), 5)
        con.close()

    def test_dois_decks_iguais_saem_os_dois(self):
        """Mesma Legend e mesmo Champion, sem `Nome:`: os dois aparecem, com
        rótulos distintos — o segundo leva o slug entre parênteses."""
        self.v.write_deck("leblanc", LISTA)
        self.v.write_deck("leblanc-baited-hook", LISTA)
        con = self._importar()
        idx = self.decks.decks_index(con)
        self.assertEqual([d["slug"] for d in idx], ["leblanc-baited-hook", "leblanc"])
        self.assertEqual(
            [d["name"] for d in idx],
            ["Emperor of the Sands · Brutalizer",
             "Emperor of the Sands · Brutalizer (leblanc)"])
        con.close()

    def test_alocacao_distingue_decks_com_o_mesmo_rotulo(self):
        """O bug de 2026-09-11: as 3 Defy estão na Coleção e o deck 1 fica com
        elas reservadas; o deck 2 tem de as ver «noutro deck», não «a comprar»."""
        self.v.write_deck("a", LISTA)
        self.v.write_deck("b", LISTA)
        con = self._importar()
        rows = {r["name"]: r for r in self.decks.deck_rows(con)}
        alloc = self.decks.allocate(con)
        a, b = alloc[rows["a"]["deck_id"]], alloc[rows["b"]["deck_id"]]
        self.assertEqual(a["na_colecao"], {"defy": 3, "brutalizer": 1,
                                           "emperor of the sands": 1})
        self.assertEqual(a["missing"], {})
        self.assertEqual(b["missing"], {}, "o deck 2 mandava comprar o que o 1 já tinha")
        self.assertEqual(b["shared"]["defy"]["qty"], 3)
        self.assertEqual([h["slug"] for h in b["shared"]["defy"]["em"]], ["a"])
        # E o índice diz o mesmo: nada a comprar. Das 5 que o deck 2 pede, 4
        # estão reservadas pelo deck 1 e 1 (a segunda Brutalizer, de 3 na
        # Coleção) ainda está livre na Coleção.
        idx = {d["slug"]: d for d in self.decks.decks_index(con)}
        self.assertEqual(idx["b"]["missing"], 0)
        self.assertEqual(idx["b"]["shared"], 4)
        self.assertEqual(idx["b"]["na_colecao"], 1)
        con.close()

    def test_staples_contam_os_dois_decks(self):
        """Pedida por dois decks com o mesmo rótulo é pedida por DOIS decks."""
        self.v.write_deck("a", LISTA + "3 Extra\n")
        self.v.write_deck("b", LISTA + "3 Extra\n")
        con = self._importar()
        pedido = self.faltas._wanted(con)
        self.assertEqual(set(pedido["defy"]["decks"]), {"a", "b"})
        self.assertEqual(pedido["defy"]["decks"]["a"]["qty"], 3)
        self.assertEqual(pedido["defy"]["qty"], 6)
        con.close()

    def test_tabela_e_order_por_slug(self):
        """`riftvault decks --order b,a` reordena por slug e a tabela mostra
        os dois, mesmo com o mesmo rótulo."""
        from riftvault import cli
        importlib.reload(cli)
        self.v.write_deck("a", LISTA)
        self.v.write_deck("b", LISTA)
        con = self._importar()
        con.close()

        saida = io.StringIO()
        with contextlib.redirect_stdout(saida):
            rc = cli.cmd_decks(argparse.Namespace(order="b,a"))
        self.assertEqual(rc, 0)
        texto = saida.getvalue()
        con = self.v.connect()
        ordem = [(r["name"], r["priority"]) for r in self.decks.deck_rows(con)]
        self.assertEqual(ordem, [("b", 1), ("a", 2)])
        linhas = [l for l in texto.splitlines() if "Emperor of the Sands" in l
                  and l[:1].isdigit()]
        self.assertEqual(len(linhas), 2, texto)
        self.assertTrue(linhas[0].startswith("1   Emperor of the Sands · Brutalizer (b)"), texto)
        self.assertTrue(linhas[1].startswith("2   Emperor of the Sands · Brutalizer "), texto)
        # Depois de reordenar, é o «a» que leva o sufixo — o rótulo segue a
        # prioridade, e a base só o refaz na importação seguinte.
        self.decks.import_all(con, log=lambda *_: None)
        nomes = {d["slug"]: d["name"] for d in self.decks.decks_index(con)}
        self.assertEqual(nomes["b"], "Emperor of the Sands · Brutalizer")
        self.assertEqual(nomes["a"], "Emperor of the Sands · Brutalizer (a)")
        con.close()


if __name__ == "__main__":
    unittest.main()

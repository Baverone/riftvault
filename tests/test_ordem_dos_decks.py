"""A ordem dos decks escreve-se no config (`decks.ordem`, 2026-09-21), e o
registo do que as listas pedem recomeça-se (`uso_decks.recomecar`).

André, 2026-09-21, ao mandar seis listas novas: os decks têm de aparecer POR
ESTA ORDEM — LeBlanc Hook, Jayce, Kennen, Akali, Ornn, Azir —, «não por ordem
alfabética nem por data», e «acrescentar um deck no fim da lista tem de
bastar». E: «recalcula o deck_need_log a partir dos seis decks (não somes por
cima do que lá estava)».

A regra:
  1. `decks.ordem` é uma lista com o slug ou o `Nome:` de cada deck; a
     posição é a prioridade (1 = principal). Manda a cada importação.
  2. O que a lista não nomear vem a seguir, pela ordem que tinha; um nome sem
     deck avisa e é ignorado — o site continua a servir os decks que há.
  3. Com a lista a mandar, os botões do site (`/api/decks/order`) e o
     `riftvault decks --order` recusam (`OrdemFixa`): mudar a base era
     mentira até à importação seguinte. Sem lista, tudo como era.
  4. `recomecar` apaga o `deck_need_log` e escreve o ponto de partida com os
     decks de hoje — as «libertadas» ficam vazias.

Tudo contra cópias descartáveis (`tests.fixture.Vault`) e um config temporário
(`RIFTVAULT_CONFIG`): nunca o `data/` nem o `riftvault_config.json` reais.
"""

from __future__ import annotations

import argparse
import contextlib
import importlib
import io
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ["RIFTVAULT_CONFIG"] = str(Path(tempfile.gettempdir()) / "riftvault-nao-existe.json")

from tests.fixture import REPO, Vault, catalogo_simples  # noqa: E402

LISTA = "Legend:\n1 Emperor of the Sands\n\nChampion:\n1 Brutalizer\n\nMainDeck:\n3 Defy\n"


class Base(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.close)
        catalogo_simples(self.v)
        from riftvault import config, decks, uso_decks
        importlib.reload(decks)
        importlib.reload(uso_decks)
        self.config, self.decks, self.uso = config, decks, uso_decks

    def com_ordem(self, ordem):
        caminho = self.v.root / "config.json"
        caminho.write_text(json.dumps({"decks": {"ordem": ordem}}), encoding="utf-8")
        os.environ["RIFTVAULT_CONFIG"] = str(caminho)
        importlib.reload(self.config)
        self.config.load.cache_clear()

        def repor():
            os.environ["RIFTVAULT_CONFIG"] = str(
                Path(tempfile.gettempdir()) / "riftvault-nao-existe.json")
            importlib.reload(self.config)
            self.config.load.cache_clear()

        self.addCleanup(repor)

    def escrever(self, slug, nome=None):
        self.v.write_deck(slug, (f"Nome: {nome}\n\n" if nome else "") + LISTA)

    def importar(self, log=None):
        con = self.v.connect()
        self.addCleanup(con.close)
        res = self.decks.import_all(con, log=log or (lambda *_: None))
        return con, res

    def ordem(self, con):
        return [(r["name"], r["priority"]) for r in self.decks.deck_rows(con)]


class TestOrdemNoConfig(Base):
    def test_a_lista_manda_pelo_nome_e_pelo_slug(self):
        """Seis decks por ordem alfabética no disco; a lista diz outra ordem,
        umas entradas pelo `Nome:`, outras pelo slug, sem olhar a maiúsculas."""
        for slug, nome in (("akali", "Akali"), ("azir", "Azir"), ("jayce", "Jayce"),
                           ("kennen", "Kennen"), ("leblanc-hook", "LeBlanc Hook"),
                           ("ornn", "Ornn")):
            self.escrever(slug, nome)
        self.com_ordem(["leblanc hook", "JAYCE", "kennen", "Akali", "ornn", "Azir"])
        con, res = self.importar()
        self.assertEqual(self.ordem(con), [
            ("leblanc-hook", 1), ("jayce", 2), ("kennen", 3), ("akali", 4),
            ("ornn", 5), ("azir", 6)])
        self.assertEqual(res["ordem"]["ordem"],
                         ["leblanc-hook", "jayce", "kennen", "akali", "ornn", "azir"])
        self.assertEqual(res["ordem"]["nao_encontrados"], [])
        # O `decks_index` (a aba Decks) sai pela mesma ordem, com o principal
        # em primeiro — não é alfabética nem a do disco.
        idx = self.decks.decks_index(con)
        self.assertEqual([d["name"] for d in idx],
                         ["LeBlanc Hook", "Jayce", "Kennen", "Akali", "Ornn", "Azir"])
        self.assertEqual(idx[0]["priority"], 1)
        # E o `results` da importação já diz a prioridade final.
        self.assertEqual({d["slug"]: d["priority"] for d in res["decks"]},
                         dict(self.ordem(con)))

    def test_mudar_a_lista_reordena_na_importacao_seguinte(self):
        self.escrever("a"), self.escrever("b"), self.escrever("c")
        self.com_ordem(["c", "a", "b"])
        con, _ = self.importar()
        self.assertEqual(self.ordem(con), [("c", 1), ("a", 2), ("b", 3)])
        con.close()
        self.com_ordem(["b", "c", "a"])
        con, res = self.importar()
        self.assertEqual(self.ordem(con), [("b", 1), ("c", 2), ("a", 3)])
        # Os ficheiros não mexeram — só a prioridade foi escrita.
        self.assertEqual([d["slug"] for d in res["decks"]], ["a", "b", "c"])

    def test_acrescentar_um_deck_no_fim_da_lista_basta(self):
        """Um deck novo entra com o ficheiro; a posição vem da lista."""
        self.escrever("a"), self.escrever("b")
        self.com_ordem(["b", "a"])
        con, _ = self.importar()
        self.assertEqual(self.ordem(con), [("b", 1), ("a", 2)])
        con.close()
        self.escrever("novo")
        self.com_ordem(["b", "a", "novo"])
        con, _ = self.importar()
        self.assertEqual(self.ordem(con), [("b", 1), ("a", 2), ("novo", 3)])
        con.close()
        # E pô-lo no meio muda-o de sítio sem mexer no ficheiro.
        self.com_ordem(["b", "novo", "a"])
        con, _ = self.importar()
        self.assertEqual(self.ordem(con), [("b", 1), ("novo", 2), ("a", 3)])

    def test_o_que_a_lista_nao_nomeia_vem_a_seguir_pela_ordem_que_tinha(self):
        self.escrever("a"), self.escrever("b"), self.escrever("c"), self.escrever("d")
        # Sem lista: a ordem do disco (a, b, c, d). Depois troca-se à mão.
        con, _ = self.importar()
        ids = {r["name"]: r["deck_id"] for r in self.decks.deck_rows(con)}
        self.decks.set_order(con, [ids["d"], ids["c"], ids["b"], ids["a"]])
        self.assertEqual(self.ordem(con), [("d", 1), ("c", 2), ("b", 3), ("a", 4)])
        con.close()
        # A lista nomeia só dois: esses primeiro, os outros a seguir como
        # estavam (c antes de b).
        self.com_ordem(["a", "d"])
        con, res = self.importar()
        self.assertEqual(self.ordem(con), [("a", 1), ("d", 2), ("c", 3), ("b", 4)])
        self.assertEqual(res["ordem"]["fora_da_lista"], ["c", "b"])

    def test_um_nome_sem_deck_avisa_e_nao_rebenta(self):
        self.escrever("a"), self.escrever("b")
        self.com_ordem(["b", "kennen", "a"])
        avisos = []
        con, res = self.importar(log=avisos.append)
        self.assertEqual(self.ordem(con), [("b", 1), ("a", 2)])
        self.assertEqual(res["ordem"]["nao_encontrados"], ["kennen"])
        self.assertTrue(any("kennen" in a for a in avisos), avisos)
        # Um deck apagado que ainda esteja na lista é o mesmo caso.
        (self.v.decks_dir / "b.txt").unlink()
        con.close()
        con, res = self.importar()
        self.assertEqual(self.ordem(con), [("a", 1)])
        self.assertEqual(res["ordem"]["nao_encontrados"], ["b", "kennen"])

    def test_a_mesma_entrada_duas_vezes_conta_uma(self):
        self.escrever("a", "Azir"), self.escrever("b")
        self.com_ordem(["b", "azir", "a", "b"])
        con, _ = self.importar()
        self.assertEqual(self.ordem(con), [("b", 1), ("a", 2)])

    def test_dois_rotulos_iguais_o_sufixo_segue_a_lista(self):
        """Dois ficheiros sem `Nome:` e a mesma Legend/Champion: o de cima na
        lista fica limpo, o outro leva o slug entre parênteses — a regra do
        `rotulos` lê a prioridade que a lista dá."""
        self.escrever("a"), self.escrever("b")
        self.com_ordem(["b", "a"])
        con, _ = self.importar()
        nomes = {d["slug"]: d["name"] for d in self.decks.decks_index(con)}
        self.assertEqual(nomes["b"], "Emperor of the Sands · Brutalizer")
        self.assertEqual(nomes["a"], "Emperor of the Sands · Brutalizer (a)")

    def test_importacao_sem_alteracoes_nao_escreve(self):
        self.escrever("a"), self.escrever("b")
        self.com_ordem(["b", "a"])
        con, _ = self.importar()
        antes = con.total_changes
        self.decks.import_all(con, log=lambda *_: None)
        self.assertEqual(con.total_changes, antes, "nada mudou, nada se escreve")

    def test_lista_mal_escrita_rebenta(self):
        self.escrever("a")
        self.com_ordem("a,b")
        with self.assertRaises(ValueError):
            self.decks.ordem_dos_decks()
        self.com_ordem([1, 2])
        with self.assertRaises(ValueError):
            self.decks.ordem_dos_decks()

    def test_sem_lista_tudo_como_era(self):
        """Sem `decks.ordem`: o disco dá a ordem, um deck novo vai para o fim,
        e o `set_order` continua a funcionar."""
        self.escrever("b"), self.escrever("a")
        con, res = self.importar()
        self.assertFalse(self.decks.ordem_fixa())
        self.assertFalse(res["ordem"]["aplicada"])
        self.assertEqual(self.ordem(con), [("a", 1), ("b", 2)])
        ids = {r["name"]: r["deck_id"] for r in self.decks.deck_rows(con)}
        self.decks.set_order(con, [ids["b"], ids["a"]])
        self.assertEqual(self.ordem(con), [("b", 1), ("a", 2)])
        con.close()
        self.escrever("novo")
        con, _ = self.importar()
        self.assertEqual(self.ordem(con), [("b", 1), ("a", 2), ("novo", 3)])


class TestOsBotoesFicamDesligados(Base):
    def test_set_order_recusa_com_a_lista(self):
        self.escrever("a"), self.escrever("b")
        self.com_ordem(["b", "a"])
        con, _ = self.importar()
        ids = {r["name"]: r["deck_id"] for r in self.decks.deck_rows(con)}
        with self.assertRaises(self.decks.OrdemFixa):
            self.decks.set_order(con, [ids["a"], ids["b"]])
        self.assertEqual(self.ordem(con), [("b", 1), ("a", 2)], "não mexeu")

    def test_a_cli_recusa_o_order(self):
        from riftvault import cli
        importlib.reload(cli)
        self.escrever("a"), self.escrever("b")
        self.com_ordem(["b", "a"])
        saida, erro = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(saida), contextlib.redirect_stderr(erro):
            rc = cli.cmd_decks(argparse.Namespace(order="a,b"))
        self.assertEqual(rc, 1)
        self.assertIn("decks.ordem", erro.getvalue())
        con = self.v.connect()
        self.addCleanup(con.close)
        self.assertEqual(self.ordem(con), [("b", 1), ("a", 2)])

    def test_a_rota_responde_409_e_o_payload_diz_ordem_fixa(self):
        from riftvault import server
        importlib.reload(server)
        self.escrever("a"), self.escrever("b")
        self.com_ordem(["b", "a"])
        con, _ = self.importar()
        ids = {r["name"]: r["deck_id"] for r in self.decks.deck_rows(con)}
        con.close()
        server.app.config["TESTING"] = True
        with server.app.test_client() as c:
            r = c.get("/api/decks.json")
            self.assertEqual(r.status_code, 200)
            self.assertTrue(r.get_json()["ordem_fixa"])
            self.assertEqual([d["slug"] for d in r.get_json()["decks"]], ["b", "a"])
            r = c.post("/api/decks/order", json={"ids": [ids["a"], ids["b"]]})
            self.assertEqual(r.status_code, 409)
            self.assertIn("decks.ordem", r.get_json()["error"])
            r = c.get("/api/decks.json")
            self.assertEqual([d["slug"] for d in r.get_json()["decks"]], ["b", "a"])

    def test_a_rota_aplica_a_lista_sem_nenhum_txt_ter_mexido(self):
        """A lista muda no config e o servidor é relançado: o `/api/decks.json`
        tem de vir pela ordem nova mesmo sem reimportação (os .txt não
        mexeram, o `_reimport_if_changed` não corre)."""
        from riftvault import server
        importlib.reload(server)
        self.escrever("a"), self.escrever("b")
        self.com_ordem(["b", "a"])
        con, _ = self.importar()
        con.close()
        self.com_ordem(["a", "b"])
        server.app.config["TESTING"] = True
        with server.app.test_client() as c:
            self.assertEqual([d["slug"] for d in c.get("/api/decks.json").get_json()["decks"]],
                             ["a", "b"])

    def test_sem_lista_a_rota_e_o_payload_ficam_como_eram(self):
        from riftvault import server
        importlib.reload(server)
        self.escrever("a"), self.escrever("b")
        con, _ = self.importar()
        ids = {r["name"]: r["deck_id"] for r in self.decks.deck_rows(con)}
        con.close()
        server.app.config["TESTING"] = True
        with server.app.test_client() as c:
            self.assertFalse(c.get("/api/decks.json").get_json()["ordem_fixa"])
            r = c.post("/api/decks/order", json={"ids": [ids["b"], ids["a"]]})
            self.assertEqual(r.status_code, 200)
            self.assertEqual([d["slug"] for d in r.get_json()["decks"]], ["b", "a"])

    def test_o_site_esconde_os_botoes_e_o_build_leva_o_flag(self):
        js = (REPO / "riftvault" / "web" / "app.js").read_text(encoding="utf-8")
        self.assertIn("state.ordemFixa = !!d.ordem_fixa", js)
        for act in ("principal", "subir", "descer"):
            m = re.search(r'!state\.ordemFixa[^\n]*\n?[^\n]*data-act="%s"' % act, js)
            self.assertIsNotNone(m, f"o botão {act} tem de ficar atrás do `ordemFixa`")
        build = (REPO / "riftvault" / "build.py").read_text(encoding="utf-8")
        self.assertIn('"ordem_fixa": decks.ordem_fixa()', build)


class TestRecomecarORegisto(Base):
    def test_recomecar_apaga_o_historico_e_escreve_o_ponto_de_partida(self):
        self.escrever("velho")
        con, _ = self.importar()
        # Uma mudança a sério: o deck velho sai, entra outro. Sem recomeçar, o
        # registo guardava as descidas do velho — «libertadas» que são só a
        # lista antiga a ir embora.
        (self.v.decks_dir / "velho.txt").unlink()
        self.escrever("novo")
        self.decks.import_all(con, log=lambda *_: None)
        self.assertTrue(self.uso.libertadas(con), "sem recomeçar, o velho liberta")
        n = self.uso.recomecar(con)
        linhas = [dict(r) for r in con.execute(
            "SELECT slug, qty_before, qty_after FROM deck_need_log ORDER BY id")]
        self.assertEqual(n, len(linhas))
        self.assertEqual({l["slug"] for l in linhas}, {"novo"})
        self.assertTrue(all(l["qty_before"] == 0 and l["qty_after"] > 0 for l in linhas))
        self.assertEqual(self.uso.libertadas(con), [])
        # O ponto de partida é EXACTAMENTE o pedido de hoje.
        self.assertEqual({l["qty_after"] for l in linhas},
                         {v["qty"] for v in self.uso.pedido_atual(con).values()})
        # E a partir daí uma descida volta a contar.
        self.v.write_deck("novo", LISTA.replace("3 Defy", "1 Defy"))
        self.decks.import_all(con, log=lambda *_: None)
        lib = self.uso.libertadas(con)
        self.assertEqual([(x["slug"], x["card_key"], x["qty"]) for x in lib],
                         [("novo", "defy", 2)])

    def test_recomecar_so_toca_no_registo(self):
        self.escrever("a")
        con, _ = self.importar()
        from riftvault import collection
        collection.adjust(con, "tst-001-100", 1, source="test")
        foto = lambda: (
            [tuple(r) for r in con.execute("SELECT printing_id, qty FROM copies ORDER BY 1")],
            con.execute("SELECT COUNT(*) FROM ops").fetchone()[0],
            [tuple(r) for r in con.execute("SELECT name, priority FROM decks ORDER BY 1")],
            con.execute("SELECT COUNT(*) FROM deck_cards").fetchone()[0],
        )
        antes = foto()
        self.uso.recomecar(con)
        self.assertEqual(foto(), antes)

    def test_a_cli_recomeca(self):
        from riftvault import cli
        importlib.reload(cli)
        self.escrever("a")
        con, _ = self.importar()
        con.execute("BEGIN")
        con.execute("INSERT INTO deck_need_log (ts, slug, deck, card_key, qty_before, qty_after) "
                    "VALUES ('2026-01-01T00:00:00+00:00', 'morto', 'Morto', 'defy', 3, 0)")
        con.execute("COMMIT")
        con.close()
        saida = io.StringIO()
        with contextlib.redirect_stdout(saida):
            rc = cli.cmd_decks(argparse.Namespace(order=None, recomecar_registo=True))
        self.assertEqual(rc, 0)
        self.assertIn("recomeçado", saida.getvalue())
        con = self.v.connect()
        self.addCleanup(con.close)
        self.assertEqual(con.execute("SELECT COUNT(*) FROM deck_need_log WHERE slug='morto'")
                         .fetchone()[0], 0)
        self.assertEqual(self.uso.libertadas(con), [])


if __name__ == "__main__":
    unittest.main()

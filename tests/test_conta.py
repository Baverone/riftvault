"""EXPORTAR, IMPORTAR e APAGAR uma conta, sem tocar nas outras (2026-09-29).

Da ordem: *"Com cinco pessoas lá dentro, restaurar um erro dele desfaz o mês
dos outros"* e *"Se isto não existir ao dia 1, um dia ele vai fazer SQL à mão
em dados vivos com um amigo à espera."*

A forma de todos os testes daqui é a mesma, e é a única que prova o que a
ordem pede: **fotografa-se o utilizador B — o ficheiro dele byte a byte e as
linhas todas das 16 tabelas — mexe-se no A, e exige-se que o B não tenha
mudado.** Mais um teste que mostra que a fotografia sabe detectar uma mudança,
senão passava sempre.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import unittest
import zipfile
from pathlib import Path

from riftvault import collection, conta, db, foil, utilizador
from tests import fixture


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else "—"


class Dois(unittest.TestCase):
    """O André (1) e o Miguel (2), com colecções diferentes."""

    def setUp(self):
        self.v = fixture.Vault()
        self.addCleanup(self.v.close)
        fixture.catalogo_simples(self.v)     # o André já fica com cartas
        con = db.connect()
        foil.ajustar(con, "tst-001-100", 2)
        con.close()

        self.miguel = utilizador.criar("Miguel", "miguel")
        self.uid_b = self.miguel["user_id"]
        conb = db.connect(user_id=self.uid_b)
        collection.adjust(conb, "tst-002-100", 4, source="test")
        collection.adjust(conb, "tst-003-100", 1, source="test")
        conb.close()

        self.vault_a = db.vault_de(utilizador.ANDRE)
        self.vault_b = db.vault_de(self.uid_b)

    def linhas(self, caminho: Path, uid: int) -> dict:
        con = db.abrir_vault(caminho, uid, readonly=True)
        try:
            fora = {}
            for t in db.TABELAS_DE_DONO:
                try:
                    fora[t] = [tuple(r) for r in con.execute(f"SELECT * FROM {t}")]  # noqa: S608
                except sqlite3.OperationalError:
                    fora[t] = []
            return fora
        finally:
            con.close()

    def foto_b(self):
        return (sha(self.vault_b), self.linhas(self.vault_b, self.uid_b))

    def foto_a(self):
        return (sha(self.vault_a), self.linhas(self.vault_a, utilizador.ANDRE))


class TestExportar(Dois):

    def test_um_zip_com_manifesto_e_a_base(self):
        r = conta.exportar("miguel")
        self.assertTrue(r["ficheiro"].exists())
        with zipfile.ZipFile(r["ficheiro"]) as z:
            nomes = set(z.namelist())
        self.assertIn(conta.NOME_MANIFESTO, nomes)
        self.assertIn(conta.NOME_VAULT, nomes)
        self.assertEqual(r["linhas"]["copies"], 2)

    def test_o_manifesto_diz_quem_e_quando_e_quantas_linhas(self):
        m = conta.ler_manifesto(conta.exportar("miguel")["ficheiro"])
        self.assertEqual(m["formato"], conta.FORMATO)
        self.assertEqual(m["utilizador"]["slug"], "miguel")
        self.assertEqual(m["utilizador"]["user_id"], self.uid_b)
        self.assertIn("quando", m)
        self.assertEqual(m["linhas"]["copies"], 2)
        self.assertTrue(m["sha256_vault"])

    def test_exportar_nao_escreve_na_base_de_ninguem(self):
        a, b = self.foto_a(), self.foto_b()
        conta.exportar("miguel")
        conta.exportar(utilizador.SLUG_ANDRE)
        self.assertEqual(self.foto_a(), a)
        self.assertEqual(self.foto_b(), b)

    def test_nao_leva_credenciais(self):
        """A `user_auth` e as sessões vivem no `data/auth.db`, fora daqui. Um
        export é uma coisa que se manda por email; um token não é."""
        with zipfile.ZipFile(conta.exportar("miguel")["ficheiro"]) as z:
            nomes = " ".join(z.namelist()).lower()
        for palavra in ("auth", "sess", "token", "credencial"):
            self.assertNotIn(palavra, nomes)

    def test_nao_leva_o_catalogo_nem_os_precos(self):
        """São partilhados e não são de ninguém — e um export com o catálogo
        lá dentro era um export que ninguém manda."""
        r = conta.exportar("miguel")
        with zipfile.ZipFile(r["ficheiro"]) as z:
            nomes = set(z.namelist())
        self.assertNotIn("catalog.db", nomes)
        self.assertNotIn("prices.db", nomes)
        self.assertLess(r["bytes"], 400_000, "o pacote está demasiado gordo")

    def test_um_slug_que_nao_existe(self):
        with self.assertRaises(utilizador.UtilizadorDesconhecido):
            conta.exportar("ninguem")


class TestImportar(Dois):

    def test_sem_confirmar_nao_escreve(self):
        p = conta.exportar("miguel")["ficheiro"]
        antes = self.foto_b()
        with self.assertRaises(conta.PrecisaConfirmar) as e:
            conta.importar(p)
        self.assertIn("miguel", str(e.exception))
        self.assertEqual(self.foto_b(), antes)

    def test_restaurar_repoe_o_que_estava(self):
        p = conta.exportar("miguel")["ficheiro"]
        antes = self.linhas(self.vault_b, self.uid_b)
        # estragar
        con = db.connect(user_id=self.uid_b)
        collection.adjust(con, "tst-002-100", -4, source="test")
        collection.adjust(con, "tst-001-100", 9, source="test")
        con.close()
        self.assertNotEqual(self.linhas(self.vault_b, self.uid_b), antes)
        conta.importar(p, confirmar=True)
        self.assertEqual(self.linhas(self.vault_b, self.uid_b), antes)

    def test_RESTAURAR_O_A_NAO_MUDA_UMA_LINHA_DO_B(self):
        """É o teste que a ordem pede pelo nome."""
        pa = conta.exportar(utilizador.SLUG_ANDRE)["ficheiro"]
        b_antes = self.foto_b()
        con = db.connect()
        collection.adjust(con, "tst-001-100", 5, source="test")
        con.close()
        conta.importar(pa, confirmar=True)
        self.assertEqual(self.foto_b(), b_antes,
                         "restaurar o André mexeu no Miguel")

    def test_e_ao_contrario(self):
        pb = conta.exportar("miguel")["ficheiro"]
        a_antes = self.foto_a()
        conta.importar(pb, confirmar=True)
        self.assertEqual(self.foto_a(), a_antes,
                         "restaurar o Miguel mexeu no André")

    def test_faz_backup_do_que_estava_la(self):
        p = conta.exportar("miguel")["ficheiro"]
        r = conta.importar(p, confirmar=True)
        self.assertIsNotNone(r["backup"])
        self.assertTrue(Path(r["backup"]).exists())

    def test_um_pacote_estragado_nao_entra(self):
        p = conta.exportar("miguel")["ficheiro"]
        antes = self.foto_b()
        # mexer no sha
        bruto = p.read_bytes()
        p.write_bytes(bruto[:-40] + b"x" * 40)
        with self.assertRaises((conta.PacoteInvalido, zipfile.BadZipFile)):
            conta.importar(p, confirmar=True)
        self.assertEqual(self.foto_b(), antes)

    def test_um_zip_que_nao_e_nosso(self):
        p = self.v.root / "qualquer.zip"
        with zipfile.ZipFile(p, "w") as z:
            z.writestr("leiame.txt", "olá")
        with self.assertRaises(conta.PacoteInvalido):
            conta.ler_manifesto(p)

    def test_um_pacote_com_linhas_de_outro_dono_e_recusado(self):
        """O caso a sério: restaurar o backup do A por cima do B."""
        p = conta.exportar("miguel")["ficheiro"]
        # forjar o manifesto para dizer que é do André
        m = conta.ler_manifesto(p)
        m["utilizador"]["user_id"] = utilizador.ANDRE
        m["utilizador"]["slug"] = utilizador.SLUG_ANDRE
        novo = self.v.root / "forjado.zip"
        with zipfile.ZipFile(p) as z0, zipfile.ZipFile(novo, "w") as z1:
            for n in z0.namelist():
                if n == conta.NOME_MANIFESTO:
                    z1.writestr(n, json.dumps(m))
                else:
                    z1.writestr(n, z0.read(n))
        antes = self.foto_a()
        with self.assertRaises(utilizador.DonoErrado):
            conta.importar(novo, confirmar=True)
        self.assertEqual(self.foto_a(), antes,
                         "o pacote de outro dono chegou a escrever")

    def test_restaurar_uma_conta_apagada_recria_a(self):
        p = conta.exportar("miguel")["ficheiro"]
        conta.apagar("miguel", confirmar=True)
        self.assertIsNone(utilizador.por_slug("miguel", obrigatorio=False))
        r = conta.importar(p, confirmar=True)
        self.assertEqual(r["utilizador"]["slug"], "miguel")
        self.assertIsNotNone(utilizador.por_slug("miguel", obrigatorio=False))
        self.assertEqual(r["linhas"]["copies"], 2)


class TestApagar(Dois):

    def test_sem_confirmar_nao_apaga_e_diz_o_que_ia_tirar(self):
        antes = self.foto_b()
        with self.assertRaises(conta.PrecisaConfirmar) as e:
            conta.apagar("miguel")
        self.assertIn("copies", str(e.exception))
        self.assertEqual(self.foto_b(), antes)
        self.assertTrue(self.vault_b.exists())

    def test_apaga_o_que_e_dele_e_diz_quantas_linhas_de_onde(self):
        r = conta.apagar("miguel", confirmar=True)
        self.assertEqual(r["linhas"]["copies"], 2)
        self.assertEqual(r["total"], sum(r["linhas"].values()))
        self.assertFalse(self.vault_b.exists())
        self.assertFalse(Path(r["pasta"]).exists())
        self.assertIsNone(utilizador.por_slug("miguel", obrigatorio=False))

    def test_O_OUTRO_FICA_EXACTAMENTE_IGUAL(self):
        """É o teste que a ordem pede pelo nome."""
        a_antes = self.foto_a()
        conta.apagar("miguel", confirmar=True)
        self.assertEqual(self.foto_a(), a_antes)

    def test_o_catalogo_e_os_precos_ficam_intactos(self):
        con = db.connect()
        n_cat = con.execute("SELECT COUNT(*) FROM catalog.printings").fetchone()[0]
        n_pre = con.execute("SELECT COUNT(*) FROM catalog.price_latest").fetchone()[0]
        con.close()
        conta.apagar("miguel", confirmar=True)
        con = db.connect()
        self.addCleanup(con.close)
        self.assertEqual(
            con.execute("SELECT COUNT(*) FROM catalog.printings").fetchone()[0], n_cat)
        self.assertEqual(
            con.execute("SELECT COUNT(*) FROM catalog.price_latest").fetchone()[0], n_pre)

    def test_faz_um_export_antes(self):
        r = conta.apagar("miguel", confirmar=True)
        self.assertIsNotNone(r["backup"])
        self.assertTrue(Path(r["backup"]).exists())
        m = conta.ler_manifesto(r["backup"])
        self.assertEqual(m["utilizador"]["slug"], "miguel")

    def test_sem_backup_se_lho_pedirem(self):
        r = conta.apagar("miguel", confirmar=True, com_backup=False)
        self.assertIsNone(r["backup"])

    def test_o_andre_nao_se_apaga(self):
        with self.assertRaises((conta.NaoSeApaga, utilizador.SlugInvalido)) as e:
            conta.apagar(utilizador.SLUG_ANDRE, confirmar=True)
        self.assertTrue(self.vault_a.exists())
        self.assertIn("1", str(e.exception) + "1")

    def test_a_fotografia_do_a_nao_e_de_zeros(self):
        """A prova pela negativa: sem isto, os testes de cima passavam mesmo
        que a fotografia não visse nada."""
        antes = self.foto_a()
        con = db.connect()
        collection.adjust(con, "tst-001-100", 1, source="test")
        con.close()
        self.assertNotEqual(self.foto_a(), antes)


if __name__ == "__main__":
    unittest.main(verbosity=2)

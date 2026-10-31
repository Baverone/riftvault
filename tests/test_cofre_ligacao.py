"""O riftvault fala com o COFRE DE CONTAS (2026-10-31).

Desde este dia as passwords do riftvault não moram no `auth.db`: moram no
cofre partilhado (`contas`), que o mtgvault também usa. O `auth.py` mantém as
funções de sempre (`definir_senha`, `entrar`, `mudar_senha`, ...) e delega.
Ficam no `auth.db` as sessões, o OAuth, os convites e o tecto do OAuth.

O que esta bateria fixa é a LIGAÇÃO — a lógica do cofre tem os testes dela no
próprio pacote:

  1. o `riftvault.senha` é o MESMO módulo que o `contas.senha` (um KDF só);
  2. o cofre segue o ensaio: com o `auth.db` numa pasta temporária, o
     `contas.db` vai para lá também, e nunca para o cofre a sério;
  3. definir uma password cria a conta no cofre com o MESMO número do registo
     e com acesso ao riftvault;
  4. entrar devolve o que sempre devolveu;
  5. a sessão leva a GERAÇÃO da password: mudar a password pelo cofre (pelo
     mtgvault, por exemplo) mata as sessões abertas antes;
  6. uma sessão de antes desta mudança (geração NULL) continua a valer.

Tudo contra pastas temporárias (`tests.fixture.Vault`, que aponta o
`CONTAS_DB` para lá): o cofre a sério e o `data/` nunca são tocados. As
passwords são inventadas.
"""

from __future__ import annotations

import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.fixture import SEM_CONFIG  # noqa: E402

os.environ["RIFTVAULT_CONFIG"] = SEM_CONFIG

from tests.fixture import Vault  # noqa: E402

#: Inventadas, e só servem aqui.
FRASE = "uma-frase-inventada-para-o-teste-31"
OUTRA = "outra-frase-inventada-para-o-teste-77"


class Base(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.close)
        os.environ["RIFTVAULT_AUTH"] = str(self.v.data / "auth.db")
        self.addCleanup(lambda: os.environ.pop("RIFTVAULT_AUTH", None))
        os.environ.pop("RIFTVAULT_ENSAIO", None)
        os.environ.pop("RIFTVAULT_USER", None)

        from riftvault import (auth, cofre, config, db, multi, privacidade,
                               senha, utilizador)
        for m in (config, db, utilizador, multi, privacidade, senha, cofre,
                  auth):
            importlib.reload(m)
        self.auth, self.cofre, self.utilizador = auth, cofre, utilizador

    def conta(self, slug: str = "miguel", password: str = FRASE) -> int:
        """Um utilizador do registo, já com a password definida pelo `auth`."""
        u = self.utilizador.criar(slug.capitalize(), slug)
        uid = int(u["user_id"])
        con = self.auth.abrir()
        try:
            self.auth.definir_senha(con, uid, password, temporaria=False)
        finally:
            con.close()
        return uid


class TestOModuloDaSenha(Base):
    def test_senha_e_o_mesmo_modulo(self):
        """Dois KDF eram duas respostas à mesma pergunta — e um dia divergiam."""
        import contas.senha
        import riftvault.senha
        from riftvault import senha
        self.assertIs(riftvault.senha, contas.senha)
        self.assertIs(senha, contas.senha)


class TestOCaminho(Base):
    def test_o_fixture_aponta_o_cofre_para_a_pasta_temporaria(self):
        self.assertEqual(Path(os.environ["CONTAS_DB"]),
                         self.v.data / "contas.db")
        self.assertEqual(self.cofre.caminho_db(), self.v.data / "contas.db")

    def test_cofre_segue_o_ensaio(self):
        """Sem `CONTAS_DB`, um `auth.db` de ensaio leva o cofre consigo."""
        antes = os.environ.pop("CONTAS_DB", None)
        self.addCleanup(lambda: os.environ.__setitem__("CONTAS_DB", antes)
                        if antes is not None else None)
        pasta = Path(tempfile.mkdtemp(prefix="riftvault-cofre-ensaio-"))
        os.environ["RIFTVAULT_AUTH"] = str(pasta / "auth.db")
        self.assertEqual(self.cofre.caminho_db(), pasta / "contas.db")
        self.assertNotEqual(self.cofre.caminho_db(),
                            self.cofre.pasta_contas() / "data" / "contas.db")

    def test_a_pasta_do_contas_encontra_se_a_partir_do_repositorio(self):
        p = self.cofre.pasta_contas()
        self.assertTrue((p / "contas" / "__init__.py").is_file(), p)


class TestADelegacao(Base):
    def test_definir_cria_conta_no_cofre(self):
        uid = self.conta("miguel")
        m = self.cofre.modulo()
        cc = self.cofre.abrir()
        try:
            c = m.por_id(cc, uid)
            self.assertIsNotNone(c, "a conta não nasceu no cofre")
            self.assertEqual(c["slug"], "miguel")
            self.assertTrue(m.tem_acesso(cc, uid, "rift"))
            self.assertTrue(m.estado_password(cc, uid)["tem"])
        finally:
            cc.close()
        # E o `auth.db` não ganhou hash nenhum: a `user_senha` é arquivo.
        con = self.auth.abrir()
        try:
            n = con.execute("SELECT COUNT(*) FROM user_senha").fetchone()[0]
        finally:
            con.close()
        self.assertEqual(n, 0)

    def test_entrar_pelo_cofre(self):
        uid = self.conta("miguel")
        con = self.auth.abrir()
        try:
            quem = self.auth.entrar(con, "miguel", FRASE, chave="1.1.1.1")
            self.assertLessEqual({"user_id", "slug", "nome", "temporaria"},
                                 set(quem))
            self.assertEqual(quem["user_id"], uid)
            self.assertEqual(quem["slug"], "miguel")
            self.assertFalse(quem["temporaria"])
            # Os erros são os do cofre, e o `except auth.ErroDeAutenticacao`
            # das rotas continua a apanhá-los.
            self.assertIs(self.auth.SenhaErrada, self.cofre.modulo().SenhaErrada)
            with self.assertRaises(self.auth.ErroDeAutenticacao):
                self.auth.entrar(con, "miguel", "nao-e-esta", chave="1.1.1.1")
        finally:
            con.close()


class TestAGeracao(Base):
    def test_sessao_com_geracao_antiga(self):
        """Mudou a password noutro sítio (o mtgvault): a sessão de cá cai."""
        uid = self.conta("miguel")
        con = self.auth.abrir()
        try:
            quem = self.auth.entrar(con, "miguel", FRASE, chave="1.1.1.1")
            s = self.auth.criar_sessao(con, user_id=uid,
                                       geracao=quem["geracao"])
            self.assertIsNotNone(self.auth.sessao(con, s["sid"]))
            m = self.cofre.modulo()
            cc = self.cofre.abrir()
            try:
                m.definir_password(cc, uid, OUTRA)
            finally:
                cc.close()
            self.assertIsNone(self.auth.sessao(con, s["sid"]))
            n = con.execute("SELECT COUNT(*) FROM sessions WHERE user_id = ?",
                            (uid,)).fetchone()[0]
            self.assertEqual(n, 0, "a linha da sessão morta tinha de sair")
        finally:
            con.close()

    def test_sessao_antiga_sem_geracao_vale(self):
        """Uma sessão de antes da migração (`geracao` NULL) não cai sozinha."""
        uid = self.conta("miguel")
        con = self.auth.abrir()
        try:
            s = self.auth.criar_sessao(con, user_id=uid)
            con.execute("UPDATE sessions SET geracao = NULL WHERE user_id = ?",
                        (uid,))
            con.commit()
            # A conta migrada tem a geração 0 (o `importar_hash` não a sobe):
            # é a esse cofre que uma sessão de antes tem de sobreviver.
            m = self.cofre.modulo()
            cc = self.cofre.abrir()
            try:
                cc.execute("UPDATE contas SET geracao = 0 WHERE id = ?", (uid,))
                cc.commit()
            finally:
                cc.close()
            self.assertIsNotNone(self.auth.sessao(con, s["sid"]))
            # NULL vale como 0: uma mudança de password depois da migração
            # também a mata, como a qualquer outra.
            cc = self.cofre.abrir()
            try:
                m.definir_password(cc, uid, OUTRA)
            finally:
                cc.close()
            self.assertIsNone(self.auth.sessao(con, s["sid"]))
        finally:
            con.close()

    def test_a_coluna_nasce_numa_base_de_ontem(self):
        """Um `auth.db` de antes não tem a coluna; o `_migrar` acrescenta-a."""
        import sqlite3
        velho = sqlite3.connect(os.environ["RIFTVAULT_AUTH"])
        velho.execute(
            "CREATE TABLE sessions (sid_hash TEXT PRIMARY KEY, user_id INTEGER, "
            "provedor TEXT, sub TEXT, nome TEXT, csrf TEXT NOT NULL, "
            "criado_em TEXT NOT NULL, visto_em TEXT NOT NULL, "
            "expira_em TEXT NOT NULL, agente TEXT)")
        velho.commit()
        velho.close()
        con = self.auth.abrir()
        try:
            cols = {r["name"] for r in con.execute("PRAGMA table_info(sessions)")}
        finally:
            con.close()
        self.assertIn("geracao", cols)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

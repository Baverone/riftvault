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

    def _so_o_ensaio(self, valor: str):
        """O ambiente sem nada que aponte o cofre, com `RIFTVAULT_ENSAIO=valor`,
        e o `config` relido com ele. Tudo volta ao que estava no fim."""
        from riftvault import config
        guardado = {v: os.environ.pop(v, None)
                    for v in ("CONTAS_DB", "RIFTVAULT_AUTH", "RIFTVAULT_DATA")}

        def repor():
            for v, antes in guardado.items():
                if antes is None:
                    os.environ.pop(v, None)
                else:
                    os.environ[v] = antes
            os.environ.pop("RIFTVAULT_ENSAIO", None)
            importlib.reload(config)
        self.addCleanup(repor)
        os.environ["RIFTVAULT_ENSAIO"] = valor
        importlib.reload(config)
        return config

    def test_ensaio_a_zero_nao_e_ensaio(self):
        """`RIFTVAULT_ENSAIO=0` é o ensaio DESLIGADO (é o que o `config` lê):
        o cofre é o a sério, e nunca um `contas.db` dentro do `data/` daqui."""
        config = self._so_o_ensaio("0")
        self.assertFalse(config.ENSAIO)
        p = self.cofre.caminho_db()  # só se resolve; não se abre
        dados = (config.ROOT / "data").resolve()
        self.assertNotEqual(p.resolve().parent, dados)
        self.assertFalse(str(p.resolve()).startswith(str(dados)), p)
        self.assertEqual(p, self.cofre.pasta_contas() / "data" / "contas.db")

    def test_ensaio_ligado_leva_o_cofre_para_o_data_do_ensaio(self):
        config = self._so_o_ensaio("1")
        self.assertTrue(config.ENSAIO)
        self.assertEqual(self.cofre.caminho_db(),
                         config.ROOT / "data-ensaio" / "contas.db")

    def test_o_gitignore_tem_o_cofre(self):
        """Um `contas.db` a parar no `data/` (um ensaio antigo, um engano) nunca
        pode ir para o Git: o repositório é PÚBLICO."""
        from riftvault import config
        linhas = (config.ROOT / ".gitignore").read_text(
            encoding="utf-8").splitlines()
        self.assertTrue("data/contas.db*" in [ln.strip() for ln in linhas],
                        "falta a linha data/contas.db* no .gitignore")

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


class TestOCofreNaoTrocaPessoas(Base):
    """Revisão de 2026-10-31: o número do cofre não é, por si, o do registo.

    Uma conta criada no cofre por outra porta (a consola do cofre, o mtgvault)
    leva um número AUTOINCREMENT que pode ser o de OUTRA pessoa do riftvault.
    Entrar com ela tem de falhar como uma password errada — nunca dar a coleção
    do dono daquele número.
    """

    def test_conta_do_cofre_com_o_numero_de_outro_nao_entra_como_ele(self):
        # O registo: 1 é o André, e o zeteste fica com o 2.
        zeteste = int(self.utilizador.criar("Zé Teste", "zeteste")["user_id"])
        m = self.cofre.modulo()
        cc = self.cofre.abrir()
        try:
            # A Ana nasceu no cofre (pela consola dele), com o número do zeteste.
            m.criar_conta(cc, "ana", "Ana", conta_id=zeteste)
            m.dar_acesso(cc, zeteste, "rift")
            m.definir_password(cc, zeteste, FRASE)
        finally:
            cc.close()
        con = self.auth.abrir()
        try:
            with self.assertRaises(self.auth.SenhaErrada) as certa:
                self.auth.entrar(con, "ana", FRASE, chave="1.1.1.1")
            with self.assertRaises(self.auth.SenhaErrada) as errada:
                self.auth.entrar(con, "ana", "nao-e-esta", chave="1.1.1.1")
        finally:
            con.close()
        self.assertEqual(str(certa.exception), str(errada.exception),
                         "a recusa não pode dizer que a password estava certa")

    def test_conta_do_cofre_sem_registo_nao_entra(self):
        m = self.cofre.modulo()
        cc = self.cofre.abrir()
        try:
            c = m.criar_conta(cc, "rui", "Rui", conta_id=500)
            m.dar_acesso(cc, c["conta_id"], "rift")
            m.definir_password(cc, c["conta_id"], FRASE)
        finally:
            cc.close()
        con = self.auth.abrir()
        try:
            with self.assertRaises(self.auth.SenhaErrada):
                self.auth.entrar(con, "rui", FRASE, chave="1.1.1.1")
        finally:
            con.close()


class TestApagarLimpaOCofre(Base):
    def _apagar(self, slug: str):
        from riftvault import conta
        importlib.reload(conta)
        conta.apagar(slug, confirmar=True, com_backup=False)

    def test_apagar_tira_a_conta_do_cofre_e_o_nome_volta_a_servir(self):
        uid = self.conta("zeteste")
        self._apagar("zeteste")
        m = self.cofre.modulo()
        cc = self.cofre.abrir()
        try:
            self.assertIsNone(m.por_id(cc, uid), "a conta ficou no cofre")
        finally:
            cc.close()
        # O nome pode voltar a ser usado — era aqui que rebentava.
        novo = int(self.utilizador.criar("Zé", "zeteste")["user_id"])
        con = self.auth.abrir()
        try:
            self.auth.nova_temporaria(con, novo)
        finally:
            con.close()

    def test_apagar_nao_tira_a_conta_a_quem_ainda_entra_no_mtg(self):
        uid = self.conta("zeteste")
        m = self.cofre.modulo()
        cc = self.cofre.abrir()
        try:
            m.dar_acesso(cc, uid, "mtg")
        finally:
            cc.close()
        self._apagar("zeteste")
        cc = self.cofre.abrir()
        try:
            self.assertIsNotNone(m.por_id(cc, uid))
            self.assertFalse(m.tem_acesso(cc, uid, "rift"))
            self.assertTrue(m.tem_acesso(cc, uid, "mtg"))
            self.assertTrue(m.estado_password(cc, uid)["tem"])
        finally:
            cc.close()

    def test_criar_pela_cli_falha_limpo_se_o_cofre_recusar(self):
        """O nome está tomado no cofre (uma conta só do mtg): sem utilizador a meio."""
        import contextlib
        import io
        from riftvault import cli
        importlib.reload(cli)
        m = self.cofre.modulo()
        cc = self.cofre.abrir()
        try:
            m.criar_conta(cc, "miguel", "Miguel do mtg", conta_id=77)
            m.dar_acesso(cc, 77, "mtg")
        finally:
            cc.close()
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            codigo = cli.main(["conta", "--criar", "miguel"])
        self.assertEqual(codigo, 1, out.getvalue() + err.getvalue())
        self.assertIn("miguel", err.getvalue())
        self.assertNotIn("Traceback", err.getvalue())
        self.assertNotIn("Password:", out.getvalue())
        self.assertIsNone(self.utilizador.por_slug("miguel", obrigatorio=False),
                          "ficou um utilizador criado a meio no registo")

    def test_criar_pela_cli_falha_limpo_com_qualquer_erro_do_cofre(self):
        """Um erro que não é de conta (a base trancada, um disco cheio) também
        desfaz o utilizador: nunca fica um no registo sem password."""
        import contextlib
        import io
        from unittest import mock
        from riftvault import cli
        importlib.reload(cli)
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(self.auth, "nova_temporaria",
                               side_effect=RuntimeError("o disco encheu")):
            with contextlib.redirect_stdout(out), \
                    contextlib.redirect_stderr(err):
                codigo = cli.main(["conta", "--criar", "miguel"])
        self.assertEqual(codigo, 1, out.getvalue() + err.getvalue())
        self.assertIn("miguel", err.getvalue())
        self.assertNotIn("Traceback", err.getvalue())
        self.assertNotIn("Password:", out.getvalue())
        self.assertIsNone(self.utilizador.por_slug("miguel", obrigatorio=False),
                          "ficou um utilizador criado a meio no registo")

    def test_criar_pela_cli_tira_do_cofre_o_que_la_ficou_a_meio(self):
        """A conta nasceu no cofre e a password falhou: sai do cofre também,
        senão o nome ficava tomado lá e o `--criar` seguinte recusava-o."""
        import contextlib
        import io
        from unittest import mock
        from riftvault import cli
        importlib.reload(cli)
        m = self.cofre.modulo()
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(m, "definir_password",
                               side_effect=RuntimeError("o disco encheu")):
            with contextlib.redirect_stdout(out), \
                    contextlib.redirect_stderr(err):
                codigo = cli.main(["conta", "--criar", "miguel"])
        self.assertEqual(codigo, 1, out.getvalue() + err.getvalue())
        self.assertNotIn("Traceback", err.getvalue())
        cc = self.cofre.abrir()
        try:
            self.assertIsNone(m.por_slug(cc, "miguel"),
                              "ficou uma conta a meio no cofre")
        finally:
            cc.close()


class TestALinhaDeArranque(Base):
    """O `serve` diz que cofre está a usar e quantas contas entram no rift —
    nunca quem são."""

    def test_diz_o_caminho_e_quantas_contas_tem_o_rift(self):
        self.conta("miguel")
        self.conta("zeteste", OUTRA)
        m = self.cofre.modulo()
        cc = self.cofre.abrir()
        try:
            c = m.criar_conta(cc, "soumtg", "Só do mtg")
            m.dar_acesso(cc, c["conta_id"], "mtg")
        finally:
            cc.close()
        linha = self.auth.linha_de_arranque()
        self.assertIn(str(self.cofre.caminho_db()), linha)
        self.assertIn("2 contas", linha)
        for slug in ("miguel", "zeteste", "soumtg"):
            self.assertNotIn(slug, linha)
        self.assertNotIn("scrypt$", linha)

    def test_cofre_que_nao_existe_diz_se_e_nao_se_cria(self):
        pasta = Path(tempfile.mkdtemp(prefix="riftvault-sem-cofre-"))
        os.environ["CONTAS_DB"] = str(pasta / "nao-ha" / "contas.db")
        linha = self.auth.linha_de_arranque()
        self.assertIn("não existe", linha.lower())
        self.assertIn(str(pasta / "nao-ha" / "contas.db"), linha)
        self.assertFalse((pasta / "nao-ha").exists(), "o arranque criou o cofre")

    def test_o_serve_imprime_a_linha(self):
        import contextlib
        import io
        from unittest import mock
        from riftvault import server
        importlib.reload(server)
        self.conta("miguel")
        out = io.StringIO()
        with mock.patch.object(server.app, "run"), \
                mock.patch.object(server, "lan_ips", return_value=["10.0.0.2"]), \
                mock.patch.object(server, "ascii_qr", return_value=""), \
                contextlib.redirect_stdout(out):
            server.serve(port=8999)
        self.assertIn(self.auth.linha_de_arranque(), out.getvalue())
        self.assertIn("1 conta ", out.getvalue())


class TestAGeracao(Base):
    def test_tirar_o_acesso_rift_mata_a_sessao(self):
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
                m.tirar_acesso(cc, uid, "rift")
            finally:
                cc.close()
            self.assertIsNone(self.auth.sessao(con, s["sid"]))
        finally:
            con.close()

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

"""ENTRAR COM PASSWORD, e a password a não aparecer em sítio nenhum.

Ordem dele, 2026-09-30: *"em vez de discord, nao era melhor a pessoa criar uma
conta com usuario e password e ficar guardado em base de dados??"* — e a
contraproposta que ele aceitou: *"pode ficar a tua sugestao de nova password, e
melhor"*, ou seja **ele nunca lê a password de ninguém**.

O que esta bateria fixa, e é a checklist da ordem:

  1. o KDF e as regras (`riftvault/senha.py`): scrypt com sal por pessoa, o
     hash auto-descritivo, a temporária, as regras da password nova;
  2. **A PROCURA DA PASSWORD EM CLARO** — na base, no `ops`, nos logs, no
     export da conta e nos backups. É o ponto 2 da checklist e o teste que
     interessa mais: escreve-se uma password conhecida e procura-se por ela em
     tudo o que fica em disco;
  3. os dois comandos dele (`--criar`, `--nova-password`) e a temporária a
     aparecer UMA vez;
  4. a troca obrigatória da temporária: com ela não se faz mais nada;
  5. **não há forma de criar uma conta sem ser pelo comando dele** — a rota de
     registo recusa, e prova-se que recusa;
  6. o travão de tentativas, com os números;
  7. o OAuth intacto e desligado;
  8. o `multi --verificar` sem exigir Discord.

Tudo contra pastas temporárias (`tests.fixture.Vault`) e um config temporário:
o `data/` e o `riftvault_config.json` a sério nunca são tocados.
"""

from __future__ import annotations

import importlib
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ["RIFTVAULT_CONFIG"] = str(
    Path(tempfile.gettempdir()) / "riftvault-nao-existe.json")

from tests.fixture import REPO, Vault  # noqa: E402

APP_JS = REPO / "riftvault" / "web" / "app.js"
CSS = REPO / "riftvault" / "web" / "style.css"

#: A password que se procura por tudo. Não é aleatória de propósito: é uma
#: cadeia improvável de aparecer por acidente num ficheiro binário, para o
#: varrimento dos bytes não dar falsos positivos nem falsos negativos.
SENTINELA = "zqx-segredo-do-miguel-742981"


class Base(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.close)
        os.environ["RIFTVAULT_AUTH"] = str(self.v.data / "auth.db")
        self.addCleanup(lambda: os.environ.pop("RIFTVAULT_AUTH", None))
        os.environ.pop("RIFTVAULT_ENSAIO", None)
        os.environ.pop("RIFTVAULT_USER", None)

        from riftvault import (abrir, auth, config, db, metrics, multi,
                               privacidade, rotas_conta, senha, utilizador)
        for m in (config, db, utilizador, multi, privacidade, senha, auth,
                  rotas_conta, abrir, metrics):
            importlib.reload(m)
        self.auth, self.senha, self.multi, self.abrir = auth, senha, multi, abrir
        self.utilizador, self.config, self.db = utilizador, config, db
        self.rotas_conta = rotas_conta
        self.cfg({})

    def cfg(self, extra: dict):
        caminho = self.v.root / "config.json"
        caminho.write_text(json.dumps(extra), encoding="utf-8")
        os.environ["RIFTVAULT_CONFIG"] = str(caminho)
        importlib.reload(self.config)
        self.config.load.cache_clear()

        def repor():
            os.environ["RIFTVAULT_CONFIG"] = str(
                Path(tempfile.gettempdir()) / "riftvault-nao-existe.json")
            importlib.reload(self.config)
            self.config.load.cache_clear()

        self.addCleanup(repor)

    def catalogo(self):
        """Uma carta, uma vez. (Alguns testes levantam dois clientes.)"""
        con = self.v.connect()
        if not con.execute("SELECT 1 FROM catalog.printings "
                           "WHERE printing_id = 'tst-001-100'").fetchone():
            self.v.add_printing(con, "tst-001-100", "TST", 1, "Defy",
                                rarity="common", size=100)
            self.v.rebuild(con)
        return con

    def cliente(self, aberto: bool = True, **extra):
        self.cfg({"multi": {"aberto": aberto}, **extra})
        con = self.catalogo()
        con.close()
        from riftvault import server
        importlib.reload(server)
        server.app.testing = True
        return server.app.test_client()

    # -- ajudas -----------------------------------------------------------

    def conta_nova(self, slug: str, nome: str = "") -> tuple[int, str]:
        """Uma conta como ELE a cria: pela app, com uma temporária. -> (id, pass)."""
        u = self.utilizador.criar(nome or slug, slug)
        con = self.auth.abrir()
        try:
            password = self.auth.nova_temporaria(con, int(u["user_id"]))
        finally:
            con.close()
        return int(u["user_id"]), password

    def com_senha(self, slug: str, password: str, nome: str = "") -> int:
        """Uma conta já com a password DELA (não temporária)."""
        uid, _tmp = self.conta_nova(slug, nome)
        con = self.auth.abrir()
        try:
            self.auth.definir_senha(con, uid, password, temporaria=False)
        finally:
            con.close()
        return uid

    def entrar(self, c, slug: str, password: str) -> str:
        r = c.post("/api/conta/entrar", json={"nome": slug, "senha": password})
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True)[:400])
        return r.get_json()["csrf"]


# --------------------------------------------------------------------------
# 1. O KDF E AS REGRAS
# --------------------------------------------------------------------------


class TestOKdf(Base):
    """Pergunta 1 da checklist: que KDF, com que parâmetros, e porquê."""

    def test_e_scrypt_da_biblioteca_padrao(self):
        import hashlib
        self.assertEqual(self.senha.ALGORITMO, "scrypt")
        self.assertTrue(hasattr(hashlib, "scrypt"),
                        "o scrypt tem de vir da stdlib — sem dependências novas")

    def test_os_parametros_sao_os_medidos(self):
        """130 ms na máquina dele. Baixá-los é uma decisão, não um descuido."""
        self.assertEqual((self.senha.N, self.senha.R, self.senha.P),
                         (2 ** 16, 8, 1))
        self.assertGreaterEqual(self.senha.SAL_BYTES, 16)
        self.assertGreaterEqual(self.senha.DKLEN, 32)

    def test_o_maxmem_vai_explicito(self):
        """A armadilha medida: o OpenSSL só dá 32 MB por omissão e n=2**16 quer 67."""
        self.assertGreater(self.senha._maxmem(2 ** 16, 8, 1), 128 * 2 ** 16 * 8)
        # E a prova pela negativa: sem o argumento, isto rebentava.
        import hashlib
        with self.assertRaises((ValueError, MemoryError)):
            hashlib.scrypt(b"x", salt=b"y" * 16, n=2 ** 16, r=8, p=1, dklen=32)

    def test_o_hash_diz_como_foi_feito(self):
        h = self.senha.cifrar("uma-password-qualquer")
        self.assertTrue(h.startswith("scrypt$65536$8$1$"))
        self.assertEqual(len(h.split("$")), 6)

    def test_o_sal_e_por_pessoa(self):
        """Duas pessoas com a mesma password têm hashes diferentes."""
        a = self.senha.cifrar("a-mesma-password")
        b = self.senha.cifrar("a-mesma-password")
        self.assertNotEqual(a, b)
        self.assertTrue(self.senha.confere(a, "a-mesma-password"))
        self.assertTrue(self.senha.confere(b, "a-mesma-password"))

    def test_confere_o_certo_e_recusa_o_errado(self):
        h = self.senha.cifrar("a-certa-e-esta")
        self.assertTrue(self.senha.confere(h, "a-certa-e-esta"))
        for errada in ("a-certa-e-est", "a-certa-e-estb", "", "A-CERTA-E-ESTA"):
            self.assertFalse(self.senha.confere(h, errada), errada)

    def test_um_hash_estragado_nao_rebenta_devolve_falso(self):
        for lixo in ("", "nao-e-um-hash", "scrypt$x$8$1$aa$bb", "a$b$c$d$e$f"):
            self.assertFalse(self.senha.confere(lixo, "qualquer"))

    def test_uma_password_antiga_continua_a_entrar_e_e_recifrada(self):
        """Subir o custo não pode trancar ninguém de fora."""
        velho = self.senha.cifrar("a-minha-password", n=2 ** 14)
        self.assertTrue(self.senha.confere(velho, "a-minha-password"))
        self.assertTrue(self.senha.precisa_recifrar(velho))
        self.assertFalse(self.senha.precisa_recifrar(
            self.senha.cifrar("a-minha-password")))

    def test_entrar_recifra_sozinho(self):
        uid = self.com_senha("miguel", SENTINELA)
        con = self.auth.abrir()
        try:
            # Finge-se uma password cifrada à antiga, como se fosse de 2026.
            con.execute("UPDATE user_senha SET hash = ? WHERE user_id = ?",
                        (self.senha.cifrar(SENTINELA, n=2 ** 14), uid))
            con.commit()
            self.auth.entrar(con, "miguel", SENTINELA, chave="1.2.3.4")
            novo = con.execute("SELECT hash FROM user_senha WHERE user_id = ?",
                               (uid,)).fetchone()["hash"]
        finally:
            con.close()
        self.assertFalse(self.senha.precisa_recifrar(novo),
                         "entrou e não foi recifrada")


class TestATemporaria(Base):
    def test_e_forte_e_facil_de_ditar(self):
        self.assertEqual(len(self.senha.PALAVRAS), 256)
        self.assertEqual(len(set(self.senha.PALAVRAS)), 256)
        import re
        for p in self.senha.PALAVRAS:
            self.assertRegex(p, r"^[a-z]{3,6}$",
                             f"«{p}» tem de ser ASCII, 3 a 6 letras")
        self.assertGreater(self.senha.BITS, 38)

    def test_sao_quatro_palavras_e_dois_digitos(self):
        import re
        vistas = set()
        for _ in range(40):
            t = self.senha.temporaria()
            self.assertRegex(t, r"^[a-z]+(-[a-z]+){3}-\d\d$", t)
            vistas.add(t)
        self.assertGreater(len(vistas), 35, "duas gerações iguais é suspeito")


class TestAsRegrasDaPasswordNova(Base):
    """Comprimento decente, sem teatro de complexidade."""

    def test_o_minimo_e_dez(self):
        self.assertEqual(self.senha.MINIMO, 10)
        with self.assertRaises(self.senha.SenhaFraca):
            self.senha.validar("123456789")
        self.senha.validar("uma-frase-qualquer")

    def test_nao_exige_maiuscula_digito_nem_simbolo(self):
        """A regra que produz `Password1!` e um post-it no monitor."""
        self.senha.validar("o meu gato dorme muito")
        self.senha.validar("abcdefghijk")

    def test_recusa_as_obvias(self):
        for m in ("password12345", "1234567890", "qwertyuiop"):
            with self.assertRaises(self.senha.SenhaFraca, msg=m):
                self.senha.validar(m)

    def test_recusa_o_proprio_nome(self):
        with self.assertRaises(self.senha.SenhaFraca):
            self.senha.validar("miguel-e-bonito", slug="miguel")
        with self.assertRaises(self.senha.SenhaFraca):
            self.senha.validar("aMiguelSilva123", nome="Miguel Silva")

    def test_recusa_um_caractere_repetido(self):
        with self.assertRaises(self.senha.SenhaFraca):
            self.senha.validar("aaaaaaaaaaaaaa")

    def test_recusa_espacos_nas_pontas(self):
        """Perdem-se ao copiar e colar, e depois ela não entra e não sabe porquê."""
        with self.assertRaises(self.senha.SenhaFraca):
            self.senha.validar(" uma frase boa ")

    def test_nao_normaliza_a_password_escolhida(self):
        """Mudá-la em silêncio era fazê-la não entrar com o que escreveu."""
        escolhida = "A Minha Frase  Com Espacos"
        self.assertEqual(self.senha.validar(escolhida), escolhida)

    def test_a_mensagem_e_em_portugues_e_diz_o_que_fazer(self):
        try:
            self.senha.validar("curta")
        except self.senha.SenhaFraca as e:
            self.assertIn("pelo menos 10", str(e))
            self.assertIn("frase", str(e))


# --------------------------------------------------------------------------
# 2. A PROCURA DA PASSWORD EM CLARO — o teste que interessa mais
# --------------------------------------------------------------------------


def _bytes_de(p: Path) -> bytes:
    try:
        return p.read_bytes()
    except OSError:
        return b""


class TestNuncaEmClaro(Base):
    """Pergunta 2 da checklist: procuraste a password em claro em todo o lado?

    A forma é sempre a mesma: escreve-se uma password CONHECIDA (a
    `SENTINELA`), faz-se o que se faz com uma password, e depois **varrem-se os
    bytes** de tudo o que ficou em disco à procura dela. Se aparecer, o teste
    falha e diz em que ficheiro.

    Varre-se em UTF-8 e em UTF-16: o `sqlite3` guarda texto em UTF-8, mas um
    log escrito por outra via em Windows podia ficar em UTF-16 e passar
    despercebido a uma procura só.
    """

    def _procurar(self, onde: Path) -> list[str]:
        agulhas = [SENTINELA.encode("utf-8"), SENTINELA.encode("utf-16-le")]
        achados = []
        if onde.is_file():
            ficheiros = [onde]
        else:
            ficheiros = [p for p in onde.rglob("*") if p.is_file()]
        for f in ficheiros:
            dados = _bytes_de(f)
            if any(a in dados for a in agulhas):
                achados.append(str(f))
        return achados

    def _mexer_com_tudo(self):
        """Faz o percurso todo de uma password: criar, entrar, trocar, apagar."""
        c = self.cliente(aberto=True)
        uid = self.com_senha("miguel", SENTINELA, "Miguel")
        csrf = self.entrar(c, "miguel", SENTINELA)
        # escreve na coleção (para haver `ops` e ficheiros do utilizador)
        c.post("/api/adjust", json={"printing_id": "tst-001-100", "delta": 2},
               headers={"X-CSRF-Token": csrf})
        # troca a password: a antiga e a nova passam as duas pelo servidor
        r = c.post("/api/conta/senha",
                   json={"atual": SENTINELA, "nova": "outra-frase-comprida"},
                   headers={"X-CSRF-Token": csrf})
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True)[:300])
        # e uma tentativa ERRADA com a sentinela (é o caso que mais tenta
        # escrever no registo de tentativas)
        c.post("/api/conta/entrar", json={"nome": "miguel", "senha": SENTINELA})
        return c, uid

    def test_nao_esta_na_base_das_credenciais(self):
        self._mexer_com_tudo()
        achados = self._procurar(Path(os.environ["RIFTVAULT_AUTH"]))
        self.assertEqual(achados, [], "a password está no auth.db EM CLARO")

    def test_nao_esta_na_base_da_colecao_nem_no_ops(self):
        self._mexer_com_tudo()
        # A `copies`/`ops` do utilizador e a base do André, as duas.
        for vault in self.v.data.rglob("vault.db"):
            self.assertEqual(self._procurar(vault), [],
                             f"a password está em {vault}")
        con = self.v.connect()
        try:
            texto = "\n".join(
                str(r) for r in con.execute("SELECT * FROM ops"))
        finally:
            con.close()
        self.assertNotIn(SENTINELA, texto, "a password está na tabela `ops`")

    def test_nao_esta_em_ficheiro_nenhum_da_pasta_de_dados(self):
        """O varrimento largo: TUDO o que ficou em disco, logs e backups."""
        self._mexer_com_tudo()
        achados = self._procurar(self.v.data)
        self.assertEqual(achados, [],
                         "a password aparece nestes ficheiros: " + str(achados))

    def test_nao_esta_no_export_da_conta(self):
        """Um export manda-se por email — não pode levar credenciais."""
        from riftvault import conta
        importlib.reload(conta)
        c, _uid = self._mexer_com_tudo()
        r = conta.exportar("miguel")
        zipe = Path(r["ficheiro"])
        self.assertEqual(self._procurar(zipe), [],
                         "a password está dentro do .zip do export")
        # E o que está lá dentro, descomprimido (um zip guarda comprimido e
        # uma procura nos bytes podia não a ver).
        import zipfile
        with zipfile.ZipFile(zipe) as z:
            for nome in z.namelist():
                self.assertNotIn(SENTINELA.encode(), z.read(nome),
                                 f"a password está em {nome}")

    def test_nao_esta_num_backup(self):
        """Os backups são cópias da base — se a base está limpa, eles também."""
        self._mexer_com_tudo()
        con = self.v.connect()
        try:
            self.db.backup(con, "prova-senhas")
        finally:
            con.close()
        achados = self._procurar(self.v.data / "backups")
        self.assertEqual(achados, [], "a password está num backup")

    def test_a_procura_apanha_mesmo_uma_password_em_claro(self):
        """A PROVA PELA NEGATIVA: um varrimento que nunca acha nada vale zero.

        Escreve-se a sentinela à mão numa tabela do `auth.db` e exige-se que o
        varrimento a encontre. Sem isto, os cinco testes de cima passavam mesmo
        que a procura estivesse a olhar para o sítio errado.
        """
        con = self.auth.abrir()
        try:
            con.execute("INSERT INTO auth_tentativas (ts, chave, provedor, ok) "
                        "VALUES ('agora', ?, 'senha', 0)", (SENTINELA,))
            con.commit()
        finally:
            con.close()
        achados = self._procurar(Path(os.environ["RIFTVAULT_AUTH"]))
        self.assertTrue(achados, "a procura não encontra uma password em claro")

    def test_o_registo_de_tentativas_nao_guarda_o_que_se_escreveu(self):
        """Uma tabela de tentativas com a password tentada é uma tabela de
        passwords com outro nome: quem se engana escreve a de outro sítio."""
        con = self.auth.abrir()
        try:
            colunas = {r["name"] for r in
                       con.execute("PRAGMA table_info(auth_tentativas)")}
        finally:
            con.close()
        self.assertEqual(
            colunas, {"id", "ts", "chave", "provedor", "ok", "user_id"},
            "há uma coluna nova no registo de tentativas — confirma que não é "
            "a password")

    def test_o_esconder_nao_deixa_escapar_um_pedaco(self):
        self.assertNotIn(SENTINELA, self.senha.esconder(SENTINELA))
        self.assertNotIn(SENTINELA[:3], self.senha.esconder(SENTINELA))
        self.assertNotIn(str(len(SENTINELA)), self.senha.esconder(SENTINELA))

    def test_o_estado_da_senha_nao_devolve_o_hash(self):
        """Uma função que devolvesse o hash acabava um dia num payload."""
        uid = self.com_senha("miguel", SENTINELA)
        con = self.auth.abrir()
        try:
            e = self.auth.estado_senha(con, uid)
        finally:
            con.close()
        self.assertEqual(set(e), {"tem", "temporaria", "criado_em", "mudado_em"})

    def test_o_payload_da_conta_nao_leva_hash_nem_password(self):
        c = self.cliente(aberto=True)
        self.com_senha("miguel", SENTINELA, "Miguel")
        self.entrar(c, "miguel", SENTINELA)
        bruto = c.get("/api/conta.json").get_data(as_text=True)
        self.assertNotIn(SENTINELA, bruto)
        self.assertNotIn("scrypt", bruto)
        self.assertNotIn("hash", bruto)


# --------------------------------------------------------------------------
# 3. OS DOIS COMANDOS DELE
# --------------------------------------------------------------------------


class TestOsComandos(Base):
    """Pergunta 3: os dois comandos existem e imprimem a temporária uma vez?"""

    def _cli(self, *args) -> tuple[int, str, str]:
        import contextlib
        import io
        from riftvault import cli
        importlib.reload(cli)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            codigo = cli.main(list(args))
        return codigo, out.getvalue(), err.getvalue()

    def test_criar_cria_a_conta_e_diz_uma_temporaria(self):
        codigo, out, _err = self._cli("conta", "--criar", "miguel",
                                      "--nome", "Miguel")
        self.assertEqual(codigo, 0, out)
        self.assertIn("Conta criada: miguel", out)
        self.assertIn("Utilizador: miguel", out)
        # A password impressa é a que entra.
        import re
        m = re.search(r"Password:\s+(\S+)", out)
        self.assertIsNotNone(m, out)
        password = m.group(1)
        self.assertRegex(password, r"^[a-z]+(-[a-z]+){3}-\d\d$")
        u = self.utilizador.por_slug("miguel")
        con = self.auth.abrir()
        try:
            quem = self.auth.entrar(con, "miguel", password, chave="1.1.1.1")
            self.assertEqual(quem["user_id"], int(u["user_id"]))
            self.assertTrue(quem["temporaria"], "nasce temporária")
        finally:
            con.close()

    def test_criar_aceita_as_duas_escritas(self):
        c1, out1, _ = self._cli("conta", "--criar", "miguel")
        c2, out2, _ = self._cli("conta", "joao", "--criar")
        self.assertEqual((c1, c2), (0, 0), out1 + out2)
        self.assertIn("Conta criada: joao", out2)

    def test_criar_recusa_um_nome_tomado_e_um_nome_reservado(self):
        self._cli("conta", "--criar", "miguel")
        codigo, _out, err = self._cli("conta", "--criar", "miguel")
        self.assertEqual(codigo, 1)
        self.assertIn("já há uma conta", err)
        codigo, _out, err = self._cli("conta", "--criar", "admin")
        self.assertEqual(codigo, 1)
        self.assertIn("reservado", err)

    def test_nova_password_da_outra_e_a_antiga_deixa_de_servir(self):
        _uid, primeira = self.conta_nova("miguel")
        codigo, out, _err = self._cli("conta", "miguel", "--nova-password")
        self.assertEqual(codigo, 0, out)
        self.assertIn("Password nova: miguel", out)
        import re
        segunda = re.search(r"Password:\s+(\S+)", out).group(1)
        self.assertNotEqual(primeira, segunda)
        con = self.auth.abrir()
        try:
            with self.assertRaises(self.auth.SenhaErrada):
                self.auth.entrar(con, "miguel", primeira, chave="9.9.9.9")
            self.auth.entrar(con, "miguel", segunda, chave="8.8.8.8")
        finally:
            con.close()

    def test_nova_password_fecha_as_sessoes_dela(self):
        """Se ela pediu outra porque perdeu o telemóvel, o telemóvel sai."""
        c = self.cliente(aberto=True)
        uid = self.com_senha("miguel", SENTINELA)
        self.entrar(c, "miguel", SENTINELA)
        self.assertTrue(c.get("/api/conta.json").get_json()["entrado"])
        self._cli("conta", "miguel", "--nova-password")
        self.assertFalse(c.get("/api/conta.json").get_json()["entrado"],
                         "a sessão antiga continuou a valer")

    def test_nova_password_do_ANDRE(self):
        """Pergunta 15: o comando exacto que ele corre para si próprio."""
        codigo, out, _err = self._cli("conta", "baverone", "--nova-password")
        self.assertEqual(codigo, 0, out)
        self.assertIn("Password nova: baverone", out)
        con = self.auth.abrir()
        try:
            self.assertTrue(self.auth.estado_senha(con, 1)["tem"])
        finally:
            con.close()

    def test_a_lista_diz_o_estado_da_password_e_nunca_a_password(self):
        self.conta_nova("miguel")
        self.com_senha("joao", "a-password-do-joao")
        _codigo, out, _err = self._cli("conta")
        self.assertIn("temporária, por trocar", out)
        self.assertIn("password definida", out)
        self.assertIn("SEM PASSWORD", out, "o André ainda não tem")
        self.assertNotIn("a-password-do-joao", out)
        self.assertNotIn("scrypt", out)

    def test_os_comandos_funcionam_com_a_PORTA_FECHADA(self):
        """Ele prepara as contas e só depois abre."""
        self.cfg({"multi": {"aberto": False}})
        codigo, out, err = self._cli("conta", "--criar", "miguel")
        self.assertEqual(codigo, 0, out + err)
        self.assertIn("FECHADA", err, "tem de avisar que ela ainda não entra")


# --------------------------------------------------------------------------
# 4. A TROCA OBRIGATÓRIA DA TEMPORÁRIA
# --------------------------------------------------------------------------


class TestATemporariaTrancaTudo(Base):
    """Pergunta 4: a troca está imposta? O que acontece a quem tente outra rota?"""

    def setUp(self):
        super().setUp()
        self.c = self.cliente(aberto=True)
        self.uid, self.tmp = self.conta_nova("miguel", "Miguel")
        self.csrf = self.entrar(self.c, "miguel", self.tmp)

    def test_entra_e_o_payload_diz_que_e_temporaria(self):
        d = self.c.get("/api/conta.json").get_json()
        self.assertTrue(d["entrado"])
        self.assertTrue(d["senha_temporaria"])
        self.assertFalse(d["editavel"],
                         "com a temporária os +/− não se podem mostrar")

    def test_nao_escreve_em_lado_nenhum(self):
        r = self.c.post("/api/adjust",
                        json={"printing_id": "tst-001-100", "delta": 1},
                        headers={"X-CSRF-Token": self.csrf})
        self.assertEqual(r.status_code, 403)
        self.assertIn("password temporária", r.get_json()["erro"])

    def test_nem_LE_a_coleccao(self):
        """A temporária andou pelo WhatsApp: quem a apanhe não lê nada."""
        for rota in ("/api/index.json", "/api/set/TST.json", "/api/decks.json",
                     "/api/venda.json", "/api/selado.json"):
            r = self.c.get(rota)
            self.assertEqual(r.status_code, 403, f"{rota} deixou ler")

    def test_as_rotas_de_escrita_TODAS_recusam(self):
        from tests.test_contas import ESCRITAS
        maus = []
        for rota in ESCRITAS:
            r = self.c.post(rota, json={}, headers={"X-CSRF-Token": self.csrf})
            if r.status_code != 403:
                maus.append(f"{rota} -> {r.status_code}")
        self.assertEqual(maus, [])

    def test_o_que_PASSA_e_so_o_necessario_para_trocar(self):
        """A página tem de poder desenhar-se, e o /sair tem de funcionar."""
        self.assertEqual(self.c.get("/").status_code, 200)
        self.assertEqual(self.c.get("/app.js").status_code, 200)
        self.assertEqual(self.c.get("/api/conta.json").status_code, 200)
        self.assertEqual(self.c.get("/sair").status_code, 302)

    def test_trocar_a_temporaria_liberta_o_site(self):
        r = self.c.post("/api/conta/senha",
                        json={"atual": self.tmp, "nova": "a-minha-frase-nova"},
                        headers={"X-CSRF-Token": self.csrf})
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True)[:300])
        novo = r.get_json()["csrf"]
        d = self.c.get("/api/conta.json").get_json()
        self.assertFalse(d["senha_temporaria"])
        self.assertTrue(d["editavel"])
        r = self.c.post("/api/adjust",
                        json={"printing_id": "tst-001-100", "delta": 2},
                        headers={"X-CSRF-Token": novo})
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True)[:300])
        self.assertEqual(r.get_json()["qty"], 2)

    def test_a_troca_exige_a_actual(self):
        r = self.c.post("/api/conta/senha",
                        json={"atual": "nao-e-esta", "nova": "uma-frase-nova"},
                        headers={"X-CSRF-Token": self.csrf})
        self.assertEqual(r.status_code, 403)
        self.assertIn("actual", r.get_json()["erro"])

    def test_a_troca_aplica_as_regras(self):
        r = self.c.post("/api/conta/senha",
                        json={"atual": self.tmp, "nova": "curta"},
                        headers={"X-CSRF-Token": self.csrf})
        self.assertEqual(r.status_code, 400)
        self.assertIn("10 caracteres", r.get_json()["erro"])

    def test_a_troca_exige_csrf(self):
        r = self.c.post("/api/conta/senha",
                        json={"atual": self.tmp, "nova": "uma-frase-nova"})
        self.assertEqual(r.status_code, 403)
        self.assertIn("CSRF", r.get_json()["erro"])

    def test_a_troca_fecha_as_outras_sessoes(self):
        outro = self.cliente(aberto=True)
        # o mesmo utilizador, noutro dispositivo
        outro.post("/api/conta/entrar",
                   json={"nome": "miguel", "senha": self.tmp})
        self.assertTrue(outro.get("/api/conta.json").get_json()["entrado"])
        self.c.post("/api/conta/senha",
                    json={"atual": self.tmp, "nova": "a-minha-frase-nova"},
                    headers={"X-CSRF-Token": self.csrf})
        self.assertFalse(outro.get("/api/conta.json").get_json()["entrado"])

    def test_a_nova_nao_pode_ser_a_mesma(self):
        r = self.c.post("/api/conta/senha",
                        json={"atual": self.tmp, "nova": self.tmp},
                        headers={"X-CSRF-Token": self.csrf})
        self.assertEqual(r.status_code, 400)


# --------------------------------------------------------------------------
# 5. NÃO HÁ COMO CRIAR UMA CONTA SEM SER PELO COMANDO DELE
# --------------------------------------------------------------------------


class TestSemRegistoAberto(Base):
    """Pergunta 5: provaste que não há outra forma de criar conta?"""

    def test_o_interruptor_esta_desligado(self):
        self.assertFalse(self.rotas_conta.REGISTO_ABERTO)

    def test_a_rota_de_registo_recusa_e_diz_o_que_fazer(self):
        c = self.cliente(aberto=True)
        r = c.post("/api/conta/registar", json={"slug": "intruso"})
        self.assertEqual(r.status_code, 403)
        self.assertIn("André", r.get_json()["erro"])
        self.assertIsNone(self.utilizador.por_slug("intruso", obrigatorio=False))

    def test_nem_com_uma_sessao_de_fornecedor(self):
        """O caminho de 29/09: entrar pelo Discord e escolher um slug."""
        from riftvault import multi
        os.environ["RIFTVAULT_ENSAIO"] = "1"
        self.addCleanup(lambda: os.environ.pop("RIFTVAULT_ENSAIO", None))
        importlib.reload(self.config)
        self.config.load.cache_clear()
        importlib.reload(multi)
        importlib.reload(self.auth)
        c = self.cliente(aberto=True)
        r = c.get("/entrar/local?sub=um-estranho")
        self.assertEqual(r.status_code, 302)
        d = c.get("/api/conta.json").get_json()
        self.assertIn("sem_conta", d, "devia dizer-lhe que não tem conta")
        self.assertNotIn("registo_pendente", d)
        r = c.post("/api/conta/registar", json={"slug": "intruso"},
                   headers={"X-CSRF-Token": d["csrf"]})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(len(self.utilizador.todos()), 1, "só o André")

    def test_a_unica_porta_e_a_do_utilizador(self):
        """Varre o código: quem cria utilizadores é o `utilizador.criar`, e
        quem o chama nas rotas é o registo (fechado) e mais ninguém."""
        fonte = (REPO / "riftvault" / "rotas_conta.py").read_text(encoding="utf-8")
        chamadas = [l.strip() for l in fonte.splitlines()
                    if "utilizador.criar" in l]
        self.assertEqual(len(chamadas), 1,
                         f"há mais do que um sítio a criar contas: {chamadas}")

    def test_o_js_nao_mostra_formulario_de_registo(self):
        js = APP_JS.read_text(encoding="utf-8")
        self.assertIn("c.sem_conta", js)
        self.assertIn("é o André que as cria", js)


# --------------------------------------------------------------------------
# 6. O TRAVÃO DE TENTATIVAS
# --------------------------------------------------------------------------


class TestOTravao(Base):
    """Pergunta 6: que limites, e porque esses números?"""

    def test_os_numeros_sao_os_escritos(self):
        self.assertEqual(self.auth.FALHAS_LIVRES_CONTA, 5)
        self.assertEqual(self.auth.FALHAS_LIVRES_CHAVE, 10)
        self.assertEqual(self.auth.ESCADA, (60, 300, 900, 3600))

    def test_a_escada_sobe_e_fica_no_tecto(self):
        """Corre ANTES da tentativa: com 4 falhas a 5.ª ainda passa, com 5 não."""
        e = self.auth._espera
        self.assertEqual(e(4, 5), 0)
        self.assertEqual(e(5, 5), 60)
        self.assertEqual(e(6, 5), 300)
        self.assertEqual(e(7, 5), 900)
        self.assertEqual(e(8, 5), 3600)
        self.assertEqual(e(99, 5), 3600, "não sobe para sempre")

    def test_cinco_erros_na_mesma_conta_ainda_deixam_tentar(self):
        """Uma password ditada pelo WhatsApp escreve-se mal duas ou três vezes."""
        self.com_senha("miguel", SENTINELA)
        con = self.auth.abrir()
        try:
            for i in range(5):
                with self.assertRaises(self.auth.SenhaErrada, msg=str(i)):
                    self.auth.entrar(con, "miguel", "errada", chave="1.1.1.1")
            # à sexta trava
            with self.assertRaises(self.auth.TemDeEsperar) as ctx:
                self.auth.entrar(con, "miguel", "errada", chave="1.1.1.1")
            self.assertIn("nesta conta", str(ctx.exception))
            # e trava a password CERTA também — senão o travão não travava nada
            with self.assertRaises(self.auth.TemDeEsperar):
                self.auth.entrar(con, "miguel", SENTINELA, chave="1.1.1.1")
        finally:
            con.close()

    def test_muitos_enderecos_nao_libertam_a_conta(self):
        """É a razão de o travão contar por CONTA e não só por endereço."""
        self.com_senha("miguel", SENTINELA)
        con = self.auth.abrir()
        try:
            for i in range(6):
                try:
                    self.auth.entrar(con, "miguel", "errada",
                                     chave=f"10.0.0.{i}")
                except self.auth.ErroDeAutenticacao:
                    pass
            with self.assertRaises(self.auth.TemDeEsperar):
                self.auth.entrar(con, "miguel", SENTINELA, chave="10.0.0.99")
        finally:
            con.close()

    def test_o_travao_por_endereco_apanha_quem_varre_nomes(self):
        """Tentar dez nomes diferentes de um sítio conta como dez falhas dele."""
        con = self.auth.abrir()
        try:
            for i in range(11):
                try:
                    self.auth.entrar(con, f"nao-existe-{i}", "x",
                                     chave="7.7.7.7")
                except self.auth.ErroDeAutenticacao:
                    pass
            with self.assertRaises(self.auth.TemDeEsperar) as ctx:
                self.auth.entrar(con, "outro", "x", chave="7.7.7.7")
            self.assertIn("deste sítio", str(ctx.exception))
        finally:
            con.close()

    def test_uma_entrada_certa_nao_conta_como_falha(self):
        self.com_senha("miguel", SENTINELA)
        con = self.auth.abrir()
        try:
            for _ in range(8):
                self.auth.entrar(con, "miguel", SENTINELA, chave="2.2.2.2")
        finally:
            con.close()

    def test_a_rota_responde_429_e_diz_quanto_esperar(self):
        c = self.cliente(aberto=True)
        self.com_senha("miguel", SENTINELA)
        for _ in range(6):
            c.post("/api/conta/entrar",
                   json={"nome": "miguel", "senha": "errada"})
        r = c.post("/api/conta/entrar",
                   json={"nome": "miguel", "senha": SENTINELA})
        self.assertEqual(r.status_code, 429)
        self.assertIn("Espera", r.get_json()["erro"])

    def test_o_travao_corre_ANTES_do_scrypt(self):
        """Verificar primeiro fazia cada tentativa custar 130 ms — era isso que
        punha o PC dele de joelhos."""
        fonte = (REPO / "riftvault" / "auth.py").read_text(encoding="utf-8")
        corpo = fonte.split("def entrar(")[1].split("\ndef ")[0]
        self.assertLess(corpo.index("travao(con"), corpo.index("confere("),
                        "o travão tem de correr antes do scrypt")

    def test_nao_ha_bloqueio_para_sempre(self):
        """Um bloqueio permanente dava a um estranho a maneira de tirar o
        riftvault a um amigo só por lhe saber o nome."""
        self.assertLessEqual(max(self.auth.ESCADA), 3600)

    def test_a_mesma_mensagem_para_nome_errado_e_password_errada(self):
        """Mensagens diferentes diziam a um estranho que nomes existem."""
        c = self.cliente(aberto=True)
        self.com_senha("miguel", SENTINELA)
        a = c.post("/api/conta/entrar",
                   json={"nome": "miguel", "senha": "errada"})
        b = c.post("/api/conta/entrar",
                   json={"nome": "nao-existe", "senha": "errada"})
        self.assertEqual(a.status_code, b.status_code)
        self.assertEqual(a.get_json()["erro"], b.get_json()["erro"])

    def test_uma_troca_de_password_falhada_conta_como_falha(self):
        c = self.cliente(aberto=True)
        self.com_senha("miguel", SENTINELA)
        csrf = self.entrar(c, "miguel", SENTINELA)
        for _ in range(6):
            c.post("/api/conta/senha",
                   json={"atual": "errada", "nova": "uma-frase-nova"},
                   headers={"X-CSRF-Token": csrf})
        con = self.auth.abrir()
        try:
            with self.assertRaises(self.auth.TemDeEsperar):
                self.auth.entrar(con, "miguel", SENTINELA, chave="1.1.1.1")
        finally:
            con.close()


# --------------------------------------------------------------------------
# 7. A ENTRADA, E O QUE A PROTEGE
# --------------------------------------------------------------------------


class TestAEntrada(Base):
    def test_entra_e_fica_com_sessao(self):
        c = self.cliente(aberto=True)
        self.com_senha("miguel", SENTINELA, "Miguel")
        r = c.post("/api/conta/entrar",
                   json={"nome": "miguel", "senha": SENTINELA})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["slug"], "miguel")
        self.assertFalse(r.get_json()["senha_temporaria"])
        d = c.get("/api/conta.json").get_json()
        self.assertTrue(d["entrado"])
        self.assertTrue(d["editavel"])

    def test_o_cookie_tem_as_propriedades(self):
        c = self.cliente(aberto=True)
        self.com_senha("miguel", SENTINELA)
        r = c.post("/api/conta/entrar",
                   json={"nome": "miguel", "senha": SENTINELA})
        bruto = "; ".join(r.headers.getlist("Set-Cookie"))
        self.assertIn("HttpOnly", bruto)
        self.assertIn("SameSite=Lax", bruto)
        self.assertIn("Path=/", bruto)

    def test_o_valor_do_cookie_nao_esta_na_base(self):
        """Na base fica o SHA-256 — quem leia o ficheiro não entra com ele."""
        c = self.cliente(aberto=True)
        self.com_senha("miguel", SENTINELA)
        c.post("/api/conta/entrar", json={"nome": "miguel", "senha": SENTINELA})
        sid = next(x.value for x in c.cookie_jar
                   if x.key == self.auth.COOKIE) if hasattr(c, "cookie_jar") \
            else c.get_cookie(self.auth.COOKIE).value
        bruto = Path(os.environ["RIFTVAULT_AUTH"]).read_bytes()
        self.assertNotIn(sid.encode(), bruto)

    def test_exige_JSON_para_travar_o_login_de_outro_site(self):
        """Um `<form>` de outro site não consegue mandar JSON — é o que impede
        alguém de fazer o browser dele entrar numa conta que não é a dele."""
        c = self.cliente(aberto=True)
        self.com_senha("miguel", SENTINELA)
        r = c.post("/api/conta/entrar",
                   data={"nome": "miguel", "senha": SENTINELA})
        self.assertEqual(r.status_code, 415)

    def test_com_a_porta_fechada_ENTRA_SE(self):
        """Mudou a 2026-09-30, à tarde: este teste FIXAVA O BECO.

        Recusar aqui era o ciclo — o `multi --verificar` exige trocar a
        temporária antes de abrir, e a troca faz-se entrando. E não afrouxa
        nada: com a porta fechada a app não tem autenticação nenhuma, por isso
        entrar não dá acesso a nada que não estivesse dado.
        """
        c = self.cliente(aberto=False)
        self.com_senha("miguel", SENTINELA)
        r = c.post("/api/conta/entrar",
                   json={"nome": "miguel", "senha": SENTINELA})
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True)[:300])
        d = c.get("/api/conta.json").get_json()
        self.assertTrue(d["entrado"])
        self.assertFalse(d["aberto"], "a porta continua fechada")

    def test_com_a_porta_fechada_a_password_errada_continua_a_recusar(self):
        c = self.cliente(aberto=False)
        self.com_senha("miguel", SENTINELA)
        r = c.post("/api/conta/entrar",
                   json={"nome": "miguel", "senha": "isto-nao-e-a-dela"})
        self.assertEqual(r.status_code, 401)

    def test_com_a_porta_fechada_tudo_como_ontem(self):
        """A regra da casa: fechada e SEM SESSÃO, um dono só e sem autenticação."""
        c = self.cliente(aberto=False)
        r = c.post("/api/adjust", json={"printing_id": "tst-001-100", "delta": 1})
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True)[:300])
        d = c.get("/api/conta.json").get_json()
        self.assertFalse(d["aberto"])
        self.assertTrue(d["editavel"])
        self.assertTrue(d["senha"], "a entrada por password existe nas duas portas")

    def test_uma_conta_sem_password_nao_entra_com_nada(self):
        self.utilizador.criar("Sem", "semsenha")
        c = self.cliente(aberto=True)
        for tentativa in ("", "qualquer-coisa", SENTINELA):
            r = c.post("/api/conta/entrar",
                       json={"nome": "semsenha", "senha": tentativa})
            self.assertEqual(r.status_code, 401)

    def test_dois_utilizadores_nao_se_confundem(self):
        c = self.cliente(aberto=True)
        self.com_senha("miguel", "a-password-do-miguel")
        self.com_senha("joao", "a-password-do-joao")
        # a password de um não entra na conta do outro
        r = c.post("/api/conta/entrar",
                   json={"nome": "miguel", "senha": "a-password-do-joao"})
        self.assertEqual(r.status_code, 401)
        csrf = self.entrar(c, "miguel", "a-password-do-miguel")
        c.post("/api/adjust", json={"printing_id": "tst-001-100", "delta": 4},
               headers={"X-CSRF-Token": csrf})
        c.get("/sair")
        csrf = self.entrar(c, "joao", "a-password-do-joao")
        d = c.get("/api/set/TST.json").get_json()
        qtys = [p["qty"] for g in d["groups"] for p in g["printings"]]
        self.assertEqual(sum(qtys), 0, "o João viu as cartas do Miguel")

    def test_sair_apaga_a_sessao(self):
        c = self.cliente(aberto=True)
        self.com_senha("miguel", SENTINELA)
        self.entrar(c, "miguel", SENTINELA)
        c.get("/sair")
        self.assertFalse(c.get("/api/conta.json").get_json()["entrado"])

    def test_apagar_a_conta_PELA_CLI_apaga_a_password(self):
        """Era por aqui que ficava um hash órfão — apanhado na prova de 30/09.

        O `conta.apagar` não toca no `auth.db` de propósito (é outra casa); quem
        limpa é quem sabe dela, no mesmo passo. A rota do site já o fazia e a
        CLI não.
        """
        import contextlib
        import io
        from riftvault import cli
        importlib.reload(cli)
        uid = self.com_senha("miguel", SENTINELA)
        con = self.auth.abrir()
        try:
            self.assertTrue(self.auth.estado_senha(con, uid)["tem"])
        finally:
            con.close()
        with contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            codigo = cli.main(["conta", "miguel", "--apagar", "--sim"])
        self.assertEqual(codigo, 0)
        con = self.auth.abrir()
        try:
            self.assertFalse(self.auth.estado_senha(con, uid)["tem"],
                             "ficou um hash órfão no auth.db")
        finally:
            con.close()

    def test_apagar_um_nao_apaga_a_password_do_outro(self):
        import contextlib
        import io
        from riftvault import cli
        importlib.reload(cli)
        self.com_senha("miguel", SENTINELA)
        outro = self.com_senha("joao", "a-frase-do-joao-2026")
        with contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            cli.main(["conta", "miguel", "--apagar", "--sim"])
        con = self.auth.abrir()
        try:
            self.assertTrue(self.auth.estado_senha(con, outro)["tem"])
            self.auth.entrar(con, "joao", "a-frase-do-joao-2026",
                             chave="1.2.3.4")
        finally:
            con.close()


# --------------------------------------------------------------------------
# 8. O OAUTH FICA, PARADO
# --------------------------------------------------------------------------


class TestOOauthFicaParado(Base):
    """Pergunta 7: ficou intacto e desligado? O botão aparece?"""

    def test_os_dois_fornecedores_continuam_no_codigo(self):
        self.assertTrue(hasattr(self.auth, "GOOGLE"))
        self.assertTrue(hasattr(self.auth, "DISCORD"))
        self.assertEqual(self.auth.DISCORD.url_quem,
                         "https://discord.com/api/users/@me")

    def test_sem_segredo_nao_esta_pronto_e_o_botao_nao_aparece(self):
        self.cfg({"multi": {"aberto": True},
                  "auth": {"discord": {"client_id": "1234"}}})
        importlib.reload(self.auth)
        prontos = [p for p in self.auth.disponiveis(self.config.load())
                   if p["pronto"] and p["nome"] != "local"]
        self.assertEqual(prontos, [], "o botão ia aparecer sem segredo")
        c = self.cliente(aberto=True,
                         auth={"discord": {"client_id": "1234"}})
        d = c.get("/api/conta.json").get_json()
        self.assertEqual([p for p in d["provedores"] if p["pronto"]], [])

    def test_com_segredo_volta_a_aparecer(self):
        os.environ["RIFTVAULT_DISCORD_SECRET"] = "um-segredo-de-teste"
        self.addCleanup(lambda: os.environ.pop("RIFTVAULT_DISCORD_SECRET", None))
        c = self.cliente(aberto=True,
                         auth={"discord": {"client_id": "1234"}})
        d = c.get("/api/conta.json").get_json()
        nomes = [p["nome"] for p in d["provedores"] if p["pronto"]]
        self.assertIn("discord", nomes)

    def test_o_client_id_dele_continua_no_config_real(self):
        """Ponto 6 da ordem: *"o `auth.discord.client_id` fica onde esta"*."""
        real = json.loads((REPO / "riftvault_config.json").read_text(encoding="utf-8"))
        self.assertIn("auth", real)
        self.assertIn("discord", real["auth"])
        self.assertTrue(real["auth"]["discord"].get("client_id"))

    def test_o_config_real_nao_tem_password_nem_segredo(self):
        """Está commitado num repositório PÚBLICO."""
        bruto = (REPO / "riftvault_config.json").read_text(encoding="utf-8")
        self.assertNotIn("client_secret", bruto)
        for suspeita in ("password\":", "senha\":", "scrypt"):
            self.assertNotIn(suspeita, bruto.lower())

    def test_a_entrada_por_password_nao_precisa_de_config(self):
        """É o que faz o `--verificar` deixar de exigir Discord."""
        self.cfg({"multi": {"aberto": True}})
        c = self.cliente(aberto=True)
        self.com_senha("miguel", SENTINELA)
        self.assertEqual(
            c.post("/api/conta/entrar",
                   json={"nome": "miguel", "senha": SENTINELA}).status_code, 200)


# --------------------------------------------------------------------------
# 9. O `multi --verificar`
# --------------------------------------------------------------------------


class TestVerificar(Base):
    """Pergunta 8: já não exige Discord?"""

    def _nomes(self, est) -> dict:
        return {p["nome"]: p for p in est["passos"]}

    def test_nao_exige_fornecedor_de_oauth(self):
        est = self.abrir.verificar(self.config.load())
        nomes = self._nomes(est)
        self.assertNotIn("Entrar sem password", nomes)
        self.assertIn("Há por onde entrar", nomes)
        self.assertTrue(nomes["Há por onde entrar"]["ok"])
        self.assertIn("password", nomes["Há por onde entrar"]["diz"])

    def test_exige_que_ELE_tenha_password(self):
        est = self.abrir.verificar(self.config.load())
        passo = self._nomes(est)["Tu consegues entrar"]
        self.assertFalse(passo["ok"])
        # O comando aconselhado passou a ser o `--definir-password`
        # (2026-09-30, à tarde): o `--nova-password` dá uma TEMPORÁRIA, e a
        # temporária não conta como pronto — mandava-o dar duas voltas.
        self.assertIn("--definir-password", passo["como"])
        self.assertFalse(est["pode_abrir"])

    def test_a_temporaria_dele_nao_conta_como_pronto(self):
        con = self.auth.abrir()
        try:
            self.auth.nova_temporaria(con, 1)
        finally:
            con.close()
        est = self.abrir.verificar(self.config.load())
        passo = self._nomes(est)["Tu consegues entrar"]
        self.assertFalse(passo["ok"], "abrir com a temporária era abrir meio fora")
        self.assertIn("temporária", passo["diz"])

    def test_com_a_password_dele_definida_deixa_abrir(self):
        con = self.auth.abrir()
        try:
            self.auth.definir_senha(con, 1, "a-password-do-andre",
                                    temporaria=False)
        finally:
            con.close()
        self.cfg({"auth": {"base_url": "https://editar.baverone.com"}})
        est = self.abrir.verificar(self.config.load())
        self.assertTrue(self._nomes(est)["Tu consegues entrar"]["ok"])
        self.assertTrue(est["pode_abrir"],
                        f"não deixou abrir: {[p['nome'] for p in est['faltam']]}")

    def test_sao_DOIS_passos_dele_e_nao_tres(self):
        est = self.abrir.verificar(self.config.load())
        dele = [p for p in est["passos"] if p["ok"] is None]
        self.assertEqual(len(dele), 2, [p["nome"] for p in dele])
        self.assertNotIn("Discord", " ".join(p["nome"] for p in dele))
        self.assertIn("Cloudflare", " ".join(p["nome"] for p in dele))

    def test_os_passos_dele_apontam_para_os_numeros_certos_do_guia(self):
        est = self.abrir.verificar(self.config.load())
        dele = [p for p in est["passos"] if p["ok"] is None]
        self.assertIn("PASSO 1", dele[0]["como"])
        self.assertIn("PASSO 2", dele[1]["como"])

    def test_o_texto_diz_o_comando_da_password(self):
        texto = self.abrir.texto(cfg=self.config.load())
        self.assertIn("definir-password", texto)


# --------------------------------------------------------------------------
# 10. O CLIENTE
# --------------------------------------------------------------------------


class TestOCliente(Base):
    def test_o_formulario_de_entrada_existe(self):
        js = APP_JS.read_text(encoding="utf-8")
        for pedaco in ("api/conta/entrar", "en-nome", "en-senha",
                       "entrarComSenha"):
            self.assertIn(pedaco, js)

    def test_o_formulario_da_troca_existe_e_e_um_so(self):
        js = APP_JS.read_text(encoding="utf-8")
        self.assertIn("api/conta/senha", js)
        self.assertEqual(js.count("function trocaHTML"), 1,
                         "duas versões do mesmo formulário divergem")

    def test_os_campos_de_password_sao_do_tipo_password(self):
        js = APP_JS.read_text(encoding="utf-8")
        for id_ in ("en-senha", "sn-atual", "sn-nova", "sn-rep"):
            bloco = js.split(f'id="{id_}"')[1][:120]
            self.assertIn('type="password"', bloco, id_)

    def test_a_confirmacao_das_duas_passwords_e_no_cliente(self):
        js = APP_JS.read_text(encoding="utf-8")
        self.assertIn("não são iguais", js)

    def test_todo_o_post_passa_pelo_cabecalhos(self):
        """A regra de 29/09, com as rotas novas lá dentro."""
        import re
        js = APP_JS.read_text(encoding="utf-8")
        maus = [m for m in re.findall(r"method: 'POST', headers: ([^,\n]+)", js)
                if "cabecalhos()" not in m]
        self.assertEqual(maus, [])

    def test_o_css_da_troca_existe(self):
        self.assertIn(".conta-det", CSS.read_text(encoding="utf-8"))

    def test_o_site_publicado_nao_mostra_nada_disto(self):
        """O `build` não tem rotas: sem resposta, a zona fica escondida.

        A condição mudou a 2026-09-30, à tarde — era `!c || !c.aberto`, e o
        `!c.aberto` escondia a entrada a quem tinha de trocar a password ANTES
        de abrir a porta. Ver `tests/test_conta_fechada.py`.
        """
        js = APP_JS.read_text(encoding="utf-8")
        self.assertIn("if (!c) { zona.hidden = true", js)


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""A autenticação: sem passwords, com PKCE, e o fornecedor local preso ao ensaio.

Estes testes correm contra um `auth.db` temporário — nunca contra o `data/` a
sério. A pergunta que o ficheiro todo responde é: quem entra é quem diz que é,
e ninguém entra por engano.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import sqlite3
import tempfile
import unittest
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

from riftvault import auth


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="riftvault-auth-"))
        os.environ["RIFTVAULT_AUTH"] = str(self.dir / "auth.db")
        self.addCleanup(lambda: os.environ.pop("RIFTVAULT_AUTH", None))
        self.con = auth.abrir()
        self.addCleanup(self.con.close)
        import shutil
        self.addCleanup(lambda: shutil.rmtree(self.dir, ignore_errors=True))


# --------------------------------------------------------------------------
# 1. NENHUMA PASSWORD, EM SÍTIO NENHUM
# --------------------------------------------------------------------------


class TestNenhumaPassword(Base):
    def test_o_esquema_nao_tem_campo_de_password(self):
        """A resposta à primeira pergunta da checklist tem de ser NÃO."""
        colunas = []
        for t in ("user_auth", "sessions", "auth_pedidos", "auth_tentativas"):
            colunas += [r["name"].lower()
                        for r in self.con.execute(f"PRAGMA table_info({t})")]
        self.assertTrue(colunas, "o esquema não foi criado")
        for proibida in ("password", "passwd", "pass", "senha", "hash_pw",
                         "password_hash", "segredo", "secret"):
            self.assertNotIn(proibida, colunas,
                             f"a coluna «{proibida}» não pode existir")

    def test_o_codigo_nao_fala_de_passwords(self):
        fonte = (Path(auth.__file__)).read_text(encoding="utf-8").lower()
        # `password` aparece só na frase que explica que não se guardam.
        self.assertNotIn("password_hash", fonte)
        self.assertNotIn("bcrypt", fonte)
        self.assertNotIn("scrypt", fonte)
        self.assertNotIn("pbkdf2", fonte)

    def test_o_token_do_fornecedor_nao_se_guarda(self):
        """O `access_token` serve uma pergunta e morre. Não há onde o pôr."""
        colunas = [r["name"].lower()
                   for r in self.con.execute("PRAGMA table_info(user_auth)")]
        for proibida in ("access_token", "token", "refresh_token", "id_token"):
            self.assertNotIn(proibida, colunas)


# --------------------------------------------------------------------------
# 2. PKCE
# --------------------------------------------------------------------------


class TestPkce(unittest.TestCase):
    def test_o_desafio_e_o_sha256_do_verifier(self):
        verifier, desafio = auth.par_pkce()
        esperado = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode("ascii")).digest()).decode().rstrip("=")
        self.assertEqual(desafio, esperado)

    def test_nao_leva_padding_nem_caracteres_fora_do_urlsafe(self):
        for _ in range(20):
            v, d = auth.par_pkce()
            for x in (v, d):
                self.assertNotIn("=", x)
                self.assertNotIn("+", x)
                self.assertNotIn("/", x)

    def test_dois_pares_nunca_saem_iguais(self):
        vistos = {auth.par_pkce()[0] for _ in range(50)}
        self.assertEqual(len(vistos), 50)

    def test_o_verifier_tem_o_comprimento_que_a_norma_pede(self):
        # O RFC 7636 pede entre 43 e 128 caracteres.
        v, _ = auth.par_pkce()
        self.assertGreaterEqual(len(v), 43)
        self.assertLessEqual(len(v), 128)


# --------------------------------------------------------------------------
# 3. OS FORNECEDORES AGUENTAM CREDENCIAIS VAZIAS
# --------------------------------------------------------------------------


class TestProvedoresSemCredenciais(unittest.TestCase):
    """Hoje o config está vazio. A app tem de DIZER o que falta, não rebentar."""

    def test_sem_config_nenhum_o_google_diz_o_que_falta(self):
        falta = auth.GOOGLE.em_falta({})
        self.assertEqual(falta, ["client_id", "client_secret"])
        self.assertFalse(auth.GOOGLE.configurado({}))

    def test_sem_config_nenhum_o_discord_diz_o_que_falta(self):
        self.assertEqual(auth.DISCORD.em_falta({}), ["client_id", "client_secret"])

    def test_so_com_o_id_falta_o_secret(self):
        cfg = {"auth": {"google": {"client_id": "abc"}}}
        self.assertEqual(auth.GOOGLE.em_falta(cfg), ["client_secret"])

    def test_espacos_em_branco_nao_contam_como_configurado(self):
        cfg = {"auth": {"google": {"client_id": "   ", "client_secret": "\t"}}}
        self.assertEqual(auth.GOOGLE.em_falta(cfg), ["client_id", "client_secret"])

    def test_com_os_dois_esta_pronto(self):
        cfg = {"auth": {"google": {"client_id": "a", "client_secret": "b"}}}
        self.assertTrue(auth.GOOGLE.configurado(cfg))
        self.assertEqual(auth.GOOGLE.em_falta(cfg), [])

    def test_usar_um_provedor_por_configurar_levanta_e_diz_onde_se_mete(self):
        with self.assertRaises(auth.ProvedorPorConfigurar) as e:
            auth.GOOGLE.exigir_configurado({})
        msg = str(e.exception)
        self.assertIn("client_id", msg)
        self.assertIn("auth.google", msg)
        self.assertIn("abrir-a-porta", msg)

    def test_um_fornecedor_que_nao_existe_rebenta_com_a_lista(self):
        with self.assertRaises(auth.ProvedorDesconhecido) as e:
            auth.provedor("facebook")
        self.assertIn("google", str(e.exception))
        self.assertIn("discord", str(e.exception))


# --------------------------------------------------------------------------
# 4. O ENDEREÇO DE ENTRADA
# --------------------------------------------------------------------------


class TestUrlDeEntrada(Base):
    def _campos(self, url: str) -> dict:
        return dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))

    def test_o_google_leva_pkce_state_e_o_escopo_minimo(self):
        cfg = {"auth": {"google": {"client_id": "cid", "client_secret": "sec"}}}
        r = auth.comecar(self.con, "google",
                         redirect_uri="https://x/callback", cfg=cfg)
        c = self._campos(r["url"])
        self.assertTrue(r["url"].startswith(auth.GOOGLE.url_autorizar))
        self.assertEqual(c["client_id"], "cid")
        self.assertEqual(c["response_type"], "code")
        self.assertEqual(c["code_challenge_method"], "S256")
        self.assertEqual(c["state"], r["state"])
        self.assertTrue(c["code_challenge"])
        self.assertEqual(c["scope"], "openid profile")

    def test_nao_se_pede_o_email_a_nenhum_dos_dois(self):
        """Menos um dado de terceiros guardado num PC de casa."""
        self.assertNotIn("email", auth.GOOGLE.escopo)
        self.assertNotIn("email", auth.DISCORD.escopo)

    def test_o_secret_nunca_vai_no_endereco(self):
        cfg = {"auth": {"discord": {"client_id": "cid", "client_secret": "SEGREDO"}}}
        r = auth.comecar(self.con, "discord",
                         redirect_uri="https://x/callback", cfg=cfg)
        self.assertNotIn("SEGREDO", r["url"])

    def test_o_verifier_fica_no_servidor_e_nao_viaja(self):
        cfg = {"auth": {"google": {"client_id": "cid", "client_secret": "sec"}}}
        r = auth.comecar(self.con, "google",
                         redirect_uri="https://x/callback", cfg=cfg)
        row = self.con.execute("SELECT verifier FROM auth_pedidos WHERE state = ?",
                               (r["state"],)).fetchone()
        self.assertTrue(row["verifier"])
        self.assertNotIn(row["verifier"], r["url"])

    def test_comecar_com_um_provedor_por_configurar_nao_grava_pedido(self):
        with self.assertRaises(auth.ProvedorPorConfigurar):
            auth.comecar(self.con, "google", redirect_uri="https://x/c", cfg={})
        n = self.con.execute("SELECT COUNT(*) AS n FROM auth_pedidos").fetchone()["n"]
        self.assertEqual(n, 0)


# --------------------------------------------------------------------------
# 5. O `state` SERVE UMA VEZ E TEM PRAZO
# --------------------------------------------------------------------------


class TestPedidos(Base):
    def _comecar(self) -> dict:
        cfg = {"auth": {"google": {"client_id": "c", "client_secret": "s"}}}
        return auth.comecar(self.con, "google",
                            redirect_uri="https://x/c", cfg=cfg)

    def _novo(self) -> str:
        return self._comecar()["state"]

    def test_consumir_devolve_o_pedido(self):
        r = self._comecar()
        p = auth.consumir_pedido(self.con, r["state"], r["nonce"])
        self.assertEqual(p["provedor"], "google")
        self.assertTrue(p["verifier"])

    def test_o_mesmo_state_nao_serve_duas_vezes(self):
        r = self._comecar()
        auth.consumir_pedido(self.con, r["state"], r["nonce"])
        with self.assertRaises(auth.PedidoInvalido):
            auth.consumir_pedido(self.con, r["state"], r["nonce"])

    # -- o `nonce` ata a entrada AO BROWSER (login CSRF) ------------------

    def test_sem_o_nonce_do_browser_a_entrada_nao_se_conclui(self):
        """É o «login CSRF»: quem começa não pode fazer outro concluir.

        Sem isto, alguém começava uma entrada, ficava com um `state` válido, e
        levava a vítima a abrir o endereço de volta — o browser dela acabava com
        uma sessão da conta DELE, e o que ela escrevesse ia para a coleção dele.
        """
        r = self._comecar()
        with self.assertRaises(auth.PedidoInvalido) as e:
            auth.consumir_pedido(self.con, r["state"], None)
        self.assertIn("browser", str(e.exception))

    def test_com_o_nonce_de_outra_entrada_nao_serve(self):
        a = self._comecar()
        b = self._comecar()
        with self.assertRaises(auth.PedidoInvalido):
            auth.consumir_pedido(self.con, a["state"], b["nonce"])

    def test_o_nonce_nao_esta_em_claro_na_base(self):
        r = self._comecar()
        bruto = Path(os.environ["RIFTVAULT_AUTH"]).read_bytes()
        self.assertNotIn(r["nonce"].encode(), bruto)

    def test_o_nonce_nao_viaja_no_endereco(self):
        r = self._comecar()
        self.assertNotIn(r["nonce"], r["url"])

    def test_dois_nonces_nunca_saem_iguais(self):
        self.assertNotEqual(self._comecar()["nonce"], self._comecar()["nonce"])

    def test_o_state_gasto_e_apagado_mesmo_com_o_nonce_errado(self):
        """Não se deixa um `state` a valer para quem tentar outra vez."""
        r = self._comecar()
        with self.assertRaises(auth.PedidoInvalido):
            auth.consumir_pedido(self.con, r["state"], "errado")
        n = self.con.execute("SELECT COUNT(*) AS n FROM auth_pedidos").fetchone()["n"]
        self.assertEqual(n, 0)

    def test_um_state_inventado_rebenta(self):
        with self.assertRaises(auth.PedidoInvalido):
            auth.consumir_pedido(self.con, "nao-existe")

    def test_um_state_vazio_rebenta(self):
        with self.assertRaises(auth.PedidoInvalido):
            auth.consumir_pedido(self.con, "")

    def test_um_pedido_velho_rebenta_e_diz_o_prazo(self):
        """E diz o PRAZO, não «outro browser»: quem demorou já perdeu o cookie."""
        r = self._comecar()
        velho = (datetime.now(timezone.utc)
                 - timedelta(minutes=auth.PEDIDO_MINUTOS + 1)).isoformat()
        self.con.execute("UPDATE auth_pedidos SET criado_em = ? WHERE state = ?",
                         (velho, r["state"]))
        self.con.commit()
        with self.assertRaises(auth.PedidoInvalido) as e:
            auth.consumir_pedido(self.con, r["state"], None)
        self.assertIn(str(auth.PEDIDO_MINUTOS), str(e.exception))
        self.assertNotIn("browser", str(e.exception))

    def test_um_pedido_velho_e_apagado_mesmo_rebentando(self):
        """Não fica lixo: quem rebenta também limpa."""
        r = self._comecar()
        velho = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        self.con.execute("UPDATE auth_pedidos SET criado_em = ? WHERE state = ?",
                         (velho, r["state"]))
        self.con.commit()
        with self.assertRaises(auth.PedidoInvalido):
            auth.consumir_pedido(self.con, r["state"], r["nonce"])
        n = self.con.execute("SELECT COUNT(*) AS n FROM auth_pedidos").fetchone()["n"]
        self.assertEqual(n, 0)

    def test_limpar_pedidos_tira_os_velhos_e_deixa_os_novos(self):
        novo = self._novo()
        velho = self._novo()
        self.con.execute(
            "UPDATE auth_pedidos SET criado_em = ? WHERE state = ?",
            ((datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(), velho))
        self.con.commit()
        self.assertEqual(auth.limpar_pedidos(self.con), 1)
        restantes = [r["state"] for r in
                     self.con.execute("SELECT state FROM auth_pedidos")]
        self.assertEqual(restantes, [novo])


# --------------------------------------------------------------------------
# 6. SESSÕES
# --------------------------------------------------------------------------


class TestSessoes(Base):
    def test_o_cookie_nao_esta_na_base_em_claro(self):
        """Ler o ficheiro não dá uma sessão utilizável."""
        s = auth.criar_sessao(self.con, user_id=7)
        bruto = Path(os.environ["RIFTVAULT_AUTH"]).read_bytes()
        self.assertNotIn(s["sid"].encode(), bruto)
        guardado = self.con.execute("SELECT sid_hash FROM sessions").fetchone()
        self.assertEqual(guardado["sid_hash"],
                         hashlib.sha256(s["sid"].encode()).hexdigest())

    def test_a_sessao_le_se_pelo_sid_em_claro(self):
        s = auth.criar_sessao(self.con, user_id=7)
        lida = auth.sessao(self.con, s["sid"])
        self.assertEqual(lida["user_id"], 7)

    def test_um_sid_errado_da_none(self):
        auth.criar_sessao(self.con, user_id=7)
        self.assertIsNone(auth.sessao(self.con, "outro-qualquer"))

    def test_um_sid_vazio_da_none(self):
        self.assertIsNone(auth.sessao(self.con, ""))
        self.assertIsNone(auth.sessao(self.con, None))

    def test_uma_sessao_expirada_da_none_e_e_apagada(self):
        s = auth.criar_sessao(self.con, user_id=7)
        self.con.execute("UPDATE sessions SET expira_em = ?",
                         ((datetime.now(timezone.utc)
                           - timedelta(days=1)).isoformat(),))
        self.con.commit()
        self.assertIsNone(auth.sessao(self.con, s["sid"]))
        n = self.con.execute("SELECT COUNT(*) AS n FROM sessions").fetchone()["n"]
        self.assertEqual(n, 0)

    def test_uma_data_ilegivel_conta_como_expirada(self):
        """Na dúvida não se deixa entrar."""
        s = auth.criar_sessao(self.con, user_id=7)
        self.con.execute("UPDATE sessions SET expira_em = 'nao-e-uma-data'")
        self.con.commit()
        self.assertIsNone(auth.sessao(self.con, s["sid"]))

    def test_cada_sessao_tem_o_seu_csrf(self):
        a = auth.criar_sessao(self.con, user_id=1)
        b = auth.criar_sessao(self.con, user_id=1)
        self.assertNotEqual(a["csrf"], b["csrf"])
        self.assertTrue(len(a["csrf"]) >= 40)

    def test_tocar_adia_a_expiracao(self):
        s = auth.criar_sessao(self.con, user_id=1)
        # Uma sessão a um dia de expirar: tocar-lhe põe-na outra vez nos 30.
        self.con.execute("UPDATE sessions SET expira_em = ?",
                         ((datetime.now(timezone.utc)
                           + timedelta(days=1)).isoformat(),))
        self.con.commit()
        self.assertTrue(auth.tocar(self.con, s["sid"]))
        depois = datetime.fromisoformat(
            auth.sessao(self.con, s["sid"])["expira_em"])
        self.assertGreater(depois, datetime.now(timezone.utc) + timedelta(days=2))

    def test_tocar_nao_escreve_mais_do_que_uma_vez_por_hora(self):
        """Uma página da Coleção são dezenas de pedidos; não vale um UPDATE cada."""
        s = auth.criar_sessao(self.con, user_id=1)
        agora = auth.sessao(self.con, s["sid"])["visto_em"]
        self.assertFalse(auth.tocar(self.con, s["sid"], None, agora),
                         "acabou de ser vista: não tinha de escrever")

    def test_passada_a_hora_volta_a_escrever(self):
        s = auth.criar_sessao(self.con, user_id=1)
        velho = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        self.assertTrue(auth.tocar(self.con, s["sid"], None, velho))

    def test_um_visto_em_ilegivel_escreve_em_vez_de_rebentar(self):
        s = auth.criar_sessao(self.con, user_id=1)
        self.assertTrue(auth.tocar(self.con, s["sid"], None, "nao-e-uma-data"))

    def test_terminar_apaga_so_aquela(self):
        a = auth.criar_sessao(self.con, user_id=1)
        b = auth.criar_sessao(self.con, user_id=1)
        auth.terminar(self.con, a["sid"])
        self.assertIsNone(auth.sessao(self.con, a["sid"]))
        self.assertIsNotNone(auth.sessao(self.con, b["sid"]))

    def test_terminar_todas_apaga_as_de_um_utilizador_e_so_dele(self):
        a = auth.criar_sessao(self.con, user_id=1)
        b = auth.criar_sessao(self.con, user_id=1)
        c = auth.criar_sessao(self.con, user_id=2)
        self.assertEqual(auth.terminar_todas(self.con, 1), 2)
        self.assertIsNone(auth.sessao(self.con, a["sid"]))
        self.assertIsNone(auth.sessao(self.con, b["sid"]))
        self.assertIsNotNone(auth.sessao(self.con, c["sid"]))

    def test_limpar_expiradas_conta_as_que_tirou(self):
        auth.criar_sessao(self.con, user_id=1)
        velha = auth.criar_sessao(self.con, user_id=2)
        self.con.execute(
            "UPDATE sessions SET expira_em = ? WHERE sid_hash = ?",
            ((datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
             hashlib.sha256(velha["sid"].encode()).hexdigest()))
        self.con.commit()
        self.assertEqual(auth.limpar_expiradas(self.con), 1)

    def test_o_agente_e_cortado_para_nao_crescer_sem_limite(self):
        auth.criar_sessao(self.con, user_id=1, agente="x" * 5000)
        row = self.con.execute("SELECT agente FROM sessions").fetchone()
        self.assertLessEqual(len(row["agente"]), 200)

    def test_sessao_dias_do_config_manda(self):
        s = auth.criar_sessao(self.con, user_id=1, cfg={"auth": {"sessao_dias": 1}})
        expira = datetime.fromisoformat(
            auth.sessao(self.con, s["sid"])["expira_em"])
        self.assertLess(expira, datetime.now(timezone.utc) + timedelta(days=2))

    def test_sessao_dias_absurdo_rebenta(self):
        for mau in (0, -5, "muitos"):
            with self.assertRaises(ValueError):
                auth.sessao_dias({"auth": {"sessao_dias": mau}})


# --------------------------------------------------------------------------
# 7. ROTAÇÃO NO LOGIN
# --------------------------------------------------------------------------


class TestRotacao(Base):
    def test_ligar_conta_da_um_cookie_NOVO_e_mata_o_antigo(self):
        pre = auth.criar_sessao(
            self.con, identidade=auth.Identidade("local", "s1", "Miguel"))
        self.assertIsNone(auth.sessao(self.con, pre["sid"])["user_id"])

        nova = auth.ligar_conta(self.con, pre["sid"], 5)

        self.assertNotEqual(nova["sid"], pre["sid"])
        self.assertIsNone(auth.sessao(self.con, pre["sid"]),
                          "o cookie do pré-registo tinha de deixar de valer")
        self.assertEqual(auth.sessao(self.con, nova["sid"])["user_id"], 5)

    def test_o_csrf_tambem_e_novo(self):
        pre = auth.criar_sessao(
            self.con, identidade=auth.Identidade("local", "s1", "M"))
        nova = auth.ligar_conta(self.con, pre["sid"], 5)
        self.assertNotEqual(nova["csrf"], pre["csrf"])

    def test_a_identidade_acompanha_a_sessao_nova(self):
        pre = auth.criar_sessao(
            self.con, identidade=auth.Identidade("discord", "abc", "Zé"))
        nova = auth.ligar_conta(self.con, pre["sid"], 9)
        s = auth.sessao(self.con, nova["sid"])
        self.assertEqual(s["provedor"], "discord")
        self.assertEqual(s["sub"], "abc")

    def test_ligar_uma_sessao_que_expirou_rebenta(self):
        pre = auth.criar_sessao(
            self.con, identidade=auth.Identidade("local", "s", "s"))
        self.con.execute("UPDATE sessions SET expira_em = ?",
                         ((datetime.now(timezone.utc)
                           - timedelta(days=1)).isoformat(),))
        self.con.commit()
        with self.assertRaises(auth.PedidoInvalido):
            auth.ligar_conta(self.con, pre["sid"], 5)


# --------------------------------------------------------------------------
# 8. CSRF
# --------------------------------------------------------------------------


class TestCsrf(Base):
    def test_o_token_certo_passa(self):
        s = auth.criar_sessao(self.con, user_id=1)
        sess = auth.sessao(self.con, s["sid"])
        self.assertTrue(auth.csrf_valido(sess, s["csrf"]))

    def test_o_token_errado_nao_passa(self):
        s = auth.criar_sessao(self.con, user_id=1)
        sess = auth.sessao(self.con, s["sid"])
        self.assertFalse(auth.csrf_valido(sess, "outro"))

    def test_sem_token_nao_passa(self):
        s = auth.criar_sessao(self.con, user_id=1)
        sess = auth.sessao(self.con, s["sid"])
        for vazio in ("", None):
            self.assertFalse(auth.csrf_valido(sess, vazio))

    def test_sem_sessao_nada_passa(self):
        self.assertFalse(auth.csrf_valido(None, "qualquer"))

    def test_o_csrf_de_outra_sessao_nao_serve(self):
        a = auth.criar_sessao(self.con, user_id=1)
        b = auth.criar_sessao(self.con, user_id=1)
        self.assertFalse(
            auth.csrf_valido(auth.sessao(self.con, a["sid"]), b["csrf"]))


# --------------------------------------------------------------------------
# 9. O TECTO DE TENTATIVAS
# --------------------------------------------------------------------------


class TestTentativas(Base):
    def test_abaixo_do_tecto_passa(self):
        cfg = {"auth": {"tentativas_por_hora": 3}}
        for _ in range(2):
            auth.registar_tentativa(self.con, "1.2.3.4", "google", False)
        auth.exigir_folga(self.con, "1.2.3.4", cfg)  # não rebenta

    def test_no_tecto_rebenta_e_diz_o_numero(self):
        cfg = {"auth": {"tentativas_por_hora": 3}}
        for _ in range(3):
            auth.registar_tentativa(self.con, "1.2.3.4", "google", False)
        with self.assertRaises(auth.DemasiadasTentativas) as e:
            auth.exigir_folga(self.con, "1.2.3.4", cfg)
        self.assertIn("3", str(e.exception))

    def test_o_tecto_e_por_chave(self):
        cfg = {"auth": {"tentativas_por_hora": 2}}
        for _ in range(2):
            auth.registar_tentativa(self.con, "1.1.1.1", "google", False)
        with self.assertRaises(auth.DemasiadasTentativas):
            auth.exigir_folga(self.con, "1.1.1.1", cfg)
        auth.exigir_folga(self.con, "2.2.2.2", cfg)  # outro IP, à vontade

    def test_as_tentativas_de_ha_mais_de_uma_hora_nao_contam(self):
        cfg = {"auth": {"tentativas_por_hora": 2}}
        for _ in range(5):
            auth.registar_tentativa(self.con, "1.1.1.1", "google", False)
        self.con.execute("UPDATE auth_tentativas SET ts = ?",
                         ((datetime.now(timezone.utc)
                           - timedelta(hours=2)).isoformat(),))
        self.con.commit()
        auth.exigir_folga(self.con, "1.1.1.1", cfg)

    def test_as_bem_sucedidas_tambem_contam(self):
        """O tecto é de PEDIDOS ao fornecedor, não de falhas."""
        cfg = {"auth": {"tentativas_por_hora": 2}}
        for _ in range(2):
            auth.registar_tentativa(self.con, "1.1.1.1", "google", True)
        with self.assertRaises(auth.DemasiadasTentativas):
            auth.exigir_folga(self.con, "1.1.1.1", cfg)

    def test_tecto_absurdo_rebenta(self):
        for mau in (0, -1, "muitas"):
            with self.assertRaises(ValueError):
                auth.tentativas_por_hora({"auth": {"tentativas_por_hora": mau}})


# --------------------------------------------------------------------------
# 10. IDENTIDADES
# --------------------------------------------------------------------------


class TestIdentidades(Base):
    def test_guardar_e_encontrar(self):
        i = auth.Identidade("google", "1234", "Miguel")
        auth.guardar_identidade(self.con, i, 3)
        self.assertEqual(auth.por_identidade(self.con, i), 3)

    def test_uma_identidade_desconhecida_da_none(self):
        self.assertIsNone(
            auth.por_identidade(self.con, auth.Identidade("google", "x", "")))

    def test_o_mesmo_sub_noutro_fornecedor_e_outra_pessoa(self):
        auth.guardar_identidade(self.con, auth.Identidade("google", "1", "A"), 1)
        self.assertIsNone(
            auth.por_identidade(self.con, auth.Identidade("discord", "1", "B")))

    def test_guardar_duas_vezes_nao_duplica(self):
        i = auth.Identidade("google", "1234", "Miguel")
        auth.guardar_identidade(self.con, i, 3)
        auth.guardar_identidade(self.con, i, 3)
        n = self.con.execute("SELECT COUNT(*) AS n FROM user_auth").fetchone()["n"]
        self.assertEqual(n, 1)

    def test_a_mesma_pessoa_pode_ligar_dois_fornecedores_ao_mesmo_utilizador(self):
        auth.guardar_identidade(self.con, auth.Identidade("google", "g", "M"), 4)
        auth.guardar_identidade(self.con, auth.Identidade("discord", "d", "M"), 4)
        self.assertEqual(len(auth.identidades_de(self.con, 4)), 2)

    def test_a_lista_de_identidades_nao_mostra_o_sub(self):
        """O `sub` é um identificador da pessoa no fornecedor; não é para mostrar."""
        auth.guardar_identidade(self.con,
                                auth.Identidade("google", "SEGREDO-123", "M"), 4)
        for x in auth.identidades_de(self.con, 4):
            self.assertNotIn("sub", x)
            self.assertNotIn("SEGREDO-123", json.dumps(x, ensure_ascii=False))

    def test_esquecer_tira_identidades_e_sessoes_e_conta_as_linhas(self):
        auth.guardar_identidade(self.con, auth.Identidade("google", "g", "M"), 4)
        auth.guardar_identidade(self.con, auth.Identidade("discord", "d", "M"), 4)
        auth.criar_sessao(self.con, user_id=4)
        auth.criar_sessao(self.con, user_id=4)
        outra = auth.criar_sessao(self.con, user_id=9)
        auth.guardar_identidade(self.con, auth.Identidade("google", "outro", "Z"), 9)

        r = auth.esquecer_identidades(self.con, 4)

        self.assertEqual(r, {"identidades": 2, "sessoes": 2})
        self.assertIsNotNone(auth.sessao(self.con, outra["sid"]),
                             "a sessão do outro utilizador não podia ser tocada")
        self.assertEqual(
            auth.por_identidade(self.con, auth.Identidade("google", "outro", "Z")), 9)


# --------------------------------------------------------------------------
# 11. O SLUG DO SUBDOMÍNIO
# --------------------------------------------------------------------------


class TestSlug(unittest.TestCase):
    def test_os_bons_passam(self):
        for bom in ("miguel", "ze-carlos", "a1", "x9y", "abc123",
                    "m" * 32, "joao-pedro-silva"):
            self.assertEqual(auth.validar_slug(bom), bom)

    def test_maiusculas_nao_se_corrigem_em_silencio(self):
        with self.assertRaises(ValueError) as e:
            auth.validar_slug("Miguel")
        self.assertIn("miguel", str(e.exception))

    def test_acentos_nao_passam(self):
        for mau in ("joão", "zé", "münchen"):
            with self.assertRaises(ValueError):
                auth.validar_slug(mau)

    def test_vazio_diz_que_falta_escolher(self):
        for mau in ("", "   ", None):
            with self.assertRaises(ValueError) as e:
                auth.validar_slug(mau)
            self.assertIn("falta", str(e.exception).lower())

    def test_um_caractere_nao_chega(self):
        with self.assertRaises(ValueError):
            auth.validar_slug("m")

    def test_nao_pode_comecar_nem_acabar_por_hifen(self):
        for mau in ("-miguel", "miguel-", "-"):
            with self.assertRaises(ValueError):
                auth.validar_slug(mau)

    def test_dois_hifens_seguidos_nao_passam(self):
        """`xn--` é punycode; proibir o par é mais simples do que explicar."""
        with self.assertRaises(ValueError) as e:
            auth.validar_slug("ab--cd")
        self.assertIn("hifen", str(e.exception).lower())

    def test_pontos_e_espacos_e_sinais_nao_passam(self):
        for mau in ("mi.guel", "mi guel", "mi_guel", "mi/guel", "mi@guel",
                    "mi%20guel", "../etc", "a\nb"):
            with self.assertRaises(ValueError):
                auth.validar_slug(mau)

    def test_comprido_demais_nao_passa(self):
        with self.assertRaises(ValueError) as e:
            auth.validar_slug("m" * 33)
        self.assertIn("32", str(e.exception))

    def test_os_reservados_do_servico_nao_passam(self):
        for mau in ("www", "api", "admin", "rift", "riftvault", "login",
                    "conta", "docs", "img", "u", "mail", "ns1", "cdn",
                    "ensaio", "teste", "status"):
            with self.assertRaises(ValueError) as e:
                auth.validar_slug(mau)
            self.assertIn("reservado", str(e.exception))

    def test_o_nome_dele_esta_reservado_para_ninguem_se_fingir_dele(self):
        for dele in ("baverone", "andre"):
            with self.assertRaises(ValueError):
                auth.validar_slug(dele)

    def test_limpar_slug_sugere_a_partir_de_um_nome(self):
        self.assertEqual(auth.limpar_slug("João Pedro"), "joao-pedro")
        self.assertEqual(auth.limpar_slug("Zé  Carlos!!"), "ze-carlos")
        self.assertEqual(auth.limpar_slug("Miguel"), "miguel")
        self.assertEqual(auth.limpar_slug("--x--"), "x")

    def test_limpar_slug_de_um_nome_impossivel_da_vazio_e_nao_rebenta(self):
        """E aí a pessoa escolhe à mão — não se inventa um nome por ela."""
        self.assertEqual(auth.limpar_slug("!!!"), "")
        self.assertEqual(auth.limpar_slug(""), "")

    def test_o_que_limpar_slug_sugere_e_valido(self):
        for nome in ("João Pedro", "Zé Carlos", "Miguel", "Ana-Maria Sá"):
            s = auth.limpar_slug(nome)
            self.assertEqual(auth.validar_slug(s), s)


if __name__ == "__main__":
    unittest.main(verbosity=2)

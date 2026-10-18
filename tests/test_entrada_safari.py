"""A entrada com Google no iPhone: o cookie do `nonce` que não chegava (2026-10-18).

O André ficou fora da conta a 16/10 e a 18/10 (09:41, iPhone): o início em
`/entrar/google` deu 302 com o cookie `riftvault_entrada` (Secure, Lax), e a
volta do Google, seis segundos depois, deu 400 com JSON cru — «esta entrada não
começou neste browser». O Safari não mandava o cookie `Lax` numa volta que é um
302 cross-site a seguir ao POST do ecrã de consentimento.

O que se fixa aqui:
  1. por HTTPS o cookie do `nonce` sai `SameSite=None; Secure`; por http, `Lax`;
  2. uma volta SEM o cookie não gasta o `state`: responde com uma página nossa
     que repete o pedido (same-site, leva o cookie) com `salto=1`;
  3. no salto, com o cookie, a entrada conclui-se — é o caso do iPhone;
  4. no salto, sem o cookie, recusa (login CSRF continua fechado) — e com uma
     PÁGINA com botão para recomeçar, não JSON cru.
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.fixture import SEM_CONFIG  # noqa: E402

os.environ["RIFTVAULT_CONFIG"] = SEM_CONFIG

from tests.test_contas import Base  # noqa: E402

DISCORD = {"discord": {"client_id": "a", "client_secret": "b"}}
HTTPS = {"X-Forwarded-Proto": "https"}


class Caso(Base):
    def setUp(self):
        super().setUp()
        self.c = self.cliente(aberto=True, auth=DISCORD)

    def comecar(self, **headers):
        r = self.c.get("/entrar/discord", headers=headers)
        self.assertEqual(r.status_code, 302, r.get_data(as_text=True)[:300])
        state = parse_qs(urlsplit(r.headers["Location"]).query)["state"][0]
        return r, state

    def pedidos(self) -> int:
        con = self.auth.abrir()
        try:
            return con.execute("SELECT COUNT(*) FROM auth_pedidos").fetchone()[0]
        finally:
            con.close()

    def sem_o_cookie(self):
        """O que o Safari fazia: a volta chega sem o cookie do `nonce`."""
        self.c.delete_cookie(self.auth.COOKIE_NONCE, path="/")


class TestOCookie(Caso):
    def test_por_https_sai_SameSite_None_e_Secure(self):
        r, _ = self.comecar(**HTTPS)
        bruto = r.headers["Set-Cookie"]
        self.assertIn(self.auth.COOKIE_NONCE, bruto)
        self.assertIn("SameSite=None", bruto)
        self.assertIn("Secure", bruto)
        self.assertIn("HttpOnly", bruto)

    def test_por_http_fica_Lax_sem_Secure(self):
        """Sem HTTPS o `None` exige `Secure`, e o browser deitava-o fora."""
        r, _ = self.comecar()
        bruto = r.headers["Set-Cookie"]
        self.assertIn("SameSite=Lax", bruto)
        self.assertNotIn("Secure", bruto)


class TestOSalto(Caso):
    def test_a_volta_sem_cookie_salta_pela_pagina_e_nao_gasta_o_state(self):
        _, state = self.comecar(**HTTPS)
        self.sem_o_cookie()
        antes = self.pedidos()
        r = self.c.get(f"/entrar/discord?code=abc&state={state}", headers=HTTPS)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.content_type.startswith("text/html"))
        corpo = r.get_data(as_text=True)
        self.assertIn("salto=1", corpo)
        self.assertIn(state, corpo)
        self.assertEqual(self.pedidos(), antes, "o state não se podia gastar aqui")

    def test_no_salto_com_o_cookie_a_entrada_conclui(self):
        """O caso do iPhone: à primeira o cookie não veio, no salto vem."""
        self.ensaio(True)
        p = self.auth.provedor("discord")
        local = self.auth.LOCAL
        original = type(p).identidade
        type(p).identidade = lambda self_, **k: local.identidade(code="amigo-x")
        self.addCleanup(setattr, type(p), "identidade", original)

        _, state = self.comecar(**HTTPS)
        r = self.c.get(f"/entrar/discord?code=abc&state={state}&salto=1",
                       headers=HTTPS)
        self.assertEqual(r.status_code, 302, r.get_data(as_text=True)[:400])
        self.assertIn(self.auth.COOKIE + "=", r.headers.get("Set-Cookie", ""))

    def test_no_salto_sem_o_cookie_recusa_com_pagina_e_botao(self):
        """O login CSRF continua fechado — e diz-se numa página, não JSON."""
        _, state = self.comecar(**HTTPS)
        self.sem_o_cookie()
        r = self.c.get(f"/entrar/discord?code=abc&state={state}&salto=1",
                       headers=HTTPS)
        self.assertEqual(r.status_code, 400)
        self.assertTrue(r.content_type.startswith("text/html"))
        corpo = r.get_data(as_text=True)
        self.assertIn("browser", corpo)
        self.assertIn('href="/entrar/discord"', corpo)
        self.assertIn("Recomeçar", corpo)
        self.assertNotIn('"erro"', corpo)
        self.assertNotIn(self.auth.COOKIE + "=", r.headers.get("Set-Cookie", ""))

    def test_um_state_ja_usado_tambem_e_pagina(self):
        """O recarregar da volta (16/10, 21:18:41): página, não JSON."""
        r = self.c.get("/entrar/discord?code=abc&state=nao-existe&salto=1")
        self.assertEqual(r.status_code, 400)
        self.assertTrue(r.content_type.startswith("text/html"))
        self.assertIn("Recomeçar", r.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main(verbosity=2)

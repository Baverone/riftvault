"""A VOLTA do `?ligar=` com a porta FECHADA (ronda de 2026-10-19).

A docstring de `rotas_conta.entrar` promete que o caminho do convite funciona
com a porta fechada. Funcionava na IDA (`?ligar=<codigo>`), mas o
`redirect_uri` não leva o `ligar`, por isso na VOLTA do fornecedor
(`?code=&state=`) o pedido chegava sem convite, `exigir_porta_aberta` dava 403
e o convite — gasto na ida — perdia-se. Aqui fixa-se a rota inteira: ida,
volta, e a volta SEM `liga_a` a continuar a recusar.

Tudo contra pastas temporárias; o Google é simulado (nunca vai à rede).
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.fixture import SEM_CONFIG  # noqa: E402

os.environ["RIFTVAULT_CONFIG"] = SEM_CONFIG

from tests.test_contas import Base  # noqa: E402

GOOGLE = {"auth": {"google": {"client_id": "cid", "client_secret": "sec"}}}


class TestVoltaDoLigarComAPortaFechada(Base):
    def _ida(self, c, convite=None):
        url = "/entrar/google" + (f"?ligar={convite}" if convite else "")
        r = c.get(url)
        self.assertEqual(r.status_code, 302, r.get_data(as_text=True)[:200])
        from urllib.parse import parse_qs, urlsplit
        return parse_qs(urlsplit(r.headers["Location"]).query)["state"][0]

    def _volta(self, c, state):
        ident = self.auth.Identidade("google", "sub-do-andre", "André")
        with mock.patch.object(self.auth.GOOGLE, "identidade",
                               return_value=ident):
            return c.get(f"/entrar/google?code=abc&state={state}",
                         follow_redirects=False)

    def setUp(self):
        super().setUp()
        self.addCleanup(lambda: os.environ.pop("RIFTVAULT_GOOGLE_SECRET", None))

    def test_ida_e_volta_com_convite_e_porta_fechada_entram(self):
        c = self.cliente(aberto=False, **GOOGLE)
        con = self.auth.abrir()
        try:
            convite = self.auth.criar_convite(con, 1)
        finally:
            con.close()
        state = self._ida(c, convite)
        r = self._volta(c, state)
        self.assertEqual(r.status_code, 302, r.get_data(as_text=True)[:300])
        self.assertIn("Set-Cookie", r.headers, "devia ter aberto sessão")

    def test_volta_SEM_liga_a_com_a_porta_fechada_continua_403(self):
        """Um `state` que não nasceu de um convite não passa a porta fechada."""
        c = self.cliente(aberto=False, **GOOGLE)
        con = self.auth.abrir()
        try:
            r = self.auth.comecar(con, "google",
                                  redirect_uri="http://x/entrar/google",
                                  cfg=self.config.load())
        finally:
            con.close()
        c.set_cookie(self.auth.COOKIE_NONCE, r["nonce"])
        resp = self._volta(c, r["state"])
        self.assertEqual(resp.status_code, 403)
        self.assertNotIn("riftvault_sessao", resp.headers.get("Set-Cookie", ""))

    def test_volta_com_state_inventado_e_porta_fechada_403(self):
        c = self.cliente(aberto=False, **GOOGLE)
        self.assertEqual(self._volta(c, "inventado").status_code, 403)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

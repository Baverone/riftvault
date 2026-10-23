"""Os bugs da ronda de 2026-10-23 (só bugs). Cada teste foi visto a CHUMBAR
contra o `main` de 23/10 antes da correcção. Tudo contra pastas temporárias;
nunca a rede nem o `data/` a sério.

1. O `api_sort` da RAD em duas numerações: as linhas da dotgg ficavam com os
   números da lista da dotgg (0..231), que colidiam com os da RiftScribe
   (0..218) — no `catalog.db` real, `rad-015-p` e `rad-018` com 34.
2. Selado: qualquer resposta que não fosse 200 apagava a imagem; só um 404/410
   é definitivo.
3. Porta fechada e o Google a voltar com `?error=access_denied` (a pessoa
   cancelou): dava «porta fechada» em vez de «o fornecedor recusou».
4. `utilizador.apresentacao` com o registo partido devolvia o André para
   qualquer dono.
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

from tests.test_radiance_dotgg import DOTGG, Base as BaseRad, _rs  # noqa: E402
from tests.test_contas import Base as BaseContas  # noqa: E402
from tests import test_sites_rift_1020 as s1020  # noqa: E402

# ---------------------------------------------------------------------------
# 1 · o api_sort da RAD
# ---------------------------------------------------------------------------

# A RAD de brincar como a RiftScribe a dá, pela ordem DELA (a medida no
# catálogo real: o número nunca desce, a família principal primeiro e as séries
# a seguir). Não traz as promos de evento nem a runa em alt art.
RIFTSCRIBE_ORDEM = [
    _rs("rad-001-005", 1, "", "RAD-001/005", "Ahri, Confident", "common"),
    _rs("rad-001a-005", 1, "a", "RAD-001a/005", "Ahri, Confident", "showcase"),
    _rs("rad-r01", 1, "r01", "RAD-R01", "Fury Rune", "common", tipo="Rune", dominios=("Fury",)),
    _rs("rad-sp1-001", 1, "sp1", "RAD-SP1/001", "Ahri, Confident", "epic"),
    _rs("rad-002-005", 2, "", "RAD-002/005", "Boy Who Shattered Time", "rare", tipo="Legend",
        dominios=("Body", "Mind")),
    _rs("rad-t02", 2, "t02", "RAD-T02", "Bomb", "common", tipo="Gear", dominios=("Colorless",)),
    _rs("rad-003-005", 3, "", "RAD-003/005", "Packed Amphitheater", "uncommon",
        tipo="Battlefield", dominios=("Colorless",)),
    _rs("rad-006-005", 6, "", "RAD-006/005", "Boy Who Shattered Time", "showcase",
        tipo="Legend", dominios=("Body", "Mind")),
    _rs("rad-006-star-005", 6, "star", "RAD-006*/005", "Boy Who Shattered Time",
        "showcase", tipo="Legend", dominios=("Body", "Mind")),
]

ESPERADA = [
    "rad-001", "rad-001a", "rad-001-p", "rad-001-p2", "rad-r01", "rad-r01a", "rad-sp1",
    "rad-002", "rad-t02",
    "rad-003",
    "rad-006", "rad-006-star",
]


class TestApiSortDaRad(BaseRad):
    def ordem(self):
        return [r[0] for r in self.con.execute(
            "SELECT printing_id FROM catalog.printings WHERE set_id = 'RAD' "
            "ORDER BY api_sort, printing_id")]

    def sorts(self):
        return [r[0] for r in self.con.execute(
            "SELECT api_sort FROM catalog.printings WHERE set_id = 'RAD'")]

    def test_depois_da_riftscribe_nao_ha_empates(self):
        self.sync_riftscribe(RIFTSCRIBE_ORDEM)
        s = self.sorts()
        self.assertEqual(len(s), len(set(s)), f"api_sort repetidos: {sorted(s)}")

    def test_depois_da_riftscribe_as_da_dotgg_ficam_no_sitio(self):
        self.sync_riftscribe(RIFTSCRIBE_ORDEM)
        self.assertEqual(self.ordem(), ESPERADA)

    def test_a_dotgg_outra_vez_por_cima_nao_desarruma(self):
        self.sync_riftscribe(RIFTSCRIBE_ORDEM)
        self.dotgg.sync(linhas_api=DOTGG, log=lambda *_: None)
        self.assertEqual(self.ordem(), ESPERADA)
        s = self.sorts()
        self.assertEqual(len(s), len(set(s)))

    def test_a_riftscribe_outra_vez_nao_desarruma(self):
        self.sync_riftscribe(RIFTSCRIBE_ORDEM)
        self.dotgg.sync(linhas_api=DOTGG, log=lambda *_: None)
        self.sync_riftscribe(RIFTSCRIBE_ORDEM)
        self.assertEqual(self.ordem(), ESPERADA)

    def test_uma_edicao_so_da_riftscribe_nao_muda(self):
        """O arrumar só mexe quando há mais do que uma fonte na edição: uma
        edição só da RiftScribe fica com os números que ela deu."""
        api = [{**c, "set_id": "ZZZ", "id": c["id"].replace("rad", "zzz"),
                "public_code": c["public_code"].replace("RAD", "ZZZ")}
               for c in RIFTSCRIBE_ORDEM]
        with mock.patch.object(self.riftscribe, "list_sets", lambda: ["ZZZ"]), \
             mock.patch.object(self.riftscribe, "iter_cards", lambda sid, delay=0: iter(api)):
            self.cat.sync(["ZZZ"], delay=0, log=lambda *_: None)
        got = {r[0]: r[1] for r in self.con.execute(
            "SELECT printing_id, api_sort FROM catalog.printings WHERE set_id = 'ZZZ'")}
        self.assertEqual(got, {c["id"].replace("rad", "zzz"): i for i, c in enumerate(api)})


# ---------------------------------------------------------------------------
# 2 · a imagem do Selado só sai com uma resposta DEFINITIVA
# ---------------------------------------------------------------------------

class TestImagemDoSelado(s1020.TestR1Gerador):

    def _correr(self, resposta):
        self.selado.sincronizar(ct=self.ct(), log=lambda *a: None, intervalo=0,
                                com_precos=False,
                                sonda_imagem=lambda url: resposta if "morta" in url else 200)
        self.selado._cache = None
        return {p["blueprint_id"]: p for p in self.selado.carregar()["produtos"]}

    def test_uma_falha_passageira_mantem_a_imagem(self):
        for resposta in (429, 500, 503, "ConnectionError", "ReadTimeout"):
            with self.subTest(resposta=resposta):
                por = self._correr(resposta)
                self.assertEqual(por[78]["img"], "https://x/morta.jpg")
                self.assertNotIn("img_falhou", por[78])

    def test_um_404_ou_410_tira_a_imagem(self):
        for resposta in (404, 410):
            with self.subTest(resposta=resposta):
                por = self._correr(resposta)
                self.assertIsNone(por[78]["img"])
                self.assertEqual(por[78]["img_falhou"], "https://x/morta.jpg")


class TestOTesteDoCatalogoNaoRebentaSemImagem(unittest.TestCase):
    """O `test_sites_rift_1020` lia o `img` do catálogo commitado e rebentava
    com `TypeError` quando ele vinha `None` — o teste dependia da rede do dia
    do `--sync`. Corre-se a mesma função com um produto sem imagem."""

    def test_sem_imagem_nao_e_type_error(self):
        import tests.test_sites_rift_1020 as t
        sem = {"blueprint_id": 408707, "nome": "Radiance | Nexus Night Promo Booster",
               "edicao": "RAD", "img": None,
               "img_falhou": "https://cardtrader.com/uploads/x.jpg"}
        with mock.patch.object(t, "produto", lambda bid: sem):
            caso = t.TestR1Imagem("test_o_408707_tem_a_imagem_actual_do_cardtrader")
            res = unittest.TestResult()
            caso.run(res)
        self.assertEqual(res.errors, [], res.errors and res.errors[0][1][-400:])


# ---------------------------------------------------------------------------
# 3 · a porta fechada e o cancelamento no Google
# ---------------------------------------------------------------------------

GOOGLE = {"auth": {"google": {"client_id": "cid", "client_secret": "sec"}}}


class TestCancelarNoGoogleComAPortaFechada(BaseContas):
    def setUp(self):
        super().setUp()
        self.addCleanup(lambda: os.environ.pop("RIFTVAULT_GOOGLE_SECRET", None))

    def _ida(self, c, convite):
        r = c.get(f"/entrar/google?ligar={convite}")
        self.assertEqual(r.status_code, 302, r.get_data(as_text=True)[:200])
        from urllib.parse import parse_qs, urlsplit
        return parse_qs(urlsplit(r.headers["Location"]).query)["state"][0]

    def _falhas(self):
        con = self.auth.abrir()
        try:
            return con.execute("SELECT COUNT(*) FROM auth_tentativas WHERE ok = 0").fetchone()[0]
        finally:
            con.close()

    def test_cancelar_com_convite_diz_que_o_fornecedor_recusou(self):
        c = self.cliente(aberto=False, **GOOGLE)
        con = self.auth.abrir()
        try:
            convite = self.auth.criar_convite(con, 1)
        finally:
            con.close()
        state = self._ida(c, convite)
        antes = self._falhas()
        r = c.get(f"/entrar/google?error=access_denied&state={state}")
        self.assertEqual(r.status_code, 400, r.get_data(as_text=True)[:300])
        self.assertIn("recusou", r.get_data(as_text=True))
        self.assertEqual(self._falhas(), antes + 1, "a tentativa falhada regista-se")

    def test_error_com_state_inventado_continua_porta_fechada(self):
        c = self.cliente(aberto=False, **GOOGLE)
        r = c.get("/entrar/google?error=access_denied&state=inventado")
        self.assertEqual(r.status_code, 403)

    def test_error_sem_state_continua_porta_fechada(self):
        c = self.cliente(aberto=False, **GOOGLE)
        r = c.get("/entrar/google?error=access_denied")
        self.assertEqual(r.status_code, 403)

    def test_error_com_state_sem_liga_a_continua_porta_fechada(self):
        c = self.cliente(aberto=False, **GOOGLE)
        con = self.auth.abrir()
        try:
            p = self.auth.comecar(con, "google", redirect_uri="http://x/entrar/google",
                                  cfg=self.config.load())
        finally:
            con.close()
        r = c.get(f"/entrar/google?error=access_denied&state={p['state']}")
        self.assertEqual(r.status_code, 403)


# ---------------------------------------------------------------------------
# 4 · a apresentação do dono com o registo partido
# ---------------------------------------------------------------------------

class TestApresentacaoComORegistoPartido(unittest.TestCase):
    def setUp(self):
        from riftvault import utilizador
        self.u = utilizador

    def _partido(self, uid):
        def rebenta(*a, **k):
            raise RuntimeError("registo partido")
        with mock.patch.object(self.u, "registo", rebenta):
            return self.u.apresentacao(uid)

    def test_outro_dono_nao_passa_a_ser_o_andre(self):
        d = self._partido(2)
        self.assertFalse(d["andre"])
        self.assertNotEqual(d["slug"], self.u.SLUG_ANDRE)
        self.assertNotEqual(d["nome"], self.u.NOME_ANDRE)

    def test_o_andre_com_o_registo_partido_continua_a_ser_o_andre(self):
        """O clone fresco (sem registo) é a página dele — não se finge nada."""
        d = self._partido(self.u.ANDRE)
        self.assertTrue(d["andre"])
        self.assertEqual(d["slug"], self.u.SLUG_ANDRE)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

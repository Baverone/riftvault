"""PRIVACIDADE POR UTILIZADOR, contra o `build.py` (2026-09-29).

Da ordem: *"O site público dele mostra hoje a coleção inteira e o valor em
euros a quem tiver o link. Os amigos vão presumir que o deles é privado."*

O campo é `users.publico`, a omissão é **a mais fechada**, e o que se prova
aqui são os TRÊS VALORES contra o site que sai mesmo:

    nada          não se gera pasta nenhuma
    sem-valores   gera a coleção, e nenhum euro em lado nenhum
    tudo          como o site dele hoje

A parte pura — a regra sobre um payload — está no `test_privacidade_filtro.py`.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

from riftvault import (build, collection, config, db, multi, privacidade,
                       utilizador)
from tests import fixture
from tests.test_privacidade_filtro import numeros, quantias_vivas

#: Preços inconfundíveis. Um preço pequeno em cêntimos COLIDE com uma contagem
#: (medido no site real: o 3195 é ao mesmo tempo o número de cópias da coleção
#: e o preço de uma carta). Com estes, qualquer sobrevivente é uma fuga.
SENTINELAS = {"tst-001-100": 777701, "tst-002-100": 777702,
              "tst-003-100": 777703}


class Base(unittest.TestCase):

    def setUp(self):
        fixture.config_decks_sem_alt_art(self)
        self.v = fixture.Vault()
        self.addCleanup(self.v.close)
        con = self.v.connect()
        self.v.add_printing(con, "tst-001-100", "TST", 1, "Defy")
        self.v.add_printing(con, "tst-002-100", "TST", 2, "Brutalizer")
        self.v.add_printing(con, "tst-003-100", "TST", 3, "Emperor of the Sands",
                            card_type="Legend")
        self.v.rebuild(con)
        for pid, c in SENTINELAS.items():
            con.execute("INSERT OR REPLACE INTO catalog.price_latest "
                        "(printing_id, price_cents, currency, source, day) "
                        "VALUES (?,?,'EUR','test','2026-09-29')", (pid, c))
        collection.adjust(con, "tst-001-100", 1, source="test")
        con.close()

    def gerar(self, modo: str, user_id: int = utilizador.ANDRE,
              pasta: str = "site") -> Path:
        # A escolha vive no REGISTO, não na base de cartas: `con=None`.
        privacidade.definir(None, user_id, modo)
        out = self.v.root / pasta
        build.build(out, log=lambda *_: None, user_id=user_id)
        return out

    def json_todos(self, out: Path):
        return {p.relative_to(out).as_posix():
                json.loads(p.read_text(encoding="utf-8"))
                for p in sorted(out.rglob("*.json"))}


class TestOsTresValores(Base):

    def test_tudo_gera_o_site_inteiro_com_os_precos(self):
        out = self.gerar("tudo")
        d = self.json_todos(out)
        self.assertIn("api/index.json", d)
        vivos = numeros(d) & set(SENTINELAS.values())
        self.assertTrue(vivos, "em «tudo» os preços TÊM de aparecer")

    def test_sem_valores_gera_a_coleccao_sem_um_unico_euro(self):
        out = self.gerar("sem-valores")
        d = self.json_todos(out)
        self.assertIn("api/index.json", d, "a coleção tem de continuar a sair")
        self.assertIn("api/set/TST.json", d)
        # rede A
        for nome, payload in d.items():
            with self.subTest(ficheiro=nome):
                self.assertEqual(quantias_vivas(payload), [],
                                 f"{nome}: sobrou uma quantia")
        # rede B
        vazou = numeros(d) & set(SENTINELAS.values())
        self.assertEqual(vazou, set(), f"vazaram preços: {sorted(vazou)}")

    def test_sem_valores_mantem_as_contagens(self):
        """Uma página sem euros continua a ser uma página da coleção."""
        out = self.gerar("sem-valores")
        idx = json.loads((out / "api" / "index.json").read_text(encoding="utf-8"))
        self.assertEqual(idx["totals"]["copies"], 1)
        niveis = idx["levels"]["levels"]
        self.assertEqual(niveis[0]["total"], 3, "o denominador desapareceu")
        self.assertIsNone(niveis[0]["cents"])

    def test_nada_nao_gera_pasta_nenhuma(self):
        privacidade.definir(None, utilizador.ANDRE, "nada")
        out = self.v.root / "site-nada"
        build.build(out, log=lambda *_: None)
        self.assertFalse((out / "api" / "index.json").exists(),
                         "gerou site para quem escolheu «nada»")

    def test_os_tres_sao_mesmo_diferentes(self):
        a = self.json_todos(self.gerar("tudo", pasta="s1"))
        b = self.json_todos(self.gerar("sem-valores", pasta="s2"))
        self.assertNotEqual(json.dumps(a, sort_keys=True, default=str),
                            json.dumps(b, sort_keys=True, default=str))


class TestOCampo(Base):

    def test_a_omissao_e_a_mais_fechada(self):
        """Um utilizador novo NÃO tem site público até o pedir."""
        u = utilizador.criar("Miguel", "miguel")
        self.assertEqual(privacidade.de(None, u["user_id"]), "nada")

    def test_o_andre_fica_em_tudo_porque_e_o_que_ja_tem(self):
        self.assertEqual(privacidade.de(None, utilizador.ANDRE), "tudo")

    def test_um_valor_inventado_rebenta(self):
        with self.assertRaises(privacidade.ValorInvalido):
            privacidade.definir(None, utilizador.ANDRE, "privado")

    def test_a_base_tambem_recusa_um_valor_inventado(self):
        """O `CHECK` da coluna é a segunda rede: nem por SQL à mão."""
        con = utilizador.abrir_registo()
        self.addCleanup(con.close)
        import sqlite3
        with self.assertRaises(sqlite3.IntegrityError):
            con.execute("UPDATE users SET publico = 'privado' WHERE user_id = 1")

    def test_a_escolha_vive_no_REGISTO_e_nao_na_base_de_cartas(self):
        """Quem lê a privacidade — uma rota, o `build` — não tem motivo
        nenhum para ter a coleção de alguém aberta."""
        u = utilizador.criar("Zeca", "zeca")
        privacidade.definir(None, u["user_id"], "sem-valores")
        reg = utilizador.abrir_registo()
        self.addCleanup(reg.close)
        self.assertEqual(
            reg.execute("SELECT publico FROM users WHERE user_id = ?",
                        (u["user_id"],)).fetchone()[0], "sem-valores")
        # e a cópia dentro da base dele acompanha, para o ficheiro se explicar
        con = db.connect(user_id=u["user_id"])
        self.addCleanup(con.close)
        self.assertEqual(
            con.execute("SELECT publico FROM users WHERE user_id = ?",
                        (u["user_id"],)).fetchone()[0], "sem-valores")


class TestPortasFechadas(Base):
    """Ponto 9: *"Quero apenas apresentar quando tiver tudo"*."""

    def test_o_interruptor_nasce_fechado(self):
        self.assertFalse(multi.aberto({}))
        self.assertFalse(multi.aberto(config.DEFAULTS))

    def test_fechado_nao_publica_a_pagina_de_outro_utilizador(self):
        u = utilizador.criar("Miguel", "miguel")
        con = db.connect(user_id=u["user_id"])
        collection.adjust(con, "tst-002-100", 2, source="test")
        privacidade.definir(None, u["user_id"], "tudo")  # ele até QUER
        con.close()
        out = self.v.root / "site"
        build.build_todos(out, log=lambda *_: None, cfg={"multi": {"aberto": False}})
        self.assertTrue((out / "api" / "index.json").exists(), "o dele tem de sair")
        self.assertFalse((out / "u" / "miguel").exists(),
                         "publicou a página de um amigo com as portas fechadas")

    def test_aberto_ja_publica(self):
        """A prova pela negativa: o mecanismo existe e é o interruptor que o
        trava. Sem isto, «não publica» podia ser «não sabe fazer»."""
        u = utilizador.criar("Miguel", "miguel")
        con = db.connect(user_id=u["user_id"])
        collection.adjust(con, "tst-002-100", 2, source="test")
        privacidade.definir(None, u["user_id"], "tudo")
        con.close()
        out = self.v.root / "site-aberto"
        build.build_todos(out, log=lambda *_: None, cfg={"multi": {"aberto": True}})
        self.assertTrue((out / "u" / "miguel" / "api" / "index.json").exists())

    def test_aberto_mas_privado_continua_sem_pagina(self):
        u = utilizador.criar("Zeca", "zeca")
        con = db.connect(user_id=u["user_id"])
        collection.adjust(con, "tst-002-100", 2, source="test")
        con.close()   # fica em «nada», que é a omissão
        out = self.v.root / "site-aberto2"
        build.build_todos(out, log=lambda *_: None, cfg={"multi": {"aberto": True}})
        self.assertFalse((out / "u" / "zeca").exists())

    def test_o_SITE_DELE_e_igual_com_o_interruptor_de_um_lado_e_do_outro(self):
        """Checklist 17: com as portas fechadas o site dele fica como hoje.

        E ABRIR as portas também não lhe muda o SITE — muda-lhe o SÍTIO, e é
        decisão dele de 2026-09-30: *"quando se abre o Riftbound, vai ter lá
        as coleções: Baverone / Miguel / Rafa"*. A partir da segunda coleção
        pública a raiz é a lista e a dele passa a `u/baverone/`, com o mesmo
        conteúdo ficheiro a ficheiro. Ver `test_lista.py`.
        """
        u = utilizador.criar("Miguel", "miguel")
        con = db.connect(user_id=u["user_id"])
        collection.adjust(con, "tst-002-100", 2, source="test")
        privacidade.definir(None, u["user_id"], "tudo")
        con.close()
        f = self.v.root / "fechado"
        a = self.v.root / "aberto"
        build.build_todos(f, log=lambda *_: None, cfg={"multi": {"aberto": False}})
        build.build_todos(a, log=lambda *_: None, cfg={"multi": {"aberto": True}})
        self.assertTrue(build.mesmo_conteudo(f, a / "u" / "baverone"),
                        "abrir as portas mudou o CONTEÚDO do site dele")

    def test_com_o_miguel_privado_a_raiz_continua_a_ser_a_dele(self):
        """A lista só toma a raiz quando há mesmo mais do que uma coleção.

        É a prova pela negativa do teste de cima: não é «abrir as portas» que
        muda a raiz, é haver uma segunda coleção PÚBLICA.
        """
        u = utilizador.criar("Miguel", "miguel")
        con = db.connect(user_id=u["user_id"])
        collection.adjust(con, "tst-002-100", 2, source="test")
        con.close()   # fica em «nada»
        f = self.v.root / "fechado2"
        a = self.v.root / "aberto2"
        build.build_todos(f, log=lambda *_: None, cfg={"multi": {"aberto": False}})
        build.build_todos(a, log=lambda *_: None, cfg={"multi": {"aberto": True}})
        self.assertTrue(build.mesmo_conteudo_raiz(f, a),
                        "abrir as portas mudou o site DELE")

    def test_nao_ha_sinal_de_login_no_html(self):
        """*"nada de «em breve», nada de link de login a espreitar"*.

        Os COMENTÁRIOS do HTML não contam, e é preciso dizê-lo: o comentário que
        explica esta própria decisão (a `#conta-zona` da fatia `2-multi-contas`)
        escreve a palavra «login», e a primeira versão deste teste — e a do
        `test_contas.py`, que tinha o mesmo defeito — apanhava-se a si própria. O
        que se mede é o que o browser MOSTRA, não o que os comentários dizem.
        """
        import re
        out = self.gerar("tudo")
        bruto = (out / "index.html").read_text(encoding="utf-8")
        html = re.sub(r"<!--.*?-->", "", bruto, flags=re.S).lower()
        for palavra in ("em breve", "login", "iniciar sessão", "entrar com",
                        "criar conta", "registar"):
            self.assertNotIn(palavra, html, f"o site dele fala de «{palavra}»")
        # E o elemento da conta existe mas nasce escondido — é o JS que o abre,
        # e só quando o `api/conta.json` disser que as contas estão abertas.
        self.assertIn('id="conta-zona"', bruto)
        zona = bruto.split('id="conta-zona"')[1][:80]
        self.assertIn("hidden", zona, "a zona da conta tem de nascer escondida")

    def test_nao_ha_cloudflared_no_repositorio(self):
        """Checklist 18: o túnel não se liga nesta fase."""
        raiz = Path(__file__).resolve().parent.parent
        maus = []
        for p in list(raiz.glob("*")) + list((raiz / "riftvault").glob("*")):
            if "cloudflared" in p.name.lower() or p.name in ("config.yml",
                                                             "cert.pem"):
                maus.append(p.name)
        self.assertEqual(maus, [], f"há configuração de túnel: {maus}")

    def test_nao_ha_utilizadores_criados_no_config_real(self):
        """*"SEM registo, SEM convites, SEM contas de amigos criadas"* — e o
        interruptor do config real tem de estar mesmo fechado."""
        raiz = Path(__file__).resolve().parent.parent
        bruto = json.loads((raiz / "riftvault_config.json").read_text(
            encoding="utf-8"))
        self.assertIs((bruto.get("multi") or {}).get("aberto", False), False,
                      "o `multi.aberto` do config REAL não está fechado")

    def test_so_ha_um_utilizador_no_registo_real(self):
        """*"SEM registo, SEM convites, SEM contas de amigos criadas"*. As
        contas de teste vivem nos testes e na base de ensaio — nunca na real."""
        raiz = Path(__file__).resolve().parent.parent
        registo = raiz / "data" / "users" / "registo.db"
        if not registo.exists():
            self.skipTest("ainda não há registo em disco")
        import sqlite3
        con = sqlite3.connect(registo)
        try:
            n = con.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            slugs = [r[0] for r in con.execute("SELECT slug FROM users")]
        finally:
            con.close()
        self.assertEqual(n, 1, f"há contas a mais no registo real: {slugs}")
        self.assertEqual(slugs, [utilizador.SLUG_ANDRE])


class TestOSitioParaPartirCoisas(unittest.TestCase):
    """O ENSAIO (`RIFTVAULT_ENSAIO=1`) — ponto 8 da ordem.

    Corre em SUBPROCESSOS porque o `config` lê o ambiente na IMPORTAÇÃO: é
    isso que faz o ensaio ser impossível de ligar a meio de uma corrida, e é
    isso que se está a testar.
    """

    CODIGO = "\n".join((
        "import sys, json",
        "sys.path.insert(0, r'{raiz}')",
        "from riftvault import multi, config",
        "print(json.dumps({{'ensaio': multi.ensaio(),",
        "  'dados': config.DATA_DIR.name, 'config': config.CONFIG_PATH.name,",
        "  'porta': multi.porta(), 'anfitriao': multi.anfitriao(),",
        "  'aberto': multi.aberto()}}))",
    ))

    def correr(self, **ambiente):
        import json as _json
        import os
        import subprocess
        raiz = Path(__file__).resolve().parent.parent
        amb = {k: v for k, v in os.environ.items()
               if not k.startswith("RIFTVAULT_")}
        amb.update(ambiente)
        r = subprocess.run(
            [sys.executable, "-X", "utf8", "-c",
             self.CODIGO.format(raiz=raiz)],
            capture_output=True, text=True, encoding="utf-8", env=amb)
        return r, (_json.loads(r.stdout) if r.returncode == 0 else None)

    def test_sem_a_variavel_e_tudo_como_sempre(self):
        _, d = self.correr()
        self.assertFalse(d["ensaio"])
        self.assertEqual(d["dados"], "data")
        self.assertEqual(d["config"], "riftvault_config.json")
        self.assertEqual(d["porta"], 8770)
        self.assertEqual(d["anfitriao"], "0.0.0.0")

    def test_com_a_variavel_muda_os_tres(self):
        _, d = self.correr(RIFTVAULT_ENSAIO="1")
        self.assertTrue(d["ensaio"])
        self.assertEqual(d["dados"], "data-ensaio")
        self.assertEqual(d["config"], "riftvault_config-ensaio.json")

    def test_O_ENSAIO_NAO_ESCUTA_NA_PORTA_DO_TUNEL(self):
        """A garantia de que o túnel nunca aponta para uma experiência, e é
        por construção: o túnel serve a 8770 e o ensaio recusa-a."""
        _, d = self.correr(RIFTVAULT_ENSAIO="1")
        self.assertEqual(d["porta"], multi.PORTA_ENSAIO)
        self.assertNotEqual(d["porta"], multi.PORTA_PRODUCAO)
        self.assertEqual(d["anfitriao"], "127.0.0.1",
                         "o ensaio saiu do loopback — fica ao alcance da LAN")

    def test_pedir_a_8770_em_ensaio_rebenta(self):
        raiz = Path(__file__).resolve().parent.parent
        import os
        import subprocess
        amb = {k: v for k, v in os.environ.items()
               if not k.startswith("RIFTVAULT_")}
        amb["RIFTVAULT_ENSAIO"] = "1"
        r = subprocess.run(
            [sys.executable, "-X", "utf8", "-c", "\n".join((
                f"import sys; sys.path.insert(0, r'{raiz}')",
                "from riftvault import multi",
                "multi.porta(8770)"))],
            capture_output=True, text=True, encoding="utf-8", env=amb)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("PortaDeProducao", r.stderr)

    def test_o_ensaio_recusa_o_data_a_serio(self):
        """O erro que isto existe para não deixar cometer: correr uma
        experiência com a coleção verdadeira por baixo."""
        raiz = Path(__file__).resolve().parent.parent
        r, _ = self.correr(RIFTVAULT_ENSAIO="1",
                           RIFTVAULT_DATA=str(raiz / "data"))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("RIFTVAULT_ENSAIO", r.stderr)
        self.assertIn("a coleção a sério", r.stderr)

    def test_exigir_ensaio_so_passa_em_ensaio(self):
        with self.assertRaises(multi.SoEmEnsaio) as e:
            multi.exigir_ensaio("fornecedor de mentira")
        self.assertIn("RIFTVAULT_ENSAIO", str(e.exception))

    def test_o_ensaio_nao_e_uma_chave_do_config(self):
        """De propósito: uma chave de ensaio dentro de um ficheiro que vai
        para o Git está a um merge de distância de ir para produção ligada."""
        raiz = Path(__file__).resolve().parent.parent
        bruto = (raiz / "riftvault_config.json").read_text(encoding="utf-8")
        self.assertNotIn("ensaio", bruto.lower())
        fonte = (raiz / "riftvault" / "multi.py").read_text(encoding="utf-8")
        self.assertIn("RIFTVAULT_ENSAIO", fonte)


if __name__ == "__main__":
    unittest.main(verbosity=2)

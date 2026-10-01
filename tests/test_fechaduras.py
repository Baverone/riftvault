"""AS FECHADURAS: quatro defeitos das contas, corrigidos a 2026-10-01.

Cada classe é um defeito, e cada uma tem pelo menos um teste que **falha no
código de antes** — não é um relatório, é a prova.

  1. **A TROCA DE PASSWORD NÃO TINHA TRAVÃO.** A rota registava a falha
     (`registar_tentativa`) e nunca chamava o travão: quem tivesse uma sessão
     martelava a password ACTUAL sem limite nenhum, a 130 ms e 64 MB de scrypt
     por palpite. A entrada chamava-o, e até havia um comentário a explicar que
     corre ANTES do scrypt; aqui não havia nada.

  2. **DAVA PARA TRANCAR UM AMIGO DE FORA** («tranca-o-amigo»). O travão contava
     por CONTA e recusava antes de verificar — e os nomes das contas estão
     PÚBLICOS em `rift.baverone.com/api/lista.json`. Meia dúzia de falhas de
     propósito e a pessoa não entrava, com a espera a renovar-se a cada falha
     nova. Hoje o travão da conta corre DEPOIS da verificação: quem sabe a
     password entra sempre, e quem está a adivinhar leva a mesma espera de
     antes.

  3. **A MEMÓRIA DO SCRYPT NÃO TINHA TECTO.** O servidor é `threaded` e cada
     verificação reserva 64 MB; nada contava quantas corriam ao mesmo tempo. O
     tecto não é por desempenho (medido: 32 em paralelo nesta máquina são
     276 ms) — é porque o `senha.confere` apanha o `MemoryError` e devolve
     **False**: com a memória a faltar, uma password CERTA saía errada e ainda
     contava para o travão.

  4. **AS SESSÕES EXPIRADAS NUNCA SAÍAM DA TABELA.** O `limpar_expiradas` e o
     `limpar_pedidos` existiam desde 2026-09-29 e **nunca eram chamados de
     sítio nenhum**. Não era um buraco; era lixo a crescer, com o índice para o
     limpar já feito.

Tudo contra pastas temporárias (`tests.fixture.Vault`) e um config temporário:
o `data/` e o `riftvault_config.json` a sério nunca são tocados.
"""

from __future__ import annotations

import importlib
import json
import os
import sys
import tempfile
import threading
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ["RIFTVAULT_CONFIG"] = str(
    Path(tempfile.gettempdir()) / "riftvault-nao-existe.json")

from tests.fixture import REPO, Vault  # noqa: E402

SENTINELA = "zqx-segredo-do-miguel-742981"
OUTRA = "uma-frase-nova-que-serve-bem"


class Base(unittest.TestCase):
    """O mesmo arranque do `test_senhas.py` — ver lá a razão de cada linha."""

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
        self.auth, self.senha, self.multi = auth, senha, multi
        self.utilizador, self.config, self.db = utilizador, config, db
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

    def com_senha(self, slug: str, password: str, nome: str = "") -> int:
        u = self.utilizador.criar(nome or slug, slug)
        con = self.auth.abrir()
        try:
            self.auth.definir_senha(con, int(u["user_id"]), password,
                                    temporaria=False)
        finally:
            con.close()
        return int(u["user_id"])

    def entrar(self, c, slug: str, password: str) -> str:
        r = c.post("/api/conta/entrar", json={"nome": slug, "senha": password})
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True)[:400])
        return r.get_json()["csrf"]

    def sem_vagas(self):
        """Ocupa a fila toda e devolve-a no fim do teste, com uma espera curta."""
        antes = self.auth.ESPERA_POR_VAGA_S
        apanhadas = [self.auth._VAGAS.acquire(timeout=1)
                     for _ in range(self.auth.VAGAS_DE_SCRYPT)]
        self.assertTrue(all(apanhadas), "a fila devia estar livre")
        self.auth.ESPERA_POR_VAGA_S = 0.2

        def devolver():
            self.auth.ESPERA_POR_VAGA_S = antes
            for _ in apanhadas:
                self.auth._VAGAS.release()

        self.addCleanup(devolver)

    def falhas(self, con, **onde) -> int:
        chave, valor = next(iter(onde.items()))
        return con.execute(
            f"SELECT COUNT(*) AS n FROM auth_tentativas "  # noqa: S608
            f"WHERE {chave} = ? AND ok = 0", (valor,)).fetchone()["n"]


# --------------------------------------------------------------------------
# DEFEITO 1 — a troca de password não tinha travão
# --------------------------------------------------------------------------


class TestOTravaoDaTroca(Base):
    """A rota da troca registava a falha e nunca travava nada."""

    def test_martelar_a_password_actual_acaba_por_ser_travado(self):
        """FALHA NO CÓDIGO DE ANTES: dava 403 para sempre, sem limite nenhum."""
        c = self.cliente(aberto=True)
        self.com_senha("miguel", SENTINELA)
        csrf = self.entrar(c, "miguel", SENTINELA)
        corpo = {"atual": "nao-e-esta", "nova": OUTRA}
        cab = {"X-CSRF-Token": csrf}

        # As cinco de graça: a password ditada escreve-se mal duas ou três vezes.
        for i in range(5):
            r = c.post("/api/conta/senha", json=corpo, headers=cab)
            self.assertEqual(r.status_code, 403, f"tentativa {i + 1}: {r.get_json()}")

        r = c.post("/api/conta/senha", json=corpo, headers=cab)
        self.assertEqual(r.status_code, 429,
                         "a sexta tentativa tinha de ser travada")
        self.assertIn("Espera", r.get_json()["erro"])

    def test_a_falha_da_troca_continua_a_contar_para_a_entrada(self):
        """Era o único efeito que a rota tinha antes, e não se perdeu."""
        c = self.cliente(aberto=True)
        uid = self.com_senha("miguel", SENTINELA)
        csrf = self.entrar(c, "miguel", SENTINELA)
        c.post("/api/conta/senha", json={"atual": "errada", "nova": OUTRA},
               headers={"X-CSRF-Token": csrf})
        con = self.auth.abrir()
        try:
            self.assertEqual(self.falhas(con, user_id=uid), 1)
        finally:
            con.close()

    def test_o_travao_da_troca_e_o_MESMO_da_entrada(self):
        """Uma política, um sítio: falhar a trocar gasta as mesmas cinco."""
        c = self.cliente(aberto=True)
        self.com_senha("miguel", SENTINELA)
        csrf = self.entrar(c, "miguel", SENTINELA)
        for _ in range(6):
            c.post("/api/conta/senha", json={"atual": "errada", "nova": OUTRA},
                   headers={"X-CSRF-Token": csrf})
        con = self.auth.abrir()
        try:
            # A conta está travada, e por isso a password ERRADA leva 429...
            with self.assertRaises(self.auth.TemDeEsperar):
                self.auth.entrar(con, "miguel", "errada", chave="1.1.1.1")
            # ... mas a CERTA entra, que é o defeito 2.
            self.auth.entrar(con, "miguel", SENTINELA, chave="1.1.1.1")
        finally:
            con.close()

    def test_o_travao_do_sitio_corre_ANTES_do_scrypt_na_troca(self):
        """Senão cada palpite custava 130 ms, que é o que o travão evita."""
        fonte = (REPO / "riftvault" / "auth.py").read_text(encoding="utf-8")
        corpo = fonte.split("def mudar_senha(")[1].split("\ndef ")[0]
        self.assertLess(corpo.index("travao_do_sitio(con"),
                        corpo.index("confere("),
                        "o travão do sítio tem de correr antes do scrypt")
        self.assertGreater(corpo.index("travao_da_conta(con"),
                           corpo.index("confere("),
                           "o travão da conta tem de correr DEPOIS — ver o "
                           "defeito 2")

    def test_a_rota_nao_tem_uma_politica_propria(self):
        """A rota não pode registar falhas por sua conta: dobrava a contagem."""
        fonte = (REPO / "riftvault" / "rotas_conta.py").read_text(
            encoding="utf-8")
        corpo = fonte.split("def mudar_senha(")[1].split("\n@bp.")[0]
        self.assertNotIn("registar_tentativa", corpo,
                         "quem registra a falha é o `auth.mudar_senha`")
        self.assertIn("chave=_chave_do_pedido()", corpo)


# --------------------------------------------------------------------------
# DEFEITO 2 — «tranca-o-amigo»
# --------------------------------------------------------------------------


class TestTrancaOAmigo(Base):
    """O ataque: sei o nome de um amigo (está no site publicado) e falho de
    propósito até ele não conseguir entrar."""

    def test_tranca_o_amigo_nao_tranca_o_amigo(self):
        """FALHA NO CÓDIGO DE ANTES: o Miguel levava 429 com a password certa."""
        self.com_senha("miguel", SENTINELA)
        con = self.auth.abrir()
        try:
            # O atacante, de um sítio qualquer, com o nome que leu na lista
            # pública. Falha o que quiser.
            for _ in range(20):
                try:
                    self.auth.entrar(con, "miguel", "palpite",
                                     chave="203.0.113.9")
                except self.auth.ErroDeAutenticacao:
                    pass
            # O Miguel, de casa dele, com a password DELE.
            quem = self.auth.entrar(con, "miguel", SENTINELA, chave="192.168.1.5")
            self.assertEqual(quem["slug"], "miguel")
        finally:
            con.close()

    def test_tranca_o_amigo_pela_rota_tambem_nao(self):
        """O mesmo ataque, por HTTP, que é como ele chegaria."""
        c = self.cliente(aberto=True)
        self.com_senha("miguel", SENTINELA)
        for _ in range(20):
            c.post("/api/conta/entrar",
                   json={"nome": "miguel", "senha": "palpite"},
                   environ_overrides={"REMOTE_ADDR": "203.0.113.9"})
        r = c.post("/api/conta/entrar",
                   json={"nome": "miguel", "senha": SENTINELA},
                   environ_overrides={"REMOTE_ADDR": "192.168.1.5"})
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True)[:300])

    def test_a_espera_renovavel_era_o_que_tornava_isto_grave(self):
        """Não era «um bloqueio permanente» — era um renovável, que para o dono
        é a mesma coisa. Com o ataque a durar horas, o dono entra na mesma."""
        self.com_senha("miguel", SENTINELA)
        con = self.auth.abrir()
        try:
            for hora in range(3):
                for _ in range(6):
                    try:
                        self.auth.entrar(con, "miguel", "palpite", chave="203.0.113.9")
                    except self.auth.ErroDeAutenticacao:
                        pass
                self.auth.entrar(con, "miguel", SENTINELA, chave="192.168.1.5")
        finally:
            con.close()

    def test_quem_ADIVINHA_continua_travado_do_mesmo_modo(self):
        """O travão não afrouxou: é a metade que justifica a excepção."""
        self.com_senha("miguel", SENTINELA)
        con = self.auth.abrir()
        try:
            for i in range(5):
                with self.assertRaises(self.auth.SenhaErrada, msg=str(i)):
                    self.auth.entrar(con, "miguel", "palpite", chave="203.0.113.9")
            with self.assertRaises(self.auth.TemDeEsperar) as ctx:
                self.auth.entrar(con, "miguel", "palpite", chave="203.0.113.9")
            self.assertIn("nesta conta", str(ctx.exception))
        finally:
            con.close()

    def test_a_escada_continua_a_subir_com_as_falhas_de_hoje(self):
        """Se a falha que trava não fosse registada, a escada parava no 1.º passo."""
        uid = self.com_senha("miguel", SENTINELA)
        con = self.auth.abrir()
        try:
            for _ in range(9):
                try:
                    self.auth.entrar(con, "miguel", "palpite", chave="203.0.113.9")
                except self.auth.ErroDeAutenticacao:
                    pass
            self.assertEqual(self.falhas(con, user_id=uid), 9,
                             "as falhas travadas também se registam")
            with self.assertRaises(self.auth.TemDeEsperar) as ctx:
                self.auth.entrar(con, "miguel", "palpite", chave="203.0.113.9")
            # 9 falhas, 5 de graça -> 4.º patamar da escada: uma hora.
            self.assertEqual(max(self.auth.ESCADA), 3600)
            self.assertGreater(ctx.exception.segundos, 3500)
        finally:
            con.close()

    def test_as_cinco_de_graca_continuam_a_ser_cinco(self):
        """A falha que acabou de acontecer não se conta a si mesma."""
        self.com_senha("miguel", SENTINELA)
        con = self.auth.abrir()
        try:
            for i in range(5):
                with self.assertRaises(self.auth.SenhaErrada, msg=str(i)):
                    self.auth.entrar(con, "miguel", "errada", chave="1.1.1.1")
        finally:
            con.close()

    def test_o_travao_do_sitio_nao_tem_excepcao_nenhuma(self):
        """E não precisa: enchê-lo tranca quem o encheu, nunca outra pessoa."""
        self.com_senha("miguel", SENTINELA)
        con = self.auth.abrir()
        try:
            for i in range(11):
                try:
                    self.auth.entrar(con, f"nao-existe-{i}", "x", chave="7.7.7.7")
                except self.auth.ErroDeAutenticacao:
                    pass
            # Mesmo com a password CERTA: deste endereço não se tenta mais.
            with self.assertRaises(self.auth.TemDeEsperar) as ctx:
                self.auth.entrar(con, "miguel", SENTINELA, chave="7.7.7.7")
            self.assertIn("deste sítio", str(ctx.exception))
            # E de outro endereço entra-se, que é a prova de que o travão do
            # sítio não tranca terceiros.
            self.auth.entrar(con, "miguel", SENTINELA, chave="8.8.8.8")
        finally:
            con.close()

    def test_o_travao_da_conta_nao_esta_a_frente_da_porta(self):
        """A prova pela leitura: na `entrar`, a conta vem depois do `confere`."""
        fonte = (REPO / "riftvault" / "auth.py").read_text(encoding="utf-8")
        corpo = fonte.split("\ndef entrar(")[1].split("\ndef ")[0]
        self.assertLess(corpo.index("travao_do_sitio(con"), corpo.index("confere("))
        self.assertGreater(corpo.index("travao_da_conta(con"), corpo.index("confere("))
        self.assertNotIn("travao(con, uid", corpo,
                         "o travão das duas dimensões de uma vez era o defeito")

    def test_o_porque_esta_escrito_no_codigo(self):
        fonte = (REPO / "riftvault" / "auth.py").read_text(encoding="utf-8")
        self.assertIn("TRANCA-O-AMIGO", fonte)
        self.assertIn("lista.json", fonte,
                      "tem de dizer que os nomes são públicos — é o que torna "
                      "o ataque possível")


# --------------------------------------------------------------------------
# DEFEITO 3 — a memória do scrypt não tinha tecto
# --------------------------------------------------------------------------


class TestOTectoDoScrypt(Base):
    """MEDIDO a 2026-10-01 na máquina dele: 32 núcleos, 31,7 GB (12,1 livres),
    64 MB e 128 ms por verificação; 32 em paralelo são 276 ms e 2 GB, sem um
    erro. O tecto não é de desempenho — ver a classe."""

    def test_ha_um_tecto_e_e_justificado(self):
        self.assertEqual(self.auth.VAGAS_DE_SCRYPT, 8)
        self.assertEqual(self.auth.ESPERA_POR_VAGA_S, 10)
        fonte = (REPO / "riftvault" / "auth.py").read_text(encoding="utf-8")
        bloco = fonte.split("QUANTAS PASSWORDS SE VERIFICAM")[1][:4000]
        for pedaco in ("32 em paralelo", "MemoryError", "12,1 GB"):
            self.assertIn(pedaco, bloco,
                          f"a medição tem de estar escrita: falta «{pedaco}»")

    def test_nunca_correm_mais_do_que_as_vagas_ao_mesmo_tempo(self):
        """FALHA NO CÓDIGO DE ANTES: corriam as 24 ao mesmo tempo."""
        self.com_senha("miguel", SENTINELA)
        a_correr = 0
        pico = 0
        tranca = threading.Lock()
        real = self.senha.confere

        def espiado(guardado, escrita):
            nonlocal a_correr, pico
            with tranca:
                a_correr += 1
                pico = max(pico, a_correr)
            try:
                time.sleep(0.02)   # o scrypt a sério leva 130 ms
                return real(guardado, escrita)
            finally:
                with tranca:
                    a_correr -= 1

        self.senha.confere = espiado
        self.addCleanup(lambda: setattr(self.senha, "confere", real))

        def tenta(i):
            con = self.auth.abrir()
            try:
                self.auth.entrar(con, "miguel", "errada", chave=f"10.0.0.{i}")
            except self.auth.ErroDeAutenticacao:
                pass
            finally:
                con.close()

        fios = [threading.Thread(target=tenta, args=(i,)) for i in range(24)]
        for f in fios:
            f.start()
        for f in fios:
            f.join()
        self.assertGreater(pico, 1, "o teste tem de ser mesmo em paralelo")
        self.assertLessEqual(pico, self.auth.VAGAS_DE_SCRYPT,
                             f"corriam {pico} verificações ao mesmo tempo")

    def test_as_tres_chamadas_ao_scrypt_passam_pela_fila(self):
        """São três e estão todas no `auth.py` — cifrar, entrar e trocar."""
        fonte = (REPO / "riftvault" / "auth.py").read_text(encoding="utf-8")
        for funcao, chamada in (("definir_senha", "cifrar("),
                                ("\ndef entrar(", "confere("),
                                ("def mudar_senha(", "confere(")):
            corpo = fonte.split(funcao)[1].split("\ndef ")[0]
            self.assertIn("_uma_vaga()", corpo, f"{funcao} sem fila")
            self.assertLess(corpo.index("_uma_vaga()"), corpo.index(chamada),
                            f"{funcao}: a vaga tem de ser pedida antes")

    def test_so_o_auth_chama_o_scrypt(self):
        """Se outro módulo o chamasse, a fila não valia nada."""
        for p in sorted((REPO / "riftvault").glob("*.py")):
            if p.name in ("auth.py", "senha.py"):
                continue
            texto = p.read_text(encoding="utf-8")
            for proibido in ("senha.confere(", "senha.cifrar("):
                self.assertNotIn(proibido, texto,
                                 f"{p.name} chama o scrypt por fora da fila")

    def test_sem_vaga_e_503_e_NAO_password_errada(self):
        """É o ponto do defeito: sob pressão de memória o `confere` devolvia
        False, e uma password certa saía «errada» — e contava falha."""
        c = self.cliente(aberto=True)
        uid = self.com_senha("miguel", SENTINELA)
        self.sem_vagas()
        r = c.post("/api/conta/entrar",
                   json={"nome": "miguel", "senha": SENTINELA})
        self.assertEqual(r.status_code, 503, r.get_data(as_text=True)[:300])
        self.assertIn("demasiadas passwords", r.get_json()["erro"])
        con = self.auth.abrir()
        try:
            self.assertEqual(self.falhas(con, user_id=uid), 0,
                             "o servidor ocupado não é uma falha da pessoa")
        finally:
            con.close()

    def test_a_fila_devolve_a_vaga_mesmo_quando_rebenta(self):
        """Uma excepção a meio não pode gastar uma vaga para sempre."""
        antes = self.auth._VAGAS._value
        with self.assertRaises(ZeroDivisionError):
            with self.auth._uma_vaga():
                1 / 0
        self.assertEqual(self.auth._VAGAS._value, antes)

    def test_a_troca_responde_503_e_nao_403(self):
        c = self.cliente(aberto=True)
        self.com_senha("miguel", SENTINELA)
        csrf = self.entrar(c, "miguel", SENTINELA)
        self.sem_vagas()
        r = c.post("/api/conta/senha",
                   json={"atual": SENTINELA, "nova": OUTRA},
                   headers={"X-CSRF-Token": csrf})
        self.assertEqual(r.status_code, 503, r.get_data(as_text=True)[:300])


# --------------------------------------------------------------------------
# DEFEITO 4 — o lixo que só crescia
# --------------------------------------------------------------------------


class TestALimpeza(Base):
    """`limpar_expiradas` e `limpar_pedidos` existiam e ninguém os chamava."""

    def _velha(self, con, user_id: int = 1, marca: str = "") -> str:
        """Uma sessão que já expirou — como uma que ninguém voltou a tocar.

        Escreve-se à mão de propósito: o `criar_sessao` já varre, e passar por
        ele apagava a anterior antes de o teste ter o que medir.
        """
        sid_hash = f"morta-{marca or self._quantas(con, 'sessions')}"
        passado = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        con.execute(
            "INSERT INTO sessions (sid_hash, user_id, csrf, criado_em, "
            "visto_em, expira_em) VALUES (?, ?, 'x', ?, ?, ?)",
            (sid_hash, user_id, passado, passado, passado))
        con.commit()
        return sid_hash

    def _quantas(self, con, tabela: str) -> int:
        return con.execute(f"SELECT COUNT(*) AS n FROM {tabela}"  # noqa: S608
                           ).fetchone()["n"]

    def test_uma_entrada_varre_as_sessoes_mortas(self):
        """FALHA NO CÓDIGO DE ANTES: as linhas mortas ficavam para sempre."""
        self.com_senha("miguel", SENTINELA)
        con = self.auth.abrir()
        try:
            for i in range(5):
                self._velha(con, marca=str(i))
            self.assertEqual(self._quantas(con, "sessions"), 5)
            self.auth.entrar(con, "miguel", SENTINELA, chave="1.1.1.1")
            self.auth.criar_sessao(con, user_id=1)
            # Só a que acabou de nascer.
            self.assertEqual(self._quantas(con, "sessions"), 1)
        finally:
            con.close()

    def test_uma_sessao_VIVA_nao_se_varre(self):
        """A prova pela negativa — uma limpeza que apague tudo não vale nada."""
        con = self.auth.abrir()
        try:
            viva = self.auth.criar_sessao(con, user_id=1)
            self._velha(con, 2, marca="a")
            self.auth.criar_sessao(con, user_id=3)
            self.assertIsNotNone(self.auth.sessao(con, viva["sid"]),
                                 "a sessão viva não pode ir no varrimento")
            self.assertEqual(self._quantas(con, "sessions"), 2)
        finally:
            con.close()

    def test_varre_as_QUATRO_tabelas_que_crescem(self):
        con = self.auth.abrir()
        try:
            self._velha(con)
            con.execute(
                "INSERT INTO auth_pedidos (state, provedor, verifier, criado_em) "
                "VALUES ('velho', 'google', 'v', ?)",
                ((datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),))
            con.execute(
                "INSERT INTO auth_convites (token_hash, user_id, criado_em, "
                "usado_em) VALUES ('gasto', 1, ?, ?)",
                (self.auth._agora(), self.auth._agora()))
            con.execute(
                "INSERT INTO auth_tentativas (ts, chave, provedor, ok) "
                "VALUES (?, '1.1.1.1', 'senha', 0)",
                ((datetime.now(timezone.utc) - timedelta(days=30)).isoformat(),))
            con.commit()

            saiu = self.auth.limpar(con)
            self.assertEqual(saiu, {"sessoes": 1, "pedidos": 1,
                                    "convites": 1, "tentativas": 1})
            for t in ("sessions", "auth_pedidos", "auth_convites",
                      "auth_tentativas"):
                self.assertEqual(self._quantas(con, t), 0, t)
        finally:
            con.close()

    def test_as_tentativas_da_ultima_hora_FICAM(self):
        """Apagá-las desligava o travão, que é o que lhes dá uso."""
        con = self.auth.abrir()
        try:
            self.auth.registar_tentativa(con, "1.1.1.1", "senha", False, 1)
            self.auth.limpar(con)
            self.assertEqual(self._quantas(con, "auth_tentativas"), 1)
            self.assertEqual(self.auth.TENTATIVAS_DIAS, 7)
        finally:
            con.close()

    def test_um_convite_por_usar_e_dentro_do_prazo_FICA(self):
        con = self.auth.abrir()
        try:
            token = self.auth.criar_convite(con, 1)
            self.auth.limpar(con)
            self.assertEqual(self.auth.usar_convite(con, token), 1)
        finally:
            con.close()

    def test_a_limpeza_e_chamada_de_um_sitio_a_SERIO(self):
        """O defeito era este: as funções existiam e ninguém as chamava."""
        fonte = (REPO / "riftvault" / "auth.py").read_text(encoding="utf-8")
        for funcao in ("def criar_sessao(", "def comecar("):
            corpo = fonte.split(funcao)[1].split("\ndef ")[0]
            self.assertIn("limpar(con)", corpo, f"{funcao} não varre nada")

    def test_varrer_nao_mexe_em_quem_esta_dentro(self):
        """Entrar não pode deitar fora a sessão de mais ninguém."""
        c = self.cliente(aberto=True)
        self.com_senha("miguel", SENTINELA)
        self.com_senha("rafa", OUTRA)
        csrf = self.entrar(c, "miguel", SENTINELA)
        self.assertTrue(csrf)
        outro = self.cliente(aberto=True).post(
            "/api/conta/entrar", json={"nome": "rafa", "senha": OUTRA})
        self.assertEqual(outro.status_code, 200)
        d = c.get("/api/conta.json").get_json()
        self.assertTrue(d["entrado"], "a sessão do Miguel sobreviveu")
        self.assertEqual(d["utilizador"]["slug"], "miguel")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()

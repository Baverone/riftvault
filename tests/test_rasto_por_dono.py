"""O RASTO E OS BACKUPS SÃO DE QUEM OS FEZ (2026-10-02).

Achado 2 do `docs/varrimento-2026-10-01.md`: os três CSV de rasto
(`locais.log`, `encomendas.log`, `decks.log`) e os backups iam para
`config.DATA_DIR`, ou seja para a pasta do André, **fosse quem fosse que
estivesse a mexer**, e as linhas não levavam coluna que dissesse de quem eram.

Não era fuga pública (os quatro caminhos estão no `.gitignore`). O estrago era
outro, e é este que os testes fixam:

  1. **o rasto deixava de servir para o que foi feito.** O `locais._log`
     promete *«se uma cópia aparecer num deck sem linha aqui, é bug»* — com
     quatro pessoas a escrever no mesmo ficheiro sem coluna de dono, essa
     verificação não se pode fazer;
  2. a coleção inteira de um amigo num `.zip` solto entre os backups do dono
     da máquina;
  3. apagar a conta de um amigo não tirava os ficheiros dele de lá.

A cura é a gémea do `config.decks_dir(con)` (2026-09-29): `config.log_path` e
`config.backups_dir`. **E os backups ficam em `data/backups/<slug>/` e NÃO em
`data/users/<slug>/backups/`** — a pasta de um utilizador é apagada inteira
pelo `utilizador.apagar`, e com os backups lá dentro o `conta.apagar` apagava
a cópia de segurança que ele próprio acabou de fazer. Há teste para isso, que
é o mais importante deste ficheiro.

Correm contra pastas temporárias. NUNCA contra o `data/` real.
"""

from __future__ import annotations

import csv
import os
import sqlite3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.fixture import (Vault, catalogo_simples,  # noqa: E402
                           config_decks_sem_alt_art)

DECK = """Nome: Azir
Legend:
1 Emperor of the Sands
Champion:
1 Brutalizer
MainDeck:
3 Defy
"""


class Base(unittest.TestCase):
    def setUp(self):
        os.environ.pop("RIFTVAULT_USER", None)
        # O config temporário é obrigatório: o `decks.apagar_todos` escreve no
        # `riftvault_config.json`, e sem isto escrevia no REAL.
        config_decks_sem_alt_art(self)
        self.v = Vault()
        self.addCleanup(self.v.close)
        self.addCleanup(lambda: os.environ.pop("RIFTVAULT_USER", None))
        catalogo_simples(self.v)
        from riftvault import config, db, locais, pending, utilizador
        self.config, self.db, self.locais = config, db, locais
        self.pending, self.u = pending, utilizador

    # -- utilitários ------------------------------------------------------

    def amigo(self, nome="Zé Teste", slug="zeteste") -> dict:
        """Um segundo utilizador, com a coleção dele (o catálogo é partilhado)."""
        from riftvault import collection
        reg = self.u.criar(nome, slug)
        con = self.db.connect(user_id=reg["user_id"])
        try:
            collection.adjust(con, "tst-001-100", 3, source="test")
        finally:
            con.close()
        return reg

    def pasta_do(self, slug: str) -> Path:
        return self.u.pasta(slug)

    def mexer_nos_locais(self, user_id: int, fonte: str):
        con = self.db.connect(user_id=user_id)
        try:
            self.locais.mover(con, "tst-001-100", 1, self.locais.COLECAO,
                              self.locais.BINDER, source=fonte)
        finally:
            con.close()


# ---------------------------------------------------------------------------
# 1. OS TRÊS LOGS
# ---------------------------------------------------------------------------

class TestOsTresLogs(Base):

    def test_o_locais_log_de_um_amigo_cai_na_pasta_DELE(self):
        reg = self.amigo()
        self.mexer_nos_locais(reg["user_id"], "varrimento-amigo")
        dele = self.pasta_do(reg["slug"]) / self.locais.LOG_NAME
        self.assertTrue(dele.exists(), f"sem rasto em {dele}")
        linhas = list(csv.DictReader(dele.read_text(encoding="utf-8-sig")
                                     .splitlines()))
        self.assertEqual(len(linhas), 1)
        self.assertEqual(linhas[0]["printing_id"], "tst-001-100")

    def test_e_NAO_na_pasta_do_andre(self):
        """A prova pela negativa da de cima: é esta que estava vermelha."""
        reg = self.amigo()
        self.mexer_nos_locais(reg["user_id"], "varrimento-amigo")
        self.assertFalse((self.v.data / self.locais.LOG_NAME).exists(),
                         "o rasto do amigo foi para a pasta do André")

    def test_o_do_andre_continua_a_cair_na_dele(self):
        """O comportamento de sempre: `data/locais.log`, o mesmo caminho."""
        self.mexer_nos_locais(self.u.ANDRE, "test")
        self.assertTrue((self.v.data / self.locais.LOG_NAME).exists())

    def test_os_dois_logs_nao_se_tocam(self):
        """O que cada um fez está no ficheiro dele, e só lá."""
        reg = self.amigo()
        self.mexer_nos_locais(self.u.ANDRE, "do-andre")
        self.mexer_nos_locais(reg["user_id"], "do-amigo")
        do_andre = (self.v.data / self.locais.LOG_NAME).read_text(encoding="utf-8")
        do_amigo = (self.pasta_do(reg["slug"]) / self.locais.LOG_NAME
                    ).read_text(encoding="utf-8")
        self.assertIn("do-andre", do_andre)
        self.assertNotIn("do-amigo", do_andre)
        self.assertIn("do-amigo", do_amigo)
        self.assertNotIn("do-andre", do_amigo)

    def test_o_encomendas_log_de_um_amigo_cai_na_pasta_DELE(self):
        reg = self.amigo()
        con = self.db.connect(user_id=reg["user_id"])
        try:
            self.pending.encomendar(con, printing_id="tst-002-100", qty=1,
                                    source="amigo")
        finally:
            con.close()
        dele = self.pasta_do(reg["slug"]) / self.pending.LOG_NAME
        self.assertTrue(dele.exists(), f"sem rasto em {dele}")
        self.assertIn("amigo", dele.read_text(encoding="utf-8"))
        self.assertFalse((self.v.data / self.pending.LOG_NAME).exists())

    def test_o_decks_log_de_um_amigo_cai_na_pasta_DELE(self):
        """As listas são de dono desde 2026-09-29; o registo delas também é."""
        from riftvault import decks, uso_decks
        reg = self.amigo()
        con = self.db.connect(user_id=reg["user_id"])
        try:
            (self.config.decks_dir(con) / "azir.txt").write_text(
                DECK, encoding="utf-8")
            decks.import_all(con, log=lambda *_: None)
            self.assertTrue(uso_decks.registar(con) is not None)
        finally:
            con.close()
        dele = self.pasta_do(reg["slug"]) / uso_decks.LOG_NAME
        self.assertTrue(dele.exists(), f"sem rasto em {dele}")
        self.assertFalse((self.v.data / uso_decks.LOG_NAME).exists())

    def test_a_CLI_diz_o_caminho_que_escreveu__nao_um_a_mao(self):
        """O `riftvault local --marcar` dizia «Rasto em data/locais.log» com o
        caminho escrito à mão — mandava um amigo procurar o ficheiro na pasta do
        André."""
        fonte = (Path(__file__).resolve().parent.parent
                 / "riftvault" / "cli.py").read_text(encoding="utf-8")
        self.assertIn("config.log_path(con, locais_mod.LOG_NAME)", fonte)
        self.assertNotIn('f"data/{locais_mod.LOG_NAME}."', fonte)

    def test_o_dono_e_o_CAMINHO__nao_uma_coluna(self):
        """A decisão: um log por pessoa. O cabeçalho é o de sempre, sem coluna
        de dono — ela seria um filtro que alguém se esquece de pôr, e a
        separação por ficheiro é a mesma que as coleções já têm."""
        self.mexer_nos_locais(self.u.ANDRE, "test")
        cab = next(csv.reader((self.v.data / self.locais.LOG_NAME)
                              .read_text(encoding="utf-8-sig").splitlines()))
        self.assertEqual(cab, ["quando", "printing_id", "codigo", "nome",
                               "quantidade", "de", "para", "origem"])


# ---------------------------------------------------------------------------
# 2. NÃO SE MEXE NO QUE JÁ LÁ ESTÁ
# ---------------------------------------------------------------------------

class TestOQueJaLaEstaFicaOndeEsta(Base):

    def test_um_log_com_linhas_antigas_continua_a_crescer_no_mesmo_ficheiro(self):
        """Os logs que já existem são do André (medido a 2026-10-02: as pastas
        dos três amigos têm só o `vault.db`). Não se dividem, não se reescrevem
        e não se movem — continuam a ser o dele."""
        velho = self.v.data / self.locais.LOG_NAME
        velho.write_text("﻿quando,printing_id,codigo,nome,quantidade,de,para,origem\n"
                         "2026-09-01T00:00:00+00:00,x,X,Y,1,a,b,antigo\n",
                         encoding="utf-8")
        self.mexer_nos_locais(self.u.ANDRE, "novo")
        texto = velho.read_text(encoding="utf-8-sig")
        self.assertIn("antigo", texto, "a linha antiga não se perdeu")
        self.assertIn("novo", texto, "a nova foi para o mesmo ficheiro")
        self.assertEqual(texto.count("quando,printing_id"), 1,
                         "não escreveu um segundo cabeçalho")

    def test_um_amigo_a_mexer_nao_reescreve_o_log_do_andre(self):
        velho = self.v.data / self.locais.LOG_NAME
        self.mexer_nos_locais(self.u.ANDRE, "do-andre")
        antes = velho.read_bytes()
        reg = self.amigo()
        self.mexer_nos_locais(reg["user_id"], "do-amigo")
        self.assertEqual(velho.read_bytes(), antes,
                         "o log do André ficou byte a byte igual")


# ---------------------------------------------------------------------------
# 3. UMA LIGAÇÃO SEM DONO NÃO É «O ANDRÉ»
# ---------------------------------------------------------------------------

class TestSemDono(Base):

    def test_o_log_de_uma_ligacao_sem_dono_rebenta(self):
        from riftvault import guarda
        con = self.db.connect()
        con.riftvault_user = None
        with self.assertRaises(guarda.SemDono):
            self.config.log_path(con, "locais.log")
        con.close()

    def test_o_backup_de_uma_ligacao_sem_dono_rebenta(self):
        from riftvault import guarda
        con = self.db.connect()
        con.riftvault_user = None
        with self.assertRaises(guarda.SemDono):
            self.config.backups_dir(con)
        con.close()

    def test_sem_ligacao_nenhuma_e_o_andre__que_e_a_CLI(self):
        self.assertEqual(self.config.log_path(None, "locais.log"),
                         self.v.data / "locais.log")
        self.assertEqual(self.config.backups_dir(None), self.v.data / "backups")

    def test_a_regra_e_a_MESMA_do_decks_dir(self):
        """Uma pergunta, uma resposta: as quatro famílias passam pelo `_dono`."""
        reg = self.amigo()
        con = self.db.connect(user_id=reg["user_id"])
        try:
            pasta = self.pasta_do(reg["slug"])
            self.assertEqual(self.config.decks_dir(con), pasta / "decks")
            self.assertEqual(self.config.log_path(con, "locais.log"),
                             pasta / "locais.log")
            self.assertEqual(self.config.user_dir(con), pasta)
        finally:
            con.close()


# ---------------------------------------------------------------------------
# 4. OS BACKUPS
# ---------------------------------------------------------------------------

class TestOsBackups(Base):

    def test_o_backup_do_vault_de_um_amigo_vai_para_a_pasta_de_backups_DELE(self):
        reg = self.amigo()
        con = self.db.connect(user_id=reg["user_id"])
        try:
            alvo = self.db.backup(con, "ensaio")
        finally:
            con.close()
        self.assertIsNotNone(alvo, "o backup deu-se")
        self.assertEqual(Path(alvo).parent,
                         self.v.data / "backups" / reg["slug"])
        self.assertFalse((self.v.data / "backups" / Path(alvo).name).exists())

    def test_o_do_andre_continua_na_raiz_dos_backups(self):
        con = self.db.connect()
        try:
            alvo = self.db.backup(con, "ensaio")
        finally:
            con.close()
        self.assertEqual(Path(alvo).parent, self.v.data / "backups")

    def test_o_CATALOGO_e_partilhado__o_backup_dele_nao_e_de_ninguem(self):
        """O catálogo é o jogo e os preços são o mercado: mandar o backup deles
        para a pasta do amigo que abriu a app primeiro era dizer que são
        dele."""
        reg = self.amigo()
        con = self.db.connect(user_id=reg["user_id"])
        try:
            alvo = self.db.backup(con, "ensaio", schema="catalog", nome="catalog")
        finally:
            con.close()
        self.assertEqual(Path(alvo).parent, self.v.data / "backups")

    def test_a_migracao_de_um_amigo_faz_backup_na_pasta_dele(self):
        """O `_migrate` chama o `backup()` — e por isso o dono tem de estar
        posto na ligação ANTES da migração (`db.connect`)."""
        reg = self.amigo()
        caminho = self.db.vault_de(reg["user_id"])
        # Põe a base dele no estado de antes de uma migração que faz backup.
        cru = sqlite3.connect(caminho)
        cru.execute("DROP TABLE IF EXISTS pending")
        cru.execute("CREATE TABLE pending (pending_id INTEGER PRIMARY KEY, "
                    "printing_id TEXT NOT NULL, qty INTEGER NOT NULL, "
                    "ordered_at TEXT NOT NULL, arrived_at TEXT, note TEXT, "
                    "source TEXT)")
        cru.commit()
        cru.close()
        con = self.db.connect(user_id=reg["user_id"])
        con.close()
        dele = list((self.v.data / "backups" / reg["slug"]).glob("*.db"))
        self.assertTrue(dele, "a migração fez backup na pasta dele")
        self.assertEqual(
            list((self.v.data / "backups").glob("vault-antes-do-pendente-foil-*.db")),
            [], "e não na do André")


# ---------------------------------------------------------------------------
# 5. O EXPORT, O RESTAURO E O APAGAR
# ---------------------------------------------------------------------------

class TestExportarEApagar(Base):

    def conta(self):
        from riftvault import conta
        return conta

    def test_o_pacote_de_um_amigo_vai_para_a_pasta_de_backups_DELE(self):
        reg = self.amigo()
        res = self.conta().exportar(reg["slug"])
        self.assertEqual(Path(res["ficheiro"]).parent,
                         self.v.data / "backups" / reg["slug"])

    def test_o_do_andre_continua_na_raiz(self):
        res = self.conta().exportar(self.u.SLUG_ANDRE)
        self.assertEqual(Path(res["ficheiro"]).parent, self.v.data / "backups")

    def test_um_destino_dado_a_mao_manda(self):
        reg = self.amigo()
        fora = Path(self.v.root) / "pendrive"
        res = self.conta().exportar(reg["slug"], destino=fora)
        self.assertEqual(Path(res["ficheiro"]).parent, fora)

    def test_o_copias_de_acha_os_novos_E_os_que_estavam_na_raiz(self):
        """Um pacote escrito antes de hoje não pode deixar de se encontrar só
        porque a regra mudou de sítio — senão o `levar_copias` deixava para
        trás exactamente os ficheiros que já lá estão."""
        conta = self.conta()
        reg = self.amigo()
        novo = Path(conta.exportar(reg["slug"])["ficheiro"])
        antigo = self.v.data / "backups" / f"conta-{reg['slug']}-20260101-000000.zip"
        antigo.write_bytes(b"pacote velho")
        achados = {p.name for p in conta.copias_de(reg["slug"])}
        self.assertIn(novo.name, achados)
        self.assertIn(antigo.name, achados)

    def test_o_copias_de_nao_apanha_o_de_outra_pessoa(self):
        conta = self.conta()
        reg = self.amigo()
        self.amigo("Zé Teste 2", "zeteste-2")
        conta.exportar(reg["slug"])
        conta.exportar("zeteste-2")
        for p in conta.copias_de(reg["slug"]):
            self.assertIn(f"conta-{reg['slug']}-", p.name)

    def test_APAGAR_A_CONTA_NAO_LEVA_OS_PACOTES_DELA(self):
        """É o teste que decide onde vivem os backups.

        Se fossem em `data/users/<slug>/backups/`, o `utilizador.apagar` —
        que apaga a pasta inteira — levava-os, **incluindo o export que o
        `conta.apagar` acabou de fazer**. A rede de segurança desaparecia no
        minuto em que é precisa, e a decisão de 2026-10-01 («os pacotes dela
        FICAM, e dizem-se») ficava revogada em silêncio.
        """
        conta = self.conta()
        reg = self.amigo()
        antes = Path(conta.exportar(reg["slug"])["ficheiro"])
        res = conta.apagar(reg["slug"], confirmar=True)
        self.assertFalse(self.pasta_do(reg["slug"]).exists(), "a conta saiu")
        self.assertTrue(antes.exists(), "o pacote de antes ficou")
        self.assertTrue(Path(res["backup"]).exists(),
                        "e o export final, que é a última rede, também")
        self.assertIn(str(antes), res["copias"])
        self.assertIn(str(res["backup"]), res["copias"])

    def test_levar_copias_leva_os_da_pasta_dela(self):
        conta = self.conta()
        reg = self.amigo()
        # Um pacote de ontem, escrito à mão: dois `exportar` no MESMO SEGUNDO
        # dão o mesmo nome e o segundo escreve por cima (é de sempre, está
        # anotado no CLAUDE.md), e aí não havia histórico nenhum para levar.
        antes = (self.v.data / "backups" / reg["slug"]
                 / f"conta-{reg['slug']}-20260101-000000.zip")
        antes.parent.mkdir(parents=True, exist_ok=True)
        antes.write_bytes(b"pacote de ontem")
        res = conta.apagar(reg["slug"], confirmar=True, levar_copias=True)
        self.assertFalse(antes.exists(), "o histórico saiu")
        self.assertTrue(Path(res["backup"]).exists(),
                        "a cópia final fica — é a ordem: exportar e só depois limpar")

    def test_a_confirmacao_diz_a_pasta_QUE_EXISTE(self):
        conta = self.conta()
        reg = self.amigo()
        p = Path(conta.exportar(reg["slug"])["ficheiro"])
        with self.assertRaises(conta.PrecisaConfirmar) as e:
            conta.apagar(reg["slug"])
        self.assertIn(str(p.parent), str(e.exception))

    def test_o_antes_de_importar_vai_para_a_pasta_dela(self):
        conta = self.conta()
        reg = self.amigo()
        pacote = conta.exportar(reg["slug"])["ficheiro"]
        res = conta.importar(pacote, confirmar=True)
        self.assertEqual(Path(res["backup"]).parent,
                         self.v.data / "backups" / reg["slug"])


# ---------------------------------------------------------------------------
# 6. O ARQUIVO DAS LISTAS DE DECK
# ---------------------------------------------------------------------------

class TestArquivoDosDecks(Base):

    def test_o_arquivo_das_listas_de_um_amigo_vai_para_a_pasta_dele(self):
        from riftvault import decks
        reg = self.amigo()
        con = self.db.connect(user_id=reg["user_id"])
        try:
            (self.config.decks_dir(con) / "azir.txt").write_text(
                DECK, encoding="utf-8")
            decks.import_all(con, log=lambda *_: None)
            res = decks.apagar_todos(con, log=lambda *_: None)
        finally:
            con.close()
        self.assertEqual(Path(res["arquivo"]).parent,
                         self.v.data / "backups" / reg["slug"])
        self.assertEqual(res["apagados"], ["azir.txt"])


# ---------------------------------------------------------------------------
# 7. O .GITIGNORE CONTINUA A TAPAR TUDO
# ---------------------------------------------------------------------------

class TestNadaVaiParaOGit(unittest.TestCase):

    def test_as_duas_pastas_novas_estao_ignoradas(self):
        """Isto é um repositório PÚBLICO. As pastas novas (`data/users/<slug>/`
        e `data/backups/<slug>/`) caem debaixo de regras que já lá estavam, e
        esta é a verificação de que não é por sorte."""
        linhas = [l.strip() for l in (Path(__file__).resolve().parent.parent
                                      / ".gitignore").read_text(
                                          encoding="utf-8").splitlines()]
        self.assertIn("data/users/", linhas,
                      "os logs de um amigo vivem debaixo desta")
        self.assertIn("data/backups/", linhas,
                      "os pacotes de todos vivem debaixo desta")


if __name__ == "__main__":
    unittest.main(verbosity=2)

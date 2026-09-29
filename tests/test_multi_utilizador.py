"""A FUNDAÇÃO DO MULTI-UTILIZADOR (2026-09-29).

André, 2026-09-29: *"Amigos meus querem usar o site para organizar a coleccao
deles. Podes fazer com que mais pessoas possam organizar a coleccao deles
tambem usando o site?"*

O que estes testes fixam, e porquê cada um:

  1. DOIS UTILIZADORES NÃO SE VEEM. É a promessa toda. Testa-se pela app
     inteira (métricas, valor, wantlist, faltas, foil), não por um `SELECT`:
     um `WHERE` esquecido numa camada não aparecia num teste de SQL.
  2. APAGAR UM NÃO TOCA NO OUTRO.
  3. O CATÁLOGO E OS PREÇOS SÃO PARTILHADOS — é isso que torna isto barato.
  4. A MIGRAÇÃO DE UMA BASE DE UM DONO NÃO PERDE NEM INVENTA UMA LINHA.
  5. O REGISTO NÃO ESTÁ NO LADO PÚBLICO: a base do André, que vai para um
     repositório público, não pode conhecer os amigos dele.

Correm contra pastas temporárias. NUNCA contra o `data/` real.
"""

from __future__ import annotations

import hashlib
import importlib
import os
import sqlite3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.fixture import Vault, catalogo_simples  # noqa: E402


def sha_copies(caminho: Path) -> str:
    """O CONTEÚDO da `copies`, sem a coluna nova — é esta a prova de que os
    números dele não mexeram."""
    con = sqlite3.connect(caminho)
    linhas = con.execute("SELECT printing_id, qty, qty_foil, updated_at "
                         "FROM copies ORDER BY printing_id").fetchall()
    con.close()
    return hashlib.sha256(
        "\n".join(f"{a}|{b}|{c}|{d}" for a, b, c, d in linhas).encode()).hexdigest()


class Base(unittest.TestCase):
    def setUp(self):
        os.environ.pop("RIFTVAULT_USER", None)
        self.v = Vault()
        self.addCleanup(self.v.close)
        self.addCleanup(lambda: os.environ.pop("RIFTVAULT_USER", None))
        catalogo_simples(self.v)
        from riftvault import db, utilizador
        self.db, self.u = db, utilizador

    def como(self, user_id: int):
        """Corre o resto do teste como aquele utilizador — é o que a sessão
        autenticada vai fazer quando existir."""
        os.environ["RIFTVAULT_USER"] = str(user_id)

    def numeros(self, user_id: int) -> dict:
        """Os números que a app mostra a um utilizador, pela app inteira."""
        from riftvault import a_subir, faltas_foil, foil, metrics, prices
        con = self.db.connect(user_id=user_id)
        try:
            idx = metrics.index_payload(con)
            val = prices.collection_value(con)
            wl = a_subir.wantlist(con)
            fe = faltas_foil.payload_completo(con)
            return {
                "copies": con.execute("SELECT COUNT(*) FROM copies").fetchone()[0],
                "copias": val["copias"],
                "cents": val["cents"],
                "niveis": [n["done"] for n in idx["levels"]["levels"]],
                "wantlist": [wl["lines"], wl["copies"], wl["cents"]],
                "faltas": fe["totals"]["copies"],
                "foil": foil.contar([i[1:] for i in foil.itens(con)])["foil"],
            }
        finally:
            con.close()


# ---------------------------------------------------------------------------
# 1. Dois utilizadores não se veem
# ---------------------------------------------------------------------------

class TestDoisNaoSeVeem(Base):

    def test_o_andre_e_o_utilizador_1_com_o_slug_que_ja_usa(self):
        self.db.connect().close()
        reg = self.u.registo(1)
        self.assertEqual(reg["user_id"], self.u.ANDRE)
        self.assertEqual(reg["slug"], "baverone")

    def test_a_coleccao_de_um_nao_aparece_na_do_outro(self):
        """A prova principal, e é pela APP INTEIRA."""
        antes = self.numeros(1)
        self.assertGreater(antes["copias"], 0, "o André tem cartas")

        self.u.criar("Miguel", "miguel")
        mig = self.u.por_slug("miguel")["user_id"]

        from riftvault import collection
        con = self.db.connect(user_id=mig)
        collection.adjust(con, "tst-001-100", 2, source="test")
        con.close()

        # O Miguel vê SÓ o dele.
        dele = self.numeros(mig)
        self.assertEqual(dele["copies"], 1)
        self.assertEqual(dele["copias"], 2)

        # E o André não mexeu em NADA.
        self.assertEqual(self.numeros(1), antes)

    def test_sao_ficheiros_diferentes_e_o_do_andre_e_o_de_sempre(self):
        self.u.criar("Miguel", "miguel")
        mig = self.u.por_slug("miguel")["user_id"]
        a, b = self.db.vault_de(1), self.db.vault_de(mig)
        self.assertNotEqual(a, b)
        self.assertEqual(a, self.v.config.VAULT_DB,
                         "o André fica no ficheiro de sempre — a migração não o move")
        self.assertEqual(b, self.v.data / "users" / "miguel" / "vault.db")

    def test_a_base_de_um_utilizador_novo_nasce_feita(self):
        """Um ficheiro que ainda não existe ganha o schema e as migrações
        todas — é disto que o registo de conta vai depender."""
        self.u.criar("Miguel", "miguel")
        mig = self.u.por_slug("miguel")["user_id"]
        self.assertFalse(self.db.vault_de(mig).exists())
        con = self.db.connect(user_id=mig)
        try:
            tabelas = {r[0] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            for t in self.db.TABELAS_DE_DONO:
                self.assertIn(t, tabelas, f"a base nova tem a `{t}`")
                self.assertIn("user_id", {r[1] for r in
                                          con.execute(f"PRAGMA table_info({t})")})
        finally:
            con.close()
        self.assertTrue(self.db.vault_de(mig).exists())

    def test_a_ligacao_sabe_de_quem_e(self):
        self.u.criar("Miguel", "miguel")
        mig = self.u.por_slug("miguel")["user_id"]
        for uid in (1, mig):
            con = self.db.connect(user_id=uid)
            self.assertEqual(con.riftvault_user, uid)
            con.close()

    def test_sem_dizer_nada_e_o_utilizador_da_sessao(self):
        """A porta única: quem não diz nada fica com o `utilizador.atual()`."""
        self.u.criar("Miguel", "miguel")
        mig = self.u.por_slug("miguel")["user_id"]
        con = self.db.connect()
        self.assertEqual(con.riftvault_user, 1)
        con.close()
        self.como(mig)
        con = self.db.connect()
        self.assertEqual(con.riftvault_user, mig)
        con.close()

    def test_as_linhas_de_cada_um_dizem_de_quem_sao(self):
        self.u.criar("Miguel", "miguel")
        mig = self.u.por_slug("miguel")["user_id"]
        from riftvault import collection
        con = self.db.connect(user_id=mig)
        collection.adjust(con, "tst-001-100", 2, source="test")
        con.close()
        con = self.db.connect(user_id=mig)
        try:
            donos = {r[0] for r in con.execute(
                "SELECT DISTINCT user_id FROM copies")}
            self.assertEqual(donos, {mig})
        finally:
            con.close()

    def test_as_pastas_de_decks_sao_de_cada_um(self):
        """Sem isto o Miguel importava as listas do André."""
        self.u.criar("Miguel", "miguel")
        mig = self.u.por_slug("miguel")["user_id"]
        self.v.write_deck("ornn", "Nome: Ornn\nLegend: Emperor of the Sands\n")
        ca = self.db.connect()
        cm = self.db.connect(user_id=mig)
        try:
            self.assertEqual(self.v.config.decks_dir(ca), self.v.decks_dir)
            self.assertNotEqual(self.v.config.decks_dir(cm), self.v.decks_dir)
            from riftvault import decks
            decks.import_all(ca, log=lambda *_: None)
            decks.import_all(cm, log=lambda *_: None)
            self.assertEqual(ca.execute("SELECT COUNT(*) FROM decks").fetchone()[0], 1)
            self.assertEqual(cm.execute("SELECT COUNT(*) FROM decks").fetchone()[0], 0,
                             "o Miguel não herda os decks do André")
        finally:
            ca.close()
            cm.close()


# ---------------------------------------------------------------------------
# 2. Apagar um não toca no outro
# ---------------------------------------------------------------------------

class TestApagar(Base):

    def test_apagar_um_utilizador_nao_toca_no_outro(self):
        antes = self.numeros(1)
        sha_antes = sha_copies(self.db.vault_de(1))

        self.u.criar("Miguel", "miguel")
        mig = self.u.por_slug("miguel")["user_id"]
        from riftvault import collection
        con = self.db.connect(user_id=mig)
        collection.adjust(con, "tst-002-100", 3, source="test")
        con.close()
        pasta = self.u.pasta("miguel")
        self.assertTrue(pasta.exists())

        out = self.u.apagar(mig)

        self.assertFalse(pasta.exists(), "a pasta dele foi-se")
        self.assertEqual(out["slug"], "miguel")
        self.assertIsNone(self.u.por_slug("miguel", obrigatorio=False),
                          "saiu do registo")
        # E o André está EXACTAMENTE como estava.
        self.assertEqual(self.numeros(1), antes)
        self.assertEqual(sha_copies(self.db.vault_de(1)), sha_antes)

    def test_o_andre_nao_se_apaga_por_aqui(self):
        """A base dele é a coleção original e está no Git."""
        with self.assertRaises(self.u.SlugInvalido):
            self.u.apagar(1)
        self.assertTrue(self.db.vault_de(1).exists())

    def test_apagar_um_que_nao_existe_rebenta(self):
        with self.assertRaises(self.u.UtilizadorDesconhecido):
            self.u.apagar(99)


# ---------------------------------------------------------------------------
# 3. O catálogo e os preços são partilhados
# ---------------------------------------------------------------------------

class TestOCatalogoEPartilhado(Base):

    def test_os_dois_leem_o_mesmo_ficheiro_de_catalogo_e_de_precos(self):
        self.u.criar("Miguel", "miguel")
        mig = self.u.por_slug("miguel")["user_id"]
        vistos = {}
        for uid in (1, mig):
            con = self.db.connect(user_id=uid)
            try:
                vistos[uid] = {r[1]: r[2] for r in con.execute("PRAGMA database_list")}
            finally:
                con.close()
        self.assertEqual(vistos[1]["catalog"], vistos[mig]["catalog"])
        self.assertEqual(vistos[1]["prices"], vistos[mig]["prices"])
        self.assertNotEqual(vistos[1]["main"], vistos[mig]["main"],
                            "a coleção é que é de cada um")

    def test_o_catalogo_nao_tem_dono(self):
        """Se um dia o `user_id` lhe chegar, é sinal de que se copiou o
        catálogo por pessoa — e isso é 1,4 MB por amigo."""
        con = self.db.connect()
        try:
            for t in ("printings", "cards", "price_latest"):
                cols = {r[1] for r in con.execute(f"PRAGMA catalog.table_info({t})")}
                if cols:
                    self.assertNotIn("user_id", cols, f"catalog.{t} não tem dono")
            cols = {r[1] for r in con.execute("PRAGMA prices.table_info(price_history)")}
            if cols:
                self.assertNotIn("user_id", cols)
        finally:
            con.close()

    def test_o_utilizador_novo_ve_o_catalogo_inteiro(self):
        self.u.criar("Miguel", "miguel")
        mig = self.u.por_slug("miguel")["user_id"]
        ca = self.db.connect()
        cm = self.db.connect(user_id=mig)
        try:
            n = ca.execute("SELECT COUNT(*) FROM catalog.printings").fetchone()[0]
            self.assertGreater(n, 0)
            self.assertEqual(
                cm.execute("SELECT COUNT(*) FROM catalog.printings").fetchone()[0], n)
        finally:
            ca.close()
            cm.close()


# ---------------------------------------------------------------------------
# 4. A migração não perde nem inventa uma linha
# ---------------------------------------------------------------------------

class TestAMigracao(Base):

    def _base_de_um_dono(self) -> tuple[Path, dict, str]:
        """Uma base como as de antes de hoje: sem `user_id` em lado nenhum.

        Os ÍNDICES caem primeiro, e não é detalhe: o SQLite recusa um
        `DROP COLUMN` numa coluna indexada, e a primeira versão deste teste
        engolia esse erro — a base ficava migrada, a migração não corria, e os
        testes passavam sem terem provado nada.
        """
        caminho = self.v.data / "vault.db"
        con = sqlite3.connect(caminho)
        for t in self.db.TABELAS_DE_DONO:
            con.execute(f"DROP INDEX IF EXISTS ix_{t}_user")
            con.execute(f"ALTER TABLE {t} DROP COLUMN user_id")
        con.execute("DROP TABLE IF EXISTS users")
        con.commit()
        # Ficou mesmo uma base de antes de hoje?
        for t in self.db.TABELAS_DE_DONO:
            assert "user_id" not in {r[1] for r in
                                     con.execute(f"PRAGMA table_info({t})")}, t
        contagens = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                     for t in self.db.TABELAS_DE_DONO}
        con.close()
        return caminho, contagens, sha_copies(caminho)

    def test_nao_perde_nem_inventa_uma_linha(self):
        caminho, antes, sha_antes = self._base_de_um_dono()
        self.assertGreater(antes["copies"], 0, "há mesmo linhas para migrar")

        con = self.db.connect()
        try:
            depois = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                      for t in self.db.TABELAS_DE_DONO}
        finally:
            con.close()

        self.assertEqual(depois, antes, "a contagem de linhas é a mesma, tabela a tabela")
        self.assertEqual(sha_copies(caminho), sha_antes,
                         "os NÚMEROS da `copies` não mexeram (a coluna nova não conta)")

    def test_carimba_todas_as_linhas_com_o_dono(self):
        self._base_de_um_dono()
        con = self.db.connect()
        try:
            for t in self.db.TABELAS_DE_DONO:
                n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                do_andre = con.execute(
                    f"SELECT COUNT(*) FROM {t} WHERE user_id = 1").fetchone()[0]
                self.assertEqual(do_andre, n, f"`{t}`: as {n} linhas ficaram do André")
                self.assertEqual(con.execute(
                    f"SELECT COUNT(*) FROM {t} WHERE user_id IS NULL").fetchone()[0], 0)
        finally:
            con.close()

    def test_a_migracao_faz_backup_e_e_idempotente(self):
        self._base_de_um_dono()
        con = self.db.connect()
        con.close()
        backups = sorted((self.v.data / "backups")
                         .glob("vault-antes-do-multi-utilizador-*.db"))
        self.assertEqual(len(backups), 1, "fez backup antes de mexer nas tabelas")
        b = sqlite3.connect(backups[0])
        self.assertNotIn("user_id", {r[1] for r in b.execute("PRAGMA table_info(copies)")},
                         "o backup é de ANTES")
        b.close()
        # A segunda ligação não volta a migrar nem a fazer backup.
        con = self.db.connect()
        con.close()
        self.assertEqual(len(sorted((self.v.data / "backups")
                                    .glob("vault-antes-do-multi-utilizador-*.db"))), 1)

    def test_todas_as_tabelas_de_dono_levaram_a_coluna_e_o_indice(self):
        con = self.db.connect()
        try:
            indices = {r[0] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='index'")}
            for t in self.db.TABELAS_DE_DONO:
                self.assertIn("user_id", {r[1] for r in
                                          con.execute(f"PRAGMA table_info({t})")}, t)
                self.assertIn(f"ix_{t}_user", indices, f"`{t}` tem índice pelo dono")
        finally:
            con.close()

    def test_a_lista_das_tabelas_de_dono_e_a_das_que_existem(self):
        """Uma tabela de dono nova que ninguém ponha na lista fica sem `user_id`
        e sem entrar no apagar de uma conta — e não há como reparar nisso."""
        con = self.db.connect()
        try:
            tabelas = {r[0] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
        finally:
            con.close()
        conhecidas = set(self.db.TABELAS_DE_DONO) | {"users", "sqlite_sequence"}
        self.assertEqual(tabelas - conhecidas, set(),
                         "há uma tabela no vault.db que ninguém classificou: "
                         "ou é de dono (vai para `db.TABELAS_DE_DONO`) ou é do "
                         "serviço (e diz-se aqui porquê)")


# ---------------------------------------------------------------------------
# 5. O registo não está no lado público
# ---------------------------------------------------------------------------

class TestORegistoNaoEPublico(Base):

    def test_a_base_do_andre_nao_conhece_os_amigos(self):
        """O `data/vault.db` é commitado num repositório PÚBLICO, de 30 em 30
        minutos. Se o registo vivesse lá, registar um amigo publicava-lhe o
        nome e o slug para sempre — mesmo com a coleção dele privada."""
        self.u.criar("Miguel", "miguel")
        self.db.connect().close()
        con = sqlite3.connect(self.db.vault_de(1))
        try:
            quem = [r[0] for r in con.execute("SELECT slug FROM users")]
        finally:
            con.close()
        self.assertEqual(quem, ["baverone"],
                         "a base pública do André só se conhece a si própria")
        self.assertEqual({u["slug"] for u in self.u.todos()},
                         {"baverone", "miguel"}, "o registo, esse, tem os dois")

    def test_o_registo_vive_fora_da_pasta_que_vai_para_o_git(self):
        self.assertEqual(self.u.registo_db(),
                         self.v.data / "users" / "registo.db")

    def test_a_pasta_dos_outros_esta_no_gitignore(self):
        raiz = Path(__file__).resolve().parent.parent
        ignore = (raiz / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("data/users/", ignore,
                      "sem isto a coleção dos amigos ia para um repositório público")

    def test_a_base_de_cada_um_diz_de_quem_e(self):
        """Para um ficheiro restaurado se explicar a quem o abre."""
        self.u.criar("Miguel", "miguel")
        mig = self.u.por_slug("miguel")["user_id"]
        self.db.connect(user_id=mig).close()
        con = sqlite3.connect(self.db.vault_de(mig))
        try:
            self.assertEqual([r[0] for r in con.execute("SELECT slug FROM users")],
                             ["miguel"])
        finally:
            con.close()

    def test_o_auth_ref_nasce_vazio_e_ninguem_lhe_escreve(self):
        """Esta corrida é a fundação do modelo, não a autenticação."""
        self.u.criar("Miguel", "miguel")
        self.assertIsNone(self.u.por_slug("miguel")["auth_ref"])
        fonte = (Path(__file__).resolve().parent.parent
                 / "riftvault" / "utilizador.py").read_text(encoding="utf-8")
        self.assertNotIn("UPDATE users SET auth_ref", fonte)


# ---------------------------------------------------------------------------
# 6. O guarda do ficheiro trocado
# ---------------------------------------------------------------------------

class TestOGuarda(Base):

    def test_uma_base_com_linhas_de_outro_dono_rebenta(self):
        """Não acontece por bug: acontece quando alguém restaura um backup por
        cima de outro. Rebenta em vez de servir a coleção errada a alguém.

        A FK é desligada para escrever o intruso porque é isso que um ficheiro
        trocado é: a linha foi escrita NOUTRA base, onde o utilizador 77 existe,
        e chegou aqui por cópia — nunca passou por uma FK desta.
        """
        con = self.db.connect()
        con.execute("PRAGMA foreign_keys=OFF")
        con.execute("UPDATE copies SET user_id = 77")
        con.close()
        with self.assertRaises(self.u.DonoErrado) as e:
            self.db.connect()
        self.assertIn("copies", str(e.exception))
        self.assertIn("77", str(e.exception))

    def test_numa_base_NOVA_a_fk_ja_recusa_um_dono_inventado(self):
        """A base criada de raiz leva `REFERENCES users(user_id)` do schema, e
        o SQLite recusa lá escrever um dono que não exista.

        NUMA BASE MIGRADA NÃO HÁ FK, e é preciso saber: o SQLite não sabe
        acrescentar uma chave estrangeira num `ALTER TABLE ADD COLUMN`, e
        refazer dezasseis tabelas da coleção dele para a ganhar não se pagava.
        É por isso que o guarda do `utilizador.guardar` existe — ele vale nos
        dois casos, e é ele que apanha o ficheiro trocado.
        """
        self.u.criar("Miguel", "miguel")
        mig = self.u.por_slug("miguel")["user_id"]
        con = self.db.connect(user_id=mig)
        try:
            from riftvault import collection
            collection.adjust(con, "tst-001-100", 1, source="test")
            with self.assertRaises(sqlite3.IntegrityError):
                con.execute("UPDATE copies SET user_id = 77")
        finally:
            con.close()

    def test_um_ficheiro_FRESCO_de_outro_dono_tambem_rebenta(self):
        """O carimbo é preguiçoso: corre no `connect`, antes das escritas da
        sessão. Uma base criada e nunca mais reaberta tem as linhas TODAS a
        NULL — e nesse estado as linhas sozinhas não distinguem ninguém.

        Quem responde é a `users` de DENTRO da base, que é a identidade do
        ficheiro. Apanhado pela sessão `riftbound-2b` a 2026-09-29, com um
        teste que forjava um manifesto e via a recusa não acontecer.
        """
        self.u.criar("Miguel", "miguel")
        mig = self.u.por_slug("miguel")["user_id"]
        from riftvault import collection
        con = self.db.connect(user_id=mig)
        collection.adjust(con, "tst-001-100", 2, source="test")
        con.close()

        # Na primeira sessão as linhas ficaram mesmo a NULL — é o caso que
        # este teste existe para cobrir.
        cru = sqlite3.connect(self.db.vault_de(mig))
        porcarimbar = cru.execute(
            "SELECT COUNT(*) FROM copies WHERE user_id IS NULL").fetchone()[0]
        cru.close()
        self.assertGreater(porcarimbar, 0, "as linhas da sessão ficam por carimbar")

        # Alguém copia a base do Miguel para o sítio do André.
        import shutil
        shutil.copy2(self.db.vault_de(mig), self.db.vault_de(1))
        with self.assertRaises(self.u.DonoErrado) as e:
            self.db.connect()
        self.assertIn("miguel" if "miguel" in str(e.exception)
                      else str(mig), str(e.exception))

    def test_uma_linha_sem_dono_e_adoptada_e_nao_rebenta(self):
        """NULL quer dizer «do dono deste ficheiro» — é um ficheiro por pessoa."""
        con = self.db.connect()
        con.execute("UPDATE copies SET user_id = NULL")
        con.close()
        con = self.db.connect()
        try:
            self.assertEqual(con.execute(
                "SELECT COUNT(*) FROM copies WHERE user_id IS NULL").fetchone()[0], 0)
            self.assertGreater(con.execute(
                "SELECT COUNT(*) FROM copies WHERE user_id = 1").fetchone()[0], 0)
        finally:
            con.close()


# ---------------------------------------------------------------------------
# 7. O slug — é o subdomínio E o nome da pasta
# ---------------------------------------------------------------------------

class TestOSlug(Base):

    def test_aceita_o_que_serve_de_subdominio(self):
        for bom in ("miguel", "joao-silva", "ze2", "ab"):
            self.assertEqual(self.u.validar_slug(bom.upper()), bom)

    def test_recusa_o_que_nao_serve(self):
        maus = ["", "a", "-x", "x-", "Mi guel", "miguel!", "joão",
                "..", "../etc", "a/b", "C:", "x" * 33]
        for mau in maus:
            with self.assertRaises(self.u.SlugInvalido, msg=mau):
                self.u.validar_slug(mau)

    def test_um_slug_nao_foge_da_pasta(self):
        """É o mesmo texto que vai para o caminho em disco."""
        for mau in ("../..", "..", "a/b"):
            with self.assertRaises(self.u.SlugInvalido):
                self.u.pasta(mau)

    def test_recusa_os_reservados(self):
        for mau in ("www", "api", "admin", "users", "riftvault"):
            with self.assertRaises(self.u.SlugInvalido):
                self.u.validar_slug(mau)

    def test_nao_ha_dois_com_o_mesmo_slug(self):
        self.u.criar("Miguel", "miguel")
        with self.assertRaises(self.u.SlugInvalido):
            self.u.criar("Outro Miguel", "miguel")

    def test_o_slug_e_o_nome_da_pasta(self):
        self.u.criar("Miguel", "miguel")
        self.assertEqual(self.u.pasta("miguel"), self.v.data / "users" / "miguel")
        self.assertEqual(self.u.pasta("baverone"), self.v.data,
                         "o André fica na pasta de sempre")


# ---------------------------------------------------------------------------
# 8. A porta única
# ---------------------------------------------------------------------------

class TestAPortaUnica(Base):

    def test_hoje_e_sempre_o_andre(self):
        self.assertEqual(self.u.atual(), self.u.ANDRE)

    def test_todo_o_codigo_que_le_dados_de_dono_vai_pelo_connect(self):
        """A porta é uma só: nenhum módulo abre o `vault.db` por fora.

        Se um dia abrir, a sessão autenticada deixa de mandar nele e a fatia
        seguinte passa a ter de se lembrar de dois sítios.
        """
        pkg = Path(__file__).resolve().parent.parent / "riftvault"
        maus = []
        for py in sorted(pkg.glob("*.py")):
            if py.name in ("db.py", "utilizador.py"):
                continue          # é aqui que a porta vive
            texto = py.read_text(encoding="utf-8")
            if "sqlite3.connect(" in texto:
                maus.append(py.name)
        self.assertEqual(maus, [],
                         "estes módulos abrem uma base por fora do `db.connect`")

    def test_o_utilizador_da_sessao_le_se_num_sitio_so(self):
        pkg = Path(__file__).resolve().parent.parent / "riftvault"
        maus = [py.name for py in sorted(pkg.glob("*.py"))
                if py.name != "utilizador.py"
                and "RIFTVAULT_USER" in py.read_text(encoding="utf-8")]
        self.assertEqual(maus, [], "quem quer saber o utilizador chama `atual()`")

    def test_o_como_vale_so_no_fio_dele(self):
        """O `serve` corre `threaded=True`: um pedido por thread.

        Uma variável global punha dois pedidos simultâneos a ver o dono um do
        outro — que é a pior avaria que este módulo podia ter. Isto foi
        apanhado por uma sessão em paralelo (a `riftbound-f3`) antes de o
        servidor chegar a usar a porta, e é por isso que o `atual()` lê um
        `ContextVar` e não uma global.
        """
        import threading
        self.u.criar("Miguel", "miguel")
        self.u.criar("Ana", "ana")
        mig = self.u.por_slug("miguel")["user_id"]
        ana = self.u.por_slug("ana")["user_id"]

        vistos, arranca = {}, threading.Barrier(2)

        def fio(nome, uid):
            with self.u.como(uid):
                arranca.wait(5)          # os dois ao mesmo tempo, de propósito
                vistos[nome] = self.u.atual()

        fios = [threading.Thread(target=fio, args=("m", mig)),
                threading.Thread(target=fio, args=("a", ana))]
        for f in fios:
            f.start()
        for f in fios:
            f.join(10)

        self.assertEqual(vistos, {"m": mig, "a": ana},
                         "cada fio viu o SEU utilizador")
        self.assertEqual(self.u.atual(), 1, "e o fio principal não mexeu")

    def test_o_como_repoe_o_que_estava_mesmo_se_rebentar(self):
        self.u.criar("Miguel", "miguel")
        mig = self.u.por_slug("miguel")["user_id"]
        with self.assertRaises(ZeroDivisionError):
            with self.u.como(mig):
                self.assertEqual(self.u.atual(), mig)
                1 / 0
        self.assertEqual(self.u.atual(), 1)

    def test_dentro_do_como_o_connect_sem_argumentos_vai_a_base_certa(self):
        """É assim que a sessão autenticada vai entrar: o servidor abre um
        `como()` e o resto do código nem sabe que mudou de dono."""
        self.u.criar("Miguel", "miguel")
        mig = self.u.por_slug("miguel")["user_id"]
        with self.u.como(mig):
            con = self.db.connect()
            try:
                self.assertEqual(con.riftvault_user, mig)
            finally:
                con.close()

    def test_um_utilizador_que_nao_existe_rebenta(self):
        with self.assertRaises(self.u.UtilizadorDesconhecido):
            self.db.connect(user_id=99)

    def test_a_variavel_mal_escrita_rebenta(self):
        os.environ["RIFTVAULT_USER"] = "o-miguel"
        with self.assertRaises(self.u.UtilizadorDesconhecido):
            self.u.atual()


if __name__ == "__main__":
    unittest.main(verbosity=1)

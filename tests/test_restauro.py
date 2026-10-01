"""O RESTAURO: um pacote só entra na conta DELE, e nunca torna nada público
(2026-10-01).

Três defeitos, os três no caminho que só se usa no pior dia — o dia em que
alguém está a restaurar alguma coisa com outra pessoa à espera:

  1. o `conta.importar` validava o pacote contra o `user_id` do MANIFESTO e a
     seguir adoptava o id do slug que já existia no registo, **sem comparar os
     dois**. Dois pacotes com o mesmo slug e ids diferentes — duas instalações,
     ou um ficheiro renomeado — e a coleção de uma pessoa aterrava por cima da
     de outra;
  2. a privacidade vive no REGISTO, e restaurar o registo de um backup trazia
     as escolhas do DIA DO BACKUP: quem tivesse fechado a coleção entretanto
     voltava a público, e o site regenera-se de 30 em 30 minutos;
  3. o `conta.apagar` deixava para trás os pacotes de exportação dessa pessoa,
     sem os nomear.

A forma dos testes é a desta casa: **nada se escreve antes de a recusa
acontecer** (fotografa-se e compara-se), e cada regra nova tem ao lado a prova
pela negativa — sem ela um teste que não vê nada passa sempre.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import unittest
import zipfile
from pathlib import Path

from riftvault import (build, collection, conta, db, multi, privacidade,
                       utilizador)
from tests import fixture


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else "—"


def forjar(pacote: Path, destino: Path, *, uid: int, slug: str) -> Path:
    """Um pacote COERENTE de outra instalação: manifesto e base com outro id.

    Não é um manifesto mexido à mão — é o que sai de uma instalação em que o
    mesmo slug tem outro `user_id` (foi semeado por outra ordem). O pacote tem
    de passar o `_so_deste_dono`, senão o teste estava a provar a guarda que já
    existia em vez da que falta.
    """
    with zipfile.ZipFile(pacote) as z:
        m = json.loads(z.read(conta.NOME_MANIFESTO).decode("utf-8"))
        bruto = {n: z.read(n) for n in z.namelist()}
    tmp = destino.with_suffix(".vault.db")
    tmp.write_bytes(bruto[conta.NOME_VAULT])
    con = sqlite3.connect(tmp, isolation_level=None)
    try:
        con.execute("DELETE FROM users")
        con.execute("INSERT INTO users (user_id, nome, slug, criado_em, publico) "
                    "VALUES (?,?,?,?,?)",
                    (uid, m["utilizador"].get("nome") or slug, slug,
                     m["utilizador"].get("criado_em") or "2026-01-01T00:00:00+00:00",
                     m["utilizador"].get("publico") or "nada"))
        for t in db.TABELAS_DE_DONO:
            try:
                con.execute(f"UPDATE {t} SET user_id = ?", (uid,))  # noqa: S608
            except sqlite3.OperationalError:
                pass
    finally:
        con.close()
    for sufixo in ("-wal", "-shm"):
        velho = tmp.with_name(tmp.name + sufixo)
        if velho.exists():
            velho.unlink()
    bruto[conta.NOME_VAULT] = tmp.read_bytes()
    m["utilizador"]["user_id"] = uid
    m["utilizador"]["slug"] = slug
    m["sha256_vault"] = hashlib.sha256(bruto[conta.NOME_VAULT]).hexdigest()
    bruto[conta.NOME_MANIFESTO] = json.dumps(m, ensure_ascii=False).encode("utf-8")
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        for n, dados in bruto.items():
            z.writestr(n, dados)
    tmp.unlink()
    return destino


class Base(unittest.TestCase):
    """O André (1) e o Miguel, com colecções diferentes."""

    def setUp(self):
        self.v = fixture.Vault()
        self.addCleanup(self.v.close)
        fixture.catalogo_simples(self.v)
        self.miguel = utilizador.criar("Miguel", "miguel")
        self.uid_b = self.miguel["user_id"]
        con = db.connect(user_id=self.uid_b)
        collection.adjust(con, "tst-002-100", 4, source="test")
        con.close()
        self.vault_a = db.vault_de(utilizador.ANDRE)
        self.vault_b = db.vault_de(self.uid_b)
        self.backups = self.v.data / "backups"

    def linhas(self, caminho: Path, uid: int) -> dict:
        con = db.abrir_vault(caminho, uid, readonly=True)
        try:
            fora = {}
            for t in db.TABELAS_DE_DONO:
                try:
                    fora[t] = [tuple(r) for r in con.execute(f"SELECT * FROM {t}")]  # noqa: S608
                except sqlite3.OperationalError:
                    fora[t] = []
            return fora
        finally:
            con.close()

    def foto(self, caminho: Path, uid: int):
        return (sha(caminho), self.linhas(caminho, uid))


# ---------------------------------------------------------------------------
# DEFEITO 1 — o pacote entra na conta errada, em silêncio
# ---------------------------------------------------------------------------

class TestPacoteNaContaErrada(Base):

    def pacote_de_outra_instalacao(self, uid: int = 77) -> Path:
        """Um pacote do slug `miguel` mas do utilizador `uid`."""
        p = conta.exportar("miguel")["ficheiro"]
        return forjar(p, self.v.root / "de-outra-casa.zip", uid=uid, slug="miguel")

    def test_o_pacote_de_outro_id_com_o_mesmo_slug_e_RECUSADO(self):
        p = self.pacote_de_outra_instalacao()
        antes = self.foto(self.vault_b, self.uid_b)
        with self.assertRaises(utilizador.DonoErrado):
            conta.importar(p, confirmar=True)
        self.assertEqual(self.foto(self.vault_b, self.uid_b), antes,
                         "o pacote de outro id chegou a escrever")

    def test_a_recusa_diz_de_quem_e_e_para_quem_ia(self):
        p = self.pacote_de_outra_instalacao(uid=77)
        with self.assertRaises(utilizador.DonoErrado) as e:
            conta.importar(p, confirmar=True)
        texto = str(e.exception)
        self.assertIn("77", texto, "não diz de quem é o pacote")
        self.assertIn(str(self.uid_b), texto, "não diz para quem ia")
        self.assertIn("miguel", texto)

    def test_nao_faz_nem_o_backup_antes_de_recusar(self):
        """A recusa é ANTES de se mexer em disco: não há limpeza a fazer."""
        p = self.pacote_de_outra_instalacao()
        antes = sorted(x.name for x in self.backups.glob("*")) \
            if self.backups.exists() else []
        with self.assertRaises(utilizador.DonoErrado):
            conta.importar(p, confirmar=True)
        depois = sorted(x.name for x in self.backups.glob("*")) \
            if self.backups.exists() else []
        self.assertEqual(depois, antes)

    def test_o_pacote_dele_proprio_entra_sem_adoptar(self):
        """A prova pela negativa: a guarda nova não bloqueia o caso normal."""
        p = conta.exportar("miguel")["ficheiro"]
        con = db.connect(user_id=self.uid_b)
        collection.adjust(con, "tst-002-100", -4, source="test")
        con.close()
        r = conta.importar(p, confirmar=True)
        self.assertEqual(r["linhas"]["copies"], 1)
        self.assertEqual(r["adoptado"], None)

    def test_com_adoptar_entra_E_A_BASE_ABRE(self):
        """A porta explícita: restaurar para uma instalação com outros ids.

        Não basta deixar entrar — o que entra tem de poder ser ABERTO. Sem
        recarimbar, a base ficava a dizer-se de outro dono e o `db.connect`
        rebentava para sempre: um import que «corre bem» e deixa a conta
        inutilizável.
        """
        p = self.pacote_de_outra_instalacao(uid=77)
        r = conta.importar(p, confirmar=True, adoptar=True)
        self.assertEqual(r["adoptado"], {"de": 77, "para": self.uid_b})
        con = db.connect(user_id=self.uid_b)
        try:
            n = con.execute("SELECT qty FROM copies WHERE printing_id = ?",
                            ("tst-002-100",)).fetchone()[0]
            donos = {r[0] for r in con.execute(
                "SELECT DISTINCT user_id FROM copies")}
        finally:
            con.close()
        self.assertEqual(n, 4, "as cartas do pacote não entraram")
        self.assertEqual(donos, {self.uid_b},
                         "as linhas ficaram carimbadas com o id antigo")

    def test_adoptar_nao_mexe_no_outro_utilizador(self):
        p = self.pacote_de_outra_instalacao(uid=77)
        antes = self.foto(self.vault_a, utilizador.ANDRE)
        conta.importar(p, confirmar=True, adoptar=True)
        self.assertEqual(self.foto(self.vault_a, utilizador.ANDRE), antes)

    def test_adoptar_quando_os_ids_batem_nao_tem_nada_para_fazer(self):
        p = conta.exportar("miguel")["ficheiro"]
        r = conta.importar(p, confirmar=True, adoptar=True)
        self.assertIsNone(r["adoptado"])

    def test_sem_confirmar_continua_a_nao_escrever(self):
        p = self.pacote_de_outra_instalacao()
        antes = self.foto(self.vault_b, self.uid_b)
        with self.assertRaises(conta.PrecisaConfirmar):
            conta.importar(p)
        self.assertEqual(self.foto(self.vault_b, self.uid_b), antes)

    def test_recriar_uma_conta_apagada_com_outro_id_nao_precisa_de_adoptar(self):
        """O id do manifesto está livre: a conta volta com o id dela."""
        p = conta.exportar("miguel")["ficheiro"]
        conta.apagar("miguel", confirmar=True, com_backup=False)
        r = conta.importar(p, confirmar=True)
        self.assertEqual(r["utilizador"]["user_id"], self.uid_b)
        self.assertIsNone(r["adoptado"])

    def test_se_o_id_do_manifesto_estiver_TOMADO_a_conta_volta_adoptada(self):
        """O caso que o `IntegrityError` já tratava — e que ficava por abrir.

        A conta foi apagada, o id dela foi dado a outra pessoa, e o pacote
        volta: entra com um id NOVO, e isso é uma adopção. Sem recarimbar, a
        base recriada não abria.
        """
        p = conta.exportar("miguel")["ficheiro"]
        conta.apagar("miguel", confirmar=True, com_backup=False)
        # O id dela fica com outra pessoa. Escreve-se o id à mão porque a
        # `users` é AUTOINCREMENT e um utilizador novo nunca reaproveita um id
        # apagado — o cenário a sério é uma instalação onde os ids foram
        # semeados por outra ordem.
        mestre = utilizador.abrir_registo()
        try:
            mestre.execute(
                "INSERT INTO users (user_id, nome, slug, criado_em, publico) "
                "VALUES (?,?,?,?,'nada')",
                (self.uid_b, "Rafa", "rafa", "2026-01-01T00:00:00+00:00"))
        finally:
            mestre.close()
        self.assertEqual(utilizador.por_slug("rafa")["user_id"], self.uid_b)
        with self.assertRaises(utilizador.DonoErrado):
            conta.importar(p, confirmar=True)
        r = conta.importar(p, confirmar=True, adoptar=True)
        novo = r["utilizador"]["user_id"]
        self.assertNotEqual(novo, self.uid_b)
        self.assertEqual(r["adoptado"], {"de": self.uid_b, "para": novo})
        con = db.connect(user_id=novo)
        try:
            self.assertEqual(con.execute(
                "SELECT qty FROM copies WHERE printing_id = ?",
                ("tst-002-100",)).fetchone()[0], 4)
        finally:
            con.close()


# ---------------------------------------------------------------------------
# DEFEITO 2 — restaurar o registo não pode tornar nada público
# ---------------------------------------------------------------------------

class TestRestaurarORegisto(Base):
    """Ponta a ponta: um registo de mentira por cima de uma cópia.

    O registo é um FICHEIRO (`data/users/registo.db`) e não há código que o
    restaure — restaura-se copiando-o de uma cópia, que é o que isto faz.
    """

    def copia_do_registo(self, nome: str = "registo-backup.db") -> Path:
        alvo = self.v.root / nome
        con = utilizador.abrir_registo()
        try:
            con.execute("VACUUM main INTO ?", (str(alvo),))
        finally:
            con.close()
        return alvo

    def restaurar(self, copia: Path) -> None:
        vivo = utilizador.registo_db()
        for sufixo in ("-wal", "-shm"):
            velho = vivo.with_name(vivo.name + sufixo)
            if velho.exists():
                velho.unlink()
        vivo.write_bytes(copia.read_bytes())

    def cru(self, uid: int) -> str:
        """O que está ESCRITO na coluna, sem a regra. Para provar o cenário."""
        con = utilizador.abrir_registo()
        try:
            return con.execute("SELECT publico FROM users WHERE user_id = ?",
                               (uid,)).fetchone()[0]
        finally:
            con.close()

    def setUp(self):
        super().setUp()
        privacidade.definir(None, self.uid_b, "tudo")
        self.copia = self.copia_do_registo()        # o dia do backup: «tudo»
        privacidade.definir(None, self.uid_b, "nada")   # ele fechou-a hoje

    def test_o_cenario_e_mesmo_o_que_se_diz(self):
        """Antes de medir a cura: o registo restaurado DIZ «tudo»."""
        self.restaurar(self.copia)
        self.assertEqual(self.cru(self.uid_b), "tudo")

    def test_UM_RESTAURO_NAO_TORNA_PUBLICA_UMA_COLECCAO_FECHADA(self):
        self.restaurar(self.copia)
        self.assertEqual(privacidade.de(None, self.uid_b), "nada")

    def test_e_nao_se_gera_pagina_nenhuma(self):
        """De ponta a ponta, com as portas abertas — é o site que conta."""
        self.restaurar(self.copia)
        out = self.v.root / "site-restaurado"
        build.build_todos(out, log=lambda *_: None,
                          cfg={"multi": {"aberto": True}})
        self.assertFalse((out / "u" / "miguel").exists(),
                         "o restauro do registo republicou uma coleção fechada")

    def test_nem_depois_de_a_base_dele_ser_aberta(self):
        """O carimbo por ligação corre a cada `db.connect` e ALARGAVA.

        Era o furo que fazia a cura durar um pedido: o `_carimbar_dono` copiava
        o registo para dentro da base, e com o registo velho isso apagava o
        único sítio onde a escolha de hoje ainda estava escrita.
        """
        self.restaurar(self.copia)
        con = db.connect(user_id=self.uid_b)
        con.close()
        self.assertEqual(privacidade.de(None, self.uid_b), "nada")
        out = self.v.root / "site-depois"
        build.build_todos(out, log=lambda *_: None,
                          cfg={"multi": {"aberto": True}})
        self.assertFalse((out / "u" / "miguel").exists())

    def test_o_desacordo_cura_se_a_seguir(self):
        """Depois de a base ser aberta, o registo fica com a escolha de hoje —
        senão um `vault.db` perdido ressuscitava o `tudo` velho."""
        self.restaurar(self.copia)
        con = db.connect(user_id=self.uid_b)
        con.close()
        self.assertEqual(self.cru(self.uid_b), "nada")

    def test_ABRIR_A_COLECCAO_CONTINUA_A_FUNCIONAR(self):
        """A prova pela negativa: a regra só fecha, não emperra.

        Sem este teste, «nunca alarga» passava com um `de()` que devolvesse
        sempre «nada».
        """
        privacidade.definir(None, self.uid_b, "sem-valores")
        self.assertEqual(privacidade.de(None, self.uid_b), "sem-valores")
        privacidade.definir(None, self.uid_b, "tudo")
        self.assertEqual(privacidade.de(None, self.uid_b), "tudo")
        con = db.connect(user_id=self.uid_b)
        con.close()
        self.assertEqual(privacidade.de(None, self.uid_b), "tudo")
        out = self.v.root / "site-aberto"
        build.build_todos(out, log=lambda *_: None,
                          cfg={"multi": {"aberto": True}})
        self.assertTrue((out / "u" / "miguel" / "api" / "index.json").exists())

    def test_um_restauro_para_MAIS_FECHADO_vale_na_mesma(self):
        """O lado seguro do erro: um registo velho mais fechado fecha."""
        privacidade.definir(None, self.uid_b, "tudo")
        copia = self.copia_do_registo("so-nada.db")
        # a cópia diz «tudo»; forja-se um registo velho a dizer «nada»
        con = sqlite3.connect(copia, isolation_level=None)
        con.execute("UPDATE users SET publico = 'nada' WHERE user_id = ?",
                    (self.uid_b,))
        con.close()
        self.restaurar(copia)
        self.assertEqual(privacidade.de(None, self.uid_b), "nada")

    def test_o_andre_nao_e_afectado(self):
        """Ele está em «tudo» desde sempre e o site dele não muda um byte."""
        self.assertEqual(privacidade.de(None, utilizador.ANDRE), "tudo")
        self.restaurar(self.copia)
        self.assertEqual(privacidade.de(None, utilizador.ANDRE), "tudo")

    def test_uma_conta_sem_base_ainda_criada_le_se_do_registo(self):
        """Quem nunca abriu a coleção não tem segundo testemunho — e nesse
        caso o registo é o único que fala."""
        nova = utilizador.criar("Zé", "zeze")
        self.assertEqual(privacidade.de(None, nova["user_id"]), "nada")
        privacidade.definir(None, nova["user_id"], "tudo")
        self.assertEqual(privacidade.de(None, nova["user_id"]), "tudo")

    def test_o_mais_fechado_e_uma_funcao_e_a_escala_esta_escrita(self):
        self.assertEqual(privacidade.mais_fechado("tudo", "nada"), "nada")
        self.assertEqual(privacidade.mais_fechado("tudo", "sem-valores"),
                         "sem-valores")
        self.assertEqual(privacidade.mais_fechado("tudo", None), "tudo")
        self.assertEqual(privacidade.mais_fechado(None, None),
                         privacidade.OMISSAO)
        self.assertEqual(privacidade.mais_fechado("tudo", "tudo"), "tudo")

    def test_restaurar_O_PACOTE_de_uma_conta_apagada_traz_a_de_volta_FECHADA(self):
        """Um pacote também é um backup: não pode republicar nada.

        A conta foi apagada; o pacote diz «tudo» porque era isso no dia do
        export. Não há consentimento vivo nenhum — volta em «nada» e quem a
        quiser pública torna-a pública outra vez.
        """
        privacidade.definir(None, self.uid_b, "tudo")
        p = conta.exportar("miguel")["ficheiro"]
        self.assertEqual(conta.ler_manifesto(p)["utilizador"]["publico"], "tudo")
        conta.apagar("miguel", confirmar=True, com_backup=False)
        r = conta.importar(p, confirmar=True)
        self.assertEqual(privacidade.de(None, r["utilizador"]["user_id"]),
                         "nada")

    def test_importar_nao_mexe_na_escolha_de_quem_ja_existe(self):
        privacidade.definir(None, self.uid_b, "tudo")
        p = conta.exportar("miguel")["ficheiro"]
        privacidade.definir(None, self.uid_b, "sem-valores")
        conta.importar(p, confirmar=True)
        self.assertEqual(privacidade.de(None, self.uid_b), "sem-valores")


# ---------------------------------------------------------------------------
# DEFEITO 3 — apagar deixava os pacotes dela para trás, calado
# ---------------------------------------------------------------------------

class TestApagarEOsPacotes(Base):

    def tres_pacotes(self) -> list[Path]:
        """Dois pacotes de datas DIFERENTES, com o nome escrito à mão.

        O nome leva o `%Y%m%d-%H%M%S` e dois exports no mesmo segundo dão o
        mesmo ficheiro — o que faz o teste medir um pacote em vez de dois. As
        datas escrevem-se aqui para o cenário ser o que se diz.
        """
        fora = []
        for n, quando in enumerate(("20260101-000001", "20260102-000002")):
            alvo = self.backups / f"conta-miguel-{quando}.zip"
            alvo.parent.mkdir(parents=True, exist_ok=True)
            fora.append(conta.exportar("miguel", destino=alvo)["ficheiro"])
            self.assertEqual(fora[n], alvo)
        return fora

    def test_apagar_DIZ_onde_ficaram_os_pacotes(self):
        antigos = self.tres_pacotes()
        r = conta.apagar("miguel", confirmar=True)
        nomes = {Path(p).name for p in r["copias"]}
        for p in antigos:
            self.assertIn(p.name, nomes, "não disse que este pacote ficou")
        self.assertIn(Path(r["backup"]).name, nomes)
        self.assertTrue(all(Path(p).exists() for p in antigos),
                        "apagou os backups sem lho pedirem")

    def test_a_mensagem_de_confirmacao_conta_os_pacotes(self):
        self.tres_pacotes()
        with self.assertRaises(conta.PrecisaConfirmar) as e:
            conta.apagar("miguel")
        self.assertIn("2", str(e.exception))
        self.assertIn("backups", str(e.exception).lower())

    def test_com_levar_copias_as_antigas_SAEM(self):
        antigos = self.tres_pacotes()
        r = conta.apagar("miguel", confirmar=True, levar_copias=True)
        for p in antigos:
            self.assertFalse(p.exists(), f"{p.name} ficou")
        self.assertTrue(Path(r["backup"]).exists(),
                        "levou a cópia que acabou de fazer")
        self.assertEqual({Path(p).name for p in r["copias"]},
                         {Path(r["backup"]).name})

    def test_levar_copias_sem_backup_nao_deixa_nada_dela(self):
        self.tres_pacotes()
        r = conta.apagar("miguel", confirmar=True, com_backup=False,
                         levar_copias=True)
        self.assertIsNone(r["backup"])
        self.assertEqual(r["copias"], [])
        self.assertEqual(conta.copias_de("miguel"), [])

    def test_leva_tambem_o_antes_de_importar(self):
        """O `importar` deixa um `.db` com a coleção inteira dela."""
        p = conta.exportar("miguel")["ficheiro"]
        imp = conta.importar(p, confirmar=True)
        self.assertIsNotNone(imp["backup"])
        self.assertIn(Path(imp["backup"]).name,
                      {Path(x).name for x in conta.copias_de("miguel")})
        conta.apagar("miguel", confirmar=True, com_backup=False,
                     levar_copias=True)
        self.assertFalse(Path(imp["backup"]).exists())

    def test_NAO_leva_os_pacotes_de_OUTRA_PESSOA(self):
        """O teste que a regra do nome exige: `conta-miguel-2-…` não é do
        `miguel`. Um prefixo cego apagava o backup de outra pessoa."""
        outra = utilizador.criar("Miguel 2", "miguel-2")
        con = db.connect(user_id=outra["user_id"])
        collection.adjust(con, "tst-001-100", 2, source="test")
        con.close()
        dela = conta.exportar("miguel-2")["ficheiro"]
        dele = conta.exportar("miguel")["ficheiro"]
        self.assertNotIn(dela.name,
                         {Path(x).name for x in conta.copias_de("miguel")})
        conta.apagar("miguel", confirmar=True, com_backup=False,
                     levar_copias=True)
        self.assertTrue(dela.exists(), "levou o pacote de outra pessoa")
        self.assertFalse(dele.exists())

    def test_as_copias_de_quem_nao_tem_nenhuma(self):
        self.assertEqual(conta.copias_de("miguel"), [])

    def test_apagar_continua_a_nao_tocar_no_andre(self):
        a = self.foto(self.vault_a, utilizador.ANDRE)
        self.tres_pacotes()
        conta.apagar("miguel", confirmar=True, levar_copias=True)
        self.assertEqual(self.foto(self.vault_a, utilizador.ANDRE), a)

    def test_o_nome_de_um_pacote_e_legivel_pela_mesma_regra_que_o_escreve(self):
        """Se o formato do nome mudar de um lado tem de mudar do outro."""
        p = conta.exportar("miguel")["ficheiro"]
        self.assertRegex(p.name, conta.NOME_DE_PACOTE)
        self.assertEqual(conta.NOME_DE_PACOTE.match(p.name).group("slug"),
                         "miguel")


class TestAConsola(unittest.TestCase):
    """As duas portas estão na consola — é lá que um restauro se faz.

    Lê-se o código-fonte, como o resto da casa faz com o `app.js`: o que se
    fixa é que a porta EXISTE e que o caminho passa por ela. Sem isto, o
    `adoptar` podia ficar só no módulo e quem está a restaurar às duas da manhã
    não tinha como lhe chegar.
    """

    @classmethod
    def setUpClass(cls):
        cls.src = (Path(__file__).resolve().parent.parent / "riftvault"
                   / "cli.py").read_text(encoding="utf-8")

    def test_ha_um_adoptar_e_vai_ao_importar(self):
        self.assertIn('"--adoptar"', self.src)
        self.assertIn("adoptar=bool(args.adoptar)", self.src)

    def test_a_recusa_do_dono_trocado_sai_escrita_e_nao_em_traceback(self):
        self.assertIn("except utilizador.DonoErrado", self.src)

    def test_ha_um_levar_copias_e_vai_ao_apagar(self):
        self.assertIn('"--levar-copias"', self.src)
        self.assertIn("levar_copias=bool(args.levar_copias)", self.src)

    def test_o_apagar_escreve_as_copias_que_ficam(self):
        self.assertIn('r["copias"]', self.src)

    def test_a_rota_de_apagar_tambem_as_diz(self):
        rotas = (Path(__file__).resolve().parent.parent / "riftvault"
                 / "rotas_conta.py").read_text(encoding="utf-8")
        self.assertIn('"copias"', rotas)


class TestAFronteira(Base):
    """O que não pode mudar com isto."""

    def test_o_catalogo_e_os_precos_nao_sao_de_ninguem(self):
        con = db.connect()
        n = con.execute("SELECT COUNT(*) FROM catalog.printings").fetchone()[0]
        con.close()
        p = conta.exportar("miguel")["ficheiro"]
        conta.importar(p, confirmar=True)
        con = db.connect()
        self.addCleanup(con.close)
        self.assertEqual(
            con.execute("SELECT COUNT(*) FROM catalog.printings").fetchone()[0], n)

    def test_a_privacidade_nao_e_dado_de_coleccao(self):
        """A escolha decide-se no REGISTO; a cópia na base é o testemunho."""
        self.assertNotIn("users", db.TABELAS_DE_DONO)

    def test_ler_a_privacidade_nao_cria_a_base_de_ninguem(self):
        nova = utilizador.criar("Ninguém", "ninguem-ainda")
        caminho = db.vault_de(nova["user_id"])
        self.assertFalse(caminho.exists())
        privacidade.de(None, nova["user_id"])
        self.assertFalse(caminho.exists(),
                         "ler a privacidade criou um vault.db vazio")

    def test_o_multi_continua_fechado_por_omissao(self):
        self.assertFalse(multi.aberto({}))


if __name__ == "__main__":
    unittest.main(verbosity=2)

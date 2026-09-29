"""ISOLAMENTO: dois utilizadores não se vêem em função pública nenhuma.

André, na ordem: *"quero que ESQUECER seja um ERRO, não uma leitura silenciosa
da tabela toda […] Percorre a API toda, não só a Colecção."*

A ordem foi escrita a contar com uma base só filtrada por `WHERE user_id = ?`.
**Não é esse o modelo que ficou** — é um ficheiro por pessoa (ver
`docs/multi-utilizador.md`) — e por isso o erro a apanhar mudou de forma. São
quatro guardas, e este ficheiro prova as quatro:

  1. tocar numa tabela de dono sem dono REBENTA, com a tabela nomeada;
  2. uma ligação ligada a alguém não pode ANEXAR outra base;
  3. uma base com linhas de outro dono recusa-se a abrir;
  4. ninguém abre um `vault.db` fora do `db.py` (lê-se o código-fonte).

E depois a prova de comportamento, que é a que interessa a quem usa isto: os
dois utilizadores têm colecções PARECIDAS — de propósito, para um engano não se
denunciar sozinho por os números serem obviamente de outra pessoa — e
**nenhuma das funções públicas deixa um ver, contar, valorizar ou escrever o
que é do outro**.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from riftvault import (a_mais, a_subir, collection, config, conta, db, decks,
                       faltas, faltas_edicao, faltas_foil, foil, guarda, locais,
                       metrics, painel, pending, principal, privacidade, prices,
                       proprias, runas_vista, selado, utilizador, venda)
from tests import fixture

# As sentinelas: cada um tem uma carta que o outro NÃO tem, com uma quantidade
# inconfundível. É por elas que se pergunta em cada payload.
SENT_A = "tst-001-100"      # o André tem 7; o Miguel 0
SENT_B = "tst-002-100"      # o Miguel tem 5; o André 0
COMUM = "tst-003-100"       # os dois têm — para o teste não passar só por
                            # tudo ser diferente
RUNA = "tst-004-100"        # para o bloco das runas ter o que contar
SO_DO_A = "tst-005-100"     # só o André tem, e nem completa
QTD_A, QTD_B = 7, 5

# Um texto que só existe na casa de cada um. Se aparecer no payload do outro,
# é fuga, e não é preciso saber que campo era.
SEGREDO_A = "SEGREDO-DO-ANDRE"
SEGREDO_B = "SEGREDO-DO-MIGUEL"


def sha_ficheiro(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else "—"


def linhas_de(caminho: Path, user_id: int) -> dict:
    """Todas as linhas das tabelas de dono de uma base, para comparar."""
    con = db.abrir_vault(caminho, user_id, readonly=True)
    try:
        fora = {}
        for t in db.TABELAS_DE_DONO:
            try:
                fora[t] = [tuple(r) for r in con.execute(
                    f"SELECT * FROM {t}")]  # noqa: S608 — `t` é interno
            except sqlite3.OperationalError:
                fora[t] = []
        return fora
    finally:
        con.close()


def texto(payload) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)


def tile_de(payload, printing_id: str) -> list[dict]:
    """Os dicionários do payload que falam DAQUELA impressão."""
    fora = []

    def anda(o):
        if isinstance(o, dict):
            if o.get("printing_id") == printing_id or o.get("id") == printing_id:
                fora.append(o)
            for v in o.values():
                anda(v)
        elif isinstance(o, list):
            for v in o:
                anda(v)
    anda(payload)
    return fora


class Dois(unittest.TestCase):
    """Duas pessoas, o mesmo catálogo, colecções PARECIDAS.

    Parecidas de propósito: se as colecções fossem obviamente diferentes, um
    engano denunciava-se sozinho pelos números, e o teste ficava a provar
    menos do que parece.
    """

    #: Um produto selado escrito à mão no config, para os dois poderem ter
    #: unidades DIFERENTES dele. Sem isto o `selado.payload` dá igual aos dois
    #: (ninguém tem nada) e o varrimento não prova nada sobre esse separador.
    SELADO = "cfg-tst-caixa-de-teste"   # `cfg-<slug(edicao + '-' + nome)>`

    def _config(self):
        """O config deste teste: a regra dos decks de hoje e um selado."""
        caminho = Path(tempfile.gettempdir()) / "riftvault-isolamento.json"
        caminho.write_text(json.dumps({
            "decks": {"so_base": False,
                      "so_normais_excepto": ["legend", "champion"],
                      "versoes_especiais": ["a", "overnumbered", "promo"]},
            "selado": {"extra": [{"nome": "Caixa de Teste", "edicao": "TST",
                                  "tipo": "caixa"}]},
        }), encoding="utf-8")
        os.environ["RIFTVAULT_CONFIG"] = str(caminho)
        self.addCleanup(lambda: os.environ.pop("RIFTVAULT_CONFIG", None))

    def setUp(self):
        self._config()
        self.v = fixture.Vault()
        self.addCleanup(self.v.close)

        # O catálogo é PARTILHADO: escreve-se uma vez e os dois lêem-no.
        con = self.v.connect()
        self.v.add_printing(con, SENT_A, "TST", 1, "Defy")
        self.v.add_printing(con, SENT_B, "TST", 2, "Brutalizer")
        self.v.add_printing(con, COMUM, "TST", 3, "Emperor of the Sands",
                            card_type="Legend")
        # Uma RUNA, para o bloco das runas ter o que contar, e uma quarta
        # carta que só um deles tem — sem ela os dois têm o mesmo NÚMERO de
        # impressões e o painel dá igual aos dois por coincidência.
        self.v.add_printing(con, RUNA, "TST", 4, "Calm Rune", card_type="Rune")
        self.v.add_printing(con, SO_DO_A, "TST", 5, "Sabotage")
        self.v.rebuild(con)
        for pid, cents in ((SENT_A, 12345), (SENT_B, 6789), (COMUM, 4242),
                           (RUNA, 11), (SO_DO_A, 500)):
            con.execute("INSERT OR REPLACE INTO catalog.price_latest "
                        "(printing_id, price_cents, currency, source, day) "
                        "VALUES (?,?,'EUR','test','2026-09-29')", (pid, cents))

        # A colecção do ANDRÉ. Cada um deixa pegada em TODOS os subsistemas —
        # senão as funções de um separador vazio dão igual aos dois e o
        # varrimento não prova nada sobre elas.
        collection.adjust(con, SENT_A, QTD_A, source="test")
        collection.adjust(con, COMUM, 1, source="test")
        collection.adjust(con, SO_DO_A, 1, source="test")
        foil.ajustar(con, SENT_A, 2)
        pending.encomendar(con, printing_id=SENT_A, qty=3, source="test")
        venda.juntar(con, SENT_A, 2)
        venda.guardar_trend(con, SENT_A, 11111)
        selado.ajustar(con, self.SELADO, 1)
        self.dir_a = config.decks_dir(con)
        (self.dir_a / "um.txt").write_text(
            f"Nome: {SEGREDO_A}\nLegend: Emperor of the Sands\n"
            f"MainDeck:\n1 Defy\n", encoding="utf-8")
        decks.import_all(con, log=lambda *_: None)
        con.close()

        # O MIGUEL
        self.miguel = utilizador.criar("Miguel", "miguel")
        self.uid_b = self.miguel["user_id"]
        conb = db.connect(user_id=self.uid_b)
        collection.adjust(conb, SENT_B, QTD_B, source="test")
        collection.adjust(conb, COMUM, 2, source="test")
        foil.ajustar(conb, SENT_B, 1)
        pending.encomendar(conb, printing_id=SENT_B, qty=1, source="test")
        venda.juntar(conb, SENT_B, 4)
        venda.guardar_trend(conb, SENT_B, 22222)
        selado.ajustar(conb, self.SELADO, 3)
        self.dir_b = config.decks_dir(conb)
        (self.dir_b / "um.txt").write_text(
            f"Nome: {SEGREDO_B}\nLegend: Emperor of the Sands\n"
            f"MainDeck:\n1 Brutalizer\n", encoding="utf-8")
        decks.import_all(conb, log=lambda *_: None)
        for d in decks.decks_index(conb):
            proprias.ajustar(conb, d["slug"], SENT_B, 1)
        runas_vista.semear(conb)
        runas_vista.ajustar(conb, "calm rune", 9)
        conb.close()

        # e o André também, para as `proprias` e as runas distinguirem
        con = db.connect(user_id=utilizador.ANDRE)
        for d in decks.decks_index(con):
            proprias.ajustar(con, d["slug"], SENT_A, 2)
        runas_vista.semear(con)
        runas_vista.ajustar(con, "calm rune", 4)
        con.close()

        self.vault_a = db.vault_de(utilizador.ANDRE)
        self.vault_b = db.vault_de(self.uid_b)


class DoisUtilizadores(Dois):
    """O varrimento da API."""

    #: AS QUE PODEM DAR O MESMO AOS DOIS, e porquê. Uma função que devolve o
    #: mesmo aos dois é, à partida, uma função que não sabe de quem são os
    #: dados — por isso a lista é curta e cada entrada tem de ter razão.
    #:
    #: `principal.estado` — qual é o deck principal vive no
    #: `riftvault_config.json`, que é UM ficheiro para toda a gente. **É
    #: limitação conhecida e está escrita** (`docs/multi-utilizador.md`,
    #: secção 6): o config por utilizador é a fatia seguinte. Até lá o ESTADO
    #: dos decks — montados, principal, ordem — é o do dono do ficheiro, e a
    #: escrita está fechada a quem não é ele (`config.ConfigPartilhado`).
    #: **As CARTAS de cada um contam na mesma**, que é o que interessa.
    PODEM_SER_IGUAIS = ("principal.estado",)

    # -- as funções públicas, uma a uma ---------------------------------

    def funcoes(self):
        """A API toda que devolve dados de dono. O nome é o do relatório."""
        cfg = config.load()
        return {
            "metrics.index_payload":
                lambda c: metrics.index_payload(c, editable=False,
                                                image_mode="remote", cfg=cfg),
            "metrics.set_payload":
                lambda c: metrics.set_payload(c, "TST", editable=False,
                                              image_mode="remote"),
            "metrics.niveis_payload": lambda c: metrics.niveis_payload(c, cfg),
            "painel.payload": lambda c: painel.payload(c, cfg),
            "runas_vista.payload": lambda c: runas_vista.payload(c, cfg),
            "collection.totals": lambda c: collection.totals(c),
            "collection.history": lambda c: collection.history(c, limit=50),
            "prices.collection_value": lambda c: prices.collection_value(c),
            "prices.value_by_set": lambda c: prices.value_by_set(c),
            "a_subir.master_faltas": lambda c: a_subir.master_faltas(c),
            "a_subir.wantlist": lambda c: a_subir.wantlist(c),
            "faltas.compras": lambda c: faltas.compras(c),
            "faltas_edicao.payload": lambda c: faltas_edicao.payload(c),
            "faltas_foil.payload_completo": lambda c: faltas_foil.payload_completo(c),
            "a_mais.payload": lambda c: a_mais.payload(c),
            "pending.encomendas": lambda c: pending.encomendas(c),
            "pending.totals": lambda c: pending.totals(c),
            "pending.grelha": lambda c: pending.grelha(c, "TST", editable=False,
                                                       image_mode="remote", cfg=cfg),
            "decks.decks_index": lambda c: decks.decks_index(c),
            "decks.deck_payload": lambda c: [
                decks.deck_payload(c, d["id"]) for d in decks.decks_index(c)],
            "principal.estado": lambda c: principal.estado(c, cfg),
            "venda.payload": lambda c: venda.payload(c, cfg, editable=False),
            "selado.payload": lambda c: selado.payload(c, cfg, editable=False),
            "locais.resumo": lambda c: locais.resumo(c),
            "locais.na_colecao": lambda c: locais.na_colecao(c, cfg),
            "foil.resumo": lambda c: foil.resumo(c, cfg),
            "locais.proprias": lambda c: locais.proprias(c),
            "uso_decks.estado": lambda c: {
                f"{k[0]}|{k[1]}": v for k, v in
                __import__("riftvault.uso_decks", fromlist=["x"]).estado(c).items()},
        }

    def test_nenhuma_funcao_publica_mostra_o_outro(self):
        """O varrimento. Para cada função: os dois payloads, e três perguntas."""
        ca = db.connect(user_id=utilizador.ANDRE)
        cb = db.connect(user_id=self.uid_b)
        self.addCleanup(ca.close)
        self.addCleanup(cb.close)
        testadas, iguais = [], []
        for nome, f in self.funcoes().items():
            with self.subTest(funcao=nome):
                pa, pb = f(ca), f(cb)
                ta, tb = texto(pa), texto(pb)
                # 1. o segredo do outro NUNCA aparece
                self.assertNotIn(SEGREDO_B, ta, f"{nome}: o André vê o Miguel")
                self.assertNotIn(SEGREDO_A, tb, f"{nome}: o Miguel vê o André")
                # 2. a sentinela de cada um vale o que é dele, e zero no outro
                for tile in tile_de(pa, SENT_B):
                    for campo in ("qty", "have", "qty_total"):
                        if campo in tile:
                            self.assertEqual(tile[campo], 0,
                                             f"{nome}: o André conta {campo} do Miguel")
                for tile in tile_de(pb, SENT_A):
                    for campo in ("qty", "have", "qty_total"):
                        if campo in tile:
                            self.assertEqual(tile[campo], 0,
                                             f"{nome}: o Miguel conta {campo} do André")
                if ta == tb:
                    iguais.append(nome)
                testadas.append(nome)
        self.assertEqual(sorted(iguais), sorted(self.PODEM_SER_IGUAIS),
                         "mudou quem distingue os donos e quem não distingue")
        self.assertGreaterEqual(len(testadas), 25,
                                "o varrimento encolheu — é para percorrer a API toda")

    def test_o_valor_de_cada_um_e_o_dele(self):
        ca = db.connect(user_id=utilizador.ANDRE)
        cb = db.connect(user_id=self.uid_b)
        self.addCleanup(ca.close)
        self.addCleanup(cb.close)
        # O valor conta as NORMAIS da Coleção e as FOILS (2026-09-26,
        # `foil.conta_para_valor`), e NÃO conta as cópias próprias de um deck.
        #   André : 7×123,45 + 1×42,42 + 1×5,00 + 2 foil×123,45 = 1 158,47 €
        #   Miguel: 5×67,89 + 2×42,42 + 1 foil×67,89           =   492,18 €
        esperado_a = QTD_A * 12345 + 4242 + 500 + 2 * 12345
        esperado_b = QTD_B * 6789 + 2 * 4242 + 1 * 6789
        self.assertEqual(prices.collection_value(ca)["cents"], esperado_a)
        self.assertEqual(prices.collection_value(cb)["cents"], esperado_b)
        self.assertNotEqual(esperado_a, esperado_b)
        # e as CÓPIAS PRÓPRIAS de um deck não entram no valor de ninguém
        self.assertNotIn(2 * 12345, (prices.collection_value(cb)["cents"],))


class EscreverNumNaoMexeNoOutro(Dois):
    """Escrever como A não pode mexer num byte de B — e ao contrário."""

    def _fotografia_b(self):
        return (sha_ficheiro(self.vault_b), linhas_de(self.vault_b, self.uid_b))

    def _fotografia_a(self):
        return (sha_ficheiro(self.vault_a),
                linhas_de(self.vault_a, utilizador.ANDRE))

    def _escrever_tudo(self, con, sent):
        """Todas as escritas que há, como aquele utilizador."""
        collection.adjust(con, sent, 2, source="test")
        collection.adjust(con, sent, -1, source="test")
        foil.ajustar(con, sent, 1)
        pending.encomendar(con, printing_id=sent, qty=1, source="test")
        pending.anular(con, printing_id=sent, qty=1, source="test")
        venda.juntar(con, sent, 1)
        venda.guardar_trend(con, sent, 1000)
        venda.limpar(con)
        runas_vista.semear(con)
        locais.mover(con, sent, 1, locais.COLECAO, locais.BINDER, source="test")
        locais.mover(con, sent, 1, locais.BINDER, locais.COLECAO, source="test")
        for d in decks.decks_index(con):
            proprias.ajustar(con, d["slug"], sent, 1)

    def test_as_escritas_todas_como_andre_nao_tocam_no_miguel(self):
        antes = self._fotografia_b()
        con = db.connect(user_id=utilizador.ANDRE)
        try:
            self._escrever_tudo(con, SENT_A)
        finally:
            con.close()
        self.assertEqual(self._fotografia_b(), antes,
                         "escrever na casa do André mexeu na do Miguel")

    def test_e_ao_contrario(self):
        antes = self._fotografia_a()
        conb = db.connect(user_id=self.uid_b)
        try:
            self._escrever_tudo(conb, SENT_B)
        finally:
            conb.close()
        self.assertEqual(self._fotografia_a(), antes,
                         "escrever na casa do Miguel mexeu na do André")

    def test_e_as_fotografias_nao_sao_de_zeros(self):
        """A prova pela negativa: sem isto, os dois de cima passavam mesmo que
        a fotografia não visse nada."""
        antes_a, antes_b = self._fotografia_a(), self._fotografia_b()
        con = db.connect(user_id=utilizador.ANDRE)
        collection.adjust(con, SENT_A, 1, source="test")
        con.close()
        conb = db.connect(user_id=self.uid_b)
        collection.adjust(conb, SENT_B, 1, source="test")
        conb.close()
        self.assertNotEqual(self._fotografia_a(), antes_a)
        self.assertNotEqual(self._fotografia_b(), antes_b)


class TestOGuardaRebenta(unittest.TestCase):
    """1 e 2: o que acontece a quem se esquece de dizer de quem são os dados."""

    def setUp(self):
        self.v = fixture.Vault()
        self.addCleanup(self.v.close)
        fixture.catalogo_simples(self.v)

    def test_ler_uma_tabela_de_dono_sem_dono_rebenta_e_diz_qual(self):
        con = db.connect()
        con.riftvault_user = None          # é isto que a autenticação vai poder ser
        with self.assertRaises(guarda.SemDono) as e:
            con.execute("SELECT qty FROM copies").fetchone()
        self.assertIn("copies", str(e.exception))
        self.assertIn("db.connect", str(e.exception))
        con.close()

    def test_escrever_tambem(self):
        con = db.connect()
        con.riftvault_user = None
        with self.assertRaises(guarda.SemDono):
            con.execute("UPDATE copies SET qty = 99")
        con.close()

    def test_cada_uma_das_16_tabelas_de_dono(self):
        con = db.connect()
        con.riftvault_user = None
        for t in db.TABELAS_DE_DONO:
            with self.subTest(tabela=t):
                with self.assertRaises(guarda.SemDono) as e:
                    con.execute(f"SELECT * FROM {t} LIMIT 1").fetchall()
                self.assertIn(t, str(e.exception))
        con.close()

    def test_o_catalogo_e_os_precos_passam_sem_dono(self):
        """São partilhados: o jogo e o mercado não são de ninguém."""
        con = db.connect()
        con.riftvault_user = None
        self.assertIsNotNone(
            con.execute("SELECT COUNT(*) FROM catalog.printings").fetchone())
        self.assertIsNotNone(
            con.execute("SELECT COUNT(*) FROM prices.price_history").fetchone())
        self.assertIsNotNone(con.execute("SELECT COUNT(*) FROM users").fetchone())
        con.close()

    def test_com_dono_passa(self):
        con = db.connect()
        self.assertIsNotNone(con.execute("SELECT qty FROM copies").fetchone())
        con.close()

    def test_uma_ligacao_ligada_nao_anexa_outra_base(self):
        """A única maneira de dois donos aparecerem no mesmo SELECT."""
        con = db.connect()
        outra = self.v.data / "outra.db"
        sqlite3.connect(outra).close()
        with self.assertRaises(guarda.SoUmaBase):
            con.execute("ATTACH DATABASE ? AS outra", (str(outra),))
        con.close()

    def test_o_backup_de_uma_MIGRACAO_continua_a_funcionar(self):
        """A armadilha que o guarda quase criou, e é a maior desta ordem.

        O `db.backup` faz `VACUUM <schema> INTO`, que **anexa o ficheiro de
        destino por dentro** — e o guarda recusa `ATTACH`. São **sete** os
        sítios que lhe chamam, e cinco são migrações que correm de DENTRO do
        `db.connect` numa base antiga: se isto se partisse, o arranque de uma
        base antiga partia-se com ele. (Alcance apontado pela sessão
        `riftbound-da`, que sugeriu testar a migração e não só a base nova.)
        """
        con = db.connect()
        alvo = db.backup(con, "teste-do-guarda")
        con.close()
        self.assertIsNotNone(alvo, "o `db.backup` devolveu None — o VACUUM "
                                   "foi recusado pelo guarda")
        self.assertTrue(alvo.exists() and alvo.stat().st_size > 0)
        # e a cópia abre e tem a coleção lá dentro
        copia = db.abrir_vault(alvo, utilizador.ANDRE, readonly=True)
        try:
            self.assertEqual(
                copia.execute("SELECT COUNT(*) FROM copies").fetchone()[0], 3)
        finally:
            copia.close()

    def test_uma_base_ANTIGA_migra_com_o_guarda_armado(self):
        """Uma base sem a coluna `user_id` e sem a `users` — o estado real do
        `data/vault.db` antes desta semana. A migração faz backup e corre
        ANTES de o guarda armar; se a ordem estivesse trocada, o primeiro
        arranque depois do merge rebentava na coleção dele."""
        v = fixture.Vault()
        self.addCleanup(v.close)
        fixture.catalogo_simples(v)
        con = db.connect()
        con.execute("PRAGMA foreign_keys=OFF")
        # desfaz a migração: tira a `users` e a coluna de uma tabela de dono
        con.execute("DROP TABLE users")
        con.execute("CREATE TABLE copies_velha (printing_id TEXT PRIMARY KEY, "
                    "qty INTEGER NOT NULL, updated_at TEXT NOT NULL, "
                    "qty_foil INTEGER NOT NULL DEFAULT 0)")
        con.execute("INSERT INTO copies_velha SELECT printing_id, qty, "
                    "updated_at, qty_foil FROM copies")
        con.execute("DROP TABLE copies")
        con.execute("ALTER TABLE copies_velha RENAME TO copies")
        antes = con.execute("SELECT printing_id, qty FROM copies "
                            "ORDER BY printing_id").fetchall()
        con.close()

        con = db.connect()          # é aqui que a migração corre
        self.addCleanup(con.close)
        cols = {r[1] for r in con.execute("PRAGMA table_info(copies)")}
        self.assertIn("user_id", cols, "a migração não correu")
        self.assertEqual(
            con.execute("SELECT printing_id, qty FROM copies "
                        "ORDER BY printing_id").fetchall(), antes,
            "a migração mexeu num número")
        # e o guarda ficou armado no fim
        con.riftvault_user = None
        with self.assertRaises(guarda.SemDono):
            con.execute("SELECT qty FROM copies").fetchone()

    def test_o_guarda_nao_custa_nada(self):
        """Medido a 2026-09-29: 50 000 consultas em 48 ms armado contra 49 ms
        desarmado. Aqui só se exige que não seja uma ordem de grandeza."""
        import time
        con = db.connect()
        n = 2000
        t0 = time.perf_counter()
        for _ in range(n):
            con.execute("SELECT qty FROM copies WHERE printing_id='tst-001-100'"
                        ).fetchone()
        armado = time.perf_counter() - t0
        con.set_authorizer(None)
        t0 = time.perf_counter()
        for _ in range(n):
            con.execute("SELECT qty FROM copies WHERE printing_id='tst-001-100'"
                        ).fetchone()
        sem = time.perf_counter() - t0
        con.close()
        self.assertLess(armado, max(sem * 5, 0.5),
                        f"o guarda custa demais: {armado:.3f}s vs {sem:.3f}s")


class TestUmaBaseDeOutroDonoRecusaSeAAbrir(unittest.TestCase):
    """3: a rede que apanha um ficheiro trocado ou um backup restaurado por
    cima do outro."""

    def test_dono_errado(self):
        v = fixture.Vault()
        self.addCleanup(v.close)
        fixture.catalogo_simples(v)
        con = db.connect()
        # Sem a FK: numa base criada DE RAIZ a coluna leva
        # `REFERENCES users(user_id)` e o SQLite recusa um dono inventado —
        # o que se quer simular aqui é o ficheiro trocado, que chega de uma
        # base MIGRADA (essa não tem FK; ver `docs/multi-utilizador.md`).
        con.execute("PRAGMA foreign_keys=OFF")
        con.execute("UPDATE copies SET user_id = 99")
        con.close()
        with self.assertRaises(utilizador.DonoErrado) as e:
            db.connect(user_id=utilizador.ANDRE).close()
        self.assertIn("copies", str(e.exception))
        self.assertIn("99", str(e.exception))


class TestNinguemAbreUmVaultForaDoDb(unittest.TestCase):
    """4: a guarda estática. É por aqui que se chegaria ao ficheiro errado sem
    passar por nenhuma das outras três."""

    PACOTE = Path(__file__).resolve().parent.parent / "riftvault"
    #: quem pode abrir uma base de DONO: o `db.py`, que é a porta única. O
    #: `utilizador.py` abre o REGISTO, que não é a coleção de ninguém.
    PODEM = {"db.py", "utilizador.py"}

    def test_so_o_db_e_o_registo_abrem_ligacoes(self):
        """Um módulo que abra um `sqlite3.connect` tem de PROVAR que não chega
        à coleção de ninguém — e a prova são DUAS propriedades do código, não
        o nome dele numa lista de excepções:

          * **não importa o `db`** — é de lá que sai o caminho de um `vault.db`
            (o `db.vault_de`);
          * **não nomeia o ficheiro do André** (`VAULT_DB`) — é o outro
            caminho, e o teste a seguir fecha-o.

        Juntas não deixam por onde: sem o `db` e sem o `VAULT_DB`, um módulo
        não consegue nomear a base de um utilizador. É o que deixa uma base do
        SERVIÇO — o registo, e a `data/auth.db` da autenticação — ser aberta
        onde faz sentido, sem abrir a porta a uma coleção.
        """
        maus = []
        for p in sorted(self.PACOTE.glob("*.py")):
            if p.name in self.PODEM:
                continue
            texto = p.read_text(encoding="utf-8")
            if "sqlite3.connect(" not in texto:
                continue
            if "import db" in texto or "VAULT_DB" in texto:
                maus.append(p.name)
        self.assertEqual(
            maus, [],
            f"abrem uma base e conseguem chegar a uma coleção: {maus}")

    def test_so_o_db_e_o_config_falam_do_ficheiro_do_andre(self):
        """`config.VAULT_DB` é o ficheiro DELE. Quem o usar directamente está
        a ler a colecção do André seja quem for que esteja na sessão."""
        maus = []
        for p in sorted(self.PACOTE.glob("*.py")):
            if p.name in {"db.py", "config.py"}:
                continue
            if "VAULT_DB" in p.read_text(encoding="utf-8"):
                maus.append(p.name)
        self.assertEqual(maus, [], f"usam o `config.VAULT_DB`: {maus}")


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""A COLEÇÃO É SOBERANA — e passa a ser TESTE, não regra falada (2026-09-29).

Da ordem: *"Já foi violada uma vez (a contagem dos foils, 26/09) e só se
apanhou por eu medir à mão. Escreve um teste que corre sempre e prova que
nenhuma operação fora do caminho da Coleção muda a `copies` de nenhum
utilizador."*

O QUE FOI A VIOLAÇÃO, porque é ela que define a forma deste teste. A 22/09 a
contagem de foil nasceu como uma FATIA do total (`CHECK (qty_foil <= qty)`) e
o `+` do foil CONVERTIA uma cópia normal. A 26/09 ele apanhou-o a olhar para o
ecrã: *"as foils quando eu marco é que tenho TAMBÉM foil, ou seja, normal +
foil"*. E a 27/09 apanhou a segunda metade: somar as foils aos ALVOS escondia
**48 cópias normais em falta, em 47 impressões**, que se liam «3/3». As duas
vezes foi ele a ver, não um teste.

TRÊS CAMADAS, porque «não mexe na `copies`» à letra seria mentira — há
operações que legitimamente lhe tocam, e escondê-las era pior:

  A. **O CAMINHO DA COLEÇÃO É UMA LISTA FECHADA.** Cinco operações podem mexer
     na `copies`. **Tudo o resto** — decks, selado, encomendas (marcar), venda
     (marcar), locais, runas, wantlist, privacidade, exportar, e o `build`
     inteiro — deixa-a byte a byte igual.
  B. **AS DUAS QUE TOCAM SEM SEREM A COLEÇÃO** (`foil.ajustar`,
     `proprias.ajustar`) **não mudam o número de cópias NORMAIS na Coleção**.
     É esta a invariante que a avaria de 26–27/09 partiu.
  C. **NADA DO QUE UM FAZ MEXE NA `copies` DO OUTRO.**

E cada camada tem a PROVA PELA NEGATIVA a seguir: um teste que mostra que a
fotografia sabe mesmo detectar uma mudança. Uma fotografia de zeros passa
sempre.
"""

from __future__ import annotations

import hashlib
import unittest

from riftvault import (a_mais, a_subir, build, collection, config, conta, db,
                       decks, faltas, faltas_edicao, faltas_foil, foil, locais,
                       metrics, painel, pending, principal, privacidade, prices,
                       proprias, runas_vista, selado, utilizador, venda)
from tests import fixture

#: As ÚNICAS que podem mexer na `copies`. Esta lista é a regra — se alguém
#: acrescentar uma sexta, este ficheiro tem de mudar, e mudá-lo é ter de
#: escrever porquê.
O_CAMINHO_DA_COLECCAO = (
    "collection.adjust",      # os `+`/`−` da grelha e o `riftvault add/remove`
    "collection.undo_last",   # o desfazer, que é o mesmo caminho ao contrário
    "pending.arrive",         # «Chegou» — entra pelo `collection.adjust`
    "venda.vender",           # «marcar como vendidas» — idem, com confirmação
    "foil.ajustar",           # o contador de FOIL (a coluna `qty_foil`)
    "proprias.ajustar",       # as cópias PRÓPRIAS de um deck (fora da Coleção)
)


def foto_copies(con) -> str:
    """O CONTEÚDO da `copies`: impressão, normais, foil. Nada mais.

    A coluna `user_id` fica de fora de propósito — a pergunta é «os números
    dele são os mesmos», e uma coluna nova não muda um número.
    """
    h = hashlib.sha256()
    for r in con.execute("SELECT printing_id, qty, qty_foil FROM copies "
                         "ORDER BY printing_id"):
        h.update(f"{r[0]}|{r[1]}|{r[2]}\n".encode())
    return h.hexdigest()


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
        for pid, c in (("tst-001-100", 1200), ("tst-002-100", 900),
                       ("tst-003-100", 5000)):
            con.execute("INSERT OR REPLACE INTO catalog.price_latest "
                        "(printing_id, price_cents, currency, source, day) "
                        "VALUES (?,?,'EUR','test','2026-09-29')", (pid, c))
        collection.adjust(con, "tst-001-100", 3, source="test")
        collection.adjust(con, "tst-002-100", 2, source="test")
        collection.adjust(con, "tst-003-100", 1, source="test")
        (config.decks_dir(con) / "ornn.txt").write_text(
            "Nome: Ornn\nLegend: Emperor of the Sands\nMainDeck:\n"
            "3 Defy\n2 Brutalizer\n", encoding="utf-8")
        decks.import_all(con, log=lambda *_: None)
        con.close()


class TestAListaFechada(Base):
    """A: tudo o que NÃO é o caminho da Coleção deixa-a igual."""

    def _tudo_o_resto(self, con):
        """Todas as operações que não são o caminho da Coleção. É o varrimento
        — decks, selado, encomendas, venda, wantlist, locais, runas, o build,
        e as leituras todas."""
        cfg = config.load()
        feitas = []

        # -- escritas que NÃO são a Coleção --------------------------------
        pending.encomendar(con, printing_id="tst-001-100", qty=2, source="test")
        feitas.append("pending.encomendar")
        pending.anular(con, printing_id="tst-001-100", qty=1, source="test")
        feitas.append("pending.anular")
        venda.juntar(con, "tst-002-100", 1); feitas.append("venda.juntar")
        venda.guardar_trend(con, "tst-002-100", 1500)
        feitas.append("venda.guardar_trend")
        venda.limpar(con); feitas.append("venda.limpar")
        runas_vista.semear(con); feitas.append("runas_vista.semear")
        locais.mover(con, "tst-001-100", 1, locais.COLECAO, locais.BINDER,
                     source="test"); feitas.append("locais.mover")
        locais.mover(con, "tst-001-100", 1, locais.BINDER, locais.COLECAO,
                     source="test"); feitas.append("locais.mover (de volta)")
        decks.import_all(con, log=lambda *_: None); feitas.append("decks.import_all")
        for d in decks.decks_index(con):
            decks.alternar_montado(con, d["slug"], False)
            decks.alternar_montado(con, d["slug"], True)
            feitas.append("decks.alternar_montado")
            break
        principal.definir(con, None); feitas.append("principal.definir")
        privacidade.definir(None, utilizador.ANDRE, "sem-valores")
        feitas.append("privacidade.definir")
        conta.exportar(utilizador.SLUG_ANDRE); feitas.append("conta.exportar")

        # -- leituras: todas ------------------------------------------------
        for nome, f in (
            ("metrics.index_payload",
             lambda: metrics.index_payload(con, editable=False,
                                           image_mode="remote", cfg=cfg)),
            ("metrics.set_payload",
             lambda: metrics.set_payload(con, "TST", editable=False,
                                         image_mode="remote")),
            ("metrics.niveis_payload", lambda: metrics.niveis_payload(con, cfg)),
            ("painel.payload", lambda: painel.payload(con, cfg)),
            ("runas_vista.payload", lambda: runas_vista.payload(con, cfg)),
            ("collection.totals", lambda: collection.totals(con)),
            ("prices.collection_value", lambda: prices.collection_value(con)),
            ("a_subir.master_faltas", lambda: a_subir.master_faltas(con)),
            ("a_subir.wantlist", lambda: a_subir.wantlist(con)),
            ("faltas.compras", lambda: faltas.compras(con)),
            ("faltas_edicao.payload", lambda: faltas_edicao.payload(con)),
            ("faltas_foil.payload_completo",
             lambda: faltas_foil.payload_completo(con)),
            ("a_mais.payload", lambda: a_mais.payload(con)),
            ("pending.encomendas", lambda: pending.encomendas(con)),
            ("pending.grelha",
             lambda: pending.grelha(con, "TST", editable=False,
                                    image_mode="remote", cfg=cfg)),
            ("decks.decks_index", lambda: decks.decks_index(con)),
            ("principal.estado", lambda: principal.estado(con, cfg)),
            ("venda.payload", lambda: venda.payload(con, cfg, editable=False)),
            ("selado.payload", lambda: selado.payload(con, cfg, editable=False)),
            ("locais.resumo", lambda: locais.resumo(con)),
            ("foil.resumo", lambda: foil.resumo(con, cfg)),
        ):
            f()
            feitas.append(nome)
        return feitas

    def test_nada_fora_do_caminho_mexe_na_copies(self):
        con = db.connect()
        self.addCleanup(con.close)
        antes = foto_copies(con)
        try:
            feitas = self._tudo_o_resto(con)
        except Exception:  # noqa: BLE001 — o que interessa é a fotografia
            raise
        self.assertGreaterEqual(len(feitas), 25,
                                "o varrimento encolheu — é para cobrir tudo")
        self.assertEqual(foto_copies(con), antes,
                         "alguma operação fora do caminho da Coleção mexeu na "
                         "`copies`")

    def test_o_build_inteiro_nao_mexe(self):
        con = db.connect()
        antes = foto_copies(con)
        con.close()
        build.build(self.v.root / "site", log=lambda *_: None)
        con = db.connect()
        self.addCleanup(con.close)
        self.assertEqual(foto_copies(con), antes, "o `build` mexeu na `copies`")

    def test_a_fotografia_nao_e_de_zeros(self):
        """A prova pela negativa: se a fotografia não detectasse nada, os
        testes acima passavam sempre."""
        con = db.connect()
        self.addCleanup(con.close)
        antes = foto_copies(con)
        collection.adjust(con, "tst-001-100", 1, source="test")
        self.assertNotEqual(foto_copies(con), antes)
        collection.adjust(con, "tst-001-100", -1, source="test")
        self.assertEqual(foto_copies(con), antes)

    def test_o_foil_tambem_entra_na_fotografia(self):
        """A avaria de 26/09 foi na coluna do foil — se ela não estivesse na
        fotografia, este ficheiro não a apanhava."""
        con = db.connect()
        self.addCleanup(con.close)
        antes = foto_copies(con)
        foil.ajustar(con, "tst-001-100", 1)
        self.assertNotEqual(foto_copies(con), antes)

    def test_a_lista_fechada_esta_escrita(self):
        self.assertEqual(len(O_CAMINHO_DA_COLECCAO), 6)
        for nome in O_CAMINHO_DA_COLECCAO:
            mod, func = nome.split(".")
            self.assertTrue(hasattr(globals()[mod], func), nome)


class TestOQueTocaSemSerAColeccao(Base):
    """B: o foil e as cópias próprias tocam na `copies` — mas o número da
    COLEÇÃO não pode mexer. É a invariante que 26–27/09 partiu."""

    def test_marcar_foil_nao_muda_as_copias_normais_da_coleccao(self):
        con = db.connect()
        self.addCleanup(con.close)
        antes = locais.na_colecao(con, com_foil=False)
        niveis = metrics.niveis_payload(con, config.load())
        foil.ajustar(con, "tst-001-100", 3)
        self.assertEqual(locais.na_colecao(con, com_foil=False), antes,
                         "marcar foil mexeu nas cópias NORMAIS da Coleção")
        self.assertEqual(metrics.niveis_payload(con, config.load()), niveis,
                         "marcar foil mexeu nos níveis — foi isto que a 27/09 "
                         "escondeu 48 cópias normais em falta")

    def test_copias_proprias_de_um_deck_nao_entram_na_coleccao(self):
        con = db.connect()
        self.addCleanup(con.close)
        antes = locais.na_colecao(con, com_foil=False)
        valor = prices.collection_value(con)["cents"]
        niveis = metrics.niveis_payload(con, config.load())
        slug = decks.decks_index(con)[0]["slug"]
        proprias.ajustar(con, slug, "tst-001-100", 2)
        self.assertEqual(locais.na_colecao(con, com_foil=False), antes)
        self.assertEqual(prices.collection_value(con)["cents"], valor,
                         "uma cópia própria de um deck valorizou a Coleção")
        self.assertEqual(metrics.niveis_payload(con, config.load()), niveis)

    def test_mas_a_copies_mexe_mesmo(self):
        """A prova pela negativa da camada B: as duas TOCAM na tabela — é por
        isso que estão na lista fechada e não no varrimento."""
        con = db.connect()
        self.addCleanup(con.close)
        antes = foto_copies(con)
        slug = decks.decks_index(con)[0]["slug"]
        proprias.ajustar(con, slug, "tst-001-100", 1)
        self.assertNotEqual(foto_copies(con), antes)


class TestNadaMexeNaColeccaoDoOutro(unittest.TestCase):
    """C: a metade multi-utilizador."""

    def setUp(self):
        fixture.config_decks_sem_alt_art(self)
        self.v = fixture.Vault()
        self.addCleanup(self.v.close)
        fixture.catalogo_simples(self.v)
        self.miguel = utilizador.criar("Miguel", "miguel")
        con = db.connect(user_id=self.miguel["user_id"])
        collection.adjust(con, "tst-002-100", 4, source="test")
        con.close()

    def _foto_do_miguel(self):
        con = db.connect(user_id=self.miguel["user_id"])
        try:
            return foto_copies(con)
        finally:
            con.close()

    def test_o_caminho_da_coleccao_do_andre_nao_toca_no_miguel(self):
        antes = self._foto_do_miguel()
        con = db.connect(user_id=utilizador.ANDRE)
        try:
            collection.adjust(con, "tst-001-100", 5, source="test")
            foil.ajustar(con, "tst-001-100", 2)
            pending.encomendar(con, printing_id="tst-001-100", qty=1,
                               source="test")
            pending.arrive(con, printing_id="tst-001-100")
        finally:
            con.close()
        self.assertEqual(self._foto_do_miguel(), antes)

    def test_e_a_fotografia_do_miguel_nao_e_de_zeros(self):
        antes = self._foto_do_miguel()
        con = db.connect(user_id=self.miguel["user_id"])
        try:
            collection.adjust(con, "tst-002-100", 1, source="test")
        finally:
            con.close()
        self.assertNotEqual(self._foto_do_miguel(), antes)


if __name__ == "__main__":
    unittest.main(verbosity=2)

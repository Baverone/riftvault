"""A ordem dos domínios e das runas é a DELE (André, 2026-10-15).

Palavras dele: *"Ordena as runas assim: Fury - Calm - Mind - Body - Chaos -
Order"* e, com uma captura do quadro Domínio do painel, *"aqui também, pela
ordem que eu te disse"*.

O que se fixa: a ordem das seis numa fonte só (`metrics.ORDEM_DOS_DOMINIOS`),
lida pelo quadro Domínio, pelo bloco «Runas — 12 de cada» (e o rasto do
contador antigo) e pelos domínios da Legend na página do deck; «Sem domínio»
e «Multi-domínio» a fechar o quadro; um domínio novo a entrar antes delas; e
que é APRESENTAÇÃO — virar a ordem ao contrário não mexe em número nenhum.

Contra pastas temporárias (`tests.fixture.Vault`); o `data/` nunca é tocado.
"""

from __future__ import annotations

import importlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.fixture import Vault, config_decks_sem_alt_art  # noqa: E402

config_decks_sem_alt_art()

A_DELE = ["fury", "calm", "mind", "body", "chaos", "order"]
RUNAS_DELE = ["Fury Rune", "Calm Rune", "Mind Rune", "Body Rune", "Chaos Rune", "Order Rune"]


class Base(unittest.TestCase):
    def setUp(self):
        config_decks_sem_alt_art(self)
        self.v = Vault()
        self.addCleanup(self.v.close)
        from riftvault import decks, metrics, painel, runas_vista
        for m in (metrics, painel, runas_vista, decks):
            importlib.reload(m)
        self.metrics, self.painel, self.rv, self.decks = metrics, painel, runas_vista, decks

    def catalogo(self, com_nova=False):
        """As seis runas do OGN, metidas por ordem ALFABÉTICA inversa (para a
        ordem do catálogo não dar a resposta por acaso), e uma runa de um
        domínio que a ordem não nomeia."""
        from riftvault import collection
        con = self.v.connect()
        nomes = sorted(RUNAS_DELE, reverse=True) + (["Zeal Rune"] if com_nova else [])
        for i, nome in enumerate(nomes, start=1):
            pid = f"ogn-{i:03d}-100"
            self.v.add_printing(con, pid, "OGN", i, nome, card_type="Rune", size=100)
        self.v.rebuild(con)
        for i, _ in enumerate(nomes, start=1):
            collection.adjust(con, f"ogn-{i:03d}-100", i, source="test")
        return con


class TestAFonteSo(Base):
    def test_a_ordem_e_a_dele(self):
        self.assertEqual(list(self.metrics.ORDEM_DOS_DOMINIOS), A_DELE)

    def test_o_painel_le_da_mesma_fonte(self):
        ids = [k for k, _ in self.painel.DOMINIOS]
        self.assertEqual(ids, A_DELE + ["none", "multi"])
        self.assertEqual([r for k, r in self.painel.DOMINIOS][:6],
                         ["Fury", "Calm", "Mind", "Body", "Chaos", "Order"])

    def test_o_desconhecido_vai_para_o_fim_por_ordem_alfabetica(self):
        chave = self.metrics.posicao_do_dominio
        self.assertEqual(sorted(["Zeal", "Order", "Aaa", "Fury Rune", "calm"], key=chave),
                         ["Fury Rune", "calm", "Order", "Aaa", "Zeal"])


class TestOQuadroDominio(Base):
    def test_as_seis_pela_ordem_dele_e_as_duas_de_fecho(self):
        itens = [(3, 1, "common", d) for d in reversed(A_DELE)]
        itens += [(3, 1, "common", "multi"), (3, 1, "common", "none")]
        c = self.painel.contar(itens)
        self.assertEqual([d["id"] for d in c["domain"]], A_DELE + ["none", "multi"])

    def test_um_dominio_novo_entra_antes_das_duas_de_fecho(self):
        itens = [(3, 1, "common", d) for d in ["zeal", "none", "multi", "order", "fury"]]
        c = self.painel.contar(itens)
        self.assertEqual([d["id"] for d in c["domain"]],
                         ["fury", "order", "zeal", "none", "multi"])
        self.assertEqual(c["domain"][2]["label"], "Zeal")   # não desaparece


class TestOBlocoDasRunas(Base):
    def test_as_seis_pela_ordem_dele_nas_duas_vistas(self):
        con = self.catalogo()
        p = self.rv.payload(con)
        self.assertEqual([x["name"] for x in p["runas"]], RUNAS_DELE)
        self.assertEqual([x["name"] for x in p["por_edicao"]["OGN"]["runas"]], RUNAS_DELE)

    def test_a_runa_que_a_ordem_nao_nomeia_vai_para_o_fim(self):
        con = self.catalogo(com_nova=True)
        p = self.rv.payload(con)
        self.assertEqual([x["name"] for x in p["runas"]], RUNAS_DELE + ["Zeal Rune"])

    def test_o_rasto_do_contador_antigo_tambem(self):
        con = self.catalogo()
        for ck in ("body rune", "calm rune", "order rune", "fury rune"):
            con.execute("INSERT INTO rune_counter_antes (card_key, qty, seeded_from, "
                        "updated_at, arquivado_em) VALUES (?,1,0,'x','y')", (ck,))
        a = self.rv.arquivo(con)
        self.assertEqual([r["card_key"] for r in a["linhas"]],
                         ["fury rune", "calm rune", "body rune", "order rune"])


class TestAPaginaDoDeck(Base):
    def test_os_dominios_da_legend(self):
        self.assertEqual(self.decks._por_dominio({"Order", "Body", "Calm"}),
                         ["Calm", "Body", "Order"])


class TestEApresentacao(Base):
    """Virar a ordem ao contrário muda a ORDEM e não um número."""

    def _numeros(self, con):
        p = self.rv.payload(con)
        runas = sorted((x["name"], x["total"], x["sem_retiradas"], x["contador"],
                        x["target"]) for x in p["runas"])
        return runas, p["totals"]

    def test_ao_contrario_da_os_mesmos_numeros(self):
        con = self.catalogo(com_nova=True)
        antes = self._numeros(con)
        self.assertNotEqual(antes[1]["total"], 0)   # a fotografia não é de zeros
        original = self.metrics.ORDEM_DOS_DOMINIOS
        self.metrics.ORDEM_DOS_DOMINIOS = tuple(reversed(original))
        self.addCleanup(setattr, self.metrics, "ORDEM_DOS_DOMINIOS", original)
        p = self.rv.payload(con)
        # A prova pela negativa: a ordem mudou mesmo…
        self.assertNotEqual([x["name"] for x in p["runas"]][:6], RUNAS_DELE)
        # …e os números não.
        self.assertEqual(self._numeros(con), antes)


if __name__ == "__main__":
    unittest.main()

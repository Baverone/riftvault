"""A RADIANCE POR NÚMERO, NÃO POR NOME (2026-10-15).

André, a olhar para a aba da Radiance: *"nao podes ordenar por numeraçao?"*. A
dotgg devolve as cartas por ordem ALFABÉTICA de nome, e o `api_sort` saía dessa
ordem de chegada. As outras cinco edições (RiftScribe) leem-se pelo número, com
as variantes coladas à base. O que se prova aqui:

  1. o `api_sort` da dotgg sai do NÚMERO, venha a resposta pela ordem que vier;
  2. as variantes ficam coladas à base, na ordem da RiftScribe;
  3. correr o sync duas vezes dá o mesmo, e arruma uma RAD gravada por nome;
  4. a sobrenumerada (acima do tamanho) fica depois da última da sequência;
  5. a grelha da edição abre pela RAD-001.
"""

from __future__ import annotations

import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.test_radiance_dotgg import DOTGG, Base  # noqa: E402

# A ordem que a RiftScribe daria a esta RAD de brincar (tamanho 5): por número,
# e dentro dele a família principal ('', a, star), as promos de evento (p, p2) e
# as séries por ordem do nome (r01, r01a, sp1, t02).
ESPERADA = [
    "rad-001", "rad-001a", "rad-001-p", "rad-001-p2", "rad-r01", "rad-r01a", "rad-sp1",
    "rad-002", "rad-t02",
    "rad-003",
    "rad-006", "rad-006-star",
]

# A resposta como a dotgg a dá de verdade: ALFABÉTICA por nome.
ALFABETICA = sorted(DOTGG, key=lambda l: (l["name"], l["id"]))


class Ordem(Base):
    def ordem(self):
        return [r["printing_id"] for r in self.con.execute(
            "SELECT printing_id FROM catalog.printings WHERE set_id = 'RAD' ORDER BY api_sort")]

    def sorts(self):
        return {r["printing_id"]: r["api_sort"] for r in self.con.execute(
            "SELECT printing_id, api_sort FROM catalog.printings WHERE set_id = 'RAD'")}

    def sync(self, linhas):
        self.dotgg.sync(linhas_api=linhas, log=lambda *_: None)


class TestPorNumero(Ordem):
    def test_a_resposta_alfabetica_sai_por_numero(self):
        self.sync(ALFABETICA)
        self.assertEqual(self.ordem(), ESPERADA)

    def test_o_numero_nunca_desce(self):
        self.sync(ALFABETICA)
        cns = [r[0] for r in self.con.execute(
            "SELECT collector_number FROM catalog.printings WHERE set_id = 'RAD' ORDER BY api_sort")]
        self.assertEqual(cns, sorted(cns))

    def test_o_api_sort_e_0_a_n_menos_1(self):
        self.sync(ALFABETICA)
        self.assertEqual(sorted(self.sorts().values()), list(range(len(ESPERADA))))

    def test_qualquer_ordem_de_chegada_da_o_mesmo(self):
        for semente in range(5):
            linhas = list(DOTGG)
            random.Random(semente).shuffle(linhas)
            self.sync(linhas)
            self.assertEqual(self.ordem(), ESPERADA, f"semente {semente}")


class TestVariantesColadas(Ordem):
    def test_a_base_vem_primeiro_e_depois_alt_e_assinada(self):
        self.sync(ALFABETICA)
        o = self.ordem()
        self.assertEqual(o.index("rad-001a"), o.index("rad-001") + 1)
        self.assertEqual(o.index("rad-006-star"), o.index("rad-006") + 1)

    def test_as_variantes_de_um_numero_ficam_juntas(self):
        self.sync(ALFABETICA)
        cns = {r[0]: r[1] for r in self.con.execute(
            "SELECT printing_id, collector_number FROM catalog.printings WHERE set_id = 'RAD'")}
        vistos, anterior = set(), None
        for pid in self.ordem():
            cn = cns[pid]
            if cn != anterior:
                self.assertNotIn(cn, vistos, f"o número {cn} aparece em dois sítios")
                vistos.add(cn)
            anterior = cn

    def test_a_chave_segue_a_riftscribe_no_ven(self):
        # VEN da RiftScribe: '', r04, sp4, t04 no mesmo número.
        rows = [{"collector_number": 4, "variant": v, "lane": self.cat.lane_of(v)}
                for v in ("t04", "sp4", "", "r04")]
        self.assertEqual([r["variant"] for r in self.dotgg.ordenar(rows)],
                         ["", "r04", "sp4", "t04"])


class TestIdempotente(Ordem):
    def test_duas_vezes_da_o_mesmo(self):
        self.sync(ALFABETICA)
        antes = self.sorts()
        self.sync(ALFABETICA)
        self.assertEqual(self.sorts(), antes)

    def test_arruma_uma_rad_gravada_por_nome(self):
        # O estado do catálogo real antes desta correcção: api_sort pela chegada.
        with self.con:
            for i, l in enumerate(ALFABETICA[:-1]):
                self.con.execute("UPDATE catalog.printings SET api_sort = ? WHERE printing_id = ?",
                                 (i, l["id"].lower()))
        self.assertNotEqual(self.ordem(), ESPERADA)
        self.sync(ALFABETICA)
        self.assertEqual(self.ordem(), ESPERADA)

    def test_os_ids_nao_mudam(self):
        antes = set(self.sorts())
        self.sync(ALFABETICA)
        self.assertEqual(set(self.sorts()), antes)


class TestSobrenumerada(Ordem):
    def test_a_sobrenumerada_fica_depois_da_ultima_da_sequencia(self):
        self.sync(ALFABETICA)
        s = self.sorts()
        ultima_seq = max(s[p] for p in ("rad-001", "rad-002", "rad-003", "rad-t02"))
        self.assertGreater(s["rad-006"], ultima_seq)
        self.assertGreater(s["rad-006-star"], s["rad-006"])


class TestGrelha(Ordem):
    def test_o_bloco_master_abre_pela_001(self):
        self.sync(ALFABETICA)
        p = self.m.set_payload(self.con, "RAD")
        master = [pid for bloco, pid in self.m.ordem_da_grelha(p) if bloco == "master"]
        self.assertEqual(master[:3], ["rad-001", "rad-002", "rad-003"])


if __name__ == "__main__":
    unittest.main()

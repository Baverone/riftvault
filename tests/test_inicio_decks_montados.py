"""O CARTÃO «DECKS MONTADOS» DO INÍCIO conta os MONTADOS (2026-10-13).

Medido a 2026-10-13 no site: o Início dizia «DECKS MONTADOS 1 de 2» com
`decks.montados: []` — nenhum montado. O número era quantos decks estavam
COMPLETOS (o Kennen, 54/54), e o rótulo dizia outra coisa: um rótulo a mentir
no sítio mais visível do site.

Ficam aqui as duas perguntas separadas: o número grande é quantos estão
MONTADOS (o `montado` de cada deck, que o `decks_index` já levava desde
2026-09-24), e quantos estão COMPLETOS vai na nota. A contagem é uma função
pura do `app.js` (`iniDecksContagem`), corrida no node com o caso dele.
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.fixture import REPO  # noqa: E402
from tests.test_desmontar import Base  # noqa: E402

APP_JS = (REPO / "riftvault" / "web" / "app.js").read_text(encoding="utf-8")


def _tem_node() -> bool:
    try:
        subprocess.run(["node", "--version"], capture_output=True, timeout=20)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def _extrair(inicio: str, fim: str) -> str:
    i = APP_JS.index(inicio)
    return APP_JS[i:APP_JS.index(fim, i) + len(fim)]


def _contar(decks: list[dict]) -> dict:
    corpo = _extrair("function iniDecksContagem", "\n}")
    prog = "%s\nconsole.log(JSON.stringify(iniDecksContagem(%s)));" % (
        corpo, json.dumps(decks))
    out = subprocess.run(["node", "-e", prog], capture_output=True, text=True)
    if out.returncode:
        raise AssertionError(out.stderr)
    return json.loads(out.stdout)


@unittest.skipUnless(_tem_node(), "node não está instalado")
class TestAContagem(unittest.TestCase):
    def test_o_caso_dele_nenhum_montado_um_completo(self):
        """Os dois decks de 2026-10-13: ambos desmontados, o Kennen completo
        (54/54) e a Leona a faltar 4. Montados: ZERO — não 1."""
        c = _contar([
            {"slug": "leona-radiant-dawn", "montado": False, "missing": 4},
            {"slug": "kennen-heart-of-the-tempest", "montado": False, "missing": 0},
        ])
        self.assertEqual(c, {"n": 2, "montados": 0, "completos": 1, "faltam": 4})

    def test_montado_e_completo_sao_perguntas_diferentes(self):
        c = _contar([{"montado": True, "missing": 3}, {"montado": True, "missing": 0},
                     {"montado": False, "missing": 0}])
        self.assertEqual((c["montados"], c["completos"]), (2, 2))
        c = _contar([{"montado": True, "missing": 5}])
        self.assertEqual((c["montados"], c["completos"]), (1, 0))

    def test_sem_o_campo_conta_como_montado(self):
        """Um payload anterior a 2026-09-24 não traz `montado`; a omissão do
        config é «todos montados», e é isso que se lê."""
        self.assertEqual(_contar([{"missing": 0}, {"missing": 1}])["montados"], 2)


class TestOCartao(unittest.TestCase):
    def _cartao(self) -> str:
        i = APP_JS.index("const c = iniDecksContagem(decks)")
        return APP_JS[i:i + 900]

    def test_o_numero_grande_e_o_dos_montados(self):
        t = self._cartao()
        self.assertIn("`${c.montados}<small> de ${c.n}</small>`", t)

    def test_o_numero_dos_completos_nao_e_o_numero_grande(self):
        t = self._cartao()
        self.assertNotIn("`${c.completos}<small>", t)
        self.assertNotIn("const cheios", APP_JS,
                         "a contagem antiga (completos com o rótulo de montados) voltou")

    def test_a_nota_diz_os_completos(self):
        self.assertIn("completos", self._cartao())


class TestOPayloadTrazOMontado(Base):
    """O cartão só pode contar montados se o `decks_index` os disser — e diz,
    desde 2026-09-24. Fixa-se aqui para o cartão não ficar a ler um campo que
    um dia desapareça."""

    def test_nenhum_montado(self):
        self.cfg_decks({"montados": []})
        con = self.catalogo()
        idx = self.decks.decks_index(con)
        self.assertEqual(len(idx), 2)
        self.assertEqual([d["montado"] for d in idx], [False, False])

    def test_um_montado(self):
        self.cfg_decks({"montados": ["azir"]})
        con = self.catalogo()
        m = {d["slug"]: d["montado"] for d in self.decks.decks_index(con)}
        self.assertEqual(m, {"azir": True, "ornn": False})


if __name__ == "__main__":
    unittest.main()

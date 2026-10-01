"""O PORTÃO DO MERGE (2026-09-29): o merge lê o PLACAR, e a falta dele é
VERMELHO.

O caso que isto existe para não repetir: nesse dia o harness disse «exit code
0» numa corrida cujo placar dizia «1 a falhar». A regra «lê o placar» era
falada; passou a ser mecânica. Ver o `CLAUDE.md`.

Os testes correm contra RAÍZES DE MENTIRA, montadas em pastas temporárias com
a forma de um repositório (um `riftvault/`, um `tests/`, um
`riftvault_config.json`). Nenhum corre a suite a sério — seria uma suite
dentro de uma suite.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from tools import placar as pl  # noqa: E402


def raiz_de_mentira(base: Path) -> Path:
    """Um repositório com a forma do nosso, mas de brincar."""
    (base / "riftvault" / "web").mkdir(parents=True)
    (base / "tests").mkdir()
    (base / "riftvault" / "a.py").write_text("x = 1\n", encoding="utf-8")
    (base / "riftvault" / "schema.sql").write_text("-- nada\n", encoding="utf-8")
    (base / "riftvault" / "web" / "app.js").write_text("// nada\n", encoding="utf-8")
    (base / "riftvault_config.json").write_text("{}", encoding="utf-8")
    (base / "tests" / "test_um.py").write_text("", encoding="utf-8")
    (base / "tests" / "test_dois.py").write_text("", encoding="utf-8")
    return base


def placar_verde(raiz: Path, **troca) -> dict:
    # As DUAS impressoes iguais e a bandeira em baixo sao parte de um placar
    # valido desde 01/10/2026: um placar sem elas nao diz se o codigo se
    # manteve o mesmo do principio ao fim da corrida, e vale vermelho (ha
    # teste proprio para isso em `TestMexeramAMeioDaCorrida`).
    digital = pl.impressao_digital(raiz)
    p = {"quando": "2026-09-29T23:00:00+00:00", "raiz": str(raiz),
         "head": "0" * 40, "impressao_digital": digital,
         "impressao_no_inicio": digital, "mexeram_a_meio": False,
         "ficheiros": len(pl.ficheiros_de_teste(raiz)), "testes": 42,
         "a_falhar": 0, "maus": []}
    p.update(troca)
    return p


class TestImpressaoDigital(unittest.TestCase):
    """O placar tem de saber QUE CÓDIGO mediu."""

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.raiz = raiz_de_mentira(Path(self.tmp.name))
        self.addCleanup(self.tmp.cleanup)

    def test_e_estavel_entre_corridas(self):
        self.assertEqual(pl.impressao_digital(self.raiz),
                         pl.impressao_digital(self.raiz))

    def test_muda_com_o_pacote(self):
        antes = pl.impressao_digital(self.raiz)
        (self.raiz / "riftvault" / "a.py").write_text("x = 2\n", encoding="utf-8")
        self.assertNotEqual(antes, pl.impressao_digital(self.raiz))

    def test_muda_com_os_testes(self):
        antes = pl.impressao_digital(self.raiz)
        (self.raiz / "tests" / "test_um.py").write_text("# novo\n", encoding="utf-8")
        self.assertNotEqual(antes, pl.impressao_digital(self.raiz))

    def test_muda_com_o_schema_e_com_o_web(self):
        for caminho in ("riftvault/schema.sql", "riftvault/web/app.js"):
            antes = pl.impressao_digital(self.raiz)
            (self.raiz / caminho).write_text("-- outro\n", encoding="utf-8")
            self.assertNotEqual(antes, pl.impressao_digital(self.raiz), caminho)

    def test_muda_com_o_config(self):
        """O config NÃO é enfeite: é lá que vivem as regras que os testes medem
        (`master_set.um_de_cada`, `selado.excluidos`, `decks.montados`)."""
        antes = pl.impressao_digital(self.raiz)
        (self.raiz / "riftvault_config.json").write_text(
            '{"multi": {"aberto": true}}', encoding="utf-8")
        self.assertNotEqual(antes, pl.impressao_digital(self.raiz))

    def test_nao_muda_com_os_dados(self):
        """Um `+` num tile não pode invalidar um placar verde: os testes correm
        contra cópias, e o `data/` não entra na impressão digital."""
        antes = pl.impressao_digital(self.raiz)
        (self.raiz / "data").mkdir()
        (self.raiz / "data" / "vault.db").write_bytes(b"x" * 100)
        self.assertEqual(antes, pl.impressao_digital(self.raiz))

    def test_um_ficheiro_novo_no_pacote_muda(self):
        antes = pl.impressao_digital(self.raiz)
        (self.raiz / "riftvault" / "b.py").write_text("y = 1\n", encoding="utf-8")
        self.assertNotEqual(antes, pl.impressao_digital(self.raiz))


class TestOPlacarAusenteEVermelho(unittest.TestCase):

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.raiz = raiz_de_mentira(Path(self.tmp.name))
        self.addCleanup(self.tmp.cleanup)

    def test_sem_placar(self):
        ok, razao = pl.verde(self.raiz)
        self.assertFalse(ok)
        self.assertIn("não há placar", razao)
        self.assertIn("VERMELHO", razao)

    def test_placar_ilegivel(self):
        (self.raiz / pl.PLACAR).write_text("{isto não é json", encoding="utf-8")
        ok, razao = pl.verde(self.raiz)
        self.assertFalse(ok)
        self.assertIn("não há placar", razao)

    def test_placar_a_meio_falta_um_campo(self):
        """Uma corrida que morreu a meio deixa um placar incompleto. Ler-lhe
        metade dos campos é pior do que não ter nenhum."""
        p = placar_verde(self.raiz)
        del p["a_falhar"]
        (self.raiz / pl.PLACAR).write_text(json.dumps(p), encoding="utf-8")
        self.assertFalse(pl.verde(self.raiz)[0])

    def test_placar_com_contagem_que_nao_e_numero(self):
        p = placar_verde(self.raiz, a_falhar="nenhum")
        (self.raiz / pl.PLACAR).write_text(json.dumps(p), encoding="utf-8")
        self.assertFalse(pl.verde(self.raiz)[0])

    def test_placar_vazio(self):
        (self.raiz / pl.PLACAR).write_text("", encoding="utf-8")
        self.assertFalse(pl.verde(self.raiz)[0])


class TestAsCincoManeirasDeEstarVermelho(unittest.TestCase):

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.raiz = raiz_de_mentira(Path(self.tmp.name))
        self.addCleanup(self.tmp.cleanup)

    def _escrever(self, **troca):
        (self.raiz / pl.PLACAR).write_text(
            json.dumps(placar_verde(self.raiz, **troca)), encoding="utf-8")

    def test_verde_quando_esta_tudo_bem(self):
        self._escrever()
        ok, razao = pl.verde(self.raiz)
        self.assertTrue(ok, razao)
        self.assertIn("VERDE", razao)
        self.assertIn("2 ficheiros", razao)
        self.assertIn("42 testes", razao)

    def test_testes_a_falhar(self):
        self._escrever(a_falhar=1, maus=[{"ficheiro": "test_um.py"}])
        ok, razao = pl.verde(self.raiz)
        self.assertFalse(ok)
        self.assertIn("1 ficheiro(s) a falhar", razao)
        self.assertIn("test_um.py", razao)

    def test_o_codigo_mudou_depois_da_corrida(self):
        """O caso a sério: «corri a suite, depois emendei uma linha»."""
        self._escrever()
        self.assertTrue(pl.verde(self.raiz)[0])
        (self.raiz / "riftvault" / "a.py").write_text("x = 99\n", encoding="utf-8")
        ok, razao = pl.verde(self.raiz)
        self.assertFalse(ok)
        self.assertIn("o código mudou", razao)

    def test_faltam_ficheiros_de_teste(self):
        """Um teste novo por correr, ou uma corrida interrompida."""
        self._escrever()
        (self.raiz / "tests" / "test_tres.py").write_text("", encoding="utf-8")
        # a impressão digital também muda — o que interessa é dar vermelho
        ok, razao = pl.verde(self.raiz)
        self.assertFalse(ok)

    def test_o_placar_mediu_mais_ficheiros_do_que_ha(self):
        self._escrever(ficheiros=9)
        ok, razao = pl.verde(self.raiz)
        self.assertFalse(ok)
        self.assertIn("9 ficheiros", razao)


class TestOPortaoRecusaOMerge(unittest.TestCase):
    """O `merge` não chama o `git` com o placar vermelho — e não há forçar."""

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.raiz = raiz_de_mentira(Path(self.tmp.name))
        self.addCleanup(self.tmp.cleanup)

    def test_merge_com_placar_vermelho_sai_1_e_nao_chama_o_git(self):
        from tools import portao
        chamadas = []
        original = portao._git
        portao._git = lambda *a, **k: chamadas.append(a) or original(*a, **k)
        self.addCleanup(lambda: setattr(portao, "_git", original))
        saida = portao.main(["merge", "um-ramo", "-m", "x",
                             "--raiz", str(self.raiz)])
        self.assertEqual(saida, 1)
        self.assertEqual(chamadas, [], "chamou o git com o placar vermelho")

    def test_verificar_sai_1_sem_placar(self):
        from tools import portao
        self.assertEqual(portao.main(["verificar", "--raiz", str(self.raiz)]), 1)

    def test_verificar_sai_0_com_placar_verde(self):
        from tools import portao
        (self.raiz / pl.PLACAR).write_text(
            json.dumps(placar_verde(self.raiz)), encoding="utf-8")
        self.assertEqual(portao.main(["verificar", "--raiz", str(self.raiz)]), 0)

    def test_nao_ha_bandeira_para_forcar(self):
        """Uma bandeira de forçar é a que se usa às duas da manhã."""
        fonte = (REPO / "tools" / "portao.py").read_text(encoding="utf-8")
        for palavra in ("--forcar", "--force", "--sim-mesmo", "--ignorar-placar"):
            self.assertNotIn(palavra, fonte)


class TestUmFicheiroQueNemCorreEVermelho(unittest.TestCase):
    """Se a saída não tem o `Ran N tests`, é um import partido — e um ficheiro
    que desaparece da contagem é a outra maneira de um vermelho passar."""

    def test_correr_marca_o_que_nao_corre(self):
        with TemporaryDirectory() as tmp:
            raiz = raiz_de_mentira(Path(tmp))
            (raiz / "tests" / "__init__.py").write_text("", encoding="utf-8")
            (raiz / "tests" / "test_um.py").write_text(
                "import unittest\n"
                "class T(unittest.TestCase):\n"
                "    def test_ok(self): pass\n", encoding="utf-8")
            (raiz / "tests" / "test_dois.py").write_text(
                "import modulo_que_nao_existe\n", encoding="utf-8")
            p = pl.correr(raiz, log=lambda *a, **k: None)
            self.assertEqual(p["ficheiros"], 2)
            self.assertEqual(p["a_falhar"], 1)
            self.assertEqual(p["maus"][0]["ficheiro"], "test_dois.py")
            # O `unittest` transforma um import partido num teste sintético
            # que falha, e por isso imprime «Ran 1 test» na mesma. O que
            # apanha o ficheiro é o CÓDIGO DE SAÍDA, não a contagem — e é
            # por isso que o placar exige as duas coisas.
            self.assertEqual(p["testes"], 2)

    def test_sem_Ran_nenhum_conta_como_nao_correu(self):
        """O outro caso: o processo morre sem o `unittest` chegar a imprimir
        nada (um `SyntaxError` no `tests/__init__.py`, um crash). Aí não há
        contagem nenhuma, e um ficheiro que desaparece da contagem é a outra
        maneira de um vermelho passar despercebido."""
        with TemporaryDirectory() as tmp:
            raiz = raiz_de_mentira(Path(tmp))
            (raiz / "tests" / "__init__.py").write_text(
                "import sys; sys.exit(3)\n", encoding="utf-8")
            p = pl.correr(raiz, log=lambda *a, **k: None)
            self.assertEqual(p["a_falhar"], 2)
            self.assertEqual(p["testes"], 0)
            self.assertTrue(all("não correu" in m["razao"] for m in p["maus"]),
                            [m["razao"] for m in p["maus"]])

    def test_correr_grava_a_impressao_digital_do_momento(self):
        with TemporaryDirectory() as tmp:
            raiz = raiz_de_mentira(Path(tmp))
            (raiz / "tests" / "__init__.py").write_text("", encoding="utf-8")
            p = pl.correr(raiz, log=lambda *a, **k: None)
            self.assertEqual(p["impressao_digital"], pl.impressao_digital(raiz))


class TestOPlacarNaoVaiParaOGit(unittest.TestCase):
    """É o resultado de uma corrida NESTA máquina, não conteúdo do projecto.
    Um placar commitado era o verde de outra pessoa a autorizar o meu merge."""

    def test_esta_no_gitignore(self):
        ig = (REPO / ".gitignore").read_text(encoding="utf-8")
        self.assertIn(pl.PLACAR, ig)


if __name__ == "__main__":
    unittest.main(verbosity=2)


class TestMexeramAMeioDaCorrida(unittest.TestCase):
    """Uma alteração DURANTE a corrida não pode sair verde (2026-10-01).

    O furo era este: a impressão digital tirava-se depois do ciclo, por isso
    ficava coerente com o disco e a `verde()` não tinha como saber que os
    primeiros ficheiros mediram outros bytes. Encontrado a 01/10 pela ordem das
    fechaduras, a quem aconteceu a sério.
    """

    def setUp(self):
        self.raiz = Path(tempfile.mkdtemp(prefix="placar-meio-"))
        self.addCleanup(shutil.rmtree, self.raiz, ignore_errors=True)
        (self.raiz / "riftvault").mkdir()
        (self.raiz / "riftvault" / "web").mkdir()
        (self.raiz / "tests").mkdir()
        (self.raiz / "riftvault_config.json").write_text("{}", encoding="utf-8")
        (self.raiz / "riftvault" / "coisa.py").write_text("A = 1\n", encoding="utf-8")
        (self.raiz / "tests" / "test_um.py").write_text("x\n", encoding="utf-8")
        (self.raiz / "tests" / "test_dois.py").write_text("x\n", encoding="utf-8")

    def _placar_verde(self, **extra):
        p = {"quando": "2026-10-01T00:00:00+00:00", "raiz": str(self.raiz),
             "head": "0" * 40,
             "impressao_digital": pl.impressao_digital(self.raiz),
             "impressao_no_inicio": pl.impressao_digital(self.raiz),
             "mexeram_a_meio": False,
             "ficheiros": 2, "testes": 10, "a_falhar": 0, "maus": []}
        p.update(extra)
        pl.gravar(self.raiz, p)
        return p

    def test_o_caso_bom_continua_verde(self):
        self._placar_verde()
        ok, razao = pl.verde(self.raiz)
        self.assertTrue(ok, razao)

    def test_as_duas_impressoes_diferentes_e_vermelho(self):
        self._placar_verde(impressao_no_inicio="a" * 64, mexeram_a_meio=True)
        ok, razao = pl.verde(self.raiz)
        self.assertFalse(ok)
        self.assertIn("A MEIO", razao)

    def test_a_bandeira_sozinha_chega_para_vermelho(self):
        # Quem escrever o placar à mão e puser só a bandeira não passa.
        self._placar_verde(mexeram_a_meio=True)
        ok, razao = pl.verde(self.raiz)
        self.assertFalse(ok)
        self.assertIn("A MEIO", razao)

    def test_um_placar_antigo_sem_o_campo_e_vermelho(self):
        p = self._placar_verde()
        del p["impressao_no_inicio"]
        p.pop("mexeram_a_meio", None)
        pl.gravar(self.raiz, p)
        ok, razao = pl.verde(self.raiz)
        self.assertFalse(ok)
        self.assertIn("antes de 01/10/2026", razao)

    def test_a_correr_apanha_uma_emenda_feita_a_meio(self):
        """O ciclo a sério, com um ficheiro a mudar entre dois testes."""
        chamadas = []
        alvo = self.raiz / "riftvault" / "coisa.py"

        class Fingida:
            returncode = 0
            stdout = "Ran 3 tests in 0.1s\n\nOK\n"
            stderr = ""

        def falso_run(*a, **k):
            chamadas.append(1)
            if len(chamadas) == 1:          # entre o primeiro e o segundo
                alvo.write_text("A = 2\n", encoding="utf-8")
            return Fingida()

        with mock.patch.object(pl.subprocess, "run", falso_run):
            p = pl.correr(self.raiz, log=lambda *a, **k: None)
        self.assertEqual(p["a_falhar"], 0, "a suite em si passou")
        self.assertTrue(p["mexeram_a_meio"], "e mesmo assim o placar não vale")
        self.assertNotEqual(p["impressao_no_inicio"], p["impressao_digital"])
        pl.gravar(self.raiz, p)
        ok, razao = pl.verde(self.raiz)
        self.assertFalse(ok, "verde a descrever código que nunca correu inteiro")
        self.assertIn("A MEIO", razao)

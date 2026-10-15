"""Nenhum teste escreve num caminho temporário PARTILHADO entre processos.

2026-10-15: com o portão a 16 trabalhadores, o `test_voltar_1` e o
`test_runas_alt_fora` passaram a só passar sozinhos. A causa era um config com
NOME FIXO no `%TEMP%` (`riftvault-voltar-1.json`), escrito e reescrito por dois
processos ao mesmo tempo — e a mesma forma estava em mais quatro ficheiros, mais
o `riftvault-nao-existe.json` que mais de quarenta partilhavam. Desde então todo
o temporário de nome escolhido pelo teste vive na pasta do processo
(`fixture.ficheiro_temporario`, `fixture.SEM_CONFIG`).

Este ficheiro guarda isso: lê o código dos testes e recusa um caminho montado
a partir do `gettempdir()` (que é o mesmo para todos os processos), e prova que
a pasta do fixture é mesmo de um processo só.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests import fixture  # noqa: E402

TESTS = Path(__file__).resolve().parent

#: Um caminho com nome escolhido pelo teste, por cima da pasta temporária
#: COMUM. (Escrito aos bocados para este ficheiro não se apanhar a si mesmo.)
PARTILHADO = re.compile(r"gettemp" + r"dir\(\)")


class TestNenhumCaminhoPartilhado(unittest.TestCase):

    def test_nenhum_teste_monta_um_caminho_no_tmp_comum(self):
        culpados = []
        for f in sorted(TESTS.glob("*.py")):
            if f.name == Path(__file__).name:
                continue          # este compara com a pasta comum de propósito
            for n, linha in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                if PARTILHADO.search(linha):
                    culpados.append(f"{f.name}:{n}: {linha.strip()}")
        self.assertEqual(
            culpados, [],
            "caminho no %TEMP% comum — dois processos escrevem-no ao mesmo tempo; "
            "usa `fixture.ficheiro_temporario(nome)` ou `fixture.SEM_CONFIG`")

    def test_a_prova_pela_negativa_o_padrao_apanha_a_forma_antiga(self):
        # Um padrão que nunca apanha nada vale zero.
        antiga = 'CONFIG = Path(tempfile.' + 'gettempdir()) / "riftvault-voltar-1.json"'
        self.assertTrue(PARTILHADO.search(antiga))


class TestAPastaEDeUmProcessoSo(unittest.TestCase):

    def test_os_caminhos_vivem_na_pasta_do_processo(self):
        pasta = fixture.pasta_do_processo()
        self.assertTrue(pasta.is_dir())
        self.assertEqual(fixture.ficheiro_temporario("x.json").parent, pasta)
        self.assertEqual(Path(fixture.SEM_CONFIG).parent, pasta)
        # …e não é a pasta temporária comum.
        self.assertNotEqual(pasta, Path(tempfile.gettempdir()))

    def test_o_config_que_nao_existe_nao_existe(self):
        self.assertFalse(Path(fixture.SEM_CONFIG).exists())

    def test_outro_processo_tem_outra_pasta_e_ela_desaparece_no_fim(self):
        prog = ("import sys; sys.path.insert(0, sys.argv[1]); "
                "from tests import fixture; "
                "print(fixture.pasta_do_processo())")
        r = subprocess.run([sys.executable, "-c", prog,
                            str(TESTS.parent)],
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        outra = Path(r.stdout.strip())
        self.assertNotEqual(outra, fixture.pasta_do_processo())
        self.assertFalse(outra.exists(),
                         "a pasta do processo tem de se apagar à saída (atexit)")


if __name__ == "__main__":
    unittest.main()

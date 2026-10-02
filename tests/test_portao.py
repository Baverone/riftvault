"""O PORTÃO DO MERGE (2026-09-29): o merge lê o PLACAR, e a falta dele é
VERMELHO.

O caso que isto existe para não repetir: nesse dia o harness disse «exit code
0» numa corrida cujo placar dizia «1 a falhar». A regra «lê o placar» era
falada; passou a ser mecânica. Ver o `CLAUDE.md`.

Os testes correm contra RAÍZES DE MENTIRA, montadas em pastas temporárias com
a forma de um repositório (um `riftvault/`, um `tests/`, um
`riftvault_config.json`). Nenhum corre a suite a sério — seria uma suite
dentro de uma suite.

DESDE 2026-09-30 A SUITE CORRE EM PARALELO e cada vermelho repete-se SOZINHO
antes de contar. Uma avaria nessa regra não dá erro — dá VERDE —, e por isso as
três perguntas ficam aqui fixadas, cada uma com a PROVA PELA NEGATIVA a seguir:
uma colisão conta verde e diz-se qual; um vermelho a sério continua a travar o
portão; e as cinco maneiras de estar vermelho valem todas na mesma.
"""

from __future__ import annotations

import json
import os
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


# ---------------------------------------------------------------------------
# A suite em PARALELO, e a repetição SOZINHO (2026-09-30)
# ---------------------------------------------------------------------------

class _ambiente:
    """As duas variáveis do modo, POSTAS e não herdadas, e repostas no fim.

    As duas chaves são sempre limpas à entrada: um teste que queira o modo
    paralelo não pode depender de quem o chamou não ter o `RIFTVAULT_SUITE_SERIE`
    no ambiente.
    """

    CHAVES = (pl.ENV_SERIE, pl.ENV_TRABALHADORES)

    def __init__(self, valores: dict[str, str] | None = None):
        self.valores = valores or {}

    def __enter__(self):
        self.antes = {k: os.environ.get(k) for k in self.CHAVES}
        for k in self.CHAVES:
            os.environ.pop(k, None)
        os.environ.update(self.valores)
        return self

    def __exit__(self, *_):
        for k in self.CHAVES:
            os.environ.pop(k, None)
        for k, v in self.antes.items():
            if v is not None:
                os.environ[k] = v
        return False


def _respostas(plano: dict[str, list[bool]]):
    """Substitui o «correr um ficheiro»: `plano[nome]` é a lista de respostas,
    por ordem das corridas (o resto passa). Não se simula uma colisão a sério —
    ela é, por definição, intermitente, e um teste que depende de temporização
    é um teste que um dia dá vermelho falso. O que se mede é a REGRA.

    A contagem de testes SOBE a cada corrida, de propósito: é assim que se
    prova qual delas é que o placar guarda.
    """
    contagem: dict[str, int] = {}

    def fingir(raiz, f):
        i = contagem.get(f.name, 0)
        contagem[f.name] = i + 1
        seq = plano.get(f.name, [True])
        return {"ficheiro": f.name, "testes": 10 + i, "segundos": 0.1,
                "ok": seq[min(i, len(seq) - 1)],
                "razao": "falhou", "cauda": "cauda de mentira"}

    return fingir, contagem


class TestAsuiteEmParalelo(unittest.TestCase):
    """O placar diz TRÊS números: à primeira, só sozinhos, a sério."""

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.raiz = raiz_de_mentira(Path(self.tmp.name))
        (self.raiz / "tests" / "test_tres.py").write_text("", encoding="utf-8")
        self.addCleanup(self.tmp.cleanup)
        antigo = pl._correr_um
        self.addCleanup(lambda: setattr(pl, "_correr_um", antigo))

    def _correr(self, plano):
        pl._correr_um, self.contagem = _respostas(plano)
        # O MODO TEM DE SER POSTO AQUI, e não herdado. Quem corre a suite pode
        # ter o `RIFTVAULT_SUITE_SERIE` no ambiente (é o que o cronómetro faz
        # para medir o modo série), e aí estes testes mediam o modo errado — foi
        # exactamente assim que este ficheiro deu vermelho na primeira medição.
        with _ambiente({pl.ENV_TRABALHADORES: "4"}):
            return pl.correr(self.raiz, log=lambda *a, **k: None)

    def test_tudo_verde_a_primeira_nao_repete_nada(self):
        """É daqui que vem a rapidez: só os vermelhos pagam a lentidão."""
        p = self._correr({})
        self.assertEqual(p["verdes_a_primeira"], 3)
        self.assertEqual(p["colidiram"], [])
        self.assertEqual(p["a_falhar"], 0)
        self.assertEqual(set(self.contagem.values()), {1})

    def test_quem_passa_a_segunda_era_colisao_e_conta_verde(self):
        p = self._correr({"test_dois.py": [False, True]})
        self.assertEqual(p["a_falhar"], 0, "uma colisão não é um vermelho")
        self.assertEqual(p["verdes_a_primeira"], 2)
        self.assertEqual([c["ficheiro"] for c in p["colidiram"]],
                         ["test_dois.py"])
        self.assertEqual(self.contagem["test_dois.py"], 2, "repetiu-se sozinho")
        pl.gravar(self.raiz, p)
        ok, razao = pl.verde(self.raiz)
        self.assertTrue(ok, razao)
        self.assertIn("test_dois.py", razao,
                      "o verde tem de dizer QUAIS colidiram — um verde que o "
                      "esconde é um verde em que se confia de menos")

    def test_a_prova_pela_negativa_da_colisao(self):
        """Sem a segunda volta isto era um vermelho, e o mesmo ficheiro a
        falhar SEMPRE tem de continuar a dar vermelho."""
        self.assertEqual(self._correr({"test_dois.py": [False, True]})["a_falhar"], 0)
        self.assertEqual(self._correr({"test_dois.py": [False, False]})["a_falhar"], 1)

    def test_quem_falha_as_duas_e_vermelho_a_serio(self):
        p = self._correr({"test_tres.py": [False, False]})
        self.assertEqual(p["a_falhar"], 1)
        self.assertEqual([m["ficheiro"] for m in p["maus"]], ["test_tres.py"])
        self.assertEqual(p["colidiram"], [])
        pl.gravar(self.raiz, p)
        ok, razao = pl.verde(self.raiz)
        self.assertFalse(ok)
        self.assertIn("test_tres.py", razao)

    def test_uma_colisao_nao_tapa_um_vermelho(self):
        p = self._correr({"test_um.py": [False, True],
                          "test_tres.py": [False, False]})
        self.assertEqual(p["verdes_a_primeira"], 1)
        self.assertEqual(len(p["colidiram"]), 1)
        self.assertEqual(p["a_falhar"], 1)
        pl.gravar(self.raiz, p)
        self.assertFalse(pl.verde(self.raiz)[0],
                         "um vermelho manda, haja ou não colisões ao lado")

    def test_a_contagem_que_vale_e_a_da_corrida_sozinho(self):
        """Quem repetiu conta pela SEGUNDA: é a que mede o ficheiro sem ninguém
        ao lado, e é a resposta em que se confia."""
        p = self._correr({"test_dois.py": [False, True]})
        self.assertEqual(p["testes"], 10 + 10 + 11)

    def test_o_modo_vai_no_placar(self):
        p = self._correr({})
        self.assertEqual(p["modo"], "paralelo")
        self.assertEqual(p["trabalhadores"], 4)


class TestORegistoDasColisoes(unittest.TestCase):
    """Uma linha por ficheiro que só passou sozinho. É MEMÓRIA e mais nada."""

    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.raiz = raiz_de_mentira(Path(self.tmp.name))
        self.addCleanup(self.tmp.cleanup)
        antigo = pl._correr_um
        self.addCleanup(lambda: setattr(pl, "_correr_um", antigo))

    def _correr(self, plano):
        pl._correr_um, _ = _respostas(plano)
        return pl.correr(self.raiz, log=lambda *a, **k: None)

    def test_uma_linha_por_colisao_com_a_data(self):
        p = self._correr({"test_dois.py": [False, True]})
        reg = self.raiz / pl.COLISOES
        self.assertTrue(reg.is_file())
        linhas = reg.read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(linhas), 1)
        self.assertIn("test_dois.py", linhas[0])
        self.assertIn(p["quando"], linhas[0], "com a data da corrida")

    def test_sem_colisoes_nao_escreve_nada(self):
        self._correr({})
        self.assertFalse((self.raiz / pl.COLISOES).exists())

    def test_acumula_e_nao_muda_o_veredicto(self):
        """Um ficheiro já registado repete-se e conta verde pelo MESMO caminho:
        não é promovido nem desculpado. É o contrário de uma lista à mão."""
        self._correr({"test_dois.py": [False, True]})
        p2 = self._correr({"test_dois.py": [False, True]})
        texto = (self.raiz / pl.COLISOES).read_text(encoding="utf-8")
        self.assertEqual(texto.strip().count("test_dois.py"), 2)
        self.assertEqual(p2["a_falhar"], 0)
        self.assertEqual(len(p2["colidiram"]), 1)

    def test_um_registo_que_nao_se_escreve_nao_estraga_a_suite(self):
        """O registo é conveniência; nunca é motivo para a suite falhar."""
        (self.raiz / "data").write_text("sou um ficheiro, não uma pasta",
                                        encoding="utf-8")
        p = self._correr({"test_dois.py": [False, True]})
        self.assertEqual(p["a_falhar"], 0)
        self.assertEqual(len(p["colidiram"]), 1)

    def test_esta_no_gitignore(self):
        ig = (REPO / ".gitignore").read_text(encoding="utf-8")
        self.assertIn(pl.COLISOES, ig,
                      "é o resultado de uma corrida NESTA máquina, como o placar")


class TestForcarOModoSerie(unittest.TestCase):
    """Tem de haver forma de correr um de cada vez, para depurar."""

    def _com(self, **env):
        with _ambiente(env):
            return pl.trabalhadores()

    def test_a_variavel_poe_a_um(self):
        self.assertEqual(self._com(**{pl.ENV_SERIE: "1"}), 1)

    def test_zero_ou_vazio_nao_liga_o_modo_serie(self):
        self.assertGreater(self._com(**{pl.ENV_SERIE: "0"}), 1)
        self.assertGreater(self._com(**{pl.ENV_SERIE: ""}), 1)

    def test_da_para_escolher_o_numero(self):
        self.assertEqual(self._com(**{pl.ENV_TRABALHADORES: "3"}), 3)

    def test_um_numero_mal_escrito_nao_rebenta_a_suite(self):
        self.assertGreater(self._com(**{pl.ENV_TRABALHADORES: "muitos"}), 1)

    def test_o_tecto_manda_sobre_os_nucleos(self):
        """NÃO é o número de núcleos (a máquina dele tem 32): cada ficheiro é
        um processo que copia bases e as abre, e a partir de certo ponto o que
        limita é o disco — apertar mais só faz subir as colisões."""
        self.assertLessEqual(self._com(), pl.TECTO_TRABALHADORES)
        self.assertGreaterEqual(pl.TECTO_TRABALHADORES, 2)

    def test_sao_variaveis_de_ambiente_e_nao_chaves_do_config(self):
        """A razão é a do `RIFTVAULT_ENSAIO`: uma chave num ficheiro commitado
        está a um merge de distância de ficar ligada sem ninguém decidir."""
        cfg = (REPO / "riftvault_config.json").read_text(encoding="utf-8")
        self.assertNotIn("suite_serie", cfg)
        self.assertNotIn("trabalhadores", cfg)

    def test_corre_mesmo_um_de_cada_vez(self):
        with TemporaryDirectory() as tmp:
            raiz = raiz_de_mentira(Path(tmp))
            antigo = pl._correr_um
            try:
                pl._correr_um, _ = _respostas({})
                with _ambiente({pl.ENV_SERIE: "1"}):
                    p = pl.correr(raiz, log=lambda *a, **k: None)
            finally:
                pl._correr_um = antigo
        self.assertEqual(p["trabalhadores"], 1)
        self.assertEqual(p["modo"], "série")
        self.assertEqual(p["a_falhar"], 0)


class TestNaoHaListaDeFicheirosMaus(unittest.TestCase):
    """Uma lista escrita à mão envelhece e dá VERMELHOS FALSOS — e um vermelho
    falso é a pior coisa que uma suite faz, porque ensina a ignorá-la."""

    def test_o_placar_nao_tem_nomes_de_ficheiros_escritos(self):
        fonte = (REPO / "tools" / "placar.py").read_text(encoding="utf-8")
        # os nomes que aparecem na docstring são exemplos DO PORQUÊ da regra de
        # um processo por ficheiro; o que não pode haver é uma lista a decidir
        for suspeito in ("MAUS = ", "COLIDEM = ", "SOZINHOS = ", "EXCEPCOES = "):
            self.assertNotIn(suspeito, fonte)

    def test_quem_decide_e_a_corrida(self):
        """Prova: o mesmo ficheiro dá verde ou vermelho consoante a SEGUNDA
        corrida, e nada mais — não há nome nenhum a pesar na decisão."""
        with TemporaryDirectory() as tmp:
            raiz = raiz_de_mentira(Path(tmp))
            antigo = pl._correr_um
            self.addCleanup(lambda: setattr(pl, "_correr_um", antigo))
            for segunda, esperado in ((True, 0), (False, 1)):
                pl._correr_um, _ = _respostas({"test_um.py": [False, segunda]})
                p = pl.correr(raiz, log=lambda *a, **k: None)
                self.assertEqual(p["a_falhar"], esperado)


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

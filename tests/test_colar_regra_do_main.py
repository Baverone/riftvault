"""O RESUMO DO `colar` E A REGRA DO MAIN (2026-10-05).

O que aconteceu: o André mandou colar o deck do Kennen e o `riftvault colar`
escreveu `Main deck  19 cartas  39 cópias   regra 40`. Eu li aquilo e disse-lhe
que lhe faltava uma carta. **NÃO FALTAVA** — a regra do main CONTA o Champion
(`deck_rules.main_includes_champion`, inferido das listas dele: 39 no MainDeck
+ 1 Champion = 40), e o `riftvault deck kennen-heart-of-the-tempest` diz,
correctamente, `main 40/40 ok`. Duas portas a dizer coisas diferentes sobre a
mesma lista, e a que ele lê primeiro era a que enganava.

A causa não era a regra: era a aritmética deixada para a cabeça de quem lê. O
comentário do `colar.por_papel` dizia-o por extenso — «é o que ele confere de
relance ("39 no main + 1 Champion = 40")». Quem lê engana-se.

O que estes testes fixam:

  * `TestASomaVemDoPayload` — o número que se compara com a regra sai do
    `colar.prever`, com a regra ligada e desligada, e o Champion não é
    presumido 1.
  * `TestOResumoDoCLI` — a linha do Main deck mostra esse número e diz de onde
    vem, sem esconder o 39.
  * `TestACaixaDoSite` — a tabela da secção Decks LÊ o payload em vez de somar
    por sua conta.
  * `TestARegraNaoMudou` — esta ordem é sobre o resumo mentir, não sobre a
    regra. O `main_includes_champion` foi INFERIDO e não está validado contra
    as regras oficiais (CLAUDE.md): mudá-lo é outra conversa e é dele.

Correm contra pastas temporárias e um catálogo de brincar: nunca contra o
`data/` a sério. Os números da lista REAL do Kennen medem-se com
`py -m riftvault colar`, na consola.
"""

from __future__ import annotations

import importlib
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

#: Um caminho que não existe: o `config` cai nos `DEFAULTS`, que é onde vive a
#: regra que isto mede. Em CADA `setUp`, e não só aqui — um teste que escreva o
#: seu config LIMPA a variável no fim, e sem ela os seguintes liam o
#: `riftvault_config.json` A SÉRIO (ver o `SEM_CONFIG` do `test_colar.py`).
SEM_CONFIG = str(Path(tempfile.gettempdir()) / "riftvault-nao-existe.json")

from tests.fixture import REPO, Vault  # noqa: E402

#: A lista do Kennen, pelas palavras dela: 39 no MainDeck e 1 Champion. É a
#: forma da lista que ele colou a 2026-10-05.
KENNEN = """Legend:
1 Kennen, Heart of the Tempest

Champion:
1 Kennen, Storm of Shuriken

MainDeck:
3 Lightning Rush
3 Rhasa the Sunderer
3 Seal of Discord
3 Shadow Order Disciple
3 Tail-Cloaked Matriarch
3 Tornado Warrior
3 Traveling Merchant
2 Ezreal, Prodigy
2 Fizz, Trickster
2 Last Rites
2 Star-Crossed
2 Tideturner
2 Up from the Deep
1 Existential Dread
1 Flash
1 Gust
1 Ride the Wind
1 Salvage
1 Switcheroo

Battlefields:
1 Minefield
1 Shadow Temple
1 Zaun Warrens

Rune Pool:
9 Chaos Rune
3 Order Rune
"""


class Base(unittest.TestCase):
    def setUp(self):
        os.environ["RIFTVAULT_CONFIG"] = SEM_CONFIG
        self.addCleanup(lambda: os.environ.pop("RIFTVAULT_CONFIG", None))
        self.v = Vault()
        self.addCleanup(self.v.close)

    def regras(self, **deck_rules):
        """Um config temporário com o bloco `deck_rules` escrito por extenso.

        É a única maneira de medir a regra desligada: o `decks.rules()` lê o
        config, e um monkey-patch ao `DEFAULT_RULES` não sobrevive ao
        `importlib.reload(config)` que o `Vault` faz (fixture.py:80).

        O `config.CONFIG_PATH` é uma constante de MÓDULO lida na importação
        (config.py:60), por isso não chega pôr a variável de ambiente — é
        preciso reimportar, como o `Vault` faz. O nome do ficheiro leva o PID
        (a suite corre em paralelo desde 2026-10-02).
        """
        caminho = (Path(tempfile.gettempdir())
                   / f"riftvault-regra-main-{os.getpid()}.json")
        caminho.write_text(json.dumps({"deck_rules": deck_rules}), encoding="utf-8")
        os.environ["RIFTVAULT_CONFIG"] = str(caminho)
        from riftvault import config
        importlib.reload(config)
        config.load.cache_clear()
        self.addCleanup(caminho.unlink, missing_ok=True)
        return caminho

    def catalogo(self, texto=KENNEN):
        """Um catálogo com as cartas desta lista, uma impressão cada."""
        from riftvault import decks
        con = self.v.connect()
        tipo = {"legend": "Legend", "champion": "Unit", "main": "Unit",
                "battlefields": "Battlefield", "runes": "Rune", "sideboard": "Unit"}
        vistos = set()
        i = 0
        for role, _, nome in decks.parse_texto(texto)["lines"]:
            if nome.strip().casefold() in vistos:
                continue
            vistos.add(nome.strip().casefold())
            i += 1
            self.v.add_printing(con, f"tst-{i:03d}-100", "TST", i, nome,
                                card_type=tipo[role])
        self.v.rebuild(con)
        return con

    @staticmethod
    def por_papel(p):
        return {b["role"]: b for b in p["por_papel"]}


class TestASomaVemDoPayload(Base):
    """O número que se compara com a regra sai do payload, não da cabeça."""

    def test_39_mais_1_Champion_dao_os_40_da_regra(self):
        """A prova do caso dele: a lista é LEGAL e o payload di-lo."""
        from riftvault import colar
        con = self.catalogo()
        p = colar.prever(con, KENNEN)
        por = self.por_papel(p)
        # As partes, que não se escondem.
        self.assertEqual(por["main"]["copias"], 39, "as cópias da SECÇÃO")
        self.assertEqual(por["champion"]["copias"], 1)
        # E o número que se compara com a regra.
        self.assertEqual(p["main_com_champion"], 40)
        self.assertEqual(p["main_com_champion"], p["regras"]["main"],
                         "a lista do Kennen é legal: 39 + 1 Champion = 40")
        self.assertEqual(p["champion_no_main"], 1)
        con.close()

    def test_com_a_regra_desligada_sao_as_39_do_main_e_mais_nada(self):
        """`main_includes_champion: false` → o Champion não entra na soma."""
        self.regras(main=40, main_includes_champion=False)
        from riftvault import colar
        con = self.catalogo()
        p = colar.prever(con, KENNEN)
        self.assertFalse(p["regras"]["main_includes_champion"])
        self.assertEqual(p["main_com_champion"], 39)
        self.assertEqual(p["champion_no_main"], 0,
                         "nenhuma cópia do Champion entrou na soma")
        self.assertEqual(self.por_papel(p)["main"]["copias"], 39,
                         "as cópias da secção não mudam com a regra")
        con.close()

    def test_o_Champion_nao_e_presumido_UM(self):
        """Duas cópias do Champion somam DUAS.

        O `+1` estava escrito à mão na tabela do site. Com um Champion a 2
        cópias (o `max_copies` é 3, portanto é uma lista possível) aquilo
        escrevia «+1 Champion = 41» com a soma a dar 41 — o texto e o número a
        contradizerem-se.
        """
        from riftvault import colar
        texto = KENNEN.replace("1 Kennen, Storm of Shuriken",
                               "2 Kennen, Storm of Shuriken")
        con = self.catalogo(texto)
        p = colar.prever(con, texto)
        self.assertEqual(self.por_papel(p)["champion"]["copias"], 2)
        self.assertEqual(p["champion_no_main"], 2)
        self.assertEqual(p["main_com_champion"], 41, "39 + 2, não 39 + 1")
        con.close()

    def test_uma_lista_sem_main_nem_Champion_nao_rebenta(self):
        """Só uma Legend: a soma é 0 e não há `KeyError` nenhum."""
        from riftvault import colar
        texto = "Legend:\n1 Kennen, Heart of the Tempest\n"
        con = self.catalogo(texto)
        p = colar.prever(con, texto)
        self.assertEqual(p["main_com_champion"], 0)
        self.assertEqual(p["champion_no_main"], 0)
        con.close()

    def test_um_Champion_sem_MainDeck_conta_o_Champion(self):
        """A soma não depende de haver uma linha `main` no `por_papel`."""
        from riftvault import colar
        texto = ("Legend:\n1 Kennen, Heart of the Tempest\n\n"
                 "Champion:\n1 Kennen, Storm of Shuriken\n")
        con = self.catalogo(texto)
        p = colar.prever(con, texto)
        self.assertEqual(p["champion_no_main"], 1)
        self.assertEqual(p["main_com_champion"], 1)
        con.close()

    def test_a_soma_e_a_MESMA_do_decks_legality(self):
        """A porta que já estava certa e a que estava a enganar têm de bater.

        O `riftvault deck` lê o `decks.legality`, que faz esta soma desde
        sempre; o resumo do colar é que a deixava de fora. Gravar a lista e
        comparar os dois números é a prova de que não há duas aritméticas.
        """
        from riftvault import colar, decks
        con = self.catalogo()
        p = colar.gravar(con, KENNEN)
        L = decks.legality(con, p["deck_id"])
        self.assertEqual(L["main"]["n"], p["main_com_champion"])
        self.assertEqual(L["main"]["alvo"], p["regras"]["main"])
        self.assertTrue(L["main"]["ok"], "e as duas dizem que a lista é legal")
        con.close()

    def test_a_previsao_continua_a_nao_gravar_nada(self):
        """O campo novo não trouxe escrita nenhuma com ele."""
        from riftvault import colar
        con = self.catalogo()
        antes = (sorted(x.name for x in self.v.decks_dir.glob("*")),
                 con.execute("SELECT COUNT(*) c FROM decks").fetchone()["c"])
        colar.prever(con, KENNEN)
        depois = (sorted(x.name for x in self.v.decks_dir.glob("*")),
                  con.execute("SELECT COUNT(*) c FROM decks").fetchone()["c"])
        self.assertEqual(antes, depois)
        con.close()


class TestOResumoDoCLI(Base):
    """A linha que ele lê primeiro."""

    def _resumo(self, texto=KENNEN):
        from riftvault import cli
        con = self.catalogo(texto)
        con.close()

        class Args:
            ficheiro = str(self.v.root / "lista.txt")
            nome = None
            gravar = False
            confirmar = False
            substituir = False

        Path(Args.ficheiro).write_text(texto, encoding="utf-8")
        # O `cmd_colar` escreve o resumo no stdout (que é o que isto mede) e as
        # notas no stderr — cala-se para não sujar a saída da suite.
        saida = io.StringIO()
        with redirect_stdout(saida), redirect_stderr(io.StringIO()):
            self.assertEqual(cli.cmd_colar(Args()), 0)
        return saida.getvalue()

    def test_a_linha_do_main_mostra_o_40_e_nao_o_39_sozinho(self):
        linha = next(l for l in self._resumo().splitlines() if "Main deck" in l)
        self.assertIn("40 cópias", linha,
                      "a coluna mostra o número que se compara com a regra")
        self.assertIn("regra 40", linha)
        # E é esta a frase que enganava: «39 cópias   regra 40».
        self.assertNotRegex(linha, r"39 cópias\s+regra 40")

    def test_a_linha_diz_de_onde_vem_a_soma(self):
        linha = next(l for l in self._resumo().splitlines() if "Main deck" in l)
        self.assertIn("39", linha, "o 39 não se esconde — ele quer as duas partes")
        self.assertIn("Champion", linha, "e diz que o que falta ali é o Champion")

    def test_o_numero_do_Champion_sai_do_payload(self):
        """Com 2 cópias do Champion a linha diz «+ 2 Champion», não «+ 1»."""
        texto = KENNEN.replace("1 Kennen, Storm of Shuriken",
                               "2 Kennen, Storm of Shuriken")
        linha = next(l for l in self._resumo(texto).splitlines() if "Main deck" in l)
        self.assertIn("41 cópias", linha)
        self.assertIn("2 Champion", linha)

    def test_a_linha_do_Champion_fica_como_estava(self):
        linha = next(l for l in self._resumo().splitlines() if "Champion" in l
                     and "Main deck" not in l)
        self.assertRegex(linha, r"Champion\s+1 cartas\s+1 cópias")

    def test_as_outras_secoes_nao_levam_soma_nenhuma(self):
        resumo = self._resumo()
        for secao, copias in (("Battlefields", "3"), ("Runas", "12")):
            linha = next(l for l in resumo.splitlines() if secao in l)
            self.assertIn(f"{copias} cópias   regra {copias}", linha,
                          f"a linha de {secao} não muda")
        self.assertNotIn("Champion)", resumo.split("Main deck")[0],
                         "e a soma só aparece na linha do main")

    def test_com_a_regra_desligada_a_linha_volta_a_dizer_39(self):
        self.regras(main=40, main_includes_champion=False)
        linha = next(l for l in self._resumo().splitlines() if "Main deck" in l)
        self.assertIn("39 cópias", linha)
        self.assertNotIn("Champion", linha,
                         "sem a regra não há soma para explicar")


class TestACaixaDoSite(unittest.TestCase):
    """A tabela da secção Decks LÊ o payload em vez de somar por sua conta.

    A caixa do site **não tinha o defeito visual** do CLI: o `colarPrevHTML`
    já somava o Champion e já mostrava `40/40` na coluna da regra. O que tinha
    era a soma repetida no cliente (uma segunda resposta à mesma pergunta) e o
    `+1` escrito à mão.
    """

    @classmethod
    def setUpClass(cls):
        cls.js = (REPO / "riftvault" / "web" / "app.js").read_text(encoding="utf-8")
        i = cls.js.index("function colarPrevHTML")
        cls.fn = cls.js[i:cls.js.index("\nasync function", i)]

    def test_a_tabela_le_o_campo_do_payload(self):
        self.assertIn("p.main_com_champion", self.fn)
        self.assertIn("p.champion_no_main", self.fn)

    def test_a_coluna_da_regra_compara_com_a_soma(self):
        self.assertRegex(self.fn, r"soma === a")

    def test_o_mais_um_deixou_de_estar_escrito_a_mao(self):
        self.assertNotIn("(+1 Champion", self.fn,
                         "o número do Champion vem do payload")
        self.assertIn("+${noMain} Champion", self.fn)

    def test_as_duas_partes_continuam_no_ecra(self):
        """A célula mostra as cópias da secção E a soma."""
        self.assertIn("${b.copias}", self.fn)
        self.assertIn("= ${soma}", self.fn)

    def test_as_TRES_portas_leem_o_MESMO_payload(self):
        """O `colar.prever` é a porta partilhada, e nenhuma rota o filtra.

        A caixa de colar (`/api/decks/prever`), a leitura por imagem
        (`/api/decks/imagem`, que enche a MESMA caixa) e o `riftvault colar`
        chamam todos o `colar.prever`. As rotas devolvem-no INTEIRO — por isso
        a correcção serve as três de uma vez, e não é presunção.
        """
        srv = (REPO / "riftvault" / "server.py").read_text(encoding="utf-8")
        self.assertIn("jsonify(colar.prever(", srv, "a caixa de colar")
        self.assertIn('"previsao": previsao', srv, "a leitura por imagem")
        cli = (REPO / "riftvault" / "cli.py").read_text(encoding="utf-8")
        self.assertIn("colar.prever(con, texto", cli, "o riftvault colar")
        # E o CLI lê os campos novos em vez de somar por sua conta.
        self.assertIn('r["main_com_champion"]', cli)
        self.assertIn('r["champion_no_main"]', cli)


class TestARegraNaoMudou(unittest.TestCase):
    """Esta ordem é sobre o resumo mentir, não sobre a regra."""

    def test_o_main_includes_champion_continua_ligado_e_anotado(self):
        from riftvault import decks
        self.assertTrue(decks.DEFAULT_RULES["main_includes_champion"])
        self.assertEqual(decks.DEFAULT_RULES["main"], 40)
        fonte = (REPO / "riftvault" / "decks.py").read_text(encoding="utf-8")
        self.assertIn("NÃO validado contra as regras oficiais", fonte,
                      "a ressalva do CLAUDE.md fica escrita onde a regra vive")

    def test_o_colar_nao_tem_regra_propria(self):
        """A regra sai do `decks.rules()`; o `colar` não escreve o número.

        O 40 e o `main_includes_champion` vivem no `decks.DEFAULT_RULES` e no
        `deck_rules` do config. O `colar` só os LÊ — se um dia ele mudar a
        regra, muda num sítio.
        """
        fonte = (REPO / "riftvault" / "colar.py").read_text(encoding="utf-8")
        codigo = "\n".join(l for l in fonte.splitlines()
                           if not l.lstrip().startswith("#"))
        self.assertIn("decks.rules()", fonte)
        self.assertIn('regras.get("main_includes_champion")', fonte)
        for escrito in ('"main": 40', "main = 40", "MAIN = 40"):
            self.assertNotIn(escrito, codigo,
                             "a regra não se escreve aqui, lê-se")


if __name__ == "__main__":
    unittest.main()

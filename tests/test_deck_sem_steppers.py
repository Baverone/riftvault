"""A PÁGINA DO DECK NÃO TEM `+`/`−` (2026-10-01).

Palavras dele: *"no deck nao precisa + e - / ele ja indica se tem ou nao tem"*.

Os únicos `+`/`−` que havia na página de um deck eram os das CÓPIAS PRÓPRIAS,
e saíram. SÃO ACÇÃO DO DECK — e é por isso que saem: ele pediu-os a 2026-09-21
com *"colocas em cada deck o + e - para eu dizer se afinal tenho ou nao"* e
revogou-os hoje com a mesma frase ao contrário. O que ficou no lugar deles é o
NÚMERO, que era a informação que estava entre os dois.

O «JÁ ENCOMENDEI» não é acção do deck e **já não estava aqui**: saiu dos decks
a 2026-09-17 (*"e tiras esta funcionalidade dos decks"*) e vive nas
«Encomendas» e, desde 2026-09-27, nas «Faltas». Fica.

ESTE FICHEIRO DEFENDE AS DUAS METADES, e a segunda é a que importa: um teste
que só dissesse «já não há steppers» passava se alguém os tirasse TODOS, e
isso era pior do que o defeito. Por isso há um teste por VISTA, com o nome da
vista, a exigir que os sete que ficam continuem lá.

E defende que ESCONDER NÃO É APAGAR: o local `proprio:<slug>`, a tabela, o
módulo, a rota `POST /api/proprias/ajustar` e o `riftvault proprias` ficam —
o que mudou é que a página do deck já não os edita.

Lê os ficheiros do `riftvault/web/` e corre a rota contra uma pasta
temporária — nunca o `data/` do André.
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.fixture import REPO  # noqa: E402

WEB = REPO / "riftvault" / "web"
CSS = (WEB / "style.css").read_text(encoding="utf-8")
JS = (WEB / "app.js").read_text(encoding="utf-8")

# Os blocos de `steppers` do `app.js`, por VISTA. A chave é o trecho que os
# identifica no ficheiro; o valor é onde eles vivem e o selector com que o
# `ligar*` lhes apanha os cliques. Os dois do deck saíram a 2026-10-01.
FICAM = {
    'steppers runa': ("Coleção — o contador DELE do bloco «Runas»", "#runas-vista"),
    'steppers foil': ("Coleção — o contador de foil do tile", "#grid"),
    'steppers enc': ("Encomendas — o tile da grelha", "#enc-grid"),
    'steppers fe-enc-bot': ("Faltas — «já encomendei»", "#fe-body"),
}
# Estes três não têm classe própria (`<div class="steppers">` seco), e por isso
# fixam-se pelo atributo que o botão leva.
FICAM_POR_ATRIBUTO = {
    'data-act="-1"': "Coleção — as cópias normais do tile",
    'data-vd="-1"': "Venda — quantas vai vender",
    'data-sl="-1"': "Produto Selado — as unidades",
}


class TestSairamOsDoDeck(unittest.TestCase):
    """O que saiu: os `+`/`−` das cópias próprias, e só eles."""

    def test_nao_ha_steppers_na_pagina_do_deck(self):
        # A `.steppers.proprias` era a ÚNICA classe de steppers desenhada no
        # `#deck-body`; se voltar, volta por aqui.
        self.assertNotIn("steppers proprias", JS)
        self.assertNotIn(".steppers.proprias", CSS)
        self.assertNotIn("prop-n", JS)
        self.assertNotIn("prop-n", CSS)

    def test_nenhum_selector_de_steppers_aponta_ao_deck_body(self):
        # A prova pela negativa do teste de cima: qualquer `querySelectorAll`
        # que vá buscar steppers dentro do `#deck-body`.
        for m in re.finditer(r"querySelectorAll\(\s*'([^']*steppers[^']*)'", JS):
            self.assertNotIn("#deck-body", m.group(1), m.group(1))

    def test_saiu_a_funcao_dos_botoes_e_a_do_clique(self):
        for s in ("function propriasBotoes", "function propriasAjustar",
                  "function ligarProprias", "ligarProprias()",
                  "data-prop-delta", "propFila", "propVoo"):
            self.assertNotIn(s, JS, f"{s} é código morto desde 2026-10-01")

    def test_o_frontend_ja_nao_chama_a_rota(self):
        # A rota fica (ver `TestEsconderNaoEApagar`); o que saiu é o `fetch`.
        # O nome dela ainda aparece no `app.js`, mas só num comentário a dizer
        # por onde é que ele mexe nas próprias agora.
        self.assertNotIn("fetch('api/proprias/ajustar'", JS)
        for m in re.finditer(r"fetch\(\s*'([^']+)'", JS):
            self.assertNotIn("proprias", m.group(1), m.group(1))

    def test_a_copia_propria_que_nao_serve_nao_tem_menos(self):
        corpo = trecho(JS, "function propriaForaTile", "\n}")
        self.assertNotIn("steppers", corpo)
        self.assertNotIn("data-prop-delta", corpo)
        # Mas continua a dizer quantas são e porque não servem.
        self.assertIn("x.qty", corpo)
        self.assertIn("x.motivo", corpo)


class TestFicaramOsOutros(unittest.TestCase):
    """O que FICOU. Um teste por vista — é esta classe que impede que «tirar os
    do deck» se transforme em «tirar os steppers todos»."""

    def test_ficam_os_sete_blocos_de_steppers(self):
        # Sete blocos: 4 com classe própria + 3 secos (Coleção, Venda, Selado).
        self.assertEqual(len(FICAM) + len(FICAM_POR_ATRIBUTO), 7)
        for marca, (vista, _) in FICAM.items():
            self.assertIn(marca, JS, f"os steppers de «{vista}» saíram sem ninguém pedir")
        for marca, vista in FICAM_POR_ATRIBUTO.items():
            self.assertIn(marca, JS, f"os steppers de «{vista}» saíram sem ninguém pedir")

    def test_cada_um_continua_a_ter_quem_lhe_apanhe_o_clique(self):
        for marca, (vista, selector) in FICAM.items():
            self.assertIn(selector, JS, f"«{vista}» ficou sem o {selector}")

    def test_a_colecao_e_que_soma_e_tira_copias(self):
        """É o sítio dessa acção — a razão por que os do deck podiam sair."""
        self.assertIn("api/adjust", JS)
        self.assertIn("#grid", JS)

    def test_o_ja_encomendei_fica_nas_faltas_e_nas_encomendas(self):
        """Não é acção do deck: saiu dos decks a 2026-09-17, não hoje."""
        self.assertIn("data-fe-d", JS)          # Faltas
        self.assertIn("data-enc=", JS)          # Encomendas
        self.assertIn("api/encomenda", JS)

    def test_o_tile_do_deck_continua_sem_os_botoes_da_encomenda(self):
        """O que 2026-09-17 tirou não voltou de arrasto com esta ordem."""
        # O fim do `deckTile` marca-se por um literal que existe antes e depois
        # desta ordem — senão o teste rebentava a LER o código antigo em vez de
        # dizer o que tem a dizer sobre ele.
        corpo = trecho(JS, "function deckTile", "Uma cópia própria que NÃO serve")
        for s in ("data-enc", "data-chegou-ck", "data-fe-d"):
            self.assertNotIn(s, corpo, s)


class TestAInformacaoFicou(unittest.TestCase):
    """«Ele já indica se tem ou não tem» — e continua a indicar, incluindo
    quantas das que tem são próprias do deck."""

    def test_o_numero_das_proprias_ficou_no_lugar_dos_botoes(self):
        self.assertIn("function propriasLinha", JS)
        self.assertIn("${propriasLinha(c)}", JS)
        corpo = trecho(JS, "function propriasLinha", "\n}")
        self.assertIn("c.proprias", corpo)
        # Sem próprias não escreve nada — é o que impede um buraco no tile.
        self.assertIn("if (!c.proprias) return ''", corpo)
        # E tem cor própria, para não parecer uma nota qualquer.
        self.assertIn(".dtile .onde.propria", CSS)

    def test_nao_diz_as_proprias_duas_vezes(self):
        """A linha «de onde vem o que tem» deixou de as repetir."""
        # O fim do `deckTile` marca-se por um literal que existe antes e depois
        # desta ordem — senão o teste rebentava a LER o código antigo em vez de
        # dizer o que tem a dizer sobre ele.
        corpo = trecho(JS, "function deckTile", "Uma cópia própria que NÃO serve")
        self.assertNotIn("próprias`)", corpo, "a nota voltou a dizer o que a linha já diz")

    def test_o_cracha_e_o_resto_da_pagina_nao_mexeram(self):
        for s in ("${c.have}/${c.wanted}",          # o crachá que «já indica»
                  "próprias do deck ${l.proprias",  # o chip do cabeçalho
                  "td('próprias'",                  # a tabela de montagem
                  "'proprias'",                     # a coluna do CSV
                  "proprias_fora",                  # a secção das que não servem
                  "propriaForaTile"):
            self.assertIn(s, JS, s)

    def test_as_notas_mandam_na_consola_e_nao_num_botao(self):
        """As três notas que mandavam carregar no `+` apontam ao comando."""
        self.assertIn("riftvault proprias", JS)
        for s in ("mete-as com o <b>+</b>", "diz quantas com o <b>+</b>",
                  "tira-as com o <b>−</b>"):
            self.assertNotIn(s, JS, f"a nota manda num botão que já não existe: {s}")


class TestEsconderNaoEApagar(unittest.TestCase):
    """O lado do servidor fica INTEIRO: é por lá que ele mexe agora.

    Quem prova que isto FUNCIONA de ponta a ponta — a rota, o local, a Coleção
    que não mexe, a CLI — é o `tests/test_copias_proprias.py`, que não se tocou
    e continua verde. Aqui só se exige que nada disso tenha sido apagado de
    arrasto com os botões.
    """

    def test_a_rota_continua_registada(self):
        servidor = (REPO / "riftvault" / "server.py").read_text(encoding="utf-8")
        self.assertIn('@app.post("/api/proprias/ajustar")', servidor)

    def test_o_modulo_e_o_local_continuam_la(self):
        modulo = (REPO / "riftvault" / "proprias.py").read_text(encoding="utf-8")
        self.assertIn("def ajustar", modulo)
        locais = (REPO / "riftvault" / "locais.py").read_text(encoding="utf-8")
        self.assertIn("PROPRIO_PREFIX", locais)

    def test_a_consola_continua_a_ser_a_porta(self):
        cli = (REPO / "riftvault" / "cli.py").read_text(encoding="utf-8")
        self.assertIn("proprias", cli)
        self.assertIn("--menos", cli)

    def test_o_payload_do_deck_continua_a_dizer_quantas_sao(self):
        """Se o servidor deixasse de mandar o `proprias`, a linha nova ficava
        sempre vazia e ninguém dava por isso."""
        decks = (REPO / "riftvault" / "decks.py").read_text(encoding="utf-8")
        self.assertIn("proprias", decks)


def trecho(texto: str, inicio: str, fim: str) -> str:
    """O corpo de uma função do `app.js`, para uma asserção não apanhar o
    ficheiro inteiro."""
    i = texto.index(inicio)
    return texto[i:texto.index(fim, i)]


if __name__ == "__main__":
    unittest.main()

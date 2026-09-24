"""A CASCA do site (2026-09-24): navegação, rotas, cabeçalho — e nada de scroll
lateral.

Pedido do André, à letra: *"faz o mesmo rebrand para os outros projetos"*,
depois de o mtgvault ter sido reestruturado. O que estava mal era o mesmo que
estava lá: duas filas de botões no topo, as duas com `overflow-x: auto`. Medido
antes de mexer, num Chrome a sério a 390 px: a fila dos decks acabava aos
**1042 px** e a das edições aos 683 px — de nove botões viam-se três.

O que este ficheiro defende, e que é o que parte primeiro quando se acrescenta
uma secção:

  * a navegação sai de UM sítio (`NAV`, no `app.js`) e cobre todas as secções,
    sem órfãs nos dois sentidos;
  * as rotas (`#a-mais`, `#decks/staples`) e os ids do DOM (`sec-a-mais`) são
    textos DIFERENTES — foi assim que se resolveu o browser a tratar a rota
    como âncora e a abrir a página já a meio;
  * não há links partidos: tudo o que a página aponta com `#` existe;
  * nenhuma barra de navegação volta a ter scroll lateral.

Lê os ficheiros do `riftvault/web/` — não precisa de base de dados nem de rede.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.fixture import REPO  # noqa: E402

WEB = REPO / "riftvault" / "web"
HTML = (WEB / "index.html").read_text(encoding="utf-8")
JS = (WEB / "app.js").read_text(encoding="utf-8")
CSS = (WEB / "style.css").read_text(encoding="utf-8")


def _bloco(nome: str, abre: str = "[", fecha: str = "]") -> str:
    """O texto de uma constante `const <nome> = [...]`/`{...}` do `app.js`.

    Conta os parênteses em vez de procurar um `\\n];`: a `SECCOES` cabe numa
    linha e a `NAV` não, e uma expressão regular preguiçosa apanhava da
    primeira até ao fim da segunda.
    """
    i = JS.index(f"const {nome} = {abre}") + len(f"const {nome} = ")
    nivel, j = 0, i
    while j < len(JS):
        if JS[j] == abre:
            nivel += 1
        elif JS[j] == fecha:
            nivel -= 1
            if nivel == 0:
                return JS[i + 1:j]
        j += 1
    raise AssertionError(f"a constante {nome} não fecha")


NAV = _bloco("NAV")
PAGINA = _bloco("PAGINA", "{", "}")
SECCOES = re.findall(r"'([a-z-]+)'", _bloco("SECCOES"))
# `{ sec: 'decks', sub: 'staples', ico: 'staples', rot: 'Por deck' }`
ITENS = re.findall(
    r"\{\s*sec:\s*'([a-z-]+)'(?:,\s*sub:\s*'([a-z-]+)')?,\s*ico:\s*'(\w+)',\s*rot:\s*'([^']+)'",
    NAV)


class TestNavegacao(unittest.TestCase):

    def test_ha_itens_e_saem_todos_da_mesma_tabela(self):
        self.assertGreaterEqual(len(ITENS), len(SECCOES),
                                "a NAV tem de cobrir pelo menos uma entrada por secção")

    def test_cada_seccao_esta_na_barra_lateral(self):
        """Uma secção sem item na barra é uma página a que não se chega."""
        naveg = {sec for sec, sub, _i, _r in ITENS if not sub}
        self.assertEqual(naveg, set(SECCOES))

    def test_cada_item_da_barra_aponta_a_uma_seccao_que_existe(self):
        for sec, _sub, _ico, rot in ITENS:
            self.assertIn(sec, SECCOES, f"«{rot}» aponta à secção {sec!r}, que não existe")

    def test_cada_seccao_tem_a_sua_section_no_html(self):
        no_html = re.findall(r'<section id="sec-([a-z-]+)"', HTML)
        self.assertEqual(no_html, SECCOES, "a ordem e o conjunto têm de bater certo")

    def test_a_rota_e_o_id_do_dom_sao_textos_diferentes(self):
        """A rota `#decks` e um `id="decks"` eram o mesmo texto, e o browser
        tratava a rota como âncora: saltava para a `<section>` e a página abria
        com o cabeçalho (migalhas, título, seletor de edição, e no telemóvel o
        `<select>` dos decks) já acima do topo do ecrã. Um `scrollTo(0, 0)` não
        chegava — o salto do browser é depois do `boot()`."""
        for sec in SECCOES:
            self.assertNotIn(f'id="{sec}"', HTML, f"o id {sec!r} volta a colidir com a rota")
        self.assertIn("$('#sec-' + s)", JS)

    def test_as_sub_vistas_dos_decks_sao_as_listas_de_compra(self):
        subs = [sub for sec, sub, _i, _r in ITENS if sub]
        ids = re.findall(r"id: '(\w+)'", _bloco("DECK_FALTA_TABS"))
        self.assertEqual(subs, ids)

    def test_cada_item_tem_um_icone_que_existe(self):
        """Um nome de ícone errado devolve string vazia — e o item ficava sem
        nada à esquerda, sem ninguém dar por isso."""
        conjunto = set(re.findall(r"^  (\w+):", re.search(
            r"const ICO = \{(.*?)\n\};", JS, re.S).group(1), re.M))
        for _sec, _sub, icone, rot in ITENS:
            self.assertIn(icone, conjunto, f"«{rot}» pede o ícone {icone!r}, que não existe")

    def test_cada_seccao_tem_titulo_e_subtitulo(self):
        """O título da página é o rótulo da barra (`renderCabecalho`); o
        subtítulo vem da tabela `PAGINA` e diz o que a página responde."""
        for sec in SECCOES:
            self.assertIn(f"'{sec}': {{", PAGINA, sec)

    def test_a_barra_e_a_mesma_no_telemovel(self):
        """Não há um segundo menu «de telemóvel» com menos coisas: o painel ☰
        mostra o MESMO `<aside id="side">`, deslocado por CSS."""
        self.assertEqual(HTML.count('id="sidenav"'), 1)
        self.assertEqual(HTML.count('id="side"'), 1)
        self.assertIn("body.menu-on .side { transform: none; }", CSS)
        self.assertIn('aria-controls="side"', HTML)


class TestLinks(unittest.TestCase):

    ROTAS_EXTERNAS = {"conteudo"}   # o salta-para-o-conteúdo

    def _internos(self, texto: str) -> list[str]:
        return [h for h in re.findall(r'href="#([^"]*)"', texto) if h]

    def test_nao_ha_links_partidos_no_html(self):
        ids = set(re.findall(r'id="([^"]+)"', HTML))
        for alvo in self._internos(HTML):
            sec = alvo.split("/")[0]
            self.assertTrue(sec in SECCOES or alvo in ids,
                            f'href="#{alvo}" não é secção nem id do documento')

    def test_nao_ha_links_partidos_no_javascript(self):
        """As notas de dentro das páginas apontam umas às outras — a do deck
        manda para as Encomendas desde 2026-09-17, e a da Coleção para as
        Faltas desde 2026-09-19. E a linha «N cópias a comprar» aponta à caixa
        do Cardmarket lá em baixo, que é um bloco desenhado em tempo de
        execução (`wlBloco`) — por isso os ids contam-se nos dois ficheiros."""
        ids = set(re.findall(r'id="([^"${]+)"', HTML)) | set(re.findall(r'id="([^"${]+)"', JS))
        for alvo in self._internos(JS):
            sec = alvo.split("/")[0]
            if "${" in alvo:
                continue          # rota montada em tempo de execução
            # O `wlBloco` escreve `id="${id}"`, com o nome vindo do argumento:
            # vale o nome aparecer no ficheiro como texto. Um `#wl-edicaoo`
            # mal escrito continua a dar vermelho.
            self.assertTrue(sec in SECCOES or alvo in ids or f"'{alvo}'" in JS,
                            f'href="#{alvo}" não é secção nem id que a página escreva')

    def test_a_casa_mae_e_o_baverone(self):
        self.assertIn('href="https://baverone.com"', HTML)
        self.assertIn("← baverone.com", HTML)


class TestSemScrollLateral(unittest.TestCase):
    """*"Nada de filas de botões com scroll lateral"* — a ordem, à letra."""

    def test_nenhuma_barra_de_navegacao_tem_overflow_x(self):
        """A regra `.tabs { overflow-x: auto }` era o que escondia os botões:
        o `scrollWidth` do documento continuava a dar 390, e por isso um teste
        que só olhasse para ele dizia que estava tudo bem."""
        self.assertNotIn("overflow-x: auto", CSS)
        self.assertNotIn("overflow-x:auto", CSS)
        self.assertNotIn(".tabs {", CSS)

    def test_o_seletor_de_edicao_envolve(self):
        m = re.search(r"\.segwrap \{(.*?)\}", CSS, re.S)
        self.assertIsNotNone(m, "não há `.segwrap` — o seletor de edição")
        self.assertIn("flex-wrap: wrap", m.group(1))

    def test_o_indice_dos_decks_vira_select_no_telemovel(self):
        """Nove botões numa fila davam 1042 px num ecrã de 390. O índice
        vertical some e fica um `<select>` — cabe, e os nomes não se cortam."""
        self.assertIn('id="deck-sel"', HTML)
        movel = CSS[CSS.index("@media (max-width: 899px)"):]
        self.assertIn(".vidx { display: none; }", movel)
        self.assertIn(".vidxsel { display: block; }", movel)

    def test_o_indice_e_o_select_saem_da_mesma_lista(self):
        """Duas listas eram duas ordens e dois rótulos para a mesma coisa."""
        corpo = re.search(r"function renderDeckTabs\(\) \{(.*?)\n\}\n", JS, re.S).group(1)
        self.assertIn("#deck-tabs", corpo)
        self.assertIn("#deck-sel", corpo)
        # Os dois lados desenham-se do `itensDoIndice()` e de mais nada.
        self.assertNotIn("state.decks", corpo)
        self.assertNotIn("DECK_FALTA_TABS", corpo)


class TestIdentidade(unittest.TestCase):
    """Os tokens comuns do baverone.com, e o que muda de projeto para projeto."""

    def test_a_cor_do_projeto_e_o_roxo_e_o_logotipo_e_um_R(self):
        self.assertIn("--accent: #a77bff;", CSS)
        self.assertIn('<span class="mk" aria-hidden="true">R</span>', HTML)

    def test_os_tokens_sao_os_do_mtgvault(self):
        for token in ("--bg: #07080d", "--card2: #0e1018", "--card: #12151f",
                      "--ink: #eef0f6", "--muted: #8c93a8",
                      "--line: rgba(255, 255, 255, .07)", "--maxw: 1200px"):
            self.assertIn(token, CSS, token)

    def test_as_letras_tem_pilha_de_sistema_por_tras(self):
        """Sem rede — ou com o Google Fonts em baixo — a página lê-se na mesma,
        só com outra letra."""
        self.assertIn("fonts.googleapis.com/css2?family=Inter", HTML)
        self.assertIn("display=swap", HTML)
        self.assertIn("--font: 'Inter', system-ui", CSS)
        self.assertIn("--font-hd: 'Space Grotesk', 'Inter', system-ui", CSS)

    def test_os_icones_sao_svg_e_nao_emojis(self):
        """Um emoji é desenhado pelo SISTEMA: sai diferente no Android dele e
        no Chrome do PC, e nunca acende com o rótulo quando o item fica
        activo."""
        self.assertFalse(re.search(r"[\U0001F300-\U0001FAFF]", NAV + PAGINA),
                         "há um emoji na navegação")
        self.assertIn("stroke-width: 1.8", CSS)

    def test_a_ajuda_longa_esta_recolhida(self):
        """*"Textos explicativos longos em `<details>` «Como ler esta
        página»"*."""
        self.assertIn("Como ler esta página", JS)
        self.assertIn("details.comoler", CSS)
        self.assertIn('id="pg-ajuda"', HTML)


class TestNadaSePerdeu(unittest.TestCase):
    """*"Nenhuma funcionalidade se perde (incluindo o modo de edição)"*."""

    def test_o_modo_de_edicao_continua_a_ligar_e_desligar_os_botoes(self):
        self.assertIn("document.body.classList.toggle('readonly', !state.editable)", JS)
        self.assertIn('id="readonly-banner"', HTML)
        self.assertIn('id="mode-badge"', HTML)

    def test_os_controlos_da_colecao_ficaram_todos(self):
        for ident in ('id="search"', 'id="grid"', 'id="painel"', 'id="foil-resumo"',
                      'id="progress"', 'id="runas-vista"', 'id="wantlists"',
                      'data-view="base"', 'data-state="indeck"'):
            self.assertIn(ident, HTML, ident)

    def test_as_encomendas_ficaram_com_os_controlos(self):
        for ident in ('id="enc-grid"', 'id="enc-search"', 'data-enc-filter="ordered"',
                      'id="enc-head"'):
            self.assertIn(ident, HTML, ident)

    def test_o_inicio_nao_faz_contas_novas(self):
        """O painel do Início mostra números que outras páginas já calculam. Se
        começar a fazer aritmética própria, passa a ser uma segunda resposta às
        mesmas perguntas — e mais cedo ou mais tarde discorda da página a que
        manda ir. A única conta permitida é a subtração de dois campos do MESMO
        payload (a coleção extra = total − listas)."""
        corpo = re.search(r"function renderInicio\(\) \{(.*?)\n\}\n", JS, re.S).group(1)
        self.assertNotIn("state.qty", corpo)
        self.assertNotIn("state.payload", corpo)
        self.assertNotIn("state.targets", corpo)

    def test_o_inicio_aguenta_um_payload_que_nao_responda(self):
        """Três dos quatro ficheiros chegam depois; um que falhe deixa o cartão
        a «—» e não leva a página atrás."""
        corpo = re.search(r"async function carregarInicio\(\) \{(.*?)\n\}\n", JS, re.S).group(1)
        self.assertIn("catch", corpo)


if __name__ == "__main__":
    unittest.main()

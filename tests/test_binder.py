"""AS FILAS DO BINDER na Coleção (2026-09-26): a primeira 4, as seguintes 8.

Pedido do André, à letra: *"quero que as filas da coleccao estejam organizas
por / primeira fila de todas 4 / depois de 8 em 8 / que e como fica o Binder"*.

O OBJECTIVO manda em tudo: **a posição de um tile na grelha é a posição da
carta na pasta dele**. É uma ferramenta para encontrar a carta. O que este
ficheiro defende é exactamente o que parte essa correspondência:

  * o número por fila tem de ser FIXO — `auto-fill` fazia-o mudar com a
    largura da janela e a 5.ª carta deixava de estar na 2.ª fila;
  * cada IMPRESSÃO ocupa UMA célula — um `.group.multi` a ocupar várias
    colunas deixava a fila com menos de 8 cartas;
  * em ecrãs estreitos NÃO REFLUI: o bloco corre para o lado;
  * só a SEQUÊNCIA do master set anda assim (é a que ele arruma por número);
  * com um filtro a esconder parte da sequência, as filas deixam de ser as da
    pasta — e aí diz-se, em vez de apontar a bolsa errada em silêncio;
  * e NÃO MEXE EM NÚMERO NENHUM: é desenho, e nenhum módulo de contas sabe
    que isto existe.

Lê os ficheiros do `riftvault/web/` e, para a ordem da sequência, um catálogo
de brincar — nunca o `data/` do André.
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.fixture import REPO, Vault  # noqa: E402

WEB = REPO / "riftvault" / "web"
CSS = (WEB / "style.css").read_text(encoding="utf-8")
JS = (WEB / "app.js").read_text(encoding="utf-8")

PRIMEIRA, FILA = 4, 8


def fila_pos(n: int) -> tuple[int, int]:
    """Fila e posição (1-based) da n-ésima carta da sequência.

    É a aritmética do ritmo 4 + 8, escrita aqui para o teste poder dizer os
    números que ele vai verificar contra a pasta. O desenho vive no CSS
    (`.grid.binder` + `.binder-gap`); isto é a mesma regra por outras palavras,
    e é de propósito que são duas: se uma delas mudar, os números deixam de
    bater e o teste dá vermelho.
    """
    if n < 1:
        raise ValueError("a primeira carta é a 1")
    if n <= PRIMEIRA:
        return 1, n
    k = n - PRIMEIRA - 1
    return 2 + k // FILA, 1 + k % FILA


def _regra(seletor: str) -> str:
    """O corpo de uma regra do CSS, pelo seletor."""
    m = re.search(re.escape(seletor) + r"\s*\{(.*?)\}", CSS, re.S)
    assert m is not None, f"não há regra `{seletor}` no style.css"
    return m.group(1)


def _corpo_do_render() -> str:
    i = JS.index("function render() {")
    return JS[i:JS.index("\nfunction renderProgress()", i)]


class TestORitmo(unittest.TestCase):
    """4 na primeira fila, 8 nas seguintes — e os números vêm de um sítio."""

    def test_os_dois_numeros_estao_escritos_uma_vez(self):
        self.assertIn(f"const BINDER_PRIMEIRA = {PRIMEIRA};", JS)
        self.assertIn(f"const BINDER_FILA = {FILA};", JS)

    def test_as_colunas_sao_oito_fixas(self):
        corpo = _regra(".grid.binder")
        self.assertIn(f"repeat({FILA}, minmax(var(--tile-binder), 1fr))", corpo)
        self.assertNotIn("auto-fill", corpo)
        self.assertNotIn("auto-fit", corpo)

    def test_o_resto_da_grelha_continua_em_auto_fill(self):
        """Só a sequência é que é fixa: os outros blocos não são a pasta."""
        self.assertIn("auto-fill", _regra("\n.grid"))

    def test_o_calco_fecha_a_primeira_fila_nas_quatro(self):
        """O calço ocupa as 4 colunas que sobram da primeira fila e empurra a
        5.ª carta para baixo. É a única maneira de ter uma fila diferente das
        outras sem escrever posições à mão em 298 tiles."""
        self.assertIn(f"grid-column: span {FILA - PRIMEIRA};", _regra(".binder-gap"))
        corpo = _corpo_do_render()
        self.assertIn("naEdicao === BINDER_PRIMEIRA", corpo)
        self.assertIn('class="binder-gap" aria-hidden="true"', corpo)

    def test_o_calco_nao_e_um_tile_nem_se_le(self):
        """Não entra no `state.tiles` (senão as setas paravam nele) e leva
        `aria-hidden` (senão um leitor de ecrã anunciava uma célula vazia)."""
        corpo = _corpo_do_render()
        calco = corpo[corpo.index('class="binder-gap"'):]
        self.assertNotIn("state.tiles.push", calco.split("}")[0])
        self.assertIn("aria-hidden", corpo[:corpo.index('binder-gap"') + 40])

    def test_o_ritmo_recomeca_em_cada_edicao(self):
        """Em «Todas» são cinco pastas seguidas, não uma de 928 cartas."""
        corpo = _corpo_do_render()
        # O contador põe-se a zero no mesmo sítio onde nasce o cabeçalho da
        # edição.
        cabecalho = corpo[corpo.index("if (g.set && g.set !== edicao)"):]
        self.assertIn("naEdicao = 0;", cabecalho[:400])

    def test_as_posicoes_que_ele_vai_conferir_contra_a_pasta(self):
        self.assertEqual(fila_pos(1), (1, 1))
        self.assertEqual(fila_pos(4), (1, 4))
        self.assertEqual(fila_pos(5), (2, 1))
        self.assertEqual(fila_pos(12), (2, 8))
        self.assertEqual(fila_pos(13), (3, 1))

    def test_a_fila_seguinte_fecha_nas_oito(self):
        self.assertEqual(fila_pos(20), (3, 8))
        self.assertEqual(fila_pos(21), (4, 1))

    def test_a_ultima_carta_da_OGN(self):
        """298 = 4 + 8 × 36 + 6: a sequência do OGN acaba na fila 38."""
        self.assertEqual(fila_pos(298), (38, 6))

    def test_a_primeira_fila_e_a_unica_com_quatro(self):
        filas = {}
        for n in range(1, 300):
            f, _ = fila_pos(n)
            filas[f] = filas.get(f, 0) + 1
        self.assertEqual(filas[1], PRIMEIRA)
        for f in range(2, 38):
            self.assertEqual(filas[f], FILA, f"a fila {f} não tem {FILA}")


class TestUmaImpressaoUmaCelula(unittest.TestCase):
    """No binder cada carta ocupa uma bolsa — nenhum grupo ocupa duas."""

    def test_nas_filas_do_binder_cada_impressao_sai_no_seu_group(self):
        corpo = _corpo_do_render()
        ramo = corpo[corpo.index("if (filasDoBinder) {"):corpo.index("const inner =")]
        self.assertIn('<div class="group">${tileHTML(g, p, i === 0)}</div>', ramo)
        # E nunca o `multi`, que é o que ocupava várias colunas. Olha-se para o
        # CÓDIGO, sem os comentários — que falam do `multi` de propósito, para
        # dizer porque é que ele não está aqui.
        codigo = "\n".join(l for l in ramo.splitlines()
                           if not l.strip().startswith("//"))
        self.assertNotIn("multi", codigo)
        self.assertNotIn("--span", codigo)

    def test_o_multi_continua_a_existir_para_os_outros_blocos(self):
        """Não se apagou o agrupamento visual: fora da sequência continua a
        ser a resposta certa (vê-se de relance que a alt art é daquela carta)."""
        corpo = _corpo_do_render()
        self.assertIn('class="group multi" style="--span:${list.length}"', corpo)
        self.assertIn("grid-column: span var(--span, 2);", CSS)

    def test_os_blocos_separam_as_variantes_e_por_isso_nao_ha_multi_hoje(self):
        """A razão de fundo de hoje não haver um único grupo `multi`: a base
        vai para a sequência e a arte alternativa para o bloco dela. Medido a
        2026-09-26 nas cinco edições reais: 928 grupos no bloco master, TODOS
        de uma impressão só. Aqui fixa-se o mecanismo que o garante."""
        v = Vault()
        try:
            con = v.connect()
            v.add_printing(con, "tst-001-100", "TST", 1, "Defy")
            v.add_printing(con, "tst-001a-100", "TST", 1, "Defy",
                           variant="a", kind="alt_art", rarity="showcase",
                           base_rarity="common")
            v.rebuild(con)
            from riftvault import metrics
            p = metrics.set_payload(con, "TST")
            grupo = next(g for g in p["groups"] if g["name"] == "Defy")
            self.assertEqual(len(grupo["printings"]), 2)
            por_bloco = {}
            for pr in grupo["printings"]:
                por_bloco.setdefault(pr.get("block") or "master", []).append(pr["code"])
            self.assertEqual(sorted(por_bloco), ["alt_art", "master"])
            for bloco, lista in por_bloco.items():
                self.assertEqual(len(lista), 1, f"o bloco {bloco} ficaria `multi`")
            con.close()
        finally:
            v.close()


class TestSoASequencia(unittest.TestCase):
    """A pasta é a sequência numerada; os outros blocos não são a pasta."""

    def test_o_bloco_esta_escrito_num_sitio(self):
        self.assertIn("const BLOCO_BINDER = 'master';", JS)

    def test_so_o_master_set_leva_as_filas_do_binder(self):
        corpo = _corpo_do_render()
        self.assertIn("b.id === BLOCO_BINDER && binder.cheio", corpo)
        self.assertIn('<div class="binder-wrap"><div class="grid binder">', corpo)

    def test_as_encomendas_ficam_como_estavam(self):
        """A grelha das Encomendas é a mesma da Coleção CORTADA na raridade
        (de Rara para cima, 2026-09-17): faltam-lhe cartas, e por isso as
        posições nunca seriam as da pasta. Não leva filas do binder."""
        i = JS.index("function renderEncomendas(")
        corpo = JS[i:JS.index("\nfunction ", i + 10)]
        self.assertNotIn("binder", corpo)

    def test_a_sequencia_sai_por_numero_de_coleccao(self):
        """Se a ordem do payload não for a do número impresso, a fila certa
        aponta a carta errada. É esta ordem que faz o ritmo valer."""
        v = Vault()
        try:
            con = v.connect()
            for cn in (3, 1, 13, 5, 12, 4, 2):   # fora de ordem, de propósito
                v.add_printing(con, f"tst-{cn:03d}-100", "TST", cn, f"Carta {cn}")
            v.rebuild(con)
            from riftvault import metrics
            p = metrics.set_payload(con, "TST")
            seq = [pr for g in p["groups"] for pr in g["printings"]
                   if (pr.get("block") or "master") == "master"]
            self.assertEqual([pr["code"] for pr in seq],
                             ["TST-001", "TST-002", "TST-003", "TST-004",
                              "TST-005", "TST-012", "TST-013"])
            # E a quinta a sair é a que cai na 2.ª fila, 1.ª posição.
            self.assertEqual(fila_pos(5), (2, 1))
            self.assertEqual(seq[4]["code"], "TST-005")
            con.close()
        finally:
            v.close()


class TestNaoReflui(unittest.TestCase):
    """Se o número por fila mudasse com a largura, a funcionalidade morria."""

    def test_nenhum_media_query_mexe_nas_filas(self):
        for m in re.finditer(r"@media[^{]*\{", CSS):
            bloco = CSS[m.end():CSS.index("\n}", m.end())]
            self.assertNotIn(".grid.binder", bloco)
            self.assertNotIn("--tile-binder", bloco)
            self.assertNotIn("--binder-gap", bloco)

    def test_o_tile_encolhe_ate_um_chao_e_o_chao_e_o_do_polegar(self):
        """104px é o mínimo que o projeto já documentava para os +/- (ver
        `--tile`). Encolher mais não evitava o scroll num telemóvel de 375px —
        8 tiles nunca cabem lá — e só estragava os botões."""
        self.assertIn("--tile-binder: 104px;", CSS)
        self.assertIn("--tile: 104px;", CSS)

    def test_abaixo_do_chao_e_o_bloco_que_corre(self):
        self.assertIn("overflow-x: auto;", _regra(".binder-wrap"))
        corpo = _regra(".grid.binder")
        self.assertIn("min-width: calc(8 * var(--tile-binder) + 7 * var(--binder-gap));",
                      corpo)

    def test_o_scroll_e_do_bloco_e_nao_da_pagina(self):
        """O `overflow-x` faz do `.binder-wrap` um contentor de scroll, e é
        isso que impede a largura mínima das 8 colunas de empurrar a grelha de
        fora (e a página) para o lado."""
        self.assertIn("grid-column: 1 / -1;", _regra(".binder-wrap"))
        self.assertIn("overscroll-behavior-x: contain;", _regra(".binder-wrap"))

    def test_num_ecra_largo_os_tiles_nao_crescem_sem_fim(self):
        self.assertIn("max-width: calc(8 * var(--tile) + 7 * var(--binder-gap));",
                      _regra(".grid.binder"))


class TestQuandoUmFiltroEsconde(unittest.TestCase):
    """Mentir na posição é pior do que mudar de desenho."""

    def test_as_filas_do_binder_exigem_a_sequencia_inteira(self):
        corpo = JS[JS.index("function binderCheio()"):]
        corpo = corpo[:corpo.index("\n}")]
        self.assertIn("visiblePrintings(g)", corpo)
        self.assertIn("vistas === todas", corpo)

    def test_e_diz_se_porque(self):
        corpo = _corpo_do_render()
        self.assertIn("!binder.cheio", corpo)
        nota = corpo[corpo.index('class="binder-nota"'):]
        nota = nota[:nota.index("</p>")]
        self.assertIn("não", nota)
        self.assertIn("${binder.vistas}", nota)
        self.assertIn("${binder.todas}", nota)
        self.assertIn("${BINDER_PRIMEIRA} + ${BINDER_FILA}", nota)
        self.assertIn(".binder-nota", CSS)


class TestNaoMexeEmNumeroNenhum(unittest.TestCase):
    """É DESENHO. Nenhuma contagem, percentagem, alvo ou bloco sabe disto."""

    def test_nenhum_modulo_de_python_conhece_o_binder(self):
        for py in sorted((REPO / "riftvault").glob("*.py")):
            texto = py.read_text(encoding="utf-8")
            for palavra in ("binder-wrap", "grid binder", "BINDER_PRIMEIRA",
                            "tile-binder"):
                self.assertNotIn(palavra, texto,
                                 f"{py.name} fala do desenho do binder")

    def test_o_binder_nao_e_um_bloco_da_grelha(self):
        """`BLOCO_BINDER` aponta para um bloco que já existia (`master`). Não
        nasceu bloco nenhum, nem alvo, nem categoria — o `metrics.BLOCOS` é o
        mesmo."""
        from riftvault import metrics
        self.assertEqual(metrics.BLOCO_MASTER, "master")
        self.assertIn("const BLOCO_BINDER = 'master';", JS)

    def test_a_grelha_desenha_as_mesmas_impressoes(self):
        """O ramo do binder empurra o MESMO `state.tiles` que o outro: o que
        muda é a célula onde cada tile cai, não quais se mostram."""
        corpo = _corpo_do_render()
        self.assertEqual(corpo.count("state.tiles.push(p.id);"), 2)
        self.assertIn("${state.tiles.length} impressões a mostrar", corpo)


class TestANota(unittest.TestCase):
    """A frase dele, a data e o porquê — na gramática das outras notas."""

    def test_o_css_diz_o_pedido_a_data_e_o_ritmo(self):
        troco = CSS[CSS.index("as filas do binder"):]
        troco = troco[:troco.index(".binder-nota")]
        self.assertIn("2026-09-26", troco)
        self.assertIn("primeira fila de todas 4", troco)
        self.assertIn("depois de 8 em 8", troco)
        self.assertIn("como fica o Binder", troco)

    def test_o_css_diz_porque_e_que_nao_pode_refluir(self):
        troco = CSS[CSS.index("as filas do binder"):CSS.index(".binder-nota")]
        self.assertIn("auto-fill", troco)
        self.assertIn("NÃO REFLUI", troco)

    def test_o_claude_md_tem_a_seccao(self):
        md = (REPO / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn("filas da coleccao estejam organizas", md)
        self.assertIn("## 26/09/2026", md)


if __name__ == "__main__":
    unittest.main()

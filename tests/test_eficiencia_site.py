"""A EFICIÊNCIA DO SITE PUBLICADO (2026-10-04) — o §5 e a lacuna 8.5 do
`docs/varrimento-2026-10-01.md`.

A lacuna 8.5, nas palavras dela: *«Nenhum teste mede o tamanho do site por
pessoa. Um teste que falhe quando a casca passa a ser copiada N vezes travava
o §5 antes de doer — hoje `tests/test_lista.py` conta ficheiros e nomes, nunca
bytes.»* É esta a vigia, e **conta BYTES**.

O que se vigia, por esta ordem:

  * **a casca é UMA SÓ** — nenhum ficheiro grande se repete byte a byte no
    site. A regra é genérica de propósito: se amanhã nascer um terceiro
    ficheiro de casca (uma fonte, um `.map`) e alguém o copiar por pessoa,
    este teste apanha-o sem ninguém o ter escrito aqui;
  * **o site não cresce com a casca** por cada pessoa nova — a conta é dos
    bytes da casca no site, que têm de ser os de UMA cópia, aconteça o que
    acontecer ao tamanho das coleções;
  * **o crivo**: um ficheiro cujo conteúdo não mudou não se reescreve, uma
    publicação em que nada mudou não escreve nada, e o `api/index.json` é
    sempre fresco quando algum outro mudou (a regra 2 do `build._Saida` — a
    prova de que o site publicado é o que foi gerado aqui).

PROVA PELA NEGATIVA, medida e escrita em
`docs/eficiencia-site-2026-10-04.md`: desfaz-se o defeito **na FONTE, uma
linha** (nunca com um monkey-patch — o `tests/fixture.py` faz
`importlib.reload(config)` em cada `setUp` e apaga patches em memória, e essa
armadilha já custou uma manhã a 2026-10-04) e vê-se o que fica vermelho.
"""

from __future__ import annotations

import hashlib
import json
import unittest
from collections import defaultdict
from pathlib import Path

from riftvault import build, collection, config, db, lista, privacidade, utilizador
from tests import fixture

#: Acima deste tamanho um ficheiro repetido já é desperdício que se vê. A
#: casca são 450 KB; os payloads pequenos (um `compras.json` de 300 bytes) podem
#: coincidir entre duas coleções parecidas sem isso ser defeito nenhum.
GRANDE_KB = 8

#: O `index.html` É a página, e cada coleção tem de ter a sua no URL dela —
#: duas pessoas com a mesma privacidade ficam com páginas byte a byte iguais e
#: isso não é casca copiada, é o sítio onde a página mora. Fica de fora da
#: regra dos duplicados, nomeado, em vez de se subir o limiar: subi-lo a 17 KB
#: (o tamanho dela) deixava passar um ficheiro de casca de 20 KB.
#:
#: SOBRA MEDIDA, e fica dita em vez de escondida: são ~16,8 KB × (N−1) —
#: 33,6 KB com as três pessoas de hoje, ~320 KB a 20. Tirá-la pedia que a
#: página fosse um esboço que carrega tudo por JavaScript, e isso é mexer no
#: frontend, não na arrumação do site.
A_PAGINA = "index.html"


class Base(unittest.TestCase):

    def setUp(self):
        fixture.config_decks_sem_alt_art(self)
        self.v = fixture.Vault()
        self.addCleanup(self.v.close)
        con = self.v.connect()
        self.v.add_printing(con, "tst-001-100", "TST", 1, "Defy")
        self.v.add_printing(con, "tst-002-100", "TST", 2, "Brutalizer")
        self.v.rebuild(con)
        collection.adjust(con, "tst-001-100", 3, source="test")
        con.close()
        privacidade.definir(None, utilizador.ANDRE, "tudo")

    # -- ajudas ------------------------------------------------------------

    def amigo(self, nome, slug, copias=2):
        u = utilizador.criar(nome, slug)
        con = db.connect(user_id=u["user_id"])
        collection.adjust(con, "tst-002-100", copias, source="test")
        con.close()
        privacidade.definir(None, u["user_id"], "tudo")
        return u

    def gerar(self, pasta="site", **kw):
        out = self.v.root / pasta
        res = build.build_todos(out, log=lambda *_: None,
                                cfg={"multi": {"aberto": True}}, **kw)
        return out, res

    def ficheiros(self, out: Path) -> dict[str, bytes]:
        return {p.relative_to(out).as_posix(): p.read_bytes()
                for p in out.rglob("*") if p.is_file()}

    def retrato(self, out: Path) -> dict[str, str]:
        return {n: hashlib.sha256(b).hexdigest()
                for n, b in self.ficheiros(out).items()}


# ---------------------------------------------------------------------------
# A lacuna 8.5: a casca é UMA SÓ, e isto conta BYTES
# ---------------------------------------------------------------------------

class TestACascaEUmaSo(Base):

    def test_nenhum_ficheiro_grande_se_repete_byte_a_byte(self):
        """A VIGIA da lacuna 8.5, na forma genérica.

        Não pergunta pelo `app.js` pelo nome: pergunta se há bytes repetidos.
        Um terceiro ficheiro de casca que nasça amanhã e que alguém copie por
        pessoa fica vermelho aqui sem ninguém ter escrito o nome dele. A única
        excepção é o `index.html` — ver `A_PAGINA`.
        """
        self.amigo("Gonçalves", "goncalves")
        self.amigo("Miguel", "miguel")
        out, _ = self.gerar()
        por_conteudo = defaultdict(list)
        for nome, corpo in self.ficheiros(out).items():
            if Path(nome).name == A_PAGINA:
                continue
            if len(corpo) >= GRANDE_KB * 1024:
                por_conteudo[hashlib.sha256(corpo).hexdigest()].append(nome)
        repetidos = {h: ns for h, ns in por_conteudo.items() if len(ns) > 1}
        self.assertEqual(
            repetidos, {},
            "há ficheiros grandes repetidos byte a byte no site — é casca "
            "copiada por pessoa, e cresce com cada pessoa nova: "
            + "; ".join(" == ".join(ns) for ns in repetidos.values()))

    def test_os_bytes_da_casca_no_site_sao_os_de_UMA_copia(self):
        """A conta que a lacuna 8.5 pedia: BYTES, não ficheiros.

        Independente do tamanho das coleções — compara os bytes da casca no
        site com os bytes da casca em `riftvault/web/`.
        """
        self.amigo("Gonçalves", "goncalves")
        self.amigo("Miguel", "miguel")
        out, _ = self.gerar()
        uma = sum((config.WEB_DIR / n).stat().st_size for n in config.CASCA)
        no_site = sum(len(b) for n, b in self.ficheiros(out).items()
                      if Path(n).name in config.CASCA)
        self.assertEqual(no_site, uma,
                         f"a casca ocupa {no_site} bytes no site e UMA cópia "
                         f"são {uma} — está copiada "
                         f"{no_site / uma if uma else 0:.0f} vezes")

    def test_uma_pessoa_nova_nao_traz_outra_casca(self):
        """O crescimento por pessoa não pode incluir a casca.

        É a pergunta do §5 em forma de teste: «a 20 pessoas são ~50 MB de
        `site/`, 8 MB disso em `app.js` iguais». Com a casca na raiz, a conta
        da casca é a mesma com 2 pessoas e com 4.
        """
        self.amigo("Gonçalves", "goncalves")
        self.amigo("Miguel", "miguel")
        out2, _ = self.gerar("com2")
        self.amigo("Rafael", "rafael")
        self.amigo("Zeca", "zeca")
        out4, _ = self.gerar("com4")

        def casca_kb(out):
            return sum(len(b) for n, b in self.ficheiros(out).items()
                       if Path(n).name in config.CASCA)

        self.assertEqual(casca_kb(out2), casca_kb(out4),
                         "o site passou a levar mais casca por ter mais gente")
        # e que o teste não está a medir zero
        self.assertGreater(casca_kb(out2), GRANDE_KB * 1024)
        self.assertEqual(len(lista.publicas({"multi": {"aberto": True}})), 5)

    def test_cada_pagina_aponta_a_casca_DA_RAIZ_e_ela_esta_la(self):
        """E o caminho é RELATIVO: o site responde em `rift.baverone.com/` e em
        `baverone.github.io/riftvault/`, e um `/app.js` absoluto dava 404 no
        segundo."""
        self.amigo("Gonçalves", "goncalves")
        out, _ = self.gerar()
        for slug in ("baverone", "goncalves"):
            pagina = out / "u" / slug / "index.html"
            html = pagina.read_text(encoding="utf-8")
            for nome in config.CASCA:
                self.assertIn(f'"../../{nome}"', html,
                              f"a página de {slug} não aponta à casca da raiz")
                self.assertNotIn(f'"/{nome}"', html,
                                 "caminho absoluto: dava 404 numa subpasta")
                alvo = (pagina.parent / f"../../{nome}").resolve()
                self.assertTrue(alvo.is_file(), f"{alvo} não existe")
                self.assertEqual(alvo, (out / nome).resolve())
            self.assertFalse((out / "u" / slug / nome).exists(),
                             "ficou uma cópia da casca na pasta da pessoa")

    def test_a_casca_da_raiz_e_a_do_riftvault_web(self):
        """Não é uma cópia transformada: são os bytes do `riftvault/web/`."""
        self.amigo("Gonçalves", "goncalves")
        out, _ = self.gerar()
        for nome in config.CASCA:
            self.assertEqual((out / nome).read_bytes(),
                             (config.WEB_DIR / nome).read_bytes())

    def test_nenhum_nome_na_raiz_comeca_por_underscore(self):
        """A armadilha do `.nojekyll`: o Pages não serve nada que comece por
        `_`, e a casca na raiz é o primeiro ficheiro que o browser pede."""
        self.amigo("Gonçalves", "goncalves")
        out, _ = self.gerar()
        maus = [p.name for p in out.iterdir() if p.name.startswith("_")]
        self.assertEqual(maus, [], f"o Pages não serve {maus}")

    def test_a_guarda_do_pages_yml_continua_a_passar(self):
        """O passo «Confirmar que a pasta do site existe» exige `site/index.html`
        e pelo menos um `*/api/index.json`. A casca na raiz não lhe mexe, mas é
        ela que mata a build quando alguém mexe na arrumação — já matou a das
        15:31 de 2026-10-01."""
        self.amigo("Gonçalves", "goncalves")
        out, _ = self.gerar()
        self.assertTrue((out / "index.html").is_file())
        self.assertGreaterEqual(len(list(out.glob("*/*/api/index.json"))), 1)

    def test_a_referencia_da_casca_tem_de_casar_com_o_index_html(self):
        """Uma página sem `style.css` não dá erro nenhum — abre em texto cru.

        Por isso o `_aponta_a_casca` REBENTA em vez de publicar assim, e é
        isso que se fixa aqui: se o `riftvault/web/index.html` mudar de forma,
        dá vermelho na suite e não na fotografia.
        """
        html = (config.WEB_DIR / "index.html").read_text(encoding="utf-8")
        for nome, ref in build.REFERENCIA_DA_CASCA.items():
            self.assertEqual(html.count(ref), 1,
                             f"o index.html refere {nome} de outra maneira")
        with self.assertRaises(ValueError):
            build._aponta_a_casca("<html>sem casca nenhuma</html>", "../../")

    def test_a_subida_sai_do_caminho_real_e_nao_de_um_literal(self):
        pub = [{"user_id": utilizador.ANDRE, "slug": "baverone"},
               {"user_id": 2, "slug": "miguel"}]
        self.assertEqual(lista.subida_da_casca(pub[0], pub), "../../")
        self.assertEqual(lista.subida_da_casca(pub[1], pub), "../../")
        # com UMA coleção a raiz é a dele e a casca fica ao lado
        self.assertIsNone(lista.subida_da_casca(pub[0], pub[:1]))

    def test_com_uma_coleccao_so_a_raiz_leva_a_casca_como_sempre_levou(self):
        """O dia de hoje não muda para quem tem uma coleção só: a casca fica
        ao lado do `index.html`, na raiz, sem `../../` nenhum."""
        out = self.v.root / "sozinho"
        build.build_todos(out, log=lambda *_: None,
                          cfg={"multi": {"aberto": False}})
        for nome in config.CASCA:
            self.assertTrue((out / nome).is_file())
        html = (out / "index.html").read_text(encoding="utf-8")
        self.assertIn('src="app.js"', html)
        self.assertNotIn("../../", html)


# ---------------------------------------------------------------------------
# O crivo: não reescrever o que não mudou
# ---------------------------------------------------------------------------

class TestOCrivo(Base):

    def test_uma_publicacao_em_que_nada_mudou_nao_escreve_NADA(self):
        """O defeito que isto fecha, medido no repositório real: os dez commits
        do `site/` de 2026-10-04, das 05:37 às 10:07, tocaram 28 ficheiros cada
        um — e em 28 de 28 só o `generated_at` mudava.

        A pergunta é pelo CRIVO e não pelos bytes em disco, e é de propósito:
        o `generated_at` tem resolução de um segundo, e duas gerações seguidas
        num teste caem no mesmo segundo — os bytes saíam iguais mesmo com o
        crivo desligado, e o teste passava com o defeito de volta. Apanhado na
        prova pela negativa, que é para isso que ela existe.
        """
        self.amigo("Gonçalves", "goncalves")
        self.amigo("Miguel", "miguel")
        out, _ = self.gerar()
        antes = self.retrato(out)
        _, res = self.gerar()              # outra vez, sem nada ter mudado
        self.assertEqual(res["crivo"]["escritos"], [],
                         "uma publicação sem mudanças escreveu ficheiros — "
                         "é um commit e uma build do Pages de 30 em 30 minutos")
        for o in res["outros"]:
            self.assertEqual(o["crivo"]["escritos"], [],
                             f"a coleção de {o['slug']} foi reescrita sem nada "
                             f"ter mudado — é exactamente o defeito de hoje: "
                             f"o `--se-mudou` só olhava para a dele")
        self.assertEqual(self.retrato(out), antes)

    def test_so_se_reescreve_o_que_mudou(self):
        self.amigo("Gonçalves", "goncalves")
        self.amigo("Miguel", "miguel")
        out, _ = self.gerar()
        antes = self.retrato(out)
        con = db.connect(user_id=utilizador.ANDRE)
        collection.adjust(con, "tst-002-100", 1, source="test")
        con.close()
        self.gerar()
        depois = self.retrato(out)
        mexidos = sorted(n for n in depois if depois[n] != antes.get(n))
        self.assertTrue(mexidos, "a mudança não chegou ao site")
        # Nada do Miguel nem do Gonçalves pode ter mexido: a carta é DELE.
        for n in mexidos:
            self.assertFalse(n.startswith(("u/miguel/", "u/goncalves/")),
                             f"{n} foi reescrito por uma carta de OUTRA pessoa")

    def test_o_INDICE_e_sempre_fresco_quando_outro_payload_mudou(self):
        """A REGRA 2, que é uma decisão e não um efeito: é o `generated_at` do
        `api/index.json` que prova que o site publicado é o que foi gerado
        aqui, e o `test.py` da `riftvault-publicar` exige que o ficheiro tenha
        sido ESCRITO HOJE quando a tarefa diz que gerou o site.

        O que se pergunta é se o índice foi ESCRITO, e não se o relógio dele
        mudou de valor: o `generated_at` tem resolução de um segundo e duas
        gerações seguidas num teste caem no mesmo segundo. É a mesma coisa que
        a tarefa mede (ela olha para o mtime), medida de maneira a não depender
        da velocidade da máquina.
        """
        self.amigo("Gonçalves", "goncalves")
        out, _ = self.gerar()
        # Estraga-se um payload que NÃO é o índice. O conteúdo do índice não
        # muda, por isso só é reescrito se a regra 2 valer.
        (out / "u" / "baverone" / "api" / "runas.json").write_text(
            '{"estragado":true}', encoding="utf-8")
        _, res = self.gerar()
        self.assertIn("api/runas.json", res["crivo"]["escritos"])
        self.assertIn(build._Saida.INDICE, res["crivo"]["escritos"],
                      "o índice ficou com o relógio velho: a prova de que o "
                      "site publicado é o gerado aqui passa a comparar uma "
                      "data antiga, e o `escrito_hoje` da tarefa chumba sem "
                      "motivo")

    def test_e_a_PROVA_PELA_NEGATIVA_da_regra_2(self):
        """Sem nada a mudar, o índice NÃO é reescrito. Senão a regra 2 dava o
        mesmo commit de 30 em 30 minutos que o crivo veio tirar."""
        self.amigo("Gonçalves", "goncalves")
        out, _ = self.gerar()
        _, res = self.gerar()
        self.assertEqual(res["crivo"]["escritos"], [],
                         "o índice foi reescrito sem nada ter mudado")
        self.assertFalse(res["mudou"])

    def test_um_payload_orfao_sai_do_site(self):
        """A garantia que o `rmtree(api/)` dava: uma edição que saia do catálogo
        tem de sair do site, e um payload órfão fazia o `--se-mudou` ver
        diferença a cada corrida."""
        self.amigo("Gonçalves", "goncalves")
        out, _ = self.gerar()
        orfao = out / "u" / "goncalves" / "api" / "set" / "ZZZ.json"
        orfao.write_text('{"edicao":"que saiu do catalogo"}', encoding="utf-8")
        self.gerar()
        self.assertFalse(orfao.exists(), "o payload órfão ficou no site")

    def test_a_poda_so_mexe_na_api(self):
        """O resto da pasta não é nosso: o `img/` de 88 MB, um `CNAME`."""
        self.amigo("Gonçalves", "goncalves")
        out, _ = self.gerar()
        intruso = out / "u" / "goncalves" / "nao-e-nosso.txt"
        intruso.write_text("x", encoding="utf-8")
        self.gerar()
        self.assertTrue(intruso.exists())

    def test_o_incremental_diz_o_MESMO_que_o_gerado_de_raiz(self):
        """O crivo não pode deixar conteúdo velho para trás — é a pergunta que
        decide se isto é uma optimização ou um bug."""
        self.amigo("Gonçalves", "goncalves")
        out, _ = self.gerar("incremental")
        for uid, delta in ((utilizador.ANDRE, 1), (2, 2), (utilizador.ANDRE, -1)):
            con = db.connect(user_id=uid)
            collection.adjust(con, "tst-002-100", delta, source="test")
            con.close()
            self.gerar("incremental", so_se_mudou=True)
        de_raiz, _ = self.gerar("de-raiz")
        self.assertTrue(build.mesmo_conteudo(out, de_raiz),
                        "o site mantido incrementalmente divergiu do gerado "
                        "de raiz")

    def test_o_mudou_vem_do_crivo_e_nao_de_ter_corrido(self):
        """E o erro cai para o lado seguro: o `cmd_build` só imprime «Site
        gerado» com `mudou`, e é daí que a tarefa tira o `site_gerado` que liga
        o `escrito_hoje`. Um `False` a mais salta a verificação; um `True` a
        mais chumbava a tarefa."""
        out, res = self.gerar()
        self.assertTrue(res["mudou"], "a primeira geração escreve tudo")
        _, res2 = self.gerar()
        self.assertFalse(res2["mudou"],
                         "disse que gerou sem ter escrito um ficheiro")
        self.assertEqual(res2["crivo"]["escritos"], [])

    def test_o_crivo_conta_o_que_fez(self):
        out, res = self.gerar()
        self.assertGreater(len(res["crivo"]["escritos"]), 10)
        self.assertGreater(res["crivo"]["kb"], 0)
        _, res2 = self.gerar()
        self.assertGreater(res2["crivo"]["iguais"], 10,
                           "não contou os ficheiros que ficaram como estavam")


# ---------------------------------------------------------------------------
# E o que NÃO podia mudar
# ---------------------------------------------------------------------------

class TestNaoEstragaNada(Base):

    def test_a_pagina_de_um_amigo_continua_com_noindex(self):
        """A casca mudou de sítio; o `noindex` não. É a decisão de 2026-09-29
        e a de 2026-10-02 (a raiz também)."""
        self.amigo("Gonçalves", "goncalves")
        out, _ = self.gerar()
        amigo = (out / "u" / "goncalves" / "index.html").read_text(encoding="utf-8")
        dele = (out / "u" / "baverone" / "index.html").read_text(encoding="utf-8")
        raiz = (out / "index.html").read_text(encoding="utf-8")
        self.assertIn("noindex", amigo)
        self.assertIn("noindex", raiz)
        self.assertNotIn("noindex", dele, "a página DELE é indexada, como sempre")

    def test_a_coleccao_de_cada_um_continua_a_ser_so_dele(self):
        """O crivo compara ficheiros; não pode trocar pastas."""
        self.amigo("Gonçalves", "goncalves", copias=7)
        out, _ = self.gerar()
        dele = json.loads((out / "u" / "baverone" / "api" / "index.json")
                          .read_text(encoding="utf-8"))
        amigo = json.loads((out / "u" / "goncalves" / "api" / "index.json")
                           .read_text(encoding="utf-8"))
        self.assertEqual(dele["totals"]["copies"], 3)
        self.assertEqual(amigo["totals"]["copies"], 7)

    def test_quem_fecha_a_coleccao_continua_a_perder_a_pagina(self):
        """O crivo não escreve, mas o `limpar_nao_publicadas` apaga — e tem de
        continuar a apagar: despublicar é tão fácil como publicar."""
        u = self.amigo("Gonçalves", "goncalves")
        self.amigo("Miguel", "miguel")
        out, _ = self.gerar()
        self.assertTrue((out / "u" / "goncalves").exists())
        privacidade.definir(None, u["user_id"], "nada")
        self.gerar()
        self.assertFalse((out / "u" / "goncalves").exists())


if __name__ == "__main__":
    unittest.main()

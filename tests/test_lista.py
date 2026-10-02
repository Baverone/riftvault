"""A LISTA das coleções públicas (2026-09-30).

André: *"a baverone.com tem que ter tudo / depois quando se abre o Riftbound,
vai ter lá, em modo leitura, as coleções: Baverone / Miguel / Rafa"*.

O que se prova aqui, por esta ordem:

  * com as portas fechadas (o de HOJE) o site dele não muda — a lista nem
    existe;
  * a partir de DUAS coleções públicas a raiz é a lista e a dele muda-se para
    `u/baverone/`, sem ele mexer numa chave;
  * quem tem privacidade «nada» **não aparece em sítio nenhum**, nem o nome;
  * um cartão de quem escolheu «sem-valores» não mostra um euro;
  * os favoritos antigos vão parar ao MESMO sítio — e isso corre no node,
    contra o JavaScript que a página leva mesmo.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

from riftvault import (abrir, build, collection, db, lista, multi, privacidade,
                       utilizador)
from tests import fixture

#: Um preço inconfundível: qualquer sobrevivente num cartão «sem-valores» é
#: uma fuga. A lição do `test_privacidade` — um preço pequeno em cêntimos
#: colide com uma contagem.
SENTINELA = 777701

#: Rotas que ele pode ter nos favoritos. A do meio é a mais antiga (a raiz
#: sem `#` nenhum) e a última é uma rota que AINDA NÃO EXISTE — o
#: reencaminhamento tem de a levar na mesma, senão ficava por manter.
ROTAS = ["#colecao", "#colecao/UNL", "#colecao/OGN", "#decks", "#decks/ornn",
         "#faltas-edicao/OGN", "#encomendas", "#venda", "#selado", "#inicio",
         "#a-mais", "#staples", "#uma-seccao-que-ainda-nao-existe/com/coisas"]


class Base(unittest.TestCase):

    def setUp(self):
        fixture.config_decks_sem_alt_art(self)
        self.v = fixture.Vault()
        self.addCleanup(self.v.close)
        con = self.v.connect()
        self.v.add_printing(con, "tst-001-100", "TST", 1, "Defy")
        self.v.add_printing(con, "tst-002-100", "TST", 2, "Brutalizer")
        self.v.rebuild(con)
        con.execute("INSERT OR REPLACE INTO catalog.price_latest "
                    "(printing_id, price_cents, currency, source, day) "
                    "VALUES ('tst-001-100',?,'EUR','test','2026-09-30')",
                    (SENTINELA,))
        collection.adjust(con, "tst-001-100", 3, source="test")
        con.close()
        privacidade.definir(None, utilizador.ANDRE, "tudo")

    # -- ajudas ------------------------------------------------------------

    def amigo(self, nome="Miguel", slug="miguel", publico="tudo"):
        u = utilizador.criar(nome, slug)
        con = db.connect(user_id=u["user_id"])
        collection.adjust(con, "tst-002-100", 2, source="test")
        con.close()
        privacidade.definir(None, u["user_id"], publico)
        return u

    def gerar(self, pasta="site", aberto=True):
        out = self.v.root / pasta
        build.build_todos(out, log=lambda *_: None,
                          cfg={"multi": {"aberto": aberto}})
        return out

    def texto_da_raiz(self, out: Path) -> str:
        """TUDO o que a raiz publica em texto — o HTML e o JSON da lista.

        É onde se procura o nome de quem não quis ser publicado: não basta o
        cartão não aparecer, o nome não pode estar em lado nenhum.
        """
        partes = [(out / "index.html").read_text(encoding="utf-8")]
        j = out / "api" / "lista.json"
        if j.exists():
            partes.append(j.read_text(encoding="utf-8"))
        return "\n".join(partes)


# ---------------------------------------------------------------------------
# Quem entra na lista
# ---------------------------------------------------------------------------

class TestQuemEntra(Base):

    def test_com_as_portas_fechadas_e_so_ele(self):
        self.amigo(publico="tudo")   # ele até QUER
        pub = lista.publicas({"multi": {"aberto": False}})
        self.assertEqual([e["slug"] for e in pub], [utilizador.SLUG_ANDRE])

    def test_ele_vem_sempre_primeiro(self):
        self.amigo("Ana", "ana")          # alfabeticamente antes dele
        self.amigo("Rafa", "rafa")
        pub = lista.publicas({"multi": {"aberto": True}})
        self.assertEqual(pub[0]["slug"], utilizador.SLUG_ANDRE)
        self.assertEqual([e["slug"] for e in pub[1:]], ["ana", "rafa"])

    def test_depois_dele_e_por_nome_sem_tropecar_nos_acentos(self):
        self.amigo("Zé", "ze")
        self.amigo("Álvaro", "alvaro")
        pub = lista.publicas({"multi": {"aberto": True}})
        self.assertEqual([e["slug"] for e in pub[1:]], ["alvaro", "ze"])

    def test_quem_esta_em_nada_nao_entra(self):
        self.amigo("Zeca", "zeca", publico="nada")
        pub = lista.publicas({"multi": {"aberto": True}})
        self.assertEqual([e["slug"] for e in pub], [utilizador.SLUG_ANDRE])

    def test_a_omissao_de_quem_entra_de_novo_e_ficar_de_fora(self):
        """Sem ninguém escolher nada: uma conta nova nasce privada."""
        u = utilizador.criar("Novo", "novo")
        self.assertEqual(privacidade.de(None, u["user_id"]),
                         privacidade.OMISSAO)
        pub = lista.publicas({"multi": {"aberto": True}})
        self.assertNotIn("novo", [e["slug"] for e in pub])

    def test_sem_valores_entra_na_lista(self):
        """«sem-valores» é público — o que ele esconde são os euros."""
        self.amigo("Rafa", "rafa", publico="sem-valores")
        pub = lista.publicas({"multi": {"aberto": True}})
        self.assertIn("rafa", [e["slug"] for e in pub])


# ---------------------------------------------------------------------------
# Quando é que a lista toma a raiz
# ---------------------------------------------------------------------------

class TestAraizSoMudaComDuas(Base):

    def test_uma_coleccao_nao_e_uma_lista(self):
        self.assertFalse(lista.na_raiz([{"slug": "baverone"}]))
        self.assertFalse(lista.na_raiz([]))

    def test_duas_ja_e(self):
        self.assertTrue(lista.na_raiz([{"slug": "a"}, {"slug": "b"}]))

    def test_com_as_portas_fechadas_a_raiz_continua_a_ser_a_coleccao_dele(self):
        self.amigo(publico="tudo")
        out = self.gerar(aberto=False)
        self.assertTrue((out / "api" / "index.json").exists(),
                        "a coleção dele tem de continuar na raiz")
        self.assertFalse((out / "api" / "lista.json").exists(),
                         "não pode haver lista com uma coleção só")
        self.assertFalse((out / "u").exists())

    def test_com_duas_a_raiz_passa_a_lista_e_ele_muda_se_para_u(self):
        self.amigo()
        out = self.gerar()
        self.assertTrue((out / "api" / "lista.json").exists())
        self.assertTrue((out / "u" / "baverone" / "api" / "index.json").exists(),
                        "a coleção dele tem de ficar em u/baverone/")
        self.assertTrue((out / "u" / "miguel" / "api" / "index.json").exists())
        html = (out / "index.html").read_text(encoding="utf-8")
        self.assertIn("l-grelha", html, "a raiz tem de ser a lista")

    def test_ele_nao_tem_de_mudar_chave_nenhuma(self):
        """A troca é automática: a MESMA chamada, sem argumento novo."""
        self.amigo()
        res = build.build_todos(self.v.root / "s", log=lambda *_: None,
                                cfg={"multi": {"aberto": True}})
        self.assertTrue(res["na_raiz"])

    def test_a_coleccao_dele_e_a_MESMA_so_mudou_de_sitio(self):
        """O conteúdo do site dele não muda ao passar para `u/baverone/`."""
        self.amigo()
        f = self.gerar("fechado", aberto=False)
        a = self.gerar("aberto", aberto=True)
        self.assertTrue(build.mesmo_conteudo(f, a / "u" / "baverone"),
                        "a coleção dele mudou de conteúdo ao mudar de sítio")

    def test_os_restos_do_site_dele_saem_da_raiz(self):
        """Senão ficavam lá os payloads antigos dele, a envelhecer."""
        f = self.gerar("site", aberto=False)          # a raiz é a dele
        self.assertTrue((f / "api" / "set").exists())
        self.assertTrue((f / "app.js").exists())
        self.amigo()
        build.build_todos(f, log=lambda *_: None, cfg={"multi": {"aberto": True}})
        self.assertFalse((f / "api" / "set").exists(),
                         "ficou na raiz a `api/set/` velha dele")
        self.assertFalse((f / "app.js").exists())
        self.assertTrue((f / "api" / "lista.json").exists())
        self.assertTrue((f / "u" / "baverone" / "app.js").exists())

    def test_quem_deixa_de_publicar_perde_a_pagina_QUE_JA_LA_ESTAVA(self):
        """Saltar não é apagar: despublicar tem de ser tão fácil como publicar."""
        u = self.amigo("Rafa", "rafa", publico="tudo")
        out = self.gerar()
        self.assertTrue((out / "u" / "rafa" / "api" / "index.json").exists())
        privacidade.definir(None, u["user_id"], "nada")
        build.build_todos(out, log=lambda *_: None,
                          cfg={"multi": {"aberto": True}})
        self.assertFalse((out / "u" / "rafa").exists(),
                         "a coleção dele ficou publicada depois de ele a fechar")

    def test_fechar_as_portas_tira_as_paginas_dos_amigos(self):
        self.amigo("Rafa", "rafa")
        out = self.gerar()
        self.assertTrue((out / "u" / "rafa").exists())
        build.build_todos(out, log=lambda *_: None,
                          cfg={"multi": {"aberto": False}})
        self.assertFalse((out / "u" / "rafa").exists())

    def test_voltar_a_haver_uma_so_tira_a_copia_dele_de_u(self):
        """Senão ficava em `u/baverone/` uma cópia a envelhecer — e é para lá
        que os favoritos foram reencaminhados enquanto a lista existiu."""
        u = self.amigo("Rafa", "rafa")
        out = self.gerar()
        self.assertTrue((out / "u" / "baverone").exists())
        privacidade.definir(None, u["user_id"], "nada")
        build.build_todos(out, log=lambda *_: None,
                          cfg={"multi": {"aberto": True}})
        self.assertFalse((out / "u" / "baverone").exists())
        self.assertTrue((out / "api" / "index.json").exists(),
                        "a coleção dele tem de voltar para a raiz")

    def test_o_limpar_nao_publicadas_so_mexe_dentro_do_u(self):
        out = self.v.root / "s"
        (out / "u" / "rafa").mkdir(parents=True)
        (out / "api").mkdir()
        (out / "CNAME").write_text("x", encoding="utf-8")
        lista.limpar_nao_publicadas(out, [])
        self.assertFalse((out / "u" / "rafa").exists())
        self.assertTrue((out / "api").exists())
        self.assertTrue((out / "CNAME").exists())

    def test_o_limpar_raiz_nao_leva_o_que_nao_e_nosso(self):
        """O `CNAME` do domínio e o `.nojekyll` não são nossos para apagar."""
        out = self.v.root / "s"
        (out / "u").mkdir(parents=True)
        (out / "CNAME").write_text("rift.baverone.com", encoding="utf-8")
        (out / ".nojekyll").write_text("", encoding="utf-8")
        (out / "app.js").write_text("//", encoding="utf-8")
        lista.limpar_raiz(out)
        self.assertTrue((out / "CNAME").exists())
        self.assertTrue((out / ".nojekyll").exists())
        self.assertTrue((out / "u").exists())
        self.assertFalse((out / "app.js").exists())


# ---------------------------------------------------------------------------
# A privacidade, no cartão
# ---------------------------------------------------------------------------

class TestPrivacidadeNoCartao(Base):

    def test_quem_esta_em_nada_nao_aparece_nem_o_nome(self):
        self.amigo("Rafa", "rafa", publico="tudo")     # para haver lista
        self.amigo("Zeca Escondido", "zeca", publico="nada")
        out = self.gerar()
        texto = self.texto_da_raiz(out)
        self.assertNotIn("Zeca", texto, "o NOME de quem não publica apareceu")
        self.assertNotIn("zeca", texto, "o SLUG de quem não publica apareceu")
        self.assertFalse((out / "u" / "zeca").exists())

    def test_o_cartao_de_sem_valores_nao_mostra_um_euro(self):
        self.amigo("Rafa", "rafa", publico="sem-valores")
        out = self.gerar()
        dados = json.loads((out / "api" / "lista.json").read_text(encoding="utf-8"))
        rafa = next(i for i in dados["coleccoes"] if i["slug"] == "rafa")
        self.assertIsNone(rafa["value_cents"], "o cartão levou euros")
        # E na página: nenhum «€» dentro do cartão dele.
        html = (out / "index.html").read_text(encoding="utf-8")
        cartao = re.search(r'<a class="l-cartao" href="u/rafa/".*?</a>', html,
                           re.S)
        self.assertIsNotNone(cartao, "o cartão do Rafa tem de existir")
        self.assertNotIn("€", cartao.group(0))

    def test_a_sentinela_nao_sobrevive_em_sem_valores(self):
        """A prova pela negativa está no teste a seguir."""
        con = db.connect(user_id=utilizador.ANDRE)
        con.close()
        privacidade.definir(None, utilizador.ANDRE, "sem-valores")
        self.amigo("Rafa", "rafa")
        out = self.gerar()
        texto = self.texto_da_raiz(out)
        self.assertNotIn(str(SENTINELA), texto)
        self.assertNotIn(str(SENTINELA // 100), texto)

    def test_mas_em_tudo_os_euros_APARECEM(self):
        """Sem isto o teste de cima passava com um cartão vazio."""
        self.amigo("Rafa", "rafa")
        out = self.gerar()
        dados = json.loads((out / "api" / "lista.json").read_text(encoding="utf-8"))
        dele = next(i for i in dados["coleccoes"]
                    if i["slug"] == utilizador.SLUG_ANDRE)
        self.assertEqual(dele["value_cents"], SENTINELA * 3)
        self.assertIn("€", (out / "index.html").read_text(encoding="utf-8"))

    def test_o_cartao_nao_mostra_mais_do_que_a_pagina_da_pessoa(self):
        """Os números saem do `api/index.json` JÁ GERADO dela."""
        self.amigo("Rafa", "rafa")
        out = self.gerar()
        dados = json.loads((out / "api" / "lista.json").read_text(encoding="utf-8"))
        rafa = next(i for i in dados["coleccoes"] if i["slug"] == "rafa")
        idx = json.loads((out / "u" / "rafa" / "api" / "index.json")
                         .read_text(encoding="utf-8"))
        self.assertEqual(rafa["cards"], idx["totals"]["cards"])
        self.assertEqual(rafa["copies"], idx["totals"]["copies"])
        self.assertEqual(rafa["value_cents"], idx["value"]["cents"])


# ---------------------------------------------------------------------------
# Os favoritos
# ---------------------------------------------------------------------------

class TestOsFavoritosNaoPartem(Base):

    def script(self, out: Path) -> str:
        html = (out / "index.html").read_text(encoding="utf-8")
        m = re.search(r"<script>(.*?)</script>", html, re.S)
        self.assertIsNotNone(m, "a página da lista tem de levar o reencaminhamento")
        return m.group(1)

    def test_o_reencaminhamento_vai_no_head(self):
        """No fim do `<body>` via-se a lista a piscar antes do salto."""
        self.amigo()
        html = (self.gerar() / "index.html").read_text(encoding="utf-8")
        self.assertLess(html.index("<script>"), html.index("</head>"))

    def test_e_CEGO_ao_nome_da_seccao(self):
        """Não repete a `SECCOES` do `app.js` — uma rota nova vai sozinha."""
        self.amigo()
        # OS COMENTÁRIOS NÃO CONTAM, e é preciso dizê-lo: o comentário que
        # explica esta própria decisão dá o `#colecao/UNL` como exemplo, e a
        # primeira versão deste teste apanhou-se a si própria (é a mesma
        # armadilha do `test_privacidade.test_nao_ha_sinal_de_login_no_html`).
        s = re.sub(r"/\*.*?\*/", "", self.script(self.gerar()), flags=re.S)
        for nome in ("colecao", "decks", "faltas", "encomendas", "venda",
                     "selado", "inicio"):
            self.assertNotIn(nome, s,
                             f"o reencaminhamento conhece «{nome}» — vai ficar "
                             f"velho na próxima secção")

    def test_cada_rota_antiga_acaba_no_mesmo_sitio(self):
        """Corre o JavaScript QUE A PÁGINA LEVA, no node."""
        node = shutil.which("node")
        if not node:
            self.skipTest("sem node")
        self.amigo()
        out = self.gerar()
        s = self.script(out)
        harness = """
        const rotas = JSON.parse(require('node:fs').readFileSync(0, 'utf8'));
        const saidas = {};
        for (const h of rotas) {
          let destino = null;
          globalThis.location = {
            hash: h,
            replace(u) { destino = u; },
          };
          %s
          saidas[h] = destino;
        }
        process.stdout.write(JSON.stringify(saidas));
        """ % s
        r = subprocess.run([node, "-e", harness], input=json.dumps(ROTAS),
                           capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)
        saidas = json.loads(r.stdout)
        for h in ROTAS:
            self.assertEqual(saidas[h], f"u/{utilizador.SLUG_ANDRE}/{h}",
                             f"o favorito «{h}» não foi parar ao mesmo sítio")

    def test_a_raiz_sem_hash_nao_reencaminha(self):
        """Senão ninguém chegava a ver a lista."""
        node = shutil.which("node")
        if not node:
            self.skipTest("sem node")
        self.amigo()
        s = self.script(self.gerar())
        harness = ("let d = null; globalThis.location = {hash: '', "
                   "replace(u){ d = u; }};\n" + s +
                   "\nprocess.stdout.write(JSON.stringify(d));")
        r = subprocess.run([node, "-e", harness], capture_output=True,
                           text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIsNone(json.loads(r.stdout))

    def test_usa_replace_para_o_botao_voltar_nao_ficar_preso(self):
        self.amigo()
        self.assertIn("location.replace", self.script(self.gerar()))

    def test_os_ficheiros_de_dados_NAO_se_reencaminham_e_esta_dito(self):
        """O que não se consegue fazer diz-se em vez de partir em silêncio.

        `/api/set/OGN.json` passa a viver em `u/baverone/api/…` e um endereço
        antigo para lá dá 404 — num alojamento estático não há como evitar sem
        duplicar o site inteiro. Fica escrito no módulo.
        """
        self.amigo()
        out = self.gerar()
        self.assertFalse((out / "api" / "set" / "TST.json").exists())
        self.assertIn("404", lista.__doc__)
        self.assertIn("api/set", lista.__doc__)


# ---------------------------------------------------------------------------
# A página aguenta zero, uma e muitas
# ---------------------------------------------------------------------------

class TestAPaginaAguenta(Base):

    def pagina(self, n: int) -> str:
        pub = [{"user_id": i + 1, "slug": f"p{i}", "nome": f"Pessoa {i}",
                "publico": "tudo"} for i in range(n)]
        return lista.html({"na_raiz": True, "dele": utilizador.SLUG_ANDRE,
                           "coleccoes": [{**e, "url": f"u/{e['slug']}/",
                                          "cards": 10, "copies": 30,
                                          "printings": 12, "playset_done": 8,
                                          "playset_total": 10,
                                          "playset_pct": 80.0,
                                          "value_cents": 1234} for e in pub]})

    def test_zero_diz_o_que_se_passa_em_vez_de_ficar_em_branco(self):
        html = self.pagina(0)
        self.assertIn("Ainda não há nenhuma coleção pública", html)
        # A CLASSE está sempre no CSS; o que não pode existir é a grelha.
        self.assertNotIn('<div class="l-grelha">', html)

    def test_uma_no_singular(self):
        self.assertIn("1 coleção ·", self.pagina(1))

    def test_cinco_cabem_na_grelha(self):
        html = self.pagina(5)
        self.assertEqual(html.count('class="l-cartao"'), 5)
        self.assertIn("5 coleções", html)

    def test_no_telemovel_a_grelha_passa_a_uma_coluna(self):
        html = self.pagina(5)
        self.assertIn("max-width: 480px", html)
        self.assertIn("grid-template-columns: 1fr", html)

    def test_a_grelha_envolve_sozinha_e_nao_corre_para_o_lado(self):
        """A lição das filas de botões de 2026-09-24."""
        html = self.pagina(5)
        self.assertIn("auto-fill", html)
        self.assertNotIn("overflow-x", html)

    def test_leva_o_viewport(self):
        self.assertIn('name="viewport"', self.pagina(2))

    def test_os_plurais(self):
        """«1 carta», e não «1 cartas» — a revisão de 2026-09-09 outra vez."""
        um = lista.html({"na_raiz": True, "dele": "baverone", "coleccoes": [
            {"slug": "x", "nome": "X", "publico": "tudo", "url": "u/x/",
             "cards": 1, "copies": 1, "printings": 1, "playset_done": 0,
             "playset_total": 928, "playset_pct": 0.0, "value_cents": 11}]})
        self.assertIn("1 carta ·", um)
        self.assertIn("1 cópia<", um)
        self.assertNotIn("1 cartas", um)
        self.assertNotIn("1 cópias", um)
        muitos = self.pagina(1)
        self.assertIn("10 cartas", muitos)
        self.assertIn("30 cópias", muitos)

    def test_um_nome_com_html_dentro_nao_escapa(self):
        html = lista.html({
            "na_raiz": True, "dele": "baverone",
            "coleccoes": [{"slug": "x", "nome": "<script>mau()</script>",
                           "publico": "tudo", "url": "u/x/", "cards": 1,
                           "copies": 1, "printings": 1, "playset_done": 1,
                           "playset_total": 1, "playset_pct": 100.0,
                           "value_cents": None}]})
        self.assertNotIn("<script>mau()", html)
        self.assertIn("&lt;script&gt;", html)

    def test_uma_coleccao_por_gerar_nao_rebenta_a_lista(self):
        vazio = self.v.root / "nao-existe"
        c = lista.cartao(vazio, {"slug": "x", "publico": "tudo"})
        self.assertIsNone(c["cards"])
        self.assertIn("coleção por gerar", lista.html(
            {"na_raiz": True, "dele": "baverone",
             "coleccoes": [{**c, "slug": "x", "nome": "X", "url": "u/x/"}]}))


# ---------------------------------------------------------------------------
# Não estraga nada do que já havia
# ---------------------------------------------------------------------------

class TestNaoEstragaNada(Base):

    def test_com_as_portas_fechadas_o_build_todos_e_o_build_dao_o_MESMO(self):
        """Checklist 1: hoje o site dele não muda um byte."""
        self.amigo(publico="tudo")
        a = self.v.root / "so-ele"
        b = self.v.root / "todos"
        build.build(a, log=lambda *_: None, user_id=utilizador.ANDRE)
        build.build_todos(b, log=lambda *_: None,
                          cfg={"multi": {"aberto": False}})
        self.assertTrue(build.mesmo_conteudo(a, b))

    def test_o_cli_gera_pela_porta_que_respeita_as_portas_e_a_lista(self):
        fonte = Path(__file__).resolve().parents[1] / "riftvault" / "cli.py"
        texto = fonte.read_text(encoding="utf-8")
        m = re.search(r"def cmd_build\(.*?\n\ndef ", texto, re.S)
        self.assertIsNotNone(m)
        self.assertIn("build_todos", m.group(0),
                      "o `riftvault build` tem de passar pelo `build_todos` — "
                      "senão a lista nunca chega ao site a sério")

    def test_a_pasta_de_prova_do_se_mudou_fica_FORA_do_site(self):
        """Uma corrida interrompida não pode deixar lixo no que se publica."""
        fonte = Path(__file__).resolve().parents[1] / "riftvault" / "build.py"
        texto = fonte.read_text(encoding="utf-8")
        self.assertIn('prova = config.ROOT / (out.name + "-prova")', texto)
        self.assertNotIn('prova = out.parent /', texto)

    def test_nenhum_modulo_de_contas_conhece_a_lista(self):
        """A lista é apresentação: não pode entrar em conta nenhuma."""
        raiz = Path(__file__).resolve().parents[1] / "riftvault"
        podem = {"build.py", "lista.py", "cli.py", "server.py"}
        for p in raiz.glob("*.py"):
            if p.name in podem:
                continue
            texto = p.read_text(encoding="utf-8")
            self.assertNotIn("import lista", texto, p.name)
            self.assertNotIn("from . import lista", texto, p.name)

    def test_ler_a_lista_nao_escreve_na_coleccao_de_ninguem(self):
        self.amigo()

        def fotografia():
            f = {}
            for uid in (utilizador.ANDRE, 2):
                con = db.connect(user_id=uid)
                try:
                    f[uid] = (
                        con.execute("SELECT COUNT(*) FROM ops").fetchone()[0],
                        sorted(tuple(r) for r in
                               con.execute("SELECT printing_id, qty, qty_foil "
                                           "FROM copies")))
                finally:
                    con.close()
            return f

        antes = fotografia()
        lista.publicas({"multi": {"aberto": True}})
        lista.payload(self.gerar(), cfg={"multi": {"aberto": True}})
        self.assertEqual(fotografia(), antes)


# ---------------------------------------------------------------------------
# A RAIZ NÃO SE INDEXA (2026-10-02)
# ---------------------------------------------------------------------------
#
# O varrimento de 2026-10-01 mediu-o ao vivo: `rift.baverone.com` respondia
# 200 com «Miguel Valente» e «Gonçalves» no HTML, com o valor da coleção de
# cada um, e sem `<meta name="robots">` — era a ÚNICA página do site assim (a
# de cada um deles já levava a marca; a dele não leva de propósito).
#
# Tudo o que está aqui lê o ficheiro que SAI do `build_todos`, nunca um pedaço
# de HTML montado à mão: o defeito era precisamente uma página que a função que
# marca nunca chegava a ver.

class TestARaizNaoSeIndexa(Base):

    def raiz_com_dois(self) -> Path:
        """Duas coleções públicas — é o estado em que a raiz é a lista."""
        self.amigo(nome="Miguel Valente", slug="miguel")
        return self.gerar()

    # -- o defeito --------------------------------------------------------

    def test_a_raiz_GERADA_leva_a_marca(self):
        out = self.raiz_com_dois()
        pagina = (out / "index.html").read_text(encoding="utf-8")
        # Que é mesmo a lista, e não a coleção dele por a troca não ter dado.
        self.assertIn('class="l-cartao"', pagina)
        self.assertIn('name="robots"', pagina)
        self.assertIn("noindex", pagina)

    def test_a_pagina_que_NOMEIA_as_pessoas_e_a_que_tem_de_estar_marcada(self):
        """O nome e o euro estão lá — e a marca também, no mesmo ficheiro."""
        out = self.raiz_com_dois()
        pagina = (out / "index.html").read_text(encoding="utf-8")
        self.assertIn("Miguel Valente", pagina)
        self.assertIn("€", pagina)
        self.assertIn("noindex", pagina)

    def test_a_marca_e_a_MESMA_das_paginas_de_cada_um(self):
        """Uma maneira de dizer, não duas: o literal vive no `abrir`."""
        out = self.raiz_com_dois()
        raiz = (out / "index.html").read_text(encoding="utf-8")
        amigo = (out / "u" / "miguel" / "index.html").read_text(encoding="utf-8")
        self.assertIn(abrir.META, raiz)
        self.assertIn(abrir.META, amigo)

    def test_vai_no_head_e_nao_depois_do_corpo(self):
        out = self.raiz_com_dois()
        pagina = (out / "index.html").read_text(encoding="utf-8")
        self.assertLess(pagina.index('name="robots"'), pagina.index("</head>"))

    def test_o_reencaminhamento_dos_favoritos_sobreviveu_a_marca(self):
        """Os dois vivem no `<head>`: a marca não pode ter empurrado o script."""
        out = self.raiz_com_dois()
        pagina = (out / "index.html").read_text(encoding="utf-8")
        cabeca = pagina[:pagina.index("</head>")]
        self.assertIn("location.replace", cabeca)
        self.assertIn('name="robots"', cabeca)

    def test_quem_decide_e_o_abrir_e_nao_um_literal_no_lista(self):
        fonte = Path(__file__).resolve().parents[1] / "riftvault" / "lista.py"
        texto = fonte.read_text(encoding="utf-8")
        self.assertIn("abrir.lista_indexavel", texto)
        self.assertIn("abrir.marcar_html", texto)
        # A etiqueta não se escreve aqui: se um dia ele quiser indexar a lista,
        # é UMA função no `abrir.py` e não uma caça ao literal.
        self.assertNotIn('<meta name="robots"', texto)

    def test_marcar_duas_vezes_nao_dobra_a_etiqueta(self):
        out = self.raiz_com_dois()
        pagina = (out / "index.html").read_text(encoding="utf-8")
        self.assertEqual(pagina.count('name="robots"'), 1)
        self.assertEqual(abrir.marcar_html(pagina), pagina)

    # -- o que NÃO podia mudar -------------------------------------------

    def test_a_pagina_DELE_continua_sem_marca(self):
        """A correcção de 2026-09-29 já se apanhou a despublicar o site dele.

        `publico_indexavel` exigia a porta aberta e metia `noindex` na página
        do próprio dono. Isto fixa que a de hoje não repete o erro: a lista
        marca-se, a dele não.
        """
        out = self.raiz_com_dois()
        dele = (out / "u" / "baverone" / "index.html").read_text(encoding="utf-8")
        self.assertNotIn('name="robots"', dele)
        self.assertTrue(abrir.publico_indexavel(dono=True))

    def test_com_uma_coleccao_so_a_raiz_e_a_DELE_e_continua_sem_marca(self):
        """Com as portas fechadas (o de hoje) nada disto se vê."""
        out = self.gerar(aberto=False)
        pagina = (out / "index.html").read_text(encoding="utf-8")
        self.assertNotIn('class="l-cartao"', pagina)   # não é a lista
        self.assertNotIn('name="robots"', pagina)

    def test_a_pagina_de_cada_amigo_continua_marcada(self):
        out = self.raiz_com_dois()
        for slug in ("miguel",):
            p = (out / "u" / slug / "index.html").read_text(encoding="utf-8")
            self.assertIn("noindex", p, slug)

    # -- a rede: nenhuma página gerada nomeia pessoas sem a marca ---------

    def test_NENHUMA_pagina_gerada_nomeia_uma_pessoa_sem_a_marca(self):
        """Varre o site todo — não é uma amostra.

        É a pergunta do ponto 4 da ordem feita em teste, para a resposta não
        envelhecer: uma página nova que nomeie alguém e saia sem marca dá
        vermelho aqui.
        """
        self.amigo(nome="Miguel Valente", slug="miguel")
        self.amigo(nome="Gonçalves", slug="goncalves")
        out = self.gerar()
        nomes = ["Miguel Valente", "Gonçalves"]
        vistas = 0
        for p in sorted(out.rglob("*.html")):
            texto = p.read_text(encoding="utf-8")
            quais = [n for n in nomes if n in texto]
            if not quais:
                continue
            vistas += 1
            self.assertIn('name="robots"', texto,
                          f"{p.relative_to(out)} nomeia {quais} e não leva "
                          f"`noindex`")
        # Prova pela negativa: se o varrimento não encontrasse página nenhuma
        # com nomes, passava sempre e não valia nada.
        self.assertGreaterEqual(vistas, 1)

    def test_o_noindex_nao_vale_para_o_JSON_e_isso_esta_dito(self):
        """O que ele escolheu NÃO fecha: os payloads continuam legíveis.

        Uma etiqueta de HTML não marca um `.json`, e fechá-los pedia um
        `robots.txt` na raiz — hipótese que ele viu e não escolheu. Fica fixado
        para ninguém ler esta ordem como «o site está fechado aos motores».
        """
        out = self.raiz_com_dois()
        j = (out / "api" / "lista.json").read_text(encoding="utf-8")
        self.assertIn("Miguel Valente", j)
        self.assertNotIn("robots", j)
        fonte = Path(__file__).resolve().parents[1] / "riftvault" / "lista.py"
        self.assertIn("api/lista.json",
                      fonte.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

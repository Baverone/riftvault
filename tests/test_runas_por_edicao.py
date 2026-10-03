"""A contagem das runas é de CADA EDIÇÃO (André, 2026-10-01).

Palavras dele: *"A contagem das runas Alt.Art é exclusiva para cada edição /
vi que a contagem está a ser partilhada por todas as edições"*.

O que estava mal: o bloco «Runas — 12 de cada» somava num número só as
impressões das CINCO edições e repetia-o em todas. Medido no `data/` real:
na página do OGN a Calm Rune dizia «na coleção: 21», e 12 dessas eram as
`SFD-R02a` do CardTrader; na do UNL dizia o mesmo 21 sem ele ter lá uma única
runa; e o OGS, que não tem runas nenhumas, levava o bloco inteiro.

O que se fixa aqui: `payload()["por_edicao"]` dá, por edição, as runas dela,
as origens dela, o total dela e o tile dela; a soma do topo (`runas`/`totals`)
não mexeu — é o que o separador «Todas» mostra, e é a única vista em que o
número somado está certo; uma edição sem runas não entra; e o CONTADOR DELE
continua a ser um por runa, de propósito e dito no ecrã.

Tudo contra pastas temporárias (`tests.fixture.Vault`) e um config que não
existe: o `data/` e o `riftvault_config.json` a sério nunca são tocados.
"""

from __future__ import annotations

import importlib
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.fixture import REPO, Vault, config_decks_sem_alt_art  # noqa: E402

config_decks_sem_alt_art()


def _config(caso, extra: dict | None = None) -> None:
    caminho = Path(tempfile.gettempdir()) / f"riftvault-runas-edicao-{os.getpid()}.json"
    caminho.write_text(json.dumps({
        "decks": {"so_base": False,
                  "so_normais_excepto": ["legend", "champion"],
                  "versoes_especiais": ["a", "overnumbered", "promo"]},
        **(extra or {})}), encoding="utf-8")
    os.environ["RIFTVAULT_CONFIG"] = str(caminho)
    caso.addCleanup(lambda: os.environ.pop("RIFTVAULT_CONFIG", None))
    from riftvault import config
    importlib.reload(config)
    config.load.cache_clear()


class Base(unittest.TestCase):
    def setUp(self):
        config_decks_sem_alt_art(self)
        self.v = Vault()
        self.addCleanup(self.v.close)
        from riftvault import metrics, runas_vista
        for m in (metrics, runas_vista):
            importlib.reload(m)
        self.metrics, self.rv = metrics, runas_vista

    def catalogo(self):
        """A Calm Rune nas quatro edições e a Fury Rune só no OGN; o OGS com
        uma Unit e nenhuma runa — é a forma do catálogo real.

        OGN: base 9 + alt art 6 (retirada) = 15
        SFD: só CardTrader — base 2 + alt art 12 (retirada) = 14
        UNL: só CardTrader — alt art 5 (retirada) = 5
        VEN: promo escondida 1 = 1
        """
        from riftvault import collection
        con = self.v.connect()
        v = self.v
        v.add_printing(con, "ogn-001-100", "OGN", 1, "Defy", size=100)
        v.add_printing(con, "ogs-001-20", "OGS", 1, "Starter Unit", size=20)
        v.add_printing(con, "ogn-042-100", "OGN", 42, "Calm Rune", card_type="Rune",
                       size=100)
        v.add_printing(con, "ogn-042a-100", "OGN", 42, "Calm Rune", card_type="Rune",
                       variant="a", kind="alt_art", rarity="showcase", size=100)
        v.add_printing(con, "ogn-007-100", "OGN", 7, "Fury Rune", card_type="Rune",
                       size=100)
        v.add_printing(con, "ven-r02", "VEN", 2, "Calm Rune", card_type="Rune",
                       variant="r02", kind="rune_promo", lane="r", codigo="VEN-R02")
        v.rebuild(con)
        for pid, sid, raw, version in (("ct-1", "SFD", "R02", "SFD"),
                                       ("ct-2", "SFD", "R02", "SFD | Alternate Art"),
                                       ("ct-3", "UNL", "R02a", "UNL | Alternate Art")):
            con.execute(
                "INSERT INTO catalog.market_only (printing_id, blueprint_id, set_id, "
                "collector_raw, card_key, market_name, market_set, version, image_url) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (pid, int(pid[3:]), sid, raw, "calm rune", "Calm Rune", sid, version,
                 f"https://cdn.example/{pid}.png"))
        collection.adjust(con, "ogn-042-100", 9, source="test")
        collection.adjust(con, "ogn-042a-100", 6, source="test")
        collection.adjust(con, "ogn-007-100", 3, source="test")
        collection.adjust(con, "ven-r02", 1, source="test")
        collection.adjust(con, "ct-1", 2, source="test")
        collection.adjust(con, "ct-2", 12, source="test")
        collection.adjust(con, "ct-3", 5, source="test")
        return con

    def ed(self, p, sid):
        return p["por_edicao"][sid]

    def runa(self, vista, nome):
        return next(x for x in vista["runas"] if x["name"] == nome)


class TestCadaEdicaoRespondePorSi(Base):
    """O número que ele vê na página de uma edição é o DESSA edição."""

    def test_o_payload_traz_uma_entrada_por_edicao_com_runas(self):
        con = self.catalogo()
        p = self.rv.payload(con)
        self.assertEqual(list(p["por_edicao"]), ["OGN", "SFD", "UNL", "VEN"])
        for sid, e in p["por_edicao"].items():
            self.assertEqual(e["set_id"], sid)
        con.close()

    def test_a_calm_rune_conta_so_as_impressoes_da_edicao_aberta(self):
        """O defeito, carta a carta: 15 no OGN, 14 no SFD, 5 no UNL, 1 no
        VEN — e nunca os 35 somados que todas diziam."""
        con = self.catalogo()
        p = self.rv.payload(con)
        esperado = {"OGN": 15, "SFD": 14, "UNL": 5, "VEN": 1}
        for sid, n in esperado.items():
            self.assertEqual(self.runa(self.ed(p, sid), "Calm Rune")["total"], n,
                             f"a Calm Rune do {sid}")
        self.assertEqual(self.runa(p, "Calm Rune")["total"], 35,
                         "a soma do topo é que leva as quatro edições")
        con.close()

    def test_as_origens_de_uma_edicao_sao_so_dela(self):
        """O que estava mal visto de outro lado: a linha do OGN listava as
        `SFD-R02a` entre as origens dela."""
        con = self.catalogo()
        p = self.rv.payload(con)
        codigos = {sid: [o["code"] for o in self.runa(self.ed(p, sid), "Calm Rune")["origens"]]
                   for sid in ("OGN", "SFD", "UNL", "VEN")}
        self.assertEqual(codigos["OGN"], ["OGN-042/100", "OGN-042a/100"])
        self.assertEqual(codigos["SFD"], ["SFD-R02", "SFD-R02a"])
        self.assertEqual(codigos["UNL"], ["UNL-R02a"])
        self.assertEqual(codigos["VEN"], ["VEN-R02"])
        for sid, cs in codigos.items():
            for c in cs:
                self.assertTrue(c.startswith(sid), f"{c} apareceu no {sid}")
        con.close()

    def test_a_runa_que_a_edicao_nao_tem_nao_aparece(self):
        """A Fury Rune só existe no OGN: no SFD a edição tem uma runa só."""
        con = self.catalogo()
        p = self.rv.payload(con)
        self.assertEqual([x["name"] for x in self.ed(p, "OGN")["runas"]],
                         ["Calm Rune", "Fury Rune"])
        for sid in ("SFD", "UNL", "VEN"):
            self.assertEqual([x["name"] for x in self.ed(p, sid)["runas"]], ["Calm Rune"])
            self.assertEqual(self.ed(p, sid)["totals"]["cards"], 1)
        self.assertEqual(self.ed(p, "OGN")["totals"]["cards"], 2)
        con.close()

    def test_a_edicao_sem_runas_nao_leva_bloco(self):
        """O OGS não tem runa nenhuma — e levava as seis das outras."""
        con = self.catalogo()
        p = self.rv.payload(con)
        self.assertNotIn("OGS", p["por_edicao"])
        self.assertNotIn("OGS", self.rv.edicoes(self.rv._na_colecao(con, self.rv.config.load())))
        con.close()

    def test_o_tile_de_cada_edicao_e_a_impressao_dela(self):
        """A imagem e o código do tile: no OGN a base da sequência, no SFD a
        base do CardTrader, e onde só há alt art é essa."""
        con = self.catalogo()
        p = self.rv.payload(con)
        self.assertEqual(self.runa(self.ed(p, "OGN"), "Calm Rune")["code"], "OGN-042/100")
        self.assertEqual(self.runa(self.ed(p, "SFD"), "Calm Rune")["code"], "SFD-R02")
        self.assertEqual(self.runa(self.ed(p, "UNL"), "Calm Rune")["code"], "UNL-R02a")
        self.assertEqual(self.runa(self.ed(p, "VEN"), "Calm Rune")["code"], "VEN-R02")
        # Fora do catálogo não há imagem em cache — só o CDN, como no Pimp.
        sfd = self.runa(self.ed(p, "SFD"), "Calm Rune")
        self.assertIsNone(sfd["img"])
        self.assertEqual(sfd["cdn"], "https://cdn.example/ct-1.png")
        self.assertEqual(self.runa(self.ed(p, "OGN"), "Calm Rune")["img"],
                         "img/ogn-042-100.webp")
        con.close()

    def test_o_sem_retiradas_e_da_edicao(self):
        """No OGN 9 das 15 não são retiradas; no SFD só a base (2); no UNL
        nenhuma (as 5 são alt art)."""
        con = self.catalogo()
        p = self.rv.payload(con)
        esperado = {"OGN": (15, 9), "SFD": (14, 2), "UNL": (5, 0), "VEN": (1, 1)}
        for sid, (total, sem) in esperado.items():
            x = self.runa(self.ed(p, sid), "Calm Rune")
            self.assertEqual((x["total"], x["sem_retiradas"]), (total, sem), sid)
        con.close()

    def test_os_totais_de_cada_edicao_somam_as_runas_dela(self):
        con = self.catalogo()
        p = self.rv.payload(con)
        for sid, e in p["por_edicao"].items():
            self.assertEqual(e["totals"]["total"],
                             sum(x["total"] for x in e["runas"]), sid)
            self.assertEqual(e["totals"]["sem_retiradas"],
                             sum(x["sem_retiradas"] for x in e["runas"]), sid)
            self.assertEqual(e["totals"]["alvo"], p["alvo"] * e["totals"]["cards"], sid)
        con.close()

    def test_a_soma_das_edicoes_e_o_total_do_topo(self):
        """A conta tem de fechar: cada impressão está em uma edição e uma
        só."""
        con = self.catalogo()
        p = self.rv.payload(con)
        for campo in ("total", "sem_retiradas"):
            self.assertEqual(sum(e["totals"][campo] for e in p["por_edicao"].values()),
                             p["totals"][campo], campo)
        con.close()


class TestASomaNaoMexeu(Base):
    """O topo do payload — o que o separador «Todas» mostra — é o mesmo de
    antes desta correcção. A fatia é vista nova, não um número novo."""

    def test_o_topo_continua_a_somar_as_edicoes_todas(self):
        con = self.catalogo()
        p = self.rv.payload(con)
        calm = self.runa(p, "Calm Rune")
        self.assertEqual(calm["total"], 35)
        self.assertEqual(calm["sem_retiradas"], 12)   # 9 do OGN + 2 do SFD + 1 do VEN
        # A ordem é a de sempre: a sequência primeiro, depois o que o site
        # ainda conta (a promo escondida), depois as retiradas, e o CardTrader
        # no fim de cada grupo.
        self.assertEqual([o["code"] for o in calm["origens"]],
                         ["OGN-042/100", "VEN-R02", "SFD-R02", "OGN-042a/100",
                          "SFD-R02a", "UNL-R02a"])
        self.assertEqual(p["totals"]["total"], 38)    # + as 3 Fury Rune
        self.assertEqual(p["totals"]["cards"], 2)
        con.close()

    def test_o_tile_do_topo_continua_a_ser_a_base_do_ogn(self):
        con = self.catalogo()
        calm = self.runa(self.rv.payload(con), "Calm Rune")
        self.assertEqual(calm["code"], "OGN-042/100")
        self.assertEqual(calm["img"], "img/ogn-042-100.webp")
        con.close()

    def test_a_referencia_global_nao_leva_a_marca_interna(self):
        """O `_todas` é a mecânica do recorte e não vai para o JSON."""
        con = self.catalogo()
        p = self.rv.payload(con)
        for vista in [p, *p["por_edicao"].values()]:
            for x in vista["runas"]:
                self.assertNotIn("_todas", x)
        json.dumps(p)   # tem de ser serializável como sempre foi
        con.close()


class TestOContadorPassouASerPorEdicao(Base):
    """A decisão que ficou por tomar a 02/10 e que ele tomou a 03/10: *"Zera
    e recontas por edicao"*. A chave passou a `(card_key, set_id)`, começa a
    zero e não há sementeira — o número é o que ELE conta daquela edição."""

    def test_a_tabela_passou_a_ter_edicao_na_chave(self):
        con = self.catalogo()
        self.rv.payload(con)
        cols = [r[1] for r in con.execute("PRAGMA table_info(rune_counter)")]
        self.assertIn("set_id", cols)
        self.assertIn("card_key", cols)
        pk = [r[1] for r in con.execute("PRAGMA table_info(rune_counter)") if r[5]]
        self.assertEqual(sorted(pk), ["card_key", "set_id"])
        con.close()

    def test_o_contador_e_SO_da_edicao_onde_ele_carregou(self):
        """O que estava mal: o número do OGN aparecia no SFD. Agora um `+` no
        OGN deixa as outras três a zero."""
        con = self.catalogo()
        self.rv.ajustar(con, "calm rune", "OGN", 7)
        p = self.rv.payload(con)
        self.assertEqual(self.runa(self.ed(p, "OGN"), "Calm Rune")["contador"], 7)
        for sid in ("SFD", "UNL", "VEN"):
            self.assertEqual(self.runa(self.ed(p, sid), "Calm Rune")["contador"], 0,
                             f"o número do OGN apareceu no {sid}")
        # Em «Todas» é a SOMA das quatro.
        self.assertEqual(self.runa(p, "Calm Rune")["contador"], 7)
        self.rv.ajustar(con, "calm rune", "SFD", 2)
        p = self.rv.payload(con)
        self.assertEqual(self.runa(p, "Calm Rune")["contador"], 9)
        self.assertEqual(p["totals"]["contador"], 9)
        con.close()

    def test_comeca_a_zero_e_nao_ha_sementeira(self):
        """A sementeira era o contrário do que ele pediu: punha 15 no OGN
        quando ele tinha contado 3 ao todo."""
        con = self.catalogo()
        p = self.rv.payload(con)
        self.assertEqual(
            [tuple(r) for r in con.execute("SELECT * FROM rune_counter")], [],
            "ler o bloco gravou linhas — a sementeira tinha de ter saído")
        for sid, e in p["por_edicao"].items():
            self.assertEqual(e["totals"]["contador"], 0, sid)
        self.assertEqual(p["totals"]["contador"], 0)
        con.close()

    def test_o_alvo_conta_celulas_runa_vezes_edicao(self):
        """12 por runa e por edição: OGN 2 células, SFD/UNL/VEN 1 cada."""
        con = self.catalogo()
        p = self.rv.payload(con)
        self.assertEqual(self.ed(p, "OGN")["totals"]["alvo"], 24)
        for sid in ("SFD", "UNL", "VEN"):
            self.assertEqual(self.ed(p, sid)["totals"]["alvo"], 12, sid)
        # «Todas» é a soma das quatro (5 células), não 12 × 6 runas.
        self.assertEqual((p["totals"]["celulas"], p["totals"]["alvo"]), (5, 60))
        con.close()

    def test_o_ajustar_devolve_os_totais_das_duas_vistas(self):
        """Uma aritmética só: o cabeçalho de cada edição mostra o contador, e
        é o servidor que o soma."""
        con = self.catalogo()
        self.rv.ajustar(con, "calm rune", "SFD", 5)
        res = self.rv.ajustar(con, "calm rune", "SFD", -2)
        self.assertEqual(res["qty"], 3)
        self.assertEqual(sorted(res["totals_por_edicao"]), ["OGN", "SFD", "UNL", "VEN"])
        self.assertEqual(res["totals_por_edicao"]["SFD"]["total"], 14)
        self.assertEqual(res["totals_por_edicao"]["SFD"]["contador"], 3)
        self.assertEqual(res["totals_por_edicao"]["OGN"]["contador"], 0)
        self.assertEqual(res["totals"]["total"], 38)
        self.assertEqual(res["totals"]["contador"], 3)
        con.close()

    def test_mexer_no_contador_nao_mexe_na_referencia_de_edicao_nenhuma(self):
        con = self.catalogo()
        antes = {sid: e["totals"]["total"] for sid, e in
                 self.rv.payload(con)["por_edicao"].items()}
        for ck, sid in (("calm rune", "OGN"), ("calm rune", "SFD"),
                        ("calm rune", "UNL"), ("calm rune", "VEN"),
                        ("fury rune", "OGN")):
            self.rv.ajustar(con, ck, sid, 99)
        depois = {sid: e["totals"]["total"] for sid, e in
                  self.rv.payload(con)["por_edicao"].items()}
        self.assertEqual(antes, depois)
        con.close()


#: As chaves que mudam sozinhas com o tempo e nao sao contabilidade nenhuma.
#: Tirar-se-iam uma a uma, mas a fotografia e' feita de payloads inteiros e um
#: deles pode ganhar outra amanha — por isso a lista e explicita e o teste
#: `test_a_fotografia_nao_tem_relogio` exige que nenhuma sobre.
RELOGIOS = ("generated_at", "synced_at", "updated_at", "as_of", "quando", "ts")


def sem_relogio(obj):
    """O mesmo objecto sem as chaves que andam com o relogio (2026-10-02).

    O merge de 02/10 parou com duas fotografias a diferir em UM SEGUNDO
    (`...:24:28` contra `...:24:27`): o `index_payload` traz um `generated_at`,
    e as duas tiram-se em momentos diferentes. Um teste que pergunta «mudou
    alguma conta?» nao pode ter o relogio dentro da conta — ou passa conforme
    calhe, que e pior do que falhar sempre.
    """
    if isinstance(obj, dict):
        return {k: sem_relogio(v) for k, v in obj.items() if k not in RELOGIOS}
    if isinstance(obj, (list, tuple)):
        return type(obj)(sem_relogio(x) for x in obj)
    return obj


class TestNaoMexeEmNumeroNenhumDoResto(Base):
    """A regra do bloco desde 2026-09-19 fica de pé: isto não conta para
    nada. A fatia por edição é vista, não contabilidade."""

    def fotografia(self, con):
        from riftvault import a_mais, a_subir, faltas_edicao, metrics, prices
        cfg = self.rv.config.load()
        bruto = {
            "niveis": metrics.niveis_payload(con, cfg),
            "index": metrics.index_payload(con, cfg),
            "wantlist": a_subir.wantlist(con),
            "faltas": faltas_edicao.payload(con, cfg)["totals"],
            "a_mais": a_mais.payload(con, cfg)["totals"],
            "valor": prices.collection_value(con),
            "sets": {sid: metrics.set_payload(con, sid, cfg)["progress"]
                     for sid in ("OGN", "OGS", "SFD", "UNL", "VEN")},
            "copies": sorted(tuple(r) for r in
                             con.execute("SELECT printing_id, qty, qty_foil FROM copies")),
        }
        return sem_relogio(bruto)

    def test_o_bloco_por_edicao_nao_mexe_em_conta_nenhuma(self):
        con = self.catalogo()
        antes = self.fotografia(con)
        p = self.rv.payload(con)
        self.assertTrue(p["por_edicao"], "a fotografia não vale com o bloco vazio")
        for ck, sid in (("calm rune", "OGN"), ("calm rune", "SFD"),
                        ("fury rune", "OGN")):
            self.rv.ajustar(con, ck, sid, 40)
        self.assertEqual(self.fotografia(con), antes)
        con.close()

    def test_a_fotografia_nao_e_de_zeros(self):
        """A prova pela negativa: se ela não detectasse uma mudança, o teste
        de cima passava com qualquer coisa."""
        from riftvault import collection
        con = self.catalogo()
        antes = self.fotografia(con)
        collection.adjust(con, "ogn-001-100", 2, source="test")
        self.assertNotEqual(self.fotografia(con), antes)
        con.close()

    def test_a_fotografia_nao_tem_relogio(self):
        """Nenhuma chave de tempo sobra — senao o teste de cima volta a passar
        ou falhar conforme o segundo em que calhe (02/10/2026)."""
        import json as _json
        con = self.catalogo()
        texto = _json.dumps(self.fotografia(con), default=str)
        for chave in RELOGIOS:
            self.assertNotIn('"%s"' % chave, texto,
                             "a fotografia voltou a levar o relogio dentro")
        con.close()

    def test_o_payload_da_edicao_nao_traz_o_bloco(self):
        con = self.catalogo()
        sp = self.metrics.set_payload(con, "OGN", self.rv.config.load())
        for proibido in ("runas", "por_edicao", "rune_counter"):
            self.assertNotIn(proibido, sp)
        con.close()


class TestFrontend(Base):
    JS = (REPO / "riftvault" / "web" / "app.js").read_text(encoding="utf-8")

    def corpo(self, nome):
        m = re.search(rf"function {nome}\((.*?)\) \{{(.*?)\n\}}\n", self.JS, re.S)
        self.assertIsNotNone(m, f"não encontrei o `{nome}` no app.js")
        return m.group(2)

    def test_o_bloco_desenha_a_fatia_da_edicao_aberta(self):
        corpo = self.corpo("runasDaEdicao")
        self.assertIn("edicaoAberta()", corpo)
        self.assertIn("p.por_edicao[sid]", corpo)
        # Em «Todas» (sem edição aberta) é a soma do topo.
        self.assertIn("p.runas", corpo)
        desenho = re.search(r"async function renderRunasVista\(reler = false\) \{(.*?)\n\}\n",
                            self.JS, re.S).group(1)
        self.assertIn("runasDaEdicao()", desenho)
        self.assertIn("v.runas.map(x => runaTile(x, v))", desenho)

    def test_um_payload_antigo_nao_parte_o_ecra(self):
        """O 8770 não se reinicia a cada merge: um payload sem `por_edicao`
        volta a ser a soma, como era."""
        corpo = self.corpo("runasDaEdicao")
        self.assertIn("!p.por_edicao", corpo)

    def test_o_cabecalho_diz_de_que_edicao_e_o_contador(self):
        corpo = self.corpo("runasHead")
        self.assertIn("v.set_id", corpo)
        self.assertIn("nesta edição", corpo)
        self.assertIn("o teu contador de ", corpo)
        # Em «Todas» di-lo, senão o 288 lia-se como um alvo por runa.
        self.assertIn("a soma do teu contador nas edições todas", corpo)

    def test_o_contador_anda_SO_na_edicao_e_na_soma(self):
        """2026-10-03: é um por (runa, edição). Um `+` no OGN muda o OGN e a
        soma de «Todas», e NÃO toca no SFD."""
        corpo = self.corpo("runaPorContador")
        self.assertIn("(p.por_edicao || {})[sid]", corpo)
        self.assertIn("p.runas", corpo)
        self.assertNotIn("runasListas", self.JS,
                         "a lista que punha o número em todas as edições saiu")
        ajustar = re.search(r"async function runaAjustar\(ck, sid, delta\) \{(.*?)\n\}\n",
                            self.JS, re.S).group(1)
        self.assertIn("runaPorContador(ck, sid", ajustar)
        self.assertIn("set_id: sid", ajustar)
        self.assertIn("if (!sid) return", ajustar)   # em «Todas» não há botões
        self.assertIn("totals_por_edicao", ajustar)
        # E continua a não tocar em mais nada do site.
        for proibido in ("api/adjust", "api/encomenda", "wlDesatualizar",
                         "encMarcaVelhos", "state.qty", "state.colecaoVelha"):
            self.assertNotIn(proibido, ajustar)

    def test_a_nota_e_a_ajuda_dizem_a_regra_nova(self):
        con = self.catalogo()
        nota = self.rv.payload(con)["nota"]
        self.assertIn("nesta edição", nota)
        self.assertIn("é DESTA edição", nota)
        # A que já estava, e continua a ter de estar.
        self.assertIn("o número é teu", nota)
        self.assertIn("sequência do master set", nota)
        self.assertIn("«nesta edição»", self.JS)
        con.close()


class TestOQueEstavaDecididoFicaDePe(Base):
    """As duas regras que a ordem manda confirmar: as runas do master set são
    1 de cada (2026-09-08; e 3 desde 2026-09-15 à tarde, por
    `master_targets_by_type`), e as promo `VEN-R01..R06` NÃO saem da Coleção
    por causa desta mudança."""

    def test_o_alvo_da_runa_do_master_set_nao_e_o_do_bloco(self):
        """O bloco pede 12; a Coleção pede o que o config disser (3 hoje). São
        dois números e vivem em dois sítios."""
        con = self.catalogo()
        cfg = self.rv.config.load()
        base = con.execute("SELECT * FROM catalog.printings WHERE printing_id = ?",
                           ("ogn-042-100",)).fetchone()
        self.assertEqual(self.metrics.alvo(base, cfg), 3)
        self.assertNotEqual(self.metrics.alvo(base, cfg), self.rv.alvo(cfg))
        self.assertEqual(self.rv.alvo(cfg), 12)
        con.close()

    def test_a_runa_base_continua_na_sequencia_do_master_set(self):
        con = self.catalogo()
        cfg = self.rv.config.load()
        sp = self.metrics.set_payload(con, "OGN", cfg)
        blocos = {pr["id"]: pr["block"] for g in sp["groups"] for pr in g["printings"]}
        self.assertEqual(blocos["ogn-042-100"], "master")
        self.assertNotIn("ogn-042a-100", blocos, "a alt art da runa está retirada")
        con.close()

    def test_a_promo_ven_r_continua_onde_estava(self):
        """Escondida da grelha (2026-09-15) mas DENTRO do vault: as cópias
        continuam no `copies` e no valor, e o bloco mostra-a no VEN."""
        from riftvault import prices
        con = self.catalogo()
        cfg = self.rv.config.load()
        promo = con.execute("SELECT * FROM catalog.printings WHERE printing_id = ?",
                            ("ven-r02",)).fetchone()
        self.assertTrue(self.metrics.escondida(promo, cfg))
        self.assertFalse(self.metrics.retirada(promo, cfg))
        self.assertEqual(con.execute("SELECT qty FROM copies WHERE printing_id = ?",
                                     ("ven-r02",)).fetchone()["qty"], 1)
        # O valor conta tudo menos as RETIRADAS (2026-09-17) — e a promo não é
        # retirada, por isso a cópia dela está lá dentro.
        fora = self.metrics.retiradas_ids(con)
        esperado = sum(r["qty"] for r in con.execute(
            "SELECT printing_id, qty FROM copies") if r["printing_id"] not in fora)
        self.assertEqual(prices.collection_value(con)["copias"], esperado)
        self.assertNotIn("ven-r02", fora)
        p = self.rv.payload(con)
        origens = [o["code"] for o in self.runa(self.ed(p, "VEN"), "Calm Rune")["origens"]]
        self.assertEqual(origens, ["VEN-R02"])
        con.close()


if __name__ == "__main__":   # pragma: no cover
    unittest.main()

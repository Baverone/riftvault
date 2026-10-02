"""AS CAIXAS do separador «Faltas» (2026-10-02).

André: *"nas faltas, tens as faltas de masterset, mas gostava que tivesse uma
caixa tambem para faltas de Overnumbered e outra caixa para faltas AltArt e uma
caixa para as faltas de Vendetta (que era tudo). pode ser com sistema de botoes
para nao ocupar muito espaco ou como achares melhor"*. E, a duas perguntas: a
caixa da edição leva **tudo** o que falta dela (master set, sobrenumeradas, alt
art, signatures e promos) e as três caixas são **iguais à do master set** — com
preço, total e lista para o Cardmarket, não são só para ver.

O que se fixa aqui:

  * as caixas são uma RE-ARRUMAÇÃO — não há item novo nem cálculo novo: os
    números de uma caixa saem dos itens que os blocos das edições já têm, e os
    `pids` dela são os mesmos `printing_id` (é isso que faz o `+` de «já
    encomendei» valer nas duas vistas, por ser a mesma linha);
  * uma caixa de BLOCO atravessa as edições, uma caixa de EDIÇÃO atravessa os
    blocos, e as duas SOBREPÕEM-SE de propósito («que era tudo»);
  * cada caixa tem a SUA wantlist, pelo mesmo gerador das outras cinco;
  * quais são vem do config, e um bloco ou uma edição que não existam REBENTAM;
  * o que fica de fora de uma caixa de edição conta-se e diz-se pelo nome — as
    ESCONDIDAS (tokens, signatures, runas sem numeração) e a metade das foils;
  * **a Coleção não mexe um número**, e a prova é uma fotografia sem o relógio
    lá dentro (o `sem_relogio`, a lição de 02/10).

Tudo contra cópias descartáveis (`tests.fixture.Vault`) e um config temporário
(`RIFTVAULT_CONFIG`): nunca o `data/` nem o `riftvault_config.json` reais.
"""

from __future__ import annotations

import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ["RIFTVAULT_CONFIG"] = str(Path(tempfile.gettempdir()) / "riftvault-nao-existe.json")

from tests.fixture import REPO, Vault  # noqa: E402

#: As chaves que andam com o relógio e não são contabilidade nenhuma. Uma
#: fotografia que pergunta «mudou alguma conta?» não pode ter o relógio dentro
#: — ou passa conforme calhe, que é pior do que falhar sempre (02/10/2026).
RELOGIOS = ("generated_at", "synced_at", "updated_at", "as_of", "quando", "ts")


def sem_relogio(obj):
    if isinstance(obj, dict):
        return {k: sem_relogio(v) for k, v in obj.items() if k not in RELOGIOS}
    if isinstance(obj, (list, tuple)):
        return type(obj)(sem_relogio(x) for x in obj)
    return obj


class Base(unittest.TestCase):
    """Duas edições com os quatro blocos, para as caixas terem o que
    atravessar: a AAA (sequência, alt art, duas sobrenumeradas, uma promo, um
    token escondido) e a BBB (sequência, alt art, uma sobrenumerada)."""

    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.close)
        from riftvault import (a_subir, cardmarket, collection, config, faltas_edicao,
                               faltas_foil, locais, metrics, pending)
        for m in (metrics, locais, pending, cardmarket, a_subir, faltas_edicao,
                  faltas_foil):
            importlib.reload(m)
        self.config, self.collection, self.pending = config, collection, pending
        self.fe, self.ff, self.metrics = faltas_edicao, faltas_foil, metrics
        self.a_subir, self.locais = a_subir, locais

    def com_config(self, extra: dict):
        caminho = self.v.root / "config.json"
        caminho.write_text(json.dumps(extra), encoding="utf-8")
        os.environ["RIFTVAULT_CONFIG"] = str(caminho)
        importlib.reload(self.config)
        self.config.load.cache_clear()

        def repor():
            os.environ["RIFTVAULT_CONFIG"] = str(
                Path(tempfile.gettempdir()) / "riftvault-nao-existe.json")
            importlib.reload(self.config)
            self.config.load.cache_clear()

        self.addCleanup(repor)

    def preco(self, con, pid, cents):
        con.execute("INSERT INTO catalog.price_latest (printing_id, price_cents, "
                    "from_foil) VALUES (?,?,0)", (pid, cents))

    def montar(self, extra: dict | None = None):
        self.com_config({
            "sets": {"AAA": {"name": "Alfa", "order": 1},
                     "BBB": {"name": "Beta", "order": 2}},
            "faltas_edicao": {"caixas_blocos": ["overnumbered", "alt_art"],
                              "caixas_edicoes": ["BBB"]},
            **(extra or {}),
        })
        con = self.v.connect()
        self.addCleanup(con.close)
        add = self.v.add_printing
        # AAA: dois da sequência, uma alt art, duas sobrenumeradas, uma promo,
        # um token (escondido).
        add(con, "aaa-001", "AAA", 1, "Alfa Um", size=30)
        add(con, "aaa-002", "AAA", 2, "Alfa Dois", size=30)
        add(con, "aaa-001a", "AAA", 1, "Alfa Um", variant="a", kind="alt_art",
            rarity="showcase", base_rarity="common", size=30)
        add(con, "aaa-031", "AAA", 31, "Alfa Sobre", rarity="rare", size=30)
        add(con, "aaa-032", "AAA", 32, "Alfa Sobre Dois", rarity="rare", size=30)
        add(con, "aaa-sp1", "AAA", 1, "Alfa Promo", variant="sp1", kind="special",
            lane="sp", rarity="epic", codigo="AAA-SP1/002")
        add(con, "aaa-t01", "AAA", 1, "Alfa Token", variant="t01", kind="token",
            lane="t", codigo="AAA-T01")
        # BBB: um da sequência, uma alt art, uma sobrenumerada, um token.
        add(con, "bbb-001", "BBB", 1, "Beta Um", size=20)
        add(con, "bbb-001a", "BBB", 1, "Beta Um", variant="a", kind="alt_art",
            rarity="showcase", base_rarity="common", size=20)
        add(con, "bbb-021", "BBB", 21, "Beta Sobre", rarity="rare", size=20)
        add(con, "bbb-t01", "BBB", 1, "Beta Token", variant="t01", kind="token",
            lane="t", codigo="BBB-T01")
        for pid, c in (("aaa-001", 100), ("aaa-002", 200), ("aaa-001a", 5000),
                       ("aaa-031", 20000), ("aaa-032", 30000), ("aaa-sp1", 9999),
                       ("aaa-t01", 5), ("bbb-001", 300), ("bbb-001a", 7000),
                       ("bbb-021", 40000), ("bbb-t01", 5)):
            self.preco(con, pid, c)
        self.v.rebuild(con)
        con.commit()
        return con

    def caixa(self, p, cid):
        return next(c for c in p["caixas"] if c["id"] == cid)

    def itens_de(self, p, c):
        por = {x["printing_id"]: x for d in p["sets"] for g in d["blocks"]
               for x in g["items"]}
        return [por[pid] for pid in c["pids"]]


class TestOQueAsCaixasSao(Base):
    def test_as_tres_caixas_pela_ordem_blocos_e_depois_edicoes(self):
        con = self.montar()
        p = self.fe.payload(con)
        self.assertEqual([c["id"] for c in p["caixas"]],
                         ["bloco-overnumbered", "bloco-alt_art", "edicao-BBB"])
        # O rótulo de uma caixa de edição é o NOME da edição (o `config
        # .set_name`) mais o sufixo — no real o nome do VEN é o código, por
        # decisão dele de 2026-08-31, e lê-se «VEN — tudo».
        self.assertEqual([c["label"] for c in p["caixas"]],
                         ["OverNumbered", "Alt Art", "Beta — tudo"])

    def test_a_caixa_de_um_bloco_atravessa_as_edicoes(self):
        """É o corte que faltava: o separador é por edição, a caixa é por
        bloco."""
        con = self.montar()
        c = self.caixa(self.fe.payload(con), "bloco-overnumbered")
        self.assertEqual(sorted(c["pids"]), ["aaa-031", "aaa-032", "bbb-021"])
        self.assertEqual(c["sets"], ["AAA", "BBB"])
        self.assertEqual(c["blocos"], ["overnumbered"])
        self.assertEqual(c["scope"], 3)

    def test_a_caixa_de_uma_edicao_atravessa_os_blocos(self):
        """«que era tudo»: a edição inteira, os quatro blocos numa lista."""
        con = self.montar()
        c = self.caixa(self.fe.payload(con), "edicao-BBB")
        self.assertEqual(sorted(c["pids"]), ["bbb-001", "bbb-001a", "bbb-021"])
        self.assertEqual(c["sets"], ["BBB"])
        self.assertEqual(c["blocos"], ["master", "overnumbered", "alt_art", "special"])

    def test_as_caixas_sobrepoem_se_e_por_isso_nao_somam_ao_total(self):
        """Dito-lhe e não objectou: uma sobrenumerada do VEN está nas duas.
        A soma das caixas é MAIOR do que o total do separador."""
        con = self.montar()
        p = self.fe.payload(con)
        over = self.caixa(p, "bloco-overnumbered")
        ed = self.caixa(p, "edicao-BBB")
        self.assertIn("bbb-021", over["pids"])
        self.assertIn("bbb-021", ed["pids"])
        # A sobrenumerada do Beta conta nas DUAS caixas e UMA vez no total: a
        # soma das duas é maior do que a união delas, e por isso somar caixas
        # não dá o separador. (Somar TODAS as caixas também não dá o total pelo
        # outro lado: elas não cobrem o master set das outras edições.)
        juntas = over["copies"] + ed["copies"]
        uniao = len(set(over["pids"]) | set(ed["pids"]))
        self.assertGreater(juntas, uniao)
        self.assertEqual(
            sum(1 for d in p["sets"] for g in d["blocks"]
                for x in g["items"] if x["printing_id"] == "bbb-021"), 1,
            "no separador a linha é uma só — a sobreposição é das caixas")

    def test_os_numeros_de_uma_caixa_sao_a_soma_dos_itens_que_ja_existiam(self):
        """Não há cálculo novo: a conta da caixa é o `soma` dos MESMOS itens."""
        con = self.montar()
        p = self.fe.payload(con)
        for c in p["caixas"]:
            esperado = self.fe.soma(self.itens_de(p, c))
            for k, v in esperado.items():
                self.assertEqual(c[k], v, f"{c['id']}.{k}")

    def test_a_caixa_leva_pids_e_NAO_uma_copia_do_item(self):
        """Uma segunda cópia da linha divergia no primeiro `+`: a caixa tem de
        apontar para a linha, não duplicá-la."""
        con = self.montar()
        c = self.caixa(self.fe.payload(con), "bloco-alt_art")
        self.assertNotIn("items", c)
        self.assertTrue(all(isinstance(x, str) for x in c["pids"]))

    def test_a_ordem_dos_pids_e_a_que_se_ve(self):
        """Numa caixa de bloco, edição a edição; numa de edição, bloco a
        bloco — as mesmas ordens dos separadores."""
        con = self.montar()
        p = self.fe.payload(con)
        over = self.caixa(p, "bloco-overnumbered")
        self.assertEqual(over["pids"], ["aaa-031", "aaa-032", "bbb-021"])
        ed = self.caixa(p, "edicao-BBB")
        self.assertEqual(ed["pids"], ["bbb-001", "bbb-021", "bbb-001a"])

    def test_a_caixa_de_um_bloco_vazio_nao_rebenta(self):
        con = self.montar({"faltas_edicao": {"caixas_blocos": ["special"],
                                             "caixas_edicoes": []}})
        c = self.caixa(self.fe.payload(con), "bloco-special")
        self.assertEqual(c["scope"], 1)
        self.assertEqual(c["sets"], ["AAA"])

    def test_o_que_ele_ja_tem_nao_entra_na_caixa(self):
        con = self.montar()
        self.collection.adjust(con, "bbb-021", 1, source="teste")
        c = self.caixa(self.fe.payload(con), "bloco-overnumbered")
        self.assertNotIn("bbb-021", c["pids"])
        self.assertEqual(c["scope"], 3, "o âmbito não encolhe, só a lista")


class TestAWantlistDeCadaCaixa(Base):
    """«as tres caixas novas sao iguais a do master set: com preco, total, e a
    lista para colar no Cardmarket. Nao sao so para ver»."""

    def test_cada_caixa_tem_a_sua_wantlist_pelo_gerador_de_sempre(self):
        from riftvault import cardmarket
        con = self.montar()
        p = self.fe.payload(con)
        for c in p["caixas"]:
            itens = [x for x in self.itens_de(p, c) if x["missing"] > 0]
            w = cardmarket.gerar(itens)
            self.assertEqual(c["wantlist"]["lines"], w["lines"], c["id"])
            self.assertEqual(c["wantlist"]["copies"], w["copies"], c["id"])
            self.assertEqual(c["wantlist"]["cents"], w["cents"], c["id"])

    def test_o_texto_sai_pelo_wantlist_caixa_e_e_o_mesmo_gerador(self):
        from riftvault import cardmarket
        con = self.montar()
        p = self.fe.payload(con)
        c = self.caixa(p, "bloco-overnumbered")
        w = self.fe.wantlist_caixa(con, "bloco-overnumbered")
        itens = [x for x in self.itens_de(p, c) if x["missing"] > 0]
        self.assertEqual(w["text"], cardmarket.gerar(itens)["text"])
        self.assertTrue(w["text"])

    def test_a_caixa_tem_preco_e_total(self):
        con = self.montar()
        c = self.caixa(self.fe.payload(con), "bloco-overnumbered")
        # 200 + 300 + 400 € (uma cópia de cada, alvo 1 nas sobrenumeradas)
        self.assertEqual(c["copies"], 3)
        self.assertEqual(c["cents"], 20000 + 30000 + 40000)

    def test_o_que_vem_a_caminho_nao_vai_para_a_wantlist_mas_fica_na_caixa(self):
        """A mesma regra dos blocos: a linha não desaparece, sai da lista."""
        con = self.montar()
        self.pending.encomendar(con, printing_id="bbb-021", qty=1)
        p = self.fe.payload(con)
        c = self.caixa(p, "bloco-overnumbered")
        self.assertIn("bbb-021", c["pids"], "a linha tem de continuar a ver-se")
        self.assertEqual(c["pending_copies"], 1)
        w = self.fe.wantlist_caixa(con, "bloco-overnumbered")
        self.assertNotIn("Beta Sobre", w["text"])
        self.assertEqual(c["copies"], 2)

    def test_a_caixa_diz_quanto_dela_ja_esta_na_wantlist_geral(self):
        """Na caixa de uma edição parte entra (o master set) e parte não — e é
        por isso que há um `lists` e não só um `in_lists`."""
        con = self.montar()
        p = self.fe.payload(con)
        ed = self.caixa(p, "edicao-BBB")
        self.assertFalse(ed["in_lists"], "nem tudo o que lá está se compra em bloco")
        self.assertEqual(ed["lists"]["copies"], 3, "as 3 cópias do master set")
        over = self.caixa(p, "bloco-overnumbered")
        self.assertEqual(over["lists"]["copies"], 0)

    def test_a_caixa_mais_cara_diz_a_linha_mais_cara(self):
        """Um total de 6 660 € em 51 cópias não se lê sem isto: 2 100 € são UMA
        carta."""
        con = self.montar()
        c = self.caixa(self.fe.payload(con), "bloco-overnumbered")
        self.assertEqual(c["mais_cara"]["cents"], 40000)
        self.assertEqual(c["mais_cara"]["name"], "Beta Sobre")

    def test_uma_caixa_sem_nada_a_comprar_nao_tem_mais_cara(self):
        con = self.montar()
        for pid in ("aaa-031", "aaa-032", "bbb-021"):
            self.collection.adjust(con, pid, 1, source="teste")
        c = self.caixa(self.fe.payload(con), "bloco-overnumbered")
        self.assertIsNone(c["mais_cara"])
        self.assertEqual(c["copies"], 0)

    def test_a_caixa_desconhecida_rebenta_com_a_lista(self):
        con = self.montar()
        with self.assertRaises(ValueError) as e:
            self.fe.wantlist_caixa(con, "bloco-nao-existe")
        self.assertIn("bloco-overnumbered", str(e.exception))


class TestOConfigMandaENaoRebentaEmSilencio(Base):
    def test_a_lista_do_config_manda(self):
        con = self.montar({"faltas_edicao": {"caixas_blocos": ["master"],
                                             "caixas_edicoes": ["AAA", "BBB"]}})
        p = self.fe.payload(con)
        self.assertEqual([c["id"] for c in p["caixas"]],
                         ["bloco-master", "edicao-AAA", "edicao-BBB"])

    def test_listas_vazias_dao_zero_caixas(self):
        con = self.montar({"faltas_edicao": {"caixas_blocos": [],
                                             "caixas_edicoes": []}})
        self.assertEqual(self.fe.payload(con)["caixas"], [])

    def test_um_bloco_que_nao_existe_rebenta(self):
        con = self.montar({"faltas_edicao": {"caixas_blocos": ["nao-existe"],
                                             "caixas_edicoes": []}})
        with self.assertRaises(ValueError) as e:
            self.fe.payload(con)
        self.assertIn("overnumbered", str(e.exception))

    def test_uma_edicao_que_este_catalogo_nao_tem_SALTA_E_DIZ(self):
        """Rebentava, e isso derrubava o `payload()` inteiro (2026-10-02).

        A intenção era boa — um botão que desaparece calado deixa-o a olhar
        para uma fila sem a caixa que pediu. Mas o preço era a página das
        Faltas, a Coleção e o build em baixo: 38 ficheiros da suite ficaram
        vermelhos de uma vez, porque os catálogos de ensaio são TST/AAA e não
        têm VEN. Em casa dava o mesmo com um catálogo atrasado ou uma edição
        que saísse. Salta-se, e o payload diz qual saltou.
        """
        con = self.montar({"faltas_edicao": {"caixas_blocos": [],
                                             "caixas_edicoes": ["ZZZ"]}})
        p = self.fe.payload(con)
        self.assertEqual(p["caixas"], [])
        self.assertEqual(p["caixas_ignoradas"], ["ZZZ"])

    def test_a_que_existe_fica_e_so_a_que_falta_salta(self):
        con = self.montar({"faltas_edicao": {"caixas_blocos": [],
                                             "caixas_edicoes": ["AAA", "ZZZ"]}})
        p = self.fe.payload(con)
        self.assertEqual([c["id"] for c in p["caixas"]], ["edicao-AAA"])
        self.assertEqual(p["caixas_ignoradas"], ["ZZZ"])

    def test_sem_nada_a_saltar_a_lista_vem_vazia(self):
        con = self.montar({"faltas_edicao": {"caixas_blocos": [],
                                             "caixas_edicoes": ["AAA"]}})
        self.assertEqual(self.fe.payload(con)["caixas_ignoradas"], [])

    def test_o_bloco_desconhecido_CONTINUA_a_rebentar(self):
        """A outra metade da decisão: aqui o conjunto de valores é fixo e só
        um erro de escrita produz um que não exista — esse grita."""
        con = self.montar({"faltas_edicao": {"caixas_blocos": ["nao-existe"],
                                             "caixas_edicoes": ["AAA"]}})
        with self.assertRaises(ValueError):
            self.fe.payload(con)

    def test_a_entrada_repetida_conta_uma(self):
        con = self.montar({"faltas_edicao": {
            "caixas_blocos": ["overnumbered", "overnumbered"],
            "caixas_edicoes": []}})
        self.assertEqual(len(self.fe.payload(con)["caixas"]), 1)

    def test_o_config_real_tem_as_tres_que_ele_pediu(self):
        bruto = json.loads((REPO / "riftvault_config.json").read_text(encoding="utf-8"))
        o = bruto["faltas_edicao"]
        self.assertEqual(o["caixas_blocos"], ["overnumbered", "alt_art"])
        self.assertEqual(o["caixas_edicoes"], ["VEN"])
        self.assertIn("_faltas_edicao_nota", bruto)

    def test_o_master_nao_esta_no_config_real_e_ha_razao(self):
        """«tens as faltas de masterset»: a lista do master set de todas as
        edições já existe — é a «Wantlist — tudo» do fim da Coleção."""
        bruto = json.loads((REPO / "riftvault_config.json").read_text(encoding="utf-8"))
        self.assertNotIn("master", bruto["faltas_edicao"]["caixas_blocos"])
        nota = bruto["_faltas_edicao_nota"]
        self.assertIn("Wantlist — tudo", nota)

    def test_os_defaults_dizem_o_mesmo_que_o_ficheiro(self):
        from riftvault import config
        self.assertEqual(config.DEFAULTS["faltas_edicao"]["caixas_blocos"],
                         ["overnumbered", "alt_art"])
        self.assertEqual(config.DEFAULTS["faltas_edicao"]["caixas_edicoes"], ["VEN"])


class TestOQueFicaDeForaDizSe(Base):
    """Ele nomeou as signatures para a caixa da edição e elas são ZERO (o VEN
    não tem nenhuma no catálogo). Não se alargou o âmbito para apanhar zero
    cartas — contou-se o que ficou de fora, pelo nome."""

    def test_as_escondidas_contam_se_por_tipo_na_caixa_de_uma_edicao(self):
        con = self.montar()
        c = self.caixa(self.fe.payload(con), "edicao-BBB")
        self.assertEqual(c["escondidas"], {"token": 1})

    def test_uma_signature_apareceria_PELO_NOME_em_vez_de_sumir(self):
        """O mecanismo que torna o zero de hoje legível: se o catálogo ganhar
        uma signature, ela aparece na linha das escondidas."""
        con = self.montar()
        self.v.add_printing(con, "bbb-030", "BBB", 30, "Beta Assinada",
                            variant="star", kind="signature", rarity="showcase",
                            size=20, codigo="BBB-030*/020")
        self.v.rebuild(con)
        c = self.caixa(self.fe.payload(con), "edicao-BBB")
        self.assertEqual(c["escondidas"].get("signature"), 1)
        self.assertNotIn("bbb-030", c["pids"], "continua fora da Coleção (09/09)")

    def test_a_caixa_de_um_bloco_nao_fala_de_escondidas(self):
        """«todas as sobrenumeradas» não promete uma edição inteira, por isso
        não tem omissão nenhuma a declarar."""
        con = self.montar()
        c = self.caixa(self.fe.payload(con), "bloco-overnumbered")
        self.assertEqual(c["escondidas"], {})

    def test_so_a_caixa_de_edicao_conta_as_foils(self):
        """O âmbito das foils são as comuns e incomuns BASE e não
        sobrenumeradas: uma caixa de sobrenumeradas nunca teve foil nenhuma
        para deixar de fora, e dizer-lhe «852 foils fora» era inventar uma
        omissão."""
        con = self.montar()
        p = self.ff.payload_completo(con)
        self.assertIn("foil", self.caixa(p, "edicao-BBB"))
        self.assertNotIn("foil", self.caixa(p, "bloco-overnumbered"))

    def test_as_foils_nao_entram_na_caixa_da_edicao(self):
        """Elas não são faltas (2026-09-27) e ele não as nomeou nesta."""
        con = self.montar()
        p = self.ff.payload_completo(con)
        c = self.caixa(p, "edicao-BBB")
        foil = next(d for d in p["sets"] if d["set"] == "BBB").get("foil") or {}
        for x in foil.get("items", []):
            self.assertEqual(sum(1 for pid in c["pids"] if pid == x["printing_id"]), 1,
                             "a impressão entra UMA vez, pela metade das normais")
        self.assertEqual(c["copies"], self.fe.soma(self.itens_de(p, c))["copies"])


class TestNaoMexeEmNumeroNenhumDaColecao(Base):
    """A exigência da ordem: os alvos, os níveis, a wantlist do master set e o
    valor saem EXACTAMENTE iguais. As caixas são vista, não contabilidade."""

    def fotografia(self, con):
        from riftvault import a_subir, metrics, prices
        cfg = self.config.load()
        p = self.fe.payload(con, cfg)
        bruto = {
            "niveis": metrics.niveis_payload(con, cfg),
            # O `cfg` vai POR NOME: o segundo posicional é o `editable`, e com
            # o config lá dentro a fotografia passava a conter o próprio
            # ficheiro que este teste muda — comparava-se a si mesma.
            "index": metrics.index_payload(con, cfg=cfg),
            "wantlist": a_subir.wantlist(con),
            "master_faltas": a_subir.master_faltas(con, cfg),
            "valor": prices.collection_value(con),
            # A metade das normais do separador, inteira: blocos, totais e as
            # wantlists por bloco. É o que não pode mexer por as caixas
            # existirem.
            "faltas_totals": p["totals"],
            "faltas_lists": p["totals_lists"],
            "faltas_sets": p["sets"],
            "faltas_blocks": p["blocks"],
            "faltas_scope": p["scope"],
            "sets": {sid: metrics.set_payload(con, sid, cfg)["progress"]
                     for sid in ("AAA", "BBB")},
            "copies": sorted(tuple(r) for r in
                             con.execute("SELECT printing_id, qty, qty_foil FROM copies")),
        }
        return sem_relogio(bruto)

    def test_as_caixas_nao_mexem_em_nada_do_que_ja_existia(self):
        con = self.montar()
        sem = self.fotografia(con)
        self.assertTrue(self.fe.payload(con)["caixas"],
                        "a fotografia não vale sem caixas nenhumas")
        # Com as caixas desligadas no config, a mesma fotografia.
        self.com_config({
            "sets": {"AAA": {"name": "Alfa", "order": 1},
                     "BBB": {"name": "Beta", "order": 2}},
            "faltas_edicao": {"caixas_blocos": [], "caixas_edicoes": []},
        })
        self.assertEqual(self.fe.payload(con)["caixas"], [])
        self.assertEqual(self.fotografia(con), sem)

    def test_a_fotografia_nao_e_de_zeros(self):
        """A prova pela negativa: se ela não detectasse uma mudança, o teste de
        cima passava com qualquer coisa."""
        con = self.montar()
        antes = self.fotografia(con)
        self.collection.adjust(con, "aaa-001", 2, source="teste")
        self.assertNotEqual(self.fotografia(con), antes)

    def test_a_fotografia_nao_tem_relogio(self):
        """Nenhuma chave de tempo sobra — senão o teste de cima volta a passar
        ou a falhar conforme o segundo em que calhe (02/10/2026)."""
        con = self.montar()
        texto = json.dumps(self.fotografia(con), default=str)
        for chave in RELOGIOS:
            self.assertNotIn('"%s"' % chave, texto,
                             "a fotografia voltou a levar o relógio dentro")

    def test_ler_as_caixas_nao_escreve(self):
        con = self.montar()
        antes = [tuple(r) for r in con.execute(
            "SELECT printing_id, qty, qty_foil FROM copies")]
        ops = con.execute("SELECT COUNT(*) FROM ops").fetchone()[0]
        self.fe.payload(con)
        self.fe.wantlist_caixa(con, "bloco-overnumbered")
        self.assertEqual([tuple(r) for r in con.execute(
            "SELECT printing_id, qty, qty_foil FROM copies")], antes)
        self.assertEqual(con.execute("SELECT COUNT(*) FROM ops").fetchone()[0], ops)

    def test_a_wantlist_geral_nao_cresce_com_as_caixas(self):
        """Acompanhar continua a não ser querer comprar em bloco: a «Wantlist —
        tudo» da Coleção é só o master set, caixas ou não."""
        con = self.montar()
        p = self.fe.payload(con)
        w = self.a_subir.wantlist(con)
        self.assertEqual(p["totals_lists"]["copies"], w["copies"])


class TestOFrontend(Base):
    APP = (REPO / "riftvault" / "web" / "app.js").read_text(encoding="utf-8")
    HTML = (REPO / "riftvault" / "web" / "index.html").read_text(encoding="utf-8")
    CSS = (REPO / "riftvault" / "web" / "style.css").read_text(encoding="utf-8")

    def test_ha_uma_fila_de_botoes_propria_e_rotulada(self):
        """«pode ser com sistema de botoes para nao ocupar muito espaco». Fila
        própria: na de cima os botões são edições, e um «VEN — tudo» ao lado do
        «VEN» lia-se como o mesmo botão."""
        self.assertIn('id="fe-caixas"', self.HTML)
        self.assertIn('id="fe-caixas-bar"', self.HTML)
        self.assertIn("Caixas", self.HTML)
        self.assertIn("segwrap", self.HTML)

    def test_a_fila_das_caixas_esconde_se_sem_caixas(self):
        self.assertIn("$('#fe-caixas-bar').hidden = !cxs.length", self.APP)

    def test_o_secbar_hidden_tem_display_none(self):
        """O `display: flex` da classe ganha ao `display: none` do atributo
        `hidden` — sem esta regra a fila aparecia vazia. A mesma armadilha do
        `.chips[hidden]`."""
        self.assertIn(".secbar[hidden]", self.CSS)

    def test_a_caixa_resolve_os_pids_para_os_MESMOS_objectos(self):
        """É isto que faz o `+` de «já encomendei» valer nas duas vistas."""
        self.assertIn("function feLigarCaixas", self.APP)
        self.assertIn("porPid.get(pid)", self.APP)

    def test_NO_NODE_a_caixa_e_o_bloco_sao_a_mesma_linha(self):
        """A afirmação central desta ordem, corrida a sério: depois do
        `feLigarCaixas`, a linha que está na caixa é o MESMO objecto que está no
        bloco da edição — por isso marcar «já encomendei» numa vista marca na
        outra. Com duas cópias isto divergia no primeiro clique.

        Salta-se sem `node`, como os outros gémeos em JavaScript do repo."""
        import shutil
        import subprocess
        if not shutil.which("node"):
            self.skipTest("sem node")
        con = self.montar()
        payload = json.dumps(self.ff.payload_completo(con), default=str)
        guiao = r"""
const APP = require('fs').readFileSync(process.argv[2], 'utf8');
function troco(nome) {
  const i = APP.indexOf('function ' + nome + '(');
  let n = 0;
  for (let k = APP.indexOf('{', i); k < APP.length; k++) {
    if (APP[k] === '{') n++;
    else if (APP[k] === '}' && --n === 0) return APP.slice(i, k + 1);
  }
}
const state = { faltasEdicao: JSON.parse(process.argv[3]) };
const { feLigarCaixas, feSoma } = new Function('state',
  troco('feLigarCaixas') + '\n' + troco('feSoma') +
  '\nreturn { feLigarCaixas, feSoma };')(state);
feLigarCaixas();
const p = state.faltasEdicao;
const over = p.caixas.find(c => c.id === 'bloco-overnumbered');
const ed = p.caixas.find(c => c.id === 'edicao-BBB');
const pid = over.pids.find(x => ed.pids.includes(x));
const noBloco = p.sets.flatMap(s => s.blocks).flatMap(g => g.items)
  .find(x => x.printing_id === pid);
const mesmo = noBloco === over.items.find(x => x.printing_id === pid)
           && noBloco === ed.items.find(x => x.printing_id === pid);
// Mexe por uma vista; as outras têm de ver.
const antes = noBloco.missing;
const naCaixa = over.items.find(x => x.printing_id === pid);
naCaixa.pending = 1; naCaixa.missing = Math.max(0, naCaixa.short - 1);
console.log(JSON.stringify({
  pid, mesmo, antes, bloco: noBloco.missing,
  outra_caixa: ed.items.find(x => x.printing_id === pid).missing,
  soma: feSoma(over.items).copies, soma_antes: over.copies,
}));
"""
        guiao_p = self.v.root / "mesma_linha.cjs"
        guiao_p.write_text(guiao, encoding="utf-8")
        app = str(REPO / "riftvault" / "web" / "app.js")
        r = subprocess.run(["node", str(guiao_p), app, payload],
                           capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)
        d = json.loads(r.stdout)
        self.assertTrue(d["pid"], "o caso precisa de uma linha nas duas caixas")
        self.assertTrue(d["mesmo"], "a caixa fez uma CÓPIA da linha")
        self.assertEqual(d["bloco"], d["antes"] - 1, "o bloco não viu o clique")
        self.assertEqual(d["outra_caixa"], d["bloco"], "as caixas divergiram")
        self.assertEqual(d["soma"], d["soma_antes"] - 1, "o feSoma não acompanhou")

    def test_uma_escolha_so_para_as_duas_filas(self):
        self.assertIn("function feCaixa", self.APP)
        self.assertIn("c.id === state.prefs.feSet", self.APP)

    def test_a_caixa_e_uma_rota_valida(self):
        self.assertIn("caixas || []).some(c => c.id === s)", self.APP)

    def test_a_caixa_desenha_tiles_e_a_caixa_do_cardmarket(self):
        self.assertIn("function renderFeCaixa", self.APP)
        self.assertIn("feWantlistHTML(null, c)", self.APP)
        self.assertIn("c.items.map(feTile)", self.APP)

    def test_a_nota_diz_que_as_caixas_se_sobrepoem(self):
        self.assertIn("sobrepõem-se", self.APP)
        self.assertIn("não\n      é o total do separador", self.APP.replace("\r", ""))

    def test_as_caixas_recontam_se_a_cada_clique(self):
        self.assertIn("for (const c of p.caixas)", self.APP)
        self.assertIn("c.lists = feSoma", self.APP)

    def test_o_nome_de_um_tipo_escondido_tem_singular(self):
        """«1 tokens» não se escreve."""
        self.assertIn("function feKind(k, n = 2)", self.APP)
        self.assertIn("['token', 'tokens']", self.APP)


class TestACLI(Base):
    CLI = (REPO / "riftvault" / "cli.py").read_text(encoding="utf-8")

    def test_ha_uma_caixa_na_consola(self):
        self.assertIn('"--caixa"', self.CLI)
        self.assertIn("wantlist_caixa", self.CLI)

    def test_a_consola_lista_as_caixas(self):
        self.assertIn("CAIXAS — o mesmo cortado ao contrário", self.CLI)
        self.assertIn("SOBREPÕEM-SE", self.CLI)


class TestARotaEOBuild(Base):
    def test_a_rota_traz_as_caixas(self):
        con = self.montar()
        from riftvault import server
        importlib.reload(server)
        server.app.config["TESTING"] = True
        with server.app.test_client() as c:
            with server.app.app_context():
                pass
        p = self.ff.payload_completo(con)
        self.assertIn("caixas", p)
        self.assertTrue(p["caixas"])

    def test_o_payload_completo_junta_as_duas_metades_e_as_caixas(self):
        con = self.montar()
        p = self.ff.payload_completo(con)
        self.assertIn("foil", p)
        self.assertIn("caixas", p)
        self.assertEqual([c["id"] for c in p["caixas"]],
                         ["bloco-overnumbered", "bloco-alt_art", "edicao-BBB"])


if __name__ == "__main__":
    unittest.main()

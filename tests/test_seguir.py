"""Seguir jogadores no Piltover Archive (2026-09-17): o motor e a CLI.

André: *"o @koko_lopez e um jogador muito bom, gostava de seguir os decks que
ele coloca e que vai atualizando"* / *"nao preciso que me diga quanto
custaria, mas sim o que falta"*.

O que se fixa aqui, sempre contra HTML GUARDADO EM FICHEIRO (as três páginas
reais de 2026-09-17 em `tests/fixtures/`) e nunca contra a rede: a leitura do
perfil (handle, decks públicos, o destaque e os últimos criados); a listagem
`/decks?q=` filtrada pelo autor, com a paginação; a página do deck com a lista
de cartas por papel; o mapeamento de nomes (pelo nome, pelo código, os dois a
discordar); as não identificadas à parte e o deck a dizer que a falta está
incompleta; o que conta como ter (tudo, incluindo o que está nos decks dele;
qualquer impressão menos assinada e retirada; o pendente não); novo vs
actualizado vs igual e o estado guardado; só se vai buscar o deck que mudou; a
educação (prefixos vedados, um pedido por segundo, User-Agent honesto); e o
FALHAR ALTO quando o HTML não tem o que se espera.

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

FX = REPO / "tests" / "fixtures"
PERFIL = FX / "piltoverarchive-perfil-koko_lopez-2026-09-17.html"
DECK = FX / "piltoverarchive-deck-f968c99a-2026-09-17.html"
LISTAGEM_P3 = FX / "piltoverarchive-decks-q-koko_lopez-p3-2026-09-17.html"
KENNEN = "f968c99a-d2c0-4f6b-91e4-263e03f300c5"


def ler(p: Path) -> str:
    return p.read_text(encoding="utf-8")


class Base(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.close)
        os.environ["RIFTVAULT_SEGUIR"] = str(self.v.data / "seguir")
        self.addCleanup(lambda: os.environ.pop("RIFTVAULT_SEGUIR", None))
        from riftvault import collection, config, decks, locais, metrics, pending, seguir
        importlib.reload(config)
        config.load.cache_clear()
        for m in (metrics, locais, pending, decks, seguir):
            importlib.reload(m)
        self.seguir, self.collection, self.config = seguir, collection, config
        self.decks, self.locais, self.pending = decks, locais, pending
        self.pasta = self.v.data / "seguir"

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

    def montar(self):
        """Um catálogo com PARTE das cartas do deck da fixture — o resto fica
        «não identificado» de propósito — e a coleção do André."""
        con = self.v.connect()
        self.addCleanup(con.close)
        add = self.v.add_printing
        add(con, "ven-155-166", "VEN", 155, "Heart of the Tempest", card_type="Legend",
            rarity="epic", size=166)
        add(con, "ven-113-166", "VEN", 113, "Kennen, Storm of Shuriken", rarity="epic", size=166)
        add(con, "ven-113a-166", "VEN", 113, "Kennen, Storm of Shuriken", variant="a",
            kind="alt_art", rarity="showcase", base_rarity="epic", size=166)
        add(con, "ogn-166-298", "OGN", 166, "Chaos Rune", card_type="Rune", size=298)
        add(con, "ogn-166a-298", "OGN", 166, "Chaos Rune", variant="a", kind="alt_art",
            card_type="Rune", rarity="showcase", base_rarity="common", size=298)
        add(con, "ogn-214-298", "OGN", 214, "Order Rune", card_type="Rune", size=298)
        add(con, "ogn-183-298", "OGN", 183, "Stacked Deck", card_type="Spell", size=298)
        add(con, "ogn-183-star-298", "OGN", 183, "Stacked Deck", variant="star",
            kind="signature", card_type="Spell", rarity="showcase", base_rarity="common",
            size=298, codigo="OGN-183*/298")
        add(con, "ogn-298-298", "OGN", 298, "Zaun Warrens", card_type="Battlefield", size=298)
        add(con, "ogn-185-298", "OGN", 185, "Traveling Merchant", size=298)
        add(con, "unl-128-219", "UNL", 128, "Star-Crossed", card_type="Spell", size=219)
        self.v.rebuild(con)
        for pid, n in (("ven-155-166", 1), ("ven-113a-166", 1), ("ogn-166-298", 8),
                       ("ogn-166a-298", 6), ("ogn-214-298", 3), ("ogn-183-298", 2),
                       ("ogn-183-star-298", 1), ("ogn-185-298", 1), ("unl-128-219", 1)):
            self.collection.adjust(con, pid, n, source="test")
        return con

    def falso_buscar(self, paginas: dict[str, str] | None = None):
        """Um `buscar` que serve ficheiros: perfil, listagem (uma página só,
        a p3 real, dita como p1) e o deck do Kennen. Regista o que se pediu."""
        pedidos: list[str] = []
        base = {
            self.seguir.url_perfil("koko_lopez"): ler(PERFIL),
            self.seguir.url_listagem("koko_lopez", 1): ler(LISTAGEM_P3).replace(
                'href="/decks?q=koko_lopez&amp;page=1"', 'href="/decks?q=koko_lopez"').replace(
                'href="/decks?q=koko_lopez&amp;page=2"', 'href="/decks?q=koko_lopez"'),
            self.seguir.url_deck(KENNEN): ler(DECK),
        }
        base.update(paginas or {})

        def buscar(url: str) -> str:
            pedidos.append(url)
            if url not in base:
                raise self.seguir.SeguirError(f"o teste não tem esta página: {url}")
            return base[url]

        buscar.pedidos = pedidos
        return buscar


# ---------------------------------------------------------------------------
# O perfil
# ---------------------------------------------------------------------------


class TestPerfil(Base):
    def test_le_o_handle_os_publicos_e_os_decks_do_html(self):
        p = self.seguir.ler_perfil(ler(PERFIL), "koko_lopez")
        self.assertEqual(p["handle"], "koko_lopez")
        self.assertEqual(p["display"], "Koko_Lopez")
        self.assertEqual(p["public_decks"], 18)
        # O destaque + os três últimos CRIADOS, sem repetir.
        self.assertEqual(len(p["decks"]), 4)
        ids = {d["id"] for d in p["decks"]}
        self.assertIn(KENNEN, ids)
        kennen = next(d for d in p["decks"] if d["id"] == KENNEN)
        self.assertEqual(kennen["title"], "Koko’s Kennen RQ Barcelona 2nd place")
        self.assertEqual(kennen["url"], f"https://piltoverarchive.com/decks/view/{KENNEN}")
        self.assertEqual(kennen["edited_at"], "2026-09-03T14:54:22.251Z")
        self.assertEqual(kennen["created_at"], "2026-08-03T18:54:59.370Z")
        self.assertEqual(kennen["legend"], "Kennen, Heart of the Tempest")
        self.assertEqual(kennen["legend_code"], "VEN-155")
        self.assertEqual(kennen["handles"], ["koko_lopez"])

    def test_o_perfil_de_outro_handle_e_erro(self):
        with self.assertRaises(self.seguir.SeguirError):
            self.seguir.ler_perfil(ler(PERFIL), "outro_jogador")

    def test_o_handle_compara_sem_maiusculas(self):
        p = self.seguir.ler_perfil(ler(PERFIL), "Koko_Lopez")
        self.assertEqual(p["handle"], "koko_lopez")


# ---------------------------------------------------------------------------
# A listagem /decks?q=
# ---------------------------------------------------------------------------


class TestListagem(Base):
    def test_filtra_pelo_autor_e_le_a_paginacao(self):
        lst = self.seguir.ler_listagem(ler(LISTAGEM_P3), "koko_lopez", 3)
        # A página 3 real tem 6 entradas: 5 dele e uma de outro autor com o
        # nome dele no título.
        self.assertEqual(lst["entradas"], 6)
        self.assertEqual(len(lst["decks"]), 5)
        self.assertTrue(all("koko_lopez" in d["handles"] for d in lst["decks"]))
        # Os links são para as páginas 1 e 2; a própria (3) é a última.
        self.assertEqual(lst["ultima_pagina"], 3)
        ornn = next(d for d in lst["decks"] if d["title"] == "Ornn TheManland list")
        self.assertEqual(ornn["edited_at"], "2026-09-09T21:28:54.272Z")
        self.assertEqual(ornn["legend"], "Ornn, Fire Below the Mountain")

    def test_outro_autor_da_zero_sem_rebentar(self):
        lst = self.seguir.ler_listagem(ler(LISTAGEM_P3), "ninguem_assim", 1)
        self.assertEqual(lst["decks"], [])
        self.assertEqual(lst["entradas"], 6)

    def test_o_perfil_mais_a_listagem_fundem_por_id(self):
        buscar = self.falso_buscar()
        out = self.seguir.listar_decks("koko_lopez", buscar, 10, log=lambda *_: None)
        ids = {d["id"] for d in out["decks"]}
        # 4 do perfil + 5 da listagem, 3 em comum = 6.
        self.assertEqual(len(ids), 6)
        self.assertEqual(out["public_decks"], 18)
        self.assertEqual(out["paginas"], 1)
        self.assertFalse(out["truncada"])
        self.assertEqual(buscar.pedidos, [self.seguir.url_perfil("koko_lopez"),
                                          self.seguir.url_listagem("koko_lopez", 1)])

    def test_max_paginas_trava_e_avisa(self):
        # A p3 real diz «última página 3» quando lida como página 1 com os
        # links originais: com max_paginas=1 pára e avisa.
        buscar = self.falso_buscar({self.seguir.url_listagem("koko_lopez", 1): ler(LISTAGEM_P3)})
        avisos = []
        out = self.seguir.listar_decks("koko_lopez", buscar, 1, log=avisos.append)
        self.assertTrue(out["truncada"])
        self.assertEqual(out["paginas_lidas"], 1)
        self.assertTrue(any("max_paginas" in a for a in avisos))

    def test_url_da_listagem(self):
        self.assertEqual(self.seguir.url_listagem("koko_lopez"),
                         "https://piltoverarchive.com/decks?q=koko_lopez")
        self.assertEqual(self.seguir.url_listagem("koko_lopez", 2),
                         "https://piltoverarchive.com/decks?q=koko_lopez&page=2")


# ---------------------------------------------------------------------------
# A página do deck
# ---------------------------------------------------------------------------


class TestDeck(Base):
    def test_le_a_lista_por_papel_com_codigos(self):
        d = self.seguir.ler_deck(ler(DECK), KENNEN)
        self.assertEqual(d["title"], "Koko’s Kennen RQ Barcelona 2nd place")
        self.assertEqual(d["author"], "Koko_Lopez")
        self.assertEqual(d["edited_at"], "2026-09-03T14:54:22.251Z")   # sem o `$D`
        self.assertEqual(d["legend"], "Kennen, Heart of the Tempest")
        self.assertEqual(d["legend_code"], "VEN-155")
        por_papel: dict[str, int] = {}
        for c in d["cards"]:
            por_papel[c["role"]] = por_papel.get(c["role"], 0) + c["qty"]
        self.assertEqual(por_papel, {"legend": 1, "champion": 1, "battlefields": 3,
                                     "runes": 12, "main": 39, "sideboard": 10})
        runas = {c["name"]: (c["qty"], c["code"]) for c in d["cards"] if c["role"] == "runes"}
        self.assertEqual(runas, {"Chaos Rune": (9, "OGN-166"), "Order Rune": (3, "OGN-214")})
        champ = next(c for c in d["cards"] if c["role"] == "champion")
        self.assertEqual((champ["name"], champ["code"], champ["type"]),
                         ("Kennen, Storm of Shuriken", "VEN-113", "Unit"))

    def test_outro_id_e_erro(self):
        with self.assertRaises(self.seguir.SeguirError):
            self.seguir.ler_deck(ler(DECK), "00000000-0000-0000-0000-000000000000")


# ---------------------------------------------------------------------------
# Falhar alto
# ---------------------------------------------------------------------------


class TestFalharAlto(Base):
    def test_html_sem_payload_rsc(self):
        with self.assertRaises(self.seguir.SiteMudou) as cm:
            self.seguir.ler_perfil("<html><body>Loading profile…</body></html>", "koko_lopez")
        self.assertIn("'rsc'", str(cm.exception))
        self.assertIn("paginas", str(cm.exception))

    def test_perfil_sem_o_objecto_profile(self):
        html = ler(PERFIL).replace('\\"profile\\":{', '\\"perfilx\\":{')
        with self.assertRaises(self.seguir.SiteMudou) as cm:
            self.seguir.ler_perfil(html, "koko_lopez")
        self.assertIn("'perfil'", str(cm.exception))

    def test_perfil_sem_featured_latest(self):
        html = ler(PERFIL).replace('\\"featured\\":', '\\"destaque\\":')
        with self.assertRaises(self.seguir.SiteMudou) as cm:
            self.seguir.ler_perfil(html, "koko_lopez")
        self.assertIn("perfil.decks", str(cm.exception))

    def test_listagem_sem_a_marca(self):
        html = ler(LISTAGEM_P3).replace('\\"currentFilters\\":', '\\"filtros\\":')
        with self.assertRaises(self.seguir.SiteMudou) as cm:
            self.seguir.ler_listagem(html, "koko_lopez", 3)
        self.assertIn("'listagem'", str(cm.exception))

    def test_listagem_com_decks_ligados_mas_sem_entradas_lidas(self):
        # As chaves trocam de ordem: o regex das entradas deixa de casar mas o
        # HTML continua a ligar 6 decks. NÃO pode sair «0 decks».
        html = ler(LISTAGEM_P3).replace('{\\"id\\":\\"', '{\\"di\\":\\"')
        with self.assertRaises(self.seguir.SiteMudou) as cm:
            self.seguir.ler_listagem(html, "koko_lopez", 3)
        self.assertIn("listagem.entrada", str(cm.exception))

    def test_deck_sem_o_objecto(self):
        html = ler(DECK).replace('\\"deck\\":{\\"id\\":', '\\"baralho\\":{\\"id\\":')
        with self.assertRaises(self.seguir.SiteMudou) as cm:
            self.seguir.ler_deck(html, KENNEN)
        self.assertIn("'deck'", str(cm.exception))

    def test_deck_sem_uma_seccao(self):
        html = ler(DECK).replace('\\"maindeck\\":[', '\\"principal\\":[')
        with self.assertRaises(self.seguir.SiteMudou) as cm:
            self.seguir.ler_deck(html, KENNEN)
        self.assertIn("maindeck", str(cm.exception))

    def test_deck_sem_nomes_de_cartas(self):
        html = ler(DECK).replace('\\"card\\":{\\"id\\":', '\\"carta\\":{\\"id\\":')
        with self.assertRaises(self.seguir.SiteMudou):
            self.seguir.ler_deck(html, KENNEN)

    def test_o_cliente_recusa_os_prefixos_vedados(self):
        c = self.seguir.Cliente(pasta=self.pasta)
        for url in ("https://piltoverarchive.com/api/trpc/decks", "https://piltoverarchive.com/admin/",
                    "https://piltoverarchive.com/_next/static/x.js", "https://piltoverarchive.com/static/a",
                    "https://riftdecks.com/users/x"):
            with self.assertRaises(self.seguir.SeguirError, msg=url):
                c(url)
        self.assertEqual(c.pedidos, 0)
        self.assertFalse(self.seguir.caminho_vedado("https://piltoverarchive.com/users/koko_lopez"))
        self.assertFalse(self.seguir.caminho_vedado("https://piltoverarchive.com/decks?q=x"))

    def test_o_intervalo_nunca_desce_do_minimo_e_o_user_agent_e_honesto(self):
        self.com_config({"seguir": {"jogadores": ["koko_lopez"], "intervalo_segundos": 0.01}})
        op = self.seguir.opcoes(self.config.load())
        self.assertEqual(op["intervalo_segundos"], self.seguir.INTERVALO_MINIMO)
        self.assertGreaterEqual(self.seguir.INTERVALO_MINIMO, 1.0)
        c = self.seguir.cliente(self.config.load())
        self.assertGreaterEqual(c.intervalo, 1.0)
        ua = c._session.headers["User-Agent"]
        self.assertTrue(ua.startswith("riftvault/"))
        self.assertTrue(ua.isascii())
        self.assertNotIn("Mozilla", ua)

    def test_estado_de_outra_versao_rebenta(self):
        self.pasta.mkdir(parents=True)
        (self.pasta / "estado.json").write_text('{"versao": 99}', encoding="utf-8")
        with self.assertRaises(self.seguir.SeguirError):
            self.seguir.carregar_estado(self.pasta)


# ---------------------------------------------------------------------------
# O mapeamento e o que falta
# ---------------------------------------------------------------------------


class TestFaltas(Base):
    def test_resolve_pelo_nome_com_prefixo_e_pelo_codigo(self):
        con = self.montar()
        r = self.seguir.resolver
        self.assertEqual(r(con, "Kennen, Heart of the Tempest", "VEN-155"),
                         ("heart of the tempest", "nome"))
        self.assertEqual(r(con, "Nome Que Não Existe", "OGN-183"), ("stacked deck", "código"))
        self.assertEqual(r(con, "Chaos Rune", None), ("chaos rune", "nome"))
        ck, motivo = r(con, "Cartinha Inventada", "XYZ-999")
        self.assertIsNone(ck)
        self.assertIn("catálogo", motivo)

    def test_nome_e_codigo_a_discordar_nao_se_escolhe(self):
        con = self.montar()
        ck, motivo = self.seguir.resolver(con, "Stacked Deck", "OGN-214")
        self.assertIsNone(ck)
        self.assertIn("stacked deck", motivo)
        self.assertIn("order rune", motivo)

    def test_o_que_conta_como_ter(self):
        con = self.montar()
        tem = self.seguir.possuidas(con)
        # Qualquer impressão serve: a alt art do Champion conta…
        self.assertEqual(tem["kennen, storm of shuriken"], 1)
        # …a signature não…
        self.assertEqual(tem["stacked deck"], 2)
        # …e a runa em alt art está retirada (não existe para o riftvault).
        self.assertEqual(tem["chaos rune"], 8)

    def test_as_copias_nos_decks_dele_contam_e_o_pendente_nao(self):
        con = self.montar()
        self.v.write_deck("meu", "Legend:\n1 Heart of the Tempest\n\nMainDeck:\n1 Traveling Merchant\n")
        self.decks.import_all(con, log=lambda *_: None)
        self.locais.mover(con, "ogn-185-298", 1, de="colecao", para="deck:meu", source="test")
        self.pending.add(con, "ogn-185-298", 2, source="test")
        self.assertEqual(self.seguir.possuidas(con)["traveling merchant"], 1)

    def test_faltas_do_deck_da_fixture(self):
        con = self.montar()
        d = self.seguir.ler_deck(ler(DECK), KENNEN)
        f = self.seguir.faltas_do_deck(con, d["cards"], self.seguir.possuidas(con))
        por_ck = {x["card_key"]: x for x in f["cards"]}
        # 9 Chaos Rune, tem 8 (a alt art retirada não conta): falta 1.
        self.assertEqual((por_ck["chaos rune"]["qty"], por_ck["chaos rune"]["have"],
                          por_ck["chaos rune"]["missing"]), (9, 8, 1))
        # 3 Stacked Deck, tem 2 base + 1 signature: falta 1.
        self.assertEqual(por_ck["stacked deck"]["missing"], 1)
        # Star-Crossed está no main (1) e no sideboard (1): pede 2, tem 1.
        self.assertEqual((por_ck["star-crossed"]["qty"], por_ck["star-crossed"]["missing"]), (2, 1))
        self.assertEqual(sorted(por_ck["star-crossed"]["roles"]), ["main", "sideboard"])
        # O Champion em alt art serve; a Legend com prefixo casa.
        self.assertEqual(por_ck["kennen, storm of shuriken"]["missing"], 0)
        self.assertEqual(por_ck["heart of the tempest"]["missing"], 0)
        self.assertEqual(por_ck["zaun warrens"]["missing"], 1)
        self.assertEqual(por_ck["traveling merchant"]["missing"], 2)
        self.assertEqual(por_ck["order rune"]["missing"], 0)
        # O deck tem 66 cartas; 11 nomes estão no catálogo de brincar, o resto
        # fica por identificar — e conta-se.
        self.assertEqual(f["wanted_copies"] + f["unidentified_copies"], 66)
        self.assertGreater(len(f["unidentified"]), 0)
        self.assertFalse(f["complete"])
        nomes = {x["name"] for x in f["unidentified"]}
        self.assertIn("Minefield", nomes)
        self.assertNotIn("Chaos Rune", nomes)
        # As faltas vêm ordenadas: mais cópias em falta primeiro.
        self.assertEqual(f["missing"][0]["card_key"], "traveling merchant")
        self.assertEqual(f["missing_copies"], 1 + 1 + 1 + 1 + 2)
        # Nunca euros.
        self.assertNotIn("cents", json.dumps(f))
        self.assertNotIn("price", json.dumps(f))

    def test_nao_identificadas_nunca_entram_na_conta(self):
        con = self.montar()
        cartas = [{"role": "main", "qty": 3, "name": "Cartinha Inventada", "code": "XYZ-001", "type": "Unit"},
                  {"role": "main", "qty": 3, "name": "Stacked Deck", "code": "OGN-183", "type": "Spell"}]
        f = self.seguir.faltas_do_deck(con, cartas, self.seguir.possuidas(con))
        self.assertEqual(f["missing_copies"], 1)
        self.assertEqual(len(f["unidentified"]), 1)
        self.assertEqual(f["unidentified_copies"], 3)
        self.assertFalse(f["complete"])

    def test_o_bench_fica_de_fora(self):
        con = self.montar()
        cartas = [{"role": "bench", "qty": 3, "name": "Stacked Deck", "code": "OGN-183", "type": "Spell"},
                  {"role": "main", "qty": 2, "name": "Stacked Deck", "code": "OGN-183", "type": "Spell"}]
        f = self.seguir.faltas_do_deck(con, cartas, self.seguir.possuidas(con))
        self.assertEqual(f["missing_copies"], 0)
        self.assertEqual(len(f["ignored"]), 1)
        self.assertTrue(f["complete"])


# ---------------------------------------------------------------------------
# Novo, actualizado, igual — e o estado
# ---------------------------------------------------------------------------


class TestEstado(Base):
    def correr(self, buscar, **kw):
        con = kw.pop("con")
        return self.seguir.correr(con, buscar, cfg=self.config.load(), jogadores=["koko_lopez"],
                                  pasta=self.pasta, log=lambda *_: None, **kw)

    def test_primeira_corrida_tudo_novo_e_le_so_o_deck_que_tem_pagina(self):
        con = self.montar()
        # Só o deck do Kennen tem página no teste; os outros 5 dão erro ao
        # pedir — o que quer dizer que a corrida REBENTA, e é o que se quer:
        # não se guarda um deck sem lista. Aqui damos-lhes a mesma página, com
        # o id trocado, para a corrida acabar.
        buscar = self.falso_buscar(self.paginas_para_todos())
        p = self.correr(buscar, con=con)
        j = p["players"][0]
        self.assertEqual(j["player"], "koko_lopez")
        self.assertEqual(j["found"], 6)
        self.assertEqual(j["counts"]["novo"], 6)
        self.assertEqual(j["public_decks"], 18)
        # 1 perfil + 1 listagem + 6 decks.
        self.assertEqual(len(buscar.pedidos), 8)
        est = json.loads((self.pasta / "estado.json").read_text(encoding="utf-8"))
        self.assertEqual(len(est["jogadores"]["koko_lopez"]["decks"]), 6)
        self.assertEqual(len(est["jogadores"]["koko_lopez"]["decks"][KENNEN]["cards"]), 33)

    def paginas_para_todos(self) -> dict[str, str]:
        """A página do Kennen com o id trocado, para cada deck que o perfil e a
        listagem anunciam."""
        buscar0 = self.falso_buscar()
        out = self.seguir.listar_decks("koko_lopez", buscar0, 10, log=lambda *_: None)
        html = ler(DECK)
        paginas = {}
        for d in out["decks"]:
            if d["id"] != KENNEN:
                paginas[self.seguir.url_deck(d["id"])] = html.replace(KENNEN, d["id"]).replace(
                    '\\"editedAt\\":\\"$D2026-09-03T14:54:22.251Z\\"',
                    f'\\"editedAt\\":\\"$D{d["edited_at"]}\\"')
        return paginas

    def test_segunda_corrida_igual_nao_vai_buscar_decks(self):
        con = self.montar()
        self.correr(self.falso_buscar(self.paginas_para_todos()), con=con)
        buscar = self.falso_buscar()          # sem páginas de deck: se pedir, rebenta
        p = self.correr(buscar, con=con)
        j = p["players"][0]
        self.assertEqual(j["counts"], {"novo": 0, "actualizado": 0, "igual": 6, "por ler": 0})
        self.assertEqual(len(buscar.pedidos), 2)
        # E as faltas continuam a sair do estado guardado.
        kennen = next(d for d in j["decks"] if d["id"] == KENNEN)
        self.assertEqual(kennen["faltas"]["missing_copies"], 6)

    def test_editado_depois_e_actualizado_e_vai_buscar_so_esse(self):
        con = self.montar()
        self.correr(self.falso_buscar(self.paginas_para_todos()), con=con)
        # O perfil e a listagem passam a dizer que o Kennen foi editado hoje;
        # a página do deck muda uma carta.
        novo = "2026-09-17T10:00:00.000Z"
        perfil = ler(PERFIL).replace('\\"editedAt\\":\\"2026-09-03T14:54:22.251Z\\"',
                                     f'\\"editedAt\\":\\"{novo}\\"')
        # (a «Minefield» não está no catálogo de brincar; a «Zaun Warrens»
        # está, e renomeá-la era identificada na mesma pelo código OGN-298)
        deck = ler(DECK).replace('\\"editedAt\\":\\"$D2026-09-03T14:54:22.251Z\\"',
                                 f'\\"editedAt\\":\\"$D{novo}\\"').replace(
            '\\"name\\":\\"Minefield\\"', '\\"name\\":\\"Cartinha Inventada\\"')
        buscar = self.falso_buscar({self.seguir.url_perfil("koko_lopez"): perfil,
                                    self.seguir.url_deck(KENNEN): deck})
        p = self.correr(buscar, con=con)
        j = p["players"][0]
        self.assertEqual(j["counts"]["actualizado"], 1)
        self.assertEqual(j["counts"]["igual"], 5)
        self.assertEqual(buscar.pedidos.count(self.seguir.url_deck(KENNEN)), 1)
        self.assertEqual(len(buscar.pedidos), 3)
        kennen = next(d for d in j["decks"] if d["id"] == KENNEN)
        self.assertEqual(kennen["estado"], "actualizado")
        self.assertEqual(kennen["edited_at"], novo)
        self.assertEqual(kennen["ultima_mudanca"]["o_que"], "actualizado")
        nomes = {x["name"] for x in kennen["faltas"]["unidentified"]}
        self.assertIn("Cartinha Inventada", nomes)
        self.assertNotIn("Minefield", nomes)
        # Terceira corrida: igual outra vez.
        p = self.correr(self.falso_buscar({self.seguir.url_perfil("koko_lopez"): perfil}), con=con)
        self.assertEqual(p["players"][0]["counts"]["igual"], 6)

    def test_editado_mas_a_lista_e_a_mesma_fica_igual(self):
        con = self.montar()
        self.correr(self.falso_buscar(self.paginas_para_todos()), con=con)
        novo = "2026-09-17T10:00:00.000Z"
        perfil = ler(PERFIL).replace('\\"editedAt\\":\\"2026-09-03T14:54:22.251Z\\"',
                                     f'\\"editedAt\\":\\"{novo}\\"')
        deck = ler(DECK).replace('\\"editedAt\\":\\"$D2026-09-03T14:54:22.251Z\\"',
                                 f'\\"editedAt\\":\\"$D{novo}\\"')
        buscar = self.falso_buscar({self.seguir.url_perfil("koko_lopez"): perfil,
                                    self.seguir.url_deck(KENNEN): deck})
        p = self.correr(buscar, con=con)
        kennen = next(d for d in p["players"][0]["decks"] if d["id"] == KENNEN)
        self.assertEqual(kennen["estado"], "igual")
        self.assertEqual(len(buscar.pedidos), 3)     # foi buscá-lo, mas não o anuncia

    def test_deck_que_desaparece_da_listagem_fica_marcado(self):
        con = self.montar()
        self.correr(self.falso_buscar(self.paginas_para_todos()), con=con)
        # Um perfil e uma listagem sem o Ornn.
        ornn = "6b5686db-f3f3-472d-86ba-ad0afc437f8e"
        outro = "6b5686db-f3f3-472d-86ba-ad0afc437f8f"
        buscar = self.falso_buscar({
            self.seguir.url_perfil("koko_lopez"): ler(PERFIL).replace(ornn, outro),
            self.seguir.url_listagem("koko_lopez", 1): self.falso_buscar()(
                self.seguir.url_listagem("koko_lopez", 1)).replace(ornn, outro),
            self.seguir.url_deck(outro): ler(DECK).replace(KENNEN, outro).replace(
                '\\"editedAt\\":\\"$D2026-09-03T14:54:22.251Z\\"',
                '\\"editedAt\\":\\"$D2026-09-09T21:28:54.272Z\\"'),
        })
        p = self.correr(buscar, con=con)
        j = p["players"][0]
        self.assertEqual([g["id"] for g in j["gone"]], [ornn])
        self.assertEqual(j["counts"]["novo"], 1)
        est = json.loads((self.pasta / "estado.json").read_text(encoding="utf-8"))
        self.assertIsNotNone(est["jogadores"]["koko_lopez"]["decks"][ornn]["ausente_desde"])

    def test_sem_rede_le_o_estado_e_nao_pede_nada(self):
        con = self.montar()
        self.correr(self.falso_buscar(self.paginas_para_todos()), con=con)
        p = self.correr(self.seguir.sem_rede, con=con, sem_rede=True)
        j = p["players"][0]
        self.assertTrue(j["offline"])
        self.assertEqual(j["found"], 6)
        self.assertEqual(j["counts"]["igual"], 6)
        kennen = next(d for d in j["decks"] if d["id"] == KENNEN)
        self.assertEqual(kennen["faltas"]["missing_copies"], 6)

    def test_sem_rede_sem_estado_nao_inventa(self):
        con = self.montar()
        p = self.correr(self.seguir.sem_rede, con=con, sem_rede=True)
        self.assertEqual(p["players"][0]["found"], 0)

    def test_a_falta_segue_a_colecao_sem_ir_ao_site(self):
        con = self.montar()
        self.correr(self.falso_buscar(self.paginas_para_todos()), con=con)
        self.collection.adjust(con, "ogn-185-298", 2, source="test")   # já tem 3 Traveling Merchant
        p = self.correr(self.seguir.sem_rede, con=con, sem_rede=True)
        kennen = next(d for d in p["players"][0]["decks"] if d["id"] == KENNEN)
        self.assertEqual(kennen["faltas"]["missing_copies"], 4)

    def test_a_corrida_nao_escreve_na_colecao(self):
        con = self.montar()
        antes = con.execute("SELECT SUM(qty) AS n, COUNT(*) AS c FROM copies").fetchone()
        ops = con.execute("SELECT COUNT(*) AS n FROM ops").fetchone()["n"]
        self.correr(self.falso_buscar(self.paginas_para_todos()), con=con)
        depois = con.execute("SELECT SUM(qty) AS n, COUNT(*) AS c FROM copies").fetchone()
        self.assertEqual((antes["n"], antes["c"]), (depois["n"], depois["c"]))
        self.assertEqual(ops, con.execute("SELECT COUNT(*) AS n FROM ops").fetchone()["n"])

    def test_classificar(self):
        c = self.seguir.classificar
        self.assertEqual(c(None, {"edited_at": "x"}), "novo")
        self.assertEqual(c({"edited_at": "x"}, {"edited_at": "x"}), "novo")   # sem cartas
        self.assertEqual(c({"edited_at": "x", "cards": [1]}, {"edited_at": "y"}), "actualizado")
        self.assertEqual(c({"edited_at": "x", "cards": [1]}, {"edited_at": "x"}), "igual")


# ---------------------------------------------------------------------------
# A CLI e o config
# ---------------------------------------------------------------------------


class TestCli(Base):
    def test_o_config_lista_os_jogadores(self):
        self.com_config({"seguir": {"jogadores": ["@koko_lopez", " outro "]}})
        op = self.seguir.opcoes(self.config.load())
        self.assertEqual(op["jogadores"], ["koko_lopez", "outro"])
        self.assertEqual(op["max_paginas"], 10)

    def test_o_config_real_segue_o_koko_lopez(self):
        raw = json.loads((REPO / "riftvault_config.json").read_text(encoding="utf-8"))
        self.assertIn("koko_lopez", raw["seguir"]["jogadores"])
        self.assertIn("_seguir_nota", raw)

    def test_o_comando_existe_e_sem_rede_nao_rebenta(self):
        con = self.montar()
        con.close()
        from riftvault import cli
        importlib.reload(cli)
        import io
        from contextlib import redirect_stderr, redirect_stdout
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = cli.main(["seguir", "--jogador", "koko_lopez", "--sem-rede"])
        self.assertEqual(rc, 0)
        self.assertIn("koko_lopez", out.getvalue())
        self.assertIn("sem rede", out.getvalue())
        self.assertNotIn("€", out.getvalue())

    def test_o_comando_imprime_o_que_falta_sem_euros(self):
        con = self.montar()
        est = self.seguir.carregar_estado(self.pasta)
        buscar = self.falso_buscar(self.paginas_para_todos_de(con))
        self.seguir.seguir_jogador(con, "koko_lopez", buscar, est, pasta=self.pasta,
                                   log=lambda *_: None)
        con.close()
        from riftvault import cli
        importlib.reload(cli)
        import io
        from contextlib import redirect_stderr, redirect_stdout
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = cli.main(["seguir", "--jogador", "koko_lopez", "--sem-rede"])
        self.assertEqual(rc, 0)
        texto = out.getvalue()
        self.assertIn("Koko’s Kennen RQ Barcelona 2nd place", texto)
        self.assertIn("faltam 6 cópias de 5 cartas", texto)
        self.assertIn("POR IDENTIFICAR", texto)
        self.assertIn("2x Traveling Merchant", texto)
        self.assertNotIn("€", texto)
        self.assertNotIn("cêntimos", texto)

    def paginas_para_todos_de(self, con) -> dict[str, str]:
        return TestEstado.paginas_para_todos(self)

    def test_json(self):
        con = self.montar()
        con.close()
        from riftvault import cli
        importlib.reload(cli)
        import io
        from contextlib import redirect_stderr, redirect_stdout
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = cli.main(["seguir", "--jogador", "koko_lopez", "--sem-rede", "--json"])
        self.assertEqual(rc, 0)
        p = json.loads(out.getvalue())
        self.assertEqual(p["players"][0]["player"], "koko_lopez")

    def test_a_cache_das_paginas_esta_fora_do_git(self):
        regras = [l.strip() for l in (REPO / ".gitignore").read_text(encoding="utf-8").splitlines()
                  if l.strip() and not l.startswith("#")]
        self.assertIn("data/seguir/paginas/", regras)
        self.assertFalse(any("estado" in r or r in ("data/seguir/", "data/seguir") for r in regras))


if __name__ == "__main__":
    unittest.main()

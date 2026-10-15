"""A RADIANCE PELA DOTGG (2026-10-15), e a PROVA de que o sync da RiftScribe não
a duplica quando a publicar.

André, nesse dia: *"coloca agora essas, dia 23 apenas confirmas se está tudo
bem"*. A dotgg dá `RAD-001`; a RiftScribe dará `rad-001-<tamanho>`. A `copies`
guarda o id sem chave estrangeira — antes de hoje o `catalog.sync` apagava o
que a API deixou de devolver e inseria o novo, e as cópias marcadas entretanto
ficavam ÓRFÃS, sem erro nenhum. O que se prova aqui:

  1. a RAD entra pela dotgg, com o vocabulário que o projecto já tem;
  2. cópias marcadas nela, depois um sync da RiftScribe com OS IDS DELA:
     uma linha por impressão, ZERO cópias órfãs, a mesma contagem;
  3. a dotgg outra vez por cima não escreve sobre a RiftScribe nem duplica.

Sem rede: a dotgg e a RiftScribe são simuladas. Tudo contra cópias
descartáveis (`tests.fixture.Vault`) e um config temporário.
"""

from __future__ import annotations

import importlib
import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.fixture import REPO, SEM_CONFIG, Vault  # noqa: E402

os.environ["RIFTVAULT_CONFIG"] = SEM_CONFIG


def _dg(gid, name, rarity, tipo="Unit", cores=("Calm",), promo="0", cost="3", might="3"):
    """Uma linha da dotgg, com as colunas medidas a 2026-10-15."""
    return {"id": gid, "slug": gid.lower(), "name": name, "name_normal": name,
            "effect": "Faz coisas.<br />E mais.", "flavor": "", "color": list(cores),
            "cost": cost, "power": "0", "type": [tipo], "supertype": "", "might": might,
            "tags": [], "set_name": "Radiance", "rarity": rarity, "cycle": None,
            "image": f"https://static.dotgg.gg/riftbound/cards/{gid}.webp",
            "promo": promo, "banned": "0", "errata": None, "image_back": None,
            "hasback": "0", "mightBonus": None}


# Uma RAD de brincar com tudo o que a de verdade traz (tamanho 5): base, alt
# art, Legend e a sobrenumerada dele com a assinada, uma promo de evento, a runa
# sem numeração e a sua alt art, um token, uma SP — e uma linha de OUTRA edição,
# que a dotgg também devolve e não pode entrar.
DOTGG = [
    _dg("RAD-001", "Ahri - Confident", "Common"),
    _dg("RAD-001A", "Ahri - Confident", "Showcase"),
    _dg("RAD-002", "Ekko - Boy Who Shattered Time", "Rare", tipo="Legend", cores=("Mind", "Body")),
    _dg("RAD-003", "Packed Amphitheater", "Uncommon", tipo="Battlefield", cores=("Colorless",)),
    _dg("RAD-006", "Ekko - Boy Who Shattered Time", "Showcase", tipo="Legend", cores=("Mind", "Body")),
    _dg("RAD-006-STAR", "Ekko - Boy Who Shattered Time", "Showcase", tipo="Legend", cores=("Mind", "Body")),
    _dg("RAD-001-P", "Ahri - Confident (Radiance December 2026 Summoner Skirmish Top 8 Promo)",
        "Rare", promo="1"),
    _dg("RAD-001-P2", "Ahri - Confident (Radiance December 2026 Summoner Skirmish Champion Promo)",
        "Rare", promo="1"),
    _dg("RAD-R01", "Fury Rune", "Common", tipo="Rune", cores=("Fury",)),
    _dg("RAD-R01A", "Fury Rune", "Showcase", tipo="Rune", cores=("Fury",)),
    _dg("RAD-T02", "Bomb", "Common", tipo="Gear", cores=("Colorless",)),
    _dg("RAD-SP1", "Ahri - Confident", "Showcase"),
    _dg("OGN-001", "Blazing Scorcher", "Common", cores=("Fury",)),
]


def _rs(pid, cn, variant, code, name, rarity, tipo="Unit", dominios=("Calm",)):
    """Uma carta como a RiftScribe a dá — os ids DELA, com o denominador."""
    return {"id": pid, "set_id": "RAD", "collector_number": cn, "variant": variant,
            "public_code": code, "name": name, "rarity": rarity, "type": tipo,
            "faction": dominios[0].lower(), "domains": list(dominios),
            "orientation": "landscape" if tipo == "Battlefield" else "portrait",
            "stats": {}, "description": "texto da RiftScribe",
            "image": f"https://cdn.riftscribe.invalid/{pid}.png",
            "image_thumb": {"medium": f"https://cdn.riftscribe.invalid/{pid}.webp"}}


# O dia em que a RiftScribe publica a RAD: as impressões que ela tem, com os ids
# dela (`rad-001-005`, `rad-006-star-005`, `rad-sp1-001`, …). Não traz as promos
# de evento nem a runa em alt art — nas edições que já tem também não as traz.
RIFTSCRIBE = [
    _rs("rad-001-005", 1, "", "RAD-001/005", "Ahri, Confident", "common"),
    _rs("rad-001a-005", 1, "a", "RAD-001a/005", "Ahri, Confident", "showcase"),
    _rs("rad-002-005", 2, "", "RAD-002/005", "Boy Who Shattered Time", "rare", tipo="Legend",
        dominios=("Body", "Mind")),
    _rs("rad-003-005", 3, "", "RAD-003/005", "Packed Amphitheater", "uncommon",
        tipo="Battlefield", dominios=("Colorless",)),
    _rs("rad-006-005", 6, "", "RAD-006/005", "Boy Who Shattered Time", "showcase",
        tipo="Legend", dominios=("Body", "Mind")),
    _rs("rad-006-star-005", 6, "star", "RAD-006*/005", "Boy Who Shattered Time",
        "showcase", tipo="Legend", dominios=("Body", "Mind")),
    _rs("rad-r01", 1, "r01", "RAD-R01", "Fury Rune", "common", tipo="Rune", dominios=("Fury",)),
    _rs("rad-t02", 2, "t02", "RAD-T02", "Bomb", "common", tipo="Gear", dominios=("Colorless",)),
    _rs("rad-sp1-001", 1, "sp1", "RAD-SP1/001", "Ahri, Confident", "epic"),
]


class Base(unittest.TestCase):
    def setUp(self):
        self.v = Vault()
        self.addCleanup(self.v.close)
        real = json.loads((REPO / "riftvault_config.json").read_text(encoding="utf-8"))
        cfg = {"master_set": real["master_set"], "runas_especiais": real.get("runas_especiais", {}),
               "dotgg": {"edicoes": ["RAD"], "tamanhos": {"RAD": 5}}}
        caminho = self.v.root / "config.json"
        caminho.write_text(json.dumps(cfg), encoding="utf-8")
        os.environ["RIFTVAULT_CONFIG"] = str(caminho)
        self.config = self.v.config
        importlib.reload(self.config)
        self.config.load.cache_clear()

        def repor():
            os.environ["RIFTVAULT_CONFIG"] = SEM_CONFIG
            importlib.reload(self.config)
            self.config.load.cache_clear()
        self.addCleanup(repor)

        from riftvault import catalog, collection, db, dotgg, metrics, riftscribe
        for m in (metrics, catalog, dotgg):
            importlib.reload(m)
        self.cat, self.dotgg, self.m, self.db = catalog, dotgg, metrics, db
        self.collection, self.riftscribe = collection, riftscribe
        self.res = dotgg.sync(linhas_api=DOTGG, log=lambda *_: None)
        self.con = db.connect()
        self.addCleanup(self.con.close)

    def rad(self):
        return {r["printing_id"]: dict(r) for r in self.con.execute(
            "SELECT * FROM catalog.printings WHERE set_id = 'RAD'")}

    def sync_riftscribe(self, api=RIFTSCRIBE):
        with mock.patch.object(self.riftscribe, "list_sets", lambda: ["RAD"]), \
             mock.patch.object(self.riftscribe, "iter_cards", lambda sid, delay=0: iter(api)):
            return self.cat.sync(["RAD"], delay=0, log=lambda *_: None)

    def copias(self):
        return {r["printing_id"]: r["qty"] for r in self.con.execute(
            "SELECT printing_id, qty FROM copies WHERE qty > 0")}

    def orfas(self):
        return [r["printing_id"] for r in self.con.execute(
            "SELECT printing_id FROM copies WHERE qty > 0 AND printing_id NOT IN "
            "(SELECT printing_id FROM catalog.printings)")]


class TestARadEntraPelaDotgg(Base):
    def test_entram_as_doze_e_so_as_da_rad(self):
        self.assertEqual(self.res["sets"], {"RAD": 12})
        self.assertNotIn("ogn-001", self.rad())
        self.assertEqual(self.res["estranhos"], [])

    def test_os_ids_sao_os_da_dotgg_em_minusculas(self):
        self.assertEqual(set(self.rad()), {
            "rad-001", "rad-001a", "rad-002", "rad-003", "rad-006", "rad-006-star",
            "rad-001-p", "rad-001-p2", "rad-r01", "rad-r01a", "rad-t02", "rad-sp1"})

    def test_as_variantes_no_vocabulario_do_projecto(self):
        r = self.rad()
        self.assertEqual(r["rad-001"]["variant_kind"], "base")
        self.assertEqual(r["rad-001a"]["variant_kind"], "alt_art")
        self.assertEqual(r["rad-006-star"]["variant_kind"], "signature")
        self.assertEqual(r["rad-001-p"]["variant_kind"], "special")
        self.assertEqual(r["rad-r01"]["variant_kind"], "rune_promo")
        self.assertEqual(r["rad-r01a"]["variant_kind"], "alt_art")
        self.assertEqual(r["rad-t02"]["variant_kind"], "token")
        self.assertEqual(r["rad-sp1"]["variant_kind"], "special")

    def test_os_nomes_a_maneira_da_riftscribe(self):
        r = self.rad()
        self.assertEqual(r["rad-001"]["name"], "Ahri, Confident")
        self.assertEqual(r["rad-002"]["name"], "Boy Who Shattered Time")   # o Legend: só o título
        self.assertEqual(r["rad-001-p"]["name"], "Ahri, Confident")        # sem o parêntese da promo
        self.assertEqual(r["rad-001-p"]["card_key"], r["rad-001"]["card_key"])

    def test_os_campos(self):
        r = self.rad()
        self.assertEqual(r["rad-002"]["faction"], "mind")
        self.assertEqual(json.loads(r["rad-002"]["domains_json"]), ["Body", "Mind"])
        self.assertEqual(r["rad-001"]["energy"], 3)
        self.assertIsNone(r["rad-001"]["power"])
        self.assertEqual(r["rad-003"]["orientation"], "landscape")
        self.assertEqual(r["rad-001"]["fonte"], "dotgg")
        self.assertTrue(r["rad-001"]["image_medium"].startswith("https://static.dotgg.gg/"))

    def test_a_sequencia_e_a_sobrenumerada(self):
        r = self.rad()
        self.assertEqual(r["rad-001"]["public_code"], "RAD-001/5")
        self.assertTrue(self.m.e_master(r["rad-001"]))
        self.assertTrue(self.m.e_overnumbered(r["rad-006"]))
        self.assertEqual(self.m.bloco(r["rad-006"]), "overnumbered")
        self.assertEqual(self.m.alvo(r["rad-006"]), 1)
        self.assertEqual(sum(self.m.e_master(x) for x in r.values()), 3)

    def test_a_assinada_escondida_a_runa_em_alt_art_retirada(self):
        r = self.rad()
        self.assertTrue(self.m.escondida(r["rad-006-star"]))
        self.assertTrue(self.m.retirada(r["rad-r01a"]))
        self.assertTrue(self.m.escondida(r["rad-r01"]))
        self.assertTrue(self.m.escondida(r["rad-t02"]))

    def test_a_promo_de_evento_fica_sem_alvo_pela_regra_que_ja_existia(self):
        r = self.rad()
        p = r["rad-001-p"]
        self.assertEqual(p["rarity"], "promo")            # o símbolo vai para a raridade
        self.assertEqual(p["base_rarity"], "rare")        # a impressa fica ao lado
        self.assertTrue(self.m.e_raridade_promo(p))
        self.assertEqual(self.m.alvo(p), 0)
        self.assertFalse(self.m.escondida(p))             # guarda-se se tiver
        self.assertFalse(self.m.e_master(p))

    def test_a_sp_pede_1_como_as_ven_sp(self):
        self.assertEqual(self.m.alvo(self.rad()["rad-sp1"]), 1)

    def test_os_aliases(self):
        al = {r["alias"]: r["printing_id"] for r in self.con.execute(
            "SELECT alias, printing_id FROM catalog.printing_aliases")}
        self.assertEqual(al["rad-001-p"], "rad-001-p")
        self.assertEqual(al["rad-001-p2"], "rad-001-p2")
        self.assertNotIn("rad-p", al)                     # serviria a todas as promos
        self.assertEqual(al["rad-001"], "rad-001")
        self.assertEqual(al["rad-r01a"], "rad-r01a")

    def test_correr_outra_vez_da_o_mesmo(self):
        antes = {k: {c: v for c, v in x.items() if c != "fetched_at"} for k, x in self.rad().items()}
        res = self.dotgg.sync(linhas_api=DOTGG, log=lambda *_: None)
        depois = {k: {c: v for c, v in x.items() if c != "fetched_at"} for k, x in self.rad().items()}
        self.assertEqual(res["sets"], {"RAD": 12})
        self.assertEqual(antes, depois)

    def test_uma_edicao_fora_da_lista_recusa(self):
        with self.assertRaises(ValueError):
            self.dotgg.sync(["OGN"], linhas_api=DOTGG, log=lambda *_: None)


class TestARiftScribeNaoDuplica(Base):
    """A PROVA que a ordem pediu: cópias marcadas na RAD da dotgg, e depois um
    sync da RiftScribe a trazer a RAD com os ids dela."""

    def setUp(self):
        super().setUp()
        self.marcadas = {"rad-001": 3, "rad-001a": 1, "rad-002": 1, "rad-006": 1,
                         "rad-001-p": 1, "rad-sp1": 2, "rad-r01a": 1, "rad-t02": 1}
        for pid, n in self.marcadas.items():
            self.collection.adjust(self.con, pid, n, source="test")
        self.copias_antes = self.copias()
        self.res_rs = self.sync_riftscribe()
        self.rad_depois = self.rad()

    def test_uma_linha_por_impressao(self):
        chaves = [(r["collector_number"], r["variant"]) for r in self.rad_depois.values()]
        self.assertEqual(len(chaves), len(set(chaves)))
        self.assertEqual(len(self.rad_depois), 12)       # as 9 dela + as 3 que só a dotgg tem

    def test_zero_copias_orfas_e_a_mesma_contagem(self):
        self.assertEqual(self.orfas(), [])
        self.assertEqual(self.copias(), self.copias_antes)
        self.assertEqual(sum(self.copias().values()), sum(self.marcadas.values()))

    def test_os_ids_que_existiam_ficaram(self):
        self.assertEqual(set(self.rad_depois), {
            "rad-001", "rad-001a", "rad-002", "rad-003", "rad-006", "rad-006-star",
            "rad-001-p", "rad-001-p2", "rad-r01", "rad-r01a", "rad-t02", "rad-sp1"})
        self.assertEqual(self.res_rs["sets"], {"RAD": 12})

    def test_os_dados_passaram_a_ser_os_da_riftscribe(self):
        r = self.rad_depois["rad-001"]
        self.assertEqual(r["fonte"], "riftscribe")
        self.assertEqual(r["public_code"], "RAD-001/005")
        self.assertEqual(r["description"], "texto da RiftScribe")
        self.assertEqual(self.rad_depois["rad-sp1"]["public_code"], "RAD-SP1/001")

    def test_o_que_so_a_dotgg_tem_fica(self):
        for pid in ("rad-001-p", "rad-001-p2", "rad-r01a"):
            self.assertEqual(self.rad_depois[pid]["fonte"], "dotgg", pid)

    def test_as_regras_continuam_iguais_depois(self):
        r = self.rad_depois
        self.assertTrue(self.m.e_overnumbered(r["rad-006"]))
        self.assertTrue(self.m.escondida(r["rad-006-star"]))
        self.assertEqual(self.m.alvo(r["rad-001-p"]), 0)

    def test_a_riftscribe_outra_vez_nao_muda_nada(self):
        self.sync_riftscribe()
        self.assertEqual(set(self.rad()), set(self.rad_depois))
        self.assertEqual(self.orfas(), [])

    def test_a_dotgg_por_cima_nao_escreve_sobre_a_riftscribe(self):
        res = self.dotgg.sync(linhas_api=DOTGG, log=lambda *_: None)
        r = self.rad()
        self.assertEqual(len(r), 12)
        self.assertEqual(r["rad-001"]["description"], "texto da RiftScribe")
        self.assertEqual(r["rad-001"]["fonte"], "riftscribe")
        self.assertEqual(res["da_riftscribe"], 9)
        self.assertEqual(self.orfas(), [])

    def test_a_riftscribe_sem_uma_carta_dela_apaga_so_essa(self):
        self.sync_riftscribe([c for c in RIFTSCRIBE if c["id"] != "rad-003-005"])
        r = self.rad()
        self.assertNotIn("rad-003", r)
        self.assertIn("rad-001-p", r)                     # a da dotgg não é dela para apagar


class TestASegundaChave(Base):
    """Se a RiftScribe escrever uma variante de outra maneira, casa pela
    impressão (número, categoria, carta) — mas só se for UMA."""

    def test_uma_sp_com_outra_escrita_casa_na_mesma(self):
        api = [_rs("rad-sp1-001", 1, "sp01", "RAD-SP01", "Ahri, Confident", "epic")]
        self.collection.adjust(self.con, "rad-sp1", 1, source="test")
        self.sync_riftscribe(api + [c for c in RIFTSCRIBE if c["variant"] != "sp1"])
        self.assertIn("rad-sp1", self.rad())
        self.assertEqual(self.orfas(), [])


class TestKindPorEdicao(unittest.TestCase):
    def test_o_extra_por_edicao_so_vale_nessa_edicao(self):
        from riftvault import catalog
        extra = {"rad:sp": "special_alt"}
        self.assertEqual(catalog.kind_of("sp1", extra, "RAD"), "special_alt")
        self.assertEqual(catalog.kind_of("sp1", extra, "VEN"), "special")

    def test_a_serie_com_a_no_fim_e_alt_art(self):
        from riftvault import catalog
        self.assertEqual(catalog.kind_of("r01a"), "alt_art")
        self.assertEqual(catalog.kind_of("r01"), "rune_promo")
        self.assertEqual(catalog.kind_of("p"), "special")


class TestPartirId(unittest.TestCase):
    def test_os_padroes_medidos(self):
        from riftvault import dotgg
        self.assertEqual(dotgg.partir_id("RAD-001"), ("RAD", 1, ""))
        self.assertEqual(dotgg.partir_id("RAD-061A"), ("RAD", 61, "a"))
        self.assertEqual(dotgg.partir_id("RAD-168-STAR"), ("RAD", 168, "star"))
        self.assertEqual(dotgg.partir_id("RAD-038-P2"), ("RAD", 38, "p2"))
        self.assertEqual(dotgg.partir_id("RAD-R04A"), ("RAD", 4, "r04a"))
        self.assertEqual(dotgg.partir_id("RAD-T06"), ("RAD", 6, "t06"))
        self.assertEqual(dotgg.partir_id("RAD-SP5"), ("RAD", 5, "sp5"))

    def test_um_id_que_nao_se_conhece_diz_se(self):
        from riftvault import dotgg
        with self.assertRaises(dotgg.IdDesconhecido):
            dotgg.partir_id("RAD-001-MB-P")


if __name__ == "__main__":
    unittest.main()

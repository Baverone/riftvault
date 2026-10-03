"""O CONTADOR DAS RUNAS PASSA A SER POR EDIÇÃO, e começa a ZERO (2026-10-03).

André, hoje, escolhido entre quatro hipóteses: *"Zera e recontas por edicao"*.
A 02/10 corrigiu-se a REFERÊNCIA («nesta edição», `tests/test_runas_por_edicao`)
e o CONTADOR ficou por resolver: a chave era só o `card_key`, por isso o mesmo
número aparecia nas quatro páginas. As 14 que ele contou à mão (Body 3, Calm 3,
Chaos 2, Fury 3, Mind 1, Order 2) não tinham edição gravada e reparti-las era
inventá-las.

O que esta bateria fixa:

* **a migração** — a chave passa a `(card_key, set_id)`, a tabela fica VAZIA, e
  as seis linhas vão para a `rune_counter_antes` com o `updated_at` de cada uma:
  zerar não é apagar o rasto. Leva backup, é idempotente, e nada se perde;
* **o contador é da edição** — um `+` no OGN não aparece no SFD, e em «Todas» é
  a soma; o alvo conta CÉLULAS (runa × edição);
* **não há sementeira** — ler o bloco deixou de escrever na base;
* **o ecrã ajuda a recontar** — o aviso diz que o zero é de hoje e mostra o que
  ele tinha contado; dispensar marca a data e NÃO apaga o rasto;
* **a CLI** — ver e mexer por edição, e o rasto a aparecer sempre;
* **nada mais mexe** — a fotografia de níveis, wantlist, Faltas, A mais, valor e
  `copies`, sem o relógio dentro, com a prova pela negativa ao lado;
* **o que estava decidido fica de pé** — as runas do master set a 3, a base na
  sequência, a alt art dela retirada, e as `VEN-R` dentro da Coleção.

Tudo contra pastas temporárias (`tests.fixture.Vault`) e um config próprio: o
`data/` e o `riftvault_config.json` a sério nunca são tocados.
"""

from __future__ import annotations

import contextlib
import importlib
import io
import json
import os
import re
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.fixture import REPO, Vault, config_decks_sem_alt_art  # noqa: E402

config_decks_sem_alt_art()

APP_JS = REPO / "riftvault" / "web" / "app.js"
CSS = REPO / "riftvault" / "web" / "style.css"

#: As chaves que andam com o relógio — a lição de 02/10: uma fotografia com o
#: relógio dentro passa ou falha conforme o segundo em que calhe.
RELOGIOS = ("generated_at", "synced_at", "updated_at", "as_of", "quando", "ts",
            "arquivado_em", "dispensado_em")


def sem_relogio(obj):
    if isinstance(obj, dict):
        return {k: sem_relogio(v) for k, v in obj.items() if k not in RELOGIOS}
    if isinstance(obj, (list, tuple)):
        return type(obj)(sem_relogio(x) for x in obj)
    return obj


def _config(caso, extra: dict | None = None) -> None:
    caminho = Path(tempfile.gettempdir()) / f"riftvault-runas-contador-{os.getpid()}.json"
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
        _config(self)
        self.v = Vault()
        self.addCleanup(self.v.close)
        from riftvault import db, metrics, runas_vista
        for m in (metrics, runas_vista):
            importlib.reload(m)
        self.metrics, self.rv, self.db = metrics, runas_vista, db

    def catalogo(self):
        """A Calm Rune nas quatro edições e a Fury Rune só no OGN; o OGS sem
        runa nenhuma — é a forma do catálogo real.

        OGN: base 9 + alt art 6 (retirada) = 15; Fury base 3
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
        for pid, cents in (("ogn-001-100", 150), ("ogn-042-100", 11),
                           ("ogn-042a-100", 500), ("ogn-007-100", 11), ("ven-r02", 12)):
            con.execute("INSERT INTO catalog.price_latest (printing_id, price_cents) "
                        "VALUES (?,?)", (pid, cents))
        collection.adjust(con, "ogn-001-100", 3, source="test")
        collection.adjust(con, "ogn-042-100", 9, source="test")
        collection.adjust(con, "ogn-042a-100", 6, source="test")
        collection.adjust(con, "ogn-007-100", 3, source="test")
        collection.adjust(con, "ven-r02", 1, source="test")
        collection.adjust(con, "ct-1", 2, source="test")
        collection.adjust(con, "ct-2", 12, source="test")
        collection.adjust(con, "ct-3", 5, source="test")
        return con

    def tabela(self, con):
        return {(r["card_key"], r["set_id"]): r["qty"] for r in
                con.execute("SELECT card_key, set_id, qty FROM rune_counter")}

    def ed(self, p, sid):
        return p["por_edicao"][sid]

    def runa(self, vista, nome):
        return next(x for x in vista["runas"] if x["name"] == nome)


# ---------------------------------------------------------------------------
# 1. A MIGRAÇÃO — zerar não é apagar o rasto
# ---------------------------------------------------------------------------

class TestAMigracao(Base):
    """A tabela ganha `set_id` e fica vazia; as seis linhas dele vão para o
    arquivo, com os números e as datas. É a única coisa desta ordem que não se
    desfaz, e por isso leva backup e tem prova pela negativa."""

    #: As seis linhas a sério, como estavam no `data/` dele a 2026-10-03 (ver a
    #: cópia em `data/backups/rune_counter-antes-de-por-edicao-*.json`).
    DELE = [
        ("body rune", 3, 2, "2026-10-01T13:00:01+00:00"),
        ("calm rune", 3, 27, "2026-09-26T21:44:48+00:00"),
        ("chaos rune", 2, 9, "2026-10-01T13:00:12+00:00"),
        ("fury rune", 3, 4, "2026-09-26T21:44:41+00:00"),
        ("mind rune", 1, 12, "2026-09-26T21:44:55+00:00"),
        ("order rune", 2, 22, "2026-09-26T19:48:38+00:00"),
    ]

    def base_de_ontem(self) -> Path:
        """Um `vault.db` com a `rune_counter` do regime antigo e as seis linhas
        dele — é a base que a migração vai encontrar."""
        caminho = self.v.root / "data" / "ontem.db"
        caminho.parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(caminho)
        con.execute("CREATE TABLE users (user_id INTEGER PRIMARY KEY, slug TEXT, "
                    "nome TEXT)")
        con.execute("CREATE TABLE rune_counter (card_key TEXT PRIMARY KEY, "
                    "qty INTEGER NOT NULL CHECK (qty >= 0), "
                    "seeded_from INTEGER NOT NULL, updated_at TEXT NOT NULL, "
                    "user_id INTEGER)")
        con.executemany("INSERT INTO rune_counter VALUES (?,?,?,?,1)", self.DELE)
        con.commit()
        con.close()
        return caminho

    def test_as_seis_linhas_dele_vao_para_o_arquivo_e_a_tabela_fica_vazia(self):
        caminho = self.base_de_ontem()
        con = sqlite3.connect(caminho)
        con.row_factory = sqlite3.Row
        n = self.db._migrar_rune_counter_por_edicao(con)
        self.assertEqual(n, 6)
        self.assertEqual([tuple(r) for r in con.execute("SELECT * FROM rune_counter")],
                         [], "a tabela tinha de ficar vazia: ele vai recontar")
        guardado = [(r["card_key"], r["qty"], r["seeded_from"], r["updated_at"])
                    for r in con.execute("SELECT * FROM rune_counter_antes "
                                         "ORDER BY card_key")]
        self.assertEqual(guardado, self.DELE,
                         "o rasto das 14 que ele contou à mão perdeu-se")
        self.assertEqual(sum(r[1] for r in guardado), 14)
        con.close()

    def test_a_chave_nova_e_card_key_mais_set_id(self):
        caminho = self.base_de_ontem()
        con = sqlite3.connect(caminho)
        con.row_factory = sqlite3.Row
        self.db._migrar_rune_counter_por_edicao(con)
        pk = [r["name"] for r in con.execute("PRAGMA table_info(rune_counter)") if r["pk"]]
        self.assertEqual(sorted(pk), ["card_key", "set_id"])
        self.assertNotIn("seeded_from",
                         [r["name"] for r in con.execute("PRAGMA table_info(rune_counter)")],
                         "sem sementeira, a coluna da sementeira não faz sentido")
        # A mesma runa em duas edições são duas linhas, e não colidem.
        con.execute("INSERT INTO rune_counter VALUES ('calm rune','OGN',3,'x',1)")
        con.execute("INSERT INTO rune_counter VALUES ('calm rune','SFD',9,'x',1)")
        self.assertEqual(con.execute("SELECT COUNT(*) FROM rune_counter").fetchone()[0], 2)
        with self.assertRaises(sqlite3.IntegrityError):
            con.execute("INSERT INTO rune_counter VALUES ('calm rune','OGN',1,'x',1)")
        con.close()

    def test_e_idempotente_e_nao_volta_a_arquivar(self):
        caminho = self.base_de_ontem()
        con = sqlite3.connect(caminho)
        con.row_factory = sqlite3.Row
        self.db._migrar_rune_counter_por_edicao(con)
        con.execute("INSERT INTO rune_counter VALUES ('calm rune','OGN',4,'x',1)")
        con.commit()
        self.assertEqual(self.db._migrar_rune_counter_por_edicao(con), 0)
        self.assertEqual([tuple(r)[:3] for r in con.execute("SELECT * FROM rune_counter")],
                         [("calm rune", "OGN", 4)],
                         "a segunda corrida mexeu no que ele já contou")
        self.assertEqual(
            con.execute("SELECT COUNT(*) FROM rune_counter_antes").fetchone()[0], 6)
        con.close()

    def test_numa_base_criada_de_raiz_a_forma_e_a_mesma(self):
        """O `schema.sql` e a migração têm de dar a MESMA tabela, senão uma
        base nova e uma base migrada medem coisas diferentes."""
        con = self.v.connect()
        de_raiz = [(r[1], r[2], r[3], r[5]) for r in
                   con.execute("PRAGMA table_info(rune_counter)")]
        con.close()
        caminho = self.base_de_ontem()
        c2 = sqlite3.connect(caminho)
        c2.row_factory = sqlite3.Row
        self.db._migrar_rune_counter_por_edicao(c2)
        migrada = [(r[1], r[2], r[3], r[5]) for r in
                   c2.execute("PRAGMA table_info(rune_counter)")]
        c2.close()
        # O `user_id` de raiz traz `REFERENCES` e a migração também; o resto
        # (nome, tipo, NOT NULL, PK) tem de bater certo coluna a coluna.
        self.assertEqual(de_raiz, migrada)

    def test_leva_backup_antes_de_refazer_a_tabela(self):
        """É a coleção dele: refazer uma tabela sem backup não se faz."""
        con = self.v.connect()
        antes = len(list(self.v.data.glob("backups/*.db")))
        con.execute("DROP TABLE rune_counter")
        con.execute("CREATE TABLE rune_counter (card_key TEXT PRIMARY KEY, "
                    "qty INTEGER NOT NULL, seeded_from INTEGER NOT NULL, "
                    "updated_at TEXT NOT NULL, user_id INTEGER)")
        con.execute("INSERT INTO rune_counter VALUES ('calm rune',3,27,'x',1)")
        self.db._migrar_rune_counter_por_edicao(con)
        depois = sorted(p.name for p in self.v.data.glob("backups/*.db"))
        self.assertEqual(len(depois), antes + 1, depois)
        self.assertTrue(any("antes-do-contador-de-runas-por-edicao" in n
                            for n in depois), depois)
        con.close()

    def test_as_duas_tabelas_estao_classificadas_como_de_dono(self):
        """Uma tabela nova que ninguém classifique fica sem `user_id` e sem
        entrar no apagar de uma conta."""
        self.assertIn("rune_counter", self.db.TABELAS_DE_DONO)
        self.assertIn("rune_counter_antes", self.db.TABELAS_DE_DONO)
        con = self.v.connect()
        for t in ("rune_counter", "rune_counter_antes"):
            cols = [r[1] for r in con.execute(f"PRAGMA table_info({t})")]
            self.assertIn("user_id", cols, t)
        con.close()

    def test_o_contador_de_ontem_nao_volta_a_valer_por_acidente(self):
        """A prova pela negativa: se a migração copiasse os números para uma
        edição, o OGN abria a dizer 3 em vez de 0 — e ele não os contou lá."""
        caminho = self.base_de_ontem()
        con = sqlite3.connect(caminho)
        con.row_factory = sqlite3.Row
        self.db._migrar_rune_counter_por_edicao(con)
        self.assertEqual(
            con.execute("SELECT COUNT(*) FROM rune_counter").fetchone()[0], 0)
        con.close()


# ---------------------------------------------------------------------------
# 2. O RASTO no ecrã, e o «dispensar»
# ---------------------------------------------------------------------------

class TestORasto(Base):

    def arquivar(self, con):
        """O que a migração deixa — aqui escrito à mão, para o teste não
        depender da ordem das migrações."""
        con.executemany(
            "INSERT INTO rune_counter_antes (card_key, qty, seeded_from, "
            "updated_at, arquivado_em) VALUES (?,?,?,?,?)",
            [("calm rune", 3, 27, "2026-09-26T21:44:48+00:00", "2026-10-03T10:00:00+00:00"),
             ("fury rune", 3, 4, "2026-09-26T21:44:41+00:00", "2026-10-03T10:00:00+00:00")])

    def test_sem_rasto_o_payload_diz_None(self):
        con = self.catalogo()
        self.assertIsNone(self.rv.payload(con)["antes"])
        con.close()

    def test_o_rasto_vem_no_payload_com_os_numeros_e_as_datas(self):
        con = self.catalogo()
        self.arquivar(con)
        a = self.rv.payload(con)["antes"]
        self.assertEqual(a["total"], 6)
        self.assertEqual(a["cards"], 2)
        self.assertEqual([r["card_key"] for r in a["linhas"]], ["calm rune", "fury rune"])
        self.assertEqual(a["linhas"][0]["qty"], 3)
        self.assertEqual(a["linhas"][0]["seeded_from"], 27)
        self.assertEqual(a["linhas"][0]["updated_at"], "2026-09-26T21:44:48+00:00")
        self.assertIsNone(a["dispensado_em"])
        self.assertIn("reposto a ZERO", a["aviso"])
        self.assertIn("por edição", a["aviso"])
        con.close()

    def test_dispensar_marca_a_data_e_NAO_apaga_o_rasto(self):
        con = self.catalogo()
        self.arquivar(con)
        a = self.rv.dispensar(con)
        self.assertIsNotNone(a["dispensado_em"])
        self.assertEqual(a["total"], 6, "dispensar apagou o rasto")
        self.assertEqual(len(self.rv.payload(con)["antes"]["linhas"]), 2)
        self.assertEqual(
            con.execute("SELECT COUNT(*) FROM rune_counter_antes").fetchone()[0], 2)
        # E volta a aparecer se ele quiser.
        self.assertIsNone(self.rv.dispensar(con, voltar=True)["dispensado_em"])
        con.close()

    def test_dispensar_nao_mexe_no_contador_nem_na_colecao(self):
        con = self.catalogo()
        self.arquivar(con)
        self.rv.ajustar(con, "calm rune", "OGN", 4)
        copias = [tuple(r) for r in con.execute("SELECT * FROM copies ORDER BY 1")]
        self.rv.dispensar(con)
        self.assertEqual(self.tabela(con), {("calm rune", "OGN"): 4})
        self.assertEqual([tuple(r) for r in con.execute("SELECT * FROM copies ORDER BY 1")],
                         copias)
        con.close()

    def test_o_ecra_mostra_o_aviso_enquanto_nao_for_dispensado(self):
        js = APP_JS.read_text(encoding="utf-8")
        corpo = re.search(r"function runasAviso\(\) \{(.*?)\n\}\n", js, re.S).group(1)
        self.assertIn("state.runas.antes", corpo)
        self.assertIn("a.dispensado_em", corpo)       # dispensado, não aparece
        self.assertIn("a.total", corpo)               # o que ele tinha contado
        self.assertIn("a.aviso", corpo)
        self.assertIn("runas-dispensar", corpo)
        desenho = re.search(r"async function renderRunasVista\(reler = false\) \{(.*?)\n\}\n",
                            js, re.S).group(1)
        self.assertIn("runasAviso()", desenho)
        # O aviso atravessa a grelha (o `#runas-vista` é uma `.grid`): sem isto
        # ficava uma célula estreita ao lado dos tiles.
        css = CSS.read_text(encoding="utf-8")
        self.assertIn(".runas-aviso {", css)
        self.assertIn("grid-column: 1 / -1", css.split(".runas-aviso {")[1][:200])

    def test_a_rota_de_dispensar(self):
        from riftvault import server
        con = self.catalogo()
        self.arquivar(con)
        con.close()
        app = server.app
        app.testing = True
        with app.test_client() as c:
            self.assertIsNone(c.get("/api/runas.json").get_json()["antes"]["dispensado_em"])
            r = c.post("/api/runas/dispensar", json={})
            self.assertEqual(r.status_code, 200)
            self.assertIsNotNone(r.get_json()["antes"]["dispensado_em"])
            self.assertIsNotNone(
                c.get("/api/runas.json").get_json()["antes"]["dispensado_em"])
            r = c.post("/api/runas/dispensar", json={"voltar": True})
            self.assertIsNone(r.get_json()["antes"]["dispensado_em"])


# ---------------------------------------------------------------------------
# 3. A CLI
# ---------------------------------------------------------------------------

class TestACLI(Base):

    def correr(self, *args):
        from riftvault import cli
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            codigo = cli.main(["runas", *args])
        return codigo, out.getvalue(), err.getvalue()

    def test_ve_e_mexe_por_edicao(self):
        con = self.catalogo()
        con.close()
        codigo, out, _ = self.correr("--edicao", "SFD", "--mais", "Calm Rune", "--n", "2")
        self.assertEqual(codigo, 0)
        self.assertIn("Calm Rune em SFD: 2 (nesta edição tens: 14)", out)
        codigo, out, _ = self.correr()
        self.assertEqual(codigo, 0)
        # Cada edição com o seu contador e o seu alvo.
        self.assertIn("OGN — contas 0 de 24", out)
        self.assertIn("SFD — contas 2 de 12", out)
        self.assertIn("Calm Rune      2/12   nesta edição: 14", out)
        self.assertIn("Calm Rune      0/12   nesta edição: 15", out)   # o OGN fica a 0
        self.assertIn("ao todo (a soma das edições): contas 2 de 60", out)

    def test_sem_edicao_recusa(self):
        con = self.catalogo()
        con.close()
        codigo, _, err = self.correr("--mais", "Calm Rune")
        self.assertEqual(codigo, 1)
        self.assertIn("--edicao", err)
        self.assertEqual(self.tabela(self.v.connect()), {})

    def test_uma_edicao_que_nao_tem_aquela_runa_recusa(self):
        con = self.catalogo()
        con.close()
        codigo, _, err = self.correr("--edicao", "SFD", "--mais", "Fury Rune")
        self.assertEqual(codigo, 1)
        self.assertIn("SFD", err)

    def test_o_rasto_aparece_sempre_na_consola(self):
        """Dispensado ou não: é o que ele confere enquanto reconta."""
        con = self.catalogo()
        con.executemany(
            "INSERT INTO rune_counter_antes (card_key, qty, seeded_from, "
            "updated_at, arquivado_em) VALUES (?,?,?,?,?)",
            [("calm rune", 3, 27, "2026-09-26T21:44:48+00:00", "2026-10-03T10:00:00+00:00"),
             ("fury rune", 3, 4, "2026-09-26T21:44:41+00:00", "2026-10-03T10:00:00+00:00")])
        con.close()
        _, out, _ = self.correr()
        self.assertIn("tinhas contado 6 ao todo", out)
        self.assertIn("calm rune      3", out)
        self.assertIn("a coleção dizia 27", out)
        codigo, out2, _ = self.correr("--dispensar")
        self.assertEqual(codigo, 0)
        self.assertIn("rasto fica", out2)
        _, out3, _ = self.correr()
        self.assertIn("tinhas contado 6 ao todo", out3)


# ---------------------------------------------------------------------------
# 4. NADA MAIS MEXE
# ---------------------------------------------------------------------------

class TestNadaMaisMexe(Base):
    """Níveis, wantlist, Faltas, A mais, valor e `copies` — sem o relógio
    dentro, e com a prova pela negativa ao lado."""

    def fotografia(self, con):
        from riftvault import a_mais, a_subir, faltas_edicao, prices
        cfg = self.rv.config.load()
        return sem_relogio({
            "niveis": self.metrics.niveis_payload(con, cfg),
            "index": self.metrics.index_payload(con, cfg=cfg),
            "wantlist": a_subir.wantlist(con),
            "master_faltas": {k: a_subir.master_faltas(con)[k]
                              for k in ("cards", "copies", "cents")},
            "faltas": faltas_edicao.payload(con, cfg)["totals"],
            "a_mais": a_mais.payload(con, cfg)["totals"],
            "valor": prices.collection_value(con),
            "sets": {sid: self.metrics.set_payload(con, sid, cfg)["progress"]
                     for sid in ("OGN", "OGS", "SFD", "UNL", "VEN")},
            "copies": sorted(tuple(r) for r in con.execute(
                "SELECT printing_id, qty, qty_foil FROM copies")),
        })

    def test_recontar_as_runas_nao_mexe_em_conta_nenhuma(self):
        con = self.catalogo()
        antes = self.fotografia(con)
        celulas = [("calm rune", "OGN"), ("calm rune", "SFD"), ("calm rune", "UNL"),
                   ("calm rune", "VEN"), ("fury rune", "OGN")]
        for ck, sid in celulas:
            self.rv.ajustar(con, ck, sid, 12)
        self.assertEqual(sum(self.tabela(con).values()), 60)
        self.assertEqual(self.fotografia(con), antes, "recontar mexeu em contas")
        for ck, sid in celulas:
            self.rv.ajustar(con, ck, sid, -12)
        self.assertEqual(self.fotografia(con), antes)
        con.close()

    def test_a_fotografia_nao_e_de_zeros(self):
        from riftvault import collection
        con = self.catalogo()
        antes = self.fotografia(con)
        collection.adjust(con, "ogn-001-100", 2, source="test")
        self.assertNotEqual(self.fotografia(con), antes)
        con.close()

    def test_a_fotografia_nao_tem_relogio(self):
        con = self.catalogo()
        texto = json.dumps(self.fotografia(con), default=str)
        for chave in RELOGIOS:
            self.assertNotIn(f'"{chave}"', texto)
        con.close()

    def test_nenhum_modulo_de_contas_conhece_a_tabela(self):
        pasta = REPO / "riftvault"
        for nome in ("metrics", "a_subir", "faltas", "faltas_edicao", "a_mais",
                     "uso_decks", "decks", "locais", "pending", "prices",
                     "collection", "cardmarket", "seguir", "catalog", "painel"):
            src = (pasta / f"{nome}.py").read_text(encoding="utf-8")
            for proibido in ("runas_vista", "rune_counter"):
                self.assertNotIn(proibido, src,
                                 f"{nome}.py conhece o contador das runas")


# ---------------------------------------------------------------------------
# 5. O QUE ESTAVA DECIDIDO FICA DE PÉ
# ---------------------------------------------------------------------------

class TestOQueEstavaDecididoFicaDePe(Base):

    def test_a_runa_do_master_set_pede_3_e_o_bloco_12(self):
        """O alvo da Coleção (2026-09-15) é 3; o 12 é só do bloco dele."""
        con = self.catalogo()
        col = self.metrics.set_payload(con, "OGN")
        na_grelha = {p["id"]: p for g in col["groups"] for p in g["printings"]}
        self.assertEqual(na_grelha["ogn-042-100"]["target"], 3)
        self.assertEqual(na_grelha["ogn-042-100"]["block"], "master")
        self.assertEqual(self.runa(self.rv.payload(con), "Calm Rune")["target"], 12)
        con.close()

    def test_a_alt_art_da_runa_continua_retirada(self):
        con = self.catalogo()
        calm = self.runa(self.ed(self.rv.payload(con), "OGN"), "Calm Rune")
        origens = {o["code"]: o for o in calm["origens"]}
        self.assertTrue(origens["OGN-042a/100"]["retirada"])
        self.assertEqual((calm["total"], calm["sem_retiradas"]), (15, 9))
        con.close()

    def test_as_promo_VEN_R_continuam_dentro_da_colecao(self):
        """Escondidas da grelha (2026-09-15), mas no `copies` e no valor."""
        from riftvault import prices
        con = self.catalogo()
        ven = self.runa(self.ed(self.rv.payload(con), "VEN"), "Calm Rune")
        self.assertTrue(ven["origens"][0]["escondida"])
        self.assertFalse(ven["origens"][0]["retirada"])
        self.assertEqual(
            con.execute("SELECT qty FROM copies WHERE printing_id='ven-r02'").fetchone()[0], 1)
        # 3 × 1,50 + 9 × 0,11 + 3 × 0,11 + a promo a 0,12 = 5,94 €.
        self.assertEqual(prices.collection_value(con)["cents"], 594)
        con.close()

    def test_o_payload_da_edicao_nao_traz_o_contador(self):
        con = self.catalogo()
        sp = self.metrics.set_payload(con, "OGN", self.rv.config.load())
        for proibido in ("runas", "por_edicao", "rune_counter", "antes"):
            self.assertNotIn(proibido, sp)
        con.close()


# ---------------------------------------------------------------------------
# 6. EM «TODAS» NÃO HÁ BOTÕES
# ---------------------------------------------------------------------------

class TestEmTodasNaoHaBotoes(Base):
    """Um clique ali não saberia a que edição somar, e escolher uma por ele
    era inventar o número outra vez."""

    def test_o_tile_so_desenha_os_steppers_com_uma_edicao_aberta(self):
        js = APP_JS.read_text(encoding="utf-8")
        tile = re.search(r"function runaTile\(x, v\) \{(.*?)\n\}\n", js, re.S).group(1)
        self.assertIn("v && v.set_id", tile)
        self.assertIn("soma_sem_botoes", tile)
        ajustar = re.search(r"async function runaAjustar\(ck, sid, delta\) \{(.*?)\n\}\n",
                            js, re.S).group(1)
        self.assertIn("if (!sid) return", ajustar)
        ligar = re.search(r"function ligarRunas\(\) \{(.*?)\n\}\n", js, re.S).group(1)
        self.assertIn("v && v.set_id", ligar)

    def test_a_frase_que_explica_vem_do_servidor(self):
        con = self.catalogo()
        p = self.rv.payload(con)
        self.assertIn("abre a edição", p["soma_sem_botoes"])
        con.close()


if __name__ == "__main__":
    unittest.main(verbosity=2)

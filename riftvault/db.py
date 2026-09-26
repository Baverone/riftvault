"""Ligações às duas bases de dados e migrações.

Como no mtgvault: `vault.db` é a base principal e `catalog.db` entra ATTACHed
como schema `catalog`. O SQLite resolve nomes não qualificados nas bases
anexadas, por isso `SELECT ... FROM printings` funciona à mesma.

`CREATE TABLE IF NOT EXISTS` não acrescenta colunas a tabelas já criadas —
toda a coluna nova tem de entrar também em `_migrate()`.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

from . import config


def _apply_schema(con: sqlite3.Connection, sql_file: str, schema: str = "main") -> None:
    sql = (config.PKG / sql_file).read_text(encoding="utf-8")
    if schema != "main":
        # Os .sql são escritos para a base principal; para a anexada é preciso
        # qualificar os CREATE.
        sql = sql.replace("CREATE TABLE IF NOT EXISTS ", f"CREATE TABLE IF NOT EXISTS {schema}.")
        sql = sql.replace("CREATE INDEX IF NOT EXISTS ", f"CREATE INDEX IF NOT EXISTS {schema}.")
    con.executescript(sql)


def _columns(con: sqlite3.Connection, table: str, schema: str = "main") -> set[str]:
    try:
        return {r[1] for r in con.execute(f"PRAGMA {schema}.table_info({table})")}
    except sqlite3.OperationalError:
        return set()


def backup(con: sqlite3.Connection, motivo: str, schema: str = "main",
           nome: str | None = None) -> Path | None:
    """Uma cópia de uma base ANTES de uma migração que lhe mexe nas tabelas.

    `VACUUM <schema> INTO` em vez de copiar o ficheiro: as bases estão em WAL e
    uma cópia de ficheiro podia apanhar uma a meio de uma transação. Vai
    para `data/backups/` (que está no `.gitignore`) e nunca se apaga sozinha —
    é a rede de segurança da coleção, que é a única coisa insubstituível aqui.

    `schema` é o nome do schema a copiar, e é um valor interno (nunca vem de
    fora): o SQLite não aceita um parâmetro ali. Com `catalog_only()` o catálogo
    É o `main`, e é por isso que o nome do ficheiro se passa à parte.

    Devolve o caminho, ou `None` se não deu (uma migração não pode falhar por
    causa do backup; quem chama decide).
    """
    nome = nome or ("vault" if schema == "main" else schema)
    alvo = config.DATA_DIR / "backups" / (
        f"{nome}-{motivo}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.db")
    try:
        alvo.parent.mkdir(parents=True, exist_ok=True)
        con.execute(f"VACUUM {schema} INTO ?", (str(alvo),))
        return alvo
    except (sqlite3.Error, OSError):
        return None


def _sql_da_copies(con: sqlite3.Connection) -> str:
    row = con.execute("SELECT sql FROM main.sqlite_master WHERE type='table' "
                      "AND name='copies'").fetchone()
    return (row[0] if row and row[0] else "").replace("\n", " ")


def _tirar_o_tecto_do_foil(con: sqlite3.Connection) -> None:
    """Deixa cair o `CHECK (qty_foil <= qty)` do modelo antigo do foil.

    O SQLite não sabe largar um CHECK: é preciso refazer a tabela (o
    procedimento de 12 passos da documentação deles). Aqui é a versão curta e
    segura porque ninguém aponta para a `copies` — não há FK para ela, nem
    índice próprio (a PK viaja no RENAME), nem trigger. Confirmado no
    `schema.sql`; se algum dia houver, tem de vir para aqui.

    OS NÚMEROS NÃO SE TOCAM, e é isso que faz esta migração não ter risco: o
    `qty` e o `qty_foil` de cada linha copiam-se tal e qual. O modelo mudou de
    LEITURA (o `qty_foil` deixou de estar dentro do `qty` e passou a somar-se),
    não de conteúdo — as cópias que ele marcou como foil já eram as foils que
    tem a mais das normais. Ver a verificação no CLAUDE.md.

    Tudo numa transação só, para o que ele gravar entretanto ficar de um lado
    ou do outro e nunca a meio: o SQLite serializa os escritores, por isso um
    `+` que chegue antes é copiado e um que chegue depois vai para a tabela
    nova.
    """
    con.execute("BEGIN IMMEDIATE")
    try:
        con.execute("CREATE TABLE copies_nova ("
                    "printing_id TEXT PRIMARY KEY, "
                    "qty INTEGER NOT NULL CHECK (qty >= 0), "
                    "updated_at TEXT NOT NULL, "
                    "qty_foil INTEGER NOT NULL DEFAULT 0 "
                    "  CHECK (qty_foil >= 0 AND qty_foil <= 9999))")
        con.execute("INSERT INTO copies_nova (printing_id, qty, updated_at, qty_foil) "
                    "SELECT printing_id, qty, updated_at, qty_foil FROM copies")
        con.execute("DROP TABLE copies")
        con.execute("ALTER TABLE copies_nova RENAME TO copies")
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise


def _migrar_price_latest(con: sqlite3.Connection, schema: str = "catalog") -> None:
    """As colunas que a `price_latest` ganhou depois da primeira versão.

    Corre com o catálogo ANEXADO (`connect`, schema `catalog`) e com o catálogo
    como base principal (`catalog_only`, schema `main`) — é a mesma tabela, e
    uma delas só a migrar deixava o `riftvault map` a olhar para colunas que não
    existem.

      `n_sellers`, `n_copies`     o tamanho da oferta (2026-09-10)
      `price_foil_cents`,
      `n_listings_foil`           o PREÇO DA FOIL, à parte (2026-09-26)

    As duas últimas levam BACKUP do catálogo antes. O `catalog.db` é
    reconstruível (`riftvault sync` + `riftvault map` + `riftvault prices`) e
    está no `.gitignore` — mas reconstruí-lo custa o catálogo inteiro e o
    mercado das cinco expansões, e o backup custa um `VACUUM INTO`. Idempotente:
    a segunda ligação já encontra as colunas e não faz nada.
    """
    tabela = "price_latest" if schema == "main" else f"{schema}.price_latest"
    cols = _columns(con, "price_latest", schema)
    if not cols:
        return
    for name in ("n_sellers", "n_copies"):
        if name not in cols:
            con.execute(f"ALTER TABLE {tabela} ADD COLUMN {name} "
                        f"INTEGER NOT NULL DEFAULT 0")
    # O preço da foil (André, 2026-09-26): *"podes meter filtro no cardtrader e
    # tirar o preco da foil mais barata?, para diferenciar os precos"*. Nasce
    # VAZIA (NULL em todas) e enche-se no `riftvault prices` seguinte; até aí as
    # cópias foil contam ao preço da normal, que é o fallback de sempre.
    if "price_foil_cents" not in cols or "n_listings_foil" not in cols:
        backup(con, "antes-do-preco-do-foil", schema=schema, nome="catalog")
        if "price_foil_cents" not in cols:
            con.execute(f"ALTER TABLE {tabela} ADD COLUMN price_foil_cents INTEGER")
        if "n_listings_foil" not in cols:
            con.execute(f"ALTER TABLE {tabela} ADD COLUMN n_listings_foil "
                        f"INTEGER NOT NULL DEFAULT 0")


def _migrate(con: sqlite3.Connection) -> None:
    """Colunas acrescentadas depois da primeira versão do schema.

    `CREATE TABLE IF NOT EXISTS` não acrescenta colunas a tabelas já criadas.
    """
    # A contagem de FOIL das comuns e incomuns (2026-09-22, `foil.py`). Uma
    # base criada de raiz já traz a coluna do `schema.sql`; uma que já exista
    # leva-a por aqui, com BACKUP antes — é a primeira migração desde o
    # início que toca na tabela `copies`, que é a coleção dele. Idempotente:
    # corre uma vez, na primeira ligação depois do merge.
    cols = _columns(con, "copies")
    if cols and "qty_foil" not in cols:
        backup(con, "antes-do-foil")
        con.execute("ALTER TABLE copies ADD COLUMN qty_foil INTEGER NOT NULL "
                    "DEFAULT 0 CHECK (qty_foil >= 0 AND qty_foil <= 9999)")

    # O FOIL SOMA-SE (André, 2026-09-26): *"as foils quando eu marco é que tenho
    # TAMBÉM foil, ou seja, normal + foil e não apenas 1, no caso daria 3+3"*.
    # O `CHECK (qty_foil <= qty)` era do modelo errado — com ele, uma carta que
    # ele só tenha em foil (0 normais, 2 foil) não se podia gravar. Sai, com
    # BACKUP antes, porque toca na tabela `copies`. Idempotente: a segunda
    # ligação já não encontra o CHECK antigo e não faz nada.
    if "qty_foil <= qty" in _sql_da_copies(con):
        backup(con, "antes-do-foil-somar")
        _tirar_o_tecto_do_foil(con)

    cols = _columns(con, "decks")
    if cols:
        for name, decl in (
            ("priority", "INTEGER NOT NULL DEFAULT 100"),  # 1 = principal
            ("legend", "TEXT"),
            ("champion", "TEXT"),
            ("display_name", "TEXT"),
            ("missing_json", "TEXT"),   # nomes da lista que não casaram no catálogo
        ):
            if name not in cols:
                con.execute(f"ALTER TABLE decks ADD COLUMN {name} {decl}")

    # As colunas da `price_latest`: o tamanho da oferta (2026-09-10) e o preço
    # da foil (2026-09-26). Vive numa função porque o `catalog_only()` também a
    # chama, com o catálogo como base principal.
    _migrar_price_latest(con, "catalog")

    # O histórico de preços mudou de casa: era do vault.db, passou a ser do
    # prices.db, para o robô do GitHub Actions poder fazer commit dele sem
    # tocar na coleção. Mudança só de ida, feita uma vez.
    # (o PRAGMA table_info não aceita `schema.tabela`; vai-se ao sqlite_master)
    if con.execute("SELECT 1 FROM main.sqlite_master WHERE type='table' "
                   "AND name='price_history'").fetchone():
        con.execute("INSERT OR IGNORE INTO prices.price_history "
                    "(printing_id, day, price_cents, currency) "
                    "SELECT printing_id, day, price_cents, currency FROM main.price_history")
        con.execute("DROP TABLE main.price_history")


def connect(readonly: bool = False) -> sqlite3.Connection:
    """Abre o vault.db com o catalog.db anexado como `catalog`."""
    config.ensure_dirs()
    con = sqlite3.connect(config.VAULT_DB, timeout=15.0, isolation_level=None)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    if not readonly:
        _apply_schema(con, "schema.sql")

    con.execute("ATTACH DATABASE ? AS catalog", (str(config.CATALOG_DB),))
    con.execute("ATTACH DATABASE ? AS prices", (str(config.PRICES_DB),))
    if not readonly:
        _apply_schema(con, "catalog_schema.sql", schema="catalog")
        _apply_schema(con, "prices_schema.sql", schema="prices")
        _migrate(con)
    return con


def catalog_only() -> sqlite3.Connection:
    """Só o catálogo — para o `sync`, que não precisa de tocar na coleção."""
    config.ensure_dirs()
    con = sqlite3.connect(config.CATALOG_DB, timeout=15.0, isolation_level=None)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    _apply_schema(con, "catalog_schema.sql")
    # Aqui o catálogo É o `main`. O `IF NOT EXISTS` do schema não acrescenta
    # colunas a uma tabela que já exista, por isso a migração corre também por
    # este caminho — senão um `riftvault map` num catálogo antigo ficava sem as
    # colunas até alguém abrir o vault.db.
    _migrar_price_latest(con, "main")
    return con


def catalog_is_empty(con: sqlite3.Connection) -> bool:
    row = con.execute("SELECT COUNT(*) AS n FROM catalog.printings").fetchone()
    return not row or row["n"] == 0

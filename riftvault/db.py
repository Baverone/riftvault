"""Ligações às duas bases de dados e migrações.

Como no mtgvault: `vault.db` é a base principal e `catalog.db` entra ATTACHed
como schema `catalog`. O SQLite resolve nomes não qualificados nas bases
anexadas, por isso `SELECT ... FROM printings` funciona à mesma.

`CREATE TABLE IF NOT EXISTS` não acrescenta colunas a tabelas já criadas —
toda a coluna nova tem de entrar também em `_migrate()`.
"""

from __future__ import annotations

import sqlite3
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


def _columns(con: sqlite3.Connection, table: str) -> set[str]:
    try:
        return {r[1] for r in con.execute(f"PRAGMA table_info({table})")}
    except sqlite3.OperationalError:
        return set()


def _migrate(con: sqlite3.Connection) -> None:
    """Colunas acrescentadas depois da primeira versão do schema.

    `CREATE TABLE IF NOT EXISTS` não acrescenta colunas a tabelas já criadas.
    """
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
    return con


def catalog_is_empty(con: sqlite3.Connection) -> bool:
    row = con.execute("SELECT COUNT(*) AS n FROM catalog.printings").fetchone()
    return not row or row["n"] == 0

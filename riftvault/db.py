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


def backup(con: sqlite3.Connection, motivo: str) -> Path | None:
    """Uma cópia do vault.db ANTES de uma migração que mexe na tabela `copies`.

    `VACUUM main INTO` em vez de copiar o ficheiro: o vault.db está em WAL e
    uma cópia de ficheiro podia apanhar uma base a meio de uma transação. Vai
    para `data/backups/` (que está no `.gitignore`) e nunca se apaga sozinha —
    é a rede de segurança da coleção, que é a única coisa insubstituível aqui.

    Devolve o caminho, ou `None` se não deu (uma migração não pode falhar por
    causa do backup; quem chama decide).
    """
    alvo = config.DATA_DIR / "backups" / (
        f"vault-{motivo}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.db")
    try:
        alvo.parent.mkdir(parents=True, exist_ok=True)
        con.execute("VACUUM main INTO ?", (str(alvo),))
        return alvo
    except (sqlite3.Error, OSError):
        return None


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
                    "DEFAULT 0 CHECK (qty_foil >= 0 AND qty_foil <= qty)")

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

    # O tamanho da oferta (2026-09-10): quantos vendedores e quantas cópias
    # estão à venda, a par do número de anúncios que já lá estava. É o mais
    # perto que há de "quais é que se vendem mais" — ver o `comuns.py`.
    cols = _columns(con, "price_latest", "catalog")
    if cols:
        for name in ("n_sellers", "n_copies"):
            if name not in cols:
                con.execute(f"ALTER TABLE catalog.price_latest "
                            f"ADD COLUMN {name} INTEGER NOT NULL DEFAULT 0")

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

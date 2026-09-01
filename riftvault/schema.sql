-- vault.db — a coleção do André. Vai para o Git.

-- O GRÃO DA COLEÇÃO: quantidade por impressão.
-- Não há coluna de acabamento: decisão do André (2026-08-31) de tratar foil e
-- normal como a mesma coisa. Se um dia mudar, acrescenta-se `finish TEXT NOT
-- NULL DEFAULT 'normal'` e passa-se a chave primária a (printing_id, finish).
--
-- Sem FK para catalog.printings: são bases de dados diferentes e o SQLite não
-- suporta FK entre bases anexadas. A integridade é garantida no código
-- (collection.resolve_printing valida contra o catálogo antes de escrever).
CREATE TABLE IF NOT EXISTS copies (
    printing_id TEXT    PRIMARY KEY,
    qty         INTEGER NOT NULL CHECK (qty >= 0),
    updated_at  TEXT    NOT NULL
);

-- Log de TUDO o que mexeu na coleção, e a base do `undo`.
CREATE TABLE IF NOT EXISTS ops (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT    NOT NULL,   -- ISO-8601 UTC
    printing_id TEXT    NOT NULL,
    delta       INTEGER NOT NULL,   -- +1 / -1 / +4 ...
    qty_after   INTEGER NOT NULL,
    source      TEXT    NOT NULL,   -- 'web' | 'cli' | 'import'
    -- Chave de idempotência. É isto que garante que cliques rápidos seguidos
    -- nunca se perdem NEM contam a dobrar: o cliente manda um delta com um id
    -- único, e um retry de rede com o mesmo id não volta a aplicar.
    request_id  TEXT    UNIQUE,
    undone_at   TEXT,               -- preenchido quando esta op é revertida
    undo_of     INTEGER             -- id da op que esta op reverte
);

CREATE INDEX IF NOT EXISTS ix_ops_ts       ON ops(ts DESC);
CREATE INDEX IF NOT EXISTS ix_ops_printing ON ops(printing_id, id DESC);

-- Preferências da UI (toggle "todas as impressões", filtros, ...).
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);

-- ---------------------------------------------------------------------------
-- Decks (fase 4). Já criadas para o schema não mudar a meio.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS decks (
    deck_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL UNIQUE,
    path         TEXT,
    content_hash TEXT,               -- dedup por conteúdo
    format       TEXT,
    imported_at  TEXT
);

CREATE TABLE IF NOT EXISTS deck_cards (
    deck_id  INTEGER NOT NULL,
    card_key TEXT    NOT NULL,       -- carta lógica: no deck, qualquer impressão conta
    role     TEXT    NOT NULL DEFAULT 'main',   -- main | runes | battlefields | legend | champion
    qty      INTEGER NOT NULL,
    raw_line TEXT,
    PRIMARY KEY (deck_id, card_key, role)
);

-- O histórico de preços vive no `prices.db` (ver riftvault/prices_schema.sql):
-- é escrito pelo robô do GitHub Actions, e não pode partilhar ficheiro com a
-- coleção sob pena de conflitos binários que custariam dados ao André.

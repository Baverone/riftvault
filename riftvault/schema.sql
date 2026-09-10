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

-- ONDE está cada cópia (André, 2026-09-10): *"a coleção fica em Binders de
-- coleção; as cartas dos decks ficam em decks, e haverá um Binder que será
-- apenas e exclusivamente para Decks/Venda"*.
--
-- Guarda SÓ o que não está na Coleção — `deck:<slug>` e `binder`. A Coleção é
-- `copies.qty` menos a soma disto, e por isso:
--
--   * a migração não escreve nada (tabela vazia = tudo na Coleção, que é o
--     default que ele pediu) e nenhuma cópia se pode perder no caminho;
--   * o `copies` continua a ser a única verdade sobre QUANTAS cópias existem,
--     e os `+`/`-` da grelha não têm de saber de locais.
--
-- A invariante `SUM(qty) <= copies.qty` é garantida no código
-- (`locais.ajustar_ao_total`), como toda a integridade entre bases aqui.
CREATE TABLE IF NOT EXISTS copy_locations (
    printing_id TEXT    NOT NULL,
    location    TEXT    NOT NULL,   -- 'binder' | 'deck:<slug>'
    qty         INTEGER NOT NULL CHECK (qty > 0),
    updated_at  TEXT    NOT NULL,
    PRIMARY KEY (printing_id, location)
);

-- O log dos movimentos de local, e a base do `riftvault local --undo`. É o
-- gémeo da `ops`, para a outra pergunta: a `ops` diz quantas cópias existem,
-- esta diz onde é que elas estão. O rasto legível para o André é o
-- `data/locais.log`, escrito ao mesmo tempo.
CREATE TABLE IF NOT EXISTS location_ops (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT    NOT NULL,
    printing_id TEXT    NOT NULL,
    qty         INTEGER NOT NULL,
    from_loc    TEXT    NOT NULL,
    to_loc      TEXT    NOT NULL,
    source      TEXT    NOT NULL,   -- 'web' | 'cli' | 'desfazer'
    request_id  TEXT    UNIQUE,     -- idempotência, como na `ops`
    undone_at   TEXT,
    undo_of     INTEGER
);

CREATE INDEX IF NOT EXISTS ix_location_ops_ts ON location_ops(ts DESC);
CREATE INDEX IF NOT EXISTS ix_copy_locations_loc ON copy_locations(location);

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

-- Cartas compradas que ainda não chegaram.
--
-- Ficam FORA de `copies`: ele ainda não as tem na mão, e a Coleção mede o que
-- está na caixa. Mas saem das faltas e das wantlists, senão comprava-as duas
-- vezes enquanto a encomenda vem a caminho.
--
-- Quando chegam, `pending.arrive()` passa-as para `copies` pelo caminho
-- normal (com entrada no `ops`, portanto com undo).
CREATE TABLE IF NOT EXISTS pending (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    printing_id TEXT    NOT NULL,
    qty         INTEGER NOT NULL CHECK (qty > 0),
    unit_cents  INTEGER,            -- o que pagou por cópia, se souber
    ordered_at  TEXT    NOT NULL,
    note        TEXT,               -- vendedor, nº de encomenda, o que for
    arrived_at  TEXT                -- preenchido quando entra na coleção
);
CREATE INDEX IF NOT EXISTS ix_pending_aberto ON pending(arrived_at, printing_id);

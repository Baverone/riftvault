-- catalog.db — cache do catálogo da RiftScribe.
-- Reconstruível com `riftvault sync`. Está no .gitignore.

-- Uma linha por edição descoberta em /api/cards/filters.
CREATE TABLE IF NOT EXISTS sets (
    set_id      TEXT PRIMARY KEY,
    name        TEXT,             -- vem do riftvault_config.json, NÃO da API
    sort_order  INTEGER,
    n_printings INTEGER NOT NULL DEFAULT 0,
    synced_at   TEXT
);

-- Uma linha por entrada de /api/cards. É o grão do catálogo E o grão da coleção.
CREATE TABLE IF NOT EXISTS printings (
    printing_id      TEXT PRIMARY KEY,          -- 'ogn-007a-298' (o `id` da API)
    set_id           TEXT NOT NULL,
    collector_number INTEGER NOT NULL,
    variant          TEXT NOT NULL DEFAULT '',  -- cru da API: '', 'a', 'star', 't04', 'sp4'
    -- `lane` separa as famílias que reutilizam o mesmo collector_number (ver
    -- ARMADILHA 1 no CLAUDE.md: em VEN, cn=4 é 4 cartas diferentes).
    lane             TEXT NOT NULL,             -- 'main' | 't' | 'r' | 'sp'
    group_key        TEXT NOT NULL,             -- 'OGN|7|main' -> agrupamento visual na grelha
    variant_kind     TEXT NOT NULL,             -- base|alt_art|signature|token|rune_promo|special
    variant_label    TEXT NOT NULL,             -- etiqueta do tile
    -- A carta lógica é o NOME, não o número (ver ARMADILHA 2: "Sett, Brawler"
    -- tem 5 impressões em 3 edições, com números diferentes).
    card_key         TEXT NOT NULL,
    public_code      TEXT,                      -- 'OGN-007a/298'
    name             TEXT NOT NULL,
    rarity           TEXT,                      -- pode vir 'showcase' na variante
    base_rarity      TEXT,                      -- raridade da base do grupo: é esta que conta
    faction          TEXT,
    domains_json     TEXT,
    type             TEXT,                      -- pode ser NULL (UNL-T04, UNL-T08)
    orientation      TEXT,
    energy           INTEGER,
    might            INTEGER,
    power            INTEGER,
    is_banned        INTEGER NOT NULL DEFAULT 0,
    is_token         INTEGER NOT NULL DEFAULT 0,
    description      TEXT,
    flavor_text      TEXT,
    artist           TEXT,
    keywords_json    TEXT,
    tags_json        TEXT,
    image_url        TEXT,                      -- originals/*.png
    image_small      TEXT,
    image_medium     TEXT,
    image_large      TEXT,
    image_path       TEXT,                      -- cache local em data/images/
    api_sort         INTEGER,                   -- ordem devolvida pela API (já agrupa variantes)
    fetched_at       TEXT
);

CREATE INDEX IF NOT EXISTS ix_printings_set   ON printings(set_id, api_sort);
CREATE INDEX IF NOT EXISTS ix_printings_card  ON printings(card_key);
CREATE INDEX IF NOT EXISTS ix_printings_group ON printings(group_key);

-- Carta lógica, derivada das impressões. É o grão da métrica PLAYSET JOGÁVEL.
CREATE TABLE IF NOT EXISTS cards (
    card_key        TEXT PRIMARY KEY,   -- nome normalizado
    name            TEXT NOT NULL,
    type            TEXT,
    faction         TEXT,
    domains_json    TEXT,
    is_banned       INTEGER NOT NULL DEFAULT 0,
    is_token        INTEGER NOT NULL DEFAULT 0,
    rep_printing_id TEXT,               -- impressão representativa (imagem na vista de deck)
    n_printings     INTEGER NOT NULL DEFAULT 0
);

-- Formas alternativas de escrever uma impressão, para o CLI e para as decklists.
-- 'ogn-100a', 'ogn-100a-298', 'ogn-100a/298', 'ogn-301*', 'ogn-301-star', ...
CREATE TABLE IF NOT EXISTS printing_aliases (
    alias       TEXT PRIMARY KEY,
    printing_id TEXT NOT NULL
);

-- Ponte para o CardTrader. Derivada, reconstruível com `riftvault map`.
-- O elo é estrutural: o `collector_number` do CardTrader já traz o sufixo da
-- variante ('007' base, '007a' arte alt., '299s' signature), por isso casa
-- diretamente com (set_id, collector_number, variant) da RiftScribe.
CREATE TABLE IF NOT EXISTS cardtrader_map (
    printing_id   TEXT PRIMARY KEY,
    blueprint_id  INTEGER NOT NULL,
    expansion_id  INTEGER,
    -- Nome e edição COMO O MERCADO OS ESCREVE. Não são os da RiftScribe:
    -- lá é "Loose Cannon", no mercado é "Jinx - Loose Cannon". É por estes
    -- que se exporta a wantlist, senão o Cardmarket não casa as cartas.
    market_name   TEXT,
    market_set    TEXT,
    cardmarket_id INTEGER,
    mapped_at     TEXT
);
CREATE INDEX IF NOT EXISTS ix_ctmap_blueprint ON cardtrader_map(blueprint_id);

-- Preço atual de TODAS as impressões. Fica no catálogo (descartável) porque
-- são 1180 linhas que mudam todos os dias — no vault.db inchava cada commit.
CREATE TABLE IF NOT EXISTS price_latest (
    printing_id TEXT PRIMARY KEY,
    price_cents INTEGER,
    currency    TEXT NOT NULL DEFAULT 'EUR',
    from_foil   INTEGER NOT NULL DEFAULT 0,  -- 1: não havia oferta normal
    n_listings  INTEGER NOT NULL DEFAULT 0,
    day         TEXT,
    source      TEXT NOT NULL DEFAULT 'cardtrader'
);

-- Impressões que o CardTrader lista e a RiftScribe ainda não tem: as runas do
-- SFD/UNL com as artes alternativas, as signatures do VEN, alguns tokens.
--
-- FICAM DE FORA DO CATÁLOGO DE PROPÓSITO. Não entram na grelha da Coleção nem
-- nas métricas: se entrassem, mudavam as barras de progresso e o master set
-- por causa de cartas que a fonte principal nem conhece, e sem informação de
-- jogo nenhuma (o CardTrader não dá tipo, domínio nem custo).
--
-- Servem só para a aba "Pimp decks" poder sugerir a versão certa — o André
-- quer as runas alternativas da edição do Legend do deck, e essas vivem aqui.
CREATE TABLE IF NOT EXISTS market_only (
    printing_id   TEXT PRIMARY KEY,   -- sintético: 'ct-<blueprint_id>'
    blueprint_id  INTEGER NOT NULL,
    set_id        TEXT NOT NULL,      -- o set_id NOSSO (OGN, SFD, ...)
    collector_raw TEXT,               -- como o CardTrader o escreve: 'R01a'
    card_key      TEXT,               -- a carta lógica, quando se consegue casar
    market_name   TEXT,
    market_set    TEXT,
    version       TEXT,               -- 'SFD | Alternate Art'
    cardmarket_id INTEGER,
    image_url     TEXT,
    seen_at       TEXT
);
CREATE INDEX IF NOT EXISTS ix_market_only_card ON market_only(card_key);

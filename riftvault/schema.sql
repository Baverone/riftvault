-- vault.db — a coleção de UM utilizador. O do André vai para o Git.

-- ---------------------------------------------------------------------------
-- QUEM É O DONO (2026-09-29): *"Amigos meus querem usar o site para organizar
-- a coleccao deles"*. Ver `riftvault/utilizador.py` e `docs/multi-utilizador.md`.
--
-- CADA UTILIZADOR TEM A SUA BASE — esta. A tabela `users` também está cá
-- dentro, com a linha do DONO deste ficheiro e só essa, e vem do
-- `users_schema.sql`, que é a definição única (o REGISTO do serviço, com toda
-- a gente, vive em `data/users/registo.db`, fora do Git — o porquê está lá).
--
-- O `user_id` das tabelas de dono não é o que SEPARA — quem separa é o
-- ficheiro. É o que faz cada linha dizer de quem é, e é o que o `db.connect`
-- verifica para recusar uma base aberta como o utilizador errado
-- (`utilizador.guardar`). O porquê de não ser um `WHERE user_id = ?` está no
-- `utilizador.py`, com os dois números que o decidiram.
--
-- O `catalog.db` (o jogo) e o `prices.db` (o mercado) NÃO levam dono: são
-- partilhados por toda a gente. Medido a 2026-09-29: a base de um utilizador
-- novo são 242 KB, contra 1,4 MB de catálogo e 745 KB de preços que ele não
-- volta a pagar.
-- ---------------------------------------------------------------------------

-- O GRÃO DA COLEÇÃO: quantidade por impressão.
-- O acabamento NÃO é parte do grão: decisão do André (2026-08-31) de tratar
-- foil e normal como a mesma coisa. A chave continua a ser `(printing_id)` e
-- o alvo do master set é por impressão — qualquer cópia o cumpre.
--
-- `qty_foil` (2026-09-22: *"para comuns e incomuns, coloca contagem para Foil
-- e Non-Foil, para todas as edicoes excepto Proving Grounds"*) é quantas
-- cópias FOIL ele tem daquela impressão.
--
-- O FOIL SOMA-SE AO NORMAL (André, 2026-09-26: *"as foils quando eu marco é
-- que tenho TAMBÉM foil, ou seja, normal + foil e não apenas 1, no caso daria
-- 3+3"*). São DUAS contagens independentes, e não uma repartição:
--
--     qty       = as cópias NORMAIS
--     qty_foil  = as cópias FOIL
--     total     = qty + qty_foil          (nunca se grava: é sempre a soma)
--
-- Com 3 normais e 3 foil ele tem SEIS cópias, não três. Até 2026-09-26 o
-- modelo era o contrário — o `qty` era o total e o `qty_foil` estava lá dentro
-- (`CHECK (qty_foil <= qty)`), e por isso marcar foil CONVERTIA uma cópia
-- normal. Era erro nosso; a migração está no `db._migrate`.
--
-- Consequências do modelo novo, todas de propósito:
--   * o `+` do foil não mexe no `qty`, e o `−` da grelha não mexe no
--     `qty_foil` — são dois contadores, cada um com o seu botão;
--   * `qty = 0` com `qty_foil > 0` é um estado LEGÍTIMO (uma carta que ele só
--     tenha em foil), e por isso o CHECK do tecto tinha de sair. O que fica é
--     `qty_foil >= 0` e um tecto largo, só por sanidade contra um dedo preso;
--   * o `qty` continua a ser o número que TODA a app conta — o foil é um
--     registo paralelo, com contadores próprios. Quem quiser somá-lo aos
--     alvos ou ao valor liga `foil.conta_para_coleccao`/`conta_para_valor`.
--
-- Sem FK para catalog.printings: são bases de dados diferentes e o SQLite não
-- suporta FK entre bases anexadas. A integridade é garantida no código
-- (collection.resolve_printing valida contra o catálogo antes de escrever).
--
-- O `user_id` aqui e nas outras tabelas de dono (2026-09-29): de quem é a
-- linha. É NULL enquanto ninguém a carimbou — e NULL quer dizer «do dono deste
-- ficheiro», porque é um ficheiro por pessoa. O `db.connect` carimba as NULL
-- na ligação seguinte e RECUSA as que tenham outro dono. Ver `utilizador.py`.
CREATE TABLE IF NOT EXISTS copies (
    printing_id TEXT    PRIMARY KEY,
    qty         INTEGER NOT NULL CHECK (qty >= 0),
    updated_at  TEXT    NOT NULL,
    qty_foil    INTEGER NOT NULL DEFAULT 0 CHECK (qty_foil >= 0 AND qty_foil <= 9999),
    user_id     INTEGER REFERENCES users(user_id)
);

-- O rasto da contagem de foil (2026-09-22). É o gémeo da `location_ops`, para
-- a outra pergunta: quantas cópias FOIL de cada impressão ele tem, e quando as
-- contou. Vive no vault.db, que vai para o Git.
--
-- As linhas com `source` acabado em `:ajuste ao total` são de ANTES de
-- 2026-09-26: eram as descidas forçadas do modelo em que o foil era um
-- subconjunto do total. Deixaram de se escrever — o `qty` e o `qty_foil` são
-- independentes —, mas as antigas ficam: é o registo do que se passou.
CREATE TABLE IF NOT EXISTS foil_ops (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT    NOT NULL,
    printing_id TEXT    NOT NULL,
    delta       INTEGER NOT NULL,
    qty_after   INTEGER NOT NULL,
    source      TEXT    NOT NULL,  -- 'web' | 'cli' | '<origem>:ajuste ao total'
    user_id     INTEGER REFERENCES users(user_id)
);
CREATE INDEX IF NOT EXISTS ix_foil_ops_ts ON foil_ops(ts DESC);

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
    user_id     INTEGER REFERENCES users(user_id),
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
    undo_of     INTEGER,
    user_id     INTEGER REFERENCES users(user_id)
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
    undo_of     INTEGER,            -- id da op que esta op reverte
    user_id     INTEGER REFERENCES users(user_id)
);

CREATE INDEX IF NOT EXISTS ix_ops_ts       ON ops(ts DESC);
CREATE INDEX IF NOT EXISTS ix_ops_printing ON ops(printing_id, id DESC);

-- Preferências da UI (toggle "todas as impressões", filtros, ...).
CREATE TABLE IF NOT EXISTS settings (
    key     TEXT PRIMARY KEY,
    value   TEXT,
    user_id INTEGER REFERENCES users(user_id)
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
    imported_at  TEXT,
    user_id      INTEGER REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS deck_cards (
    deck_id  INTEGER NOT NULL,
    card_key TEXT    NOT NULL,       -- carta lógica: no deck, qualquer impressão conta
    role     TEXT    NOT NULL DEFAULT 'main',   -- main | runes | battlefields | legend | champion
    qty      INTEGER NOT NULL,
    raw_line TEXT,
    user_id  INTEGER REFERENCES users(user_id),
    PRIMARY KEY (deck_id, card_key, role)
);

-- O HISTÓRICO do que cada deck PEDE (2026-09-17, para o separador «A mais»:
-- *"cartas que estavam num deck e deixaram de estar"*).
--
-- Até aqui não havia registo nenhum: a alocação aos decks é recalculada a
-- cada leitura a partir dos `decks/*.txt`, e a `copy_locations` só guarda o
-- que o André marca à mão (vazia no vault.db real). Uma carta que saía de uma
-- lista desaparecia sem rasto. Isto é o rasto: uma linha por (deck, carta)
-- de cada vez que a quantidade PEDIDA muda, escrita no fim do
-- `decks.import_all` — o único sítio por onde as listas entram. A última
-- linha por (deck, carta) é o estado; uma descida é uma libertação.
--
-- É o que a lista PEDE, não o que está alocado: a alocação também desce quando
-- ele vende uma cópia, e isso não é «saiu do deck». Um deck apagado deixa
-- todas as cartas dele a 0, com o rótulo guardado para o ecrã.
CREATE TABLE IF NOT EXISTS deck_need_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT    NOT NULL,
    slug        TEXT    NOT NULL,
    deck        TEXT    NOT NULL,   -- rótulo na altura (o deck pode já não existir)
    card_key    TEXT    NOT NULL,
    qty_before  INTEGER NOT NULL,
    qty_after   INTEGER NOT NULL,
    user_id     INTEGER REFERENCES users(user_id)
);
CREATE INDEX IF NOT EXISTS ix_deck_need_log_carta ON deck_need_log(slug, card_key, id DESC);

-- O CONTADOR DAS RUNAS DELE (André, 2026-09-19: *"runas nao contabilizam
-- nada, eu e que mexo nisso para minha referencia, nao entram para decks, nao
-- entram para coleccao, nada, so para mim"*).
--
-- É o número que o bloco «Runas — 12 de cada» mostra, e é DELE: os `+`/`−`
-- desse bloco escrevem aqui e em mais lado nenhum. Não é uma contagem de
-- cópias — o `copies` continua a ser a única verdade sobre o que ele tem —
-- e NINGUÉM o lê para fazer contas (`tests/test_runas_vista.py` recusa que
-- um módulo de contas importe o `runas_vista`). Vive no vault.db, e não num
-- ficheiro solto, porque é o vault.db que vai para o Git e para o backup.
--
-- UMA LINHA POR RUNA **E POR EDIÇÃO** (André, 2026-10-03: *"Zera e recontas
-- por edicao"*). Até 02/10 a chave era só o `card_key`: um número por runa,
-- repetido nas quatro páginas, porque as 14 que ele contou à mão não tinham
-- edição gravada e não se podiam repartir sem as inventar. Ele escolheu
-- recontar: a chave passou a `(card_key, set_id)` e o contador COMEÇA A ZERO.
--
-- NÃO HÁ SEMENTEIRA. Até 02/10 cada linha nascia com o que ele fisicamente
-- tinha dessa runa, para não ter de carregar 74 vezes; isso agora era o
-- contrário do que ele pediu (o número tem de ser o que ELE conta, não o que
-- a coleção calcula). Uma linha só nasce de um `+`, e por isso **LER o bloco
-- deixou de escrever**. Uma runa sem linha lê-se 0.
CREATE TABLE IF NOT EXISTS rune_counter (
    card_key    TEXT    NOT NULL,
    set_id      TEXT    NOT NULL,
    qty         INTEGER NOT NULL CHECK (qty >= 0),
    updated_at  TEXT    NOT NULL,
    user_id     INTEGER REFERENCES users(user_id),
    PRIMARY KEY (card_key, set_id)
);

-- O RASTO DO CONTADOR DE ANTES DE 2026-10-03 — zerar não é apagar.
--
-- As seis linhas que a `rune_counter` tinha (14 cópias ao todo: Body 3, Calm
-- 3, Chaos 2, Fury 3, Mind 1, Order 2) foram contadas À MÃO por ele e não se
-- recuperam de fonte nenhuma. Ficam aqui, com o `updated_at` de cada uma, para
-- ele poder conferir o que tinha ANTES de recontar — a página mostra-as
-- enquanto ele não dispensar o aviso (`dispensado_em`), e o `riftvault runas`
-- mostra-as sempre. Não é contabilidade: ninguém a lê para fazer contas.
CREATE TABLE IF NOT EXISTS rune_counter_antes (
    card_key      TEXT    PRIMARY KEY,
    qty           INTEGER NOT NULL,  -- o que ele tinha contado
    seeded_from   INTEGER NOT NULL,  -- o que a coleção dizia na sementeira
    updated_at    TEXT    NOT NULL,  -- o último toque DELE, na altura
    arquivado_em  TEXT    NOT NULL,
    dispensado_em TEXT,              -- NULL = o aviso ainda aparece no ecrã
    user_id       INTEGER REFERENCES users(user_id)
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
--
-- O ACABAMENTO DA ENCOMENDA (`foil`, 2026-09-27). Até aqui a `pending` guardava
-- a IMPRESSÃO e mais nada — e quando os `+`/`−` chegaram às Faltas, onde metade
-- do separador é de FOILS (2026-09-27), uma foil encomendada entrava na coleção
-- como NORMAL. Isso estragava a contagem dele, que são duas colunas
-- independentes (`copies.qty` e `copies.qty_foil`), por isso a linha passou a
-- dizer o que foi comprado:
--
--     foil = 0   uma cópia normal   -> quando chega, soma ao `copies.qty`
--     foil = 1   uma cópia foil     -> quando chega, soma ao `copies.qty_foil`
--
-- As linhas que já cá estavam ficam a 0, que é o que eram: até 2026-09-27 só
-- havia como encomendar normais. A migração está no `db._migrar_pending_foil`.
CREATE TABLE IF NOT EXISTS pending (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    printing_id TEXT    NOT NULL,
    qty         INTEGER NOT NULL CHECK (qty > 0),
    unit_cents  INTEGER,            -- o que pagou por cópia, se souber
    ordered_at  TEXT    NOT NULL,
    note        TEXT,               -- vendedor, nº de encomenda, o que for
    arrived_at  TEXT,               -- preenchido quando entra na coleção
    foil        INTEGER NOT NULL DEFAULT 0 CHECK (foil IN (0, 1)),
    user_id     INTEGER REFERENCES users(user_id)
);
CREATE INDEX IF NOT EXISTS ix_pending_aberto ON pending(arrived_at, printing_id);

-- ---------------------------------------------------------------------------
-- A VENDA EM CURSO (André, 2026-09-25): *"permite-me marcar as cartas que
-- estou a vender no momento para apresentar a conta a pessoa"*. Ver `venda.py`.
-- ---------------------------------------------------------------------------

-- As cartas que ele está a vender AGORA. Uma linha por IMPRESSÃO (é ele que
-- escolhe a versão que tem na mão), uma venda de cada vez — o «limpar venda»
-- esvazia a tabela.
--
-- MARCAR PARA VENDA NÃO TIRA NADA DE LADO NENHUM: isto é uma lista de
-- intenção e mais nenhum módulo a lê. Os níveis, o denominador, as Faltas, as
-- wantlists, o valor, o A mais, os decks, o foil e as cópias próprias dão
-- exactamente os mesmos números com a tabela cheia ou vazia
-- (`tests/test_venda.py` fotografa-os). Quem baixa as cópias é o botão
-- separado «marcar como vendidas» (`venda.vender`), pelo `collection.adjust`.
--
-- A `origem` (2026-09-27) diz DE ONDE veio a linha: `NULL` é ele a marcá-la à
-- mão, `deck:<slug>` é uma cópia própria de um deck que deixou de ser
-- principal ou foi desfeito (*"se eu 'desfazer' o deck ou deixar de ser o
-- principal, essas cartas passam a venda (apenas se valerem pelo menos 0,50
-- euros)"*). É o que deixa a página dizer de onde vieram e tirá-las de uma
-- vez — entrar na Venda não é vender.
CREATE TABLE IF NOT EXISTS sale_lines (
    printing_id TEXT    PRIMARY KEY,
    qty         INTEGER NOT NULL CHECK (qty > 0),
    added_at    TEXT    NOT NULL,
    origem      TEXT,
    user_id     INTEGER REFERENCES users(user_id)
);

-- O TREND DO CARDMARKET, metido À MÃO por ele, por impressão.
--
-- A app não tem — nem pode ter — preços do Cardmarket: o `price_latest` é do
-- CardTrader e é a oferta mais barata, a API oficial deles está fechada a
-- novas candidaturas e o site responde 403 a pedidos automáticos. Por isso o
-- número vem do campo que ele preenche a olhar para a página da carta lá, e
-- fica guardado com a DATA, para a venda seguinte vir preenchida e para se
-- poder dizer que está velho (`venda.trend_valido_dias`). Nunca se escreve
-- aqui um preço do CardTrader.
CREATE TABLE IF NOT EXISTS cardmarket_trend (
    printing_id TEXT    PRIMARY KEY,
    cents       INTEGER NOT NULL CHECK (cents >= 0),
    updated_at  TEXT    NOT NULL,
    source      TEXT    NOT NULL,  -- 'web' | 'cli' — sempre à mão
    user_id     INTEGER REFERENCES users(user_id)
);

-- O registo das vendas FECHADAS. Uma linha por carta, agrupadas pelo
-- `sale_id` (o instante em que ele carregou em «marcar como vendidas»), com o
-- Trend que estava em vigor nessa altura: a conta de uma venda antiga não
-- muda quando o Trend mudar. As cópias descem pelo `collection.adjust`, por
-- isso o desfazer é o de sempre (a `ops`).
CREATE TABLE IF NOT EXISTS sale_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT    NOT NULL,
    sale_id     TEXT    NOT NULL,
    printing_id TEXT    NOT NULL,
    qty         INTEGER NOT NULL,
    unit_cents  INTEGER,            -- o Trend na altura; NULL = linha sem Trend
    source      TEXT    NOT NULL,
    user_id     INTEGER REFERENCES users(user_id)
);
CREATE INDEX IF NOT EXISTS ix_sale_log_venda ON sale_log(sale_id, id);

-- ---------------------------------------------------------------------------
-- PRODUTO SELADO (André, 2026-09-25): *"um separador que e 'Produto Selado',
-- em que vai tudo o que e produtos de coleccao do Riftbound […] para eu saber
-- o que ha, o que tenho e o que nao tenho"*. Ver `selado.py`.
-- ---------------------------------------------------------------------------

-- Quantas unidades ele tem de cada produto selado. O `product_id` é
-- `ct-<blueprint_id>` (o que veio do CardTrader) ou `cfg-<slug>` (um produto
-- escrito à mão no `selado.extra`). Começa VAZIA — tudo a zero.
--
-- O SELADO NÃO ENTRA NA COLEÇÃO. Esta tabela não é lida por módulo nenhum de
-- contas: os níveis, o denominador, o A mais, as Faltas, as wantlists, o valor
-- da Coleção, os decks, o foil, as cópias próprias e a Venda dão exactamente
-- os mesmos números com ela cheia ou vazia (`tests/test_selado.py`
-- fotografa-os). O valor do selado é um total PRÓPRIO, nunca somado ao da
-- Coleção — uma caixa por abrir não é uma carta no binder.
CREATE TABLE IF NOT EXISTS sealed_copies (
    product_id TEXT    PRIMARY KEY,
    qty        INTEGER NOT NULL CHECK (qty >= 0),
    updated_at TEXT    NOT NULL,
    user_id    INTEGER REFERENCES users(user_id)
);

-- O PREÇO DO CARDMARKET, METIDO À MÃO, por produto selado (2026-09-28).
--
-- Porque é que existe: o preço da aba vem do CardTrader, e 7 dos 30 produtos
-- não têm lá oferta nenhuma — liam-se «—», que ele leu como «não está
-- disponível». Dois deles TÊM oferta no Cardmarket (medida a 2026-09-28 pelo
-- Chrome dele: o *Unleashed Sleeved Booster* a 13,00 € e o *Replacement Card
-- Booster* a 35,00 €), e a app não a pode ir buscar: o Cardmarket responde 403
-- a pedidos automáticos e a API deles está fechada a novas candidaturas.
--
-- É o mesmo mecanismo do Trend da Venda (`cardmarket_trend`, 2026-09-25) e
-- pela mesma razão — o que não se pode medir, escreve-se à mão, com a data.
-- Tabela à parte porque a chave é outra: ali é `printing_id` (uma carta), aqui
-- é `product_id` (`ct-<blueprint>` ou `cfg-<slug>`). Meter ids de produto numa
-- coluna chamada `printing_id` era mentir no nome e sujar as leituras da Venda.
--
-- NÃO ENTRA NA COLEÇÃO, como a `sealed_copies`: só o valor do selado a lê.
CREATE TABLE IF NOT EXISTS sealed_price (
    product_id TEXT    PRIMARY KEY,
    cents      INTEGER NOT NULL CHECK (cents >= 0),
    updated_at TEXT    NOT NULL,
    source     TEXT    NOT NULL,  -- 'web' | 'cli' — sempre à mão
    user_id    INTEGER REFERENCES users(user_id)
);

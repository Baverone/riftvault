-- prices.db — histórico de preços. VAI para o Git, separado do vault.db.
--
-- PORQUÊ UM FICHEIRO À PARTE
--     O GitHub Actions corre o `riftvault prices` sozinho e faz commit do que
--     escreve. Se isso fosse para dentro do vault.db, um dia em que o André
--     tivesse mexido na coleção localmente daria um conflito num ficheiro
--     BINÁRIO — e resolver um conflito de SQLite é escolher uma das versões e
--     perder a outra. A coleção é a única coisa insubstituível aqui.
--
--     Com o histórico à parte, o robô só toca no prices.db e o vault.db é
--     sempre e só do André. Na pior das hipóteses perde-se um dia de preços.

CREATE TABLE IF NOT EXISTS price_history (
    printing_id TEXT    NOT NULL,
    day         TEXT    NOT NULL,   -- YYYY-MM-DD
    price_cents INTEGER NOT NULL,
    currency    TEXT    NOT NULL DEFAULT 'EUR',
    PRIMARY KEY (printing_id, day)
);

CREATE INDEX IF NOT EXISTS ix_price_hist ON price_history(printing_id, day DESC);

-- Tamanho da OFERTA ao longo do tempo (2026-09-10).
--
-- PORQUE É QUE ISTO EXISTE
--     O André perguntou quais as comuns e incomuns que "costumam vender-se
--     mais". Volume de vendas não existe em fonte pública nenhuma — o
--     Cardmarket responde 403 a bots e a API pública dele devolve 410. O que o
--     CardTrader dá é o lado da OFERTA: quantos anúncios, quantos vendedores e
--     quantas cópias estão à venda hoje.
--
--     Uma fotografia da oferta não diz nada sobre procura. Uma SÉRIE já diz
--     alguma coisa: listagens a cair com o preço a subir é gente a comprar.
--     Por isso isto começa a acumular agora — em Setembro de 2026 tem um dia
--     só, e a página diz que ainda não dá para tirar conclusões.
--
--     Fica no prices.db, com o histórico de preços, pelas mesmas razões: é o
--     robô que escreve, o vault.db é só do André.
--
-- SÓ QUANDO MEXE MESMO
--     `prices._guardar_oferta` só grava quando o número de anúncios muda pelo
--     menos 3 unidades ou 10% face ao último registo. O ficheiro vai para o
--     Git e cada commit guarda-o inteiro; gravar as ~1200 impressões todos os
--     dias engordava-o com o ruído de uma ou duas listagens.
CREATE TABLE IF NOT EXISTS listings_history (
    printing_id TEXT    NOT NULL,
    day         TEXT    NOT NULL,   -- YYYY-MM-DD
    n_listings  INTEGER NOT NULL,
    n_sellers   INTEGER NOT NULL DEFAULT 0,
    n_copies    INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (printing_id, day)
);

CREATE INDEX IF NOT EXISTS ix_listings_hist ON listings_history(printing_id, day DESC);

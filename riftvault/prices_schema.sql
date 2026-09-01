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

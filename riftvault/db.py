"""Ligações às duas bases de dados e migrações.

Como no mtgvault: `vault.db` é a base principal e `catalog.db` entra ATTACHed
como schema `catalog`. O SQLite resolve nomes não qualificados nas bases
anexadas, por isso `SELECT ... FROM printings` funciona à mesma.

`CREATE TABLE IF NOT EXISTS` não acrescenta colunas a tabelas já criadas —
toda a coluna nova tem de entrar também em `_migrate()`.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from . import config, guarda, utilizador

# AS TABELAS DE DONO (2026-09-29). São as que guardam o que é de UMA pessoa, e
# são as que levaram a coluna `user_id`. Fica aqui, numa lista só, porque três
# coisas a leem e têm de ler a mesma: a migração, o carimbo/guarda do
# `utilizador.guardar` e o apagar de uma conta (`utilizador.apagar`).
#
# UMA TABELA NOVA NO `vault.db` TEM DE SER CLASSIFICADA: ou é de dono e vem
# para aqui (ganha `user_id`, índice, e entra no apagar de uma conta), ou é do
# serviço e diz-se porquê. O `test_multi_utilizador` rebenta se aparecer uma
# que ninguém classificou — é a rede para quem vier a seguir.
#
# A `users` NÃO está cá: é o registo de quem existe, não é dado de ninguém.
# O `catalog.db` e o `prices.db` também não — são partilhados por toda a gente
# (ver `riftvault/utilizador.py`).
TABELAS_DE_DONO = (
    "copies", "copy_locations", "foil_ops", "location_ops", "ops", "pending",
    "sale_lines", "sale_log", "cardmarket_trend", "sealed_copies",
    "sealed_price", "rune_counter", "rune_counter_antes", "settings",
    "decks", "deck_cards", "deck_need_log",
)


class Ligacao(guarda.Ligacao):
    """Uma ligação que sabe DE QUEM são os dados que tem abertos.

    O `sqlite3.Connection` não deixa pôr-lhe atributos (não tem `__dict__`), e
    o dono tem de viajar com a ligação: todas as camadas recebem um `con` e
    nenhuma recebe um `user_id`. Uma subclasse é a maneira de o fazer sem
    mudar 134 assinaturas.

    **`riftvault_user = None` NÃO quer dizer «o André»** (2026-09-29, a ordem
    das guardas): quer dizer «não se sabe», e nesse estado **tocar numa das
    `TABELAS_DE_DONO` rebenta** (`guarda.SemDono`), com a tabela nomeada. É a
    diferença entre um esquecimento que se vê e um que serve a coleção de
    alguém a quem não é dono dela — ver `riftvault/guarda.py`.
    """


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

    **O VAULT VAI PARA A PASTA DE BACKUPS DE QUEM É** (2026-10-02, achado 2 do
    varrimento): a cópia da coleção de um amigo caía solta entre as do André.
    **O CATÁLOGO E OS PREÇOS NÃO: são PARTILHADOS**, não são de ninguém, e por
    isso o backup deles fica em `data/backups/` seja quem for que esteja a
    correr a migração — mandá-lo para a pasta do amigo que abriu a app primeiro
    era dizer que o catálogo é dele. O discriminante é o `schema`: só o `main`
    de uma ligação ao vault é de dono.

    Devolve o caminho, ou `None` se não deu (uma migração não pode falhar por
    causa do backup; quem chama decide).
    """
    nome = nome or ("vault" if schema == "main" else schema)
    pasta = (config.backups_dir(con) if schema == "main"
             else config.DATA_DIR / "backups")
    alvo = pasta / (
        f"{nome}-{motivo}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.db")
    try:
        alvo.parent.mkdir(parents=True, exist_ok=True)
        # O `guarda.a_copiar` é preciso e não é enfeite: o `VACUUM INTO`
        # **anexa o ficheiro de destino por dentro**, e o guarda recusa
        # `ATTACH` numa ligação já ligada a um utilizador. Medido a
        # 2026-09-29 — sem esta porta, armar o guarda partia todas as
        # migrações com backup.
        with guarda.a_copiar(con):
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


def _migrar_rune_counter_por_edicao(con: sqlite3.Connection) -> int:
    """O contador das runas passa a ser POR EDIÇÃO, e começa a ZERO (2026-10-03).

    André, hoje: *"Zera e recontas por edicao"* — escolhido entre quatro
    hipóteses, depois de a 02/10 se ter corrigido a referência «nesta edição» e
    de o CONTADOR ter ficado por resolver. A chave era só o `card_key`, por isso
    o mesmo número aparecia nas quatro páginas: as 14 que ele contou à mão não
    tinham edição gravada e reparti-las era inventá-las.

    **ZERAR NÃO É APAGAR O RASTO.** As seis linhas vão para a
    `rune_counter_antes` com o `qty`, o `seeded_from` e o `updated_at` de cada
    uma — é o que ele vai conferir enquanto reconta, no ecrã e no `riftvault
    runas`. Fora disso há a cópia de segurança em `data/backups/` (JSON e SQL),
    tirada à mão antes desta mudança.

    REFAZ A TABELA porque o SQLite não sabe mudar uma PRIMARY KEY, e por isso
    leva BACKUP: é uma tabela do vault.db. Numa transação só, para o que ele
    carregar entretanto ficar de um lado ou do outro. Idempotente: a segunda
    ligação já encontra o `set_id` e não faz nada — nem backup, senão cada
    arranque do `serve` deixava um.

    CORRE ANTES do `_migrar_user_id`, como o tecto do foil: quem refaz uma
    tabela tem de passar antes de haver uma coluna a mais para copiar. A
    `user_id` da tabela nova vem da migração seguinte (ou do `schema.sql`, numa
    base de raiz) e as linhas arquivadas são carimbadas pelo
    `utilizador.guardar`, como as outras.

    Devolve quantas linhas arquivou (0 quando não havia nada a fazer).
    """
    cols = _columns(con, "rune_counter")
    if not cols or "set_id" in cols:
        return 0
    backup(con, "antes-do-contador-de-runas-por-edicao")
    agora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    con.execute("BEGIN IMMEDIATE")
    try:
        # A tabela do rasto primeiro: se isto falhasse depois do DROP, as 14
        # dele desapareciam. (`schema.sql` já a criou numa base de raiz; aqui
        # faz falta para uma base que vem de ontem.)
        con.execute("CREATE TABLE IF NOT EXISTS rune_counter_antes ("
                    "card_key TEXT PRIMARY KEY, "
                    "qty INTEGER NOT NULL, "
                    "seeded_from INTEGER NOT NULL, "
                    "updated_at TEXT NOT NULL, "
                    "arquivado_em TEXT NOT NULL, "
                    "dispensado_em TEXT, "
                    "user_id INTEGER REFERENCES users(user_id))")
        n = con.execute(
            "INSERT OR IGNORE INTO rune_counter_antes "
            "(card_key, qty, seeded_from, updated_at, arquivado_em) "
            "SELECT card_key, qty, seeded_from, updated_at, ? FROM rune_counter",
            (agora,)).rowcount
        con.execute("DROP TABLE rune_counter")
        con.execute("CREATE TABLE rune_counter ("
                    "card_key TEXT NOT NULL, "
                    "set_id TEXT NOT NULL, "
                    "qty INTEGER NOT NULL CHECK (qty >= 0), "
                    "updated_at TEXT NOT NULL, "
                    "user_id INTEGER REFERENCES users(user_id), "
                    "PRIMARY KEY (card_key, set_id))")
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise
    return max(0, n)


def _migrar_pending_foil(con: sqlite3.Connection) -> None:
    """A coluna `foil` da `pending` (2026-09-27, com os `+`/`−` nas Faltas).

    Metade do separador «Faltas» é de FOILS desde 2026-09-27, e ele passou a
    poder marcar «já encomendei» também lá. A `pending` guardava a IMPRESSÃO e
    não o acabamento: sem esta coluna, uma foil encomendada entrava na coleção
    como normal — e o `copies.qty` e o `copies.qty_foil` são duas contagens
    independentes desde 2026-09-26. Estragar-lhe a contagem é o erro que esta
    coluna existe para não cometer.

    LEVA BACKUP: mexe numa tabela do vault.db, que é a coleção dele. As linhas
    que já cá estão ficam a `0` — eram todas de cópias normais, porque até hoje
    não havia outra maneira de encomendar. Numa transação só, para o que ele
    encomendar entretanto ficar de um lado ou do outro. Idempotente: a segunda
    ligação já encontra a coluna e não faz nada.
    """
    cols = _columns(con, "pending")
    if not cols or "foil" in cols:
        return
    backup(con, "antes-do-pendente-foil")
    con.execute("BEGIN IMMEDIATE")
    try:
        con.execute("ALTER TABLE pending ADD COLUMN foil INTEGER NOT NULL "
                    "DEFAULT 0 CHECK (foil IN (0, 1))")
        con.execute("COMMIT")
    except Exception:
        con.execute("ROLLBACK")
        raise


def _migrar_sale_lines_origem(con: sqlite3.Connection) -> None:
    """A coluna `origem` da `sale_lines` (2026-09-27, com o Deck Principal).

    Sem ela não se sabe que linhas da Venda vieram de desfazer um deck, e ele
    pediu para isso ser VISÍVEL e para as poder tirar de uma vez. As linhas que
    já cá estão ficam a `NULL` — foram todas marcadas à mão, que era a única
    maneira que havia.

    LEVA BACKUP na mesma: é uma tabela do vault.db, e a regra desta casa é essa
    (a tabela é só de intenção, o backup custa um `VACUUM INTO`). Idempotente.
    """
    cols = _columns(con, "sale_lines")
    if not cols or "origem" in cols:
        return
    backup(con, "antes-da-origem-da-venda")
    con.execute("BEGIN IMMEDIATE")
    try:
        con.execute("ALTER TABLE sale_lines ADD COLUMN origem TEXT")
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


def _migrar_user_id(con: sqlite3.Connection) -> list[str]:
    """A coluna `user_id` nas tabelas de dono (2026-09-29, multi-utilizador).

    LEVA BACKUP: mexe em todas as tabelas do vault.db, que é a coleção dele. É
    um `ALTER TABLE ADD COLUMN` por tabela — não refaz tabela nenhuma, por isso
    **não toca num número**: nem o `qty`, nem o `qty_foil`, nem o `updated_at`.
    A coluna nasce a NULL em todas as linhas e é o `utilizador.guardar` que a
    carimba a seguir, com o dono desta base.

    As PK NÃO mudam, e é decisão consciente: com um ficheiro por pessoa o
    `printing_id` continua a ser único dentro da base, e passá-las a
    `(user_id, ...)` obrigava a refazer dez tabelas na coleção dele para um
    ganho que só existe se um dia tudo se juntar num ficheiro só. O que isso
    precisaria está escrito no `docs/multi-utilizador.md`.

    Idempotente: a segunda ligação já encontra as colunas e não faz nada —
    inclusive não faz backup, senão cada arranque do `serve` deixava um.
    Devolve as tabelas que migrou, para quem quiser dizê-lo.

    OS ÍNDICES vivem aqui e não no `schema.sql`, e é por obrigação: o schema
    corre ANTES desta migração, e numa base que já existe o `CREATE TABLE IF
    NOT EXISTS` é um no-op — um `CREATE INDEX ... (user_id)` no schema
    rebentava com «no such column: user_id» antes de a coluna nascer. Correm
    sempre, também numa base criada de raiz, onde as colunas já vêm do schema.
    """
    faltam = [t for t in TABELAS_DE_DONO
              if (cols := _columns(con, t)) and "user_id" not in cols]
    if faltam:
        backup(con, "antes-do-multi-utilizador")
        con.execute("BEGIN IMMEDIATE")
        try:
            for t in faltam:
                # Sem `REFERENCES` no ALTER: o SQLite não o aceita a apontar
                # para uma tabela que a base pode ainda não ter semeado. Numa
                # base criada de raiz a referência vem do `schema.sql`, onde a
                # ordem das tabelas é garantida.
                con.execute(f"ALTER TABLE {t} ADD COLUMN user_id INTEGER")  # noqa: S608
            con.execute("COMMIT")
        except Exception:
            con.execute("ROLLBACK")
            raise
    for t in TABELAS_DE_DONO:
        if "user_id" in _columns(con, t):
            con.execute(f"CREATE INDEX IF NOT EXISTS ix_{t}_user ON {t}(user_id)")
    return faltam


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

    # O contador das runas por EDIÇÃO (2026-10-03). Também refaz uma tabela, por
    # isso vem com o tecto do foil, antes do `_migrar_user_id`.
    _migrar_rune_counter_por_edicao(con)

    # O acabamento da encomenda (2026-09-27): sem ela uma foil encomendada nas
    # Faltas entrava na coleção como normal.
    _migrar_pending_foil(con)

    # De onde veio cada linha da Venda (2026-09-27): à mão, ou de um deck que
    # deixou de ser principal.
    _migrar_sale_lines_origem(con)

    # O que o público vê (2026-09-29): a coluna `users.publico`, numa base que
    # já tenha a tabela sem ela. Ver `privacidade.migrar`.
    from . import privacidade
    privacidade.migrar(con)

    # De quem é cada linha (2026-09-29, multi-utilizador). Vem depois das
    # outras de propósito: as que refazem tabelas (o tecto do foil) têm de
    # correr antes de haver uma coluna a mais para copiar.
    _migrar_user_id(con)

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


def vault_de(user_id: int | None = None) -> Path:
    """O ficheiro `vault.db` de um utilizador.

    O ANDRÉ FICA ONDE SEMPRE ESTEVE, e por isso o `RIFTVAULT_DB` continua a
    mandar nele — é a variável com que se aponta a coleção dele para outro
    sítio (é o que as medições e os testes usam). Os outros vivem em
    `data/users/<slug>/vault.db`.

    Para saber o slug é preciso ler o REGISTO (`data/users/registo.db`), que
    vive fora do Git — ver `utilizador.registo_db`.
    """
    uid = utilizador.atual() if user_id is None else int(user_id)
    if uid == utilizador.ANDRE:
        return config.VAULT_DB
    return utilizador.pasta(utilizador.registo(uid)["slug"]) / "vault.db"


def connect(readonly: bool = False, user_id: int | None = None) -> sqlite3.Connection:
    """Abre o vault.db DE UM UTILIZADOR, com o catálogo e os preços anexados.

    É A PORTA ÚNICA (2026-09-29). Todo o código que lê ou escreve dados de dono
    recebe um `con`, e todo o `con` sai daqui — por isso é aqui, e só aqui, que
    se responde a «de quem são estes dados». Quem não diz nada fica com o
    utilizador da sessão (`utilizador.atual()`, hoje sempre o André).

    A ligação leva o dono em `con.riftvault_user`, para quem precisar dele não
    ter de voltar a perguntar ao ambiente a meio de um pedido.

    O `catalog.db` e o `prices.db` são os MESMOS para toda a gente: o catálogo é
    o jogo e os preços são o mercado — não são a coleção de ninguém. Medido a
    2026-09-29: a base de um utilizador novo são 242 KB, contra 1,4 MB de
    catálogo e 745 KB de preços que ele não volta a pagar.
    """
    uid = utilizador.atual() if user_id is None else int(user_id)
    caminho = vault_de(uid)
    config.ensure_dirs()
    caminho.parent.mkdir(parents=True, exist_ok=True)

    con = sqlite3.connect(caminho, timeout=15.0, isolation_level=None,
                          factory=Ligacao)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    if not readonly:
        _apply_schema(con, "users_schema.sql")
        _apply_schema(con, "schema.sql")

    con.execute("ATTACH DATABASE ? AS catalog", (str(config.CATALOG_DB),))
    con.execute("ATTACH DATABASE ? AS prices", (str(config.PRICES_DB),))
    # O DONO POSTO ANTES DA MIGRAÇÃO (2026-10-02). Era posto no fim, e desde que
    # o backup de uma migração vai para a pasta de quem é (`config.backups_dir`)
    # isso deixou de servir: o `_migrate` chama o `backup()` e perguntava a uma
    # ligação que ainda não sabia de quem era. O ficheiro já está escolhido
    # (`vault_de(uid)`), por isso dizê-lo mais cedo não afirma nada de novo —
    # só o diz antes de alguém precisar. O guarda continua a armar-se no fim.
    con.riftvault_user = uid
    if not readonly:
        _apply_schema(con, "catalog_schema.sql", schema="catalog")
        _apply_schema(con, "prices_schema.sql", schema="prices")
        _migrate(con)
        # A ORDEM IMPORTA. O guarda pergunta à `users` de dentro de quem é o
        # ficheiro, e tem de a ver ANTES de lhe escrevermos a linha desta
        # sessão — senão via duas e não sabia qual era a do ficheiro.
        utilizador.guardar(con, uid, TABELAS_DE_DONO)
        # E só depois a linha do DONO, para a base se explicar a quem a abrir
        # ou a restaurar. O registo de quem existe é outro ficheiro, fora do
        # Git (`utilizador.registo_db`).
        _carimbar_dono(con, uid)
    # O GUARDA arma-se no fim, e a ordem importa: o catálogo e os preços já
    # estão anexados (depois disto a ligação não anexa mais nada) e o dono já
    # está posto (senão a própria migração rebentava). Ver `guarda.py`.
    guarda.armar(con, TABELAS_DE_DONO)
    return con


def abrir_vault(caminho: Path, user_id: int, readonly: bool = True) -> Ligacao:
    """Um `vault.db` À PARTE, pelo caminho, para trabalho de FICHEIRO.

    Não é a porta de quem lê a coleção — essa é o `connect()`, e é a única que
    anexa o catálogo, corre as migrações e carimba o dono. Isto é para quem
    precisa de abrir um ficheiro que ainda não está em serviço: o
    `conta.exportar` (contar as linhas e copiar), o `conta.importar` (ver de
    quem são as linhas ANTES de o pôr na pasta de alguém) e as medições.

    Vive aqui e não no `conta.py` para o `tests/test_isolamento.py` poder
    continuar a exigir que **ninguém abra uma base fora do `db.py`** — é essa
    regra que impede alguém chegar ao ficheiro errado sem passar por nenhuma
    das outras guardas.

    Leva o dono e o guarda armado, como qualquer ligação desta casa.
    """
    con = sqlite3.connect(caminho, timeout=15.0, isolation_level=None,
                          factory=Ligacao)
    con.row_factory = sqlite3.Row
    if not readonly:
        _apply_schema(con, "users_schema.sql")
        _apply_schema(con, "schema.sql")
    con.riftvault_user = int(user_id)
    guarda.armar(con, TABELAS_DE_DONO)
    return con


def _carimbar_dono(con: sqlite3.Connection, user_id: int) -> None:
    """Põe (e mantém) a linha do dono dentro da base dele.

    Copia-se do registo em vez de se escrever à mão para o nome e o slug não
    poderem divergir dos do registo — que é quem manda. Corre em toda a ligação
    porque é barato e porque assim uma mudança de nome no registo chega cá.

    O `publico` viaja com eles (2026-09-29): a escolha de privacidade decide-se
    no REGISTO (ver `privacidade.py`), e esta cópia é o SEGUNDO TESTEMUNHO dela
    — a única coisa que sobrevive a um restauro do registo, porque os dois
    ficheiros não se restauram juntos.

    **E POR ISSO ESTA CÓPIA NUNCA SE ALARGA AQUI** (2026-10-01). Até então
    escrevia-se o valor do registo por cima do que lá estava: com um registo
    restaurado de uma cópia antiga, isto apagava a escolha de hoje e republicava
    uma coleção que a pessoa tinha fechado. O `privacidade.reconciliar` devolve
    o mais fechado dos dois e cura o desacordo nos dois lados — alargar é só
    pelo `privacidade.definir`, que é uma pessoa a escolher.
    """
    from . import privacidade          # local: o `privacidade` importa o `db`
    reg = utilizador.registo(user_id)
    publico = privacidade.reconciliar(con, user_id, reg.get("publico"))
    con.execute("INSERT INTO users (user_id, nome, slug, criado_em, publico, "
                "auth_ref) VALUES (?,?,?,?,?,NULL) "
                "ON CONFLICT(user_id) DO UPDATE SET "
                "nome = excluded.nome, slug = excluded.slug, "
                "publico = excluded.publico",
                (reg["user_id"], reg["nome"], reg["slug"], reg["criado_em"],
                 publico))


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

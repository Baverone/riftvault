# riftvault para mais do que uma pessoa

**2026-09-29.** André: *"Amigos meus querem usar o site para organizar a
coleccao deles. Podes fazer com que mais pessoas possam organizar a coleccao
deles tambem usando o site?"*

Decisões dele no mesmo dia, nas respostas:

* contas a sério, com backend — não é guardar no browser de cada um;
* a prazo, **tudo** o que ele tem: coleção, foils, binder, wantlist, faltas,
  decks, selado, encomendas, venda;
* cada pessoa tem um site público **só de leitura**, como o dele hoje, num
  subdomínio com o nome dela — *"ao inves de Baverone.riftvault seria
  Miguel.riftvault"*;
* servidor: *"Comecamos no meu pc como recomendaste, se se tornar mais serio
  pensamos numa alternativa"* — o Flask continua no PC dele, exposto por
  **túnel Cloudflare**;
* começar por uma **fatia fina**, não tudo de uma vez.

Este documento é o que trava as decisões más daqui a três semanas. **Os números
são medidos, não estimados**, e diz-se onde foram medidos.

---

## 1. O que hoje é de UM só dono, e o que já é partilhado

Medido a 2026-09-29 no `data/` real.

### O que é dele, e só dele

| onde | o quê | tamanho / linhas |
|---|---|---|
| `data/vault.db` | a coleção e tudo o que ela arrasta — 16 tabelas | **864 KB, 4 778 linhas** |
| `riftvault_config.json` | as REGRAS: alvos, foil, master set, decks, selado, venda, abas | 1 ficheiro global |
| `decks/*.txt` | as listas de deck | hoje **0** (apagadas a 2026-09-28) |
| `data/locais.log`, `decks.log`, `encomendas.log` | as cópias legíveis dos registos — **de cada um, no `config.log_path(con, ...)`, desde 2026-10-02** | no `.gitignore` |
| `data/seguir/estado.json` | os jogadores que ele segue | 1 ficheiro |
| `site/` | o site publicado — um só | no Git |
| o `serve` no 8770 | um processo, uma coleção, sem autenticação | — |

As 16 tabelas de dono, com as linhas dele (é a lista `db.TABELAS_DE_DONO`):

```
copies 1046 · ops 3031 · foil_ops 560 · pending 130 · rune_counter 6
sealed_copies 5 · copy_locations 0 · location_ops 0 · sale_lines 0
sale_log 0 · cardmarket_trend 0 · sealed_price 0 · settings 0
decks 0 · deck_cards 0 · deck_need_log 0
                                                    TOTAL 4 778
```

### O que já é partilhado, e é a razão de isto ser barato

| onde | o quê | tamanho |
|---|---|---|
| `data/catalog.db` | o CATÁLOGO: 1 180 impressões, 935 cartas, os preços de hoje | **1,4 MB** |
| `data/prices.db` | o HISTÓRICO de preços e da oferta | **745 KB** |
| `data/selado_catalogo.json` | o catálogo do produto selado | 92 KB |
| `data/images/` | as imagens (hoje `static_images: "remote"`) | ~88 MB |

Nada disto é a coleção de ninguém: é **o jogo** e **o mercado**. Um utilizador
novo não paga nada disto — medido, a base de um utilizador com três cartas são
**242 KB**.

### O que está no caminho

1. **O `riftvault_config.json` é global e as regras dentro dele são DELE.** O
   `foil.raridades`, o `master_set.um_de_cada`, o `decks.so_base`, o
   `selado.excluidos`, o `venda.trend_valido_dias`. Hoje um amigo herda-as
   todas. Ver a secção 6.
2. **O `build.py` gera UM site**, para `site/`, a partir da sessão actual.
3. **O `serve` não tem autenticação nenhuma** e é isso que o CLAUDE.md diz
   desde 2026-09-02: *"quem chegar ao URL escreve na coleção"*. É aceitável na
   LAN; deixa de ser no momento em que houver um segundo utilizador.
4. **`config.DATA_DIR` e `DECKS_DIR` eram fixos.** O primeiro continua a ser (é
   a raiz de tudo); o segundo passou a ser por utilizador nesta fatia
   (`config.decks_dir(con)`).

---

## 2. O modelo, tabela a tabela

### A decisão de fundo: **um ficheiro por pessoa**, não `WHERE user_id = ?`

Duas medições decidiram-no, e as duas são verificáveis.

**(a) O `data/vault.db` está commitado num repositório PÚBLICO e é empurrado
sozinho.** `gh repo view` diz `"visibility":"PUBLIC"`; `git ls-files data/` diz
`data/vault.db`; `git rev-list --count HEAD -- data/vault.db` diz **95
commits**; a tarefa `riftvault-publicar` corre de 30 em 30 minutos. Pôr a
coleção de um amigo nesse ficheiro **publicava-a**, para sempre — o histórico
do Git não se apaga, e um repositório público é clonado e caches são feitas. A
coleção do André é dele e ele escolheu publicá-la; a do Miguel não é nossa para
publicar.

**(b) São 134 statements de SQL em 19 módulos a tocar nas tabelas de dono.**
Uma separação que dependa de 134 `WHERE` bem lembrados falha em silêncio e
falha do lado pior: um esquecido numa LEITURA mostra a coleção de um a outro;
num teste, 133 certos passam.

Com um ficheiro por pessoa a separação é **física** — os dados do outro não
estão sequer na ligação — e não há nada para esquecer. Zero dos 134 statements
mudou.

```
data/
  vault.db                     o ANDRÉ (user 1) — no Git, como sempre
  catalog.db  prices.db        PARTILHADOS, sem dono
  users/                       <<< NO .gitignore
    registo.db                 o REGISTO: quem existe
    miguel/vault.db            a coleção do Miguel
    miguel/decks/*.txt         as listas dele
```

### `users` — quem existe

```sql
CREATE TABLE users (
    user_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    nome       TEXT NOT NULL,
    slug       TEXT NOT NULL UNIQUE,   -- o subdomínio E o nome da pasta
    criado_em  TEXT NOT NULL,
    auth_ref   TEXT                    -- vazio; ver a secção 4
);
```

Vive em **dois** sítios, e a diferença é toda a questão da privacidade:

* **`data/users/registo.db`** — o registo do serviço, com toda a gente. **Fora
  do Git.**
* **dentro de cada `vault.db`** — a linha do DONO daquele ficheiro, e só essa,
  para o ficheiro se explicar a quem o abre ou o restaura de um backup.

**O registo não pode viver no `vault.db` do André** pela mesma razão (a): com
ele lá dentro, registar um amigo publicava-lhe o **nome** e o **slug** no
GitHub de 30 em 30 minutos — mesmo que a coleção dele ficasse privada, a
existência dele era publicada. Isto foi apanhado a meio desta corrida, por duas
sessões em paralelo (a `riftbound-2b` e a `riftbound-f3`), e corrigido antes do
merge; o desenho tinha a armadilha a dois metros da armadilha que ele próprio
identificou.

A definição da tabela está uma vez só, em `riftvault/users_schema.sql`, e é
aplicada nos dois — duas escritas da mesma tabela divergem, e é esta a tabela
que decide de quem são os dados.

### O `user_id` nas 16 tabelas de dono

`ALTER TABLE <t> ADD COLUMN user_id INTEGER` + `CREATE INDEX ix_<t>_user`, nas
16. **Não refaz tabela nenhuma, e por isso não toca num número.**

**Não é o `user_id` que separa — é o ficheiro.** Vale a pena ser explícito,
porque uma coluna que parece fazer uma coisa e não faz é pior do que não
existir. Ela faz três:

1. **cada linha diz de quem é**, e por isso uma base aberta como o utilizador
   errado é **detectável**: `utilizador.guardar()` recusa-a (`DonoErrado`). É a
   rede que apanha um ficheiro copiado para a pasta errada ou um backup
   restaurado por cima de outro;
2. **a migração faz-se hoje**, com um utilizador e zero risco, em vez de uma
   noite com vinte pessoas a usar isto;
3. **uma consolidação futura** (Postgres, ou um ficheiro só) passa a ser um
   `INSERT ... SELECT` sem ambiguidade.

`NULL` quer dizer «do dono deste ficheiro» — é um ficheiro por pessoa. O
`db.connect` carimba as `NULL` e recusa as de outro dono.

**Uma assimetria que é preciso conhecer:** numa base criada **de raiz** a coluna
leva `REFERENCES users(user_id)` e o SQLite recusa escrever um dono inventado;
numa base **migrada** não há FK — o SQLite não sabe acrescentar uma chave
estrangeira num `ADD COLUMN`, e refazer dezasseis tabelas da coleção dele para
a ganhar não se pagava. É por isso que o guarda do `utilizador.guardar` existe:
ele vale nos dois casos. Há teste para os dois.

**E o carimbo é PREGUIÇOSO.** O `utilizador.guardar` corre no `db.connect`, ou
seja antes das escritas dessa sessão: uma linha escrita durante a sessão fica a
`NULL` e só é carimbada na abertura seguinte — e uma base criada e nunca mais
reaberta tem as linhas **todas** a `NULL`. Nesse estado as linhas sozinhas não
distinguem ninguém. Por isso o guarda pergunta por **dois** sítios, e o
primeiro é o que manda: a tabela `users` de DENTRO da base, que é a identidade
do ficheiro e que o `db._carimbar_dono` escreve em toda a ligação. Foi apanhado
pela sessão `riftbound-2b` com um teste que forjava um manifesto e via a recusa
não acontecer; há agora teste para o ficheiro fresco.

### O que uma consolidação num ficheiro só ainda precisaria

Não sai de graça, e fica escrito para ninguém contar com isso:

* as **PK passam a `(user_id, ...)`** em `copies`, `copy_locations`,
  `rune_counter`, `settings`, `sale_lines`, `cardmarket_trend`,
  `sealed_copies`, `sealed_price` — e `decks.name` deixa de poder ser `UNIQUE`
  sozinho. São dez tabelas a refazer;
* os 134 statements passam todos a levar `WHERE user_id = ?`;
* e o `data/vault.db` tem de **sair do Git** primeiro, senão volta o problema
  (a).

---

## 3. A forma recomendada: leituras estáticas, túnel só para a edição

**Concordo, e implementa-se sem nada de novo.** A razão é que já é assim que o
riftvault funciona desde 2026-09-10, e por uma lição paga cara: nesse dia as
builds do Pages morreram a tarde inteira porque a RiftScribe caiu, e o site
ficou parado com ele fora de casa. A cura foi **gerar no PC e deixar o Pages só
servir**. A mesma forma responde agora a uma pergunta diferente — o risco.

```
  quem só espreita          ──> GitHub Pages (ficheiros estáticos)
  <nome>.rift.baverone.com       o PC dele NÃO está no caminho

  quem edita a sua coleção  ──> túnel Cloudflare ──> Flask no PC dele
  (autenticado)                                      (ligação de SAÍDA)
```

**Porque é que isto é o certo, e não só o conveniente:**

1. **O tráfego é quase todo de leitura.** Quem espreita uma coleção nunca toca
   no PC dele: pede um `.json` a um CDN. O PC só serve quem está mesmo a
   editar, que são poucas pessoas e poucos minutos por dia.
2. **A superfície de ataque encolhe para uma porta autenticada.** Tudo o que é
   público é um ficheiro estático — não há SQL, não há escrita, não há sessão.
   Um bug no `metrics.py` não é explorável por um estranho.
3. **O PC desligado não parte o site.** É a lição de 2026-09-10, agora com
   mais peso: se o PC de um amigo fosse a fonte do site dele, o site morria a
   cada reinício. Com Pages, o pior que acontece é o site estar desactualizado.
4. **Não custa nada de novo.** O `build.py` já gera exactamente estes
   ficheiros; falta-lhe correr por utilizador e escrever para pastas
   diferentes.
5. **O túnel é uma ligação de SAÍDA.** Isto é o que faz o túnel não contrariar
   as duas proibições do CLAUDE.md — o IP da LAN nunca vai para nada
   publicado, e não há porto aberto no router. O `cloudflared` liga-se de
   dentro para fora.

**O que ele tem de aceitar, dito às claras:** o site público de cada amigo é
**público**. Um subdomínio que ninguém divulga não é uma palavra-passe. Se
alguém quiser a coleção privada, ou não se publica site nenhum para essa
pessoa, ou o Pages fica de fora e a leitura passa também pelo túnel
autenticado — e aí o PC desligado **apaga** o site dela. As duas coisas não se
podem ter ao mesmo tempo, e a escolha é por utilizador.

**A única alternativa séria seria servir tudo pelo túnel**, e recomendo contra:
punha o PC dele no caminho de todas as leituras, ressuscitava a avaria de
2026-09-10 e dava a um estranho uma porta para o `serve`.

---

## 4. O mapa `<nome>.rift.baverone.com` → os dados dessa pessoa

```
  miguel.rift.baverone.com
         └──> slug "miguel"
              └──> utilizador 2                   (data/users/registo.db)
                   └──> data/users/miguel/vault.db
```

O **slug é a chave**, e é por isso que a validação é estreita
(`utilizador.validar_slug`): minúsculas, dígitos e hífen, 2 a 32, sem começar
nem acabar em hífen — a intersecção do que um DNS aceita com o que um nome de
pasta aceita. É a mesma string que vai para o caminho em disco, e por isso
`..`, `/` e `C:` são recusados; há teste. Há também uma lista de reservados
(`www`, `api`, `admin`, `users`, …).

**O que só o André pode fazer**, e está por fazer: a conta Cloudflare, apontar
os nameservers de `baverone.com`, autenticar o `cloudflared`, e o registo
wildcard `*.rift.baverone.com`.

**A alternativa em caminho, se o wildcard der problemas** (certificado,
plano, ou ele simplesmente não querer mexer no DNS):

```
  baverone.github.io/riftvault/u/miguel/
```

O `build.py` escreve para `site/u/<slug>/` em vez de uma pasta por
subdomínio, e o frontend não muda **desde que os URLs da API sejam relativos**
— e são (`api/sets.json`, não `/api/sets.json`). É uma linha no build.
Custa: URLs mais feios e nenhum isolamento de cookies entre utilizadores (tudo
na mesma origem), o que só importa quando houver sessões no lado público — e
não há. **Recomendação:** começar por `/u/<slug>/`, que não precisa de ele
mexer em DNS nenhum, e passar a subdomínio quando o Cloudflare estiver de pé.

---

## 5. As fases

### Fase 1 — a fundação no modelo de dados ✅ (esta corrida)

`users`, o `user_id` nas 16 tabelas, a migração com backup e índice, o registo
fora do Git, a porta única (`utilizador.atual`, `db.connect(user_id=…)`), a
pasta de decks por utilizador, e 38 testes.

**Fora, de propósito:** autenticação, túnel, subdomínios, site por utilizador,
UI. **Para ele nada muda** — ver a secção 7.

### Fase 2 — identidade

`utilizador.atual()` passa a ler a sessão. As credenciais vão para uma tabela
`user_auth` **numa base à parte, fora do Git** — nunca na `users`, que viaja em
`SELECT *` e cuja linha do André viaja para um repositório público. O
`auth_ref` fica como ponteiro e **hoje não se escreve lá nada**.

Sem isto o modo edição continua a ser só LAN, sem palavra-passe, como o
CLAUDE.md manda desde 2026-09-02.

### Fase 3 — um site por utilizador

`build.py` corre por utilizador (`db.connect(user_id=…)`) e escreve para
`site/u/<slug>/`. O `--se-mudou` passa a ser por utilizador, senão um `+` de um
amigo gasta uma build do Pages para toda a gente.

### Fase 4 — o túnel

`cloudflared` para o 8770, autenticação à frente, e o `serve` a deixar de fazer
bind em `0.0.0.0` sem a ter.

### Fase 5 — o que fica por decidir

A separação do config (secção 6), quotas, e o que fazer com o `riftvault
prices` quando forem 20 pessoas (é partilhado: não cresce).

---

## 6. O config: o que é regra do produto e o que é preferência de cada um

Hoje é um ficheiro global e **um amigo herda as regras do André**. Isso é
limitação conhecida desta fatia, não uma decisão.

### O config é o furo que a separação por ficheiro NÃO tapa

Vale a pena ser explícito, porque é o ponto fraco desta arquitectura e foi
encontrado enquanto ela se construía (pelas sessões `riftbound-f3` e
`riftbound-2b`). A separação é por ficheiro **de base de dados** — e o
`riftvault_config.json` não é uma base de dados. Há rotas que lhe **escrevem**:

* `POST /api/decks/montar` → `decks.montados`
* `POST /api/decks/principal` → `decks.principal`

Um amigo autenticado a carregar em «Montar» escrevia o slug do deck dele na
lista do André. **Não passa pelo SQLite**, por isso nenhum guarda ao nível da
ligação o vê.

Consequência, enquanto o config for global: **o estado dos decks (montados,
principal, ordem) fica fora das contas.** A tapagem imediata é recusar a
escrita a quem não é o utilizador 1 (`config.escrever_valor`), e é o que as
fatias seguintes fazem; a tapagem a sério é a separação abaixo.

### A linha que proponho

| | exemplos | de quem |
|---|---|---|
| **regra do produto** | `sets`, `playset_targets_by_type`, `master_set.escondidas`, `runas_especiais.retiradas`, `precos.linguas`, `mercados.*`, `selado.categorias` | do RIFTVAULT — é o jogo e o mercado. Fica global. |
| **preferência de utilizador** | `master_set.um_de_cada`, `foil.*`, `decks.*`, `abas.escondidas`, `venda.*`, `selado.excluidos`, `listas_de_compra.so_master_set` | de CADA UM. É a coleção *dele* que ele está a definir. |

O teste é: *"se o Miguel discordar disto, está errado ou é só diferente?"* Que
as promos pedem 1 de cada é uma escolha do André sobre a coleção dele; que as
runas sem numeração estão escondidas é uma propriedade do catálogo.

**Como se implementa quando chegar a altura:** `config.load(user_id)` funde o
global com um `data/users/<slug>/config.json`, e a UI escreve só no segundo.
`config.load` é `@lru_cache(maxsize=1)` — passa a ser por utilizador.

**Não se fez agora** porque a fatia fina é o modelo de dados, e porque mexer no
config é mexer em 30 decisões dele de três semanas.

---

## 7. Os riscos que ele assume ao guardar dados de terceiros

Sem dramatizar e sem varrer para debaixo do tapete. **Isto é o que muda quando
os dados deixam de ser só dele.**

### Os backups do que é deles

O `data/vault.db` dele está no Git — é isso que lhe dá um backup versionado de
graça, com 95 pontos de restauro. **Os dos amigos não têm nada disso, e é de
propósito** (secção 2a): a pasta `data/users/` está no `.gitignore`.

**Portanto: os amigos não têm backup nenhum hoje.** Se o disco dele morrer, a
coleção deles morre com ele. É preciso, antes de aceitar o primeiro amigo:

* uma cópia periódica de `data/users/` para fora do PC (um disco externo, ou um
  repositório **privado**, ou uma pasta sincronizada);
* e dizer a cada um, ao entrar, com que frequência é feita.

A migração desta corrida já deixou `vault-antes-do-multi-utilizador-*.db` em
`data/backups/` — mas isso é um instantâneo de hoje, não uma política.

**Desde 2026-10-02 cada um tem a sua pasta de backups** (`config.backups_dir`):
`data/backups/` continua a ser a dele e os outros vão para
`data/backups/<slug>/`. **E não para `data/users/<slug>/backups/`**, que era o
sítio óbvio: a pasta de um utilizador é apagada inteira pelo
`utilizador.apagar`, e com os backups lá dentro o `conta.apagar` apagava a
cópia de segurança que ele próprio acabou de fazer — a rede desaparecia no
minuto em que é precisa. Uma cópia periódica para fora do PC passa a ser **duas
pastas** (`data/users/` e `data/backups/`), e continua a fazer falta.

### Apagar a conta a pedido

`utilizador.apagar(user_id)` apaga a pasta dele e a linha do registo. É barato
**porque a separação é por ficheiro**: uma pasta e uma linha, em vez de
dezasseis `DELETE` que é preciso lembrar de escrever todos. O utilizador 1 não
se apaga por aqui.

O que **falta** e é dele decidir: por quanto tempo é que a cópia fica. O resto
foi respondido a 2026-10-01 (ver «O que o restauro não pode fazer», na secção
4): o `conta.apagar` guarda uma cópia primeiro, **diz** quais as cópias dela que
ficam em disco — senão «apaguei a minha conta» era falso e calado — e
`--levar-copias` leva-as também.

### Se o PC estiver desligado

* **quem só espreita não dá por nada** — o site é estático, no Pages. É o
  ponto 3 da secção 3 e é a razão principal para a recomendar;
* **quem quer editar não consegue**, e vê um erro de ligação. Não há perda de
  dados: a edição é síncrona, e o que não foi gravado não foi mostrado como
  gravado;
* **o site deles fica pelo último `build`** — desactualizado, nunca em branco.

Com a expectativa certa isto é aceitável entre amigos. **Não é aceitável se ele
prometer um serviço**, e é a diferença que convém dizer-lhes ao entrar.

### Se alguém entrar na máquina

Quem tiver a máquina tem **as coleções todas**: as bases não estão cifradas e
não há nada no riftvault que as proteja de quem tem o disco. Isto já era
verdade para a dele; a diferença é que agora é a de terceiros.

Concretamente, e por ordem de probabilidade:

1. **o túnel é a porta nova.** Sem autenticação à frente, um URL do túnel é
   escrita na coleção de quem estiver na sessão. A fase 4 não pode ir para o ar
   sem a fase 2 — *"se algum dia for preciso expor mesmo, aí sim é preciso
   autenticação primeiro — não inverter a ordem"* (CLAUDE.md);
2. **a LAN continua sem palavra-passe.** Com um segundo utilizador, quem estiver
   no Wi-Fi de casa pode escrever na coleção de um amigo. Hoje isso é o André e
   a família; convém que continue a ser;
3. **um `git push` com a pasta errada.** O `.gitignore` cobre `data/users/`, e
   há teste que o exige. Um `git add -f` fura-o à mesma.

### O que isto não muda

O `catalog.db` e o `prices.db` não são dados de ninguém, e as tarefas que os
actualizam (`riftvault sync`, `map`, `prices`) continuam iguais e continuam a
servir toda a gente. **Não há pedidos de rede novos por utilizador** — é a
segunda razão para os manter partilhados, a seguir ao disco.

---

## 8. A porta única

```python
utilizador.atual()                   # o utilizador desta sessão — HOJE sempre 1
db.connect(readonly=False, user_id=None)   # a base DAQUELE utilizador
con.riftvault_user                   # o dono, a viajar com a ligação
config.decks_dir(con)                # a pasta de `.txt` daquele utilizador
db.TABELAS_DE_DONO                   # as 16 que levaram `user_id`
```

**Todo o código que lê ou escreve dados de dono recebe um `con`, e todo o `con`
sai do `db.connect`.** É por isso que a fatia seguinte é pequena: a autenticação
muda `atual()` e mais nada. Dois testes guardam isto — nenhum módulo abre uma
base por fora do `db.connect`, e nenhum lê a variável do utilizador fora do
`utilizador.py`.

`RIFTVAULT_USER` deixa correr o CLI e as medições como outro utilizador. É uma
variável do ambiente dele, na máquina dele, do mesmo tipo do `RIFTVAULT_DATA`
que já existia — **o servidor nunca a lê de um pedido**.

---------------------------------------------------------------------------
# AS GUARDAS (2026-09-29, a seguir à fundação)

O pedido dele: *"O que achas que deve ser já feito para evitar erros futuros,
e o quê? / Posso concordar e começamos também já a tratar disso?"* — concordou
de antemão com o que fosse proposto. O que se segue é curto de propósito: são
as coisas **baratas agora e caras depois de haver gente lá dentro**.

## 1. PORTAS FECHADAS ATÉ ELE MANDAR ABRIR

*"Quero apenas apresentar quando tiver tudo"* (André, 2026-09-29).

Um interruptor só, no config, **e nasce fechado**:

    "multi": { "aberto": false }

Lê-se por uma função (`multi.aberto(cfg)`) e por mais nenhuma. Enquanto for
`false`:

| | |
|---|---|
| registo / convites / contas de amigos | **não existem**. Há um utilizador: ele. As contas de teste vivem nos testes e na base de ensaio, nunca no `data/vault.db` real. |
| o túnel | **não se liga**. Não há cloudflared instalado nem configurado. O que falta fazer quando for altura está na secção «O que só ele pode fazer». |
| páginas públicas de outros | **não se publicam**. O `build.py` sabe gerá-las e há teste que o prova, mas para o `site/` vai só a dele. |
| o site público dele | **exactamente como está hoje** — nem «em breve», nem um link de login a espreitar. Há teste (`test_portas_fechadas`) que compara o site gerado com o de hoje, ficheiro a ficheiro. |

Quando ele quiser abrir, muda-se **um valor**, não dez condições espalhadas.

## 2. O QUE O PÚBLICO VÊ: `users.publico`

Três valores, e **a omissão é a mais fechada**:

| valor | o que o público vê |
|---|---|
| **`nada`** (omissão) | **nada** — não se gera site nenhum para essa pessoa |
| `sem-valores` | a coleção, e **nenhum euro em lado nenhum** |
| `tudo` | como o site dele hoje |

**Porquê `nada` por omissão.** Publicar a coleção de outra pessoa tem de ser um
acto ESCOLHIDO. Uma página pública indexa-se no Google e fica em cache em
sítios que não controlamos: na prática **não se despublica**. E o valor em
euros de uma coleção, ao lado de um nome e de um subdomínio, é informação com
consequências fora do ecrã.

**O André fica em `tudo`**, e não é excepção: é o que ele já escolheu e tem. A
migração escreve-lho, e por isso o site dele não muda um byte.

**Como é que o `sem-valores` tira os euros.** Uma regra só, aplicada ao payload
antes de ser escrito: *uma chave cujo NOME fala de dinheiro e cujo VALOR é um
número perde o valor; uma string com `€` também*. Não é uma lista de chaves
escrita à mão — uma lista fica velha na primeira vez que um payload ganha um
campo, e fica velha em silêncio. Medido no site real a 2026-09-29: **272 chaves
distintas, 31 falam de dinheiro, ~7 000 ocorrências, e um único `€` em texto**
(o recibo da Venda).

Há **duas redes**, e apanham coisas diferentes: o teste exige que nenhuma chave
de quantia sobreviva, *e* pega em números que **são** preços conhecidos desta
coleção (o valor total, o preço de cartas concretas) e exige que não apareçam
em lado nenhum. A segunda apanha uma quantia com um nome que não fale de
dinheiro, que é o que a regra sozinha deixaria passar.

## 3. ISOLAMENTO IMPOSTO PELO CÓDIGO

A ordem foi escrita a contar com uma base só, filtrada por `WHERE user_id = ?`,
e nesse modelo o erro clássico é um `WHERE` esquecido. **Não é esse o modelo
que ficou** (ver a secção da fundação): é **um ficheiro por pessoa**, e um
`WHERE` esquecido já não mostra nada de ninguém — os dados do outro não estão
na ligação.

Mas o modelo novo tem o SEU esquecimento, e são **quatro** as guardas:

1. **Tocar numa tabela de dono sem dono REBENTA** (`guarda.py`, `SemDono`), com
   a tabela nomeada na mensagem. É um autorizador do `sqlite3` — não um wrapper
   à volta do `execute`, que se contorna com um `cursor()`. Medido: **50 000
   consultas em 48 ms armado contra 49 ms desarmado**, custo nenhum (o SQLite
   chama-o na PREPARAÇÃO e o Python guarda os statements em cache).
   **Onde isto vai valer**: hoje `utilizador.atual()` devolve sempre o André,
   por isso nunca dispara. No dia em que houver sessões, `atual()` vai poder
   não saber quem é — e sem guarda esse dia serve a coleção do André a um
   visitante anónimo, em silêncio.
2. **Uma ligação ligada a um utilizador não pode anexar outra base**
   (`SoUmaBase`). É a única maneira de dois donos aparecerem no mesmo `SELECT`.
   O catálogo e os preços anexam-se antes de o guarda armar.
3. **Uma base com linhas de outro dono recusa-se a abrir** (`utilizador.guardar`,
   `DonoErrado`) — é o que apanha um ficheiro trocado ou um backup restaurado
   por cima do outro.
4. **Ninguém abre um `vault.db` fora do `db.py`.** `tests/test_isolamento.py`
   lê o código-fonte e recusa um `sqlite3.connect` ou um `config.VAULT_DB` em
   qualquer outro módulo — é por aí que se chegaria ao ficheiro errado sem
   passar por nenhuma das outras três.

## 4. BACKUP, RESTAURO E APAGAR — POR PESSOA (`conta.py`)

*"Com cinco pessoas lá dentro, restaurar um erro dele desfaz o mês dos
outros."*

    conta.exportar(slug, destino=None)        -> um .zip
    conta.importar(ficheiro, confirmar=True, adoptar=False)
    conta.apagar(slug, confirmar=True, levar_copias=False)
    conta.copias_de(slug)                     -> o que fica dela em disco

O que torna isto barato é o ficheiro por pessoa: exportar é empacotar o
ficheiro dela, importar é pô-lo de volta, apagar é apagar a pasta e a linha do
registo. Nenhuma das três toca num byte de outra pessoa.

O pacote leva o `vault.db` (por `VACUUM INTO` — as bases estão em WAL), o
config dela e as listas dela. **Não leva credenciais**: a `user_auth` e as
sessões vivem no `data/auth.db`, fora do Git e fora daqui, e quem as limpa ao
apagar uma conta é o código da autenticação, no mesmo passo. **Não leva o
catálogo nem os preços**: são partilhados e não são de ninguém.

**O utilizador 1 não se apaga por aqui** — é na base dele que vive a tabela
`users`. Apagá-lo não apagava uma conta, apagava o serviço.

### O que o restauro não pode fazer (2026-10-01)

Três buracos no caminho que só se usa no pior dia, os três com teste que falha
no código de antes:

1. **UM PACOTE SÓ ENTRA NA CONTA DELE.** O `importar` validava o pacote contra o
   `user_id` do manifesto e a seguir adoptava o id do slug que já existia no
   registo, **sem os comparar**: um pacote de `miguel` exportado de outra
   instalação (onde o `miguel` é o 7) aterrava na base do `miguel` desta (que é
   o 2). Hoje compara e **recusa** (`conta.DonoTrocado`, da família do
   `DonoErrado`), antes de escrever um byte. O caso legítimo — restaurar para
   uma instalação em que os ids foram semeados por outra ordem — tem uma porta
   explícita, `adoptar=True` (`--adoptar`), que **recarimba a base inteira** para
   o id de destino: deixar entrar sem recarimbar dava uma conta que não abria
   mais, que é pior do que uma recusa.
2. **UM RESTAURO NUNCA ALARGA A PRIVACIDADE.** A escolha vive no registo, que é
   um ficheiro; quem o restaurar de uma cópia fica com as escolhas do dia da
   cópia, e quem tivesse fechado a coleção entretanto voltava a público — com o
   site a regenerar-se de 30 em 30 minutos. A regra é «**só se alarga por um
   `privacidade.definir()` explícito; qualquer outro caminho só pode fechar**»,
   e os dois testemunhos são o registo e a cópia dentro do `vault.db` (que já
   existia e agora se LÊ). Está por extenso no topo do `privacidade.py`.
   O lado mau do erro é fechar o que estava aberto: desfaz-se com um clique, ao
   contrário de publicar o que estava fechado.
3. **APAGAR UMA CONTA DIZ O QUE FICA.** Os `.zip` de cada export e os
   `antes-de-importar-*.db` de cada restauro têm a coleção inteira dela e
   **ficam** — é a única maneira de desfazer um apagar feito por engano, e é a
   mesma razão por que o `apagar` exporta antes. O que não podem é ficar
   calados: vão no `copias` do resultado, a mensagem da confirmação conta-os, e
   `levar_copias=True` (`--levar-copias`) apaga-os para quem pede «apaga os meus
   dados» e quer dizer todos. **Responde à pergunta que estava aberta em «Apagar
   a conta a pedido»**, acima, menos a parte do «por quanto tempo», que é dele.

## 5. A IDENTIDADE É EMPRESTADA — decisão, não implementação

*"Não quero que ele guarde passwords, nunca."*

**A autenticação será por um fornecedor que já existe** — OAuth / OpenID
Connect —, e o riftvault guarda apenas o identificador que o fornecedor
devolve. Nunca uma palavra-passe, nunca um hash de palavra-passe.

**Porquê, em três razões e por esta ordem:**

1. **O que não se guarda não se perde.** Uma base de palavras-passe é um alvo,
   e este projecto corre no PC de casa dele, sem equipa de segurança, sem
   rotação de chaves e sem ninguém de vigia. O risco de guardar credenciais é
   assimétrico: o ganho é zero e a perda é a conta de um amigo noutros sítios,
   porque as pessoas repetem palavras-passe.
2. **Não há «esqueci-me da palavra-passe» para construir.** Recuperação de
   conta por email é um sistema inteiro — envio, tokens com prazo, limites de
   tentativa — e é onde as contas se perdem de verdade.
3. **É menos um passo para quem entra.** São amigos a organizar cartas, não
   clientes: um botão «entrar com…» e está feito.

**Qual fornecedor: o Discord primeiro, o Google a seguir.** É onde a malta de
TCG já está — as comunidades de Riftbound, as ligas e os torneios organizam-se
lá — e é a conta que um amigo dele já tem aberta no telemóvel. O Google fica
como segundo por ser o denominador comum de quem não usa Discord. **Não se
implementou nada** e a decisão de quantos fornecedores ligar é dele.

**O encaixe já está preparado e está VAZIO**: `users.auth_ref` é o sítio onde o
identificador do fornecedor vai casar com o utilizador. As credenciais e as
sessões **não vão para o `vault.db`**: vão para um `data/auth.db` próprio, fora
do Git — porque o `data/vault.db` está commitado num repositório público e
empurrado de 30 em 30 minutos, e o `sub` do Google ou do Discord de um amigo é
identidade, não se despublica de um histórico com 95 commits, e não tem nada
que estar lá.

## 6. UM SÍTIO PARA PARTIR COISAS (`RIFTVAULT_ENSAIO=1`)

Até aqui tudo se mede contra CÓPIAS do `data/` mas corre contra o `main` e o
8770 — que é a máquina dele, com a coleção dele. Com dados de terceiros lá
dentro isso deixa de chegar.

O ensaio é uma variável do **AMBIENTE e não uma chave do config**: uma chave de
ensaio dentro de um ficheiro que vai para o Git está a um merge de distância de
ir para produção ligada. Uma variável de ambiente não se commita.

Com `RIFTVAULT_ENSAIO=1`:

| | a sério | ensaio |
|---|---|---|
| dados | `data/` | **`data-ensaio/`** |
| config | `riftvault_config.json` | **`riftvault_config-ensaio.json`** |
| o `serve` escuta em | `0.0.0.0:8770` | **`127.0.0.1:8779`** |

**A garantia de que o túnel nunca aponta para o ensaio é a última linha, e é
por construção:** o túnel serve a **8770**, o ensaio **recusa-se a escutar
nessa porta** (`multi.PortaDeProducao`) e só aceita a interface de loopback —
nada do ensaio está sequer na rede local, quanto mais fora de casa. A 8779 já
era a porta da casa para servir uma cópia.

**E o ensaio recusa-se a usar o `data/` a sério**: o `config` rebenta ao ser
importado se as duas coisas coincidirem. É o erro que isto existe para não
deixar acontecer — correr uma experiência com a coleção verdadeira por baixo.

`multi.exigir_ensaio("<o quê>")` é para o que só pode existir lá: um fornecedor
de autenticação de mentira, dados semeados, uma conta de teste.

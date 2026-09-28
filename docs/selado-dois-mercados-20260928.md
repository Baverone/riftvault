# Produto selado — o registo FECHADO dos dois mercados

**28/09/2026.** Este ficheiro substitui o `selado-falta-cardmarket-20260927.md`,
que era a lista do que faltava confirmar. Já não falta: os dois mercados estão
varridos e as decisões estão tomadas.

| | como se leu | o que deu |
|---|---|---|
| **CardTrader** | API v2, com o token (27/09) | 13 categorias do jogo 22, 17 expansões, **210 produtos não-single**, 85 nas 6 categorias de selado. **Nenhum produto selado do CardTrader é desconhecido da app.** |
| **Cardmarket** | **o Chrome dele** (28/09) — a extensão passa o Cloudflare; a API deles está fechada a novos pedidos de acesso | 4 categorias de selado: Boosters (26), Booster Boxes (18), Champion Decks (9), Box Sets (20) = **73 produtos, 68 com oferta** |

Os dados em cru: `ai-pc/work/selado-varrimento.json` (CardTrader) e
`ai-pc/work/cardmarket-selado.json` (Cardmarket).

---

## As duas descobertas sobre o Cardmarket

Valem para qualquer leitura futura, e a segunda é uma armadilha a sério.

### 1. Não há página própria para DISPLAYS nem para CASES

Vendem-se **dentro da entrada do produto simples**, com o vendedor a escrever o
que é na nota. Medido:

- `Box-Sets/Spiritforged-Pre-Rift-Event-Kit` — ofertas de «SEALED CASE (16 kits
  + box)» a **1350 €** e «Sealed Case for 16 players» a **1800 €**, ao lado do
  kit de um jogador a ~49 €;
- `Champion-Decks/Vi-Champion-Deck` — «FRENCH 4 = display sceellee» a **12,49 €**.

É por isto que os 17 produtos do `selado.extra` não têm página própria em
mercado nenhum: **não é falha do catálogo, é o modelo deles.**

### 2. O «From» NÃO é o preço do produto

No `Unleashed-Pre-Rift-Event-Kit` o «From 2,50 €» são vendedores a vender **um
deck solto de dentro do kit** («ONLY Vi deck (sealed) - nothing else»); o kit
inteiro está a ~22-26 €. **Não usar o «From» deles como preço sem ler a nota do
vendedor.** O preço da app continua a ser o do CardTrader.

### E o que ficou confirmado do URL

O caminho `/en/Riftbound/Products/<Categoria>/<Slug>` responde, com estes cinco
valores de categoria: `Boosters`, `Booster-Boxes`, `Champion-Decks`, `Box-Sets`
e `Sets`. **O template que a app usa é outro** (`?idProduct={id}`) e continua
por confirmar — ver `riftvault/mercados.py`, que diz o que faltaria para o
trocar (o slug deles e a categoria deles, nenhum dos quais a app tem).

---

## O que ficou decidido a 28/09

### a) Voltam à aba os que o Cardmarket revelou ter oferta — **dois**

*"Repor so os 5 novos"*. Dos 15 que tinham saído a 26/09 por não terem oferta em
lado nenhum, o Cardmarket revelou oferta em **5**. Dois voltaram:

| produto | Cardmarket | porquê volta |
|---|---|---|
| **Unleashed Sleeved Booster** | «Unleashed Sleeved Booster», desde **13,00 €** | inglês; «sleeved» é embalagem, não língua |
| **Replacement Card Booster** | «Replacement Card Booster», desde **35,00 €** | inglês |

Os outros três **não voltaram, pela regra da língua** (alínea b):

| produto | Cardmarket | porquê fica fora |
|---|---|---|
| Unleashed Slim Booster | «Unleashed Booster **(Chinese, Slim)**», 2,49 € | impressão chinesa |
| Unleashed Slim Booster Box | «Unleashed Booster Box **(Chinese, Slim)**», 35,70 € | impressão chinesa |
| **Immersive Arcane Promo Pack** | «Arcane: Immersive Music Experience Booster», 80,00 € | **a `versao` do CardTrader diz «Chinese Exclusive»** — ver a nota abaixo |

Os **23 que tinham oferta no CardTrader** ficam fora (*"deixa como está"*, 26/09)
e os Champion Deck também — os **11** de 26/09 (*"retira os Champion Deck
todos"*) mais o «Origins: Champion Deck Set» de 25/09.

> **A terceira linha é uma decisão minha, e é a única coisa desta ordem que não
> se fez como estava escrita.** O pedido mandava repor os três. Medido antes de
> tocar: o blueprint 408687 («Immersive Arcane Promo Pack») tem
> `versao: "Chinese Exclusive"` no catálogo do CardTrader — a mesma string dos
> outros dois «Promo Pack», que estão fora. O Cardmarket tem-no a 80,00 € com
> outro nome (casado pelo `cardmarket_id` 904521 do próprio blueprint) e **não**
> lhe põe rótulo de língua. As duas ordens de hoje colidem neste produto: pela
> (a) volta, pela (b) não pode entrar. Ficou fora — é o que a regra nova diz, e
> foi a regra nova que cortou os outros dois da mesma lista. **Repor é tirar o
> nome do `selado.excluidos`**, e a decisão é dele.

### b) Regra nova e geral: só impressão inglesa

*"nao quero nada que nao seja impressao Inglesa"*.

É a mesma escolha que os preços já faziam pelo outro lado desde 2026-08-31
(`precos.linguas: ["en"]`, que no *Origins Booster Box* deixava de fora 6 ofertas
`zh-CN` e 3 `fr`). A diferença é que até aqui a língua filtrava o **preço** de um
produto que ficava na lista; agora **tira o produto**.

**Aplica-se à mão, pelo `selado.excluidos`** — não há campo de língua nos
blueprints. O marcador lê-se no `nome`, na `versao` («Chinese Exclusive») ou no
rótulo do Cardmarket («(Chinese, Slim)», «(Chinese, Jumbo)», «(Chinese)»).
**Cuidado a cada `riftvault selado --sync`**: um produto novo com esse marcador
entra na aba sozinho.

**Saiu por esta regra:** o **Arcane Chinese Promo Set** (ARC) — varridos os 48
da aba, era o único com marcador de língua.

**Formato não é língua:** «Slim», «Jumbo» e «Sleeved» são embalagens, e a
impressão inglesa de um produto com irmão chinês fica (o *Arcane Box Set* fica;
o «Arcane Box Set (Chinese)» do Cardmarket nunca chegou a estar na aba, porque a
app não vê o catálogo deles).

### c) Sai da aba o que não tem página própria — os 17 do `selado.extra`

*"Tira os que nao tem pagina propria"*. Os 7 Champion Deck Display, os 2 Showdown
Decks Display, os 3 Vault Bundle Case, o Proving Grounds Box Set Case e os 4
Pre-Rift EVENT Kit. Eles existem (levantamento dele de 25/09, em
`ai-pc/work/riftbound-produto-selado.md`); o que não existe é uma página onde
comprá-los — e a descoberta 1 explica porquê.

**O que saiu foi a presença na aba, não o conhecimento.** Os 17 objectos estão
inteiros em `_selado_extra_arquivado` no config (nome, edição, tipo, data,
conteúdo, notas — incluindo a dúvida dos 4 ou 12 vaults do case da Unleashed), e
**repor é copiá-los de volta** para o `selado.extra`. As unidades dele nos ids
`cfg-…` ficam na `sealed_copies`; estavam todas a zero.

---

## O efeito, medido

Contra uma cópia do `data/` real, o mesmo código e o mesmo catálogo, mudando só
o config, com o site gerado dos dois lados: **30 ficheiros, 29 iguais**; o único
que difere é o `api/selado.json` (98 088 → 67 757 bytes). O `copies` não mexeu um
número (1041 linhas, 2632 normais, 448 foil, o mesmo sha256).

| | antes | depois |
|---|---|---|
> **Na mesma noite a aba passou de 32 para 30**, por outra ordem: *"não quero
> «decks» para colecionar"* tirou a categoria **262 «Riftbound Starter Decks»**
> das `selado.categorias`, e com ela os 2 Showdown Deck (os únicos da 262 que
> ainda estavam visíveis — os Champion Deck já tinham saído a 26/09). Os 18
> nomes de decks do `selado.excluidos` ficaram redundantes e foram para
> `_selado_decks_arquivado`: a lista passou de **49 para 31**. Ver o CLAUDE.md.

| produtos na aba | 48 | **32** |
| dos quais «por sair» | 11 | 8 |
| tenho · cópias | 5 · 5 | **5 · 5** |
| não tenho | 32 | 19 |
| percentagem | 13,5 % | **20,8 %** |
| **valor do selado** | **552,56 €** | **552,56 €** |
| sem preço | 23 | **7** |
| vindos do config (`extra`) | 17 | **0** |
| `selado.excluidos` | 50 | **49** |

**O valor não mexeu, e tinha de ser:** as 5 unidades que ele tem são todas de
produtos do CardTrader que ficaram na aba (Origins, Spiritforged, Unleashed e
Vendetta Booster Box, e o Origins: Proving Grounds), e os 17 arquivados não
tinham preço nem unidades.

Por edição: OGN 5 → 2, OGS 2 → 1, SFD 6 → 3, UNL 8 → 5, VEN 8 → 5, RAD 7 → 4,
ARC 2 → 1, PROMO-RIFT 5 → **6**; LGC 2, PG2 1, REC 1 e T1S 1 não mexem.

**Os dois que voltaram aparecem sem preço** («—»), e é honesto: o CardTrader tem
zero ofertas de ambos — foi por isso que saíram a 26/09 — e a app não guarda
preços do Cardmarket. Ver a proposta abaixo.

---

## O buraco que fica, e o que se propõe (nada disto foi feito)

### 1. A app só vê o catálogo do CardTrader

O `--sync` lê a API do CardTrader e mais nada. Um produto que **só o Cardmarket
lista** é invisível: não está na aba, não está no `scope.fora`, não está sequer
no `selado.excluidos` — não existe.

**Medido produto a produto** (`_revisao\_so_no_cardmarket.py`, com a tabela de
correspondência escrita à mão, porque os nomes divergem — «Origins Case (6x
Booster Box)» lá é «Origins Booster Box Case» cá; o script recusa uma tabela que
aponte a um nome que a app não tenha): dos **73** do Cardmarket a app conhece
**57** e desconhece **16**, dos quais **13 com oferta viva**.

> A ordem desta sessão dizia 14 (12 com oferta). Medi 16 e 13: a diferença são o
> «Vendetta Booster (Chinese, Slim)» e o «Vendetta Booster Box (Chinese, Slim)»,
> que a app não tem — o «Slim» dela é só OGN, SFD e UNL —, ambos sem oferta.

| o que é | quantos |
|---|---|
| booster e booster box **(Chinese, Jumbo)** de OGN, SFD, UNL e VEN | 8 (7 com oferta) |
| booster e booster box **(Chinese, Slim)** da VEN | 2 (nenhum com oferta) |
| *Spiritforged Sleeved Booster* (12,00 €) e *Vendetta Sleeved Booster* (11,25 €) | 2 |
| *Worlds 25 Commemorative Booster* (22,00 €) | 1 |
| *Project K Promos Booster* (2450,00 €) | 1 |
| *Arcane Box Set (Chinese)* (1499,00 €) | 1 |
| *Unleashed: Prize Wall Rune Bundle* (220,00 €) | 1 |

Dez dos 16 são impressão chinesa, e por isso ele **não os quer** (a regra da
alínea b). Os outros seis são os únicos que a decisão de hoje deixaria entrar —
se a app soubesse que existem.

### 2. ~~Um preço do Cardmarket metido à mão~~ — **FEITO na noite de 28/09**

Os dois que voltaram valem 13,00 € e 35,00 € no Cardmarket e a app mostrava
«—». Ele leu isso como «não tem disponível» (*"ainda estao la champions decks
que nao tem disponiveis"*), e foi essa queixa que a fez nascer.

**A tabela `sealed_price`** (`product_id`, `cents`, `updated_at`, `source`) é o
gémeo do Trend da Venda, com a chave certa — ali é `printing_id`, uma carta;
aqui é `product_id`. `riftvault selado --preco ID [EUROS]`,
`POST /api/selado/preco`, e um campo «CM» em cada linha do 8770. **Conta o do
CardTrader quando existe** (é medido) e o do Cardmarket quando não existe; a
linha diz sempre de onde veio o número, e onde não há nenhum diz **«sem oferta
no CardTrader · a app não lê o Cardmarket»** em vez de um traço mudo.

**Os dois preços não foram semeados** — são medições de ontem e envelhecem; o
número do Cardmarket é dele: `--preco ct-363132 13,00` e
`--preco ct-379338 35,00`.

**Fica por fazer:** a marca de «velho» ao fim de N dias, que a Venda tem
(`venda.trend_valido_dias`). Aqui mostra-se a data e mais nada.

### 3. Um aviso de língua no `--sync`

A regra nova aplica-se à mão. Um `Spiritforged Booster (Chinese, Jumbo)` que
entre no catálogo amanhã aparece na aba sem ninguém dar por isso. O `--sync`
podia dizer, no fim, que produtos novos trazem marcador de língua no nome ou na
versão — **avisar, não esconder**, que é a regra desta casa.

### 4. O `Arcane Box Set` tem a mesma `versao` que o `Arcane Complete Set`

Os dois dizem «6 Card Set», e o segundo saiu a 25/09 por ser *"um conjunto de
CARTAS, não produto selado"*. Não é matéria de língua e não se tocou; mas se o
critério de 25/09 vale, vale para os dois. **É pergunta para ele.**

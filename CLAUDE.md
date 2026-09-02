# CLAUDE.md — riftvault

Contexto do projeto para o Claude Code. Lê isto antes de mexer em código.

## O que é

Gestor pessoal da coleção de **Riftbound** (TCG da Riot), do André. Python +
SQLite, mesma arquitetura do `mtgvault`. Objetivo: ter **playsets**, incluindo
artes normais **e** alternativas.

Duas secções apenas: **Coleção** e **Decks**.

## Regras de trabalho

- **Comentários, README e mensagens em português (de Portugal).** Nomes de
  funções, variáveis e tabelas em inglês.
- **Não inventes dados.** Se a API não devolver um campo, não o preenchas de
  memória — regista aqui que não foi validado.
- Comentários explicam *porquê*, não *o quê*.
- Tudo o que ainda não foi validado contra a API real vive na secção
  "Superfícies não validadas", no fim.

## Dois modos

- **Edição (local):** `riftvault serve` levanta um servidor local que serve o
  site e escreve no `vault.db`. Bind `0.0.0.0` + QR no arranque, para usar o
  telemóvel enquanto se mexe nas cartas.
- **Publicado (leitura):** `riftvault build` gera o MESMO frontend em estático,
  sem controlos de edição, publicado no GitHub Pages por GitHub Actions.

O frontend é o mesmo ficheiro nos dois modos. Ele pede sempre os mesmos URLs
(`api/sets.json`, `api/set/<ID>.json`, ...); em modo edição o servidor
responde dinamicamente, em modo publicado são ficheiros reais gerados pelo
build. Um flag no payload (`"editable": true/false`) liga/desliga os `+`/`-`.

## Sem autenticação — cuidado com a exposição

O modo edição **não tem autenticação nenhuma**: quem chegar ao URL escreve na
coleção. É aceitável na LAN, não é na internet.

Para acesso de fora, a resposta é **Tailscale** (rede privada entre os
dispositivos dele), não port forwarding nem tunnels públicos. O
`server.tailscale_ip()` deteta a tailnet e o banner de arranque mostra esse
endereço e o QR quando existe.

Se algum dia for preciso expor mesmo, aí sim é preciso autenticação primeiro —
não inverter a ordem.

## Três bases de dados

- `data/vault.db` — a coleção e os decks. **Commitado. Só o André escreve.**
- `data/prices.db` — histórico de preços. **Commitado. Só o robô escreve.**
- `data/catalog.db` — cache do catálogo da RiftScribe. **No `.gitignore`**
  (reconstruível com `riftvault sync`).
- `data/images/` — cache local das imagens. **No `.gitignore`.**

**Porque é que o histórico de preços não está no vault.db.** O GitHub Actions
corre o `riftvault prices` sozinho e faz commit do resultado. Se isso fosse
para dentro do vault.db, bastava o André ter mexido na coleção localmente para
dar um conflito num ficheiro **binário** — e resolver um conflito de SQLite é
escolher uma das versões e perder a outra. A coleção é a única coisa
insubstituível aqui, por isso o robô nunca lhe toca. Na pior das hipóteses
perde-se um dia de preços.

`db.connect()` anexa as duas: `catalog` e `prices`. As consultas ao histórico
qualificam sempre `prices.price_history`.

Como no mtgvault, o `catalog.db` é ATTACHed como schema `catalog`. O SQLite
não suporta chaves estrangeiras entre bases de dados: `copies.printing_id`
não tem FK declarada, a integridade é garantida no código.

---

# A API da RiftScribe — o que foi VALIDADO (2026-08-31)

Base: `https://riftscribe.gg/api`. Pública, sem autenticação.
Spec guardada em `docs/riftscribe-openapi.json`.
Snapshot completo das 1180 entradas em
`docs/riftscribe-cards-snapshot-2026-08-31.json`.

## A questão crítica das variantes: RESOLVIDA

**As variantes VÊM na listagem como entradas separadas.** Não é preciso varrer
sufixos nem inventar estratégias. `GET /api/cards?set_id=OGN&limit=200` devolve
a arte base *e* a arte alternativa como dois objetos distintos, cada um com o
seu `id`, o seu `public_code` e o seu **URL de imagem próprio**.

O campo que as distingue é `variant`, presente tanto no `CardSummaryRead`
(listagem) como no `CardRead` (detalhe):

> "Variant discriminator: '' base, 'a' alt-art, 'star' signature, 'tNN' token"

**Além disso, a ordenação `sort=default` já coloca cada variante imediatamente
a seguir à sua carta base** — exatamente o agrupamento visual pretendido.
Não é preciso reordenar.

Valores de `variant` observados nas 1180 entradas:

| `variant` | n | significado |
|---|---|---|
| `''` | 1020 | impressão base |
| `a` | 102 | arte alternativa |
| `star` | 36 | signature (código impresso leva `*`) |
| `t01`..`t08` | 10 | tokens |
| `r01`..`r06` | 6 | runas promo (só VEN) |
| `sp1`..`sp6` | 6 | promos especiais (só VEN) |

Nunca aparece `b` — **no máximo uma arte alternativa por carta**.
Nenhum grupo tem `a` **e** `star` ao mesmo tempo.
Todos os 102 `a` e todos os 36 `star` têm a sua base na mesma listagem.

## Exemplo real: carta base vs arte alternativa

```
                 BASE                        ALT ART
id               ogn-007-298                 ogn-007a-298
public_code      OGN-007/298                 OGN-007a/298
name             Fury Rune                   Fury Rune
set_id           OGN                         OGN
collector_number 7                           7
variant          ""                          "a"
rarity           common                      showcase      <-- muda!
faction          fury                        fury
domains          ["Fury"]                    ["Fury"]
type             Rune                        Rune
orientation      portrait                    portrait
stats            {energy,might,power}        idem
image            .../originals/ogn-007-298-868b5cd63536371d.png
                                             .../originals/ogn-007a-298-af47f970776f6f15.png
image_thumb      small/medium/large .webp    idem, com outro hash
image_blur_data_url  data:image/jpeg;base64  diferente
is_banned        false                       false
```

**Imagem por variante: CONFIRMADO.** O hash no nome do ficheiro é diferente,
e as duas descarregam com HTTP 200 (`originals/*.png` ~1,4 MB,
`thumbnails/large/*.webp` ~105 KB).

Exemplo de signature: `ogn-299-star-298`, `public_code` `OGN-299*/298`.

## As 5 edições

`GET /api/cards/filters` devolve `sets: [OGN, OGS, SFD, UNL, VEN]`.

| set | entradas | base | alt art | signature | outras |
|---|---|---|---|---|---|
| OGN | 352 | 310 | 30 | 12 | — |
| OGS | 24 | 24 | — | — | — |
| SFD | 288 | 251 | 24 | 12 | 1 token |
| UNL | 288 | 238 | 30 | 12 | 8 tokens |
| VEN | 228 | 197 | 18 | — | 13 (6 runas, 6 promos, 1 token) |
| **total** | **1180** | 1020 | 102 | 36 | 22 |

**A API NÃO devolve o nome das edições, só o código.** O mapeamento
`OGN -> "Origins"` etc. tem de ser local (`riftvault_config.json`). Não foi
validado contra fonte nenhuma — os nomes que lá estiverem são palpite até o
André confirmar. Também não há endpoint de edições nem data de lançamento: a
ordem dos separadores vem do config.

## Outros valores de filtro (validados)

- `factions`: body, calm, chaos, colorless, fury, mind, order
- `rarities`: common, uncommon, rare, epic, **showcase**
- `types`: Battlefield, Gear, Legend, Rune, Spell, Unit (+ 2 entradas com
  `type: null` — `UNL-T04 "Buff"` e `UNL-T08 "XP Tracker"`)

`showcase` **não é uma raridade de jogo, é um tratamento**: quase todas as
artes alternativas e signatures têm `rarity: "showcase"`. Os contadores por
raridade da UI devem usar a raridade da **base**, não a da variante, senão a
contagem fica distorcida.

## ARMADILHA 1 — `(set_id, collector_number)` NÃO é chave única

Em **VEN** o mesmo `collector_number` é reutilizado por famílias diferentes:

```
cn=4  variant=""     Dune Surfer        ven-004-166
cn=4  variant="r04"  Body Rune          ven-r04
cn=4  variant="sp4"  Sett, Brawler      ven-sp4-006
cn=4  variant="t04"  Recruit (NX)       ven-t04
```

A chave de agrupamento visual tem de ser **(set_id, collector_number, lane)**,
onde `lane` é o prefixo alfabético do `variant`: `main` para `''`/`a`/`star`,
e `t`/`r`/`sp` para os outros. Com isto dão **1042 grupos** para 1180 entradas,
e nenhum grupo fica sem base.

## ARMADILHA 2 — reimpressões showcase com número de coleção PRÓPRIO

Não é só o sufixo. A mesma carta lógica reaparece **na mesma edição** com outro
número de coleção. Exemplos: OGN 299–310, SFD 222–251, UNL 220–238, VEN 167–197.
E é a essas reimpressões que o `star` se agarra, não à base original.

Caso canónico, **"Sett, Brawler" — 5 impressões em 3 edições**:

```
ogn-164-298       OGN-164/298    variant=""      epic
ogn-164a-298      OGN-164a/298   variant="a"     showcase
sfd-232-221       SFD-232/221    variant=""      showcase
sfd-232-star-221  SFD-232*/221   variant="star"  showcase
ven-sp4-006       VEN-SP4/006    variant="sp4"   epic
```

Consequência: **a carta lógica não pode ser identificada pelo número de
coleção**. 104 nomes aparecem em mais do que um `(set, collector_number)`.
1180 impressões correspondem a **935 nomes distintos**.

A carta lógica é chaveada pelo **nome normalizado** (`card_key`). Verificado:
não há duas cartas diferentes com o mesmo nome no catálogo atual. As 4 Legends
de starter do OGS já vêm com nome próprio (`Dark Child - Starter`,
`Wuju Bladesman - Starter`, `Lady of Luminosity - Starter`,
`Might of Demacia - Starter`) e não colidem com nada.

## ARMADILHA 3 — a API não sabe o que é foil

**Procurado em toda a spec: não existe `foil`, `finish`, `holo` nem
`treatment`.** As únicas ocorrências de "finish" são o `is_finished` do jogo
Riftboundle. O "printing" da API é *arte*, não *acabamento*.

Os acabamentos (`normal`/`foil`) são **inteiramente locais ao riftvault**. Que
impressões existem em foil, e se as signature são foil-only, é conhecimento do
André, não da API. Fica em `riftvault_config.json` e **é palpite até ele
confirmar**.

## Endpoints úteis

| endpoint | notas |
|---|---|
| `GET /api/cards` | `set_id`, `q`, `faction`, `rarity`, `type`, `types[]`, `domain_identity[]`, `is_banned`, `sort`, `limit` (**máx. 200**), `offset`. Total no header `X-Total-Count`. Devolve `CardSummaryRead[]`. |
| `GET /api/cards/{card_id}` | `CardRead` = summary + `description`, `flavor_text`, `art{artist}`, `keywords`, `tags`, `prev_card_id`, `next_card_id`. Aceita `OGN-7`, `OGN-007`, `OGN-007a`, `OGN-301-star`, `OGN-301*`, `UNL-T03`. |
| `GET /api/cards/filters` | `sets`, `factions`, `rarities`, `types`. |

O catálogo inteiro são **7 pedidos** (5 edições; OGN, SFD e UNL em 2 páginas).
A listagem já traz tudo o que a grelha precisa; o detalhe só é preciso para
`description`/`keywords`/`artist` — e **`artist` veio `null`** na carta testada.

## Restrições externas

| Fonte | Estado |
|---|---|
| `riftscribe.gg/api` | pública, sem auth, sem rate-limit documentado. Ser educado: 1 pedido/s no sync. |
| `cdn.riftscribe.gg` | imagens HTTP 200 diretas, sem auth. `originals/*.png` ~1,4 MB, `thumbnails/large/*.webp` ~105 KB — **usar os thumbnails no cache**. |

---

## Superfícies NÃO validadas contra a API real

Se algo vier errado, é aqui:

1. **Nomes das edições** (`OGN -> ?`). A API não os dá. Mapeamento local, por
   confirmar com o André.
2. **Acabamentos (normal/foil) por impressão.** A API não sabe nada disto.
   Que cartas existem em foil, e se as signature são foil-only, é palpite.
3. **Alvos de playset por tipo** (Unit/Spell/Gear 3, Battlefield 1, Legend 1,
   Rune 12, Token 0) vieram do André, não das regras oficiais.
4. **Regras de legalidade de deck** (40 main, 12 runas, 3 battlefields, limite
   de 3 cópias, domain identity) vieram do André, não estão na API.
5. **Estabilidade dos `id`.** Assume-se que `ogn-007a-298` é estável entre
   syncs. Se a RiftScribe re-hashar os ficheiros muda o URL da imagem, mas
   presume-se que o `id` fica. Não testado ao longo do tempo.
6. **Sets futuros.** A descoberta é dinâmica por `/api/cards/filters`, mas uma
   edição nova pode trazer um `variant` novo (`b`? `sp7`?). O parser de
   `variant` tem de falhar de forma visível, não silenciosa.

---

# Decisões de implementação (2026-08-31)

## Sem acabamentos

Decisão do André: **foil e normal contam como a mesma coisa**. A tabela
`copies` é só `(printing_id, qty)` — não há coluna `finish`. O CLI aceita
`--foil` e ignora-o, para não dar erro por hábito.

O alvo do master set é por impressão, e qualquer cópia serve para o cumprir.

Se um dia isto mudar: acrescentar `finish TEXT NOT NULL DEFAULT 'normal'` a
`copies`, passar a PK a `(printing_id, finish)`, e o mesmo em `ops`.

## Alvo do master da impressão base

`master_base_follows_type: true` no config. O André pediu "base 3, alt art 1,
signature 1", mas 3 fixo daria Rune base = 3 (quando o playset são 12) e Legend
base = 3 (quando basta 1). Por isso o alvo do master da **base** segue
`playset_targets_by_type`; as variantes mantêm o 1. Põe-se `false` para voltar
ao 3 fixo.

## Cliques rápidos: deltas idempotentes, não debounce

O cliente manda `{printing_id, delta, request_id}`; o servidor faz
`qty = qty + delta` em `BEGIN IMMEDIATE`, e `ops.request_id` é `UNIQUE`.

- Nenhum clique se perde: não há janela onde dois cliques colapsem num só.
- Nenhum clique conta a dobrar: um retry com o mesmo `request_id` devolve o
  resultado guardado sem voltar a aplicar.

Testado: 40 pedidos concorrentes ao mesmo tile deram exatamente +40; o mesmo
`request_id` repetido 5 vezes contou 1.

No cliente, o estado local é a verdade enquanto houver pedidos em voo
(`state.pending` por carta lógica); só se aceita o valor do servidor quando o
contador chega a zero, senão uma resposta atrasada punha o contador para trás.

## Nomes das edições

**Decidido (André, 2026-08-31): ficam os CÓDIGOS** nos separadores, **exceto o
OGS, que mostra `OGS (Proving Grounds)`** — é o set de starters e convinha
distingui-lo do OGN.

A API da RiftScribe não dá os nomes das edições. Os verdadeiros vieram da
lista de expansões do CardTrader (`cardtrader.com/en/games/riftbound/expansions`),
e batem certo com os cinco códigos:

| código | nome |
|---|---|
| OGN | Origins |
| OGS | Origins: Proving Grounds |
| SFD | Spiritforged |
| UNL | Unleashed |
| VEN | Vendetta |

(O OGS ser "Proving Grounds" explica as quatro Legends com nome `— Starter`.)

## Tokens: 1 de cada

**Decidido (André, 2026-08-31): `token_target: 1`**, nas duas métricas. Os
tokens não são cartas de deck, mas contam para a coleção estar completa.

`token_card_keys` no config marca como token as cartas que a API imprime como
base mas que o são: `Recruit (DE/NX/ZN)` e `Sprite` (OGN-271..274), `Gold`
(SFD-003), e os nomes que só existem como token noutras edições. **A lista é
palpite meu, por confirmar.** O flag propaga-se da carta lógica para todas as
impressões dela (`catalog.rebuild_cards`).

## Faltas: carência GLOBAL, não alocação

`faltas.py` responde a "o que comprar primeiro". A conta é diferente da do
`decks.allocate`: aqui soma-se o que TODOS os decks pedem de uma carta e
desconta-se o que ele tem. A alocação por prioridade responde a outra coisa
(quem fica com o quê) e não serve para decidir compras.

- **TETO POR CARTA (André, 2026-09-01):** a carência é limitada ao alvo de
  playset da carta, mesmo que a soma dos decks peça mais. Cinco decks a pedir
  3 Defy não são 15 Defy para comprar — são 3, e trocam-se entre decks. Isso
  vale 3 nas Units/Spells/Gears, **12 nas Runas** e **1 nos Legends e
  Battlefields**, porque é o mesmo alvo da métrica de playset jogável. Efeito
  medido: 88 -> 85 cartas, 262 -> 210 cópias, 919,94 € -> 848,01 €.
- **Runas fora da conta (André, 2026-09-01):** `faltas_ignorar_tipos` no
  config, default `["Rune"]`. São baratas e compram-se a granel, e a 12 por
  deck enchiam os staples. **Só afeta a secção Faltas** — na secção Decks e na
  Coleção continuam a contar, porque aí a pergunta é outra.
- **Staples** = carência > 0 e pedida por >= 2 decks. É o critério de "rende
  mais por euro".
- **A subir** = **todo o Riftbound**, não só a coleção (André, 2026-09-01):
  serve para apanhar cartas a valorizar antes de entrarem num deck dele. As
  que ele tem ou de que precisa vêm marcadas. O `prices.sync_prices` grava
  histórico das **1178** impressões com preço, não só das de interesse.
- A prontidão mede-se em **impressões com duas leituras**, não em dias
  gravados: o histórico só escreve quando o preço muda, por isso é normal ter
  vários dias e nada comparável. Enquanto não houver, a aba diz isso — não
  inventa tendência.
- O `pct` é **primeiro -> último** dentro da janela, com sinal. Uma carta que
  desceu não aparece; verificado com dados reais (o `Not So Fast` foi de 2,10
  para 0,70 e ficou de fora, como devia).
- Custo em disco medido: o `prices.db` passou de 52 KB para 140 KB ao alargar
  de 290 para 1178 impressões. Cresce só com o que muda. Se um dia incomodar,
  o sítio para podar é aqui.

## "Pimp decks"

`faltas.pimp()` — quarta aba das Faltas. Todas as impressões **alteradas** das
cartas que os decks usam: artes alternativas, signatures, as reimpressões
showcase (que têm número de coleção próprio) e as promos. Alterada = tudo o
que não é a impressão canónica, e canónica é a base da edição mais antiga.

**Fora:** `pimp_ignorar_tipos`, default `["signature", "rune_promo"]` —
decisões dele, 2026-09-01. Nas runas a versão que ele quer pimpar é a **arte
alternativa do OGN**, não a promo do VEN (`VEN-R01`..`R06`). Ficam as artes
alternativas, as reimpressões showcase e as promos especiais (`sp1`..`sp6`).

**É lista de compras** (mudou 2026-09-02). Desconta o que ele tem **e o que
vem a caminho**, por impressão: a quantidade mostrada é só o que ainda falta
comprar. As versões já completas saem da lista e contam em `done`. Antes
mostrava tudo, incluindo o que ele já tinha — ele pediu para tirar.

**Arruma-se por DECK, nunca por edição** (André, 2026-09-01). A vista "Todas"
tem um cabeçalho por deck; as sub-abas mostram um deck de cada vez, em grelha
corrida. O `by_set` continua a existir no payload mas o frontend achata-o
(`achata()`), ordenando pelo custo — é o custo que decide a troca.

A decisão de pimpar é por deck: é a olhar para um deck de cada vez que ele
decide o que trocar. Na vista por deck a quantidade é a que AQUELE deck usa;
na global é a soma com o teto. Uma carta usada por dois decks aparece nos dois
— aqui isso é a informação, não duplicação a evitar.

**Cuidado com os contadores.** A vista "Todas" mostra os decks um a seguir ao
outro, por isso a soma dos decks é o que se vê no ecrã — não o `printings` do
payload, que é a vista global com quantidades somadas. A aba e o resumo usam
a soma dos decks, senão o número no separador não batia com os tiles.

**A lista dos decks leva SÓ a versão mais barata** (André, 2026-09-01). Houve
uma versão com um visto "com artes alternativas" na lista dos decks; foi
retirada, é aqui que essa pergunta vive.

## BURACO NO CATÁLOGO: 48 impressões que a RiftScribe não tem

Medido a 2026-09-01, contra os blueprints do CardTrader:

| edição | CardTrader | RiftScribe | a mais no CT |
|---|---|---|---|
| OGN | 353 | 352 | 1 (token `Buff`) |
| OGS | 25 | 24 | 1 |
| SFD | 302 | 288 | **14** (runas R01–R06 + artes alt., tokens) |
| UNL | 300 | 288 | **12** (artes alt. das runas) |
| VEN | 247 | 228 | **20** (artes alt. das runas + 9 signatures) |

Confirmado na fonte: `GET /api/cards?set_id=SFD&type=Rune` devolve
`X-Total-Count: 0`. A RiftScribe só tem runas no OGN (12) e no VEN (6).

**Consequência prática.** O André pediu que o Pimp mostrasse, nas runas, as da
edição do Legend do deck. Os dois decks dele têm Legend do SFD, e as runas
alternativas do SFD existem (`SFD-R01a`..`R06a` no CardTrader) — mas não estão
no catálogo, por isso continua a aparecer a do OGN.

A preferência **já está implementada** (`pimp()` -> `montar(pedido, preferir)`)
e passa a funcionar sozinha assim que o catálogo tiver as cartas. Hoje não
muda nada.

**Resolvido com `catalog.market_only`** (2026-09-01). O André deixou a decisão
comigo e escolhi o caminho do meio: as 48 impressões ficam numa tabela à
parte, **fora do catálogo**.

- Não entram na grelha da Coleção nem em métrica nenhuma. As barras de
  progresso, o master set e as contagens por raridade continuam a medir os
  1180 da RiftScribe — que é a fonte que tem informação de jogo (tipo,
  domínio, custo). O CardTrader não dá nada disso.
- Entram **só na aba Pimp**, marcadas "fora do catálogo", porque aí a
  pergunta é de mercado e não de coleção.
- Casam-se com a carta lógica por número de coleção e, falhando isso, por
  nome: 41 das 48. As 7 que sobram são tokens que não temos.
- Levam preço (o `sync_prices` inclui-as) e imagem do CardTrader.

**ARMADILHA — colisão de números no CardTrader.** Eles escrevem a `Calm Rune`
alternativa do SFD com o mesmo `R02` da base. Deduplicar o índice por número
de coleção fazia desaparecer a segunda — justamente a runa que o deck do Ornn
quer. O `sync_map` guarda agora a lista toda (`singles`) e usa o índice só
para casar; o `market_only` sai do que não foi casado, por `blueprint_id`.

**Efeito:** os dois decks têm Legend do SFD e passam a mostrar as runas
alternativas do SFD (`SFD-R02`, `SFD-R03a`, `SFD-R06a`) em vez das do OGN.

## Wantlist do Cardmarket

`faltas.wantlist()` gera `qtd Nome (Edição)` por linha. Botão na secção
Faltas → Por deck, e `riftvault wantlist [--deck X] [--todos] [--out f.txt]`.

**O nome tem de ser o DO MERCADO, não o da RiftScribe.** Lá é
"Darius, Trifarian", no Cardmarket/CardTrader é "Darius - Trifarian" —
vírgula contra hífen. 414 das 1179 impressões diferem. O `cardtrader_map`
guarda `market_name`, `market_set` e `cardmarket_id`, recolhidos no
`riftvault map`.

A edição vai junto porque 104 nomes existem em mais do que uma edição e sem
ela ficaria ambíguo.

**NÃO VALIDADO contra o Cardmarket.** O site responde 403 a pedidos
automáticos e não há conta para experimentar. O formato `qtd nome (edição)` é
o que a ajuda deles documenta e o que as extensões de bulk import usam. Que o
Cardmarket tem Riftbound está confirmado: **as 1178 impressões têm
`card_market_ids`** nos blueprints do CardTrader.

**Formato confirmado na ajuda deles:** `4x High Tide (V.1) (Fallen Empires)` —
quantidade, nome, versão opcional, edição opcional.

**O FOIL NÃO SE MARCA NO TEXTO.** Confirmado: no Cardmarket o foil é um filtro
*por entrada*, posto na interface depois de a carta entrar na lista, a par de
idioma, condição, signed e altered. Por isso o `wantlist()` devolve também
`foil` — as linhas cujas impressões só têm oferta foil no mercado (623 das
1179) — para ele saber onde ligar o filtro à mão. Não inventar uma sintaxe.

**As versões (V.n) são INFERIDAS, não lidas.** `_versoes()` agrupa pelo
`group_key` — edição + número de coleção — e numera pela ordem do variante.

**Foi o André que corrigiu o agrupamento** (2026-09-01): "as signatures são
normalmente as V.2". Eu agrupava por carta lógica, e a `Daughter of the Void`
do OGN dava três versões (base 247, showcase 299, signature 299*), pondo a
signature em V.3. Se lá é V.2, o Cardmarket trata a 247 e a 299 como produtos
diferentes e só junta as impressões que partilham número de coleção. Com o
agrupamento certo, **as 36 signatures ficam todas em V.2 e as 102 artes
alternativas também** — consistente com o que ele vê no site.

Isto também resolve o problema do nome: o CardTrader escreve a arte
alternativa de 3 cartas com vírgula e a base com hífen ("Darius, Trifarian" vs
"Darius - Trifarian"), e agrupar por nome partia-as em dois grupos de um.
Todas as versões saem com o nome da base.

**ARMADILHA — o `price_latest` mora no catalog.db, que é descartável.** Apagar
o catalog.db deita fora os preços atuais e só o `riftvault prices` os repõe.
O histórico sobrevive (está no prices.db). No GitHub Actions isto resolve-se
sozinho porque o sync e os preços correm em sequência; localmente, quem apagar
o catálogo tem de voltar a correr os preços.

**A caixa de texto não é um fallback do clipboard, é o mecanismo principal.**
O `navigator.clipboard` exige contexto seguro, e no telemóvel isto abre por
http num IP da rede local — lá nunca funcionaria.

## Encomendas a caminho (`pending`)

Uma carta comprada mas ainda não recebida não está na coleção — mas também já
não é uma falta. A tabela `pending` (vault.db) é a diferença entre as duas:

- **Fora do `copies`**: a Coleção mede o que está na caixa. As barras de
  progresso, o valor e o master set não mexem enquanto a encomenda vem.
- **Descontada das faltas**: o `faltas.shortfall`, o `por_deck` e o
  `todos_juntos` somam o pendente ao que ele tem, senão as listas mandavam
  comprar outra vez.
- `pending.arrive()` passa para o `copies` pelo `collection.adjust`, portanto
  fica no `ops` e dá para desfazer.

Aceita `market_only`: ele comprou runas do SFD que a RiftScribe não tem, e
essas contam na mesma (`pending.open_by_card` junta as duas fontes).

**Aliases das market_only.** O `sync_map` regista `sfd-r02a` -> `ct-374043`
no `printing_aliases`, com o sufixo `a` acrescentado quando o CardTrader o
omite. Sem isso o `riftvault add SFD-R02a` falhava — e foi assim que a fatura
dele veio escrita.

## Onde está cada cópia

`decks.printing_allocation` responde a "não encontro a carta no binder, onde
está?". A alocação por prioridade é por carta lógica — diz que o Azir leva 3
Brutalizer, não de que impressão. Aqui escolhe-se a impressão, e a regra é
**artes base primeiro**, para as alternativas e signatures ficarem no binder.

Aparece nos dois lados: no tile da Coleção (`2× Ornn · 1 no binder`) e na
grelha do deck. Não confundir com o `shared` da alocação, que é a carta que
falta a este deck por estar num deck anterior.

## Ordenação da grelha (REMOVIDA)

Houve ordenação por Tipo/Raridade/Custo e por folhas do binder. **O André
mandou tirar as duas** (2026-09-01): a grelha vai só por número de coleção, e
ele organiza o binder à mão. Não voltar a acrescentar sem ele pedir.

## Preços: CardTrader (2026-08-31)

A RiftScribe **não tem preços nenhuns** — procurado `price`, `market`, `usd`,
`eur`, `tcgplayer`, `cardmarket` em toda a spec: zero. O Cardmarket responde
403 a bots. A fonte é o **CardTrader**, API v2, `CARDTRADER_TOKEN` no ambiente.

**Riftbound é o `game_id` 22.** As expansões do CardTrader têm `code` igual ao
`set_id` da RiftScribe em minúsculas: `ogn` 4166, `ogs` 4275, `sfd` 4299,
`unl` 4425, `ven` 4521. Os singles são `category_id` 258; o resto é selado.

**A ponte, validada:** o `fixed_properties.collector_number` dos blueprints já
traz o sufixo da variante — `007` base, `007a` arte alternativa, `299s`
signature. Casa diretamente com `(set_id, collector_number, variant)`, sem
comparar nomes (que são diferentes: "Jinx - Loose Cannon" lá, "Loose Cannon"
cá). **Medido: 1179/1180 (99,9%), sem ambiguidades.** A única que falha é
`VEN-T04 "Recruit (NX)"`, um token que o CardTrader não lista. O CardTrader
tem impressões a mais que a RiftScribe ainda não tem (runas promo do SFD/UNL,
signatures do VEN); ficam de fora por não haver impressão nossa.

**ARMADILHA — User-Agent com acentos dá 403.** Testado: `"...colecao"` devolve
200, `"...coleção"` devolve 403. Os User-Agent do `prices.py` e do
`riftscribe.py` são ASCII puro de propósito. Não lhes ponhas acentos.

**Critério de preço:** menor preço pedido em Near Mint/Mint, inglês, sem
graded/altered/signed, vendedor não ausente. Tudo vem em EUR. Prefere-se a
oferta não foil; se não houver nenhuma usa-se a foil e marca-se `from_foil`.

**A ressalva que importa:** `riftbound_foil` é significativo mas está muito
desequilibrado — em OGN, 179 blueprints só têm ofertas foil, 164 têm as duas e
só 28 são só normal. Como o riftvault não distingue acabamentos, o valor das
cartas que só existem em foil no CardTrader pode estar **sobreavaliado**. Por
isso `collection_value` devolve `cents_de_foil` e o `riftvault value` diz que
percentagem do total vem daí — não escondas esse número num total limpo.

**Onde ficam:** `catalog.price_latest` (as 1180, descartável) e `price_history`
no `vault.db` (só as que ele TEM, e só quando o preço muda — o vault.db vai
para o Git e cada commit guarda o ficheiro inteiro).

## Vista por omissão: todas as impressões

**Decidido (André, 2026-08-31):** a grelha abre em "Todas as impressões", não
em "Só artes base". O botão continua lá, mas não é o default
(`app.js` -> `state.prefs.view = 'all'`).

## Servidor

Flask (o André pediu FastAPI ou Flask, "o mais simples"). Uma ligação SQLite
por pedido, porque os objetos do `sqlite3` não atravessam threads e o servidor
corre em modo `threaded`.

O QR usa o pacote `qrcode`; se não estiver instalado, ou se a consola não
aguentar os blocos, imprime só o URL. A consola do Windows abre em cp1252 —
`cli.main()` força UTF-8 na saída, senão os acentos e o QR rebentam.

## Decks (2026-08-31)

**Alocação por prioridade.** Os decks têm uma ordem (`decks.priority`, 1 =
principal). Percorrem-se por essa ordem e cada um serve-se do que sobra: o
deck 1 fica com o que precisa, o deck 2 só recebe o que sobrou. Uma carta que
falte ao deck 2 **por já estar noutro deck** é mostrada com o deck onde está —
é diferente de não a ter, e não entra na lista de compras desse deck.

A alocação é **global e por carta lógica**, não por deck nem por papel: mudar
a ordem refaz tudo (`decks.allocate`). Uma carta que esteja no main e no
sideboard disputa o mesmo stock.

**Nome do separador:** Legend · Champion (pedido do André).

**Apagar um deck** = apagar o `.txt`. O `import_all` remove da base os decks
cujo ficheiro desapareceu. O servidor relê os ficheiros quando algum mexeu
(`server._reimport_if_changed`), não é preciso reiniciar.

**Formato das listas:** secções com cabeçalho terminado em `:` (Legend,
Champion, MainDeck, Battlefields, Rune Pool, Sideboard) e linhas `N Nome`.
Aceita também códigos (`3 OGN-045`).

**ARMADILHA — nomes dos Legends.** As listas escrevem `Azir, Emperor of the
Sands`, mas no catálogo o Legend é só `Emperor of the Sands`. Quando o nome
exato falha, tira-se o prefixo antes da primeira vírgula. É seguro:
**nenhum dos 49 Legends tem vírgula no nome** (verificado).

**Regras de legalidade** (`deck_rules` no config): main 40, runas 12,
battlefields 3, máximo 3 cópias, identidade de domínio pelo Legend.
`main_includes_champion: true` foi **inferido** das duas listas do André, que
têm 39 no MainDeck + 1 Champion = 40 — **não validado contra as regras
oficiais**. Se estiver errado, é uma linha no config.

## Estado

- **Feito:** catálogo, as duas métricas, CLI completo, modo edição, modo
  publicado, workflow do Pages, e a vista de Coleção com variantes e `+`/`-`.
- **Feito também:** preços/valor (CardTrader) e a secção Decks com alocação
  por prioridade, validação de legalidade e lista de compras.
- **Por fazer:** vista "todos os decks ao mesmo tempo" (hoje vê-se deck a deck,
  com as partilhadas assinaladas); e apagar decks pela interface (hoje apaga-se
  o `.txt`).

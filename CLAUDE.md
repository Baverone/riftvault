# CLAUDE.md — riftvault

Contexto do projeto para o Claude Code. Lê isto antes de mexer em código.

## O que é

Gestor pessoal da coleção de **Riftbound** (TCG da Riot), do André. Python +
SQLite, mesma arquitetura do `mtgvault`. Objetivo: ter **playsets**, incluindo
artes normais **e** alternativas.

Secções: **Coleção**, **Decks**, **Faltas** e **Venda**.

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

**O IP da LAN muda sozinho.** A 2026-09-02 a rede passou de `192.168.0.x`
para `192.168.1.x` e o URL que ele tinha deixou de responder — pareceu que o
site tinha ido abaixo, mas o servidor estava de pé. O `serve` passa a listar
**todos** os endereços (`server.lan_ips()`), porque mostrar um só engana
quando há Ethernet e Wi-Fi em sub-redes diferentes.

Nem o `getaddrinfo(gethostname())` nem sondar a tabela de rotas com um socket
UDP encontram a interface secundária quando a principal tem métrica melhor —
os dois foram testados. É preciso perguntar ao sistema (`ipconfig` no Windows,
`ip -4 -o addr` no resto).

Isto continua a acontecer enquanto for DHCP. A cura é o Tailscale, que dá um
endereço fixo.

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
7. **Endereço da página da carta**, no CardTrader e na RiftScribe. Nenhuma das
   duas APIs o dá, e a aba "A subir" precisa de um link. Os formatos usados
   (`cardtrader.com/cards/<blueprint_id>`, `riftscribe.gg/cards/<printing_id>`)
   são **presunção minha, por abrir e confirmar**. Ficam em `a_subir.DEFAULTS`
   e mudam-se numa linha.

---

# Decisões de implementação (2026-08-31)

## Sem acabamentos

Decisão do André: **foil e normal contam como a mesma coisa**. A tabela
`copies` é só `(printing_id, qty)` — não há coluna `finish`. O CLI aceita
`--foil` e ignora-o, para não dar erro por hábito.

O alvo do master set é por impressão, e qualquer cópia serve para o cumprir.

Se um dia isto mudar: acrescentar `finish TEXT NOT NULL DEFAULT 'normal'` a
`copies`, passar a PK a `(printing_id, finish)`, e o mesmo em `ops`.

## Artes alternativas fora do master set

`master_targets_by_variant.alt_art = 0` (André, 2026-09-02). A percentagem de
set completo passa a medir só a impressão base e as signatures; as artes
alternativas continuam na grelha, contam para o playset jogável e para o
valor da coleção, mas **não entram no denominador**.

Denominadores: OGN 352 -> 322, SFD 288 -> 264, UNL 288 -> 258, VEN 228 -> 210.
(**A 2026-09-08 os tokens juntaram-se-lhes** e estes números baixaram outra vez
— SFD 263, UNL 250, VEN 209. Ver a secção "A Coleção é o master set".)

**ALVO e CONTA são campos diferentes** (2026-09-02). A primeira versão pôs o
alvo da arte alternativa a 0, e o tile perdeu o `0/1` — ele quer ver quantas
lhe faltam, só não quer que baixem a percentagem. São duas perguntas, agora
com dois campos:

- `master_targets_by_variant` -> o alvo fixo por variante.
- `master_variantes_playset` -> as variantes cujo alvo segue o playset do tipo
  em vez do alvo fixo (`["alt_art"]`, ver a secção abaixo).
- `master_set.fora` -> o que fica fora do master set (era
  `master_ignorar_variantes: ["alt_art"]`, desde 2026-09-08 é `["-T", "a"]`),
  via `metrics.e_master()`.

O payload leva `block` por impressão e o `renderProgress` respeita-o — a
percentagem é recalculada no cliente, por isso não bastava mudar o servidor.
(O campo chamava-se `counts` até 2026-09-08; passou a ser o bloco da grelha,
porque é a mesma pergunta.)

## A Coleção é o master set: os `-T` e os `a` vão para o fim (2026-09-08)

Palavras dele: *"As cartas que forem 'sigla-T' ou 'a' no fim (de arte
alternativa) não as quero na sequência do master set; quero-as ordenadas depois
do master set. A Coleção é de master set. O resto provavelmente vai para venda
ou jogar nos decks seleccionados."*

**A regra é o CÓDIGO IMPRESSO**, e no catálogo lê-se pelo `variant_kind`, que é
derivado do mesmo sufixo: `UNL-T03` -> `token`, `UNL-228a` -> `alt_art`.
Ficam **dentro** do master set tudo o que ele não nomeou: as signatures
(`OGN-299*`), as runas promo (`VEN-R01`) e as promos especiais (`VEN-SP4`).

**Uma função só: `metrics.e_master(printing)`.** Havia duas leituras a divergir
— a percentagem já ignorava as artes alternativas (2026-09-02) mas a grelha
punha-as na sequência, e os tokens contavam para a percentagem. Agora a métrica,
a grelha, o «A subir», a lista do master set e a Venda perguntam todos à mesma
função. O `metrics.master_counts` foi **removido**. Configura-se em
`master_set.fora`, hoje `["-T", "a"]` (ver a secção a seguir).

**O que mudou nos números** (medido a 2026-09-08, só os tokens saem — as artes
alternativas já estavam fora):

| | antes | agora |
|---|---|---|
| denominador do master set | 1078 | **1068** |
| SFD / UNL / VEN | 264 / 258 / 210 | **263 / 250 / 209** |
| âmbito do «A subir» | 1042 | **1032** |
| lista do master set | 695 impressões, 29 441,06 € | **686, 29 440,08 €** |

O OGN e o OGS não mexem: não têm tokens com sufixo `-T`.

**Os tokens com número de coleção próprio ficam.** `OGN-271/298` (o Recruit) e
`SFD-003` (o Gold) são tokens por natureza — é o que o `token_card_keys` marca —
mas o código deles não leva sufixo nenhum: estão numerados dentro da edição, por
isso continuam na sequência. A regra é o código, não a natureza da carta.

### Ordem: blocos, nunca intercalados

A grelha percorre os grupos **uma vez por bloco**: primeiro o master set
inteiro, por número de coleção; depois «Fora do master set — tokens»; depois
«Fora do master set — artes alternativas». O `metrics.BLOCOS` manda na ordem e
nos rótulos, o payload leva `block` em cada impressão e a lista `blocks` do
set, e o `render()` do `app.js` faz os dois ciclos. O `metrics.ordem_da_grelha`
diz a mesma ordem em Python, para dar para testar sem browser.

Isto era mesmo visível: em UNL a sequência era `UNL-001, UNL-T01, UNL-002,
UNL-T02, ...` — um token entre cada duas cartas.

**Cada bloco de fora tem contador próprio** ("tens N de M"), recalculado no
cliente como as barras. O alvo dos tiles não mexeu: uma alt art de Unit continua
a mostrar `0/3` e um token `0/1` — ALVO e CONTA são campos diferentes desde
2026-09-02.

**O VEN continua a intercalar as runas promo e as promos especiais**
(`VEN-001, VEN-R01, VEN-SP1, VEN-002, ...`). Ele não as nomeou e ficaram como
estavam. Se quiser, é acrescentar `"-R"` e `"-SP"` ao `master_set.fora` — mas
isso tira-as **também** da percentagem, porque é a mesma pergunta.

### A lista escreve-se pelos sufixos: `master_set.fora` (2026-09-08)

A regra é o código impresso, mas a lista escrevia-se pelo nome interno da
variante — duas escritas para a mesma coisa. Passou a ser
`"master_set": { "fora": ["-T", "a"] }`, que é como ele fala. O
`metrics.kinds_fora()` traduz para `variant_kind`:

| escreve-se | tira | exemplo |
|---|---|---|
| `-T` | tokens | `UNL-T03` |
| `a` | artes alternativas | `UNL-228a` |
| `*` | signatures | `OGN-299*` |
| `-R` | runas promo | `VEN-R01` |
| `-SP` | promos especiais | `VEN-SP4` |

Aceita também os nomes das variantes (`token`, `alt_art`, ...) — dão o mesmo.
`master_ignorar_variantes` é o nome antigo da lista e continua a ser lido:
a tradução está no `config._migrar_master_set`, para haver uma leitura só do
config. Um ficheiro com os dois nomes usa o novo.

**Um valor desconhecido rebenta (`ValueError`), de propósito.** É o ponto 6 das
"Superfícies não validadas": uma edição nova pode trazer um sufixo novo, e isso
tem de aparecer em vez de ser contado em silêncio.

**As signatures ficam preparadas e DESLIGADAS.** Acrescentar `"*"` manda-as
para um bloco próprio no fim da grelha («Fora do master set — signatures») —
o `metrics.BLOCOS` passou a ter um bloco com rótulo por variante, para nada
cair no genérico «outras»; os vazios não aparecem, por isso hoje continuam a
ver-se três. Fica desligado porque **é decisão dele e ele não a tomou**: nomeou
os `-T` e os `a`, não estas. Medido: ligar baixa o denominador de **1068 para
1032**. Não confundir com o `a_subir.excluir`, que já as tira das listas
de compra sem lhes mexer na percentagem.

## Secção «Venda» (2026-09-08)

A segunda metade da frase dele: *"o resto provavelmente vai para venda ou jogar
nos decks seleccionados"*. `riftvault/venda.py`, `api/venda.json`, quarta secção
no frontend e `riftvault venda` no CLI.

Pega no que está fora do master set e ele **tem na caixa**, e parte em duas:
**usada num deck seleccionado** (a cópia está alocada a um deck) e **candidata
a venda**. Uma impressão pode ser as duas: 2 cópias num deck e 1 a mais vende
só 1.

**Quem decide o que está num deck é o `decks.printing_allocation`** — a mesma
função do "2× Ornn · 1 no binder" do tile. Ela escolhe **artes base primeiro**,
de propósito, por isso uma arte alternativa só aparece alocada quando não há
cópias base que cheguem. É a resposta certa aqui: essa alt art está a ser jogada
porque faz falta.

**NADA SAI DA BASE.** Não há botão de vender, não se mexe no `copies` nem no
`ops` — é uma sugestão. Há teste que confirma que o `listar()` não escreve.

Medido a 2026-09-08: **23 impressões, 28 cópias, 106,18 €** (22 artes
alternativas + 5 cópias do `SFD-T03` Gold). Duas ficam de fora por estarem em
decks: `OGN-042a` Calm Rune ×6 (Azir) e `OGN-089a` Mind Rune ×1 (Ornn).

**A ressalva:** a lista sai no formato de **wantlist** do Cardmarket
(`N Nome (V.n) (Edição)`), o mesmo das listas de compra — foi o que ele pediu.
**Não é o formato de importação de stock de vendedor**, que não foi validado e
não se inventou.

**Tensão conhecida, por decidir com ele:** a lista mostra a impressão inteira,
não só o que passa do alvo. Uma alt art com 1 cópia e alvo 3 aparece na mesma
como candidata a venda, e as 5 cópias do Gold também (alvo 1). É o que a frase
dele diz — o que está fora do master set vai para venda ou para os decks — mas
choca com o alvo de playset das alt arts de 2026-09-05. Se ele quiser guardar o
alvo, muda-se numa linha em `venda.listar`: `sobra = qty - max(usadas, alvo)`.

**O gerador do Cardmarket é o mesmo.** A quantidade da linha passou a sair do
`cardmarket.quantidade()`: `missing` nas listas de compra, `qty` na de venda.
O gémeo em JavaScript é o `cmQtd`, e há smoke test que compara os dois texto a
texto.

**O Pimp NÃO foi tocado**, de propósito. Ele é uma lista de compra de artes
alternativas — precisamente do que está fora do master set — mas a pergunta
dele é de DECK, não de coleção: "que versão da carta que já jogo é que quero
mais bonita". Tirar-lhe as alt arts era apagar a aba. As listas que passaram a
ignorar o que está fora do master set são as que medem a coleção: «A subir» e
«Master set».

## Impressões vetadas no Pimp (2026-09-05)

"troca essa versao do Baron Nashor por outra Alt Art, nunca irei comprar essa
carta" — o `unl-238-219` estava a 2400,64 € e sozinho fazia 79% do total do
deck do Kennen (3028 € -> 627 € depois de sair).

`pimp_ignorar_impressoes` é uma lista de `printing_id`, filtrada em
`faltas.pimp()` a seguir ao `pimp_ignorar_tipos`. Veta a impressão, não a
carta: o Baron Nashor continua no Pimp pela arte alternativa `unl-147a-219`
(20,27 €), que já lá estava — as duas apareciam lado a lado.

**A classe toda:** 128 impressões têm número de coleta acima do tamanho
nominal do set (OGN 298, SFD 221, UNL 219, VEN 166). 36 são signatures, já
fora por `pimp_ignorar_tipos`; as outras 92 são `variant_kind = base` —
Legends, Units e Gear, mediana 80 €, mínimo 31 €. Não foram vetadas em bloco:
ele só falou desta. Se um dia pedir, a regra existe e é `collector_number >
tamanho do set`.

### Alt arts com contagem de playset (2026-09-05)

O alvo fixo de 1 não chegava: "para as Alt Art tbm quero a contagem de playset,
elas contam na ordenação, contam para os decks, mas não contam para a % de
faltas". O alvo da arte alternativa passou a seguir `playset_targets_by_type`,
como já fazia a base — Unit/Spell/Gear 3, Rune 12, Legend e Battlefield 1.

Configura-se em `master_variantes_playset`. O que decide a percentagem não
mexeu, por isso os denominadores foram exatamente os mesmos (OGN 322, SFD 264,
UNL 258 — a 2026-09-08 os tokens baixaram os dois últimos, ver adiante).
O que muda é o badge do tile e, por consequência, o filtro "Faltas" da
grelha: uma `Calm Rune` alt art com 6 cópias lia-se 6/1 (completa) e agora lê-se
6/12 (parcial), que é o ponto — ele quer ver quantas lhe faltam.

Não mexe na secção Faltas nem nos decks: ambos usam `playset_target` por carta
lógica, nunca o alvo do master. Confirmado depois da mudança: 15 cartas, 26
cópias, 170,28 € — igual ao de antes.

O "valor se estivesse completa" segue o `counts`, não o alvo: se a variante
não faz parte do set, não faz parte do preço de o completar.

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

**REVOGADO EM PARTE a 2026-09-08.** O `token_target: 1` continua a ser o ALVO —
o tile diz `0/1` e ele vê quantos lhe faltam — mas os tokens com código `-T`
deixaram de entrar na **percentagem** de master set e passaram para um bloco no
fim da grelha. Ver "A Coleção é o master set".

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
  deck enchiam os staples. **Só afeta as abas dos decks** (Staples, Por deck e
  as wantlists) — na secção Decks, na Coleção e na aba A subir continuam a
  contar, porque aí a pergunta é outra.
- **Staples** = carência > 0 e pedida por >= 2 decks. É o critério de "rende
  mais por euro".
- **A subir** mudou de âmbito a 2026-09-08 e mudou de casa: vive agora no
  `a_subir.py` e já não depende dos decks. Ver a secção própria abaixo.
- Custo em disco medido: o `prices.db` passou de 52 KB para 140 KB ao alargar
  de 290 para 1178 impressões. Cresce só com o que muda. Se um dia incomodar,
  o sítio para podar é aqui.

## "A subir": só o master set, só o que ainda não tem (2026-09-08)

Palavras dele: *"confere todas as cartas de Riftbound de masterset e as que
subirem pelo menos 10% assinalas; na página ordenas por % de um lado e por
valor no outro (duas abas); quando já tenho as cartas, deixas de seguir — isto
vai servir só para o que eu ainda não tenho. Depois arranjamos um valor métrico
para dar 'urgência' a comprar."*

Isto **revoga a decisão de 2026-09-01** de a aba ser o Riftbound inteiro. O
`prices.sync_prices` continua a gravar as 1178 — o histórico é barato e serve
de base — mas a **vista** passou a ser uma lista de vigia de compras.

`riftvault/a_subir.py`, chamado pelo `faltas.payload()` na chave `a_subir` (era
`spiking`). O `faltas.py` ficou sem a função e sem as constantes `SPIKE_*`.

**"Masterset" é a métrica 2, não uma edição.** Ele não tem no catálogo nenhum
set chamado assim; o que o riftvault chama master set é o alvo por IMPRESSÃO.
O âmbito são por isso as impressões que entram na **percentagem de set
completo** (`metrics.master_target > 0` e `metrics.e_master`), nas cinco
edições: eram **1078 das 1180**, e desde 2026-09-08 são **1068**. Ficam de fora
as 102 artes alternativas e os 10 tokens `-T`, por `master_set.fora`.
Seguir cartas que não contam para o master set seria medir outra coisa que não a
barra que ele vê na Coleção.

**"Ainda não tenho" = a regra do filtro Faltas da grelha**, `cópias + a caminho
< alvo do master`. Uma Unit com 1 de 3 ainda o obriga a comprar 2, logo o preço
ainda lhe interessa. O que vem a caminho conta como tido, como em toda a secção
Faltas. Muda-se em `a_subir.regra_falta`: `"nenhuma"` segue só as que estão a
zero cópias. Medido a 2026-09-08: **686 seguidas** com a regra `master` (eram
731 antes de os tokens saírem do master set, e 695 depois de as signatures
saírem das listas de compra).

**O preço de há N dias é o que estava EM VIGOR nessa data**, não o primeiro
registo dentro da janela. O `price_history` só grava quando o preço muda: uma
carta que valia 1 € há 90 dias e subiu para 2 € há 3 dias tem um único registo
na janela, e comparar com ele dava 0%. A versão antiga fazia isso e media
subidas a menos. Quando não há registo nenhum antes do início da janela usa-se
o mais antigo que existe e a linha diz **"desde <data>"** — hoje é o caso das
57, porque o histórico só começa a 2026-08-31.

**As duas ordens saem do servidor** (`rank_pct`, `rank_valor`) e não do
cliente, para os desempates viverem num sítio só e serem testáveis. O filtro de
raridade usa a raridade da **base**, como os contadores da Coleção.

**A urgência está DESLIGADA de propósito** (`a_subir.urgencia: false`). A
fórmula proposta é `Δ%_janela × 0,5 + Δ%_curto × 1,0 + (preço_hoje /
preço_mediano_da_raridade) × 10`, com os pesos no config. Está calculada em
todos os itens (`urgency`) mas a coluna não aparece — é uma proposta à espera
do veredito dele, não uma decisão minha. Nota medida: o terceiro termo domina
os outros dois nas cartas caras (o `Bloodharbor Ripper` a 133 € dá 7983 contra
466 do topo por %), por isso ou o peso baixa ou o preço relativo entra em log.

**NÃO VALIDADO — os links das cartas.** Nem a RiftScribe nem o CardTrader dão o
endereço da página da carta em lado nenhum da API, e nesta corrida não houve
rede para experimentar. Os dois formatos (`cardtrader.com/cards/<blueprint_id>`
e `riftscribe.gg/cards/<printing_id>`) são presunção, e estão em
`a_subir.DEFAULTS` para se corrigirem numa linha se abrirem em 404.

### Showcases fora das listas de compra (2026-09-08)

*"No riftvault, 'a subir', tira também os showcases."* Segunda exclusão do
mesmo dia, e a que obrigou a config a mudar de forma.

**O showcase NÃO é um `variant_kind`, é uma `rarity`.** As 42 que saem têm
todas `variant_kind = base`: são as reimpressões showcase com número de coleção
próprio da ARMADILHA 2 (`SFD-232/221`, `OGN-299/298`). O `excluir_tipos`, que
só lia variantes, não lhes tocava — por isso passou a haver dois campos:

```json
"a_subir": { "excluir": { "tipos": ["signature"], "raridades": ["showcase"] } }
```

`excluir_tipos` é o nome antigo e continua a ser lido, **a valer o que valia**:
`config._migrar_a_subir` traduz para `{"tipos": [...], "raridades": []}`, com as
raridades vazias de propósito — um ficheiro escrito antes de hoje não excluía
raridade nenhuma e não é a migração que lhe muda a resposta. Um ficheiro com os
dois nomes usa o novo. Como nos pesos da urgência, escrever só um dos campos não
apaga o outro.

**A página diz quantas tirou POR CRITÉRIO**, e cada impressão conta uma vez só,
pelo primeiro que lhe bate (tipos antes de raridades). É preciso escolher:
**as 36 signatures também têm raridade `showcase`**, e contá-las nas duas dava
uma soma maior que o total. Hoje lê-se «78 impressões (36 signature + 42
showcase)». O `a_subir.resumo_fora` é quem faz esta conta, e o `foraTexto` do
`app.js` escreve o mesmo texto nas duas abas.

**Medido a 2026-09-08:** «A subir» passou de 53 para **49 cartas**, de 122 para
114 cópias e de 3405,14 € para **2858,02 €**. As quatro que saíram são todas do
SFD: `SFD-228` Bard (55,64 € ×3), `SFD-232` Sett (69,64 € ×3), `SFD-242`
Glorious Executioner (85,64 €) e `SFD-243` Void Burrower (85,64 €). O chip de
raridade «showcase» desapareceu da barra de filtros. A lista do «Master set»
passou de 686 para **647 impressões**, de 1411 para 1337 cópias e de 29 440,08 €
para **21 056,34 €** — e ficou sem nenhuma impressão sem preço.

**Não mexe na métrica**, como as signatures: `metrics.e_master` não sabe desta
lista e os 42 showcases continuam no denominador da percentagem de set completo
(1068). O âmbito das listas de compra é que baixou de 1032 para **990**.

**A LEITURA QUE FICA POR CONFIRMAR — «showcase» pode querer dizer outra coisa.**
Só o OGN (12) e o SFD (30) têm impressões de raridade `showcase`; as
reimpressões de topo do UNL e do VEN têm raridade de jogo (`rare`, `common`) e
**ficam na lista**. São 48 das 647 do master set, mas valem **18 342,81 € dos
21 056,34 €** — `UNL-221` Lonely Poro a 245,64 €, `VEN-184` Leona a 90,64 €,
`UNL-228` Bloodharbor Ripper a 133,58 €. Se o que ele quis dizer foi *"as
reimpressões caras de topo de set"* e não *"a raridade showcase"*, o filtro
certo é o `collector_number > tamanho nominal da edição` (a classe das 128 já
descrita em «Impressões vetadas no Pimp»), não a raridade. **É pergunta para
ele**; implementou-se o que ele disse à letra.

### Signatures fora das listas de compra (2026-09-08)

"No 'a subir', estás a pôr uma carta signed — não quero." Eram quatro, e valiam
**8 729,69 € dos 12 134,83 €** da lista: `SFD-224*` Aphelios (2000,64 €),
`UNL-234*` Scorn of the Moon (3198,76 €), `OGN-308*` Herald of the Arcane
(1850,64 €) e `OGN-305*` Unforgiven (1679,65 €). A lista passou de 57 para
**53 cartas** e de 12 134,83 € para **3 405,14 €**. (Nesse mesmo dia os
showcases levaram-na de 53 para 49 e de 3405,14 € para 2858,02 € — secção
acima.)

`a_subir.excluir.tipos`, default `["signature"]`, aplicado por
`a_subir.excluir()` logo a seguir ao `masterset()`. Aceita qualquer
`variant_kind`. (A chave chamava-se `excluir_tipos` até nesse mesmo dia os
showcases se lhe juntarem — ver a secção acima.)
**Não mexe na métrica**: as 36 signatures continuam no
denominador da percentagem de set completo (`metrics.e_master` diz que sim) —
o que mudou é a página, e a página diz quantas tirou (`scope.excluded`).
Não confundir com o `master_set.fora`, que tira mesmo do master set.

**Vale também para a lista do master set**, e isso é uma extensão minha do que
ele disse: ele falou da aba "A subir", mas as duas são listas de compra e ele
não compra signatures. É uma linha de config para separar as duas, se ele
quiser a lista completa com elas.

## Listas para o Cardmarket (2026-09-08)

"No final dá-me uma lista para o Cardmarket para eu conseguir comprar as
coisas." Três botões no fim da aba "A subir" e da aba "Master set":

- **Copiar para o Cardmarket** — `N Nome (V.n) (Edição)`, o formato da ajuda
  deles (`4x High Tide (V.1) (Fallen Empires)`).
- **Copiar com código** — `N Nome [UNL-228]`. **Os `[ ]` não são sintaxe do
  Cardmarket** e o importador não os lê: é para ele desambiguar à mão qual das
  versões quer. Está escrito na nota por baixo da caixa.
- **Descarregar CSV** — as oito colunas que ele pediu, com cabeçalho.

**O gerador é UM.** `riftvault/cardmarket.py` em Python (`linha`, `gerar`,
`csv_texto`) e `cmLinha`/`cmCSV` no `app.js`, com smoke test que compara os dois
contra o mesmo payload. O `faltas._versoes` mudou-se para `cardmarket.versoes`
e o `faltas.wantlist` passou a escrever pelo `cardmarket.linha`, para não
haver três formatos a divergir.

**As listas saem do que está no ecrã**, com o filtro activo — a raridade em "A
subir", a edição no "Master set". O `cmLigar` recebe uma *função*, não uma
lista, para o botão apanhar o filtro no momento do clique.

**O total em euros fica FORA do texto** (por baixo da caixa, e no `stderr` do
CLI). Uma linha de total colada na wantlist era importada como se fosse uma
carta.

**NÃO REVALIDADO nesta corrida.** Não houve rede daqui (o `WebFetch` e o
`WebSearch` foram negados pelo modo em que a sessão corria), por isso o formato
é o que já estava registado no CLAUDE.md como confirmado na ajuda deles, e o
mesmo que o `wantlist()` dos decks usa desde 2026-09-01. Não inventei variação
nenhuma. Se algum dia houver rede, o que falta confirmar é se a secção de
Riftbound do Cardmarket aceita a edição escrita como o CardTrader a escreve
("Origins", "Spiritforged", "Unleashed", "Vendetta") — é daí que vem o
`market_set`.

**Medida que interessa:** hoje **as 53 linhas de "A subir" são todas de
impressões que o CardTrader só lista em foil**, e no master set são 371 das
686. O aviso do foil por baixo da caixa deixa de ser uma nota de rodapé e passa
a ser a lista inteira — ver a ressalva do `from_foil` na secção dos preços.

## "Master set": a lista completa das faltas (2026-09-08)

"Lista completa das faltas do master set, não só as que sobem — para ele
comprar tudo o que falta de uma vez se quiser." Aba nova em Faltas,
`a_subir.master_faltas()`: mesmo âmbito, mesma regra de carência e as mesmas
exclusões da aba "A subir", sem o filtro de subida.

Ordenada por **edição e número de coleção** (pedido dele), que é a ordem do
binder e das páginas de venda — não pelo preço.

Medido a 2026-09-08, **depois de os tokens saírem do master set**: **686
impressões, 1411 cópias, 29 440,08 €**, uma sem oferta no CardTrader (entra na
lista, não entra no total). Por edição: OGN 252, VEN 170, SFD 145, UNL 105,
OGS 14. (Antes dessa decisão eram 695 / 1420 / 29 441,06 €, com UNL 113 e
VEN 171 — a diferença são os 10 tokens.)

**E depois de os showcases saírem das listas de compra**, no mesmo dia: **647
impressões, 1337 cópias, 21 056,34 €**, nenhuma sem oferta no CardTrader. Por
edição: OGN 241, VEN 170, SFD 117, UNL 105, OGS 14 — só o OGN e o SFD mexem,
que são as duas edições com raridade `showcase`.

**Sem imagens de propósito.** São centenas de linhas e o `faltas.json` é
descarregado inteiro a cada visita. Mesmo assim o ficheiro passou de **89 KB
para 296 KB** — é o custo desta aba, medido. Duas podas já feitas: sem
`set_name` por item (a edição já vem no grupo) e o `market_name` só quando
difere mesmo do nosso (poupou 18 KB). Se voltar a incomodar, o sítio para
podar é este — a seguir sairiam o `have`/`target` e o `printing_id`.

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

O formato vive no `cardmarket.linha` desde 2026-09-08 — o `faltas.wantlist()`
escreve por lá, e o `_versoes` mudou-se para `cardmarket.versoes`. Botão na
secção Faltas → Por deck, e `riftvault wantlist [--deck X] [--todos]
[--out f.txt]`. As abas "A subir" e "Master set" têm listas próprias, do mesmo
gerador (ver a secção acima).

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
- Confirma-se pela interface: botão **Chegou** em cada carta e um "Chegou
  tudo", em Faltas -> A caminho (`POST /api/pending/arrive`). Ou
  `riftvault pending --chegou [ID]`.

**Desfazer uma entrada tem DUAS metades.** O `collection.undo_last` reverte as
cópias mas não mexe no `pending.arrived_at` — é preciso pôr a NULL também,
senão a carta desaparece das duas listas. Não há undo automático disto.

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

## Filtro de estado: só "Faltas"

Havia `Em falta` (zero cópias) e `Parciais` (tem algumas, não as suficientes).
**Juntaram-se num só** (André, 2026-09-05): a pergunta é sempre a mesma — o
que é que ainda me falta — e tanto faz faltarem 3, 2 ou 1. `Faltas` é
`tileState() !== 'done'`.

O `loadPrefs` converte um `'partial'` guardado em `'missing'`: sem isso a
grelha abria sem botão nenhum selecionado, num filtro que já não existe.

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
- **Feito também:** as abas "A subir" e "Master set", com as listas para o
  Cardmarket (copiar, copiar com código, CSV) e o `riftvault a-subir`.
- **Feito também:** a Coleção em blocos (master set primeiro, `-T` e `a`
  depois), com uma só `metrics.e_master`, e a secção "Venda" com o
  `riftvault venda`.
- **Por fazer:** vista "todos os decks ao mesmo tempo" (hoje vê-se deck a deck,
  com as partilhadas assinaladas); e apagar decks pela interface (hoje apaga-se
  o `.txt`).

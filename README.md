# riftvault

Gestor da minha coleção de **Riftbound**. Objetivo: ter playsets, incluindo as
artes normais **e** as alternativas.

Duas secções: **Coleção** e **Decks**. O catálogo vem da API pública da
[RiftScribe](https://riftscribe.gg) e os preços do
[CardTrader](https://www.cardtrader.com).

---

## Instalar

Precisa de Python 3.11+ e de dois pacotes:

```bash
py -m pip install flask requests qrcode
```

(`qrcode` é opcional — só serve para mostrar o QR ao arrancar o servidor.)

## Primeira utilização

```bash
py -m riftvault sync --images
```

Descarrega as 5 edições (1180 impressões) e o cache das imagens (~70 MB).
Demora uns minutos: há uma pausa de 1 segundo entre pedidos, por educação para
com a API. Para só uma edição:

```bash
py -m riftvault sync --set OGN --images
```

## Modo edição (o do dia a dia)

```bash
py -m riftvault serve
```

Levanta o site em `0.0.0.0:8770` e mostra o URL da rede local com um QR. Aponta
o telemóvel ao QR e ficas com a coleção na mão enquanto mexes nas cartas.
Tudo o que carregares nos `+` e `−` é escrito no `data/vault.db`.

No Windows há o atalho `riftvault.cmd`, por isso dá para escrever só
`riftvault serve`.

### Chegar ao servidor de fora de casa

**O riftvault não tem autenticação.** Quem chegar ao URL pode escrever na
coleção. Em casa não faz diferença; exposto à internet faz toda.

Por isso: **não abras o porto no router**, e não uses ngrok nem tunnels
públicos sem autenticação por cima. Usa uma rede privada:

1. Instala o [Tailscale](https://tailscale.com/download) no PC e no telemóvel
2. Entra com a mesma conta nos dois
3. O `riftvault serve` passa a mostrar-te o endereço `100.x.y.z` e o QR

Funciona em qualquer rede e nada fica exposto. O PC tem de estar ligado com o
servidor a correr.

Se lá fora só quiseres **consultar**, o modo publicado (GitHub Pages) chega e
não precisa do PC ligado.

## Modo publicado (só leitura)

```bash
py -m riftvault build
```

Gera `site/` — o **mesmo** frontend, sem os controlos de edição. É o que o
GitHub Actions publica no GitHub Pages (`.github/workflows/pages.yml`).

---

## Ordenar e filtrar a grelha

- **Ordem:** primeiro a **sequência do master set**, por número de coleção, com
  as signatures logo a seguir à carta base. Depois, em blocos próprios no fim,
  o que está **fora do master set**: os tokens (código `-T`) e as artes
  alternativas (número acabado em `a`). Nunca intercalados. Cada bloco tem o
  seu contador — "tens N de M" — que **não** entra na percentagem de master set.
- **Filtros:** Tudo / Faltas, e por tipo de impressão (Base, Arte alt.,
  Signature, Tokens/Promos). "Faltas" mostra tudo o que não está completo,
  tanto faz faltarem 3, 2 ou 1.
- **Procura** por nome ou código.

As escolhas ficam guardadas no browser.

## Faltas

Terceira secção, com seis abas:

- **Staples** — cartas que **mais do que um deck** pede e que não tens em
  número suficiente. São as que rendem mais por euro: uma compra serve vários
  decks. Cada tile diz quantos decks a querem e quais.
- **Por deck** — o que falta a cada deck, agrupado por edição.
- **Pimp decks** — as versões **alteradas** das cartas que os teus decks usam:
  artes alternativas e showcase. Sem signatures e sem as runas promo do VEN
  — nas runas o que se pimpa é a arte alternativa. Dá para vetar impressões
  à peça em `pimp_ignorar_impressoes` (as sobrenumeradas caras); a carta
  continua lá pelas outras versões. Muda-se em
  `pimp_ignorar_tipos`. Mostra só **o que falta comprar**: desconta o que já tens e o que vem a
  caminho. Nas runas mostra a versão da **edição do Legend do deck**. Algumas dessas
  impressões (as runas do SFD, UNL e VEN) a RiftScribe ainda não tem; vêm do
  CardTrader e aparecem marcadas **"fora do catálogo"** — não contam para as
  métricas da Coleção, só servem para comprar.

  Arrumado **por deck**, nunca por edição: a vista **Todas** tem uma
  secção por deck, e há sub-abas para veres um de cada vez com a quantidade
  que esse deck usa. Cada sub-aba tem a sua lista para a wantlist.
- **Master set** — a lista **completa** do que falta à coleção, não só o que
  está a subir: para comprares tudo de uma vez se te apetecer. Mesmo âmbito e
  mesma regra da aba anterior (conta enquanto *cópias + a caminho < alvo*), sem
  o filtro de subida e sem as signatures nem os showcases. Por **edição e
  número de coleção**,
  que é a ordem do binder. Filtro por edição, e os mesmos três botões de lista
  para o Cardmarket.
- **A caminho** — o que já compraste e ainda não chegou. Não conta na Coleção
  (essa mede o que tens na caixa) mas já sai das faltas e das wantlists, para
  não comprares duas vezes. Quando chegar, carrega em **Chegou** na carta (ou em "Chegou tudo") e ela
  passa para a Coleção. Também dá pela linha de comandos:
  `py -m riftvault pending --chegou [ID]`.
- **A subir** — do **master set**, só o que **ainda não tens** e subiu 10% ou
  mais nos últimos 30 dias. Assim que compras a carta ela sai daqui: isto é
  uma lista de vigia de compras, não um índice de mercado.

  Duas abas sobre a mesma lista: **por %** (o que está a disparar) e **por
  valor** (o que te vai custar caro se esperares). Cada linha leva a arte
  pequena, o nome, a edição e o número, a raridade, o preço de então, o de
  hoje, o Δ da janela e o Δ de 7 dias, com links para o CardTrader e para a
  RiftScribe. Há um filtro rápido por raridade.

  **As signatures e os showcases não entram** (`a_subir.excluir`, decisões tuas
  a 2026-09-08: *"estás a pôr uma carta signed — não quero"* e *"tira também os
  showcases"*). São dois critérios porque são duas coisas: a signature é uma
  **variante** (o `*` do código) e o showcase é uma **raridade** — as 42 que
  saem daqui são reimpressões com número de coleção normal, como a
  `SFD-232/221`. A nota por baixo do resumo diz quantas saíram por cada
  critério. Continuam todas a contar na percentagem de set completo da
  Coleção — o que muda é só esta página e as listas de compra que saem dela.

  No fim há os três botões das **listas para o Cardmarket** (ver abaixo).

  O histórico só grava quando o preço **muda**, por isso o preço "de há 30
  dias" é o que estava em vigor nessa data, mesmo que o registo seja mais
  antigo. Enquanto o `prices.db` não tiver 30 dias, a comparação é *desde* a
  data mais antiga que houver e a linha diz isso — nunca finge a janela toda.
  O GitHub Actions atualiza os preços sozinho todos os dias.

  A janela, o limiar e a regra de "ainda não tenho" mexem-se em `a_subir`, no
  `riftvault_config.json`. Há ainda uma coluna de **urgência**, desligada de
  propósito (`a_subir.urgencia: false`) — é uma proposta de fórmula à espera
  de veredito, não uma decisão.

**As runas não entram nas abas dos decks** (Staples, Por deck e as wantlists)
— são baratas e compram-se a granel, e a 12 por deck enchiam os staples.
Continuam a contar na secção Decks, na Coleção e na aba **A subir**, que mede
o master set e não os decks. O que fica de fora está em
`faltas_ignorar_tipos`, no config.

**Nunca se compra mais do que um playset da mesma carta.** Cinco decks a pedir
3 Defy não são 15 Defy — são 3, e trocam-se entre decks. O teto é o alvo de
playset: 3 nas Units/Spells/Gears, 12 nas Runas, 1 nos Legends e Battlefields.
Cada carta mostra o que os decks pedem ao todo e o teto que se aplicou.

A carência aqui é **global** — soma-se o que todos os decks pedem e desconta-se
o que tens. É diferente da alocação por prioridade da secção Decks, que
responde a outra pergunta: quem fica com o quê.

## Wantlist do Cardmarket

Há listas em três sítios, todas com o mesmo formato porque saem do mesmo
gerador (`riftvault/cardmarket.py`):

- **Coleção**, no fim de cada edição: **Wantlist Cardmarket — <edição>**, com
  as faltas dessa edição já escritas na caixa, e a seguir **Wantlist — tudo**
  com as cinco edições seguidas. O cabeçalho da edição diz *faltam N cópias ·
  X €* e leva-te ao bloco.
- **Faltas → A subir** e **Faltas → Master set**, com três botões:
  **Copiar para o Cardmarket**, **Copiar com código** e **Descarregar CSV**.
- **Faltas → Por deck** e **Pimp decks**, com o botão de sempre.

As wantlists da Coleção são a **mesma lista** da aba *Master set*, cortada por
edição: os mesmos alvos dos três blocos (playset na sequência, 1 por runa, 1 por
runa especial, 1 por arte alternativa), a mesma regra *cópias + a caminho <
alvo* e as mesmas exclusões (signatures e showcases). Em modo edição, um `+` ou
um `−` marca-as como desatualizadas e aparece um botão **Atualizar** — não se
volta a pedir o ficheiro sozinho.

As listas saem sempre do que está **no ecrã** — respeitam a aba, a edição e a
raridade que tiveres escolhidas. A quantidade de cada linha é o que **falta
comprar**: alvo menos o que tens menos o que vem a caminho.

Pela linha de comandos:

```bash
py -m riftvault a-subir                     # a tabela do que está a subir
py -m riftvault a-subir --cardmarket        # as linhas para colar
py -m riftvault a-subir --cardmarket --codigos
py -m riftvault a-subir --todas             # tudo o que falta do master set
py -m riftvault a-subir --todas --csv faltas.csv

py -m riftvault wantlist --edicao OGN       # as faltas do master set do OGN
py -m riftvault wantlist --cardmarket       # as cinco edições seguidas
py -m riftvault wantlist --edicao unl --codigos

py -m riftvault wantlist                    # tudo, um deck de cada vez
py -m riftvault wantlist --deck ornn        # só um deck
py -m riftvault wantlist --todos            # todos montados ao mesmo tempo
py -m riftvault wantlist --out faltas.txt
```

O `wantlist` responde a duas perguntas diferentes com o mesmo formato: sem
`--edicao`/`--cardmarket` é o que falta aos **decks**; com um deles é o que
falta ao **master set** de cada edição — o mesmo que a Coleção mostra no fim.
O corte por edição e os totais saem no `stderr`, para o `stdout` ficar colável
tal e qual.

O formato é `3 Nome da Carta (V.n) (Edição)`, com o nome **como o mercado o
escreve** — `Darius - Trifarian`, não `Darius, Trifarian` como está na
RiftScribe. Sem isso o Cardmarket não casa as cartas.

O **Copiar com código** dá `3 Nome da Carta [UNL-228]`. Os `[ ]` **não** são
sintaxe do Cardmarket: é para desambiguares à mão qual das versões queres,
quando o nome sozinho não chega. Para colar, usa o primeiro botão.

O **CSV** leva cabeçalho e oito colunas — quantidade, nome, código, edição,
raridade, preço de hoje, Δ % e custo. Na lista do master set a coluna do Δ vem
vazia: essa lista não é sobre preço a subir.

**O total em euros aparece por baixo da caixa, não dentro dela** — uma linha de
total colada na wantlist era importada como se fosse uma carta.

A lista dos decks leva sempre a **versão mais barata** de cada carta. As
versões bonitas vivem na aba **Pimp decks**, que tem lista própria.

**O foil não se pode marcar no texto.** No Cardmarket o foil é um filtro por
entrada, posto na interface depois de a carta entrar na lista. Por isso, por
baixo do texto aparece a lista das cartas que **só têm oferta foil** no
mercado — são essas em que tens de ligar o filtro *Foil* à mão.

Os números de versão são **inferidos** pela ordem do número de coleção, não
lidos do Cardmarket. Se saírem trocados, diz e corrijo.

## As duas métricas

São mostradas sempre lado a lado, nunca uma em vez da outra.

**1. Playset jogável** — alvo por *carta lógica* (o nome). Qualquer impressão,
de qualquer edição, conta. Alvos por tipo, em `riftvault_config.json`:
Unit/Spell/Gear 3, Battlefield 1, Legend 1, Rune 12, tokens 1.

**2. Master set** — alvo por *impressão*. A base segue o alvo de jogo e cada
signature 1.

**O master set é a sequência numerada da edição.** Ficam de fora as impressões
com sufixo no código: os tokens (`UNL-T03`) e as artes alternativas
(`UNL-228a`). Não entram na percentagem, e na grelha aparecem em blocos
próprios depois da sequência. As signatures (`OGN-299*`), as runas promo
(`VEN-R01`) e as promos especiais (`VEN-SP4`) **continuam dentro**.

**As artes alternativas pedem playset na mesma** — um alt art de Unit mostra
`0/3`, um de Rune mostra `0/12` — porque o alvo e a percentagem são perguntas
diferentes. São três ajustes: `master_targets_by_variant` é o alvo fixo,
`master_variantes_playset` diz quais as variantes que seguem o playset em vez
desse alvo fixo, e `master_set.fora` é o que fica fora do master set.

### O que fica fora: `master_set.fora`

A lista escreve-se pelos **sufixos do código impresso**, no
`riftvault_config.json`:

```json
"master_set": { "fora": ["-T", "a"] }
```

| escreves | tira | exemplo |
|---|---|---|
| `-T` | tokens | `UNL-T03` |
| `a` | artes alternativas | `UNL-228a` |
| `*` | signatures | `OGN-299*` |
| `-R` | runas promo | `VEN-R01` |
| `-SP` | promos especiais | `VEN-SP4` |

Também aceita os nomes das variantes (`token`, `alt_art`, `signature`,
`rune_promo`, `special`, `base`) — dá o mesmo. Um valor que não seja nenhum
destes **dá erro**, de propósito: se uma edição nova trouxer um sufixo que o
riftvault não conhece, é melhor rebentar do que contá-lo em silêncio.

**Para tirar as signatures da sequência** basta acrescentar `"*"`:

```json
"master_set": { "fora": ["-T", "a", "*"] }
```

Ficam num bloco próprio no fim da grelha, como os tokens. **Atenção:** isso
tira-as *também* do denominador da percentagem (1068 → 1032 impressões) —
sair da sequência e sair da conta são a mesma pergunta. Hoje está **desligado**,
à espera de decisão: elas continuam a contar para o set estar completo. Nas
*listas de compra* já não aparecem desde 2026-09-08, mas isso é outro ajuste
(`a_subir.excluir`).

O nome antigo desta lista era `master_ignorar_variantes`; um config que ainda
o traga continua a funcionar.

Não se distingue foil de normal: uma cópia é uma cópia.

## Venda

Quarta secção. O que tens **fora do master set** — os `-T` e os `a` — partido em
duas leituras:

- **usada num deck seleccionado** — a cópia está alocada a um deck da secção
  Decks. Fica onde está e não entra na lista.
- **candidata a venda** — nenhum deck a usa. Nome, código, quantidade, preço de
  hoje e total, mais o botão para copiar a lista no formato do Cardmarket.

Uma impressão pode estar nas duas: 2 cópias num deck e 1 a mais vende só 1.

**Nada sai da base.** É uma sugestão — não há botão de vender e a coleção não
mexe. As impressões do master set nunca entram aqui, por muitas que tenhas a
mais.

```bash
py -m riftvault venda                # a tabela
py -m riftvault venda --cardmarket   # as linhas para copiar
py -m riftvault venda --csv venda.csv
```

## Valor da coleção

Preços do [CardTrader](https://www.cardtrader.com). Precisas de um token da
API, criado nas definições do perfil deles:

```bash
setx CARDTRADER_TOKEN "o-teu-token"
```

Depois (abre um terminal novo primeiro):

```bash
py -m riftvault map      # liga as impressões aos blueprints (uma vez)
py -m riftvault prices   # descarrega os preços (~225 MB, 5 pedidos)
py -m riftvault value    # mostra o valor
```

O preço de cada impressão é o **mais baixo em Near Mint/Mint, inglês**, sem
cartas graded, alteradas ou assinadas. Prefere-se a oferta não foil.

As cartas de **1 € para cima** mostram o preço por cima da própria carta; as
mais baratas só na linha de baixo do tile. O limiar é o
`price_badge_min_cents` no `riftvault_config.json`.

**Cuidado com o total:** muitas cartas de Riftbound só têm oferta em foil no
CardTrader. Como o riftvault não distingue acabamentos, essas podem estar
sobreavaliadas — o `riftvault value` diz-te que percentagem do total vem daí.

## Decks

As listas ficam em `decks/*.txt`. Cada uma dá um separador, com o nome
**Legend · Champion**.

Os decks têm uma **ordem**, e é ela que manda: o deck 1 fica com as cartas de
que precisa, o deck 2 só recebe o que sobrou. Quando falta uma carta ao deck 2
porque o deck 1 a levou, o site diz **em que deck está** em vez de a mandar
para a lista de compras. Mudar a ordem refaz a alocação toda.

Para reordenar, usa os botões **Tornar principal / Subir / Descer** no site,
ou:

```bash
py -m riftvault decks --order azir,ornn   # o primeiro passa a principal
py -m riftvault deck azir --onde          # detalhe, com as impressões a usar
py -m riftvault shopping --deck azir --csv faltas.csv
```

Para **apagar** um deck, apaga o `.txt` — o site atualiza-se sozinho.

Cada deck é uma grelha de cartas, como a Coleção. A moldura diz o estado:
verde tens, vermelho falta, âmbar está noutro deck. O canto mostra quantas o
deck pede, e o badge quantas lhe estão alocadas.

Ao contrário, na **Coleção** cada carta que saiu para um deck diz para qual —
para quando a procuras no binder e ela não lá está. Quando só parte saiu, diz
quantas ficaram (`2× Ornn, Fire Below the Mountain · 1 no binder`). As cópias
que vão para os decks são as **artes base primeiro**, para as alternativas e
signatures ficarem no binder.

O cabeçalho valida main 40 (o Champion conta), 12 runas, 3 battlefields,
máximo 3 cópias e a identidade de domínio do Legend, e mostra **quantas cópias
faltam por edição** com o custo estimado. Cada carta em falta conta na edição
onde sai mais barata — é onde a irias comprar. As que existem em mais do que
uma edição estão assinaladas no tooltip, para o número não parecer mais firme
do que é. Cartas que faltam por estarem noutro deck não entram nessa conta:
essas não se compram.

A seguir ao deck vem **"Em falta, por edição"**: as mesmas cartas em falta, mas
arrumadas por edição e ordenadas pelo que custam — é a vista de quem vai
comprar, não de quem vai montar. Cada carta mostra a impressão dessa edição, o
que faltam e o custo, e diz se também existe noutra edição. Essas regras estão em
`deck_rules` no `riftvault_config.json`.

## Linha de comandos

```bash
riftvault sync [--set OGN] [--images] [--fast]   # catálogo
riftvault images [--set OGN]                     # só as imagens em falta
riftvault serve [--port 8770]                    # modo edição
riftvault build [--out site]                     # modo publicado
riftvault add OGN-100a x1                        # somar cópias
riftvault remove OGN-100a x1                     # tirar cópias
riftvault set OGN-100a 3                         # fixar a quantidade
riftvault undo                                   # desfazer a última operação
riftvault log -n 20                              # histórico
riftvault stats                                  # resumo por edição
riftvault find "sett"                            # procurar impressões
riftvault decks [--order azir,ornn]               # decks e alocação
riftvault deck azir [--onde]                      # detalhe de um deck
riftvault shopping [--deck azir] [--csv f.csv]    # o que falta comprar
riftvault a-subir [--cardmarket] [--todas]        # master set: a subir / tudo
riftvault venda [--cardmarket] [--csv f.csv]      # fora do master set, a sobrar
riftvault map / prices / value                    # CardTrader
```

O `add`/`remove` aceitam qualquer forma de escrever a impressão: `OGN-7`,
`OGN-007`, `OGN-007a`, `ogn-007a-298`, `OGN-299*`, `OGN-299-star`, `UNL-T03`.

## Ficheiros

```
riftvault/
  riftscribe.py   cliente da API
  catalog.py      constrói o catalog.db (impressões + cartas lógicas + aliases)
  collection.py   escrita na coleção, log e undo
  metrics.py      as duas métricas, os blocos da grelha e os payloads
  a_subir.py      o que falta do master set (a subir, e a lista completa)
  venda.py        o que está fora do master set e sobra dos decks
  server.py       modo edição (Flask)
  build.py        modo publicado (estático)
  cli.py          linha de comandos
  web/            index.html + app.js + style.css — o MESMO nos dois modos
data/
  vault.db        a coleção e os decks. VAI para o Git. Só tu escreves.
  prices.db       histórico de preços. VAI para o Git. Só o robô escreve.
  catalog.db      cache do catálogo. NÃO vai (está no .gitignore).
  images/         cache das imagens. NÃO vai.
decks/            listas de deck em .txt
docs/             spec da API e snapshot do catálogo, para referência
```

O contexto todo — incluindo as armadilhas da API e o que ainda não foi
validado — está no [CLAUDE.md](CLAUDE.md).

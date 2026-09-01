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

- **Ordem:** número de coleção, com as artes alternativas e signatures logo a
  seguir à carta base.
- **Filtros:** Tudo / Em falta / Parciais, e por tipo de impressão
  (Base, Arte alt., Signature, Tokens/Promos).
- **Procura** por nome ou código.

As escolhas ficam guardadas no browser.

## Faltas

Terceira secção, com três abas:

- **Staples** — cartas que **mais do que um deck** pede e que não tens em
  número suficiente. São as que rendem mais por euro: uma compra serve vários
  decks. Cada tile diz quantos decks a querem e quais.
- **Por deck** — o que falta a cada deck, agrupado por edição.
- **Pimp decks** — as versões **alteradas** das cartas que os teus decks usam:
  artes alternativas e showcase. Sem signatures e sem as runas promo do VEN
  — nas runas o que se pimpa é a arte alternativa. Muda-se em
  `pimp_ignorar_tipos`. Nas runas mostra a versão da **edição do Legend do deck**. Algumas dessas
  impressões (as runas do SFD, UNL e VEN) a RiftScribe ainda não tem; vêm do
  CardTrader e aparecem marcadas **"fora do catálogo"** — não contam para as
  métricas da Coleção, só servem para comprar.

  Arrumado **por deck**, nunca por edição: a vista **Todas** tem uma
  secção por deck, e há sub-abas para veres um de cada vez com a quantidade
  que esse deck usa. Cada sub-aba tem a sua lista para a wantlist. Não é lista de
  compras; inclui as que já tens (moldura verde), porque serve para saberes o
  que existe quando andas a procurar. Tem lista para a wantlist também.
- **A caminho** — o que já compraste e ainda não chegou. Não conta na Coleção
  (essa mede o que tens na caixa) mas já sai das faltas e das wantlists, para
  não comprares duas vezes. Quando chegar:
  `py -m riftvault pending --chegou`.
- **A subir** — **todo o Riftbound**, não só a tua coleção: impressões que
  subiram mais de 15% nos últimos 30 dias. As que já tens ficam com moldura
  verde, as que te faltam com moldura vermelha e o que custou esperar. Serve
  para apanhar cartas a valorizar antes de entrarem num deck teu. O GitHub
  Actions atualiza os preços sozinho todos os dias.

**As runas não entram nesta secção** — são baratas e compram-se a granel, e a
12 por deck enchiam os staples. Continuam a contar na secção Decks e na
Coleção. O que fica de fora está em `faltas_ignorar_tipos`, no config.

**Nunca se compra mais do que um playset da mesma carta.** Cinco decks a pedir
3 Defy não são 15 Defy — são 3, e trocam-se entre decks. O teto é o alvo de
playset: 3 nas Units/Spells/Gears, 12 nas Runas, 1 nos Legends e Battlefields.
Cada carta mostra o que os decks pedem ao todo e o teto que se aplicou.

A carência aqui é **global** — soma-se o que todos os decks pedem e desconta-se
o que tens. É diferente da alocação por prioridade da secção Decks, que
responde a outra pergunta: quem fica com o quê.

## Wantlist do Cardmarket

Na secção Faltas → Por deck há um botão **Lista para a wantlist do
Cardmarket**, que dá o texto da aba que estiveres a ver. Ou pela linha de
comandos:

```bash
py -m riftvault wantlist                    # tudo, um deck de cada vez
py -m riftvault wantlist --deck ornn        # só um deck
py -m riftvault wantlist --todos            # todos montados ao mesmo tempo
py -m riftvault wantlist --out faltas.txt
```

O formato é `3 Nome da Carta (Edição)`, com o nome **como o mercado o
escreve** — `Darius - Trifarian`, não `Darius, Trifarian` como está na
RiftScribe. Sem isso o Cardmarket não casa as cartas.

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

**2. Master set** — alvo por *impressão*. A base segue o alvo de jogo, cada
arte alternativa 1, cada signature 1. Configurável, incluindo por impressão.

Não se distingue foil de normal: uma cópia é uma cópia.

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
  metrics.py      as duas métricas e os payloads do frontend
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

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

- **Ordem:** três blocos seguidos, nunca intercalados. Primeiro a **sequência
  do master set**, por número de coleção; depois **as runas especiais, 1 de
  cada**; depois **as artes alternativas, 1 de cada**. Os três contam para a
  percentagem. Só no fim vem o que está **fora da coleção** — os tokens (código
  `-T`), as signatures (código `*`), as **sobrenumeradas** (as «300/298») e as
  **promos** (`VEN-SP4`) —, cada um com o seu contador "tens N de M" e a dizer
  que **não** entra na percentagem.
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
  o filtro de subida. As signatures e os showcases já nem chegam a esta lista:
  saíram todos da coleção (as signatures a 09-09, as sobrenumeradas a 10-09) e
  os filtros de compra ficaram sem nada para tirar. Por **edição e número de
  coleção**,
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

  **Os showcases não entram** (`a_subir.excluir`, decisão tua a 2026-09-08:
  *"tira também os showcases"*). O showcase é uma **raridade**, não uma
  variante: as 42 que saem daqui são reimpressões com número de coleção normal,
  como a `SFD-232/221`, e continuam a contar na percentagem de set completo — o
  que muda é só esta página e as listas de compra que saem dela. A nota por
  baixo do resumo diz quantas saíram e por que critério.

  **As signatures também não**, mas por outro motivo desde 2026-09-09: saíram da
  Coleção inteira, que é o âmbito desta página, por isso já nem chegam à
  exclusão (o resumo passou de «78 impressões (36 signature + 42 showcase)» a
  «42 (42 showcase)»). A exclusão delas fica no config na mesma, para o caso de
  voltarem.

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
  com as cinco edições seguidas. O cabeçalho da edição diz *N cópias a comprar
  nesta edição · X €* e leva-te ao bloco.
- **Faltas → A subir** e **Faltas → Master set**, com três botões:
  **Copiar para o Cardmarket**, **Copiar com código** e **Descarregar CSV**.
- **Faltas → Por deck** e **Pimp decks**, com o botão de sempre.

As wantlists da Coleção são a **mesma lista** da aba *Master set*, cortada por
edição: os mesmos alvos dos três blocos (playset na sequência, 1 por runa, 1 por
runa especial, 1 por arte alternativa), a mesma regra *cópias + a caminho <
alvo* e a mesma exclusão dos showcases. Em modo edição, um `+` ou
um `−` marca-as como desatualizadas e aparece um botão **Atualizar** — não se
volta a pedir o ficheiro sozinho.

Os dois blocos partilham um **degrau**: *até 1 de cada · até 2 de cada ·
playset*. É a mesma lista com `min(k, alvo)` no lugar do alvo, e o que ela pede
são exatamente as cópias que os chips da contagem por níveis dizem que faltam.

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
py -m riftvault wantlist --cardmarket --nivel 1   # só uma de cada

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

**2. Master set** — alvo por *impressão*, e a **Coleção são três blocos**
(decisões tuas de 2026-09-08):

| bloco | o que é | alvo por impressão |
|---|---|---|
| 1 | a sequência do master set, por número de coleção | o **playset do tipo** (Unit/Spell/Gear 3, Legend e Battlefield 1) — **menos as runas, que são 1** |
| 2 | as runas especiais (a runa que não é a base), por edição | **1** |
| 3 | as artes alternativas | **1** |

Os três contam para a percentagem: hoje são **1036 impressões** no denominador.
As runas promo (`VEN-R01`) estão no bloco 2, com as outras runas especiais.
Fica de fora o que o `master_set.fora` disser — hoje os tokens (`UNL-T03`), as
**signatures** (`OGN-299*`, decisão tua de 2026-09-09: *"das coleções tira as
signatures, fazemos 1 Alt Art de cada mas as signature não"*), as
**sobrenumeradas** (`SFD-244/221`, decisão tua de 2026-09-10: *"também não quero
para a coleção as overnumbered"*) e as **promos** (`VEN-SP4`, do mesmo dia:
*"quero que as promos fiquem também à parte, tal como as signature e as
overnumbered"*), que aparecem em blocos informativos no fim da grelha, com alvo
1 mas sem entrar na conta.

**O playset jogável da runa continua 12**: colecionar e jogar são perguntas
diferentes, e são as 12 que enchem o Rune Pool de um deck.

Os ajustes: `master_targets_by_variant` é o alvo fixo por variante,
`runas_especiais` é a regra das runas (o que é runa, que alvo tem, e quais
ficam na sequência), `master_variantes_playset` diz quais as variantes que
seguem o playset em vez do alvo fixo (está **vazio**), e `master_set.fora` é o
que fica fora da coleção.

### Contagem por níveis: 1 de cada, 2 de cada, o playset

Por baixo das barras, uma linha de chips para a edição aberta e outra para as
cinco: `1/3 · 64 % · faltam 420 · …`, `2/3 · …`, `playset (3/3) · …`. O alvo do
nível *k* é `min(k, alvo)`, por isso as impressões de alvo 1 só podem faltar no
primeiro degrau — e a percentagem do **último** degrau é exatamente a da barra
do master set.

Conta **cópias**, não o que vem a caminho (é a regra da Coleção), e conta tudo
o que está no denominador — que desde 2026-09-10 já não tem signatures, nem
sobrenumeradas, nem promos. As wantlists do fim da página é que descontam o pendente — ali a
pergunta é o que há a **comprar** —, e é só por isso que os dois números ainda
não são iguais.

Na linha de comandos, `riftvault stats` imprime a tabela por edição.

### O que fica fora: `master_set.fora`

A lista escreve-se pelos **sufixos do código impresso**, no
`riftvault_config.json`:

```json
"master_set": { "fora": ["-T", "*", "overnumbered", "promo"] }
```

| escreves | tira | exemplo |
|---|---|---|
| `-T` | tokens | `UNL-T03` |
| `a` | artes alternativas | `UNL-228a` |
| `*` | signatures | `OGN-299*` |
| `-R` | runas promo | `VEN-R01` |
| `-SP` ou `promo` | promos | `VEN-SP4` |
| `overnumbered` | as sobrenumeradas | `SFD-244/221` |

Também aceita os nomes das variantes (`token`, `alt_art`, `signature`,
`rune_promo`, `special`, `base`) — dá o mesmo. Um valor que não seja nenhum
destes **dá erro**, de propósito: se uma edição nova trouxer um sufixo que o
riftvault não conhece, é melhor rebentar do que contá-lo em silêncio.

`overnumbered` é a única entrada que **não** é uma variante: é o número que
passa o tamanho da edição, e o tamanho lê-se no denominador do próprio código
impresso (`SFD-244/**221**`), não num número escrito à mão.

**As signatures saíram a 2026-09-09** (*"das coleções tira as signatures,
fazemos 1 Alt Art de cada mas as signature não"*): é o `"*"` da lista. Ficam num
bloco próprio no fim da grelha, como os tokens — com alvo 1, para veres as que
tens —, e saem do denominador da percentagem (1170 → **1134** impressões), das
contagens por níveis e das wantlists. Sair da sequência e sair da conta são a
mesma pergunta, respondida uma vez só. Para as pôr de volta tira-se o `"*"`.
Nas *listas de compra* já não apareciam desde 2026-09-08, por outro ajuste
(`a_subir.excluir`), que fica de pé: se um dia voltarem à coleção, continuam a
não ser para comprar.

**As sobrenumeradas saíram a 2026-09-10** (*"também não quero para a coleção as
overnumbered"*): são as **92** impressões cujo número passa o tamanho da edição
e que ainda contavam — OGN 12, SFD 30, UNL 19, VEN 31; o OGS não tem nenhuma.
São as reimpressões de topo de set da ARMADILHA 2 (a mesma carta a reaparecer na
mesma edição com número próprio). As 36 signatures também são sobrenumeradas,
mas já tinham saído no dia anterior e ficam no bloco delas. **Nenhuma arte
alternativa é sobrenumerada** — elas partilham o número da base —, por isso o
«1 alt art de cada» fica intacto. O denominador passou de 1134 para **1042** e
as cinco que tens continuam visíveis no bloco «Fora da coleção —
sobrenumeradas», com alvo 1.

**As promos saíram no mesmo dia** (*"deparei-me com as VEN-SP (promos). Quero
que as promos fiquem também à parte, tal como as signature e as overnumbered"*):
escreve-se `"promo"` na lista, e são as **6** `VEN-SP1..SP6` — as únicas do
catálogo inteiro, todas no Vendetta. Precisavam de entrada própria porque
**nenhuma delas é sobrenumerada**: o `VEN-SP4/006` é a 4 de uma série de 6, e o
critério de ontem lê o código como ele está escrito. O denominador passou de 1042
para **1036** (VEN 196 → 190) e a que tens (`VEN-SP5` Ezreal, Prodigy) continua
visível no bloco «Fora da coleção — promos», com alvo 1.

**As runas promo do VEN (`VEN-R01..R06`) NÃO saíram com elas.** São outra
categoria (`rune_promo`) e são elas que enchem o bloco «1 runa especial de cada»
no Vendetta — a tua decisão de 2026-09-08. Se as quiseres fora também, é
acrescentar `"-R"` à lista.

O nome antigo desta lista era `master_ignorar_variantes`; um config que ainda
o traga continua a funcionar.

Não se distingue foil de normal: uma cópia é uma cópia.

## Venda

Quarta secção. O que tens **fora da sequência do master set** — os tokens
(`-T`), as signatures (`*`), as sobrenumeradas, as promos (`VEN-SP`), as runas
especiais e as artes alternativas —, partido em duas leituras:

- **usada num deck seleccionado** — a cópia está alocada a um deck da secção
  Decks. Fica onde está e não entra na lista.
- **candidata a venda** — nenhum deck a usa. Nome, código, quantidade, preço de
  hoje e total, mais o botão para copiar a lista no formato do Cardmarket.

Uma impressão pode estar nas duas: 2 cópias num deck e 1 a mais vende só 1.

**É só o EXCEDENTE.** Nos blocos que contam para a coleção — as runas especiais
e as artes alternativas — guarda-se **1 de cada**, que é o que a coleção pede, e
só sobra o resto; a primeira arte alternativa é coleção, a sexta é venda. Os
tokens e as signatures, que estão fora da coleção, sobram inteiros.

**Sobre as signatures:** desde que saíram da coleção (2026-09-09), uma signature
que tenhas e nenhum deck use aparece aqui como candidata — é a regra de sempre,
aplicada ao bloco novo. Hoje não tens nenhuma na caixa, por isso a lista não
mexeu; **diz se preferes que fiquem sempre de fora da venda.**

**E sobre as sobrenumeradas, o mesmo — só que desta vez tem efeito.** Com a
decisão de 2026-09-10 entraram na Venda as **5** que tens e nenhum deck usa:
`OGN-303` Nine-Tailed Fox, `SFD-224` Aphelios, `SFD-244` Fire Below the
Mountain, `UNL-231` Wuju Master e `UNL-235` Deceiver — **654 €**, e a caixa
passou de 4,11 € para 658,06 €. Não vendi nada nem mexi na coleção: é uma
sugestão. **Diz se as queres aí ou se preferes guardá-las.**

**E com as promos, outra vez o mesmo:** a `VEN-SP5` Ezreal, Prodigy que tens
(**18,87 €**) passou a candidata a venda. É a mesma pergunta das duas de cima.

**Duas origens desde 2026-09-10, e cada linha diz a sua:**

- **do binder Decks/Venda** — cópias que tiraste da Coleção e que **nenhum deck
  pede**. Entram seja qual for o bloco, incluindo a sequência do master set:
  foste tu que as tiraste da coleção.
- **da Coleção** — o que passa do alvo, como sempre. Aqui a sequência do master
  set continua a **não** entrar, por muitas que tenhas a mais (decisão de
  2026-09-08).

O que está **dentro** de um deck nunca aparece na lista — está sleevado e a
jogar.

**Nada sai da base.** É uma sugestão — não há botão de vender e a coleção não
mexe.

```bash
py -m riftvault venda                # a tabela
py -m riftvault venda --cardmarket   # as linhas para copiar
py -m riftvault venda --csv venda.csv
```

### Comuns e incomuns: o que vender

*"Vê no Cardmarket e CardTrader quais as comuns e incomuns que costumam
vender-se mais, e quais as mais caras, para eu saber o que vender."* É a secção
dobrada no fim da página Venda, e o `py -m riftvault venda --comuns`.

**A resposta curta: não tens nada para vender aí.** O teu excedente em comuns e
incomuns são **22 impressões, 33 cópias, 3,83 €** — vinte delas ao preço mínimo
do CardTrader (11 cêntimos) e metade são tokens do UNL. O dinheiro do que te
sobra está nas seis que já aparecem em cima na Venda (**675 € dos 695 €**), e
essas não são comuns.

**Não existe "quais se vendem mais".** Ninguém publica volume de vendas:
o Cardmarket responde **403** ao site e **410** à API pública, e a alternativa
era registar uma app com chave própria — que a regra de só usar a subscrição não
permite. Do CardTrader vem o lado da **oferta**: preço mínimo, quantos anúncios,
quantos vendedores e quantas cópias estão à venda. A coluna **procura** é o
preço a dividir pela mediana da raridade, reforçado pela subida do preço; mede
quanto o mercado pede **acima do saldo**, não quantas se venderam. Hoje as duas
medianas são as duas 11 cêntimos, por isso as duas listas saem quase iguais.

**A lista das caras é para NÃO venderes.** As seis comuns caras do Riftbound são
os Poros do UNL (`UNL-220` a `UNL-225`, de 100 a 286 €) — não tens nenhuma. A
sétima já é a `OGN-183` Stacked Deck a 4,91 €.

Passou também a guardar-se o número de anúncios ao longo do tempo
(`listings_history` no `prices.db`). Com um dia não diz nada; ao fim de umas
semanas, anúncios a cair com o preço a subir é o sinal mais próximo de procura
que dá para ter.

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
quantas ficaram (`3× Azir · 1 na Coleção`).

### Onde está cada cópia (2026-09-10)

Cada cópia tem **um local**, e só um:

| local | o que é | conta para |
|---|---|---|
| **Coleção** | os binders de coleção | a percentagem de master set, os níveis, as wantlists |
| **Deck `<slug>`** | sleevada dentro de um dos `decks/*.txt` | só esse deck |
| **Binder Decks/Venda** | o stock livre | qualquer deck, por prioridade; o que sobra é venda |

- **A Coleção só conta o que está na Coleção.** Uma cópia que esteja num deck
  deixa de contar para a barra, mesmo sendo a mesma impressão — a impressão
  volta a aparecer como falta.
- **Os decks nunca tiram da Coleção.** Uma carta que o deck pede e que está nos
  binders de coleção aparece como **«na Coleção — mover ou comprar»**: não é
  «tenho» nem é «a comprar», é decisão tua.
- **Desfazer um deck** manda tudo o que estava nele para o binder Decks/Venda,
  onde fica disponível para outro deck. Nada volta à Coleção sozinho.

**Por omissão está tudo na Coleção.** A marcação faz-se em dois passos, e o
segundo só grava o que confirmares:

```bash
py -m riftvault local                                   # onde está o quê
py -m riftvault local --deck azir --propor              # a proposta (não grava)
py -m riftvault local --deck azir --marcar "ogn-045-298:3,ogn-102-298:2"
py -m riftvault local OGN-100a 2 --para binder          # mover à mão
py -m riftvault local --desfazer-deck azir              # tudo para o binder
py -m riftvault local --undo                            # desfazer o último
```

No site, em modo edição, é o botão **«Marcar o que este deck usa…»** no
cabeçalho do deck: mostra a proposta com checkboxes e grava **só as marcadas**.
O «Marcar tudo» liga as caixas e mais nada.

Cada movimento deixa uma linha em **`data/locais.log`** (CSV: quando, cópia,
de → para, de onde veio o clique). Se uma cópia aparecer num deck sem linha
aí, é bug.

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
riftvault venda --comuns                          # comuns e incomuns: as caras
riftvault local [...]                             # onde está cada cópia
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
  locais.py       onde está cada cópia: Coleção, deck, binder Decks/Venda
  metrics.py      as duas métricas, os blocos da grelha e os payloads
  a_subir.py      o que falta do master set (a subir, e a lista completa)
  venda.py        o que está fora do master set e sobra dos decks
  comuns.py       comuns e incomuns: as mais caras e o que tens a mais
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

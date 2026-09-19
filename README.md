# riftvault

Gestor da minha coleção de **Riftbound**. Objetivo: ter playsets, incluindo as
artes normais **e** as alternativas.

Secções: **Coleção**, **Decks**, **Quanto custa**, **Faltas**, **A mais** e
**Encomendas**. O catálogo vem da API pública da
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

### O modo edição é só para casa

**O riftvault não tem autenticação.** Quem chegar ao URL pode escrever na
coleção. Em casa não faz diferença; exposto à internet faz toda.

Por isso: **não abras o porto no router**, e não uses ngrok nem tunnels
públicos sem autenticação por cima. O `riftvault serve` mostra só os
endereços da rede local; o da LAN nunca vai para o site publicado.

Se lá fora só quiseres **consultar**, o modo publicado (GitHub Pages) chega e
não precisa do PC ligado.

## Modo publicado (só leitura)

```bash
py -m riftvault build
```

Gera `site/` — o **mesmo** frontend, sem os controlos de edição.

**A pasta `site/` vai no Git, e é ela que o GitHub Pages publica** (desde
2026-09-10). O workflow `.github/workflows/pages.yml` não vai à rede: pega na
pasta commitada e publica-a, mais nada. Quem gera o site é o PC — as tarefas
`riftvault-publicar` (de 30 em 30 min) e `riftvault-daily` (07:30) do `ai-pc`.

Foi a RiftScribe que obrigou a isto: a 10/09/2026, das 11:55 às 17:45, todas as
builds morreram ao fim de 45 s a descarregar o catálogo (`riftscribe.gg/api` em
timeout, do Actions e do PC) e o site ficou parado na versão da manhã. O
catálogo completo já está no PC e a colecção também — o Pages não precisava de
rede nenhuma.

```bash
py -m riftvault build --se-mudou
```

Gera para uma pasta de prova e compara com o `site/` commitado **ignorando o
`generated_at`**: se o conteúdo é o mesmo, não escreve nada. É isto que impede
a tarefa de meia em meia hora de gastar uma build do Pages só porque o relógio
andou.

As **imagens continuam a vir do CDN** (`static_images: "remote"`): são ~88 MB e
não têm nada que fazer no Git. Se a RiftScribe estiver em baixo, a página abre
na mesma — só as imagens é que não aparecem.

---

## Ordenar e filtrar a grelha

- **Ordem:** blocos seguidos, nunca intercalados, pela ordem de 2026-09-19
  (*"coloca as OverNumbered a seguir ao master Set, depois as AltArt, depois
  as Promos"*): primeiro a **sequência do master set**, por número de
  coleção — a única que conta para a percentagem —; depois as
  **sobrenumeradas** (as «300/298», 1 de cada); depois **as artes
  alternativas, a playset**; depois as **promos** (`VEN-SP4`, a playset); e
  as runas especiais, se as houver (bloco **vazio** hoje — as artes
  alternativas das runas do OGN saíram de tudo a 2026-09-17). Cada bloco da
  coleção extra tem o seu contador e diz que **não** entra na percentagem:
  «tens N de M» (impressões de que tens pelo menos uma cópia) e, quando o
  bloco pede playset, «· K no playset completo» a seguir. Os tokens (`-T`), as
  signatures (`*`) e as runas promo (`VEN-R01`) não aparecem. A ordem
  escreve-se em `master_set.ordem_dos_blocos` no config.
- **Runas — 12 de cada:** o bloco que fecha a grelha, **o teu contador**
  (2026-09-19: *"mete 12 runas de cada — nao contabilizes para nada, e so para
  mim para contabilizar ali algumas coisas"*; e, à tarde, *"runas nao
  contabilizam nada, eu e que mexo nisso para minha referencia"*). As seis
  runas do jogo, cada uma com um número **que pões tu** com os `+`/`−` do
  tile (só no modo edição; nunca abaixo de 0), guardado numa tabela própria
  do `vault.db` e semeado uma única vez com o que tinhas na mão. Ao lado, em
  letra pequena, «na coleção: N» — **tudo o que tens dela, de todas as
  versões**: a base do OGN (que também está na sequência, em cima), a alt art
  retirada, a promo do VEN, as do CardTrader — só para comparares. Não conta
  para nada: nem barra, nem níveis, nem wantlist, nem valor, nem decks.
  `riftvault runas [--mais RUNA | --menos RUNA] [--n N]` na consola.
- **Filtros:** Tudo / Faltas, e por tipo de impressão (Base, Arte alt.,
  Signature, Tokens/Promos). "Faltas" mostra tudo o que não está completo,
  tanto faz faltarem 3, 2 ou 1.
- **Procura** por nome ou código.

As escolhas ficam guardadas no browser.

## Quanto custa

Terceira secção: a **tabela de preços do jogo** (chamava-se «Faltas» até
2026-09-15 de manhã e mostrava o que faltava; à tarde ficou claro que *"o
separador quanto custa nao e para ter as faltas! e para passar a ter o top 5
comum mais cara, por cada set / o top 5 incomum / o top5 rara / o top5
mitica"*; o identificador interno continua `faltas`). Para **cada edição**
com botão, quatro blocos — **comuns, incomuns, raras, míticas** — com as
**5 mais caras** de cada (`quanto_custa.top_por_raridade`), do mais caro para
o mais barato. Um separador por edição em cima e um **Todas** que as mostra
uma a seguir à outra.

- **Entram todas as cartas da edição, tenhas ou não tenhas.** Não é uma lista
  de compra: uma carta de que já tens as três cópias continua a ser das mais
  caras e aparece. Cada linha diz **tens N/M** (as cópias na Coleção e o
  alvo), só como informação — verde quando está ao alvo.
- **«Míticas» são as `epic`** do catálogo da RiftScribe, que não tem outra
  raridade acima (não há *mythic*). A quinta raridade do catálogo,
  `showcase`, é o tratamento das reimpressões de topo do OGN e do SFD e não
  cabe em nenhum dos quatro blocos.
- **Só a sequência de cada edição.** As artes alternativas ficam de fora a
  pedido (*"AltArt nao precisa fazer isto"*); as sobrenumeradas e as promos
  também, porque são a mesma categoria (*"Alt Art, overnumbered, etc etc é
  puramente coleção"*) — e com elas dentro os blocos das comuns e das raras
  do UNL e do VEN eram só reimpressões de topo (os Poros a 100–285 €).
  `quanto_custa.so_sequencia: false` mete-as. Tokens, signatures e runas sem
  numeração continuam escondidos, como em todo o lado.
- **Sem o OGS** (`quanto_custa.sem_edicoes`), de quando isto eram faltas
  (*"menos proving grounds"*). O rodapé diz o que ficou de fora.
- **Preços só de ofertas em inglês** (`precos.linguas`; *"apenas cartas
  versao ingles"*), Near Mint/Mint, o mais baixo no CardTrader.

Na consola: `py -m riftvault quanto-custa [--edicao OGN]`.

## Faltas

Quarta secção (15/09/2026, fim da tarde): **o que falta, por edição, em
quatro blocos, cada um com a sua wantlist** — *"quero as faltas por edicao e
dividido em 3 partes / Masterset / Alt Art / OverNumbered"* e, a 19/09,
*"quero 4 wantlist: 1 so para o master set, 1 so para as Alt.Art, 1 so para
as Overnumbered, uma so para as Promo (no caso SP)"*. Não é o separador
antigo (esse era por raridade e passou a ser o «Quanto custa»); é uma secção
própria, com a **carta em imagem** e o crachá a dizer **quantas faltam**.

- Um botão por edição (o OGS entra) e «Todas», cada edição com **Master set**
  (a sequência, alvo do tipo — Unit/Spell/Gear 3, Legend e Battlefield 1,
  runas numeradas 3), **OverNumbered** (as sobrenumeradas, 1 de cada —
  *"overnumbered continua 1 de cada"*), **Alt Art** (as artes alternativas,
  **a playset** desde 2026-09-18 — *"Alt Art para playset"* —; os decks nunca
  levantam este alvo; **sem as das runas**, que saíram de tudo a 2026-09-17)
  e **Promos** (as `VEN-SP`, **1 de cada** desde 2026-09-19). A ordem é a
  **mesma da grelha da Coleção** (`master_set.ordem_dos_blocos`): muda-se num
  sítio e muda nos dois. Cada bloco diz quantas faltam e quanto custa fechar;
  a edição soma os quatro.
- **Cada bloco tem a sua wantlist do Cardmarket**, por baixo das cartas — já
  preenchida, com os três botões de sempre (copiar, com código, CSV) —, só
  com o que há a **comprar**. São quatro por edição, separadas; a do master
  set é **exactamente** a wantlist dessa edição no fim da Coleção. Na
  consola: `py -m riftvault faltas --edicao OGN --bloco alt_art --cardmarket`
  (blocos: `master`, `alt_art`, `overnumbered`, `special`).
- **O que vem a caminho conta.** Uma carta já encomendada aparece a azul
  tracejado, «a caminho», **não soma** ao que há a comprar e não vai para a
  wantlist do bloco; uma parcialmente coberta diz «1 a caminho · 2 por
  comprar».
- **A wantlist geral continua a ser só o master set.** A do fim de cada
  edição da Coleção e a «Wantlist — tudo» não levam Alt Art, OverNumbered nem
  Promos (*"apenas pedi para ser feito track de playset para eu saber
  exatamente quantas tenho"*) — essas três compram-se, quando ele quiser,
  pela wantlist **própria do bloco**. O cabeçalho diz as duas contas —
  «fechar os quatro blocos» e «wantlist geral». Para meter os quatro na
  geral é **uma linha** no config: `listas_de_compra.so_master_set: false`.

`api/faltas_edicao.json`; na consola, `py -m riftvault faltas [--edicao OGN]
[--bloco B] [--cardmarket]`. A conta é a **mesma** da wantlist
(`a_subir.masterset` + os locais + o pendente) — não há segunda
implementação, só outra arrumação.

**As faltas dos decks não estão aqui.** As do master set estão também na
**wantlist do fim de cada edição** da Coleção (`api/wantlist.json`) e as dos
decks nas abas do separador **Decks**, a seguir aos decks
(`api/compras.json`):

- **Decks → Staples** — cartas que **mais do que um deck** pede e que não tens em
  número suficiente. São as que rendem mais por euro: uma compra serve vários
  decks. Cada tile diz quantos decks a querem e quais.
- **Decks → Por deck** — o que falta a cada deck, agrupado por edição.
- **Decks → Pimp decks** — as versões **alteradas** das cartas que os teus decks usam:
  artes alternativas e showcase. Sem signatures e sem promos de runa
  (`pimp_ignorar_tipos`), e **sem runas nenhumas desde 2026-09-17**: a runa
  em arte alternativa está retirada de tudo (ver «As runas em Alt Art»
  abaixo) e não é versão para pimpar — nem as do catálogo (`OGN-042a`) nem
  as que só o CardTrader tem (`SFD-R02a`), que antes apareciam marcadas
  **"fora do catálogo"**. Dá para vetar impressões à peça em
  `pimp_ignorar_impressoes` (as sobrenumeradas caras); a carta continua lá
  pelas outras versões. Mostra só **o que falta comprar**: desconta o que já
  tens e o que vem a caminho.

  Arrumado **por deck**, nunca por edição: a vista **Todas** tem uma
  secção por deck, e há sub-abas para veres um de cada vez com a quantidade
  que esse deck usa. Cada sub-aba tem a sua lista para a wantlist.
### Encomendas (2026-09-17)

O separador **Encomendas** é **a grelha da Coleção, de Rara para cima** — as
mesmas edições, os mesmos blocos, os mesmos tiles com imagem, tenhas a carta
ou não — onde marcas **o que compraste e ainda não chegou**. Em cada tile:

- o crachá continua a ser o da Coleção (`1/3`): **encomendar não é ter**;
- o **+** marca mais uma cópia comprada **dessa versão** (a alt art é a alt
  art, a base é a base), o **−** tira-a, e «+2» a azul diz quantas vêm a caminho;
- **Chegou (N)** dá entrada dessa impressão na Coleção — passa pelo mesmo
  `+` da grelha, fica no histórico e dá para anular.

Uma encomenda **não conta** para a percentagem, os níveis nem o valor até
chegar; **desconta** das listas de compra (wantlists, Faltas, «falta
comprar» dos decks). O corte é pela raridade da base a partir de
`encomendas.raridade_minima` (`rare`: raras, míticas e as `showcase`); o que
vier a caminho fora da grelha (uma comum pela consola, uma runa do CardTrader)
aparece no cabeçalho com o seu «Chegou». No site publicado é só leitura.

Os `+`/`−` e o «Chegou» viveram nos tiles dos **decks** de 11 a 17/09; lá
ficou só a informação «N a caminho». Na consola: `py -m riftvault encomendas
[--mais REF [N] | --menos REF [N] | --chegou [REF]]` (por código é só essa
impressão, por nome é a carta) e `py -m riftvault pending --chegou [ID]`.

A aba **A subir** (do master set, o que ainda não tens e subiu 10% ou mais
nos últimos 30 dias) saiu do site com o separador; a conta continua na
consola, `py -m riftvault a-subir [--cardmarket]`, com as mesmas exclusões
(`a_subir.excluir`) e a mesma regra de «ainda não tenho».

**As runas não se contam nos decks** (17/09/2026, à noite — frase tua:
*"esquece as runas, nao facas contagem de runas nos decks, indica me so
quantas sao e eu organizo isso sozinho a mao"*). O Rune Pool de cada deck
continua a ler-se e a mostrar-se com as quantidades da lista («9 Chaos Rune,
3 Order Rune») e o cabeçalho continua a validar as 12 runas — mas não há
tenho/faltam, alocação da Coleção, disputa entre decks, falta a comprar nem
euros para uma runa, e a grelha da Coleção deixou de dizer «Azir 9» numa
runa. O «tenho X de N» do deck conta só o resto — **54 de 54** num deck de
66, com «· 12 runas» ao lado —; o denominador desce de propósito, porque
deixar o 66 dizia que faltavam 12. É `decks.contar_runas: false` no config
(`true` volta a contá-las). Já antes disso as runas não entravam nas abas
Staples/Por deck (`faltas_ignorar_tipos`, 01/09/2026 — eram baratas e
enchiam os staples); esse botão fica, mas com este já não tira nada. A
Coleção **não** mexe: as 6 runas base do OGN continuam a 3 no master set, a
contar para a percentagem e para as wantlists.

**Os decks que pedem a mesma carta compram o que a Coleção não chega para
todos** (11/09/2026). Cinco decks a pedir 3 Defy com 3 na Coleção são 12 Defy a
comprar — já não se «trocam entre decks»; o teto do playset que havia até
essa data ficou revogado. Cada carta mostra o que os decks pedem ao todo.

A carência aqui é **global** — soma-se o que todos os decks pedem e desconta-se
o que tens — e dá a mesma soma que a secção Decks: a alocação por prioridade
diz quem fica com o quê, e o que sobra por deck é o que esse deck compra.

## A mais

Quinta secção (17/09/2026): *"todas as cartas que estao listadas a mais ou
que estavam num deck e deixaram de estar"*. Um botão por edição (o OGS fica
sem botão mas aparece em «Todas»), e em cada edição dois blocos, com a
**carta em imagem** e o crachá a dizer o número:

- **Excedente** — impressões de que tens **mais cópias do que o alvo** que a
  Coleção e os decks já usam: playset na sequência e nas artes alternativas
  (desde 2026-09-18), 1 nas sobrenumeradas e nas promos (estas desde
  2026-09-19; os decks não levantam este alvo), e o que está
  escondido (tokens, signatures) não tem alvo e sobra inteiro, marcado. A
  conta é `cópias − max(usadas nos decks, alvo)`: **o que os decks levam
  nunca é a mais**, o que está no binder Decks/Venda e nenhum deck pede é, e
  o que está sleevado num deck nunca aparece. «tens 5, queres 3 → 2 a mais».
- **Sem runas, nunca** (17/09/2026, à noite — *"no a mais nunca aparece
  Runas"*): uma runa não aparece em nenhum dos dois blocos, esteja na
  sequência (as 9 Calm Rune de que a Coleção pede 3) ou escondida (as
  `VEN-R`), nem nas libertadas. O cabeçalho diz quantas ficaram de fora por
  isso. É `a_mais.sem_runas: true` no config.
- **Libertadas dos decks** — o que uma lista de deck **pedia e deixou de
  pedir** (carta tirada da lista, quantidade baixada, ou o deck apagado), com
  a data, quantas tens e quem ainda a pede. **O registo nasceu a
  17/09/2026 e começa vazio**: o riftvault não guardava o que os decks
  pediam — a alocação é recalculada a cada leitura —, por isso só sabe do
  que mudou desde então. Escreve-se no fim de cada importação das listas
  (`deck_need_log` no vault.db; cópia legível em `data/decks.log`).

**Só mostra.** Não muda alvos nem contas — a percentagem, a wantlist, a
falta dos decks e o valor ficam iguais — e não é a Venda: não há preço de
venda nem lista para o Cardmarket. `api/a_mais.json`; na consola,
`py -m riftvault a-mais [--edicao OGN]`.

## Seguir jogadores (Piltover Archive)

17/09/2026: *"o @koko_lopez e um jogador muito bom, gostava de seguir os
decks que ele coloca e que vai atualizando"* / *"nao preciso que me diga
quanto custaria, mas sim o que falta"*. Por agora só na consola (a secção no
site é a parte 2):

```bash
py -X utf8 -m riftvault seguir [--jogador NOME] [--so-mudados] [--sem-rede] [--json]
```

Os handles a seguir ficam em `seguir.jogadores` no `riftvault_config.json`.
Para cada um lê o perfil (`/users/<nome>`), a listagem pública
(`/decks?q=<nome>`, filtrada pelo autor) e a página de cada deck **novo ou
actualizado** desde a última corrida — e diz, por deck, **o que te falta**
para o montar: conta tudo o que tens (incluindo o que está nos teus decks),
qualquer impressão menos assinada, e **nunca euros**. Um nome que não esteja
no catálogo fica «por identificar», nunca adivinhado, e o deck diz em cima
que a falta está incompleta. O estado fica em `data/seguir/estado.json`.

Educação: só páginas HTML (a `/api/` deles está proibida no `robots.txt`),
um pedido por segundo, User-Agent honesto, nada de contas. O perfil em HTML
não traz a lista toda (o browser vai buscá-la à API), por isso a página diz
quantos o perfil anuncia e quantos a listagem deu — hoje 18 e 17. Se o site
mudar de forma, o comando **rebenta** com o nome da marca que faltou em vez
de dizer «não te falta nada».

## Wantlist do Cardmarket

Há listas em três sítios, todas com o mesmo formato porque saem do mesmo
gerador (`riftvault/cardmarket.py`):

- **Coleção**, no fim de cada edição: **Wantlist Cardmarket — <edição>**, com
  as faltas dessa edição já escritas na caixa, e a seguir **Wantlist — tudo**
  com as cinco edições seguidas. O cabeçalho da edição diz *N cópias a comprar
  nesta edição · X €* e leva-te ao bloco.
  Os três botões: **Copiar para o Cardmarket**, **Copiar com código** e
  **Descarregar CSV**.
- **Decks → Por deck** e **Decks → Pimp decks**, com o botão de sempre.
- Na consola, `py -m riftvault a-subir --cardmarket` (o que está a subir) e
  `--todas` (tudo o que falta ao master set).

As wantlists da Coleção são a lista completa do que falta ao master set
(`a_subir.master_faltas`), cortada por edição: só a sequência (as runas
numeradas a 3, como o resto; a coleção extra fica fora por
`listas_de_compra.so_master_set`), a mesma regra *cópias + a caminho <
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
| 1 | a sequência do master set, por número de coleção | o **playset do tipo** (Unit/Spell/Gear 3, Legend e Battlefield 1, **runas 3** desde 2026-09-15 — `master_targets_by_type`) |
| 2 | as runas especiais (a runa que não é a base), por edição | o das artes alternativas — bloco **vazio** desde 2026-09-17, ver «As runas em Alt Art» abaixo |
| 3 | as artes alternativas | o **playset do tipo** (2026-09-18: *"muda novamente: Alt Art para playset"*; pediram 1 de cada de 16/09 a 18/09 — os decks nunca o levantam, ver «Que versão joga cada carta») |

O alvo da coleção extra é **por categoria**, em `master_set.um_de_cada`: o
que lá está pede 1 (hoje `["overnumbered", "promo"]`), o que não está pede o
playset do tipo — as artes alternativas. As promos `VEN-SP` andaram:
playset a 14/09, 1 a 15/09, playset a 18/09 (*"as promos SP podes meter 3 de
cada"*) e 1 outra vez a 2026-09-19 (*"as Promo passam a 1 de cada ao inves
de playset"*). Uma palavra a mais ou a menos nessa lista é a única diferença
entre «alt art a 1» e «alt art a playset».

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
`runas_especiais` é a regra das runas (`tipos`: o que é runa; `excepto`: quais
ficam na sequência; `retiradas`: quais deixam de existir para o riftvault —
hoje `["a"]`), `master_variantes_playset` diz quais as variantes que
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
visível no bloco «Fora da coleção — promos», com alvo 1. (Desde 2026-09-18 o
bloco chama-se «Coleção — promos — playset» e pede 3: *"as promos SP podes
meter 3 de cada"*.)

**As runas promo do VEN (`VEN-R01..R06`) saíram a 2026-09-15**, por outra
frase tua (*"Saiem as runas todas e deixam de contar para masterset […] menos
as que tem numeração de masterset"*). O critério é a **numeração**: uma runa
com número da edição (`OGN-007/298` e a arte alternativa dela) fica onde
estava, com alvo 1; uma runa **sem** numeração (as `VEN-R`, código sem
`/tamanho`) está **escondida** como os tokens e as signatures — `"-R"` passou
de `fora_da_percentagem` para `escondidas`. O denominador não mexeu (já não
contavam); o que desapareceu foi o bloco «runas especiais» do Vendetta.

O nome antigo desta lista era `master_ignorar_variantes`; um config que ainda
o traga continua a funcionar.

### As runas em Alt Art saíram de tudo (2026-09-17)

Frase tua: *"deixa as runas Alt Art, **nao incluas em nada**"*. Uma runa em
arte alternativa (`OGN-007a..214a`, e as `SFD/UNL/VEN-R0Xa` que só o
CardTrader tem) é uma impressão **retirada**: não aparece na Coleção, não
conta para o master set nem para o denominador, não entra em wantlist
nenhuma, não aparece no Faltas, no Quanto custa, no A mais nem no Pimp, **não
conta para o valor nem para o playset jogável**, e os decks jogam a runa
**base**. É mais do que «escondida» — um token escondido ainda vale dinheiro e
aparece no A mais; uma retirada não existe para o riftvault. As cópias que
tens **não saem da base** (as 6 `OGN-042a` continuam gravadas), só ninguém
as lê.

O que **não** mudou: as runas base do master set (as 6 do OGN) pedem **3**,
como as outras cartas; as sobrenumeradas continuam a **1 de cada** e as artes
alternativas de cartas que não são runas pedem o que o `um_de_cada` disser
(1 nesse dia; **playset** desde 2026-09-18). (Os decks pediram a arte
alternativa por cima entre 2026-09-16 e 2026-09-17; já não pedem — ver «Que
versão joga cada carta», na secção Decks.)

Escreve-se em `runas_especiais.retiradas` (hoje `["a"]`, com a mesma
gramática das listas do `master_set`); a pergunta responde-se numa função só,
`metrics.retirada`, a que a Coleção, o valor, os decks, o Pimp e o A mais
perguntam todos. `tipos: []` desliga — sem «runa» não há runa retirada. Para
elas voltarem a tudo é reverter o merge `f1dbd5b`.

Houve nessa manhã uma regra intermédia — os decks a pedir a arte alternativa
da runa **da edição da Legend** — que durou umas horas e saiu inteira do
código com esta; não existe.

Não se distingue foil de normal: uma cópia é uma cópia.

## Venda (apagada a 2026-09-15)

Havia uma quarta secção, «Venda», com o excedente da caixa e uma análise das
comuns e incomuns mais caras. *"Esquece a parte da venda, podes apagar para já,
se for necessário mando fazer novamente"* — e foi apagada: o separador, a
página, o `riftvault venda`, o `api/venda.json` e os módulos `venda.py` e
`comuns.py`. Está tudo no histórico do git; o commit a reverter está no
relatório `riftvault-sem-venda.md`.

O que ficou, porque não era só da Venda: o **binder Decks/Venda** (é um local
das cópias, ver «Onde está cada cópia»), o `decks.colecao_allocation` (é o que
a grelha da Coleção usa para dizer «Azir 3 · Ornn 1»), e a recolha do número
de anúncios, vendedores e cópias à venda no CardTrader (`prices.oferta`,
`listings_history` no `prices.db`) — são dados de mercado e continuam a
crescer com o `riftvault prices`.

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
que precisa, o deck 2 só recebe o que sobrou. **Os decks usam a Coleção**
(11/09/2026: *"se há na coleção o deck usa"*) — uma cópia conta para a barra do
master set e para o deck ao mesmo tempo. Quando falta uma carta ao deck 2
porque o deck 1 a levou, ela vai **para a lista de compras** desse deck, e o
site diz em que deck está a que existe (*"caso algum deck ou decks já estão a
usar as cartas disponíveis na coleção, o próximo passa a marcar como faltas
para comprar"*). Mudar a ordem refaz a alocação toda.

### As runas não se contam (2026-09-17, à noite)

Frase tua: *"esquece as runas, nao facas contagem de runas nos decks, indica
me so quantas sao e eu organizo isso sozinho a mao"*. O **Rune Pool** de cada
deck continua a aparecer com as quantidades da lista e o cabeçalho continua a
validar as 12 — e mais nada: uma runa não tem tenho/faltam, não se serve da
Coleção, não disputa com outro deck, não entra na falta a comprar, não tem
preço, não se propõe para marcar, não vai ao Pimp. A barra «cartas alocadas a
este deck» conta só o resto (**54/54** com **· 12 runas** ao lado), e os tiles
das runas têm a moldura neutra com só o «9×». `decks.contar_runas: false` no
config; `true` volta a contá-las. A Coleção não mexe (as runas base do OGN
continuam a 3), e as runas em Alt Art continuam retiradas.

### Que versão joga cada carta (2026-09-17)

Frase tua: *"os decks apenas jogaram versoes normais, com excepcao da Legend
e do Champion que serao Alt Art ou Overnumbered ou SP, mas nunca assinada"*.

- **Tudo o que está no main, nos battlefields e no sideboard joga a versão
  normal** — a base da edição, sem sobrenumeração — **primeiro** (o Rune Pool
  deixou de se contar nessa noite, ver acima).
  Desde a tarde de 2026-09-17 (*"caso um deck precise de uma carta, que não
  há versão disponível em normal, mas esteja disponível em Alt.Art ou outra,
  usa"*), **o que a base não tapar completa-se com outra versão que tenhas**
  — Alt Art, sobrenumerada ou promo, nunca assinada — antes de ser falta; a
  falta que sobrar aponta à base. Uma runa em Alt Art continua **retirada** e
  não tapa nada. **A vista do deck separa as versões por arte**: uma carta
  servida por mais do que uma impressão reparte-se em sub-linhas
  («2 normal · UNL-176» / «1 Alt Art · UNL-176a», na CLI e no site); servida
  por uma só, não. O alvo da Coleção não mexe — a arte alternativa continua a
  pedir 1, jogue ou não.
- **A Legend e o Champion jogam uma versão especial**: arte alternativa,
  sobrenumerada ou promo `VEN-SP` — **nunca uma assinada**. Se tens mais do
  que uma versão especial, qualquer uma serve; se não tens nenhuma, a falta
  aponta à **mais barata**, e a página do deck diz qual é e quais as outras
  («versão especial: `VEN-113a/166` (a comprar) · ou …»). Sem versão especial
  no catálogo, joga a base e não há falta.
- **Só uma cópia é especial.** A Legend é uma por deck; um Champion que a
  lista jogue mais vezes tem as restantes na base.
- **O alvo da Coleção nunca sobe por causa dos decks.** As OverNumbered e as
  promos pedem 1 de cada (2026-09-19), as Alt Art o playset (2026-09-18),
  joguem ou não num deck — é o `master_set.um_de_cada` que manda. (Entre 2026-09-16 e
  2026-09-17 os decks jogavam tudo em Alt Art e o alvo subia ao que eles
  pediam — durou um dia, saiu inteiro do código e não volta sem pedires.)

No config: `decks.so_normais_excepto` (os papéis que jogam a versão
especial, hoje `["legend", "champion"]`; vazio = tudo na base) e
`decks.versoes_especiais` (o que conta como especial, na gramática das listas
do `master_set`: `["a", "overnumbered", "promo"]`; escrever `"*"` aí dá erro
de propósito). No código, `decks.Versoes` e `decks.versoes_dos_decks`.

Para reordenar, usa os botões **Tornar principal / Subir / Descer** no site,
ou:

```bash
py -m riftvault decks --order azir,ornn   # o primeiro passa a principal
py -m riftvault deck azir --onde          # detalhe, com as impressões a usar
py -m riftvault shopping --deck azir --csv faltas.csv
```

Para **apagar** um deck, apaga o `.txt` — o site atualiza-se sozinho.

Cada deck é uma grelha de cartas, como a Coleção. A moldura diz o estado:
verde tens, vermelho falta, âmbar falta mas existe num deck de cima (compra-se
na mesma; a nota diz onde está). O canto mostra quantas o deck pede, e o badge
quantas lhe estão alocadas.

Ao contrário, na **Coleção** cada carta que algum deck usa diz quais e quanto
— `Azir 3 · Kennen 2 (faltam 2)` —, a vermelho quando um deck não recebe o
que pede. O filtro **Em decks** mostra só essas, e `riftvault stats --usadas`
lista o mesmo na consola. E cada carta que saiu fisicamente para um deck diz
para qual — para quando a procuras no binder e ela não lá está. Quando só parte
saiu, diz quantas ficaram (`3× Azir · 1 na Coleção`).

### Onde está cada cópia (2026-09-10)

Cada cópia tem **um local**, e só um:

| local | o que é | conta para |
|---|---|---|
| **Coleção** | os binders de coleção | a percentagem de master set, os níveis, as wantlists |
| **Deck `<slug>`** | sleevada dentro de um dos `decks/*.txt` | só esse deck |
| **Binder Decks/Venda** | o stock livre | qualquer deck, por prioridade |

- **A Coleção só conta o que está na Coleção.** Uma cópia que esteja num deck
  deixa de contar para a barra, mesmo sendo a mesma impressão — a impressão
  volta a aparecer como falta.
- **Os decks montam-se com os três locais** (11/09/2026). Uma carta que o deck
  pede e que está nos binders de coleção conta como «tenho», e a página do
  deck diz «na Coleção». O local é informação de onde a cópia está — não
  desconta nada.
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
do que é. Cartas que faltam por estarem noutro deck entram nessa conta desde
11/09/2026: compram-se, e o chip «disputadas» diz quantas são.

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
riftvault build [--out site] [--se-mudou]        # modo publicado
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
riftvault local [...]                             # onde está cada cópia
riftvault map / prices / value                    # CardTrader
riftvault seguir [--jogador NOME] [--so-mudados]  # decks dos jogadores seguidos: o que falta
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
  seguir.py       os decks dos jogadores seguidos no Piltover Archive e o que falta
  server.py       modo edição (Flask)
  build.py        modo publicado (estático)
  cli.py          linha de comandos
  web/            index.html + app.js + style.css — o MESMO nos dois modos
data/
  vault.db        a coleção e os decks. VAI para o Git. Só tu escreves.
  prices.db       histórico de preços. VAI para o Git. Só o robô escreve.
  catalog.db      cache do catálogo. NÃO vai (está no .gitignore).
  images/         cache das imagens. NÃO vai.
  seguir/         estado.json (os decks seguidos; VAI) e paginas/ (HTML lido; NÃO vai)
decks/            listas de deck em .txt
docs/             spec da API e snapshot do catálogo, para referência
```

O contexto todo — incluindo as armadilhas da API e o que ainda não foi
validado — está no [CLAUDE.md](CLAUDE.md).

# riftvault

Gestor da minha coleção de **Riftbound**. Objetivo: ter playsets, incluindo as
artes normais **e** as alternativas.

Secções: **Coleção**, **Decks**, **Faltas**, **A mais** (escondida desde
25/09/2026), **Encomendas** e **Venda**. O
catálogo vem da API pública da
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

## Como o site está organizado (2026-09-24)

O riftvault é uma secção do **baverone.com** e veste a mesma roupa do
`mtgvault`: barra lateral fixa à esquerda, cabeçalho de página com migalhas,
fundo `#07080d`, Space Grotesk nos títulos e Inter no texto. O que muda de
projeto para projeto é uma cor — aqui o **roxo `#a77bff`** — e a inicial do
logótipo, o **«R»**.

**A navegação sai de um sítio só:** a tabela `NAV` no `riftvault/web/app.js`.
Dela saem a barra lateral, as migalhas e o título de cada página. Uma secção
nova é uma linha ali.

| grupo | página | o que responde |
|---|---|---|
| — | **Início** | o painel de hoje: master set, o que falta comprar, valor, decks montados, o que vem a caminho, a coleção extra |
| Coleção | **Coleção** | a grelha, edição a edição |
| | **Faltas** | o que falta para fechar cada edição, em quatro blocos |
| | **A mais** | o excedente e o que os decks libertaram — **escondida hoje** |
| Decks | **Decks** | as listas montadas |
| | **Staples** | as cartas que vários decks pedem |
| | **Por deck** · **Pimp decks** | as outras listas de compra dos decks — **escondidas hoje** |
| | **Produto Selado** | displays, cases, decks, bundles e Proving Grounds: o que há, o que tens e o que não tens |
| Compras | **Encomendas** | o que compraste e ainda não chegou |
| | **Venda** | o que estás a vender agora e a conta para quem compra |

**Esconder uma aba é uma linha de config** (25/09/2026):
`"abas": { "escondidas": ["a-mais", "pordeck", "pimp"] }`. Esconder **não é
apagar** — o «A mais» continua a ser calculado, o `api/a_mais.json` e o
`api/compras.json` continuam a ser gerados e servidos, e o `riftvault a-mais`
continua a responder. O que sai é o botão, no servidor local e no site
publicado. **Repor é tirar o nome da lista, mais nada.** Os nomes são
`inicio`, `colecao`, `faltas-edicao`, `a-mais`, `decks`, `staples`, `pordeck`,
`pimp`, `encomendas`, `venda` e `selado` (também se aceitam como se lêem no
ecrã: «A mais», «Por deck», «Pimp deck», «Produto Selado»); um nome
desconhecido rebenta. Ver `riftvault/abas.py`.

**Cada vista tem endereço.** `#colecao/UNL`, `#faltas-edicao/OGN`,
`#decks/ornn`, `#decks/staples`, `#encomendas/VEN` — dá para guardar nos
favoritos e o «voltar» do browser sabe desfazer. Os nomes das rotas são os de
sempre; o que mudou foi o id da `<section>` no DOM, que passou a `sec-<nome>`:
a rota e o id eram o mesmo texto e o browser tratava `#decks` como âncora,
abrindo a página já com o cabeçalho acima do topo do ecrã.

**No telemóvel é a MESMA navegação**, num painel que abre no botão ☰ — não há
um menu «de telemóvel» com menos coisas lá dentro.

### Nada de botões a correr para o lado

Era o problema, e está medido. As duas filas de separadores do topo tinham
`overflow-x: auto`, e por isso o `scrollWidth` da página dava sempre 390 num
telemóvel de 390 px — parecia que estava tudo bem. Medido num Chrome a sério,
a 390 px, **antes**:

| fila | largura real | largura visível | escondido |
|---|---|---|---|
| secções (Coleção … Encomendas) | 393 px | 232 px | 161 px |
| edições (OGN … Todas) | 695 px | 390 px | 305 px |
| **decks** (6 decks + 3 listas) | **1253 px** | 390 px | **863 px** |

Dos nove botões dos decks viam-se três. **Depois: zero** — nenhum contentor
da página tem conteúdo escondido para o lado, a 390 px ou a 1440 px. No lugar
das filas ficaram:

- o **seletor de edição**, um controlo segmentado que *envolve* (parte-se em
  linhas em vez de correr);
- o **índice vertical dos decks**, à esquerda do conteúdo no PC e um
  `<select>` no telemóvel — os dois desenhados da mesma lista
  (`itensDoIndice`), para não haver duas ordens nem dois rótulos.

`tests/test_casca.py` fixa isto: sem `overflow-x: auto` no CSS, toda a secção
com item na barra e vice-versa, nenhum link `#` partido, a rota e o id do DOM
diferentes, e os ícones da navegação a existirem (SVG, nunca emojis — um
emoji é desenhado pelo sistema e nunca acende com o rótulo).

### O painel do Início não faz contas

Todos os números vêm de payloads que as outras páginas já pediam
(`api/index.json`, `api/decks.json`, `api/encomendas.json`,
`api/faltas_edicao.json`) e aparecem como de lá vêm. Um painel com aritmética
própria era uma segunda resposta às mesmas perguntas — e mais cedo ou mais
tarde discordava da página a que manda ir. Há teste. Se um dos ficheiros não
responder, o cartão fica a «—» e a página aguenta-se.

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

## Faltas

Terceira secção (15/09/2026, fim da tarde): **o que falta, por edição, em
quatro blocos, cada um com a sua wantlist** — *"quero as faltas por edicao e
dividido em 3 partes / Masterset / Alt Art / OverNumbered"* e, a 19/09,
*"quero 4 wantlist: 1 so para o master set, 1 so para as Alt.Art, 1 so para
as Overnumbered, uma so para as Promo (no caso SP)"*. Não é o separador
antigo de faltas (esse era por raridade, passou a ser a tabela de preços
«Quanto custa» a 15/09 e foi apagado a 19/09 — ver o `CLAUDE.md`); é uma
secção própria, com a **carta em imagem** e o crachá a dizer **quantas
faltam**.

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

**Cada deck tem as suas cópias próprias** (21/09/2026 — frase tua: *"voltamos
aos decks usarem a coleccao, mas cada deck precisa de ter as cartas proprias;
colocas em cada deck o + e - para eu dizer se afinal tenho ou nao; estas
copias que eu coloco nos decks nao sao para adicionar a coleccao"*). Os decks
voltaram a usar a Coleção como desde 11/09 (a grelha diz «Azir 3», o filtro
«Em decks», as libertadas, o «para que deck» das Encomendas) e **não partilham
entre si**: o que os seis precisam é a **soma** (324 cópias de 136 cartas a
21/09; 54 por deck; main e sideboard somam; runas fora). E cada carta de cada
deck tem um **`+`/`−`** para dizeres quantas cópias tens **guardadas para
aquele deck** — as **cópias próprias**, no local `proprio:<slug>`
(`riftvault proprias azir --mais OGN-045 3` na consola). Regras: **não entram
na Coleção** — não contam para os níveis, o denominador, as Faltas, as
wantlists, as Encomendas, o A mais, o valor nem o playset jogável; meter ou
tirar uma não mexe um número da Coleção —; são **só daquele deck**; servem
**primeiro**, e o que sobrar vai buscar à Coleção — por isso meter próprias
**liberta** cópias da Coleção que o deck usava (e, pela regra do A mais de
17/09, uma cópia libertada acima do alvo passa a aparecer lá como a mais);
`faltam = precisa − próprias − o que a Coleção alocou`. **Só versões base**,
a Legend e o Champion incluídos (`decks.so_base: true`): o `+` só aceita a
base; uma própria de outra versão que lá esteja fica em «não servem», com o
motivo. A regra de 17/09 (Legend/Champion numa versão especial) está
desligada e não volta só por se pôr `so_base: false` — com isso qualquer
versão não assinada serve um lugar normal (a base primeiro). Medido a 21/09,
com as próprias a zero: faltam **37 cópias de 19 cartas** aos seis decks
(`so_base: false` daria 36 de 18 — a diferença é 1× Vi, Peacekeeper, que tens
em Alt Art); o pior caso é o Defy: precisam de 9, tens 2.

(A **experiência do pool próprio** — um pool único partilhado por todos os
decks, fora da Coleção, `decks.modo: "pool_proprio"` — durou a manhã de
21/09/2026 e acabou com a frase de cima. Escrever esse valor no config
rebenta.)

## A mais

Quarta secção (17/09/2026): *"todas as cartas que estao listadas a mais ou
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
são exatamente as cópias que a contagem por níveis da barra diz que faltam
(a mesma conta dos cartões do painel, mas em cópias e com as runas).

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

### O painel do topo: 1 de cada, 2 de cada, playset — e Raridade / Domínio

(2026-09-21, o «layout H».) Por baixo dos separadores das edições e por cima
da grelha, **três cartões** — «1 de cada», «2 de cada», «playset» —, cada um
com o **tenho/total** em grande (impressões, nunca percentagem), uma barra
fina e «faltam N»; e por baixo **dois quadros**, **Raridade** e **Domínio**,
uma linha por categoria com a bolinha da cor, três mini-barras (uma por
nível, da mais escura à mais clara) e o tenho/total à direita.

- nível 1 = impressões com pelo menos **1** cópia; nível 2 = com pelo menos
  **min(2, alvo)**; nível 3 = com o **alvo** (o playset). Onde o alvo é 1
  (Legends, Battlefields, sobrenumeradas, promos) os três coincidem.
- É sobre o **bloco escolhido** nos chips do painel — master set,
  sobrenumeradas, artes alternativas, promos — da **edição aberta**, ou de
  **«Todas»** (o separador novo, no fim da fila das edições, que mostra as
  cinco seguidas na grelha). No fim da fila de chips há o **«Tudo»**: todos
  os blocos dessa edição somados num só número, **cada bloco com o seu
  alvo** (não há um alvo único por cima de tudo); com «Todas» escolhido é
  tudo de todas as edições. O que abre por omissão continua a ser o master
  set.
- **As runas nunca entram** — nem no total, nem nos níveis, nem nos quadros.
  A barra do master set continua a contá-las (a 3, no OGN), por isso o cartão
  «playset» e a barra diferem em 6 impressões no OGN; o painel diz «sem as 6
  runas».
- Conta **cópias na Coleção**, não o que vem a caminho; as escondidas e as
  retiradas ficam de fora como ficam da grelha. A raridade é a da base do
  grupo; «Sem domínio» é o `Colorless` e «Multi-domínio» as cartas com dois.
- Anda ao mesmo tempo que os `+`/`−`; a verdade do servidor vem em
  `progress.painel` de cada edição e em `painel` do `api/index.json`.

Na linha de comandos, `riftvault stats` imprime a tabela — por bloco, por
edição e «TODAS». A paleta do painel está em variáveis no topo do
`style.css` (`--h-*`, `--lvl-*`, `--rar-*`, `--dom-*`), para se alargar ao
resto do site quando for altura.

A contagem antiga por níveis (a da barra, em **cópias** em falta e com as
runas) continua a existir por baixo — é o que a linha «N cópias a comprar» e
o degrau das wantlists lêem —, só deixou de ter chips próprios.

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
nenhuma, não aparece no Faltas, no A mais nem no Pimp, **não conta para o
valor nem para o playset jogável**, e os decks jogam a runa
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

Não se distingue foil de normal no GRÃO da coleção: uma cópia é uma cópia, e o
alvo do master set é por impressão. Desde 2026-09-22 há, ao lado disso, uma
**contagem** de quantas foils tens de cada — que se SOMA às normais e, desde
2026-09-26 à tarde, **conta** para o master set e para o valor; ver a secção a
seguir.

## Foil e não-foil, nas comuns e incomuns (2026-09-22, corrigido a 2026-09-26)

*"Para comuns e incomuns, coloca contagem para Foil e Non-Foil, para todas as
edicoes excepto Proving Grounds"* — «Proving Grounds» é o OGS, por isso vale
para o OGN, o SFD, o UNL e o VEN.

**O foil SOMA-SE ao normal.** São duas contagens independentes:

    copies.qty       as cópias NORMAIS
    copies.qty_foil  as cópias FOIL
    total            qty + qty_foil   (nunca se grava: é a soma)

Com 3 normais e 3 foil tens **seis** cópias, não três. (Até 2026-09-26 era ao
contrário — o `qty` era o total e o foil estava lá dentro, por isso o `+` do
foil *convertia* uma normal. Era erro nosso: *"as foils quando eu marco é que
tenho TAMBÉM foil, ou seja, normal + foil e não apenas 1, no caso daria 3+3"*.
Nenhum número guardado precisou de mudar — o que saiu foi o `CHECK` da base.)

Nas cartas do âmbito — as impressões **base**, não sobrenumeradas, comuns e
incomuns, dessas quatro edições: **512 impressões** — o tile da Coleção ganha,
por baixo dos `+`/`−` de sempre, um contador pequeno de foil e a linha «3
normais · 3 foil = 6». O `+` do foil **não mexe nas normais** (e o `−` da
grelha não mexe nas foils): acrescenta uma foil, e o total sobe. Não tem tecto
natural — trava só num limite de sanidade. Por baixo do painel do topo há o
resumo da edição aberta (ou de «Todas»), com uma linha por raridade.

**Uma carta só em foil** (0 normais, foil > 0) é estado legítimo desde
2026-09-26, e conta: o crachá lê `2/3`, porque as foils são cópias da impressão.
A linha de baixo diz «0 normais · 2 foil = 2» e o `−` fica desligado — ele baixa
as normais, e não há nenhuma.

### O FOIL CONTA (2026-09-26, à tarde)

*"Contam para o valor sim, e contabilizas tambem como parte do master set"*. As
duas chaves que nasceram desligadas de manhã estão **ligadas**, e uma cópia foil
vale como cópia da impressão:

| chave | hoje | o que faz |
|---|---|---|
| `foil.conta_para_coleccao` | **true** | os foils contam para os ALVOS: os três níveis, o denominador, as Faltas e as wantlists. O que a impressão tem é `qty + qty_foil` |
| `foil.conta_para_valor` | **true** | os foils contam para o VALOR, **ao preço da normal** |
| `foil.entra_no_a_mais` | **false** | os foils **não** entram no que sobra no «A mais» |

**O valor é um PISO, e a página di-lo.** Não há fonte de preço de foil — o
catálogo tem um preço por impressão, o Cardmarket responde 403 e o CardTrader não
dá trend —, por isso as foils contam ao preço da versão normal e o valor real é
mais alto. A ressalva aparece em todos os sítios onde o número aparece (a barra
da Coleção, o cartão do Início, o resumo do foil, o `riftvault value`). Nas
impressões que o CardTrader **só lista em foil** (`from_foil`) o preço já é de
foil e essas não levam ressalva — o `riftvault value` diz quantas caem em cada
caso.

**Os foils nunca são excedente.** Com eles a contar, 3 normais + 3 foil contra um
alvo de 3 dariam «3 a mais para vender» no «A mais» — e os foils são peça de
coleção. O excedente conta primeiro as **normais**, e o cabeçalho diz quantas
foils ficaram de fora. A mesma cautela vale para o aviso de stock da Venda, para
a proposta de marcação dos locais e para o `−` do tile: os três contam cópias
físicas de acabamento normal, não alvos.

**Nos decks as normais servem primeiro.** Um deck joga foil ou normal, tanto faz,
mas não se lhe tira um foil havendo normal — e quando não há, a página e a tabela
de montagem dizem quantas das cópias que ele vai buscar à Coleção são foils, para
não o mandarem procurar uma normal que não existe.

O âmbito muda-se no mesmo sítio: `foil.raridades` e `foil.edicoes_fora`.

Na consola: `riftvault foil` (o resumo, `--edicao OGN` para uma só),
`riftvault foil OGN-045` (uma impressão) e `riftvault foil OGN-045 --mais 2` /
`--menos 2`. A rota é `POST /api/foil/ajustar`; no site publicado é só de
leitura, como o resto.

## Venda — a conta de quem compra (2026-09-25)

*"Este separador permite-me marcar as cartas que estou a vender no momento para
apresentar a conta a pessoa. **Todos os preços têm que ser o Trend do
Cardmarket!**"*

Uma venda de cada vez. Juntas as cartas (procura por nome ou código, ou o botão
**+ venda** no tile da Coleção), pões a quantidade, e o ecrã dá a conta para
virares para a pessoa do outro lado da mesa — nome, edição, número, quantidade,
Trend unitário, subtotal e total, com um botão para copiar em texto. Feito para
o telemóvel: a 375 px cada linha da conta vira um cartão e nada corre para o
lado.

**O preço é o Trend do Cardmarket, e tens de ser tu a metê-lo.** O riftvault
não tem preços do Cardmarket e não os pode ter: a API oficial deles está
fechada a novas candidaturas, o site responde 403 a pedidos automáticos, as
APIs de terceiros que revendem o Trend são pagas e scraping está fora de
questão. Por isso cada linha tem um campo em euros e um link para a página da
carta lá (pelo `cardmarket_id`, que o `riftvault map` já recolhe — 1178 das
1179 impressões têm um; na que falta o link é a pesquisa pelo nome de mercado).
O Trend fica guardado por impressão **com a data**, para a venda seguinte vir
preenchida, e passados `venda.trend_valido_dias` dias aparece marcado como
velho — não se apaga.

**O preço do CardTrader nunca entra na conta.** Aparece ao lado, escrito
«CardTrader, só referência», porque é a oferta mais barata de lá e não um
Trend. Uma linha sem Trend conta **zero** e o cabeçalho diz quantas faltam.

**Marcar cartas para venda não tira nada de lado nenhum**: não mexe nos níveis,
no denominador, nas Faltas, nas wantlists, no valor, nos decks, no foil nem nas
cópias próprias (`tests/test_venda.py` fotografa tudo isso, mete e tira linhas
e exige que fique igual). Quem baixa as cópias é o botão **separado** «marcar
como vendidas», que pede confirmação, passa pelo caminho de sempre (fica no
registo, dá para desfazer) e guarda a venda no `sale_log` com o Trend da
altura.

Avisa — não bloqueia — quando pões à venda mais cópias do que tens registadas,
ou uma carta que um deck **montado** está a usar.

Na consola: `riftvault venda` (a lista e a conta), `--juntar REF [N]`,
`--tirar REF [N]`, `--trend REF EUR`, `--limpar` e `--vender --sim`. No site
publicado é só de leitura, como o resto.

## Produto Selado (2026-09-25)

*"Um separador que é «Produto Selado», em que vai tudo o que é produtos de
coleção do Riftbound, como displays ou boxcase, ou duel decks, proving ground,
etc etc, para eu saber o que há, o que tenho e o que não tenho."*

**A lista vem do CardTrader**, porque o catálogo da RiftScribe só tem cartas —
não tem produto selado nenhum. E a separação selado/single **não é um palpite**:
o CardTrader arruma os blueprints por **categoria** e publica-as
(`GET /categories`). As do Riftbound são treze, e a **258 é «Riftbound
Singles»** — as cartas. Entram seis:

| categoria | o que é | quantos (25/09/2026) |
|---|---|---|
| 259 Booster Boxes | os displays | 10 |
| 260 Boosters | pacotes soltos | 21 |
| 261 Bundles | vaults, pre-rift kits, bundles | 13 |
| 262 Starter Decks | champion, trial e showdown («duel») decks | 24 |
| 263 Box Sets & Displays | os **cases**, as box sets e os **Proving Grounds** | 15 |
| 283 Complete Sets | sets de cartas vendidos juntos | 2 |
| | da API, juntando os repetidos | 81 |
| | mais os 17 do `selado.extra` | 98 |
| | menos os 32 do `selado.excluidos` | **66** |

**O que ele mandou tirar** (25/09/2026), em duas ordens da mesma noite e na
mesma lista: primeiro os **13 boosters soltos**, as **3 slim booster box**, o
«Origins: Champion Deck Set» (*compram-se à unidade*), as «Spiritforged Bulk
Runes» e os **4 Pre-Rift Kit de UM jogador** — 22; depois os **2 «Card Set»** da
categoria «Complete Sets» (*são conjuntos de cartas*), com que essa categoria
fica vazia na aba, e os **8 Trial Deck** da PROMO-RIFT (os 4 «Origins: X Trial
Deck», os 2 «Trial Deck Set» e os 2 «Trial Deck Case») — **32 ao todo**.

**Esconder não é apagar**, como no `abas.escondidas`: o
`data/selado_catalogo.json` fica intacto e **repor é tirar o nome da lista**.
Saem da aba, dos contadores, da percentagem e do total, no 8770 e no site
publicado; o cabeçalho diz quantos são e quais, para nunca desaparecerem em
silêncio. O nome é **exacto**, nunca um pedaço — é o que faz o «Spiritforged
Pre-Rift Kit» sair e o «Spiritforged Pre-Rift **EVENT** Kit» ficar, e o «Origins
Booster» sair sem levar o «Origins | Nexus Night Promo Booster». Um nome que
não case rebenta, com os parecidos.

**Tira-se por nome, nunca por categoria.** Os dois «Trial Deck Case» são de «Box
Sets & Displays» e saem porque ele os nomeou; da mesma categoria **ficam** o
«Arcane Box Set» (a caixa de coleccionador — não confundir com o «Arcane
Complete Set», que saiu), o «Arcane Chinese Promo Set», o «Signature Edition Box
Set», o «Origins: Proving Grounds Box Set Case», o «Instant Match Box 2025» e a
«Secret Garden Bundle Box». A 283 também fica em `selado.categorias`: o que saiu
foram os dois produtos, não a categoria. Ficam ainda, porque ele não os nomeou:
os 4 EVENT Kit, os 9 displays de decks, os 4 Nexus Night Promo Booster, os Promo
Pack, e todas as booster box normais, cases, vaults, decks e Proving Grounds.

O CardTrader escreve «2024 Trial Deck Set **Set**» e «2025 Trial Deck Set
**Set**»: `selado.nome_limpo` junta a palavra repetida. É apresentação — o `id`
vem do `blueprint_id` e não muda —, e mexe em 2 dos 117 produtos.

**Os acessórios tinham secção própria, e estão DESLIGADOS** (25/09/2026). Os 10
Albums e os 9 Deck Boxes entram por `selado.acessorios`, numa secção
**«Acessórios»** no fim, com contadores e valor próprios e um botão que a
esconde — e **nunca contaram para o produto selado** (nem no «o que há», nem no
«tenho», nem no «não tenho», nem no valor). Nessa mesma noite ele mandou tirar
os acessórios todos, binders e deck boxes incluídos, e **a lista ficou vazia**:
a secção não aparece. **Esvaziar não é apagar** — a chave e o código ficam, e
**repor é escrever os números das categorias outra vez**.

**Ficam mesmo de fora** — 48 playmats e 31 sleeves (acessórios de *jogo*, e 79
linhas a afogar as do selado), os 10 binders e os 9 deck boxes (enquanto
`selado.acessorios` estiver vazia), 13 memorabilia (os standees acrílicos vêm
**dentro** do Proving Grounds Box Set: contá-los à parte era contar o mesmo
produto duas vezes) e 13 cartas oversized (são cartas, não produto).
**Não desaparecem em silêncio**: o cabeçalho da página diz quantos são, por
categoria. Metê-los é acrescentar o número a `selado.categorias`.

**Blueprints repetidos juntam-se** (`selado.juntar_duplicados`, ligado). O
CardTrader tem os quatro Trial Decks da Origins com **dois blueprints cada**,
com o mesmo nome, a mesma edição, a mesma categoria e a versão vazia nos dois.
Sondadas as ofertas dos oito a 25/09/2026: os antigos (330845–330848) têm
**zero ofertas e nenhum id do Cardmarket**; os novos (363136–363139) têm as
ofertas todas e um id cada. É duplicação do catálogo deles — juntam-se num só e
a linha diz que blueprint juntou. **Não às cegas**: a chave leva a versão, por
isso os «2024 Trial Deck Set» e «2025 Trial Deck Set» continuam a ser dois.

**Três estados, que é o que ele pediu:** o que **há** (a lista toda), o que
**tens** e o que **não tens**, com os contadores no topo e um filtro por baixo.
Cada produto tem `+`/`−` e começa tudo a zero.

**Link de compra para os dois mercados** (25/09/2026: *"Se possivel, mete link
para compra no cardmarket e no cardtrader"*). Cada linha leva «Cardmarket» e
«CardTrader», a abrir em separador novo; os templates vivem no bloco
`mercados` do config, que é o mesmo que a Venda usa (`riftvault/mercados.py`).

| | formato | validado? | quantos dos 98 |
|---|---|---|---|
| CardTrader | `cardtrader.com/en/cards/<blueprint_id>` | **sim**, 25/09/2026 — o id sozinho responde 200 e o site acrescenta-lhe o slug; um id inventado dá 404; sem o `/en/` a página abre em italiano | **81** directos |
| Cardmarket | `…/Riftbound/Products?idProduct=<cardmarket_id>` | **não** — o site responde 403 a pedidos automáticos (nem o `robots.txt` responde) e não há conta | **52** directos |
| pesquisa | `…/en/search?q=` e `…/Products/Search?searchString=` | o do CardTrader responde 200 | 17 e 46 |

Quem não tem id nesse mercado leva o link de **pesquisa pelo nome**, e a linha
**diz que é pesquisa** — nunca se monta um endereço com um id que não existe.
O produto selado tem template próprio no Cardmarket: um display **não é um
«Single»**, e escrever-lhe esse caminho era dizer no URL uma coisa que se sabe
falsa. Se algum abrir em 404, é uma linha de config e todos os links mudam com
ela.

**Por sair.** A Radiance sai a 23/10/2026 e a Legacy e a The Reckoning estão
anunciadas para 2027: esses produtos aparecem marcados **«por sair»** e **não
contam para o que falta** — não se pode ter o que ainda não existe. As datas
vêm do config (`selado.datas_por_edicao`, ditas por ele): a API do CardTrader
**não dá data de lançamento nenhuma**. A Proving Grounds (OGS) ficou sem data
no primeiro dia porque ele não a deu; é da era da Origins, **31/10/2025**
(25/09/2026).

**O selado NÃO entra na Coleção.** Nem nos níveis, nem no denominador, nem nas
Faltas, nem nas wantlists, nem no A mais, nem nos decks, nem no foil, nem nas
cópias próprias, nem na Venda. As unidades vivem numa tabela à parte
(`sealed_copies`) que mais nenhum módulo lê, e o **valor do selado é um total
próprio, nunca somado ao valor da Coleção** — uma caixa por abrir não é uma
carta no binder. Medido a 25/09/2026 contra uma cópia dos dados reais: com 12
unidades de selado (1 874,00 €) na base, o site gerado sai **igual ficheiro a
ficheiro** (30 ficheiros), a menos do `api/selado.json`; o valor da Coleção
continua nos 6 615,91 €. `tests/test_selado.py` fixa isso.

**Acrescentar à mão** o que a API não tem: `selado.extra` no
`riftvault_config.json`, com `nome` (obrigatório), `edicao`, `tipo`, `data`,
`preco_eur`, `conteudo` (o que vem dentro) e `nota` (ressalvas). A lista da app
é a da API **mais** estes.

**São 17, e não são casos raros** (levantamento dele de 25/09/2026, em
`ai-pc/work/riftbound-produto-selado.md`): é precisamente o que um catálogo de
mercado não lista, porque quase não circula solto.

| o quê | quantos | conteúdo |
|---|---|---|
| Champion Deck Displays — OGN Jinx/Viktor/Lee Sin, SFD Rumble/Fiora, UNL Vi/Vex | 7 | 4 decks iguais · MSRP 79,96 USD |
| Showdown Decks Displays — VEN Zed vs Shen, RAD Evelynn vs Seraphine | 2 | 4 conjuntos de dois jogadores · MSRP 139,96 USD |
| Vault Bundle Case — UNL, VEN, RAD | 3 | 12 vaults (o da UNL com a dúvida escrita: uma fonte diz 4) |
| Proving Grounds Box Set Case — OGS | 1 | 6 caixas |
| **Pre-Rift EVENT Kit** — SFD, UNL, VEN, RAD | 4 | 16 kits de jogador + 1 display · MSRP 480 USD |

O **Pre-Rift EVENT Kit** e o «Pre-Rift Kit» do CardTrader são **produtos
diferentes** — o segundo é o kit de UM jogador (~40 USD, 29,99 € em loja PT) —
e por isso aparecem os dois, cada um com o seu conteúdo escrito.

**Os MSRP dele são em dólares e ficam no `conteudo`, nunca no preço.** Não há
taxa de câmbio validada em lado nenhum do riftvault, e inventar uma era
escrever um número que ninguém mediu: a linha diz «—» e conta no «sem preço».

**Os preços** são a oferta mais barata do CardTrader, em inglês e **por abrir**
(`properties_hash.sealed`) — a regra é diferente da das cartas, porque uma
oferta de selado não tem condição nenhuma. Hoje 34 dos 85 não têm oferta em
inglês e aparecem a «—».

A lista em disco é o `data/selado_catalogo.json` (vai para o Git: é o catálogo,
não a coleção). Atualiza-se **à mão** com `riftvault selado --sync` — um pedido
por segundo, como o `riftvault prices`, que não foi tocado. Na consola:
`riftvault selado [--edicao VEN] [--so-faltas | --so-tenho]`,
`--mais ID [N]` e `--menos ID [N]`.

## A Venda anterior (apagada a 2026-09-15)

Havia uma quarta secção, «Venda», com o excedente da caixa e uma análise das
comuns e incomuns mais caras. **Não é a de hoje**: aquela era uma *sugestão*
calculada pelo riftvault (o que sobra acima do alvo) e essa pergunta vive hoje
no separador **A mais**. *"Esquece a parte da venda, podes apagar para já,
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
cartas graded, alteradas ou assinadas. Prefere-se a oferta não foil. A língua
é o `precos.linguas` do `riftvault_config.json` (*"apenas cartas versao
ingles"*, 2026-09-15) e filtra-se na recolha — só as ofertas nessas línguas
entram no preço e nas contagens da oferta.

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

### Montado ou desmontado (2026-09-24)

Frase tua: *"vamos desmontar os decks todos com excepcao da LeBlanc, vou
colocar tudo nos binders das edicoes e depois voltar a montar deck a deck e
assim conseguir perceber o que tenho e nao tenho"*.

`decks.montados` no config é a lista dos decks **montados** (o slug ou o
`Nome:`, como a `decks.ordem`). Hoje é `["LeBlanc Hook"]`: os outros cinco
estão desmontados.

Um deck **desmontado não consome nada da Coleção**: não aparece na grelha como
uso («Azir 3»), não entra na alocação, não gera libertadas no «A mais», não
entra no «falta comprar aos decks», nas Staples nem no «falta encomendar». A
Coleção dá **exactamente os mesmos números que daria se o `.txt` não
existisse** — há um teste que fotografa níveis, denominador, wantlists, valor,
Faltas, Encomendas, o painel e a grelha e exige que sejam iguais.

A lista dele **continua a ver-se**, e a página mostra a **simulação** de o
montar a seguir aos que estão montados: o que sairia da Coleção e o que
faltaria. A simulação não consome — dois decks desmontados podem «contar» a
mesma cópia, e é isso que a pergunta *«e se montasse este agora?»* quer dizer.

Muda-se no botão **Montar/Desmontar** da página do deck (que escreve no
`riftvault_config.json`, sem reformatar o resto do ficheiro) ou com
`riftvault decks --montar SLUG` / `--desmontar SLUG`. **Sem a chave, todos
montados**; a lista **vazia** é «nenhum montado» — são coisas diferentes, e
desmontar o último escreve `[]`.

### A regra de raridade: o que devia ser cópia própria (2026-09-24)

Frase tua: *"vou tentar ao maximo que cartas de raridade Rara para baixo
fiquem alocadas exclusivamente a coleccao e as repetidas exclusivamente aos
decks, para nao ter que mexer na coleccao. apenas miticas para acima devo ter
que usar as da coleccao"*.

No Riftbound **não há «mítica»**: a escada do catálogo é `common < uncommon <
rare < epic < showcase`, por isso «Rara para baixo» são as comuns, incomuns e
raras, e «míticas para cima» são as `epic` e as `showcase`.

`decks.coleccao_so_a_partir_de: "epic"`: dessa raridade **para cima** um deck
serve-se da Coleção sem aviso; **abaixo** dela, a cópia devia vir das **cópias
próprias do deck**. **Não bloqueia nada — marca**: a alocação é exactamente a
mesma, e o que muda é que a carta leva um aviso (moldura dourada e «N da
Coleção — é rare: devia ser própria do deck») e o deck um contador «**N** da
Coleção que não deviam». `null` desliga o aviso.

### Montar este deck, carta a carta (2026-09-24)

Na página de cada deck, por baixo do cabeçalho, uma tabela para ele montar o
deck com as cartas na mão: uma linha por carta — **precisa / próprias /
deck+binder / Coleção / falta** —, somada por carta (2 Sabotage no main e 1 no
sideboard são 3 Sabotage), **ordenada pelo que falta primeiro**, depois pelo
que tem de ir buscar à Coleção, e no fim o que já está. O `!` é a regra de
raridade. Abre fechada quando não falta nada; num telemóvel cada linha passa a
cartão, com o rótulo de cada número à esquerda. Também está no `riftvault deck
<slug>`.

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

**A ordem dos decks escreve-se no config** (2026-09-21): `decks.ordem` no
`riftvault_config.json` é a lista dos decks — o slug (o nome do ficheiro sem
`.txt`) ou o `Nome:` de cada um —, e a posição é a prioridade: o primeiro é o
principal. Para reordenar, muda-se a lista; para juntar um deck, mete-se o
`.txt` em `decks/` e o nome no fim da lista. O que a lista não nomear vem a
seguir, pela ordem que tinha; um nome sem deck é ignorado com aviso no
`riftvault decks`. Enquanto a lista existir, os botões **Tornar principal /
Subir / Descer** do site e o `--order` ficam desligados (a importação
seguinte repunha a lista e o clique era mentira). Com a lista vazia volta a
valer a prioridade guardada na base, e aí sim:

```bash
py -m riftvault decks --order azir,ornn   # o primeiro passa a principal
py -m riftvault deck azir --onde          # detalhe, com as impressões a usar
py -m riftvault shopping --deck azir --csv faltas.csv
```

Para **apagar** um deck, apaga o `.txt` — o site atualiza-se sozinho. Para
**trocar os decks todos de uma vez** e não ficar com a lista velha registada
como «libertadas» no A mais, `py -m riftvault decks --recomecar-registo`
apaga o `deck_need_log` e recomeça-o com os decks de hoje.

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
riftvault decks [--order azir,ornn] [--recomecar-registo]  # decks e alocação (a ordem vem de decks.ordem)
riftvault deck azir [--onde]                      # detalhe de um deck
riftvault shopping [--deck azir] [--csv f.csv]    # o que falta comprar
riftvault a-subir [--cardmarket] [--todas]        # master set: a subir / tudo
riftvault local [...]                             # onde está cada cópia
riftvault map / prices / value                    # CardTrader
riftvault seguir [--jogador NOME] [--so-mudados]  # decks dos jogadores seguidos: o que falta
riftvault venda [--juntar REF N] [--trend REF EUR] [--vender --sim]  # a venda em curso e a conta
riftvault selado [--sync] [--mais ID N] [--edicao VEN] [--so-faltas]  # produto selado: o que há e o que tens
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
  venda.py        a venda em curso e a conta (preços: o Trend do Cardmarket, à mão)
  selado.py       produto selado: o que há (CardTrader), o que tens e o que não tens
  server.py       modo edição (Flask)
  build.py        modo publicado (estático)
  cli.py          linha de comandos
  web/            index.html + app.js + style.css — o MESMO nos dois modos
                  (a casca — barra lateral, cabeçalho, rotas — sai da tabela
                   NAV do app.js; os tokens da marca do topo do style.css)
data/
  vault.db        a coleção e os decks. VAI para o Git. Só tu escreves.
  prices.db       histórico de preços. VAI para o Git. Só o robô escreve.
  catalog.db      cache do catálogo. NÃO vai (está no .gitignore).
  selado_catalogo.json  o produto selado que EXISTE, do CardTrader. VAI para o
                  Git (é catálogo, não coleção); `riftvault selado --sync`.
  images/         cache das imagens. NÃO vai.
  seguir/         estado.json (os decks seguidos; VAI) e paginas/ (HTML lido; NÃO vai)
decks/            listas de deck em .txt
docs/             spec da API e snapshot do catálogo, para referência
```

O contexto todo — incluindo as armadilhas da API e o que ainda não foi
validado — está no [CLAUDE.md](CLAUDE.md).

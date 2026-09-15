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

- **Ordem:** três blocos seguidos, nunca intercalados. Primeiro a **sequência
  do master set**, por número de coleção; depois **as runas especiais, 1 de
  cada**; depois **as artes alternativas, 1 de cada**. Os três contam para a
  percentagem. Só no fim vem o que está **fora da coleção** — os tokens (código
  `-T`), as signatures (código `*`), as **sobrenumeradas** (as «300/298») e as
  **promos** (`VEN-SP4`) —, cada um com o seu contador e a dizer que **não**
  entra na percentagem. O contador diz «tens N de M» (impressões de que tens
  pelo menos uma cópia) e, quando o bloco pede playset, «· K no playset
  completo» a seguir (2026-09-15: o número sozinho lia-se como «não tens
  nenhuma»).
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

Quarta secção (15/09/2026, fim da tarde): **o que falta, por edição, em três
blocos** — *"quero as faltas por edicao e dividido em 3 partes / Masterset /
Alt Art / OverNumbered"*. Não é o separador antigo (esse era por raridade e
passou a ser o «Quanto custa»); é uma secção própria, com a **carta em
imagem** e o crachá a dizer **quantas faltam**.

- Um botão por edição (o OGS entra) e «Todas», cada edição com **Master set**
  (a sequência, alvo do tipo — Unit/Spell/Gear 3, Legend e Battlefield 1,
  runas numeradas 3), **Alt Art** (as artes alternativas, playset — as das
  runas do OGN incluídas) e **OverNumbered** (as sobrenumeradas, 1 de cada).
  Cada bloco diz quantas faltam e quanto custa fechar; a edição soma os três.
- **O que vem a caminho conta.** Uma carta já encomendada aparece a azul
  tracejado, «a caminho», e **não soma** ao que há a comprar; uma parcialmente
  coberta diz «1 a caminho · 2 por comprar».
- **Ver não é comprar.** Só o **Master set** entra na wantlist do fim de cada
  edição, na «Wantlist — tudo» e no texto do Cardmarket; Alt Art e
  OverNumbered são para **ver** quantas faltam (*"apenas pedi para ser feito
  track de playset para eu saber exatamente quantas tenho"*). O cabeçalho
  diz as duas contas — «fechar os três blocos» e «a comprar». Para os meter
  nas compras é **uma linha** no config: `listas_de_compra.so_master_set:
  false` (a mesma que manda nas wantlists).
- As promos `VEN-SP` **não estão** em nenhum dos três blocos (ele nomeou
  três); o rodapé diz quantas ficaram de fora.

`api/faltas_edicao.json`; na consola, `py -m riftvault faltas [--edicao OGN]`.
A conta é a **mesma** da wantlist (`a_subir.masterset` + os locais + o
pendente) — não há segunda implementação, só outra arrumação.

**As faltas dos decks não estão aqui.** As do master set estão também na
**wantlist do fim de cada edição** da Coleção (`api/wantlist.json`) e as dos
decks nas abas do separador **Decks**, a seguir às Encomendas
(`api/compras.json`):

- **Decks → Staples** — cartas que **mais do que um deck** pede e que não tens em
  número suficiente. São as que rendem mais por euro: uma compra serve vários
  decks. Cada tile diz quantos decks a querem e quais.
- **Decks → Por deck** — o que falta a cada deck, agrupado por edição.
- **Decks → Pimp decks** — as versões **alteradas** das cartas que os teus decks usam:
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
- **Decks → Encomendas** — o que já compraste e ainda não chegou, para que
  deck vai, e o que ainda falta encomendar. Não conta na Coleção (essa mede o
  que tens na caixa) mas já sai das faltas e das wantlists, para não comprares
  duas vezes. Quando chegar, carrega em **Chegou** na linha (ou em "Chegou
  tudo") e ela passa para a Coleção. Também dá pela linha de comandos:
  `py -m riftvault encomendas` e `py -m riftvault pending --chegou [ID]`.

A aba **A subir** (do master set, o que ainda não tens e subiu 10% ou mais
nos últimos 30 dias) saiu do site com o separador; a conta continua na
consola, `py -m riftvault a-subir [--cardmarket]`, com as mesmas exclusões
(`a_subir.excluir`) e a mesma regra de «ainda não tenho».

**As runas não entram nas abas dos decks** (Staples, Por deck e as wantlists)
— são baratas e compram-se a granel, e a 12 por deck enchiam os staples.
Continuam a contar na secção Decks, na Coleção e no `riftvault a-subir`, que
mede o master set e não os decks. O que fica de fora está em
`faltas_ignorar_tipos`, no config.

**Os decks que pedem a mesma carta compram o que a Coleção não chega para
todos** (11/09/2026). Cinco decks a pedir 3 Defy com 3 na Coleção são 12 Defy a
comprar — já não se «trocam entre decks»; o teto do playset que havia até
essa data ficou revogado. Cada carta mostra o que os decks pedem ao todo.

A carência aqui é **global** — soma-se o que todos os decks pedem e desconta-se
o que tens — e dá a mesma soma que a secção Decks: a alocação por prioridade
diz quem fica com o quê, e o que sobra por deck é o que esse deck compra.

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
(`a_subir.master_faltas`), cortada por edição: os mesmos alvos dos três blocos (playset na sequência, 1 por runa, 1 por
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

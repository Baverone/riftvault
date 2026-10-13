# Revisão do site e propostas — 2026-10-13

Pedido do André: «faz revisão ao site e testa, propõe melhorias e procura por
novas features que consideres importantes». Tudo o que é número aqui foi medido
hoje, no site publicado, com o comando ou o script ao lado. O que vem de leitura
externa está marcado com a fonte.

---

## 1. O que testei, e o que o site aguentou

**O portão**: `py tools\portao.py suite` → **VERDE: 84 ficheiros, 2724 testes,
0 vermelhos**, 1092 s, HEAD `8724dd17`.

**O site publicado**, medido no browser com `performance.getEntriesByType`:

| | medido |
|---|---|
| DOMContentLoaded | **486 ms** |
| load | **542 ms** |
| pedidos | 40 |
| transferido | **209,7 KB** (app.js 109,6 · faltas_edicao.json 34,1 · style.css 26,6) |
| nós no DOM (uma edição) | 4 889 |
| desenhar «Todas» (1122 impressões) | **1 168 ms**, 18 930 nós |
| reflow forçado | 0 ms |

**Acessibilidade**, calculada contra o fundo REAL de cada elemento (subindo a
árvore até um fundo opaco, que é onde o teste ingénuo se engana): **1 elemento
abaixo do WCAG AA em toda a página**, e é a letra do logótipo, que está num
gradiente que o teste não lê. Na prática, **zero**.

A folha de estilo tem **9 breakpoints** (359, 559, 560, 699, 899 / 620, 900,
1000), `prefers-reduced-motion`, folha de impressão, e
`meta viewport width=device-width, viewport-fit=cover`. Há caixa de pesquisa
(«Procurar carta ou código…»). Sem overflow horizontal.

**Três coisas que eu ia escrever e que a medição desmentiu**, e ficam escritas
porque a lição é a medição: (1) «o site congela o browser» — não congela, o que
rebenta é o `Page.captureScreenshot` numa página de 45 mil píxeis; (2) «não tem
pesquisa» — tem; (3) «há texto com contraste de 1,14» — há, mas é texto escuro
dentro de um crachá colorido, e o crachá é que é o fundo.

---

## 2. O que encontrei de errado

### 2.1 A página é alta demais, e isso é o problema de uso que sobra
`#colecao/all` tem **45 586 píxeis de altura** — cerca de 65 ecrãs. Uma edição
sozinha (VEN) são **12 407 px**, uns 17 ecrãs. Não é lentidão: é que para ver a
última carta da lista há que atravessar tudo. Com a Radiance a entrar a 23/10
(167 cartas + 66 showcase), isto piora ~15 %.

### 2.2 Oito alvos de toque abaixo de 32 px
Medido: 8 elementos clicáveis com menos de 32 px de altura, entre eles o «Início»
da barra lateral (18 px) e os links do rodapé (14 px). No rato não se nota; no
telemóvel nota-se.

### 2.3 A página de entrada publica o valor em euros de cada pessoa
`rift.baverone.com` mostra, sem sessão nenhuma: André 8 328,60 €, Gonçalves
921,79 €, Miguel 216,81 €. Se foi escolha de cada um, está certo e não se mexe.
Se o modo de privacidade de alguém for `sem-valores`, isto é uma fuga — e não
confirmei qual é o modo de cada um.

### 2.4 Trabalho feito que ficou parado
O ramo `ai-pc/colar-regra-do-main-2026-10-05` estava pronto desde 5/10 — 4
commits, correcção no `cli.py`, no `colar.py` e no `app.js`, mais
`tests/test_colar_regra_do_main.py` com 393 linhas — e **ficou oito dias por
juntar**. É a correcção do resumo que fazia uma lista legal de 40 cartas parecer
uma carta curta.

### 2.5 As rondas automáticas não estão a fazer o trabalho
- A **ronda diária** disparou todas as noites (a última a 13/10 às 01:52, 30
  minutos, com sucesso) e, em **oito noites**, produziu **zero commits** e
  **zero relatórios**. O último `docs/relatorio-*.md` é de 04/10. O guião manda
  escrever um por noite.
- A **ronda semanal de melhorias nunca disparou**: não tem `last_fired_at` e o
  próximo agendamento já saltou para 18/10. A de 11/10 não aconteceu — é por
  isso que nunca viste propostas nenhumas.

Desde 05/10 o riftvault tem **9 commits, todos automáticos** (preços e site), e
o ai-pc tem **1**.

---

## 3. O que já está construído e não está a ser usado

| | estado |
|---|---|
| `prices.db` · `price_history(printing_id, day, price_cents)` | **38 dias**, de 31/08 a 12/10, 6 826 linhas — e não há um único gráfico no site |
| `copy_locations(printing_id, location, qty)` | tabela criada, **0 linhas** — o «onde está a carta» está feito e por estrear |
| `cardmarket_trend`, `sale_lines` | criadas, 0 linhas |

---

## 4. Propostas, por valor a dividir pelo esforço

### P1 — O gráfico de valor da colecção (os dados já cá estão)
38 dias de preço por impressão em `price_history`. Falta uma tabela de total
diário e um gráfico. **A parte que separa um gráfico honesto de um que mente**:
marcar no eixo os dias em que entraram ou saíram cartas, senão não se distingue
«a carta subiu» de «comprei mais três» (ideia do MythicHub, lida a 13/10). E
distinguir o valor guardado do calculado ao vivo.

### P2 — A Radiance (RAD) entra a 23/10, e a lista de cartas sai a 16/10
Dez dias. 167 cartas colecionáveis + **66 showcase**. Traz categorias que o
riftvault hoje não separa: **Special Alt** (série K/DA) é diferente de **Alt
Art**, e há **Overnumbered com assinatura de artista**, que é subvariante das
Overnumbered. Há ainda uma **Ultimate Rare a 0,025 % dos pacotes**
(`Packed Amphitheater`) — se essa entrar na lista de faltas do master set como
se fosse comprável, estraga o total em euros de toda a gente. E as promos de
evento (Heimerdinger de Pre-Rift, pacotes Nexus Nights) não são de edição
nenhuma: precisam de gaveta própria. (playriftbound.com, 25/09/2026; wiki do
League, lida 13/10/2026 — a wiki diz 26/10 e a Riot diz 23/10, não resolvi.)

### P3 — Segunda fonte de preços, de graça: a API do RiftHunt
`api.rifthunt.com`, sem chave, sem quota, 1432 impressões em 9 sets,
`/bulk/prices` com 1423 linhas actualizadas diariamente, normal e foil
separados. Hoje os preços vêm só do CardTrader. Uma segunda fonte apanha o dia
em que uma delas se engana, e cobre variantes. (rifthunt.com/api, lido
13/10/2026; pedem < 10 req/s e User-Agent descritivo.)

### P4 — «O que mexeu esta semana»
Com o histórico de P1: uma coluna de variação por carta (dia/semana/mês), em
percentagem e em euros, ordenável. É a ferramenta para decidir o que vender da
pilha «a mais» — 192 cópias hoje, 7 455,89 €.

### P5 — Trocas e empréstimos entre os três
Foi o buraco do mercado inteiro: de todas as aplicações que o levantamento
cobriu, **só uma** (MTG Trades, iOS) tem empréstimos, e o Deckbox **desistiu**
do cruzamento automático de trocas por dar ruído em vez de decisões. Vocês são
três no mesmo site, com as colecções todas na mesma máquina: a intersecção
«o que lhe falta ∩ o que eu tenho a mais» é barata de calcular e, ao contrário
do Deckbox, pode ser cortada no top N por valor. O detalhe que o MTG Trades faz
bem: guardar o **preço da altura** da troca, senão o histórico fica a parecer
um erro dois anos depois.

### P6 — Estrear o `copy_locations`
A tabela existe e está vazia. Para uma colecção de 3 359 cópias, saber em que
binder está a carta é o trabalho verdadeiro quando se vai montar um deck.

### P7 — Legalidade por edição
A rotação de Standard está planeada para **2028** e já há **13 cartas banidas**
(Ekko Recurrent e Stacked Deck entraram a 18/09). Um campo de legalidade por
edição custa pouco agora e muito depois. (playriftbound.com/rules-hub, lido
13/10/2026.)

### P8 — Altura da página (o ponto 2.1)
Paginação ou carregamento à medida no separador «Todas», e o filtro a ficar
colado ao topo. Não é performance: é não ter de atravessar 65 ecrãs.

---

## 5. O que NÃO proponho, e porquê
- **Reescrever o site para ser mais rápido**: 542 ms e 210 KB. Não há problema
  para resolver.
- **Optimizador de compras à Cardmarket**: a optimização real precisa da oferta
  por vendedor, que a Cardmarket não dá de graça. O que se pode fazer é partir
  as faltas em lotes que façam sentido como uma encomenda só.
- **Reconhecimento de carta por câmara para registar na colecção**: o leitor de
  imagem já existe para decklists; apontá-lo à entrada de colecção é trabalho a
  sério e o ganho só aparece com uma pilha de cartas na mão.

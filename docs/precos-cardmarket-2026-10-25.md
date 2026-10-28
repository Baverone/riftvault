# Os preços do Cardmarket — o que o `cmPrice` é, e de onde vem o Trend (2026-10-25)

Pedido do André: *"preciso que estejas constantemente a atulizar o Price Trend do
market, principalmente de Radiance, pois vou abrir muitos boosters e vou vender
cartas [...] podes criar Excel para servir de base de dados e ires atualizando os
precos"*.

## 1. O `cmPrice` da dotgg é a MÉDIA DE 1 DIA, não o Price Trend

**Medido de duas maneiras, no mesmo dia.**

### a) Contra o price guide oficial do Cardmarket, carta a carta (todas)

O Cardmarket publica um ficheiro de download diário por jogo
(`downloads.s3.cardmarket.com/productCatalog/priceGuide/price_guide_22.json`, o
Riftbound é o jogo **22**, 1862 produtos, `createdAt 2026-10-25T02:47:35+0200`),
com `avg`, `low`, `trend`, `avg1`, `avg7`, `avg30` e os mesmos `-foil`. Comparados
com os `cmPrice`/`cmFoilPrice` da dotgg pelo `cmid`:

| a dotgg bate ao cêntimo com… | normal (1633) | foil (1577) |
|---|---|---|
| **`avg1` (média de 1 dia)** | **1429** | **1559** |
| `trend` (Price Trend) | 190 | 96 |
| `low` (From) | 356 | 43 |
| `avg7` | 130 | 75 |
| `avg30` | 106 | 64 |

(As contagens sobrepõem-se: um preço pode bater com dois campos.) Quando o `avg1`
não existe, a dotgg cai para o `low` (Angler Wyrm, RAD-113: 1,75 €).

### b) Contra a página da carta, aberta no Chrome (10 leituras)

| carta | dotgg `cmPrice` | Trend (página) | média 30 d | média 7 d | média 1 d | guia `avg1` | guia `trend` |
|---|---|---|---|---|---|---|---|
| Abandon UNL-131 | 0,39 | 0,42 | 0,39 | 0,42 | 0,46 | 0,39 | 0,42 |
| Abandon UNL-131 **foil** | 1,99 | 2,07 | 2,32 | 2,14 | 1,65 | 1,99 | 2,12 |
| Amateur Demolitionist RAD-001 | 0,09 | 0,03 | 0,16 | 0,14 | 0,09 | 0,09 | 0,06 |
| Amateur Demolitionist RAD-001 **foil** | 0,27 | 0,32 | 0,26 | 0,26 | 0,30 | 0,27 | 0,30 |
| An Offer You Can't Refuse RAD-101 | 0,31 | 0,31 | 0,42 | 0,40 | 0,32 | 0,31 | 0,31 |
| Angler Wyrm RAD-113 (só foil) | 1,75 | **2,99** | 3,64 | 3,63 | 2,95 | — (`low` 1,75) | `trend-foil` **2,99** |
| Ahri, Inquisitive OGN-119 (só foil) | 8,00 | **4,58** | 4,59 | 4,49 | 5,57 | 8,00 | `trend-foil` 4,45 |
| Ambessa VEN-196 (só foil) | 95,00 | **60,61** | 73,94 | 61,10 | 60,00 | 95 | `trend-foil` **60,61** |

Duas conclusões:

1. **O `cmPrice` é a média de 1 dia do guia** — a página, aberta horas depois,
   já mostra uma média de 1 dia mais nova; o guia é a fotografia das 02:47.
   O 0,39 do Abandon coincidia com a média de 30 dias por acaso.
2. **Numa carta que só existe em foil, a página mostra os números do FOIL** — e o
   `cmPrice` da dotgg é um número do lado normal que a página nem mostra
   (Ambessa: 95,00 € contra o Trend de 60,61 €).

**Por isso o riftvault não usa o `cmPrice` da dotgg.** O Trend vem do guia
oficial; a dotgg serve para ligar cada impressão ao produto do Cardmarket (`cmid`,
`cmurl`) e dá o preço do outro mercado em dólares.

O Cardmarket (as páginas) não se leu por programa: as 10 leituras foram no Chrome
do André, à mão, e o desafio anti-bot passou sozinho. O guia é um ficheiro de
download — um pedido por dia.

## 2. O que fica guardado (`data/prices.db`)

| tabela | o quê |
|---|---|
| `cardmarket_price_history` | uma linha por impressão e por DIA (mesmo sem mudança): trend, From, médias 1/7/30, normal e foil, e o outro mercado em cêntimos de dólar |
| `cardmarket_ligacao` | a ligação de cada impressão ao produto do Cardmarket (o `cmid`, o URL, `has_normal`) — à parte porque não muda de dia para dia |
| `cardmarket_dia` | um registo por dia: a hora do guia e de onde veio a ligação |

**Crescimento medido:** o primeiro dia (com a ligação) +184 KB; cada dia a mais
**~75 KB** (1439 linhas), ou seja ~27 MB por ano num ficheiro que vai para o Git
todos os dias. A primeira versão (tudo numa linha) crescia 320 KB por dia.

## 3. Os números de 25/10 (cópia do `data/` real)

- catálogo: **1421 impressões**; com linha do Cardmarket **1407**; com preço de
  referência (o Trend que a página mostra) **1399**;
- **RAD: 232 impressões, 226 com linha, 218 com preço**;
- **sem preço nenhum: 22** — 14 sem produto no Cardmarket (os tokens `UNL-T01..T08`,
  `VEN-T04`, `RAD-T02/T06`, as promos de evento `RAD-0xx-P`) e 8 com produto mas
  sem Trend (quatro assinadas da RAD, duas do VEN, `RAD-045` e `RAD-045a`);
- **valor da Coleção** (as mesmas cópias que o site conta): **10 686,47 €** pelo
  Trend do Cardmarket contra **11 646,85 €** pelo CardTrader (o do site) —
  **−960,38 € (−8,2 %)**; 6 cópias em 6 impressões sem Trend ficam fora do
  primeiro total. Quase toda a diferença vem das cartas caras (Baron Nashor
  1 793,84 € contra 2 100,64 €; Ahri SFD-227 471,76 € contra 590,64 €; os Poros).

## 4. O Excel

`precos/riftvault-precos-AAAA-MM-DD.xlsx` e `precos/riftvault-precos.xlsx` (o
mesmo, nome fixo), na raiz do projecto, fora do Git. Folhas: **Leia-me**,
**Radiance**, **Tudo**, **O que tenho**, **A subir - a descer**. Gerado pelo
`riftvault cardmarket --excel` e todos os dias pela `riftvault-daily`.

**O EXCEL É GERADO, NUNCA EDITADO À MÃO.** A base de dados continua a ser o
`prices.db` e o `vault.db` — se o Excel passar a ser editável, passam a existir
duas verdades e elas divergem na primeira semana (foi o que nos custou dois dias
com o catálogo). O Excel é uma VISTA, regenerada todos os dias e sempre que ele
pedir, com a data e a hora lá dentro.

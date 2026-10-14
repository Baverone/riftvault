# Plano de teste e fundamentals — Riftbound e Magic

Escrito a 13/10/2026; as quatro decisões dele estão na secção 10 e já estão
aplicadas no resto do documento (14/10/2026). Tudo o que é regra oficial,
opinião de autor ou cálculo meu está marcado. As fontes estão no fim de cada secção, com data. O que não
verifiquei está na secção 9 — e não aparece como se fosse certo em mais nenhum
sítio deste documento.

---

## 0. A tua intuição, corrigida

Disseste: «quero começar a ter metas de jogos para conseguir começar a meter
repetições, penso que seja uma boa forma de testar». Metade disto está certa e
a outra metade é a forma mais comum de desperdiçar tempo de teste.

**As repetições são a parte certa.** **A meta em número de jogos é a parte
errada** — não porque sejam poucos jogos, mas porque jogos não respondem à
pergunta que normalmente se lhes faz.

O número que mostra isto: um resultado de **13-7** (65%) é compatível com o
matchup ser na verdade **41%** (desvantagem real) ou **85%**. Vinte jogos não
distinguem «esmaga» de «moeda ao ar». Até 15-5 deixa 50,9% dentro do intervalo.

O mesmo cálculo visto do outro lado, e é aqui que ele passa a ser útil: um
problema que aconteça em **10% dos jogos** aparece duas ou mais vezes em 20
jogos com **87,8%** de probabilidade. Em 15% dos jogos, **96,1%**.

Ou seja: **20 jogos são um detector de problemas, não um medidor de win rate.**
Uma carta que fica morta na mão, uma mão que te arrependes de ter ficado, um
erro de sequência que repetes, um padrão de falta de recurso — isso vê-se em 20
jogos. Uma diferença de 5 pontos de win rate precisa de **3 130 jogos** e nunca
vais lá chegar; correr atrás dela é o buraco onde o tempo desaparece.

**Daí a regra que atravessa este plano todo: cada bloco de repetições tem uma
pergunta escrita antes de começar, e a conclusão responde a essa pergunta e a
mais nenhuma.** Nunca se escreve uma percentagem de matchup a partir de dez ou
vinte jogos. Escreve-se: apertado / desequilibrado / atropelo, e quais foram os
dois ou três problemas que se repetiram.

E a segunda regra, que é a mais contra-intuitiva: **conta-se drills, não só
jogos.** Os cinco critérios de prática deliberada (Ericsson) exigem objectivo
bem definido, execução autónoma, **feedback imediato e informativo**,
repetição da mesma tarefa, e orientação. Jogar um match falha três deles —
não tem objectivo único, o feedback é tardio e confundido pela variância (às
vezes perdes jogos que jogaste bem) e não tem professor. Um drill de
mulligan com resposta publicada cumpre os cinco. Isto é a minha leitura dos
critérios aplicada a cartas, não um estudo sobre jogos de cartas — mas é o
raciocínio que faz o plano ter drills e não só jogos.

> Fontes: Karsten, «Magic Math: How Many Games do You Need for Statistical
> Significance in Playtesting?» (ChannelFireball, anunciado 01/08/2018) —
> ±10% exige ~100 jogos, ±5% ~400, 7-3 dá intervalo 34,8%–93,3%, p=0,172.
> Os intervalos de 13-7 e 15-5 e as probabilidades de detecção são cálculo meu,
> pelo método exacto (Clopper–Pearson), reproduzindo os números publicados do
> Karsten. Critérios de prática deliberada: Ericsson, resposta a Macnamara &
> Hambrick, *Psychological Research* (2020), doi:10.1007/s00426-020-01368-3.

---

## 1. Riftbound: os fundamentals (e o que tens de desaprender do Magic)

### 1.1 Energia renova-se, Power sacrifica-se

Canalizas **2 runas por turno** (o segundo jogador canaliza 3 no seu primeiro
turno). Cada runa faz **um trabalho por turno**: ou exausta para **1 Energia**
— e volta a estar pronta no teu Awaken seguinte — ou **recicla para 1 Power**,
e vai para o fundo do Rune Deck, fora durante vários turnos. Deck de runas: 12,
sempre separado. Isso dá um tecto de rampa de **6 turnos**.

A tradução para quem vem do Magic: **Energia é destapar terrenos, Power é
sacrificar um terreno.** Não há mana screw nem land drops, por isso o «erro de
curva» aqui não é ficar sem terra — é **gastar Power a mais, cedo**, e ficar
três turnos depois com o depósito pequeno. A comunidade converge em que **cerca
de 2/3 do deck deve ser jogável só com Energia**; uma carta de 4 Energia + 1
Power consome **cinco** runas num só turno.

A linha de fundamentals mais afiada que encontrei: **acabar o turno com 0
Energia anuncia ao adversário que não podes responder, e convida-o a atacar.**
E o inverso é o teu maior ganho: como a Energia se renova, ficar com runas
abertas é **quase gratuito**, portanto um adversário competente está quase
sempre a representar algo.

Não existe consenso numérico sobre «quanto Power é demasiado». Qualquer guia que
te diga quantas runas deves canalizar por turno está errado — canalizar não é
uma escolha, são 2 automáticas. A decisão é **quantas reciclas**.

### 1.2 O jogo é um tabuleiro que se comporta como corrida

Ganha-se com **8 pontos**, e num duelo só há **2 battlefields** em jogo. Ganhas
ponto ao **conquistar** (mover para um battlefield livre, ou ficar o único lado
com unidades depois de um showdown) e ao **manter** (1 ponto por battlefield
controlado, no teu Beginning phase). Cada battlefield pontua **uma vez por
turno**. O máximo prático é **2 pontos por turno** — logo o relógio teórico mais
rápido é de **4 turnos**.

A consequência que desfaz os instintos de Magic: **não existe «estabilizar e
ganhar mais tarde»**. Estabilizar a 0 pontos por turno perde contra quem faz 1.
Cada turno em que não pontuas é um turno perdido para sempre. O exemplo que a
comunidade usa: um jogador com 5 cartas na mão e 4 pontos perde contra um com 0
cartas e 8 pontos.

E às vezes **dás um battlefield de propósito** — quando já estás à frente nos
pontos, quando o deck dele te moe no longo prazo, ou quando aquele battlefield
não importa.

### 1.3 Combate: não há dano a picar

Num showdown somam-se os Might dos dois lados, o dano é **simultâneo**, o dano
letal tem de ser atribuído a uma unidade antes de passar à seguinte (**TANK
primeiro**), e no fim **todos os sobreviventes curam por completo**. Se só
sobreviverem atacantes, conquistam e pontuam; se sobreviver **qualquer**
defensor, não há conquista e os atacantes voltam à base. O controlo **não muda
durante** o showdown, só depois.

Logo: **não existe dano a picar.** Cada battlefield é tudo-ou-nada por turno.
Trocar dano «quase letal» não serve de nada.

Erros de principiante que as fontes nomeiam: mandar tudo a um battlefield (em
vez de atacar com **uma** unidade, ganhar o showdown e só depois mover as
outras); desenvolver antes de agir (começa o showdown com as runas ainda em pé);
e não resolver o draw antes de se comprometer.

### 1.4 Focus: a prioridade é a habilidade distintiva

No máximo um jogador tem **Focus** — a permissão de agir enquanto o turno está
em Showdown Open State. Quem contestou o battlefield ganha Focus primeiro;
passar prioridade **não** perde o Focus; quando a corrente fecha, o Focus passa
ao jogador seguinte; se todos passarem sem jogar nada, o showdown fecha.
**ACTION** joga-se em showdowns, **REACTION** também com a corrente aberta (e
resolve antes do que já lá está), e as habilidades de runa **não podem ser
respondidas**.

**O drill que isto pede** (desenho meu, não vem de fonte): antes de cada
showdown, dizer em voz alta (i) quantas runas ele tem abertas, (ii) qual é a
Reaction mais barata nas cores dele que ganha à minha linha, (iii) se consigo
ganhar o showdown **através** dessa carta. É o equivalente a «jogar a contar com
o Counterspell», mas dispara várias vezes por turno em vez de uma.

### 1.5 Champion: morre a sério

O Chosen Champion começa fora do deck e da mão, pode ser jogado **a qualquer
momento do teu turno**, e conta como **uma das 40** cartas. Quando morre, vai
para o lixo e **não volta** à Champion Zone. Não é um comandante. Portanto
comporta-se como um recurso de um só uso: joga-se **para ganhar um showdown**,
não para ter presença. O único conselho publicado é **levar cópias extra** (até
3), porque o adversário responde à primeira. Sobre o *timing* não há literatura
nenhuma — é um buraco público, não uma coisa que eu saiba e não esteja a dizer.

### 1.6 O que é fixo na construção

40 cartas no main (Champion incluído) · 1 Champion Legend · **12** runas do
Domain Identity do Legend · **3** battlefields de nomes diferentes ·
**sideboard ≤ 10**, trocas **1-por-1** entre jogos, **nenhuma no jogo 1**,
limite de 3 cópias a contar main+side · o **Champion pode ser trocado** ·
**runas, Legend e battlefields ficam trancados** depois do registo.

E uma regra sem equivalente no Magic: **os battlefields revelam-se antes das
mãos de abertura e dos mulligans.** A revelação é informação viva para a decisão
de mulligan — isso é uma habilidade treinável por si só.

Rácios em que a comunidade converge: metade ou mais do deck em unidades; **7–9
cartas de custo 2** (só as sem Power contam); uma unidade de custo X quando
tiveres X runas; spells sobretudo interacção, com mistura de Actions e
Reactions; **pouco gear**; divisão de runas **6-6** por defeito, 7-5 ou 8-4 se um
Domain carregar o Power, 12-0 se só um tiver Power. Um modelo contado de um
precon: **28 unidades / 10 spells / 2 gear**, com 26 das 40 jogáveis só com
Energia.

> Fontes: Core Rules (PDF, actualizado 09/10/2026) e o booklet oficial de
> instruções para quem já joga TCGs, via <https://playriftbound.com/en-us/rules-hub/>;
> Mobalytics «Beginner Fundamentals» (08/01/2026) e «Deckbuilding Fundamentals»
> (17/07/2026); LearnRiftbound, páginas «Resource System» e «Tempo vs Value»
> (sem data); Mythras, «Riftbound Deckbuilding Basics» (01/08/2026, actualizado
> 10/10/2026); Bausch, «Three Concepts to Master» (Ultimate Guard, 27/04/2026);
> RiftMana, «8 Tips to Improve At Riftbound Quickly» (19/11/2025).

---

## 2. Como se testa: cada técnica responde a uma pergunta

| técnica | pergunta a que responde | repetições | como engana |
|---|---|---|---|
| **Goldfish** (sozinho, sem adversário) | O deck executa? Em quantos turnos fecha? | «várias vezes» e média; ~1 hora para conhecer um deck novo | Não sabe nada do teu win condition. Em Riftbound, sem adversário não há showdown nem pontos — mede curva e mais nada |
| **Drill de mão** (keep/mull) | Os meus keeps estão certos? O deck sobrevive a um mulligan? | É aqui que as repetições são baratas: centenas de mãos | Não ensina keeps pós-sideboard contra um deck conhecido |
| **Duas mãos** (jogar os dois lados) | Como é que o matchup se desenrola? O meu plano de sideboard faz sentido? | Poucos jogos, para aprender | **Viés de informação escondida**: não consegues des-saber a outra mão. Nunca dá percentagens |
| **Gauntlet** (contra os decks do topo) | Que deck devo jogar, dado o campo que espero? | 4 a 6 decks com planos distintos; entre 4-5 e 20 jogos por matchup, segundo quem escreve | Decks estranhos no gauntlet dão resultados falsos; testar brews só uns contra os outros faz perder semanas num deck que não compete |
| **Sideboard** | O que entra e o que sai, contra cada deck? | ~60% dos jogos de torneio são com sideboard; num bloco de 10, **4 pré e 6 pós** | O adversário também faz board, e isso é incerto; resultados pós-board valem menos do que gostarias |
| **Play/draw** | A minha conclusão é um artefacto de quem começou? | Trocar os decks ao jogo 10, 10 de cada lado | Ignorar isto deturpa as decisões de sideboard |
| **Carta A vs carta B** | Esta carta é melhor do que aquela? | **Não tentar abaixo de 75 matches** | O exemplo publicado: **500 matches** para concluir que **não havia diferença** de win rate |

**O que fazer em vez da comparação carta-a-carta:** estados de jogo
fabricados — recuar o jogo, começar com a carta candidata na mão — usados em
poucos jogos, para julgar se a carta importa, nunca para tirar percentagens. E
**mudar uma coisa de cada vez**: nunca a base de mana e o sideboard na mesma
sessão.

**Revisão, que é onde está o maior ganho e o menor custo.** O argumento mais
forte que encontrei a favor de rever **mais tarde** e não no momento: um
jogador avaliou a sua própria actuação num match em **8/10 na altura e 4/10 ao
revê-la dois anos depois**. Tu já tens a infraestrutura montada — fazes lives
com OBS. Um VOD é a revisão.

E o formato da nota de revisão é sempre o mesmo, uma linha: **a decisão que eu
mudava**. Escrita durante o jogo, discutida depois.

**Espaçar em vez de amontoar.** Na meta-análise de prática distribuída, a
recordação média foi **36,7% massificada contra 47,3% espaçada** (271
comparações). Quarenta jogos num sábado é a condição massificada; os mesmos 40
em quatro noites é a espaçada. Cuidado honesto: estes estudos são sobre
retenção de material declarativo — um guia de sideboard é material declarativo,
a tua qualidade de jogo não é. Portanto o que isto sustenta é **auto-quiz
espaçado do guia de sideboard**, não «espaçar melhora o teu jogo».

> Fontes: Moursund (magic.wizards.com, 30/08/2010); Linn (SCG, 18/05/2009);
> Verhey, «Five Trials of Playtesting» (magic.wizards.com, 01/06/2017);
> Lax, «Procedural Playtesting» (SCG, 17/05/2011); Nicastri (SCG, 08/01/2009);
> Jacob (SCG, 08/10/2010); Dougherty (SCG, 20/12/2002); Paskins (SCG,
> 20/04/2004); Sam Black, «How to Playtest» (SCG, 21/12/2017); Ruel (SCG,
> 05/01/2010); Overturf (Quiet Speculation, 14/12/2016); estudo do Punishing
> Fire (modernnexus.com); Robert Lee (MTG Arena Zone, página sem data);
> Cepeda et al., *Psychological Bulletin* 132(3) 2006; Dunlosky et al., 2013.

---

## 3. As ferramentas que existem hoje (e o que custam)

Tudo o que está aqui é **grátis**, como manda a tua regra de 07/09. O que custa
dinheiro está marcado e está fora do plano.

### Riftbound

**Rift Atlas** — <https://play.riftatlas.com/> · «Free to play · No download
required», no browser, feito pela comunidade («Riot Games does not endorse or
sponsor this project»). **Verifiquei a página eu mesmo hoje.** Tem:

- **Quick Match** (fila, Bo1 ou Bo3), **Private Room** (código, até 4 jogadores,
  duelo/2v2), **Solo Room** («testar um deck sozinho ou jogar os dois lados»),
  **Spectate** e **Sealed**.
- **Rewind** (desfaz a última acção), **Auto-pay** (exausta e recicla as runas
  que a carta pede e registra cada pagamento), **prompts de Conquer+Score**, e
  **mostra quem tem o Focus no showdown**.

Esta última é a razão pela qual a ferramenta é melhor do que parece: o §1.4 é a
habilidade mais difícil do jogo e o simulador diz-te, a cada momento, quem tem
a permissão de agir. É um treinador de prioridade.

**E resolve-te um problema que acabaste de criar.** Desmontaste os decks todos
para arrumar nos binders — «Coleção é Coleção e não mexe». No Rift Atlas podes
treinar o Kennen, o Leona e os quatro decks do topo do metagame **sem tocar nas
cartas**. As cartas ficam nas folhas e os jogos fazem-se no browser.

**RiftLite** — <https://www.riftlite.com/> · «Free to start», sem conta
obrigatória, Windows e macOS, versão 0.9.10, também da comunidade e sem aval da
Riot. **Verifiquei eu mesmo hoje.** Segue os matches **automaticamente** a
partir do Rift Atlas e do TCG Arena («no match form and no start-tracking
button»), reconstrói **replays animados incluindo Bo3 completos**, e tem
**revisão de vídeo**: gravar o match, ver até **6×**, pôr marcas, desenhos e
notas de áudio, exportar MP4. Relatórios semanais de metagame — o último de
12/10/2026.

**Fora do plano:** Tabletop Simulator custa 19,99 $ (e as mods de Riftbound
aparecem removidas da Workshop — não confirmei). Pixelborn é incompleto e pode
ser fechado pela Riot. **Não há cliente digital oficial** e não há nenhum
anunciado com data.

### Magic

| | Pioneer | Standard | Premodern · Legacy · Modern · Pauper · cEDH · Duel Commander |
|---|---|---|---|
| **Arena** (grátis) | ✅ formato nativo desde 10/05/2025 (era «Explorer»); as cartas «rebalanceadas» foram revertidas a 22/09/2026, o que tirou a última objecção séria | ✅ | ❌ |
| **MTGO** | ✅ ligas sancionadas | ✅ | ✅ (Legacy só aqui) — **mas obriga a comprar colecção digital: fora da tua regra** |
| **XMage** (grátis, offline, **com IA**) | ✅ | ✅ | ✅ provavelmente — tem «dezenas de formatos», mas **não confirmei** que valide Premodern/Legacy |
| **Cockatrice / Untap.in** (grátis) | ✅ sem validação de regras, precisa de humano (os dois têm modo sozinho) | ✅ | ✅ |
| **ScrollVault / Moxfield / Archidekt** | drills de mão e goldfish | idem | idem |

**A conclusão que decide o teu plano de Magic:** dos teus formatos, **só o
Standard tem adversários grátis a sério** — e tens lá o **4-5C Control**. Se
quiseres a Arena para Pioneer, falta-te construir um deck. Tudo o resto
(Premodern com o **Stiflenought** à frente, Legacy, Modern, Pauper, os dois
Commander) **não tem fornecimento de adversários grátis**: para esses, as metas
são **drills, duas mãos, guias de sideboard escritos e jogos em papel** — nunca
contagens de jogos que não consegues cumprir.

> Fontes: páginas das próprias ferramentas, lidas hoje (13/10/2026);
> «State of the Formats 2026» (magic.wizards.com, 11/09/2026) para o Pioneer na
> Arena e a reversão das cartas rebalanceadas; «Announcing Pioneer»
> (magic.wizards.com, 05/05/2025); MTGO getting-started e eventos construídos
> (mtgo.com, lidos 13/10/2026); XMage (github.com/magefree/mage, versão
> 11/07/2026); Cockatrice 3.1.1 (10/10/2026).

---

## 4. O plano semanal — as metas

**Três a quatro horas por semana, espalhadas por três ou quatro noites**
(escolha tua, 14/10), nunca numa maratona. Pausa a cada 2 matches. Uma segunda
noite de teste só nas duas semanas antes de um evento, se houver um.

| meta da semana | número | pergunta a que responde |
|---|---|---|
| Decisões de mão (keep/mull) | **50** | Os meus keeps estão certos? |
| Goldfishes com contagem de turnos | **10** | O deck executa, e em quantos turnos? |
| Jogos de Riftbound no Rift Atlas, **Quick Match** | **5** (Bo1) | Onde é que eu perco os pontos? |
| Matches de Magic na Arena (Bo3) | **5** (um «evento») | Os meus planos de sideboard aguentam? |
| Revisão escrita | **1 jogo, 1 decisão** | Qual é a decisão que eu mudava? |
| Auto-quiz do guia de sideboard | **1 deck** | Sei o plano de cor, ou só o reconheço? |

**Versão de semana má (~1 hora):** 20 decisões de mão + 2 jogos + 1 revisão
escrita. Isto não é falhar a semana — é o chão, e cumprir o chão durante dois
meses vale mais do que um sábado de 40 jogos.

**Os três drills de Riftbound a sós** (desenho meu; não existe literatura
publicada sobre treino solo deste jogo):

1. **Drill de mulligan com battlefield revelado** — revela um dos teus três
   battlefields ao acaso, só depois decide o keep. Treina a regra do §1.6, que
   não tem equivalente no Magic, e não precisa de adversário.
2. **Drill de curva e Power** — goldfish de 6 turnos, a registar quantas runas
   reciclaste e em que turno é que, pela primeira vez, não conseguiste pagar.
3. **Drill de showdown a duas mãos**, no Solo Room, a usar o indicador de Focus
   para conferir **cada** decisão de passar.

**O que fica escrito em cada bloco** (é o registo que torna 20 jogos úteis):
adversário, quem começou, mulligans, apertado/desequilibrado/atropelo, cartas
que ficaram mortas, carta que ganhou o jogo, e **a decisão que eu mudava**. No
Riftbound o RiftLite já grava quase tudo isto sem tu escreveres nada — e a
razão de preferir a ferramenta ao caderno é conhecida: o modo de falhar
histórico dos cadernos de teste é as pessoas deixarem de os preencher.

---

## 5. O plano por deck — três fases

Para cada deck que queiras levar a sério, por esta ordem. Não se passa à fase
seguinte sem fechar a anterior.

**Fase 1 — conhecer o deck (não precisa de adversário).**
10 goldfishes com contagem de turnos · 50 decisões de mão, **sem mulligar abaixo
de seis no início** para aprenderes como o deck joga, e só depois a testar mãos
pequenas · 10 jogos a duas mãos.
Pergunta: *executa? o que fica morto? os meus keeps?*
Regra que protege o teste: as regras de mulligan do treino são **iguais** às do
torneio. Se um deck mulliga muito, arranja-se o deck, não a regra.

**Fase 2 — conhecer os matchups.**
Um bloco de **10 jogos** contra cada um dos **3 ou 4 decks mais comuns**, com
**4 pré-board e 6 pós-board**, alternando quem começa. Para Riftbound o
gauntlet de hoje é **Kennen** (Order/Chaos) primeiro, e depois **Irelia**
(Calm/Chaos), **Master Yi** (Calm/Body) e **Rengar** (Fury/Body) — as três
fontes com números concordam neste conjunto. Para o Magic, os decks que já
vigias no mtgvault.
Pergunta: *como é que este matchup se ganha, e o que é que eu troco?*
No fim do bloco escreve-se apertado/desequilibrado/atropelo e os problemas
repetidos. **Não se escreve uma percentagem.**

**Fase 3 — fechar.**
Guia de sideboard escrito por matchup, **incluindo as cartas de sideboard que
ele provavelmente tem** · auto-quiz espaçado (três vezes ao longo de duas
semanas, não uma releitura na noite anterior) · e a lista fixada.
Como **não há evento marcado** (decisão tua, 14/10), a regra de trancar o deck
duas semanas antes não se aplica agora — guarda-se para quando houver data. O
que fica no lugar dela é a regra que a substitui bem: **um deck de cada vez até
fechar as três fases**, em vez de saltar de deck a cada sessão má. A estimativa
publicada é que acertar no «melhor» deck vale 2 a 5% — cerca de 1 match em 20 —
enquanto a prática funda com um só deck vale muito mais.

Por deck, isto dá **30 a 40 jogos a sério** mais os drills — que é a ordem de
grandeza que as fontes relatam para alguém com emprego, e muito abaixo das 30
horas que as equipas de 2009 descreviam.

**A linha do «não vale a pena»:** nunca tentar uma comparação carta-a-carta
abaixo de 75 matches. Em vez disso, estado de jogo fabricado e uma justificação
escrita.

**Depois de um evento ao vivo: uma semana sem testar.** Não é preguiça, é a
regra que quem passou por burnout escreveu.

---

## 6. O calendário manda no plano

| data | o que é | o que faz ao plano |
|---|---|---|
| **16/10/2026** | O patch de regras da Radiance entra em vigor (Deploy, Show Off, Disarm; camada própria para efeitos de cópia; **«Pick» = não-alvo** e «Choose» = alvo; **instrução mal-alvejada é *ignorada*** e arrasta as ligadas, a falhada é *negada* e as ligadas tentam) | Esta semana é de **fluência de regras**, não de jogos. A diferença ignorada/negada é uma armadilha para quem vem do «fizzle» do Magic |
| **16–22/10** | Pre-Rifts da Radiance (Sealed) | — |
| **23/10/2026** | **Radiance sai** (167 cartas, 9 Legends novos) e entra no Standard | O metagame actual (Kennen primeiro) é **base de comparação, não alvo** |
| **06–08/11** | Regional Championship europeu, Stuttgart — **Standard já com Radiance** | O metagame roda ~2 semanas depois do lançamento. **Não gastes repetições num gauntlet de Vendetta agora** |
| **09/11 e 14/12** | Summoner Skirmish 1 e 2 (Bo3, competitivo) | Se quiseres um alvo com data, é aqui |
| **29/01/2027** | Set «Legacy»: muda templating («Create» em vez de «Play», «When I enter» em vez de «When you play me») | O que aprenderes sobre triggers de *play* tem data de validade |

**Portanto a ordem das próximas três semanas é esta:** até 23/10, regras novas
+ drills + Rift Atlas a solo; a partir de 23/10, dados novos e só então montar
o gauntlet da fase 2.

---

## 7. Leitura e vídeo, por ordem

Para os fundamentals de Riftbound, nesta ordem:

1. **Booklet oficial de instruções para quem já joga TCGs** (PDF, via o Rules
   Hub) — é o melhor arranque para alguém que vem do Magic: estrutura do turno,
   passos do showdown, pontuação, Legend/Champion e timing de action/reaction em
   poucas páginas. **É da era Origins (© 2025)**: confirma o que for de timing
   nas Core Rules de 09/10/2026.
2. **Core Rules (09/10/2026) + Radiance Patch Notes (09/10/2026)** — o único
   sítio onde se resolve uma dúvida de Focus, corrente ou camadas.
   <https://playriftbound.com/en-us/rules-hub/>
3. **LearnRiftbound**, páginas «Resource System» e «Tempo vs Value» — o melhor
   texto escrito sobre o §1.1 e o §1.2. Fraqueza: **sem datas**.
4. **Mobalytics**, «Beginner Fundamentals» (08/01/2026) e «Deckbuilding
   Fundamentals» (17/07/2026) — a secção «Good Habits & Precautions» é pura
   tomada de decisão.
5. **Mythras, «Riftbound Deckbuilding Basics»** (01/08/2026, act. 10/10/2026) —
   o guia mais quantitativo: tabela de runas por turno, modelo de 40 cartas
   contado, matemática dos pips de Power. **Tem um erro conhecido** (ver §9).
6. **Hextech Analytics** — snapshots de metagame datados e com metodologia
   declarada. É daqui que sai o gauntlet.
7. **RiftLite** — não é guia, é a metade da revisão deste plano.
8. **Piltover Archive** — a base de decks que a comunidade usa, e relatórios de
   torneio escritos pelos jogadores com o raciocínio de sideboard e battlefields.
9. **The Winning Point** (podcast semanal) — raciocínio sobre metagame.

Para o método de teste, no Magic: Verhey «Five Trials of Playtesting»
(01/06/2017), Lax «Procedural Playtesting» (17/05/2011), a matemática do
Karsten, e as séries de drill **«Keep or Mulligan»** do PVDDR (com respostas
publicadas no dia seguinte) e a do Reid Duke (que dá o enquadramento: identifica
a peça que falta, e pergunta a probabilidade de a encontrares e o que a mão faz
enquanto espera — «foca-te no raciocínio, não em acertar na resposta»).

---

## 8. O que ainda não existe e eu não invento

- **Quantos jogos a comunidade de Riftbound acha que são precisos** para
  aprender um deck ou avaliar uma mudança: **não há fonte datada e com autor**.
  O vídeo que provavelmente responde a isto é «How to Actually Practice
  Riftbound», que não consegui ler de onde estou.
- **Técnica de jogo a duas mãos, protocolo de adversário guiado ou lista de
  drills** para Riftbound: **não existe nada publicado**. Os três drills do §4
  são meus.
- **Timing de deploy do Champion**: sem literatura.
- O número real da vantagem de começar em Constructed: não encontrei fonte
  fiável. **Mede o teu** — as ferramentas de registo calculam-no.

---

## 9. O que está em disputa, e o meu erro de hoje

**Em disputa, e importa:** como se escolhem os battlefields em **Bo3**. As
Tournament Rules dizem **aleatório** para Bo1 e para Limited Bo1; dois autores
da comunidade (um deles o Mythras, do §7) dizem que em Bo3 se escolhe e que um
battlefield usado não se repete no match. A regra que decidia isto é a secção
«Modes of Play» das Core Rules, que não foi possível extrair do PDF. **O
conselho de construção é o mesmo nas duas leituras: os teus três battlefields
têm todos de ser jogáveis a sério.**

**Não verificado:** a cláusula de que o **ponto final tem de vir de manter** um
battlefield (está no booklet oficial da era Origins, não a localizei nas Core
Rules de 09/10/2026 — fica para confirmar na regra 469); se as mods de Riftbound
do Tabletop Simulator foram mesmo removidas; a série «Riftbound Fundamentals»
do canal Games Deconstructed; e dois artigos do TCGplayer Infinite que são
provavelmente os melhores para ti — «An MTG Player's Guide to Riftbound» e «You
Are Scoring Points Wrong In Riftbound» — que não se conseguem ler por
automatismo. **Esses dois vale a pena abrires à mão.**

**O meu erro.** Passei a regra de nunca ir ao riftbound.gg ao pesquisador do
Riftbound, e **esqueci-me de a passar ao segundo**, que tratou do método de
teste — e esse foi lá buscar coisas. **Nada do que veio de lá entrou neste
documento**: as duas ferramentas da secção 3 (Rift Atlas e RiftLite) vieram da
pesquisa limpa e **confirmei as duas eu mesmo**, página a página, hoje. Mas o
erro foi meu e fica escrito.

**Não medi nada disto em ti.** Este documento é pesquisa e desenho; os números
da secção 4 são propostas ancoradas no que outros relatam, não medições tuas.
A primeira medição real é a tua primeira semana.

---

## 10. As tuas decisões (14/10/2026)

| pergunta | o que escolheste | o que isso muda |
|---|---|---|
| Volume semanal | **3-4 h, em 3 ou 4 noites** | As metas da secção 4 ficam como estão escritas. O chão da semana má continua válido — é o chão, não o alvo |
| Onde registar | **RiftLite + Arena, automático** | **Não escrevo código novo no riftvault para isto.** O RiftLite grava os matches do Rift Atlas sozinho e dá-te os replays; a tua parte é só a linha da revisão, uma por semana |
| Alvo | **Sem data: jogar melhor** | O plano fica cíclico. O calendário da secção 6 passa a servir só para saber quando as regras e o metagame mudam — e a regra nova é **um deck de cada vez até fechar as três fases** |
| Adversários no Riftbound | **Quick Match no Rift Atlas** | É o único teste verdadeiramente às cegas que consegues ter sozinho: o adversário sabe o deck dele e só te vê o que se veria num torneio. Os drills a solo da secção 4 continuam, porque é neles que está a prática deliberada. **Nada de voltar a montar decks em papel** — as cartas ficam nos binders |

**O que fica à tua espera, e é a primeira coisa a fazer:** instalar o RiftLite
(Windows, grátis, sem conta obrigatória) e abrir o Rift Atlas no browser. São
os dois pilares do plano e nenhum deles custa nada. Eu não instalo programas na
tua máquina sem tu dizeres.

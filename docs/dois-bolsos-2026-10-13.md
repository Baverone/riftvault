# Os dois bolsos — a medição, antes de mexer (2026-10-13)

Palavras dele, hoje, por ordem: *«mudei a minha forma de querer a coleção /
quero as comuns e incomuns Foil (playset) e à parte quero ter 2 playset de cada
(non-foil)»* · *«quero 3 foil, isso é coleção, depois quero multiplos para
Decks»* · *«coleção quero apenas 3 Foils, pronto»* · *«vou aplicar a regra de
Coleção é Coleção e não mexe, tudo tem que lá estar / Deck é Deck / tudo o que
eu marcar que tenho no deck, deve ser tratado como à parte, caso o deck deixe de
jogar, essas cartas ficaram guardadas para outro deck que as possa usar mais
tarde»*.

**Conclusão primeiro: a regra à letra faz cair a percentagem de master set de
89,2 % para 51,2 % e põe os dois decks a precisar de 49 cópias · 407,02 € que
ele hoje não precisa.** São dois dos sinais que a ordem mandava travar
(«a percentagem a cair a pique»), por isso **a mudança de modelo NÃO se
implementou neste ramo**. Os números são honestos — não é um erro de conta, é o
que a regra diz —, mas são decisões dele, e há três perguntas que só ele
responde (no fim). O ramo leva esta medição e a correcção do rótulo «Decks
montados» do Início.

## Como se mediu

Tudo contra uma CÓPIA do `data/` real (`_revisao\_ef_copiar_dados.py`, as
bases por `Connection.backup()`, o `data/` só se leu), com o config e os
`decks/*.txt` copiados para a mesma pasta (`_revisao\_bolsos_preparar.py`).

* `_revisao\_bolsos_medir.py <árvore> <dados> <config> <saída> [chave=valor…]`
  — o painel do Início pelas mesmas funções que o alimentam
  (`metrics.index_payload`, `faltas_foil.payload_completo`, `decks.decks_index`,
  `decks.resumo_das_faltas`, `a_mais.payload`), mais a conta (c).
* `_revisao\_bolsos_listar.py` — o aviso de raridade e a falta dos decks, carta
  a carta (`decks.allocate`).
* `_revisao\_bolsos_amais.py` — o «A mais» partido pelo âmbito do foil.
* O «depois» precisou de código: um mecanismo MÍNIMO atrás de uma chave
  (`foil.coleccao_em_foil`), que muda só dois funis — a Coleção das impressões
  do âmbito do foil passa a contar as FOILS (`locais.na_colecao`), e o monte de
  onde os decks se servem passa a ser o STOCK DE DECKS em vez da Coleção
  (`decks.pool_dos_decks`). **Esse mecanismo NÃO está no ramo**: está em
  `_revisao\dois-bolsos-mecanismo.patch` (296 linhas, `git apply`), para a
  medição se poder repetir. Não está completo (ver «O que a regra à letra
  parte») e por isso não se juntou.

**O utilizador:** `SELECT user_id, COUNT(*) FROM copies GROUP BY 1` dá
`[(1, 1060)]` — as 1 060 linhas do `vault.db` dele são todas do utilizador 1
(o `coalesce(user_id,0)=0` da ordem não podia dar nada). A `copies` (1 060
linhas · 2 742 normais · 625 foil, sha `66ba0cc5e4e9`) foi a MESMA em todas as
corridas.

## a) As «86 cópias que saem da Coleção»

**Hoje saem ZERO.** Os dois decks estão DESMONTADOS (`decks.montados: []`), e
um desmontado não consome nada (2026-09-24). As 86 do `riftvault decks` são a
SIMULAÇÃO de os montar — cada um contra a Coleção inteira:

| deck | aviso | comuns | incomuns | raras |
|---|---|---|---|---|
| Leona Radiant Dawn | 44 cópias de 21 cartas | 14 | 11 | 19 |
| Kennen, Heart of the Tempest | 42 cópias de 23 cartas | 17 | 13 | 12 |
| **total** | **86** | **31** | **24** | **31** |

Com os dois montados a sério (o segundo já não vê o que o primeiro levou) são
**84** (44 + 40). A lista carta a carta sai do `_bolsos_listar.py`; as raras são
Fiora, Victorious 3 · Harnessed Dragon 2 · Kayle, Justified 3 · Kennen, Keeper
of Balance 2 · Radiant Dawn 1 · Scuttle Crab 3 · Vi, Peacekeeper 3 · Zhonya's
Hourglass 2 (Leona) e Decree of Unity 2 · Fizz, Trickster 2 · Heart of the
Tempest 1 · Rhasa the Sunderer 3 · Switcheroo 2 · Tideturner 2 (Kennen).

**As 55 comuns e incomuns deixam de ser problema com a regra nova** — vêm das
normais, que passam a stock. **As 31 raras são o problema**: ele tem cada uma ao
alvo da Coleção (3) e não mais, por isso «Deck é Deck» obriga a comprar outra.

## b) O painel do Início, número a número

«Hoje» = o config de hoje. «À letra» = a Coleção das comuns e incomuns em foil e
os decks a NUNCA tirarem da Coleção (`coleccao_so_a_partir_de: null`). «Com
épicas» = o mesmo, mas a deixar os decks pedirem emprestado da épica para cima
(a frase dele de 2026-09-24, *«apenas miticas para acima devo ter que usar as da
coleccao»*, que a de hoje parece revogar).

| número | hoje | à letra | com épicas |
|---|---|---|---|
| **Master set · playset** | **828/928 = 89,2 %** · faltam 160 cópias | **475/928 = 51,2 %** · faltam 918 | igual à letra |
| 1 de cada · 2 de cada | 98,3 % · 94,8 % | 76,4 % · 62,9 % | igual |
| **Falta comprar** (wantlist geral) | **130 cópias · 82 cartas · 428,38 €** | **888 · 435 · 528,34 €** (ao preço da NORMAL — ver abaixo) | igual |
| **Valor da coleção** | **8 328,60 € · 3 359 cópias** | igual (o valor é o que ele TEM) | igual |
| Decks montados (o cartão) | «1 de 2» — **mentira**, ver a secção própria | «0 de 2» | «0 de 2» |
| Leona (simulação) | 50/54 · falta 4 | **29/54 · falta 23** | 36/54 · falta 17 |
| Kennen (simulação) | **54/54** · completo | **30/54 · falta 24** | 41/54 · falta 13 |
| os dois montados: falta comprar aos decks | **6 cópias · 2 cartas · 14,31 €** | **49 · 24 · 407,02 €** | 32 · 15 · 54,14 € |
| Coleção extra | 192 cópias · 7 455,89 € | igual | igual |
| Faltas, metade das foils | 829 cópias · 341,98 € | igual — **e passa a contar as mesmas foils duas vezes** | igual |
| Uso na grelha («em uso no deck») | 0 (nada montado) | 0 | 0 |

**O que os decks passam a pedir à letra** (montados): Leona — Astral Heron 3,
Vilemaw 2, Zenith Blade 3 (épicas), Fiora 3, Harnessed Dragon 2, Kayle 3,
Kennen, Keeper of Balance 2, Radiant Dawn 1, Vi 2, Zhonya's 1 (raras), Salvage 1.
Kennen — Ezreal, Prodigy 1, Kennen, Storm of Shuriken 1, Last Rites 2, Lightning
Rush 3, Seal of Discord 3, Vex 1 (épicas), Decree of Unity 2, Fizz 2, Heart of
the Tempest 1, Rhasa 3, Switcheroo 2, Tideturner 2 (raras), Flash 1, Salvage 2.
As épicas valem **352,88 €** dos 407,02 € — é a diferença entre «à letra» e
«com épicas».

**A percentagem cai porque a coleção dele em foil está a meio, não por um
erro:** das 512 impressões do âmbito do foil (comuns e incomuns, base, sem o
OGS), ele tem 625 foils; a Coleção que contava as normais passa a contar essas.

## c) As comuns e incomuns

| | |
|---|---|
| impressões do âmbito do foil | **512** (`foil.no_ambito`) |
| cópias NORMAIS que saem da Coleção para o stock de decks | **1 416** |
| cópias FOIL que ele tem | **625** |
| foils que FALTAM para o alvo 3 (o `metrics.alvo`; runas base 3) | **775** |
| custo ao preço foil de hoje (`price_latest.price_foil_cents`) | **333,97 €** (19 cópias sem oferta foil, ao preço da normal → é um piso) |
| stock de decks à solta (normais do âmbito + o que passa do alvo no resto) | **1 559 cópias em 568 impressões** (1 416 do âmbito) |

## d) O «A mais»

**O «192 cópias · 7 455,89 €» da ordem não é o «A mais»** — é o cartão «Coleção
extra» do Início (alt art, sobrenumeradas e promos por fechar), e não mexe. O «A
mais» hoje é **122 cópias de 61 impressões · 43,59 €**; dessas, **12 cópias de 11
impressões (1,32 €)** são normais do âmbito do foil, que à letra deixam de ser «a
mais» e passam a stock. O resto (110 cópias · 42,27 €) são raras e outras acima
do alvo — que *«multiplos para Decks»* também manda para o stock. **À letra, o
«A mais» como existe deixa de ter sentido:** tudo o que não é Coleção é stock de
decks (1 559 cópias). Ficaria por decidir se o «A mais» passa a ser «o stock que
nenhum deck usa» — e aí não explode por erro, explode por definição (122 → mais
de 1 500).

## O que a regra à letra PARTE, além dos números

Medido com o mecanismo mínimo ligado — é por isto que ele não se juntou:

1. **As Faltas contam as foils das comuns duas vezes.** A metade das normais
   passa a pedir as foils (é a Coleção), e a metade das foils (2026-09-27, *«as
   foils não são faltas, são complemento»*) continua a pedi-las: a metade das
   normais sobe 758 cópias (130 → 888) e a das foils fica nas 829, com as mesmas
   foils lá dentro.
2. **A wantlist geral pede foils ao preço da normal e sem dizer que são foil.**
   Os 528,34 € são a 0,11 €/carta; ao preço foil a parte das comuns são os
   333,97 € da secção (c). A linha do Cardmarket não marca foil (é um filtro por
   entrada, 2026-09-01) e teria de vir toda marcada.
3. **O tile mente.** O crachá da Coleção passaria a ser as foils e a linha de
   baixo também (`foil M/T`); os `+`/`−` do tile mexem nas normais, que deixam de
   mexer no crachá.
4. **A grelha diria «em uso no deck X»** em cartas que vêm do stock (53 cartas
   com os dois montados) — o deck já não usa a Coleção.

Cada um tem conserto; nenhum é uma linha.

## O rótulo «Decks montados» — corrigido neste ramo

O Início dizia **«DECKS MONTADOS 1 de 2»** com `decks.montados: []`. O número era
`decks.filter(d => !d.missing).length` — quantos estão COMPLETOS (o Kennen,
54/54). O rótulo estava certo e a conta errada: passou a contar o `montado` de
cada deck (que o `decks_index` traz desde 2026-09-24) e a dizer os completos na
nota — hoje o cartão diz **«0 de 2»** e por baixo **«1 de 2 completos — faltam
4 cópias para os outros; num desmontado é a simulação de o montares.»** `iniDecksContagem` no `app.js`,
`tests/test_inicio_decks_montados.py` (8 testes; prova pela negativa contra o
`app.js` do `main`: **6 vermelhos**, os 2 verdes são os que fixam que o
`decks_index` já trazia o `montado`).

## As perguntas que são dele

1. **A percentagem de master set passa a medir as comuns e incomuns EM FOIL?**
   Hoje 89,2 %; à letra 51,2 %. (A metade das foils das Faltas já mostra esse
   alvo hoje, como complemento: 829 cópias · 341,98 €.)
2. **«Deck é Deck» vale para as épicas também?** À letra os dois decks precisam
   de **407,02 €** (49 cópias); deixando-os pedir emprestado da épica para cima,
   **54,14 €** (32). A 2026-09-24 ele disse *«apenas miticas para acima devo ter
   que usar as da coleccao»*.
3. **A mensagem 1 ou a 3?** A 1 queria *«2 playset de cada (non-foil)»* à parte;
   a 3 diz *«apenas 3 Foils, pronto»*. Com a 3, as 1 416 normais são stock de
   decks sem alvo nenhum — não há wantlist de normais, e as que faltam a um deck
   compram-se pelo deck.

Com as três respondidas o mecanismo do patch serve de ponto de partida: os dois
funis estão certos; falta reconciliar as Faltas, a wantlist, o tile e o «A mais».

---

# v2 — as decisões dele, e o que se fez (2026-10-14)

Ramo `ai-pc/dois-bolsos-v2-2026-10-13`. **O patch de cima NÃO se usou**: as
decisões mudaram a pergunta (a Coleção das comuns NÃO passa a foil), e por
isso o mecanismo é outro — e mais pequeno.

1. **«Duas percentagens lado a lado».** O master set não mexe. Ao lado nasce o
   **master set foil** (`foil.master_set_foil`, `index.levels_foil`, um cartão
   no Início e uma tabela no `riftvault stats`): o mesmo denominador (928), as
   impressões do âmbito do foil contam as FOILS contra o alvo 3, as outras
   contam como no master set. A wantlist dele é a metade das foils das Faltas
   — e por isso o alvo das foils passou de Rune 12 para **Rune 3** (o tile, as
   Faltas e o número têm de dizer o mesmo).
2. **«Épicas podem vir da Coleção».** `decks.abaixo_do_patamar:
   "so_o_excedente"` reusa o `coleccao_so_a_partir_de` de 24/09: abaixo da épica
   o deck só vê da Coleção **o que passa do alvo** (`decks.so_o_excedente`);
   o resto é próprio, stock ou falta. A omissão do código continua `marca`.
3. **O bolso comum é o binder** que já existia. Desmontar
   (`principal.montar`), apagar a lista (`colar.apagar`) e apagar todos
   (`decks.apagar_todos`) mandam as próprias e as sleevadas para lá
   (`locais.devolver_ao_stock`); lá servem qualquer deck, e **o binder deixou de
   contar para o valor** (`locais.contadas`, `prices.copias_sql`), como as
   próprias — senão desmontar fazia o valor subir.

## A tabela, antes e depois (cópia do `data/` de 2026-10-14, `copies` sha `66ba0cc5e4e9`)

| número do painel | antes (`main`) | depois (ramo) |
|---|---|---|
| Master set · 1 de cada | 912/928 = 98,3 % | **igual** |
| Master set · 2 de cada | 880/928 = 94,8 % | **igual** |
| Master set · playset | 828/928 = 89,2 % · faltam 160 · 691,16 € | **igual** |
| **Master set foil** · 1 de cada | — | **709/928 = 76,4 %** · faltam 219 · 126,98 € |
| **Master set foil** · 2 de cada | — | **584/928 = 62,9 %** · faltam 514 · 467,48 € |
| **Master set foil** · playset | — | **475/928 = 51,2 %** · faltam 918 · 1 026,38 € |
| Falta comprar (wantlist geral) | 130 cópias · 82 cartas · 426,07 € | **igual** |
| Valor da coleção | 8 297,82 € · 3 359 cópias | **igual** |
| Coleção extra | 192 cópias · 7 379,81 € | **igual** |
| Faltas, metade das foils | 829 cópias · 368 impressões · 345,78 € | **775 · 368 · 337,77 €** (as 6 runas: 12 → 3) |
| Decks montados (cartão) | 0 de 2 | **igual** |
| Leona (simulação) | 50/54 · falta 4 · aviso 44 | **10/54 · falta 43** · aviso 0 |
| Kennen (simulação) | 54/54 · falta 0 · aviso 42 | **12/54 · falta 42** · aviso 0 |
| os dois montados: falta comprar aos decks | 6 cópias · 2 cartas · 14,31 € | **85 cópias · 43 cartas · 62,86 €** |
| «A mais» (os dois montados) | 122 cópias · 61 | **118 · 60** |
| «A mais» (nada montado, o de hoje) | 122 · 61 | **igual** |

**Os «~54 €» da ordem são 62,86 €, e o número de cópias é outro.** Os 54,14 € de
13/10 contavam as comuns normais como stock livre (porque nessa hipótese a
Coleção delas era em foil). Com a decisão 1 as normais continuam a ser a
Coleção, e só o que passa do alvo serve os decks: são **85 cópias**, mais do
que as 32 de então, mas baratas — comuns, incomuns e raras.

## O que fica sem resposta (a pergunta 3)

O «2 playset non-foil» deixou de ser alvo e nenhum número da app o pedia — a
contagem por níveis nunca passou do playset. Mas há um sítio onde ele deixa de
ter resposta: **as normais que passam do alvo (o excedente) não têm casa
visível.** Os decks usam-nas, mas o único ecrã que as lista é o «A mais», que
está escondido (`abas.escondidas`). Se ele quiser ver «o stock à solta para os
decks», é decidir se o «A mais» volta, ou se o binder e o excedente se mostram
juntos na secção Decks.

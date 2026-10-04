# Relatório de 2026-10-04 — o varrimento fechou, e o que custou

Escrito pela supervisora. Todos os números abaixo vêm de um comando; onde não
vêm, está dito. A última secção são os meus erros do dia, e são seis.

## 1. O que ficou feito

**No riftvault** (`main`, portão VERDE: 84 ficheiros, 2724 testes, 0 vermelhos)

| | |
|---|---|
| lacunas 8.1 e 8.2 do varrimento | fechadas, e a vigia de cada uma **medida** — a reverter o defeito na fonte, 8, 6 e 7 testes ficam vermelhos |
| §5, correcção A — a casca na raiz | `site/` de **78 para 74 ficheiros**, de 7 181,7 para **6 280,0 KB** (−901,7) |
| §5, correcção B — não reescrever o que não mudou | publicação sem mudanças: **28 ficheiros → 0**; uma carta de uma pessoa: **31 → 5**; catálogo novo: **47 → 11** |
| lacuna 8.5 | `tests/test_eficiencia_site.py`, a vigia que **conta bytes** por pessoa |

Com isto o varrimento de 01/10 está fechado nas dez secções. Fica de fora,
por decisão dele, o `robots.txt` na raiz.

**No ai-pc** (`master`, bateria: 0 vermelhos, 22 tarefas com cenário)

| | |
|---|---|
| correcções soltas desde 02/10 | o `riftvault-daily` não tinha o `indice()` que o `publicar` levou a 02/10 — era o **terceiro** caminho hardcoded; mais o NameError que rebentava no caso normal, o tibia-site a apontar ainda para o Vercel, e a mensagem muda do `baiakvault-publicar` |
| reposistório privado | `Baverone/ai-pc` — 73 commits e 4 ramos que **não existiam em sítio nenhum fora deste disco** |
| tarefa `ai-pc-push` | 05:15, 21/21 no autoteste; a prova é o sha local contra o `ls-remote` **depois** do push, nunca o exit code |
| cenários do gestor-email | juntos; o `test_tarefas` acusava-os desde 30/09, e um vermelho permanente ensina a ignorar vermelhos |
| `.gitattributes` | sem ele, a árvore vista de fora do Windows aparecia **toda** modificada: 137 ficheiros de ruído para 10 alterações a sério |
| aviso de «por commitar» | de **352 entradas para 20** |
| disco | **567 MB** libertados no `_revisao`; o `_to_delete` apagado |

## 2. A avaria que ninguém tinha visto

Os **dez commits do `site/` de hoje, das 05:37 às 10:07**, tocaram 28 ficheiros
cada um, e em **28 de 28 só o `generated_at` mudava**. É a avaria de 10/09 outra
vez: o `--se-mudou` olhava para a colecção DELE e nunca para as dos amigos. A
`riftvault-publicar` corre 48×/dia. A correcção B fecha-a, e a corrida das
18:08 já disse «nada a fazer» com o site em dia — que é a prova em produção.

## 3. Dois processos esquecidos, um deles há nove dias

A pasta `_revisao\riftvault-selado-tirar2` resistia a ser apagada há três
tentativas, e não era mistério: era a **directoria de trabalho** de um
`python _revisao/_servir_tirar2.py` de **25 de Setembro**, nove dias de pé, à
escuta em `127.0.0.1:8784`, de uma ordem que acabou há muito. O próprio script
já não existia — tinha sido apagado na limpeza de hoje, sem se saber que havia
um processo a correr nele.

Lição para a ronda nocturna: o `processos.py` sabe matar a árvore das sessões
Claude, mas um `python _revisao/_qualquer.py` lançado DENTRO de uma ordem não é
seguido por ninguém. Vi mais 30 processos velhos e não lhes toquei — a maioria
são o Codex dele e as tarefas `serve`.

## 4. Uma ferramenta que não estava em sítio nenhum

O `work/juntar-ramo.py` — o guião com que se juntam os ramos do riftvault, o que
mede as colecções por sha256 antes e depois, corre o portão e confere que a
config não perdeu chaves — **não estava no git**. A ferramenta de que se depende
para não estragar as colecções não tinha histórico nenhum. Está commitada.

## 5. Os meus erros, hoje

1. **«604 commits» no ai-pc.** São **73**. 604 é o número do riftvault, e eu
   abri-lhe uma caixa de decisão com o número errado lá dentro.
2. **«o ai-pc existe só nesse disco».** Errado: a tarefa `backup-offsite` já
   zipava os DADOS dele para os Releases do `Baverone/ai-pc-backups`, todos os
   dias às 04:00. O que não ia era o **código** — o plano leva o `runs.db`, os
   `task.json` e uns `.md`, e nem o `runner.py`, nem um único `run.py`/`test.py`,
   nem o `tests/`, nem o `knowledge/`. Essa metade era real; a afirmação era
   larga demais.
3. **«dezenas de ficheiros» na pasta *Claude outputs*.** São **4606**.
4. **A minha consulta ao `runs.db`** deu testes falhados em todas as tarefas: o
   `test_status` é `pass`, não `ok`, e eu li a minha própria coluna errada.
   Verdade do dia: **499 pass, 18 skipped, 0 falhas**.
5. **«352 ficheiros soltos» e «`work/` com 537 MB».** São **3989** (o
   `git status` normal colapsa uma pasta inteira numa linha) e **0,6 MB** (a
   minha contagem somou as subpastas dentro do total da pasta-mãe).
6. **Desconfiei antes de ler.** Vi a casca três vezes no `site/` commitado do
   ramo da eficiência e tratei isso como possível defeito. A ordem tinha
   escrito, na secção «o que NÃO se fez e porquê», que um build numa worktree
   sai errado — o `data/users/` e o `catalog.db` estão no `.gitignore` — e que
   provou a transição contra o `site/` real com uma cópia do `data/`. Fui fazer
   o build de qualquer maneira e ele **apagou as três pessoas** do site daquela
   worktree; tive de repor. Verificar por fora é a minha função; não ler o que a
   ordem escreveu antes de desconfiar não é.

Mais duas de menor monta: chamei `build_todos` como se fosse subcomando da CLI
(é função; a CLI é `build`), e mandei uma ordem com JSON inválido por causa das
escapes do PowerShell — o runner recusou-a bem, com a razão escrita.

## 6. O que fica em aberto

* o `robots.txt` na raiz da lista — ele escolheu não o pôr;
* `s72-ITA-MLT-u21_v2.xlsx` na raiz do ai-pc: não me pareceu lixo óbvio, fica
  para ele dizer;
* os dois ficheiros de dados do `work/mtg-fotos` por commitar — estado da
  corrida das 02:00, que consumiu as 322 fotos da fila; por decisão dele, não
  se commitam;
* 20 ficheiros à vista no aviso das 05:15, todos documentos e dados em `work/`.

# A eficiência do site publicado — 2026-10-04

O §5 do `docs/varrimento-2026-10-01.md` («434 KB de casca repetida por pessoa,
e cada publicação reescreve 4,65 MB») e a lacuna **8.5** do §8 («nenhum teste
mede o tamanho do site por pessoa»).

Ramo `ai-pc/eficiencia-site-2026-10-04`, quatro commits — um por correcção,
mais o da vigia.

---

## O que se mediu primeiro, e uma coisa era pior do que o varrimento dizia

O varrimento mediu **um** commit (`89345f96`: 46 ficheiros, 4 651 KB) e leu
dali «uma pessoa a somar uma carta faz reescrever o site das três». O regime
PERMANENTE é pior, e vê-se no repositório real
(`_revisao\_ef_git_site.py`, `_ef_relogio_so.py`):

> Os dez commits do `site/` de 2026-10-04, das **05:37 às 10:07**, de meia em
> meia hora, tocaram **exactamente 28 ficheiros cada um** — `goncalves` 14 +
> `miguel` 14 — e em **28 de 28 só o `generated_at` mudava**.

Comparados dois pares de commits consecutivos (`8dc51ee` vs `9ee8c32` e
`43df041` vs `fb2d659`) com a regra do `build._sem_relogio`: 28/28 nos dois.
Às 05:37 da manhã ninguém estava a mexer em nada.

Era **um commit, um push e uma build do Pages de 30 em 30 minutos, 48 vezes
por dia, sem uma carta mexer** — a avaria de 2026-09-10 de volta pela porta de
trás. A causa: o `--se-mudou` só olhava para a coleção DELE; as dos amigos
eram regeneradas sempre, e o relógio bastava para o Git ver tudo como novo.

(Durante esta ordem apareceu o 11.º, às 10:37, igual aos outros.)

---

## As duas correcções

### A — a casca na raiz, uma vez só

`app.js` (350,9 KB) e `style.css` (99,5 KB) eram byte a byte iguais nas três
pastas `u/<slug>/`: **900,7 KB repetidos**, e mais 450 KB por cada pessoa
nova. Passaram a viver na raiz, e cada `u/<slug>/index.html` aponta-lhes com
`../../`.

* `config.CASCA` é a definição única. A casca tem **dois** escritores — o
  `build._gerar` quando a raiz é a coleção dele, o `lista.escrever` quando é a
  lista — e o `build` importa o `lista`, por isso não podia ser de nenhum dos
  dois;
* `lista.subida_da_casca` conta a profundidade do caminho REAL (`u/<slug>/`
  → `../../`), para a arrumação poder mudar sem isto ficar a mentir;
* **os caminhos têm de ser relativos.** O site responde ao mesmo tempo em
  `rift.baverone.com/` e em `baverone.github.io/riftvault/` — é por este
  segundo que o `test.py` da `riftvault-publicar` pergunta —, e um `/app.js`
  absoluto dava 404 lá. Provado nos dois alojamentos;
* o `_aponta_a_casca` **rebenta** se a referência não estiver no `index.html`
  exactamente uma vez: uma página sem `style.css` não dá erro nenhum, abre em
  texto cru, e descobria-se pela fotografia em vez do teste;
* o `casca` vai **também na prova do `--se-mudou`**. Sem ele a prova leva a
  casca que o `out` já não tem, o `mesmo_conteudo` compara conjuntos de
  ficheiros diferentes e diz «mudou» a TODAS as corridas — a avaria de
  2026-09-10 outra vez, por outro caminho;
* o `app.js`/`style.css` saíram do `lista.RESTOS_DA_RAIZ`: deixaram de ser
  restos do site DELE e passaram a ser a casca, que é da raiz seja quem for o
  dono dela;
* **a cópia velha sai** (`_Saida.remover`), senão a poupança era mentira — o
  `limpar_raiz` só mexe na raiz e a poda dos órfãos só mexe na `api/`.

### B — não reescrever o que não mudou

O `build.mesmo_conteudo` já sabia comparar dois sites ignorando o
`generated_at`; passou a decidir **ficheiro a ficheiro** (`build._Saida`) e não
só o site todo. A `api/` deixou de se apagar de raiz — os órfãos podam-se ao
fim, o que dá a mesma garantia (uma edição que sai do catálogo sai do site)
sem obrigar a reescrever os 24 payloads que não mudaram.

---

## Antes e depois

### O tamanho do `site/`

`_revisao\_ef_medir_site.py` (o `site/` commitado) e `_ef_transicao.py` (o
mesmo `site/`, depois do primeiro build com o código novo, contra uma cópia do
`data/` real):

| | ficheiros | KB | a casca está em |
|---|---|---|---|
| **antes** | 78 | 7 181,7 | **6 sítios** (3 pastas × 2 ficheiros) |
| **depois** | 74 | 6 280,0 | **2 sítios** (a raiz) |
| poupança | −4 | **−901,7** | |

Para fazer a transição o build escreve **2 ficheiros, 36,4 KB** na pasta dele
(o `index.html`, que ganhou o `../../`, e o `api/index.json` pela regra 2),
com 22 a ficarem como estavam.

Por pessoa nova a poupança é de **450,4 KB**: a 10 pessoas são ~4,1 MB; a 20,
~8,6 MB.

### Os ficheiros reescritos por publicação

`_revisao\_ef_publicacoes.py`: a MESMA árvore e os MESMOS dados dos dois lados
(uma cópia do `data/` real feita com `Connection.backup()`), três cenários
seguidos. Conta-se o que o **Git** veria — ficheiros cujo CONTEÚDO mudou —, que
é o que vai no blob e no deploy; o mtime não interessa, o Git não o guarda.

| cenário | antes | depois |
|---|---|---|
| **nada mudou** | 28 ficheiros · 2 450,2 KB | **0 · 0,0 KB** |
| uma carta de UMA pessoa | 31 · 2 516,0 KB | **5 · 336,5 KB** |
| o catálogo mudou (é partilhado) | 47 · 4 787,5 KB | **11 · 1 879,5 KB** |

No cenário 2 os 5 são a `api/lista.json` e o `index.html` da raiz (o cartão
dela mudou de números) e três ficheiros da pessoa que mexeu; **nenhum
ficheiro das outras duas**.

### O que não mudou

O `site/` gerado continua a passar a guarda do `.github/workflows/pages.yml`
(`_ef_guarda_pages.py`): há `site/index.html`, há 3 `*/api/index.json`, e
nenhum nome na raiz começa por `_` — o Pages não serve nada que comece assim,
e a casca na raiz é o primeiro ficheiro que o browser pede.

---

## A decisão sobre o `generated_at` do índice

Era a armadilha que a ordem mandava não deixar implícita, e tem duas metades.

**O que o índice faz.** A `riftvault-publicar` e a `riftvault-daily` leem o
`generated_at` do `api/index.json` de referência — qual é sai da
`api/lista.json`, que diz de quem é a coleção dele — e comparam-no com o que o
GitHub Pages serve. É essa comparação que apanhou a avaria de 2026-09-10 (as
builds a morrer com o commit em `origin/main`). E o `test.py` dela faz, no
ponto 4, uma segunda pergunta: quando a tarefa diz que gerou o site
(`site_gerado`), o ficheiro tem de ter sido **escrito hoje**.

**Deixá-lo passar pelo crivo dava as duas avarias de uma vez:** a prova a
comparar um `generated_at` velho (e portanto a passar sempre, mesmo com o
Pages atrasado) e a tarefa a chumbar sem motivo no `escrito_hoje`.

**A decisão, que são duas regras** (`build._Saida`):

1. **ou se escreve tudo o que mudou, ou não se escreve nada.** Se nenhum
   ficheiro de uma pessoa diferir, não se toca em nenhum — nem no índice.
   Senão o índice sozinho dava o mesmo commit de 30 em 30 minutos que isto
   veio tirar;
2. **o `api/index.json` é SEMPRE reescrito, com relógio fresco, quando algum
   outro mudou.** Custa um ficheiro de ~20 KB por pessoa, e só em publicações
   que já iam acontecer.

**O alinhamento com a tarefa é exacto, e é por isso que isto fecha.** O
`site_gerado` dela é o `"Site gerado" in out` do `cmd_build`, que o imprime
só quando o `res["mudou"]` DELE é verdadeiro. Ou seja, o `escrito_hoje` só
pergunta pelo índice dele quando o `_gerar` dele correu — e aí a regra 2
garante-o fresco. Quando só um amigo mexeu, o `_gerar` dele não corre, o
`site_gerado` é falso, o ponto 4 não se faz, e o ponto 5 compara o relógio
velho de um lado com o mesmo relógio velho do outro: iguais, sem falso
vermelho.

O `res["mudou"]` passou a vir do crivo (era `True` sempre que o `_gerar`
corresse), e **o erro cai para o lado seguro**: um `False` a mais salta a
verificação; um `True` a mais chumbava a tarefa.

**Nada se mudou em `ai-pc/tasks/`.** A decisão foi tomada de maneira a que as
duas tarefas continuem a dizer a verdade sem lhes tocar.

---

## A vigia (lacuna 8.5)

`tests/test_eficiencia_site.py`, **24 testes**. A lacuna pedia um teste que
falhe «quando a casca passa a ser copiada N vezes»; o que faltava era contar
**bytes** — o `tests/test_lista.py` conta ficheiros e nomes.

A regra do duplicado é **genérica**: não pergunta pelo `app.js` pelo nome,
pergunta se há ficheiros grandes (≥ 8 KB) repetidos byte a byte no site. Um
terceiro ficheiro de casca que nasça amanhã — uma fonte, um `.map`, um segundo
`.js` — e que alguém copie por pessoa fica vermelho sem ninguém ter escrito o
nome dele.

### A sobra que fica, medida e dita

A única excepção à regra é o **`index.html`**: ele É a página, e cada coleção
tem de ter a sua no URL dela. Duas pessoas com a mesma privacidade ficam com
páginas byte a byte iguais, e isso não é casca copiada — é o sítio onde a
página mora. São **~16,8 KB × (N−1)**: 33,6 KB com as três pessoas de hoje,
~320 KB a 20.

Tirá-la pedia que a página fosse um esboço que carrega tudo por JavaScript, e
isso é mexer no frontend e não na arrumação do site. **Não se fez**, e não se
subiu o limiar para a tapar: subi-lo aos 17 KB dela deixava passar um ficheiro
de casca de 20 KB.

### A prova pela negativa

«Há testes» não é «há vigia»: um teste que passa dos dois lados não vigia
nada. Por cada defeito desfaz-se **uma linha na FONTE**, numa worktree
descartável, e corre-se o mesmo ficheiro de teste
(`_revisao\_ef_prova_negativa.py`; relatório em `_ef_prova_negativa.json`).

**Nunca com monkey-patch**: o `tests/fixture.py:80` faz
`importlib.reload(config)` em cada `setUp` e apaga patches em memória — a
armadilha está no commit `5cc073e` e no §8b do varrimento, e já custou uma
manhã a 2026-10-04.

| defeito de volta | a linha desfeita | hoje | com o defeito |
|---|---|---|---|
| **A** — a casca copiada por pessoa | `build.py`: `for name in (() if casca else CASCA):` → `for name in CASCA:` | 22 verdes | **4 VERMELHOS** |
| **B** — reescrever tudo, mudado ou não | `build.py`: `mudaram = sorted(r for r in self._corpos if r not in self._iguais)` → `sorted(self._corpos)` | 22 verdes | **4 VERMELHOS** |
| **B, regra 2** — o índice com o relógio velho | `build.py`: sem o `a_escrever.add(self.INDICE)` | 22 verdes | **1 VERMELHO** |

Os vermelhos são os certos, pelo nome. **A**:
`test_nenhum_ficheiro_grande_se_repete_byte_a_byte`,
`test_os_bytes_da_casca_no_site_sao_os_de_UMA_copia`,
`test_uma_pessoa_nova_nao_traz_outra_casca`,
`test_cada_pagina_aponta_a_casca_DA_RAIZ_e_ela_esta_la`. **B**:
`test_uma_publicacao_em_que_nada_mudou_nao_escreve_NADA` (que inclui as
coleções dos AMIGOS, que era onde o defeito vivia),
`test_so_se_reescreve_o_que_mudou`,
`test_o_mudou_vem_do_crivo_e_nao_de_ter_corrido`,
`test_e_a_PROVA_PELA_NEGATIVA_da_regra_2`. **Regra 2**:
`test_o_INDICE_e_sempre_fresco_quando_outro_payload_mudou`.

(A tabela é de quando eram 22 testes; os dois da cópia velha da casca
entraram no commit seguinte.)

**E a prova pela negativa apanhou um teste que não vigiava nada**, que é para
isso que ela existe: o `test_uma_publicacao_em_que_nada_mudou_nao_escreve_NADA`
comparava os BYTES em disco e **passava com o crivo desligado** — o
`generated_at` tem resolução de um segundo e duas gerações seguidas num teste
caem no mesmo segundo, por isso os bytes saíam iguais de qualquer maneira.
Passou a perguntar ao crivo (`res["crivo"]["escritos"] == []`), que não
depende da velocidade da máquina.

---

## A prova de ponta a ponta

O André pediu-a expressamente a 2026-10-01: a suite verde não prova que uma
página publicada abre. `_revisao\_ef_servir_e_abrir.py` serve o `site/` gerado
num servidor HTTP local e, por cada coleção:

* pede o `index.html` e **lê dele** o `src=`/`href=` da casca (não se adivinha
  o caminho), resolve-os contra o URL da página como o browser faz e confirma
  **200**;
* confirma que resolvem para a RAIZ e que é **um ficheiro só para as três**;
* resolve sete `api/*.json` relativos — `index`, `decks`, `set/OGN`,
  `encomendas/OGN`, `runas`, `faltas_edicao` — e confirma 200 + JSON válido;
* confirma o `noindex`: nas duas dos amigos e na raiz, **não** na dele.

Repetido **servindo numa subpasta** (`/<pasta>/`), que é como o
`baverone.github.io/riftvault/` responde. Resultado nos dois alojamentos:

```
/app.js       pedida por 3 pagina(s)
/style.css    pedida por 3 pagina(s)
>>> TUDO OK: casca a 200 na raiz, api/*.json a resolver, noindex no sitio,
    nos dois alojamentos.
```

### E o crivo não deixa nada velho para trás

`_revisao\_ef_crivo_integro.py`, contra uma cópia do `data/` real:

1. um site mantido **incrementalmente** (quatro publicações, com mudanças em
   dois utilizadores pelo meio) diz o MESMO que um gerado de raiz
   (`build.mesmo_conteudo` = `True`);
2. um payload **órfão** (`api/set/ZZZ.json`) sai mesmo do site, e um ficheiro
   que não é da `api/` fica onde está;
3. a **regra 2** dispara, com a prova pela negativa ao lado: sem nada a mudar,
   o índice não mexe.

---

## O que NÃO se fez, e porquê

* **o `site/` deste ramo não foi regenerado.** Não houve conflito nenhum para
  resolver — o ramo não toca em `site/` —, e regenerá-lo numa worktree sai
  **errado**: o `data/catalog.db` e o `data/users/` estão no `.gitignore`, por
  isso numa worktree o catálogo está vazio e as coleções dos amigos não
  existem. O que se fez em vez disso foi provar a transição contra o `site/`
  REAL e uma cópia do `data/` (ver a tabela acima); o primeiro `riftvault
  build` na máquina dele faz exactamente isso — escreve 2 ficheiros e tira 4;
* **o `index.html` repetido por pessoa** — ver «a sobra que fica»;
* **nada em `ai-pc/tasks/`** — ver a decisão do `generated_at`;
* **o `Cache-Control`** que o §5 anota («nenhuma rota manda `Cache-Control`»)
  é do modo edição, que é o 8770 em casa dele. Não é tamanho de site e não
  estava na ordem;
* **o `/api/compras.json`**, o pior rácio medido no §5 (359 ms para 1,4 KB,
  porque corre a alocação dos decks inteira), também é do modo edição. Fica
  anotado.

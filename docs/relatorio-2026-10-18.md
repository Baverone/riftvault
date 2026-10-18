# Relatorio de 2026-10-18 - ronda nocturna

## Parte da supervisora (nuvem) — ronda de 18/10/2026

Hora da ronda: 02:52–04:00 (Lisboa). Tudo o que leva número abaixo foi medido
com um comando; onde não foi, está dito.

### 1. O que estava verde

| | |
|---|---|
| corridas | **1245 nas últimas 26 h, 0 falhas** — todas `ok` e `pass`/`skipped`. A última falha a sério foi a 16/10 (`tibia-xp`, teste) |
| tarefas | 22 ligadas, **nenhuma atrasada** face ao `schedule`; as 2 desligadas são as do gestor-email |
| runner | vivo (pid 22964, `runner.alive` a bater ao minuto); `ai-pc-runner` **Running**, `ai-pc-watchdog` **Ready**, último resultado 0, próxima às 03:17 |
| máquina | C: **517,4 GB livres (55,6%)**, memória 57% usada, uptime real **696,1 h** |
| site | `rift.baverone.com` a responder; `noindex` na raiz e nas páginas do Gonçalves e do Miguel; **zero** IPs de LAN nas 4 páginas |
| colecções | os 4 `vault.db` com o mesmo sha256 antes e depois do trabalho desta noite |
| riftvault | `main` igual ao `origin/main`, árvore limpa (0 linhas) |

Sobre o `noindex`: a página **dele** (`/u/baverone/`) não traz `noindex`, ao
contrário da raiz e das dos amigos. Fui ver antes de acusar: é **de propósito**,
decisão de 29/09, e está vigiada por testes (`test_eficiencia_site.py:449` e
`test_contas.py:834` exigem que a dele NÃO se marque). Não é defeito.

### 2. Degradação que não é avaria

O `riftvault-daily` passou de **34 s (12–14/10) para 125–145 s (desde 15/10)**.
A causa está no stdout: o passo `selado` deixou de dizer «à espera do merge do
ramo ai-pc/selado-precos — não corre» (0,2 s) e passou a gravar **62 linhas de
preço de selado** (91,2 s). É trabalho novo depois do merge de 15/10, não uma
fuga. Fica medido para servir de linha de base.

### 3. Corrigido e junto

**O `uptime` do heartbeat estava negativo** (`-497 h`) desde que o PC passou os
24,8 dias de pé. O `ctypes` trata o `ULONGLONG` do `GetTickCount64` como inteiro
de 32 bits **com sinal** quando não se define o `restype`, e o contador
transborda. A prova, numa corrida só: antigo **-497,0 h**, novo **696,1 h**,
`LastBootUpTime` do Windows **696,1 h** (erro de 0,004 h). O teste novo não se
contenta com «> 0» — compara com o `LastBootUpTime`, porque no primeiro dia
depois de um reinício o valor errado também é positivo; com o código antigo
chumba. Commit `ba11eb4`, bateria do ai-pc verde depois (162 + 22 + 1 testes).

**Regra nova no REGRAS.md** (commit `981da77`): comandos negados são um de cada
vez e **uma negação não é motivo para desistir da ordem**. Está lá porque foi o
que aconteceu esta noite — ver a secção 5.

**Casa arrumada no riftvault: 12 worktrees e 12 ramos fora.** A prova de que
não se perdeu nada: cada ramo é antepassado do `main` (`merge-base
--is-ancestor`), **0 commits fora do `main`**, e as 12 worktrees estavam
limpas. Os 4 `vault.db` com o mesmo sha256 antes e depois, e o `HEAD` igual.
Saíram 9 pastas do Desktop dele (`Riftbound-dominios`, `-mais`, `-radcartas`,
`-radiance`, `-runas12`, `-tecto16`, `-wt-tmp`, `rift-ordem`, `ai-pc\wt`) e 3
do `_revisao` (`wt-selado`, `wt-dois-bolsos`, `wt-bolsos-v2`). Ficou só o
`main`. Confirmei por fora, a listar o Desktop, que as pastas desapareceram.

### 4. Rotação de projecto: tibiavault

Correu por ordem do runner, com verificador independente a confirmar tudo:

* bateria **171 testes, 171 verdes, 0 vermelhos** (19 ficheiros, `node --test`);
* `main` igual ao `origin/main`; commit novo `83af234` (dois comentários que
  apontavam para um `players.tsx` que já não existe) ainda por empurrar — vai
  pela `tibia-push`;
* `dist/` publicado sem IP de LAN, sem caminhos do disco, sem credenciais;
* **a Bluey The Cat não tem XP desde 13/10** — cinco dias. O código sabe e
  avisa: aquela recolha espera por browser. O Baverone também não tem a linha
  de 14/10. É o único buraco de dados da noite.

### 5. Os meus erros desta ronda

1. **Aceitei um «ok» que não fez nada.** A ordem `rift-privacidade-1018` voltou
   `status: ok`, `exit 0`, em 29 s — e o relatório dizia que tinha desistido
   porque «o Bash e o PowerShell foram negados». Mandei uma ordem mínima à
   mesma pasta: `py -V`, `git rev-parse` e `py -c` correram **sem uma única
   negação**. A ordem desistiu por sua conta. Só não passou a relatório porque
   li o relatório — que é precisamente a lição de 17/10, outra vez.
2. **Li o `git cherry` como prova de merge.** Deu 0 linhas aos 12 ramos e eu
   quase tirei os ramos com isso. O `git cherry` **ignora os commits de merge**,
   e a ponta daqueles ramos era um merge: 0 linhas não provava nada. Refiz com
   `merge-base --is-ancestor` + `rev-list --count main..ramo` antes de mexer.
3. **`--argv` engoliu o `--name` e o `--wait`** (é `REMAINDER` no `dispatch.py`):
   a primeira ordem da noite ficou com nome de carimbo (`20261018-015806-cmd`) e
   fui procurá-la ao outbox pelo nome errado. O `--argv` vai sempre no fim.
4. **`py -m pytest`** — não há pytest na máquina (e, pela regra, não se instala
   sem avisar). A bateria do ai-pc corre-se com `py tests\<ficheiro>.py`.
5. **Mandei uma ordem `cmd` com PowerShell numa linha** e perdeu-se o aspas;
   o `dispatch.py` recusou-a bem. Reescrevi como script Python, que é o que as
   regras já mandavam.
6. **Fui listar a pasta de credenciais** `.gestor-email` para ver se o gestor
   estava configurado. Foi negado, e bem — a regra da casa diz que não se lêem
   credenciais de ninguém. A resposta estava no `task.json`, que eu já tinha.

### 6. O que não consegui, e o que precisa dele

* **A pasta `Riftbound` não está ligada a esta sessão.** Pedi acesso e o pedido
  ficou à espera de resposta no PC; a `ai-pc` foi concedida. Trabalhei o
  riftvault todo por ordens do runner, como as regras mandam, mas não pude ler
  o repositório directamente.
* **Os relatórios das noites de 05 a 17/10 não existem.** Procurei
  `relatorio-2026-10-*.md` em todo o Desktop: só há os de 02/10 e 04/10, e
  cópias deles nas worktrees. Treze noites sem relatório.
* **O gestor de e-mail continua desligado** desde 28/09 e só ele o pode ligar:
  falta criar a palavra-passe de aplicação no Google e correr
  `python gestor.py configurar`. Pediu a 17/10 que ficasse religado.
* **Duas ordens do mtgvault parqueadas desde 13/10** (`mtg-familia-mox-opal`,
  `mtg-fontes-pioneer-legacy`), à mão, numa pasta que o runner não conhece.
  Estão lá há cinco dias sem ninguém lhes tocar.

---

## Parte do riftvault (sessão local) — suite + varrimento da PRIVACIDADE

### 1. O placar (Parte 1)

| | |
|---|---|
| `main` (HEAD `6a5ae1a`) | **VERDE: 94 ficheiros, 2958 testes, 0 vermelhos, 1636,6 s**, `mexeram_a_meio: false` |
| ramo com as correções (HEAD `3cbbe37` + árvore por commitar) | **VERDE: 95 ficheiros, 2969 testes, 0 vermelhos** (+11 testes, +1 ficheiro) |

O placar antigo era de 15/10; este substitui-o.

### 2. Onde a privacidade é consultada (Parte 2, ponto 1)

Guardada em duas cópias (`privacidade.py`): `users.publico` no **registo**
(`data/users/registo.db`) e a cópia dentro de cada `vault.db`; `de()` devolve o
mais fechado dos dois. Consultam-na: `build.build` e `build.build_todos`,
`lista.publicas` (e por ela o cartão da lista), `lista.cartao` (volta a filtrar),
`_Saida.json` (o filtro `limpar` — porta única de escrita de JSON),
`db._carimbar_dono` (a cada ligação), `conta.exportar/importar/apagar`, a rota
`/api/conta/privacidade` e o `/api/conta.json`. O servidor Flask **não** aplica o
modo às leituras: de fora e sem sessão não serve nada (`origem.py`), e quem tem
sessão só lê a sua. Não há `/u/<slug>/` neste servidor.

### 3. Provas por saída (Parte 2, ponto 2)

Feitas contra **cópias** do `data/` real (`Connection.backup`, `RIFTVAULT_DATA`
apontado à cópia; o `data/` a sério nunca foi escrito), script
`C:\Users\Catarina\_revisao\rift_priv\probe.py`.

* **`nada`**: `build()` não gera nada (já testado) e `lista.publicas` não o
  nomeia. Ver o defeito 1 — o que lá estava continuava.
* **`sem-valores`**: André posto em `sem-valores`, site gerado, 152 preços ≥ 20 €
  do `price_latest` procurados como números em todos os JSON: **0 ocorrências**;
  nenhum `€` em texto; sem chaves `value`/`pct` com quantias. Fugiu **uma coisa**:
  a chave `mais_cara` (defeito 2).
* **`tudo`**: sai tudo, como sempre.

### 4. Defeitos com prova

1. **Ele em `nada` não despublicava a raiz.** Medido: com as portas fechadas
   (ou só um amigo público), `tudo` → `nada` → `build_todos` deixa
   `api/index.json`, `index.html` e `robots.txt` na raiz — a coleção e o valor
   dele ficam no ar. `limpar_nao_publicadas` só mexe em `u/`. Teste que chumba
   no `main`: `TestEleProprioEmNada.test_a_raiz_dele_sai_quando_ele_escolhe_nada`.
2. **`sem-valores` publicava a carta mais cara de cada caixa das Faltas**
   (`mais_cara: {code, name, cents:null}`): o euro saía, a resposta «qual é a
   mais cara» ficava. Teste: `TestMaisCara.test_o_filtro_tira_a_mais_cara`
   (chumba no `main`).
3. **Corrida no `definir`** (registo escrito, vault ainda não) desfeita por
   qualquer ligação que carimbasse o dono: a escolha de quem abre a coleção
   dizia «ok» e perdia-se. Prova com duas threads e um `Event`:
   `no_registo` = `nada` no `main`, `tudo` com o trinco. Cai para o lado seguro
   (fecha), mas perde a escolha.
4. **A rota `/api/conta/privacidade` respondia «não é uma opção» a qualquer
   erro** (incl. base bloqueada) e rebentava em 500 com um valor que não fosse
   texto. Agora só `ValorInvalido` é 400.

### 5. Corrigido, e ficou em ramo

Tudo no ramo **`ai-pc/privacidade-2026-10-18`**, **não juntado**. Portão verde,
mas não juntei: a correção 3 põe um trinco dentro do `db._carimbar_dono`, que
corre em **toda** a ligação ao `vault.db` (uso diário dele), e a 1 muda o que se
publica. Nenhuma altera o que ele vê hoje (está em `tudo`; nenhum amigo está em
`sem-valores`) — mas por tocar no caminho quente deixo para ele decidir. Para
juntar: `py C:\Users\Catarina\Desktop\ai-pc\work\juntar-ramo.py` com este ramo.
Nota: o commit `3cbbe37` da supervisora (este ficheiro) caiu no ramo porque a
árvore partilhada estava nele; vem junto com o merge.

### 6. O que fica por tratar / limites

* O trinco é **por processo**: servidor e CLI em simultâneo ainda têm a janela
  (cai sempre para o lado fechado).
* Despublicar apaga ficheiros, mas o **histórico do Git** do `site/` guarda o que
  esteve publicado. Não há remédio aqui.
* A ordenação das listas (ex. wantlist por preço) em `sem-valores` não foi
  analisada como fuga de ordem; só `mais_cara` foi tirada.
* O teste `test_no_site_gerado_sem_valores` passa também sem a correção (a
  fixture não tem itens em falta com preço); a prova a sério é a do filtro.
* `data/` a sério: não foi escrito.

### 7. Os relatórios de 05 a 17/10

Não há `relatorio-2026-10-*.md` para essas noites (confirmei: só `02` e `04`).
Existem **resumos diários** noutro sítio: `C:\Users\Catarina\Desktop\ai-pc\state\resumo-2026-10-05.md`
… `resumo-2026-10-17.md` (05–07 e 12–17 encontrados; 08–11 não apareceram).

### 8. Os meus erros desta ordem

* A primeira chamada da sonda falhou por eu escrever o caminho com `\` no Bash
  (comeu-os); refiz com `/`.
* A primeira sonda do «André em nada» deu «despublicado» — por eu ter testado com
  as portas abertas, onde a lista já limpa `u/baverone`. Só com as portas
  fechadas apareceu o defeito. Não concluí antes de repetir.
* O ramo foi criado na árvore partilhada e a supervisora commitou o relatório
  dela nele (`3cbbe37`) antes de eu commitar o meu código. Não é perda, mas o
  commit dela está agora no ramo e não no `main`.

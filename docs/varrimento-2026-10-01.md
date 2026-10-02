# Varrimento geral — 2026-10-01

**NADA A DEITAR FOGO.** Nenhum dado de nenhuma pessoa está exposto no
repositório público, nem está no histórico: `git log --all -- "data/users/*"
"data/auth.db"` devolve **vazio** e `git rev-list --all --objects | grep -i
"auth\.db\|registo\.db\|users/"` devolve **vazio** — nunca entrou. O `rafael`
(`publico = "nada"`) não aparece em nenhum dos 78 ficheiros do `site/`, nem o
slug nem o nome. Não há escrita sem dono e não há perda de coleção.

Isto é só **medir e listar**. Não se mudou uma linha de código: o único ficheiro
novo é este. As correcções são ordens a seguir, uma de cada vez.

* **Placar da suite:** 75 ficheiros, 2 403 testes, **0 a falhar**, em 4 fatias
  no primeiro plano (179 + 306 + 261 + 292 s = **1 038 s, 17 min 18 s**), contra
  o `main` em `b209443`.
* **Scripts de medição:** `C:\Users\Catarina\_revisao\_varr_1_site.py` a
  `_varr_12_robots.py`. Tudo contra cópias (`VACUUM INTO`, as bases estão em
  WAL) ou `GET`. O `data/` a sério nunca se escreveu — a `copies` dele tem as
  mesmas 1 046 linhas, 2 663 normais + 540 foil, no princípio e no fim.

---

## 1. A RAIZ PUBLICADA NOMEIA DOIS AMIGOS E NÃO TEM `noindex` — e o `robots.txt` que devia travar isso está num sítio que nenhum motor lê

**Onde.** `riftvault/build.py:239-255` (quem decide marcar) · `riftvault/abrir.py:398-405`
(a marca e o `robots.txt`) · `riftvault/abrir.py:423-440` (`publico_indexavel`) ·
`riftvault/lista.py:372-385` (`limpar_raiz`, que tira o `robots.txt` da raiz e
não põe outro) · `riftvault/lista.py:85` (`RESTOS_DA_RAIZ`).

**O que se mediu**, ao vivo e no `site/` commitado:

| pedido | resposta |
|---|---|
| `https://rift.baverone.com/robots.txt` | **404 Not Found** |
| `https://rift.baverone.com/u/miguel/robots.txt` | **200**, `User-agent: *` / `Disallow: /` |
| `https://rift.baverone.com/` | **200**, sem `<meta name="robots">`, sem `X-Robots-Tag`, e com **«Miguel Valente»** e **«Gonçalves»** no HTML |

E no ficheiro que vai para o ar, `site/index.html`:

* linha 93 — `<h2>Gonçalves</h2> … 433 cartas · 1 184 cópias … 686,57 €`
* linha 94 — `<h2>Miguel Valente</h2> … 6 cartas · 15 cópias … 216,86 €`
* `grep 'name="robots"' site/index.html` → **zero**
* `site/robots.txt` → **AUSENTE** (nunca foi versionado: `git log -- site/robots.txt` é vazio)
* `site/u/goncalves/index.html` e `site/u/miguel/index.html` → **têm** `noindex`
* `site/u/baverone/index.html` → **não tem**, e está certo (é a dele)

**O estrago.** O `robots.txt` lê-se **só em `/robots.txt` do anfitrião** — um
ficheiro em `/u/<slug>/robots.txt` nunca é pedido por motor nenhum, e o do
anfitrião responde 404, o que para um motor significa «podes rastrear tudo».
Das «duas portas» que o `abrir.py` diz fechar (*"os dois juntos fecham as duas
portas"*), **uma está inerte**. A que funciona — o `noindex` na página — protege
a coleção de cada um, mas **não a raiz que os nomeia**: o Google pode indexar
`rift.baverone.com` e mostrar «Gonçalves — 686,57 €». O próprio código escreve
porque é que isto importa: *«uma página da coleção de um amigo indexada no
Google antes de ele saber que existe é um erro que NÃO SE DESFAZ»*. Os dois
escolheram `tudo`, mas foi o código que decidiu que a página deles não se
indexa «até ele dizer o contrário» — e a lista desfaz essa decisão sem ninguém
a ter tomado.

**Custo de corrigir.** Duas decisões e duas linhas: (a) um `robots.txt` **na
raiz** (`Disallow: /u/` enquanto a de um amigo não se indexar), que é
exactamente onde o `RESTOS_DA_RAIZ` hoje o apaga; (b) o `publico_indexavel`
passar a responder também pela página da LISTA — ou a lista mostrar só o nome
de quem o tiver autorizado à parte de «publicar a coleção». Mais um teste no
`test_lista.py`, que hoje **não tem nenhum** sobre indexação (ver §8).

---

## 2. OS LOGS E OS BACKUPS DE UM AMIGO CAEM NA PASTA DO ANDRÉ, E SEM DIZER DE QUEM SÃO

> **CORRIGIDO a 2026-10-02** (`config.log_path`, `config.user_dir`,
> `config.backups_dir`, `tests/test_rasto_por_dono.py`) — ver a secção própria
> no fim do CLAUDE.md. Um log por pessoa (o dono é o CAMINHO, não uma coluna);
> os backups em `data/backups/<slug>/` e **não** dentro da pasta apagável do
> utilizador; os logs que já existem ficam onde estão, porque são todos dele —
> medido. O teste que fixava o defeito (`tests/test_binders.py:399`) **não
> precisou de mudança nenhuma**: o caminho do André não mexeu.

**Onde.** `riftvault/locais.py:422` · `riftvault/pending.py:807` ·
`riftvault/uso_decks.py:141` — os três fazem `config.DATA_DIR / LOG_NAME`.
E `riftvault/decks.py:531` · `riftvault/db.py:90` · `riftvault/conta.py:238,281,537`
— `config.DATA_DIR / "backups"`.

**O que se mediu** (`_varr_4_amigo.py`, numa cópia, com `RIFTVAULT_DATA` próprio).
Criou-se o utilizador 2 («zeteste»), entrou-se, e fez-se um `locais.marcar`
como ele:

```
locais.log       na pasta do ANDRE=True   na do amigo=False
   2 linha(s); a ultima:
   2026-10-01T18:10:14+00:00,ogn-045-298,OGN-045/298,Defy,1,Coleção,Binder Decks/Venda,varrimento-amigo
   ha COLUNA de utilizador? NAO

conta.exportar('zeteste') -> backups/conta-zeteste-20261001-191015.zip
   esta na pasta do AMIGO? NAO — na do Andre
```

Esta é a família que o `config.decks_dir(con)` já resolveu para os `.txt` dos
decks (2026-09-29) e que **os logs e os backups não acompanharam**.

**NÃO é fuga pública.** `git check-ignore -v` confirma os quatro:
`data/locais.log` (`.gitignore:40`), `data/encomendas.log` (`:43`),
`data/decks.log` (`:46`), `data/backups/` (`:92`).

**O estrago.** Três coisas, por ordem:

1. **o rasto deixa de servir para o que foi feito.** O `locais.py` promete
   *«se uma cópia aparecer num deck sem linha aqui, é bug»* — com quatro pessoas
   a escrever no mesmo CSV e **sem coluna que diga quem**, essa verificação
   deixa de se poder fazer. O mesmo no `encomendas.log` e no `decks.log`
   (60 798 bytes hoje);
2. **a coleção inteira de um amigo num `.zip` na pasta dele.** O
   `conta.exportar` e o backup de «antes de importar» vão para
   `data/backups/`, que hoje tem **18 ficheiros / 7 680 KB**;
3. **apagar a conta de um amigo não tira os ficheiros dele da pasta do dono.**
   Está dito no resultado (`copias que ficam=2`) e é decisão deliberada — mas a
   pasta onde ficam é a errada.

**Custo de corrigir.** Uma função (`config.log_path(con, nome)`, gémea exacta do
`decks_dir(con)` que já existe) e três chamadas; o mesmo para os dois caminhos
de `backups`. **E atenção: o teste actual FIXA o defeito** —
`tests/test_binders.py:399` exige `self.v.data / self.locais.LOG_NAME`, a raiz.
Corrigir o código obriga a corrigir esse teste, e é o teste que está velho.

---

## 3. `riftvault multi --verificar` DIZ `[TEU]` A DOIS PASSOS QUE ESTÃO FEITOS — E VERIFICÁVEIS

> **CORRIGIDO a 2026-10-02** (`abrir.perguntar_ao_tunel`, `abrir._tunel`,
> `tests/test_achados_346.py`) — ver a secção própria no fim do CLAUDE.md. Os
> dois passos `[TEU]` passaram a **UM que mede**: um `GET` ao
> `auth.base_url/api/conta.json` e lê-se o `origem`/`sinais` que a própria app
> escreveu. Medido outra vez a 02/10: **200, nove sinais, `origem: "fora"`**.
> A marca ` TEU  ` do `None` passou a `NÃO SEI`, e **sem rede a resposta é «não
> sei», nunca «falta»**. A medição é INJECTÁVEL e por omissão não há rede — quem
> a pede é o comando que um humano corre. O teste que fixava o defeito
> (`test_senhas.test_sao_DOIS_passos_dele_e_nao_tres`) foi reescrito: era ele
> que exigia os dois passos presumidos.

**Onde.** `riftvault/abrir.py` (`verificar`, os passos `[TEU]`).

**O que o comando diz hoje:**

```
[ TEU  ] A conta na Cloudflare: só tu podes criá-la.
[ TEU  ] Os nameservers do baverone.com + o túnel: só tu podes mudá-los, e é o passo com risco.
           ANTES de trocar, confirma que a Cloudflare já tem os cinco endereços … O rift.baverone.com não pode cair.
```

**O que se mediu, no mesmo minuto:**

| | |
|---|---|
| `sc query Cloudflared` | `STATE : 4 RUNNING` |
| `tasklist` | `cloudflared.exe` PID **26828**, 41 716 K |
| `GET https://editar.baverone.com/api/conta.json` | **200 em 309 ms**, `origem: "fora"`, **nove sinais** (`CF-Connecting-IP`, `CF-Ray`, `CF-IPCountry`, `CF-Visitor`, `CF-Warp-Tag-Id`, `CDN-Loop`, `X-Forwarded-For`, `X-Forwarded-Proto`, e o anfitrião público) |
| `GET https://rift.baverone.com/api/lista.json` | **200 em 222 ms**, três coleções |

Ou seja: a conta na Cloudflare existe, os nameservers estão trocados e o túnel
corre. Os dois `[TEU]` estão feitos, e **mediam-se com o que a app já sabe
fazer** — o `origem.py` acabou de nascer para ler exactamente estes sinais.

**O estrago.** O passo 2 é o único da lista com risco declarado («o
rift.baverone.com não pode cair») e a verificação manda-o lá outra vez. Uma
checklist que presume em vez de medir ensina a ignorar a checklist — e a seguir
ignora-se o passo que importava.

**Custo de corrigir.** Dois passos que medem: um `GET` ao `auth.base_url` com
timeout curto (se responder 200 e trouxer sinais de intermediário, o túnel está
vivo → `[OK]`) e o estado do serviço. **Sem rede, a resposta é «não sei», não
«falta»** — é a diferença entre não medir e medir mal.

---

## 4. O PAYLOAD CONTRADIZ-SE: `editable: true` A QUEM NÃO PODE ESCREVER

> **CORRIGIDO a 2026-10-02** (`rotas_conta.editavel`, `server._editavel`,
> `metrics.index_payload(servidor=...)`) — ver a secção própria no fim do
> CLAUDE.md. Os 15 `True` fixos passaram a chamar a regra que já existia, e o
> `api_conta` chama a MESMA. Medido no servidor a sério, mesmo pedido anónimo
> com a porta aberta: **antes 8 payloads contradiziam o `conta.json`, agora
> zero**; e com a porta fechada de casa continua tudo `true` — o uso dele não
> mexeu. O **site publicado sai igual ficheiro a ficheiro**, com uma chave nova
> (`servidor: false`, +17 bytes por `index.json`).
>
> **O campo tinha de se PARTIR EM DOIS**, e isso a ordem não previu: o `app.js`
> usava o `editable` também para decidir se vale a pena pedir o
> `api/conta.json`, por isso torná-lo honesto **escondia a caixa de «Entrar»**
> a um leitor anónimo com a porta aberta — o beco de 2026-09-30 por outro
> caminho. A segunda pergunta ganhou campo próprio (`servidor`).

**Onde.** `riftvault/server.py` — **15 sítios** com `editable=True` fixo (linhas
133, 144, 153, 217, 245, 270, 281, 318, 347, 360, 382, 401, 550, 559, 659)
contra `riftvault/rotas_conta.py:573` — `"editavel": not aberto and de_casa`.

**O que se mediu** no 8770, mesmo pedido anónimo de casa, com
`multi.aberto: true` (que é o estado commitado desde `79fe63b`):

```
/api/conta.json            200    editavel=False
/api/decks.json            200    editable=True
/api/index.json            200    editable=True
/api/set/VEN.json          200    editable=True
/api/runas.json            200    editable=True
/api/venda.json            200    editable=True
/api/selado.json           200    editable=True
/api/encomendas.json       200    editable=True
```

**O estrago.** Hoje **não se vê**, porque o cliente corrige:
`app.js:966-967` faz `meu = !state.conta || state.conta.editavel !== false` e
`state.editable = !!state.index.editable && meu`. O estrago é no próximo leitor
que confie no campo — a CLI, um teste, uma vista nova, um script dele — e o
sintoma será `+`/`−` desenhados a dar 401 a cada clique, que é precisamente o
que a nota do `api_conta` diz querer evitar.

**Custo de corrigir.** Uma função em `server.py` (`_editavel()`, que lê o `g`
que o `_antes` já preenche) e 15 substituições. Ou, melhor: **tirar o campo de
14 payloads** e deixá-lo só no `index.json` e no `conta.json` — são duas
respostas à mesma pergunta espalhadas por quinze sítios.

---

## 5. EFICIÊNCIA: 434 KB DE CASCA REPETIDA POR PESSOA, E CADA PUBLICAÇÃO REESCREVE 4,65 MB

### O que se mediu

**O site publicado hoje: 7 231 KB em 78 ficheiros.**

| pasta | tamanho | ficheiros | o maior |
|---|---|---|---|
| `site/` (raiz: `index.html` + `api/lista.json`) | 6,0 KB | 3 | — |
| `site/u/baverone/` | **2 108,7 KB** | 25 | `app.js` 325,3 KB |
| `site/u/goncalves/` | **2 472,8 KB** | 25 | `api/faltas_edicao.json` 602,6 KB |
| `site/u/miguel/` | **2 643,6 KB** | 25 | `api/faltas_edicao.json` 734,3 KB |

**As páginas dos amigos são MAIORES do que a dele**, e a razão é boa: quanto
menos cartas tem, mais faltas tem para listar (o Miguel tem 6 cartas e
734 KB de `faltas_edicao.json`).

**O que se repete, byte a byte** (sha256 iguais nas três pastas):

| | por pessoa | hoje (3) | a 10 | a 20 |
|---|---|---|---|---|
| `app.js` | 325,3 KB | 975,9 KB | | |
| `style.css` | 93,1 KB | 279,2 KB | | |
| **total de casca repetida** | **434,4 KB** | **868,8 KB** | **3,82 MB** | **8,06 MB** |

(O `index.html` difere, e bem: 16 414 bytes no dele contra 16 532 nos dos
amigos — a diferença é o `noindex`.)

**O build é rápido e não é o problema:**

```
build()       — só o André              0.7s   25 ficheiros   2.06 MB
build_todos() — 4 no registo, 3 públicos 1.5s   77 ficheiros   7.06 MB
  por pessoa a mais: ~0.3s e ~1.67 MB
  a 10 públicas: ~5s, ~24.6 MB;  a 20: ~9s, ~49.6 MB
--se-mudou, segunda corrida: 2.5s, mudou=False
```

**O que escala mal é o número de ficheiros reescritos.** O commit `89345f96`
tocou **46 ficheiros e 4 651 KB de blobs novos**; a `riftvault-publicar` corre
48×/dia. Os commits de antes de haver amigos tocavam 16-18 ficheiros. Ou seja:
uma pessoa a somar **uma carta** faz reescrever o site das três, porque o
`generated_at` muda em todos — o `build.mesmo_conteudo` ignora-o para DECIDIR
se publica, mas quando publica reescreve tudo.

**O que NÃO é o problema, e é preciso dizê-lo:** o repositório. `git
count-objects -vH` dá `size-pack: 5.78 MiB` depois de **599 commits**, 131 deles
de `site/` e 99 de `data/vault.db`. O Git delta-comprime JSON muito bem.

### Consultas e tempo de resposta

Contado com `set_trace_callback` (a única porta — a `sqlite3.Connection` é
imutável e não se pode espiar), contra uma cópia:

| payload | consultas | ms | KB |
|---|---|---|---|
| `index_payload` | 19 | 119 | 23,3 |
| `set_payload(OGN)` | 56 | 35 | 282,6 |
| `set_payload(VEN)` | 56 | 30 | 189,3 |
| `pending.grelha(OGN)` | 59 | 36 | 89,3 |
| `faltas_foil.payload_completo` | 17 | 33 | 335,4 |
| `a_mais.payload` | 37 | 20 | 33,1 |
| `faltas_edicao.payload` | 7 | 18 | 138,5 |
| `selado.payload` | 2 | 41 | 72,2 |

**Não há N+1 em sítio nenhum** — 56 consultas para 928 impressões é cada bloco
e cada métrica uma vez. Isto está bem e não precisa de nada.

No 8770 a sério (duas corridas, para separar o arranque frio):

| rota | 1.ª | 2.ª | KB |
|---|---|---|---|
| `/api/compras.json` | 357 ms | 359 ms | **1,4** |
| `/api/encomendas/OGN.json` | 358 | 276 | 81,2 |
| `/api/set/SFD.json` | 284 | 352 | 210,9 |
| `/api/index.json` | 273 | 284 | 20,3 |
| `/api/set/OGN.json` | 243 | 231 | 257,0 |
| `/api/a_mais.json` | 233 | 313 | 29,9 |
| `/api/faltas_edicao.json` | 152 | 246 | 303,6 |
| `/api/runas.json` | 48 | 28 | 4,3 |

* primeira visita à Coleção: **5 pedidos, 320 KB, 553 ms** (sem as imagens);
* separador «Todas»: **5 pedidos, 866 KB, 974 ms**;
* `/api/compras.json` é o pior rácio — **359 ms para 1,4 KB** (corre a alocação
  dos decks inteira para devolver quase nada);
* nenhuma rota manda `Cache-Control`.

### A partir de quantas pessoas é que isto deixa de servir

Com os números acima, e sem inventar limites que não medi nesta corrida:

* **até ~5 pessoas** nada disto se nota: ~12 MB de `site/`, build em 2 s;
* **entre 10 e 15** começa a doer: ~25-37 MB de árvore de trabalho commitada,
  3,8-5,7 MB disso em `app.js`/`style.css` idênticos, e cada publicação a
  reescrever ~15-23 MB de blobs — multiplicado por 48 corridas/dia no pior
  caso, em que alguém mexe sempre em alguma coisa;
* **a 20** são ~50 MB de `site/` e ~30 MB de blobs por publicação. É aí que o
  `git clone` do repositório e o passo de deploy do Pages passam a ser o
  pescoço, não o build.

**Custo de corrigir (duas correcções independentes).** A casca na raiz
(`/app.js`, `/style.css`) com `u/<slug>/index.html` a apontar-lhe tira
434 KB × (N−1) e é uma mudança de caminhos no `build.py`. Não reescrever o
`generated_at` em ficheiros cujo conteúdo não mudou é mais fundo — o
`mesmo_conteudo` já sabe compará-los ignorando-o, falta usar essa comparação
para decidir **ficheiro a ficheiro** e não só para o site todo.

---

## 6. `conta.apagar()` DEIXA O HASH DA PASSWORD ATRÁS — DEPENDE DE CADA CHAMADOR SE LEMBRAR

> **CORRIGIDO a 2026-10-02** (`conta.apagar` → `auth.esquecer_identidades`) —
> ver a secção própria no fim do CLAUDE.md. Fez-se **as duas coisas** que esta
> secção propõe, e não só o teste: a primitiva passou a limpar (é ela a camada
> de POLÍTICA — a confirmação, o export antes, a contagem) e **devolve o que
> limpou** em `auth`, para os dois chamadores dizerem o número em vez de
> voltarem a perguntar. A casa continua a ser a de lá: quem apaga é o
> `auth.esquecer_identidades`, e é **depois** do `utilizador.apagar` (ao
> contrário, um apagar que falhasse deixava uma conta VIVA sem entrada). Mais
> o teste que a secção preferia: por **cada** caminho — biblioteca, CLI, rota —
> varre-se o `auth.db`, com a prova pela negativa ao lado.

**Onde.** `riftvault/conta.py` (`apagar`) · `riftvault/auth.py:1516-1535`
(`esquecer_identidades`, que apaga as três coisas, a password incluída).

**O que se mediu.** Depois de `conta.apagar("zeteste", confirmar=True)` numa
cópia:

```
identidades no auth.db depois: []
hash de password ainda la? {'tem': True, 'temporaria': False,
                            'criado_em': '2026-10-01T18:10:14+00:00', ...}
```

**Hoje não há hash órfão por um caminho real**: os dois chamadores que contam
limpam — `riftvault/cli.py:1550` e `riftvault/rotas_conta.py:1056`. E
`users.user_id` é `AUTOINCREMENT` (`riftvault/users_schema.sql:25`), por isso
**ninguém herda a password de ninguém**: um id apagado não se reutiliza.

**O estrago.** É uma primitiva que deixa dados pessoais atrás e confia na
memória de quem a chama — e a própria docstring do `esquecer_identidades` diz
que a razão de ela existir é *«apagar a conta tem de apagar tudo o que é da
pessoa: é isso que se responde a quem pede para ser apagado»*. O terceiro
chamador é que paga. **Não há teste que apanhe um chamador esquecido** (ver §8).

**Custo de corrigir.** Ou o `conta.apagar` chama o `auth.esquecer_identidades`
(mantendo a ordem «exportar primeiro»), ou um teste que, para **cada** caminho
de apagar, varra o `auth.db` à procura do `user_id`. Preferia o teste: as duas
casas são separadas de propósito, e o que falha é a disciplina, não o desenho.

---

## 7. RAMOS E WORKTREES

**52 ramos locais. 47 já estão no `main`** (0 commits fora, 0 ficheiros
diferentes) — são lixo seguro. **Quatro por fundir:**

| ramo | commits fora | veredito |
|---|---|---|
| `ai-pc/revisao-2026-09-06` | 7 | **LIXO** — os sete arranjos estão TODOS no `main` |
| `ai-pc/signatures-fora-2026-09-11` | 2 | **LIXO** — superado |
| `ai-pc/suite-paralela-2026-09-30` | 1 (WIP) | **VALE, e é o único urgente** |
| `ai-pc/links-2026-09-16` | 4 | **a IDEIA vale, o código está velho** |

**`ai-pc/revisao-2026-09-06` — verificado arranjo a arranjo, por marca no
`main`**, não por `git cherry` (as linhas mudaram em 558 commits):

| arranjo | marca | no `main`? |
|---|---|---|
| `sync`: edição vazia da API já não apaga o catálogo dela | «a API não devolveu nenhuma entrada» em `catalog.py` | **SIM** (linha 207) |
| …e o `sets_vazias` chega à CLI (sai com 1) | `vazias` em `cli.py` | **SIM** |
| `web`: teclado só mexe na Coleção quando está à vista | `#sec-colecao` em `app.js` | **SIM** |
| `web`: índice de deck guardado que já não existe | `prefs.deck` em `app.js` | **SIM** |
| `build`: reler as listas antes dos payloads | `import_all` em `build.py:282` | **SIM** |
| `decks`: Legend sem domínios rebentava a secção | `json.loads(... or "[]") if legend_dom else set()` | **SIM** |
| `prices` / README: comentários | — | **SIM** |

O mais valioso dos sete era o primeiro — uma resposta vazia da RiftScribe
apagava o catálogo de uma edição inteira e o `build` publicava um site sem ela
sem dar erro. **Está no `main`**, com o comentário e tudo. O ramo pode ir.

**`ai-pc/suite-paralela-2026-09-30`** (`44b9652`, `.gitignore` +
`tests/test_portao.py` + `tools/placar.py` + `tools/portao.py`, +470/−27).
Propõe correr a suite em paralelo e dar **três** números em vez de um: quantos
ficheiros passaram à primeira, quantos só passaram **sozinhos** (colisões entre
processos, não defeitos — e é a distinção que o `placar` hoje não sabe fazer) e
quantos são vermelhos a sério. **Mediu-se o que isto poupa: a suite leva
17 min 18 s** em série, um processo por ficheiro, com os três mais lentos a
`test_senhas` 62,4 s (o scrypt, 130 ms por hash), `test_restauro` 39,5 s e
`test_lista` 33,4 s. É o único dos quatro que vale salvar com urgência.

**`ai-pc/links-2026-09-16`** (`riftvault/links.py` + payload + bloco no
cabeçalho + `tests/test_links.py`): um bloco com «editar em casa / ver / editar
de fora», a LAN só no 8770 e nunca no `site/`. Nasceu com o `editar_externo` a
`null` porque não havia túnel — **hoje há** (`editar.baverone.com`, medido no
§3), e a funcionalidade passou a fazer sentido. Mas o ramo está **343 commits
atrás** do `main`, de antes do rebrand de 24/09 que reescreveu o `app.js`
inteiro: **refazer é mais barato do que rebasear**. Guardar a ideia, não o
código.

**Worktrees: 27** (26 além da principal, **289 MB**). Seis estão sujas e
cinco delas só com rascunho:

```
riftvault-melhorias        ?? .tmp/
riftvault-niveis           ?? .tmp-parity/
riftvault-sem-signatures   ?? _medir_sig.py
riftvault-signatures-fora   M README.md
riftvault-venda-comuns     ?? _lixo/
wt-deck-sem-steppers        M app.js  M style.css  M test_copias_proprias.py
                           ?? tests/test_deck_sem_steppers.py   <-- OUTRA SESSÃO, A CORRER AGORA
```

**Não se mexeu em nenhuma**, como pedido. A `wt-deck-sem-steppers` é a ordem que
corre em paralelo no `app.js` — não lhe tocar.

---

## 8. O QUE A SUITE NÃO COBRE, E DEVIA

Nas partes onde um erro custa dados. Cada um destes é um teste pequeno.

1. **Nenhum teste exige que um log seja do utilizador que o escreveu** — e
   `tests/test_binders.py:399` **fixa o contrário** (`self.v.data / LOG_NAME`,
   a raiz). O teste está a trancar o defeito do §2. Faltam: o log de um amigo na
   pasta dele, e uma linha que diga de quem é.
2. **Nenhum teste sobre a indexação da RAIZ.** `grep "noindex\|robots"` em
   `tests/test_lista.py` e `tests/test_privacidade.py` → **zero**. Os que
   existem (`tests/test_contas.py:776-802`) são da página de cada um. Falta: a
   página da lista, quando nomeia alguém que não é o dono, tem de sair marcada —
   ou não nomear ninguém.
3. ~~**Nenhum teste varre o `auth.db` depois de apagar uma conta.**~~
   **FEITO a 2026-10-02**: `test_achados_346.TestApagarNaoDeixaNadaNoAuthDb`
   percorre os três caminhos (biblioteca, CLI, rota) e varre as três tabelas,
   com a prova pela negativa ao lado.
4. ~~**Nenhum teste exige coerência entre os dois campos de «podes editar».**~~
   **FEITO a 2026-10-02**: `test_achados_346.TestOPayloadNaoSeContradiz` varre
   os payloads de leitura e compara cada `editable` com o `editavel` do
   `/api/conta.json`, nos quatro regimes (porta aberta/fechada, de casa/de
   fora, entrado, com a temporária).
5. **Nenhum teste mede o tamanho do site por pessoa.** Um teste que falhe
   quando a casca passa a ser copiada N vezes travava o §5 antes de doer — hoje
   `tests/test_lista.py` conta ficheiros e nomes, nunca bytes.

---

## 9. `decks.so_base` — MEDIDO, E NÃO MUDADO (era o pedido)

**O que o config diz:** `riftvault_config.json:65` — `"so_base": true`, com
`"so_normais_excepto": []`. **O que ele disse** a 17/09 e repetiu hoje: *«usa o
que está na coleção, seja foil, Alt Art ou Overnumbered»* — e o CLAUDE.md
escreve a regra na secção «o deck aproveita as versões que ele tem».

**Medido** (`_varr_6_sobase.py` e `_varr_7_porque_zero.py`, a mesma cópia, só o
config a mudar entre as duas leituras):

| | `so_base: true` (hoje) | `so_base: false` |
|---|---|---|
| decks | 1 (`Leona Radiant Dawn`, **desmontado**) | igual |
| tenho / pede | 50/54 | 50/54 |
| `resumo_das_faltas` | **0 cópias · 0 cartas · 0,00 €** | **igual** |
| falta na simulação | 3× Zenith Blade, 1× Salvage | **as mesmas** |
| «noutra versão» | 0 | **0** |

**Virar o botão muda ZERO. E «zero» não é prova — aqui está porquê, e o que o
quebraria:**

1. o único deck está **DESMONTADO** (`decks.montados: []`), e um deck desmontado
   não consome a Coleção (24/09): o `resumo_das_faltas` é 0 nas duas
   configurações, por isso o botão não tem onde fazer diferença;
2. **nem na SIMULAÇÃO muda.** As duas cartas que lhe faltam não têm versão
   alternativa nenhuma na mão: `Zenith Blade` só existe como `OGN-262/298`
   (base, epic) e ele tem **0**; `Salvage` só existe como `OGN-224/298` (base,
   uncommon) e ele tem **2** de 3;
3. a **única** carta do deck em que uma versão alternativa taparia um buraco é a
   **Calm Rune** (pede 6, tem 3 em `OGN-042`, tem **6** em `OGN-042a`) — e essa
   não se move por **dois** motivos independentes, os dois decisões dele de
   17/09: as runas não se contam nos decks (`contar_runas: false`) e a arte
   alternativa de runa está **retirada** (`runas_especiais.retiradas: ["a"]`);
4. de todas as cartas do deck, só **4** têm alguma versão alternativa na mão.

**O que quebra o zero:** uma carta que não seja runa, que o deck peça, que lhe
falte em base, e de que ele tenha uma Alt Art / sobrenumerada / promo. Hoje há
**zero** dessas. No dia em que houver uma, o `so_base: true` esconde-lhe uma
carta que ele tem na mão.

**Conclusão.** A contradição é real mas custa **zero cópias e zero euros**: é
defeito de **coerência** — o config e o CLAUDE.md dizem coisas diferentes sobre
a mesma regra —, não de números. **Não virei o botão**, e a decisão é dele. Se
quiser virá-lo, é uma palavra; se quiser manter o `true`, o que falta é o
CLAUDE.md dizer que a regra de 17/09 está **desligada** desde 21/09 e porquê.

---

## 10. Privacidade: a pergunta pela negativa

*O que é que está no `site/u/<slug>/` que não devia?* Varrido ficheiro a
ficheiro:

| | |
|---|---|
| registo | `1 baverone tudo` · `2 miguel tudo` · `3 rafael nada` · `4 goncalves tudo` |
| tem página? | baverone SIM · miguel SIM · goncalves SIM · **rafael não** |
| o `rafael` aparece em algum dos 78 ficheiros do `site/`? | **NÃO** (procurado o slug e o nome, em `.json`, `.html`, `.js`, `.css`) |
| chaves de dinheiro com valor | baverone 6 313 · goncalves 7 387 · miguel 7 947 — e os três estão em `tudo`, por isso é o esperado |
| ninguém em `sem-valores` hoje | o filtro não se exercita no site real — exercitou-se numa cópia: `publico=sem-valores` → **0** chaves de dinheiro com número |
| `data/users/registo.db`, `data/auth.db`, as três `vault.db` dos amigos | **em disco sim, no Git não** (e nunca estiveram) |
| `.gitignore` | `data/users/` (`:13`) · `data/auth.db` (`:87`) · `data/backups/` (`:92`) · `*-prova/` (`:65`) |

**E o caminho inteiro de um amigo, provado numa cópia:** criar → temporária
(`fita-dica-bolo-ficha-36`) → entrar → trocar (`temporaria=False`) → entrar com
a nova → editar (+3 OGN-045 → 3 cópias) → `tudo` (página e lista) →
`sem-valores` (0 euros) → `nada` (**a pasta desaparece, o nome e o slug não
ficam em ficheiro nenhum, e a raiz volta a ser a dele**) → apagar.
**A 30/09 isto dava página preta aos quatro; hoje não dá.** O único senão é o
§6 (o hash fica se se chamar a biblioteca em vez da CLI ou da rota).

---

## Resumo, para decidir a ordem das correcções

| # | o que | custo | urgência |
|---|---|---|---|
| 1 | `noindex` + `robots.txt` na raiz da lista | 2 linhas + 1 teste | **alta** — uma página indexada não se desfaz · **o `noindex` FEITO a 02/10**; o `robots.txt` na raiz continua por decidir (ele escolheu não o pôr) |
| 2 | logs e backups por utilizador | 1 função + 6 chamadas + ajustar `test_binders` | ~~alta~~ **FEITO a 2026-10-02** |
| 4 | o `editable` dos payloads | 1 função + 15 linhas (ou tirar 14) | ~~média~~ **FEITO a 2026-10-02** — e foram DOIS campos, não um |
| 3 | o `--verificar` a medir o túnel | 2 passos | ~~média~~ **FEITO a 2026-10-02** — um passo que mede |
| 6 | `conta.apagar` e o `auth.db` | 1 teste (preferível) | ~~média~~ **FEITO a 2026-10-02** — a primitiva limpa, e o teste também |
| 5 | casca na raiz e o `generated_at` | caminhos no `build.py` / comparação por ficheiro | **baixa hoje, alta aos 10-15** |
| 8 | os cinco testes que faltam | pequenos, um a um | média |
| 9 | `so_base` — a coerência do CLAUDE.md | uma palavra, **decisão dele** | baixa (custa zero hoje) |
| 7 | 47 ramos lixo; salvar a `suite-paralela` | — | baixa, mas a suite a 17 min paga-se |

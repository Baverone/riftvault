# Contas e autenticação — o desenho, e o que o decidiu

Fatia `2-multi-contas`, 2026-09-29, **revista a 2026-09-30 (as passwords)**.
Vem a seguir a `0-multi-utilizador-1` (o modelo de dados,
`docs/multi-utilizador.md`) e a `1-multi-guardas` (o isolamento, a privacidade
e o interruptor).

O guia dos passos DELE está em `docs/abrir-a-porta.md`. Este ficheiro é o
porquê.

---

## 0. A DECISÃO DE 2026-09-30: passwords, mas nenhuma legível

**O que ele pediu**, no dia seguinte a isto ficar pronto com OAuth:

> *"em vez de discord, nao era melhor a pessoa criar uma conta com usuario e
> password e ficar guardado em base de dados?? / **o esqueci-me da password
> fica manual, eu acedo o ficheiro e digo A pessoa a password dela** / isto e
> uma coisa caseira, para usar entre amigos, entao nao ha problema"*

A primeira metade fez-se tal e qual. **A segunda recusei**, contrapus, e ele
aceitou:

> *"pode ficar a tua sugestao de nova password, e melhor / faz e da-me o
> proximo passo que precisas entao"*

**A contraproposta, numa linha:** ele nunca LÊ a password de ninguém — quando
alguém se esquece, ele DÁ UMA NOVA (`riftvault conta <nome> --nova-password`),
temporária, que a pessoa é obrigada a trocar ao entrar.

> **Acrescentado a 2026-09-30, à tarde:** há um segundo comando,
> `riftvault conta <nome> --definir-password`, que pergunta a password **duas
> vezes e não a mostra** (`getpass`) e a deixa escolhida de vez — sem browser e
> sem passar por uma temporária. Nasceu de um beco: a troca da temporária só se
> fazia no site, e o site escondia a caixa de «Entrar» enquanto a porta das
> contas estivesse fechada. Está resolvido nos dois lados (ver o CLAUDE.md,
> «O BECO DA PORTA FECHADA»), e este comando fica como rede de segurança:
> **uma recuperação nunca mais depende do browser.** As regras de força são as
> mesmas — é o `senha.validar` nos dois caminhos.

### Porque é que recusei ler a password

Não é por «boas práticas». É por **uma coisa concreta que acontece a toda a
gente: as pessoas reutilizam passwords.** A password que o Miguel escolher para
o riftvault é, com grande probabilidade, a do email dele. Guardá-la legível
transforma o risco de:

> «alguém mexeu no PC do André e viu as cartas de três amigos»

em:

> «alguém mexeu no PC do André e entrou no **email** de três amigos»

E o segundo não é um problema de cartas. Isto num PC de casa, ao lado de um
repositório **público** que é empurrado para o GitHub de 30 em 30 minutos —
onde um ficheiro trocado de pasta é uma fuga permanente.

**O fluxo dele não muda.** Continua a ser ele a resolver, na consola, sem
emails, sem sistemas e sem depender de nada: um comando, uma password nova,
três linhas para mandar pelo WhatsApp. O que muda é que já não existe nada que
possa vazar — e por isso a pergunta «e se alguém ler o ficheiro?» deixa de ter
resposta má.

### O que se guarda, e como

`scrypt` da biblioteca padrão, **n=2^16, r=8, p=1**, sal de 16 bytes por
pessoa. **Medido na máquina dele a 2026-09-30:** 32 ms a n=2^14, 64 ms a 2^15,
**130 ms a 2^16**, 262 ms a 2^17. Escolheu-se o de 130 ms — imperceptível para
quem entra uma vez por mês, e 130 ms × 67 MB de memória por tentativa para quem
atacar o ficheiro.

**Armadilha medida:** o `hashlib.scrypt` passa `maxmem=0` ao OpenSSL, que são
32 MB, e o n=2^16 quer 67 — sem o argumento explícito isto rebentava na
primeira password.

O hash guardado **diz como foi feito** (`scrypt$65536$8$1$sal$hash`): o dia em
que estes parâmetros ficarem baratos, sobe-se o `N` e as passwords antigas
continuam a entrar, recifradas na primeira vez que a pessoa entra. Guardar só o
hash e presumir os parâmetros era prender-se a eles para sempre.

### A password temporária

Quatro palavras de uma lista de 256 e dois dígitos —
`varanda-tigre-bolo-chave-47`. **38,6 bits**, ou 4×10^11 combinações: offline,
a 130 ms cada, são ~1 600 anos de um núcleo; online, com o travão, é
inalcançável. As palavras são ASCII, 3 a 6 letras, sem acentos nem cedilha — há
que as ditar ao telefone —, e os hífens dizem onde cada uma acaba.

**Vive uns minutos**: quem entra com ela não pode fazer mais NADA senão trocá-la
(ver §3b). O tempo de vida dela é o tempo que o amigo leva a abrir o WhatsApp.

### As regras da password que a pessoa escolhe

**Dez caracteres, e recusam-se as óbvias.** Não há exigência de maiúscula,
dígito e símbolo, e é uma decisão: essa regra produz `Password1!` e um post-it
no monitor. Dez caracteres de uma frase que a pessoa se lembre valem mais.
Recusam-se: as da lista das mais usadas (com os dígitos do fim ignorados —
`password12345` continua a ser `password`), o próprio nome de utilizador, o
nome dela, um caractere repetido, e espaços nas pontas (perdem-se ao copiar e
colar, e depois ela não entra e não sabe porquê).

### NÃO HÁ REGISTO ABERTO

As contas nascem de `riftvault conta --criar <nome>` e de mais lado nenhum. A
rota `/api/conta/registar` responde **403** com o que fazer, e há teste que
tenta criar uma conta por todos os caminhos que restam. É o que ele quer —
*"entre amigos"* — e tem a vantagem de não haver formulário público onde bater.

**Não é uma chave de config**, de propósito: uma chave num ficheiro commitado
está a um merge de distância de abrir o registo sem ninguém ter decidido nada.
É uma constante no código (`rotas_conta.REGISTO_ABERTO`).

---

## 1. O OAuth ficou, parado

O caminho de 29/09 — entrar com Google ou Discord — **não se apagou**. Está
inteiro e testado, e um dia pode servir (é a forma de ele não ter de gerir
password nenhuma). Ordem dele, 2026-09-30: *"Nao apagues o codigo do Discord e
do Google […] Sem segredo configurado, o botao simplesmente nao aparece. O
`auth.discord.client_id` que ja esta no config fica onde esta."*

O que continua a valer, e que foi bem pensado na altura:

### O que se guarda de cada pessoa

`provedor` + `sub` (o identificador dela nesse fornecedor) + o `user_id` daqui.
**Nenhum token do fornecedor é gravado**: o `access_token` serve uma pergunta
(«quem és tu?») e morre no mesmo pedido. Não se pede o email — o `sub` é que
identifica, e é menos um dado de terceiros num PC de casa
(`scope` = `openid profile` no Google, `identify` no Discord).

### Não se verifica o `id_token` à mão

Validar a assinatura de um JWT exige JWKS, rotação de chaves e RSA, e é um dos
sítios clássicos de falhas (`alg: none`, `kid` não verificado, expiração
esquecida). Em vez disso pergunta-se ao fornecedor, por TLS, com o
`access_token`: `userinfo` no Google, `users/@me` no Discord. **Quem autentica
a resposta é o TLS** — a mesma garantia em que a troca do código já assenta — e
não há criptografia nossa para correr mal.

**Uma diferença desde 30/09:** entrar por um fornecedor **não cria conta**. Quem
entre sem ter conta aqui vê uma frase a dizer que é o André que as cria. O
`riftvault multi --ligar` (o código de uso único da consola) continua a ser o
caminho para LIGAR um fornecedor a uma conta que já existe.

---

## 2. ONDE VIVEM AS CREDENCIAIS — e a armadilha que quase se repetiu

`data/auth.db`, ficheiro à parte, **no `.gitignore`**. Com passwords lá dentro
(2026-09-30) isto passou de cuidado a essencial: um hash publicado no GitHub é
um hash que qualquer pessoa pode atacar com todo o tempo do mundo, e uma
password reutilizada que caia é uma conta de email de um amigo.

A `1-multi-guardas` propôs pô-las na «base do sistema», que é o
`data/vault.db`. Mediu-se antes de aceitar:

```
$ git ls-files data/          ->  data/vault.db
$ git remote -v               ->  https://github.com/Baverone/riftvault.git  (PÚBLICO)
```

e a tarefa `riftvault-publicar` faz commit e push **de 30 em 30 minutos**. O
`sub` do Google é um identificador estável e único de uma pessoa: ali dentro
ficava publicado para sempre, com histórico, e não se despublica um repositório
com 95 commits.

**É a mesma armadilha que levou a `0-multi-utilizador-1` a pôr cada coleção num
ficheiro seu** — e ela tinha ficado a dois metros de distância: a tabela `users`
estava do lado público, e registar um amigo publicava-lhe o nome e o slug (mesmo
com a coleção privada, a *existência* dele ficava no GitHub). Foi corrigido na
mesma corrida: o registo passou a `data/users/registo.db`, fora do Git, e cada
`vault.db` só tem a linha do seu dono.

**Consequência escrita:** `users.auth_ref` fica **vazia**. Nem um ponteiro
opaco. O mapa identidade→utilizador existe num sítio só, e esse sítio não vai
para o Git.

Efeitos laterais bons: um `git clone` do repositório público não traz sessões de
ninguém, e um `git checkout` de um commit antigo não ressuscita uma sessão
expirada nem uma identidade apagada.

---

## 3. Sessões

| propriedade | valor | porquê |
|---|---|---|
| `HttpOnly` | sim | o JavaScript não lhe chega: um XSS não a rouba |
| `SameSite` | `Lax` | **não `Strict`**: a volta do fornecedor é uma navegação que vem de outro site, e com `Strict` o cookie não seguia e a entrada nunca se concluía. `Lax` deixa passar a navegação de topo e continua a travar os pedidos de terceiros |
| `Secure` | só em HTTPS | no 8770 de casa é `http://`; um `Secure` ali fazia o browser descartar o cookie e a sessão nunca pegava |
| `path` | `/` | — |
| duração | 30 dias, renovados ao usar | ele mexe na coleção com o telemóvel e não quer entrar a cada vez; um mês é pouco para um cookie roubado servir de chave permanente |

**Na base está o SHA-256 do que está no cookie.** Quem leia o ficheiro não fica
com uma sessão utilizável — a mesma ideia de guardar hashes em vez de
passwords. Há teste que abre o `auth.db` em bruto e confirma que o valor do
cookie não aparece lá dentro.

**Rotação no login.** Uma sessão nasce sem dono (`user_id` a NULL) enquanto a
pessoa escolhe o nome do endereço. Ao criar a conta o identificador é
**substituído** e o antigo apagado: o valor que andou pelo browser antes de
haver conta não é o que passa a dar acesso à conta. Se alguém tivesse fixado
aquele cookie, deixa de valer no instante em que a conta nasce.

### CSRF

Token por sessão, exigido em **todos** os métodos que escrevem, num
**cabeçalho** (`X-CSRF-Token`) e não num cookie — num cookie era enviado pelo
browser junto com o pedido falso, que é exactamente o que isto trava.

No cliente havia **17** `fetch` de POST, cada um com o seu literal de
cabeçalhos. Passaram todos por **uma** função (`cabecalhos()`), e há teste que
lê o `app.js` e rebenta se aparecer um POST que não passe por ela. Acrescentar
a marca a 17 sítios à mão era garantir que um dia se esquecia num — e um
esquecido é uma rota sem protecção, não um erro visível.

### A entrada por password não pode usar a marca de CSRF — e o que a protege

Quem está a entrar ainda não tem sessão, logo não tem marca nenhuma. O que se
faz em vez disso: **a rota exige `Content-Type: application/json`** (415 se não
vier). Um `<form>` de outro site não consegue mandar JSON — o browser obriga a
um pedido prévio de permissão (CORS preflight) que nós não respondemos.

O que isto trava chama-se **login CSRF** e não é teórico aqui: alguém levar o
browser do André a entrar numa conta que não é a dele, e o que ele escrevesse a
seguir ia para a coleção do atacante, a pensar que era a dele. É o mesmo
problema que o `nonce` resolve no caminho do OAuth.

### A PASSWORD TEMPORÁRIA TRANCA O SITE ATÉ SER TROCADA

Ordem dele: *"Quem entra com uma temporaria e OBRIGADO a trocar antes de fazer
seja o que for"*. Com uma temporária, **tudo o que é `/api/` responde 403**
menos duas rotas: o `api/conta.json` (para a página saber o que mostrar) e o
`api/conta/senha` (a troca). O resto — o `index.html`, o `app.js`, o CSS — passa,
senão não havia página onde mostrar o formulário; e o `/sair` funciona.

**Bloqueia as LEITURAS e não só as escritas**, e é a parte que interessa: a
temporária andou por uma aplicação de mensagens. Quem a apanhasse no caminho
podia não escrever nada e ler a coleção toda. Uma password que passou pelo
WhatsApp vale para trocar a password, e mais nada.

O estado lê-se **a cada pedido** e não se guarda na sessão: assim a troca
liberta o site no pedido seguinte, sem ter de entrar outra vez. É um `SELECT`
por chave primária numa tabela com tantas linhas quantos os amigos dele.

**Trocar a password fecha TODAS as sessões dela** e abre uma nova. Se alguém
tinha o cookie (que é a razão de estar a trocar), deixa de valer; entrar outra
vez no telemóvel é o preço, e é o que se espera de uma troca de password.

### Tecto de tentativas

**No OAuth:** 20 por hora e por endereço (`auth.tentativas_por_hora`). Não é uma
password que se adivinhe; o que isto trava é usar o riftvault como amplificador
de pedidos ao Google à custa do IP dele.

**NA PASSWORD (2026-09-30) é outro travão, porque uma password ADIVINHA-SE.**
Conta FALHAS na última hora, em duas dimensões, e faz esperar cada vez mais:

| | de graça | porquê esse número |
|---|---|---|
| por **conta** | 5 falhas | uma password ditada pelo WhatsApp escreve-se mal duas ou três vezes; quem se engana tem de poder tentar sem ir pedir ajuda |
| por **endereço** | 10 falhas | o dobro, porque um endereço pode ser uma casa inteira: dois amigos atrapalhados no mesmo wi-fi não se trancam um ao outro |

A escada, a contar da **última** falha: **1 → 5 → 15 → 60 minutos**. Ao quarto
patamar está numa hora, que é a janela de contagem: no pior caso são ~9
tentativas por hora contra 4×10^11 combinações. Um ataque de dicionário
desiste.

**As duas dimensões fazem falta as duas:** só por endereço, quem tivesse muitos
endereços (qualquer pessoa com dados móveis) batia à vontade numa conta; só por
conta, alguém podia varrer nomes de utilizador à vontade. A chave do balde do
endereço é falsificável — e não faz mal: falsificá-la dá mais baldes, não dá
acesso a nada. Em sítio nenhum do código o endereço decide **quem** alguém é.

**Não há bloqueio permanente**, de propósito: era a maneira de um estranho
tirar o riftvault a um amigo só por lhe saber o nome. E o travão corre **antes**
do scrypt — verificar primeiro fazia cada tentativa custar 130 ms, e era isso
que punha o PC dele de joelhos.

**A mesma mensagem para «não existe» e «password errada»**, e a falha conta nos
dois casos: mensagens diferentes (ou tempos diferentes) diziam a um estranho
que nomes de utilizador existem, e o nome é metade do que ele precisa.

---

## 4. A DECISÃO DA LAN — e o facto que a decidiu

O CLAUDE.md diz, desde o início: *«O modo edição não tem autenticação nenhuma:
quem chegar ao URL escreve na coleção. É aceitável na LAN, não é na internet.»*
Com coleções de amigos lá dentro, deixa de ser aceitável na LAN — o risco já não
é só dele para assumir.

Pensou-se em confiar no endereço de quem pede («se vem de casa, é ele»).
**Não se pode, e a razão é concreta e verificável:**

```
cloudflared tunnel run --url http://localhost:8770 riftvault
```

O túnel faz um pedido a `localhost:8770`. **Todo o tráfego da internet chega ao
Flask como `127.0.0.1`.** Uma regra que confiasse no loopback dava a identidade
do André a qualquer visitante do mundo. Por isso:

> **Não há atalho por endereço. Nem loopback, nem sub-rede, nem cabeçalho.** Em
> sítio nenhum do `rotas_conta.py` se lê o `remote_addr` para decidir quem é
> alguém — só para contar tentativas.

> ### ⚠ A CONCLUSÃO DESTA SECÇÃO ESTAVA ERRADA, e deu um buraco (2026-10-01)
>
> O FACTO acima continua verdadeiro — medido outra vez a 01/10. Errada era a
> conclusão: de «o loopback não prova que é ele» tirou-se «não se pode
> distinguir nada», e daí **«então a porta decide»**. O resultado foi que
> `multi.aberto: false` DESLIGAVA a autenticação, e com o túnel vivo isso era
> escrita anónima na coleção dele a partir da internet; e um pedido sem sessão
> caía na base do utilizador 1, sem a privacidade ser consultada.
>
> **Hoje quem manda na autenticação é a ORIGEM do pedido, não a porta.** A
> pergunta mudou de forma: não «isto vem de fora?» mas **«isto é
> inequivocamente de casa?»** — um E de três condições (endereço da rede de
> casa, nenhum cabeçalho de intermediário, não pediu o anfitrião público).
> Medido contra o túnel a sério: nove sinais, cada um suficiente sozinho, e a
> Cloudflare não reescreve o `Host`. Ver **`docs/origem-do-pedido.md`** e o
> `riftvault/origem.py`. As duas linhas abaixo são as de 29/09 e valem hoje
> **só para quem está em casa**.

O que fica, em duas linhas (**em casa**; de fora exige-se sessão sempre, ver o
aviso acima):

- **Porta FECHADA** (`multi.aberto: false`): um dono só, sem autenticação, tudo
  **exactamente** como ontem. Não há dados de terceiros para proteger, e ele não
  fica fechado fora da sua própria app às duas da manhã.
- **Porta ABERTA**: toda a escrita exige sessão e CSRF, **ele incluído**. Entra
  uma vez e a sessão dura 30 dias — é o que já faz com o telemóvel.

E o travão que fecha o círculo: **o `riftvault multi --verificar` recusa abrir
enquanto ele não puder entrar** (password definida, ou um fornecedor ligado).
Assim nunca se abre a porta com ele do lado de fora.

### O `RIFTVAULT_USER` é uma armadilha num servidor

`utilizador.atual()` lê essa variável de ambiente, que é **global ao processo**.
Num servidor `threaded` isso significaria todos os pedidos a cair no mesmo dono.
Por isso o servidor **passa sempre o `user_id` explícito** ao `db.connect` e
nunca depende do `atual()`, e há um guarda que se recusa a servir com a porta
aberta e a variável definida.

---

## 5. Porque é que isto é seguro por construção

A `0-multi-utilizador-1` pôs cada coleção num **ficheiro** seu. O servidor só
abre a base do dono da sessão. Não existe caminho de código que abra a base de
outra pessoa para escrever:

> não é um `WHERE user_id` que se pode esquecer — é um ficheiro que não se chega
> a abrir.

As rotas de escrita herdam isto sem uma linha cada (são 23 a 2026-10-02; o
número vive na asserção do `tests/test_contas.py`, e é uma só). Mesmo assim
testam-se todas, uma por uma, porque «não devia ser possível» não é uma
medição.

### O FURO QUE ISTO NÃO TAPA — e que a medição encontrou

A separação por ficheiro cobre tudo o que está numa **base de dados**. Duas
rotas não estão:

```
POST /api/decks/montar     -> decks.alternar_montado()   -> decks.montados
POST /api/decks/principal  -> decks.escrever_principal() -> decks.principal
```

Estas escrevem no **`riftvault_config.json`**, que é **um ficheiro para todos**.
Um amigo autenticado a carregar em «Montar» escrevia o slug do deck dele na
lista do André. Não é uma leitura indevida — é uma **escrita cruzada**, e escapa
a um `authorizer` do `sqlite3` por não passar pelo SQLite.

Medido: varrido o `decks.py`, há **três** funções a escrever no config
(`alternar_montado`, `escrever_principal`, `apagar_todos`) e só as duas
primeiras têm rota; a terceira é da CLI.

Ficam em `rotas_conta.SO_DO_DONO`, com 403 e uma frase que explica, para quem
não é o utilizador 1. Três testes: as rotas recusam; **o ficheiro de config não
mexeu** depois da tentativa (não é só o código de resposta); e um que varre o
`decks.py` e **dá vermelho se aparecer outra função a escrever no config
partilhado** — para isto não voltar a passar por descuido.

**A lição, para a fatia seguinte:** num sistema multi-inquilino, «onde é que
isto se guarda?» tem de ser perguntado a cada escrita, não só às tabelas. Um
ficheiro de configuração é estado partilhado tanto quanto uma tabela sem
`user_id`.

---

## 6. Os endereços — e o `Miguel.riftvault` que ele pediu

Ele escreveu *«ao invés de Baverone.riftvault seria Miguel.riftvault»*. Fica o
nome, **com uma barra em vez de um ponto**:

```
rift.baverone.com/u/miguel/
```

A razão é medida. Os sites públicos estão no **GitHub Pages**, que aceita **um**
endereço personalizado por repositório e **não** aceita `*.rift.baverone.com`.
Para ser `miguel.rift.baverone.com` seria preciso ou um repositório por amigo,
ou pôr a Cloudflare a reescrever endereços à frente do GitHub — mais uma peça
para manter, e uma peça cuja falha tira os sites do ar.

A forma com barra funciona **hoje**, sem infraestrutura nova. O nome que ele
escolhe é o mesmo nas duas formas, por isso a escolha não fica presa: se um dia
se quiser o ponto, muda-se o gerador e não o que os amigos escreveram.

### Dois endereços com papéis diferentes, e é de propósito

| endereço | quem serve | de onde | se o PC estiver desligado |
|---|---|---|---|
| `rift.baverone.com/u/<slug>/` | quem só espreita | GitHub Pages (estático) | **continua a abrir** |
| `editar.baverone.com` | quem edita, autenticado | o PC dele, pelo túnel | não abre |

É a forma recomendada na `0-multi-utilizador-1` e mantém-se: **o PC dele fica
fora do caminho de quem só espreita**, que é a maior parte do tráfego e do
risco. Um site público não depende da máquina estar ligada; no pior caso quem
edita espera.

---

## 7. Privacidade: uma coleção nova nasce PRIVADA

`users.publico` (da `1-multi-guardas`): `nada` | `sem-valores` | `tudo`, com
**`nada`** por omissão. O André fica em `tudo`, que é o que já tem.

A razão do default mais fechado: publicar a coleção de outra pessoa tem de ser
um acto **escolhido**. Uma página publicada indexa-se e, na prática, não se
despublica. Os amigos vão presumir que o deles é privado — e vão ter razão.

Enquanto a porta estiver fechada, o `build.py` publica **só** o dele e nada
mais, mesmo que existam linhas na `users`. Quando começar a publicar os outros,
sai tudo com `noindex` até ele dizer o contrário.

---

## 8. Limites, e dois dispositivos a escrever ao mesmo tempo

**Tamanho do pedido: 256 KB** (`rotas_conta.CORPO_MAXIMO`, com um `413` que
explica). Quase tudo o que a app manda é um `printing_id` e um delta (~80
bytes); o `/api/local/marcar` é a excepção, porque manda uma LISTA de linhas e
marcar uma coleção à mão são centenas. Sem tecto nenhum, um corpo de 2 GB é um
ataque de uma linha.

**Por sessão:** não há tecto de pedidos por sessão, e é uma escolha. O que uma
sessão consegue fazer é escrever na coleção DELA, e o `request_id` já impede que
um clique conte duas vezes; um tecto ali só atrapalharia quem está a marcar uma
caixa de cartas ao domingo. O tecto que existe é no que ainda **não** tem
sessão — a entrada, 20 por hora e por endereço —, que é onde um estranho pode
bater.

**Dois dispositivos do mesmo utilizador, ao mesmo tempo: já estava resolvido, e
continua.** É a decisão de 2026-09-01 («cliques rápidos: deltas idempotentes,
não debounce»), e ela sobrevive intacta ao multi-utilizador:

- o cliente manda `{printing_id, delta, request_id}` e o servidor faz
  `qty = qty + delta` dentro de um `BEGIN IMMEDIATE`. Dois dispositivos a somar
  +1 dão **+2**, não +1: os deltas não se perdem porque nenhum deles lê-e-escreve
  um valor absoluto;
- `ops.request_id` é `UNIQUE`, por isso um retry do telemóvel com sinal fraco
  devolve o resultado guardado em vez de contar outra vez;
- e agora **cada um escreve no SEU ficheiro**, o que torna a disputa ainda mais
  rara: dois utilizadores diferentes nunca disputam o mesmo `vault.db`. A
  serialização do SQLite só tem de resolver o caso de uma pessoa em dois
  dispositivos.

O que a sessão acrescenta a isto é pouco e de propósito: a escrita do
`visto_em`/`expira_em` (o «a sessão dura enquanto se usa») está limitada a **uma
vez por hora** por sessão. Sem isso, uma página da Coleção — que puxa o payload,
o índice e dezenas de imagens — fazia dezenas de `UPDATE` no `auth.db` por
visita, e o custo não comprava nada.

## 9. O que ficou de fora desta fatia, e porquê

- **Config por utilizador.** As regras do `riftvault_config.json` (`foil.raridades`,
  `master_set.*`, alvos, `decks.*`, `selado.*`) continuam **globais**: um amigo
  herda as regras dele. São decisões de coleção que ele tomou ao longo de um mês
  e que um amigo pode querer diferentes (um pode não colecionar foils). É
  limitação conhecida, está no `docs/multi-utilizador.md` com a separação
  proposta, e não se inventou aqui um config por utilizador de véspera.
- **Ligar/desligar um segundo fornecedor pela página.** O modelo aguenta (a
  `user_auth` tem chave `(provedor, sub)` e vários por `user_id`), e a página
  mostra os que estão ligados. Falta o botão de acrescentar. Não é preciso para
  entrar nem para editar.
- **Convites.** Com a porta aberta, quem chegar ao endereço registra-se. Se ele
  quiser só amigos, o mais simples é uma lista de `sub` permitidos — mas isso
  exige que ele recolha os `sub` de cada um, o que é pior do que parece. Fica
  como pergunta.
- **Mudar de slug depois de criado.** O endereço é o slug e mudá-lo parte os
  links que o amigo já deu. Não se faz sem ele decidir o que acontece ao antigo.

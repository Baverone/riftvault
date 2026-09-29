# Contas e autenticação — o desenho, e o que o decidiu

Fatia `2-multi-contas`, 2026-09-29. Vem a seguir a `0-multi-utilizador-1` (o
modelo de dados, `docs/multi-utilizador.md`) e a `1-multi-guardas` (o
isolamento, a privacidade e o interruptor).

O guia dos passos DELE está em `docs/abrir-a-porta.md`. Este ficheiro é o
porquê.

---

## 1. Nenhuma password, e o que isso dá de graça

Não há campo de password, não há hash, não há «esqueci-me da minha». Quem entra
prova quem é ao **Google** ou ao **Discord**, e o riftvault fica com um ponteiro.

Não é preguiça: é o que se evita.

| o que não existe | logo não pode correr mal |
|---|---|
| tabela de passwords | não há nada para vazar num PC de casa |
| «recuperar password» | não há email a enviar nem token a expirar mal |
| política de força | não há utilizador a reutilizar a password do banco |
| bcrypt/argon2 e os parâmetros | não há escolha de custo errada em 2029 |

**Recomendado: Discord primeiro.** A malta de TCG já o tem, e a aplicação
fica pronta em cinco minutos. O Google obriga a um ecrã de consentimento que,
para contas que não a dele, passa por verificação — pode levar dias. Os dois
podem estar ligados ao mesmo tempo e a mesma pessoa pode usar qualquer deles.

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

---

## 2. ONDE VIVEM AS CREDENCIAIS — e a armadilha que quase se repetiu

`data/auth.db`, ficheiro à parte, **no `.gitignore`**.

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

### Tecto de tentativas

20 por hora e por endereço (`auth.tentativas_por_hora`). Não é uma password que
se adivinhe; o que isto trava é usar o riftvault como amplificador de pedidos ao
Google à custa do IP dele. A chave do balde é o endereço, **que é
falsificável** — e não faz mal: falsificá-lo dá mais baldes, não dá acesso a
nada. Em sítio nenhum do código o endereço decide **quem** alguém é.

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

O que fica, em duas linhas:

- **Porta FECHADA** (`multi.aberto: false`, o de hoje): um dono só, sem
  autenticação, tudo **exactamente** como ontem. Não há dados de terceiros para
  proteger, e ele não fica fechado fora da sua própria app às duas da manhã.
- **Porta ABERTA**: toda a escrita exige sessão e CSRF, **ele incluído**. Entra
  uma vez com o Discord e a sessão dura 30 dias — é o que já faz com o
  telemóvel.

E o travão que fecha o círculo: **o `riftvault multi --verificar` recusa abrir
enquanto a conta dele não estiver ligada a um fornecedor.** Assim nunca se abre
a porta com ele do lado de fora.

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

As 20 rotas de escrita herdam isto sem uma linha cada. Mesmo assim testam-se
todas, uma por uma, porque «não devia ser possível» não é uma medição.

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

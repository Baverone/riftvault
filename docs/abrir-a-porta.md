# Abrir a porta aos amigos — os teus dois passos

> **Para o André.** Está tudo construído e testado. Falta o que só tu podes
> fazer, porque precisa das tuas contas: eu não crio contas em teu nome nem
> toco no teu domínio.
>
> **Nada está aberto.** O `multi.aberto` está em `false`: hoje o riftvault é de
> um dono só, exactamente como ontem. Ninguém se pode registar, e o teu site
> público não tem sinal nenhum de que isto existe — nem um link de login. Tu é
> que abres, quando quiseres, e o comando do fim desta página recusa abrir
> enquanto faltar alguma coisa.
>
> **ERAM TRÊS PASSOS E SÃO DOIS.** O primeiro era criar uma aplicação no
> Discord, para os teus amigos entrarem sem password. Pediste o contrário —
> *"em vez de discord, nao era melhor a pessoa criar uma conta com usuario e
> password"* — e por isso esse passo desapareceu: as contas e as passwords são
> tuas, feitas por ti na consola, e não é preciso pedir nada a ninguém. O que
> falta é só o que põe isto acessível de fora de casa.
>
> Lê a página toda antes de começares. São ~30 minutos, e o passo 2 tem uma
> espera que não depende de ti.

---

## Antes de tudo: a única coisa que pode correr mal

O passo 2 muda **quem responde pelo `baverone.com`**. Se correr mal, os teus
cinco sites deixam de abrir — não se apagam, mas ficam inacessíveis até se
corrigir.

Estes são os cinco que têm de continuar a funcionar:

| endereço | o que é |
|---|---|
| `baverone.com` | a tua página de entrada |
| `rift.baverone.com` | **o riftvault** |
| `mtg.baverone.com` | o mtgvault |
| `baiak.baverone.com` | o baiakvault |
| `tibia.baverone.com` | o tibiavault |

**A regra de ouro do passo 2: antes de mudares os nameservers, confirmas que a
Cloudflare já tem os cinco. Se faltar um, não mudes nada** — escreve-o à mão
primeiro. A ordem certa é *copiar e confirmar, e só depois trocar*.

Há uma verificação no fim de cada passo. Faz sempre.

---

## Passo 1 — a conta na Cloudflare

**Para quê:** para os teus amigos chegarem ao teu PC de fora de casa **sem
abrires uma porta no teu router e sem o teu IP aparecer em sítio nenhum**. O
teu PC faz uma ligação de saída para a Cloudflare e é por dentro dela que o
tráfego entra. É por isso que isto não contraria a regra de nunca publicar o IP
da tua LAN.

1. **https://dash.cloudflare.com/sign-up** → cria a conta (email + password).
   Plano **Free**. Confirma o email.

Fica aqui. **Não adiciones o domínio ainda** — isso é o passo 2, e a ordem
importa.

### Verificação do passo 1

Consegues entrar em `dash.cloudflare.com` e vês um painel vazio. É tudo.

---

## Passo 2 — o domínio e o túnel

Este é o passo com risco. Faz-se em cinco partes e há uma confirmação a meio
que **não deves saltar**.

### 2a. ESCREVE O QUE TENS AGORA (cinco minutos que te salvam a noite)

Vai ao sítio onde compraste o `baverone.com` (o registrar) e abre a zona de
DNS. **Tira uma fotografia ao ecrã** e copia para um ficheiro de texto todas as
linhas. Guarda também os **nameservers actuais** (algo como `ns1.xxx.com`) — é
o caminho de volta se quiseres desfazer.

Vais precisar de reconhecer estas:

| tipo | nome | valor esperado |
|---|---|---|
| A (quatro linhas) | `@` ou `baverone.com` | `185.199.108.153`, `.109.153`, `.110.153`, `.111.153` |
| CNAME | `rift` | `baverone.github.io` |
| CNAME | `mtg` | `baverone.github.io` |
| CNAME | `baiak` | `baverone.github.io` |
| CNAME | `tibia` | `baverone.github.io` |

(Os quatro endereços `185.199.*` são do GitHub Pages. Podes ter em vez deles
registos `AAAA`, ou um `ALIAS`/`ANAME` no apex — copia o que **tiveres**, não o
que esta tabela diz.)

### 2b. Adicionar o domínio à Cloudflare

1. No painel: **Add a site** → escreve `baverone.com` → **Continue**.
2. Plano **Free** → **Continue**.
3. A Cloudflare vai **ler sozinha** os teus registos e mostrar uma lista.

### 2c. A CONFIRMAÇÃO QUE NÃO SE SALTA

Compara a lista da Cloudflare com o que escreveste em 2a, **linha por linha**.

- **Os cinco nomes estão lá?** (`baverone.com`, `rift`, `mtg`, `baiak`,
  `tibia`)
- **Falta algum?** Acrescenta-o à mão, agora, com **Add record**, com o valor
  que copiaste.

Depois, e isto é importante:

> **Põe todas as linhas do GitHub Pages em «DNS only» — a nuvem CINZENTA, não
> a laranja.** Clica na nuvem para alternar.
>
> Porquê: com a nuvem laranja a Cloudflare põe-se no meio, e o certificado
> HTTPS do GitHub Pages deixa de se conseguir renovar. O sintoma aparece
> semanas depois — o site começa a dar aviso de segurança — e é chato de
> diagnosticar. Cinzento é a Cloudflare a ser só a lista telefónica, que é o
> que precisas aqui.

**Se qualquer coisa não bater certo, para e não avances.** Nada aconteceu
ainda: enquanto não mudares os nameservers, a Cloudflare está a preparar uma
zona que ninguém usa.

### 2d. Mudar os nameservers

A Cloudflare dá-te dois nomes (tipo `ana.ns.cloudflare.com` e
`bob.ns.cloudflare.com`). Vais ao **registrar** (não à Cloudflare), procuras
«Nameservers» / «Servidores de nomes», escolhes «personalizado» e substituis os
que lá estão pelos dois da Cloudflare. Guarda.

Agora **espera**. Costuma levar de 10 minutos a 2 horas; pode chegar a 24. A
Cloudflare manda-te um email a dizer «is now active».

**Durante a espera os sites continuam a funcionar** — os nameservers antigos
ainda respondem enquanto a mudança se propaga. É normal que uns computadores
vejam a zona nova e outros a antiga durante umas horas.

### 2e. Verificação do passo 2 — ANTES de instalar o túnel

Abre um separador e confirma **os cinco**, um por um:

- https://baverone.com
- https://rift.baverone.com ← **este é o riftvault; tem de abrir a tua coleção**
- https://mtg.baverone.com
- https://baiak.baverone.com
- https://tibia.baverone.com

Confirma também o **candado** do HTTPS em cada um.

> **Se o `rift.baverone.com` não abrir:** vai à Cloudflare → DNS → confirma que
> existe `CNAME rift → baverone.github.io` e que a nuvem está **cinzenta**.
> Nove de dez vezes é isso. Se quiseres desfazer tudo, volta ao registrar e
> repõe os nameservers que escreveste em 2a.

Só depois de os cinco abrirem é que avanças.

### 2f. O túnel

Agora sim, o que deixa os amigos editar de fora de casa.

1. Instala o cloudflared. Num terminal:
   ```
   winget install --id Cloudflare.cloudflared
   ```
2. Liga-o à tua conta (abre o browser e pede para escolheres `baverone.com`):
   ```
   cloudflared tunnel login
   ```
3. Cria o túnel:
   ```
   cloudflared tunnel create riftvault
   ```
4. Dá-lhe o endereço — é o que está em `auth.base_url` do config:
   ```
   cloudflared tunnel route dns riftvault editar.baverone.com
   ```
5. Diz-lhe para onde apontar — **a porta 8770, que é onde o teu riftvault
   corre**:
   ```
   cloudflared tunnel run --url http://localhost:8770 riftvault
   ```

> **A porta 8770 é a real e nunca é ensaio.** A base de ensaio corre na 8779 e o
> túnel não a conhece: não há maneira de o túnel apontar para dados de
> brincar, nem de um ensaio aparecer na internet.

### Verificação do passo 2f

Com o `riftvault serve` a correr, abre **https://editar.baverone.com** no
telemóvel, **fora do wi-fi de casa** (com dados móveis). Tem de aparecer o
riftvault e, na barra do lado, uma caixa a pedir **Utilizador** e **Password**.

---

## Antes de abrir: a TUA password (um minuto, e é importante)

**Faz isto antes de abrir a porta.** Depois de abrires, escrever passa a exigir
entrar — e sem password ficas do lado de fora da tua própria coleção. O
`--verificar` não te deixa abrir sem isto, de propósito.

Tu já existes: és o utilizador **1**, com o nome `baverone`, e tens a coleção
toda. O que te falta é uma password. **Este é o comando:**

```
riftvault conta baverone --definir-password
```

Ele pergunta-a **duas vezes e não a mostra** (não aparece nada no ecrã enquanto
escreves — é normal). Pelo menos 10 caracteres; uma frase curta serve, tipo
`o meu gato dorme muito`. Não precisa de maiúsculas nem de símbolos. Fica
escolhida de vez, num passo só.

> **Isto era mais complicado até 2026-09-30, à tarde, e era um beco.** O
> comando era o `--nova-password`, que te dá uma password **temporária** —
> depois tinhas de abrir o site e trocá-la. Só que o site escondia a caixa de
> «Entrar» enquanto a porta estivesse fechada: não abrias sem trocar e não
> trocavas sem abrir. Está resolvido nos dois lados — a caixa aparece sempre no
> `riftvault serve`, e agora há este comando que resolve tudo na consola.

**Pelo site também dá**, se preferires: com o `riftvault serve` a correr, a
caixa «Entrar» está na barra do lado, com a porta fechada e tudo. Entras com a
temporária e ele pede-te logo uma tua — **com a temporária não dá para fazer
mais nada**, e é de propósito.

> **Nem eu consigo ler a tua password depois disso**, e é a mesma regra para
> todos: o que fica guardado não se desfaz de volta. Se a perderes, corres o
> mesmo comando outra vez e escolhes outra. Não há nada a recuperar porque não
> há nada legível para recuperar.

Confirma:

```
riftvault multi --verificar
```

Tem de dizer **`Tu consegues entrar: tens password definida`**. Enquanto a tua
for a temporária, ele continua a dizer que falta — abrir a porta com a
temporária era abri-la contigo meio de fora.

---

## Criar a conta de um amigo

**As contas não se criam sozinhas.** Não há registo no site: quem chegar lá sem
conta vê uma frase a dizer para te pedir uma. É o que tu querias — *"isto e uma
coisa caseira, para usar entre amigos"* — e quer dizer que ninguém entra sem
passar por ti.

### 1. Cria a conta

```
riftvault conta --criar miguel
```

(o nome é o que fica no endereço da coleção dele: `rift.baverone.com/u/miguel/`.
Só minúsculas, números e hífens. Se ele se chamar diferente do endereço, usa
`--nome "Miguel Silva"`.)

Ele escreve algo assim:

```
Conta criada: miguel

  Manda-lhe isto, e mais nada:

      Endereço:   https://editar.baverone.com
      Utilizador: miguel
      Password:   varanda-tigre-bolo-chave-47

      (é temporária — o site pede-lhe uma dela na primeira vez)

Esta password aparece AQUI e em sítio nenhum mais: fica guardada
cifrada, e nem tu a consegues ler outra vez. Se ela se esquecer,
corre `riftvault conta miguel --nova-password` e dá-lhe outra.
```

### 2. Manda-lhe as três linhas

Por WhatsApp, à vontade. A password é temporária e **só serve para ele escolher
uma dele** — assim que ele a trocar, aquela que andou pelo WhatsApp deixa de
valer para nada.

### 3. Quando ele se esquecer da password

Vai acontecer. **Tu não a lês** — dás-lhe outra:

```
riftvault conta miguel --nova-password
```

Escreve uma temporária nova, fecha as sessões que ele tinha abertas (se foi o
telemóvel que ele perdeu, o telemóvel sai), e ele volta a escolher uma dele na
primeira entrada.

Se ele estiver ao teu lado e for mais simples escolher a dele ali mesmo, há o
outro comando — pergunta-a duas vezes, não a mostra, e fica escolhida de vez
(não é temporária, por isso ele não tem de trocar nada a seguir):

```
riftvault conta miguel --definir-password
```

> **Porque não te dou a password dela para lhe ler ao telefone?** Porque tu
> pediste isso e eu contrapus: *«as pessoas reutilizam passwords»*. A que o
> Miguel escolher é provavelmente a do email dele. Guardá-la legível no teu PC
> transformava «alguém mexeu no meu computador» em «alguém entrou no email de
> três amigos meus» — e o estrago já não era sobre cartas. Dar uma nova custa-te
> exactamente o mesmo trabalho e não guarda nada que possa vazar.

### Ver quem existe e em que estado está

```
riftvault conta
```

```
  1  baverone         André                password definida
  2  miguel           Miguel               temporária, por trocar
```

Nunca mostra passwords — só se cada um já escolheu a dele.

### Se um amigo quiser sair

```
riftvault conta miguel --apagar --sim
```

Faz uma cópia da coleção dele primeiro (`data/backups/`), apaga a pasta dele, a
linha do registo, a password e as sessões. **Não toca na tua nem na de mais
ninguém.**

---

## E agora, abrir

```
riftvault multi --verificar
```

Ele diz, em português, o que está pronto e o que falta. **Enquanto faltar
alguma coisa, recusa-se a abrir** — não é um aviso, é um travão.

Quando estiver tudo verde:

```
riftvault multi --abrir
```

Isto muda **um** valor no config (`multi.aberto`, de `false` para `true`) e mais
nada. A partir daí:

- os amigos a quem **tu** criaste conta podem entrar em `editar.baverone.com`
  com o nome e a password que lhes deste;
- cada um edita **só** a coleção dele;
- a tua coleção continua a ser tua — ninguém a consegue escrever, e há teste
  que percorre **todas** as rotas de escrita a tentar;
- a coleção de cada amigo nasce **privada** (`publico: "nada"`): não se publica
  nada dele até ele escolher publicar. Isto é de propósito: uma página
  publicada indexa-se, e na prática não se despublica.

Para fechar outra vez, a qualquer momento:

```
riftvault multi --fechar
```

Ninguém perde nada: as contas e as coleções ficam, só deixa de se entrar.

---

## Duas coisas que é melhor saberes antes de convidares alguém

**1. O PC desligado = ninguém edita.** O túnel sai do teu PC. Com ele
desligado, ou sem o `riftvault serve` a correr, os amigos não conseguem editar
— vêem um erro da Cloudflare. **Os sites públicos continuam a abrir** (esses
estão no GitHub, não no teu PC), e é de propósito: quem só espreita nunca
depende da tua máquina estar ligada.

**2. Os dados deles ficam no teu PC, e são responsabilidade tua.** Um amigo que
peça para apagar a conta apaga-se com `riftvault conta <nome> --apagar --sim`.
Os backups da coleção dele são os teus backups. E se alguém entrar na tua
máquina, entra nas coleções todas — é o preço de ser o teu PC a servir, e é um
risco aceitável entre amigos, mas é bom que seja dito e não descoberto.

**3. Quem erra a password muitas vezes fica a esperar.** À sexta tentativa
errada na mesma conta começa uma espera que sobe: 1 minuto, 5, 15, uma hora. É
o que impede alguém de ficar a adivinhar à vontade contra o teu PC. Se um amigo
te disser «não me deixa entrar», ou é a password errada ou é isto — espera uns
minutos e tenta outra vez. **Nunca fica trancado para sempre**, de propósito:
senão bastava um estranho saber o nome dele para lhe tirar o riftvault.

---

## O «entrar com Discord» ficou feito, e desligado

Antes de tu pedires as passwords, isto entrava-se com uma conta do Discord ou
do Google. Esse caminho **está construído e testado, e ficou parado** — não se
apagou nada, e o teu `client_id` do Discord continua no config.

**Não aparece botão nenhum** enquanto não houver um segredo configurado, por
isso nada disto te incomoda. Se um dia quiseres ligá-lo (para não teres de
gerir passwords de ninguém), é criar a aplicação no Discord, meter o
`client_id` em `auth.discord.client_id` e o segredo **no ambiente**:

```
setx RIFTVAULT_DISCORD_SECRET "aqui-o-secret"
```

> **O segredo nunca vai para o config.** O `riftvault_config.json` está
> commitado num repositório **público** e é empurrado para o GitHub de 30 em 30
> minutos: um segredo lá dentro ficava publicado no histórico e a única saída
> era revogá-lo no Discord. O `multi --verificar` avisa-te se isso acontecer.

Com isso feito, quem tiver conta aqui pode ligar o Discord à conta dela e
entrar pelos dois caminhos. **Quem NÃO tiver conta continua a não se poder
registar** — entrar pelo Discord não cria uma conta; cria-a tu, como acima.

### Com o Google, se algum dia quiseres

Dá mais trabalho: precisa de um projeto na Google Cloud, de um ecrã de
consentimento, e — para contas que não a tua — de passar pela verificação
deles, que pode levar dias. Se quiseres mesmo:

1. **https://console.cloud.google.com** → cria um projeto.
2. **APIs & Services → OAuth consent screen** → External → preenche o mínimo →
   em **Test users** acrescenta os emails dos teus amigos (enquanto não estiver
   verificado, só os de teste entram).
3. **Credentials → Create Credentials → OAuth client ID** → tipo **Web
   application**.
4. **Authorized redirect URIs** → `https://editar.baverone.com/entrar/google`
5. O **Client ID** vai para `auth.google.client_id` no config; o **Client
   secret** vai para o ambiente, como o do Discord:
   `setx RIFTVAULT_GOOGLE_SECRET "aqui-o-secret"`.

Os dois podem estar ligados ao mesmo tempo; a caixa de entrada mostra um botão
por cada um que esteja configurado, por baixo do nome e da password. A mesma
pessoa pode ligar os dois à mesma conta e entrar por qualquer deles.

---

## Uma nota sobre o `Miguel.riftvault` que pediste

Tu disseste *«ao invés de Baverone.riftvault seria Miguel.riftvault»*. O nome
de cada um fica, mas **com uma barra em vez de um ponto**:

```
rift.baverone.com/u/miguel/
```

A razão é medida e não é preguiça: os sites públicos estão no **GitHub Pages**,
que só aceita **um** endereço personalizado por repositório e **não** aceita
`*.rift.baverone.com`. Para ser `miguel.rift.baverone.com` era preciso ou um
repositório por amigo, ou pôr a Cloudflare a reescrever endereços à frente do
GitHub — mais uma peça para manter, e uma peça que, se falhar, tira os sites do
ar.

A forma com barra funciona **hoje**, sem mais nada, e o nome dele continua no
endereço. Se um dia quiseres mesmo o ponto, muda-se — o nome que ele escolhe é
o mesmo nas duas formas, por isso a escolha não fica presa.

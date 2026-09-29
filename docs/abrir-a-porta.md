# Abrir a porta aos amigos — os teus três passos

> **Para o André.** Está tudo construído e testado. Falta o que só tu podes
> fazer, porque precisa das tuas contas e das tuas passwords: eu não crio
> contas em teu nome nem toco no teu domínio.
>
> **Nada está aberto.** O `multi.aberto` está em `false`: hoje o riftvault é de
> um dono só, exactamente como ontem. Ninguém se pode registar, e o teu site
> público não tem sinal nenhum de que isto existe — nem um link de login. Tu é
> que abres, quando quiseres, e o comando do fim desta página recusa abrir
> enquanto faltar alguma coisa.
>
> Lê a página toda antes de começares. São ~40 minutos, e o passo 3 tem uma
> espera que não depende de ti.

---

## Antes de tudo: a única coisa que pode correr mal

O passo 3 muda **quem responde pelo `baverone.com`**. Se correr mal, os teus
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

**A regra de ouro do passo 3: antes de mudares os nameservers, confirmas que a
Cloudflare já tem os cinco. Se faltar um, não mudes nada** — escreve-o à mão
primeiro. A ordem certa é *copiar e confirmar, e só depois trocar*.

Há uma verificação no fim de cada passo. Faz sempre.

---

## Passo 1 — a entrada («entrar com Discord»)

**Para quê:** para os teus amigos entrarem sem password. Ninguém inventa uma
password nova e tu nunca guardas nenhuma — quem confirma que o Miguel é o
Miguel é o Discord, não o teu PC.

**Recomendo o Discord** e não o Google, por duas razões: a malta de TCG já tem
Discord, e o Google obriga a um ecrã de consentimento que, para contas fora da
tua, exige verificação e pode levar dias. O Discord dá-te o que precisas em
cinco minutos. (Se preferires Google, ou os dois, está escrito no fim.)

### O que clicar

1. Vai a **https://discord.com/developers/applications** e entra com o teu
   Discord.
2. **New Application**, canto superior direito. Nome: `riftvault`. Aceita os
   termos, **Create**.
3. No menu da esquerda, **OAuth2**.
4. Copia o **Client ID** (é um número comprido). Guarda-o.
5. Ao lado, **Client Secret** → **Reset Secret** → confirma → **Copy**.
   **Este só aparece uma vez.** Se o perderes, fazes Reset outra vez.
6. Ainda em OAuth2, secção **Redirects** → **Add Redirect**, e escreve
   exactamente isto, sem barra no fim:

   ```
   https://editar.baverone.com/entrar/discord
   ```

   **Save Changes** no fundo.

> **Este endereço tem de ser igual ao caractere.** É a protecção que impede
> outra pessoa de usar a tua aplicação para se fingir de ti. Se te enganares, o
> Discord recusa a entrada com «Invalid OAuth2 redirect_uri» — não é o
> riftvault que está mal.
>
> Ainda não existe nada nesse endereço. Passa a existir no passo 3.

### Onde se escreve no riftvault — e ATENÇÃO onde NÃO se escreve

São dois valores e vão para sítios **diferentes**, de propósito.

**O Client ID vai para o config.** Não é secreto (viaja no endereço quando
alguém entra, à vista de todos). Abre `riftvault_config.json` e mete:

```json
"auth": {
  "base_url": "https://editar.baverone.com",
  "discord": { "client_id": "AQUI-O-CLIENT-ID" },
  "google":  { "client_id": "" }
}
```

**O Client Secret NÃO vai para o config.** Vai para o ambiente. Numa consola:

```
setx RIFTVAULT_DISCORD_SECRET "aqui-o-secret"
```

e **fecha essa consola e abre outra** (o `setx` só vale nas consolas novas).
Depois arranca o `riftvault serve` na consola nova.

> **Porque é que isto importa, e não é preciosismo:** o `riftvault_config.json`
> **está commitado** no repositório, e o repositório é **público** e é empurrado
> para o GitHub **de 30 em 30 minutos** pela tarefa `riftvault-publicar`. Um
> secret colado lá dentro ia para o GitHub no push seguinte, ficava no
> histórico, e **não se despublica** — a única saída seria fazer Reset Secret no
> Discord. É a mesma regra que o teu `CARDTRADER_TOKEN` já segue.
>
> O `riftvault multi --verificar` avisa-te se o secret estiver no ficheiro, e
> diz-te o comando para o tirar de lá.

### Verificação do passo 1

```
riftvault multi --verificar
```

Tem de dizer **`Discord: pronto`**. Se disser «falta client_secret», é porque
o valor não ficou colado.

---

## Passo 2 — a conta na Cloudflare

**Para quê:** para os teus amigos chegarem ao teu PC de fora de casa **sem
abrires uma porta no teu router e sem o teu IP aparecer em sítio nenhum**. O
teu PC faz uma ligação de saída para a Cloudflare e é por dentro dela que o
tráfego entra. É por isso que isto não contraria a regra de nunca publicar o IP
da tua LAN.

1. **https://dash.cloudflare.com/sign-up** → cria a conta (email + password).
   Plano **Free**. Confirma o email.

Fica aqui. **Não adiciones o domínio ainda** — isso é o passo 3, e a ordem
importa.

### Verificação do passo 2

Consegues entrar em `dash.cloudflare.com` e vês um painel vazio. É tudo.

---

## Passo 3 — o domínio e o túnel

Este é o passo com risco. Faz-se em cinco partes e há uma confirmação a meio
que **não deves saltar**.

### 3a. ESCREVE O QUE TENS AGORA (cinco minutos que te salvam a noite)

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

### 3b. Adicionar o domínio à Cloudflare

1. No painel: **Add a site** → escreve `baverone.com` → **Continue**.
2. Plano **Free** → **Continue**.
3. A Cloudflare vai **ler sozinha** os teus registos e mostrar uma lista.

### 3c. A CONFIRMAÇÃO QUE NÃO SE SALTA

Compara a lista da Cloudflare com o que escreveste em 3a, **linha por linha**.

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

### 3d. Mudar os nameservers

A Cloudflare dá-te dois nomes (tipo `ana.ns.cloudflare.com` e
`bob.ns.cloudflare.com`). Vais ao **registrar** (não à Cloudflare), procuras
«Nameservers» / «Servidores de nomes», escolhes «personalizado» e substituis os
que lá estão pelos dois da Cloudflare. Guarda.

Agora **espera**. Costuma levar de 10 minutos a 2 horas; pode chegar a 24. A
Cloudflare manda-te um email a dizer «is now active».

**Durante a espera os sites continuam a funcionar** — os nameservers antigos
ainda respondem enquanto a mudança se propaga. É normal que uns computadores
vejam a zona nova e outros a antiga durante umas horas.

### 3e. Verificação do passo 3 — ANTES de instalar o túnel

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
> repõe os nameservers que escreveste em 3a.

Só depois de os cinco abrirem é que avanças.

### 3f. O túnel

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
4. Dá-lhe o endereço (é o mesmo que escreveste no Discord, no passo 1):
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

### Verificação do passo 3f

Com o `riftvault serve` a correr, abre **https://editar.baverone.com** no
telemóvel, **fora do wi-fi de casa** (com dados móveis). Tem de aparecer o
riftvault e um botão **Entrar com Discord**.

---

## Antes de abrir: liga a TUA conta (dois minutos, e é importante)

**Tens de fazer isto antes de abrir a porta.** Depois de abrires, escrever passa
a exigir entrar — e se a tua conta não estiver ligada ao Discord ficas do lado de
fora da tua própria coleção. O `--verificar` não te deixa abrir sem isto, de
propósito.

A razão de ser um passo à parte: **tu já existes.** És o utilizador 1, com o nome
`baverone`, e tens a coleção toda. «Registar-te» não faz sentido — o registo
pedia-te um nome de endereço, e o teu já é teu. O que falta é **ligar** a tua
conta do Discord à conta que já tens.

Com o `riftvault serve` a correr, noutro terminal:

```
riftvault multi --ligar
```

Ele dá-te um endereço. Abre-o no browser **deste PC**, entra com o Discord, e
está feito. O código serve **uma vez** e expira em 30 minutos.

> **Porque é que o código vem da consola e não é um botão na página?** Porque
> ter acesso à consola deste PC prova que és tu — e um botão na página não
> provava nada. Não há nenhum atalho baseado no endereço de quem pede, e isso é
> deliberado: o túnel da Cloudflare faz **todo** o tráfego da internet chegar ao
> riftvault como se viesse de dentro do teu PC (`127.0.0.1`), por isso uma regra
> do tipo «se vem de casa, é o André» dava a tua conta a qualquer visitante.

Confirma:

```
riftvault multi --verificar
```

Tem de dizer **`Tu consegues entrar: a tua conta está ligada ao discord`**.

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

- os teus amigos podem registar-se em `editar.baverone.com`;
- cada um escolhe o nome do endereço dele e edita **só** a coleção dele;
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
peça para apagar a conta apaga-se com `riftvault conta --apagar <nome>`. Os
backups da coleção dele são os teus backups. E se alguém entrar na tua máquina,
entra nas coleções todas — é o preço de ser o teu PC a servir, e é um risco
aceitável entre amigos, mas é bom que seja dito e não descoberto.

---

## Se preferires o Google (ou os dois)

O Google dá mais trabalho: precisa de um projeto na Google Cloud, de um ecrã
de consentimento, e — para contas que não a tua — de passar pela verificação
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

Os dois podem estar ligados ao mesmo tempo; a página de entrada mostra um
botão por cada um que esteja configurado. A mesma pessoa pode ligar os dois à
mesma conta e entrar por qualquer deles.

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

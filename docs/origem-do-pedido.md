# De onde vem o pedido (2026-10-01)

Duas revisões externas independentes leram o código a 01/10 e encontraram os
mesmos dois defeitos, no mesmo sítio e com a mesma raiz: **a app perguntava à
porta das contas se era preciso autenticação, em vez de perguntar a quem estava
a bater.** Este documento é o que se mediu e o que ficou no lugar.

---

## Os dois defeitos

**1. «Fechar» desligava a autenticação.** O guarda tinha isto:

```python
if request.method in ESCREVE:
    if not aberto and g.sessao is None:
        return None            # passa SEM sessão e SEM CSRF
    return _guardar_escrita()
```

Com `multi.aberto: false` qualquer escrita passava. E o túnel
(`editar.baverone.com`) está vivo e aponta para a 8770 — medido a 01/10, o
`cloudflared` corre como serviço do Windows (`tunnel run --token-file`). Ou
seja: **escrita anónima na coleção dele a partir da internet**, à distância de
um `git checkout` do config.

**2. Um pedido sem sessão caía na base do utilizador 1.** O mesmo caminho:
`get_con()` com `riftvault_user=None` → `db.connect(user_id=None)` →
`utilizador.atual()` → **o André**. A privacidade dele nunca era consultada, e
por isso no dia em que a pusesse em `nada` o `editar.baverone.com` continuava a
servir tudo a quem lá fosse.

---

## O que estava escrito, e a conclusão que estava errada

Desde 29/09 este repositório diz, aqui e no `rotas_conta.py`:

> **Não há atalho por endereço. Nem loopback, nem sub-rede, nem cabeçalho.**
> O túnel faz todo o tráfego da internet chegar ao Flask como `127.0.0.1`.

**O facto continua verdadeiro** — e foi medido outra vez a 01/10. O que estava
errado era a conclusão: de *«o loopback não prova que é ele»* tirou-se *«não se
pode distinguir nada»*, e daí *«então a porta decide»*.

Mas há coisas que o loopback **não explica**, e são essas que decidem. A
pergunta mudou de forma: não se pergunta «isto vem de fora?» (falsificável para
ambos os lados), pergunta-se **«isto é inequivocamente de casa?»**.

---

## A regra: um E de três condições

`origem.classificar` só diz «de casa» se as TRÊS se verificarem:

| # | condição | porque é que não se forja |
|---|---|---|
| 1 | o par TCP está numa gama da casa (loopback, RFC 1918, link-local) | o `remote_addr` é o par da ligação TCP, não se escolhe. O túnel **não consegue** produzir um `192.168.1.x` — fala com o `localhost` |
| 2 | nenhum cabeçalho de intermediário | um browser não manda nenhum dos 21 da lista; quem os põe é quem está no meio |
| 3 | não pediu o anfitrião público (`auth.base_url`) | para a Cloudflare encaminhar para o túnel, o pedido tem de ser para aquele nome |

**A direcção do erro é a que interessa:** forjar qualquer uma delas só pode
TIRAR confiança, nunca dá-la. Quem estiver na rede de casa e mandar um
`CF-Connecting-IP` inventado consegue uma coisa só — passar a precisar de
password. Para um pedido da internet ser tratado como de casa teria de vencer as
três ao mesmo tempo.

Nenhuma é, sozinha, uma prova. Juntas são o mais perto disso que há sem mudar o
túnel, e cada uma tapa o buraco das outras.

---

## O QUE SE MEDIU, a 2026-10-01, contra o túnel a sério

`GET https://editar.baverone.com/api/conta.json`, com o código novo a correr na
8770. O servidor respondeu `origem: "fora"` com **nove sinais**:

```
CF-Connecting-IP   CF-Ray   CF-IPCountry   CF-Visitor   CF-Warp-Tag-Id
CDN-Loop   X-Forwarded-For   X-Forwarded-Proto
+  pediu editar.baverone.com, que é o endereço público
```

**Cada um basta sozinho** — e é essa a redundância que faltava. Se a Cloudflare
deixar de pôr sete deles, o oitavo chega; se deixar de pôr os oito, chega o
nome.

Dois factos que vale a pena ter escritos:

* **a Cloudflare NÃO reescreve o `Host`.** Chega `editar.baverone.com` ao Flask,
  e por isso a condição 3 funciona mesmo sem cabeçalho nenhum;
* o mesmo pedido a `http://127.0.0.1:8770` dá `origem: "casa"`, zero sinais.

E a prova do que o defeito 1 era, feita num servidor HTTP a sério com
`multi.aberto: false` e estes nove sinais (pasta de dados descartável, o `data/`
dele nunca tocado — `_revisao\_prova_porta_fechada.py`):

| | pelo túnel | de casa |
|---|---|---|
| `POST /api/adjust`, `/api/foil/ajustar`, `/api/undo`, `/api/decks/montar`, `/api/conta/privacidade` | **401** | passa o guarda (404 da rota: a carta não existe) |
| `GET /api/index.json`, `/decks.json`, `/venda.json`, `/selado.json`, `/runas.json`, `/encomendas.json` | **401** | **200** |
| `GET /`, `/app.js`, `/style.css`, `/api/conta.json` | **200** | 200 |

---

## As gamas da casa escrevem-se uma a uma — e não é pedantismo

A primeira versão fazia `ip.is_loopback or ip.is_private or ip.is_link_local`, e
a bateria apanhou-a no primeiro teste: **para o Python, `203.0.113.9` é
privado.** Ele marca assim as gamas reservadas para documentação
(`192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`) e a `240.0.0.0/4`.

E o pior não é a lista estar errada — é **mudar sozinha**: o que o Python entende
por «privado» já mudou entre versões (a `100.64.0.0/10` do CGNAT das operadoras
era privada e no 3.14 não é). Uma decisão de segurança não pode depender disso em
silêncio.

---

## O que ficou a significar «fechado»

| | |
|---|---|
| **a PORTA** (`multi.aberto`) | fechada: OAuth parado, sem registo, só o site DELE se publica, e **em casa** escreve-se sem password |
| **a ORIGEM** | se é preciso entrar. De fora exige-se sessão para **tudo**, leitura incluída, com a porta aberta ou fechada |

**O que a porta fechada NÃO faz** — e isto apanhou-nos a escrever o contrário
no meio desta própria correcção: não impede quem já tem conta de entrar. A
entrada por password não passa pela porta desde 30/09, e **medido a 01/10**:
com `multi.aberto: false`, um amigo com conta entra (200) e o guarda deixa-o
escrever na coleção **dele**. Uma mensagem do `--fechar` chegou a dizer «os
teus amigos deixam de entrar»; estava errada e foi corrigida antes do merge.

Fechar deixou de desligar a autenticação. A docstring do `abrir.fechar()` dizia
*«Ninguém perde nada — só deixa de se entrar»*, e essa frase era parte do
defeito: descrevia como inofensiva a chave que punha a autenticação abaixo.
Está corrigida, e o `riftvault multi --fechar` passou a dizer as duas metades.

---

## Porque é que a privacidade fica respeitada sem uma linha de filtragem

De fora e sem sessão **não se serve nada** — nem um payload, nem uma imagem. Não
há o que filtrar. É a mesma decisão do `_u_explica` de 29/09: filtrar dezassete
rotas de leitura era deixar uma esquecida a vazar; as coleções que se vêem sem
entrar estão no site ESTÁTICO, que o `build.py` gera já filtrado.

A lista do que passa (`rotas_conta.DE_FORA_SEM_SESSAO`) é **literal** e não
«qualquer ficheiro que exista no `web/`»: um ficheiro novo naquela pasta não pode
passar a ser público em silêncio. Há teste que compara as duas coisas.

---

## O que isto NÃO faz

**Não protege a rede de casa.** Quem estiver na LAN com a porta fechada continua
a escrever na coleção dele sem password. É a decisão dele, está no banner do
`serve` — *«Sem palavra-passe: quem chegar ao URL pode escrever na coleção. Não
abras este porto no router.»* — e não era desta correcção mudá-la.

**Não é identidade.** Isto nunca diz QUEM é alguém, só se o pedido pode ser
tratado como o de alguém que está em casa. Quem decide quem é alguém continua a
ser a sessão. Por isso também não substitui o guarda da escrita: de casa com a
porta aberta, escrever continua a exigir sessão e CSRF.

## Fotografado, e uma coisa veio de lá

A 1280 e a 375 px, contra um servidor de prova com a porta fechada. O truque,
que serve para a próxima vez: **pôr o `auth.base_url` no próprio endereço do
servidor de prova** faz o mesmo processo responder «casa» num URL
(`127.0.0.1:8782`) e «fora» no outro (`localhost:8782`), sem ter de forjar
cabeçalhos dentro de um browser.

Quem chega de fora vê o ecrã de entrar, com o formulário — e não um «Falhou a
carregar: HTTP 401».

**O que a foto a 375 px apanhou:** a frase *«o formulário está na barra do
lado»* mente no telemóvel — ali a barra está atrás do **☰ Menu**. O formulário
está lá (o `mostrarSeTrancado` esconde só o `#sidenav`, não a `<aside>` inteira,
e a foto com o menu aberto mostra-o), mas o ecrã mandava procurar uma coisa que
não se vê. Vinha assim **desde 30/09**, no ecrã da password temporária. A frase
passou a dizer os dois sítios.

---

## Se um dia a casa passar a pedir password

Há um caso em que isto acontece de propósito e convém não o ler como avaria:
**se ele puser um intermediário à frente do 8770 em casa** (um nginx para ter
HTTPS na LAN, um proxy do telemóvel, uma VPN que reescreva pedidos), esse
intermediário põe um `X-Forwarded-*` ou um `Via`, e a partir daí a casa passa a
contar como «de fora».

É o lado certo do erro — com um proxy à frente já não se sabe quem está do outro
lado —, e **não é adivinhação nenhuma**: o `api/conta.json` diz
`origem: "fora"` e lista o cabeçalho pelo nome, por isso a causa lê-se em
dez segundos, do telemóvel. Se um dia ele quiser mesmo confiar nesse
intermediário, é aqui que se decide, e é uma decisão dele.

---

**Um detalhe medido, que fica anotado:** o `config.load()` tem `lru_cache`, por
processo. O `riftvault multi --fechar` numa consola **não** muda a porta do
`serve` que já está a correr — só na reinicialização seguinte. Não é desta ordem
e não é um buraco de segurança (a origem é lida a cada pedido, não vem do
cache), mas é uma surpresa à espera de quem contar o contrário.

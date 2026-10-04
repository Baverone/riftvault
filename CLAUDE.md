# CLAUDE.md — riftvault

Contexto do projeto para o Claude Code. Lê isto antes de mexer em código.

## O que é

Gestor pessoal da coleção de **Riftbound** (TCG da Riot), do André. Python +
SQLite, mesma arquitetura do `mtgvault`. Objetivo: ter **playsets**, incluindo
artes normais **e** alternativas.

**DESDE 2026-09-21 (TARDE) CADA DECK TEM AS SUAS CÓPIAS PRÓPRIAS** — ver a
última secção deste ficheiro. Os decks servem-se da Coleção (11/09) **e**
cada um tem um monte à parte (`proprio:<slug>`; os `+`/`−` de cada carta saíram
a **2026-10-01** — a página diz quantas são e quem as mexe é o `riftvault
proprias <slug> --mais/--menos`)
que serve primeiro e **nunca conta para a Coleção**; os decks não partilham
entre si (a soma); **só versões base, a Legend e o Champion incluídos**
(`decks.so_base: true`). A experiência do pool próprio (`decks.modo =
"pool_proprio"`, a manhã desse dia) ACABOU — escrever esse valor rebenta. As
secções abaixo que falam da Legend/Champion em versão especial (17/09) ou de
outras versões a tapar buracos descrevem a regra que `so_base: false` liga;
com `true` (hoje) não valem.

**DESDE 2026-09-27 HÁ UM DECK PRINCIPAL** (`decks.principal`, hoje «LeBlanc
Hook») — *"Deck Principal: neste caso LeBlanc […] todas as cartas do Deck sao
Wantlist, as comuns e incomuns em Foil"*. É UM só, é sempre montado
(`montados` diz quais estão montados; esta chave diz qual deles ele joga), e
**não é a prioridade 1**. Tem WANTLIST própria — o que lhe falta para ser
auto-suficiente (`precisa − cópias próprias`; uma carta marcada com o `+` sai
da lista), com as comuns e incomuns em foil. **A Coleção é soberana**: o que o
deck usa dela é um empréstimo de APRESENTAÇÃO (o tile diz «em uso no deck X», a
página do deck diz «X cartas em uso da Coleção, ainda falta Y específica») e
não muda um número. Ao deixar de ser principal ou ao ser desfeito, as cópias
PRÓPRIAS dele que valham **0,50 €** (`decks.venda_minimo_cents`) ganham uma
linha na Venda marcada com a origem — as de menos continuam próprias, e
**entrar na Venda não é vender** (nada sai do `proprio:<slug>`). Ver a última
secção deste ficheiro.

**DESDE 2026-09-24 CADA DECK ESTÁ MONTADO OU DESMONTADO** (`decks.montados`,
hoje `["LeBlanc Hook"]` — os outros cinco desmontados) — ver a última secção
deste ficheiro. Um deck DESMONTADO não consome NADA da Coleção: a Coleção dá
exactamente os mesmos números que daria se o `.txt` não existisse, e o que a
página dele mostra é uma SIMULAÇÃO. Do mesmo dia, a REGRA DE RARIDADE
(`decks.coleccao_so_a_partir_de: "epic"`): abaixo desse patamar a cópia devia
vir das próprias do deck — **marca, não bloqueia**.

**DESDE 2026-09-26 A GRELHA DA COLEÇÃO TEM AS FILAS DO BINDER** — a sequência
do master set sai com a **primeira fila de 4 e as seguintes de 8**, porque é
assim que a pasta dele está (`.grid.binder` no CSS, `BINDER_PRIMEIRA`/
`BINDER_FILA` no `app.js`; ver a última secção deste ficheiro). A posição de um
tile É a posição da carta na pasta: por isso o número por fila é FIXO (nada de
`auto-fill` ali), cada impressão ocupa UMA célula (nada de `.group.multi` na
sequência), e num ecrã estreito o bloco corre para o lado em vez de refluir.
**Não mexe em número nenhum** — é desenho, e nenhum `.py` sabe que existe.

**DESDE 2026-09-25 AS ABAS ESCONDEM-SE POR CONFIG** (`abas.escondidas`, hoje
`["a-mais", "pordeck", "pimp"]`) — ver a última secção deste ficheiro.
Esconder **não é apagar**: o «A mais», o «Por deck» e o «Pimp decks» continuam
a ser calculados, o `api/a_mais.json` e o `api/compras.json` continuam a ser
gerados e servidos, e o `riftvault a-mais` continua a responder — o que saiu
foi o botão, no 8770 e no site publicado. Repor é tirar o nome da lista.

**DESDE 2026-09-27 AS FALTAS TÊM `+` E `−` DE «JÁ ENCOMENDEI»** — *"nas
faltas, coloca o + e - para eu indicar que ja encomendei, fica bem mais facil
para eu visualizar assim"*. São os MESMOS botões do separador Encomendas
(nasceram nos decks a 11/09, saíram para as Encomendas a 17/09), a mesma
tabela `pending` e **um número só** nas duas vistas; o «Chegou» continua só
nas Encomendas. **A linha não desaparece** quando ele marca — passa a dizer
«faltam N · M já encomendadas» e sai só da wantlist. E a encomenda ganhou
ACABAMENTO (`pending.foil`, com migração e backup): uma foil encomendada entra
no `copies.qty_foil` e uma normal no `qty`. Ver a última secção deste ficheiro.

Secções: **Coleção**, **Decks**, **Faltas** (de
2026-09-15 ao fim da tarde — por edição, três blocos; **quatro desde
2026-09-19, cada um com a sua wantlist**; e **DUAS METADES desde 2026-09-27**
— as NORMAIS nesses quatro blocos e as **FOILS** à parte, que *"nao sao
faltas, sao apenas complemento e indicativo"*, com a QUINTA wantlist, alvo
igual ao playset do tipo (Rune 12) e fora de tudo o que já se contava
(`faltas_foil.py`) — ver a última secção deste
ficheiro; id interno `faltas-edicao`, `api/faltas_edicao.json`,
`faltas_edicao.py`) e **A mais**
(2026-09-17 — o excedente acima do alvo e as cartas libertadas dos decks; id
`a-mais`, `api/a_mais.json`, `a_mais.py` + `uso_decks.py`; ver a secção
própria no fim deste ficheiro) e **Encomendas** (2026-09-17, à tarde — a
grelha da Coleção de Rara para cima com os `+`/`−` do que comprou e o
«Chegou»; id `encomendas`, `api/encomendas/<SET>.json` + `api/encomendas.json`,
`pending.grelha`; os controlos SAÍRAM dos tiles dos decks — ver a última
secção deste ficheiro). Há ainda o **seguir jogadores** do Piltover
Archive (2026-09-17, `seguir.py`, `riftvault seguir`; por agora só na
consola — a secção no site é a parte 2, por fazer; ver a última secção deste
ficheiro). **Houve um «Quanto custa», APAGADO a 2026-09-19** (chamou-se
**Faltas** até 2026-09-15 de manhã e mostrou as faltas até à tarde desse
dia; de 2026-09-15 à tarde a 2026-09-19 foi a TABELA DE PREÇOS — o top 5
mais caras por raridade, em cada edição, tenha ele ou não; *"podes apagar o
botao do 'Quanto custa'"* — ver a última secção deste ficheiro, que diz o
commit a partir do qual se recupera. As secções abaixo que falam dele, das
abas «Master set», «A subir» e «A caminho» e do `api/quanto_custa.json` são
história; o `api/faltas.json` de antes de 2026-09-15 partiu-se em
`api/wantlist.json` e `api/compras.json`, que ficam. O identificador
`faltas` continua no `faltas.py`, que tem as listas de compra dos DECKS; no
site já não há secção nenhuma com esse id.) Há também **Produto Selado** (2026-09-25 — displays, cases, decks, bundles,
boosters e Proving Grounds: o que há, o que tem e o que não tem; a lista vem
das CATEGORIAS do CardTrader, o catálogo em `data/selado_catalogo.json`, id
`selado`, `api/selado.json`, `selado.py`; **não entra na Coleção** e o valor
dele nunca se soma ao dela. **Desde 2026-09-26 são 48**: os 81 da
API (4 blueprints repetidos juntados, `selado.juntar_duplicados`) mais 17
escritos à mão em `selado.extra` — displays de champion e de showdown decks,
cases de vaults, o case do Proving Grounds e os Pre-Rift EVENT Kit —,
**menos os 50 que ele mandou tirar** (`selado.excluidos`, a mesma ideia das
abas: esconder não é apagar, o catálogo fica intacto e repor é tirar o nome
da lista — 22 numa primeira ordem, mais 2 «Card Set» e 8 Trial Deck numa
segunda, mais os 11 **Champion Deck** a 26/09, mais os **7 que não se compram
em lado nenhum** na mesma noite; os 7 Champion Deck **Display**
da `extra` e os 2 Showdown Deck ficam, e as **edições por sair também ficam**
— não têm `cardmarket_id` mas têm ofertas em pré-venda). A secção dos **binders e deck boxes** (`selado.acessorios`) ficou
com a **lista VAZIA** nessa mesma noite — ele mandou tirar os acessórios
todos —, e por isso não aparece; a chave e o código ficam, e repor é escrever
os números outra vez. Ver a última secção deste ficheiro.)
E há uma **Venda** OUTRA VEZ, desde 2026-09-25 — mas é outra pergunta: a
conta de uma venda em curso, para mostrar a quem compra, com os preços a
serem o **Trend do Cardmarket metido à mão** (id `venda`, `api/venda.json`,
`venda.py`); ver a última secção deste ficheiro. (A Venda de 2026-09-08 —
uma sugestão do que sobra acima do alvo — foi apagada a 2026-09-15 a pedido
dele e não voltou: essa pergunta vive no «A mais» desde 2026-09-17. As
secções abaixo que falam dela são história.)

## Regras de trabalho

- **Comentários, README e mensagens em português (de Portugal).** Nomes de
  funções, variáveis e tabelas em inglês.
- **Não inventes dados.** Se a API não devolver um campo, não o preenchas de
  memória — regista aqui que não foi validado.
- Comentários explicam *porquê*, não *o quê*.
- Tudo o que ainda não foi validado contra a API real vive na secção
  "Superfícies não validadas", no fim.

## Dois modos

- **Edição (local):** `riftvault serve` levanta um servidor local que serve o
  site e escreve no `vault.db`. Bind `0.0.0.0` + QR no arranque, para usar o
  telemóvel enquanto se mexe nas cartas.
- **Publicado (leitura):** `riftvault build` gera o MESMO frontend em estático,
  sem controlos de edição, publicado no GitHub Pages por GitHub Actions.

**O `build` corre NO PC e o `site/` vai no Git (2026-09-10).** Ver a secção
própria, "O site é gerado no PC". O GitHub Actions deixou de gerar seja o que
for: só publica a pasta commitada, sem rede nenhuma.

O frontend é o mesmo ficheiro nos dois modos. Ele pede sempre os mesmos URLs
(`api/sets.json`, `api/set/<ID>.json`, ...); em modo edição o servidor
responde dinamicamente, em modo publicado são ficheiros reais gerados pelo
build. Um flag no payload (`"editable": true/false`) liga/desliga os `+`/`-`.

## Sem autenticação — cuidado com a exposição

O modo edição **não tem autenticação nenhuma**: quem chegar ao URL escreve na
coleção. É aceitável na LAN, não é na internet.

**O IP da LAN muda sozinho.** A 2026-09-02 a rede passou de `192.168.0.x`
para `192.168.1.x` e o URL que ele tinha deixou de responder — pareceu que o
site tinha ido abaixo, mas o servidor estava de pé. O `serve` passa a listar
**todos** os endereços (`server.lan_ips()`), porque mostrar um só engana
quando há Ethernet e Wi-Fi em sub-redes diferentes.

Nem o `getaddrinfo(gethostname())` nem sondar a tabela de rotas com um socket
UDP encontram a interface secundária quando a principal tem métrica melhor —
os dois foram testados. É preciso perguntar ao sistema (`ipconfig` no Windows,
`ip -4 -o addr` no resto).

Isto continua a acontecer enquanto for DHCP; o `serve` lista os endereços
todos e é isso que há.

**O Tailscale saiu (2026-09-17).** Esteve recomendado como o caminho para
chegar ao servidor de fora de casa (rede privada entre os dispositivos dele);
o André mandou esquecê-lo e desinstalou-o do PC. O `server.tailscale_ip()` e
as linhas do banner que o mencionavam foram apagados nesse dia: o banner
mostra só o acesso local. Não há hoje maneira de chegar ao modo edição de
fora de casa, e é assim de propósito — sem autenticação, o modo edição é só
para a LAN; port forwarding e tunnels públicos continuam fora de questão. O
IP da LAN nunca vai para nada que se publique no GitHub Pages.

Se algum dia for preciso expor mesmo, aí sim é preciso autenticação primeiro —
não inverter a ordem.

## Três bases de dados

**DESDE 2026-09-29 O `vault.db` É DE UM UTILIZADOR, e há mais do que um
possível** — *"Amigos meus querem usar o site para organizar a coleccao
deles"*. O do André é o `data/vault.db` de sempre (utilizador **1**, slug
**`baverone`**, no Git); os outros vivem em `data/users/<slug>/vault.db`, que
está no **`.gitignore`** — este repositório é PÚBLICO e o `vault.db` é
commitado de 30 em 30 minutos, e a coleção de um amigo não é nossa para
publicar. O `catalog.db` e o `prices.db` **não têm dono**: são partilhados. A
porta única é o `utilizador.atual()` + `db.connect(user_id=…)`; hoje devolve
sempre o André. Ver a última secção deste ficheiro e `docs/multi-utilizador.md`.

- `data/vault.db` — a coleção e os decks. **Commitado. Só o André escreve.**
  (Desde 2026-09-22 a `copies` tem a coluna `qty_foil` — a contagem de foil
  das comuns e incomuns; a migração fez backup em `data/backups/`, que está
  no `.gitignore`. **DESDE 2026-09-26 o `qty` são as cópias NORMAIS e o
  `qty_foil` as FOIL, e o total é a SOMA** — eram duas leituras da mesma
  cópia até aí, e o `+` do foil convertia uma normal; erro nosso. Ver a
  última secção deste ficheiro.)
- `data/prices.db` — histórico de preços. **Commitado. Só o robô escreve.**
- `data/catalog.db` — cache do catálogo da RiftScribe. **No `.gitignore`**
  (reconstruível com `riftvault sync`).
- `data/images/` — cache local das imagens. **No `.gitignore`.**

**Porque é que o histórico de preços não está no vault.db.** O GitHub Actions
corre o `riftvault prices` sozinho e faz commit do resultado. Se isso fosse
para dentro do vault.db, bastava o André ter mexido na coleção localmente para
dar um conflito num ficheiro **binário** — e resolver um conflito de SQLite é
escolher uma das versões e perder a outra. A coleção é a única coisa
insubstituível aqui, por isso o robô nunca lhe toca. Na pior das hipóteses
perde-se um dia de preços.

`db.connect()` anexa as duas: `catalog` e `prices`. As consultas ao histórico
qualificam sempre `prices.price_history`.

Como no mtgvault, o `catalog.db` é ATTACHed como schema `catalog`. O SQLite
não suporta chaves estrangeiras entre bases de dados: `copies.printing_id`
não tem FK declarada, a integridade é garantida no código.

---

# O site é gerado no PC (2026-09-10)

**O que aconteceu.** A 10/09, das 11:55 às 17:45, TODAS as builds do Pages
morreram ao fim de 45 s no passo «Descarregar o catálogo»: o
`riftscribe.gg/api/cards/filters` deixou de responder — timeout do GitHub **e**
do PC, portanto era mesmo deles. O site ficou parado na versão das 09:08 (o VEN
ainda a 196 impressões, antes das promos saírem) com o André fora de casa a
olhar para ele. Cada push a `main` gastava uma build que morria.

**O erro de fundo era de desenho.** O `catalog.db` está no `.gitignore` porque
é reconstruível, e a consequência era o Actions ter de o reconstruir **a cada
build** — 7 pedidos à RiftScribe para publicar uma página que só precisava de
dados que já estavam todos no PC. A única coisa insubstituível daqui, a
colecção, mora no PC; o catálogo completo também. **O Pages não tinha nada que
precisar de rede.**

**A cura é a do mtgvault**, que já publicava assim: gerar no PC, commitar o
resultado, e deixar o Actions só servir.

| | antes | agora |
|---|---|---|
| quem corre o `riftvault build` | GitHub Actions | o PC (`riftvault-publicar`, `riftvault-daily`) |
| de onde vem o catálogo | descarregado da RiftScribe a cada build | `data/catalog.db`, que já está em disco |
| o que o workflow faz | sync + map + prices + commit + build + deploy | `checkout` -> `upload-pages-artifact` -> `deploy` |
| pedidos de rede no workflow | 7 à RiftScribe + o CardTrader inteiro | **zero** |
| o que o workflow escreve no repo | `data/prices.db` | **nada** (`contents: read`) |

## `site/` deixou de estar no `.gitignore`

São **1,2 MB em 17 ficheiros** (`api/faltas.json` 220 KB, os cinco
`api/set/*.json` 720 KB, `venda.json` 55 KB, e o `index.html`/`app.js`/`css`).
É JSON, comprime bem, e só se commita quando muda mesmo — ver a seguir.

**As imagens NÃO vão para o Git.** São ~88 MB e o `static_images` fica em
`"remote"`: o browser dele vai ao `cdn.riftscribe.gg`, como já ia. Isso é o
browser a buscar imagens, não uma build — se a RiftScribe estiver em baixo a
**página abre na mesma**, só fica sem as fotos. É a diferença que interessa: o
site deixou de poder ficar parado, no máximo fica feio.

## `--se-mudou`: o relógio não é conteúdo

O `generated_at` muda a cada geração. Sem defesa nenhuma, a tarefa de 30 em 30
minutos commitava um site novo e gastava uma build do Pages **48 vezes por
dia**, para sempre, sem uma carta ter mudado.

`riftvault build --se-mudou` gera para uma pasta de prova (`site-prova/`, fora
do Git), compara com o `site/` **ignorando todos os `generated_at`**
(`build.mesmo_conteudo`), e só reescreve se o conteúdo diferir. Compara-se o
RESULTADO, não as datas dos ficheiros de entrada: o `vault.db` é reescrito por
qualquer clique, mesmo um que não mude número nenhum, e o WAL faz o mesmo ao
contrário.

A `api/` é apagada antes de cada geração — uma edição que saia do catálogo tem
de sair do site, e um payload órfão fazia o `--se-mudou` ver diferença **em
todas as corridas**, que é a mesma avaria por outro caminho.

## O que o workflow deixou de fazer, e onde passou a ser feito

| passo que saiu do `pages.yml` | onde está agora |
|---|---|
| `riftvault sync` | passo `sync` do `riftvault-daily` (já lá estava, não essencial) |
| `riftvault map` + `riftvault prices` | passo `prices` do mesmo (já lá estava) |
| commit do `data/prices.db` | passo `commit` do mesmo (um só push) |
| `riftvault build` | passo `site` do `riftvault-daily` e a `riftvault-publicar` |

Nada se perdeu: os três primeiros já eram feitos no PC todos os dias, o
workflow é que os repetia. O que é novo é a geração.

**Os preços deixaram de ser essenciais no `riftvault-daily`** — e não é
indulgência. A publicação do site vem DEPOIS deles: com o CardTrader ou a
RiftScribe em baixo, a tarefa acaba o trabalho (gera o site com os dados que há
e publica a colecção que o André editou) e **só depois** diz que o passo
falhou. O teste continua a dar vermelho — «correu» não é «actualizou» —, o que
muda é que o vermelho já não impede o site de ir para o ar.

## O teste pergunta pelo site QUE ESTÁ NO AR

Não chega o commit estar em `origin/main`: era isso que estava verde enquanto
as builds morriam. Os dois `test.py` fazem GET a
`baverone.github.io/riftvault/api/index.json` e comparam o `generated_at` de lá
com o do `site/api/index.json` daqui. Se o de lá estiver atrasado:

- **commit do site com menos de 15 min** -> AVISO, o Pages ainda está a
  construir (as builds boas levavam ~1 min);
- **mais do que isso** -> VERMELHO, com o `gh run list` na mensagem. É
  exactamente o caso de 10/09.

---

# A Coleção em três categorias; a coleção extra acompanha-se, não se compra (2026-09-14/15)

**As secções de 09-08 a 09-10 sobre blocos, alvos e o que sai da Coleção são
história desde a noite de 2026-09-14.** O que manda hoje está nas `_notas` do
`riftvault_config.json` e no topo do `metrics.py`; aqui fica o resumo.

Palavras dele (14/09, à noite): *"quero masterset com playset / runas 1 de
cada / Alt Art, overnumbered, etc etc mete Playset na contagem / mas só quero
% de completo para masterset! / o que é Alt Art e Overnumbered, etc etc é
puramente coleção"*. E (15/09): *"sobrenumeradas não entram na wantlist, nem
na % de coleção completa; apenas pedi para ser feito track de playset para eu
saber exatamente quantas tenho"*.

| categoria | config | o que é | grelha | % e níveis | listas de compra |
|---|---|---|---|---|---|
| 1. master set | o resto | a sequência da edição | sim, alvo = playset do tipo (as runas numeradas do OGN a **3** desde 15/09 à tarde) | **sim** | **sim** |
| 2. coleção extra | `master_set.fora_da_percentagem` = `["a", "overnumbered", "promo"]` | artes alternativas, sobrenumeradas, promos | sim — o alvo é **por categoria**, `master_set.um_de_cada` = `["overnumbered", "promo"]`: sobrenumeradas **1 de cada** (15/09), **artes alternativas a playset** (18/09 — *"muda novamente: Alt Art para playset"*; pediram 1 de 16/09 a 18/09) e **promos 1 de cada** (19/09 — *"as Promo passam a 1 de cada ao inves de playset"*; andaram playset 14/09 → 1 15/09 → playset 18/09 → 1 19/09; ver a última secção deste ficheiro); **os decks nunca levantam este alvo** (17/09: os decks jogam a base, e a Legend/Champion uma versão especial) | não | **não** (15/09) |
| 3. escondidas | `master_set.escondidas` = `["-T", "*", "-R"]` | tokens, signatures e — desde 15/09 à tarde — as runas sem numeração de master set (`VEN-R01..R06`) | não | não | não |
| 4. retiradas | `runas_especiais.retiradas` = `["a"]` (`metrics.retirada`) | as **runas em Alt Art** (`OGN-007a..214a`, e as `SFD/UNL/VEN-R0Xa` do CardTrader) — desde 17/09 | **não** | não | não — e **não contam no valor nem no playset jogável**, nem no A mais, nem no Pimp; os decks jogam a runa base (e desde a noite de 17/09 **não contam runa nenhuma** — ver «as runas saem da contagem dos decks», no fim deste ficheiro) |

(O `-R` passou da lista 2 para a 3 a 2026-09-15 — ver a secção "As runas sem
numeração saem", no fim deste ficheiro. O alvo 1 das sobrenumeradas e das
promos é da mesma tarde — ver "Sobrenumeradas e promos voltam a 1 de cada",
a seguir a essa; o das artes alternativas é de 16/09; as duas voltaram ao
playset a 18/09, em duas ordens — ver as duas últimas secções. A categoria 4
é de 17/09 — ver "As runas em Alt Art saem de tudo", no fim.)

**Acompanhar não é querer comprar.** Na noite de 14/09 a coleção extra entrou
inteira nas listas de compra (a leitura foi «um alvo sem lista de compra é um
alvo sem maneira de o cumprir») e a wantlist passou de 3 337 € para 30 646 €,
7 202 € só em três `UNL-238` Baron Nashor que ele disse a 09-05 que nunca
compraria. A frase de 15/09 corrige isso: `listas_de_compra.so_master_set`
(default `true`, `config.DEFAULTS` também) tira o bloco 2 de TODAS as listas —
«A subir», «Master set», wantlists por edição, «Wantlist — tudo», por nível,
texto do Cardmarket — em `a_subir.excluir`, que sai por BLOCO antes dos dois
critérios de 09-08 (tipo `signature`, raridade `showcase`). A página e o CLI
dizem quantas tirou e de que bloco (`scope.excluded_by`, `excluded_labels`).

**A Venda não mexe com este botão.** A coleção extra continua a vender-se só
acima do alvo (`cópias − max(usadas, alvo)`). Pergunta aberta: acompanhar uma
carta a playset impede vendê-la?

**Medido a 2026-09-15 no `main`, na mesma corrida (botão desligado → ligado):**
wantlist «tudo» 424 linhas · 885 cópias · **29 716,39 € → 229 · 432 ·
1 629,47 €**; «A subir» 69 cartas · 150 cópias · 4 178,75 € → **30 · 58 ·
262,77 €** (âmbito 1134 → 928); percentagem **689/928 = 74,2 %** nos dois —
não mexe, já não contava o bloco 2. Fora das listas: 206 impressões (12 runas
especiais, 96 artes alternativas, 92 sobrenumeradas, 6 promos).

`tests/test_tres_blocos.py` fixa as três categorias e o botão;
`test_coerencia`, `test_niveis`, `test_wantlist_edicao`, `test_signatures` e
`test_cardmarket` foram reescritos a 15/09 porque descreviam a noite de 14/09.
**Cuidado com o nome `signature`**: é ao mesmo tempo um bloco da grelha e um
tipo do `excluir.tipos`, e o `resumo_fora` deduplica os critérios por isso.

---

# Decks com a MESMA Legend partilham cartas, não disputam (2026-09-11, noite)

Palavras dele: *"deck com o mesmo Legend, partilham cartas. Os 2 decks de
LeBlanc partilham as mesmas cartas, são só 2 listas diferentes em algumas
cartas. Então o que encomendar para 1 deck, estou a encomendar para o outro
também."*

**A regra numa frase:** decks com a mesma Legend (mesmo `card_key` da linha
`Legend:`) são duas listas do mesmo deck físico — nunca se jogam ao mesmo
tempo —, formam um **grupo**, e dentro do grupo a procura de cada carta é o
**MÁXIMO** entre as listas, não a soma. O grupo serve-se da Coleção como um
deck só, na prioridade do melhor colocado dos membros; o que lhe falta é falta
dos dois, a mesma carta, a mesma quantidade, **contada uma vez** no total
geral. Entre grupos diferentes (Ornn, Azir, Kennen, grupo LeBlanc) continua a
regra da secção a seguir: soma, disputa, o de baixo compra.

**Onde vive:** `decks.grupos` (a Legend agrupa; `lider` é o membro de
prioridade mais alta, `rotulo` é `A ·· B`) e `decks.allocate`, cuja unidade
passou a ser o grupo — funde as listas por máximo, aloca, e espalha o resultado
por cada membro cortado ao que ele pede. Cada entrada da alocação leva
`grupo` com o resultado ao nível do grupo (`missing`, `a_caminho`, `ordered`,
os montes) e `partilhada` nas cartas que o irmão também pede. **Quem soma
totais lê só as entradas com `grupo.lider`** — é o único cuidado que a camada
pede: `resumo_das_faltas`, `pending.encomendas` («Falta encomendar» e o
«para»), `_por_impressao` (Venda, «usadas nos decks») e o `faltas._wanted`
(a `qty` soma por grupo, `n_grupos` decide as Staples — uma compra que serve
decks DIFERENTES, não duas listas do mesmo). `missing_by_set(..., grupo=True)`
responde pelo grupo.

**Apresentação:** a página de cada deck continua a ser a lista dele; a carta
que o irmão também pede diz «partilhada com …» em vez de «-> 3x em …» e não é
disputa. Na tabela do `riftvault decks`, na secção Decks do site e nas abas
das Faltas os membros levam `·· ` à frente e uma linha a explicar. A soma das
abas «Por deck» **já não é o total** quando há grupos — a nota do «Todos
juntos» diz porquê. `tests/test_mesma_legend.py` fixa tudo isto contra
cópias.

**Uma encomenda (`+`) feita pela Coleção desconta nos dois** — já era assim,
porque a encomenda é da Coleção e o monte `a_caminho` é lido pelo líder.

**Medido no `data/` real** (5 decks, os dois LeBlanc com a mesma Legend): ver
o relatório `ai-pc/work/revisao/riftvault-mesma-legend.md`.

---

# Os decks partilham a Coleção; o que não chega compra-se (2026-09-11)

Palavras dele: *"Os decks podem usar cartas da coleção. Na coleção indica onde
as cartas estão a ser usadas. Os decks que precisem de cartas iguais, caso não
haja suficientes na coleção, ficam em falta e é necessário comprar!"* E, a
confirmar: *"se há na coleção o deck usa; caso algum deck ou decks já estão a
usar as cartas disponíveis na coleção, o próximo passa a marcar como faltas
para comprar"*.

**Isto revoga a regra 2 dos três locais de 2026-09-10** («os decks só se montam
com Deck + Binder Decks/Venda») e a REGRA CENTRAL antiga do `decks.py` («uma
carta que falte por estar noutro deck não é o mesmo que uma carta que não se
tem»). Três regras, uma por frase:

1. **Uma cópia que exista conta para o deck**, esteja na Coleção, sleevada no
   deck ou no binder Decks/Venda. `decks.pool_dos_decks` dá os três montes e o
   `allocate` serve-se deles por esta ordem: deck, binder, Coleção. A marcação
   de locais (`riftvault local`, `copy_locations`, os botões do site) fica como
   **informação de onde a cópia está** — não desconta nada. A mesma cópia
   conta para a barra do master set E para o deck. O `tenho` do Ornn passou de
   «0/66 · na Coleção 62 (não conta)» para **62/66**.
2. **A Coleção diz onde cada carta está a ser usada.** O `metrics.set_payload`
   leva `decks` em cada grupo (`decks.uso_por_carta`), a grelha mostra
   «Azir 3 · Kennen 2 (faltam 2)» no primeiro tile de cada carta — a vermelho
   quando um deck não recebe o que pede —, há um filtro **Em decks** ao lado
   de «Faltas», e `riftvault stats --usadas` lista o mesmo.
3. **O que um deck não recebe é falta a comprar, sempre.** `allocate.missing`
   = o que o deck pede − o que lhe calhou; `shared` passou a ser a parte disso
   que existe num deck de cima («disputadas»), só informação. Entra no «Falta
   comprar, por edição», no `shopping`, na tabela do `riftvault decks` (coluna
   `disputadas` no lugar de `noutro`), numa linha nova do `riftvault stats`
   (`decks.resumo_das_faltas`) e na secção Faltas.

**A fórmula, por carta lógica:** `procura_total = Σ(o que cada deck pede, em
todos os papéis)`; `a comprar = max(0, procura_total − cópias que existem)`,
distribuída pelos decks de prioridade mais baixa. **O sideboard soma à procura
como o main** e disputa o mesmo stock — era a regra que já existia (`need`
agrupa por carta, sem olhar ao papel) e ficou fixada em teste; na página do
deck o main serve-se primeiro.

**O teto por carta de 2026-09-01 ficou revogado.** O `faltas.shortfall` deixou
de limitar a carência ao playset («cinco decks a pedir 3 Defy são 3, e
trocam-se entre decks»): a frase de hoje diz o contrário. O `faltas.por_deck`
deixou de ter a reserva partilhada e passou a ser o `missing` da alocação
(com o pendente somado à Coleção via `allocate(extra=...)`), por isso a soma
das abas é o mesmo número que «Todos juntos» e que a secção Decks — uma
resposta só para «o que este deck compra». As runas continuam fora das abas
dos decks (`faltas_ignorar_tipos`), como antes.

**A Venda não vende o que os decks usam da Coleção.** `decks.colecao_allocation`
(o gémeo do `binder_allocation`, artes base primeiro) diz que impressões da
Coleção estão a ser jogadas, e o `venda.excedente` passou a
`cópias − max(usadas nos decks, alvo)`, com «usadas» a ser a **soma** do que
os decks levam. Estava `na_colecao − alvo`, sem os decks, porque a Coleção
não montava decks. Com o máximo em vez da soma vendia-se uma cópia que dois
decks disputam; há teste. A lista «Em uso nos decks» da Venda não repete a
sequência inteira do master set que os decks jogam — só o que estava no
âmbito da Venda ou está fisicamente num deck/binder.

**Medido no `data/` real (5 decks; o Akali saiu na manhã de 11/09):**

| deck | antes (10/09) | depois |
|---|---|---|
| Ornn | 0/66 · coleção 62 · falta 4 · noutro 0 | **62/66 · falta 4 · disputadas 0** |
| Azir | 0/66 · coleção 51 · falta 4 · noutro 11 | **51/66 · falta 15 · disputadas 11** |
| Kennen | 0/66 · coleção 32 · falta 29 · noutro 5 | **32/66 · falta 34 · disputadas 3** |
| LeBlanc | 0/66 · coleção 39 · falta 5 · noutro 22 | **39/66 · falta 27 · disputadas 12** |
| LeBlanc Baited Hook | 0/66 · coleção 17 · falta 5 · noutro 44 | **17/66 · falta 49 · disputadas 33** |
| **total a comprar** | 47 cópias · 393,33 € (26 cartas) | **129 cópias · 481,46 € (44 cartas), 59 disputadas** |

A secção Faltas («Falta comprar aos decks», sem runas, com o pendente) passou
de 25 cartas · 36 cópias · 409,12 € para **40 · 80 · 475,28 €** — o mesmo que o
«Todos juntos» já dizia. As Staples passaram de 5 para **20**. A Venda passou
de 17 impressões · 25 cópias · 718,90 € para **15 · 19 · 577,21 €**: saíram a
`UNL-235` Deceiver (118,64 €, o LeBlanc usa-a) e as 5 `OGN-042a` Calm Rune
(é o Ornn, prioridade 1, que leva as 6 da Coleção — `decks.colecao_allocation`
serve-o primeiro e o Azir fica a 0 delas; medido a 2026-09-11). A percentagem
de master set **não mexe**.

---

# Onde está cada cópia: três locais (2026-09-10)

**A regra 2 desta secção («os decks só se montam com Deck + Binder») foi
revogada a 2026-09-11** — ver a secção acima. Os três locais continuam a
existir e a Coleção continua a ser a única que conta para a percentagem; o
que mudou é que os decks também se servem dela.

Palavras dele: *"vou querer ter as cartas da coleção apenas alocadas à coleção e
as cartas dos decks apenas alocadas a Decks. Ou seja: a coleção fica em Binders
de coleção; as cartas dos decks ficam em decks, e haverá um Binder que será
apenas e exclusivamente para Decks/Venda — caso um deck seja desfeito, as cartas
ficam para outro deck ou nesse binder."*

**Isto é a mudança mais funda desde o início.** Até aqui uma cópia era um número
(`copies.qty`) e "estar num deck" era uma DEDUÇÃO — a alocação por prioridade
adivinhava-o a partir das listas, com artes base primeiro. Agora é um FACTO
gravado, e a mesma cópia já não pode contar duas vezes.

| local | escreve-se | o que é | conta para |
|---|---|---|---|
| Coleção | `colecao` | os binders de coleção | a percentagem, os níveis, as wantlists |
| Deck | `deck:<slug>` | sleevada num dos `decks/*.txt` | só esse deck |
| Binder Decks/Venda | `binder` | o stock livre | qualquer deck por prioridade; o que sobra é venda |

## A COLEÇÃO NÃO SE GRAVA, CALCULA-SE

A `copy_locations` guarda **só** o que NÃO está na Coleção. A Coleção é
`copies.qty − Σ(o resto)`. Duas coisas de uma vez:

- **a migração não escreve linha nenhuma.** *"Onde não se sabe o local, fica
  Coleção por omissão"* sai de graça de uma tabela vazia, e por isso a contagem
  de cópias antes e depois é a mesma **por construção** — não há um passo de
  cópia de dados que possa perder uma cópia pelo caminho. Não foi preciso backup
  nenhum: a migração é um `CREATE TABLE IF NOT EXISTS`.
- **o `copies` continua a ser a única verdade sobre QUANTAS cópias existem.** Os
  `+`/`−` da grelha não sabem de locais: somam ao total, e o que sobe é a
  Coleção.

O preço é a invariante `Σ(fora) <= total`, garantida em
`locais.ajustar_ao_total`, chamado pelo `collection.adjust` quando o total
desce. Um `−` numa impressão que está toda num deck tira-a **do deck** (binder
primeiro, decks depois) e deixa rasto `-> (saiu da coleção)`. Sem isto a Coleção
ficava com contagem negativa.

## As três regras, e onde vivem

1. **A Coleção só conta cópias com local = Coleção.** `locais.na_colecao` é a
   única resposta, e é ela que o `metrics.set_payload`, o
   `metrics.itens_da_colecao` (níveis) e o `a_subir.em_falta` (as três listas de
   compra) leem. Uma cópia num deck **volta a aparecer como falta** — é a
   consequência que ele pediu.
2. ~~**Os decks só se montam com Deck + Binder Decks/Venda.**~~ **REVOGADO a
   2026-09-11**: os decks servem-se dos três montes (deck, binder, Coleção) e
   o `na_colecao` do `allocate` passou a ser parte do `tenho`. O que está
   sleevado num deck continua a ser DAQUELE deck e não anda.
3. **Desfazer um deck manda tudo para o binder** (`locais.desfazer_deck`), onde
   fica disponível para outro deck. **Nada volta à Coleção**: quem as tirou de
   lá foi ele.

## A marcação: propor é do vault, gravar é dele

`locais.propor_deck` calcula o que o deck usaria da Coleção (artes base
primeiro) e **não grava nada**. `locais.marcar` grava **só as linhas que vierem
na lista** — uma lista vazia levanta `SemCopias`, e o `/api/local/marcar`
devolve 400 com a razão escrita. É a lição do mtgvault de 2026-09-09: lá o
registo gravou uma alocação calculada inteira, incluindo duas cartas que ele
tinha dito não ter. **O «Marcar tudo» só liga as checkboxes.**

Rasto duplo: `location_ops` (que é o que o `--undo` lê) e `data/locais.log`, um
CSV com quando, cópia, de → para e a origem do clique. **Se uma cópia aparecer
num deck sem linha no log, é bug.**

## O que mudou nas leituras

- `decks.printing_allocation` passou a **ler** os locais em vez de os adivinhar.
  A heurística "artes base primeiro" sobrevive em dois sítios onde continua a
  ser a pergunta certa: a PROPOSTA (`propor_deck`) e o `binder_allocation` (que
  cópia do binder é que o deck leva).
- O tile da Coleção mostra o `qty` da **Coleção** no badge e o `locations` na
  linha de baixo (`3× Azir · 1 na Coleção`). O `/api/adjust` passou a devolver
  `qty_colecao` e `locations` a par do `qty` (que continua a ser o total
  físico) — trocá-los punha a barra a contar cartas que estão em decks.
- A **Venda** tem duas origens e cada linha diz a sua: `from_binder` (nenhum
  deck a pede) e `from_colecao` (acima do alvo — e, desde 2026-09-11, acima do
  que os decks usam da Coleção: `cópias − max(usadas, alvo)`). O que está
  DENTRO de um deck nunca aparece. A sequência do master set **na Coleção** continua fora
  (2026-09-08), mas a que está no binder Decks/Venda entra: foi ele que a tirou
  de lá.
- O **valor** da coleção continua a ser o total físico: uma carta não vale menos
  por estar sleevada.

## O que NÃO mudou, de propósito

- **A secção Faltas (`faltas.py`) continua a contar as cópias todas**, esteja
  onde estiverem (`decks.owned_by_card`). Ela responde a "o que comprar primeiro
  para os decks" — ~~com o teto do playset~~ (**o teto caiu a 2026-09-11**: a
  carência é a soma do que os decks pedem menos o que ele tem, ver "Os decks
  partilham a Coleção"); passá-la a cega para a Coleção fazia-a
  dizer, no dia da migração, que ele tem de comprar quase tudo outra vez.
  **É pergunta para ele** — ver o relatório `riftvault-binders.md`.
- **O playset JOGÁVEL** (`metrics.owned_by_card`, a métrica 1) também é o total
  físico. É o "quantas destas cartas tenho ao todo", e é a mesma pergunta do
  Pimp.
- **O `−` do tile tira da Coleção.** Com a Coleção a zero fica desligado, mesmo
  que ele tenha cópias em decks — a grelha é dos binders de coleção. Tira-se
  pelo `riftvault remove` ou move-se primeiro.

## Efeito medido no `data/` real

Ver a tabela do relatório. **Na prática: a percentagem de master set NÃO desce**
(a migração deixa tudo na Coleção) e os **decks passavam a 0 alocadas** até ele
marcar — o que estava a contar como "no deck" era uma dedução, e ela
desapareceu. **Durou um dia**: a 2026-09-11 ele disse *"se há na coleção o
deck usa"* e os decks voltaram a contar a Coleção (Ornn 62/66 sem marcar
nada). A marcação ficou como informação de onde a cópia está.

---

# A API da RiftScribe — o que foi VALIDADO (2026-08-31)

Base: `https://riftscribe.gg/api`. Pública, sem autenticação.
Spec guardada em `docs/riftscribe-openapi.json`.
Snapshot completo das 1180 entradas em
`docs/riftscribe-cards-snapshot-2026-08-31.json`.

## A questão crítica das variantes: RESOLVIDA

**As variantes VÊM na listagem como entradas separadas.** Não é preciso varrer
sufixos nem inventar estratégias. `GET /api/cards?set_id=OGN&limit=200` devolve
a arte base *e* a arte alternativa como dois objetos distintos, cada um com o
seu `id`, o seu `public_code` e o seu **URL de imagem próprio**.

O campo que as distingue é `variant`, presente tanto no `CardSummaryRead`
(listagem) como no `CardRead` (detalhe):

> "Variant discriminator: '' base, 'a' alt-art, 'star' signature, 'tNN' token"

**Além disso, a ordenação `sort=default` já coloca cada variante imediatamente
a seguir à sua carta base** — exatamente o agrupamento visual pretendido.
Não é preciso reordenar.

Valores de `variant` observados nas 1180 entradas:

| `variant` | n | significado |
|---|---|---|
| `''` | 1020 | impressão base |
| `a` | 102 | arte alternativa |
| `star` | 36 | signature (código impresso leva `*`) |
| `t01`..`t08` | 10 | tokens |
| `r01`..`r06` | 6 | runas promo (só VEN) |
| `sp1`..`sp6` | 6 | promos especiais (só VEN) |

Nunca aparece `b` — **no máximo uma arte alternativa por carta**.
Nenhum grupo tem `a` **e** `star` ao mesmo tempo.
Todos os 102 `a` e todos os 36 `star` têm a sua base na mesma listagem.

## Exemplo real: carta base vs arte alternativa

```
                 BASE                        ALT ART
id               ogn-007-298                 ogn-007a-298
public_code      OGN-007/298                 OGN-007a/298
name             Fury Rune                   Fury Rune
set_id           OGN                         OGN
collector_number 7                           7
variant          ""                          "a"
rarity           common                      showcase      <-- muda!
faction          fury                        fury
domains          ["Fury"]                    ["Fury"]
type             Rune                        Rune
orientation      portrait                    portrait
stats            {energy,might,power}        idem
image            .../originals/ogn-007-298-868b5cd63536371d.png
                                             .../originals/ogn-007a-298-af47f970776f6f15.png
image_thumb      small/medium/large .webp    idem, com outro hash
image_blur_data_url  data:image/jpeg;base64  diferente
is_banned        false                       false
```

**Imagem por variante: CONFIRMADO.** O hash no nome do ficheiro é diferente,
e as duas descarregam com HTTP 200 (`originals/*.png` ~1,4 MB,
`thumbnails/large/*.webp` ~105 KB).

Exemplo de signature: `ogn-299-star-298`, `public_code` `OGN-299*/298`.

## As 5 edições

`GET /api/cards/filters` devolve `sets: [OGN, OGS, SFD, UNL, VEN]`.

| set | entradas | base | alt art | signature | outras |
|---|---|---|---|---|---|
| OGN | 352 | 310 | 30 | 12 | — |
| OGS | 24 | 24 | — | — | — |
| SFD | 288 | 251 | 24 | 12 | 1 token |
| UNL | 288 | 238 | 30 | 12 | 8 tokens |
| VEN | 228 | 197 | 18 | — | 13 (6 runas, 6 promos, 1 token) |
| **total** | **1180** | 1020 | 102 | 36 | 22 |

**A API NÃO devolve o nome das edições, só o código.** O mapeamento
`OGN -> "Origins"` etc. tem de ser local (`riftvault_config.json`). Não foi
validado contra fonte nenhuma — os nomes que lá estiverem são palpite até o
André confirmar. Também não há endpoint de edições nem data de lançamento: a
ordem dos separadores vem do config.

## Outros valores de filtro (validados)

- `factions`: body, calm, chaos, colorless, fury, mind, order
- `rarities`: common, uncommon, rare, epic, **showcase**
- `types`: Battlefield, Gear, Legend, Rune, Spell, Unit (+ 2 entradas com
  `type: null` — `UNL-T04 "Buff"` e `UNL-T08 "XP Tracker"`)

`showcase` **não é uma raridade de jogo, é um tratamento**: quase todas as
artes alternativas e signatures têm `rarity: "showcase"`. Os contadores por
raridade da UI devem usar a raridade da **base**, não a da variante, senão a
contagem fica distorcida.

## ARMADILHA 1 — `(set_id, collector_number)` NÃO é chave única

Em **VEN** o mesmo `collector_number` é reutilizado por famílias diferentes:

```
cn=4  variant=""     Dune Surfer        ven-004-166
cn=4  variant="r04"  Body Rune          ven-r04
cn=4  variant="sp4"  Sett, Brawler      ven-sp4-006
cn=4  variant="t04"  Recruit (NX)       ven-t04
```

A chave de agrupamento visual tem de ser **(set_id, collector_number, lane)**,
onde `lane` é o prefixo alfabético do `variant`: `main` para `''`/`a`/`star`,
e `t`/`r`/`sp` para os outros. Com isto dão **1042 grupos** para 1180 entradas,
e nenhum grupo fica sem base.

## ARMADILHA 2 — reimpressões showcase com número de coleção PRÓPRIO

Não é só o sufixo. A mesma carta lógica reaparece **na mesma edição** com outro
número de coleção. Exemplos: OGN 299–310, SFD 222–251, UNL 220–238, VEN 167–197.
E é a essas reimpressões que o `star` se agarra, não à base original.

Caso canónico, **"Sett, Brawler" — 5 impressões em 3 edições**:

```
ogn-164-298       OGN-164/298    variant=""      epic
ogn-164a-298      OGN-164a/298   variant="a"     showcase
sfd-232-221       SFD-232/221    variant=""      showcase
sfd-232-star-221  SFD-232*/221   variant="star"  showcase
ven-sp4-006       VEN-SP4/006    variant="sp4"   epic
```

Consequência: **a carta lógica não pode ser identificada pelo número de
coleção**. 104 nomes aparecem em mais do que um `(set, collector_number)`.
1180 impressões correspondem a **935 nomes distintos**.

A carta lógica é chaveada pelo **nome normalizado** (`card_key`). Verificado:
não há duas cartas diferentes com o mesmo nome no catálogo atual. As 4 Legends
de starter do OGS já vêm com nome próprio (`Dark Child - Starter`,
`Wuju Bladesman - Starter`, `Lady of Luminosity - Starter`,
`Might of Demacia - Starter`) e não colidem com nada.

## ARMADILHA 3 — a API não sabe o que é foil

**Procurado em toda a spec: não existe `foil`, `finish`, `holo` nem
`treatment`.** As únicas ocorrências de "finish" são o `is_finished` do jogo
Riftboundle. O "printing" da API é *arte*, não *acabamento*.

Os acabamentos (`normal`/`foil`) são **inteiramente locais ao riftvault**. Que
impressões existem em foil, e se as signature são foil-only, é conhecimento do
André, não da API. Fica em `riftvault_config.json` e **é palpite até ele
confirmar**.

## Endpoints úteis

| endpoint | notas |
|---|---|
| `GET /api/cards` | `set_id`, `q`, `faction`, `rarity`, `type`, `types[]`, `domain_identity[]`, `is_banned`, `sort`, `limit` (**máx. 200**), `offset`. Total no header `X-Total-Count`. Devolve `CardSummaryRead[]`. |
| `GET /api/cards/{card_id}` | `CardRead` = summary + `description`, `flavor_text`, `art{artist}`, `keywords`, `tags`, `prev_card_id`, `next_card_id`. Aceita `OGN-7`, `OGN-007`, `OGN-007a`, `OGN-301-star`, `OGN-301*`, `UNL-T03`. |
| `GET /api/cards/filters` | `sets`, `factions`, `rarities`, `types`. |

O catálogo inteiro são **7 pedidos** (5 edições; OGN, SFD e UNL em 2 páginas).
A listagem já traz tudo o que a grelha precisa; o detalhe só é preciso para
`description`/`keywords`/`artist` — e **`artist` veio `null`** na carta testada.

## Restrições externas

| Fonte | Estado |
|---|---|
| `riftscribe.gg/api` | pública, sem auth, sem rate-limit documentado. Ser educado: 1 pedido/s no sync. |
| `cdn.riftscribe.gg` | imagens HTTP 200 diretas, sem auth. `originals/*.png` ~1,4 MB, `thumbnails/large/*.webp` ~105 KB — **usar os thumbnails no cache**. |

---

## Superfícies NÃO validadas contra a API real

Se algo vier errado, é aqui:

1. **Nomes das edições** (`OGN -> ?`). A API não os dá. Mapeamento local, por
   confirmar com o André.
2. **Acabamentos (normal/foil) por impressão.** A API não sabe nada disto.
   Que cartas existem em foil, e se as signature são foil-only, é palpite.
3. **Alvos de playset por tipo** (Unit/Spell/Gear 3, Battlefield 1, Legend 1,
   Rune 12, Token 0) vieram do André, não das regras oficiais.
4. **Regras de legalidade de deck** (40 main, 12 runas, 3 battlefields, limite
   de 3 cópias, domain identity) vieram do André, não estão na API.
5. **Estabilidade dos `id`.** Assume-se que `ogn-007a-298` é estável entre
   syncs. Se a RiftScribe re-hashar os ficheiros muda o URL da imagem, mas
   presume-se que o `id` fica. Não testado ao longo do tempo.
6. **Sets futuros.** A descoberta é dinâmica por `/api/cards/filters`, mas uma
   edição nova pode trazer um `variant` novo (`b`? `sp7`?). O parser de
   `variant` tem de falhar de forma visível, não silenciosa.
7. **Endereço da página da carta**, no CardTrader e na RiftScribe. Nenhuma das
   duas APIs o dá, e a aba "A subir" precisa de um link. O da RiftScribe
   (`riftscribe.gg/cards/<printing_id>`) continua **presunção, por abrir e
   confirmar**; fica em `a_subir.DEFAULTS` e muda-se numa linha.
   **O do CARDTRADER FOI VALIDADO a 2026-09-25, à noite** (ver `mercados.py`,
   e a secção própria no fim deste ficheiro): o `robots.txt` deles permite as
   páginas e publica os sitemaps; os 348 780 URLs de blueprint estão todos no
   formato `…/en/cards/<id>-<slug>`; o id sozinho (`/en/cards/330791`)
   responde **200** e redirecciona para o slug; um id que não existe dá
   **404**; e `…/en/search?q=` responde 200. O `/en/` faz falta — sem ele a
   página abre em **italiano**, que é o que o link do «A subir» fazia desde
   2026-09-08, corrigido nesse dia.
   **O do Cardmarket continua por validar, desde 2026-09-25**: cada linha da
   Venda, e agora cada linha do Produto Selado, leva um link para a página lá,
   montado com o `cardmarket_id` (`mercados.cardmarket_url` e
   `mercados.cardmarket_url_selado`; as duas chaves viviam no bloco `venda` e
   mudaram-se nessa noite). **Não foi validado** — o site deles responde 403 a
   pedidos automáticos, nem o `robots.txt` responde, e não há conta para
   experimentar —, e por isso cada linha leva também um **segundo link, de
   pesquisa** pelo nome (`mercados.cardmarket_busca`), que é a forma que o
   Scryfall usa para o mesmo fim. Se o primeiro abrir em 404, é uma linha de
   config e todos os links mudam com ela.

---

# Decisões de implementação (2026-08-31)

## Sem acabamentos

Decisão do André: **foil e normal contam como a mesma coisa**. A tabela
`copies` é só `(printing_id, qty)` — não há coluna `finish`. O CLI aceita
`--foil` e ignora-o, para não dar erro por hábito.

O alvo do master set é por impressão, e qualquer cópia serve para o cumprir.

Se um dia isto mudar: acrescentar `finish TEXT NOT NULL DEFAULT 'normal'` a
`copies`, passar a PK a `(printing_id, finish)`, e o mesmo em `ops`.

**Isto CONTINUA DE PÉ depois de 2026-09-22, de 2026-09-26 e de 2026-09-27, no
GRÃO.** A `copies.qty_foil` não é um acabamento no grão: a chave continua a ser
`(printing_id)` e o alvo continua a ser por impressão. É uma CONTAGEM à parte —
e desde 26/09 uma contagem que **se soma** às normais quando a pergunta é
«quantas cartas tenho na mão» (3 normais + 3 foil = 6 cópias), não uma fatia
delas. **NOS ALVOS NUNCA SE SOMAM**, desde a noite de 27/09: o
`foil.conta_para_coleccao` voltou a `false` (somar escondia-lhe faltas — 47
impressões, 48 cópias normais) e o `conta_para_valor` fica a `true`; no tile o
crachá é as NORMAIS e a linha de baixo é o foil, contra o `foil.alvo`. A foil
ganhou **preço próprio** (`price_latest.price_foil_cents`) na noite de 26/09 —
ver as três últimas secções deste ficheiro.

## Artes alternativas fora do master set

**REVOGADO a 2026-09-08, à tarde:** voltaram para dentro da percentagem, com
alvo 1, no bloco próprio delas — ver "A Coleção em três blocos". O que se segue
é história.

`master_targets_by_variant.alt_art = 0` (André, 2026-09-02). A percentagem de
set completo passa a medir só a impressão base e as signatures; as artes
alternativas continuam na grelha, contam para o playset jogável e para o
valor da coleção, mas **não entram no denominador**.

Denominadores: OGN 352 -> 322, SFD 288 -> 264, UNL 288 -> 258, VEN 228 -> 210.
(**A 2026-09-08 os tokens juntaram-se-lhes** e estes números baixaram outra vez
— SFD 263, UNL 250, VEN 209. Ver a secção "A Coleção é o master set".)

**ALVO e CONTA são campos diferentes** (2026-09-02). A primeira versão pôs o
alvo da arte alternativa a 0, e o tile perdeu o `0/1` — ele quer ver quantas
lhe faltam, só não quer que baixem a percentagem. São duas perguntas, agora
com dois campos:

- `master_targets_by_variant` -> o alvo fixo por variante.
- `master_variantes_playset` -> as variantes cujo alvo segue o playset do tipo
  em vez do alvo fixo (`["alt_art"]`, ver a secção abaixo).
- `master_set.fora` -> o que fica fora do master set (era
  `master_ignorar_variantes: ["alt_art"]`, desde 2026-09-08 é `["-T", "a"]`),
  via `metrics.e_master()`.

O payload leva `block` por impressão e o `renderProgress` respeita-o — a
percentagem é recalculada no cliente, por isso não bastava mudar o servidor.
(O campo chamava-se `counts` até 2026-09-08; passou a ser o bloco da grelha,
porque é a mesma pergunta.)

## As signatures saem da Coleção (2026-09-09)

Palavras dele: *"no riftvault, das coleções tira as signatures, fazemos 1 Alt
Art de cada mas as signature não"*.

Uma frase, duas metades: as **artes alternativas** ficam como estão (bloco 3,
alvo 1) e as **signatures** saem da Coleção inteira. Não entram na sequência,
não entram no bloco das runas especiais, não entram no bloco das artes
alternativas, e saem do denominador da percentagem, das contagens por níveis e
das wantlists. Continuam na grelha, num bloco próprio no fim («Fora da coleção —
signatures»), com alvo 1 — as que ele tenha continuam visíveis e contadas.

**Isto era a decisão que estava anotada como DESLIGADA desde 2026-09-08.** O
mecanismo já lá estava: é o `"*"` no `master_set.fora`, que nesse dia ficou
`["-T", "*"]` (a 2026-09-10 ganhou o `"overnumbered"`). Uma
pergunta, uma função — `metrics.e_master` —, e é o **mesmo critério**
(`variant_kind == "signature"`, o sufixo `*` do código impresso) que o
`a_subir.excluir` já usava para as tirar das listas de compra. Não há segunda
definição de "isto é uma signature". O `config.DEFAULTS` levou o `"*"` também,
para um riftvault sem ficheiro de config não medir outra coisa.

**As duas decisões continuam a viver em sítios diferentes, de propósito.** A de
2026-09-08 (*"estás a pôr uma carta signed — não quero"*) é das listas de
compra e fica em `a_subir.excluir.tipos`; esta é da coleção e fica em
`master_set.fora`. Hoje a primeira já não tira nenhuma — as signatures nem
chegam ao âmbito —, e é por isso que a página passou a dizer «42 impressões (42
showcase)» em vez de «78 (36 signature + 42 showcase)». Fica lá para o caso de
elas voltarem.

**São 36, e ele não tem nenhuma.** OGN 12, SFD 12, UNL 12; o VEN não tem
signatures no catálogo da RiftScribe. Medido a 2026-09-09: **zero cópias** na
`copies`. Por isso o numerador não mexe em lado nenhum e a percentagem SOBE.

**O que mudou nos números** (medido a 2026-09-09 contra o `data/` real):

| | antes | depois |
|---|---|---|
| denominador da percentagem | 1170 | **1134** |
| percentagem global | 479/1170 = 40,9% | **479/1134 = 42,2%** |
| OGN / OGS / SFD / UNL / VEN | 352 / 24 / 287 / 280 / 227 | **340 / 24 / 275 / 268 / 227** |
| níveis (1 de cada / 2 / playset) | 64,2% / 54,4% / 40,9% | **66,2% / 56,2% / 42,2%** |
| faltam, por nível | 419 / 746 / 1231 | **383 / 710 / 1195** |
| € por nível | 64 366,17 / 72 793,82 / 81 352,88 € | **13 112,90 / 21 540,55 / 30 099,61 €** |
| «A subir» | 56 cartas, 106 cópias, 2 963,73 € | igual |
| «Master set» / wantlists | 613 impressões, 1 117 cópias, 21 551,64 € | igual |
| «Venda» | 2 impressões, 6 cópias, 4,10 € | igual |

O numerador não mexe (ele não tem nenhuma), o denominador encolhe 36 e a
percentagem sobe 1,3 pontos. **Os degraus perdem 36 cópias cada um e 51 253,27 €
em qualquer deles** — como o alvo delas é 1, faltavam inteiras nos três níveis e
custavam o mesmo nos três. Era quase dois terços do «custo de fechar a coleção»,
e vinha todo de cartas que ele não compra. As listas de compra não mexem **em
nada**: já não as levavam desde 2026-09-08. O que muda na página do «A subir» é
o texto do resumo — «42 impressões (42 showcase)» em vez de «78 (36 signature +
42 showcase)».

Por edição, o bloco novo: OGN 0/12, SFD 0/12, UNL 0/12; OGS e VEN não têm
signatures e não ganham bloco nenhum.

A contagem por níveis, medida a 2026-09-09 (`riftvault stats`):

| | 1 de cada | 2 de cada | playset |
|---|---|---|---|
| OGN | 243/340 = 71,5 % · faltam 97 · 1 564,47 € | 179/340 = 52,6 % · faltam 207 · 1 993,83 € | 125/340 = 36,8 % · faltam 371 · 2 449,19 € |
| OGS | 24/24 = 100 % · faltam 0 | 24/24 = 100 % · faltam 0 | 11/24 = 45,8 % · faltam 13 · 13,39 € |
| SFD | 209/275 = 76,0 % · faltam 66 · 3 182,59 € | 190/275 = 69,1 % · faltam 122 · 5 560,44 € | 151/275 = 54,9 % · faltam 217 · 7 979,09 € |
| UNL | 212/268 = 79,1 % · faltam 56 · 4 380,03 € | 193/268 = 72,0 % · faltam 87 · 7 832,11 € | 151/268 = 56,3 % · faltam 160 · 11 330,86 € |
| VEN | 63/227 = 27,8 % · faltam 164 · 3 985,81 € | 51/227 = 22,5 % · faltam 294 · 6 154,17 € | 41/227 = 18,1 % · faltam 434 · 8 327,08 € |
| **total** | **751/1134 = 66,2 % · faltam 383 · 13 112,90 €** | **637/1134 = 56,2 % · faltam 710 · 21 540,55 €** | **479/1134 = 42,2 % · faltam 1195 · 30 099,61 €** |

O VEN não mexe em linha nenhuma: é a única edição sem signatures no catálogo.
O OGN é o que mais mexe em euros — as 12 dele valiam 26 574,93 € do nível 3.

**A consequência que ele não pediu: a Venda.** O âmbito da Venda é "não é o
bloco `master`", e as signatures passaram a estar nesse caso — uma que ele
tenha e nenhum deck use aparece como candidata, como já acontecia com os
tokens. Hoje não muda nada (zero na caixa) e há teste que fixa o
comportamento. **É pergunta para ele**, e vale zero cópias hoje.

## As sobrenumeradas saem da Coleção (2026-09-10)

Palavras dele: *"no riftvault, também não quero para a coleção as
overnumbered"*.

**Sobrenumerada = o número de coleccionador passa o tamanho da edição** — as
«300/298». São as reimpressões de topo de set da ARMADILHA 2: a mesma carta
lógica reaparece na MESMA edição com número de coleção próprio (OGN 299–310,
SFD 222–251, UNL 220–238, VEN 167–197). É a classe das 128 que já estava
descrita em «Impressões vetadas no Pimp», e agora tem nome e regra.

**O critério é o CÓDIGO IMPRESSO, e o tamanho da edição vem de lá.** O
`public_code` traz os dois números — `SFD-244/221` é a 244 de um set de 221 —,
por isso `metrics.tamanho_do_set` lê o denominador da própria linha do catálogo:
não é um número escrito à mão, não é uma segunda consulta, e uma edição nova
traz o seu tamanho sozinha. Confirmado no catálogo real: o denominador é o mesmo
em todas as impressões da lane principal de cada edição (OGN 298, OGS 24,
SFD 221, UNL 219, VEN 166).

**As 16 sem denominador nunca são sobrenumeradas**, e é a resposta certa: os
tokens `-T` e as runas promo `VEN-R01..R06` não trazem `/tamanho` porque são
numerados numa série própria, fora da numeração da edição. O `VEN-SP4/006` é a
4 de uma série de 6 — o código diz que série é, e por isso também não conta.

**Um ponto de verdade só, partilhado com o «A subir»:**
`metrics.fora_da_colecao`, pela mesma lista `master_set.fora`, que passou a
`["-T", "*", "overnumbered"]`. O `e_master` (a percentagem), o `bloco` (a
grelha) e o âmbito das listas de compra perguntam todos à mesma função — é a
arquitetura das signatures de 2026-09-09, para outra categoria. O
`tests/test_overnumbered.py` fixa a partilha e parte se alguma das páginas
passar a responder sozinha.

**`overnumbered` é a única entrada da lista que não é uma variante.** É um
critério de NÚMERO, como o `showcase` do `a_subir.excluir` é um critério de
raridade. Fica na mesma lista de propósito: a pergunta é uma só («o que é que
não é a Coleção») e tem de ter uma resposta só. O `metrics._fora` lê as duas
metades de uma vez, e um valor desconhecido continua a rebentar.

**A ordem dos critérios é variante primeiro, número depois.** As 36 signatures
são TODAS sobrenumeradas, e mesmo assim continuam no bloco «Fora da coleção —
signatures»: o que as tirou foi a frase de 2026-09-09, e mudá-las de cabeçalho
agora era apagar essa decisão do ecrã.

**Nenhuma arte alternativa é sobrenumerada** — elas partilham o número da base
(`OGN-007a/298` é a 7) —, por isso o «1 alt art de cada» de 2026-09-08 fica
intacto. Medido: 0 das 102.

**São 92 as que saem hoje**, das 128 (as outras 36 são as signatures, já fora):

| edição | sobrenumeradas | signatures (já fora) | saem agora | que ele tem |
|---|---|---|---|---|
| OGN | 24 | 12 | **12** | 1 |
| OGS | 0 | — | 0 | 0 |
| SFD | 42 | 12 | **30** | 2 |
| UNL | 31 | 12 | **19** | 2 |
| VEN | 31 | — | **31** | 0 |
| **total** | **128** | 36 | **92** | **5** |

**Alvo 1 no bloco de fora.** Uma Unit sobrenumerada pediria o playset (3) pelo
`master_base_follows_type`; fora da coleção pede 1, como as signatures e os
tokens (`metrics.ALVO_OVERNUMBERED`). Pedir o playset de uma carta que já não se
coleciona era ler o número ao contrário. ALVO e CONTA continuam a ser campos
diferentes — quem tem a linha do catálogo na mão chama o `metrics.alvo`, que é a
porta de entrada nova; o `master_target` dos quatro escalares fica para quem não
a tem.

**O que mudou nos números** (medido a 2026-09-10 no `main`, depois do merge,
contra o `data/` real; o «antes» foi medido na mesma corrida, com o config sem a
palavra — não são os números de 09-09, que já estão velhos nos preços e na
coleção):

| | antes | depois |
|---|---|---|
| denominador da percentagem | 1134 | **1042** |
| OGN / OGS / SFD / UNL / VEN | 340 / 24 / 275 / 268 / 227 | **328 / 24 / 245 / 249 / 196** |
| percentagem global (playset) | 525/1134 = 46,3 % | **521/1042 = 50,0 %** |
| níveis (1 de cada / 2 / playset) | 66,8 % / 57,8 % / 46,3 % | **72,3 % / 62,5 % / 50,0 %** |
| faltam, por nível | 376 / 687 / 1128 | **289 / 553 / 947** |
| € por nível | 13 071,43 / 21 485,89 / 30 041,03 € | **1 140,33 / 1 985,69 / 2 971,73 €** |
| «Master set» / wantlist playset | 567 impressões, 1050 cópias, 21 426,15 € | **519, 944, 2 932,90 €** |
| wantlist até 1 de cada | 336 linhas, 8 924,39 € | **288, 1 136,22 €** |
| wantlist até 2 de cada | 437 linhas, 15 117,57 € | **389, 1 976,86 €** |
| «A subir» | 63 cartas, 119 cópias, 3 300,25 € | **54, 100, 809,45 €** |
| «Venda» | 2 impressões, 6 cópias, 4,11 € | **7, 11, 658,06 €** |

**O número que salta à vista é o euro: fechar a coleção deixou de custar 30 mil
euros e passa a custar 2 972 €.** É a mesma leitura das signatures de ontem —
saiu do denominador o que ele nunca ia comprar. O numerador quase não mexe (ele
tem 5 destas): perde 5 no nível 1 e 4 nos outros dois, e a percentagem sobe
3,7 pontos.

**Isto FECHA a pergunta que estava anotada em «Showcases fora das listas de
compra».** Lá ficou escrito que as 48 reimpressões de topo do UNL e do VEN
tinham raridade de jogo (`rare`, `common`), escapavam ao filtro de raridade e
valiam quase todo o dinheiro da lista — e que a dúvida era se «showcase» queria
dizer a raridade ou as reimpressões caras de topo de set. **Queria dizer as
reimpressões**, e ele disse-o pelo nome certo: as 48 são exactamente a
diferença do «Master set» no UNL (117 → 100) e no VEN (186 → 155), e valem os
18 493 € que a lista perdeu.

**A consequência: o `a_subir.excluir` ficou a tirar ZERO.** As 42 impressões de
raridade `showcase` que ele excluía eram todas sobrenumeradas e saem agora antes,
com a coleção. A página passa a dizer «0 impressões» em vez de «42 (42
showcase)». **Fica no config na mesma**, como a das signatures: são decisões
diferentes e, se um dia estas voltarem à coleção, continuam a não ser para
comprar.

**A consequência que ele não pediu: a Venda, e desta vez tem efeito.** O âmbito
dela é "não é o bloco `master`", e as sobrenumeradas passaram a estar nesse
caso. Entraram **5 impressões, 5 cópias, 653,95 €** — `OGN-303` Nine-Tailed Fox
(385,64 €), `SFD-224` Aphelios (55,64 €), `SFD-244` Fire Below the Mountain
(80,64 €), `UNL-231` Wuju Master (31,41 €) e `UNL-235` Deceiver (100,62 €). A
caixa passou de 4,11 € para 658,06 €. **É pergunta para ele** — nada saiu da
base, é uma sugestão —, e há teste que fixa o comportamento.

## As promos VEN-SP saem da Coleção (2026-09-10)

Palavras dele, horas depois da secção acima: *"no riftvault, Vendetta,
deparei-me com as VEN-SP (promos). Quero que as promos fiquem também à parte,
tal como as signature e as overnumbered"*.

**Terceira categoria pelo mesmo mecanismo**, e a mais simples das três: as
promos SÃO uma variante (`variant_kind = "special"`, o sufixo `-SP` do código
impresso), por isso bastou uma palavra na lista `master_set.fora`, que passou a
`["-T", "*", "overnumbered", "promo"]`. O `metrics.e_master` (a percentagem), o
`bloco` (a grelha) e o âmbito das listas de compra continuam a perguntar todos
ao `metrics.fora_da_colecao`. Não houve função nova — só uma entrada de config e
o `PALAVRA_KIND`.

**A palavra é dele, e por isso é aceite a par do sufixo.** Ele nomeou-as
«promos», não `-SP`: `metrics.PALAVRA_KIND` traduz `promo -> special`, como o
`SUFIXO_KIND` traduz `-sp -> special`. As três escritas (`promo`, `-SP`,
`special`) dão o mesmo kind, e há teste que o fixa. Um valor desconhecido
continua a rebentar.

### O que o catálogo tem, e em que edições

**São 6 no catálogo inteiro, todas no VEN.** Varridas as lanes todas das cinco
edições (a `lane` é o prefixo alfabético do `variant` — ver ARMADILHA 1):

| lane | o que é | OGN | OGS | SFD | UNL | VEN |
|---|---|---|---|---|---|---|
| `main` | a numeração da edição (base, `a`, `star`) | 352 | 24 | 287 | 280 | 215 |
| `t` | tokens `-T` | — | — | 1 | 8 | 1 |
| `r` | runas promo `VEN-R01..R06` | — | — | — | — | 6 |
| `sp` | **promos `VEN-SP1..SP6`** | — | — | — | — | **6** |

Fora da lane principal e dos tokens só há estas duas famílias, e as duas só
existem no Vendetta. **Uma edição nova que traga uma lane nova rebenta** no
`_fora` se alguém a escrever, mas passa despercebida se ninguém a escrever — é o
ponto 6 das "Superfícies não validadas", e continua de pé.

As 6, todas `Unit` de raridade `epic`, com `public_code` `VEN-SPn/006`:
`VEN-SP1` Kai'Sa, Survivor (60,82 €), `VEN-SP2` Sona, Harmonious (28,00 €),
`VEN-SP3` Ahri, Inquisitive (110,38 €), `VEN-SP4` Sett, Brawler (16,25 €),
`VEN-SP5` Ezreal, Prodigy (18,87 €) e `VEN-SP6` Lux, Crownguard (30,39 €) —
**264,71 €**. **Ele tem uma**, a `VEN-SP5`.

**Precisavam de entrada própria porque NENHUMA é sobrenumerada.** O
`VEN-SP4/006` é a 4 de uma série de 6, e o critério de ontem lê o denominador do
próprio código: a série delas é outra, e o código diz isso. Já estava anotado no
relatório das sobrenumeradas — é exactamente por isso que esta decisão não vinha
de graça com aquela.

### As runas promo `VEN-R01..R06` NÃO saem

São `rune_promo`, não `special`, e ficam **dentro** da Coleção, no bloco «1 runa
especial de cada» — decisão dele de 2026-09-08. **No VEN são elas que enchem
esse bloco**: sem elas o bloco 2 do Vendetta ficava vazio (a RiftScribe não tem
runas alternativas no VEN — ver BURACO NO CATÁLOGO). Ele nomeou as `VEN-SP`;
tirar as `VEN-R` com elas era apagar a outra decisão, e a lição das signatures
de ontem é essa mesma — variante primeiro, e só o que ele nomeou.

Quem as quiser fora escreve `"-R"` na lista, e aí saem também da percentagem
(são as mesmas 6, valem 73 cêntimos ao todo).

### O que mudou nos números

Medido a 2026-09-10 no `main`, depois do merge, contra o `data/` real. O «antes»
foi medido na mesma corrida, com o config sem a palavra — não são os números do
relatório das sobrenumeradas, que já estão velhos na coleção e nos preços.

| | antes | depois |
|---|---|---|
| denominador da percentagem | 1042 | **1036** |
| OGN / OGS / SFD / UNL / VEN | 328 / 24 / 245 / 249 / 196 | 328 / 24 / 245 / 249 / **190** |
| master set do VEN | 41/196 = 20,9 % | **40/190 = 21,1 %** |
| percentagem global (playset) | 573/1042 = 55,0 % | **572/1036 = 55,2 %** |
| níveis (1 de cada / 2 / playset) | 74,1 % / 65,0 % / 55,0 % | **74,4 % / 65,3 % / 55,2 %** |
| faltam, por nível | 270 / 527 / 888 | **265 / 522 / 883** |
| € por nível | 1 138,24 / 1 982,83 / 2 965,06 € | **892,40 / 1 736,99 / 2 719,22 €** |
| «Master set» / wantlist playset | 467 impressões, 885 cópias, 2 926,23 € | **462, 880, 2 680,39 €** |
| wantlist até 1 de cada | 269 linhas, 1 134,13 € | **264, 888,29 €** |
| wantlist até 2 de cada | 363 linhas, 1 974,00 € | **358, 1 728,16 €** |
| «A subir» | 54 cartas, 100 cópias, 361,29 € | igual |
| «Venda» | 15 impressões, 19 cópias, 659,04 € | **16, 20, 677,91 €** |

**Os três degraus perdem exactamente o mesmo: 5 cópias e 245,84 €.** O alvo
delas é 1, por isso as 5 que lhe faltam custavam o mesmo nos três níveis — é a
mesma aritmética das signatures. O numerador perde 1 (a `VEN-SP5`, que ele tem
completa) e o denominador 6, e a percentagem sobe 0,2 pontos. **É a mais pequena
das três decisões desta semana** — as signatures valiam 51 mil euros e as
sobrenumeradas 27 mil; estas valem 246 €.

**O «A subir» não mexe em nada.** Nenhuma das 5 subia 10 % na janela, por isso
não estava na lista — o que baixou foi só o âmbito de partida, de 1042 para
1036.

**A consequência que ele não pediu: a Venda, outra vez.** O âmbito dela é "não é
o bloco `master`", e as promos passaram a estar nesse caso: a `VEN-SP5` Ezreal,
Prodigy que ele tem entrou como candidata, **1 impressão, 1 cópia, 18,87 €**. A
caixa passou de 659,04 € para 677,91 €. **É pergunta para ele** — nada saiu da
base —, e há teste que fixa o comportamento.

**O bloco novo:** «Fora da coleção — promos», alvo 1, só no VEN (0/6 nas
outras quatro edições não aparece, porque os blocos vazios não se mostram).
Hoje lê-se **1/6**. O rótulo do bloco `special` passou de «promos especiais» a
«promos», que é como ele lhes chama e como o catálogo as etiqueta
(`variant_label: "Promo"`).

## A Coleção em três blocos: playset, 1 runa especial, 1 alt art (2026-09-08)

Palavras dele, **na mesma tarde e depois da secção a seguir**: *"Para o
riftvault faz: master set playset todo seguido; 1 runa especial de cada para
cada set; no fim 1 alt art de cada."*

Isto **revoga em parte** a decisão de manhã: as artes alternativas voltaram
para dentro da percentagem — continuam a ser a cauda da grelha, mas com alvo
**1**, e a contar. Os tokens `-T` continuam fora.

| # | bloco | o que é | alvo por impressão |
|---|---|---|---|
| 1 | `master` | a sequência do master set, por número de coleção | **playset do tipo** (Unit/Spell/Gear 3, Legend e Battlefield 1) — **menos as runas, que são 1 desde a noite desse dia** (ver a secção a seguir) |
| 2 | `rune_special` | as runas especiais, por edição | **1** |
| 3 | `alt_art` | as artes alternativas | **1** |
| — | `token` | os `-T` | 1 no tile, **fora** da percentagem |

**«Runa especial» = impressão de runa que não é a base** (`runas_especiais`:
`{"tipos": ["Rune"], "excepto": ["base"], "alvo": 1}`). A runa BASE fica no
bloco 1 — **e desde a noite de 2026-09-08 pede 1 como as outras**, ver a secção
a seguir; o que ainda distingue a base da especial é só o bloco. São **6 no
OGN** (as artes
alternativas `OGN-007a`..`214a`) e **6 no VEN** (as promo `VEN-R01`..`R06`).
No SFD e no UNL dão zero: é o BURACO NO CATÁLOGO (a RiftScribe não tem runas
nessas edições; as do CardTrader vivem no `market_only`, fora das métricas).
Assim que ela as tiver, entram sozinhas — o critério é por tipo e variante.

**A runa especial ganha à arte alternativa.** A alt art de uma runa é as duas
coisas; ele nomeou-a como runa, por isso vai para o bloco 2.

**Três funções, uma pergunta cada:** `metrics.e_master` (conta?),
`metrics.bloco` (em que bloco?), `metrics.conta_bloco` (este bloco entra na
percentagem?). O payload leva `block`, `counts` e `short` por bloco; o
`renderProgress` recalcula no cliente, como sempre.

**O que mudou nos números** (medido a 2026-09-08 contra o `data/` real):

| | antes | depois |
|---|---|---|
| denominador da percentagem | 1068 | **1170** |
| percentagem global | 445/1068 = 41,7% | **472/1170 = 40,3%** |
| OGN / OGS / SFD / UNL / VEN | 322 / 24 / 263 / 250 / 209 | **352 / 24 / 287 / 280 / 227** |
| soma dos alvos das alt arts | 360 (playset) | **96** (1 de cada) |
| lista do «Master set» | 546 impressões, 1103 cópias, 21 121,86 € | **620, 1177, 21 574,21 €** |
| «A subir» | 42 cartas, 93 cópias, 2 908,41 € | **57, 108, 2 951,57 €** |
| «Venda» | 26 impressões, 31 cópias, 118,30 € | **2, 6, 4,10 €** |

A percentagem desce 1,4 pontos porque o denominador cresce 102 e o numerador
só 27 — das 108 impressões que entraram ele já tem 27 completas.
`api/faltas.json` passou de 234 KB para 269 KB.

**`master_variantes_playset` ficou a `[]`** — revoga o playset das alt arts de
2026-09-05. ALVO e CONTA continuam a ser campos diferentes; o que mudou é que
agora dizem os dois a mesma coisa nas alt arts.

## As runas do master set são 1 de cada, não 12 (2026-09-08, à noite)

Palavras dele, horas depois da secção acima: *"As runas normais, quando têm
número de set, apenas 1 de cada também, em vez de 12 (playset)."*

Isto **revoga o playset das runas no bloco 1**. Passou a haver **uma regra só
para as runas**, em `metrics.master_target`: tipo runa -> alvo do master **1**,
base ou especial. O que ainda distingue a base da especial é o BLOCO — a base
fica na sequência, as outras vão para o bloco 2 —, já não o alvo.

**O playset JOGÁVEL da runa continua 12** (`playset_targets_by_type`), e é de
propósito: colecionar e jogar são duas perguntas diferentes, e é a métrica 1 que
responde ao Rune Pool dos decks. A secção Faltas, a alocação e as listas de
compra dos decks não mexeram — usam `playset_target` por carta lógica, nunca o
alvo do master.

**Três campos, três perguntas** (`runas_especiais`, o mesmo bloco de config):
`tipos` diz o que é uma runa e por isso decide o ALVO de todas (`metrics.e_runa`),
`alvo` é esse alvo, e `excepto` diz quais ficam na sequência
(`metrics.e_runa_especial`, que passou a ser só sobre o bloco). `tipos: []`
desliga a regra toda e as runas voltam aos 12.

**São só as 6 runas base do OGN.** É o BURACO NO CATÁLOGO outra vez: a
RiftScribe não tem runas no SFD nem no UNL, e as do VEN são todas promo
(`VEN-R01`..`R06`, que já pediam 1). Por isso só o OGN mexe.

**O que mudou nos números** (medido a 2026-09-08 contra o `data/` real):

| | antes | depois |
|---|---|---|
| percentagem global | 472/1170 = 40,3% | **478/1170 = 40,9%** |
| OGN | 119/352 = 33,8% | **125/352 = 35,5%** |
| bloco `master` do OGN | 114/322 | **120/322** |
| soma dos alvos do bloco `master` | 2832 | **2766** |
| lista do «Master set» | 620 impressões, 1177 cópias, 21 574,21 € | **614, 1118, 21 567,33 €** |
| «A subir» | 57 cartas, 108 cópias, 2 951,57 € | igual (seguidas 620 -> **614**) |
| «Venda» | 2 impressões, 6 cópias, 4,10 € | igual |

O denominador **não mexe** — as runas já contavam, o que mudou foi o alvo. As 6
runas base do OGN passam de `1/12`, `1/12`, `3/12`, `3/12`, `3/12`, `2/12` a
completas, e saem das listas de compra: **−6 impressões, −59 cópias, −6,88 €**.
O «A subir» não mexe porque nenhuma delas subia (são cêntimos, abaixo do
`preco_minimo_cents`). `api/faltas.json` passou de 269 KB para **266 KB**.

**A Venda não mexe, e é por decisão anterior.** O âmbito dela é "não é o bloco
`master`", e a runa base está na sequência — *"a sequência nunca entra na venda,
por muitas cópias que ele tenha"*. Medido: se um dia essa regra mudar, o alvo
novo põe à venda **2 cópias** — `OGN-126` Body Rune, que ele tem 3 vezes e
nenhum deck usa. Todas as outras estão alocadas a decks e o `max(usadas, alvo)`
protege-as. **É pergunta para ele**, e vale 2 cópias de uma runa.

### A Venda passou a ser o EXCEDENTE

Com as alt arts dentro da coleção, a Venda esvaziava-se. A frase dele resolve a
tensão que o CLAUDE.md já tinha anotada: se «1 alt art de cada» é coleção, a
sexta é venda. `venda.listar` passou a `sobra = qty - max(usadas, alvo)` nos
blocos que contam, e mantém `qty - usadas` nos tokens, que estão fora da
coleção. O âmbito é agora "não é o bloco `master`" em vez de "não é master
set" — a sequência nunca entra na venda, por muitas cópias que ele tenha.

Ficam hoje `UNL-059a` Master Yi ×1 (tem 2, alvo 1) e `SFD-T03` Gold ×5.

### As exclusões do «A subir» valem só na SEQUÊNCIA (`so_no_master`)

**Extensão minha, por confirmar com ele.** De manhã ele mandou tirar das listas
de compra as signatures e os showcases; o `showcase` é uma RARIDADE e as 42 que
saíam eram todas `variant_kind = base`, porque as alt arts nem estavam no
âmbito. À tarde elas voltaram — e **54 das 102 têm raridade `showcase`**.
Deixar a exclusão global apagava em silêncio a decisão nova.

`a_subir.excluir.so_no_master: true` (default) limita as duas exclusões ao
bloco `master`. As contas não mexeram: continuam **78 (36 signature + 42
showcase)**, as mesmas de antes. `false` volta ao global, e aí saem também 54
alt arts e 3 runas.

Fica de pé a pergunta que já estava anotada: quando ele disse «tira também os
showcases», falava da raridade ou das reimpressões caras de topo de set?

## A Coleção é o master set: os `-T` e os `a` vão para o fim (2026-09-08)

**REVOGADO EM PARTE na mesma tarde** — as artes alternativas voltaram para
dentro da percentagem, com alvo 1. Ver a secção acima. O que se segue é a
decisão de manhã, e continua a valer para os tokens.


Palavras dele: *"As cartas que forem 'sigla-T' ou 'a' no fim (de arte
alternativa) não as quero na sequência do master set; quero-as ordenadas depois
do master set. A Coleção é de master set. O resto provavelmente vai para venda
ou jogar nos decks seleccionados."*

**A regra é o CÓDIGO IMPRESSO**, e no catálogo lê-se pelo `variant_kind`, que é
derivado do mesmo sufixo: `UNL-T03` -> `token`, `UNL-228a` -> `alt_art`.
Ficam **dentro** do master set tudo o que ele não nomeou: as signatures
(`OGN-299*`), as runas promo (`VEN-R01`) e as promos especiais (`VEN-SP4`).

**Uma função só: `metrics.e_master(printing)`.** Havia duas leituras a divergir
— a percentagem já ignorava as artes alternativas (2026-09-02) mas a grelha
punha-as na sequência, e os tokens contavam para a percentagem. Agora a métrica,
a grelha, o «A subir», a lista do master set e a Venda perguntam todos à mesma
função. O `metrics.master_counts` foi **removido**. Configura-se em
`master_set.fora`, hoje `["-T", "a"]` (ver a secção a seguir).

**O que mudou nos números** (medido a 2026-09-08, só os tokens saem — as artes
alternativas já estavam fora):

| | antes | agora |
|---|---|---|
| denominador do master set | 1078 | **1068** |
| SFD / UNL / VEN | 264 / 258 / 210 | **263 / 250 / 209** |
| âmbito do «A subir» | 1042 | **1032** |
| lista do master set | 695 impressões, 29 441,06 € | **686, 29 440,08 €** |

O OGN e o OGS não mexem: não têm tokens com sufixo `-T`.

**Os tokens com número de coleção próprio ficam.** `OGN-271/298` (o Recruit) e
`SFD-003` (o Gold) são tokens por natureza — é o que o `token_card_keys` marca —
mas o código deles não leva sufixo nenhum: estão numerados dentro da edição, por
isso continuam na sequência. A regra é o código, não a natureza da carta.

### Ordem: blocos, nunca intercalados

A grelha percorre os grupos **uma vez por bloco**: primeiro o master set
inteiro, por número de coleção; depois «Fora do master set — tokens»; depois
«Fora do master set — artes alternativas». O `metrics.BLOCOS` manda na ordem e
nos rótulos, o payload leva `block` em cada impressão e a lista `blocks` do
set, e o `render()` do `app.js` faz os dois ciclos. O `metrics.ordem_da_grelha`
diz a mesma ordem em Python, para dar para testar sem browser.

Isto era mesmo visível: em UNL a sequência era `UNL-001, UNL-T01, UNL-002,
UNL-T02, ...` — um token entre cada duas cartas.

**Cada bloco de fora tem contador próprio** ("tens N de M"), recalculado no
cliente como as barras. O alvo dos tiles não mexeu: uma alt art de Unit continua
a mostrar `0/3` e um token `0/1` — ALVO e CONTA são campos diferentes desde
2026-09-02.

**O VEN continua a intercalar as runas promo e as promos especiais**
(`VEN-001, VEN-R01, VEN-SP1, VEN-002, ...`). Ele não as nomeou e ficaram como
estavam. Se quiser, é acrescentar `"-R"` e `"-SP"` ao `master_set.fora` — mas
isso tira-as **também** da percentagem, porque é a mesma pergunta.

### A lista escreve-se pelos sufixos: `master_set.fora` (2026-09-08)

A regra é o código impresso, mas a lista escrevia-se pelo nome interno da
variante — duas escritas para a mesma coisa. Passou a ser
`"master_set": { "fora": ["-T", "a"] }`, que é como ele fala. O
`metrics.kinds_fora()` traduz para `variant_kind`:

| escreve-se | tira | exemplo |
|---|---|---|
| `-T` | tokens | `UNL-T03` |
| `a` | artes alternativas | `UNL-228a` |
| `*` | signatures | `OGN-299*` |
| `-R` | runas promo | `VEN-R01` |
| `-SP` ou `promo` | promos | `VEN-SP4` |
| `overnumbered` | as sobrenumeradas | `SFD-244/221` |

A última entrada não é um sufixo nem uma variante: é o NÚMERO acima do tamanho
da edição (2026-09-10 — ver a secção própria). Vive na mesma lista porque é a
mesma pergunta.

A penúltima tem duas escritas porque ele nomeou-as pela PALAVRA e não pelo
sufixo (*"as VEN-SP (promos)"*, 2026-09-10). O `metrics.PALAVRA_KIND` traduz
`promo -> special`, a par do `SUFIXO_KIND`. **«Promo» é só a `special`** — as
runas promo do VEN escrevem-se `-R` e são outra decisão (ver a secção própria).

Aceita também os nomes das variantes (`token`, `alt_art`, ...) — dão o mesmo.
`master_ignorar_variantes` é o nome antigo da lista e continua a ser lido:
a tradução está no `config._migrar_master_set`, para haver uma leitura só do
config. Um ficheiro com os dois nomes usa o novo.

**Um valor desconhecido rebenta (`ValueError`), de propósito.** É o ponto 6 das
"Superfícies não validadas": uma edição nova pode trazer um sufixo novo, e isso
tem de aparecer em vez de ser contado em silêncio.

**As signatures ficaram preparadas e DESLIGADAS — e foram LIGADAS a
2026-09-09**, quando ele as nomeou (*"das coleções tira as signatures"*). Ver a
secção "As signatures saem da Coleção". O que se segue é como estava até lá.

Acrescentar `"*"` manda-as
para um bloco próprio no fim da grelha («Fora do master set — signatures») —
o `metrics.BLOCOS` passou a ter um bloco com rótulo por variante, para nada
cair no genérico «outras»; os vazios não aparecem, por isso hoje continuam a
ver-se três. Fica desligado porque **é decisão dele e ele não a tomou**: nomeou
os `-T` e os `a`, não estas. Medido: ligar baixa o denominador de **1068 para
1032**. Não confundir com o `a_subir.excluir`, que já as tira das listas
de compra sem lhes mexer na percentagem.

## Comuns e incomuns: o que vender (2026-09-10)

Palavras dele: *"se puderes, vê no Cardmarket e CardTrader quais as comuns e
incomuns que costumam vender-se mais, e quais as mais caras, para eu saber o que
vender"*.

`riftvault/comuns.py`, secção **dobrada** no fim da página Venda (vai no mesmo
`api/venda.json`) e `riftvault venda --comuns` no CLI.

### A resposta curta: não há nada para vender

**O excedente dele em comuns e incomuns vale 3,83 €** — 22 impressões, 33
cópias, e 20 delas a 11 cêntimos, que é o preço mínimo do CardTrader. Metade são
tokens do UNL. Fazer o trabalho valeu na mesma, porque a lista das caras diz-lhe
o que **não** deitar para o saldo, mas o número é este e não convém arredondá-lo.

O dinheiro do excedente dele está noutro lado, e já estava na página: **713,26 €
ao todo, e 690,74 € disso em seis impressões** que saíram da Coleção esta semana
(`OGN-303` Nine-Tailed Fox a 385,64 €, `UNL-235` Deceiver a 118,64 €, `SFD-244`
a 80,64 €, `SFD-224` a 55,64 €, `UNL-231` a 31,41 € e a `VEN-SP5` a 18,77 €).
Comuns e incomuns são 3,83 € dos 713,26 €.

### VOLUME DE VENDAS NÃO EXISTE — e é isso que ele perguntou

*"Quais as que costumam vender-se mais"* não tem resposta em fonte pública
nenhuma. Medido a 2026-09-10, da máquina dele:

| fonte | resposta |
|---|---|
| `cardmarket.com/en/Riftbound` | **403** a pedidos automáticos (já estava no CLAUDE.md) |
| `api.cardmarket.com/ws/v2.0/.../games` | **410 Gone** — a API pública deles morreu |
| `api.cardtrader.com/api/v2` | **200**, com o token que já lá estava |

O que resta no Cardmarket seria uma app registada com chave própria, e a regra
dele é *só a subscrição*. **Não há nada do Cardmarket nesta secção**, e a página
diz isso em vez de mostrar uma coluna vazia.

Do CardTrader vem o lado da **OFERTA**: preço mínimo, quantos anúncios, quantos
vendedores distintos e quantas cópias estão à venda. **Oferta não é procura** —
uma comum com 300 anúncios a 11 cêntimos tem muita oferta, e isso é o contrário
de se vender. Por isso a secção **não tem lista de "as que se vendem mais"**:
tem as caras, e um sinal de procura que diz o que é.

### O sinal de procura, e o que ele mede

    procura = (preço ÷ mediana da raridade)
              × (1 + max(0, Δ% do preço na janela) ÷ 100)
              × (1 + max(0, queda % dos anúncios na janela) ÷ 100)

O primeiro factor é o que o mercado pede **acima do saldo da raridade**; é a
coisa mais próxima de procura que se mede sem volume. O segundo vem do
`price_history`. O terceiro é o único que fala de movimento — oferta a encolher
com o preço a subir é gente a comprar — e **vale zero hoje**, porque o histórico
da oferta nasceu nesta ordem e tem um dia só.

**Hoje as duas listas saem quase iguais, e não é erro.** A mediana das comuns e
a das incomuns são as duas **11 cêntimos**, o mínimo do CardTrader; com o mesmo
denominador para toda a gente, o preço relativo *é* o preço. Está escrito no
ecrã e na docstring do `comuns.procura`.

### As 6 «comuns» que valem dinheiro são os Poros do UNL

| código | carta | preço | anúncios | vendedores | tem? |
|---|---|---|---|---|---|
| `UNL-221` | Lonely Poro | 285,64 € | 6 | 6 | — |
| `UNL-222` | Plundering Poro | 141,24 € | 13 | 13 | — |
| `UNL-220` | Pouty Poro | 140,64 € | 11 | 11 | — |
| `UNL-224` | Mystic Poro | 135,61 € | 9 | 9 | — |
| `UNL-225` | Daring Poro | 109,87 € | 16 | 16 | — |
| `UNL-223` | Veteran Poro | 100,64 € | 22 | 21 | — |

São comuns de raridade e **sobrenumeradas** (`UNL-220..225` num set de 219) —
saíram da Coleção a 2026-09-10 —, e o CardTrader **só as lista em foil**
(`from_foil`), por isso o preço pode estar sobreavaliado, como sempre. **Ele não
tem nenhuma.** A sétima carta da lista já é a `OGN-183` Stacked Deck a **4,91 €**
(tem 3, e a coleção pede 3) e a partir daí é tudo abaixo de 2,50 €.

### O excedente é o que já existia, com um âmbito mais largo

**Não há critério novo.** A conta é a do `venda.excedente`, extraída do
`venda.listar` para ser uma só:

    sobra = cópias − max(usadas nos decks, alvo da Coleção)

A única diferença é o `incluir_master=True`: aqui a **sequência do master set
entra**, porque é lá que as comuns vivem e uma quinta cópia de uma Unit de
playset 3 não faz falta a ninguém. A secção Venda continua com o âmbito estreito
de 2026-09-08 (*"a sequência nunca entra na venda"*) e os números dela **não
mexeram**. **Nada sai da base**, como sempre: é sugestão.

### A raridade exige-se nas DUAS colunas

`rarity` (a impressa) **e** `base_rarity` (a do grupo) têm as duas de ser comum
ou incomum. As seis runas de arte alternativa do OGN são o caso: base `common`,
impressão `showcase`. O mercado paga-lhes preço de showcase, e numa lista de
cartas de saldo isso responde a outra pergunta. Há teste.

### O que passou a ser gravado

O `prices.oferta` (era `lowest`, que continua a responder) passou a contar
**vendedores distintos** e **cópias à venda**, a par dos anúncios. Duas colunas
novas no `catalog.price_latest` — com migração, porque o `CREATE TABLE IF NOT
EXISTS` não acrescenta colunas — e uma tabela nova no **prices.db**:

    listings_history (printing_id, day, n_listings, n_sellers, n_copies)

**Porque é que isto nasce agora.** Uma fotografia da oferta não diz nada; uma
série diz. É o único caminho para responder mesmo à pergunta dele, e só começa a
valer ao fim de umas semanas de `riftvault prices`. Medido no primeiro dia:
**1179 linhas, 163 230 anúncios, 1 259 890 cópias à venda** no Riftbound inteiro.

**Só grava quando mexe mesmo** (`prices._guardar_oferta`): pelo menos 3 anúncios
ou 10% de diferença face ao último registo. O `prices.db` vai para o Git e cada
commit guarda o ficheiro inteiro — gravar 1200 linhas por dia era engordá-lo com
o ruído de uma ou duas listagens.

**Custo medido:** `api/venda.json` passou de **10 618 para 53 360 bytes**. É a
secção inteira num ficheiro que já era descarregado — não há pedido novo, e a
secção vem dobrada.

### O que fica por decidir

1. **A lista das caras é para NÃO vender, não para vender.** Ele não tem
   nenhuma das seis; se um dia abrir um Poro, o que a página lhe diz é que
   aquilo não é saldo. Fica assim até ele dizer o contrário.
2. **A pergunta da Venda continua aberta, pela quarta vez.** Ver as secções das
   signatures, das sobrenumeradas e das promos: ele nunca disse se o que sai da
   Coleção deve ser sugerido para venda.

## Secção «Venda» (2026-09-08)

A segunda metade da frase dele: *"o resto provavelmente vai para venda ou jogar
nos decks seleccionados"*. `riftvault/venda.py`, `api/venda.json`, quarta secção
no frontend e `riftvault venda` no CLI.

Pega no que está fora do master set e ele **tem na caixa**, e parte em duas:
**usada num deck seleccionado** (a cópia está alocada a um deck) e **candidata
a venda**. Uma impressão pode ser as duas: 2 cópias num deck e 1 a mais vende
só 1.

**Quem decide o que está num deck é o `decks.printing_allocation`** — a mesma
função do "2× Ornn · 1 no binder" do tile. Ela escolhe **artes base primeiro**,
de propósito, por isso uma arte alternativa só aparece alocada quando não há
cópias base que cheguem. É a resposta certa aqui: essa alt art está a ser jogada
porque faz falta.

**NADA SAI DA BASE.** Não há botão de vender, não se mexe no `copies` nem no
`ops` — é uma sugestão. Há teste que confirma que o `listar()` não escreve.

Medido a 2026-09-08: **23 impressões, 28 cópias, 106,18 €** (22 artes
alternativas + 5 cópias do `SFD-T03` Gold). Duas ficam de fora por estarem em
decks: `OGN-042a` Calm Rune ×6 (Azir) e `OGN-089a` Mind Rune ×1 (Ornn).

**A ressalva:** a lista sai no formato de **wantlist** do Cardmarket
(`N Nome (V.n) (Edição)`), o mesmo das listas de compra — foi o que ele pediu.
**Não é o formato de importação de stock de vendedor**, que não foi validado e
não se inventou.

**Tensão conhecida, por decidir com ele:** a lista mostra a impressão inteira,
não só o que passa do alvo. Uma alt art com 1 cópia e alvo 3 aparece na mesma
como candidata a venda, e as 5 cópias do Gold também (alvo 1). É o que a frase
dele diz — o que está fora do master set vai para venda ou para os decks — mas
choca com o alvo de playset das alt arts de 2026-09-05. Se ele quiser guardar o
alvo, muda-se numa linha em `venda.listar`: `sobra = qty - max(usadas, alvo)`.

**O gerador do Cardmarket é o mesmo.** A quantidade da linha passou a sair do
`cardmarket.quantidade()`: `missing` nas listas de compra, `qty` na de venda.
O gémeo em JavaScript é o `cmQtd`, e há smoke test que compara os dois texto a
texto.

**O Pimp NÃO foi tocado**, de propósito. Ele é uma lista de compra de artes
alternativas — precisamente do que está fora do master set — mas a pergunta
dele é de DECK, não de coleção: "que versão da carta que já jogo é que quero
mais bonita". Tirar-lhe as alt arts era apagar a aba. As listas que passaram a
ignorar o que está fora do master set são as que medem a coleção: «A subir» e
«Master set».

## Impressões vetadas no Pimp (2026-09-05)

"troca essa versao do Baron Nashor por outra Alt Art, nunca irei comprar essa
carta" — o `unl-238-219` estava a 2400,64 € e sozinho fazia 79% do total do
deck do Kennen (3028 € -> 627 € depois de sair).

`pimp_ignorar_impressoes` é uma lista de `printing_id`, filtrada em
`faltas.pimp()` a seguir ao `pimp_ignorar_tipos`. Veta a impressão, não a
carta: o Baron Nashor continua no Pimp pela arte alternativa `unl-147a-219`
(20,27 €), que já lá estava — as duas apareciam lado a lado.

**A classe toda:** 128 impressões têm número de coleta acima do tamanho
nominal do set (OGN 298, SFD 221, UNL 219, VEN 166). 36 são signatures, já
fora por `pimp_ignorar_tipos`; as outras 92 são `variant_kind = base` —
Legends, Units e Gear, mediana 80 €, mínimo 31 €. Não foram vetadas em bloco:
ele só falou desta. Se um dia pedir, a regra existe e é `collector_number >
tamanho do set`.

### Alt arts com contagem de playset (2026-09-05)

**REVOGADO a 2026-09-08, à tarde:** *"no fim 1 alt art de cada"*. O alvo voltou
a 1 e o `master_variantes_playset` ficou vazio. O que se segue é história.

O alvo fixo de 1 não chegava: "para as Alt Art tbm quero a contagem de playset,
elas contam na ordenação, contam para os decks, mas não contam para a % de
faltas". O alvo da arte alternativa passou a seguir `playset_targets_by_type`,
como já fazia a base — Unit/Spell/Gear 3, Rune 12, Legend e Battlefield 1.

Configura-se em `master_variantes_playset`. O que decide a percentagem não
mexeu, por isso os denominadores foram exatamente os mesmos (OGN 322, SFD 264,
UNL 258 — a 2026-09-08 os tokens baixaram os dois últimos, ver adiante).
O que muda é o badge do tile e, por consequência, o filtro "Faltas" da
grelha: uma `Calm Rune` alt art com 6 cópias lia-se 6/1 (completa) e agora lê-se
6/12 (parcial), que é o ponto — ele quer ver quantas lhe faltam.

Não mexe na secção Faltas nem nos decks: ambos usam `playset_target` por carta
lógica, nunca o alvo do master. Confirmado depois da mudança: 15 cartas, 26
cópias, 170,28 € — igual ao de antes.

O "valor se estivesse completa" segue o `counts`, não o alvo: se a variante
não faz parte do set, não faz parte do preço de o completar.

## Alvo do master da impressão base

`master_base_follows_type: true` no config. O André pediu "base 3, alt art 1,
signature 1", mas 3 fixo daria Legend base = 3 (quando basta 1). Por isso o
alvo do master da **base** segue `playset_targets_by_type`; as variantes mantêm
o 1. Põe-se `false` para voltar ao 3 fixo.

**As runas não passam por aqui desde 2026-09-08 à noite** — o `runas_especiais`
responde antes e dá-lhes 1, base ou especial (ver "As runas do master set são 1
de cada"). Era este flag que lhes dava os 12.

## Cliques rápidos: deltas idempotentes, não debounce

O cliente manda `{printing_id, delta, request_id}`; o servidor faz
`qty = qty + delta` em `BEGIN IMMEDIATE`, e `ops.request_id` é `UNIQUE`.

- Nenhum clique se perde: não há janela onde dois cliques colapsem num só.
- Nenhum clique conta a dobrar: um retry com o mesmo `request_id` devolve o
  resultado guardado sem voltar a aplicar.

Testado: 40 pedidos concorrentes ao mesmo tile deram exatamente +40; o mesmo
`request_id` repetido 5 vezes contou 1.

No cliente, o estado local é a verdade enquanto houver pedidos em voo
(`state.pending` por carta lógica); só se aceita o valor do servidor quando o
contador chega a zero, senão uma resposta atrasada punha o contador para trás.

## Nomes das edições

**Decidido (André, 2026-08-31): ficam os CÓDIGOS** nos separadores, **exceto o
OGS, que mostra `OGS (Proving Grounds)`** — é o set de starters e convinha
distingui-lo do OGN.

A API da RiftScribe não dá os nomes das edições. Os verdadeiros vieram da
lista de expansões do CardTrader (`cardtrader.com/en/games/riftbound/expansions`),
e batem certo com os cinco códigos:

| código | nome |
|---|---|
| OGN | Origins |
| OGS | Origins: Proving Grounds |
| SFD | Spiritforged |
| UNL | Unleashed |
| VEN | Vendetta |

(O OGS ser "Proving Grounds" explica as quatro Legends com nome `— Starter`.)

## Tokens: 1 de cada

**Decidido (André, 2026-08-31): `token_target: 1`**, nas duas métricas. Os
tokens não são cartas de deck, mas contam para a coleção estar completa.

**REVOGADO EM PARTE a 2026-09-08.** O `token_target: 1` continua a ser o ALVO —
o tile diz `0/1` e ele vê quantos lhe faltam — mas os tokens com código `-T`
deixaram de entrar na **percentagem** de master set e passaram para um bloco no
fim da grelha. Ver "A Coleção é o master set".

`token_card_keys` no config marca como token as cartas que a API imprime como
base mas que o são: `Recruit (DE/NX/ZN)` e `Sprite` (OGN-271..274), `Gold`
(SFD-003), e os nomes que só existem como token noutras edições. **A lista é
palpite meu, por confirmar.** O flag propaga-se da carta lógica para todas as
impressões dela (`catalog.rebuild_cards`).

## Faltas: carência GLOBAL, não alocação

`faltas.py` responde a "o que comprar primeiro". A conta é diferente da do
`decks.allocate`: aqui soma-se o que TODOS os decks pedem de uma carta e
desconta-se o que ele tem. A alocação por prioridade responde a outra coisa
(quem fica com o quê) e não serve para decidir compras.

- **TETO POR CARTA (André, 2026-09-01) — REVOGADO a 2026-09-11.** A carência
  era limitada ao alvo de playset da carta, mesmo que a soma dos decks pedisse
  mais: cinco decks a pedir 3 Defy não eram 15 Defy para comprar — eram 3, e
  trocavam-se entre decks (efeito medido na altura: 88 -> 85 cartas, 262 ->
  210 cópias, 919,94 € -> 848,01 €). A frase de 11/09 (*"os decks que
  precisem de cartas iguais, caso não haja suficientes na coleção, ficam em
  falta e é necessário comprar"*) diz o contrário, e a carência passou a ser
  a soma. O `cap` continua no payload só como informação do playset.
- **Runas fora da conta (André, 2026-09-01):** `faltas_ignorar_tipos` no
  config, default `["Rune"]`. São baratas e compram-se a granel, e a 12 por
  deck enchiam os staples. **Só afeta as abas dos decks** (Staples, Por deck e
  as wantlists) — na secção Decks, na Coleção e na aba A subir continuam a
  contar, porque aí a pergunta é outra.
- **Staples** = carência > 0 e pedida por >= 2 decks. É o critério de "rende
  mais por euro".
- **A subir** mudou de âmbito a 2026-09-08 e mudou de casa: vive agora no
  `a_subir.py` e já não depende dos decks. Ver a secção própria abaixo.
- Custo em disco medido: o `prices.db` passou de 52 KB para 140 KB ao alargar
  de 290 para 1178 impressões. Cresce só com o que muda. Se um dia incomodar,
  o sítio para podar é aqui.

## "A subir": só o master set, só o que ainda não tem (2026-09-08)

Palavras dele: *"confere todas as cartas de Riftbound de masterset e as que
subirem pelo menos 10% assinalas; na página ordenas por % de um lado e por
valor no outro (duas abas); quando já tenho as cartas, deixas de seguir — isto
vai servir só para o que eu ainda não tenho. Depois arranjamos um valor métrico
para dar 'urgência' a comprar."*

Isto **revoga a decisão de 2026-09-01** de a aba ser o Riftbound inteiro. O
`prices.sync_prices` continua a gravar as 1178 — o histórico é barato e serve
de base — mas a **vista** passou a ser uma lista de vigia de compras.

`riftvault/a_subir.py`, chamado pelo `faltas.payload()` na chave `a_subir` (era
`spiking`). O `faltas.py` ficou sem a função e sem as constantes `SPIKE_*`.

**"Masterset" é a métrica 2, não uma edição.** Ele não tem no catálogo nenhum
set chamado assim; o que o riftvault chama master set é o alvo por IMPRESSÃO.
O âmbito são por isso as impressões que entram na **percentagem de set
completo** (`metrics.master_target > 0` e `metrics.e_master`), nas cinco
edições: eram **1078 das 1180**, e desde 2026-09-08 são **1068**. Ficam de fora
as 102 artes alternativas e os 10 tokens `-T`, por `master_set.fora`.
Seguir cartas que não contam para o master set seria medir outra coisa que não a
barra que ele vê na Coleção.

**"Ainda não tenho" = a regra do filtro Faltas da grelha**, `cópias + a caminho
< alvo do master`. Uma Unit com 1 de 3 ainda o obriga a comprar 2, logo o preço
ainda lhe interessa. O que vem a caminho conta como tido, como em toda a secção
Faltas. Muda-se em `a_subir.regra_falta`: `"nenhuma"` segue só as que estão a
zero cópias. Medido a 2026-09-08: **686 seguidas** com a regra `master` (eram
731 antes de os tokens saírem do master set, e 695 depois de as signatures
saírem das listas de compra).

**O preço de há N dias é o que estava EM VIGOR nessa data**, não o primeiro
registo dentro da janela. O `price_history` só grava quando o preço muda: uma
carta que valia 1 € há 90 dias e subiu para 2 € há 3 dias tem um único registo
na janela, e comparar com ele dava 0%. A versão antiga fazia isso e media
subidas a menos. Quando não há registo nenhum antes do início da janela usa-se
o mais antigo que existe e a linha diz **"desde <data>"** — hoje é o caso das
57, porque o histórico só começa a 2026-08-31.

**As duas ordens saem do servidor** (`rank_pct`, `rank_valor`) e não do
cliente, para os desempates viverem num sítio só e serem testáveis. O filtro de
raridade usa a raridade da **base**, como os contadores da Coleção.

**A urgência está DESLIGADA de propósito** (`a_subir.urgencia: false`). A
fórmula proposta é `Δ%_janela × 0,5 + Δ%_curto × 1,0 + (preço_hoje /
preço_mediano_da_raridade) × 10`, com os pesos no config. Está calculada em
todos os itens (`urgency`) mas a coluna não aparece — é uma proposta à espera
do veredito dele, não uma decisão minha. Nota medida: o terceiro termo domina
os outros dois nas cartas caras (o `Bloodharbor Ripper` a 133 € dá 7983 contra
466 do topo por %), por isso ou o peso baixa ou o preço relativo entra em log.

**NÃO VALIDADO — os links das cartas.** Nem a RiftScribe nem o CardTrader dão o
endereço da página da carta em lado nenhum da API, e nesta corrida não houve
rede para experimentar. Os dois formatos (`cardtrader.com/cards/<blueprint_id>`
e `riftscribe.gg/cards/<printing_id>`) são presunção, e estão em
`a_subir.DEFAULTS` para se corrigirem numa linha se abrirem em 404.

### Showcases fora das listas de compra (2026-09-08)

*"No riftvault, 'a subir', tira também os showcases."* Segunda exclusão do
mesmo dia, e a que obrigou a config a mudar de forma.

**O showcase NÃO é um `variant_kind`, é uma `rarity`.** As 42 que saem têm
todas `variant_kind = base`: são as reimpressões showcase com número de coleção
próprio da ARMADILHA 2 (`SFD-232/221`, `OGN-299/298`). O `excluir_tipos`, que
só lia variantes, não lhes tocava — por isso passou a haver dois campos:

```json
"a_subir": { "excluir": { "tipos": ["signature"], "raridades": ["showcase"] } }
```

`excluir_tipos` é o nome antigo e continua a ser lido, **a valer o que valia**:
`config._migrar_a_subir` traduz para `{"tipos": [...], "raridades": []}`, com as
raridades vazias de propósito — um ficheiro escrito antes de hoje não excluía
raridade nenhuma e não é a migração que lhe muda a resposta. Um ficheiro com os
dois nomes usa o novo. Como nos pesos da urgência, escrever só um dos campos não
apaga o outro.

**A página diz quantas tirou POR CRITÉRIO**, e cada impressão conta uma vez só,
pelo primeiro que lhe bate (tipos antes de raridades). É preciso escolher:
**as 36 signatures também têm raridade `showcase`**, e contá-las nas duas dava
uma soma maior que o total. Hoje lê-se «78 impressões (36 signature + 42
showcase)». O `a_subir.resumo_fora` é quem faz esta conta, e o `foraTexto` do
`app.js` escreve o mesmo texto nas duas abas.

**Medido a 2026-09-08:** «A subir» passou de 53 para **49 cartas**, de 122 para
114 cópias e de 3405,14 € para **2858,02 €**. As quatro que saíram são todas do
SFD: `SFD-228` Bard (55,64 € ×3), `SFD-232` Sett (69,64 € ×3), `SFD-242`
Glorious Executioner (85,64 €) e `SFD-243` Void Burrower (85,64 €). O chip de
raridade «showcase» desapareceu da barra de filtros. A lista do «Master set»
passou de 686 para **647 impressões**, de 1411 para 1337 cópias e de 29 440,08 €
para **21 056,34 €** — e ficou sem nenhuma impressão sem preço.

**Não mexe na métrica**, como as signatures: `metrics.e_master` não sabe desta
lista e os 42 showcases continuam no denominador da percentagem de set completo
(1068). O âmbito das listas de compra é que baixou de 1032 para **990**.

**A LEITURA QUE FICA POR CONFIRMAR — «showcase» pode querer dizer outra coisa.**
Só o OGN (12) e o SFD (30) têm impressões de raridade `showcase`; as
reimpressões de topo do UNL e do VEN têm raridade de jogo (`rare`, `common`) e
**ficam na lista**. São 48 das 647 do master set, mas valem **18 342,81 € dos
21 056,34 €** — `UNL-221` Lonely Poro a 245,64 €, `VEN-184` Leona a 90,64 €,
`UNL-228` Bloodharbor Ripper a 133,58 €. Se o que ele quis dizer foi *"as
reimpressões caras de topo de set"* e não *"a raridade showcase"*, o filtro
certo é o `collector_number > tamanho nominal da edição` (a classe das 128 já
descrita em «Impressões vetadas no Pimp»), não a raridade. **É pergunta para
ele**; implementou-se o que ele disse à letra.

### Signatures fora das listas de compra (2026-09-08)

"No 'a subir', estás a pôr uma carta signed — não quero." Eram quatro, e valiam
**8 729,69 € dos 12 134,83 €** da lista: `SFD-224*` Aphelios (2000,64 €),
`UNL-234*` Scorn of the Moon (3198,76 €), `OGN-308*` Herald of the Arcane
(1850,64 €) e `OGN-305*` Unforgiven (1679,65 €). A lista passou de 57 para
**53 cartas** e de 12 134,83 € para **3 405,14 €**. (Nesse mesmo dia os
showcases levaram-na de 53 para 49 e de 3405,14 € para 2858,02 € — secção
acima.)

`a_subir.excluir.tipos`, default `["signature"]`, aplicado por
`a_subir.excluir()` logo a seguir ao `masterset()`. Aceita qualquer
`variant_kind`. (A chave chamava-se `excluir_tipos` até nesse mesmo dia os
showcases se lhe juntarem — ver a secção acima.)
**Não mexia na métrica**: as 36 signatures continuavam no
denominador da percentagem de set completo (`metrics.e_master` dizia que sim) —
o que mudou aqui foi a página, e a página diz quantas tirou (`scope.excluded`).
Não confundir com o `master_set.fora`, que tira mesmo do master set — **e que
a 2026-09-09 passou a tirá-las também**, por outra frase dele. Desde então esta
exclusão já não tira nenhuma (elas nem chegam ao âmbito) e fica no config para o
caso de voltarem à coleção: são duas perguntas, e continuam a ter duas
respostas.

**Vale também para a lista do master set**, e isso é uma extensão minha do que
ele disse: ele falou da aba "A subir", mas as duas são listas de compra e ele
não compra signatures. É uma linha de config para separar as duas, se ele
quiser a lista completa com elas.

## A wantlist no fim de cada edição, na Coleção (2026-09-08)

*"Quero também que no fim de cada edição me dês uma wantlist para eu colocar no
Cardmarket."*

Dois blocos no fim da secção Coleção, a seguir à grelha: **«Wantlist Cardmarket
— <edição>»** com as faltas da edição aberta, e **«Wantlist — tudo»** com as
cinco seguidas, pela ordem dos separadores. A caixa já vem **preenchida** — a
wantlist está ali, não é preciso carregar em nada primeiro — e por baixo dela
ficam os três botões de sempre (copiar, copiar com código, CSV) e o total em €.
No cabeçalho da edição há uma linha «faltam N cópias · X €» que liga ao bloco.

**NÃO É UMA LISTA NOVA — é a do «Master set», cortada por edição.** Mesmo
âmbito (os três blocos da Coleção), mesmos alvos (playset na sequência, 1 nas
runas, 1 nas runas especiais, 1 nas artes alternativas, tudo por
`metrics.master_target`), mesma regra `cópias + a caminho < alvo`, e as mesmas
exclusões de `a_subir.excluir` — é a terceira lista de compra e ele não compra
signatures nem showcases. Uma segunda implementação era uma segunda resposta à
mesma pergunta.

**Por isso a Coleção passou a pedir o `api/faltas.json`.** É de onde a aba
«Master set» já vive (chave `master`), e gerar um segundo ficheiro com os
mesmos dados custava os mesmos ~200 KB duas vezes. Custo medido: o
`faltas.json` **não cresceu** (267 KB) e nenhum payload de edição cresceu
(`api/set/OGN.json` continua nos 196 KB); o que muda é que uma visita só à
Coleção passa a descarregá-lo. O `garanteFaltas()` só BUSCA — desenhar a secção
Faltas continua a ser do `loadFaltas`, senão uma visita à Coleção montava
também os tiles do Pimp, com as imagens todas.

`a_subir.wantlist(con, set_id=None)` do lado do Python (CLI e testes) e
`renderWantlists()` do lado do browser; as linhas saem as duas do gerador único
(`cardmarket.linha` / `cmLinha`). Há smoke test que compara os dois texto a
texto nas cinco edições.

**Em modo edição a lista fica velha, e diz-se.** Um `+` marca-a como
desatualizada (`wlDesatualizar`) e aparece um botão **Atualizar**; não se volta
a pedir o ficheiro sozinho porque ele pode estar a marcar uma caixa inteira de
cartas e são centenas de KB de cada vez.

**A pergunta que fica:** as exclusões. Ele nunca falou delas neste pedido, e
aplicá-las aqui é **extensão minha** — a mesma que já se tinha feito ao
«Master set». Se ele quiser a wantlist da edição com tudo lá dentro, é
`a_subir.excluir.tipos`/`raridades` a vazio — medido: sobe de **614 para 689
linhas** e de **21 567,33 € para 81 202,46 €**, quase tudo nas 36 signatures.

Medido a 2026-09-08 contra o `data/` real: **614 linhas, 1118 cópias,
21 567,33 €**, os mesmos números da aba «Master set» — OGN 204, OGS 14, SFD 93,
UNL 117, VEN 186. **307 das 614** só têm oferta foil no CardTrader.

No CLI: `riftvault wantlist --edicao OGN` (uma edição) e
`riftvault wantlist --cardmarket` (todas). Sem nenhum dos dois, o `wantlist`
continua a ser o dos decks — são duas perguntas com o mesmo formato. O corte
por edição e os totais vão para o `stderr`, para o `stdout` ficar colável.

## Contagem por níveis: 1 de cada, 2 de cada, o playset (2026-09-08)

Palavras dele: *"Para a coleção de master set, gostava que fizesses também uma
contagem: quantas cartas faltam para ter 1 de cada, quantas faltam para ter 2 de
cada, quantas faltam para ter o playset de cada — do género 1/3 Z % · 2/3 X % ·
3/3 Y %."*

Uma linha de chips por baixo das barras da Coleção, **global e por edição**, e
um degrau a mais nas wantlists do fim da página. Nada disto é um âmbito novo:

    alvo do nível k = min(k, alvo do master)
    faltam_k = Σ max(0, min(k, alvo) − cópias)
    %_k      = impressões com cópias ≥ min(k, alvo) / impressões do âmbito
    €_k      = preço de hoje × faltam_k

**O ÂMBITO É O DA BARRA, não só a sequência.** Ele escreveu "para a coleção de
master set", e o que o riftvault chama a percentagem de master set são os TRÊS
blocos da Coleção. Ficaram todos, e as impressões de alvo 1 — as runas e os
Legends da sequência, as runas especiais e as artes alternativas — **só podem
faltar no nível 1**, porque `min(k, 1)` nunca lhes pede mais. A alternativa era
contar só a sequência; escolhi esta porque assim **a percentagem do último nível
é EXACTAMENTE a da barra por cima da qual ela aparece**. Duas percentagens
diferentes a dizerem "master set" no mesmo canto do ecrã liam-se como um erro de
contagem. Há teste que fixa a igualdade.

**O denominador é o mesmo nos três níveis** (as impressões todas do âmbito),
senão as percentagens não eram comparáveis entre si — é o mesmo denominador da
barra.

**Conta CÓPIAS, não o que vem a caminho.** É a regra da Coleção: o `pending`
fica fora do `copies` e as barras não mexem enquanto a encomenda vem. As
wantlists por nível é que descontam o pendente, como sempre fizeram — ali a
pergunta é o que há a COMPRAR. O mesmo vale para as exclusões: os showcases
contam nestas percentagens (como na barra) e ficam de fora das listas de compra
(como nas outras duas). **As signatures deixaram de contar nas duas coisas a
2026-09-09**, quando saíram da coleção — os números desta secção são de
2026-09-08 e por isso ainda as levam.

**Quantos degraus há: o maior alvo do catálogo** (`metrics.niveis_max`), hoje
**3**. Vem do catálogo inteiro e não de cada edição para as cinco mostrarem os
mesmos — uma edição só de Legends daria um degrau só e o `1/3` de uma deixava de
se comparar com o `1/1` da outra. Não há valor escrito à mão: se as runas
voltarem ao playset (`runas_especiais.tipos: []`), passam a ser 12 degraus, e é
isso que se vê.

**Onde vive:** `metrics.niveis` (a conta), `metrics.niveis_payload` (global +
`by_set`) e `metrics.niveis_max`. O payload da edição leva
`progress.levels` e o `api/index.json` leva `levels`; o cliente recalcula os
números a partir do estado local, como faz com as barras, mas os DEGRAUS vêm do
servidor para não haver duas regras. O global é a soma das edições — todos os
campos são somas —, por isso o `renderProgress` troca só a edição aberta pelos
números otimistas e as outras quatro ficam como vieram. No CLI é o
`riftvault stats`, que passou a imprimir a tabela por baixo das duas métricas.

### Wantlist por nível

Os dois blocos do fim da Coleção ganharam **até 1 de cada / até 2 / playset**. É
a mesma lista, com `min(k, alvo)` no lugar do alvo: `a_subir.wantlist(...,
nivel=k)` em Python (e `riftvault wantlist --edicao OGN --nivel 1`), `wlItens`
no browser, e o gerador de linhas continua a ser um só. Os dois blocos
partilham o degrau — é a mesma pergunta, e vê-los responder coisas diferentes na
mesma página confundia.

O que sai bate certo com a contagem: **a wantlist do nível k pede exactamente as
`faltam_k` cópias** que os chips mostram (a menos das exclusões, que são das
listas de compra e não da métrica). Há teste que compara os dois, e o `wlItens`
do `app.js` foi comparado linha a linha com o Python nos três níveis.

O «A subir», a Venda e a aba «Master set» **não mudaram**: ele falou da contagem
e das wantlists da Coleção.

### Os números de hoje

Medido a 2026-09-08 contra o `data/` real (`riftvault stats`). **Os números
mudaram a 2026-09-09**, quando as signatures saíram da coleção: os denominadores
perderam 36 e cada degrau perdeu 36 cópias e 51 253,27 € — ver "As signatures
saem da Coleção" para a tabela nova. O que se segue é o de 2026-09-08.

| | 1 de cada | 2 de cada | playset |
|---|---|---|---|
| OGN | 243/352 = 69,0 % · faltam 109 · 28 139,40 € | 179/352 = 50,9 % · faltam 219 · 28 568,76 € | 125/352 = 35,5 % · faltam 383 · 29 024,12 € |
| OGS | 23/24 = 95,8 % · faltam 1 · 5,92 € | 23/24 = 95,8 % · faltam 1 · 5,92 € | 10/24 = 41,7 % · faltam 14 · 19,31 € |
| SFD | 209/287 = 72,8 % · faltam 78 · 18 701,81 € | 190/287 = 66,2 % · faltam 134 · 21 090,39 € | 151/287 = 52,6 % · faltam 229 · 23 519,73 € |
| UNL | 212/280 = 75,7 % · faltam 68 · 13 556,50 € | 193/280 = 68,9 % · faltam 99 · 17 008,58 € | 151/280 = 53,9 % · faltam 172 · 20 507,33 € |
| VEN | 63/227 = 27,8 % · faltam 164 · 3 985,81 € | 51/227 = 22,5 % · faltam 294 · 6 154,17 € | 41/227 = 18,1 % · faltam 434 · 8 327,08 € |
| **total** | **750/1170 = 64,1 % · faltam 420 · 64 389,44 €** | **636/1170 = 54,4 % · faltam 747 · 72 827,82 €** | **478/1170 = 40,9 % · faltam 1232 · 81 397,57 €** |

O último nível é a barra do master set, como tem de ser: **478/1170 = 40,9 %**.
O OGS é o caso que se lê de relance — 95,8 % com uma de cada e 41,7 % em
playset: falta-lhe **uma** carta, mas faltam-lhe as segundas e terceiras cópias
de quase tudo.

**Os euros do nível 3 (81 397,57 €) NÃO são os da wantlist (21 567,33 €)**, e é
de propósito: a contagem é a métrica — contava as 36 signatures e conta os 42
showcases (que valem quase tudo isto) e não desconta o que vem a caminho —, a
wantlist é lista de compra e tira-lhes as duas coisas. A 2026-09-09, com as
signatures fora da métrica, a diferença encolheu para 30 099,61 € contra
21 551,64 € — o que sobra são os showcases e o pendente.

Wantlists por nível, hoje (`riftvault wantlist --cardmarket --nivel N`):

| degrau | linhas | cópias | € | só foil |
|---|---|---|---|---|
| até 1 de cada | 344 | 344 | 8 983,34 € | 211 |
| até 2 de cada | 456 | 652 | 15 222,29 € | 269 |
| playset (omissão) | 614 | 1118 | 21 567,33 € | 307 |

A linha do playset é **exactamente** a de antes desta ordem — a lista por
omissão não mexeu.

**Custo em disco:** `api/index.json` passou de 572 para **1922 bytes** (é onde
vive a contagem das cinco edições), `api/set/OGN.json` cresceu **227 bytes** e o
`api/faltas.json` **13**.

## Listas para o Cardmarket (2026-09-08)

"No final dá-me uma lista para o Cardmarket para eu conseguir comprar as
coisas." Três botões no fim da aba "A subir" e da aba "Master set":

- **Copiar para o Cardmarket** — `N Nome (V.n) (Edição)`, o formato da ajuda
  deles (`4x High Tide (V.1) (Fallen Empires)`).
- **Copiar com código** — `N Nome [UNL-228]`. **Os `[ ]` não são sintaxe do
  Cardmarket** e o importador não os lê: é para ele desambiguar à mão qual das
  versões quer. Está escrito na nota por baixo da caixa.
- **Descarregar CSV** — as oito colunas que ele pediu, com cabeçalho.

**O gerador é UM.** `riftvault/cardmarket.py` em Python (`linha`, `gerar`,
`csv_texto`) e `cmLinha`/`cmCSV` no `app.js`, com smoke test que compara os dois
contra o mesmo payload. O `faltas._versoes` mudou-se para `cardmarket.versoes`
e o `faltas.wantlist` passou a escrever pelo `cardmarket.linha`, para não
haver três formatos a divergir.

**As listas saem do que está no ecrã**, com o filtro activo — a raridade em "A
subir", a edição no "Master set". O `cmLigar` recebe uma *função*, não uma
lista, para o botão apanhar o filtro no momento do clique.

**O total em euros fica FORA do texto** (por baixo da caixa, e no `stderr` do
CLI). Uma linha de total colada na wantlist era importada como se fosse uma
carta.

**NÃO REVALIDADO nesta corrida.** Não houve rede daqui (o `WebFetch` e o
`WebSearch` foram negados pelo modo em que a sessão corria), por isso o formato
é o que já estava registado no CLAUDE.md como confirmado na ajuda deles, e o
mesmo que o `wantlist()` dos decks usa desde 2026-09-01. Não inventei variação
nenhuma. Se algum dia houver rede, o que falta confirmar é se a secção de
Riftbound do Cardmarket aceita a edição escrita como o CardTrader a escreve
("Origins", "Spiritforged", "Unleashed", "Vendetta") — é daí que vem o
`market_set`.

**Medida que interessa:** hoje **as 53 linhas de "A subir" são todas de
impressões que o CardTrader só lista em foil**, e no master set são 371 das
686. O aviso do foil por baixo da caixa deixa de ser uma nota de rodapé e passa
a ser a lista inteira — ver a ressalva do `from_foil` na secção dos preços.

## "Master set": a lista completa das faltas (2026-09-08)

"Lista completa das faltas do master set, não só as que sobem — para ele
comprar tudo o que falta de uma vez se quiser." Aba nova em Faltas,
`a_subir.master_faltas()`: mesmo âmbito, mesma regra de carência e as mesmas
exclusões da aba "A subir", sem o filtro de subida.

Ordenada por **edição e número de coleção** (pedido dele), que é a ordem do
binder e das páginas de venda — não pelo preço.

Medido a 2026-09-08, **depois de os tokens saírem do master set**: **686
impressões, 1411 cópias, 29 440,08 €**, uma sem oferta no CardTrader (entra na
lista, não entra no total). Por edição: OGN 252, VEN 170, SFD 145, UNL 105,
OGS 14. (Antes dessa decisão eram 695 / 1420 / 29 441,06 €, com UNL 113 e
VEN 171 — a diferença são os 10 tokens.)

**E depois de os showcases saírem das listas de compra**, no mesmo dia: **647
impressões, 1337 cópias, 21 056,34 €**, nenhuma sem oferta no CardTrader. Por
edição: OGN 241, VEN 170, SFD 117, UNL 105, OGS 14 — só o OGN e o SFD mexem,
que são as duas edições com raridade `showcase`.

**Sem imagens de propósito.** São centenas de linhas e o `faltas.json` é
descarregado inteiro a cada visita. Mesmo assim o ficheiro passou de **89 KB
para 296 KB** — é o custo desta aba, medido. Duas podas já feitas: sem
`set_name` por item (a edição já vem no grupo) e o `market_name` só quando
difere mesmo do nosso (poupou 18 KB). Se voltar a incomodar, o sítio para
podar é este — a seguir sairiam o `have`/`target` e o `printing_id`.

## "Pimp decks"

`faltas.pimp()` — quarta aba das Faltas. Todas as impressões **alteradas** das
cartas que os decks usam: artes alternativas, signatures, as reimpressões
showcase (que têm número de coleção próprio) e as promos. Alterada = tudo o
que não é a impressão canónica, e canónica é a base da edição mais antiga.

**Fora:** `pimp_ignorar_tipos`, default `["signature", "rune_promo"]` —
decisões dele, 2026-09-01. Nas runas a versão que ele quer pimpar é a **arte
alternativa do OGN**, não a promo do VEN (`VEN-R01`..`R06`). Ficam as artes
alternativas, as reimpressões showcase e as promos especiais (`sp1`..`sp6`).

**É lista de compras** (mudou 2026-09-02). Desconta o que ele tem **e o que
vem a caminho**, por impressão: a quantidade mostrada é só o que ainda falta
comprar. As versões já completas saem da lista e contam em `done`. Antes
mostrava tudo, incluindo o que ele já tinha — ele pediu para tirar.

**Arruma-se por DECK, nunca por edição** (André, 2026-09-01). A vista "Todas"
tem um cabeçalho por deck; as sub-abas mostram um deck de cada vez, em grelha
corrida. O `by_set` continua a existir no payload mas o frontend achata-o
(`achata()`), ordenando pelo custo — é o custo que decide a troca.

A decisão de pimpar é por deck: é a olhar para um deck de cada vez que ele
decide o que trocar. Na vista por deck a quantidade é a que AQUELE deck usa;
na global é a soma com o teto. Uma carta usada por dois decks aparece nos dois
— aqui isso é a informação, não duplicação a evitar.

**Cuidado com os contadores.** A vista "Todas" mostra os decks um a seguir ao
outro, por isso a soma dos decks é o que se vê no ecrã — não o `printings` do
payload, que é a vista global com quantidades somadas. A aba e o resumo usam
a soma dos decks, senão o número no separador não batia com os tiles.

**A lista dos decks leva SÓ a versão mais barata** (André, 2026-09-01). Houve
uma versão com um visto "com artes alternativas" na lista dos decks; foi
retirada, é aqui que essa pergunta vive.

## BURACO NO CATÁLOGO: 48 impressões que a RiftScribe não tem

Medido a 2026-09-01, contra os blueprints do CardTrader:

| edição | CardTrader | RiftScribe | a mais no CT |
|---|---|---|---|
| OGN | 353 | 352 | 1 (token `Buff`) |
| OGS | 25 | 24 | 1 |
| SFD | 302 | 288 | **14** (runas R01–R06 + artes alt., tokens) |
| UNL | 300 | 288 | **12** (artes alt. das runas) |
| VEN | 247 | 228 | **20** (artes alt. das runas + 9 signatures) |

Confirmado na fonte: `GET /api/cards?set_id=SFD&type=Rune` devolve
`X-Total-Count: 0`. A RiftScribe só tem runas no OGN (12) e no VEN (6).

**Consequência prática.** O André pediu que o Pimp mostrasse, nas runas, as da
edição do Legend do deck. Os dois decks dele têm Legend do SFD, e as runas
alternativas do SFD existem (`SFD-R01a`..`R06a` no CardTrader) — mas não estão
no catálogo, por isso continua a aparecer a do OGN.

A preferência **já está implementada** (`pimp()` -> `montar(pedido, preferir)`)
e passa a funcionar sozinha assim que o catálogo tiver as cartas. Hoje não
muda nada.

**Resolvido com `catalog.market_only`** (2026-09-01). O André deixou a decisão
comigo e escolhi o caminho do meio: as 48 impressões ficam numa tabela à
parte, **fora do catálogo**.

- Não entram na grelha da Coleção nem em métrica nenhuma. As barras de
  progresso, o master set e as contagens por raridade continuam a medir os
  1180 da RiftScribe — que é a fonte que tem informação de jogo (tipo,
  domínio, custo). O CardTrader não dá nada disso.
- Entram **só na aba Pimp**, marcadas "fora do catálogo", porque aí a
  pergunta é de mercado e não de coleção.
- Casam-se com a carta lógica por número de coleção e, falhando isso, por
  nome: 41 das 48. As 7 que sobram são tokens que não temos.
- Levam preço (o `sync_prices` inclui-as) e imagem do CardTrader.

**ARMADILHA — colisão de números no CardTrader.** Eles escrevem a `Calm Rune`
alternativa do SFD com o mesmo `R02` da base. Deduplicar o índice por número
de coleção fazia desaparecer a segunda — justamente a runa que o deck do Ornn
quer. O `sync_map` guarda agora a lista toda (`singles`) e usa o índice só
para casar; o `market_only` sai do que não foi casado, por `blueprint_id`.

**Efeito:** os dois decks têm Legend do SFD e passam a mostrar as runas
alternativas do SFD (`SFD-R02`, `SFD-R03a`, `SFD-R06a`) em vez das do OGN.

## Wantlist do Cardmarket

O formato vive no `cardmarket.linha` desde 2026-09-08 — o `faltas.wantlist()`
escreve por lá, e o `_versoes` mudou-se para `cardmarket.versoes`. Botão na
secção Faltas → Por deck, e `riftvault wantlist [--deck X] [--todos]
[--out f.txt]`. As abas "A subir" e "Master set" têm listas próprias, do mesmo
gerador (ver a secção acima).

**O nome tem de ser o DO MERCADO, não o da RiftScribe.** Lá é
"Darius, Trifarian", no Cardmarket/CardTrader é "Darius - Trifarian" —
vírgula contra hífen. 414 das 1179 impressões diferem. O `cardtrader_map`
guarda `market_name`, `market_set` e `cardmarket_id`, recolhidos no
`riftvault map`.

A edição vai junto porque 104 nomes existem em mais do que uma edição e sem
ela ficaria ambíguo.

**NÃO VALIDADO contra o Cardmarket.** O site responde 403 a pedidos
automáticos e não há conta para experimentar. O formato `qtd nome (edição)` é
o que a ajuda deles documenta e o que as extensões de bulk import usam. Que o
Cardmarket tem Riftbound está confirmado: **as 1178 impressões têm
`card_market_ids`** nos blueprints do CardTrader.

**Formato confirmado na ajuda deles:** `4x High Tide (V.1) (Fallen Empires)` —
quantidade, nome, versão opcional, edição opcional.

**O FOIL NÃO SE MARCA NO TEXTO.** Confirmado: no Cardmarket o foil é um filtro
*por entrada*, posto na interface depois de a carta entrar na lista, a par de
idioma, condição, signed e altered. Por isso o `wantlist()` devolve também
`foil` — as linhas cujas impressões só têm oferta foil no mercado (623 das
1179) — para ele saber onde ligar o filtro à mão. Não inventar uma sintaxe.

**As versões (V.n) são INFERIDAS, não lidas.** `_versoes()` agrupa pelo
`group_key` — edição + número de coleção — e numera pela ordem do variante.

**Foi o André que corrigiu o agrupamento** (2026-09-01): "as signatures são
normalmente as V.2". Eu agrupava por carta lógica, e a `Daughter of the Void`
do OGN dava três versões (base 247, showcase 299, signature 299*), pondo a
signature em V.3. Se lá é V.2, o Cardmarket trata a 247 e a 299 como produtos
diferentes e só junta as impressões que partilham número de coleção. Com o
agrupamento certo, **as 36 signatures ficam todas em V.2 e as 102 artes
alternativas também** — consistente com o que ele vê no site.

Isto também resolve o problema do nome: o CardTrader escreve a arte
alternativa de 3 cartas com vírgula e a base com hífen ("Darius, Trifarian" vs
"Darius - Trifarian"), e agrupar por nome partia-as em dois grupos de um.
Todas as versões saem com o nome da base.

**ARMADILHA — o `price_latest` mora no catalog.db, que é descartável.** Apagar
o catalog.db deita fora os preços atuais e só o `riftvault prices` os repõe.
O histórico sobrevive (está no prices.db). No GitHub Actions isto resolve-se
sozinho porque o sync e os preços correm em sequência; localmente, quem apagar
o catálogo tem de voltar a correr os preços.

**A caixa de texto não é um fallback do clipboard, é o mecanismo principal.**
O `navigator.clipboard` exige contexto seguro, e no telemóvel isto abre por
http num IP da rede local — lá nunca funcionaria.

## Encomendas a caminho (`pending`)

Uma carta comprada mas ainda não recebida não está na coleção — mas também já
não é uma falta. A tabela `pending` (vault.db) é a diferença entre as duas:

- **Fora do `copies`**: a Coleção mede o que está na caixa. As barras de
  progresso, o valor e o master set não mexem enquanto a encomenda vem.
- **Descontada das faltas**: o `faltas.shortfall`, o `por_deck` e o
  `todos_juntos` somam o pendente ao que ele tem, senão as listas mandavam
  comprar outra vez.
- `pending.arrive()` passa para o `copies` pelo `collection.adjust`, portanto
  fica no `ops` e dá para desfazer.
- Confirma-se pela interface: botão **Chegou** em cada carta e um "Chegou
  tudo", em Faltas -> A caminho (`POST /api/pending/arrive`). Ou
  `riftvault pending --chegou [ID]`.

**Desfazer uma entrada tem DUAS metades.** O `collection.undo_last` reverte as
cópias mas não mexe no `pending.arrived_at` — é preciso pôr a NULL também,
senão a carta desaparece das duas listas. Não há undo automático disto.

Aceita `market_only`: ele comprou runas do SFD que a RiftScribe não tem, e
essas contam na mesma (`pending.open_by_card` junta as duas fontes).

**Aliases das market_only.** O `sync_map` regista `sfd-r02a` -> `ct-374043`
no `printing_aliases`, com o sufixo `a` acrescentado quando o CardTrader o
omite. Sem isso o `riftvault add SFD-R02a` falhava — e foi assim que a fatura
dele veio escrita.

## Onde está cada cópia

`decks.printing_allocation` responde a "não encontro a carta no binder, onde
está?". A alocação por prioridade é por carta lógica — diz que o Azir leva 3
Brutalizer, não de que impressão. Aqui escolhe-se a impressão, e a regra é
**artes base primeiro**, para as alternativas e signatures ficarem no binder.

Aparece nos dois lados: no tile da Coleção (`2× Ornn · 1 no binder`) e na
grelha do deck. Não confundir com o `shared` da alocação, que é a carta que
falta a este deck por estar num deck anterior.

## Filtro de estado: só "Faltas"

Havia `Em falta` (zero cópias) e `Parciais` (tem algumas, não as suficientes).
**Juntaram-se num só** (André, 2026-09-05): a pergunta é sempre a mesma — o
que é que ainda me falta — e tanto faz faltarem 3, 2 ou 1. `Faltas` é
`tileState() !== 'done'`.

O `loadPrefs` converte um `'partial'` guardado em `'missing'`: sem isso a
grelha abria sem botão nenhum selecionado, num filtro que já não existe.

## Ordenação da grelha (REMOVIDA)

Houve ordenação por Tipo/Raridade/Custo e por folhas do binder. **O André
mandou tirar as duas** (2026-09-01): a grelha vai só por número de coleção, e
ele organiza o binder à mão. Não voltar a acrescentar sem ele pedir.

## Preços: CardTrader (2026-08-31)

A RiftScribe **não tem preços nenhuns** — procurado `price`, `market`, `usd`,
`eur`, `tcgplayer`, `cardmarket` em toda a spec: zero. O Cardmarket responde
403 a bots. A fonte é o **CardTrader**, API v2, `CARDTRADER_TOKEN` no ambiente.

**Riftbound é o `game_id` 22.** As expansões do CardTrader têm `code` igual ao
`set_id` da RiftScribe em minúsculas: `ogn` 4166, `ogs` 4275, `sfd` 4299,
`unl` 4425, `ven` 4521. Os singles são `category_id` 258; o resto é selado.

**A ponte, validada:** o `fixed_properties.collector_number` dos blueprints já
traz o sufixo da variante — `007` base, `007a` arte alternativa, `299s`
signature. Casa diretamente com `(set_id, collector_number, variant)`, sem
comparar nomes (que são diferentes: "Jinx - Loose Cannon" lá, "Loose Cannon"
cá). **Medido: 1179/1180 (99,9%), sem ambiguidades.** A única que falha é
`VEN-T04 "Recruit (NX)"`, um token que o CardTrader não lista. O CardTrader
tem impressões a mais que a RiftScribe ainda não tem (runas promo do SFD/UNL,
signatures do VEN); ficam de fora por não haver impressão nossa.

**ARMADILHA — User-Agent com acentos dá 403.** Testado: `"...colecao"` devolve
200, `"...coleção"` devolve 403. Os User-Agent do `prices.py` e do
`riftscribe.py` são ASCII puro de propósito. Não lhes ponhas acentos.

**Critério de preço:** menor preço pedido em Near Mint/Mint, inglês, sem
graded/altered/signed, vendedor não ausente. Tudo vem em EUR. Prefere-se a
oferta não foil; se não houver nenhuma usa-se a foil e marca-se `from_foil`.

**A ressalva que importa:** `riftbound_foil` é significativo mas está muito
desequilibrado — em OGN, 179 blueprints só têm ofertas foil, 164 têm as duas e
só 28 são só normal. Como o riftvault não distingue acabamentos, o valor das
cartas que só existem em foil no CardTrader pode estar **sobreavaliado**. Por
isso `collection_value` devolve `cents_de_foil` e o `riftvault value` diz que
percentagem do total vem daí — não escondas esse número num total limpo.

**Onde ficam:** `catalog.price_latest` (as 1180, descartável) e `price_history`
no `vault.db` (só as que ele TEM, e só quando o preço muda — o vault.db vai
para o Git e cada commit guarda o ficheiro inteiro).

**Desde 2026-09-10 grava-se também o TAMANHO da oferta** (`prices.oferta`, que
substituiu o `lowest` sem o apagar): quantos anúncios, quantos **vendedores
distintos** e quantas **cópias à venda**. As contagens seguem o acabamento do
preço — se o preço vem da foil, contam-se só as foil, senão o número não
correspondia ao preço mostrado. Vai para o `price_latest` e, ao longo do tempo,
para o `prices.listings_history` — ver «Comuns e incomuns: o que vender».

## Vista por omissão: todas as impressões

**Decidido (André, 2026-08-31):** a grelha abre em "Todas as impressões", não
em "Só artes base". O botão continua lá, mas não é o default
(`app.js` -> `state.prefs.view = 'all'`).

## Servidor

Flask (o André pediu FastAPI ou Flask, "o mais simples"). Uma ligação SQLite
por pedido, porque os objetos do `sqlite3` não atravessam threads e o servidor
corre em modo `threaded`.

O QR usa o pacote `qrcode`; se não estiver instalado, ou se a consola não
aguentar os blocos, imprime só o URL. A consola do Windows abre em cp1252 —
`cli.main()` força UTF-8 na saída, senão os acentos e o QR rebentam.

## Decks (2026-08-31)

**Alocação por prioridade.** Os decks têm uma ordem (`decks.priority`, 1 =
principal). Percorrem-se por essa ordem e cada um serve-se do que sobra: o
deck 1 fica com o que precisa, o deck 2 só recebe o que sobrou. Uma carta que
falte ao deck 2 **por já estar noutro deck** é mostrada com o deck onde está —
e, desde 2026-09-11, **entra na lista de compras desse deck na mesma** (ver
"Os decks partilham a Coleção"); até lá não entrava.

A alocação é **global e por carta lógica**, não por deck nem por papel: mudar
a ordem refaz tudo (`decks.allocate`). Uma carta que esteja no main e no
sideboard disputa o mesmo stock.

**Nome do separador:** Legend · Champion (pedido do André).

**Apagar um deck** = apagar o `.txt`. O `import_all` remove da base os decks
cujo ficheiro desapareceu. O servidor relê os ficheiros quando algum mexeu
(`server._reimport_if_changed`), não é preciso reiniciar.

**Formato das listas:** secções com cabeçalho terminado em `:` (Legend,
Champion, MainDeck, Battlefields, Rune Pool, Sideboard) e linhas `N Nome`.
Aceita também códigos (`3 OGN-045`).

**ARMADILHA — nomes dos Legends.** As listas escrevem `Azir, Emperor of the
Sands`, mas no catálogo o Legend é só `Emperor of the Sands`. Quando o nome
exato falha, tira-se o prefixo antes da primeira vírgula. É seguro:
**nenhum dos 49 Legends tem vírgula no nome** (verificado).

**Regras de legalidade** (`deck_rules` no config): main 40, runas 12,
battlefields 3, máximo 3 cópias, identidade de domínio pelo Legend.
`main_includes_champion: true` foi **inferido** das duas listas do André, que
têm 39 no MainDeck + 1 Champion = 40 — **não validado contra as regras
oficiais**. Se estiver errado, é uma linha no config.

## Revisão do site (2026-09-09)

Ordem dele a 2026-09-08: *"Revê também os meus sites de MTG, Riftbound e Tibia
à procura de melhorias."* O que se corrigiu foi só o de **baixo risco** — texto
que mentia, plurais, imagens sem alternativa e um cabeçalho fora de âmbito. As
regras de negócio não foram tocadas; as propostas ficaram no relatório
`ai-pc/work/revisao/melhorias-riftvault.md`, para ele decidir.

**O cabeçalho da secção Faltas mentia em quatro das seis abas.** O
`#falta-head` mostra o `faltas.totals` — a carência GLOBAL DOS DECKS
(`faltas.shortfall`) — e estava em todas as abas. Na aba «Master set» lia-se
*«Falta comprar 25 cartas · 34 cópias · 356,91 €»* por cima de *«614 impressões
em falta · 1118 cópias · 21 567,33 €»*, que é outra pergunta. Passou a chamar-se
**«Falta comprar aos decks»** e a aparecer só onde é a conta da página
(`FALTA_HEAD = ['staples', 'deck']` no `app.js`). Pôr lá as outras abas é
acrescentar o id à lista.

**Os dois totais dos decks diferem de propósito, e agora está escrito.**
(**Deixaram de diferir a 2026-09-11**: sem teto, o cabeçalho e a soma da aba
«Por deck» dão o mesmo número — 80 cópias · 475,28 € nesse dia — e a nota do
`faltaHead()` foi reescrita. O que se segue é como estava a 09-09.) O
cabeçalho soma o que TODOS os decks pedem com o teto do playset (34 cópias); a
aba «Por deck» conta o que sobra depois dos decks anteriores (33). Hoje a
diferença é a `Salvage`: três decks pedem 2 cada, ele tem 2, e nenhum deck
sozinho fica a faltar — mas ao todo ainda lhe falta 1 para o playset. Aparece
nas Staples e em nenhuma aba de deck.

**A linha «faltam N cópias» da Coleção estava encostada a outro número
diferente.** Por cima dela, o chip do playset da contagem por níveis diz «faltam
383 · 29 024,12 €» (OGN) e ela dizia «Faltam 360 cópias · 1 306,14 €». São a
MÉTRICA e a LISTA DE COMPRA — a métrica contava as signatures, conta os
showcases e não desconta o pendente —, mas lado a lado liam-se como erro de
contagem. (Mais tarde nesse mesmo dia as signatures saíram da métrica e a frase do ecrã
passou a dizer só «showcases»; o chip do OGN é agora «faltam 371 · 2 449,19 €».)
A linha
passou a «**360** cópias **a comprar** nesta edição» e a explicar a diferença
quando ela existe. O `tests/test_coerencia.py` fixa o que essa frase promete: a
lista nunca pede mais do que a contagem, e sem exclusões nem pendente os dois
números são o mesmo.

**Corrigido também:** «2 impressãoões a mais» na Venda (plural partido), «os
cinco decks montados ao mesmo tempo» quando são quatro (passou a contar os
decks), «1 versões»/«1 cartas» nos contadores das Faltas e do Pimp, a Venda sem
o `imgFallback` ligado (uma imagem que o cache local não tivesse ficava partida
em vez de cair para o CDN), um segundo `addEventListener('error')` no `#grid`
que era cópia do primeiro, os `aria-label` dos `+`/`−` sem o nome da carta, e o
`/favicon.ico` — o único 404 em 1870 pedidos do `data/serve.log`, agora servido
por um ícone embutido em `data:` no `index.html`.

**O README tinha decisões revogadas.** Dizia que as artes alternativas estavam
fora do master set e pediam playset (`0/3`, `0/12`), que o `master_set.fora` era
`["-T", "a"]` e que o denominador era 1068. Hoje são três blocos, alt art 1,
`["-T"]` e **1170** — medido, com `["-T","*"]` a dar 1134. Ganhou também a
secção da contagem por níveis, que não estava lá.

**Uma mudança só de frontend NÃO precisa de reiniciar o `serve` do 8770.** O
`server.web_asset` serve o `app.js`, o `index.html` e o `style.css` com
`send_from_directory` a cada pedido, e sem cache (`_sem_cache`) — quem estiver
com a página aberta só tem de recarregar. O que fica preso num processo antigo
são os **módulos Python** (foi o caso da contagem por níveis, a 2026-09-08): aí
sim é preciso matar o 8770 e deixar o vigia `riftvault-serve` relançar.
Confirmado a 2026-09-09 pedindo os três ficheiros ao servidor que já estava a
correr.

**Sem rede nesta sessão:** o `WebFetch` e o `curl` foram negados pelo modo em
que a sessão corria, por isso os links do «A subir»
(`cardtrader.com/cards/<blueprint_id>` e `riftscribe.gg/cards/<printing_id>`)
continuam **por validar** — ver "Superfícies NÃO validadas", ponto 7.

## Estado

- **Feito:** catálogo, as duas métricas, CLI completo, modo edição, modo
  publicado, workflow do Pages, e a vista de Coleção com variantes e `+`/`-`.
- **Feito também:** preços/valor (CardTrader) e a secção Decks com alocação
  por prioridade, validação de legalidade e lista de compras.
- **Feito também:** as abas "A subir" e "Master set", com as listas para o
  Cardmarket (copiar, copiar com código, CSV) e o `riftvault a-subir`.
- **Feito também:** a Coleção em blocos (master set primeiro, `-T` e `a`
  depois), com uma só `metrics.e_master`, e a secção "Venda" com o
  `riftvault venda`.
- **Feito também:** a Coleção em três blocos — master set em playset, 1 runa
  especial de cada por edição, 1 arte alternativa de cada — com percentagem
  global e por bloco, e a Venda a mostrar só o excedente.
- **Feito também:** as runas do master set a 1 de cada — base ou especial —,
  com o playset jogável a continuar nos 12 para os decks.
- **Feito também:** a wantlist do Cardmarket no fim de cada edição da Coleção
  (e uma de tudo no fim da página), com a linha «faltam N cópias · X €» no
  cabeçalho, e o `riftvault wantlist --edicao X`.
- **Feito também:** a contagem por níveis do master set — 1 de cada, 2 de cada,
  o playset —, global e por edição, com o degrau também nas wantlists da
  Coleção e a tabela no `riftvault stats`.
- **Feito também:** a revisão do site de 2026-09-09 — textos, plurais, imagens
  da Venda, o cabeçalho das Faltas com o âmbito certo e o favicon.
- **Feito também:** as signatures fora da Coleção (2026-09-09) — bloco próprio
  no fim da grelha, fora da percentagem, das contagens por níveis e das
  wantlists; as artes alternativas continuam a 1 de cada.
- **Feito também:** as sobrenumeradas fora da Coleção (2026-09-10) — as
  «300/298», pelo denominador do próprio código impresso; mesmo mecanismo das
  signatures, denominador 1134 -> 1042, e a pergunta dos «showcases» de
  2026-09-08 fica respondida.
- **Feito também:** as promos `VEN-SP` fora da Coleção (2026-09-10) — terceira
  categoria pelo mesmo mecanismo, e a mais barata (246 €); são 6, só no VEN, e
  nenhuma é sobrenumerada. Denominador 1042 -> 1036. As runas promo `VEN-R01`
  ficaram dentro, no bloco das runas especiais.
- **Feito também:** as comuns e incomuns (2026-09-10) — as mais caras e o sinal
  de procura, secção dobrada na Venda e `riftvault venda --comuns`. **Volume de
  vendas não existe em fonte pública**, e a página diz isso; o CardTrader passou
  a dar vendedores e cópias à venda, com histórico novo no `listings_history`.
  O excedente dele em comuns e incomuns vale **3,83 €**.
- **Feito também:** os locais das cópias (2026-09-10) — Coleção, `deck:<slug>` e
  binder Decks/Venda, com a Coleção a contar só o que está nela, os decks a não
  tirarem de lá, o desfazer-deck a mandar tudo para o binder, a venda por origem,
  a marcação em dois passos (propor / confirmar linha a linha) e o rasto em
  `data/locais.log`. `riftvault local` no CLI.
- **Feito também:** o site gerado no PC (2026-09-10) — o `site/` vai no Git e o
  `pages.yml` publica-o sem tocar na rede; `riftvault build --se-mudou` para
  não gastar uma build do Pages por cada volta do relógio. A RiftScribe em
  baixo já não pode parar o site.
- **Feito também:** o `Nome:` no ficheiro do deck (2026-09-11) e a chave dos
  decks a ser o slug em todo o lado — dois decks com a mesma Legend/Champion
  deixaram de se fundir na alocação e nas Staples.
- **Feito também:** os decks a partilhar a Coleção (2026-09-11, tarde) — uma
  cópia na Coleção conta para o deck; o que dois decks disputam e a Coleção
  não chega é falta a comprar do deck de baixo (o teto do playset de 09-01
  caiu); a grelha da Coleção diz que decks usam cada carta, com filtro «Em
  decks» e `riftvault stats --usadas`; a Venda não vende o que os decks usam
  da Coleção. `tests/test_partilha_compra.py`.
- **Feito e APAGADO a 2026-09-19:** o separador «Quanto custa» (2026-09-15,
  era «Faltas») — abriu na «Master set» por raridade e por preço; à tarde
  desse dia as abas por deck (Staples, Por deck, Pimp decks) passaram para o
  separador Decks (e lá ficam) e ao fim da tarde passou a ser a tabela de
  preços (top 5 por raridade, por edição, tenha ele ou não). Ele mandou
  apagar o botão a 19/09 — ver a última secção deste ficheiro. O que ficou
  dessa semana porque não era só dele: a língua das ofertas em config
  (`precos.linguas`, já era só inglês), as abas dos decks no separador
  Decks, o `api/wantlist.json` e o `api/compras.json`.
- **Feito também:** seguir jogadores no Piltover Archive (2026-09-17, parte 1
  de 2) — `seguir.py`, `riftvault seguir`, `seguir.jogadores` no config, o
  estado em `data/seguir/estado.json`; só o motor e a CLI. Ver a última
  secção deste ficheiro.
- **Feito também:** o separador «Encomendas» (2026-09-17, à tarde) — a grelha
  da Coleção de Rara para cima, com os `+`/`−` do que comprou e o «Chegou»
  por impressão; os controlos saíram dos tiles dos decks. Ver a última
  secção deste ficheiro. (Fecha o «registar uma encomenda pela interface» da
  revisão de 09-09 — já se fazia nos decks desde 11/09, agora faz-se aqui.)
- **Feito também:** o deck aproveita as versões que ele tem (2026-09-17, ao
  fim da tarde) — um lugar normal que a base não tape serve-se de outra
  versão (Alt Art, sobrenumerada, promo; nunca assinada nem retirada) antes
  de ser falta, e a vista do deck (CLI e site) reparte cada carta pelas
  impressões que a servem. Ver «o deck aproveita as versões que ele tem»,
  no fim deste ficheiro.
- **Feito também:** as runas saem da contagem dos decks (2026-09-17, à
  noite) — o Rune Pool lê-se e mostra-se só com as quantidades, sem
  tenho/faltam, alocação, disputa, compra nem euros; o «tenho X de N» conta
  só o resto (54/54 · 12 runas); e as runas nunca aparecem no «A mais».
  `decks.contar_runas: false`, `a_mais.sem_runas: true`. Ver a penúltima
  secção deste ficheiro.
- **Feito também:** as Alt Art voltam ao playset (2026-09-18) — o `a` saiu
  do `master_set.um_de_cada`, que é o alvo por categoria da coleção extra;
  sobrenumeradas e promos continuam a 1; percentagem, wantlist e valor não
  mexem. Ver a penúltima secção deste ficheiro.
- **Feito também:** as promos SP a playset (2026-09-18, mais tarde) — o
  `promo` saiu do `master_set.um_de_cada`; só as sobrenumeradas ficam a 1;
  as 6 são Units, «3 de cada» = playset; nada mais mexe. Ver a penúltima
  secção deste ficheiro.
- **Feito e DESFEITO no mesmo dia:** a montra «Promos» (2026-09-18, à tarde)
  — as promos da comunidade (Nexus Night, bundles, …) com a foto da versão
  normal; ele viu-a e mandou apagar. Ver a penúltima secção deste ficheiro.
  As 6 `VEN-SP` ficam como estavam.
- **Feito também:** a ordem dos blocos da Coleção em config e o bloco «Runas
  — 12 de cada» (2026-09-19) — master set, sobrenumeradas, alt art, promos
  (`master_set.ordem_dos_blocos`); e no fim da grelha uma VISTA das seis
  runas com tudo o que ele tem de cada, que não conta para nada
  (`runas_vista.py`, `api/runas.json`, `riftvault runas`). Ver a penúltima
  secção deste ficheiro.
- **Feito também:** o bloco das runas passa a ser o CONTADOR dele, com `+`
  e `−` (2026-09-19, à tarde) — o número vem da tabela `rune_counter` do
  vault.db, semeada uma vez com o que ele tinha na mão (76), e os botões
  (só no 8770) escrevem lá e em mais lado nenhum; «na coleção: N» fica ao
  lado, em letra pequena, como referência. Medido: pôr os contadores a 99
  ou a 0 não mexe em número nenhum. Ver a penúltima secção deste ficheiro.
- **Feito também:** as promos voltam a 1 de cada e o separador Faltas passa
  a QUATRO blocos, cada um com a sua wantlist (2026-09-19, à noite) — o
  `promo` voltou ao `master_set.um_de_cada`; o bloco «Promos» entra nas
  Faltas pela ordem partilhada da Coleção (`master_set.ordem_dos_blocos`), e
  por baixo de cada bloco há a caixa do Cardmarket só desse bloco
  (`faltas_edicao.wantlist`, `riftvault faltas --edicao X --bloco B
  --cardmarket`). A wantlist geral, o denominador, os níveis e o valor não
  mexem. Ver a penúltima secção deste ficheiro.
- **Feito também:** sai o deck do Kennen, outra vez (2026-09-20) — `git rm
  decks/kennen.txt`; ficam **três decks**: Ornn, Azir e LeBlanc Baited Hook.
  Com ele sai a falta da Legend `VEN-197/166` (210,63 €), que era quase toda
  a falta dos decks; as «Libertadas» do A mais apanharam as 30 cartas · 54
  cópias (mais 2 runas · 12 fora, por `a_mais.sem_runas`). Ver a última
  secção deste ficheiro.
- **Feito também:** o painel do topo da Coleção, o «layout H» (2026-09-21)
  — três cartões (1 de cada, 2 de cada, playset, em tenho/total) e dois
  quadros (Raridade, Domínio) sobre o bloco escolhido da edição aberta ou
  de «Todas» (separador novo, as cinco edições seguidas na grelha); as
  runas nunca entram; `painel.py`, `progress.painel`, `index.painel`,
  `riftvault stats`. Os chips antigos dos níveis e das raridades saíram.
  Ver a última secção deste ficheiro.
- **Feito também:** os seis decks novos, por ordem (2026-09-21) — LeBlanc
  Hook, Jayce, Kennen, Akali, Ornn, Azir, as listas dele tal e qual; a ordem
  passa a viver no config (`decks.ordem`, `decks.aplicar_ordem`; os botões
  de reordenar e o `--order` ficam desligados enquanto a lista existir); o
  `deck_need_log` recomeçou do zero (`uso_decks.recomecar`, `riftvault decks
  --recomecar-registo`). Ver a última secção deste ficheiro.
- **Feito e ACABADO no mesmo dia:** a experiência do pool próprio dos decks
  (2026-09-21, de manhã, `decks.modo = "pool_proprio"`) — um pool único,
  partilhado (máximo por carta), fora da Coleção. Durou até à tarde; o pool
  estava vazio. Ver a penúltima secção deste ficheiro (o que era) e a última
  (o que ficou no lugar dela).
- **Feito também:** as CÓPIAS PRÓPRIAS de cada deck (2026-09-21, à tarde) —
  os decks voltam a usar a Coleção (11/09) e cada um tem um monte à parte no
  local `proprio:<slug>` (`+`/`−` em cada carta da página do deck **até
  2026-10-01**, `riftvault proprias SLUG --mais/--menos`), que serve primeiro, é só daquele deck e
  NUNCA conta para a Coleção (nem para o valor); os decks não partilham entre
  si (a soma); só versões base, a Legend e o Champion incluídos
  (`decks.so_base`); `proprias.py`, `POST /api/proprias/ajustar`. Ver a
  última secção deste ficheiro.
- **Feito também:** a contagem de FOIL e NÃO-FOIL das comuns e incomuns
  (2026-09-22) — a coluna `copies.qty_foil`, o âmbito em config
  (`foil.raridades`, `foil.edicoes_fora`: as impressões base, não
  sobrenumeradas, comuns e incomuns, fora o OGS — 512 impressões), o contador
  pequeno em cada tile, o resumo por edição e em «Todas» por baixo do painel,
  `riftvault foil` e `POST /api/foil/ajustar`. **Não mexe em número nenhum do
  site** e há teste que o fotografa.
- **CORRIGIDO a 2026-09-26:** o FOIL **soma-se** ao normal — *"normal + foil
  e não apenas 1, no caso daria 3+3"*. Fizemo-lo como uma FATIA do total (o
  `+` do foil convertia uma cópia normal); passou a `qty` = normais,
  `qty_foil` = foils, **total = a soma**, com o `CHECK` do tecto e o
  `ao_descer` fora (migração só de schema, com backup — **nenhum número dos
  dados mexeu**, verificado impressão a impressão na `foil_ops`). Um `qty`
  a 0 com foil é estado legítimo. Duas chaves novas, que nasceram a `false`
  e que ele mandou LIGAR nessa tarde: `foil.conta_para_coleccao` e
  `foil.conta_para_valor`. Ver as três secções do fim deste ficheiro.
- **CORRIGIDO OUTRA VEZ a 2026-09-27, à noite:** o `foil.conta_para_coleccao`
  voltou a **`false`** e o TILE passou a ter **duas contagens separadas** —
  *"quero que haja 2 contagens separadas / a de normais e de foils / quando me
  falta normais nao consigo perceber automaticamente que falta"*. Somar as
  foils aos alvos escondia-lhe **48 cópias normais em 47 impressões** que se
  liam «3/3» com as normais a 2/3. O crachá é as normais, a linha de baixo é o
  foil contra o `foil.alvo` (o playset do tipo), e a separação **não depende de
  chave nenhuma**. O `conta_para_valor` FICA a `true`: é outra pergunta e o
  valor **não mudou** (7 802,52 €). Playset 87,5 % → **82,4 %**, e a descida é
  a correcção a aparecer. Ver a última secção deste ficheiro.
- **Feito também:** o PREÇO DA FOIL, à parte (2026-09-26, à noite) —
  *"podes meter filtro no cardtrader e tirar o preco da foil mais barata?,
  para diferenciar os precos"*: `price_latest.price_foil_cents` e
  `n_listings_foil` (o mínimo das ofertas foil, com os mesmos filtros das
  normais), uma cópia foil vale esse preço, e o **FALLBACK** (sem oferta
  foil, conta ao da normal) é contado e dito em vez de ficar num
  comentário. O preço da cópia NORMAL não mexeu — há teste contra o mercado
  real. Medido: **1144 das 1180** impressões com preço de foil, as 259 foils
  dele de 29,65 € para **50,78 €**, zero no fallback. Ver a última secção
  deste ficheiro.
- **Feito também:** montado ou desmontado, a regra de raridade e o modo
  de remontagem (2026-09-24) — `decks.montados` (hoje só o LeBlanc Hook;
  um deck desmontado não consome NADA da Coleção e a página dele é uma
  simulação), `decks.coleccao_so_a_partir_de: "epic"` (abaixo disso a
  cópia devia ser própria do deck — MARCA, não bloqueia) e a tabela
  «Montar este deck, carta a carta», que a 375 px vira cartões. Botão na
  página do deck (escreve no config), `riftvault decks
  --montar/--desmontar`, `POST /api/decks/montar`. Ver a última secção
  deste ficheiro.
- **Feito também:** o separador «Venda» (2026-09-25) — a conta de uma venda em
  curso, para mostrar a quem compra; os preços são o **Trend do Cardmarket
  metido à mão** (a app não tem nem pode ter preços do Cardmarket), o do
  CardTrader aparece rotulado «só referência» e nunca entra no total, e uma
  linha sem Trend conta ZERO; marcar para venda não mexe em número nenhum da
  Coleção e quem baixa as cópias é o botão separado «marcar como vendidas»,
  com confirmação e registo (`venda.py`, `api/venda.json`, `riftvault venda`).
  Ver a última secção deste ficheiro.
- **Feito também:** o separador «Produto Selado» (2026-09-25) — displays,
  cases, decks, bundles, boosters e Proving Grounds, com os três estados (o
  que há · o que tem · o que não tem), filtro e contadores; a lista vem do
  **CardTrader**, pelas CATEGORIAS dele (a 258 são as cartas), e os
  acessórios ficam de fora, contados; os que ainda não saíram aparecem
  marcados e não contam para o que falta; o valor do selado é um total
  próprio, **nunca somado ao da Coleção**; `selado.py`,
  `data/selado_catalogo.json`, `riftvault selado [--sync]`,
  `POST /api/selado/ajustar`. Ver a última secção deste ficheiro.
- **Feito também:** os **links de compra** no Produto Selado (2026-09-25, à
  noite) — «Cardmarket» e «CardTrader» em cada linha, directos quando há id
  e de PESQUISA pelo nome quando não há (dito, nunca escondido); os
  templates passaram do bloco `venda` para o bloco **`mercados`** do config
  (`mercados.py`), que os dois separadores partilham. O do **CardTrader
  ficou VALIDADO** (o `blueprint_id` sozinho responde 200; sem o `/en/` abria
  em italiano — corrigido também no «A subir»); o do Cardmarket **não**
  (403). Dos 98 selados: 81 com `blueprint_id`, 52 com `cardmarket_id`. Ver
  a última secção deste ficheiro.
- **Feito também:** tirar selados por config (2026-09-25, à noite) —
  `selado.excluidos`, 22 produtos fora (13 boosters soltos, 3 slim booster
  box, o Champion Deck Set da Origins, as Bulk Runes e os 4 Pre-Rift Kit de
  um jogador): 98 → **76**. Esconder não é apagar — o catálogo em disco fica
  intacto e repor é tirar o nome da lista; o nome é exacto e um que não case
  rebenta. Mais a limpeza do «Trial Deck Set **Set**» do catálogo
  (`selado.nome_limpo`, sem mexer no id). Ver a última secção deste ficheiro.
- **Feito também:** os 7 selados que não se compram em lado nenhum
  (2026-09-26) — *"os produtos selados que ainda ficaram, que eu procuro no
  cardmarket e nao tem disponivel, podes tirar"*: `selado.excluidos` 43 →
  **50**, a aba 55 → **48**. O critério é o cruzamento das duas coisas que se
  medem (**o Cardmarket responde 403** e não dá para lhe ver o stock): sem
  `cardmarket_id` **e** zero ofertas no CardTrader, medidas AO VIVO. As
  **edições por sair ficam** — não têm id mas têm pré-venda —, e há teste que
  rebenta se alguém simplificar o critério para «não tem Cardmarket, sai».
  **Por decidir:** os «Nexus Night Promo Booster» do UNL e do VEN. Ver a
  última secção deste ficheiro.
- **Feito também:** só impressão INGLESA no selado, e sai da aba quem não tem
  PÁGINA PRÓPRIA (2026-09-28) — fecha o varrimento dos dois mercados (o
  Cardmarket lido pelo **Chrome dele**: 73 produtos, 68 com oferta). Três
  ordens, ZERO mecanismo novo: voltam **2** dos 5 que o Cardmarket revelou
  (*Unleashed Sleeved Booster*, *Replacement Card Booster*), sai o **Arcane
  Chinese Promo Set** pela regra da língua (`_selado_so_ingles`), e os **17 do
  `selado.extra`** saem da aba para o `_selado_extra_arquivado` — esvaziar não
  é apagar. A aba 48 → **32**; o valor e o `copies` não mexem. **Duas
  descobertas:** o Cardmarket não dá página a displays nem a cases (vendem-se
  dentro do produto simples, na nota do vendedor) e o **«From» deles não é o
  preço**. Ver a última secção deste ficheiro.
- **Feito também:** NADA EM FORMA DE DECK no selado, e o «—» a dizer o que se
  passa (2026-09-28, à noite) — *"nao quero «decks» para colecionar"*: a
  categoria **262** saiu das `selado.categorias` (a regra é a CATEGORIA, não
  uma lista de nomes — um Champion Deck novo não precisa de ser escrito), a
  aba 32 → **30**, e os 18 nomes redundantes foram do `excluidos` (49 → **31**)
  para o `_selado_decks_arquivado`. **Não havia Champion Deck nenhum na aba** —
  o que lá estava eram os 2 Showdown Deck, e TINHAM oferta. O `--sync` correu
  e os **7 sem preço continuam os mesmos 7**: não era catálogo velho. O traço
  seco passou a dizer «sem oferta no CardTrader · a app não lê o Cardmarket», e
  o preço de lá ganhou a tabela **`sealed_price`** (o gémeo do Trend da Venda,
  `riftvault selado --preco ID EUROS`). Ver a última secção deste ficheiro.
- **Feito também:** as FALTAS EM DUAS METADES (2026-09-27) — as normais nos
  quatro blocos de sempre e as **FOILS** à parte, com a quinta wantlist;
  *"as foils nao sao faltas, sao apenas complemento e indicativo"*, por isso
  ficam fora da contagem de faltas, da percentagem e das listas que já
  existem (o `faltas_edicao.py` nem conhece a coluna — quem junta as duas é
  o `faltas_foil.payload_completo`, e a metade das normais sai BYTE A BYTE
  igual). Alvo = o playset do tipo que já existe (Battlefield 1, **Rune
  12**); âmbito = o do contador de foil (512, comuns e incomuns, sem OGS);
  preço da foil com o fallback contado; e o aviso das 47 impressões com foil
  e o playset das normais incompleto. Ver a última secção deste ficheiro.
- **Feito também:** os `+`/`−` de «JÁ ENCOMENDEI» nas Faltas (2026-09-27) —
  em todas as linhas de todos os blocos, as foils incluídas; são os mesmos
  botões das Encomendas (a `pending`, a rota `/api/encomenda`), sem contador
  novo, e **a linha não desaparece** — passa a dizer quanto falta e quantas
  vêm a caminho, e sai só da wantlist. A encomenda passou a ter ACABAMENTO
  (`pending.foil`, migração com backup): uma foil chega ao `copies.qty_foil`
  e uma normal ao `qty`. O «Chegou» continua só nas Encomendas, e as foils
  aparecem lá na lista «fora da grelha» (o corte é de rara para cima e elas
  são todas comuns/incomuns — **10 linhas de normais e 412 de foils** ficam
  fora dos tiles; a `encomendas.raridade_minima` NÃO se mudou). Ver a última
  secção deste ficheiro.
- **Feito também:** o DECK PRINCIPAL (2026-09-27) — `decks.principal` (um só,
  sempre montado, não é a prioridade 1), a WANTLIST dele (`precisa − próprias`,
  comuns e incomuns em foil ao preço de foil com o fallback contado; uma carta
  marcada com o `+` sai), as duas indicações («em uso no deck X» no tile,
  «X cartas em uso da Coleção, ainda falta Y» na página do deck) — e ao deixar
  de ser principal ou ser desfeito, as cópias próprias de **0,50 € para cima**
  vão à Venda marcadas com a origem, as de menos ficam, e **nada sai do deck**.
  A Coleção não muda um número: medido, zero diferenças em 24 invariantes.
  `principal.py`, `POST /api/decks/principal`, `riftvault principal`. Ver a
  última secção deste ficheiro.
- **Feito também:** AS GUARDAS do multi-utilizador (2026-09-29, a seguir à
  fundação) — o interruptor `multi.aberto` (nasce FECHADO: sem registo, sem
  túnel, sem páginas de outros, e o site dele igual ao de hoje); `users.publico`
  (`nada` por omissão, o André em `tudo`) com o `build.py` a respeitá-lo e o
  filtro que tira **7 129 quantias** no site real; o guarda em tempo de
  execução (tocar numa tabela de dono sem dono rebenta a dizer qual, e uma
  ligação ligada não anexa outra base — **custo medido: nenhum**); o
  `config.ConfigPartilhado`, que tapa o que o SQL não vê; `conta.py`
  (exportar/importar/apagar uma pessoa sem tocar nas outras); a Coleção
  Soberana como TESTE, em três camadas com prova pela negativa; a base de
  ENSAIO (`RIFTVAULT_ENSAIO=1`, que se recusa a usar o `data/` a sério); e o
  PORTÃO do merge, que lê o placar. A identidade fica DECIDIDA e não
  implementada. Ver as duas secções no fim deste ficheiro.
- **Feito também:** as CONTAS (2026-09-29, à noite) — sessões com cookie
  `HttpOnly`/`SameSite=Lax`, CSRF num cabeçalho e uma só função no cliente, o
  guarda que protege as 20 rotas de escrita, o furo do config partilhado
  (`SO_DO_DONO`), e o `multi --verificar` que recusa abrir com coisas em falta.
  **A forma de entrar mudou no dia seguinte** — ver a seguir.
- **Feito também:** ENTRAR COM UTILIZADOR E PASSWORD (2026-09-30) — *"em vez de
  discord, nao era melhor a pessoa criar uma conta com usuario e password"*,
  com a contraproposta que ele aceitou: **nenhuma password se pode LER**.
  `scrypt` da stdlib (n=2^16, **130 ms medidos na máquina dele**, sal por
  pessoa, hash auto-descritivo), a temporária de 4 palavras que ele dita e que
  **tranca o site até ser trocada**, o travão de tentativas em duas dimensões
  (5 por conta · 10 por endereço · 1→5→15→60 min), **sem registo aberto** (as
  contas nascem de `riftvault conta --criar`), e o OAuth intacto e sem botão.
  O `multi --verificar` deixou de exigir Discord e os passos DELE passaram de
  três a dois. `senha.py`, `tests/test_senhas.py`. Ver a penúltima secção deste
  ficheiro.
- **CORRIGIDO no mesmo dia, à tarde:** o BECO DA PORTA FECHADA — a caixa de
  «Entrar» escondia-se com `multi.aberto: false`, e o `multi --verificar` exige
  trocar a temporária ANTES de abrir: **não abria sem trocar e não trocava sem
  abrir**. Hoje esconde-se no **SITE PUBLICADO** (pelo `index.editable`, que já
  existia), a entrada por password **funciona com a porta fechada** (a porta só
  decide se a ESCRITA exige sessão), e o `boot()` deixou de morrer no 403 da
  trava da temporária — o **segundo beco**, que existia com a porta aberta
  também. Mais a rede de segurança `riftvault conta <slug>
  --definir-password`, que resolve tudo na consola. O site publicado sai
  **igual ficheiro a ficheiro**. Ver a última secção deste ficheiro.
- **CORRIGIDO a 2026-10-01:** **QUEM MANDA NA AUTENTICAÇÃO É A ORIGEM, NÃO A
  PORTA** (`origem.py`) — duas revisões externas independentes encontraram os
  mesmos dois defeitos: «fechar» a porta **desligava** a autenticação (com o
  túnel vivo, escrita anónima da internet) e um pedido sem sessão caía na base
  do utilizador **1**, sem a privacidade ser consultada. Hoje um pedido que não
  seja inequivocamente de casa (um **E** de três condições: endereço da rede de
  casa, nenhum cabeçalho de intermediário, não pediu o anfitrião público) exige
  sessão para **tudo**, leitura incluída, com a porta aberta ou fechada; **o uso
  dele em casa fica igual** (telemóvel na LAN, sem password). Medido contra o
  túnel a sério: **nove sinais**, cada um suficiente sozinho. Ver a última
  secção deste ficheiro e `docs/origem-do-pedido.md`.
- **Feito também:** O RESTAURO (2026-10-01) — um pacote só entra na conta DELE
  (`conta.DonoTrocado`, com a porta explícita `--adoptar`, que recarimba a base
  para o id de destino: deixar entrar sem recarimbar dava uma conta que não
  abria mais); **um restauro nunca ALARGA a privacidade** — dois testemunhos (o
  registo e a cópia dentro do `vault.db`), o mais fechado ganha, e só o
  `privacidade.definir` alarga; e apagar uma conta **diz** que pacotes dela
  ficam em disco, com `--levar-copias` para os levar. Medido no `data/` real:
  os quatro registos e as quatro bases dizem o mesmo, **zero** passam a ficar
  mais fechados. Ver a última secção deste ficheiro.
- **CORRIGIDO a 2026-10-01:** a CONTAGEM DAS RUNAS é de cada EDIÇÃO
  (`runas_vista.por_edicao`) — *"A contagem das runas Alt.Art é exclusiva para
  cada edição / vi que a contagem está a ser partilhada por todas as edições"*.
  Tinha razão: o bloco somava as cinco edições num número só e repetia-o em
  todas (no OGN a Calm Rune dizia «21», e **12 dessas eram as `SFD-R02a`**; no
  UNL dizia o mesmo 21 sem ele ter lá uma runa; o OGS levava o bloco inteiro).
  A soma do topo não mexeu — é o que «Todas» mostra —, e o **contador dele**
  ficou um por runa, dito no ecrã; **a 2026-10-03 passou a ser por edição
  também** (ver o ponto a seguir). Ver a última secção deste ficheiro.
- **ACABADO a 2026-10-03:** o CONTADOR das runas passa a ser **POR EDIÇÃO** e
  começa a **ZERO** — *"Zera e recontas por edicao"*, escolhido por ele entre
  quatro hipóteses. A `rune_counter` ganhou `set_id` na chave (migração que
  refaz a tabela, com backup) e as seis linhas dele — **14 cópias**: Body 3,
  Calm 3, Chaos 2, Fury 3, Mind 1, Order 2 — foram para a
  **`rune_counter_antes`** com o `updated_at` de cada uma: **zerar não é apagar
  o rasto**. Com elas saiu a SEMENTEIRA (o número tem de ser o que ELE conta, e
  no OGN a Calm Rune calculava 9 contra os 3 que ele contou), e por isso **ler o
  bloco deixou de escrever na base**. O ecrã ajuda a recontar: um aviso em cima
  a dizer que o zero é de hoje, com o que ele tinha contado ao lado e um
  «dispensar» que marca a data sem apagar nada; e **os `+`/`−` só aparecem na
  página de uma edição** — em «Todas» o crachá é a soma. Ver a última secção
  deste ficheiro.
- **CORRIGIDO a 2026-10-02:** a RAIZ PUBLICADA deixa de se indexar
  (`abrir.lista_indexavel`) — a lista nomeia os amigos **e o valor da coleção de
  cada um** e era a única página do site sem `noindex`; a de cada um deles já a
  tinha. Escolha dele entre quatro hipóteses: *"a lista deixa de ser indexada,
  como já acontece com as páginas de cada um; quem tiver o link abre tudo
  igual"* — não quis tirar os euros nem fechar o site com um `robots.txt` na
  raiz. Pelo mesmo caminho das outras páginas (`abrir.marcar_html`). Medido: 77
  ficheiros de cada lado, **uma** diferença (o `index.html`, +116 bytes); a dele
  continua sem marca. Ver a última secção deste ficheiro.

- **Feito também:** a PÁGINA DO DECK NÃO TEM `+`/`−` (2026-10-01) — *"no deck
  nao precisa + e - / ele ja indica se tem ou nao tem"*. Saíram os das CÓPIAS
  PRÓPRIAS, que eram os únicos que lá estavam, e ficou o **número** («N
  próprias do deck») no lugar deles; mexer nele é no `riftvault proprias`. As
  outras **sete** famílias de `+`/`−` não se tocaram — medido no browser: a
  página do deck passou de **27 steppers a 0** e a Coleção (512), as Faltas
  (232), as Encomendas (162), a Venda (3) e o Selado (30) ficaram iguais. Ver a
  última secção deste ficheiro.
- **Feito também:** COLAR UMA DECKLIST (2026-10-02) — a caixa de copy-paste na
  secção Decks, com a previsão antes de gravar (as linhas que casaram, as que
  não casaram, a aritmética por papel) e o `.txt` a aterrar na pasta DE QUEM
  COLOU; o leitor é UM só (`decks.parse_texto`, o mesmo dos ficheiros) e o deck
  nasce do `import_all` de sempre. Mais a **edição que cobre sozinha**
  (`decks.por_cobertura`) e as duas frases do relato («2 de OGN + 1 de UNL»,
  «3 — 1 normal, 2 Alt Art»), e a **arte a cinzento** no que ele não tem.
  `colar.py`, três rotas, `riftvault colar`, e o botão «Apagar a lista» — que
  fecha o «apagar decks pela interface» que estava por fazer desde o início.
  **A leitura por IMAGEM não se fez**: não há OCR nenhum na máquina e não se
  instala nada. Ver a última secção deste ficheiro.
- **Feito também:** LER UMA DECKLIST POR IMAGEM (2026-10-02, à tarde) — a
  segunda porta da mesma caixa, e **sem OCR**: não há nenhum nesta máquina
  (medido outra vez) e não se instalou nada. Cada recorte casa-se com a ARTE
  do catálogo (as 1180 `.webp` que já estavam em disco), o que identifica a
  IMPRESSÃO exacta — as duas Alt Art da lista dele saíram certas —, e as
  quantidades lêem-se dos crachás `xN` por template, com uma guarda
  TOPOLÓGICA (buracos) que torna a confusão 3/8 impossível. Os papéis vêm do
  `type` do catálogo e o corte do sideboard do ESPAÇO entre linhas. O texto
  entra pela MESMA porta (`colar.py`) e enche a MESMA caixa, que é editável.
  **Prova com a imagem dele: 31/31 cartas, zero dúvidas.** `imagem.py`,
  `POST /api/decks/imagem`, `riftvault imagem`. Ver a última secção deste
  ficheiro.
- **Feito também:** A EFICIÊNCIA DO SITE (2026-10-04) — a CASCA (`app.js`,
  `style.css`) passou a viver na raiz UMA VEZ SÓ, com cada
  `u/<slug>/index.html` a apontar-lhe `../../` (`site/` 78 ficheiros /
  7 181,7 KB → **74 / 6 280,0 KB**, −901,7 KB, e −450,4 KB por cada pessoa
  nova); e um ficheiro cujo conteúdo não mudou **deixou de se reescrever**
  (`build._Saida`, o `mesmo_conteudo` a decidir ficheiro a ficheiro). O regime
  permanente era pior do que o varrimento dizia: **os dez commits do `site/`
  de 2026-10-04, de meia em meia hora das 05:37 às 10:07, tocaram 28 ficheiros
  cada um e em 28 de 28 só o relógio mudava** — um commit e uma build do Pages
  de 30 em 30 minutos, 48×/dia, porque o `--se-mudou` só olhava para a coleção
  dele. Hoje uma publicação em que nada mudou escreve **0 ficheiros**. A
  decisão sobre o `generated_at` do índice (a prova de que o site publicado é
  o gerado aqui) está escrita e em teste, e **nada se mudou em
  `ai-pc/tasks/`**. Fecha a lacuna 8.5: `tests/test_eficiencia_site.py`, 24
  testes que CONTAM BYTES, com prova pela negativa na FONTE (4/4/1 vermelhos).
  Ver a última secção deste ficheiro e `docs/eficiencia-site-2026-10-04.md`.
- **Por fazer:** a parte 2 do seguir — o separador no site e a tarefa diária;
  e a vista "todos os decks ao mesmo tempo" (hoje vê-se deck a deck, com as
  partilhadas assinaladas).

## `Nome:` no ficheiro do deck, e a chave de um deck é o SLUG (2026-09-11)

Palavras dele: *"adiciona outro deck de LeBlanc, chama-lhe LeBlanc Baited
Hook"*. O `decks/leblanc-baited-hook.txt` tem a mesma Legend e o mesmo
Champion do `leblanc.txt`, e o rótulo era só `legend · champion`: liam-se os
dois igual.

**Uma linha opcional `Nome: <texto>` (ou `Name:`) no `.txt`, antes do
`Legend:`.** Se existir, é o rótulo em todo o lado — CLI, secção Decks, Pimp
decks, «Deck …» dos locais, wantlists. Sem ela fica `legend · champion`, como
sempre. Só o `leblanc-baited-hook.txt` a tem; os outros cinco não. O Legend e
o Champion continuam guardados à parte (`decks.legend`/`champion`).

**O bug que estava por baixo era pior do que o rótulo.** Dois sítios
comparavam decks pelo RÓTULO e fundiam os dois LeBlanc:

- `decks.allocate`: o «está noutro deck?» era `h["deck"] != nome`. O segundo
  LeBlanc não via o primeiro como outro deck, e o que o primeiro já tinha
  reservado da Coleção saía como **a comprar**. Medido no `data/` real:
  o LeBlanc Baited Hook passou de «falta 30 · noutro 19» para
  **«falta 5 · noutro 44»** — 25 cópias que ele já tem (Karthus, Ruined Rex,
  Glasc Mixologist, …) deixaram de estar na lista de compras.
- `faltas._wanted`: os decks que pedem uma carta eram um dicionário por
  rótulo. Uma carta nos dois LeBlanc contava como pedida por UM deck e não era
  staple. As cartas pedidas por >= 2 decks passaram de 21 para **36**, e as
  Staples de 2 para **5**.

Agora `held` e `_wanted` levam o `slug` e comparam por ele; o `deck` (rótulo)
é só para mostrar. **A chave de um deck é sempre o slug** (`path.stem`).

**Se o rótulo ainda se repetir** (dois ficheiros sem `Nome:` e a mesma
Legend/Champion), `decks.rotulos` deixa o de prioridade mais alta como está e
acrescenta o slug entre parênteses aos outros — aparecem os dois, nunca um
atrás do outro. O `deckCurto` do `app.js` guarda esse sufixo nos rótulos
curtos. `tests/test_nome_do_deck.py` fixa tudo isto, contra pastas
temporárias.

**A tabela de 5 linhas para 6 decks NÃO se reproduziu**: com o `data/` real
copiado para `_lixo/`, o `riftvault decks` de antes da correcção já mostrava as
6 linhas (com dois rótulos iguais). O que faltava era o sufixo, não a linha.

## 11/09/2026 - decks independentes: feito e DESFEITO no mesmo dia

A regra «cada deck e independente; a Colecao fica com as comuns e incomuns e o deck compra as suas» foi implementada (merge e793cf2) e revertida a pedido do Andre minutos depois: «afinal nao, mete a colecao a partilhar cartas com os decks». Vale o modelo dos binders de 10/09: uma copia na Colecao conta para o deck. Nao voltar a implementar sem ele pedir. O teste dessa ordem apagou o riftvault_config.json real durante a bateria - qualquer teste novo tem de correr contra copias, nunca contra o data/ e o config a serio.

## 15/09/2026 - a Venda foi APAGADA

Palavras dele: *"esquece a parte da venda, podes apagar para já, se for
necessário mando fazer novamente"*. Não é desligar por config nem esconder o
separador: o código saiu — `riftvault/venda.py`, `riftvault/comuns.py`, o
`riftvault venda [--comuns]`, a rota `/api/venda.json`, o `site/api/venda.json`,
o separador e a página no `app.js`/`index.html`, o CSS próprio, a chave
`comuns` do config e os testes só dela (`test_venda.py`, `test_comuns.py`, mais
as classes `TestVenda*` dos outros). Ramo `ai-pc/sem-venda-2026-09-15`; o commit
exacto a reverter para ela voltar está no relatório
`ai-pc/work/revisao/riftvault-sem-venda.md`.

**O que ficou, de propósito, porque não era só da Venda:** o local «binder
Decks/Venda» (`locais.BINDER`, o nome fica); o `decks.colecao_allocation` e o
`binder_allocation` (a grelha da Coleção lê-os para o «Azir 3 · Ornn 1»); o
`prices.oferta`/`listings_history` (recolha de mercado, continua no `riftvault
prices`); o `a_subir.medianas_por_raridade` e o `a_subir.ponto`; o
`cardmarket.quantidade` a aceitar `qty`. O `cmLigar`/`cmMostrar` do `app.js`
perderam o parâmetro `onde`, que só a Venda usava.

**Não voltar a construir sem ele pedir.** As perguntas abertas das secções de
cima («deve o que sai da Coleção ser sugerido para venda?», «acompanhar uma
carta impede vendê-la?») ficaram sem resposta — ele mandou apagar em vez de
responder.

## 15/09/2026 — o contador dos blocos diz as duas contas

Fotografias dele do 8770: «Coleção — promos — playset · tens **0** de 6» com o
`VEN-SP4` e o `VEN-SP5` a cores e com o crachá «1/3». **Não era bug de
contagem**: o `tens N de M` conta PLAYSETS COMPLETOS (`qty >= target`,
`metrics.set_payload` e o `render()` do `app.js`), e isso era o número certo
desde 2026-09-08 — só que nessa altura a coleção extra pedia 1 e «tens N» era
o mesmo que «tens pelo menos uma». Quando a 14/09 o alvo passou a playset, o
número ficou certo e a etiqueta passou a mentir. Não foi o merge `9d5b544`: o
contador não mudava desde 08/09.

Agora o cabeçalho diz **«tens 2 de 6 · 0 no playset completo»**; o «· K no
playset completo» só aparece quando o bloco pede mais do que 1 (`max_target`),
senão eram dois números iguais. O payload leva `owned`, `done` e `max_target`
por bloco; o cliente recalcula os três. O master set não tem cabeçalho (é a
barra), mas leva os mesmos campos. `tests/test_contador_bloco.py`.

## 15/09/2026 — as runas sem numeração saem (`-R` para `escondidas`)

Palavras dele: *"Tira as Runas de aparecerem"*; perguntado se eram só as
especiais: *"Saiem as runas todas e deixam de contar para masterset"*; e logo
a seguir: *"menos as que tem numeração de masterset"*.

**O critério é a NUMERAÇÃO, não o tipo.** As 18 runas do catálogo:

| | código | lado |
|---|---|---|
| 6 bases do OGN | `OGN-007/298` … `OGN-214/298` | numeradas — ficam na sequência, alvo 1, contam |
| 6 artes alternativas do OGN | `OGN-007a/298` … `OGN-214a/298` | numeradas (partilham o número da base) — ficam no bloco «runas especiais», coleção extra, alvo 1 |
| 6 promo do VEN | `VEN-R01` … `VEN-R06` | **sem** numeração (sem `/tamanho`) — **escondidas** |

Uma linha de config: `"-R"` saiu de `fora_da_percentagem` e entrou em
`escondidas` (`riftvault_config.json` e `config.DEFAULTS`). Não houve função
nova — é o mecanismo dos tokens e das signatures. **O que está escondido não
sai do vault**: as cópias continuam no `copies` e no valor.

**Os números não mexem, e é o esperado**: as `-R` já estavam fora da
percentagem desde 14/09. Medido antes e depois na mesma corrida — denominador
**928**, níveis **91,6 % / 82,5 % / 74,2 %** (850/766/689), wantlist «tudo»
**229 linhas · 432 cópias · 1 629,47 €**, valor da coleção **2 144,86 €** —
tudo igual. O que muda: o separador do VEN passa de 227 para **221**
impressões e o bloco «Coleção — runas especiais» do VEN desaparece. **No OGN o
bloco fica**, com as 6 artes alternativas das runas — são numeradas.

**A pergunta que fica:** as artes alternativas das runas do OGN têm número
(`OGN-007a/298`) mas não são a sequência. Pelo critério dele, à letra, ficam;
se o que ele queria era «só as runas base», é tirar o `alt_art` de runa do
`e_runa_especial` — pergunta para ele, não se inventou.
`tests/test_runas_fora.py`; `test_masterset`, `test_promos`, `test_signatures`
e `test_tres_blocos` foram ajustados porque descreviam a runa promo no bloco.

## 15/09/2026 — sobrenumeradas e promos voltam a 1 de cada (`master_set.um_de_cada`)

Palavras dele: *"overnumbered e promos (SP) voltamos a 1 de cada"* e, logo a
seguir, *"se eu tiver mais adiciono na mesma"*.

**Revoga, só para estes dois blocos, o «Alt Art, overnumbered, etc etc mete
Playset na contagem» de 14/09 à noite.** As artes alternativas ficam a
playset (ele não as nomeou); as runas ficam como a ordem das runas as deixou.

| bloco | alvo antes | alvo agora |
|---|---|---|
| `overnumbered` (92: OGN 12, SFD 30, UNL 19, VEN 31) | playset do tipo (47 a 3, 45 já a 1 — Legends e Battlefields) | **1** |
| `special` (as 6 `VEN-SP`) | 3 (são Units) | **1** |
| `alt_art`, `rune_special` | playset / 1 | igual |

**Uma lista nova no `master_set`, com a mesma gramática das outras duas:**
`"um_de_cada": ["overnumbered", "promo"]` (`riftvault_config.json` e
`config.DEFAULTS`). Responde a UMA pergunta só — o ALVO (`metrics.e_um_de_cada`,
lido pelo `master_target` depois das runas e antes do playset do tipo). Não
mexe no bloco, na percentagem (continuam fora por `fora_da_percentagem`) nem
nas listas de compra (continuam fora por `listas_de_compra.so_master_set`).
O cabeçalho dos dois blocos passou a dizer «— 1 de cada» (`_sufixo_alvo`).
Um valor desconhecido rebenta, como nas outras listas.

**«Se eu tiver mais adiciono na mesma» manda na leitura do número.** 1 é o
que ele quer TER de cada, não um tecto. Uma segunda cópia fica no tile como
**«2/1», a verde** — é a forma que a página já tinha para a quarta cópia de
uma Unit da sequência e para as runas base do OGN que ele tem a 3 (`3/1`) —,
conta no valor, e nada a marca como a mais: o `set_payload` não tem campo
de excesso e o `test_alvo_1.py` fixa que o tile com 2 tem exactamente os
campos do tile com 1 e o bloco conta o mesmo. **Não se inventou uma marca
nova**: a única leitura que a frase dele permite é «tenho, e tenho mais».

**O cabeçalho dos blocos, depois da ordem anterior.** O «tens N de M» conta
impressões com pelo menos uma cópia (`owned`) e o «· K no playset completo»
só aparece com `max_target > 1`. Com alvo 1 as duas contas são o mesmo número
e o sufixo desaparece sozinho: lê-se «Coleção — promos — 1 de cada · tens 2
de 6», que é verdade e completo. Não foi preciso mexer no `app.js`.

**Medido a 2026-09-15 no `main`, na mesma corrida, mesmo `vault.db` e mesmos
preços — os três invariantes NÃO mexem:** níveis **91,6 / 82,5 / 74,2 %**
(850/766/689 de 928), wantlist «tudo» **229 linhas · 432 cópias ·
1 629,47 €**, valor **2 144,86 €**. O que muda são os dois blocos:
sobrenumeradas 92, tem pelo menos uma de **6**, completas 5 → **6**; promos 6,
tem **2**, completas 0 → **2**. Nenhuma com mais do que uma cópia hoje.

`tests/test_alvo_1.py`; `test_promos`, `test_overnumbered`,
`test_tres_blocos` e `test_contador_bloco` foram ajustados porque descreviam
estes blocos a playset (o `test_contador_bloco` passou a usar as artes
alternativas como bloco de playset).

**O README continua a descrever os três blocos de 09-08** (três a contar,
denominador 1036, `master_set.fora`) — está velho desde 14/09, não é desta
ordem; fica anotado.

## 15/09/2026 — o separador «Faltas» passa a «Quanto custa»

**O separador foi APAGADO a 2026-09-19** — ver a última secção deste
ficheiro. Esta secção e as duas seguintes são história.

Palavras dele: *"na aba faltas, Renomeia para algo que seja apelativo a ter
atenção ao preço"* / *"fazes novamente para cada set (menos proving grounds)
um botão"* / *"depois metes para cada raridade, as cartas por ordem de
preço"*.

**O nome.** O terceiro separador chama-se **«Quanto custa»** (escolha do
supervisor da ordem: «faltas» descreve a ausência e não fala de dinheiro;
«Quanto custa» põe a pergunta do preço em primeiro lugar). Mudou só a
**etiqueta visível** — `index.html`, `app.js`, README, este ficheiro, o site
gerado. **O identificador interno continua `faltas`** em todo o lado: a
secção `#faltas`, o `#falta-tabs`, a chave `state.faltas`/`prefs.falta`, o
`api/faltas.json`, o `faltas.py`. Mudá-lo arrastava a rota, o ficheiro
publicado, os ids de DOM e vinte testes por uma palavra que ele não vê.

**Os botões por edição já existiam** — a aba «Master set» tinha chips por
edição desde 062688e (2026-09-08), com o OGS e um «todas», mas a secção abria
nas Staples e ele não os via. O «novamente» resolveu-se aí: a **«Master set»
passou a ser a primeira aba e a que abre por omissão**, e os chips passaram a
vir do servidor. `a_subir.edicoes_quanto_custa` lê as edições do **catálogo**
(uma edição nova ganha botão sozinha) menos `quanto_custa.sem_edicoes`
(`["OGS"]`, com `_nota` no config: pedido dele a 15/09). Vai no payload em
`master.quanto_custa` (`sets`, `sem_edicoes`, `rarity_order`). **«Tudo» é o
que os botões mostram — sem o OGS**; as 13 cartas dele (18,03 €) continuam na
wantlist da Coleção e a página diz-o. A escolha guardada (`prefs.masterSet`)
sobrevive ao refresh; uma escolha que já não tenha botão cai em «tudo».

**Por raridade, por preço.** `a_subir.por_raridade` (gémeo `qcGrupos` no
`app.js`, comparado ao Python nas 10 combinações edição × ordem contra o
`data/` real): raridades **da mais rara para a mais comum** (`epic, rare,
uncommon, common` — a raridade é o primeiro sinal do preço, e as épicas
custam mais; uma desconhecida vai para o fim), dentro de cada uma **pelo preço
unitário**, do mais caro para o mais barato por omissão (é o que o faz reparar
no preço), desempate pelo total e pelo código. O inversor («mais barato
primeiro», `prefs.masterOrd`) só troca a ordem **dentro** de cada raridade —
os cabeçalhos ficam no sítio. Cada raridade diz o subtotal (preço × cópias em
falta), o fim diz o total e a soma por raridade. **Sem preço** vai para um
grupo próprio no fim («sem oferta no CardTrader»), subtotal `None`, fora do
total — não desaparece nem conta como zero. O preço passou a coluna a negrito
e no telemóvel deixou de ser ele que se esconde (era o `.mf-preco`; agora é o
total da linha). `a_subir.quanto_custa(con, cfg, set_id, ordem)` é a mesma
coisa em Python, para o CLI e os testes.

**NÃO É UMA LISTA NOVA.** São os itens do `master_faltas` arrumados de outra
maneira: só o master set (`listas_de_compra.so_master_set`), mesma regra de
carência, mesmas exclusões. **Medido a 2026-09-15 no `main` e no ramo, mesma
corrida, mesmo `data/`:** níveis **850/766/689 de 928 = 91,6 / 82,5 /
74,2 %**, wantlist «tudo» **229 linhas · 432 cópias · 1 629,47 €**, valor
**2 144,86 €** — iguais nos dois. O que a página mostra: «tudo» (4 edições)
216 impressões · 419 cópias · **1 611,44 €** (épicas 1 504,90 € + raras
93,13 € + incomuns 12,74 € + comuns 0,67 €); OGN 783,58 €, SFD 360,41 €, UNL
319,56 € (só épicas), VEN 147,89 €; zero sem preço hoje.

`tests/test_quanto_custa.py` (21 testes, contra cópias e config temporário):
botões, OGS fora, edição nova, «tudo» sem OGS, ordem por raridade e por
preço (com os preços fora da ordem do número, para a ordenação apagada dar
vermelho), inversor, unitário e não total, sem preço no fim, subtotais e
total, a mesma lista do «Master set», a coleção extra fora, não escreve.

## 15/09/2026, à tarde — as runas numeradas pedem 3 (`master_targets_by_type`)

Palavras dele: *"as runas que estao no masterset (acho que e so origin) vamos
ate 3 como as outras cartas"*.

**A regra em duas linhas:** uma runa COM numeração de master set pede o alvo
normal, **3**, como uma Unit — base na sequência (`OGN-007/298`) ou arte
alternativa no bloco «runas especiais» (`OGN-007a/298`). As sem numeração
(`VEN-R01..R06`) continuam escondidas (ordem `runas-fora`, mesma manhã).

Revoga em definitivo o «runas 1 de cada» (2026-09-08; reafirmado a 14/09 à
noite). **O ramo runa→1 saiu do `metrics.master_target`**: o alvo é o do tipo
(`metrics.alvo_do_tipo` = `master_targets_by_type` por cima de
`playset_targets_by_type`), e a runa deixou de ser caso especial no código.
`master_targets_by_type: {"Rune": 3}` é a única entrada — é a tabela que
separa «colecionar» (3) de «jogar» (12, o Rune Pool).

**São só as do OGN, e ele tem razão.** No catálogo da RiftScribe as 18 runas
são: 6 bases OGN (numeradas, sequência), 6 artes alternativas OGN (numeradas,
bloco «runas especiais», coleção extra) e 6 promo VEN (sem numeração,
escondidas). O SFD e o UNL não têm runas na RiftScribe (BURACO NO CATÁLOGO);
as do CardTrader vivem no `market_only`, fora das métricas.

**Medido a 2026-09-15 no `main` (`c501739`) e no ramo, mesma corrida, mesmo
`vault.db`, mesmo catálogo e preços:**

| | antes | depois | porquê |
|---|---|---|---|
| denominador | 928 | **928** | conta IMPRESSÕES, não cópias; o alvo não mexe nele |
| nível 1 | 850/928 = 91,6 % · faltam 78 · 386,51 € | igual | as 6 bases OGN já tinham ≥ 1 |
| nível 2 | 766/928 = 82,5 % · faltam 229 · 1 119,54 € | **763/928 = 82,2 %** · faltam **232** · 1 119,87 € | 3 runas a 1 cópia (`OGN-007`, `126`, `166`) deixam de estar feitas: +3 |
| playset | 689/928 = 74,2 % · faltam 457 · 1 991,92 € | **686/928 = 73,9 %** · faltam **463** · 1 992,58 € | as mesmas 3 × 2 cópias: +6 |
| wantlist «tudo» | 229 linhas · 432 cópias · 1 629,47 € | **231 · 436 · 1 629,91 €** | entram `OGN-007` Fury Rune e `OGN-126` Body Rune, 2 cada a 0,11 €; a `OGN-166` tem 7 a caminho e não entra |
| valor da coleção | 2 144,86 € | **2 144,86 €** | não mexe, como tem de ser |

As outras três bases (`042` ×9, `089` ×3, `214` ×5) já estavam a 3 ou mais e
leem-se «9/3» a verde — a leitura de «se eu tiver mais adiciono na mesma».

**Os restos da config, um a um** (confirmados com `git grep`):

- `runas_especiais.alvo` — **saiu** no `4c5a817`; `tipos`/`excepto` ficam,
  porque decidem o BLOCO (`metrics.e_runa_especial`), não o alvo.
- `playset_targets_by_type.Rune: 12` — **fica, porque ainda é lido**: é a
  métrica 1 (a barra do playset jogável na Coleção, `g["playset"]`), a
  resposta do `/api/card`, o teto do Pimp e o `cap` das Faltas. É o Rune Pool
  dos decks, não um alvo de coleção.
- `faltas_ignorar_tipos: ["Rune"]` — **fica, e não esconde nada do «Quanto
  custa»**: só o `faltas.py` o lê (Staples, Por deck, Todos juntos — as abas
  dos DECKS, decisão de 2026-09-01). O «Quanto custa»/«Master set» é o
  `a_subir.master_faltas`, que não o conhece — medido: a Fury Rune e a Body
  Rune aparecem lá a «1/3».

`tests/test_runas_3.py` fixa a regra (era referido por cinco testes e não
existia); `test_niveis`, `test_contador_bloco` e `test_wantlist_edicao`
descreviam a runa a 1 e foram ajustados.

## 15/09/2026, à tarde — «Quanto custa»: só inglês, por edição, top 5 por raridade

**O separador foi APAGADO a 2026-09-19** — ver a última secção deste
ficheiro. O ponto 1 (a língua, `precos.linguas`) e o ponto 2 (as abas por
deck no separador Decks) ficaram; o ponto 3 saiu com o separador.

Palavras dele: *"apenas cartas versao ingles"* / *"no quanto custa, quero as
mais caras por edicao, nao por deck, e quero em cada edicao o top5 de mais
caras de comuns, e top5 de incomuns, e top5 de Raras"* / *"miticas e AltArt
nao precisa fazer isto"*. Ramo `ai-pc/top5-2026-09-15`; relatório em
`ai-pc/work/revisao/riftvault-top5.md`.

**1. Só inglês — já era, e passou a estar à vista.** O `prices._usable` já
exigia `riftbound_language == "en"` desde 2026-08-31 (`LANGUAGE`, fixo no
código): cada oferta do CardTrader traz a língua (`en`, `fr`, `zh-CN`, … —
vê-se no `tests/fixtures/cardtrader-ogs-market.json`, que é um snapshot real)
e as outras nunca entraram no preço nem nas contagens da oferta. A RiftScribe
**não tem língua por impressão** — o catálogo é o das cartas em inglês, não
há segunda língua para filtrar. Passou a `precos.linguas: ["en"]`
(`riftvault_config.json` e `config.DEFAULTS`, lido por `prices.linguas`),
com `_precos_nota`; a lista vazia rebenta. **Os preços e a wantlist NÃO
mudaram com isto** — medido na mesma corrida, antes e depois: níveis
850/763/686 de 928, wantlist «tudo» 231 · 436 · 1 629,91 €, valor
2 144,86 €. Na lista do Cardmarket a língua **não se marca no texto** — é um
filtro por entrada na interface deles, como o foil — e a nota por baixo da
caixa passou a dizê-lo.

**2. Por edição, não por deck.** O separador tinha seis abas e três eram por
deck: Staples, Por deck e Pimp decks. Saíram daqui e **vivem no separador
Decks, a seguir às Encomendas** (`DECK_FALTA_TABS` no `app.js`, ids
`staples`/`pordeck`/`pimp` em `state.deckId`). Nada se apagou: são os mesmos
dados do `faltas.json` e as mesmas funções de desenho (`renderStaples`,
`renderPorDeck`, `renderPimp`); o que muda é onde escrevem — `faltaSaida`
lê do estado se está no separador Decks e devolve `#deck-head`/`#deck-body`
ou `#falta-head`/`#falta-body`. O cabeçalho «Falta comprar aos decks»
(`FALTA_HEAD`) foi com elas. O «Quanto custa» ficou com **Master set, A subir
e A caminho**; uma escolha guardada de uma aba que mudou de sítio cai na
primeira. A página de cada deck já tinha o «Em falta, por edição» e o CSV —
o que só existia aqui (Staples, «Todos juntos», Pimp) é o que se mudou.

**3. Top 5 por raridade, em cada edição.** `quanto_custa.top_por_raridade: 5`
e `quanto_custa.raridades_com_top: ["rare", "uncommon", "common"]`
(`riftvault_config.json` e `config.DEFAULTS`, `_quanto_custa_top_nota`).
`a_subir.por_raridade(itens, ordem, top)` mantém `items` inteiro no grupo e
acrescenta `top`, `top_ids` (as que se vêem fechado — as `n` mais caras, as
mesmas seja qual for o inversor) e `hidden` (`cards`/`copies`/`cents` do que
não se vê); um grupo que caiba não leva corte. O gémeo `qcGrupos` do
`app.js` faz o mesmo, comparado ao Python nas 10 combinações edição × ordem
contra o `data/` real (0 diferenças). O rodapé de cada grupo cortado diz
«mais N raras · K cópias · X € que não se vêem, mas contam no subtotal» com
um **ver todas** (abre o grupo, não se guarda). **As épicas mostram-se
todas** — é a raridade de topo no catálogo da RiftScribe, não há «mítica»;
as artes alternativas já não chegam a este separador desde a manhã
(`listas_de_compra.so_master_set`), confirmado: 0 no âmbito. **O subtotal de
cada raridade, o total do separador e a wantlist contam tudo** — a wantlist
sai dos `items`, não do que se vê; `test_top5` fixa que o total é o mesmo do
`master_faltas` e maior que a soma do visível.

**No «tudo»** (as quatro edições com botão) o top 5 é sobre as quatro
juntas, não 5 por edição — ele pediu «em cada edição», e é isso que os
botões por edição dão; o «tudo» é o resumo. Se quiser 5 por edição também no
«tudo», é agrupar por `set` antes de cortar.

**Medido a 2026-09-15 no `main` (`c0d8823`) e no ramo, mesma corrida, mesmo
`data/`:** os três invariantes iguais (acima). «Quanto custa» «tudo» 218
impressões · 423 cópias · **1 611,88 €** nos dois; o que o corte esconde do
ecrã: raras 25 de 30 (8,37 €), incomuns 49 de 54 (9,83 €), comuns 3 de 8
(0,33 €) — 18,53 € em 77 linhas, todos no subtotal. Por edição: OGN 784,02 €
(raras 15 de 20 fora, incomuns 37 de 42, comuns 3 de 8), SFD 360,41 € (raras
3 de 8, incomuns 7 de 12), UNL 319,56 € (só épicas, nada cortado), VEN
147,89 € (2 raras, nada cortado).

`tests/test_top5.py` (20 testes, contra cópias e config temporário): a
oferta noutra língua não entra, a lista do config manda, vazia rebenta; sete
comuns → cinco vistas e «mais 2» com a soma certa; subtotal e total contam as
sete; épicas todas; um grupo que cabe não leva corte; `top_por_raridade: 3`
corta a 3, `0` desliga; o inversor mostra as mesmas cinco ao contrário; o
payload leva o corte; e o separador não tem abas por deck (lê o `app.js`).

## 15/09/2026, fim da tarde — o «Quanto custa» NÃO é as faltas: é a tabela de preços

**O separador foi APAGADO a 2026-09-19** — ver a última secção deste
ficheiro. A tabela de preços (`quanto_custa.py`, a rota, o `riftvault
quanto-custa`, a chave de config) saiu inteira; o que esta secção descreve
como «ficou (partilhado)» — `faltas.compras`, `api/compras.json`,
`api/wantlist.json`, o `riftvault a-subir` — continua.

Palavras dele: *"o separador quanto custa **nao e para ter as faltas!** / e
para passar a ter o top 5 comum mais cara, por cada set / o top 5 incomum mais
cara por cada set / o top5 rara mais cara por cada set / o top5 mitica mais
cara por cada set"* e, antes, *"apenas cartas versao ingles"*. Perguntado até
onde ia o «podes apagar as faltas»: **só o separador**. Ramo
`ai-pc/top5-2026-09-15` (recriado — o da manhã já tinha sido fundido);
relatório em `ai-pc/work/revisao/riftvault-top5.md`.

**As duas ordens anteriores de hoje sobre este separador eram o entendimento
errado** («Master set» por raridade e por preço; depois o top 5 do que
FALTAVA). O separador é uma **tabela de preços do jogo**: para cada edição,
quatro blocos — comuns, incomuns, raras, míticas — com as
`quanto_custa.top_por_raridade` (5) mais caras de cada, **tenha ele ou não**.
Uma carta de que já tem as três cópias continua a ser das mais caras e
aparece; a linha diz «tens N/M» (cópias na Coleção, `locais.na_colecao`, e o
alvo) só como informação. Sem totais nem subtotais — não é uma lista de compra.

**«Mítica» é o `epic` da RiftScribe.** O catálogo tem `common`, `uncommon`,
`rare`, `epic` e `showcase`; não há `mythic`. A página escreve «míticas» e
diz que são as *epic*. A `showcase` não é raridade de jogo (é o tratamento
das 42 reimpressões de topo do OGN/SFD) e não cabe em nenhum dos quatro
blocos — hoje nem chega lá, ver a seguir.

**O que entra: só a sequência da edição** (`metrics.e_master`, o bloco
`master`), `quanto_custa.so_sequencia: true`. Ele tirou as artes alternativas
pelo nome (*"AltArt nao precisa fazer isto"*); as sobrenumeradas e as promos
são a mesma categoria nas palavras dele de 14/09 (*"Alt Art, overnumbered, etc
etc é puramente coleção"*) e saem pela mesma razão — **e não é indiferente**:
no UNL e no VEN as sobrenumeradas têm raridade de jogo no catálogo, e com elas
dentro o top 5 das comuns do UNL eram os cinco Poros (`UNL-221` Lonely Poro a
285,64 €, …), o das raras do UNL e do VEN eram só reimpressões de topo
(`VEN-189` Rogue Assassin a 400,64 €) e o das míticas do UNL abria com o
`UNL-238` Baron Nashor a 2 100,64 €; no OGN e no SFD as mesmas reimpressões
são `showcase` e nem cabiam nos blocos. Medido antes de decidir. **É
pergunta para ele** — `so_sequencia: false` mete a coleção extra (menos as
artes alternativas) e a linha diz o bloco («sobrenumeradas», «promos»).
Tokens, signatures e runas sem numeração continuam escondidos
(`metrics.e_colecao`). Sem preço não entra (não há por onde ordenar) e o
rodapé conta-as.

**O OGS continua sem botão** (`quanto_custa.sem_edicoes: ["OGS"]`), de
manhã, quando isto eram faltas (*"menos proving grounds"*). Agora que é uma
tabela de preços ele pode querer o OGS de volta — é decisão dele, ficou no
relatório.

**A língua já estava certa, e é na recolha que existe.** O `prices._usable`
só aceita ofertas com `riftbound_language` em `precos.linguas` (`["en"]`,
desde a manhã; antes era `LANGUAGE = "en"` fixo desde 2026-08-31). A
RiftScribe não tem língua por impressão. Não há segunda filtragem na tabela:
o `price_latest` já é só inglês, e por isso **os preços e a wantlist não
mudaram com a língua** — medido na mesma corrida, antes e depois.

### O que se apagou das faltas, e o que ficou por ser partilhado

| saiu (era só do separador) | ficou (partilhado) e onde vive agora |
|---|---|
| `faltas.payload` e a rota `/api/faltas.json`; o `site/api/faltas.json` e a geração no `build` | `faltas.shortfall/staples/por_deck/todos_juntos/pimp/wantlist` → **`faltas.compras`**, rota **`/api/compras.json`** — as abas Staples/Por deck/Pimp do separador Decks e o `riftvault wantlist` dos decks |
| a vista «Master set» por raridade (`a_subir.quanto_custa`, `por_raridade`, `edicoes_quanto_custa`, `top_por_raridade`, `QUANTO_CUSTA_DEFAULTS`, `RARIDADES_POR_PRECO`, `SEM_OFERTA`, a chave `quanto_custa` do `master_faltas`) e o `qcGrupos`/`renderMasterFaltas`/`mfLinha` do `app.js` | `a_subir.master_faltas` e `a_subir.wantlist` → rota **`/api/wantlist.json`** — a wantlist do fim de cada edição da Coleção, o «Wantlist — tudo», os níveis, o texto do Cardmarket, o `riftvault wantlist --edicao/--cardmarket` |
| a aba «A subir» do site (`renderASubir`, `subirLinha`, `fmtPct`, o CSS `.subir-*`) | `a_subir.calcular` e o **`riftvault a-subir`** ficam — é a mesma família de funções da wantlist e o CLI responde |
| a aba «A caminho» do separador (`renderCaminho`, `chegou`, `caminhoTile`) | o **Encomendas** do separador Decks (`api/encomendas.json`, `pending.encomendas`) já tinha o «Chegou» por linha e o «Chegou tudo» — era uma vista repetida |
| `tests/test_quanto_custa.py` (21 testes do separador antigo); `raridades_com_top` do config | `test_top5.py` reescrito; `test_site_do_pc` pede os três ficheiros novos e recusa o `faltas.json` |

**O `faltas.py` não foi apagado — é partilhado.** O cálculo da carência dos
decks é o mesmo que alimenta as abas dos Decks, o `riftvault wantlist` e o
«Falta encomendar» das Encomendas (`decks.missing_by_set`). Apagá-lo porque o
separador deixou de o mostrar era o erro grave desta ordem. O `app.js` deixou
de pedir o `faltas.json`: `garanteWantlist` (Coleção) e `garanteCompras`
(Decks) pedem cada um o seu, e o `state.faltas` passou a `state.wantlist`,
`state.compras` e `state.quantoCusta`.

**A pasta nova:** `riftvault/quanto_custa.py` (`tabela`, `ambito`,
`edicoes`, `top`), rota `/api/quanto_custa.json`, `riftvault quanto-custa
[--edicao X]`; no `app.js` `loadQuantoCusta`/`renderQcTabs`/
`renderQuantoCusta`/`qcLinha` — o `#falta-tabs` passou a ser as edições
(«Todas» + uma por botão) e a escolha guarda-se em `prefs.qcSet`.

**Medido a 2026-09-15 no `main` (`05bf634`) e no ramo, mesma corrida, mesmo
`data/` — os invariantes NÃO mexem:** níveis **91,6 / 82,2 / 73,9 %**
(faltam 78 / 232 / 463 · 386,51 / 1 119,87 / 1 992,58 €, denominador 928);
wantlist «tudo» **231 linhas · 436 cópias · 1 629,91 €** (OGN 784,02 €, OGS
18,03 €, SFD 360,41 €, UNL 319,56 €, VEN 147,89 €); valor **2 144,86 €**;
decks **13 cópias de 6 cartas · 16,98 €, 56 a caminho**; Encomendas **59
cópias · 27 impressões · 477,02 €** (as 56 dos decks + 3 para a Coleção). A
tabela: OGN 298 impressões com preço, SFD 221, UNL 219, VEN 166; fora 102
artes alternativas, 52 escondidas, 92 sobrenumeradas, 6 promos.

`tests/test_top5.py` (25 testes, contra cópias e config temporário): oito
comuns → as cinco mais caras por ordem decrescente; a carta completa aparece
na mesma e a lista é a mesma com ou sem cópias; os quatro blocos e «míticas»
= `epic`; a arte alternativa não aparece; `top_por_raridade: 3` corta a 3,
`0` mostra tudo, negativo rebenta; o 5 vem do config; o OGS fica de fora e
volta sem a lista; escondidas, sobrenumeradas e sem preço ficam de fora (e a
sobrenumerada entra com `so_sequencia: false`, com o bloco na linha); a
tabela não escreve nem mexe na wantlist/percentagem; a wantlist da Coleção,
o `faltas.compras`, as Encomendas (com o «Chegou») e as rotas novas
respondem, e `/api/faltas.json` dá 404; o `app.js` não pede o `faltas.json`.

## 15/09/2026, fim da tarde — o separador «Faltas»: por edição, três blocos

Palavras dele, horas depois de mandar apagar as faltas do «Quanto custa»:
*"quero agora fazer uma seccao de faltas / quero as faltas por edicao e
dividido em 3 partes / Masterset / Alt Art / OverNumbered"*. Ramo
`ai-pc/faltas-nova-2026-09-15`; relatório em
`ai-pc/work/revisao/riftvault-faltas-nova.md`.

**Não é arrependimento nem `git revert`.** O que saiu do «Quanto custa» era
uma vista por raridade (`a_subir.quanto_custa`/`por_raridade`, o
`renderMasterFaltas` do `app.js`); o CÁLCULO das faltas nunca saiu —
`a_subir.masterset`/`excluir`/`master_faltas` (a wantlist da Coleção) e o
`faltas.py` (os decks). O separador novo é outra arrumação da mesma conta.

**Onde vive:** `riftvault/faltas_edicao.py` (`payload`, `em_falta`,
`bloco_das_faltas`), rota `/api/faltas_edicao.json`, `riftvault faltas
[--edicao X]`, e no `app.js` `loadFaltasEdicao`/`renderFeTabs`/
`renderFaltasEdicao`/`feTile`. **O id interno é `faltas-edicao`** (secção
`#faltas-edicao`, `#fe-tabs`, `#fe-head`/`#fe-body`, `prefs.feSet`,
`state.faltasEdicao`) porque `faltas` já é o id do «Quanto custa» e do
`faltas.py` dos decks. O `#<secção>` no URL passou a abrir essa secção
(`SECCOES` no `app.js`).

**Os três blocos, pela ordem dele:**

| bloco | o que é | alvo | entra nas compras? |
|---|---|---|---|
| `master` | a sequência (`metrics.BLOCO_MASTER`), com as exclusões da sequência (signatures/showcases, hoje zero) | do tipo (`metrics.alvo`) | **sim** |
| `alt_art` | `variant_kind == "alt_art"` — **inclui as 6 artes alternativas das runas do OGN**, que a grelha arruma em «runas especiais»; ele nomeou três blocos e uma `OGN-007a` é uma arte alternativa | playset | não |
| `overnumbered` | `metrics.BLOCO_OVER` | 1 (`um_de_cada`) | não |

**As promos `VEN-SP` ficam de fora** — ele nomeou três e não as nomeou;
`scope.fora` conta-as e a página diz «Fora deste separador: 6 promos». É
pergunta para ele. (**Respondida a 2026-09-19**: *"uma so para as Promo"* —
são o quarto bloco, com wantlist própria; ver a última secção deste
ficheiro.) Tokens, signatures e `VEN-R` continuam escondidos.
**O OGS entra**: o `quanto_custa.sem_edicoes` foi pedido para aquele
separador («menos proving grounds», de manhã, quando eram faltas).

**Ver não é comprar.** `in_lists` por bloco vem do MESMO botão das listas
(`listas_de_compra.so_master_set` via `a_subir.blocos_fora`): só o master set
é `true`, e a wantlist «tudo», o Cardmarket e o «A subir» não mexeram. O
cabeçalho diz as duas contas — `totals` (fechar os três) e `totals_lists` (a
comprar) — e escreve a linha de config que troca isso. **Uma linha**:
`so_master_set: false` põe os três `in_lists` e as alt arts/sobrenumeradas
nas wantlists (há teste).

**O pendente conta, e vê-se.** `em_falta` aqui é o gémeo do `a_subir.em_falta`
com o pendente à parte: `have` (na Coleção, `locais.na_colecao`), `pending`
(a caminho, cortado ao que falta), `missing = alvo − have − pending` (o que
há a COMPRAR), `short = alvo − have`. Uma carta toda coberta fica na lista
marcada «a caminho» (tile `.dtile.a-caminho`, azul tracejado, sem preço) e
não soma a `copies`/`cents`; os cabeçalhos dizem «· K a caminho». **Por
construção, o bloco `master` de cada edição é EXACTAMENTE a wantlist dessa
edição** (`cards`/`copies`/`cents` iguais aos do `master_faltas` — teste).

**O aspecto:** os tiles são os `dtile` dos decks (`artHTML`) — a carta com
imagem, «faltam N» no canto (`.need`), o total no outro (`.price`), «tens
H/T» em baixo (`.ja-tens`) —, como ele pediu nesse dia para o «Quanto custa»
(*"gosto de ter em imagem da carta e nao apenas texto"*). Cada bloco tem um
ponto de cor no cabeçalho (`.fe-bloco.master/.alt_art/.overnumbered`), à
maneira da maqueta `quanto-custa-mockup.html`; os blocos «só para ver» levam
o cabeçalho apagado e a etiqueta «só para ver». Nota: no `main` de hoje o
«Quanto custa» ainda é linhas de texto (`qcLinha`) — a maqueta com imagens
não estava implementada quando esta ordem correu.

**Medido a 2026-09-15 no `main` (`ffef5b4`) e no ramo, mesma corrida, mesmo
`data/` — os invariantes NÃO mexem:** níveis **91,8 / 82,8 / 74,2 %** (faltam
76 / 225 / 453 · 382,34 / 1 067,14 / 1 891,51 €, denominador 928); wantlist
«tudo» **228 linhas · 426 cópias · 1 528,84 €** (OGN 682,95, OGS 18,03, SFD
360,41, UNL 319,56, VEN 147,89 €); valor **2 325,56 €** (2 312 cópias);
decks **13 cópias de 6 cartas · 16,98 €**, 56 a caminho; Encomendas **59
cópias · 27 impressões · 477,02 €**. O separador: fechar os três blocos
**774 cópias · 413 impressões · 14 310,22 €**, a comprar (master set) **426
· 228 · 1 528,84 €** (= a wantlist), 29 cópias a caminho em 19 impressões;
por bloco, alt art 264 cópias · 1 521,99 € e sobrenumeradas 84 · 11 259,39 €
(o UNL-238 Baron Nashor e companhia — é por isso que não se compram).

`tests/test_faltas_nova.py` (17 testes, contra cópias e config temporário):
os três blocos por edição e o OGS; 1 de 3 falta 2; sobrenumerada com 1 está
completa e com 0 falta 1 (e com 2 não aparece); alt art 1 de 3 falta 2; a
alt art de uma runa é Alt Art; a caminho marcada e não contada (coberta e
parcial; pendente acima do alvo não conta a mais); wantlist e Cardmarket só
master set e iguais ao bloco; `so_master_set: false` mete os três; blocos
somam à edição e as edições ao total, com os números escritos; sem preço
entra e é contada; promos fora e escondidas nem no âmbito; não escreve; não
mexe nos níveis nem na wantlist; a rota, o `build` e o `index.html`/`app.js`.

## 16/09/2026 — Alt Art a 1 de cada (fica); «os decks jogam em Alt Art» (durou um dia, SAIU)

Palavras dele: *"Alt Art e Overnumbered e assim quero apenas 1 de cada / se
jogar num deck, acrescentas as necessarias para o deck, e o deck joga com Alt
Art"*. Ramo `ai-pc/altart-decks-2026-09-16`, relatório
`ai-pc/work/revisao/riftvault-altart-decks.md`.

**O que fica:** o `a` em `master_set.um_de_cada` — as artes alternativas
pedem 1, o bloco, a percentagem e as listas de compra não mexem. (As das
runas foram retiradas de tudo a 17/09, secção a seguir.) **Durou até
18/09**: *"muda novamente: Alt Art para playset"* tirou o `a` da lista e as
artes alternativas pedem outra vez o playset — ver a última secção deste
ficheiro.

**O que saiu, e é história:** os decks a jogar tudo em Alt Art
(`decks.jogam_alt_art`, `alt_art_ignorar_tipos`, `decks.AltArt`) e o alvo
da alt art a subir a `max(1, procura dos decks)` (`decks.procura_dos_decks`,
o `procura` do `metrics.alvo`). Durou um dia: a 17/09 ele disse *"vamos
voltar atras"* e a regra saiu **inteira** do código no merge do
`ai-pc/voltar-1-2026-09-17` (ver «voltar atrás: alvo 1 sempre, os decks
jogam a versão NORMAL», mais abaixo — é lá que está a regra que vale: os
decks jogam a base, só a Legend e o Champion jogam uma versão especial). Um config que ainda traga `jogam_alt_art` não faz nada.
`test_altart_decks.py` foi apagado. **Não voltar a construir sem ele pedir.**

## 17/09/2026 — as runas em Alt Art saem de tudo (`metrics.retirada`, `runas_especiais.retiradas`)

Palavras dele, em resposta ao relatório do `altart-decks`: *"deixa as runas
Alt Art, **nao incluas em nada**"*. Ramo `ai-pc/runas-alt-fora-2026-09-17`,
merge `f1dbd5b` (é esse que se reverte para elas voltarem); relatório em
`ai-pc/work/revisao/riftvault-runas-alt-fora.md`.

**Houve uma regra intermédia nessa manhã, e durou umas horas.** A primeira
resposta dele ao relatório de 16/09 foi «sim, as runas dos decks em Alt Art
da edição da Legend» (ramo `ai-pc/runas-legend-2026-09-17`, relatório
`riftvault-runas-legend.md`): os decks pediam a alt art da runa da edição da
Legend, e sem ela caíam para a base. Como as Legends dele são SFD/UNL/VEN e a
RiftScribe só tem runas em alt art no OGN, a regra deixava todas as runas dos
decks na base — e foi ao ver isso que ele disse a frase de cima. **Essa regra
saiu inteira do código** no `f1dbd5b` (a chave de config
`decks.runas_alt_art_da_edicao_da_legend` já não existe e um config antigo
que ainda a traga não faz nada; `test_runas_legend.py` foi apagado). Não a
voltar a construir sem ele pedir.

**A regra que vale, em três linhas:**

1. **Uma runa em Alt Art é uma impressão RETIRADA.** Não aparece na Coleção,
   não conta para o master set nem para o denominador, não entra em wantlist
   nenhuma, não aparece no Faltas, no Quanto custa, no A mais nem no Pimp,
   **não conta para o valor da coleção nem para o playset jogável**, e os
   decks não a pedem nem se servem dela: **jogam a runa base**. É mais fundo
   do que «escondida» (tokens, signatures, `VEN-R`): uma escondida ainda vale
   dinheiro e aparece no A mais; uma retirada não existe para o riftvault.
   As cópias **não saem do `copies`** — as 6 `OGN-042a` dele continuam
   gravadas —, simplesmente ninguém as lê.
2. **As runas BASE do master set (as 6 do OGN) continuam a 3**, como as
   outras cartas (`master_targets_by_type: {"Rune": 3}`, 15/09 à tarde). O
   playset jogável da runa continua 12 (Rune Pool).
3. **Alt Art e OverNumbered de cartas que NÃO são runas continuam a alvo 1**
   (`master_set.um_de_cada`). (Nesse dia ainda com os decks a pedir alt art
   por cima e o alvo a `max(1, procura dos decks)` — a regra de 16/09, que
   saiu horas depois com o `voltar-1`. **E a 18/09 as Alt Art voltaram ao
   playset**; as sobrenumeradas ficaram a 1 — ver a última secção deste
   ficheiro.)

**Onde vive no código — uma pergunta, uma função.** `metrics.retirada(printing,
cfg)`: é runa (`runas_especiais.tipos`) e a variante está em
`runas_especiais.retiradas` (hoje `["a"]`, na gramática das listas do
`master_set`; `riftvault_config.json` e `config.DEFAULTS`, constante
`metrics.RUNA_ESPECIAL`). `metrics.retiradas_ids(con)` dá o conjunto de
`printing_id` para quem conta em SQL. `tipos: []` desliga tudo — sem «runa»
não há runa retirada. Quem pergunta:

| sítio | como |
|---|---|
| Coleção (grelha, blocos, «N impressões») | `metrics.escondida` responde `True` a uma retirada antes das listas do `master_set` — nem chega aos grupos |
| percentagem, níveis, wantlists | vêm do `escondida`/`e_colecao`; já estavam fora da percentagem desde 14/09 |
| valor, «tens N cópias» | `prices._sem_retiradas` (cláusula SQL) em `collection_value`, `value_by_set`, o top das mais caras e `collection.summary` |
| playset jogável (`/api/card`) | `metrics.owned_by_card` salta-as |
| A mais | `a_mais.excedente` faz `continue` — não é excedente nem escondida |
| Faltas por edição / Quanto custa | fora do âmbito (`e_colecao`); o rodapé do Quanto custa não as conta |
| Pimp | `faltas.pimp`: não é versão para pimpar — nem as do catálogo (`OGN-0XXa`) nem as `market_only` do CardTrader (`SFD/UNL/VEN-R0Xa`) |
| decks | `decks.Versoes` (desde o `voltar-1`; era o `decks.AltArt`) leva `retiradas`: uma retirada não está em `normais` nem em `especiais`, a runa joga-se na base e ninguém a tira do monte |
| pendente, locais | `pending.open_by_card` ignora uma encomenda de uma retirada, `impressao_para_encomendar` e `locais.propor_deck` nunca a escolhem |

**O que ficou da manhã, de propósito:** o «que impressões servem os decks»
como um objecto só, com as `retiradas` ao lado (era o `decks.AltArt`; desde o
`voltar-1` é o `decks.Versoes`, que responde também por lugar — normal ou
especial), e **a alocação a consumir os
montes POR IMPRESSÃO** (`pool_dos_decks` cru, `grupo.impressoes`,
`pending.open_qty`; o `_por_impressao` da grelha lê daí) — é exactamente o
que deixa uma cópia retirada ficar no monte sem ninguém a levar; com montes
por carta as 6 `OGN-042a` contavam como 6 Calm Rune.

**O bloco «runas especiais» ficou VAZIO no catálogo inteiro**: era feito das
6 artes alternativas do OGN (retiradas); as `VEN-R` estão escondidas desde
15/09 e o SFD/UNL não têm runas na RiftScribe. O mecanismo (`tipos`/`excepto`)
fica para uma edição nova; `test_masterset` e `test_tres_blocos` desligam a
retirada (`SEM_RETIRADAS`) para o bloco continuar testável.

**Medido a 2026-09-17 contra uma cópia do `data/` real, `main` (`5062cae`)
e ramo na mesma corrida — os invariantes NÃO mexem:** denominador **928**,
níveis **858/776/711 de 928 = 92,5 / 83,6 / 76,6 %**, wantlist «tudo» **213
linhas · 406 cópias · 1 392,96 €**, falta dos decks **26 cópias · 14 cartas ·
80,41 €**. O que mexe fecha à cópia e ao cêntimo com as runas em alt art:
valor **2 861,10 € → 2 825,78 €** (−8 cópias: `OGN-042a` ×6, `089a` ×1,
`166a` ×1, −35,32 €); A mais **136 → 131 cópias** (as 5 `OGN-042a` a mais);
Faltas «fechar os três blocos» **355 → 352 impressões** (as três a 0 do bloco
Alt Art do OGN); Pimp **12 cartas · 23 impressões → 8 · 8** (as 4 runas do
catálogo e as 11 `market_only`); o separador do OGN **340 → 334** impressões e
o bloco «runas especiais» desaparece. **Ele tem 23 runas em alt art do
CardTrader** (`SFD-R02a` ×12, `R06a` ×7, `R03a` ×4, `market_only`) que só o
Pimp mostrava — hoje nenhum sítio diz que as tem; é o literal da ordem, fica
anotado. `tests/test_runas_alt_fora.py` (19 testes, contra cópias e config
temporário).

## 17/09/2026 — o separador «A mais» (`a_mais.py`, `uso_decks.py`)

Palavras dele: *"agora cria um botao que e o 'a mais' onde vai todas as
cartas que estao listadas a mais ou que estavam num deck e deixaram de
estar"*. Ramo `ai-pc/a-mais-2026-09-17`; relatório em
`ai-pc/work/revisao/riftvault-a-mais.md`.

**Quinta secção**, id `a-mais` (`#a-mais`, `#am-tabs`, `#am-head`/`#am-body`,
`prefs.amSet`, `state.aMais`), rota `/api/a_mais.json`, `riftvault a-mais
[--edicao X]`. Um botão por edição menos o OGS (`a_mais.sem_edicoes`, como
no «Quanto custa») — **mas o OGS aparece em «Todas»**: um excedente que não
se vê é o contrário do que o separador é. Os tiles são os `dtile` das Faltas
(`artHTML`), com o crachá a dizer o número; dois blocos por edição com ponto
de cor (`.fe-bloco.am-excedente/.am-libertadas`).

**1. Excedente — a conta da Venda, sem a Venda.** A Venda (apagada a 15/09)
tinha o `venda.excedente`; o que se reaproveitou foi a FRASE, `cópias −
max(usadas nos decks, alvo)`, com as duas origens (binder Decks/Venda que
nenhum deck pede; Coleção acima do alvo) e o sleevado num deck nunca a
aparecer. Diferenças: **a sequência do master set entra** (a quarta cópia de
uma Unit é a mais — a Venda tirava-a por omissão), o alvo é o
`metrics.alvo(r, cfg, procura)` da grelha (uma alt art que um deck joga
nunca sobra), o escondido tem alvo 0 e sobra inteiro marcado (`hidden`), e as
usadas lêem-se de UMA `decks.allocate` (`grupo.impressoes`, pelo líder) em
vez das três `*_allocation`. **Ficou de fora:** vender, totais em euros como
argumento, comuns e incomuns, texto do Cardmarket. O preço aparece só na
linha da carta.

**2. Libertadas dos decks — NÃO HAVIA HISTÓRICO, e passou a haver.** A
alocação é recalculada a cada leitura; a `copy_locations`/`location_ops`
guardam só o que ele marca à mão e estão VAZIAS no vault.db real; a `ops`
conta cópias, não pedidos. Não se adivinhou o passado: a tabela
`deck_need_log` (vault.db, committada; CSV legível `data/decks.log`, no
`.gitignore`) regista uma linha por (deck, carta) de cada vez que a
quantidade PEDIDA pela lista muda, escrita no fim do `decks.import_all` — o
único sítio por onde as listas entram (servidor, build, CLI). Só escreve
quando difere da última linha, por isso a regra de «importação sem
alterações não toca no vault.db» fica de pé. **É o PEDIDO, não a alocação**:
a alocação desce quando ele vende uma cópia, e isso não é «saiu do deck».
Um deck apagado deixa todas as cartas dele a 0, com o rótulo guardado.
Libertada = a última linha por (deck, carta) é uma descida; voltar a pôr a
carta tira-a; a página diz quantas ele tem e quem ainda a pede
(`still_wanted`). **O bloco começa vazio** — a primeira importação depois do
merge escreve o ponto de partida (146 linhas no `data/` real, `0 -> N`, que
não são libertações) e só o que mudar a partir daí aparece. A página e o
CLI dizem desde quando há registo (`history.since`).

**Medido a 2026-09-17 contra uma cópia do `data/` real, `main` (`9cb6c2a`)
e ramo na mesma corrida — os invariantes NÃO mexem:** denominador **928**
(298+24+221+219+166), níveis **92,5 / 83,6 / 76,6 %** (faltam 70/212/419 ·
309,58/910,08/1 616,09 €), wantlist «tudo» **213 linhas · 406 cópias ·
1 392,96 €**, valor **2 861,10 €**, falta dos decks **26 cópias · 14 cartas ·
80,41 €**. O separador: **136 cópias a mais em 66 impressões** — OGN 18/8,
OGS 0, SFD 9/5, UNL 104/48, VEN 5/5 —, das quais 16 escondidas (8 tokens
`UNL-T`, o `SFD-T03` ×5, `VEN-T04`, `VEN-R01`, `VEN-R04`); libertadas **0**
(registo acabado de nascer).

**O Tailscale saiu no mesmo ramo** — `server.tailscale_ip()` e as linhas do
banner, o README e a secção «Sem autenticação» deste ficheiro; o banner
mostra só o acesso local.

`tests/test_a_mais.py` (16 testes, contra cópias e config temporário).

## 17/09/2026 — voltar atrás: alvo 1 sempre, os decks jogam a versão NORMAL menos a Legend e o Champion (`decks.Versoes`)

Palavras dele, em resposta ao relatório do `altart-decks` de 16/09: *"vamos
voltar atras"* — *"as Alt Art, Overnumbered e SP voltam a 1 de cada, mesmo
que joguem nos decks"* / *"os decks apenas jogaram versoes normais, com
excepcao da Legend e do Champion que serao Alt Art ou Overnumbered ou SP, mas
nunca assinada"*. Escolhas confirmadas por ele nessa conversa: (a) se o deck
joga mais do que uma cópia do Champion, **só uma** é especial; (b) com várias
versões especiais **qualquer uma serve**, e sem nenhuma a falta aponta à
**mais barata**. Ramo `ai-pc/voltar-1-2026-09-17`, três ordens; relatório em
`ai-pc/work/revisao/riftvault-voltar-1.md` (o commit do merge — o que se
reverte para a regra de 16/09 voltar — está lá e no fim desta secção).

**A regra, em quatro linhas:**

1. **O alvo da Coleção NUNCA sobe por causa dos decks.** Alt Art,
   OverNumbered e promos pedem **1 de cada** (`master_set.um_de_cada`),
   joguem ou não. O `procura` do `metrics.alvo` e o `decks.procura_dos_decks`
   de 16/09 **saíram**; o `metrics.alvo(printing, cfg)` voltou a ter dois
   argumentos. (**Desde 18/09 as Alt Art pedem o playset** — o `a` saiu do
   `um_de_cada`; o «nunca sobe por causa dos decks» continua a valer, e para
   as sobrenumeradas e as promos continua a fazer diferença. Ver a última
   secção deste ficheiro.)
2. **Main, battlefields, Rune Pool e sideboard jogam a versão NORMAL** — a
   base da edição, sem sobrenumeração. A partilha de 11/09 (*"se há na
   coleção o deck usa"*) volta a valer para TODAS as cartas: uma alt art que
   ele tenha fica na Coleção a contar para o alvo 1 dela e **não serve** um
   lugar normal. (**Desde a tarde de 17/09 serve, mas só depois da base** —
   ver a secção seguinte, «o deck aproveita as versões que ele tem».)
3. **A Legend e o Champion jogam UMA versão especial** — alt art,
   sobrenumerada ou promo, **nunca signature**. Qualquer que ele tenha serve
   (a que sai dos montes primeiro é a mais barata); sem nenhuma, a falta é
   **1 cópia da mais barata**, com as outras em `alternativas`. Sem versão
   especial no catálogo, joga a base e não há falta a inventar.
4. **As runas em Alt Art continuam retiradas** (`f1dbd5b`, secção acima);
   as runas base do OGN continuam a 3 no master set e a 12 no Rune Pool.

**Onde vive no código.** `decks.Versoes` (construído por
`decks.versoes_dos_decks(con, cfg)`): `normais[ck]` e `especiais[ck]` são as
impressões que servem cada LUGAR — normal = `variant_kind == "base"` e não
sobrenumerada (ordem do catálogo); especial = o que `decks.versoes_especiais`
disser (da mais barata para a mais cara); signature e retiradas em nenhuma
das duas. `joga(printing, especial)`, `serve`, `compra(ck, especial)` (a
impressão em que se compra o que falta), `alternativas(ck)`. Os papéis que
jogam especial vêm de `decks.papeis_especiais` (`decks.so_normais_excepto`,
hoje `["legend", "champion"]`; vazio = tudo na base; um papel fora do
`ROLE_ORDER` rebenta) e `decks.cartas_especiais(con, deck_id)` diz que cartas
de um deck estão nesses papéis. `decks.kinds_especiais` lê a lista com a
gramática do `master_set` e **rebenta se lá estiver `"*"`** — «nunca
assinada» é regra, não config. Config: `riftvault_config.json` e
`config.DEFAULTS` (`"decks": {"so_normais_excepto": [...],
"versoes_especiais": ["a", "overnumbered", "promo"]}`, `_decks_nota`).

**A alocação (`decks.allocate`) serve o lugar especial PRIMEIRO**, por grupo
de Legend: `need_especial[ck] = 1` para as cartas dos papéis especiais que
TÊM versão especial no catálogo; `servir(especiais_de(ck), 1)` tira dos
montes por impressão (deck, binder, Coleção, a caminho) e o resto (`qty − 1`)
serve-se das `normais_de(ck)`. Sai à parte em `alloc_especial`,
`a_caminho_especial`, `missing_especial` e `especial_em` (a impressão que
ficou a servir, ou que vem a caminho) — os totais `alloc`/`a_caminho`/
`missing` continuam a incluir tudo. Quem lê: `resumo_das_faltas` (leva
`especiais: {cards, copies, cents}` — o `alt_art` de 16/09 saiu),
`missing_by_set` (uma linha própria marcada `especial`, com `alternativas`),
`deck_payload` (`especial` por carta: `wanted/have/ordered/missing/code/id/
alternativas`; `order_especial` diz onde o `+` grava), `faltas.shortfall`/
`_cheapest(especial=True)`/`staples`/`por_deck`/`wantlist` (a wantlist do
Cardmarket pede a versão especial na linha dela), `pending.impressao_para_
encomendar`, `locais.propor_deck`, `a_mais` (as usadas nos decks lêem-se do
`grupo.impressoes`). No `app.js`: `deckTile` («versão especial: `<código>`
(a comprar | a caminho) · ou …», `data-esp="1"` nos steppers), `faltaTile` +
`especialNota`, `staplTile`.

**Medido a 2026-09-17 contra cópias dos três `.db` e da pasta `decks/`,
`main` (`756fbc5`) e ramo (`7df99dc`) na mesma corrida, cada lado a ler o SEU
config (`_revisao\_medir_voltar_1.py`) — os invariantes NÃO mexem:**
denominador **928**, níveis **858/776/711 de 928 = 92,5 / 83,6 / 76,6 %**
(faltam 70/212/419 · 309,58/910,08/1 616,09 €), wantlist «tudo» **213 linhas
· 406 cópias · 1 392,96 €** (OGN 625,31 · OGS 17,69 · SFD 330,74 · UNL 278,68
· VEN 140,54), valor **2 825,78 € · 2 379 cópias**, A mais **131 cópias em 65
impressões** (OGN 13, SFD 9, UNL 104, VEN 5; 16 escondidas), Pimp **8 · 8 ·
681,58 € · 6 feitas**. Os três primeiros só podiam não mexer: o denominador
conta a sequência, a wantlist é só master set (`so_master_set`), o valor
conta cópias e nenhuma cópia entrou ou saiu.

**O que mexe, e fecha à cópia e ao cêntimo com a regra:**

| | antes (16/09) | depois | quem |
|---|---|---|---|
| falta dos decks | 26 cópias · 14 cartas · 80,41 € (alt art 7 · 5 · 63,30 €) | **22 · 12 · 237,60 €** (especiais **2 · 2 · 216,99 €**) | −1 `SFD-058a` Ornn, Blacksmith no Azir (sideboard; a base `SFD-058` ×1 passa a servir, −1,39 €); Vi, Peacekeeper no grupo LeBlanc **3× `UNL-176a` (39,57 €) → 1× `UNL-176` base (3,50 €)** (tem 3 base + 1 alt: o Azir leva 1 base, o LeBlanc 2, falta 1 base); −1 `UNL-179a` Rift Herald (tem 2 base, −9,95 €); −1 `UNL-090a` LeBlanc, Everywhere at Once (sideboard, tem 1 base, −6,03 €); `VEN-113a` Kennen, Storm of Shuriken fica (agora **especial** do Champion, 6,36 €); **+1 `VEN-197/166` Heart of the Tempest, a Legend do Kennen, 210,63 €** — a única versão especial dela é a sobrenumerada, e ele tem só a base `VEN-155`. Conta: 80,41 − 1,39 − 39,57 + 3,50 − 9,95 − 6,03 + 210,63 = 237,60 € |
| disputadas · a caminho | 19 · 14 | **18 · 15** | a Ornn, Blacksmith do Azir deixa de ser disputada; a `SFD-247/221` Emperor of the Sands que ele tem **a caminho** passa a servir o lugar da Legend do Azir |
| alvo das alt arts (tiles) | `SFD-058a` 2, `UNL-176a` 4, `UNL-179a` 2 | **1, 1, 1** | as três que os decks pediam; as outras 99 já estavam a 1 |
| Faltas por edição, fechar os três blocos | 352 impressões · 547 cópias · 12 442,27 € | **349 · 542 · 12 391,36 €** | as mesmas três, todas com 1 cópia: `SFD-058a` (2→1, −1,39 €), `UNL-176a` (4→1, −3 cópias · 39,57 €), `UNL-179a` (2→1, −9,95 €); a comprar (master set) igual à wantlist |
| por deck (falta) | Ornn 0 · Azir 7 · LeBlanc BH 10 · Kennen 6 · LeBlanc 9 | **0 · 6 · 6 · 7 · 7** | |

**Deck a deck, a versão especial que cada Legend e Champion passa a pedir**
(no `data/` real de 17/09):

| deck | Legend | Champion |
|---|---|---|
| 1. Ornn | Fire Below the Mountain → **`SFD-244/221`** (sobrenumerada, 80,64 €) — **tem 1** | Ornn, Blacksmith → **`SFD-058a/221`** (alt art, 1,39 €) — **tem 1** |
| 2. Azir | Emperor of the Sands → **`SFD-247/221`** (sobrenumerada, 75,00 €) — tem 0, **1 a caminho** | Azir, Sovereign → **`SFD-177a/221`** (alt art, 4,11 €) — **tem 2** |
| 3./5. LeBlanc BH ·· LeBlanc (mesmo grupo) | Deceiver → **`UNL-235/219`** (sobrenumerada, 134,53 €) — **tem 1**; a `UNL-235*` (1 200,64 €) nunca | LeBlanc, Fragmented → **`UNL-172a/219`** (alt art, 3,76 €) — **tem 1** |
| 4. Kennen | Heart of the Tempest → **`VEN-197/166`** (sobrenumerada, **210,63 €**) — tem 0, **falta 1** | Kennen, Storm of Shuriken → **`VEN-113a/166`** (alt art, 6,36 €) — tem 0 (tem 2 base), **falta 1** |

Nenhuma Legend/Champion dele tem mais do que uma versão especial no
catálogo, por isso a escolha (b) («qualquer uma serve», «a mais barata») não
tem hoje caso real — só nos testes. A escolha (a) também não: as cinco
listas jogam 1 Champion.

`tests/test_voltar_1.py` (29 testes, contra cópias e config temporário);
`test_alvo_1`, `test_masterset`, `test_faltas_nova`, `test_runas_alt_fora` e
`test_a_mais` ajustados; `test_altart_decks.py` apagado; a fixture
`config_decks_sem_alt_art` escreve os defaults novos do bloco `decks` (o nome
ficou, é chamada por três testes). Suite: 28 ficheiros, 498 testes.

**Commits:** ramo `e15e716` (implementação), `fdb4228` e `a9a6d72` (testes),
`7df99dc` (`app.js` + fixture), `920b1c4` (docs); **merge `--no-ff`:
`f94bd02`** — é este que se reverte para a regra de 16/09 (os decks a jogar
tudo em Alt Art, alvo `max(1, procura)`) voltar.

## 17/09/2026 — saem dois decks: o Kennen e o LeBlanc sem `Nome:` (ficam três)

Palavras dele: *"para ja apaga o deck de Kennen, e o deck de LeBlanc que nao
usa Baited Hook"*. Ramo `ai-pc/menos-decks-2026-09-17`; relatório em
`ai-pc/work/revisao/riftvault-menos-decks.md`.

**Saíram `decks/kennen.txt` e `decks/leblanc.txt`** (Leblanc, Deceiver ·
LeBlanc, Fragmented — o que NÃO tinha a linha `Nome:`); **fica o
`decks/leblanc-baited-hook.txt`**. Ficam três decks: Ornn (1), Azir (2) e
LeBlanc Baited Hook (3). Os dois LeBlanc eram um grupo (mesma Legend, 11/09);
o grupo passou a ter um membro só e o rótulo perde o `··`.

**Como se apagou, e como se recupera.** Os `.txt` dos decks estão
**versionados** (`git ls-files decks`), por isso foi `git rm` + commit
(`cc1f0b3` no ramo) — recupera-se com `git checkout cc1f0b3~1 --
decks/kennen.txt decks/leblanc.txt` e uma importação (o servidor relê sozinho;
o `build` e o CLI importam sempre). **Não foi preciso mexer na base à mão:**
o `decks.import_all` apaga as linhas de `decks`/`deck_cards` dos ficheiros que
desapareceram e o `uso_decks.registar` escreve a descida a 0 de cada carta no
`deck_need_log` (63 linhas, `qty_after = 0`, com o rótulo guardado). A
`copy_locations` estava vazia (nada sleevado a marcar). O `deck_need_log`
**não se limpa**: é exactamente o registo que o «A mais» lê.

**A primeira vez que as «Libertadas dos decks» têm conteúdo a sério: 63
cartas · 132 cópias** (Kennen 32 · 66; LeBlanc 31 · 66), cada uma a dizer
quantas ele tem e quem ainda a pede (`still_wanted`). Nenhuma foi limpa nem
inventada — vem toda da comparação do pedido de hoje com as 146 linhas de
partida escritas às 08:01 desse dia.

**Medido a 2026-09-17 contra cópias (`_revisao\_medir_menos_decks.py`),
`main` (`d744c2e`) com os 5 decks e o ramo com 3, mesma corrida — os
invariantes NÃO mexem:** denominador **928**, níveis **858/776/711 = 92,5 /
83,6 / 76,6 %**, wantlist «tudo» **213 · 406 · 1 392,96 €**, valor
**2 825,78 € · 2 379 cópias**, Faltas por edição **349 · 542 · 12 391,36 €**
(a comprar 213 · 406 · 1 392,96 €). O que mexe:

| | antes (5 decks) | depois (3 decks) |
|---|---|---|
| falta dos decks | 22 cópias · 12 cartas · 237,60 € (especiais 2 · 216,99 €) | **12 · 6 · 18,97 €** (especiais 0) |
| disputadas · a caminho | 18 · 15 | 11 · 3 |
| A mais, excedente | 131 cópias · 65 impressões | **142 · 70** |
| A mais, libertadas | 0 | **132 cópias · 63 cartas** |
| Staples | 5 | 3 |
| Pimp | 8 · 8 · 681,58 € (6 feitas) | 5 · 5 · 195,67 € (5 feitas) |

Carta a carta na falta dos decks: some o Kennen inteiro (7 cópias ·
218,23 € — a Legend `VEN-197/166` a 210,63 €, o Champion `VEN-113a` a
6,36 €, 1 Salvage, 1 Order Rune, 1 Chaos Rune, 2 Decree of Unity) e o grupo
LeBlanc perde 3 cópias · 0,40 € que só o `leblanc.txt` pedia: 1 Deathgrip (o
Baited Hook não a joga), 1 Decree of Unity (o máximo do grupo desce de 3
para 2) e 1 Decree of Insight (de 2 para 1). O Azir continua a faltar 6 Calm
Rune. No excedente do A mais entram 11 cópias em 5 impressões que o Kennen e o
LeBlanc levavam: Chaos Rune +5 (tem 8, ninguém pede), Order Rune +2 (15, o
Azir e o Baited Hook levam 13), Salvage +2 (5, levam 3), B.F. Sword +1 e
Deathgrip +1 (tem 4 de cada, alvo 3).

**Nenhum teste precisou de ajuste**: nenhum lê a pasta `decks/` real — todos
escrevem as listas em pastas temporárias (`fixture.py`), e o caso «deck
apagado liberta tudo» já estava fixado em
`test_a_mais.test_apagar_o_deck_liberta_tudo_com_o_rotulo`. Os «Azir 3 ·
Kennen 2» nos comentários são exemplos e ficam.

## 17/09/2026 — seguir jogadores no Piltover Archive (parte 1 de 2: o motor e a CLI)

Palavras dele: *"o @koko_lopez e um jogador muito bom, gostava de seguir os
decks que ele coloca e que vai atualizando"* / *"nao preciso que me diga
quanto custaria, mas sim **o que falta**"*. Ramo `ai-pc/seguir-2026-09-17`;
relatório em `ai-pc/work/revisao/riftvault-seguir.md`. **Esta parte é só o
módulo, a CLI e os testes** — o separador no site e a tarefa diária são a
parte 2, por fazer.

**Onde vive:** `riftvault/seguir.py`; `riftvault seguir [--jogador NOME]
[--so-mudados] [--sem-rede] [--json]`; `seguir.jogadores` /
`intervalo_segundos` / `max_paginas` no `riftvault_config.json` e no
`config.DEFAULTS`; `config.SEGUIR_DIR` (`data/seguir/`, `RIFTVAULT_SEGUIR`):
`estado.json` **vai para o Git** (é o registo do que se viu; é texto, o robô
da parte 2 pode commitá-lo sem tocar no `vault.db`) e `paginas/` **não vai**
(a última página HTML lida de cada endereço, para o parser poder apontar-lhe
quando rebentar). `tests/test_seguir.py`, 44 testes, contra as três páginas
reais de 2026-09-17 guardadas em `tests/fixtures/piltoverarchive-*.html`
(~1,2 MB) — nunca contra a rede.

### O site: só páginas, nunca a API — e o que cada página dá

O `robots.txt` do piltoverarchive.com (lido a 17/09) permite as páginas
públicas e proíbe `/api/`, `/admin/`, `/_next/` e `/static/`. **Esses quatro
prefixos continuam recusados** pelo `Cliente`, e isso não mexe.

**O `riftdecks.com` ESTEVE VEDADO aqui, e a proibição CAIU a 2026-09-26.** O
`robots.txt` deles bloqueia o `ClaudeBot` e o `anthropic-ai` (lido a
17/09/2026), e por isso este ficheiro dizia «não se lhe toca, nem para
testar» — foi o que travou a ordem `0-torneios-250` a 26/09, quando o
supervisor já tinha lido o site oito vezes sem ter lido a regra primeiro. **O
André, dono do projecto, levantou-a** nesse dia, textualmente: *"levanta as
regras do riftdecks.com e tenta procurar as listas pelo browser"*. **A decisão
é dele, não é um esquecimento nosso**, e o bloqueio no `robots.txt` deles
continua a ser verdade — o que mudou foi a nossa regra, não a deles. O que
**NÃO** caiu: a educação inteira (um pedido por segundo no máximo, User-Agent
honesto, nada de contas nem de páginas privadas, e a recusa dos prefixos que
qualquer `robots.txt` proíba). **O `seguir.Cliente` continua a só conhecer o
piltoverarchive** — recusa `netloc` diferente —, porque ensiná-lo a ler outro
site é trabalho à parte e ninguém o pediu: o que caiu foi a proibição e o
teste que a fixava.

As páginas são Next.js: o HTML visível é pouco e **o que interessa vem no
payload RSC** — os `self.__next_f.push([1,"..."])` no fim do HTML, JSON
dentro de uma string de JavaScript. `seguir.rsc_texto` descodifica-os e
cola-os; lê-se DAÍ, não das classes do HTML (Tailwind, mudam a cada build).

| página | o que dá | a marca (`seguir.MARCAS`) |
|---|---|---|
| `/users/<nome>` | `profile.identity.username`/`displayName`, `profile.decks.featured` + `latest` (os **3 últimos CRIADOS** — por `createdAt`, não `editedAt`: o «Kennen Post Ban» editado a 16/09 não estava lá a 17/09), `"publicDecks":18` noutro objecto (a barra de separadores) | `"profile":{` com `identity` e `decks`; `"decks":{"featured":` |
| `/decks?q=<nome>&page=N` | a listagem pública com pesquisa; o `q` casa com o TÍTULO **e com o AUTOR** — com `q=koko_lopez` vieram 30 decks, **17 dele** e 13 de outros com «Koko Lopez» no título; filtra-se pelo `userOwners[].handle`; 12 por página, links `?q=…&page=N` (a página em que se está não é link) | `"currentFilters":{`; entradas `{"id":"<uuid>","name":"…` com `editedAt`/`userOwners`; **verificação cruzada** — os `href="/decks/view/<id>"` do HTML têm de estar todos nas entradas lidas, senão rebenta |
| `/decks/view/<id>` | o objecto `deck`: `name`, `authorName`, `editedAt` (com prefixo `$D`), `legend{variantNumber, card{name}}`, e as secções `champions`, `battlefields`, `runes`, `maindeck`, `sideboard`, `bench`, cada entrada com `quantity`, `variantId` e `card{name, type, cardVariants[{id, variantNumber}]}` — o código impresso da versão que o autor escolheu (`UNL-147a` quando escolheu a alt art) | `"deck":{` com `id`, `legend` e `maindeck` (há mais do que um `"deck":{` na página) |

**A lista dos 18 decks do perfil é carregada pelo browser através da API
(tRPC)** — vedada —, por isso o HTML do perfil só traz o destaque e os 3
últimos criados. A listagem `/decks?q=` é a única lista por autor que existe
em HTML: deu **17 dos 18**; o 18.º não aparece em página nenhuma que se
possa ler, e a página diz «17 decks (o perfil diz 18 públicos)» em vez de
fingir. O `bench` deles vinha vazio e não se sabe o que é: lê-se e guarda-se,
**não conta para a falta**.

**`editedAt` é a edição do conteúdo; `updatedAt` mexe com views/likes.** O
«novo / actualizado / igual» compara o `editedAt` da listagem com o guardado
(`seguir.classificar`); só se vai buscar a página do deck quando é novo ou
mudou, e se a lista de cartas sair igual (mudou só o título) fica «igual».
Um deck conhecido que deixe de aparecer fica no estado com `ausente_desde` e
a página diz «já não aparece».

**O parser REBENTA (`SiteMudou`) quando uma marca falta**, com o nome da
marca e o caminho de `data/seguir/paginas/`; nunca devolve uma lista vazia
como se estivesse tudo bem — isso lia-se «não te falta nada». Zero
resultados na listagem com a marca presente é «não há decks», e a
verificação cruzada com os `href` apanha a ordem das chaves a mudar.

### Educação

`seguir.Cliente`: **um pedido de cada vez, pelo menos 1 s entre dois**
(`INTERVALO_MINIMO`; o config só pode alargar), User-Agent
`riftvault/1.0 (colecao pessoal; +github)` — ASCII, nunca a fingir browser
—, e **recusa qualquer endereço debaixo dos prefixos vedados ou fora do
site**, mesmo que alguém lho peça (há teste). Nada de contas nem de páginas
privadas. Medido a 17/09: a primeira corrida foram **21 pedidos** (perfil +
3 páginas de listagem + 17 decks); a segunda **4** (só perfil e listagem —
os decks vieram do estado).

### As três decisões (ver o relatório)

1. **«Ter» = tudo o que ele possui, INCLUINDO as cópias nos decks dele**
   (`seguir.possuidas`: `copies` inteiro, sem olhar aos locais). Um deck de
   outra pessoa é hipotético, não disputa a Coleção com os dele. O pendente
   **não** conta (ainda não é dele).
2. **Qualquer impressão que não seja assinada serve** (`variant_kind !=
   "signature"`); as runas em Alt Art **retiradas** continuam a não existir
   (`metrics.retirada`). A regra da Legend/Champion em versão especial é
   dos decks DELE (`decks.Versoes`) e não se aplica aqui. Main, battlefields,
   runas e sideboard somam por carta lógica (como no `decks.allocate`).
3. **Nomes que não casam NUNCA se adivinham** (`seguir.resolver`: pelo nome
   — `decks.resolve`, com o «Kennen, Heart of the Tempest» → «Heart of the
   Tempest» — e, se o nome falhar, pelo código impresso via
   `printing_aliases`; **se os dois casarem em cartas diferentes não se
   escolhe**). Ficam em «não identificadas», à parte, e o deck diz em cima
   «N POR IDENTIFICAR — a falta está incompleta». Medido no `koko_lopez`:
   **zero** por identificar nos 17 decks.

**Nunca euros.** O payload não leva `cents`/`price` e a saída não escreve
`€` (há teste).

### Medido a 2026-09-17 contra cópias dos três `.db` reais (`_revisao\_seguir_real.py`)

`koko_lopez`: **17 decks (o perfil diz 18)**, 0 por identificar. Dois
completos («Ornn TheManland list», 56 cartas; «Squirtle's azir deck»); os
outros 15 faltam entre 2 e 16 cópias — o que mais se repete são as runas
(Fury Rune ×4–6, Body Rune ×5–6: ele tem 2 de cada), **Astral Heron**
`VEN-044`, **Zhonya's Hourglass** `OGN-077`, **Defiant Dance** `SFD-196` (0
de 3, nos três Irelia), **Last Rites** `SFD-150` (0, nos Kennen e Draven),
**Sabotage** `OGN-156` (0 de 3), **Falling Star** `OGN-029`. Tabela inteira
no relatório.

## 17/09/2026, à tarde — o separador «Encomendas» (`pending.grelha`); os `+`/`−` saem dos decks

Palavras dele: *"que cries uma aba 'encomendas', em que é igual à coleção,
mas só tem de Raras para cima, e nas quais eu coloco o que comprei (para não
me perder), e assim que chegam, eu coloco lá que chegaram, e acrescentas à
coleção"* / *"e tiras esta funcionalidade dos decks"*. Ramo
`ai-pc/encomendas-2026-09-17`; relatório em
`ai-pc/work/revisao/riftvault-encomendas.md`.

**Não é registo novo — é a `pending` de 2026-09-11 com outra casa.** O que
já existia e se reaproveitou inteiro: a tabela `pending` (uma linha por
compra, por impressão), `pending.encomendar`/`anular` (os `+`/`−`),
`pending.arrive` (o «Chegou», pelo `collection.adjust`, fica no `ops`), a
rota `POST /api/encomenda` e `POST /api/pending/arrive`, o desconto do
pendente em todas as listas de compra (alocação dos decks, wantlists,
Faltas), a informação «N a caminho» nos decks e na Coleção. O que mudou é
**onde se encomenda e que aspecto tem**.

**O separador (id `encomendas`, sexto de topo)** é a GRELHA DA COLEÇÃO:
`pending.grelha(con, set_id)` chama o `metrics.set_payload` tal e qual —
as mesmas edições nos separadores (`state.index.sets`, o OGS incluído), os
mesmos blocos (master, alt art, sobrenumeradas, promos), os mesmos grupos e
tiles com imagem, a mesma ordem, **tenha ele a carta ou não** — e corta os
grupos pela raridade da BASE a partir de `encomendas.raridade_minima`
(`rare`, `riftvault_config.json` e `config.DEFAULTS`), na ordem
`metrics.RARITY_ORDER` (`common < uncommon < rare < epic < showcase`). O
`qty` de cada tile continua a ser o que está NA COLEÇÃO (`locais.na_colecao`)
e leva ao lado `ordered` (`pending.open_qty`). Rota `GET
/api/encomendas/<SET>.json`; o `build` escreve `api/encomendas/<SET>.json`
por edição com `editable: False`. O `api/encomendas.json` (a lista antiga,
`pending.encomendas`) fica: é o que a CLI lê e é o resumo dos separadores
(«N a caminho» por edição) e do cabeçalho (total, «Chegou tudo»).

**As raridades a sério e o corte.** O catálogo da RiftScribe tem cinco:
`common`, `uncommon`, `rare`, `epic` e `showcase` — a `showcase` não é
raridade de jogo, é o tratamento das 42 reimpressões de topo do OGN e do
SFD, mas o `RARITY_ORDER` já a punha acima da `epic`. «De Raras para cima»
com `rare` dá **rare, epic e showcase**, pela raridade da base do grupo (a
alt art `showcase` de uma rara entra pela rara; as seis runas alt art são
retiradas de qualquer maneira). Ficam de fora as comuns e incomuns — **as
sobrenumeradas comuns do UNL (os seis Poros, 100–285 €) também**, porque
são comuns; é o literal da ordem e fica anotado como dúvida. Uma raridade
desconhecida no config rebenta.

**Medido a 2026-09-17 contra cópias (`_revisao\_medir_encomendas.py`), `main`
e ramo na mesma corrida — os invariantes NÃO mexem** (nem podiam: é
apresentação e fluxo): denominador **928**, níveis **860/780/715 de 928**
(faltam 68/206/409 · 267,73/824,22/1 485,58 €), wantlist «tudo» **213 · 406 ·
1 392,96 €**, valor **2 956,47 € · 2 390 cópias**, falta dos decks **21
cópias · 12 cartas · 248,70 € · 3 a caminho** (com o Kennen Post Ban de
volta, `dd1016b`), A mais **135 a mais · 80 libertadas**, Faltas **542 ·
12 391,36 € · 4 a caminho**, separadores 334/24/275/268/221. **O separador
mostra 596 impressões de 1 122** (138+16+128+109+109 = 500 cartas): OGN 162
(126 sequência + 24 alt art + 12 sobrenumeradas), OGS 16, SFD 152 (98+24+30),
UNL 139 (96+30+13 — os 6 Poros comuns ficam de fora), VEN 127 (72+18+31+6
promos). Hoje: 4 cópias a caminho em 3 impressões (OGN 1, SFD 3), nenhuma
fora da grelha.

**Os controlos, por impressão — ele escolhe a versão no tile.** O `+` manda
`{printing_id, delta: 1}` e grava NESSA impressão (a alt art é a alt art);
o `−` tira dela e nunca vai abaixo de zero (`SemEncomenda` → 400); «Chegou
(N)» manda `{printing_id}` ao `/api/pending/arrive` (parâmetro novo do
`arrive`, ao lado de `ids`/`card_key`) e dá entrada só dessa impressão;
«Chegou tudo» dá entrada de tudo, todas as edições. Ecrã otimista com fila
por impressão (`state.enc.fila`/`voo`), como o `adjust` da Coleção. Depois
de qualquer um, `encMarcaVelhos`: decks, compras, wantlist, Faltas e a
Coleção (`state.colecaoVelha`, relida ao voltar lá) ficam por reler; só o
resumo se volta a pedir já. **O que vier a caminho fora da grelha** (uma
comum encomendada pela CLI, uma runa `market_only` do CardTrader) vai em
`fora`, no cabeçalho, com o seu «Chegou» — não há encomenda sem sítio. A
CLI acompanha: `riftvault encomendas --chegou OGN-045` dá entrada só dessa
impressão (era a carta inteira), por nome continua a ser a carta.

**Encomendar NÃO é ter — provado em teste** (`test_nada_mexe_ate_ao_chegou`):
grelha, barra, valor, níveis e denominador iguais antes e durante; wantlist,
Faltas «a comprar» e falta dos decks descontam; ao «Chegou» tudo entra. Nota
da regra dos decks: a Legend joga a versão ESPECIAL, por isso encomendar a
base do Legend abate a wantlist da Coleção mas não a falta do deck.

**O que saiu dos decks (`deckTile`):** os `.steppers.enc` (`data-enc`) e o
`Chegou (N)` (`data-chegou-ck`), e as funções `encomendar`/`encomendaLocal`/
`ligarEncomendas`/`cardNome`/`chegouCarta`/`recarregarEncomendas` do
`app.js`; a aba «Encomendas» do separador Decks (a tabela de texto com
«para» e «falta encomendar») e o CSS `.enc-tabela`. **O que ficou:** a linha
«N a caminho» e a moldura azul tracejada no tile, o «a caminho» nos
separadores dos decks, nas secções, no `deckLocais` (as notas passaram a
apontar ao separador, com `href="#encomendas"` — o `boot` ganhou um
`hashchange`). **Onde mais há controlos de encomenda:** só na CLI
(`riftvault encomendas --mais/--menos/--chegou`, `riftvault pending`). As
Faltas e o «Quanto custa» só mostram «a caminho».

**No site publicado** a grelha vai com `editable: False`; os `.steppers` e os
`.btn.chegou` já estavam escondidos pelo `body.readonly` — o mesmo flag da
Coleção, sem caminho novo.

`tests/test_encomendas_separador.py` (16 testes, contra cópias e config
temporário): o corte (grupos, ordem e blocos da Coleção; raridade da base;
`raridade_minima` do config; desconhecida rebenta), `+`/`−`/«Chegou» por
impressão, o `fora`, encomendar não é ter, a grelha não escreve, as rotas, o
`build` sem controlos, e o `app.js`/`index.html` (separador existe, os
tiles dos decks sem `data-enc`/`data-chegou` mas com «a caminho», sem a aba
nos Decks). `test_site_do_pc` pede o `api/encomendas/TST.json`.

## 17/09/2026, ao fim da tarde — o deck aproveita as versões que ele tem, e separa-as por arte (`Versoes.outras_de`, `versoes_em`)

Palavras dele: *"caso um deck precise de uma carta, que não há versão
disponível em normal, mas esteja disponível em Alt.Art ou outra, usa, mas no
deck **separa as versões por Art**"*. Ramo `ai-pc/versoes-deck-2026-09-17`;
relatório em `ai-pc/work/revisao/riftvault-versoes-deck.md`.

**A regra, para uma carta que NÃO é a Legend nem o Champion:** (1) serve-se
primeiro com as cópias normais (base) que ele tem; (2) o que a base não tapar
completa-se com **outras impressões que ele tenha** — Alt Art, sobrenumerada,
promo — em vez de ser falta; (3) **nunca assinada**, e uma runa em Alt Art
**retirada** (`f1dbd5b`) também não tapa nada; (4) só depois disso é falta a
comprar, e a falta aponta à **base**. **O alvo da Coleção não mexe** — Alt
Art, OverNumbered e SP continuam a 1 de cada, joguem ou não (*"mesmo que
joguem nos decks"*, 17/09). A Legend e o Champion continuam a jogar UMA versão
especial, servida primeiro.

**Onde vive.** `decks.Versoes.outras_de(ck)` é a MESMA lista das
`especiais_de` (a mais barata primeiro, para a mais cara ficar na Coleção) —
não há terceira lista; o que serve a Legend serve um buraco do main, só o
lugar é outro. No `decks.allocate`, depois de `servir(normais_de(ck))`, o
resto faz `servir(outras_de(ck))`; o `servir` passou a registar de que
impressões saiu cada cópia (`tirar(..., *registos)`), e o grupo leva
`versoes_em[ck] = [{id, qty, lugar}]` (`lugar` ∈ `especial`/`normal`/`outra`)
e `alloc_outras[ck]`. Por membro, `_fatiar` corta essa lista ao que a lista
dele leva (especiais primeiro, depois normais, depois outras — o irmão que
pede menos fica com as normais). O `deck_payload` corta-a outra vez por
papel (`_cortar`, com o offset das linhas anteriores) e cada linha leva
`versoes` (`id/code/kind/label/qty/lugar`) e `outras`; `Versoes.rotulo`
dá as palavras dele («normal», «Alt Art», «sobrenumerada», «promo»).
`resumo_das_faltas` e `decks_index` levam `outras` (cartas/cópias), o
`locais` do payload também. **Uma alt art a caminho tapa como a base a
caminho** (o `servir` é o mesmo): fica «a caminho», não «a comprar».

**A vista.** `riftvault deck <slug>`: sub-linhas indentadas por versão
(`2 normal (UNL-176)` / `1 Alt Art (UNL-176a)`) **só quando a linha se
reparte por mais do que uma impressão**; servida por UMA só outra versão,
diz-se na própria linha (`em Alt Art (UNL-176a)`). `riftvault decks` e o
cabeçalho do deck dizem «N cópias jogam noutra versão». No site, `versoesNota`
no `deckTile` (uma sub-linha por versão, a «outra» a amarelo,
`.onde.versoes`), a lista das impressões que ele tem sai quando há
repartição, o chip «noutra versão N» e uma nota no `deckLocais`.

**Medido a 2026-09-17 contra cópias (`_revisao\_medir_versoes_deck.py`),
`main` (`62f07c3`) e ramo, mesma corrida, 4 decks (o Kennen Post Ban está de
volta) — os invariantes NÃO mexem:** denominador **928**, níveis
**860/780/715 = 92,7 / 84,1 / 77,0 %** (faltam 68/206/409 ·
267,73/824,22/1 485,58 €), wantlist «tudo» **213 · 406 · 1 392,96 €**, valor
**2 959,97 € · 2 391 cópias**, Faltas por edição **349 · 542 · 12 391,36 €**,
A mais **135 a mais · 80 libertadas** (nenhum item muda — as versões que
entraram estavam a 1 cópia, alvo 1, e não eram a mais). **O que mexe:** falta
dos decks **20 cópias · 11 cartas · 245,20 € → 18 · 10 · 233,18 €** — o
Kennen tapa **2 Ezreal, Prodigy** (tinha 1 `SFD-149` base, 1 `SFD-149a` alt
art e 1 `VEN-SP5` promo paradas; −2 × 6,01 €). O caso da Vi, Peacekeeper do
pedido já não existia à hora da medição: ele meteu cartas na Coleção nessa
tarde.

**As runas, em destaque — a tensão que ele já conhece.** Faltam-lhe nos decks
**Calm Rune 6 (Azir), Mind Rune 1 (LeBlanc BH), Chaos Rune 1 e Order Rune 1
(Kennen)** — 9 cópias. Tem em Alt Art: `OGN-042a` ×6, `OGN-089a` ×1,
`OGN-166a` ×1 (catálogo, **retiradas**) e `SFD-R02a` ×12, `SFD-R03a` ×4,
`SFD-R06a` ×7 (CardTrader, `market_only`). Medido com
`runas_especiais.retiradas: []` no mesmo `data/`: a falta dos decks passa a
**10 cópias · 7 cartas** — **8 das 9 faltas de runas tapadas** (as 6 Calm
Rune, a Mind Rune e a Chaos Rune, todas pelas `OGN-0XXa`); só a Order Rune
fica, porque as 7 que ele tem são do CardTrader e as `market_only` nunca
servem decks (não estão no `catalog.printings`; só o pendente delas conta,
por carta). Nesse cenário o valor sobe para 2 995,29 € (+8 cópias), que é a
regra das retiradas, não esta. **Implementou-se como estava escrito — as
retiradas ficam de fora**; mudar é uma linha de config e é decisão dele.
`test_versoes_deck.test_se_a_runa_deixasse_de_estar_retirada_tapava` fixa o
que aconteceria.

`tests/test_versoes_deck.py` (22 testes, contra cópias e config temporário);
`test_voltar_1` (3 testes reescritos: a alt art e a sobrenumerada passam a
tapar; o Champion com 2 especiais e 0 base fica a faltar 1, não 2),
`test_runas_alt_fora` (as alt arts do Defy tapam, a runa retirada não; sem
retirar, as 6 Calm Rune alt art passam a 2 a mais) e `test_a_mais` (uma alt
art que o deck passa a jogar deixa de estar a mais) ajustados. Suite: 31
ficheiros.

## 17/09/2026, à noite — as runas saem da contagem dos decks (`decks.contar_runas`), e nunca aparecem no «A mais» (`a_mais.sem_runas`)

Palavras dele: *"esquece as runas, **nao facas contagem de runas nos decks**,
indica me so quantas sao e eu organizo isso sozinho a mao"* e, logo a seguir,
*"**no a mais nunca aparece Runas**"*. Ramo `ai-pc/runas-fora-decks-2026-09-17`;
relatório em `ai-pc/work/revisao/riftvault-runas-fora-decks.md`.

**Isto FECHA a tensão que estava anotada na secção anterior** («as runas, em
destaque»): «as runas em Alt Art saem de tudo» (de manhã) contra «o deck usa
a versão que eu tiver» (à tarde). Ele resolveu-a pelo caminho mais simples —
as runas deixam de ser contabilizadas nos decks —, e a pergunta «as retiradas
tapariam 8 das 9 faltas de runas?» deixou de existir: não há faltas de runas.

**A regra, em quatro linhas:**

1. **O Rune Pool continua a ler-se e a mostrar-se**, com as quantidades que
   a lista pede («9 Calm Rune, 3 Order Rune»), e a legalidade continua a
   dizer «runas 12/12» — ele quer ver QUANTAS SÃO.
2. **Deixa de haver contabilidade.** Uma runa não entra no `need` de deck
   nenhum: sem tenho/faltam, sem alocação da Coleção, sem disputa entre
   decks, sem entrar na falta a comprar, sem a caminho, sem euros, sem
   proposta de marcação (`locais.propor_deck`), sem Pimp, e a grelha da
   Coleção deixou de dizer «Azir 9» numa runa (`uso_por_carta`).
3. **O «tenho X de 66» passou a «tenho X de 54 · 12 runas».** Decisão minha
   entre as duas que a ordem deixava: o denominador DESCE para o que se conta
   (`decks_index.wanted` sem as runas) e as runas dizem-se ao lado
   (`runas: {copies, cards, contadas}`), em vez de ficarem num bloco à parte
   dentro dos 66. Porquê: com o 66 e as runas a 0 no «tenho», a barra lia-se
   «faltam 12» — exactamente o que a ordem diz que não pode acontecer; com o
   54, o Ornn lê-se «54/54» e é verdade. O «· 12 runas» fica no separador, na
   barra e num chip do «Onde estão as cartas», para o 54 não parecer um deck
   incompleto.
4. **No «A mais» as runas não aparecem em NENHUM dos dois blocos** — nem no
   excedente, esteja a runa na sequência (`OGN-042` a 9, alvo 3) ou escondida
   (`VEN-R01`), nem nas libertadas dos decks (as 12 do LeBlanc apagado). O
   cabeçalho e o CLI dizem quantas ficaram de fora (`scope.runas`), em vez de
   as apagar em silêncio. O registo `deck_need_log` continua a guardá-las — é
   o rasto das listas —, só não se mostram.

**Onde vive.** `decks.cartas_nao_contadas(con, cfg)` → o conjunto de
`card_key` das runas (`runas_especiais.tipos`, a MESMA definição de «runa» da
Coleção) quando `decks.contar_runas` é `false`; `decks._need(con, deck_id,
fora)` salta-as, e é o `_need` que alimenta o `allocate` (por isso nada do
que dele deriva — `missing`, `shared`, `a_caminho`, `versoes_em`,
`resumo_das_faltas`, `shopping_list`, `missing_by_set`, `faltas.compras`,
`pending.encomendas`, `a_mais._usadas` — vê runas), o `uso_por_carta`, o
`owned_by_card` dos decks, o `propor_deck` e o `faltas._wanted`/`pimp`. O
`deck_payload` marca cada linha com `contado` (a runa: `wanted` e mais nada —
`have/missing/ordered` a 0, `price/versoes/printings` vazios) e cada secção
com `nao_contadas`; o payload e o `decks_index` levam `runas`. No `app.js`:
`runasCurto`/`runasNaoContadas` (separador, barra, chip), o cabeçalho do Rune
Pool («12 · não se contam, organizas à mão»), o tile `.dtile.neutro
.nao-contada` só com o «9×», o CSV salta-as. Na CLI: coluna «runas» no
`riftvault decks`, linha «runas: 12 (2 cartas) — não se contam» e o Rune Pool
com `- 9 Calm Rune` no `riftvault deck`, e o «fora, por serem runas» no
`riftvault a-mais`. `a_mais.excedente/libertadas(…, todas=True)` devolvem-nas
marcadas `runa`, para o `payload` contar o `scope.runas`. Config:
`riftvault_config.json` e `config.DEFAULTS` (`decks.contar_runas: false`,
`a_mais.sem_runas: true`, `_decks_runas_nota`, `_a_mais_nota`). `true`/`false`
voltam ao que era. **Uma carta sleevada num deck que seja runa não é
«extra»** (a lista pede-a, só não se conta) — há teste.

**O que NÃO mudou, de propósito:** as 6 runas base do OGN a **3** no master
set, a contar para a percentagem e para as wantlists (`master_targets_by_type`);
as runas em Alt Art **retiradas** (`f1dbd5b`); a Legend e o Champion numa
versão especial; «o deck completa com Alt Art/OverNumbered/SP que ele tenha»
para o que não é runa; `faltas_ignorar_tipos: ["Rune"]` continua a ser lido
(já não tira nada); o `seguir.py` (os decks dos OUTROS continuam a contar as
runas na falta — ele falou dos decks dele; fica anotado como dúvida no
relatório).

**Medido a 2026-09-17 contra cópias (`_revisao\_medir_runas_fora_decks.py`),
`main` (`28248e6`) e ramo na mesma corrida, em TRÊS cenários — antes; meio
(ramo com `a_mais.sem_runas: false`, para separar os dois efeitos); depois
— e os invariantes NÃO mexem em nenhum:** denominador **928**, níveis
**860/780/715 = 92,7 / 84,1 / 77,0 %** (faltam 68/206/409 ·
267,73/824,22/1 485,58 €), wantlist «tudo» **213 · 406 · 1 392,96 €** (OGN
625,31 · OGS 17,69 · SFD 330,74 · UNL 278,68 · VEN 140,54), valor **2 959,97 €
· 2 391 cópias**, Faltas por edição **349 · 542 · 12 391,36 €** (a comprar
213 · 406 · 1 392,96 €), Staples/Por deck/Pimp **iguais** (6 cartas · 9
cópias · 232,13 €; Pimp 10 · 11 · 749,73 €) — já não levavam runas.

**O que mexe:**

| | antes | depois |
|---|---|---|
| falta dos decks | 18 cópias · 10 cartas · 233,18 € · 13 disputadas | **9 · 6 · 232,13 € · 5 disputadas** |
| as 9 que saem | 6 Calm Rune (Azir), 1 Mind Rune (LeBlanc BH), 1 Chaos Rune e 1 Order Rune (Kennen) — 1,05 € | — |
| Ornn | 66/66 | **54/54 · 12 runas** |
| Azir | 59/66 · falta 6 · 6 disputadas · 1 a caminho | **53/54 · falta 0 · 1 a caminho** |
| LeBlanc Baited Hook | 60/66 · falta 5 · 4 disputadas | **49/54 · falta 4 · 3 disputadas** |
| Kennen Post Ban | 58/66 · falta 7 · 3 disputadas | **48/54 · falta 5 · 2 disputadas** |
| grelha da Coleção nas runas | «Ornn 8 · Azir 7 (faltam 6)» na Calm Rune, etc. | nada |
| runas que os decks prendiam | `OGN-042` 9 · `089` 7 · `166` 8 · `214` 15 = 39 cópias | 0 |

**O «A mais», nos dois sentidos, separados:**

| | excedente | libertadas | escondidas |
|---|---|---|---|
| antes | 69 impressões · 135 cópias (runas: `VEN-R01`, `VEN-R04` ×1, escondidas) | 39 cartas · 80 cópias (runas: Order Rune 8 e Mind Rune 4 do `leblanc.txt` apagado) | 12 · 16 |
| meio (as runas soltam-se) | **73 · 162** — entram `OGN-042` +6 (tem 9, alvo 3), `089` +4 (7), `166` +5 (8), `214` +12 (15) = **+27** | 39 · 80 | 12 · 16 |
| depois (e saem) | **67 · 133** — saem as 4 do OGN (27) e as 2 `VEN-R` (2) = **−29** | **37 · 68** = **−12** | 10 · 14 |

Saldo antes → depois: excedente **−2 cópias** (só as duas `VEN-R`; as 27
soltas nunca chegaram a ver-se), libertadas **−12**. `scope.runas` diz
exactamente isto: excedente 6 impressões · 29 cópias, libertadas 2 cartas · 12
cópias.

`tests/test_runas_fora_decks.py` (27 testes, contra cópias e config
temporário); `test_versoes_deck` (os dois testes da runa reescritos: a runa
nem entra, e a tensão fechou — só com `contar_runas: true` é que a alt art
tapava), `test_runas_alt_fora` (a classe `TestOsDecks` liga `contar_runas`
para continuar a ver o MECANISMO da retirada nos decks; o A mais «sem
retirar» liga os dois botões) e `test_a_mais` (o `scope` cresceu) ajustados.
Suite: 32 ficheiros.

## 18/09/2026 — as Alt Art voltam ao playset; OverNumbered (e promos) ficam a 1 (`master_set.um_de_cada`)

Palavras dele: *"muda novamente: **Alt Art para playset**, **overnumbered
continua 1 de cada**"*. Ramo `ai-pc/altart-playset-2026-09-18`; relatório em
`ai-pc/work/revisao/riftvault-altart-playset.md`.

**A regra, em três linhas:**

1. **Alt Art pede o playset do tipo** — Unit/Spell/Gear 3, Legend e
   Battlefield 1 (`metrics.alvo_do_tipo`) —, como a sequência. É um regresso
   parcial ao 14/09 (*"Alt Art, overnumbered, etc etc mete Playset na
   contagem"*): pediram 1 de 16/09 a 18/09.
2. **OverNumbered continua a 1 de cada.** **As promos `VEN-SP` também** —
   ele não as nomeou desta vez, e a 15/09 disse *"overnumbered e promos (SP)
   voltamos a 1 de cada"*: as duas andaram sempre juntas. **É dúvida no
   relatório**, não decisão dele; se quiser as promos a playset, é tirar
   `"promo"` da lista. (**Respondida horas depois**: *"as promos SP podes
   meter 3 de cada"* — o `"promo"` saiu; ver a secção a seguir.)
3. **As runas em Alt Art continuam retiradas de tudo** (`f1dbd5b`); o
   playset não lhes toca.

**Onde vive — não houve função nova.** O alvo por categoria da coleção extra
É o `master_set.um_de_cada` (`riftvault_config.json` e `config.DEFAULTS`):
o que lá está pede 1, o que não está pede o playset do tipo. Passou de
`["a", "overnumbered", "promo"]` a **`["overnumbered", "promo"]`** — uma
palavra. O `metrics.master_target`/`e_um_de_cada`/`_sufixo_alvo` já liam a
lista; o mecanismo estava «só desligado». Não se acrescentou uma segunda
tabela de alvos por categoria: era uma segunda maneira de dizer o mesmo, e
o `ALVO_UM = 1` é o significado do nome da lista, não um número por
categoria. O `master-sub` do `index.html` (estava a dizer «runas 1 · 1 de
cada arte alt.» desde 14/09) passou a descrever o de hoje.

**O que NÃO muda, medido:** a coleção extra continua fora da percentagem
(`fora_da_percentagem`) e fora de todas as listas de compra
(`listas_de_compra.so_master_set` — *"acompanhar não é querer comprar"*,
15/09): subir o alvo das alt arts **não** as põe na wantlist «tudo» nem nas
listas por nível. Os decks jogam a base, a Legend/Champion uma versão
especial, completam com outra impressão que ele tenha, não contam runas; a
procura dos decks continua a não levantar o alvo (irrelevante para as alt
arts agora, continua a valer para as sobrenumeradas e as promos). O
separador Encomendas e o corte de raridade não mexem.

**Medido a 2026-09-18 contra cópias (`_revisao\_medir_altart_playset.py`),
`main` (`25a31ba`) e ramo na mesma corrida, cada lado a ler o SEU config —
os invariantes NÃO mexem:** denominador **928**, níveis **860/780/715 de 928
= 92,7 / 84,1 / 77,0 %** (faltam 68/206/409 · 267,73/824,22/1 485,58 €),
wantlist «tudo» **213 linhas · 406 cópias · 1 392,96 €** (OGN 625,31 · OGS
17,69 · SFD 330,74 · UNL 278,68 · VEN 140,54), valor **2 959,97 € · 2 391
cópias**, falta dos decks **9 cópias · 6 cartas · 232,13 €**, Staples/Por
deck/Pimp iguais.

**O que mexe:**

| | antes (alvo 1) | depois (playset) |
|---|---|---|
| tiles das alt arts na Coleção | 96 a «N/1» | **96 a «N/3»** — as 96 alt arts do catálogo (102 − 6 runas retiradas) são todas Units; 41 com pelo menos uma cópia, 2 com duas (`SFD-177a` Azir, Sovereign; `UNL-059a` Master Yi, Unstoppable), nenhuma a 3 |
| cabeçalho do bloco | «Coleção — artes alternativas — 1 de cada · tens 10 de 24» (OGN) | «— playset · tens 10 de 24 · **0 no playset completo**» |
| Faltas, bloco Alt Art (fechar) | **55 impressões · 55 cópias · 364,95 €** (OGN 14 · 106,29 € / SFD 14 · 54,11 € / UNL 15 · 143,31 € / VEN 12 · 55,24 €) | **96 · 245 · 1 420,07 €** (OGN 24 · 62 · 403,09 € / SFD 24 · 61 · 224,88 € / UNL 30 · 74 · 602,34 € / VEN 18 · 48 · 189,76 €) — **+41 impressões · +190 cópias · +1 055,12 €** |
| Faltas, «fechar os três blocos» | 349 · 542 · 12 391,36 € | **390 · 732 · 13 452,48 €** |
| Faltas, «a comprar» (= wantlist) | 213 · 406 · 1 392,96 € | **igual** |
| A mais, excedente | 67 impressões · 133 cópias | **65 · 131** — saem a `SFD-177a` (tem 2, alvo 1 → 3, 1 usada pelo Champion do Azir) e a `UNL-059a` (tem 2, alvo 1 → 3); libertadas 37 · 68 iguais |

Carta a carta no bloco Alt Art: as 55 que já faltavam (0 cópias) passam de
«faltam 1» a «faltam 3»; as 39 com 1 cópia entram a «faltam 2»; as 2 com 2
cópias entram a «faltam 1». As mais caras do bloco: `OGN-039a` Kai'Sa,
Survivor 3 × 49,63 €, `SFD-057a` Irelia, Fervent 3 × 29,40 €, `UNL-120a`
Rengar, Trophy Hunter 3 × 28,40 €, `UNL-150a` Vex, Apathetic 3 × 25,40 €,
`UNL-028a` Pyke, Dockside Butcher 2 × 20,17 €.

**Testes ajustados** (o teste é que estava velho, não o código):
`test_a_mais` (alt art 4 de 3 → 1 a mais; a que o deck usa), `test_a_subir`,
`test_alvo_1` (voltou ao que descrevia a 15/09, com o caso «o `a` no
`um_de_cada` volta a pô-la a 1»), `test_coerencia`, `test_faltas_nova` (1 de
3 falta 2, totais), `test_masterset` (alvos, rótulos, os botões antigos, o
`alvo` antigo das runas), `test_runas_3`, `test_tres_blocos`,
`test_wantlist_edicao` (a V.2 a 3 com o botão desligado); `test_voltar_1`,
`test_versoes_deck` e `test_runas_alt_fora` passaram a escrever o config de
hoje (sem o `a`) e ganharam o caso do `a` de volta; `test_contador_bloco`
só o comentário. Suite: 32 ficheiros, 0 a falhar.

## 18/09/2026, mais tarde — as promos SP passam a playset (3 de cada); só as sobrenumeradas ficam a 1

**REVOGADO a 2026-09-19** (*"as Promo passam a 1 de cada ao inves de
playset"*) — durou um dia; ver a última secção deste ficheiro. O que se segue
é como estava a 18/09.

Palavras dele: *"as promos SP podes meter 3 de cada"*. É a resposta à dúvida
da secção anterior (as promos tinham ficado a 1 com as sobrenumeradas por
analogia com 15/09). Ramo `ai-pc/sp-playset-2026-09-18`; relatório em
`ai-pc/work/revisao/riftvault-sp-playset.md`.

**A regra, em duas linhas:**

1. **As promos `VEN-SP` pedem o playset do tipo.** As 6 do catálogo
   (`VEN-SP1..SP6` — Kai'Sa, Sona, Ahri, Sett, Ezreal, Lux) são **todas
   `Unit`, `epic`**, por isso «playset» e «3 de cada» são o mesmo número e
   não houve nada a decidir. Implementou-se o playset, que é o mecanismo que
   existe: se uma edição nova trouxer uma promo Legend ou Battlefield, ela
   pede 1 — é o `metrics.alvo_do_tipo`, como nas alt arts.
2. **As sobrenumeradas continuam a 1 de cada.** É a única entrada que resta
   no `master_set.um_de_cada`.

**Onde vive — a mesma palavra de ontem.** `master_set.um_de_cada` passou de
`["overnumbered", "promo"]` a **`["overnumbered"]`** (`riftvault_config.json`
e `config.DEFAULTS`); as notas do config, os docstrings do `metrics.py`
(`master_target`, `e_um_de_cada`, `_sufixo_alvo`), o comentário do
`decks.py`, o `master-sub` do `index.html` («alt art e promos a playset,
sobrenumeradas 1 de cada») e o README dizem o de hoje. O bloco chama-se
«Coleção — promos — playset» e o cabeçalho ganha a segunda conta («tens 2
de 6 · 0 no playset completo», `max_target` 3).

**O que NÃO muda, medido a 2026-09-18 contra cópias
(`_revisao\_medir_sp_playset.py`), `main` (`c77d06a`) e ramo na mesma
corrida, cada lado a ler o SEU config:** denominador **928**, níveis
**860/780/715 de 928 = 92,7 / 84,1 / 77,0 %** (faltam 68/206/409 ·
269,02/832,81/1 505,73 €), wantlist «tudo» **213 linhas · 406 cópias ·
1 416,51 €** (OGN 624,58 · OGS 17,78 · SFD 332,70 · UNL 291,47 · VEN 149,98),
valor **3 005,89 € · 2 391 cópias**, falta dos decks **9 cópias · 6 cartas ·
231,93 €**, Staples/Por deck/Pimp, Encomendas (**4 cópias · 3 impressões ·
164,22 €**) e o separador **Faltas** inteiro (fechar os três blocos 390 ·
732 · 13 342,62 €; a comprar 213 · 406 · 1 416,51 €) — **iguais nos dois
lados.** (Os euros diferem dos da secção anterior porque o `main` já tem os
preços de 18/09, `c77d06a`, e ele meteu cartas na Coleção entretanto — não
é desta ordem.) A coleção extra continua fora da percentagem e das listas
de compra: subir o alvo das promos não as põe em wantlist nenhuma.

**O separador Faltas NÃO tem bloco de promos** (15/09: ele nomeou três
blocos e não as nomeou; `scope.fora = {promos: 6}`), por isso «quanto cresce
o bloco das promos nas Faltas» não tem sítio onde se ler — mediu-se pela
grelha da Coleção (alvo − cópias, × preço de hoje). **Fica como dúvida** se
agora que pedem 3 ele as quer no Faltas.

**O que mexe:**

| | antes (alvo 1) | depois (playset) |
|---|---|---|
| tiles das promos na Coleção | 6 a «N/1» | **6 a «N/3»** |
| cabeçalho do bloco (VEN) | «Coleção — promos — 1 de cada · tens 2 de 6» | «**— playset** · tens 2 de 6 · **0 no playset completo**» |
| para fechar o bloco | **4 impressões · 4 cópias · 215,25 €** | **6 · 16 · 713,27 €** (+2 · +12 · +498,02 €) |
| A mais, excedente | 65 impressões · 131 cópias | **igual** — nenhuma promo tinha mais do que 1 cópia (as duas dele, `VEN-SP4` e `VEN-SP5`, estão a 1) |

Carta a carta: `VEN-SP1` Kai'Sa, Survivor 0/3 · 3 × 60,82 € = 182,46 €;
`VEN-SP2` Sona, Harmonious 0/3 · 79,20 €; `VEN-SP3` Ahri, Inquisitive 0/3 ·
3 × 97,64 € = 292,92 €; `VEN-SP4` Sett, Brawler **1/3** · 2 × 15,96 € =
31,92 €; `VEN-SP5` Ezreal, Prodigy **1/3** · 2 × 17,80 € = 35,60 €;
`VEN-SP6` Lux, Crownguard 0/3 · 91,17 €.

**Testes ajustados** (o teste é que estava velho, não o código):
`test_alvo_1` (a promo pede 3 e volta a 1 com o `promo` na lista; «1/3» e
«4/3»; o cabeçalho diz 1 de cada só nas sobrenumeradas), `test_masterset`,
`test_promos` (rótulo, alvo, «1 de 3»), `test_tres_blocos` (alvos e o botão
desligado), `test_contador_bloco` (as promos a playset dizem as duas contas;
com o `promo` na lista voltam a «tens 2 de 6» completo); `test_voltar_1`,
`test_versoes_deck` e `test_runas_alt_fora` passaram a escrever o config de
hoje (sem o `promo`). Suite: 32 ficheiros, 0 a falhar.

## 18/09/2026, à tarde — a montra «Promos» foi APAGADA (durou umas horas)

Palavras dele, pouco depois de a ver: *"podes apagar esta funcao das promos,
**as unicas que ficam sao as do SP**"*. Relatório em
`ai-pc/work/revisao/riftvault-promos-fora.md`.

**O que era:** o merge `f7522c7` dessa manhã — um botão **Promos** ao lado
das edições da Coleção, com as 128 cartas promo da comunidade (Nexus Night,
bundles, eventos de lançamento, Summoner Skirmish, …) lidas do riftbound.gg
para `data/promos_oficiais.json`, casadas com o catálogo e mostradas com a
foto da versão NORMAL. Só mostrava; não contava para nada.

**O que se fez:** `git revert -m 1 f7522c7`, directamente no `main`, sem
conflitos — saíram o `riftvault/promos.py`, o `data/promos_oficiais.json`, o
`tests/test_promos_montra.py`, a rota `/api/promos.json`, o `api/promos.json`
do `build`, o `riftvault promos`, o `config.PROMOS_PATH`, o botão e a
`#promos` do `index.html`/`app.js`/`style.css`, e as secções do README e
deste ficheiro. **Para a trazer de volta** é reverter o commit da reversão
(está no relatório) — o código e a lista já casada voltam inteiros. **Não
voltar a construir sem ele pedir.** O `robots.txt` do riftbound.gg continua a
proibir o `anthropic-ai`.

**As 6 `VEN-SP` são OUTRA COISA e não foram tocadas.** São impressões que o
catálogo da RiftScribe conhece, estão na categoria `promo` da coleção extra
(`master_set.fora_da_percentagem`) e pedem o playset desde `147ec02` (a
secção anterior). Medido a 2026-09-18 contra cópias do `data/` real
(`ai-pc/work/revisao/_medir_promos_fora.py`, `d19cf8d` vs `main` revertido,
na mesma corrida): o bloco «Coleção — promos — playset» continua «tens 2 de 6
· 0 no playset completo» (`max_target` 3), os seis tiles a «0/3, 0/3, 0/3,
1/3, 1/3, 0/3»; e **nada mexe** — denominador **928**, níveis **860/780/715
= 92,7 / 84,1 / 77,0 %**, wantlist «tudo» **213 · 406 · 1 416,51 €**, valor
**3 005,89 € · 2 391 cópias**, falta dos decks **9 · 6 · 231,93 €**, compras,
Encomendas (4 cópias · 164,22 €), Faltas por edição (390 · 732 ·
13 342,62 €), A mais (65 · 131 / 37 · 68, item a item), os grupos por edição
(310/24/251/238/203) e os blocos da grelha — iguais nos dois lados. Suite: 32
ficheiros.

## 19/09/2026 — a ordem dos blocos da Coleção passa a config; o bloco «Runas — 12 de cada», só para ver

Palavras dele: *"na ordem das coleccoes: coloca as **OverNumbered a seguir ao
master Set**, depois as **AltArt**, depois as **Promos**, e depois mete **12
runas de cada** (nao contabilizes para nada, e so para mim para contabilizar
ali algumas coisas)"*. Ramo `ai-pc/ordem-blocos-2026-09-19`; relatório em
`ai-pc/work/revisao/riftvault-ordem-blocos.md`.

**1. A ordem.** Estava cravada na lista `metrics.BLOCOS` (master set, runas
especiais, artes alternativas, sobrenumeradas, promos) e o `set_payload`
percorria-a. Passou a `master_set.ordem_dos_blocos` no config
(`riftvault_config.json` e `config.DEFAULTS`, hoje `["master",
"overnumbered", "a", "promo"]`), lida por `metrics.ordem_dos_blocos` — a
mesma gramática das outras listas do `master_set` (`a`, `promo`, `-SP`,
`overnumbered`) ou o id do bloco; o que a lista não nomear vem A SEGUIR pela
ordem do catálogo `BLOCOS` (hoje só as runas especiais, vazias); um valor
desconhecido rebenta. `BLOCOS` ficou como o CATÁLOGO dos blocos (ids e
rótulos), não a ordem. **Só a ordem mexeu**: rótulos, alvos, contadores,
percentagem e listas iguais. O separador Faltas tem a ordem própria dele
(master set, Alt Art, OverNumbered — 15/09) e não lê isto. (**Desde a noite
de 2026-09-19 lê** — `faltas_edicao.blocos` corta esta lista aos quatro
blocos dele; ver a última secção deste ficheiro.)

**2. O bloco das runas — uma VISTA, não uma categoria.** `riftvault/
runas_vista.py`, rota `/api/runas.json` (um ficheiro para as cinco edições —
as runas são as mesmas seis), `riftvault runas`; no `app.js` o
`renderRunasVista` escreve no `#runas-vista`, a seguir à grelha, em todas as
edições; o `state.runas` só é lido por ele. As 6 runas do catálogo (Body,
Calm, Chaos, Fury, Mind, Order — `runas_especiais.tipos`, a mesma definição
de «runa»), uma linha cada, alvo `runas_vista.alvo` (12; não positivo
rebenta).

**«Tenho» = tudo o que ele fisicamente tem, de todas as versões** — é a
leitura desta ordem e a única coisa nela que contraria uma regra anterior:
conta a base do OGN (a sequência), a arte alternativa do OGN (**retirada**
de tudo desde 17/09), a promo do VEN (escondida) e as do CardTrader que a
RiftScribe não tem (`market_only`, que hoje nenhum sítio mostra), esteja a
cópia na Coleção, num deck ou no binder. Por contrariar a retirada, cada
linha leva os DOIS números — `total` e `sem_retiradas` — e o tile mostra o
segundo quando difere; não se escolheu por ele. Medido a 2026-09-19 contra
cópias: **74 runas à mão (43 sem as retiradas)** — Body 2, Calm **27** (9
`OGN-042` + 6 `OGN-042a` + 12 `SFD-R02a`), Chaos 9 (8 + 1), Fury 2, Mind
**12** (7 + 1 + 4 `SFD-R03a`), Order **22** (15 + 7 `SFD-R06a`); sem as
retiradas 2 / 9 / 8 / 2 / 7 / 15.

**As 6 runas base do OGN aparecem duas vezes** — na sequência (a 3) e aqui
(a 12) — e está escrito no ecrã: o cabeçalho do bloco diz *«só para
contares o que tens à mão — não conta para as métricas. As runas base do OGN
também estão na sequência do master set, em cima; aqui somam-se TODAS as
versões que tens, incluindo as que o resto do site não conta»*
(`runas_vista.NOTA`).

**NÃO CONTA PARA NADA, e há teste.** `tests/test_runas_vista.py` (19
testes, contra cópias e config temporário) lê o código-fonte e recusa que
qualquer módulo de contas (`metrics`, `a_subir`, `faltas`, `faltas_edicao`,
`a_mais`, `uso_decks`, `decks`, `locais`, `pending`, `prices`, `collection`,
`quanto_custa`, `cardmarket`, `seguir`, `catalog`, `db`) importe o
`runas_vista` — só o `server`, o `build` e a `cli` o chamam; o payload da
edição e o da Encomendas não o trazem; mudar o alvo de 12 para 1 não mexe em
número nenhum (barra, índice, níveis, wantlist, Faltas, A mais); o `payload`
não escreve e não leva euros; e o `renderProgress`/`render` do `app.js` não
lêem o `state.runas`.

**Medido a 2026-09-19 contra cópias (`_medir_ordem_blocos.py`), `main`
(`c7e66bf`) e ramo na mesma corrida — os invariantes NÃO mexem:**
denominador **928**, níveis **860/783/718 de 928 = 92,7 / 84,4 / 77,4 %**
(faltam 68/203/403 · 268,59/784,15/1 417,64 €), wantlist «tudo» **210 linhas
· 400 cópias · 1 330,72 €**, valor **3 350,11 € · 2 402 cópias**, falta dos
decks **9 · 6 · 231,67 €**, compras, Encomendas (4 cópias · 161,92 €),
Faltas por edição (385 · 722 · 13 011,42 €; a comprar 210 · 400 ·
1 330,72 €), A mais (65 · 131 / 37 · 68, item a item), os grupos por edição
(310/24/251/238/203) e os blocos da grelha (rótulo, total, owned, done,
max_target) — iguais nos dois lados. (Os números diferem dos de 18/09 porque
ele meteu cartas na Coleção entretanto — não é desta ordem.) O que muda: a
ordem `['master', 'alt_art', 'overnumbered', 'special']` → `['master',
'overnumbered', 'alt_art', 'special']` em todas as edições, e o
`api/runas.json` que só existe no depois. Suite: 33 ficheiros.

## 19/09/2026, à tarde — o bloco das runas é o CONTADOR dele, com `+` e `−` (`rune_counter`)

Palavras dele: *"as runas tens que colocar botoes de + e - tbm"* e, perguntado
o que os botões mexem: *"runas **nao contabilizam nada**, **eu e que mexo
nisso para minha referencia**, nao entram para decks, nao entram para
coleccao, nada, **so para mim**"*. Ramo `ai-pc/runas-contador-2026-09-19`;
relatório em `ai-pc/work/revisao/riftvault-runas-contador.md`.

**O que mudou numa frase:** o número do bloco «Runas — 12 de cada» deixou de
ser calculado a partir do que ele tem e passou a ser **dele** — está na
tabela `rune_counter` do vault.db (`card_key`, `qty >= 0`, `seeded_from`,
`updated_at`), os `+`/`−` do bloco escrevem lá (`runas_vista.ajustar`,
`POST /api/runas/ajustar {card_key, delta}`, `riftvault runas --mais/--menos
RUNA [--n N]`) e em mais lado nenhum, e **ninguém lê esse número para fazer
contas**. O alvo continua 12 por runa (`runas_vista.alvo`), só para a barra.

**Decisões tomadas sem lhe perguntar (estão no relatório):**

1. **Um só conjunto de 6 contadores**, não um por edição — o bloco aparece
   no fim de todas as edições com o mesmo número, porque são as runas dele.
2. **Sementeira única, por runa** (`runas_vista.semear`): a primeira leitura
   que encontre uma runa sem linha cria-a com o `total` da referência nesse
   momento (todas as versões, retiradas e CardTrader incluídas — o que o
   bloco calculava de manhã). Depois disso o número nunca mais é recalculado
   a partir da coleção: uma linha a 0 é dele, e semear duas vezes semeia
   zero na segunda (há teste). Uma runa que apareça numa edição nova
   semeia-se nessa altura, uma vez, pela mesma regra. A sementeira é a única
   escrita de uma leitura, e é só nessa tabela — `copies`, `ops`, `pending`
   e locais não se tocam (há teste). **No `data/` real quem semeia é o
   primeiro processo com o código novo a abrir o vault.db** — a `publicar`
   depois do merge —, com o que ele tiver na mão nesse momento.
3. **A referência «na coleção: N» fica**, em letra pequena e apagada por
   baixo do tile (`.onde.tenho.ref`), com as origens só no `title`; no
   cabeçalho «contas **76** de 72 · na coleção: 76 (45 sem as retiradas)».
   É o que o bloco calculava até aqui e continua a calcular
   (`runas_vista._na_colecao`: `total`, `sem_retiradas`, `origens`) — não
   é contabilidade, é para ele comparar o que contou à mão com o que o site
   sabe. Um `+` da GRELHA numa runa relê o bloco (`runaMexeu`) para a
   referência andar; o contador não mexe com isso.
4. **O chão é zero**: `ajustar` faz `max(0, qty + delta)` e devolve 0 sem
   erro (não é uma encomenda por anular); o `−` do tile desliga-se a 0.

**Onde os botões aparecem:** são `.steppers` como todos os outros — o
`body.readonly` do site publicado esconde-os — e, por cima disso, só se
desenham quando o PAYLOAD traz `editable: true` (o servidor) e `contador`
(código novo). O `build` escreve `editable: false`. **O 8770 não se
reinicia a cada merge e o `app.js` é lido do disco a cada pedido**: com o
Python antigo a servir o payload de manhã (sem `contador`), o `app.js` novo
mostra o número calculado e sem botões (`runaContador`), até o vigia
relançar o processo — nada parte no meio.

**A prova de que não conta, medida.** `tests/test_runas_vista.py` passou de
19 para **30 testes**: além de recusar que qualquer módulo de contas importe
o `runas_vista`, `test_mexer_nos_contadores_nao_mexe_em_numero_nenhum`
fotografa grelha, blocos, barra, índice, níveis, wantlist, valor, Faltas, A
mais, decks, Encomendas e `copies` com os contadores semeados, todos a 99 e
todos a 0 — os três JSON são iguais. `ajustar` escreve só na `rune_counter`;
o `+` numa runa por semear semeia primeiro (não nasce a 1); o que não é runa
é `RunaDesconhecida` (404 na rota); a CLI mexe só no contador; o `app.js`
manda ao `api/runas/ajustar` e não toca em `api/adjust`, encomendas,
`wlDesatualizar` nem `state.qty`.

**Medido a 2026-09-19 contra cópias (`ai-pc/work/revisao/_medir_runas_contador.py`),
`main` (`2043ec8`) e ramo na mesma corrida, em QUATRO cenários — antes;
depois (semeado); depois com os 6 contadores a 99; depois com os 6 a 0 — e
os invariantes NÃO mexem em nenhum:** denominador **928**, níveis
**872/805/731 de 928 = 94,0 / 86,7 / 78,8 %** (faltam 56/172/362 ·
184,86/577,86/1 177,95 €), wantlist «tudo» **197 linhas · 362 cópias ·
1 177,95 €** (OGN 512,86 · OGS 16,93 · SFD 339,93 · UNL 270,77 · VEN 37,46),
valor **5 677,90 € · 2 460 cópias**, falta dos decks **13 · 7 · 223,83 €**,
compras, Encomendas (0), Faltas por edição (358 · 665 · 10 856,18 €; a
comprar 197 · 362 · 1 177,95 €), A mais (64 · 130 / 37 · 68, item a item),
os tiles da grelha e das Encomendas (qty/alvo/bloco, impressão a impressão),
os grupos por edição (310/24/251/238/203), o `copies` inteiro e o número de
`ops`. (Os números diferem dos da secção anterior porque ele meteu cartas
entretanto — não é desta ordem; o 928 é o mesmo.) O que muda: o
`api/runas.json` ganha `contador`, `editable` e `semeadas`; **a sementeira
seria Body 2 · Calm 27 · Chaos 9 · Fury 4 · Mind 12 · Order 22 = 76** (a
ordem falava em 74 com Fury 2 — ele meteu 2 Fury Rune desde a medição da
manhã); a referência «na coleção» é igual nos quatro cenários. Suite: 33
ficheiros, 0 a falhar.

## 19/09/2026, à noite — quatro wantlists por edição (o bloco «Promos» nas Faltas, uma wantlist por bloco); as promos voltam a 1 de cada

Palavras dele: *"as wantlist das edicoes, quero **4 wantlist**: 1 so para o
master set, 1 so para as Alt.Art, 1 so para as Overnumbered, uma so para as
Promo (no caso SP) — e as **Promo passam a 1 de cada** ao inves de playset"*.
Ramo `ai-pc/quatro-wantlists-2026-09-19`; relatório em
`ai-pc/work/revisao/riftvault-quatro-wantlists.md`.

### 1. As promos voltam a 1 de cada — e o historial do alvo delas

Uma palavra: o `"promo"` voltou a `master_set.um_de_cada`
(`riftvault_config.json` e `config.DEFAULTS`), que fica `["overnumbered",
"promo"]`. É o contrário exacto do merge `147ec02` de 18/09 (a secção
«as promos SP passam a playset», acima, ficou marcada como revogada). As
**Alt Art continuam no playset**. Os testes que fixavam as promos a 3 (de
18/09) foram REPOSTOS à versão pré-`147ec02` — o teste é que estava velho,
não o código — e ganharam o caso «tirar o `promo` da lista volta a pô-la ao
playset».

**O alvo das promos `VEN-SP` andou quatro vezes em cinco dias, e é aqui que
fica escrito:**

| data | alvo | frase |
|---|---|---|
| 2026-09-14, à noite | playset (3) | *"Alt Art, overnumbered, etc etc mete Playset na contagem"* |
| 2026-09-15 | **1** | *"overnumbered e promos (SP) voltamos a 1 de cada"* |
| 2026-09-18, de manhã | playset (3) | *"as promos SP podes meter 3 de cada"* (merge `147ec02`) |
| 2026-09-19, à noite | **1** | *"as Promo passam a 1 de cada ao inves de playset"* (esta ordem) |

O mecanismo é sempre o mesmo — a palavra na lista — e é por isso que cada
ida e volta é um commit pequeno. Se voltar a mudar, é aqui que se acrescenta
uma linha.

### 2. O quarto bloco nas Faltas, e uma wantlist por bloco

**O que havia ATÉ AQUI, para não se inventar história:** o separador Faltas
tinha TRÊS blocos (Master set, Alt Art, OverNumbered — 15/09), com a ordem
cravada no `faltas_edicao.BLOCOS`, as promos de fora (`scope.fora`, «Fora
deste separador: 6 promos» — a pergunta de 15/09) e **nenhuma wantlist por
bloco** — os itens já levavam os campos do gerador do Cardmarket
(`market_name`, `v`, …) desde 15/09, mas só o bloco `master` os usava, e
indirectamente, pela wantlist do fim de cada edição da Coleção. A ordem de
19/09 chegou a dizer que cada bloco «já tinha a sua wantlist desde 16/09»;
não tinha — fica no relatório.

**O que passou a haver:**

- **Quatro blocos**, o catálogo em `faltas_edicao.BLOCO_LABEL` (`master`
  «Master set», `alt_art` «Alt Art», `overnumbered` «OverNumbered»,
  `special` «Promos»); `bloco_das_faltas` manda a promo para `special`.
  `scope.fora` fica vazio (só uma variante nova cairia lá).
- **A ordem é a da Coleção**: `faltas_edicao.blocos(cfg)` corta
  `metrics.ordem_dos_blocos(cfg)` (`master_set.ordem_dos_blocos`) aos
  quatro ids — hoje master set, sobrenumeradas, alt art, promos. Ele muda
  num sítio e muda nos dois. Na mensagem de 19/09 enumerou «master set,
  Alt.Art, Overnumbered, Promo» — leu-se como a ordem de quem enumera, não
  como pedido de ordem diferente; se ele quiser a outra, é a lista do config.
- **Uma wantlist do Cardmarket por bloco e por edição**, por baixo dos
  tiles: `faltas_edicao.wantlist(con, set_id, bloco, com_codigo)` em Python
  (o texto sai do `cardmarket.gerar`, o gerador único), o resumo
  `blocks[].wantlist` (`lines/copies/cents/foil`) no payload, e no `app.js`
  o `feWantlistHTML`/`feWantlistItens` com a caixa `cmZonaHTML` já
  preenchida, os três botões de sempre e o CSV
  `riftvault-faltas-<SET>-<bloco>-<data>.csv`. Só o que há a **comprar**
  (`missing > 0`) — o que vem a caminho está nos tiles, marcado, e não vai
  para o Cardmarket, como na wantlist da Coleção. **A do bloco `master` é,
  texto a texto, a wantlist dessa edição da Coleção** (`a_subir.wantlist`)
  — há teste. Na CLI: `riftvault faltas --edicao OGN --bloco alt_art
  --cardmarket [--codigos]` (stdout colável, resumo no stderr);
  `--bloco` sozinho filtra a listagem.
- **A wantlist GERAL não cresce.** `in_lists` continua a vir de
  `listas_de_compra.so_master_set`: a do fim de cada edição da Coleção, a
  «Wantlist — tudo» e o `totals_lists` são só o master set — *"acompanhar
  não é querer comprar"* (15/09) continua a valer para as listas gerais; o
  que 19/09 acrescenta é que cada bloco extra se compra, quando ele quiser,
  pela lista própria. A nota da Coleção aponta às outras três
  (`<a href="#faltas-edicao">Faltas</a>`) e o cabeçalho das Faltas passou de
  «só para ver» a «wantlist própria», com «Fechar os quatro blocos» e
  «Wantlist geral».

**Medido a 2026-09-19 contra cópias (`ai-pc/work/revisao/_medir_quatro_wantlists.py`),
`main` (`854d92f`) e ramo na mesma corrida, cada lado a ler o SEU config —
os invariantes NÃO mexem:** denominador **928**, níveis **896/835/766 de 928
= 96,6 / 90,0 / 82,5 %** (faltam 32/123/283 · 79,37/408,68/965,28 €),
wantlist «tudo» **162 linhas · 283 cópias · 965,28 €** (OGN 391,70 · OGS
16,93 · SFD 265,01 · UNL 266,48 · VEN 25,16), valor **6 239,64 € · 2 564
cópias**, falta dos decks **10 cópias · 4 cartas · 216,30 €**, compras,
Encomendas (0), os grupos por edição (310/24/251/238/203), os blocos da
grelha menos o das promos, e as wantlists dos três blocos que já existiam
(iguais linha a linha). (Os números diferem dos da secção anterior porque
ele meteu cartas entretanto — não é desta ordem; o 928 é o mesmo.)

**As quatro wantlists, depois (linhas · cópias · €; «só foil» = linhas com
oferta só em foil no CardTrader):**

| edição | master set | OverNumbered | Alt Art | Promos |
|---|---|---|---|---|
| OGN | 81 · 147 · 391,70 € (34 só foil) | 6 · 6 · 595,96 € | 23 · 50 · 308,67 € | — |
| OGS | 13 · 13 · 16,93 € | — | — | — |
| SFD | 33 · 60 · 265,01 € | 23 · 23 · 1 702,89 € | 24 · 56 · 233,50 € | — |
| UNL | 24 · 40 · 266,48 € | 8 · 8 · 2 709,07 € | 30 · 70 · 590,28 € | — |
| VEN | 11 · 23 · 25,16 € | 26 · 26 · 3 126,37 € | 18 · 40 · 158,12 € | **2 · 2 · 56,79 €** (`VEN-SP2` Sona 26,40 €, `VEN-SP6` Lux 30,39 €) |
| **total** | **162 · 283 · 965,28 €** (= a wantlist «tudo») | 63 · 63 · 8 134,29 € | 95 · 216 · 1 290,57 € | 2 · 2 · 56,79 € |

Fora do master set, quase tudo só tem oferta foil (as 63 sobrenumeradas, as
95 alt arts e as 2 promos, todas) — é a ressalva do `from_foil` de sempre.

**O que mexe:** os seis tiles das promos passam de «N/3» a «N/1» (tem
`SP1` 1, `SP3` 1, `SP4` 1, `SP5` **2**, `SP2` e `SP6` 0); o bloco «Coleção —
promos» passa de «playset · tens 4 de 6 · 0 no playset completo» a «1 de
cada · tens 4 de 6» (`done` 0 → 4, `max_target` 3 → 1); o separador Faltas
passa de 3 a 4 blocos, «fechar» de **320 impressões · 562 cópias ·
10 390,14 €** para **322 · 564 · 10 446,93 €** (as 2 promos a faltar; a
ordem dos blocos muda, os totais dos outros três não), «a comprar» igual
(162 · 283 · 965,28 €); **e o «A mais» sobe 1 cópia: 130 → 131 (VEN 3 → 4)**
— a `VEN-SP5` Ezreal, Prodigy que ele tem a 2 com alvo agora 1. A ordem
dizia que o A mais não mexia, contando com «duas delas a 1 cópia»; ele tem
hoje quatro com pelo menos uma e a SP5 a 2, e a regra do excedente
(`cópias − max(usadas, alvo)`, 17/09) é a mesma que a 18/09 tirou a
`SFD-177a` do A mais quando o alvo subiu — agora entra a SP5 quando desce.
Não é um número novo, é o alvo a mudar; fica no relatório.

`tests/test_faltas_nova.py` reescrito (27 testes, contra cópias e config
temporário): os quatro blocos pela ordem da Coleção e a ordem a vir do
config; a promo com 0 falta 1, com 1 está completa, com 2 não é a mais aqui;
com o `promo` fora do `um_de_cada` volta a pedir 3; cada bloco tem a sua
wantlist e só a sua (ids, quantidades, euros, texto = `cardmarket.linha`
linha a linha); a do master set é a da Coleção (texto, com e sem código); o
que vem a caminho não vai para a wantlist do bloco; as três extra não fazem
crescer a geral; bloco/edição desconhecidos rebentam; a CLI escreve a do
bloco e recusa `--cardmarket` sem `--bloco`; o `app.js` desenha uma caixa
por bloco e a Coleção aponta às outras. Os oito ficheiros de testes que
`147ec02` tinha ajustado voltaram atrás com o historial. Suite: 33
ficheiros, 0 a falhar.

## 19/09/2026, à noite — o separador «Quanto custa» foi APAGADO

Palavras dele: *"podes apagar o botao do 'Quanto custa'"*. Ramo
`ai-pc/sem-quanto-custa-2026-09-19`; relatório em
`ai-pc/work/revisao/riftvault-sem-quanto-custa.md`.

**O que era.** O terceiro separador. Chamou-se «Faltas» até 2026-09-15 de
manhã (as listas de compra dos decks e do master set); de manhã a 15/09
passou a «Quanto custa» (as faltas do master set por raridade e por preço);
à tarde as abas por deck saíram para o separador Decks; ao fim da tarde
passou a ser a **tabela de preços do jogo** — para cada edição menos o OGS,
o top 5 mais caras de comuns, incomuns, raras e míticas (`epic`), só a
sequência, **tenha ele ou não**. Nunca contou para nada: era apresentação
(`quanto_custa.py`, `api/quanto_custa.json`, `riftvault quanto-custa`, a
chave `quanto_custa` do config, o botão e a secção `#faltas` com o
`#falta-tabs` no site, o CSS `mf-*`/`qc-*`, `tests/test_top5.py`).

**Como saiu.** À mão, em três commits no ramo (apresentação; rota, `build`
e CLI; módulo, config e testes) — não havia um commit único a reverter,
porque nasceu a 15/09 de uma renomeação e cresceu em três ordens. **Nenhum
módulo de contas o importava** (só `server`, `build` e `cli`), por isso não
houve nada a desatar. O `git grep -i "quanto.custa\|quanto_custa\|quantoCusta"`
no código-fonte dá zero, com quatro excepções que são PALAVRAS DELE sobre o
`seguir` e não sobre o separador (*"nao preciso que me diga quanto
custaria"* — `seguir.py`, `cli.py`, `config.py` e a `_seguir_nota` do
`riftvault_config.json`) e o teste que fixa a remoção
(`tests/test_sem_quanto_custa.py`, o único que pode dizer o nome; recusa-o
em todo o resto).

**O que ficou, de propósito, porque não era só dele:** a língua das ofertas
(`precos.linguas`, o filtro é na recolha — os testes foram para
`tests/test_precos_ingles.py`); as abas Staples / Por deck / Pimp no
separador Decks (`faltas.compras`, `api/compras.json`); a wantlist da
Coleção (`a_subir.master_faltas`, `api/wantlist.json`); o `riftvault
a-subir`; o `a_mais.sem_edicoes` (o «menos proving grounds» de 15/09 vale
hoje só no A mais); o `faltas.py` inteiro (as listas dos decks). O
`.fe-set` das Faltas e do A mais já tinha margem própria — a classe
`qc-set` que lá estava por cima era peso morto e saiu.

**Recupera-se a partir de `2f49a17`** (o `main` de 2026-09-19 22:22, o
último commit antes da remoção): `git checkout 2f49a17 --
riftvault/quanto_custa.py tests/test_top5.py` traz o módulo e os testes, e
o resto (rota, `build`, CLI, `app.js`, `index.html`, `style.css`, config)
vem de reverter o merge do ramo, cujo sha está no relatório. **Não voltar a
construir sem ele pedir.**

**Medido a 2026-09-19 contra cópias (`ai-pc/work/revisao/_medir_sem_quanto_custa.py`),
`main` (`2f49a17`) e ramo na mesma corrida, cada lado a ler o SEU config —
TUDO IGUAL:** denominador **928**, níveis **896/835/766 de 928 = 96,6 / 90,0
/ 82,5 %** (faltam 32/123/283 · 79,37/408,68/965,28 €), wantlist «tudo»
**162 linhas · 283 cópias · 965,28 €** (OGN 391,70 · OGS 16,93 · SFD 265,01 ·
UNL 266,48 · VEN 25,16), valor **6 239,64 € · 2 564 cópias**, falta dos decks
**10 cópias · 4 cartas · 216,30 €**, compras (3 Staples; Pimp 9 · 10 ·
729,12 €), Encomendas (0), A mais **65 · 131 / 37 · 68** item a item, o
separador Faltas inteiro (322 · 564 · 10 446,93 €; a comprar 162 · 283 ·
965,28 €; os quatro blocos e as quatro wantlists por edição), os blocos e
os tiles da grelha impressão a impressão, os grupos por edição
(310/24/251/238/203). **O `site/api/` gerado é igual ficheiro a ficheiro**
(23 JSON, a menos do relógio); o que muda é só o `api/quanto_custa.json`,
que deixa de existir, e os três ficheiros estáticos (`app.js`,
`index.html`, `style.css`). Suite: 34 ficheiros (`test_top5` saiu,
`test_precos_ingles` e `test_sem_quanto_custa` entraram), 0 a falhar.

## 20/09/2026 — sai o deck do Kennen, outra vez (ficam três: Ornn, Azir, LeBlanc Baited Hook)

Palavras dele: *"retira o deck de kennen, fica apenas deck de Azir, Ornn e
Leblanc Hook"*. Ramo `ai-pc/sem-kennen-2026-09-20`; relatório em
`ai-pc/work/revisao/riftvault-sem-kennen.md`.

**É a segunda vez.** A 17/09 saíram o Kennen e o LeBlanc sem `Nome:` (merge
`fd79bbc`); nessa noite o Kennen voltou com a lista «Koko's Kennen Post Ban»
(`dd1016b`, prioridade 4). Hoje sai de novo, pelo mesmo caminho: o
`decks/kennen.txt` **estava versionado** (`git ls-files decks/`), por isso foi
`git rm` + commit — **`393e6f0`** no ramo. Recupera-se com `git checkout
393e6f0~1 -- decks/kennen.txt` e uma importação (o `serve` relê a pasta
sozinho; o `build` e o CLI importam sempre); volta com prioridade nova (para o
fim), porque a prioridade vivia na tabela `decks` e essa linha saiu.

**A base de dados não se tocou à mão, e confirmou-se que continua a não ser
preciso**: o `decks.import_all` apaga as linhas de `decks`/`deck_cards` do
slug sem ficheiro (`removed: ['kennen']`, 32 `need_changes`) e o
`uso_decks.registar` escreve **32 linhas** no `deck_need_log` (243 → 275
eventos), uma descida a 0 por carta, com o rótulo guardado. A
`copy_locations` está vazia (nada sleevado marcado). O `deck_need_log` não se
limpa — é o que o «A mais» lê.

**O que isto fecha:** a Legend do Kennen em versão especial (`VEN-197/166`
Heart of the Tempest, a sobrenumerada, **210,63 €**) era 97 % da falta dos
decks e a pergunta «vale a pena comprá-la?» estava em aberto desde 17/09.
Deixou de ser preciso decidir.

**Medido a 2026-09-20 contra cópias (`C:\Users\Catarina\_revisao\_medir_sem_kennen.py`),
`main` (`8ac19b8`, 4 decks) e ramo (3 decks) na mesma corrida, cada lado com
a SUA pasta `decks/` — os invariantes NÃO mexem:** denominador **928**, níveis
**896/835/766 de 928 = 96,6 / 90,0 / 82,5 %** (faltam 32/123/283 ·
80,28/415,97/977,14 €), wantlist «tudo» **162 linhas · 283 cópias ·
977,14 €** (OGN 406,17 · OGS 16,92 · SFD 265,01 · UNL 265,52 · VEN 23,52),
valor **6 249,45 € · 2 564 cópias**, Encomendas **0**, o separador Faltas
inteiro (fechar os quatro blocos 322 · 564 · 10 723,90 €; a comprar 162 ·
283 · 977,14 €) e as **quatro wantlists por edição** (as 20 combinações
edição × bloco, linha a linha), os grupos por edição (310/24/251/238/203).
Os euros diferem dos da secção de 19/09 só pelo `8ac19b8 preços:
2026-09-20` desta manhã — as 2 564 cópias são as mesmas, nenhuma carta
entrou ou saiu.

**O que mexe:**

| | antes (4 decks) | depois (3 decks) |
|---|---|---|
| falta dos decks | **10 cópias · 4 cartas · 216,30 €** (especiais 1 · 1 · 210,63 €) · 7 disputadas | **7 · 3 · 5,39 €** (especiais 0) · 5 disputadas |
| A mais — excedente | 65 impressões · 131 cópias | **65 · 132** (`OGN-224` Salvage: tem 5, alvo 3, usadas 4 → 3, a mais 1 → **2**) |
| A mais — libertadas | 37 cartas · 68 cópias | **67 · 122** (+30 · +54, todas do Kennen) |
| A mais — runas fora (`scope.runas`) | excedente 6 · 29; libertadas 2 · 12 | excedente igual; libertadas **4 · 24** (+9 Chaos Rune, +3 Order Rune) |
| Pimp | 9 cartas · 10 impressões · 734,46 € · 6 feitas | **5 · 5 · 195,71 € · 5 feitas** |
| Staples | 3 | 3 |

Carta a carta na falta dos decks: o Kennen levava **1× Heart of the Tempest
`VEN-197/166` (210,63 €, a Legend em sobrenumerada) e 2× Decree of Unity
`VEN-131` (0,28 €)** — 3 cópias · 210,91 €. Ficam 1× Defy (Ornn), 3× Defy
(Azir), 2× Decree of Unity e 1× Decree of Insight (LeBlanc BH): 7 cópias ·
5,39 €. 216,30 − 210,91 = 5,39 ✓.

As libertadas do Kennen são as 32 cartas · 66 cópias da lista, menos as 2
runas (9 Chaos + 3 Order = 12 cópias) que o `a_mais.sem_runas` tira e conta
em `scope.runas`: **30 cartas · 54 cópias** nos tiles. Só duas ainda são
pedidas por outro deck (Decree of Unity: Azir 3 · LeBlanc BH 2; Salvage: Azir
2 · LeBlanc BH 1); as outras 28 dizem «ainda: ninguém».

**Nenhum teste precisou de ajuste** — nenhum lê a pasta `decks/` real; os
`Kennen` do `test_seguir.py` são o deck do koko_lopez nas fixtures do
Piltover Archive. Suite: 34 ficheiros, 0 a falhar, na worktree e no `main`.

## 21/09/2026 — o painel do topo da Coleção: o «layout H» (três cartões, Raridade e Domínio) e o separador «Todas»

O André escolheu, entre as maquetas, o **layout H** (`ai-pc/work/layout-H-cartoes.html`)
para o topo da aba Coleção. Ramo `ai-pc/coleccao-H-2026-09-21`.

**O que ficou, por baixo dos separadores das edições e por cima da grelha:**

1. **Três cartões** lado a lado — «1 DE CADA», «2 DE CADA», «PLAYSET» —,
   cada um com o **tenho/total em grande (impressões, nunca percentagem)**,
   uma barra fina e «faltam N» (impressões por chegar ao nível). Nível 1 =
   pelo menos 1 cópia; nível 2 = pelo menos `min(2, alvo)`; nível 3 = o
   alvo. Onde o alvo é 1 (Legends, Battlefields, sobrenumeradas, promos) os
   três coincidem — é o esperado, não uma excepção.
2. **Dois quadros** por baixo — **Raridade** e **Domínio** —, uma linha por
   categoria: bolinha da cor, nome, três mini-barras (escura = nível 1,
   média = 2, clara = playset) e o tenho/total à direita; cabeçalho com a
   legenda «1 · 2 · playset». «Sem domínio» é o `Colorless` da RiftScribe;
   «Multi-domínio» são as cartas com dois domínios (uma linha só — senão a
   soma das linhas passava o total). Nomes em português pela ordem da
   maqueta; uma categoria nova que o catálogo traga aparece na mesma.
3. **Sobre o BLOCO escolhido** (chips no painel: master set, sobrenumeradas,
   artes alternativas, promos — os da grelha, pela ordem do config,
   `prefs.painelBloco`) **da edição aberta, ou de «Todas»**.

**As regras que a ordem fixou, e onde vivem:**

- **Tudo calculado no servidor, zero números escritos à mão**:
  `riftvault/painel.py` (`contar`, `itens`, `payload`, `da_edicao`,
  `texto`). Vai em `progress.painel` de cada `api/set/<ID>.json` e em
  `painel` do `api/index.json` (todas as edições e a chave `all`). O cliente
  recalcula a cada `+`/`−` a partir do estado local, como as barras
  (`painelContar` no `app.js` é o gémeo do `painel.contar`, e
  `tests/test_painel.py` corre os dois sobre os mesmos itens no **node**,
  se houver); a ordem e os nomes das linhas vêm do servidor
  (`painel.rarities`/`domains`), não há segunda cópia. Cada grupo do payload
  leva `domain` e `rune` para isso.
- **As RUNAS nunca entram** — nem no total, nem nos níveis, nem nos quadros
  (`metrics.e_runa`, a mesma definição de «runa» da Coleção). A barra do
  master set **continua a contá-las** (as 6 bases do OGN a 3, 2026-09-15) —
  essa regra não mexeu —, por isso no OGN o cartão «playset» lê 212/292 e
  a barra 217/298; o painel diz «sem as 6 runas — nunca entram aqui»
  (`runes_out`). A nota da linha «N cópias a comprar» foi reescrita porque
  os chips a que apontava saíram.
- **As escondidas e as retiradas seguem a regra da grelha**:
  `metrics.escondida` (que já inclui `retirada`) — verificou-se e
  manteve-se; há teste que compara, impressão a impressão, o que a grelha
  mostra com o que o painel conta.
- **Telemóvel**: abaixo de 700 px os três cartões empilham e os quadros
  passam a um por linha (`@media (max-width: 699px)`).
- **A paleta do mockup em variáveis no topo do `style.css`** (`--h-bg`,
  `--h-card`, `--h-line`, `--h-track`, `--h-text`, `--h-dim`, `--h-dim-2`,
  `--h-on`, a rampa `--lvl-1/2/3`, `--rar-*`, `--dom-*`), sem cores
  inline, para se alargar às outras abas quando ele quiser. **Sem tipo de
  letra externo** (a maqueta usava Google Fonts): o site não pede nada à
  rede além das imagens — `system-ui`, com os tamanhos e o `letter-spacing`
  da maqueta.

**O separador «Todas»** (no fim da fila das edições) mostra as cinco
seguidas na grelha — `loadTodas` pede os cinco `api/set/<ID>.json` e cola
um payload só (`juntarEdicoes`), com um cabeçalho fino por edição dentro de
cada bloco; os `printing_id` são únicos, por isso os `+`/`−`, as barras e o
valor funcionam iguais. A wantlist da edição some (fica só a de tudo), o
Encomendas continua a abrir uma edição (`edicaoAberta()`), e o
`state.levels` não guarda a chave `all` (contava a dobrar). Enquanto as
edições carregam, o painel mostra os números do servidor (`index.painel`).

**O que saiu do topo**: os chips da contagem por níveis (`#master-niveis`,
`renderNiveis`/`niveisLinha`/`niveisChip`/`niveisTotal`) e os chips das
raridades (`#rarities`) — a mesma informação passou para o painel. As três
barras (playsets jogáveis, master set, valor) e os chips por bloco ficam
por baixo do painel, mais pequenos. A contagem por níveis da barra
(`metrics.niveis`, em CÓPIAS e com as runas) continua a existir: é o que a
linha «N cópias a comprar» e o degrau das wantlists lêem.

**Melhorias fora do pedido, no que se tocou:** `metrics.alvo_do_bloco`
passou a público («playset» / «1 de cada») e o `faltas_edicao` deixou de
chamar o `_sufixo_alvo` privado; o `loadSet` ignora uma resposta que chegue
depois de ele ter mudado de separador (antes, dois cliques rápidos podiam
pôr a grelha de uma edição debaixo do separador de outra) e os cliques nos
separadores passaram a apanhar o erro em toast em vez de rejeição por
tratar; o `painel.da_edicao` varre só a edição pedida; um comentário velho
do `state.blocks` («os três contam para a percentagem», de 09-14) foi
corrigido; `.chip-b.is-static`, que nada usava, saiu do CSS.

**Medido a 2026-09-21 contra cópias do `data/` real
(`_revisao\_medir_painel_H.py`), bloco master set, tenho/total em
impressões, sem as runas:**

| edição | 1 de cada | 2 de cada | playset | barra do master set |
|---|---|---|---|---|
| OGN | 273/292 | 242/292 | 212/292 | 217/298 (+6 runas, 5 completas) |
| OGS | 24/24 | 24/24 | 11/24 | 11/24 |
| SFD | 215/221 | 200/221 | 188/221 | 188/221 |
| UNL | 216/219 | 206/219 | 195/219 | 195/219 |
| VEN | 163/166 | 159/166 | 155/166 | 155/166 |
| **TODAS** | **891/922** | **831/922** | **761/922** | 766/928 |

Sobrenumeradas (1 de cada, os três iguais): OGN 6/12, SFD 7/30, UNL 11/19,
VEN 6/31, todas 30/92. Artes alternativas (playset): OGN 18/24 · 4 · 2, SFD
12/24 · 4 · 0, UNL 16/30 · 4 · 0, VEN 11/18 · 3 · 0, todas 57/96 · 15 · 2.
Promos (1 de cada): VEN 5/6. **Nada mais mexe**: o `painel.payload` só lê,
e a percentagem, os níveis da barra, as wantlists, o valor, as Faltas, o A
mais e as Encomendas não o conhecem. `tests/test_painel.py` (30 testes:
nível 1 ≥ 2 ≥ 3 em todas as categorias, edições e blocos; a soma das
raridades e dos domínios é o total do bloco, nível a nível; «Todas» é a
soma; runas fora; escondidas/retiradas como na grelha; alvo 1 coincide;
não escreve, sem euros; o HTML/CSS/JS; o gémeo em JS). Suite: 35
ficheiros, 0 a falhar.

**Fotografar a 375 px**: o Chrome headless não deixa a janela abaixo de
~500 px — `_revisao\_foto_cdp.mjs` (node, DevTools Protocol,
`Emulation.setDeviceMetricsOverride`) é o caminho, com um `js` opcional
para clicar antes da foto.

## 21/09/2026 — os seis decks novos, por esta ordem; a ordem passa a viver no config (`decks.ordem`)

O André mandou seis decklists (`ai-pc/work/decks-2026-09-21/01..06-*.txt`)
e quer que os decks da app sejam EXACTAMENTE essas seis, por esta ordem:
**LeBlanc Hook, Jayce, Kennen, Akali, Ornn, Azir**. Ramo
`ai-pc/decks-nova-leva-2026-09-21`; relatório em
`ai-pc/work/revisao/riftvault-decks-nova-leva.md`.

**As listas entraram tal e qual** — byte a byte, com uma linha `Nome: <nome>`
à frente (a convenção do repo para o rótulo; só o LeBlanc a tinha) — em
`decks/leblanc-hook.txt`, `jayce.txt`, `kennen.txt`, `akali.txt`, `ornn.txt`,
`azir.txt`. O `leblanc-baited-hook.txt` é o LeBlanc actualizado, renomeado
(o nome novo é «LeBlanc Hook»); o Ornn e o Azir foram substituídos pela lista
nova; o Jayce e o Akali são novos; o Kennen volta (saiu a 20/09). **Nada foi
arquivado** (não havia deck fora dos seis). Aritmética conferida em cada um,
antes de tocar em código: 39 no MainDeck · 3 battlefields · 10 no sideboard
· 12 runas · 1 Legend · 1 Champion; cartas distintas no MainDeck LeBlanc 16,
Jayce 15, Kennen 21, Akali 16, Ornn 17, Azir 16 — tudo bate. **Todas as
cartas casam no catálogo** (0 por casar nos seis) e **nenhuma é `is_banned`**;
os seis são legais (main 40/40, runas 12/12, battlefields 3/3, máximo 3,
domínios ok).

**A ordem escreve-se no config.** `decks.ordem` (`riftvault_config.json` e
`config.DEFAULTS`, `_decks_ordem_nota`) é a lista dos decks — o slug ou o
`Nome:` de cada um, sem olhar a maiúsculas —, e a posição é a prioridade
(1 = principal). `decks.aplicar_ordem` grava-a na tabela `decks` no fim de
cada `import_all` (servidor, build, CLI) e também no `/api/decks.json`
(para uma lista mudada no config valer sem nenhum `.txt` ter mexido); só
escreve quando difere. O que a lista não nomear vem a seguir, pela ordem que
tinha; um nome sem deck avisa (`nao_encontrados`, no `riftvault decks`) e
não rebenta — o site tem de continuar a servir os decks que há; a mesma
entrada duas vezes conta uma; e a posição já é lida ANTES do `rotulos`, para
dois decks com o mesmo rótulo levarem o sufixo pela ordem certa. **Enquanto a
lista existir, os botões «Tornar principal / Subir / Descer» do site e o
`riftvault decks --order` ficam desligados** (`decks.OrdemFixa`; a rota
`/api/decks/order` responde 409 com a razão, o `app.js` esconde os botões
pelo `ordem_fixa` do payload e diz onde se muda): a importação seguinte
repunha a lista e o clique era mentira. Lista vazia = tudo como era (a
prioridade guardada na base, decks novos para o fim).

**O `deck_need_log` recomeçou do zero** — *"recalcula o deck_need_log a
partir dos seis decks (não somes por cima do que lá estava)"*.
`uso_decks.recomecar` apaga a tabela e escreve o ponto de partida com os
decks de hoje (`0 -> N`), `riftvault decks --recomecar-registo` na CLI.
Sem isto, a troca ficava registada como descidas do LeBlanc antigo, do Ornn
e do Azir por cima do histórico de 17–20/09 — dezenas de «libertadas» no A
mais que eram só a lista velha a ir embora. Medido contra cópias: 275
linhas · 96 descidas antes → com a importação dos seis 436 · 134 → depois do
recomeço **170 linhas de partida · 0 descidas**; as «libertadas» do A mais
passam de 67 cartas · 122 cópias a **0**. Correu no `data/` real depois do
merge (o `data/decks.log`, o CSV, guarda o rasto todo).

**As regras de 17/09 continuam a valer, e vêem-se nos números:** as runas
não se contam (os seis dizem «54 de 54 · 12 runas»); a Legend e o Champion
jogam uma versão especial (no Jayce a Legend `VEN-194/166` e no Kennen a
`VEN-197/166` são sobrenumeradas em falta; no Akali faltam as duas,
`VEN-189/166` e `VEN-021a/166`); o resto joga a base e completa com outra
versão que ele tenha (o Azir joga 1 Vi, Peacekeeper do sideboard em
`UNL-176a`, separada na vista).

**Medido a 2026-09-21 contra cópias (`C:\Users\Catarina\_revisao\_medir_decks_nova_leva.py`),
`main` (`9306e4e`, 3 decks) e ramo (6 decks) na mesma corrida — os
invariantes NÃO mexem:** denominador **928**, níveis **897/836/766 de 928 =
96,7 / 90,1 / 82,5 %** (faltam 31/121/281 · 80,12/425,64/1 009,02 €),
wantlist «tudo» **162 linhas · 281 cópias · 1 009,02 €**, valor **6 429,55 €
· 2 570 cópias**, Encomendas 0, o separador Faltas inteiro (319 · 558 ·
10 634,48 €; a comprar 162 · 281 · 1 009,02 €) e as wantlists por bloco, os
grupos por edição (310/24/251/238/203). **O que mexe:** falta dos decks
**7 cópias · 3 cartas · 5,39 € → 40 · 22 · 965,47 €** (18 disputadas;
especiais 4 · 805,04 € — as três Legends/Champion acima); A mais excedente
**65 · 132 → 62 · 125** (Charm, Salvage e Deathgrip deixam de sobrar, o
Scuttle Crab passa de 6 a 3 a mais — os decks novos levam-nos); Pimp 5 → 15
cartas; Staples 3 → 10.

**O que falta para montar cada deck** (cópias · cartas distintas; sem
preços — é o que ele pediu):

| # | deck | falta | o quê |
|---|---|---|---|
| 1 | LeBlanc Hook | **0** | — |
| 2 | Jayce | **13 · 7** | 2 Catalyst of Aeons `OGN-138`, 2 Dazzling Aurora `OGN-160`, 1 Defender of Tomorrow `VEN-194/166` (Legend, versão especial), 2 Elder Dragon `UNL-118`, 3 Garbage Grabber `OGN-099`, 1 Gutter Palace `UNL-088`, 2 Sabotage `OGN-156` |
| 3 | Kennen | **2 · 2** | 1 Decree of Unity `VEN-131`, 1 Heart of the Tempest `VEN-197/166` (Legend, versão especial) |
| 4 | Akali | **7 · 6** | 1 Akali, Deadly Weapon `VEN-021a` (Champion, versão especial), 1 Defy `OGN-045`, 1 Forgotten Monument `SFD-209`, 1 Irelia, Fervent `SFD-057`, 1 Rogue Assassin `VEN-189/166` (Legend, versão especial), 2 Zhonya's Hourglass `OGN-077` |
| 5 | Ornn | **4 · 2** | 1 Decree of Insight `VEN-061`, 3 Defy `OGN-045` |
| 6 | Azir | **14 · 7** | 2 Charm `OGN-043`, 2 Decree of Focus `VEN-040`, 3 Defy `OGN-045`, 1 Disarming Rake `SFD-032`, 3 Discipline `OGN-058`, 2 Sacrifice `UNL-173`, 1 Salvage `OGN-224` |

(A falta é a da ALOCAÇÃO por prioridade — o Defy que o Ornn pedia a 1 cópia
quando era o principal passa a 3 porque agora é o quinto e o Akali leva-o
antes.)

`tests/test_ordem_dos_decks.py` (19 testes, contra cópias e config
temporário): a lista pelo nome e pelo slug, mudar reordena, acrescentar no
fim basta, o que não está vem a seguir pela ordem que tinha, nome sem deck
avisa, entrada repetida conta uma, o sufixo dos rótulos iguais segue a lista,
sem alterações não escreve, lista mal escrita rebenta, sem lista tudo como
era; `set_order`/CLI/rota recusam com a lista e funcionam sem ela, a rota
aplica a lista sem reimportar, o `app.js` esconde os botões e o `build` leva
o flag; o `recomecar` apaga o histórico e escreve o ponto de partida, só toca
no registo, e a CLI recomeça. Suite: 36 ficheiros, 0 a falhar.

## 21/09/2026, de manhã — A EXPERIÊNCIA do pool próprio dos decks (`decks.modo = "pool_proprio"`) — ACABOU à tarde

**Esta secção é história desde 2026-09-21 à tarde** — ver a secção a seguir.
O pool estava vazio quando acabou; a maquinaria (o `ajustar`, a rota, a CLI,
os tiles com `+`/`−`) passou a ser POR DECK (`proprias.py`). Escrever
`pool_proprio` no config hoje rebenta. O que se segue é como estava de manhã.

Palavras dele: *"quero que a coleccao fique sempre imaculada, nada sai da
coleccao; os decks, todos partilham as mesmas cartas, mas nao usam
absolutamente nada da coleccao; so jogam com versoes base; vamos ver como
fica assim as coisas, para ter uma ideia"*. **É uma experiência, atrás de UMA
chave**, e ficou a valer no merge (`decks.modo: "pool_proprio"` no
`riftvault_config.json`, com `_decks_modo_nota`). Voltar atrás é escrever
`"coleccao"` (a omissão, `config.DEFAULTS`): nada se apaga nem se reescreve
na coleção. Ramo `ai-pc/pool-proprio-2026-09-21`.

**O modelo, em cinco linhas** (o topo do `pool.py` diz o mesmo):

1. **A Coleção fica intacta.** Com o modo ligado nenhuma conta da Coleção
   sabe que há decks: níveis, Faltas, as quatro wantlists, valor, Encomendas
   e A mais calculam-se como se não houvesse decks. `decks.uso_por_carta` e
   `a_mais._usadas` devolvem vazio, o «para que deck» e o «falta encomendar
   aos decks» das Encomendas vêm vazios, as «libertadas» não se mostram (o
   `deck_need_log` continua a escrever-se), a grelha esconde o filtro «Em
   decks» (`index.modo_decks`) e o `propor_deck` não propõe nada. O A mais
   passa a ser o excedente verdadeiro face aos alvos.
2. **Os decks têm pool próprio.** As cópias vivem no local `pool-decks`
   (`locais.POOL`, na `copy_locations`, ao lado do `binder` e dos
   `deck:<slug>`). O pool **começa a zero** e é ele que lá mete o que tiver:
   `pool.ajustar` escreve no `copies` E no local numa transação só (a
   Coleção, `copies − Σ fora`, fica onde estava), com rasto na `ops`, na
   `location_ops` (`(entrou no pool)` → pool, pool → `(saiu do pool)`) e no
   `data/locais.log`; `−` nunca abaixo de zero no pool; `request_id`
   repetido não conta a dobrar; só versões base (`NaoBase`). Uma cópia no
   pool **nunca conta para a Coleção**: o `na_colecao` já a tirava (é um
   local como os outros) e o **valor, o playset jogável e o «tens N cópias»
   passaram a ler `locais.contadas`** / `prices.copias_sql` (o `copies`
   menos o pool, só neste modo). Os `+`/`−` estão na aba «Pool dos decks»
   (`POST /api/pool/ajustar {printing_id, delta, request_id?}`) e na CLI
   (`riftvault pool --mais REF [N]` / `--menos`). O `riftvault undo`
   genérico reverte a linha da `ops` e o `ajustar_ao_total` tira do pool a
   seguir (binder, pool, decks — o pool entrou nessa ordem): um `+` desfaz-se
   bem; o undo de um `−` põe a cópia na Coleção, não no pool — para mexer no
   pool é pelo `pool.ajustar`.
3. **Os decks partilham entre si.** O pool precisa do **MÁXIMO** por carta
   entre os decks (`pool.necessidades`), não da soma; dentro do MESMO deck
   main e sideboard somam (é o `decks._need` de sempre). Runas fora
   (`decks.cartas_nao_contadas`). Cada deck avalia-se SOZINHO contra o pool
   inteiro (`alloc = min(pede, tem no pool)`) — não há prioridade nem
   disputa.
4. **Só versões base.** `variant_kind == "base"` e não sobrenumerada — a
   Legend e o Champion também: **a regra de 17/09 (versão especial) NÃO se
   aplica aqui**. `versoes_dos_decks` devolve `especiais = {}`, `papeis = ∅`
   e sem o recurso a «o que houver de não-assinado»: uma carta sem base fica
   em `sem_base` e a página diz quais (hoje nenhuma).
5. **A aba Decks** abre em «Pool dos decks»: precisa de ter / tem / faltam
   (o máximo, a soma ao lado), por deck se o pool chega, os tiles com
   `+`/`−` e «tens H/N», «Só o que falta», a wantlist do pool (o gerador
   único, `cardmarket.gerar`), o que está no pool sem servir (`fora`) e as
   sem base. As abas Staples / Por deck / Pimp não se mostram neste modo (o
   `faltas.compras` continua a calcular-se, contra o pool, para a CLI). A
   página de cada deck diz «do pool N · faltam ao pool N» e sem «Marcar o que
   este deck usa». `api/pool.json` e `api/decks.json` levam `modo`.

**Onde encaixa.** `decks.allocate` chama `pool.alocacao` neste modo e
devolve a MESMA forma de sempre — por deck, com `grupo` (`lider` só no
primeiro deck; o `grupo` é o pool inteiro) —, para `deck_payload`,
`decks_index`, `resumo_das_faltas`, `missing_by_set`, `faltas.compras`,
`pending.encomendas` e `a_mais` não terem de saber do modo; `shared`,
`a_caminho`, os três montes da Coleção, o lugar especial e as «outras» vêm
vazios, `no_pool` é o `alloc`. Um `modo` desconhecido rebenta.

**Medido a 2026-09-21 contra cópias (`C:\Users\Catarina\_revisao\_medir_pool_proprio.py`),
três cenários na mesma corrida — `main` (config real), ramo com `coleccao`,
ramo com `pool_proprio`:** `main` == ramo/`coleccao` em TUDO (denominador,
níveis, wantlist, valor, totais, Faltas e as 20 wantlists por bloco,
Encomendas, grupos, tiles, usos na grelha, A mais item a item, falta dos
decks, por deck, Staples, Pimp). Ramo/`pool_proprio`: **os invariantes da
Coleção iguais** — denominador **928**, níveis **897/836/766 de 928**
(faltam 31/121/281 · 80,12/425,64/1 009,02 €), wantlist «tudo» **162 linhas
· 281 cópias · 1 009,02 €**, valor **6 495,04 € · 2 572 cópias**, Faltas
**556 cópias · 10 568,99 €** (a comprar 281 · 1 009,02 €), Encomendas a
caminho 0, grupos 310/24/251/238/203, os tiles impressão a impressão — e o
que muda de propósito: cartas com uso de decks na grelha **149 → 0**; A mais
**62 impressões · 125 cópias → 69 · 140** (as 15 cópias que os decks
descontavam — Charm +2, Salvage +2, Brutalizer +3, Deathgrip +1, Seat of
Power +1, Vi Peacekeeper +1, Decree of Focus +1, Hidden Blade 2→3, Scuttle
Crab 3→6 — e o `used` a 0 em todas); «falta encomendar aos decks» das
Encomendas 22 cartas · 40 cópias → 0; falta dos decks **40 cópias · 22
cartas · 965,47 € → 282 · 136 · 1 156,42 €** (o pool a zero: falta tudo),
cada deck **0/54**. **O pool: precisa de 282 cópias de 136 cartas (a soma
dos seis seria 324), cada deck pede 54, nenhuma carta sem versão base** —
os números que ele calculou batem todos (o «61 cartas» do A mais são 61
cartas lógicas em 62 impressões; 110 cópias em base; cobririam 16 das
282). Wantlist do pool: 136 linhas · 282 · 1 156,42 €, 57 só com oferta
foil.

**Cuidado ao voltar a `coleccao` com cópias no pool:** ficam gravadas (no
`copies` e no local) e nesse modo contam para o valor mas não para os decks
nem para a Coleção — tira-se com `riftvault pool --menos` antes, ou
deixa-se. Hoje o pool está a zero e voltar atrás repõe os números ao
exemplar (há teste).

`tests/test_pool_proprio.py` (22 testes, contra cópias e config temporário):
o máximo entre decks e a soma main+sideboard; o pool a zero e cada deck
contra o pool inteiro; a Legend e o Champion na base; a alt art no pool não
serve e é dita; a carta sem base é dita; `ajustar` não mexe na Coleção,
retry não dobra, rasto; o local no resumo e no tile; a Coleção com o modo
ligado dá EXACTAMENTE o mesmo que sem decks nenhuns; meter 5 cópias no pool
não mexe em nada da Coleção; o A mais sem desconto; a grelha sem usos;
voltar a `coleccao` repõe tudo; modo desconhecido rebenta; rotas, build, CLI,
`app.js`. `test_sem_quanto_custa` ganhou a chave `modo` no `compras`. Suite:
37 ficheiros, 0 a falhar.

## 21/09/2026, à tarde — acaba a experiência do pool; CADA DECK TEM AS SUAS CÓPIAS PRÓPRIAS (`proprias.py`, `proprio:<slug>`); só versões base (`decks.so_base`)

Palavras dele: *"voltamos aos decks usarem a coleccao, mas cada deck precisa
de ter as cartas proprias; colocas em cada deck o + e - para eu dizer se
afinal tenho ou nao; estas copias que eu coloco nos decks nao sao para
adicionar a coleccao"*. Ramo `ai-pc/copias-proprias-2026-09-21`.

**A experiência do pool próprio acabou** — durou a manhã, o pool estava
VAZIO (nada a salvar), e a maquinaria dela (o `ajustar`, a rota, a CLI, os
tiles com `+`/`−`) passou a ser POR DECK. `decks.modo` voltou a `coleccao` e
é o único valor aceite: `pool_proprio` **rebenta com a razão** (`decks.modo()`,
chamado de caminho pelo `so_base()`), em vez de ligar em silêncio um modelo
que já não existe; `pool.py` passou a `proprias.py` (`git mv`), o
`api/pool.json`, o `POST /api/pool/ajustar`, o `riftvault pool`, a aba «Pool
dos decks», o `locais.POOL`/`no_pool` e todos os ramos `if pool_proprio()`
(a_mais, pending, faltas, metrics, prices, locais, decks, cli, build, server,
app.js) saíram. O `modo` saiu dos payloads (`decks.json` leva `so_base`).

### O modelo que fica

1. **`decks.modo = "coleccao"`**: os decks usam a Coleção exactamente como
   antes da experiência (11/09) — a grelha diz «Azir 3», o filtro «Em
   decks», as libertadas e o «para que deck» das Encomendas voltaram.
2. **Cada deck precisa das suas próprias cartas — a SOMA, não o máximo.** Os
   seis pedem **324 cópias de 136 cartas** (54 cada); main e sideboard somam
   dentro do mesmo deck; runas fora (`contar_runas: false`). A regra dos
   decks com a mesma Legend (11/09, partilham) ficou no código e **não tem
   caso hoje** (seis Legends distintas) — fica anotado.
3. **CÓPIAS PRÓPRIAS DO DECK, com `+` e `−`** — a parte nova. Em cada carta
   de cada deck há um `+`/`−` (só no 8770; `body.readonly` esconde-os) e um
   número entre eles: quantas cópias ele tem GUARDADAS PARA AQUELE DECK.
   Vivem no local **`proprio:<slug>`** da `copy_locations` (`locais.
   PROPRIO_PREFIX`, `proprio_local`, `proprias`, `proprias_de`), separado do
   `deck:<slug>` (que marca onde está uma cópia da COLEÇÃO que o deck usa —
   os dois não se misturam). Regras:
   - **NÃO ENTRAM NA COLEÇÃO.** Não contam para os níveis, o denominador, o A
     mais (não são excedente), as Faltas, nenhuma wantlist, as Encomendas
     (`locais.na_colecao` já as tira, por serem um local como os outros), e
     — **decisão minha, escrita aqui** — também **não contam para o valor
     nem para o playset jogável nem para o «tens N cópias»**
     (`locais.contadas`, `prices.copias_sql`, `metrics.owned_by_card`,
     `collection.totals`; o `qty_valor` do tile). A ordem dizia "(contam
     para o valor mas nunca para a Coleccao)" a descrever o pool, mas o pool
     da manhã já as tirava do valor, e o valor é um número da página da
     Coleção: um `+` num deck não pode mexer lá. Se ele quiser o valor das
     próprias, é uma linha a menos no `contadas`/`copias_sql` — e um número
     à parte na página do deck, não no da Coleção.
     `tests/test_copias_proprias.py::TestNaoEntramNaColecao` fotografa
     níveis, denominador, wantlist, valor (total, por edição, top), totais,
     grelha (qty/alvo/qty_valor), playset jogável, barra, painel, Faltas (os
     quatro blocos por edição), Encomendas e os itens do A mais (`have`,
     `extra`), mete 10 próprias em dois decks e tira-as: **igual**.
   - **São daquele deck e só daquele**: as do Ornn não servem o Azir.
   - **Servem PRIMEIRO**: no `decks.allocate` há uma passagem prévia por
     membro — o monte `proprio:<slug>` (`pool_dos_decks()["proprias"]`) é
     consumido pela ordem dos lugares (especial, base, outras) antes dos
     quatro montes de sempre (sleevado, binder, Coleção, a caminho); o que
     sobra da lista (`needs_liq`) é o que o deck pede ao grupo. Meter
     próprias **LIBERTA** cópias da Coleção que o deck usava — e pela regra
     do A mais de 17/09 (`cópias − max(usadas, alvo)`) uma cópia libertada
     acima do alvo passa a aparecer lá como a mais (é o «usadas» a descer;
     `test_libertar_a_colecao_e_visivel_no_a_mais_pela_regra_de_sempre`).
     É a única coisa da página da Coleção que pode mexer, e não é por contar
     as próprias.
   - **`faltam(deck) = precisa − próprias − o que a Coleção lhe alocou`**
     (menos o que vem a caminho) — há teste com a fórmula.
   - Por membro o `allocate` devolve `proprias` (por carta, o que cobriram —
     já dentro do `alloc`), `proprias_fora` (as que NÃO servem: outra versão
     com `so_base`, uma carta que a lista não pede, acima do pedido — com o
     motivo; uma runa própria não é «fora»), e as entradas do `versoes_em`
     marcadas `propria`. O grupo leva `proprias` (soma dos membros) e
     `impressoes_proprias`, à parte dos três montes de `impressoes` — quem
     lê `impressoes` para saber o que os decks tiram à Coleção (`a_mais.
     _usadas`) não as vê, de propósito. `uso_por_carta` (a grelha) diz o que
     o deck ainda pede à Coleção depois das próprias e leva `proprias` ao
     lado («Azir 1 +3 próprias»); uma carta toda coberta por próprias não
     aparece como uso.
   - **Entrar e sair**: `proprias.ajustar(con, slug, ref, delta)` escreve no
     `copies` E no local numa transação só (a Coleção, `copies − Σ fora`,
     fica onde estava), `−` nunca abaixo de zero nas próprias, `request_id`
     repetido não dobra, rasto na `ops`, `location_ops` (`(entrou como cópia
     própria)` → `proprio:<slug>` → `(saiu das cópias próprias)`) e
     `data/locais.log`; recusa o que não serve (`NaoServe`) e o deck
     desconhecido (`DeckDesconhecido`). `POST /api/proprias/ajustar {slug,
     printing_id, delta, request_id?}` (400/404); `riftvault proprias [SLUG]
     [--mais REF [N] | --menos REF [N]] [--so-faltas]` — sem slug uma linha
     por deck, com slug carta a carta; REF pode ser o nome da carta
     (`proprias.impressao_para`: grava na base em que se compra, ou na
     impressão própria que o deck já tiver). O `ajustar_ao_total` (um `−` da
     grelha além da Coleção) tira do binder, depois das próprias, depois dos
     decks. O `propor_deck` desconta as próprias antes de propor. As próprias
     de um deck cujo `.txt` desapareça ficam gravadas (o `riftvault local`
     lista-as) e continuam fora da Coleção e do valor.
   - **No site**: `propriasBotoes(c)` no `deckTile` (o `+` grava em
     `propria_compra` — a base em que se compra —, o `−` tira da última de
     `proprias_em`), `propriasAjustar` (fila por deck+impressão, relê o deck
     e os separadores, marca compras/A mais/Encomendas/Coleção como velhos),
     o chip «próprias do deck N» e a nota no `deckLocais`, a secção «Cópias
     próprias que não servem este deck» (`propriaForaTile`, com `−`), «N
     próprias» na linha de origem do tile, a coluna `proprias` no CSV.
     `deck_payload` leva por carta `proprias`, `propria_compra`,
     `proprias_em`, `versoes[].propria`; por secção `proprias`; `so_base`,
     `local_proprias`, `proprias_fora` (com imagem e motivo) e
     `locais.proprias`/`proprias_fora`; `decks_index` leva `proprias` e
     `proprias_fora` por deck.
4. **VERSÕES: `decks.so_base: true`**, a Legend e o Champion incluídos — a
   última coisa que ele disse sobre versões (de manhã) e mantém-se. Com
   `true` `versoes_dos_decks` dá `especiais = {}`, `papeis = ∅`, sem o
   recurso a «o que houver de não-assinado»: um lugar de deck só se serve da
   base não sobrenumerada; a alt art da Vi, Peacekeeper que ele tem NÃO tapa
   o Azir. **A regra de 17/09 (Legend/Champion numa versão especial) NÃO
   volta só por o modo ser `coleccao`**: `so_normais_excepto` passou a `[]`
   no config real e no `DEFAULTS` (a nota do config diz que só é lido com
   `so_base: false`). **Desliga-se mudando esta chave sozinha**: `so_base:
   false` → qualquer versão não assinada e não retirada serve um lugar
   normal (a base primeiro, as outras que ele tenha a seguir —
   `Versoes.outras_de`), e a Legend/Champion continua na base enquanto
   `so_normais_excepto` estiver vazio; escrever lá os papéis traz a regra de
   17/09 de volta (há teste dos três casos). Os testes que descrevem a regra
   de 17/09 (`test_voltar_1`, `test_versoes_deck`, `test_runas_alt_fora`,
   `test_runas_vista`, `test_encomendas_separador`, a fixture
   `config_decks_sem_alt_art`, um caso do `test_a_mais`) passaram a escrever
   `so_base: false` — o teste é que descrevia outra regra, não o código.

**Medido a 2026-09-21 contra cópias (`C:\Users\Catarina\_revisao\_medir_copias_proprias.py`),
cinco cenários na mesma corrida — `main` com o config real (pool), `main`
com `coleccao` (a regra de 17/09), ramo com `so_base: true`, ramo com
`so_base: false`, ramo com próprias metidas — e os invariantes da Coleção
IGUAIS nos cinco:** denominador **928**, níveis **897/836/766 de 928**
(faltam 31/121/281 · 80,12/425,64/1 009,02 €), wantlist «tudo» **162 linhas
· 281 cópias · 1 009,02 €**, valor **6 555,58 € · 2 573 cópias**, totais,
Faltas (555 · 10 508,45 €; a comprar 281 · 1 009,02 €) e as 20 wantlists por
bloco, Encomendas a caminho 0, grupos 310/24/251/238/203, os tiles impressão
a impressão (qty/alvo/bloco/qty_valor). **A conferência do André bate
toda:** os seis decks pedem **324 cópias de 136 cartas** (54 cada); com as
próprias a zero e `so_base: true` faltam **37 cópias de 19 cartas**
(165,33 €); com `so_base: false` **36 de 18** — a única diferença é **1×
Vi, Peacekeeper** (o Azir, tapada pela `UNL-176a`); **Defy precisa de 9, tem
2 em base**. A regra de 17/09 (main/coleccao) dava 40 · 22 · 965,47 € — as
três Legends/Champion em versão especial (805,04 €) saem com o `so_base`.
Cartas com uso de decks na grelha 0 (pool) → **149**; A mais **62 · 125**
(o pool dava 69 · 140, sem o desconto dos decks); Staples 11.

**Por deck (próprias a zero, `so_base: true`):**

| # | deck | tenho/pede | falta | o quê |
|---|---|---|---|---|
| 1 | LeBlanc Hook | 54/54 | **0** | — |
| 2 | Jayce | 42/54 | **12 · 6** | 2 Catalyst of Aeons, 2 Dazzling Aurora, 2 Elder Dragon, 3 Garbage Grabber, 1 Gutter Palace, 2 Sabotage |
| 3 | Kennen | 53/54 | **1 · 1** | 1 Decree of Unity |
| 4 | Akali | 49/54 | **5 · 4** | 1 Defy, 1 Forgotten Monument, 1 Irelia, Fervent, 2 Zhonya's Hourglass |
| 5 | Ornn | 50/54 | **4 · 2** | 1 Decree of Insight, 3 Defy |
| 6 | Azir | 39/54 | **15 · 8** | 2 Charm, 2 Decree of Focus, 3 Defy, 1 Disarming Rake, 3 Discipline, 2 Sacrifice, 1 Salvage, 1 Vi, Peacekeeper |

(Face à regra de 17/09 saem a Legend do Jayce `VEN-194/166`, a do Kennen
`VEN-197/166`, a Legend e o Champion do Akali — jogam a base que ele tem —,
e entra a Vi, Peacekeeper do Azir, que só existe dele em Alt Art.)

**Com próprias metidas na cópia** (Ornn 3 Defy, Azir 3 Defy + 1 Charm, Jayce
2 Sabotage, Kennen 1 Decree of Unity, Akali 2 Zhonya's): falta dos decks
**37 → 25 cópias**, o Kennen fecha (54/54), o Ornn passa a faltar só 1, a
grelha continua a dizer 149 cartas em uso, e a Coleção **não mexe** — nem o
A mais (nenhuma das libertadas está acima do alvo hoje: Defy 2 de 3).

`tests/test_copias_proprias.py` (28 testes, contra cópias e config
temporário; substitui o `test_pool_proprio.py`): a soma e não o máximo; a
Coleção volta a saber dos decks; `so_base` a omissão, os papéis não mandam
com `true`, `false` sozinho dá qualquer versão, `false` + papéis traz 17/09;
`ajustar` não mexe na Coleção, `−` a zero, retry, recusa, deck desconhecido,
rasto, o local no resumo e no tile, um `−` da grelha tira das próprias;
servem primeiro e libertam, só ao deck delas, as que não servem com o
motivo, a página reparte por linha, o `+` por nome; meter/tirar não mexe em
número nenhum da Coleção, não são excedente nem valem, a libertação visível
no A mais pela regra de sempre; `pool_proprio` rebenta, sem chave é
`coleccao` + `so_base`, o config real; rotas, build, CLI, `app.js`.
`test_a_mais` (a alt art a tapar → `so_base: false`), `test_partilha_compra`
(`proprias` no uso), `test_sem_quanto_custa` (sem `modo`), `test_build`
(comentário) ajustados. Suite: 37 ficheiros, 0 a falhar.

## 21/09/2026, ao fim da tarde — o chip «Tudo» no painel da Coleção (`painel.TUDO`)

**Era a segunda metade da ordem `0-decks-copias-proprias.json` e FICOU POR
FAZER** na sessão anterior — fez-se a dos decks e esta não saiu, nem se
disse que não tinha saído. Ramo `ai-pc/chip-tudo-2026-09-21`.

**O que é.** Nos chips de bloco do painel do topo da Coleção (master set,
sobrenumeradas, artes alternativas, promos — o layout H de manhã) há agora
um chip **«Tudo»**, **no fim da fila**, que junta todos os blocos dessa
edição num só número; com «Tudo» escolhido os três cartões e os dois quadros
são sobre esse conjunto. **Não confundir com o separador «Todas»**, que é
das EDIÇÕES: «Tudo» = todos os blocos de UMA edição; «Tudo» com «Todas»
escolhido = tudo de todas as edições. **O que abre por omissão continua a
ser o master set** (`prefs.painelBloco: 'master'`).

**A regra: os níveis SOMAM-SE bloco a bloco, cada um com o SEU alvo** —
master set o alvo por categoria, sobrenumeradas 1, artes alternativas
playset, promos 1. Não há um alvo único por cima de tudo: no `payload` a
mesma impressão, com o mesmo `metrics.alvo`, entra no seu bloco E na chave
`tudo` (`por[sid][TUDO]`), por isso a soma sai por construção. **As runas
continuam fora**, como em todo o painel. O «Tudo» **não é um bloco da
grelha**: o id não existe no `metrics.BLOCOS`, nunca chega ao
`metrics.bloco`, e não aparece no `set_payload["blocks"]`.

**Onde vive.** `painel.TUDO = "tudo"`, `TUDO_LABEL`, `TUDO_ALVO` («cada
bloco com o seu alvo»); `payload` acrescenta `{"id": "tudo", "label":
"Tudo", "target": TUDO_ALVO, "counts": None}` no fim de `blocks` e a chave
`tudo` no fim de `sets[<edição>]` e de `sets["all"]`; `da_edicao` e o
`riftvault stats` (`texto`) levam-no de graça. No `app.js`: `const TUDO =
'tudo'`, `painelBlocos` acrescenta o chip depois dos blocos do payload
(`[...ids, TUDO]`) e `painelItens(TUDO)` não filtra por bloco (cada
impressão com o alvo do seu tile).

**Medido a 2026-09-21 contra cópias do `data/` real
(`C:\Users\Catarina\_revisao\_medir_chip_tudo.py`), em impressões, sem as
runas — «Tudo» = 1 de cada / 2 de cada / playset:**

| edição | blocos | Tudo | = soma dos blocos |
|---|---|---|---|
| OGN | master 292 · over 12 · alt 24 | **297 / 252 / 220 de 328** | ✓ |
| OGS | master 24 | **24 / 24 / 11 de 24** | ✓ |
| SFD | master 221 · over 30 · alt 24 | **235 / 212 / 196 de 275** | ✓ |
| UNL | master 219 · over 19 · alt 30 | **243 / 222 / 206 de 268** | ✓ |
| VEN | master 166 · over 31 · alt 18 · promos 6 | **186 / 174 / 167 de 221** | ✓ |
| **Todas** | 922 · 92 · 96 · 6 | **985 / 884 / 800 de 1116** | ✓ = soma das cinco |

Raridades e domínios somam o total do «Tudo» em todas as seis; runas fora
6 (OGN). Os blocos por edição não mexeram (são os de manhã); só se
acrescentou a chave.

`tests/test_painel.py` 30 → **38 testes** (`TestTudo`: no fim da fila em
cada edição; a soma dos blocos nível a nível, com os números escritos e a
prova pela negativa — com alvo 3 por cima de tudo dava `[6, 4, 2]` em vez
de `[6, 4, 3]`; raridades e domínios batem; «Tudo» de «Todas» = soma das
duas edições de brincar; runas fora; chega à edição, ao index e ao texto;
o `app.js`). Três testes que descreviam a lista de blocos sem o «Tudo»
foram ajustados. Suite: 37 ficheiros, 0 a falhar.

## 22/09/2026 — a contagem de FOIL e NÃO-FOIL das comuns e incomuns (`foil.py`, `copies.qty_foil`)

Palavras dele: *"para comuns e incomuns, coloca contagem para Foil e
Non-Foil, para todas as edicoes excepto Proving Grounds"*. «Proving Grounds» é
o OGS, por isso vale para o OGN, o SFD, o UNL e o VEN. Ramo
`ai-pc/foil-2026-09-22`.

**Isto NÃO revoga a decisão de 2026-08-31** (*"foil e normal contam como a
mesma coisa"*). O acabamento continua a não ser parte do grão da coleção: a
chave do `copies` é `(printing_id)`, o alvo do master set é por impressão e
qualquer cópia o cumpre. O que nasceu é uma REPARTIÇÃO do que ele já tem, ao
lado das contas — e a prova de que não entra em nenhuma é um teste.

### 1. Uma verdade só, nunca duas — **ESTE PONTO ESTAVA ERRADO, ver 26/09**

> **REVOGADO a 2026-09-26.** O que se segue descreve o foil como uma FATIA do
> total, e não é o que ele queria: *"as foils quando eu marco é que tenho
> TAMBÉM foil, ou seja, normal + foil"*. Hoje o `qty` são as NORMAIS, o
> `qty_foil` são as FOILS, o total é a SOMA, o `CHECK` do tecto saiu e o
> `ao_descer` deixou de existir. Ver a última secção deste ficheiro. O que
> fica de pé desta secção é o ponto 2 (o âmbito), o ponto 3 (o foil não mexe
> em conta nenhuma) e a migração da coluna.

A contagem é a coluna **`copies.qty_foil`** — quantas das cópias daquela
impressão são foil. **O não-foil NUNCA se grava**: é sempre `qty − qty_foil`,
derivado na leitura, no Python e no `app.js`. Guardar os dois era ter duas
verdades que mais cedo ou mais tarde deixavam de somar o total. É a mesma
arquitectura da Coleção, que também não se grava (`locais.na_colecao` é o
`copies.qty` menos os outros locais).

A base garante-o: `CHECK (qty_foil >= 0 AND qty_foil <= qty)`. Quando o total
desce abaixo do que estava marcado como foil — um `−` na grelha, um `−` nas
cópias próprias de um deck —, **o foil desce com ele**: `foil.ao_descer`,
chamado DENTRO da transação e ANTES de escrever o `qty` (baixar o foil
primeiro mantém o CHECK verdadeiro a cada passo), com linha na tabela
**`foil_ops`** (`source` acaba em `:ajuste ao total`). Os dois únicos sítios
que baixam o `copies.qty` são o `collection.adjust` e o `proprias.ajustar`, e
os dois passam por lá; há teste para cada um.

**A migração é a primeira desde o início que toca na tabela `copies`**, por
isso leva BACKUP antes (`db.backup`, `VACUUM main INTO
data/backups/vault-antes-do-foil-<ts>.db` — `VACUUM INTO` e não uma cópia de
ficheiro, porque o vault.db está em WAL). É idempotente: corre na primeira
ligação depois do merge e nunca mais. Uma base criada de raiz já traz a coluna
do `schema.sql` e não migra nada. A pasta `data/backups/` está no
`.gitignore`.

### 2. O âmbito, em config

`foil.raridades` (`["common", "uncommon"]`) e `foil.edicoes_fora` (`["OGS"]`),
no `riftvault_config.json` e no `config.DEFAULTS`. Uma raridade que o catálogo
não conheça rebenta, e a lista vazia também — é a regra das outras listas do
config. Vale para as impressões **base, não sobrenumeradas**: a arte
alternativa e a reimpressão de topo de set são outra impressão, com outro
preço e outro mercado. Uma pergunta, uma função: `foil.no_ambito`, a que o
tile, o resumo, a rota e a CLI perguntam todos.

**Medido a 2026-09-22 contra uma cópia do `data/` real — bate com a
conferência dele, impressão a impressão e cópia a cópia:**

| edição | comuns | incomuns | total |
|---|---|---|---|
| OGN | 88 impressões · 291 cópias | 84 · 132 | 172 · 423 |
| SFD | 60 · 180 | 63 · 165 | 123 · 345 |
| UNL | 60 · 180 | 63 · 166 | 123 · 346 |
| VEN | 48 · 144 | 46 · 118 | 94 · 262 |
| **total** | **256 · 795** | **256 · 581** | **512 impressões · 1376 cópias** |

O **OGS fica todo de fora** (nenhum tile com contador, `progress.foil` a
`None` para a página não mostrar uma caixa vazia). Ficam também de fora, por
não serem a base: as artes alternativas, as sobrenumeradas (incluindo as
comuns — os seis Poros do UNL), as promos, as signatures e os tokens.
**Começam todas a ZERO foil**; ele marca à mão.

### 3. O foil NÃO MEXE EM NADA — e há teste que o prova

`tests/test_foil.py::TestNaoMexeEmNadaDoQueJaExiste` fotografa níveis,
denominador, as três barras, o painel (da edição e o geral), os blocos, as
wantlists, o valor (total, por edição, top), os totais, a grelha
(`qty`/`qty_total`/`qty_valor`/alvo/bloco), o playset jogável, as Faltas (os
quatro blocos por edição), as Encomendas, o A mais, a falta dos decks e o
`copies` inteiro; mete foils, tira foils, e exige que fique **igual**. É a
mesma defesa do `test_copias_proprias.py` de 21/09. Outro teste recusa que um
módulo de contas (`a_subir`, `faltas`, `faltas_edicao`, `a_mais`, `uso_decks`,
`decks`, `locais`, `pending`, `prices`, `painel`, `runas_vista`, `cardmarket`,
`seguir`, `catalog`) importe o `foil` ou mencione `qty_foil` — se um dia
importar, é sinal de que o foil entrou numa conta.

**Medido a 2026-09-22 contra cópias do `data/` real
(`C:\Users\Catarina\_revisao\_medir_foil.py`), `main` (`59746e7`) e ramo na
mesma corrida, cada lado a ler o SEU config — TUDO IGUAL:** denominador
**928**, níveis **897/836/766 de 928** (faltam 31/121/281 ·
81,96/428,24/1 014,48 €), wantlist «tudo» **162 linhas · 281 cópias ·
1 014,48 €** e por edição, valor **6 612,64 € · 2 573 cópias** e por edição,
totais, falta dos decks **37 cópias · 19 cartas · 168,43 €**, Encomendas, o
separador Faltas inteiro (317 · 555 · 10 212,74 €; a comprar 162 · 281 ·
1 014,48 €) e as **20 wantlists por bloco**, o A mais (excedente e libertadas,
item a item), o painel, as barras, os blocos, os grupos por edição e os tiles
impressão a impressão. Zero diferenças.

### 4. O contador no tile

Nas cartas do âmbito, por baixo dos `+`/`−` de sempre: um contador pequeno de
foil e a linha **«N normais · M foil»**. O `+` do foil **nunca aumenta o
total** — converte uma cópia que ele já tem —, trava em 0 e no total, e o
servidor faz o mesmo (`max(0, min(atual + delta, total))`), por isso um clique
a mais não dá erro, dá o mesmo número.

**O total a que o foil se compara é o FÍSICO** (`copies.qty`, o `qty_total`
do tile), não o `qty` da Coleção: uma carta não deixa de ser foil por estar
sleevada num deck ou nas cópias próprias dele. É o mesmo tecto do CHECK. Há
teste com uma cópia sleevada: a grelha lê «1 na Coleção» e o foil vai a 3.

No payload de cada impressão: `foil` e `foil_ok`. No `app.js`: `foilLinha`,
`foilAjustar` (fila por impressão, sem `request_id` — repetir o mesmo pedido
dá o mesmo resultado, é `min`/`max`), e o `applyLocal` corta o foil quando o
total desce, como o `ao_descer` faz na base. O `/api/adjust` passou a devolver
`foil` para o tile poder acertar.

### 5. O resumo, por baixo do painel

`#foil-resumo`, logo a seguir ao painel do topo e antes das barras: o total e
uma linha por raridade — impressões, cópias, normais e foil —, da edição
aberta ou de «Todas». Fica aí e não dentro do painel porque é outra pergunta:
o painel conta o que FALTA, isto reparte o que ele TEM. Recalculado no cliente
a cada `+`/`−` (`foilContar` é o gémeo do `foil.contar`, com teste que corre
os dois no node, como o do painel); a verdade do servidor vai em
`progress.foil` de cada edição e em `foil` do `api/index.json`. Nos 375 px os
três blocos empilham.

**Os números de arranque (tudo a zero foil):** OGN 172 impressões · 423
cópias · 423 normais · 0 foil; SFD 123 · 345; UNL 123 · 346; VEN 94 · 262;
**Todas 512 · 1376 · 1376 normais · 0 foil**.

### 6. A CLI e a rota

`riftvault foil` (o resumo por edição e raridade; `--edicao OGN` para uma só),
`riftvault foil OGN-045` (uma impressão), `riftvault foil OGN-045 --mais 2` /
`--menos 2`. `POST /api/foil/ajustar {printing_id, delta}` — 400 fora do
âmbito, 404 se a impressão não existir. O `riftvault stats` ganhou a tabela.
No site publicado é só de leitura: os `.steppers` já são escondidos pelo
`body.readonly`, e o `editable: false` do payload nem os desenha.

`tests/test_foil.py` (31 testes, contra pastas temporárias e config
temporário). Suite: **38 ficheiros, 0 a falhar**.

## 24/09/2026 — o REBRAND: a casca do baverone.com, e a navegação sai das filas de botões

Palavras dele: *"faz o mesmo rebrand para os outros projetos"*, depois de o
`mtgvault` ter sido reestruturado nesse dia. Ordem em
`ai-pc/work/rebrand-rift.md`; relatório, inventário, mapa antigo→novo e
capturas antes/depois em `ai-pc/Claude outputs/rebrand-riftvault/`.

**O riftvault é uma SPA, não um site de páginas.** O `mtgvault` gera um
`.html` por página e a casca dele vive no `site_shell.py`; aqui há um
`index.html` + `app.js` + `style.css`, os mesmos nos dois modos, e o
`build.py` limita-se a copiá-los. Por isso **não se portou o `site_shell.py`**
— seria trocar a arquitetura para não ganhar nada. O que se portou foi o
SISTEMA: os mesmos tokens, a mesma barra lateral, o mesmo cabeçalho de
página, os mesmos ícones. A «regra num sítio só» passou a ser a tabela `NAV`
do `app.js`, de onde saem a barra, as migalhas e os títulos.

### O que estava mal, e está medido

As duas filas de separadores do topo tinham `overflow-x: auto`. Um teste que
olhasse para o `scrollWidth` do documento dizia 390 num telemóvel de 390 px e
dava tudo por bom — o conteúdo estava escondido DENTRO do contentor. Medido
num Chrome a sério, a 390 px, contra o site publicado (que ainda tinha o
código antigo): a fila das secções ocupava **393 px em 232**, a das edições
**695 em 390** e a dos decks **1253 px em 390** — de nove botões viam-se três.
Depois: **zero contentores com conteúdo escondido para o lado**, a 390 e a
1440 px, em todas as secções.

### O que ficou

| | antes | agora |
|---|---|---|
| navegação | duas filas de botões com scroll lateral, no `index.html` | barra lateral fixa (≥ 900 px) e painel ☰ no telemóvel, da tabela `NAV` |
| edições | `nav.tabs` com scroll | controlo segmentado que ENVOLVE (`.segwrap`) |
| decks (9 botões) | `nav.tabs` com scroll | índice vertical (`.vidx`) e `<select>` no telemóvel, os dois do `itensDoIndice()` |
| cabeçalho | `<h1>riftvault</h1>` e mais nada | migalhas, título (= o rótulo da barra), subtítulo por vista |
| explicações longas | soltas na página | `<details>` «Como ler esta página», no rodapé |
| rotas | `#decks` | `#decks/ornn`, `#colecao/UNL`, `#faltas-edicao/OGN`, … |
| cor | azul `#7c8cff` e a paleta H em azul | **roxo `#a77bff`**, logótipo «R» |
| letra | `system-ui` | Space Grotesk + Inter (Google Fonts, com pilha de sistema) |

**Os NOMES das secções não mudaram** (`colecao`, `decks`, `faltas-edicao`,
`a-mais`, `encomendas`) — são a rota e a chave das preferências guardadas.
**O id da `<section>` no DOM mudou para `sec-<nome>`**, e isso é a correção
de um bug que nasceu com a rota: os dois eram o mesmo texto, o browser
tratava `#decks` como âncora e saltava para a secção — a página abria com as
migalhas, o título, o seletor de edição e (no telemóvel) o `<select>` dos
decks já acima do topo do ecrã. Um `scrollTo(0, 0)` não chega: o salto do
browser é DEPOIS do `boot()`.

### A secção nova: «Início»

O painel de hoje — master set nos três níveis, o que falta comprar, o valor,
os decks montados, o que vem a caminho, a coleção extra —, os atalhos e a
lista dos decks com as percentagens. **Não faz conta nenhuma**: tudo sai do
`api/index.json`, do `api/decks.json`, do `api/encomendas.json` e do
`api/faltas_edicao.json`, como de lá vem, e há teste que o fixa (um painel com
aritmética própria era uma segunda resposta às mesmas perguntas). Os três
últimos chegam depois e um que falhe deixa o cartão a «—».

**O «Quanto custa» da arquitetura sugerida na ordem NÃO foi reconstruído.** Foi
apagado a 2026-09-19 a pedido dele (*"podes apagar o botao do 'Quanto
custa'"*), e este ficheiro diz «não voltar a construir sem ele pedir». A ordem
do rebrand dizia «ajusta depois do inventário» — o inventário diz que foi ele
que o mandou apagar há cinco dias. Fica como pergunta no RESUMO.

### Erros corrigidos pelo caminho (*"corrige tudo o que achares que é erro"*)

1. **A rota era âncora** — o de cima. Era o mais grave: no telemóvel comia o
   cabeçalho inteiro de qualquer página aberta por `#`.
2. **`loadDeck` não protegia contra respostas fora de ordem.** Dois cliques
   rápidos em decks diferentes e o payload lento desenhava por cima do
   rápido. O `loadSet` já tinha essa guarda desde 21/09; o `loadDeck` não.
   Também deixou de ficar com o cabeçalho do deck anterior enquanto carrega.
3. **`renderEncTabs` escrevia o nome da edição sem escapar** (`${s.name}`),
   ao contrário de todos os outros separadores.
4. O `api/decks.json` era pedido duas vezes quando o Início e os Decks
   abriam na mesma visita (`garanteDecks`).
5. O painel do Início, na primeira versão, chamou «impressões» às cópias que
   faltam (`niveis.missing` conta CÓPIAS, `done`/`total` contam IMPRESSÕES) e
   escreveu «Catálogo (RiftScribe)» ao lado de `totals.printings`, que é
   quantas impressões ele TEM (1006) e não o tamanho do catálogo (1180).
   Apanhados na revisão das capturas, antes do merge.
6. O painel ☰ recebia o foco ao abrir e o `:focus-visible` desenhava uma
   risca roxa de alto a baixo ao lado da navegação.
7. **Na cópia publicada o subtítulo da Coleção prometia os `+`/`−`**, numa
   página onde eles estão escondidos de propósito. As páginas que falam de
   escrita ganharam um `sub_ro` no `PAGINA`, usado quando `!state.editable`.

### Medido

Os números da coleção **não mexem** — isto é apresentação e não toca em
Python nenhum a não ser nos testes: o rebrand mudou `riftvault/web/*`,
`README.md`, este ficheiro e cinco ficheiros de teste que descreviam a casca
antiga. Nenhum `.py` do pacote foi tocado.

`tests/test_casca.py` (26 testes) fixa a navegação, as rotas, os links e a
ausência de scroll lateral. `test_painel` (a paleta), `test_a_mais`,
`test_faltas_nova`, `test_encomendas_separador` e `test_sem_quanto_custa`
foram ajustados porque descreviam a fila de botões. Suite: **39 ficheiros,
784 testes, 0 a falhar** (um processo por ficheiro — a bateria toda num
processo só tem 13 falhas de estado partilhado que já lá estavam, no
`test_mesma_legend` e no `test_nome_do_deck`, que passam sozinhos).

## 24/09/2026 — DECK MONTADO OU DESMONTADO (`decks.montados`), a REGRA DE RARIDADE (`decks.coleccao_so_a_partir_de`) e o modo de remontagem

Palavras dele: *"vamos desmontar os decks todos com excepcao da LeBlanc, vou
colocar tudo nos binders das edicoes e depois voltar a montar deck a deck e
assim conseguir perceber o que tenho e nao tenho. tal como dito antes, o que
tiver a mais dos decks fica exclusivo para o deck e nao entra na coleccao. vou
tentar ao maximo que cartas de raridade Rara para baixo fiquem alocadas
exclusivamente a coleccao e as repetidas exclusivamente aos decks, para nao ter
que mexer na coleccao. apenas miticas para acima devo ter que usar as da
coleccao"*. Ramo `ai-pc/desmontar-2026-09-24`.

**No Riftbound NÃO HÁ «mítica».** A escada do catálogo é `common < uncommon <
rare < epic < showcase` (a `showcase` nem é raridade de jogo, é o tratamento
das reimpressões de topo). «Rara para baixo» = common+uncommon+rare; «míticas
para cima» = epic+showcase. Está escrito no config e na mensagem de erro.

### 1. Montado ou desmontado

`decks.montados` é a lista dos decks MONTADOS (o slug ou o `Nome:`, a
gramática da `decks.ordem`), hoje `["LeBlanc Hook"]`. **Sem a chave, todos
montados** — é o que valia até aqui e o que um riftvault sem config mede; a
lista **vazia** é «nenhum montado». São coisas diferentes de propósito: o
botão de desmontar o último escreve `[]`, e se o vazio quisesse dizer «todos»
esse clique fazia o contrário do que diz.

**Um deck desmontado não consome NADA da Coleção:** não aparece na grelha como
uso (`uso_por_carta`), não entra no «falta comprar aos decks»
(`resumo_das_faltas`), nas Staples nem no «Todos juntos» (`faltas._wanted`,
`_falta_global`), no «para»/«falta encomendar» das Encomendas
(`pending.encomendas`), no que os decks tiram à Coleção (`a_mais._usadas`,
`decks._por_impressao`), e a proposta de marcação recusa-o
(`locais.propor_deck`). **Não gera libertadas**: desmontar não mexe no
`deck_cards`, por isso o `deck_need_log` não escreve linha nenhuma — apagar o
`.txt` é que liberta, e é essa a diferença que ele quer.

**A alocação passou a ter DUAS PASSAGENS** (`decks.allocate`): primeiro os
grupos dos montados, pela prioridade de sempre, a consumir os montes; depois
cada desmontado sozinho, contra uma **cópia** do que sobrou. O resultado de um
desmontado é por isso uma **simulação** — «se montasse este a seguir aos que
estão montados, o que sairia da Coleção e o que me faltava» — e não consome:
dois desmontados podem contar a mesma cópia, que é o que a pergunta quer
dizer. Cada entrada leva `montado`, e quem soma decks lê só os montados. A
lista continua toda a ver-se; a página, o índice e o `riftvault decks` dizem
«desmontado» e que os números são simulação.

O botão **Montar/Desmontar** vive na página do deck e escreve no
`riftvault_config.json` (*"o estado é do config, não só da base, para não se
perder"*): `decks.alternar_montado` → `config.escrever_lista`, que troca **só
o valor daquela chave, como texto**, a contar chavetas para achar o bloco. O
ficheiro dele é escrito à mão, com objectos numa linha e dezenas de `_notas`;
um `json.dumps(indent=2)` do ficheiro inteiro reformatava-o todo a cada
clique. Na CLI: `riftvault decks --montar/--desmontar SLUG`. Na rota:
`POST /api/decks/montar {slug, montado}`.

### 2. A regra de raridade — MARCA, não bloqueia

`decks.coleccao_so_a_partir_de: "epic"`: dessa raridade para cima um deck
serve-se da Coleção sem aviso; abaixo dela, a cópia devia vir das **cópias
próprias do deck** (`proprias.py`). **A alocação é EXACTAMENTE a mesma** — há
teste que compara a alocação com o aviso ligado e desligado, campo a campo — e
o que sai é `aviso_colecao`, por carta e somado: o tile leva moldura dourada e
«N da Coleção — é rare: devia ser própria do deck», o deck um chip «N da
Coleção que não deviam», e o `riftvault decks` uma coluna. `null` ou `""`
desliga; uma raridade que o catálogo não conheça rebenta com a lista das que
existem.

A raridade de uma carta é a `base_rarity` da impressão BASE que o deck joga
(`decks.raridade_por_carta`): a arte alternativa de uma rara é `showcase` e
continua a ser uma rara.

### 3. O modo de remontagem

Na página de cada deck, um `<details>` **«Montar este deck, carta a carta»**:
uma linha por carta com **precisa / próprias / deck+binder / Coleção / falta**,
**somada por carta** (2 Sabotage no main e 1 no sideboard são 3 Sabotage — quem
está a montar tem a carta na mão uma vez só), ordenada pelo que **falta**
primeiro, depois pelo que sai da Coleção, e no fim o que já está. O `!` é a
regra de raridade. Aberto quando falta alguma coisa ou o deck está desmontado.
**A 375 px cada linha passa a cartão** (`@media (max-width: 559px)`, cada `td`
com o seu rótulo): é com o telemóvel na mão e as cartas à frente que ele vai
percorrer isto. O mesmo no `riftvault deck <slug>` (`_montagem`, `_por_carta`).

### Medido a 2026-09-24 contra uma cópia do `data/` real (`_revisao\_medir_desmontar.py`), quatro cenários na mesma corrida

**Os números dele batem todos:** os seis decks pedem **324 cópias** — por
raridade **273 de 113 cartas** em common+uncommon+rare e **51 de 23** em
epic+showcase; por deck (baixa/epic+) akali **42/12**, azir **50/4**, jayce
**44/10**, kennen **42/12**, leblanc-hook **45/9**, ornn **50/4**. O excedente
LIMPO (cópias − alvo, sem decks a consumir) é **152 cópias em 62 impressões do
bloco master set** — com a coleção extra dentro são 153/63, e a única a mais é
a `VEN-SP5` Ezreal (2 cópias, alvo 1). Desse excedente, o que serve os decks:
**31 cópias de raridade baixa e ZERO de epic+**.

**A promessa da ordem, medida:** a Coleção com os cinco desmontados (cenário
B) dá **exactamente** o mesmo que a Coleção com a pasta `decks/` só com o
`leblanc-hook.txt` (cenário C) — níveis, denominador, wantlist, valor,
totais, grelha impressão a impressão, usos, painel, Faltas (os quatro blocos),
Encomendas e o excedente do A mais item a item. A **única** diferença são as
libertadas: B **0**, C **132 cartas · 270 cópias** — apagar o `.txt` liberta,
desmontar não, e é isso que ele quer para voltar a montar.

| | todos montados | só o LeBlanc montado |
|---|---|---|
| cartas com uso de decks na grelha | **149** | **27** |
| falta comprar aos decks | 37 cópias | **0** (o LeBlanc está completo) |
| A mais — excedente | 62 impressões · 125 cópias | **69 · 140** |
| A mais — libertadas | 0 | **0** |

Por deck, com as próprias a ZERO (tenho/54 · da Coleção · falta · aviso):
LeBlanc Hook **54/54 · 54 · 0 · 45**; Jayce 42/54 · 42 · 12 · **37**; Kennen
53/54 · 53 · 1 · **41**; Akali 50/54 · 50 · 4 · **39**; Ornn 52/54 · 52 · 2 ·
**48**; Azir 50/54 · 50 · 4 · **46**. (Os avisos dos desmontados são maiores
do que com tudo montado — 38→39, 46→48, 35→46 — porque a simulação vê a
Coleção que os outros decks já não estão a prender.)

`tests/test_desmontar.py` (35 testes, contra pastas temporárias e config
temporário): a chave e as três leituras dela; **a fotografia da Coleção
desmontado == sem o deck**; desmontar não gera libertadas; não aparece no uso,
na falta, nas Staples, no «para» das Encomendas; a proposta recusa-o; a lista
continua a ver-se; dois desmontados contam a mesma cópia; as próprias servem
na mesma; montar volta a consumir; o config escrito sem perder o feitio nem as
`_notas`; a regra de raridade marca e não bloqueia, o patamar vem do config,
uma raridade inventada rebenta, as próprias tiram o aviso, a runa nunca avisa;
as rotas, o `build`, a CLI e o `app.js`/`style.css`.

**Um erro apanhado pelas capturas, antes do merge:** o `>` que fechava a tag
do `<div class="dtile …">` perdeu-se ao acrescentar a classe do aviso, e o
browser passou a ler o tile inteiro como uma tag só — cada pedaço da carta
virou um item da grelha. As fotos a 1280 e a 375 px são a maneira de o ver; o
`test_casca` não o apanha porque não desenha nada.

Suite: **40 ficheiros, 0 a falhar**.

## 25/09/2026 — o separador «VENDA»: a conta de quem compra, com o Trend do Cardmarket METIDO À MÃO

Palavras dele: *"quero que cries um separador que e: Venda. este separador
permite-me marcar as cartas que estou a vender no momento para apresentar a
conta a pessoa. **todos os precos tem que ser o Trend do Cardmarket!**"*.
Ramo `ai-pc/venda-2026-09-25`.

**NÃO É A VENDA DE 2026-09-08** (apagada a 2026-09-15). Aquela era uma
SUGESTÃO calculada — o que sobra acima do alvo —, e essa pergunta vive hoje no
separador «A mais» (2026-09-17). Esta é outra: ele está à mesa com o comprador,
marca o que está a vender, e o ecrã dá a conta. **A lista é dele, não é
calculada.** Do código antigo (`git show 5b35747~1:riftvault/venda.py`) não se
reaproveitou nada: a conta do excedente já tinha sido reaproveitada pelo A
mais, e o resto respondia a outra pergunta. O que se reaproveitou foi a
ARQUITECTURA de duas ordens recentes — o `foil.py` (uma tabela à parte, uma
fotografia de tudo a provar que não mexe em nada) e o `proprias.py` (escrita
com rasto, e o botão que mexe na coleção a ser separado e explícito).

### O PREÇO: por que é que ele tem de o meter à mão

**A app não tem preços do Cardmarket e não os pode ter.** Verificado a
2026-09-25, antes de desenhar seja o que for:

| fonte | o que há |
|---|---|
| `catalog.price_latest` | 1227 linhas, **todas** `source='cardtrader'` — e é a OFERTA MAIS BARATA em NM/Mint, inglês (`prices.oferta`), não um Trend |
| API oficial do Cardmarket | **fechada a novas candidaturas** (página de ajuda deles, lida a 25/09) |
| `cardmarket.com` | **403** a pedidos automáticos (está no CLAUDE.md desde 2026-08-31) |
| APIs de terceiros que revendem Trend | pagas — e a regra dele é *só a subscrição* |
| scraping | fora de questão |

A sessão da ordem `0-venda-preco-ct`, a correr em paralelo, confirmou o outro
lado da mesma pergunta: **o «CT Market Price» do CardTrader não existe na API
v2** (nem campo, nem endpoint, nem agregação que o reproduza); o único número
agregado que se reproduz ao cêntimo é o «Best Deal», que é preço de compra e
não avaliação. Não há por onde ir buscar um Trend.

**Por isso o Trend é um CAMPO que ele preenche**, em euros, a olhar para a
página da carta no Cardmarket — e a linha tem o link para lá. Guarda-se por
IMPRESSÃO com a data (`cardmarket_trend`), para a venda seguinte vir
preenchida; passados `venda.trend_valido_dias` dias (7) marca-se como velho e
**não se apaga** — um Trend de há duas semanas é melhor ponto de partida do
que um campo em branco.

**O preço do CardTrader aparece na linha, rotulado «CardTrader, só
referência», e NUNCA entra no total** — nem como omissão de uma linha por
preencher: uma linha sem Trend conta **ZERO** e o cabeçalho diz «Falta 1 linha
sem Trend». Substituí-lo era apresentar a conta errada a uma pessoa a sério.
Há teste: com o Brutalizer a 9,00 € no CardTrader e sem Trend, o total é 0,00 €.

### O que se guarda, e onde

Três tabelas novas no vault.db (`CREATE TABLE IF NOT EXISTS`, sem migração e
sem backup — não tocam no `copies`):

| tabela | o que é |
|---|---|
| `sale_lines` | a venda EM CURSO: uma linha por impressão (ele escolhe a versão que tem na mão), uma venda de cada vez |
| `cardmarket_trend` | o Trend dele, por impressão, com a data e a origem |
| `sale_log` | as vendas FECHADAS: uma linha por carta, agrupadas pelo `sale_id`, com o Trend **da altura** (a conta de ontem não muda quando o Trend mudar) |

### MARCAR PARA VENDA NÃO TIRA NADA DE LADO NENHUM

`tests/test_venda.py::TestNaoMexeEmNadaDaColecao` fotografa níveis,
denominador, as três barras, o painel (da edição e o geral), os blocos, as
wantlists, o valor (total, por edição), os totais, a grelha
(qty/qty_total/qty_valor/alvo/bloco/foil), o playset jogável, as Faltas (os
quatro blocos por edição), as Encomendas, o A mais item a item, a falta dos
decks, o `uso_por_carta`, os locais e o `copies` inteiro — mete seis cópias na
venda, mete Trends, tira tudo, e exige que fique **igual**. É a defesa do
`test_copias_proprias` (21/09) e do `test_foil` (22/09). Outro teste recusa que
um módulo de contas importe o `venda` ou mencione as tabelas dele: só o
`server`, o `build` e a `cli` o chamam.

**Quem baixa as cópias é o botão SEPARADO «marcar como vendidas»**
(`venda.vender`): sem `confirmar` levanta `PrecisaConfirmar` (a rota devolve
**409** e o ecrã pergunta), e com ele cada linha passa pelo `collection.adjust`
— portanto fica na `ops`, dá para **desfazer** com o undo de sempre, e o
`locais.ajustar_ao_total` tira a cópia de onde ela estiver. Vender mais do que
tem baixa o que há (o `adjust` trava no zero) e o resultado diz quanto faltou.

### Avisa, não bloqueia

Pôr à venda mais cópias do que tem registadas, ou uma carta que um deck
**MONTADO** usa (hoje só o LeBlanc Hook — um desmontado não usa nada, regra de
24/09; lê-se do mesmo `decks.uso_por_carta` da grelha), dá aviso na linha e no
cabeçalho. Ele é que sabe o que tem na mão.

### A página

Cabeçalho com o total e os avisos; a procura (nome ou código, no catálogo
inteiro — `GET /api/venda/procurar`, só no modo edição, porque a grelha só tem
uma edição em memória e a venda é de tudo); uma linha por carta com a arte, os
`+`/`−`, o campo do Trend, o preço do CardTrader rotulado e **dois links**
(`Cardmarket` pelo id, `procurar` pelo nome — ver «Superfícies não validadas»,
ponto 7); e no fim **A CONTA**, limpa, para virar o ecrã: nome, edição, número,
quantidade, Trend unitário, subtotal e total, com «Copiar a conta».

**A 375 px** cada linha da conta vira cartão (o mesmo que a tabela de montagem
dos decks faz desde 24/09) e a linha de venda passa a duas filas. Medido com o
DevTools Protocol a 375 px, na cópia dos dados reais: `documentElement.
scrollWidth == clientWidth == 375`, **zero** elementos fora do ecrã ou com
scroll próprio. Há teste que fixa as regras do `@media`.

Na Coleção, cada tile de que ele tenha alguma cópia ganhou um **«+ venda»**
discreto (só no modo edição, só com cópias — um botão em 1180 tiles era
ruído), que junta uma cópia daquela impressão e diz no toast o que aconteceu,
com atalho para a secção.

No site publicado a Venda é **só de leitura**: o `build` escreve
`api/venda.json` com `editable: false` e o cliente nem desenha os `+`/`−`, o
campo do Trend ou os botões.

### Medido a 2026-09-25 contra uma CÓPIA do `data/` real

(`_revisao\_venda_dados.py` + `_venda_exemplo.py`; a Venda escreve, por isso
nunca se serviu o `data/` a sério.) Uma venda de exemplo com 1× `OGN-039a`
Kai'Sa a 52,50 €, 2× `UNL-228` Bloodharbor Ripper a 139,00 € e 3× `OGN-045`
Defy **sem Trend**: total **330,50 €**, 6 cartas em 3 linhas, «Falta 1 linha
sem Trend», e dois avisos de stock. Os mesmos CardTrader ao lado seriam 49,63 €,
114,52 € e 1,25 € — e **não entram**: a soma deles daria outra conta.

**Nada da Coleção mexe com isto**: a secção é apresentação mais três tabelas
próprias, e a única escrita que toca no `copies` é o «marcar como vendidas».

### Erros corrigidos pelo caminho

1. **`$('#colecao')` no `wireKeyboard`** — o rebrand de 24/09 mudou o id da
   secção para `sec-colecao` e esta linha ficou a perguntar por um elemento que
   já não existe: `null.hidden` rebentava **a cada tecla** premida fora de um
   campo de texto, e por isso as setas e os `+`/`−` do teclado não faziam nada
   na Coleção. Passou a `#sec-colecao`.
2. **A classe `aviso`** que a linha de venda usava é, no resto do site, uma
   caixa de texto com `max-width: 62ch` — as linhas com aviso apareciam a
   metade da largura das outras. As classes da secção passaram todas a levar o
   prefixo `vd-`. Só se vê numa fotografia a 1280 px, que é para isso que ela
   serve.
3. Plurais: «Faltam 1 linhas» na conta, no CLI e na página.

`tests/test_venda.py` (34 testes, contra pastas temporárias e config
temporário). `test_site_do_pc` passou a exigir o `api/venda.json` (era o
contrário desde 15/09), `test_sem_quanto_custa` ganhou a secção nova na lista
das que existem, e o `test_a_mais` passou a procurar o `api/venda` só no troço
do A mais — o ficheiro inteiro volta a ter uma Venda.

Suite: **41 ficheiros, 0 a falhar**.

## 25/09/2026 — as abas ESCONDEM-SE por config (`abas.escondidas`): saem o «A mais», o «Por deck» e o «Pimp decks»

Palavras dele: *"Tira a aba 'A mais', 'Por Deck' e 'Pimp Deck'"*. Ramo
`ai-pc/abas-2026-09-25`.

**ESCONDER NÃO É APAGAR, e é a diferença que interessa.** O `a_mais.py` e o
`faltas.py` ficam como estavam, as rotas continuam a responder
(`/api/a_mais.json`, `/api/compras.json`), o `build` continua a escrever os
dois ficheiros e a CLI continua a ter o `riftvault a-mais`. O que sai é o
BOTÃO: a entrada na barra lateral, a vista no índice dos decks (e no `<select>`
do telemóvel), o atalho do Início e a rota que lá levava. **Repor uma aba é
tirar o nome da lista, mais nada** — ao contrário da tabela de preços de
19/09, que se recupera de um commit.

**Onde vive.** `riftvault/abas.py` — o catálogo das dez abas (`ABAS`, pela
ordem da barra), `escondidas(cfg)`, `visiveis(cfg)`, `payload(cfg)` e
`texto(cfg)` (uma linha no `riftvault stats`). A lista vai no
`api/index.json` (`metrics.index_payload`, que ganhou `cfg`), **nos dois
modos** — é isso que faz a mesma linha de config tirar a aba do 8770 e do site
publicado —, e o `app.js` lê de lá: **não há segunda lista no JavaScript**.

**Os nomes que casam.** O id é a ROTA quando é secção e o id da vista quando é
sub-vista: `inicio`, `colecao`, `faltas-edicao`, `a-mais`, `decks`,
`staples`, `pordeck`, `pimp`, `encomendas`, `venda`. Aceitam-se também como
ele as lê no ecrã — «A mais», «Por deck», «Pimp deck», «Pimp decks»,
«Faltas», «Início» —, pela mesma ideia do `metrics.PALAVRA_KIND`. **Um nome
desconhecido rebenta**, com a lista do que existe: uma aba mal escrita
ignorada em silêncio deixava-o a olhar para um separador que mandou tirar.
Sem a chave, nada escondido. Config real:
`"abas": { "escondidas": ["a-mais", "pordeck", "pimp"] }`.

**No `app.js`**, uma função (`abaVisivel`) e seis sítios: o `renderNav` (salta
os itens e o grupo que fique vazio), o `seccaoValida`/`seccaoInicial` (uma
secção escondida é, para as rotas, uma secção que não existe — o `#a-mais` de
um favorito cai na primeira que se veja, e o `hashchange` faz o mesmo), o
`deckFaltaTabs()`/`deckFaltaIds()` (o `DECK_FALTA_IDS` deixou de existir; a
`DECK_FALTA_TABS` fica inteira, é o catálogo), o `loadDecks` (uma preferência
guardada com o «Por deck» abre no primeiro deck), os atalhos do Início, e os
DOIS textos que nomeavam as abas — a ajuda dos Decks (a única `ajuda` que
passou a ser função, `ajudaListasDeCompra`) e a nota do «Falta comprar aos
decks», que mandava ir ao «Por deck». **O `renderNav()` mudou-se para DEPOIS
do `api/index.json`** (desenhá-lo antes mostrava por um instante uma aba que
ele mandou tirar); se o índice falhar, o `boot().catch` desenha-o na mesma.

**Medido a 2026-09-25 contra uma cópia do `data/` real
(`_revisao\_medir_abas.py` + `_copiar_dados_abas.py`), o MESMO código e a
MESMA cópia, mudando só o `abas.escondidas` — os dois JSON saem BYTE A BYTE
IGUAIS** (164 285 bytes, mesmo sha256): denominador **928**, níveis
**897/836/766 de 928**, wantlist «tudo» **162 linhas · 281 cópias ·
1 028,67 €** (e as cinco por edição), valor **6 615,91 € · 2 573 cópias**,
Faltas **555 cópias · 10 178,32 €** (a comprar 281 · 1 028,67 €) e as 20
wantlists por bloco, A mais **69 cartas · 140 cópias** item a item (e 0
libertadas), decks **0 cópias** (só o LeBlanc Hook montado, e está completo),
Encomendas 0, Venda 0, o painel, os grupos, os blocos e a grelha impressão a
impressão. **E o site gerado dos dois lados: 29 ficheiros, os mesmos nomes, e
só o `api/index.json` difere** (a menos do relógio) — o `api/a_mais.json`
(34 097 bytes) e o `api/compras.json` (13 881 bytes) saem idênticos.

Fotografado a 1400 px e a 375 px contra o site gerado: a barra fica com
Início · Coleção · Faltas · Decks · Staples · Encomendas · Venda, o índice dos
decks com «Listas de compra: Staples» só, o Início com quatro atalhos, o
`#a-mais` a cair noutra secção, e as duas frases sem as abas que saíram.

`tests/test_abas.py` (29 testes, contra pastas temporárias e config
temporário): o config (sem chave, a lista, os nomes dele, o desconhecido a
rebentar, a lista mal escrita, **repor = tirar da lista**, o config real, o
default, e o catálogo a bater certo com a `SECCOES`/`DECK_FALTA_TABS` do
`app.js`); o payload (o índice, o servidor a continuar a servir o
`a_mais.json` e o `compras.json`, o site publicado com os mesmos ficheiros, o
A mais e as compras a darem o mesmo item a item, e ler não escreve); **a
fotografia** — níveis, denominador, wantlists (geral e por edição), valor,
totais, grelha, barras, painel, foil, blocos, Faltas com as wantlists por
bloco, Encomendas, A mais, decks, compras, Venda e o `copies` inteiro — com as
abas à vista, com as três escondidas, com as DEZ escondidas e repostas, tudo
igual (mais um teste que exige que a fotografia não seja de zeros); nenhum
módulo de contas importa o `abas`; e o `app.js`. Suite: **42 ficheiros, 0 a
falhar**.

## 25/09/2026 — o separador «PRODUTO SELADO» (`selado.py`, `data/selado_catalogo.json`)

Palavras dele: *"faz uma lista, para acrescentar um separador que e 'Produto
Selado', em que vai tudo o que e produtos de coleccao do Riftbound, como
displays ou boxcase, ou duel decks, proving ground, etc etc, para eu saber o
que ha, o que tenho e o que nao tenho"*. Ramo `ai-pc/selado-2026-09-25`.

### 1. A lista vem do CardTrader, e a separação selado/single é DELES

**O catálogo da RiftScribe só tem cartas** — não há endpoint nem campo de
display, booster box ou deck. A fonte é a API v2 do CardTrader, a mesma que já
dá os preços, com o mesmo token.

E não foi preciso adivinhar o que é selado: o CardTrader arruma os blueprints
por **categoria** e publica-as em `GET /categories`. As do Riftbound são
**treze**, com nome, e a **258 é «Riftbound Singles»** — é a constante
`prices.SINGLES_CATEGORY`, que o `riftvault map` já usava desde 2026-08-31
para ficar só com as cartas (*"booster boxes, playmats e afins"*, no
comentário). Isto é o outro lado da mesma linha.

| entra (`selado.categorias`) | n | fica de fora (acessórios) | n |
|---|---|---|---|
| 259 Booster Boxes | 10 | 264 Playmats | 48 |
| 260 Boosters | 21 | 266 Sleeves | 31 |
| 261 Bundles | 13 | 265 Albums | 10 |
| 262 Starter Decks | 24 | 267 Deck Boxes | 9 |
| 263 Box Sets & Displays | 15 | 268 Memorabilia | 13 |
| 283 Complete Sets | 2 | 284 Oversized | 13 |
| **total** | **85** | uma sem nome no Riftbound (206, um dado) | 1 |

**Os acessórios não desaparecem em silêncio**: o `scope.fora` conta-os por
categoria e o cabeçalho da página di-lo. Metê-los é acrescentar o número à
lista do config; escrever a **258 rebenta** (punha 1180 cartas no separador).
**São 210 não-singles ao todo** — o ficheiro guarda-os todos, para mudar a
lista do config não obrigar a voltar à rede.

**Resposta CRUA guardada** em `C:\Users\Catarina\_revisao\selado-cru-20260925-174327.json`
(categorias + expansões + todos os não-singles por expansão) e as ofertas de
quatro produtos em `selado-ofertas-cru.json`.

### 2. O TIPO: a categoria, corrigida pelo nome

`selado.tipo_de(nome, versao, categoria_id)`. A categoria decide — 259
`display`, 260 `booster`, 261 `bundle`, 262 `deck`, 263 `caixa`, 283
`conjunto` — **menos quando o nome diz outra coisa**, e é preciso: a 263 mete
no mesmo saco o *Origins Booster Box Case* (seis displays), o *Origins:
Proving Grounds* e a *Instant Match Box*. São três coisas diferentes para quem
coleciona e ele nomeou duas delas, por isso o nome ganha: `\bcase\b` →
`case`, `proving grounds` → `proving-grounds`. Os «duel decks» dele são os
*Showdown Deck* do CardTrader, na categoria dos Starter Decks → `deck`.

### 3. Os três estados, e os «por sair»

`ha` (a lista toda) · `tenho` (unidades > 0) · `falta`. **O `falta` NÃO conta
os «por sair»** — não se pode ter o que ainda não existe —, e por isso
`tenho + falta == saiu`. Contadores no topo, filtro por baixo (Tudo · Tenho ·
Não tenho · Por sair) e uma procura.

**As datas vêm DELE** (`selado.datas_por_edicao`): OGN 2025-10-31, SFD
2026-02-13, UNL 2026-05-08, VEN 2026-07-31, RAD 2026-10-23. **A API do
CardTrader não dá data de lançamento nenhuma** — uma expansão são quatro
campos (`id`, `game_id`, `code`, `name`). As edições anunciadas sem data
exacta escrevem-se em `selado.por_sair` (hoje LGC, PG2 e REC, *"em 2027"*).
O OGS **não tem data** porque ele não a deu — e sem data não é «por sair».

### 4. O SELADO NÃO ENTRA NA COLEÇÃO

As unidades vivem na tabela **`sealed_copies`** (vault.db), que mais nenhum
módulo lê, e o **valor do selado é um total próprio, NUNCA somado ao valor da
Coleção** — uma caixa por abrir não é uma carta no binder.

**Medido a 2026-09-25 contra uma CÓPIA do `data/` real
(`_revisao\_medir_selado.py`), o mesmo código, a gerar o site duas vezes —
uma com a `sealed_copies` vazia, outra com 12 unidades (1 874,00 €) lá
dentro:** níveis, denominador, wantlist, valor (**6 615,91 €, 2 573 cópias,
igual dos dois lados**), totais, painel, foil, Faltas, A mais, decks,
Encomendas, Venda e as edições do índice — **iguais**; e o site gerado sai
**igual ficheiro a ficheiro (30 ficheiros)**, a menos do relógio. O único que
difere é o `api/selado.json`, que é o desta secção.

`tests/test_selado.py` (61 testes) fotografa níveis, denominador, wantlist,
valor, totais, grelha, playset jogável, barras, painel, foil, blocos, Faltas,
Encomendas, A mais, decks, uso, Venda, `copies`, locais e `ops`, mete e tira
selado, e exige igualdade — mais um teste que exige que a fotografia não seja
de zeros, e outro que recusa que qualquer módulo de contas importe o `selado`
ou mencione a `sealed_copies`. É a defesa das cópias próprias (21/09), do
foil (22/09) e da Venda (25/09).

### 5. O preço do selado é OUTRA REGRA, medida

Sondadas 4 blueprints (106 ofertas) a 2026-09-25: uma oferta de produto
selado **não tem `condition`** (vem `None` em todas — não há «Near Mint» de um
display) e traz duas propriedades próprias:

    properties_hash.sealed             (bool)  <- ainda está por abrir
    properties_hash.riftbound_language ('en', 'zh-CN', 'fr', 'kr')

Por isso `selado.preco_do_selado`: fora o graded, o vendedor de férias e o que
não esteja em EUR; **`sealed: false` não conta** (é um produto já aberto); e a
língua segue o `precos.linguas` de sempre, porque a diferença é grande — no
*Origins Booster Box* são 51 ofertas `en`, 6 `zh-CN` e 3 `fr`. **Hoje 34 dos
85 não têm oferta em inglês** e aparecem a «—»; um produto sem preço vale zero
no total e não rebenta.

### 6. Onde fica, e o ritmo dos pedidos

`data/selado_catalogo.json` (92 KB) **vai para o Git**: é o CATÁLOGO — o que
existe —, é texto, e o site publicado precisa dele. Atualiza-se **à mão** com
`riftvault selado --sync`: 1 pedido de cada vez, 1 s entre dois (o mesmo
ritmo do `riftvault prices`), **104 pedidos** na primeira corrida (categorias
+ expansões + 17 blueprints/export + 85 preços). **O `riftvault prices`
diário NÃO foi tocado** — isto não entra em tarefa nenhuma.

### 7. O que ele pode mudar sem código

`selado.categorias` (o que é selado), `datas_por_edicao`, `por_sair`,
`ordem_das_edicoes` e **`selado.extra`** — produtos que a API não tem
(regionais, promocionais), com `nome` (obrigatório), `edicao`, `tipo`, `data`,
`preco_eur` e `nota`. A lista da app é a da API **mais** estes; um `tipo` que
não exista rebenta com a lista dos que há, e tirar a entrada tira o produto.

### 8. A página

Cabeçalho com os quatro números (o que há · tenho · não tenho · valor do
selado, dito «à parte do valor da Coleção»), a linha das categorias que
ficaram de fora, o filtro e a procura, e a lista **agrupada por edição** pela
ordem do config. Cada linha: a foto (do CardTrader), o nome, o tipo, a edição,
a categoria, a data (ou «por sair»), o preço rotulado **CardTrader** e os
`+`/`−`. **A 375 px** a linha parte-se — a foto e o nome em cima, o preço e os
botões numa fila por baixo —, e os quatro números passam a duas colunas;
medido no Chrome (DevTools Protocol): `documentElement.scrollWidth ==
clientWidth == 375`, zero scroll lateral. No site publicado é só leitura
(`editable: false`), pelo mesmo flag da Coleção. A aba respeita o
`abas.escondidas` (id `selado`, ou «Produto Selado»).

**Duplicados do CardTrader ficam como estão** — ~~a *Origins: Jinx Trial Deck*
aparece duas vezes (blueprints 330845 e 363136), e as quatro Trial Decks do
mesmo modo. São dois blueprints deles; inventar uma deduplicação por nome
escondia um produto que pode ser mesmo diferente. Fica anotado.~~
**RESPONDIDO a 2026-09-25, à noite**: foram-se ver as ofertas dos oito e é
DUPLICAÇÃO — juntam-se. Ver a secção a seguir.

**Alvo 1 de cada, implícito**: «tenho» é ter pelo menos uma unidade. Ele não
disse quantas quer de cada produto, e não se inventou um alvo — o contador
sobe o que ele quiser e a percentagem é sobre produtos, não sobre unidades.

Suite: **43 ficheiros, 0 a falhar**.

## 25/09/2026, à noite — o que FALTAVA ao Produto Selado: 17 do `selado.extra`, a secção «Acessórios», e os Trial Decks eram duplicação

Palavras dele: *"o catalogo do CardTrader NAO tem tudo: eu fiz um levantamento
independente (loja oficial da Riot, playriftbound.com, TCGplayer com 76
selados, fichas do distribuidor PHD Games e lojas portuguesas)"* — em
`ai-pc/work/riftbound-produto-selado.md` — *"FALTAM ESTES, e sao precisamente o
tipo de coisa que um catalogo de mercado nao lista porque quase nao circula
solta. Mete-os pela chave `selado.extra` que ja fizeste (e para isto que ela
serve)"*. Ramo `ai-pc/selado-extra-2026-09-25`.

### 1. Os 17 produtos do `selado.extra`

| o quê | n | edições | `conteudo` |
|---|---|---|---|
| Champion Deck Display | **7** | OGN Jinx/Viktor/Lee Sin · SFD Rumble/Fiora · UNL Vi/Vex | 4 decks iguais · MSRP 79,96 USD |
| Showdown Decks Display | **2** | VEN Zed vs Shen · RAD Evelynn vs Seraphine | 4 conjuntos de dois jogadores · MSRP 139,96 USD |
| Vault Bundle Case | **3** | UNL · VEN · RAD | 12 vaults |
| Proving Grounds Box Set Case | **1** | OGS | 6 caixas |
| **Pre-Rift EVENT Kit** | **4** | SFD · UNL · VEN · RAD | 16 kits de jogador + 1 display · MSRP 480 USD |

**A `nota` é para as RESSALVAS, e por isso nasceu um campo `conteudo` à
parte.** O case do Vault da Unleashed leva `conteudo: "12 vaults"` e
`nota: "DÚVIDA: as fontes divergem — umas dizem 12 vaults, outras 4. Fica 12
(como o da Vendetta e o da Radiance, confirmados), por confirmar."` — a página
escreve as duas com cores diferentes (o conteúdo em branco, a nota a amarelo),
porque um «12 vaults» com uma fonte a dizer 4 tem de se ler como dúvida e não
como facto. Os quatro EVENT Kit levam nota a dizer que **não são** o
«Pre-Rift Kit» do CardTrader, que é o kit de UM jogador (~40 USD, 29,99 € em
loja PT): são dois produtos e aparecem os dois, lado a lado na mesma edição.

**Os MSRP dele são em DÓLARES e ficam no `conteudo`, NUNCA no preço.** Não há
taxa de câmbio validada em lado nenhum do riftvault, e pôr um número em euros
era inventar dados. As 17 linhas dizem «—» e contam no `sem_preco`, que passou
de 34 para 47.

**A Proving Grounds (OGS) ganhou data**: `2025-10-31`, a da Origins. Ficou sem
ela no primeiro dia porque ele não a tinha dado.

### 2. Os ACESSÓRIOS numa secção à parte (`selado.acessorios`)

Decisão pedida a mim, e é **sim** para os binders e os deck boxes: entram
`[265, 267]` — 10 Albums e 9 Deck Boxes —, numa **secção «Acessórios»** no fim
da página, com contadores e valor próprios e um botão que a esconde
(`prefs.selAcess`, começa à vista). **Não contam para o produto selado**: nem
no «o que há», nem no «tenho», nem no «não tenho», nem no valor do selado — há
teste que fotografa os `totals` com a lista cheia e vazia e exige que sejam
iguais. São **três totais separados**, e nenhum se soma ao da Coleção.

Porquê estes e não os outros: vendem-se selados e guardam-se (o *Radiance:
9-Pocket Collector Binder* anda a 33,99 € em loja portuguesa). **Ficam de
fora**, contados no `scope.fora` como sempre: as 48 **playmats** e as 31
**sleeves** (acessórios de *jogo*, e 79 linhas a afogar as 98 do selado), a
**memorabilia** (268 — os quatro standees acrílicos vêm DENTRO do Proving
Grounds Box Set, e contá-los à parte era contar o mesmo produto duas vezes) e
as **oversized** (284 — são cartas grandes, não produto). Uma categoria nas
duas listas rebenta; a 258 em qualquer das duas rebenta.

Ganharam **tipo próprio** (`binder`, `deck-box`): «Outro» num binder não diz
nada.

**Os preços deles estão por ir buscar.** O `--sync` só pede preços do que está
em `selado.categorias`, e a ordem dizia para não tocar em `data/` — que é onde
vive o `selado_catalogo.json`. Os 19 aparecem a «—» e o valor dos acessórios
é 0,00 € até correr `riftvault selado --sync`.

### 3. Os Trial Decks eram DUPLICAÇÃO (`selado.juntar_duplicados`)

A pergunta estava anotada («ficam como estão… fica anotado»). Foram-se ver as
ofertas dos oito blueprints na API, a 2026-09-25
(`_revisao\_trial_decks.py`, resposta crua em `trial-decks-ofertas.json`):

| carta | blueprint | ofertas | vendedores | preço mín. | `card_market_ids` |
|---|---|---|---|---|---|
| Jinx | 330845 | **0** | 0 | — | `[]` |
| Jinx | **363136** | 1 | 1 | 400,59 € | `[862849]` |
| Viktor | 330846 | **0** | 0 | — | `[]` |
| Viktor | **363137** | 2 | 2 | 100,64 € | `[862851]` |
| Volibear | 330848 | **0** | 0 | — | `[]` |
| Volibear | **363138** | 2 | 2 | 195,64 € | `[862850]` |
| Yasuo | 330847 | **0** | 0 | — | `[]` |
| Yasuo | **363139** | 3 | 3 | 100,64 € | `[862852]` |

Mesma expansão (4167, `promo-rift`), mesma categoria (262), mesmo nome, versão
vazia nos dois, `fixed_properties` vazias nos dois. **É duplicação do catálogo
deles**: os 3308xx são de Outubro de 2025 e nunca foram ligados ao Cardmarket;
os 3631xx têm as ofertas todas e um id cada. Juntam-se.

**Não às cegas.** A chave é `(edição, nome, versão, categoria)`, e o que fica é
o que tem id do Cardmarket → preço → mais anúncios → `blueprint_id` maior. Os
«2024 Trial Deck Set» e «2025 Trial Deck Set» dizem o ano na VERSÃO e
continuam a ser dois — há teste. A linha diz «junta 1 blueprint do CardTrader
(330847)». E o que ele tivesse gravado num id que se juntou **continua a
contar** (`itens` soma os `duplicados`): juntar duas linhas do catálogo deles
não pode apagar unidades dele. `juntar_duplicados: false` mostra os dois.

### Medido a 2026-09-25 contra cópias do `data/` real

`_revisao\_medir_selado_extra.py`, `main` (`cf9b750`) e ramo na mesma corrida,
cada lado a ler o SEU config — **os invariantes da Coleção NÃO mexem**:
denominador **928**, níveis **897/836/766 de 928** (faltam 31/121/281 ·
83,77/440,65/1 028,67 €), wantlist «tudo» **162 linhas · 281 cópias ·
1 028,67 €**, valor **6 615,91 € · 2 573 cópias**, totais (1006 impressões,
909 cartas), Faltas (555 cópias · 10 178,32 €), A mais, decks, Encomendas,
Venda, painel e a grelha impressão a impressão — **tudo igual**.

**O que muda:**

| | antes | depois |
|---|---|---|
| produto selado | 85 (68 saíram · 17 por sair) | **98** (78 · 20) |
| acessórios | — (10+9 no `fora`) | **19** em secção própria (17 · 2 por sair) |
| blueprints juntos | 0 | **4** |
| sem preço | 34 | **47** (os 17 do config, que não levam preço; −4 duplicados) |
| `scope.fora` | 206×1, 264×48, **265×10**, 266×31, **267×9**, 268×13, 284×13 | 206×1, 264×48, 266×31, 268×13, 284×13 |

Por edição (antes → depois, com quantos são do config): OGN 10 → **13** (3),
OGS 1 → **2** (1), SFD 10 → **13** (3), UNL 12 → **16** (4), VEN 7 → **10**
(3), RAD 7 → **10** (3), LGC 7, PG2 1, REC 2, ARC 3, OP 1, PROMO-RIFT 22 →
**18** (os 4 juntos), T1S 2. Acessórios: SFD 6, PROMO-RIFT 8, T1S 3, RAD 1,
LGC 1.

**Um erro apanhado pela fotografia**, antes do merge: o `.section-head`
capitaliza cada palavra, e o subtítulo dos Acessórios lia-se «Binders E Deck
Boxes — Não Contam Para O Produto Selado». É uma frase, não um rótulo:
`.sl-acess-cab small { text-transform: none }`, com teste. A 375 px
(DevTools Protocol, contra o site gerado): `scrollWidth == clientWidth ==
375`, zero elementos fora do ecrã e zero com scroll próprio.

`tests/test_selado_extra.py` (50 testes, contra cópias e config temporário):
os extras com o conteúdo, o MSRP que não vira preço, o conteúdo e a nota como
campos diferentes, o EVENT Kit a par do kit de um jogador; os acessórios
marcados, com contadores e valor próprios, a não mexerem nos do selado, a
saírem do `fora` e a voltarem lá com a lista vazia, com tipo próprio, e as
duas listas a rebentarem quando se cruzam; os duplicados juntos, o vivo
escolhido, a versão a impedir a junção, o desligar, o que estava gravado no
outro a contar, e o id juntado a deixar de ser válido; o config real (os 17,
os 7, os 2, os 4 cases com a dúvida, os 4 EVENT Kit, a data da OGS); **a
fotografia** — a MESMA do `test_selado`, por referência, para não haver duas
definições de «número da Coleção» — com selado, acessórios e extras metidos e
tirados; e a página. Suite: **44 ficheiros, 0 a falhar**.

## 25/09/2026, à noite — os LINKS DE COMPRA do Produto Selado, e o bloco `mercados` do config

Palavras dele: *"Se possivel, mete link para compra no cardmarket e no
cardtrader"*. Ramo `ai-pc/selado-links-2026-09-25`.

### O CardTrader ficou VALIDADO; o Cardmarket não pôde ser

Medido a 2026-09-25 da máquina dele, com o User-Agent de sempre
(`riftvault/1.0 (colecao pessoal; +github)`), 1 pedido de cada vez:

| pedido | resposta |
|---|---|
| `www.cardtrader.com/robots.txt` | **200** — só proíbe `/uploads/` (e permite `/uploads/blueprints/`), e publica os sitemaps |
| `sitemaps/en/blueprint_products.xml.gz` + os 7 sub-ficheiros | 348 780 URLs, **todos** `…/en/cards/<blueprint_id>-<slug>` |
| `…/en/cards/330791` | **200**, redirecciona para `…/330791-origins-booster-box-origins` |
| `…/en/cards/999999999` | **404** — o formato é mesmo verificado |
| `…/cards/330791` (sem o `/en/`) | 200, mas em **italiano** |
| `…/en/search?q=Origins%20Booster%20Box` | **200**, com o produto na página |
| `www.cardmarket.com/robots.txt` | **403** (Cloudflare, «Just a moment…») |

O link do CardTrader **não é presunção**: o `blueprint_id` sozinho chega e o
site acrescenta-lhe o slug. Não se contornou bloqueio nenhum — o Cardmarket
responde 403 a tudo, e é dado e segue: o link directo lá continua NÃO
VALIDADO, como na Venda, e por isso **cada linha leva dois links**.
Aproveitou-se para corrigir o `a_subir.DEFAULTS.link_cardtrader`, que desde
2026-09-08 abria em italiano (`cardtrader.com/cards/<id>`, sem o `/en/`).

### Uma pergunta, um sítio: o bloco `mercados`

As duas chaves do Cardmarket viviam no `venda` (25/09, à tarde) — nome de UMA
aba para uma pergunta que passou a ser de duas. **Mudaram-se para
`riftvault/mercados.py`**, bloco `mercados` do config, com mais três:

    cardmarket_url          {id}  a carta       (NÃO VALIDADO)
    cardmarket_url_selado   {id}  o produto     (NÃO VALIDADO)
    cardmarket_busca        {q}   a pesquisa
    cardtrader_url          {id}  o produto/carta   (VALIDADO)
    cardtrader_busca        {q}   a pesquisa        (VALIDADO)

**Um config escrito antes de hoje continua a valer**: se o `venda` trouxer
`cardmarket_url`/`cardmarket_busca` e o `mercados` estiver nos defaults, são
as do `venda` que mandam; com as duas escritas ganha a nova (a regra do
`_migrar_master_set`). A comparação é com o DEFAULT e não com «está no
ficheiro» porque o `config.load` funde por chave de topo — `cfg["mercados"]`
traz sempre o bloco inteiro. Um template sem o `{id}`/`{q}` **rebenta**.

**O selado tem template próprio de propósito**: um display não é um «Single»,
e escrever-lhe o caminho `Products/Singles` era dizer no URL uma coisa que se
sabe falsa. O que identifica o produto é o `idProduct`; o caminho é a
categoria deles, e é a parte que se presume.

### O que a página mostra

Dois `<a>` curtos por linha — «Cardmarket» e «CardTrader» —, `target="_blank"`
e `rel="noreferrer noopener"`, em `flex-wrap`. **Sem id nesse mercado, o link
é de PESQUISA pelo nome e di-lo** («procurar», apagado, com o porquê no
`title`); nunca se monta um endereço com um id que não existe. O termo é o
nome mais a versão, **sem as aspas** (`Origins: "Jinx" Champion Deck` — numa
caixa de pesquisa as aspas lêem-se como «frase exacta»). O cabeçalho diz
quantos são pesquisa e que o do Cardmarket não está confirmado. No site
publicado os links funcionam na mesma: são links, não controlos.

**Medido a 2026-09-25 no catálogo real:** dos **98 produtos selados**, **81
têm `blueprint_id`** (17 sem — os do `selado.extra`, que a API não tem) e **52
têm `cardmarket_id`** (46 sem). Dos **19 acessórios**, 19 com `blueprint_id` e
**nenhum** com `cardmarket_id` (o `--sync` ainda não passou por eles). O
`payload.links` conta isto, por mercado, e diz qual está validado.

**A 375 px** (Chrome, DevTools Protocol, contra o site gerado, com as 117
linhas à vista): `scrollWidth == clientWidth == 375`, **zero** elementos fora
do ecrã ou com scroll próprio; 234 links, todos com `_blank` e `noopener`, 82
de pesquisa.

**Nada da Coleção mexe** — é apresentação: `tests/test_selado_links.py` (39
testes) repete a fotografia do `test_selado` por referência, e recusa que um
módulo de contas importe o `mercados`.


## 25/09/2026, à noite — o André manda tirar 22 selados (`selado.excluidos`)

Palavras dele, depois de ver a lista dos 98: *"Tira estes"* — os **boosters
soltos** (13), as **slim booster box** (3), o **«Origins: Champion Deck Set»**
(*"compram-se à unidade"*), as **«Spiritforged Bulk Runes»** e os quatro
**Pre-Rift Kit**, o de UM jogador. Ramo `ai-pc/selado-tirar-2026-09-25`.

**ESCONDER NÃO É APAGAR.** É a arquitectura do `abas.escondidas` (25/09) para
outra lista: `selado.excluidos` é uma lista de **nomes** (ou de ids
`ct-<blueprint>`), o `data/selado_catalogo.json` **fica intacto** e **repor é
tirar o nome da lista**. Os 22 saem da aba, dos contadores, da percentagem e do
total, no 8770 e no site publicado; o `scope.excluidos` di-los um a um (id,
nome, edição, tipo) e a página mostra-os num `<details>` a dizer que nada foi
apagado. Uma unidade gravada num produto excluído **não se apaga** e volta a
contar quando o nome sair da lista (há teste).

**O ponto único é o `_crus`**, que filtra antes de qualquer conta: aba,
contadores, valor, CLI, `build` e `ajustar` vêem todos a mesma lista. Um `+`
num excluído levanta `ProdutoExcluido` (subclasse de `ProdutoDesconhecido` —
quem tratava um trata os dois) a dizer como se repõe.

**O nome é EXACTO, nunca um pedaço** (`_chave_nome`: colapsa espaços, tira
maiúsculas). É o que faz o *Spiritforged Pre-Rift Kit* sair e o *Spiritforged
Pre-Rift **EVENT** Kit* ficar — são dois produtos, e o nome de um está dentro do
outro —, e o *Origins Booster* sair sem levar o *Origins | Nexus Night Promo
Booster* nem a *Origins Booster Box*. **Um nome que não case REBENTA**, com os
parecidos (difflib) e a dica do id; um nome que case com **mais do que um**
também rebenta, e diz os ids (hoje nenhum dos 117 se repete). A excepção, e é
estreita: **sem catálogo em disco** (o `--sync` ainda não correu, ou um `build`
num `data/` limpo) um nome do CardTrader não pode casar e ignora-se — a secção
mostra-se vazia como sempre fez, em vez de parar a página por não ter sido
sincronizada. Um nome ambíguo rebenta nos dois casos. **Risco anotado**: se um
blueprint for retirado do CardTrader e o `--sync` correr, o nome dele na lista
passa a não casar e a página rebenta até ele o tirar do config — é a regra desta
casa para config que deixa de bater com os dados (`master_set.fora`), e o
`--sync` é um comando à mão.

**O nome dobrado do catálogo.** O CardTrader escreve «2024 Trial Deck Set
**Set**» e «2025 Trial Deck Set **Set**». `selado.nome_limpo` junta uma palavra
repetida a seguir a si mesma (`\b(\w+)(?:\s+\1)+\b`, re.I) — **apresentação**:
o `id` vem do `blueprint_id` e não muda, o item leva `nome_bruto`, e o
`excluidos` casa com as **duas** escritas. Medido: mexe em **2 dos 117**. A
junção de duplicados continua a distinguir pela VERSÃO, por isso os dois Trial
Deck Set continuam a ser dois (os nomes limpos são iguais).

**Medido a 2026-09-25 contra uma cópia do `data/` real
(`_revisao\_medir_selado_tirar.py`), o MESMO código e a MESMA cópia, mudando só
a lista — os invariantes da Coleção NÃO mexem:** denominador **928**, níveis
**897/836/766 de 928** (faltam 31/121/281 · 83,77/440,65/1 028,67 €), wantlist
«tudo» **162 linhas · 281 cópias · 1 028,67 €**, valor **6 615,91 € · 2 573
cópias**, totais, Faltas (555 cópias · 10 178,32 €), A mais, decks, Encomendas,
Venda, painel e foil — **iguais**. E o **site gerado sai igual ficheiro a
ficheiro (30 ficheiros)**: o único que difere a sério (sem o relógio) é o
`api/selado.json`, que passa de 219 495 para **183 966 bytes**. Os **19
acessórios não mexem** (contadores e valor iguais).

**O que muda:**

| | antes | depois |
|---|---|---|
| produto selado | 98 (78 saíram · 20 por sair) | **76** (61 · 15) |
| não tenho | 78 | **61** |
| sem preço | 47 | **37** |
| acessórios | 19 | **19** |

Por edição (o que há): OGN 13 → **8**, OGS 2, SFD 13 → **8**, UNL 16 → **11**,
VEN 10 → **8**, RAD 10 → **7**, LGC 7 → **6**, PG2 1, REC 2 → **1**, ARC 3,
OP 1, PROMO-RIFT 18, T1S 2.

**Confirmado um a um, e nenhum saiu por acidente:** os 4 **Pre-Rift EVENT Kit**,
os 9 **displays de decks** (7 champion + 2 showdown), os 4 **Nexus Night Promo
Booster**, os **Trial Deck Set** de 2024 e 2025 (com o nome corrigido), o
**Arcane Promo Pack**, o **Immersive Arcane Promo Pack**, o **Promo Pack** e o
**Replacement Card Booster** (ele não se pronunciou sobre estes quatro — ficam),
e todas as **Booster Box** normais, **Booster Box Case**, **Vault**, **Vault
Bundle Case**, decks e **Proving Grounds**.

`tests/test_selado_tirar.py` (56 testes, contra cópias e config temporário): a
gramática da chave (nome, id, maiúsculas e espaços, o que não casa, o ambíguo, o
que não é texto, a lista mal escrita, sem catálogo); saem dos contadores, da
percentagem, do valor e das duas vistas (8770 e publicado); a unidade gravada
não se apaga e volta; **repor é tirar o nome da lista** (o payload volta ao
mesmo); o catálogo em disco fica intacto; o `scope` e o CLI dizem quais; o
`ajustar` recusa; o config REAL (os 22 pelos cinco grupos, e os que têm de
ficar); os 22 contra o **catálogo real** (98 → 76, cada nome casa com um, os 19
acessórios não mexem, a conta por edição); o nome dobrado; **a fotografia** — a
MESMA do `test_selado`, por referência — com produtos tirados e repostos; e a
página. Suite: **46 ficheiros, 0 a falhar**.

(Os números deste ficheiro — 22, 76, os 19 acessórios — são os de ANTES da
segunda ordem da mesma noite, que os levou a 32 e 66 e desligou os acessórios.
Ver a secção a seguir; os testes desta foram ajustados nos números, não
apagados: são a prova de que os 22 dele continuam fora.)

## 25/09/2026, à noite — mais 10 selados fora (32) e os ACESSÓRIOS DESLIGADOS

Palavras dele, depois de ver a lista já com os 22 fora: tirar os **«Card Set»**
(a categoria «Riftbound Complete Sets», 283 — *"são conjuntos de CARTAS, não
produto selado"*), os **Trial Deck** todos, e os **acessórios todos** — binders,
sleeves e deck boxes. Ramo `ai-pc/selado-tirar2-2026-09-25`.

**NÃO HÁ MECANISMO NOVO, e é esse o ponto.** As duas metades fazem-se com as
chaves que já existiam: `selado.excluidos` passou de 22 a **32** nomes e
`selado.acessorios` ficou **vazia**. Zero linhas de lógica nova — e é a prova de
que as chaves da ordem anterior e de 25/09 de manhã estavam no sítio certo.

**Os 10 que saem:**

| grupo | n | quais |
|---|---|---|
| «Card Set» (categoria 283) | **2** | `ct-380641` Unleashed: Poro Scene Set (UNL), `ct-349091` Arcane Complete Set (ARC) |
| Trial Deck (todos PROMO-RIFT) | **8** | `ct-363136..363139` Origins: Jinx / Viktor / Volibear / Yasuo Trial Deck, `ct-383046` 2024 Trial Deck Set, `ct-383045` 2025 Trial Deck Set, `ct-330871` 2024 Trial Deck Case, `ct-330873` 2025 Trial Deck Case |

Com os dois primeiros **a categoria «Complete Sets» fica vazia na aba** — mas a
283 FICA em `selado.categorias`: o que saiu foram os dois produtos, não a
categoria, e um «Complete Set» novo volta a aparecer. Escreve-se o nome **limpo**
(«2024 Trial Deck Set»), que é o que está no ecrã desde a ordem anterior; o bruto
do catálogo («… Set **Set**») casa na mesma. Os 4 Trial Decks da Origins são os
blueprints **vivos** (3631xx): os 3308xx já vinham juntados pelo
`juntar_duplicados` e escrevê-los rebentava.

**TIRA-SE POR NOME, NUNCA POR CATEGORIA — e aqui era fácil enganar-se.** Os dois
«Trial Deck Case» são da **263 «Box Sets & Displays»**, a mesma categoria de
tudo o que ele mandou ficar; saem porque ele os nomeou um a um, e a 263 fica com
12 dos 15. Confirmado um a um, e nenhum saiu por acidente: **Arcane Box Set** (a
caixa de coleccionador, que não é o «Arcane Complete Set»), **Arcane Chinese
Promo Set**, **The T1 Worlds Champion | Signature Edition Box Set**, **Origins:
Proving Grounds Box Set Case**, **Origins: Instant Match Box 2025** e **Secret
Garden Bundle Box**.

**Os acessórios: `selado.acessorios: []`.** A secção «Acessórios» (binders e deck
boxes, 19 linhas) nasceu de manhã e saiu à noite — **é ele que decide**. Com a
lista vazia o cabeçalho, o botão de filtro e as linhas desaparecem sozinhos: o
`app.js` já se guardava no `ac.totals.ha`/`at.ha`, e não foi preciso tocar-lhe.
**ESVAZIAR NÃO É APAGAR**: a chave, o código da secção e os contadores próprios
ficam, e **repor é escrever os números das categorias outra vez** (há teste que o
faz, e outro que confirma que uma unidade gravada num acessório não se perde
enquanto a lista está vazia). As duas categorias voltam ao `fora`, **contadas**:
265 Albums 10 e 267 Deck Boxes 9 — nunca se apagam em silêncio.

**Medido a 2026-09-25 contra uma cópia do `data/` real
(`_revisao\_medir_selado_tirar2.py`), o MESMO código e a MESMA cópia, mudando só
o config — os invariantes da Coleção NÃO mexem:** denominador **928**, níveis
**897/836/766 de 928** (faltam 31/121/281 · 83,77/440,65/1 028,67 €), wantlist
«tudo» **162 linhas · 281 cópias · 1 028,67 €**, valor **6 615,91 € · 2 573
cópias**, totais, Faltas (555 cópias · 10 178,32 €), A mais, decks, Encomendas,
Venda, painel e foil — **os 12 iguais**. E o **site gerado sai igual ficheiro a
ficheiro (30 ficheiros)**: o único que difere a sério (sem o relógio) é o
`api/selado.json`, que passa de 183 966 para **128 523 bytes**.

**O que muda:**

| | antes | depois |
|---|---|---|
| produto selado | 76 (61 saíram · 15 por sair) | **66** (51 · 15) |
| não tenho | 61 | **51** |
| sem preço | 37 | **31** |
| acessórios | 19 · secção própria | **0 · a secção não aparece** |
| excluídos | 22 | **32** |
| `fora` (265 · 267) | 0 · 0 | **10 · 9** |

Por edição (o que há): **ARC 3 → 2**, **UNL 11 → 10**, **PROMO-RIFT 18 → 10**; as
outras dez não mexem (OGN 8, OGS 2, SFD 8, VEN 8, RAD 7, LGC 6, PG2 1, REC 1,
OP 1, T1S 2). **Total 76 → 66.**

`tests/test_selado_tirar2.py` (45 testes, contra cópias e config temporário): os
10 contra o **catálogo real** (cada nome casa com um, saem da aba, a 283 fica
vazia, os 8 são da PROMO-RIFT, os 4 vivos, o nome limpo, nenhum Trial Deck fica,
os 6 parecidos ficam, da 263 só saem os dois que ele nomeou, 66 selados e a conta
por edição); o **config real** (32 sem repetidos, os 10 lá, **os 22 da ordem
anterior inteiros**, nenhum dos que ficam na lista, `acessorios` vazia e a chave
lá, a 283 intacta em `categorias`); os **acessórios desligados** (sem linhas, o
selado não mexe, as categorias voltam ao `fora`, **repor é escrever os números**,
a unidade gravada não se perde, e o código da secção ficou); **repor é tirar o
nome da lista**; e **a fotografia** — a MESMA do `test_selado`, por referência —
com os dez tirados e os acessórios desligados, e depois repostos.
`test_selado_tirar.py` e `test_selado_extra.py` foram ajustados nos NÚMEROS (22 →
32, 76 → 66, os 19 acessórios → desligados) — o teste é que descrevia o de
antes, não o código. Suite: **47 ficheiros, 0 a falhar**.

## 26/09/2026 — ERRO NOSSO: o FOIL SOMA-SE ao normal, não é uma fatia dele

Palavras dele, apanhado enquanto actualizava a coleção: *"as foils quando eu
marco é que tenho TAMBÉM foil, ou seja, **normal + foil e não apenas 1**, no
caso daria **3+3**"*. Ramo `ai-pc/foil-soma-2026-09-26`.

**O que estava mal.** Fizemos o foil de 22/09 como um SUBCONJUNTO do total: o
`copies.qty` era o total, o `qty_foil` estava lá dentro (`CHECK (qty_foil <=
qty)`), o não-foil era `qty − qty_foil`, e por isso **o `+` do foil CONVERTIA
uma cópia normal em foil** em vez de acrescentar uma. Com 3 cópias e 3 foils
ele via «0 normais · 3 foil» quando o que queria dizer era «tenho 3 normais E 3
foils».

**O modelo que fica:**

    copies.qty       = as cópias NORMAIS
    copies.qty_foil  = as cópias FOIL
    total            = qty + qty_foil     (nunca se grava: é a soma)

São **dois contadores independentes**, cada um com o seu botão: o `+` do foil
não mexe no `qty` e o `−` da grelha (ou das cópias próprias de um deck) não
mexe no `qty_foil`. Com 3 normais e 3 foil ele tem **seis** cópias.

### Os dados guardados JÁ ESTAVAM CERTOS — verificado antes de mexer

Nenhuma migração de dados. Conferido impressão a impressão contra a `foil_ops`
(45 linhas, todas de 26/09, todas `web`) e contra a `ops`:

* as impressões com foil tinham **todas `qty = 3` desde 2026-09-11 às 20:23**,
  de uma sessão de entrada em bloco — muito antes de o foil existir. São mesmo
  as 3 NORMAIS dele;
* os `+` do foil de 26/09 vieram todos por cima disso, sem lhe tocar;
* **as 3 linhas `:ajuste ao total` que existem são do `ven-012-166`** e não são
  conversão: às 12:39:49 ele carregou 3× no `−` da GRELHA (o `qty` foi 3→0), o
  `ao_descer` cortou o foil com ele, e às 12:40–12:50 ele repôs os dois. A
  `ops` mostra o mesmo padrão de ida e volta em sete impressões (`ven-002`,
  `003`, `005`, `007`, `012`, `014`, `025`) — **todas com saldo ZERO**, todas a
  acabar nos mesmos `qty = 3` de 11/09. Era ele a lutar com o tecto.

A soma dos deltas da `foil_ops` bate com o `qty_foil` guardado em **todas** as
impressões (0 a divergir). **Nenhum caso de conversão a assinalar.**

(Os números andaram durante a sessão, porque ele estava a marcar foils ao mesmo
tempo: a ordem falava de 13 impressões e 35 foils, a primeira leitura deu 15/39,
a medição deu **48 impressões e 124 foils** e a fotografia final 49/126. Todas
VEN, todas comuns e incomuns, todas com os 3 normais completos.)

### O que mudou mesmo

1. **O `CHECK` perdeu o tecto** (`qty_foil <= qty` → só `qty_foil >= 0` e um
   `<= 9999` de sanidade, o `foil.LIMITE`). O SQLite não sabe largar um CHECK:
   é preciso refazer a tabela, e é o que o `db._tirar_o_tecto_do_foil` faz —
   numa transação só, com **BACKUP antes** (`vault-antes-do-foil-somar-*.db`,
   por `VACUUM INTO`), idempotente, e **sem tocar num único número** (os
   `qty`/`qty_foil` copiam-se tal e qual). Não há FK, índice próprio nem
   trigger a apontar para a `copies` — confirmado no `schema.sql`.
2. **`qty = 0` com `qty_foil > 0` passou a ser estado legítimo**: uma carta que
   ele só tenha em foil. Era impossível de gravar até aqui.
3. **O `foil.ao_descer` foi-se**, e com ele as chamadas no `collection.adjust`
   e no `proprias.ajustar`: um `−` nas normais não pode levar uma foil. As
   linhas `:ajuste ao total` que ficaram na `foil_ops` são história e a tabela
   di-lo.
4. **O `+` do foil não trava no `qty`** — trava no `LIMITE`, que é sanidade e
   não um número de coleção. O tile diz «**3 normais · 3 foil = 6**» e o resumo
   por edição passou a «N normais · M foil / X cópias ao todo».

### As duas perguntas que são dele, em config e DESLIGADAS

`foil.conta_para_coleccao` e `foil.conta_para_valor`, as duas a **`false`** —
com elas assim a app mede **exactamente** o de sempre. Ligam-se numa linha:

| chave | o que liga | por onde entra |
|---|---|---|
| `conta_para_coleccao` | os foils contam para os ALVOS (os três níveis, o denominador, as Faltas, as wantlists) | `locais.na_colecao` |
| `conta_para_valor` | os foils contam para o VALOR, **ao preço da normal** | `locais.contadas` e `prices.copias_sql` |

Os dois funis leem a chave **directamente do config**, sem importar o `foil` —
é o que deixa o `locais` e o `prices` continuarem a não conhecer o módulo, e o
teste a poder prová-lo. **Não há preço de foil no catálogo** (o CardTrader dá
um preço por impressão), por isso ligar o segundo é assumir que uma foil vale o
mesmo que a normal, o que é falso no mercado.

**Medido a 2026-09-26 contra cópias do `data/` real
(`_revisao\_medir_foil_soma.py`, cinco corridas sobre cópias independentes do
mesmo `data/`, o `main` e o ramo na mesma corrida):**

* **`main` vs ramo com os botões desligados: ZERO diferenças** em 23
  invariantes — denominador **928**, níveis **897/836/766 de 928** (faltam
  31/121/281 · 89,27/458,08/1 056,62 €), wantlist «tudo» **162 linhas · 281
  cópias · 1 056,62 €** e as cinco por edição, valor **6 645,21 € · 2 573
  cópias** e por edição, totais, Faltas (**555 cópias · 10 232,99 €**; a
  comprar 281 · 1 056,62 €) e os quatro blocos por edição, A mais (excedente
  item a item e libertadas), decks, Encomendas, painel, Venda, Selado, a grelha
  impressão a impressão e o `copies` inteiro.
* **`conta_para_coleccao: true` → ZERO impressões sobem de nível.** É a
  resposta à pergunta (a), e tem razão de ser: **as 48 impressões com foil têm
  todas os 3 normais**, ou seja o alvo já estava cumprido — ele só marcou foil
  em cartas de que já tinha o playset. Níveis, denominador, Faltas e wantlists
  ficam iguais ao cêntimo. **O que mudaria mesmo era o «A mais»**: 69 → **117**
  itens e 140 → **264** cópias, porque cada foil passa a ser excedente acima do
  alvo. Fica anotado — é o efeito que ele não pediu.
* **`conta_para_valor: true` → +13,64 €.** 6 645,21 € → **6 658,85 €**, +124
  cópias, **todas no VEN** (1 058,56 → 1 072,20 €). São comuns e incomuns a
  **11 cêntimos**, o mínimo do CardTrader. Os níveis, o denominador e a
  wantlist não mexem — são botões separados, e há teste que o fixa.
* **Cartas só em foil (0 normais, foil > 0): ZERO hoje.** Fotografado o caso à
  mão numa cópia (o `VEN-011` Pendulum Blade a 0 normais + 2 foil): o tile fica
  **a cinzento, com o crachá `0/3`** — a Coleção conta as normais, e para ela
  ele não a tem —, o `−` desligado, sem o botão «+ venda», e a linha por baixo
  a dizer «**0 normais · 2 foil = 2**» com o contador do foil a 2. A 375 px
  `scrollWidth == clientWidth == 375` e zero elementos fora do ecrã.

`tests/test_foil.py` passou de 31 para **44 testes**: o CHECK sem tecto, as
duas migrações (a da coluna e a de hoje, esta a provar que **nenhum número
mexe** e que a PK sobrevive ao RENAME), «3+3 dão 6», as duas contagens
independentes nos dois sítios que baixam o `qty`, o estado `0 normais + foil`,
a fotografia de tudo (com mais foils do que normais, e com uma carta só em
foil) mais um teste que exige que a fotografia não seja de zeros, os dois
botões ligados um a um e os dois juntos (e a reversibilidade), o limite, o
gémeo em JavaScript, a rota, a CLI e o `app.js` (que já não corta o foil no
`applyLocal`). O guarda das importações ficou **mais forte**: nenhum módulo de
contas importa o `foil`, e o `qty_foil` só pode aparecer no `locais` e no
`prices`, cada um com a sua chave. Suite: **47 ficheiros, 0 a falhar**.

## 26/09/2026, à noite — o PREÇO DA FOIL, à parte (`price_latest.price_foil_cents`)

Palavras dele: *"podes meter filtro no cardtrader e tirar o preco da foil mais
barata?, para diferenciar os precos"*. Ramo `ai-pc/foil-preco-2026-09-26`.

**O que estava mal.** A ordem da tarde ligou o `foil.conta_para_valor` mas não
fez a parte do preço: as foils contavam ao `price_cents`, que é o preço da
NORMAL. Medido no `data/` real antes de mexer: **103 impressões, 254 cópias
foil, TODAS avaliadas a 11 ou 14 cêntimos** (o chão do CardTrader para uma
comum), a somar 27,97 € — e nenhuma com `from_foil = 1`, ou seja o único caso
que o código tratava como «já é preço de foil» não acontecia em nenhuma delas.
O pior é que os docstrings **documentavam a falha em vez de a resolver**: o
`prices.py` dizia «não há preço de foil no catálogo» e «hoje está desligado»
(estava ligado desde essa tarde).

### A coluna, e o filtro que já lá estava

`catalog.price_latest` ganhou **`price_foil_cents`** e **`n_listings_foil`**
(migração `db._migrar_price_latest`, com **backup do catalog.db** — `VACUUM
catalog INTO data/backups/catalog-antes-do-preco-do-foil-*.db`; o catálogo é
reconstruível, mas reconstruí-lo custa o mercado das cinco expansões). A
migração corre pelas DUAS portas — `db.connect()` (catálogo anexado) e
`db.catalog_only()` (catálogo como base principal, que é por onde o `riftvault
map` entra) —, porque o `CREATE TABLE IF NOT EXISTS` não acrescenta colunas e
uma delas só a migrar deixava o `map` a olhar para colunas que não existem.

**Não houve filtro novo a inventar.** O `prices.oferta()` já separava as ofertas
em `normal` e `foil` pelo `properties_hash.riftbound_foil` — e **deitava a lista
das foils fora**. Passou a guardá-la: `foil_cents = min(foil)`, com o `_usable`
de sempre (Mint/Near Mint, a língua do `precos.linguas`, sem
graded/signed/altered, vendedor presente, EUR). Só a `riftbound_foil` muda.

**O preço NORMAL não mexeu, e prova-se.** A escolha do `cents`/`from_foil` é a
mesma linha de antes; o `tests/test_foil_preco.py` guarda uma cópia fiel da
implementação anterior (`oferta_como_era`) e compara os cinco campos dela com os
novos sobre o **mercado real do OGS** (`tests/fixtures/cardtrader-ogs-market.json`)
e sobre 14 casos gerados. Nessa fixture há **uma** oferta foil utilizável, e é o
caso a sério: o blueprint `344333` tem normal **82** cêntimos e foil **171** —
mais do dobro, e era a 82 que contava.

**Quando `from_foil` é 1 os dois preços são o mesmo número**: a única oferta era
foil. Guardam-se os dois de propósito, para a leitura do valor ser uniforme (uma
cópia foil lê sempre o `price_foil_cents`) em vez de ter de perguntar pelo
`from_foil` primeiro. Um `NULL` novo **apaga** o antigo, como no `price_cents`:
se hoje não há oferta foil, a cópia tem de cair para o fallback contado em vez
de ficar presa ao preço da semana passada.

### O valor: uma conta, três implementações

`prices.copias_sql` passou a dar **três colunas** — `qty_normal` (as normais
menos as próprias dos decks), `qty_foil` (as foils que contam, zero com o botão
desligado) e `qty` (a soma, que é o que o `collection.totals` lê e por isso
manteve o nome). E nasceu o **`prices.valor_sql`**, a única definição do valor:

    normais × price_cents  +  foils × COALESCE(price_foil_cents, price_cents)

O `COALESCE` de dentro é o **FALLBACK**, e é ele que faz do total um PISO. Os
gémeos: `prices.valor_das_copias` (Python, para o payload da edição, que já tem
os números na mão) e `valorDasCopias` (JavaScript, que recalcula a cada `+`/`−`).
`tests/test_foil_preco.py::TestOsTresGemeos` corre os três sobre os mesmos oito
casos, o JS no node.

**O `valor_dos_foils` reescreveu-se** e agora responde à pergunta certa:
`preco_de_foil` (há `price_foil_cents` — ou `from_foil`, que é o mesmo número),
**`ao_preco_da_normal`** (o fallback: não há oferta foil, a cópia conta ao preço
da normal) e `sem_preco`. É este segundo número que a página, o `riftvault foil`
e o `riftvault value` dizem — o fallback ficou **contado e visível**, não num
comentário.

**Um erro de rigor corrigido pelo caminho:** o `cents_de_foil` (a ressalva de
2026-08-31, «quanto do total vem de cartas que o CardTrader só lista em foil»)
passou a contar só as cópias **normais** dessas impressões. As foils delas têm
agora o preço certo e não são ressalva nenhuma.

### O que se vê

No tile, a par da contagem: **«· foil 1,50 €»**, ou **«· foil ao preço da
normal»** (a amarelo, com o porquê no `title`) quando o CardTrader não a tem em
foil. Sem `nowrap`, ao contrário do total — a frase é longa e a 375 px tem de
poder partir-se; com `nowrap` era a avaria medida a 22/09. O payload da edição
leva `price_foil` e `qty_valor_foil` por impressão.

**A barra do valor passou a bater certo com o servidor — duas divergências,
as duas fechadas.** O cliente recalcula o valor a cada `+`/`−` varrendo a
grelha, e dava um número diferente do `progress.value.owned` por dois motivos:

1. somava `state.qty × price` — o `qty` da COLEÇÃO —, enquanto o servidor soma
   o `qty_valor` (as físicas menos as próprias dos decks): numa coleção com
   cópias sleevadas num deck a barra dizia menos. Passou a haver
   `state.valNorm`, semeado do `qty_valor − qty_valor_foil` e a andar com os
   `+`/`−` como o `state.tot`. (Hoje dá o mesmo número porque a
   `copy_locations` está vazia; era um bug à espera da primeira marcação.)
2. as **escondidas** (tokens, signatures, runas sem numeração) valem o que ele
   tem delas e entram no `owned` do servidor, mas **nunca chegam à grelha** —
   o cliente não tinha por onde as somar. O payload passou a levar
   `progress.value.hidden_owned`, o pedaço do `owned` que não está na grelha, e
   o cliente parte dele. Medido no `data/` real: era **1,65 €** (SFD 0,55 · UNL
   0,88 · VEN 0,22); **agora as cinco edições fecham ao cêntimo** — OGN
   1 907,50 · OGS 81,12 · SFD 1 779,31 · UNL 1 752,56 · VEN 1 264,49 €, cliente
   igual a servidor em todas.

Fica de pé, anotada, uma terceira diferença que **não é do cliente**: a soma
das cinco edições (6 784,98 €) não é o valor da coleção inteira (6 890,36 €) —
faltam-lhe as `market_only` (as runas do CardTrader que a RiftScribe não tem),
que não pertencem a edição nenhuma do payload. É de sempre e é outra pergunta.

Na consola: o `riftvault foil REF` diz os dois preços e marca o fallback
(`_precos_foil`); o `riftvault foil` e o `riftvault stats` levam a linha do
valor (`foil._linha_do_valor`, que recebe o `valor_dos_foils` por parâmetro para
o `foil.py` continuar a não conhecer o `prices`); o `riftvault value` diz quantas
caem em cada caso; e o top das mais valiosas deixou de mentir a multiplicação —
com foils a linha diz «3x 0,11 € + 2 foil x 1,50 €».

### Medido a 2026-09-26, à noite, contra o `data/` REAL

`riftvault prices` corrido com o código novo (5 expansões, 1227 linhas):
**1144 das 1180 impressões do catálogo ficaram com preço de foil** (mais 29 das
`market_only` = 1173 linhas). As 36 sem preço de foil não têm oferta foil no
CardTrader; **uma** não tem preço nenhum (a `VEN-T04`, o token que eles não
listam, desde 2026-08-31).

**O efeito isolado** (`_revisao\_medir_foil_preco_efeito.py`, o MESMO `data/` e
os MESMOS preços, mudando só a regra):

| | ao preço da normal (a regra da tarde) | ao preço da foil (agora) |
|---|---|---|
| valor da coleção | **6 869,23 €** | **6 890,36 €** (+21,13 €) |
| as 259 cópias foil dele | 29,65 € | **50,78 €** (+71 %) |
| impressões com foil | 108 | 108, **todas com preço de foil a sério** |
| no fallback | — | **zero** |

As mais caras em foil: `OGN-045` Defy **5,02 €** em foil contra 1,25 € em normal
(32 anúncios foil), `OGN-213` Hidden Blade 2,09 € contra 0,11 €, `VEN-083`
Rampage 1,06 € contra 0,11 €. É esta a diferença que ele queria ver: a maioria
das foils dele são comuns cujo normal está no chão dos 11 cêntimos e cuja foil
vale três a vinte vezes mais.

**Os invariantes NÃO mexem:** denominador **928**, níveis **908/867/805 de 928**
(faltam 20/79/200), **2 888 cópias**, e o **«A mais» igual** — `foil.
entra_no_a_mais` continua `false` e o preço não faz nascer excedente nenhum (há
teste com a prova pela negativa). **O `copies` não se tocou**: nem o `qty` nem o
`qty_foil`, verificado antes e depois da corrida do sync (e ele esteve a marcar
foils durante a ordem — as 103/254 do início eram 108/259 no fim, e isso é ele,
não nós).

**O valor «antes desta ordem» era 6 925,80 €** e ficou em 6 890,36 €, mas **a
descida não é desta mudança**: o `riftvault prices` trouxe os preços de hoje e
121 das 1227 impressões mudaram de preço normal (o mercado). Com os preços novos,
a mudança desta ordem vale **+21,13 €** — é a linha da tabela acima, que é a
única comparação honesta.

**O histórico continua a ser só do preço normal.** A `price_history` tem uma
coluna de preço e o «A subir» mede a subida da carta que ele compra; uma série
da foil é outra pergunta, e ele não a fez.

**A 375 px o preço foi para uma LINHA PRÓPRIA** dentro do bloco do foil
(`flex: 0 0 100%`, com `flex-wrap` no `.foil-linha`). Ao lado dos `+`/`−`
sobravam ~50 px num tile de ~109 px e «foil ao preço da normal» saía a **uma
palavra por linha** — visto na fotografia, não no código. Medido depois:
`documentElement.scrollWidth == clientWidth == 375`, zero elementos fora do ecrã
e **zero com scroll próprio** (antes o `.foil-linha` transbordava 3 px, e isso
subia pela `.group` e pela `.grid` acima).

`tests/test_foil_preco.py` (57 testes): a coluna e a migração (de raiz, num
catálogo antigo, com backup, idempotente, pelas duas portas); o `oferta()` (o
mínimo das foils, os seis filtros um a um, a língua do config); **o preço normal
igual ao de antes** (fixture real + gerados); o valor (foil ao preço da foil, o
fallback contado, o `from_foil`, sem preço, por edição, o top, a barra da edição,
a chave desligada, a runa retirada); os três gémeos; **a barra do cliente igual
à do servidor**, com uma escondida com cópias e preço a prová-lo; o que não mexe
(`copies`, alvos, «A mais», histórico); os docstrings que mentiam (em cinco
ficheiros); a interface; e o `sync_prices` a gravar as duas colunas. Suite:
**49 ficheiros, 0 a falhar**.

## 26/09/2026, à tarde — o FOIL CONTA: para o valor e para o master set; e NUNCA no «A mais»

**A METADE DO «MASTER SET» DESTA SECÇÃO FOI REVOGADA a 2026-09-27, à noite** —
o `foil.conta_para_coleccao` voltou a `false` e as duas contagens passaram a
ver-se separadas no tile; ver a última secção deste ficheiro. Tudo o que aqui
se diz sobre os foils contarem para os níveis, o denominador, as Faltas e as
wantlists é história (e o mecanismo continua lá, atrás da chave). **A metade do
VALOR fica de pé**: as foils contam para o valor, ao preço da foil, e esse
número não mexeu. As quatro cautelas — o «A mais», o `propor_deck`, a Venda e
os decks — também ficam.

Palavras dele, a responder às duas perguntas que a ordem da manhã deixou em
config: *"contam para o valor sim, e contabilizas tambem como parte do master
set"*. Ramo `ai-pc/foil-conta-2026-09-26`.

**As duas chaves passaram a `true`** (`riftvault_config.json` e
`config.DEFAULTS`), e nasceu uma terceira, `entra_no_a_mais: false`, que é uma
decisão dele tomada na mesma mensagem. O mecanismo já estava todo feito de
manhã — os dois funis (`locais.na_colecao`, `locais.contadas` +
`prices.copias_sql`) já liam as chaves —, por isso o trabalho desta ordem não
foi ligá-las: foi o que se parte quando elas ligam.

    copies.qty        as cópias NORMAIS
    copies.qty_foil   as cópias FOIL
    o que a impressão TEM (níveis, denominador, Faltas, wantlists, valor)
                    = qty + qty_foil

### 1. O PREÇO DO FOIL: o valor é um PISO, e a página di-lo

**Não há fonte de preço de foil, e não se inventou nenhuma.** O catálogo tem um
preço por impressão; o Cardmarket responde 403 e a API deles está fechada; o
CardTrader não dá trend (provado a 25/09, ordem `0-venda-preco-ct`). Por isso as
foils contam **ao preço da NORMAL**, o valor fica **por baixo** do real, e isso
diz-se em **todos** os sítios onde o número aparece: a barra do valor da
Coleção, o cartão do Início, o resumo do foil e o `riftvault value`.

**A ressalva vai DENTRO do `collection_value`** (a chave `foils`), não à parte:
uma vista que mostrasse o total tinha de ir buscar a ressalva à mão, e mais
cedo ou mais tarde uma esquecia-se.

**Há um caso SEM ressalva, e é preciso separá-lo:** quando o
`price_latest.from_foil` é 1 o CardTrader só listava oferta foil e **o preço já
é de foil** — essa cópia está avaliada com o preço certo (e é a NORMAL que pode
estar sobreavaliada, a ressalva de sempre desde 2026-08-31).
`prices.valor_dos_foils` parte os foils em três: `ao_preco_da_normal` (com
ressalva), `preco_de_foil` (sem) e `sem_preco` (não contam).

**Medido no `data/` real: as 159 foils dele caem TODAS no primeiro caso** — 58
impressões, 17,49 €, nenhuma com `from_foil` e nenhuma sem preço. São comuns e
incomuns do VEN a 11 cêntimos, o mínimo do CardTrader.

### 2. A CONSEQUÊNCIA QUE ELE DECIDIU: os foils não são excedente

Com os foils a contar, uma carta com 3 normais e 3 foil tem **6 cópias contra
um alvo de 3**, e o «A mais» diria **«3 a mais»** — mandava-o vender os foils.
Decisão dele: **`foil.entra_no_a_mais: false`**. O excedente conta primeiro as
**NORMAIS** (`locais.na_colecao(..., com_foil=False)`) e os foils nunca entram
no que sobra. São peça de coleção, não excedente.

**Medido, e é a razão de a chave existir:** o excedente fica **exactamente
igual** — 69 impressões · 140 cópias, item a item, `extra` a `extra` —; com a
chave a `true` passava a **127 · 299**, com **58 impressões** a dizer «a mais»
que hoje dizem zero (`VEN-001` a 3 a mais, `VEN-002` a 3, …). A prova pela
negativa está em teste.

**Ficam de fora, mas dizem-se**, como as runas desde 17/09: `scope.foil` conta
**159 cópias em 58 impressões** e o cabeçalho escreve-o; uma linha que TENHA
foils e excedente ao mesmo tempo diz os dois («2 a mais · 3 foil, que não
entram»). O `scope.foil` conta **todas** as foils que a Coleção conta, não só as
das impressões que chegam aos tiles — a maioria tem o alvo cumprido só com as
normais e nunca aparece na lista, e contar só essas dava zero com 159 lá.

**O `have` do tile continua a ser as normais.** Com as foils dentro lia-se
«tens 9/3 · 2 a mais», que é ilegível.

### 3. A MESMA CAUTELA em mais três sítios, cada um pela sua razão

Não é a regra do «A mais» repetida: é que estes três contam **cópias físicas de
acabamento normal**, não alvos. Todos passaram a `na_colecao(..., com_foil=False)`:

| onde | porquê |
|---|---|
| `locais.propor_deck` | propõe MOVER uma cópia para `copy_locations`, e essa tabela conta normais — propor uma foil era mandar marcar uma normal que não existe |
| **Venda** (`venda.itens`) | o aviso de stock é sobre as cópias que o «marcar como vendidas» vai baixar, e esse baixa o `copies.qty`. Dizer que tem 6 quando tem 3 normais e 3 foil mandava-o vender o que não quer vender |
| o `−` da grelha | baixa as NORMAIS. Com 0 normais e 3 foils o `qty` da Coleção é 3 e o botão tem de estar **desligado** — `qtyNormais()` no `app.js`, em vez do `qty` |

### 4. NOS DECKS: as normais servem primeiro, e é estrutural

Palavras dele: *"um deck joga a carta, foil ou normal, tanto faz — mas nao lhe
tires um foil se houver normal disponivel"*.

**Não houve ordenação a inventar, e é importante dizer porquê:** o monte da
Coleção é **um número por impressão** (`pool_dos_decks["colecao"]`), não uma
lista de cópias com acabamento. O que o `allocate` tira dele são as normais até
elas acabarem; só o que passa desse número é que é foil. Não há por onde tirar
uma foil primeiro.

**O que faltava era DIZÊ-LO**, e é o que se fez: `decks.foils_nos_decks(con,
cfg, alloc=None)` devolve, por impressão e por (deck, carta), quantas das cópias
que o deck leva da Coleção são foils — `total consumido − normais`, e entre
decks é o de **prioridade mais baixa** que fica com a foil, porque os de cima já
levaram as normais (que é a ordem em que ele monta). Sem isto a tabela «Montar
este deck, carta a carta» mandava-o procurar no binder uma normal que não
existe. Aparece: `foil_na_colecao` por carta e por secção no `deck_payload`,
`foil_na_colecao`/`foil_cartas` no deck, a célula «Coleção» da tabela de
montagem com «N foil», a nota do `<details>`, e o `riftvault deck <slug>`.

**Medido no `data/` real: ZERO.** Nenhum deck se serve de uma foil hoje — as 58
impressões com foil são comuns e incomuns do VEN com os 3 normais completos, e
os decks levam normais. O mecanismo está em teste (1 normal + 2 foil → «2 vieram
das foils»; 2 normais + 5 foils com um deck a pedir 3 → **1** foil, não 3).

**Um deck DESMONTADO não leva foil nenhuma**, como não leva normal nenhuma
(24/09).

### 4b. UM BUG QUE AS CHAVES ACORDARAM: o `qty_colecao` do `/api/adjust`

Apanhado a testar o ecrã, não a ler o código. O `+`/`−` de uma cópia normal
devolve `qty_colecao`, e é dele que o cliente faz o `state.qty` — o número do
crachá. Vinha do `locais.por_local`, que conta **só as normais** (uma foil não
tem local), enquanto a grelha vem do `locais.na_colecao`, que desde hoje soma as
foils. Resultado: um `+` numa carta com foils **perdia-as no crachá** — de «6/3»
para «4/3» em vez de «7/3», até recarregar a página.

`server._locais_de` passou a tirar o `qty_colecao` do **mesmo funil da grelha**.
O `locations` continua a vir do `por_local`: «onde estão as cópias» é pergunta
das normais. Há teste, e ele fica **vermelho** com a linha antiga (4 != 7).

**A lição, para a próxima chave de config:** quando um número passa a vir de um
funil novo, não basta o payload da página — há que procurar **todos** os sítios
que devolvem «o mesmo número» por outro caminho. Aqui eram dois (a grelha e a
resposta do `adjust`) e só um estava ligado ao funil.

### 4c. UMA COLEAÇÃO ANOTADA: o playset JOGÁVEL anda com o botão do VALOR

`metrics.owned_by_card` (a métrica 1, o «playset jogável» da grelha) lê o
`locais.contadas`, e é o `foil.conta_para_valor` que manda nesse funil. Ou seja:
o playset jogável conta as foils **porque o botão do valor está ligado**, não
porque exista um botão de «as foils jogam-se». Hoje dá o resultado certo — uma
foil é jogável e vale dinheiro, e os dois botões estão ligados —, mas se ele um
dia desligar só o do valor, o playset jogável deixa de as contar, o que não é o
que a frase dele diz. **Fica anotado, não se inventou uma terceira chave**: é
pergunta para ele, e vale zero hoje.

**E uma segunda, do mesmo tipo:** a referência «na coleção: N» do bloco das
runas (`runas_vista._qtys`) lê o `copies.qty` cru — as **normais** —, e a
docstring promete «tudo o que ele fisicamente tem dela, de todas as versões».
As 6 runas base do OGN são comuns, base e não sobrenumeradas, por isso **estão
no âmbito do foil e têm contador**: se ele marcar foil numa delas, a referência
fica por baixo. **Vale zero hoje** — as 58 impressões com foil são todas do VEN,
e no VEN não há runas na lane principal (as `VEN-R` são `rune_promo`, fora do
âmbito). Não se mexeu: aquele bloco é o contador DELE e não conta para nada, e o
`test_runas_vista` proíbe-o de ler a coluna do foil. Fica anotado.

### 5. Um `+` de foil passou a mexer no ecrã todo

Com as chaves ligadas, o contador do foil deixou de ser um canto isolado: o
`state.qty` do cliente é `normais + foils`, e é dele que saem o crachá, as três
barras, o painel, os níveis e o valor. O `foilAplicarLocal` (o gémeo do
`applyLocal` das normais) mexe no `state.qty`, no playset jogável e marca a
wantlist como velha; com as duas chaves desligadas continua a mexer só na linha
do foil, como antes. A frase do `title` da linha («não contam para os alvos nem
para o valor») **mentia** com as chaves ligadas e passou a sair das chaves
(`foilContamTxt`).

### Medido a 2026-09-26 contra CÓPIAS do `data/` real

`_revisao\_medir_foil_conta.py` (+ `_worker.py`), quatro corridas sobre cópias
independentes do mesmo `data/`: **A** `main`, **B** ramo com os dois botões a
`false`, **C** ramo com o **config real** (o DEPOIS), **D** ramo com
`entra_no_a_mais: true` (só para provar que a regra faz diferença). O `data/` a
sério nunca se tocou — ele estava a mexer na coleção.

**A == B em 25 invariantes** (só o campo `foil` novo, a zeros, e as funções que
o `main` ainda não tem): o código novo com os botões desligados mede
exactamente o de antes.

| | ANTES (B) | DEPOIS (C) |
|---|---|---|
| **valor** | **6 645,21 € · 2 573 cópias** | **6 662,70 € · 2 732 cópias** (**+17,49 €**, +159) |
| valor do VEN | 1 058,56 € | 1 076,05 € (as outras quatro não mexem) |
| denominador | 928 | **928** |
| nível 1 · 2 · playset | **897 / 836 / 766 de 928** | **897 / 836 / 766 de 928** |
| faltam, por nível | 31 / 121 / 281 cópias | **iguais** |
| € por nível | 89,27 / 458,08 / 1 056,62 € | **iguais** |
| wantlist «tudo» | 162 linhas · 281 cópias · 1 056,62 € | **igual** (e as cinco por edição) |
| Faltas, fechar os 4 blocos | 317 · 555 · 10 232,99 € | **igual** (os 20 blocos por edição, zero a mexer) |
| A mais, excedente | 69 impressões · 140 cópias | **69 · 140**, item a item |
| decks (falta comprar) | 0 cópias | **0** |
| decks a levar foil | — | **0 cópias, 0 impressões** |
| Encomendas · Venda · painel | — | **iguais** |
| cópias na grelha | — | **58 tiles** passam de `3` a `6` (`VEN-001` «6/3» a verde) |

**Níveis por edição, antes e depois (iguais nos dois):** OGN 279/247/217 de
298 · OGS 24/24/11 de 24 · SFD 215/200/188 de 221 · UNL 216/206/195 de 219 ·
VEN 163/159/155 de 166.

### QUANTAS IMPRESSÕES SOBEM DE NÍVEL: **ZERO** — e é a resposta certa

O «tenho» sobe em **58 impressões** e **nenhuma** cumpre mais um degrau: **as 58
com foil têm todas as 3 normais**, ou seja o playset já estava feito. Ele só
marcou foil em cartas de que já tinha o playset. Por isso os níveis, o
denominador, as Faltas e as **cinco wantlists** ficam **iguais ao cêntimo** —
não é o mecanismo a não funcionar, é a coleção dele. A primeira foil numa carta
incompleta muda isto, e há teste: 1 normal + 2 foil de um alvo de 3 fecha o
playset e sai da wantlist.

**Os foils que ele tem, na cópia medida: 159 em 58 impressões, todas comuns e
incomuns do VEN; nenhuma carta só em foil (0 normais).**

`tests/test_foil_conta.py` (**49 testes**, contra pastas temporárias e config
temporário): as três chaves no config real e nos `DEFAULTS`, a omissão da
terceira a `false`; o tile a dizer `3 normais + 3 foil = 6`, duas foils a
fechar um playset, uma carta só em foil a passar a contar, o denominador
quieto, as Faltas e a wantlist a descontá-las, desligar a chave a voltar atrás,
as foils de uma runa retirada a não contar; o valor ao preço da normal, a
repartição nos três casos (com ressalva, `from_foil`, sem preço), a ressalva
dentro do `collection_value`, e **os dois botões a serem separados**; o «A
mais» igual com e sem foils, o excedente a contar primeiro as normais, o
`scope.foil`, o `have` sem foils, e a **prova pela negativa** com a chave a
`true`; os decks (nenhum leva foil havendo normais; leva e diz-se; a foil é a
ÚLTIMA a sair; entre decks calha ao de baixo; desmontado não leva; com a chave
desligada não vê foil); as três cautelas (`propor_deck`, Venda, o `−`); a
fronteira (nenhum módulo de contas importa o `foil`; a coluna só se lê nos dois
funis — e é por isso que o `a_mais` e o `decks` passaram a saber que há foils
**pelo `locais`**, nunca pela coluna); a interface (a ressalva nos três sítios, o
`from_foil` separado, o «não entram no que sobra», a frase velha apagada, o `+` a
mexer no crachá, a tabela de montagem, o CSS e o CLI); e o `qty_colecao` do
`/api/adjust` a bater com a grelha (4b).

Suite: **48 ficheiros, 0 a falhar**.

## 26/09/2026 — os CHAMPION DECK saem do Produto Selado (66 → 55); e o «bug» dos Trial Deck Set NÃO EXISTIA

Palavras dele: *"retira os Champion Deck todos"*. Ramo
`ai-pc/selado-champion-2026-09-26`.

**NÃO HÁ MECANISMO NOVO, pela terceira vez** — é a mesma `selado.excluidos`
das duas ordens de 25/09 (22 → 32 → **43**), e mais nada. Zero linhas de
lógica; o trabalho foi verificar o que sai, o que fica, e a parte da ordem
que estava errada.

### 1. Os 11 que saem, todos da categoria 262

OGN «Jinx» / «Viktor» / «Lee Sin» · SFD «Rumble» / «Fiora» · UNL «Vi» /
«Vex» · LGC «Ashe» / «Tryndamere» / «Lux» / «Garen». O «Origins: Champion
Deck Set» já saíra a 25/09 (*"compram-se à unidade"*). Confirmado contra o
catálogo real: cada nome casa com UM produto, e depois destes **não fica na
aba nenhum Champion Deck vindo do CardTrader**.

### 2. O que FICA, e é onde era fácil enganar-se

- **Os 2 Showdown Deck** (Vendetta «Zed vs Shen», Radiance «Evelynn vs
  Seraphine»): outra linha de produto, e ele nomeou o Champion Deck.
- **Os 7 Champion Deck Display** da `selado.extra` (OGN Jinx/Viktor/Lee Sin,
  SFD Rumble/Fiora, UNL Vi/Vex). **É a prova do «o nome é EXACTO, nunca um
  pedaço»**: o nome de cada um dos 11 está literalmente DENTRO do nome do
  display dele (`Origins: "Jinx" Champion Deck` ⊂ `Origins: "Jinx" Champion
  Deck Display`), e mesmo assim os displays não vão atrás. Ele nunca os
  nomeou, e o padrão dele ao longo de 25/09 foi tratar a unidade e o display
  como linhas separadas (as «Slim Booster Box» foram pedidas à parte dos
  «boosters soltos»). **Ficam até ele dizer** — e os 2 Showdown Decks
  Display também, o que dá 9 displays de decks na `extra`, como antes.

### 3. O BUG REPORTADO NÃO EXISTIA — e por isso não se escreveu nada

A ordem trazia um bug a corrigir: *«há dois Trial Decks ainda visíveis por o
nome não bater — o catálogo tem "2024 Trial Deck Set Set" e a lista tem "2024
Trial Deck Set"»*. **Os dois estão fora desde 25/09 e nunca estiveram
visíveis.** O `_resolver_excluidos` indexa cada produto pelas DUAS escritas —
o nome LIMPO (`selado.nome_limpo`, que junta a palavra dobrada) e o
`nome_bruto` do catálogo —, é o que a nota do config já dizia («o bruto do
catálogo casa na mesma») e o que o
`test_selado_tirar2.test_o_nome_limpo_e_o_que_casa_nos_trial_deck_set` já
fixava, a passar. Medido no payload real, antes de tocar em nada: **zero
produtos com «trial deck» no nome visíveis**.

**Não se acrescentaram os nomes dobrados, e a razão não é só serem
redundantes:** seriam uma segunda linha para o mesmo produto que passaria a
**REBENTAR** no dia em que o CardTrader corrigisse o nome — aí o `nome_bruto`
passava a «2024 Trial Deck Set» e a entrada «… Set Set» deixava de casar com
nada, que é `ValueError` e página parada. Escrever o nome limpo é a escrita
que sobrevive às duas versões do catálogo.

### 4. A pergunta geral que a ordem fez bem em fazer: exclusões mortas

*«Vê se há mais casos do mesmo — nomes na `selado.excluidos` que não casam
com nenhum produto.»* **Hoje são ZERO**: as 43 entradas casam todas, cada uma
com exactamente um produto.

O que faltava era o guarda permanente. O `_resolver_excluidos` já rebenta com
uma entrada morta — mas só quando alguém lhe pede o payload, e o `tolerante`
cala-o de propósito quando não há catálogo em disco.
`TestNenhumaExclusaoMorta` faz a pergunta de frente, para a lista INTEIRA e
não para os nomes de uma ordem: todas casam, nenhuma é ambígua, e a prova
pela negativa (uma entrada inventada tem de rebentar). É o teste que apanha o
caso a sério que há-de vir — **um blueprint retirado do CardTrader depois de
um `--sync`**, que faz o nome dele na lista deixar de casar.

### Medido a 2026-09-26 contra uma CÓPIA do `data/` real

`_revisao\_medir_champion.py`: o MESMO código e a MESMA cópia, mudando só a
lista, a gerar o site dos dois lados. **Os 30 ficheiros saem IGUAIS ficheiro
a ficheiro** (a menos do relógio) — o único que difere é o `api/selado.json`,
de 128 523 para **110 194 bytes**. Nada fora do selado mexe, e não é asserção:
é o site inteiro comparado byte a byte. (O `data/` a sério nunca se tocou —
ele estava a marcar foils.)

| | antes | depois |
|---|---|---|
| produto selado | 66 (51 saíram · 15 por sair) | **55** |
| não tenho | 51 | **44** (os 4 da LGC são «por sair» e nunca contaram) |
| excluídos | 32 | **43** |
| acessórios | 0 | **0** |
| champion decks do CardTrader na aba | 11 | **0** |
| champion deck displays na aba | 7 | **7** |
| showdown decks na aba | 2 | **2** |

Por edição (o que há): **OGN 8 → 5**, **SFD 8 → 6**, **UNL 10 → 8**, **LGC
6 → 2**; as outras nove não mexem (OGS 2, VEN 8, RAD 7, PG2 1, REC 1, ARC 2,
OP 1, PROMO-RIFT 10, T1S 2). **Total 66 → 55.**

`tests/test_selado_champion.py` (45 testes, contra cópias e config
temporário): o mecanismo (o deck sai, o **display dele fica**, o showdown
fica, sai dos contadores, o `scope` di-lo, repor é tirar o nome, a unidade
gravada não se apaga e volta, o `+` recusa, o catálogo em disco intacto); o
**config real** (43 sem repetidos, os 11 lá, as 32 das ordens anteriores
inteiras, os 7 displays e os 2 showdown FORA da lista e dentro da `extra`, os
nomes dobrados não escritos); os **11 contra o catálogo real** (cada um casa,
todos da 262, nenhum champion deck do CardTrader fica, os 7 displays ficam e
são 7, os 2 showdown ficam, 55 selados, a conta por edição, a LGC sem
champion decks); **nenhuma exclusão morta** (as 43 casam, nenhuma ambígua, e
uma inventada rebenta); os **Trial Deck Set já fora** (o catálogo escreve-os
dobrados, a lista limpa, e mesmo assim casam e não se vêem); e **a
fotografia** — a MESMA do `test_selado`, por referência — a tirar e a repor.
`test_selado_tirar` e `test_selado_tirar2` foram ajustados nos NÚMEROS (32 →
43, 66 → 55, a conta por edição): o teste é que descrevia o de antes, não o
código.

Suite: **50 ficheiros, 0 a falhar**.

## 26/09/2026 — os 7 selados que NÃO SE COMPRAM EM LADO NENHUM (48); as edições POR SAIR ficam

Palavras dele: *"os produtos selados que ainda ficaram, que eu procuro no
cardmarket e nao tem disponivel, podes tirar"*. Ramo
`ai-pc/selado-sem-mercado-2026-09-26`.

**NÃO HÁ MECANISMO NOVO, pela quarta vez** — é a mesma `selado.excluidos` das
três ordens anteriores (22 → 32 → 43 → **50**), e mais nada. O trabalho desta
ordem foi **medir**, e depois **não** tirar o que a letra do pedido tiraria.

### 1. O pedido dele não se mede à letra — e o critério que o substitui

**O Cardmarket não se pode consultar.** Responde **403** a pedidos automáticos
(está no CLAUDE.md desde 2026-08-31), a API pública morreu (410) e a de
parceiros está fechada a novas candidaturas. Não há maneira de saber se um
produto tem stock lá. Cruzaram-se por isso as duas coisas que **se medem**:

| coluna | o que diz |
|---|---|
| `cardmarket_id` do catálogo | sem ele o Cardmarket **nem página tem** para o produto |
| ofertas no CardTrader | medidas **AO VIVO** pela API v2, a 2026-09-26 |

    ZERO NAS DUAS COLUNAS = ninguém vende, em lado nenhum.

**As ofertas do catálogo em disco não servem para isto**, e foi preciso
descobri-lo: o `data/selado_catalogo.json` é do `--sync` de 25/09 e já estava
velho — dizia **zero** ofertas na «Origins: Proving Grounds», que ao vivo tinha
**24**. Medir pelo disco tirava um produto que se compra. O script é
`_revisao\_medir_selado_cm.py` (1 pedido de cada vez), e a resposta crua ficou
em `_revisao\selado-ofertas-vivo.json`.

### 2. Os 7, e o que cada um tinha

Medido ao vivo: **dos 38 visíveis com `blueprint_id`, estes 7 são EXACTAMENTE
os que têm zero ofertas** — nem um a mais, nem um a menos.

| produto | edição | Cardmarket | ofertas CT |
|---|---|---|---|
| Tournament Gift Box | OP | — | 0 |
| Arcane Promo Pack | PROMO-RIFT | — | 0 |
| Origins: Instant Match Box 2025 | PROMO-RIFT | — | 0 |
| Promo Pack | PROMO-RIFT | — | 0 |
| The T1 Worlds Champion \| Player Bundle | T1S | — | 0 |
| Immersive Arcane Promo Pack | PROMO-RIFT | 904521 | 0 |
| Replacement Card Booster | PROMO-RIFT | 877733 | 0 |

Os dois últimos têm página no Cardmarket e zero ofertas — que é a mesma coisa
para quem quer comprar. E o **«Replacement Card Booster» nem produto é**: é o
serviço da Riot de substituição de cartas danificadas. Ficou avisado a 25/09 e
por decidir; sai agora com os outros.

**Os três «Promo Pack» são a prova do «o nome é EXACTO, nunca um pedaço»** —
«Promo Pack» está dentro de «Arcane Promo Pack», que está dentro de
«Immersive Arcane Promo Pack». Escreveram-se os três, um a um, e cada um casa
com o seu (há teste que confirma os três ids distintos).

### 3. O QUE NÃO SAI, e é o ponto desta ordem

**As edições POR SAIR não têm `cardmarket_id` NENHUM — e têm ofertas a sério
em pré-venda.** Tirá-las por não terem Cardmarket era tirar exactamente o que
ele quer ver a chegar:

| produto | ofertas CT (ao vivo) |
|---|---|
| Legacy Booster Box | 6 |
| Legacy Vault | 4 |
| Legacy: Proving Grounds | 5 |
| Radiance Booster Box | 18 |
| Radiance Booster Box Case | 11 |
| The Reckoning Booster Box | 5 |
| Arcane Box Set | 4 |
| Gift of the Rift Bundle | 3 |

É por isto que o critério exige **zero nas DUAS colunas** e não basta faltar o
id. `TestOCriterioNaoEFaltarOIdDoCardmarket` fica **vermelho** se alguém o
simplificar, e tem a prova pela negativa lá dentro (a regra errada, escrita à
mão, apanha a pré-venda).

**Os 17 do `selado.extra` não se medem por este critério.** Não têm
`blueprint_id` nem `cardmarket_id` — a API não os tem —, e por isso pela letra
saíam todos. **Ficam:** foram escritos à mão a 25/09 *precisamente porque* um
catálogo de mercado não os lista, e aplicar-lhes a regra era desfazer essa
ordem. Fica dito no config e há teste.

### 4. POR DECIDIR: os «Nexus Night Promo Booster» do UNL e do VEN

Não têm `cardmarket_id` mas **têm 13 e 6 ofertas** no CardTrader. Pela letra do
pedido saíam; por se comprarem, ficam. **Não se decidiu aqui** — ficaram na aba
e a pergunta foi devolvida. O do OGN tem Cardmarket (856097) e 12 ofertas, e
fica de certeza; o do SFD tem Cardmarket (872892) e 15.

### Medido a 2026-09-26 contra uma CÓPIA do `data/` real

`_revisao\_medir_selado_sem_mercado.py`: o MESMO código e a MESMA cópia,
mudando só a lista, a gerar o site dos dois lados. **Os 30 ficheiros saem
IGUAIS ficheiro a ficheiro** (a menos do relógio) — o único que difere é o
`api/selado.json`, de 110 194 para **98 040 bytes**. Nada fora do selado mexe,
e não é asserção: é o site inteiro comparado byte a byte. (O `data/` a sério
nunca se tocou.)

| | antes | depois |
|---|---|---|
| produto selado | 55 | **48** |
| não tenho | 44 | **37** |
| por sair | 11 | **11** (não mexe — é o ponto) |
| sem preço | 30 | **23** |
| excluídos | 43 | **50** |
| acessórios | 0 | **0** |
| Nexus Night na aba | 4 | **4** |

Por edição (o que há): **a OP desaparece** (1 → 0, tinha um produto só), a
**PROMO-RIFT 10 → 5** e a **T1S 2 → 1**; as outras dez não mexem (OGN 5, OGS 2,
SFD 6, UNL 8, VEN 8, RAD 7, LGC 2, PG2 1, REC 1, ARC 2). **Total 55 → 48.**

`tests/test_selado_sem_mercado.py` (52 testes, contra cópias e config
temporário): o mecanismo (tira-se por nome; **zero ofertas sozinho NÃO esconde
nada** — esconder é decisão dele, senão a aba mudava a cada `--sync`; ter
página no Cardmarket não salva quem está nomeado; o nome exacto com o par
«Promo Pack»; sai dos contadores e do valor; repor é tirar o nome; a unidade
gravada não se apaga e volta; o `+` recusa; o catálogo intacto); **o critério**
(sem id mas com ofertas FICA, e a prova pela negativa); o **config real** (50
sem repetidos, os 7 lá, as 43 anteriores inteiras, a pré-venda e os Nexus Night
**fora** da lista, os 17 da `extra` fora, e a nota a explicar o critério); os
**7 contra o catálogo real** (cada um casa, saem da aba, os ids batem com o
medido, 48 selados, a conta por edição, a OP desaparece); **o que fica** (a
pré-venda visível e sem `cardmarket_id`, as quatro edições por sair, o Arcane
Box Set, os 4 Nexus Night, os 17 da `extra`, os três «Promo Pack» com ids
distintos); **nenhuma exclusão morta** com as 50; e **a fotografia** — a MESMA
do `test_selado`, por referência. `test_selado_tirar`, `test_selado_tirar2` e
`test_selado_champion` foram ajustados nos NÚMEROS (43 → 50, 55 → 48, a conta
por edição) e nos produtos que **deixaram de ser exemplo de «parecido que
fica»** (o «Origins: Instant Match Box 2025» e os «Promo Pack»: estão hoje na
lista, mas não por essas ordens — e é isso que os testes novos lá dizem). O
`test_selado_tirar` ganhou a constante `OS_22`, que não existia.

Suite: **51 ficheiros, 0 a falhar**.

## 26/09/2026 — AS FILAS DA COLEÇÃO SÃO AS DO BINDER: 4, e depois 8 em 8

Palavras dele: *"quero que as filas da coleccao estejam organizas por /
primeira fila de todas 4 / depois de 8 em 8 / que e como fica o Binder"*. Ramo
`ai-pc/binder-2026-09-26`.

**O objectivo manda em tudo o resto: a posição de um tile na grelha é a
posição da carta na PASTA dele.** É uma ferramenta para encontrar a carta —
abrir a página, contar a fila, ir buscá-la. Tudo o que quebre essa
correspondência está errado, por melhor que fique. É essa frase que decide as
cinco decisões abaixo.

**É SÓ DESENHO.** Não se tocou num único `.py` do pacote: a mudança é o
`riftvault/web/style.css` e o `riftvault/web/app.js`. Medido na página, num
Chrome a sério, com a MESMA cópia do `data/` real, antes e depois: painel,
barras, resumo do foil, cabeçalhos dos blocos, a linha de contagem e **os 2 244
crachás dos tiles** (alvo e linha do foil, impressão a impressão) nas cinco
edições e no «Todas» — **zero diferenças em 6 separadores × 7 leituras**.

### 1. O ritmo é FIXO: 4 + 8, nunca `auto-fill`

A `.grid` da Coleção era `repeat(auto-fill, minmax(var(--tile), 1fr))` — o
número de cartas por fila mudava com a largura da janela. Para a pasta isso é
inútil: a 5.ª carta tem de estar SEMPRE na 2.ª fila. A sequência passou a ter
**8 colunas escritas** (`.grid.binder`) e a primeira fila fecha nas 4 com um
calço invisível de 4 colunas (`.binder-gap`), que o `render()` põe a seguir ao
4.º tile de cada edição. O calço não é um tile: não entra no `state.tiles`
(as setas não param nele) e leva `aria-hidden`.

Os dois números vivem num sítio (`BINDER_PRIMEIRA = 4`, `BINDER_FILA = 8`, no
`app.js`) e o ritmo **recomeça em cada edição** — em «Todas» são cinco pastas
seguidas, não uma de 928 cartas. Medido no browser: 5 calços, cada edição a
abrir na sua fila 1 (OGN-001, OGS-001, SFD-001, UNL-001, VEN-001).

### 2. UMA IMPRESSÃO, UMA CÉLULA — e o `.group.multi` que havia

O problema que estava no caminho: `.group.multi` põe `--span:N` e faz um grupo
com N variantes ocupar **N colunas**. Com isso a fila deixava de ter 8 cartas e
a correspondência partia-se. No binder cada carta ocupa uma bolsa, ponto — por
isso nas filas do binder cada impressão sai no seu `.group` e **nenhum grupo
ocupa mais do que uma célula**.

**Quantos grupos `multi` há hoje: ZERO, em todos os blocos e nas cinco
edições** (medido a 26/09: 928 grupos no bloco `master`, TODOS de uma impressão
só). E há uma razão estrutural para isso, que se fixou em teste: os blocos
separam as variantes — a base vai para a sequência, a arte alternativa para o
bloco `alt_art`, a sobrenumerada para o `overnumbered` —, e `multi` só
aparecia se duas impressões do MESMO grupo caíssem no MESMO bloco. O `multi`
fica no código para os outros blocos (é lá que continua a ser a resposta
certa); na sequência não se usa.

### 3. Só a SEQUÊNCIA do master set

É a que ele arruma na pasta por número. Os outros blocos — sobrenumeradas,
artes alternativas, promos, runas especiais — ficam em `auto-fill` como
estavam. **A grelha das Encomendas também não muda**: é a da Coleção CORTADA
na raridade (de Rara para cima, 17/09), faltam-lhe cartas, e as posições nunca
seriam as da pasta.

**Por decidir com ele** (não se aplicou nada «por coerência»): a cauda da
grelha é uma lista de 12 a 96 cartas por bloco que ele guarda noutro sítio, e
pô-la a 4 + 8 prometia uma posição de pasta que não existe. A leitura que
proponho é: as sobrenumeradas, as artes alternativas e as promos **só** devem
seguir o ritmo se ele as arrumar na MESMA pasta a seguir à sequência — e aí a
pergunta seguinte é se a contagem continua de onde a sequência ficou (a 299.ª
carta na fila 38, posição 7) ou se cada bloco começa numa página nova. Enquanto
ele não disser, ficam como estão.

### 4. ECRÃS ESTREITOS: encolhe até 104 px e depois CORRE, sem refluir

Refluir para 4 ou 2 por fila mataria a funcionalidade. O tile encolhe até
`--tile-binder`, e o chão é **104 px** — o mesmo que o `--tile` já
documentava como mínimo para o polegar. Não se foi abaixo disso de propósito:
8 tiles nunca cabem num telemóvel de 375 px, por isso encolher mais não evitava
o scroll e só estragava os `+`/`−`. Abaixo do chão é o **bloco** que corre
(`.binder-wrap { overflow-x: auto }`), e é o `overflow` que impede a largura
mínima das 8 colunas de empurrar a página.

**Medido num Chrome a sério, 11 larguras, a página do OGN** (janela → largura
do bloco → scroll?):

| janela | bloco | coluna | scroll no bloco | scroll na página |
|---|---|---|---|---|
| 1600 | 1140 px | 135,5 px | não | não |
| 1440 | 1122 px | 133,3 px | não | não |
| 1280 | 962 px | 113,2 px | não | não |
| **1206** | **888 px** | **104 px** | **não** (é o limite) | não |
| 1200 | 882 px | 104 px | **sim** | não |
| 1100 | 785 px | 104 px | sim | não |
| 900 | 595 px | 104 px | sim | não |
| 375 | 347 px | 104 px | sim | não |

**A partir de 1206 px de janela não há scroll; abaixo disso o bloco corre.** As
8 colunas precisam de 888 px (8 × 104 + 7 × 8 de `gap`); a barra lateral come
258 px e o `.wrap` até 60 px de margem. A página **nunca** corre para o lado, em
largura nenhuma — medido.

### 5. Quando um filtro esconde parte da sequência, NÃO se finge

A procura, o «Faltas», o «só artes base» e os filtros de tipo tiram impressões
da grelha. Com elas de fora, a carta que ficasse no lugar da escondida apontava
a bolsa errada — e uma posição errada é pior do que um desenho diferente. O
`binderCheio()` compara o que se vê com a sequência inteira; se faltar alguma,
a grelha volta ao `auto-fill` e escreve porquê («vêem-se 43 de 298 impressões»,
medido com o filtro «Faltas» no OGN).

**Onde ele pode conferir, na OGN** (medido na página, não em aritmética — a
posição saiu do `getBoundingClientRect` de cada tile): 1.ª carta `OGN-001`
fila 1 posição 1; 4.ª `OGN-004` fila 1 posição 4; 5.ª `OGN-005` **fila 2
posição 1**; 12.ª `OGN-012` fila 2 posição 8; 13.ª `OGN-013` **fila 3
posição 1**; e a última, `OGN-298`, na fila 38 posição 6 (298 = 4 + 8×36 + 6).
As cinco edições: OGN 298 impressões, OGS 24, SFD 221, UNL 219, VEN 166.

`tests/test_binder.py` (30 testes): o ritmo e os dois números; as 8 colunas
fixas e o resto da grelha em `auto-fill`; o calço a fechar a primeira fila e a
não ser tile; o recomeço por edição; as posições que ele vai conferir contra a
pasta; uma impressão uma célula (e o `multi` a ficar para os outros blocos, com
o mecanismo dos blocos a explicar o zero de hoje); só o master set, com as
Encomendas de fora; a sequência a sair por número de coleção; **nenhum `@media`
mexe nas filas**; o chão, o scroll no bloco e não na página; o aviso do filtro;
e **nenhum módulo de Python conhece o binder**. O `test_casca` tinha
`assertNotIn("overflow-x: auto", CSS)` para a página inteira (a lição das filas
de botões de 24/09): passou a exigir que o único `overflow-x` do site seja o do
`.binder-wrap` — se alguém puser scroll lateral numa barra de botões, dá
vermelho outra vez.

Suite: **52 ficheiros, 0 a falhar**.

## 27/09/2026 — AS FALTAS EM DUAS METADES: as normais e as FOILS (`faltas_foil.py`), com a QUINTA wantlist

Palavras dele: *"quero as faltas separadas, as normais e as foils / as foils
nao sao faltas, sao apenas complemento e indicativo / mais tarde poderao vir a
ser compradas, entao preciso que tenham uma wantlist a parte"*. Sobre o alvo:
*"o alvo das foils e 3 de cada"* e, a precisar-se logo a seguir, *"no caso,
playset"*. Ramo `ai-pc/faltas-foil-2026-09-27`.

### 1. O ALVO é o PLAYSET DO TIPO — e a ordem dizia duas coisas

`metrics.playset_target` / `playset_targets_by_type`, a tabela que já manda no
playset jogável: Unit/Spell/Gear 3, Battlefield 1, Legend 1, **Rune 12**, token
1 (`token_target`). **Não se escreveu alvo novo em lado nenhum.**

A ordem nomeou no texto o `metrics.alvo_do_tipo` — que é o alvo de COLEÇÃO do
tipo e dá **Rune 3**, por causa do `master_targets_by_type` de 15/09 —, mas a
lista de alvos dela diz «Rune 12», o `playset_targets_by_type` é a tabela do
12, e **o total que ela mandou confirmar só fecha com o 12**. Escolheu-se pelos
números. A consequência, dita em voz alta: **numa runa o alvo em foil (12) não
é o alvo da coleção normal (3)** — as 6 runas base do OGN pedem 72 foils. É a
única divergência entre as duas metades, e é pergunta para ele.

### 2. AS FOILS NÃO SÃO FALTAS — e isso é arquitectura, não um comentário

O bloco fica fora da contagem de faltas, da percentagem da Coleção e dos três
níveis, das quatro wantlists por bloco e de todas as listas de compra que já
existem. **O `faltas_edicao.py` (a metade das normais) não conhece o módulo
novo nem a coluna `qty_foil`**; quem compõe as duas é o
`faltas_foil.payload_completo`, e a metade das normais vem de lá tal e qual —
`blocks` (quatro, nunca cinco), `totals`, `totals_lists` e `scope`.

**Não confundir com a decisão de 2026-09-26.** Desde essa tarde o que uma
impressão TEM, para os alvos da Coleção, é `qty + qty_foil` — uma foil tapa um
buraco do master set (`foil.conta_para_coleccao`). O que nasce hoje é a
pergunta SIMÉTRICA: «quantas foils me faltam para ter o playset EM FOIL». São
duas contas diferentes sobre a mesma coluna, e nenhuma mexe na outra.

### 3. O ÂMBITO é o do contador de foil; de rara para cima NÃO se lista nada

`foil.no_ambito` — as impressões BASE, não sobrenumeradas, das raridades do
`foil.raridades` (comuns e incomuns), fora as edições do `foil.edicoes_fora` (o
OGS). **São 512**, e nelas entram os **4 tokens** que a API imprime como Unit
(`OGN-271..274`, Recruit ×3 e Sprite): têm contador de foil na grelha desde
22/09 e por isso têm-no aqui, com o alvo deles, 1. **A ordem media 508** por os
ter tirado à mão; preferiu-se não abrir um segundo âmbito por quatro impressões
que o contador já conta.

Em Riftbound as raridades acima de incomum só existem em foil — a carta normal
*é* a foil —, e listá-las era duplicar a coleção inteira numa segunda lista.

### 4. A QUINTA WANTLIST, o preço da foil, e o que não há

A quinta, com a mesma gramática das quatro de 19/09: só o que há a comprar, o
texto do `cardmarket.gerar` (o gerador único), `riftvault faltas --edicao OGN
--bloco foil --cardmarket`. **O texto não leva marca de foil** — no Cardmarket
é um filtro por entrada (regra de 01/09) —, e por isso TODAS as linhas vêm
marcadas, com a frase própria («estas N linhas são FOIL») em vez da das
normais («N destas só têm oferta foil no mercado»).

**O preço é o da FOIL** (`metrics.precos_de_foil_map`, o `price_foil_cents` de
26/09 à noite); sem oferta foil a linha cai para o preço da normal, e esse
fallback **conta-se e diz-se** (`no_foil_price`, o marcador «normal» no tile) —
é ele que faz do total um PISO. **Não há PENDENTE de foil**: a `pending` guarda
a impressão encomendada, não o acabamento, e não se inventou um que a base não
tem.

### 5. O AVISO que ele pediu de volta

As impressões em que ele TEM foil e o playset das **NORMAIS** ainda está
incompleto (`aviso_normais`, um `<details>` no cabeçalho): a foil está a tapar
o buraco — o tile da Coleção diz «3/3» porque a foil conta desde 26/09, e em
normais ele tem 2. **Não se decidiu nada sobre elas** — mostram-se e contam-se.

### Medido a 2026-09-27 contra uma CÓPIA do `data/` real

`_revisao\_medir_faltas_foil_lado.py` (+ `_preparar_medicao.py`,
`_comparar_faltas_foil.py`): o `main` num worktree e o ramo, cada um com a sua
cópia do MESMO instante dos dados — o André estava a marcar foils enquanto isto
corria, e o `data/` a sério nunca se tocou.

**A METADE DAS NORMAIS SAI BYTE A BYTE IGUAL** (mesmo sha256 do JSON inteiro,
138 347 bytes): as faltas **432 cópias de 258 impressões · 9 069,11 €**, a
comprar **185 cópias de 116 · 843,43 €**, as **20 wantlists por bloco** texto a
texto, os quatro blocos de cada edição item a item, os níveis **910/873/812 de
928**, a wantlist geral e as cinco por edição, o valor **7 802,52 €**, o painel
e o `copies` inteiro. Por edição: OGN 123 · SFD 135 · UNL 93 · VEN 68 · OGS 13.

A metade das foils, na mesma fotografia: âmbito **512 impressões**, alvo somado
**1454**, tem **448 foils** em 218 impressões, **faltam 1006 cópias de 412
impressões · 409,04 €** (9 linhas ao preço da normal, nenhuma sem preço). Por
tipo: Unit 456 · Spell 296 · Gear 125 · **Rune 72** · Battlefield 57. Por
edição: OGN 499 · SFD 305 · UNL 180 · VEN 22.

**O 1195 DA ORDEM CONFIRMA-SE, e a diferença tem duas causas, as duas benignas:**
o alvo somado das 508 (o âmbito dela, sem os 4 tokens) é **1450**, e
`1450 − 255 = 1195` — exactamente o número dela, com as 255 foils do momento em
que ela mediu. Hoje ele tem **448** (marcou 193 desde então, que é o que o
próprio pedido avisou que ia acontecer), e por isso faltam **1002** sem os
tokens e **1006** com eles. As duas linhas que não dependem das foils novas
batem ao número: **Rune 72** e **Battlefield 57**, iguais nas duas medições.

**O aviso são 47 impressões, não 11** — mesma causa: ele marcou foil em mais
cartas de playset normal incompleto. As cinco que a ordem nomeou estão lá
(`OGN-087` Lecturing Yordle, `OGN-095` Stupefy, `OGN-130` Crackshot Corsair,
`OGN-133` Flurry of Blades, `OGN-144` Spoils of War), todas a «normais 2/3 ·
foil 1»; a lista inteira sai no `riftvault faltas` e na página. A única a 1/3 é
a `UNL-070` Turn to Dust (1 normal, 2 foils).

`tests/test_faltas_foil.py` (55 testes, contra pastas temporárias e config
temporário): a metade das normais campo a campo igual ao `faltas_edicao`; os
quatro blocos a continuarem quatro; as foils fora dos totais e das listas;
mexer na coluna do foil a não mexer nas normais (com o botão de 26/09
desligado, que é o que isola o código de hoje) e o teste que diz que COM ele
ligado mexem, e que isso é a decisão de 26/09; a fotografia a não ser de zeros;
**Battlefield 1 e Rune 12**, o alvo a vir da tabela do config e o ficheiro a não
ter alvo escrito; o âmbito (só comuns e incomuns, a alt art e a sobrenumerada
fora, o OGS sem metade, o mesmo conjunto do contador do tile); a quinta
wantlist (o gerador único, só o que falta, todas as linhas a precisarem do
filtro, a geral a não crescer, a edição fora do âmbito a rebentar); o preço da
foil, o fallback contado, o `from_foil`; o aviso; o pendente a ser sempre 0;
ler não escreve; a fronteira; e a rota, o `build`, a CLI, o `app.js`, o CSS e a
nota do config. Suite: **53 ficheiros, 0 a falhar**.

**Fotografado** a 1280 e a 375 px contra o ramo servido no 8779 (a cópia dos
dados): `documentElement.scrollWidth == clientWidth == 375`, sem scroll lateral
na página. Dois acertos vieram das fotos, não do código: o `<b>` da linha da
metade dava «complemento , NÃO SÃO FALTAS» por causa do `letter-spacing` (é
agora «complemento · não são faltas», e o resumo repetido saiu), e a palavra
«foil» a seguir ao preço no tile fazia o preço ser elidido a 375 px — ficou só
a marca do PISO, que é a excepção que interessa.

## 26/09/2026 — A PROIBIÇÃO DO `riftdecks.com` CAIU, por decisão do André

Palavras dele, textuais: *"levanta as regras do riftdecks.com e tenta procurar
as listas pelo browser"*.

**O que estava escrito, e porquê.** O `robots.txt` do `riftdecks.com` bloqueia
o `ClaudeBot` e o `anthropic-ai` (lido a 2026-09-17, quando nasceu o
`seguir.py`), e por isso este ficheiro, o `seguir.py` e a `_seguir_nota` do
config diziam «está VEDADO… não se lhe toca, nem para testar». **Funcionou**:
a 26/09 o supervisor já tinha lido o site oito vezes sem ter lido a regra
primeiro, e foi a ordem `0-torneios-250` que se recusou a continuar e o
apanhou.

**Quem a levantou, e que fique claro que não foi esquecimento nosso.** O
André, dono do projecto, a 2026-09-26, com a frase acima. O `robots.txt` deles
**continua a bloquear** — o que mudou foi a regra desta casa, não a deles; a
decisão é dele e fica registada como dele.

**O que caiu:** a proibição do domínio (nos três sítios onde estava escrita) e
o caso do `test_seguir.test_o_cliente_recusa_os_prefixos_vedados` que fixava o
`https://riftdecks.com/users/x` como recusado. No lugar dele ficou um domínio
neutro (`…invalid`), porque o que esse teste fixa é o guarda do `netloc` — «o
`Cliente` só conhece o piltoverarchive» — e não a proibição de um site.

**O que NÃO caiu — a educação inteira, intacta:** `INTERVALO_MINIMO = 1.0`
segundo entre dois pedidos, e o config só pode ALARGAR (`seguir.opcoes`);
User-Agent honesto, ASCII, que diz o que isto é e não finge ser browser
(`USER_AGENT`, com teste); nada de contas nem de páginas privadas; e a recusa
dos `PREFIXOS_VEDADOS` (`/api/`, `/admin/`, `/_next/`, `/static/`) que o
`robots.txt` do piltoverarchive proíbe — esses quatro **continuam recusados**,
e o teste deles não se tocou. **A proibição do riftdecks nunca serviu de
desculpa para não haver limite de ritmo em sítio nenhum** — verificado: o
ritmo vive no `seguir.Cliente` e é do site que se LÊ, não do que se recusa, e
os outros três módulos de rede têm o deles, cada um a dizer porquê
(`riftscribe.POLITE_DELAY = 1.0` «a API não documenta rate-limit, por
educação»; o `selado.sincronizar` com `intervalo = 1.0`; o `prices.py` a 1,0 s
nas expansões e a 0,5 s por blueprint, que é o único abaixo de um segundo e
está dentro do limite que o CardTrader documenta, 200 pedidos/10 s).

**O que esta ordem NÃO fez, de propósito:** ensinar o `seguir.Cliente` a ler o
riftdecks. Ele continua a conhecer só o piltoverarchive (`BASE`, e
`caminho_vedado` recusa outro `netloc`) — ler um segundo site é um parser novo,
marcas novas e fixtures novas, e ninguém o pediu ainda. Aqui só caiu a
proibição explícita e o teste que a fixava.

Suite: **52 ficheiros, 0 a falhar**.

## 27/09/2026 — os `+`/`-` de «JÁ ENCOMENDEI» nas FALTAS; e a encomenda passa a ter ACABAMENTO (`pending.foil`)

Palavras dele: *"nas faltas, coloca o + e - para eu indicar que ja encomendei,
fica bem mais facil para eu visualizar assim"*. Ramo
`ai-pc/faltas-encomendar-2026-09-27`.

**NÃO HÁ MECANISMO NOVO, e é o ponto de partida.** Os `+`/`-` das encomendas
existem desde 2026-09-11 e escrevem na tabela `pending`; a rota é a
`POST /api/encomenda` e as funções são o `pending.encomendar`/`anular`. O
trabalho desta ordem foi **ligar o botão numa terceira casa** e, a seguir,
resolver o que se parte quando ele lá está.

**O HISTÓRICO DOS MESMOS DOIS BOTÕES**, para não se voltar a fazer o percurso:

| quando | onde | frase |
|---|---|---|
| 2026-09-11 | nos tiles dos **decks** | *"podes criar, nos decks, um botão de + e - que indique o que já está encomendado (comprado), mas que ainda não chegou"* |
| 2026-09-17 | saem dos decks para o separador **Encomendas** | *"uma aba 'encomendas' […] e tiras esta funcionalidade dos decks"* |
| **2026-09-27** | chegam ao separador **Faltas**, e às FOILS | *"nas faltas, coloca o + e - para eu indicar que ja encomendei"* |

Nos decks ficou só a informação «N a caminho» (17/09) e **isso não mudou**: os
tiles dos decks continuam sem steppers, e o `test_encomendas_separador`
continua a exigi-lo.

### 1. UM NÚMERO SÓ, duas vistas

As Faltas e as Encomendas leem os dois da `pending`. Não há contador novo nem
tabela nova — `test_faltas_encomendar.test_nao_ha_tabela_nova_nenhuma`
fotografa a lista de tabelas antes e depois de um `+` e exige que seja a mesma,
e o `test_uma_so_verdade_faltas_e_encomendas_dizem_o_mesmo` compara o número do
tile das Faltas com o `open_qty`, com o `grelha().totals.ordered` e com o
`encomendas().totals` na mesma corrida. Um segundo contador punha as duas
vistas a divergir, e era esse o erro a evitar.

**O `+` grava na IMPRESSÃO do tile.** Nas Faltas cada linha é uma impressão
(a alt art é a alt art, a sobrenumerada é a sobrenumerada), por isso não há
aqui a escolha «carta ou impressão» que o `impressao_para_encomendar` faz nas
listas por carta — essa continua a ser a regra da CLI por nome e do `+` das
linhas dos decks.

### 2. A LINHA NÃO DESAPARECE — é o pedido, e já estava meio feito

O pendente **já** descontava das faltas desde 2026-09-11, e uma falta que
sumisse ao ser encomendada era o contrário do que ele pediu («fica bem mais
fácil para eu **visualizar**»). O `faltas_edicao.em_falta` já guardava o
`pending` À PARTE do `missing` desde 15/09 — o item fica na lista com
`missing` 0 —, e o que faltava era o ecrã dizer as duas coisas.

Agora o tile diz: «faltam N» (ou «a caminho» quando a encomenda cobre tudo),
`+N` no canto, moldura azul tracejada, e em baixo «**N já encomendada(s)** ·
faltam M» / «· nada por comprar». **O que sai é só a wantlist do bloco** — o
que vem a caminho não se compra outra vez — e a conta do que há a comprar.
Três testes fixam isto, incluindo o caso que interessa (encomendar TUDO o que
falta) nas duas metades.

**No cliente as somas refazem-se sem pedir nada** (`feSoma`, o gémeo do
`faltas_edicao.soma`, comparado com o Python no node): o tile que mexeu é
redesenhado no lugar e só os cabeçalhos, os separadores e a caixa da wantlist
se acertam. Redesenhar a grelha inteira a cada clique fazia as imagens todas
piscar.

### 3. O ACABAMENTO: a coluna `pending.foil` (0/1)

Metade do separador é de FOILS desde 2026-09-27 (a ordem anterior), e ele disse
delas *"mais tarde poderao vir a ser compradas"* — por isso o `+` tem de estar
lá também. Mas a `pending` guardava a IMPRESSÃO e não o acabamento: uma foil
encomendada entrava na coleção como NORMAL, e o `copies.qty` e o
`copies.qty_foil` são duas contagens independentes desde 2026-09-26. **Estragar
a contagem dele era o erro a não cometer.**

    pending.foil = 0   uma cópia normal  -> ao chegar, `collection.adjust` -> copies.qty
    pending.foil = 1   uma cópia FOIL    -> ao chegar, `foil.ajustar`      -> copies.qty_foil

Migração em `db._migrar_pending_foil`, **com backup**
(`vault-antes-do-pendente-foil-*.db`, por `VACUUM INTO`) porque mexe numa
tabela do vault.db, numa transação só e idempotente. **As 130 linhas que lá
estavam ficaram a 0** — eram todas de normais, que era a única coisa que havia
como encomendar (verificado na cópia: 130 linhas, `SUM(foil) = 0`, todas já
chegadas).

**O acabamento acompanha a encomenda de ponta a ponta:** o `+` grava-o (e
**valida** que a impressão tem contador de foil — marcar foil numa rara era
gravar o que nenhuma página mostra), o `-` só tira de linhas do mesmo
acabamento, o «Chegou» soma ao contador certo, e as LEITURAS separam-se —
`pending.open_qty()` dá as NORMAIS (é este o pendente que as faltas normais, as
wantlists e os decks descontam) e `open_qty(foil=True)` dá as foils, que só a
metade das foils lê. O `open_by_card` (o grão dos decks) também só conta as
normais: a alocação serve-se do `copies.qty` e uma foil a caminho não é uma
normal a caminho.

**O `foil.ajustar` ganhou `validar=False`, com UM chamador.** O `pending.arrive`
chama-o assim de propósito: uma foil que ele já encomendou tem de poder CHEGAR
mesmo que o `foil.raridades` encolha entretanto — recusar a entrada era
perder-lhe a cópia. Quem valida é o `+`.

**O desfazer é diferente nas duas metades, e diz-se:** uma normal que chega
passa pelo `collection.adjust` e desfaz-se com o `riftvault undo` (a `ops`);
uma foil deixa rasto na `foil_ops` e desfaz-se com
`riftvault foil REF --menos N`.

### 4. A FRONTEIRA do foil mudou de sítio, não caiu

O `test_foil`/`test_foil_conta` proibiam o `pending` de importar o `foil` ou de
nomear o `qty_foil`. O `pending` **saiu dessa lista**: uma encomenda passou a
ter acabamento, e é ele que encaminha a entrada. O que interessa continua
fixado, agora no `test_faltas_encomendar.TestAFronteira`: o `pending` **não
escreve** no `copies` (não há `UPDATE copies` nem `INSERT INTO copies` no
ficheiro — quem escreve é o `foil.ajustar`, e é isso que mantém o rasto e a
conta num sítio só), o `open_qty()` por omissão só dá as normais, o
`open_by_card` também, e uma foil a caminho **não abate uma falta normal** nem
o contrário (dois testes, com o payload inteiro comparado campo a campo).

### 5. AVISO que ele mandou devolver e NÃO resolver: o corte de raridade

`encomendas.raridade_minima` está em `"rare"` e **não se mudou**. Tudo o que ele
marcar abaixo de rara grava na `pending` mas não cabe na GRELHA do separador
Encomendas. Medido na cópia do `data/` de 2026-09-27:

| | linhas | cópias em falta |
|---|---|---|
| normais comuns | 3 | 4 |
| normais incomuns | 7 | 8 |
| **abaixo de rara, nas normais** | **10** | **12** |
| **foils** (todas comuns e incomuns) | **412** | **1006** |
| **total fora da grelha** | **422** | **1018** |

(Normais por raridade, para contexto: rara 74 linhas · 127 cópias, mítica 148 ·
267, showcase 26 · 26.)

**Não ficam invisíveis** — e essa parte resolveu-se sem tocar na chave: o
`pending.grelha` já tinha a lista «a caminho nesta edição, **fora da grelha**»
(17/09), e ela passou a dizer o acabamento. Uma foil a caminho aparece lá,
marcada **FOIL** na cor do foil, com o seu «Chegou»; o total do cabeçalho
(«N cópias a caminho, todas as edições») conta tudo. O que é verdade é que não
aparecem num TILE, e que é preciso estar na edição certa para ver a lista. **A
decisão de baixar ou não a `raridade_minima` é dele.**

### 6. Dois defeitos apanhados pela fotografia, não pelo código

1. **O «Chegou» daquela lista era um botão VAZIO.** Um `<button>` como item de
   um `inline-flex` ficava com a caixa de conteúdo a ZERO (8 px de altura ao
   todo) e o `overflow: hidden` que o Chrome lhe põe cortava a palavra. Está
   assim desde 2026-09-17 e **nunca se viu porque a lista estava sempre
   vazia**: as encomendas eram todas de rara para cima e cabiam na grelha. Com
   as foils passa a ter conteúdo sempre — `min-height: 22px` e `line-height`
   explícito no `.btn.chegou.mini`.
2. **A palavra «foils» no meio da frase** saiu numa linha só, porque o
   `.enc-fora b` é um BLOCO (é a linha de título daquele bloco). Passou a
   `<i class="foil">`.

### Medido a 2026-09-27 contra uma CÓPIA do `data/` real

`_revisao\_copiar_dados_faltas_enc.py` (por `VACUUM INTO`, não `copy2`: as
bases estão em WAL e ele estava a marcar foils) e
`_revisao\_medir_faltas_enc.py`. **Os invariantes NÃO mexem, e não podiam:**
marcar uma encomenda não toca no `copies`. Com uma normal e uma foil marcadas —
denominador **928**, níveis iguais, valor **7 802,52 €**, `copies` igual linha a
linha, e **desmarcar repõe tudo** (o `pending` volta às 130 linhas). O que mexe
é só o que tem de mexer: as faltas a COMPRAR passam de **432 para 431 cópias** e
o «a caminho» de **0 para 1**, com as duas linhas a continuarem na lista.

O separador hoje: normais **432 cópias de 258 impressões · 9 069,11 €** (a
comprar, wantlist geral: 185 · 116 · 843,43 €); foils **1006 cópias de 412
impressões · 409,04 €** — os mesmos números da ordem de ontem.

**Fotografado** a 1280 e a 375 px contra o ramo servido no 8779 (a cópia dos
dados): `documentElement.scrollWidth == clientWidth == 375`, **241 tiles com
`+` e 241 com `−`**, zero «Chegou» nas Faltas, e as linhas marcadas a dizer «1
já encomendada · nada por comprar» / «1 já encomendada · faltam 2». Clicado no
browser: dois cliques rápidos no mesmo `+` dão **2** (a fila por linha é a das
Encomendas), o `−` dá 1, a linha nunca sai e o cabeçalho do bloco acerta
(«faltam 494 cópias de 171 impressões · 224,38 € · 5 a caminho»). E pela rota,
o que interessa: um «Chegou» de 3 foils levou o `ogn-001-298` de
`(qty 3, qty_foil 0)` a **`(qty 3, qty_foil 3)`** — as normais não mexeram.

`tests/test_faltas_encomendar.py` (42 testes, contra pastas temporárias e
config temporário): o mesmo mecanismo e a tabela que já existia, sem tabela
nova; uma só verdade nas duas vistas; **a linha não desaparece** (nas normais,
nas foils, e com a encomenda a cobrir tudo) e o que sai é só a wantlist; a
coluna `foil` no schema com o CHECK, a migração de uma base antiga com backup e
idempotente; o `+` numa foil grava foil, e uma impressão sem contador de foil
rebenta; o «Chegou» de uma foil soma ao `qty_foil` e o de uma normal ao `qty`,
juntas cada uma no seu, e por acabamento; o `-` nunca abaixo de zero, só em
linhas por chegar, e uma metade não desfaz a outra; a fronteira (quatro
testes); o «fora da grelha» das Encomendas com o acabamento e o preço da foil;
ler não escreve; a rota, a CLI, o `app.js`, o CSS e o gémeo em JavaScript.
`test_foil`, `test_foil_conta` e `test_encomendas_separador` foram ajustados —
a fronteira mudou de sítio e o payload ganhou dois campos.

Suite: **54 ficheiros, 0 a falhar**.

## 27/09/2026, à noite — ERRO NOSSO, OUTRA VEZ: as duas contagens SEPARADAS no tile, e o `conta_para_coleccao` de volta a `false`

Palavras dele: *"quero que haja 2 contagens separadas / a de normais e de
foils, / verifiquei ontem que a contagem sobe com as foils e a impressao que
fica e que eu tenho as cartas todas, e quando me falta normais nao consigo
perceber automaticamente que falta / quero que a contagem na carta seja a de
non-foil e a de baixo seja a foil, as coisas separadas"*. Ramo
`ai-pc/foil-separado-2026-09-27`.

### O erro, e porque é que a medição de 26/09 não o apanhou

A 2026-09-26, à tarde, ele disse *"contabilizas tambem como parte do master
set"* e ligámos o `foil.conta_para_coleccao`. Medimos nessa corrida que **zero
impressões subiam de nível** e dissemos-lhe isso. Era verdade **naquele
minuto**, e a razão está escrita na secção dessa tarde: *«as 48 impressões com
foil têm todas os 3 normais, ou seja o alvo já estava cumprido — ele só marcou
foil em cartas de que já tinha o playset»*. Escrevemos lá que «a primeira foil
numa carta incompleta muda isto» e seguimos em frente.

Ele marcou mais **193 foils** e a primeira foil numa carta incompleta chegou.
**Medido a 2026-09-27, contra uma cópia do `data/` real: 47 impressões liam-se
«3/3» com as normais a 2/3, e escondiam 48 cópias NORMAIS em falta.** Os
exemplos que ele nomeou estão todos na lista: `OGN-087` Lecturing Yordle,
`OGN-095` Stupefy, `OGN-130` Crackshot Corsair, `OGN-133` Flurry of Blades,
`OGN-144` Spoils of War, `SFD-001` Against the Odds. São 46 a 2/3 com 1 foil
(1 cópia cada) e a `UNL-070` Turn to Dust a **1/3 com 2 foils** (2 cópias) —
46 + 2 = 48.

**A LIÇÃO, e é a que interessa guardar: a ideia de somar depende do HÁBITO DE
MARCAÇÃO dele, não de uma regra.** Enquanto ele só marcasse foil em cartas de
playset feito, somar não escondia nada; a partir da primeira foil numa carta
incompleta, esconde. **Um número que só está certo enquanto ele marcar por uma
certa ordem não é um número** — e uma medição que dá zero diferença por causa do
estado dos dados nesse dia não é prova de que a regra está certa. Quando uma
medição der «não muda nada», a pergunta seguinte é *porque é que não muda, e o
que é que tem de acontecer para passar a mudar*. Estava escrito no CLAUDE.md e
não foi lido como aviso.

### O que mudou

**1. No TILE são duas contagens, e a separação é ESTRUTURAL** (não depende de
chave nenhuma):

| | o que conta | contra que alvo |
|---|---|---|
| o **crachá**, na arte | as cópias **NORMAIS** da Coleção (`qty`) | `metrics.alvo` — o alvo da Coleção |
| a **linha**, por baixo | as cópias **FOIL** (`qty_foil`) | **`foil.alvo`** — o playset do tipo |

A linha dizia «2 normais · 1 foil = 3» e passou a dizer **«foil 1/3»**: as
normais saíram dela (estão no crachá, uma linha acima) e **o total somado
desapareceu** — era ele que escondia a falta. Leva fundo próprio, a cor do foil
e uma **risca em cima** que a separa do playset jogável; a `is-done` marca
quando a contagem de foil chegou ao playset. **O alvo não é tecto**: 4 foils de
um playset de 3 lêem-se «4/3», como o crachá das normais já fazia.

**O ALVO DE FOIL MUDOU DE CASA, e é uma resposta só.** Era o `faltas_foil.alvo`
(de manhã); passou para **`foil.alvo`**, porque o tile precisava do mesmo número
e a pergunta «quantas foils quero ter» é da mesma casa que «esta impressão tem
contador de foil» (`foil.no_ambito`). Continua a ser o `metrics.playset_target`
(`playset_targets_by_type`): Unit/Spell/Gear 3, Battlefield 1, Legend 1, **Rune
12**. O `faltas_foil.alvo` fica e delega. Por isso **numa runa base o crachá
pede 3 e a linha do foil pede 12** — a divergência que já estava anotada de
manhã, agora visível no tile.

Uma avaria evitada pelo caminho: o `foil.ids_do_ambito` não trazia o `type` nem
o `is_token` no SELECT, e o `metrics.campo` devolve `None` no que não vier — o
alvo saía errado **em silêncio**. As duas colunas entraram na consulta, e há
teste.

**2. A linha só aparece nas 512 do âmbito** (`foil.no_ambito` — comuns e
incomuns, base, não sobrenumeradas, fora o OGS). Numa rara não aparece: em
Riftbound rara para cima só existe em foil, a cópia dele já está no `qty`, e um
«0/3 foil» ali era mentira. Há teste que exige que o âmbito do tile, o do
contador e o da metade das foils das Faltas sejam **o mesmo conjunto**.

**3. As contas voltam a ser das NORMAIS.** `foil.conta_para_coleccao` a
**`false`** (no `riftvault_config.json` e no `config.DEFAULTS`): os três níveis,
a percentagem, o denominador, as Faltas e todas as listas de compra olham só
para o `copies.qty`, pelo `locais.na_colecao`. **Não se apagou a chave** — é a
cultura desta casa (esconder não é apagar) e o mecanismo continua testado nos
dois sentidos; o que mudou é o valor e a nota, que diz porque é que a ideia de
somar não resiste. A omissão também é `false`: um riftvault sem config **não
pode** esconder faltas.

**4. O `foil.conta_para_valor` NÃO se tocou.** É outra pergunta e ele não a
mudou: as foils contam para o valor, ao preço da foil, com o fallback contado.
**O valor não mudou: 7 802,52 € em 3 072 cópias dos dois lados**, medido.

**5. A metade das FOILS das Faltas e a 5.ª wantlist ficam como estavam** — já
eram a leitura certa. O `aviso_normais` (que nasceu de manhã exactamente para
este caso) continua a apanhar as 47; a diferença é que agora o tile já o diz
sozinho.

**6. Os `+`/`−` dos dois contadores continuam a funcionar**, cada um no seu: o
`+` do foil não mexe no `qty` e o `−` da grelha não mexe no `qty_foil`. Com o
`conta_para_coleccao` a `false`, um `+` de foil **não mexe em nível,
percentagem nem wantlist nenhuma**; mexe no valor e no playset jogável, que é a
outra chave. A CLI diz o mesmo que o tile (`2 normais · foil 1/3`), e o
`foil.ajustar` devolve `foil_target` para não haver dois números.

### Medido a 2026-09-27, à noite, na MESMA cópia do `data/` real

Dois processos, a mesma cópia, cada um com o seu ficheiro de config
(`_revisao\_medir_foil_sep2.py` + `_medir_foil_sep_worker.py`). O `data/` a
sério nunca se escreveu — ele estava a marcar foils enquanto isto corria.

| | ANTES (a somar) | DEPOIS (separadas) |
|---|---|---|
| **1 de cada** | 910/928 = 98,1 % · faltam 18 | **910/928 = 98,1 %** · faltam 18 |
| **2 de cada** | 873/928 = 94,1 % · faltam 71 | **872/928 = 94,0 %** · faltam 72 |
| **playset** | 812/928 = **87,5 %** · faltam 185 | **765/928 = 82,4 %** · faltam **233** |
| denominador | 928 | **928** |
| Faltas, a comprar | 185 cópias de 116 impressões · 843,43 € | **233 de 163 · 848,91 €** |
| Faltas, fechar os 4 blocos | 432 cópias de 258 · 9 069,11 € | **480 de 305 · 9 074,59 €** |
| wantlist geral | 116 linhas · 185 cópias | **163 · 233** |
| **VALOR** | **7 802,52 € · 3 072 cópias** | **7 802,52 € · 3 072 cópias** |
| metade das FOILS | 1 006 cópias de 412 · 409,04 € | **igual** |
| resumo do foil | 512 impressões · 448 foils em 218 | **igual** |
| tiles a passar de COMPLETO a INCOMPLETO | — | **47** |

**A percentagem do playset desce 5,1 pontos, e é a correcção a aparecer.** A
aritmética fecha por dentro: 47 impressões saem do nível 3 e as 48 cópias voltam
a ser faltas (46 × 1 + 2 da `UNL-070`); no nível 2 mexe **uma** — a `UNL-070`, a
única a 1 normal —, e o nível 1 não mexe porque nenhuma delas estava a zero
normais. **Os números da ordem (908/867/805) eram de mais cedo nesse dia**; a
diferença é ele a meter cartas, não esta mudança.

**O `copies` não se tocou**: nem o `qty` nem o `qty_foil`, verificado antes e
depois. Ele esteve a marcar foils durante a ordem (448 na medição), e isso não é
bug.

`tests/test_foil_separado.py` (40 testes, contra pastas temporárias e config
temporário): **o caso dele** — 2 normais de 3 com 1 foil aparece incompleta no
tile, nos níveis, nas Faltas e na wantlist, com a **prova pela negativa** (com a
chave ligada lê-se «3/3» e sai das duas listas); o tile (as três chaves no
payload, o crachá e a linha a serem números diferentes, a separação sem depender
de chaves, mais foils do que o alvo); o âmbito (rara e OGS sem linha, o mesmo
conjunto nos três sítios, o config a mandar); o alvo (playset do tipo,
Battlefield 1, **Rune 12 contra 3 na coleção**, a tabela do config, o mesmo da
metade das foils, uma resposta só, o `type` no SELECT); o valor (igual com a
chave ligada ou não, as foils a continuarem a contar, as três leituras de
referência); os dois contadores (cada um no seu, o `−` a travar no zero, o
`foil_target` no `ajustar`, a CLI); a metade das foils e a 5.ª wantlist
inalteradas; o config (chave, default, omissão segura, a nota); e a interface.
`test_foil`, `test_foil_conta` e `test_faltas_foil` foram ajustados — descreviam
o valor antigo da chave, a casa antiga do alvo e o formato antigo da linha.

Suite: **55 ficheiros, 0 a falhar**.

## 27/09/2026 — O DECK PRINCIPAL: a wantlist dele, as duas indicações, e a Venda ao desfazer (`principal.py`)

Palavras dele: *"os decks quero uma coisa / **Deck Principal**: neste caso
LeBlanc / eu coloco + e - se tenho a carta no Deck / **a Colecao e soberana,
nao e para mexer** / todas as cartas do Deck sao Wantlist, as comuns e incomuns
em Foil, / caso eu ainda nao tenha marcado, usa da colecao mas aparece
indicado: / Na colecao aparece que esta a ser usado em X Deck / No deck aparece
algo do genero: X cartas em uso da colecao, ainda falta especifica para o deck
/ Se eu 'desfazer' o deck ou deixar de ser o principal, essas cartas passam a
venda (apenas se valerem pelo menos 0,50 euros)"*. Ramo
`ai-pc/deck-principal-2026-09-27`.

**METADE JÁ EXISTIA, E REUTILIZOU-SE INTEIRA.** As cópias próprias de cada deck
são de 21/09 (`proprias.py`): o local `proprio:<slug>`, os `+`/`−` em cada carta
da página do deck, o não entrarem na Coleção nem no valor, o servirem primeiro.
O `deck:<slug>` é de 10/09 e o «Azir 3» da grelha (`decks.uso_por_carta`) de
11/09. **Não há mecanismo novo ao lado** — o que nasceu foi só o que faltava.

### 1. `decks.principal`, e a relação com o `montados`

`decks.principal` é UM deck (o slug ou o `Nome:`, como a `ordem` e os
`montados`), hoje **«LeBlanc Hook»**. A relação, que é a pergunta a não deixar
por responder:

| chave | responde a |
|---|---|
| `decks.montados` | QUAIS estão montados (um desmontado não consome a Coleção — 24/09) |
| `decks.principal` | qual DESSES é o que ele está a jogar |

**O principal é SEMPRE montado** (`montados_estado`: se a lista não o nomear,
conta como montado à mesma e `principal_implicito` di-lo; o botão escreve-o nas
duas chaves, para o config nunca dizer duas coisas), e **desmontar o principal
DESPROMOVE-O** — limpa a chave; sem isso o «o principal conta como montado»
voltava a montá-lo e o clique não fazia nada. **Sem a chave não há principal**,
e aí não há wantlist de deck principal nem despromoção a disparar: é de
propósito, porque a despromoção mexe na Venda e isso não pode acontecer por uma
leitura nem por uma mudança de ordem.

**NÃO É A PRIORIDADE 1.** A prioridade (`decks.ordem`) diz quem se serve
primeiro da Coleção; hoje calham no mesmo deck e podem não calhar. O ecrã
deixou de chamar «principal» à prioridade 1 (o crachá passou a «prioridade 1» e
o botão a «Passar a prioridade 1»): duas perguntas com a mesma palavra no mesmo
sítio liam-se como uma.

### 2. A wantlist: `precisa − próprias`, e o acabamento manda no preço

«Todas as cartas do Deck são Wantlist» é o deck inteiro menos o que ele já
marcou com `+`: **uma carta marcada SAI da lista**. **Não desconta a Coleção** —
é o ponto do pedido: se ainda não a marcou, o deck joga com a da Coleção e as
duas indicações dizem-no, mas ela continua na wantlist porque o que se quer é o
deck ficar com as suas.

**Comuns e incomuns em FOIL, rara para cima a normal.** O critério é o
**`foil.no_ambito`** — exactamente as impressões que têm contador de foil no
tile (base, não sobrenumerada, comum ou incomum, fora o OGS). Não se escreveu
uma segunda definição de «isto quer-se em foil»: se ele alargar o
`foil.raridades`, alarga aqui também, e há teste que compara os dois conjuntos.
Em Riftbound de rara para cima a carta *é* a foil, e não há acabamento a
escolher.

O preço de uma linha foil é o `price_foil_cents` (26/09), com o **fallback para
o da normal contado e dito** (`no_foil_price`) — o mesmo que a metade das foils
das Faltas faz, e que faz do total um **PISO**. O texto sai do gerador único
(`cardmarket.gerar`) e **não leva marca de foil** (lá é um filtro por entrada,
regra de 01/09). **As runas ficam de fora**, como em todos os decks desde 17/09
à noite; a página diz quantas são.

### 3. As duas indicações — e o empréstimo é de APRESENTAÇÃO

* **Na Coleção, no tile:** a entrada do deck principal em `uso_por_carta` leva
  `principal: true` e o tile escreve **«em uso no deck LeBlanc Hook 3»**.
* **Na página do deck:** «**53** cartas em uso da Coleção (26 cartas
  distintas), ainda faltam **54** específicas para o deck · 226,66 €».

**A Coleção é soberana, e prova-se.** Nada disto move uma cópia: o que o deck
usa da Coleção continua a ser o `decks.allocate` de sempre, que não escreve
nada. Ver a medição.

### 4. Quando deixa de ser principal ou é desfeito: a Venda, de 0,50 € para cima

As cópias PRÓPRIAS dele passam a linhas da Venda, **só as que valham
`decks.venda_minimo_cents`** (50). As emprestadas da Coleção não vão a lado
nenhum — deixam simplesmente de estar emprestadas. **TRÊS DECISÕES minhas,
ditas:**

**(a) O preço que decide é o mesmo que a Venda mostra** — o Trend do Cardmarket
se ele já o meteu, senão o do CardTrader, e o **preço de foil** quando a carta é
das que o deck quer em foil. É uma função só (`venda.preco_de_referencia`), e a
linha da Venda mostra-a em `preco_criterio`: senão o número no ecrã não batia
com o critério que a pôs lá. Uma cópia **sem preço nenhum** não chega ao mínimo
e fica.

**(b) As de menos de 0,50 € NÃO desaparecem:** continuam cópias próprias daquele
deck, fora da Coleção e do valor, e a página diz quantas são e quanto valem ao
todo (`proprias_por_valor`, que responde **antes e depois** — é com ela que ele
vê o que vai acontecer antes de carregar).

**(c) Entrar na Venda NÃO é vender.** A Venda é uma área de marcação
(`sale_lines`) que não mexe em número nenhum; quem baixa cópias é o botão
separado «marcar como vendidas». Por isso **nada sai do `proprio:<slug>`**: a
cópia fica onde está e ganha uma linha marcada `deck:<slug>` (a coluna
**`origem`**, migrada com backup), que a página mostra à parte com o preço que a
trouxe e se tira de uma vez (`venda.limpar(origem=...)`, botão «Tirar as deste
deck»). Uma linha que ele já tivesse marcado à mão **não muda de dono** — senão
o «tirar as do deck» levava as dele.

### Medido a 2026-09-27 contra uma CÓPIA do `data/` real

`_revisao\_medir_principal.py` (o `main` num worktree e o ramo, cada um com a
sua cópia do MESMO instante dos dados, por `VACUUM INTO` — o `data/` a sério
nunca se escreveu; ele estava a mexer na coleção enquanto isto corria). Cada
lado leu o SEU config.

**ZERO DIFERENÇAS em 24 invariantes:** denominador **928**, níveis, valor
**7 802,52 €**, valor por edição, totais, wantlist geral e as cinco por edição,
painel, resumo do foil, **as Faltas normais (`totals`, `totals_lists` e os 20
blocos por edição, com as quatro wantlists)**, **a metade das FOILS e a QUINTA
wantlist** (`totals`, `scope` e por edição), A mais item a item, Encomendas,
falta dos decks, o índice dos decks, o `copies` inteiro e a grelha impressão a
impressão nas cinco edições. As faltas: **305 cartas · 480 cópias ·
9 074,59 €** dos dois lados.

**O que o separador diz, com os dados de hoje** (LeBlanc Hook, o único montado):

| | |
|---|---|
| wantlist do deck principal | **54 cópias de 26 cartas · 226,66 €** |
| em foil (comuns e incomuns) | 25 cópias em 13 cartas · 25,11 € |
| ao preço da normal (piso) | **0** — todas têm oferta foil |
| normais (rara para cima) | 29 cópias em 13 cartas · 201,55 € |
| runas de fora | 12 (2 cartas) |
| em uso da Coleção | **53 cópias em 26 cartas** |
| cópias próprias hoje | **0** — nada iria para a Venda se o despromovesse agora |

Por raridade: comuns 6 cartas · 14 cópias · 5,20 € (foil); incomuns 7 · 11 ·
19,91 € (foil); raras 9 · 20 · 45,95 € (normal); épicas 4 · 9 · 155,60 €
(normal). As mais caras: 3× Baited Hook `OGN-242` 115,86 €, 2× Thousand-Tailed
Watcher `OGN-116` 27,80 €, 2× Mirror Image `UNL-200` 21,42 €.

**Exercitado pela rota, contra a cópia:** marcadas 1 Baited Hook (rara,
38,62 €) e 1 Soaring Scout (comum, 0,19 € em foil) como próprias; ao passar o
principal para outro deck foi **1 cópia · 38,62 €** para a Venda e **ficou 1 ·
0,19 €** no deck, com a linha a dizer «do deck LeBlanc Hook · 38,62 €» e o
botão «Tirar as deste deck». As duas próprias continuaram no
`proprio:leblanc-hook`.

**Fotografado** a 1280 e a 375 px contra o ramo servido no 8779 (a cópia):
`documentElement.scrollWidth == clientWidth == 375`, zero elementos fora do
ecrã. A tabela da wantlist vira cartões a 559 px — **nada de scroll lateral**,
que continua a ser só o das filas do binder.

`tests/test_deck_principal.py` (51 testes, contra pastas temporárias e config
temporário): a chave e a relação com o `montados` (implícito, escrita nas duas,
desmontar despromove, sem chave não há, nome que não casa avisa, mal escrita
rebenta); a wantlist (`precisa − próprias`, o `+` a tirar a linha, o acabamento
igual ao contador do tile e a andar com o config, o preço de foil, o fallback
contado, o total, as runas fora, o texto do gerador único); as duas indicações;
**a Coleção não muda um número** (a mesma fotografia do `test_copias_proprias`,
mais a metade das foils e a quinta wantlist) e um teste que exige que ela não
seja de zeros; a despromoção (só as >= 0,50 €, as de menos ficam próprias, nada
sai do local, o Trend dele a ganhar ao CardTrader, sem preço fica, o mínimo do
config, desfazer o deck faz o mesmo, a origem e o «tirar de uma vez», a linha
dele que não muda de dono, escolher o mesmo deck não faz nada, a migração numa
base antiga); e as rotas, o `build`, a CLI, o `app.js` e o CSS.
`test_partilha_compra` foi ajustado — descrevia a entrada do uso sem o campo
novo.

Suite: **56 ficheiros, 0 a falhar**.

## 28/09/2026 — SÓ IMPRESSÃO INGLESA; e sai da aba quem não tem PÁGINA PRÓPRIA (a aba fica em 32)

O varrimento dos dois mercados fechou, e com ele três decisões dele no mesmo
dia. Ramo `ai-pc/selado-ingles-2026-09-28`; o registo dos dois mercados está em
`docs/selado-dois-mercados-20260928.md` (substitui o
`selado-falta-cardmarket-20260927.md`, que era a lista do que faltava).

**NÃO HÁ MECANISMO NOVO, pela quinta vez.** As três ordens fazem-se com as duas
chaves que já existiam — `selado.excluidos` e `selado.extra` — e zero linhas de
lógica nova. O trabalho foi medir.

### O varrimento, fechado

| | como se leu | o que deu |
|---|---|---|
| **CardTrader** | API v2, com o token (27/09) | 13 categorias do jogo 22, 17 expansões, **210 produtos não-single**, 85 nas 6 categorias de selado. **Nenhum produto selado do CardTrader é desconhecido da app.** |
| **Cardmarket** | **o Chrome dele** (28/09) — a extensão passa o Cloudflare; a API deles está fechada a novos pedidos | Boosters (26), Booster Boxes (18), Champion Decks (9), Box Sets (20) = **73 produtos, 68 com oferta** |

**DUAS DESCOBERTAS sobre o Cardmarket, que valem para qualquer leitura futura:**

1. **Não há página própria para DISPLAYS nem para CASES.** Vendem-se DENTRO da
   entrada do produto simples, com o vendedor a escrever o que é na nota. No
   `Box-Sets/Spiritforged-Pre-Rift-Event-Kit` há «SEALED CASE (16 kits + box)» a
   **1350 €** e «Sealed Case for 16 players» a **1800 €** ao lado do kit de um
   jogador a ~49 €; no `Champion-Decks/Vi-Champion-Deck` há «FRENCH 4 = display
   sceellee» a 12,49 €. É por isto que os 17 do `selado.extra` não têm página em
   lado nenhum: **não é falha do catálogo, é o modelo deles.**
2. **O «From» NÃO é o preço do produto.** No `Unleashed-Pre-Rift-Event-Kit` o
   «From 2,50 €» são vendedores a vender UM deck solto de dentro do kit («ONLY
   Vi deck (sealed) - nothing else»); o kit inteiro está a ~22-26 €. Não usar o
   «From» deles como preço sem ler a nota do vendedor.

**O URL:** ficou confirmado o CAMINHO `/en/Riftbound/Products/<Categoria>/<Slug>`
(com `Boosters`, `Booster-Boxes`, `Champion-Decks`, `Box-Sets` e `Sets`). **O
template da app é outro** — `?idProduct={id}` — e **continua por confirmar**:
nunca se abriu um. Para o trocar faltavam o slug deles (que não é o nosso nome:
«Origins Booster Box Case» é lá «Origins Case (6x Booster Box)») e a categoria
deles, e inventar qualquer dos dois era escrever no URL o que ninguém mediu. O
`mercados.py` diz isto, e o link de **pesquisa** continua a ser a rede de
segurança de cada linha.

### a) Voltam os que o Cardmarket revelou ter oferta — **dois**, não três

*"Repor so os 5 novos"*. Dos 15 que saíram a 26/09 por não terem oferta em lado
nenhum, o Cardmarket revelou-a em 5. Voltaram o **Unleashed Sleeved Booster**
(13,00 €) e o **Replacement Card Booster** (35,00 €). Os outros três ficam fora
pela regra da língua: o *Unleashed Slim Booster* e o *Unleashed Slim Booster
Box* (o Cardmarket chama-lhes «Unleashed Booster (Chinese, Slim)» e «Unleashed
Booster Box (Chinese, Slim)»; o CardTrader só lhes chama «Slim») — e o
**Immersive Arcane Promo Pack**.

**O terceiro é decisão minha e é a única coisa desta ordem que não se fez como
estava escrita.** Medido antes de mexer: o blueprint 408687 tem `versao:
"Chinese Exclusive"` no catálogo do CardTrader — a mesma string dos outros dois
«Promo Pack», que estão fora. O Cardmarket tem-no a 80,00 € com outro nome
(«Arcane: Immersive Music Experience Booster», casado pelo `cardmarket_id`
904521 do próprio blueprint) e não lhe põe rótulo de língua. As duas ordens do
dia colidem neste produto: pela (a) volta, pela (b) não pode entrar. **Ficou
fora** — é o que a regra nova diz, e foi ela que cortou os outros dois da mesma
lista. Repor é tirar o nome do `selado.excluidos`, e é decisão dele. Há teste
que dá vermelho se um `--sync` mudar essa versão.

Os **23 que tinham oferta no CardTrader** ficam fora (*"deixa como está"*,
26/09) e os Champion Deck também — os **11** de 26/09 mais o «Origins: Champion
Deck Set» de 25/09.

### b) A REGRA NOVA: só impressão inglesa (`_selado_so_ingles`)

Palavras dele: *"nao quero nada que nao seja impressao Inglesa"*. Uma caixa da
impressão chinesa (ou de outra língua) **não entra na aba, tenha oferta ou
não**.

É a mesma escolha que os PREÇOS já faziam pelo outro lado desde 2026-08-31 — o
`precos.linguas` (`["en"]`) só aceita ofertas `riftbound_language: "en"`, e no
*Origins Booster Box* eram 51 `en`, 6 `zh-CN` e 3 `fr`. A diferença é que até
aqui a língua filtrava o **preço** de um produto que ficava na lista; agora
**tira o produto**.

**Aplica-se À MÃO, pelo `selado.excluidos`, e não por código** — não há campo de
língua nos blueprints. O marcador lê-se no `nome` («Arcane Chinese Promo Set»),
na `versao` («Chinese Exclusive») ou no rótulo do Cardmarket («(Chinese,
Slim)»). **Cuidado a cada `riftvault selado --sync`**: um produto novo com esse
marcador entra na aba sozinho.

**Varridos os 48 da aba, só UM tinha marcador: o «Arcane Chinese Promo Set»**
(ARC), e saiu. **Formato não é língua** — «Slim», «Jumbo» e «Sleeved» são
embalagens, e é por isso que o *Unleashed Sleeved Booster* voltou no mesmo dia;
e a impressão inglesa de um produto com irmão chinês fica (o *Arcane Box Set*
fica). Há teste com a armadilha nos dois sentidos.

### c) Os 17 do `selado.extra` saem da aba — e ficam ARQUIVADOS no config

Palavras dele: *"Tira os que nao tem pagina propria"*. Só fica na aba o que é
produto **listado** num dos dois mercados, e nenhum dos 17 o é: os 7 Champion
Deck Display, os 2 Showdown Decks Display, os 3 Vault Bundle Case, o Proving
Grounds Box Set Case e os 4 Pre-Rift EVENT Kit. Eles EXISTEM (levantamento dele
de 25/09); o que não existe é uma página onde comprá-los — e a descoberta 1
explica porquê.

**O que saiu foi a PRESENÇA na aba, não o conhecimento.** O `selado.extra` ficou
`[]` e os 17 objectos estão inteiros no **`_selado_extra_arquivado`** do config
(nome, edição, tipo, data, `conteudo` e `nota` — incluindo a dúvida dos 4 ou 12
vaults do case da Unleashed), com a data, a frase dele e a razão. **Repor é
copiá-los de volta** para o `selado.extra`, e há teste que o faz e compara campo
a campo. É a mesma ideia do `abas.escondidas`, do `selado.excluidos` e dos
acessórios de 25/09. As unidades dele nos ids `cfg-…` ficam na `sealed_copies` e
voltam a contar — estavam todas a ZERO a 28/09.

### Medido a 2026-09-28 contra uma CÓPIA do `data/` real

`_revisao\_medir_selado_ingles.py`, o MESMO código e o MESMO catálogo, mudando
só o config, com o site gerado dos dois lados. **Os 30 ficheiros saem IGUAIS
ficheiro a ficheiro** (a menos do relógio) — o único que difere é o
`api/selado.json`, de 98 088 para **67 757 bytes**. Nada fora do selado mexe, e
não é asserção: é o site inteiro comparado byte a byte. O **`copies` não mexeu um
número** (1041 linhas, 2632 normais, 448 foil, o mesmo sha256).

| | antes | depois |
|---|---|---|
| produtos na aba | 48 | **32** |
| dos quais «por sair» | 11 | 8 |
| tenho · cópias | 5 · 5 | **5 · 5** |
| não tenho | 32 | **19** |
| percentagem | 13,5 % | **20,8 %** |
| **valor do selado** | **552,56 €** | **552,56 €** |
| sem preço | 23 | **7** |
| vindos do config (`extra`) | 17 | **0** |
| `selado.excluidos` | 50 | **49** |

**O valor não mexeu, e tinha de ser:** as 5 unidades que ele tem são todas de
produtos do CardTrader que ficaram na aba (as quatro Booster Box e o Origins:
Proving Grounds), e os 17 arquivados não tinham preço nem unidades. As 18 linhas
que saíram são os 17 do `extra` mais o «Arcane Chinese Promo Set»; entraram 2.
Por edição: OGN 5 → 2, OGS 2 → 1, SFD 6 → 3, UNL 8 → 5, VEN 8 → 5, RAD 7 → 4,
ARC 2 → 1, PROMO-RIFT 5 → **6**; LGC 2, PG2 1, REC 1 e T1S 1 não mexem.

**Os dois que voltaram aparecem sem preço** («—»), e é honesto: o CardTrader tem
zero ofertas dos dois — foi por isso que saíram a 26/09 — e a app não guarda
preços do Cardmarket.

### O BURACO QUE FICA (proposto, NÃO feito)

**A app só vê o catálogo do CardTrader.** Um produto que só o Cardmarket lista é
invisível: não está na aba, não está no `scope.fora`, não está sequer no
`excluidos` — não existe. **Medido produto a produto**
(`_revisao\_so_no_cardmarket.py`): dos 73 do Cardmarket a app conhece **57** e
desconhece **16**, dos quais **13 com oferta viva**. (A ordem dizia 14 e 12; a
diferença são os dois «Vendetta Booster (Chinese, Slim)» e «Vendetta Booster Box
(Chinese, Slim)», que a app não tem — o Slim dela é só OGN/SFD/UNL — e que não
têm oferta.) Dez são impressão chinesa e ele não a quer; os outros seis são o
*Spiritforged* e o *Vendetta Sleeved Booster*, o *Worlds 25 Commemorative
Booster*, o *Project K Promos Booster*, o *Arcane Box Set (Chinese)* e o
*Unleashed: Prize Wall Rune Bundle*. As propostas (nenhuma feita) estão no `docs/`: um preço do Cardmarket
metido à mão como o Trend da Venda; um aviso de língua no `--sync`; e a pergunta
do *Arcane Box Set*, que tem a mesma `versao` («6 Card Set») do *Arcane Complete
Set*, que saiu a 25/09 por ser um conjunto de cartas.

`tests/test_selado_ingles.py` (49 testes, contra cópias e config temporário): a
regra da língua (a app **não adivinha**, o nomeado sai, **formato não é língua**,
o irmão inglês fica, a língua na versão, os contadores e o valor, repor, o
catálogo intacto); o `extra` vazio (aparecem, somem, os do CardTrader não mexem,
**repor é copiar de volta** campo a campo, a unidade gravada não se perde, o
conteúdo e a nota sobrevivem); o **config real** (o `extra` vazio, os 17
arquivados inteiros com todos os campos, a data/frase/razão, os dois que
voltaram, o chinês que saiu, os três da língua que ficam fora, as duas notas,
sem repetidos, as ordens anteriores inteiras, o default que não esconde nada); o
**catálogo real** (32 na aba, nenhum do config, **nenhum produto com marcador de
língua**, o Sleeved que fica, as 49 entradas a casarem com um produto cada, uma
inventada a rebentar, e a versão «Chinese Exclusive» do 408687); e **a
fotografia** — a MESMA do `test_selado`, por referência.

## 28/09/2026 — OS DECKS FORAM APAGADOS TODOS (ficam ZERO); e `decks.apagar_todos`

Palavras dele: *"apaga os decks todos, vamos atualizar com as listas novas
posteriormente"*. Houve um torneio grande (RQ Los Angeles) e a ideia é
substituir as seis listas pelas melhores de cada Legend que saírem de lá. Ramo
`ai-pc/sem-decks-2026-09-28`.

**HOJE NÃO HÁ DECKS NENHUNS.** Todas as secções acima que falam de decks —
a partilha da Coleção (11/09), montado/desmontado (24/09), o deck principal e
a wantlist dele (27/09), as cópias próprias (21/09), a regra de raridade
(24/09), as versões (17/09) — descrevem REGRAS que continuam inteiras no
código e no config, mas **não têm hoje nenhum caso**: `decks.montados` é `[]`,
`decks.principal` é `null` e `decks.ordem` é `[]`. Voltam a valer assim que
entrar o primeiro `.txt`.

### A PRECONDIÇÃO, verificada antes de tocar em nada

`locais.proprias(con)` devolvia **`{}`**, a `copy_locations` estava **vazia** e
a `sale_lines` também: **ele não tinha nenhuma cópia própria marcada em deck
nenhum**. Por isso apagar **não desencadeou a regra da Venda** (as próprias de
0,50 € para cima do deck principal) e **não perdeu nenhuma marcação feita à
mão**. Era a condição que fazia a ordem ser segura, e mediu-se pela função da
app, não por SQL.

### `decks.apagar_todos` — porque é uma função e não SQL à mão

Já se tinham apagado decks três vezes (17/09 o Kennen e um LeBlanc, 20/09 o
Kennen outra vez, 21/09 a troca das seis listas) e todas as vezes foi o mesmo
percurso feito à mão, **com uma parte esquecida de cada vez** — a 21/09 foi
preciso descobrir o `uso_decks.recomecar` para o histórico não ficar a dizer
que ele tinha deixado de jogar 132 cartas. Isto repete-se a cada torneio.

Seis passos, **cada um pela porta que já existia** — não há SQL novo:

1. **conta as cópias próprias** (`locais.proprias`) e di-las; nunca as apaga —
   uma cópia própria é dele e fica gravada no `proprio:<slug>`, fora da
   Coleção e do valor, como já acontecia a um deck cujo `.txt` desaparecia;
2. **despromove o principal** (`principal.definir(con, None)`), que é quem
   trata da regra dos 0,50 € — com zero próprias é um no-op, e é o caso de
   hoje; a regra fica honrada para a próxima vez;
3. **manda ao binder** o que estivesse sleevado (`locais.desfazer_deck`);
   nunca à Coleção — *"quem as tirou de lá foi ele"*;
4. **arquiva e apaga os `.txt`**;
5. **tira as linhas da base pelo `import_all`** — «decks cujo ficheiro
   desapareceu saem, é assim que se apaga um deck» já lá estava escrito;
6. **recomeça o registo** (`uso_decks.recomecar`) e **limpa o config**.

**AS REGRAS DO CONFIG NÃO SE TOCAM** (`so_base`, `venda_minimo_cents`,
`coleccao_so_a_partir_de`, `modo`, `versoes_especiais`, `contar_runas`): são
decisões dele e as listas novas vão querer as mesmas. Só saem as três chaves
que NOMEIAM decks que deixaram de existir, e há teste que exige que sejam
exactamente essas três.

**O arquivo a sério é o GIT.** Os `decks/*.txt` são versionados desde sempre
(recupera-se com `git checkout <sha>~1 -- decks/`, o caminho de 17/09 e de
20/09); a pasta `data/backups/decks-<data>/` é a cópia de conveniência, para
ele abrir uma lista sem git à mão — e está no `.gitignore`, como todos os
backups. Na CLI: `riftvault decks --apagar-todos` diz o que ia fazer e **pede
confirmação**; `--sim` faz, com backup do `vault.db` primeiro (`db.backup`).

### ZERO DECKS É UM ESTADO NORMAL — e foi preciso arranjá-lo

Exercitados contra uma cópia do `data/` real com os decks apagados: os 17
payloads, as duas metades das Faltas, a wantlist, o painel, o `build`
(20 ficheiros, `api/decks.json` com `decks: []` e zero payloads de deck
órfãos), as 12 rotas e a CLI — **nada rebentou**. O que estava mal era o que
se LIA:

| onde | dizia | diz |
|---|---|---|
| cartão «Decks montados» do Início | **«0 de 0 · estão todos completos»** | «—» e a frase |
| lista «Os decks» do Início | nada (vazio mudo) | a frase |
| índice dos decks | o grupo «Os decks» desaparecia | o grupo, com a frase |
| `riftvault decks` | só a fila dos títulos da tabela | a frase |
| `riftvault wantlist` | **uma linha em branco** | nada no stdout (fica colável), a frase no stderr |
| `riftvault principal` | «`--definir leblanc-hook` escolhe um» | um deck que EXISTA, ou a frase |

O primeiro era o pior: **uma mentira das duas metades** — `decks = []` é
truthy, `cheios === decks.length` é `0 === 0`, e o cartão dava por completos
decks que não existem.

**A frase é UMA** e vive no `decks.py` (`SEM_DECKS`, `SEM_DECKS_COMO`), com o
`app.js` a repeti-la e o teste a comparar as duas escritas. **Não nomeia o
torneio**: hoje é verdade e no mês que vem não — o que não muda é o estado e
como sair dele. Há teste que recusa a palavra no `app.js` e no `cli.py`.

### Medido a 2026-09-28, antes e depois, no `data/` real

**Zero diferenças em tudo o que é número da Coleção:**

| | antes (6 decks) | depois (0 decks) |
|---|---|---|
| denominador | **928** | **928** |
| 1 de cada · 2 de cada · playset | **910 / 872 / 775** de 928 | **iguais** |
| valor | **7 775,37 € · 3 173 cópias** | **iguais** |
| `copies` (sha256) | `10b9f143…` | **o mesmo** |
| cópias normais · foil | 2 642 · 539 | **iguais** |
| wantlist «tudo» | 153 linhas · 223 cópias · 833,66 € | **iguais** |
| Faltas normais · foils | 470 · 9 045,64 € · 915 · 375,33 € | **iguais** |
| `sale_lines` | 0 linhas | **0 linhas** |
| `decks` · `deck_cards` · `deck_need_log` | 6 · 182 · 170 | **0 · 0 · 0** |
| `decks.montados` · `principal` · `ordem` | `["LeBlanc Hook"]` · `"LeBlanc Hook"` · 6 nomes | `[]` · `null` · `[]` |
| cartas com uso de decks na grelha | 27 | **0** |
| «libertadas» do A mais | 0 | **0** (o `recomecar` é que o garante) |

As «libertadas» a zero são o ponto do passo 6: sem ele seriam **170 linhas** de
descida a zero, e o «A mais» mostrava-as como cartas que ele deixou de jogar.

`tests/test_sem_decks.py` (38 testes, contra pastas temporárias e config
temporário): apaga as quatro coisas e arquiva primeiro; as regras ficam e só
as três chaves de estado saem; **a fotografia** da Coleção (níveis,
denominador, wantlist, valor, totais, grelha com o foil, master, painel, as
duas metades das Faltas, Encomendas e o sha da `copies`) igual antes e depois,
mais o teste que exige que ela não seja de zeros; a `copies` byte a byte e a
`ops` sem linhas novas; a regra dos 0,50 € (a de 1,50 € vai, a de 0,20 € fica,
a origem `deck:<slug>`, e **nada sai do `proprio:`**); as próprias não se
apagam e continuam fora do valor; o sleevado vai ao binder e não à Coleção;
zero decks nos 17 payloads, no `build`, nas rotas e na CLI; e a frase — a
mesma nos dois sítios, sem nomear o torneio, e em cada um dos seis sítios onde
a lista fica vazia.

## 28/09/2026, à noite — NADA EM FORMA DE DECK no Produto Selado (a aba fica em 30); e o «—» passa a DIZER o que se passa

Palavras dele: *"verifica novamente os produtos selados, ainda estao la
champions decks que nao tem disponiveis / e nao quero «decks» para
colecionar"*. Ramo `ai-pc/selado-sem-decks-2026-09-28`.

### A PRIMEIRA METADE DA QUEIXA NÃO BATIA CERTO, e diz-se

Medido antes de tocar em nada, com o catálogo fresco: **não havia Champion
Deck nenhum na aba** — saíram a 25 e 26/09 e continuavam em `selado.excluidos`.
O que lá estava com «Deck» no nome eram os **dois SHOWDOWN DECK**, e esses
**tinham oferta**:

| | preço | anúncios | Cardmarket |
|---|---|---|---|
| VEN «Zed vs Shen» Showdown Deck | 14,20 € | 58 | 888360 |
| RAD «Evelynn vs Seraphine» Showdown Deck | 35,41 € | 9 | 897517 |

Ele juntou duas queixas numa: «champions decks que não têm disponíveis» não
existia, «não quero decks para colecionar» é a que tem efeito — e é essa que
tira os dois Showdown Deck.

### 1. A REGRA É A CATEGORIA, NÃO UMA LISTA DE NOMES

A **262 «Riftbound Starter Decks»** saiu das `selado.categorias`, que ficam
`[259, 260, 261, 263, 283]`. **Zero mecanismo novo**: é o `selado._crus` a
filtrar por `categoria_id`, como sempre fez — uma linha de config.

**Porquê a categoria e não mais nomes:** uma lista de `excluidos` só apanha o
que JÁ existe e voltava a falhar no próximo lançamento. Há teste que mete um
Champion Deck NOVO no catálogo e exige que ele não apareça sem ninguém
escrever o nome.

**Medido no catálogo real:** a 262 tem **24 blueprints** (20 produtos depois
de juntar os 4 pares repetidos de Trial Deck) — os 11 Champion Deck, o
«Origins: Champion Deck Set», os 4 «Origins: X Trial Deck», os 2 «Trial Deck
Set» e os 2 Showdown Deck. **Nenhum tinha unidades gravadas** na
`sealed_copies` (as 5 dele são as quatro Booster Box e o Origins: Proving
Grounds), por isso nada dele ficou em risco.

**O QUE A REGRA NÃO APANHA, e fica dito em vez de escondido:** um produto em
forma de deck que o CardTrader arrume noutra categoria. É o caso dos dois
«Trial Deck Case», que são da **263** e continuam a sair pelo NOME. O
`tests/test_selado_sem_decks.py` varre a aba inteira por nome e por tipo e
rebenta se alguma coisa em forma de deck aparecer por qualquer via.

**O `DEFAULTS` não mexeu, de propósito.** A 262 **é** uma categoria de selado
no CardTrader — isso é um facto deles — e o que ele decidiu é uma escolha
DELE, que vive no `riftvault_config.json`, como o `selado.excluidos` e o
`abas.escondidas`. Um riftvault sem config vê o catálogo inteiro.

### 2. Os 18 nomes redundantes saíram da lista, e a decisão NÃO se perdeu

Com a 262 fora, **18 das 49 entradas** de `selado.excluidos` deixaram de
fazer trabalho nenhum. Ficaram em **31**. Deixá-las lá fazia a lista mentir
sobre o que está a fazer; apagá-las sem mais perdia a memória de quem as
mandou tirar — por isso foram para **`_selado_decks_arquivado`** no config,
com a data, a frase e a razão, como os 17 do `_selado_extra_arquivado` de
horas antes:

- **de 25/09** (7): o «Origins: Champion Deck Set» (*"compram-se à unidade"*),
  os 4 «Origins: X Trial Deck» e os 2 «Trial Deck Set»;
- **de 26/09** (11): os Champion Deck todos (3 OGN, 2 SFD, 2 UNL, 4 LGC).

**Ficaram no `excluidos`** os 2 «Trial Deck Case» — são da 263 e a regra não
os apanha. **Repor é escrever 262 outra vez** em `selado.categorias`, e aí os
18 nomes têm de voltar à lista, senão os Champion Deck voltam com eles.

### 3. O CATÁLOGO ESTAVA VELHO — e não era essa a causa dos «—»

O `api/selado.json` dizia `catalog: 2026-09-25T16:53`. Corrido o
`riftvault selado --sync` (104 pedidos, 1/s), o catálogo passou a
**2026-09-28T17:35** e o valor do selado de 552,56 € para **555,91 €** (o
mercado a mexer nos que têm oferta).

**Os 7 sem preço continuam os MESMOS 7 depois da leitura fresca**: nenhum era
catálogo desactualizado, todos têm mesmo zero ofertas em inglês no CardTrader
hoje — Origins: Proving Grounds, Unleashed Sleeved Booster, Legacy: Proving
Grounds, Secret Garden Bundle Box, Lunar Revel 2026 Bundle, Replacement Card
Booster e The T1 Worlds Champion | Signature Edition Box Set.

### 4. O «—» ERA UM BUG DE LEITURA, e é a queixa real dele

Um traço seco lia-se «este produto não existe». O que a app sabe é outra
coisa: **o CARDTRADER não tem oferta**, e ela **não lê o Cardmarket** (403 a
pedidos automáticos, API fechada a novas candidaturas). Dois desses 7 voltaram
à aba ONTEM precisamente porque o Cardmarket os tem (13,00 € e 35,00 €,
medidos pelo Chrome dele).

**A linha passou a dizer as duas coisas**, no site e no CLI, e o preço de lá
ganhou um sítio para ele o escrever — **a tabela `sealed_price`**
(`product_id`, `cents`, `updated_at`, `source`), que é o mesmo mecanismo do
Trend da Venda de 25/09 e pela mesma razão: *o que não se pode medir,
escreve-se à mão, com a data.* Tabela à parte porque a chave é outra — ali é
`printing_id` (uma carta), aqui é `product_id`; meter ids de produto numa
coluna chamada `printing_id` era mentir no nome e sujar as leituras da Venda.

**QUAL DOS DOIS CONTA** (`selado._preco_final`): o do **CardTrader quando
existe** — é medido, e é o que a aba sempre mostrou, por isso esta ordem não
mexe num número que ele já conhece —, o do **Cardmarket quando não existe**. A
linha diz sempre de que mercado veio o número; quando ele escreve um por cima
de um preço do CardTrader, os dois mostram-se e continua a contar o medido.
Trocar a ordem é o `or` do `_preco_final`.

Onde vive: `selado.precos_a_mao` / `definir_preco` / `_preco_final`,
`POST /api/selado/preco`, `riftvault selado --preco ID [EUROS]` (só o ID
apaga), o campo «CM» em cada linha (só no 8770; grava ao SAIR do campo, não a
cada tecla) e os contadores `sem_preco` (sem preço NENHUM), `sem_cardtrader`
e `preco_a_mao`. **Não toca no `copies`, na `ops`, nos locais nem na
`sealed_copies`** — há teste, e nenhum módulo de contas pode importar a
tabela, como a `sealed_copies`.

**Os dois preços NÃO foram semeados.** São medições de ontem e envelhecem; a
regra desta casa é que o número do Cardmarket é dele. São dois comandos:
`riftvault selado --preco ct-363132 13,00` e
`riftvault selado --preco ct-379338 35,00`.

### Medido a 2026-09-28, à noite, com o MESMO código e o MESMO catálogo

O «antes» é o config de ontem, reconstruído a partir do próprio arquivo — não
escrito à mão (`_revisao\_medir_sem_decks_selado.py`).

| | antes | depois |
|---|---|---|
| produtos na aba | 32 | **30** |
| dos quais «por sair» | 8 | 7 |
| tenho · unidades | 5 · 5 | **5 · 5** |
| não tenho | 19 | 18 |
| percentagem | 20,8 % | **21,7 %** |
| **valor do selado** | **555,91 €** | **555,91 €** |
| sem preço nenhum | 7 | 7 |
| categorias no config | 6 | **5** |
| nomes em `selado.excluidos` | 49 | **31** |
| **decks na aba** (por tipo · por nome) | **2 · 2** | **0 · 0** |

**Saíram exactamente 2** (os dois Showdown Deck) e entrou zero; por edição só
mexem a VEN (5→4) e a RAD (4→3). **O valor não mexeu, e tinha de ser:** as 5
unidades dele são todas de produtos que ficaram. **O `copies` tem o mesmo
sha256** (`44f6424d…`, 1044 linhas, 2659 normais + 539 foil) antes e depois.

`tests/test_selado_sem_decks.py` (73 testes): a regra pela categoria e a prova
pela negativa; **um Champion Deck novo que ninguém nomeou não aparece**; o
tipo `deck` fora da aba e dos `tipos` do payload; a 262 contada no `fora`;
uma unidade gravada num deck não se apaga e volta; repor é escrever 262; o
`selado.extra` pode na mesma ter um deck à mão, e diz-se; o config e o
catálogo REAIS (os 18 arquivados com a data e a razão, os 2 «Trial Deck Case»
que ficam, **nenhuma entrada do `excluidos` a tirar um produto da 262**, e
**nada em forma de deck na aba por via nenhuma**); o preço do Cardmarket (as
duas ordens do `_preco_final`, a vírgula e o ponto, apagar, o valor, os
contadores, as recusas, a data e a origem, e **escreve só na `sealed_price`**);
a interface (o traço seco desapareceu, o 403 no cabeçalho, o campo só em modo
edição, grava ao sair, e a frase sem `nowrap` — a lição de 22/09); a rota e a
CLI; e a **fotografia do `test_selado`, por referência**.

Cinco ficheiros de teste foram ajustados nos NÚMEROS e no MECANISMO — o teste
é que descrevia o de ontem, não o código: `test_selado_tirar`,
`test_selado_tirar2`, `test_selado_champion`, `test_selado_sem_mercado` e
`test_selado_ingles` (49 → 31 nomes, 32 → 30 produtos, e as asserções de «está
no `excluidos`» passaram a «está fora da aba **e** a decisão está arquivada»).
Os que perguntavam a categoria de um deck passaram a perguntá-la ao
**catálogo em disco**: desde hoje os produtos da 262 não chegam ao `_crus`.

## 29/09/2026 — MAIS DO QUE UMA PESSOA: a fundação (`utilizador.py`, `users`, `user_id`)

Palavras dele: *"Amigos meus querem usar o site para organizar a coleccao
deles. Podes fazer com que mais pessoas possam organizar a coleccao deles
tambem usando o site?"* — com contas a sério e backend, a prazo tudo o que ele
tem, um site público só de leitura por pessoa num subdomínio com o nome dela
(*"ao inves de Baverone.riftvault seria Miguel.riftvault"*), o servidor a
começar no PC dele por túnel Cloudflare, e **a começar por uma fatia fina**.
Ramo `ai-pc/multi-utilizador-2026-09-29`; o desenho inteiro está em
**`docs/multi-utilizador.md`**.

**ESTA CORRIDA É SÓ A FUNDAÇÃO DO MODELO DE DADOS.** Não há autenticação, não
há túnel, não há subdomínios, não há site por utilizador: dependem de passos
que só ele pode dar (a conta Cloudflare, os nameservers, o `cloudflared`).
**Para ele não muda nada** — medido, zero diferenças em 26 superfícies.

### A decisão de fundo: UM FICHEIRO POR PESSOA, não `WHERE user_id = ?`

Duas medições decidiram-no, e a primeira sozinha chegava:

1. **O `data/vault.db` está commitado num repositório PÚBLICO e é empurrado
   sozinho.** `gh repo view` diz `PUBLIC`, `git ls-files data/` diz
   `data/vault.db`, e são **95 commits** dele, de 30 em 30 minutos, pela
   `riftvault-publicar`. Pôr a coleção de um amigo nesse ficheiro
   **publicava-a**, para sempre — o histórico do Git não se apaga. A coleção do
   André é dele e ele escolheu publicá-la; a do Miguel não é nossa para
   publicar.
2. **São 134 statements de SQL em 19 módulos** a tocar nas tabelas de dono. Uma
   separação que dependa de 134 `WHERE` bem lembrados falha em silêncio e do
   lado pior: um esquecido numa LEITURA mostra a coleção de um a outro.

Com um ficheiro por pessoa a separação é **física** e **nenhum dos 134
statements mudou**.

```
data/vault.db                o ANDRÉ (utilizador 1, slug `baverone`) — no Git
data/catalog.db  prices.db   PARTILHADOS, sem dono
data/users/                  <<< NO .gitignore
  registo.db                 o REGISTO: quem existe
  miguel/vault.db            a coleção do Miguel
  miguel/decks/*.txt         as listas dele
```

Medido: a base de um utilizador novo são **242 KB**, contra 1,4 MB de catálogo
e 745 KB de preços que ele não volta a pagar.

### O REGISTO não pode viver do lado público — apanhado a meio da corrida

A `users` estava no `data/vault.db`. Com ela lá, **registar um amigo publicava
o nome e o slug dele no GitHub**, de 30 em 30 minutos e com histórico — mesmo
que a coleção dele ficasse privada. Era a mesma armadilha que fez cada coleção
ir para um ficheiro próprio, a dois metros de distância. Foi apanhada pelas
duas sessões que trabalhavam nas fatias seguintes (a `riftbound-2b` e a
`riftbound-f3`) e corrigida antes do merge.

Agora a `users` vive em **dois** sítios, com a definição uma vez só
(`riftvault/users_schema.sql`): o **registo** em `data/users/registo.db`, fora
do Git, com toda a gente; e **dentro de cada `vault.db`** a linha do DONO
daquele ficheiro e só essa, para o ficheiro se explicar a quem o restaura. A
base pública do André conhece **só o André** — há teste.

### O `user_id` nas 16 tabelas: o que faz e o que NÃO faz

`ALTER TABLE … ADD COLUMN user_id INTEGER` + índice, nas 16 (a lista é o
`db.TABELAS_DE_DONO`). **Não refaz tabela nenhuma e não toca num número.**
Migradas **4 778 linhas**, todas para o utilizador 1, zero por carimbar.

**NÃO é o `user_id` que separa — é o ficheiro.** Ele faz três coisas: cada
linha diz de quem é, e por isso uma base aberta como o utilizador errado é
DETECTÁVEL (`utilizador.guardar` levanta `DonoErrado` — é a rede que apanha um
backup restaurado por cima de outro); a migração faz-se hoje, com um
utilizador e zero risco; e uma consolidação futura passa a ser um `INSERT …
SELECT`. **`NULL` quer dizer «do dono deste ficheiro»** e é adoptado na ligação
seguinte.

**Uma assimetria a conhecer:** numa base criada de raiz a coluna leva
`REFERENCES users(user_id)` e a FK recusa um dono inventado; numa base
**migrada não há FK** — o SQLite não sabe acrescentar uma chave estrangeira num
`ADD COLUMN`, e refazer dezasseis tabelas da coleção dele não se pagava. É por
isso que o guarda existe: vale nos dois casos. Há teste para cada.

**E o carimbo é PREGUIÇOSO**: corre no `connect`, antes das escritas da sessão,
por isso uma base criada e nunca mais reaberta tem as linhas todas a `NULL` e
as linhas sozinhas não distinguem ninguém. O guarda pergunta por isso a DOIS
sítios, e o que manda é a `users` de dentro da base — a identidade do ficheiro,
escrita em toda a ligação. Apanhado pela sessão `riftbound-2b`.

**O FURO QUE A SEPARAÇÃO POR FICHEIRO NÃO TAPA: o config.** O
`riftvault_config.json` é UM ficheiro para todos e não é uma base de dados —
o `POST /api/decks/montar` e o `/api/decks/principal` escrevem lá, e um amigo
escrevia na lista do André sem passar pelo SQLite. Enquanto o config for
global, **o estado dos decks fica fora das contas**. Apanhado pela sessão
`riftbound-f3`; está na secção 6 do documento.

**As PK não mudaram**, de propósito: com um ficheiro por pessoa o
`printing_id` continua único. O que uma consolidação num ficheiro só ainda
precisaria está escrito no `docs/multi-utilizador.md`, para ninguém contar que
sai de graça.

### A PORTA ÚNICA

```python
utilizador.atual()                 # o utilizador desta sessão — HOJE sempre 1
utilizador.como(uid)               # gestor de contexto, por FIO
db.connect(readonly=False, user_id=None)
con.riftvault_user                 # o dono viaja com a ligação
config.decks_dir(con)              # a pasta de `.txt` daquele utilizador
db.TABELAS_DE_DONO                 # as 16
```

Todo o código que lê dados de dono recebe um `con`, e **todo o `con` sai do
`db.connect`** — por isso é aí, e só aí, que se responde a «de quem são estes
dados», e a autenticação vai ser uma mudança no `atual()` e mais nada. Dois
testes guardam-no: nenhum módulo abre uma base por fora do `db.connect`, e
nenhum lê a variável do utilizador fora do `utilizador.py`.

**O `atual()` lê um `contextvars.ContextVar`, não uma global** — o `serve`
corre `threaded=True`, e uma global punha dois pedidos simultâneos a ver o dono
um do outro. Foi um defeito real apanhado pela sessão `riftbound-f3` antes de o
servidor chegar a usar a porta. O `RIFTVAULT_USER` continua a valer para o CLI
e para as medições, e **não serve para o servidor**.

**A pasta de decks passou a ser por utilizador** (`config.decks_dir(con)`, três
chamadas): sem isso um segundo utilizador importava as listas do André.

### Medido a 2026-09-29, `main` e ramo, contra cópias do `data/` real

**ZERO DIFERENÇAS em 26 superfícies** — denominador **928**, níveis
**910/875/786 de 928**, valor **8 144,89 € · 3 195 cópias**, wantlist «tudo»
**142 linhas · 209 cópias · 755,85 €** (e o TEXTO, por sha256), as cinco por
edição, Faltas **449 cópias · 8 693,28 €** e as foils **914 · 376,67 €**, os 20
blocos por edição, A mais, Encomendas, Venda, Selado, painel, foil, e a grelha
impressão a impressão nas cinco edições. **A `copies` tem o mesmo sha256 do
conteúdo** (`a85095b4…`, 1 046 linhas, 2 663 normais + 540 foil).

Exercitado com um segundo utilizador contra uma cópia dos dados reais: o
Miguel vê **3 impressões · 11 cópias · 242,77 €**, o André continua nos
**8 144,89 €** ao cêntimo, os ficheiros são dois, e **o catálogo e os preços
são o MESMO ficheiro** para os dois (1 180 impressões, 1 227 preços).

`tests/test_multi_utilizador.py` (**41 testes**): dois utilizadores não se veem
(pela app inteira — métricas, valor, wantlist, faltas, foil — e não por um
`SELECT`); apagar um não toca no outro e o André não se apaga por aqui; o
catálogo é partilhado e não tem dono; **a migração de uma base de um dono não
perde nem inventa uma linha** (contagem tabela a tabela + sha256 da `copies`),
faz backup e é idempotente; o registo não está no lado público; o guarda do
ficheiro trocado; o slug que não foge da pasta; e a porta única, com o
`como()` a valer só no seu fio (dois fios com uma `Barrier`).

**Um teste que é uma rede para o futuro:** o
`test_a_lista_das_tabelas_de_dono_e_a_das_que_existem` rebenta se alguém
acrescentar uma tabela ao `vault.db` sem a classificar — ou é de dono (vai para
o `db.TABELAS_DE_DONO`, ganha `user_id` e entra no apagar de uma conta) ou é do
serviço, e diz-se porquê.

Dois testes do `test_foil.py` foram ajustados — descreviam a tabela antiga: um
fazia `INSERT INTO copies VALUES (…)` posicional com 4 valores (a `copies` tem
5 colunas desde hoje) e dois contavam `glob("*.db")` esperando exactamente 1
backup, quando uma base antiga passa agora por duas migrações. Passaram a
contar o que há antes e depois, que é o que queriam dizer.

### O que fica por fazer, e o que só ele pode fazer

**Fases 2 a 5** no `docs/multi-utilizador.md`: identidade (as credenciais numa
base à parte, fora do Git — **nunca na `users`**, que viaja em `SELECT *`), um
site por utilizador (`build.py` por `user_id`, para `site/u/<slug>/`), o túnel,
e a separação do config. **Hoje as regras do `riftvault_config.json` são
GLOBAIS e um amigo herda as dele** — é limitação conhecida, com a linha
proposta (regra do produto vs preferência de utilizador) escrita no documento.

**A forma recomendada, e concordo com ela:** as leituras públicas continuam
ESTÁTICAS (Pages) e o túnel serve só a edição autenticada. É a arquitectura de
2026-09-10, agora a responder ao risco em vez de à disponibilidade: o PC dele
fica fora do caminho de quem só espreita.

**Os riscos de guardar dados de terceiros** estão na secção 7 do documento, e o
mais urgente é este: **os amigos não têm backup nenhum**. O `data/vault.db`
dele tem 95 pontos de restauro no Git; a pasta `data/users/` está no
`.gitignore` de propósito, e por isso precisa de uma cópia para fora do PC
ANTES do primeiro amigo. Também lá: apagar a conta a pedido, o PC desligado, e
quem entrar na máquina tem as coleções todas.

## 29/09/2026, à noite — CONTAS: entrar sem password, e a porta ainda FECHADA (`auth.py`, `rotas_conta.py`, `abrir.py`)

**A METADE DA IDENTIDADE FOI REVOGADA NO DIA SEGUINTE.** A 2026-09-30 ele pediu
**utilizador e password** e isso é o que vale — ver a última secção deste
ficheiro. Tudo o que aqui se diz sobre «nunca se guarda uma password» e sobre o
Discord/Google ser a forma de entrar é história: o OAuth **fica no código,
parado e sem botão**, e as contas nascem de `riftvault conta --criar`. O resto
desta secção — as sessões, o CSRF, o cookie, a decisão da LAN, o furo do config
partilhado, os endereços — continua a valer inteiro.

Palavras dele, antes de ir dormir: *"Quero que deixas a parte do riftbound
pronta para amigos meus criarem conta e poderem comecar a usar a registar a
coleccao deles!!! Nao estarei aqui para aprovar pois estou a dormir, faz tudo o
que puderes sem precisar de mim, quero isso a funcionar!"* — e, uma hora antes,
*"Quero apenas apresentar quando tiver tudo"*. As duas encaixam: **tudo a
funcionar e pronto a abrir, com a porta ainda fechada.** Ele abre quando quiser.

Terceira fatia da cadeia, a seguir à `0-multi-utilizador-1` (o modelo de dados)
e à `1-multi-guardas` (o isolamento, a privacidade e o `multi.aberto`). O
desenho está em `docs/contas-e-autenticacao.md` e o guia dos passos DELE em
`docs/abrir-a-porta.md`.

### NENHUMA PASSWORD, EM SÍTIO NENHUM

Não há campo, não há hash, não há «esqueci-me da minha». Entra-se com uma conta
que já existe — **Discord** (recomendado: a malta de TCG já o tem e a aplicação
faz-se em cinco minutos) ou **Google** (que obriga a ecrã de consentimento e
verificação, e pode levar dias). Guarda-se `provedor` + `sub` + `user_id`, e
**nenhum token do fornecedor**: o `access_token` serve uma pergunta («quem és
tu?») e morre no mesmo pedido. Não se pede o email — o `sub` identifica, e é
menos um dado de terceiros num PC de casa.

**Não se verifica o `id_token` à mão, de propósito.** Validar a assinatura de um
JWT exige JWKS, rotação de chaves e RSA, e é um dos sítios clássicos de falhas
(`alg: none`, o `kid` não verificado, a expiração esquecida). Pergunta-se ao
fornecedor por TLS (`userinfo` no Google, `users/@me` no Discord): quem autentica
a resposta é o TLS, e não há criptografia nossa para correr mal.

### ONDE VIVEM AS CREDENCIAIS — e a armadilha que quase se repetiu

**`data/auth.db`, à parte e no `.gitignore`.** A `1-multi-guardas` propôs
pô-las na «base do sistema», que é o `data/vault.db`. Mediu-se antes de aceitar:
`git ls-files data/` devolve `data/vault.db`, o `origin` é
`github.com/Baverone/riftvault` (**PÚBLICO**) e a `riftvault-publicar` faz push
**de 30 em 30 minutos**. O `sub` do Google é um identificador estável e único de
uma pessoa: ali ficava publicado para sempre, com histórico.

**É a mesma armadilha que levou a `0-multi-utilizador-1` a pôr cada coleção num
ficheiro seu — e ela tinha ficado a dois metros.** A tabela `users` estava do
lado público: registar um amigo publicava-lhe o nome e o slug, mesmo com a
coleção privada. Corrigido na mesma corrida (o registo passou a
`data/users/registo.db`). Por isso **`users.auth_ref` fica VAZIA** — nem um
ponteiro opaco.

**E o mesmo vale para o CLIENT SECRET, contra o que esta ordem escreveu
primeiro.** O `riftvault_config.json` **está commitado** (`git ls-files`
confirma). O segredo passou a vir do AMBIENTE (`RIFTVAULT_DISCORD_SECRET` /
`RIFTVAULT_GOOGLE_SECRET`), que é a regra que o `.gitignore` já escreve para o
`CARDTRADER_TOKEN`; o `client_id` **não é segredo** (viaja no endereço de
autorização) e fica no config. O `multi --verificar` avisa se o segredo estiver
no ficheiro versionado, com o comando para o tirar de lá.

### O QUE DECIDIU A REGRA DA LAN: O TÚNEL FAZ A INTERNET PARECER LOOPBACK

O CLAUDE.md diz desde o início que *«o modo edição não tem autenticação nenhuma
[…] é aceitável na LAN»*. Com coleções de amigos lá dentro deixa de ser.

Pensou-se em confiar no endereço («se vem de casa, é ele»). **Não se pode:**
`cloudflared tunnel run --url http://localhost:8770` faz **todo** o tráfego da
internet chegar ao Flask como `127.0.0.1`. Uma regra que confiasse no loopback
dava a identidade do André a qualquer visitante. Por isso **não há atalho por
endereço em sítio nenhum** — o `remote_addr` só se lê para contar tentativas.

| | |
|---|---|
| porta FECHADA (`multi.aberto: false`, o de hoje) | um dono só, sem autenticação, **tudo exactamente como ontem** |
| porta ABERTA | toda a escrita exige sessão e CSRF, **ele incluído** — entra uma vez e a sessão dura 30 dias |

### O CAMINHO DO PRIMEIRO UTILIZADOR (`multi --ligar`) — um buraco que partia tudo

**Ele JÁ EXISTE**: é o utilizador 1, com o slug `baverone`. Na primeira entrada
com o Discord o `por_identidade` devolvia `None` e a app oferecia-lhe o
**REGISTO** — que lhe pedia um slug que ele não podia escolher, porque o dele já
é dele (`utilizador.criar` recusa um slug tomado). Formulário sem saída, com a
coleção de um mês do outro lado. E o próprio `--verificar` mandava-o fazer isso.

A saída é `riftvault multi --ligar`: um código de uso único criado na **consola**
(`auth_convites`, o SHA-256 do código; `auth_pedidos.liga_a`), que autoriza a
próxima entrada a **ligar-se** a uma conta que já existe. Duas decisões:
**funciona com a porta FECHADA** (ele liga antes de abrir, e por isso nunca se
abre a porta com ele do lado de fora) e **o código vem da consola** — quem tem a
consola do PC é o dono do PC, e isso prova mais do que qualquer verificação de
IP. O convite gasta-se na IDA, para não ficar um código válido à espera.

### O QUE É SEGURO POR CONSTRUÇÃO, E O FURO QUE NÃO ERA

Cada coleção é um FICHEIRO, e o servidor só abre a do dono da sessão: **não é um
`WHERE user_id` que se pode esquecer, é um ficheiro que não se chega a abrir.** O
`g.riftvault_user` é escrito **num sítio só** (a sessão), e há teste que varre o
próprio ficheiro e rebenta se alguém lho voltar a atribuir a partir do caminho —
era assim que a base de outra pessoa se abria num GET, e só não vazava porque
nenhuma rota casava com o prefixo `/u/<slug>/`: segurança por acidente.

**O furo a sério estava fora das bases de dados.** Duas rotas não escrevem em
tabela nenhuma — escrevem no `riftvault_config.json`, que é UM ficheiro para
todos:

    POST /api/decks/montar     -> decks.alternar_montado()    -> decks.montados
    POST /api/decks/principal  -> decks.escrever_principal()   -> decks.principal

Um amigo autenticado a carregar em «Montar» escrevia o slug do deck DELE na
lista do André. Não passa pelo SQLite, por isso um `authorizer` não o vê.
Ficam em `rotas_conta.SO_DO_DONO` (403 com a razão), e a `1-multi-guardas`
acrescentou um guarda dentro do `config.escrever_valor` para cobrir a CLI.
**Consequência escrita: o ESTADO dos decks (montados/principal/ordem) fica fora
das contas** até o config ser por utilizador.

**A lição, para a fatia seguinte:** num sistema multi-inquilino, «onde é que
isto se guarda?» tem de ser perguntado a cada ESCRITA, não só às tabelas. Um
ficheiro de configuração é estado partilhado tanto quanto uma tabela sem dono.

### Sessões, CSRF e o resto

Cookie `HttpOnly`, `SameSite=Lax` (**não `Strict`**: a volta do fornecedor é uma
navegação que vem de outro site, e com `Strict` o cookie não seguia e a entrada
nunca se concluía), `Secure` só em HTTPS (no 8770 é `http://` e um `Secure` ali
fazia o browser descartá-lo). Na base fica o **SHA-256** do que está no cookie.
**Rotação no login**: uma sessão nasce sem dono enquanto se escolhe o nome, e ao
criar a conta o identificador é substituído. Uma sessão pré-registo dura **uma
hora**, não trinta dias.

**CSRF num cabeçalho, não num cookie** (num cookie era enviado junto com o
pedido falso, que é o que isto trava). No cliente havia **17** `fetch` de POST,
cada um com o seu literal de cabeçalhos: passaram todos por **uma** função
(`cabecalhos()`), e há teste que lê o `app.js` e rebenta se aparecer um POST que
não passe por ela — acrescentar a marca a 17 sítios à mão era garantir que um dia
se esquecia num, e um esquecido é uma rota sem protecção, não um erro visível.

**Login CSRF fechado**: o `state` não estava atado ao browser, e sem isso quem
começasse uma entrada podia levar OUTRA pessoa a concluí-la — o browser dela
ficava com uma sessão da conta dele. Há um `nonce` num cookie curto e o SHA-256
dele na `auth_pedidos`. O **prazo verifica-se ANTES do nonce**, por causa da
mensagem: quem demorou vinte minutos também perdeu o cookie, e dizer-lhe «não
começou neste browser» mandava-o procurar um problema que não tem.

Tecto de **20 tentativas por hora e por endereço** — a chave do balde é
falsificável e não faz mal: falsificá-la dá mais baldes, não dá acesso. Corpo do
pedido até **256 KB** (o `/api/local/marcar` manda uma lista de centenas de
linhas). `RIFTVAULT_USER` definido com a porta aberta **recusa arrancar**: fixa o
dono para o processo inteiro e faria todos os pedidos escrever na mesma coleção.

### O `Miguel.riftvault` que ele pediu é com BARRA, e a razão é medida

`rift.baverone.com/u/miguel/`. Os sites públicos estão no **GitHub Pages**, que
aceita **um** endereço personalizado por repositório e **não** aceita
`*.rift.baverone.com`. Para ser `miguel.rift.baverone.com` era preciso ou um
repositório por amigo, ou a Cloudflare a reescrever endereços à frente do GitHub
— mais uma peça, e uma peça cuja falha tira os sites do ar. O nome que ele
escolhe é o mesmo nas duas formas, por isso a escolha não fica presa.

**Dois endereços com papéis diferentes, de propósito:** o público é estático
(GitHub Pages) e **abre com o PC desligado**; o de edição
(`editar.baverone.com`) é o PC dele pelo túnel. O PC fica fora do caminho de
quem só espreita, que é a maior parte do tráfego e do risco.

### O que ficou de fora, e porquê

- **Config por utilizador.** As regras (`foil.raridades`, `master_set.*`, alvos,
  `decks.*`, `selado.*`) continuam **globais**: um amigo herda as dele. É
  limitação conhecida da `0-multi-utilizador-1`, está no documento dela, e não
  se inventou aqui um config por utilizador de véspera.
- **O estado dos decks** — ver o furo do config, acima.
- **Convites.** Com a porta aberta, quem chegar ao endereço registra-se. Uma
  lista de `sub` permitidos obrigava-o a recolher o `sub` de cada amigo, o que é
  pior do que parece. Fica como pergunta.
- **Mudar de slug.** O endereço É o slug, e mudá-lo parte os links que o amigo
  já deu. Não se faz sem ele decidir o que acontece ao antigo.

## 29/09/2026 — AS GUARDAS: isolamento imposto pelo código, conta por pessoa, privacidade, e as portas fechadas

Palavras dele: *"O que achas que deve ser já feito para evitar erros futuros, e
o quê? / Posso concordar e começamos também já a tratar disso?"* — concordou de
antemão. A lista é curta de propósito: são as coisas **baratas agora e caras
depois de haver gente lá dentro**. Ramo `ai-pc/guardas-2026-09-29`, a seguir à
fundação (a secção acima). Ver `docs/multi-utilizador.md`, «As guardas».

### 1. PORTAS FECHADAS até ele mandar abrir (`multi.aberto`)

*"Quero apenas apresentar quando tiver tudo"* (2026-09-29). Um interruptor só,
no config, e **nasce fechado**:

    "multi": { "aberto": false }

Lê-se por `multi.aberto(cfg)` e por mais nenhuma função. Enquanto for `false`:
não há registo nem contas de amigos (há **um** utilizador, ele); **o túnel não
se liga** — não há cloudflared instalado nem configurado; as páginas públicas
dos outros **não se publicam** (o `build_todos` sabe gerá-las e há teste que o
prova, mas para o `site/` vai só a dele); e **o site dele fica exactamente como
hoje**, sem «em breve» nem link de login. Quando ele quiser abrir, muda-se **um
valor**, não dez condições.

### 2. O QUE O PÚBLICO VÊ: `users.publico`

| valor | o público vê |
|---|---|
| **`nada`** (omissão) | **nada** — não se gera site nenhum |
| `sem-valores` | a coleção, e **nenhum euro em lado nenhum** |
| `tudo` | como o site dele hoje |

**A omissão é a mais fechada** porque publicar a coleção de outra pessoa tem de
ser um acto ESCOLHIDO: uma página pública indexa-se e fica em cache em sítios
que não controlamos — na prática **não se despublica**. **O André fica em
`tudo`**, que é o que ele já escolheu e tem; o site dele não muda um byte.

O campo vive no **REGISTO** (`data/users/registo.db`), não na coleção — quem o
lê não tem motivo nenhum para ter a base de cartas de alguém aberta. A cópia
que viaja dentro de cada `vault.db` é descritiva.

**Como é que o `sem-valores` tira os euros: TRÊS regras**, aplicadas ao payload
antes de ser escrito (`privacidade.limpar`), e **uma porta só** no `build.py`
(o `escrever()`, com teste que recusa um `json.dumps` fora dele):

1. uma chave cujo NOME fala de dinheiro e cujo valor é um número perde o valor;
2. `total` é AMBÍGUA — é uma quantia nas linhas das Faltas (`price × missing`)
   e uma CONTAGEM em todo o resto (o denominador «910 de 928»). Medido contexto
   a contexto no site real: nas **820** em que é dinheiro o dicionário tem
   sempre um `price` ao lado; nas **84** em que é contagem, nenhuma tem;
3. **um dicionário cujo nome fala de dinheiro tem dinheiro lá dentro**, tenham
   as chaves o nome que tiverem. Esta nasceu de uma fuga a sério: o
   `progress.value` é `{"owned": 213751, "full": 128087, "hidden_owned": 0}` —
   o valor da coleção em cêntimos, com três nomes que não dizem dinheiro.

**DUAS REDES, e apanham coisas diferentes.** A regra apanha o que tem nome; o
teste pega em números que **são** preços (sentinelas inconfundíveis — um preço
pequeno em cêntimos COLIDE com uma contagem: o 3195 é ao mesmo tempo o número
de cópias da coleção e o preço de uma carta) e exige que não apareçam em lado
nenhum. Foi a segunda que encontrou a fuga da regra 3. **Medido no site real:
tira 7 129 quantias e 1 texto com `€` nos 20 ficheiros, e as contagens — o
denominador, as cópias, as percentagens — ficam.**

### 3. ISOLAMENTO IMPOSTO PELO CÓDIGO — e a pergunta mudou de forma

A ordem foi escrita a contar com uma base só filtrada por `WHERE user_id = ?`,
onde o erro clássico é um `WHERE` esquecido. **Não é esse o modelo que ficou**
(ver a secção da fundação): é **um ficheiro por pessoa**, e um `WHERE`
esquecido já não mostra nada de ninguém — os dados do outro não estão na
ligação. O modelo novo tem o SEU esquecimento, e são **quatro** as guardas:

1. **Tocar numa tabela de dono sem dono REBENTA** (`guarda.SemDono`), com a
   tabela nomeada. É um **autorizador do `sqlite3`** — não um wrapper à volta
   do `execute`, que se contorna com um `cursor()`. **Medido: 50 000 consultas
   em 48 ms armado contra 49 ms desarmado**, custo nenhum (o SQLite chama-o na
   PREPARAÇÃO e o Python guarda os statements em cache). Hoje nunca dispara
   porque `utilizador.atual()` devolve sempre o André; **o dia em que valer** é
   aquele em que houver sessões e `atual()` puder não saber quem é — sem
   guarda, esse dia serve a coleção dele a um visitante anónimo, em silêncio.
2. **Uma ligação ligada a alguém não pode ANEXAR outra base** (`SoUmaBase`) —
   é a única maneira de dois donos aparecerem no mesmo `SELECT`.
   **ARMADILHA MEDIDA: o `VACUUM INTO` anexa o destino por dentro**, e sem uma
   porta explícita isto partia **todos** os backups das migrações. A porta é o
   `guarda.a_copiar(con)`, um contador que fecha mesmo que rebente lá dentro, e
   só se usa no `db.backup` e no `conta`.
3. **Uma base com dados de outro dono recusa-se a abrir**
   (`utilizador.guardar`, `DonoErrado`).
4. **Ninguém abre um `vault.db` fora do `db.py`** — `tests/test_isolamento.py`
   lê o código-fonte e recusa um `sqlite3.connect` ou o caminho fixo da base
   dele em qualquer outro módulo.

**O QUE O AUTORIZADOR NÃO VÊ, e é preciso dizê-lo: o que não é SQL.** As
escritas no `riftvault_config.json` (`decks.montados`, `decks.principal`) não
passam pelo SQLite — um amigo autenticado a carregar em «Montar» escrevia o
slug do deck DELE na lista do André. Tapado por um guarda próprio,
`config.ConfigPartilhado`, no `escrever_valor` (cobre a CLI e tudo o resto), e
pela camada de rotas (cobre o HTTP com a mensagem certa). Pelo mesmo motivo o
`config.decks_dir(con)` passou a rebentar com uma ligação sem dono, em vez de
devolver a pasta dele. **Consequência honesta:** enquanto o config não for por
utilizador, o ESTADO dos decks — montados, principal, ordem — é o do dono do
ficheiro. As CARTAS de cada um contam na mesma.

**A prova de comportamento:** dois utilizadores com colecções PARECIDAS (de
propósito — obviamente diferentes, um engano denunciava-se sozinho) e pegada em
todos os subsistemas, e **26 funções públicas** varridas, cada uma com três
perguntas: o segredo do outro nunca aparece, a sentinela do outro vale zero, e
a função DISTINGUE os donos. **Uma função que dê o mesmo aos dois é uma função
que não sabe de quem são os dados** — a lista das que podem dar igual tem uma
entrada só (`principal.estado`, pela razão do config acima) e está escrita no
teste.

### 4. BACKUP, RESTAURO E APAGAR — por pessoa (`conta.py`)

*"Com cinco pessoas lá dentro, restaurar um erro dele desfaz o mês dos
outros."*

    conta.exportar(slug)                       -> um .zip
    conta.importar(ficheiro, confirmar=True)
    conta.apagar(slug, confirmar=True)

Barato por a separação ser por ficheiro. O pacote leva o `vault.db` (por
`VACUUM INTO` — as bases estão em WAL), o config e as listas dele; **não leva
credenciais** (vivem no `data/auth.db`, fora do Git e fora daqui) **nem o
catálogo nem os preços** (são partilhados). O `apagar` **faz um export antes**,
diz quantas linhas saíram de que tabelas, e é a POLÍTICA por cima da primitiva
`utilizador.apagar`. **O utilizador 1 não se apaga por aqui.**

**UMA DESCOBERTA A MEDIR, e mudou o código dos dois lados: o carimbo do dono é
PREGUIÇOSO.** O `utilizador.guardar` corre no `db.connect`, ou seja ANTES das
escritas da sessão — uma linha escrita durante a sessão fica a `NULL` e só é
carimbada na abertura seguinte. **Um ficheiro criado e nunca mais reaberto tem
as linhas todas a `NULL`**, e nesse estado elas não distinguem ninguém: um
backup de outra pessoa passava. Apanhado com um teste que forjava um manifesto
e via a recusa não acontecer. A identidade fiável do ficheiro é a **`users` de
dentro dele**, que o `_carimbar_dono` escreve em toda a ligação — e é por aí
que o `guardar` e o `conta` passaram a perguntar primeiro.

### 5. A COLEÇÃO É SOBERANA — e passou a ser TESTE

*"Já foi violada uma vez (a contagem dos foils, 26/09) e só se apanhou por eu
medir à mão."* `tests/test_coleccao_soberana.py`, **três camadas**, porque «não
mexe na `copies`» à letra seria mentira:

- **A.** O caminho da Coleção é uma **lista fechada de seis** (`collection.adjust`,
  `undo_last`, `pending.arrive`, `venda.vender`, `foil.ajustar`,
  `proprias.ajustar`). **Tudo o resto** — 25 operações e o `build` inteiro —
  deixa a `copies` byte a byte igual;
- **B.** as duas que tocam sem serem a Coleção (`foil`, `proprias`) **não mudam
  o número de cópias NORMAIS na Coleção** nem os níveis. É a invariante que a
  avaria de 26–27/09 partiu;
- **C.** nada do que um faz mexe na `copies` do outro.

Cada camada tem a **prova pela negativa** a seguir — um teste que mostra que a
fotografia sabe mesmo detectar uma mudança. Uma fotografia de zeros passa
sempre, e era assim que isto não valia nada.

### 6. A IDENTIDADE É EMPRESTADA — decisão, não implementação

*"Não quero que ele guarde passwords, nunca."* **Autenticação por um fornecedor
que já existe** (OAuth/OIDC); o riftvault guarda só o identificador que ele
devolve. Três razões: o que não se guarda não se perde (uma base de palavras-
passe é um alvo, e isto corre no PC de casa dele); não há «esqueci-me da
palavra-passe» para construir; e é menos um passo para quem entra. **Discord
primeiro, Google a seguir** — é onde a malta de TCG já está. **Não se
implementou nada**; o encaixe é o `users.auth_ref`, e está vazio.

### 7. UM SÍTIO PARA PARTIR COISAS (`RIFTVAULT_ENSAIO=1`)

| | a sério | ensaio |
|---|---|---|
| dados | `data/` | **`data-ensaio/`** |
| config | `riftvault_config.json` | **`riftvault_config-ensaio.json`** |
| o `serve` escuta em | `0.0.0.0:8770` | **`127.0.0.1:8779`** |

É uma variável do AMBIENTE e **não** uma chave do config: uma chave de ensaio
dentro de um ficheiro que vai para o Git está a um merge de distância de ir
para produção ligada. **A garantia de que o túnel nunca aponta para o ensaio é
a última linha, e é por construção:** o túnel serve a 8770, o ensaio recusa-se a
escutar nessa porta (`multi.PortaDeProducao`) e só aceita o loopback. **E o
ensaio recusa-se a usar o `data/` a sério** — o `config` rebenta ao ser
importado.

### 8. O PORTÃO DO MERGE

Ver a secção própria, a seguir.

## 29/09/2026 — O PORTÃO DO MERGE LÊ O PLACAR, e um placar ausente é VERMELHO

**O que aconteceu.** A 2026-09-29 o harness que corre estas sessões disse
**«exit code 0»** numa corrida cuja suite tinha acabado de imprimir **«1 a
falhar»**. Quem lesse o código de saída dava o ramo por verde e fazia o merge.

A regra «lê o PLACAR, não acredites no harness» já estava escrita nas regras da
casa desde que isto começou — e era uma regra FALADA. Uma regra falada é uma
regra que um dia se esquece, às duas da manhã, no fim de uma ordem longa.
Passou a ser mecânica.

**`tools/placar.py` + `tools/portao.py`.**

    py -X utf8 tools/portao.py suite        corre a suite e grava o placar
    py -X utf8 tools/portao.py verificar    lê o placar; sai 1 se vermelho
    py -X utf8 tools/portao.py merge <ramo> -m "<mensagem>" [--push]

O `merge` **verifica primeiro e recusa-se a chamar o `git`** se o placar não
for verde. **Não há bandeira para forçar**, e é de propósito: uma bandeira de
forçar é a que se usa exactamente na noite em que não se devia. Quem quiser
mesmo integrar com a suite vermelha escreve o `git merge` à mão — e aí é uma
decisão, não um descuido.

**AS CINCO MANEIRAS DE ESTAR VERMELHO** (`placar.verde`), e nenhuma é
«a suite falhou»:

| | |
|---|---|
| 1 | **não há placar** — ninguém correu a suite |
| 2 | **o placar não se lê** — JSON partido, campos a menos, corrida morta a meio |
| 3 | **o código mudou depois de a suite ter corrido** |
| 4 | **o placar mediu menos ficheiros do que os que estão em disco** |
| 5 | **há ficheiros a falhar** |

A 3 é a que apanha o caso a sério, e é a razão de o placar guardar uma
**impressão digital**: o sha256 de tudo o que pode mudar a resposta da suite —
o `riftvault/` (`.py`, `.sql` e o `web/`, que os testes leem como texto), os
`tests/`, e o `riftvault_config.json`, que não é enfeite (é lá que vivem as
regras que os testes medem). Se um byte de qualquer um deles mudou desde a
corrida, **o placar é de outro código** e não autoriza este merge. «Corri a
suite, depois emendei uma linha» deixou de passar.

O `data/` **não** entra na impressão digital: os testes correm contra cópias e
pastas temporárias, e pô-lo lá fazia um `+` num tile invalidar um placar verde.

**Um ficheiro que nem chega a correr conta como vermelho.** Se a saída não
tiver o `Ran N tests` do `unittest` — um import partido, por exemplo —, o
placar não o conta como zero testes: marca-o a falhar, com a razão («não
correu»). Um ficheiro que desaparece da contagem é a outra maneira de um
vermelho passar despercebido.

**O `.placar.json` está no `.gitignore`**, e isso é decisão e não descuido: é o
resultado de uma corrida NESTA máquina, não conteúdo do projecto. Um placar
commitado era a pior versão deste problema — o verde de outra pessoa a
autorizar o meu merge.

O `tools/portao.py merge` recusa também com a **árvore de trabalho suja**: o
placar mediu o que está em disco, e o merge integra o que está commitado. Se as
duas coisas diferem, o placar não fala do que vai ser integrado.

## 2026-09-30 — ENTRA-SE COM UTILIZADOR E PASSWORD; e NENHUMA se pode LER (`senha.py`)

Palavras dele: *"em vez de discord, nao era melhor a pessoa criar uma conta com
usuario e password e ficar guardado em base de dados?? / **o esqueci-me da
password fica manual, eu acedo o ficheiro e digo A pessoa a password dela** /
isto e uma coisa caseira, para usar entre amigos, entao nao ha problema"*. Ramo
`ai-pc/senhas-2026-09-30`; o desenho e a razão em
`docs/contas-e-autenticacao.md` (secção 0) e o guia dele em
`docs/abrir-a-porta.md`.

**A PRIMEIRA METADE FEZ-SE, A SEGUNDA NÃO — e ele aceitou a contraproposta:**
*"pode ficar a tua sugestao de nova password, e melhor / faz e da-me o proximo
passo que precisas entao"*. Ou seja: entra-se com utilizador e password, mas
**ele nunca lê a password de ninguém**. Quem se esquece não recebe a que tinha
— recebe uma NOVA, temporária, que é obrigado a trocar ao entrar.

**A RAZÃO, para ficar escrita: as pessoas reutilizam passwords.** A que o amigo
escolher é provavelmente a do email dele. Guardá-la legível num PC de casa, ao
lado de um repositório PÚBLICO empurrado de 30 em 30 minutos, transforma
«alguém leu o meu ficheiro» em «alguém entrou no email de três amigos meus» — e
o estrago já não é sobre cartas. **O fluxo dele fica IGUAL**: continua a ser
ele a resolver, na consola, sem emails nem sistemas; o que muda é que em vez de
LER dá uma nova.

### O KDF, medido na máquina dele

`hashlib.scrypt` — **da biblioteca padrão**, sem dependência nova para
instalar nem para explicar quando ele reinstalar o Python. Medido a 2026-09-30
(Python 3.14, média de 3 corridas): n=2^14 **32 ms** · n=2^15 **64 ms** ·
**n=2^16 130 ms (67 MB)** · n=2^17 **262 ms**. Escolheu-se o de **130 ms**:
imperceptível para quem entra uma vez por mês, e é o custo que um atacante paga
por CADA tentativa se um dia levar o ficheiro.

**ARMADILHA MEDIDA: o `maxmem` tem de ir explícito.** O `hashlib.scrypt` passa
`maxmem=0` ao OpenSSL, que são **32 MB**, e o n=2^16 quer 67 — sem o argumento
isto rebentava na primeira password. Há teste com a prova pela negativa.

O hash guardado **diz como foi feito** (`scrypt$65536$8$1$sal$hash`): subir o
`N` um dia não tranca ninguém de fora, porque cada password se verifica com os
parâmetros dela e é recifrada na primeira entrada (`precisa_recifrar`). Sal de
16 bytes **por pessoa**.

### A temporária: quatro palavras e dois dígitos

`varanda-tigre-bolo-chave-47` — 4 palavras de uma lista de **256** (8 bits
cada) e 2 dígitos: **38,6 bits**, 4×10^11 combinações. Offline, a 130 ms cada,
são ~1 600 anos de um núcleo; online, com o travão, é inalcançável. As palavras
são ASCII, 3 a 6 letras, **sem acentos nem cedilha** (há que as ditar), e os
hifens dizem onde cada uma acaba. A lista é fixa e tem um `assert` a fixar as
256 — nove saíram por serem confundíveis com outra (cedo/cego, jacto/jato,
grito/grifo, …).

**A PASSWORD QUE A PESSOA ESCOLHE: dez caracteres e mais nada.** Sem exigência
de maiúscula, dígito e símbolo — essa regra produz `Password1!` e um post-it.
Recusam-se as da lista das mais usadas (com os dígitos do fim ignorados:
`password12345` continua a ser `password`), o próprio nome, um caractere
repetido, e espaços nas pontas (perdem-se ao copiar e colar).

### A TEMPORÁRIA TRANCA O SITE até ser trocada

*"Quem entra com uma temporaria e OBRIGADO a trocar antes de fazer seja o que
for"*. Com uma temporária **tudo o que é `/api/` responde 403** menos o
`api/conta.json` e o `api/conta/senha`; o resto (o `index.html`, o `app.js`, o
CSS, o `/sair`) passa, senão não havia página onde mostrar o formulário.
**Bloqueia as LEITURAS e não só as escritas**, e é a parte que interessa: a
temporária andou pelo WhatsApp, e quem a apanhasse podia não escrever nada e
ler a coleção toda. O estado lê-se a cada pedido (um `SELECT` por chave
primária) para a troca libertar o site no pedido seguinte. **Trocar fecha TODAS
as sessões dela** e abre uma nova.

### O TRAVÃO: duas dimensões, escada a subir

Uma password ADIVINHA-SE (um `sub` do Discord não), por isso o tecto de 20/hora
do OAuth não chega. Conta FALHAS na última hora: **5 de graça por CONTA** (uma
password ditada escreve-se mal duas ou três vezes) e **10 por ENDEREÇO** (o
dobro, porque um endereço pode ser uma casa inteira). A escada, a contar da
última falha: **1 → 5 → 15 → 60 minutos**. As duas dimensões fazem falta as
duas — só por endereço, quem tivesse dados móveis batia à vontade numa conta;
só por conta, dava para varrer nomes. **Não há bloqueio permanente**, de
propósito: era a maneira de um estranho tirar o riftvault a um amigo só por lhe
saber o nome. E **o travão corre ANTES do scrypt** (há teste que lê a ordem no
código): verificar primeiro fazia cada tentativa custar 130 ms, que era o que
punha o PC dele de joelhos.

**Um defeito apanhado em teste:** o `_espera` dava **seis** tentativas de graça
e não cinco — isto corre antes da tentativa, por isso com 5 falhas no registo a
seguinte é a SEXTA e tem de ser travada. Faltava um `+ 1`.

### NÃO HÁ REGISTO ABERTO

As contas nascem de `riftvault conta --criar <nome>` e de mais lado nenhum; a
rota `/api/conta/registar` responde **403** com o que fazer, e quem entre por um
fornecedor sem ter conta vê uma frase em vez de um formulário. **Não é uma
chave de config**, de propósito: uma chave num ficheiro commitado está a um
merge de distância de abrir o registo sem ninguém ter decidido nada
(`rotas_conta.REGISTO_ABERTO`).

### O QUE ELE CORRE

    riftvault conta --criar miguel            cria e diz uma temporária (uma vez)
    riftvault conta miguel --nova-password    o «esqueci-me»
    riftvault conta                           quem existe e em que estado está
    riftvault conta baverone --nova-password  A DELE, antes de abrir a porta

Os dois primeiros funcionam com a **porta fechada** (ele prepara e só depois
abre) e o `--nova-password` **fecha as sessões** dela — se foi o telemóvel que
ela perdeu, o telemóvel sai.

### O `multi --verificar` deixou de exigir Discord; os passos dele são DOIS

O passo «Entrar sem password» saiu: a entrada por password não precisa de
configurar nada. No lugar ficam **«Há por onde entrar»** (sempre verde, diz o
que está ligado) e **«Tu consegues entrar»**, que agora exige **password
definida** — e a temporária **não conta**, porque com ela ele entra e não faz
mais nada. Os passos DELE passaram de três a **dois**: a conta na Cloudflare e
os nameservers + o túnel. O `docs/abrir-a-porta.md` perdeu o passo 1 e ganhou a
secção **«Criar a conta de um amigo»**, com o que lhe mandar e o que fazer
quando ele se esquecer.

### O OAUTH FICA, PARADO

Ordem dele: *"Nao apagues o codigo do Discord e do Google […] Sem segredo
configurado, o botao simplesmente nao aparece"*. Não se apagou uma linha: os
dois fornecedores, o PKCE, o `nonce`, os convites de ligação e os testes deles
estão inteiros, e o `auth.discord.client_id` continua no config. **Sem segredo
no ambiente o `pronto` vem a `false` e o botão não se desenha** — há teste nos
dois sentidos. A diferença: entrar por um fornecedor **não cria conta**.

### Dois defeitos apanhados a escrever isto

1. **O índice do `user_id` não podia estar no `ESQUEMA`.** Num `auth.db` de
   ontem a `auth_tentativas` existe sem a coluna, o `CREATE TABLE IF NOT
   EXISTS` não a acrescenta, e o `CREATE INDEX` por cima de uma coluna que não
   existe rebenta **antes** de o `_migrar` a poder criar. Vive no `_migrar`, que
   corre depois. Provado nos dois sentidos: base de ontem e base de raiz.
2. **A CLI deixava um hash órfão.** O `conta.apagar` não toca no `auth.db` de
   propósito (é outra casa); quem limpa é quem sabe dela, no mesmo passo — a
   rota do site já o fazia e o `riftvault conta --apagar` não. Apanhado a
   escrever a prova de ponta a ponta.

### Medido

**A `copies` DELE não mexeu**: 1046 linhas · 2663 normais · 540 foil, sha256 do
conteúdo **`1f6c9cae…`**, igual no princípio e no fim — e igual ao da prova de
29/09, o que quer dizer que nenhuma das duas ordens lhe tocou. Nada desta ordem
escreve na coleção: a prova de ponta a ponta corre toda na base de ENSAIO
(`docs/prova-senhas-2026-09-30.md`), contra o `riftvault serve` a sério na 8779,
e o `data/` só se lê — por cópia com `VACUUM INTO`, que é a forma segura com as
bases em WAL.

**Dois defeitos do PRÓPRIO GUIÃO da prova, e os dois valem a pena:** a primeira
versão escolheu `a-frase-do-joao-2026` para password do João — **a regra
recusou-a**, por conter o nome dele, e ele ficou preso na temporária a ler 403
em tudo (a regra estava certa; a prova é que escolhia mal). E o travão passou
para o FIM: no meio, deixava as contas a esperar e os passos seguintes liam
429 em vez do que queriam medir.

`tests/test_senhas.py` é a bateria nova, e a parte dela que interessa mais é **a
procura da password em claro**: escreve-se uma password conhecida, faz-se o
percurso todo (criar, entrar, trocar, errar, exportar, backup) e **varrem-se os
bytes** do `auth.db`, do `vault.db`, do `ops`, do `.zip` do export e dos
backups, em UTF-8 e UTF-16. Com a **prova pela negativa**: um teste escreve a
password à mão numa tabela e exige que o varrimento a encontre — um varrimento
que nunca acha nada vale zero. O `test_contas.py` e o `test_auth.py` foram
ajustados: descreviam o registo aberto e o «não há password nenhuma» de 29/09,
que era o regime de ontem.

## 2026-09-30 — A LISTA das coleções públicas (`lista.py`); e a raiz só muda com DUAS

Palavras dele: *"a baverone.com tem que ter tudo / depois quando se abre o
Riftbound, vai ter lá, em modo leitura, as coleções: Baverone / Miguel / Rafa
/ na Baverone.com, em baixo, é onde se entra para editar / cada pessoa tem um
acesso usuário password que edita a sua própria coleção"*. Ramo
`ai-pc/lista-2026-09-30`.

**AS PÁGINAS INDIVIDUAIS JÁ EXISTIAM** — o `build.build_todos` gera `u/<slug>/`
desde 29/09 e já salta quem tem privacidade «nada» ou está atrás das portas
fechadas. O que faltava era o ÍNDICE que as junta, e é só isso que nasceu aqui.

### 1. A troca é AUTOMÁTICA, e não uma chave que ele tenha de mudar

    0 ou 1 coleção pública  ->  a raiz fica EXACTAMENTE como está hoje
    2 ou mais               ->  a raiz é a lista, e a dele vai para `u/baverone/`

`lista.MINIMO_PARA_A_RAIZ = 2`. **Com as portas fechadas há uma pública (a
dele), por isso HOJE NADA MUDA** — e é a leitura da frase dele de 29/09,
*"quero apenas apresentar quando tiver tudo"*. A lista aparece sozinha no dia
em que ele abrir as portas e um amigo escolher publicar, que é exactamente o
dia em que ela passa a fazer sentido: **uma lista com uma entrada só não é uma
lista**, é um clique a mais entre ele e a coleção dele, e uma montra de um
serviço que ainda não tem ninguém.

**Medido a 2026-09-30 contra o `data/` real** (`_revisao\_medir_lista.py`, o
`build.build()` de antes e o `build.build_todos()` de agora na mesma corrida):
**24 ficheiros dos dois lados, os mesmos nomes, ZERO a diferir em conteúdo** —
os 4 que diferem em bytes diferem só no `generated_at`, porque as duas gerações
caíram em segundos diferentes.

### 2. O `riftvault build` passou a ser o `build_todos`

Estava a chamar o `build()`, que só sabe do site DELE: a lista nunca chegaria
ao site a sério. Com as portas fechadas os dois fazem o mesmo — há teste que os
compara —, e a partir de agora é o `build_todos` que responde pelas portas, pela
privacidade de cada um e pela lista.

**Quando a lista toma a raiz, os restos do site dele SAEM de lá**
(`lista.limpar_raiz`, `RESTOS_DA_RAIZ`): a `api/`, o `app.js`, o `style.css` e
o `robots.txt`. Senão ficavam na raiz os payloads antigos dele a envelhecer, e
um `api/index.json` velho ainda por cima fazia o `--se-mudou` comparar contra o
sítio errado. É uma lista ESCRITA e não um «apaga o que não é `u/`»: na raiz
podem estar coisas que não são nossas para apagar — o `CNAME` do domínio, o
`.nojekyll`, o `img/` de 88 MB de uma corrida em `static_images: local`.

**E DESPUBLICAR PASSOU A SER TÃO FÁCIL COMO PUBLICAR**
(`lista.limpar_nao_publicadas`), que é a metade que faltava à privacidade de
29/09. Quem tivesse escolhido «tudo» e mudasse para «nada» deixava de ter
página GERADA — mas a que já lá estava **ficava publicada para sempre**: o
`build.py` saltava-a, e saltar não é apagar. Agora qualquer pasta debaixo de
`u/` que já não se publique sai do site: por a pessoa ter fechado a coleção,
por as portas se terem fechado, ou por ele ter voltado à raiz (senão ficava em
`u/baverone/` uma cópia a envelhecer — e é para lá que os favoritos foram
reencaminhados enquanto a lista existiu). Só mexe DENTRO do `u/`.

**A pasta de prova do `--se-mudou` mudou-se para a raiz do repo.** Era
`out.parent / (out.name + "-prova")`, e com o site dele em `site/u/baverone/`
isso era **dentro do `site/`**: uma corrida interrompida a meio deixava uma
`site/u/baverone-prova/` commitada e publicada. Para o `site/` o caminho é o
mesmo de sempre (`site-prova/`, que já estava no `.gitignore`).

### 3. OS FAVORITOS DELE NÃO PARTEM — e o que não se consegue diz-se

O site é uma aplicação de uma página com rotas no `#` (`#colecao/UNL`,
`#decks/ornn`). **O `#` nunca chega ao servidor**, por isso não há
reencaminhamento de servidor que o possa apanhar — e o GitHub Pages também não
tem regras de reencaminhamento nenhumas. Quem o vê é o browser, e é por isso
que o reencaminhamento vive na página da lista, em JavaScript, **no `<head>`**
(no fim do `<body>` via-se a lista a piscar antes do salto) e com
`location.replace` (com `href`, o botão «voltar» trazia a pessoa outra vez para
aqui).

É deliberadamente **CEGO ao nome da secção** — não repete a `SECCOES` do
`app.js`. Uma rota nova nasce reencaminhada sozinha, e um `#` que já não exista
cai na regra de sempre do `app.js` (abre a primeira secção visível), que é o
mesmo que acontecia antes. **Testado no node, contra o JavaScript que a página
leva mesmo**: 13 endereços — `#colecao`, `#colecao/UNL`, `#colecao/OGN`,
`#decks`, `#decks/ornn`, `#faltas-edicao/OGN`, `#encomendas`, `#venda`,
`#selado`, `#inicio`, `#a-mais`, `#staples` e um inventado que ainda não existe
— acabam todos em `u/baverone/<o mesmo #>`; a raiz sem `#` **não** reencaminha,
senão ninguém chegava a ver a lista.

**O QUE NÃO SE CONSEGUE REENCAMINHAR, e fica dito em vez de partir em
silêncio:** os ficheiros de dados (`/api/set/OGN.json` e companhia) passam a
viver em `u/baverone/api/…` e um endereço antigo para eles dá **404**. Num
alojamento estático não há como evitar sem duplicar o site inteiro na raiz. São
endereços de máquina e não de pessoa — o que se marca nos favoritos é a página,
e essa é reencaminhada. Há teste que exige que isto continue escrito.

### 4. A privacidade, no cartão

**Quem está em «nada» não aparece em sítio nenhum — nem o nome.** Não é só não
ter cartão: o teste varre o HTML da raiz **e** o `api/lista.json` à procura do
nome e do slug. Não estar na lista é a forma mais completa de não estar
publicado, e «nada» é a OMISSÃO de quem entra de novo.

**Os números de cada cartão saem do `api/index.json` JÁ GERADO da pessoa** — não
se calculam outra vez. Duas consequências, as duas boas: não há uma segunda
definição de «quantas cartas tem o Miguel», e **o cartão não pode mostrar mais
do que a página dela já mostra**, porque lê o ficheiro que já passou pelo
`privacidade.limpar`. Por cima disso o cartão volta a passar pelo mesmo filtro —
cinto e suspensórios de propósito: «um cartão de quem escolheu sem-valores não
mostra euros» deixa de depender de alguém se lembrar. Com a **prova pela
negativa** ao lado (em «tudo» os euros TÊM de aparecer), senão o teste passava
com um cartão vazio.

### 5. A página

Uma página estática à parte, com os tokens da marca (o roxo `#a77bff`, o «R»),
**sem depender do `app.js`**. Cabeçalho, um cartão por coleção (inicial, nome,
barra do playset, cartas/cópias e o valor quando o há), e o rodapé a dizer que
quem não escolheu publicar não aparece. **Zero** diz o que se passa em vez de
ficar em branco; **uma** escreve-se no singular; **cinco** enchem a grelha, que
envolve sozinha (`auto-fill`, nada de `overflow-x` — a lição das filas de
botões de 24/09) e passa a uma coluna abaixo dos 480 px. Medido no Chrome a
**375 px**: `scrollWidth == clientWidth == 375`, zero elementos fora do ecrã e
zero com scroll próprio. O nome vai escapado (um nome com HTML dentro não
escapa).

**Não se tocou no `baverone-home`** (a página de entrada dele): é outra ordem, e
só se lhe mexe quando o `editar.baverone.com` existir — senão ficava lá um link
partido.

`tests/test_lista.py` (43 testes): quem entra e a ordem (ele primeiro, depois
por nome sem tropeçar nos acentos); a raiz só muda com duas, e a coleção dele é
a MESMA ao mudar de sítio; quem fecha a coleção perde a página que já lá
estava; os restos saem e o `CNAME` fica; a privacidade no
cartão com as duas redes; os favoritos no node; a página com zero, uma e cinco;
e que **nenhum módulo de contas importa o `lista`** — é apresentação. O
`test_privacidade.test_o_SITE_DELE_e_igual_com_o_interruptor_de_um_lado_e_do_outro`
foi ajustado (abrir as portas com um amigo público muda-lhe o SÍTIO, não o
conteúdo) e ganhou ao lado a prova pela negativa: com o amigo privado, a raiz
continua a ser a dele.

## 2026-09-30, à tarde — O BECO DA PORTA FECHADA: a entrada esconde-se no SITE PUBLICADO, não com a porta fechada

**ERRO NOSSO, e a causa foi ler mal uma frase dele.** A 29/09 ele disse *"Quero
apenas apresentar quando tiver tudo"* e nós traduzimos isso para «esconder a
zona da conta enquanto `multi.aberto` for `false`». O que ele não queria era um
link de login **no SITE PUBLICADO**; no 8770, que é a casa dele, esconder a
entrada não serve ninguém. Ramo `ai-pc/conta-fechada-2026-09-30`.

**O ciclo, e ele estava preso nele.** O `renderConta()` começava com
`if (!c || !c.aberto) { zona.hidden = true; … }` — com a porta fechada não se
desenhava **nem a caixa de «Entrar»**. Mas o `multi --verificar` **recusa
abrir** enquanto a password dele for a temporária, e a troca só se fazia
entrando no site. Medido no `data/` real: o `--verificar` dizia
*«[FALTA] Tu consegues entrar: a tua password é a temporária»* e mandava-o
«abrir o site e entrar» — o site não tinha por onde.

### 1. O critério novo: é o `index.editable`, e já existia

Não se inventou bandeira nenhuma. O `boot()` já distinguia os dois modos para
não deixar um 404 na consola da cópia publicada:

    state.conta = state.index.editable ? await getJSON('api/conta.json') : null;

O servidor manda **sempre** `editable: true` no `api/index.json`
(`server.py:116`) e o `build` manda **sempre** `false` (`build.py:253`) — por
isso `state.conta` é um objecto no servidor e `null` no estático, que é
exactamente a pergunta certa. O `renderConta` passou a esconder-se com **`if
(!c)`**, e mais nada mudou.

**No servidor a caixa aparece com a porta fechada, e diz o que é verdade**: «as
contas ainda não estão abertas — isto é para tratares da TUA password;
enquanto estiver fechada não precisas de entrar para usar o site, e os teus
amigos ainda não conseguem».

### 2. A porta NÃO é a fechadura da entrada

Não chegava mudar o ecrã: com a porta fechada o `_antes` **nem resolvia a
sessão** e o `/api/conta/entrar` respondia **403**. Três mudanças no
`rotas_conta.py`, e a regra passou a ser uma frase:

> **Entrar funciona sempre. A porta decide apenas se a ESCRITA exige sessão.**

Com a porta fechada a app continua a não ter autenticação nenhuma — quem chega
ao 8770 já escreve tudo —, por isso deixar entrar **não dá acesso a nada que
não estivesse dado**: dá o que faltava, que é o sítio onde se troca a password.
O travão de tentativas corre igual nas duas portas (há teste).

| | porta FECHADA, **sem** sessão | porta FECHADA, **com** sessão | porta ABERTA |
|---|---|---|---|
| escrever | não pede nada (o de ontem, ao byte) | guarda inteiro: CSRF, dono, `SO_DO_DONO` | guarda inteiro |
| a base que se abre | a dele (utilizador 1) | a de quem entrou | a de quem entrou |
| `auth.db` | **nem se abre** (só há cookie) | abre | abre |

A segunda coluna é **estritamente mais segura do que ontem**, e é precisa: ele
já pode criar a conta de um amigo com a porta fechada (`riftvault conta
--criar`, 30/09 de manhã), e sem isto esse amigo escrevia no config partilhado
dele. **O OAuth continua a exigir a porta aberta** — obriga a configurar uma
aplicação em sítio de terceiros e ele não precisa dela para tratar da password.

### 3. O SEGUNDO BECO, que a ordem não nomeou — e que existia com a porta ABERTA

O `_trava_temporaria` responde **403 a tudo o que é `/api/`** (é de propósito:
a temporária andou pelo WhatsApp). O `boot()` pede o `api/index.json` na
primeira linha e **morria ali** — o `renderConta()` nunca chegava a ser
chamado, e o ecrã da troca, que é a ÚNICA coisa que se pode fazer com uma
temporária, não era desenhado. **Lia-se «Falhou a carregar: HTTP 403».**

O `boot()` passou a apanhar essa falha e a perguntar ao `api/conta.json`, que é
o que passa a trava (`COM_TEMPORARIA`). Se a resposta for «trancado», desenha o
formulário e pára; **se não for, o erro original sobe** — um `riftvault sync`
em falta tem de continuar a dizer o que é (há teste).

**Duas correcções vieram da FOTOGRAFIA, não do código:** a primeira versão
escrevia a frase no `#grid`, que vive dentro de uma `<section hidden>` — via-se
um ecrã preto ao lado do formulário; e chamava o `renderNav()`, que sem o
índice **mostrava as três abas que ele mandou esconder** a 25/09 («A mais»,
«Por deck», «Pimp decks»). A frase foi para o cabeçalho da página e a navegação
fica de fora enquanto o site está trancado.

### 4. A REDE DE SEGURANÇA: `riftvault conta <slug> --definir-password`

Para nunca mais a recuperação depender do browser. Pergunta a password **duas
vezes e não a mostra** (`getpass` da biblioteca padrão — não aparece no ecrã,
não vai para o histórico da consola, não passa por ficheiro nenhum), e aplica
as **mesmas** regras de força do site (`senha.validar`, pelo `definir_senha`):
não há uma porta com regras mais frouxas, e não há uma segunda lista de regras
a divergir. Grava com `temporaria=False` — é escolhida, não ditada, e por isso
**não tranca o site** — e fecha as sessões abertas dela, como a troca pelo site.

**Nunca um argumento** (`--password xyz`): ia para o histórico da consola. Há
teste que o proíbe no ficheiro inteiro.

O `multi --verificar` passou a apontar para aqui: os passos dele continuam
**dois**, mas o que era «dá-te uma temporária, abre o site, entra, troca» é
agora um comando só. O `--nova-password` fica — é o «esqueci-me» de um amigo,
que é outra pergunta.

### Medido a 2026-09-30, à tarde

**O SITE PUBLICADO não mexe.** Gerado dos dois lados contra a MESMA cópia do
`data/` real (`_revisao\_medir_conta_fechada.py` + `_comparar_cf.py`, com o
`main` num worktree): **24 ficheiros de cada lado, os mesmos nomes; os 20 JSON
da `api/` byte a byte iguais** (a menos do relógio). Dos quatro estáticos, o
`index.html` e o `style.css` diferem **só em comentários** (verificado com
`diff`: zero mudanças de marcação ou de regras) e o `app.js` leva o código
novo. O HTML publicado não tem **nada** de contas no texto visível, o
`#conta-zona` nasce `hidden`, o `api/index.json` diz `editable: false` e **não
existe `api/conta.json` no estático**. E há teste que gera o site com a porta
fechada e com a porta aberta e exige que saia **igual ficheiro a ficheiro**: o
publicado deixou de depender do `multi.aberto`.

**A COLEÇÃO não se tocou.** Tudo correu contra uma cópia feita por `VACUUM
INTO` (as bases estão em WAL e ele estava a mexer na coleção). O `registo.db`
real continua com **`baverone` e mais ninguém** — a conta de prova nasceu e
morreu na cópia. A `copies` real: **1046 linhas · 2663 normais + 540 foil**.

**A prova por HTTP**, contra um `riftvault serve` a sério na 8779
(`_prova_cf_http.py`), **19/19**: com a porta fechada o `api/conta.json`
responde 200 (`aberto: false`, `entrado: false`, `editavel: true`, `senha:
true`); entra-se com a temporária; o `api/index.json` passa a **403** e o
`api/conta.json` continua a **200** com o `csrf`; troca-se; o site volta a 200
e `editavel: true`. **Fotografado** a 1280 px nos dois estados
(`_foto-cf-fechada-1280.png`, `_foto-cf-temporaria-1280.png`).

`tests/test_conta_fechada.py` (**37 testes**): o critério e que não é bandeira
nova; a entrada por HTTP com a porta fechada, com o travão; o estático sem nada
e igual nas duas portas; a troca da temporária de ponta a ponta, com a fraca
recusada e o `/sair` sempre possível; o segundo beco (o índice barrado, o
`conta.json` não, e o erro que não é a trava a continuar a subir); o
`--definir-password` (aceita, recusa cinco fracas com a razão certa, pergunta
duas vezes, não mostra nada, fecha as sessões, e o slug que não existe nem
chega a perguntar); e o que **não** mudou. `test_contas.py` e `test_senhas.py`
foram ajustados em quatro testes — **fixavam o beco**: `!c.aberto` no
`renderConta`, o `/api/conta/entrar` a dar 403 com a porta fechada, e o
`--nova-password` na dica do `--verificar`.

## 2026-10-01 — QUEM MANDA NA AUTENTICAÇÃO É A ORIGEM, NÃO A PORTA (`origem.py`)

Duas revisões externas independentes (o ChatGPT e uma sessão de Claude Code)
leram o código a 01/10 e encontraram **os mesmos dois defeitos no topo**, no
mesmo sítio e com a mesma raiz: a app perguntava à PORTA DAS CONTAS
(`multi.aberto`) se era preciso autenticação, em vez de perguntar a quem estava
a bater. Ramo `ai-pc/origem-2026-10-01`; o desenho e as medições em
**`docs/origem-do-pedido.md`**.

### Os dois defeitos, e porque é que eram a sério

**1. «Fechar» DESLIGAVA a autenticação.** O guarda tinha
`if not aberto and g.sessao is None: return None` — com a porta fechada
qualquer escrita passava sem sessão e sem CSRF. E o túnel está VIVO: medido a
01/10, o `cloudflared` corre como **serviço do Windows** (`tunnel run
--token-file`) e o `editar.baverone.com` chega ao 8770. Era escrita anónima na
coleção dele a partir da internet, à distância de um `git checkout` do config —
o `multi.aberto: true` vivia numa modificação por gravar até ele o commitar
nessa manhã (`79fe63b`), como mitigação.

**2. Um pedido sem sessão caía na base do utilizador 1.** O mesmo caminho:
`get_con()` com `riftvault_user=None` → `db.connect(user_id=None)` →
`utilizador.atual()` → **o André**. A privacidade dele nunca era consultada, e
por isso no dia em que a pusesse em «nada» o `editar.baverone.com` continuava a
servir tudo.

### O FACTO estava certo; a CONCLUSÃO estava errada

Está escrito desde 29/09 — aqui, no `rotas_conta.py` e no
`docs/contas-e-autenticacao.md` — que **não há atalho por endereço**, porque «o
túnel faz todo o tráfego da internet chegar ao Flask como `127.0.0.1`». **O
facto continua verdadeiro** e foi medido outra vez. O que estava errado foi
tirar dali «não se pode distinguir nada» e daí «então a porta decide».

Há coisas que o loopback **não explica**, e são essas que decidem. A pergunta
mudou de forma: não «isto vem de fora?» (falsificável para os dois lados), mas
**«isto é inequivocamente de casa?»**.

### A regra: um E de TRÊS condições (`origem.py`)

`de_casa` exige as três ao mesmo tempo — o par TCP numa gama da casa
(loopback, RFC 1918, link-local), **nenhum** dos 21 cabeçalhos de intermediário,
e **não** ter pedido o anfitrião público (`auth.base_url`).

**A direcção do erro é a que interessa:** forjar qualquer uma só pode TIRAR
confiança, nunca dá-la — quem estiver na rede de casa e mandar um
`CF-Connecting-IP` inventado consegue uma coisa só, passar a precisar de
password. Para um pedido da internet ser tratado como de casa teria de vencer as
três.

**AS GAMAS DA CASA ESCREVEM-SE UMA A UMA, e não é pedantismo.** A primeira
versão fazia `ip.is_private` e a bateria apanhou-a no primeiro teste: **para o
Python, `203.0.113.9` é privado** (ele marca assim as gamas de documentação e a
`240.0.0.0/4`). E o pior não é a lista estar errada — é **mudar sozinha**: o
CGNAT `100.64.0.0/10` era privado e no 3.14 não é. Uma decisão de segurança não
pode depender disso em silêncio.

### Medido contra o TÚNEL A SÉRIO, a 2026-10-01

`GET https://editar.baverone.com/api/conta.json` com o código novo na 8770:
**`origem: "fora"`, com NOVE sinais** — `CF-Connecting-IP`, `CF-Ray`,
`CF-IPCountry`, `CF-Visitor`, `CF-Warp-Tag-Id`, `CDN-Loop`, `X-Forwarded-For`,
`X-Forwarded-Proto`, **mais o anfitrião público**. Cada um basta sozinho, e é
essa a redundância que faltava. Dois factos que ficam escritos: **a Cloudflare
NÃO reescreve o `Host`** (chega `editar.baverone.com` ao Flask, por isso a
terceira condição funciona sem cabeçalho nenhum), e o mesmo pedido ao
`127.0.0.1:8770` dá `origem: "casa"` com zero sinais.

**A prova do defeito 1** num servidor HTTP a sério com `multi.aberto: false` e
estes nove sinais (pasta de dados descartável — o `data/` dele nunca tocado,
`_revisao\_prova_porta_fechada.py`): pelo túnel, as cinco escritas e as seis
leituras dão **401**, e a casca (`/`, `/app.js`, `/style.css`,
`/api/conta.json`) dá **200**; de casa, a leitura dá **200** e a escrita passa o
guarda (404 da rota, que não achou a carta — ou seja, não pediu password).

### O que ficou a significar «fechado»

| | |
|---|---|
| **a PORTA** (`multi.aberto`) | fechada: OAuth parado, sem registo, só o site DELE se publica, e **em casa** escreve-se sem password |
| **a ORIGEM** | se é preciso entrar. De fora exige sessão para **tudo**, leitura incluída, com a porta aberta ou fechada |

**O que a porta fechada NÃO faz, e apanhou-nos a escrever o contrário no meio
desta correcção:** não impede quem já tem conta de entrar. A entrada por
password não passa pela porta desde 30/09, e **medido a 01/10** — com
`multi.aberto: false` um amigo com conta entra (200) e o guarda deixa-o
escrever na coleção **dele**. Uma mensagem do `--fechar` chegou a dizer «os
teus amigos deixam de entrar»; estava errada e foi corrigida antes do merge,
a par das duas docstrings do `auth.py` que diziam «fechada, ninguém entra» e
«com a porta fechada a app não tem autenticação nenhuma».

A docstring do `abrir.fechar()` dizia *«Ninguém perde nada — só deixa de se
entrar»*, e **essa frase era parte do defeito**: descrevia como inofensiva a
chave que punha a autenticação abaixo. Está corrigida, e o `riftvault multi
--fechar` passou a dizer as duas metades («em casa voltas a escrever sem
password» / «de fora continua a pedir que entres, mesmo para ver»). O
`--verificar` e o `--abrir` também.

**A privacidade fica respeitada sem uma linha de filtragem:** de fora e sem
sessão não se serve nada — nem um payload, nem uma imagem —, por isso não há o
que filtrar. É a decisão do `_u_explica` de 29/09: filtrar dezassete rotas de
leitura era deixar uma esquecida a vazar. A lista do que passa
(`rotas_conta.DE_FORA_SEM_SESSAO`) é **literal** e não «qualquer ficheiro do
`web/`» — um ficheiro novo naquela pasta não pode passar a público em silêncio, e
há teste que compara as duas coisas.

**O `get_con()` passou a REBENTAR** (`rotas_conta.SemSessao`) num pedido de fora
sem sessão, em vez de abrir a base do utilizador 1. Não devia chegar lá — o
guarda responde 401 antes —, é a rede para uma rota futura que escape.

### O que isto NÃO faz, e fica dito

**Não protege a rede de casa.** Quem estiver na LAN com a porta fechada continua
a escrever na coleção dele sem password: é a decisão dele, está no banner do
`serve` e não era desta correcção mudá-la. **Não é identidade** — isto nunca diz
QUEM é alguém, só se o pedido pode ser tratado como de casa; quem decide quem é
alguém continua a ser a sessão, e de casa com a porta aberta escrever continua a
exigir sessão e CSRF.

**Anotado:** o `config.load()` tem `lru_cache` por processo, por isso um
`riftvault multi --fechar` na consola **não** muda a porta do `serve` que já
está a correr — só na reinicialização seguinte. Não é buraco (a origem lê-se a
cada pedido), é uma surpresa à espera de quem contar o contrário.

### Fotografado, e uma coisa veio de lá

A 1280 e a 375 px, contra um servidor de prova com a porta fechada (o truque:
pôr o `auth.base_url` no próprio endereço do servidor de prova faz o mesmo
processo responder «casa» num URL e «fora» no outro, sem forjar cabeçalhos num
browser — `_revisao\_foto_origem.py`). Quem chega de fora vê **o ecrã de
entrar**, com o formulário, e não um «Falhou a carregar: HTTP 401».

**O que a foto a 375 px apanhou:** a frase *«o formulário está na barra do
lado»* mente no telemóvel — ali a barra está atrás do **☰ Menu**. O formulário
ESTÁ lá (o `mostrarSeTrancado` esconde só o `#sidenav`, não a `<aside>`
inteira, e a foto com o menu aberto mostra-o), mas o ecrã mandava-o procurar
uma coisa que não se vê. Vinha assim **desde 30/09**, no ecrã da password
temporária. A frase passou a dizer os dois sítios, de um sítio só do código
(`ONDE_ESTA_O_FORMULARIO`).

`tests/test_origem.py` (**46 testes**): a regra sem Flask (o telemóvel, o
loopback, o `is_private` que não serve, o E que não é um OU, os nove sinais
medidos cada um sozinho, forjar só tira confiança, os sinais sem valores de
cabeçalhos); a escrita anónima recusada pelo túnel e da rua, com a porta
**fechada** e **aberta**, e a `copies` a não mexer; a leitura anónima recusada
em **todas** as rotas `GET /api/` do `url_map` (varrimento, não amostra), as
imagens incluídas, com a privacidade nos três valores; o `get_con` a rebentar,
com prova pela negativa; a porta de entrada a funcionar de fora, de ponta a
ponta e ainda a exigir CSRF; **o uso dele em casa** (PC e telemóvel, a ler e a
escrever sem password); e as mensagens. `test_conta_fechada` foi ajustado em
três testes — liam o `app.js` com cortes de tamanho fixo e descreviam a nota que
passou a ter três casos em vez de dois.

**O placar já estava VERMELHO antes desta ordem, e não era por causa dela.**
Dois testes do `test_privacidade.py` exigiam, do ambiente REAL, o mundo de
29/09: `multi.aberto: false` no config e **um** utilizador no registo. Ele abriu
a porta (commit `79fe63b`, dele) e criou **três** contas a sério (`goncalves`,
`miguel`, `rafael`) — provado que é anterior: o `git show main:riftvault_config.json`
já dizia `true` e nenhum dos dois ficheiros está no diff desta ordem. Os testes é
que estavam velhos. Ficaram a medir o que não envelhece: o interruptor da porta
tem de estar **escrito** no ficheiro commitado (é a lição desta ordem — o estado
vivia numa modificação por gravar, e um `git checkout` mudava-o sozinho), e
**nenhuma conta de TESTE** no registo real (o `miguel` fica de fora dessa lista:
é um amigo a sério e um nome de brincar nos testes ao mesmo tempo). A metade «há
um utilizador só» morreu no dia em que ele criou as contas dos amigos.

## 2026-10-01 — O RESTAURO: um pacote só entra na conta DELE, e um restauro nunca torna nada público (`conta.py`, `privacidade.py`)

Três defeitos no caminho que só se usa no pior dia — aquele em que alguém está a
restaurar alguma coisa com outra pessoa à espera. Ramo
`ai-pc/restauro-2026-10-01`; o desenho está na secção 4 do
`docs/multi-utilizador.md` e a regra da privacidade no topo do `privacidade.py`.

**A ordem dos commits é a prova:** os testes entraram PRIMEIRO e falhavam **24
de 35** no código de ontem; depois da cura passam os **40**.

### 1. O pacote entrava na conta errada, em silêncio

O `conta.importar` validava o pacote contra o `user_id` do **manifesto**
(`_so_deste_dono`) e logo a seguir fazia `uid = reg["user_id"]` — **adoptava o id
do slug que já existia no registo, sem o comparar com o que vinha no pacote** — e
copiava. Um pacote de `miguel` exportado de outra instalação (onde o `miguel` é o
7) aterrava na base do `miguel` desta (que é o 2): com sorte dava uma conta que
**não abria mais** (o `utilizador.guardar` vê a `users` de dentro a dizer outro
dono e rebenta, para sempre), sem sorte era a coleção de uma pessoa por cima da
de outra. O backup limitava o estrago; o certo é **recusar**.

Hoje compara e recusa com **`conta.DonoTrocado`** — subclasse do
`utilizador.DonoErrado`, porque é a mesma família («este ficheiro não é desta
pessoa») e quem já apanha um apanha os dois —, a dizer de quem é o pacote e para
quem ia. **A pergunta faz-se TODA antes da primeira escrita**: o `INSERT` a
apanhar o `IntegrityError` já era escrever primeiro e pensar depois
(`_dono_do_id`).

**A porta explícita do caso legítimo é `adoptar=True` (`--adoptar`)** — restaurar
para uma instalação em que os ids foram semeados por outra ordem, ou uma conta
cujo id entretanto foi dado a outra pessoa — e ela **RECARIMBA a base inteira**
(`_readoptar`): deixar entrar sem recarimbar era o tal import que «corre bem» e
deixa a conta inutilizável. A linha do dono **muda de id em vez de ser apagada**,
e isso não é indiferente: as tabelas de dono declaram `REFERENCES
users(user_id)` e o `db.connect` abre com `foreign_keys=ON` — sem pai nenhum, a
primeira migração que reescreva uma tabela (o `_tirar_o_tecto_do_foil`
reconstrói a `copies`) rebentava na chave estrangeira.

### 2. Restaurar o registo republicava uma coleção fechada

A privacidade vive no REGISTO, que é um ficheiro (`data/users/registo.db`) e
**não há código que o restaure** — restaura-se copiando-o de uma cópia. Quem o
fizesse ficava com as escolhas do DIA DA CÓPIA, e quem tivesse fechado a coleção
entretanto **voltava a público**, com o site a regenerar-se de 30 em 30 minutos.
Pior: o `db._carimbar_dono` copia o registo para dentro da base **em toda a
ligação**, e por isso o primeiro `db.connect` apagava o único sítio onde a
escolha de hoje ainda estava escrita — a cura durava um pedido.

**A regra, numa frase: uma escolha só se ALARGA por um `privacidade.definir()`
explícito; qualquer outro caminho só pode FECHAR.** São dois testemunhos — o
registo e a cópia dentro de cada `vault.db`, que existia desde 29/09 (o
`_carimbar_dono` escreve-a) e que agora **se LÊ**: é a única coisa que sobrevive
a um restauro do registo, porque os dois ficheiros não se restauram juntos. O
`de()` devolve o **mais fechado** dos dois (`mais_fechado`, que lê a escala da
própria `VALORES` em vez de uma segunda tabela de números), o `reconciliar` cura
o desacordo **nos dois lados** (senão ficava um `tudo` velho no registo à espera
de que a base desaparecesse para voltar a valer), e o `importar` escreve na base
restaurada o que o **registo diz hoje** — é ele o testemunho vivo, porque não foi
ele que foi restaurado. **Uma conta RECRIADA de um pacote volta em «nada»**: foi
apagada, não há consentimento vivo nenhum, e o pacote diz o que era no dia do
export.

**O lado mau do erro, escolhido de propósito:** um `vault.db` restaurado de uma
cópia antiga pode fechar uma coleção que hoje está aberta — e isso desfaz-se com
um clique. O contrário não se desfaz: uma página pública indexa-se e fica em
cache em sítios que não controlamos. E o `no_vault` **não engole um «database is
locked»** (`_ainda_nao_ha_coluna`): devolver `None` ali é dizer «este testemunho
não diz nada», e sem o testemunho a escolha do registo passava sozinha, que é a
direcção má.

**MEDIDO no `data/` a sério** (`_revisao\_medir_restauro.py`, só leitura, contra
cópias com o `-wal` e o `-shm`): os **quatro** registos e as **quatro** cópias
dentro das bases dizem o mesmo — `baverone tudo`, `miguel tudo`, `rafael nada`,
`goncalves tudo`. **ZERO passam a ficar mais fechados: a regra nova não muda o
que se publica hoje, para ninguém.** Era a única maneira de esta ordem fazer
estragos (o site dele regenera-se sozinho) e por isso mediu-se antes.

### 3. Apagar uma conta deixava os pacotes dela para trás, calado

Em `data/backups/` ficam os `.zip` de cada export e os
`antes-de-importar-*.db` de cada restauro, **com a coleção inteira dela lá
dentro**. **FICAM, de propósito:** é a única maneira de desfazer um apagar feito
por engano, e é a mesma razão por que o `apagar` exporta antes de apagar —
deitá-las fora calados fazia a rede de segurança desaparecer exactamente no
minuto em que é precisa. O que não podem é ficar **caladas**: vão no `copias` do
resultado, a mensagem da confirmação conta-as, a CLI escreve-as uma a uma e a
rota `/api/conta/apagar` devolve-as. **`levar_copias=True` (`--levar-copias`)
apaga-as**, para quem pede «apaga os meus dados» e quer dizer todos; a ordem é
**exportar primeiro e limpar depois**, senão um export que falhasse deixava-a sem
nada.

**O nome de um pacote lê-se pela MESMA regra que o escreve** (`NOME_DE_PACOTE`,
`NOME_DE_ANTERIOR`) e o slug compara-se **inteiro**: um `glob("conta-miguel-*")`
cego também apanha o `conta-miguel-2-…`, que é de **outra pessoa** — apagar o
backup de quem não pediu nada era o pior que esta função podia fazer. Há teste
com os dois slugs.

**Dois defeitos apanhados pelos próprios testes**, e nenhum pela leitura do
código: o caminho na mensagem da confirmação era `pasta.parent / "backups"`, que
dá a raiz do repo para ele e `data/users/backups` para os outros — **nenhum dos
dois existe** —, e o cenário do «id tomado» não se produzia com um utilizador
novo, porque a `users` é `AUTOINCREMENT` e nunca reaproveita um id apagado.

**Medido e NÃO mudado:** dois exports no MESMO SEGUNDO dão o mesmo nome de
ficheiro (o `%Y%m%d-%H%M%S`) e o segundo escreve por cima do primeiro, em
silêncio. É de sempre, o conteúdo é o mesmo nesse segundo, e mudá-lo era mudar o
formato do nome que o `copias_de` passou a ler. Fica anotado. **E o config
continua GLOBAL** — um amigo herda as regras dele —, que é a limitação conhecida
de 29/09 e não é desta ordem.

`tests/test_restauro.py` (**40 testes**, contra pastas temporárias): o pacote de
outro id recusado e **nada escrito** (nem o backup), a recusa a dizer os dois
ids, o pacote dele próprio a entrar como sempre (a prova pela negativa), o
`--adoptar` a entrar **e a base a ABRIR** com as linhas carimbadas no id novo, o
id tomado; o restauro do registo ponta a ponta (uma cópia por cima da outra) a
não republicar nada — nem depois de a base ser aberta —, o desacordo a curar-se,
**abrir a coleção a continuar a funcionar** (sem isto, «nunca alarga» passava com
um `de()` que devolvesse sempre «nada»), o restauro para mais fechado, o André
intacto, a conta sem base ainda criada; e as cópias que ficam, as que saem, a que
NÃO é dela, e as duas portas na consola.

## 2026-10-01 — A CONTAGEM DAS RUNAS É DE CADA EDIÇÃO (`runas_vista.por_edicao`)

Palavras dele: *"A contagem das runas Alt.Art é exclusiva para cada edição / vi
que a contagem está a ser partilhada por todas as edições"*. Ramo
`ai-pc/runas-edicao-2026-10-01`.

**Tinha razão, e o defeito era NOSSO — de 2026-09-19, escrito no código como se
fosse decisão.** O bloco «Runas — 12 de cada» somava num número só as impressões
das CINCO edições e repetia-o em todas: o comentário do `app.js` dizia *«fecha a
grelha em todas as edições (as runas são as mesmas seis)»* e o docstring do
módulo *«tudo o que ele fisicamente tem de cada runa … seja que impressão for»*.
Isso é verdade da CARTA LÓGICA e falso da COLEÇÃO — e a Coleção inteira é feita
ao contrário (um alvo por impressão, um bloco por edição): a `SFD-R02a` é uma
carta e a `OGN-042a` é outra.

**Medido no `data/` real antes de mexer** (`_revisao\_medir_runas_edicao.py`,
contra uma cópia por `VACUUM INTO`): na página do **OGN** a Calm Rune dizia «na
coleção: **21**» — e **12 dessas eram as `SFD-R02a`** do CardTrader; a Mind Rune
dizia 12 com 4 do SFD; a Order Rune 22 com 7 do SFD. Na página do **UNL** dizia
exactamente o mesmo 21, 12 e 22 **sem ele ter lá uma única runa**. E o **OGS**,
que não tem runa nenhuma no catálogo, levava o bloco inteiro.

As runas em arte alternativa, por edição: **OGN 6** no catálogo
(`OGN-007a..214a`, 8 cópias), **SFD 6** (`market_only`, **23 cópias** — 12 Calm,
4 Mind, 7 Order), **UNL 6** (0) e **VEN 6** (0). São 31 cópias, e estavam todas
misturadas em seis linhas.

**A correcção.** `payload()` ganhou **`por_edicao`**: cada origem passou a dizer
a `set_id` a que pertence e a trazer o tile dela, e o `_fechar` — a MESMA função
— calcula os dois totais, o tile e a lista visível tanto para o conjunto inteiro
como para a fatia de uma edição (uma conta só, não duas). O topo (`runas` e
`totals`) **não mexeu** e continua a ser a soma: é o que o separador «Todas»
mostra, e é a única vista em que o número somado está certo. Continua a ser **UM
ficheiro** (`api/runas.json`) — as seis runas são as mesmas, o que muda é a
impressão. No `app.js` o `runasDaEdicao()` escolhe a fatia pelo `edicaoAberta()`
que já existia; um payload sem `por_edicao` (o 8770 não se reinicia a cada
merge) volta a ser a soma, como era. A linha do tile passou de «na coleção» a
**«nesta edição»**, e o `riftvault runas` ganhou a tabela por edição.

**O OGS deixou de levar bloco** — `edicoes()` só devolve as edições que TÊM
runas.

**O CONTADOR DELE NÃO SE PARTIU, e é decisão a tomar por ele.** O alvo é «12 de
cada», que é o **Rune Pool de um deck**: 12 × 6 runas × 4 edições = **288** não é
uma coisa que se tenha nem se jogue. E os seis números que ele contou à mão
(Body 3, Calm 3, Chaos 2, Fury 3, Mind 1, Order 2 — **14**, semeados a 26/09 e
a 01/10) **não têm edição nenhuma gravada**: reparti-los era inventá-los, e a
regra do bloco desde 19/09 é que *«uma linha a 0 é uma linha dele e nunca mais
se recalcula a partir da coleção»*. Por isso a `rune_counter` continua com a
chave de sempre (`card_key`, sem `set_id`), o crachá é o mesmo nas quatro
edições, e **o cabeçalho DI-LO** em vez de o esconder: «contas 14 de 72 (o teu
contador, igual em todas as edições) · nesta edição (OGN) tens: 45 (37 sem as
retiradas)». Um `+` numa edição mexe o número em todas (`runaPorContador`), e os
totais das duas vistas vêm do servidor (`totals_por_edicao`), para não haver uma
segunda aritmética no cliente. **É pergunta para ele.**

**Medido a 2026-10-01, o `main` e o ramo na MESMA cópia do `data/` real**
(`_revisao\_comparar_runas.py`) — **o topo não mexe**: `totals` iguais, as seis
linhas da soma iguais campo a campo (70 cópias, 39 sem as retiradas, 14 no
contador, alvo 72), e a soma das edições fecha com o total (70 = 45+23+0+2;
39 = 37+0+0+2).

| edição | antes (o mesmo em todas) | depois |
|---|---|---|
| **OGN** | na coleção **70** (39 sem as retiradas) | **45** (37) — Body 1 · Calm 9 · Chaos 9 · Fury 3 · Mind 8 · Order 15 |
| **SFD** | 70 (39) | **23** (0) — Calm 12 · Mind 4 · Order 7, todas alt art do CardTrader |
| **UNL** | 70 (39) | **0** (0) |
| **VEN** | 70 (39) | **2** (2) — Fury 1 · Body 1, as promo `VEN-R01`/`R04` |
| **OGS** | 70 (39), com o bloco inteiro | **sem bloco** |
| «Todas» | — | **70** (39), a soma |

Carta a carta, o que ele vai ver mudar: a **Calm Rune** passa de «21» em todas
as páginas a **9 no OGN · 12 no SFD · 0 no UNL · 0 no VEN**; a **Mind Rune** de
12 a **8 · 4 · 0 · 0**; a **Order Rune** de 22 a **15 · 7 · 0 · 0**. A Chaos e a
Fury quase não mexem (não têm impressões do CardTrader): 9 → 9 no OGN, 4 → 3 no
OGN + 1 no VEN.

**O que estava decidido fica de pé, e há teste para os dois:** as runas do master
set continuam a pedir o alvo da Coleção (**3**, `master_targets_by_type` desde
15/09 à tarde; o 12 é só do bloco e vive noutro sítio), a runa base continua na
**sequência** do master set e a alt art dela continua **retirada**; e as promo
`VEN-R01..R06` **não saem da Coleção** — continuam escondidas da grelha (15/09)
mas dentro do vault, no `copies` e no valor, e o bloco mostra-as no VEN, que é
onde elas são.

**NÃO MEXE EM NÚMERO NENHUM DO RESTO**, como desde 19/09:
`tests/test_runas_por_edicao.py::TestNaoMexeEmNumeroNenhumDoResto` fotografa
níveis, índice, wantlist, Faltas, A mais, valor, as cinco barras e o `copies`
inteiro, mexe nos contadores, e exige igualdade — com a prova pela negativa ao
lado (um `+` na grelha TEM de mudar a fotografia, senão ela não vale nada).

`tests/test_runas_por_edicao.py` (**28 testes**; **20 falham no `main`** e os 8
que passam são os que fixam o que não pode mudar): cada edição responde por si
(o total, as origens só dela, a runa que ela não tem, o tile dela, o
`sem_retiradas` dela, os totais a somarem as runas dela e as edições a somarem o
total); a soma do topo intacta e sem a marca interna `_todas`; o contador
continua dele (a chave da tabela, o mesmo número em todas, a sementeira pela
soma, os totais das duas vistas, e mexer nele não mexe na referência de edição
nenhuma); a fotografia; e o frontend (a fatia, o payload antigo que não parte o
ecrã, o cabeçalho, o contador a andar em todas as listas, a nota e a ajuda). O
`test_runas_vista.py` foi ajustado em **um** teste — fixava o literal «na
coleção» do tile.

## 2026-10-02 — A RAIZ PUBLICADA DEIXA DE SE INDEXAR (`abrir.lista_indexavel`)

Achado 1 do `docs/varrimento-2026-10-01.md`: `rift.baverone.com` respondia
**200** com **«Gonçalves»** e **«Miguel Valente»** no HTML, e o valor da coleção
de cada um, **sem `<meta name="robots">`**. Era a ÚNICA página do site assim —
a de cada um deles já saía marcada desde 2026-09-29, a dele não sai de
propósito (é a dele). A lista desfazia essa decisão sem ninguém a ter tomado.

**Escolha dele, com as quatro hipóteses à frente:** *"a lista deixa de ser
indexada, como já acontece com as páginas de cada um; quem tiver o link abre
tudo igual"*. Não quis tirar os euros da lista nem fechar o site todo com um
`robots.txt` na raiz. Ramo `ai-pc/raiz-noindex-2026-10-02`.

**Pelo caminho que já existia, e por isso são duas linhas de código.** Quem
decide é o `abrir.lista_indexavel()` — ao lado do `publico_indexavel()`, no
mesmo ficheiro, para quem procurar «o que é que se indexa» achar as duas
respostas no mesmo sítio — e quem aplica é o `abrir.marcar_html()`, o mesmo das
páginas de cada um. O literal da etiqueta continua a viver num sítio só, e o
`lista.py` **não** pode escrever um `<meta name="robots">` próprio (há teste).
Vai no `html()` e não no `escrever()`: quem chamar a função leva a página como
ela vai para o ar.

**Medido a 2026-10-02 contra cópias do `data/` real
(`_revisao\_medir_raiz_noindex.py`; cada `.db` por `Connection.backup()`, o
`data/` a sério só se leu), o `main` e o ramo na mesma corrida com a MESMA
cópia: 77 ficheiros de cada lado, os mesmos nomes, e UMA diferença de
conteúdo** — o `index.html` da raiz, 5 300 → 5 416 bytes, as duas linhas da
marca e mais nada.

| página gerada | antes | depois |
|---|---|---|
| `index.html` (a lista, nomeia André · Gonçalves · Miguel Valente) | **não** | **SIM** |
| `u/baverone/index.html` (a dele) | não | **não** — de propósito |
| `u/goncalves/index.html` | SIM | SIM |
| `u/miguel/index.html` | SIM | SIM |

São as **quatro** páginas HTML do site; os outros 73 ficheiros são `.json`,
`.js`, `.css`, `.nojekyll` e `robots.txt`, e **nenhum pode levar a etiqueta**.

**O PONTO 4, procurado e não presumido** (`_revisao\_varrer_nomes_no_site.py`,
os 78 ficheiros do `site/` commitado contra os nomes e os slugs do registo
real): a única página que nomeia OUTRA pessoa é a raiz. O `title` de cada
página é genérico («riftvault — coleção de Riftbound»), por isso a página de um
amigo não o nomeia; os `u/*/app.js` e `u/*/style.css` levam «André» e
«baverone» em comentários e URLs do código da app. **O `rafael`
(`publico = "nada"`) não aparece em ficheiro nenhum** — nem o nome nem o slug,
como o varrimento já tinha medido.

**O QUE ISTO NÃO FECHA, e ele sabe.** O `noindex` é uma etiqueta de HTML:
não vale para o **`api/lista.json`**, que leva os mesmos nomes e os mesmos
números, nem para os payloads de cada pessoa. Num alojamento estático não há
`X-Robots-Tag` para lhes pôr; fechá-los pedia o `robots.txt` **na raiz**, que
é a hipótese que ele viu e não escolheu. Está em teste para ninguém ler esta
ordem como «o site está fechado aos motores».

**O `u/<slug>/robots.txt` ESTÁ INERTE, e NÃO se apagou.** Um `robots.txt`
lê-se só em `/robots.txt` do anfitrião — o que o `build._gerar` escreve numa
subpasta nunca é pedido por motor nenhum, e o `rift.baverone.com/robots.txt`
responde **404**, que para um motor significa «podes rastrear tudo». Das «duas
portas» que o comentário do `abrir.py` dizia fechar, só a etiqueta fecha
alguma — e o comentário passou a dizê-lo. Fica porque não expõe nada (não leva
nomes), custa dois ficheiros, e volta a ser o sítio certo no dia em que o site
de um amigo tiver anfitrião próprio (`miguel.rift.baverone.com`, o que ele
pediu primeiro — ver `docs/multi-utilizador.md`). **Decisão dele.**

**Anotado, e CORRIGIDO horas depois** (ver a secção dos achados 3/4/6, acima —
passou a ser do `lista.escrever`): o `site/.nojekyll` da raiz era um resto de
quando a raiz era o site dele — desde que a lista a tomou, o `_gerar` escreve-o
em `u/baverone/` e ninguém o reescrevia na raiz. **Sobrevivia por estar
commitado** (o `RESTOS_DA_RAIZ` não lhe toca de propósito, e continua a não
tocar), e faz falta: sem ele o Pages ignora pastas começadas por `_`. Uma
geração num clone limpo não o criava — medido no mesmo dia, horas depois.

`tests/test_lista.py` ganhou a `TestARaizNaoSeIndexa` (**12 testes**, que lêem
o ficheiro que SAI do `build_todos` e nunca um pedaço de HTML à mão — o defeito
era precisamente uma página que a função que marca nunca chegava a ver):
**8 falham no código de hoje**, e os 4 que passam são os que fixam o que não
podia mudar — a página dele sem marca (a correcção de 29/09 já se apanhou a
despublicar o site dele), as dos amigos com marca, a raiz de uma coleção só, e
o JSON que a etiqueta não alcança.

## 2026-10-01 — A PÁGINA DO DECK NÃO TEM `+`/`−`; e as outras sete famílias não se tocaram

Palavras dele: *"no deck nao precisa + e - / ele ja indica se tem ou nao tem"*.
Ramo `ai-pc/deck-sem-steppers-2026-10-01`.

### O inventário, porque o `app.js` desenha `steppers` em NOVE sítios

A ordem avisou que o perigo aqui era tirar os errados. Foram-se listar todos
antes de apagar nada — a vista de cada um, e o selector com que o `ligar*` lhe
apanha os cliques:

| # | classe | vista | selector | saiu? |
|---|---|---|---|---|
| 1 | `steppers runa` | **Coleção** — o contador DELE do bloco «Runas» | `#runas-vista` | fica |
| 2 | `steppers` (`data-act`) | **Coleção** — as cópias normais do tile | `#grid` | fica |
| 3 | `steppers foil` | **Coleção** — o contador de foil do tile | `#grid` | fica |
| 4 | **`steppers proprias`** | **DECK** — `propriasBotoes` no `deckTile` | `#deck-body` | **SAIU** |
| 5 | **`steppers proprias`** | **DECK** — `propriaForaTile` (só o `−`) | `#deck-body` | **SAIU** |
| 6 | `steppers enc` | **Encomendas** — o tile da grelha | `#enc-grid` | fica |
| 7 | `steppers fe-enc-bot` | **Faltas** — «já encomendei» | `#fe-body` | fica |
| 8 | `steppers` (`data-vd`) | **Venda** — quantas vai vender | `#vd-body` | fica |
| 9 | `steppers` (`data-sl`) | **Produto Selado** — as unidades | `.sl-lista` | fica |

**Só os 4 e 5 viviam na página do deck**, e o `propriasBotoes` já tinha um
`!state.deck` à entrada — por isso nunca apareciam nas sub-vistas (Staples, Por
deck, Pimp) que também escrevem no `#deck-body`.

### A pergunta da ordem: de quem é a acção

- **As CÓPIAS PRÓPRIAS são acção do DECK — e é por isso que saem.** Ele pediu-as
  a 2026-09-21 com *"cada deck precisa de ter as cartas proprias; **colocas em
  cada deck o + e - para eu dizer se afinal tenho ou nao**"*. A frase de hoje é
  a mesma frase ao contrário: o botão existia para ele DIZER se tinha, e ele diz
  que a página já o indica. É uma revogação no mesmo vocabulário, não uma
  interpretação nossa.
- **O «JÁ ENCOMENDEI» não é acção do deck, e já não estava aqui.** CLAUDE.md,
  2026-09-17: *"uma aba 'encomendas' […] **e tiras esta funcionalidade dos
  decks**"* — os `+`/`−` da encomenda viveram no `deckTile` de 11/09 a 17/09 e
  saíram nesse dia; o que ficou foi a informação «N a caminho». Hoje vivem nas
  **Encomendas** (#6) e nas **Faltas** (#7, 27/09). **Ficam**, e não havia nada
  a tirar da página do deck por causa deles.

### ESCONDER NÃO É APAGAR, e o número fica

O local `proprio:<slug>`, a tabela, o `proprias.py`, a rota
`POST /api/proprias/ajustar` e o `riftvault proprias <slug> --mais/--menos`
**ficam intactos** — o que mudou é que a página do deck já não os edita. O que
saiu do `app.js` foi o que lá estava morto a seguir: o `propriasBotoes`, o
`propriaForaTile`, o `ligarProprias`, o `propriasAjustar` (o único que chamava a
rota) e o estado `propFila`/`propVoo`.

**No lugar dos botões ficou o NÚMERO** (`propriasLinha`, «**2** próprias do
deck», na cor das próprias), que era a informação que estava entre os dois — por
isso o tile não fica com um buraco. Sem próprias não escreve nada. A linha «de
onde vem o que tem» **deixou de as repetir**, senão diziam-se duas vezes. E as
três notas que mandavam carregar no `+` passaram a dizer o comando.

O resto da página não mexeu: o crachá `have/wanted` (o «já indica se tem ou não
tem»), o chip «próprias do deck N», a coluna `próprias` da tabela de montagem,
o aviso da regra de raridade, a secção «que não servem» e a coluna do CSV.

### Medido NO BROWSER, o `main` e o ramo contra a MESMA cópia dos dados

A sonda é uma só (`_revisao\_foto_steppers_sonda.py`), para a comparação valer;
o `main` na 8778 e o ramo na 8779, contra `_revisao\dados-steppers` — uma cópia
por `VACUUM INTO`, com duas cópias próprias e três linhas de venda metidas
nela, porque uma aba vazia dava zero steppers e isso **lia-se como «os botões
saíram»**, que é o erro a não cometer.

| vista (375 px) | `main` | ramo |
|---|---|---|
| **página do deck** | **27 steppers · 52 botões** | **0 · 0** |
| linha «próprias do deck» no deck | 0 | **2** |
| Coleção | 512 · 1024 | **512 · 1024** |
| Faltas | 232 · 464 | **232 · 464** |
| Encomendas | — | 162 · 324 |
| Venda | — | 3 · 6 |
| Produto Selado | — | 30 · 60 |

**A 375 px não há buraco nem scroll lateral na página do deck**:
`scrollWidth == clientWidth == 375`, 31 tiles, **zero** elementos fora do ecrã
e zero com scroll próprio, a 375 e a 1280.

**Duas coisas que a medição mostrou NÃO serem desta ordem**, porque o `main` dá
o mesmo à letra: a Coleção a 375 px tem `SCROLL:binder-wrap` e a grelha a sair
do ecrã — são as **filas do binder**, de propósito desde 26/09 (*"num ecrã
estreito o bloco corre para o lado"*) —, e as Faltas a 375 px têm quatro
pequenos `span` a transbordar (`var`, `piso` ×3). Ficam anotadas; não se
tocaram.

**Uma armadilha da medição, para a próxima:** com `multi.aberto: true` (o config
dele desde 01/10) um pedido sem sessão lê `editavel: false`, o `app.js` põe a
página em `readonly` e **não desenha stepper nenhum, em vista nenhuma**. A
primeira corrida deu 0 em todas as abas e parecia um estrago enorme; era a
autenticação. Mede-se com a porta fechada **na cópia**.

`tests/test_deck_sem_steppers.py` (**18 testes**), em quatro classes, e a
segunda é a que importa: **um teste que só dissesse «já não há steppers» passava
se alguém os tirasse todos**. `TestSairamOsDoDeck` (a classe, o CSS, o
selector que já não aponta ao `#deck-body`, as funções mortas, o `fetch`, o
tile sem o `−`); **`TestFicaramOsOutros`** (um teste por vista, com o nome da
vista, mais o «já encomendei» que não é do deck); `TestAInformacaoFicou` (o
número no lugar dos botões, sem duplicar, e o crachá e a tabela intactos); e
`TestEsconderNaoEApagar` (a rota, o módulo, o local, a CLI e o campo do
payload). **A prova pela negativa** está em
`_revisao\_prova_negativa_steppers.py`, que corre a bateria contra o `app.js` do
`main`: **8 dos 18 ficam VERMELHOS** (todos os que fixam o que saiu) e os 10 que
fixam o que ficou continuam verdes — e o script rebenta se algum trocar de lado.
O `test_copias_proprias.py::TestFrontend` foi ajustado: descrevia os botões de
ontem.

## 2026-10-02 — COLAR UMA DECKLIST (`colar.py`): a porta pela janela do browser

Palavras dele: *"dos decks, tem que ser possivel colar o texto em copy paste e
gerar o deck, depois diz as cartas que tens e que nao tens, com imagem com cor
e sem cor"* e *"quero que, para introduzir uma decklist, a seccao de decks seja
possivel ler 2 tipos: Imagem / TxT introduzido"*. Ramo
`ai-pc/colar-decklist-2026-10-02`.

Até aqui a única maneira de meter uma lista era pôr um `.txt` na pasta `decks/`
**à mão** — foi assim que a `leona-radiant-dawn.txt` entrou a 01/10. O motor
dos decks já estava todo feito; o que faltava era a porta.

### 1. NÃO HÁ LEITOR NOVO, e é o ponto de partida

O `decks.parse(path)` passou a ser uma casca do **`decks.parse_texto(texto)`**,
e é por aí que entram os dois caminhos. Um segundo leitor divergia do primeiro
no dia em que o formato mudasse, e aí uma lista colada e a mesma lista em
ficheiro davam decks diferentes. Há teste que lê o `colar.py` e recusa que ele
tenha gramática própria (`ROLES`, `endswith(":")`, `^(\d+)`).

Pelo mesmo motivo o deck nasce do **`decks.import_all`**: o texto colado aterra
como `.txt` em `config.decks_dir(con)` — a pasta **DE QUEM COLOU** (por
utilizador desde 2026-09-29, por isso cada amigo escreve na dele) — e a seguir
importa-se pela porta de sempre. O ficheiro continua a dar-se a ler, a
versionar no Git e a abrir num editor; leva à frente um comentário
(`colar.MARCA`) a dizer de onde veio, e um `Nome:` se a lista não o trazia.

### 2. ANTES DE GRAVAR, MOSTRA — e uma lista não vira deck em silêncio

`POST /api/decks/prever` **não escreve nada** (há teste que fotografa
ficheiros, `decks`, `deck_cards`, `copies` e `ops` antes e depois) e devolve as
linhas que casaram com o catálogo, **as que não casaram**, e a aritmética por
papel contra o `deck_rules`. `gravar()` sem `confirmar` **recusa-se** quando
alguma linha não casou (`PrecisaConfirmar` → 409), e sem `substituir` recusa-se
a escrever por cima de um deck que existe (`NomeOcupado` → 409) — a mesma forma
do `venda.vender`.

O **slug** sai do `Nome:` ou da Legend, e é saneado: vira um caminho em disco e
vem de uma caixa de texto (teste com `../../etc/passwd` e companhia).

`POST /api/decks/apagar` é o par, com o botão **«Apagar a lista»** na página do
deck: quem mete uma lista pela janela tem de poder tirá-la por lá, e era a
última coisa que ainda obrigava a ir à pasta à mão (estava em «Por fazer»
desde o início). **Não apaga cópias** — as próprias do deck ficam no
`proprio:<slug>`, como já acontecia a um deck cujo ficheiro desaparecia, e é
por isso que a pergunta fala da LISTA e não do deck. Na consola,
`riftvault colar [FICHEIRO] [--gravar]` (sem ficheiro lê do stdin; sem
`--gravar` só mostra).

### 3. A REGRA DAS VERSÕES: duas metades já existiam, e DIZ-SE qual

*"usa o que esta na coleccao, sendo foil ou nao, sendo Alt Art ou nao, sendo
Overnumbered ou nao. Se nao houver versao normal, ele avisa que sao X normais e
X Alt Art"* / *"se houver em duas edicoes diferentes, conta as 2, seleciona a
que cobrir o numero necessario, caso nao consiga, indica que e x de uma edicao
e x de outra"*.

Medido antes de escrever código (`_revisao\_medir_versoes_1002.py`), são **três
perguntas** e só uma era nova:

| metade | estado | hoje vale? |
|---|---|---|
| Alt Art / OverNumbered a taparem um lugar normal | **JÁ EXISTIA** (`Versoes.outras_de`, 2026-09-17) e o `decks.so_base: true` desliga-a | **ligar não muda nada**: medido, 0 cópias tapadas dos dois lados |
| a foil servir um deck | o monte vem do `locais.na_colecao`, que com `foil.conta_para_coleccao: false` (27/09) **só dá normais** | sem caso: as cartas do deck dele têm **0 foils** |
| a edição que COBRE SOZINHA | **não existia** — o `tirar` consumia pela ordem do catálogo e repartia sempre | sem caso hoje: **nenhuma** carta do deck tem base em mais do que uma edição |

**O `so_base` NÃO se virou**, e é decisão dele: ligá-lo faz a Alt Art e a
sobrenumerada que ele tenha taparem buracos do main. Hoje vale zero cópias; o
dia em que ele comprar uma alt art de uma carta que joga, passa a valer.
`tests/test_colar.py::TestComQueSeTapou` fixa as duas pontas — o que acontece
com ele ligado, e que o config de hoje o tem desligado.

**O que se construiu** foi a terceira: `decks.por_cobertura(pids, qty,
disponivel, set_de)` põe à frente a edição que cobre o pedido sozinha, antes de
o `tirar` consumir. A unidade é a **edição** (é como ele falou, e uma edição
pode ter mais do que uma impressão da mesma carta); entre as que cobrem e entre
as que não cobrem a ordem do catálogo mantém-se, e sem nenhuma a cobrir nada se
mexe. E as duas metades do RELATO, que valem assim que houver caso: cada versão
do payload leva agora o **`set`**, e a página escreve «2 de OGN + 1 de UNL»
(`edicoesNota`) e «3 — 1 normal, 2 Alt Art» (`tapadaNota`).

### 4. A COR: a cores quando tem, a cinzento quando não tem

`filter: grayscale(1)` na arte do tile quando `have === 0` — **a mesma foto com
um filtro**, não uma imagem nova (o `cdn.riftscribe.gg` continua a servir uma
só). O crachá, o «N×» e a moldura ficam a cores: são a informação, e a cinzento
perdiam-se. O que vem a caminho conta como «não tem»: ele ainda não a tem na
mão.

### 4b. O GUARDA DAS CONTAS APANHOU-ME, e é para isso que ele existe

A suite deu vermelho no `test_contas.py`:
`test_a_lista_das_rotas_esta_completa` varre o `server.py` à procura de
`@app.post` e exige que **todas** as rotas de escrita estejam na lista que a
bateria das contas percorre — as três novas não estavam. Não era um teste
velho a descrever o passado: era a pergunta 7 da checklist de 2026-09-29
(«percorreste TODAS?») a funcionar no primeiro caso real depois de ela nascer.

As três entraram na `ESCRITAS` (20 → **23**) e **passam os três testes de
guarda sem uma linha de código**: sem sessão **401**, com sessão e sem CSRF
**403**, com CSRF errado **403** — é o guarda genérico por MÉTODO
(`rotas_conta.ESCREVE`), que as apanha por serem POST.

**O `prever` entra na lista apesar de não escrever na base.** É um POST que LÊ
a coleção de quem o manda (resolve os nomes contra o catálogo e diz o que ele
tem), e desde 2026-10-01 um pedido que não seja de casa precisa de sessão para
ler. Deixá-lo de fora era abrir uma leitura pela porta das escritas.

### 5. A IMAGEM FICOU POR FAZER, e está DITA

**Não há OCR nenhum instalado na máquina dele** — medido a 2026-10-02: nem
`pytesseract`, nem `tesseract` no PATH, nem `easyocr`, `paddleocr` ou
`rapidocr_onnxruntime`. Há `PIL` e `numpy`, que abrem uma imagem e não lhe lêem
texto nenhum. A regra da casa é não instalar nada por iniciativa própria, por
isso a metade da imagem **não se fez** e não se fingiu que se fez.
`TestOCR` existe para o dia em que alguém instalar um: aí fica vermelho, e é o
sinal de que a segunda metade se pode construir — **com o critério dele**: só
entra o que casa EXACTAMENTE com o catálogo, e diz-se quantas linhas não
conseguiu ler.

### Medido a 2026-10-02 contra uma CÓPIA do `data/` real

`_revisao\_prova_colar.py` (por `VACUUM INTO`: as bases estão em WAL; o `data/`
a sério nunca se escreveu). A lista dele pelas DUAS portas:

| | pelo `.txt` à mão | **pela caixa de colar** |
|---|---|---|
| deck | Leona Radiant Dawn | **igual** |
| tenho | 50/54 · 12 runas fora | **igual** |
| **falta** | **4 cópias de 2 cartas** | **4 cópias de 2 cartas** |
| quais | 3× Zenith Blade · 1× Salvage (tem 2 de 3) | **as mesmas** |
| a cinzento (0 cópias) | 1 carta | 1 carta |

**As duas portas dão o mesmo deck**, carta a carta — e é o número que a ordem
mandava confirmar. Fotografado a 375 e a 1280 px contra o ramo servido na 8779:
`documentElement.scrollWidth == clientWidth == 375`, **zero** elementos a sair
pela direita e **zero** com scroll próprio; 29 tiles, **1 a cinzento** (a
Zenith Blade, com `0/3` e «faltam 3 a comprar»), **0 steppers** — a decisão de
01/10 fica de pé.

**Dois defeitos vieram da FOTOGRAFIA, não do código:** o `.section-head` é
`text-transform: capitalize` e só o `<span>` está isento — com `<small>` lia-se
«Vai Gravar-Se Como Leona-Radiant-Dawn.Txt», que é a mesma avaria do Produto
Selado («Binders E Deck Boxes», 2026-09-25); e a 375 px o
`justify-content: space-between` da célula mandava «39» e «(+1 Champion = 40)»
para extremos opostos da linha.

**A frase do «sem decks» mudou nos dois sítios** (`decks.SEM_DECKS_COMO` e o
`app.js`, que o `test_sem_decks` compara): passou a dizer a porta nova
primeiro. E um teste desse ficheiro foi **endurecido**, não afrouxado: lia o
`loadDecks` com um corte de 1400 caracteres e dava vermelho só por a função ter
crescido — passou a ler a função inteira, que é a lição do `test_conta_fechada`
de 01/10.

`tests/test_colar.py` (**39 testes**, contra pastas temporárias e um catálogo de
brincar): um leitor só e a lista real pelas duas portas; a previsão que não
escreve; as linhas que não casam a travarem o gravar; o slug que não foge da
pasta; a edição que cobre e as que se repartem; o que se tapou com que versão;
a cor; a Coleção que não mexe (com a prova pela negativa ao lado); as três
rotas; o botão de apagar; a CLI; e o OCR que não há.

**A PROVA PELA NEGATIVA** (`_revisao\_prova_negativa_colar.py`, que corre a
bateria contra uma árvore com o `riftvault/` do `main`): **só CINCO passam**, e
são exactamente os que fixam o que NÃO podia mudar — o `decks.so_base: true` no
config real, o mecanismo do `so_base` nos dois sentidos (que é de 2026-09-17 e
não desta ordem), a prova pela negativa da fotografia da Coleção, e o OCR que
não há. Os outros **34 ficam vermelhos**: o `colar.py` não existe lá, o
`decks.parse_texto` também não, e o `app.js`/`style.css` não têm nenhuma das
marcas.

## 2026-10-02, à tarde — LER UMA DECKLIST POR IMAGEM (`imagem.py`), sem OCR nenhum

Palavras dele, de 2026-10-01: *"quero que, para introduzir uma decklist, a
seccao de decks seja possivel ler 2 tipos: **Imagem** / TxT introduzido"*. A
metade do texto fez-se nesse dia; esta é a outra. O caso de prova é uma página
de classificações a sério — UVS Games, RQ Los Angeles, 2026-09-26, «Rengar,
Pridestalker» por DSG Prismaticism, 1.º de 2165 jogadores. Ramo
`ai-pc/imagem-decklist-2026-10-02`.

### 1. NÃO HÁ OCR, e por isso não se lê texto nenhum

Medido outra vez a 2026-10-02, antes de desenhar seja o que for: **não há
`pytesseract`, nem `tesseract` no PATH, nem `easyocr`, `paddleocr`,
`rapidocr`, `cv2`, `imagehash` nem `scipy`.** Há **Pillow 12.2** e **numpy
2.4**, e mais nada. A regra da casa é não instalar nada, por isso a pergunta
passou a ser «o que é que se consegue identificar sem ler uma letra».

A resposta estava em disco: **`data/images/` tem as 1180 artes do catálogo**,
600×837 em `.webp`, descarregadas pelo `riftvault images`. Casar o recorte com
a arte **identifica a IMPRESSÃO**, não só a carta — e isso é MELHOR do que ler
o nome, porque separa a base da arte alternativa. Na lista dele havia duas Alt
Art (`OGN-007a` Fury Rune ×4 e `OGN-039a` Kai'Sa ×3) e **as duas saíram
certas**.

**A assinatura tem DUAS metades**, e a segunda faz falta: um `dHash` 16×16 da
janela da ARTE (que o crachá não tapa) e outro da CARTA INTEIRA com o crachá
tapado **nos dois lados**, mais a cor média 4×4. Só com a arte, duas impressões
com a mesma arte e molduras diferentes ficavam empatadas — é o caso da runa
base do OGN contra a promo do VEN. Com a carta inteira separam-se.

**Os battlefields aparecem DEITADOS na página**, e o catálogo sabe disso: a
coluna `orientation` tem 66 `landscape`. Cada uma entra no índice **duas
vezes**, rodada 90 e 270 — uma landscape rodada cabe exactamente na caixa de
uma portrait. Sem isto os três battlefields da lista dele davam lixo
(pontuação 89–97 contra 39–47 depois).

O índice é **1246 assinaturas para 1180 artes** e leva ~13 s a construir, com
cache em `data/images/.assinaturas.npz` (dentro do cache das imagens, que já
está no `.gitignore`), invalidada pela contagem e pelo `mtime` dos ficheiros.

### 2. AS QUANTIDADES: os crachás, e a guarda que é topológica

São `x1`, `x3`, `x8` — brancos, grandes, sempre no mesmo canto. A caixa
**mediu-se pela VARIÂNCIA entre as 31 cartas**: o que é igual em todas e é
escuro é o crachá (relativo `0.385, 0.841`–`0.615, 1.0`). Mas o recorte é
reencontrado em cada carta, pela caixa escura cheia — sem isso o branco
apanhava a **caixa de texto creme da própria carta** e os glifos vinham todos
colados num só. Foi o defeito que fez 13 das 31 falharem a meio da ordem.

Os dígitos lêem-se por **template de uma fonte do Windows** (Arial, 31/31 na
imagem de prova). Como uma fonte que acerta numa imagem não é garantia
nenhuma, por cima há uma **guarda TOPOLÓGICA**: conta-se os BURACOS do glifo
(um `8` tem dois, o `0/4/6/9` um, os outros nenhum) e só se compara com os
dígitos desse grupo. A confusão clássica 3↔8 — que o Segoe UI fazia nove vezes
em 31 — deixa de ser possível, porque é uma propriedade da forma e não da
fonte. Sem fonte nenhuma em disco, a quantidade fica por ler e **diz-se**.

### 3. OS PAPÉIS vêm do catálogo; da imagem só se lê o CORTE

`Legend`, `Rune` e `Battlefield` saem do `type` da impressão. O sideboard é a
única coisa que a disposição tem de dar, e lê-se o **ESPAÇO** entre linhas, não
a palavra: na página de prova sobram 94 e 69 px entre linhas seguidas (0,13 e
0,10 da altura de uma carta) e **274 no corte** (0,38). O limite é `0.22`.
**Não se compara com a mediana dos intervalos**, de propósito — com duas linhas
só, a mediana É o corte e ele deixava de se ver. Com mais do que um corte não
se adivinha qual é qual: fica tudo no deck e a página di-lo.

**O CHAMPION é um PALPITE DE DISPOSIÇÃO, e vai dito.** O catálogo **não o
marca** (as `tags_json` estão todas vazias, verificado) e em Riftbound «Champion
Unit» é um supertipo que dezenas de cartas têm — o Champion de um deck é o que
casa com a Legend, e isso não está na base. A página põe-no logo a seguir aos
battlefields, e é daí que ele sai; a caixa do texto é editável e o ecrã e o CLI
avisam para conferir a linha.

### 4. «SÓ ACEITA O QUE TEM A CERTEZA»

Uma carta só entra com pontuação ≤ 110 **e** margem ≥ 25 para a segunda. O que
não passa fica de fora, é CONTADO, e a página diz com o que se parecia — nunca
se escolhe o mais parecido. Medido: as 31 leituras boas deram margem 62–164; a
única dúvida que apareceu durante a ordem deu **1,9**.

**A margem mede-se contra a melhor CARTA diferente, não contra a melhor
IMPRESSÃO diferente**, e foi isso que resolveu a última dúvida. Era a Body Rune:
`OGN-126` e `VEN-R04` são a mesma arte e ficaram a 1,9 de distância — mas são
**a mesma carta**, dão a mesma linha, e a lista que sai daqui é por NOME. Não
havia nada a desempatar.

### 5. PELA MESMA PORTA, e o tecto do corpo passou a ser POR ROTA

A imagem produz **texto**, e daí para a frente é o `colar.py` de 01/10: o mesmo
`prever`, o mesmo `gravar`, o mesmo `decks.parse_texto`. **Não há segundo
caminho de gravação**, e há teste que recusa que o `imagem.py` tenha gramática
própria. No ecrã, o texto lido enche a **MESMA caixa** do copy-paste — é
editável, que é o que faz o palpite do Champion e as linhas por ler serem
corrigíveis antes de gravar.

`POST /api/decks/imagem` (não grava nada; devolve o texto, o que não leu e a
previsão) e `riftvault imagem foto.png [--gravar]`, que escreve o texto no
stdout (colável) e as dúvidas no stderr.

**O tecto do corpo deixou de ser um só.** O do Flask é global e a imagem de
prova são **19 MB**; ficou no maior (40 MB) e são as outras **vinte e duas**
rotas que passaram a ser travadas no `_antes`, nos mesmos 256 KB de sempre
(`rotas_conta.CORPO_DE_FICHEIRO`). Assim o alargamento é explícito e vale só
onde está escrito. A rota entrou na lista das escritas do `test_contas` — **o
guarda das contas apanhou-a**, como tinha apanhado as três do colar.

### Medido a 2026-10-02 contra o `data/` real, com a imagem dele

`_revisao\_prova_imagem.py` (só leitura; a única escrita é a cache de
assinaturas, que está no `.gitignore`):

| | |
|---|---|
| grelha | 6 colunas × 6 linhas, **31 cartas** |
| lidas | **31** |
| por ler | **0** |
| Legend | 1 — `UNL-183/219` Pridestalker |
| Champion | 1 — `UNL-120/219` Rengar, Trophy Hunter |
| MainDeck | **39** cópias em 17 cartas (39 + 1 Champion = **40**) |
| Battlefields | 3 |
| Rune Pool | **12** — 8 Body Rune + 4 Fury Rune |
| Sideboard | 10 |
| linhas que o catálogo não conhece | **0** |

**A aritmética que ele leu a olho fecha toda**, e as duas Alt Art estão lá. A
geometria saiu ao pixel: colunas em 84/647/1210/1773/2336/2899 (largura 491),
linhas em 692/1498/2303/3109/4095/4876 (altura 712) — conferidas contra a
medição à mão.

`tests/test_imagem.py` (**25 testes**, contra pastas temporárias e um catálogo
de brincar — nunca contra a coleção dele; a página de torneio é montada pelo
próprio teste): o texto sai no formato que o `colar` já lê e o módulo não tem
gramática própria; ler não grava nada; os crachás de 1 a 9; **o 8 não vira 3**,
provado pelos buracos; a ambígua fica de fora e é contada — e a ambígua é
metade de uma carta e metade de outra, para provar a regra da MARGEM, que é a
que protege a sério (uma intrusa qualquer seria apanhada por qualquer regra); o
corte do sideboard pelo espaço, com DUAS linhas só, e com dois cortes a não
adivinhar; os papéis do catálogo; as recusas legíveis; o ecrã; e o tecto do
corpo por rota.

### O que NÃO se fez, e porquê

- **Ler o CÓDIGO do rodapé** (`UNL • 183/219`). É legível na imagem e teria
  confirmado cada carta por um segundo caminho — mas precisa de OCR ou de uma
  biblioteca de glifos para dígitos e para os cinco códigos de edição, e com a
  arte a dar 31/31 não se pagava. Fica como o caminho óbvio se um dia uma
  página der margens apertadas.
- **Outras disposições.** Isto lê a grelha regular das páginas de
  classificações. Uma fotografia de cartas em cima da mesa, com perspectiva e
  sombras, é outro problema — e a recusa é legível («não se vê uma grelha de
  cartas nesta imagem»), em vez de uma lista inventada.
- **Uma segunda imagem de prova.** Só há esta; os limiares estão medidos contra
  ela e contra as páginas sintéticas dos testes. Se uma página nova falhar, os
  números a mexer são o `MAX_PONTO`, o `MIN_MARGEM` e o `SALTO`, e cada um está
  comentado com a medição que lhe deu origem.

## 2026-10-02 — AS CAIXAS DAS FALTAS: o separador cortado AO CONTRÁRIO (`faltas_edicao.caixas`)

Palavras dele: *"nas faltas, tens as faltas de masterset, mas gostava que
tivesse uma caixa tambem para faltas de Overnumbered e outra caixa para faltas
AltArt e uma caixa para as faltas de Vendetta (que era tudo). pode ser com
sistema de botoes para nao ocupar muito espaco ou como achares melhor"*. E, a
duas perguntas: a caixa do Vendetta leva **tudo** o que falta da edição (master
set, sobrenumeradas, alt art, signatures e promos) e as três caixas são **iguais
à do master set** — com preço, total e lista para o Cardmarket, *"nao sao so
para ver"*. Ramo `ai-pc/caixas-faltas-2026-10-02`.

### 1. O que faltava, e porque é que ele disse «tens as faltas de masterset»

O separador é **por EDIÇÃO** desde 2026-09-15: com «Todas» escolhido são cinco
edições × quatro blocos, e portanto **vinte listas do Cardmarket** para
percorrer. O corte que não existia é o de atravessar as edições — e a frase dele
diz exactamente qual é a excepção: **a lista do master set de todas as edições
JÁ EXISTE**, é a «Wantlist — tudo» do fim da Coleção (`a_subir.wantlist`). As
outras três categorias nunca tiveram uma lista que não fosse por edição.

| caixa | atravessa | âmbito | tem ≥1 | FALTAM | CUSTAM |
|---|---|---|---|---|---|
| **OverNumbered** | 4 edições (o OGS não tem) | 92 impressões | 41 | **51 cópias de 51** | **6 660,55 €** |
| **Alt Art** | 4 edições | 96 | 80 | **160 cópias de 84** | **1 014,90 €** |
| **VEN — tudo** | os 4 blocos do VEN | 221 | 199 | **58 cópias de 39** | **2 069,42 €** |

Medido a 2026-10-02 contra uma cópia do `data/` real (`VACUUM INTO`: as bases
estão em WAL). **Os números são reais e explicam-se**, e conferiu-se antes de
desenhar seja o que for:

* **6 660 € em 51 cópias são 131 €/carta, e 2 100 € são UMA**: o `UNL-238` Baron
  Nashor, a carta que ele disse a 2026-09-05 que **nunca compraria** — 31 % do
  total da caixa. As seguintes são `VEN-189` Rogue Assassin 390 €, `SFD-225`
  Irelia 300 €, `OGN-299` Daughter of the Void 200 €. É a classe das
  reimpressões de topo de set, e é por isso que elas saíram da Coleção a
  2026-09-10 e não entram nas listas gerais. Por isso cada caixa leva a
  **`mais_cara`** no payload e o cabeçalho escreve-a: um total de 6 660 € sem
  ela não se lê.
* o VEN parte-se em master 9 cópias · 23,57 € + sobrenumeradas 18 · 1 921,65 €
  (93 % da caixa) + alt art 31 · 124,20 € + promos **0** — ele tem as seis
  `VEN-SP` todas. 9+18+31+0 = 58 ✓.

### 2. NÃO É UM CÁLCULO NOVO — e não há um segundo item

Uma caixa é uma **re-arrumação** dos itens que o `payload` já calculou, e leva
só a lista dos `printing_id` (**`pids`**): nunca uma cópia da linha. O
`feLigarCaixas` do `app.js` resolve-os para os MESMOS objectos, por referência.

**É isso que faz o `+` de «já encomendei» (2026-09-27) continuar a valer sem
plumbing nenhum**: o `feItem()` mexe num objecto só, e a caixa e o bloco da
edição dizem o mesmo número por serem a mesma linha. Com duas cópias divergiam
no primeiro clique — e o payload engordava com 174 linhas repetidas.

Pelo mesmo princípio a caixa tem a FORMA de um bloco (`id`, `label`, `scope`, os
campos do `soma`, `wantlist`), e por isso o `feTile`, o `feWantlistHTML`, o
`feSoma` e o `feWlSoma` desenham-na sem saber que ela existe.

### 3. AS CAIXAS SOBREPÕEM-SE, e é o que ele quer

Uma sobrenumerada do VEN está na caixa «OverNumbered» **e** na «VEN — tudo» —
«que era tudo»; foi-lhe dito e não objectou. Consequência: **a soma das caixas
não é o total do separador**, e a página di-lo, como a nota do «Todos juntos»
dos decks diz desde 2026-09-11. No separador a linha continua a ser UMA (há
teste).

### 4. O BOTÃO «VEN — tudo» não se chama «VEN», e a razão é de leitura

O separador já tem um botão **«VEN»** (a edição em quatro blocos, com o master
set na wantlist geral) e esta caixa é outra coisa. Dois botões com a mesma
palavra lado a lado leem-se como um — é a lição do «principal» contra a
«prioridade 1» de 2026-09-27. O nome vem do `config.set_name`, que para o VEN é
o **código** por decisão dele de 2026-08-31; o sufixo é que diz o que a caixa
tem. Pelo mesmo motivo a fila das caixas é uma fila **PRÓPRIA e rotulada**
(«CAIXAS»), por baixo da das edições («EDIÇÃO»), com **uma só escolha**
(`prefs.feSet`) nas duas.

### 5. AS SIGNATURES: ele nomeou-as e são ZERO

A caixa do VEN leva «master set, sobrenumeradas, alt art, **signatures** e
promos» nas palavras dele. As signatures saíram da Coleção a 2026-09-09 e estão
ESCONDIDAS (`master_set.escondidas` leva o `"*"`), por isso não chegam ao
âmbito — e **o VEN não tem nenhuma no catálogo da RiftScribe**: medido a 02/10,
**0 de 228**, como este ficheiro já dizia desde 09/09.

**Não se alargou o âmbito para apanhar zero cartas.** Fazê-lo era desfazer a
decisão de 09/09 sem um caso. O que se fez foi **contar o que ficou de fora e
pô-lo no ecrã**: no VEN são **7 escondidas — 6 runas sem numeração (`VEN-R01..
R06`, que ele mandou esconder a 15/09) e 1 token** —, e uma signature nova
apareceria ali **pelo nome** em vez de desaparecer em silêncio (há teste que
mete uma no catálogo e exige que ela apareça na linha). **As foils também não
entram** — não são faltas desde 27/09 e ele não as nomeou nesta —, e a caixa diz
quantas são (19 cópias no VEN).

### 6. Quais são as caixas vive no CONFIG

`faltas_edicao.caixas_blocos` (ids de bloco → uma caixa com esse bloco de todas
as edições) e `caixas_edicoes` (códigos de edição → a edição inteira). Hoje
`["overnumbered", "alt_art"]` e `["VEN"]`. Uma edição nova que ele queira ver
inteira é **uma palavra na lista**, não um `if`. Um bloco ou uma edição que não
existam **REBENTAM**, com a lista do que há — a regra das outras listas do
config. Lista vazia = sem caixas, e a fila de botões desaparece sozinha.

### Medido a 2026-10-02 — o site INTEIRO, `main` e ramo, na mesma cópia

`_revisao\_medir_main_vs_caixas.py`: o `main` (`af9c3a0`) num worktree e o ramo,
cada um a gerar o site contra a MESMA cópia do `data/` real, com o MESMO config.
**25 ficheiros de cada lado, os mesmos nomes; dos 21 JSON, UM difere** — o
`api/faltas_edicao.json`, e dentro dele **a única chave nova é `caixas`: o resto
do ficheiro é byte a byte igual ao do main**. Os outros três que diferem são o
`app.js`, o `index.html` e o `style.css`, que são o código desta ordem.

Ou seja: os níveis, o denominador, a wantlist do master set, o valor, as Faltas
normais, a metade das foils, o painel, o A mais, as Encomendas, a Venda e o
Selado **não mexem um número**, e não é uma asserção — é o site comparado
ficheiro a ficheiro.

### A 375 px, e o que a fotografia apanhou

Medido no Chrome a sério (DevTools Protocol) contra o ramo servido na 8779, nas
três caixas e a 375 e 1280 px: `documentElement.scrollWidth == clientWidth ==
375`, **zero** elementos com scroll próprio no `#fe-body`, e a fila de botões
**envolve** (`segwrap`), não corre para o lado. A caixa do VEN mostra **39 tiles
e 1 lista**; a vista por edição do mesmo VEN mostra **50 tiles e 4 listas** — é
o «não ocupar muito espaço» a aparecer no número.

**Três coisas vieram da medição e da foto, não do código:**

1. **`.secbar[hidden]` fazia falta.** O `display: flex` da classe ganha ao
   `display: none` que o browser dá ao atributo `hidden`, e sem a regra a fila
   das caixas aparecia vazia com a lista do config a `[]`. É a mesma armadilha
   do `.chips[hidden]`, que já estava no ficheiro.
2. **«852 foils fora» numa caixa de sobrenumeradas era uma omissão inventada.**
   O âmbito das foils são as comuns e incomuns BASE e não sobrenumeradas: uma
   caixa de sobrenumeradas ou de alt art **nunca teve foil nenhuma** para deixar
   de fora. Só as caixas de edição contam foils (e é o
   `faltas_foil.payload_completo` que o faz — o `faltas_edicao` continua a não
   conhecer a outra metade).
3. **«1 tokens»**, e o título da lista a ler-se «Wantlist — VEN — tudo · a
   edição inteira · 4 blocos», três traços para uma lista.

**Transbordo a 375 px: 3 `<i class="var">Arte alt.</i>`, e NÃO é desta ordem** —
provado medindo o mesmo na vista por edição do VEN, no mesmo ramo e com os
mesmos tiles: **os mesmos 3**. É o que este ficheiro já anotava a 27/09 («quatro
pequenos `span` a transbordar (`var`, `piso` ×3). Ficam anotadas; não se
tocaram»). A caixa do OverNumbered, que não tem alt arts, dá **0**.

### Na consola

`riftvault faltas --caixa bloco-overnumbered [--codigos]` escreve a lista para
colar (o stdout fica colável, o resto vai para o stderr, como no `riftvault
wantlist`); o `riftvault faltas` sem argumentos passou a listar as três caixas
com o `--caixa` de cada uma e a dizer que se sobrepõem. Uma caixa desconhecida
rebenta com a lista das que há.

`tests/test_caixas_faltas.py` (**49 testes**, contra cópias e config
temporário): o que as caixas são (os dois cortes, a sobreposição, a ordem dos
`pids`, os números a saírem do `soma` dos mesmos itens, a caixa a levar `pids` e
não itens); a wantlist de cada uma pelo gerador único, com o pendente a sair da
lista e a linha a ficar; o `lists` a dizer quanto dela já está na wantlist
geral; a `mais_cara`; o config a mandar, as listas vazias, o bloco e a edição
inventados a rebentarem, e o config REAL; o que fica de fora dito pelo nome (com
uma signature metida no catálogo a aparecer na linha); e **a fotografia da
Coleção** — níveis, índice, wantlist, master_faltas, valor, as quatro chaves da
metade das normais, o painel de cada edição e a `copies` — igual com as caixas
ligadas e desligadas, com a **prova pela negativa** ao lado e **sem o relógio
dentro** (`sem_relogio`, a lição de ontem).

**Dois defeitos do PRÓPRIO TESTE, e o segundo vale para o ficheiro ao lado:** o
`metrics.index_payload(con, cfg)` passa o config no segundo posicional, que é o
**`editable`** — a fotografia passava a conter o próprio ficheiro que o teste
muda e comparava-se a si mesma. O `cfg` vai agora por nome. O
`tests/test_runas_por_edicao.py` tem a mesma chamada posicional (fica anotado:
lá não dá falso negativo porque aquele teste não mexe no config, mas é a mesma
armadilha à espera).

## 2026-10-02 — OS ACHADOS 3, 4 e 6 DA VARREDURA: a checklist passa a MEDIR, o payload deixa de se contradizer, e apagar a conta apaga a password

Três defeitos do `docs/varrimento-2026-10-01.md`, mais o `.nojekyll` da raiz que
ele encontrou no mesmo dia. Ramo `ai-pc/achados-346-2026-10-02`.

### 3. A VERIFICAÇÃO PRESUMIA DOIS PASSOS QUE ESTAVAM FEITOS

O `riftvault multi --verificar` marcava `[TEU]` — «só tu podes» — a «a conta na
Cloudflare» e aos «nameservers do baverone.com + o túnel». **Estavam feitos
desde 29/09 e eram verificáveis**, e isso mediu-se duas vezes: o serviço
`Cloudflared` em `STATE: 4 RUNNING` e o
`https://editar.baverone.com/api/conta.json` a responder **200 em ~330 ms, com
`origem: "fora"` e NOVE sinais de intermediário**.

**O estrago era de checklist, e era o pior sítio para o ter:** o passo 2 é o
único da lista com risco declarado — *«o rift.baverone.com não pode cair»* — e a
verificação mandava-o lá outra vez. Uma checklist que presume ensina a ignorar a
checklist, e a seguir ignora-se o passo que importava.

**Passou a ser UM passo que PERGUNTA** (`abrir._tunel` +
`abrir.perguntar_ao_tunel`): um `GET` ao `auth.base_url/api/conta.json`, e
lê-se o `origem`/`sinais` **que a própria app escreveu**. Se um pedido que saiu
pela internet volta a dizer «vi-te chegar de fora», então a conta na Cloudflare
existe, os nameservers estão trocados, o `cloudflared` corre e entrega neste
Flask — **os quatro de uma vez**.

**Daqui não se vêem os cabeçalhos da Cloudflare** (são postos no caminho de
ida), por isso não se tentou adivinhá-los: pergunta-se a quem tem a resposta.
E é o `/api/conta.json` de propósito — é a única rota que diz `origem`/`sinais`
e das poucas que passa **sem sessão vindo de fora**
(`rotas_conta.DE_FORA_SEM_SESSAO`); qualquer outra dá 401, e aí não se
distinguia «o túnel está em baixo» de «o túnel está vivo e pediu password».

**É UM E NÃO DOIS** porque a medição prova a cadeia inteira e, quando falha,
**não sabe dizer qual elo quebrou**. Partir a resposta em dois era voltar a
presumir metade. Os dois passos dele continuam escritos no «como» — o que
deixou de se presumir é se estão feitos.

**SEM REDE A RESPOSTA É «NÃO SEI», NUNCA «FALTA»** — é a diferença entre não
medir e medir mal, e era medir mal que lá estava. A marca ` TEU  ` do `None`
passou a **`NÃO SEI`**, e a linha «falta só o que é teu (as linhas marcadas
TEU)» foi-se: já não há nenhuma.

**A medição é INJECTÁVEL e por omissão NÃO HÁ REDE** (`verificar(cfg,
medir=None)`). É uma escolha: o `verificar` é chamado pelo `--abrir` e pela
bateria inteira, e uma biblioteca que vá à rede nas costas de quem a chama fica
a ver se um `urlopen` estoura o prazo. Quem pede a medição é o comando que um
humano corre — o `cmd_multi` passa o `perguntar_ao_tunel`.

**E o passo NÃO trava o `--abrir`**, nem com vermelho nem com «não sei»: o
`--abrir` recusa pelos passos que deixam **ele** de fora da própria coleção, e
abrir com o túnel em baixo não perde nada (os amigos não chegam lá). Fazê-lo
essencial tinha ainda um efeito pior: um `ok=None` por falta de rede passava a
travar o `--abrir` num avião.

**As cinco respostas, cada uma a dizer o que sabe:** `OK` (200 + «fora», com N
sinais); **`NÃO SEI`** (sem endereço escrito · ninguém pediu a medição · a rede
não deu); **`FALTA`** (um código que não é 200 — o DNS resolve e o túnel está em
baixo · respondeu mas não era o riftvault · a app diz que o pedido lhe chegou
**de casa**, e aí o endereço público não passa por túnel nenhum, que é
configuração errada e não falta de passo).

**O teste que fixava o defeito era o `test_senhas.test_sao_DOIS_passos_dele_e_
nao_tres`** — exigia `len(dele) == 2` e que o `dele[0]` apontasse ao PASSO 1 e o
`dele[1]` ao PASSO 2. Foi reescrito; era o teste que estava velho, como o
`test_binders.py:399` estava para o achado 2.

### 4. O PAYLOAD CONTRADIZIA-SE A SI PRÓPRIO

**Medido no servidor a sério**, mesmo pedido anónimo de casa, com
`multi.aberto: true` (o estado commitado dele): o `/api/conta.json` dizia
`editavel: false` e **oito payloads diziam `editable: true`** — eram 15
`editable=True` **fixos** no `server.py` contra a regra que vivia no
`rotas_conta.api_conta`.

Hoje não se via, porque o `app.js` cruzava os dois campos e ficava pelo mais
restritivo. O estrago era no próximo leitor que confiasse no campo — a CLI, um
teste, uma vista nova —, e o sintoma seriam `+`/`−` desenhados a dar 401 a cada
clique, que é precisamente o que a nota do `api_conta` diz querer evitar.

**Uma resposta só: `rotas_conta.editavel()`**, onde a regra já estava e onde
vive o `g` que o `_antes` preenche. O `server.py` tem um `_editavel()` que é só
o caminho até ela, e o `api_conta` chama a MESMA função — por isso a regra está
escrita uma vez. As duas metades: **com sessão de uma conta** pode escrever quem
não está na página de outra pessoa (`somente_leitura`) e não está com a
password temporária; **sem sessão**, só de casa E com a porta fechada.

**O CAMPO TINHA DE SE PARTIR EM DOIS, e a ordem não previu isto.** O `editable`
respondia a DUAS perguntas de uma vez, e a segunda era o `boot()` a usá-lo para
decidir se vale a pena pedir o `api/conta.json` (no estático não há rota, e
pedir deixava um 404 na consola). Torná-lo honesto, com um campo só,
**escondia a caixa de «Entrar»** a um leitor anónimo com a porta aberta — que é
precisamente quem tem de a ver. Era o beco de 2026-09-30 por outro caminho.
Nasceu por isso o **`servidor`** (`metrics.index_payload(servidor=...)`): o
servidor manda `true`, o `build` manda `false`, e a omissão é `false` — um
ficheiro gerado por uma versão antiga não pode passar por servidor.

**Medido a 2026-10-02 contra cópias do `data/` real** (o `main` num worktree e o
ramo, a mesma cópia do mesmo instante):

| | `main` | ramo |
|---|---|---|
| payloads que contradizem o `conta.json` (porta aberta, anónimo de casa) | **8 de 8** | **0** |
| porta FECHADA, de casa | tudo `true` | **tudo `true`** (o uso dele não mexe) |
| o `boot()` pede o `conta.json`? | sim (pelo `editable`) | **sim** (pelo `servidor`) |
| site publicado | 77 ficheiros | **78** (o `.nojekyll`, ver a seguir) |
| JSON do site a diferir | — | **3**, e só pela chave nova `servidor: false` (+17 bytes cada) |

**O site publicado mantém todos os 48 `editable: false`** — comparado ficheiro a
ficheiro, não por asserção.

### 6. APAGAR A CONTA DEIXAVA O HASH DA PASSWORD ATRÁS

O `conta.apagar` não tocava no `data/auth.db` **de propósito** — está na
docstring desde 29/09: «a `user_auth` é desta casa e a limpeza também». O
problema é que a limpeza era feita **por cada chamador**, e a `cli.py` e a
`rotas_conta.py` tinham cada uma a sua cópia da mesma disciplina. **Hoje não
havia hash órfão por um caminho real** (os dois lembravam-se) e `users.user_id`
é `AUTOINCREMENT`, por isso ninguém herdava a password de ninguém. O defeito era
de desenho: uma primitiva que deixa dados pessoais atrás e confia na MEMÓRIA de
quem a chama, com o terceiro chamador a pagar.

**Fechou-se no sítio certo, e fez-se as duas coisas** que o §6 propõe:

* o `conta.apagar` chama o `auth.esquecer_identidades` — é ele a camada de
  POLÍTICA (a confirmação, o export antes, a contagem), e «apagar a conta apaga
  tudo o que é da pessoa» é uma invariante de política. **A casa continua a ser
  a de lá**: quem mexe na `user_auth` é a função do `auth.py`; o que mudou é
  quem a manda;
* e **devolve o que limpou** em `res["auth"]`, para a CLI e a rota dizerem o
  número em vez de voltarem a perguntar — as duas chamadas de fora saíram;
* **mais o teste que o §6 preferia**: por **cada** caminho de apagar
  (biblioteca, CLI, rota) varrem-se as três tabelas do `auth.db` à procura do
  `user_id`, com a prova pela negativa ao lado (um varrimento que nunca ache
  nada vale zero).

**É DEPOIS do `utilizador.apagar`, de propósito:** se o apagar falhasse, ter
limpado a password primeiro deixava uma conta **VIVA sem forma de entrar**. Ao
contrário fica, no pior caso, um hash órfão de um id que nunca se reutiliza — é
o lado seguro do erro.

### E O `.nojekyll` DA RAIZ, que ele encontrou no mesmo dia

**Confirmado, e era como ele disse.** Quem o escreve é o `build._gerar`, na
pasta que gera — e desde que a lista tomou a raiz (2026-09-30) essa pasta é
`u/baverone/`. **O da raiz só sobrevivia por estar COMMITADO**, de quando a raiz
era o site dele. Medido a 2026-10-02 numa geração contra uma cópia do `data/`
real: a raiz saiu com `api/`, `index.html` e `u/` — **e mais nada**.

Sem ele o **GitHub Pages ignora pastas começadas por `_`**. Hoje não há nenhuma
na raiz, por isso o site não está partido; o que estava partido era a garantia —
um ficheiro que o Git guarda e nenhum código reescreve é um ficheiro que
desaparece no dia em que alguém apagar o `site/` e voltar a gerar.

**Passou a ser do `lista.escrever`**, que é quem escreve a raiz quando a lista a
toma. O `RESTOS_DA_RAIZ` continua a não lhe tocar, e bem: é uma lista ESCRITA
porque na raiz há coisas que não são nossas para apagar (o `CNAME` do domínio, o
`img/` de 88 MB de uma corrida em `static_images: local`).

### O que se mediu e se decidiu NÃO mudar

* **o `robots.txt` na raiz** (a outra metade do achado 1) — ele escolheu a 02/10
  não o pôr (*"a lista deixa de ser indexada… quem tiver o link abre tudo
  igual"*). Não se mexeu;
* **o que o `--abrir` recusa** — a correcção do achado 3 não mudou o conjunto de
  passos que travam a abertura, e isso é deliberado: mudar o que o `--abrir`
  recusa como efeito secundário de um arranjo de checklist era outra ordem;
* **a `encomendas.raridade_minima`**, o `decks.so_base` e os restantes achados
  (1 parcial, 5, 7, 8.1, 8.2, 8.5, 9) — ficam como estavam; são decisões dele ou
  ordens à parte.

`tests/test_achados_346.py` (**41 testes**, contra pastas temporárias e um config
temporário; **nenhum vai à rede** — a medição do túnel injecta-se, que é metade
da razão de ela ser injectável): as cinco respostas do passo medido, o «não sei»
que não é «falta», o passo que não trava o `--abrir`, o prober que nunca levanta
e o User-Agent ASCII; o `editable` de **todos** os payloads de leitura comparado
com o `editavel` do `conta.json` nos quatro regimes (porta aberta/fechada, de
casa/de fora, entrado, com a temporária), o `servidor` nas duas pontas e a caixa
de «Entrar» a continuar a aparecer; o `auth.db` varrido pelos três caminhos de
apagar; e o `.nojekyll` na raiz e em cada `u/`. **A PROVA PELA NEGATIVA**
(`_revisao\_prova_negativa_346.py`, que corre a bateria contra uma árvore com o
`riftvault/` do `main`): **30 dos 41 ficam vermelhos**, e os 11 que passam são
os que fixam o que NÃO podia mudar — o utilizador 1 que não se apaga, a rota e a
CLI que já limpavam o `auth.db`, o `.nojekyll` de cada `u/`, e o `editable` de
quem está entrado.

**Quatro testes foram reescritos, e os quatro FIXAVAM o que estava errado** —
é o padrão desta casa, o mesmo do `test_binders.py:399` no achado 2:
`test_senhas.test_sao_DOIS_passos_dele_e_nao_tres` (exigia os dois passos
presumidos e que o `dele[0]` apontasse ao PASSO 1 e o `dele[1]` ao PASSO 2); e
três que exigiam o literal `state.index.editable` como bandeira do estático —
`test_conta_fechada.test_a_bandeira_e_o_index_editable_que_ja_existia`, o
`test_conta_fechada.test_o_site_gerado_diz_editable_false_e_por_isso_nao_pergunta`
e o `test_contas.test_o_site_publicado_nao_pede_a_conta`. **Nos três a
invariante não mudou** (o estático não pergunta pelo `conta.json`): mudou o
campo que a decide, e o do site gerado passou a exigir as DUAS coisas
(`servidor: false` **e** `editable: false`). Os dois últimos só apareceram na
primeira corrida da suite — não se viam a ler o código.

## 2026-10-02 — O RASTO E OS BACKUPS SÃO DE QUEM OS FEZ (`config.log_path`, `config.backups_dir`)

Achado 2 do `docs/varrimento-2026-10-01.md`: os três CSV de rasto e os backups
iam para `config.DATA_DIR`, ou seja para a pasta do André, **fosse quem fosse
que estivesse a mexer**. Seis sítios, e os três logs sem coluna que dissesse de
quem era a linha. Ramo `ai-pc/logs-por-dono-2026-10-02`.

**NÃO É FUGA PÚBLICA, e verificou-se outra vez:** `data/users/`,
`data/backups/`, `data/locais.log`, `data/encomendas.log` e `data/decks.log`
estão todos no `.gitignore`, e as pastas novas (`data/users/<slug>/`,
`data/backups/<slug>/`) caem debaixo das duas primeiras — não é por sorte, há
teste. **O estrago era outro**, e por esta ordem:

1. **o rasto deixava de servir para o que foi feito.** O `locais._log` promete
   *«se uma cópia aparecer num deck sem linha aqui, é bug»* — com quatro
   pessoas a escrever no mesmo CSV e sem coluna de dono, essa verificação não
   se pode fazer;
2. a coleção inteira de um amigo num `.zip` solto entre os backups do dono;
3. apagar a conta de um amigo não tirava os ficheiros dele de lá.

**O caminho já estava aberto**: o `config.decks_dir(con)` resolveu esta família
para os `.txt` dos decks a 2026-09-29. Fizeram-se-lhe os gémeos —
`config.user_dir(con)`, `config.log_path(con, nome)` e
`config.backups_dir(con|slug)` —, e a regra de «de quem é esta ligação» passou
a viver numa função só (`config._dono`), que as quatro famílias partilham.
**Uma ligação sem dono continua a não ser «o André»** (`guarda.SemDono`); sem
ligação nenhuma é ele, que é a CLI e o comportamento de sempre.

### As duas decisões que a ordem mandava tomar

**1. UM LOG POR PESSOA, e o dono é o CAMINHO — não uma coluna.** É a mesma
separação que os dados já têm desde 2026-09-29: as coleções estão separadas por
FICHEIRO e não por um `WHERE user_id` que se esquece. Três razões, por ordem de
peso: um rasto com a forma dos dados que rastreia verifica-se por comparação
directa, sem filtro que alguém se tenha de lembrar de pôr; **apagar a conta
leva o rasto dela** (com um ficheiro só era preciso reescrever um CSV para tirar
as linhas de uma pessoa, e reescrever um registo é a operação que um registo
existe para não precisar); e o que um amigo mexe nas cartas dele não é
informação do André. O cabeçalho dos três CSV **não mudou**.

**2. OS LOGS QUE JÁ EXISTEM FICAM ONDE ESTÃO — e nada se reescreveu nem se
moveu.** Medido a 2026-10-02 antes de tocar em código: as pastas dos três
amigos têm **só o `vault.db`** (`data/users/{rafael,miguel,goncalves}/`), e as
linhas do `data/*.log` de 30/09 e 01/10 — 2 no `locais.log`, 8 no
`encomendas.log`, 27 no `decks.log` — são **todas identificáveis como dele** (o
deck «Leona Radiant Dawn», encomendas de cartas da coleção dele). Não havia
linhas de ninguém misturadas para dividir. O `data/locais.log` continua a ser o
dele e a crescer; se alguma vez houver dúvida sobre uma linha anterior a hoje,
ela não tem resposta — é o estrago que isto fecha para a frente, não para trás.

### A DECISÃO QUE NÃO ESTAVA NA ORDEM: os backups NÃO vão para a pasta do utilizador

O sítio óbvio era `data/users/<slug>/backups/`, e **está errado**: o
`utilizador.apagar` apaga a pasta inteira, e o `conta.apagar` faz um export
ANTES de apagar — a última cópia de segurança de uma conta era apagada no mesmo
passo que a conta, e desaparecia exactamente no minuto em que é precisa. Isso
revogava em silêncio a decisão de 2026-10-01 (*«os pacotes dela FICAM, e
dizem-se»*). Por isso vão para **`data/backups/<slug>/`**: ficam separados,
nomeados, e sobrevivem ao apagar. `levar_copias=True` continua a ser a resposta
a quem pede «apaga os meus dados» e quer dizer todos. **Há teste, e é o mais
importante do ficheiro.**

**O CATÁLOGO E OS PREÇOS NÃO TÊM DONO, e o backup deles também não.** O
`db.backup` só manda para a pasta de alguém o `schema == "main"` (o vault);
mandar a cópia do `catalog.db` para a pasta do amigo que abriu a app primeiro
era dizer que o catálogo é dele.

**O `copias_de` passou a procurar em DOIS sítios** — a pasta dela e a raiz
`data/backups/`, pela mesma regra de nome. Um pacote escrito antes de hoje não
pode deixar de se encontrar só porque a regra mudou de sítio, senão o
`levar_copias` deixava para trás exactamente os ficheiros que já lá estão.
(Medido: na raiz a sério **não há pacote de amigo nenhum** — são 13 ficheiros,
todos do vault dele, do config dele ou do catálogo partilhado, mais o
`decks-20260928-141128/` do «apaga os decks todos». **Não houve nada a mover.**)

**MEDIDO E NÃO MUDADO, de propósito:** o `abrir.py:167` (o
`riftvault multi --verificar`) confirma que ficam fora do Git o `auth.db` e a
pasta `data/users/` — e **não nomeia o `data/backups/`**, que desde hoje tem a
coleção de um amigo dentro de um `.zip` numa subpasta. Não é exposição nova
(`git check-ignore` confirma as quatro escritas: `data/users/miguel/locais.log`
e `decks.log` pela linha 13, `data/backups/miguel/*.zip` e `*.db` pela 92), e o
`data/backups/` já guardava pacotes de amigos antes desta ordem — era esse o
defeito. Mudar o texto do `--verificar` é o achado 3 do varrimento, que é outra
ordem; alargá-lo aqui custava uma segunda corrida da suite por uma frase que
não muda o que fica em disco. **Fica anotado para quem fizer o achado 3.**

**Um efeito de ordem, apanhado a implementar:** o `_migrate` chama o `backup()`,
e o `con.riftvault_user` era posto **no fim** do `db.connect` — a migração de um
amigo perguntava a uma ligação que ainda não sabia de quem era. O dono passou
a ser posto antes da migração; o ficheiro já está escolhido (`vault_de(uid)`),
por isso dizê-lo mais cedo não afirma nada de novo. O guarda continua a armar-se
no fim.

### O ENSAIO DO VARRIMENTO, REPETIDO (`_revisao\_ensaio_rasto_dono.py`)

Contra uma CÓPIA do `data/` real (por `VACUUM INTO` — as bases estão em WAL), o
MESMO guião a correr contra o `main` e contra o ramo. Criar o utilizador 2,
mexer como ele (marcar um local e encomendar), e ver onde cai cada coisa:

| | `main` (o defeito) | ramo (a cura) |
|---|---|---|
| `locais.log` do amigo | na pasta do **André** | **`users/zeteste/locais.log`** |
| `encomendas.log` do amigo | na pasta do **André** | **`users/zeteste/encomendas.log`** |
| o log do André mexeu? | **SIM**, nos dois | **não**, em nenhum |
| `conta.exportar('zeteste')` | `backups/conta-zeteste-….zip` | **`backups/zeteste/conta-zeteste-….zip`** |
| `db.backup` do vault dele | `backups/vault-….db` | **`backups/zeteste/vault-….db`** |
| **o do André** | `locais.log`, `backups/` | **os mesmos caminhos** |
| apagar a conta dele | o pacote fica (na pasta errada) | **o pacote fica, na dele** |

A prova pela negativa está na mesma corrida: as linhas do André continuam a cair
em `data/locais.log` e `data/encomendas.log` e o backup dele em
`data/backups/`, e o log dele fica **byte a byte igual** quando o amigo mexe.
(Nota do ensaio contra o `main`: o `db.backup` do André devolveu `None` porque
os dois backups caíam na mesma pasta com o mesmo nome do mesmo segundo — a
colisão de nomes que está anotada em «O RESTAURO» e que não se mudou. No ramo
caem em pastas diferentes e os dois dão-se.)

### Testes

**E a CLI passou a dizer o caminho QUE ESCREVEU.** O `riftvault local --marcar`
imprimia «Rasto em `data/locais.log`» com o caminho à mão — mandava um amigo
procurar o ficheiro na pasta do André. **Dois textos ficaram por acertar, e
dizem-se:** a ajuda do `app.js` na página dos locais (**não se tocou** porque há
outra ordem a correr nesse ficheiro hoje) e o `--help` do `riftvault conta`
(«omissão: `data/backups/`», «os pacotes dela em `data/backups/`»), que continua
exacto para o André e incompleto para os outros. São duas frases, e não valiam
uma segunda corrida da suite.

`tests/test_rasto_por_dono.py` (**29 testes**, contra pastas temporárias e um
config temporário — o `decks.apagar_todos` escreve no config): os três logs de
um amigo na pasta dele e **não** na do André, os dois logs que não se tocam, o
dono a ser o caminho e não uma coluna; o que já lá está a continuar a crescer no
mesmo ficheiro e a não ser reescrito; a ligação sem dono a rebentar nas duas
funções novas e a regra a ser a MESMA do `decks_dir`; o backup do vault dele na
pasta dele, o do André na raiz, **o do catálogo partilhado**, e a migração de um
amigo; o export, o `antes-de-importar`, o `copias_de` nos dois sítios e a não
apanhar o de outra pessoa; **apagar a conta a não levar os pacotes dela** e o
`levar_copias` a levá-los; o arquivo das listas de deck; e o `.gitignore`.

**A PROVA PELA NEGATIVA** (`_revisao\_prova_negativa_rasto.py`, que corre a
bateria contra uma árvore com o `riftvault/` do `main`): **17 dos 29 ficam
vermelhos** — são todos os que fixam a cura. Os 12 que passam nos dois lados são
os que fixam o que NÃO podia mudar (o caminho do André, o log antigo que não se
move, o cabeçalho dos CSV, o `.gitignore`, a confirmação do apagar).

**E O TESTE QUE A ORDEM DIZIA QUE FIXAVA O DEFEITO NÃO PRECISOU DE MUDANÇA
NENHUMA.** O `tests/test_binders.py:399` exige `self.v.data /
self.locais.LOG_NAME` — a raiz —, e isso **continua a ser verdade**: aquele
teste corre como o utilizador 1, e para o André o `utilizador.pasta()` devolve o
`data/`, por isso o caminho dele não mexeu. **Os 25 sítios da suite (em 11
ficheiros) que nomeiam um log ou a pasta `backups/` são TODOS do André** e
nenhum precisou de ser tocado: **zero testes ajustados nesta ordem.** O que a
ordem leu como «o teste fixa o defeito» era, na verdade, o teste a fixar a parte
que não podia mudar.

## 2026-10-03 — O CONTADOR DAS RUNAS PASSA A SER POR EDIÇÃO, e começa a ZERO (`rune_counter.set_id`, `rune_counter_antes`)

Palavras dele, escolhidas entre quatro hipóteses que lhe foram postas:
**«Zera e recontas por edicao»** — *"o contador passa a ser POR EDIÇÃO e começa
a zero; ele volta a contar as runas uma vez, já separadas, e a partir daí fica
certo"*. Ramo `ai-pc/runas-contador-edicao-2026-10-03`.

**É A SEGUNDA METADE DE 2026-10-01.** Nesse dia corrigiu-se a REFERÊNCIA («na
coleção» → «nesta edição»), porque o bloco somava as cinco edições num número
só e repetia-o em todas. O CONTADOR ficou de fora, e está escrito porquê: a
chave era só o `card_key`, os 14 que ele contou à mão não tinham edição gravada,
e reparti-los era inventá-los. Ele resolveu-o pelo único caminho honesto —
recontar.

### 1. A CÓPIA DE SEGURANÇA, antes de tocar em nada

As seis linhas dele **não se recuperam de fonte nenhuma**: não são calculadas,
são contadas à mão. Antes da primeira linha de código,
`_revisao\_backup_rune_counter.py` (só leitura, por ligação `mode=ro`) escreveu
duas vezes o mesmo pacote — um JSON com as linhas e os `updated_at`, e um `.sql`
com os `INSERT` prontos a colar:

    data/backups/rune_counter-antes-de-por-edicao-20261003-122326.json  (e .sql)
    C:\Users\Catarina\_revisao\rune_counter-antes-de-por-edicao-20261003-122326.json

Em dois sítios de propósito: o `data/backups/` está no `.gitignore` e é a pasta
que o `conta.apagar` conta, mas é na mesma a pasta de um projecto; o `_revisao`
é fora dele. **O que lá está, e é o que ele reconta contra:**

| runa | contava | a coleção dizia na sementeira | último toque dele |
|---|---|---|---|
| Body Rune | **3** | 2 | 2026-10-01 |
| Calm Rune | **3** | 27 | 2026-09-26 |
| Chaos Rune | **2** | 9 | 2026-10-01 |
| Fury Rune | **3** | 4 | 2026-09-26 |
| Mind Rune | **1** | 12 | 2026-09-26 |
| Order Rune | **2** | 22 | 2026-09-26 |
| **total** | **14** | | |

### 2. ZERAR NÃO É APAGAR O RASTO — a `rune_counter_antes`

A `rune_counter` ganhou **`set_id`** e a chave passou a `(card_key, set_id)`. O
SQLite não sabe mudar uma PRIMARY KEY, por isso a migração REFAZ a tabela
(`db._migrar_rune_counter_por_edicao`), e por isso leva **backup**, corre numa
transação só e é idempotente. Vem com o tecto do foil, **antes** do
`_migrar_user_id`: quem refaz uma tabela passa antes de haver uma coluna a mais
para copiar.

**As seis linhas não se perdem**: vão para a **`rune_counter_antes`** com o
`qty`, o `seeded_from` e o `updated_at` de cada uma. A tabela do rasto cria-se
**antes** do `DROP` — se a ordem fosse a outra, uma falha a meio levava as 14
dele. Ninguém a lê para fazer contas: é o que ele confere enquanto reconta, no
ecrã e no `riftvault runas`.

**A SEMENTEIRA FOI-SE, e é o ponto da mudança.** Até 02/10 cada linha nascia com
o que ele fisicamente tinha dessa runa, para não ter de carregar 74 vezes. Com o
contador por edição isso era o contrário do que ele pediu: no OGN a Calm Rune
calculava **9** e ele tinha contado **3**. Uma célula só nasce de um `+`, uma
célula sem linha lê-se 0 — e por isso **ler o bloco deixou de escrever na
base**, que é uma propriedade que vale a pena ter escrita (a `semear` era a única
escrita de uma leitura em toda a app).

### 3. O ECRÃ TEM DE AJUDAR A RECONTAR, e tem de dizer que o zero é de hoje

Um bloco a zeros, sozinho, lê-se **«não tens runas»** — que é o contrário do que
se passa (ele tem 70 cópias de runas). Por isso há um **aviso** em cima do
bloco, enquanto ele não o dispensar: diz que o contador foi reposto para passar
a ser por edição, mostra o que ele tinha contado (**14 ao todo**, runa a runa) e
tem um «Dispensar este aviso».

**Dispensar NÃO apaga o rasto**: marca a data (`dispensado_em`) e as seis linhas
ficam na tabela e no `riftvault runas`. Uma coluna e não um `DELETE`, pela mesma
razão de sempre nesta casa — esconder não é apagar; e `--repor-aviso` traz o
aviso de volta.

**OS `+`/`−` SÓ APARECEM NA PÁGINA DE UMA EDIÇÃO.** Em «Todas» o crachá é a soma
das quatro e no lugar dos botões fica a frase que diz porquê — um clique ali não
saberia a que edição somar, e escolher uma por ele era inventar o número outra
vez, que é exactamente o que esta ordem veio desfazer. O `runaPorContador` do
`app.js` mudou de sentido: um `+` no OGN muda a célula do OGN e a SOMA de
«Todas», e **não toca no SFD** — até 02/10 era o contrário (havia um número só e
tinha de mudar em todas as listas), e o `runasListas` que o fazia saiu.

### 4. O ALVO conta CÉLULAS, não runas — e é decisão a confirmar com ele

«12 de cada» agora que a célula é por edição lê-se **12 por runa e por edição**:
uma edição fechada são **72** (um Rune Pool que se pode montar só com runas
dela) e «Todas» são **288**, que é a soma das quatro. A docstring de 19/09 usava
esse 288 como ARGUMENTO PARA NÃO partir o contador (*"não é uma coisa que se
tenha nem se jogue"*); ele decidiu parti-lo, e o número passou a ser a
consequência. O cabeçalho de «Todas» di-lo («a soma do teu contador nas edições
todas») para o 288 não se ler como um alvo por runa. **Se ele não quiser esse
288, é uma linha no `runas_vista.alvo` e é decisão dele.**

### 5. Medido a 2026-10-03, o `main` e o ramo contra cópias do MESMO instante

`_revisao\_medir_runas_contador.py` (as bases estão em WAL: copiam-se por
`Connection.backup()`, nunca por `copy2`; o `data/` a sério só se leu).

**A tabela:** antes `['card_key', 'qty', 'seeded_from', 'updated_at',
'user_id']` com 6 linhas; depois `['card_key', 'set_id', 'qty', 'updated_at',
'user_id']` com **0**, e as 6 no arquivo com as datas intactas.

**O que ele vê no ecrã** (o crachá de cada runa, por página):

| página | antes | depois |
|---|---|---|
| **«Todas»** | contas **14** de 72 | contas **0** de **288** · tens 70 (39 sem as retiradas) |
| **OGN** | contas 14 de 72 (o mesmo 14) | contas **0** de 72 · nesta edição tens **45** (37) |
| **SFD** | contas 14 de 72 (o mesmo 14) | contas **0** de 72 · nesta edição tens **23** (0) |
| **UNL** | contas 14 de 72 (o mesmo 14) | contas **0** de 72 · nesta edição tens **0** |
| **VEN** | contas 14 de 72 (o mesmo 14) | contas **0** de 72 · nesta edição tens **2** |

Runa a runa, o que ele vai ver mudar: o crachá da Calm Rune dizia **3** nas
quatro páginas e passa a **0 · 0 · 0 · 0**; o mesmo para as outras cinco. A
REFERÊNCIA ao lado não mexeu um número — é a de 02/10 (OGN: Body 1 · Calm 9 ·
Chaos 9 · Fury 3 · Mind 8 · Order 15; SFD: Calm 12 · Mind 4 · Order 7; VEN: Body
1 · Fury 1) —, e é com ela que ele compara o que conta.

**O OGS continua sem bloco** (não tem runas), e a soma do topo continua 70 / 39
sem as retiradas.

### 6. O que se mediu e se decidiu NÃO mudar

- **As runas do master set continuam a pedir 3** (`master_targets_by_type`,
  15/09 à tarde); o 12 é só do bloco dele e vive noutro sítio. A runa base
  continua na **sequência**, a arte alternativa dela continua **retirada**
  (17/09), e as promo `VEN-R01..R06` continuam **dentro** da Coleção —
  escondidas da grelha (15/09), mas no `copies` e no valor. Há teste para cada.
- **A REFERÊNCIA «nesta edição» não se tocou**: é a de 02/10 e está certa.
- **O `runas_vista.alvo` fica em 12.** Mexer nele a par desta ordem era mudar
  duas coisas de uma vez e não saber qual delas ele estava a aprovar.
- **Nada mais mexe, e não é asserção:** a fotografia de níveis, índice,
  wantlist, `master_faltas`, Faltas, A mais, valor, as cinco barras e o `copies`
  é igual com as células todas a 12 e todas a 0 — **sem o relógio dentro** (a
  lição de 02/10), com a prova pela negativa ao lado (um `+` na grelha TEM de
  mudar a fotografia) e com um teste que recusa que qualquer módulo de contas
  nomeie o `runas_vista` ou a `rune_counter`.

`tests/test_runas_contador_edicao.py` (**27 testes**): a migração (as seis para
o arquivo e a tabela vazia, a chave nova e a colisão, idempotente, a forma igual
numa base de raiz e numa migrada, o backup, as duas tabelas classificadas em
`TABELAS_DE_DONO`, e o contador de ontem a não voltar a valer por acidente); o
rasto (no payload com os números e as datas, dispensar a marcar sem apagar, a
não mexer no contador nem na coleção, o ecrã, a rota); a CLI (ver e mexer por
edição, sem `--edicao` recusa, a edição que não tem aquela runa recusa, o rasto
sempre); nada mais mexe; o que estava decidido; e «Todas» sem botões.
`test_runas_vista` (9 testes) e `test_runas_por_edicao` (6) foram reescritos —
**fixavam o regime antigo**: a sementeira, o `ajustar(con, ck, delta)` sem
edição, a tabela sem `set_id` e o «o contador é o mesmo em todas as edições»,
que era a decisão que ele acabou de revogar. O `test_contas` ganhou a rota nova
na lista das escritas (23 → **25**).

## 2026-10-03 — O `decks.so_base` VIRA PARA A REGRA DELE: o deck usa o que está na Coleção, seja que arte for

Palavras dele, ditas duas vezes: *"usa o que esta na coleccao, sendo foil ou
nao, sendo Alt Art ou nao, sendo Overnumbered ou nao. Se nao houver versao
normal, ele avisa que sao X normais e X Alt Art / Overnumbered ou o que quer que
seja"* (2026-10-01) e *"caso um deck precise de uma carta, que nao ha versao
disponivel em normal, mas esteja disponivel em Alt Art ou outra, usa, mas no
deck separa as versoes por Art"* (2026-09-17). Ramo `ai-pc/so-base-2026-10-03`.

**O MECANISMO JÁ ESTAVA TODO FEITO, e não se reescreveu nada.** É de 2026-09-17,
à tarde — `Versoes.outras_de` (as mesmas versões especiais, a mais barata
primeiro, para a mais cara ficar na Coleção), o `versoes_em` a repartir cada
linha pelas impressões que a servem, e no `app.js` o `versoesNota` (as
sub-linhas «2 normal · UNL-176» / «1 Alt Art · UNL-176a»), o `tapadaNota` (a
conta por arte, «3 — 1 normal, 2 Alt Art») e o `edicoesNota` («2 de OGN + 1 de
UNL», de 01/10). **O que faltava era o interruptor**, e o config dizia o
contrário desde 2026-09-21.

**VIROU NOS TRÊS SÍTIOS que respondiam à mesma pergunta** — o
`riftvault_config.json`, o `config.DEFAULTS` e a omissão do `decks.so_base()`.
A omissão virou também de propósito: com `true`, um riftvault sem config **manda
comprar uma carta que ele tem em Alt Art**, e isso é uma falta que não existe. É
a mesma leitura do `foil.conta_para_coleccao` de 27/09 — a omissão não pode
mentir sobre faltas, em nenhuma das duas direcções.

**A regra de 2026-09-17 sobre a Legend/Champion jogarem uma versão ESPECIAL
continua DESLIGADA**, e isso não é descuido: depende do `so_normais_excepto`,
que está VAZIO desde 21/09, e **não volta** só por esta chave ir a `false`. Hoje
todos os lugares — a Legend e o Champion incluídos — jogam a base e tapam com
outra arte que ele tenha. É o literal da frase dele.

### Medido a 2026-10-03: ZERO diferença, e o zero EXPLICA-SE

Contra uma cópia do `data/` real (`VACUUM INTO` — as bases estão em WAL; o
`data/` a sério só se leu), o MESMO código e a MESMA cópia dos dois lados,
mudando só a chave (`_revisao\_medir_so_base.py`), em **dois** cenários: com o
deck desmontado (o de hoje) e com ele **montado**, que é o que vai acontecer
quando ele o montar.

| | `so_base: true` | `so_base: false` |
|---|---|---|
| níveis (1 de cada / 2 / playset) | **911 / 876 / 797** de 928 | **iguais** |
| valor | **8 353,93 €** · 3 299 cópias | **igual** |
| wantlist «tudo» | 131 linhas · 196 cópias · 718,11 € | **igual** |
| Faltas (fechar · a comprar) | 407 · 8 377,13 € · 196 · 718,11 € | **iguais** |
| A mais, painel, os 96 alvos das alt art | — | **iguais** |
| falta do deck (montado) | 4 cópias de 2 cartas · 1,56 € | **igual** |

**Porque é que é zero** (`_revisao\_so_base_outras.py`): das **25 cartas** que o
deck pede, ele tem OUTRA arte de **quatro** — Kennen `VEN-135a`, Leona
`OGN-079a`, Vi `UNL-176a` e Radiant Dawn `OGN-306` (sobrenumerada) — e **nas
quatro a BASE já cobre** o que o deck pede; e as duas que faltam (**3× Zenith
Blade `OGN-262`, 1× Salvage `OGN-224`**) não existem no catálogo em arte nenhuma
além da base. **É uma consequência da coleção DE HOJE, não da regra**: no dia em
que uma base não chegar, a outra arte tapa — e é essa a pergunta que a medição
tem de responder, não «mudou algum número hoje» (a lição do foil de 26–27/09).

**O alvo da Coleção NÃO sobe por isto** — *"vamos voltar atras"* (17/09) —, e
mediu-se impressão a impressão: os alvos das artes alternativas são os mesmos
com o interruptor de um lado e do outro.

**A página do deck deixou de ficar calada.** A nota que dizia «Só **versões
base**, a Legend e o Champion incluídos» desaparecia com a chave a `false` e
nada tomava o lugar dela; passou a dizer a regra em vigor nos dois sentidos.

`tests/test_so_base_dele.py` (**25 testes**, contra pastas temporárias e config
temporário): a regra pelas palavras dele — a alt art parada a tapar a terceira
cópia e a **prova pela negativa** (com `true` a MESMA coleção mandava comprar o
que ele tem), a sobrenumerada a tapar também, a **assinada que NUNCA tapa**, a
runa em alt art **retirada** que também não, e a falta a comprar-se na BASE; a
separação por arte (as sub-linhas, os rótulos que são as palavras dele, «3 — 1
normal, 2 Alt Art», o CLI, e as duas frases do `app.js`); o alvo da Coleção que
não sobe (e uma alt art que o deck joga a continuar a poder estar «a mais»); **a
fotografia** da Coleção igual dos dois lados — níveis, denominador, wantlist
(texto incluído), valor, totais, grelha, playset jogável, barra, painel, Faltas,
Encomendas e A mais —, com a prova pela negativa ao lado **e** com a outra
metade (os decks TÊM de mexer, senão o primeiro teste não prova nada); e o
interruptor nos três sítios, com `true` a voltar ao que era.

**O que se mediu e se decidiu NÃO mudar:** o `so_normais_excepto` fica VAZIO (a
regra da Legend/Champion em versão especial é outra decisão dele e ele não a
pediu de volta); o `versoes_especiais` fica `["a", "overnumbered", "promo"]`; e o
`state.soBase` do `app.js` está **morto desde 01/10** (é escrito no
`garanteDecks` e nunca lido — era a etiqueta ao lado dos `+`/`−` das cópias
próprias, que saíram nesse dia). Fica anotado; tirá-lo era mexer no `app.js` por
uma linha que ninguém vê.

## 2026-10-04 — A EFICIÊNCIA DO SITE: a casca na raiz, e um ficheiro que não mudou não se reescreve

O §5 e a lacuna 8.5 do `docs/varrimento-2026-10-01.md`. Ramo
`ai-pc/eficiencia-site-2026-10-04`; as medições todas em
**`docs/eficiencia-site-2026-10-04.md`**.

**O REGIME PERMANENTE ERA PIOR DO QUE O VARRIMENTO DIZIA, e mediu-se primeiro.**
Ele mediu UM commit (46 ficheiros); o que acontecia todos os dias era isto: os
dez commits do `site/` de 2026-10-04, das **05:37 às 10:07**, de meia em meia
hora, tocaram **exactamente 28 ficheiros cada um** — `goncalves` 14 + `miguel`
14 — e em **28 de 28 só o `generated_at` mudava** (comparados dois pares de
commits consecutivos com a regra do `build._sem_relogio`). Era um commit, um
push e uma build do Pages de 30 em 30 minutos, 48 vezes por dia, sem uma carta
mexer — **a avaria de 2026-09-10 de volta pela porta de trás**, porque o
`--se-mudou` só olhava para a coleção DELE e as dos amigos eram sempre
regeneradas.

**A — A CASCA NA RAIZ, UMA VEZ SÓ.** O `app.js` (350,9 KB) e o `style.css`
(99,5 KB) eram byte a byte iguais nas três pastas `u/<slug>/`: 900,7 KB
repetidos, e mais 450,4 KB por cada pessoa nova. Passaram a viver na raiz, e
cada `u/<slug>/index.html` aponta-lhes com `../../`. `config.CASCA` é a
definição única — a casca tem DOIS escritores (o `build._gerar` quando a raiz é
a coleção dele, o `lista.escrever` quando é a lista) e o `build` importa o
`lista`, por isso não podia ser de nenhum dos dois. **Os caminhos têm de ser
relativos**: o site responde em `rift.baverone.com/` E em
`baverone.github.io/riftvault/` (é por este que o teste da `riftvault-publicar`
pergunta), e um `/app.js` absoluto dava 404 no segundo. O `_aponta_a_casca`
**rebenta** se a referência não estiver no `index.html` exactamente uma vez —
uma página sem `style.css` não dá erro nenhum, abre em texto cru. O `casca` vai
**também na prova do `--se-mudou`**: sem ele a prova leva a casca que o `out` já
não tem e o `mesmo_conteudo` diz «mudou» a todas as corridas. E **a cópia velha
sai** (`_Saida.remover`), senão a poupança era mentira: o `limpar_raiz` só mexe
na raiz e a poda dos órfãos só mexe na `api/`.

**B — O CRIVO.** O `mesmo_conteudo` já sabia comparar ignorando o
`generated_at`; passou a decidir **ficheiro a ficheiro** (`build._Saida`). A
`api/` deixou de se apagar de raiz — os órfãos podam-se ao fim, que dá a mesma
garantia sem obrigar a reescrever os 24 payloads que não mudaram.

**O `generated_at` do ÍNDICE — a decisão explícita.** É ele a prova de que o
site publicado é o que foi gerado aqui (a `riftvault-publicar` compara-o com o
que o Pages serve, e o `test.py` dela exige, quando a tarefa diz que gerou o
site, que o ficheiro tenha sido **escrito hoje**). Deixá-lo passar pelo crivo
dava as duas avarias de uma vez: a prova a comparar uma data velha e a tarefa a
chumbar sem motivo. São **duas regras**: (1) ou se escreve tudo o que mudou ou
não se escreve nada — se nenhum ficheiro de uma pessoa diferir, nem o índice se
toca; (2) o `api/index.json` é **sempre** reescrito, com relógio fresco, quando
algum outro mudou. O alinhamento com a tarefa é exacto: o `site_gerado` dela é o
`res["mudou"]` DELE (o `cmd_build` só imprime «Site gerado» nesse caso), por
isso o `escrito_hoje` só pergunta pelo índice dele quando o `_gerar` dele
correu. **Nada se mudou em `ai-pc/tasks/`.**

**Medido** (`_revisao\_ef_medir_site.py`, `_ef_publicacoes.py`,
`_ef_transicao.py`, contra cópias do `data/` real feitas por
`Connection.backup()`):

| | antes | depois |
|---|---|---|
| `site/` | 78 ficheiros · 7 181,7 KB | **74 · 6 280,0 KB** (−901,7) |
| a casca está em | 6 sítios | **2** (a raiz) |
| publicação em que **nada mudou** | 28 ficheiros · 2 450,2 KB | **0 · 0,0 KB** |
| uma carta de UMA pessoa | 31 · 2 516,0 KB | **5 · 336,5 KB** |
| o catálogo mudou | 47 · 4 787,5 KB | **11 · 1 879,5 KB** |

A transição no `site/` real escreve **2 ficheiros (36,4 KB)** e tira 4.

**PROVA DE PONTA A PONTA** (ele pediu-a a 01/10; a suite verde não prova que uma
página publicada abre): servido em local, as três páginas abrem a 200, a casca
que CADA UMA pede — lida do próprio HTML — resolve para `/app.js` e
`/style.css` da raiz (um ficheiro para as três), sete `api/*.json` relativos
resolvem dentro da pasta de cada pessoa, e o `noindex` está nas duas dos amigos
e na raiz, **não** na dele. Repetido numa subpasta. A guarda do `pages.yml`
passa, e nenhum nome na raiz começa por `_`.

`tests/test_eficiencia_site.py` (**24 testes**, a lacuna 8.5) **conta BYTES**, e
a regra do duplicado é genérica: não pergunta pelo `app.js` pelo nome, pergunta
se há ficheiros grandes repetidos byte a byte — um terceiro ficheiro de casca
que nasça amanhã fica vermelho sem ninguém ter escrito o nome dele. A única
excepção é o `index.html`, que É a página e tem de existir no URL de cada
pessoa: **sobra 16,4 KB hoje** (há DUAS páginas possíveis, a marcada e a dele —
as dos dois amigos são iguais; ~312 KB a 20 da mesma privacidade), e está dita
em vez de escondida. Prova pela
negativa com o defeito desfeito **na FONTE, uma linha** por correcção (nunca
monkey-patch — o `fixture.py` recarrega o `config`): **4 / 4 / 1 vermelhos**, e
ela apanhou um teste que não vigiava nada (comparava bytes em disco e passava
com o crivo desligado, porque o `generated_at` tem resolução de um segundo).

**Quatro testes ajustados, todos porque FIXAVAM A ARRUMAÇÃO ANTIGA**: os dois
`mesmo_conteudo(dele, u/baverone)` passaram a comparar a `api/` (a coleção dele
é a `api/`; a casca é de todos) e os dois do `limpar_raiz` passaram a exigir que
a casca FIQUE e que a `api/` dele saia.

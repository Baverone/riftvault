# CLAUDE.md — riftvault

Contexto do projeto para o Claude Code. Lê isto antes de mexer em código.

## O que é

Gestor pessoal da coleção de **Riftbound** (TCG da Riot), do André. Python +
SQLite, mesma arquitetura do `mtgvault`. Objetivo: ter **playsets**, incluindo
artes normais **e** alternativas.

Secções: **Coleção**, **Decks**, **Quanto custa**, **Faltas** (a quarta é de
2026-09-15 ao fim da tarde — por edição, três blocos; id interno
`faltas-edicao`, `api/faltas_edicao.json`, `faltas_edicao.py`) e **A mais**
(2026-09-17 — o excedente acima do alvo e as cartas libertadas dos decks; id
`a-mais`, `api/a_mais.json`, `a_mais.py` + `uso_decks.py`; ver a secção
própria no fim deste ficheiro) e **Encomendas** (2026-09-17, à tarde — a
grelha da Coleção de Rara para cima com os `+`/`−` do que comprou e o
«Chegou»; id `encomendas`, `api/encomendas/<SET>.json` + `api/encomendas.json`,
`pending.grelha`; os controlos SAÍRAM dos tiles dos decks — ver a última
secção deste ficheiro). Há ainda o **seguir jogadores** do Piltover
Archive (2026-09-17, `seguir.py`, `riftvault seguir`; por agora só na
consola — a secção no site é a parte 2, por fazer; ver a última secção deste
ficheiro). O «Quanto custa» (chamou-se **Faltas** até
2026-09-15 de manhã e mostrou as faltas até à tarde desse dia; **desde
2026-09-15 à tarde é a TABELA DE PREÇOS** — o top 5 mais caras por raridade,
em cada edição, tenha ele ou não — ver a última secção deste ficheiro. As
secções abaixo que falam das abas «Master set», «A subir» e «A caminho» do
separador são história; o `api/faltas.json` foi apagado e partido em
`api/wantlist.json`, `api/compras.json` e `api/quanto_custa.json`. O
identificador interno continua `faltas` nos ids de DOM, na chave de estado e
no `faltas.py`, que ficou com as listas de compra dos DECKS.) (Houve uma
**Venda**, apagada a 2026-09-15 a pedido dele — ver a penúltima secção. As
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

- `data/vault.db` — a coleção e os decks. **Commitado. Só o André escreve.**
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
| 2. coleção extra | `master_set.fora_da_percentagem` = `["a", "overnumbered", "promo"]` | artes alternativas, sobrenumeradas, promos | sim — o alvo é **por categoria**, `master_set.um_de_cada` = `["overnumbered", "promo"]`: sobrenumeradas e promos **1 de cada** (15/09), **artes alternativas a playset** (18/09 — *"muda novamente: Alt Art para playset"*; pediram 1 de 16/09 a 18/09; ver a última secção deste ficheiro); **os decks nunca levantam este alvo** (17/09: os decks jogam a base, e a Legend/Champion uma versão especial) | não | **não** (15/09) |
| 3. escondidas | `master_set.escondidas` = `["-T", "*", "-R"]` | tokens, signatures e — desde 15/09 à tarde — as runas sem numeração de master set (`VEN-R01..R06`) | não | não | não |
| 4. retiradas | `runas_especiais.retiradas` = `["a"]` (`metrics.retirada`) | as **runas em Alt Art** (`OGN-007a..214a`, e as `SFD/UNL/VEN-R0Xa` do CardTrader) — desde 17/09 | **não** | não | não — e **não contam no valor nem no playset jogável**, nem no A mais, nem no Pimp; os decks jogam a runa base (e desde a noite de 17/09 **não contam runa nenhuma** — ver «as runas saem da contagem dos decks», no fim deste ficheiro) |

(O `-R` passou da lista 2 para a 3 a 2026-09-15 — ver a secção "As runas sem
numeração saem", no fim deste ficheiro. O alvo 1 das sobrenumeradas e das
promos é da mesma tarde — ver "Sobrenumeradas e promos voltam a 1 de cada",
a seguir a essa; o das artes alternativas é de 16/09. A categoria 4 é de
17/09 — ver "As runas em Alt Art saem de tudo", no fim.)

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
   duas APIs o dá, e a aba "A subir" precisa de um link. Os formatos usados
   (`cardtrader.com/cards/<blueprint_id>`, `riftscribe.gg/cards/<printing_id>`)
   são **presunção minha, por abrir e confirmar**. Ficam em `a_subir.DEFAULTS`
   e mudam-se numa linha.

---

# Decisões de implementação (2026-08-31)

## Sem acabamentos

Decisão do André: **foil e normal contam como a mesma coisa**. A tabela
`copies` é só `(printing_id, qty)` — não há coluna `finish`. O CLI aceita
`--foil` e ignora-o, para não dar erro por hábito.

O alvo do master set é por impressão, e qualquer cópia serve para o cumprir.

Se um dia isto mudar: acrescentar `finish TEXT NOT NULL DEFAULT 'normal'` a
`copies`, passar a PK a `(printing_id, finish)`, e o mesmo em `ops`.

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
- **Feito também:** o separador «Quanto custa» (2026-09-15, era «Faltas») —
  abre na «Master set», com um botão por edição do catálogo (menos o OGS) e
  «tudo», por raridade e por preço com inversor, subtotais e total, sem preço
  no fim. Só apresentação: percentagem, wantlist e valor não mexem.
- **Feito também:** o «Quanto custa» só por edição (2026-09-15, tarde) — as
  abas por deck (Staples, Por deck, Pimp decks) passaram para o separador
  Decks; nas raras, incomuns e comuns só se vêem as 5 mais caras de cada
  (`quanto_custa.top_por_raridade`), com rodapé do que ficou de fora e «ver
  todas»; épicas todas; subtotais, total e wantlist contam tudo. A língua
  das ofertas passou a config (`precos.linguas`), já era só inglês.
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
  mexem. Ver a última secção deste ficheiro.
- **Por fazer:** a parte 2 do seguir — o separador no site e a tarefa diária;
  vista "todos os decks ao mesmo tempo" (hoje vê-se deck a deck,
  com as partilhadas assinaladas); e apagar decks pela interface (hoje apaga-se
  o `.txt`).

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
pergunta para ele. Tokens, signatures e `VEN-R` continuam escondidos.
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
públicas e proíbe `/api/`, `/admin/`, `/_next/` e `/static/`. **O
`riftdecks.com` está VEDADO** pelo `robots.txt` deles ao ClaudeBot e ao
`anthropic-ai`: não se lhe toca, nem para testar.

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
   `"promo"` da lista.
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


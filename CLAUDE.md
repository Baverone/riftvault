# CLAUDE.md — riftvault

Contexto do projeto para o Claude Code. Lê isto antes de mexer em código.

## O que é

Gestor pessoal da coleção de **Riftbound** (TCG da Riot), do André. Python +
SQLite, mesma arquitetura do `mtgvault`. Objetivo: ter **playsets**, incluindo
artes normais **e** alternativas.

Secções: **Coleção**, **Decks**, **Faltas** e **Venda**.

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

Isto continua a acontecer enquanto for DHCP. A cura é o Tailscale, que dá um
endereço fixo.

Para acesso de fora, a resposta é **Tailscale** (rede privada entre os
dispositivos dele), não port forwarding nem tunnels públicos. O
`server.tailscale_ip()` deteta a tailnet e o banner de arranque mostra esse
endereço e o QR quando existe.

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
(o Azir e o Ornn jogam com elas). A percentagem de master set **não mexe**.

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
  para os decks", com o teto do playset; passá-la a cega para a Coleção fazia-a
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

**Os dois totais dos decks diferem de propósito, e agora está escrito.** O
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
- **Por fazer:** vista "todos os decks ao mesmo tempo" (hoje vê-se deck a deck,
  com as partilhadas assinaladas); e apagar decks pela interface (hoje apaga-se
  o `.txt`).
- **Por fazer, da revisão:** registar uma encomenda («a caminho») pela
  interface — hoje só pelo `riftvault pending`, e ele compra no telemóvel.

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


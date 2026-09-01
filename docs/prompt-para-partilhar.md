# Prompt para partilhar

Texto para enviar a alguém que queira construir um riftvault igual, com um
agente de código (Claude Code ou equivalente). Inclui tudo o que foi validado
contra a API real a 2026-08-31, para não ter de se descobrir outra vez.

**Não inclui a parte dos preços / valor da coleção** (CardTrader), que ficou de
fora de propósito.

---

Quero um site pessoal para gerir a minha coleção de **Riftbound** (o TCG da
Riot), com o objetivo de ter playsets, incluindo artes normais **e**
alternativas. Chama-lhe `riftvault`.

## Stack e modo de funcionamento

- Python + SQLite. Sem frameworks de frontend, sem passo de build.
- `vault.db` (a minha coleção, commitada) + `catalog.db` (cache do catálogo, no
  `.gitignore`, reconstruível).
- **Dois modos, com o MESMO frontend:**
  - **Edição (local):** `riftvault serve` levanta um servidor local (Flask) que
    serve o site e escreve no `vault.db`. Bind `0.0.0.0` e mostra o URL da rede
    local + um QR ao arrancar, para eu usar o telemóvel enquanto mexo nas
    cartas.
  - **Publicado (leitura):** `riftvault build` gera o mesmo site em estático,
    sem controlos de edição, para GitHub Pages via GitHub Actions.
  - O frontend pede sempre os mesmos URLs (`api/index.json`,
    `api/set/<ID>.json`). Em modo edição o servidor responde dinamicamente; em
    modo publicado são ficheiros reais. Um flag `editable` no payload liga e
    desliga os `+`/`-`.
- Um `CLAUDE.md` na raiz com o contexto e as decisões.

## Fonte do catálogo: API da RiftScribe

Pública, sem autenticação. Base `https://riftscribe.gg/api`.
Spec em `https://riftscribe.gg/openapi.json` — lê-a primeiro e gera os modelos
a partir dela; não assumas campos.

- `GET /api/cards` — `set_id`, `q`, `faction`, `rarity`, `type`, `types[]`,
  `domain_identity[]`, `is_banned`, `sort`, `limit` (**máximo 200**), `offset`.
  O total vem no header `X-Total-Count`.
- `GET /api/cards/{card_id}` — aceita `OGN-7`, `OGN-007`, `OGN-007a`,
  `OGN-301-star`, `OGN-301*`, `UNL-T03`.
- `GET /api/cards/filters` — `sets`, `factions`, `rarities`, `types`.

O catálogo inteiro são 7 pedidos. Faz cache local das imagens (usa os
thumbnails `medium`, ~59 KB cada; os originais são ~1,4 MB).

### O que já foi verificado contra a API real (2026-08-31)

Confirma isto rapidamente antes de começar, mas não voltes a investigar do zero:

**As variantes vêm na listagem como entradas separadas.** Não é preciso varrer
sufixos. Cada uma tem `id`, `public_code` e **URL de imagem próprios**. O campo
que as distingue é `variant`, presente na listagem e no detalhe:

| `variant` | n | significado |
|---|---|---|
| `''` | 1020 | impressão base |
| `a` | 102 | arte alternativa |
| `star` | 36 | signature (o código impresso leva `*`) |
| `t01`..`t08` | 10 | tokens |
| `r01`..`r06` | 6 | runas promo (só VEN) |
| `sp1`..`sp6` | 6 | promos especiais (só VEN) |

Nunca aparece `b` (no máximo uma arte alternativa por carta) e nenhum grupo tem
`a` e `star` ao mesmo tempo. **A ordenação `sort=default` já coloca cada
variante logo a seguir à sua base** — é a ordem que a grelha quer, não
reordenes.

São **5 edições e 1180 impressões**: OGN 352, OGS 24, SFD 288, UNL 288, VEN 228.

### Três armadilhas que custaram a descobrir

**1. `(set_id, collector_number)` NÃO é chave única.** Em VEN o mesmo número é
reutilizado por famílias diferentes:

```
cn=4 variant=""    Dune Surfer      cn=4 variant="sp4" Sett, Brawler
cn=4 variant="r04" Body Rune        cn=4 variant="t04" Recruit (NX)
```

A chave de agrupamento visual tem de ser `(set_id, collector_number, lane)`,
onde `lane` é o prefixo alfabético do `variant` (`main` para `''`/`a`/`star`,
senão `t`/`r`/`sp`). Dá 1042 grupos, nenhum sem base.

**2. A mesma carta reaparece com número de coleção próprio, até na mesma
edição.** OGN 299–310, SFD 222–251, UNL 220–238, VEN 167–197 são reimpressões
showcase — e é a essas que o `star` se agarra, não à base original. Exemplo:
"Sett, Brawler" tem 5 impressões em 3 edições (`ogn-164-298`, `ogn-164a-298`,
`sfd-232-221`, `sfd-232-star-221`, `ven-sp4-006`).

Consequência: **a carta lógica não pode ser identificada pelo número de
coleção.** Chaveia-a pelo nome normalizado. São 1180 impressões para 935 nomes
distintos, e não há dois cards diferentes com o mesmo nome.

**3. A API não sabe o que é foil.** Não existe `foil`, `finish`, `holo` nem
`treatment` em lado nenhum da spec. Se quiseres acabamentos, são conhecimento
teu, não da API.

**Mais dois pormenores:** `showcase` não é uma raridade de jogo, é um
tratamento — quase todas as artes alternativas e signatures vêm com
`rarity: "showcase"`, por isso os contadores por raridade têm de usar a
raridade da **base** do grupo, senão ficam distorcidos. E a API **não devolve o
nome das edições**, só o código (os verdadeiros são Origins, Origins: Proving
Grounds, Spiritforged, Unleashed, Vendetta).

## Modelo de dados

- **Impressão (printing)** = uma entrada da API. É o grão da coleção: a
  quantidade é por impressão.
- **Carta lógica (card)** = o nome normalizado. Uma carta tem N impressões.

Duas métricas de completude, **calculadas e mostradas sempre em paralelo**:

1. **Playset jogável** — alvo por carta lógica; qualquer impressão de qualquer
   edição conta. Alvos por tipo, configuráveis: Unit/Spell/Gear 3,
   Battlefield 1, Legend 1, Rune 12, tokens 1.
2. **Master set** — alvo por impressão. A base segue o alvo de jogo (senão uma
   Rune base pediria 3 quando o playset são 12), cada arte alternativa 1, cada
   signature 1. Configurável, incluindo por impressão.

Guarda os alvos num JSON versionado, não na base de dados.

Regista **todas** as alterações numa tabela de operações (timestamp, impressão,
delta, quantidade depois, origem web/cli) e usa-a para o `undo`.

## O site — só duas secções

### 1) Coleção

- Separadores no topo, um por edição, descobertos dinamicamente pela API.
- Grelha completa da edição, com **todas as impressões**, cada uma no seu tile.
  As variantes aparecem imediatamente a seguir à base a que pertencem,
  visualmente agrupadas (moldura e faixa lateral partilhadas) e com etiqueta do
  tipo ("Arte alt.", "Signature").
- Estado visual por tile: sem cópias → imagem dessaturada e escurecida com
  badge `0/3`; parcial → imagem normal com badge; completo → badge discreto.
- **`+` e `-` em cada tile**, sempre visíveis e grandes para dedo em telemóvel.
  Atuam na impressão daquele tile — sem menus de escolha, o tile já *é* a
  variante.
- Atualização otimista, escrita em background; se falhar, reverte e avisa. Sem
  confirmação por clique. Toast com "anular" e histórico no `vault.db`.
- **Cliques rápidos seguidos não podem perder contagens.** Não uses debounce:
  o cliente manda um **delta** com um `request_id` único e o servidor faz
  `qty = qty + delta` dentro de uma transação, com o `request_id` `UNIQUE` na
  tabela de operações. Assim nenhum clique se perde (não há janela onde dois
  colapsem num só) e um retry de rede não conta a dobrar. Testa com pedidos
  concorrentes ao mesmo tile.
- Topo: duas barras de progresso lado a lado (playsets jogáveis e master set) e
  contadores por raridade.
- Filtros: tudo / em falta / parciais; e por tipo de impressão (base, arte
  alternativa, signature, tokens e promos). Procura por nome ou código.
- **Ordenar por: nº de coleção, tipo, raridade ou custo de energia.** Nos três
  últimos, cabeçalhos de secção com a contagem. Ordena sempre o *grupo*, nunca
  o tile, e tira o critério da impressão base — senão as artes alternativas
  fogem para outra secção por causa do `rarity: showcase`.
- Guarda as preferências no browser.
- Desktop: setas para navegar na grelha, `+`/`-` para ajustar.

### 2) Decks

- Um separador por deck, listas em `decks/*.txt`. Deteta o formato; suporta
  `3 Nome da Carta` e códigos `3 OGN-045`. Deduplicação por hash do conteúdo.
- Conta contra a métrica de playset jogável (qualquer impressão serve), mas
  mostra também que impressões eu usaria.
- Lista com quantidade pedida, o que tenho e o que falta, com as linhas em
  falta destacadas.
- Cabeçalho com Legend, Champion, domínios e validação de legalidade: 40 no
  main, 12 runas, 3 battlefields, limite de 3 cópias, identidade de domínio.
- Barra de completude e lista de compras exportável para CSV.
- Conflitos entre decks: assinala quando dois decks pedem a mesma carta e não
  tenho cópias para os dois ao mesmo tempo. Vista isolada e vista de todos os
  decks ao mesmo tempo.

## Também quero

- CLI: `riftvault add OGN-100a x1`, `remove`, `set`, `undo`, `log`, `stats`,
  `find`, `sync`, `serve`, `build`. O `add`/`remove` devem aceitar qualquer
  forma de escrever a impressão (`OGN-7`, `OGN-007a`, `ogn-007a-298`,
  `OGN-299*`, `UNL-T03`) — constrói uma tabela de aliases no catálogo.

## Como quero que trabalhes

1. Confirma as variantes contra a API real e mostra-me a estrutura de uma carta
   base e de uma arte alternativa antes de escreveres código.
2. Propõe o schema SQLite e espera pelo meu OK.
3. Faz o catálogo e a vista de Coleção com UMA edição, variantes incluídas e os
   `+`/`-` a funcionar, para eu testar no telemóvel.
4. Só depois os decks.

Comentários e README em português, código em inglês. Regista no `CLAUDE.md`
tudo o que não validares contra a API real.

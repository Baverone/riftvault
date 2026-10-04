/* riftvault — frontend único.
 *
 * O MESMO ficheiro corre nos dois modos. Em modo edição, `api/index.json` e
 * `api/set/<ID>.json` são respostas do servidor Flask; em modo publicado são
 * ficheiros estáticos gerados pelo `riftvault build`. O flag `editable` no
 * payload é o que liga ou desliga os controlos de escrita.
 */

'use strict';

const $ = (s, r = document) => r.querySelector(s);
const PREFS = 'riftvault.prefs.v1';
const UNDO_MS = 9000;          // quanto tempo o toast de anular fica no ecrã
// O separador «Todas» da Coleção (2026-09-21): as edições todas seguidas na
// grelha, e o painel do topo somado. É a mesma chave do `painel.TODAS`.
const TODAS = 'all';
// O chip «Tudo» do painel (2026-09-21): todos os BLOCOS de uma edição num
// só número, cada impressão com o alvo do seu bloco. É a chave do
// `painel.TUDO`. Não confundir com `TODAS`, que é das edições.
const TUDO = 'tudo';

const state = {
  index: null,
  setId: null,
  payload: null,
  // «Estou dentro, e isto é meu?» (2026-09-29). Com as contas FECHADAS o
  // `editable` é o de sempre — um dono só. Com elas abertas passa a ser
  // `index.editable && é meu`: a coleção de outro é leitura, mesmo autenticado.
  // Desde 2026-10-02 o `index.editable` do servidor já responde a isto sozinho
  // (`rotas_conta.editavel()`); o `&& é meu` fica como segunda rede.
  editable: false,
  // O que o `api/conta.json` respondeu: a porta, a sessão, o token de CSRF e os
  // fornecedores prontos. `null` no site publicado, que nem tem essa rota.
  conta: null,
  imageMode: 'local',
  // printing_id -> cópias nos binders de COLEÇÃO (verdade local, otimista).
  // Desde 2026-09-10 não é o total físico: as que estão num deck ou no binder
  // Decks/Venda não contam para a Coleção. O total vive no `locs`.
  qty: new Map(),
  // O TOTAL FÍSICO por impressão (todos os locais) — é o tecto do contador de
  // foil (2026-09-22): uma carta não deixa de ser foil por estar sleevada.
  tot: new Map(),
  // printing_id -> cópias marcadas como foil, o conjunto das impressões que
  // têm contador (as comuns e incomuns base, fora o OGS — `foil.no_ambito`) e
  // o ALVO de foil de cada uma (2026-09-27, à noite: o `foil.alvo`, o playset
  // do tipo). É uma contagem À PARTE do `tot` e **nunca se soma a ele no
  // tile**: o crachá é as normais, esta linha é o foil.
  foil: new Map(), foilOk: new Set(), foilAlvo: new Map(),
  // Os dois preços por impressão, em cêntimos. O da FOIL (2026-09-26, à tarde)
  // só existe nas que o CardTrader tem em foil: quem não está lá conta ao preço
  // da normal — o FALLBACK, que se marca na linha e faz do valor um piso.
  preco: new Map(), precoFoil: new Map(),
  // As cópias NORMAIS que contam para o VALOR (`qty_valor` menos as foils): as
  // físicas menos as próprias dos decks. Não é o `qty` da Coleção nem o
  // `qty_total` — é o número que o servidor usa (`metrics.set_payload`), e tê-lo
  // aqui é o que faz a barra do valor bater certo com o backend.
  valNorm: new Map(),
  // Os `+`/`−` do contador de foil: fila e pedidos em voo por impressão, como
  // as runas e as Encomendas — o último a chegar é que manda.
  foilFila: new Map(), foilVoo: new Map(),
  locs: new Map(),             // printing_id -> [{loc, label, qty}]
  play: new Map(),             // card_key -> {owned, target}
  targets: new Map(),          // printing_id -> alvo do master (o do tile)
  // printing_id -> bloco da grelha: 'master' (a sequência, a única que conta
  // para a percentagem) e a coleção extra em blocos próprios a seguir —
  // sobrenumeradas, artes alternativas, promos —, pela ordem do config
  // (`metrics.ordem_dos_blocos`). Ver `metrics.BLOCOS`.
  blocks: new Map(),
  // Os ids de bloco que entram na percentagem, ditos pelo payload (`counts`).
  // A regra vive no servidor; aqui só se recalcula para as barras andarem ao
  // mesmo tempo que os +/-.
  counting: new Set(),
  // A contagem por níveis da barra (1 de cada, 2 de cada, playset) POR
  // EDIÇÃO: set_id -> [{k, done, total, missing, cents}]. Começa com os
  // números do `api/index.json` e a edição que estiver aberta passa a ser
  // recalculada localmente, como as barras. Desde 2026-09-21 só a linha «N
  // cópias a comprar» a lê — os chips passaram para o painel do topo.
  levels: new Map(),
  meta: new Map(),             // printing_id -> {name, card_key, rarity}
  pending: new Map(),          // card_key -> pedidos por responder
  tiles: [],                   // impressões visíveis, pela ordem do ecrã
  focus: -1,
  // Default: TODAS as impressões (decisão do André). O botão "Só artes base"
  // continua lá, mas não é o que se vê ao abrir.
  decks: null, deckId: null, deck: null,
  ordemFixa: false,            // a ordem vem do config (`decks.ordem`): sem botões
  // Só versões base nos decks (2026-09-21, `decks.so_base`, do `api/decks.json`).
  soBase: true,
  // O antigo `faltas.json` partiu-se a 2026-09-15 (à tarde) na wantlist da
  // Coleção (`api/wantlist.json`) e nas listas de compra dos decks
  // (`api/compras.json`). Cada um tem o pedido a caminho guardado (`*P`) para
  // não se pedir duas vezes. (A terceira parte, a tabela de preços, foi
  // apagada com o separador dela a 2026-09-19 — ver o CLAUDE.md.)
  wantlist: null, wantlistP: null, compras: null, comprasP: null,
  // O separador «Faltas» (2026-09-15, fim da tarde): `api/faltas_edicao.json`.
  // Os `+`/`−` de «já encomendei» (2026-09-27) escrevem na mesma `pending` do
  // separador «Encomendas» — um número só, duas vistas — e têm a mesma fila
  // por linha, para dois cliques rápidos serem dois pedidos e nunca um a
  // dobrar. A chave é (impressão, acabamento): a mesma carta pode estar em
  // falta nas duas metades.
  faltasEdicao: null, feFila: new Map(), feVoo: new Map(),
  // O separador «A mais» (2026-09-17): `api/a_mais.json`.
  aMais: null,
  // O separador «Venda» (2026-09-25): a venda em curso (`api/venda.json`).
  // Só o `renderVenda` o lê — marcar cartas para venda não conta para nada, e
  // as cópias só descem no «marcar como vendidas».
  venda: null,
  // O separador «Produto Selado» (2026-09-25): `api/selado.json`. Só o
  // `renderSelado` o lê — o selado NÃO entra na Coleção (nem níveis, nem
  // denominador, nem valor), e o total dele é um número à parte.
  selado: null, slQ: '',
  // O bloco «Runas — 12 de cada» do fim da Coleção (2026-09-19):
  // `api/runas.json`. Só o `renderRunasVista` o lê — não conta para nada.
  runas: null,
  // O separador «Encomendas» (2026-09-17): a grelha da Coleção de Rara para
  // cima, com o que vem a caminho por impressão (`api/encomendas/<ID>.json`)
  // e o resumo de tudo o que está a caminho (`api/encomendas.json`, para os
  // separadores e o cabeçalho). `ordered` e `qty` são a verdade local,
  // otimista, como o `state.qty` da Coleção; `fila`/`voo` são os pedidos do
  // `+`/`−` por impressão, em fila, para só o último aceitar o servidor.
  enc: { setId: null, payload: null, resumo: null, ordered: new Map(), qty: new Map(),
         fila: new Map(), voo: new Map() },
  // A grelha da Coleção ficou velha (uma encomenda mudou o «a caminho» dos
  // decks, ou um «Chegou» pôs cópias na caixa): relê-se quando ele voltar lá.
  colecaoVelha: false,
  // Se as contagens já mudaram desde que a wantlist chegou.
  wlStale: false,
  // As abas ESCONDIDAS (2026-09-25, `abas.escondidas` no config), como vêm no
  // `api/index.json`. Não há segunda lista aqui: o servidor é que decide, e
  // por isso a mesma linha de config vale no 8770 e no site publicado. Vazio
  // até o índice chegar — e é por isso que o `renderNav()` só corre depois.
  escondidas: new Set(),
  prefs: { view: 'all', stateFilter: 'all',
           kinds: ['base', 'alt_art', 'signature', 'other'],
           set: null, deck: null, faltaDeck: 0, pimpDeck: 'todos',
           // As wantlists da Coleção: até que nível se compra (1, 2, … ) ou
           // `null` para o alvo inteiro — o playset da sequência.
           wlNivel: null,
           // O painel do topo da Coleção (2026-09-21): o bloco escolhido —
           // master set, sobrenumeradas, artes alternativas, promos.
           painelBloco: 'master',
           // «Faltas»: a edição escolhida (`all` = todas, uma a seguir à
           // outra). Sobrevive ao refresh.
           feSet: 'all',
           // «A mais»: a edição escolhida, como nos outros dois.
           amSet: 'all',
           // «Encomendas»: a edição aberta (uma de cada vez, como na Coleção)
           // e o filtro — tudo, só o que vem a caminho, só o que falta.
           encSet: null, encFilter: 'all',
           // «Produto Selado»: qual dos três estados está a ver — tudo, o que
           // tem, o que não tem (e os que ainda não saíram, à parte). O
           // `selAcess` é o botão que esconde a secção dos acessórios
           // (binders e deck boxes); começa à vista.
           selFiltro: 'all', selAcess: true,
           section: 'colecao' },
};

/* ------------------------------------------------------------ preferências */

function loadPrefs() {
  try {
    const raw = localStorage.getItem(PREFS);
    if (raw) Object.assign(state.prefs, JSON.parse(raw));
  } catch (_) { /* localStorage pode estar bloqueado; segue com os defaults */ }
  // 'partial' foi absorvido por 'missing'; sem isto a grelha abria sem filtro
  // nenhum selecionado.
  if (state.prefs.stateFilter === 'partial') state.prefs.stateFilter = 'missing';
}
function savePrefs() {
  try { localStorage.setItem(PREFS, JSON.stringify(state.prefs)); } catch (_) {}
}

/* ==========================================================================
   A CASCA (2026-09-24) — navegação, cabeçalho, rotas

   Pedido do André: *"faz o mesmo rebrand para os outros projetos"*, depois de
   o mtgvault ter sido reestruturado. O que estava mal aqui era o mesmo que
   estava lá: DUAS filas de botões no topo, as duas com scroll lateral. Num
   telemóvel de 390 px a fila dos decks acabava aos 1042 px — nove botões, dos
   quais três se viam. Navegar era adivinhar o que estava fora do ecrã.

   Agora há UM sítio para a navegação: a tabela `NAV`. Dela saem a barra
   lateral (a mesma no PC e no painel ☰), as migalhas e o título de cada
   página. Uma secção nova é uma linha aqui.
   ========================================================================== */

/* Os ícones, em linha e com `currentColor` — acendem com o rótulo quando o
   item fica activo, coisa que um emoji (desenhado pelo SISTEMA, com cor
   própria) nunca fez. Geometria do conjunto Feather (MIT). */
const ICO = {
  inicio: '<path d="M3 9.5 12 2l9 7.5V20a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M9 22V12.5h6V22"/>',
  colecao: '<path d="M2 3.5h5.5a4 4 0 0 1 4 4v13a3 3 0 0 0-3-3H2z"/>'
         + '<path d="M22 3.5h-5.5a4 4 0 0 0-4 4v13a3 3 0 0 1 3-3H22z"/>',
  faltas: '<circle cx="9.5" cy="20.5" r="1.3"/><circle cx="19" cy="20.5" r="1.3"/>'
        + '<path d="M1.5 2h3.3l2.5 12.2a1.9 1.9 0 0 0 1.9 1.5h9.2a1.9 1.9 0 0 0 1.9-1.5L22.2 6H6.2"/>',
  amais: '<path d="M2.5 3.5h19v5h-19z"/><path d="M4.4 8.5V20a1.5 1.5 0 0 0 1.5 1.5h12.2'
       + 'a1.5 1.5 0 0 0 1.5-1.5V8.5"/><path d="M10 12.5h4"/>',
  decks: '<path d="M12 2.4 2.2 7.2 12 12l9.8-4.8z"/><path d="m2.2 16.8 9.8 4.8 9.8-4.8"/>'
       + '<path d="m2.2 12 9.8 4.8L21.8 12"/>',
  staples: '<path d="M22 12h-4.2l-2.9 8.4L9 3.6 6.1 12H2"/>',
  pordeck: '<path d="M12 20.5V9.5"/><path d="M18.2 20.5v-17"/><path d="M5.8 20.5v-6"/>',
  pimp: '<path d="M13.2 2 3.4 13.8h8.1l-.7 8.2 9.8-11.8h-8.1z"/>',
  encomendas: '<path d="M1.5 4h13.6v12.4H1.5z"/><path d="M15.1 8.4h3.9l3.5 3.5v4.5h-7.4z"/>'
            + '<circle cx="6" cy="19" r="2.2"/><circle cx="18.4" cy="19" r="2.2"/>',
  valor: '<path d="M22.5 6.5 13.8 15.2l-4.6-4.6L1.5 18.3"/><path d="M16.8 6.5h5.7v5.7"/>',
  montado: '<path d="M21.5 11.1V12a9.5 9.5 0 1 1-5.6-8.7"/><path d="m8 11.5 3.2 3.2L22 4"/>',
  cartas: '<rect x="3" y="3" width="18" height="18" rx="2.2"/><circle cx="8.6" cy="8.6" r="1.6"/>'
        + '<path d="m21 15.5-4.8-4.8L5.5 21"/>',
  menu: '<path d="M3.5 12h17"/><path d="M3.5 6h17"/><path d="M3.5 18h17"/>',
  venda: '<path d="M12 1.8v20.4"/><path d="M17 5.6H9.5a3.4 3.4 0 0 0 0 6.8h5a3.4 3.4 0 0 1 0 6.8H6"/>',
  selado: '<path d="M2.5 8.2 12 3.1l9.5 5.1v7.6L12 20.9l-9.5-5.1z"/>'
        + '<path d="M2.5 8.2 12 13.3l9.5-5.1"/><path d="M12 13.3v7.6"/>',
  ajuda: '<circle cx="12" cy="12" r="9.5"/>'
       + '<path d="M9.3 9.2a2.8 2.8 0 0 1 5.4.9c0 1.9-2.7 2.8-2.7 2.8"/><path d="M12 17h.01"/>',
};

/* Um nome que não exista devolve string VAZIA e não um quadrado — um ícone a
   faltar não pode tapar o rótulo que está ao lado dele. */
function ico(nome, tam = 18) {
  const d = ICO[nome];
  if (!d) return '';
  const cls = tam === 18 ? 'ico' : `ico i${tam}`;
  return `<svg class="${cls}" viewBox="0 0 24 24" aria-hidden="true">${d}</svg>`;
}

/* A NAVEGAÇÃO. `sub` é uma sub-vista da mesma secção (`#decks/staples`); sem
   ela, o item é a secção inteira. A ordem é a que ele vê na barra. */
const NAV = [
  { grupo: '', itens: [
    { sec: 'inicio', ico: 'inicio', rot: 'Início', nota: 'o painel de hoje' },
  ] },
  { grupo: 'Coleção', itens: [
    { sec: 'colecao', ico: 'colecao', rot: 'Coleção', nota: 'a grelha, por edição' },
    { sec: 'faltas-edicao', ico: 'faltas', rot: 'Faltas', nota: 'o que falta, por bloco' },
    { sec: 'a-mais', ico: 'amais', rot: 'A mais', nota: 'excedente e libertadas' },
    { sec: 'selado', ico: 'selado', rot: 'Produto Selado',
      nota: 'displays, cases, decks, bundles' },
  ] },
  { grupo: 'Decks', itens: [
    { sec: 'decks', ico: 'decks', rot: 'Decks', nota: 'as listas montadas' },
    { sec: 'decks', sub: 'staples', ico: 'staples', rot: 'Staples',
      desc: 'As cartas que <b>mais do que um deck</b> pede e que não tens em número '
          + 'suficiente — uma compra serve vários.' },
    { sec: 'decks', sub: 'pordeck', ico: 'pordeck', rot: 'Por deck',
      desc: 'A mesma falta dos decks, repartida por prioridade: o que sobra ao deck '
          + 'de baixo depois de os de cima se servirem.' },
    { sec: 'decks', sub: 'pimp', ico: 'pimp', rot: 'Pimp decks',
      desc: 'As versões alteradas das cartas que os decks jogam — arte alternativa, '
          + 'sobrenumerada, promo. É uma lista de compra, já sem o que tens.' },
  ] },
  { grupo: 'Compras', itens: [
    { sec: 'encomendas', ico: 'encomendas', rot: 'Encomendas', nota: 'o que vem a caminho' },
    { sec: 'venda', ico: 'venda', rot: 'Venda', nota: 'a conta de quem compra' },
  ] },
];

/* O título e o subtítulo de cada página. O TÍTULO é o mesmo rótulo da barra
   lateral, de propósito: carregar em «A mais» e chegar a uma página com outro
   nome é a página a discordar do menu que lá levou. */
const PAGINA = {
  'inicio': {
    sub: 'O que a coleção diz hoje — e por onde continuar.',
  },
  'colecao': {
    sub: 'A sequência do master set e a coleção extra, edição a edição. '
       + 'Os <b>+</b> e <b>−</b> mexem nas cópias que estão nos binders de coleção.',
    sub_ro: 'A sequência do master set e a coleção extra, edição a edição.',
    ajuda: '<p>A barra do <b>master set</b> conta só a sequência da edição, a playset e com '
         + 'as runas numeradas incluídas. A <b>coleção extra</b> — artes alternativas (a '
         + 'playset), sobrenumeradas e promos (1 de cada) — aparece na grelha em blocos '
         + 'próprios e <b>não entra na percentagem nem em lista de compra nenhuma</b>: '
         + 'acompanhar não é querer comprar.</p>'
         + '<p>Tokens, signatures e as runas sem numeração de master set não se mostram; as '
         + 'runas em arte alternativa estão retiradas de tudo. O bloco <b>Runas — 12 de '
         + 'cada</b>, no fim, é o contador dele: os <b>+</b>/<b>−</b> de lá escrevem numa '
         + 'tabela à parte e não contam para número nenhum do site. O <b>crachá</b> é o '
         + 'contador, igual em todas as edições; a linha de baixo, <b>«nesta edição»</b>, '
         + 'conta só as impressões da edição aberta — a arte alternativa de cada edição é '
         + 'uma carta própria.</p>'
         + '<p>Nas comuns e incomuns há <b>duas contagens separadas</b>, e nunca se '
         + 'somam: o <b>crachá</b> do tile são as <b>normais</b> contra o alvo da '
         + 'Coleção, e a linha por baixo são as <b>foils</b> contra o playset do tipo em '
         + 'foil (numa runa, 12). As foils <b>não contam</b> para os alvos, os níveis, a '
         + 'percentagem nem as listas de compra — se contassem, 2 normais e 1 foil '
         + 'liam-se «3/3» e uma falta de normais desaparecia do ecrã. <b>Contam para o '
         + 'valor</b>, ao <b>preço da foil</b> do CardTrader, e só ao da normal quando '
         + 'não há oferta foil (a linha do tile diz qual é o caso). No «A mais» não '
         + 'entram: não são excedente.</p>',
  },
  'decks': {
    sub: 'As listas montadas, o que cada uma tem e o que lhe falta. '
       + 'A ordem vem do <code>riftvault_config.json</code>.',
    // A ÚNICA `ajuda` que é função, e não texto: a última frase descreve as
    // listas de compra uma a uma, e com o «Por deck» escondido (2026-09-25)
    // ficava a explicar uma aba que já não está no índice ao lado. Uma função
    // porque a tabela é lida quando o ficheiro carrega, antes de o
    // `api/index.json` dizer quais são as escondidas.
    ajuda: () =>
      '<p>Um deck serve-se primeiro das <b>cópias próprias</b> (as que guardaste para '
         + 'ele, que nunca contam para a Coleção nem para o valor), depois do que está '
         + 'sleevado, do binder e da <b>Coleção</b>. O que não recebe é falta a comprar, '
         + 'mesmo que a carta exista num deck de cima.</p>'
         + '<p>As <b>runas não se contam</b>: o Rune Pool diz só quantas são e organizas-'
         + 'las à mão. Por isso o «tenho» é de 54 e não de 66.</p>'
         + ajudaListasDeCompra(),
  },
  'faltas-edicao': {
    sub: 'O que falta para fechar cada edição, em duas metades — as normais em '
       + 'quatro blocos e as foils à parte, cada uma com a sua wantlist.',
    ajuda: '<p><b>As normais</b>, em quatro blocos por edição: <b>Master set</b>, '
         + '<b>OverNumbered</b>, <b>Alt Art</b> e <b>Promos</b>, pela mesma ordem da '
         + 'Coleção. Cada um tem a sua caixa do Cardmarket, já preenchida.</p>'
         + '<p>Só o <b>master set</b> entra na wantlist geral da Coleção — os outros três '
         + 'compram-se pela lista própria, quando quiseres. Uma carta que já vem a caminho '
         + 'aparece marcada e não vai para wantlist nenhuma.</p>'
         + '<p><b>As foils não são faltas</b> — são complemento e indicativo, e por isso '
         + 'ficam numa metade própria, com a <b>quinta wantlist</b>: não entram na '
         + 'contagem de faltas, na percentagem da Coleção nem em nenhuma das listas de '
         + 'compra que já existem. O alvo delas é o <b>playset do tipo</b> (Unit/Spell/Gear '
         + '3, Battlefield 1, <b>Rune 12</b>) e só se listam comuns e incomuns: de rara '
         + 'para cima as cartas só existem em foil, e listá-las era duplicar a coleção.</p>',
  },
  'a-mais': {
    sub: 'O excedente acima do alvo e as cartas que os decks deixaram de pedir. '
       + 'Só mostra — nada sai da coleção.',
    ajuda: '<p>O <b>excedente</b> é <code>cópias − max(usadas nos decks, alvo)</code>: o que '
         + 'sobra depois de servir os decks e de cumprir o alvo da coleção.</p>'
         + '<p>As <b>libertadas</b> saem do registo das listas dos decks: uma carta aparece '
         + 'aqui quando a quantidade que um deck pede desce. As <b>runas nunca aparecem</b> '
         + 'em nenhum dos dois blocos.</p>',
  },
  'encomendas': {
    sub: 'A grelha da Coleção de Rara para cima, para marcares o que compraste '
       + 'e dares entrada quando chega.',
    sub_ro: 'A grelha da Coleção de Rara para cima, com o que foi comprado e '
          + 'ainda não chegou.',
    ajuda: '<p>Encomendar <b>não é ter</b>: o que está a caminho não entra na Coleção, não '
         + 'mexe na barra, nos níveis nem no valor. O que faz é <b>descontar das listas de '
         + 'compra</b>, para não mandarem comprar outra vez.</p>'
         + '<p>Carregar em <b>Chegou</b> passa as cópias para a Coleção — e isso fica no '
         + 'registo, dá para desfazer.</p>',
  },
  'venda': {
    sub: 'O que estás a vender agora e a conta para quem compra. '
       + 'Os preços são o <b>Trend do Cardmarket</b>, metido por ti.',
    sub_ro: 'A venda que estava em curso quando o site foi gerado. '
          + 'Os preços são o Trend do Cardmarket, metido à mão.',
    ajuda: '<p>O preço de cada linha é o <b>Trend do Cardmarket</b> e tens de ser tu a '
         + 'metê-lo: a app <b>não tem preços do Cardmarket</b> e não os pode ter — a API '
         + 'oficial deles está fechada a novas candidaturas e o site responde 403 a pedidos '
         + 'automáticos. Cada linha tem o link para a página da carta lá: abres, vês o '
         + 'Trend, escreves.</p>'
         + '<p>O preço do <b>CardTrader</b> que aparece ao lado é a oferta mais barata de '
         + 'lá, não um Trend — é só referência e <b>nunca entra na conta</b>. Uma linha sem '
         + 'Trend vale <b>zero</b> e o total diz quantas faltam; não se substitui por nada.</p>'
         + '<p>Marcar cartas para venda <b>não tira nada</b> da coleção: não mexe nos níveis, '
         + 'nas Faltas, no valor, nos decks nem no A mais. Quem baixa as cópias é o botão '
         + '<b>Marcar como vendidas</b>, que pede confirmação e fica no registo.</p>'
         + '<p>O Trend fica guardado por impressão com a data, para a venda seguinte já vir '
         + 'preenchida. Passados uns dias aparece marcado como velho — vale a pena '
         + 'confirmá-lo antes de cobrar.</p>',
  },
  'selado': {
    sub: 'Displays, cases, decks, bundles e Proving Grounds: o que <b>há</b>, o que '
       + '<b>tens</b> e o que <b>não tens</b>. Não entra na Coleção.',
    sub_ro: 'Displays, cases, decks, bundles e Proving Grounds: o que há, o que ele '
          + 'tem e o que não tem. Não entra na Coleção.',
    ajuda: '<p>A lista vem do <b>CardTrader</b>, que arruma os blueprints por '
         + '<b>categoria</b>: a 258 são as cartas e as outras são produto e acessórios. '
         + 'Entram seis categorias — <i>Booster Boxes, Boosters, Bundles, Starter Decks, '
         + 'Box Sets &amp; Displays, Complete Sets</i>. <b>Playmats, sleeves, moedas e '
         + 'cartas oversized ficam de fora</b>: são acessórios de jogo, não produto selado. '
         + 'O cabeçalho diz quantos são.</p>'
         + '<p>Os <b>binders e os deck boxes</b> têm uma <b>secção à parte</b>, em baixo, '
         + 'com contadores e valor próprios e um botão que a esconde: vendem-se selados e '
         + 'guardam-se, mas um binder não é um display e <b>não conta</b> para o «o que há / '
         + 'tenho / não tenho» do selado.</p>'
         + '<p>O que ainda <b>não saiu</b> aparece marcado e <b>não conta para o que falta</b> '
         + '— não se pode ter o que ainda não existe. As datas de saída vêm do config: a '
         + 'API do CardTrader não dá data nenhuma.</p>'
         + '<p>O <b>selado não entra na Coleção</b>: nem nos níveis, nem no denominador, nem '
         + 'nas Faltas, nem nas wantlists, nem no A mais, nem nos decks. O <b>valor do '
         + 'selado</b> é um total próprio e <b>nunca se soma ao valor da Coleção</b> — uma '
         + 'caixa por abrir não é uma carta no binder. O dos acessórios é um terceiro total, '
         + 'também à parte.</p>'
         + '<p>Os preços são a oferta mais barata do CardTrader, em inglês e por abrir. '
         + 'Quando o CardTrader tem <b>dois blueprints para o mesmo produto</b> (acontece nos '
         + 'Trial Decks da Origins: um par tem as ofertas todas, o outro zero) juntam-se num '
         + 'só, e a linha diz qual juntou.</p>'
         + '<p>Cada linha tem <b>link de compra</b> para o <b>Cardmarket</b> e para o '
         + '<b>CardTrader</b>. O do CardTrader está <b>confirmado</b> (o id do blueprint '
         + 'sozinho abre a página do produto); o do Cardmarket <b>não pôde ser</b> — o site '
         + 'deles responde 403 a pedidos automáticos e não há conta para experimentar. Por '
         + 'isso quem não tem id nesse mercado leva um link de <b>pesquisa pelo nome</b>, que '
         + 'diz que é pesquisa; se o link directo abrir em 404, muda-se uma linha do config '
         + '(<code>mercados</code>) e todos os links mudam com ela.</p>'
         + '<p>O que a API não tem acrescenta-se à mão em <code>selado.extra</code>, no '
         + '<code>riftvault_config.json</code>, com o <b>conteúdo</b> ao lado; os '
         + '<b>MSRP são em dólares</b> e ficam no conteúdo, nunca no preço, porque não há '
         + 'câmbio validado aqui. <b>A lista está vazia desde 28/09/2026</b>: os 17 que lá estavam — os '
         + 'displays de decks, os cases de vaults e os Pre-Rift EVENT Kit — saíram porque '
         + '<i>não têm página própria</i> em mercado nenhum, e o Cardmarket não dá página a '
         + 'displays nem a cases (vendem-se dentro da entrada do produto simples, com o '
         + 'vendedor a escrever na nota). <b>Esvaziar não é apagar</b>: o que se sabe deles '
         + 'ficou em <code>_selado_extra_arquivado</code>, e repor é copiá-los de volta.</p>'
         + '<p><b>Só impressão inglesa</b> (28/09/2026). Uma caixa da impressão chinesa não '
         + 'entra aqui, tenha oferta ou não — é a mesma regra que os preços já seguiam '
         + '(<code>precos.linguas</code>). Escreve-se à mão no <code>selado.excluidos</code>, '
         + 'porque não há campo de língua no catálogo: o marcador está no nome, na versão '
         + '(«Chinese Exclusive») ou no rótulo do Cardmarket. <b>«Slim», «Jumbo» e «Sleeved» '
         + 'são embalagens, não línguas.</b></p>'
         + '<p>O que <b>tu mandaste tirar</b> vive em <code>selado.excluidos</code>, no '
         + 'mesmo ficheiro: sai da lista, dos contadores, da percentagem e do total. '
         + '<b>Esconder não é apagar</b> — o catálogo em disco fica intacto e <b>repor é '
         + 'tirar o nome da lista</b>. O cabeçalho diz quantos são e quais.</p>',
  },
};

/* A frase da ajuda dos Decks que descreve as listas de compra, só com as que
   se vêem. Sem nenhuma, não se escreve frase nenhuma. */
function ajudaListasDeCompra() {
  const frases = {
    staples: '<b>Staples</b> são as cartas que mais do que um deck pede — uma compra '
           + 'serve vários.',
    pordeck: '<b>Por deck</b> reparte a mesma falta por prioridade.',
    pimp: '<b>Pimp decks</b> são as versões alteradas das cartas que os decks jogam.',
  };
  const texto = deckFaltaIds().map(id => frases[id]).filter(Boolean).join(' ');
  return texto ? `<p>${texto}</p>` : '';
}

/* ------------------------------------------------- as abas escondidas

   André, 2026-09-25: *"Tira a aba 'A mais', 'Por Deck' e 'Pimp Deck'"*.

   ESCONDER NÃO É APAGAR. A `NAV`, a `SECCOES`, a `DECK_FALTA_TABS` e todas as
   funções de desenho ficam exactamente como estavam — o «A mais» continua a
   ser calculado e o `api/a_mais.json` a ser pedido por quem lhe chegar. O que
   esta função faz é tirar o BOTÃO: a entrada na barra, a vista no índice dos
   decks, o atalho do Início e a rota.

   A lista vem do servidor (`api/index.json` -> `abas.escondidas`), nos dois
   modos: é a mesma linha de config a tirar a aba do 8770 e do site publicado.
   Repor é tirar o nome da lista — não há nada aqui a mudar.

   O `id` de uma aba é a ROTA quando é secção (`a-mais`) e o id da vista quando
   é sub-vista (`pordeck`). */
function abaVisivel(id) {
  return !state.escondidas.has(id);
}

/* O id da aba de um item da `NAV`: a sub-vista, quando a tem. */
function abaDoItem(it) {
  return it.sub || it.sec;
}

/* O item da barra lateral de uma secção (o primeiro sem `sub`) — é dele que
   saem o título da página e o grupo das migalhas. */
function navItem(sec) {
  for (const g of NAV) for (const it of g.itens) if (it.sec === sec && !it.sub) return { ...it, grupo: g.grupo };
  return { sec, rot: sec, grupo: '', ico: '' };
}

function navSub(sec, sub) {
  for (const g of NAV) for (const it of g.itens) if (it.sec === sec && it.sub === sub) return it;
  return null;
}

function renderNav() {
  const alvo = $('#sidenav');
  let out = '';
  for (const g of NAV) {
    // Um grupo que fique sem itens nenhuns não deixa o cabeçalho dele sozinho.
    const itens = g.itens.filter(it => abaVisivel(abaDoItem(it)));
    if (!itens.length) continue;
    out += '<div class="sgrp">';
    if (g.grupo) out += `<div class="sgh">${escapeHTML(g.grupo)}</div>`;
    for (const it of itens) {
      const href = '#' + it.sec + (it.sub ? '/' + it.sub : '');
      const cls = 'sli' + (it.sub ? ' sub' : '');
      const nt = it.nota ? `<small>${escapeHTML(it.nota)}</small>` : '';
      out += `<a class="${cls}" href="${href}" data-sec="${escapeAttr(it.sec)}"`
           + ` data-sub="${escapeAttr(it.sub || '')}">`
           + `<span class="ic">${ico(it.ico, it.sub ? 16 : 18)}</span>`
           + `<span class="tx">${escapeHTML(it.rot)}${nt}</span></a>`;
    }
    out += '</div>';
  }
  alvo.innerHTML = out;
  for (const a of alvo.querySelectorAll('a')) a.onclick = fecharMenu;
}

/* Acende o item da barra lateral. Um item COM sub-vista só acende quando a
   sub-vista é a que está aberta; o item da secção acende quando não há
   nenhuma sub-vista da lista escolhida (senão acendiam dois ao mesmo tempo). */
function marcarNav(sec, sub) {
  for (const a of document.querySelectorAll('#sidenav a')) {
    const s = a.dataset.sub || '';
    const on = a.dataset.sec === sec && (s ? s === sub : !navSub(sec, sub));
    a.classList.toggle('cur', on);
    if (on) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current');
  }
}

function renderCabecalho(sec, sub) {
  const it = navItem(sec);
  const s = navSub(sec, sub);
  const titulo = s ? s.rot : it.rot;
  const p = PAGINA[sec] || {};
  $('#pg-titulo').textContent = titulo;
  $('#topbar-tit').textContent = titulo;
  document.title = `${titulo} · riftvault`;
  // Uma sub-vista responde a outra pergunta que a secção: o «Staples» com o
  // subtítulo dos Decks por cima dizia-lhe que ia ver a lista dos decks.
  //
  // E o `sub_ro` é para a CÓPIA PUBLICADA: o subtítulo da Coleção prometia
  // que «os + e − mexem nas cópias», numa página onde eles não existem de
  // propósito. Onde não há versão de leitura, o texto serve nos dois.
  $('#pg-sub').innerHTML = (s && s.desc)
    || (!state.editable && p.sub_ro) || p.sub || '';
  // O grupo só entra quando ACRESCENTA: «Início › Decks › Decks» lia-se como
  // um erro de contagem, e é o que acontece sempre que a secção dá o nome ao
  // grupo dela.
  const meio = it.grupo && it.grupo !== it.rot
    ? `<i>›</i><span>${escapeHTML(it.grupo)}</span>` : '';
  const ate = s ? `<i>›</i><a href="#${sec}">${escapeHTML(it.rot)}</a>` : '';
  $('#pg-crumbs').innerHTML = sec === 'inicio'
    ? `<b>${escapeHTML(titulo)}</b>`
    : `<a href="#inicio">Início</a>${meio}${ate}<i>›</i><b>${escapeHTML(titulo)}</b>`;
  // «Como ler esta página»: o texto longo lê-se UMA vez e depois é só
  // distância até ao fim da página — fica fechado, com o resumo no botão.
  // `ajuda` é texto em todas as páginas menos nos Decks, onde é função (a
  // frase das listas de compra depende de quais delas se vêem — 2026-09-25).
  const ajuda = typeof p.ajuda === 'function' ? p.ajuda() : p.ajuda;
  $('#pg-ajuda').innerHTML = ajuda
    ? `<details class="comoler"><summary>${ico('ajuda', 16)}<span>Como ler esta página`
      + `</span></summary><div class="cltx">${ajuda}</div></details>`
    : '';
}

/* ------------------------------------------------- o painel ☰ do telemóvel */

function abrirMenu() {
  document.body.classList.add('menu-on');
  $('#menub').setAttribute('aria-expanded', 'true');
  try { $('#side').focus(); } catch (_) {}
}
function fecharMenu() {
  document.body.classList.remove('menu-on');
  $('#menub').setAttribute('aria-expanded', 'false');
}

function wireCasca() {
  $('#menub-ic').innerHTML = ico('menu', 17);
  $('#menub').onclick = () =>
    document.body.classList.contains('menu-on') ? fecharMenu() : abrirMenu();
  $('#veu').onclick = fecharMenu;
  document.addEventListener('keydown', e => { if (e.key === 'Escape') fecharMenu(); });
}

/* ---------------------------------------------------------------- as rotas

   `#<secção>` e `#<secção>/<sub-vista>` — a edição da Coleção, das Faltas, do
   A mais e das Encomendas, e o deck ou a lista dos Decks. Uma sub-vista com
   URL é o que deixa ligar a «as faltas do UNL» de fora da página, e é o que o
   botão «voltar» do browser passa a saber desfazer. */
function lerHash() {
  const h = decodeURIComponent((location.hash || '').slice(1));
  const [sec, sub] = h.split('/');
  return { sec, sub: sub || '' };
}

/* Escreve a rota no URL sem disparar o `hashchange` (já estamos a desenhar a
   secção — deixá-lo disparar dava um segundo desenho por cada clique). */
let aEscreverHash = false;
function escreverHash(sec, sub) {
  const novo = '#' + sec + (sub ? '/' + sub : '');
  if (location.hash === novo) return;
  aEscreverHash = true;
  try { location.hash = novo; } finally { setTimeout(() => { aEscreverHash = false; }, 0); }
}

/* ------------------------------------------------------------------ dados */

async function getJSON(url) {
  const r = await fetch(url, { cache: 'no-store' });
  if (!r.ok) throw new Error(`${url} -> HTTP ${r.status}`);
  return r.json();
}

/* Os cabeçalhos de TODO o pedido que escreve (2026-09-29).
 *
 * Havia dezassete `fetch` de POST neste ficheiro, cada um com o seu literal de
 * cabeçalhos. Acrescentar a marca de CSRF a cada um à mão era garantir que um
 * dia se esquecia num — e um esquecido é uma rota sem protecção, não um erro
 * visível. Por isso há UMA função, e o `test_contas.py` lê este ficheiro e
 * rebenta se aparecer um POST que não passe por ela.
 *
 * O token vem do `api/conta.json` e vai num CABEÇALHO, não num cookie: um
 * cookie era enviado pelo browser junto com o pedido falso de outro site, que é
 * exactamente o que isto tenta travar. Com a porta fechada não há sessão nem
 * token, e o cabeçalho sai vazio — o servidor também não o exige. */
function cabecalhos() {
  const h = { 'Content-Type': 'application/json' };
  if (state.conta && state.conta.csrf) h['X-CSRF-Token'] = state.conta.csrf;
  return h;
}

/* ------------------------------------------------------------------ conta */

/* A zona da conta na barra lateral.
 *
 * NO SITE PUBLICADO NÃO DESENHA NADA, e é a decisão dele de 2026-09-29
 * (*"Quero apenas apresentar quando tiver tudo"*): a cópia publicada fica
 * exactamente como estava, sem um «em breve» nem um link de login à espreita.
 *
 * O CRITÉRIO MUDOU a 2026-09-30, e a versão anterior era um beco. Escondia-se
 * quando a PORTA das contas estava fechada (`!c.aberto`) — mas o
 * `multi --verificar` exige que ele troque a password temporária ANTES de
 * abrir, e a troca só se faz entrando no site: não abria sem trocar e não
 * trocava sem abrir. O que ele pediu era outra coisa — não queria um link de
 * login no SITE PUBLICADO; no 8770, que é a casa dele, esconder a entrada não
 * serve ninguém.
 *
 * Hoje o critério é `state.conta` existir: o `boot()` só pede o
 * `api/conta.json` quando o `index.servidor` diz que isto é o servidor. No
 * estático não há rota nenhuma, não se pergunta, e isto fica `null` — a mesma
 * condição que já evitava um 404 na consola.
 *
 * (Era o `index.editable` até 2026-10-02. Mudou porque esse campo passou a
 * dizer a verdade sobre quem pode escrever, e com a porta aberta a verdade é
 * `false` para um leitor anónimo — que é precisamente quem tem de ver esta
 * caixa. Ver o `boot()`.) */
function renderConta() {
  const zona = $('#conta-zona');
  if (!zona) return;
  const c = state.conta;
  if (!c) { zona.hidden = true; zona.innerHTML = ''; return; }
  zona.hidden = false;

  /* 1. ENTROU COM A TEMPORÁRIA (2026-09-30). O site está trancado até trocar
   *    (`rotas_conta._trava_temporaria`), por isso esta zona é a ÚNICA coisa
   *    com que ela pode mexer — e não se mostra mais nada para não parecer que
   *    o resto está avariado. */
  if (c.entrado && c.senha_temporaria) {
    zona.innerHTML = `<div class="conta-cx">
      <b>Escolhe a tua password</b>
      <small>Estás a usar a password temporária que o André te deu. Escolhe
      uma tua para poderes usar o site — pelo menos 10 caracteres; uma frase
      curta serve.</small>
      ${trocaHTML(true)}
      <a class="btn ghost" href="sair">Sair</a>
    </div>`;
    ligarTroca(true);
    return;
  }

  /* 2. ENTROU POR UM FORNECEDOR E NÃO TEM CONTA AQUI. Não há registo aberto
   *    (2026-09-30): as contas nascem de um comando dele. */
  if (c.sem_conta) {
    zona.innerHTML = `<div class="conta-cx">
      <b>Ainda não tens conta</b>
      <small>As contas aqui não se criam sozinhas — é o André que as cria.
      Pede-lhe uma e ele dá-te um nome de utilizador e uma password.</small>
      <a class="btn ghost" href="sair">Sair</a>
    </div>`;
    return;
  }

  /* 3. O registo por fornecedor, se um dia for ligado (`REGISTO_ABERTO`). */
  if (c.registo_pendente) {
    const p = c.registo_pendente;
    zona.innerHTML = `<div class="conta-cx">
      <b>Falta escolher o teu endereço</b>
      <small>Entraste com ${escapeHTML(p.provedor || '')}. O nome que
      escolheres fica no endereço da tua coleção.</small>
      <label class="conta-lbl" for="rg-slug">rift.baverone.com/u/</label>
      <input id="rg-slug" class="conta-inp" value="${escapeAttr(p.slug_sugerido || '')}"
             maxlength="32" autocomplete="off" spellcheck="false">
      <button class="btn primary" id="rg-criar" type="button">Criar a conta</button>
      <p class="conta-erro" id="rg-erro" hidden></p>
    </div>`;
    $('#rg-criar').addEventListener('click', criarConta);
    $('#rg-slug').addEventListener('keydown', (e) => {
      if (e.key === 'Enter') criarConta();
    });
    return;
  }

  /* 4. NÃO ENTROU: o nome e a password. Os botões dos fornecedores só
   *    aparecem se ele os tiver configurado — o OAuth ficou parado a
   *    2026-09-30, e sem segredo o `pronto` vem a `false`. */
  if (!c.entrado) {
    const bts = (c.provedores || []).filter((p) => p.pronto).map((p) =>
      `<a class="btn ghost" href="entrar/${encodeURIComponent(p.nome)}">ou entrar com ${escapeHTML(p.etiqueta)}</a>`).join('');
    // A NOTA TEM DE DIZER A VERDADE NOS DOIS SÍTIOS (2026-10-01). A frase
    // «enquanto estiver fechada não precisas de entrar» é verdade em casa e
    // MENTIRA de fora: desde hoje a origem é que decide se é preciso entrar, e
    // de fora é preciso sempre, com a porta aberta ou fechada.
    let nota = '';
    if (c.exige_entrar) {
      nota = `<small>Estás a chegar de fora de casa. Daqui o riftvault pede
         sempre que entres — mesmo para ver a coleção.</small>`;
    } else if (!c.aberto) {
      nota = `<small>As contas ainda não estão abertas — isto é para tratares da
         TUA password. Em casa não precisas de entrar para usar o site, e os
         teus amigos ainda não conseguem.</small>`;
    }
    zona.innerHTML = `<div class="conta-cx">
      <b>Entrar</b>
      ${nota}
      <label class="conta-lbl" for="en-nome">Utilizador</label>
      <input id="en-nome" class="conta-inp" maxlength="32" autocomplete="username"
             spellcheck="false" autocapitalize="off">
      <label class="conta-lbl" for="en-senha">Password</label>
      <input id="en-senha" class="conta-inp" type="password" maxlength="256"
             autocomplete="current-password">
      <button class="btn primary" id="en-ok" type="button">Entrar</button>
      <p class="conta-erro" id="en-erro" hidden></p>
      ${c.aberto ? '<small>Não tens conta? Pede uma ao André — é ele que as cria.</small>' : ''}
      ${bts}
    </div>`;
    $('#en-ok').addEventListener('click', entrarComSenha);
    for (const id of ['#en-nome', '#en-senha']) {
      $(id).addEventListener('keydown', (e) => {
        if (e.key === 'Enter') entrarComSenha();
      });
    }
    return;
  }

  /* 5. Entrou, tudo normal. */
  const u = c.utilizador || {};
  const priv = { nada: 'privada', 'sem-valores': 'pública, sem valores', tudo: 'pública' };
  zona.innerHTML = `<div class="conta-cx">
    <b>${escapeHTML(u.nome || u.slug || '')}</b>
    <small>a tua coleção · <span id="ct-priv">${escapeHTML(priv[u.publico] || u.publico || '')}</span></small>
    <select class="conta-sel" id="ct-publico" aria-label="Quem vê a minha coleção">
      <option value="nada"${u.publico === 'nada' ? ' selected' : ''}>Só eu</option>
      <option value="sem-valores"${u.publico === 'sem-valores' ? ' selected' : ''}>Pública, sem os valores em €</option>
      <option value="tudo"${u.publico === 'tudo' ? ' selected' : ''}>Pública, com tudo</option>
    </select>
    <details class="conta-det"><summary>Trocar a password</summary>
      ${trocaHTML(false)}
    </details>
    <a class="btn ghost" href="sair">Sair</a>
  </div>`;
  ligarTroca(false);
  $('#ct-publico').addEventListener('change', async (e) => {
    try {
      const r = await fetch('api/conta/privacidade', {
        method: 'POST', headers: cabecalhos(),
        body: JSON.stringify({ publico: e.target.value }),
      });
      const res = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(res.erro || res.error || `HTTP ${r.status}`);
      state.conta.utilizador.publico = res.publico;
      $('#ct-priv').textContent = priv[res.publico] || res.publico;
      toast(res.publico === 'nada'
        ? 'A tua coleção deixou de ser publicada.'
        : 'A tua coleção passa a ser publicada na próxima geração do site.');
    } catch (err) { toast(`Não deu: ${err.message}`); }
  });
}

/* O formulário da troca. O MESMO nos dois sítios — quem entrou com a
 * temporária e quem quer trocar por gosto —, para não haver duas versões da
 * mesma coisa a divergir. A actual pede-se sempre: um computador deixado
 * aberto no café não pode dar a conta a quem passar. */
function trocaHTML(temporaria) {
  return `<label class="conta-lbl" for="sn-atual">${temporaria
    ? 'A password temporária' : 'A password de agora'}</label>
    <input id="sn-atual" class="conta-inp" type="password" maxlength="256"
           autocomplete="current-password">
    <label class="conta-lbl" for="sn-nova">A password nova</label>
    <input id="sn-nova" class="conta-inp" type="password" maxlength="256"
           autocomplete="new-password">
    <label class="conta-lbl" for="sn-rep">Outra vez, para confirmar</label>
    <input id="sn-rep" class="conta-inp" type="password" maxlength="256"
           autocomplete="new-password">
    <button class="btn primary" id="sn-ok" type="button">Guardar a password</button>
    <p class="conta-erro" id="sn-erro" hidden></p>`;
}

function ligarTroca(temporaria) {
  const bt = $('#sn-ok');
  if (!bt) return;
  bt.addEventListener('click', () => trocarSenha(temporaria));
  for (const id of ['#sn-atual', '#sn-nova', '#sn-rep']) {
    $(id).addEventListener('keydown', (e) => {
      if (e.key === 'Enter') trocarSenha(temporaria);
    });
  }
}

async function entrarComSenha() {
  const erro = $('#en-erro');
  const bt = $('#en-ok');
  erro.hidden = true;
  bt.disabled = true;
  try {
    const r = await fetch('api/conta/entrar', {
      method: 'POST', headers: cabecalhos(),
      body: JSON.stringify({
        nome: ($('#en-nome').value || '').trim(),
        senha: $('#en-senha').value || '',
      }),
    });
    const res = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(res.erro || res.error || `HTTP ${r.status}`);
    // A coleção passa a ser a dela: relê tudo em vez de remendar o ecrã.
    location.reload();
  } catch (err) {
    erro.textContent = err.message;
    erro.hidden = false;
    bt.disabled = false;
  }
}

async function trocarSenha(temporaria) {
  const erro = $('#sn-erro');
  const bt = $('#sn-ok');
  erro.hidden = true;
  const nova = $('#sn-nova').value || '';
  // A confirmação verifica-se AQUI e não no servidor: é um erro de escrita,
  // não uma questão de segurança, e assim ela vê-o sem esperar por um pedido.
  if (nova !== ($('#sn-rep').value || '')) {
    erro.textContent = 'As duas passwords novas não são iguais.';
    erro.hidden = false;
    return;
  }
  bt.disabled = true;
  try {
    const r = await fetch('api/conta/senha', {
      method: 'POST', headers: cabecalhos(),
      body: JSON.stringify({ atual: $('#sn-atual').value || '', nova }),
    });
    const res = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(res.erro || res.error || `HTTP ${r.status}`);
    if (temporaria) {
      location.reload();   // o site estava trancado: agora abre
    } else {
      state.conta.csrf = res.csrf;
      toast('Password trocada. As outras sessões foram fechadas.');
      $('#sn-atual').value = ''; $('#sn-nova').value = ''; $('#sn-rep').value = '';
      bt.disabled = false;
    }
  } catch (err) {
    erro.textContent = err.message;
    erro.hidden = false;
    bt.disabled = false;
  }
}

async function criarConta() {
  const erro = $('#rg-erro');
  const bt = $('#rg-criar');
  erro.hidden = true;
  bt.disabled = true;
  try {
    const r = await fetch('api/conta/registar', {
      method: 'POST', headers: cabecalhos(),
      body: JSON.stringify({ slug: ($('#rg-slug').value || '').trim() }),
    });
    const res = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(res.erro || res.error || `HTTP ${r.status}`);
    // A conta nasceu: relê tudo, porque agora há uma coleção (vazia) dele.
    location.reload();
  } catch (err) {
    erro.textContent = err.message;
    erro.hidden = false;
    bt.disabled = false;
  }
}

/* Onde está a caixa de entrar, nos dois tamanhos de ecrã. Num sítio só porque
 * é a mesma frase em dois ecrãs: a password temporária e o «entra para ver». */
const ONDE_ESTA_O_FORMULARIO =
  'O formulário está na barra do lado — no telemóvel, no botão ☰ Menu.';

/* O site está trancado — por uma password temporária (2026-09-30) ou por vir de
 * FORA de casa sem sessão (2026-10-01)? Então desenha SÓ o ecrã de entrar e diz
 * que sim.
 *
 * Chama-se quando o `api/index.json` falha, e é a rede do segundo beco de
 * 2026-09-30. Não decide nada por si: pergunta ao servidor, que é quem sabe, e
 * se a resposta não for «trancado» devolve `false` para o erro original subir —
 * um `riftvault sync` em falta tem de continuar a dizer o que é. */

async function mostrarSeTrancado() {
  const c = await getJSON('api/conta.json').catch(() => null);
  if (!c) return false;
  // DOIS MOTIVOS PARA O SITE ESTAR TRANCADO, e o ecrã é o mesmo:
  //   * entrou com a temporária e tem de a trocar (2026-09-30);
  //   * está FORA DE CASA e não entrou (2026-10-01) — de fora o servidor pede
  //     sessão para tudo, leituras incluídas, e o `api/index.json` dá 401.
  // Sem o segundo caso, quem abrisse o editar.baverone.com lia «Falhou a
  // carregar: HTTP 401» em vez de ver a caixa de entrar — era o mesmo beco de
  // 30/09 por outra porta.
  const temporaria = c.entrado && c.senha_temporaria;
  const temDeEntrar = !c.entrado && c.exige_entrar;
  if (!temporaria && !temDeEntrar) return false;
  state.conta = c;
  renderConta();
  // A NAVEGAÇÃO FICA DE FORA, e é de propósito: as abas escondidas
  // (2026-09-25) vêm no `api/index.json`, que está barrado — desenhá-la aqui
  // mostrava as três que ele mandou tirar. E enquanto o site está trancado não
  // se chega a secção nenhuma, por isso não faz falta nenhuma.
  const nav = $('#sidenav');
  if (nav) nav.hidden = true;
  // A mensagem vai para o CABEÇALHO, não para o `#grid`: as secções estão todas
  // `hidden` (o `boot()` não chegou à parte que abre uma), e uma frase dentro
  // de uma secção escondida é uma frase que ninguém lê — ficava um ecrã preto
  // ao lado do formulário, que é o que a fotografia mostrou.
  const tit = temporaria ? 'Escolhe uma password' : 'Entra para ver a tua coleção';
  $('#pg-titulo').textContent = tit;
  // «NA BARRA DO LADO» MENTE NO TELEMÓVEL, e foi a fotografia a 375 px que o
  // mostrou: ali a barra está atrás do ☰ Menu e o ecrã mandava-o procurar uma
  // coisa que não se vê. Diz-se os dois sítios. (Vinha assim desde 30/09, no
  // ecrã da password temporária.)
  $('#pg-sub').textContent = temporaria
    ? 'O site fica à espera até escolheres uma password tua — a temporária '
      + 'serve para isso e mais nada. ' + ONDE_ESTA_O_FORMULARIO
    : 'Estás a chegar de fora de casa, e daqui pede-se sempre que entres — '
      + 'mesmo para ver. ' + ONDE_ESTA_O_FORMULARIO;
  $('#topbar-tit').textContent = tit;
  return true;
}

async function boot() {
  loadPrefs();
  wireCasca();
  wireControls();
  wireKeyboard();

  // O SITE PODE ESTAR TRANCADO POR UMA PASSWORD TEMPORÁRIA (2026-09-30), e
  // isto era o segundo beco: o `_trava_temporaria` do servidor responde 403 a
  // tudo o que é `/api/`, o `api/index.json` é a primeira coisa que se pede, e
  // o `boot()` morria aqui — o ecrã da troca, que é a ÚNICA coisa que ela pode
  // fazer, nunca chegava a ser desenhado. Lia-se «Falhou a carregar: HTTP 403».
  // O `api/conta.json` é o que passa a trava, de propósito (ver `COM_TEMPORARIA`).
  try {
    state.index = await getJSON('api/index.json');
  } catch (err) {
    if (await mostrarSeTrancado()) return;
    throw err;
  }
  // As abas escondidas (2026-09-25) vêm no índice, e por isso a barra só se
  // desenha DEPOIS dele: desenhá-la antes mostrava por um instante uma aba que
  // ele mandou tirar. Se o índice falhar, o `boot().catch` do fim do ficheiro
  // desenha-a na mesma — sem navegação não se chega a lado nenhum.
  state.escondidas = new Set((state.index.abas || {}).escondidas || []);
  renderNav();

  // QUEM SOU EU (2026-09-29). Com a porta das contas fechada e de casa isto
  // responde `{aberto: false, editavel: true}`. Com a porta aberta, EDITAR É
  // «estou dentro E isto é meu»: sem sessão a página é de leitura, como a de um
  // amigo é para mim.
  //
  // No SITE PUBLICADO não se pergunta: aquilo são ficheiros e não há rota
  // nenhuma. Sem esta condição cada visita à cópia publicada deixava um 404 de
  // `api/conta.json` na consola — a página funcionava (o `catch` devolvia
  // `null`), mas um 404 no site dele lê-se como avaria.
  //
  // O CRITÉRIO É O `servidor`, E ERA O `editable` ATÉ 2026-10-02. O `editable`
  // respondia a duas perguntas de uma vez — «posso escrever?» e «isto é o
  // servidor?» — e por isso NÃO PODIA DIZER A VERDADE: com a porta aberta, um
  // leitor anónimo não pode escrever, mas se o campo dissesse `false` o
  // `conta.json` deixava de ser pedido e a caixa de «Entrar» desaparecia (o
  // `renderConta` esconde-se com `state.conta` nulo). Era o beco de 2026-09-30
  // por outro caminho. Duas perguntas, dois campos.
  state.conta = state.index.servidor
    ? await getJSON('api/conta.json').catch(() => null) : null;
  // O `editable` do índice já vem honesto do servidor, e o `meu` fica como
  // segunda rede: a resposta do `conta.json` é a mesma, e um ficheiro gerado
  // por uma versão antiga continua a ser lido pelo lado restritivo.
  const meu = !state.conta || state.conta.editavel !== false;
  state.editable = !!state.index.editable && meu;
  renderConta();
  state.imageMode = state.index.image_mode || 'local';
  document.body.classList.toggle('readonly', !state.editable);
  $('#mode-badge').hidden = state.editable;
  // O chip "só leitura" ao lado do título passa despercebido — quem abre isto
  // no telemóvel carrega no sítio dos +/- e não percebe porque não acontece
  // nada. O aviso tem de ser grande.
  $('#readonly-banner').hidden = state.editable;
  $('#generated').textContent = state.index.generated_at
    ? `Atualizado em ${state.index.generated_at.replace('T', ' ').replace('+00:00', ' UTC')}.` : '';

  // A contagem por níveis das cinco edições, como estava quando o ficheiro foi
  // gerado. A edição que ele abrir passa a ser recalculada a partir dos +/-.
  for (const [sid, ls] of Object.entries((state.index.levels || {}).by_set || {})) {
    state.levels.set(sid, ls);
  }

  // A rota do URL manda; sem ela, a última secção que ele abriu. Uma
  // preferência guardada com a secção Venda (apagada a 2026-09-15) ou com a
  // tabela de preços (`faltas`, apagada a 2026-09-19) cai na Coleção, como
  // qualquer outro nome que já não exista.
  //
  // Uma aba ESCONDIDA (2026-09-25) é, para as rotas, uma secção que não
  // existe: o `#a-mais` de um favorito antigo cai na primeira que se vê, como
  // qualquer outro nome que já não exista.
  const r = lerHash();
  const sec = seccaoValida(r.sec) ? r.sec
    : seccaoValida(state.prefs.section) ? state.prefs.section : seccaoInicial();
  const sub = seccaoValida(r.sec) ? r.sub : '';

  // A Coleção carrega-se sempre à partida: é dela que saem as barras, o painel
  // e o `state.qty` que a secção Encomendas e o bloco das runas leem.
  renderSetTabs();
  const first = state.index.sets[0];
  const daRota = sec === 'colecao' && sub
    && (sub === TODAS || state.index.sets.some(s => s.id === sub)) ? sub : null;
  const wanted = daRota
    || (state.prefs.set === TODAS || state.index.sets.some(s => s.id === state.prefs.set)
        ? state.prefs.set : (first && first.id));
  if (wanted) await loadSet(wanted, { url: false });

  showSection(sec, sub);

  // Uma ligação `#encomendas` dentro da página (a nota do deck), o botão
  // «voltar» do browser e um endereço colado à mão entram todos por aqui.
  window.addEventListener('hashchange', () => {
    if (aEscreverHash) return;
    const h = lerHash();
    if (seccaoValida(h.sec)) showSection(h.sec, h.sub, { url: false });
  });
}

async function loadSet(setId, { url = true } = {}) {
  state.setId = setId;
  state.prefs.set = setId;
  savePrefs();
  if (url && state.prefs.section === 'colecao') escreverHash('colecao', setId);
  renderSetTabs();

  $('#grid').innerHTML = '<p class="empty">a carregar…</p>';
  // Em «Todas» o painel aparece já com os números do servidor (vêm no
  // `index.json`), enquanto as edições carregam.
  if (setId === TODAS) renderPainel();
  const p = setId === TODAS ? await loadTodas() : await getJSON(`api/set/${setId}.json`);
  // Ele mudou de separador enquanto isto vinha: o que chegou já não é o que
  // está escolhido, e desenhá-lo punha a grelha de uma edição debaixo do
  // separador de outra.
  if (state.setId !== setId) return;
  state.payload = p;
  state.imageMode = p.image_mode || state.imageMode;

  state.qty.clear(); state.play.clear(); state.targets.clear();
  state.blocks.clear(); state.meta.clear(); state.counting.clear();
  state.locs.clear(); state.tot.clear(); state.foil.clear(); state.foilOk.clear();
  state.foilAlvo.clear();
  state.preco.clear(); state.precoFoil.clear(); state.valNorm.clear();
  for (const b of p.blocks || []) if (b.counts) state.counting.add(b.id);
  if (!(p.blocks || []).length) state.counting.add('master');
  for (const g of p.groups) {
    state.play.set(g.card_key, { owned: g.playset.owned, target: g.playset.target });
    for (const pr of g.printings) {
      state.qty.set(pr.id, pr.qty);
      state.tot.set(pr.id, pr.qty_total || 0);
      if (pr.foil) state.foil.set(pr.id, pr.foil);
      if (pr.foil_ok) state.foilOk.add(pr.id);
      if (pr.foil_target) state.foilAlvo.set(pr.id, pr.foil_target);
      state.valNorm.set(pr.id, (pr.qty_valor || 0) - (pr.qty_valor_foil || 0));
      if (pr.price != null) state.preco.set(pr.id, pr.price);
      if (pr.price_foil != null) state.precoFoil.set(pr.id, pr.price_foil);
      state.locs.set(pr.id, pr.locations || []);
      state.targets.set(pr.id, pr.target);
      state.blocks.set(pr.id, pr.block || 'master');
      state.meta.set(pr.id, { name: pr.name, card_key: g.card_key, rarity: g.rarity, cn: g.cn });
    }
  }
  render();
  // Fora do `render()` de propósito: as wantlists são da EDIÇÃO, não do que
  // está no ecrã, e o `render()` corre a cada tecla da caixa de procura.
  renderWantlists();
  renderFoilResumo();
  renderFaltaLinha();
  // Idem: o bloco das runas é da EDIÇÃO (desde 2026-10-01), não do filtro.
  renderRunasVista();
}

/* A edição aberta na Coleção, ou `null` em «Todas» — para quem precisa de UMA
   edição (o separador Encomendas, a wantlist da edição). */
function edicaoAberta() {
  return state.setId && state.setId !== TODAS ? state.setId : null;
}

/* ================================== o separador «Todas» (2026-09-21)

   As edições todas seguidas, na ordem dos separadores. Não há ficheiro
   próprio: pedem-se os `api/set/<ID>.json` de todas e cola-se um payload só,
   com a mesma forma — os `groups` levam a edição (`set`, `set_name`) para a
   grelha pôr um cabeçalho quando muda de edição, e os `blocks` são a união,
   pela ordem do servidor (`index.painel.blocks`). Tudo o que lê o payload
   (as barras, o painel, o valor, os +/-) funciona igual, porque os
   `printing_id` são únicos no catálogo inteiro. */
async function loadTodas() {
  const sets = state.index?.sets || [];
  const ps = await Promise.all(sets.map(s => getJSON(`api/set/${s.id}.json`)));
  return juntarEdicoes(sets, ps);
}

function juntarEdicoes(sets, ps) {
  const groups = [];
  const blocks = new Map();
  const hidden = new Set();
  const progress = {
    playset: { done: 0, total: 0 }, master: { done: 0, total: 0 },
    value: { owned: 0, full: 0, currency: 'EUR', has_prices: false },
    rarities: [], levels: [], painel: { blocks: {}, runes_out: 0 },
    // A contagem de foil das edições todas (2026-09-22): a soma vem do
    // servidor (`index.foil.sets.all`); os números que se vêem recalculam-se
    // do estado, como sempre.
    foil: state.index?.foil?.sets?.[TODAS] || null,
  };
  ps.forEach((p, i) => {
    for (const g of p.groups) groups.push({ ...g, set: sets[i].id, set_name: sets[i].name });
    for (const b of p.blocks || []) {
      const j = blocks.get(b.id);
      if (!j) { blocks.set(b.id, { ...b }); continue; }
      j.done += b.done; j.total += b.total; j.owned += b.owned;
      j.max_target = Math.max(j.max_target, b.max_target);
    }
    for (const k of p.hidden_kinds || []) hidden.add(k);
    const pr = p.progress || {};
    for (const c of ['playset', 'master']) {
      if (!pr[c]) continue;
      progress[c].done += pr[c].done; progress[c].total += pr[c].total;
    }
    if (pr.value) {
      progress.value.owned += pr.value.owned || 0;
      progress.value.full += pr.value.full || 0;
      progress.value.has_prices = progress.value.has_prices || !!pr.value.has_prices;
    }
    progress.painel.runes_out += pr.painel?.runes_out || 0;
  });
  // A soma dos blocos do servidor está no `index.painel.sets.all`; os
  // números que se vêem recalculam-se do estado, como sempre.
  progress.painel.blocks = state.index?.painel?.sets?.[TODAS] || {};
  const ordem = (state.index?.painel?.blocks || []).map(b => b.id);
  const lista = [...blocks.values()].sort((a, b) => {
    const ia = ordem.indexOf(a.id), ib = ordem.indexOf(b.id);
    return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib);
  });
  const primeiro = ps[0] || {};
  return {
    editable: !!primeiro.editable,
    image_mode: primeiro.image_mode,
    generated_at: primeiro.generated_at,
    set: { id: TODAS, name: `Todas as edições` },
    price_badge_min: primeiro.price_badge_min,
    progress, blocks: lista, hidden_kinds: [...hidden], groups,
  };
}

/* ================================ o bloco «Runas — 12 de cada» (2026-09-19)

   André, de manhã: *"depois mete 12 runas de cada (nao contabilizes para
   nada, e so para mim para contabilizar ali algumas coisas)"*; à tarde, ao
   pedir os botões: *"runas nao contabilizam nada, eu e que mexo nisso para
   minha referencia, nao entram para decks, nao entram para coleccao, nada,
   so para mim"*.

   É O CONTADOR DELE: o número do crachá vem da `rune_counter` do vault.db e
   os `+`/`−` daqui escrevem SÓ lá (`api/runas/ajustar`) — não no `copies`,
   não nas encomendas, não nos locais. Vem de `api/runas.json` — fora do
   payload da edição, de propósito —, e não entra em conta nenhuma daqui: nem
   na barra, nem nos níveis, nem no valor, nem nas wantlists. O `state.runas`
   não é lido por mais ninguém.

   A REFERÊNCIA É DA EDIÇÃO ABERTA (2026-10-01). André: *"A contagem das
   runas Alt.Art é exclusiva para cada edição / vi que a contagem está a ser
   partilhada por todas as edições"*. O ficheiro continua a ser um só (as
   seis runas são as mesmas), mas traz `por_edicao`: na página do OGN a linha
   «nesta edição» conta as impressões do OGN, na do SFD as do SFD, e em
   «Todas» a soma. O OGS não tem runas e não leva bloco nenhum.

   E O CONTADOR TAMBÉM, DESDE 2026-10-03. André: *"Zera e recontas por
   edicao"* — a tabela ganhou `set_id`, o contador foi reposto a ZERO e ele
   reconta-as aqui, edição a edição. Duas consequências no ecrã: há um AVISO
   em cima a dizer que o zero é de hoje (senão lia-se «não tens runas»), com
   o que ele tinha contado à mão ao lado e um «dispensar»; e **os `+`/`−` só
   aparecem na página de uma edição** — em «Todas» o crachá é a soma das
   quatro e um clique não saberia a que edição somar.

   Ao lado, em letra pequena, «nesta edição: N» é o que o site sabe que ele
   tem das impressões DESSA edição (a base e a alt art retirada no OGN; a
   promo escondida no VEN; as do CardTrader no SFD/UNL/VEN) — só para ele
   comparar com o que contou à mão. */
async function renderRunasVista(reler = false) {
  const el = $('#runas-vista');
  if (!el) return;
  if (reler || !state.runas) {
    try { state.runas = await getJSON('api/runas.json'); }
    catch (err) { el.innerHTML = ''; return; }
  }
  const v = runasDaEdicao();
  if (!v || !(v.runas || []).length) { el.innerHTML = ''; return; }
  // Os tiles vão directos na grelha (o `#runas-vista` é uma `.grid`), sem o
  // `.group.multi`: um grupo de 6 colunas não cabe no telemóvel.
  el.innerHTML = runasHead(v) + runasAviso() + v.runas.map(x => runaTile(x, v)).join('');
  ligarRunas();
}

/* O AVISO DO ZERO (2026-10-03): o contador foi reposto para passar a ser por
   edição, e sem isto um bloco a zeros lia-se «não tens runas». Mostra o que
   ele tinha contado à mão — 14 ao todo —, para ele conferir enquanto reconta,
   e sai com o «dispensar». Dispensar NÃO apaga o rasto: marca a data, e as
   seis linhas ficam na base e no `riftvault runas`. */
function runasAviso() {
  const a = state.runas && state.runas.antes;
  if (!a || a.dispensado_em) return '';
  const linhas = a.linhas.map(r => `${escapeHTML(r.card_key.split(' ')[0])} <b>${r.qty}</b>`)
    .join(' · ');
  return `<div class="runas-aviso" id="runas-aviso">
    <p>${escapeHTML(a.aviso)}</p>
    <p class="ref">Tinhas contado <b>${a.total}</b> ao todo, sem edição:
      ${linhas}.</p>
    ${state.runas.editable
      ? '<button class="btn mini" id="runas-dispensar">Dispensar este aviso</button>'
      : ''}
  </div>`;
}

/* A vista do bloco: a fatia da edição aberta, ou a soma das cinco em
   «Todas». `null` numa edição sem runas (o OGS) — e num payload anterior a
   2026-10-01, que não traz `por_edicao`, volta a ser a soma, para o 8770 não
   partir entre o merge e o relançamento do processo. */
function runasDaEdicao() {
  const p = state.runas;
  if (!p) return null;
  const todas = { set_id: null, runas: p.runas || [], totals: p.totals };
  const sid = edicaoAberta();
  if (!sid || !p.por_edicao) return todas;
  return p.por_edicao[sid] || null;
}

/* Um payload SEM `contador` vem de um servidor anterior à tarde de 19/09
   (o 8770 não se reinicia a cada merge, e o `app.js` é lido do disco a cada
   pedido): mostra-se o número calculado e sem botões, até o vigia relançar
   o processo. Os botões pedem o `editable` do PAYLOAD, como a Coleção. */
function runaContador(x) {
  return x.contador != null ? x.contador : x.total;
}

/* Recebe a VISTA (a fatia da edição ou a soma), não o payload: o `alvo` e a
   `nota` são do payload e o resto é da vista. */
function runasHead(v) {
  const p = state.runas;
  const t = v.totals;
  const sem = t.sem_retiradas !== t.total ? ` (${t.sem_retiradas} sem as retiradas)` : '';
  const n = t.contador != null ? t.contador : t.total;
  // Numa edição o contador é DELA; em «Todas» é a soma das quatro, e aí
  // di-lo — senão um 288 no alvo lia-se como um alvo por runa.
  const quem = v.set_id
    ? `(o teu contador de ${escapeHTML(v.set_id)}) · nesta edição (${escapeHTML(v.set_id)})`
    : '(a soma do teu contador nas edições todas) · nas edições todas';
  return `<h2 class="section-head fora vista" id="runas-head">Runas — ${p.alvo} de cada
      <span>contas <b>${n}</b> de <b>${t.alvo}</b>
      <small class="ref">${quem}
      tens: ${t.total}${sem}</small> — ${escapeHTML(p.nota)}</span></h2>`;
}

/* Recebe a VISTA a par do item: é o `v.set_id` que decide se há botões — o
   contador é por edição, e em «Todas» não há onde somar o clique. */
function runaTile(x, v) {
  const n = runaContador(x);
  const feito = n >= x.target;
  // As origens só no `title`: a linha visível é a referência curta, para não
  // poluir um bloco que é dele.
  const origens = x.origens.map(o => `${o.qty}× ${(o.code || '').split('/')[0]} ${o.label}`)
    .join(' · ') || 'nenhuma à mão';
  const sem = x.sem_retiradas !== x.total ? ` (${x.sem_retiradas} sem as retiradas)` : '';
  const onde = v && v.set_id ? 'nesta edição' : 'na coleção';
  const botoes = state.runas && state.runas.editable && x.contador != null && v && v.set_id
    ? `<div class="steppers runa">
      <button class="step minus" data-runa-delta="-1" ${n > 0 ? '' : 'disabled'}
              aria-label="menos uma no teu contador de ${escapeAttr(x.name)} em ${escapeAttr(v.set_id)}"
              title="menos uma (só no teu contador de ${escapeAttr(v.set_id)})">−</button>
      <button class="step plus" data-runa-delta="1"
              aria-label="mais uma no teu contador de ${escapeAttr(x.name)} em ${escapeAttr(v.set_id)}"
              title="mais uma (só no teu contador de ${escapeAttr(v.set_id)})">+</button>
    </div>`
    : state.runas && state.runas.editable && v && !v.set_id
      ? `<div class="onde ref soma-sem-botoes">${escapeHTML(state.runas.soma_sem_botoes || '')}</div>`
      : '';
  return `<div class="dtile neutro vista${feito ? ' ok' : ''}" data-runa="${escapeAttr(x.card_key)}">
    ${artHTML(x, `<span class="need">${n}/${x.target}</span>`)}
    <div class="tname" title="${escapeAttr(x.name)}">${escapeHTML(x.name)}</div>
    ${botoes}
    <div class="onde tenho ref" title="${escapeAttr(origens)}">${onde}: <b>${x.total}</b>${escapeHTML(sem)}</div>
  </div>`;
}

/* Os botões de cada tile. Chama-se depois de cada desenho, porque o
   `innerHTML` deita os handlers fora. */
function ligarRunas() {
  const v = runasDaEdicao();
  for (const b of document.querySelectorAll('#runas-vista .steppers.runa .step')) {
    b.onclick = () => runaAjustar(b.closest('.dtile').dataset.runa,
                                  v && v.set_id, Number(b.dataset.runaDelta));
  }
  const d = $('#runas-dispensar');
  if (d) d.onclick = () => runasDispensar();
}

function runaRefreshTile(ck) {
  const el = document.querySelector(`#runas-vista .dtile[data-runa="${CSS.escape(ck)}"]`);
  const v = runasDaEdicao();
  const x = v && v.runas.find(r => r.card_key === ck);
  if (!el || !x) return;
  el.outerHTML = runaTile(x, v);
  const head = $('#runas-head');
  if (head) head.outerHTML = runasHead(v);
  ligarRunas();
}

/* O contador é POR EDIÇÃO desde 2026-10-03: um `+` no OGN muda a célula do
   OGN e a SOMA que «Todas» mostra, e NÃO toca no SFD. Até 02/10 era o
   contrário — havia um número só e tinha de mudar em todas as listas. */
function runaPorContador(ck, sid, novo) {
  const p = state.runas;
  if (!p) return;
  const e = (p.por_edicao || {})[sid];
  if (!e) return;
  const x = e.runas.find(r => r.card_key === ck);
  if (!x) return;
  const antes = x.contador || 0;
  x.contador = novo;
  if (e.totals) e.totals.contador = e.runas.reduce((s, r) => s + (r.contador || 0), 0);
  // A soma de «Todas»: o delta desta célula, nada mais.
  const soma = (p.runas || []).find(r => r.card_key === ck);
  if (soma) soma.contador = Math.max(0, (soma.contador || 0) + (novo - antes));
  if (p.totals) {
    p.totals.contador = (p.runas || []).reduce((s, r) => s + (r.contador || 0), 0);
  }
}

/* O «dispensar» do aviso do zero: marca a data na base e volta a desenhar o
   bloco. Não apaga o rasto — o `riftvault runas` continua a mostrá-lo. */
async function runasDispensar() {
  if (!state.editable || !state.runas || !state.runas.editable) return;
  try {
    const r = await fetch('api/runas/dispensar', {
      method: 'POST', headers: cabecalhos(), body: JSON.stringify({}),
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    state.runas.antes = (await r.json()).antes;
    renderRunasVista();
  } catch (err) { toast(`Não gravou: ${err.message}`, { error: true }); }
}

/* O clique no `+`/`−` do contador: ecrã otimista, pedidos da MESMA runa em
   fila — como as Encomendas —, e só o último em voo aceita o número do
   servidor. Grava SÓ na `rune_counter`; nada mais no site muda, e por isso
   não se marca nada como velho. */
async function runaAjustar(ck, sid, delta) {
  if (!state.editable || !state.runas || !state.runas.editable) return;
  // Sem edição aberta não há célula onde contar — em «Todas» não há botões.
  if (!sid) return;
  const v = runasDaEdicao();
  const x = v && v.runas.find(r => r.card_key === ck);
  if (!x || x.contador == null) return;
  if (delta < 0 && x.contador <= 0) return;
  state.runas.voo = state.runas.voo || new Map();
  state.runas.fila = state.runas.fila || new Map();
  runaPorContador(ck, sid, Math.max(0, x.contador + delta));
  runaRefreshTile(ck);
  state.runas.voo.set(ck, (state.runas.voo.get(ck) || 0) + 1);
  const fila = state.runas.fila.get(ck) || Promise.resolve();
  const tarefa = fila.then(async () => {
    const r = await fetch('api/runas/ajustar', {
      method: 'POST', headers: cabecalhos(),
      body: JSON.stringify({ card_key: ck, set_id: sid, delta }),
    });
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error || `HTTP ${r.status}`);
    return r.json();
  });
  state.runas.fila.set(ck, tarefa.catch(() => {}));
  try {
    const res = await tarefa;
    const resto = (state.runas.voo.get(ck) || 1) - 1;
    state.runas.voo.set(ck, resto);
    if (resto === 0) {
      runaPorContador(ck, sid, res.qty);
      // Os totais vêm do servidor (uma aritmética só): a soma e cada edição.
      state.runas.totals = res.totals;
      for (const [s, t] of Object.entries(res.totals_por_edicao || {})) {
        if (state.runas.por_edicao && state.runas.por_edicao[s]) {
          state.runas.por_edicao[s].totals = t;
        }
      }
      runaRefreshTile(ck);
    }
  } catch (err) {
    state.runas.voo.set(ck, Math.max(0, (state.runas.voo.get(ck) || 1) - 1));
    // Desfaz ESTE delta sobre o valor de agora, não sobre o `antes`: pode
    // haver mais cliques em voo na fila desta runa.
    runaPorContador(ck, sid, Math.max(0, x.contador - delta));
    runaRefreshTile(ck);
    toast(`Não gravou: ${err.message}`, { error: true });
  }
}

/* As runas da referência «na coleção»: um `+`/`−` da GRELHA numa delas relê
   o ficheiro (é pequeno), para a referência andar com a grelha. O contador
   dele não mexe com isso — vem da tabela dele. */
function runaMexeu(cardKey) {
  if (!state.runas || !cardKey) return;
  if (state.runas.runas.some(x => x.card_key === cardKey)) renderRunasVista(true);
}

/* --------------------------------------------------------------- separadores */

function renderSetTabs() {
  const nav = $('#set-tabs');
  nav.innerHTML = '';
  const sets = state.index?.sets || [];
  const botao = (id, nome, sub) => {
    const b = document.createElement('button');
    b.className = 'tab' + (id === state.setId ? ' is-on' : '');
    b.setAttribute('aria-pressed', id === state.setId ? 'true' : 'false');
    b.innerHTML = `${escapeHTML(nome)}<small>${sub}</small>`;
    b.onclick = () => loadSet(id).catch(err => toast(err.message, { error: true }));
    nav.appendChild(b);
  };
  for (const s of sets) botao(s.id, s.name, `${s.n_printings} impressões`);
  // «Todas» (2026-09-21): as edições seguidas, e o painel do topo somado.
  if (sets.length > 1) {
    botao(TODAS, 'Todas', `${sets.reduce((n, s) => n + s.n_printings, 0)} impressões`);
  }
}

/* -------------------------------------------------------------- filtragem */

function tileState(pid) {
  const q = state.qty.get(pid) || 0;
  const t = state.targets.get(pid) || 0;
  if (t <= 0) return q > 0 ? 'done' : 'none';   // tokens: alvo 0, sem estado parcial
  if (q <= 0) return 'none';
  return q >= t ? 'done' : 'partial';
}

function kindBucket(kind) {
  return (kind === 'base' || kind === 'alt_art' || kind === 'signature') ? kind : 'other';
}

function visiblePrintings(group) {
  const term = ($('#search').value || '').trim().toLowerCase();
  if (term) {
    const hay = `${group.name} ${group.printings.map(p => p.code || '').join(' ')}`.toLowerCase();
    if (!hay.includes(term)) return [];
  }
  let list = state.prefs.view === 'base' ? group.printings.filter(p => p.head) : group.printings;

  if (state.prefs.view === 'all') {
    list = list.filter(p => state.prefs.kinds.includes(kindBucket(p.kind)));
  }
  // "Faltas" é tudo o que ainda não está completo — tanto faz faltarem 3, 2
  // ou 1. Havia dois filtros separados (em falta / parciais) e o André pediu
  // para juntar: a pergunta é sempre a mesma, o que é que ainda me falta.
  if (state.prefs.stateFilter === 'missing') {
    list = list.filter(p => tileState(p.id) !== 'done');
  }
  // "Em decks" é por CARTA, não por impressão: a alocação é por carta lógica
  // e o rótulo «Azir 3 · Kennen 2» é do grupo inteiro (2026-09-11).
  if (state.prefs.stateFilter === 'indeck' && !(group.decks || []).length) {
    return [];
  }
  return list;
}

/* ----------------------------------------------------------------- render */

function imgSrc(p) {
  return state.imageMode === 'remote' ? (p.cdn || p.img) : (p.img || p.cdn);
}
function imgAlt(p) {
  return state.imageMode === 'remote' ? (p.img || '') : (p.cdn || '');
}

function tileHTML(g, p, comUso = false) {
  const q = state.qty.get(p.id) || 0;
  const t = state.targets.get(p.id) || 0;
  const st = tileState(p.id);
  const play = state.play.get(g.card_key) || { owned: 0, target: 0 };
  const badge = t > 0 ? `${q}/${t}` : `${q}`;
  const alt = imgAlt(p);

  return `<div class="tile ${st}" data-pid="${escapeAttr(p.id)}" data-ck="${escapeAttr(g.card_key)}">
    <div class="art${p.landscape ? ' landscape' : ''}">
      <img src="${imgSrc(p)}" alt="${escapeAttr(p.name)}" loading="lazy" decoding="async"
           ${alt ? `data-fallback="${escapeAttr(alt)}"` : ''}>
      <span class="label ${p.kind}">${p.label}</span>
      ${p.price != null && p.price >= priceBadgeMin()
        ? `<span class="price">${eurShort(p.price)}</span>` : ''}
      <span class="cn">${p.code ? escapeHTML(p.code.split('/')[0]) : g.cn}</span>
      <span class="badge">${badge}</span>
    </div>
    <div class="tname" title="${escapeAttr(p.name)}">${escapeHTML(p.name)}</div>
    <div class="steppers">
      <button class="step minus" data-act="-1" aria-label="menos uma de ${escapeAttr(p.name)}"
              ${qtyNormais(p.id) <= 0 ? 'disabled' : ''}>−</button>
      <button class="step plus" data-act="1" aria-label="mais uma de ${escapeAttr(p.name)}">+</button>
    </div>
    <div class="playset ${play.target > 0 && play.owned >= play.target ? 'is-done' : ''}"
         data-kind="${g.is_token ? 'token' : 'jogável'}"
         ${p.price != null ? `data-price="${p.price}"` : ''}>
      ${g.is_token ? 'token' : 'jogável'} ${play.owned}/${play.target}${p.price != null ? ` · ${eur(p.price)}` : ''}
    </div>
    ${foilLinha(p.id)}
    ${venderLinha(p.id)}
    ${deckLine(p.id)}
    ${comUso ? usoLine(g) : ''}
  </div>`;
}

/* «juntar à venda» (2026-09-25), no tile da Coleção: só no modo edição e só
   nas cartas de que ele TEM alguma cópia — não se vende o que não se tem, e
   um botão em todos os 1180 tiles era ruído. Junta uma cópia desta IMPRESSÃO
   à venda em curso (a versão que tem na mão é a que ele carrega) e não tira
   nada de lado nenhum: a coleção só desce no «marcar como vendidas». */
function venderLinha(pid) {
  if (!state.editable || !(state.tot.get(pid) || 0)) return '';
  return `<button type="button" class="vd-add" data-vender="1"
    title="juntar uma à venda em curso">+ venda</button>`;
}

/* ================================ o contador de FOIL (André, 2026-09-22)

   *"para comuns e incomuns, coloca contagem para Foil e Non-Foil, para todas
   as edicoes excepto Proving Grounds"*. Nas cartas do âmbito (as impressões
   base, não sobrenumeradas, comuns e incomuns, fora o OGS — quem decide é o
   `foil.no_ambito` do servidor, que manda `foil_ok` no payload) o tile ganha,
   por baixo dos `+`/`−` de sempre, um contador de foil com o alvo dele.

   DUAS CONTAGENS SEPARADAS, NUNCA SOMADAS NO TILE (André, 2026-09-27, à noite):
   *"quero que haja 2 contagens separadas / a de normais e de foils / quero que
   a contagem na carta seja a de non-foil e a de baixo seja a foil, as coisas
   separadas"*.

     o CRACHÁ, em cima     as NORMAIS da Coleção contra o `metrics.alvo`
                           (`state.qty` / `state.targets`) — é a que manda, e é
                           a que ele lê de relance
     esta LINHA, em baixo  as FOILS contra o `foil.alvo` (`state.foil` /
                           `state.foilAlvo`) — o playset do tipo, o mesmo alvo
                           da metade das foils do separador Faltas, e por isso
                           numa runa base o crachá pede 3 e esta linha pede 12

   O ERRO QUE ISTO CORRIGE era nosso: entre 2026-09-26 e 2026-09-27 o tile
   somava as duas contagens («2 normais · 1 foil = 3» num alvo de 3, crachá
   «3/3» a verde), e ele deixou de ver o que lhe faltava — *"a impressao que
   fica e que eu tenho as cartas todas, e quando me falta normais nao consigo
   perceber automaticamente que falta"*. Eram 47 impressões e 48 cópias normais
   escondidas. A separação aqui é ESTRUTURAL, não depende de chave nenhuma.

   O `+` do foil acrescenta uma foil e não converte nada; não tem tecto natural
   (o alvo é um alvo, não um tecto — ter 4 foils de um playset de 3 é legítimo e
   lê-se «4/3»), e trava só no `limite` que o servidor manda.                */

function foilLimite() { return state.index?.foil?.limite || 9999; }

function foilLinha(pid) {
  if (!state.foilOk.has(pid)) return '';
  const f = state.foil.get(pid) || 0;
  const t = state.foilAlvo.get(pid) || 0;
  const lim = foilLimite();
  const feito = t > 0 && f >= t;
  const controlos = state.editable ? `<span class="steppers foil">
      <button class="step minus" data-foil="-1" aria-label="menos uma foil"
              ${f <= 0 ? 'disabled' : ''}>−</button>
      <button class="step plus" data-foil="1" aria-label="mais uma foil"
              ${f >= lim ? 'disabled' : ''}>+</button>
    </span>` : '';
  // O que as foils contam vem do servidor (`foil.conta_para_coleccao` /
  // `conta_para_valor`): a frase muda com as chaves em vez de ficar a dizer o
  // de antes. Hoje só a segunda está ligada.
  const contam = foilContamTxt();
  const pf = foilPrecoTxt(pid);
  // O PREÇO vai numa LINHA PRÓPRIA, a seguir aos `+`/`−` e com a largura toda
  // do tile (`flex-basis: 100%`), não encostado às contagens: a 375 px o tile
  // tem ~109 px e a metade que sobrava ao lado dos botões punha «foil ao preço
  // da normal» a uma palavra por linha. Medido.
  return `<div class="foil-linha${feito ? ' is-done' : ''}" title="foil: tens ${f} de ${
    t} (o playset do tipo, em foil). É uma contagem SEPARADA da das normais, que está no crachá em cima — as duas nunca se somam.${
    contam ? ` As foils contam ${contam}.` : ' As foils não contam para os alvos da Coleção nem para o valor.'}${
    pf ? ` ${pf.title}` : ''}">
    <span class="foil-txt">foil <b class="fo">${f}</b>${
      t > 0 ? `<i class="dim">/${t}</i>` : ''}</span>${controlos}${
    pf ? `<span class="${pf.cls}">${pf.txt}</span>` : ''}</div>`;
}

/* O PREÇO DA FOIL NO TILE (2026-09-26, à tarde)

   Onde aparece a contagem de foil aparece o preço dela — e a marca de quando é
   FALLBACK. Duas leituras, de propósito diferentes à vista:

     `foil 1,50 €`             há oferta foil no CardTrader: é este o preço a que
                               as cópias foil dele contam no valor
     `foil ao preço da normal` não há oferta foil: a cópia conta ao preço da
                               normal, e o valor dela é um PISO

   Só se mostra com o `foil.conta_para_valor` ligado: com ele desligado o preço
   da foil não entra em conta nenhuma e era ruído no tile. */
function foilPrecoTxt(pid) {
  if (!(state.index?.foil || {}).conta_para_valor) return null;
  const pf = state.precoFoil.get(pid);
  if (pf != null) {
    return { txt: `foil ${eur(pf)}`, cls: 'fo-preco',
             title: `Uma cópia foil conta ${eur(pf)} no valor — o preço da foil mais `
                  + 'barata no CardTrader (Near Mint/Mint, inglês).' };
  }
  // Sem `price` não há nada a dizer: a impressão não tem oferta nenhuma.
  const p = state.preco.get(pid);
  if (p == null) return null;
  return { txt: 'foil ao preço da normal', cls: 'fo-preco fo-piso',
           title: `O CardTrader não tem esta em foil: uma cópia foil conta ${eur(p)}, `
                + 'o preço da normal. É um piso — o real é mais alto.' };
}

/* «para os alvos da Coleção e para o valor» — das chaves do servidor, para não
   haver segunda lista no cliente. Vazio quando nenhuma está ligada. */
function foilContamTxt() {
  const cat = state.index?.foil || {};
  return [cat.conta_para_coleccao ? 'para os alvos da Coleção' : null,
          cat.conta_para_valor ? 'para o valor' : null].filter(Boolean).join(' e ');
}

/* AS CÓPIAS NORMAIS QUE A COLEÇÃO TEM (2026-09-26)

   Com `foil.conta_para_coleccao` ligado, o `state.qty` de uma impressão é
   `normais na Coleção + foils`. O `−` do tile baixa o `copies.qty`, que são as
   NORMAIS: com 0 normais e 3 foils o `qty` é 3 e o botão tem de estar
   DESLIGADO, senão prometia tirar uma cópia que não existe. */
function qtyNormais(pid) {
  const q = state.qty.get(pid) || 0;
  if (!(state.index?.foil || {}).conta_para_coleccao) return q;
  return Math.max(0, q - (state.foil.get(pid) || 0));
}

/* A fila é por impressão: o ecrã anda já, e só a última resposta manda. Não há
   `request_id` — repetir o mesmo pedido dá o mesmo resultado (`min`/`max` no
   servidor). O `+` do foil NUNCA manda um `+` de cópias normais: são dois
   contadores, cada um com a sua rota. */
async function foilAjustar(pid, delta) {
  if (!state.editable || !state.foilOk.has(pid)) return;
  const antes = state.foil.get(pid) || 0;
  const novo = Math.max(0, Math.min(antes + delta, foilLimite()));
  if (novo === antes) return;
  state.foil.set(pid, novo);
  foilAplicarLocal(pid, novo - antes);
  renderFoilResumo();

  const emVoo = (state.foilVoo.get(pid) || 0) + 1;
  state.foilVoo.set(pid, emVoo);
  try {
    const r = await fetch('api/foil/ajustar', {
      method: 'POST',
      headers: cabecalhos(),
      body: JSON.stringify({ printing_id: pid, delta }),
    });
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error || `HTTP ${r.status}`);
    const res = await r.json();
    const resto = (state.foilVoo.get(pid) || 1) - 1;
    state.foilVoo.set(pid, resto);
    if (resto === 0) {
      const d = res.foil - (state.foil.get(pid) || 0);
      state.foil.set(pid, res.foil);
      foilAplicarLocal(pid, d);
      renderFoilResumo();
    }
  } catch (err) {
    state.foilVoo.set(pid, Math.max(0, (state.foilVoo.get(pid) || 1) - 1));
    const d = antes - (state.foil.get(pid) || 0);
    state.foil.set(pid, antes);
    foilAplicarLocal(pid, d);
    renderFoilResumo();
    toast(`Não gravou o foil: ${err.message}`, { error: true });
  }
}

/* O QUE UM `+` DE FOIL MEXE, ALÉM DA LINHA DO FOIL

   Depende das chaves do servidor, e hoje (2026-09-27, à noite) só uma está
   ligada:

     `conta_para_coleccao` **false** — o `state.qty` (o crachá, as três barras, o
                           painel, os níveis) **não mexe**: a Coleção conta as
                           normais. Era ligá-la que fazia 2 normais + 1 foil
                           lerem-se «3/3» e escondia-lhe a falta.
     `conta_para_valor`    **true** — o valor e o playset JOGÁVEL mexem (os dois
                           leem o `contadas`, que é o funil dessa chave).

   As NORMAIS (`state.tot`, `state.qty`) nunca mexem por aqui: são duas
   contagens independentes, e é o `−` do tile que baixa as normais. */
function foilAplicarLocal(pid, delta) {
  const cat = state.index?.foil || {};
  if (!cat.conta_para_coleccao && !cat.conta_para_valor) {
    refreshFoil(pid);           // o registo paralelo: só a linha do foil mexe
    return;
  }
  const ck = state.meta.get(pid)?.card_key;
  if (delta) {
    // `state.qty` é o que a Coleção TEM desta impressão, e é dele que saem o
    // crachá, as três barras, o painel, os níveis e o valor no cliente.
    if (cat.conta_para_coleccao) {
      state.qty.set(pid, Math.max(0, (state.qty.get(pid) || 0) + delta));
      wlDesatualizar();         // o que a impressão tem mudou: a lista ficou velha
    }
    // O playset JOGÁVEL da carta lê o `contadas`, que o outro botão alimenta.
    const play = state.play.get(ck);
    if (play && cat.conta_para_valor) play.owned = Math.max(0, play.owned + delta);
  }
  // O tile inteiro (crachá, estado, o `−`, a linha do foil) e, no fim, as
  // barras — o `refreshTiles` já chama o `renderProgress`.
  refreshTiles(pid, ck);
}

function refreshFoil(pid) {
  for (const el of document.querySelectorAll(`#grid .tile[data-pid="${CSS.escape(pid)}"]`)) {
    const linha = el.querySelector('.foil-linha');
    const novo = foilLinha(pid);
    if (linha) linha.outerHTML = novo;
  }
}

/* O resumo por edição (e em «Todas»), logo por baixo do painel: quantas
   comuns e incomuns ele tem em foil e quantas em normal, em IMPRESSÕES e em
   CÓPIAS. Recalculado do estado local, como o painel, para andar ao mesmo
   tempo que os `+`/`−`; o gémeo em Python é o `foil.contar`. Enquanto a
   edição carrega («Todas»), mostram-se os números do servidor. */

/* @foil-puro:inicio — só JavaScript puro, sem DOM nem `state`, para o teste
   o poder correr no node tal e qual. */
function foilContar(itens, labels) {
  const novo = () => ({ printings: 0, copies: 0, foil: 0, normal: 0, foil_printings: 0 });
  // `copies` é a SOMA das duas contagens (2026-09-26), nunca um número
  // guardado; até essa data era o total guardado e o `normal` a subtracção.
  const somar = (slot, normal, f) => {
    slot.printings++; slot.normal += normal; slot.foil += f;
    slot.copies += normal + f; slot.foil_printings += f > 0 ? 1 : 0;
  };
  const ORDEM = ['common', 'uncommon', 'rare', 'epic', 'showcase'];
  const total = novo();
  const por = new Map();
  for (const it of itens) {
    const rar = String(it.rarity || '?').toLowerCase();
    const normal = it.normal || 0, f = it.foil || 0;
    if (!por.has(rar)) por.set(rar, novo());
    somar(total, normal, f);
    somar(por.get(rar), normal, f);
  }
  const chaves = ORDEM.filter(r => por.has(r))
    .concat([...por.keys()].filter(r => !ORDEM.includes(r)).sort());
  total.rarity = chaves.map(r => ({
    id: r, label: (labels || {})[r] || (r.charAt(0).toUpperCase() + r.slice(1)),
    ...por.get(r),
  }));
  return total;
}
/* @foil-puro:fim */

function foilItens() {
  const itens = [];
  for (const g of state.payload?.groups || []) {
    for (const p of g.printings) {
      if (!state.foilOk.has(p.id)) continue;
      itens.push({ rarity: p.rarity || g.rarity || '?',
                   normal: state.tot.get(p.id) || 0,
                   foil: state.foil.get(p.id) || 0 });
    }
  }
  return itens;
}

/* O VALOR DAS CÓPIAS DE UMA IMPRESSÃO, em cêntimos — o terceiro gémeo do
   `prices.valor_sql` (SQL, a coleção inteira) e do `prices.valor_das_copias`
   (Python, o payload da edição). Aqui recalcula-se a cada `+`/`−`, como as
   barras, e por isso tem de dar o MESMO número que o servidor.

   As normais ao preço da normal; as FOIL ao preço da foil, e só ao da normal
   quando o CardTrader não as tem em foil (o fallback). Com
   `foil.conta_para_valor` desligado as foils não entram.

   As normais são o `state.valNorm` — as físicas menos as próprias dos decks —,
   não o `state.qty` da Coleção: era esse que estava aqui, e numa coleção com
   cópias sleevadas num deck a barra do valor dizia menos do que o servidor. */
function valorDasCopias(pid, preco) {
  const cat = state.index?.foil || {};
  const norm = state.valNorm.get(pid) || 0;
  const fo = cat.conta_para_valor ? (state.foil.get(pid) || 0) : 0;
  const pf = state.precoFoil.get(pid);
  return norm * preco + fo * (pf != null ? pf : preco);
}

/* O PREÇO DO FOIL: O FALLBACK FAZ DO VALOR UM PISO (2026-09-26)

   Com o `foil.conta_para_valor` ligado as foils somam-se ao valor ao PREÇO DA
   FOIL (`price_latest.price_foil_cents`, o mínimo das ofertas foil do
   CardTrader). Só quando não há oferta foil nenhuma é que a cópia cai para o
   preço da normal — e é ESSE pedaço que faz do total um piso, por isso diz-se
   onde o valor aparece em vez de se apresentar um número limpo.

   `curto` é a versão de uma linha, para debaixo da barra do valor. O
   `prices.valor_dos_foils` é quem separa os dois casos e os conta. */
function foilNotaValor(curto) {
  const f = state.index?.value?.foils;
  if (!f || !f.copies) return '';
  const n = f.ao_preco_da_normal || {};
  const pf = f.preco_de_foil || {};
  if (!n.copies) {
    return curto ? '' : `As ${f.copies} cópias foil estão contadas ao
      <b>preço da foil</b> do CardTrader.`;
  }
  if (curto) return `inclui ${n.copies} foil ao preço da normal — o real é mais alto`;
  return `${pf.copies ? `<b>${pf.copies} cópias foil</b> estão contadas ao
    <b>preço da foil</b> do CardTrader. ` : ''}<b>${n.copies}</b> ${
    pf.copies ? 'contam' : 'cópias foil estão contadas'} <b>ao preço da versão
    normal</b>, por o CardTrader não ter oferta foil delas — esse pedaço é um
    <b>piso</b> e o real é mais alto.${
      (f.sem_preco || {}).copies
        ? ` ${f.sem_preco.copies} sem preço no CardTrader não contam.` : ''}`;
}


function renderFoilResumo() {
  const el = $('#foil-resumo');
  if (!el) return;
  // O servidor manda o rótulo de cada raridade e o âmbito; sem ele (um payload
  // velho) a secção nem aparece.
  const cat = state.index?.foil;
  const doServidor = state.payload?.progress?.foil
    || cat?.sets?.[state.setId] || null;
  if (!cat || !doServidor) { el.innerHTML = ''; el.hidden = true; return; }
  const conta = state.payload ? foilContar(foilItens(), cat.labels) : doServidor;
  if (!conta || !conta.printings) { el.innerHTML = ''; el.hidden = true; return; }
  el.hidden = false;

  const bloco = (rot, c) => `<div class="fo-bloco">
    <div class="fo-rot">${escapeHTML(rot)}</div>
    <div class="fo-num"><b>${c.normal}</b> normais · <b class="fo">${c.foil}</b> foil</div>
    <div class="fo-sub">${c.printings} impressões · ${c.copies} cópias ao todo${
      c.foil_printings ? ` · ${c.foil_printings} com foil` : ''}</div>
  </div>`;
  const nomes = (cat.raridades || []).map(r => (cat.labels || {})[r] || r);
  // As duas perguntas dele dizem-se sempre: a linha muda quando ele ligar um
  // dos botões, em vez de o número mudar sem aviso.
  const contam = [cat.conta_para_coleccao ? 'para os alvos da Coleção' : null,
                  cat.conta_para_valor ? 'para o valor' : null].filter(Boolean);
  el.innerHTML = `<div class="fo-head">Foil e não-foil
      <small>${escapeHTML(nomes.join(' e ').toLowerCase() || 'comuns e incomuns')},
      só as impressões base${(cat.sem_edicoes || []).length
        ? ` — o ${escapeHTML(cat.sem_edicoes.join(', '))} fica de fora` : ''}.
      São duas contagens <b>separadas</b> — aqui somam-se para dizer quantas cartas
      tem na mão (3 normais e 3 foil são 6 cópias), mas nos <b>alvos nunca</b>:
      no tile o crachá é as normais e a linha de baixo é o foil, cada um com o seu.
      ${contam.length ? `Os foils contam ${escapeHTML(contam.join(' e '))}.`
        : 'Não contam para os alvos nem para o valor.'}
      ${cat.conta_para_coleccao ? '' : `<b>Não contam para os alvos</b>: se
        contassem, 2 normais e 1 foil liam-se «3/3» e uma falta de normais
        desaparecia do ecrã.`}
      ${cat.conta_para_valor ? foilNotaValor() : ''}
      ${cat.conta_para_coleccao ? `No «A mais» <b>não entram no que sobra</b>:
        o excedente conta primeiro as normais — os foils são peça de coleção,
        não excedente.` : ''}</small></div>
    <div class="fo-linhas">${bloco('Tudo', conta)}${
      conta.rarity.map(r => bloco(r.label, r)).join('')}</div>`;
}

/* QUE DECKS USAM ESTA CARTA (André, 2026-09-11): *"na coleção indica onde as
   cartas estão a ser usadas"*. É por carta lógica — a alocação é por carta —,
   por isso sai uma vez por grupo, no primeiro tile visível. «Azir 3 · Kennen 2
   (faltam 2)»: o Azir leva as 3 que pede, o Kennen pede 2 e não recebe nenhuma
   porque a Coleção não chega para os dois — essas 2 são para comprar. */
function usoLine(g) {
  const uso = g.decks || [];
  if (!uso.length) return '';
  // O que já vem a caminho para o deck (2026-09-11) não é falta: diz-se à
  // parte, com o mesmo número que a página do deck mostra.
  // O que o deck cobre com as suas cópias PRÓPRIAS (2026-09-21) não é uso
  // da Coleção: `wanted` já vem sem isso, e diz-se ao lado quantas são.
  // O DECK PRINCIPAL (2026-09-27) di-lo por extenso — *"na coleção aparece
  // que está a ser usado em X Deck"*. Esta cópia é da Coleção e continua
  // dela: o empréstimo é de apresentação, nada saiu daqui.
  const txt = uso.map(u => (u.principal
    ? `<b>em uso no deck ${escapeHTML(deckCurto(u.deck))}</b> ${u.wanted}`
    : `${escapeHTML(deckCurto(u.deck))} ${u.wanted}`)
    + (u.missing ? ` (falta${u.missing === 1 ? '' : 'm'} ${u.missing})` : '')
    + (u.ordered ? ` (${u.ordered} a caminho)` : '')
    + (u.proprias ? ` <i class="dim">+${u.proprias} próprias</i>` : '')).join(' · ');
  const falta = uso.reduce((s, u) => s + u.missing, 0);
  const pri = uso.some(u => u.principal);
  return `<div class="emdecks${falta ? ' falta' : ''}${pri ? ' principal' : ''}"
    title="${escapeAttr(uso.map(u =>
    `${u.deck}${u.principal ? ' (deck principal)' : ''}: pede ${u.wanted} à Coleção, tem ${u.have}${u.missing ? `, faltam ${u.missing}` : ''}${
      u.ordered ? `, ${u.ordered} a caminho` : ''}${u.proprias ? `, mais ${u.proprias} próprias do deck` : ''}`)
    .join(' / '))}">${txt}</div>`;
}

/* ONDE estão as cópias (André, 2026-09-10): *"a coleção fica em Binders de
   coleção; as cartas dos decks ficam em decks, e haverá um Binder que será
   apenas e exclusivamente para Decks/Venda"*.

   A `badge` do tile conta só as que estão nos binders de COLEÇÃO — é ela que
   manda na percentagem. Esta linha diz onde estão as outras, e é o que ele vai
   ler quando não encontrar a carta no binder. Só aparece quando há alguma fora
   da Coleção: com tudo arrumado, o tile fica como sempre esteve. */
function deckLine(pid) {
  const locs = state.locs.get(pid) || [];
  const fora = locs.filter(x => x.loc !== 'colecao');
  if (!fora.length) return '<div class="indeck" hidden></div>';
  const naCol = locs.find(x => x.loc === 'colecao');
  const onde = fora.map(x => `${x.qty}× ${escapeHTML(curtoLocal(x.label))}`).join(', ');
  return `<div class="indeck" title="${escapeAttr(fora.map(x => x.label).join(' / '))}">
    ${onde}${naCol ? ` · ${naCol.qty} na Coleção` : ''}</div>`;
}

/* «Deck Azir · Brutalizer» -> «Azir»; «Binder Decks/Venda» -> «Decks/Venda». */
function curtoLocal(label) {
  if (!label) return '';
  if (label.startsWith('Deck ')) return deckCurto(label.slice(5));
  if (label.startsWith('Binder ')) return label.slice(7);
  return label;
}

/* O rótulo curto de um deck: «Azir, Emperor · Azir, Sovereign» -> «Azir, Emperor».
   Um `Nome:` do ficheiro não tem « · » e fica inteiro. Se o servidor tiver
   desambiguado dois rótulos iguais com « (slug)» no fim, o sufixo fica —
   senão os dois LeBlanc voltavam a ler-se igual nos chips (2026-09-11). */
function deckCurto(name) {
  if (!name) return '';
  // Um GRUPO de Legend vem como «LeBlanc ·· LeBlanc Baited Hook» (2026-09-11,
  // noite): encurta-se cada membro e o «··» fica, é ele que diz que são dois.
  if (name.includes(' ·· ')) return name.split(' ·· ').map(deckCurto).join(' ·· ');
  const m = name.match(/^(.*?)( \([^()]*\))?$/);
  const base = m ? m[1] : name;
  const sufixo = m && m[2] ? m[2] : '';
  return base.split(' · ')[0] + sufixo;
}

/* O ritmo do binder dele (André, 2026-09-26): *"primeira fila de todas 4 /
   depois de 8 em 8 / que e como fica o Binder"*. Números FIXOS — a posição de
   um tile é a posição da carta na pasta, e um número que mudasse com a largura
   da janela não servia para encontrar a carta. Ver `.grid.binder` no CSS. */
const BINDER_PRIMEIRA = 4;
const BINDER_FILA = 8;

/* O bloco que é a ordem do binder: a sequência numerada do master set. Os
   outros blocos NÃO são a pasta (são a cauda da grelha) e ficam como estavam
   — decisão por confirmar com ele, ver o CLAUDE.md. */
const BLOCO_BINDER = 'master';

/* As filas do binder só valem com a SEQUÊNCIA INTEIRA no ecrã.
   Qualquer filtro — a procura, «Faltas», «só artes base», os tipos — esconde
   impressões, e a carta que ficasse no lugar da escondida passava a apontar a
   bolsa errada. Nesse caso volta-se ao `auto-fill` e diz-se porquê: mentir na
   posição é pior do que mudar de desenho. */
function binderCheio() {
  let todas = 0, vistas = 0;
  for (const g of state.payload?.groups || []) {
    todas += g.printings.filter(p => (p.block || 'master') === BLOCO_BINDER).length;
    vistas += visiblePrintings(g).filter(p => (p.block || 'master') === BLOCO_BINDER).length;
  }
  return { cheio: todas > 0 && vistas === todas, todas, vistas };
}

/* A grelha em blocos (André, 2026-09-08): *"master set playset todo seguido"*,
   nunca intercalados. A ORDEM é a de 2026-09-19 (*"coloca as OverNumbered a
   seguir ao master Set, depois as AltArt, depois as Promos"*): primeiro a
   sequência do master set, por número de coleção; depois as sobrenumeradas;
   depois as artes alternativas; depois as promos.

   Os blocos, a ordem e os rótulos vêm do payload (`metrics.ordem_dos_blocos`,
   `master_set.ordem_dos_blocos` no config), para a regra viver num sítio só; o
   contador de cada um é recalculado aqui, como as barras, para andar ao mesmo
   tempo que os +/-.

   A SEQUÊNCIA sai nas filas do binder (4 + 8) quando está inteira no ecrã —
   ver `binderCheio` aqui em cima e `.grid.binder` no CSS. */
function render() {
  const grid = $('#grid');
  const parts = [];
  state.tiles = [];

  const grupos = state.payload?.groups || [];
  const blocos = state.payload?.blocks || [{ id: BLOCO_BINDER, label: null }];
  let mostrados = 0;

  const binder = binderCheio();

  for (const b of blocos) {
    const pedacos = [];
    // As filas do binder valem para a sequência, e só com ela inteira.
    const filasDoBinder = b.id === BLOCO_BINDER && binder.cheio;
    // Quantos tiles já saíram na edição que está a ser desenhada: é ele que
    // decide onde entra o calço que fecha a primeira fila nas 4. Recomeça a
    // cada edição — em «Todas» cada edição é a sua pasta.
    let naEdicao = 0;
    let feitas = 0, total = 0, alguma = 0, alvoMax = 0;
    let edicao = null;
    for (const g of grupos) {
      const list = visiblePrintings(g).filter(p => (p.block || 'master') === b.id);
      if (!list.length) continue;
      // Em «Todas» os grupos vêm de cinco edições seguidas: um cabeçalho
      // fino cada vez que a edição muda dentro do bloco, senão o OGN-298 e o
      // OGS-001 ficavam colados sem nada a dizer que a edição acabou.
      if (g.set && g.set !== edicao) {
        edicao = g.set;
        naEdicao = 0;
        pedacos.push(`<h3 class="section-head edicao">${escapeHTML(g.set_name || g.set)}</h3>`);
      }
      for (const p of list) {
        const t = state.targets.get(p.id) || 0;
        if (t <= 0) continue;
        total++;
        const q = state.qty.get(p.id) || 0;
        if (q >= t) feitas++;
        if (q > 0) alguma++;
        alvoMax = Math.max(alvoMax, t);
      }
      if (filasDoBinder) {
        // UMA IMPRESSÃO, UMA CÉLULA — no binder cada carta ocupa uma bolsa.
        // Nada de `.group.multi` a ocupar várias colunas: a fila deixava de
        // ter 8 cartas e a posição deixava de ser a da pasta. (Hoje não há
        // grupo nenhum com duas impressões no mesmo bloco — medido a
        // 2026-09-26 nas cinco edições —, mas a regra não pode depender
        // disso.)
        list.forEach((p, i) => {
          state.tiles.push(p.id);
          pedacos.push(`<div class="group">${tileHTML(g, p, i === 0)}</div>`);
          naEdicao++;
          if (naEdicao === BINDER_PRIMEIRA) {
            pedacos.push('<div class="binder-gap" aria-hidden="true"></div>');
          }
        });
        continue;
      }
      const inner = list.map((p, i) => {
        state.tiles.push(p.id);
        return tileHTML(g, p, i === 0);   // o uso nos decks sai uma vez por carta
      }).join('');
      pedacos.push(list.length > 1
        ? `<div class="group multi" style="--span:${list.length}">${inner}</div>`
        : `<div class="group">${inner}</div>`);
    }
    if (!pedacos.length) continue;
    mostrados++;
    if (b.label) {
      // "tens N de M" — o contador do bloco. O cabeçalho ocupa a linha inteira
      // da grelha (`.section-head`), sem grelha aninhada. Os blocos da coleção
      // dizem que contam para a percentagem; os de fora dizem que não — é a
      // diferença toda entre eles e tem de se ler no ecrã.
      //
      // «tens N» é de quantas impressões ele tem PELO MENOS UMA cópia. Quando o
      // bloco pede playset, o «N no playset completo» vai a seguir: desde que a
      // coleção extra passou a pedir 3 (2026-09-14), o contador de playsets
      // sozinho dizia «tens 0 de 6» com duas cartas a cores na grelha
      // (fotografias do André, 2026-09-15). Com alvo 1 os dois números são o
      // mesmo e diz-se um só.
      const completos = alvoMax > 1
        ? ` · <b>${feitas}</b> no playset completo` : '';
      parts.push(`<h2 class="section-head ${b.counts ? 'cauda' : 'fora'}">${escapeHTML(b.label)}
        <span>tens <b>${alguma}</b> de <b>${total}</b>${completos} — ${b.counts ? '' : 'não '}
        contam para a percentagem de master set</span></h2>`);
    }
    if (b.id === BLOCO_BINDER && !binder.cheio) {
      // Um filtro escondeu parte da sequência. Dizer isto é o que impede a
      // página de apontar a bolsa errada em silêncio.
      parts.push(`<p class="binder-nota">As filas <b>não</b> são as do binder:
        um filtro está a esconder parte da sequência (vêem-se
        <b>${binder.vistas}</b> de <b>${binder.todas}</b> impressões). Limpa a
        procura e os filtros para voltar às filas de
        ${BINDER_PRIMEIRA} + ${BINDER_FILA}.</p>`);
    }
    parts.push(filasDoBinder
      ? `<div class="binder-wrap"><div class="grid binder">${pedacos.join('')}</div></div>`
      : pedacos.join(''));
  }

  grid.innerHTML = parts.join('');
  $('#empty').hidden = mostrados > 0;
  $('#count-line').textContent = `${state.tiles.length} impressões a mostrar`
    + (state.payload ? ` · ${state.payload.groups.length} cartas ${
      state.setId === TODAS ? 'nas edições todas' : 'na edição'}` : '');
  renderProgress();
  state.focus = -1;
}

function renderProgress() {
  if (!state.payload) return;

  // Recalculado no cliente a partir do estado local, para as barras andarem
  // ao mesmo tempo que os +/- (atualização otimista).
  let pDone = 0, pTotal = 0, mDone = 0, mTotal = 0;
  const seen = new Set();
  const porBloco = new Map();
  // Os degraus da contagem por níveis da barra vêm do servidor (são os do
  // catálogo inteiro); os números recalculam-se aqui, no mesmo ciclo da
  // barra — é o mesmo âmbito. Só a linha «N cópias a comprar» os lê hoje; os
  // chips que os mostravam deram lugar ao painel do topo (2026-09-21).
  const niv = Array.from({ length: niveisN() },
                         (_, i) => ({ k: i + 1, done: 0, total: 0, missing: 0, cents: 0 }));

  for (const g of state.payload.groups) {
    const play = state.play.get(g.card_key);
    if (play && play.target > 0 && !seen.has(g.card_key)) {
      seen.add(g.card_key);
      pTotal++;
      if (play.owned >= play.target) pDone++;
    }
    for (const p of g.printings) {
      const t = state.targets.get(p.id) || 0;
      // O alvo é o que se mostra no tile; o bloco é o que entra na conta. Os
      // tokens têm alvo (ele quer ver quantos lhe faltam) mas ficam fora da
      // percentagem; os três blocos da coleção contam todos.
      if (t <= 0) continue;
      const bloco = state.blocks.get(p.id) || 'master';
      const ok = (state.qty.get(p.id) || 0) >= t;
      const bslot = porBloco.get(bloco) || [0, 0];
      bslot[1]++; if (ok) bslot[0]++;
      porBloco.set(bloco, bslot);
      if (!state.counting.has(bloco)) continue;
      mTotal++; if (ok) mDone++;
      const tem = state.qty.get(p.id) || 0;
      for (const nv of niv) {
        // `min(k, alvo)`: uma impressão de alvo 1 — Legend, Battlefield — só
        // pode faltar no nível 1; do 2 em diante já está feita.
        const falta = Math.max(0, Math.min(nv.k, t) - tem);
        nv.total++; nv.missing += falta; nv.cents += falta * (p.price || 0);
        if (!falta) nv.done++;
      }
    }
  }

  $('#play-num').textContent = `${pDone}/${pTotal}`;
  $('#play-bar').style.width = pTotal ? `${(pDone / pTotal) * 100}%` : '0';
  $('#master-num').textContent = `${mDone}/${mTotal}`;
  $('#master-bar').style.width = mTotal ? `${(mDone / mTotal) * 100}%` : '0';

  // A percentagem de cada bloco, por baixo da barra global: a barra soma os
  // três blocos da coleção e ele quer ver de onde vem cada pedaço (e como está
  // o dos tokens, que não entra). Mesma ordem do payload.
  const chips = (state.payload.blocks || []).filter(b => porBloco.has(b.id)).map(b => {
    const [d, t] = porBloco.get(b.id);
    const nome = b.short || b.id;
    const pct = t ? Math.round((d / t) * 100) : 0;
    return `<span class="rarity ${d >= t ? 'is-done' : ''}${b.counts ? '' : ' is-out'}"
      title="${b.counts ? 'conta' : 'não conta'} para a percentagem de master set"
      >${escapeHTML(nome)} <b>${d}/${t}</b> · ${pct}%</span>`;
  });
  $('#master-blocks').innerHTML = chips.length > 1 ? chips.join('') : '';

  // Só as edições a sério: em «Todas» a conta é das cinco juntas e guardá-la
  // debaixo de uma sexta chave contava tudo a dobrar.
  if (niv.length && state.setId !== TODAS) state.levels.set(state.setId, niv);
  renderPainel();
  renderFoilResumo();

  // Valor: recalculado localmente pela mesma razão que as barras — para andar
  // ao mesmo tempo que os +/-. A barra compara o que tenho com o que a edição
  // inteira valeria pela métrica de master set.
  const val = state.payload.progress.value;
  const block = $('#value-block');
  if (val && val.has_prices) {
    // As ESCONDIDAS (tokens, signatures, runas sem numeração) valem o que ele
    // tem delas mas nunca chegam à grelha: o servidor manda esse pedaço à parte
    // para a barra recalculada aqui dar o mesmo número que a dele.
    let owned = val.hidden_owned || 0;
    for (const g of state.payload.groups) {
      for (const p of g.printings) {
        if (p.price != null) owned += valorDasCopias(p.id, p.price);
      }
    }
    block.hidden = false;
    $('#value-block .bar-label span').textContent =
      state.setId === TODAS ? 'Valor das edições todas' : 'Valor nesta edição';
    $('#value-num').textContent = eur(owned);
    $('#value-bar').style.width = val.full ? `${Math.min(100, (owned / val.full) * 100)}%` : '0';
    // A ressalva do foil (2026-09-26): as foils que o CardTrader não tem em
    // foil contam ao preço da normal, e por isso este número é um piso. Nunca
    // mostrar o valor sem ela.
    const nota = foilNotaValor(true);
    $('#value-sub').innerHTML = `de ${eur(val.full)} se estivesse completa${
      nota ? ` · <i class="fo-piso">${escapeHTML(nota)}</i>` : ''}`;
  } else {
    block.hidden = true;
  }
}


/* ================================ o painel do topo da Coleção (2026-09-21)

   O André escolheu o «layout H»: por baixo dos separadores das edições e por
   cima da grelha, TRÊS CARTÕES — «1 de cada», «2 de cada», «playset» — com o
   tenho/total em grande (nunca a percentagem), uma barra fina e o «faltam
   N»; e por baixo DOIS QUADROS, Raridade e Domínio, uma linha por categoria
   com a bolinha da cor, três mini-barras (uma por nível) e o tenho/total à
   direita. Sobre o BLOCO escolhido (master set, sobrenumeradas, artes
   alternativas, promos — ou «Tudo», os blocos todos somados, cada um com o
   seu alvo) da edição aberta, ou de «Todas».

   A conta é a do `painel.py` do servidor, recalculada aqui a partir do
   estado local para andar ao mesmo tempo que os +/-, como as barras:

     nível 1 = impressões com pelo menos 1 cópia
     nível 2 = com pelo menos min(2, alvo)
     nível 3 = com pelo menos o alvo (o playset)

   Nos blocos de alvo 1 os três coincidem — é o esperado. AS RUNAS NUNCA
   ENTRAM (o `rune` do grupo vem do servidor), e o cabeçalho diz quantas
   ficaram de fora quando isso faz o playset diferir da barra do master set.
   As escondidas nem chegam ao payload, como sempre.

   `painelContar` é o gémeo do `painel.contar` do Python e há um teste que
   corre os dois sobre os mesmos itens (`tests/test_painel.py`, via node).  */

/* @painel-puro:inicio — só JavaScript puro, sem DOM nem `state`, para o
   teste o poder correr no node tal e qual. */

/* O alvo do nível k (de 3) para uma impressão de alvo `alvo`: 1, min(2,
   alvo), o alvo. O gémeo do `metrics.alvo_do_nivel`. */
function painelAlvoDoNivel(k, alvo) {
  return k >= 3 ? alvo : Math.min(k, alvo);
}

/* `itens` = [{alvo, tem, rarity, domain}]; `cat` = {rarities: [[id, rótulo]],
   domains: [[id, rótulo]]} (a ordem e os nomes vêm do servidor). Devolve
   {n, levels: [n1, n2, n3], rarity: [{id, label, n, levels}], domain: [...]}. */
function painelContar(itens, cat) {
  const N = 3;
  const novo = () => ({ n: 0, levels: [0, 0, 0] });
  const total = novo();
  const porRar = new Map(), porDom = new Map();
  for (const it of itens) {
    const alvo = it.alvo || 0;
    if (alvo <= 0) continue;
    const marca = [];
    for (let k = 1; k <= N; k++) marca.push((it.tem || 0) >= painelAlvoDoNivel(k, alvo) ? 1 : 0);
    const rar = String(it.rarity || '?').toLowerCase();
    const dom = String(it.domain || 'none').toLowerCase();
    if (!porRar.has(rar)) porRar.set(rar, novo());
    if (!porDom.has(dom)) porDom.set(dom, novo());
    for (const slot of [total, porRar.get(rar), porDom.get(dom)]) {
      slot.n++;
      for (let i = 0; i < N; i++) slot.levels[i] += marca[i];
    }
  }
  const linhas = (por, ordem) => {
    const rot = new Map(ordem);
    const chaves = ordem.map(([id]) => id).filter(id => por.has(id));
    const extra = [...por.keys()].filter(id => !rot.has(id)).sort();
    return [...chaves, ...extra].map(id => ({
      id, label: rot.get(id) || (id.charAt(0).toUpperCase() + id.slice(1)),
      n: por.get(id).n, levels: por.get(id).levels,
    }));
  };
  // Um domínio novo entra antes das duas linhas de fecho («Sem domínio»,
  // «Multi-domínio»), como no Python.
  const doms = cat.domains || [];
  const fecho = doms.filter(([id]) => id === 'none' || id === 'multi');
  const fixos = doms.filter(([id]) => id !== 'none' && id !== 'multi');
  const novos = [...porDom.keys()].filter(id => !doms.some(([d]) => d === id)).sort()
    .map(id => [id, id.charAt(0).toUpperCase() + id.slice(1)]);
  return {
    n: total.n, levels: total.levels,
    rarity: linhas(porRar, cat.rarities || []),
    domain: linhas(porDom, [...fixos, ...novos, ...fecho]),
  };
}
/* @painel-puro:fim */

/* Os itens do bloco escolhido, do estado local: uma impressão por linha, com
   o alvo do tile e as cópias na Coleção. Com «Tudo» (`TUDO`) entram as
   impressões de todos os blocos, cada uma com o alvo do SEU tile — é assim
   que os níveis saem somados bloco a bloco, sem um alvo único por cima. As
   runas ficam de fora aqui — é o `rune` do grupo, dito pelo servidor.
   Devolve também quantas runas ficaram de fora, para o cabeçalho. */
function painelItens(bloco) {
  const itens = [];
  let runas = 0;
  for (const g of state.payload?.groups || []) {
    for (const p of g.printings) {
      const t = state.targets.get(p.id) || 0;
      if (t <= 0) continue;
      if (bloco !== TUDO && (state.blocks.get(p.id) || 'master') !== bloco) continue;
      if (g.rune) { runas++; continue; }
      itens.push({ alvo: t, tem: state.qty.get(p.id) || 0,
                   rarity: g.rarity || '?', domain: g.domain || 'none' });
    }
  }
  return { itens, runas };
}

/* Os blocos que o painel oferece: os do payload da edição aberta, pela ordem
   do servidor, com o rótulo e o alvo do `index.painel.blocks` — e no FIM o
   «Tudo», que não é um bloco da grelha (nunca vem no `payload.blocks`). O
   que abre por omissão continua a ser o primeiro, o master set. */
function painelBlocos() {
  const cat = new Map((state.index?.painel?.blocks || []).map(b => [b.id, b]));
  const ids = (state.payload?.blocks || []).map(b => b.id);
  if (!ids.length) return [];
  return [...ids, TUDO].map(id => cat.get(id)
    || { id, label: id === TUDO ? 'Tudo' : id, target: '' });
}

function renderPainel() {
  const el = $('#painel');
  if (!el) return;
  const cat = state.index?.painel || {};
  const blocos = painelBlocos();
  if (!blocos.length) { el.innerHTML = ''; return; }
  // Uma escolha guardada de um bloco que esta edição não tem (o OGS não tem
  // sobrenumeradas) cai no primeiro — o master set.
  let escolhido = state.prefs.painelBloco;
  if (!blocos.some(b => b.id === escolhido)) escolhido = blocos[0].id;

  let conta, runas;
  if (state.payload) {
    const r = painelItens(escolhido);
    conta = painelContar(r.itens, cat);
    runas = r.runas;
  } else {
    // «Todas» ainda a carregar: os números do servidor, tal e qual.
    conta = cat.sets?.[state.setId]?.[escolhido];
    runas = cat.runes_out?.[state.setId] || 0;
    if (!conta) { el.innerHTML = '<p class="empty">a carregar…</p>'; return; }
  }

  const niveis = cat.levels || [{ label: '1 de cada' }, { label: '2 de cada' }, { label: 'playset' }];
  const pct = (d, n) => (n ? (d / n) * 100 : 0).toFixed(1);
  const cartoes = niveis.map((lv, i) => {
    const d = conta.levels[i] || 0;
    return `<div class="cartao">
      <div class="cartao-rot">${escapeHTML(lv.label)}</div>
      <div class="cartao-num">${d}<span>/${conta.n}</span></div>
      <div class="cartao-bar"><i class="n${i + 1}" style="width:${pct(d, conta.n)}%"></i></div>
      <div class="cartao-falta">faltam <b>${conta.n - d}</b></div>
    </div>`;
  }).join('');

  const quadro = (titulo, prefixo, linhas) => `<div class="quadro">
    <div class="quadro-head"><span class="quadro-tit">${titulo}</span>
      <span class="quadro-leg">1 · 2 · playset</span></div>
    <div class="quadro-linhas">${linhas.length ? linhas.map(l => `<div class="ql">
      <span class="dot ${prefixo}-${escapeAttr(l.id)}"></span>
      <span class="ql-nome">${escapeHTML(l.label)}</span>
      ${l.levels.map((d, i) => `<span class="mini"
        title="${escapeAttr(niveis[i]?.label || '')}: ${d} de ${l.n}"><i class="n${i + 1}"
        style="width:${pct(d, l.n)}%"></i></span>`).join('')}
      <span class="ql-num">${l.levels[l.levels.length - 1]}<span>/${l.n}</span></span>
    </div>`).join('') : '<p class="empty">nada neste bloco</p>'}</div>
  </div>`;

  const chips = blocos.map(b => `<button class="chip-b ${b.id === escolhido ? 'is-on' : ''}"
    data-painel-bloco="${escapeAttr(b.id)}" title="${escapeAttr(b.target ? `alvo: ${b.target}` : '')}"
    >${escapeHTML(b.label)}</button>`).join('');
  // O cartão «playset» do master set NÃO é a barra do master set quando há
  // runas: a barra conta-as (a 3, desde 2026-09-15), o painel nunca. Diz-se
  // em vez de deixar dois números diferentes a olhar um para o outro.
  const nota = runas
    ? `<span class="painel-nota">sem as ${runas} runa${runas === 1 ? '' : 's'} — nunca entram aqui</span>`
    : '';

  el.innerHTML = `<div class="painel-top"><div class="chips painel-blocos">${chips}</div>${nota}</div>
    <div class="painel-cartoes">${cartoes}</div>
    <div class="painel-quadros">${quadro('Raridade', 'rar', conta.rarity)}${quadro('Domínio', 'dom', conta.domain)}</div>`;

  for (const b of el.querySelectorAll('[data-painel-bloco]')) {
    b.onclick = () => {
      state.prefs.painelBloco = b.dataset.painelBloco;
      savePrefs();
      renderPainel();
    };
  }
}


/* ================================ contagem por níveis da barra (2026-09-08)

   André: *"quantas cartas faltam para ter 1 de cada, quantas faltam para ter
   2 de cada, quantas faltam para ter o playset de cada."* É a MESMA conta da
   barra do master set, partida em degraus (`min(k, alvo)`), e conta CÓPIAS
   em falta. Desde 2026-09-21 mostra-se no painel de cima (por impressões, e
   sem as runas); o que fica aqui é o que a linha «N cópias a comprar» e o
   selector das wantlists ainda lêem.                                        */

/* Quantos degraus há. Vem do servidor (`metrics.niveis_max`, o maior alvo do
   catálogo inteiro) para as cinco edições mostrarem os mesmos. */
function niveisN() {
  const doSet = state.payload?.progress?.levels;
  if (doSet && doSet.length) return doSet.length;
  return (state.index?.levels?.levels || []).length;
}


/* ============================ wantlists do Cardmarket, no fim de cada edição

   André, 2026-09-08: *"Quero também que no fim de cada edição me dês uma
   wantlist para eu colocar no Cardmarket."*

   NÃO É UMA LISTA NOVA. São as faltas do master set (`a_subir.master_faltas`,
   o `api/wantlist.json`), cortadas por edição e escritas pelo MESMO gerador
   (`cmLinha`). Até 2026-09-15 vinham dentro do `api/faltas.json`, chave
   `master`; esse ficheiro foi apagado com o separador das faltas e esta
   lista, que é da Coleção, ficou com URL próprio.

   É SÓ o master set (2026-09-15): a coleção extra tem alvo na grelha para ele
   ver quantas tem, não para comprar — o servidor já a tira
   (`listas_de_compra.so_master_set`) e o `scope` diz quantas.

   Dois blocos: o da edição aberta e, a seguir, o de todas as edições pela
   ordem dos separadores.                                                    */

/* Os itens de uma edição (ou de todas, com `setId` a nulo), até ao nível
   pedido.

   O NÍVEL não é uma lista nova: é o mesmo `min(k, alvo)` da contagem por
   níveis, aplicado às faltas que o servidor já mandou. Dá para fazer aqui
   porque cada item traz o `have` (cópias + a caminho) e o `target`; o gémeo em
   Python é o `nivel` do `a_subir.wantlist`, e há teste que compara os dois. */
function wlItens(setId, nivel) {
  const m = state.wantlist;
  if (!m) return [];
  const base = m.sets.filter(s => !setId || s.set === setId).flatMap(s => s.items);
  if (!nivel) return base;
  const out = [];
  for (const x of base) {
    const alvo = Math.min(nivel, x.target);
    const missing = alvo - x.have;
    if (missing <= 0) continue;
    out.push({ ...x, target: alvo, full_target: x.target, missing,
               total: (x.price || 0) * missing });
  }
  return out;
}

/* Os degraus do seletor: os mesmos da contagem por níveis. */
function wlNiveis() {
  const n = niveisN();
  if (n) return n;
  const alvos = wlItens(null).map(x => x.target || 1);
  return alvos.length ? Math.max(...alvos) : 1;
}

/* «até 1 de cada / até 2 / playset». O último degrau é o alvo inteiro, e vale
   `null` — assim a lista sem seletor é exactamente a de sempre. */
function wlSeletorHTML(nivel) {
  const n = wlNiveis();
  if (n < 2) return '';
  const bt = (v, txt) => `<button class="chip-b ${(nivel || 0) === (v || 0) ? 'is-on' : ''}"
    data-wlnivel="${v == null ? '' : v}">${txt}</button>`;
  let s = '';
  for (let k = 1; k < n; k++) s += bt(k, k === 1 ? 'até 1 de cada' : `até ${k} de cada`);
  return `<div class="chips wl-niveis">${s}${bt(null, 'playset')}</div>`;
}

/* O `wantlist.json` são centenas de KB e não se pede duas vezes: quem chegar
   segundo espera pelo pedido que já vai a caminho. Só BUSCA. */
function garanteWantlist(forcar = false) {
  if (state.wantlist && !forcar) return Promise.resolve(state.wantlist);
  if (!state.wantlistP) {
    state.wantlistP = getJSON('api/wantlist.json')
      .then(p => { state.wantlist = p; return p; })
      .finally(() => { state.wantlistP = null; });
  }
  return state.wantlistP;
}

/* O mesmo para as listas de compra dos decks (Staples, Por deck, Pimp decks):
   só busca — desenhar é o `loadDeckFaltas`. */
function garanteCompras(forcar = false) {
  if (state.compras && !forcar) return Promise.resolve(state.compras);
  if (!state.comprasP) {
    state.comprasP = getJSON('api/compras.json')
      .then(p => { state.compras = p; return p; })
      .finally(() => { state.comprasP = null; });
  }
  return state.comprasP;
}

/* Volta a pedir o ficheiro e redesenha o que já estiver no ecrã. */
function wlAtualizar(zona) {
  state.wlStale = false;
  zona.innerHTML = '<p class="empty">a atualizar…</p>';
  garanteWantlist(true)
    .then(() => { renderWantlists(); renderFaltaLinha(); })
    .catch(err => { zona.innerHTML = `<p class="empty">${escapeHTML(err.message)}</p>`; });
}

function renderWantlists() {
  const zona = $('#wantlists');
  if (!zona) return;

  if (!state.wantlist) {
    zona.innerHTML = '<p class="empty">a preparar a wantlist…</p>';
    garanteWantlist()
      .then(() => { renderWantlists(); renderFaltaLinha(); })
      .catch(err => { zona.innerHTML = `<p class="empty">${escapeHTML(err.message)}</p>`; });
    return;
  }
  const m = state.wantlist;

  const nome = state.payload?.set?.name || state.setId || '';
  const nivel = state.prefs.wlNivel || null;
  // Em «Todas» o bloco da edição era o mesmo que o de tudo: fica só o de tudo.
  const edicao = edicaoAberta();
  const daEdicao = edicao ? wlItens(edicao, nivel) : null;
  const todas = wlItens(null, nivel);
  const sufixo = nivel ? `-ate${nivel}` : '';
  // O que o degrau muda na lista, dito por extenso: sem isto, uma lista que
  // encolhe a metade parece que perdeu cartas.
  const doNivel = nivel
    ? ` Está no degrau <b>até ${nivel} de cada</b>: de cada carta pede-se no
        máximo ${nivel}, e as de alvo <b>1</b> (Legends e Battlefields) vão
        sempre por inteiro.`
    : '';

  zona.innerHTML = `
    ${state.wlStale ? `<p class="note wl-stale">As contagens mudaram desde que
      esta lista foi feita. <button class="btn ghost" id="wl-refresh">Atualizar</button></p>` : ''}

    ${daEdicao ? wlBloco('wl-edicao', `Wantlist Cardmarket — ${escapeHTML(nome)} · master set`, daEdicao,
      `Tudo o que falta desta edição ao <b>master set</b> — a sequência, a que
       conta para a percentagem —, ao <b>playset</b> do tipo (Unit/Spell/Gear
       e runa 3, Legend e Battlefield 1). Conta enquanto <b>cópias + a
       caminho &lt; alvo</b>, e vai por número de coleção.${doNivel}
       As outras wantlists desta edição — <b>Alt Art</b>, <b>OverNumbered</b> e
       <b>Promos</b>, uma por bloco, separadas — estão no separador
       <a href="#faltas-edicao">Faltas</a>.${foraTexto(m.scope)}`, nivel) : ''}

    ${wlBloco('wl-tudo', 'Wantlist — tudo', todas,
      `As cinco edições seguidas, na ordem dos separadores — tudo o que falta
       ao master set, para comprar de uma vez.${doNivel}`, nivel)}`;

  const rf = $('#wl-refresh');
  if (rf) rf.onclick = () => wlAtualizar(zona);

  // Os dois blocos partilham o degrau: são a mesma pergunta ("até quantas
  // compro"), e vê-los responder coisas diferentes na mesma página confundia.
  for (const b of zona.querySelectorAll('[data-wlnivel]')) {
    b.onclick = () => {
      state.prefs.wlNivel = b.dataset.wlnivel ? Number(b.dataset.wlnivel) : null;
      savePrefs();
      renderWantlists();
    };
  }

  if (edicao) {
    wlLigar('wl-edicao', () => wlItens(edicao, state.prefs.wlNivel || null),
            `riftvault-wantlist-${edicao}${sufixo}-${hojeISO()}.csv`);
  }
  wlLigar('wl-tudo', () => wlItens(null, state.prefs.wlNivel || null),
          `riftvault-wantlist-tudo${sufixo}-${hojeISO()}.csv`);
}

function wlBloco(id, titulo, itens, nota, nivel) {
  const copias = itens.reduce((s, x) => s + cmQtd(x), 0);
  const cents = itens.reduce((s, x) => s + (x.total || 0), 0);
  const semPreco = itens.filter(x => x.price == null).length;
  if (!itens.length) {
    return `<section class="wl-bloco" id="${id}">
      <h2 class="section-head wl-head">${titulo}</h2>
      ${wlSeletorHTML(nivel)}
      <p class="empty">Não falta nada${nivel ? ` até ${nivel} de cada` : ''} —
        não há nada para comprar aqui.</p></section>`;
  }
  return `<section class="wl-bloco" id="${id}">
    <h2 class="section-head wl-head">${titulo}
      <span>${itens.length} impress${itens.length === 1 ? 'ão' : 'ões'} ·
        ${copias} cópia${copias === 1 ? '' : 's'} · ${eur(cents)}${
        semPreco ? ` · ${semPreco} sem preço no CardTrader` : ''}</span></h2>
    ${wlSeletorHTML(nivel)}
    <p class="note">${nota}</p>
    ${cmZonaHTML(id + '-cm')}</section>`;
}

/* Os mesmos três botões das outras listas — e a caixa já vem preenchida, que é
   o ponto do pedido dele: a wantlist está ali, pronta a copiar, sem ter de
   carregar em nada primeiro. */
function wlLigar(id, getItens, ficheiro) {
  const zid = id + '-cm';
  if (!$(`#${zid}-txt`)) return;
  cmLigar(zid, getItens, ficheiro);
  cmMostrar(zid, getItens(), false, { foco: false, copiar: false });
}

/* A linha no cabeçalho da edição, a ligar ao bloco. Os números são os do
   bloco — não os da barra de progresso —, senão o que ele lê em cima não batia
   certo com a lista para onde a linha o manda. */
function renderFaltaLinha() {
  const el = $('#falta-linha');
  if (!el) return;
  const m = state.wantlist;
  const d = m && m.sets.find(s => s.set === state.setId);
  el.hidden = !d;
  if (!d) return;
  // Esta linha é a LISTA DE COMPRA, e o painel por cima é a MÉTRICA — o
  // «faltam N» dos cartões são IMPRESSÕES por chegar ao nível; isto são
  // CÓPIAS a comprar, e as cópias da barra (`state.levels`, o playset do
  // master set com as runas) contam os showcases e não descontam o que vem a
  // caminho. Vistos lado a lado sem explicação liam-se como erro de contagem
  // (2026-09-09). Diz-se a diferença, e só quando ela existe. O «mais» só
  // acontece com o `listas_de_compra.so_master_set` desligado.
  const nv = (state.levels.get(state.setId) || []).slice(-1)[0];
  const menos = nv && nv.missing > d.copies;
  const mais = nv && nv.missing < d.copies;
  el.innerHTML = `<b>${d.copies}</b> cópia${d.copies === 1 ? '' : 's'}
    <b>a comprar</b> nesta edição · <b>${eur(d.cents)}</b> ao preço de hoje —
    <a href="#wl-edicao">wantlist para o Cardmarket</a>${menos
      ? `<br><small>São menos do que as <b>${nv.missing}</b> cópias que faltam
         ao playset do master set: a lista de compra não leva showcases e já
         desconta o que vem a caminho. (Os «faltam» dos cartões em cima são
         impressões, não cópias.)</small>` : ''}${mais
      ? `<br><small>São mais do que as <b>${nv.missing}</b> cópias que faltam
         ao playset do master set: a lista leva também a coleção extra (artes
         alternativas, sobrenumeradas, promos), que não conta para a
         percentagem.</small>` : ''}`;
}

/* Um `+` ou um `−` desatualiza as duas listas, que vieram do servidor. Não se
   volta a pedir o `wantlist.json` sozinho — são centenas de KB e ele pode
   estar a marcar uma caixa inteira de cartas. Diz-se que está velha e ele
   atualiza quando quiser. */
function wlDesatualizar() {
  if (state.wlStale || !state.wantlist) return;
  state.wlStale = true;
  renderWantlists();
}

/* Atualiza no sítio os tiles afetados, sem voltar a desenhar a grelha toda —
   redesenhar 352 tiles a cada clique dava lag no telemóvel. */
function refreshTiles(pid, cardKey) {
  for (const el of document.querySelectorAll(`.tile[data-pid="${CSS.escape(pid)}"]`)) {
    const q = state.qty.get(pid) || 0;
    const t = state.targets.get(pid) || 0;
    const focused = el.classList.contains('focus');
    el.className = `tile ${tileState(pid)}${focused ? ' focus' : ''} flash`;
    el.querySelector('.badge').textContent = t > 0 ? `${q}/${t}` : `${q}`;
    // O `−` baixa as NORMAIS, não o `qty` da Coleção (que desde 2026-09-26
    // pode trazer foils por cima) — ver o `qtyNormais`.
    el.querySelector('.step.minus').disabled = qtyNormais(pid) <= 0;
    const linha = el.querySelector('.indeck');
    if (linha) linha.outerHTML = deckLine(pid);
    const fo = el.querySelector('.foil-linha');
    if (fo) fo.outerHTML = foilLinha(pid);
    setTimeout(() => el.classList.remove('flash'), 400);
  }
  // A métrica de playset é da carta lógica: mexe em todos os tiles dela.
  const play = state.play.get(cardKey);
  if (play) {
    for (const el of document.querySelectorAll(`.tile[data-ck="${CSS.escape(cardKey)}"] .playset`)) {
      // O prefixo e o preço vêm de data-attributes para não se perderem ao
      // reescrever a linha a cada clique.
      const preco = el.dataset.price ? ` · ${eur(Number(el.dataset.price))}` : '';
      el.textContent = `${el.dataset.kind || 'jogável'} ${play.owned}/${play.target}${preco}`;
      el.classList.toggle('is-done', play.target > 0 && play.owned >= play.target);
    }
  }
  renderProgress();
}

/* -------------------------------------------------------------- escrita */

function applyLocal(pid, delta) {
  const ck = state.meta.get(pid)?.card_key;
  state.qty.set(pid, Math.max(0, (state.qty.get(pid) || 0) + delta));
  // As NORMAIS físicas andam com o `+`/`−` (é o `copies.qty` que muda). O FOIL
  // não se toca: são duas contagens independentes desde 2026-09-26, cada uma
  // com o seu botão. Até essa data o foil era cortado aqui, porque era uma
  // fatia do total.
  state.tot.set(pid, Math.max(0, (state.tot.get(pid) || 0) + delta));
  // O que conta para o VALOR anda com as físicas: um `+` na grelha é uma cópia
  // da Coleção, e as próprias dos decks (que é o que o `qty_valor` desconta)
  // não mexem por aqui.
  state.valNorm.set(pid, Math.max(0, (state.valNorm.get(pid) || 0) + delta));
  // O `+`/`-` mexe nos binders de COLEÇÃO — é a grelha da Coleção. As cópias
  // que estão num deck ou no binder Decks/Venda não mexem daqui.
  const locs = (state.locs.get(pid) || []).slice();
  const i = locs.findIndex(x => x.loc === 'colecao');
  if (i >= 0) locs[i] = { ...locs[i], qty: Math.max(0, locs[i].qty + delta) };
  else if (delta > 0) locs.unshift({ loc: 'colecao', label: 'Coleção', qty: delta });
  state.locs.set(pid, locs.filter(x => x.qty > 0));
  const play = state.play.get(ck);
  if (play) play.owned = Math.max(0, play.owned + delta);
  refreshTiles(pid, ck);
}

async function adjust(pid, delta) {
  if (!state.editable) return;
  if (delta < 0 && (state.qty.get(pid) || 0) <= 0) return;

  const ck = state.meta.get(pid)?.card_key;
  applyLocal(pid, delta);                       // otimista: o ecrã anda já
  state.pending.set(ck, (state.pending.get(ck) || 0) + 1);

  // Cada clique vai como um DELTA com id próprio. Sem debounce: é o servidor
  // que soma dentro de uma transação, por isso cliques rápidos seguidos não
  // se perdem, e um retry com o mesmo request_id não conta a dobrar.
  const requestId = (crypto.randomUUID ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`);

  try {
    const r = await fetch('api/adjust', {
      method: 'POST',
      headers: cabecalhos(),
      body: JSON.stringify({ printing_id: pid, delta, request_id: requestId }),
    });
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error || `HTTP ${r.status}`);
    const res = await r.json();

    // Só aceitamos o valor do servidor quando não há mais nada em voo para
    // esta carta — senão uma resposta atrasada punha o contador para trás.
    const left = (state.pending.get(ck) || 1) - 1;
    state.pending.set(ck, left);
    if (left === 0) {
      // `res.qty` é o total FÍSICO; a grelha da Coleção mostra o `qty_colecao`.
      state.qty.set(pid, res.qty_colecao != null ? res.qty_colecao : res.qty);
      if (res.qty != null) state.tot.set(pid, res.qty);
      if (res.foil != null) state.foil.set(pid, res.foil);
      if (res.locations) state.locs.set(pid, res.locations);
      if (res.playset) state.play.set(ck, { owned: res.playset.owned, target: res.playset.target });
      refreshTiles(pid, ck);
    }
    if (res.op_id) toastUndo(pid, delta, res.op_id);
    wlDesatualizar();
    runaMexeu(ck);
    // O separador «Encomendas» mostra o mesmo `qty`: relê-se quando ele lá for.
    state.enc.payload = null;
  } catch (err) {
    state.pending.set(ck, Math.max(0, (state.pending.get(ck) || 1) - 1));
    applyLocal(pid, -delta);                    // falhou: reverte e avisa
    toast(`Não gravou: ${err.message}`, { error: true });
  }
}

async function undo(opId, pid, delta) {
  try {
    const r = await fetch('api/undo', {
      method: 'POST',
      headers: cabecalhos(),
      body: JSON.stringify({ op_id: opId }),
    });
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error || `HTTP ${r.status}`);
    const res = await r.json();
    state.qty.set(pid, res.qty_colecao != null ? res.qty_colecao : res.qty);
    if (res.qty != null) state.tot.set(pid, res.qty);
    if (res.foil != null) state.foil.set(pid, res.foil);
    if (res.locations) state.locs.set(pid, res.locations);
    const ck = state.meta.get(pid)?.card_key;
    if (res.playset) state.play.set(ck, { owned: res.playset.owned, target: res.playset.target });
    refreshTiles(pid, ck);
    wlDesatualizar();
    runaMexeu(ck);
    state.enc.payload = null;
  } catch (err) {
    toast(`Não deu para anular: ${err.message}`, { error: true });
  }
}

/* ------------------------------------------------------------------ toasts */

function toast(msg, { error = false, action = null, ms = 4000 } = {}) {
  const el = document.createElement('div');
  el.className = 'toast' + (error ? ' err' : '');
  el.innerHTML = `<span>${escapeHTML(msg)}</span>`;
  if (action) {
    const b = document.createElement('button');
    b.textContent = action.label;
    b.onclick = () => { el.remove(); action.run(); };
    el.appendChild(b);
  }
  $('#toasts').appendChild(el);
  setTimeout(() => el.remove(), ms);
  // Nunca mais do que 3 no ecrã ao mesmo tempo.
  const all = $('#toasts').children;
  while (all.length > 3) all[0].remove();
}

function toastUndo(pid, delta, opId) {
  const name = state.meta.get(pid)?.name || pid;
  toast(`${delta > 0 ? '+' : ''}${delta} ${name}`, {
    ms: UNDO_MS,
    action: { label: 'Anular', run: () => undo(opId, pid, delta) },
  });
}

/* ---------------------------------------------------------------- eventos */

// Imagem local em falta cai para o CDN (e vice-versa no modo publicado).
function imgFallback(e) {
  const img = e.target;
  if (img.tagName !== 'IMG' || !img.dataset.fallback) return;
  img.src = img.dataset.fallback;
  delete img.dataset.fallback;
}

function wireControls() {
  $('#grid').addEventListener('click', (e) => {
    // «+ venda» (2026-09-25): junta uma cópia desta impressão à venda em
    // curso. Não mexe na coleção — ver `venda.py`.
    const vend = e.target.closest('.vd-add');
    if (vend) {
      const t = vend.closest('.tile');
      venderDaGrelha(t.dataset.pid, t.querySelector('.tname')?.textContent || '');
      return;
    }
    const btn = e.target.closest('.step');
    if (!btn) return;
    const tile = btn.closest('.tile');
    // O contador de foil (2026-09-22) é outro par de botões no mesmo tile: o
    // `data-foil` reparte o que ele já tem, o `data-act` mexe no total.
    if (btn.dataset.foil) foilAjustar(tile.dataset.pid, Number(btn.dataset.foil));
    else adjust(tile.dataset.pid, Number(btn.dataset.act));
  });

  // Imagem local em falta cai para o CDN (e vice-versa no modo publicado).
  // Qualquer secção com artes tem de estar nesta lista: uma imagem que o cache
  // local ainda não tivesse aparecia partida e não caía para o CDN.
  for (const alvo of ['#grid', '#deck-body', '#fe-body', '#am-body', '#enc-grid',
                      '#vd-body']) {
    $(alvo).addEventListener('error', imgFallback, true);
  }
  wireEncomendas();

  for (const b of document.querySelectorAll('.seg-btn[data-view]')) {
    b.classList.toggle('is-on', b.dataset.view === state.prefs.view);
    b.onclick = () => {
      state.prefs.view = b.dataset.view; savePrefs();
      document.querySelectorAll('.seg-btn[data-view]').forEach(x => x.classList.toggle('is-on', x === b));
      $('#kind-filter').hidden = state.prefs.view === 'base';
      render();
    };
  }
  $('#kind-filter').hidden = state.prefs.view === 'base';

  for (const b of document.querySelectorAll('.seg-btn[data-state]')) {
    b.classList.toggle('is-on', b.dataset.state === state.prefs.stateFilter);
    b.onclick = () => {
      state.prefs.stateFilter = b.dataset.state; savePrefs();
      document.querySelectorAll('.seg-btn[data-state]').forEach(x => x.classList.toggle('is-on', x === b));
      render();
    };
  }

  for (const cb of document.querySelectorAll('#kind-filter input')) {
    cb.checked = state.prefs.kinds.includes(cb.value);
    cb.onchange = () => {
      state.prefs.kinds = [...document.querySelectorAll('#kind-filter input')]
        .filter(x => x.checked).map(x => x.value);
      savePrefs(); render();
    };
  }

  let t = null;
  $('#search').addEventListener('input', () => { clearTimeout(t); t = setTimeout(render, 160); });
}

/* Desktop: setas navegam na grelha, + e − ajustam o tile em foco. */
function wireKeyboard() {
  document.addEventListener('keydown', (e) => {
    if (e.target.matches('input, textarea')) return;
    // As outras secções só ficam `hidden` — os tiles da Coleção continuam no
    // DOM e o querySelectorAll apanhava-os na mesma. Sem esta guarda, uma seta
    // seguida de `+` na secção Decks somava uma cópia a uma carta que nem
    // sequer estava no ecrã, sem nada a dizer que tinha acontecido.
    // (O id da secção passou a `sec-colecao` no rebrand de 2026-09-24 e esta
    // linha ficou a perguntar por um elemento que já não existe — `null.hidden`
    // rebentava a cada tecla premida fora de um campo de texto.)
    if ($('#sec-colecao').hidden) return;
    const tiles = [...document.querySelectorAll('.tile')];
    if (!tiles.length) return;

    if (e.key === '+' || e.key === '=') { act(1); return; }
    if (e.key === '-' || e.key === '_') { act(-1); return; }
    if (!e.key.startsWith('Arrow')) return;
    e.preventDefault();

    if (state.focus < 0) { setFocus(0, tiles); return; }
    const cur = tiles[state.focus];
    if (e.key === 'ArrowRight') return setFocus(Math.min(state.focus + 1, tiles.length - 1), tiles);
    if (e.key === 'ArrowLeft') return setFocus(Math.max(state.focus - 1, 0), tiles);

    // Cima/baixo por geometria: os grupos ocupam larguras diferentes, por isso
    // contar colunas não chega — procura-se o tile mais próximo na linha acima
    // ou abaixo.
    const r = cur.getBoundingClientRect();
    const dir = e.key === 'ArrowDown' ? 1 : -1;
    let best = -1, bestScore = Infinity;
    tiles.forEach((el, i) => {
      const b = el.getBoundingClientRect();
      const dy = (b.top - r.top) * dir;
      if (dy < r.height * 0.5) return;
      const score = dy * 3 + Math.abs((b.left + b.width / 2) - (r.left + r.width / 2));
      if (score < bestScore) { bestScore = score; best = i; }
    });
    if (best >= 0) setFocus(best, tiles);

    function act(d) {
      if (state.focus < 0) return;
      adjust(tiles[state.focus].dataset.pid, d);
    }
  });
}

function setFocus(i, tiles) {
  tiles.forEach(el => el.classList.remove('focus'));
  state.focus = i;
  tiles[i].classList.add('focus');
  tiles[i].scrollIntoView({ block: 'nearest', behavior: 'smooth' });
}

/* =========================================================== SECÇÃO DECKS

   A alocação vem toda do servidor: os decks são percorridos por ordem de
   prioridade e cada um serve-se do que sobra — do que está sleevado nele, do
   binder Decks/Venda e da Coleção (André, 2026-09-11: «se há na coleção o deck
   usa»). O que um deck não recebe é para COMPRAR, mesmo que exista num deck de
   cima; nesse caso a carta diz onde está («3× em Azir»), como informação.   */

/* O `api/decks.json` é pedido por DUAS secções — os Decks e o painel do Início
   — e é sempre o mesmo ficheiro. Pede-se uma vez só. */
async function garanteDecks() {
  if (state.decks) return state.decks;
  const d = await getJSON('api/decks.json');
  state.decks = d.decks;
  // A ordem escrita no config (`decks.ordem`, 2026-09-21) manda: sem botões
  // de reordenar, senão o clique era desfeito na importação seguinte.
  state.ordemFixa = !!d.ordem_fixa;
  // Só versões base (2026-09-21, `decks.so_base`): diz-se ao lado dos `+`/`−`.
  state.soBase = d.so_base !== false;
  return state.decks;
}

async function loadDecks(sub = '') {
  await garanteDecks();
  renderDeckTabs();
  // A rota do URL (`#decks/ornn`, `#decks/staples`) manda; a seguir, a última
  // escolha. Uma preferência guardada com a aba «Encomendas» (que viveu aqui
  // de 2026-09-11 a 2026-09-17, e passou a separador próprio) ou com a aba
  // «Pool dos decks» (a experiência da manhã de 2026-09-21) cai no 1.º deck —
  // e o mesmo vale para uma vista ESCONDIDA (2026-09-25): quem tinha o «Por
  // deck» guardado abre no primeiro deck, não numa vista que já não existe.
  const ids = deckFaltaIds();
  // A caixa de colar (2026-10-02) é uma vista como as outras — só existe no
  // modo edição, por isso `#decks/colar` no site publicado cai no 1.º deck.
  const podeColar = !!state.editable;
  const daRota = ids.includes(sub) ? sub
    : (podeColar && sub === COLAR_ID) ? COLAR_ID
    : (state.decks.find(x => x.slug === sub) || {}).id;
  const first = daRota
    || (ids.includes(state.prefs.deck)
        || (podeColar && state.prefs.deck === COLAR_ID)
        || state.decks.some(x => x.id === state.prefs.deck)
      ? state.prefs.deck : (state.decks[0] && state.decks[0].id));
  if (first === COLAR_ID) await loadColar();
  else if (ids.includes(first)) await loadDeckFaltas(first);
  else if (first) await loadDeck(first);
  else if (podeColar) await loadColar();   // sem decks, abre onde se entra um
  else {
    $('#deck-head').innerHTML = '';
    $('#deck-body').innerHTML = `<p class="empty">${SEM_DECKS} ${SEM_DECKS_COMO}
      <br>A Coleção dá exactamente os mesmos números que daria se nunca tivesse
      havido decks: nada em uso, nada a comprar aos decks.</p>`;
  }
}

/* ZERO DECKS (2026-09-28): a frase é a MESMA da consola — o `decks.SEM_DECKS`
   e o `SEM_DECKS_COMO` do `decks.py`, e o `tests/test_sem_decks.py` compara as
   duas escritas para não poderem divergir. Não nomeia a razão de HOJE de a
   lista estar vazia — isso é verdade num dia e falso no seguinte; o que não
   muda é o estado e como sair dele. */
const SEM_DECKS = 'Não há decks.';
const SEM_DECKS_COMO = 'Cola a lista na secção Decks, ou mete um .txt em decks/.';

/* O índice dos decks. Era uma FILA de nove botões que, num telemóvel de
   390 px, acabava aos 1042 px — vêem-se três, os outros seis estavam fora do
   ecrã. Passou a índice VERTICAL à esquerda do conteúdo (≥ 900 px) e a um
   `<select>` no telemóvel: cabe tudo, e os nomes já não são cortados.

   Os dois saem da MESMA lista (`itensDoIndice`), para não haver duas ordens
   nem dois rótulos para a mesma coisa. */
function itensDoIndice() {
  const decks = (state.decks || []).map(d => {
    const pct = d.wanted ? Math.round((d.have / d.wanted) * 100) : 0;
    // Membros de um grupo de Legend (2026-09-11, noite) levam «··»: são
    // listas do mesmo deck físico e partilham as cartas.
    const grupo = d.grupo && d.grupo.variantes;
    return {
      grupo: 'Os decks',
      chave: d.slug, on: d.id === state.deckId, ico: 'decks',
      rot: (d.priority === 1 ? '★ ' : '') + (grupo ? '·· ' : '') + d.name,
      titulo: grupo ? `A mesma Legend que ${d.grupo.irmaos.join(', ')}: partilham as cartas` : '',
      // As runas não se contam (2026-09-17, à noite): o «tenho X de N» é sem
      // elas, e a linha diz só quantas há.
      // Um deck DESMONTADO (2026-09-24) não consome nada da Coleção: o índice
      // diz-o em vez da percentagem, que ali seria uma simulação.
      nota: d.montado === false
        ? `desmontado · precisaria de ${d.wanted}`
        : `${pct}% · ${d.have}/${d.wanted}`
          + (d.ordered ? ` · ${d.ordered} a caminho` : '') + runasCurto(d.runas),
      off: d.montado === false,
      accao: () => loadDeck(d.id),
    };
  });
  // Sem decks o grupo «Os decks» desaparecia do índice e lia-se como se se
  // tivesse perdido (2026-09-28). A nota entra AQUI, na lista partilhada, e
  // não em cada um dos dois renderizadores — senão o `<select>` do telemóvel
  // ficava sem ela, que é a divergência que esta lista existe para evitar.
  // `vazio: true` diz «isto é uma frase, não um sítio para onde ir».
  if (state.decks && !state.decks.length) {
    decks.push({ grupo: 'Os decks', chave: '', vazio: true,
                 rot: SEM_DECKS, nota: SEM_DECKS_COMO });
  }
  // A lista «Encomendas» que era o último separador daqui (2026-09-11) passou
  // a separador de topo a 2026-09-17 («tiras esta funcionalidade dos decks»).
  // As abas por deck que viviam no antigo separador «Faltas» até 2026-09-15
  // (Staples, Por deck, Pimp decks): o contador só se sabe depois do
  // `compras.json`.
  // (E as ESCONDIDAS por `abas.escondidas` não entram — 2026-09-25.)
  const listas = deckFaltaTabs().map(t => ({
    grupo: 'Listas de compra',
    chave: t.id, on: state.deckId === t.id, ico: t.id, rot: t.label, titulo: '',
    nota: contadorFalta(t.id) || t.sub,
    accao: () => loadDeckFaltas(t.id),
  }));
  // COLAR UMA LISTA (2026-10-02). Só no modo edição: o site publicado é de
  // leitura e não tem onde gravar. Entra no índice E no `<select>` do
  // telemóvel porque sai desta mesma lista.
  const entrar = state.editable ? [{
    grupo: 'Entrar um deck',
    chave: COLAR_ID, on: state.deckId === COLAR_ID, ico: 'decks',
    rot: 'Colar uma lista', titulo: 'copy-paste de uma decklist',
    nota: 'copy-paste do texto',
    accao: () => loadColar(),
  }] : [];
  return decks.concat(listas, entrar);
}

function renderDeckTabs() {
  const itens = itensDoIndice();
  const nav = $('#deck-tabs');
  nav.innerHTML = '';
  let grupo = null;
  for (const it of itens) {
    if (it.grupo !== grupo) {
      grupo = it.grupo;
      const h = document.createElement('div');
      h.className = 'vgh';
      h.textContent = grupo;
      nav.appendChild(h);
    }
    // Um item `vazio` é uma FRASE, não um botão: não há para onde ir.
    if (it.vazio) {
      const p = document.createElement('p');
      p.className = 'vidx-vazio';
      p.textContent = `${it.rot} ${it.nota}`;
      nav.appendChild(p);
      continue;
    }
    const b = document.createElement('button');
    b.type = 'button';
    b.className = (it.on ? 'is-on' : '') + (it.off ? ' is-off' : '');
    if (it.on) b.setAttribute('aria-current', 'true');
    if (it.titulo) b.title = it.titulo;
    b.innerHTML = `<span class="ic">${ico(it.ico, 16)}</span>`
      + `<span class="vtx">${escapeHTML(it.rot)}<small>${escapeHTML(it.nota)}</small></span>`;
    b.onclick = it.accao;
    nav.appendChild(b);
  }

  // O mesmo índice, no telemóvel. `<optgroup>` para os dois grupos se lerem.
  const sel = $('#deck-sel');
  sel.innerHTML = '';
  let og = null;
  for (const it of itens) {
    if (!og || og.label !== it.grupo) {
      og = document.createElement('optgroup');
      og.label = it.grupo;
      sel.appendChild(og);
    }
    const o = document.createElement('option');
    o.value = it.chave;
    o.textContent = `${it.rot} — ${it.nota}`;
    o.selected = it.on;
    // A frase do «sem decks» aparece, mas não se escolhe.
    if (it.vazio) o.disabled = true;
    og.appendChild(o);
  }
  sel.onchange = () => {
    const it = itensDoIndice().find(x => x.chave === sel.value);
    if (it && it.accao) it.accao();
  };
}

/* «· 12 runas» — as que a lista pede e NÃO se contam (André, 2026-09-17, à
   noite: «indica me so quantas sao e eu organizo isso sozinho a mao»). Vazio
   quando não há runas, ou quando elas contam (`decks.contar_runas: true`). */
function runasCurto(r) {
  if (!runasNaoContadas(r)) return '';
  return ` · ${r.copies} runas`;
}

function runasNaoContadas(r) {
  return !!(r && !r.contadas && r.copies);
}

async function loadDeck(deckId) {
  state.deckId = deckId;
  state.prefs.deck = deckId;
  savePrefs();
  renderDeckTabs();
  if (state.prefs.section === 'decks') escreverHash('decks', deckSubAtual());
  $('#deck-head').innerHTML = '';
  $('#deck-body').innerHTML = '<p class="empty">a carregar…</p>';
  state.deck = await getJSON(`api/deck/${deckId}.json`);
  if (state.deckId !== deckId) return;     // entretanto abriu outro deck
  renderDeck();
}

function renderDeck() {
  const p = state.deck;
  const idx = state.decks.find(d => d.id === p.id) || {};
  const L = p.legality;

  const chip = (ok, txt) => `<span class="chip-l ${ok ? 'ok' : 'bad'}">${txt}</span>`;
  const pct = idx.wanted ? (idx.have / idx.wanted) * 100 : 0;
  // O DECK PRINCIPAL (2026-09-27). Vem em todos os decks; `e_principal` diz
  // se é este. Um payload antigo (o 8770 por relançar) não o traz.
  const pri = p.principal || {};

  $('#deck-head').innerHTML = `
    <div class="deck-card">
      <div class="deck-title">
        <b>${escapeHTML(p.name)}</b>
        ${/* «principal» é o DECK PRINCIPAL (2026-09-27), não a prioridade 1:
              são duas perguntas e tinham a mesma palavra. A prioridade diz
              quem se serve primeiro da Coleção. */ ''}
        ${pri.e_principal ? '<span class="prio pri">DECK PRINCIPAL</span>' : ''}
        <span class="prio">prioridade ${p.priority}</span>
        ${p.montado === false ? '<span class="prio off">desmontado</span>' : ''}
        ${p.grupo && p.grupo.variantes ? `<span class="prio grupo">variante de ${
          escapeHTML(p.grupo.irmaos.map(deckCurto).join(', '))}</span>` : ''}
      </div>
      ${p.montado === false ? `<small class="nota">Este deck está <b>desmontado</b>:
        não está a usar nenhuma cópia da Coleção — não aparece na grelha, não entra
        na falta a comprar nem no «A mais». O que se vê aqui é a <b>simulação</b> de
        o montar a seguir aos que estão montados.</small>` : ''}
      ${p.grupo && p.grupo.variantes ? `<small class="nota">A mesma Legend que
        <b>${escapeHTML(p.grupo.irmaos.join(', '))}</b>: são listas do mesmo deck e
        partilham as cartas — o que falta a uma é a mesma compra da outra
        (<b>${p.grupo.missing}</b> cópias para o grupo, contadas uma vez no total).</small>` : ''}
      <div class="deck-meta">
        <span><i>Legend</i> ${escapeHTML(p.legend || '—')}</span>
        <span><i>Champion</i> ${escapeHTML(p.champion || '—')}</span>
        <span><i>Domínios</i> ${(L.dominios.legend || []).join(' + ') || '—'}</span>
      </div>
      <div class="bar-label"><span>Cartas alocadas a este deck${
        runasNaoContadas(p.runas) ? ' <i class="dim">(sem as runas)</i>' : ''}</span>
        <b>${idx.have || 0}/${idx.wanted || 0}${runasCurto(p.runas)}</b></div>
      <div class="bar"><i style="width:${pct}%"></i></div>
      <div class="chips-l">
        ${chip(L.main.ok, `main ${L.main.n}/${L.main.alvo}`)}
        ${chip(L.runes.ok, `runas ${L.runes.n}/${L.runes.alvo}`)}
        ${chip(L.battlefields.ok, `battlefields ${L.battlefields.n}/${L.battlefields.alvo}`)}
        ${chip(L.max_copies.ok, `máx. ${L.max_copies.alvo} cópias`)}
        ${chip(L.dominios.ok, L.dominios.ok ? 'domínios ok'
          : `${L.dominios.fora.length} fora de domínio`)}
      </div>
      ${p.missing_by_set.length ? `<div class="falta-set">
        <span class="falta-lbl">Falta comprar</span>
        ${p.missing_by_set.map(m => `<span class="fs" title="${m.cards} carta${
          m.cards === 1 ? '' : 's'}${m.multi ? `, ${m.multi} também noutra edição` : ''}">
          ${escapeHTML(m.set)} <b>${m.copies}</b>${m.cents ? ` · ${eur(m.cents)}` : ''}
        </span>`).join('')}
      </div>` : ''}
      ${L.main_inclui_champion
        ? '<small class="nota">O Champion conta para as 40 do main.</small>' : ''}
      ${p.unresolved.length ? `<small class="nota bad">Não casaram no catálogo:
        ${p.unresolved.map(u => escapeHTML(u.name)).join(', ')}</small>` : ''}
      ${principalNota(p, pri)}
      ${deckLocais(p)}
      <div class="deck-actions">
        ${state.editable ? `<button class="btn ${pri.e_principal ? '' : 'primaria'}"
          data-act="${pri.e_principal ? 'despromover' : 'tornar-principal'}">${
          pri.e_principal ? 'Deixar de ser o deck principal' : 'Tornar DECK PRINCIPAL'}</button>` : ''}
        ${state.editable ? `<button class="btn ${p.montado === false ? 'primaria' : ''}"
          data-act="${p.montado === false ? 'montar' : 'desmontar'}">${
          p.montado === false ? 'Montar este deck' : 'Desmontar'}</button>` : ''}
        ${state.editable && !state.ordemFixa && p.priority !== 1
          ? `<button class="btn" data-act="principal">Passar a prioridade 1</button>` : ''}
        ${state.editable && !state.ordemFixa ? `<button class="btn" data-act="subir">Subir</button>
          <button class="btn" data-act="descer">Descer</button>` : ''}
        <button class="btn" data-act="csv">Lista de compras (CSV)</button>
        ${/* APAGAR A LISTA (2026-10-02): o par da caixa de colar. Quem mete
              uma lista pela janela tem de poder tirá-la por lá — era a última
              coisa que ainda obrigava a ir à pasta à mão. NÃO apaga cópias:
              as próprias do deck ficam no `proprio:<slug>`. */ ''}
        ${state.editable
          ? '<button class="btn perigo" data-act="apagar-lista">Apagar a lista</button>' : ''}
        ${state.editable && state.ordemFixa
          ? '<small class="nota">A ordem dos decks está no <code>riftvault_config.json</code> (<code>decks.ordem</code>) — muda-se lá.</small>' : ''}
      </div>
    </div>`;

  // O Rune Pool não se conta (2026-09-17, à noite): o cabeçalho diz só
  // quantas runas a lista pede — «12 · organizas à mão» — em vez de «0/12».
  const cabec = s => {
    const nao = s.nao_contadas || 0;
    if (nao && !s.wanted) return `${nao} · não se contam, organizas à mão`;
    return `${s.have}/${s.wanted}${s.ordered ? ` · ${s.ordered} a caminho` : ''}${
      nao ? ` · ${nao} não contadas` : ''}`;
  };
  const listas = p.sections.map(s => `
    <h2 class="section-head">${s.label}
      <span>${cabec(s)}</span></h2>
    <div class="grid deck-grid">${s.cards.map(deckTile).join('')}</div>`).join('');

  // Depois do deck, o mesmo em falta mas arrumado por edição — é a vista de
  // quem vai comprar, não de quem vai montar.
  const faltas = p.missing_by_set.length ? `
    <h2 class="falta-head">Em falta, por edição</h2>
    ${p.missing_by_set.map(m => `
      <h3 class="section-head sub">${escapeHTML(m.name)}
        <span>${m.copies} cópia${m.copies === 1 ? '' : 's'} de ${m.cards} carta${
          m.cards === 1 ? '' : 's'}${m.cents ? ` · ${eur(m.cents)}` : ''}</span></h3>
      <div class="grid deck-grid">${m.items.map(faltaTile).join('')}</div>`).join('')}` : '';

  // As cópias PRÓPRIAS deste deck que não o servem (2026-09-21): outra
  // versão com `so_base`, uma carta que a lista não pede, ou acima do que
  // pede. Dizem-se com o motivo, em vez de desaparecer.
  const foraP = (p.proprias_fora || []).length ? `
    <h2 class="section-head">Cópias próprias que não servem este deck
      <span>${plural(p.locais.proprias_fora, 'cópia', 'cópias')}</span></h2>
    <p class="note">Estão guardadas para este deck mas a lista não as usa nesta versão:
      deixa-as ficar, ou tira-as com
      <code>riftvault proprias ${escapeHTML(p.slug)} --menos REF</code>.
      Não contam para a Coleção.</p>
    <div class="grid deck-grid">${p.proprias_fora.map(propriaForaTile).join('')}</div>` : '';

  $('#deck-body').innerHTML = principalWantlist(p, pri) + montagemHTML(p)
    + listas + foraP + faltas;

  for (const b of document.querySelectorAll('#deck-head .btn[data-act]')) {
    b.onclick = () => deckAction(b.dataset.act);
  }
  for (const b of document.querySelectorAll('#deck-head .btn[data-loc]')) {
    b.onclick = () => locaisAction(b.dataset.loc);
  }
  // A wantlist do deck principal sai pelo gerador único, como todas as outras.
  if (pri.e_principal && pri.wantlist && pri.wantlist.items.length) {
    cmLigar('pri', () => pri.wantlist.items,
            `riftvault-deck-${p.slug}-${hojeISO()}.csv`);
  }
}

/* O MODO DE REMONTAGEM (André, 2026-09-24): *"vou colocar tudo nos binders das
   edicoes e depois voltar a montar deck a deck e assim conseguir perceber o que
   tenho e nao tenho"*.

   Uma TABELA, não tiles: ele vai percorrê-la com as cartas na mão, e o que
   precisa é de uma linha por carta com quatro números — precisa / próprias /
   no binder ou no deck / da Coleção — e o que falta. Ordenada pelo que FALTA
   primeiro, depois pelo que sai da Coleção (é o que tem de ir buscar) e só no
   fim o que já está. Fechada por omissão (`<details>`), para não empurrar a
   lista de cartas para baixo em quem não está a montar.

   A 375 px a tabela não cabe: abaixo dos 560 px cada linha passa a um cartão
   (o CSS trata disso, `.mont-tab` em modo bloco com `data-label`), e por isso
   cada `<td>` leva o seu rótulo. */
function montagemHTML(p) {
  // Somadas POR CARTA: a lista mostra-se por papel, mas quem está a montar
  // tem a carta na mão uma vez só — 2 Sabotage no main e 1 no sideboard são
  // 3 Sabotage para arranjar, não duas linhas.
  const por = new Map();
  for (const s of p.sections) {
    for (const c of s.cards) {
      if (c.contado === false) continue;
      let e = por.get(c.card_key);
      if (!e) {
        e = { name: c.name, rarity: c.rarity, wanted: 0, proprias: 0, no_deck: 0,
              no_binder: 0, na_colecao: 0, missing: 0, aviso: 0, foil_na_colecao: 0 };
        por.set(c.card_key, e);
      }
      for (const k of ['wanted', 'proprias', 'no_deck', 'no_binder', 'na_colecao',
                       'missing', 'aviso', 'foil_na_colecao']) e[k] += c[k] || 0;
    }
  }
  const cartas = [...por.values()];
  if (!cartas.length) return '';
  cartas.sort((a, b) => (b.missing - a.missing) || ((b.aviso || 0) - (a.aviso || 0))
    || (b.na_colecao - a.na_colecao) || a.name.localeCompare(b.name));
  const faltam = cartas.reduce((s, c) => s + c.missing, 0);
  const daColecao = cartas.reduce((s, c) => s + c.na_colecao, 0);
  const td = (rot, v, cls) => `<td data-l="${rot}"${cls ? ` class="${cls}"` : ''}>${v}</td>`;
  const linhas = cartas.map(c => {
    // `r-` na linha e `m-` nas células, de propósito: com o mesmo nome nos
    // dois, a cor da linha pintava todos os números dela.
    const est = c.missing ? 'falta' : (c.aviso ? 'regra' : 'ok');
    return `<tr class="r-${est}">
      <td data-l="carta" class="m-nome">${escapeHTML(c.name)}${
        c.aviso ? `<span class="m-rar" title="${escapeAttr(
          `${c.aviso} cópia(s) a sair da Coleção e esta carta é ${c.rarity || '?'} — `
          + `pela regra, devia vir das cópias próprias do deck`)}">! ${
          escapeHTML(c.rarity || '')}</span>` : ''}</td>
      ${td('precisa', c.wanted)}
      ${td('próprias', c.proprias || 0, c.proprias ? 'm-prop' : 'm-zero')}
      ${td('deck/binder', (c.no_deck || 0) + (c.no_binder || 0),
        (c.no_deck || c.no_binder) ? '' : 'm-zero')}
      ${td('Coleção', `${c.na_colecao || 0}${c.foil_na_colecao
        ? `<i class="m-foil" title="${escapeAttr(
            `${c.foil_na_colecao} dessas cópias são FOIL — as normais servem `
            + `primeiro, e estas são as que sobraram para foil`)}"> ${
            c.foil_na_colecao} foil</i>` : ''}`,
        c.aviso ? 'm-aviso' : (c.na_colecao ? '' : 'm-zero'))}
      ${td('falta', c.missing || 0, c.missing ? 'm-falta' : 'm-zero')}
    </tr>`;
  }).join('');
  return `<details class="montagem" ${faltam || p.montado === false ? 'open' : ''}>
    <summary>Montar este deck, carta a carta
      <span>${cartas.length} cartas · ${faltam} a arranjar · ${daColecao} da Coleção${
        p.aviso_colecao ? ` · ${p.aviso_colecao} contra a regra` : ''}</span></summary>
    <p class="note">Por esta ordem: primeiro o que falta, depois o que tens de ir
      buscar à Coleção, e no fim o que já está.
      ${p.montado === false ? '<b>O deck está desmontado</b>: os números da Coleção são a simulação de o montares a seguir aos que estão montados. ' : ''}
      ${p.raridade_colecao ? `O <b>!</b> é a regra de raridade: abaixo de
        <b>${escapeHTML(p.raridade_colecao)}</b> a cópia devia ser <b>própria do deck</b>,
        não sair da Coleção.` : ''}
      ${p.foil_na_colecao ? `<b>${plural(p.foil_na_colecao, 'cópia', 'cópias')}</b> de ${
        plural(p.foil_cartas, 'carta', 'cartas')} saem da Coleção <b>em foil</b>: o deck
        joga foil ou normal, tanto faz, mas as <b>normais servem primeiro</b> — estas são
        as que sobraram para foil.` : ''}</p>
    <table class="mont-tab">
      <thead><tr><th>carta</th><th>precisa</th><th>próprias</th><th>deck/binder</th>
        <th>Coleção</th><th>falta</th></tr></thead>
      <tbody>${linhas}</tbody>
    </table>
  </details>`;
}

/* ONDE estão as cartas deste deck. As três primeiras somam o que o deck tem
   e dizem onde ele as vai encontrar — no deck já sleevadas, no binder
   Decks/Venda por ir buscar, ou na Coleção, que desde 2026-09-11 conta («se há
   na coleção o deck usa»). O que falta compra-se; se parte disso existe num
   deck de cima, diz-se quantas («disputadas»), só como informação. */
/* AS DUAS INDICAÇÕES do Deck Principal (André, 2026-09-27): *"No deck aparece
   algo do genero: X cartas em uso da colecao, ainda falta especifica para o
   deck"*. A outra metade é no tile da Coleção (`usoLine`).

   O empréstimo é de APRESENTAÇÃO: a Coleção não perde cópia nenhuma, não muda
   níveis nem valor — *"a Coleção é soberana, não é para mexer"*. O que a linha
   diz é de onde vem cada cópia que o deck está a jogar hoje, e quanto ainda
   falta comprar para ele ficar com as suas. */
function principalNota(p, pri) {
  if (!pri || pri.slug === undefined) return '';
  const usa = pri.em_uso_da_colecao || 0;
  const falta = pri.falta_proprias || 0;
  if (!pri.e_principal) {
    return pri.slug ? `<small class="nota">O deck principal é
      <b>${escapeHTML(pri.name || pri.slug)}</b>${state.editable
        ? ' — a wantlist e a regra da Venda são dele.' : '.'}</small>` : '';
  }
  return `<div class="pri-linha">
    <b>${usa}</b> ${usa === 1 ? 'carta em uso' : 'cartas em uso'} da Coleção${
      pri.cartas_da_colecao ? ` (${plural(pri.cartas_da_colecao, 'carta', 'cartas')} distintas)` : ''},
    ainda ${falta === 1 ? 'falta' : 'faltam'} <b>${falta}</b> específica${
      falta === 1 ? '' : 's'} para o deck${
      pri.falta_cents ? ` · ${eur(pri.falta_cents)}` : ''}.
    <small>As da Coleção continuam da Coleção — estão emprestadas, não saíram de
      lá. As <b>próprias</b> deste deck são ${pri.proprias || 0}.</small>
  </div>`;
}

/* A WANTLIST DO DECK PRINCIPAL: *"todas as cartas do Deck sao Wantlist, as
   comuns e incomuns em Foil"*. É o que falta para o deck ser AUTO-SUFICIENTE —
   o que ainda não está nas cópias próprias dele —, e uma carta marcada com o
   `+` sai daqui. O acabamento é o do contador de foil do tile. */
function principalWantlist(p, pri) {
  const w = pri && pri.wantlist;
  if (!pri || !pri.e_principal || !w) return '';
  const t = w.totals;
  const cab = `<h2 class="section-head">Wantlist do deck principal
    <span>${t.copies} ${t.copies === 1 ? 'cópia' : 'cópias'} de ${
      plural(t.cards, 'carta', 'cartas')}${t.cents ? ` · ${eur(t.cents)}` : ''}</span></h2>`;
  if (!w.items.length) {
    return `${cab}<p class="note">Já tens cópias próprias de tudo o que este deck
      pede. Nada a comprar.</p>`;
  }
  const linhas = w.items.map(x => `<tr class="${x.foil ? 'pri-foil' : ''}">
    <td data-l="falta"><b>${x.missing}</b></td>
    <td data-l="carta">${escapeHTML(x.name)}</td>
    <td data-l="código"><code>${escapeHTML((x.code || '').split('/')[0])}</code></td>
    <td data-l="acabamento">${x.foil
      ? `<span class="foil">foil</span>${x.price !== null && !x.price_is_foil
          ? ' <i class="dim" title="o CardTrader não a tem em foil: conta ao preço da normal">piso</i>' : ''}`
      : '<span class="dim">normal</span>'}</td>
    <td data-l="preço">${x.price === null ? '—' : eur(x.price)}</td>
    <td data-l="total">${x.price === null ? '—' : eur(x.total)}</td>
    <td data-l="da Coleção">${x.na_colecao
      ? `<span class="pri-emprestada">${x.na_colecao} emprestada${x.na_colecao === 1 ? '' : 's'}</span>`
      : ''}</td>
  </tr>`).join('');
  return `${cab}
  <p class="note">O que falta para este deck ser <b>auto-suficiente</b>: tudo o
    que ele pede e ainda não marcaste como <b>cópia própria</b>. As
    <b>comuns e incomuns</b> querem-se em <b>foil</b>; de rara para cima é a
    carta normal (no Riftbound essas já só existem em foil). As que dizem
    «emprestadas» estão a ser jogadas com cópias da Coleção — continuam a
    fazer falta ao deck.${w.runas.copies ? ` As <b>${w.runas.copies}</b> runas
    ficam de fora, como em todos os decks: organizas à mão.` : ''}</p>
  ${t.no_foil_price ? `<p class="note aviso">${plural(t.no_foil_price, 'linha foil conta', 'linhas foil contam')}
    ao preço da <b>normal</b> — o CardTrader não as tem em foil. O total é um
    <b>piso</b>.</p>` : ''}
  ${/* Sem scroll lateral: a 375 px cada linha passa a cartão, como a tabela
        de montagem (o CSS trata disso, com o `data-l` de cada célula). O
        único `overflow-x` do site é o das filas do binder. */ ''}
  <table class="pri-tabela"><thead><tr>
    <th>falta</th><th>carta</th><th>código</th><th>acab.</th>
    <th>preço</th><th>total</th><th>da Coleção</th>
  </tr></thead><tbody>${linhas}</tbody></table>
  <p class="note">O <b>foil não se marca no texto</b> do Cardmarket: lá é um
    filtro por entrada, ligado na interface deles — ${plural(t.foil_cards, 'linha', 'linhas')}
    ${t.foil_cards === 1 ? 'precisa' : 'precisam'} dele.</p>
  ${cmZonaHTML('pri')}`;
}

function deckLocais(p) {
  const l = p.locais || {};
  const chip = (mau, txt) => `<span class="chip-l ${mau ? 'bad' : 'ok'}">${txt}</span>`;
  return `<div class="locais-deck">
    <div class="bar-label"><span>Onde estão as cartas deste deck</span></div>
    <div class="chips-l">
      <span class="chip-l propria">próprias do deck ${l.proprias || 0}</span>
      ${chip(false, `no deck ${l.no_deck || 0}`)}
      ${chip(false, `no binder Decks/Venda ${l.no_binder || 0}`)}
      ${chip(false, `na Coleção ${l.na_colecao || 0}`)}
      ${l.ordered ? `<span class="chip-l caminho">a caminho ${l.ordered}</span>` : ''}
      ${chip(l.missing, `a comprar ${l.missing || 0}`)}
      ${l.shared ? chip(true, `${l.shared} disputadas com um deck de cima`) : ''}
      ${l.outras ? `<span class="chip-l outra">noutra versão ${l.outras}</span>` : ''}
      ${l.extra ? chip(true, `a mais neste deck ${l.extra}`) : ''}
      ${l.proprias_fora ? chip(true, `${l.proprias_fora} próprias que não servem`) : ''}
      ${p.aviso_colecao ? `<span class="chip-l regra" title="${escapeAttr(
        `abaixo de ${p.raridade_colecao} a cópia devia ser própria do deck`)}">${
        p.aviso_colecao} da Coleção que não deviam</span>` : ''}
      ${runasNaoContadas(p.runas) ? `<span class="chip-l neutra">${p.runas.copies} runas à mão</span>` : ''}
    </div>
    ${p.aviso_colecao ? `<small class="nota regra"><b>${p.aviso_colecao}</b> ${
      p.aviso_colecao === 1 ? 'cópia sai' : 'cópias saem'} da Coleção com raridade
      abaixo de <b>${escapeHTML(p.raridade_colecao || '')}</b>, em ${
      plural(p.aviso_cartas, 'carta', 'cartas')}. Pela regra de 2026-09-24, de
      <b>${escapeHTML(p.raridade_colecao || '')}</b> para baixo as cópias dos decks
      deviam ser <b>próprias do deck</b> e a Coleção ficar quieta${
      state.editable ? ` — mete-as com <code>riftvault proprias ${escapeHTML(p.slug)} --mais REF</code>` : ''}. Não bloqueia
      nada: é só um aviso.</small>` : ''}
    <small class="nota">As <b>cópias próprias</b> são as que tens guardadas
      <b>para este deck</b>${state.editable ? ` — a página diz quantas tem cada carta;
      para mudar o número é <code>riftvault proprias ${escapeHTML(p.slug)} --mais/--menos REF</code>` : ''}.
      Servem-no primeiro, só a ele, e <b>não contam para a Coleção</b> (nem para o
      valor); o que elas não taparem vem da Coleção, e o resto é a comprar.${
      p.so_base
        ? ' Só <b>versões base</b>, a Legend e o Champion incluídos (<code>decks.so_base</code>).'
        : ` O deck usa <b>o que está na Coleção, seja que arte for</b>: a base primeiro e,
           no que ela não tapar, outra versão que tenhas — Alt Art, sobrenumerada ou promo
           (nunca assinada). Quando isso acontece a linha da carta diz as versões por arte,
           e o que faltar compra-se na base.`}</small>
    ${runasNaoContadas(p.runas) ? `<small class="nota">As <b>${p.runas.copies}</b> runas
      do Rune Pool não se contam: não entram no tenho, na falta nem na lista de
      compras — a lista diz só quantas são, e organizas as runas à mão.</small>` : ''}
    ${l.shared ? `<small class="nota">Das <b>${l.missing}</b> a comprar,
      <b>${l.shared}</b> existem na Coleção mas um deck de prioridade mais alta
      já as usa — compram-se na mesma.</small>` : ''}
    ${l.outras ? `<small class="nota"><b>${l.outras}</b> ${l.outras === 1 ? 'cópia joga' : 'cópias jogam'}
      noutra versão (Alt Art, sobrenumerada ou promo — nunca assinada) porque a
      base não chega; as cartas repartidas dizem que versões as servem.</small>` : ''}
    ${l.ordered ? `<small class="nota">As <b>${l.ordered}</b> a caminho já estão
      compradas: não contam como tidas até chegarem, e já não estão na lista de
      compras. Quando chegarem, dá-lhes entrada no separador
      <b><a href="#encomendas">Encomendas</a></b>.</small>`
      : (state.editable && l.missing ? `<small class="nota">Compraste alguma?
      Marca-a no separador <b><a href="#encomendas">Encomendas</a></b> — sai da
      lista de compras e fica «a caminho» até lhe dares entrada.</small>` : '')}
    ${l.na_colecao && state.editable && p.montado !== false ? `<small class="nota">As <b>${l.na_colecao}</b>
      da Coleção contam para este deck. Se as sleevares, marca-as para o
      riftvault saber onde estão.</small>` : ''}
    ${l.extra ? `<small class="nota bad">${l.extra} cópias estão marcadas neste
      deck e a lista já não as pede.</small>` : ''}
    ${state.editable ? `<div class="deck-actions">
      ${/* Desmontado, a marcação não faz sentido — o deck não está a tirar
            nada da Coleção, e o `propor_deck` recusa-a (2026-09-24). */ ''}
      ${p.montado === false ? ''
        : '<button class="btn" data-loc="propor">Marcar o que este deck usa…</button>'}
      ${l.no_deck ? '<button class="btn" data-loc="desfazer">Desfazer deck</button>' : ''}
    </div>` : ''}
    <div id="propor-zona"></div>
  </div>`;
}

async function locaisAction(act) {
  if (act === 'propor') return proporDeck();
  if (act === 'desfazer') return desfazerDeck();
}

/* A PROPOSTA. O servidor calcula, o ecrã mostra, e **grava-se só o que ele
   marcar**. Nunca a lista calculada: a 2026-09-09 o mtgvault gravou uma
   alocação inteira de uma vez, com duas cartas que ele tinha dito não ter, e a
   lição foi esta. O «marcar tudo» só liga as checkboxes — visível e
   reversível — e não grava nada por si. */
async function proporDeck() {
  const zona = $('#propor-zona');
  zona.innerHTML = '<p class="empty">a calcular…</p>';
  let p;
  try {
    p = await getJSON(`api/local/propor/${encodeURIComponent(state.deck.slug)}.json`);
  } catch (err) {
    zona.innerHTML = '';
    return toast(`Não deu para calcular: ${err.message}`, { error: true });
  }
  if (!p.items.length) {
    zona.innerHTML = '<p class="empty">Nada do que este deck pede está na Coleção.</p>';
    return;
  }
  zona.innerHTML = `<div class="propor">
    <h3>Estas ${p.copies} cópias estão na Coleção e este deck pede-as.
      <span>Marca as que estão mesmo dentro do deck. Só se grava o que marcares.</span></h3>
    <div class="propor-lista">${p.items.map(proporLinha).join('')}</div>
    <div class="propor-acoes">
      <button class="btn" id="propor-todas">Marcar tudo</button>
      <button class="btn" id="propor-nenhuma">Desmarcar tudo</button>
      <button class="btn primary" id="propor-gravar">Gravar as marcadas (0)</button>
    </div>
    <small class="nota">Cada cópia que mude de sítio deixa uma linha em
      <code>data/locais.log</code>.</small>
  </div>`;

  const caixas = () => [...zona.querySelectorAll('input[type=checkbox]')];
  const contar = () => {
    const n = caixas().filter(c => c.checked)
      .reduce((s, c) => s + Number(c.dataset.qty), 0);
    $('#propor-gravar').textContent = `Gravar as marcadas (${n})`;
    $('#propor-gravar').disabled = n === 0;
  };
  for (const c of caixas()) c.onchange = contar;
  $('#propor-todas').onclick = () => { caixas().forEach(c => { c.checked = true; }); contar(); };
  $('#propor-nenhuma').onclick = () => { caixas().forEach(c => { c.checked = false; }); contar(); };
  $('#propor-gravar').onclick = () => gravarMarcadas(p, caixas());
  contar();
}

function proporLinha(x) {
  const src = state.imageMode === 'remote' ? (x.cdn || x.img) : (x.img || x.cdn);
  return `<label class="propor-item">
    <input type="checkbox" data-pid="${escapeAttr(x.printing_id)}" data-qty="${x.qty}">
    ${src ? `<img src="${src}" alt="" loading="lazy" decoding="async">` : ''}
    <span class="pn"><b>${x.qty}×</b> ${escapeHTML(x.name)}</span>
    <span class="pc">${escapeHTML((x.code || '').split('/')[0])}</span>
    <span class="pl">tens ${x.na_colecao} na Coleção</span>
  </label>`;
}

async function gravarMarcadas(p, caixas) {
  const linhas = caixas.filter(c => c.checked).map(c => ({
    printing_id: c.dataset.pid, qty: Number(c.dataset.qty),
  }));
  // Lista vazia é um erro, não um sucesso silencioso — o servidor recusa na
  // mesma, com 400. Aqui só se evita o pedido.
  if (!linhas.length) return toast('Não marcaste nenhuma.', { error: true });
  const porMarcar = p.items.length - linhas.length;
  if (porMarcar && !confirm(
    `Vais registar ${linhas.length} de ${p.items.length} linhas neste deck.\n`
    + `As outras ${porMarcar} ficam na Coleção, como estão.\n\nGravar?`)) return;
  try {
    const r = await fetch('api/local/marcar', {
      method: 'POST', headers: cabecalhos(),
      body: JSON.stringify({ para: p.para, de: p.de, linhas }),
    });
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error || `HTTP ${r.status}`);
    const res = await r.json();
    toast(`${res.copies} cópias marcadas no deck.`);
    for (const f of res.falhadas || []) toast(`${f.printing_id}: ${f.erro}`, { error: true });
    await recarregarDepoisDeMover();
  } catch (err) {
    toast(`Não gravou: ${err.message}`, { error: true });
  }
}

async function desfazerDeck() {
  if (!confirm(`Desfazer «${state.deck.name}»?\n\n`
    + 'Todas as cópias que estão neste deck passam ao binder Decks/Venda e '
    + 'ficam disponíveis para outro deck. Nada volta à Coleção.')) return;
  try {
    const r = await fetch('api/local/desfazer-deck', {
      method: 'POST', headers: cabecalhos(),
      body: JSON.stringify({ slug: state.deck.slug }),
    });
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error || `HTTP ${r.status}`);
    const res = await r.json();
    toast(`${res.copies} cópias passaram ao binder Decks/Venda.`);
    await recarregarDepoisDeMover();
  } catch (err) {
    toast(`Não deu para desfazer: ${err.message}`, { error: true });
  }
}

/* Mover cópias mexe na Coleção e nos decks todos: as duas leituras vêm dos
   mesmos locais. Recarrega-se o que está no ecrã e marca-se o resto como
   velho. */
async function recarregarDepoisDeMover() {
  state.decks = (await getJSON('api/decks.json')).decks;
  renderDeckTabs();
  await loadDeck(state.deckId);
  if (state.setId) await loadSet(state.setId);
  // Depois do `loadSet`: as wantlists vêm do `wantlist.json`, que não se volta
  // a pedir sozinho — são centenas de KB. Fica marcado como velho, com o botão.
  wlDesatualizar();
  state.compras = null;
  state.enc.payload = null;
}

/* Tile de deck: a mesma linguagem visual da Coleção, mas o que interessa aqui
   é quantas o deck pede e quantas estão de facto alocadas.

   NÃO HÁ `+`/`−` NENHUNS NESTE TILE, e já foram daqui duas famílias:
   - os da ENCOMENDA e o «Chegou», de 2026-09-11 a 2026-09-17 («tiras esta
     funcionalidade dos decks») — vivem nas «Encomendas» e nas «Faltas»;
   - os das CÓPIAS PRÓPRIAS, de 2026-09-21 a 2026-10-01 (*"no deck nao precisa
     + e - / ele ja indica se tem ou nao tem"*) — mexem-se na consola.
   O que fica é a INFORMAÇÃO: o crachá `have/wanted`, «N próprias do deck»,
   «N a caminho», e a moldura azul tracejada quando tudo o que faltava já vem
   a caminho. O `missing` do deck já vem descontado do servidor; aqui só se
   mostra. */
function deckTile(c) {
  const src = state.imageMode === 'remote' ? (c.cdn || c.img) : (c.img || c.cdn);
  const alt = state.imageMode === 'remote' ? (c.img || '') : (c.cdn || '');
  // Uma runa não se conta (2026-09-17, à noite): a carta com o «N×» que a
  // lista pede, moldura neutra, sem crachá tenho/faltam, sem preço — ele
  // organiza-as à mão. Não pode dizer que falta, nem que está ok.
  if (c.contado === false) {
    return `<div class="dtile neutro nao-contada" data-ck="${escapeAttr(c.card_key)}">
      <div class="art${c.landscape ? ' landscape' : ''}">
        ${src ? `<img src="${src}" alt="${escapeAttr(c.name)}" loading="lazy" decoding="async"
           ${alt ? `data-fallback="${escapeAttr(alt)}"` : ''}>` : ''}
        <span class="need">${c.wanted}×</span>
      </div>
      <div class="tname" title="${escapeAttr(c.name)}">${escapeHTML(c.name)}</div>
      ${codeLine(c)}
      <div class="onde tenho">não se conta — organizas à mão</div>
    </div>`;
  }
  // O que falta é para comprar, sempre (2026-09-11). «shared» é só a cor: a
  // falta existe num deck de cima, e a nota diz onde. Com tudo o que falta já
  // a caminho, a moldura fica a azul tracejado — nem tenho, nem falta.
  const st = c.missing ? (c.shared ? 'shared' : 'gone') : (c.ordered ? 'a-caminho' : 'ok');

  // O irmão do grupo (mesma Legend) que também pede esta carta: é a mesma
  // compra, não uma disputa (2026-09-11, noite). Diz-se na linha da falta.
  const irmaos = (c.partilhada || []).map(h => escapeHTML(deckCurto(h.deck))).join(', ');
  let nota = '';
  if (c.missing || c.ordered) {
    const onde = c.missing && c.shared ? ` — ${c.shared.em
      .map(h => `${h.qty}× em «${escapeHTML(deckCurto(h.deck))}»`).join(', ')}` : '';
    const partes = [];
    if (c.missing) partes.push(`falta${c.missing === 1 ? '' : 'm'} ${c.missing} a comprar${onde}`);
    if (c.ordered) partes.push(`<span class="caminho">${c.ordered} a caminho</span>`);
    if (irmaos) partes.push(`<span class="partilhada">partilhada com ${irmaos}</span>`);
    nota = `<div class="onde ${c.missing ? (c.shared ? 'shared' : 'falta') : 'caminho'}">${
      partes.join(' · ')}</div>`;
  } else if (irmaos) {
    nota = `<div class="onde tenho">partilhada com ${irmaos}</div>`;
  } else if (c.no_binder || (c.no_deck && c.na_colecao) || (c.proprias && c.proprias < c.have)) {
    // De onde vem o que tem, quando não vem todo do mesmo sítio. As próprias
    // não entram aqui: têm a linha delas (`propriasLinha`) e diziam-se duas
    // vezes.
    const partes = [];
    if (c.no_deck) partes.push(`${c.no_deck} já no deck`);
    if (c.no_binder) partes.push(`${c.no_binder} por ir buscar ao binder Decks/Venda`);
    if (c.na_colecao) partes.push(`${c.na_colecao} na Coleção`);
    nota = `<div class="onde tenho">${partes.join(' · ')}</div>`;
  } else if (c.printings.length && (c.versoes || []).length <= 1) {
    // Com a linha repartida por versão (abaixo) esta lista dizia o mesmo.
    nota = `<div class="onde tenho">${c.printings
      .map(x => `${x.qty}× ${escapeHTML(x.code || x.id)}`).join(' · ')}</div>`;
  }
  // A Legend e o Champion jogam UMA versão especial — Alt Art, sobrenumerada
  // ou promo, nunca assinada (2026-09-17). A linha diz qual serve (ou qual se
  // compra) e que outras serviam.
  if (c.especial) {
    const e = c.especial;
    const alt = (e.alternativas || []).map(a => escapeHTML((a || '').split('/')[0]));
    nota += `<div class="onde especial">versão especial: ${escapeHTML((e.code || '?').split('/')[0])}${
      e.missing ? ' (a comprar)' : e.ordered ? ' (a caminho)' : ''}${
      alt.length ? ` · ou ${alt.join(', ')}` : ''}</div>`;
  }
  nota += versoesNota(c);
  // A REGRA DE RARIDADE (André, 2026-09-24): esta cópia sai da Coleção e a
  // carta está abaixo do patamar — devia ser uma cópia PRÓPRIA do deck. Só
  // avisa; a alocação é a mesma.
  if (c.aviso) {
    nota += `<div class="onde regra">${c.aviso} da Coleção${
      c.rarity ? ` — é ${escapeHTML(c.rarity)}` : ''}: devia${c.aviso === 1 ? '' : 'm'}
      ser própria${c.aviso === 1 ? '' : 's'} do deck</div>`;
  }

  // A COR DIZ SE ELE TEM (André, 2026-10-01): *"diz as cartas que tens e que
  // nao tens, com imagem com cor e sem cor"*. A cinzento = não tem NENHUMA
  // cópia desta carta; a cores a partir da primeira. Faz-se em CSS
  // (`filter: grayscale(1)`) e não com imagens novas — é a mesma foto, e o
  // cache do browser e o `cdn.riftscribe.gg` continuam a servir uma só.
  // O que vem a caminho conta como «não tem»: ele ainda não a tem na mão.
  const semCor = !c.have ? ' sem-cor' : '';

  return `<div class="dtile ${st}${c.outras ? ' outra-versao' : ''}${
    c.aviso ? ' tem-regra' : ''}" data-ck="${escapeAttr(c.card_key)}">
    <div class="art${c.landscape ? ' landscape' : ''}${semCor}">
      ${src ? `<img src="${src}" alt="${escapeAttr(c.name)}" loading="lazy" decoding="async"
         ${alt ? `data-fallback="${escapeAttr(alt)}"` : ''}>` : ''}
      <span class="need">${c.wanted}×</span>
      <span class="badge">${c.have}/${c.wanted}</span>
    </div>
    <div class="tname" title="${escapeAttr(c.name)}">${escapeHTML(c.name)}</div>
    ${codeLine(c)}
    ${propriasLinha(c)}
    ${nota}
  </div>`;
}

/* QUANTAS CÓPIAS PRÓPRIAS deste deck tem esta carta.
   Teve aqui os `+`/`−` de 2026-09-21 a 2026-10-01 (André, 21/09: «colocas em
   cada deck o + e - para eu dizer se afinal tenho ou nao»). Ele revogou-os com
   a mesma frase ao contrário — *"no deck nao precisa + e - / ele ja indica se
   tem ou nao tem"* —, e por isso o que fica no lugar deles é o NÚMERO, que era
   a informação que estava entre os dois. Mexer nele é na consola
   (`riftvault proprias <slug> --mais/--menos REF`): nada se apagou, o local
   `proprio:<slug>` e a rota continuam lá.
   As próprias NÃO contam para a Coleção (nem para o valor), por isso este
   número não é o crachá — o crachá é `have/wanted`, e as próprias são parte
   do `have`. */
function propriasLinha(c) {
  if (!c.proprias) return '';
  return `<div class="onde propria" title="cópias próprias deste deck — não contam para a Coleção">
    <b>${c.proprias}</b> ${c.proprias === 1 ? 'própria' : 'próprias'} do deck</div>`;
}

/* Uma cópia própria que NÃO serve este deck: a arte, quantas e o motivo.
   Tinha um `−` para a tirar; saiu a 2026-10-01 com os outros botões da página
   do deck. Tira-se na consola — a nota por cima da grelha di-lo. */
function propriaForaTile(x) {
  return `<div class="dtile neutro" data-ck="${escapeAttr(x.card_key || '')}">
    ${artHTML(x, `<span class="need">${x.qty}×</span>`)}
    <div class="tname" title="${escapeAttr(x.name)}">${escapeHTML(x.name)}</div>
    ${codeLine({ code: x.code })}
    <div class="onde shared">${escapeHTML(x.motivo)}</div>
  </div>`;
}

/* O `propriasAjustar` que mandava o delta para `api/proprias/ajustar` viveu
   aqui de 2026-09-21 a 2026-10-01 e saiu com os botões que o chamavam. A ROTA
   e o `riftvault proprias` ficam: as cópias próprias não se apagaram, só
   deixaram de se editar pela página do deck. */

/* «Separa as versões por Art» (André, 2026-09-17): uma linha do deck servida
   por mais do que uma impressão reparte-se, uma sub-linha por versão —
   «2 normal · UNL-176» / «1 Alt Art · UNL-176a». Servida por uma impressão
   só, não se enche o tile: se essa única impressão for OUTRA versão (a base
   não chegou e a alt art tapou tudo), diz-se numa linha corrida. */
function versoesNota(c) {
  const vs = c.versoes || [];
  const cod = x => escapeHTML((x.code || x.id || '?').split('/')[0]);
  let out = '';
  if (vs.length > 1) {
    out = `<div class="onde versoes">${vs.map(x =>
      `<span class="${x.lugar === 'outra' ? 'outra' : ''}">${x.qty} ${escapeHTML(x.label)} · ${cod(x)}</span>`
    ).join('')}</div>`;
  } else if (vs.length === 1 && c.outras) {
    out = `<div class="onde versoes"><span class="outra">em ${escapeHTML(vs[0].label)} · ${cod(vs[0])}</span></div>`;
  }
  return out + edicoesNota(c) + tapadaNota(c);
}

/* AS DUAS EDIÇÕES (André, 2026-10-01): *"se houver em duas edicoes diferentes,
   conta as 2, seleciona a que cobrir o numero necessario, **caso nao consiga,
   indica que e x de uma edicao e x de outra**"*.

   Quem escolhe é o `decks.por_cobertura`, que põe à frente a edição que cobre
   sozinha; esta linha é a segunda metade — a que só aparece quando NENHUMA
   cobriu e a linha ficou mesmo repartida por edições. Com uma edição só não
   escreve nada: o código da carta já a diz. */
function edicoesNota(c) {
  const por = new Map();
  for (const x of (c.versoes || [])) {
    if (!x.set) continue;
    por.set(x.set, (por.get(x.set) || 0) + x.qty);
  }
  if (por.size < 2) return '';
  return `<div class="onde edicoes" title="nenhuma edição cobria sozinha as ${c.wanted} — tens de ir a duas">${
    [...por].map(([s, n]) => `${n} de ${escapeHTML(s)}`).join(' + ')}</div>`;
}

/* COM O QUE SE TAPOU (André, 2026-10-01): *"Se nao houver versao normal, ele
   avisa que sao X normais e X Alt Art / Overnumbered ou o que quer que seja"*.
   A conta por ARTE, numa frase — as sub-linhas de cima dizem-no por impressão,
   e numa carta servida por três impressões isso lê-se mal. Só sai quando
   alguma cópia veio de outra versão por a base não ter chegado. */
function tapadaNota(c) {
  if (!c.outras) return '';
  const por = new Map();
  for (const x of (c.versoes || [])) {
    if (x.lugar === 'especial') continue;
    const k = x.lugar === 'outra' ? (x.label || 'outra') : 'normal';
    por.set(k, (por.get(k) || 0) + x.qty);
  }
  if (!por.size) return '';
  return `<div class="onde tapada">${c.have} — ${[...por]
    .map(([k, n]) => `${n} ${escapeHTML(k)}`).join(', ')}</div>`;
}

/* Edição + número + preço, em texto legível. É por aqui que ele procura a
   carta na caixa ou na loja — no canto da imagem era pequeno de mais. */
function codeLine(x) {
  if (!x.code && x.price == null) return '';
  const cod = x.code ? escapeHTML(x.code.split('/')[0]) : '';
  const pr = x.price != null ? eur(x.price) : '';
  return `<div class="codigo">${cod}${cod && pr ? ' · ' : ''}${pr}</div>`;
}

/* Tile de compra: a carta que falta, na edição onde sai mais barata. */
function faltaTile(x) {
  const src = state.imageMode === 'remote' ? (x.cdn || x.img) : (x.img || x.cdn);
  const alt = state.imageMode === 'remote' ? (x.img || '') : (x.cdn || '');
  return `<div class="dtile gone">
    <div class="art${x.landscape ? ' landscape' : ''}">
      ${src ? `<img src="${src}" alt="${escapeAttr(x.name)}" loading="lazy" decoding="async"
         ${alt ? `data-fallback="${escapeAttr(alt)}"` : ''}>` : ''}
      <span class="need">${x.qty}×</span>
      ${x.price != null ? `<span class="price">${eurShort(x.total)}</span>` : ''}
    </div>
    <div class="tname" title="${escapeAttr(x.name)}">${escapeHTML(x.name)}</div>
    ${codeLine(x)}
    ${especialNota(x)}
    ${(x.also || []).length ? `<div class="onde tenho">também em ${x.also.join(', ')}</div>` : ''}
  </div>`;
}

/* A linha de compra que é a VERSÃO ESPECIAL da Legend/Champion (2026-09-17):
   diz que o é, e que outras versões especiais serviam na mesma — qualquer
   uma serve, a lista aponta à mais barata. */
function especialNota(x) {
  if (!x.especial) return '';
  const alt = (x.alternativas || []).map(a =>
    `${escapeHTML((a.code || '').split('/')[0])}${a.price != null ? ` ${eur(a.price)}` : ''}`);
  return `<div class="onde especial">versão especial (Legend/Champion)${
    alt.length ? ` · ou ${alt.join(', ')}` : ''}</div>`;
}

async function deckAction(act) {
  if (act === 'csv') return exportCSV();
  if (act === 'montar' || act === 'desmontar') return montarDeck(act === 'montar');
  if (act === 'tornar-principal') return definirPrincipal(state.deck.slug);
  if (act === 'despromover') return definirPrincipal(null);
  if (act === 'apagar-lista') return apagarLista();
  const ids = state.decks.map(d => d.id);
  const i = ids.indexOf(state.deckId);
  let novo = ids.slice();
  if (act === 'principal') { novo.splice(i, 1); novo.unshift(state.deckId); }
  if (act === 'subir' && i > 0) { [novo[i - 1], novo[i]] = [novo[i], novo[i - 1]]; }
  if (act === 'descer' && i < ids.length - 1) { [novo[i + 1], novo[i]] = [novo[i], novo[i + 1]]; }
  try {
    const r = await fetch('api/decks/order', {
      method: 'POST', headers: cabecalhos(),
      body: JSON.stringify({ ids: novo }),
    });
    // O servidor diz porquê (409 com a ordem no config) — mostra-se a razão,
    // não o número.
    const body = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(body.error || `HTTP ${r.status}`);
    state.decks = body.decks;
    renderDeckTabs();
    await loadDeck(state.deckId);   // a alocação mudou para toda a gente
    toast('Ordem alterada — a alocação foi refeita.');
  } catch (err) {
    toast(`Não deu para reordenar: ${err.message}`, { error: true });
  }
}

/* APAGAR A LISTA de um deck (2026-10-02) — o par da caixa de colar.
   NÃO apaga cópias: as próprias do deck ficam gravadas no `proprio:<slug>`,
   fora da Coleção, como já acontecia a um deck cujo `.txt` desaparecia. É por
   isso que a pergunta fala da LISTA e não do deck. */
async function apagarLista() {
  const p = state.deck;
  if (!p) return;
  if (!confirm(`Apagar a lista «${p.name}»?\n\n`
    + 'O deck deixa de existir e a Coleção volta a dar os números que daria se '
    + 'ele nunca tivesse havido. As cópias NÃO se apagam — as próprias deste '
    + 'deck continuam guardadas.')) return;
  try {
    const r = await fetch('api/decks/apagar', {
      method: 'POST', headers: cabecalhos(),
      body: JSON.stringify({ slug: p.slug, confirmar: true }),
    });
    const body = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(body.error || `HTTP ${r.status}`);
    state.decks = body.decks;
    state.compras = null;
    state.aMais = null;
    state.colecaoVelha = true;
    state.deckId = null;
    state.prefs.deck = null;
    savePrefs();
    toast(`A lista «${p.name}» foi apagada.`);
    await loadDecks();
  } catch (err) {
    toast(`Não deu para apagar: ${err.message}`, { error: true });
  }
}

/* O DECK PRINCIPAL (André, 2026-09-27). Escreve `decks.principal` no config,
   como o montar/desmontar escreve o `decks.montados`.

   O deck que SAI é despromovido: as cópias próprias dele que valham pelo menos
   0,50 € ganham uma linha na Venda, marcada com a origem. **Entrar na Venda
   não é vender** — nada saiu do deck e nada baixou —, e as de menos de 0,50 €
   continuam próprias. O toast diz as duas metades. */
async function definirPrincipal(slug) {
  try {
    const r = await fetch('api/decks/principal', {
      method: 'POST', headers: cabecalhos(),
      body: JSON.stringify({ slug }),
    });
    const body = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(body.error || `HTTP ${r.status}`);
    state.decks = body.decks;
    state.colecaoVelha = true;
    state.compras = null;
    state.aMais = null;
    state.venda = null;
    renderDeckTabs();
    await loadDeck(state.deckId);
    const mov = body.movimento;
    let msg = slug
      ? `«${body.estado.name}» passou a ser o DECK PRINCIPAL.`
      : 'Já não há deck principal.';
    if (mov) {
      const a = mov.para_a_venda, b = mov.ficam;
      msg += ` ${a.copies} ${a.copies === 1 ? 'cópia própria foi' : 'cópias próprias foram'}`
        + ` para a Venda (${eur(a.cents)})`
        + (b.copies ? `; ${b.copies} abaixo de ${eur(mov.minimo_cents)} ficaram no deck.` : '.');
    }
    toast(msg);
  } catch (err) {
    toast(`Não deu para mudar o deck principal: ${err.message}`, { error: true });
  }
}

/* MONTAR / DESMONTAR (André, 2026-09-24). Escreve `decks.montados` no
   `riftvault_config.json` (o estado é de lá, «para não se perder») e refaz a
   alocação de toda a gente: desmontar liberta o que o deck estava a usar da
   Coleção, montar volta a prendê-lo. Por isso a Coleção, o A mais, as
   Encomendas e as listas de compra ficam por reler. */
async function montarDeck(montado) {
  const p = state.deck;
  try {
    const r = await fetch('api/decks/montar', {
      method: 'POST', headers: cabecalhos(),
      body: JSON.stringify({ slug: p.slug, montado }),
    });
    const body = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(body.error || `HTTP ${r.status}`);
    state.decks = body.decks;
    state.colecaoVelha = true;
    state.compras = null;
    state.aMais = null;
    state.enc.payload = null;
    state.venda = null;
    renderDeckTabs();
    await loadDeck(state.deckId);
    let msg = montado
      ? `«${p.name}» montado — volta a servir-se da Coleção.`
      : `«${p.name}» desmontado — deixou de usar a Coleção.`;
    // Desmontar o DECK PRINCIPAL despromove-o (2026-09-27), e as cópias
    // próprias dele que valham o mínimo passam a linhas da Venda.
    if (body.movimento) {
      const a = body.movimento.para_a_venda, b = body.movimento.ficam;
      msg += ` Já não é o deck principal: ${a.copies} `
        + `${a.copies === 1 ? 'cópia própria foi' : 'cópias próprias foram'} para a `
        + `Venda (${eur(a.cents)})`
        + (b.copies ? `; ${b.copies} abaixo de ${eur(body.movimento.minimo_cents)} ficaram.` : '.');
    }
    toast(msg);
  } catch (err) {
    toast(`Não deu para ${montado ? 'montar' : 'desmontar'}: ${err.message}`, { error: true });
  }
}

function exportCSV() {
  const p = state.deck;
  const linhas = [['seccao', 'carta', 'pedidas', 'tenho', 'proprias', 'faltam', 'onde_estao']];
  for (const s of p.sections) {
    for (const c of s.cards) {
      // Uma runa não se conta — nem falta, nem entra na lista de compras.
      if (!c.missing || c.contado === false) continue;
      linhas.push([s.label, c.name, c.wanted, c.have, c.proprias || 0, c.missing,
        c.shared ? c.shared.em.map(h => `${h.qty}x ${h.deck}`).join(' | ') : '']);
    }
  }
  const csv = linhas.map(r => r.map(v =>
    `"${String(v).replace(/"/g, '""')}"`).join(',')).join('\r\n');
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8' }));
  a.download = `${p.slug}-faltas.csv`;
  a.click();
  URL.revokeObjectURL(a.href);
}

/* ================================================ SEPARADOR «ENCOMENDAS»

   André, 2026-09-17: *"que cries uma aba 'encomendas', em que é igual à
   coleção, mas só tem de Raras para cima, e nas quais eu coloco o que comprei
   (para não me perder), e assim que chegam, eu coloco lá que chegaram, e
   acrescentas à coleção"* / *"e tiras esta funcionalidade dos decks"*.

   É A GRELHA DA COLEÇÃO — as mesmas edições nos separadores, os mesmos blocos,
   os mesmos tiles com imagem, a mesma ordem, tenha ele a carta ou não —
   cortada a Rara para cima pelo servidor (`pending.grelha`,
   `api/encomendas/<ID>.json`). O que muda nos tiles são os botões: o `+`/`−`
   aqui é o que ele COMPROU E AINDA NÃO CHEGOU (a `pending`, por impressão —
   ele escolhe a versão no próprio tile) e o «Chegou (N)» dá entrada dessa
   impressão na Coleção. O crachá continua a ser o da Coleção (`q/alvo`):
   encomendar não é ter. O resumo de tudo o que está a caminho vem do
   `api/encomendas.json` (é o que a CLI lê), para os separadores e o cabeçalho.

   Os `+`/`−` e o «Chegou» viveram nos tiles dos decks de 2026-09-11 a
   2026-09-17; lá ficou só a informação «N a caminho».                     */

async function loadEncomendas(setId = null) {
  const sets = state.index?.sets || [];
  if (!setId) {
    setId = sets.some(s => s.id === state.prefs.encSet) ? state.prefs.encSet
      : (state.enc.setId || edicaoAberta() || (sets[0] && sets[0].id));
  }
  if (!setId) return;
  state.enc.setId = setId;
  state.prefs.encSet = setId;
  savePrefs();
  if (state.prefs.section === 'encomendas') escreverHash('encomendas', setId);
  renderEncTabs();
  $('#enc-grid').innerHTML = '<p class="empty">a carregar…</p>';
  // O resumo é pequeno e é o que os separadores mostram («N a caminho» por
  // edição); a grelha é da edição aberta. Os dois em paralelo.
  const [resumo, p] = await Promise.all([
    state.enc.resumo ? Promise.resolve(state.enc.resumo) : getJSON('api/encomendas.json'),
    getJSON(`api/encomendas/${setId}.json`),
  ]);
  state.enc.resumo = resumo;
  state.enc.payload = p;
  state.enc.ordered.clear(); state.enc.qty.clear();
  for (const g of p.groups) {
    for (const pr of g.printings) {
      state.enc.ordered.set(pr.id, pr.ordered || 0);
      state.enc.qty.set(pr.id, pr.qty || 0);
    }
  }
  renderEncTabs();
  renderEncomendas();
}

/* Os separadores por edição: os da Coleção, com «N a caminho» por baixo. */
function renderEncTabs() {
  const nav = $('#enc-tabs');
  nav.innerHTML = '';
  const porSet = new Map();
  for (const g of (state.enc.resumo?.a_caminho || [])) porSet.set(g.set, g.copies);
  for (const s of (state.index?.sets || [])) {
    const b = document.createElement('button');
    const on = s.id === state.enc.setId;
    b.className = 'tab' + (on ? ' is-on' : '');
    b.setAttribute('aria-pressed', on ? 'true' : 'false');
    const n = porSet.get(s.id) || 0;
    b.innerHTML = `${escapeHTML(s.name)}<small>${n ? `${n} a caminho` : 'nada a caminho'}</small>`;
    b.onclick = () => loadEncomendas(s.id);
    nav.appendChild(b);
  }
}

/* Os nomes das raridades como ele lhes chama. A `showcase` não é raridade de
   jogo — é o tratamento das reimpressões de topo do OGN e do SFD — e fica com
   o nome do catálogo; a `epic` é a «mítica» — a raridade de topo. */
const RARIDADE_PT = { common: 'comum', uncommon: 'incomum', rare: 'rara',
                      epic: 'mítica', showcase: 'showcase' };
function rarityLabel(r) { return RARIDADE_PT[r] || r || '?'; }

function encEstado(pid, t) {
  const q = state.enc.qty.get(pid) || 0;
  if (t <= 0) return q > 0 ? 'done' : 'none';
  if (q <= 0) return 'none';
  return q >= t ? 'done' : 'partial';
}

/* O cabeçalho: o total a caminho (todas as edições), o «Chegou tudo», o que
   esta edição mostra, e o que vem a caminho desta edição FORA da grelha (uma
   comum encomendada pela CLI, uma runa do CardTrader) — com o «Chegou» de
   cada uma, para não haver encomenda sem sítio onde se lhe dê entrada. */
function renderEncHead() {
  const p = state.enc.payload;
  const r = state.enc.resumo || { totals: { copies: 0, printings: 0, cents: 0, sem_preco: 0, paid: 0 } };
  const t = r.totals;
  const aqui = [...state.enc.ordered.values()].reduce((s, n) => s + n, 0);
  const aquiImp = [...state.enc.ordered.values()].filter(n => n > 0).length;
  const fora = p.fora || [];
  const foraN = fora.reduce((s, x) => s + x.qty, 0);
  const raridades = (p.rarities || []).map(x => escapeHTML(rarityLabel(x))).join(', ');

  $('#enc-head').innerHTML = `<div class="deck-card">
    <div class="deck-title"><b>Encomendas</b>
      <span class="prio">${t.copies ? `${plural(t.copies, 'cópia', 'cópias')} a caminho · ${
        plural(t.printings, 'impressão', 'impressões')}${
        t.cents ? ` · ${eur(t.cents)} ao preço de hoje` : ''}${
        t.sem_preco ? ` (${t.sem_preco} sem preço)` : ''}${
        t.paid ? ` · pagaste ${eur(t.paid)}` : ''}` : 'nada a caminho'}</span></div>
    <div class="deck-meta">
      <span><i>${escapeHTML(p.set.name)}</i>${plural(p.totals.printings, 'impressão', 'impressões')} de ${
        escapeHTML(rarityLabel(p.rarity_min))} para cima (${raridades}) — ${
        p.totals.printings_colecao} na Coleção</span>
      <span><i>A caminho nesta edição</i>${aqui ? `${plural(aqui, 'cópia', 'cópias')} em ${
        plural(aquiImp, 'impressão', 'impressões')}` : 'nada'}${
        foraN ? ` · <b>${foraN}</b> fora desta grelha` : ''}</span>
    </div>
    <small class="nota">O que compraste e ainda não chegou. <b>Não conta na Coleção</b>
      — o crachá de cada carta continua a ser o que tens na caixa — mas já saiu
      das listas de compra e das wantlists. O <b>+</b> marca mais uma cópia
      comprada desta versão; o <b>−</b> tira-a; <b>Chegou</b> dá-lhe entrada na
      Coleção. A grelha é a da Coleção, de ${escapeHTML(rarityLabel(p.rarity_min))}
      para cima, tenhas a carta ou não.</small>
    ${fora.length ? `<div class="enc-fora">
      <b>A caminho nesta edição, fora da grelha</b> (abaixo de ${
        escapeHTML(rarityLabel(p.rarity_min))}, fora do catálogo da RiftScribe,
      ou <i class="foil">foils</i> — que são todas comuns e incomuns e por isso
      nunca cabem nesta grelha):
      ${fora.map(x => `<span class="enc-fora-item${x.foil ? ' foil' : ''}">${x.qty}× ${
        escapeHTML(x.name || x.printing_id)}
        <i>${escapeHTML((x.code || '').split('/')[0])}${x.foil ? ' · FOIL' : ''}${
        x.market_only ? ' · fora do catálogo' : ''}</i>
        ${state.editable ? `<button class="btn chegou mini" data-chegou-pid="${escapeAttr(x.printing_id)}"
          data-chegou-foil="${x.foil ? '1' : '0'}"
          title="dar entrada na Coleção${x.foil ? ', no contador de foil' : ''}">Chegou</button>` : ''}</span>`).join('')}
    </div>` : ''}
    ${state.editable && t.copies ? `<div class="deck-actions">
      <button class="btn" id="enc-chegou-tudo">Chegou tudo (${plural(t.copies, 'cópia', 'cópias')}, todas as edições)</button>
    </div>` : ''}
  </div>`;

  for (const b of document.querySelectorAll('#enc-head [data-chegou-pid]')) {
    b.onclick = () => encChegou(b.dataset.chegouPid, b,
                                b.dataset.chegouFoil === '1');
  }
  const tudo = $('#enc-chegou-tudo');
  if (tudo) tudo.onclick = () => encChegouTudo(tudo);
}

/* A grelha: os mesmos dois ciclos do `render()` da Coleção — uma vez por
   bloco, depois os grupos por número de coleção. O contador de cada bloco diz
   o que vem a caminho. */
function renderEncomendas() {
  const p = state.enc.payload;
  if (!p) return;
  renderEncHead();
  const grid = $('#enc-grid');
  const parts = [];
  const term = ($('#enc-search').value || '').trim().toLowerCase();
  const filtro = state.prefs.encFilter;
  let mostrados = 0, tiles = 0;

  for (const b of (p.blocks || [{ id: 'master', label: null, counts: true }])) {
    const pedacos = [];
    let aCaminho = 0, comAlguma = 0, total = 0;
    for (const g of p.groups) {
      let list = g.printings.filter(pr => (pr.block || 'master') === b.id);
      if (term) {
        const hay = `${g.name} ${g.printings.map(pr => pr.code || '').join(' ')}`.toLowerCase();
        if (!hay.includes(term)) list = [];
      }
      if (filtro === 'ordered') list = list.filter(pr => (state.enc.ordered.get(pr.id) || 0) > 0);
      if (filtro === 'missing') list = list.filter(pr => encEstado(pr.id, pr.target || 0) !== 'done');
      if (!list.length) continue;
      for (const pr of list) {
        total++;
        const n = state.enc.ordered.get(pr.id) || 0;
        if (n) { aCaminho += n; comAlguma++; }
      }
      const inner = list.map((pr, i) => { tiles++; return encTile(g, pr, i === 0); }).join('');
      pedacos.push(list.length > 1
        ? `<div class="group multi" style="--span:${list.length}">${inner}</div>`
        : `<div class="group">${inner}</div>`);
    }
    if (!pedacos.length) continue;
    mostrados++;
    if (b.label) {
      parts.push(`<h2 class="section-head ${b.counts ? 'cauda' : 'fora'}">${escapeHTML(b.label)}
        <span>${aCaminho ? `<b>${aCaminho}</b> a caminho em <b>${comAlguma}</b> de ${total}`
          : `nada a caminho nas ${total}`} impressões</span></h2>`);
    }
    parts.push(pedacos.join(''));
  }

  grid.innerHTML = parts.join('');
  $('#enc-empty').hidden = mostrados > 0;
  $('#enc-count').textContent = `${tiles} impressões a mostrar · ${p.totals.cards} cartas de ${
    rarityLabel(p.rarity_min)} para cima nesta edição`;
  ligarEnc();
}

/* O tile: o da Coleção (`tileHTML`), com os botões da encomenda no lugar dos
   `+`/`−` das cópias. A moldura azul tracejada e a linha «N a caminho» são as
   mesmas que os decks e as Faltas já usam para o que vem a caminho. */
function encTile(g, p, comUso = false) {
  const q = state.enc.qty.get(p.id) || 0;
  const t = p.target || 0;
  const n = state.enc.ordered.get(p.id) || 0;
  const st = encEstado(p.id, t);
  const play = g.playset || { owned: 0, target: 0 };
  const badge = t > 0 ? `${q}/${t}` : `${q}`;
  const alt = imgAlt(p);
  return `<div class="tile enc ${st}${n ? ' a-caminho' : ''}" data-pid="${escapeAttr(p.id)}" data-ck="${escapeAttr(g.card_key)}">
    <div class="art${p.landscape ? ' landscape' : ''}">
      <img src="${imgSrc(p)}" alt="${escapeAttr(p.name)}" loading="lazy" decoding="async"
           ${alt ? `data-fallback="${escapeAttr(alt)}"` : ''}>
      <span class="label ${p.kind}">${p.label}</span>
      ${p.price != null && p.price >= (state.enc.payload.price_badge_min || 100)
        ? `<span class="price">${eurShort(p.price)}</span>` : ''}
      <span class="cn">${p.code ? escapeHTML(p.code.split('/')[0]) : g.cn}</span>
      <span class="badge">${badge}</span>
      ${n ? `<span class="enc-n" title="${n} a caminho">+${n}</span>` : ''}
    </div>
    <div class="tname" title="${escapeAttr(p.name)}">${escapeHTML(p.name)}</div>
    <div class="steppers enc">
      <button class="step minus" data-enc="-1" ${n ? '' : 'disabled'}
              aria-label="menos uma encomendada de ${escapeAttr(p.name)}"
              title="menos uma a caminho">−</button>
      <button class="step plus" data-enc="1"
              aria-label="mais uma encomendada de ${escapeAttr(p.name)}"
              title="comprei mais uma (fica a caminho)">+</button>
    </div>
    <div class="onde ${n ? 'caminho' : 'tenho'}">${n ? `<b>${n}</b> a caminho` : 'nada a caminho'}${
      p.ordered_foil ? ` · <b>${p.ordered_foil}</b> foil` : ''}${
      p.price != null ? ` · ${eur(p.price)}` : ''}</div>
    ${n ? `<button class="btn chegou" data-chegou-pid="${escapeAttr(p.id)}"
      title="dar entrada na Coleção das ${n} que vêm a caminho">Chegou (${n})</button>` : ''}
    <div class="playset ${play.target > 0 && play.owned >= play.target ? 'is-done' : ''}">
      ${g.is_token ? 'token' : 'jogável'} ${play.owned}/${play.target}</div>
    ${comUso ? usoLine(g) : ''}
  </div>`;
}

/* Os botões de cada tile. Chama-se depois de cada desenho, porque o
   `innerHTML` deita os handlers fora. */
function ligarEnc() {
  for (const b of document.querySelectorAll('#enc-grid .steppers.enc .step')) {
    b.onclick = () => encAjustar(b.closest('.tile').dataset.pid, Number(b.dataset.enc));
  }
  for (const b of document.querySelectorAll('#enc-grid [data-chegou-pid]')) {
    b.onclick = () => encChegou(b.dataset.chegouPid, b);
  }
}

function encRefreshTile(pid) {
  const el = document.querySelector(`#enc-grid .tile[data-pid="${CSS.escape(pid)}"]`);
  if (!el) return;
  const g = state.enc.payload.groups.find(x => x.printings.some(pr => pr.id === pid));
  const pr = g && g.printings.find(x => x.id === pid);
  if (!g) return;
  el.outerHTML = encTile(g, pr, g.printings[0].id === pid);
  ligarEnc();
  renderEncHead();
}

/* O clique no `+`/`−`: ecrã otimista, e os pedidos da MESMA impressão em fila
   — dois cliques rápidos são dois pedidos, nunca um só nem a dobrar. Só o
   último em voo aceita o número do servidor, senão uma resposta atrasada
   punha o contador para trás. Grava na `pending` NESTA impressão. */
async function encAjustar(pid, delta) {
  if (!state.editable) return;
  const n = state.enc.ordered.get(pid) || 0;
  if (delta < 0 && n <= 0) return;
  state.enc.ordered.set(pid, Math.max(0, n + delta));
  encRefreshTile(pid);
  state.enc.voo.set(pid, (state.enc.voo.get(pid) || 0) + 1);
  const fila = state.enc.fila.get(pid) || Promise.resolve();
  const tarefa = fila.then(async () => {
    const r = await fetch('api/encomenda', {
      method: 'POST', headers: cabecalhos(),
      body: JSON.stringify({ printing_id: pid, delta }),
    });
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error || `HTTP ${r.status}`);
    return r.json();
  });
  state.enc.fila.set(pid, tarefa.catch(() => {}));
  try {
    const res = await tarefa;
    const resto = (state.enc.voo.get(pid) || 1) - 1;
    state.enc.voo.set(pid, resto);
    if (resto === 0) {
      state.enc.ordered.set(pid, res.open_printing || 0);
      encRefreshTile(pid);
      // Só o último pedido em voo desta impressão marca o resto como velho
      // — os do meio já não correspondem ao que está no ecrã.
      encMarcaVelhos(false);
    }
    toast(`${res.open_printing} a caminho de ${encNome(pid)}`, { ms: 2500 });
  } catch (err) {
    state.enc.voo.set(pid, Math.max(0, (state.enc.voo.get(pid) || 1) - 1));
    state.enc.ordered.set(pid, Math.max(0, (state.enc.ordered.get(pid) || 0) - delta));
    encRefreshTile(pid);
    toast(`Não gravou: ${err.message}`, { error: true });
  }
}

function encNome(pid) {
  for (const g of state.enc.payload?.groups || []) {
    const pr = g.printings.find(x => x.id === pid);
    if (pr) return pr.name;
  }
  return pid;
}

/* Uma encomenda mudou: as listas de compra e as wantlists descontam o que vem
   a caminho, os decks dizem «N a caminho», a grelha da Coleção também. Das
   páginas grandes nada se pede já — marcam-se como velhas e pedem-se quando
   ele lá voltar. Só o resumo (pequeno) se volta a pedir, para os separadores
   e o cabeçalho dizerem o número certo. Com `chegou`, mexeu a caixa: a
   Coleção, o valor e o «A mais» também. */
function encMarcaVelhos(chegou) {
  state.decks = null;
  state.compras = null;
  state.wantlist = null;
  state.faltasEdicao = null;
  state.colecaoVelha = true;
  wlDesatualizar();
  if (chegou) { state.aMais = null; state.runas = null; }
  encRecalcularResumo();
}

async function encRecalcularResumo() {
  try {
    state.enc.resumo = await getJSON('api/encomendas.json');
    renderEncTabs();
    if (state.enc.payload) renderEncHead();
  } catch (_) { /* o próximo `loadEncomendas` volta a pedir */ }
}

/* «Chegou» num tile: tudo o que está a caminho DESSA impressão entra na
   Coleção (`/api/pending/arrive`, o mesmo do «Chegou tudo» e da CLI). */
async function encChegou(pid, botao, foil) {
  if (!pid) return toast('Não sei que carta é esta.', { error: true });
  if (botao) { botao.disabled = true; botao.textContent = 'a dar entrada…'; }
  try {
    const r = await fetch('api/pending/arrive', {
      method: 'POST', headers: cabecalhos(),
      // Com `foil` entram só as linhas desse acabamento, e cada uma no
      // contador dela: uma foil soma ao `qty_foil` (2026-09-27).
      body: JSON.stringify(foil === undefined
        ? { printing_id: pid } : { printing_id: pid, foil: !!foil }),
    });
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error || `HTTP ${r.status}`);
    const res = await r.json();
    const n = res.arrived.reduce((s, x) => s + x.qty, 0);
    const nf = res.arrived.filter(x => x.foil).reduce((s, x) => s + x.qty, 0);
    toast(`${n} ${n === 1 ? 'cópia entrou' : 'cópias entraram'} na Coleção${
      nf ? ` (${nf} no contador de foil)` : ''}.`);
    // No tile: as que chegaram passam de «a caminho» a tidas. Uma FOIL mexe no
    // outro contador (o `qty_foil`, que este tile não segue) — relê-se.
    if (!foil && state.enc.ordered.has(pid)) {
      state.enc.ordered.set(pid, 0);
      state.enc.qty.set(pid, (state.enc.qty.get(pid) || 0) + n);
      const g = state.enc.payload.groups.find(x => x.printings.some(pr => pr.id === pid));
      if (g && g.playset) g.playset.owned += n;
      encRefreshTile(pid);
    } else {
      // Era uma das «fora da grelha»: relê-se a edição.
      await loadEncomendas(state.enc.setId);
    }
    encMarcaVelhos(true);
  } catch (err) {
    toast(`Não deu para dar entrada: ${err.message}`, { error: true });
    if (botao) { botao.disabled = false; botao.textContent = 'Chegou'; }
  }
}

async function encChegouTudo(botao) {
  if (!confirm('Dar entrada na Coleção de TUDO o que está a caminho, em todas as edições?')) return;
  if (botao) { botao.disabled = true; botao.textContent = 'a dar entrada…'; }
  try {
    const r = await fetch('api/pending/arrive', {
      method: 'POST', headers: cabecalhos(), body: '{}',
    });
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error || `HTTP ${r.status}`);
    const res = await r.json();
    const n = res.arrived.reduce((s, x) => s + x.qty, 0);
    toast(`${n} ${n === 1 ? 'cópia entrou' : 'cópias entraram'} na Coleção.`);
    encMarcaVelhos(true);
    await loadEncomendas(state.enc.setId);
  } catch (err) {
    toast(`Não deu para dar entrada: ${err.message}`, { error: true });
    if (botao) botao.disabled = false;
  }
}

/* Os controlos fixos do separador: o filtro (tudo / a caminho / faltas) e a
   procura. Ligam-se uma vez, no arranque. */
function wireEncomendas() {
  for (const b of document.querySelectorAll('.seg-btn[data-enc-filter]')) {
    b.classList.toggle('is-on', b.dataset.encFilter === state.prefs.encFilter);
    b.onclick = () => {
      state.prefs.encFilter = b.dataset.encFilter; savePrefs();
      document.querySelectorAll('.seg-btn[data-enc-filter]')
        .forEach(x => x.classList.toggle('is-on', x === b));
      renderEncomendas();
    };
  }
  let t = null;
  $('#enc-search').addEventListener('input', () => {
    clearTimeout(t); t = setTimeout(renderEncomendas, 160);
  });
}

/* As secções. `faltas-edicao` é o separador «Faltas» de
   2026-09-15 (o id `faltas` era o da tabela de preços, apagada a 2026-09-19);
   `a-mais` é o «A mais» de 2026-09-17; `encomendas` é o separador
   «Encomendas» do mesmo dia. `inicio` é o painel de 2026-09-24.

   Os NOMES não mudaram com o rebrand, de propósito: são a rota (`#a-mais`) e a
   chave das preferências guardadas, e renomeá-los partia as ligações que já
   existem dentro da página (a nota de um deck aponta ao `#encomendas` desde
   2026-09-17) e os favoritos dele.

   O que mudou foi o id no DOM, que passou a `sec-<nome>`. A rota e o id eram o
   MESMO texto, e por isso o browser tratava `#decks` como âncora e saltava
   para a `<section>` — a página abria com o cabeçalho (migalhas, título, o
   seletor de edição, e no telemóvel o `<select>` dos decks) já acima do topo
   do ecrã. Um `scrollTo(0, 0)` não chegava: o salto do browser é DEPOIS do
   `boot()`. Com os dois nomes separados não há âncora nenhuma a apanhar. */
const SECCOES = ['inicio', 'colecao', 'decks', 'faltas-edicao', 'a-mais', 'encomendas', 'venda', 'selado'];

/* Desenha a secção e põe a rota no URL. `sub` é a sub-vista — a edição, o deck
   ou a lista de compra. Vazia, usa-se a última que ele escolheu. */
let seccaoNoEcra = null;

/* Uma secção que existe E que se vê. As escondidas (2026-09-25) tratam-se como
   nomes que não existem — não há meio caminho: se o botão saiu, a rota
   também. */
function seccaoValida(name) {
  return SECCOES.includes(name) && abaVisivel(name);
}

/* Onde se cai quando a rota não serve: o Início, ou a primeira secção que se
   veja. A Coleção é a última defesa — com TUDO escondido não há para onde ir,
   e uma página em branco era pior do que a grelha. */
function seccaoInicial() {
  if (seccaoValida('inicio')) return 'inicio';
  return SECCOES.find(seccaoValida) || 'colecao';
}

function showSection(name, sub = '', { url = true } = {}) {
  if (!seccaoValida(name)) name = seccaoInicial();
  const mudou = name !== seccaoNoEcra;
  seccaoNoEcra = name;
  state.prefs.section = name;
  savePrefs();
  for (const s of SECCOES) $('#sec-' + s).hidden = s !== name;
  marcarNav(name, sub);
  renderCabecalho(name, sub);
  if (url) escreverHash(name, sub);
  fecharMenu();
  // Quem muda de secção quer o princípio dela; quem só troca de edição fica
  // onde está.
  if (mudou) window.scrollTo(0, 0);
  abrirSubVista(name, sub);
}

/* A sub-vista de cada secção, e o carregamento preguiçoso que já existia. Um
   `sub` que não exista (um favorito de uma edição que saiu do catálogo, um
   deck apagado) é ignorado em silêncio e fica o que estava — nunca uma página
   em branco. */
function abrirSubVista(name, sub) {
  const erro = (alvo, err) => { $(alvo).innerHTML = `<p class="empty">${escapeHTML(err.message)}</p>`; };

  if (name === 'inicio') {
    renderInicio();
    carregarInicio().catch(err => toast(err.message, { error: true }));
    return;
  }

  if (name === 'colecao') {
    const val = sub && (sub === TODAS || (state.index?.sets || []).some(s => s.id === sub));
    // Uma encomenda ou um «Chegou» mudou o que a grelha da Coleção diz («N a
    // caminho» nos decks, as cópias na caixa): relê-se a edição aberta.
    const velha = state.colecaoVelha;
    if (velha) state.colecaoVelha = false;
    const alvo = val ? sub : state.setId;
    if (alvo && (val ? alvo !== state.setId : velha)) {
      loadSet(alvo).catch(err => toast(err.message, { error: true }));
    }
    return;
  }

  if (name === 'decks') {
    // `state.decks` pode já estar preenchido pelo painel do Início sem que
    // nenhum deck tenha sido aberto — quem decide é o `deckId`.
    if (state.deckId === null) loadDecks(sub).catch(err => erro('#deck-body', err));
    else if (sub) abrirDeckOuLista(sub);
    return;
  }

  if (name === 'faltas-edicao') {
    if (!state.faltasEdicao) { loadFaltasEdicao(sub).catch(err => erro('#fe-body', err)); return; }
    if (sub && feSetValido(sub) && sub !== state.prefs.feSet) {
      state.prefs.feSet = sub; savePrefs(); renderFeTabs(); renderFaltasEdicao();
    }
    return;
  }

  if (name === 'a-mais') {
    if (!state.aMais) { loadAMais(sub).catch(err => erro('#am-body', err)); return; }
    if (sub && amSetValido(sub) && sub !== state.prefs.amSet) {
      state.prefs.amSet = sub; savePrefs(); renderAmTabs(); renderAMais();
    }
    return;
  }

  if (name === 'encomendas') {
    const val = sub && (state.index?.sets || []).some(s => s.id === sub);
    if (!state.enc.payload || (val && sub !== state.enc.setId)) {
      loadEncomendas(val ? sub : null).catch(err => erro('#enc-grid', err));
    }
    return;
  }

  if (name === 'venda') {
    // A venda muda por fora (a CLI, outro telemóvel): relê-se sempre que se
    // entra — é um payload pequeno e é a conta que ele vai cobrar a alguém.
    loadVenda().catch(err => erro('#vd-body', err));
    return;
  }

  if (name === 'selado') {
    if (!state.selado) loadSelado().catch(err => erro('#sl-body', err));
  }
}

/* O `sub` dos Decks é o SLUG do deck (estável e legível no URL) ou o id de uma
   das listas de compra. O payload do deck continua a pedir-se pelo número —
   a tradução é aqui. */
function abrirDeckOuLista(sub) {
  if (deckFaltaIds().includes(sub)) {
    if (state.deckId !== sub) loadDeckFaltas(sub);
    return;
  }
  const d = (state.decks || []).find(x => x.slug === sub);
  if (d && d.id !== state.deckId) loadDeck(d.id);
}

/* O slug do que está aberto nos Decks — é o que vai para o URL. */
function deckSubAtual() {
  if (deckFaltaIds().includes(state.deckId)) return state.deckId;
  const d = (state.decks || []).find(x => x.id === state.deckId);
  return d ? d.slug : '';
}

function feSetValido(s) {
  return s === 'all' || (state.faltasEdicao?.sets || []).some(x => x.set === s)
    || (state.faltasEdicao?.caixas || []).some(c => c.id === s);
}
function amSetValido(s) {
  return s === 'all' || (state.aMais?.sets || []).some(x => x.set === s && x.button);
}


/* ==========================================================================
   INÍCIO — o painel de hoje (2026-09-24)

   NÃO HÁ CONTA NOVA NENHUMA AQUI. Todos os números saem de payloads que as
   outras secções já pediam — `api/index.json` (níveis, valor, totais),
   `api/decks.json`, `api/encomendas.json` e `api/faltas_edicao.json` — e são
   mostrados exactamente como lá vêm. É de propósito: um painel que fizesse a
   sua própria aritmética era uma segunda resposta às mesmas perguntas, e mais
   cedo ou mais tarde discordava da página a que manda ir.

   Por isso também desenha DUAS vezes: à entrada, com o que já está em memória
   (o índice chega sempre no arranque), e outra vez quando os três ficheiros
   que faltam responderem. Um que falhe deixa o cartão dele a «—» e não leva a
   página atrás.                                                             */

let inicioAPedir = null;

async function carregarInicio() {
  if (inicioAPedir) return inicioAPedir;
  const tentar = async (falta, fn) => { if (falta) { try { await fn(); } catch (_) {} } };
  inicioAPedir = Promise.all([
    tentar(!state.decks, garanteDecks),
    tentar(!state.enc.resumo, async () => { state.enc.resumo = await getJSON('api/encomendas.json'); }),
    tentar(!state.faltasEdicao, async () => { state.faltasEdicao = await getJSON('api/faltas_edicao.json'); }),
  ]).then(() => {
    inicioAPedir = null;
    if (state.prefs.section === 'inicio') renderInicio();
  });
  return inicioAPedir;
}

function iniCartao(cls, icone, rotulo, valor, nota) {
  return `<div class="ini-card ${cls}">
    <div class="k"><span class="ic">${ico(icone, 14)}</span>${escapeHTML(rotulo)}</div>
    <p class="v">${valor}</p>
    <p class="n">${nota}</p></div>`;
}

function renderInicio() {
  const ix = state.index;
  if (!ix) return;
  const niveis = (ix.levels || {}).levels || [];
  const play = niveis.find(l => l.k === 3);
  const um = niveis.find(l => l.k === 1);
  const dois = niveis.find(l => l.k === 2);
  const fe = state.faltasEdicao;
  const enc = state.enc.resumo;
  const decks = state.decks;
  const tr = '<span class="n">—</span>';

  /* ------------------------------------------------------------- cartões */
  let cartoes = '';
  // O `done`/`total` dos níveis conta IMPRESSÕES; o `missing` conta CÓPIAS
  // (`metrics.niveis`: a soma de `min(k, alvo) − cópias`). São duas unidades
  // na mesma linha e têm de ser ditas pelo nome — a primeira versão desta
  // página chamou «impressões» às 281 cópias que faltam.
  cartoes += iniCartao('rox', 'colecao', 'Master set · playset',
    play ? `${num(play.done)}<small>/${num(play.total)}</small>` : tr,
    play ? `<b>${fmtPct(play.pct)}</b> das impressões — faltam <b>${
             plural(play.missing, 'cópia', 'cópias')}</b>.`
         + (um && dois ? ` 1 de cada ${fmtPct(um.pct)} · 2 de cada ${fmtPct(dois.pct)}.` : '')
         : 'a carregar…');

  const fl = fe && fe.totals_lists;
  cartoes += iniCartao('gold', 'faltas', 'Falta comprar',
    fl ? `${num(fl.copies)}<small> cópias</small>` : tr,
    fl ? `${eur(fl.cents)} ao preço de hoje · ${plural(fl.cards, 'carta', 'cartas')}.
          Só o <b>master set</b> — a coleção extra compra-se pela lista do bloco.`
       : 'a carregar as faltas…');

  const v = ix.value || {};
  const tt = ix.totals || {};
  cartoes += iniCartao('ok', 'valor', 'Valor da coleção',
    v.cents != null ? eur(v.cents) : tr,
    `${num(tt.copies || 0)} cópias de ${num(tt.cards || 0)} cartas${
      v.copias_sem_preco ? ` · ${plural(v.copias_sem_preco, 'cópia sem preço', 'cópias sem preço')}` : ''}.
     As cópias próprias dos decks não contam. ${foilNotaValor()}`);

  // ZERO DECKS (2026-09-28) é um estado normal — entre apagar as listas velhas
  // e escrever as novas. Precisa de caso PRÓPRIO: com `decks = []` o cartão
  // dizia «0 de 0 · estão todos completos», que é uma mentira das duas metades.
  if (decks && !decks.length) {
    cartoes += iniCartao('', 'montado', 'Decks montados', '<span class="n">—</span>',
      `${SEM_DECKS} ${SEM_DECKS_COMO} A Coleção dá os mesmos números que daria
       se nunca tivesse havido decks.`);
  } else if (decks) {
    const cheios = decks.filter(d => !d.missing).length;
    const faltam = decks.reduce((n, d) => n + (d.missing || 0), 0);
    cartoes += iniCartao(cheios === decks.length ? 'ok' : '', 'montado', 'Decks montados',
      `${cheios}<small> de ${decks.length}</small>`,
      faltam ? `faltam <b>${plural(faltam, 'cópia', 'cópias')}</b> para montar os outros.`
             : 'estão todos completos.');
  } else {
    cartoes += iniCartao('', 'montado', 'Decks montados', tr, 'a carregar os decks…');
  }

  const et = enc && enc.totals;
  cartoes += iniCartao(et && et.copies ? 'gold' : '', 'encomendas', 'A caminho',
    et ? `${num(et.copies)}<small> cópias</small>` : tr,
    et ? (et.copies ? `${plural(et.printings, 'impressão', 'impressões')} · ${eur(et.cents)}.
            Dá entrada em <a href="#encomendas">Encomendas</a> quando chegarem.`
                    : 'nada encomendado por chegar.')
       : 'a carregar…');

  // O que falta para fechar a COLEÇÃO EXTRA: o total das Faltas menos a parte
  // que entra nas listas de compra (o master set). É a subtração de dois
  // números do mesmo payload, não uma conta nova.
  const extra = fe && fe.totals && fl
    ? { copies: fe.totals.copies - fl.copies, cents: fe.totals.cents - fl.cents } : null;
  cartoes += iniCartao('', 'amais', 'Coleção extra',
    extra ? `${num(extra.copies)}<small> cópias</small>` : tr,
    extra ? `alt art, sobrenumeradas e promos por fechar — ${eur(extra.cents)}.
             <b>Não</b> entram na percentagem nem na wantlist geral.`
          : 'a carregar…');
  $('#inicio-cartoes').innerHTML = cartoes;

  /* ------------------------------------------------------------- atalhos */
  const atalhos = [
    ['colecao', 'colecao', 'Coleção', 'marcar o que chegou'],
    ['faltas-edicao', 'faltas', 'Faltas', 'o que comprar, por bloco'],
    ['decks', 'decks', 'Decks', 'o que falta a cada um'],
    ['encomendas', 'encomendas', 'Encomendas', 'o que vem a caminho'],
    ['a-mais', 'amais', 'A mais', 'o que sobra'],
    ['selado', 'selado', 'Produto Selado', 'o que há e o que tens'],
  ];
  // Um atalho para uma aba escondida (2026-09-25) era um botão para uma página
  // a que já não se chega pela barra.
  $('#inicio-atalhos').innerHTML = '<p class="ini-h">Onde vais mais vezes</p>'
    + '<div class="ini-atalhos-in">' + atalhos.filter(([sec]) => abaVisivel(sec))
      .map(([sec, ic, rot, nota]) =>
      `<a class="ini-atalho" href="#${sec}"><span class="ic">${ico(ic, 20)}</span>
        <span><b>${escapeHTML(rot)}</b><small>${escapeHTML(nota)}</small></span></a>`).join('')
    + '</div>';

  /* --------------------------------------------------------------- decks */
  if (decks && decks.length) {
    $('#inicio-decks').innerHTML = '<p class="ini-h">Os decks</p><div class="ini-lista">'
      + decks.map(d => {
        const pct = d.wanted ? Math.round((d.have / d.wanted) * 100) : 0;
        const cls = d.missing ? 'falta' : 'cheio';
        return `<button type="button" class="ini-linha ${cls}" data-deck="${escapeAttr(d.slug)}">
          <span class="nm"><b>${escapeHTML(d.name)}</b><small>${escapeHTML(d.legend)}${
            runasNaoContadas(d.runas) ? ` · ${d.runas.copies} runas à mão` : ''}</small></span>
          <span class="pc">${pct}% · ${d.have}/${d.wanted}<i><span style="width:${
            Math.min(100, pct)}%"></span></i></span></button>`;
      }).join('') + '</div>';
    for (const b of document.querySelectorAll('#inicio-decks .ini-linha')) {
      b.onclick = () => showSection('decks', b.dataset.deck);
    }
  } else if (decks) {
    // Sem decks a lista ficava a vazio MUDO. Diz-se, e diz-se que a Coleção
    // não perdeu nada com isso — é a pergunta que ele faria a seguir.
    $('#inicio-decks').innerHTML = '<p class="ini-h">Os decks</p>'
      + `<p class="empty">${SEM_DECKS} ${SEM_DECKS_COMO}</p>`;
  } else {
    $('#inicio-decks').innerHTML = '';
  }

  /* -------------------------------------------------------------- fontes */
  const quando = s => s ? escapeHTML(String(s).replace('T', ' ').replace('+00:00', ' UTC')) : '—';
  // `totals.printings` é quantas impressões ele TEM, não o tamanho do catálogo
  // — a primeira versão desta tabela escreveu-lhe «Catálogo (RiftScribe)» ao
  // lado, o que dava um catálogo de 1006 quando ele tem 1180.
  $('#inicio-fontes').innerHTML = '<p class="ini-h">De quando são estes números</p><table>'
    + `<tr><td>Coleção e decks</td><td>${quando(ix.generated_at)}</td></tr>`
    + `<tr><td>Preços (CardTrader)</td><td>${quando(v.day)}</td></tr>`
    + `<tr><td>Impressões com pelo menos uma cópia</td><td>${num(tt.printings || 0)}</td></tr>`
    + '</table>';
}


/* ================================== LISTAS DE COMPRA DOS DECKS (separador Decks)

   Leituras da mesma carência: soma-se o que todos os decks pedem e
   desconta-se o que ele tem — e o que um deck não recebe compra-se, mesmo que
   exista num deck de cima (desde 2026-09-11 não há teto do playset, e a aba
   «Por deck» É a alocação por prioridade).

   Viveram no antigo separador «Faltas» (que passou a tabela de preços e foi
   apagado a 2026-09-19) até 2026-09-15 à tarde; desde então são abas do separador
   Decks, a seguir aos decks, e lêem o `api/compras.json` (o que restou do
   antigo `faltas.json`). Os ids não podem colidir com um slug de deck — é o
   `state.deckId` que os guarda. */
const DECK_FALTA_TABS = [
  { id: 'staples', label: 'Staples', sub: 'pedidas por vários decks' },
  { id: 'pordeck', label: 'Por deck', sub: 'o que falta a cada um' },
  { id: 'pimp', label: 'Pimp decks', sub: 'versões alteradas das cartas dos decks' },
];
/* As que se VÊEM. A tabela acima é o catálogo e fica inteira; a lista de
   `abas.escondidas` (2026-09-25) é que decide quais delas entram no índice,
   no `<select>` do telemóvel e nas rotas `#decks/<vista>`. As funções de
   desenho (`renderPorDeck`, `renderPimp`) não se tocam — o cálculo continua no
   `api/compras.json`, que continua a ser pedido pelas que ficam. */
function deckFaltaTabs() {
  return DECK_FALTA_TABS.filter(t => abaVisivel(t.id));
}
function deckFaltaIds() {
  return deckFaltaTabs().map(t => t.id);
}

function contadorFalta(id) {
  const f = state.compras;
  if (!f) return '';
  if (id === 'staples') return plural(f.staples.length, 'carta', 'cartas');
  if (id === 'pordeck') return plural(f.por_deck.reduce((s, d) => s + d.copies, 0), 'cópia', 'cópias');
  if (id === 'pimp') return plural(f.pimp.by_deck.reduce((s, d) => s + d.printings, 0),
                                   'versão', 'versões');
  return '';
}

/* Uma das abas por deck, dentro do separador Decks. */
async function loadDeckFaltas(id) {
  state.deckId = id;
  state.prefs.deck = id;
  savePrefs();
  renderDeckTabs();
  if (state.prefs.section === 'decks') escreverHash('decks', id);
  $('#deck-head').innerHTML = '';
  $('#deck-body').innerHTML = '<p class="empty">a carregar…</p>';
  try {
    await garanteCompras();
  } catch (err) {
    $('#deck-body').innerHTML = `<p class="empty">${escapeHTML(err.message)}</p>`;
    return;
  }
  if (state.deckId !== id) return;      // entretanto abriu outro separador
  renderDeckTabs();                     // agora com os contadores
  $('#deck-head').innerHTML = FALTA_HEAD.includes(id) ? faltaHead() : '';
  if (id === 'staples') renderStaples();
  else if (id === 'pordeck') renderPorDeck();
  else renderPimp();
}

/* ======================================================= COLAR UMA LISTA ===
   André, 2026-10-01: *"dos decks, tem que ser possivel colar o texto em copy
   paste e gerar o deck"*. Até 2026-10-02 a única porta era pôr um `.txt` na
   pasta `decks/` à mão.

   DOIS PASSOS, e o primeiro não grava: «Ler» mostra o que vai gravar (as
   linhas que casaram, as que não casaram, a aritmética) e só depois «Gravar»
   escreve. Uma lista com um nome que o catálogo não conhece não pode virar um
   deck em silêncio — o servidor recusa-a com 409 e é preciso confirmar.

   O id não pode colidir com um slug de deck (é o `state.deckId` que o guarda),
   e por isso é uma palavra que o `_slug` do `colar.py` nunca produz sozinha
   para um deck: um deck chamado «colar» ficaria com este id. É o mesmo risco
   que os ids do `DECK_FALTA_TABS` já corriam desde 2026-09-15. */
const COLAR_ID = 'colar';

async function loadColar() {
  state.deckId = COLAR_ID;
  state.prefs.deck = COLAR_ID;
  savePrefs();
  renderDeckTabs();
  if (state.prefs.section === 'decks') escreverHash('decks', COLAR_ID);
  // `<span>` e não `<small>`: o `.section-head` é `text-transform: capitalize`
  // e só o `span` está isento. Isto é uma FRASE — com `<small>` lia-se
  // «Copy-Paste De Uma Decklist». É a mesma avaria do Produto Selado
  // («Binders E Deck Boxes», 2026-09-25), e a cura é usar a marcação que já
  // existe em vez de uma regra nova.
  $('#deck-head').innerHTML = `<div class="section-head"><h2>Colar uma lista</h2>
    <span>copy-paste de uma decklist — vira um deck gravado</span></div>`;
  renderColar();
}

/* O estado da caixa vive aqui e não no `state`: é de um ecrã só, e perde-se
   de propósito quando ele sai — uma previsão guardada envelhecia em silêncio
   (a Coleção dele muda a cada `+`). */
let colarEstado = { texto: '', prev: null, erro: '', ocupado: false,
                    img: null, aler: false };

function renderColar() {
  const e = colarEstado;
  $('#deck-body').innerHTML = `
    <p class="note">Cola a lista como ela sai do sítio onde a construíste — com
    as secções (<code>Legend:</code>, <code>Champion:</code>, <code>MainDeck:</code>,
    <code>Battlefields:</code>, <code>Rune Pool:</code>, <code>Sideboard:</code>)
    e as linhas <code>3 Nome da carta</code>. Não precisa de código de edição:
    o nome identifica a carta, e o deck usa as versões que tiveres.
    Uma linha <code>Nome: …</code> no topo dá o nome ao deck.</p>
    <p class="note">Ou <b>escolhe uma IMAGEM</b> da página de classificações, com
    a grelha de cartas: cada carta é reconhecida pela ARTE e a quantidade pelo
    crachá <code>xN</code>. O que sair vem para a caixa de baixo, para
    <b>emendares antes de gravar</b> — e o que não se reconhecer fica de fora e
    é dito, nunca adivinhado.</p>
    <div class="colar-bar">
      <input type="file" id="colar-img" accept="image/*" class="colar-img"
        aria-label="Escolhe a imagem da decklist">
      ${e.aler ? '<span class="note">a ler a imagem…</span>' : ''}
    </div>
    ${e.img ? colarImagemHTML(e.img) : ''}
    <textarea id="colar-txt" class="colar-txt" rows="12" spellcheck="false"
      placeholder="Nome: O meu deck&#10;&#10;Legend:&#10;1 Leona, Radiant Dawn&#10;&#10;MainDeck:&#10;3 Zenith Blade&#10;…"
      aria-label="Cola aqui a decklist">${escapeHTML(e.texto)}</textarea>
    <div class="colar-bar">
      <button type="button" class="btn" id="colar-ler">Ler a lista</button>
      ${e.prev ? `<button type="button" class="btn primary" id="colar-gravar">${
        e.ocupado ? 'Substituir o deck' : 'Gravar o deck'}</button>` : ''}
      <button type="button" class="btn" id="colar-limpar">Limpar</button>
    </div>
    ${e.erro ? `<p class="note aviso">${escapeHTML(e.erro)}</p>` : ''}
    ${e.prev ? colarPrevHTML(e.prev) : ''}`;

  $('#colar-txt').oninput = (ev) => { colarEstado.texto = ev.target.value; };
  $('#colar-ler').onclick = () => colarLer();
  $('#colar-limpar').onclick = () => {
    colarEstado = { texto: '', prev: null, erro: '', ocupado: false,
                    img: null, aler: false };
    renderColar();
  };
  const fi = $('#colar-img');
  if (fi) fi.onchange = (ev) => {
    const f = ev.target.files && ev.target.files[0];
    if (f) colarImagem(f);
  };
  const g = $('#colar-gravar');
  if (g) g.onclick = () => colarGravar();
}

/* O que a IMAGEM deu, e sobretudo o que ela NÃO deu. */
function colarImagemHTML(r) {
  const d = r.duvidas || [];
  const avisos = [];
  if (r.champion_por_posicao) avisos.push(
    'o <b>Champion</b> saiu da POSIÇÃO na página — o catálogo não o marca: ' +
    'confere a linha antes de gravar');
  if (!r.sideboard) avisos.push(
    'não se viu corte nenhum para o <b>sideboard</b>: ficou tudo no deck');
  return `<div class="colar-img-res">
    <p class="note"><b>${r.cartas.length}</b> carta(s) lida(s) das
      ${r.grelha.cartas} da imagem${d.length
        ? `, <b class="aviso">${d.length} por ler</b>` : ', nenhuma por ler'}.</p>
    ${d.length ? `<ul class="colar-falhas">${d.map(x => `<li>linha ${x.linha},
      coluna ${x.coluna}: ${escapeHTML(x.porque)}${x.parecida
        ? ` <small>(parecida com ${escapeHTML(x.parecida)}${
            x.qty ? `, ×${x.qty}` : ''})</small>` : ''}</li>`).join('')}</ul>
      <p class="note">Escreve-as à mão na caixa — a lista só leva o que se
      reconheceu com certeza.</p>` : ''}
    ${avisos.map(a => `<p class="note aviso">${a}</p>`).join('')}
  </div>`;
}

async function colarImagem(ficheiro) {
  colarEstado.aler = true;
  colarEstado.erro = '';
  renderColar();
  try {
    const r = await fetch('api/decks/imagem', {
      method: 'POST',
      headers: { ...cabecalhos(), 'Content-Type': 'application/octet-stream' },
      body: ficheiro,
    });
    const j = await r.json();
    if (!r.ok) throw new Error(j.error || `HTTP ${r.status}`);
    colarEstado.img = j;
    // O texto vai para a MESMA caixa do copy-paste, e é editável: daí para a
    // frente é o caminho de sempre.
    colarEstado.texto = j.texto || '';
    colarEstado.prev = j.previsao || null;
    colarEstado.ocupado = !!(j.previsao && j.previsao.ocupado);
  } catch (err) {
    colarEstado.erro = err.message;
    colarEstado.img = null;
  }
  colarEstado.aler = false;
  renderColar();
}

/* A PREVISÃO: o que vai gravar, antes de gravar. */
function colarPrevHTML(p) {
  const falhas = p.nao_casaram || [];
  const regras = p.regras || {};
  const alvo = { main: regras.main, runes: regras.runes, battlefields: regras.battlefields };
  return `<div class="colar-prev">
    <div class="section-head"><h3>${escapeHTML(p.nome)}</h3>
      <span>vai gravar-se como <code>${escapeHTML(p.slug)}.txt</code>${
        p.ocupado ? ' — <b>já existe um deck com este nome</b>' : ''}</span></div>
    <table class="colar-tab">
      <thead><tr><th>Secção</th><th>Cartas</th><th>Cópias</th><th>Regra</th></tr></thead>
      <tbody>${(p.por_papel || []).map(b => {
        const a = alvo[b.role];
        // A regra do main conta o Champion (`main_includes_champion`), que é o
        // que as listas dele fazem: 39 + 1 = 40.
        const soma = b.role === 'main' && regras.main_includes_champion
          ? b.copias + ((p.por_papel.find(x => x.role === 'champion') || {}).copias || 0)
          : b.copias;
        return `<tr${b.faltam_ler ? ' class="tem-falha"' : ''}>
          <td data-l="Secção">${escapeHTML(b.label)}</td>
          <td data-l="Cartas">${b.cartas}</td>
          <td data-l="Cópias"><span>${b.copias}${
            b.role === 'main' && regras.main_includes_champion && soma !== b.copias
              ? ` <small>(+1 Champion = ${soma})</small>` : ''}</span></td>
          <td data-l="Regra">${a ? `<span class="${soma === a ? 'ok' : 'nok'}">${soma}/${a}</span>` : '—'}</td>
        </tr>`;
      }).join('')}</tbody>
    </table>
    ${falhas.length ? `<div class="colar-falhas">
      <b>${falhas.length} ${falhas.length === 1 ? 'linha não casou' : 'linhas não casaram'}
      com o catálogo</b> — corrige o nome, ou grava sem elas:
      <ul>${falhas.map(f => `<li><code>${escapeHTML(f.qty + ' ' + f.raw)}</code>
        <small>(${escapeHTML(f.role)})</small></li>`).join('')}</ul></div>`
      : `<p class="note tudo-casou">As ${p.totais.linhas} linhas casaram todas com o catálogo.</p>`}
    <details class="colar-linhas"><summary>As ${p.totais.linhas} linhas lidas
      (${p.totais.copias} cópias)</summary>
      <ul>${(p.linhas || []).map(l => `<li class="${l.casou ? '' : 'nok'}">
        ${l.qty}× ${escapeHTML(l.name || l.raw)}
        <small>${escapeHTML(l.casou ? (l.type || '') : 'não casou')}</small></li>`).join('')}</ul>
    </details></div>`;
}

async function colarLer() {
  const texto = ($('#colar-txt') || {}).value || '';
  colarEstado.texto = texto;
  colarEstado.erro = '';
  colarEstado.prev = null;
  try {
    const r = await fetch('api/decks/prever', {
      method: 'POST', headers: cabecalhos(),
      body: JSON.stringify({ texto }),
    });
    const j = await r.json();
    if (!r.ok) throw new Error(j.error || `HTTP ${r.status}`);
    colarEstado.prev = j;
    colarEstado.ocupado = !!j.ocupado;
  } catch (err) {
    colarEstado.erro = err.message;
  }
  renderColar();
}

async function colarGravar() {
  const e = colarEstado;
  if (!e.prev) return;
  // Duas perguntas, cada uma com a sua confirmação: gravar sem as linhas que
  // não casaram, e escrever por cima de um deck que já existe.
  if ((e.prev.nao_casaram || []).length
      && !confirm(`${e.prev.nao_casaram.length} linha(s) não casaram com o `
        + 'catálogo e vão ficar de fora do deck. Gravar assim?')) return;
  if (e.ocupado && !confirm(`Já existe um deck «${e.prev.slug}». `
      + 'A lista dele vai ser substituída por esta. Continuar?')) return;
  e.erro = '';
  renderColar();
  try {
    // `substituir` vai com o que a PREVISÃO disse, não `true` fixo: se o deck
    // passou a existir entre o «Ler» e o «Gravar», o servidor responde 409 e
    // ele volta a ler — com `true` fixo, escrevia-se por cima sem perguntar.
    const r = await fetch('api/decks/colar', {
      method: 'POST', headers: cabecalhos(),
      body: JSON.stringify({ texto: e.texto, confirmar: true,
                             substituir: !!e.ocupado }),
    });
    const j = await r.json();
    if (!r.ok) throw new Error(j.error || `HTTP ${r.status}`);
    state.decks = j.decks;
    // Gravar um deck muda o que a Coleção diz que está em uso, o que falta
    // comprar e o «A mais»: marcam-se por reler, como o resto da app faz.
    state.compras = null;
    state.aMais = null;
    state.colecaoVelha = true;
    wlDesatualizar();
    colarEstado = { texto: '', prev: null, erro: '', ocupado: false };
    toast(`Deck «${j.nome}» gravado.`);
    const d = (j.decks || []).find(x => x.slug === j.slug);
    if (d) { await loadDeck(d.id); return; }
  } catch (err) {
    e.erro = err.message;
  }
  renderColar();
}

/* O cabeçalho é a carência GLOBAL DOS DECKS (`faltas.shortfall`): tudo o que
   os decks pedem, sem teto, menos o que ele tem e o que vem a caminho — o
   mesmo número que a aba «Por deck» soma. Só descreve as Staples e o Por
   deck; no Pimp era outra pergunta (ver `FALTA_HEAD`). */
const FALTA_HEAD = ['staples', 'pordeck'];

function faltaHead() {
  const f = state.compras;
  const t = f.totals;
  return `<div class="deck-card">
    <div class="deck-title"><b>Falta comprar aos decks</b>
      <span class="prio">${plural(t.cards, 'carta', 'cartas')} · ${
        plural(t.copies, 'cópia', 'cópias')}</span></div>
    <div class="deck-meta">
      <span><i>Custo estimado</i>${eur(t.cents)}</span>
      <span><i>Critério</i>preço mais baixo no CardTrader, edição mais barata</span>
      ${f.ignored_types.length ? `<span><i>Fora da conta</i>${
        f.ignored_types.join(', ')} — compram-se a granel</span>` : ''}
    </div>
    <small class="nota">Soma o que <b>todos</b> os decks pedem menos o que tens:
      o que um deck não recebe compra-se, mesmo que exista num deck de cima.${
        // Com o «Por deck» escondido (2026-09-25) não se manda ninguém a uma
        // aba que já não está no índice.
        abaVisivel('pordeck')
          ? `
      A aba <i>Por deck</i> reparte este mesmo número por prioridade${
        (f.por_deck || []).some(d => d.grupo && d.grupo.variantes)
          ? ' — excepto nos decks com a <b>mesma Legend</b>, que partilham as cartas: cada um mostra a sua lista, mas a compra é uma e aqui conta uma vez'
          : ''}.`
          : ''}</small>
  </div>`;
}

function renderStaples() {
  const f = state.compras;
  $('#deck-body').innerHTML = f.staples.length ? `
    <p class="note">Cartas que <b>mais do que um deck</b> pede e que não tens
      em número suficiente. São as que rendem mais por euro — uma compra
      serve vários decks.</p>
    <div class="grid deck-grid">${f.staples.map(staplTile).join('')}</div>`
    : '<p class="empty">Nenhuma carta é pedida por dois decks ao mesmo tempo.</p>';
}


/* ====================================================== «FALTAS»

   O que falta, por edição, em quatro blocos (André, 2026-09-15, fim da tarde:
   "quero as faltas por edicao e dividido em 3 partes / Masterset / Alt Art /
   OverNumbered"; 2026-09-19: "quero 4 wantlist: 1 so para o master set, 1 so
   para as Alt.Art, 1 so para as Overnumbered, uma so para as Promo"). Vem
   tudo do servidor (`api/faltas_edicao.json`, `faltas_edicao.payload`) — a
   mesma carência da wantlist do fim de cada edição da Coleção, os blocos pela
   ordem da Coleção; aqui só se desenha.

   A carta com imagem, não texto — é o que ele pediu nesse mesmo dia ("gosto
   de ter em imagem da carta e nao apenas texto"). Os tiles
   são os `dtile` dos decks (`artHTML`), com o crachá a dizer QUANTAS FALTAM.

   CADA BLOCO TEM A SUA WANTLIST (2026-09-19): por baixo dos tiles, a caixa
   do Cardmarket já preenchida, escrita pelo mesmo gerador das outras listas
   (`cmLinha`), só com o que há a comprar. Só os blocos com `in_lists` (o
   master set) entram na wantlist GERAL da Coleção — os outros dizem-no no
   cabeçalho; a wantlist deles é própria do bloco. Uma carta a caminho
   aparece marcada e não vai para nenhuma das duas.

   DUAS METADES, DESDE 2026-09-27 (André: "quero as faltas separadas, as
   normais e as foils / as foils nao sao faltas, sao apenas complemento e
   indicativo / mais tarde poderao vir a ser compradas, entao preciso que
   tenham uma wantlist a parte"). Em cada edição: primeiro as NORMAIS, os
   quatro blocos como sempre; depois as FOILS (`s.foil`, do
   `faltas_foil.bloco`), num bloco só, com a QUINTA wantlist. O alvo delas é o
   playset do TIPO (Rune 12, Battlefield 1) e o preço é o da FOIL.

   As foils NÃO SOMAM a nada do que está em cima: os `totals`, os
   `totals_lists` e os quatro blocos vêm do `faltas_edicao.payload` e não
   sabem que esta metade existe. O cabeçalho conta-as à parte, e o número
   grande do separador continua a ser o das normais.                         */

async function loadFaltasEdicao(sub = '') {
  $('#fe-body').innerHTML = '<p class="empty">a carregar…</p>';
  state.faltasEdicao = await getJSON('api/faltas_edicao.json');
  feLigarCaixas();
  if (sub && feSetValido(sub)) state.prefs.feSet = sub;
  renderFeTabs();
  renderFaltasEdicao();
}

/* AS CAIXAS (2026-10-02): a caixa vem do servidor com os `pids` e SEM itens —
   aqui resolvem-se para os MESMOS objectos que as edições têm, por referência.

   É o que faz uma caixa comportar-se como um bloco no resto do ficheiro (o
   `feSoma`, o `feWantlistItens`, o `feTile`, o `feWlSoma` não sabem que ela
   existe) e é o que faz o `+` de «já encomendei» continuar a valer: o
   `feItem()` mexe num objecto só, e a caixa e o bloco da edição dizem o mesmo
   número por serem a MESMA linha. Com duas cópias divergiam no primeiro
   clique. */
function feLigarCaixas() {
  const p = state.faltasEdicao;
  if (!p?.caixas) return;
  const porPid = new Map();
  for (const s of p.sets) {
    for (const g of s.blocks) for (const x of g.items) porPid.set(x.printing_id, x);
  }
  for (const c of p.caixas) c.items = (c.pids || []).map(pid => porPid.get(pid)).filter(Boolean);
}

/* A caixa escolhida, ou `null` se o que está escolhido é uma edição. UMA
   escolha para as duas filas de botões — `prefs.feSet`. */
function feCaixa() {
  return (state.faltasEdicao?.caixas || []).find(c => c.id === state.prefs.feSet) || null;
}

function renderFeTabs() {
  const p = state.faltasEdicao;
  if (!feSetValido(state.prefs.feSet)) state.prefs.feSet = 'all';
  const escolher = (id) => {
    state.prefs.feSet = id; savePrefs();
    escreverHash('faltas-edicao', id);
    renderFeTabs(); renderFaltasEdicao();
  };
  const fila = (nav, botoes) => {
    nav.innerHTML = '';
    for (const s of botoes) {
      const b = document.createElement('button');
      const on = s.id === state.prefs.feSet;
      b.className = 'tab' + (on ? ' is-on' : '');
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
      b.innerHTML = `${escapeHTML(s.name)}<small>${escapeHTML(feCurto(s.t))}</small>`;
      b.onclick = () => escolher(s.id);
      nav.appendChild(b);
    }
  };
  fila($('#fe-tabs'), [{ id: 'all', name: 'Todas', t: p.totals },
                       ...p.sets.map(s => ({ id: s.set, name: s.name, t: s }))]);
  // A fila das caixas não aparece quando não há nenhuma (lista vazia no
  // config): um rótulo «Caixas» sobre o vazio não diz nada.
  const cxs = p.caixas || [];
  $('#fe-caixas-bar').hidden = !cxs.length;
  if (cxs.length) fila($('#fe-caixas'), cxs.map(c => ({ id: c.id, name: c.label, t: c })));
}

/* «faltam 304 · 2 257 €» — o resumo curto de um bloco, edição ou total. */
function feCurto(t) {
  if (!t.copies && !t.pending_copies) return 'nada falta';
  return `faltam ${t.copies} · ${eurShort(t.cents)}`;
}

/* «faltam N cópias de M · X €[ · K a caminho]» — a frase dos cabeçalhos. */
function feResumo(t) {
  if (!t.copies && !t.pending_copies) return 'nada falta';
  const partes = [];
  if (t.copies) partes.push(`faltam <b>${plural(t.copies, 'cópia', 'cópias')}</b> de ${
    plural(t.cards, 'impressão', 'impressões')} · <b>${eur(t.cents)}</b>${
    t.no_price ? ` (${t.no_price} sem preço)` : ''}`);
  if (t.pending_copies) partes.push(`<i class="caminho">${t.pending_copies} a caminho</i>`);
  return partes.join(' · ');
}

function renderFaltasEdicao() {
  const cx = feCaixa();
  if (cx) { renderFeCaixa(cx); return; }
  const p = state.faltasEdicao;
  const sel = state.prefs.feSet;
  const sets = p.sets.filter(s => sel === 'all' || s.set === sel);
  const t = p.totals, tl = p.totals_lists;
  const nasListas = p.blocks.filter(b => b.in_lists).map(b => b.label);
  const soVer = p.blocks.filter(b => !b.in_lists).map(b => b.label);
  const fora = Object.entries(p.scope.fora || {}).map(([b, n]) => `${n} ${escapeHTML(b)}`);

  const nBlocos = p.blocks.length;
  const quantos = { 3: 'três', 4: 'quatro', 5: 'cinco' }[nBlocos] || String(nBlocos);

  $('#fe-head').innerHTML = `<div class="deck-card">
    <div class="deck-title"><b>Faltas</b>
      <span class="prio">${plural(t.cards, 'impressão', 'impressões')} · ${
        plural(t.copies, 'cópia', 'cópias')}</span></div>
    <div class="deck-meta">
      <span><i>Fechar os ${quantos} blocos</i>${eur(t.cents)}</span>
      <span><i>Wantlist geral (${escapeHTML(nasListas.join(' + '))})</i>${eur(tl.cents)} · ${
        plural(tl.copies, 'cópia', 'cópias')}</span>
      ${t.pending_copies ? `<span><i>A caminho</i>${t.pending_copies} cópias — não contam</span>` : ''}
    </div>
    <small class="nota">Cada bloco tem a <b>sua wantlist</b> do Cardmarket, por baixo das
      cartas — ${quantos} por edição, separadas. Só o <b>${escapeHTML(nasListas.join(' e '))}</b>
      entra na wantlist geral (a do fim de cada edição da Coleção e a «Wantlist — tudo»)${
      soVer.length ? ` — <b>${escapeHTML(soVer.join(', '))}</b> não entram lá
      (<code>listas_de_compra.so_master_set</code>): acompanhar não é comprar em bloco,
      cada uma dessas listas copia-se à parte` : ''}.
      ${state.editable ? `O <b>+</b> de cada carta marca «<b>já encomendei</b>» e o
      <b>−</b> desmarca — são os mesmos botões do separador <b>Encomendas</b>, o
      mesmo registo e o mesmo número. A linha <b>não desaparece</b>: passa a dizer
      quanto ainda falta e quantas vêm a caminho, e só sai da wantlist (não se
      compra duas vezes). O <b>Chegou</b> continua nas Encomendas. ` : ''}
      O que vem a caminho aparece marcado e não vai para nenhuma lista.
      Preço mais baixo em Near Mint/Mint no CardTrader, só ofertas em inglês.${
      fora.length ? `<br>Fora deste separador: ${fora.join(', ')} — não estão em nenhum dos ${quantos} blocos.` : ''}</small>
    ${feFoilCabecalho(p.foil)}
  </div>`;

  $('#fe-body').innerHTML = sets.map(s => `
    <h2 class="section-head fe-set">${escapeHTML(s.name)}
      <span data-fe-res="set:${escapeAttr(s.set)}">${feResumo(s)}</span></h2>
    <p class="fe-metade normais">Normais — <b>as faltas</b></p>
    ${s.blocks.map(g => `
      <h3 class="section-head sub fe-bloco ${g.id}${g.in_lists ? '' : ' fe-ver'}">${escapeHTML(g.label)}
        <small>${escapeHTML(g.target_label)}${g.in_lists ? '' : ' · wantlist própria'}</small>
        <span data-fe-res="bloco:${escapeAttr(s.set)}:${escapeAttr(g.id)}">${feResumo(g)}</span></h3>
      ${g.items.length
        ? `<div class="grid deck-grid fe-grid">${g.items.map(feTile).join('')}</div>`
        : `<p class="empty fe-vazio">${g.scope ? 'Nada falta neste bloco.' : 'Esta edição não tem impressões neste bloco.'}</p>`}
      ${feWantlistHTML(s, g)}`).join('')}
    ${feFoilMetade(s)}`).join('');

  // As caixas vêm preenchidas, como as da Coleção: a wantlist está ali, sem
  // carregar em nada. Uma por (edição, bloco), com id próprio para as
  // botões não colidirem. A das foils é a quinta e liga-se igual; a nota dela
  // é outra (`foilTodas`), porque ali TODAS as linhas precisam do filtro.
  for (const s of sets) {
    for (const g of feBlocosTodos(s)) {
      const itens = feWantlistItens(g);
      if (!itens.length) continue;
      const zid = feWlId(s, g) + '-cm';
      cmLigar(zid, () => feWantlistItens(g), `riftvault-faltas-${s.set}-${g.id}-${hojeISO()}.csv`);
      cmMostrar(zid, itens, false,
                { foco: false, copiar: false, foilTodas: g.id === 'foil' });
    }
  }
  ligarFeEnc();
}

/* Os blocos de uma edição, nas duas metades: os quatro das normais e, se a
   edição tiver âmbito de foil (o OGS não tem), o das foils. */
function feBlocosTodos(s) {
  return s.foil ? [...s.blocks, s.foil] : s.blocks;
}

/* ------------------------------------------------------------------ AS CAIXAS

   André, 2026-10-02: *"gostava que tivesse uma caixa tambem para faltas de
   Overnumbered e outra caixa para faltas AltArt e uma caixa para as faltas de
   Vendetta (que era tudo). pode ser com sistema de botoes para nao ocupar muito
   espaco"*.

   Uma caixa é UMA lista e UMA wantlist, com o mesmo aspecto de um bloco — os
   mesmos tiles (`feTile`), a mesma caixa do Cardmarket (`feWantlistHTML`), o
   mesmo resumo (`feResumo`). O que muda é o corte: ali é «este bloco desta
   edição», aqui é «este bloco de todas as edições» ou «esta edição inteira». */
function renderFeCaixa(c) {
  $('#fe-head').innerHTML = feCaixaCabecalho(c);
  $('#fe-body').innerHTML = `
    <h2 class="section-head fe-set">${escapeHTML(c.label)}
      <span data-fe-res="caixa:${escapeAttr(c.id)}">${feResumo(c)}</span></h2>
    ${c.items.length
      ? `<div class="grid deck-grid fe-grid">${c.items.map(feTile).join('')}</div>`
      : `<p class="empty fe-vazio">${c.scope
          ? 'Nada falta nesta caixa.' : 'Esta caixa não tem impressões no âmbito.'}</p>`}
    ${feWantlistHTML(null, c)}`;

  const itens = feWantlistItens(c);
  if (itens.length) {
    const zid = feWlId(null, c) + '-cm';
    cmLigar(zid, () => feWantlistItens(c), `riftvault-faltas-${c.id}-${hojeISO()}.csv`);
    cmMostrar(zid, itens, false, { foco: false, copiar: false });
  }
  ligarFeEnc();
}

/* O cabeçalho de uma caixa. À parte porque o `feAcertarResumos` o reescreve a
   cada `+` — e aí não se pode redesenhar o `#fe-body`, que faria as imagens
   todas piscar. Aqui não há imagens, por isso reescreve-se inteiro em vez de
   haver os mesmos números escritos em dois sítios. */
function feCaixaCabecalho(c) {
  const p = state.faltasEdicao;
  const esc = Object.entries(c.escondidas || {})
    .map(([k, n]) => `${n} ${escapeHTML(feKind(k, n))}`);
  return `<div class="deck-card">
    <div class="deck-title"><b>${escapeHTML(c.label)}</b>
      <span class="prio">${escapeHTML(c.escopo_label)} · ${
        plural(c.scope, 'impressão', 'impressões')}</span></div>
    <div class="deck-meta">
      <span><i>Fechar esta caixa</i>${eur(c.cents)} · ${
        plural(c.copies, 'cópia', 'cópias')}</span>
      <span><i>Alvo</i>${escapeHTML(c.target_label)}</span>
      ${c.mais_cara ? `<span><i>A mais cara, sozinha</i>${eur(c.mais_cara.cents)} —
        ${escapeHTML(c.mais_cara.name)} <code>${escapeHTML(
          (c.mais_cara.code || '').split('/')[0])}</code></span>` : ''}
      ${c.pending_copies ? `<span><i>A caminho</i>${c.pending_copies} cópias — não contam</span>` : ''}
    </div>
    <small class="nota">Uma caixa é o separador cortado <b>ao contrário</b>: em vez
      de uma edição em ${plural(p.blocks.length, 'bloco', 'blocos')}, ${
      c.set ? `a edição <b>inteira</b> numa lista só` :
              `este bloco de <b>todas as edições</b> numa lista só`}.
      <b>As caixas sobrepõem-se</b> — uma sobrenumerada do VEN está na caixa
      «OverNumbered» e também na «VEN — tudo» —, por isso <b>a soma das caixas não
      é o total do separador</b> (${eur(p.totals.cents)}).
      ${c.lists.copies ? `Desta caixa, ${plural(c.lists.copies, 'cópia', 'cópias')} ·
        ${eur(c.lists.cents)} já ${c.lists.copies === 1 ? 'está' : 'estão'} na wantlist
        geral da Coleção (é o master set): comprando por aqui não compras duas vezes,
        é a mesma carta.` : `Nada desta caixa está na wantlist geral da Coleção
        (<code>listas_de_compra.so_master_set</code>) — é esta a lista dela.`}
      ${esc.length ? `<br>Fora desta caixa, por estarem <b>escondidas</b> em todo o
        site (<code>master_set.escondidas</code>): ${esc.join(' · ')}.` : ''}
      ${c.foil ? ` E ${c.foil} cópias na metade das <i class="foil">foils</i>, que
        não são faltas (2026-09-27) e têm a lista delas no separador da edição.` : ''}
      ${state.editable ? ` O <b>+</b> e o <b>−</b> são os mesmos de sempre e o mesmo
        registo: marcar aqui marca na edição, é a mesma linha.` : ''}</small>
  </div>`;
}

/* O nome de um `variant_kind` em palavras dele, para a linha das escondidas.
   É aqui que uma signature apareceria pelo nome se o VEN passasse a ter uma —
   hoje são zero (medido a 2026-10-02: 0 de 228). */
function feKind(k, n = 2) {
  const nomes = {
    rune_promo: ['runa sem numeração', 'runas sem numeração'],
    token: ['token', 'tokens'],
    signature: ['signature', 'signatures'],
    alt_art: ['arte alternativa', 'artes alternativas'],
    special: ['promo', 'promos'],
    base: ['da sequência', 'da sequência'],
  }[k];
  return nomes ? nomes[n === 1 ? 0 : 1] : k;
}

/* ---------------------------------------------------------------- «JÁ ENCOMENDEI»

   O gémeo do `faltas_edicao.soma` em JavaScript: as contas de um bloco, de uma
   edição e do separador saem daqui a cada `+`/`−`, como as barras da Coleção se
   recalculam a cada clique. Há teste que corre os dois sobre os mesmos itens. */

/* @fe-soma:inicio — troço puro, corrido no node pelo teste que o compara com
   o `faltas_edicao.soma` em Python. Não toca no DOM nem no estado. */
function feSoma(itens) {
  return {
    cards: itens.filter(x => x.missing > 0).length,
    copies: itens.reduce((n, x) => n + x.missing, 0),
    cents: itens.reduce((n, x) => n + (x.total || 0), 0),
    no_price: itens.filter(x => x.missing > 0 && x.price == null).length,
    pending_cards: itens.filter(x => x.pending > 0).length,
    pending_copies: itens.reduce((n, x) => n + (x.pending || 0), 0),
    short_cards: itens.length,
  };
}
/* @fe-soma:fim */

/* O resumo da wantlist de um bloco — só o que há a COMPRAR. É o gémeo do
   `faltas_edicao._wantlist_do_bloco`: o que vem a caminho sai da lista (não se
   compra duas vezes) mas fica no tile, marcado. */
function feWlSoma(g) {
  const itens = feWantlistItens(g);
  return { lines: itens.length,
           copies: itens.reduce((n, x) => n + cmQtd(x), 0),
           cents: itens.reduce((n, x) => n + (x.total || 0), 0),
           foil: itens.filter(x => x.foil_only).length };
}

/* Refaz as somas todas a partir dos `items`, que são a verdade no cliente
   enquanto há pedidos em voo. Não pede nada ao servidor. */
function feRecontar() {
  const p = state.faltasEdicao;
  if (!p) return;
  const todos = [], nasListas = [], foils = [];
  for (const s of p.sets) {
    for (const g of s.blocks) {
      Object.assign(g, feSoma(g.items));
      g.wantlist = feWlSoma(g);
      todos.push(...g.items);
      if (g.in_lists) nasListas.push(...g.items);
    }
    Object.assign(s, feSoma(s.blocks.flatMap(g => g.items)));
    s.lists = feSoma(s.blocks.filter(g => g.in_lists).flatMap(g => g.items));
    if (s.foil) {
      Object.assign(s.foil, feSoma(s.foil.items));
      s.foil.wantlist = feWlSoma(s.foil);
      foils.push(...s.foil.items);
    }
  }
  p.totals = feSoma(todos);
  p.totals_lists = feSoma(nasListas);
  // As caixas são os MESMOS itens noutro corte, por isso refazem-se da mesma
  // forma — e o `lists` delas também, que é o que a nota promete («desta caixa,
  // X já está na wantlist geral»).
  if (p.caixas?.length) {
    const geral = new Set(nasListas);
    for (const c of p.caixas) {
      Object.assign(c, feSoma(c.items || []));
      c.wantlist = feWlSoma(c);
      c.lists = feSoma((c.items || []).filter(x => geral.has(x)));
    }
  }
  if (p.foil) {
    p.foil.totals = { ...feSoma(foils),
                      no_foil_price: p.sets.reduce(
                        (n, s) => n + (s.foil ? s.foil.no_foil_price : 0), 0) };
  }
}

/* A MESMA impressão pode estar nas duas metades — uma comum que lhe falte em
   normal E em foil —, por isso a chave de uma linha é (impressão, acabamento),
   nunca só a impressão. */
function feItem(pid, foil) {
  for (const s of state.faltasEdicao?.sets || []) {
    for (const g of feBlocosTodos(s)) {
      if ((g.id === 'foil') !== !!foil) continue;
      const x = g.items.find(it => it.printing_id === pid);
      if (x) return x;
    }
  }
  return null;
}

/* O clique no `+`/`−`: ecrã otimista e pedidos da MESMA linha em fila, como no
   separador «Encomendas» (é a mesma rota e a mesma tabela). Só o último em voo
   aceita o número do servidor, senão uma resposta atrasada punha o contador
   para trás.

   A LINHA NÃO SAI DA LISTA: mexe-se no `pending` e no `missing` do item, e o
   item fica onde estava. É o pedido dele — «fica bem mais fácil para eu
   visualizar». */
async function feAjustar(pid, foil, delta) {
  if (!state.editable) return;
  const x = feItem(pid, foil);
  if (!x) return;
  const antes = { pending: x.pending || 0, missing: x.missing, total: x.total };
  if (delta < 0 && antes.pending <= 0) return;
  feAplicar(x, Math.max(0, Math.min(antes.pending + delta, x.short)));
  feDesenharLinha(pid, foil);

  const chave = `${pid}|${foil ? 1 : 0}`;
  state.feVoo.set(chave, (state.feVoo.get(chave) || 0) + 1);
  const fila = state.feFila.get(chave) || Promise.resolve();
  const tarefa = fila.then(async () => {
    const r = await fetch('api/encomenda', {
      method: 'POST', headers: cabecalhos(),
      body: JSON.stringify({ printing_id: pid, delta, foil: !!foil }),
    });
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error || `HTTP ${r.status}`);
    return r.json();
  });
  state.feFila.set(chave, tarefa.catch(() => {}));
  try {
    const res = await tarefa;
    const resto = (state.feVoo.get(chave) || 1) - 1;
    state.feVoo.set(chave, resto);
    if (resto === 0) {
      feAplicar(x, Math.min(res.open_printing || 0, x.short));
      feDesenharLinha(pid, foil);
      feMarcaVelhos();
    }
    toast(`${res.open_printing} a caminho de ${x.name}${foil ? ' (foil)' : ''}`, { ms: 2500 });
  } catch (err) {
    state.feVoo.set(chave, Math.max(0, (state.feVoo.get(chave) || 1) - 1));
    x.pending = antes.pending; x.missing = antes.missing; x.total = antes.total;
    feDesenharLinha(pid, foil);
    toast(`Não gravou: ${err.message}`, { error: true });
  }
}

/* O pendente muda, o que falta COMPRAR muda com ele — e o `short` (o que falta
   na caixa) não, que é o que mantém a linha na lista. */
function feAplicar(x, pending) {
  x.pending = pending;
  x.missing = Math.max(0, x.short - pending);
  x.total = (x.price || 0) * x.missing;
}

/* Redesenha só o tile que mexeu, e acerta os números à volta: os cabeçalhos da
   edição e do bloco, o do separador, os separadores de edição e a caixa da
   wantlist (de onde a linha encomendada saiu). */
function feDesenharLinha(pid, foil) {
  feRecontar();
  const sel = `.dtile[data-fe-pid="${CSS.escape(pid)}"][data-fe-foil="${foil ? 1 : 0}"]`;
  const el = document.querySelector(`#fe-body ${sel}`);
  const x = feItem(pid, foil);
  if (el && x) { el.outerHTML = feTile(x); ligarFeEnc(); }
  feAcertarResumos();
  renderFeTabs();
}

/* A caixa do Cardmarket de um bloco (ou de uma CAIXA, com `s` a `null`): o
   cabeçalho dela e o texto, depois de uma linha ter saído por ter sido
   encomendada. */
function feAcertarWantlist(s, g) {
  const zona = document.getElementById(feWlId(s, g));
  if (!zona) return;
  const w = g.wantlist || {};
  const h = zona.querySelector('.fe-wl-head span');
  if (h) {
    h.innerHTML = `${plural(w.lines, 'linha', 'linhas')} ·
      ${plural(w.copies, 'cópia', 'cópias')} · ${eur(w.cents)}`;
  }
  cmMostrar(feWlId(s, g) + '-cm', feWantlistItens(g), false,
            { foco: false, copiar: false, foilTodas: g.id === 'foil' });
}

/* Os `<span>` dos cabeçalhos e as caixas do Cardmarket, sem redesenhar a
   grelha inteira — redesenhá-la a cada clique fazia as imagens todas piscar. */
function feAcertarResumos() {
  const p = state.faltasEdicao;
  const sel = state.prefs.feSet;
  const cx = feCaixa();
  if (cx) {
    $('#fe-head').innerHTML = feCaixaCabecalho(cx);
    const r = document.querySelector(`#fe-body [data-fe-res="caixa:${CSS.escape(cx.id)}"]`);
    if (r) r.innerHTML = feResumo(cx);
    feAcertarWantlist(null, cx);
    return;
  }
  for (const s of p.sets.filter(x => sel === 'all' || x.set === sel)) {
    const cab = document.querySelector(`#fe-body [data-fe-res="set:${CSS.escape(s.set)}"]`);
    if (cab) cab.innerHTML = feResumo(s);
    for (const g of feBlocosTodos(s)) {
      const c = document.querySelector(
        `#fe-body [data-fe-res="bloco:${CSS.escape(s.set)}:${CSS.escape(g.id)}"]`);
      if (c) c.innerHTML = feResumo(g);
      feAcertarWantlist(s, g);
    }
  }
  // O cabeçalho do separador: os números grandes e o resumo das foils.
  const t = p.totals, tl = p.totals_lists;
  const th = $('#fe-head .deck-title .prio');
  if (th) {
    th.textContent = `${plural(t.cards, 'impressão', 'impressões')} · ${
      plural(t.copies, 'cópia', 'cópias')}`;
  }
  const metas = document.querySelectorAll('#fe-head > .deck-card > .deck-meta span');
  if (metas[0]) metas[0].innerHTML = `<i>Fechar os ${feQuantos()} blocos</i>${eur(t.cents)}`;
  if (metas[1]) {
    metas[1].innerHTML = `<i>Wantlist geral (${escapeHTML(
      p.blocks.filter(b => b.in_lists).map(b => b.label).join(' + '))})</i>${
      eur(tl.cents)} · ${plural(tl.copies, 'cópia', 'cópias')}`;
  }
  const fr = $('#fe-head .fe-foil-resumo .deck-meta span');
  if (fr && p.foil) fr.innerHTML = `<i>Foils — complemento</i>${feResumo(p.foil.totals)}`;
}

function feQuantos() {
  const n = state.faltasEdicao.blocks.length;
  return { 3: 'três', 4: 'quatro', 5: 'cinco' }[n] || String(n);
}

function ligarFeEnc() {
  for (const b of document.querySelectorAll('#fe-body .fe-enc-bot .step')) {
    const t = b.closest('.dtile');
    b.onclick = () => feAjustar(t.dataset.fePid, t.dataset.feFoil === '1',
                                Number(b.dataset.feD));
  }
}

/* Uma encomenda mudou: as outras páginas que descontam o pendente ficam
   velhas. O gémeo do `encMarcaVelhos`, visto do outro lado — aqui é o
   separador «Encomendas» que tem de ser relido, porque o número é o mesmo. */
function feMarcaVelhos() {
  state.decks = null;
  state.compras = null;
  state.wantlist = null;
  state.enc.payload = null;
  state.enc.resumo = null;
  state.colecaoVelha = true;
  wlDesatualizar();
}

/* A metade das FOILS de uma edição: a mesma forma de um bloco, com o rótulo
   da metade por cima para não se confundir com as faltas. */
function feFoilMetade(s) {
  const g = s.foil;
  if (!g) return `<p class="fe-metade foil">Foils — <b>esta edição não tem
    impressões com contagem de foil</b> (fora do âmbito).</p>`;
  return `<p class="fe-metade foil">Foils — <b>complemento</b> · não são faltas</p>
    <h3 class="section-head sub fe-bloco foil fe-ver">${escapeHTML(g.label)}
      <small>${escapeHTML(g.target_label)} · wantlist própria</small>
      <span data-fe-res="bloco:${escapeAttr(s.set)}:${escapeAttr(g.id)}">${feResumo(g)}</span></h3>
    ${g.items.length
      ? `<div class="grid deck-grid fe-grid">${g.items.map(feTile).join('')}</div>`
      : `<p class="empty fe-vazio">${g.scope
          ? 'Tens o playset em foil de tudo o que pode existir em foil nesta edição.'
          : 'Esta edição não tem impressões com contagem de foil.'}</p>`}
    ${feWantlistHTML(s, g)}`;
}

/* O que o cabeçalho diz das foils: a conta à parte, o âmbito, e o AVISO das
   impressões em que a foil está a tapar um buraco das normais. Nada disto
   soma aos números de cima — é o que ele quis dizer com «complemento». */
function feFoilCabecalho(f) {
  if (!f) return '';
  const t = f.totals, s = f.scope, av = f.aviso_normais || [];
  return `<div class="fe-foil-resumo">
    <div class="deck-meta">
      <span><i>Foils — complemento</i>${feResumo(t)}</span>
      <span><i>Tens</i>${plural(s.owned, 'foil', 'foils')} em ${s.owned_printings} de ${
        plural(s.printings, 'impressão', 'impressões')} · alvo ${s.target}</span>
    </div>
    <small class="nota">As foils <b>não são faltas</b> — são complemento e
      indicativo, e têm <b>wantlist própria</b>. Não entram na contagem de
      faltas aqui em cima, na percentagem da Coleção, nos três níveis nem nas
      listas de compra que já existem. O alvo é o <b>playset do tipo</b>
      (Unit/Spell/Gear 3, Battlefield 1, <b>Rune 12</b>) e só se listam
      ${escapeHTML((s.rarities || []).map(r => (s.rarity_labels || {})[r] || r).join(' e ')
        .toLowerCase())}${s.sem_edicoes && s.sem_edicoes.length
        ? `, fora ${escapeHTML(s.sem_edicoes.join(', '))}` : ''}: de rara para cima as
      cartas só existem em foil — a carta normal <i>é</i> a foil, e listá-las era
      duplicar a coleção.
      O preço é o da <b>foil</b> no CardTrader${t.no_foil_price
        ? ` — ${plural(t.no_foil_price, 'linha', 'linhas')} conta${
            t.no_foil_price === 1 ? '' : 'm'} ao preço da normal por não haver oferta
          foil, por isso o total é um <b>piso</b>` : ''}.
      O texto da wantlist não leva marca de foil: liga o filtro <i>Foil</i> em cada
      entrada depois de colares.</small>
    ${av.length ? `<details class="fe-aviso"><summary>${plural(av.length,
        'impressão', 'impressões')} com foil e o playset das <b>normais</b> ainda
        incompleto — a foil está a tapar o buraco</summary>
      <ul>${av.map(x => `<li><code>${escapeHTML((x.code || '').split('/')[0])}</code>
        ${escapeHTML(x.name)} — normais <b>${x.normais}/${x.target}</b> · ${
        plural(x.foil, 'foil', 'foils')}</li>`).join('')}</ul>
      <p class="nota">O tile da Coleção diz <code>${av[0].target}/${av[0].target}</code>
        porque a foil conta para o master set desde 2026-09-26; em normais faltam-te
        as que aqui se dizem. Não muda regra nenhuma — está aqui para se ver.</p>
    </details>` : ''}
  </div>`;
}

/* A wantlist de um bloco é só o que há a COMPRAR — o que vem a caminho está
   nos tiles, marcado, e não vai para o Cardmarket (a da Coleção faz o mesmo).
   Gémeo do `faltas_edicao.wantlist` em Python; há teste que compara o texto. */
function feWantlistItens(g) {
  return g.items.filter(x => x.missing > 0);
}

/* `s` a `null` é uma CAIXA (2026-10-02): a lista dela não é de uma edição, e
   por isso o id e o título saem do id da caixa. */
function feWlId(s, g) {
  return s ? `fe-wl-${s.set}-${g.id}` : `fe-wl-cx-${g.id}`;
}

function feWantlistHTML(s, g) {
  const itens = feWantlistItens(g);
  if (!itens.length) return '';
  const w = g.wantlist || {};
  // Numa caixa o rótulo basta — o âmbito («4 edições», «a edição inteira») já
  // está no cabeçalho da página, e repeti-lo aqui dava «Wantlist — VEN — tudo ·
  // a edição inteira · 4 blocos», que são três traços para uma lista.
  const titulo = s ? `${escapeHTML(s.name)} · ${escapeHTML(g.label)}`
                   : escapeHTML(g.label);
  return `<section class="wl-bloco fe-wl" id="${feWlId(s, g)}">
    <h4 class="wl-head fe-wl-head">Wantlist — ${titulo}
      <span>${plural(w.lines != null ? w.lines : itens.length, 'linha', 'linhas')} ·
        ${plural(w.copies != null ? w.copies : itens.reduce((n, x) => n + cmQtd(x), 0), 'cópia', 'cópias')}
        · ${eur(w.cents != null ? w.cents : itens.reduce((n, x) => n + (x.total || 0), 0))}</span></h4>
    ${cmZonaHTML(feWlId(s, g) + '-cm')}
  </section>`;
}

/* Um tile: a arte, «faltam N» no canto (ou «a caminho» quando o pendente
   cobre tudo), o total no outro canto, «tens H/T» em baixo.

   Nas FOILS (2026-09-27) o mesmo tile diz «tens H/T foil» e, quando o preço
   veio da normal por não haver oferta foil, marca-o com «normal» — é o PISO.
   Não há segundo tile: é a mesma pergunta («quantas faltam») sobre a outra
   contagem. O preço NÃO leva a palavra «foil»: o bloco inteiro é de foils e o
   crachá já o diz, e a 375 px a linha do código é elidida — a palavra a mais
   cortava o preço, que é o que ali interessa. A marca do piso fica, porque é
   a excepção. */
function feTile(x) {
  const cls = (x.missing > 0 ? 'gone' : 'a-caminho') + (x.foil ? ' fe-foil' : '')
    + (x.pending ? ' fe-enc' : '');
  const crachá = x.missing > 0 ? `faltam ${x.missing}` : 'a caminho';
  const piso = x.foil && x.price != null && !x.price_is_foil;
  return `<div class="dtile ${cls}" data-fe-pid="${escapeAttr(x.printing_id)}"
       data-fe-foil="${x.foil ? '1' : '0'}">
    ${artHTML(x, `<span class="need">${crachá}</span>
      <span class="ja-tens">tens ${x.have}/${x.target}${x.foil ? ' foil' : ''}</span>
      ${x.price != null && x.missing > 0 ? `<span class="price">${eurShort(x.total)}</span>` : ''}
      ${x.pending ? `<span class="enc-n" title="${x.pending} já encomendada${
        x.pending === 1 ? '' : 's'}">+${x.pending}</span>` : ''}`)}
    <div class="tname" title="${escapeAttr(x.name)}">${escapeHTML(x.name)}${
      x.label && x.label !== 'Base' ? ` <i class="var">${escapeHTML(x.label)}</i>` : ''}</div>
    <div class="codigo">${escapeHTML((x.code || '').split('/')[0])}${
      x.price != null ? ` · ${eur(x.price)}${piso
        ? ' <i class="piso" title="Não há oferta foil no CardTrader: esta linha conta ao preço da NORMAL, por isso o total é um piso.">normal</i>'
        : ''}` : ' · sem preço'}</div>
    ${feEncHTML(x)}
  </div>`;
}

/* Os `+`/`−` de «já encomendei» (André, 2026-09-27: *"nas faltas, coloca o + e
   - para eu indicar que ja encomendei, fica bem mais facil para eu visualizar
   assim"*).

   SÃO OS MESMOS BOTÕES DAS ENCOMENDAS, não um contador novo: a mesma rota
   (`POST /api/encomenda`), a mesma tabela (`pending`), o mesmo número. Nas
   foils vai `foil: true`, para a cópia entrar no contador de foil quando
   chegar.

   A LINHA NUNCA DESAPARECE. O pendente desconta do «faltam», mas o item fica
   na lista — o tile passa a dizer as duas coisas, «faltam N» e «M já
   encomendadas», e só quando a encomenda cobre tudo é que o crachá vira «a
   caminho». O «Chegou» não está aqui: vive no separador «Encomendas», como
   desde 2026-09-17. */
function feEncHTML(x) {
  const n = x.pending || 0;
  const linha = n
    ? `<b>${n}</b> já encomendada${n === 1 ? '' : 's'}${
        x.missing > 0 ? ` · faltam ${x.missing}` : ' · nada por comprar'}`
    : 'nada encomendado';
  const botoes = state.editable ? `<div class="steppers fe-enc-bot">
      <button class="step minus" data-fe-d="-1" ${n ? '' : 'disabled'}
              aria-label="menos uma encomendada de ${escapeAttr(x.name)}"
              title="afinal não encomendei esta">−</button>
      <button class="step plus" data-fe-d="1"
              aria-label="marcar mais uma encomendada de ${escapeAttr(x.name)}"
              title="já encomendei mais uma${x.foil ? ' (foil)' : ''}">+</button>
    </div>` : '';
  return `${botoes}<div class="onde ${n ? 'caminho' : 'tenho'}">${linha}</div>`;
}


/* ====================================================== «A MAIS»

   André, 2026-09-17: "cria um botao que e o 'a mais' onde vai todas as cartas
   que estao listadas a mais ou que estavam num deck e deixaram de estar".
   Vem tudo do servidor (`api/a_mais.json`, `a_mais.payload`): por edição, dois
   blocos — o EXCEDENTE (mais cópias do que o alvo que a Coleção e os decks já
   usam: «tens 5, queres 3 -> 2 a mais») e as LIBERTADAS DOS DECKS (o que uma
   lista pedia e deixou de pedir, lido do registo `deck_need_log`, que nasceu
   nesta ordem e começa vazio). Só mostra: não muda alvos, não vende nada.

   Os tiles são os `dtile` das Faltas — a carta com imagem, o crachá no canto
   com o número que interessa (quantas a mais / quantas libertadas).       */

async function loadAMais(sub = '') {
  $('#am-body').innerHTML = '<p class="empty">a carregar…</p>';
  state.aMais = await getJSON('api/a_mais.json');
  if (sub && amSetValido(sub)) state.prefs.amSet = sub;
  renderAmTabs();
  renderAMais();
}

function renderAmTabs() {
  const nav = $('#am-tabs');
  const p = state.aMais;
  nav.innerHTML = '';
  const comBotao = p.sets.filter(s => s.button);
  if (state.prefs.amSet !== 'all' && !comBotao.some(s => s.set === state.prefs.amSet)) {
    state.prefs.amSet = 'all';
  }
  const botoes = [{ set: 'all', name: 'Todas', sub: amCurto(p.totals) },
                  ...comBotao.map(s => ({ ...s, sub: amCurto({ excedente: s.excedente, libertadas: s.libertadas }) }))];
  for (const s of botoes) {
    const b = document.createElement('button');
    const on = s.set === state.prefs.amSet;
    b.className = 'tab' + (on ? ' is-on' : '');
    b.setAttribute('aria-pressed', on ? 'true' : 'false');
    b.innerHTML = `${escapeHTML(s.name)}<small>${escapeHTML(s.sub)}</small>`;
    b.onclick = () => {
      state.prefs.amSet = s.set; savePrefs();
      escreverHash('a-mais', s.set);
      renderAmTabs(); renderAMais();
    };
    nav.appendChild(b);
  }
}

/* «12 a mais · 3 libertadas» — o resumo curto de uma edição ou do total. */
function amCurto(t) {
  const partes = [];
  if (t.excedente.copies) partes.push(`${t.excedente.copies} a mais`);
  if (t.libertadas.copies) partes.push(`${t.libertadas.copies} libertadas`);
  return partes.length ? partes.join(' · ') : 'nada a mais';
}

function renderAMais() {
  const p = state.aMais;
  const sel = state.prefs.amSet;
  // «Todas» inclui a edição sem botão (o OGS): um excedente que não se vê é o
  // contrário do que este separador é. Diz-se no cabeçalho dela.
  const sets = p.sets.filter(s => sel === 'all' || s.set === sel);
  const t = p.totals, h = p.history || {};
  const semBotao = p.sets.filter(s => !s.button).map(s => s.name);
  // As runas ficam de fora dos dois blocos (2026-09-17, à noite: «no a mais
  // nunca aparece Runas»). Diz-se quantas ficaram de fora, não se escondem.
  const sc = p.scope || {}, ru = sc.runas || {};
  const runasFora = sc.sem_runas && ((ru.excedente || {}).copies || (ru.libertadas || {}).copies)
    ? `<br>Sem runas, de propósito — organizas as runas à mão. Ficaram de fora ${
        plural(ru.excedente.copies, 'cópia', 'cópias')} a mais em ${
        plural(ru.excedente.cards, 'impressão', 'impressões')} de runa${
        ru.libertadas.copies ? ` e ${plural(ru.libertadas.copies, 'runa libertada', 'runas libertadas')} dos decks` : ''}.`
    : (sc.sem_runas ? '<br>Sem runas, de propósito — organizas as runas à mão.' : '');
  // OS FOILS NUNCA ENTRAM NO QUE SOBRA (2026-09-26, `foil.entra_no_a_mais`):
  // com eles a contar para a Coleção, 3 normais + 3 foil contra um alvo de 3
  // diriam «3 a mais», e ele não vende os foils. Ficam de fora, e diz-se.
  const fo = sc.foil || {};
  const foilFora = (!sc.foil_no_excedente && fo.copies)
    ? `<br><b>Os foils não entram no que sobra</b>: o excedente conta primeiro as
       normais. Ficaram de fora ${plural(fo.copies, 'cópia foil', 'cópias foil')} em ${
       plural(fo.printings, 'impressão', 'impressões')} — contam para a Coleção e
       para o valor, mas são peça de coleção, não excedente.`
    : '';

  $('#am-head').innerHTML = `<div class="deck-card">
    <div class="deck-title"><b>A mais</b>
      <span class="prio">${plural(t.excedente.copies, 'cópia', 'cópias')} a mais · ${
        plural(t.libertadas.copies, 'libertada', 'libertadas')} dos decks</span></div>
    <div class="deck-meta">
      <span><i>Excedente</i>${plural(t.excedente.cards, 'impressão', 'impressões')} · ${
        plural(t.excedente.copies, 'cópia', 'cópias')}</span>
      <span><i>Libertadas dos decks</i>${plural(t.libertadas.cards, 'carta', 'cartas')} · ${
        plural(t.libertadas.copies, 'cópia', 'cópias')}</span>
      <span><i>Registo dos decks</i>${h.since
        ? `desde ${h.since.slice(0, 10)} · ${plural(h.events, 'mudança', 'mudanças')}`
        : 'ainda vazio'}</span>
    </div>
    <small class="nota"><b>Excedente</b>: cópias acima do alvo que a Coleção e os decks
      já usam — playset na sequência, 1 nas artes alternativas e sobrenumeradas,
      e o que está escondido (tokens, signatures) não tem alvo. O que os decks
      levam nunca conta como a mais.
      <b>Libertadas dos decks</b>: o que uma lista pedia e deixou de pedir — o
      registo nasceu a 2026-09-17 e só sabe do que mudou desde então.
      Isto só mostra: não muda alvos nem contas, e não é uma lista de venda.${runasFora}${foilFora}${
      semBotao.length ? `<br>Sem botão próprio: ${semBotao.map(escapeHTML).join(', ')} — aparece em «Todas».` : ''}</small>
  </div>`;

  $('#am-body').innerHTML = sets.map(s => `
    <h2 class="section-head fe-set">${escapeHTML(s.name)}
      <span>${amResumo(s)}</span></h2>
    <h3 class="section-head sub fe-bloco am-excedente">Excedente
      <small>mais cópias do que o alvo</small>
      <span>${s.excedente.copies ? `<b>${plural(s.excedente.copies, 'cópia', 'cópias')}</b> a mais em ${
        plural(s.excedente.cards, 'impressão', 'impressões')}` : 'nada a mais'}</span></h3>
    ${s.excedente.items.length
      ? `<div class="grid deck-grid fe-grid">${s.excedente.items.map(amTile).join('')}</div>`
      : '<p class="empty fe-vazio">Nada acima do alvo nesta edição.</p>'}
    <h3 class="section-head sub fe-bloco am-libertadas">Libertadas dos decks
      <small>estavam numa lista e deixaram de estar</small>
      <span>${s.libertadas.copies ? `<b>${plural(s.libertadas.copies, 'cópia', 'cópias')}</b> de ${
        plural(s.libertadas.cards, 'carta', 'cartas')}` : 'nenhuma'}</span></h3>
    ${s.libertadas.items.length
      ? `<div class="grid deck-grid fe-grid">${s.libertadas.items.map(amLibTile).join('')}</div>`
      : `<p class="empty fe-vazio">${h.since
          ? 'Nenhum deck libertou cartas desta edição desde que há registo.'
          : 'O registo do que os decks pedem ainda está vazio — enche a partir da próxima vez que uma lista mudar.'}</p>`}`).join('');
}

function amResumo(s) {
  const partes = [];
  if (s.excedente.copies) partes.push(`<b>${s.excedente.copies}</b> a mais`);
  if (s.libertadas.copies) partes.push(`<b>${s.libertadas.copies}</b> libertadas`);
  return partes.length ? partes.join(' · ') : 'nada a mais';
}

/* Um tile do excedente: a arte, «N a mais» no canto, «tens H/T» em baixo, e
   de onde vem (Coleção / binder) e o que os decks levam. */
function amTile(x) {
  const origem = [x.from_colecao ? `${x.from_colecao} na Coleção` : '',
                  x.from_binder ? `${x.from_binder} no binder` : ''].filter(Boolean).join(' · ');
  return `<div class="dtile a-mais${x.hidden ? ' escondida' : ''}">
    ${artHTML(x, `<span class="need">${x.extra} a mais</span>
      <span class="ja-tens">tens ${x.have}/${x.hidden ? '–' : x.target}</span>`)}
    <div class="tname" title="${escapeAttr(x.name)}">${escapeHTML(x.name)}${
      x.label && x.label !== 'Base' ? ` <i class="var">${escapeHTML(x.label)}</i>` : ''}</div>
    <div class="codigo">${escapeHTML((x.code || '').split('/')[0])}${
      x.price != null ? ` · ${eur(x.price)}` : ''}</div>
    <div class="onde tenho">${escapeHTML(origem)}${
      x.used ? ` · ${x.used} nos decks` : ''}${
      x.hidden ? ` · <i>${escapeHTML(x.block_label)}, sem alvo</i>` : ''}</div>${
    x.foil ? `<div class="onde tenho fo-fora"><b class="fo">${x.foil} foil</b> —
      não entram no que sobra</div>` : ''}
  </div>`;
}

/* Um tile das libertadas: a carta, «N libertadas» no canto, de que deck saiu
   e quando, e quem ainda a pede. */
function amLibTile(x) {
  const ainda = (x.still_wanted || []).map(d => `${escapeHTML(deckCurto(d.deck))} ${d.qty}`).join(' · ');
  return `<div class="dtile a-mais libertada">
    ${artHTML(x, `<span class="need">${x.qty} ${x.qty === 1 ? 'libertada' : 'libertadas'}</span>
      <span class="ja-tens">tens ${x.have}</span>`)}
    <div class="tname" title="${escapeAttr(x.name)}">${escapeHTML(x.name)}</div>
    <div class="codigo">${escapeHTML((x.code || '').split('/')[0])}${
      x.price != null ? ` · ${eur(x.price)}` : ''}</div>
    <div class="onde tenho" title="${escapeAttr(x.deck)}">saiu de ${
      escapeHTML(deckCurto(x.deck))} a ${escapeHTML((x.ts || '').slice(0, 10))}</div>
    <div class="onde ${ainda ? 'shared' : 'tenho'}">${ainda ? `ainda pedida: ${ainda}` : 'nenhum deck a pede'}</div>
  </div>`;
}


/* ========================================================== «VENDA» (2026-09-25)

   André: *"este separador permite-me marcar as cartas que estou a vender no
   momento para apresentar a conta a pessoa. todos os precos tem que ser o
   Trend do Cardmarket!"*.

   O PREÇO DE CADA LINHA É METIDO POR ELE. A app não tem preços do Cardmarket
   e não os pode ter (API deles fechada a novas candidaturas, site a responder
   403 a pedidos automáticos, terceiros pagos) — por isso a linha tem um campo
   em euros, o link para a página da carta lá, e o Trend fica guardado por
   impressão com a data. O preço do CardTrader aparece ao lado, ROTULADO, e
   nunca entra no total: uma linha por preencher vale ZERO e o total diz
   quantas faltam.

   Isto NÃO tira nada da coleção. Quem baixa cópias é o botão separado «marcar
   como vendidas», com confirmação — ver `venda.py`.

   Tudo vem e volta pelo servidor: cada `+`, cada Trend e cada «limpar»
   devolvem o payload inteiro (`api/venda.json`), que é pequeno (a venda tem
   linhas, não centenas). Não há estado otimista a manter em duas cópias. */

async function loadVenda() {
  $('#vd-body').innerHTML = '<p class="empty">a carregar…</p>';
  state.venda = await getJSON('api/venda.json');
  renderVenda();
}

/* Qualquer escrita devolve o payload novo — uma resposta, um desenho. */
async function vdPost(url, corpo) {
  const r = await fetch(url, {
    method: 'POST', headers: cabecalhos(),
    body: JSON.stringify(corpo || {}),
  });
  const res = await r.json().catch(() => ({}));
  if (!r.ok) { const e = new Error(res.error || `HTTP ${r.status}`); e.status = r.status; throw e; }
  state.venda = res;
  renderVenda();
  return res;
}

function renderVenda() {
  const p = state.venda;
  if (!p) return;
  const t = p.totals;
  const avisos = [];
  if (t.sem_trend) {
    avisos.push(`<b>${t.sem_trend === 1 ? 'Falta' : 'Faltam'} ${
      plural(t.sem_trend, 'linha', 'linhas')} sem Trend</b> — ${
      t.sem_trend === 1 ? 'vale' : 'valem'} zero no total.
      O preço do CardTrader <b>não</b> as substitui.`);
  }
  if (t.trend_velho) {
    avisos.push(`${plural(t.trend_velho, 'linha tem', 'linhas têm')} o Trend com mais de
      ${plural(p.trend_valido_dias, 'dia', 'dias')} — vale a pena confirmar antes de cobrar.`);
  }
  if (t.avisos_stock) {
    avisos.push(`${plural(t.avisos_stock, 'linha vende', 'linhas vendem')} mais cópias do
      que tens registadas.`);
  }
  if (t.em_decks) {
    avisos.push(`${plural(t.em_decks, 'carta está', 'cartas estão')} a ser usada por um
      deck montado.`);
  }

  $('#vd-head').innerHTML = `<div class="deck-card">
    <div class="deck-title"><b>Venda em curso</b>
      <span class="prio">${plural(t.copies, 'carta', 'cartas')} · ${
        plural(t.lines, 'linha', 'linhas')}</span></div>
    <div class="deck-meta">
      <span><i>Total</i><b class="vd-total">${eur(t.cents)}</b></span>
      <span><i>Preços</i>Trend do Cardmarket, metido por ti</span>
      <span><i>Coleção</i>não mexe até carregares em «marcar como vendidas»</span>
    </div>
    ${avisos.length ? `<small class="nota vd-avisos">${avisos.join('<br>')}</small>` : ''}
    ${vdOrigens(t)}
  </div>`;

  $('#vd-juntar').innerHTML = state.editable ? `
    <div class="vd-procura">
      <label class="vlbl" for="vd-q">Juntar carta à venda</label>
      <input id="vd-q" type="search" placeholder="nome ou código (Defy, OGN-045)…"
             autocomplete="off">
      <div id="vd-res" class="vd-res"></div>
    </div>` : '';
  if (state.editable) vdLigarProcura();

  $('#vd-body').innerHTML = p.items.length
    ? `<div class="vd-linhas">${p.items.map(vdLinha).join('')}</div>`
    : `<p class="empty">A venda está vazia. ${state.editable
        ? 'Procura a carta aqui em cima, ou carrega em «vender» no tile dela, na Coleção.'
        : 'Não havia nada em venda quando este site foi gerado.'}</p>`;
  vdLigarLinhas();
  renderVdConta();
}

/* AS LINHAS QUE VIERAM DE UM DECK (André, 2026-09-27): *"se eu 'desfazer' o
   deck ou deixar de ser o principal, essas cartas passam a venda (apenas se
   valerem pelo menos 0,50 euros)"*.

   Vê-se de onde vieram e tiram-se de uma vez — entrar na Venda **não é
   vender**: é uma marcação, e ele tira de lá o que quiser. O «limpar» com
   origem deixa intactas as linhas que ele marcou à mão. */
function vdOrigens(t) {
  const lst = t.origens || [];
  if (!lst.length) return '';
  return `<div class="vd-origens">${lst.map(o => `
    <div class="vd-origem">
      <span><b>${o.copies}</b> ${o.copies === 1 ? 'cópia veio' : 'cópias vieram'} de
        <b>${escapeHTML(deckCurto(o.deck || o.slug || ''))}</b> deixar de ser o deck
        principal${o.cents ? ` · ${eur(o.cents)}` : ''}</span>
      ${state.editable ? `<button class="btn ghost" data-vd-origem="${escapeAttr(o.origem)}">
        Tirar as deste deck</button>` : ''}
    </div>`).join('')}
    <small class="nota">São cópias <b>próprias</b> desse deck (não da Coleção) que
      valiam pelo menos o mínimo. <b>Continuam no deck</b>: entrar na Venda não é
      vender, e quem baixa cópias é o «marcar como vendidas».</small>
  </div>`;
}

/* Uma linha: a carta, os `+`/`−` da quantidade, o campo do TREND (dele), o
   preço do CardTrader ao lado — rotulado, e fora da conta — e os links para
   o Cardmarket. */
function vdLinha(x) {
  // As classes levam o prefixo `vd-`: `aviso` sozinha é uma caixa de texto do
  // resto do site (com `max-width: 62ch`) e encolhia a linha a meio da lista.
  const cls = [x.a_mais_do_que_tens ? 'vd-alerta' : '',
               x.trend == null ? 'vd-st' : ''].join(' ');
  const trend = x.trend == null ? '' : (x.trend / 100).toFixed(2);
  const marcas = [];
  if (x.a_mais_do_que_tens) {
    marcas.push(`<span class="vd-marca av">só tens ${x.have}</span>`);
  }
  if (x.em_decks.length) {
    marcas.push(`<span class="vd-marca deck">${escapeHTML(x.em_decks.map(deckCurto).join(' · '))}</span>`);
  }
  if (x.trend != null && x.trend_velho) {
    marcas.push(`<span class="vd-marca velho">Trend de há ${plural(x.trend_dias, 'dia', 'dias')}</span>`);
  }
  // DE ONDE VEIO (2026-09-27): esta linha não foi ele que a marcou — veio de
  // um deck que deixou de ser principal, e o preço que a pôs aqui é este.
  if (x.origem_deck) {
    marcas.push(`<span class="vd-marca origem" title="${escapeAttr(
      'cópia própria deste deck; entrou por valer pelo menos o mínimo. '
      + 'Entrar na Venda não é vender — nada saiu do deck.')}">do deck ${
      escapeHTML(deckCurto(x.origem_deck))}${x.preco_criterio != null
        ? ` · ${eur(x.preco_criterio)}${x.criterio_foil ? ' foil' : ''}` : ''}</span>`);
  }
  return `<div class="vd-linha ${cls}" data-pid="${escapeAttr(x.printing_id)}">
    ${artHTML(x, `<span class="need">${x.qty}×</span>`)}
    <div class="vd-meio">
      <div class="tname" title="${escapeAttr(x.name)}">${escapeHTML(x.name)}${
        x.label && x.label !== 'Base' ? ` <i class="var">${escapeHTML(x.label)}</i>` : ''}</div>
      <div class="codigo">${escapeHTML((x.code || '').split('/')[0])} ·
        ${escapeHTML(x.set_name)}</div>
      <div class="vd-links">
        <a href="${escapeAttr(x.url)}" target="_blank" rel="noreferrer noopener">Cardmarket</a>
        <a href="${escapeAttr(x.url_busca)}" target="_blank" rel="noreferrer noopener"
           class="alt">procurar</a>
        <span class="vd-ct" title="a oferta mais barata do CardTrader — não é um Trend e
          não entra na conta">${x.price != null ? eur(x.price) : '—'} <i>CardTrader, só referência</i></span>
      </div>
      ${marcas.length ? `<div class="vd-marcas">${marcas.join('')}</div>` : ''}
    </div>
    <div class="vd-dir">
      ${state.editable ? `<div class="steppers">
        <button class="step minus" data-vd="-1" aria-label="menos uma de ${escapeAttr(x.name)}">−</button>
        <b>${x.qty}</b>
        <button class="step plus" data-vd="1" aria-label="mais uma de ${escapeAttr(x.name)}">+</button>
      </div>` : `<div class="vd-qtd">${x.qty}×</div>`}
      <label class="vd-trend">
        <span>Trend €</span>
        ${state.editable
          ? `<input type="number" inputmode="decimal" step="0.01" min="0" value="${trend}"
                    data-trend placeholder="—" aria-label="Trend do Cardmarket de ${escapeAttr(x.name)}">`
          : `<b>${x.trend != null ? eur(x.trend) : '—'}</b>`}
      </label>
      <div class="vd-sub">${x.trend != null ? eur(x.subtotal) : '<i>sem Trend</i>'}</div>
    </div>
  </div>`;
}

function vdLigarLinhas() {
  for (const b of document.querySelectorAll('#vd-head [data-vd-origem]')) {
    b.onclick = () => vdLimparOrigem(b.dataset.vdOrigem);
  }
  for (const b of document.querySelectorAll('#vd-body .step[data-vd]')) {
    b.onclick = () => vdAjustar(b.closest('.vd-linha').dataset.pid, Number(b.dataset.vd));
  }
  for (const i of document.querySelectorAll('#vd-body input[data-trend]')) {
    // No `change` (Enter ou sair do campo), não a cada tecla: gravar a meio de
    // «12,5» punha lá 12 e redesenhava a linha por baixo dos dedos dele.
    i.onchange = () => vdTrend(i.closest('.vd-linha').dataset.pid, i.value);
    i.onkeydown = e => { if (e.key === 'Enter') i.blur(); };
  }
}

/* O «+ venda» do tile da Coleção. Não desenha a secção Venda (ele está na
   Coleção); marca-a por reler e diz no toast o que aconteceu, com um atalho
   para lá ir. */
async function venderDaGrelha(pid, nome) {
  try {
    const r = await fetch('api/venda/linha', {
      method: 'POST', headers: cabecalhos(),
      body: JSON.stringify({ printing_id: pid, delta: 1 }),
    });
    const res = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(res.error || `HTTP ${r.status}`);
    state.venda = res;
    const n = (res.items.find(x => x.printing_id === pid) || {}).qty || 1;
    toast(`${nome || 'carta'}: ${n} na venda · ${res.totals.lines} linhas`, {
      action: { label: 'ver a venda', run: () => showSection('venda') },
    });
  } catch (err) { toast(err.message, { error: true }); }
}

async function vdAjustar(pid, delta) {
  try {
    await vdPost('api/venda/linha', { printing_id: pid, delta });
  } catch (err) { toast(err.message, { error: true }); }
}

async function vdTrend(pid, valor) {
  try {
    await vdPost('api/venda/trend', { printing_id: pid, eur: valor });
  } catch (err) { toast(err.message, { error: true }); }
}

/* Tira de uma vez as linhas que vieram de um deck. Não mexe nas cópias: elas
   continuam próprias do deck, como sempre estiveram. */
async function vdLimparOrigem(origem) {
  try {
    const res = await vdPost('api/venda/limpar', { origem });
    toast(`${plural(res.limpas, 'linha saiu', 'linhas saíram')} da venda — as cópias
      continuam no deck.`);
  } catch (err) { toast(err.message, { error: true }); }
}

/* A procura: só no modo edição (o site publicado não tem servidor para
   responder). Devolve impressões do catálogo inteiro — é a única maneira de
   juntar uma carta de uma edição que não esteja aberta na Coleção. */
function vdLigarProcura() {
  const cx = $('#vd-q');
  let t = null;
  cx.addEventListener('input', () => {
    clearTimeout(t);
    t = setTimeout(() => vdProcurar(cx.value.trim()), 200);
  });
}

async function vdProcurar(q) {
  const alvo = $('#vd-res');
  if (!alvo) return;
  if (q.length < 2) { alvo.innerHTML = ''; return; }
  try {
    const r = await getJSON('api/venda/procurar?q=' + encodeURIComponent(q));
    alvo.innerHTML = r.items.length
      ? r.items.map(x => `<button type="button" class="vd-hit" data-pid="${escapeAttr(x.printing_id)}">
          <span class="nm">${escapeHTML(x.name)}${x.label && x.label !== 'Base'
            ? ` <i class="var">${escapeHTML(x.label)}</i>` : ''}</span>
          <span class="cd">${escapeHTML((x.code || '').split('/')[0])} · ${escapeHTML(x.set_name)}
            · tens ${x.have}${x.na_venda ? ` · ${x.na_venda} na venda` : ''}</span>
        </button>`).join('')
      : '<p class="empty">Nada com esse nome ou código.</p>';
    for (const b of alvo.querySelectorAll('.vd-hit')) {
      b.onclick = async () => {
        await vdAjustar(b.dataset.pid, 1);
        $('#vd-q').value = '';
        $('#vd-res').innerHTML = '';
        $('#vd-q').focus();
      };
    }
  } catch (err) { alvo.innerHTML = `<p class="empty">${escapeHTML(err.message)}</p>`; }
}

/* A CONTA, limpa, para virar o ecrã para quem compra: nome, edição, número,
   quantidade, Trend unitário, subtotal e o total. A 375 px cada linha vira
   cartão (as colunas de uma tabela de seis não cabem num telemóvel). */
function renderVdConta() {
  const p = state.venda;
  const t = p.totals;
  if (!p.items.length) { $('#vd-conta').innerHTML = ''; return; }
  const linhas = p.items.map(x => `<tr${x.trend == null ? ' class="r-sem"' : ''}>
    <td class="v-nome" data-l="Carta">${escapeHTML(x.name)}</td>
    <td data-l="Edição">${escapeHTML(x.set)}</td>
    <td data-l="Nº">${escapeHTML((x.code || '').split('/')[0])}</td>
    <td data-l="Qtd">${x.qty}×</td>
    <td data-l="Trend">${x.trend != null ? eur(x.trend) : '<i>sem Trend</i>'}</td>
    <td data-l="Subtotal" class="v-sub">${x.trend != null ? eur(x.subtotal) : '—'}</td>
  </tr>`).join('');

  $('#vd-conta').innerHTML = `
    <h3 class="section-head sub vd-cab">A conta<small>para mostrar a quem compra</small>
      <span>${eur(t.cents)}</span></h3>
    <div class="vd-conta">
      <table class="vd-tab">
        <thead><tr><th>Carta</th><th>Edição</th><th>Nº</th><th>Qtd</th>
          <th>Trend</th><th>Subtotal</th></tr></thead>
        <tbody>${linhas}</tbody>
        <tfoot><tr><td colspan="4" data-l="Total">TOTAL</td>
          <td data-l="Cartas">${t.copies}×</td>
          <td class="v-tot" data-l="Total">${eur(t.cents)}</td></tr></tfoot>
      </table>
      ${t.sem_trend ? `<p class="vd-falta">${plural(t.sem_trend, 'linha', 'linhas')}
        sem Trend — ${t.sem_trend === 1 ? 'não está' : 'não estão'} no total.</p>` : ''}
      <p class="vd-fonte">Preços: <b>Trend do Cardmarket</b>.</p>
    </div>
    <div class="wl-zona vd-botoes">
      <button class="btn" id="vd-copiar">Copiar a conta</button>
      ${state.editable ? `<button class="btn ghost" id="vd-limpar">Limpar a venda</button>
        <button class="btn perigo" id="vd-vender">Marcar como vendidas</button>` : ''}
      <textarea id="vd-txt" class="wl-txt" readonly hidden></textarea>
      <small class="nota" id="vd-nota" hidden></small>
    </div>`;

  $('#vd-copiar').onclick = () => {
    const tx = $('#vd-txt'), nt = $('#vd-nota');
    tx.value = p.texto;
    tx.rows = Math.min(16, Math.max(4, p.texto.split('\n').length));
    tx.hidden = false; nt.hidden = false;
    tx.focus(); tx.select();
    nt.textContent = 'A conta está aqui — copia com Ctrl+C (no telemóvel, toca e mantém).';
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(tx.value)
        .then(() => { nt.textContent = 'Conta copiada.'; }).catch(() => {});
    }
  };
  if (!state.editable) return;

  $('#vd-limpar').onclick = async () => {
    if (!confirm(`Limpar a venda (${plural(t.lines, 'linha', 'linhas')})? `
                 + 'Não mexe na coleção, e os Trends ficam guardados.')) return;
    try { await vdPost('api/venda/limpar'); toast('Venda limpa.'); }
    catch (err) { toast(err.message, { error: true }); }
  };

  // «Marcar como vendidas» é o único botão desta página que mexe na coleção:
  // pede confirmação, diz o que vai baixar, e o servidor recusa sem o
  // `confirmar` (409). Não é automático em circunstância nenhuma.
  $('#vd-vender').onclick = async () => {
    const aviso = `Marcar como vendidas?\n\n`
      + `Isto BAIXA ${plural(t.copies, 'cópia', 'cópias')} da coleção`
      + (t.sem_trend ? `\n${plural(t.sem_trend, 'linha', 'linhas')} sem Trend — vão a zero.` : '')
      + `\n\nTotal a cobrar: ${eur(t.cents).replace(/ /g, ' ')}`;
    if (!confirm(aviso)) return;
    try {
      const res = await vdPost('api/venda/vender', { confirmar: true });
      const v = res.vendida;
      toast(`Vendidas ${plural(v.copies, 'cópia', 'cópias')} · ${eur(v.totals.cents)}`
            + (v.em_falta ? ` (faltaram ${v.em_falta})` : ''), { ms: 9000 });
      // As cópias baixaram: a Coleção, as listas de compra e os decks ficam
      // por reler, como depois de um «Chegou» das Encomendas.
      state.colecaoVelha = true;
      wlDesatualizar();
      state.compras = null; state.faltasEdicao = null; state.aMais = null;
      state.decks = null; state.enc.payload = null; state.enc.resumo = null;
    } catch (err) { toast(err.message, { error: true }); }
  };
}


/* ================================================ «PRODUTO SELADO» (2026-09-25)

   André: *"faz uma lista, para acrescentar um separador que e 'Produto
   Selado', em que vai tudo o que e produtos de coleccao do Riftbound, como
   displays ou boxcase, ou duel decks, proving ground, etc etc, para eu saber
   o que ha, o que tenho e o que nao tenho"*.

   TRÊS ESTADOS, que é o que ele pediu: o que HÁ (a lista toda), o que TEM
   (unidades > 0) e o que NÃO TEM. Os contadores estão no topo e o filtro
   troca entre eles. Os que ainda NÃO SAÍRAM aparecem marcados e NÃO contam
   para o que falta.

   O SELADO NÃO ENTRA NA COLEÇÃO. Os `+`/`−` escrevem numa tabela à parte
   (`sealed_copies`) e não há nenhum número da Coleção que mexa com eles — o
   valor do selado é um total próprio, e está escrito no ecrã que é à parte.
   Ver `selado.py`.

   Como na Venda, cada escrita devolve o payload inteiro e redesenha: a lista
   tem dezenas de linhas, não centenas, e assim não há duas cópias do estado
   a divergir.                                                               */

const SL_FILTROS = [
  { id: 'all', rot: 'Tudo' },
  { id: 'tenho', rot: 'Tenho' },
  { id: 'falta', rot: 'Não tenho' },
  { id: 'porsair', rot: 'Por sair' },
];

async function loadSelado() {
  $('#sl-body').innerHTML = '<p class="empty">a carregar…</p>';
  state.selado = await getJSON('api/selado.json');
  renderSelado();
}

async function slPost(corpo, rota = 'api/selado/ajustar') {
  const r = await fetch(rota, {
    method: 'POST', headers: cabecalhos(),
    body: JSON.stringify(corpo),
  });
  const res = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(res.error || `HTTP ${r.status}`);
  state.selado = res;
  renderSelado();
  return res;
}

/* O filtro é do ECRÃ e não do servidor: a lista inteira vem no payload (são
   dezenas de produtos) e os contadores do topo contam sempre TUDO — é o que
   faz «o que há / o que tenho / o que não tenho» ser lido de uma vez. */
function slServe(x) {
  const f = state.prefs.selFiltro;
  if (f === 'tenho') return x.qty > 0;
  if (f === 'falta') return x.qty === 0 && !x.por_sair;
  if (f === 'porsair') return x.por_sair;
  return true;
}

function renderSelado() {
  const p = state.selado;
  if (!p) return;
  const t = p.totals;
  // Os ACESSÓRIOS (binders e deck boxes) são uma secção à parte com números
  // próprios: não entram no «o que há / tenho / não tenho» nem no valor do
  // selado. Ver `selado.py`.
  const at = (p.acessorios && p.acessorios.totals) || { ha: 0 };
  const q = (state.slQ || '').trim().toLowerCase();
  const casa = x => !q || `${x.nome} ${x.versao} ${x.edicao} ${x.tipo_label}`
    .toLowerCase().includes(q);

  const fora = (p.scope.fora || []).reduce((s, x) => s + x.n, 0);
  // O que ele mandou tirar (`selado.excluidos`). Diz-se quantos e quais: o
  // catálogo em disco está intacto e repor é tirar o nome da lista.
  const tirados = p.scope.excluidos || [];
  $('#sl-head').innerHTML = `<div class="deck-card">
    <div class="deck-title"><b>Produto selado</b>
      <span class="prio">${plural(t.copias, 'unidade', 'unidades')}</span></div>
    <div class="sl-nums">
      <span class="sl-num ha"><i>O que há</i><b>${t.ha}</b>
        <small>${t.saiu} já saíram${t.por_sair ? ` · ${t.por_sair} por sair` : ''}</small></span>
      <span class="sl-num tem"><i>Tenho</i><b>${t.tenho}</b>
        <small>${fmtPct(t.pct)} dos que saíram</small></span>
      <span class="sl-num falta"><i>Não tenho</i><b>${t.falta}</b>
        <small>sem contar os que ainda não saíram</small></span>
      <span class="sl-num val"><i>Valor do selado</i><b>${eur(t.valor_cents)}</b>
        <small>à parte do valor da Coleção</small></span>
    </div>
    <small class="nota">Lista do <b>CardTrader</b>${p.catalogo_em
      ? ` (${escapeHTML(String(p.catalogo_em).slice(0, 10))})` : ''} — as categorias
      de produto selado dele${t.do_config ? `, mais ${plural(t.do_config, 'produto', 'produtos')}
      do config` : ''}.
      ${at.ha ? `Os <b>${at.ha}</b> acessórios (binders e deck boxes) têm secção
        própria em baixo e <b>não contam</b> para estes números.` : ''}
      ${p.scope.juntos ? ` ${plural(p.scope.juntos, 'blueprint repetido', 'blueprints repetidos')}
        do CardTrader ${p.scope.juntos === 1 ? 'foi juntado' : 'foram juntados'} ao produto
        a que ${p.scope.juntos === 1 ? 'pertencia' : 'pertenciam'} — a linha di-lo.` : ''}
      ${slForaTexto(p.scope.fora)}
      ${t.preco_a_mao ? ` ${plural(t.preco_a_mao, 'produto tem', 'produtos têm')} o
        preço do <b>Cardmarket</b> metido por ti.` : ''}
      ${t.sem_preco ? ` <b>${t.sem_preco}</b> sem oferta no <b>CardTrader</b> — o preço
        da app vem só de lá, e o <b>Cardmarket responde 403</b> a pedidos automáticos:
        o preço de lá escreve-se à mão, na linha.` : ''}
      ${slLinksNota(p.links)}
      O selado <b>não entra</b> na Coleção — nem nos níveis, nem nas Faltas, nem no valor.</small>
    ${tirados.length ? `<details class="sl-tirados"><summary><b>${
      tirados.length}</b> ${tirados.length === 1 ? 'produto tirado' : 'produtos tirados'}
      por ti — não contam para estes números</summary>
      <small class="nota">Estão em <code>selado.excluidos</code>, no
        <code>riftvault_config.json</code>. <b>Nada foi apagado</b>: o catálogo em disco
        está intacto e <b>repor é tirar o nome da lista</b>.</small>
      <ul class="sl-tirados-lista">${tirados.map(x => `<li>${escapeHTML(x.nome)}
        <span class="dim">${escapeHTML(x.edicao || '—')} · ${
          escapeHTML(x.tipo_label)}</span></li>`).join('')}</ul></details>` : ''}
  </div>`;

  $('#sl-filtros').innerHTML = `
    <div class="seg" role="group" aria-label="Produto selado — o que mostrar">
      ${SL_FILTROS.map(f => `<button class="seg-btn${
        state.prefs.selFiltro === f.id ? ' is-on' : ''}" data-sl-filter="${f.id}">${
        f.rot}</button>`).join('')}
    </div>
    ${at.ha ? `<button class="btn${state.prefs.selAcess === false ? '' : ' is-on'}"
      id="sl-acess" aria-pressed="${state.prefs.selAcess === false ? 'false' : 'true'}">
      Acessórios (${at.ha})</button>` : ''}
    <input id="sl-q" type="search" placeholder="Procurar produto…" autocomplete="off"
           value="${escapeAttr(state.slQ || '')}">`;
  for (const b of document.querySelectorAll('#sl-filtros [data-sl-filter]')) {
    b.onclick = () => {
      state.prefs.selFiltro = b.dataset.slFilter;
      savePrefs();
      renderSelado();
    };
  }
  const ab = $('#sl-acess');
  if (ab) {
    ab.onclick = () => {
      state.prefs.selAcess = state.prefs.selAcess === false;
      savePrefs();
      renderSelado();
    };
  }
  const cx = $('#sl-q');
  if (cx) {
    cx.oninput = () => { state.slQ = cx.value; renderSeladoCorpo(); };
    cx.onkeydown = e => { if (e.key === 'Escape') { cx.value = ''; state.slQ = ''; renderSeladoCorpo(); } };
  }
  renderSeladoCorpo(casa);
}

function renderSeladoCorpo(casa) {
  const p = state.selado;
  if (!p) return;
  if (!casa) {
    const q = (state.slQ || '').trim().toLowerCase();
    casa = x => !q || `${x.nome} ${x.versao} ${x.edicao} ${x.tipo_label}`
      .toLowerCase().includes(q);
  }
  if (!p.items.length) {
    $('#sl-body').innerHTML = '<p class="empty">A lista está vazia. Corre '
      + '<code>riftvault selado --sync</code> no PC para a ir buscar ao CardTrader.</p>';
    return;
  }
  const grupos = sets => {
    let html = '';
    for (const g of sets) {
      const itens = g.items.filter(x => slServe(x) && casa(x));
      if (!itens.length) continue;
      const gt = g.totals;
      html += `<h3 class="section-head sub sl-cab">
        ${escapeHTML(g.label)}<small>${escapeHTML(g.set)}</small>
        <span>${gt.tenho}/${gt.saiu}${gt.por_sair ? ` · ${gt.por_sair} por sair` : ''}</span></h3>
        <div class="sl-lista">${itens.map(slLinha).join('')}</div>`;
    }
    return html;
  };
  let out = grupos(p.sets);
  const ac = p.acessorios;
  // A secção dos acessórios vem SEMPRE depois do selado e diz, no cabeçalho,
  // que não conta para ele — é a razão de estar à parte e não de estar cá.
  if (ac && ac.totals.ha && state.prefs.selAcess !== false) {
    const corpo = grupos(ac.sets);
    out += `<h2 class="section-head sl-acess-cab">Acessórios
      <small>binders e deck boxes — <b>não contam</b> para o produto selado</small>
      <span>${ac.totals.tenho}/${ac.totals.saiu} · ${eur(ac.totals.valor_cents)}</span></h2>
      ${corpo || '<p class="empty">Nada corresponde a este filtro.</p>'}`;
  }
  $('#sl-body').innerHTML = out
    || '<p class="empty">Nada corresponde a este filtro.</p>';
  slLigar();
}

/* As categorias que não entram na aba, contadas — e em DOIS grupos, porque
   são duas razões diferentes (2026-09-28): as que nunca foram produto selado
   (playmats, sleeves, memorabilia, oversized) e as que ELE tirou. Dizer que
   os 24 «Starter Decks» «não são produto selado» era falso: são, e foi ele
   que os tirou por não querer decks para colecionar. */
function slForaTexto(fora) {
  if (!fora || !fora.length) return '';
  const nome = x => `${x.n} ${escapeHTML(x.categoria.replace(/^Riftbound /, ''))}`;
  const nunca = fora.filter(x => !x.tirada);
  const tiradas = fora.filter(x => x.tirada);
  const p = [];
  if (nunca.length) {
    p.push(` <b>${nunca.reduce((s, x) => s + x.n, 0)}</b> ficam de fora
      (${nunca.map(nome).join(', ')}): não são produto selado nem acessório de
      coleção.`);
  }
  if (tiradas.length) {
    p.push(` <b>${tiradas.reduce((s, x) => s + x.n, 0)}</b> são produto selado
      que <b>tiraste</b> (${tiradas.map(nome).join(', ')}) — a categoria saiu do
      <code>selado.categorias</code>, e repor é escrevê-la outra vez.`);
  }
  return p.join('');
}

/* O PREÇO de uma linha do selado, e de onde ele veio.
   Um «—» seco lia-se «este produto não existe» — foi a queixa dele a 28/09.
   O que a app sabe é que o CARDTRADER não tem oferta, e que ela NÃO LÊ o
   Cardmarket (403); as duas coisas dizem-se, e o preço de lá tem um campo
   para ele o escrever, como o Trend da Venda. */
function slPreco(x) {
  const cm = x.preco_cm_cents != null;
  const linha = x.preco_fonte === 'cardmarket'
    ? `<div class="sl-preco cm">${eur(x.preco_cm_cents)}
         <i title="Escrito por ti — a app não lê o Cardmarket.">Cardmarket, à mão${
           x.preco_cm_dia ? ` · ${escapeHTML(x.preco_cm_dia)}` : ''}</i></div>`
    : x.preco_fonte === 'cardtrader'
      ? `<div class="sl-preco">${eur(x.preco_cents)}<i>CardTrader</i>
           ${cm ? `<i class="cm2" title="Escrito por ti. O preço que conta é o do
             CardTrader, que é medido.">Cardmarket ${eur(x.preco_cm_cents)}</i>` : ''}</div>`
      : `<div class="sl-preco vazio"><b>sem oferta</b>
           <i>no CardTrader · a app não lê o Cardmarket</i></div>`;
  if (!state.editable) return linha;
  return `${linha}
    <div class="sl-cm" title="O preço do Cardmarket, em euros. A app não o pode ir
      buscar (403): escreve-o tu, como o Trend da Venda. Em branco, apaga.">
      <label>Cardmarket <input type="text" inputmode="decimal" class="sl-cm-in"
        value="${cm ? escapeAttr((x.preco_cm_cents / 100).toFixed(2)) : ''}"
        placeholder="€" size="5" aria-label="preço do Cardmarket de ${
          escapeAttr(x.nome)}, em euros"></label>
    </div>`;
}

function slLinha(x) {
  const cls = [x.qty > 0 ? 'tem' : '', x.por_sair ? 'porsair' : '',
    x.acessorio ? 'acess' : ''].join(' ');
  const marcas = [];
  if (x.por_sair) {
    marcas.push(`<span class="sl-marca ps">por sair${x.data ? ` · ${escapeHTML(x.data)}` : ''}</span>`);
  } else if (x.data) {
    marcas.push(`<span class="sl-marca dt">${escapeHTML(x.data)}</span>`);
  }
  if (x.fonte === 'config') marcas.push('<span class="sl-marca cfg">do config</span>');
  // O CONTEÚDO (4 decks iguais, 16 kits + 1 display, 12 vaults) e a NOTA são
  // duas coisas: o primeiro é o que vem dentro, a segunda é a ressalva. Um
  // «12 vaults» com uma fonte a dizer 4 tem de se ler como dúvida, não como
  // facto.
  if (x.conteudo) marcas.push(`<span class="sl-marca dentro">${escapeHTML(x.conteudo)}</span>`);
  if (x.nota) marcas.push(`<span class="sl-marca nota">${escapeHTML(x.nota)}</span>`);
  if (x.duplicados && x.duplicados.length) {
    marcas.push(`<span class="sl-marca dup" title="O CardTrader tem mais do que um
      blueprint com este nome, esta edição e esta versão; o que ficou é o que tem as
      ofertas.">junta ${plural(x.duplicados.length, 'blueprint', 'blueprints')} do
      CardTrader (${escapeHTML(x.duplicados.map(d => d.blueprint_id).join(', '))})</span>`);
  }
  // A imagem vem do CardTrader (é o dono da lista). Sem imagem, um quadrado
  // com o tipo lá dentro — nunca um ícone partido.
  const arte = x.img
    ? `<img src="${escapeAttr(x.img)}" alt="" loading="lazy" decoding="async"
            onerror="this.remove()">`
    : `<span class="sl-semimg">${escapeHTML(x.tipo_label)}</span>`;
  return `<div class="sl-linha ${cls}" data-pid="${escapeAttr(x.id)}">
    <div class="sl-art">${arte}${x.qty ? `<span class="sl-qty">${x.qty}×</span>` : ''}</div>
    <div class="sl-meio">
      <div class="tname" title="${escapeAttr(x.nome)}">${escapeHTML(x.nome)}${
        x.versao ? ` <i class="var">${escapeHTML(x.versao)}</i>` : ''}</div>
      <div class="codigo"><span class="sl-tipo">${escapeHTML(x.tipo_label)}</span>
        ${escapeHTML(x.edicao_label)}${x.categoria
          ? ` · ${escapeHTML(x.categoria.replace(/^Riftbound /, ''))}` : ''}</div>
      ${slLinks(x)}
      ${marcas.length ? `<div class="sl-marcas">${marcas.join('')}</div>` : ''}
    </div>
    <div class="sl-dir">
      ${slPreco(x)}
      ${state.editable ? `<div class="steppers">
        <button class="step minus" data-sl="-1" aria-label="menos um ${escapeAttr(x.nome)}"
          ${x.qty ? '' : 'disabled'}>−</button>
        <b>${x.qty}</b>
        <button class="step plus" data-sl="1" aria-label="mais um ${escapeAttr(x.nome)}">+</button>
      </div>` : `<div class="sl-tenho">${x.qty ? `tens ${x.qty}` : 'não tens'}</div>`}
    </div>
  </div>`;
}

/* Quantos links são a página do produto e quantos são pesquisa — dito uma vez
   no cabeçalho, para não ser preciso descobri-lo linha a linha. */
function slLinksNota(L) {
  if (!L) return '';
  const p = [];
  if (L.cardmarket.pesquisa) {
    p.push(`<b>${L.cardmarket.pesquisa}</b> sem id do Cardmarket (o link abre a pesquisa
      pelo nome)`);
  }
  if (L.cardtrader.pesquisa) {
    p.push(`<b>${L.cardtrader.pesquisa}</b> fora do catálogo do CardTrader (idem)`);
  }
  return `Cada linha leva <b>link de compra</b> para o Cardmarket e para o CardTrader${
    p.length ? `: ${p.join(', ')}` : ''}. O endereço do CardTrader está confirmado; o do
    Cardmarket <b>não</b> — o site deles responde 403 a pedidos automáticos, e é por isso
    que há sempre um link de pesquisa ao lado.`;
}

/* Os dois links de compra de cada linha (2026-09-25). Curtos, porque a linha
   tem de caber num telemóvel: «Cardmarket» e «CardTrader», e quem não tem id
   nesse mercado leva «procurar» — dito, não escondido, porque um link de
   pesquisa não é a página do produto. Os templates vêm do `mercados.py`; o do
   CardTrader está validado, o do Cardmarket não (403 a pedidos automáticos). */
function slLinks(x) {
  const L = x.links;
  if (!L) return '';
  const um = (l, rot, titulo) => l ? `<a href="${escapeAttr(l.url)}" target="_blank"
    rel="noreferrer noopener" class="${l.pesquisa ? 'alt' : ''}"
    title="${escapeAttr(titulo)}">${rot}${l.pesquisa ? ' <i>procurar</i>' : ''}</a>` : '';
  return `<div class="sl-links">${
    um(L.cardmarket, 'Cardmarket', L.cardmarket && L.cardmarket.pesquisa
      ? 'este produto não tem id do Cardmarket no catálogo — abre a pesquisa pelo nome'
      : 'a página do produto no Cardmarket (o formato do endereço não está validado: '
        + 'o site deles responde 403 a pedidos automáticos)')
  }${
    um(L.cardtrader, 'CardTrader', L.cardtrader && L.cardtrader.pesquisa
      ? 'este produto não está no catálogo do CardTrader — abre a pesquisa pelo nome'
      : 'a página do produto no CardTrader')
  }</div>`;
}

function slLigar() {
  for (const b of document.querySelectorAll('#sl-body .step[data-sl]')) {
    b.onclick = async () => {
      const pid = b.closest('.sl-linha').dataset.pid;
      try { await slPost({ product_id: pid, delta: Number(b.dataset.sl) }); }
      catch (err) { toast(err.message, { error: true }); }
    };
  }
  // O preço do Cardmarket, escrito por ele. Grava-se ao SAIR do campo (ou no
  // Enter) e não a cada tecla — senão cada dígito era um pedido e um redesenho.
  for (const inp of document.querySelectorAll('#sl-body .sl-cm-in')) {
    const antes = inp.value;
    const gravar = async () => {
      if (inp.value.trim() === antes.trim()) return;
      const pid = inp.closest('.sl-linha').dataset.pid;
      try {
        await slPost({ product_id: pid, eur: inp.value.trim() || null },
                     'api/selado/preco');
      } catch (err) { toast(err.message, { error: true }); inp.value = antes; }
    };
    inp.onchange = gravar;
    inp.onkeydown = (ev) => { if (ev.key === 'Enter') { ev.preventDefault(); inp.blur(); } };
  }
}


/* O que o `a_subir.excluir` tirou, por critério — o mesmo texto nas listas de
   compra todas. Por critério porque as signatures também são de raridade
   showcase: um número só não dizia quantas saíram por serem uma coisa ou a
   outra. Os blocos da coleção extra (2026-09-15) levam o nome do cabeçalho da
   grelha, que vem no `excluded_labels`. */
function foraTexto(scope) {
  if (!scope.excluded) return '';
  const nomes = scope.excluded_labels || {};
  const motivos = (scope.excluded_by || [])
    .map(c => `${c.n} ${escapeHTML(nomes[c.criterio] || c.criterio)}`).join(' + ');
  const extra = scope.so_master_set
    ? ` A <b>coleção extra</b> (artes alternativas, runas especiais,
        sobrenumeradas, promos) tem alvo na grelha para veres quantas tens de
        cada e não entra na lista geral — cada bloco tem a sua wantlist, à
        parte, no separador <a href="#faltas-edicao">Faltas</a>.`
    : ` A exclusão é da <b>sequência</b>: a coleção extra entra na mesma, ao
        playset.`;
  return `<br>Fora desta lista: <b>${scope.excluded}</b> impressões
    (${motivos}).${extra}`;
}

/* --------------------------------------------- listas para o Cardmarket

   UM gerador, dois sítios (pedido do André, 2026-09-08): a aba «A subir» e a
   aba «Master set». O gémeo em Python é o `cardmarket.py` — escreve exactamente
   a mesma linha, e há teste que compara os dois.

   As listas saem sempre do que está NO ECRÃ, com o filtro e a ordem que
   estiverem activos: é isso que ele está a olhar quando carrega no botão.

   O nome é o DO MERCADO ("Darius - Trifarian"), não o da RiftScribe
   ("Darius, Trifarian"), senão não casa lá nada.

   A caixa de texto é o mecanismo principal, não um fallback: o
   `navigator.clipboard` só existe em contexto seguro, e no telemóvel isto abre
   por http num IP da rede local — ou seja, lá nunca funcionaria.           */

/* Quantas cópias vão na linha. Nas listas de compra o campo chama-se `missing`
   (o que falta comprar); `qty` fica como segunda hipótese para um item que não
   o traga. Gémeo do `cardmarket.quantidade` em Python. */
function cmQtd(it) {
  return it.missing != null ? it.missing : (it.qty || 0);
}

function cmLinha(it, comCodigo) {
  const nome = it.market_name || it.name || '';
  const n = cmQtd(it);
  if (comCodigo) {
    const c = (it.code || '').split('/')[0];
    return `${n} ${nome}${c ? ` [${c}]` : ''}`;
  }
  let l = `${n} ${nome}`;
  if (it.v && (it.n_versions || 1) > 1) l += ` (V.${it.v})`;   // só quando há mais que uma
  if (it.market_set) l += ` (${it.market_set})`;
  return l;
}

const CM_CABECALHO = ['quantidade', 'nome', 'codigo', 'edicao', 'raridade',
                      'preco_hoje_eur', 'delta_pct', 'custo_eur'];

function cmCSV(itens) {
  const campo = v => {
    const s = String(v ?? '');
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const cents = c => (c == null ? '' : (c / 100).toFixed(2));
  const linhas = [CM_CABECALHO.join(',')];
  for (const it of itens) {
    linhas.push([
      cmQtd(it),
      it.market_name || it.name || '',
      (it.code || '').split('/')[0],
      it.market_set || it.set_name || it.set || '',
      it.rarity || '',
      cents(it.price),
      it.pct == null ? '' : it.pct.toFixed(1),
      cents(it.total),
    ].map(campo).join(','));
  }
  return linhas.join('\n') + '\n';
}

/* Os três botões e a caixa. `id` prefixa os elementos para as duas abas
   poderem coexistir sem colidir. */
function cmZonaHTML(id) {
  return `<div class="wl-zona cm-zona">
    <div class="cm-botoes">
      <button class="btn" data-cm="${id}" data-cm-modo="normal">Copiar para o Cardmarket</button>
      <button class="btn ghost" data-cm="${id}" data-cm-modo="codigo">Copiar com código</button>
      <button class="btn ghost" data-cm="${id}" data-cm-modo="csv">Descarregar CSV</button>
    </div>
    <textarea id="${id}-txt" class="wl-txt" readonly hidden></textarea>
    <small class="nota" id="${id}-nota" hidden></small>
    <small class="nota aviso-foil" id="${id}-foil" hidden></small>
  </div>`;
}

/* `getItens` é uma função, não uma lista: assim os botões apanham sempre o
   filtro que estiver activo no momento do clique, e não o que estava quando a
   página foi desenhada. */
function cmLigar(id, getItens, nomeFicheiro) {
  for (const b of document.querySelectorAll(`[data-cm="${id}"]`)) {
    b.onclick = () => {
      const itens = getItens();
      if (b.dataset.cmModo === 'csv') { cmDescarregar(itens, nomeFicheiro, id); return; }
      cmMostrar(id, itens, b.dataset.cmModo === 'codigo');
    };
  }
}

/* Todas as listas que passam por aqui são de COMPRA e vão para a wantlist do
   Cardmarket (a de venda, que dizia outra coisa na nota, saiu a 2026-09-15).

   `foco` e `copiar` só se desligam nas wantlists da Coleção, que já vêm
   preenchidas sem ninguém carregar em nada: aí roubar o foco atirava a página
   para o fim, e escrever no clipboard sem ele pedir apagava-lhe o que lá
   tivesse. Nos botões continuam ligados, que é o que se espera de um clique. */
function cmMostrar(id, itens, comCodigo, { foco = true, copiar = true,
                                           foilTodas = false } = {}) {
  const linhas = itens.map(it => cmLinha(it, comCodigo));
  const txt = $(`#${id}-txt`), nota = $(`#${id}-nota`), fnota = $(`#${id}-foil`);
  txt.value = linhas.join('\n');
  txt.rows = Math.min(16, Math.max(4, linhas.length));
  txt.hidden = false; nota.hidden = false;
  if (foco) { txt.focus(); txt.select(); }

  const copias = itens.reduce((s, x) => s + cmQtd(x), 0);
  const cents = itens.reduce((s, x) => s + (x.total || 0), 0);
  // O total NÃO vai no texto: uma linha de total colada na wantlist seria
  // importada como se fosse uma carta.
  const resumo = `${linhas.length} linhas · ${copias} cópias · ${eur(cents)}`
    + (comCodigo ? ' · com código, para desambiguar à mão (o Cardmarket não lê os [ ])' : '');

  // A língua também não se marca no texto: no Cardmarket é um filtro por
  // entrada, como o foil. Os preços daqui são só de ofertas em inglês
  // (`precos.linguas`), por isso diz-se para ligar o mesmo lá.
  const destino = 'Cola na wantlist do Cardmarket e liga o filtro de língua '
    + '(inglês) — os preços daqui são só de ofertas em inglês.';
  if (!copiar) {
    nota.textContent = `${resumo} — carrega em copiar, ou seleciona e copia à mão.`;
  } else if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(txt.value)
      .then(() => { nota.textContent = `${resumo} — copiadas. ${destino}`; })
      .catch(() => { nota.textContent = `${resumo} — já selecionadas, copia com Ctrl+C.`; });
  } else {
    nota.textContent = `${resumo} — já selecionadas, copia com Ctrl+C `
      + `(no telemóvel, toca e mantém).`;
  }

  // O foil NÃO se pode marcar no texto — é um filtro por entrada, posto na
  // interface deles. Aqui só se diz em que linhas é preciso ligá-lo.
  //
  // A lista vai dentro de um <details>: na wantlist de tudo são 307 linhas e na
  // do OGN 90, e como as duas caixas da Coleção já vêm preenchidas, a página
  // acabava em várias centenas de linhas de texto monoespaçado — no telemóvel é
  // um scroll sem fim. Fica aberta quando é curta, que é quando se lê de
  // relance. O <details> é do próprio browser: não precisa de JavaScript e o
  // texto continua todo lá para copiar.
  //
  // `foilTodas` é a wantlist das FOILS (2026-09-27): ali a lista É de foils, e
  // dizer «só têm oferta foil no mercado» era outra frase — o que se diz é que
  // todas precisam do filtro.
  const foil = linhas.filter((_, i) => itens[i].foil_only);
  fnota.hidden = !foil.length;
  if (foil.length) {
    const porque = `O texto da wantlist não leva marca de foil — depois de
         colares, liga o filtro <i>Foil</i> nestas entradas.`;
    fnota.innerHTML = `<b>${foilTodas
      ? `${foil.length === 1 ? 'Esta linha é' : 'Estas ' + foil.length + ' linhas são'} FOIL.`
      : `${foil.length} ${foil.length === 1 ? 'destas só tem' : 'destas só têm'}
         oferta foil no mercado.`}</b> ${porque}
      <details class="foil-lista"${foil.length <= 8 ? ' open' : ''}>
        <summary>ver ${plural(foil.length, 'linha', 'linhas')}</summary>
        ${foil.map(escapeHTML).join('<br>')}</details>`;
  }
}

function cmDescarregar(itens, nomeFicheiro, id) {
  // O BOM é para o Excel em português abrir os acentos direitos.
  const blob = new Blob(['﻿' + cmCSV(itens)], { type: 'text/csv;charset=utf-8' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = nomeFicheiro;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 5000);
  const nota = $(`#${id}-nota`);
  if (nota) {
    nota.hidden = false;
    nota.textContent = `${itens.length} linhas em ${nomeFicheiro}.`;
  }
}

function hojeISO() {
  return new Date().toISOString().slice(0, 10);
}


/* Sub-abas dentro de "Por deck". Cada deck conta o que a alocação por
   prioridade não lhe dá — é a mesma lista da secção Decks. Desde 2026-09-11 o
   deck de baixo compra o que o de cima já usa («o próximo passa a marcar como
   faltas para comprar»), por isso a soma das abas é o custo de ter os decks
   todos montados, e a última aba («Todos juntos») dá o mesmo total — excepto
   nos decks com a MESMA LEGEND (2026-09-11, noite), que partilham as cartas:
   cada aba mostra a sua lista, mas a compra é uma e o total conta-a uma vez. */
function renderPorDeck() {
  const f = state.compras;
  const um = f.por_deck.reduce((s, d) => s + d.cents, 0);
  const copias = f.por_deck.reduce((s, d) => s + d.copies, 0);
  const tj = f.todos_juntos;
  const grupos = f.por_deck.some(d => d.grupo && d.grupo.variantes);
  // O índice do deck escolhido fica guardado no browser, mas apagar um deck é
  // apagar o .txt — e aí o índice antigo passa a apontar para fora da lista.
  // Sem esta correção o `f.por_deck[sel]` vinha `undefined`, a secção Faltas
  // rebentava em branco e ficava assim a cada recarga, porque o índice mau
  // continuava no localStorage.
  let sel = state.prefs.faltaDeck ?? 0;
  if (sel !== 'todos' && !f.por_deck[sel]) sel = f.por_deck.length ? 0 : 'todos';

  const abas = f.por_deck.map((d, i) => `
    <button class="seg-btn ${i === sel ? 'is-on' : ''}" data-fd="${i}"${
      d.grupo && d.grupo.variantes ? ` title="${escapeAttr(`A mesma Legend que ${
        d.grupo.irmaos.join(', ')}: partilham as cartas, a compra conta uma vez`)}"` : ''}>
      ${d.priority}. ${d.grupo && d.grupo.variantes ? '·· ' : ''}${escapeHTML(deckCurto(d.name))}
      <b>${d.copies}</b></button>`).join('')
    + `<button class="seg-btn ${sel === 'todos' ? 'is-on' : ''}" data-fd="todos">
        Todos juntos <b>${tj.copies}</b></button>`;

  const alvo = sel === 'todos' ? tj : f.por_deck[sel];
  const sobre = sel !== 'todos' && f.por_deck[sel].grupo && f.por_deck[sel].grupo.variantes
    ? ` Este deck tem a <b>mesma Legend</b> que ${escapeHTML(f.por_deck[sel].grupo.irmaos.join(', '))}:
       partilham as cartas, e o que aqui falta é a mesma compra que falta lá — em
       «Todos juntos» conta uma vez.` : '';
  const intro = sel === 'todos'
    ? `<p class="note">O que custaria ter os <b>${f.por_deck.length}</b> decks
       montados <b>ao mesmo tempo</b>, com cópias para cada um. ${
         tj.copies === copias
           ? 'É a soma das abas dos decks: cada deck compra o que a Coleção não chega para ele.'
           : grupos && tj.copies < copias
             ? `São <b>${tj.copies}</b> cópias e não ${copias}: os decks marcados com «··»
                têm a mesma Legend e partilham as cartas — a compra deles conta uma vez.`
             : `São <b>${eur(tj.cents - um)}</b> e <b>${tj.copies - copias}</b> cópias
                a mais do que a soma das abas dos decks.`}</p>`
    : `<p class="note">O que falta a este deck depois de os decks de cima se
       servirem da Coleção. ${sel > 0
         ? 'O que um deck de cima já usa não conta para este: compra-se.'
         : 'É o primeiro da fila, por isso serve-se primeiro.'}${sobre}</p>`;

  $('#deck-body').innerHTML = `
    <div class="seg seg-wrap">${abas}</div>
    <div class="deck-card resumo">
      <b>${sel === 'todos' ? 'Todos ao mesmo tempo' : escapeHTML(f.por_deck[sel].name)}</b>
      <span>${alvo.cards} cartas · ${alvo.copies} cópias · ${eur(alvo.cents)}</span>
    </div>
    ${intro}
    ${alvo.by_set.length ? alvo.by_set.map(m => `
      <h3 class="section-head sub">${escapeHTML(m.name)}
        <span>${m.copies} cópia${m.copies === 1 ? '' : 's'} de ${m.cards} carta${
          m.cards === 1 ? '' : 's'}${m.cents ? ` · ${eur(m.cents)}` : ''}</span></h3>
      <div class="grid deck-grid">${m.items.map(faltaTile).join('')}</div>`).join('')
      : '<p class="empty">Nada a comprar — este deck fica completo com o que vem acima.</p>'}
    <div class="wl-zona">
      <button class="btn" id="wl-btn">Lista para a wantlist do Cardmarket</button>
      <textarea id="wl-txt" class="wl-txt" readonly hidden></textarea>
      <small class="nota" id="wl-nota" hidden></small>
      <small class="nota aviso-foil" id="wl-foil" hidden></small>
    </div>
    <p class="note total-linha">Somando as abas dos decks:
      <b>${copias} cópias · ${eur(um)}</b> para os ter todos montados.</p>`;

  for (const b of document.querySelectorAll('#deck-body .seg-btn[data-fd]')) {
    b.onclick = () => {
      const v = b.dataset.fd;
      state.prefs.faltaDeck = v === 'todos' ? 'todos' : Number(v);
      savePrefs();
      renderPorDeck();
    };
  }
  $('#wl-btn').onclick = () => mostrarWantlist(alvo);
}

/* Texto para colar na wantlist do Cardmarket.

   Usa o nome COMO O MERCADO O ESCREVE ("Darius - Trifarian"), não o da
   RiftScribe ("Darius, Trifarian"), senão não casa lá nada.

   A caixa de texto é o mecanismo principal, não um fallback: o
   `navigator.clipboard` só existe em contexto seguro, e no telemóvel isto
   abre por http num IP da rede local — ou seja, lá nunca funcionaria. */
/* A lista dos decks leva só a versão mais barata de cada carta. As versões
   bonitas vivem na aba "Pimp decks", que é outra pergunta. */
function mostrarWantlist(alvo, comVar = false) {
  const linhas = [], foil = [];

  const escreve = (qtd, nome, v, n, edicao, ehFoil) => {
    let l = `${qtd} ${nome}`;
    if (v && n > 1) l += ` (V.${v})`;      // só numera quando há mais do que uma
    if (edicao) l += ` (${edicao})`;
    linhas.push(l);
    if (ehFoil) foil.push(l);
  };

  for (const g of alvo.by_set) {
    for (const it of g.items) {
      escreve(it.qty, it.market_name || it.name, it.v, it.n_versions,
              it.market_set, it.foil_only);
      if (comVar) {
        for (const o of (it.outras_versoes || [])) {
          escreve(it.qty, o.name, o.v, o.n, o.set, o.foil_only);
        }
      }
    }
  }
  const txt = $('#wl-txt');
  const nota = $('#wl-nota');
  txt.value = linhas.join('\n');
  txt.rows = Math.min(16, Math.max(4, linhas.length));
  txt.hidden = false;
  nota.hidden = false;
  txt.focus();
  txt.select();

  // O foil NÃO se pode marcar no texto — é um filtro por entrada, posto na
  // interface deles. Aqui só se diz em que linhas é preciso ligá-lo.
  const fnota = $('#wl-foil');
  if (foil.length) {
    fnota.hidden = false;
    fnota.innerHTML = `<b>${foil.length} destas só têm oferta foil no mercado.</b>
      O texto da wantlist não leva marca de foil — depois de colares, liga o
      filtro <i>Foil</i> nestas entradas:<br>${foil.map(escapeHTML).join('<br>')}`;
  } else {
    fnota.hidden = true;
  }

  const n = linhas.length;
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(txt.value)
      .then(() => { nota.textContent = `${n} linhas copiadas. Cola na wantlist do Cardmarket.`; })
      .catch(() => { nota.textContent = `${n} linhas — já selecionadas, copia com Ctrl+C.`; });
  } else {
    nota.textContent = `${n} linhas — já selecionadas, copia à mão (no telemóvel, `
      + `toca e mantém para copiar).`;
  }
}


/* "Pimp decks": as versões alteradas das cartas que os decks usam — artes
   alternativas, showcase e promos. É lista de compras: desconta o que ele já
   tem e o que vem a caminho, e a quantidade é só o que ainda falta comprar. */
function renderPimp() {
  const p = state.compras.pimp;
  if (!p.printings) {
    $('#deck-body').innerHTML = '<p class="empty">Nenhuma carta dos teus decks tem versão alterada.</p>';
    return;
  }
  // Mesma história do "Por deck": o índice guardado pode ter sobrevivido ao
  // deck. Cai para a vista "Todas" em vez de rebentar.
  let sel = state.prefs.pimpDeck ?? 'todos';
  if (sel !== 'todos' && !p.by_deck[sel]) sel = 'todos';
  const alvo = sel === 'todos' ? p : p.by_deck[sel];

  const somaDecks = p.by_deck.reduce((s, d) => s + d.printings, 0);
  const abas = `<button class="seg-btn ${sel === 'todos' ? 'is-on' : ''}" data-pd="todos">
      Todas <b>${somaDecks}</b></button>`
    + p.by_deck.map((d, k) => `
      <button class="seg-btn ${k === sel ? 'is-on' : ''}" data-pd="${k}">
        ${d.priority}. ${escapeHTML(deckCurto(d.name))}
        <b>${d.printings}</b></button>`).join('');

  $('#deck-body').innerHTML = `
    <div class="seg seg-wrap">${abas}</div>
    <div class="deck-card resumo">
      <b>${sel === 'todos' ? 'Todas as versões alteradas' : escapeHTML(p.by_deck[sel].name)}</b>
      <span>${sel === 'todos'
        ? `${plural(somaDecks, 'versão', 'versões')} · ${
            eur(p.by_deck.reduce((s, d) => s + d.cents, 0))}`
        : `${plural(alvo.cards, 'carta', 'cartas')} · ${
            plural(alvo.printings, 'versão', 'versões')} · ${eur(alvo.cents)}`}${
        alvo.done ? ` · ${alvo.done} já feitas` : ''}</span>
    </div>
    <p class="note">${sel === 'todos'
      ? `O que falta comprar para pimpar, deck a deck: artes alternativas,
         showcase e promos. Uma carta que dois decks usem aparece nos dois.`
      : `O que falta comprar para pimpar este deck.`}
      Já <b>não</b> mostra o que tens nem o que vem a caminho — a quantidade
      é só o que ainda falta comprar.</p>
    ${sel === 'todos'
      ? p.by_deck.map(d => `
          <h3 class="section-head sub">${d.priority}. ${escapeHTML(d.name)}
            <span>${plural(d.printings, 'versão', 'versões')} · ${eur(d.cents)}${
              d.owned ? ` · já tens ${d.owned}` : ''}</span></h3>
          <div class="grid deck-grid">${
            achata(d).map(x => pimpTile(x, false)).join('')}</div>`).join('')
      : `<div class="grid deck-grid">${
          achata(alvo).map(x => pimpTile(x, false)).join('')}</div>`}
    <div class="wl-zona">
      <button class="btn" id="pimp-btn">Lista para a wantlist do Cardmarket</button>
      <textarea id="pimp-txt" class="wl-txt" readonly hidden></textarea>
      <small class="nota" id="pimp-nota" hidden></small>
    </div>`;

  for (const b of document.querySelectorAll('#deck-body .seg-btn[data-pd]')) {
    b.onclick = () => {
      const v = b.dataset.pd;
      state.prefs.pimpDeck = v === 'todos' ? 'todos' : Number(v);
      savePrefs();
      renderPimp();
    };
  }

  $('#pimp-btn').onclick = () => {
    const linhas = [];
    // Na vista "Todas" a lista sai deck a deck, na mesma ordem do ecrã.
    const fonte = sel === 'todos' ? p.by_deck.flatMap(achata) : achata(alvo);
    for (const it of fonte) {
      let l = `${it.qty} ${it.market_name || it.name}`;
      if (it.v && it.n_versions > 1) l += ` (V.${it.v})`;
      if (it.market_set) l += ` (${it.market_set})`;
      linhas.push(l);
    }
    const tx = $('#pimp-txt'), nt = $('#pimp-nota');
    tx.value = linhas.join('\n');
    tx.rows = Math.min(16, Math.max(4, linhas.length));
    tx.hidden = false; nt.hidden = false;
    tx.focus(); tx.select();
    nt.textContent = `${linhas.length} linhas — já selecionadas, copia com Ctrl+C `
      + `(no telemóvel, toca e mantém).`;
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(tx.value)
        .then(() => { nt.textContent = `${linhas.length} linhas copiadas.`; })
        .catch(() => {});
    }
  };
}

/* Achata as edições: aqui a arrumação é por DECK, não por edição. Dentro do
   deck ordena-se pelo que custa, que é o que decide a troca. */
function achata(d) {
  return d.by_set.flatMap(g => g.items).sort((a, b) => b.total - a.total);
}

function pimpTile(x, comDecks = true) {
  return `<div class="dtile ${x.have ? 'ok' : 'neutro'}">
    ${artHTML(x, `<span class="need">${x.qty}×</span>
      ${x.have ? `<span class="ja-tens">tens ${x.have}</span>` : ''}
      ${x.market_only ? '<span class="so-mercado" title="A RiftScribe ainda não tem esta impressão; veio do CardTrader">fora do catálogo</span>' : ''}
      ${x.price != null ? `<span class="price">${eurShort(x.total)}</span>` : ''}`)}
    <div class="tname" title="${escapeAttr(x.name)}">${escapeHTML(x.name)}</div>
    <div class="codigo">${escapeHTML((x.code || '').split('/')[0])}${
      x.price != null ? ` · ${eur(x.price)}` : ''}</div>
    <div class="onde tenho">${escapeHTML(x.label)}${
      comDecks && x.decks.length
        ? ` · ${x.decks.map(d => escapeHTML(deckCurto(d))).join(', ')}` : ''}</div>
  </div>`;
}


function artHTML(x, extra = '') {
  const src = state.imageMode === 'remote' ? (x.cdn || x.img) : (x.img || x.cdn);
  const alt = state.imageMode === 'remote' ? (x.img || '') : (x.cdn || '');
  return `<div class="art${x.landscape ? ' landscape' : ''}">
    ${src ? `<img src="${src}" alt="${escapeAttr(x.name)}" loading="lazy" decoding="async"
       ${alt ? `data-fallback="${escapeAttr(alt)}"` : ''}>` : ''}
    ${extra}
    <span class="cn">${escapeHTML((x.code || '').split('/')[0])}</span>
  </div>`;
}

function staplTile(x) {
  return `<div class="dtile gone">
    ${artHTML(x, `<span class="need">${x.missing}×</span>
      <span class="decks-n">${x.n_decks} decks</span>
      ${x.price != null ? `<span class="price">${eurShort(x.total)}</span>` : ''}`)}
    <div class="tname" title="${escapeAttr(x.name)}">${escapeHTML(x.name)}</div>
    <div class="onde tenho">${x.decks.map(d =>
      `${d.qty}× ${escapeHTML(deckCurto(d.deck))}`).join('<br>')}</div>
    ${x.especial ? `<div class="onde especial">${x.especial.qty}× em versão especial (${
      escapeHTML((x.especial.code || '').split('/')[0])}${
      x.especial.price != null ? ` · ${eur(x.especial.price)}` : ''})</div>` : ''}
  </div>`;
}


/* ------------------------------------------------------------------ utils */

function eur(cents) {
  if (cents == null) return '—';
  return (cents / 100).toLocaleString('pt-PT', { style: 'currency', currency: 'EUR' });
}

// A partir de quanto é que o preço aparece por cima da carta (do config).
function priceBadgeMin() {
  return state.payload?.price_badge_min ?? 100;
}

// Versão curta para caber no tile: sem cêntimos a partir dos 100 €.
function eurShort(cents) {
  const v = cents / 100;
  return v.toLocaleString('pt-PT', {
    style: 'currency', currency: 'EUR',
    minimumFractionDigits: v >= 100 ? 0 : 2,
    maximumFractionDigits: v >= 100 ? 0 : 2,
  });
}

/* «1 versão» / «2 versões». Havia meia dúzia de sítios a escrever sempre o
   plural — «1 versões», «1 cartas» —, e uma lista de um item lida assim parece
   um contador partido. */
function plural(n, um, muitos) {
  return `${n} ${n === 1 ? um : muitos}`;
}

/* «2 573» — o separador dos milhares. Os números grandes do painel do Início
   liam-se «2573», que a esta distância é fácil de ler como 257. */
function num(n) {
  return Number(n || 0).toLocaleString('pt-PT').replace(/ /g, ' ');
}

/* «82,5 %» — vírgula decimal e espaço antes do símbolo, como se escreve em
   português. Uma percentagem redonda sai sem casa decimal («100 %»). */
function fmtPct(p) {
  if (p == null) return '—';
  const n = Number(p);
  return `${(Math.round(n * 10) / 10).toFixed(n % 1 ? 1 : 0).replace('.', ',')} %`;
}

function escapeHTML(s) {
  return String(s ?? '').replace(/[&<>]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
}
function escapeAttr(s) {
  return escapeHTML(s).replace(/"/g, '&quot;');
}

boot().catch(err => {
  // A barra lateral desenha-se depois do `api/index.json` (é de lá que vêm as
  // abas escondidas). Se ele não responder, desenha-se aqui com tudo à vista:
  // sem navegação nenhuma não se chega a lado nenhum.
  try { renderNav(); } catch (_) {}
  $('#grid').innerHTML = `<p class="empty">Falhou a carregar: ${escapeHTML(err.message)}<br>
    <small>Se é a primeira vez, corre <code>riftvault sync</code>.</small></p>`;
});

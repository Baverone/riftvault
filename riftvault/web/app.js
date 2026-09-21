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

const state = {
  index: null,
  setId: null,
  payload: null,
  editable: false,
  imageMode: 'local',
  // printing_id -> cópias nos binders de COLEÇÃO (verdade local, otimista).
  // Desde 2026-09-10 não é o total físico: as que estão num deck ou no binder
  // Decks/Venda não contam para a Coleção. O total vive no `locs`.
  qty: new Map(),
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
  // O antigo `faltas.json` partiu-se a 2026-09-15 (à tarde) na wantlist da
  // Coleção (`api/wantlist.json`) e nas listas de compra dos decks
  // (`api/compras.json`). Cada um tem o pedido a caminho guardado (`*P`) para
  // não se pedir duas vezes. (A terceira parte, a tabela de preços, foi
  // apagada com o separador dela a 2026-09-19 — ver o CLAUDE.md.)
  wantlist: null, wantlistP: null, compras: null, comprasP: null,
  // O separador «Faltas» (2026-09-15, fim da tarde): `api/faltas_edicao.json`.
  faltasEdicao: null,
  // O separador «A mais» (2026-09-17): `api/a_mais.json`.
  aMais: null,
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

/* ------------------------------------------------------------------ dados */

async function getJSON(url) {
  const r = await fetch(url, { cache: 'no-store' });
  if (!r.ok) throw new Error(`${url} -> HTTP ${r.status}`);
  return r.json();
}

async function boot() {
  loadPrefs();
  wireControls();
  wireKeyboard();

  state.index = await getJSON('api/index.json');
  state.editable = !!state.index.editable;
  state.imageMode = state.index.image_mode || 'local';
  document.body.classList.toggle('readonly', !state.editable);
  $('#mode-badge').hidden = state.editable;
  // O chip "só leitura" ao lado do título passa despercebido — quem abre isto
  // no telemóvel carrega no sítio dos +/- e não percebe porque não acontece
  // nada. O aviso tem de ser grande.
  $('#readonly-banner').hidden = state.editable;
  $('#generated').textContent = state.index.generated_at
    ? `Atualizado em ${state.index.generated_at.replace('T', ' ').replace('+00:00', ' UTC')}.` : '';

  for (const b of document.querySelectorAll('#section-tabs .tab')) {
    b.onclick = () => showSection(b.dataset.section);
  }

  // A contagem por níveis das cinco edições, como estava quando o ficheiro foi
  // gerado. A edição que ele abrir passa a ser recalculada a partir dos +/-.
  for (const [sid, ls] of Object.entries((state.index.levels || {}).by_set || {})) {
    state.levels.set(sid, ls);
  }

  renderSetTabs();
  const first = state.index.sets[0];
  const wanted = state.prefs.set === TODAS || state.index.sets.some(s => s.id === state.prefs.set)
    ? state.prefs.set : (first && first.id);
  if (wanted) await loadSet(wanted);
  // Uma preferência guardada com a secção Venda (apagada a 2026-09-15) ou
  // com a tabela de preços (`faltas`, apagada a 2026-09-19) cai aqui na
  // Coleção, como qualquer outro nome que já não exista.
  // `#decks`, `#faltas-edicao`, … no URL abre essa secção — dá para ligar a
  // uma secção directamente; sem ele fica a última que ele abriu.
  const hash = location.hash.slice(1);
  showSection(SECCOES.includes(hash) ? hash
    : SECCOES.includes(state.prefs.section) ? state.prefs.section : 'colecao');
  // Uma ligação `#encomendas` dentro da página (a nota do deck) abre a secção
  // sem recarregar.
  window.addEventListener('hashchange', () => {
    const h = location.hash.slice(1);
    if (SECCOES.includes(h)) showSection(h);
  });
}

async function loadSet(setId) {
  state.setId = setId;
  state.prefs.set = setId;
  savePrefs();
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
  state.locs.clear();
  for (const b of p.blocks || []) if (b.counts) state.counting.add(b.id);
  if (!(p.blocks || []).length) state.counting.add('master');
  for (const g of p.groups) {
    state.play.set(g.card_key, { owned: g.playset.owned, target: g.playset.target });
    for (const pr of g.printings) {
      state.qty.set(pr.id, pr.qty);
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
  renderFaltaLinha();
  // Idem: o bloco das runas é do JOGO inteiro, não da edição nem do filtro.
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
   payload da edição, de propósito —, fecha a grelha em todas as edições (as
   runas são as mesmas seis), e não entra em conta nenhuma daqui: nem na
   barra, nem nos níveis, nem no valor, nem nas wantlists. O `state.runas`
   não é lido por mais ninguém.

   Ao lado, em letra pequena, «na coleção: N» é o que o site sabe que ele
   tem de todas as versões (a base do OGN, que também está na sequência em
   cima; a alt art retirada; a promo do VEN escondida; as do CardTrader) —
   só para ele comparar com o que contou à mão. */
async function renderRunasVista(reler = false) {
  const el = $('#runas-vista');
  if (!el) return;
  if (reler || !state.runas) {
    try { state.runas = await getJSON('api/runas.json'); }
    catch (err) { el.innerHTML = ''; return; }
  }
  const p = state.runas;
  if (!(p.runas || []).length) { el.innerHTML = ''; return; }
  // Os tiles vão directos na grelha (o `#runas-vista` é uma `.grid`), sem o
  // `.group.multi`: um grupo de 6 colunas não cabe no telemóvel.
  el.innerHTML = runasHead(p) + p.runas.map(runaTile).join('');
  ligarRunas();
}

/* Um payload SEM `contador` vem de um servidor anterior à tarde de 19/09
   (o 8770 não se reinicia a cada merge, e o `app.js` é lido do disco a cada
   pedido): mostra-se o número calculado e sem botões, até o vigia relançar
   o processo. Os botões pedem o `editable` do PAYLOAD, como a Coleção. */
function runaContador(x) {
  return x.contador != null ? x.contador : x.total;
}

function runasHead(p) {
  const t = p.totals;
  const sem = t.sem_retiradas !== t.total ? ` (${t.sem_retiradas} sem as retiradas)` : '';
  const n = t.contador != null ? t.contador : t.total;
  return `<h2 class="section-head fora vista" id="runas-head">Runas — ${p.alvo} de cada
      <span>contas <b>${n}</b> de <b>${t.alvo}</b>
      <small class="ref">· na coleção: ${t.total}${sem}</small> — ${escapeHTML(p.nota)}</span></h2>`;
}

function runaTile(x) {
  const n = runaContador(x);
  const feito = n >= x.target;
  // As origens só no `title`: a linha visível é a referência curta, para não
  // poluir um bloco que é dele.
  const origens = x.origens.map(o => `${o.qty}× ${(o.code || '').split('/')[0]} ${o.label}`)
    .join(' · ') || 'nenhuma à mão';
  const sem = x.sem_retiradas !== x.total ? ` (${x.sem_retiradas} sem as retiradas)` : '';
  const botoes = state.runas && state.runas.editable && x.contador != null
    ? `<div class="steppers runa">
      <button class="step minus" data-runa-delta="-1" ${n > 0 ? '' : 'disabled'}
              aria-label="menos uma no teu contador de ${escapeAttr(x.name)}"
              title="menos uma (só no teu contador)">−</button>
      <button class="step plus" data-runa-delta="1"
              aria-label="mais uma no teu contador de ${escapeAttr(x.name)}"
              title="mais uma (só no teu contador)">+</button>
    </div>` : '';
  return `<div class="dtile neutro vista${feito ? ' ok' : ''}" data-runa="${escapeAttr(x.card_key)}">
    ${artHTML(x, `<span class="need">${n}/${x.target}</span>`)}
    <div class="tname" title="${escapeAttr(x.name)}">${escapeHTML(x.name)}</div>
    ${botoes}
    <div class="onde tenho ref" title="${escapeAttr(origens)}">na coleção: <b>${x.total}</b>${escapeHTML(sem)}</div>
  </div>`;
}

/* Os botões de cada tile. Chama-se depois de cada desenho, porque o
   `innerHTML` deita os handlers fora. */
function ligarRunas() {
  for (const b of document.querySelectorAll('#runas-vista .steppers.runa .step')) {
    b.onclick = () => runaAjustar(b.closest('.dtile').dataset.runa, Number(b.dataset.runaDelta));
  }
}

function runaRefreshTile(ck) {
  const el = document.querySelector(`#runas-vista .dtile[data-runa="${CSS.escape(ck)}"]`);
  const x = state.runas && state.runas.runas.find(r => r.card_key === ck);
  if (!el || !x) return;
  el.outerHTML = runaTile(x);
  const head = $('#runas-head');
  if (head) head.outerHTML = runasHead(state.runas);
  ligarRunas();
}

/* O clique no `+`/`−` do contador: ecrã otimista, pedidos da MESMA runa em
   fila — como as Encomendas —, e só o último em voo aceita o número do
   servidor. Grava SÓ na `rune_counter`; nada mais no site muda, e por isso
   não se marca nada como velho. */
async function runaAjustar(ck, delta) {
  if (!state.editable || !state.runas || !state.runas.editable) return;
  const x = state.runas.runas.find(r => r.card_key === ck);
  if (!x || x.contador == null) return;
  if (delta < 0 && x.contador <= 0) return;
  state.runas.voo = state.runas.voo || new Map();
  state.runas.fila = state.runas.fila || new Map();
  x.contador = Math.max(0, x.contador + delta);
  state.runas.totals.contador = state.runas.runas.reduce((s, r) => s + r.contador, 0);
  runaRefreshTile(ck);
  state.runas.voo.set(ck, (state.runas.voo.get(ck) || 0) + 1);
  const fila = state.runas.fila.get(ck) || Promise.resolve();
  const tarefa = fila.then(async () => {
    const r = await fetch('api/runas/ajustar', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ card_key: ck, delta }),
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
      x.contador = res.qty;
      state.runas.totals = res.totals;
      runaRefreshTile(ck);
    }
  } catch (err) {
    state.runas.voo.set(ck, Math.max(0, (state.runas.voo.get(ck) || 1) - 1));
    x.contador = Math.max(0, x.contador - delta);
    state.runas.totals.contador = state.runas.runas.reduce((s, r) => s + r.contador, 0);
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
              ${q <= 0 ? 'disabled' : ''}>−</button>
      <button class="step plus" data-act="1" aria-label="mais uma de ${escapeAttr(p.name)}">+</button>
    </div>
    <div class="playset ${play.target > 0 && play.owned >= play.target ? 'is-done' : ''}"
         data-kind="${g.is_token ? 'token' : 'jogável'}"
         ${p.price != null ? `data-price="${p.price}"` : ''}>
      ${g.is_token ? 'token' : 'jogável'} ${play.owned}/${play.target}${p.price != null ? ` · ${eur(p.price)}` : ''}
    </div>
    ${deckLine(p.id)}
    ${comUso ? usoLine(g) : ''}
  </div>`;
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
  const txt = uso.map(u => `${escapeHTML(deckCurto(u.deck))} ${u.wanted}`
    + (u.missing ? ` (falta${u.missing === 1 ? '' : 'm'} ${u.missing})` : '')
    + (u.ordered ? ` (${u.ordered} a caminho)` : '')).join(' · ');
  const falta = uso.reduce((s, u) => s + u.missing, 0);
  return `<div class="emdecks${falta ? ' falta' : ''}" title="${escapeAttr(uso.map(u =>
    `${u.deck}: pede ${u.wanted}, tem ${u.have}${u.missing ? `, faltam ${u.missing}` : ''}${
      u.ordered ? `, ${u.ordered} a caminho` : ''}`)
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

/* A grelha em blocos (André, 2026-09-08): *"master set playset todo seguido"*,
   nunca intercalados. A ORDEM é a de 2026-09-19 (*"coloca as OverNumbered a
   seguir ao master Set, depois as AltArt, depois as Promos"*): primeiro a
   sequência do master set, por número de coleção; depois as sobrenumeradas;
   depois as artes alternativas; depois as promos.

   Os blocos, a ordem e os rótulos vêm do payload (`metrics.ordem_dos_blocos`,
   `master_set.ordem_dos_blocos` no config), para a regra viver num sítio só; o
   contador de cada um é recalculado aqui, como as barras, para andar ao mesmo
   tempo que os +/-. */
function render() {
  const grid = $('#grid');
  const parts = [];
  state.tiles = [];

  const grupos = state.payload?.groups || [];
  const blocos = state.payload?.blocks || [{ id: 'master', label: null }];
  let mostrados = 0;

  for (const b of blocos) {
    const pedacos = [];
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
    parts.push(pedacos.join(''));
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

  // Valor: recalculado localmente pela mesma razão que as barras — para andar
  // ao mesmo tempo que os +/-. A barra compara o que tenho com o que a edição
  // inteira valeria pela métrica de master set.
  const val = state.payload.progress.value;
  const block = $('#value-block');
  if (val && val.has_prices) {
    let owned = 0;
    for (const g of state.payload.groups) {
      for (const p of g.printings) {
        if (p.price != null) owned += (state.qty.get(p.id) || 0) * p.price;
      }
    }
    block.hidden = false;
    $('#value-block .bar-label span').textContent =
      state.setId === TODAS ? 'Valor das edições todas' : 'Valor nesta edição';
    $('#value-num').textContent = eur(owned);
    $('#value-bar').style.width = val.full ? `${Math.min(100, (owned / val.full) * 100)}%` : '0';
    $('#value-sub').textContent = `de ${eur(val.full)} se estivesse completa`;
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
   alternativas, promos) da edição aberta, ou de «Todas».

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
   o alvo do tile e as cópias na Coleção. As runas ficam de fora aqui — é o
   `rune` do grupo, dito pelo servidor. Devolve também quantas runas ficaram
   de fora, para o cabeçalho. */
function painelItens(bloco) {
  const itens = [];
  let runas = 0;
  for (const g of state.payload?.groups || []) {
    for (const p of g.printings) {
      const t = state.targets.get(p.id) || 0;
      if (t <= 0) continue;
      if ((state.blocks.get(p.id) || 'master') !== bloco) continue;
      if (g.rune) { runas++; continue; }
      itens.push({ alvo: t, tem: state.qty.get(p.id) || 0,
                   rarity: g.rarity || '?', domain: g.domain || 'none' });
    }
  }
  return { itens, runas };
}

/* Os blocos que o painel oferece: os do payload da edição aberta, pela ordem
   do servidor, com o rótulo e o alvo do `index.painel.blocks`. */
function painelBlocos() {
  const cat = new Map((state.index?.painel?.blocks || []).map(b => [b.id, b]));
  const ids = (state.payload?.blocks || []).map(b => b.id);
  return ids.map(id => cat.get(id) || { id, label: id, target: '' });
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
    el.querySelector('.step.minus').disabled = q <= 0;
    const linha = el.querySelector('.indeck');
    if (linha) linha.outerHTML = deckLine(pid);
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
      headers: { 'Content-Type': 'application/json' },
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
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ op_id: opId }),
    });
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error || `HTTP ${r.status}`);
    const res = await r.json();
    state.qty.set(pid, res.qty_colecao != null ? res.qty_colecao : res.qty);
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
    const btn = e.target.closest('.step');
    if (!btn) return;
    const tile = btn.closest('.tile');
    adjust(tile.dataset.pid, Number(btn.dataset.act));
  });

  // Imagem local em falta cai para o CDN (e vice-versa no modo publicado).
  // Qualquer secção com artes tem de estar nesta lista: uma imagem que o cache
  // local ainda não tivesse aparecia partida e não caía para o CDN.
  for (const alvo of ['#grid', '#deck-body', '#fe-body', '#am-body', '#enc-grid']) {
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
    if ($('#colecao').hidden) return;
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

async function loadDecks() {
  const d = await getJSON('api/decks.json');
  state.decks = d.decks;
  renderDeckTabs();
  // Uma preferência guardada com a aba «Encomendas» (que viveu aqui de
  // 2026-09-11 a 2026-09-17, e passou a separador próprio) cai no primeiro deck.
  const first = DECK_FALTA_IDS.includes(state.prefs.deck)
    || state.decks.some(x => x.id === state.prefs.deck)
    ? state.prefs.deck : (state.decks[0] && state.decks[0].id);
  if (DECK_FALTA_IDS.includes(first)) await loadDeckFaltas(first);
  else if (first) await loadDeck(first);
  else $('#deck-body').innerHTML = '<p class="empty">Não há decks. Mete um .txt em <code>decks/</code>.</p>';
}

function renderDeckTabs() {
  const nav = $('#deck-tabs');
  nav.innerHTML = '';
  for (const d of state.decks) {
    const b = document.createElement('button');
    b.className = 'tab' + (d.id === state.deckId ? ' is-on' : '');
    const pct = d.wanted ? Math.round((d.have / d.wanted) * 100) : 0;
    // Membros de um grupo de Legend (2026-09-11, noite) levam «··»: são
    // listas do mesmo deck físico e partilham as cartas.
    const grupo = d.grupo && d.grupo.variantes;
    // As runas não se contam (2026-09-17, à noite): o «tenho X de N» é sem
    // elas, e o separador diz só quantas há.
    b.innerHTML = `${d.priority === 1 ? '★ ' : ''}${grupo ? '<span class="grupo-marca" title="' +
      escapeAttr(`A mesma Legend que ${d.grupo.irmaos.join(', ')}: partilham as cartas`) + '">··</span> ' : ''}${
      escapeHTML(d.name)}<small>${pct}% · ${d.have}/${d.wanted}${
      d.ordered ? ` · ${d.ordered} a caminho` : ''}${runasCurto(d.runas)}</small>`;
    b.onclick = () => loadDeck(d.id);
    nav.appendChild(b);
  }
  // A lista «Encomendas» que era o último separador daqui (2026-09-11) passou
  // a separador de topo a 2026-09-17 («tiras esta funcionalidade dos decks»).
  // As abas por deck que viviam no antigo separador «Faltas» até 2026-09-15
  // (Staples, Por deck, Pimp decks): o contador só se sabe depois do
  // `compras.json`.
  for (const t of DECK_FALTA_TABS) {
    const b = document.createElement('button');
    b.className = 'tab' + (state.deckId === t.id ? ' is-on' : '');
    b.innerHTML = `${t.label}<small>${contadorFalta(t.id) || t.sub}</small>`;
    b.onclick = () => loadDeckFaltas(t.id);
    nav.appendChild(b);
  }
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
  $('#deck-body').innerHTML = '<p class="empty">a carregar…</p>';
  state.deck = await getJSON(`api/deck/${deckId}.json`);
  renderDeck();
}

function renderDeck() {
  const p = state.deck;
  const idx = state.decks.find(d => d.id === p.id) || {};
  const L = p.legality;

  const chip = (ok, txt) => `<span class="chip-l ${ok ? 'ok' : 'bad'}">${txt}</span>`;
  const pct = idx.wanted ? (idx.have / idx.wanted) * 100 : 0;

  $('#deck-head').innerHTML = `
    <div class="deck-card">
      <div class="deck-title">
        <b>${escapeHTML(p.name)}</b>
        <span class="prio">${p.priority === 1 ? 'principal' : `prioridade ${p.priority}`}</span>
        ${p.grupo && p.grupo.variantes ? `<span class="prio grupo">variante de ${
          escapeHTML(p.grupo.irmaos.map(deckCurto).join(', '))}</span>` : ''}
      </div>
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
      ${deckLocais(p)}
      <div class="deck-actions">
        ${state.editable && p.priority !== 1
          ? `<button class="btn" data-act="principal">Tornar principal</button>` : ''}
        ${state.editable ? `<button class="btn" data-act="subir">Subir</button>
          <button class="btn" data-act="descer">Descer</button>` : ''}
        <button class="btn" data-act="csv">Lista de compras (CSV)</button>
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

  $('#deck-body').innerHTML = listas + faltas;

  for (const b of document.querySelectorAll('#deck-head .btn[data-act]')) {
    b.onclick = () => deckAction(b.dataset.act);
  }
  for (const b of document.querySelectorAll('#deck-head .btn[data-loc]')) {
    b.onclick = () => locaisAction(b.dataset.loc);
  }
}

/* ONDE estão as cartas deste deck. As três primeiras somam o que o deck tem
   e dizem onde ele as vai encontrar — no deck já sleevadas, no binder
   Decks/Venda por ir buscar, ou na Coleção, que desde 2026-09-11 conta («se há
   na coleção o deck usa»). O que falta compra-se; se parte disso existe num
   deck de cima, diz-se quantas («disputadas»), só como informação. */
function deckLocais(p) {
  const l = p.locais || {};
  const chip = (mau, txt) => `<span class="chip-l ${mau ? 'bad' : 'ok'}">${txt}</span>`;
  return `<div class="locais-deck">
    <div class="bar-label"><span>Onde estão as cartas deste deck</span></div>
    <div class="chips-l">
      ${chip(false, `no deck ${l.no_deck || 0}`)}
      ${chip(false, `no binder Decks/Venda ${l.no_binder || 0}`)}
      ${chip(false, `na Coleção ${l.na_colecao || 0}`)}
      ${l.ordered ? `<span class="chip-l caminho">a caminho ${l.ordered}</span>` : ''}
      ${chip(l.missing, `a comprar ${l.missing || 0}`)}
      ${l.shared ? chip(true, `${l.shared} disputadas com um deck de cima`) : ''}
      ${l.outras ? `<span class="chip-l outra">noutra versão ${l.outras}</span>` : ''}
      ${l.extra ? chip(true, `a mais neste deck ${l.extra}`) : ''}
      ${runasNaoContadas(p.runas) ? `<span class="chip-l neutra">${p.runas.copies} runas à mão</span>` : ''}
    </div>
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
    ${l.na_colecao && state.editable ? `<small class="nota">As <b>${l.na_colecao}</b>
      da Coleção contam para este deck. Se as sleevares, marca-as para o
      riftvault saber onde estão.</small>` : ''}
    ${l.extra ? `<small class="nota bad">${l.extra} cópias estão marcadas neste
      deck e a lista já não as pede.</small>` : ''}
    ${state.editable ? `<div class="deck-actions">
      <button class="btn" data-loc="propor">Marcar o que este deck usa…</button>
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
      method: 'POST', headers: { 'Content-Type': 'application/json' },
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
      method: 'POST', headers: { 'Content-Type': 'application/json' },
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

   Os `+`/`−` da encomenda e o «Chegou» viveram aqui de 2026-09-11 a
   2026-09-17 («tiras esta funcionalidade dos decks»): passaram para o
   separador «Encomendas». O que fica é a INFORMAÇÃO — «N a caminho», e a
   moldura azul tracejada quando tudo o que faltava já vem a caminho. O
   `missing` do deck já vem descontado do servidor; aqui só se mostra. */
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
  } else if (c.no_binder || (c.no_deck && c.na_colecao)) {
    // De onde vem o que tem, quando não vem todo do mesmo sítio.
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

  return `<div class="dtile ${st}${c.outras ? ' outra-versao' : ''}" data-ck="${escapeAttr(c.card_key)}">
    <div class="art${c.landscape ? ' landscape' : ''}">
      ${src ? `<img src="${src}" alt="${escapeAttr(c.name)}" loading="lazy" decoding="async"
         ${alt ? `data-fallback="${escapeAttr(alt)}"` : ''}>` : ''}
      <span class="need">${c.wanted}×</span>
      <span class="badge">${c.have}/${c.wanted}</span>
    </div>
    <div class="tname" title="${escapeAttr(c.name)}">${escapeHTML(c.name)}</div>
    ${codeLine(c)}
    ${nota}
  </div>`;
}

/* «Separa as versões por Art» (André, 2026-09-17): uma linha do deck servida
   por mais do que uma impressão reparte-se, uma sub-linha por versão —
   «2 normal · UNL-176» / «1 Alt Art · UNL-176a». Servida por uma impressão
   só, não se enche o tile: se essa única impressão for OUTRA versão (a base
   não chegou e a alt art tapou tudo), diz-se numa linha corrida. */
function versoesNota(c) {
  const vs = c.versoes || [];
  const cod = x => escapeHTML((x.code || x.id || '?').split('/')[0]);
  if (vs.length > 1) {
    return `<div class="onde versoes">${vs.map(x =>
      `<span class="${x.lugar === 'outra' ? 'outra' : ''}">${x.qty} ${escapeHTML(x.label)} · ${cod(x)}</span>`
    ).join('')}</div>`;
  }
  if (vs.length === 1 && c.outras) {
    return `<div class="onde versoes"><span class="outra">em ${escapeHTML(vs[0].label)} · ${cod(vs[0])}</span></div>`;
  }
  return '';
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
  const ids = state.decks.map(d => d.id);
  const i = ids.indexOf(state.deckId);
  let novo = ids.slice();
  if (act === 'principal') { novo.splice(i, 1); novo.unshift(state.deckId); }
  if (act === 'subir' && i > 0) { [novo[i - 1], novo[i]] = [novo[i], novo[i - 1]]; }
  if (act === 'descer' && i < ids.length - 1) { [novo[i + 1], novo[i]] = [novo[i], novo[i + 1]]; }
  try {
    const r = await fetch('api/decks/order', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ids: novo }),
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    state.decks = (await r.json()).decks;
    renderDeckTabs();
    await loadDeck(state.deckId);   // a alocação mudou para toda a gente
    toast('Ordem alterada — a alocação foi refeita.');
  } catch (err) {
    toast(`Não deu para reordenar: ${err.message}`, { error: true });
  }
}

function exportCSV() {
  const p = state.deck;
  const linhas = [['seccao', 'carta', 'pedidas', 'tenho', 'faltam', 'onde_estao']];
  for (const s of p.sections) {
    for (const c of s.cards) {
      // Uma runa não se conta — nem falta, nem entra na lista de compras.
      if (!c.missing || c.contado === false) continue;
      linhas.push([s.label, c.name, c.wanted, c.have, c.missing,
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
    b.className = 'tab' + (s.id === state.enc.setId ? ' is-on' : '');
    const n = porSet.get(s.id) || 0;
    b.innerHTML = `${s.name}<small>${n ? `${n} a caminho` : 'nada a caminho'}</small>`;
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
        escapeHTML(rarityLabel(p.rarity_min))}, ou fora do catálogo da RiftScribe):
      ${fora.map(x => `<span class="enc-fora-item">${x.qty}× ${escapeHTML(x.name || x.printing_id)}
        <i>${escapeHTML((x.code || '').split('/')[0])}${x.market_only ? ' · fora do catálogo' : ''}</i>
        ${state.editable ? `<button class="btn chegou mini" data-chegou-pid="${escapeAttr(x.printing_id)}"
          title="dar entrada na Coleção">Chegou</button>` : ''}</span>`).join('')}
    </div>` : ''}
    ${state.editable && t.copies ? `<div class="deck-actions">
      <button class="btn" id="enc-chegou-tudo">Chegou tudo (${plural(t.copies, 'cópia', 'cópias')}, todas as edições)</button>
    </div>` : ''}
  </div>`;

  for (const b of document.querySelectorAll('#enc-head [data-chegou-pid]')) {
    b.onclick = () => encChegou(b.dataset.chegouPid, b);
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
      method: 'POST', headers: { 'Content-Type': 'application/json' },
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
async function encChegou(pid, botao) {
  if (!pid) return toast('Não sei que carta é esta.', { error: true });
  if (botao) { botao.disabled = true; botao.textContent = 'a dar entrada…'; }
  try {
    const r = await fetch('api/pending/arrive', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ printing_id: pid }),
    });
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error || `HTTP ${r.status}`);
    const res = await r.json();
    const n = res.arrived.reduce((s, x) => s + x.qty, 0);
    toast(`${n} ${n === 1 ? 'cópia entrou' : 'cópias entraram'} na Coleção.`);
    // No tile: as que chegaram passam de «a caminho» a tidas.
    if (state.enc.ordered.has(pid)) {
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
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}',
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

/* Os separadores de cima. `faltas-edicao` é o separador «Faltas» de
   2026-09-15 (o id `faltas` era o da tabela de preços, apagada a 2026-09-19);
   `a-mais` é o «A mais» de 2026-09-17; `encomendas` é o separador
   «Encomendas» do mesmo dia. */
const SECCOES = ['colecao', 'decks', 'faltas-edicao', 'a-mais', 'encomendas'];

function showSection(name) {
  state.prefs.section = name;
  savePrefs();
  for (const s of SECCOES) $('#' + s).hidden = s !== name;
  $('#set-tabs').hidden = name !== 'colecao';
  $('#deck-tabs').hidden = name !== 'decks';
  $('#fe-tabs').hidden = name !== 'faltas-edicao';
  $('#am-tabs').hidden = name !== 'a-mais';
  $('#enc-tabs').hidden = name !== 'encomendas';
  for (const b of document.querySelectorAll('#section-tabs .tab')) {
    b.classList.toggle('is-on', b.dataset.section === name);
  }
  // Uma encomenda ou um «Chegou» mudou o que a grelha da Coleção diz («N a
  // caminho» nos decks, as cópias na caixa): relê-se a edição aberta.
  if (name === 'colecao' && state.colecaoVelha && state.setId) {
    state.colecaoVelha = false;
    loadSet(state.setId).catch(err => toast(err.message, { error: true }));
  }
  if (name === 'encomendas' && !state.enc.payload) loadEncomendas().catch(err =>
    $('#enc-grid').innerHTML = `<p class="empty">${escapeHTML(err.message)}</p>`);
  if (name === 'decks' && !state.decks) loadDecks().catch(err =>
    $('#deck-body').innerHTML = `<p class="empty">${escapeHTML(err.message)}</p>`);
  if (name === 'faltas-edicao' && !state.faltasEdicao) loadFaltasEdicao().catch(err =>
    $('#fe-body').innerHTML = `<p class="empty">${escapeHTML(err.message)}</p>`);
  if (name === 'a-mais' && !state.aMais) loadAMais().catch(err =>
    $('#am-body').innerHTML = `<p class="empty">${escapeHTML(err.message)}</p>`);
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
const DECK_FALTA_IDS = DECK_FALTA_TABS.map(t => t.id);

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
      o que um deck não recebe compra-se, mesmo que exista num deck de cima.
      A aba <i>Por deck</i> reparte este mesmo número por prioridade${
        (f.por_deck || []).some(d => d.grupo && d.grupo.variantes)
          ? ' — excepto nos decks com a <b>mesma Legend</b>, que partilham as cartas: cada um mostra a sua lista, mas a compra é uma e aqui conta uma vez'
          : ''}.</small>
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
   aparece marcada e não vai para nenhuma das duas.                          */

async function loadFaltasEdicao() {
  $('#fe-body').innerHTML = '<p class="empty">a carregar…</p>';
  state.faltasEdicao = await getJSON('api/faltas_edicao.json');
  renderFeTabs();
  renderFaltasEdicao();
}

function renderFeTabs() {
  const nav = $('#fe-tabs');
  const p = state.faltasEdicao;
  nav.innerHTML = '';
  if (state.prefs.feSet !== 'all' && !p.sets.some(s => s.set === state.prefs.feSet)) {
    state.prefs.feSet = 'all';
  }
  const botoes = [{ set: 'all', name: 'Todas', sub: feCurto(p.totals) },
                  ...p.sets.map(s => ({ ...s, sub: feCurto(s) }))];
  for (const s of botoes) {
    const b = document.createElement('button');
    b.className = 'tab' + (s.set === state.prefs.feSet ? ' is-on' : '');
    b.innerHTML = `${escapeHTML(s.name)}<small>${escapeHTML(s.sub)}</small>`;
    b.onclick = () => { state.prefs.feSet = s.set; savePrefs(); renderFeTabs(); renderFaltasEdicao(); };
    nav.appendChild(b);
  }
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
      O que vem a caminho aparece marcado e não vai para nenhuma lista.
      Preço mais baixo em Near Mint/Mint no CardTrader, só ofertas em inglês.${
      fora.length ? `<br>Fora deste separador: ${fora.join(', ')} — não estão em nenhum dos ${quantos} blocos.` : ''}</small>
  </div>`;

  $('#fe-body').innerHTML = sets.map(s => `
    <h2 class="section-head fe-set">${escapeHTML(s.name)}
      <span>${feResumo(s)}</span></h2>
    ${s.blocks.map(g => `
      <h3 class="section-head sub fe-bloco ${g.id}${g.in_lists ? '' : ' fe-ver'}">${escapeHTML(g.label)}
        <small>${escapeHTML(g.target_label)}${g.in_lists ? '' : ' · wantlist própria'}</small>
        <span>${feResumo(g)}</span></h3>
      ${g.items.length
        ? `<div class="grid deck-grid fe-grid">${g.items.map(feTile).join('')}</div>`
        : `<p class="empty fe-vazio">${g.scope ? 'Nada falta neste bloco.' : 'Esta edição não tem impressões neste bloco.'}</p>`}
      ${feWantlistHTML(s, g)}`).join('')}`).join('');

  // As caixas vêm preenchidas, como as da Coleção: a wantlist está ali, sem
  // carregar em nada. Uma por (edição, bloco), com id próprio para as
  // botões não colidirem.
  for (const s of sets) {
    for (const g of s.blocks) {
      const itens = feWantlistItens(g);
      if (!itens.length) continue;
      const zid = feWlId(s, g) + '-cm';
      cmLigar(zid, () => feWantlistItens(g), `riftvault-faltas-${s.set}-${g.id}-${hojeISO()}.csv`);
      cmMostrar(zid, itens, false, { foco: false, copiar: false });
    }
  }
}

/* A wantlist de um bloco é só o que há a COMPRAR — o que vem a caminho está
   nos tiles, marcado, e não vai para o Cardmarket (a da Coleção faz o mesmo).
   Gémeo do `faltas_edicao.wantlist` em Python; há teste que compara o texto. */
function feWantlistItens(g) {
  return g.items.filter(x => x.missing > 0);
}

function feWlId(s, g) {
  return `fe-wl-${s.set}-${g.id}`;
}

function feWantlistHTML(s, g) {
  const itens = feWantlistItens(g);
  if (!itens.length) return '';
  const w = g.wantlist || {};
  return `<section class="wl-bloco fe-wl" id="${feWlId(s, g)}">
    <h4 class="wl-head fe-wl-head">Wantlist — ${escapeHTML(s.name)} · ${escapeHTML(g.label)}
      <span>${plural(w.lines != null ? w.lines : itens.length, 'linha', 'linhas')} ·
        ${plural(w.copies != null ? w.copies : itens.reduce((n, x) => n + cmQtd(x), 0), 'cópia', 'cópias')}
        · ${eur(w.cents != null ? w.cents : itens.reduce((n, x) => n + (x.total || 0), 0))}</span></h4>
    ${cmZonaHTML(feWlId(s, g) + '-cm')}
  </section>`;
}

/* Um tile: a arte, «faltam N» no canto (ou «a caminho» quando o pendente
   cobre tudo), o total no outro canto, «tens H/T» em baixo. */
function feTile(x) {
  const cls = x.missing > 0 ? 'gone' : 'a-caminho';
  const crachá = x.missing > 0 ? `faltam ${x.missing}` : 'a caminho';
  return `<div class="dtile ${cls}">
    ${artHTML(x, `<span class="need">${crachá}</span>
      <span class="ja-tens">tens ${x.have}/${x.target}</span>
      ${x.price != null && x.missing > 0 ? `<span class="price">${eurShort(x.total)}</span>` : ''}`)}
    <div class="tname" title="${escapeAttr(x.name)}">${escapeHTML(x.name)}${
      x.label && x.label !== 'Base' ? ` <i class="var">${escapeHTML(x.label)}</i>` : ''}</div>
    <div class="codigo">${escapeHTML((x.code || '').split('/')[0])}${
      x.price != null ? ` · ${eur(x.price)}` : ' · sem preço'}</div>
    ${x.pending ? `<div class="onde caminho">${x.pending} a caminho${
      x.missing > 0 ? ` · ${x.missing} por comprar` : ''}</div>` : ''}
  </div>`;
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

async function loadAMais() {
  $('#am-body').innerHTML = '<p class="empty">a carregar…</p>';
  state.aMais = await getJSON('api/a_mais.json');
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
    b.className = 'tab' + (s.set === state.prefs.amSet ? ' is-on' : '');
    b.innerHTML = `${escapeHTML(s.name)}<small>${escapeHTML(s.sub)}</small>`;
    b.onclick = () => { state.prefs.amSet = s.set; savePrefs(); renderAmTabs(); renderAMais(); };
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
      Isto só mostra: não muda alvos nem contas, e não é uma lista de venda.${runasFora}${
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
      x.hidden ? ` · <i>${escapeHTML(x.block_label)}, sem alvo</i>` : ''}</div>
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
function cmMostrar(id, itens, comCodigo, { foco = true, copiar = true } = {}) {
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
  const foil = linhas.filter((_, i) => itens[i].foil_only);
  fnota.hidden = !foil.length;
  if (foil.length) {
    const porque = `O texto da wantlist não leva marca de foil — depois de
         colares, liga o filtro <i>Foil</i> nestas entradas.`;
    fnota.innerHTML = `<b>${foil.length} ${foil.length === 1 ? 'destas só tem'
      : 'destas só têm'} oferta foil no mercado.</b> ${porque}
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

function escapeHTML(s) {
  return String(s ?? '').replace(/[&<>]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
}
function escapeAttr(s) {
  return escapeHTML(s).replace(/"/g, '&quot;');
}

boot().catch(err => {
  $('#grid').innerHTML = `<p class="empty">Falhou a carregar: ${escapeHTML(err.message)}<br>
    <small>Se é a primeira vez, corre <code>riftvault sync</code>.</small></p>`;
});

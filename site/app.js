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
  // printing_id -> bloco da grelha. A Coleção são três blocos seguidos —
  // 'master' (a sequência, em playset — mas as runas a 1), 'rune_special'
  // (1 de cada) e 'alt_art' (1 de cada) — e os três contam para a
  // percentagem. O que ficou fora da
  // coleção vai para blocos próprios no fim. Ver `metrics.BLOCOS`.
  blocks: new Map(),
  // Os ids de bloco que entram na percentagem, ditos pelo payload (`counts`).
  // A regra vive no servidor; aqui só se recalcula para as barras andarem ao
  // mesmo tempo que os +/-.
  counting: new Set(),
  // A contagem por níveis (1 de cada, 2 de cada, playset) POR EDIÇÃO:
  // set_id -> [{k, done, total, missing, cents}]. Começa com os números do
  // `api/index.json` e a edição que estiver aberta passa a ser recalculada
  // localmente, como as barras. O global é a soma — todos os campos são somas,
  // por isso editar uma edição não estraga as outras quatro.
  levels: new Map(),
  meta: new Map(),             // printing_id -> {name, card_key, rarity}
  pending: new Map(),          // card_key -> pedidos por responder
  tiles: [],                   // impressões visíveis, pela ordem do ecrã
  focus: -1,
  // Default: TODAS as impressões (decisão do André). O botão "Só artes base"
  // continua lá, mas não é o que se vê ao abrir.
  decks: null, deckId: null, deck: null, faltas: null, venda: null,
  // O `faltas.json` a caminho (as wantlists da Coleção e a secção Faltas comem
  // o mesmo ficheiro), e se as contagens já mudaram desde que ele chegou.
  faltasP: null, wlStale: false,
  prefs: { view: 'all', stateFilter: 'all',
           kinds: ['base', 'alt_art', 'signature', 'other'],
           set: null, deck: null, falta: 'staples', faltaDeck: 0, pimpDeck: 'todos',
           // "A subir": qual das duas abas (por % / por valor) e o filtro de
           // raridade, ambos guardados como o resto das escolhas.
           subirOrd: 'pct', subirRar: 'all',
           // As wantlists da Coleção: até que nível se compra (1, 2, … ) ou
           // `null` para o alvo inteiro — o playset da sequência.
           wlNivel: null,
           // "Master set": qual a edição escolhida no filtro da lista de faltas.
           masterSet: 'all',
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
  const wanted = state.index.sets.some(s => s.id === state.prefs.set) ? state.prefs.set : (first && first.id);
  if (wanted) await loadSet(wanted);
  showSection(['decks', 'faltas', 'venda'].includes(state.prefs.section)
    ? state.prefs.section : 'colecao');
}

async function loadSet(setId) {
  state.setId = setId;
  state.prefs.set = setId;
  savePrefs();
  renderSetTabs();

  $('#grid').innerHTML = '<p class="empty">a carregar…</p>';
  const p = await getJSON(`api/set/${setId}.json`);
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
}

/* --------------------------------------------------------------- separadores */

function renderSetTabs() {
  const nav = $('#set-tabs');
  nav.innerHTML = '';
  for (const s of (state.index?.sets || [])) {
    const b = document.createElement('button');
    b.className = 'tab' + (s.id === state.setId ? ' is-on' : '');
    b.innerHTML = `${s.name}<small>${s.n_printings} impressões</small>`;
    b.onclick = () => loadSet(s.id);
    nav.appendChild(b);
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
  return list;
}

/* ----------------------------------------------------------------- render */

function imgSrc(p) {
  return state.imageMode === 'remote' ? (p.cdn || p.img) : (p.img || p.cdn);
}
function imgAlt(p) {
  return state.imageMode === 'remote' ? (p.img || '') : (p.cdn || '');
}

function tileHTML(g, p) {
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
  </div>`;
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
  if (label.startsWith('Deck ')) return label.slice(5).split(' · ')[0];
  if (label.startsWith('Binder ')) return label.slice(7);
  return label;
}

/* A grelha em blocos (André, 2026-09-08): *"master set playset todo seguido; 1
   runa especial de cada para cada set; no fim 1 alt art de cada"*. Primeiro a
   sequência do master set, por número de coleção; depois as runas especiais;
   depois as artes alternativas; e só no fim o que ficou FORA da coleção (hoje
   os tokens). Nunca intercalados.

   Os blocos e os rótulos vêm do payload (`metrics.BLOCOS`), para a regra viver
   num sítio só; o contador de cada um é recalculado aqui, como as barras, para
   andar ao mesmo tempo que os +/-. */
function render() {
  const grid = $('#grid');
  const parts = [];
  state.tiles = [];

  const grupos = state.payload?.groups || [];
  const blocos = state.payload?.blocks || [{ id: 'master', label: null }];
  let mostrados = 0;

  for (const b of blocos) {
    const pedacos = [];
    let feitas = 0, total = 0;
    for (const g of grupos) {
      const list = visiblePrintings(g).filter(p => (p.block || 'master') === b.id);
      if (!list.length) continue;
      for (const p of list) {
        const t = state.targets.get(p.id) || 0;
        if (t <= 0) continue;
        total++;
        if ((state.qty.get(p.id) || 0) >= t) feitas++;
      }
      const inner = list.map(p => { state.tiles.push(p.id); return tileHTML(g, p); }).join('');
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
      parts.push(`<h2 class="section-head ${b.counts ? 'cauda' : 'fora'}">${escapeHTML(b.label)}
        <span>tens <b>${feitas}</b> de <b>${total}</b> — ${b.counts ? '' : 'não '}
        contam para a percentagem de master set</span></h2>`);
    }
    parts.push(pedacos.join(''));
  }

  grid.innerHTML = parts.join('');
  $('#empty').hidden = mostrados > 0;
  $('#count-line').textContent = `${state.tiles.length} impressões a mostrar`
    + (state.payload ? ` · ${state.payload.groups.length} cartas na edição` : '');
  renderProgress();
  state.focus = -1;
}

function renderProgress() {
  if (!state.payload) return;

  // Recalculado no cliente a partir do estado local, para as barras andarem
  // ao mesmo tempo que os +/- (atualização otimista).
  let pDone = 0, pTotal = 0, mDone = 0, mTotal = 0;
  const seen = new Set();
  const rar = new Map();
  const porBloco = new Map();
  // Os degraus da contagem por níveis vêm do servidor (são os do catálogo
  // inteiro, para as cinco edições se compararem); os números recalculam-se
  // aqui, no mesmo ciclo da barra — é o mesmo âmbito, e a percentagem do
  // último nível tem de continuar a dar exactamente a da barra.
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
        // `min(k, alvo)`: uma impressão de alvo 1 — runa, Legend, arte
        // alternativa — só pode faltar no nível 1; do 2 em diante já está feita.
        const falta = Math.max(0, Math.min(nv.k, t) - tem);
        nv.total++; nv.missing += falta; nv.cents += falta * (p.price || 0);
        if (!falta) nv.done++;
      }
      const key = g.rarity || '?';
      const slot = rar.get(key) || [0, 0];
      slot[1]++; if (ok) slot[0]++;
      rar.set(key, slot);
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

  if (niv.length) state.levels.set(state.setId, niv);
  renderNiveis(niv);

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
    $('#value-num').textContent = eur(owned);
    $('#value-bar').style.width = val.full ? `${Math.min(100, (owned / val.full) * 100)}%` : '0';
    $('#value-sub').textContent = `de ${eur(val.full)} se estivesse completa`;
  } else {
    block.hidden = true;
  }

  const order = ['common', 'uncommon', 'rare', 'epic', 'showcase'];
  const rows = [...rar.entries()].sort((a, b) => {
    const ia = order.indexOf(a[0]), ib = order.indexOf(b[0]);
    return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib);
  });
  $('#rarities').innerHTML = rows.map(([k, v]) =>
    `<span class="rarity ${v[0] >= v[1] ? 'is-done' : ''}">${k} <b>${v[0]}/${v[1]}</b></span>`
  ).join('');
}


/* ================================ contagem por níveis do master set

   André, 2026-09-08: *"quantas cartas faltam para ter 1 de cada, quantas
   faltam para ter 2 de cada, quantas faltam para ter o playset de cada — do
   género 1/3 Z % · 2/3 X % · 3/3 Y %."*

   É a MESMA conta da barra do master set, partida em degraus: o alvo do nível k
   é `min(k, alvo)`, por isso as impressões de alvo 1 (as runas, os Legends e os
   Battlefields da sequência, as runas especiais e as artes alternativas) só
   podem faltar no nível 1, e a percentagem do último nível dá exactamente a da
   barra. Conta CÓPIAS, não o que vem a caminho — é a regra da Coleção; as
   wantlists por nível é que descontam o pendente, porque aí a pergunta é o que
   há a comprar.                                                             */

/* Quantos degraus há. Vem do servidor (`metrics.niveis_max`, o maior alvo do
   catálogo inteiro) para as cinco edições mostrarem os mesmos. */
function niveisN() {
  const doSet = state.payload?.progress?.levels;
  if (doSet && doSet.length) return doSet.length;
  return (state.index?.levels?.levels || []).length;
}

/* A soma das edições todas: as da sessão como estão no ecrã, as outras como
   vieram do servidor. Todos os campos são somas, por isso isto é o global. */
function niveisTotal() {
  const n = niveisN();
  if (!n || state.levels.size < 2) return null;
  const out = Array.from({ length: n },
                         (_, i) => ({ k: i + 1, done: 0, total: 0, missing: 0, cents: 0 }));
  for (const ls of state.levels.values()) {
    for (const lv of ls) {
      const nv = out[lv.k - 1];
      if (!nv) continue;                 // edição de outro tempo, com outros degraus
      nv.done += lv.done; nv.total += lv.total;
      nv.missing += lv.missing; nv.cents += lv.cents;
    }
  }
  return out;
}

function renderNiveis(daEdicao) {
  const el = $('#master-niveis');
  if (!el) return;
  // Uma edição sem nada que conte para a barra não tem degraus que mostrar —
  // um "0 %" de um denominador vazio lia-se como coleção por fazer.
  if (!daEdicao || !daEdicao.some(lv => lv.total)) { el.innerHTML = ''; return; }

  const total = niveisTotal();
  const nome = state.payload?.set?.name || state.setId || 'esta edição';
  el.innerHTML =
    niveisLinha(escapeHTML(nome), daEdicao)
    + (total ? niveisLinha(`as ${state.levels.size} edições`, total) : '');
}

function niveisLinha(rotulo, ls) {
  const n = ls.length;
  return `<div class="niveis-linha"><span class="niveis-rot">${rotulo}</span>
    ${ls.map(lv => niveisChip(lv, n)).join('')}</div>`;
}

/* «1/3 · 97 % · faltam 12 · 15,40 €». O euro é o preço de hoje das cópias que
   faltam NESSE nível, e só aparece quando há preços — um "0,00 €" por falta de
   dados lia-se como "não custa nada". */
function niveisChip(lv, n) {
  const pct = lv.total ? Math.round((lv.done / lv.total) * 100) : 0;
  const feito = !lv.missing;
  const rotulo = lv.k === n ? `playset (${lv.k}/${n})` : `${lv.k}/${n}`;
  return `<span class="rarity nivel ${feito ? 'is-done' : ''}"
    title="${lv.done} de ${lv.total} impressões já com ${lv.k} cópia${lv.k === 1 ? '' : 's'}${
      lv.k === n ? ' (ou o alvo delas, se for menor)' : ' ou o alvo delas, se for menor'}"
    >${rotulo} <b>${pct} %</b>${feito ? ' · completo'
      : ` · faltam <b>${lv.missing}</b>${lv.cents ? ` · ${eur(lv.cents)}` : ''}`}</span>`;
}


/* ============================ wantlists do Cardmarket, no fim de cada edição

   André, 2026-09-08: *"Quero também que no fim de cada edição me dês uma
   wantlist para eu colocar no Cardmarket."*

   NÃO É UMA LISTA NOVA. São as mesmas faltas do master set que a aba «Master
   set» mostra — o `api/faltas.json`, chave `master` —, cortadas por edição e
   escritas pelo MESMO gerador (`cmLinha`). Por isso a Coleção passou a pedir
   também o `faltas.json`: é mais barato descarregar um ficheiro que já existe
   do que gerar um segundo com os mesmos dados dentro (medido no relatório).

   Os alvos são os dos três blocos da Coleção — playset na sequência, 1 por
   runa, 1 por runa especial, 1 por arte alternativa — porque vêm do mesmo
   `metrics.master_target` de tudo o resto.

   Dois blocos: o da edição aberta e, a seguir, o de todas as edições pela
   ordem dos separadores.                                                    */

/* Os itens de uma edição (ou de todas, com `setId` a nulo), até ao nível
   pedido.

   O NÍVEL não é uma lista nova: é o mesmo `min(k, alvo)` da contagem por
   níveis, aplicado às faltas que o servidor já mandou. Dá para fazer aqui
   porque cada item traz o `have` (cópias + a caminho) e o `target`; o gémeo em
   Python é o `nivel` do `a_subir.wantlist`, e há teste que compara os dois. */
function wlItens(setId, nivel) {
  const m = state.faltas && state.faltas.master;
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

/* O `faltas.json` é grande e não se pede duas vezes: as wantlists da Coleção e
   a secção Faltas comem o mesmo ficheiro, e quem chegar segundo espera pelo
   pedido que já vai a caminho.

   Só BUSCA — desenhar a secção Faltas é o `loadFaltas`. Se desenhasse aqui, uma
   visita à Coleção montava também os tiles do Pimp e das Staples, com as
   imagens todas, para uma secção que ele pode nunca abrir. */
function garanteFaltas(forcar = false) {
  if (state.faltas && !forcar) return Promise.resolve(state.faltas);
  if (!state.faltasP) {
    state.faltasP = getJSON('api/faltas.json')
      .then(p => { state.faltas = p; return p; })
      .finally(() => { state.faltasP = null; });
  }
  return state.faltasP;
}

/* Volta a pedir o ficheiro e redesenha o que já estiver no ecrã. */
function wlAtualizar(zona) {
  state.wlStale = false;
  zona.innerHTML = '<p class="empty">a atualizar…</p>';
  garanteFaltas(true)
    .then(() => {
      renderWantlists();
      renderFaltaLinha();
      // A secção Faltas vive do mesmo ficheiro; se já foi desenhada uma vez,
      // ficava com os números velhos.
      if ($('#falta-tabs').children.length) { renderFaltaTabs(); renderFaltas(); }
    })
    .catch(err => { zona.innerHTML = `<p class="empty">${escapeHTML(err.message)}</p>`; });
}

function renderWantlists() {
  const zona = $('#wantlists');
  if (!zona) return;

  if (!state.faltas) {
    zona.innerHTML = '<p class="empty">a preparar a wantlist…</p>';
    garanteFaltas()
      .then(() => { renderWantlists(); renderFaltaLinha(); })
      .catch(err => { zona.innerHTML = `<p class="empty">${escapeHTML(err.message)}</p>`; });
    return;
  }
  const m = state.faltas.master;
  if (!m) { zona.innerHTML = ''; return; }   // payload antigo, sem a lista

  const nome = state.payload?.set?.name || state.setId || '';
  const nivel = state.prefs.wlNivel || null;
  const daEdicao = wlItens(state.setId, nivel);
  const todas = wlItens(null, nivel);
  const sufixo = nivel ? `-ate${nivel}` : '';
  // O que o degrau muda na lista, dito por extenso: sem isto, uma lista que
  // encolhe a metade parece que perdeu cartas.
  const doNivel = nivel
    ? ` Está no degrau <b>até ${nivel} de cada</b>: das cartas com playset pede-se
        ${nivel}, e as de alvo <b>1</b> (runas, Legends, Battlefields, runas
        especiais e artes alternativas) vão sempre por inteiro.`
    : '';

  zona.innerHTML = `
    ${state.wlStale ? `<p class="note wl-stale">As contagens mudaram desde que
      esta lista foi feita. <button class="btn ghost" id="wl-refresh">Atualizar</button></p>` : ''}

    ${wlBloco('wl-edicao', `Wantlist Cardmarket — ${escapeHTML(nome)}`, daEdicao,
      `Tudo o que falta desta edição ao <b>master set</b>, pelos alvos dos três
       blocos da Coleção: <b>playset</b> na sequência, <b>1</b> por runa,
       <b>1</b> por runa especial e <b>1</b> por arte alternativa. Conta
       enquanto <b>cópias + a caminho &lt; alvo</b>, e vai por número de
       coleção.${doNivel}${foraTexto(m.scope)}`, nivel)}

    ${wlBloco('wl-tudo', 'Wantlist — tudo', todas,
      `As cinco edições seguidas, na ordem dos separadores. É a mesma lista da
       aba <b>Faltas → Master set</b>, sem o filtro de edição.${doNivel}`, nivel)}`;

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

  wlLigar('wl-edicao', () => wlItens(state.setId, state.prefs.wlNivel || null),
          `riftvault-wantlist-${state.setId}${sufixo}-${hojeISO()}.csv`);
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
  cmMostrar(zid, getItens(), false, 'wantlist', { foco: false, copiar: false });
}

/* A linha no cabeçalho da edição, a ligar ao bloco. Os números são os do
   bloco — não os da barra de progresso —, senão o que ele lê em cima não batia
   certo com a lista para onde a linha o manda. */
function renderFaltaLinha() {
  const el = $('#falta-linha');
  if (!el) return;
  const m = state.faltas && state.faltas.master;
  const d = m && m.sets.find(s => s.set === state.setId);
  el.hidden = !d;
  if (!d) return;
  // Esta linha fica logo por baixo dos chips dos níveis, e os dois números não
  // são o mesmo: o chip é a MÉTRICA (conta os showcases, e não desconta o que
  // vem a caminho) e esta linha é a LISTA DE COMPRA. Vistos lado
  // a lado sem explicação — «faltam 383» em cima, «faltam 360» em baixo — liam-
  // se como erro de contagem. Diz-se a diferença, e só quando ela existe.
  const nv = (state.levels.get(state.setId) || []).slice(-1)[0];
  const difere = nv && nv.missing > d.copies;
  el.innerHTML = `<b>${d.copies}</b> cópia${d.copies === 1 ? '' : 's'}
    <b>a comprar</b> nesta edição · <b>${eur(d.cents)}</b> ao preço de hoje —
    <a href="#wl-edicao">wantlist para o Cardmarket</a>${difere
      ? `<br><small>São menos do que as <b>${nv.missing}</b> do playset aqui em
         cima: a lista de compra não leva showcases e já desconta o que vem a
         caminho.</small>` : ''}`;
}

/* Um `+` ou um `−` desatualiza as duas listas, que vieram do servidor. Não se
   volta a pedir o `faltas.json` sozinho — são centenas de KB e ele pode estar a
   marcar uma caixa inteira de cartas. Diz-se que está velha e ele atualiza
   quando quiser. */
function wlDesatualizar() {
  if (state.wlStale || !state.faltas) return;
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
  // A Venda também tem artes, e ficava de fora desta lista: uma imagem que o
  // cache local ainda não tivesse aparecia partida e não caía para o CDN.
  for (const alvo of ['#grid', '#deck-body', '#falta-body', '#venda-body']) {
    $(alvo).addEventListener('error', imgFallback, true);
  }

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
   prioridade e cada um serve-se do que sobra. Uma carta que falte por já
   estar num deck anterior mostra ONDE está — é diferente de não a ter.      */

async function loadDecks() {
  const d = await getJSON('api/decks.json');
  state.decks = d.decks;
  renderDeckTabs();
  const first = state.decks.some(x => x.id === state.prefs.deck)
    ? state.prefs.deck : (state.decks[0] && state.decks[0].id);
  if (first) await loadDeck(first);
  else $('#deck-body').innerHTML = '<p class="empty">Não há decks. Mete um .txt em <code>decks/</code>.</p>';
}

function renderDeckTabs() {
  const nav = $('#deck-tabs');
  nav.innerHTML = '';
  for (const d of state.decks) {
    const b = document.createElement('button');
    b.className = 'tab' + (d.id === state.deckId ? ' is-on' : '');
    const pct = d.wanted ? Math.round((d.have / d.wanted) * 100) : 0;
    b.innerHTML = `${d.priority === 1 ? '★ ' : ''}${escapeHTML(d.name)}<small>${pct}% · ${d.have}/${d.wanted}</small>`;
    b.onclick = () => loadDeck(d.id);
    nav.appendChild(b);
  }
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
      </div>
      <div class="deck-meta">
        <span><i>Legend</i> ${escapeHTML(p.legend || '—')}</span>
        <span><i>Champion</i> ${escapeHTML(p.champion || '—')}</span>
        <span><i>Domínios</i> ${(L.dominios.legend || []).join(' + ') || '—'}</span>
      </div>
      <div class="bar-label"><span>Cartas alocadas a este deck</span>
        <b>${idx.have || 0}/${idx.wanted || 0}</b></div>
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

  const listas = p.sections.map(s => `
    <h2 class="section-head">${s.label}
      <span>${s.have}/${s.wanted}</span></h2>
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

/* ONDE estão as cartas deste deck (André, 2026-09-10). São quatro respostas
   diferentes e cada uma pede uma acção diferente: as do deck já lá estão, as
   do binder Decks/Venda são para ir buscar, as da Coleção são duplicado a
   comprar ou a decidir, e as que faltam compram-se. */
function deckLocais(p) {
  const l = p.locais || {};
  const chip = (mau, txt) => `<span class="chip-l ${mau ? 'bad' : 'ok'}">${txt}</span>`;
  return `<div class="locais-deck">
    <div class="bar-label"><span>Onde estão as cartas deste deck</span></div>
    <div class="chips-l">
      ${chip(false, `no deck ${l.no_deck || 0}`)}
      ${chip(false, `no binder Decks/Venda ${l.no_binder || 0}`)}
      ${chip(l.na_colecao, `na Coleção ${l.na_colecao || 0}`)}
      ${chip(l.missing, `a comprar ${l.missing || 0}`)}
      ${l.extra ? chip(true, `a mais neste deck ${l.extra}`) : ''}
    </div>
    ${l.na_colecao ? `<small class="nota">As <b>${l.na_colecao}</b> que estão nos
      binders de coleção não montam este deck — são duplicado a comprar ou a
      decidir. Marca as que estão mesmo no deck.</small>` : ''}
    <small class="nota">Cada deck é independente: o que está noutro deck não
      desconta a falta. Nas <b>comuns e incomuns</b> a Coleção fica com as
      dela — o deck compra as suas${l.colecao_fica
        ? `, e são <b>${l.colecao_fica}</b> cópias das que tens na Coleção` : ''}.</small>
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

/* Mover cópias mexe na Coleção, nos decks todos e na Venda: as três leituras
   vêm dos mesmos locais. Recarrega-se o que está no ecrã e marca-se o resto
   como velho. */
async function recarregarDepoisDeMover() {
  state.decks = (await getJSON('api/decks.json')).decks;
  renderDeckTabs();
  await loadDeck(state.deckId);
  state.venda = null;
  if (state.setId) await loadSet(state.setId);
  // Depois do `loadSet`: as wantlists vêm do `faltas.json`, que não se volta a
  // pedir sozinho — são centenas de KB. Fica marcado como velho, com o botão.
  wlDesatualizar();
}

/* Tile de deck: a mesma linguagem visual da Coleção, mas o que interessa aqui
   é quantas o deck pede e quantas estão de facto alocadas. */
function deckTile(c) {
  // «na Coleção» é um estado próprio desde 2026-09-10: a carta existe, mas
  // está nos binders de coleção e não monta este deck. Não é o mesmo que não a
  // ter, nem o mesmo que estar noutro deck — e desde 2026-09-11 «noutro deck»
  // já não é um estado: cada deck é independente, e o que está noutro deck
  // compra-se na mesma. Fica só a nota de onde ela também está.
  const st = c.missing ? (c.na_colecao ? 'shared' : 'gone') : 'ok';
  const src = state.imageMode === 'remote' ? (c.cdn || c.img) : (c.img || c.cdn);
  const alt = state.imageMode === 'remote' ? (c.img || '') : (c.cdn || '');

  let nota = '';
  if (c.shared) {
    nota = `<div class="onde falta">faltam ${c.missing} — também ${c.shared.em
      .map(h => `${h.qty}× em «${escapeHTML(h.deck.split(' · ')[0])}»`
        + (h.onde === 'colecao' ? ' (na Coleção)' : '')).join(', ')}</div>`;
  } else if (c.na_colecao) {
    const comprar = c.missing - c.na_colecao;
    nota = `<div class="onde shared">${c.na_colecao} na Coleção — mover ou comprar${
      comprar > 0 ? ` · ${comprar} a comprar` : ''}</div>`;
  } else if (c.missing && c.colecao_fica) {
    // Ele TEM-nA, mas é comum ou incomum: a Coleção fica com as dela e este
    // deck compra as suas (André, 2026-09-11). Dizer só «faltam N» era mentira.
    nota = `<div class="onde falta">${c.missing} a comprar — a Coleção fica com
      ${c.colecao_fica === 1 ? 'a que tens' : `as ${c.colecao_fica} que tens`}</div>`;
  } else if (c.missing) {
    nota = `<div class="onde falta">faltam ${c.missing}</div>`;
  } else if (c.no_binder) {
    nota = `<div class="onde tenho">${c.no_binder} por ir buscar ao binder
      Decks/Venda${c.no_deck ? ` · ${c.no_deck} já no deck` : ''}</div>`;
  } else if (c.printings.length) {
    nota = `<div class="onde tenho">${c.printings
      .map(x => `${x.qty}× ${escapeHTML(x.code || x.id)}`).join(' · ')}</div>`;
  }

  return `<div class="dtile ${st}">
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
    ${(x.also || []).length ? `<div class="onde tenho">também em ${x.also.join(', ')}</div>` : ''}
  </div>`;
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
      if (!c.missing) continue;
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

function showSection(name) {
  state.prefs.section = name;
  savePrefs();
  for (const s of ['colecao', 'decks', 'faltas', 'venda']) $('#' + s).hidden = s !== name;
  $('#set-tabs').hidden = name !== 'colecao';
  $('#deck-tabs').hidden = name !== 'decks';
  $('#falta-tabs').hidden = name !== 'faltas';
  for (const b of document.querySelectorAll('#section-tabs .tab')) {
    b.classList.toggle('is-on', b.dataset.section === name);
  }
  if (name === 'decks' && !state.decks) loadDecks().catch(err =>
    $('#deck-body').innerHTML = `<p class="empty">${escapeHTML(err.message)}</p>`);
  // O `loadFaltas` passa pelo `garanteFaltas`: a Coleção já pode ter pedido o
  // mesmo ficheiro para as wantlists do fim da página, e não se pede duas vezes.
  if (name === 'faltas' && !state.faltas) loadFaltas().catch(err =>
    $('#falta-body').innerHTML = `<p class="empty">${escapeHTML(err.message)}</p>`);
  if (name === 'venda' && !state.venda) loadVenda().catch(err =>
    $('#venda-body').innerHTML = `<p class="empty">${escapeHTML(err.message)}</p>`);
}


/* ========================================================== SECÇÃO FALTAS

   Três leituras da mesma carência. A carência é GLOBAL — soma-se o que todos
   os decks pedem e desconta-se o que ele tem — e não a alocação por
   prioridade, que responde a outra pergunta (quem fica com o quê).          */

const FALTA_TABS = [
  { id: 'staples', label: 'Staples', sub: 'pedidas por vários decks' },
  { id: 'deck', label: 'Por deck', sub: 'o que falta a cada um' },
  { id: 'spike', label: 'A subir', sub: 'do master set, o que ainda não tens' },
  { id: 'master', label: 'Master set', sub: 'tudo o que falta à coleção' },
  { id: 'pimp', label: 'Pimp decks', sub: 'versões alteradas das cartas dos decks' },
  { id: 'caminho', label: 'A caminho', sub: 'comprado, ainda não chegou' },
];

async function loadFaltas() {
  await garanteFaltas();
  renderFaltaTabs();
  renderFaltas();
}

function renderFaltaTabs() {
  const nav = $('#falta-tabs');
  nav.innerHTML = '';
  const f = state.faltas;
  for (const t of FALTA_TABS) {
    const b = document.createElement('button');
    b.className = 'tab' + (t.id === state.prefs.falta ? ' is-on' : '');
    let n = '';
    if (t.id === 'staples') n = plural(f.staples.length, 'carta', 'cartas');
    if (t.id === 'deck') n = plural(f.por_deck.reduce((s, d) => s + d.copies, 0), 'cópia', 'cópias');
    if (t.id === 'spike') n = f.a_subir.ready
      ? plural(f.a_subir.items.length, 'carta', 'cartas') : 'sem histórico';
    if (t.id === 'master') n = plural(f.master.copies, 'cópia', 'cópias');
    if (t.id === 'pimp') n = plural(f.pimp.by_deck.reduce((s, d) => s + d.printings, 0),
                                    'versão', 'versões');
    if (t.id === 'caminho') n = f.pending.copies
      ? plural(f.pending.copies, 'cópia', 'cópias') : 'nada';
    b.innerHTML = `${t.label}<small>${n}</small>`;
    b.onclick = () => { state.prefs.falta = t.id; savePrefs(); renderFaltaTabs(); renderFaltas(); };
    nav.appendChild(b);
  }
}

/* O cabeçalho é a carência GLOBAL DOS DECKS (`faltas.shortfall`): tudo o que
   os decks pedem, com o teto do playset, menos o que ele tem e o que vem a
   caminho. Só descreve duas das seis abas — as Staples e o Por deck — e nas
   outras estava a mentir: por cima de «614 impressões em falta · 21 567,33 €»
   do master set lia-se «Falta comprar 25 cartas · 34 cópias · 356,91 €», que é
   outra pergunta. Por isso passou a ter o âmbito no título e a aparecer só
   onde é a conta da página (ver `FALTA_HEAD`). */
const FALTA_HEAD = ['staples', 'deck'];

function faltaHead() {
  const f = state.faltas;
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
    <small class="nota">Soma o que <b>todos</b> os decks pedem, até ao playset
      de cada carta. A aba <i>Por deck</i> pode dar menos: aí uma carta que dois
      decks peçam compra-se uma vez e troca-se entre eles.</small>
  </div>`;
}

function renderFaltas() {
  const f = state.faltas;
  const which = state.prefs.falta;
  $('#falta-head').innerHTML = FALTA_HEAD.includes(which) ? faltaHead() : '';

  if (which === 'staples') {
    $('#falta-body').innerHTML = f.staples.length ? `
      <p class="note">Cartas que <b>mais do que um deck</b> pede e que não tens
        em número suficiente. São as que rendem mais por euro — uma compra
        serve vários decks.</p>
      <div class="grid deck-grid">${f.staples.map(staplTile).join('')}</div>`
      : '<p class="empty">Nenhuma carta é pedida por dois decks ao mesmo tempo.</p>';
    return;
  }

  if (which === 'deck') {
    renderPorDeck();
    return;
  }

  if (which === 'master') {
    renderMasterFaltas();
    return;
  }

  if (which === 'pimp') {
    renderPimp();
    return;
  }

  if (which === 'caminho') {
    renderCaminho();
    return;
  }

  renderASubir();
}


/* ------------------------------------------------------- "A subir"

   O que ainda FALTA do master set e está a ficar mais caro. Duas abas sobre a
   mesma lista — por % e por valor — porque são duas perguntas diferentes: uma
   é "o que está a disparar", a outra "o que me vai custar caro se esperar".

   A ordem das duas vem do servidor (`rank_pct` e `rank_valor`), para os
   critérios de desempate viverem num sítio só.                             */

/* O que o `a_subir.excluir` tirou, por critério — o mesmo texto nas duas listas
   de compra. Por critério porque as signatures também são de raridade showcase:
   um número só não dizia quantas saíram por serem uma coisa ou a outra. */
function foraTexto(scope) {
  if (!scope.excluded) return '';
  const motivos = (scope.excluded_by || [])
    .map(c => `${c.n} ${escapeHTML(c.criterio)}`).join(' + ');
  return `<br>Fora da lista: <b>${scope.excluded}</b> impressões
    (${motivos}) — continuam a contar na percentagem de master set,
    só não entram nas listas de compra. A exclusão é da <b>sequência</b>: as
    runas especiais e as artes alternativas entram na mesma, 1 de cada.`;
}

function renderASubir() {
  const sp = state.faltas.a_subir;

  if (!sp.ready) {
    $('#falta-body').innerHTML = `<div class="aviso">
      <b>Ainda não há com que comparar.</b>
      <p>${sp.days_recorded
        ? `Já há ${sp.days_recorded === 1 ? 'um dia' : `${sp.days_recorded} dias`} de preços
           gravados${sp.first ? ` (desde ${sp.first})` : ''}, mas <b>nenhuma</b> das cartas
           seguidas tem preço com que comparar.`
        : 'Ainda não há preços gravados.'}</p>
      <p>O histórico só escreve quando o preço <em>muda</em>, por isso é normal
      demorar uns dias a encher. Corre <code>riftvault prices</code> de vez em
      quando e esta aba começa a dizer alguma coisa.</p>
      <p>São seguidas <b>${sp.tracked || 0} impressões</b> — as do master set
      que ainda te faltam.</p>
    </div>`;
    return;
  }

  const rar = state.prefs.subirRar;
  const lista = sp.items.filter(x => rar === 'all' || x.rarity === rar);
  const ord = state.prefs.subirOrd === 'valor' ? 'valor' : 'pct';
  lista.sort((a, b) => (ord === 'valor' ? a.rank_valor - b.rank_valor
                                        : a.rank_pct - b.rank_pct));

  const cents = lista.reduce((s, x) => s + x.buy_cents, 0);
  const copias = lista.reduce((s, x) => s + x.missing, 0);
  // Quantas ainda não têm histórico que cubra a janela inteira. Enquanto o
  // `prices.db` for novo são todas, e a página tem de o dizer.
  const parciais = lista.filter(x => !x.full_window).length;

  $('#falta-body').innerHTML = `
    <div class="seg seg-wrap">
      <button class="seg-btn ${ord === 'pct' ? 'is-on' : ''}" data-subir="pct">
        Por % <b>${sp.items.length}</b></button>
      <button class="seg-btn ${ord === 'valor' ? 'is-on' : ''}" data-subir="valor">
        Por valor <b>${eurShort(sp.totals.cents)}</b></button>
    </div>

    <div class="deck-card resumo">
      <b>${lista.length} carta${lista.length === 1 ? '' : 's'} a subir</b>
      <span>${copias} cópia${copias === 1 ? '' : 's'} · ${eur(cents)} para as comprar
        hoje · ${eur(lista.reduce((s, x) => s + x.extra_cents, 0))} do que já subiu</span>
    </div>

    <p class="note">Do <b>master set</b> (${sp.scope.printings} impressões nas
      ${sp.scope.sets.length} edições), só o que <b>ainda te falta</b>:
      ${sp.tracked} impressões seguidas, das quais ${sp.comparable} já têm preço
      com que comparar. Mostram-se as que subiram
      <b>${sp.min_pct}%</b> ou mais nos últimos <b>${sp.window_days} dias</b>.
      Assim que compras a carta, ela sai daqui.
      ${parciais ? `<br><b>${parciais}</b> ainda não têm ${sp.window_days} dias
        de histórico — nessas a comparação é <i>desde</i> a data indicada, não
        da janela toda.` : ''}
      ${foraTexto(sp.scope)}</p>

    <div class="chips subir-rar">
      <button class="chip-b ${rar === 'all' ? 'is-on' : ''}" data-srar="all">
        todas <b>${sp.items.length}</b></button>
      ${sp.rarities.map(r => `
        <button class="chip-b ${rar === r.rarity ? 'is-on' : ''}" data-srar="${escapeAttr(r.rarity)}">
          ${escapeHTML(r.rarity)} <b>${r.n}</b></button>`).join('')}
    </div>

    ${lista.length ? `<div class="subir-lista">${lista.map(subirLinha).join('')}</div>`
      : `<p class="empty">Nenhuma carta desta raridade subiu ${sp.min_pct}% ou
         mais nos últimos ${sp.window_days} dias.</p>`}
    ${lista.length ? cmZonaHTML('subir') : ''}`;

  // As listas saem do que está à vista: a raridade escolhida e a ordem da aba.
  if (lista.length) cmLigar('subir', () => lista, `riftvault-a-subir-${hojeISO()}.csv`);

  for (const b of document.querySelectorAll('[data-subir]')) {
    b.onclick = () => {
      state.prefs.subirOrd = b.dataset.subir; savePrefs(); renderASubir();
    };
  }
  for (const b of document.querySelectorAll('[data-srar]')) {
    b.onclick = () => {
      state.prefs.subirRar = b.dataset.srar; savePrefs(); renderASubir();
    };
  }
}

function subirLinha(x) {
  const sp = state.faltas.a_subir;
  const src = state.imageMode === 'remote' ? (x.cdn || x.img) : (x.img || x.cdn);
  const alt = state.imageMode === 'remote' ? (x.img || '') : (x.cdn || '');
  // Δ da janela curta: pode não haver leitura anterior ao limite dela, e aí a
  // percentagem é desde a data que houver — vai marcada com ~.
  const curto = x.pct_short == null ? ''
    : `<small class="d7" title="${x.short_full ? `últimos ${sp.short_days} dias`
        : `desde ${x.short_since}`}">${sp.short_days} d ${
        x.short_full ? '' : '~'}${fmtPct(x.pct_short)}</small>`;

  return `<div class="subir-row">
    <div class="subir-art${x.landscape ? ' landscape' : ''}">
      ${src ? `<img src="${src}" alt="${escapeAttr(x.name)}" loading="lazy" decoding="async"
         ${alt ? `data-fallback="${escapeAttr(alt)}"` : ''}>` : ''}
    </div>

    <div class="subir-main">
      <div class="subir-nome">${escapeHTML(x.name)}
        ${x.label && x.label !== 'Base' ? `<i class="var">${escapeHTML(x.label)}</i>` : ''}</div>
      <div class="codigo">${escapeHTML((x.code || '').split('/')[0])} ·
        ${escapeHTML(x.set_name)} · ${escapeHTML(x.rarity)}</div>
      <div class="subir-nums">
        <span class="preco-antes">${eur(x.from_cents)}</span>
        <span class="seta">→</span>
        <b class="preco-hoje">${eur(x.to_cents)}</b>
        <span class="desde" title="preço em vigor a ${x.since}">${
          x.full_window ? `há ${sp.window_days} d` : `desde ${x.since}`}</span>
        <span class="falta-n">faltam ${x.missing}× · ${eur(x.buy_cents)}</span>
      </div>
      <div class="subir-links">
        ${x.url_cardtrader ? `<a href="${escapeAttr(x.url_cardtrader)}" target="_blank"
           rel="noreferrer noopener">CardTrader</a>` : ''}
        ${x.url_riftscribe ? `<a href="${escapeAttr(x.url_riftscribe)}" target="_blank"
           rel="noreferrer noopener">RiftScribe</a>` : ''}
      </div>
    </div>

    <div class="subir-delta">
      <b class="up">${x.full_window ? '' : '~'}${fmtPct(x.pct)}</b>
      ${curto}
      ${sp.urgencia ? `<small class="urg" title="Δ%${sp.window_days}d × ${
        sp.pesos.janela} + Δ%${sp.short_days}d × ${sp.pesos.curto} + preço/mediana × ${
        sp.pesos.preco_relativo}">urg. ${x.urgency}</small>` : ''}
    </div>
  </div>`;
}

function fmtPct(v) {
  return `${v > 0 ? '+' : ''}${v.toLocaleString('pt-PT', { maximumFractionDigits: 1 })}%`;
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
   (o que falta comprar); na lista de venda chama-se `qty` (o que sobra dos
   decks). Gémeo do `cardmarket.quantidade` em Python. */
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
function cmLigar(id, getItens, nomeFicheiro, onde = 'wantlist') {
  for (const b of document.querySelectorAll(`[data-cm="${id}"]`)) {
    b.onclick = () => {
      const itens = getItens();
      if (b.dataset.cmModo === 'csv') { cmDescarregar(itens, nomeFicheiro, id); return; }
      cmMostrar(id, itens, b.dataset.cmModo === 'codigo', onde);
    };
  }
}

/* `onde` é só o texto da nota: nas listas de compra a lista vai para a
   wantlist, na de venda não — dizer-lhe "cola na wantlist" seria mandá-lo
   comprar o que quer vender.

   `foco` e `copiar` só se desligam nas wantlists da Coleção, que já vêm
   preenchidas sem ninguém carregar em nada: aí roubar o foco atirava a página
   para o fim, e escrever no clipboard sem ele pedir apagava-lhe o que lá
   tivesse. Nos botões continuam ligados, que é o que se espera de um clique. */
function cmMostrar(id, itens, comCodigo, onde = 'wantlist',
                   { foco = true, copiar = true } = {}) {
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

  const destino = onde === 'wantlist' ? 'Cola na wantlist do Cardmarket.'
                                      : 'É a lista das cartas, para levares para onde vendes.';
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
    const porque = onde === 'wantlist'
      ? `O texto da wantlist não leva marca de foil — depois de colares, liga o
         filtro <i>Foil</i> nestas entradas.`
      : `O preço que está aqui é o da oferta foil, que pode não ser o da tua
         cópia.`;
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


/* ------------------------------------------------- "Master set": tudo o que falta

   A aba «A subir» responde a "o que me está a fugir de preço"; esta responde a
   "e se eu quisesse fechar isto tudo". Mesmo âmbito e mesma regra de carência,
   sem o filtro de subida — e por EDIÇÃO e NÚMERO, que é a ordem por que as
   cartas estão no binder e nas páginas de venda (pedido do André).

   Sem imagens de propósito: são centenas de linhas, e o `faltas.json` é
   descarregado inteiro a cada visita.                                        */

function renderMasterFaltas() {
  const m = state.faltas.master;
  if (!m.copies) {
    $('#falta-body').innerHTML = `<p class="empty">Não falta nada ao master set.</p>`;
    return;
  }

  const sel = state.prefs.masterSet || 'all';
  const sets = m.sets.filter(s => sel === 'all' || s.set === sel);
  const itens = sets.flatMap(s => s.items);
  const copias = itens.reduce((a, x) => a + x.missing, 0);
  const cents = itens.reduce((a, x) => a + (x.total || 0), 0);
  const semPreco = itens.filter(x => x.price == null).length;

  $('#falta-body').innerHTML = `
    <div class="deck-card resumo">
      <b>${itens.length} impressões em falta</b>
      <span>${copias} cópia${copias === 1 ? '' : 's'} · ${eur(cents)} para as comprar hoje${
        semPreco ? ` · ${semPreco} sem preço no CardTrader` : ''}</span>
    </div>

    <p class="note">Tudo o que falta ao <b>master set</b> — o mesmo âmbito da
      barra de progresso da Coleção, com a mesma regra do filtro <i>Faltas</i>
      da grelha: conta enquanto <b>cópias + a caminho &lt; alvo</b>.
      Por edição e número de coleção.
      ${foraTexto(m.scope)}
      ${semPreco ? `<br>${semPreco} não têm oferta no CardTrader: entram na lista
        mas não no total, por isso o custo é <i>pelo menos</i> isto.` : ''}</p>

    <div class="chips subir-rar">
      <button class="chip-b ${sel === 'all' ? 'is-on' : ''}" data-mset="all">
        todas <b>${m.copies}</b></button>
      ${m.sets.map(s => `
        <button class="chip-b ${sel === s.set ? 'is-on' : ''}" data-mset="${escapeAttr(s.set)}">
          ${escapeHTML(s.name)} <b>${s.copies}</b></button>`).join('')}
    </div>

    ${sets.map(s => `
      <h3 class="section-head sub">${escapeHTML(s.name)}
        <span>${s.copies} cópia${s.copies === 1 ? '' : 's'} de ${s.cards}
          impress${s.cards === 1 ? 'ão' : 'ões'} · ${eur(s.cents)}</span></h3>
      <div class="mf-lista">${s.items.map(mfLinha).join('')}</div>`).join('')}

    ${cmZonaHTML('mfalta')}`;

  for (const b of document.querySelectorAll('[data-mset]')) {
    b.onclick = () => {
      state.prefs.masterSet = b.dataset.mset; savePrefs(); renderMasterFaltas();
    };
  }
  // A lista sai com o filtro de edição que estiver activo.
  cmLigar('mfalta', () => itens, `riftvault-master-faltas-${hojeISO()}.csv`);
}

function mfLinha(x) {
  return `<div class="mf-row">
    <span class="mf-code">${escapeHTML((x.code || '').split('/')[0])}</span>
    <span class="mf-nome" title="${escapeAttr(x.name)}">${escapeHTML(x.name)}${
      x.label && x.label !== 'Base' ? ` <i class="var">${escapeHTML(x.label)}</i>` : ''}</span>
    <span class="mf-tem">${x.have}/${x.target}</span>
    <span class="mf-falta">${x.missing}×</span>
    <span class="mf-preco">${x.price == null ? '—' : eur(x.price)}</span>
    <span class="mf-total">${x.price == null ? '' : eur(x.total)}</span>
  </div>`;
}


/* Sub-abas dentro de "Por deck". Cada deck conta só o que a lista dos decks
   anteriores AINDA não cobre — as cartas trocam-se entre decks, não se compram
   aos pares. A última aba responde à pergunta oposta: e se quisesse os decks
   todos montados ao mesmo tempo? */
function renderPorDeck() {
  const f = state.faltas;
  const um = f.por_deck.reduce((s, d) => s + d.cents, 0);
  const copias = f.por_deck.reduce((s, d) => s + d.copies, 0);
  const tj = f.todos_juntos;
  // O índice do deck escolhido fica guardado no browser, mas apagar um deck é
  // apagar o .txt — e aí o índice antigo passa a apontar para fora da lista.
  // Sem esta correção o `f.por_deck[sel]` vinha `undefined`, a secção Faltas
  // rebentava em branco e ficava assim a cada recarga, porque o índice mau
  // continuava no localStorage.
  let sel = state.prefs.faltaDeck ?? 0;
  if (sel !== 'todos' && !f.por_deck[sel]) sel = f.por_deck.length ? 0 : 'todos';

  const abas = f.por_deck.map((d, i) => `
    <button class="seg-btn ${i === sel ? 'is-on' : ''}" data-fd="${i}">
      ${d.priority}. ${escapeHTML(d.name.split(' · ')[0])}
      <b>${d.copies}</b></button>`).join('')
    + `<button class="seg-btn ${sel === 'todos' ? 'is-on' : ''}" data-fd="todos">
        Todos juntos <b>${tj.copies}</b></button>`;

  const alvo = sel === 'todos' ? tj : f.por_deck[sel];
  const intro = sel === 'todos'
    ? `<p class="note">O que custaria ter os <b>${f.por_deck.length}</b> decks
       montados <b>ao mesmo tempo</b>, com cópias para cada um — sem trocar
       cartas de deck. São <b>${eur(tj.cents - um)}</b> e
       <b>${tj.copies - copias}</b> cópias a mais do que montá-los um de cada
       vez.</p>`
    : `<p class="note">O que falta a este deck <b>depois</b> de comprares as
       listas dos anteriores. ${sel > 0
         ? 'As cartas que os decks de cima já obrigam a comprar não voltam a contar aqui.'
         : 'É o primeiro da fila, por isso leva a lista inteira.'}</p>`;

  $('#falta-body').innerHTML = `
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
      <b>${copias} cópias · ${eur(um)}</b> para os montar um de cada vez.</p>`;

  for (const b of document.querySelectorAll('#falta-body .seg-btn[data-fd]')) {
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
  const p = state.faltas.pimp;
  if (!p.printings) {
    $('#falta-body').innerHTML = '<p class="empty">Nenhuma carta dos teus decks tem versão alterada.</p>';
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
        ${d.priority}. ${escapeHTML(d.name.split(' · ')[0])}
        <b>${d.printings}</b></button>`).join('');

  $('#falta-body').innerHTML = `
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

  for (const b of document.querySelectorAll('#falta-body .seg-btn[data-pd]')) {
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
        ? ` · ${x.decks.map(d => escapeHTML(d.split(' · ')[0])).join(', ')}` : ''}</div>
  </div>`;
}


/* "A caminho": comprado mas ainda não em casa. Não está na Coleção — essa
   mede o que está na caixa — mas já saiu das faltas, senão ele comprava duas
   vezes enquanto a encomenda vem. */
function renderCaminho() {
  const p = state.faltas.pending;
  if (!p.copies) {
    $('#falta-body').innerHTML = `<p class="empty">Nada a caminho.<br>
      <small>Regista com <code>riftvault pending</code>.</small></p>`;
    return;
  }
  // Agrupar por edição: é assim que as encomendas chegam e se conferem.
  const porSet = new Map();
  for (const it of p.items) {
    if (!porSet.has(it.set_id)) porSet.set(it.set_id, []);
    porSet.get(it.set_id).push(it);
  }

  $('#falta-body').innerHTML = `
    <div class="deck-card resumo">
      <b>A caminho</b>
      <span>${p.copies} cópias em ${p.lines} linhas${p.cents ? ` · ${eur(p.cents)}` : ''}</span>
    </div>
    <p class="note">Já compradas, ainda não em casa. <b>Não contam na Coleção</b>
      — essa mede o que tens na caixa — mas já saíram das faltas e das
      wantlists. Quando chegarem, corre
      <b>Chegou</b> em cada carta, ou o botão em baixo para dar entrada de tudo.</p>
    ${state.editable ? `<div class="wl-zona">
      <button class="btn" id="chegou-tudo">Chegou tudo (${p.copies} cópias)</button>
    </div>` : ''}
    ${[...porSet.entries()].map(([s, itens]) => `
      <h3 class="section-head sub">${escapeHTML(s)}
        <span>${itens.reduce((a, x) => a + x.qty, 0)} cópias${
          itens.some(x => x.unit_cents)
            ? ` · ${eur(itens.reduce((a, x) => a + (x.unit_cents || 0) * x.qty, 0))}` : ''}</span></h3>
      <div class="grid deck-grid">${itens.map(caminhoTile).join('')}</div>`).join('')}`;

  for (const b of document.querySelectorAll('#falta-body [data-chegou]')) {
    b.onclick = () => chegou(Number(b.dataset.chegou), b);
  }
  const tudo = $('#chegou-tudo');
  if (tudo) tudo.onclick = () => chegou(null, tudo);
}

/* Confirmar a chegada: sai do "a caminho" e entra na Coleção. Passa pelo
   mesmo caminho dos `+`, portanto fica no log e dá para desfazer. */
async function chegou(id, botao) {
  if (botao) { botao.disabled = true; botao.textContent = 'a dar entrada…'; }
  try {
    const r = await fetch('api/pending/arrive', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(id ? { id } : {}),
    });
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error || `HTTP ${r.status}`);
    const res = await r.json();
    const n = res.arrived.reduce((s, x) => s + x.qty, 0);
    toast(`${n} ${n === 1 ? 'cópia entrou' : 'cópias entraram'} na coleção.`);
    // A coleção mudou: força-se a recarga em vez de tentar remendar o estado.
    state.faltas = null;
    state.payload = null;
    await loadFaltas();
    if (state.setId) await loadSet(state.setId);
    showSection('faltas');
  } catch (err) {
    toast(`Não deu para dar entrada: ${err.message}`, { error: true });
    if (botao) { botao.disabled = false; botao.textContent = 'Chegou'; }
  }
}

/* Tile de encomenda. Sem moldura de estado: não é "tenho" nem "falta", é
   uma terceira coisa — está a chegar. */
function caminhoTile(x) {
  return `<div class="dtile neutro a-caminho" data-pid="${x.id}">
    ${artHTML(x, `<span class="need">${x.qty}×</span>
      ${x.market_only ? '<span class="so-mercado">fora do catálogo</span>' : ''}
      ${x.unit_cents ? `<span class="price pago">${eurShort(x.unit_cents * x.qty)}</span>` : ''}`)}
    <div class="tname" title="${escapeAttr(x.name || '')}">${escapeHTML(x.name || x.printing_id)}</div>
    <div class="codigo">${escapeHTML((x.code || '').split('/')[0])}${
      x.unit_cents ? ` · ${eur(x.unit_cents)}` : ''}</div>
    ${x.label !== 'Base' ? `<div class="onde tenho">${escapeHTML(x.label)}</div>` : ''}
    ${state.editable ? `<button class="btn chegou" data-chegou="${x.id}">Chegou</button>` : ''}
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
      `${d.qty}× ${escapeHTML(d.deck.split(' · ')[0])}`).join('<br>')}</div>
  </div>`;
}


/* ========================================================== SECÇÃO VENDA

   "A Coleção é de master set. O resto provavelmente vai para venda ou jogar nos
   decks seleccionados" (André, 2026-09-08). Isto é a segunda metade da frase: o
   que ele TEM a mais da sequência do master set, partido em "está num deck" e
   "sobra". Desde a decisão da tarde ("1 alt art de cada") a cauda da coleção só
   entra no EXCEDENTE — a primeira arte alternativa é coleção, a sexta é venda.

   NADA SAI DA BASE. É uma sugestão — não há botão de vender, não se mexe no
   `copies`. A lista sai em texto, como as de compra.                        */

async function loadVenda() {
  state.venda = await getJSON('api/venda.json');
  renderVenda();
}

function renderVenda() {
  const v = state.venda;
  const corpo = $('#venda-body');

  if (!v.printings && !v.in_decks) {
    corpo.innerHTML = `<p class="empty">Não tens nada a mais do que a coleção
      pede — nem tokens (<code>-T</code>), que estão fora dela, nem cópias
      repetidas das runas especiais ou das artes alternativas.</p>`
      + comunsHTML(v.comuns);
    comunsLigar(v.comuns);
    return;
  }

  corpo.innerHTML = `
    <div class="deck-card resumo">
      <b>${v.printings} impress${v.printings === 1 ? 'ão' : 'ões'} a mais</b>
      <span>${v.copies} cópia${v.copies === 1 ? '' : 's'} · ${eur(v.cents)} ao preço
        de hoje${v.no_price ? ` · ${v.no_price} sem oferta no CardTrader` : ''}</span>
    </div>

    <p class="note">Só o que <b>tens na caixa</b> e a <b>sequência do master
      set</b> não pede: os tokens (<code>-T</code>), que estão fora da coleção,
      e as cópias a mais das runas especiais e das artes alternativas — dessas
      guarda-se <b>1 de cada</b>, que é o que a coleção pede, e só sobra o
      resto. O que algum deck usa fica de fora da lista e aparece
      em baixo${v.in_decks ? `: são <b>${v.in_decks}</b> impressões,
      ${v.in_decks_copies} cópias` : ''}.
      <br>Desde 10/09 a lista tem <b>duas origens</b> e cada linha diz a sua: o
      <b>binder Decks/Venda</b> (cópias que tiraste da Coleção e que nenhum deck
      pede) e a <b>Coleção</b> (o que passa do alvo). O que está <b>dentro</b>
      de um deck nunca aparece.
      <br>Isto é uma <b>sugestão</b>: não mexe na coleção, não há nada a
      confirmar. As impressões da sequência do master set que estão na Coleção
      nunca entram aqui, por muitas que tenhas a mais — mas as que puseste no
      binder Decks/Venda entram, porque já não são coleção.
      ${v.no_price ? `<br><b>${v.no_price}</b> não têm oferta no CardTrader:
        entram na lista, não entram no total.` : ''}</p>

    ${(v.origins || []).length ? `<div class="chips venda-blocos">${v.origins.map(o => `
      <span class="chip-b is-static">${escapeHTML(o.label)}
        <b>${o.copies}</b> · ${eurShort(o.cents)}</span>`).join('')}</div>` : ''}

    ${v.blocks.length ? `<div class="chips venda-blocos">${v.blocks.map(b => `
      <span class="chip-b is-static">${escapeHTML(b.label || b.id)}
        <b>${b.copies}</b> · ${eurShort(b.cents)}</span>`).join('')}</div>` : ''}

    ${v.items.length ? `<div class="grid deck-grid">${v.items.map(vendaTile).join('')}</div>`
      : '<p class="empty">Tudo o que tens a mais está a ser usado nos decks.</p>'}

    ${v.items.length ? cmZonaHTML('venda') : ''}
    ${v.items.length ? `<small class="nota">A lista sai no formato do Cardmarket
      (<code>N Nome (V.n) (Edição)</code>), o mesmo das listas de compra — é um
      formato de <i>wantlist</i>, não de importação de stock de vendedor. Serve
      para saberes o que tens para vender, não para o carregar lá.</small>` : ''}

    ${v.kept.length ? `
      <h3 class="section-head sub">Dentro de um deck — não estão para venda
        <span>${v.in_decks_copies} cópias marcadas em decks</span></h3>
      <div class="grid deck-grid">${v.kept.map(vendaTile).join('')}</div>` : ''}

    ${comunsHTML(v.comuns)}`;

  if (v.items.length) {
    cmLigar('venda', () => v.items, `riftvault-venda-${hojeISO()}.csv`, 'venda');
  }
  comunsLigar(v.comuns);
}

/* ---------------------------------------------- comuns e incomuns (2026-09-10)

   "Vê no Cardmarket e CardTrader quais as comuns e incomuns que costumam
   vender-se mais, e quais as mais caras, para eu saber o que vender" (André).

   Vem DOBRADA: são duas tabelas de vinte linhas e a pergunta principal da
   página continua a ser o excedente lá de cima.

   O QUE ESTA SECÇÃO NÃO TEM: uma lista de "as que se vendem mais". Volume de
   vendas não existe em fonte pública nenhuma — o Cardmarket dá 403 no site e
   410 na API — e inventar uma coluna a partir do número de anúncios seria
   mostrar OFERTA com o nome de procura. Ver `riftvault/comuns.py`.          */

/* O catálogo escreve as raridades em inglês; o ecrã é dele. */
const COMUNS_RAR = { common: 'comuns', uncommon: 'incomuns', rare: 'raras',
                     epic: 'épicas', showcase: 'showcase' };

function comunsHTML(c) {
  if (!c) return '';
  const rar = (c.rarities || []).map(r => COMUNS_RAR[r] || r).join(' e ');
  const s = c.sell || { printings: 0, copies: 0, cents: 0, items: [] };
  const k = c.keep || { printings: 0, items: [] };

  return `<details class="comuns-bloco">
    <summary><b>Comuns e incomuns: as mais caras e o que tens a mais</b>
      <span>${c.universe.priced} impressões com preço · o teu excedente vale
        ${eur(s.cents)}</span></summary>

    <p class="note"><b>O que isto mede.</b> A fonte é o <b>CardTrader</b>
      (preços de ${escapeHTML(c.day || '—')}): preço mínimo pedido, número de
      anúncios e de vendedores. <b>Do Cardmarket não vem nada</b> —
      ${escapeHTML(c.sources.cardmarket.why)}.
      <br><b>Não há volume de vendas em lado nenhum público</b>, por isso não há
      aqui nenhuma lista de "as que mais se vendem". A coluna <b>procura</b> é o
      preço a dividir pela mediana da raridade (${(c.rarities || []).map(r =>
        `${COMUNS_RAR[r] || r} ${eur(c.medians[r])}`).join(' · ')}), reforçado pela
      subida do preço e pela queda dos anúncios em ${c.window_days} dias — mede
      quanto o mercado pede <i>acima do saldo</i>, não quantas se venderam.
      ${c.listings_days < 2 ? `<br>O histórico do número de anúncios começou
        agora (${c.listings_days} dia): a queda de anúncios ainda não conta para
        nada. Ganha sentido ao fim de umas semanas de <code>riftvault prices</code>.`
        : ''}</p>

    <h3 class="section-head sub">As mais caras
      <span>top ${c.top} de ${c.universe.priced} ${escapeHTML(rar)}</span></h3>
    ${comunsTabela(c.by_price)}

    <h3 class="section-head sub">Sinal de procura mais alto
      <span>preço acima do saldo da raridade — não é volume de vendas</span></h3>
    ${comunsTabela(c.by_demand)}

    <h3 class="section-head sub">O que vender
      <span>${s.printings} impressões · ${s.copies} cópias ·
        ${eur(s.cents)}</span></h3>
    <p class="note">Só o que <b>nem a Coleção nem os decks pedem</b> — a mesma
      conta do excedente lá de cima, mas com a sequência do master set incluída,
      porque é lá que as comuns vivem. Nada disto mexe na coleção.</p>
    ${s.items.length ? comunsTabela(s.items, true) + cmZonaHTML('comuns')
      : `<p class="empty">Não tens nenhuma comum ou incomum a mais.</p>`}

    ${k.printings ? `
      <h3 class="section-head sub">Guardar, não vender
        <span>${k.printings} impressões baratas mas a subir</span></h3>
      ${comunsTabela(k.items, true)}` : ''}
  </details>`;
}

function comunsTabela(itens, comExcedente = false) {
  return `<table class="cm-tabela"><thead><tr>
      <th>código</th><th>nome</th><th class="n">preço</th><th class="n">procura</th>
      <th class="n">anúncios</th><th class="n">vend.</th><th class="n">Δ% ${''}</th>
      <th class="n">${comExcedente ? 'a mais' : 'tens'}</th>
      ${comExcedente ? '<th class="n">total</th>' : ''}</tr></thead><tbody>
    ${itens.map(x => `<tr>
      <td class="cod">${escapeHTML((x.code || '').split('/')[0])}</td>
      <td title="${escapeAttr(x.name)}">${escapeHTML(x.name)}${
        x.outside ? ` <span class="fora-tag">fora da coleção</span>` : ''}${
        x.from_foil ? ` <span class="fora-tag">só foil</span>` : ''}</td>
      <td class="n">${eur(x.price)}</td>
      <td class="n">${x.demand.toLocaleString('pt-PT')}</td>
      <td class="n">${x.n_listings}</td>
      <td class="n">${x.n_sellers || '—'}</td>
      <td class="n ${x.pct > 0 ? 'sobe' : ''}">${
        x.pct == null ? '—' : fmtPct(x.pct)}</td>
      <td class="n">${comExcedente ? x.qty : x.have || '—'}</td>
      ${comExcedente ? `<td class="n">${eur(x.total)}</td>` : ''}
    </tr>`).join('')}</tbody></table>`;
}

function comunsLigar(c) {
  if (c && c.sell && c.sell.items.length) {
    cmLigar('comuns', () => c.sell.items,
            `riftvault-comuns-${hojeISO()}.csv`, 'venda');
  }
}


function vendaTile(x) {
  const onde = (x.in_decks || []).map(d =>
    `${d.qty}× ${escapeHTML(d.deck.split(' · ')[0])}`).join(', ');
  return `<div class="dtile ${x.state === 'deck' ? 'neutro' : 'gone'}">
    ${artHTML(x, `<span class="need">${x.qty || x.have}×</span>
      ${x.price != null ? `<span class="price">${eurShort(x.total || x.price)}</span>` : ''}`)}
    <div class="tname" title="${escapeAttr(x.name)}">${escapeHTML(x.name)}</div>
    <div class="codigo">${escapeHTML((x.code || '').split('/')[0])} ·
      ${escapeHTML(x.label)}${x.price != null ? ` · ${eur(x.price)}` : ''}</div>
    <div class="onde ${x.state === 'deck' ? 'tenho' : ''}">${
      onde ? `usada num deck: ${onde}` : 'candidata a venda'}${
      x.state === 'deck' && x.qty > 0 ? ` · ${x.qty} a mais` : ''}</div>
    ${vendaOrigem(x)}
  </div>`;
}

/* DE ONDE vem cada cópia da linha (André, 2026-09-10): *"cada linha a dizer de
   onde vem"*. Tirar do binder Decks/Venda é arrumação; tirar da Coleção é
   vender coleção, e isso lê-se de outra maneira. */
function vendaOrigem(x) {
  const p = [];
  if (x.from_binder) p.push(`${x.from_binder} do binder Decks/Venda`);
  if (x.from_colecao) p.push(`${x.from_colecao} da Coleção (acima do alvo)`);
  return p.length ? `<div class="onde origem">${p.join(' · ')}</div>` : '';
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

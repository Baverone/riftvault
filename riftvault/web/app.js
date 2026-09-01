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
  qty: new Map(),              // printing_id -> quantidade (verdade local, otimista)
  play: new Map(),             // card_key -> {owned, target}
  targets: new Map(),          // printing_id -> alvo do master
  meta: new Map(),             // printing_id -> {name, card_key, rarity}
  pending: new Map(),          // card_key -> pedidos por responder
  tiles: [],                   // impressões visíveis, pela ordem do ecrã
  focus: -1,
  // Default: TODAS as impressões (decisão do André). O botão "Só artes base"
  // continua lá, mas não é o que se vê ao abrir.
  decks: null, deckId: null, deck: null, faltas: null,
  prefs: { view: 'all', stateFilter: 'all',
           kinds: ['base', 'alt_art', 'signature', 'other'],
           set: null, deck: null, falta: 'staples', faltaDeck: 0, pimpDeck: 'todos',
           section: 'colecao' },
};

/* ------------------------------------------------------------ preferências */

function loadPrefs() {
  try {
    const raw = localStorage.getItem(PREFS);
    if (raw) Object.assign(state.prefs, JSON.parse(raw));
  } catch (_) { /* localStorage pode estar bloqueado; segue com os defaults */ }
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

  renderSetTabs();
  const first = state.index.sets[0];
  const wanted = state.index.sets.some(s => s.id === state.prefs.set) ? state.prefs.set : (first && first.id);
  if (wanted) await loadSet(wanted);
  showSection(['decks', 'faltas'].includes(state.prefs.section)
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

  state.qty.clear(); state.play.clear(); state.targets.clear(); state.meta.clear();
  for (const g of p.groups) {
    state.play.set(g.card_key, { owned: g.playset.owned, target: g.playset.target });
    for (const pr of g.printings) {
      state.qty.set(pr.id, pr.qty);
      state.targets.set(pr.id, pr.target);
      state.meta.set(pr.id, { name: pr.name, card_key: g.card_key, rarity: g.rarity, cn: g.cn });
    }
  }
  render();
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
  const f = state.prefs.stateFilter;
  if (f === 'missing') list = list.filter(p => tileState(p.id) === 'none');
  else if (f === 'partial') list = list.filter(p => tileState(p.id) === 'partial');
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
      <button class="step minus" data-act="-1" aria-label="menos uma" ${q <= 0 ? 'disabled' : ''}>−</button>
      <button class="step plus" data-act="1" aria-label="mais uma">+</button>
    </div>
    <div class="playset ${play.target > 0 && play.owned >= play.target ? 'is-done' : ''}"
         data-kind="${g.is_token ? 'token' : 'jogável'}"
         ${p.price != null ? `data-price="${p.price}"` : ''}>
      ${g.is_token ? 'token' : 'jogável'} ${play.owned}/${play.target}${p.price != null ? ` · ${eur(p.price)}` : ''}
    </div>
    ${deckLine(p)}
  </div>`;
}

/* Se a carta não está no binder é porque saiu para um deck. Esta linha diz
   qual — é o que ele vai à Coleção procurar quando não a encontra no binder. */
function deckLine(p) {
  const n = (p.in_decks || []).reduce((s, x) => s + x.qty, 0);
  if (!n) return '';
  const livre = (p.qty || 0) - n;
  const onde = p.in_decks
    .map(x => `${x.qty}× ${escapeHTML(x.deck.split(' · ')[0])}`).join(', ');
  return `<div class="indeck" title="${escapeAttr(p.in_decks.map(x => x.deck).join(' / '))}">
    ${onde}${livre > 0 ? ` · ${livre} no binder` : ''}</div>`;
}

function render() {
  const grid = $('#grid');
  const parts = [];
  state.tiles = [];

  // Ordem única: número de coleção (a mesma que a API devolve, que já põe
  // cada variante logo a seguir à sua base).
  for (const g of (state.payload?.groups || [])) {
    const list = visiblePrintings(g);
    if (!list.length) continue;
    const multi = list.length > 1;
    const inner = list.map(p => { state.tiles.push(p.id); return tileHTML(g, p); }).join('');
    parts.push(multi
      ? `<div class="group multi" style="--span:${list.length}">${inner}</div>`
      : `<div class="group">${inner}</div>`);
  }

  grid.innerHTML = parts.join('');
  $('#empty').hidden = parts.length > 0;
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

  for (const g of state.payload.groups) {
    const play = state.play.get(g.card_key);
    if (play && play.target > 0 && !seen.has(g.card_key)) {
      seen.add(g.card_key);
      pTotal++;
      if (play.owned >= play.target) pDone++;
    }
    for (const p of g.printings) {
      const t = state.targets.get(p.id) || 0;
      if (t <= 0) continue;
      const ok = (state.qty.get(p.id) || 0) >= t;
      mTotal++; if (ok) mDone++;
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
      state.qty.set(pid, res.qty);
      if (res.playset) state.play.set(ck, { owned: res.playset.owned, target: res.playset.target });
      refreshTiles(pid, ck);
    }
    if (res.op_id) toastUndo(pid, delta, res.op_id);
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
    state.qty.set(pid, res.qty);
    const ck = state.meta.get(pid)?.card_key;
    if (res.playset) state.play.set(ck, { owned: res.playset.owned, target: res.playset.target });
    refreshTiles(pid, ck);
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
  for (const alvo of ['#grid', '#deck-body', '#falta-body']) {
    $(alvo).addEventListener('error', imgFallback, true);
  }

  $('#grid').addEventListener('error', (e) => {
    const img = e.target;
    if (img.tagName !== 'IMG' || !img.dataset.fallback) return;
    img.src = img.dataset.fallback;
    delete img.dataset.fallback;
  }, true);

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

  for (const b of document.querySelectorAll('#deck-head .btn')) {
    b.onclick = () => deckAction(b.dataset.act);
  }
}

/* Tile de deck: a mesma linguagem visual da Coleção, mas o que interessa aqui
   é quantas o deck pede e quantas estão de facto alocadas. */
function deckTile(c) {
  const st = c.missing ? (c.shared ? 'shared' : 'gone') : 'ok';
  const src = state.imageMode === 'remote' ? (c.cdn || c.img) : (c.img || c.cdn);
  const alt = state.imageMode === 'remote' ? (c.img || '') : (c.cdn || '');

  let nota = '';
  if (c.shared) {
    nota = `<div class="onde shared">falta ${c.missing} — ${c.shared.em
      .map(h => `${h.qty}× em «${escapeHTML(h.deck.split(' · ')[0])}»`).join(', ')}</div>`;
  } else if (c.missing) {
    nota = `<div class="onde falta">faltam ${c.missing}</div>`;
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
  for (const s of ['colecao', 'decks', 'faltas']) $('#' + s).hidden = s !== name;
  $('#set-tabs').hidden = name !== 'colecao';
  $('#deck-tabs').hidden = name !== 'decks';
  $('#falta-tabs').hidden = name !== 'faltas';
  for (const b of document.querySelectorAll('#section-tabs .tab')) {
    b.classList.toggle('is-on', b.dataset.section === name);
  }
  if (name === 'decks' && !state.decks) loadDecks().catch(err =>
    $('#deck-body').innerHTML = `<p class="empty">${escapeHTML(err.message)}</p>`);
  if (name === 'faltas' && !state.faltas) loadFaltas().catch(err =>
    $('#falta-body').innerHTML = `<p class="empty">${escapeHTML(err.message)}</p>`);
}


/* ========================================================== SECÇÃO FALTAS

   Três leituras da mesma carência. A carência é GLOBAL — soma-se o que todos
   os decks pedem e desconta-se o que ele tem — e não a alocação por
   prioridade, que responde a outra pergunta (quem fica com o quê).          */

const FALTA_TABS = [
  { id: 'staples', label: 'Staples', sub: 'pedidas por vários decks' },
  { id: 'deck', label: 'Por deck', sub: 'o que falta a cada um' },
  { id: 'spike', label: 'A subir', sub: 'comprar antes que suba mais' },
  { id: 'pimp', label: 'Pimp decks', sub: 'versões alteradas das cartas dos decks' },
];

async function loadFaltas() {
  state.faltas = await getJSON('api/faltas.json');
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
    if (t.id === 'staples') n = `${f.staples.length} cartas`;
    if (t.id === 'deck') n = `${f.por_deck.reduce((s, d) => s + d.copies, 0)} cópias`;
    if (t.id === 'spike') n = f.spiking.ready ? `${f.spiking.items.length} cartas` : 'sem histórico';
    if (t.id === 'pimp') n = `${f.pimp.printings} versões`;
    b.innerHTML = `${t.label}<small>${n}</small>`;
    b.onclick = () => { state.prefs.falta = t.id; savePrefs(); renderFaltaTabs(); renderFaltas(); };
    nav.appendChild(b);
  }
}

function faltaHead() {
  const f = state.faltas;
  const t = f.totals;
  return `<div class="deck-card">
    <div class="deck-title"><b>Falta comprar</b>
      <span class="prio">${t.cards} cartas · ${t.copies} cópias</span></div>
    <div class="deck-meta">
      <span><i>Custo estimado</i>${eur(t.cents)}</span>
      <span><i>Critério</i>preço mais baixo no CardTrader, edição mais barata</span>
      ${f.ignored_types.length ? `<span><i>Fora da conta</i>${
        f.ignored_types.join(', ')} — compram-se a granel</span>` : ''}
    </div>
  </div>`;
}

function renderFaltas() {
  const f = state.faltas;
  $('#falta-head').innerHTML = faltaHead();
  const which = state.prefs.falta;

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

  if (which === 'pimp') {
    renderPimp();
    return;
  }

  const sp = f.spiking;
  if (!sp.ready) {
    $('#falta-body').innerHTML = `<div class="aviso">
      <b>Ainda não há com que comparar.</b>
      <p>${sp.days_recorded
        ? `Já há ${sp.days_recorded === 1 ? 'um dia' : `${sp.days_recorded} dias`} de preços
           gravados${sp.first ? ` (desde ${sp.first})` : ''}, mas <b>nenhuma carta tem duas
           leituras</b> ainda — sem duas, não há subida para medir.`
        : 'Ainda não há preços gravados.'}</p>
      <p>O histórico só escreve quando o preço <em>muda</em>, por isso é normal
      demorar uns dias a encher. Corre <code>riftvault prices</code> de vez em
      quando e esta aba começa a dizer alguma coisa.</p>
      <p>São seguidas <b>${sp.tracked || 0} impressões</b> — o Riftbound
      inteiro, não só a tua coleção.</p>
    </div>`;
    return;
  }
  const meus = sp.items.filter(x => x.missing || x.have).length;
  $('#falta-body').innerHTML = sp.items.length ? `
    <p class="note">Todo o Riftbound, não só a tua coleção: impressões que
      subiram mais de ${sp.min_pct}% nos últimos ${sp.window_days} dias.
      ${meus ? `<b>${meus}</b> ${meus === 1 ? 'toca-te' : 'tocam-te'} —
      moldura verde já tens, vermelha faz-te falta.` : 'Nenhuma delas te toca.'}
      Seguidas ${sp.tracked} impressões.</p>
    <div class="grid deck-grid">${sp.items.map(spikeTile).join('')}</div>`
    : `<p class="empty">Nenhuma impressão subiu mais de ${sp.min_pct}% nos
       últimos ${sp.window_days} dias.</p>`;
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
  const sel = state.prefs.faltaDeck ?? 0;

  const abas = f.por_deck.map((d, i) => `
    <button class="seg-btn ${i === sel ? 'is-on' : ''}" data-fd="${i}">
      ${d.priority}. ${escapeHTML(d.name.split(' · ')[0])}
      <b>${d.copies}</b></button>`).join('')
    + `<button class="seg-btn ${sel === 'todos' ? 'is-on' : ''}" data-fd="todos">
        Todos juntos <b>${tj.copies}</b></button>`;

  const alvo = sel === 'todos' ? tj : f.por_deck[sel];
  const intro = sel === 'todos'
    ? `<p class="note">O que custaria ter os cinco decks montados
       <b>ao mesmo tempo</b>, com cópias para cada um — sem trocar cartas de
       deck. São <b>${eur(tj.cents - um)}</b> e <b>${tj.copies - copias}</b>
       cópias a mais do que montá-los um de cada vez.</p>`
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
   alternativas, showcase, signatures e promos. Não é uma lista de compras: é
   para saber o que existe e poder filtrar quando andar a procurar. Por isso
   entram também as que ele já tem, marcadas. */
function renderPimp() {
  const p = state.faltas.pimp;
  if (!p.printings) {
    $('#falta-body').innerHTML = '<p class="empty">Nenhuma carta dos teus decks tem versão alterada.</p>';
    return;
  }
  const sel = state.prefs.pimpDeck ?? 'todos';
  const alvo = sel === 'todos' ? p : p.by_deck[sel];

  const abas = `<button class="seg-btn ${sel === 'todos' ? 'is-on' : ''}" data-pd="todos">
      Todas <b>${p.printings}</b></button>`
    + p.by_deck.map((d, k) => `
      <button class="seg-btn ${k === sel ? 'is-on' : ''}" data-pd="${k}">
        ${d.priority}. ${escapeHTML(d.name.split(' · ')[0])}
        <b>${d.printings}</b></button>`).join('');

  $('#falta-body').innerHTML = `
    <div class="seg seg-wrap">${abas}</div>
    <div class="deck-card resumo">
      <b>${sel === 'todos' ? 'Todas as versões alteradas' : escapeHTML(p.by_deck[sel].name)}</b>
      <span>${alvo.cards} cartas · ${alvo.printings} versões · ${eur(alvo.cents)}${
        alvo.owned ? ` · já tens ${alvo.owned}` : ''}</span>
    </div>
    <p class="note">${sel === 'todos'
      ? `As versões alteradas das cartas que os teus decks usam, deck a deck:
         artes alternativas, showcase e promos. Uma carta que dois decks usem
         aparece nos dois.`
      : `O que dá para trocar neste deck. A quantidade é a que ele usa.`}
      Moldura verde: já tens essa versão.</p>
    ${sel === 'todos'
      ? p.by_deck.map(d => `
          <h3 class="section-head sub">${d.priority}. ${escapeHTML(d.name)}
            <span>${d.printings} versões · ${eur(d.cents)}${
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
      ${x.have ? '<span class="ja-tens">tens</span>' : ''}
      ${x.price != null ? `<span class="price">${eurShort(x.total)}</span>` : ''}`)}
    <div class="tname" title="${escapeAttr(x.name)}">${escapeHTML(x.name)}</div>
    <div class="codigo">${escapeHTML((x.code || '').split('/')[0])}${
      x.price != null ? ` · ${eur(x.price)}` : ''}</div>
    <div class="onde tenho">${escapeHTML(x.label)}${
      comDecks && x.decks.length
        ? ` · ${x.decks.map(d => escapeHTML(d.split(' · ')[0])).join(', ')}` : ''}</div>
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

function spikeTile(x) {
  // Marca as que lhe tocam: tem, ou faz-lhe falta. As outras são só o mercado.
  const meu = x.missing ? 'falta' : (x.have ? 'tenho' : '');
  return `<div class="dtile ${x.missing ? 'gone' : (x.have ? 'ok' : 'neutro')}">
    ${artHTML(x, `${meu === 'falta' ? `<span class="need">${x.missing}×</span>` : ''}
      ${meu === 'tenho' ? `<span class="need have">${x.have}×</span>` : ''}
      <span class="spike">+${x.pct}%</span>`)}
    <div class="tname" title="${escapeAttr(x.name)}">${escapeHTML(x.name)}
      ${x.label !== 'Base' ? `<i class="var">${escapeHTML(x.label)}</i>` : ''}</div>
    <div class="onde spike-nota">${eur(x.from_cents)} → <b>${eur(x.to_cents)}</b></div>
    ${x.missing ? `<div class="onde falta">custou-te ${eur(x.extra_cents)} esperar</div>` : ''}
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

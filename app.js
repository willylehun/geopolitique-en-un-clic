const REGIONS = [
  'International', 'Europe', 'Asie', 'Amérique du Nord',
  'Amérique du Sud', 'Afrique', 'Océanie'
];

const state = { region: 'International', period: 'day', bucket: null, data: [] };
const $ = (q) => document.querySelector(q);

function stars(score) {
  return '★'.repeat(score) + '☆'.repeat(10 - score);
}

function escapeHtml(s='') {
  return s.replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
}

function sortItems(items) {
  return [...items].sort((a,b) => (b.score - a.score) || a.summary.localeCompare(b.summary));
}

function getBuckets() {
  const values = [...new Set(state.data
    .filter(x => x.region === state.region && x.period === state.period)
    .map(x => x.bucket))];
  return values.sort().reverse();
}

function renderRegions() {
  const nav = $('#regionNav');
  nav.innerHTML = '';
  REGIONS.forEach(region => {
    const btn = document.createElement('button');
    btn.className = 'region-btn' + (state.region === region ? ' active' : '');
    btn.textContent = region;
    btn.onclick = () => { state.region = region; state.bucket = null; render(); };
    nav.appendChild(btn);
  });
}

function renderHistory() {
  const select = $('#historySelect');
  const buckets = getBuckets();
  if (!state.bucket || !buckets.includes(state.bucket)) state.bucket = buckets[0] || null;
  select.innerHTML = buckets.map(b => `<option value="${escapeHtml(b)}" ${b===state.bucket?'selected':''}>${escapeHtml(b)}</option>`).join('');
  select.disabled = buckets.length === 0;
  select.onchange = e => { state.bucket = e.target.value; renderNews(); };
}

function renderNews() {
  const items = sortItems(state.data.filter(x =>
    x.region === state.region && x.period === state.period && x.bucket === state.bucket && x.score >= 5
  ));

  const header = $('#summaryHeader');
  const list = $('#newsList');
  const label = state.period === 'day' ? 'Jour' : state.period === 'week' ? 'Semaine' : 'Mois';
  header.innerHTML = `<h2>${escapeHtml(state.region)} — ${label}</h2><p>${state.bucket ? escapeHtml(state.bucket) : 'Aucun historique disponible'} • ${items.length} sujet${items.length>1?'s':''}</p>`;

  if (!items.length) {
    list.innerHTML = '<div class="empty">Aucune information notée 5/10 ou plus pour cette période.</div>';
    return;
  }

  list.innerHTML = items.map(item => `
    <article class="news-item ${item.score >= 8 ? 'hot' : ''}">
      <div class="meta">
        <span class="score">${item.score}/10</span>
        <span class="stars" aria-label="${item.score} étoiles sur 10">${stars(item.score)}</span>
        ${item.category ? `<span class="tag">${escapeHtml(item.category)}</span>` : ''}
      </div>
      <p>${escapeHtml(item.summary)}</p>
      <div class="sources">(${item.sources.map(escapeHtml).join(' • ')})</div>
    </article>
  `).join('');
}

function renderPeriods() {
  document.querySelectorAll('.period-tab').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.period === state.period);
    btn.onclick = () => { state.period = btn.dataset.period; state.bucket = null; render(); };
  });
}

function render() {
  renderRegions();
  renderPeriods();
  renderHistory();
  renderNews();
}

async function loadData() {
  try {
    const res = await fetch('data/news.json', { cache: 'no-store' });
    if (!res.ok) throw new Error('data load failed');
    const payload = await res.json();
    state.data = Array.isArray(payload.items) ? payload.items : [];
  } catch (_) {
    state.data = [];
  }
  render();
}

let deferredPrompt;
window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault(); deferredPrompt = e;
  const btn = $('#installBtn'); btn.hidden = false;
  btn.onclick = async () => { deferredPrompt.prompt(); await deferredPrompt.userChoice; btn.hidden = true; };
});

if ('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js');
loadData();
const REGIONS = [
  { name: 'International', icon: '🌐', desc: 'Grandes crises, marchés mondiaux et diplomatie' },
  { name: 'Europe', icon: '🇪🇺', desc: 'UE, Russie, Ukraine et voisinage européen' },
  { name: 'Asie', icon: '🌏', desc: 'Chine, Inde, Moyen-Orient et Asie-Pacifique' },
  { name: 'Amérique du Nord', icon: '🌎', desc: 'États-Unis, Canada et Mexique' },
  { name: 'Amérique du Sud', icon: '🧭', desc: 'Brésil, Argentine et continent sud-américain' },
  { name: 'Afrique', icon: '🌍', desc: 'Politique, sécurité et économies africaines' },
  { name: 'Océanie', icon: '🌊', desc: 'Australie, Nouvelle-Zélande et Pacifique' }
];

const state = {
  region: null,
  period: 'day',
  bucket: null,
  data: [],
  buckets: { day: [], week: [], month: [] },
  coverage: {}
};

const $ = (q) => document.querySelector(q);

function stars(score) {
  return '★'.repeat(score) + '☆'.repeat(10 - score);
}

function escapeHtml(s = '') {
  return String(s).replace(/[&<>'"]/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
  }[c]));
}

function regionMeta(name) {
  return REGIONS.find(r => r.name === name) || REGIONS[0];
}

function sortItems(items) {
  return [...items].sort((a, b) => (b.score - a.score) || a.summary.localeCompare(b.summary, 'fr'));
}

function getBuckets() {
  const configured = state.buckets[state.period] || [];
  if (configured.length) return configured;
  return [...new Set(state.data.filter(x => x.period === state.period).map(x => x.bucket))];
}

function renderRegionGrid() {
  const grid = $('#regionGrid');
  grid.innerHTML = REGIONS.map(region => `
    <button class="region-card" data-region="${escapeHtml(region.name)}">
      <span class="region-card-icon">${region.icon}</span>
      <span class="region-card-copy">
        <strong>${escapeHtml(region.name)}</strong>
        <small>${escapeHtml(region.desc)}</small>
      </span>
      <span class="region-arrow">›</span>
    </button>
  `).join('');

  grid.querySelectorAll('.region-card').forEach(btn => {
    btn.onclick = () => openRegion(btn.dataset.region);
  });
}

function openRegion(region) {
  state.region = region;
  state.period = 'day';
  state.bucket = null;
  $('#regionPage').hidden = true;
  $('#newsPage').hidden = false;
  $('#backBtn').hidden = false;
  const meta = regionMeta(region);
  $('#regionTitle').textContent = region;
  $('#regionIcon').textContent = meta.icon;
  renderNewsPage();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function goHome() {
  state.region = null;
  $('#newsPage').hidden = true;
  $('#regionPage').hidden = false;
  $('#backBtn').hidden = true;
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function itemMatchesRegion(item) {
  if (Array.isArray(item.regions)) return item.regions.includes(state.region);
  return item.region === state.region;
}

function renderPeriods() {
  document.querySelectorAll('.period-tab').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.period === state.period);
    btn.onclick = () => {
      state.period = btn.dataset.period;
      state.bucket = null;
      renderNewsPage();
    };
  });
}

function renderHistory() {
  const select = $('#historySelect');
  const buckets = getBuckets();

  if (!state.bucket || !buckets.includes(state.bucket)) {
    state.bucket = buckets[0] || null;
  }

  if (!buckets.length) {
    select.innerHTML = '<option>Aucun historique</option>';
    select.disabled = true;
    $('#coverageText').textContent = '';
    return;
  }

  select.disabled = false;
  select.innerHTML = buckets.map(b =>
    `<option value="${escapeHtml(b)}" ${b === state.bucket ? 'selected' : ''}>${escapeHtml(b)}</option>`
  ).join('');

  select.onchange = e => {
    state.bucket = e.target.value;
    renderNews();
  };

  updateCoverage();
}

function updateCoverage() {
  const el = $('#coverageText');
  if (!state.bucket) {
    el.textContent = '';
    return;
  }
  const key = `${state.period}:${state.bucket}`;
  el.textContent = state.coverage[key] || '';
}

function renderNews() {
  updateCoverage();

  const items = sortItems(state.data.filter(x =>
    itemMatchesRegion(x) &&
    x.period === state.period &&
    x.bucket === state.bucket &&
    x.score >= 5
  ));

  const header = $('#summaryHeader');
  const list = $('#newsList');

  header.innerHTML = `
    <div>
      <span class="result-count">${items.length} sujet${items.length > 1 ? 's' : ''}</span>
      <span class="result-date">${state.bucket ? escapeHtml(state.bucket) : ''}</span>
    </div>
  `;

  if (!items.length) {
    const message = state.period === 'month'
      ? 'Le condensé mensuel se construira au fil des prochaines veilles.'
      : 'Aucun événement majeur retenu pour cette zone et cette période.';
    list.innerHTML = `<div class="empty"><span>◎</span><p>${message}</p></div>`;
    return;
  }

  list.innerHTML = items.map(item => `
    <article class="news-item ${item.score >= 8 ? 'hot' : ''}">
      <div class="meta">
        <span class="score score-${item.score}">${item.score}/10</span>
        <span class="stars" aria-label="${item.score} étoiles sur 10">${stars(item.score)}</span>
        ${item.category ? `<span class="tag">${escapeHtml(item.category)}</span>` : ''}
      </div>
      <p class="news-summary">${escapeHtml(item.summary)}</p>
      <div class="sources">(${item.sources.map(escapeHtml).join(' • ')})</div>
    </article>
  `).join('');
}

function renderNewsPage() {
  renderPeriods();
  renderHistory();
  renderNews();
}

async function loadData() {
  try {
    const res = await fetch('data/news.json?v=' + Date.now(), { cache: 'no-store' });
    if (!res.ok) throw new Error('data load failed');
    const payload = await res.json();
    state.data = Array.isArray(payload.items) ? payload.items : [];
    state.buckets = payload.buckets || state.buckets;
    state.coverage = payload.coverage || {};
  } catch (error) {
    console.error(error);
    state.data = [];
  }
  renderRegionGrid();
}

$('#backBtn').onclick = goHome;

let deferredPrompt;
window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  deferredPrompt = e;
  const btn = $('#installBtn');
  btn.hidden = false;
  btn.onclick = async () => {
    deferredPrompt.prompt();
    await deferredPrompt.userChoice;
    btn.hidden = true;
  };
});

if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('sw.js');
}

loadData();
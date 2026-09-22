const REGIONS = [
  { name: 'International', icon: '🌐', desc: 'Grandes crises, marchés mondiaux et diplomatie' },
  { name: 'Europe', icon: '🇪🇺', desc: 'UE, Russie, Ukraine et voisinage européen' },
  { name: 'Asie', icon: '🌏', desc: 'Asie, Moyen-Orient et Indo-Pacifique' },
  { name: 'Amérique du Nord', icon: '🌎', desc: 'États-Unis, Canada et Mexique' },
  { name: 'Amérique du Sud', icon: '🧭', desc: 'Brésil, Argentine et continent sud-américain' },
  { name: 'Afrique', icon: '🌍', desc: 'Politique, sécurité et économies africaines' },
  { name: 'Océanie', icon: '🌊', desc: 'Australie, Nouvelle-Zélande et Pacifique' }
];

const CONTINENT_NAMES = ['Europe', 'Asie', 'Amérique du Nord', 'Amérique du Sud', 'Afrique', 'Océanie'];

const state = {
  mode: 'region',
  region: null,
  country: null,
  period: 'day',
  bucket: null,
  data: [],
  buckets: { day: [], week: [], month: [] },
  coverage: {},
  visibleCount: 10,
  countryThreshold: 5
};

const $ = q => document.querySelector(q);

function stars(score) {
  const safe = Math.max(0, Math.min(10, Number(score) || 0));
  return '★'.repeat(safe) + '☆'.repeat(10 - safe);
}

function escapeHtml(s = '') {
  return String(s).replace(/[&<>'"]/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
  }[c]));
}

function normalizeText(s = '') {
  return String(s)
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[’']/g, "'")
    .replace(/[^a-z0-9' -]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function regionMeta(name) {
  return REGIONS.find(r => r.name === name) || REGIONS[0];
}

function sortItems(items) {
  return [...items].sort((a, b) => {
    const ta = Date.parse(a.published_at || a._loadedAt || 0) || 0;
    const tb = Date.parse(b.published_at || b._loadedAt || 0) || 0;
    return (b.score - a.score) || (tb - ta) || a.summary.localeCompare(b.summary, 'fr');
  });
}

function articleLinks(item) {
  const urls = [...(item.urls || []), ...(item.url ? [item.url] : [])].filter(Boolean);
  if (urls.length) return urls;
  const q = encodeURIComponent(item.summary || '');
  return q ? [`https://news.google.com/search?q=${q}&hl=fr&gl=FR&ceid=FR%3Afr`] : [];
}

function clickableSummary(item) {
  const links = articleLinks(item);
  const text = escapeHtml(item.summary);
  if (!links.length) return `<p class="news-summary">${text}</p>`;
  return `<a class="news-summary news-link" href="${escapeHtml(links[0])}" target="_blank" rel="noopener noreferrer" title="Ouvrir l’article source">${text}<span class="link-mark">↗</span></a>`;
}

function getBuckets() {
  const configured = state.buckets[state.period] || [];
  if (configured.length) return configured;
  return [...new Set(state.data.filter(x => x.period === state.period).map(x => x.bucket))];
}

function renderRegionGrid() {
  const grid = $('#regionGrid');
  const regionCards = REGIONS.map(region => `
    <button class="region-card" data-region="${escapeHtml(region.name)}">
      <span class="region-card-icon">${region.icon}</span>
      <span class="region-card-copy">
        <strong>${escapeHtml(region.name)}</strong>
        <small>${escapeHtml(region.desc)}</small>
      </span>
      <span class="region-arrow">›</span>
    </button>
  `).join('');

  const countryCard = `
    <button class="region-card country-entry-card" id="countryEntry">
      <span class="region-card-icon">🏳️</span>
      <span class="region-card-copy">
        <strong>Par pays</strong>
        <small>Rechercher parmi les 195 pays du monde</small>
      </span>
      <span class="region-arrow">›</span>
    </button>
  `;

  grid.innerHTML = regionCards + countryCard;
  grid.querySelectorAll('[data-region]').forEach(btn => {
    btn.onclick = () => openRegion(btn.dataset.region);
  });
  $('#countryEntry').onclick = openCountryPicker;
}

function openRegion(region) {
  state.mode = 'region';
  state.region = region;
  state.country = null;
  state.period = 'day';
  state.bucket = null;
  state.visibleCount = 10;
  $('#regionPage').hidden = true;
  $('#countryPage').hidden = true;
  $('#newsPage').hidden = false;
  const meta = regionMeta(region);
  $('#regionTitle').textContent = region;
  $('#regionIcon').textContent = meta.icon;
  $('#sectionEyebrow').textContent = 'CONDENSÉ';
  renderNewsPage();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function openCountryPicker() {
  state.mode = 'country';
  state.region = null;
  state.country = null;
  state.bucket = null;
  $('#regionPage').hidden = true;
  $('#newsPage').hidden = true;
  $('#countryPage').hidden = false;
  $('#countryPickerLabel').textContent = 'Choisir un pays';
  $('#countryDropdown').hidden = false;
  $('#countryPickerButton').setAttribute('aria-expanded', 'true');
  $('#countrySearch').value = '';
  renderCountryList('');
  setTimeout(() => $('#countrySearch').focus(), 50);
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function renderCountryList(query = '') {
  const q = normalizeText(query);
  const matches = COUNTRIES.filter(country => normalizeText(country).includes(q));
  const list = $('#countryList');

  if (!matches.length) {
    list.innerHTML = '<div class="country-no-result">Aucun pays trouvé</div>';
    return;
  }

  list.innerHTML = matches.map(country => `
    <button type="button" class="country-option" data-country="${escapeHtml(country)}">
      <span>🏳️</span>
      <span>${escapeHtml(country)}</span>
    </button>
  `).join('');

  list.querySelectorAll('.country-option').forEach(btn => {
    btn.onclick = () => selectCountry(btn.dataset.country);
  });
}

function selectCountry(country) {
  state.mode = 'country';
  state.country = country;
  state.region = null;
  state.period = 'day';
  state.bucket = null;
  state.visibleCount = 10;
  state.countryThreshold = 5;
  $('#countryPickerLabel').textContent = country;
  $('#countryDropdown').hidden = true;
  $('#countryPickerButton').setAttribute('aria-expanded', 'false');
  $('#countryPage').hidden = true;
  $('#newsPage').hidden = false;
  $('#regionIcon').textContent = '🏳️';
  $('#regionTitle').textContent = country;
  $('#sectionEyebrow').textContent = 'VEILLE PAYS';
  renderNewsPage();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function goHome() {
  state.mode = 'region';
  state.region = null;
  state.country = null;
  state.bucket = null;
  $('#countryPage').hidden = true;
  $('#newsPage').hidden = true;
  $('#regionPage').hidden = false;
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function itemMatchesRegion(item, region = state.region) {
  if (Array.isArray(item.regions)) return item.regions.includes(region);
  return item.region === region;
}

function normalizedKey(item) {
  return normalizeText(item.summary || '');
}

function getInternationalDigest() {
  const selected = [];
  const seen = new Set();
  const base = state.data.filter(x =>
    x.period === state.period &&
    x.bucket === state.bucket &&
    x.score >= 5
  );

  for (const continent of CONTINENT_NAMES) {
    const top = sortItems(base.filter(x => itemMatchesRegion(x, continent))).slice(0, 2);
    for (const item of top) {
      const key = normalizedKey(item);
      if (!key || seen.has(key)) continue;
      selected.push({ ...item, originRegion: continent });
      seen.add(key);
    }
  }

  if (selected.length < 10) {
    const pool = sortItems(base.filter(x =>
      CONTINENT_NAMES.some(continent => itemMatchesRegion(x, continent))
    ));
    for (const item of pool) {
      if (selected.length >= 10) break;
      const key = normalizedKey(item);
      if (!key || seen.has(key)) continue;
      selected.push({
        ...item,
        originRegion: CONTINENT_NAMES.find(continent => itemMatchesRegion(item, continent)) || ''
      });
      seen.add(key);
    }
  }

  return sortItems(selected);
}

function countryAliases(country) {
  const aliases = new Set([normalizeText(country)]);
  const configured = (COUNTRY_ALIASES && COUNTRY_ALIASES[country]) || [];
  configured.forEach(alias => aliases.add(normalizeText(alias)));

  if (country.includes('(')) {
    aliases.add(normalizeText(country.replace(/\s*\([^)]*\)/g, '')));
  }

  if (country === 'Congo (RDC)') {
    ['rdc', 'république démocratique du congo', 'democratic republic of congo', 'congo-kinshasa'].forEach(x => aliases.add(normalizeText(x)));
  }
  if (country === 'Congo (République du)') {
    ['république du congo', 'republic of congo', 'congo-brazzaville'].forEach(x => aliases.add(normalizeText(x)));
  }
  if (country === 'Tchéquie') {
    ['république tchèque', 'czechia', 'czech republic'].forEach(x => aliases.add(normalizeText(x)));
  }
  if (country === 'Birmanie') {
    ['myanmar', 'birman'].forEach(x => aliases.add(normalizeText(x)));
  }
  if (country === 'Eswatini') {
    ['swaziland'].forEach(x => aliases.add(normalizeText(x)));
  }
  if (country === 'Timor oriental') {
    ['timor-leste', 'east timor'].forEach(x => aliases.add(normalizeText(x)));
  }

  return [...aliases].filter(Boolean);
}

function itemMatchesCountry(item, country = state.country) {
  if (!country) return false;

  if (Array.isArray(item.countries)) {
    const normalizedCountry = normalizeText(country);
    if (item.countries.some(c => normalizeText(c) === normalizedCountry)) return true;
  }

  const haystack = normalizeText([
    item.summary || '',
    item.category || '',
    ...(item.sources || [])
  ].join(' '));

  return countryAliases(country).some(alias => {
    if (!alias || alias.length < 3) return false;
    const padded = ` ${haystack} `;
    return padded.includes(` ${alias} `) || haystack.includes(alias);
  });
}

function getCountryFeed() {
  const base = state.data.filter(x =>
    x.period === state.period &&
    x.bucket === state.bucket &&
    itemMatchesCountry(x)
  );

  for (let threshold = 5; threshold >= 1; threshold--) {
    const found = sortItems(base.filter(x => Number(x.score) >= threshold));
    if (found.length) {
      state.countryThreshold = threshold;
      return found;
    }
  }

  state.countryThreshold = 1;
  return [];
}

function renderPeriods() {
  document.querySelectorAll('.period-tab').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.period === state.period);
    btn.onclick = () => {
      state.period = btn.dataset.period;
      state.bucket = null;
      state.visibleCount = 10;
      state.countryThreshold = 5;
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
    state.visibleCount = 10;
    state.countryThreshold = 5;
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
  el.textContent = state.coverage[`${state.period}:${state.bucket}`] || '';
}

function renderNews() {
  updateCoverage();

  let raw;
  if (state.mode === 'country') {
    raw = getCountryFeed();
  } else if (state.region === 'International') {
    raw = getInternationalDigest();
  } else {
    raw = sortItems(state.data.filter(x =>
      itemMatchesRegion(x) &&
      x.period === state.period &&
      x.bucket === state.bucket &&
      x.score >= 5
    ));
  }

  const seen = new Set();
  const items = raw.filter(item => {
    const k = normalizedKey(item);
    if (!k || seen.has(k)) return false;
    seen.add(k);
    return true;
  });

  const header = $('#summaryHeader');
  const list = $('#newsList');

  let thresholdNote = '';
  if (state.mode === 'country' && items.length && state.countryThreshold < 5) {
    thresholdNote = `<span class="threshold-note">Seuil abaissé à ${state.countryThreshold}/10 faute d’actualité ≥5/10</span>`;
  }

  header.innerHTML = `
    <div>
      <span class="result-count">${items.length} information${items.length > 1 ? 's' : ''}</span>
      <span class="result-date">${state.bucket ? escapeHtml(state.bucket) : ''}</span>
    </div>
    ${thresholdNote}
  `;

  if (!items.length) {
    list.innerHTML = state.mode === 'country'
      ? '<div class="empty"><span>◎</span><p>Aucune actualité trouvée pour ce pays sur cette période, même après abaissement du seuil.</p></div>'
      : '<div class="empty"><span>◎</span><p>Aucune information majeure disponible pour cette période.</p></div>';
    return;
  }

  const shown = items.slice(0, state.visibleCount);
  list.innerHTML = shown.map(item => `
    <article class="news-item ${item.score >= 8 ? 'hot' : ''}">
      <div class="meta">
        <span class="score score-${item.score}">${item.score}/10</span>
        <span class="stars" aria-label="${item.score} étoiles sur 10">${stars(item.score)}</span>
        ${state.region === 'International' && item.originRegion ? `<span class="origin-region">${escapeHtml(item.originRegion)}</span>` : ''}
        ${item.category ? `<span class="tag">${escapeHtml(item.category)}</span>` : ''}
      </div>
      ${clickableSummary(item)}
      <div class="sources">(${(item.sources || []).map(escapeHtml).join(' • ')})</div>
    </article>
  `).join('');

  if (items.length > shown.length) {
    list.insertAdjacentHTML('beforeend',
      `<button class="more-button" id="moreButton">Suite (${items.length - shown.length})</button>`
    );
    $('#moreButton').onclick = () => {
      state.visibleCount += 10;
      renderNews();
    };
  }
}

function renderNewsPage() {
  renderPeriods();
  renderHistory();
  renderNews();
}

async function loadData() {
  try {
    const stamp = Date.now();
    const urls = [
      'data/news.json',
      'data/hourly.json',
      'data/hourly-archive-2026-09-21.json',
      'data/hourly-10.json',
      'data/hourly-11.json',
      'data/hourly-12.json',
      'data/hourly-13.json',
      'data/hourly-14.json',
      'data/hourly-15.json',
      'data/hourly-16.json',
      'data/hourly-17.json',
      'data/hourly-18.json',
      'data/hourly-19.json',
      'data/hourly-latest.json'
    ];

    const results = await Promise.all(
      urls.map(url => fetch(url + '?v=' + stamp, { cache: 'no-store' }).catch(() => null))
    );

    if (!results[0] || !results[0].ok) throw new Error('data load failed');

    const payloads = [];
    for (const res of results) {
      payloads.push(res && res.ok
        ? await res.json()
        : { items: [], buckets: {}, coverage: {} }
      );
    }

    state.data = payloads.flatMap(p =>
      Array.isArray(p.items)
        ? p.items.map(x => ({ ...x, _loadedAt: x.published_at || p.generated_at || '' }))
        : []
    );

    state.buckets = {
      day: [...new Set(payloads.flatMap(p => (p.buckets && p.buckets.day) || []))],
      week: [...new Set(payloads.flatMap(p => (p.buckets && p.buckets.week) || []))],
      month: [...new Set(payloads.flatMap(p => (p.buckets && p.buckets.month) || []))]
    };

    state.coverage = Object.assign({}, ...payloads.map(p => p.coverage || {}));
  } catch (error) {
    console.error(error);
    state.data = [];
  }

  renderRegionGrid();
}

$('#brandHome').onclick = goHome;

$('#countryPickerButton').onclick = () => {
  const dropdown = $('#countryDropdown');
  dropdown.hidden = !dropdown.hidden;
  $('#countryPickerButton').setAttribute('aria-expanded', String(!dropdown.hidden));
  if (!dropdown.hidden) {
    $('#countrySearch').focus();
  }
};

$('#countrySearch').addEventListener('input', e => renderCountryList(e.target.value));

if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('sw.js');
}

loadData();
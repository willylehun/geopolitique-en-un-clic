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
  countryThreshold: 5,
  electionData: null,
  candidateId: null,
  electionPeriod: 'day',
  electionBucket: null,
  electionVisibleCount: 10,
  electionView: 'candidates',
  candidateTab: 'news',
  partyName: null,
  partyTab: 'news'
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

  const electionCard = `
    <button class="region-card election-entry-card" id="electionEntry">
      <span class="region-card-icon">🗳️</span>
      <span class="region-card-copy">
        <strong>Élection française</strong>
        <small>Présidentielle 2027 : candidats, actualités et programmes</small>
      </span>
      <span class="region-arrow">›</span>
    </button>
  `;

  grid.innerHTML = regionCards + countryCard + electionCard;
  grid.querySelectorAll('[data-region]').forEach(btn => {
    btn.onclick = () => openRegion(btn.dataset.region);
  });
  $('#countryEntry').onclick = openCountryPicker;
  const electionEntry = $('#electionEntry');
  if (electionEntry) electionEntry.onclick = openElectionPicker;
}

function openRegion(region) {
  $('#brandHome').classList.remove('home-mode');
  state.mode = 'region';
  state.region = region;
  state.country = null;
  state.period = 'day';
  state.bucket = null;
  state.visibleCount = 10;
  $('#regionPage').hidden = true;
  $('#countryPage').hidden = true;
  $('#electionPage').hidden = true;
  $('#newsPage').hidden = false;
  const meta = regionMeta(region);
  $('#regionTitle').textContent = region;
  $('#regionIcon').textContent = meta.icon;
  $('#sectionEyebrow').textContent = 'CONDENSÉ';
  renderNewsPage();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function openCountryPicker() {
  $('#brandHome').classList.remove('home-mode');
  state.mode = 'country';
  state.region = null;
  state.country = null;
  state.bucket = null;
  $('#regionPage').hidden = true;
  $('#newsPage').hidden = true;
  $('#electionPage').hidden = true;
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
  $('#brandHome').classList.add('home-mode');
  state.mode = 'region';
  state.region = null;
  state.country = null;
  state.bucket = null;
  $('#countryPage').hidden = true;
  $('#electionPage').hidden = true;
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


function openElectionPicker() {
  $('#brandHome').classList.remove('home-mode');
  state.mode = 'election';
  state.region = null;
  state.country = null;
  state.candidateId = null;
  state.electionPeriod = 'day';
  state.electionBucket = null;
  state.electionVisibleCount = 10;
  state.electionView = 'candidates';
  state.candidateTab = 'news';
  state.partyName = null;
  $('#regionPage').hidden = true;
  $('#countryPage').hidden = true;
  $('#newsPage').hidden = true;
  $('#electionPage').hidden = false;
  $('#candidateContent').hidden = true;
  $('#partyContent').hidden = true;
  renderElectionMode();
  $('#candidatePickerLabel').textContent = 'Choisir un candidat';
  $('#candidateDropdown').hidden = false;
  $('#candidatePickerButton').setAttribute('aria-expanded', 'true');
  $('#candidateSearch').value = '';
  if (state.electionData) {
    $('#electionOfficialNote').textContent = state.electionData.official_note || '';
  }
  renderCandidateList('');
  setTimeout(() => $('#candidateSearch').focus(), 50);
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function renderElectionMode() {
  document.querySelectorAll('.election-mode-tab').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.electionView === state.electionView);
    btn.onclick = () => {
      state.electionView = btn.dataset.electionView;
      $('#candidateArea').hidden = state.electionView !== 'candidates';
      $('#partyArea').hidden = state.electionView !== 'parties';
      $('#candidateContent').hidden = true;
      $('#partyContent').hidden = true;
      if (state.electionView === 'parties') renderPartyList('');
    };
  });
  $('#candidateArea').hidden = state.electionView !== 'candidates';
  $('#partyArea').hidden = state.electionView !== 'parties';
}

function getParties() {
  const map = new Map();
  for (const c of state.electionData?.candidates || []) {
    if (!c.party) continue;
    if (!map.has(c.party)) map.set(c.party, { name:c.party, candidate_ids:[], ...(state.electionData?.parties || []).find(p => p.name === c.party) });
    map.get(c.party).candidate_ids = [...new Set([...(map.get(c.party).candidate_ids || []), c.id])];
  }
  for (const p of state.electionData?.parties || []) if (!map.has(p.name)) map.set(p.name, p);
  return [...map.values()].sort((x,y)=>x.name.localeCompare(y.name,'fr'));
}

function renderPartyList(query='') {
  const q=normalizeText(query), list=$('#partyList');
  const parties=getParties().filter(p=>normalizeText(p.name).includes(q));
  list.innerHTML=parties.length ? parties.map(p=>`<button type="button" class="candidate-option" data-party="${escapeHtml(p.name)}"><span class="candidate-option-name">${escapeHtml(p.name)}</span><span class="candidate-option-status">${(p.candidate_ids||[]).length} candidat(s) suivi(s)</span></button>`).join('') : '<div class="country-no-result">Aucun parti trouvé</div>';
  list.querySelectorAll('[data-party]').forEach(b=>b.onclick=()=>selectParty(b.dataset.party));
}

function selectParty(name) {
  state.partyName=name; state.partyTab='news'; state.electionPeriod='day'; state.electionBucket=null;
  $('#partyPickerLabel').textContent=name; $('#partyDropdown').hidden=true; $('#partyContent').hidden=false;
  $('#partyName').textContent=name;
  renderPartyCandidates();
  renderPartyPage();
}

function renderInfoCards(items, emptyText) {
  if (!items?.length) return `<div class="empty"><span>◎</span><p>${escapeHtml(emptyText)}</p></div>`;
  return items.map(x=>`<article class="program-card"><p>${escapeHtml(typeof x==='string'?x:(x.summary||x.text||''))}</p>${x.sources?.length?`<div class="sources">(${x.sources.map(escapeHtml).join(' • ')})</div>`:''}</article>`).join('');
}

function renderCandidateTab() {
  const c=(state.electionData?.candidates||[]).find(x=>x.id===state.candidateId); if(!c)return;
  document.querySelectorAll('.candidate-detail-tab').forEach(b=>{b.classList.toggle('active',b.dataset.candidateTab===state.candidateTab);b.onclick=()=>{state.candidateTab=b.dataset.candidateTab;renderCandidateTab();};});
  $('#candidateNewsPanel').hidden=state.candidateTab!=='news'; $('#candidateProgramPanel').hidden=state.candidateTab!=='program';
  $('#candidateBioPanel').hidden=state.candidateTab!=='bio'; $('#candidateControversyPanel').hidden=state.candidateTab!=='controversies';
  if(state.candidateTab==='bio') $('#candidateBio').innerHTML=c.bio? `<article class="program-card"><p>${escapeHtml(c.bio)}</p></article>` : renderInfoCards([], 'Parcours en cours de documentation par la veille.');
  if(state.candidateTab==='controversies') $('#candidateControversies').innerHTML=renderInfoCards(c.controversies, 'Aucune controverse suffisamment documentée dans les sources suivies.');
}

function partyNews() {
  const p=getParties().find(x=>x.name===state.partyName); if(!p)return[];
  const ids=p.candidate_ids||[];
  return (state.electionData?.news||[]).filter(n=>(n.party_names||[]).includes(p.name)||(n.candidate_ids||[]).some(id=>ids.includes(id))).filter(electionItemInBucket);
}

function renderPartyCandidates() {
  const p=getParties().find(x=>x.name===state.partyName);
  const box=$('#partyCandidates');
  if(!p || !box) return;
  const candidates=(state.electionData?.candidates||[]).filter(c=>(p.candidate_ids||[]).includes(c.id));
  box.innerHTML=candidates.length ? candidates.map(c=>`
    <button type="button" class="candidate-option party-candidate-link ${c.status==='withdrawn'?'withdrawn':''}" data-party-candidate="${escapeHtml(c.id)}">
      <span class="candidate-option-name"><strong>${escapeHtml(c.name)}</strong></span>
      <span class="candidate-option-status">${escapeHtml(c.status_label||'')}</span>
    </button>`).join('') : '<div class="country-no-result">Aucun candidat relié actuellement.</div>';
  box.querySelectorAll('[data-party-candidate]').forEach(b=>b.onclick=()=>{
    state.electionView='candidates'; renderElectionMode(); selectCandidate(b.dataset.partyCandidate);
  });
}

function renderPartyPage() {
  renderPartyCandidates();
  renderElectionPeriods(); renderElectionHistory();
  const p=getParties().find(x=>x.name===state.partyName); if(!p)return;
  document.querySelectorAll('.party-detail-tab').forEach(b=>{b.classList.toggle('active',b.dataset.partyTab===state.partyTab);b.onclick=()=>{state.partyTab=b.dataset.partyTab;renderPartyPage();};});
  $('#partyNewsPanel').hidden=state.partyTab!=='news'; $('#partyProgramPanel').hidden=state.partyTab!=='program'; $('#partyControversyPanel').hidden=state.partyTab!=='controversies';
  if(state.partyTab==='news'){const items=partyNews();$('#partyNewsList').innerHTML=items.length?items.map(i=>`<article class="news-item"><div class="meta"><span class="tag">${escapeHtml(formatIsoDateFr(i.date))}</span></div><p class="news-summary">${escapeHtml(i.summary)}</p><div class="sources">(${(i.sources||[]).map(escapeHtml).join(' • ')})</div></article>`).join(''):'<div class="empty"><span>◎</span><p>Aucune actualité enregistrée pour ce parti sur cette période.</p></div>';}
  $('#partyProgram').innerHTML=p.program?Object.entries(p.program).map(([k,v])=>`<article class="program-card"><h4>${escapeHtml(k)}</h4><p>${escapeHtml(v)}</p></article>`).join(''):renderInfoCards([], 'Programme du parti en cours de documentation par la veille.');
  $('#partyControversies').innerHTML=renderInfoCards(p.controversies, 'Aucune controverse suffisamment documentée dans les sources suivies.');
}

function candidateLabel(candidate) {
  return `${candidate.name} (${candidate.party})`;
}

function isCandidateVisible(candidate) {
  if (candidate.status !== 'withdrawn') return true;
  if (!candidate.withdrawn_at) return true;
  const today = parisTodayISO();
  const start = new Date(candidate.withdrawn_at + 'T12:00:00Z');
  const end = new Date(today + 'T12:00:00Z');
  const ageDays = Math.floor((end - start) / 86400000);
  return ageDays < 7;
}

function renderCandidateList(query = '') {
  const list = $('#candidateList');
  const data = state.electionData;
  if (!data) {
    list.innerHTML = '<div class="country-no-result">Chargement des candidatures…</div>';
    return;
  }
  const q = normalizeText(query);
  const candidates = [...(data.candidates || [])]
    .filter(c => isCandidateVisible(c) && normalizeText(candidateLabel(c)).includes(q))
    .sort((a, b) => {
      if ((a.status === 'withdrawn') !== (b.status === 'withdrawn')) return a.status === 'withdrawn' ? 1 : -1;
      return a.name.localeCompare(b.name, 'fr');
    });

  if (!candidates.length) {
    list.innerHTML = '<div class="country-no-result">Aucun candidat trouvé</div>';
    return;
  }

  list.innerHTML = candidates.map(candidate => `
    <button type="button" class="candidate-option ${candidate.status === 'withdrawn' ? 'withdrawn' : ''}" data-candidate="${escapeHtml(candidate.id)}">
      <span class="candidate-option-name">${escapeHtml(candidate.name)} <small>(${escapeHtml(candidate.party)})</small></span>
      <span class="candidate-option-status">${escapeHtml(candidate.status_label || '')}</span>
    </button>
  `).join('');

  list.querySelectorAll('.candidate-option').forEach(btn => {
    btn.onclick = () => selectCandidate(btn.dataset.candidate);
  });
}

function selectCandidate(candidateId) {
  const candidate = (state.electionData?.candidates || []).find(c => c.id === candidateId);
  if (!candidate) return;

  state.mode = 'election';
  state.candidateId = candidateId;
  state.electionPeriod = 'day';
  state.electionBucket = null;
  state.electionVisibleCount = 10;

  $('#candidatePickerLabel').textContent = candidateLabel(candidate);
  $('#candidateDropdown').hidden = true;
  $('#candidatePickerButton').setAttribute('aria-expanded', 'false');
  $('#candidateContent').hidden = false;
  $('#candidateName').textContent = candidate.name;
  $('#candidateParty').textContent = candidate.party;
  $('#candidateStatus').textContent = candidate.status_label || '';
  $('#candidateStatus').className = 'candidate-status status-' + (candidate.status || 'unknown');

  state.candidateTab = 'news';
  renderElectionPage();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function parisTodayISO() {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Europe/Paris', year: 'numeric', month: '2-digit', day: '2-digit'
  }).formatToParts(new Date());
  const map = Object.fromEntries(parts.map(p => [p.type, p.value]));
  return `${map.year}-${map.month}-${map.day}`;
}

function formatIsoDateFr(iso) {
  const [y, m, d] = iso.split('-').map(Number);
  return new Intl.DateTimeFormat('fr-FR', {
    day: 'numeric', month: 'long', year: 'numeric', timeZone: 'Europe/Paris'
  }).format(new Date(Date.UTC(y, m - 1, d, 12, 0, 0)));
}

function weekBucket(iso) {
  const [y, m, d] = iso.split('-').map(Number);
  const date = new Date(Date.UTC(y, m - 1, d, 12));
  const day = (date.getUTCDay() + 6) % 7;
  const monday = new Date(date);
  monday.setUTCDate(date.getUTCDate() - day);
  const sunday = new Date(monday);
  sunday.setUTCDate(monday.getUTCDate() + 6);
  const toIso = dt => dt.toISOString().slice(0, 10);
  return `${toIso(monday)}|${toIso(sunday)}`;
}

function monthBucket(iso) {
  return iso.slice(0, 7);
}

function electionBuckets() {
  const news = state.electionData?.news || [];
  const today = parisTodayISO();
  const dates = [...new Set([today, ...news.map(n => n.date).filter(Boolean)])].sort().reverse();

  if (state.electionPeriod === 'day') return dates;
  if (state.electionPeriod === 'week') {
    return [...new Set(dates.map(weekBucket))].sort().reverse();
  }
  return [...new Set(dates.map(monthBucket))].sort().reverse();
}

function electionBucketLabel(bucket) {
  if (state.electionPeriod === 'day') return formatIsoDateFr(bucket);
  if (state.electionPeriod === 'week') {
    const [start, end] = bucket.split('|');
    return `${formatIsoDateFr(start)} – ${formatIsoDateFr(end)}`;
  }
  const [y, m] = bucket.split('-').map(Number);
  return new Intl.DateTimeFormat('fr-FR', {
    month: 'long', year: 'numeric', timeZone: 'Europe/Paris'
  }).format(new Date(Date.UTC(y, m - 1, 1, 12)));
}

function electionItemInBucket(item) {
  if (!item?.date || !state.electionBucket) return false;
  if (state.electionPeriod === 'day') return item.date === state.electionBucket;
  if (state.electionPeriod === 'week') return weekBucket(item.date) === state.electionBucket;
  return monthBucket(item.date) === state.electionBucket;
}

function renderElectionPeriods() {
  document.querySelectorAll('.election-period-tab').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.electionPeriod === state.electionPeriod);
    btn.onclick = () => {
      state.electionPeriod = btn.dataset.electionPeriod;
      state.electionBucket = null;
      state.electionVisibleCount = 10;
      renderElectionPage();
    };
  });
}

function renderElectionHistory() {
  const select = state.electionView === 'parties' ? $('#electionHistorySelectParty') : $('#electionHistorySelect');
  const buckets = electionBuckets();
  if (!state.electionBucket || !buckets.includes(state.electionBucket)) {
    state.electionBucket = buckets[0] || null;
  }
  if (!buckets.length) {
    select.innerHTML = '<option>Aucun historique</option>';
    select.disabled = true;
    return;
  }
  select.disabled = false;
  select.innerHTML = buckets.map(bucket =>
    `<option value="${escapeHtml(bucket)}" ${bucket === state.electionBucket ? 'selected' : ''}>${escapeHtml(electionBucketLabel(bucket))}</option>`
  ).join('');
  select.onchange = e => {
    state.electionBucket = e.target.value;
    state.electionVisibleCount = 10;
    if (state.electionView === 'parties') renderPartyPage(); else renderElectionNews();
  };
}

function renderElectionNews() {
  const candidateId = state.candidateId;
  const candidate = (state.electionData?.candidates || []).find(c => c.id === candidateId);
  const items = (state.electionData?.news || [])
    .filter(item => (item.candidate_ids || []).includes(candidateId) && electionItemInBucket(item))
    .sort((a, b) => (b.date || '').localeCompare(a.date || ''));

  $('#electionNewsHeader').innerHTML = `
    <div>
      <span class="result-count">${items.length} actualité${items.length > 1 ? 's' : ''}</span>
      <span class="result-date">${state.electionBucket ? escapeHtml(electionBucketLabel(state.electionBucket)) : ''}</span>
    </div>
  `;

  const list = $('#electionNewsList');
  if (!items.length) {
    list.innerHTML = `<div class="empty"><span>◎</span><p>Aucune actualité enregistrée pour ${escapeHtml(candidate?.name || 'ce candidat')} sur cette période.</p></div>`;
    return;
  }

  const shown = items.slice(0, state.electionVisibleCount);
  list.innerHTML = shown.map(item => `
    <article class="news-item election-news-item">
      <div class="meta">
        <span class="tag">Présidentielle 2027</span>
        <span class="election-date">${escapeHtml(formatIsoDateFr(item.date))}</span>
      </div>
      ${item.url
        ? `<a class="news-summary news-link" href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(item.summary)}<span class="link-mark">↗</span></a>`
        : `<p class="news-summary">${escapeHtml(item.summary)}</p>`
      }
      <div class="sources">(${(item.sources || []).map(escapeHtml).join(' • ')})</div>
    </article>
  `).join('');

  if (items.length > shown.length) {
    list.insertAdjacentHTML('beforeend', `<button class="more-button" id="electionMoreButton">Suite (${items.length - shown.length})</button>`);
    $('#electionMoreButton').onclick = () => {
      state.electionVisibleCount += 10;
      renderElectionNews();
    };
  }
}

function renderCandidateProgram() {
  const data = state.electionData;
  const candidate = (data?.candidates || []).find(c => c.id === state.candidateId);
  if (!candidate) return;

  const fallback = data.program_fallback || 'Aucune proposition suffisamment documentée à ce stade.';
  $('#programGrid').innerHTML = (data.sectors || []).map(sector => `
    <article class="program-card">
      <h4>${escapeHtml(sector)}</h4>
      <p class="${candidate.program?.[sector] ? '' : 'program-missing'}">${escapeHtml(candidate.program?.[sector] || fallback)}</p>
    </article>
  `).join('');

  $('#candidateSources').innerHTML = candidate.sources?.length
    ? `<strong>Sources de synthèse :</strong> ${candidate.sources.map(escapeHtml).join(' • ')}`
    : '';
}

function renderElectionPage() {
  renderElectionPeriods();
  renderElectionHistory();
  renderElectionNews();
  renderCandidateProgram();
  renderCandidateTab();
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
    const hourlyFiles = Array.from({ length: 24 }, (_, hour) =>
      'data/hourly-' + String(hour).padStart(2, '0') + '.json'
    );
    const legacyHourlyFiles = Array.from({ length: 24 }, (_, hour) =>
      'data/hourly-' + hour + '.json'
    );
    const urls = [
      'data/news.json',
      'data/hourly.json',
      'data/hourly-archive-2026-09-21.json',
      ...hourlyFiles,
      ...legacyHourlyFiles,
      'data/hourly-latest.json'
    ];

    const [results, electionRes] = await Promise.all([
      Promise.all(urls.map(url => fetch(url + '?v=' + stamp, { cache: 'no-store' }).catch(() => null))),
      fetch('data/election.json?v=' + stamp, { cache: 'no-store' }).catch(() => null)
    ]);
    if (electionRes && electionRes.ok) {
      state.electionData = await electionRes.json();
    }

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

$('#candidatePickerButton').onclick = () => {
  const dropdown = $('#candidateDropdown');
  dropdown.hidden = !dropdown.hidden;
  $('#candidatePickerButton').setAttribute('aria-expanded', String(!dropdown.hidden));
  if (!dropdown.hidden) $('#candidateSearch').focus();
};

$('#candidateSearch').addEventListener('input', e => renderCandidateList(e.target.value));
$('#partyPickerButton').onclick = () => { const d=$('#partyDropdown'); d.hidden=!d.hidden; $('#partyPickerButton').setAttribute('aria-expanded',String(!d.hidden)); if(!d.hidden) $('#partySearch').focus(); };
$('#partySearch').addEventListener('input', e => renderPartyList(e.target.value));

if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('sw.js');
}

loadData();
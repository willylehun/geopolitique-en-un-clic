"""Sources de fond : provenance, surveillance et rotation indépendante des actualités."""
import hashlib
import json
import re
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser

MAX_BYTES = 8 * 1024 * 1024


class DocumentText(HTMLParser):
    """Ignore scripts, navigation et formulaires ; garde les liens de documents."""
    IGNORED = {'script', 'style', 'nav', 'header', 'footer', 'form', 'noscript', 'svg'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.parts = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        ignored = (self.stack and self.stack[-1][1]) or tag in self.IGNORED
        if tag not in {'img', 'br', 'hr', 'input', 'meta', 'link', 'source', 'wbr', 'area', 'embed', 'param', 'col', 'base'}:
            self.stack.append((tag, ignored))
        if not ignored:
            if tag == 'a' and attrs.get('href'):
                self.links.append(attrs['href'])
            # Certains programmes sont publiés entièrement en images.
            if tag == 'img' and attrs.get('src'):
                self.parts.append('image:' + attrs['src'])

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break

    def handle_data(self, text):
        if not self.stack or not self.stack[-1][1]:
            self.parts.append(text)


def fingerprint(raw, content_type, url):
    if raw.startswith(b'%PDF-'):
        return hashlib.sha256(raw).hexdigest(), []
    if 'html' not in content_type:
        raise ValueError('Format de source non reconnu')
    parser = DocumentText()
    parser.feed(raw.decode('utf-8', errors='replace'))
    body = re.sub(r'\s+', ' ', ' '.join(parser.parts)).strip()
    if len(body) < 100 or any(s in body.lower() for s in ('just a moment', 'verify you are human', 'checking your browser', 'access denied')):
        raise ValueError('Page vide ou protection empêchant la lecture')
    links = sorted({urllib.parse.urljoin(url, link) for link in parser.links
                    if re.search(r'programme|program|projet|livret|\.pdf(?:\?|$)', link, re.I)})
    # Un nouveau PDF lié depuis une page doit déclencher une alerte même
    # lorsque son libellé est identique à l'ancien document.
    payload = body + '\n' + '\n'.join(links)
    return hashlib.sha256(payload.encode()).hexdigest(), links[:40]


def fetch_document(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'GeopolitiqueElectionWatch/1.0', 'Accept': 'text/html,application/pdf'})
    with urllib.request.urlopen(request, timeout=12) as response:
        raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError('Document supérieur à 8 Mo')
        return fingerprint(raw, response.headers.get('Content-Type', ''), response.geturl())


def apply_reviews(data, reviewed):
    candidates = data.setdefault('candidates', [])
    ids = {c['id'] for c in candidates}
    for cid, record in reviewed.items():
        if cid not in ids and record.get('candidate'):
            candidates.append(dict(record['candidate'], program={}, sources=[]))
            ids.add(cid)
    for candidate in candidates:
        record = reviewed.get(candidate['id'])
        if not record:
            continue
        candidate['program_review'] = {k: record.get(k, '') for k in ('reviewed_at', 'review_note', 'document_kind')}
        candidate['program_documents'] = record.get('source_documents', [])
        for source in record.get('sources', []):
            if source not in candidate.setdefault('sources', []):
                candidate['sources'].append(source)
        for topic, proposal in record.get('program', {}).items():
            current = candidate.setdefault('program', {}).get(topic, '')
            owned = candidate.get('program_review_values', {}).get(topic)
            if not current or current.startswith('Aucune proposition') or current == owned or current == proposal:
                candidate['program'][topic] = proposal
                candidate.setdefault('program_review_values', {})[topic] = proposal
                candidate.setdefault('program_sources', {})[topic] = record.get('program_sources', {}).get(topic, record.get('sources', []))


def monitor_sources(data, state, reviewed, now, fetch=fetch_document):
    """Même quota par candidat ; les échecs ne deviennent jamais des succès."""
    watched = state.setdefault('program_source_checks', {})
    active = [c for c in data.get('candidates', []) if c.get('status') not in ('withdrawn', 'removed')]
    jobs = []
    for candidate in active:
        docs = reviewed.get(candidate['id'], {}).get('source_documents', [])
        # Deux sources par passage et candidat, rotation des sources longues.
        offset = int(state.get('program_source_cursor', {}).get(candidate['id'], 0))
        chosen = [docs[(offset + n) % len(docs)] for n in range(min(2, len(docs)))] if docs else []
        for doc in chosen:
            jobs.append((candidate, doc))
        state.setdefault('program_source_cursor', {})[candidate['id']] = (offset + len(chosen)) % max(1, len(docs))

    def check(job):
        candidate, doc = job
        try:
            digest, links = fetch(doc['url'])
            return candidate, doc, digest, links, None
        except Exception as exc:
            return candidate, doc, None, [], str(exc)[:200]

    with ThreadPoolExecutor(max_workers=6) as pool:
        for candidate, doc, digest, links, error in pool.map(check, jobs):
            source_key = candidate['id'] + '|' + doc['url']
            previous = watched.get(source_key, {})
            result = dict(previous, attempted_at=now, url=doc['url'], label=doc.get('label', 'Source'))
            if error:
                result.update(status='error', error=error)
            else:
                changed = bool(previous.get('digest') and previous['digest'] != digest)
                result.update(status='ok', digest=digest, successful_at=now, document_links=links)
                result.pop('error', None)
                if changed:
                    result['changed_at'] = now
                    candidate.setdefault('program_source_changes', []).insert(0, {
                        'date': now[:10], 'detected_at': now, 'url': doc['url'],
                        'label': doc.get('label', 'Source'),
                        'summary': 'Le contenu ou les documents liés de cette source ont changé. Les propositions modifiées restent à vérifier.'})
                    candidate['program_source_changes'] = candidate['program_source_changes'][:12]
            watched[source_key] = result
    for candidate in active:
        docs = reviewed.get(candidate['id'], {}).get('source_documents', [])
        candidate['program_watch'] = [watched.get(candidate['id'] + '|' + d['url'], {
            'url': d['url'], 'label': d.get('label', 'Source'), 'status': 'pending'}) for d in docs]
    state['last_program_candidate_count'] = len(active)
    state['last_program_source_attempt_count'] = len(jobs)
    state['last_program_source_success_count'] = sum(1 for c, d in jobs if watched[c['id']+'|'+d['url']]['status']=='ok')


def deep_query(name):
    return f'"{name}" "2027" (programme OR projet OR proposition OR entretien OR livre OR controverse OR enquête OR condamnation OR démenti) when:365d'


def add_discoveries(candidate, rows, matches, trusted, now):
    discoveries = candidate.setdefault('background_discoveries', [])
    known = {r.get('url') for r in discoveries}
    for row in rows:
        # Un titre trouvé est une piste, jamais une proposition ou accusation validée.
        if row.get('url') in known or not matches(row) or not trusted(row):
            continue
        discoveries.append({'title': row['title'], 'url': row['url'], 'source': row.get('source', ''),
                            'date': row['date'].date().isoformat(), 'found_at': now, 'status': 'to_review'})
        known.add(row['url'])
    discoveries.sort(key=lambda r: r.get('date', ''), reverse=True)
    candidate['background_discoveries'] = discoveries[:15]
    candidate['background_searched_at'] = now

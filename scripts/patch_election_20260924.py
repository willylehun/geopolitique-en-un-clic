import json
from pathlib import Path

path = Path('data/election.json')
data = json.loads(path.read_text(encoding='utf-8'))
now = '2026-09-24T10:33:00+02:00'

news = data.setdefault('news', [])
by_id = {item.get('id'): item for item in news}

updates = [
    {
        'id': '2026-09-23-retailleau-retraites',
        'date': '2026-09-23',
        'candidate_ids': ['bruno-retailleau'],
        'party_names': ['Les Républicains'],
        'summary': 'Bruno Retailleau a précisé son projet de réforme des retraites : un âge minimal de départ à 63 ans avec une décote de 7 % par année manquante, un taux plein automatique à 65 ans et l’introduction d’une part de capitalisation pour les jeunes.',
        'sources': ['LCP — 23 septembre 2026'],
        'url': 'https://lcp.fr/actualites/retraites-bruno-retailleau-veut-un-age-minimal-de-depart-a-63-ans-et-un-taux-plein-a-65'
    },
    {
        'id': '2026-09-24-philippe-attal-duel',
        'date': '2026-09-24',
        'candidate_ids': ['edouard-philippe', 'gabriel-attal'],
        'party_names': ['Horizons', 'Renaissance'],
        'summary': 'La rivalité entre Édouard Philippe et Gabriel Attal s’est durcie dans la campagne du bloc central. Les deux candidats maintiennent néanmoins l’objectif d’un rassemblement autour d’une candidature unique avant le premier tour, tandis qu’une étude de la Fondation Jean-Jaurès souligne que leurs électorats ne se reporteraient que partiellement de l’un vers l’autre.',
        'sources': ['Le Monde — 24 septembre 2026'],
        'url': 'https://www.lemonde.fr/politique/article/2026/09/24/presidentielle-2027-derriere-le-duel-de-plus-en-plus-acerbe-entre-edouard-philippe-et-gabriel-attal-des-electorats-loin-d-etre-fongibles_6781447_823448.html'
    }
]

for item in updates:
    if item['id'] not in by_id:
        news.append(item)

candidates = {c.get('id'): c for c in data.get('candidates', [])}
retailleau = candidates.get('bruno-retailleau')
if retailleau:
    retailleau.setdefault('program', {})['Travail & retraites'] = 'Propose un âge minimal de départ à la retraite à 63 ans, assorti d’une décote de 7 % par année manquante, un taux plein automatique à 65 ans et l’introduction d’une part de capitalisation pour les jeunes.'
    if 'LCP — retraites, 23 septembre 2026' not in retailleau.setdefault('sources', []):
        retailleau['sources'].append('LCP — retraites, 23 septembre 2026')
    retailleau['last_checked_at'] = now

for cid in ('edouard-philippe', 'gabriel-attal'):
    if cid in candidates:
        candidates[cid]['last_checked_at'] = now

parties = {p.get('name'): p for p in data.get('parties', [])}
for pname, news_ids in {
    'Les Républicains': ['2026-09-23-retailleau-retraites'],
    'Horizons': ['2026-09-24-philippe-attal-duel'],
    'Renaissance': ['2026-09-24-philippe-attal-duel'],
}.items():
    party = parties.get(pname)
    if not party:
        continue
    party['last_checked_at'] = now
    arr = party.setdefault('news', [])
    for nid in news_ids:
        if nid not in arr:
            arr.append(nid)

lr = parties.get('Les Républicains')
if lr:
    lr.setdefault('program', {})['Travail & retraites'] = 'Bruno Retailleau, candidat LR, propose un âge minimal de départ à 63 ans, un taux plein automatique à 65 ans et une part de capitalisation pour les jeunes.'
    if 'LCP — retraites, 23 septembre 2026' not in lr.setdefault('sources', []):
        lr['sources'].append('LCP — retraites, 23 septembre 2026')

data['generated_at'] = now
path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
json.loads(path.read_text(encoding='utf-8'))
print('election.json valide; actualités:', len(data.get('news', [])))

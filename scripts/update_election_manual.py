import json
from pathlib import Path

PATH = Path("data/election.json")
NOW = "2026-09-24T09:12:00+02:00"
NEWS_ID = "2026-09-23-primary-first-debate"
SOURCE_MONDE = "Le Monde — premier débat de la primaire à gauche, 24 septembre 2026"
SOURCE_SENAT = "Public Sénat — bilan du premier débat de la primaire à gauche, 24 septembre 2026"
URL = "https://www.lemonde.fr/politique/article/2026/09/24/primaire-a-gauche-la-situation-a-gaza-et-l-alliance-avec-lfi-electrisent-le-premier-debat-televise_6781332_823448.html"

with PATH.open(encoding="utf-8") as f:
    data = json.load(f)

updates = {
    "raphael-glucksmann": {
        "Économie": "Lors du premier débat de la primaire, il a défendu une taxe sur les gros héritages destinée notamment à financer une baisse de la CSG et a proposé un statut pour les familles monoparentales.",
        "Europe & international": "Il maintient une ligne de soutien à l’Ukraine et, sur Gaza, parle de crimes contre l’humanité et de crimes de guerre sans employer le terme de génocide.",
        "Institutions & démocratie": "Il exclut une alliance nationale avec La France insoumise aux élections législatives et défend une offre sociale-démocrate autonome."
    },
    "olivier-faure": {
        "Économie": "Lors du premier débat de la primaire, il a défendu l’indexation des salaires sur l’inflation et une sécurité sociale alimentaire.",
        "Travail & retraites": "Il défend l’abrogation de la réforme des retraites portant l’âge légal à 64 ans.",
        "Europe & international": "Il soutient l’Ukraine et emploie le terme de génocide pour qualifier la situation à Gaza.",
        "Institutions & démocratie": "Il défend le maintien de convergences parlementaires avec les autres forces de gauche, y compris LFI, sans présenter cela comme une alliance présidentielle."
    },
    "jerome-guedj": {
        "Santé": "Il défend une « grande sécu » consistant à intégrer à la Sécurité sociale la couverture aujourd’hui assurée par les complémentaires santé.",
        "Institutions & démocratie": "Il exclut une nouvelle alliance nationale avec La France insoumise et présente cette rupture comme un axe majeur de sa candidature à la primaire."
    },
    "segolene-royal": {
        "Économie": "Lors du premier débat de la primaire, elle a proposé le rétablissement d’un impôt de solidarité sur la fortune financière et une réduction du train de vie de l’État avant de nouveaux prélèvements.",
        "Europe & international": "Sur l’Ukraine, elle met en avant la négociation et la médiation pour rechercher une paix durable ; sur Gaza, elle emploie le terme de génocide."
    },
    "emmanuel-maurel": {
        "Économie": "Lors du premier débat de la primaire, il a défendu l’indexation des salaires sur l’inflation et contesté l’idée d’une annulation générale de la dette.",
        "Institutions & démocratie": "Il refuse de structurer toute la stratégie de la gauche uniquement autour de son rapport à LFI et met en avant un projet fondé sur le partage des pouvoirs, des savoirs et des richesses."
    }
}

checked_ids = set(updates)
for candidate in data.get("candidates", []):
    cid = candidate.get("id")
    if cid not in updates:
        continue
    candidate.setdefault("program", {}).update(updates[cid])
    sources = candidate.setdefault("sources", [])
    for source in (SOURCE_MONDE, SOURCE_SENAT):
        if source not in sources:
            sources.append(source)
    candidate["last_checked_at"] = NOW

news = data.setdefault("news", [])
item = {
    "id": NEWS_ID,
    "date": "2026-09-23",
    "candidate_ids": ["raphael-glucksmann", "emmanuel-maurel", "segolene-royal", "olivier-faure", "jerome-guedj"],
    "party_names": ["Place publique", "Gauche républicaine et socialiste", "Parti socialiste"],
    "summary": "Le premier débat de la primaire social-démocrate a opposé Raphaël Glucksmann, Emmanuel Maurel, Ségolène Royal, Olivier Faure et Jérôme Guedj. Les échanges ont notamment porté sur les salaires, la protection sociale, la dette, l’Ukraine, Gaza et la stratégie d’alliance avec La France insoumise.",
    "sources": [SOURCE_MONDE, SOURCE_SENAT],
    "url": URL
}
existing = next((x for x in news if x.get("id") == NEWS_ID), None)
if existing:
    existing.update(item)
else:
    news.append(item)

for party in data.get("parties", []):
    ids = set(party.get("candidate_ids", []))
    if not (ids & checked_ids):
        continue
    sources = party.setdefault("sources", [])
    for source in (SOURCE_MONDE, SOURCE_SENAT):
        if source not in sources:
            sources.append(source)
    refs = party.setdefault("news", [])
    if NEWS_ID not in refs:
        refs.append(NEWS_ID)
    party["last_checked_at"] = NOW

data["generated_at"] = NOW

with PATH.open("w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
    f.write("\n")

# Validation explicite après écriture.
with PATH.open(encoding="utf-8") as f:
    json.load(f)

import json
from pathlib import Path

PATH = Path("data/election.json")
data = json.loads(PATH.read_text(encoding="utf-8"))
now = "2026-09-24T14:12:57+02:00"
fallback = data.get("program_fallback", "Aucune proposition 2027 suffisamment détaillée n’est encore documentée dans les sources suivies.")
sectors = data.get("sectors", [])

candidate_id = "olivier-becht"
if not any(c.get("id") == candidate_id for c in data.get("candidates", [])):
    data.setdefault("candidates", []).append({
        "id": candidate_id,
        "name": "Olivier Becht",
        "party": "Sans étiquette",
        "status": "declared",
        "status_label": "Candidature déclarée",
        "program": {sector: fallback for sector in sectors},
        "sources": ["Le Monde — candidature annoncée le 24 septembre 2026", "Paris Match — entretien annonçant la candidature, 24 septembre 2026"],
        "last_checked_at": now,
        "bio": "Député de la 5e circonscription du Haut-Rhin depuis 2017, ancien maire de Rixheim de 2008 à 2017 et ancien ministre délégué chargé du commerce extérieur, de l’attractivité et des Français de l’étranger entre 2022 et 2024. Ancien président du groupe Agir ensemble à l’Assemblée nationale, il se présente sans étiquette partisane et se revendique de l’« extrême centre ».",
        "controversies": []
    })

news_id = "2026-09-24-becht-candidature"
if not any(n.get("id") == news_id for n in data.get("news", [])):
    data.setdefault("news", []).append({
        "id": news_id,
        "date": "2026-09-24",
        "candidate_ids": [candidate_id],
        "party_names": [],
        "summary": "Olivier Becht, député du Haut-Rhin et ancien ministre du commerce extérieur, a annoncé sa candidature à l’élection présidentielle de 2027. Il affirme se présenter sans camp politique et se revendique de l’« extrême centre ».",
        "sources": ["Le Monde — 24 septembre 2026", "Paris Match — 24 septembre 2026"],
        "url": "https://www.lemonde.fr/politique/article/2026/09/24/l-ancien-ministre-olivier-becht-candidat-a-l-election-presidentielle_6781497_823448.html"
    })

# Si la catégorie Sans étiquette est déjà suivie comme pseudo-parti, on y rattache le candidat.
for party in data.get("parties", []):
    if party.get("name") == "Sans étiquette":
        ids = party.setdefault("candidate_ids", [])
        if candidate_id not in ids:
            ids.append(candidate_id)
        party["last_checked_at"] = now
        news = party.setdefault("news", [])
        if news_id not in news:
            news.append(news_id)
        break

data["generated_at"] = now
PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

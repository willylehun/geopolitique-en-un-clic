#!/usr/bin/env python3
"""Construit l'API statique consommée par l'application à partir du magasin canonique."""
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/"data"/"news.json"
COVERAGE=ROOT/"data"/"country-coverage.json"
OUT=ROOT/"api"/"news.json"
STATUS=ROOT/"api"/"status.json"
INDEX=ROOT/"api"/"index.json"
LATEST=ROOT/"api"/"latest.json"
DAYS=ROOT/"api"/"days"

def main():
    data=json.loads(SRC.read_text(encoding="utf-8"))
    coverage=json.loads(COVERAGE.read_text(encoding="utf-8")) if COVERAGE.exists() else {}
    items=data.get("items",[])
    # Un seul événement canonique; l'API expose les mêmes données sans recopier les archives horaires.
    payload={
      "api_version":1,
      "generated_at":data.get("generated_at"),
      "timezone":"Europe/Paris",
      "buckets":data.get("buckets",{}),
      "coverage":data.get("coverage",{}),
      "items":items,
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(payload,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    status={
      "ok":True,
      "generated_at":datetime.now(ZoneInfo("Europe/Paris")).isoformat(),
      "items":len(items),
      "covered_countries":coverage.get("covered_count",0),
      "missing_countries":coverage.get("missing_count",195),
      "coverage_date":coverage.get("date"),
    }
    STATUS.write_text(json.dumps(status,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

    # Export incrémental léger: le mobile charge d'abord la journée courante.
    today=datetime.now(ZoneInfo("Europe/Paris")).date()
    def item_day(item):
        try: return datetime.fromisoformat(item.get("published_at","")).astimezone(ZoneInfo("Europe/Paris")).date()
        except Exception: return None
    latest=[item for item in items if item_day(item)==today]
    LATEST.write_text(json.dumps({"api_version":1,"generated_at":status["generated_at"],"date":today.isoformat(),"items":latest},ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    DAYS.mkdir(parents=True,exist_ok=True)
    by_day={}
    for item in items:
        d=item_day(item)
        if d: by_day.setdefault(d.isoformat(),[]).append(item)
    # Ne réécrire que les journées dont le contenu diffère.
    for day,day_items in by_day.items():
        path=DAYS/f"{day}.json"
        raw=json.dumps({"api_version":1,"date":day,"items":day_items},ensure_ascii=False,separators=(",",":"))+"\n"
        if not path.exists() or path.read_text(encoding="utf-8")!=raw:
            path.write_text(raw,encoding="utf-8")

    # Index léger pour les clients: l'application peut cibler un pays/une région
    # sans retraiter l'intégralité du magasin canonique.
    countries={}; regions={}
    for idx,item in enumerate(items):
        for country in item.get("countries",[]) or []:
            countries.setdefault(country,[]).append(idx)
        for region in item.get("regions",[]) or []:
            regions.setdefault(region,[]).append(idx)
    index={"api_version":1,"generated_at":status["generated_at"],"countries":countries,"regions":regions}
    INDEX.write_text(json.dumps(index,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    print("api built",status,"country indexes",len(countries),"region indexes",len(regions))

if __name__=="__main__":
    main()

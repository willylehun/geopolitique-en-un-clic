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

#!/usr/bin/env python3
import json, os, re, time, urllib.error, urllib.parse, urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"/"election.json"
STATE=ROOT/"data"/"election-monitor-state.json"
PARIS=ZoneInfo("Europe/Paris")
UTC=ZoneInfo("UTC")
BATCH=max(1,int(os.getenv("ELECTION_BATCH_SIZE","6")))
RETENTION_DAYS=7

# Sources françaises reconnues. Les sources officielles sont conservées lorsqu'elles
# apparaissent dans les résultats, mais aucune controverse n'est créée automatiquement.
TRUSTED=("Le Monde","Franceinfo","France Info","France Inter","France 24","AFP","Public Sénat",
         "LCP","Le Figaro","Libération","Les Echos","La Croix","Ouest-France","20 Minutes",
         "BFMTV","RMC","TF1 INFO","France Télévisions","Mediapart","Le Point","L'Express",
         "Le Parisien","HuffPost","Politico","POLITICO")
OFFICIAL_HINTS=("assemblee-nationale.fr","senat.fr","vie-publique.fr","conseil-constitutionnel.fr",
                "interieur.gouv.fr","gouvernement.fr")

def norm(s):
    return re.sub(r"\s+"," ",(s or "").strip())

def key(s):
    return re.sub(r"[^a-z0-9à-ÿ]+"," ",(s or "").lower()).strip()[:180]

def trusted(source,url=""):
    s=(source or "").lower()
    return any(x.lower() in s for x in TRUSTED) or any(x in (url or "").lower() for x in OFFICIAL_HINTS)

def google_exact(name):
    q=f'"{name}" when:30d'
    url="https://news.google.com/rss/search?"+urllib.parse.urlencode({"q":q,"hl":"fr","gl":"FR","ceid":"FR:fr"})
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 GeoClicElection/3.0"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req,timeout=25) as r: root=ET.fromstring(r.read())
            break
        except urllib.error.HTTPError as e:
            if e.code not in (429,503): raise
            time.sleep(3*(attempt+1))
    else: return []
    out=[]
    for item in root.findall(".//item"):
        title=norm(item.findtext("title"))
        link=norm(item.findtext("link"))
        src_el=item.find("source")
        source=norm(src_el.text if src_el is not None else "")
        try: dt=parsedate_to_datetime(item.findtext("pubDate"))
        except Exception: continue
        if dt.tzinfo is None: dt=dt.replace(tzinfo=UTC)
        local=dt.astimezone(PARIS)
        if not title or not trusted(source,link): continue
        # Le nom exact doit apparaître dans le titre : évite les résultats de recherche seulement connexes.
        if name.casefold() not in title.casefold(): continue
        out.append({"title":title,"source":source or "Source officielle","url":link,"date":local})
    return out

def load_state():
    try: return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception: return {"cursor":0,"runs":0,"checked":{}}

def save_state(state,now):
    state["runs"]=int(state.get("runs",0))+1
    state["last_run_at"]=now.isoformat()
    STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def news_id(name,dt,title):
    slug=re.sub(r"[^a-z0-9]+","-",name.lower()).strip("-")[:45]
    return f"{dt.date().isoformat()}-{slug}-{abs(hash(key(title)))%100000000:08d}"

with DATA.open(encoding="utf-8") as f: data=json.load(f)
now=datetime.now(PARIS)
cut30=now-timedelta(days=30)
cut7=now-timedelta(days=RETENTION_DAYS)

entities=[]
for c in data.get("candidates",[]):
    if c.get("status") not in ("withdrawn","removed"):
        entities.append(("candidate",c.get("id"),c.get("name")))
for p in data.get("parties",[]):
    entities.append(("party",p.get("name"),p.get("name")))
entities=[x for x in entities if x[2]]

state=load_state()
cursor=int(state.get("cursor",0))%max(1,len(entities))
batch=[entities[(cursor+i)%len(entities)] for i in range(min(BATCH,len(entities)))]
state["cursor"]=(cursor+len(batch))%max(1,len(entities))
checked=state.setdefault("checked",{})

news=data.setdefault("news",[])
existing={(n.get("date"),key(n.get("summary") or n.get("title"))):n for n in news}
cmap={c.get("id"):c for c in data.get("candidates",[])}
pmap={p.get("name"):p for p in data.get("parties",[])}

for kind,eid,name in batch:
    try: rows=google_exact(name)
    except Exception as e:
        print(f"{name}: {e}")
        continue
    checked[f"{kind}:{eid}"]=now.isoformat()
    if kind=="candidate" and eid in cmap: cmap[eid]["last_checked_at"]=now.isoformat()
    if kind=="party" and eid in pmap: pmap[eid]["last_checked_at"]=now.isoformat()
    for row in rows:
        if row["date"]<cut30: continue
        k=(row["date"].date().isoformat(),key(row["title"]))
        item=existing.get(k)
        if not item:
            item={
              "id":news_id(name,row["date"],row["title"]),
              "date":row["date"].date().isoformat(),
              "candidate_ids":[],
              "party_names":[],
              "summary":row["title"],
              "sources":[row["source"]],
              "url":row["url"]
            }
            news.append(item); existing[k]=item
        if kind=="candidate":
            if eid not in item.setdefault("candidate_ids",[]): item["candidate_ids"].append(eid)
            party=cmap.get(eid,{}).get("party")
            if party and party not in item.setdefault("party_names",[]): item["party_names"].append(party)
        else:
            if eid not in item.setdefault("party_names",[]): item["party_names"].append(eid)
        if row["source"] not in item.setdefault("sources",[]): item["sources"].append(row["source"])

# Règle de retrait : les candidats retirés restent visibles sept jours lorsqu'une date de retrait existe.
kept=[]
for c in data.get("candidates",[]):
    if c.get("status") not in ("withdrawn","removed"):
        kept.append(c); continue
    raw=c.get("withdrawn_at") or c.get("withdrawal_date")
    try: wd=datetime.fromisoformat(raw).astimezone(PARIS) if raw else None
    except Exception: wd=None
    if not wd or wd>=cut7: kept.append(c)
data["candidates"]=kept

# Les actualités restent disponibles sur 30 jours ; Jour/7 jours/30 jours sont filtrés par l'application.
news.sort(key=lambda n:(n.get("date",""),n.get("id","")),reverse=True)
data["generated_at"]=now.isoformat()
with DATA.open("w",encoding="utf-8") as f:
    json.dump(data,f,ensure_ascii=False,indent=2); f.write("\n")
# Validation explicite avant toute publication.
with DATA.open(encoding="utf-8") as f: json.load(f)
save_state(state,now)

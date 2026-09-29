#!/usr/bin/env python3
import html as html_lib
import json, os, re, time, unicodedata, urllib.error, urllib.parse, urllib.request
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
BATCH=max(1,int(os.getenv("ELECTION_BATCH_SIZE","12")))

TRUSTED=(
 "Le Monde","Franceinfo","France Info","France Inter","France 24","AFP","Reuters","Associated Press","AP",
 "Public Sénat","LCP","Le Figaro","Libération","Les Echos","La Croix","Ouest-France","20 Minutes",
 "BFMTV","RMC","TF1 INFO","France Télévisions","Mediapart","Le Point","L'Express","Le Parisien",
 "HuffPost","Politico","POLITICO","Euronews"
)
OFFICIAL_HINTS=(
 "assemblee-nationale.fr","senat.fr","vie-publique.fr","conseil-constitutionnel.fr",
 "interieur.gouv.fr","gouvernement.fr","horizonsleparti.fr"
)

POLITICAL_HINTS=(
 "présidentielle","presidentielle","candidat","candidature","campagne","programme","proposition","propose",
 "retraite","immigration","écologie","ecologie","économie","economie","fiscal","impôt","impot","emploi",
 "travail","santé","sante","éducation","education","école","ecole","sécurité","securite","justice",
 "diplomatie","ukraine","europe","défense","defense","agriculture","climat","intelligence artificielle",
 "ia ","parti","élection","election","primaire","sondage","ralliement","soutien","retrait","500 signatures",
 "polémique","polemique","controverse","antisémit","antisemit","racis","plainte","enquête","enquete",
 "condamn","procès","proces","mise en examen","diffamation","assemblée","assemblee","sénat","senat",
 "gouvernement","député","depute","ministre"
)
PROGRAM_HINTS=(
 "programme","proposition","propose","projet","retraite","immigration","écologie","ecologie","économie",
 "economie","fiscal","emploi","travail","santé","sante","éducation","education","sécurité","securite",
 "justice","défense","defense","agriculture","climat","intelligence artificielle"
)
CONTROVERSY_HINTS=(
 "controverse","polémique","polemique","antisémit","antisemit","racis","plainte","enquête","enquete",
 "condamn","procès","proces","mise en examen","diffamation","accus","perquisition"
)
CANDIDACY_HINTS=("candidature","candidat","retrait","retire","primaire","500 signatures","ralliement","soutien")

PARTY_ALIASES={
 "Rassemblement national":["Rassemblement national","RN","Jordan Bardella"],
 "Les Républicains":["Les Républicains","LR"],
 "La France insoumise":["La France insoumise","LFI"],
 "Renaissance":["Renaissance"],
 "Horizons":["Horizons"],
 "Place publique":["Place publique"],
 "Reconquête !":["Reconquête","Reconquete"],
 "Les Écologistes":["Les Écologistes","Les Ecologistes"],
}
GENERIC_PARTIES={"Horizons","Renaissance","La Convention","Debout !","Nouvelle Énergie"}

def norm(s):
    return re.sub(r"\s+"," ",(s or "").strip())

def fold(s):
    return "".join(ch for ch in unicodedata.normalize("NFD",(s or "").casefold()) if unicodedata.category(ch)!="Mn")

def key(s):
    return re.sub(r"[^a-z0-9à-ÿ]+"," ",(s or "").lower()).strip()[:180]

def has_phrase(text, phrase):
    t=fold(text); p=fold(phrase).strip()
    if not p: return False
    if len(p)<=4 and p.isalpha():
        return bool(re.search(r"(?<![a-z0-9])"+re.escape(p)+r"(?![a-z0-9])",t))
    return p in t

def trusted(source,url=""):
    s=(source or "").lower()
    return any(x.lower() in s for x in TRUSTED) or any(x in (url or "").lower() for x in OFFICIAL_HINTS)

def strip_html(raw):
    text=html_lib.unescape(raw or "")
    text=re.sub(r"(?is)<[^>]+>"," ",text)
    return norm(text)

def clean_title(title,source=""):
    out=norm(title)
    if source:
        out=re.sub(r"\s*[-–—|]\s*"+re.escape(source)+r"\s*$","",out,flags=re.I)
    return out.strip(" -–—|")

def election_context(text):
    low=fold(text)
    return any(fold(x) in low for x in POLITICAL_HINTS)

def topic_for(text):
    low=fold(text)
    if any(fold(x) in low for x in CONTROVERSY_HINTS): return "controverse"
    if any(fold(x) in low for x in PROGRAM_HINTS): return "programme"
    if any(fold(x) in low for x in CANDIDACY_HINTS): return "candidature"
    return "actualité"

def summary_from(title,description,source):
    title=clean_title(title,source)
    desc=strip_html(description)
    # Les descriptions Google répètent souvent seulement le titre et le média.
    title_words=set(re.findall(r"[a-zà-ÿ0-9]+",fold(title)))
    desc_words=set(re.findall(r"[a-zà-ÿ0-9]+",fold(desc)))
    extra=len(desc_words-title_words)
    if len(desc)>=90 and extra>=8:
        if fold(title) in fold(desc):
            return desc[:700]
        return (title+". "+desc)[:700]
    return title

def google_search(query):
    url="https://news.google.com/rss/search?"+urllib.parse.urlencode({"q":query,"hl":"fr","gl":"FR","ceid":"FR:fr"})
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 GeoClicElection/4.0"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req,timeout=25) as r:
                root=ET.fromstring(r.read())
            break
        except urllib.error.HTTPError as e:
            if e.code not in (429,503): raise
            time.sleep(3*(attempt+1))
    else:
        return []
    out=[]
    for item in root.findall(".//item"):
        title=norm(item.findtext("title"))
        link=norm(item.findtext("link"))
        desc=norm(item.findtext("description"))
        src_el=item.find("source")
        source=norm(src_el.text if src_el is not None else "")
        try: dt=parsedate_to_datetime(item.findtext("pubDate"))
        except Exception: continue
        if dt.tzinfo is None: dt=dt.replace(tzinfo=UTC)
        local=dt.astimezone(PARIS)
        if not title or not trusted(source,link): continue
        out.append({"title":title,"description":desc,"source":source or "Source officielle","url":link,"date":local})
    return out

def google_exact(name):
    # Recherche détaillée : le nom seul + termes de campagne, sur 30 jours.
    q=f'"{name}" (présidentielle OR programme OR proposition OR candidat OR campagne OR politique OR retraite OR immigration OR écologie OR économie OR sécurité OR controverse OR plainte) when:30d'
    return google_search(q)

def load_state():
    try: return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception: return {"cursor":0,"runs":0,"checked":{}}

def save_state(state,now):
    state["runs"]=int(state.get("runs",0))+1
    state["last_run_at"]=now.isoformat()
    STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def news_id(name,dt,title):
    slug=re.sub(r"[^a-z0-9]+","-",fold(name)).strip("-")[:45]
    return f"{dt.date().isoformat()}-{slug}-{abs(hash(key(title)))%100000000:08d}"

def entity_aliases(kind,eid,name):
    if kind=="candidate":
        return [name]
    return PARTY_ALIASES.get(name,[name])

def row_matches_entity(row,kind,eid,name):
    title=row.get("title","")
    aliases=entity_aliases(kind,eid,name)
    if not any(has_phrase(title,a) for a in aliases):
        return False
    # Évite « Horizons » (livres, associations…), Renaissance artistique, etc.
    return election_context(title)

def row_is_useful(row):
    title=clean_title(row.get("title",""),row.get("source",""))
    if not election_context(title):
        return False
    noise=(
      "dernier hommage","people","livres pour","élargir ses horizons","val'horizons","val’horizons",
      "photos amateurs","festival","concert","football","match","horoscope"
    )
    low=fold(title)
    return not any(fold(x) in low for x in noise)

with DATA.open(encoding="utf-8") as f:
    data=json.load(f)
now=datetime.now(PARIS)
cut30=now-timedelta(days=30)
cut3=now-timedelta(days=3)

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
existing_by_url={(n.get("date"),n.get("url")):n for n in news if n.get("url")}
existing_by_key={(n.get("date"),key(n.get("summary") or n.get("title"))):n for n in news}
cmap={c.get("id"):c for c in data.get("candidates",[])}
pmap={p.get("name"):p for p in data.get("parties",[])}

def attach(row,matches):
    if row["date"]<cut30 or not row_is_useful(row): return
    title=clean_title(row["title"],row["source"])
    kdate=row["date"].date().isoformat()
    item=existing_by_url.get((kdate,row["url"])) or existing_by_key.get((kdate,key(title)))
    if not item:
        item={
          "id":news_id(matches[0][2] if matches else "presidentielle",row["date"],title),
          "date":kdate,
          "candidate_ids":[],
          "party_names":[],
          "summary":summary_from(row["title"],row.get("description",""),row["source"]),
          "sources":[row["source"]],
          "url":row["url"],
          "topic":topic_for(title)
        }
        news.append(item)
        existing_by_url[(kdate,row["url"])]=item
        existing_by_key[(kdate,key(title))]=item
    else:
        # Améliorer un ancien titre seul si la description apporte du fond.
        better=summary_from(row["title"],row.get("description",""),row["source"])
        if len(better)>len(item.get("summary","")):
            item["summary"]=better
        item.setdefault("topic",topic_for(title))
    for kind,eid,name in matches:
        if kind=="candidate":
            if eid not in item.setdefault("candidate_ids",[]): item["candidate_ids"].append(eid)
            party=cmap.get(eid,{}).get("party")
            if party and party not in item.setdefault("party_names",[]): item["party_names"].append(party)
        else:
            if eid not in item.setdefault("party_names",[]): item["party_names"].append(eid)
    if row["source"] not in item.setdefault("sources",[]): item["sources"].append(row["source"])

# Passe prioritaire : tous les candidats/partis sont recherchés par groupes sur les 3 derniers jours.
priority_rows=[]
chunk_size=7
for i in range(0,len(entities),chunk_size):
    chunk=entities[i:i+chunk_size]
    names=[]
    for kind,eid,name in chunk:
        # Les noms complets des candidats et les noms de partis sont quotés.
        names.append(f'"{name}"')
    q="("+ " OR ".join(names) +") (programme OR proposition OR retraite OR immigration OR écologie OR économie OR santé OR éducation OR sécurité OR justice OR controverse OR antisémitisme OR racisme OR plainte OR enquête OR candidature OR retrait OR primaire) when:3d"
    try:
        rows=google_search(q)
    except Exception as e:
        print("PRIORITE",e)
        continue
    for row in rows:
        if row["date"]<cut3: continue
        matches=[e for e in chunk if row_matches_entity(row,*e)]
        if matches: attach(row,matches)

# Trois filets thématiques transversaux : programme, controverses, candidatures.
campaign_queries=[
 '"présidentielle 2027" (programme OR proposition OR retraite OR immigration OR écologie OR économie OR santé OR éducation OR sécurité OR justice) when:3d',
 '"présidentielle 2027" (controverse OR antisémitisme OR racisme OR plainte OR enquête OR condamnation OR procès OR "mise en examen") when:3d',
 '"présidentielle 2027" (candidature OR retrait OR primaire OR "500 signatures" OR soutien OR ralliement) when:3d'
]
for q in campaign_queries:
    try: rows=google_search(q)
    except Exception as e:
        print("CAMPAGNE",e); continue
    for row in rows:
        if row["date"]<cut3: continue
        matches=[e for e in entities if row_matches_entity(row,*e)]
        if matches: attach(row,matches)

# Rotation détaillée pour le suivi de fond et last_checked_at.
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
        if row_matches_entity(row,kind,eid,name):
            attach(row,[(kind,eid,name)])

def news_words(text):
    stop={"présidentielle","presidentielle","2027","edouard","édouard","marine","jordan","le","la","les","de","des","du","un","une","et","en","sur","pour","avec"}
    return {w for w in re.findall(r"[a-zà-ÿ0-9]+",fold(text)) if len(w)>2 and w not in stop}

def same_news_event(a,b):
    if a.get("date")!=b.get("date") or a.get("topic")!=b.get("topic"):
        return False
    ac=set(a.get("candidate_ids",[]) or []); bc=set(b.get("candidate_ids",[]) or [])
    ap=set(a.get("party_names",[]) or []); bp=set(b.get("party_names",[]) or [])
    if not ((ac and bc and ac&bc) or (ap and bp and ap&bp)):
        return False
    wa=news_words(a.get("summary","")); wb=news_words(b.get("summary",""))
    if not wa or not wb: return False
    inter=len(wa&wb)
    return inter/max(1,min(len(wa),len(wb)))>=0.55

deduped=[]
for item in news:
    merged=False
    for kept in deduped:
        if same_news_event(kept,item):
            kept["sources"]=list(dict.fromkeys((kept.get("sources",[]) or [])+(item.get("sources",[]) or [])))
            urls=list(dict.fromkeys((kept.get("urls",[]) or [])+([kept.get("url")] if kept.get("url") else [])+([item.get("url")] if item.get("url") else [])))
            if urls: kept["urls"]=urls
            if len(item.get("summary",""))>len(kept.get("summary","")):
                kept["summary"]=item.get("summary","")
            kept["candidate_ids"]=list(dict.fromkeys((kept.get("candidate_ids",[]) or [])+(item.get("candidate_ids",[]) or [])))
            kept["party_names"]=list(dict.fromkeys((kept.get("party_names",[]) or [])+(item.get("party_names",[]) or [])))
            merged=True
            break
    if not merged:
        deduped.append(item)
news=deduped
data["news"]=news

# Archivage permanent : un candidat sorti reste conservé mais n'est plus recherché activement.
for c in data.get("candidates",[]):
    if c.get("status") in ("withdrawn","removed"):
        c["archived"]=True
        c.setdefault("withdrawal_reason","Motif à documenter")
    else:
        c["archived"]=False

news.sort(key=lambda n:(n.get("date",""),n.get("id","")),reverse=True)
data["generated_at"]=now.isoformat()
state["last_priority_entity_count"]=len(entities)
state["last_detailed_batch_count"]=len(batch)
with DATA.open("w",encoding="utf-8") as f:
    json.dump(data,f,ensure_ascii=False,indent=2); f.write("\n")
with DATA.open(encoding="utf-8") as f: json.load(f)
save_state(state,now)

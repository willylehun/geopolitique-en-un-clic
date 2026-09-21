#!/usr/bin/env python3
import json, os, re, sys, urllib.parse, urllib.request, xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timedelta, time as dtime
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"/"news.json"
PARIS=ZoneInfo("Europe/Paris")
UTC=ZoneInfo("UTC")
FR_MONTHS=["janvier","février","mars","avril","mai","juin","juillet","août","septembre","octobre","novembre","décembre"]

REGIONS={
 "International":"geopolitics OR diplomacy OR sanctions OR global economy OR world trade OR energy crisis OR security",
 "Europe":"Europe OR European Union OR EU OR Ukraine OR Russia OR France OR Germany OR Britain OR UK OR Italy OR Spain OR Poland",
 "Asie":"Asia OR China OR Japan OR India OR Korea OR Taiwan OR Iran OR Israel OR Gaza OR Saudi OR Yemen OR Indonesia",
 "Amérique du Nord":"United States OR USA OR Canada OR Mexico",
 "Amérique du Sud":"South America OR Latin America OR Brazil OR Brasil OR Argentina OR Colombia OR Chile OR Peru OR Venezuela OR Ecuador OR Bolivia OR Uruguay OR Paraguay OR Guyana OR Suriname OR Mercosur OR Amazon",
 "Afrique":"Africa OR Afrique OR Nigeria OR South Africa OR Kenya OR Sudan OR South Sudan OR Congo OR DRC OR Ethiopia OR Somalia OR Morocco OR Algeria OR Egypt OR Ghana OR Mali OR Burkina Faso OR Niger OR Chad OR Cameroon OR Senegal OR Ivory Coast OR Côte d’Ivoire OR Uganda OR Tanzania OR Rwanda OR Mozambique OR Angola OR Zambia OR Zimbabwe OR Libya OR Tunisia",
 "Océanie":"Oceania OR Australia OR New Zealand OR Pacific Islands OR Pacific Forum OR Fiji OR Papua New Guinea OR PNG OR Samoa OR Tonga OR Vanuatu OR Solomon Islands OR Kiribati OR Tuvalu OR Palau OR Micronesia OR Marshall Islands OR Nauru OR New Caledonia"
}
IMPACT_QUERY="war OR conflict OR sanctions OR election OR inflation OR oil OR gas OR trade OR tariffs OR security OR central bank OR diplomacy OR military OR government OR economy OR climate OR energy OR technology OR migration"

SOURCE_LABELS=[
 "Reuters","Associated Press","AP News","BBC","France 24","DW","Al Jazeera","Financial Times","The Economist",
 "The Guardian","Euronews","POLITICO","Le Monde","AFP","NHK","Japan Times","Nikkei Asia","CNA","Channel NewsAsia",
 "The Straits Times","Yonhap","The Korea Herald","The Hindu","The Indian Express","Dawn","The Jakarta Post","Kompas",
 "Tempo","Bangkok Post","Focus Taiwan","Taipei Times","Rappler","The New York Times","The Washington Post",
 "The Wall Street Journal","NPR","PBS NewsHour","ProPublica","Axios","Los Angeles Times","CBS News","CBC",
 "The Globe and Mail","CTV News","El Universal","Folha","O Globo","Estadão","Agência Brasil","La Nación","Clarín",
 "El Tiempo","El Espectador","El Comercio","La Tercera","News24","Daily Maverick","Mail & Guardian","SABC News",
 "Nation Africa","The EastAfrican","Premium Times","Channels Television","Jeune Afrique","Africa Check",
 "ABC News","ABC Australia","SBS News","Sydney Morning Herald","The Age","Australian Financial Review","RNZ",
 "New Zealand Herald","Stuff","Newsroom"
]

IMPACT={
 10:["nuclear war","world war","invasion","state of emergency","coup attempt"],
 9:["missile","airstrike","air strike","war","sanctions","central bank","rate hike","rate cut","ceasefire","military attack","tariff","default","earthquake"],
 8:["strike","conflict","election","inflation","interest rate","trade war","oil","gas","military","security","summit","embargo","currency","recession","gdp","defence","defense"],
 7:["government","president","prime minister","parliament","diplomacy","trade","energy","bank","budget","protest","border","climate","flood","wildfire","technology"," ai "],
 6:["economy","economic","market","investment","export","import","migration","health","disease","infrastructure","shipping","food","agriculture"]
}
CATEGORIES=[
 ("Conflit",["war","missile","strike","attack","military","ceasefire","invasion"]),
 ("Économie",["economy","inflation","gdp","market","rate","bank","budget","debt"]),
 ("Énergie",["oil","gas","energy","lng","opec","pipeline"]),
 ("Diplomatie",["summit","diplomacy","talks","treaty","sanctions"]),
 ("Politique",["election","government","president","minister","parliament"]),
 ("Sécurité",["security","terror","border","cyber"]),
 ("Climat",["climate","flood","wildfire","storm","earthquake"]),
 ("Technologie",["technology","artificial intelligence"," ai ","semiconductor","chip"])
]

def fr_date(d): return f"{d.day} {FR_MONTHS[d.month-1]} {d.year}"
def month_bucket(d): return f"{FR_MONTHS[d.month-1].capitalize()} {d.year}"
def week_bucket(d):
    mon=d-timedelta(days=d.weekday()); sun=mon+timedelta(days=6)
    if mon.month==sun.month:return f"{mon.day}–{sun.day} {FR_MONTHS[mon.month-1]} {sun.year}"
    return f"{fr_date(mon)} – {fr_date(sun)}"

def score(title):
    t=" "+title.lower()+" "
    for s in sorted(IMPACT,reverse=True):
        if any(w in t for w in IMPACT[s]): return s
    return 5

def category(title):
    t=" "+title.lower()+" "
    for cat,words in CATEGORIES:
        if any(w in t for w in words): return cat
    return "Géopolitique"

def key_title(title):
    words=re.findall(r"[a-z0-9à-ÿ]+",title.lower())
    stop={"the","a","an","of","to","and","in","on","for","with","as","at","de","la","le","les","des","du","un","une","et","en","sur"}
    return " ".join(w for w in words if w not in stop)[:150]

def clean_title(raw):
    raw=re.sub(r"\s+"," ",raw or "").strip()
    parts=raw.rsplit(" - ",1)
    return (parts[0].strip(),parts[1].strip()) if len(parts)==2 and len(parts[1])<70 else (raw,"")

def trusted_source(label):
    l=(label or "").lower()
    return any(s.lower() in l for s in SOURCE_LABELS)

def source_name(label):
    l=(label or "").strip()
    if "associated press" in l.lower() or l.lower()=="ap news": return "AP"
    if "abc.net.au" in l.lower(): return "ABC Australia"
    return l or "Source"

def editorial_day(dt): return dt.astimezone(PARIS).date()

def google_rss(region,start_date,end_date):
    # Les régions structurellement moins couvertes utilisent une requête plus large :
    # on cherche d'abord les pays/organisations, puis le filtre d'impact est fait localement.
    if region in ("Afrique","Amérique du Sud","Océanie"):
        q=f'({REGIONS[region]}) after:{start_date.isoformat()} before:{(end_date+timedelta(days=1)).isoformat()}'
    else:
        q=f'({REGIONS[region]}) ({IMPACT_QUERY}) after:{start_date.isoformat()} before:{(end_date+timedelta(days=1)).isoformat()}'
    params={"q":q,"hl":"fr","gl":"FR","ceid":"FR:fr"}
    url="https://news.google.com/rss/search?"+urllib.parse.urlencode(params)
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 GeoClic/1.3"})
    with urllib.request.urlopen(req,timeout=30) as r:
        root=ET.fromstring(r.read())
    out=[]
    for item in root.findall(".//item"):
        title_el=item.find("title"); link_el=item.find("link"); date_el=item.find("pubDate"); src_el=item.find("source")
        if title_el is None or date_el is None: continue
        try: dt=parsedate_to_datetime(date_el.text)
        except: continue
        if dt.tzinfo is None: dt=dt.replace(tzinfo=UTC)
        title,fallback=clean_title(title_el.text or "")
        src=(src_el.text if src_el is not None else fallback) or fallback
        if not trusted_source(src): continue
        out.append({"title":title,"source":src,"date":dt,"url":link_el.text if link_el is not None else ""})
    return out

def parse_bucket_date(bucket):
    months={m:i+1 for i,m in enumerate(FR_MONTHS)}
    m=re.match(r"(\d+)\s+(\w+)\s+(\d{4})",bucket or "")
    if not m:return None
    return datetime(int(m.group(3)),months[m.group(2)],int(m.group(1))).date()

def build_generated(start_date,end_date):
    generated=[]
    for region in REGIONS:
        grouped=defaultdict(list); seen=set()

        # Le backfill historique interroge chaque journée séparément pour éviter
        # que les résultats récents n'écrasent les jours plus anciens.
        if os.getenv("BACKFILL_MONTH","0")=="1":
            ranges=[(start_date+timedelta(days=i),start_date+timedelta(days=i))
                    for i in range((end_date-start_date).days+1)]
        else:
            ranges=[(start_date,end_date)]

        for a,b in ranges:
            try:
                articles=google_rss(region,a,b)
            except Exception as e:
                print("RSS",region,a,b,e,file=sys.stderr)
                articles=[]

            for art in articles:
                d=editorial_day(art["date"])
                if d<start_date or d>end_date: continue
                title=art["title"]
                if len(title)<22: continue
                k=(d,key_title(title))
                if not k[1] or k in seen: continue
                seen.add(k)
                grouped[d].append({
                  "regions":[region],"period":"day","bucket":fr_date(d),"score":score(title),
                  "category":category(title),"summary":title,"sources":[source_name(art["source"])],
                  "url":art["url"],"published_at":art["date"].astimezone(PARIS).isoformat(),"origin":"rss"
                })

        for i in range((end_date-start_date).days+1):
            d=start_date+timedelta(days=i)
            rows=sorted(grouped.get(d,[]),key=lambda x:x.get("published_at",""),reverse=True)
            # Objectif de couverture : jusqu’à 25 sujets/jour/région, sans inventer de sujets.
            generated.extend(rows[:25])
    return generated

def main():
    now=datetime.now(PARIS)
    backfill=os.getenv("BACKFILL_MONTH","0")=="1"
    old=json.loads(DATA.read_text(encoding="utf-8")) if DATA.exists() else {"items":[]}
    start_date=now.date().replace(day=1) if backfill else now.date()
    end_date=now.date()

    generated=build_generated(start_date,end_date)
    rebuilt={fr_date(start_date+timedelta(days=i)) for i in range((end_date-start_date).days+1)}

    preserved=list(old.get("items",[]))
    old_daily=[x for x in preserved if x.get("period")=="day"]
    existing={(x.get("bucket"), tuple(x.get("regions",[])), key_title(x.get("summary",""))) for x in old_daily}
    fresh=[]
    for x in generated:
        k=(x.get("bucket"), tuple(x.get("regions",[])), key_title(x.get("summary","")))
        if k not in existing:
            fresh.append(x); existing.add(k)
    day_items=old_daily+fresh
    non_daily_manual=[x for x in old.get("items",[]) if x.get("period")!="day" and x.get("origin") not in ("rss","gdelt")]

    by_region=defaultdict(list)
    for x in day_items:
        d=parse_bucket_date(x.get("bucket"))
        if not d: continue
        for region in x.get("regions",[]): by_region[region].append((d,x))

    week_names=sorted({week_bucket(d) for rows in by_region.values() for d,_ in rows},reverse=True)
    month_names=sorted({month_bucket(d) for rows in by_region.values() for d,_ in rows},reverse=True)
    summaries=[]
    for region,rows in by_region.items():
        for period,names,limit in (("week",week_names,18),("month",month_names,30)):
            for name in names:
                subset=[(d,x) for d,x in rows if (week_bucket(d) if period=="week" else month_bucket(d))==name]
                subset.sort(key=lambda z:(-z[1]["score"],z[0]))
                used=set(); picked=[]
                for _,x in subset:
                    k=key_title(x["summary"])
                    if k in used: continue
                    used.add(k)
                    y=dict(x)
                    y["period"]=period; y["bucket"]=name; y["origin"]="rss"
                    picked.append(y)
                    if len(picked)>=limit: break
                summaries.extend(picked)

    day_buckets=[fr_date(end_date-timedelta(days=i)) for i in range((end_date-start_date).days+1)] if backfill else [fr_date(start_date)]
    coverage={}
    for i in range((end_date-start_date).days+1):
        d=start_date+timedelta(days=i)
        s=datetime.combine(d,dtime(0,0),PARIS); e=datetime.combine(d,dtime(23,59),PARIS)
        coverage[f"day:{fr_date(d)}"]=f"Journée civile : {s.strftime('%d/%m %H:%M')} → {e.strftime('%d/%m %H:%M')}"
    for w in week_names: coverage[f"week:{w}"]="Condensé automatique de la semaine"
    for m in month_names: coverage[f"month:{m}"]="Condensé automatique du mois"

    out={
      "generated_at":now.isoformat(),"timezone":"Europe/Paris",
      "window_rule":"Une date couvre de 00h00 à 23h59 heure de Paris.",
      "target_per_region_per_day":15,
      "buckets":{"day":day_buckets,"week":week_names,"month":month_names},
      "coverage":coverage,
      "items":day_items+non_daily_manual+summaries
    }
    DATA.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
    print("generated",len(generated),"daily items; total",len(out["items"]))

if __name__=="__main__": main()

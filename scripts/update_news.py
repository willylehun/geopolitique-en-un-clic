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

REGIONS={
 "International":"geopolitics sanctions diplomacy war conflict oil gas inflation trade tariffs security central bank election",
 "Europe":"Europe EU Ukraine Russia France Germany Britain UK Italy Spain Poland Balkans",
 "Asie":"Asia China Japan India Pakistan Korea Taiwan Iran Israel Gaza Saudi Yemen Indonesia Philippines",
 "Amérique du Nord":"United States USA Canada Mexico",
 "Amérique du Sud":"Brazil Argentina Colombia Chile Peru Venezuela Ecuador Bolivia Paraguay Uruguay Suriname Guyana",
 "Afrique":"Africa Nigeria South Africa Kenya Sudan Congo Ethiopia Somalia Morocco Algeria Egypt Ghana Mali Niger",
 "Océanie":"Australia New Zealand Pacific Fiji Papua New Guinea Samoa Tonga"
}

SITES=[
 "reuters.com","apnews.com","bbc.com","france24.com","dw.com","aljazeera.com",
 "ft.com","theguardian.com","euronews.com","channelnewsasia.com","cbc.ca",
 "abc.net.au","rnz.co.nz","news24.com","nation.africa"
]
SOURCE_NAMES={
 "Reuters":"Reuters","Associated Press":"AP","AP News":"AP","BBC":"BBC","France 24":"France 24",
 "DW":"DW","Al Jazeera":"Al Jazeera","Financial Times":"Financial Times",
 "The Guardian":"The Guardian","Euronews":"Euronews","CNA":"CNA","CBC":"CBC",
 "ABC News":"ABC Australia","ABC Australia":"ABC Australia","RNZ":"RNZ",
 "News24":"News24","Nation":"Nation Africa"
}
FR_MONTHS=["janvier","février","mars","avril","mai","juin","juillet","août","septembre","octobre","novembre","décembre"]

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

def week_bucket(d):
    mon=d-timedelta(days=d.weekday()); sun=mon+timedelta(days=6)
    if mon.month==sun.month:return f"{mon.day}–{sun.day} {FR_MONTHS[mon.month-1]} {sun.year}"
    return f"{fr_date(mon)} – {fr_date(sun)}"

def month_bucket(d): return f"{FR_MONTHS[d.month-1].capitalize()} {d.year}"

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
    # Google News often appends " - Source"
    parts=raw.rsplit(" - ",1)
    if len(parts)==2 and len(parts[1])<50:
        return parts[0].strip(), parts[1].strip()
    return raw,""

def source_name(label):
    for k,v in SOURCE_NAMES.items():
        if k.lower() in (label or "").lower(): return v
    return label or "Source"

def editorial_day(dt):
    return (dt.astimezone(PARIS)-timedelta(hours=6,minutes=30)).date()

def google_rss(region,start_date,end_date):
    # end_date is inclusive in our logic; Google before: is exclusive, so add one day.
    siteq=" OR ".join(f"site:{s}" for s in SITES)
    q=f'({REGIONS[region]}) ({siteq}) after:{start_date.isoformat()} before:{(end_date+timedelta(days=1)).isoformat()}'
    params={"q":q,"hl":"en-US","gl":"US","ceid":"US:en"}
    url="https://news.google.com/rss/search?"+urllib.parse.urlencode(params)
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 GeoClic/1.2"})
    with urllib.request.urlopen(req,timeout=30) as r:
        root=ET.fromstring(r.read())
    out=[]
    for item in root.findall(".//item"):
        title_el=item.find("title"); link_el=item.find("link"); date_el=item.find("pubDate")
        if title_el is None or date_el is None: continue
        try: dt=parsedate_to_datetime(date_el.text)
        except: continue
        if dt.tzinfo is None: dt=dt.replace(tzinfo=UTC)
        title,src=clean_title(title_el.text or "")
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
        # Split month in halves to increase result depth.
        ranges=[]
        cur=start_date
        while cur<=end_date:
            stop=min(cur+timedelta(days=9),end_date)
            ranges.append((cur,stop))
            cur=stop+timedelta(days=1)

        articles=[]
        for a,b in ranges:
            try: articles.extend(google_rss(region,a,b))
            except Exception as e: print("RSS",region,a,b,e,file=sys.stderr)

        grouped=defaultdict(list); seen=set()
        for a in articles:
            d=editorial_day(a["date"])
            if d<start_date or d>end_date: continue
            title=a["title"]
            if len(title)<22: continue
            k=(d,key_title(title))
            if not k[1] or k in seen: continue
            seen.add(k)
            grouped[d].append({
              "regions":[region],"period":"day","bucket":fr_date(d),"score":score(title),
              "category":category(title),"summary":title,"sources":[source_name(a["source"])],
              "url":a["url"],"origin":"rss"
            })

        for d in (start_date+timedelta(days=i) for i in range((end_date-start_date).days+1)):
            rows=sorted(grouped.get(d,[]),key=lambda x:(-x["score"],x["summary"]))
            generated.extend(rows[:12])
    return generated

def main():
    now=datetime.now(PARIS)
    backfill=os.getenv("BACKFILL_MONTH","0")=="1"
    old=json.loads(DATA.read_text(encoding="utf-8")) if DATA.exists() else {"items":[]}

    if backfill:
        start_date=now.date().replace(day=1)
        end_date=now.date()
    else:
        start_date=(now-timedelta(days=1)).date()
        end_date=start_date

    generated=build_generated(start_date,end_date)
    rebuilt={fr_date(start_date+timedelta(days=i)) for i in range((end_date-start_date).days+1)}

    preserved=[x for x in old.get("items",[]) if not (x.get("origin")=="rss" and x.get("period")=="day" and x.get("bucket") in rebuilt)]
    # Preserve curated/manual daily entries and generated entries from dates outside current rebuild.
    day_items=[x for x in preserved if x.get("period")=="day"]+generated
    non_daily_manual=[x for x in old.get("items",[]) if x.get("period")!="day" and x.get("origin") not in ("rss","gdelt")]

    by_region=defaultdict(list)
    for x in day_items:
        d=parse_bucket_date(x.get("bucket"))
        if not d: continue
        for region in x.get("regions",[]): by_region[region].append((d,x))

    week_names=sorted({week_bucket(d) for rows in by_region.values() for d,_ in rows},reverse=True)
    month_names=sorted({month_bucket(d) for rows in by_region.values() for d,_ in rows},reverse=True)
    summary=[]

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
                    y={kk:vv for kk,vv in x.items() if kk!="url"}
                    y["period"]=period; y["bucket"]=name; y["origin"]="rss"
                    picked.append(y)
                    if len(picked)>=limit: break
                summary.extend(picked)

    if backfill:
        day_buckets=[fr_date(end_date-timedelta(days=i)) for i in range((end_date-start_date).days+1)]
    else:
        all_days=sorted({d for rows in by_region.values() for d,_ in rows},reverse=True)
        day_buckets=[fr_date(d) for d in all_days]

    coverage={}
    all_dates=[start_date+timedelta(days=i) for i in range((end_date-start_date).days+1)]
    for d in all_dates:
        start=datetime.combine(d,dtime(6,30),PARIS)
        end=start+timedelta(days=1)-timedelta(minutes=1)
        coverage[f"day:{fr_date(d)}"]=f"Fenêtre : {start.strftime('%d/%m %H:%M')} → {end.strftime('%d/%m %H:%M')}"
    for w in week_names: coverage[f"week:{w}"]="Condensé automatique de la semaine"
    for m in month_names: coverage[f"month:{m}"]="Condensé automatique du mois"

    out={
      "generated_at":now.isoformat(),"timezone":"Europe/Paris",
      "window_rule":"Une date couvre de 06h30 ce jour-là à 06h29 le lendemain.",
      "target_per_region_per_day":10,
      "buckets":{"day":day_buckets,"week":week_names,"month":month_names},
      "coverage":coverage,
      "items":day_items+non_daily_manual+summary
    }
    DATA.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
    print("generated",len(generated),"daily items; total",len(out["items"]))

if __name__=="__main__": main()

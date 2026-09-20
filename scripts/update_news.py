#!/usr/bin/env python3
import json, os, re, sys, time, urllib.parse, urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, time as dtime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"/"news.json"
PARIS=ZoneInfo("Europe/Paris")
UTC=ZoneInfo("UTC")

REGIONS={
 "International":"geopolitics OR sanctions OR diplomacy OR war OR conflict OR oil OR gas OR inflation OR trade OR tariffs OR security OR central bank OR election",
 "Europe":"Europe OR European Union OR EU OR Ukraine OR Russia OR France OR Germany OR Britain OR UK OR Italy OR Spain OR Poland OR Balkans",
 "Asie":"Asia OR China OR Japan OR India OR Pakistan OR Korea OR Taiwan OR Iran OR Israel OR Gaza OR Saudi OR Yemen OR Indonesia OR Philippines",
 "Amérique du Nord":'"United States" OR U.S. OR USA OR Canada OR Mexico',
 "Amérique du Sud":"Brazil OR Argentina OR Colombia OR Chile OR Peru OR Venezuela OR Ecuador OR Bolivia OR Paraguay OR Uruguay OR Suriname OR Guyana",
 "Afrique":"Africa OR Nigeria OR South Africa OR Kenya OR Sudan OR Congo OR Ethiopia OR Somalia OR Morocco OR Algeria OR Egypt OR Ghana OR Mali OR Niger",
 "Océanie":"Australia OR New Zealand OR Pacific OR Fiji OR Papua New Guinea OR Samoa OR Tonga"
}

DOMAINS=[
 "reuters.com","apnews.com","bbc.com","france24.com","dw.com","aljazeera.com",
 "ft.com","theguardian.com","euronews.com","channelnewsasia.com","cbc.ca",
 "abc.net.au","rnz.co.nz","news24.com","nation.africa"
]
SOURCE_NAMES={
 "reuters.com":"Reuters","apnews.com":"AP","bbc.com":"BBC","france24.com":"France 24",
 "dw.com":"DW","aljazeera.com":"Al Jazeera","ft.com":"Financial Times",
 "theguardian.com":"The Guardian","euronews.com":"Euronews","channelnewsasia.com":"CNA",
 "cbc.ca":"CBC","abc.net.au":"ABC Australia","rnz.co.nz":"RNZ",
 "news24.com":"News24","nation.africa":"Nation Africa"
}
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
FR_MONTHS=["janvier","février","mars","avril","mai","juin","juillet","août","septembre","octobre","novembre","décembre"]

def source_name(domain):
    d=(domain or "").lower()
    for k,v in SOURCE_NAMES.items():
        if k in d:return v
    return d.replace("www.","") or "Source"

def clean_title(title):
    title=re.sub(r"\s+"," ",title or "").strip()
    return title[:230]

def key_title(title):
    words=re.findall(r"[a-z0-9à-ÿ]+",title.lower())
    stop={"the","a","an","of","to","and","in","on","for","with","as","at","de","la","le","les","des","du","un","une","et","en","sur"}
    return " ".join(w for w in words if w not in stop)[:150]

def score(title):
    t=" "+title.lower()+" "
    for s in sorted(IMPACT,reverse=True):
        if any(w in t for w in IMPACT[s]):return s
    return 5

def category(title):
    t=" "+title.lower()+" "
    for cat,words in CATEGORIES:
        if any(w in t for w in words):return cat
    return "Géopolitique"

def fr_date(d):
    return f"{d.day} {FR_MONTHS[d.month-1]} {d.year}"

def parse_seen(value):
    if not value:return None
    digits=re.sub(r"\D","",value)
    if len(digits)<12:return None
    try:
        dt=datetime.strptime(digits[:14] if len(digits)>=14 else digits[:12],"%Y%m%d%H%M%S" if len(digits)>=14 else "%Y%m%d%H%M").replace(tzinfo=UTC)
        return dt.astimezone(PARIS)
    except:return None

def editorial_day(local_dt):
    return (local_dt-timedelta(hours=6,minutes=30)).date()

def gdelt(region,start_local,end_local,maxrecords=250):
    domain_q=" OR ".join(f"domain:{d}" for d in DOMAINS)
    q=f"({domain_q}) ({REGIONS[region]})"
    params={
      "query":q,"mode":"artlist","maxrecords":str(maxrecords),"format":"json","sort":"hybridrel",
      "startdatetime":start_local.astimezone(UTC).strftime("%Y%m%d%H%M%S"),
      "enddatetime":end_local.astimezone(UTC).strftime("%Y%m%d%H%M%S")
    }
    url="https://api.gdeltproject.org/api/v2/doc/doc?"+urllib.parse.urlencode(params)
    req=urllib.request.Request(url,headers={"User-Agent":"GeoClic/1.1"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req,timeout=30) as r:
                return json.load(r).get("articles",[])
        except Exception as e:
            print("GDELT",region,"attempt",attempt+1,e,file=sys.stderr)
            time.sleep(2+attempt)
    return []

def week_bucket(d):
    mon=d-timedelta(days=d.weekday()); sun=mon+timedelta(days=6)
    if mon.month==sun.month:return f"{mon.day}–{sun.day} {FR_MONTHS[mon.month-1]} {sun.year}"
    return f"{fr_date(mon)} – {fr_date(sun)}"

def month_bucket(d):
    return f"{FR_MONTHS[d.month-1].capitalize()} {d.year}"

def main():
    now=datetime.now(PARIS)
    backfill=os.getenv("BACKFILL_MONTH","0")=="1"
    old=json.loads(DATA.read_text(encoding="utf-8")) if DATA.exists() else {"items":[]}
    manual=[x for x in old.get("items",[]) if x.get("origin")!="gdelt"]

    if backfill:
        first=now.replace(day=1,hour=6,minute=30,second=0,microsecond=0)
        start=first
        end=now
        dates=[]
        d=first.date()
        while d<=now.date():
            dates.append(d); d+=timedelta(days=1)
    else:
        target=(now-timedelta(days=1)).date()
        start=datetime.combine(target,dtime(6,30),PARIS)
        end=start+timedelta(days=1)-timedelta(seconds=1)
        dates=[target]

    generated=[]
    for region in REGIONS:
        arts=gdelt(region,start,end,250 if backfill else 120)
        grouped=defaultdict(list)
        seen=set()
        for a in arts:
            title=clean_title(a.get("title",""))
            local=parse_seen(a.get("seendate") or a.get("seenDate") or "")
            if not title or len(title)<22 or not local:continue
            day=editorial_day(local)
            if day not in dates:continue
            k=key_title(title)
            if not k or k in seen:continue
            seen.add(k)
            grouped[day].append({
              "regions":[region],"period":"day","bucket":fr_date(day),"score":score(title),
              "category":category(title),"summary":title,"sources":[source_name(a.get("domain",""))],
              "url":a.get("url"),"origin":"gdelt"
            })
        for day in dates:
            rows=sorted(grouped.get(day,[]),key=lambda x:(-x["score"],x["summary"]))
            generated.extend(rows[:12])
        time.sleep(.4)

    rebuilt={fr_date(d) for d in dates}
    preserved=[x for x in old.get("items",[]) if not (x.get("origin")=="gdelt" and x.get("period")=="day" and x.get("bucket") in rebuilt)]
    day_items=[x for x in preserved if x.get("period")=="day"]+generated
    non_daily_manual=[x for x in manual if x.get("period")!="day"]

    # Build summaries strictly from daily rows.
    by_region=defaultdict(list)
    for x in day_items:
        m=re.match(r"(\d+)\s+(\w+)\s+(\d{4})",x.get("bucket",""))
        if not m:continue
        months={m:i+1 for i,m in enumerate(FR_MONTHS)}
        dt=datetime(int(m.group(3)),months[m.group(2)],int(m.group(1))).date()
        for region in x.get("regions",[]):by_region[region].append((dt,x))

    summary=[]
    week_names=sorted({week_bucket(d) for rows in by_region.values() for d,_ in rows},reverse=True)
    month_names=sorted({month_bucket(d) for rows in by_region.values() for d,_ in rows},reverse=True)
    for region,rows in by_region.items():
        for period,names in (("week",week_names),("month",month_names)):
            for name in names:
                subset=[(d,x) for d,x in rows if (week_bucket(d) if period=="week" else month_bucket(d))==name]
                subset.sort(key=lambda z:(-z[1]["score"],z[0]))
                used=set(); picked=[]
                lim=18 if period=="week" else 30
                for _,x in subset:
                    k=key_title(x["summary"])
                    if k in used:continue
                    used.add(k)
                    y={k:v for k,v in x.items() if k!="url"}
                    y["period"]=period;y["bucket"]=name;y["origin"]="gdelt"
                    picked.append(y)
                    if len(picked)>=lim:break
                summary.extend(picked)

    day_buckets=[fr_date(d) for d in sorted({d for rows in by_region.values() for d,_ in rows},reverse=True)]
    # Ensure full current month appears day-by-day during backfill, even if one day has fewer qualifying stories.
    if backfill:
        day_buckets=[fr_date(d) for d in sorted(dates,reverse=True)]

    coverage={}
    for d in dates if backfill else [dates[0]]:
        startd=datetime.combine(d,dtime(6,30),PARIS); endd=startd+timedelta(days=1)-timedelta(minutes=1)
        coverage[f"day:{fr_date(d)}"]=f"Fenêtre : {startd.strftime('%d/%m %H:%M')} → {endd.strftime('%d/%m %H:%M')}"
    for w in week_names:coverage[f"week:{w}"]="Condensé automatique de la semaine"
    for m in month_names:coverage[f"month:{m}"]="Condensé automatique du mois"

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

if __name__=="__main__":main()

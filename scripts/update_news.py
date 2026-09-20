#!/usr/bin/env python3
import json, os, re, sys, time, urllib.parse, urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, time as dtime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "news.json"
PARIS = ZoneInfo("Europe/Paris")
UTC = ZoneInfo("UTC")

REGIONS = {
    "International": {
        "terms": "geopolitics OR sanctions OR diplomacy OR war OR conflict OR oil OR gas OR inflation OR trade OR tariffs OR security OR central bank OR election",
    },
    "Europe": {
        "terms": "Europe OR European Union OR EU OR Ukraine OR Russia OR France OR Germany OR Britain OR UK OR Italy OR Spain OR Poland OR Balkans",
    },
    "Asie": {
        "terms": "Asia OR China OR Japan OR India OR Pakistan OR Korea OR Taiwan OR Iran OR Israel OR Gaza OR Saudi OR Yemen OR Indonesia OR Philippines",
    },
    "Amérique du Nord": {
        "terms": '"United States" OR U.S. OR USA OR Canada OR Mexico',
    },
    "Amérique du Sud": {
        "terms": "Brazil OR Argentina OR Colombia OR Chile OR Peru OR Venezuela OR Ecuador OR Bolivia OR Paraguay OR Uruguay OR Suriname OR Guyana",
    },
    "Afrique": {
        "terms": "Africa OR Nigeria OR South Africa OR Kenya OR Sudan OR Congo OR Ethiopia OR Somalia OR Morocco OR Algeria OR Egypt OR Ghana OR Mali OR Niger",
    },
    "Océanie": {
        "terms": "Australia OR New Zealand OR Pacific OR Fiji OR Papua New Guinea OR Samoa OR Tonga",
    },
}

DOMAINS = [
    "reuters.com", "apnews.com", "bbc.com", "france24.com", "dw.com",
    "aljazeera.com", "ft.com", "theguardian.com", "euronews.com",
    "nhk.or.jp", "channelnewsasia.com", "straitstimes.com", "thehindu.com",
    "cbc.ca", "abcnews.go.com", "abc.net.au", "rnz.co.nz",
    "news24.com", "nation.africa", "premiumtimesng.com",
    "folha.uol.com.br", "lanacion.com.ar", "eltiempo.com"
]

SOURCE_NAMES = {
    "reuters.com": "Reuters", "apnews.com": "AP", "bbc.com": "BBC",
    "france24.com": "France 24", "dw.com": "DW", "aljazeera.com": "Al Jazeera",
    "ft.com": "Financial Times", "theguardian.com": "The Guardian",
    "euronews.com": "Euronews", "nhk.or.jp": "NHK", "channelnewsasia.com": "CNA",
    "straitstimes.com": "The Straits Times", "thehindu.com": "The Hindu",
    "cbc.ca": "CBC", "abcnews.go.com": "ABC News", "abc.net.au": "ABC Australia",
    "rnz.co.nz": "RNZ", "news24.com": "News24", "nation.africa": "Nation Africa",
    "premiumtimesng.com": "Premium Times", "folha.uol.com.br": "Folha",
    "lanacion.com.ar": "La Nación", "eltiempo.com": "El Tiempo"
}

IMPACT = {
    10: ["nuclear war", "world war", "invasion", "state of emergency", "coup d'etat", "coup attempt"],
    9: ["missile", "airstrike", "air strike", "war", "invasion", "sanctions", "central bank", "rate hike",
        "rate cut", "oil shock", "ceasefire", "military attack", "tariff", "debt default", "earthquake"],
    8: ["strike", "conflict", "election", "inflation", "interest rate", "trade war", "oil", "gas", "military",
        "security", "summit", "embargo", "currency", "recession", "gdp", "defence", "defense"],
    7: ["government", "president", "prime minister", "parliament", "diplomacy", "trade", "energy", "bank",
        "budget", "protest", "border", "climate", "flood", "wildfire", "technology", "ai"],
    6: ["economy", "economic", "market", "investment", "export", "import", "migration", "health", "disease",
        "infrastructure", "shipping", "food", "agriculture"],
}

CATEGORIES = [
    ("Conflit", ["war", "missile", "strike", "attack", "military", "ceasefire", "invasion"]),
    ("Économie", ["economy", "inflation", "gdp", "market", "rate", "bank", "budget", "debt"]),
    ("Énergie", ["oil", "gas", "energy", "lng", "opec", "pipeline"]),
    ("Diplomatie", ["summit", "diplomacy", "talks", "treaty", "sanctions"]),
    ("Politique", ["election", "government", "president", "minister", "parliament"]),
    ("Sécurité", ["security", "terror", "border", "cyber"]),
    ("Climat", ["climate", "flood", "wildfire", "storm", "earthquake"]),
    ("Technologie", ["technology", "artificial intelligence", " ai ", "semiconductor", "chip"]),
]

def source_name(domain):
    d = (domain or "").lower()
    for key, name in SOURCE_NAMES.items():
        if key in d:
            return name
    return d.replace("www.", "") or "Source"

def category(title):
    t = " " + title.lower() + " "
    for cat, words in CATEGORIES:
        if any(w in t for w in words):
            return cat
    return "Géopolitique"

def score(title):
    t = title.lower()
    for s in sorted(IMPACT.keys(), reverse=True):
        if any(w in t for w in IMPACT[s]):
            return s
    return 5

def clean_title(title):
    title = re.sub(r"\s+", " ", title or "").strip()
    title = re.sub(r"\s+[-|–—]\s+(Reuters|AP News|BBC.*|France 24|DW.*)$", "", title, flags=re.I)
    return title[:230]

def norm_key(title):
    words = re.findall(r"[a-z0-9à-ÿ]+", title.lower())
    stop = {"the","a","an","of","to","and","in","on","for","with","as","at","de","la","le","les","des","du","un","une","et","en","sur"}
    return " ".join(w for w in words if w not in stop)[:140]

def gdelt_fetch(region, start_local, end_local):
    domain_q = " OR ".join(f"domain:{d}" for d in DOMAINS)
    terms = REGIONS[region]["terms"]
    query = f"({domain_q}) ({terms})"
    params = {
        "query": query,
        "mode": "artlist",
        "maxrecords": "250",
        "format": "json",
        "sort": "hybridrel",
        "startdatetime": start_local.astimezone(UTC).strftime("%Y%m%d%H%M%S"),
        "enddatetime": end_local.astimezone(UTC).strftime("%Y%m%d%H%M%S"),
    }
    url = "https://api.gdeltproject.org/api/v2/doc/doc?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "GeoClic/1.0"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.load(r).get("articles", [])
        except Exception as exc:
            print(f"GDELT {region} attempt {attempt+1}: {exc}", file=sys.stderr)
            time.sleep(2 + attempt)
    return []

def fetch_day(day):
    start = datetime.combine(day.date(), dtime(6,30), PARIS)
    end = start + timedelta(days=1) - timedelta(seconds=1)
    bucket = day.strftime("%-d %B %Y")
    fr_months = {
      "January":"janvier","February":"février","March":"mars","April":"avril","May":"mai","June":"juin",
      "July":"juillet","August":"août","September":"septembre","October":"octobre","November":"novembre","December":"décembre"
    }
    for en, fr in fr_months.items(): bucket = bucket.replace(en, fr)
    out = []
    for region in REGIONS:
        articles = gdelt_fetch(region, start, end)
        seen = set()
        candidates = []
        for a in articles:
            title = clean_title(a.get("title", ""))
            if not title or len(title) < 22:
                continue
            s = score(title)
            if s < 5:
                continue
            key = norm_key(title)
            if not key or key in seen:
                continue
            seen.add(key)
            candidates.append({
                "regions": [region],
                "period": "day",
                "bucket": bucket,
                "score": s,
                "category": category(title),
                "summary": title,
                "sources": [source_name(a.get("domain",""))],
                "url": a.get("url"),
                "origin": "gdelt"
            })
        candidates.sort(key=lambda x: (-x["score"], x["summary"]))
        # Around 10, never pad with low-value fabricated items.
        out.extend(candidates[:12])
        time.sleep(0.35)
    return bucket, out

def fr_date(d):
    months = ["janvier","février","mars","avril","mai","juin","juillet","août","septembre","octobre","novembre","décembre"]
    return f"{d.day} {months[d.month-1]} {d.year}"

def week_bucket(d):
    monday = d - timedelta(days=d.weekday())
    sunday = monday + timedelta(days=6)
    if monday.month == sunday.month:
        months = ["janvier","février","mars","avril","mai","juin","juillet","août","septembre","octobre","novembre","décembre"]
        return f"{monday.day}–{sunday.day} {months[monday.month-1]} {sunday.year}"
    return f"{fr_date(monday)} – {fr_date(sunday)}"

def month_bucket(d):
    months = ["Janvier","Février","Mars","Avril","Mai","Juin","Juillet","Août","Septembre","Octobre","Novembre","Décembre"]
    return f"{months[d.month-1]} {d.year}"

def condense(items, period, bucket, region, limit=15):
    relevant = [x for x in items if x.get("period")=="day" and region in x.get("regions",[]) and x.get("_date")]
    if period == "week":
        relevant = [x for x in relevant if week_bucket(x["_date"].date()) == bucket]
    else:
        relevant = [x for x in relevant if month_bucket(x["_date"].date()) == bucket]
    relevant.sort(key=lambda x: (-x["score"], x["summary"]))
    seen=set(); out=[]
    for x in relevant:
        k=norm_key(x["summary"])
        if k in seen: continue
        seen.add(k)
        y={k:v for k,v in x.items() if not k.startswith("_")}
        y["period"]=period; y["bucket"]=bucket
        out.append(y)
        if len(out)>=limit: break
    return out

def parse_bucket_date(bucket):
    months = {"janvier":1,"février":2,"mars":3,"avril":4,"mai":5,"juin":6,"juillet":7,"août":8,"septembre":9,"octobre":10,"novembre":11,"décembre":12}
    m=re.match(r"(\d+)\s+(\w+)\s+(\d{4})", bucket)
    if not m: return None
    return datetime(int(m.group(3)),months[m.group(2)],int(m.group(1)),tzinfo=PARIS)

def main():
    now=datetime.now(PARIS)
    backfill=os.getenv("BACKFILL_MONTH","0")=="1"
    data=json.loads(DATA.read_text(encoding="utf-8")) if DATA.exists() else {"items":[]}
    existing=data.get("items",[])

    if backfill:
        start=now.replace(day=1,hour=0,minute=0,second=0,microsecond=0)
        days=[start+timedelta(days=i) for i in range((now.date()-start.date()).days+1)]
    else:
        d=(now-timedelta(days=1)).date()
        days=[datetime.combine(d,dtime(0,0),PARIS)]

    new_items=[]
    new_buckets=[]
    for day in days:
        bucket, fetched=fetch_day(day)
        new_buckets.append(bucket)
        new_items.extend(fetched)

    # Remove generated daily rows for rebuilt dates; preserve curated/manual rows.
    rebuild=set(new_buckets)
    kept=[x for x in existing if not (x.get("origin")=="gdelt" and x.get("period")=="day" and x.get("bucket") in rebuild)]

    daily=kept+new_items
    for x in daily:
        if x.get("period")=="day":
            x["_date"]=parse_bucket_date(x.get("bucket",""))

    # Rebuild generated week/month condensates from all daily rows.
    daily=[x for x in daily if not (x.get("origin")=="gdelt" and x.get("period") in ("week","month"))]
    all_days=[x for x in daily if x.get("period")=="day" and x.get("_date")]
    weeks=sorted({week_bucket(x["_date"].date()) for x in all_days}, reverse=True)
    months=sorted({month_bucket(x["_date"].date()) for x in all_days}, reverse=True)

    summaries=[]
    for region in REGIONS:
        for wb in weeks:
            for x in condense(all_days,"week",wb,region,15):
                x["origin"]="gdelt"; summaries.append(x)
        for mb in months:
            for x in condense(all_days,"month",mb,region,25):
                x["origin"]="gdelt"; summaries.append(x)

    for x in daily:
        x.pop("_date",None)

    day_buckets=sorted({x["bucket"] for x in daily if x.get("period")=="day"}, key=lambda b: parse_bucket_date(b) or datetime.min.replace(tzinfo=PARIS), reverse=True)
    coverage={}
    for b in day_buckets:
        d=parse_bucket_date(b)
        if d:
            start=d.replace(hour=6,minute=30)
            end=start+timedelta(days=1)-timedelta(minutes=1)
            coverage[f"day:{b}"]=f"Fenêtre : {start.strftime('%d/%m %H:%M')} → {end.strftime('%d/%m %H:%M')}"
    for w in weeks: coverage[f"week:{w}"]="Condensé automatique de la semaine"
    for m in months: coverage[f"month:{m}"]="Condensé automatique du mois"

    out={
        "generated_at":now.isoformat(),
        "timezone":"Europe/Paris",
        "window_rule":"Une date couvre de 06h30 ce jour-là à 06h29 le lendemain.",
        "target_per_region_per_day":10,
        "buckets":{"day":day_buckets,"week":weeks,"month":months},
        "coverage":coverage,
        "items":daily+summaries
    }
    DATA.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"wrote {len(out['items'])} items")

if __name__=="__main__":
    main()

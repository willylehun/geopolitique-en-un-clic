#!/usr/bin/env python3
import json, os, re, sys, urllib.parse, urllib.request, xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timedelta, time as dtime
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"/"news.json"
COUNTRY_COVERAGE=ROOT/"data"/"country-coverage.json"
MONITOR_STATE=ROOT/"data"/"monitor-state.json"
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
SOURCE_LABELS=["Reuters","Associated Press","AP News","BBC","France 24","DW","Al Jazeera","Financial Times","The Economist","The Guardian","Euronews","POLITICO","Le Monde","AFP","NHK","Japan Times","Nikkei Asia","CNA","Channel NewsAsia","The Straits Times","Yonhap","The Korea Herald","The Hindu","The Indian Express","Dawn","The Jakarta Post","Kompas","Tempo","Bangkok Post","Focus Taiwan","Taipei Times","Rappler","The New York Times","The Washington Post","The Wall Street Journal","NPR","PBS NewsHour","ProPublica","Axios","Los Angeles Times","CBS News","CBC","The Globe and Mail","CTV News","El Universal","Folha","O Globo","Estadão","Agência Brasil","La Nación","Clarín","El Tiempo","El Espectador","El Comercio","La Tercera","News24","Daily Maverick","Mail & Guardian","SABC News","Nation Africa","The EastAfrican","Premium Times","Channels Television","Jeune Afrique","Africa Check","ABC News","ABC Australia","SBS News","Sydney Morning Herald","The Age","Australian Financial Review","RNZ","New Zealand Herald","Stuff","Newsroom"]
IMPACT={10:["nuclear war","world war","invasion","state of emergency","coup attempt"],9:["missile","airstrike","air strike","war","sanctions","central bank","rate hike","rate cut","ceasefire","military attack","tariff","default","earthquake"],8:["strike","conflict","election","inflation","interest rate","trade war","oil","gas","military","security","summit","embargo","currency","recession","gdp","defence","defense"],7:["government","president","prime minister","parliament","diplomacy","trade","energy","bank","budget","protest","border","climate","flood","wildfire","technology"," ai "],6:["economy","economic","market","investment","export","import","migration","health","disease","infrastructure","shipping","food","agriculture"]}
CATEGORIES=[("Conflit",["war","missile","strike","attack","military","ceasefire","invasion"]),("Économie",["economy","inflation","gdp","market","rate","bank","budget","debt"]),("Énergie",["oil","gas","energy","lng","opec","pipeline"]),("Diplomatie",["summit","diplomacy","talks","treaty","sanctions"]),("Politique",["election","government","president","minister","parliament"]),("Sécurité",["security","terror","border","cyber"]),("Climat",["climate","flood","wildfire","storm","earthquake"]),("Technologie",["technology","artificial intelligence"," ai ","semiconductor","chip"])]
EN_WORDS={"the","and","with","from","after","against","says","will","amid","over","into","government","president","minister","election","war","trade","security","talks","deal","attack","military","court","bank","rate","climate"}
FR_WORDS={"le","la","les","des","du","de","un","une","et","avec","dans","pour","sur","après","contre","gouvernement","président","ministre","élection","guerre","commerce","sécurité"}

def fr_date(d): return f"{d.day} {FR_MONTHS[d.month-1]} {d.year}"
def month_bucket(d): return f"{FR_MONTHS[d.month-1].capitalize()} {d.year}"
def week_bucket(d):
    mon=d-timedelta(days=d.weekday()); sun=mon+timedelta(days=6)
    return f"Semaine du {fr_date(mon)} au {fr_date(sun)}"
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
    words=re.findall(r"[a-z0-9à-ÿ]+",(title or "").lower())
    stop={"the","a","an","of","to","and","in","on","for","with","as","at","de","la","le","les","des","du","un","une","et","en","sur"}
    return " ".join(w for w in words if w not in stop)[:150]
def clean_title(raw):
    raw=re.sub(r"\s+"," ",raw or "").strip(); parts=raw.rsplit(" - ",1)
    return (parts[0].strip(),parts[1].strip()) if len(parts)==2 and len(parts[1])<70 else (raw,"")
def trusted_source(label): return any(s.lower() in (label or "").lower() for s in SOURCE_LABELS)
def source_name(label):
    l=(label or "").strip()
    if "associated press" in l.lower() or l.lower()=="ap news": return "AP"
    if "abc.net.au" in l.lower(): return "ABC Australia"
    return l or "Source"
def editorial_day(dt): return dt.astimezone(PARIS).date()
def looks_english(text):
    words=re.findall(r"[a-zà-ÿ]+",(text or "").lower())
    en=sum(w in EN_WORDS for w in words); fr=sum(w in FR_WORDS for w in words)
    return en>=2 and en>fr

def google_rss_query(query):
    params={"q":query,"hl":"fr","gl":"FR","ceid":"FR:fr"}; url="https://news.google.com/rss/search?"+urllib.parse.urlencode(params)
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 GeoClic/1.6"})
    with urllib.request.urlopen(req,timeout=30) as r: root=ET.fromstring(r.read())
    out=[]
    for item in root.findall(".//item"):
        title_el=item.find("title"); link_el=item.find("link"); date_el=item.find("pubDate"); src_el=item.find("source")
        if title_el is None or date_el is None: continue
        try: dt=parsedate_to_datetime(date_el.text)
        except: continue
        if dt.tzinfo is None: dt=dt.replace(tzinfo=UTC)
        title,fallback=clean_title(title_el.text or ""); src=(src_el.text if src_el is not None else fallback) or fallback
        if not trusted_source(src) or looks_english(title): continue
        out.append({"title":title,"source":src,"date":dt,"url":link_el.text if link_el is not None else ""})
    return out

def google_rss(region,start_date,end_date):
    base=REGIONS[region]
    q=f'({base}) after:{start_date.isoformat()} before:{(end_date+timedelta(days=1)).isoformat()}' if region in ("Afrique","Amérique du Sud","Océanie") else f'({base}) ({IMPACT_QUERY}) after:{start_date.isoformat()} before:{(end_date+timedelta(days=1)).isoformat()}'
    return google_rss_query(q)

def load_missing_countries():
    if not COUNTRY_COVERAGE.exists(): return []
    try: return json.loads(COUNTRY_COVERAGE.read_text(encoding="utf-8")).get("missing_countries",[])
    except Exception as e:
        print("coverage",e,file=sys.stderr); return []

# Pays dont le nom est contenu dans celui d'un autre pays : les requêtes génériques
# sont trop ambiguës pour valider automatiquement leur couverture.
AMBIGUOUS_COUNTRY_TERMS={
    "Soudan","Soudan du Sud",
    "Guinée","Guinée-Bissau","Guinée équatoriale","Papouasie-Nouvelle-Guinée",
    "Congo","République du Congo","République démocratique du Congo",
    "Niger","Nigeria",
    "Corée du Nord","Corée du Sud",
    "Dominique","République dominicaine",
}
COUNTRY_QUERY_HINTS={
    "Soudan":"Khartoum OR Port-Soudan",
    "Soudan du Sud":"Juba OR South Sudan",
    "Guinée":"Conakry",
    "Guinée-Bissau":"Bissau",
    "Guinée équatoriale":"Malabo OR Equatorial Guinea",
    "Papouasie-Nouvelle-Guinée":"Port Moresby OR Papua New Guinea",
    "Congo":"Brazzaville OR Republic of Congo",
    "République du Congo":"Brazzaville OR Republic of Congo",
    "République démocratique du Congo":"Kinshasa OR DR Congo OR DRC",
    "Niger":"Niamey",
    "Nigeria":"Abuja OR Lagos",
    "Corée du Nord":"Pyongyang OR North Korea",
    "Corée du Sud":"Seoul OR South Korea",
    "Dominique":"Roseau OR Dominica",
    "République dominicaine":"Santo Domingo OR Dominican Republic",
}

def country_query_name(country):
    hint=COUNTRY_QUERY_HINTS.get(country)
    return f'("{country}" OR {hint})' if hint else f'"{country}"'

def load_monitor_state():
    try:
        return json.loads(MONITOR_STATE.read_text(encoding="utf-8"))
    except Exception:
        return {"country_cursor":0,"day_cursor":0,"runs":0}

def save_monitor_state(state, now, country_step=0, day_step=0):
    state["country_cursor"]=int(state.get("country_cursor",0))+country_step
    state["day_cursor"]=int(state.get("day_cursor",0))+day_step
    state["runs"]=int(state.get("runs",0))+1
    state["last_run_at"]=now.isoformat()
    MONITOR_STATE.write_text(json.dumps(state,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def country_title_matches(country,title):
    t=(title or "").lower()
    # Empêcher les faux positifs les plus dangereux entre États aux noms proches.
    exclusions={
      "Soudan":["soudan du sud","south sudan"], "Niger":["nigeria","nigerian"],
      "Guinée":["guinée-bissau","guinée équatoriale","papouasie-nouvelle-guinée","equatorial guinea","papua new guinea","guinea-bissau"],
      "Congo (République du)":["république démocratique du congo","rdc","dr congo","drc"],
      "Dominique":["république dominicaine","dominican republic"],
    }
    if any(x in t for x in exclusions.get(country,[])): return False
    hints={
      "Soudan":["soudan","sudan","khartoum","port-soudan"],"Soudan du Sud":["soudan du sud","south sudan","juba"],
      "Niger":["niger","niamey"],"Nigeria":["nigeria","nigerian","abuja","lagos"],
      "Guinée":["guinée","guinea","conakry"],"Guinée-Bissau":["guinée-bissau","guinea-bissau","bissau"],
      "Guinée équatoriale":["guinée équatoriale","equatorial guinea","malabo"],
      "Papouasie-Nouvelle-Guinée":["papouasie-nouvelle-guinée","papua new guinea","port moresby"],
      "Congo (République du)":["congo-brazzaville","république du congo","republic of congo","brazzaville"],
      "Congo (RDC)":["rdc","république démocratique du congo","dr congo","drc","kinshasa"],
      "Dominique":["dominique","dominica","roseau"],"République dominicaine":["république dominicaine","dominican republic","santo domingo"],
    }
    return any(x in t for x in hints.get(country,[country.lower()]))

def country_backfill(start_date,end_date,state):
    rows=[]; found=set()
    multiplier=max(1,min(int(os.getenv("FETCH_MULTIPLIER","1") or "1"),8))
    themes=[
        IMPACT_QUERY,
        "politique diplomatie gouvernement élection relations internationales",
        "économie commerce énergie sanctions investissement",
        "sécurité conflit défense migration climat technologie",
        "santé société droits humains justice éducation",
        "environnement catastrophe agriculture alimentation eau",
        "industrie infrastructures transports numérique innovation",
        "ONU Union européenne sommet accord coopération aide humanitaire",
    ][:multiplier]
    countries=load_missing_countries()
    batch_size=max(1,int(os.getenv("COUNTRY_BATCH_SIZE","12") or "12"))
    if countries:
        offset=int(state.get("country_cursor",0))%len(countries)
        countries=(countries+countries)[offset:offset+min(batch_size,len(countries))]
    for country in countries:
        articles=[]
        for theme in themes:
            q=f'{country_query_name(country)} ({theme}) after:{start_date.isoformat()} before:{(end_date+timedelta(days=1)).isoformat()}'
            try: articles.extend(google_rss_query(q))
            except Exception as e:
                print("COUNTRY",country,theme,e,file=sys.stderr)
        seen=set()
        for art in articles:
            d=editorial_day(art["date"]); title=art["title"]
            if d<start_date or d>end_date or len(title)<22 or not country_title_matches(country,title): continue
            k=(d,key_title(title))
            if not k[1] or k in seen: continue
            seen.add(k); found.add(country)
            rows.append({"regions":["International"],"countries":[country],"period":"day","bucket":fr_date(d),"score":score(title),"category":category(title),"summary":title,"sources":[source_name(art["source"])],"url":art["url"],"published_at":art["date"].astimezone(PARIS).isoformat(),"origin":"rss"})
            if len(seen)>=10: break
    return rows,found

def update_country_coverage(found,now):
    if not COUNTRY_COVERAGE.exists() or not found: return
    try: data=json.loads(COUNTRY_COVERAGE.read_text(encoding="utf-8"))
    except Exception: return
    covered=set(data.get("covered_countries",[])); covered.update(found)
    missing=[c for c in data.get("missing_countries",[]) if c not in covered]
    data["date"]=fr_date(now.date()); data["covered_countries"]=sorted(covered); data["missing_countries"]=missing
    data["covered_count"]=len(covered); data["missing_count"]=len(missing); data["updated_at"]=now.isoformat()
    COUNTRY_COVERAGE.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")

def parse_bucket_date(bucket):
    months={m:i+1 for i,m in enumerate(FR_MONTHS)}; m=re.match(r"(\d+)\s+(\w+)\s+(\d{4})",bucket or "")
    if not m:return None
    return datetime(int(m.group(3)),months[m.group(2)],int(m.group(1))).date()

def build_generated(start_date,end_date):
    generated=[]
    multiplier=max(1,min(int(os.getenv("REGION_FETCH_MULTIPLIER",os.getenv("FETCH_MULTIPLIER","1")) or "1"),8))
    themes=[
        None,
        "politique diplomatie gouvernement élection relations internationales",
        "économie commerce énergie sanctions investissement",
        "sécurité conflit défense migration climat technologie",
        "santé société droits humains justice éducation",
        "environnement catastrophe agriculture alimentation eau",
        "industrie infrastructures transports numérique innovation",
        "ONU Union européenne sommet accord coopération aide humanitaire",
    ][:multiplier]
    all_dates=[start_date+timedelta(days=i) for i in range((end_date-start_date).days+1)]
    if os.getenv("BACKFILL_MONTH","0")=="1" and all_dates:
        batch_days=max(1,int(os.getenv("DAY_BATCH_SIZE","3") or "3"))
        state=load_monitor_state()
        offset=int(state.get("day_cursor",0))%len(all_dates)
        selected=(all_dates+all_dates)[offset:offset+min(batch_days,len(all_dates))]
        if end_date not in selected: selected.append(end_date)
        ranges=[(d,d) for d in dict.fromkeys(selected)]
    else:
        ranges=[(start_date,end_date)]
    for region in REGIONS:
        grouped=defaultdict(list); seen=set()
        for a,b in ranges:
            articles=[]
            for theme in themes:
                try:
                    if theme is None:
                        articles.extend(google_rss(region,a,b))
                    else:
                        base=REGIONS[region]
                        q=f'({base}) ({theme}) after:{a.isoformat()} before:{(b+timedelta(days=1)).isoformat()}'
                        articles.extend(google_rss_query(q))
                except Exception as e:
                    print("RSS",region,a,b,theme,e,file=sys.stderr)
            for art in articles:
                d=editorial_day(art["date"]); title=art["title"]
                if d<start_date or d>end_date or len(title)<22: continue
                k=(d,key_title(title))
                if not k[1] or k in seen: continue
                seen.add(k); grouped[d].append({"regions":[region],"period":"day","bucket":fr_date(d),"score":score(title),"category":category(title),"summary":title,"sources":[source_name(art["source"])],"url":art["url"],"published_at":art["date"].astimezone(PARIS).isoformat(),"origin":"rss"})
        for d in dict.fromkeys(a for a,_ in ranges):
            rows=sorted(grouped.get(d,[]),key=lambda x:x.get("published_at",""),reverse=True)
            generated.extend(rows)
    return generated

def main():
    now=datetime.now(PARIS); backfill=os.getenv("BACKFILL_MONTH","0")=="1"
    old=json.loads(DATA.read_text(encoding="utf-8")) if DATA.exists() else {"items":[]}
    start_date=now.date().replace(day=1) if backfill else now.date(); end_date=now.date()
    state=load_monitor_state()
    generated=build_generated(start_date,end_date)
    country_rows,found=country_backfill(start_date,end_date,state) if backfill else ([],set())
    generated.extend(country_rows)
    old_daily=[x for x in old.get("items",[]) if x.get("period")=="day"]
    # Conserver tout l'historique valide : les éléments existants ne sont jamais supprimés par la veille.
    existing={(x.get("bucket"),tuple(x.get("regions",[])),key_title(x.get("summary",""))) for x in old_daily}; fresh=[]
    for x in generated:
        k=(x.get("bucket"),tuple(x.get("regions",[])),key_title(x.get("summary","")))
        if k not in existing: fresh.append(x); existing.add(k)
    day_items=old_daily+fresh
    non_daily_manual=[x for x in old.get("items",[]) if x.get("period")!="day" and x.get("origin") not in ("rss","gdelt")]
    by_region=defaultdict(list)
    for x in day_items:
        d=parse_bucket_date(x.get("bucket"))
        if not d: continue
        for region in x.get("regions",[]): by_region[region].append((d,x))
    week_names=sorted({week_bucket(d) for rows in by_region.values() for d,_ in rows},key=lambda w: parse_bucket_date(w.replace("Semaine du ","")) or datetime.min.date(),reverse=True)
    month_names=sorted({month_bucket(d) for rows in by_region.values() for d,_ in rows},reverse=True)
    all_days=sorted({d for rows in by_region.values() for d,_ in rows},reverse=True); day_buckets=[fr_date(d) for d in all_days]
    coverage={}
    for i in range((end_date-start_date).days+1):
        d=start_date+timedelta(days=i); s=datetime.combine(d,dtime(0,0),PARIS); e=datetime.combine(d,dtime(23,59),PARIS)
        coverage[f"day:{fr_date(d)}"]=f"Journée civile : {s.strftime('%d/%m %H:%M')} → {e.strftime('%d/%m %H:%M')}"
    for w in week_names: coverage[f"week:{w}"]="Toutes les actualités conservées de cette semaine"
    for m in month_names: coverage[f"month:{m}"]="Toutes les actualités conservées de ce mois"
    out={"generated_at":now.isoformat(),"timezone":"Europe/Paris","window_rule":"Une date couvre de 00h00 à 23h59 heure de Paris.","target_per_region_per_day":60,"buckets":{"day":day_buckets,"week":week_names,"month":month_names},"coverage":coverage,"items":day_items+non_daily_manual}
    DATA.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
    update_country_coverage(found,now)
    save_monitor_state(state,now,
        country_step=int(os.getenv("COUNTRY_BATCH_SIZE","12")) if backfill else 0,
        day_step=int(os.getenv("DAY_BATCH_SIZE","3")) if backfill else 0)
    print("generated",len(generated),"daily items; countries found",len(found),"total",len(out["items"]),
          "cursors",state.get("country_cursor"),state.get("day_cursor"))

if __name__=="__main__": main()

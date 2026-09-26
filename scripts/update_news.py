#!/usr/bin/env python3
import json, os, re, sys, time, urllib.error, urllib.parse, urllib.request, xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
from datetime import datetime, timedelta, time as dtime
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"/"news.json"
COUNTRY_COVERAGE=ROOT/"data"/"country-coverage.json"
MONITOR_STATE=ROOT/"data"/"monitor-state.json"
PENDING_TRANSLATIONS=ROOT/"data"/"pending-translations.json"
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
SOURCE_LABELS=["Reuters","Associated Press","AP News","BBC","France 24","DW","Al Jazeera","Financial Times","The Economist","The Guardian","Euronews","POLITICO","Le Monde","AFP","NHK","Japan Times","Nikkei Asia","CNA","Channel NewsAsia","The Straits Times","Yonhap","The Korea Herald","The Hindu","The Indian Express","Dawn","The Jakarta Post","Kompas","Tempo","Bangkok Post","Focus Taiwan","Taipei Times","Rappler","The New York Times","The Washington Post","The Wall Street Journal","NPR","PBS NewsHour","ProPublica","Axios","Los Angeles Times","CBS News","CBC","The Globe and Mail","CTV News","El Universal","Folha","O Globo","Estadão","Agência Brasil","La Nación","Clarín","El Tiempo","El Espectador","El Comercio","La Tercera","News24","Daily Maverick","Mail & Guardian","SABC News","Nation Africa","The EastAfrican","Premium Times","Channels Television","Jeune Afrique","Africa Check","ABC News","ABC Australia","SBS News","Sydney Morning Herald","The Age","Australian Financial Review","RNZ","New Zealand Herald","Stuff","Newsroom","Daily Nation","The Standard Kenya","Citizen Digital","Monitor Uganda","The Independent Uganda","The Namibian","Namibian Sun","Mmegi","Zambia Daily Mail","Lusaka Times","The Herald Zimbabwe","NewsDay Zimbabwe","Agence Ivoirienne de Presse","Fraternité Matin","Cameroon Tribune","CRTV","Radio Okapi","Actualite.cd","Agence Nigérienne de Presse","Le Sahel","Sidwaya","L’Observateur Paalga","Inforpress","Seychelles News Agency","Seychelles Broadcasting Corporation","Kuensel","Kathmandu Post","The Himalayan Times","Maldives Independent","Daily Mirror Sri Lanka","Khaama Press","TOLOnews","UzA","AzerNews","Trend News Agency","Reforma","Excélsior","El Financiero","Prensa Libre","La Prensa Nicaragua","La Nación Costa Rica","La Estrella de Panamá","Listín Diario","Jamaica Gleaner","Trinidad and Tobago Guardian","Stabroek News","Kaieteur News","El Observador","El País Uruguay","ABC Color","Última Hora Paraguay","La República Perú","El Universo","Primicias","Fiji Times","Fiji Broadcasting Corporation","FBC News","NBC PNG","Post-Courier","The National PNG","Samoa Observer","Matangi Tonga","Solomon Star","SIBC","Vanuatu Daily Post","VBTC"]
IMPACT={10:["nuclear war","world war","invasion","state of emergency","coup attempt"],9:["missile","airstrike","air strike","war","sanctions","central bank","rate hike","rate cut","ceasefire","military attack","tariff","default","earthquake"],8:["strike","conflict","election","inflation","interest rate","trade war","oil","gas","military","security","summit","embargo","currency","recession","gdp","defence","defense"],7:["government","president","prime minister","parliament","diplomacy","trade","energy","bank","budget","protest","border","climate","flood","wildfire","technology"," ai "],6:["economy","economic","market","investment","export","import","migration","health","disease","infrastructure","shipping","food","agriculture"]}
CATEGORIES=[("Conflit",["war","missile","strike","attack","military","ceasefire","invasion"]),("Économie",["economy","inflation","gdp","market","rate","bank","budget","debt"]),("Énergie",["oil","gas","energy","lng","opec","pipeline"]),("Diplomatie",["summit","diplomacy","talks","treaty","sanctions"]),("Politique",["election","government","president","minister","parliament"]),("Sécurité",["security","terror","border","cyber"]),("Climat",["climate","flood","wildfire","storm","earthquake"]),("Technologie",["technology","artificial intelligence"," ai ","semiconductor","chip"])]
EN_WORDS={"the","and","with","from","after","against","says","will","amid","over","into","government","president","minister","election","war","trade","security","talks","deal","attack","military","court","bank","rate","climate"}
FR_WORDS={"le","la","les","des","du","de","un","une","et","avec","dans","pour","sur","après","contre","gouvernement","président","ministre","élection","guerre","commerce","sécurité"}

COUNTRY_REGIONS={
 "Europe": {"Albanie","Allemagne","Andorre","Autriche","Belgique","Biélorussie","Bosnie-Herzégovine","Bulgarie","Chypre","Croatie","Danemark","Espagne","Estonie","Finlande","France","Grèce","Hongrie","Irlande","Islande","Italie","Lettonie","Liechtenstein","Lituanie","Luxembourg","Macédoine du Nord","Malte","Moldavie","Monaco","Monténégro","Norvège","Pays-Bas","Pologne","Portugal","Roumanie","Royaume-Uni","Russie","Saint-Marin","Serbie","Slovaquie","Slovénie","Suède","Suisse","Tchéquie","Ukraine","Vatican"},
 "Asie": {"Afghanistan","Arabie saoudite","Arménie","Azerbaïdjan","Bahreïn","Bangladesh","Bhoutan","Birmanie","Brunei","Cambodge","Chine","Corée du Nord","Corée du Sud","Géorgie","Inde","Indonésie","Irak","Iran","Israël","Japon","Jordanie","Kazakhstan","Kirghizistan","Koweït","Laos","Liban","Malaisie","Maldives","Mongolie","Népal","Oman","Ouzbékistan","Pakistan","Palestine","Philippines","Qatar","Singapour","Sri Lanka","Syrie","Tadjikistan","Thaïlande","Timor oriental","Turkménistan","Turquie","Émirats arabes unis","Vietnam","Yémen"},
 "Amérique du Nord": {"Antigua-et-Barbuda","Bahamas","Barbade","Belize","Canada","Costa Rica","Cuba","Dominique","États-Unis","Grenade","Guatemala","Haïti","Honduras","Jamaïque","Mexique","Nicaragua","Panama","République dominicaine","Saint-Christophe-et-Niévès","Saint-Vincent-et-les-Grenadines","Sainte-Lucie","Salvador","Trinité-et-Tobago"},
 "Amérique du Sud": {"Argentine","Bolivie","Brésil","Chili","Colombie","Équateur","Guyana","Paraguay","Pérou","Suriname","Uruguay","Venezuela"},
 "Afrique": {"Afrique du Sud","Algérie","Angola","Bénin","Botswana","Burkina Faso","Burundi","Cameroun","Cap-Vert","Comores","Congo (RDC)","Congo (République du)","Côte d’Ivoire","Djibouti","Eswatini","Gabon","Gambie","Ghana","Guinée","Guinée-Bissau","Guinée équatoriale","Kenya","Lesotho","Libye","Libéria","Madagascar","Malawi","Mali","Maroc","Maurice","Mauritanie","Mozambique","Namibie","Niger","Nigeria","Ouganda","République centrafricaine","Rwanda","Sao Tomé-et-Principe","Seychelles","Sierra Leone","Somalie","Soudan","Soudan du Sud","Sénégal","Tanzanie","Tchad","Togo","Tunisie","Zambie","Zimbabwe","Égypte","Érythrée","Éthiopie"},
 "Océanie": {"Australie","Fidji","Kiribati","Micronésie","Nauru","Nouvelle-Zélande","Palaos","Papouasie-Nouvelle-Guinée","Samoa","Tonga","Tuvalu","Vanuatu","Îles Marshall","Îles Salomon"}
}
COUNTRY_TO_REGION={country:region for region,countries in COUNTRY_REGIONS.items() for country in countries}
TRANSLATION_CACHE={}
PENDING=[]

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
STATE_MEDIA_HINTS={
 "CRTV":"média public / contrôlé par l’État","Cameroon Tribune":"média public / contrôlé par l’État",
 "Agence Ivoirienne de Presse":"agence publique","Agence Nigérienne de Presse":"agence publique",
 "Le Sahel":"média public","Inforpress":"agence publique","Seychelles News Agency":"agence publique",
 "Seychelles Broadcasting Corporation":"média public","Fiji Broadcasting Corporation":"média public",
 "FBC News":"média public","NBC PNG":"média public","SIBC":"média public","VBTC":"média public",
 "UzA":"agence publique","NHK":"média public","BBC":"média public","France 24":"média public",
 "DW":"média public","CBC":"média public","ABC Australia":"média public","RNZ":"média public",
 "TOLOnews":"média privé","Khaama Press":"média privé",
}
def source_name(label):
    l=(label or "").strip()
    if "associated press" in l.lower() or l.lower()=="ap news": l="AP"
    if "abc.net.au" in l.lower(): l="ABC Australia"
    base=l or "Source"
    note=STATE_MEDIA_HINTS.get(base)
    return f"{base} ({note})" if note else base
def editorial_day(dt): return dt.astimezone(PARIS).date()
def looks_english(text):
    words=re.findall(r"[a-zà-ÿ]+",(text or "").lower())
    en=sum(w in EN_WORDS for w in words); fr=sum(w in FR_WORDS for w in words)
    return en>=2 and en>fr

def french_summary(text, meta=None):
    """Traduit/synthétise le titre source en français. Un échec est mis en attente, jamais publié en langue étrangère."""
    text=re.sub(r"\\s+"," ",text or "").strip()
    if not text: return None
    if text in TRANSLATION_CACHE: return TRANSLATION_CACHE[text]
    params={"client":"gtx","sl":"auto","tl":"fr","dt":"t","q":text}
    url="https://translate.googleapis.com/translate_a/single?"+urllib.parse.urlencode(params)
    try:
        req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 GeoClic/2.1"})
        with urllib.request.urlopen(req,timeout=15) as r:
            payload=json.loads(r.read().decode("utf-8","replace"))
        translated="".join(part[0] for part in payload[0] if part and part[0]).strip()
        if translated:
            TRANSLATION_CACHE[text]=translated
            return translated
    except Exception as e:
        print("TRANSLATION",e,file=sys.stderr)
    if meta is not None:
        PENDING.append({**meta,"original_summary":text})
    return None

def regions_for_countries(countries, importance):
    regs=[]
    for country in countries:
        region=COUNTRY_TO_REGION.get(country)
        if region and region not in regs: regs.append(region)
    if importance>=7: regs.append("International")
    return regs

GDELT_DOC="https://api.gdeltproject.org/api/v2/doc/doc"
GOOGLE_503_COUNT=0
GOOGLE_DISABLED=False
GDELT_429_COUNT=0
GDELT_DISABLED=False

def gdelt_query(query,maxrecords=250,start_date=None,end_date=None):
    global GDELT_429_COUNT,GDELT_DISABLED
    if GDELT_DISABLED: return []
    params={"query":query,"mode":"ArtList","format":"json","maxrecords":str(maxrecords),"sort":"DateDesc"}
    if start_date and end_date:
        start_dt=datetime.combine(start_date,dtime.min,tzinfo=PARIS).astimezone(UTC)
        end_dt=datetime.combine(end_date+timedelta(days=1),dtime.min,tzinfo=PARIS).astimezone(UTC)
        params["startdatetime"]=start_dt.strftime("%Y%m%d%H%M%S")
        params["enddatetime"]=end_dt.strftime("%Y%m%d%H%M%S")
    else:
        params["timespan"]="1d"
    url=GDELT_DOC+"?"+urllib.parse.urlencode(params)
    req=urllib.request.Request(url,headers={"User-Agent":"GeoClic/2.0 (+GitHub Actions)"})
    try:
        with urllib.request.urlopen(req,timeout=25) as r: data=json.loads(r.read().decode("utf-8","replace"))
    except urllib.error.HTTPError as e:
        if e.code==429:
            GDELT_429_COUNT+=1
            if GDELT_429_COUNT>=2:
                GDELT_DISABLED=True
                print("GDELT désactivé pour ce run après limitations 429; bascule Google News",file=sys.stderr)
            return []
        raise
    out=[]
    for art in data.get("articles",[]):
        title=(art.get("title") or "").strip()
        if not title: continue
        seen=art.get("seendate") or ""
        try: dt=datetime.strptime(seen[:14],"%Y%m%dT%H%M%S").replace(tzinfo=UTC)
        except Exception: dt=datetime.now(UTC)
        out.append({"title":title,"source":art.get("domain") or "GDELT","date":dt,"url":art.get("url") or ""})
    return out

def google_rss_query(query):
    global GOOGLE_503_COUNT,GOOGLE_DISABLED
    if GOOGLE_DISABLED: return []
    params={"q":query,"hl":"fr","gl":"FR","ceid":"FR:fr"}; url="https://news.google.com/rss/search?"+urllib.parse.urlencode(params)
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 GeoClic/2.0"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req,timeout=30) as r: root=ET.fromstring(r.read())
            break
        except urllib.error.HTTPError as e:
            if e.code not in (429,503): raise
            GOOGLE_503_COUNT+=1
            if GOOGLE_503_COUNT>=3:
                GOOGLE_DISABLED=True; print("Google News désactivé pour ce run après erreurs 429/503",file=sys.stderr); return []
            time.sleep(2**attempt*4)
    else: return []
    out=[]
    for item in root.findall(".//item"):
        title_el=item.find("title"); link_el=item.find("link"); date_el=item.find("pubDate"); src_el=item.find("source")
        if title_el is None or date_el is None: continue
        try: dt=parsedate_to_datetime(date_el.text)
        except: continue
        if dt.tzinfo is None: dt=dt.replace(tzinfo=UTC)
        title,fallback=clean_title(title_el.text or ""); src=(src_el.text if src_el is not None else fallback) or fallback
        if not trusted_source(src): continue
        out.append({"title":title,"source":src,"date":dt,"url":link_el.text if link_el is not None else ""})
    return out

def google_rss(region,start_date,end_date):
    base=REGIONS[region]
    q=f'({base}) when:1d' if region in ("Afrique","Amérique du Sud","Océanie") else f'({base}) ({IMPACT_QUERY}) when:1d'
    return google_rss_query(q)

def load_country_coverage():
    if not COUNTRY_COVERAGE.exists(): return {}
    try:
        return json.loads(COUNTRY_COVERAGE.read_text(encoding="utf-8"))
    except Exception as e:
        print("coverage",e,file=sys.stderr); return {}

def load_target_countries():
    """Retourne les 195 pays : tous restent inclus dans la rotation de veille."""
    data=load_country_coverage()
    return list(dict.fromkeys(data.get("missing_countries",[])+data.get("covered_countries",[])))

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

def global_country_discovery(start_date,end_date,countries):
    """Collecte mutualisée : quelques flux mondiaux, puis classification locale vers les 195 pays."""
    articles=[]
    # Flux thématiques larges en français : davantage de pays par appel qu'une requête pays par pays.
    queries=[
      "(politique OR gouvernement OR élection OR diplomatie OR sommet)",
      "(économie OR commerce OR énergie OR sanctions OR investissement)",
      "(sécurité OR conflit OR défense OR justice OR manifestation)",
      "(climat OR catastrophe OR environnement OR santé OR migration)",
      "(international OR monde OR coopération OR crise OR accord)",
    ]
    # Google News est volontairement mutualisé : deux appels pour tout le monde, pas 195.
    # Les fournisseurs sont interrogés en parallèle. Une source lente ne bloque plus les autres.
    jobs=[]
    with ThreadPoolExecutor(max_workers=8) as pool:
        if not GOOGLE_DISABLED:
            jobs += [(pool.submit(google_rss_query,q+" when:1d"),"GOOGLE GLOBAL") for q in queries]
        if not GDELT_DISABLED:
            jobs += [(pool.submit(gdelt_query,q,150,start_date,end_date),"GDELT GLOBAL") for q in queries]
        for future,label in jobs:
            try: articles.extend(future.result())
            except Exception as e: print(label,e,file=sys.stderr)
    rows=[]; found=set(); seen=set()
    for art in articles:
        d=editorial_day(art["date"]); title=art.get("title","")
        if d<start_date or d>end_date or len(title)<22: continue
        matched=[country for country in countries if country_title_matches(country,title)]
        if not matched: continue
        k=(d,key_title(title))
        if not k[1] or k in seen: continue
        seen.add(k); found.update(matched)
        s=score(title)
        summary=french_summary(title,{"countries":matched,"date":fr_date(d),"source":source_name(art["source"]),"url":art["url"]})
        if not summary: continue
        regions=regions_for_countries(matched,s)
        rows.append({"regions":regions,"countries":matched,"period":"day","bucket":fr_date(d),"score":s,"category":category(summary),"summary":summary,"sources":[source_name(art["source"])],"url":art["url"],"published_at":art["date"].astimezone(PARIS).isoformat(),"origin":"global"})
    return rows,found

def country_backfill(start_date,end_date,state):
    rows=[]; found=set()
    themes=["politique OR diplomatie OR gouvernement OR élection OR économie OR sécurité OR conflit OR défense OR migration OR climat OR santé OR société OR justice OR environnement OR catastrophe OR énergie OR technologie OR coopération"]
    all_countries=load_target_countries()
    # Collecte mondiale mutualisée en premier : tous les pays sont traités de manière égale.
    global_rows,global_found=global_country_discovery(start_date,end_date,all_countries)
    rows.extend(global_rows); found.update(global_found)
    # Traitement par petits lots persistants : chaque run écrit son lot avant que le suivant ne soit traité.
    # Le lot ciblé complète la collecte mondiale sans priorité liée au niveau de couverture.
    batch_size=max(1,int(os.getenv("COUNTRY_BATCH_SIZE","10") or "10"))
    ordered=list(all_countries)
    if ordered:
        offset=int(state.get("country_cursor",0))%len(ordered)
        countries=(ordered+ordered)[offset:offset+min(batch_size,len(ordered))]
    else:
        countries=[]
    # Un budget couvre tout le lot : Google prend automatiquement le relais lorsque GDELT est limité.
    google_budget=max(0,int(os.getenv("GOOGLE_FALLBACK_BUDGET",str(batch_size)) or str(batch_size)))
    for country in countries:
        articles=[]
        q=f'{country_query_name(country)} (government OR election OR economy OR security OR conflict OR diplomacy OR climate OR energy OR health OR justice)'
        if not GDELT_DISABLED:
            try: articles.extend(gdelt_query(q,100,start_date,end_date))
            except Exception as e: print("GDELT COUNTRY",country,e,file=sys.stderr)
        # Google News n'est plus la source primaire. Il ne sert qu'aux trous, avec budget et coupe-circuit 429/503.
        # GDELT sert à découvrir les articles, même lorsque le titre est dans une autre langue.
        # Le fallback Google est déclenché tant qu'aucun titre français publiable n'a été trouvé.
        usable=[a for a in articles if country_title_matches(country,a.get("title",""))]
        if (not usable or GDELT_DISABLED) and google_budget>0 and not GOOGLE_DISABLED:
            google_budget-=1
            # Une seule requête large par pays : beaucoup plus rapide et moins exposée aux 429/503
            # que la boucle historique sur de nombreux thèmes.
            try:
                articles.extend(google_rss_query(f'{country_query_name(country)} (actualité OR politique OR économie OR sécurité OR diplomatie OR climat OR santé) when:1d'))
            except Exception as e:
                print("GOOGLE FALLBACK",country,e,file=sys.stderr)
            time.sleep(0.15)
        seen=set()
        for art in articles:
            d=editorial_day(art["date"]); title=art["title"]
            if d<start_date or d>end_date or len(title)<22 or not country_title_matches(country,title): continue
            k=(d,key_title(title))
            if not k[1] or k in seen: continue
            seen.add(k)
            s=score(title)
            summary=french_summary(title,{"countries":[country],"date":fr_date(d),"source":source_name(art["source"]),"url":art["url"]})
            if not summary: continue
            found.add(country)
            rows.append({"regions":regions_for_countries([country],s),"countries":[country],"period":"day","bucket":fr_date(d),"score":s,"category":category(summary),"summary":summary,"sources":[source_name(art["source"])],"url":art["url"],"published_at":art["date"].astimezone(PARIS).isoformat(),"origin":"gdelt" if "GDELT" in source_name(art["source"]) else "rss"})
    return rows,found

def update_country_coverage(found,now):
    if not COUNTRY_COVERAGE.exists(): return
    try: data=json.loads(COUNTRY_COVERAGE.read_text(encoding="utf-8"))
    except Exception: return
    targets=list(dict.fromkeys(data.get("covered_countries",[])+data.get("missing_countries",[])))
    # Cumul entre les lots du même jour ; remise à zéro au changement de journée.
    # Normaliser les noms pour éviter qu'une variante d'accent/casse empêche le comptage.
    canonical={key_title(c):c for c in targets}
    previous=set(data.get("covered_countries",[])) if data.get("date")==fr_date(now.date()) else set()
    normalized_found={canonical.get(key_title(c),c) for c in found}
    covered=sorted(previous|normalized_found)
    covered_set={key_title(c) for c in covered}
    missing=[c for c in targets if key_title(c) not in covered_set]
    data["date"]=fr_date(now.date()); data["target_countries"]=len(targets)
    previous_checked=set(data.get("checked_countries",[])) if data.get("date")==fr_date(now.date()) else set()
    checked=sorted(previous_checked|set(found))
    data["checked_count"]=len(checked); data["checked_countries"]=checked
    data["covered_countries"]=covered; data["missing_countries"]=missing
    data["covered_count"]=len(covered); data["missing_count"]=len(missing); data["updated_at"]=now.isoformat()
    data["rule"]="Couverture cumulative sur la journée civile Europe/Paris : les 195 pays restent dans la rotation ; covered = au moins une actualité du jour publiée ; missing = pays sans actualité publiée à cet instant. Plusieurs articles distincts par pays sont autorisés."
    COUNTRY_COVERAGE.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

def parse_bucket_date(bucket):
    months={m:i+1 for i,m in enumerate(FR_MONTHS)}; m=re.match(r"(\d+)\s+(\w+)\s+(\d{4})",bucket or "")
    if not m:return None
    return datetime(int(m.group(3)),months[m.group(2)],int(m.group(1))).date()

def build_generated(start_date,end_date):
    generated=[]
    themes=[None,"politique OR diplomatie OR économie OR sécurité OR conflit OR élection OR climat OR énergie"]
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
                        q=f'({base}) ({theme}) when:1d'
                        articles.extend(google_rss_query(q))
                except Exception as e:
                    print("RSS",region,a,b,theme,e,file=sys.stderr)
            # GDELT complète les continents lorsque Google News est limité ou incomplet.
            if not GDELT_DISABLED:
                try: articles.extend(gdelt_query(f'({REGIONS[region]})',200,a,b))
                except Exception as e: print("GDELT REGION",region,a,b,e,file=sys.stderr)
            for art in articles:
                d=editorial_day(art["date"]); title=art["title"]
                if d<start_date or d>end_date or len(title)<22: continue
                k=(d,key_title(title))
                if not k[1] or k in seen: continue
                summary=french_summary(title,{"regions":[region],"date":fr_date(d),"source":source_name(art["source"]),"url":art["url"]})
                if not summary: continue
                seen.add(k); grouped[d].append({"regions":[region],"period":"day","bucket":fr_date(d),"score":score(title),"category":category(summary),"summary":summary,"sources":[source_name(art["source"])],"url":art["url"],"published_at":art["date"].astimezone(PARIS).isoformat(),"origin":"rss"})
        for d in dict.fromkeys(a for a,_ in ranges):
            rows=sorted(grouped.get(d,[]),key=lambda x:x.get("published_at",""),reverse=True)
            generated.extend(rows)
    return generated

def main():
    now=datetime.now(PARIS); backfill=os.getenv("BACKFILL_MONTH","0")=="1"
    old=json.loads(DATA.read_text(encoding="utf-8")) if DATA.exists() else {"items":[]}
    include_previous=os.getenv("INCLUDE_PREVIOUS_DAY","0")=="1"
    start_date=now.date().replace(day=1) if backfill else (now.date()-timedelta(days=1) if include_previous else now.date()); end_date=now.date()
    state=load_monitor_state()
    generated=build_generated(start_date,end_date)
    country_rows,found=country_backfill(start_date,end_date,state)
    generated.extend(country_rows)
    old_daily=[x for x in old.get("items",[]) if x.get("period")=="day"]
    # Conserver tout l'historique valide : les éléments existants ne sont jamais supprimés par la veille.
    existing={(x.get("bucket"),tuple(x.get("regions",[])),key_title(x.get("summary",""))) for x in old_daily}; fresh=[]
    for x in generated:
        k=(x.get("bucket"),tuple(x.get("regions",[])),key_title(x.get("summary","")))
        if k not in existing: fresh.append(x); existing.add(k)
    day_items=old_daily+fresh
    # Garde-fous d'affichage appliqués aussi à l'historique existant :
    # aucun texte anglais publié et International réservé aux scores >= 7.
    cleaned=[]
    for x in day_items:
        if looks_english(x.get("summary","")):
            continue
        y=dict(x)
        regs=list(y.get("regions",[]) or [])
        if int(y.get("score",0) or 0)<7:
            regs=[r for r in regs if r!="International"]
        y["regions"]=regs
        cleaned.append(y)
    day_items=cleaned
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
    # Les articles dont la traduction a échoué sont conservés pour un prochain passage.
    previous_pending=[]
    if PENDING_TRANSLATIONS.exists():
        try: previous_pending=json.loads(PENDING_TRANSLATIONS.read_text(encoding="utf-8")).get("items",[])
        except Exception: previous_pending=[]
    pending_by_url={x.get("url") or (x.get("date","")+x.get("original_summary","")):x for x in previous_pending+PENDING}
    PENDING_TRANSLATIONS.write_text(json.dumps({"updated_at":now.isoformat(),"items":list(pending_by_url.values())},ensure_ascii=False,indent=2)+"\\n",encoding="utf-8")
    # Reconstituer aussi la couverture à partir de toutes les actualités déjà
    # conservées pour aujourd'hui : un pays trouvé par un lot précédent reste couvert.
    today_bucket=fr_date(now.date())
    for item in day_items:
        if item.get("bucket")==today_bucket:
            found.update(item.get("countries",[]))
    update_country_coverage(found,now)
    save_monitor_state(state,now,
        country_step=int(os.getenv("COUNTRY_BATCH_SIZE","12")),
        day_step=int(os.getenv("DAY_BATCH_SIZE","3")) if backfill else 0)
    print("generated",len(generated),"daily items; countries found",len(found),"total",len(out["items"]),
          "cursors",state.get("country_cursor"),state.get("day_cursor"))

if __name__=="__main__": main()

#!/usr/bin/env python3
import base64, html as html_lib
import json, os, re, sys, time, unicodedata, urllib.error, urllib.parse, urllib.request, xml.etree.ElementTree as ET
from difflib import SequenceMatcher
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
from datetime import datetime, timedelta, time as dtime
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from zoneinfo import ZoneInfo

try:
    import httpx
except ImportError:  # urllib fallback for local environments without HTTP/2 extras.
    httpx=None

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
MAJOR_NEWS_QUERIES=[
  "(war OR invasion OR missile OR airstrike OR ceasefire OR coup OR military escalation OR armed conflict)",
  "(sanctions OR state of emergency OR diplomatic crisis OR peace agreement OR treaty OR national election)",
  "(earthquake OR tsunami OR major flood OR wildfire OR disaster OR energy crisis OR sovereign default)",
]
SOURCE_LABELS=["Reuters","Associated Press","AP News","BBC","France 24","DW","Al Jazeera","Financial Times","The Economist","The Guardian","Euronews","POLITICO","Le Monde","AFP","NHK","Japan Times","Nikkei Asia","CNA","Channel NewsAsia","The Straits Times","Yonhap","The Korea Herald","The Hindu","The Indian Express","Dawn","The Jakarta Post","Kompas","Tempo","Bangkok Post","Focus Taiwan","Taipei Times","Rappler","The New York Times","The Washington Post","The Wall Street Journal","NPR","PBS NewsHour","ProPublica","Axios","Los Angeles Times","CBS News","CBC","The Globe and Mail","CTV News","El Universal","Folha","O Globo","Estadão","Agência Brasil","La Nación","Clarín","El Tiempo","El Espectador","El Comercio","La Tercera","News24","Daily Maverick","Mail & Guardian","SABC News","Nation Africa","The EastAfrican","Premium Times","Channels Television","Jeune Afrique","Africa Check","ABC News","ABC Australia","SBS News","Sydney Morning Herald","The Age","Australian Financial Review","RNZ","New Zealand Herald","Stuff","Newsroom","Daily Nation","The Standard Kenya","Citizen Digital","Monitor Uganda","The Independent Uganda","The Namibian","Namibian Sun","Mmegi","Zambia Daily Mail","Lusaka Times","The Herald Zimbabwe","NewsDay Zimbabwe","Agence Ivoirienne de Presse","Fraternité Matin","Cameroon Tribune","CRTV","Radio Okapi","Actualite.cd","Agence Nigérienne de Presse","Le Sahel","Sidwaya","L’Observateur Paalga","Inforpress","Seychelles News Agency","Seychelles Broadcasting Corporation","Kuensel","Kathmandu Post","The Himalayan Times","Maldives Independent","Daily Mirror Sri Lanka","Khaama Press","TOLOnews","UzA","AzerNews","Trend News Agency","Reforma","Excélsior","El Financiero","Prensa Libre","La Prensa Nicaragua","La Nación Costa Rica","La Estrella de Panamá","Listín Diario","Jamaica Gleaner","Trinidad and Tobago Guardian","Stabroek News","Kaieteur News","El Observador","El País Uruguay","ABC Color","Última Hora Paraguay","La República Perú","El Universo","Primicias","Fiji Times","Fiji Broadcasting Corporation","FBC News","NBC PNG","Post-Courier","The National PNG","Samoa Observer","Matangi Tonga","Solomon Star","SIBC","Vanuatu Daily Post","VBTC"]
IMPACT={
 10:["guerre nucléaire","guerre mondiale","emploi de l’arme nucléaire","attaque nucléaire","invasion générale","coup d’état réussi","renversement du gouvernement","nuclear war","world war"],
 9:["guerre","invasion","frappe aérienne","frappe de missile","attaque militaire","cessez-le-feu","mobilisation militaire","état d’urgence","coup d’état","sanctions internationales","défaut souverain","séisme majeur","missile","airstrike","ceasefire","military attack","sanctions"],
 8:["conflit armé","inflation","taux directeur","banque centrale","récession","embargo","sommet international","accord de paix","traité","crise politique","crise diplomatique","crise énergétique","pétrole","gaz","défense nationale","ministère de la défense","dépenses de défense","politique de défense","sécurité nationale","tarifs douaniers","droits de douane","réduction tarifaire","réductions tarifaires","conflict","interest rate","central bank","recession","summit","embargo","oil","gas","national defense","defense ministry","defence ministry","defense spending"],
 7:["diplomatie","commerce international","frontière internationale","migration internationale","prix de l’énergie","marché de l’énergie","politique énergétique","sécurité énergétique","production électrique","réseau électrique","électricité","énergies renouvelables","climat","inondation majeure","feu de forêt","catastrophe naturelle","cyberattaque","technologie stratégique","régulation de l’intelligence artificielle","loi sur l’intelligence artificielle","semi-conducteur","puces électroniques","accord commercial","diplomacy","international trade","international border","international migration","energy prices","energy market","energy policy","energy security","electricity","renewable energy","climate","major flood","wildfire","cyberattack","ai regulation","semiconductor","chip export"],
 6:["gouvernement","premier ministre","parlement","budget de l’état","manifestation","migration","frontière","économie","marché","investissement","exportation","importation","santé publique","épidémie","infrastructure","transport maritime","agriculture","justice","government","prime minister","parliament","budget","protest","migration","border","economic","market","investment","export","import","health","disease","infrastructure","shipping","agriculture"],
 5:["politique locale","administration","entreprise","société","politics","business","society"]
}
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
REJECTION_STATS=defaultdict(int)
DISCOVERY_STATS=defaultdict(int)

# Désambiguïsation éditoriale des dirigeants fréquemment cités. Cette table
# n'ajoute aucun fait à l'événement : elle explicite uniquement fonction et pays.
LEADER_LABELS={
    "Edi Rama":"le Premier ministre Edi Rama (Albanie)",
    "Emmanuel Macron":"le président Emmanuel Macron (France)",
    "Donald Trump":"le président Donald Trump (États-Unis)",
    "Xi Jinping":"le président Xi Jinping (Chine)",
    "Vladimir Poutine":"le président Vladimir Poutine (Russie)",
    "Volodymyr Zelensky":"le président Volodymyr Zelensky (Ukraine)",
    "Giorgia Meloni":"la présidente du Conseil Giorgia Meloni (Italie)",
    "Friedrich Merz":"le chancelier Friedrich Merz (Allemagne)",
    "Keir Starmer":"le Premier ministre Keir Starmer (Royaume-Uni)",
    "Narendra Modi":"le Premier ministre Narendra Modi (Inde)",
    "Benjamin Netanyahu":"le Premier ministre Benjamin Netanyahu (Israël)",
    "Jim Chalmers":"le trésorier fédéral Jim Chalmers (Australie)",
    "Keith Kellogg":"le général Keith Kellogg (États-Unis)",
    "Pete Hegseth":"le secrétaire à la Défense Pete Hegseth (États-Unis)",
    "Israel Katz":"le ministre de la Défense Israel Katz (Israël)",
    "Sergueï Lavrov":"le ministre russe des Affaires étrangères Sergueï Lavrov (Russie)",
    "Sergei Lavrov":"le ministre russe des Affaires étrangères Sergueï Lavrov (Russie)",
    "Serghei Lavrov":"le ministre russe des Affaires étrangères Sergueï Lavrov (Russie)",
    "Marco Rubio":"le secrétaire d’État Marco Rubio (États-Unis)",
    "Christine Lagarde":"la présidente de la Banque centrale européenne Christine Lagarde (Union européenne)",
}

PERSON_SURNAME_ALIASES={
    "Trump":("Donald Trump","président"),
    "Xi":("Xi Jinping","président"),
    "Macron":("Emmanuel Macron","président"),
    "Poutine":("Vladimir Poutine","président"),
    "Putin":("Vladimir Poutine","président"),
    "Zelensky":("Volodymyr Zelensky","président"),
    "Netanyahu":("Benjamin Netanyahu","Premier ministre"),
    "Rama":("Edi Rama","Premier ministre"),
    "Starmer":("Keir Starmer","Premier ministre"),
    "Merz":("Friedrich Merz","chancelier"),
    "Modi":("Narendra Modi","Premier ministre"),
    "Chalmers":("Jim Chalmers","trésorier fédéral"),
    "Hegseth":("Pete Hegseth","secrétaire à la Défense"),
    "Katz":("Israel Katz","ministre de la Défense"),
    "Lavrov":("Sergueï Lavrov","ministre des Affaires étrangères"),
    "Rubio":("Marco Rubio","secrétaire d’État"),
    "Lagarde":("Christine Lagarde","présidente de la Banque centrale européenne"),
}

def enrich_leader_context(text):
    """Précise fonction et pays d'un responsable connu sans inventer le contenu de la source."""
    out=(text or "").strip()

    # Noms complets : normaliser un titre éventuel.
    for name,label in LEADER_LABELS.items():
        if name.lower() not in out.lower() or label.lower() in out.lower():
            continue
        pattern=r"(?i)(?:le |la )?(?:président(?:e)?|premier ministre|première ministre|chancelier|présidente du conseil|trésorier(?: fédéral)?|ministre des finances|général|ministre des affaires étrangères|secrétaire à la défense|ministre de la défense|secrétaire d['’]état|présidente de la banque centrale européenne)?\s*"+re.escape(name)+r"(?:\s*\([^)]+\))?"
        out=re.sub(pattern,label,out,count=1)

    # Noms de famille seuls, très fréquents dans les titres.
    for alias,(full_name,role) in PERSON_SURNAME_ALIASES.items():
        label=LEADER_LABELS.get(full_name)
        if not label or label.lower() in out.lower() or not re.search(r"(?i)\b"+re.escape(alias)+r"\b",out):
            continue
        # Un nom de famille précédé d'un autre prénom propre n'est pas automatiquement
        # le responsable connu (ex. « Nirav Modi » n'est pas Narendra Modi).
        if full_name.lower() not in out.lower() and re.search(r"\b[A-ZÀ-Ý][a-zà-ÿ'’-]+\s+"+re.escape(alias)+r"\b",out):
            continue
        # Prépositions françaises : « de Trump » -> « du président Donald Trump (États-Unis) ».
        if role=="président":
            bare=label[3:] if label.lower().startswith("le ") else label
            out=re.sub(r"(?i)\bde\s+(?:le\s+président\s+)?"+re.escape(alias)+r"\b","du "+bare,out,count=1)
            out=re.sub(r"(?i)\bà\s+(?:le\s+président\s+)?"+re.escape(alias)+r"\b","au "+bare,out,count=1)
        if label.lower() in out.lower():
            continue
        pattern=r"(?i)(?:le |la )?(?:président(?:e)?|premier ministre|première ministre|chancelier|trésorier(?: fédéral)?|ministre des finances|secrétaire à la défense|ministre de la défense|ministre des affaires étrangères)?\s*\b"+re.escape(alias)+r"\b"
        out=re.sub(pattern,label,out,count=1)
    # Nettoyer les répétitions héritées d'anciens enrichissements.
    for name,label in LEADER_LABELS.items():
        first=name.split()[0]
        out=re.sub(r"(?i)\\b"+re.escape(first)+r"\\s+"+re.escape(label),label,out)
        out=re.sub(r"(?i)\\b(?:le\\s+)?président\\s+"+re.escape(first)+r"\\s+"+re.escape(label),label,out)
        out=out.replace(f"({label})",label)

    # Nettoyer les contractions/espaces créés par la normalisation des titres.
    out=out.replace("\\1 ","")
    out=re.sub(r"(?i)\bdu\s+le\s+président\b","du président",out)
    out=re.sub(r"(?i)\bde\s+le\s+président\b","du président",out)
    out=re.sub(r"(?i)\bdu\s+la\s+présidente\b","de la présidente",out)
    out=re.sub(r"(?i)\bde(?:le)?\s+président\b","du président",out)
    out=re.sub(r"(?i)\bavec(?:le)\s+président\b","avec le président",out)
    out=re.sub(r"(?i)\bselon(?:le)\s+président\b","selon le président",out)
    out=re.sub(r"(?i)\bdu\s+le\s+Premier ministre\b","du Premier ministre",out)
    out=re.sub(r"(?i)\bde\s+le\s+Premier ministre\b","du Premier ministre",out)
    # Réparer les mots accolés au libellé ajouté : « réunionle président ».
    out=re.sub(r"(?<=[A-Za-zÀ-ÿ])(?=(?:le|la)\s+(?:président|présidente|Premier ministre|Première ministre|chancelier|trésorier fédéral|général)\b)"," ",out)
    out=re.sub(r"(?i)\badministration\s+le président\b","administration du président",out)
    out=re.sub(r"(?i)\bla raison est la guerre du président\b","la raison est attribuée à la guerre selon le président",out)
    for country in COUNTRY_TO_REGION:
        duplicated=f"({country}) ({country})"
        while duplicated in out:
            out=out.replace(duplicated,f"({country})")
    # Après suppression d'un pays doublé, réparer les transitions entre deux responsables.
    out=re.sub(
        r"(?i)(ancien(?:ne)?\s+(?:émissaire|envoyé spécial)\s+du président\s+[^()]+\([^)]+\))\s+(le président\s+)",
        r"\1 : \2",out
    )
    out=re.sub(
        r"(?i)\bréunion\s+(le président\s+[^()]+\([^)]+\))\s*-\s*(le président\s+[^()]+\([^)]+\))",
        r"réunion entre \1 et \2",out
    )
    out=re.sub(
        r"(?i)(ancien(?:ne)?\s+(?:émissaire|envoyé spécial)\s+du président\s+[^()]+\([^)]+\))\s+(le président\s+)",
        r"\1 : \2",out
    )
    # Repasser après dédoublonnage des parenthèses.
    out=re.sub(
        r"(?i)(ancien(?:ne)?\s+(?:émissaire|envoyé spécial)\s+du président\s+[^()]+\([^)]+\))\s+(le président\s+)",
        r"\1 : \2",out
    )
    out=re.sub(r"([,:;.!?])(?=[A-Za-zÀ-ÿ])",r"\1 ",out)
    out=re.sub(r"\s+"," ",out).strip()
    # Normaliser les translittérations et les répétitions introduites par certains titres.
    out=re.sub(r"(?i)\b(?:Sergei|Sergey)\s+Lavrov\b","Sergueï Lavrov",out)
    out=re.sub(
        r"(?i)\b(?:le\s+)?président\s+Donald\s+(?:le\s+président\s+Donald\s+)+Trump\s*\(États-Unis\)",
        "le président Donald Trump (États-Unis)",out
    )
    out=re.sub(
        r"(?i)\b(?:le\s+)?président\s+Donald\s+Trump\s*\(États-Unis\)\s+(?:le\s+)?président\s+Donald\s+Trump\s*\(États-Unis\)",
        "le président Donald Trump (États-Unis)",out
    )
    out=re.sub(r"(?i)\ble président(?:\s+[a-zà-ÿ-]+)?\s+le président\b","le président",out)
    out=re.sub(r"(?i)\ble Premier ministre(?:\s+[a-zà-ÿ-]+)?\s+le Premier ministre\b","le Premier ministre",out)
    out=re.sub(r"(?i)\bla présidente(?:\s+[a-zà-ÿ-]+)?\s+la présidente\b","la présidente",out)
    for alias,(full_name,_role) in PERSON_SURNAME_ALIASES.items():
        label=LEADER_LABELS.get(full_name)
        if not label:
            continue
        known_first=full_name.split()[0].lower()
        pattern=r"\b([A-ZÀ-Ý][a-zà-ÿ'’-]+)\s+"+re.escape(label)
        def _restore_other_name(m, alias=alias, known_first=known_first):
            first=m.group(1)
            return m.group(0) if first.lower()==known_first else f"{first} {alias}"
        out=re.sub(pattern,_restore_other_name,out)
    if out:
        out=out[0].upper()+out[1:]
    return out

# Lieux infranationaux fréquemment rencontrés. Ajouter le pays seulement lorsque
# le lieu est suffisamment non ambigu et que le pays n'est pas déjà explicite.
PLACE_COUNTRIES={
    "Aceh du Sud-Est":"Indonésie",
    "Aceh Tenggara":"Indonésie",
    "Banda Aceh":"Indonésie",
    "Aceh":"Indonésie",
    "Tigré":"Éthiopie",
    "Tigray":"Éthiopie",
    "Darfour":"Soudan",
    "Gaza":"Palestine",
    "Cisjordanie":"Palestine",
    "Taïwan":"Taïwan",
    "Kitchener":"Canada",
    "Ontario":"Canada",
    "Colombie-Britannique":"Canada",
    "British Columbia":"Canada",
    "Californie":"États-Unis",
    "California":"États-Unis",
    "Ohio":"États-Unis",
    "Dijon":"France",
    "Berlin":"Allemagne",
    "Rhénanie du Nord-Westphalie":"Allemagne",
    "Odisha":"Inde",
    "Dubaï":"Émirats arabes unis",
    "Dubai":"Émirats arabes unis",
}

def enrich_place_context(text):
    """Ajoute le pays d'un lieu infranational connu lorsqu'il n'est pas déjà précisé."""
    out=(text or "").strip()
    # Les noms les plus longs d'abord pour éviter que « Aceh » capture « Aceh du Sud-Est ».
    for place,country in sorted(PLACE_COUNTRIES.items(),key=lambda kv:len(kv[0]),reverse=True):
        if not re.search(r"(?i)\b"+re.escape(place)+r"\b",out):
            continue
        if re.search(r"(?i)"+re.escape(place)+r"\s*\("+re.escape(country)+r"\)",out):
            continue
        if re.search(r"(?i)\b"+re.escape(country)+r"\b",out):
            continue
        out=re.sub(r"(?i)\b"+re.escape(place)+r"\b",lambda m:f"{m.group(0)} ({country})",out,count=1)
    return out

def enrich_editorial_context(text):
    return enrich_place_context(enrich_leader_context(text))

def fr_date(d): return f"{d.day} {FR_MONTHS[d.month-1]} {d.year}"
def month_bucket(d): return f"{FR_MONTHS[d.month-1].capitalize()} {d.year}"
def week_bucket(d):
    mon=d-timedelta(days=d.weekday()); sun=mon+timedelta(days=6)
    return f"Semaine du {fr_date(mon)} au {fr_date(sun)}"
def is_french_2027_presidential(text):
    """Isole la campagne présidentielle française 2027 de la veille géopolitique générale."""
    t=" "+(text or "").lower()+" "
    france=("france" in t or "français" in t or "française" in t)
    presidential=("présidentielle" in t or "présidentiel" in t or "présidence" in t)
    campaign=("2027" in t or "candidat" in t or "candidature" in t or "primaire" in t or "programme" in t)
    return presidential and campaign and (france or "2027" in t)

def clean_summary_text(text):
    """Retire le bruit éditorial/SEO sans inventer d'information."""
    raw="".join(ch for ch in (text or "") if unicodedata.category(ch)!="Cf")
    out=re.sub(r"\\s+"," ",raw).strip()
    # Suffixes publicitaires ou de portail qui n'apportent rien au fait.
    out=re.sub(r"(?i)\\s*\\|\\s*actualités gratuites en ligne.*$","",out)
    out=re.sub(r"(?i)\\s*[–—-]\\s*journal approfondi.*$","",out)
    out=re.sub(r"(?i)\\s*[–—-]\\s*dernières nouvelles.*$","",out)
    boilerplate_markers=(
      "en l'absence d'un accord écrit avec",
      "en l’absence d’un accord écrit avec",
      "vous pouvez extraire un maximum de",
      "tous droits réservés",
      "all rights reserved",
      "reproduction interdite"
    )
    lower=out.lower()
    cuts=[lower.find(marker) for marker in boilerplate_markers if lower.find(marker)>=0]
    if cuts:
        out=out[:min(cuts)].rstrip(" .;:-")
    out=re.sub(r"(?i)\bdu\s+le\s+président\b","du président",out)
    out=re.sub(r"(?i)\bde\s+le\s+président\b","du président",out)
    out=re.sub(r"(?i)\bDonald\s+le\s+président\s+Donald\s+Trump\b","Donald Trump",out)
    out=re.sub(r"(?i)\bLarmée\b","L’armée",out)
    out=re.sub(r"(?i)\blemprise\b","l’emprise",out)
    out=re.sub(r"(?i)\blIran\b","l’Iran",out)
    out=re.sub(r"(?i)\bdOrmuz\b","d’Ormuz",out)
    out=re.sub(r"(?i)\s*Lire l'article complet sur [^.]+\.?$","",out)
    out=re.sub(r"(?i)\s*Lire l’article complet sur [^.]+\.?$","",out)
    out=re.sub(
        r"(?i)La Russie n’a pas reçu de signaux encourageants de la part des États-Unis concernant les propriétés diplomatiques\s+le ministre russe des Affaires étrangères Sergueï Lavrov \(Russie\)",
        "Le ministre russe des Affaires étrangères Sergueï Lavrov (Russie) affirme que la Russie n’a pas reçu de signaux encourageants des États-Unis concernant les propriétés diplomatiques",
        out
    )
    out=re.sub(
        r"(?i)\ble président russe\s+le président Vladimir Poutine \(Russie\)",
        "le président Vladimir Poutine (Russie)",out
    )
    out=re.sub(r"\s+,",",",out)
    out=re.sub(r"(?i)\bU\.\s*S\.\b","États-Unis",out)
    out=re.sub(r"(?i)\bEtats-Unis\b","États-Unis",out)
    out=re.sub(r"(?i)\bMoyen\s*-\s*Orient\b","Moyen-Orient",out)
    out=re.sub(r"(?i)\bDUBAI\s+—\s+","Dubaï (Émirats arabes unis) — ",out)
    out=re.sub(r"(?i)\s*\|\s*Actualités sur les conflits","",out)
    out=re.sub(r"(?i)\bLecture de trois minutes\b","",out)
    out=re.sub(r"(?i)\s*\|\s*GDA\s*[–—-]\s*Groupe de journaux américain","",out)
    out=re.sub(r"\.{3,}","…",out)
    out=re.sub(r"\s+"," ",out).strip()
    return out.strip(" |–—-")

def is_market_listing_noise(text):
    """Détecte fiches boursières/cotations qui ne décrivent aucun événement."""
    raw=clean_summary_text(text)
    t=" "+raw.lower()+" "
    listing_terms=(
      " activité |"," cotation "," cours de l'action "," cours de l’action ",
      " fiche valeur "," action |"," isin "," wkn "," ticker "," valorisation ",
      " pdmr "," director/pdmr "," director / actionnariat "," actionnariat pdmr ",
      " annonce réglementaire "," regulatory announcement "," shareholding announcement "
    )
    code_like=bool(re.search(r"\\b(?:HK|US|DE|FR|GB|LU|CH)[A-Z0-9]{8,}\\b",raw,re.I) or
                   re.search(r"\\b[A-Z][A-Z0-9]{4,7}\\b",raw))
    hard_listing_terms=(
      " pdmr "," director/pdmr "," director / actionnariat "," actionnariat pdmr ",
      " regulatory announcement "," shareholding announcement "," rns announcement "
    )
    if any(x in t for x in hard_listing_terms):
        return True
    event_verbs=(
      "annonce","publie","signe","acquiert","vend","investit","construit","ferme",
      "ouvre","réduit","augmente","baisse","chute","progresse","licencie","sanction",
      "interdit","export","importe","accord","contrat","résultat","bénéfice","perte",
      "production","usine","restriction","enquête","fusion"
    )
    has_event=any(x in t for x in event_verbs)
    return (any(x in t for x in listing_terms) or code_like) and not has_event

def is_useful_article(text):
    """Garde seulement un contenu qui apporte un fait, une décision, une évolution ou une conséquence utile à la veille géopolitique."""
    raw=clean_summary_text(text)
    t=" "+raw.lower()+" "
    if len(re.findall(r"[a-zà-ÿ0-9]+",t))<5:
        return False
    if is_market_listing_noise(raw):
        return False

    summary_markup_noise=(
      "<meta","width=device-width",'name="viewport','property="og:',
      "data-rh=","https://static.","%2c$width","shrink-to-fit"
    )
    if any(x in t for x in summary_markup_noise):
        return False

    # Hors sujet sans ambiguïté : certains mots (ex. « migration ») ont aussi
    # un sens non politique et ne doivent jamais déclencher la veille.
    always_low_value=(
      "migration animale","migration des oiseaux","migration des baleines",
      "documentaire animalier","documentaire nature","programme tv","horoscope",
      "recette de cuisine","croisière touristique",
      "nou camp","sièges vip","fc barcelone","business vip",
      "théâtre","theatre","mise en scène","spectateur","comédie noire","pièce de théâtre","ubu roi",
      "service de rencontres","firstdate","célibataires","application de rencontre","dating service",
      "retient ses larmes","holds back tears","défunt père","late father",
      "ma liste d'achat","ma liste d’achat","je continue d'ajouter","je continue d’ajouter",
      "je retourne à nouveau dans","my buy list","my position","i'm buying","i am buying"
    )
    if any(x in t for x in always_low_value):
        return False

    # Signaux qui peuvent rendre pertinent un sujet normalement périphérique.
    strong=(
      "guerre","invasion","frappe","missile","cessez-le-feu","coup d’état","coup d'etat",
      "sanction","embargo","élection nationale","élection présidentielle","élections législatives",
      "gouvernement","parlement","diplomatie","traité","accord de paix","frontière","migration",
      "armée","militaire","terror","cyberattaque","état d’urgence","état d'urgence",
      "banque centrale","taux directeur","inflation","défaut souverain","droits de douane",
      "tarifs douaniers","commerce international","réfugié","réfugiés","justice constitutionnelle",
      "cour constitutionnelle","loi","réforme","régulation","national security"
    )
    has_strong=any(term_in_text(t,x) for x in strong)

    # Sport, people, divertissement, culture et loisirs : hors produit sauf conséquence publique forte.
    low_value=(
      " football "," uefa "," mlb "," nba "," ligue des nations "," match de "," score ",
      " buteur "," championnat "," tournoi "," coupe du monde "," formule 1 "," grand prix ",
      " chanteur "," chanteuse "," concert "," the weeknd "," shakira "," acteur "," actrice ",
      " célébrité "," people "," série télé "," soap opera "," spoilers "," programme tv ",
      " horoscope "," recette "," mode "," carnaval "," croisière "," exposition d'art ",
      " exposition de "," peinture "," artiste oublié "," festival de musique "," streaming ",
      " sport "," sportif "," sportive "," documentaire "," migration animale "," faune sauvage "
    )
    if any(x in t for x in low_value) and not has_strong:
        return False

    # Cours d'une action isolée / langage de trading : pas de veille géopolitique
    # sans sanction, contrôle export, décision publique ou enjeu industriel stratégique.
    single_stock_noise=(
      "cours de l'action","cours de l’action","cours des actions","fait chuter le cours",
      "chute du cours","actions technologiques s'affaiblissent","actions technologiques s’affaiblissent",
      "chip high flyer","action en hausse","action en baisse","fiche valeur"
    )
    strategic_market_context=(
      "sanction","contrôle des exportations","restriction d'exportation","restriction d’exportation",
      "droits de douane","tarifs douaniers","gouvernement","ministère","régulateur",
      "subvention publique","sécurité nationale","embargo","interdiction"
    )
    if any(x in t for x in single_stock_noise) and not any(x in t for x in strategic_market_context):
        return False

    # Ouvertures de commerces, vie culturelle locale et lecture : hors veille.
    local_lifestyle=("librairie","lecteurs","ouverture du magasin","ouverture d'un magasin","ouverture d’un magasin","nouvelle maison pour feltrinelli")
    if any(x in t for x in local_lifestyle) and not has_strong:
        return False

    # Éviter les spéculations/sujets people sur la santé ou l'apparence d'un responsable.
    health_gossip=("éruption cutanée","rash","ecchymose","bruising","apparence physique")
    if any(x in t for x in health_gossip) and not any(x in t for x in ("hospitalisé","communiqué médical","bulletin médical","opération","diagnostic officiel")):
        return False

    # Faits divers strictement locaux sans portée institutionnelle ou géopolitique.
    local_incident=(
      "incendie d'un appartement","incendie d’une appartement","incendie d'une maison",
      "incendie d’une maison","accident de voiture","accident de la route","faits divers",
      "personnes déplacées après l'incendie d'un appartement","personnes déplacées après l’incendie d’un appartement"
    )
    if any(x in t for x in local_incident) and not has_strong:
        return False

    # Contenus de service/SEO ou de consommation courante.
    service_noise=(
      "en direct gratuitement","live gratuitement","via espn","disney plus","programme tv",
      "prix de l'essence aujourd'hui","prix de l’essence aujourd’hui","meilleures offres",
      "guide d'achat","guide d’achat","prix bloqué pendant","offre à prix fixe",
      "réduction de 30 %","réduction de 30%","sconto del 30",
      "retrouvez l'émission","retrouvez l’émission","émission le 18h eco",
      "programme de l'émission","programme de l’émission"
    )
    if any(x in t for x in service_noise) and not has_strong:
        return False

    # Conférences commerciales/éducatives sans décision publique ni enjeu stratégique.
    if (" summit " in t or " sommet " in t) and any(x in t for x in (" apprentissage "," éducation "," education "," livres aux robots ")) and not has_strong:
        return False

    # Données de consommation/secteur très spécialisées sans portée macroéconomique ou publique.
    consumer_market=("ventes au détail de véhicules","location de voitures particulières","marché automobile","immatriculations automobiles")
    if any(x in t for x in consumer_market) and not has_strong:
        return False

    # Langage typique de contenu promotionnel d'entreprise.
    corporate_promo=(
      "nous avons expédié","créant des synergies","répondre aux demandes les plus exigeantes",
      "unités en 40 ans","présente sa nouvelle gamme","légende de l'image de presse",
      "légende de l’image de presse","cérémonie d'ouverture officielle","cérémonie d’ouverture officielle",
      "ouvre la chaîne d'assemblage final","ouvre la chaîne d’assemblage final","globenewswire"
    )
    if any(x in t for x in corporate_promo) and not has_strong:
        return False

    private_deal_noise=(
      "participation majoritaire","private equity","capital-investissement",
      "rachat par ","acquisition par ","prend une participation","take majority stake"
    )
    strategic_deal_context=(
      "gouvernement","État","état","sanction","régulateur","sécurité nationale",
      "infrastructure critique","énergie stratégique","défense","contrôle des exportations",
      "entreprise publique","state-owned","national security","critical infrastructure"
    )
    if any(x in t for x in private_deal_noise) and not any(x.lower() in t for x in strategic_deal_context):
        return False

    # Prévisions de marché promotionnelles et communiqués sans décision publique ou enjeu stratégique.
    market_promo=(
      "le marché de l'intelligence artificielle","le marché de l’intelligence artificielle",
      "devrait atteindre","communiqué de presse","press release","marché devrait atteindre"
    )
    if sum(1 for x in market_promo if x in t)>=2 and not has_strong:
        return False

    # Interviews, plateaux et hypothèses sans fait nouveau : hors veille.
    discussion_noise=("dans l'émission","dans l’émission","interroge","débat télévisé","table ronde")
    decision_terms=("annonce","décide","adopte","approuve","rejette","impose","signe","interdit","lance","démissionne","vote","sanctionne","condamne","autorise","suspend")
    if sum(1 for x in discussion_noise if x in t)>=2 and not any(x in t for x in decision_terms):
        return False
    if t.strip().startswith("que fera ") and " si " in t and not any(x in t for x in decision_terms):
        return False

    # Les chroniques boursières quotidiennes ne deviennent pas géopolitiques parce
    # qu'elles citent le pétrole ou les rendements obligataires.
    market_roundup_noise=(
      "l’ambiance à wall street","l'ambiance à wall street","les bourses du jour",
      "marchés aujourd'hui","marchés aujourd’hui","markets today",
      "wall street est mitigée","la plupart des sociétés cotées","séance boursière",
      "actions technologiques","nasdaq composite"
    )
    if any(x in t for x in market_roundup_noise) and not any(x in t for x in (
        "sanction","embargo","banque centrale","réserve fédérale","fed","taux directeur",
        "défaut souverain","crise financière","droits de douane","tarifs douaniers"
    )):
        return False

    # Un incident mortel sans cause ni portée publique claire ne suffit pas.
    incomplete_incident=("incident a eu lieu","incident s'est produit","incident s’est produit")
    if any(x in t for x in incomplete_incident) and any(x in t for x in ("tués","morts","décès")) and not any(x in t for x in (
        "attaque","attentat","explosion","fusillade","combat","conflit","terror","accident","enquête","armée"
    )):
        return False

    # Une rétrospective historique n'est pas une actualité du jour sans fait nouveau actuel.
    historical_retrospective=(
      "guerre froide","cold war","chute du mur de berlin","fall of the berlin wall",
      "archives historiques","historical archives","il y a plusieurs décennies"
    )
    current_hook=(
      "aujourd'hui","aujourd’hui","ce mardi","ce mercredi","ce jeudi","ce vendredi",
      "a annoncé","a déclaré","annonce","publie","publication","nouvelle étude",
      "rapport publié","vient de","2026","message officiel","décision"
    )
    if any(x in t for x in historical_retrospective) and not any(x in t for x in current_hook):
        return False

    # Un éditorial/opinion n'est utile que s'il décrit aussi un fait concret, une décision ou une évolution.
    opinion=(" éditorial "," editorial "," opinion "," chronique "," tribune ")
    informative=(
      " annonce "," décide "," adopte "," approuve "," rejette "," impose "," suspend ",
      " signe "," conclut "," interdit "," autorise "," lance "," déploie "," ordonne ",
      " démissionne "," retire "," reconnaît "," augmente "," baisse "," recule "," progresse ",
      " atteint "," vote "," élit "," élu "," élue "," accuse "," condamne "," enquête ",
      " sanctionne "," frappe "," attaque "," envahit "," évacue "," ferme "," ouvre ",
      " a annoncé "," a décidé "," a adopté "," a approuvé "," a rejeté "," a imposé ",
      " a signé "," a conclu "," a interdit "," a lancé "," a déployé "," a ordonné ",
      " a démissionné "," a retiré "," a reconnu "," a augmenté "," a baissé "," a reculé ",
      " a progressé "," a atteint "," a voté "," a été élu "," a été élue "," a condamné ",
      " accord "," traité "," réforme "," loi "," budget "," taux "," inflation "," déficit ",
      " exportation "," importation "," tarifs douaniers "," droits de douane "
    )
    if any(x in t for x in opinion) and not any(x in t for x in informative):
        return False

    # Un titre uniquement interrogatif pose un sujet mais ne donne pas la réponse :
    # il n'est conservé que s'il contient déjà un fait concret vérifiable.
    if raw.rstrip().endswith("?") and not any(x in t for x in informative):
        return False

    # Titres purement thématiques : ils nomment un sujet mais n'apprennent aucun fait.
    vague_topics=(
      "il y pense encore","joue avec le monde à propos du pétrole","la politique de tous les côtés",
      "le dividende de l'intelligence artificielle","le dividende de l’intelligence artificielle",
      "l'avenir de l'intelligence artificielle","l’avenir de l’intelligence artificielle",
      "les enjeux de l'intelligence artificielle","les enjeux de l’intelligence artificielle",
      "réflexions sur ","regard sur ","qui a eu le plus de succès",
      "qui a eu le plus de succes","le plus performant","le moins réussi","le moins reussi"
    )
    if any(x in t for x in vague_topics) and not any(x in t for x in informative):
        return False

    return True

def note_rejection(reason, title="", url=""):
    REJECTION_STATS[reason]+=1
    # Garder les logs lisibles : seulement les trois premiers exemples par motif.
    if REJECTION_STATS[reason]<=3:
        print(f"REJET {reason}: {(title or '')[:180]} | {(url or '')[:160]}",file=sys.stderr)

def title_rejection_reason(title):
    """Le titre sert à découvrir. On ne rejette ici que les hors-sujet manifestes."""
    raw=clean_summary_text(title)
    t=" "+raw.lower()+" "
    if not raw or len(re.findall(r"[a-zà-ÿ0-9]+",t))<4:
        return "titre_trop_pauvre"
    if is_market_listing_noise(raw):
        return "fiche_boursiere"

    # Ces contenus ne deviennent pas géopolitiques parce qu'ils contiennent un mot
    # comme « énergie », « accord », « marché » ou le nom d'un pays.
    obvious_noise=(
      "coachella","festival de musique","livestream","diffusion en direct de coachella",
      "concert","tournée musicale","billetterie","programme tv","soap opera","spoilers",
      "théâtre","theatre","mise en scène","spectateur","comédie noire","pièce de théâtre","ubu roi",
      "service de rencontres","firstdate","célibataires","application de rencontre","dating service",
      "horoscope","recette","mode","sneakers","célébrité","people","shakira","the weeknd",
      "football","uefa","mlb","nba","championnat","match de","buteur","formule 1",
      "croisière","zoo","pandas","concours littéraire","la casa de los famosos"
    )
    if any(x in t for x in obvious_noise):
        return "sport_divertissement_loisirs"

    health_gossip=("éruption cutanée","rash","ecchymose","bruising","apparence physique")
    if any(x in t for x in health_gossip):
        return "people_sante_speculative"
    return None

def content_rejection_reason(text):
    """Analyse le résumé tiré du contenu, après découverte par le titre."""
    raw=clean_summary_text(text)
    if not is_useful_article(raw):
        return "contenu_hors_sujet"
    # Un contenu sans aucun signal géopolitique/économique/public concret n'est pas
    # publié, même si son titre a été découvert par un flux thématique.
    if score(raw)<5:
        return "pas_de_signal_geopolitique"
    return None

def article_candidate_priority(art):
    """Priorise les URL éditeur directes, puis le contenu et les titres à fort signal."""
    title=(art.get("title") or "").strip()
    has_detail=detail_is_substantive(title,art.get("description") or "")
    source_ok=trusted_source(art.get("source") or "")
    direct_url=not is_google_news_url(art.get("url",""))
    try:
        ts=art.get("date").timestamp()
    except Exception:
        ts=0
    return (0 if direct_url else 1,0 if has_detail else 1,-score(title),0 if source_ok else 1,-ts)

def prioritize_articles(articles,start_date,end_date,country=None):
    """Trie les titres avant analyse et garde une source de secours par événement."""
    out=[]; seen_urls=set(); per_title=defaultdict(int)
    # Choisir les candidats par qualité avant la limite par titre pour qu'un lien
    # éditeur Bing/GDELT ne soit pas écarté derrière deux enveloppes Google.
    for art in sorted(articles,key=article_candidate_priority):
        title=(art.get("title") or "").strip()
        url=(art.get("url") or "").strip()
        if len(title)<22:
            note_rejection("titre_trop_court",title,url)
            continue
        try:
            d=editorial_day(art["date"])
        except Exception:
            note_rejection("date_invalide",title,url)
            continue
        if d<start_date or d>end_date:
            continue
        if country and not country_title_matches(country,title):
            continue
        reason=title_rejection_reason(title)
        if reason:
            note_rejection(reason,title,url)
            continue
        k=(d,key_title(title))
        if not k[1]:
            continue
        url_key=url or (source_name(art.get("source",""))+"|"+k[1])
        if url_key in seen_urls or per_title[k]>=2:
            continue
        seen_urls.add(url_key); per_title[k]+=1; out.append(art)
    DISCOVERY_STATS["titres_candidats"]+=len(out)
    return sorted(out,key=article_candidate_priority)

def term_in_text(text, term):
    """Cherche un mot/une expression complète, jamais une sous-chaîne accidentelle."""
    value=(text or "").lower()
    needle=(term or "").strip().lower()
    if not needle: return False
    return re.search(r"(?<![a-z0-9à-ÿ])"+re.escape(needle)+r"(?![a-z0-9à-ÿ])",value,re.I) is not None

def election_score(text):
    """Une élection nationale est majeure quand le texte décrit le scrutin, son résultat ou une étape décisive."""
    t=" "+(text or "").lower()+" "
    elected=(
      "élu président" in t or "élue présidente" in t or "nouveau président" in t or
      "nouvelle présidente" in t or "nouveau premier ministre" in t or
      "nouvelle première ministre" in t
    )
    if elected:
        return 9
    national_terms=("élection présidentielle","élections présidentielles","élection nationale","élections législatives")
    decisive_terms=("scrutin","vote","urnes","résultat","résultats","second tour","premier tour","électeurs","dépouillement","majorité","sièges","participation")
    if any(x in t for x in national_terms) and any(x in t for x in decisive_terms):
        return 8
    return 0

def score(text):
    """Importance géopolitique 1-10, calculée sur le texte français quand disponible."""
    t=" "+(text or "").lower()+" "
    # Culture, célébrités et décès sans conséquence publique majeure restent hors
    # de la hiérarchie géopolitique. Exception : dirigeant en exercice, conflit,
    # assassinat/attaque politique ou implication directe/documentée de l'État.
    death_terms=(" décès "," mort "," meurt "," décède "," décédé "," décédée "," died "," death ")
    culture_terms=(" actrice "," acteur "," chanteur "," chanteuse "," artiste "," écrivain "," écrivaine "," réalisateur "," réalisatrice "," musicien "," musicienne "," célébrité "," cinéma "," culture ")
    geopolitical_death=(" président en exercice "," présidente en exercice "," premier ministre en exercice "," chef d'état "," chef d’état "," conflit "," guerre "," frappe "," attaque "," assassinat "," assassiné "," assassinée "," état responsable "," gouvernement responsable "," forces de sécurité "," armée ")
    if any(w in t for w in death_terms) and any(w in t for w in culture_terms) and not any(w in t for w in geopolitical_death):
        return 2
    hits=[]
    for level,words in IMPACT.items():
        count=sum(1 for w in words if term_in_text(t,w))
        if count:
            hits.append((level,count))
    forced=election_score(text)
    if not hits:
        return max(4,forced)
    highest=max(max(level for level,_ in hits),forced)
    # Plusieurs signaux concordants peuvent relever d'un point un sujet déjà important,
    # sans transformer artificiellement une actualité mineure en crise mondiale.
    signal_count=sum(count for level,count in hits if level>=6)
    if highest in (6,7,8) and signal_count>=3:
        highest+=1

    # « gas » désigne souvent l'essence automobile dans les titres nord-américains :
    # un prix local à la pompe n'est pas une crise énergétique internationale.
    retail_fuel=any(x in t for x in ("prix du gaz","prix de l'essence","prix de l’essence","à la pompe","gas prices","pump prices","winter-blend gasoline","summer fuel"))
    strategic_fuel=any(x in t for x in ("guerre","embargo","sanction","pétrole brut","crude oil","détroit d'ormuz","détroit d’ormuz","pipeline","crise énergétique","réserve stratégique","réserves stratégiques","opec","opep"))
    if retail_fuel and not strategic_fuel:
        highest=min(highest,6)

    # Une séance boursière ordinaire ne devient pas géopolitique parce que le pétrole bouge.
    routine_market=any(x in t for x in ("marchés aujourd'hui","marchés aujourd’hui","markets today","actions chutent","stocks fall","wall street mardi","wall street today"))
    market_cause=any(x in t for x in ("guerre","sanction","embargo","banque centrale","taux directeur","récession","crise financière","tarifs douaniers","droits de douane"))
    if routine_market and not market_cause:
        highest=min(highest,6)

    local_response=any(x in t for x in (
      "entreprises locales","commerce local","municipalité","conseil municipal","ville de ",
      "city council","local businesses","local business","municipal plan"
    ))
    national_decision=any(x in t for x in (
      "gouvernement fédéral","gouvernement national","président","premier ministre","parlement",
      "banque centrale","ministère fédéral","federal government","national government","congress"
    ))
    if local_response and not national_decision:
        highest=min(highest,6)

    standalone_commodity=any(x in t for x in (
      "prix du pétrole azerbaïdjanais","prix du pétrole recule","prix du pétrole baisse",
      "oil price falls","oil price declines","oil price rises","cours du pétrole recule"
    ))
    commodity_cause=any(x in t for x in (
      "guerre","sanction","embargo","opec","opep","détroit d'ormuz","détroit d’ormuz",
      "attaque","frappe","rupture d'approvisionnement","rupture d’approvisionnement",
      "réserve stratégique","tarifs douaniers","droits de douane"
    ))
    if standalone_commodity and not commodity_cause:
        highest=min(highest,6)

    advocacy_only=any(x in t for x in (
      "marches pour le climat","marche pour le climat","appel à manifester",
      "doivent être aussi antiracistes","tribune militante"
    ))
    concrete_policy=any(x in t for x in (
      "adopte","adopté","loi","vote","gouvernement","parlement","interdit",
      "accord","budget","sanction","élection","décision","décret","règlement"
    ))
    if advocacy_only and not concrete_policy:
        highest=min(highest,6)

    # Un sondage / scénario simulé informe sur la campagne mais n'est pas en lui-même
    # un résultat électoral ou une décision publique majeure.
    pre_election_poll=any(x in t for x in (
      "selon un sondage","sondage atlas","sondage électoral","poll shows","opinion poll",
      "second tour simulé","scénario du second tour","statistiquement à égalité"
    ))
    official_election_event=any(x in t for x in (
      "résultats officiels","résultat officiel","dépouillement","a été élu","a été élue",
      "élu président","élue présidente","remporte l'élection","remporte l’élection"
    ))
    if pre_election_poll and not official_election_event:
        highest=min(highest,6)

    # Coupons, bons et aides de consommation destinés aux ménages restent des mesures
    # domestiques sauf s'ils sont liés à une crise nationale/internationale documentée.
    consumer_aid=any(x in t for x in (
      "coupon d'essence","coupon de gaz","coupon d’énergie","coupon d'énergie",
      "bon d'essence","bon de gaz","chèque énergie","energy voucher","fuel voucher"
    ))
    aid_crisis=any(x in t for x in (
      "état d'urgence","état d’urgence","crise énergétique","pénurie nationale",
      "rationnement","guerre","sanction","embargo"
    ))
    if consumer_aid and not aid_crisis:
        highest=min(highest,6)

    # Une opération privée de capital-investissement / prise de participation n'entre
    # pas dans International sans décision étatique, sécurité nationale ou choc d'offre.
    private_corporate_deal=any(x in t for x in (
      "capital-investissement","private equity","participation majoritaire",
      "prise de participation majoritaire","acquisition majoritaire","majority stake"
    ))
    strategic_corporate_context=any(x in t for x in (
      "sécurité nationale","national security","sanction","embargo","contrôle des exportations",
      "restriction d'exportation","restriction d’exportation","gouvernement","régulateur",
      "subvention publique","défense nationale","pénurie","rupture d'approvisionnement",
      "rupture d’approvisionnement"
    ))
    if private_corporate_deal and not strategic_corporate_context:
        highest=min(highest,6)

    # Les demandes administratives de versement de fonds déjà programmés ne sont pas
    # des crises internationales tant qu'il n'y a ni blocage, ni litige, ni condition nouvelle.
    administrative_funding=any(x in t for x in (
      "demande de paiement","demande de versement","payment request",
      "plan national de relance et de résilience","recovery and resilience plan"
    ))
    funding_conflict=any(x in t for x in (
      "bloque","bloqué","suspend","suspendu","refuse","refusé","conditionne",
      "litige","sanction","procédure d'infraction","procédure d’infraction"
    ))
    if administrative_funding and not funding_conflict:
        highest=min(highest,6)

    disciplinary_sanction=any(x in t for x in (
      "sanctions disciplinaires","sanctions de la fraternité","sanctions universitaires",
      "expulsions et suspensions","disciplinary sanctions","university sanctions",
      "fraternity sanctions","commission d'audience","commission d’audience"
    ))
    if disciplinary_sanction:
        highest=min(highest,6)

    return min(10,highest)
def category(title):
    t=" "+title.lower()+" "
    for cat,words in CATEGORIES:
        if any(term_in_text(t,w) for w in words): return cat
    return "Géopolitique"
def key_title(title):
    words=re.findall(r"[a-z0-9à-ÿ]+",(title or "").lower())
    stop={"the","a","an","of","to","and","in","on","for","with","as","at","de","la","le","les","des","du","un","une","et","en","sur"}
    return " ".join(w for w in words if w not in stop)[:150]
def clean_title(raw):
    raw=re.sub(r"\s+"," ",raw or "").strip(); parts=raw.rsplit(" - ",1)
    return (parts[0].strip(),parts[1].strip()) if len(parts)==2 and len(parts[1])<70 else (raw,"")
def trusted_source(label): return any(s.lower() in (label or "").lower() for s in SOURCE_LABELS)

def source_reliability_score(label):
    """Note éditoriale indicative 1-10, distincte de l'importance géopolitique."""
    raw=(label or "").strip()
    low=raw.lower()
    if not raw:
        return 5
    # Grandes agences internationales.
    if any(x in low for x in ("reuters","associated press","ap news","agence france-presse")) or low in ("ap","afp"):
        return 9
    # Médias reconnus disposant de standards éditoriaux robustes.
    high=(
      "bbc","france 24","dw","deutsche welle","financial times","le monde","nhk",
      "cbc","abc australia","abc.net.au","rnz","npr","pbs","propublica","politico",
      "the guardian","new york times","washington post","wall street journal",
      "bloomberg","al jazeera","euronews","le temps","faz.net","el mundo",
      "the times of israel","the globe and mail","sydney morning herald","the age"
    )
    if any(x in low for x in high):
        return 8
    # Sources étatiques / institutionnelles : utiles pour leurs propres positions,
    # mais à lire comme source institutionnelle plutôt que comme média indépendant.
    state_or_official=(
      "xinhua","rt.com","russia today","azərtac","azertac","correodelorinoco",
      "média public / contrôlé par l’état","media public / controle par l'etat",
      "agence publique","state media","government media"
    )
    if any(x in low for x in state_or_official):
        return 6
    # Sources explicitement militantes / de plaidoyer ou portails syndiqués opaques.
    advocacy_or_syndication=(
      "ncr-iran.org","infoaut.org","presse-toi à gauche","europesun.com","iraqsun.com",
      "shanghainews.net","coloradostar.com","californiatelegraph.com","britainnews.net",
      "indiagazette.com"
    )
    if any(x in low for x in advocacy_or_syndication):
        return 5
    # Une source déjà reconnue dans la liste de veille obtient un niveau élevé mais prudent.
    if trusted_source(raw):
        return 7
    # Média national/local non référencé : utilisable, avec prudence et recoupement si sensible.
    return 6

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
    if "fiabilité " in l.lower():
        return l
    if "associated press" in l.lower() or l.lower()=="ap news": l="AP"
    if "abc.net.au" in l.lower(): l="ABC Australia"
    base=l or "Source"
    note=STATE_MEDIA_HINTS.get(base)
    display=f"{base} ({note})" if note else base
    score_value=source_reliability_score(display)
    return f"{display} — fiabilité {score_value}/10"
def editorial_day(dt): return dt.astimezone(PARIS).date()
def looks_english(text):
    words=re.findall(r"[a-zà-ÿ]+",(text or "").lower())
    en=sum(w in EN_WORDS for w in words); fr=sum(w in FR_WORDS for w in words)
    return en>=2 and en>fr

def french_summary(text, meta=None):
    """Produit un résumé français exploitable. Les nouveaux résumés doivent préciser les acteurs/pays lorsque le titre source les donne."""

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
            translated=enrich_editorial_context(translated)
            TRANSLATION_CACHE[text]=translated
            return translated
    except Exception as e:
        print("TRANSLATION",e,file=sys.stderr)
    if meta is not None:
        PENDING.append({**meta,"original_summary":text})
    return None


ARTICLE_DETAIL_CACHE={}
ARTICLE_DETAIL_USED=0
EXISTING_DETAIL_USED=0
GOOGLE_NEWS_URL_CACHE={}
GOOGLE_NEWS_RESOLVED={}
GOOGLE_NEWS_DECODE_USED=0
GOOGLE_BING_FALLBACK_USED=0

def strip_html_text(raw):
    if not raw: return ""
    text=html_lib.unescape(raw)
    text=re.sub(r"(?is)<(?:script|style|noscript)[^>]*>.*?</(?:script|style|noscript)>"," ",text)
    text=re.sub(r"(?s)<[^>]+>"," ",text)
    text=re.sub(r"\s+"," ",text).strip()
    return text

def detail_is_substantive(title, detail):
    detail=clean_summary_text(strip_html_text(detail))
    if not detail: return False
    words=re.findall(r"[a-zà-ÿ0-9]+",detail.lower())
    if len(words)<12: return False
    # Un flux RSS Google répète souvent seulement le titre et le nom du média.
    title_words=set(re.findall(r"[a-zà-ÿ0-9]+",(title or "").lower()))
    detail_words=set(words)
    if title_words and len(detail_words)<=len(title_words)+3:
        overlap=len(title_words & detail_words)/max(1,len(title_words))
        if overlap>=0.75: return False
    generic=("google news","lire la suite","read more","voir l'article","voir l’article","breaking news")
    if any(x in detail.lower() for x in generic) and len(words)<20: return False
    return True


class ArticleHTMLExtractor(HTMLParser):
    """Extrait proprement descriptions META et paragraphes sans capturer les attributs HTML voisins."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.descriptions=[]
        self.paragraphs=[]
        self._skip=0
        self._in_p=0
        self._p_parts=[]

    def handle_starttag(self,tag,attrs):
        tag=(tag or "").lower()
        attrs={str(k).lower(): (v or "") for k,v in attrs}
        if tag in ("script","style","noscript"):
            self._skip+=1
            return
        if self._skip:
            return
        if tag=="meta":
            key=(attrs.get("name") or attrs.get("property") or "").strip().lower()
            content=(attrs.get("content") or "").strip()
            if key in ("description","og:description","twitter:description") and len(content)>=60:
                self.descriptions.append(content)
        elif tag=="p":
            self._in_p+=1
            if self._in_p==1:
                self._p_parts=[]

    def handle_data(self,data):
        if self._skip or not self._in_p:
            return
        if data and data.strip():
            self._p_parts.append(data.strip())

    def handle_endtag(self,tag):
        tag=(tag or "").lower()
        if tag in ("script","style","noscript"):
            if self._skip:
                self._skip-=1
            return
        if self._skip:
            return
        if tag=="p" and self._in_p:
            self._in_p-=1
            if self._in_p==0:
                value=re.sub(r"\s+"," "," ".join(self._p_parts)).strip()
                if len(value)>=100:
                    self.paragraphs.append(value)
                self._p_parts=[]

def is_google_news_url(url):
    try:
        p=urllib.parse.urlparse(url or "")
        parts=[part for part in p.path.split("/") if part]
        return _is_google_host(p.hostname) and len(parts)>=2 and parts[-2] in ("articles","read")
    except Exception:
        return False

def _is_google_host(host):
    host=(host or "").lower().rstrip(".")
    return host=="google.com" or host.endswith(".google.com") or host=="googleusercontent.com" or host.endswith(".googleusercontent.com") or host=="gstatic.com" or host.endswith(".gstatic.com")

def _publisher_url(value):
    """Retourne une URL éditoriale, jamais une page intermédiaire Google."""
    value=html_lib.unescape(str(value or "")).replace("\\/","/").strip()
    if not value.startswith(("http://","https://")):
        return ""
    try:
        parsed=urllib.parse.urlsplit(value)
        if parsed.scheme not in ("http","https") or not parsed.hostname or _is_google_host(parsed.hostname):
            return ""
        if parsed.username or parsed.password:
            return ""
        return value
    except Exception:
        return ""

class _GoogleArticleParams(HTMLParser):
    def __init__(self, article_id):
        super().__init__(convert_charrefs=True)
        self.article_id=article_id
        self.params={}
        self.unmatched_params=[]
        self.publisher_candidates=[]

    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        signature=attrs.get("data-n-a-sg") or ""
        timestamp=attrs.get("data-n-a-ts") or ""
        if signature and timestamp:
            candidate={"signature":signature,"timestamp":timestamp}
            if attrs.get("data-n-a-id")==self.article_id:
                self.params=candidate
            else:
                self.unmatched_params.append(candidate)
        if tag=="meta":
            key=(attrs.get("property") or attrs.get("name") or "").lower()
            if key in ("og:url","twitter:url"):
                self.publisher_candidates.append(attrs.get("content") or "")
        elif tag=="link" and "canonical" in (attrs.get("rel") or "").lower().split():
            self.publisher_candidates.append(attrs.get("href") or "")

def _google_article_decode_params(body, article_id):
    parser=_GoogleArticleParams(article_id)
    try:
        parser.feed(body or "")
    except Exception:
        pass
    sig=parser.params.get("signature","").strip()
    ts=parser.params.get("timestamp","").strip()
    if sig and ts:
        return ts,sig
    if len(parser.unmatched_params)==1:
        candidate=parser.unmatched_params[0]
        DISCOVERY_STATS["google_decode_params_id_absent"]+=1
        return candidate["timestamp"],candidate["signature"]
    return "",""

def _google_batchexecute_publisher(raw):
    """Déplie le JSON imbriqué de batchexecute et extrait garturlres."""
    text=str(raw or "").lstrip()
    if text.startswith(")]}'"):
        text=text[4:].lstrip("\r\n")
    pending=[text]
    seen=set()
    for _ in range(6):
        next_pending=[]
        for item in pending:
            if isinstance(item,list):
                if len(item)>1 and item[0]=="garturlres":
                    resolved=_publisher_url(item[1])
                    if resolved: return resolved
                next_pending.extend(v for v in item if isinstance(v,(list,str)))
                continue
            candidate=(item or "").strip()
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            candidate=re.sub(r"^\d+\s*\n","",candidate)
            for line in candidate.splitlines():
                line=line.strip()
                if line and line not in seen: next_pending.append(line)
            try:
                parsed=json.loads(candidate)
            except Exception:
                continue
            if isinstance(parsed,list): next_pending.append(parsed)
        pending=next_pending
    return ""

def decode_google_news_direct_id(art_id):
    """Décode les anciens identifiants qui encapsulent l'URL éditeur."""
    if not art_id:
        return ""
    try:
        padded=art_id+"="*((4-len(art_id)%4)%4)
        decoded=base64.urlsafe_b64decode(padded.encode("ascii"))
        # Les anciens IDs stockaient parfois l'URL en clair dans le protobuf.
        # Les IDs récents CBMi contiennent plutôt un jeton à résoudre côté Google.
        for match in re.finditer(rb"https?://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]+",decoded):
            resolved=_publisher_url(match.group(0).decode("utf-8","replace"))
            if resolved:
                DISCOVERY_STATS["google_decode_direct_success"]+=1
                return resolved
        DISCOVERY_STATS["google_decode_direct_no_url"]+=1
    except Exception as exc:
        DISCOVERY_STATS["google_decode_direct_error"]+=1
        print("GOOGLE NEWS DIRECT",art_id,exc,file=sys.stderr)
    return ""

def _request_google_page(url):
    headers={
        "User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/128.0 Safari/537.36",
        "Accept":"text/html,application/xhtml+xml",
        "Accept-Language":"fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    if httpx is not None:
        current=url
        # Keep httpx's native User-Agent instead of claiming to be Chrome; its
        # HTTP/2 transport and matching client fingerprint avoids the JS shell.
        with httpx.Client(http2=True,follow_redirects=False,timeout=10) as client:
            for _ in range(4):
                response=client.get(current,follow_redirects=False)
                if response.status_code in (301,302,303,307,308):
                    destination=urllib.parse.urljoin(current,response.headers.get("location", ""))
                    if urllib.parse.urlparse(destination).hostname=="news.google.com":
                        current=destination
                        continue
                    return destination,""
                response.raise_for_status()
                return str(response.url),response.content[:400000].decode("utf-8","replace")
        return current,""
    req=urllib.request.Request(url,headers={
        "User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/128.0 Safari/537.36",
        "Accept":"text/html,application/xhtml+xml",
        "Accept-Language":"fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    })
    class SameGoogleNewsRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,request,response,code,message,headers,new_url):
            if urllib.parse.urlparse(new_url).hostname=="news.google.com":
                return super().redirect_request(request,response,code,message,headers,new_url)
            return None
    opener=urllib.request.build_opener(SameGoogleNewsRedirect)
    current=url
    for _ in range(4):
        try:
            with opener.open(urllib.request.Request(current,headers=dict(req.header_items())),timeout=10) as response:
                final_url=response.geturl()
                body=response.read(400000).decode("utf-8","replace")
                return final_url,body
        except urllib.error.HTTPError as exc:
            location=exc.headers.get("Location") if exc.headers else ""
            destination=urllib.parse.urljoin(current,location) if location else ""
            if exc.code in (301,302,303,307,308) and urllib.parse.urlparse(destination).hostname=="news.google.com":
                current=destination
                continue
            if destination:
                return destination,""
            raise
    return current,""

def _google_article_page_url(source_url):
    """Build the RSS splash URL that returns the article decode parameters."""
    p=urllib.parse.urlsplit(source_url)
    query=dict(urllib.parse.parse_qsl(p.query,keep_blank_values=True))
    # Google exposes article splash parameters consistently with its default locale.
    # Preserve an explicit locale from the incoming RSS URL.
    hl=query.get("hl") or "en-US"
    gl=query.get("gl") or "US"
    ceid=query.get("ceid") or "US:en"
    article_id=next((part for part in reversed(p.path.split("/")) if part),"")
    query=urllib.parse.urlencode({"hl":hl,"gl":gl,"ceid":ceid})
    return urllib.parse.urlunsplit(("https","news.google.com",f"/rss/articles/{urllib.parse.quote(article_id,safe='')}",query,""))

def _post_google_article_decode(art_id, timestamp, signature):
    context=[
      ["X","X",["X","X"],None,None,1,1,"US:en",None,1,None,None,None,None,None,0,1],
      "X","X",1,[1,1,1],1,1,None,0,0,None,0
    ]
    inner=["garturlreq",context,art_id,int(timestamp) if str(timestamp).isdigit() else timestamp,signature]
    envelope=["Fbv4je",json.dumps(inner,separators=(",",":")),None,"0"]
    f_req=json.dumps([[envelope]],separators=(",",":"))
    headers={
      "User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/128.0 Safari/537.36",
      "Content-Type":"application/x-www-form-urlencoded;charset=UTF-8",
      "Referer":"https://news.google.com/"
    }
    body="f.req="+urllib.parse.quote(f_req,safe="")
    if httpx is not None:
        with httpx.Client(http2=True,timeout=10) as client:
            response=client.post(
                "https://news.google.com/_/DotsSplashUi/data/batchexecute",
                content=body,
                headers={k:v for k,v in headers.items() if k!="User-Agent"}
            )
            response.raise_for_status()
            return response.text
    req=urllib.request.Request("https://news.google.com/_/DotsSplashUi/data/batchexecute",data=body.encode("utf-8"),headers=headers)
    with urllib.request.urlopen(req,timeout=10) as response:
        return response.read().decode("utf-8","replace")

def decode_google_news_url(source_url):
    """Résout les URL RSS Google News vers une URL réelle de l'éditeur."""
    global GOOGLE_NEWS_DECODE_USED
    source_url=(source_url or "").strip()
    if not is_google_news_url(source_url):
        return source_url
    if source_url in GOOGLE_NEWS_URL_CACHE:
        return GOOGLE_NEWS_URL_CACHE[source_url] or source_url

    budget=max(0,int(os.getenv("GOOGLE_NEWS_DECODE_BUDGET","12") or "12"))
    if budget<=0:
        DISCOVERY_STATS["google_decode_disabled"]+=1
        GOOGLE_NEWS_URL_CACHE[source_url]=""
        return source_url
    if GOOGLE_NEWS_DECODE_USED>=budget:
        DISCOVERY_STATS["google_decode_budget_epuise"]+=1
        GOOGLE_NEWS_URL_CACHE[source_url]=""
        return source_url
    GOOGLE_NEWS_DECODE_USED+=1

    p=urllib.parse.urlparse(source_url)
    parts=[x for x in p.path.split("/") if x]
    art_id=parts[-1] if len(parts)>=2 and parts[-2] in ("articles","read") else ""
    if not art_id:
        DISCOVERY_STATS["google_decode_id_invalide"]+=1
        GOOGLE_NEWS_URL_CACHE[source_url]=""
        return source_url

    direct=decode_google_news_direct_id(art_id)
    if direct:
        GOOGLE_NEWS_URL_CACHE[source_url]=direct
        GOOGLE_NEWS_RESOLVED[source_url]=direct
        DISCOVERY_STATS["google_decode_success"]+=1
        return direct
    DISCOVERY_STATS["google_decode_direct_fallback"]+=1

    # Only the RSS splash route returns signatures to non-browser clients.
    page_urls=[_google_article_page_url(source_url)]
    for page_url in dict.fromkeys(page_urls):
        try:
            final_url,body=_request_google_page(page_url)
            resolved=_publisher_url(final_url)
            if resolved:
                GOOGLE_NEWS_URL_CACHE[source_url]=resolved
                GOOGLE_NEWS_RESOLVED[source_url]=resolved
                DISCOVERY_STATS["google_decode_success"]+=1
                return resolved

            timestamp,signature=_google_article_decode_params(body,art_id)
            if timestamp and signature:
                raw=_post_google_article_decode(art_id,timestamp,signature)
                resolved=_google_batchexecute_publisher(raw)
                if resolved:
                    GOOGLE_NEWS_URL_CACHE[source_url]=resolved
                    GOOGLE_NEWS_RESOLVED[source_url]=resolved
                    DISCOVERY_STATS["google_decode_success"]+=1
                    return resolved
                DISCOVERY_STATS["google_decode_no_url"]+=1
            else:
                parser=_GoogleArticleParams(art_id)
                try: parser.feed(body)
                except Exception: pass
                for candidate in parser.publisher_candidates:
                    resolved=_publisher_url(candidate)
                    if resolved:
                        GOOGLE_NEWS_URL_CACHE[source_url]=resolved
                        GOOGLE_NEWS_RESOLVED[source_url]=resolved
                        DISCOVERY_STATS["google_decode_metadata_fallback"]+=1
                        DISCOVERY_STATS["google_decode_success"]+=1
                        return resolved
                attrs=sorted(set(re.findall(r"data-n-a-(?:id|sg|ts)",body or "")))
                preview=strip_html_text(body)[:180]
                print("GOOGLE NEWS PARAMS ABSENTS",page_url,"final",final_url,"attrs",attrs,"preview",preview,file=sys.stderr)
                DISCOVERY_STATS["google_decode_params_absents"]+=1
        except urllib.error.HTTPError as exc:
            DISCOVERY_STATS[f"google_decode_http_{exc.code}"]+=1
            print("GOOGLE NEWS DECODE HTTP",exc.code,page_url,file=sys.stderr)
        except Exception as exc:
            DISCOVERY_STATS["google_decode_error"]+=1
            print("GOOGLE NEWS DECODE",page_url,exc,file=sys.stderr)

    GOOGLE_NEWS_URL_CACHE[source_url]=""
    return source_url

def article_detail_budget_exhausted(existing=False, targeted=False):
    if existing:
        budget=max(1,int(os.getenv("EXISTING_DETAIL_BUDGET","6") or "6"))
        return EXISTING_DETAIL_USED>=budget
    env_name="TARGETED_DETAIL_BUDGET" if targeted else "ARTICLE_DETAIL_BUDGET"
    default="160" if targeted else "96"
    budget=max(1,int(os.getenv(env_name,default) or default))
    return ARTICLE_DETAIL_USED>=budget

def fetch_article_detail(url, existing=False, targeted=False):
    """Récupère le contenu avec une réserve supplémentaire pour les pays ciblés."""
    global ARTICLE_DETAIL_USED,EXISTING_DETAIL_USED
    original_url=(url or "").strip()
    if not original_url: return ""
    if original_url in ARTICLE_DETAIL_CACHE: return ARTICLE_DETAIL_CACHE[original_url]
    url=decode_google_news_url(original_url)
    if url in ARTICLE_DETAIL_CACHE:
        ARTICLE_DETAIL_CACHE[original_url]=ARTICLE_DETAIL_CACHE[url]
        return ARTICLE_DETAIL_CACHE[url]
    if _is_google_host(urllib.parse.urlparse(url).hostname):
        ARTICLE_DETAIL_CACHE[original_url]=""
        DISCOVERY_STATS["google_intermediaire_non_resolu"]+=1
        return ""
    if existing:
        budget=max(1,int(os.getenv("EXISTING_DETAIL_BUDGET","6") or "6"))
        if EXISTING_DETAIL_USED>=budget:
            return ""
        EXISTING_DETAIL_USED+=1
    else:
        env_name="TARGETED_DETAIL_BUDGET" if targeted else "ARTICLE_DETAIL_BUDGET"
        default="160" if targeted else "96"
        budget=max(1,int(os.getenv(env_name,default) or default))
        if ARTICLE_DETAIL_USED>=budget:
            return ""
        ARTICLE_DETAIL_USED+=1
    try:
        req=urllib.request.Request(url,headers={
            "User-Agent":"Mozilla/5.0 GeoClic/3.0",
            "Accept":"text/html,application/xhtml+xml"
        })
        with urllib.request.urlopen(req,timeout=5) as r:
            final_url=r.geturl()
            body=r.read(350000).decode("utf-8","replace")
        # Si la résolution Google a échoué, la page intermédiaire n'est pas du contenu éditorial.
        if _is_google_host(urllib.parse.urlparse(final_url).hostname):
            ARTICLE_DETAIL_CACHE[url]=""
            ARTICLE_DETAIL_CACHE[original_url]=""
            DISCOVERY_STATS["google_intermediaire_non_resolu"]+=1
            return ""
        parser=ArticleHTMLExtractor()
        try:
            parser.feed(body)
        except Exception as parse_exc:
            print("ARTICLE HTML PARSE",url,parse_exc,file=sys.stderr)
        candidates=[strip_html_text(x) for x in parser.descriptions if len(strip_html_text(x))>=80]
        # Fallback : premiers paragraphes significatifs.
        if not candidates:
            candidates=[strip_html_text(x) for x in parser.paragraphs if len(strip_html_text(x))>=100]
            total=0; limited=[]
            for val in candidates:
                limited.append(val); total+=len(val)
                if total>=900: break
            candidates=limited
        unique=[]
        seen_detail=set()
        for val in candidates:
            k=key_title(val)
            if not k or k in seen_detail: continue
            seen_detail.add(k)
            unique.append(val)
        detail=" ".join(unique[:3])
        detail=re.sub(r"\s+"," ",detail).strip()[:1200]
        ARTICLE_DETAIL_CACHE[url]=detail
        ARTICLE_DETAIL_CACHE[original_url]=detail
        if detail:
            DISCOVERY_STATS["contenus_recuperes"]+=1
        else:
            DISCOVERY_STATS["contenus_vides"]+=1
        return detail
    except Exception as exc:
        print("ARTICLE DETAIL",url,exc,file=sys.stderr)
        ARTICLE_DETAIL_CACHE[url]=""
        ARTICLE_DETAIL_CACHE[original_url]=""
        DISCOVERY_STATS["contenus_inaccessibles"]+=1
        return ""

def sentence_words(text):
    stop={"le","la","les","de","des","du","un","une","et","ou","à","au","aux","en","dans","sur","pour","avec","par","qui","que","se","sa","son","ses","ce","ces","cette","est","sont","a","ont"}
    return {w for w in re.findall(r"[a-zà-ÿ0-9]+",(text or "").lower()) if len(w)>2 and w not in stop}

def summaries_same_event(a,b):
    """Détecte les reprises/syndications du même événement sans fusionner des sujets seulement voisins."""
    wa=sentence_words(a); wb=sentence_words(b)
    if not wa or not wb: return False
    inter=len(wa & wb)
    containment=inter/max(1,min(len(wa),len(wb)))
    jaccard=inter/max(1,len(wa | wb))
    if containment>=0.82 or jaccard>=0.68:
        return True
    aliases={name.lower() for name in PERSON_SURNAME_ALIASES}
    ta=" "+(a or "").lower()+" "; tb=" "+(b or "").lower()+" "
    shared_actor={name for name in aliases if term_in_text(ta,name) and term_in_text(tb,name)}
    return bool(shared_actor) and containment>=0.58

def merge_item_into(target,source):
    target["score"]=max(int(target.get("score",0) or 0),int(source.get("score",0) or 0))
    target["countries"]=list(dict.fromkeys(list(target.get("countries",[]) or [])+list(source.get("countries",[]) or [])))
    target["sources"]=list(dict.fromkeys(list(target.get("sources",[]) or [])+list(source.get("sources",[]) or [])))
    if not target.get("url") and source.get("url"):
        target["url"]=source["url"]
    if (source.get("published_at") or "") > (target.get("published_at") or ""):
        target["published_at"]=source.get("published_at")
    if target.get("countries"):
        target["regions"]=regions_for_countries(target["countries"],target["score"])
    else:
        regs=list(dict.fromkeys(list(target.get("regions",[]) or [])+list(source.get("regions",[]) or [])))
        target["regions"]=[r for r in regs if r!="International" or target["score"]>=7]
    # Garder le résumé le plus informatif.
    if len(source.get("summary","")) > len(target.get("summary","")):
        target["summary"]=source.get("summary","")
    return target

def trim_incomplete_tail(text):
    value=clean_summary_text(text)
    if not value: return value
    last=max(value.rfind(". "),value.rfind("! "),value.rfind("? "))
    if last>=0:
        tail=value[last+2:].strip()
        if tail and len(re.findall(r"[a-zà-ÿ0-9]+",tail.lower()))<=7 and not re.search(r'[.!?…»"]$',tail):
            value=value[:last+1].strip()
    return value

def dedupe_summary_sentences(text):
    parts=re.split(r"(?<=[.!?])\s+",clean_summary_text(text))
    out=[]; seen_keys=set(); seen_sets=[]
    for part in parts:
        part=part.strip()
        if not part: continue
        part=part[0].upper()+part[1:]
        k=key_title(part)
        words=sentence_words(part)
        if not k or k in seen_keys: continue
        duplicate=False
        for prev in seen_sets:
            if not words or not prev: continue
            inter=len(words & prev)
            union=len(words | prev)
            containment=inter/max(1,min(len(words),len(prev)))
            jaccard=inter/max(1,union)
            if containment>=0.82 or jaccard>=0.68:
                duplicate=True
                break
        if duplicate: continue
        seen_keys.add(k); seen_sets.append(words); out.append(part)
    return trim_incomplete_tail(" ".join(out))

def _source_identity(label):
    raw=(label or "").strip()
    if not raw: return ""
    raw=re.sub(r"\s*[—-]\s*fiabilité\s+\d+/10.*$","",raw,flags=re.I)
    raw=re.sub(r"\([^)]*\)","",raw).strip()
    host=(urllib.parse.urlparse(raw if "://" in raw else "//"+raw).hostname or "").lower()
    if host:
        raw=host.removeprefix("www.").split(".")[0]
    else:
        raw=raw.lower()
    raw=re.sub(r"[^a-z0-9]+","",raw)
    return {"associatedpress":"ap","apnews":"ap","afp":"agencefrancepresse"}.get(raw,raw)

def _same_publisher(left, right):
    a=_source_identity(left); b=_source_identity(right)
    if not a or not b: return False
    return a==b or (min(len(a),len(b))>=5 and (a.startswith(b) or b.startswith(a)))

class _RSSAnchorParser(HTMLParser):
    """Conserve les liens d'article présents dans le descriptif HTML de Google RSS."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links=[]
        self._href=""
        self._parts=[]

    def handle_starttag(self, tag, attrs):
        if tag.lower()=="a":
            self._href=dict(attrs).get("href","") or ""
            self._parts=[]

    def handle_data(self, data):
        if self._href and data and data.strip():
            self._parts.append(data.strip())

    def handle_endtag(self, tag):
        if tag.lower()=="a" and self._href:
            self.links.append((self._href," ".join(self._parts)))
            self._href=""
            self._parts=[]

def google_rss_publisher_url(raw_description, title, source):
    """Use only an external RSS anchor whose editor and label match the item."""
    parser=_RSSAnchorParser()
    try:
        parser.feed(html_lib.unescape(raw_description or ""))
    except Exception:
        return ""
    matches=[]
    for href,label in parser.links:
        url=_publisher_url(href)
        if not url or not _same_publisher(source,urllib.parse.urlparse(url).hostname or ""):
            continue
        similarity=_title_similarity(title,label)
        if similarity<0.70:
            continue
        matches.append((url,similarity))
    if not matches:
        return ""
    best=max(score for _,score in matches)
    urls={url for url,score in matches if score>=best-0.04}
    return next(iter(urls)) if len(urls)==1 else ""

def _title_similarity(left, right):
    a=key_title(left); b=key_title(right)
    if not a or not b: return 0.0
    aw=set(a.split()); bw=set(b.split())
    overlap=len(aw & bw)/max(1,len(aw | bw))
    return max(overlap,SequenceMatcher(None,a,b).ratio())

def matching_publisher_article_url(article, candidates):
    """Fait le lien par titre proche, même jour et même éditeur, sans deviner le média."""
    title=key_title(article.get("title",""))
    if not title: return ""
    try: day=editorial_day(article["date"])
    except Exception: return ""
    matches=[]
    for candidate in candidates or ():
        candidate_url=(candidate.get("url") or "").strip()
        if not candidate_url or _is_google_host(urllib.parse.urlparse(candidate_url).hostname):
            continue
        try:
            if editorial_day(candidate["date"])!=day: continue
        except Exception:
            continue
        similarity=_title_similarity(article.get("title",""),candidate.get("title",""))
        if similarity<0.78 or not _same_publisher(article.get("source",""),candidate.get("source","")):
            continue
        matches.append((candidate_url,similarity))
    if not matches: return ""
    best=max(similarity for _,similarity in matches)
    best_urls={url for url,similarity in matches if similarity>=best-0.04}
    return next(iter(best_urls)) if len(best_urls)==1 else ""

def resolve_google_news_with_bing(article):
    """Cherche un lien éditeur Bing pour un titre Google News non résolu."""
    global GOOGLE_BING_FALLBACK_USED
    source_url=(article.get("url") or "").strip()
    if not is_google_news_url(source_url) or BING_DISABLED:
        return ""
    budget=max(0,int(os.getenv("GOOGLE_BING_FALLBACK_BUDGET","12") or "12"))
    if GOOGLE_BING_FALLBACK_USED>=budget:
        DISCOVERY_STATS["google_bing_fallback_budget_epuise"]+=1
        return ""
    title=(article.get("title") or "").strip()
    if not title: return ""
    GOOGLE_BING_FALLBACK_USED+=1
    DISCOVERY_STATS["google_bing_fallback_queries"]+=1
    results=bing_rss_query('"'+title.replace('"',' ')+'"')
    publisher_url=matching_publisher_article_url(article,results)
    if not publisher_url:
        DISCOVERY_STATS["google_bing_fallback_no_match"]+=1
        return ""
    GOOGLE_NEWS_URL_CACHE[source_url]=publisher_url
    GOOGLE_NEWS_RESOLVED[source_url]=publisher_url
    DISCOVERY_STATS["google_bing_fallback_success"]+=1
    DISCOVERY_STATS["google_decode_success"]+=1
    return publisher_url

def article_summary(art, meta=None, targeted=False, candidates=None):
    """Le titre découvre l'article ; le contenu décide, avec une réserve pour les pays ciblés."""
    title=(art.get("title") or "").strip()
    url=art.get("url","")
    if not title:
        note_rejection("titre_absent",title,url)
        return None
    if is_google_news_url(url):
        DISCOVERY_STATS["google_cross_feed_match_attempts"]+=1
        cross_feed_url=matching_publisher_article_url(art,candidates)
        publisher_url=cross_feed_url
        if not publisher_url:
            publisher_url=resolve_google_news_with_bing(art)
        if publisher_url:
            GOOGLE_NEWS_URL_CACHE[url]=publisher_url
            GOOGLE_NEWS_RESOLVED[url]=publisher_url
            art["url"]=publisher_url
            url=publisher_url
            if meta is not None:
                meta=dict(meta)
                meta["url"]=publisher_url
            if cross_feed_url:
                DISCOVERY_STATS["google_decode_cross_feed_fallback"]+=1
                DISCOVERY_STATS["google_decode_success"]+=1
        else:
            DISCOVERY_STATS["google_cross_feed_no_match"]+=1
    reason=title_rejection_reason(title)
    if reason:
        note_rejection(reason,title,url)
        return None

    detail=(art.get("description") or "").strip()
    if not detail_is_substantive(title,detail):
        if article_detail_budget_exhausted(targeted=targeted):
            note_rejection("budget_analyse_epuise_cible" if targeted else "budget_analyse_epuise",title,url)
            return None
        detail=fetch_article_detail(url,targeted=targeted)
        resolved_url=GOOGLE_NEWS_RESOLVED.get(url)
        if resolved_url:
            art["url"]=resolved_url
            url=resolved_url
            if meta is not None:
                meta=dict(meta)
                meta["url"]=resolved_url
    if not detail_is_substantive(title,detail):
        note_rejection("contenu_indisponible",title,url)
        return None

    source_text=f"{title}. {detail[:900]}"
    combined=french_summary(source_text,meta)
    if not combined:
        note_rejection("traduction_indisponible",title,url)
        return None
    combined=clean_summary_text(dedupe_summary_sentences(enrich_editorial_context(combined)))
    if len(combined)>700:
        cut=combined[:700]
        stop=max(cut.rfind(". "),cut.rfind("! "),cut.rfind("? "))
        combined=(cut[:stop+1] if stop>320 else cut.rstrip()+"…")
    combined=trim_incomplete_tail(combined)

    reason=content_rejection_reason(combined)
    if reason:
        note_rejection(reason,title,url)
        return None
    DISCOVERY_STATS["articles_valides"]+=1
    return combined

def enrich_existing_item(item):
    """Améliore progressivement les anciennes entrées du jour qui n'ont encore qu'un titre."""
    y=dict(item)
    y["summary"]=dedupe_summary_sentences(enrich_editorial_context(y.get("summary","")))
    if y.get("content_enriched") is True or not y.get("url"):
        return y

    detail=fetch_article_detail(y.get("url",""),existing=True)
    if not detail_is_substantive(y.get("summary",""),detail):
        return y
    detail_fr=french_summary(detail[:900],{
        "countries":y.get("countries",[]),
        "date":y.get("bucket",""),
        "source":(y.get("sources") or ["Source"])[0],
        "url":y.get("url","")
    })
    if not detail_fr:
        return y
    combined=clean_summary_text(dedupe_summary_sentences(
        enrich_editorial_context(f"{y.get('summary','')}. {clean_summary_text(detail_fr)}")
    ))
    combined=trim_incomplete_tail(combined)
    if is_useful_article(combined):
        y["summary"]=combined
        y["content_enriched"]=True
    return y

def regions_for_countries(countries, importance):
    regs=[]
    for country in countries:
        region=COUNTRY_TO_REGION.get(country)
        if region and region not in regs: regs.append(region)
    if importance>=7: regs.append("International")
    return regs

REGION_TEXT_HINTS={
  "Europe":("europe","union européenne","commission européenne","parlement européen","bruxelles","berlin","rhénanie du nord-westphalie"),
  "Asie":("asie","moyen-orient","détroit d'ormuz","détroit d’ormuz","golfe persique"),
  "Amérique du Nord":("amérique du nord","californie","california","ohio","wall street","réserve fédérale","federal reserve","u . s ."),
  "Amérique du Sud":("amérique du sud","mercosur"),
  "Afrique":("afrique","union africaine"),
  "Océanie":("océanie","pacifique sud"),
}
def infer_regions_from_text(text):
    value=(text or "").lower()
    regs=[]
    for region,hints in REGION_TEXT_HINTS.items():
        if any(term_in_text(value,h) for h in hints):
            regs.append(region)
    return regs

GDELT_DOC="https://api.gdeltproject.org/api/v2/doc/doc"
GOOGLE_503_COUNT=0
GOOGLE_DISABLED=False
BING_ERROR_COUNT=0
BING_DISABLED=False
BING_LAST_CALL=0.0
BING_MIN_INTERVAL=0.8
GDELT_429_COUNT=0
GDELT_DISABLED=False
GDELT_LAST_CALL=0.0
GDELT_MIN_INTERVAL=8.0

def gdelt_query(query,maxrecords=250,start_date=None,end_date=None):
    global GDELT_429_COUNT,GDELT_DISABLED,GDELT_LAST_CALL
    if GDELT_DISABLED: return []
    wait=GDELT_MIN_INTERVAL-(time.monotonic()-GDELT_LAST_CALL)
    if wait>0:
        time.sleep(wait)
    GDELT_LAST_CALL=time.monotonic()
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
    data=None
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req,timeout=25) as r:
                data=json.loads(r.read().decode("utf-8","replace"))
            break
        except urllib.error.HTTPError as e:
            if e.code!=429:
                raise
            GDELT_429_COUNT+=1
            print(f"GDELT 429 tentative {attempt+1}/2",file=sys.stderr)
            if attempt==0:
                time.sleep(8)
                continue
            if GDELT_429_COUNT>=6:
                GDELT_DISABLED=True
                print("GDELT désactivé pour ce run après limitations répétées; bascule Google News",file=sys.stderr)
            return []
    if data is None:
        return []
    out=[]
    for art in data.get("articles",[]):
        title=(art.get("title") or "").strip()
        if not title: continue
        seen=art.get("seendate") or ""
        try: dt=datetime.strptime(seen[:14],"%Y%m%dT%H%M%S").replace(tzinfo=UTC)
        except Exception: dt=datetime.now(UTC)
        out.append({"title":title,"source":art.get("domain") or "GDELT","date":dt,"url":art.get("url") or "","description":art.get("description") or art.get("snippet") or ""})
    return out

def bing_direct_url(raw):
    raw=(raw or "").strip()
    if not raw:
        return ""
    try:
        parsed=urllib.parse.urlparse(raw)
        if parsed.netloc.lower().endswith("bing.com") and parsed.path.lower().endswith("/news/apiclick.aspx"):
            q=urllib.parse.parse_qs(parsed.query)
            direct=(q.get("url") or [""])[0]
            if direct:
                return urllib.parse.unquote(direct)
    except Exception:
        pass
    return raw

def bing_rss_query(query):
    """Fallback ciblé : Bing News RSS, avec URL éditeur quand disponible."""
    global BING_ERROR_COUNT,BING_DISABLED,BING_LAST_CALL
    if BING_DISABLED:
        return []
    wait=BING_MIN_INTERVAL-(time.monotonic()-BING_LAST_CALL)
    if wait>0:
        time.sleep(wait)
    BING_LAST_CALL=time.monotonic()
    params={"q":query,"format":"RSS","qft":'interval="7"',"setlang":"fr-fr","cc":"FR"}
    url="https://www.bing.com/news/search?"+urllib.parse.urlencode(params)
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 GeoClic/3.0"})
    root=None
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req,timeout=20) as r:
                root=ET.fromstring(r.read())
            break
        except Exception as exc:
            BING_ERROR_COUNT+=1
            print("BING RSS",query,exc,file=sys.stderr)
            if attempt==0:
                time.sleep(2)
    if root is None:
        if BING_ERROR_COUNT>=4:
            BING_DISABLED=True
            print("Bing News RSS désactivé pour ce run après erreurs répétées",file=sys.stderr)
        return []

    out=[]
    for item in root.findall(".//item"):
        title_el=item.find("title"); link_el=item.find("link"); date_el=item.find("pubDate"); desc_el=item.find("description")
        if title_el is None or date_el is None:
            continue
        try:
            dt=parsedate_to_datetime(date_el.text)
        except Exception:
            continue
        if dt.tzinfo is None:
            dt=dt.replace(tzinfo=UTC)
        title,fallback=clean_title(title_el.text or "")
        direct=bing_direct_url(link_el.text if link_el is not None else "")
        src=""
        for child in list(item):
            if child.tag.lower().endswith("source") and (child.text or "").strip():
                src=(child.text or "").strip()
                break
        if not src:
            try:
                src=urllib.parse.urlparse(direct).netloc.replace("www.","")
            except Exception:
                src=fallback
        out.append({
          "title":title,"source":src or fallback or "Bing News","date":dt,"url":direct,
          "description":strip_html_text(desc_el.text if desc_el is not None else "")
        })
    DISCOVERY_STATS["bing_resultats"]+=len(out)
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
        title_el=item.find("title"); link_el=item.find("link"); date_el=item.find("pubDate"); src_el=item.find("source"); desc_el=item.find("description")
        if title_el is None or date_el is None: continue
        try: dt=parsedate_to_datetime(date_el.text)
        except: continue
        if dt.tzinfo is None: dt=dt.replace(tzinfo=UTC)
        title,fallback=clean_title(title_el.text or ""); src=(src_el.text if src_el is not None else fallback) or fallback
        # Ne pas exclure un média local/étranger simplement parce qu'il n'est pas
        # dans SOURCE_LABELS. La liste sert uniquement à prioriser les sources connues ;
        # la pertinence est décidée ensuite par l'analyse du contenu.
        if not (src or "").strip():
            continue
        if trusted_source(src):
            DISCOVERY_STATS["google_sources_connues"]+=1
        else:
            DISCOVERY_STATS["google_sources_non_referencees"]+=1
        google_url=link_el.text if link_el is not None else ""
        raw_description=desc_el.text if desc_el is not None else ""
        publisher_url=google_rss_publisher_url(raw_description,title,src)
        if publisher_url and is_google_news_url(google_url):
            GOOGLE_NEWS_URL_CACHE[google_url]=publisher_url
            GOOGLE_NEWS_RESOLVED[google_url]=publisher_url
            DISCOVERY_STATS["google_rss_description_fallback"]+=1
            DISCOVERY_STATS["google_decode_success"]+=1
            article_url=publisher_url
        else:
            article_url=google_url
        out.append({"title":title,"source":src,"date":dt,"url":article_url,"description":strip_html_text(raw_description)})
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

SPECIAL_COUNTRY_HINTS={
    "États-Unis":["états-unis","etats-unis","united states","u.s.","u . s ."," usa ","américain","américaine","américains","américaines","californie","california","ohio"],
    "Royaume-Uni":["royaume-uni","united kingdom","britain","british","britannique","britanniques","londres","london"],
    "Allemagne":["allemagne","germany","deutschland","allemand","allemande","allemands","allemandes","berlin","berlinoise","berliner"],
}

def country_title_matches(country,title):
    t=(title or "").lower()
    explicit_specific={
      "Soudan du Sud":["soudan du sud","south sudan"],
      "Guinée-Bissau":["guinée-bissau","guinea-bissau"],
      "Guinée équatoriale":["guinée équatoriale","equatorial guinea"],
      "Papouasie-Nouvelle-Guinée":["papouasie-nouvelle-guinée","papua new guinea"],
      "République dominicaine":["république dominicaine","dominican republic"],
      "Corée du Nord":["corée du nord","north korea"],
      "Corée du Sud":["corée du sud","south korea"],
      "Congo (RDC)":["république démocratique du congo","democratic republic of congo","dr congo","drc","rdc","kinshasa"],
      "Congo (République du)":["république du congo","republic of congo","congo-brazzaville","brazzaville"],
    }
    if country in explicit_specific and any(x in t for x in explicit_specific[country]):
        return True
    # Les États aux noms emboîtés sont validés du plus spécifique au plus général.
    # Une mention explicite d'un autre État de la même famille interdit le classement générique.
    family_exclusions={
      "Soudan":["soudan du sud","south sudan"],
      "Soudan du Sud":[],
      "Guinée":["guinée-bissau","guinea-bissau","guinée équatoriale","equatorial guinea","papouasie-nouvelle-guinée","papua new guinea"],
      "Guinée-Bissau":["guinée équatoriale","equatorial guinea","papouasie-nouvelle-guinée","papua new guinea"],
      "Guinée équatoriale":["papouasie-nouvelle-guinée","papua new guinea"],
      "Niger":["nigeria","nigerian","nigériane","nigérian","nigérians","nigérianes"],
      "Dominique":["république dominicaine","dominican republic"],
      "Corée du Nord":["corée du sud","south korea"],
      "Corée du Sud":["corée du nord","north korea"],
      "Congo (République du)":["république démocratique du congo","democratic republic of congo","rdc","dr congo","drc","kinshasa"],
      "Congo (RDC)":["république du congo","republic of congo","congo-brazzaville","brazzaville"],
    }
    if any(x in t for x in family_exclusions.get(country,[])): return False
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
      "Dominique":["la dominique","île de la dominique","dominica","roseau","commonwealth of dominica"],"République dominicaine":["république dominicaine","dominican republic","santo domingo"],
    }
    if country in SPECIAL_COUNTRY_HINTS and any(term_in_text(t,x) for x in SPECIAL_COUNTRY_HINTS[country]):
        return True
    return any(term_in_text(t,x) for x in hints.get(country,[country.lower()]))

def disambiguate_countries(countries,title):
    """Reclasse les familles de noms ambigus sans confondre un État avec un autre."""
    matched=[c for c in countries if country_title_matches(c,title)]
    t=(title or "").lower()

    # Colombie-Britannique / British Columbia = Canada, jamais Colombie ou Royaume-Uni.
    if "colombie-britannique" in t or "british columbia" in t:
        matched=[c for c in matched if c not in ("Colombie","Royaume-Uni")]
        if "Canada" in countries and "Canada" not in matched:
            matched.append("Canada")

    # Un nom de média du type « Groupe de journaux américain » n'est pas le sujet
    # géographique de l'article. Il faut un autre indice explicite pour classer USA.
    outlet_us=("groupe de journaux américain" in t or "american newspaper group" in t)
    explicit_us=any(x in t for x in (
      "états-unis","etats-unis","united states","washington","réserve fédérale",
      "federal reserve","donald trump","maison-blanche","white house","congrès américain",
      "congress","américains","americans"
    ))
    if outlet_us and not explicit_us:
        matched=[c for c in matched if c!="États-Unis"]

    # Un seul membre d'une famille géographique ambiguë est conservé, sauf article
    # mentionnant explicitement plusieurs États complets.
    families=[
      ["Soudan du Sud","Soudan"],
      ["Papouasie-Nouvelle-Guinée","Guinée équatoriale","Guinée-Bissau","Guinée"],
      ["Nigeria","Niger"],
      ["République dominicaine","Dominique"],
      ["Corée du Nord","Corée du Sud"],
      ["Congo (RDC)","Congo (République du)"],
    ]
    for family in families:
        present=[c for c in family if c in matched]
        if len(present)>1:
            # country_title_matches contient les exclusions ; si plusieurs restent,
            # conserver les mentions réellement explicites plutôt que le terme court.
            explicit=[c for c in present if country_title_matches(c,title)]
            for c in present:
                if c not in explicit: matched.remove(c)
    return list(dict.fromkeys(matched))

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
      # Passe prioritaire : maximiser la détection rapide des événements à fort impact.
      *MAJOR_NEWS_QUERIES,
    ]
    # Google News est volontairement mutualisé : deux appels pour tout le monde, pas 195.
    # Les fournisseurs sont interrogés en parallèle. Une source lente ne bloque plus les autres.
    jobs=[]
    with ThreadPoolExecutor(max_workers=6) as pool:
        if not GOOGLE_DISABLED:
            jobs=[(pool.submit(google_rss_query,q+" when:1d"),"GOOGLE GLOBAL") for q in queries]
        for future,label in jobs:
            try: articles.extend(future.result())
            except Exception as e: print(label,e,file=sys.stderr)
    if not BING_DISABLED:
        bing_global_queries=[
          "(politique OR gouvernement OR diplomatie OR économie OR sécurité OR conflit)",
          *MAJOR_NEWS_QUERIES,
        ]
        for q in bing_global_queries:
            try:
                DISCOVERY_STATS["bing_global_queries"]+=1
                articles.extend(bing_rss_query(q))
            except Exception as e:
                print("BING GLOBAL",e,file=sys.stderr)
    # GDELT est interrogé séquentiellement et cadencé : les appels parallèles précédents
    # provoquaient des 429 puis coupaient la principale source de liens directs.
    if not GDELT_DISABLED:
        gdelt_global_queries=[
          "(government OR election OR diplomacy OR sanctions OR conflict OR security OR economy OR trade OR energy OR climate)",
          "(war OR invasion OR missile OR ceasefire OR coup OR sanctions OR state of emergency OR diplomatic crisis OR peace agreement OR national election OR sovereign default)",
        ]
        for q in gdelt_global_queries:
            DISCOVERY_STATS["gdelt_global_queries"]+=1
            try: articles.extend(gdelt_query(q,150,start_date,end_date))
            except Exception as e: print("GDELT GLOBAL",e,file=sys.stderr)
    articles=prioritize_articles(articles,start_date,end_date)
    rows=[]; found=set(); seen=set()
    for art in articles:
        d=editorial_day(art["date"]); title=art.get("title","")
        if d<start_date or d>end_date or len(title)<22: continue
        matched=disambiguate_countries(countries,title)
        if not matched: continue
        k=(d,key_title(title))
        if not k[1] or k in seen: continue
        summary=article_summary(art,{"countries":matched,"date":fr_date(d),"source":source_name(art["source"]),"url":art["url"]},candidates=articles)
        if not summary: continue
        seen.add(k); found.update(matched)
        s=score(summary)
        regions=regions_for_countries(matched,s)
        rows.append({"regions":regions,"countries":matched,"period":"day","bucket":fr_date(d),"score":s,"category":category(summary),"summary":summary,"sources":[source_name(art["source"])],"url":art["url"],"published_at":art["date"].astimezone(PARIS).isoformat(),"origin":"global","content_enriched":True})
    return rows,found

def time_priority_countries(countries, now):
    """Priorise les zones dont la journée médiatique est active, sans exclure aucun pays."""
    hour=now.astimezone(PARIS).hour
    # Matin France : Asie/Océanie publient déjà; la côte Est/Ouest américaine
    # publie encore en soirée locale, donc elle reste prioritaire également.
    if 0 <= hour < 7:
        priority=["Asie","Océanie","Amérique du Nord","Amérique du Sud","Afrique","Europe"]
    elif 7 <= hour < 13:
        priority=["Asie","Europe","Afrique","Océanie","Amérique du Nord","Amérique du Sud"]
    elif 13 <= hour < 18:
        priority=["Europe","Afrique","Amérique du Nord","Amérique du Sud","Asie","Océanie"]
    else:
        priority=["Amérique du Nord","Amérique du Sud","Europe","Afrique","Asie","Océanie"]
    rank={r:i for i,r in enumerate(priority)}
    return sorted(countries,key=lambda country:(rank.get(COUNTRY_TO_REGION.get(country),99),country))

def country_backfill(start_date,end_date,state):
    rows=[]; found=set()
    themes=["politique OR diplomatie OR gouvernement OR élection OR économie OR sécurité OR conflit OR défense OR migration OR climat OR santé OR société OR justice OR environnement OR catastrophe OR énergie OR technologie OR coopération"]
    all_countries=load_target_countries()
    # Collecte mondiale mutualisée en premier : tous les pays sont traités de manière égale.
    global_rows,global_found=global_country_discovery(start_date,end_date,all_countries)
    rows.extend(global_rows); found.update(global_found)
    # Traitement par lots : 75 % des places ciblent les pays encore sans article,
    # 25 % restent réservées aux pays déjà couverts afin qu'ils continuent à tourner.
    batch_size=max(1,int(os.getenv("COUNTRY_BATCH_SIZE","10") or "10"))
    coverage_state=load_country_coverage()
    missing_set=set(coverage_state.get("missing_countries",[]) or [])
    covered_set=set(coverage_state.get("covered_countries",[]) or [])
    now_for_priority=datetime.now(PARIS)
    missing_ordered=time_priority_countries([c for c in all_countries if c in missing_set],now_for_priority)
    covered_ordered=time_priority_countries([c for c in all_countries if c in covered_set],now_for_priority)

    if missing_ordered and covered_ordered:
        missing_take=max(1,min(len(missing_ordered),(batch_size*3)//4))
        covered_take=max(1,min(len(covered_ordered),batch_size-missing_take))
    elif missing_ordered:
        missing_take=min(batch_size,len(missing_ordered)); covered_take=0
    else:
        missing_take=0; covered_take=min(batch_size,len(covered_ordered))

    countries=[]
    if missing_take:
        moff=int(state.get("country_missing_cursor",0))%len(missing_ordered)
        countries.extend((missing_ordered+missing_ordered)[moff:moff+missing_take])
        state["country_missing_cursor"]=int(state.get("country_missing_cursor",0))+missing_take
    if covered_take:
        coff=int(state.get("country_covered_cursor",0))%len(covered_ordered)
        countries.extend((covered_ordered+covered_ordered)[coff:coff+covered_take])
        state["country_covered_cursor"]=int(state.get("country_covered_cursor",0))+covered_take

    countries=list(dict.fromkeys(countries))
    state["last_targeted_countries"]=list(countries)
    state["last_targeted_count"]=len(countries)
    state["last_targeted_missing_count"]=sum(1 for c in countries if c in missing_set)
    state["last_targeted_covered_count"]=sum(1 for c in countries if c in covered_set)
    # Google couvre tout le lot. GDELT, plus précieux car il fournit des liens directs,
    # n'est utilisé que pour quelques pays par cycle afin de respecter son rate-limit.
    google_budget=max(0,int(os.getenv("GOOGLE_FALLBACK_BUDGET",str(batch_size)) or str(batch_size)))
    gdelt_budget=max(0,int(os.getenv("GDELT_COUNTRY_BUDGET","2") or "2"))
    for country in countries:
        articles=[]
        q=f'{country_query_name(country)} (government OR election OR economy OR security OR conflict OR diplomacy OR climate OR energy OR health OR justice)'
        if gdelt_budget>0 and not GDELT_DISABLED:
            gdelt_budget-=1
            DISCOVERY_STATS["gdelt_country_queries"]+=1
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
                DISCOVERY_STATS["google_country_queries"]+=1
                articles.extend(google_rss_query(f'{country_query_name(country)} (actualité OR politique OR économie OR sécurité OR diplomatie OR climat OR santé) when:1d'))
            except Exception as e:
                print("GOOGLE FALLBACK",country,e,file=sys.stderr)
            time.sleep(0.15)
        if not BING_DISABLED:
            try:
                DISCOVERY_STATS["bing_country_queries"]+=1
                articles.extend(bing_rss_query(f'{country_query_name(country)} (politique OR économie OR sécurité OR diplomatie OR conflit OR climat OR énergie)'))
            except Exception as e:
                print("BING COUNTRY",country,e,file=sys.stderr)
        articles=prioritize_articles(articles,start_date,end_date,country=country)
        seen=set()
        for art in articles:
            d=editorial_day(art["date"]); title=art["title"]
            k=(d,key_title(title))
            if not k[1] or k in seen: continue
            summary=article_summary(art,{"countries":[country],"date":fr_date(d),"source":source_name(art["source"]),"url":art["url"]},targeted=True,candidates=articles)
            if not summary: continue
            seen.add(k)
            s=score(summary)
            found.add(country)
            DISCOVERY_STATS["articles_valides_cibles"]+=1
            rows.append({"regions":regions_for_countries([country],s),"countries":[country],"period":"day","bucket":fr_date(d),"score":s,"category":category(summary),"summary":summary,"sources":[source_name(art["source"])],"url":art["url"],"published_at":art["date"].astimezone(PARIS).isoformat(),"origin":"gdelt" if "GDELT" in source_name(art["source"]) else "rss","content_enriched":True})
    return rows,found

def update_country_coverage(found,now,checked_countries=None):
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
    checked_now=set(checked_countries or [])
    checked=sorted(previous_checked|checked_now)
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
            if not BING_DISABLED:
                try:
                    DISCOVERY_STATS["bing_region_queries"]+=1
                    articles.extend(bing_rss_query(f'({REGIONS[region]}) ({IMPACT_QUERY})'))
                except Exception as e:
                    print("BING REGION",region,a,b,e,file=sys.stderr)
            # Les résultats GDELT mondiaux sont classés localement par pays/région.
            # Ne pas refaire sept appels GDELT par continent : cela provoquait des 429.
            articles=prioritize_articles(articles,start_date,end_date)
            for art in articles:
                d=editorial_day(art["date"]); title=art["title"]
                k=(d,key_title(title))
                if not k[1] or k in seen: continue
                summary=article_summary(art,{"regions":[region],"date":fr_date(d),"source":source_name(art["source"]),"url":art["url"]},candidates=articles)
                if not summary: continue
                importance=score(summary)
                # International est strictement réservé aux événements d’importance >= 7.
                if region=="International" and importance<7: continue
                seen.add(k); grouped[d].append({"regions":[region],"period":"day","bucket":fr_date(d),"score":importance,"category":category(summary),"summary":summary,"sources":[source_name(art["source"])],"url":art["url"],"published_at":art["date"].astimezone(PARIS).isoformat(),"origin":"rss","content_enriched":True})
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
    # Les anciennes entrées du jour peuvent provenir de l'ancienne logique « titre seul ».
    # Les enrichir progressivement, sans réécrire massivement tout l'historique.
    today_bucket=fr_date(now.date())
    candidates=[
        i for i,x in enumerate(day_items)
        if x.get("bucket")==today_bucket and x.get("content_enriched") is not True and x.get("url")
    ]
    def existing_priority(i):
        text=(day_items[i].get("summary") or "").lower()
        full=any(name.lower() in text for name in LEADER_LABELS)
        alias=any(re.search(r"(?i)\\b"+re.escape(name)+r"\\b",text) for name in PERSON_SURNAME_ALIASES)
        return (0 if full else (1 if alias else 2),-int(day_items[i].get("score",0) or 0),-(len(day_items[i].get("summary") or "")))
    for i in sorted(candidates,key=existing_priority):
        if EXISTING_DETAIL_USED>=max(1,int(os.getenv("EXISTING_DETAIL_BUDGET","6") or "6")):
            break
        day_items[i]=enrich_existing_item(day_items[i])

    # Règle stricte demandée : aucune entrée automatique du jour ne doit être un simple titre.
    # Les jours historiques sont conservés. Les lots manuels restent conservés s'ils ont déjà
    # été vérifiés humainement ; les flux rss/gdelt/global doivent avoir un contenu enrichi.
    day_items=[
        x for x in day_items
        if x.get("bucket")!=today_bucket
        or x.get("origin") not in ("rss","gdelt","global")
        or x.get("content_enriched") is True
    ]
    # La campagne présidentielle française 2027 appartient exclusivement à
    # data/election.json : elle ne doit jamais alimenter Pays/continents/International.
    day_items=[x for x in day_items if not is_french_2027_presidential(x.get("summary",""))]
    # Nettoyage éditorial : retirer les contenus hors sujet ou sans valeur informative
    # (sport/people/faits divers locaux/SEO/opinions vagues), y compris s'ils avaient
    # auparavant reçu une note artificiellement élevée par un mot-clé générique.
    useful_items=[]
    for x in day_items:
        y=dict(x)
        y["summary"]=trim_incomplete_tail(
            dedupe_summary_sentences(enrich_editorial_context(y.get("summary","")))
        )
        if y.get("bucket")==today_bucket:
            y["sources"]=list(dict.fromkeys(source_name(src) for src in (y.get("sources",[]) or [])))
            reason=content_rejection_reason(y["summary"])
            if reason:
                note_rejection("existant_"+reason,y.get("summary",""),y.get("url",""))
                continue
            useful_items.append(y)
        elif is_useful_article(y["summary"]):
            # Ne pas réécrire massivement l'historique avec le nouveau seuil.
            useful_items.append(y)
    day_items=useful_items
    # Réappliquer la grille courante à tout l'historique Jour à chaque cycle.
    # Les pays déterminent leur continent ; International est ajouté/retiré
    # automatiquement selon la nouvelle note (>= 7), sans supprimer l'article.
    rescored=[]
    for x in day_items:
        y=dict(x)
        summary=y.get("summary","")
        y["score"]=score(summary)
        # Une élection nationale d'un dirigeant est un événement international majeur.
        y["score"]=max(y["score"],election_score(summary))
        # Recalcul canonique des pays/continents. Un article découvert dans un
        # flux régional (ex. Europe) ne doit jamais hériter de cette région si son
        # texte identifie explicitement un pays d'un autre continent.
        countries=disambiguate_countries(load_target_countries(),summary)
        if not countries:
            countries=list(y.get("countries",[]) or [])
        text_regions=infer_regions_from_text(summary)
        if countries:
            y["countries"]=countries
            regs=[r for r in regions_for_countries(countries,y["score"]) if r!="International"]
            for r in text_regions:
                if r not in regs:
                    regs.append(r)
        else:
            # Sans pays identifié, le texte prime sur le flux de découverte.
            regs=list(text_regions) if text_regions else [r for r in list(y.get("regions",[]) or []) if r!="International"]
        if y["score"]>=7:
            if "International" not in regs:
                regs.append("International")
        else:
            regs=[r for r in regs if r!="International"]
        y["regions"]=list(dict.fromkeys(regs))
        rescored.append(y)
    # Un événement doit exister une seule fois par journée civile, quel que
    # soit le flux (pays, continent ou International) qui l'a découvert.
    merged={}
    order=[]
    for y in rescored:
        raw_url=(y.get("url") or "").strip()
        url_key=re.sub(r"[?#].*$","",raw_url).rstrip("/")
        if url_key:
            k=(y.get("bucket"),"url",url_key)
        else:
            k=(y.get("bucket"),"summary",key_title(y.get("summary","")))
        if k not in merged:
            merged[k]=dict(y)
            order.append(k)
            continue
        z=merged[k]
        merge_item_into(z,y)
    day_items=[merged[k] for k in order]

    # Deux médias peuvent republier la même dépêche sous des URL différentes.
    # Fusionner seulement quand le contenu est très proche et que les pays sont compatibles.
    event_deduped=[]
    for y in day_items:
        merged_into_existing=False
        ycountries=set(y.get("countries",[]) or [])
        for z in event_deduped:
            if z.get("bucket")!=y.get("bucket"):
                continue
            zcountries=set(z.get("countries",[]) or [])
            countries_compatible=(not ycountries or not zcountries or bool(ycountries & zcountries))
            if countries_compatible and summaries_same_event(z.get("summary",""),y.get("summary","")):
                merge_item_into(z,y)
                merged_into_existing=True
                break
        if not merged_into_existing:
            event_deduped.append(dict(y))
    day_items=event_deduped
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
    update_country_coverage(found,now,state.get("last_targeted_countries",[]))
    state["last_rejection_stats"]=dict(sorted(REJECTION_STATS.items()))
    state["last_discovery_stats"]=dict(sorted(DISCOVERY_STATS.items()))
    state["last_content_fetches"]=ARTICLE_DETAIL_USED
    state["last_google_decode_used"]=GOOGLE_NEWS_DECODE_USED
    state["last_google_decode_success"]=int(DISCOVERY_STATS.get("google_decode_success",0))
    state["last_gdelt_429_count"]=GDELT_429_COUNT
    state["last_gdelt_disabled"]=GDELT_DISABLED
    state["last_google_disabled"]=GOOGLE_DISABLED
    state["last_bing_error_count"]=BING_ERROR_COUNT
    state["last_bing_disabled"]=BING_DISABLED
    state["last_generated_count"]=len(generated)
    print("rejections",dict(sorted(REJECTION_STATS.items())),"discovery",dict(sorted(DISCOVERY_STATS.items())),
          "content_fetches",ARTICLE_DETAIL_USED,"gdelt_429",GDELT_429_COUNT,file=sys.stderr)
    save_monitor_state(state,now,
        country_step=int(os.getenv("COUNTRY_BATCH_SIZE","12")),
        day_step=int(os.getenv("DAY_BATCH_SIZE","3")) if backfill else 0)
    print("generated",len(generated),"daily items; countries found",len(found),"total",len(out["items"]),
          "cursors",state.get("country_cursor"),state.get("day_cursor"))

if __name__=="__main__": main()

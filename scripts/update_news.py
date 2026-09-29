#!/usr/bin/env python3
import html as html_lib
import json, os, re, sys, time, unicodedata, urllib.error, urllib.parse, urllib.request, xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
from datetime import datetime, timedelta, time as dtime
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
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
}

def enrich_leader_context(text):
    """Précise fonction et pays d'un responsable connu sans inventer le contenu de la source."""
    out=(text or "").strip()

    # Noms complets : normaliser un titre éventuel.
    for name,label in LEADER_LABELS.items():
        if name.lower() not in out.lower() or label.lower() in out.lower():
            continue
        pattern=r"(?i)(?:le |la )?(?:président(?:e)?|premier ministre|première ministre|chancelier|présidente du conseil|trésorier(?: fédéral)?|ministre des finances|général|ministre des affaires étrangères|secrétaire à la défense|ministre de la défense|secrétaire d['’]état)?\s*"+re.escape(name)+r"(?:\s*\([^)]+\))?"
        out=re.sub(pattern,label,out,count=1)

    # Noms de famille seuls, très fréquents dans les titres.
    for alias,(full_name,role) in PERSON_SURNAME_ALIASES.items():
        label=LEADER_LABELS.get(full_name)
        if not label or label.lower() in out.lower() or not re.search(r"(?i)\b"+re.escape(alias)+r"\b",out):
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
}

def enrich_place_context(text):
    """Ajoute le pays d'un lieu infranational connu lorsqu'il n'est pas déjà précisé."""
    out=(text or "").strip()
    # Les noms les plus longs d'abord pour éviter que « Aceh » capture « Aceh du Sud-Est ».
    for place,country in sorted(PLACE_COUNTRIES.items(),key=lambda kv:len(kv[0]),reverse=True):
        if not re.search(r"(?i)\\b"+re.escape(place)+r"\\b",out):
            continue
        if re.search(r"(?i)"+re.escape(place)+r"\\s*\\("+re.escape(country)+r"\\)",out):
            continue
        if re.search(r"(?i)\\b"+re.escape(country)+r"\\b",out):
            continue
        out=re.sub(r"(?i)\\b"+re.escape(place)+r"\\b",lambda m:f"{m.group(0)} ({country})",out,count=1)
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
    return out.strip(" |–—-")

def is_market_listing_noise(text):
    """Détecte fiches boursières/cotations qui ne décrivent aucun événement."""
    raw=clean_summary_text(text)
    t=" "+raw.lower()+" "
    listing_terms=(
      " activité |"," cotation "," cours de l'action "," cours de l’action ",
      " fiche valeur "," action |"," isin "," wkn "," ticker "," valorisation "
    )
    code_like=bool(re.search(r"\\b(?:HK|US|DE|FR|GB|LU|CH)[A-Z0-9]{8,}\\b",raw,re.I) or
                   re.search(r"\\b[A-Z][A-Z0-9]{4,7}\\b",raw))
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
      "service de rencontres","firstdate","célibataires","application de rencontre","dating service"
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
      "guide d'achat","guide d’achat"
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
    corporate_promo=("nous avons expédié","créant des synergies","répondre aux demandes les plus exigeantes","unités en 40 ans","présente sa nouvelle gamme")
    if any(x in t for x in corporate_promo) and not has_strong:
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
      "réflexions sur ","regard sur "
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
    """Priorise d'abord les articles dont le flux fournit déjà du contenu, puis les titres à fort signal."""
    title=(art.get("title") or "").strip()
    has_detail=detail_is_substantive(title,art.get("description") or "")
    source_ok=trusted_source(art.get("source") or "")
    try:
        ts=art.get("date").timestamp()
    except Exception:
        ts=0
    return (0 if has_detail else 1,-score(title),0 if source_ok else 1,-ts)

def prioritize_articles(articles,start_date,end_date,country=None):
    """Trie les titres avant analyse et garde une source de secours par événement."""
    out=[]; seen_urls=set(); per_title=defaultdict(int)
    for art in articles:
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

def article_detail_budget_exhausted(existing=False):
    if existing:
        budget=max(1,int(os.getenv("EXISTING_DETAIL_BUDGET","6") or "6"))
        return EXISTING_DETAIL_USED>=budget
    budget=max(1,int(os.getenv("ARTICLE_DETAIL_BUDGET","96") or "96"))
    return ARTICLE_DETAIL_USED>=budget

def fetch_article_detail(url, existing=False):
    """Récupère une description ou les premiers paragraphes, avec budget strict pour protéger la veille."""
    global ARTICLE_DETAIL_USED,EXISTING_DETAIL_USED
    url=(url or "").strip()
    if not url: return ""
    if url in ARTICLE_DETAIL_CACHE: return ARTICLE_DETAIL_CACHE[url]
    if existing:
        budget=max(1,int(os.getenv("EXISTING_DETAIL_BUDGET","6") or "6"))
        if EXISTING_DETAIL_USED>=budget:
            return ""
        EXISTING_DETAIL_USED+=1
    else:
        budget=max(1,int(os.getenv("ARTICLE_DETAIL_BUDGET","96") or "96"))
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
        # Les pages intermédiaires Google News n'apportent pas le contenu éditorial.
        if "news.google.com" in urllib.parse.urlparse(final_url).netloc.lower():
            ARTICLE_DETAIL_CACHE[url]=""
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
        if detail:
            DISCOVERY_STATS["contenus_recuperes"]+=1
        else:
            DISCOVERY_STATS["contenus_vides"]+=1
        return detail
    except Exception as exc:
        print("ARTICLE DETAIL",url,exc,file=sys.stderr)
        ARTICLE_DETAIL_CACHE[url]=""
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

def article_summary(art, meta=None):
    """Le titre découvre l'article ; le contenu décide s'il mérite d'être publié."""
    title=(art.get("title") or "").strip()
    url=art.get("url","")
    if not title:
        note_rejection("titre_absent",title,url)
        return None
    reason=title_rejection_reason(title)
    if reason:
        note_rejection(reason,title,url)
        return None

    detail=(art.get("description") or "").strip()
    if not detail_is_substantive(title,detail):
        if article_detail_budget_exhausted():
            note_rejection("budget_analyse_epuise",title,url)
            return None
        detail=fetch_article_detail(url)
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

GDELT_DOC="https://api.gdeltproject.org/api/v2/doc/doc"
GOOGLE_503_COUNT=0
GOOGLE_DISABLED=False
GDELT_429_COUNT=0
GDELT_DISABLED=False
GDELT_LAST_CALL=0.0
GDELT_MIN_INTERVAL=3.0

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
        if not trusted_source(src): continue
        out.append({"title":title,"source":src,"date":dt,"url":link_el.text if link_el is not None else "","description":strip_html_text(desc_el.text if desc_el is not None else "")})
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
    "États-Unis":["états-unis","etats-unis","united states","u.s."," usa ","américain","américaine","américains","américaines","washington"],
    "Royaume-Uni":["royaume-uni","united kingdom","britain","british","britannique","britanniques","londres","london"],
}

def country_title_matches(country,title):
    t=(title or "").lower()
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
      "Dominique":["dominique","dominica","roseau"],"République dominicaine":["république dominicaine","dominican republic","santo domingo"],
    }
    if country in SPECIAL_COUNTRY_HINTS and any(x in t for x in SPECIAL_COUNTRY_HINTS[country]):
        return True
    return any(x in t for x in hints.get(country,[country.lower()]))

def disambiguate_countries(countries,title):
    """Reclasse les familles de noms ambigus sans confondre un État avec un autre."""
    matched=[c for c in countries if country_title_matches(c,title)]
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
    # GDELT est interrogé séquentiellement et cadencé : les appels parallèles précédents
    # provoquaient des 429 puis coupaient la principale source de liens directs.
    if not GDELT_DISABLED:
        gdelt_global_queries=[
          "(geopolitics OR diplomacy OR sanctions OR global economy OR security)",
          *MAJOR_NEWS_QUERIES,
        ]
        for q in gdelt_global_queries:
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
        summary=article_summary(art,{"countries":matched,"date":fr_date(d),"source":source_name(art["source"]),"url":art["url"]})
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
    # Traitement par petits lots persistants : chaque run écrit son lot avant que le suivant ne soit traité.
    # Le lot ciblé complète la collecte mondiale sans priorité liée au niveau de couverture.
    batch_size=max(1,int(os.getenv("COUNTRY_BATCH_SIZE","10") or "10"))
    # La rotation de 195 pays est conservée, mais l'ordre du lot s'adapte à
    # l'heure française afin de chercher d'abord là où les rédactions publient.
    ordered=time_priority_countries(list(all_countries),datetime.now(PARIS))
    if ordered:
        offset=int(state.get("country_cursor",0))%len(ordered)
        countries=(ordered+ordered)[offset:offset+min(batch_size,len(ordered))]
    else:
        countries=[]
    state["last_targeted_countries"]=list(countries)
    state["last_targeted_count"]=len(countries)
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
        articles=prioritize_articles(articles,start_date,end_date,country=country)
        seen=set()
        for art in articles:
            d=editorial_day(art["date"]); title=art["title"]
            k=(d,key_title(title))
            if not k[1] or k in seen: continue
            summary=article_summary(art,{"countries":[country],"date":fr_date(d),"source":source_name(art["source"]),"url":art["url"]})
            if not summary: continue
            seen.add(k)
            s=score(summary)
            found.add(country)
            rows.append({"regions":regions_for_countries([country],s),"countries":[country],"period":"day","bucket":fr_date(d),"score":s,"category":category(summary),"summary":summary,"sources":[source_name(art["source"])],"url":art["url"],"published_at":art["date"].astimezone(PARIS).isoformat(),"origin":"gdelt" if "GDELT" in source_name(art["source"]) else "rss","content_enriched":True})
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
            articles=prioritize_articles(articles,start_date,end_date)
            for art in articles:
                d=editorial_day(art["date"]); title=art["title"]
                k=(d,key_title(title))
                if not k[1] or k in seen: continue
                summary=article_summary(art,{"regions":[region],"date":fr_date(d),"source":source_name(art["source"]),"url":art["url"]})
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
        if countries:
            y["countries"]=countries
            regs=regions_for_countries(countries,y["score"])
        else:
            # Sujet réellement régional sans pays identifiable : conserver la
            # région du flux, mais appliquer normalement le seuil International.
            regs=[r for r in list(y.get("regions",[]) or []) if r!="International"]
            if y["score"]>=7 and "International" in (x.get("regions",[]) or []):
                regs.append("International")
        if y["score"]<7:
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
    update_country_coverage(found,now)
    state["last_rejection_stats"]=dict(sorted(REJECTION_STATS.items()))
    state["last_discovery_stats"]=dict(sorted(DISCOVERY_STATS.items()))
    state["last_content_fetches"]=ARTICLE_DETAIL_USED
    state["last_gdelt_429_count"]=GDELT_429_COUNT
    state["last_gdelt_disabled"]=GDELT_DISABLED
    state["last_google_disabled"]=GOOGLE_DISABLED
    state["last_generated_count"]=len(generated)
    print("rejections",dict(sorted(REJECTION_STATS.items())),"discovery",dict(sorted(DISCOVERY_STATS.items())),
          "content_fetches",ARTICLE_DETAIL_USED,"gdelt_429",GDELT_429_COUNT,file=sys.stderr)
    save_monitor_state(state,now,
        country_step=int(os.getenv("COUNTRY_BATCH_SIZE","12")),
        day_step=int(os.getenv("DAY_BATCH_SIZE","3")) if backfill else 0)
    print("generated",len(generated),"daily items; countries found",len(found),"total",len(out["items"]),
          "cursors",state.get("country_cursor"),state.get("day_cursor"))

if __name__=="__main__": main()

#!/usr/bin/env python3
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
NEWS=ROOT/'data'/'news.json'
COVERAGE=ROOT/'data'/'country-coverage.json'
PARIS=ZoneInfo('Europe/Paris')

EVENTS=[
  {
    'regions':['Afrique'],'countries':['Afrique du Sud'],'period':'day','bucket':'23 septembre 2026','score':7,'category':'Économie',
    'summary':"La Banque de réserve sud-africaine relève son taux directeur de 25 points de base à 7,25 %, invoquant des risques haussiers sur l’inflation.",
    'sources':['SAnews','South African Reserve Bank'],'url':'https://www.sanews.gov.za/south-africa/mpc-raises-repo-rate-725','origin':'manual_verified'
  },
  {
    'regions':['Amérique du Sud'],'countries':['Bolivie'],'period':'day','bucket':'19 septembre 2026','score':8,'category':'Économie',
    'summary':"Le Congrès bolivien approuve un accord de prêt de 1,9 milliard de dollars avec le FMI ; le gouvernement supprime ensuite les subventions au diesel dans le cadre du programme de stabilisation.",
    'sources':['Associated Press','FMI'],'url':'https://apnews.com/article/d5ac4a2558132559e1d544807b89d528','origin':'manual_verified'
  },
  {
    'regions':['Asie'],'countries':['Bahreïn'],'period':'day','bucket':'13 septembre 2026','score':8,'category':'Diplomatie',
    'summary':"Bahreïn refuse de participer à la réunion proposée à Oman entre l’Iran et les États du Golfe sur le détroit d’Ormuz tant que ses relations diplomatiques avec Téhéran ne sont pas rétablies.",
    'sources':['AFP','Al Jazeera'],'url':'https://www.aljazeera.com/news/2026/9/12/bahrain-says-it-will-not-participate-in-irans-proposed-hormuz-meeting','origin':'manual_verified'
  },
  {
    'regions':['Europe'],'countries':['Bulgarie'],'period':'day','bucket':'18 septembre 2026','score':7,'category':'Sécurité',
    'summary':"La Bulgarie décide d’équiper des infrastructures critiques de systèmes anti-drones et de renforcer les patrouilles autour des sites de production et de stockage d’armements.",
    'sources':['Reuters','The Sofia Globe'],'url':'https://www.ekathimerini.com/politics/foreign-policy/1315691/bulgaria-to-deploy-anti-drone-systems-at-critical-infrastructure-facilities/','origin':'manual_verified'
  },
  {
    'regions':['Asie'],'countries':['Birmanie'],'period':'day','bucket':'11 septembre 2026','score':7,'category':'Diplomatie',
    'summary':"Min Aung Hlaing effectue une visite d’État au Cambodge et rencontre Hun Sen et Hun Manet, dans le cadre de la reprise des contacts régionaux de la Birmanie avec l’ASEAN.",
    'sources':['Associated Press','Agence Kampuchea Presse'],'url':'https://www.akp.gov.kh/post/detail/380767','origin':'manual_verified'
  }
]

def key(item):
    return (item.get('bucket',''),item.get('summary','').strip().lower())

def main():
    news=json.loads(NEWS.read_text(encoding='utf-8'))
    existing={key(x) for x in news.get('items',[])}
    added=[]
    for event in EVENTS:
        if key(event) not in existing:
            news.setdefault('items',[]).append(event); existing.add(key(event)); added.append(event)
    if not added:
        print('manual backfill: aucun nouvel événement')
        return
    days=set(news.setdefault('buckets',{}).setdefault('day',[]))
    days.update(e['bucket'] for e in added)
    months={'janvier':1,'février':2,'mars':3,'avril':4,'mai':5,'juin':6,'juillet':7,'août':8,'septembre':9,'octobre':10,'novembre':11,'décembre':12}
    def day_key(x):
        p=x.split(); return (int(p[2]),months[p[1]],int(p[0])) if len(p)==3 and p[1] in months else (0,0,0)
    news['buckets']['day']=sorted(days,key=day_key,reverse=True)
    now=datetime.now(PARIS); news['generated_at']=now.isoformat()
    NEWS.write_text(json.dumps(news,ensure_ascii=False,indent=2),encoding='utf-8')

    cov=json.loads(COVERAGE.read_text(encoding='utf-8'))
    covered=set(cov.get('covered_countries',[])); newly={c for e in added for c in e.get('countries',[])}; covered.update(newly)
    all_missing=cov.get('missing_countries',[])
    cov['covered_countries']=sorted(covered); cov['missing_countries']=[c for c in all_missing if c not in covered]
    cov['covered_count']=len(covered); cov['missing_count']=len(cov['missing_countries']); cov['updated_at']=now.isoformat()
    COVERAGE.write_text(json.dumps(cov,ensure_ascii=False,indent=2),encoding='utf-8')
    print('manual backfill:',len(added),'événements ajoutés; couverture',cov['covered_count'])

if __name__=='__main__': main()

"""Keyless public football context; missing coverage is never an empty injury list.

Only past, completed matches supply xG. Player availability is a timestamped
observation, not a retrospectively reconstructed model training feature.
"""
import gzip
import hashlib
import json
import math
import re
import time
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

import engine
from lifecycle import iso, kickoff, record_id

XG_LEAGUES = {'E0':'EPL','D1':'Bundesliga','I1':'Serie_A','SP1':'La_liga','F1':'Ligue_1'}
ESPN_LEAGUES = {'E0':'eng.1','E1':'eng.2','D1':'ger.1','D2':'ger.2','I1':'ita.1','I2':'ita.2',
 'SP1':'esp.1','SP2':'esp.2','F1':'fra.1','F2':'fra.2','N1':'ned.1','B1':'bel.1',
 'P1':'por.1','T1':'tur.1','SC0':'sco.1','SC1':'sco.2'}
ALIASES = {
 'mancity':'manchestercity','manunited':'manchesterunited','manutd':'manchesterunited',
 'nottmforest':'nottinghamforest','nottforest':'nottinghamforest','nottm':'nottinghamforest',
 'wolves':'wolverhamptonwanderers','wolverhampton':'wolverhamptonwanderers',
 'newcastle':'newcastleunited','westham':'westhamunited','brighton':'brightonhovealbion',
 'tottenham':'tottenhamhotspur','spurs':'tottenhamhotspur','leeds':'leedsunited','ipswich':'ipswichtown',
 'leicester':'leicestercity','coventry':'coventrycity','bournemouth':'afcbournemouth',
 'parissg':'parissaintgermain','psg':'parissaintgermain','stetienne':'saintetienne',
 'bayernmunich':'bayernmunchen','bayern':'bayernmunchen','dortmund':'borussiadortmund',
 'einfrankfurt':'eintrachtfrankfurt','mgladbach':'borussiamonchengladbach',
 'borussiamgladbach':'borussiamonchengladbach','leverkusen':'bayerleverkusen',
 'rb leipzig':'rbleipzig','athmadrid':'atleticomadrid','athleticomadrid':'atleticomadrid',
 'athbilbao':'athleticclub','athleticbilbao':'athleticclub','sociedad':'realsociedad',
 'celta':'celtavigo','betis':'realbetis','espanol':'espanyol','alaves':'alaves',
 'inter':'internazionale','intermilan':'internazionale','milan':'acmilan',
 'verona':'hellasverona','spbraga':'braga','sporting':'sportingcp','sportinglisbon':'sportingcp',
 'qpr':'queensparkrangers','sheffieldweds':'sheffieldwednesday','sheffieldwed':'sheffieldwednesday',
 'sheffieldutd':'sheffieldunited','westbrom':'westbromwichalbion',
 'koln':'cologne','hamburg':'hamburger','mainz':'mainz05','rasenballsportleipzig':'rbleipzig',
 'parma':'parmacalcio1913','lacoruna':'deportivolacoruna','santander':'racingsantander',
 'vallecano':'rayovallecano','oviedo':'realoviedo','valladolid':'realvalladolid',
}

def canonical(name):
    text=unicodedata.normalize('NFKD',str(name)).encode('ascii','ignore').decode().lower()
    text=re.sub(r'\b(fc|cf|sc|ac|afc|sv|vfb|vfl|1)\b','',text)
    key=re.sub('[^a-z0-9]','',text)
    # Canonical targets go through the same punctuation / club-prefix removal.
    target=ALIASES.get(key,key)
    return re.sub(r'^(afc|ac)(?=bournemouth|milan)', '', target)

def number(value):
    try:
        n=float(value)
        return n if math.isfinite(n) and n >= 0 else None
    except (ValueError,TypeError):return None

def date(value):
    return engine.parse_date(value)

class Client:
    def __init__(self, root, now=None, budget=100):
        self.root=Path(root); self.root.mkdir(parents=True,exist_ok=True)
        self.now=now or datetime.now(timezone.utc); self.log=[]; self.remaining=budget
        self.blocked=set()
        self.deadline=time.monotonic()+240

    def get(self,key,url,ttl,normalize,headers=None,group=None):
        path=self.root/(key+'.json'); old=None
        if path.exists():
            try:old=json.loads(path.read_text(encoding='utf-8'))
            except (ValueError,OSError):pass
        fetched=date(old.get('fetchedAt')) if old else None
        age=(self.now-fetched).total_seconds() if fetched else None
        if old and age is not None and 0 <= age < ttl:
            result={**old,'status':'cached','checkedAt':iso(self.now),'ageMinutes':round(age/60)}
            self.log.append({k:result.get(k) for k in ('source','url','status','fetchedAt','checkedAt','ageMinutes')})
            return result
        reason='İstek bütçesi doldu' if self.remaining <= 0 else 'Kaynak erişimi bu çalışmada reddedildi'
        if time.monotonic()>self.deadline:reason='Bu çalışmanın ek veri indirme süresi doldu'
        if self.remaining>0 and time.monotonic()<=self.deadline and (group or key) not in self.blocked:
            self.remaining-=1
            try:
                request=urllib.request.Request(url,headers={'User-Agent':'OPUS-football-engine/1.6 (public statistics)',
                    'Accept':'application/json','Accept-Encoding':'gzip',**(headers or {})})
                with urllib.request.urlopen(request,timeout=18) as response:
                    raw=response.read(8_000_001)
                    if len(raw)>8_000_000:raise ValueError('Yanıt boyutu sınırı aşıldı')
                if raw[:2]==b'\x1f\x8b':raw=gzip.decompress(raw)
                if len(raw)>32_000_000:raise ValueError('Açılmış yanıt boyutu sınırı aşıldı')
                payload=normalize(json.loads(raw))
                result={'source':key,'url':url,'fetchedAt':iso(self.now),'checkedAt':iso(self.now),
                        'status':'fresh','ageMinutes':0,'data':payload}
                tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8');tmp.replace(path)
                self.log.append({k:result[k] for k in ('source','url','status','fetchedAt','checkedAt','ageMinutes')})
                return result
            except Exception as exc:
                reason=f'{type(exc).__name__}: {exc}'
                if isinstance(exc,urllib.error.HTTPError) and exc.code in (401,403,429):self.blocked.add(group or key)
        result={'source':key,'url':url,'status':'stale' if old else 'unavailable','checkedAt':iso(self.now),
                'fetchedAt':old.get('fetchedAt') if old else None,'ageMinutes':round(age/60) if age is not None else None,
                'message':reason,'data':old.get('data') if old else None}
        self.log.append({k:v for k,v in result.items() if k!='data'})
        return result

def normalize_xg(payload):
    if not isinstance(payload,dict) or not isinstance(payload.get('dates'),list):raise ValueError('xG şeması geçersiz')
    rows=[]
    for r in payload['dates']:
        h,a=r.get('h',{}),r.get('a',{}); values=r.get('xG') or {}
        hg,ag=number((r.get('goals') or {}).get('h')),number((r.get('goals') or {}).get('a'))
        xh,xa=number(values.get('h')),number(values.get('a'))
        start=date(r.get('datetime'))
        if r.get('isResult') is not True or start is None or None in (hg,ag,xh,xa):continue
        if not h.get('title') or not a.get('title'):continue
        rows.append({'date':start.date().isoformat(),'home':h['title'],'away':a['title'],
                     'hg':hg,'ag':ag,'xgHome':xh,'xgAway':xa,'id':str(r.get('id',''))})
    if not rows:raise ValueError('Tamamlanmış, xG içeren maç bulunamadı')
    return rows

def fetch_xg(client,seasons):
    output={}
    for code,league in XG_LEAGUES.items():
        output[code]=[]
        for year in seasons:
            page=f'https://understat.com/league/{league}/{year}'
            record=client.get(f'xg_{code}_{year}',f'https://understat.com/getLeagueData/{league}/{year}',
                6*3600 if year==max(seasons) else 30*86400,normalize_xg,
                {'X-Requested-With':'XMLHttpRequest','Referer':page},group='understat')
            # Historical xG remains factual even if a refresh fails. Current form
            # displays refresh failure separately and cannot label stale data live.
            output[code].extend(record.get('data') or [])
    return output

def attach_xg(histories,xg):
    matched={}
    for league,rows in histories.items():
        index={}; duplicates=set()
        for item in xg.get(league,[]):
            key=(item['date'],canonical(item['home']),canonical(item['away']))
            if key in index:duplicates.add(key)
            index[key]=item
        n=0
        for row in rows:
            m=engine.normalize_match(row);d=date(m['date'])
            key=(d.date().isoformat() if d else '',canonical(m['home']),canonical(m['away']))
            found=index.get(key)
            if found and key not in duplicates and m['hg']==found['hg'] and m['ag']==found['ag']:
                row['UnderstatHxG']=found['xgHome'];row['UnderstatAxG']=found['xgAway'];n+=1
        matched[league]=n
    return matched

def normalize_fpl(payload):
    if not isinstance(payload.get('teams'),list) or not isinstance(payload.get('elements'),list):raise ValueError('FPL şeması geçersiz')
    teams={str(t['id']):t['name'] for t in payload['teams']}
    if len(teams)<10:raise ValueError('FPL takım listesi eksik')
    players=[]
    for p in payload['elements']:
        if str(p.get('team')) not in teams:continue
        players.append({'id':str(p['id']),'team':teams[str(p['team'])],
          'name':(' '.join([p.get('first_name',''),p.get('second_name','')])).strip() or p.get('web_name',''),
          'position':{1:'Kaleci',2:'Defans',3:'Orta saha',4:'Forvet'}.get(p.get('element_type'),'Bilinmiyor'),
          'status':p.get('status','unknown'),'news':str(p.get('news',''))[:200],
          'reportedAt':p.get('news_added'),'chanceNextRound':p.get('chance_of_playing_next_round'),
          'minutes':number(p.get('minutes')),'seasonXg':number(p.get('expected_goals'))})
    if not players:raise ValueError('FPL oyuncu listesi boş')
    return {'teams':list(teams.values()),'players':players}

def normalize_scoreboard(payload):
    if not isinstance(payload.get('events'),list):raise ValueError('ESPN fikstür şeması geçersiz')
    rows=[]
    for e in payload['events']:
        comps=e.get('competitions') or []
        if not comps:continue
        sides={c.get('homeAway'):c.get('team',{}) for c in comps[0].get('competitors',[])}
        if not all(sides.get(s,{}).get('id') and sides[s].get('displayName') for s in ('home','away')):continue
        rows.append({'id':str(e['id']),'date':e.get('date'),'status':(e.get('status') or {}).get('type',{}).get('state'),
                     **{s:{'id':str(sides[s]['id']),'name':sides[s]['displayName']} for s in ('home','away')}})
    return rows

def normalize_roster(payload):
    if payload.get('status')!='success' or not isinstance(payload.get('athletes'),list):raise ValueError('ESPN kadro şeması geçersiz')
    rows=[{'id':str(p['id']),'name':p.get('displayName',''),'position':(p.get('position') or {}).get('displayName',''),
           'jersey':p.get('jersey')} for p in payload['athletes'] if p.get('id') and p.get('displayName')]
    if len(rows)<11:raise ValueError('Takım kadrosu yetersiz')
    return {'teamId':str((payload.get('team') or {}).get('id','')),'players':rows,'sourceUpdatedAt':payload.get('timestamp')}

def normalize_lineups(payload):
    if not isinstance(payload,dict) or not isinstance(payload.get('rosters'),list):raise ValueError('Kesin kadro henüz yayımlanmadı')
    result={}
    for side in payload['rosters']:
        players=[]
        for r in side.get('roster',[]):
            a=r.get('athlete') or {}
            if r.get('starter') is True and a.get('id') and a.get('displayName'):
                players.append({'id':str(a['id']),'name':a['displayName'],'position':(r.get('position') or {}).get('displayName',''),'jersey':r.get('jersey')})
        if len(players)==11 and len({p['id'] for p in players})==11:
            result[str((side.get('team') or {}).get('id'))]={'players':players,'formation':side.get('formation')}
    return result

def usable(record):return record and record.get('status') in ('fresh','cached')

def match_event(fixture,events):
    f=engine.normalize_match(fixture);start=kickoff(fixture)
    matches=[]
    for e in events or []:
        t=date(e.get('date'))
        if start and t and abs((start-t).total_seconds())<=900 and all(canonical(e[s]['name'])==canonical(f[s]) for s in ('home','away')):
            matches.append(e)
    return matches[0] if len(matches)==1 else None

def context_for_fixture(league,fixture,fpl,events,rosters,lineups,now):
    f=engine.normalize_match(fixture); start=kickoff(fixture)
    out={'home':{},'away':{},'observedAt':iso(now),'notes':[]}
    event=match_event(fixture,events)
    for side in ('home','away'):
        team=out[side];team['squad']={'status':'unavailable','players':[]}
        team['availability']={'status':'unsupported','players':[],'source':None}
        team['lineup']={'status':'not_published','players':[]}
        if league=='E0':
            team['availability']={'status':fpl.get('status','unavailable'),'source':'FPL','url':'https://fantasy.premierleague.com/statistics',
                 'fetchedAt':fpl.get('fetchedAt'),'players':[]}
            players=[p for p in (fpl.get('data') or {}).get('players',[]) if canonical(p['team'])==canonical(f[side])]
            if players:
                team['squad']={'status':fpl['status'],'source':'FPL','fetchedAt':fpl.get('fetchedAt'),'players':players}
                team['availability']['players']=[p for p in players if p['status'] in ('i','d','s','u')]
            elif usable(fpl):team['availability']['status']='unmatched'
        if event:
            tid=event[side]['id'];r=rosters.get(league+'|'+tid)
            if r and r.get('data') and (r['data'].get('teamId') in ('',tid)):
                team['squad']={**r,'source':'ESPN','players':r['data']['players']};team['squad'].pop('data',None)
            lr=lineups.get(event['id']);found=((lr or {}).get('data') or {}).get(tid)
            if lr and found and usable(lr) and start and now<start and event.get('status')=='pre':
                team['lineup']={'status':'confirmed','source':'ESPN','fetchedAt':lr['fetchedAt'],**found}
    if not event:out['notes'].append('Maç iki takım ve başlama saatiyle ESPN kaydına eşleştirilemedi; başka maçın kadrosu kullanılmadı.')
    out['notes'].append('Sakatlık ve oyuncu listeleri zaman damgalı ek bilgidir. Geçmiş maç öncesi arşivi oluşmadan olasılıklara rastgele yüzde etkisi eklenmez.')
    return out

def collect_context(client,fixtures):
    fpl=client.get('fpl','https://fantasy.premierleague.com/api/bootstrap-static/',1800,normalize_fpl,group='fpl')
    events={};rosters={};lineups={};today=client.now.strftime('%Y%m%d')
    upcoming=[f for f in fixtures if kickoff(f) and client.now<kickoff(f)<=client.now+timedelta(days=7)]
    end=max((kickoff(f) for f in upcoming),default=client.now).strftime('%Y%m%d')
    for code in sorted({f.get('Div') or f.get('league') for f in upcoming} & set(ESPN_LEAGUES)):
        league=ESPN_LEAGUES[code]
        r=client.get(f'events_{code}',f'https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/scoreboard?dates={today}-{end}&limit=100',1800,normalize_scoreboard,group='espn_events_'+code)
        # Old scoreboard schedules cannot confirm a match's current lineup.
        events[code]=(r.get('data') or []) if usable(r) else []
    # Check every league before spending the remaining budget on team rosters.
    # Request only exact fixture matches and prioritize the nearest kickoffs.
    matched=[]
    for f in sorted(upcoming,key=kickoff):
        code=f.get('Div') or f.get('league');event=match_event(f,events.get(code))
        if event:matched.append((code,event))
    for code,event in matched:
        league=ESPN_LEAGUES[code];start=date(event['date'])
        if start and client.now<start<=client.now+timedelta(minutes=90) and event.get('status')=='pre':
            lineups[event['id']]=client.get('lineup_'+event['id'],f'https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/summary?event={event["id"]}',900,normalize_lineups,group='espn_lineups')
    for code,event in matched:
        league=ESPN_LEAGUES[code]
        for side in ('home','away'):
            t=event[side];key=code+'|'+t['id']
            if key in rosters:continue
            rosters[key]=client.get('roster_'+code+'_'+t['id'],f'https://site.api.espn.com/apis/site/v2/sports/soccer/{league}/teams/{t["id"]}/roster',86400,normalize_roster,group='espn_rosters_'+code)
    return {record_id(f.get('Div') or f.get('league'),f):context_for_fixture(f.get('Div') or f.get('league'),f,fpl,events.get(f.get('Div') or f.get('league')),rosters,lineups,client.now) for f in upcoming}

def register_context(records,league,fixture,context,now):
    start=kickoff(fixture)
    if not start or now>=start:return
    key=record_id(league,fixture)
    previous=next((r for r in records if r['id']==key),None)
    snapshot=json.loads(json.dumps(context))
    if previous:previous.update(latestAt=iso(now),latest=snapshot)
    else:records.append({'id':key,'league':league,'kickoffAt':iso(start),'firstAt':iso(now),'first':snapshot,'latestAt':iso(now),'latest':snapshot})

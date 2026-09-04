import csv, io, json, os, urllib.request, time
from datetime import datetime, timezone
from pathlib import Path
from engine import predict, backtest, normalize_match
from lifecycle import audit_and_settle, eligibility, kickoff, iso, register_prediction, record_id
import forecast_audit
import external_data
from quality_model import VERSION, ensure_model, predict as calibrated_predict

ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'; RAW=ROOT/'raw'; DATA.mkdir(exist_ok=True); RAW.mkdir(exist_ok=True)
LEAGUES={'E0':'Premier League','E1':'Championship','D1':'Bundesliga','D2':'Bundesliga 2','I1':'Serie A','I2':'Serie B','SP1':'La Liga','SP2':'La Liga 2','F1':'Ligue 1','F2':'Ligue 2','N1':'Eredivisie','B1':'Belgium 1','P1':'Portugal 1','T1':'Türkiye Süper Lig','SC0':'Scotland Premiership','SC1':'Scotland Championship'}
SEASONS=['2627','2526','2425']
UA='Mozilla/5.0 OPUS-Probability-Engine/1.2 (research; CSV client)'
FIXTURE_URLS=[
    'https://www.football-data.co.uk/fixtures.csv',
    # legacy/fallback path retained only if provider redirects differently in future
    'https://www.football-data.co.uk/matches/resources/fixtures.csv',
]
REQUIRED_FIXTURE_FIELDS={'Div','Date','HomeTeam','AwayTeam'}

def nowiso(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')
def get(url,retries=3):
    err=None
    for i in range(retries):
        try:
            req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'text/csv,text/plain,*/*'})
            with urllib.request.urlopen(req,timeout=30) as r:
                b=r.read()
                if len(b)<20: raise RuntimeError('boş/kısa yanıt')
                return b
        except Exception as e:
            err=e; time.sleep(1.2*(i+1))
    raise err

def parse_csv_bytes(b):
    txt=b.decode('utf-8-sig',errors='replace')
    return list(csv.DictReader(io.StringIO(txt)))

def csv_headers(b):
    txt=b.decode('utf-8-sig',errors='replace')
    reader=csv.reader(io.StringIO(txt))
    try:return [x.strip() for x in next(reader)]
    except StopIteration:return []

def fixture_payload_is_valid(b):
    headers=set(csv_headers(b))
    if not REQUIRED_FIXTURE_FIELDS.issubset(headers):
        return False, sorted(headers)
    rows=parse_csv_bytes(b)
    recognized=sum(1 for r in rows if (r.get('Div') or '').strip() in LEAGUES and (r.get('HomeTeam') or '').strip() and (r.get('AwayTeam') or '').strip())
    return recognized>0, sorted(headers)

def atomic_json(path,obj):
    tmp=path.with_suffix(path.suffix+'.tmp'); tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8'); tmp.replace(path)
def load_json(path,default):
    try:return json.loads(path.read_text(encoding='utf-8'))
    except:return default

def recent_download(key,path,seconds):
    if not path.exists():return None
    stamp=load_json(RAW/'fetch-times.json',{}).get(key)
    parsed=external_data.date(stamp)
    if parsed and 0 <= (datetime.now(timezone.utc)-parsed).total_seconds() < seconds:return stamp
    return None

def remember_download(key):
    path=RAW/'fetch-times.json'; stamps=load_json(path,{})
    stamps[key]=nowiso();atomic_json(path,stamps)

def fetch_cached(url,key,log):
    p=RAW/f'{key}.csv'
    stamp=recent_download(key,p,7200)
    if stamp:
        b=p.read_bytes()
        if {'Date','HomeTeam','AwayTeam','FTHG','FTAG'}.issubset(csv_headers(b)):
            log.append({'ok':True,'source':key,'url':url,'checkedAt':stamp,'message':'İki saatlik indirme aralığı dolmadı; doğrulanmış yerel veri'})
            return parse_csv_bytes(b),False
    try:
        b=get(url)
        if not {'Date','HomeTeam','AwayTeam','FTHG','FTAG'}.issubset(csv_headers(b)):
            raise ValueError('Sonuç CSV şeması geçersiz; son iyi önbellek korundu')
        p.write_bytes(b); remember_download(key);log.append({'ok':True,'source':key,'url':url,'checkedAt':nowiso(),'message':f'{len(b)} bayt kontrol edildi'})
        return parse_csv_bytes(b),False
    except Exception as e:
        if p.exists():
            log.append({'ok':True,'stale':True,'source':key,'url':url,'message':f'canlı indirme başarısız; son iyi önbellek kullanıldı: {e}'})
            return parse_csv_bytes(p.read_bytes()),True
        log.append({'ok':False,'source':key,'url':url,'message':str(e)})
        return [],True

def fetch_fixtures(log):
    p=RAW/'fixtures.csv'
    stamp=recent_download('fixtures',p,1800)
    if stamp:
        b=p.read_bytes();valid,headers=fixture_payload_is_valid(b)
        if valid:
            log.append({'ok':True,'source':'fixtures','url':FIXTURE_URLS[0],'checkedAt':stamp,'message':'30 dakikalık indirme aralığı dolmadı; doğrulanmış fikstür'})
            return parse_csv_bytes(b),False,FIXTURE_URLS[0],headers
    errors=[]
    for url in FIXTURE_URLS:
        try:
            b=get(url)
            valid,headers=fixture_payload_is_valid(b)
            if not valid:
                errors.append(f'{url}: geçersiz fikstür CSV şeması; headers={headers[:12]}')
                log.append({'ok':False,'source':'fixtures_candidate','url':url,'message':errors[-1]})
                continue
            rows=parse_csv_bytes(b)
            p.write_bytes(b)
            remember_download('fixtures')
            recognized=sum(1 for r in rows if (r.get('Div') or '').strip() in LEAGUES)
            log.append({'ok':True,'source':'fixtures','url':url,'message':f'{len(rows)} satır; {recognized} desteklenen lig fikstürü'})
            return rows,False,url,headers
        except Exception as e:
            errors.append(f'{url}: {e}')
            log.append({'ok':False,'source':'fixtures_candidate','url':url,'message':str(e)})
    if p.exists():
        b=p.read_bytes(); valid,headers=fixture_payload_is_valid(b)
        if valid:
            rows=parse_csv_bytes(b)
            recognized=sum(1 for r in rows if (r.get('Div') or '').strip() in LEAGUES)
            log.append({'ok':True,'stale':True,'source':'fixtures','url':'cache','message':f'canlı kaynaklar başarısız; son doğrulanmış cache kullanıldı: {len(rows)} satır; {recognized} desteklenen'})
            return rows,True,'cache',headers
    log.append({'ok':False,'source':'fixtures','message':'Doğrulanmış fikstür verisi bulunamadı. ' + ' | '.join(errors)})
    return [],True,None,[]

def load_ledger(path):
    if not path.exists():
        return {'predictions':[]}
    # A corrupt ledger must stop the update rather than silently erase history.
    ledger=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(ledger,dict) or not isinstance(ledger.get('predictions'),list):
        raise ValueError('Tahmin defteri okunamadı; güncelleme durduruldu')
    return ledger

def main():
    log=[]; histories={}; stale_sources=0; stale_leagues=set()
    for code,name in LEAGUES.items():
        rows=[]
        for s in SEASONS:
            url=f'https://www.football-data.co.uk/mmz4281/{s}/{code}.csv'
            a,stale=fetch_cached(url,f'{s}_{code}',log); stale_sources+=int(stale); rows+=a
            if stale: stale_leagues.add(code)
        histories[code]=rows

    fixtures,stale,fixture_source,fixture_headers=fetch_fixtures(log); stale_sources+=int(stale)
    fixture_stale=stale
    fixture_rows=len(fixtures)
    recognized_rows=sum(1 for r in fixtures if (r.get('Div') or r.get('League') or '').strip() in LEAGUES)

    ledger_path=DATA/'ledger.json'; ledger=load_ledger(ledger_path)
    records=ledger.get('predictions',[])
    forecast_path=DATA/'forecast-ledger.json'
    forecasts=load_ledger(forecast_path)['predictions']
    external=external_data.Client(RAW/'external',budget=100)
    years=sorted({2000+int(s[:2]) for s in SEASONS})
    xg=external_data.fetch_xg(external,years)
    xg_matched=external_data.attach_xg(histories,xg)
    print('External xG matched:',xg_matched,flush=True)
    contexts=external_data.collect_context(external,fixtures)
    context_path=DATA/'context-ledger.json'
    context_records=load_ledger(context_path)['predictions']
    artifact=ensure_model(histories,DATA/'model.json')
    forecast_audit.settle(forecasts,histories,datetime.now(timezone.utc))
    results=audit_and_settle(records,histories,datetime.now(timezone.utc),fixtures)
    predictions=[]; skipped=[]
    for row in fixtures:
        code=(row.get('Div') or row.get('League') or '').strip()
        if code not in LEAGUES:continue
        f=normalize_match(row); f['date']=row.get('Date') or f['date']; f['time']=row.get('Time') or ''
        if not f['home'] or not f['away'] or not f['date']:
            skipped.append({'league':code,'date':f.get('date'),'home':f.get('home'),'away':f.get('away'),'reason':'Fikstür satırında tarih/takım alanı eksik'})
            continue
        reason=eligibility(code,f,results,datetime.now(timezone.utc))
        if reason:
            skipped.append({'league':code,'date':f['date'],'home':f['home'],'away':f['away'],'reason':reason})
            continue
        pr=calibrated_predict(artifact,code,histories.get(code,[]),f)
        if not pr['ok']:
            skipped.append({'league':code,'date':f['date'],'home':f['home'],'away':f['away'],'reason':pr['reason']}); continue
        if fixture_stale or code in stale_leagues:
            for candidate in pr['decision']['candidates']:
                candidate.update(tier='PAS',score=0,reason='Kaynak kontrolü başarısız; eski veriyle aday oluşturulmaz. '+candidate['reason'])
            pr['decision']['best']={'market':None,'tier':'PAS','p':None,'marketP':None,'edge':None,'score':0,
                                   'reason':'Kaynak kontrolü başarısız; yalnız analiz gösteriliyor'}
        # Recheck after computation in case kickoff occurred while the model ran.
        created=datetime.now(timezone.utc)
        if eligibility(code,f,results,created):
            skipped.append({'league':code,'date':f['date'],'home':f['home'],'away':f['away'],'reason':'Hesaplama sırasında başlama saati geçti'})
            continue
        d=pr['decision']['best']; mid=record_id(code,f)
        rec={'id':mid,'league':code,'leagueName':LEAGUES[code],'date':f['date'],'time':f.get('time',''),'home':f['home'],'away':f['away'],'lambdaH':pr['strengths']['lambdaH'],'lambdaA':pr['strengths']['lambdaA'],'reliability':pr['strengths']['reliability'],'topScores':pr['model']['scores'],'model':{k:pr['model'][k] for k in ['HOME','DRAW','AWAY','U25','O25','BTTS_YES','BTTS_NO']},'market':pr['market'],'decision':d}
        rec.update(kickoffAt=iso(kickoff(f)),candidates=pr['decision']['candidates'],calculatedAt=iso(created))
        rec.update(modelVersion=VERSION,modelId=pr['modelId'],context=pr['context'],rawModel=pr['rawModel'],
                   sampleHome=pr['strengths']['nH'],sampleAway=pr['strengths']['nA'])
        rec['enrichment']=contexts.get(mid,{'home':{},'away':{},'notes':['Ek veri henüz alınamadı.']})
        for field in ('injuries','suspensions'):
            rec['context']['availability'][field]=all(rec['enrichment'].get(s,{}).get('availability',{}).get('status') in ('fresh','cached') for s in ('home','away'))
        rec['context']['availability']['lineups']=all(rec['enrichment'].get(s,{}).get('lineup',{}).get('status')=='confirmed' for s in ('home','away'))
        external_data.register_context(context_records,code,f,rec['enrichment'],created)
        observed=forecast_audit.register(forecasts,rec,created)
        if observed:
            rec['firstAnalysisAt']=observed['createdAt']
        locked=register_prediction(records,rec,created)
        if locked:
            rec['lockedPrediction']={k:locked.get(k) for k in ('market','tier','p','marketP','edge','createdAt','forwardTestEligible','modelVersion')}
        predictions.append(rec)

    audit_and_settle(records,histories,datetime.now(timezone.utc),fixtures)
    ledger={'updatedAt':nowiso(),'predictions':sorted(records,key=lambda x:(x.get('auditedKickoffAt') or x['createdAt'],x['league'],x['home']))}
    atomic_json(ledger_path,ledger)
    forecast_audit.settle(forecasts,histories,datetime.now(timezone.utc))
    atomic_json(forecast_path,{'updatedAt':nowiso(),'predictions':forecasts})
    atomic_json(DATA/'model.json',artifact)
    atomic_json(DATA/'model-quality.json',artifact['report'])
    atomic_json(context_path,{'updatedAt':nowiso(),'predictions':context_records})
    enrichment={'updatedAt':nowiso(),'xgMatchedHistory':xg_matched,'sources':external.log,
       'coverage':{code:{'fixtures':sum(p['league']==code for p in predictions),
         'xg':sum(p['league']==code and p['context']['availability']['xg'] for p in predictions),
         'injuries':sum(p['league']==code and p['context']['availability']['injuries'] for p in predictions),
         'squads':sum(p['league']==code and all(p['enrichment'].get(s,{}).get('squad',{}).get('status') in ('fresh','cached') for s in ('home','away')) for p in predictions),
         'lineups':sum(p['league']==code and p['context']['availability']['lineups'] for p in predictions)} for code in LEAGUES}}
    atomic_json(DATA/'enrichment.json',enrichment)
    print('External coverage:',json.dumps(enrichment['coverage']),flush=True)
    summary_path=os.environ.get('GITHUB_STEP_SUMMARY')
    if summary_path:
        lines=['## Dynamic source validation','',
            '| League | Fixtures | xG | Player status | Squads | Confirmed XI |',
            '|---|---:|---:|---:|---:|---:|']
        lines += ['| '+code+' | '+' | '.join(str(c[k]) for k in ('fixtures','xg','injuries','squads','lineups'))+' |' for code,c in enrichment['coverage'].items()]
        lines += ['', '| Source | Status | Download time |','|---|---|---|']
        lines += ['| '+s['source']+' | '+s['status']+' | '+str(s.get('fetchedAt') or 'unavailable')+' |' for s in external.log]
        with open(summary_path,'a',encoding='utf-8') as handle:handle.write('\n'.join(lines)+'\n')
    settled=[x for x in ledger['predictions'] if x['status']=='SETTLED' and x.get('forwardTestEligible')]
    live_summary={}
    for code in LEAGUES:
        z=[x for x in settled if x['league']==code]
        live_summary[code]={'n':len(z),'wins':sum(1 for x in z if x['won']),'hitRate':(sum(1 for x in z if x['won'])/len(z) if z else None)}

    health={
        'fixtureSource':fixture_source,
        'fixtureRows':fixture_rows,
        'recognizedFixtures':recognized_rows,
        'fixtureHeaders':fixture_headers,
        'evaluatedFixtures':len(predictions)+len(skipped),
        'predictions':len(predictions),
        'skipped':len(skipped),
        'ledger':len(ledger['predictions']),
        'excludedFromForwardTest':sum(not x.get('forwardTestEligible',False) for x in records),
        'awaitingResults':sum(x.get('displayStatus')=='AWAITING_RESULT' for x in records),
        'fixtureFirstDate':min((iso(kickoff(r)) for r in fixtures if kickoff(r)),default=None),
        'fixtureLastDate':max((iso(kickoff(r)) for r in fixtures if kickoff(r)),default=None),
    }
    finished=datetime.now(timezone.utc)
    predictions=[p for p in predictions if kickoff(p)>finished]
    health['predictions']=len(predictions)
    health['futureFixtureCount']=sum(bool(kickoff(r) and kickoff(r)>finished) for r in fixtures if (r.get('Div') or '').strip() in LEAGUES)
    dashboard={'version':VERSION,'updatedAt':iso(finished),'dataMode':'validated cache-first server-side','refreshIntervalMinutes':30,'sourceTimezone':'Europe/London','staleSources':stale_sources,'health':health,'leagues':LEAGUES,'predictions':predictions,'skipped':skipped,'matrix':{},'ledger':ledger['predictions'],'liveSummary':live_summary,'log':log,
               'quality':artifact['report'],'forecastAudit':forecast_audit.summary(forecasts,VERSION),'enrichment':enrichment}
    atomic_json(DATA/'dashboard.json',dashboard)
    ok=sum(1 for x in log if x.get('ok')); fail=sum(1 for x in log if not x.get('ok'))
    print(f'OPUS V{VERSION} update complete. sources_ok={ok} failed={fail} fixture_rows={fixture_rows} recognized={recognized_rows} predictions={len(predictions)} skipped={len(skipped)} ledger={len(ledger["predictions"])} fixture_source={fixture_source}')

if __name__=='__main__':main()

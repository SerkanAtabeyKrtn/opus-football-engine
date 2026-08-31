import csv, io, json, os, hashlib, urllib.request, time
from datetime import datetime, timezone
from pathlib import Path
from engine import predict, backtest, normalize_match

ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'; RAW=ROOT/'raw'; DATA.mkdir(exist_ok=True); RAW.mkdir(exist_ok=True)
LEAGUES={'E0':'Premier League','E1':'Championship','D1':'Bundesliga','D2':'Bundesliga 2','I1':'Serie A','I2':'Serie B','SP1':'La Liga','SP2':'La Liga 2','F1':'Ligue 1','F2':'Ligue 2','N1':'Eredivisie','B1':'Belgium 1','P1':'Portugal 1','T1':'Türkiye Süper Lig','SC0':'Scotland Premiership','SC1':'Scotland Championship'}
SEASONS=['2627','2526','2425']
UA='Mozilla/5.0 OPUS-Probability-Engine/1.1 (research; CSV client)'

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
def atomic_json(path,obj):
    tmp=path.with_suffix(path.suffix+'.tmp'); tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8'); tmp.replace(path)
def load_json(path,default):
    try:return json.loads(path.read_text(encoding='utf-8'))
    except:return default

def fetch_cached(url,key,log):
    p=RAW/f'{key}.csv'
    try:
        b=get(url); p.write_bytes(b); log.append({'ok':True,'source':key,'message':f'{len(b)} bayt güncellendi'})
        return parse_csv_bytes(b),False
    except Exception as e:
        if p.exists():
            log.append({'ok':True,'stale':True,'source':key,'message':f'canlı indirme başarısız; son iyi önbellek kullanıldı: {e}'})
            return parse_csv_bytes(p.read_bytes()),True
        log.append({'ok':False,'source':key,'message':str(e)})
        return [],True

def match_id(league,date,home,away):
    s=f'{league}|{date}|{home}|{away}'.lower().strip(); return hashlib.sha1(s.encode()).hexdigest()[:16]
def main():
    log=[]; histories={}; stale_sources=0
    for code,name in LEAGUES.items():
        rows=[]
        for s in SEASONS:
            url=f'https://www.football-data.co.uk/mmz4281/{s}/{code}.csv'
            a,stale=fetch_cached(url,f'{s}_{code}',log); stale_sources+=int(stale); rows+=a
        histories[code]=rows
    fixtures,stale=fetch_cached('https://www.football-data.co.uk/matches/resources/fixtures.csv','fixtures',log); stale_sources+=int(stale)
    ledger_path=DATA/'ledger.json'; ledger=load_json(ledger_path,{'predictions':[]}); existing={x['id']:x for x in ledger.get('predictions',[])}
    predictions=[]; skipped=[]
    for row in fixtures:
        code=row.get('Div') or row.get('League') or ''
        if code not in LEAGUES:continue
        f=normalize_match(row); f['date']=row.get('Date') or f['date']; f['time']=row.get('Time') or ''
        if not f['home'] or not f['away'] or not f['date']:continue
        pr=predict(histories.get(code,[]),f)
        if not pr['ok']:
            skipped.append({'league':code,'date':f['date'],'home':f['home'],'away':f['away'],'reason':pr['reason']}); continue
        d=pr['decision']['best']; mid=match_id(code,f['date'],f['home'],f['away'])
        rec={'id':mid,'league':code,'leagueName':LEAGUES[code],'date':f['date'],'time':f.get('time',''),'home':f['home'],'away':f['away'],'lambdaH':pr['strengths']['lambdaH'],'lambdaA':pr['strengths']['lambdaA'],'reliability':pr['strengths']['reliability'],'topScores':pr['model']['scores'],'model':{k:pr['model'][k] for k in ['HOME','DRAW','AWAY','U25','O25','BTTS_YES','BTTS_NO']},'market':pr['market'],'decision':d}
        predictions.append(rec)
        if d['tier']!='PAS' and mid not in existing:
            existing[mid]={'id':mid,'createdAt':nowiso(),'league':code,'leagueName':LEAGUES[code],'date':f['date'],'home':f['home'],'away':f['away'],'market':d['market'],'tier':d['tier'],'p':d['p'],'marketP':d['marketP'],'edge':d['edge'],'status':'PENDING','hg':None,'ag':None,'won':None}
    # settle ledger from latest histories; never change original prediction fields
    result_index={}
    for code,rows in histories.items():
        for r in rows:
            m=normalize_match(r)
            if m['hg'] is None or m['ag'] is None:continue
            result_index[match_id(code,m['date'],m['home'],m['away'])]=(int(m['hg']),int(m['ag']))
    from engine import outcome
    for mid,x in existing.items():
        if x.get('status')=='PENDING' and mid in result_index:
            hg,ag=result_index[mid]; x['hg']=hg;x['ag']=ag;x['won']=bool(outcome(x['market'],hg,ag));x['status']='SETTLED';x['settledAt']=nowiso()
    ledger={'updatedAt':nowiso(),'predictions':sorted(existing.values(),key=lambda x:(x['date'],x['league'],x['home']))}
    atomic_json(ledger_path,ledger)
    # matrices
    matrices={}
    for code,rows in histories.items():
        if len(rows)>=40:
            try: matrices[code]=backtest(rows)
            except Exception as e: log.append({'ok':False,'source':f'backtest_{code}','message':str(e)})
    settled=[x for x in ledger['predictions'] if x['status']=='SETTLED']
    live_summary={}
    for code in LEAGUES:
        z=[x for x in settled if x['league']==code]
        live_summary[code]={'n':len(z),'wins':sum(1 for x in z if x['won']),'hitRate':(sum(1 for x in z if x['won'])/len(z) if z else None)}
    dashboard={'version':'1.1','updatedAt':nowiso(),'dataMode':'cache-first server-side','staleSources':stale_sources,'leagues':LEAGUES,'predictions':predictions,'skipped':skipped,'matrix':matrices,'ledger':ledger['predictions'],'liveSummary':live_summary,'log':log}
    atomic_json(DATA/'dashboard.json',dashboard)
    ok=sum(1 for x in log if x.get('ok')); fail=sum(1 for x in log if not x.get('ok'))
    print(f'OPUS V1.1 update complete. sources_ok={ok} failed={fail} predictions={len(predictions)} ledger={len(ledger["predictions"])}')
if __name__=='__main__':main()

import math
from functools import lru_cache
from datetime import datetime, timezone

MARKETS = ['U25','O25','BTTS_NO','BTTS_YES','HOME','DRAW','AWAY']
EPS = 1e-12

def clamp(x,a,b): return max(a,min(b,x))
def safe_num(v):
    try:
        if v is None or v == '': return None
        x=float(v)
        return x if math.isfinite(x) else None
    except: return None

@lru_cache(maxsize=16384)
def parse_date(s):
    if isinstance(s, datetime): return s
    if not s: return None
    s=str(s).strip()
    for fmt in ('%d/%m/%Y','%d/%m/%y','%Y-%m-%d','%Y-%m-%dT%H:%M:%S','%Y-%m-%dT%H:%M:%SZ'):
        try: return datetime.strptime(s,fmt).replace(tzinfo=timezone.utc)
        except: pass
    try: return datetime.fromisoformat(s.replace('Z','+00:00')).astimezone(timezone.utc)
    except: return None

def recency_weight(match_date, as_of, half_life=180):
    d,a=parse_date(match_date),parse_date(as_of)
    if not d or not a: return 1.0
    days=max(0,(a-d).total_seconds()/86400)
    return 0.5**(days/half_life)

def effective_n(w):
    s=sum(w); s2=sum(x*x for x in w)
    return s*s/s2 if s2 else 0

def weighted_mean(vals,w):
    z=[(v,ww) for v,ww in zip(vals,w) if v is not None and ww>0]
    if not z:return None
    sw=sum(ww for _,ww in z)
    return sum(v*ww for v,ww in z)/sw

def shrink_ratio(raw,n_eff,k=8): return 1+(raw-1)*(n_eff/(n_eff+k))

def normalize_match(r):
    return {
        'date': r.get('date') or r.get('Date'),
        'time': r.get('time') or r.get('Time') or '',
        'home': r.get('home') or r.get('HomeTeam'),
        'away': r.get('away') or r.get('AwayTeam'),
        'hg': safe_num(r.get('hg') if 'hg' in r else r.get('FTHG')),
        'ag': safe_num(r.get('ag') if 'ag' in r else r.get('FTAG')),
        'oddsH': safe_num(r.get('oddsH') or r.get('B365H') or r.get('AvgH') or r.get('PSH')),
        'oddsD': safe_num(r.get('oddsD') or r.get('B365D') or r.get('AvgD') or r.get('PSD')),
        'oddsA': safe_num(r.get('oddsA') or r.get('B365A') or r.get('AvgA') or r.get('PSA')),
        'oddsO25': safe_num(r.get('oddsO25') or r.get('B365>2.5') or r.get('Avg>2.5') or r.get('P>2.5')),
        'oddsU25': safe_num(r.get('oddsU25') or r.get('B365<2.5') or r.get('Avg<2.5') or r.get('P<2.5')),
        # Optional adapter fields; the current Football-Data CSV has no BTTS odds.
        'oddsBTTSYes': safe_num(r.get('oddsBTTSYes')),
        'oddsBTTSNo': safe_num(r.get('oddsBTTSNo')),
    }

def calculate_strengths(history, home, away, as_of, half_life=180):
    cutoff=parse_date(as_of)
    prior=[]
    for row in history:
        m=normalize_match(row); d=parse_date(m['date'])
        if m['hg'] is not None and m['ag'] is not None and d and cutoff and d < cutoff:
            prior.append(m)
    if len(prior)<20:return {'ok':False,'reason':'Lig geçmişi yetersiz','n':len(prior)}
    lw=[recency_weight(m['date'],as_of,half_life) for m in prior]
    lhome=weighted_mean([m['hg'] for m in prior],lw); laway=weighted_mean([m['ag'] for m in prior],lw)
    if not lhome or not laway:return {'ok':False,'reason':'Lig gol tabanı hesaplanamadı'}
    hh=[m for m in prior if m['home']==home]; aa=[m for m in prior if m['away']==away]
    if len(hh)<3 or len(aa)<3:return {'ok':False,'reason':'Takım ev/deplasman örneklemi yetersiz','nH':len(hh),'nA':len(aa)}
    hhw=[recency_weight(m['date'],as_of,half_life) for m in hh]; aaw=[recency_weight(m['date'],as_of,half_life) for m in aa]
    nH,nA=effective_n(hhw),effective_n(aaw)
    hGF=weighted_mean([m['hg'] for m in hh],hhw); hGA=weighted_mean([m['ag'] for m in hh],hhw)
    aGF=weighted_mean([m['ag'] for m in aa],aaw); aGA=weighted_mean([m['hg'] for m in aa],aaw)
    hAtk=shrink_ratio(hGF/lhome,nH); hDef=shrink_ratio(hGA/laway,nH)
    aAtk=shrink_ratio(aGF/laway,nA); aDef=shrink_ratio(aGA/lhome,nA)
    def form(team):
        arr=[m for m in prior if m['home']==team or m['away']==team]
        arr.sort(key=lambda x: parse_date(x['date']),reverse=True); arr=arr[:8]
        if len(arr)<4:return (1,1)
        gf=[m['hg'] if m['home']==team else m['ag'] for m in arr]; ga=[m['ag'] if m['home']==team else m['hg'] for m in arr]
        w=[0.85**i for i in range(len(arr))]; base=(lhome+laway)/2
        atk=weighted_mean(gf,w)/base; deff=weighted_mean(ga,w)/base
        return clamp(1+0.10*(atk-1),0.90,1.10),clamp(1+0.10*(deff-1),0.90,1.10)
    hfa,hfd=form(home); afa,afd=form(away)
    hAtk*=hfa; hDef*=hfd; aAtk*=afa; aDef*=afd
    lh=clamp(lhome*hAtk*aDef,0.20,3.50); la=clamp(laway*aAtk*hDef,0.20,3.50)
    rel=clamp((min(nH,nA)-2)/10,0,1)
    return {'ok':True,'lambdaH':lh,'lambdaA':la,'leagueHome':lhome,'leagueAway':laway,'hAtk':hAtk,'hDef':hDef,'aAtk':aAtk,'aDef':aDef,'nH':nH,'nA':nA,'reliability':rel}

def pois(k,l): return math.exp(-l)*(l**k)/math.factorial(k)
def score_matrix(lh,la,max_goals=9):
    mx=[[pois(h,lh)*pois(a,la) for a in range(max_goals+1)] for h in range(max_goals+1)]
    total=sum(map(sum,mx))
    return [[p/total for p in row] for row in mx]
def probs_from_matrix(mx):
    H=D=A=U=B=0; scores=[]
    for h,row in enumerate(mx):
        for a,p in enumerate(row):
            if h>a:H+=p
            elif h==a:D+=p
            else:A+=p
            if h+a<=2:U+=p
            if h>0 and a>0:B+=p
            scores.append({'score':f'{h}-{a}','p':p})
    scores.sort(key=lambda x:x['p'],reverse=True)
    return {'HOME':H,'DRAW':D,'AWAY':A,'U25':U,'O25':1-U,'BTTS_YES':B,'BTTS_NO':1-B,'scores':scores[:5]}
def devig(odds):
    vals=[safe_num(x) for x in odds]
    if any(x is None or x<=1 for x in vals):return None
    inv=[1/x for x in vals]; s=sum(inv)
    return [x/s for x in inv]
def market_probabilities(f):
    f=normalize_match(f); out={}
    one=devig([f['oddsH'],f['oddsD'],f['oddsA']])
    if one:out.update(HOME=one[0],DRAW=one[1],AWAY=one[2])
    ou=devig([f['oddsO25'],f['oddsU25']])
    if ou:out.update(O25=ou[0],U25=ou[1])
    btts=devig([f['oddsBTTSYes'],f['oddsBTTSNo']])
    if btts:out.update(BTTS_YES=btts[0],BTTS_NO=btts[1])
    return out
def choose_decision(model,market,reliability):
    c=[]
    for k in MARKETS:
        p=model.get(k); mp=market.get(k); edge=(p-mp) if (p is not None and mp is not None) else None
        tier='PAS'; score=0
        if reliability>=.55:
            if p>=.78 and (edge is None or edge>=.025): tier='GÜVENLİ'; score=3*p+(edge or 0)
            elif p>=.63 and edge is not None and edge>=.05: tier='DENGELİ'; score=4*edge+2*p
            elif .55<=p<.63 and edge is not None and edge>=.08: tier='AGRESİF'; score=5*edge+p
        if reliability<.55: reason='Takım örneklemi yetersiz'
        elif tier!='PAS': reason='Karar eşiğini geçti' if edge is not None else 'Yalnız model olasılığı; piyasa oranı yok'
        elif mp is None: reason='Piyasa oranı yok; dengeli/agresif kıyası yapılamıyor'
        elif p<.55: reason='Model olasılığı karar eşiğinin altında'
        else: reason='Olasılık ve piyasa farkı birlikte karar eşiğini geçmiyor'
        c.append({'market':k,'p':p,'marketP':mp,'edge':edge,'tier':tier,'score':score,'reason':reason})
    active=sorted([x for x in c if x['tier']!='PAS'],key=lambda x:x['score'],reverse=True)
    return {'best':active[0] if active else {'market':None,'tier':'PAS','p':None,'marketP':None,'edge':None,'score':0},'candidates':c}
def predict(history,fixture):
    f=normalize_match(fixture); s=calculate_strengths(history,f['home'],f['away'],f['date'])
    if not s['ok']:return {'ok':False,'reason':s['reason'],'strengths':s}
    model=probs_from_matrix(score_matrix(s['lambdaH'],s['lambdaA'])); market=market_probabilities(f); dec=choose_decision(model,market,s['reliability'])
    return {'ok':True,'fixture':f,'strengths':s,'model':model,'market':market,'decision':dec}
def outcome(market,hg,ag):
    if market=='U25':return int(hg+ag<=2)
    if market=='O25':return int(hg+ag>=3)
    if market=='BTTS_YES':return int(hg>0 and ag>0)
    if market=='BTTS_NO':return int(hg==0 or ag==0)
    if market=='HOME':return int(hg>ag)
    if market=='DRAW':return int(hg==ag)
    if market=='AWAY':return int(hg<ag)
def metrics(records):
    if not records:return {'n':0,'hitRate':None,'brier':None,'logLoss':None,'calibrationGap':None,'score':None}
    b=ll=pm=ym=0; hits=0
    for r in records:
        y=r['y']; p=clamp(r['p'],EPS,1-EPS); hits+=int((p>=.5)==(y==1)); b+=(p-y)**2; ll+=-(y*math.log(p)+(1-y)*math.log(1-p)); pm+=p;ym+=y
    n=len(records); b/=n;ll/=n;pm/=n;ym/=n;cal=abs(pm-ym); sample=1-math.exp(-n/50); quality=clamp(1-b/.25,0,1); calibration=clamp(1-cal/.20,0,1)
    score=100*(.45*quality+.30*calibration+.25*sample)
    return {'n':n,'hitRate':hits/n,'brier':b,'logLoss':ll,'calibrationGap':cal,'score':score}
def backtest(matches,max_matches=700):
    clean=[normalize_match(x) for x in matches]; clean=[x for x in clean if x['hg'] is not None and x['ag'] is not None and parse_date(x['date'])]
    clean.sort(key=lambda x:parse_date(x['date'])); clean=clean[-max_matches:]
    buckets={k:[] for k in MARKETS}; decisions=[]
    for i,f in enumerate(clean):
        if i<30:continue
        pr=predict(clean[:i],f)
        if not pr['ok']:continue
        for k in MARKETS:buckets[k].append({'p':pr['model'][k],'y':outcome(k,f['hg'],f['ag'])})
        d=pr['decision']['best']
        if d['market']:decisions.append({'p':d['p'],'y':outcome(d['market'],f['hg'],f['ag']),'tier':d['tier'],'market':d['market']})
    return {'matrix':{k:metrics(v) for k,v in buckets.items()},'decisionMetrics':metrics(decisions),'decisions':decisions}

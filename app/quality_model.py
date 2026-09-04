"""Chronological calibration and an explicit, independently checked decision gate.

No observed match result, current-match shot count or post-match xG is an input.
The final assessment period is never used to fit coefficients or select penalties.
"""
import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

import calibration
import engine

VERSION = '1.6'
SPEC = 'quality-xg-2026-09-04-b'
LEAGUE_CODES = ['E0','E1','D1','D2','I1','I2','SP1','SP2','F1','F2','N1','B1','P1','T1','SC0','SC1']
FAMILIES = {'result': ['HOME','DRAW','AWAY'], 'goals': ['O25','U25'], 'btts': ['BTTS_YES','BTTS_NO']}
PLAN = {'fitBefore': '2026-01-01', 'selectBefore': '2026-04-01', 'testBefore': '2026-07-01'}
PENALTIES = (30.0, 100.0)


def logit(p):
    p = min(.999, max(.001, p))
    return math.log(p / (1 - p))


def context(history, fixture):
    f = engine.normalize_match(fixture)
    start = engine.parse_date(f['date'])
    output = {}
    values = []
    for side in ('home','away'):
        team = f[side]
        prior = [r for r in history if engine.parse_date(r.get('Date') or r.get('date')) and
                 engine.parse_date(r.get('Date') or r.get('date')) < start and
                 team in (r.get('HomeTeam') or r.get('home'), r.get('AwayTeam') or r.get('away')) and
                 engine.normalize_match(r)['hg'] is not None and engine.normalize_match(r)['ag'] is not None]
        prior.sort(key=lambda r: engine.parse_date(r.get('Date') or r.get('date')), reverse=True)
        ages = [(start - engine.parse_date(r.get('Date') or r.get('date'))).total_seconds()/86400 for r in prior]
        rest = ages[0] if ages else None
        load = sum(age <= 14 for age in ages)
        shots_for, shots_against = [], []
        for r in prior[:8]:
            home = (r.get('HomeTeam') or r.get('home')) == team
            sf, sa = engine.safe_num(r.get('HST' if home else 'AST')), engine.safe_num(r.get('AST' if home else 'HST'))
            if sf is not None and sa is not None and sf >= 0 and sa >= 0:
                shots_for.append(sf)
                shots_against.append(sa)
        shot_balance = ((sum(shots_for) - sum(shots_against)) / len(shots_for) / 5) if shots_for else 0.0
        values += [min(rest if rest is not None else 7, 21)/7, min(load, 6)/3,
                   max(-2, min(2, shot_balance)), len(shots_for)/8]
        output[side] = {'restDays': round(rest,1) if rest is not None else None,
                        'matchesLast14Days': load, 'shotsMatches': len(shots_for),
                        'shotsOnTargetFor': round(sum(shots_for)/len(shots_for),2) if shots_for else None,
                        'shotsOnTargetAgainst': round(sum(shots_against)/len(shots_against),2) if shots_against else None}
        xg=[]
        for r in prior[:8]:
            home=(r.get('HomeTeam') or r.get('home'))==team
            xf,xa=engine.safe_num(r.get('UnderstatHxG' if home else 'UnderstatAxG')),engine.safe_num(r.get('UnderstatAxG' if home else 'UnderstatHxG'))
            if xf is not None and xa is not None and all(math.isfinite(v) and v>=0 for v in (xf,xa)):
                xg.append((xf,xa))
        output[side]['xg']={'matches':len(xg),'for':sum(x[0] for x in xg)/len(xg) if xg else None,
            'against':sum(x[1] for x in xg)/len(xg) if xg else None,'source':'Understat' if xg else None}
    output['scope'] = 'Yalnız mevcut lig geçmişi; kupa, milli takım ve diğer organizasyonlar dahil değil.'
    output['availability'] = {'injuries': False, 'suspensions': False, 'lineups': False, 'xg': False}
    output['availability']['xg']=all(output[s]['xg']['matches']>=3 for s in ('home','away'))
    return values, output


def record(league, history, fixture):
    result = engine.predict(history, fixture)
    if not result['ok']:
        return None
    values, info = context(history, fixture)
    f = engine.normalize_match(fixture)
    return {'league': league, 'date': engine.parse_date(f['date']).date().isoformat(),
            'home': f['home'], 'away': f['away'], 'raw': result['model'],
            'market': result['market'], 'strengths': result['strengths'], 'contextValues': values,
            'context': info, 'odds': {k:f.get(v) for k,v in [('HOME','oddsH'),('DRAW','oddsD'),('AWAY','oddsA'),('O25','oddsO25'),('U25','oddsU25'),('BTTS_YES','oddsBTTSYes'),('BTTS_NO','oddsBTTSNo')]},
            'legacyDecision': result['decision']['best']}


def replay(histories):
    records = []
    for league, rows in histories.items():
        clean = []
        seen = set()
        for r in rows:
            m = engine.normalize_match(r)
            date = engine.parse_date(m['date'])
            key = (date, m['home'], m['away'])
            if date and all(v is not None and v >= 0 and int(v) == v for v in (m['hg'],m['ag'])) and key not in seen:
                clean.append(r)
                seen.add(key)
        clean.sort(key=lambda r: engine.parse_date(r.get('Date') or r.get('date')))
        for i, fixture in enumerate(clean):
            if i < 30:
                continue
            value = record(league, clean[:i], fixture)
            if value is None:
                continue
            match = engine.normalize_match(fixture)
            hg, ag = match['hg'], match['ag']
            value['labels'] = {'result': 0 if hg>ag else 1 if hg==ag else 2,
                               'goals': 0 if hg+ag>2 else 1,
                               'btts': 0 if hg>0 and ag>0 else 1}
            records.append(value)
        print(f'Historical features ready: {league}', flush=True)
    return sorted(records, key=lambda r:(r['date'],r['league'],r['home'],r['away']))


def eligible(row, family, use_market):
    return not use_market or all(k in row['market'] for k in FAMILIES[family])


def features(row, family, use_market=False, use_xg=False):
    markets = FAMILIES[family]
    raw = [row['raw'][k] for k in markets]
    values = [math.log(max(raw[i],.001)/max(raw[-1],.001)) for i in range(len(raw)-1)]
    if use_market:
        market = [row['market'][k] for k in markets]
        values += [math.log(max(market[i],.001)/max(market[-1],.001)) for i in range(len(market)-1)]
    values += row['contextValues']
    if use_xg:
        for side in ('home','away'):
            xg=row.get('context',{}).get(side,{}).get('xg',{})
            n=xg.get('matches',0)
            values += [min(xg.get('for') or 0,6)/3,min(xg.get('against') or 0,6)/3,min(n,8)/8]
    values += [min(row['strengths'][n],30)/10 for n in ('nH','nA')]
    values += [float(row['league']==code) for code in LEAGUE_CODES]
    return values


def train_model(rows, family, use_market, penalty, use_xg=False):
    rows = [r for r in rows if eligible(r,family,use_market)]
    model = calibration.fit([features(r,family,use_market,use_xg) for r in rows],
                            [r['labels'][family] for r in rows],len(FAMILIES[family]),penalty)
    model['useMarket'] = use_market
    model['useXg'] = use_xg
    return model


def probabilities(model, rows, family):
    return calibration.predict(model, [features(r,family,model['useMarket'],model.get('useXg',False)) for r in rows])


def empirical(rows, family):
    k = len(FAMILIES[family])
    counts = np.bincount([r['labels'][family] for r in rows],minlength=k).astype(float) + 1
    return (counts/counts.sum()).tolist()


def benchmark(rows, family, fallback):
    markets = FAMILIES[family]
    return [[r['market'][k] for k in markets] if eligible(r,family,True) else fallback for r in rows]


def calibration_bins(rows, probs, family):
    buckets = []
    for lower, upper in [(0,.2),(.2,.4),(.4,.6),(.6,.8),(.8,1.00001)]:
        # One most-probable outcome per match; never pool complementary events,
        # whose middle bin would otherwise be mechanically calibrated to 50%.
        data = [(max(p),float(r['labels'][family]==int(np.argmax(p)))) for r,p in zip(rows,probs)
                if lower <= max(p) < upper]
        if data:
            buckets.append({'from':lower,'to':min(upper,1),'n':len(data),
                            'predicted':sum(p for p,y in data)/len(data),
                            'observed':sum(y for p,y in data)/len(data)})
    return buckets


def build(histories):
    rows = replay(frozen_histories(histories))
    fit_rows = [r for r in rows if r['date'] < PLAN['fitBefore']]
    select_rows = [r for r in rows if PLAN['fitBefore'] <= r['date'] < PLAN['selectBefore']]
    test_rows = [r for r in rows if PLAN['selectBefore'] <= r['date'] < PLAN['testBefore']]
    if min(len(fit_rows), len(select_rows), len(test_rows)) < 300:
        raise ValueError('Zaman sıralı eğitim / seçim / bağımsız test verisi yetersiz')
    artifact = {'version': VERSION, 'spec': SPEC, 'plan': PLAN, 'families': {}, 'gates': {}}
    report = {'version':VERSION, 'plan':PLAN, 'counts':{'fit':len(fit_rows),'selection':len(select_rows),'test':len(test_rows)},
              'families':{}, 'limitations':['Bağımsız test geçmiş maç simülasyonudur; canlı performans değildir.',
              'Geçmiş CSV oranlarının kayıt saati bilinmiyor; getiriler gerçekleşmiş kazanç olarak yorumlanamaz.',
              'Understat xG kapsamı beş büyük ligle sınırlıdır; diğer liglere xG uydurulmaz.',
              'Oyuncu durumu ve kadro ek bilgi olarak kaydedilir; geçmiş maç öncesi arşivi olmadığından sayısal etkileri eğitilmedi.',
              'Dinlenme ve maç yoğunluğu yalnız kapsanan lig maçlarından hesaplanır.']}
    production_fit = fit_rows + select_rows
    for family, markets in FAMILIES.items():
        candidates = []
        fallback_candidates = []
        for use_market in (False, True):
            selected = [r for r in select_rows if eligible(r,family,use_market)]
            available_fit = [r for r in fit_rows if eligible(r,family,use_market)]
            if min(len(selected),len(available_fit)) < 100:
                continue
            xg_available=sum(r.get('context',{}).get('availability',{}).get('xg',False) for r in available_fit)>=100
            for use_xg in ((False,True) if xg_available else (False,)):
                for penalty in PENALTIES:
                    fitted = train_model(available_fit,family,use_market,penalty,use_xg)
                    predicted = probabilities(fitted, selected, family)
                    score = calibration.metrics(predicted,[r['labels'][family] for r in selected])
                    candidate = {'useMarket':use_market,'useXg':use_xg,'penalty':penalty,'score':score,'model':fitted}
                    candidates.append(candidate)
                    if not use_market:
                        fallback_candidates.append(candidate)
        if not candidates:
            raise ValueError('Kalibrasyon adayı üretilemedi: '+family)
        # Compare candidates on exactly the same validation matches.
        common = [r for r in select_rows if all(eligible(r,family,c['useMarket']) for c in candidates)]
        for c in candidates:
            c['selectionLogLoss'] = calibration.metrics(probabilities(c['model'],common,family),[r['labels'][family] for r in common])['logLoss']
        chosen = min(candidates,key=lambda c:(c['selectionLogLoss'],not c['useMarket'], -c['penalty']))
        fallback = min(fallback_candidates,key=lambda c:c['selectionLogLoss'])
        fitted = train_model(production_fit,family,chosen['useMarket'],chosen['penalty'],chosen['useXg'])
        fallback_model = train_model(production_fit,family,False,fallback['penalty'],fallback['useXg'])
        prior = empirical(production_fit,family)
        artifact['families'][family] = {'model':fitted,'fallback':fallback_model,'prior':prior}
        test = [r for r in test_rows if eligible(r,family,chosen['useMarket'])]
        predicted = probabilities(fitted,test,family)
        raw = [[r['raw'][k] for k in markets] for r in test]
        base = benchmark(test,family,prior)
        labels = [r['labels'][family] for r in test]
        report['families'][family] = {'name':{'result':'Maç sonucu','goals':'2,5 gol','btts':'Karşılıklı gol'}[family],
            'method':('Model + piyasa + maç bağlamı' if chosen['useMarket'] else 'Kalibre model + maç bağlamı')+(' + geçmiş xG' if chosen['useXg'] else ''),
            'usesXg':chosen['useXg'],
            'xgTestMatches':sum(r.get('context',{}).get('availability',{}).get('xg',False) for r in test),
            'selectionCandidates':[{k:c[k] for k in ('useMarket','useXg','penalty','selectionLogLoss')} for c in candidates],
            'selectedPenalty':chosen['penalty'], 'selectionLogLoss':chosen['selectionLogLoss'],
            'old':calibration.metrics(raw,labels),'new':calibration.metrics(predicted,labels),
            'reference':calibration.metrics(base,labels),
            'referenceName':'Piyasa olasılığı' if all(eligible(r,family,True) for r in test) else 'Eğitim dönemi sonuç sıklığı',
            'bins':calibration_bins(test,predicted,family)}
        # Require matched independent evidence for every league/market before an active decision.
        for league in LEAGUE_CODES:
            indices = [i for i,r in enumerate(test) if r['league']==league]
            for j,market in enumerate(markets):
                values = [(predicted[i][j],float(test[i]['labels'][family]==j),base[i][j]) for i in indices]
                n = len(values)
                new_brier = sum((p-y)**2 for p,y,b in values)/n if n else None
                ref_brier = sum((b-y)**2 for p,y,b in values)/n if n else None
                selected_values = [(p,y,b) for i,(p,y,b) in zip(indices,values)
                                   if p >= .55 and test[i]['odds'].get(market) and p*test[i]['odds'][market]-1 >= .05]
                selection_n = len(selected_values)
                calibration_gap = abs(sum(p-y for p,y,b in selected_values)/selection_n) if selection_n else None
                passed = n >= 80 and selection_n >= 30 and new_brier <= ref_brier and calibration_gap <= .08
                reasons = []
                if n < 80: reasons.append('Bağımsız testte en az 80 maç yok')
                if selection_n < 30: reasons.append('Benzer aday kararlarda en az 30 sonuç yok')
                if n and new_brier > ref_brier: reasons.append('Piyasa / referans doğruluğu aşılmadı')
                if calibration_gap is not None and calibration_gap > .08: reasons.append('Olasılık ile gerçekleşen sonuç farkı yüksek')
                artifact['gates'][league+'|'+market] = {'eligible':passed,'n':n,'candidateN':selection_n,
                    'brier':new_brier,'referenceBrier':ref_brier,'calibrationGap':calibration_gap,
                    'reason':'Bağımsız test koşulları sağlandı' if passed else '; '.join(reasons)}
        print(f'Calibration complete: {family}',flush=True)
    report['gates'] = artifact['gates']
    artifact['modelId'] = hashlib.sha256(json.dumps(artifact,sort_keys=True).encode()).hexdigest()[:16]
    report['modelId'] = artifact['modelId']
    artifact['report'] = report
    return artifact


def frozen_histories(histories):
    cutoff = engine.parse_date(PLAN['testBefore'])
    result = {}
    for league,rows in histories.items():
        prior = [r for r in rows if engine.parse_date(r.get('Date') or r.get('date')) and
                 engine.parse_date(r.get('Date') or r.get('date')) < cutoff]
        result[league] = sorted(prior,key=lambda r:(str(r.get('Date') or r.get('date')),str(r.get('HomeTeam') or r.get('home')),str(r.get('AwayTeam') or r.get('away'))))
    return result


def fingerprint(histories):
    # New-season outcomes update team form but cannot silently retune this model.
    payload = json.dumps({'spec':SPEC,'plan':PLAN,'histories':frozen_histories(histories)},sort_keys=True,separators=(',',':'))
    return hashlib.sha256(payload.encode()).hexdigest()


def ensure_model(histories, path):
    key = fingerprint(histories)
    if path.exists():
        artifact = json.loads(path.read_text(encoding='utf-8'))
        if artifact.get('spec') == SPEC and artifact.get('inputFingerprint') == key:
            return artifact
    artifact = build(histories)
    artifact['inputFingerprint'] = key
    return artifact


def predict(artifact, league, history, fixture):
    row = record(league,history,fixture)
    if row is None:
        return {'ok':False,'reason':'Takım veya lig geçmişi yetersiz'}
    if row['date'] < PLAN['testBefore']:
        return {'ok':False,'reason':'Model sürümünün kullanım başlangıcından önceki maç'}
    model_probs = {}
    for family, markets in FAMILIES.items():
        fitted = artifact['families'][family]['model']
        if not eligible(row,family,fitted['useMarket']):
            fitted = artifact['families'][family]['fallback']
        dist = probabilities(fitted,[row],family)[0]
        model_probs.update(dict(zip(markets,dist)))
    candidates = []
    for market in engine.MARKETS:
        p, mp, odds = model_probs[market], row['market'].get(market), row['odds'].get(market)
        gate = artifact['gates'].get(league+'|'+market,{'eligible':False,'reason':'Bağımsız test kaydı yok'})
        ev = p*odds-1 if odds and odds>1 else None
        reasons = []
        if not gate['eligible']: reasons.append(gate['reason'])
        if min(row['strengths']['nH'],row['strengths']['nA']) < 8: reasons.append('Takım geçmişi yetersiz')
        if mp is None or ev is None: reasons.append('Karşılaştırılabilir piyasa oranı yok')
        if p < .55: reasons.append('Olasılık aday eşiğinin altında')
        if ev is not None and ev < .05: reasons.append('Referans oranda yeterli beklenen değer yok')
        active = not reasons
        candidates.append({'market':market,'p':p,'marketP':mp,'edge':p-mp if mp is not None else None,
            'tier':'ADAY' if active else 'PAS','score':ev if active else 0,'expectedValue':ev,'referenceOdds':odds,
            'minimumOdds':1.05/p,'reason':'; '.join(reasons) if reasons else 'Bağımsız test ve değer koşulları sağlandı; referans oran güncel olmalı.',
            'evidence':gate})
    active = sorted([c for c in candidates if c['tier']=='ADAY'],key=lambda c:c['score'],reverse=True)
    best = active[0] if active else {'market':None,'tier':'PAS','p':None,'marketP':None,'edge':None,'score':0,
                                    'reason':'Bağımsız test ve veri koşullarını karşılayan aday yok'}
    return {'ok':True,'strengths':row['strengths'],'model':{**model_probs,'scores':row['raw']['scores']},
            'rawModel':row['raw'],'market':row['market'],'decision':{'best':best,'candidates':candidates},
            'context':row['context'],'modelId':artifact['modelId'],'modelVersion':VERSION}


if __name__ == '__main__':
    import csv
    root = Path(__file__).resolve().parents[1]
    histories = {code:[] for code in LEAGUE_CODES}
    for file in (root/'raw').glob('*.csv'):
        parts = file.stem.split('_')
        if len(parts)==2 and parts[0] in ('2425','2526','2627') and parts[1] in histories:
            with file.open(encoding='utf-8-sig',newline='') as handle:
                histories[parts[1]].extend(csv.DictReader(handle))
    model = ensure_model(histories,root/'data/model.json')
    (root/'data/model.json').write_text(json.dumps(model,ensure_ascii=False,indent=2),encoding='utf-8')
    (root/'data/model-quality.json').write_text(json.dumps(model['report'],ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'counts':model['report']['counts'],'families':model['report']['families'],
                      'approvedGates':sum(g['eligible'] for g in model['gates'].values())},ensure_ascii=False,indent=2))

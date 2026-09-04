"""Lock every prematch probability vector, including matches with a PAS decision."""
from copy import deepcopy

import engine
from lifecycle import identity, index_histories, iso, kickoff


def register(records, prediction, now):
    start = kickoff(prediction)
    if not start or start <= now:
        return None
    version = prediction['modelVersion']
    key = identity(prediction['league'], prediction)
    old = next((r for r in records if identity(r['league'],r)==key and r['modelVersion']==version),None)
    if old:
        return old
    fields = ('id','league','leagueName','date','time','home','away','modelVersion','modelId',
              'model','rawModel','market','context','decision','candidates')
    item = {key:deepcopy(prediction[key]) for key in fields}
    item.update(createdAt=iso(now),kickoffAt=iso(start),status='PENDING',hg=None,ag=None,
                outcomes=None,forwardTestEligible=True)
    records.append(item)
    return item


def settle(records, histories, now):
    results,_ = index_histories(histories)
    for item in records:
        start,created = kickoff(item),engine.parse_date(item.get('createdAt'))
        item['forwardTestEligible'] = bool(start and created and created < start)
        key = identity(item['league'],item)
        if item['status']=='PENDING' and key in results and start and start <= now:
            hg,ag = results[key]
            item.update(status='SETTLED',hg=hg,ag=ag,settledAt=iso(now),
                        outcomes={k:engine.outcome(k,hg,ag) for k in engine.MARKETS})


def summary(records, version):
    rows = [r for r in records if r.get('modelVersion')==version and r.get('forwardTestEligible')]
    settled = [r for r in rows if r['status']=='SETTLED']
    result = {'version':version,'total':len(rows),'settled':len(settled),
              'pending':sum(r['status']=='PENDING' for r in rows),'markets':{}}
    for market in engine.MARKETS:
        data = [(r['model'][market],r['outcomes'][market]) for r in settled]
        result['markets'][market] = {'n':len(data),'brier':sum((p-y)**2 for p,y in data)/len(data) if data else None,
            'predicted':sum(p for p,y in data)/len(data) if data else None,
            'observed':sum(y for p,y in data)/len(data) if data else None}
    return result

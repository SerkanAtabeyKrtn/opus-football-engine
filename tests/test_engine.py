import sys, pathlib, math
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'app'))
from engine import *
def synthetic():
    rows=[]
    teams=['A','B','C','D']
    from datetime import datetime,timedelta
    d=datetime(2025,1,1)
    for i in range(80):
        h=teams[i%4];a=teams[(i+1+(i//4)%2)%4]
        if a==h:a=teams[(i+2)%4]
        rows.append({'Date':(d+timedelta(days=i*3)).strftime('%d/%m/%Y'),'HomeTeam':h,'AwayTeam':a,'FTHG':str((i*3)%4),'FTAG':str((i*5)%3),'B365H':'2.2','B365D':'3.2','B365A':'3.4','B365>2.5':'2.0','B365<2.5':'1.8'})
    return rows
h=synthetic();f={'Date':'01/12/2025','HomeTeam':'A','AwayTeam':'B','B365H':'2.2','B365D':'3.2','B365A':'3.4','B365>2.5':'2','B365<2.5':'1.8'}
p=predict(h,f);assert p['ok']; assert .999999 < sum(sum(r) for r in score_matrix(1.2,.9)) < 1.000001
assert abs(p['model']['U25']+p['model']['O25']-1)<1e-9
assert abs(p['model']['BTTS_NO']+p['model']['BTTS_YES']-1)<1e-9
assert abs(p['model']['HOME']+p['model']['DRAW']+p['model']['AWAY']-1)<1e-9
q=devig([2,3,4]);assert abs(sum(q)-1)<1e-12
# leakage: future extreme result must not change prediction at same as_of
p1=predict(h,f); h2=h+[{'Date':'02/12/2025','HomeTeam':'A','AwayTeam':'B','FTHG':'20','FTAG':'0'}];p2=predict(h2,f);assert abs(p1['strengths']['lambdaH']-p2['strengths']['lambdaH'])<1e-12
# decision tiers non-overlap
d=choose_decision({'U25':.66,'O25':.34,'BTTS_NO':.5,'BTTS_YES':.5,'HOME':.5,'DRAW':.2,'AWAY':.3},{'U25':.58},.9);assert d['best']['tier']=='DENGELİ'
print('ALL ENGINE TESTS PASSED')

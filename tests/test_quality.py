import copy
import math
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
import calibration
import quality_model as quality
import forecast_audit
from lifecycle import register_prediction


def training_rows():
    rows=[]
    for period,date in enumerate(('2025-10-01','2026-02-01','2026-05-01')):
        for i in range(320):
            p=.25+(i%11)/25
            rows.append({'league':'E0','date':date,'home':str(i),'away':'B',
                'raw':{'HOME':p,'DRAW':.25,'AWAY':.75-p,'O25':p,'U25':1-p,'BTTS_YES':p,'BTTS_NO':1-p},
                'market':{'HOME':.4,'DRAW':.3,'AWAY':.3,'O25':.5,'U25':.5},
                'contextValues':[1,1,0,0,1,1,0,0],'strengths':{'nH':10,'nA':10},
                'odds':{'HOME':2.2,'DRAW':3.1,'AWAY':3.1,'O25':1.9,'U25':1.9},
                'labels':{'result':i%3,'goals':i%2,'btts':(i//3)%2}})
    return rows


class QualityTests(unittest.TestCase):
    def test_new_season_results_cannot_silently_retune_a_frozen_model(self):
        past={'E0':[dict(Date='01/05/2026',HomeTeam='A',AwayTeam='B',FTHG=1,FTAG=0)]}
        first=quality.fingerprint(past)
        current=copy.deepcopy(past)
        current['E0'].append(dict(Date='01/09/2026',HomeTeam='A',AwayTeam='B',FTHG=5,FTAG=0))
        self.assertEqual(first,quality.fingerprint(current))
        current['E0'][0]['FTHG']=2
        self.assertNotEqual(first,quality.fingerprint(current))

    def test_logistic_solver_improves_overconfident_probabilities_and_normalizes(self):
        x=[[quality.logit(.9 if i%2 else .1)] for i in range(400)]
        y=[int((i%2 and i%10!=1) or (not i%2 and i%10==0)) for i in range(400)]
        fit=calibration.fit(x,y,2,30)
        predictions=calibration.predict(fit,x)
        self.assertTrue(all(abs(sum(p)-1)<1e-12 and all(0<pv<1 for pv in p) for p in predictions))
        old=[[.1,.9] if i%2 else [.9,.1] for i in range(400)]
        self.assertLess(calibration.metrics(predictions,y)['logLoss'],calibration.metrics(old,y)['logLoss'])

    def test_changing_holdout_labels_cannot_change_fitted_parameters(self):
        rows=training_rows()
        for i,r in enumerate(rows):
            r['context']={'availability':{'xg':True},
                'home':{'xg':{'matches':8,'for':1+(i%7)/7,'against':.9}},
                'away':{'xg':{'matches':8,'for':.8,'against':1+(i%5)/5}}}
        with patch.object(quality,'replay',return_value=rows):
            first=quality.build({})
        changed=copy.deepcopy(rows)
        for r in changed:
            if r['date']>='2026-04-01':
                r['labels']={k:(v+1)%len(quality.FAMILIES[k]) for k,v in r['labels'].items()}
        with patch.object(quality,'replay',return_value=changed):
            second=quality.build({})
        self.assertEqual(first['families'],second['families'])
        self.assertEqual(first['families']['result']['model']['trainingCount'],640)

    def test_context_ignores_current_and_future_match_results_and_shots(self):
        history=[dict(Date='01/09/2026',HomeTeam='A',AwayTeam='B',FTHG=1,FTAG=0,HST=4,AST=2)]
        fixture=dict(Date='05/09/2026',HomeTeam='A',AwayTeam='B')
        original=quality.context(history,fixture)
        malicious=[dict(fixture,FTHG=20,FTAG=0,HST=200,AST=0),
                   dict(Date='06/09/2026',HomeTeam='A',AwayTeam='B',FTHG=30,FTAG=0,HST=200,AST=0)]
        self.assertEqual(original,quality.context(history+malicious,fixture))
        self.assertEqual(original[1]['home']['restDays'],4)
        self.assertFalse(original[1]['availability']['xg'])

    def test_unknown_odds_never_generate_an_active_candidate(self):
        row=training_rows()[0]
        row.update(date='2026-09-05',context={},market={},raw={**row['raw'],'scores':[]})
        artifact={'modelId':'test','families':{k:{'model':{'useMarket':False},'fallback':{'useMarket':False}} for k in quality.FAMILIES},
                  'gates':{'E0|'+k:{'eligible':True,'reason':'test'} for k in quality.engine.MARKETS}}
        row['odds']={}
        with patch.object(quality,'record',return_value=row), patch.object(quality,'probabilities',side_effect=lambda m,r,f:[[.8,.1,.1]] if f=='result' else [[.8,.2]]):
            p=quality.predict(artifact,'E0',[],{})
        self.assertEqual(p['decision']['best']['tier'],'PAS')
        self.assertEqual(len(p['decision']['candidates']),7)

    def test_no_evidence_cannot_be_overridden_by_a_high_probability(self):
        row=training_rows()[0]
        row.update(date='2026-09-05',context={},raw={**row['raw'],'scores':[]})
        artifact={'modelId':'test','families':{k:{'model':{'useMarket':False},'fallback':{'useMarket':False}} for k in quality.FAMILIES},'gates':{}}
        with patch.object(quality,'record',return_value=row), patch.object(quality,'probabilities',side_effect=lambda m,r,f:[[.95,.03,.02]] if f=='result' else [[.95,.05]]):
            p=quality.predict(artifact,'E0',[],{})
        self.assertEqual(p['decision']['best']['tier'],'PAS')

    def test_price_with_negative_value_is_rejected_despite_probability_edge(self):
        row=training_rows()[0]
        row.update(date='2026-09-05',context={},raw={**row['raw'],'scores':[]})
        row['market'].update(HOME=.6,DRAW=.2,AWAY=.2)
        row['odds'].update(HOME=1.5,DRAW=1.5,AWAY=1.5,O25=1.5,U25=1.5)
        artifact={'modelId':'test','families':{k:{'model':{'useMarket':False},'fallback':{'useMarket':False}} for k in quality.FAMILIES},
                  'gates':{'E0|'+k:{'eligible':True,'reason':'test'} for k in quality.engine.MARKETS}}
        with patch.object(quality,'record',return_value=row), patch.object(quality,'probabilities',side_effect=lambda m,r,f:[[.65,.2,.15]] if f=='result' else [[.5,.5]]):
            p=quality.predict(artifact,'E0',[],{})
        self.assertEqual(p['decision']['best']['tier'],'PAS')
        home=next(c for c in p['decision']['candidates'] if c['market']=='HOME')
        self.assertGreater(home['edge'],0)
        self.assertLess(home['expectedValue'],0)

    def test_candidate_requires_evidence_sample_and_positive_price_value(self):
        row=training_rows()[0]
        row.update(date='2026-09-05',context={},raw={**row['raw'],'scores':[]})
        artifact={'modelId':'test','families':{k:{'model':{'useMarket':False},'fallback':{'useMarket':False}} for k in quality.FAMILIES},
                  'gates':{'E0|HOME':{'eligible':True,'reason':'test'}}}
        with patch.object(quality,'record',return_value=row), patch.object(quality,'probabilities',side_effect=lambda m,r,f:[[.65,.2,.15]] if f=='result' else [[.5,.5]]):
            p=quality.predict(artifact,'E0',[],{})
        self.assertEqual(p['decision']['best']['tier'],'ADAY')
        self.assertEqual(p['decision']['best']['market'],'HOME')
        self.assertAlmostEqual(p['decision']['best']['expectedValue'],.65*2.2-1)
        self.assertAlmostEqual(p['decision']['best']['minimumOdds'],1.05/.65)

    def test_probability_audit_records_pas_and_never_rewrites_first_analysis(self):
        now=datetime(2026,9,4,10,tzinfo=timezone.utc)
        item=dict(id='a',league='E0',leagueName='Premier League',date='05/09/2026',time='15:00',home='A',away='B',
                  modelVersion='1.5',modelId='frozen',model={k:.5 for k in quality.engine.MARKETS},rawModel={},market={},context={},
                  decision={'tier':'PAS'},candidates=[])
        records=[]
        first=forecast_audit.register(records,item,now)
        item['model']['O25']=.9
        again=forecast_audit.register(records,item,now)
        self.assertIs(first,again)
        self.assertEqual(first['model']['O25'],.5)
        histories={'E0':[dict(Date='05/09/2026',HomeTeam='A',AwayTeam='B',FTHG=2,FTAG=1)]}
        forecast_audit.settle(records,histories,datetime(2026,9,6,tzinfo=timezone.utc))
        self.assertEqual(first['status'],'SETTLED')
        self.assertEqual(first['outcomes']['O25'],1)
        self.assertEqual(forecast_audit.summary(records,'1.5')['settled'],1)
        self.assertIsNone(forecast_audit.register([],item,datetime(2026,9,6,tzinfo=timezone.utc)))

    def test_legacy_locked_decision_survives_upgrade(self):
        now=datetime(2026,9,4,10,tzinfo=timezone.utc)
        item=dict(id='a',league='E0',leagueName='Premier League',date='05/09/2026',time='15:00',home='A',away='B',
                  decision={'market':'HOME','tier':'GÜVENLİ','p':.8,'marketP':.7,'edge':.1})
        records=[]
        first=register_prediction(records,item,now)
        saved=copy.deepcopy(first)
        item.update(modelVersion='1.5',modelId='new')
        item['decision'].update(p=.6,tier='ADAY')
        self.assertIs(register_prediction(records,item,now),first)
        self.assertEqual(first,saved)


if __name__=='__main__':
    unittest.main()

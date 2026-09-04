import copy
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
from lifecycle import audit_and_settle, eligibility, kickoff, register_prediction, identity
from engine import market_probabilities, choose_decision
import update

NOW = datetime(2026, 9, 4, 12, tzinfo=timezone.utc)


def fixture(day='04/09/2026', clock='15:00'):
    return dict(Div='E1', Date=day, Time=clock, HomeTeam='A', AwayTeam='B')


def prediction(day='04/09/2026', clock='15:00'):
    return dict(id='new', league='E1', leagueName='Championship', date=day,
                time=clock, home='A', away='B',
                decision=dict(tier='DENGELİ',market='U25',p=.7,marketP=.6,edge=.1))


class LifecycleTests(unittest.TestCase):
    def test_corrupt_ledger_cannot_silently_reset_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'ledger.json'
            path.write_text('{broken',encoding='utf-8')
            with self.assertRaises(ValueError):
                update.load_ledger(path)
            self.assertEqual(path.read_text(),'{broken')

    def test_kickoff_includes_uk_daylight_saving(self):
        self.assertEqual(kickoff(fixture()).hour,14)
        self.assertEqual(kickoff(fixture('04/01/2026')).hour,15)
        self.assertIsNone(kickoff(fixture(clock='')))
        self.assertIsNone(kickoff(fixture(clock='TBD')))
        self.assertIsNone(kickoff(fixture('25/10/2026','01:30')))

    def test_started_and_finished_fixtures_are_rejected(self):
        f=fixture(clock='13:00')
        self.assertIsNotNone(eligibility('E1', f, {}, NOW))
        self.assertIsNone(eligibility('E1', fixture(), {}, NOW))
        self.assertIsNotNone(eligibility('E1', fixture(), {identity('E1',fixture()):(1,0)}, NOW))
        self.assertIsNotNone(eligibility('E1',fixture(clock=''),{},NOW))

    def test_registration_checks_time_and_preserves_first_prediction(self):
        records=[]
        first=register_prediction(records,prediction(),NOW)
        protected={k:first[k] for k in ('market','p','tier','edge','createdAt','kickoffAt')}
        changed=prediction();changed['decision'].update(market='HOME',p=.8)
        self.assertIs(register_prediction(records,changed,NOW),first)
        self.assertEqual({k:first[k] for k in protected},protected)
        self.assertEqual(len(records),1)
        self.assertIsNone(register_prediction([],prediction('03/09/2026'),NOW))

    def test_audit_excludes_late_records_without_losing_results(self):
        rec=register_prediction([],prediction(),NOW)
        rec['createdAt']='2026-09-05T12:00:00Z'
        history={'E1':[dict(fixture(),FTHG='1',FTAG='0')]}
        audit_and_settle([rec],history,datetime(2026,9,6,tzinfo=timezone.utc))
        self.assertFalse(rec['forwardTestEligible'])
        self.assertEqual(rec['status'],'SETTLED')
        self.assertTrue(rec['won'])
        self.assertEqual(rec['p'],.7)

    def test_valid_prediction_settles_even_without_fixture_feed(self):
        rec=register_prediction([],prediction(),NOW)
        history={'E1':[dict(fixture(),Date='2026-09-04',FTHG='0',FTAG='0')]}
        later=datetime(2026,9,5,tzinfo=timezone.utc)
        audit_and_settle([rec],history,later,[])
        self.assertTrue(rec['forwardTestEligible'])
        self.assertEqual(rec['status'],'SETTLED')
        settled=copy.deepcopy(rec)
        audit_and_settle([rec],history,later,[])
        self.assertEqual(rec,settled)

    def test_missing_result_has_explicit_awaiting_status(self):
        rec=register_prediction([],prediction(),NOW)
        later=datetime(2026,9,5,12,tzinfo=timezone.utc)
        audit_and_settle([rec],{},later)
        self.assertEqual(rec['status'],'PENDING')
        self.assertEqual(rec['displayStatus'],'AWAITING_RESULT')

    def test_result_cannot_settle_before_known_kickoff(self):
        rec=register_prediction([],prediction(),NOW)
        history={'E1':[dict(fixture(),FTHG='0',FTAG='0')]}
        audit_and_settle([rec],history,NOW)
        self.assertEqual(rec['status'],'PENDING')

    def test_unverifiable_legacy_timing_is_excluded(self):
        rec=dict(prediction(),createdAt='2026-09-04T10:00:00Z',status='PENDING')
        rec.pop('time')
        audit_and_settle([rec],{},NOW)
        self.assertFalse(rec['forwardTestEligible'])

    def test_all_seven_markets_are_compared_and_btts_odds_are_optional(self):
        model=dict(U25=.4,O25=.6,BTTS_NO=.3,BTTS_YES=.7,HOME=.8,DRAW=.1,AWAY=.1)
        markets=market_probabilities(dict(oddsH=2,oddsD=4,oddsA=4,oddsBTTSYes=2,oddsBTTSNo=2))
        decision=choose_decision(model,markets,.9)
        self.assertEqual(len(decision['candidates']),7)
        self.assertEqual(decision['best']['market'],'HOME')
        btts=next(c for c in decision['candidates'] if c['market']=='BTTS_YES')
        self.assertEqual(btts['tier'],'DENGELİ')
        missing=choose_decision(model,{},.9)
        btts=next(c for c in missing['candidates'] if c['market']=='BTTS_YES')
        self.assertEqual(btts['tier'],'PAS')
        self.assertIn('Piyasa oranı yok',btts['reason'])

    def test_invalid_results_download_keeps_good_cache(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(update,'RAW',Path(tmp)):
            path=Path(tmp)/'sample.csv'
            original=b'Date,HomeTeam,AwayTeam,FTHG,FTAG\n01/09/2026,A,B,1,0\n'
            path.write_bytes(original)
            with patch.object(update,'get',return_value=b'<html>maintenance</html>'):
                rows,stale=update.fetch_cached('https://example.test','sample',[])
            self.assertTrue(stale)
            self.assertEqual(path.read_bytes(),original)
            self.assertEqual(rows[0]['FTHG'],'1')

    def test_update_does_not_predict_past_fixtures_and_audits_existing_ledger(self):
        past=fixture('01/09/2026')
        old=dict(id='old',league='E1',leagueName='Championship',date='01/09/2026',
                 home='A',away='B',createdAt='2026-09-03T10:00:00Z',market='U25',
                 tier='DENGELİ',p=.7,marketP=.6,edge=.1,status='PENDING')
        with tempfile.TemporaryDirectory() as tmp, patch.object(update,'DATA',Path(tmp)), \
             patch.object(update,'LEAGUES',{'E1':'Championship'}), \
             patch.object(update,'SEASONS',['2627']), \
             patch.object(update,'fetch_cached',return_value=([dict(past,FTHG='1',FTAG='0')],False)), \
             patch.object(update,'fetch_fixtures',return_value=([past],False,'test',[])), \
             patch.object(update,'ensure_model',return_value={'report':{}}), \
             patch.object(update,'predict') as predictor:
            Path(tmp,'ledger.json').write_text(json.dumps({'predictions':[old]}),encoding='utf-8')
            update.main()
            predictor.assert_not_called()
            data=json.loads(Path(tmp,'dashboard.json').read_text(encoding='utf-8'))
        self.assertEqual(data['predictions'],[])
        self.assertEqual(data['ledger'][0]['status'],'SETTLED')
        self.assertEqual(data['ledger'][0]['p'],.7)
        self.assertEqual(data['liveSummary']['E1']['n'],0)
        self.assertEqual(data['health']['excludedFromForwardTest'],1)


if __name__=='__main__':
    unittest.main()

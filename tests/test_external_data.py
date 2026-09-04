import copy
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
import external_data as ext
import quality_model as quality

NOW=datetime(2026,9,4,12,tzinfo=timezone.utc)

class ExternalDataTests(unittest.TestCase):
    def test_xg_only_completed_matches_and_exact_result_identity(self):
        r={'id':'1','datetime':'2026-09-01 19:00:00','isResult':True,
           'h':{'title':'Manchester City'},'a':{'title':'Arsenal'},'goals':{'h':'2','a':'1'},'xG':{'h':'1.8','a':'0.9'}}
        bad=copy.deepcopy(r);bad['isResult']=False
        invalid=copy.deepcopy(r);invalid['xG']['h']='NaN'
        source=ext.normalize_xg({'dates':[r,bad,invalid]})
        self.assertEqual(len(source),1)
        history={'E0':[{'Date':'01/09/2026','HomeTeam':'Man City','AwayTeam':'Arsenal','FTHG':2,'FTAG':1},
                       {'Date':'01/09/2026','HomeTeam':'Arsenal','AwayTeam':'Man City','FTHG':2,'FTAG':1},
                       {'Date':'01/09/2026','HomeTeam':'Man City','AwayTeam':'Arsenal','FTHG':4,'FTAG':0}]}
        self.assertEqual(ext.attach_xg(history,{'E0':source})['E0'],1)
        self.assertEqual(history['E0'][0]['UnderstatHxG'],1.8)
        self.assertNotIn('UnderstatHxG',history['E0'][1]);self.assertNotIn('UnderstatHxG',history['E0'][2])

    def test_duplicate_xg_identity_is_not_guessed(self):
        x={'date':'2026-09-01','home':'A','away':'B','hg':1,'ag':0,'xgHome':1,'xgAway':0}
        history={'E0':[dict(Date='01/09/2026',HomeTeam='A',AwayTeam='B',FTHG=1,FTAG=0)]}
        self.assertEqual(ext.attach_xg(history,{'E0':[x,x]})['E0'],0)

    def test_future_and_current_xg_never_enter_features(self):
        history=[dict(Date=f'{i:02}/08/2026',HomeTeam='A',AwayTeam='B',FTHG=1,FTAG=0,UnderstatHxG=1.3,UnderstatAxG=.6) for i in (1,8,15,22)]
        fixture=dict(Date='05/09/2026',HomeTeam='A',AwayTeam='B')
        before=quality.context(history,fixture)
        after=quality.context(history+[dict(fixture,FTHG=8,FTAG=1,UnderstatHxG=9,UnderstatAxG=7),
              dict(Date='06/09/2026',HomeTeam='A',AwayTeam='B',FTHG=5,FTAG=0,UnderstatHxG=10,UnderstatAxG=6)],fixture)
        self.assertEqual(before,after)
        self.assertTrue(before[1]['availability']['xg'])
        self.assertAlmostEqual(before[1]['home']['xg']['for'],1.3)

    def test_unknown_xg_columns_are_not_labelled_understat(self):
        rows=[dict(Date=f'{i:02}/08/2026',HomeTeam='A',AwayTeam='B',FTHG=1,FTAG=0,HxG=2.0,AxG=1.0) for i in (1,8,15,22)]
        result=quality.context(rows,dict(Date='05/09/2026',HomeTeam='A',AwayTeam='B'))
        self.assertFalse(result[1]['availability']['xg'])
        self.assertEqual(result[1]['home']['xg']['matches'],0)

    def test_cache_failure_retains_data_but_is_never_fresh(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'sample.json';old={'source':'sample','url':'https://example.org','fetchedAt':ext.iso(NOW-timedelta(hours=2)),'data':{'value':1}}
            p.write_text(json.dumps(old))
            c=ext.Client(tmp,NOW)
            with patch.object(ext.urllib.request,'urlopen',side_effect=OSError('offline')):
                r=c.get('sample','https://example.org',1800,lambda x:x)
            self.assertEqual(r['data'],old['data']);self.assertEqual(r['status'],'stale');self.assertFalse(ext.usable(r))
            self.assertEqual(json.loads(p.read_text()),old)

    def test_fresh_cache_avoids_repeated_requests_and_future_timestamp_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'sample.json';old={'source':'sample','url':'https://example.org','fetchedAt':ext.iso(NOW-timedelta(minutes=10)),'data':{}}
            p.write_text(json.dumps(old))
            with patch.object(ext.urllib.request,'urlopen',side_effect=OSError('offline')) as request:
                self.assertEqual(ext.Client(tmp,NOW).get('sample','https://example.org',1800,lambda x:x)['status'],'cached')
                request.assert_not_called()
                old['fetchedAt']=ext.iso(NOW+timedelta(minutes=1));p.write_text(json.dumps(old))
                self.assertEqual(ext.Client(tmp,NOW).get('sample','https://example.org',1800,lambda x:x)['status'],'stale')

    def test_unsupported_injuries_are_not_an_all_clear(self):
        f=dict(Date='05/09/2026',Time='15:00',HomeTeam='A',AwayTeam='B')
        result=ext.context_for_fixture('SP2',f,{'status':'fresh','data':{}},[],{},{},NOW)
        self.assertEqual(result['home']['availability']['status'],'unsupported')
        self.assertEqual(result['home']['lineup']['status'],'not_published')

    def test_confirmed_lineups_require_eleven_starters_and_matching_fixture(self):
        roster=[{'starter':True,'athlete':{'id':str(i),'displayName':str(i)}} for i in range(11)]
        data=ext.normalize_lineups({'rosters':[{'team':{'id':'h'},'roster':roster},{'team':{'id':'a'},'roster':roster[:10]}]})
        self.assertIn('h',data);self.assertNotIn('a',data)
        f=dict(Date='04/09/2026',Time='14:00',HomeTeam='A',AwayTeam='B')
        e={'id':'m','date':ext.iso(ext.kickoff(f)),'status':'pre','home':{'id':'h','name':'A'},'away':{'id':'a','name':'B'}}
        lines={'m':{'status':'fresh','fetchedAt':ext.iso(NOW),'data':data}}
        found=ext.context_for_fixture('E0',f,{},[e],{},lines,NOW)
        self.assertEqual(found['home']['lineup']['status'],'confirmed')
        e['away']['name']='C'
        self.assertEqual(ext.context_for_fixture('E0',f,{},[e],{},lines,NOW)['home']['lineup']['status'],'not_published')

    def test_first_context_is_immutable_and_updates_stop_at_kickoff(self):
        f=dict(Date='04/09/2026',Time='14:00',HomeTeam='A',AwayTeam='B');rows=[]
        ext.register_context(rows,'E0',f,{'value':1},NOW)
        ext.register_context(rows,'E0',f,{'value':2},NOW+timedelta(minutes=10))
        self.assertEqual(rows[0]['first'],{'value':1});self.assertEqual(rows[0]['latest'],{'value':2})
        before=copy.deepcopy(rows)
        ext.register_context(rows,'E0',f,{'value':3},ext.kickoff(f))
        self.assertEqual(rows,before)

    def test_limited_requests_check_all_leagues_then_lineups_then_nearest_squads(self):
        fixtures=[dict(Div='B1',Date='04/09/2026',Time='16:00',HomeTeam='C',AwayTeam='D'),
                  dict(Div='E0',Date='04/09/2026',Time='14:00',HomeTeam='Tottenham',AwayTeam='Arsenal')]
        events={}
        for f in fixtures:
            code=f['Div'];events[code]=[{'id':code,'date':ext.iso(ext.kickoff(f)),'status':'pre',
              'home':{'id':code+'h','name':f['HomeTeam']},'away':{'id':code+'a','name':f['AwayTeam']}}]
        other=copy.deepcopy(events['E0'][0]);other.update(id='unmatched',date='2026-09-06T13:00:00Z')
        other['home']['id']='wrong';events['E0'].append(other)
        calls=[]
        class FakeClient:
            now=NOW
            def get(self,key,url,ttl,normalize,**kwargs):
                calls.append(key)
                return {'status':'fresh','fetchedAt':ext.iso(NOW),'data':events.get(key.removeprefix('events_'),{})}
        ext.collect_context(FakeClient(),fixtures)
        self.assertEqual(calls[:4],['fpl','events_B1','events_E0','lineup_E0'])
        self.assertEqual(calls[4:],['roster_E0_E0h','roster_E0_E0a','roster_B1_B1h','roster_B1_B1a'])
        self.assertEqual(ext.canonical('Spurs'),ext.canonical('Tottenham Hotspur'))
        for a,b in [('Buyuksehyr','Istanbul Basaksehir'),('Goztep','Goztepe'),('Sociedad B','Real Sociedad II')]:
            self.assertEqual(ext.event_name(a),ext.event_name(b))
        self.assertNotEqual(ext.event_name('Real Sociedad II'),ext.event_name('Real Sociedad'))

if __name__=='__main__':unittest.main()

import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'app'))
from update import fixture_payload_is_valid, parse_csv_bytes, REQUIRED_FIXTURE_FIELDS


def test_valid_fixture_payload():
    b=(
        'Div,Date,Time,HomeTeam,AwayTeam,B365H,B365D,B365A,B365>2.5,B365<2.5\n'
        'I2,31/08/2026,19:30,Palermo,Modena,1.90,3.20,4.10,2.05,1.75\n'
        'SP2,31/08/2026,20:00,Burgos,Castellon,2.20,3.00,3.40,2.10,1.70\n'
    ).encode()
    ok,headers=fixture_payload_is_valid(b)
    assert ok
    assert REQUIRED_FIXTURE_FIELDS.issubset(set(headers))
    rows=parse_csv_bytes(b)
    assert len(rows)==2 and rows[0]['Div']=='I2'


def test_html_or_wrong_schema_rejected():
    b=b'<html><body>Latest fixtures page</body></html>'
    ok,headers=fixture_payload_is_valid(b)
    assert not ok


def test_unknown_league_only_rejected():
    b=('Div,Date,HomeTeam,AwayTeam\nZZ,31/08/2026,A,B\n').encode()
    ok,_=fixture_payload_is_valid(b)
    assert not ok

if __name__=='__main__':
    test_valid_fixture_payload(); test_html_or_wrong_schema_rejected(); test_unknown_league_only_rejected(); print('test_update.py PASS')

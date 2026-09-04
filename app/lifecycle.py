"""Fixture eligibility and auditable, immutable forward-test records."""
import hashlib
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from engine import normalize_match, parse_date, outcome

# Football-Data fixture clock is treated as UK local time (including DST).
# A fixture without a clock is not eligible for a timed forward prediction.
SOURCE_TZ = ZoneInfo('Europe/London')


def iso(value):
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def kickoff(row):
    explicit = row.get('kickoffAt')
    if explicit:
        try:
            value = datetime.fromisoformat(explicit.replace('Z', '+00:00'))
            return value.astimezone(timezone.utc) if value.tzinfo else None
        except (TypeError, ValueError):
            return None
    m = normalize_match(row)
    date = parse_date(m['date'])
    if not date or not m['time']:
        return None
    try:
        clock = datetime.strptime(m['time'].strip(), '%H:%M').time()
    except ValueError:
        return None
    local = datetime.combine(date.date(), clock, SOURCE_TZ)
    # Do not guess a time inside a DST transition's missing or repeated hour.
    if local.utcoffset() != local.replace(fold=1).utcoffset():
        return None
    return local.astimezone(timezone.utc)


def identity(league, row):
    m = normalize_match(row)
    date = parse_date(m['date'])
    day = date.date().isoformat() if date else str(m['date'])
    return '|'.join([league, day, str(m['home'] or '').strip().casefold(), str(m['away'] or '').strip().casefold()])


def index_histories(histories):
    results, times = {}, {}
    for league, rows in histories.items():
        for row in rows:
            m = normalize_match(row)
            key = identity(league, m)
            if kickoff(m):
                times[key] = kickoff(m)
            if all(v is not None and v >= 0 and v == int(v) for v in (m['hg'], m['ag'])):
                results[key] = (int(m['hg']), int(m['ag']))
    return results, times


def eligibility(league, fixture, results, now):
    m = normalize_match(fixture)
    if identity(league, m) in results or (m['hg'] is not None and m['ag'] is not None):
        return 'Sonucu mevcut; yeni tahmin üretilmez'
    start = kickoff(fixture)
    if not start:
        return 'Başlama tarihi veya saati doğrulanamıyor'
    if start <= now:
        return 'Başlama saati geçti; sonuç kaynağı bekleniyor'
    return None


def audit_and_settle(records, histories, now, fixtures=()):
    results, times = index_histories(histories)
    for row in fixtures:
        start = kickoff(row)
        if start:
            times.setdefault(identity(row.get('Div') or row.get('league') or '', row), start)
    for rec in records:
        key = identity(rec['league'], rec)
        # Preserve the kickoff stored when the prediction was created.
        start = kickoff(rec) or times.get(key)
        created = parse_date(rec.get('createdAt'))
        day = parse_date(rec.get('date'))
        if start and created:
            valid = created < start
            reason = 'Maç öncesi kaydedildi' if valid else 'Maç başladıktan sonra oluşturuldu'
        elif created and day and created.astimezone(SOURCE_TZ).date() > day.date():
            valid, reason = False, 'Maç tarihinden sonra oluşturuldu'
        else:
            valid, reason = False, 'Maç öncesi kayıt zamanı doğrulanamıyor'
        rec['forwardTestEligible'] = valid
        rec['auditReason'] = reason
        rec['auditedKickoffAt'] = iso(start) if start else None
        if rec.get('status') == 'PENDING' and key in results and (not start or start <= now):
            hg, ag = results[key]
            rec.update(hg=hg, ag=ag, won=bool(outcome(rec['market'], hg, ag)), status='SETTLED', settledAt=iso(now))
        if rec.get('status') == 'SETTLED':
            rec['displayStatus'] = 'SETTLED'
        elif not valid:
            rec['displayStatus'] = 'UNVERIFIED'
        elif start and start <= now:
            rec['displayStatus'] = 'AWAITING_RESULT'
        else:
            rec['displayStatus'] = 'SCHEDULED'
    return results


def register_prediction(records, prediction, now):
    key = identity(prediction['league'], prediction)
    found = next((r for r in records if identity(r['league'], r) == key), None)
    if found:
        return found
    start = kickoff(prediction)
    d = prediction['decision']
    if not start or start <= now or d['tier'] == 'PAS':
        return None
    record = {k: prediction[k] for k in ('league', 'leagueName', 'date', 'time', 'home', 'away')}
    record.update(id=prediction['id'], createdAt=iso(now), kickoffAt=iso(start),
                  market=d['market'], tier=d['tier'], p=d['p'], marketP=d['marketP'],
                  edge=d['edge'], status='PENDING', hg=None, ag=None, won=None,
                  modelVersion=prediction.get('modelVersion','1.3'), forwardTestEligible=True, auditReason='Maç öncesi kaydedildi',
                  displayStatus='SCHEDULED')
    if prediction.get('modelId'):
        record.update(modelId=prediction['modelId'],referenceOdds=d.get('referenceOdds'),
                      expectedValue=d.get('expectedValue'),minimumOdds=d.get('minimumOdds'))
    records.append(record)
    return record


def record_id(league, fixture):
    return hashlib.sha1(identity(league, fixture).encode()).hexdigest()[:16]

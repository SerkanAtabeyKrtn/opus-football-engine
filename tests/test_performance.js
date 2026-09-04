const assert=require('node:assert/strict');
const P=require('../performance.js');
const NOW=Date.parse('2026-09-04T12:00:00Z');
function record(id,extra={}){
  return {id,league:'E1',leagueName:'Championship',date:'02/09/2026',home:'A'+id,away:'B'+id,
    market:'O25',tier:'DENGELİ',p:.7,status:'SETTLED',won:true,hg:2,ag:1,
    forwardTestEligible:true,createdAt:'2026-09-01T10:00:00Z',auditedKickoffAt:'2026-09-02T18:45:00Z',...extra};
}
let passed=0;
function test(name,fn){fn();passed++;console.log('PASS '+name)}
test('Only audited, prematch, settled predictions enter performance',()=>{
  const rows=[record('a'),record('b',{forwardTestEligible:false}),record('c',{status:'PENDING',won:null}),
    record('d',{won:'true'}),record('e',{tier:'PAS'}),record('f',{createdAt:'2026-09-03T10:00:00Z'}),
    record('g',{auditedKickoffAt:'2026-09-05T18:45:00Z'}),record('h',{auditedKickoffAt:null})];
  const before=JSON.stringify(rows),result=P.collect(rows,NOW);
  assert.equal(result.records.length,1);assert.equal(result.pending,1);assert.equal(result.excluded,6);
  assert.equal(JSON.stringify(rows),before);
});
test('Duplicate fixture formats count once, preserving the first locked record',()=>{
  const original=record('a'),duplicate=record('changed-id',{date:'2026-09-02',home:'Aa',away:'Ba',createdAt:'2026-09-01T12:00:00Z',won:false});
  const result=P.collect([duplicate,original],NOW);
  assert.equal(result.records.length,1);assert.equal(result.duplicates,1);assert.equal(result.records[0].won,true);
});
test('Each fixture counts once per league and once for each participating team',()=>{
  const rows=P.collect([record('a',{home:'A',away:'B'}),record('b',{home:'B',away:'C',won:false}),record('c',{home:'A',away:'D',league:'F1'})],NOW).records;
  const leagues=P.group(rows),teams=P.group(rows,'team');
  assert.equal(leagues.find(g=>g.id==='E1').n,2);
  const b=teams.find(g=>g.id===P.teamId('E1','B'));
  assert.equal(b.n,2);assert.equal(b.wins,1);assert.equal(b.hitRate,.5);
  assert.equal(teams.filter(g=>g.name==='A').length,2);
  assert.equal(P.summary(rows).n,3);
});
test('Tier, market, period, league and team filters combine correctly',()=>{
  const rows=P.collect([record('a',{home:'A',away:'B'}),record('b',{tier:'AGRESİF'}),record('c',{market:'U25'}),
    record('d',{createdAt:'2026-07-01T10:00:00Z',auditedKickoffAt:'2026-07-02T18:45:00Z'})],NOW).records;
  const filtered=P.filter(rows,{days:30,tier:'DENGELİ',market:'O25',league:'E1',team:P.teamId('E1','A')},NOW);
  assert.equal(filtered.length,1);assert.equal(filtered[0].id,'a');
  assert.equal(P.filter(rows,{days:30},NOW).length,3);
  assert.equal(P.filter(rows,{market:'BTTS_YES'},NOW).length,0);
});
test('Small perfect sample does not outrank sustained performance by default',()=>{
  const single={id:'one',name:'One',n:1,wins:1,hitRate:1,lowerBound:P.wilsonLower(1,1)};
  const sustained={id:'many',name:'Many',n:20,wins:18,hitRate:.9,lowerBound:P.wilsonLower(18,20)};
  assert.equal(P.rank([single,sustained])[0].id,'many');
  assert.equal(P.rank([single,sustained],{sort:'rate'})[0].id,'one');
  assert.equal(P.rank([single,sustained],{min:5}).length,1);
  assert.ok(Math.abs(P.wilsonLower(1,1)-.20654931437723745)<1e-10);
});
test('Top five limit and ties are deterministic',()=>{
  const groups=Array.from({length:8},(_,i)=>({id:String(i),name:'League '+i,n:10+i,hitRate:.5,lowerBound:.1}));
  assert.equal(P.rank(groups).length,5);
  assert.equal(P.rank(groups)[0].id,'7');
  assert.deepEqual(P.rank(groups,{min:100}),[]);
});
test('Empty and losing samples never imply a successful prediction',()=>{
  const empty=P.summary([]);assert.equal(empty.hitRate,null);assert.equal(empty.n,0);
  const losers=P.collect([record('x',{won:false}),record('y',{won:false})],NOW).records;
  const total=P.summary(losers);assert.equal(total.hitRate,0);assert.equal(total.losses,2);
  assert.equal(P.wilsonLower(0,2),0);
});
console.log(`${passed} performance tests passed`);

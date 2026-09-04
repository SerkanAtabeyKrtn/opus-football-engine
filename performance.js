/* Pure calculations shared by the page and regression tests. */
const OpusPerformance=(()=>{
  const markets=['U25','O25','BTTS_NO','BTTS_YES','HOME','DRAW','AWAY'];
  const tiers=['GÜVENLİ','DENGELİ','AGRESİF'];
  const teamId=(league,team)=>JSON.stringify([league,team.trim().toLocaleLowerCase('en')]);
  const time=value=>typeof value==='string'?Date.parse(value):NaN;
  function matchKey(r){
    const parts=String(r.date||'').match(/^(\d{2})\/(\d{2})\/(\d{2}|\d{4})$/);
    const day=parts?`${parts[3].length===2?'20':''}${parts[3]}-${parts[2]}-${parts[1]}`:String(r.date||'').slice(0,10);
    return JSON.stringify([r.league,day,r.home.trim().toLocaleLowerCase('en'),r.away.trim().toLocaleLowerCase('en')]);
  }
  function collect(ledger,now=Date.now()){
    const records=[],seen=new Set();let excluded=0,pending=0,duplicates=0;
    const rows=(Array.isArray(ledger)?ledger:[]).slice().sort((a,b)=>time(a.createdAt)-time(b.createdAt));
    for(const r of rows){
      const startMs=time(r.kickoffAt||r.auditedKickoffAt),created=time(r.createdAt);
      if(r.forwardTestEligible!==true || !Number.isFinite(created) || !Number.isFinite(startMs) || created>=startMs ||
         !markets.includes(r.market) || !tiers.includes(r.tier) || !r.league ||
         typeof r.home!=='string' || !r.home.trim() || typeof r.away!=='string' || !r.away.trim()){
        excluded++;continue;
      }
      if(r.status==='PENDING'){pending++;continue}
      if(r.status!=='SETTLED'||typeof r.won!=='boolean'||startMs>now){excluded++;continue}
      const key=matchKey(r);
      if(seen.has(key)){duplicates++;continue}
      seen.add(key);records.push({...r,startMs,home:r.home.trim(),away:r.away.trim()});
    }
    return {records,excluded,pending,duplicates};
  }
  function filter(records,options={},now=Date.now()){
    const since=options.days?now-Number(options.days)*86400000:-Infinity;
    return records.filter(r=>r.startMs>=since && r.startMs<=now &&
      (!options.tier||r.tier===options.tier) && (!options.market||r.market===options.market) &&
      (!options.league||r.league===options.league) &&
      (!options.team||[teamId(r.league,r.home),teamId(r.league,r.away)].includes(options.team)));
  }
  function summary(records){
    const n=records.length,wins=records.filter(r=>r.won===true).length;
    return {n,wins,losses:n-wins,hitRate:n?wins/n:null,lowerBound:wilsonLower(wins,n)};
  }
  function wilsonLower(wins,n){
    if(!n)return 0;
    // Lower bound of the 95% two-sided Wilson interval; used only for display ranking.
    const z=1.959963984540054,p=wins/n,z2=z*z;
    return Math.max(0,(p+z2/(2*n)-z*Math.sqrt(p*(1-p)/n+z2/(4*n*n)))/(1+z2/n));
  }
  function group(records,kind='league'){
    const groups=new Map();
    for(const r of records){
      const members=kind==='team'?[...new Set([r.home,r.away])].map(name=>({id:teamId(r.league,name),name,league:r.league,leagueName:r.leagueName||r.league})):
        [{id:r.league,name:r.leagueName||r.league,league:r.league,leagueName:r.leagueName||r.league}];
      // One match contributes once per participating team, never twice to a league.
      for(const member of new Map(members.map(m=>[m.id,m])).values()){
        if(!groups.has(member.id))groups.set(member.id,{...member,records:[]});
        groups.get(member.id).records.push(r);
      }
    }
    return [...groups.values()].map(g=>({...g,...summary(g.records)}));
  }
  function rank(groups,{min=1,sort='confidence',limit=5}={}){
    const metric=sort==='rate'?'hitRate':'lowerBound';
    return groups.filter(g=>g.n>=Number(min)).slice().sort((a,b)=>b[metric]-a[metric] || b.n-a.n || b.hitRate-a.hitRate || a.name.localeCompare(b.name,'tr')).slice(0,limit);
  }
  return {collect,filter,summary,group,rank,wilsonLower,teamId};
})();
if(typeof module!=='undefined'&&module.exports)module.exports=OpusPerformance;

let performanceData=null,performanceInitialized=false,performanceLimit=50;
function renderPerformance(data){
  performanceData=data;
  const byId=id=>document.getElementById(id),api=OpusPerformance;
  const html=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const percent=x=>x==null?'—':new Intl.NumberFormat('tr-TR',{style:'percent',maximumFractionDigits:1}).format(x);
  const marketNames={U25:'2,5 Alt',O25:'2,5 Üst',BTTS_NO:'KG Yok',BTTS_YES:'KG Var',HOME:'Ev kazanır',DRAW:'Beraberlik',AWAY:'Deplasman kazanır'};
  if(!performanceInitialized){
    for(const [key,name] of Object.entries(marketNames))byId('perf-market').add(new Option(name,key));
    for(const id of ['perf-version','perf-period','perf-tier','perf-market','perf-min','perf-sort','perf-league','perf-team','perf-result']){
      byId(id).onchange=()=>{
        if(id!=='perf-team'&&id!=='perf-result')byId('perf-team').value='';
        performanceLimit=50;renderPerformance(performanceData);
      };
    }
    byId('perf-more').onclick=()=>{performanceLimit+=50;renderPerformance(performanceData)};
    performanceInitialized=true;
  }
  byId('perf-updated').textContent='Veri kontrolü: '+new Date(data.updatedAt).toLocaleString('tr-TR',{timeZone:'Europe/Istanbul'})+' (Türkiye)';
  const now=Date.now(),audit=api.collect(data.ledger,now);
  const filters={version:byId('perf-version').value,days:Number(byId('perf-period').value),tier:byId('perf-tier').value,market:byId('perf-market').value};
  const base=api.filter(audit.records,filters,now),overview=api.summary(base);
  const rankOptions={min:Number(byId('perf-min').value),sort:byId('perf-sort').value,limit:5};
  byId('perf-total').textContent=overview.n;byId('perf-wins').textContent=overview.wins;
  byId('perf-losses').textContent=overview.losses;byId('perf-rate').textContent=percent(overview.hitRate);
  byId('perf-data-note').textContent=`Seçili filtrelerde ${base.length} sonuçlanan aday. Tüm sürümlerde ${audit.records.length} doğrulanmış ve sonuçlanmış kayıt · ${audit.pending} sonuç bekliyor · ${audit.excluded} hesap dışı`+
    (audit.duplicates?` · ${audit.duplicates} yinelenen kayıt sayılmadı`:'')+
    '. Başarı, ilk kaydedilen tahminin gerçek sonuçla karşılaştırılmasıdır. Yeni sürümün başarısı eski modelden ayrı izlenir.';
  byId('perf-ranking-note').textContent=rankOptions.sort==='confidence'?
    'Sıralama başarıyı ve maç sayısını birlikte dikkate alır. Örneğin 1/1 yapan lig, 18/20 yapan ligin önüne geçmez. Yüzde sütunu gerçekleşen isabet oranıdır.':
    'Sıralama doğrudan gerçekleşen başarı yüzdesine göredir; eşitlikte daha çok maç öne çıkar. Az maçla oluşan yüksek yüzdeler kalıcı başarı göstermez.';
  const leagues=api.group(base),topLeagues=api.rank(leagues,rankOptions);
  const sample=g=>`<span class="sample ${g.n<20?'aggressive':''}">${g.n<20?'Az veri':'20+ maç'}</span>`;
  const rate=g=>`<b>${percent(g.hitRate)}</b><span class="hit-bar" aria-hidden="true"><i style="width:${g.hitRate*100}%"></i></span>`;
  byId('perf-leagues').innerHTML=topLeagues.length?topLeagues.map((g,i)=>`<tr><td>${i+1}</td><td><button class="rank-link" data-league="${html(g.id)}">${html(g.name)}</button></td><td>${rate(g)}</td><td>${g.wins} / ${g.n}</td><td>${g.losses}</td><td>${sample(g)}</td></tr>`).join(''):
    '<tr><td colspan="6">Bu filtrelerde sıralanabilecek lig yok. Dönemi genişletebilir veya en az maç sayısını azaltabilirsiniz.</td></tr>';
  byId('perf-league-note').textContent=topLeagues.length<5?`${topLeagues.length} lig gösteriliyor; seçili ölçütlerle beş lig için yeterli kayıt yok.`:'İlk 5 lig · Takımlarını ve maçlarını görmek için lig adına tıklayın.';
  const previousLeague=byId('perf-league').value,previousTeam=byId('perf-team').value;
  byId('perf-league').replaceChildren(new Option('Tüm ligler',''));
  for(const g of leagues.slice().sort((a,b)=>a.name.localeCompare(b.name,'tr')))byId('perf-league').add(new Option(g.name,g.id));
  byId('perf-league').value=leagues.some(g=>g.id===previousLeague)?previousLeague:'';
  const league=byId('perf-league').value,scoped=api.filter(base,{league},now);
  const teams=api.group(scoped,'team'),topTeams=api.rank(teams,rankOptions);
  byId('perf-team').replaceChildren(new Option('Tüm takımlar',''));
  for(const g of teams.slice().sort((a,b)=>a.name.localeCompare(b.name,'tr')))byId('perf-team').add(new Option(`${g.name} · ${g.leagueName}`,g.id));
  byId('perf-team').value=teams.some(g=>g.id===previousTeam)?previousTeam:'';
  byId('perf-team-title').textContent='En başarılı 5 takım'+(league?' · '+(data.leagues[league]||league):' · Tüm ligler');
  byId('perf-teams').innerHTML=topTeams.length?topTeams.map((g,i)=>`<tr><td>${i+1}</td><td><button class="rank-link" data-team="${i}">${html(g.name)}</button><small class="league-caption">${html(g.leagueName)}</small></td><td>${rate(g)}</td><td>${g.wins} / ${g.n}</td><td>${g.losses}</td><td>${sample(g)}</td></tr>`).join(''):
    '<tr><td colspan="6">Bu filtrelerde sıralanabilecek takım yok. Sonuçlar biriktikçe takım sıralaması oluşacak.</td></tr>';
  for(const button of byId('perf-leagues').querySelectorAll('[data-league]'))button.onclick=()=>{
    byId('perf-league').value=button.dataset.league;byId('perf-team').value='';performanceLimit=50;renderPerformance(performanceData);
  };
  for(const button of byId('perf-teams').querySelectorAll('[data-team]'))button.onclick=()=>{
    byId('perf-team').value=topTeams[Number(button.dataset.team)].id;performanceLimit=50;renderPerformance(performanceData);
  };
  const team=byId('perf-team').value,allMatches=api.filter(scoped,{team},now),detailSummary=api.summary(allMatches);
  const scopeName=team?teams.find(g=>g.id===team).name:league?(data.leagues[league]||league):'Tüm ligler';
  byId('perf-match-title').textContent='Tahminlerin sonuçları · '+scopeName;
  byId('perf-match-summary').textContent=`${detailSummary.wins} doğru / ${detailSummary.n} sonuçlanan maç · Başarı ${percent(detailSummary.hitRate)}`;
  const result=byId('perf-result').value;
  const matches=allMatches.filter(r=>!result||(result==='won'?r.won:!r.won)).sort((a,b)=>b.startMs-a.startMs);
  byId('perf-matches').innerHTML=matches.length?matches.slice(0,performanceLimit).map(r=>`<tr><td>${new Date(r.startMs).toLocaleDateString('tr-TR',{timeZone:'Europe/Istanbul'})}</td><td>${html(r.leagueName||r.league)}</td><td>${html(r.home)} – ${html(r.away)}</td><td>${html(marketNames[r.market])}<small class="league-caption">${html(r.tier)}</small></td><td>${percent(r.p)}</td><td>${r.hg!=null&&r.ag!=null?html(r.hg)+'–'+html(r.ag):'—'}</td><td class="${r.won?'safe':'bad'}">${r.won?'DOĞRU':'YANLIŞ'}</td></tr>`).join(''):
    '<tr><td colspan="7">Bu seçimde sonuçlanan tahmin yok.</td></tr>';
  byId('perf-match-count').textContent=`${Math.min(performanceLimit,matches.length)} / ${matches.length} maç gösteriliyor. Sonuç filtresi sıralamaları ve başarı yüzdesini değiştirmez.`;
  byId('perf-more').hidden=matches.length<=performanceLimit;
}

let D=null, selectedId=null;
const $=id=>document.getElementById(id);
const labels={U25:'2,5 Alt',O25:'2,5 Üst',BTTS_NO:'KG Yok',BTTS_YES:'KG Var',HOME:'Ev kazanır',DRAW:'Beraberlik',AWAY:'Deplasman kazanır'};
const esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pct=x=>x==null?'—':(x*100).toFixed(1)+'%';
const edge=x=>x==null?'—':(x>=0?'+':'')+(x*100).toFixed(1)+' puan';
const date=x=>x?new Date(x).toLocaleString('tr-TR',{timeZone:'Europe/Istanbul',dateStyle:'short',timeStyle:'short'}):'Bilinmiyor';
const tag=t=>`<span class="tag ${t==='GÜVENLİ'?'safe':t==='DENGELİ'?'balanced':t==='AGRESİF'?'aggressive':'pass'}">${esc(t)}</span>`;
function selected(){return [...$('league').selectedOptions].map(x=>x.value)}
function isUpcoming(p,now=Date.now()){
  return Number.isFinite(Date.parse(p.kickoffAt)) && Date.parse(p.kickoffAt)>now &&
    !D.ledger.some(r=>r.id===p.id && r.status==='SETTLED');
}
async function load(){
  try{
    const response=await fetch('data/dashboard.json?x='+Date.now(),{cache:'no-store'});
    if(!response.ok)throw Error('Veri alınamadı ('+response.status+')');
    const value=await response.json();
    if(!Array.isArray(value.predictions)||!Array.isArray(value.ledger))throw Error('Veri biçimi geçersiz');
    D=value;render();
  }catch(e){$('stamp').textContent='Son kontrol başarısız; son gösterilen veri korunuyor.';$('log').textContent=String(e)}
}
function render(){
  const opts=$('league');
  if(!opts.options.length)Object.entries(D.leagues).forEach(([k,v])=>{
    const o=new Option(v+' ['+k+']',k);o.selected=['E1','D2','I2','SP2','F2','N1','P1','T1'].includes(k);opts.add(o);
  });
  const s=new Set(selected()),now=Date.now();
  const ps=D.predictions.filter(x=>s.has(x.league)&&isUpcoming(x,now)).sort((a,b)=>Date.parse(a.kickoffAt)-Date.parse(b.kickoffAt));
  $('kL').textContent=s.size;$('kM').textContent=ps.length;
  $('kA').textContent=ps.filter(x=>x.decision.tier!=='PAS').length;
  $('kP').textContent=ps.filter(x=>x.decision.tier==='PAS').length;
  $('kS').textContent=D.staleSources;
  const age=Math.max(0,Math.floor((now-Date.parse(D.updatedAt))/60000));
  $('stamp').textContent='Son veri kontrolü: '+date(D.updatedAt)+' (Türkiye) · '+age+' dakika önce';
  $('stamp').classList.toggle('bad',age>(D.refreshIntervalMinutes||120)*2);
  const health=D.health||{};
  $('freshness').textContent='Kaynak fikstür aralığı: '+date(health.fixtureFirstDate)+' — '+date(health.fixtureLastDate)+
    '. Otomatik kontrol yaklaşık 2 saatte bir yapılır. Kaynağın yeni sonuç veya fikstür yayımlaması ayrıca beklenir.'+
    (D.staleSources?' '+D.staleSources+' kaynak son indirilen önbellekten okunuyor.':'')+
    (health.futureFixtureCount===0?' Kaynakta henüz başlamamış desteklenen maç yok.':'');
  $('pred').innerHTML=ps.length?ps.map((p,i)=>`<tr data-i="${i}" style="cursor:pointer"><td>${esc(p.leagueName)}</td><td>${date(p.kickoffAt)}</td><td>${esc(p.home)} – ${esc(p.away)}</td><td>${p.lambdaH.toFixed(2)} / ${p.lambdaA.toFixed(2)}</td><td>${esc(p.topScores[0]?.score||'—')}</td><td>${tag(p.decision.tier)} ${esc(labels[p.decision.market]||'')}</td><td>${pct(p.decision.p)}</td><td>${edge(p.decision.edge)}</td></tr>`).join(''):
    '<tr><td colspan="8">Seçili liglerde tahmin üretilebilen, henüz başlamamış maç yok. Yeni fikstür bekleniyor.</td></tr>';
  [...$('pred').querySelectorAll('[data-i]')].forEach((tr,i)=>tr.onclick=()=>{selectedId=ps[i].id;detail(ps[i])});
  const current=ps.find(p=>p.id===selectedId);
  if(current)detail(current);else{$('detail').textContent='Bir maça tıklayın. Yedi pazarın olasılıklarını ve karar gerekçelerini burada görebilirsiniz.';selectedId=null}
  $('matrix').innerHTML=[...s].map(k=>{
    const m=D.matrix[k];if(!m)return '';
    return `<tr><td>${esc(D.leagues[k])}</td>${Object.keys(labels).map(x=>`<td title="Örneklem: ${m.matrix[x]?.n||0}">${m.matrix[x]?.score?.toFixed(0)??'—'}</td>`).join('')}<td>${m.decisionMetrics?.score?.toFixed(0)??'—'}</td></tr>`;
  }).join('');
  const led=D.ledger.filter(x=>s.has(x.league)).slice().sort((a,b)=>Date.parse(b.auditedKickoffAt||b.createdAt)-Date.parse(a.auditedKickoffAt||a.createdAt));
  $('ledger').innerHTML=led.map(x=>{
    let status=x.status==='SETTLED'?(x.won?'DOĞRU':'YANLIŞ'):
      (Date.parse(x.kickoffAt||x.auditedKickoffAt)<=now?'SONUÇ KAYNAĞI BEKLENİYOR':'MAÇ BEKLENİYOR');
    if(!x.forwardTestEligible)status='TEST DIŞI · '+(x.status==='SETTLED'?status:'Zaman doğrulanamadı');
    return `<tr><td>${esc(x.date)}</td><td>${esc(x.leagueName)}</td><td>${esc(x.home)} – ${esc(x.away)}</td><td>${tag(x.tier)} ${esc(labels[x.market]||x.market)}</td><td title="${esc(x.auditReason)}">${status}${x.status==='SETTLED'?` (${x.hg}–${x.ag})`:''}<br><small>${!x.forwardTestEligible?esc(x.auditReason):'Maç öncesi kayıt'}</small></td></tr>`;
  }).join('');
  const excluded=led.filter(x=>!x.forwardTestEligible).length;
  $('audit').textContent=excluded+' kayıt maç öncesi tahmin testinin dışında. Eski kararlar ve sonuçlar saklanır; bu kayıtlar ileriye dönük başarı hesabına katılmaz.';
  renderPerformance(D);
  $('log').textContent=D.log.map(x=>`${x.ok?'OK':'HATA'} ${x.source}: ${x.message}${x.stale?' [ÖNBELLEK]':''}`).join('\n');
}
function detail(p){
  const locked=p.lockedPrediction;
  $('detail').innerHTML=`<b>${esc(p.home)} – ${esc(p.away)}</b><br>${date(p.kickoffAt)} (Türkiye)<br>Takım örneklemi güvenilirliği: ${pct(p.reliability)}
    <p><b>Güncel karar: ${esc(p.decision.tier)} ${esc(labels[p.decision.market]||'')}</b><br>Model ${pct(p.decision.p)} · Piyasa ${pct(p.decision.marketP)} · Fark ${edge(p.decision.edge)}</p>
    ${locked?`<p>Testte kilitli karar: <b>${esc(locked.tier)} ${esc(labels[locked.market])}</b> · ${pct(locked.p)}<br>Kayıt: ${date(locked.createdAt)}${locked.forwardTestEligible?'':' · TEST DIŞI'}</p>`:''}
    <div style="overflow:auto"><table><thead><tr><th>Pazar</th><th>Model</th><th>Piyasa</th><th>Fark</th></tr></thead><tbody>${Object.keys(labels).map(k=>{
      const c=(p.candidates||[]).find(x=>x.market===k);
      return `<tr><td>${labels[k]}</td><td>${pct(p.model[k])}</td><td>${pct(p.market[k])}</td><td>${edge(c?.edge)}</td></tr><tr><td colspan="4" class="note">${esc(c?.tier||'PAS')}: ${esc(c?.reason||'Gerekçe için veri güncellemesi bekleniyor')}</td></tr>`;
    }).join('')}</tbody></table></div><p>KG piyasa oranı mevcut kaynakta yok. Köşe vuruşu, kart, ilk yarı ve diğer gol çizgileri bu motor sürümünde hesaplanmıyor.</p>`;
}
$('league').onchange=()=>D&&render();$('refresh').onclick=load;
const local=location.hostname==='127.0.0.1'||location.hostname==='localhost';
$('update').hidden=!local;
$('update').onclick=async()=>{
  const b=$('update');b.disabled=true;b.textContent='Güncelleniyor…';
  try{const r=await fetch('/api/update',{method:'POST'});if(!r.ok)throw Error('Veri kontrolü tamamlanamadı');await load()}
  catch(e){$('log').textContent=String(e)}finally{b.disabled=false;b.textContent='Şimdi Veriyi Güncelle'}
};
load();
setInterval(()=>{if(!document.hidden)load()},5*60*1000);
setInterval(()=>{if(D&&!document.hidden)render()},30*1000);
document.addEventListener('visibilitychange',()=>{if(!document.hidden)load()});

function switchView(){
  const performance=location.hash==='#basari';
  $('performance-view').hidden=!performance;$('predictions-view').hidden=performance;
  $('view-performance').setAttribute('aria-pressed',String(performance));
  $('view-predictions').setAttribute('aria-pressed',String(!performance));
}
$('view-performance').onclick=()=>{location.hash='basari'};
$('view-predictions').onclick=()=>{location.hash='tahminler'};
window.addEventListener('hashchange',switchView);switchView();

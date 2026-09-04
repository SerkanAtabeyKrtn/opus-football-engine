const externalStatus={fresh:'Güncel indirme',cached:'Geçerli önbellek',stale:'Eski veri',unavailable:'Veri alınamadı',unsupported:'Bu lig için kaynak yok',unmatched:'Takım eşleşmedi',not_published:'Kesin ilk 11 alınmadı',confirmed:'Kesin ilk 11'};
const playerStatus={i:'Sakat',d:'Durumu şüpheli',s:'Cezalı',u:'Kullanılamıyor',a:'Uygun'};
function externalDate(value){return value?date(value)+' (Türkiye)':'—'}
function sourceName(key){return key.startsWith('xg_')?'Understat':key==='fpl'?'Premier League / FPL':'ESPN'}
function renderExternal(data){
  const e=data.enrichment, target=$('external-coverage');
  if(!target)return;
  if(!e){$('external-status').textContent='Ek veri raporu henüz alınamadı.';return}
  const rows=Object.values(e.coverage||{}),sum=k=>rows.reduce((n,r)=>n+(r[k]||0),0);
  const failed=(e.sources||[]).filter(s=>!['fresh','cached'].includes(s.status)).length;
  $('external-status').textContent=`${sum('fixtures')} maçta: iki takım için xG geçmişi ${sum('xg')}, oyuncu durumu ${sum('injuries')}, takım listesi ${sum('squads')}, kesin ilk 11 ${sum('lineups')}. ${failed} kaynak isteğinde güncel veri alınamadı. Son işlem: ${externalDate(e.updatedAt)}.`;
  target.innerHTML=Object.entries(e.coverage||{}).map(([code,c])=>`<tr><td>${esc(data.leagues[code]||code)}</td><td>${c.fixtures}</td><td>${c.xg}</td><td>${c.injuries}</td><td>${c.squads}</td><td>${c.lineups}</td></tr>`).join('');
  $('external-sources').innerHTML=(e.sources||[]).map(s=>`<tr><td>${sourceName(s.source)}<small class="league-caption">${esc(s.source)}</small></td><td>${esc(externalStatus[s.status]||s.status)}</td><td>${externalDate(s.fetchedAt)}</td></tr>`).join('');
  const families=data.quality?.families||{};
  $('external-xg-model').textContent='Geçmiş xG, aynı yöntem seçimi maçlarında xG içermeyen modelle karşılaştırıldı. '+Object.values(families).map(f=>`${f.name}: ${f.usesXg?'xG kullanılıyor':'xG eklemek seçim döneminde daha iyi sonuç vermedi; temel model seçildi'}`).join(' · ')+'. Bu seçim geçmiş testte veya gelecekte mutlaka üstünlük sağlamaz.';
}
function externalDetail(p){
  const e=p.enrichment||{},modelFamilies=D?.quality?.families||{};
  const blocks=['home','away'].map(side=>{
    const c=e[side]||{},availability=c.availability||{},squad=c.squad||{},lineup=c.lineup||{},xg=p.context?.[side]?.xg||{};
    const usable=['fresh','cached'].includes(availability.status);
    const missing=(availability.players||[]).map(a=>`<li><b>${esc(a.name)}</b> · ${esc(playerStatus[a.status]||a.status)}${a.chanceNextRound!=null?` · Sonraki tur oynama olasılığı (kaynak): %${esc(a.chanceNextRound)}`:''}${a.news?`<br><small>${esc(a.news)}</small>`:''}${a.reportedAt?`<br><small>Haber zamanı: ${externalDate(a.reportedAt)}</small>`:''}</li>`).join('');
    const players=(squad.players||[]).map(a=>`<li>${esc(a.name)}${a.position?' · '+esc(a.position):''}</li>`).join('');
    const starters=(lineup.players||[]).map(a=>`<li>${esc(a.name)}</li>`).join('');
    return `<section><h4>${esc(p[side])}</h4><p><b>Geçmiş gerçek xG:</b> ${xg.matches?`${xg.matches} lig maçı · Üretilen ${xg.for.toFixed(2)} / verilen ${xg.against.toFixed(2)} ortalama`:'Bu takım için eşleşen geçmiş xG yok'}<br><small>Kaynak: Understat. Son sekiz lig maçı içinde bulunan kayıtlar; bugünkü maçın xG tahmini değildir.</small></p>
      <p><b>Oyuncu durumu:</b> ${esc(externalStatus[availability.status]||'Veri alınamadı')}<br><small>${esc(availability.source||'')} · Son indirme ${externalDate(availability.fetchedAt)}</small></p>
      ${missing?`<ul>${missing}</ul>`:`<p class="note">${usable?'Kaynakta şu anda bildirilen eksik oyuncu yok. Bu, kesin ilk 11 onayı değildir.':'Bilgi eksik; “sakat oyuncu yok” kabul edilmez.'}</p>`}
      <details><summary>Takım oyuncu listesi · ${squad.players?.length||0} oyuncu · ${esc(externalStatus[squad.status]||'Veri alınamadı')}</summary><p>Kaynak ${esc(squad.source||'—')} · ${externalDate(squad.fetchedAt)}. Bu liste maçın ilk 11’i değildir.</p>${players?`<ul>${players}</ul>`:''}</details>
      <p><b>${esc(externalStatus[lineup.status]||'Kesin ilk 11 alınmadı')}</b>${lineup.status==='confirmed'?` · ${externalDate(lineup.fetchedAt)}${lineup.formation?' · '+esc(lineup.formation):''}`:''}</p>${starters?`<ul>${starters}</ul>`:''}</section>`;
  }).join('');
  return `<div class="external-detail"><h3>Sakatlık, kadro ve xG</h3><p class="note">xG kullanılan tahmin grupları: ${Object.values(modelFamilies).filter(f=>f.usesXg).map(f=>esc(f.name)).join(', ')||'Bu ayarda yok'}. Oyuncu durumu ve kadro bilgisi ilk gözlemden itibaren arşivlenir; olasılığa sayısal etkisi henüz doğrulanmadı.</p>${blocks}<p class="note">${(e.notes||[]).map(esc).join(' ')}</p></div>`;
}

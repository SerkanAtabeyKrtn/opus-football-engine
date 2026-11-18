/* OPUS 1.7 additive panel: does not modify the existing dashboard renderer. */
(() => {
  const el = id => document.getElementById(id);
  const esc = s => String(s ?? '—').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fmt = v => Number.isFinite(v) ? (v*100).toFixed(1)+'%' : '—';
  const tr = value => {try{return new Date(value).toLocaleString('tr-TR',{timeZone:'Europe/Istanbul',dateStyle:'short',timeStyle:'short'});}catch{return '—';}};
  async function render(){
    try {
      const response = await fetch('data/dashboard.json?t='+Date.now(),{cache:'no-store'});
      if(!response.ok) throw Error('HTTP '+response.status);
      const d = await response.json();
      const f = d.freshness || {};
      if(el('opus17-health')) el('opus17-health').textContent = `Son analiz: ${tr(d.updatedAt)} · Kaynak: ${f.fixtureSource || d.health?.fixtureSource || 'bilinmiyor'} · Gelecek fikstür: ${f.futureFixtureCount ?? d.health?.futureFixtureCount ?? '—'} · Analiz: ${f.analysisReadyCount ?? d.predictions?.length ?? '—'}${f.warning ? ' · UYARI: '+f.warning : ''}${f.analysisCoverageWarning ? ' · UYARI: '+f.analysisCoverageWarning : ''}`;
      const rows = Object.entries(d.funnel||{}).map(([code,r])=>`<tr><td>${esc(d.leagues?.[code]||code)}</td><td>${r.fixtureRows||0}</td><td>${r.eligible||0}</td><td>${r.modelOk||0}</td><td>${r.approved||0}</td><td>${r.monitoring||0}</td><td>${esc(Object.entries(r.skippedReasons||{}).map(([k,v])=>`${k}: ${v}`).join(' · ')||'—')}</td></tr>`).join('');
      if(el('opus17-funnel')) el('opus17-funnel').innerHTML = '<table><thead><tr><th>Lig</th><th>Fikstür</th><th>Uygun</th><th>Analiz</th><th>Onaylı</th><th>İzleme pazarı</th><th>Eleme nedenleri</th></tr></thead><tbody>'+rows+'</tbody></table>';
      const observations = (d.monitoring||[]).flatMap(m=>(m.candidates||[]).map(c=>({m,c})));
      if(el('opus17-monitor')) el('opus17-monitor').innerHTML = observations.length ? observations.map(({m,c})=>`<tr><td>${esc(m.leagueName||m.league)}</td><td>${esc(m.home)} – ${esc(m.away)}</td><td>${tr(m.kickoffAt)}</td><td>${esc(c.market)}</td><td>${fmt(c.p)}</td><td>${Number.isFinite(c.referenceOdds)?c.referenceOdds.toFixed(2):'Yok'}</td><td>${esc(c.reason)}</td></tr>`).join('') : '<tr><td colspan="7">Şu an izlenecek maç bulunmuyor; veri güncelliği panelini kontrol edin.</td></tr>';
    } catch(e) {if(el('opus17-health')) el('opus17-health').textContent='V1.7 veri paneli yüklenemedi: '+e.message;}
  }
  render();
  el('refresh')?.addEventListener('click',render);
  document.addEventListener('visibilitychange',()=>{if(!document.hidden) render();});
})();

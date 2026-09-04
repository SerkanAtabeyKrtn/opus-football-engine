function renderQuality(data){
  const q=data.quality, audit=data.forecastAudit||{};
  if(!q){$('quality-status').textContent='Model kontrol raporu henüz alınamadı.';return}
  const approved=Object.values(q.gates||{}).filter(g=>g.eligible).length;
  $('quality-status').textContent='V'+q.version+' deneysel model · Gerçek maç öncesi sonuçlarla doğrulama sürüyor. “ADAY” kazanç veya isabet garantisi değildir.';
  $('quality-counts').textContent=`${q.counts.fit.toLocaleString('tr-TR')} maç: ilk ayar · ${q.counts.selection.toLocaleString('tr-TR')} maç: yöntem seçimi · ${q.counts.test.toLocaleString('tr-TR')} ayrı maç: son kontrol. Son kontrol maçları model katsayılarına öğretilmedi.`;
  $('quality-periods').textContent='İlk ayar: 1 Ocak 2026 öncesi. Yöntem seçimi: Ocak–Mart 2026. Bağımsız kontrol: Nisan–Haziran 2026. Geçmiş istatistikleri yeni maçlarla güncellenir; bu sürümün kalibrasyon yöntemi sabittir.';
  $('quality-live').textContent=`V${q.version}: ${audit.total||0} maçın ilk analizi kayıtlı · ${audit.settled||0} sonuçlandı · ${audit.pending||0} bekliyor. PAS verilen maçların yedi olasılığı da değişmeden saklanır.`;
  const number=x=>x==null?'—':Number(x).toFixed(4);
  $('quality-comparison').innerHTML=Object.values(q.families).map(f=>`<tr><td>${esc(f.name)}<small class="league-caption">${esc(f.method)} · ${f.new.n} maç</small></td><td>${pct(f.old.accuracy)}</td><td>${pct(f.new.accuracy)}</td><td>${pct(f.reference.accuracy)}<small class="league-caption">${esc(f.referenceName)}</small></td><td>${number(f.old.brier)} → ${number(f.new.brier)}<small class="league-caption">Referans: ${number(f.reference.brier)}</small></td></tr>`).join('');
  $('quality-gates-note').textContent=`${approved} / ${Object.keys(q.gates||{}).length} lig ve pazar birleşimi mevcut kontrol koşullarını karşılıyor. Diğerlerinde olasılıklar gösterilir, aktif aday verilmez. Küçük farklar ve az maç kalıcı üstünlük kanıtı değildir.`;
  $('quality-gates').innerHTML=Object.entries(data.leagues).map(([league,name])=>`<tr><td>${esc(name)}</td>${Object.keys(labels).map(k=>{
    const g=q.gates[league+'|'+k];return `<td title="${esc(g?.reason)}">${g?.eligible?'İzleme adayı':'PAS'}<small class="league-caption">${g?.candidateN||0} benzer karar / ${g?.n||0} test maçı</small></td>`
  }).join('')}</tr>`).join('');
  const selected=$('quality-family').value||'result', family=q.families[selected];
  $('quality-calibration').innerHTML=(family.bins||[]).map(b=>`<tr><td>%${Math.round(b.from*100)}–${Math.round(b.to*100)}</td><td>${b.n}</td><td>${pct(b.predicted)}</td><td>${pct(b.observed)}</td><td>${b.n<50?'Az veri':'Karşılaştırılabilir örneklem'}</td></tr>`).join('');
  $('quality-forward').innerHTML=Object.entries(audit.markets||{}).map(([k,m])=>`<tr><td>${labels[k]}</td><td>${m.n}</td><td>${pct(m.predicted)}</td><td>${pct(m.observed)}</td><td>${number(m.brier)}</td></tr>`).join('');
  $('quality-limitations').replaceChildren(...q.limitations.map(text=>{const p=document.createElement('p');p.textContent=text;return p}));
}
document.getElementById('quality-family').onchange=()=>D&&renderQuality(D);

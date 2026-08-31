# OPUS Football Probability Engine V1.1 — Test Raporu

## 1. Motor birim testleri — PASS
- Skor olasılık matrisi toplamı = 1.
- 2.5 Alt + 2.5 Üst = 1.
- KG Var + KG Yok = 1.
- Ev + Beraberlik + Deplasman = 1.
- De-vig piyasa olasılıkları toplamı = 1.
- Dengeli karar eşiği doğru sınıflandırılıyor.
- Gelecekteki bir maç sonucu geçmiş tarihteki tahmini değiştirmiyor (data leakage testi).

## 2. Forward-test defteri — PASS
- Mevcut bir tahmin yeniden hesaplandığında pazar, olasılık, edge ve tier geriye dönük değiştirilmiyor.
- Settlement yalnızca sonuç/status alanlarını güncelliyor.

## 3. Web sunucusu — PASS
- `index.html` HTTP 200.
- `data/dashboard.json` HTTP 200.
- Dashboard sürümü: 1.1.
- Veri modu: cache-first server-side.

## 4. CORS mimarisi — PASS
- Browser HTML içinde football-data.co.uk çağrısı yok.
- Browser HTML içinde allorigins/CORS proxy çağrısı yok.
- Dış veri erişimi yalnızca `app/update.py` sunucu katmanında.

## 5. Hata toleransı — PASS (kod/kontrat)
- Canlı indirme başarısızsa son başarılı raw cache kullanılır.
- Cache de yoksa veri eksikliği loglanır; tahmin uydurulmaz.
- JSON yazımı atomik geçici dosya + replace yöntemiyle yapılır.

## 6. Bulut otomasyonu — hazır
`.github/workflows/update.yml`:
- Her gün 05:15 UTC otomatik güncelleme.
- Cuma/Cumartesi/Pazar 12:15 UTC ek güncelleme.
- Tahmin/settlement/backtest sonrası `data` ve `raw` değişikliklerini repoya commit eder.

## Çalışma ortamı sınırı
Bu paket oluşturulurken modelin çalışma konteynerinden Football-Data CSV dosyasına doğrudan ağ indirmesi başarılamadı. Bu nedenle canlı kaynaktan sahte bir başarı sonucu raporlanmadı. Veri indirme katmanı tarayıcıdan çıkarılıp Python sunucu tarafına taşındı. Kullanıcı makinesinde veya GitHub Actions runner'ında ilk gerçek indirme `app/update.py` tarafından yapılacaktır.

# OPUS V1.5

Maç öncesi futbol olasılıkları, değişmez tahmin kaydı ve ölçülen model kalitesi.
Canlı site: https://serkanatabeykrtn.github.io/opus-football-engine/

## Yeni model

Gol geçmişi, ev/deplasman etkisi ve son sekiz maçın formuna; lig maçları arasındaki dinlenme, son 14 gündeki maç yoğunluğu ve mevcut geçmiş isabetli şut verisi eklenir. Sonuç olasılıkları düzenlileştirilmiş lojistik/çok sınıflı kalibrasyonla ayarlanır. Sonuç ve 2,5 gol gruplarında piyasa olasılıkları da girdi olarak kullanılır; karşılıklı golde piyasa oranı bulunmadığında model tabanlı kalibrasyon kullanılır.

- İlk eğitim: 1 Ocak 2026 öncesi, 6.797 uygun maç.
- Yöntem seçimi: Ocak–Mart 2026, 1.728 uygun maç; iki sabit düzenlileştirme seçeneği (30/100), piyasalı/piyasasız modeller aynı maçlarda karşılaştırılır.
- Katsayılar ilk iki dönemle yeniden kurulur. Son kontrol: Nisan–Haziran 2026, ayrı 1.062 maç.
- Son kontrol etiketleri katsayı eğitimine ve yöntem seçimine girmez. Bu dönemde lig/pazar aday izinleri denetlenir; buradaki sonuçlar yeni canlı test başarısı sayılmaz.
- Yeni sezon sonuçları takım formunu günceller; kalibrasyonu sessizce yeniden eğitmez. Yeni kalibrasyon için yeni, açık bir model sürümü ve zaman planı gerekir.

`Model Kontrolü` ekranı aynı maçlardaki eski/yeni/referans sonuçlarını, olasılık gruplarının gerçekleşme oranlarını ve her lig/pazarın aday durumunu gösterir. Yeni model eski motora göre üç grupta da daha düşük olasılık hatası verdi; maç sonucu ve 2,5 gol gruplarında piyasa referansını genel olarak geçemedi. Kalıcı üstünlük veya kazanç kanıtlanmış değildir.

## Karar ve gerçek takip

Yeni sürümde GÜVENLİ/DENGELİ/AGRESİF yerine ADAY veya PAS kullanılır. Eski etiketler eski kayıtlarda aynen saklanır.

ADAY için lig/pazar bağımsız testinde en az 80 maç ve olasılık ≥%55, referans oran üzerinden beklenen değer ≥%5 koşullarına benzeyen en az 30 karar aranır. Test olasılık hatası referanstan kötü olmamalı ve bu adayların ortalama olasılık–gerçekleşme farkı 8 puanı aşmamalıdır. Güncel maçın ağırlıklı takım örneklemleri en az sekiz olmalıdır. Eksik fiyat veya başarısız kaynak kontrolü aktif adayı engeller. Bunlar deneysel tarama kurallarıdır; çok sayıda lig/pazar karşılaştırması ve küçük örneklem nedeniyle kalıcı avantaj kanıtı değildir.

Görünen oranlar kaynağın referans fiyatlarıdır; bahis sitesinde halen mevcut oldukları doğrulanmış değildir. Beklenen değer `p × oran − 1` ile hesaplanır. Kalibre model olasılığı da hatalı olabilir. Hiçbir stake veya para işlemi otomatik yapılmaz.

`data/ledger.json` ilk seçilmiş kararı korur. `data/forecast-ledger.json`, PAS dahil her modellenebilen maçın yedi olasılığını sürüm başına maç başlamadan bir kez kaydeder. Sonradan model, oran veya karar değişse bile ilk kayıt değişmez. Sonuçlar fikstürden bağımsız işlenir. Başarı Analizi yeni modeli varsayılan olarak gösterir; Önceki motor filtresi eski sonuçları açar.

## Veri kapsamı

Football-Data CSV kaynağı kullanılır. Sakatlık, ceza, kadro ve gerçek xG kaynağı henüz bağlı değildir. Eksiklikler ekranda belirtilir. İsabetli şut xG olarak sunulmaz; dinlenme/yoğunluk yalnız mevcut lig maçlarını kapsar, kupa ve milli maçları kapsamaz. KG piyasa oranı kaynakta yoktur. Kart, korner ve ilk yarı pazarları hesaplanmaz.

Kaynak: https://www.football-data.co.uk/matches.php
Kalibrasyon yöntemi açıklaması: https://scikit-learn.org/stable/modules/calibration.html

## Güncelleme ve çalıştırma

GitHub görevi yaklaşık iki saatte bir çalışır. Kaynağın fikstür yayımlama zamanı ayrıca beklenir. Yeni tahmin yalnız henüz başlamamış maçlara üretilir; tarihi veya saati doğrulanamayan maçlar alınmaz. İlk yeni model kurulumu birkaç dakika sürebilir; değişmeyen eğitim verisinde kaydedilmiş model yeniden kullanılır.

Python 3.12 ve Node.js ile:

```text
python -m pip install -r requirements.txt
python -m unittest discover -s tests -p "test_*.py" -v
node tests/test_performance.js
python app/update.py
python app/server.py
```

Windows: START_OPUS.bat veya UPDATE_ONLY.bat. GitHub Pages üzerinde yerel veri güncelleme düğmesi gizlenir. Ekran beş dakikada bir veriyi yeniden okur; başlamış maçlar otuz saniyede bir listeden çıkarılır. Veri bağlantısı yapılandırılacaksa anahtarlar tarayıcıya veya açık depoya konulmamalıdır.

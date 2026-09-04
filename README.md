# OPUS V1.4

Bu sürüm veri kontrolünü, geçmiş maç filtresini ve test defterinin zaman denetimini düzeltir. Poisson modeli, olasılık eşikleri ve pazar sıralama formülü korunur.

## Güncellemeler

- Veri kontrolü yaklaşık iki saatte bir; GitHub kuyruk gecikmeleri mümkündür.
- Son veri kontrolü, verinin yaşı ve kaynağın fikstür aralığı ayrı gösterilir.
- Başlamış, sonucu mevcut veya saati doğrulanamayan maçlara yeni tahmin yazılmaz.
- İlk kayıt kilitlidir; güncel hesaplama ve testteki karar ayrı gösterilir.
- Maç sonrası oluşturulan kayıtlar silinmeden TEST DIŞI işaretlenir ve başarı özetinden çıkarılır.
- Fikstürden düşen kayıtlar sezon sonuçlarından kapatılır. Sonuç gecikmesi açıkça gösterilir.
- Yedi pazar için olasılık, piyasa farkı ve seçilme/elenme gerekçesi gösterilir.
- Bozuk sonuç CSV'si son iyi önbelleği bozmaz. Bozuk defter güncellemeyi durdurur.

## Kaynak ve model sınırları

Football-Data CSV'si canlı skor servisi değildir. Fikstür ve oranlar genel olarak salı ve cuma yayımlanır. Yeni veri yayımlanmadığında daha sık kontrol yapmak yeni maç veya sonuç getirmez. updatedAt kontrolün tamamlandığı zamandır; her kaynak kaydının o anda değiştiği anlamına gelmez.

Model 2,5 Alt/Üst, KG Yok/Var ve Ev/Beraberlik/Deplasman olasılıklarını hesaplar. Mevcut kaynakta KG oranları yoktur; bu yüzden KG için DENGELİ/AGRESİF piyasa farkı kriteri karşılanamaz. Önceki GÜVENLİ kuralı yüksek model olasılığıyla piyasa oranı olmadan çalışabilir; ekran bunu açıklar. İsteğe bağlı oddsBTTSYes ve oddsBTTSNo alanları eklendi; yeni veri sağlayıcısı bağlanmadı.

Korner, kart, ilk yarı ve diğer gol çizgileri uygulanmamıştır. Lig–pazar matrisi rapordur; ana kararın sıralama ağırlığı değildir.

Kaynak maç saatleri Europe/London kabulüyle yaz/kış saatine göre UTC'ye çevrilir; sağlayıcı değiştiğinde bu kabul yeniden doğrulanmalıdır. Belirsiz veya eksik saatler tahmine alınmaz. Ekran Türkiye saatini gösterir. Yeni kayıtlarda createdAt, kickoffAt ve modelVersion saklanır. Eski kayıtların zamanı sezon/fikstür kayıtlarından denetlenir. Sağlayıcının takım adını veya maç tarihini değiştirmesini mevcut kimlik yapısı otomatik çözmez.

## Paketi uygulama

1. GitHub Desktop ile projenin son sürümünü alın ve kendi değişikliklerinizi saklayın.
2. Paket dosyalarını klasör yapısını koruyarak proje üzerine kopyalayın. Paket data/ ve raw/ içermez; mevcut defteri değiştirmeyin.
3. Aşağıdaki testleri çalıştırıp kaynak değişikliklerini GitHub'a gönderin.
4. OPUS automatic data update kaynak değişikliklerinde otomatik başlar. Gerekirse Actions üzerinden Run workflow kullanılabilir.
5. Veri işlemi ve mevcut Pages yayını tamamlandıktan sonra V1.3 başlığını, son veri kontrolünü ve TEST DIŞI kayıtları doğrulayın. Yeni fikstür yoksa boş aktif liste beklenen davranıştır.

## Yerel kullanım ve test

Python 3.12 önerilir. Windows saat dilimi verisi için tzdata gerekebilir; başlatma dosyaları eksikse kurar. GitHub iş akışı da bağımlılığı kurar.

```text
python -m pip install -r requirements.txt
python tests/test_engine.py
python tests/test_ledger.py
python tests/test_update.py
python -m unittest discover -s tests -p "test_lifecycle.py" -v
```

START_OPUS.bat yerel veri işlemini ve arayüzü açar. GitHub Pages üzerinde yerel güncelleme düğmesi gizlidir. Ekran beş dakikada bir veriyi yeniden okur, otuz saniyede bir başlamış maçları eler.

Bu düzeltmeler modelin tahmin başarısını veya kârlılığını doğrulamaz.

## V1.4 — Başarı Analizi

Üstteki Başarı Analizi sekmesi veya #basari adresi açılır. Lig sıralaması mevcut tahmin ekranındaki varsayılan sekiz lige bağlı değildir; tüm liglerdeki geçerli sonuçları kapsar.

- En başarılı 5 lig; doğru/toplam, yanlış ve başarı yüzdesi.
- Lige tıklayınca o ligin en başarılı 5 takımı ve tüm maçları.
- Takıma tıklayınca takımın maçları, kilitli tahmin, model olasılığı, gerçek skor ve sonuç.
- Dönem (tümü/30/90 gün), karar türü, pazar ve en az maç sayısı filtreleri.
- Yalnız doğru / yalnız yanlış seçimi sadece maç listesini filtreler; başarı oranının paydasını değiştirmez.
- Bir maç lig toplamında bir kez; her iki takımın katılım kaydında birer kez sayılır. Takım satırı takımın galibiyetini değil motorun o maçlardaki tahmin isabetini ölçer.
- Bekleyen, geç kaydedilen, zamanı doğrulanmayan, yinelenen ve PAS kayıtları başarıya katılmaz.

Varsayılan sıralama, başarı ve maç sayısını birlikte dikkate almak için %95 iki taraflı Wilson aralığının alt sınırını kullanır. Bu puan ekrandaki gerçekleşen başarı yüzdesinden farklıdır. Başarı yüzdesi seçeneğiyle doğrudan isabet oranına göre de sıralanabilir. 20'den az maç Az veri etiketlidir; 20 maçın aşılması da kesin başarı iddiası değildir. Sıralama karar motorunun kurallarını değiştirmez.

Yöntem: https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm
Yeni hesaplama testleri: node tests/test_performance.js
Bu test için Node.js gerekir; GitHub Ubuntu çalıştırıcısında mevcuttur. Arayüzün kullanımı için Node.js kurulması gerekmez.

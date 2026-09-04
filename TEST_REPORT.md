# V1.3 doğrulama — 4 Eylül 2026

İncelenen üretim sürümü: d929e5cc7275ae4d50942c7459bd33cc161a5db9.
Veri anı: 2026-09-04 05:27:22 UTC.

- Mevcut motor ve fikstür şema testleri geçti.
- On bir yeni test; saat dilimi, geçmiş/sonuçlanmış maç engeli, kayıt değişmezliği, geç kayıtların denetimi, sonuç eşleştirme, sonuç bekleme, eksik zaman, yedi pazar, KG oranları, bozuk CSV ve defter koruması ile ana güncelleme akışını kapsıyor.
- JavaScript sözdizimi kontrolü geçti.
- Üretim CSV'leri ve defteri ağdan yeniden çekilmeden değerlendirildi: 52 kayıt korundu, 43 geç kayıt test dışında, 9 kayıt maç öncesi. Desteklenen 23 fikstürün tamamı geçmiş olduğundan aktif tahmin sıfır. Bu yerel kontrol için değişmeyen geçmiş performans matrisleri yeniden kullanıldı.
- Tarayıcıda boş aktif liste, Türkiye saati ve TEST DIŞI etiketleri doğrulandı. Ayrı, açıkça etiketlenmiş sınama maçıyla yedi pazarın gerekçeleri ve eksik KG oranı gösterimi kontrol edildi.

Canlı site değiştirilmedi. Yeni zamanlamanın canlı çalışması, değişiklikler gönderilip iş akışı tamamlandığında doğrulanmalıdır. Üretilmiş önizleme verisi ve sınama fikstürleri pakete dahil edilmedi.


## V1.4 başarı ekranı doğrulaması

- Yedi yeni başarı analizi testi geçti: geçerli kayıt süzme, aynı maçın yinelenmesi, lig/takım sayımı, birleşik filtreler, küçük örneklemin sıralanması, ilk beş sınırı ve boş/kayıp örneklem.
- On bir önceki yaşam döngüsü testi tekrar geçti. Yeni arayüz dosyaları ve dashboard.js sözdizimi kontrolünden geçti.
- Gerçek denetlenmiş veride 9 maç / 6 doğru / 3 yanlış; toplam %66,7.
- Başarı + maç sayısı sırası: Scotland Premiership 3/4; Championship 1/1; Ligue 1 1/1; Portugal 1 1/2; La Liga 2 0/1. Bu kayıtların tamamı az örneklemlidir.
- Tarayıcıda lig → takım → maç geçişi doğrulandı. Aberdeen seçimi Celtic–Aberdeen maçını ve 1/1 sonucu gösterdi. Yalnız yanlış filtresi boş liste gösterirken 1/1 özetini değiştirmedi.
- DENGELİ filtresinde 5 maç / 3 doğru / %60 ve 4 lig gösterildi. En az 20 maç filtresi boş sıralama durumunu doğru gösterdi. Sayfa görünümü kontrol edildi.
- Canlı siteye gönderim yapılmadı. HTML önizleme 4 Eylül 2026 veri anını içerir; canlı veri çekmez. ZIP kaynak değişikliklerini içerir, data/ veya raw/ içermez.

# OPUS V1.5 — model ve doğrulama raporu

4 Eylül 2026. Baz sürüm: V1.4, ana kaynak birleştirmesi fe7d89c; üretim veri anı 07:27:45 UTC.

## Zaman sıralı karşılaştırma

6.797 eğitim, 1.728 yöntem seçimi, 1.062 bağımsız değerlendirme maçı. Bağımsız dönem Nisan–Haziran 2026'dır. Her maçın özellikleri yalnız daha önceki tarihlerden hesaplandı. Katsayılar bağımsız test dönemiyle eğitilmedi. Aynı değerlendirme maçlarında:

| Grup | Eski isabet | Yeni isabet | Referans isabet | Eski Brier | Yeni Brier | Referans Brier |
|---|---:|---:|---:|---:|---:|---:|
| Maç sonucu | %48,5 | %50,9 | %52,2 | 0,2047 | 0,2002 | 0,1993 |
| 2,5 gol | %53,6 | %58,4 | %59,4 | 0,2478 | 0,2413 | 0,2397 |
| Karşılıklı gol | %53,0 | %56,1 | %57,0 | 0,2482 | 0,2435 | 0,2462 |

İlk iki referans piyasa olasılığıdır; KG referansı eğitim dönemi sonuç sıklığıdır. İsabet, her grupta en olası sonucu seçme isabetidir, yalnız ADAY kararlarının sonucu değildir. Brier burada sınıflar üzerinden ortalama kare olasılık hatasıdır. Gruplar farklı sınıf sayılarına sahip olduğundan farklı grupların Brier değerleri doğrudan birbirine üstünlük ölçüsü olarak kullanılmaz.

Gelişmeler bu örneklemde gözlenmiştir; istatistiksel olarak kalıcı üstünlük ya da kazanç kanıtı değildir. Piyasa ölçütü sonuç ve 2,5 golde genel olarak hâlâ daha iyi. 112 lig/pazar birleşiminin yalnız biri mevcut aday kontrolünü geçti (La Liga 2 / 2,5 Üst; 107 maç, 31 benzer karar). Küçük fark ve çoklu karşılaştırma nedeniyle bu da yalnız izleme adayıdır.

## Doğrulama

- 22 Python yaşam döngüsü/model testi; ayrıca mevcut motor ve defter kontrolleri geçti. Tarih sızıntısı, ayrılmış test etiketlerinin katsayılara etkisizliği, yeni sezonun sabit modeli sessizce değiştirmemesi, eksik oran ve eksik kanıtta PAS, fiyat üzerinden beklenen değer, önceki kayıtların değişmezliği, PAS olasılıklarının saklanması ve sonuç işleme kontrol edildi.
- Sekiz JavaScript performans testi geçti; yeni ADAY sürümü eski modelden ayrı sayılıyor.
- JavaScript sözdizimi kontrolleri geçti.
- Mevcut üretim CSV anlık görüntüsüyle tam yerel güncelleme akışı geçti; 52 kaydın bütün mevcut alanları korundu. Eski 9 geçerli sonuç ve 43 test dışı kayıt kaybolmadı.
- Tarayıcıda Model Kontrolü, olasılık grubu seçimi, yeni sürümün boş başlangıcı ve Önceki motor filtresindeki 6/9 sonucu doğrulandı. Hata günlüğünde uygulama hatası görülmedi.

## Açık kapsam

Sakatlık, ceza, kadro ve gerçek xG entegrasyonu için veri hesabı/erişimi henüz sağlanmadı; bu alanların kullanıldığı iddia edilmiyor. Geçmiş oranların kayıt saati bilinmiyor. Maç dinlenme/yoğunluk verisi yalnız kapsanan ligleri içerir. Gerçek para ile performans doğrulanmış değildir. Yeni sürümün canlı sonuçları ayrıca birikmelidir.

Canlı yayın, kaynak dosyalarının karşılaştırılması ve GitHub güncelleme görevinin başarılı tamamlanmasıyla ayrıca doğrulanır.

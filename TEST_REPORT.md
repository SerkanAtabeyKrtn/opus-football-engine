# OPUS V1.6 doğrulama raporu

4 Eylül 2026. Dinamik sakatlık / kadro / geçmiş xG bağlantıları.

## Yerel doğrulama

- Beş ligde 15 Understat sezon kaynağı başarıyla okundu. Tarih, takımlar ve skor birlikte doğrulanarak 3.590 geçmiş maç xG ile eşleşti.
- 32 Python testi ve 8 JavaScript performans testi geçti. xG tarih sızıntısı, yanlış/çift takım eşleşmesi, kaynak kökeni, eski önbellek, eksik kaynağın bilinmiyor kalması, kesin ilk 11 için 11 farklı başlangıç oyuncusu, ilk gözlemin değişmezliği, istek önceliği ve başlama sonrası kayıt engeli kapsanır. Birim testleri dış kaynak isteği yapmaz.
- Eğitim 6.797, yöntem seçimi 1.728, bağımsız kontrol 1.062 maç. Seçim sonucunda maç sonucu ve KG modelleri geçmiş xG kullanıyor; 2,5 gol modeli xG'siz yöntemi seçti. Son kontrol etiketleri katsayı veya yöntem seçiminde kullanılmadı.

| Grup | V1.5 isabet | V1.6 isabet | V1.5 Brier | V1.6 Brier |
|---|---:|---:|---:|---:|
| Maç sonucu | %50,9 | %51,4 | 0,200163 | 0,200578 |
| 2,5 gol | %58,4 | %58,4 | 0,241263 | 0,241263 |
| Karşılıklı gol | %56,1 | %56,1 | 0,243506 | 0,243694 |

Daha düşük Brier daha iyidir. xG, bu bağımsız örneklemde V1.5'e göre olasılık hatasını iyileştirmedi; isabet ve olasılık hatası farklı ölçümlerdir. Bağlantının kurulması veya daha fazla özellik, daha başarılı model anlamına gelmez. İlk ham motora göre üç grupta da hata düşüktür; genel piyasa üstünlüğü veya kârlılık kanıtı yoktur. Lig/pazar kurallarını yalnız La Liga 2 / 2,5 Üst geçiyor.

## Kapsam

Oyuncu durumlarının ücretsiz kaynağı Premier League ile sınırlıdır. Diğer ligler için sakatlık verisi uydurulmaz. Kadro ve kesin ilk 11 kapsamı kaynağın yayımlamasına / erişimine bağlıdır. Bu değişkenlerin sayısal tahmin etkisi için maç öncesi arşiv biriktirilir; etkileri eğitilmiş gibi gösterilmez. Güncel haber saati ile indirme saati ayrıdır.

GitHub Actions 33873607982 sunucu denemesi başarıyla tamamlandı; Understat, FPL ve ESPN'den gerçek veri alındı. İlk soğuk indirmede istek sınırı nedeniyle eksik kalan kadrolar için tüm lig fikstürlerini önceleyen, ardından yaklaşan maçın kesin ilk 11 ve takım listelerini alan sıra eklendi. Geçerli önbellek istek bütçesinden düşmez. Canlı yayın sonuçları dağıtım sırasında ayrıca doğrulanır.

# OPUS V1.6

Maç öncesi olasılık motoru ve değişmez test kaydı. [Canlı site](https://serkanatabeykrtn.github.io/opus-football-engine/).

## Dinamik ek veriler

- Understat: Premier League, Bundesliga, Serie A, La Liga ve Ligue 1 için tamamlanmış maçların gerçek xG verisi. 2024, 2025 ve 2026 başlangıçlı sezonlar; son sekiz lig maçındaki üretilen/verilen xG. Başka bir ligin xG’si doldurulmaz.
- Premier League / FPL: Premier League oyuncu durumları, sakat/şüpheli/cezalı/kullanılamayan oyuncular ve takım oyuncu listesi. Rapor tarihi ve indirme zamanı ayrı tutulur. Boş veya başarısız kaynak, “eksik oyuncu yok” anlamına gelmez.
- ESPN: eşleşen fikstürlerde takım oyuncu listeleri; maçın son 90 dakikasında yayımlanmışsa kesin ilk 11. İki takım ve başlama saati birlikte eşleşmelidir. Tam 11 farklı başlangıç oyuncusu olmadan kadro kesinleşmiş sayılmaz.

Bağlantılar anahtar istemeyen genel erişim noktalarını kullanır; ücretli abonelik veya kullanıcı anahtarı eklenmedi. Kaynak kapsamı ve erişimi değişebilir. “Model Kontrolü → Dinamik veri bağlantıları” her ligde kullanılabilir maç sayısını ve kaynakların gerçek son indirme zamanını gösterir. Takım listesi maçın ilk 11’i değildir. Sakatlık kapsamı Premier League ile sınırlıdır; diğer liglerde bilinmiyor olarak kalır.

## Modelde kullanım

xG içeren ve içermeyen modeller aynı Ocak–Mart 2026 yöntem seçimi maçlarında karşılaştırılır. Eğitim 1 Ocak 2026 öncesi, bağımsız değerlendirme Nisan–Haziran 2026'dır. Geçmiş xG yalnız maçtan önceki tamamlanmış maçlardan gelir; maçın kendi xG'si ve gelecekteki sonuçlar özellik olamaz. Takım adları açık eşleme kurallarıyla eşlenir; tarih, iki takım ve gerçek skor uyuşmadığında xG bağlanmaz.

Oyuncu durumları ve kadrolar zaman damgalı ek analiz ve ileriye dönük araştırma verisidir. Geçmiş maç öncesi arşivi bulunmadığı için sakat oyuncu sayısından rastgele olasılık indirimi yapılmaz. Bu sayısal etkinin doğrulandığı iddia edilmez. xG eklemek de otomatik başarı artışı sağlamaz; gerçek ölçümler ekranda görünür.

ADAY/PAS koşulları korunur: yeterli takım geçmişi, lig/pazar değerlendirmesi, kullanılabilir referans oran ve pozitif hesaplanan değer. Mevcut ilk seçilmiş karar değiştirilmez. Her model sürümünün yedi olasılığı PAS dahil ayrı kilitlenir. `context-ledger.json` ilk ek veri gözlemini korur; son maç öncesi gözlem başlama saatinden sonra değiştirilmez. V1.6, V1.5 ve önceki sürümler başarı ekranında ayrı izlenir.

## Güncelleme

GitHub görevi yaklaşık 30 dakikada bir çalışır; kuyruk gecikmesi olabilir. Fikstür ve FPL 30 dakika, sonuç CSV'leri 2 saat, takım listeleri 24 saat, güncel sezon xG 6 saat aralıkla yeniden indirilir. Biten sezon xG verisi 30 gün önbellekte tutulur. Her çalışmada en fazla 100 ek kaynak isteği ve 4 dakika indirme süresi ayrılır; kalan kaynaklar sonraki çalışmalarda tamamlanır. 401/403/429 yanıtlarında aynı kaynak grubu o çalışmada tekrar denenmez. Eski önbellek yeni indirilmiş gibi sunulmaz. Kaynak hatası son iyi veriyi silmez.

```text
python -m pip install -r requirements.txt
python -m unittest discover -s tests -p "test_*.py" -v
node tests/test_performance.js
python app/update.py
python app/server.py
```

Windows: START_OPUS.bat veya UPDATE_ONLY.bat. Ekran beş dakikada bir kayıtlı veriyi yeniden okur. Yalnız başlamamış maçlara yeni analiz kaydedilir. Başarı; maç öncesinde saklanan ilk tahmin ile doğrulanmış sonuçtan hesaplanır. Kart, korner ve ilk yarı pazarları yoktur; KG piyasa oranı mevcut CSV'de bulunmaz.

Kaynaklar: [Football-Data](https://www.football-data.co.uk/matches.php), [Understat](https://understat.com/), [FPL istatistik açıklaması](https://www.premierleague.com/en/news/2176606), [ESPN](https://www.espn.com/soccer/).

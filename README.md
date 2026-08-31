# OPUS Football Probability Engine V1.1

## Neyi düzeltti?
V1 tarayıcı içinden football-data.co.uk dosyalarına `fetch()` yapıyordu. Bu CORS/ağ politikaları nedeniyle güvenilir değildi. V1.1'de tarayıcı dış veri kaynağına **hiç bağlanmaz**. Python veri katmanı CSV'leri sunucu tarafından indirir, doğrular, cache'e yazar ve `data/dashboard.json` üretir. Arayüz yalnızca aynı kaynaktaki JSON'u okur.

## Yerel kullanım
Windows'ta `START_OPUS.bat` dosyasına çift tıklayın. Veri güncellenir, ardından `http://127.0.0.1:8765` açılır. Python 3 gerekir; ek paket gerekmez.

## Tam otomatik ücretsiz bulut modu
Proje GitHub deposuna konduğunda `.github/workflows/update.yml` her gün ve hafta sonu ek bir kez otomatik çalışır. `app/update.py` veriyi çeker, yeni maç tahminlerini kilitli forward-test defterine yazar, sonuçlanan maçları kapatır ve Lig×Pazar matrisini günceller. GitHub Pages `index.html` + `data/dashboard.json` yayınlayabilir.

GitHub Pages ayarı: Settings → Pages → Deploy from branch → `main` / root.

## Bilimsel korumalar
- Data leakage engeli: maçın tahmin tarihinde yalnızca daha eski sonuçlar kullanılır.
- Zaman ağırlığı + shrinkage + ev/deplasman hücum-savunma güçleri.
- Poisson skor dağılımı.
- Piyasa oranları varsa de-vig benchmark.
- GÜVENLİ / DENGELİ / AGRESİF / PAS.
- Brier + log-loss + kalibrasyon + örneklem tabanlı Lig×Pazar matrisi.
- Forward-test tahmini oluşturulduktan sonra tahmin/olasılık/edge alanları değiştirilemez; sadece sonuç alanları eklenir.
- İndirme başarısız olursa son başarılı cache korunur. Veri yoksa tahmin uydurulmaz.

## Veri kaynağı
Football-Data.co.uk sezon CSV'leri ve haftalık fixtures.csv. Tarayıcı scraping'i yoktur.

## Test
`python tests/test_engine.py`
`python tests/test_ledger.py`

## Not
Model istatistiksel araştırma ve olasılık değerlendirmesi içindir; kazanç garantisi vermez.

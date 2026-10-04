# Transkript

> Windows için tamamen yerel çalışan, Türkçe odaklı masaüstü transkripsiyon uygulaması.  
> *Privacy-focused, offline Turkish transcription desktop application powered by faster-whisper.*

[![Platform](https://img.shields.io/badge/Platform-Windows_10_%2F_11-blue.svg)](#sistem-gereksinimleri)
[![Python](https://img.shields.io/badge/Python-3.10_%7C_3.11_%7C_3.12-blue.svg)](#development-setup)
[![Engine](https://img.shields.io/badge/Engine-faster--whisper-teal.svg)](#özellikler)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Transkript, danışma ve mülakat ses kayıtlarını bulut servislerine veya harici API'lere göndermeden, kullanıcının kendi Windows bilgisayarında güvenli ve yerel olarak metne dönüştürmek için geliştirilmiş bir masaüstü uygulamasıdır.

---

## Özellikler

- **Türkçe Odaklı Transkripsiyon:** `faster-whisper` (`small` modeli, `int8` CPU çıkarımı) ile Türkçe konuşmalarda optimize edilmiş yüksek kelime doğruluğu.
- **Tamamen Yerel / Çevrimdışı Çalışma:** Çevrimiçi API, bulut transkripsiyonu veya harici sunucu bağımlılığı yoktur. Model yüklendikten sonra internetsiz çalışabilir.
- **Geniş Format Desteği:** MP3, WAV ve M4A formatlarını doğrudan çözer.
- **Otomatik Donanım Profili (Hardware Profiler):** Bilgisayarın çekirdek ve RAM durumuna göre sistemi yormayacak şekilde dinamik `LOW` (2 thread), `BALANCED` (4 thread) veya `HIGH` (6-8 thread) CPU tahsisi yapar; arayüzün kilitlenmesini ve aşırı ısınmayı önler.
- **Aşamalı Metin Akışı (Incremental Streaming):** Uzun kayıtlarda konuşma işlendikçe transkript parça parça ekrana akar.
- **Kesintiye Karşı Kurtarma (Checkpoint / Recovery):** Uzun süreli görüşmelerde beklenmeyen sistem kapanmalarına karşı kısmi transkripti yerel diskte geçici olarak korur; başarılı işlem bitiminde bu veriyi otomatik olarak temizler.
- **Kullanıcı Tanımlı Özel Terimler (Custom Hotwords):** Kayıtta geçen kişi adları, kurumlar veya teknik klinik kavramlar (ör. üniversite isimleri, klinik terimler) kullanıcı tarafından isteğe bağlı olarak belirtilebilir.
- **Sessizlik Filtresi (Silero VAD):** Konuşma aralarındaki sessizliklerde modelin gereksiz beklemesini veya tekrar döngülerine girmesini engeller.
- **Gizlilik Odaklı Tanılama Logları:** Teşhis loglarına ses dosyası dalga formu, transkript metni veya kullanıcı tanımlı özel terimler kesinlikle yazılmaz.
- **Sinematik ve Dokunsal Arayüz:** Sıfır harici CDN, sıfır uzak font ve sıfır ağır framework bağımlılığına sahip, Microsoft Edge WebView2 üzerinde çalışan orijinal karanlık ses iş istasyonu arayüzü.

---

## Nasıl Çalışır?

1. **Sesini seç:** MP3, WAV veya M4A uzantılı ses kaydını uygulamaya yükle.
2. **İstersen özel terimler ekle:** Kişi, kurum veya yanlış anlaşılabilecek özel kelimeleri virgülle ayırarak belirt.
3. **Cihazında metne dönüştür:** Türkçe konuşma modeli kaydı tamamen bilgisayarında işler, ilerlemeyi anlık olarak gösterir ve metni düzenlenebilir ekrana aktarır.

---

## Gizlilik İlkeleri ve Sınırları

- **Yerel İşlem:** Ses kayıtları ve oluşturulan transkriptler bilgisayarınızdan dışarı çıkmaz.
- **Bulut / API Yok:** Uygulama, konuşma tanıma için hiçbir harici bulut servisine, üçüncü taraf yapay zekâ sunucusuna veya çevrimiçi API'ye bağlanmaz.
- **Telemetri Yok:** Kullanıcı hareketlerini, kullanım sürelerini veya dosya isimlerini toplayan hiçbir analitik/telemetri kodu bulunmaz.
- **Tanılama Gizliliği:** Hata durumlarında oluşturulan teknik log dosyalarına ses içeriği veya transkript metinleri asla kaydedilmez.
- **Geçici Kurtarma:** Uzun görüşmeler sırasında işlem yarıda kalırsa veri kaybını önlemek amacıyla `%LOCALAPPDATA%\Transkript\recovery\` dizininde geçici bir kurtarma metni tutulabilir. İşlem başarıyla (%100) tamamlandığında bu dosya otomatik olarak silinir.
- **Sorumluluk Sınırları:** Bu uygulama %100 saldırı geçirmez veya erişilmesi imkânsız bir kasa garantisi vermez; bilgisayarın fiziksel ve işletim sistemi düzeyindeki güvenliği kullanıcının sorumluluğundadır. Ses kaydı alırken ilgili kişilerin açık rızasını/onayını almak ve yürürlükteki kişisel veri/etik kurallarına uymak tamamen kullanıcının yükümlülüğündedir.

---

## Sistem Gereksinimleri

Transkript V0, Windows masaüstü ortamları için tasarlanmıştır.

- **İşletim Sistemi:** Windows 10 (64-bit) veya Windows 11
- **Çalışma Zamanı:** Microsoft Edge WebView2 Runtime (Modern Windows sürümlerinde yerleşik olarak mevcuttur)
- **İşlemci (CPU):** 4 veya daha fazla çekirdekli 64-bit x86-64 işlemci (AVX/AVX2 desteği önerilir)
- **Bellek (RAM):** Asgari 8 GB RAM (16 GB önerilir)
- **Disk Alanı:** Model ve bağımlılıklar için yaklaşık 1.5 - 2 GB boş disk alanı

> **Test Edilen Geliştirme Donanımı:**  
> Intel Core i5-10300H (4 fiziksel / 8 mantıksal çekirdek, 2.50 GHz), 16 GB DDR4 RAM, Windows 11.  
> Bu donanım üzerinde sistem otomatik olarak `BALANCED` (4 CPU threads) profili seçmiş, 64 dakikalık gerçek ses kaydını yaklaşık 18.7 dakikada (RTF 0.29 / 3.4 kat hızında) başarıyla tamamlamıştır.

---

## Development Setup

Geliştirici ortamında kaynak koddan çalıştırmak için:

```powershell
# 1. Depoyu klonlayın
git clone https://github.com/kullanici-adi/transkript.git
cd transkript

# 2. Python sanal ortamını oluşturun ve etkinleştirin
python -m venv .venv
.venv\Scripts\activate

# 3. Temel çalışma zamanı bağımlılıklarını yükleyin
pip install -r requirements.txt

# 4. (İsteğe bağlı) Test ve kıyaslama araçlarını yüklemek isterseniz:
pip install -r requirements-dev.txt

# 5. Uygulamayı başlatın
python app.py
```

Alternatif olarak, Windows üzerinde doğrudan `baslat.bat` dosyasına çift tıklayarak da başlatabilirsiniz.

---

## Testler

Depo, özel veya hassas kişisel veriler içermeyen sentetik test senaryolarıyla birlikte gelir:

```powershell
# Temel motor ve birim testleri:
python tests/test_domain_vocabulary.py
python tests/test_hardware_profiler.py
python tests/test_api_flow.py
python tests/test_transcribe.py
python tests/test_failure_recovery.py

# Arayüz ve hareket sistemi doğrulaması:
python tests/test_redesign_ui.py
python tests/test_full_ui_interaction.py
```

---

## Kıyaslama ve Doğruluk (Benchmarks)

Uygulamanın motor performansı geliştirme sürecinde kontrollü koşullarda ölçülmüştür:

| Test Türü | Veri Kaynağı | Model / Ayar | İşlem Hızı (RTF) | Ölçülen Değer |
| :--- | :--- | :--- | :--- | :--- |
| **Sentetik PDR Diyaloğu** | 107 sn edge-tts sentetik ses | `small` (int8, 4 threads) | ~0.29 (3.4x hız) | Hatasız tam metin |
| **Klinik PDR Terimleri** | 68 sn sentetik terim kaydı | `small` (int8, 4 threads) | ~0.35 (2.8x hız) | %1.41 WER (%98.59 doğruluk) |
| **Uzun Kayıt Deneyi** | 64 dk Türkçe konuşma | `small` (int8, 4 threads) | 0.2877 (3.48x hız) | %6.86 WER (~%93.14 kelime doğruluğu)* |

*\*Önemli Not: Uzun kayıt kıyaslamasındaki referans metin insan onaylı mutlak doğru (ground truth) olmayıp bağımsız bir yapay zekâ modeli (Google AI Studio) çıktısıdır. Bu metrikler genel bir doğruluk garantisi olmayıp, geliştirme donanımındaki göreceli motor başarımını göstermektedir. Özel konuşma kayıtları gizlilik nedeniyle depoda paylaşılmamaktadır.*

---

## Proje Durumu

**Transkript V0 (Erken Sürüm / Aktif Geliştirme)**

Bu yazılım erken aşama bir masaüstü yardımcı aracıdır; klinik tanı koyma aracı, onaylanmış tıbbi cihaz veya resmi sağlık yazılımı değildir. Üretilen transkriptlerin doğruluğu kayıt kalitesine, arka plan gürültüsüne, konuşmacı aksanına ve mesafe durumuna göre değişebilir. Kullanıcının metni inceleyerek doğrulaması önerilir.

---

## Etik ve Yasal Kullanım

- Görüşme kaydı almadan önce tüm tarafların yürürlükteki mevzuata (KVKK vb.) uygun şekilde bilgilendirilmesi ve gerekli açık rızalarının alınması kullanıcının şahsi sorumluluğundadır.
- Transkript uygulamasının üçüncü şahısların izinsiz dinlenmesi veya rızası hilafına kaydedilen seslerin işlenmesi amacıyla kullanılması uygun değildir.

---

## Lisans

Bu proje MIT License altında lisanslanmaktadır.

Ayrıntılar için `LICENSE` dosyasına bakın.

Üçüncü taraf bağımlılıkların lisans detayları için [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) dosyasına başvurabilirsiniz.


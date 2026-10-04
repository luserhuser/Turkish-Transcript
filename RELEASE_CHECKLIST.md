# Transkript — Sürüm Hazırlık ve Dağıtım Kontrol Listesi (Release Checklist)

Bu liste, Transkript uygulamasının genel GitHub yayını ve Windows kurulum paketi (Installer) dağıtımı öncesinde doğrulanması gereken adımları içerir.

---

## 1. Kod Tabanı & Gizlilik Güvenliği (Release Freeze & Privacy)

- [x] **Tüm Regresyon Testleri Başarılı:**
  - `python tests/test_domain_vocabulary.py` (14/14 PASS)
  - `python tests/test_hardware_profiler.py` (CASE A-H PASS)
  - `python tests/test_api_flow.py` (PASS)
  - `python tests/test_transcribe.py` (PASS)
  - `python tests/test_failure_recovery.py` (PASS)
  - `python tests/test_redesign_ui.py` (ALL_PASS)
  - `python tests/test_full_ui_interaction.py` (ALL_PASS)
- [x] **Özel Ses ve Transkript Denetimi:**
  - Depoda hiçbir gerçek danışma kaydı (`.mp3`, `.wav`, vb.) bulunmuyor.
  - Sadece sentetik TTS test sesleri (`sample_15s.mp3`, `sample_counseling_2m.mp3`, `sample_pdr_clinical_terms.mp3`) dahil edilmiş durumda.
  - Gerçek kayıtlara ait benchmark transkriptleri (`output_*.txt`, `reference_transcript*.txt`) `.gitignore` ile hariç tutulmuş.
- [x] **Hassas Bilgi ve Gizli Anahtar Taraması (Secret Scan):**
  - Depoda API anahtarı, token, şifre, özel anahtar veya `.env` dosyası bulunmuyor.
  - Kodlarda ve dökümanlarda geliştiriciye özel sabit yerel dosya yolları (`C:\Users\...`) bulunmuyor.

---

## 2. Dökümantasyon & Lisanslama

- [x] **README.md Tamamlandı:**
  - Özellikler, kurulum, mimari, gizlilik sınırları ve etik kullanım açıklandı.
  - Gerçekçi olmayan veya abartılı iddialar ("%100 güvenli", "asla erişilemez") yer almıyor.
- [x] **Üçüncü Taraf Bildirimleri:** `THIRD_PARTY_NOTICES.md` incelendi ve doğrulandı.
- [x] **Transkript Proje Lisansı Seçildi:**
  - Kullanıcı tarafından standart MIT Lisansı seçildi ve kök dizinde `LICENSE` dosyası oluşturuldu.


---

## 3. Temiz Kurulum Testi (Clean Environment Verification)

- [ ] **Temiz Sanal Ortamda Doğrulama:**
  - Yeni bir dizinde `git clone` simülasyonu yapıldı.
  - `python -m venv .venv` oluşturuldu ve `pip install -r requirements.txt` çalıştırıldı.
  - `python app.py` ile uygulamanın hatasız açıldığı doğrulandı.

---

## 4. Paketleme ve Installer Hazırlığı (Build & Package)

- [ ] **PyInstaller Spec Dosyası Oluşturuldu:**
  - `pywebview`, `ctranslate2`, `faster_whisper` ve CTranslate2 DLL bağımlılıkları spec dosyasına dahil edildi.
  - Gömülü `small` Whisper model dosyaları paket klasör yapısına eklendi.
- [ ] **PyInstaller Derlemesi Alındı:**
  - Tek klasörlü veya bağımsız binary derlemesi başarıyla tamamlandı.
- [ ] **Inno Setup Installer Betiği Hazırlandı:**
  - `Transkript-Setup.exe` derleyicisi yapılandırıldı.
  - Başlat menüsü kısayolu, masaüstü simgesi ve temiz uninstaller tanımlandı.
- [ ] **Temiz Windows Cihazında Test Edildi:**
  - Python veya geliştirici araçları kurulu olmayan temiz bir Windows 10/11 ortamında kurulum yapıldı.
  - Kurulumun sorunsuz tamamlandığı ve uygulamanın internetsiz çevrimdışı transkripsiyon yaptığı doğrulandı.

---

## 5. GitHub Yayını & Sürüm Çıkışı (GitHub Release)

- [ ] **GitHub Deposu Oluşturuldu:**
  - Gizlilik ve `.gitignore` doğrulaması sonrası ilk commit atıldı.
  - Depo genel kullanıma (Public) açıldı.
- [ ] **GitHub Sürümü (Release v0.1.0) Oluşturuldu:**
  - Sürüm notları eklendi.
  - Derlenen `Transkript-Setup.exe` kurulum dosyası release varlıklarına (Assets) eklendi.
- [ ] **Sağlama Toplamları (Checksums) Üretildi:**
  - `Transkript-Setup.exe` için SHA-256 hash değeri üretilip release notlarına eklendi:
    ```powershell
    Get-FileHash -Algorithm SHA256 Transkript-Setup.exe
    ```

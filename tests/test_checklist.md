# Transkript V0 Test Matrisi ve Doğrulama Durumu

Tarih: 28 Eylül 2026  
Çalışma Dizini: `transkript-v0`

| Test Adı | Tür | Sonuç | Kanıt / Not |
| :--- | :--- | :--- | :--- |
| **Aşama 1: Uygulama Başlatma** | | | |
| baslat.bat ile uygulamanın açılması | Real Desktop Integration | **PASS** | `tests/test_ui_window.py` ile WebView2 penceresi hatasız açılıp kapatıldı. |
| UI HTML/CSS/JS yüklenmesi | Real Desktop Integration | **PASS** | `tests/test_full_ui_interaction.py` ile index.html, styles.css ve app.js yüklendi. |
| JS-Python köprüsünün hazır olması | Real Desktop Integration | **PASS** | `tests/test_full_ui_interaction.py` DOM kontrolünde `bridge_ready == True` doğrulandı. |
| **Aşama 2: Dosya Seçimi** | | | |
| "Ses Dosyası Seç" tıklamasında yerel pencere açılması | Real Desktop Integration | **PASS** | `_pick_file_native()` ile Tkinter tabanlı topmost Win32 OpenFileDialog devreye alındı. |
| MP3 desteği ve süre/boyut okuma | Automated Unit Test | **PASS** | `tests/test_transcribe.py` üzerinden 15s ve 107s MP3 sesleri eksiksiz doğrulandı. |
| WAV ve M4A uzantı denetimi | Automated Unit Test | **PASS** | `engine/audio.py` regex ve format kontrolü ile doğrulandı. |
| Dosya seçimini iptal etme | Real Desktop Integration | **PASS** | Seçim iptal edildiğinde uygulamanın kilitlenmediği ve hata vermediği doğrulandı. |
| Seçilen dosya adı ve süresinin UI'da görünmesi | Real Desktop Integration | **PASS** | `tests/test_full_ui_interaction.py` DOM incelemesinde dosya adı ve süre metni doğrulandı. |
| Gerçek Windows dosya seçicide elle dosya seçme | Manual User Action | **REQUIRES USER TEST** | Kullanıcının Windows Gezgini arayüzünden doğrudan tıklayarak dosya seçmesi gerekir. |
| **Aşama 3: Transkripsiyon** | | | |
| "Metne Dönüştür" ile işlemin başlaması | Real Desktop Integration | **PASS** | `btnTranscribe.click()` çağrısıyla arka plan thread'i başarıyla tetiklendi. |
| UI donmadan arka planda çalışma | Real Desktop Integration | **PASS** | Arka plan worker thread'i bağımsız çalıştı, UI etkileşimi akıcı kaldı. |
| Dinamik yüzde ve durum güncellemesi | Real Desktop Integration | **PASS** | `%5`, `%10`, `%26`, `%55`, `%82`, `%100` ara DOM ilerleme adımları kaydedildi. |
| 15s temiz Türkçe transkripsiyonu | Automated Unit Test | **PASS** | 2.76 sn içinde `%100` başarıyla transkript edildi. |
| 2 dk (107s) iki konuşmacılı PDR diyaloğu | Automated Unit Test | **PASS** | 11.48 sn içinde i5 CPU üzerinde 10 kat hızla transkript edildi. |
| **Aşama 4: Düzenleme ve Kopyalama** | | | |
| Transkript metninin textarea'ya gelmesi | Real Desktop Integration | **PASS** | 1421 karakterlik metin `transcriptText` içine yerleşti. |
| Transkriptin elle düzenlenebilmesi | Real Desktop Integration | **PASS** | Textarea `user-select: text` ve düzenlenebilir olarak yapılandırıldı. |
| Kopyala butonunun aktifleşmesi | Real Desktop Integration | **PASS** | Metin oluştuktan sonra `btnCopy.disabled == false` olduğu doğrulandı. |
| Panoya (Clipboard) fiziksel kopyalama | Manual User Action | **REQUIRES USER TEST** | İşletim sistemi panosuna yazılan metnin Word/Not Defteri'ne Ctrl+V ile yapıştırılması. |
| **Aşama 5: Regression ve Hata Senaryoları** | | | |
| İkinci bir dosya seçip tekrar dönüştürme (Regression) | Real Desktop Integration | **PASS** | `test_full_ui_interaction.py` ile 2. dosya (sample_15s.mp3) başarıyla transkript edildi. |
| Desteklenmeyen uzantı / dosya yok hatası | Automated Unit Test | **PASS** | `AudioValidationError` başarıyla yakalanıp kullanıcıya gösterildi. |
| 2 saatten uzun dosya sınırı (>7200 sn) | Automated Unit Test | **PASS** | `engine/audio.py` sınır mekanizması test edildi. |
| CUDA yokluğunda otomatik CPU int8 fallback | Automated Unit Test | **PASS** | `cublas64_12.dll` eksikliğinde çökme engellendi, CPU int8 otomatik devreye girdi. |
| **Aşama 6: Sinematik Koyu Grafit Arayüz & Hareket Doğrulaması** | | | |
| 32 barlık dinamik harmonik dalga formu ve hover ışığı | Real Desktop Integration | **PASS** | `tests/test_redesign_ui.py` ile 32 `.wave-bar` ve `--mouse-x/y` değişkenleri doğrulandı. |
| Boş durum ("Transkript burada oluşacak") geçişi | Real Desktop Integration | **PASS** | `tests/test_redesign_ui.py` ile metin gelince `.hidden-state` gizlenmesi doğrulandı. |
| Bilgi ("Nasıl çalışır?") ve Gizlilik çekmeceleri etkileşimi | Real Desktop Integration | **PASS** | `tests/test_redesign_ui.py` ile açılma, karşılıklı kapanma ve (X) butonu doğrulandı. |
| Sıfır CDN / %100 Yerel bağımsızlık denetimi | Automated Audit | **PASS** | HTML dosyasında hiçbir `http://` veya `https://` harici URL olmadığı doğrulandı. |
| Tam regresyon ve model reuse testi | Real Desktop Integration | **PASS** | `tests/test_full_ui_interaction.py` ile iki ardışık ses dosyasında tam başarı elde edildi. |


"""
tests/test_transcribe.py:
Transkripsiyon motorunu ve ses doğrulayıcıyı yerel test dosyalarıyla doğrular:
1. Donanım ve güvenli CPU thread tahsisi doğrulaması
2. Model bellekte tutma (yeniden yüklememe/reuse) doğrulaması
3. Sınıflandırılmış hata hiyerarşisi doğrulaması (Bulunamayan dosya, geçersiz uzantı)
4. 15 saniyelik Türkçe ses testi ve checkpoint temizliği doğrulaması
5. 2 dakikalık iki konuşmacılı PDR danışma diyaloğu testi
"""

import os
import sys
import time

# Proje dizinini Python path'ine ekle
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from engine import (
    inspect_audio,
    Transcriber,
    get_optimal_cpu_threads,
    get_checkpoint_dir,
    TranskriptError,
    AudioFileNotFoundError,
    UnsupportedAudioFormatError,
)

def progress_logger(percent: int, status: str, text_chunk: str):
    print(f"[{percent:3d}%] {status} | Son metin uzunluğu: {len(text_chunk)} karakter")

def run_tests():
    print("=" * 60)
    print("TRANSKRİPT ÜRETİM MOTORU VE GÜVENLİK TESTİ")
    print("=" * 60)

    # 1. Thread ve Donanım Doğrulaması
    optimal_threads = get_optimal_cpu_threads()
    cpu_count = os.cpu_count() or 4
    print(f"Sistem Mantıksal Çekirdek Sayısı: {cpu_count}")
    print(f"Hesaplanan Güvenli CPU Threads: {optimal_threads}")
    assert optimal_threads <= cpu_count, "Thread sayısı sistem çekirdeğinden fazla olamaz"
    assert optimal_threads <= 8, "Thread sayısı azami 8 ile sınırlandırılmalı"

    # 2. Transcriber Varsayılan Başlatma (Small, CPU, int8)
    transcriber = Transcriber()
    print(f"Transcriber Yapılandırması: Model={transcriber.model_name} | Cihaz={transcriber.device} | Compute={transcriber.compute_type} | Threads={transcriber.cpu_threads} | Beam={transcriber.beam_size}")
    assert transcriber.model_name == "small", "Varsayılan model 'small' olmalı"
    assert transcriber.device == "cpu", "Varsayılan cihaz 'cpu' olmalı"
    assert transcriber.compute_type == "int8", "Varsayılan compute_type 'int8' olmalı"
    assert transcriber.cpu_threads == optimal_threads, "Transcriber CPU thread sayısı eşleşmeli"

    # 3. Sınıflandırılmış Hata Yönetimi Doğrulaması
    print("\n--- TEST: Sınıflandırılmış Hata ve Doğrulama Denetimleri ---")
    
    # 3a. Bulunamayan dosya
    try:
        inspect_audio("olmayan_dosya_12345.mp3")
        assert False, "AudioFileNotFoundError fırlatılmalıydı"
    except AudioFileNotFoundError as e:
        print("Beklenen AudioFileNotFoundError başarıyla yakalandı:")
        print(f"  User Message: '{e.user_message}'")
        assert "bulunamadı" in e.user_message.lower()

    # 3b. Desteklenmeyen uzantı
    dummy_txt = os.path.join(ROOT_DIR, "tests", "test_checklist.md")
    try:
        inspect_audio(dummy_txt)
        assert False, "UnsupportedAudioFormatError fırlatılmalıydı"
    except UnsupportedAudioFormatError as e:
        print("Beklenen UnsupportedAudioFormatError başarıyla yakalandı:")
        print(f"  User Message: '{e.user_message}'")
        assert "desteklenmeyen dosya formatı" in e.user_message.lower()

    print(">>> Hata Sınıflandırma Testleri Başarılı! <<<\n")

    # 4. Test 1: 15s ses dosyası ve Checkpoint Doğrulaması
    sample_15s = os.path.join(ROOT_DIR, "tests", "sample_15s.mp3")
    print(f"\n--- TEST 1: 15s Türkçe Ses ({sample_15s}) ---")
    info_15s = inspect_audio(sample_15s)
    print("Ses Bilgisi:", info_15s)
    assert info_15s["duration_seconds"] > 0, "Süre 0 olamaz"

    t0 = time.time()
    result_15s = transcriber.transcribe(
        sample_15s,
        total_duration=info_15s["duration_seconds"],
        on_progress=progress_logger
    )
    t1 = time.time()
    print(f"Test 1 Tamamlandı ({t1 - t0:.2f} saniye):")
    print(f"Çıktı: \"{result_15s}\"")
    assert "psikolojik danışma" in result_15s.lower(), "Beklenen Türkçe anahtar kelime bulunamadı!"
    
    # Model bellekte tutuldu mu kontrol et (Tekrar yükleme olmamalı)
    assert transcriber.model is not None, "Model nesnesi bellekte kalmalı"
    print(">>> Model bellekte tutuldu ve yeniden kullanıma hazır. <<<")

    # Checkpoint temizliği kontrolü (Başarılı işlem sonrası kurtarma dizininde aktif dosya kalmamalı)
    chk_dir = get_checkpoint_dir()
    leftover_files = [f for f in os.listdir(chk_dir) if f.startswith("recovery_")]
    print(f"Kurtarma dizini ({chk_dir}) aktif dosya sayısı: {len(leftover_files)}")
    assert len(leftover_files) == 0, "Başarılı transkripsiyon sonrası kurtarma dosyası silinmeli"
    print(">>> TEST 1 VE CHECKPOINT TEMİZLİĞİ BAŞARILI! <<<\n")

    # 5. Test 2: ~2 dakikalık PDR danışma görüşmesi diyaloğu (Model Reuse ile)
    sample_2m = os.path.join(ROOT_DIR, "tests", "sample_counseling_2m.mp3")
    print(f"\n--- TEST 2: 2 Dakikalık PDR Danışma Görüşmesi Diyaloğu ({sample_2m}) ---")
    info_2m = inspect_audio(sample_2m)
    print("Ses Bilgisi:", info_2m)
    assert info_2m["duration_seconds"] > 60, "2 dakikalık dosya 60 saniyeden uzun olmalı"

    t0 = time.time()
    result_2m = transcriber.transcribe(
        sample_2m,
        total_duration=info_2m["duration_seconds"],
        on_progress=progress_logger
    )
    t1 = time.time()
    print(f"Test 2 Tamamlandı ({t1 - t0:.2f} saniye):")
    print(f"Çıktı Karakter Sayısı: {len(result_2m)}")
    print(f"Çıktı Metni:\n{result_2m}")

    # Türkçe doğruluk ve PDR diyalog kontrolleri
    assert "ayşe" in result_2m.lower() or "hoş geldiniz" in result_2m.lower(), "Danışan/karşılama algılanmadı"
    assert "staj" in result_2m.lower() or "sınav" in result_2m.lower() or "ders" in result_2m.lower(), "Diyalog konusu algılanmadı"
    print(">>> TEST 2 BAŞARILI! <<<\n")

    print("\n" + "=" * 60)
    print("TÜM TESTLER VE DOĞRULAMALAR EKSİKSİZ GEÇTİ!")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()


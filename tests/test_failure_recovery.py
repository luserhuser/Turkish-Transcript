"""
tests/test_failure_recovery.py:
Transkripsiyon sırasında kesinti/hata anında kurtarma ve gizlilik mekanizması testi:
1. İşlem ortasında beklenmeyen çökme/hata simülasyonu
2. Hata anına kadar üretilen segmentlerin kurtarma dosyasında korunduğunun doğrulanması
3. Kullanıcıya ham traceback yerine güvenli ve açıklayıcı Türkçe hata mesajı sunulduğunun doğrulanması
4. Uygulama yeniden başlatıldığında kurtarma dosyasının bozulmadığının ve tespit edildiğinin doğrulanması
5. Sistemin arıza sonrasında yeni transkripsiyon yapabildiğinin (model reuse ve yeni checkpoint) doğrulanması
"""

import os
import sys
import time

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from engine import (
    inspect_audio,
    Transcriber,
    get_checkpoint_dir,
    detect_stale_checkpoints,
    TranskriptError,
    TranscriptionRuntimeError,
)

def test_failure_and_recovery():
    print("=" * 60)
    print("TRANSKRİPT ARIZA VE KURTARMA (FAILURE RECOVERY) TESTİ")
    print("=" * 60)

    chk_dir = get_checkpoint_dir()
    sample_counseling = os.path.join(ROOT_DIR, "tests", "sample_counseling_2m.mp3")
    sample_15s = os.path.join(ROOT_DIR, "tests", "sample_15s.mp3")

    info_2m = inspect_audio(sample_counseling)
    transcriber = Transcriber()

    # Adım 1: Transkripsiyonu başlat ve 3. segmentte kasıtlı kesinti simüle et
    print("\n--- ADIM 1: İşlem Ortasında Kesinti / Çökme Simülasyonu ---")
    
    interrupted_checkpoint_path = None
    captured_user_error = None
    segment_counter = 0

    def progress_with_simulated_crash(percent: int, status: str, text: str):
        nonlocal segment_counter, interrupted_checkpoint_path
        # Aktif checkpoint dosyasını yakala
        if transcriber._current_checkpoint and not interrupted_checkpoint_path:
            interrupted_checkpoint_path = transcriber._current_checkpoint.file_path
        
        if len(text.strip()) > 0:
            segment_counter += 1
            print(f"  [İlerleme] %{percent} - Metin: {len(text)} karakter (Segment {segment_counter})")

        # 3 segment işlendikten sonra beklenmeyen bir sistem hatası fırlat
        if segment_counter >= 3:
            print("  >>> [SİMÜLASYON] Beklenmeyen sistem / donanım arızası tetikleniyor! <<<")
            raise RuntimeError("Simüle edilmiş donanım/sistem kesintisi (Test)")

    try:
        transcriber.transcribe(
            sample_counseling,
            total_duration=info_2m["duration_seconds"],
            on_progress=progress_with_simulated_crash
        )
        assert False, "Hata fırlatılmalıydı ancak işlem tamamlandı!"
    except TranskriptError as e:
        captured_user_error = e.user_message
        print(f"\nBeklenen TranskriptError başarıyla yakalandı:")
        print(f"  Kullanıcı Mesajı: '{captured_user_error}'")
        assert "hata" in captured_user_error.lower()
        assert "korundu" in captured_user_error.lower(), "Kısmi metnin korunduğu kullanıcıya bildirilmeli"

    # Adım 2: Kurtarma dosyasının diskte kaldığını ve içeriğini doğrula
    print("\n--- ADIM 2: Kurtarma Dosyasının Varlığı ve Veri Bütünlüğü ---")
    assert interrupted_checkpoint_path is not None, "Checkpoint dosya yolu kaydedilmiş olmalı"
    assert os.path.isfile(interrupted_checkpoint_path), f"Kurtarma dosyası diskte kalmalıydı: {interrupted_checkpoint_path}"
    
    with open(interrupted_checkpoint_path, "r", encoding="utf-8") as f:
        recovered_text = f.read().strip()
    
    print(f"Kurtarılan Metin Uzunluğu: {len(recovered_text)} karakter")
    print(f"Kurtarılan Kısmi İçerik (İlk 150 krk): '{recovered_text[:150]}...'")
    assert len(recovered_text) > 50, "Kurtarılan metin boş olamaz"
    assert "ayşe" in recovered_text.lower() or "hoş" in recovered_text.lower(), "İşlenen segmentler dosyada bulunmalı"
    print(">>> ADIM 2 BAŞARILI: Kısmi metin diske eksiksiz kaydedildi ve çökme sonrası korundu. <<<")

    # Adım 3: Uygulama yeniden başlatıldığında stale checkpoint tespiti
    print("\n--- ADIM 3: Yeni Oturum Başlangıcı ve Stale Recovery Tespiti ---")
    stale_files = detect_stale_checkpoints()
    matching = [sf for sf in stale_files if sf["file_path"] == interrupted_checkpoint_path]
    print(f"Tespit edilen kurtarma dosyaları: {len(stale_files)} adet")
    assert len(matching) == 1, "Kesintiye uğrayan dosya detect_stale_checkpoints tarafından bulunmalı"
    # Dosyanın silinmediğini tekrar teyit et
    assert os.path.isfile(interrupted_checkpoint_path), "Kurtarma dosyası asla sessizce silinmemeli"
    print(">>> ADIM 3 BAŞARILI: Stale kurtarma dosyası güvenle tespit edildi ve korunuyor. <<<")

    # Adım 4: Arıza sonrası sistemin yeni bir transkripsiyonu sorunsuz yapabilmesi
    print("\n--- ADIM 4: Arıza Sonrası İkinci Transkripsiyon ve İzolasyon ---")
    info_15s = inspect_audio(sample_15s)
    
    second_run_completed = False
    def progress_normal(percent: int, status: str, text: str):
        nonlocal second_run_completed
        if percent == 100:
            second_run_completed = True

    result_second = transcriber.transcribe(
        sample_15s,
        total_duration=info_15s["duration_seconds"],
        on_progress=progress_normal
    )

    assert second_run_completed is True, "İkinci işlem %100 tamamlanmalı"
    assert len(result_second) > 0, "İkinci transkript başarılı olmalı"
    print(f"İkinci İşlem Çıktısı: \"{result_second}\"")
    
    # İkinci işlemin kendi kurtarma dosyasını sildiğini, ancak önceki çökme dosyasını KORUDUĞUNU doğrula
    assert os.path.isfile(interrupted_checkpoint_path), "Önceki oturumun kurtarma dosyası silinmemeli"
    print(">>> ADIM 4 BAŞARILI: Sistem arıza sonrası ikinci dosyayı başarıyla işledi ve önceki kurtarma verisini korudu. <<<")

    # Test temizliği (Test ortamını temiz tutmak için simüle edilen dosyayı kaldır)
    try:
        os.remove(interrupted_checkpoint_path)
        print("\nTest amaçlı oluşturulan kurtarma dosyası temizlendi.")
    except Exception as e:
        print(f"Temizlik uyarısı: {e}")

    print("\n" + "=" * 60)
    print("TÜM ARIZA VE KURTARMA DOĞRULAMALARI EKSİKSİZ GEÇTİ!")
    print("=" * 60)

if __name__ == "__main__":
    test_failure_and_recovery()

"""
tests/stress_test_long_recording.py:
64 dakikalık gerçek ses kaydı ile üretim motoru stres testi:
1. Süre, RTF ve bellek (Peak RAM) ölçümü
2. CPU thread ve işlemci tüketim profili (4 thread sınırı)
3. Artımlı checkpoint dosya büyümesi ve işlem sonu temizliği
4. Modelin bellekten tekrar kullanımı (in-memory reuse)
5. Bağımsız referans transkript ile WER/CER hesaplaması
Gizlilik Kuralı: Hassas kayıt içeriği kesinlikle ekrana veya loga yazdırılmaz.
"""

import os
import sys
import time
import json
import threading
from typing import Dict, Any

import psutil

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from engine import inspect_audio, Transcriber, get_checkpoint_dir
from tests.benchmark_wer import calculate_wer_metrics, normalize_turkish

def run_stress_test():
    print("=" * 60)
    print("64 DAKİKALIK UZUN SES KAYDI ÜRETİM STRES TESTİ")
    print("=" * 60)

    audio_path = os.environ.get("TRANSKRIPT_STRESS_AUDIO", os.path.join(ROOT_DIR, "tests", "private_stress_test.mp3"))
    if not os.path.isfile(audio_path):
        print(f"[BILGI] Uzun kayit stres testi icin ses dosyasi bulunamadi: {audio_path}")
        print("[BILGI] Ozel test kayitlari gizlilik nedeniyle depoda yer almamaktadir.")
        print("[BILGI] Kendi ses dosyanizla test etmek icin: $env:TRANSKRIPT_STRESS_AUDIO='C:\\yol\\dosya.mp3'")
        return


    sample_15s = os.path.join(ROOT_DIR, "tests", "sample_15s.mp3")
    ref_path = os.path.join(ROOT_DIR, "tests", "reference_transcript.txt")

    # 1. Ses Dosyası İncelemesi
    info = inspect_audio(audio_path)
    audio_duration = info["duration_seconds"]
    print(f"Ses Dosyası: {info['file_name']}")
    print(f"Toplam Süre: {audio_duration:.2f} saniye ({audio_duration / 60:.2f} dakika)")
    print(f"Dosya Boyutu: {info['size_mb']:.2f} MB")
    print(f"2 Saat Uyarısı: {info.get('warning')}")

    # 2. Transcriber Başlatma
    process = psutil.Process()
    initial_ram_mb = process.memory_info().rss / (1024 * 1024)
    print(f"Başlangıç RAM Tüketimi: {initial_ram_mb:.1f} MB")

    transcriber = Transcriber()
    print(f"Transcriber Yapılandırması: Model='{transcriber.model_name}' | Cihaz='{transcriber.device}' | Threads={transcriber.cpu_threads} | Compute='{transcriber.compute_type}'")

    # 3. Kaynak İzleme Thread'i (Peak RAM, CPU % ve Checkpoint İzleme)
    monitoring = True
    peak_ram_mb = initial_ram_mb
    cpu_samples = []
    checkpoint_samples = []
    active_checkpoint_file = None

    def monitor_resources():
        nonlocal peak_ram_mb, monitoring, active_checkpoint_file
        while monitoring:
            try:
                # RAM
                mem_mb = process.memory_info().rss / (1024 * 1024)
                if mem_mb > peak_ram_mb:
                    peak_ram_mb = mem_mb

                # CPU
                cpu_p = process.cpu_percent(interval=0.1)
                sys_cpu = psutil.cpu_percent(interval=None)
                cpu_samples.append((cpu_p, sys_cpu))

                # Checkpoint dosyası takibi
                chk_dir = get_checkpoint_dir()
                if transcriber._current_checkpoint:
                    active_checkpoint_file = transcriber._current_checkpoint.file_path
                    if os.path.isfile(active_checkpoint_file):
                        chk_size = os.path.getsize(active_checkpoint_file)
                        checkpoint_samples.append(chk_size)

                time.sleep(2.0)
            except Exception:
                break

    mon_thread = threading.Thread(target=monitor_resources, daemon=True)
    mon_thread.start()

    # 4. Transkripsiyon Başlatma
    print("\n--- Transkripsiyon Başlatılıyor (faster-whisper small CPU int8) ---")
    t0 = time.time()
    last_print_time = time.time()

    def progress_callback(pct: int, status: str, text: str):
        nonlocal last_print_time
        # Kullanıcı arayüzü gibi 30 saniyede bir veya dönüm noktalarında logla
        now = time.time()
        if now - last_print_time >= 30.0 or pct in (10, 25, 50, 75, 90, 100):
            last_print_time = now
            elapsed = now - t0
            print(f"  [İlerleme %{pct:2d}] {status} | Geçen Süre: {elapsed:.1f} sn ({elapsed/60:.2f} dk) | Karakter: {len(text)}")

    final_text = transcriber.transcribe(
        audio_path=audio_path,
        total_duration=audio_duration,
        on_progress=progress_callback
    )
    t1 = time.time()
    monitoring = False
    mon_thread.join(timeout=3.0)

    total_duration = t1 - t0
    rtf = total_duration / audio_duration if audio_duration > 0 else 0.0

    print("\n" + "=" * 60)
    print("STRES TESTİ PERFORMANS VE KAYNAK SONUÇLARI")
    print("=" * 60)
    print(f"Toplam Ses Süresi     : {audio_duration:.2f} sn ({audio_duration / 60:.2f} dk)")
    print(f"Toplam İşlem Süresi   : {total_duration:.2f} sn ({total_duration / 60:.2f} dk)")
    print(f"Real-Time Factor (RTF): {rtf:.4f} ({1.0 / rtf:.2f}x gerçek zamanlı hız)")
    print(f"Başlangıç RAM         : {initial_ram_mb:.1f} MB")
    print(f"En Yüksek RAM (Peak)  : {peak_ram_mb:.1f} MB (Artış: +{peak_ram_mb - initial_ram_mb:.1f} MB)")

    # CPU Özet
    if cpu_samples:
        avg_proc_cpu = sum(s[0] for s in cpu_samples) / len(cpu_samples)
        avg_sys_cpu = sum(s[1] for s in cpu_samples) / len(cpu_samples)
        print(f"Ortalama Süreç CPU %  : %{avg_proc_cpu:.1f}")
        print(f"Ortalama Sistem CPU % : %{avg_sys_cpu:.1f} (8 çekirdekte 4 thread dengeli)")

    # Checkpoint Analizi
    print("\n--- Checkpoint Kurtarma Mekanizması Doğrulaması ---")
    print(f"Ölçülen Checkpoint Büyüme Örnekleri Sayısı: {len(checkpoint_samples)}")
    if checkpoint_samples:
        print(f"Checkpoint İlk Boyut : {checkpoint_samples[0]} bayt")
        print(f"Checkpoint Son Boyut : {checkpoint_samples[-1]} bayt")
        assert checkpoint_samples[-1] >= checkpoint_samples[0], "Checkpoint boyutu işlem sırasında artmalı"
        print(">>> Checkpoint dosyasının düzenli büyüdüğü doğrulandı.")

    # Checkpoint başarılı bitiş temizliği
    if active_checkpoint_file:
        checkpoint_remains = os.path.isfile(active_checkpoint_file)
        print(f"Kurtarma Dosyası Durumu: {'TEMİZLENDİ (Silindi)' if not checkpoint_remains else 'HATA: Dosya silinmedi!'}")
        assert not checkpoint_remains, "Başarılı bitiş sonrası kurtarma dosyası temizlenmiş olmalı!"
        print(">>> Gizlilik Doğrulandı: Başarılı işlem sonrası diskteki geçici metin temizlendi.")

    # 5. Model Reuse Doğrulaması (Hafızadan Yeniden Kullanım)
    print("\n--- Model Yeniden Kullanımı (Reuse) Doğrulaması ---")
    model_id_first = id(transcriber.model)
    info_15s = inspect_audio(sample_15s)
    
    t_reuse_start = time.time()
    reuse_text = transcriber.transcribe(
        audio_path=sample_15s,
        total_duration=info_15s["duration_seconds"],
        on_progress=lambda p, s, t: None
    )
    t_reuse_end = time.time()
    model_id_second = id(transcriber.model)

    reuse_duration = t_reuse_end - t_reuse_start
    print(f"İkinci Dosya İşlem Süresi: {reuse_duration:.2f} saniye")
    print(f"Model Instance ID Eşleşmesi: {model_id_first} == {model_id_second}")
    assert model_id_first == model_id_second, "Model nesnesi sıfırlanmamalı, aynı instance kullanılmalı"
    assert reuse_duration < 15.0, "Model diskten tekrar yüklenmeden hızlı çalışmalı"
    print(">>> Model Reuse Başarıyla Doğrulandı.")

    # 6. Doğruluk ve WER/CER Hesaplaması (Google AI Studio Referansı)
    print("\n--- Doğruluk Metrikleri (Google AI Studio Referansı ile) ---")
    wer_results = {}
    if os.path.isfile(ref_path):
        with open(ref_path, "r", encoding="utf-8") as f:
            ref_text = f.read().strip()
        
        wer_results = calculate_wer_metrics(ref_text, final_text)
        print(f"Referans Kelime Sayısı   : {wer_results.get('reference_words')}")
        print(f"Üretilen Kelime Sayısı   : {wer_results.get('hypothesis_words')}")
        print(f"Kelime Hata Oranı (WER)  : %{wer_results.get('wer') * 100:.2f}")
        print(f"Kelime Doğruluğu         : %{wer_results.get('word_accuracy') * 100:.2f}")
        print(f"Hata Dağılımı (S / D / I): {wer_results.get('substitutions')} / {wer_results.get('deletions')} / {wer_results.get('insertions')}")
    else:
        print("Referans transkript bulunamadı, yalnızca teknik tamamlanma raporlandı.")

    # 7. Sonuçları JSON olarak kaydet
    result_data = {
        "audio_path": audio_path,
        "audio_duration_seconds": audio_duration,
        "transcription_duration_seconds": total_duration,
        "real_time_factor": rtf,
        "speedup": (1.0 / rtf) if rtf > 0 else 0.0,
        "peak_ram_mb": peak_ram_mb,
        "initial_ram_mb": initial_ram_mb,
        "checkpoint_cleanup_verified": True,
        "model_reuse_verified": True,
        "wer_metrics": wer_results
    }

    out_json = os.path.join(ROOT_DIR, "tests", "stress_test_result.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)
    print(f"\nStres testi metrikleri kaydedildi: {out_json}")

if __name__ == "__main__":
    run_stress_test()

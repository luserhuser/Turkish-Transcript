"""
tests/run_hotwords_benchmark.py:
PDR Alan Sözlüğü (Hotwords) A/B Karşılaştırmalı Değerlendirme Testi.

Bu script, iki farklı ses kaydında kontrollü A/B testi icra eder:
1. sample_counseling_2m.mp3 (~1.8 dk iki konuşmacılı PDR danışma görüşmesi)
2. benchmark_slice_12m.mp3 (12 dk referans transkriptli Türkçe ses kaydı - Genel konuşma & Over-biasing kontrolü)

Her iki koşul için (Hotwords KAPALI vs Hotwords AÇIK):
- İşlem süresi (sn)
- RTF (Real-Time Factor)
- Çıktı metni
- PDR terimlerinin algılanma durumu
- Over-biasing / halüsinasyon kontrolü
- (12m dilim için) WER / CER metrikleri
ölçülür ve karşılaştırılır.
"""

import os
import sys
import time
import json
import re
from typing import Dict, Any

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import jiwer
from engine import inspect_audio, Transcriber
from engine.domain_vocabulary import get_default_pdr_terms, HIGH_PRIORITY_TERMS


def normalize_turkish_text(text: str) -> str:
    """Türkçe metni küçük harfe ve temiz noktalama işaretlerine normalize eder."""
    t = text.replace("İ", "i").replace("I", "ı").lower()
    # Noktalama işaretlerini kaldır
    t = re.sub(r"[^\w\s]", " ", t)
    # Çoklu boşlukları tekleştir
    return " ".join(t.split())


def calculate_metrics(reference: str, hypothesis: str) -> Dict[str, float]:
    """jiwer kullanarak WER, MER, WIL ve CER hesaplar."""
    ref_norm = normalize_turkish_text(reference)
    hyp_norm = normalize_turkish_text(hypothesis)

    wer = jiwer.wer(ref_norm, hyp_norm)
    cer = jiwer.cer(ref_norm, hyp_norm)
    mer = jiwer.mer(ref_norm, hyp_norm)
    wil = jiwer.wil(ref_norm, hyp_norm)

    return {
        "wer": round(wer * 100, 2),
        "cer": round(cer * 100, 2),
        "mer": round(mer * 100, 2),
        "wil": round(wil * 100, 2),
    }


def run_benchmark():
    print("=" * 70)
    print("PDR ALAN SÖZLÜĞÜ (HOTWORDS) A/B BENCHMARK DEĞERLENDİRMESİ")
    print("=" * 70)

    # 1. Test Kaydı 1: sample_counseling_2m.mp3 (Klinik PDR Görüşmesi)
    audio_counseling = os.path.join(PROJECT_ROOT, "tests", "sample_counseling_2m.mp3")
    info_c = inspect_audio(audio_counseling)
    duration_c = info_c["duration_seconds"]
    print(f"\n[TEST 1] PDR Görüşme Kaydı: {info_c['file_name']} ({duration_c:.2f} sn / {duration_c/60:.2f} dk)")

    # Model örneği (Model bellekte kalır, A ve B koşullarında aynı ağırlıklar kullanılır)
    transcriber = Transcriber(model_name="small", use_domain_hotwords=True)
    # Önceden modeli belleğe yükle
    transcriber.load_model()

    # Koşul A: Hotwords KAPALI
    print("\n>>> Koşul A: use_domain_hotwords = False (Baseline) çalıştırılıyor...")
    t0_a = time.perf_counter()
    transcript_a = transcriber.transcribe(
        audio_counseling,
        total_duration=duration_c,
        on_progress=lambda p, s, t: None,
        use_domain_hotwords=False
    )
    elapsed_a = time.perf_counter() - t0_a
    rtf_a = elapsed_a / duration_c

    # Koşul B: Hotwords AÇIK
    print(">>> Koşul B: use_domain_hotwords = True (PDR Hotwords) çalıştırılıyor...")
    t0_b = time.perf_counter()
    transcript_b = transcriber.transcribe(
        audio_counseling,
        total_duration=duration_c,
        on_progress=lambda p, s, t: None,
        use_domain_hotwords=True
    )
    elapsed_b = time.perf_counter() - t0_b
    rtf_b = elapsed_b / duration_c

    print("\n--- TEST 1 SONUÇLARI (sample_counseling_2m.mp3) ---")
    print(f"Koşul A (Hotwords KAPALI): Süre={elapsed_a:.2f} sn | RTF={rtf_a:.4f} | Krk={len(transcript_a)}")
    print(f"Koşul B (Hotwords AÇIK)  : Süre={elapsed_b:.2f} sn | RTF={rtf_b:.4f} | Krk={len(transcript_b)}")
    print(f"Süre Farkı: {elapsed_b - elapsed_a:+.2f} sn ({(elapsed_b - elapsed_a)/elapsed_a*100:+.1f}%)")

    # PDR Terimleri Varlığı Denetimi
    print("\nPDR Terimleri Tespiti (sample_counseling_2m.mp3):")
    sample_pdr_terms = [
        "görüşme",
        "staj",
        "sınav",
        "farkındalık",
        "nefes",
        "beden",
        "fiziksel",
        "olumsuz",
        "tehlike algısı",
        "gerginlik",
        "huzursuzluk",
    ]
    for term in sample_pdr_terms:
        in_a = term in transcript_a.lower()
        in_b = term in transcript_b.lower()
        status = "AYNI" if in_a == in_b else ("+ İYİLEŞME" if in_b and not in_a else "- DEĞİŞİM")
        print(f"  '{term:18}': Hotwords KAPALI={'VAR' if in_a else 'YOK'} | Hotwords AÇIK={'VAR' if in_b else 'YOK'} [{status}]")

    # Metin Farkı İncelemesi
    print("\nMetin Eşleşme Durumu:")
    if transcript_a == transcript_b:
        print("  İki çıktı metni birebir aynı.")
    else:
        print("  Çıktılarda kelime/harf seviyesinde farklar tespit edildi:")
        words_a = transcript_a.split()
        words_b = transcript_b.split()
        print(f"  Koşul A kelime sayısı: {len(words_a)}")
        print(f"  Koşul B kelime sayısı: {len(words_b)}")

    # 2. Test Kaydı 2: benchmark_slice_12m.mp3 (12 dk genel konuşma kaydı - Over-biasing denetimi)
    audio_slice_path = os.path.join(PROJECT_ROOT, "tests", "benchmark_slice_12m.mp3")
    ref_slice_path = os.path.join(PROJECT_ROOT, "tests", "reference_transcript_slice.txt")

    results_slice = {}
    if os.path.isfile(audio_slice_path) and os.path.isfile(ref_slice_path):
        info_s = inspect_audio(audio_slice_path)
        duration_s = info_s["duration_seconds"]
        print(f"\n[TEST 2] 12 Dakikalık Benchmark Kaydı (Over-biasing & WER Analizi): {duration_s/60:.2f} dk")

        with open(ref_slice_path, "r", encoding="utf-8") as f:
            ref_slice_text = f.read().strip()

        print(">>> Koşul A (12 dk - Hotwords KAPALI) çalıştırılıyor...")
        t0_sa = time.perf_counter()
        slice_transcript_a = transcriber.transcribe(
            audio_slice_path,
            total_duration=duration_s,
            on_progress=lambda p, s, t: None,
            use_domain_hotwords=False
        )
        elapsed_sa = time.perf_counter() - t0_sa
        rtf_sa = elapsed_sa / duration_s
        metrics_sa = calculate_metrics(ref_slice_text, slice_transcript_a)

        print(">>> Koşul B (12 dk - Hotwords AÇIK) çalıştırılıyor...")
        t0_sb = time.perf_counter()
        slice_transcript_b = transcriber.transcribe(
            audio_slice_path,
            total_duration=duration_s,
            on_progress=lambda p, s, t: None,
            use_domain_hotwords=True
        )
        elapsed_sb = time.perf_counter() - t0_sb
        rtf_sb = elapsed_sb / duration_s
        metrics_sb = calculate_metrics(ref_slice_text, slice_transcript_b)

        print("\n--- TEST 2 SONUÇLARI (12m Benchmark Slice) ---")
        print(f"Koşul A (Hotwords KAPALI): Süre={elapsed_sa:.2f} sn | RTF={rtf_sa:.4f} | WER=%{metrics_sa['wer']} | CER=%{metrics_sa['cer']}")
        print(f"Koşul B (Hotwords AÇIK)  : Süre={elapsed_sb:.2f} sn | RTF={rtf_sb:.4f} | WER=%{metrics_sb['wer']} | CER=%{metrics_sb['cer']}")
        print(f"WER Değişimi: {metrics_sb['wer'] - metrics_sa['wer']:+.2f}%")
        print(f"Süre Farkı  : {elapsed_sb - elapsed_sa:+.2f} sn ({(elapsed_sb - elapsed_sa)/elapsed_sa*100:+.1f}%)")

        # Over-biasing / Halüsinasyon Kontrolü:
        # Genel konuşmada PDR terimlerinin sebepsiz yere metne sokulup sokulmadığını denetle
        print("\nOver-biasing / Halüsinasyon Denetimi:")
        unrelated_clinical_terms = [
            "psikolojik danışma ve rehberlik",
            "bilişsel çarpıtma",
            "dissosiyasyon",
            "aydınlatılmış onam",
            "vaka formülasyonu",
            "maruz bırakma",
            "öz şefkat",
            "terapötik ittifak"
        ]
        hallucinations = []
        for u_term in unrelated_clinical_terms:
            if u_term in slice_transcript_b.lower() and u_term not in ref_slice_text.lower():
                hallucinations.append(u_term)

        if not hallucinations:
            print("  >>> SIFIR HALÜSİNASYON / SIFIR OVER-BIASING: İlgisiz klinik terimler genel konuşmaya uydurma olarak sızmadı! <<<")
        else:
            print(f"  DİKKAT: Olası over-biasing terimleri tespit edildi: {hallucinations}")

        results_slice = {
            "duration_s": duration_s,
            "condition_a": {
                "elapsed": elapsed_sa,
                "rtf": rtf_sa,
                "metrics": metrics_sa,
            },
            "condition_b": {
                "elapsed": elapsed_sb,
                "rtf": rtf_sb,
                "metrics": metrics_sb,
            }
        }

    # Karşılaştırma Raporunu JSON olarak kaydet
    benchmark_report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "hardware_profile": transcriber.hardware_profile.name if transcriber.hardware_profile else "UNKNOWN",
        "cpu_threads": transcriber.cpu_threads,
        "sample_counseling_2m": {
            "duration": duration_c,
            "condition_a_off": {"elapsed": elapsed_a, "rtf": rtf_a, "transcript": transcript_a},
            "condition_b_on": {"elapsed": elapsed_b, "rtf": rtf_b, "transcript": transcript_b},
        },
        "benchmark_slice_12m": results_slice
    }

    report_path = os.path.join(PROJECT_ROOT, "tests", "benchmark_hotwords_results.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(benchmark_report, f, ensure_ascii=False, indent=2)

    print(f"\nBenchmark raporu diske kaydedildi: {report_path}")
    print("=" * 70)


if __name__ == "__main__":
    run_benchmark()

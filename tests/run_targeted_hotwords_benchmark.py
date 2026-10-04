"""
tests/run_targeted_hotwords_benchmark.py:
Hedeflenmiş PDR Hotwords (OFF vs 5 vs 10 vs 20) Kapsamlı A/B/C/D Benchmark Testi.

Bu script:
1. Tokenizer Token Bütçe Analizi (5, 10, 20 ve 111 terim için)
2. 12 Dakikalık Benchmark Kaydı (benchmark_slice_12m.mp3) üzerinde:
   - A: Hotwords OFF (Baseline)
   - B: 5 Terim (PDR_HOTWORDS_5)
   - C: 10 Terim (PDR_HOTWORDS_10)
   - D: 20 Terim (PDR_HOTWORDS_20)
   Metrikler: WER, CER, MER, WIL, İşlem Süresi, RTF, Kelime Sayısı, İkame (S), Silme (D), Ekleme (I)
   Over-biasing / Yanlış PDR Terimi Enjeksiyonu Denetimi
3. Klinik PDR Terimleri Kaydı (sample_pdr_clinical_terms.mp3) üzerinde:
   - 20 terimin her birinin OFF / 5 / 10 / 20 altındaki tanınma doğruluğu
4. Karar ve Kazanan Belirleme Raporu
"""

import sys
import os
import time
import json
import re
from typing import Dict, Any, List

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import jiwer
from engine import inspect_audio, Transcriber
from engine.domain_vocabulary import (
    PDR_HOTWORDS_5,
    PDR_HOTWORDS_10,
    PDR_HOTWORDS_20,
    get_master_pdr_terms,
    build_hotwords,
    build_hotwords_list,
)


def normalize_turkish_text(text: str) -> str:
    """Türkçe metni küçük harfe ve temiz noktalama işaretlerine normalize eder."""
    t = text.replace("İ", "i").replace("I", "ı").lower()
    t = re.sub(r"[^\w\s]", " ", t)
    return " ".join(t.split())


def calculate_detailed_metrics(reference: str, hypothesis: str) -> Dict[str, Any]:
    """jiwer kullanarak detaylı S, D, I, H ve WER/CER hesaplar."""
    ref_norm = normalize_turkish_text(reference)
    hyp_norm = normalize_turkish_text(hypothesis)

    output = jiwer.process_words(ref_norm, hyp_norm)
    cer = jiwer.cer(ref_norm, hyp_norm)
    mer = jiwer.mer(ref_norm, hyp_norm)
    wil = jiwer.wil(ref_norm, hyp_norm)

    return {
        "wer": round(output.wer * 100, 2),
        "cer": round(cer * 100, 2),
        "mer": round(mer * 100, 2),
        "wil": round(wil * 100, 2),
        "substitutions": output.substitutions,
        "deletions": output.deletions,
        "insertions": output.insertions,
        "hits": output.hits,
        "ref_word_count": len(ref_norm.split()),
        "hyp_word_count": len(hyp_norm.split()),
    }


def analyze_token_counts(transcriber: Transcriber) -> Dict[str, Any]:
    """Whisper tokenizer token kullanımını ölçer."""
    tokenizer = transcriber.model.hf_tokenizer
    master_terms = get_master_pdr_terms()

    token_counts = {}
    sets = [
        ("5_terms", PDR_HOTWORDS_5),
        ("10_terms", PDR_HOTWORDS_10),
        ("20_terms", PDR_HOTWORDS_20),
        ("111_master", master_terms),
    ]

    for name, terms in sets:
        text = " " + " ".join(terms)
        tokens = tokenizer.encode(text)
        token_counts[name] = {
            "term_count": len(terms),
            "char_count": len(text),
            "token_count": len(tokens),
            "terms": terms,
        }
    return token_counts


def run_targeted_benchmark():
    print("=" * 75)
    print("HEDEFLENMİŞ PDR HOTWORDS A/B/C/D BENCHMARK DEĞERLENDİRMESİ")
    print("=" * 75, flush=True)

    # 1. Transcriber Örneği ve Model Yükleme (Model bellekte tutulur)
    transcriber = Transcriber(model_name="small", use_domain_hotwords=False, hotword_mode="off")
    print("Transcriber modeli belleğe yükleniyor (small - CPU int8)...", flush=True)
    transcriber.load_model()

    # 2. Token Bütçe Analizi
    print("\n--- 1. TOKENIZER TOKEN BÜTÇESİ ANALİZİ ---", flush=True)
    token_analysis = analyze_token_counts(transcriber)
    for name, data in token_analysis.items():
        print(f"  [{name:10}] Terim: {data['term_count']:3d} | Karakter: {data['char_count']:4d} | Token: {data['token_count']:3d} tokens", flush=True)

    # 3. 12 Dakikalık Benchmark Slice Değerlendirmesi
    slice_audio_path = os.path.join(PROJECT_ROOT, "tests", "benchmark_slice_12m.mp3")
    slice_ref_path = os.path.join(PROJECT_ROOT, "tests", "reference_transcript_slice.txt")

    modes_to_test = [
        ("OFF", "off"),
        ("5", "5"),
        ("10", "10"),
        ("20", "20"),
    ]

    benchmark_12m_results = {}
    over_biasing_report = {}

    if os.path.isfile(slice_audio_path) and os.path.isfile(slice_ref_path):
        info_slice = inspect_audio(slice_audio_path)
        duration_slice = info_slice["duration_seconds"]
        with open(slice_ref_path, "r", encoding="utf-8") as f:
            slice_reference = f.read().strip()

        print(f"\n--- 2. 12 DAKİKALIK BENCHMARK TESTİ ({info_slice['file_name']} - {duration_slice/60:.2f} dk) ---", flush=True)

        for label, mode in modes_to_test:
            print(f"\n>>> Koşul {label} (hotword_mode='{mode}') çalıştırılıyor...", flush=True)
            t0 = time.perf_counter()
            transcript = transcriber.transcribe(
                slice_audio_path,
                total_duration=duration_slice,
                on_progress=lambda p, s, t: None,
                hotword_mode=mode
            )
            elapsed = time.perf_counter() - t0
            rtf = elapsed / duration_slice

            metrics = calculate_detailed_metrics(slice_reference, transcript)
            metrics["elapsed_seconds"] = round(elapsed, 2)
            metrics["rtf"] = round(rtf, 4)
            metrics["transcript"] = transcript

            benchmark_12m_results[label] = metrics
            print(f"    Sonuç {label:3}: Süre={elapsed:.2f} sn | RTF={rtf:.4f} | WER=%{metrics['wer']} | CER=%{metrics['cer']} | S={metrics['substitutions']} D={metrics['deletions']} I={metrics['insertions']}", flush=True)

        # 4. Over-Biasing ve Yanlış Enjeksiyon Denetimi (12 dk Kaydında)
        print("\n--- 3. OVER-BIASING VE HALÜSİNASYON DENETİMİ (12m Genel Kayıt) ---", flush=True)
        ref_norm = normalize_turkish_text(slice_reference)

        for label, mode in modes_to_test:
            hyp_norm = normalize_turkish_text(benchmark_12m_results[label]["transcript"])
            hallucinated_terms = []
            for term in PDR_HOTWORDS_20:
                t_clean = normalize_turkish_text(term)
                if t_clean in hyp_norm and t_clean not in ref_norm:
                    hallucinated_terms.append(term)
            over_biasing_report[label] = hallucinated_terms
            print(f"  Koşul {label:3}: Hatalı Eklenen PDR Terimleri ({len(hallucinated_terms)} adet): {hallucinated_terms if hallucinated_terms else 'YOK (Temiz)'}", flush=True)
    else:
        print("\n--- 2 & 3. 12 DAKİKALIK BENCHMARK TESTİ: [ATLANDI] ---")
        print("  (Özel benchmark ses dilimi ve referans metni gizlilik nedeniyle depoda yer almamaktadır.)", flush=True)


    # 5. Klinik PDR Kaydında Terim Bazlı Tanınma Analizi
    clinical_audio_path = os.path.join(PROJECT_ROOT, "tests", "sample_pdr_clinical_terms.mp3")
    clinical_ref_path = os.path.join(PROJECT_ROOT, "tests", "reference_pdr_clinical_terms.txt")

    info_clinical = inspect_audio(clinical_audio_path)
    duration_clinical = info_clinical["duration_seconds"]

    with open(clinical_ref_path, "r", encoding="utf-8") as f:
        clinical_reference = f.read().strip()

    print(f"\n--- 4. KLİNİK PDR TERİMLERİ KAYDI ({info_clinical['file_name']} - {duration_clinical:.1f} sn) ---", flush=True)
    clinical_results = {}

    for label, mode in modes_to_test:
        print(f">>> Klinik Test - Koşul {label} (hotword_mode='{mode}') çalıştırılıyor...", flush=True)
        t0 = time.perf_counter()
        transcript = transcriber.transcribe(
            clinical_audio_path,
            total_duration=duration_clinical,
            on_progress=lambda p, s, t: None,
            hotword_mode=mode
        )
        elapsed = time.perf_counter() - t0
        rtf = elapsed / duration_clinical

        metrics = calculate_detailed_metrics(clinical_reference, transcript)
        metrics["elapsed_seconds"] = round(elapsed, 2)
        metrics["rtf"] = round(rtf, 4)
        metrics["transcript"] = transcript

        clinical_results[label] = metrics
        print(f"    Klinik {label:3}: Süre={elapsed:.2f} sn | RTF={rtf:.4f} | WER=%{metrics['wer']} | CER=%{metrics['cer']}", flush=True)

    # 6. 20 Terimin Tek Tek Tanınma Durumu Karşılaştırması
    print("\n--- 5. 20 HEDEF PDR TERİMİNİN TEK TEK TANINMA DOĞRULUĞU ---", flush=True)
    term_recognition_table = {}

    for term in PDR_HOTWORDS_20:
        term_clean = normalize_turkish_text(term)
        rec_status = {}
        for label, _ in modes_to_test:
            hyp_norm = normalize_turkish_text(clinical_results[label]["transcript"])
            rec_status[label] = term_clean in hyp_norm
        term_recognition_table[term] = rec_status

    print(f"{'TERİM':30} | {'OFF':5} | {'5':5} | {'10':5} | {'20':5}", flush=True)
    print("-" * 55, flush=True)
    for term, status in term_recognition_table.items():
        s_off = "DOĞRU" if status["OFF"] else "YANLIŞ"
        s_5   = "DOĞRU" if status["5"] else "YANLIŞ"
        s_10  = "DOĞRU" if status["10"] else "YANLIŞ"
        s_20  = "DOĞRU" if status["20"] else "YANLIŞ"
        print(f"{term:30} | {s_off:5} | {s_5:5} | {s_10:5} | {s_20:5}", flush=True)

    # 7. Sonuç Raporu ve JSON Kaydı
    final_data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "hardware_profile": transcriber.hardware_profile.name if transcriber.hardware_profile else "UNKNOWN",
        "cpu_threads": transcriber.cpu_threads,
        "token_analysis": token_analysis,
        "benchmark_12m": {
            label: {k: v for k, v in res.items() if k != "transcript"}
            for label, res in benchmark_12m_results.items()
        },
        "over_biasing_report": over_biasing_report,
        "clinical_benchmark": {
            label: {k: v for k, v in res.items() if k != "transcript"}
            for label, res in clinical_results.items()
        },
        "term_recognition_table": term_recognition_table,
    }

    out_file = os.path.join(PROJECT_ROOT, "tests", "targeted_hotwords_benchmark_results.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)

    print(f"\nBenchmark sonuçları diske kaydedildi: {out_file}", flush=True)
    print("=" * 75, flush=True)


if __name__ == "__main__":
    run_targeted_benchmark()

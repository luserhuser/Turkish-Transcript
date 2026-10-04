"""
tests/run_controlled_experiments.py: 12 dakikalık temsil edici benchmark parçası
(tests/benchmark_slice_12m.mp3) üzerinde faster-whisper small modelinin
tek değişkenli kontrollü deneylerini sırayla koşturur ve sonuçları tablo olarak sunar.
"""

import os
import sys
import json
import time

from benchmark_wer import run_benchmark

AUDIO_PATH = os.path.join(os.path.dirname(__file__), "benchmark_slice_12m.mp3")
REF_PATH = os.path.join(os.path.dirname(__file__), "reference_transcript_slice.txt")

if not os.path.isfile(AUDIO_PATH) or not os.path.isfile(REF_PATH):
    print("[BILGI] Kontrollu deneyler icin ozel benchmark kaydi (benchmark_slice_12m.mp3) bulunamadi.")
    print("[BILGI] Bu dosya gizlilik nedeniyle depoda tutulmamaktadir. Test zararsizca atlandi.")
    sys.exit(0)


experiments = [
    {
        "name": "CONTROL (Varsayılan)",
        "tag": "control",
        "beam_size": 5,
        "vad_filter": True,
        "condition_on_previous_text": False,
        "temperature": 0.0
    },
    {
        "name": "EXP 1: beam_size=1 (Greedy)",
        "tag": "beam1",
        "beam_size": 1,
        "vad_filter": True,
        "condition_on_previous_text": False,
        "temperature": 0.0
    },
    {
        "name": "EXP 2: VAD Kapalı",
        "tag": "novad",
        "beam_size": 5,
        "vad_filter": False,
        "condition_on_previous_text": False,
        "temperature": 0.0
    },
    {
        "name": "EXP 3: condition_on_prev=True",
        "tag": "condition_true",
        "beam_size": 5,
        "vad_filter": True,
        "condition_on_previous_text": True,
        "temperature": 0.0
    },
]

all_results = []

print(f"\n{'='*75}")
print("KONTROLLÜ DENEYLER BAŞLIYOR: faster-whisper 'small' (12 dk Temsilci Dilim)")
print(f"Ses: {AUDIO_PATH}")
print(f"Referans: {REF_PATH}")
print(f"{'='*75}\n")

for exp in experiments:
    print(f"\n>>> ÇALIŞTIRILIYOR: {exp['name']} <<<")
    res = run_benchmark(
        audio_path=AUDIO_PATH,
        model_name="small",
        reference_path=REF_PATH,
        device="cpu",
        compute_type="int8",
        beam_size=exp["beam_size"],
        vad_filter=exp["vad_filter"],
        condition_on_previous_text=exp["condition_on_previous_text"],
        temperature=exp["temperature"],
        tag=exp["tag"]
    )
    all_results.append({
        "config_name": exp["name"],
        "tag": exp["tag"],
        "beam_size": exp["beam_size"],
        "vad_filter": exp["vad_filter"],
        "condition_on_prev": exp["condition_on_previous_text"],
        "wer": res["metrics"].get("wer", 0.0),
        "word_accuracy": res["metrics"].get("word_accuracy", 0.0),
        "elapsed_sec": res["elapsed_time_sec"],
        "elapsed_min": round(res["elapsed_time_sec"] / 60.0, 2),
        "rtf": res["rtf"],
        "peak_ram_mb": res["peak_ram_mb"],
        "substitutions": res["metrics"].get("substitutions", 0),
        "deletions": res["metrics"].get("deletions", 0),
        "insertions": res["metrics"].get("insertions", 0),
        "hits": res["metrics"].get("hits", 0),
    })

# Özet Tablo
print("\n" + "="*85)
print("KONTROLLÜ DENEY SONUÇ TABLOSU (small - 12 dk Temsilci Dilim)")
print("="*85)
print(f"{'CONFIG':<30} | {'WER':<8} | {'SÜRE':<10} | {'RTF':<8} | {'RAM':<10} | {'S / D / I'}")
print("-" * 85)
for r in all_results:
    s_d_i = f"{r['substitutions']} / {r['deletions']} / {r['insertions']}"
    print(f"{r['config_name']:<30} | %{r['wer']:<7.2f} | {r['elapsed_min']} dk     | {r['rtf']:<8.4f} | {r['peak_ram_mb']} MB   | {s_d_i}")
print("="*85)

# JSON olarak kaydet
out_json = os.path.join(os.path.dirname(__file__), "experiments_summary.json")
with open(out_json, "w", encoding="utf-8") as f:
    json.dump(all_results, f, ensure_ascii=False, indent=2)
print(f"\nÖzet veriler kaydedildi: {out_json}")

"""
tests/benchmark_wer.py: Model benchmark ve WER hesaplama scripti.
Faster-Whisper modelleri (base, small vb.) için işlem süresi, RTF, RAM tüketimi
ve Türkçe metin normalizasyonu ile WER (Word Error Rate) hesaplamasını otomatikleştirir.
"""

import os
import sys
import time
import argparse
import json
import re
import threading
from typing import Optional, Tuple, Dict, Any

import psutil
from faster_whisper import WhisperModel
import jiwer


def normalize_turkish(text: str) -> str:
    """
    Türkçe karakter ve noktalama kurallarına uygun metin normalizasyonu:
    - 'I' -> 'ı' ve 'İ' -> 'i' dönüşümü (Türkçe küçük harf doğruluğu)
    - Küçük harfe çevirme
    - Noktalama işaretleri ve özel karakterlerin kaldırılması
    - Fazla boşlukların temizlenmesi
    """
    if not text:
        return ""
    # Türkçe büyük harf dönüşümü
    text = text.replace("I", "ı").replace("İ", "i")
    text = text.lower()
    # Noktalama ve altçizgileri boşlukla değiştir, sadece harf ve rakamları koru
    text = re.sub(r"[\W_]+", " ", text)
    # Fazla boşlukları teke indir
    return " ".join(text.split())


def calculate_wer_metrics(reference_text: str, hypothesis_text: str) -> Dict[str, Any]:
    """
    Normalize edilmiş referans ve hipotez metinleri üzerinden
    WER, Doğruluk, Substitution, Deletion, Insertion ve Hit değerlerini hesaplar.
    """
    ref_norm = normalize_turkish(reference_text)
    hyp_norm = normalize_turkish(hypothesis_text)

    if not ref_norm:
        return {
            "error": "Referans metin boş.",
            "wer": 0.0,
            "word_accuracy": 0.0,
            "substitutions": 0,
            "deletions": 0,
            "insertions": 0,
            "hits": 0,
            "reference_words": 0,
            "hypothesis_words": len(hyp_norm.split()) if hyp_norm else 0,
        }

    output = jiwer.process_words(ref_norm, hyp_norm)
    ref_words_count = output.substitutions + output.deletions + output.hits
    wer_pct = output.wer * 100.0
    word_accuracy_pct = max(0.0, 100.0 - wer_pct)

    return {
        "wer": round(wer_pct, 2),
        "word_accuracy": round(word_accuracy_pct, 2),
        "substitutions": output.substitutions,
        "deletions": output.deletions,
        "insertions": output.insertions,
        "hits": output.hits,
        "reference_words": ref_words_count,
        "hypothesis_words": len(hyp_norm.split()),
        "ref_sample": ref_norm[:150] + "..." if len(ref_norm) > 150 else ref_norm,
        "hyp_sample": hyp_norm[:150] + "..." if len(hyp_norm) > 150 else hyp_norm,
    }


class MemoryMonitor:
    """Arka planda tepe RAM (Peak RSS) tüketimini MB cinsinden izler."""
    def __init__(self, interval_sec: float = 0.5):
        self.interval = interval_sec
        self.peak_memory_mb = 0.0
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._process = psutil.Process(os.getpid())

    def start(self):
        self._running = True
        self.peak_memory_mb = self._process.memory_info().rss / (1024 * 1024)
        self._thread = threading.Thread(target=self._monitor, daemon=True)
        self._thread.start()

    def _monitor(self):
        while self._running:
            try:
                rss_mb = self._process.memory_info().rss / (1024 * 1024)
                if rss_mb > self.peak_memory_mb:
                    self.peak_memory_mb = rss_mb
            except Exception:
                pass
            time.sleep(self.interval)

    def stop(self) -> float:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        try:
            final_rss = self._process.memory_info().rss / (1024 * 1024)
            if final_rss > self.peak_memory_mb:
                self.peak_memory_mb = final_rss
        except Exception:
            pass
        return round(self.peak_memory_mb, 2)


def run_benchmark(
    audio_path: str,
    model_name: str = "small",
    reference_path: Optional[str] = None,
    output_path: Optional[str] = None,
    device: str = "cpu",
    compute_type: str = "int8",
    beam_size: int = 5,
    vad_filter: bool = True,
    condition_on_previous_text: bool = False,
    temperature: float = 0.0,
    tag: str = ""
) -> Dict[str, Any]:
    """
    Belirtilen model ve parametreler ile transkripsiyon benchmark'ı çalıştırır.
    """
    tag_str = f" [{tag}]" if tag else ""
    print(f"\n{'='*70}")
    print(f"BENCHMARK BAŞLATIYOR{tag_str}: Model='{model_name}' | Device='{device}' | Compute='{compute_type}'")
    print(f"Ses Dosyası: {audio_path}")
    print(f"Parametreler: beam_size={beam_size}, vad_filter={vad_filter}, condition_on_prev={condition_on_previous_text}, temp={temperature}")
    print(f"{'='*70}")

    if not os.path.isfile(audio_path):
        raise FileNotFoundError(f"Ses dosyası bulunamadı: {audio_path}")

    # RAM izleme başlat
    mem_monitor = MemoryMonitor(interval_sec=0.25)
    mem_monitor.start()

    start_time = time.perf_counter()

    # Model yükleme
    print(f"[{time.strftime('%H:%M:%S')}] Model yükleniyor ({model_name})...")
    model = WhisperModel(
        model_name,
        device=device,
        compute_type=compute_type
    )

    vad_params = dict(
        min_silence_duration_ms=500,
        speech_pad_ms=400,
    ) if vad_filter else None

    print(f"[{time.strftime('%H:%M:%S')}] Transkripsiyon işleniyor...")

    segments, info = model.transcribe(
        audio_path,
        language="tr",
        task="transcribe",
        vad_filter=vad_filter,
        vad_parameters=vad_params,
        beam_size=beam_size,
        temperature=temperature,
        condition_on_previous_text=condition_on_previous_text
    )

    audio_duration_sec = info.duration
    collected_texts = []
    seg_count = 0

    last_log_time = time.time()
    for seg in segments:
        text_clean = seg.text.strip()
        if text_clean:
            collected_texts.append(text_clean)
        seg_count += 1
        # Her 20 saniyede bir ilerleme bildirimi yaz
        if time.time() - last_log_time > 20.0:
            last_log_time = time.time()
            pct = min(100.0, (seg.end / audio_duration_sec) * 100.0) if audio_duration_sec else 0.0
            print(f"  > İlerleme: {seg.end:.1f}s / {audio_duration_sec:.1f}s (%{pct:.1f}) | {seg_count} segment")

    elapsed_time_sec = time.perf_counter() - start_time
    peak_ram_mb = mem_monitor.stop()

    full_transcript = " ".join(collected_texts).strip()

    # RTF (Real-Time Factor) = İşlem Süresi / Ses Süresi
    rtf = elapsed_time_sec / audio_duration_sec if audio_duration_sec > 0 else 0.0

    print(f"\n[{time.strftime('%H:%M:%S')}] Transkripsiyon tamamlandı!")
    print(f"  - Ses Süresi: {audio_duration_sec:.2f} saniye ({audio_duration_sec/60:.2f} dakika)")
    print(f"  - İşlem Süresi: {elapsed_time_sec:.2f} saniye ({elapsed_time_sec/60:.2f} dakika)")
    print(f"  - Real-Time Factor (RTF): {rtf:.4f} (Gerçek zamanın {1/rtf:.2f}x katı hızında)")
    print(f"  - Tepe RAM (Peak RSS): {peak_ram_mb:.1f} MB")
    print(f"  - Toplam Üretilen Kelime: {len(full_transcript.split())}")

    # Transkripti kaydet
    file_suffix = f"_{tag}" if tag else ""
    if not output_path:
        output_path = os.path.join(os.path.dirname(__file__), f"output_{model_name}{file_suffix}.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_transcript)
    print(f"  - Üretilen Transkript Kaydedildi: {output_path}")

    # Referans metin karşılaştırması
    wer_results = {}
    if reference_path and os.path.isfile(reference_path):
        print(f"\nReferans transkript karşılaştırılıyor ({reference_path})...")
        with open(reference_path, "r", encoding="utf-8") as f:
            ref_text = f.read()
        wer_results = calculate_wer_metrics(ref_text, full_transcript)
        print(f"  - Reference Transcript: {wer_results['reference_words']} kelime")
        print(f"  - Model Transcript: {wer_results['hypothesis_words']} kelime")
        print(f"  - WER: %{wer_results['wer']:.2f}")
        print(f"  - Kelime Doğruluğu: %{wer_results['word_accuracy']:.2f}")
        print(f"  - Substitutions (S): {wer_results['substitutions']}")
        print(f"  - Deletions (D): {wer_results['deletions']}")
        print(f"  - Insertions (I): {wer_results['insertions']}")
        print(f"  - Hits (C): {wer_results['hits']}")
    else:
        print("\n[BİLGİ] Referans transkript dosyası verilmediği için WER hesaplaması beklemede.")

    result_data = {
        "tag": tag,
        "model": model_name,
        "device": device,
        "compute_type": compute_type,
        "audio_duration_sec": round(audio_duration_sec, 2),
        "elapsed_time_sec": round(elapsed_time_sec, 2),
        "rtf": round(rtf, 4),
        "peak_ram_mb": peak_ram_mb,
        "output_path": output_path,
        "metrics": wer_results,
        "settings": {
            "language": "tr",
            "task": "transcribe",
            "beam_size": beam_size,
            "temperature": temperature,
            "condition_on_previous_text": condition_on_previous_text,
            "vad_filter": vad_filter,
            "vad_parameters": vad_params
        }
    }

    # JSON olarak da kaydet
    json_path = os.path.join(os.path.dirname(__file__), f"benchmark_result_{model_name}{file_suffix}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result_data, f, ensure_ascii=False, indent=2)

    return result_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="faster-whisper WER Benchmark Suite")
    parser.add_argument("--audio", type=str, default=None, help="Ses dosyası yolu")
    parser.add_argument("--model", type=str, default="small", choices=["tiny", "base", "small", "medium", "large-v3"], help="Whisper model boyutu")
    parser.add_argument("--reference", type=str, default=None, help="Google AI Studio referans transkript dosyası (.txt)")
    parser.add_argument("--output", type=str, default=None, help="Çıktı transkript dosya yolu")
    parser.add_argument("--device", type=str, default="cpu", choices=["cpu", "cuda"], help="Donanım (cpu veya cuda)")
    parser.add_argument("--compute_type", type=str, default="int8", help="Compute type (int8, float16 vb.)")
    parser.add_argument("--beam_size", type=int, default=5, help="Beam size (1=greedy, 5=standart)")
    parser.add_argument("--vad_filter", action="store_true", default=True, help="Silero VAD filtreleme aç (varsayılan: True)")
    parser.add_argument("--no_vad_filter", action="store_false", dest="vad_filter", help="Silero VAD filtrelemeyi kapat")
    parser.add_argument("--condition_on_previous_text", action="store_true", default=False, help="Önceki metne şartla (varsayılan: False)")
    parser.add_argument("--temperature", type=float, default=0.0, help="Sıcaklık (varsayılan: 0.0)")
    parser.add_argument("--tag", type=str, default="", help="Test etiketi (ör: control, beam1, novad, condition_true)")
    parser.add_argument("--compare_only", type=str, default=None, nargs=2, metavar=("REF_FILE", "HYP_FILE"), help="İki dosyayı karşılaştırarak yalnızca WER hesapla")

    args = parser.parse_args()

    if args.compare_only:
        ref_f, hyp_f = args.compare_only
        with open(ref_f, "r", encoding="utf-8") as f:
            ref_t = f.read()
        with open(hyp_f, "r", encoding="utf-8") as f:
            hyp_t = f.read()
        res = calculate_wer_metrics(ref_t, hyp_t)
        print("\n--- WER HESAPLAMA SONUCU ---")
        print(f"Referans Kelime: {res['reference_words']}")
        print(f"Hipotez Kelime: {res['hypothesis_words']}")
        print(f"WER: %{res['wer']:.2f}")
        print(f"Kelime Doğruluğu: %{res['word_accuracy']:.2f}")
        print(f"Substitutions (S): {res['substitutions']}")
        print(f"Deletions (D): {res['deletions']}")
        print(f"Insertions (I): {res['insertions']}")
        print(f"Hits (C): {res['hits']}")
    else:
        if not args.audio or not os.path.isfile(args.audio):
            print("[BILGI] Belirtilen ses dosyasi bulunamadi veya belirtilmedi.")
            print("Kullanim ornegi: python benchmark_wer.py --audio <ses_dosyasi.mp3> [--reference <referans.txt>]")
            sys.exit(0)
        run_benchmark(
            audio_path=args.audio,

            model_name=args.model,
            reference_path=args.reference,
            output_path=args.output,
            device=args.device,
            compute_type=args.compute_type,
            beam_size=args.beam_size,
            vad_filter=args.vad_filter,
            condition_on_previous_text=args.condition_on_previous_text,
            temperature=args.temperature,
            tag=args.tag
        )

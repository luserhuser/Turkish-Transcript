"""
tests/test_hardware_profiler.py:
Otomatik donanım profili ve güvenli thread tahsisi test paketi:
CASE A: 4 mantıksal CPU, düşük/temel RAM -> LOW -> 2 threads
CASE B: 8 mantıksal CPU, dengeli RAM -> BALANCED -> 4 threads
CASE C: 16+ mantıksal CPU, 16+ GB RAM, sağlıklı boş RAM -> HIGH -> 6–8 threads
CASE D: Güçlü CPU ancak kritik derecede düşük boş RAM -> Güvenli downgrade (LOW/BALANCED)
CASE E: Donanım tespiti istisnası (arızası) -> Güvenli fallback, uygulama çalışmaya devam eder
CASE F: cpu_threads asla azami güvenli sınırı (<= 8) aşmaz
CASE G: Transcriber varsayılan olarak small + cpu + int8 başlatır
CASE H: Profil önbelleği güvenle yazılır ve okunur
"""

import os
import sys
import tempfile
import json
from unittest.mock import patch

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from engine import (
    Transcriber,
    HardwareProfile,
    detect_hardware_profile,
    get_hardware_cache_path,
)
from engine.hardware import (
    classify_hardware,
    _load_cached_hardware,
    _save_cached_hardware,
    HARD_MAX_CPU_THREADS,
)

def run_hardware_profiler_tests():
    print("=" * 60)
    print("DONANIM PROFİLİ VE GÜVENLİ THREAD TAHSİSİ TESTLERİ")
    print("=" * 60)

    # CASE A: 4 mantıksal CPU, düşük/temel RAM -> LOW -> 2 threads
    print("\n--- CASE A: 4 Çekirdek, Temel RAM Testi ---")
    p_a = classify_hardware(
        logical_cpus=4,
        physical_cpus=2,
        total_ram_gb=6.0,
        available_ram_gb=3.5,
        cpu_name="Basic Quad-Core CPU"
    )
    print(f"Profil: {p_a.name} | Threads: {p_a.cpu_threads} | Gerekçe: {p_a.reason}")
    assert p_a.name == "LOW", f"Beklenen LOW, alınan: {p_a.name}"
    assert p_a.cpu_threads == 2, f"Beklenen 2 thread, alınan: {p_a.cpu_threads}"
    print(">>> CASE A BAŞARILI! <<<")

    # CASE B: 8 mantıksal CPU, sağlıklı RAM -> BALANCED -> 4 threads
    print("\n--- CASE B: 8 Çekirdek, Dengeli RAM Testi ---")
    p_b = classify_hardware(
        logical_cpus=8,
        physical_cpus=4,
        total_ram_gb=16.0,
        available_ram_gb=8.0,
        cpu_name="Intel Core i5-10300H"
    )
    print(f"Profil: {p_b.name} | Threads: {p_b.cpu_threads} | Gerekçe: {p_b.reason}")
    assert p_b.name == "BALANCED", f"Beklenen BALANCED, alınan: {p_b.name}"
    assert p_b.cpu_threads == 4, f"Beklenen 4 thread, alınan: {p_b.cpu_threads}"
    print(">>> CASE B BAŞARILI! <<<")

    # CASE C: 16+ mantıksal CPU, 16+ GB RAM, sağlıklı boş RAM -> HIGH -> 6-8 threads
    print("\n--- CASE C: 16 Çekirdek, 32 GB RAM Testi ---")
    p_c = classify_hardware(
        logical_cpus=16,
        physical_cpus=8,
        total_ram_gb=32.0,
        available_ram_gb=18.0,
        cpu_name="AMD Ryzen 7 5800X / Intel Core i7"
    )
    print(f"Profil: {p_c.name} | Threads: {p_c.cpu_threads} | Gerekçe: {p_c.reason}")
    assert p_c.name == "HIGH", f"Beklenen HIGH, alınan: {p_c.name}"
    assert p_c.cpu_threads in (6, 8), f"Beklenen 6 veya 8 thread, alınan: {p_c.cpu_threads}"
    assert p_c.cpu_threads <= HARD_MAX_CPU_THREADS
    print(">>> CASE C BAŞARILI! <<<")

    # CASE D: Güçlü CPU ancak kritik derecede düşük boş RAM -> Güvenli Downgrade
    print("\n--- CASE D: Güçlü CPU, Kritik Düşük Kullanılabilir Bellek Testi ---")
    # D1: Boş RAM < 2.5 GB -> LOW seviyesine düşürülmeli
    p_d1 = classify_hardware(
        logical_cpus=16,
        physical_cpus=8,
        total_ram_gb=32.0,
        available_ram_gb=1.8, # Çok düşük boş bellek
        cpu_name="AMD Ryzen 7 5800X"
    )
    print(f"D1 (1.8 GB Boş RAM) -> Profil: {p_d1.name} | Threads: {p_d1.cpu_threads} | Gerekçe: {p_d1.reason}")
    assert p_d1.name == "LOW", f"Kritik RAM'de LOW bekleniyordu, alınan: {p_d1.name}"
    assert p_d1.cpu_threads == 2, f"Kritik RAM'de 2 thread bekleniyordu, alınan: {p_d1.cpu_threads}"

    # D2: Boş RAM < 5.0 GB -> BALANCED seviyesine sınırlandırılmalı
    p_d2 = classify_hardware(
        logical_cpus=16,
        physical_cpus=8,
        total_ram_gb=32.0,
        available_ram_gb=3.8, # 5 GB altı boş bellek
        cpu_name="AMD Ryzen 7 5800X"
    )
    print(f"D2 (3.8 GB Boş RAM) -> Profil: {p_d2.name} | Threads: {p_d2.cpu_threads} | Gerekçe: {p_d2.reason}")
    assert p_d2.name == "BALANCED", f"5GB altı RAM'de BALANCED bekleniyordu, alınan: {p_d2.name}"
    assert p_d2.cpu_threads == 4, f"BALANCED için 4 thread bekleniyordu, alınan: {p_d2.cpu_threads}"
    print(">>> CASE D BAŞARILI! <<<")

    # CASE E: Donanım tespiti istisnası (arızası) -> Güvenli Fallback
    print("\n--- CASE E: Donanım Tespiti İstisnası / Fallback Testi ---")
    with patch("engine.hardware._query_static_hardware", side_effect=RuntimeError("Simüle donanım çökmesi")):
        fallback_profile = detect_hardware_profile(force_refresh=True)
        print(f"Fallback Profil: {fallback_profile.name} | Threads: {fallback_profile.cpu_threads} | Gerekçe: {fallback_profile.reason}")
        assert fallback_profile is not None
        assert fallback_profile.name in ("BALANCED", "LOW")
        assert fallback_profile.cpu_threads in (2, 4)
        assert "fallback" in fallback_profile.reason.lower()
    print(">>> CASE E BAŞARILI! <<<")

    # CASE F: cpu_threads asla azami güvenli sınırı (<= 8) aşmaz
    print("\n--- CASE F: Güvenli Tavan ve Aşırı Çekirdek Sınırı Testi ---")
    # 64 çekirdekli sistem simülasyonu
    p_f64 = classify_hardware(
        logical_cpus=64,
        physical_cpus=32,
        total_ram_gb=128.0,
        available_ram_gb=64.0,
        cpu_name="AMD Threadripper PRO"
    )
    print(f"64 Çekirdek Profil: {p_f64.name} | Threads: {p_f64.cpu_threads}")
    assert p_f64.cpu_threads <= 8, f"8 thread sınırı aşılamaz, alınan: {p_f64.cpu_threads}"

    # 1 çekirdekli sistem simülasyonu
    p_f1 = classify_hardware(
        logical_cpus=1,
        physical_cpus=1,
        total_ram_gb=4.0,
        available_ram_gb=2.0
    )
    print(f"1 Çekirdek Profil: {p_f1.name} | Threads: {p_f1.cpu_threads}")
    assert p_f1.cpu_threads == 1
    print(">>> CASE F BAŞARILI! <<<")

    # CASE G: Transcriber varsayılan olarak small + cpu + int8 başlatır
    print("\n--- CASE G: Transcriber Başlatma ve Donanım Entegrasyonu ---")
    transcriber = Transcriber()
    print(f"Transcriber Yapılandırması:")
    print(f"  Model       : {transcriber.model_name}")
    print(f"  Cihaz       : {transcriber.device}")
    print(f"  Compute     : {transcriber.compute_type}")
    print(f"  Beam        : {transcriber.beam_size}")
    print(f"  Threads     : {transcriber.cpu_threads}")
    print(f"  Profil Adı  : {transcriber.hardware_profile.name if transcriber.hardware_profile else 'None'}")
    
    assert transcriber.model_name == "small", "Model small olmalı"
    assert transcriber.device == "cpu", "Cihaz cpu olmalı"
    assert transcriber.compute_type == "int8", "Compute type int8 olmalı"
    assert transcriber.beam_size == 5, "Beam size 5 olmalı"
    assert transcriber.cpu_threads == 4, f"Bu makinede (8 çekirdek) 4 thread bekleniyordu, alınan: {transcriber.cpu_threads}"
    assert transcriber.hardware_profile.name == "BALANCED"
    print(">>> CASE G BAŞARILI! <<<")

    # CASE H: Profil önbelleği güvenle yazılır ve okunur
    print("\n--- CASE H: Profil Önbelleği Okuma/Yazma ve Bozuk Dosya Testi ---")
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_cache_file = os.path.join(tmpdir, "test_cache.json")
        sample_static = {
            "logical_cpus": 12,
            "physical_cpus": 6,
            "total_ram_gb": 32.0,
            "cpu_name": "Test CPU",
            "architecture": "AMD64",
            "platform_info": "Windows Test",
            "gpus": ["Test GPU"]
        }
        _save_cached_hardware(temp_cache_file, sample_static)
        assert os.path.isfile(temp_cache_file), "Önbellek dosyası oluşturulmalı"

        loaded = _load_cached_hardware(temp_cache_file)
        assert loaded is not None
        assert loaded["logical_cpus"] == 12
        assert loaded["total_ram_gb"] == 32.0
        assert loaded["profiler_version"] == 1

        # Bozuk JSON testi
        with open(temp_cache_file, "w", encoding="utf-8") as f:
            f.write("Bozuk JSON içeriği {{{")
        corrupted_loaded = _load_cached_hardware(temp_cache_file)
        assert corrupted_loaded is None, "Bozuk önbellek dosyası None dönmeli, hata fırlatmamalı"
    print(">>> CASE H BAŞARILI! <<<")

    print("\n" + "=" * 60)
    print("TÜM DONANIM PROFİLİ TESTLERİ (CASE A - H) EKSİKSİZ GEÇTİ!")
    print("=" * 60)

if __name__ == "__main__":
    run_hardware_profiler_tests()

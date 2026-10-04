"""
engine/hardware.py: Otomatik donanım tespiti, CPU profil sınıflandırması ve güvenli thread seçimi.

Gizlilik & Güvenlik Kuralı:
- Yalnızca teknik donanım metrikleri tespit edilir ve loglanır.
- Asla kullanıcı dosyaları, ses içerikleri veya transkript metinleri okunmaz/kaydedilmez.
- Donanım tespiti hatası uygulamanın başlamasını ASLA engellemez (güvenli fallback).

Profiller:
- LOW: 2-4 çekirdek veya kritik düzeyde düşük kullanılabilir RAM (<2.5 GB) -> 2 thread
- BALANCED: 6-8 çekirdek, dengeli RAM -> 4 thread
- HIGH: 12+ çekirdek, 16+ GB RAM, sağlıklı kullanılabilir RAM -> 6-8 thread (azami 8)

Tüm profiller üretim motorunun kararlı temelini korur:
model="small", device="cpu", compute_type="int8"
"""

import os
import sys
import json
import platform
import datetime
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any, Tuple

try:
    import psutil
except ImportError:
    psutil = None

from .logging_config import get_logger

logger = get_logger()

PROFILER_VERSION = 1
HARD_MAX_CPU_THREADS = 8


@dataclass
class HardwareProfile:
    """Sistem donanım profilini ve CTranslate2 kaynak yapılandırmasını temsil eder."""
    name: str                # "LOW", "BALANCED", "HIGH"
    cpu_threads: int         # 2, 4, 6, 8
    logical_cpus: int
    physical_cpus: int
    total_ram_gb: float
    available_ram_gb: float
    cpu_name: str
    architecture: str
    platform_info: str
    gpus: List[str]
    reason: str
    cached: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def get_hardware_cache_path() -> str:
    """Donanım profili önbellek dosya yolunu döner."""
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        cache_dir = os.path.join(local_app_data, "Transkript")
    else:
        cache_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.makedirs(cache_dir, exist_ok=True)
    return os.path.join(cache_dir, "hardware_profile.json")


def _detect_cpu_name() -> str:
    """Windows kayıt defteri veya platform üzerinden CPU modelini güvenle tespit eder."""
    if platform.system() == "Windows":
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
            )
            cpu_name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            winreg.CloseKey(key)
            if cpu_name and cpu_name.strip():
                return cpu_name.strip()
        except Exception:
            pass

    return platform.processor() or "Bilinmeyen CPU"


def _detect_gpus() -> List[str]:
    """
    Windows üzerinde ekran kartı üreticilerini güvenle tespit eder (ileride kullanım için).
    Mevcut çıkarımı veya backend seçimini etkilemez.
    """
    gpus: List[str] = []
    if platform.system() == "Windows":
        try:
            import winreg
            key_path = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path)
            i = 0
            while True:
                try:
                    subkey_name = winreg.EnumKey(key, i)
                    i += 1
                    if subkey_name.isdigit():
                        subkey = winreg.OpenKey(key, subkey_name)
                        try:
                            desc, _ = winreg.QueryValueEx(subkey, "DriverDesc")
                            if desc and desc not in gpus:
                                gpus.append(str(desc))
                        except Exception:
                            pass
                        finally:
                            winreg.CloseKey(subkey)
                except OSError:
                    break
            winreg.CloseKey(key)
        except Exception:
            pass

    return gpus


def _query_live_available_ram_gb() -> float:
    """Sistemin anlık kullanılabilir RAM miktarını GB cinsinden döner."""
    if psutil is not None:
        try:
            return round(psutil.virtual_memory().available / (1024 ** 3), 2)
        except Exception:
            pass
    return 4.0  # Güvenli varsayılan


def _query_static_hardware() -> Dict[str, Any]:
    """Değişmeyen statik donanım özelliklerini sorgular."""
    logical = os.cpu_count() or 4
    physical = logical
    total_ram = 8.0

    if psutil is not None:
        try:
            logical = psutil.cpu_count(logical=True) or logical
            physical = psutil.cpu_count(logical=False) or physical
            total_ram = round(psutil.virtual_memory().total / (1024 ** 3), 2)
        except Exception as e:
            logger.warning("psutil donanım sorgusu hatası: %s", e)

    return {
        "logical_cpus": logical,
        "physical_cpus": physical,
        "total_ram_gb": total_ram,
        "cpu_name": _detect_cpu_name(),
        "architecture": platform.machine() or "x86_64",
        "platform_info": f"{platform.system()} {platform.release()} ({platform.version()})",
        "gpus": _detect_gpus(),
    }


def classify_hardware(
    logical_cpus: int,
    physical_cpus: int,
    total_ram_gb: float,
    available_ram_gb: float,
    cpu_name: str = "",
    architecture: str = "",
    platform_info: str = "",
    gpus: Optional[List[str]] = None,
    cached: bool = False
) -> HardwareProfile:
    """
    Donanım ve anlık bellek durumuna göre LOW / BALANCED / HIGH profilini belirler.
    
    Kurallar:
    1. Ham Donanım Adayı:
       - 12+ mantıksal çekirdek ve 15+ GB toplam RAM -> HIGH
       - 6-8 mantıksal çekirdek ve 7+ GB toplam RAM  -> BALANCED
       - Diğer durumlar                             -> LOW
       
    2. Anlık Kullanılabilir Bellek Düşürme (Downgrade) Koruması:
       - Boş RAM < 2.5 GB: Donanım ne olursa olsun LOW (2 thread)
       - Boş RAM < 5.0 GB: HIGH adayı ise BALANCED (4 thread) seviyesine indirilir
       
    3. Thread Güvenlik Sınırları:
       - LOW: 2 thread (tek çekirdekse 1)
       - BALANCED: 4 thread
       - HIGH: 6 thread (16+ çekirdek ve 8+ GB boş RAM varsa 8 thread)
       - Asla 8 thread aşılmaz.
       - Asla tüm çekirdekler tüketilmez; OS ve WebView2 için çekirdek payı bırakılır.
    """
    gpus = gpus or []

    # 1. Ham donanıma göre başlangıç adayı
    if logical_cpus >= 12 and total_ram_gb >= 15.0:
        candidate = "HIGH"
    elif logical_cpus >= 6 and total_ram_gb >= 7.0:
        candidate = "BALANCED"
    else:
        candidate = "LOW"

    # 2. Anlık boş RAM koruması ve nihai profil seçimi
    if available_ram_gb < 2.5:
        profile_name = "LOW"
        threads = 2 if logical_cpus >= 2 else 1
        if candidate != "LOW":
            reason = (
                f"Kritik düzeyde düşük kullanılabilir bellek ({available_ram_gb:.1f} GB < 2.5 GB) "
                f"nedeniyle {candidate} yerine güvenli LOW (2 thread) seçildi."
            )
        else:
            reason = f"Temel donanım ({logical_cpus} mantıksal CPU, {total_ram_gb:.1f} GB RAM) doğrultusunda LOW seçildi."

    elif available_ram_gb < 5.0:
        if candidate == "HIGH":
            profile_name = "BALANCED"
            threads = 4
            reason = (
                f"Kısıtlı kullanılabilir bellek ({available_ram_gb:.1f} GB < 5.0 GB) "
                f"nedeniyle HIGH yerine BALANCED (4 thread) seçildi."
            )
        elif candidate == "BALANCED":
            profile_name = "BALANCED"
            threads = 4
            reason = (
                f"Dengeli modern donanım ({logical_cpus} mantıksal CPU, {total_ram_gb:.1f} GB RAM, "
                f"{available_ram_gb:.1f} GB boş) doğrultusunda BALANCED seçildi."
            )
        else:
            profile_name = "LOW"
            threads = 2 if logical_cpus >= 2 else 1
            reason = f"Temel donanım ({logical_cpus} mantıksal CPU, {total_ram_gb:.1f} GB RAM) doğrultusunda LOW seçildi."

    else:
        # Sağlıklı boş RAM (>= 5.0 GB)
        profile_name = candidate
        if profile_name == "HIGH":
            threads = 8 if (logical_cpus >= 16 and available_ram_gb >= 8.0) else 6
            reason = (
                f"Yüksek performanslı donanım ({logical_cpus} mantıksal CPU, {total_ram_gb:.1f} GB RAM, "
                f"{available_ram_gb:.1f} GB boş) doğrultusunda HIGH seçildi."
            )
        elif profile_name == "BALANCED":
            threads = 4
            reason = (
                f"Dengeli modern donanım ({logical_cpus} mantıksal CPU, {total_ram_gb:.1f} GB RAM, "
                f"{available_ram_gb:.1f} GB boş) doğrultusunda BALANCED seçildi."
            )
        else:
            profile_name = "LOW"
            threads = 2 if logical_cpus >= 2 else 1
            reason = f"Temel donanım ({logical_cpus} mantıksal CPU, {total_ram_gb:.1f} GB RAM) doğrultusunda LOW seçildi."

    # 3. Sert Güvenlik Tavanları
    # a. Asla 8 thread'i aşma
    threads = min(threads, HARD_MAX_CPU_THREADS)
    # b. Çekirdek sayısından fazla thread atama
    threads = min(threads, max(1, logical_cpus))
    # c. 4+ çekirdekli sistemlerde tüm çekirdekleri tüketme (en az 1-2 çekirdek boş bırak)
    if logical_cpus >= 4 and threads >= logical_cpus:
        threads = max(2, logical_cpus - 2)

    return HardwareProfile(
        name=profile_name,
        cpu_threads=threads,
        logical_cpus=logical_cpus,
        physical_cpus=physical_cpus,
        total_ram_gb=total_ram_gb,
        available_ram_gb=available_ram_gb,
        cpu_name=cpu_name,
        architecture=architecture,
        platform_info=platform_info,
        gpus=gpus,
        reason=reason,
        cached=cached
    )


def _load_cached_hardware(cache_path: str) -> Optional[Dict[str, Any]]:
    """Önbellekten statik donanım özelliklerini okur."""
    if not os.path.isfile(cache_path):
        return None
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("profiler_version") == PROFILER_VERSION and "logical_cpus" in data:
            return data
    except Exception as e:
        logger.warning("Donanım önbelleği okunamadı: %s", e)
    return None


def _save_cached_hardware(cache_path: str, static_info: Dict[str, Any]) -> None:
    """Statik donanım özelliklerini önbelleğe kaydeder."""
    try:
        payload = {
            "profiler_version": PROFILER_VERSION,
            "last_detected": datetime.datetime.now().isoformat(),
            **static_info
        }
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning("Donanım önbelleği yazılamadı: %s", e)


def detect_hardware_profile(force_refresh: bool = False) -> HardwareProfile:
    """
    Sistem donanım profilini tespit eder veya önbellekten okuyarak canlı RAM ile değerlendirir.
    
    Parametreler:
    - force_refresh: True ise önbelleğe bakılmaksızın tüm donanım baştan sorgulanır.
    
    Döner:
    - HardwareProfile nesnesi (LOW, BALANCED veya HIGH).
    
    Hata Toleransı:
    - Hiçbir istisna dışarı sızmaz; en kötü arıza durumunda güvenli BALANCED/LOW fallback döner.
    """
    cache_path = get_hardware_cache_path()

    try:
        static_info = None
        is_cached = False

        if not force_refresh:
            static_info = _load_cached_hardware(cache_path)
            if static_info:
                is_cached = True

        if not static_info:
            static_info = _query_static_hardware()
            _save_cached_hardware(cache_path, static_info)
            is_cached = False

        # Canlı anlık kullanılabilir bellek her zaman güncel sorgulanır
        live_available_ram = _query_live_available_ram_gb()

        profile = classify_hardware(
            logical_cpus=static_info.get("logical_cpus", os.cpu_count() or 4),
            physical_cpus=static_info.get("physical_cpus", os.cpu_count() or 4),
            total_ram_gb=static_info.get("total_ram_gb", 8.0),
            available_ram_gb=live_available_ram,
            cpu_name=static_info.get("cpu_name", "Bilinmeyen CPU"),
            architecture=static_info.get("architecture", platform.machine() or "x86_64"),
            platform_info=static_info.get("platform_info", ""),
            gpus=static_info.get("gpus", []),
            cached=is_cached
        )

        logger.info(
            "Donanım profili belirlendi: %s | CPU Threads: %d | Mantıksal Çekirdek: %d | Fiziksel: %d | RAM: %.1f GB (%.1f GB kullanılabilir) | Önbellek: %s",
            profile.name, profile.cpu_threads, profile.logical_cpus, profile.physical_cpus,
            profile.total_ram_gb, profile.available_ram_gb, profile.cached
        )
        logger.info("Donanım profil gerekçesi: %s", profile.reason)

        return profile

    except Exception as e:
        logger.exception("Donanım tespiti sırasında beklenmeyen hata: %s. Güvenli fallback uygulanıyor.", e)
        logical = os.cpu_count() or 4
        fallback_name = "BALANCED" if logical >= 6 else "LOW"
        fallback_threads = 4 if fallback_name == "BALANCED" else 2
        return HardwareProfile(
            name=fallback_name,
            cpu_threads=fallback_threads,
            logical_cpus=logical,
            physical_cpus=logical,
            total_ram_gb=8.0,
            available_ram_gb=4.0,
            cpu_name="Bilinmeyen CPU",
            architecture=platform.machine() or "x86_64",
            platform_info=f"{platform.system()} {platform.release()}",
            gpus=[],
            reason="Donanım tespiti başarısız oldu; sistem kararlılığı için güvenli fallback profili seçildi.",
            cached=False
        )

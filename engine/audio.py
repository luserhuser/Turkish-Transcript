"""
engine/audio.py: Ses dosyası doğrulama, süre ve format kontrolleri.
MP3, WAV, M4A formatlarını ve en fazla 2 saatlik (7200 sn) ses sınırını denetler.
PyAV tabanlı yerel çözümleme yapar, sistemde harici FFmpeg kurulumu gerektirmez.
"""

import os
from typing import Dict, Any, Tuple
import av

from .exceptions import (
    TranskriptError,
    AudioError,
    AudioFileNotFoundError,
    AudioAccessError,
    UnsupportedAudioFormatError,
    AudioCorruptedError,
    AudioDurationLimitError
)
from .logging_config import get_logger

logger = get_logger()

MAX_DURATION_SECONDS = 7200  # 2 saat sınırı
SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".m4a"}

# Geriye dönük uyumluluk için alias
AudioValidationError = AudioError


def inspect_audio(file_path: str) -> Dict[str, Any]:
    """
    Ses dosyasını inceler; formatını, süresini ve uygunluğunu doğrular.
    Geçersiz, bozuk veya 2 saati aşan kayıtlarda uygun AudioError alt sınıfını fırlatır.
    """
    if not file_path:
        raise AudioFileNotFoundError(file_path)

    # 1. Dosya varlığı kontrolü
    if not os.path.isfile(file_path):
        logger.warning("Dosya bulunamadı: %s", file_path)
        raise AudioFileNotFoundError(file_path)

    # 2. Dosya okunabilirlik / izin kontrolü
    if not os.access(file_path, os.R_OK):
        logger.warning("Dosyaya okuma izni yok: %s", file_path)
        raise AudioAccessError(file_path, "Okuma izni reddedildi.")

    # 3. Format / uzantı kontrolü
    _, ext = os.path.splitext(file_path)
    ext_lower = ext.lower()
    if ext_lower not in SUPPORTED_EXTENSIONS:
        logger.warning("Desteklenmeyen uzantı: %s (%s)", ext, file_path)
        raise UnsupportedAudioFormatError(ext)

    # 4. PyAV ile dosya akışını ve süresini çözümle
    try:
        with av.open(file_path, mode="r", metadata_errors="ignore") as container:
            audio_streams = [s for s in container.streams if s.type == "audio"]
            if not audio_streams:
                logger.warning("Geçerli ses akışı bulunamadı: %s", file_path)
                raise AudioCorruptedError("Dosyada geçerli bir ses akışı bulunamadı.")

            stream = audio_streams[0]
            duration_sec = 0.0
            if container.duration is not None:
                duration_sec = float(container.duration) / 1000000.0
            elif stream.duration is not None and stream.time_base is not None:
                duration_sec = float(stream.duration * stream.time_base)

            sample_rate = stream.sample_rate or 16000
            channels = stream.channels or 1

    except AudioError:
        raise
    except Exception as e:
        logger.exception("PyAV ses çözme hatası: %s", e)
        raise AudioCorruptedError(f"Ses akışı çözülemedi: {str(e)}")

    # 5. Süre kontrolü ve uzun kayıt uyarısı (2 saat üzeri dosyalar engellenmez, işleme devam edilir)
    warning_msg = None
    if duration_sec > MAX_DURATION_SECONDS:
        hours = duration_sec / 3600.0
        logger.warning(
            "Uzun süreli ses kaydı: %.1f saat (%s). İşlem süresi dosya uzunluğuna bağlı olarak artacaktır.",
            hours, file_path
        )
        warning_msg = f"Kayıt süresi 2 saatin üzerinde ({hours:.1f} saat). İşlem süresi bilgisayarınızın donanımına göre uzayabilir."

    try:
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    except Exception:
        file_size_mb = 0.0

    result = {
        "file_path": file_path,
        "file_name": os.path.basename(file_path),
        "extension": ext_lower,
        "duration_seconds": round(duration_sec, 2),
        "sample_rate": sample_rate,
        "channels": channels,
        "size_mb": round(file_size_mb, 2),
        "warning": warning_msg
    }

    logger.info(
        "Ses incelendi: %s | Süre: %.2f sn (%.2f dk) | Boyut: %.2f MB | %d Hz | %d kanal",
        result["file_name"], result["duration_seconds"], result["duration_seconds"] / 60.0,
        result["size_mb"], result["sample_rate"], result["channels"]
    )
    return result

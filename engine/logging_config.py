"""
engine/logging_config.py: Transkript için gizlilik odaklı, hafif yerel loglama yöneticisi.
ÖNEMLİ GİZLİLİK KURALI:
Hassas PDR danışma görüşmeleri içerdiği için ses dalgaları veya transkript metinleri
kesinlikle log dosyasına yazılmaz. Yalnızca model yükleme, donanım/thread seçimi,
dosya meta verileri (süre, boyut vb.) ve hata teşhis kayıtları tutulur.
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from typing import Optional

LOGGER_NAME = "transkript"

def get_log_dir() -> str:
    """Yerel log dizinini belirler ve oluşturur."""
    # Windows LocalAppData veya yerel çalışma dizini
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        log_dir = os.path.join(local_app_data, "Transkript", "logs")
    else:
        # Fallback: proje dizini içi
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
    
    os.makedirs(log_dir, exist_ok=True)
    return log_dir


def setup_logging(log_level: int = logging.INFO) -> logging.Logger:
    """
    Transkript teşhis loglayıcısını yapılandırır.
    Maksimum 5 MB boyutunda, 3 yedekli döner dosya (rotating handler) ve konsol çıktısı sağlar.
    """
    logger = logging.getLogger(LOGGER_NAME)
    if logger.handlers:
        return logger

    logger.setLevel(log_level)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s (%(threadName)s): %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 1. Konsol çıktısı
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 2. Döner dosya çıktısı
    try:
        log_dir = get_log_dir()
        log_file = os.path.join(log_dir, "transkript.log")
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=5 * 1024 * 1024, # 5 MB
            backupCount=3,
            encoding="utf-8"
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"[UYARI] Log dosyası oluşturulamadı: {e}", file=sys.stderr)

    logger.info("Transkript loglama sistemi başlatıldı.")
    return logger


def get_logger() -> logging.Logger:
    """Yapılandırılmış logger nesnesini döner."""
    return logging.getLogger(LOGGER_NAME)

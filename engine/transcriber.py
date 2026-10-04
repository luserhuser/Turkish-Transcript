"""
engine/transcriber.py: Üretim odaklı, kararlı, Türkçe optimize faster-whisper transkripsiyon motoru.
Gizlilik, uzun kayıt kararlılığı (azami 2 saat), güvenli CPU thread yönetimi,
incremental checkpoint kurtarma ve sınıflandırılmış hata yönetimi içerir.
"""

import os
import sys
import time
import threading
from typing import Callable, Optional, Dict, Any, Tuple, Iterable, List

from faster_whisper import WhisperModel
import ctranslate2

from .exceptions import (
    TranskriptError,
    AudioFileNotFoundError,
    AudioAccessError,
    ModelLoadError,
    InsufficientMemoryError,
    TranscriptionRuntimeError,
    TranscriptionCancelledError
)
from .checkpoint import TranscriptCheckpoint
from .logging_config import get_logger
from .hardware import HardwareProfile, detect_hardware_profile
from .domain_vocabulary import (
    build_hotwords,
    build_hotwords_list,
    get_default_pdr_terms,
    get_default_pdr_hotwords,
    get_targeted_pdr_terms,
    VALID_HOTWORD_MODES,
    DEFAULT_HOTWORD_MODE,
)

logger = get_logger()

# Varsayılan üretim parametreleri (Doğruluk ve donanım testleriyle belirlenmiştir)
DEFAULT_MODEL_NAME = "small"
DEFAULT_LANGUAGE = "tr"
DEFAULT_TASK = "transcribe"
DEFAULT_COMPUTE_TYPE = "int8"
DEFAULT_BEAM_SIZE = 5
DEFAULT_TEMPERATURE = 0.0
DEFAULT_CONDITION_ON_PREVIOUS_TEXT = False
DEFAULT_VAD_FILTER = True
DEFAULT_USE_DOMAIN_HOTWORDS = False
DEFAULT_HOTWORD_MODE = "off"
DEFAULT_VAD_PARAMS = dict(
    min_silence_duration_ms=500,
    speech_pad_ms=400,
)


def get_optimal_cpu_threads() -> int:
    """
    Sistem donanımına göre güvenli CPU iş parçacığı (threads) sayısını belirler.
    detect_hardware_profile() üzerinden otomatik profil ve RAM durumunu değerlendirir.
    """
    try:
        profile = detect_hardware_profile()
        return profile.cpu_threads
    except Exception as e:
        logger.warning("Otomatik thread belirleme hatası: %s, statik hesaba geçiliyor.", e)
        logical_cpus = os.cpu_count() or 4
        if logical_cpus <= 4:
            return max(1, min(2, logical_cpus))
        elif logical_cpus <= 8:
            return 4
        return min(8, max(4, logical_cpus // 2))


def resolve_model_path(model_name: str = "small") -> Tuple[str, bool]:
    """
    Model yolunu ve çevrimdışı çalışma modunu çözer.
    İleride Transkript-Setup.exe ile paketlenecek yerel model klasörlerini önceliklendirir.
    
    Kontrol Sırası:
    1. Çevre değişkeni (TRANSKRIPT_MODEL_DIR)
    2. PyInstaller bundle klasörü (sys._MEIPASS / models / model_name)
    3. Uygulama yerel modeller klasörü (<APP_DIR> / models / model_name)
    4. Kullanıcı yerel veri klasörü (%LOCALAPPDATA% / Transkript / models / model_name)
    5. Geliştirme ortamı: HuggingFace hub model adı (önbellek üzerinden)
    
    Döner: (model_path_veya_adi, local_files_only_bayragi)
    """
    app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates = []

    # 1. Çevre değişkeni
    env_dir = os.environ.get("TRANSKRIPT_MODEL_DIR")
    if env_dir:
        candidates.append(os.path.join(env_dir, model_name))
        candidates.append(env_dir)

    # 2. PyInstaller _MEIPASS
    if hasattr(sys, "_MEIPASS"):
        candidates.append(os.path.join(sys._MEIPASS, "models", model_name))

    # 3. Proje dizini içi models/
    candidates.append(os.path.join(app_dir, "models", model_name))

    # 4. LocalAppData
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        candidates.append(os.path.join(local_app_data, "Transkript", "models", model_name))

    for path in candidates:
        if os.path.isdir(path):
            # Model dosyaları (model.bin veya config.json) var mı kontrol et
            has_bin = os.path.isfile(os.path.join(path, "model.bin"))
            has_cfg = os.path.isfile(os.path.join(path, "config.json"))
            if has_bin or has_cfg:
                logger.info("Paketlenmiş yerel model bulundu (tamamen çevrimdışı): %s", path)
                return path, True

    # Yerel paket bulunamazsa geliştirme ortamı standart HF model adı kullanılır
    logger.info("Model adı olarak '%s' kullanılacak (HuggingFace önbelleği).", model_name)
    return model_name, False


class Transcriber:
    """
    Yerel Whisper transkripsiyon yöneticisi.
    Modeli bellekte tutar ve tekrar tekrar yüklemeyi önler.
    Güvenli thread seçimi, Silero VAD ve incremental kurtarma sağlar.
    """
    def __init__(
        self,
        model_name: str = DEFAULT_MODEL_NAME,
        device: str = "cpu",
        compute_type: str = DEFAULT_COMPUTE_TYPE,
        beam_size: int = DEFAULT_BEAM_SIZE,
        cpu_threads: Optional[int] = None,
        use_domain_hotwords: bool = DEFAULT_USE_DOMAIN_HOTWORDS,
        hotword_mode: str = DEFAULT_HOTWORD_MODE
    ):
        self.model_name = model_name
        self.beam_size = beam_size
        self.use_domain_hotwords = use_domain_hotwords
        self.hotword_mode = str(hotword_mode).lower().strip()

        # Otomatik donanım profili tespiti
        try:
            self.hardware_profile: Optional[HardwareProfile] = detect_hardware_profile()
        except Exception as e:
            logger.warning("Hardware profile tespiti hatası: %s", e)
            self.hardware_profile = None

        if cpu_threads is not None:
            self.cpu_threads = cpu_threads
        elif self.hardware_profile is not None:
            self.cpu_threads = self.hardware_profile.cpu_threads
        else:
            self.cpu_threads = get_optimal_cpu_threads()
        
        # Donanım tespiti ve güvenli CPU fallback
        self.device, self.compute_type = self._detect_hardware(preferred_device=device, preferred_compute=compute_type)
        
        self.model: Optional[WhisperModel] = None
        self._lock = threading.Lock()
        self._cancel_requested = False
        self._current_checkpoint: Optional[TranscriptCheckpoint] = None

        profile_label = self.hardware_profile.name if self.hardware_profile else "DEFAULT"
        logger.info(
            "Transcriber başlatıldı: Model='%s' | Cihaz='%s' | Compute='%s' | Profil='%s' | CPU Threads=%d | Beam=%d | HotwordMod='%s' | Hotwords=%s",
            self.model_name, self.device, self.compute_type, profile_label, self.cpu_threads, self.beam_size, self.hotword_mode, self.use_domain_hotwords
        )

    def _detect_hardware(self, preferred_device: str = "cpu", preferred_compute: str = "int8") -> Tuple[str, str]:
        """
        NVIDIA GPU ve CUDA kontrolü yapar.
        CUDA 12 DLL'leri eksikse veya GPU kullanılamazsa şeffaf ve güvenli biçimde CPU int8 fallback seçer.
        CPU her zaman garantili ve varsayılan çalışma yoludur.
        """
        if preferred_device == "cuda":
            try:
                cuda_count = ctranslate2.get_cuda_device_count()
                if cuda_count > 0:
                    # cublas64_12.dll kütüphanesinin çalışma zamanında gerçekten yüklenebilir olduğunu test et
                    import numpy as np
                    test_model = WhisperModel("tiny", device="cuda", compute_type="float16")
                    dummy_audio = np.zeros(16000, dtype=np.float32)
                    _ = list(test_model.transcribe(dummy_audio, vad_filter=False)[0])
                    del test_model
                    logger.info("CUDA GPU ivmelendirmesi doğrulandı ve etkinleştirildi.")
                    return "cuda", "float16"
            except Exception as e:
                logger.info("CUDA doğrulanamadı (%s), CPU moduna güvenle geçiliyor.", e)

        return "cpu", "int8"

    def load_model(self, on_status: Optional[Callable[[str], None]] = None) -> None:
        """
        Modeli diskten/cache'den yükler. Model zaten yüklüyse tekrar yüklemez (yeniden kullanım).
        Thread-safe olarak korunur.
        """
        with self._lock:
            if self.model is not None:
                return

            status_msg = f"Model yükleniyor ({self.model_name} - {self.device.upper()})..."
            logger.info(status_msg)
            if on_status:
                on_status(status_msg)

            model_path_or_name, is_local_files_only = resolve_model_path(self.model_name)
            load_start = time.perf_counter()

            try:
                self.model = WhisperModel(
                    model_path_or_name,
                    device=self.device,
                    compute_type=self.compute_type,
                    cpu_threads=self.cpu_threads,
                    num_workers=1,
                    local_files_only=is_local_files_only
                )
                load_duration = time.perf_counter() - load_start
                logger.info("Model başarıyla yüklendi (%.2f saniye): %s", load_duration, self.model_name)

            except MemoryError as e:
                logger.exception("Model yüklenirken yetersiz bellek hatası: %s", e)
                raise InsufficientMemoryError(f"Model yüklenirken RAM tükendi: {str(e)}")

            except Exception as e:
                err_str = str(e).lower()
                if "out of memory" in err_str or "cuda error: out of memory" in err_str:
                    logger.exception("Model yüklenirken OOM hatası: %s", e)
                    raise InsufficientMemoryError(str(e))

                # CUDA başarısız olduysa CPU int8 fallback dene
                if self.device == "cuda":
                    logger.warning("CUDA üzerinde model yüklenemedi (%s), CPU moduna geçiliyor...", e)
                    if on_status:
                        on_status("CUDA başlatılamadı, CPU moduna geçiliyor...")
                    self.device = "cpu"
                    self.compute_type = "int8"
                    try:
                        self.model = WhisperModel(
                            model_path_or_name,
                            device="cpu",
                            compute_type="int8",
                            cpu_threads=self.cpu_threads,
                            num_workers=1,
                            local_files_only=is_local_files_only
                        )
                        logger.info("Model CPU modunda başarıyla yüklendi: %s", self.model_name)
                        return
                    except Exception as cpu_err:
                        logger.exception("CPU fallback yüklemesi de başarısız oldu: %s", cpu_err)
                        raise ModelLoadError(self.model_name, str(cpu_err))

                logger.exception("Model yükleme hatası: %s", e)
                raise ModelLoadError(self.model_name, str(e))

    def cancel(self):
        """Devam eden transkripsiyon işlemini durdurma bayrağını kaldırır."""
        logger.info("Transkripsiyon iptal talebi alındı.")
        self._cancel_requested = True

    def transcribe(
        self,
        audio_path: str,
        total_duration: float,
        on_progress: Callable[[int, str, str], None],
        on_error: Optional[Callable[[str], None]] = None,
        use_domain_hotwords: Optional[bool] = None,
        hotword_mode: Optional[str] = None,
        custom_hotwords: Optional[Iterable[str]] = None
    ) -> str:
        """
        Ses dosyasını Türkçe olarak, Silero VAD filtrelemesi, PDR alan sözlüğü (hotwords)
        ve artımsal checkpoint kurtarma koruması ile metne dönüştürür.
        
        Parametreler:
        - audio_path: İşlenecek ses dosyası yolu
        - total_duration: Toplam süre (ilerleme yüzdesi hesabı için)
        - on_progress: Callback (yüzde, durum_mesajı, birikimli_metin)
        - on_error: Hata callback'i
        - use_domain_hotwords: Alan sözlüğü biasing aktif mi (None ise Transcriber varsayılanı)
        - hotword_mode: 'off', '5', '10', '20', 'full' (None ise Transcriber varsayılanı)
        - custom_hotwords: İsteğe bağlı özel terimler
        """
        self._cancel_requested = False

        if not os.path.isfile(audio_path):
            err = AudioFileNotFoundError(audio_path)
            logger.error(str(err))
            if on_error:
                on_error(err.user_message)
            raise err

        checkpoint = TranscriptCheckpoint()
        self._current_checkpoint = checkpoint
        checkpoint.start()

        transcribe_start_time = time.perf_counter()
        file_base_name = os.path.basename(audio_path)
        logger.info("Transkripsiyon başlatılıyor: %s (Toplam Süre: %.1f sn)", file_base_name, total_duration)

        collected_texts = []

        try:
            # 1. Modeli hazırla (varsa tekrar kullan, yoksa yükle)
            self.load_model(on_status=lambda msg: on_progress(5, msg, ""))

            on_progress(10, "Ses akışı hazırlanıyor...", "")

            # 2. Silero VAD yapılandırması (Kısık konuşmaları korumak için 400ms padding)
            vad_params = dict(
                min_silence_duration_ms=500,
                speech_pad_ms=400,
            ) if DEFAULT_VAD_FILTER else None

            # 3. PDR Alan Sözlüğü (Hotwords) Hazırlığı
            if hotword_mode is not None:
                active_mode = str(hotword_mode).lower().strip()
            elif use_domain_hotwords is not None:
                active_mode = "full" if use_domain_hotwords else "off"
            else:
                if self.hotword_mode != "off":
                    active_mode = self.hotword_mode
                elif self.use_domain_hotwords:
                    active_mode = "full"
                else:
                    active_mode = "off"

            hotwords_param: Optional[str] = None
            active_terms = build_hotwords_list(mode=active_mode, custom_terms=custom_hotwords)
            if active_terms:
                hotwords_param = " ".join(active_terms)
                logger.info(
                    "PDR alan sözlüğü (hotwords) devrede [Mod: %s] | Toplam terim sayısı: %d",
                    active_mode,
                    len(active_terms)
                )
            else:
                hotwords_param = None
                logger.info("PDR alan sözlüğü (hotwords) devre dışı [Mod: %s].", active_mode)

            # 4. faster-whisper transcribe çağrısı (Artımsal generator)
            segments, info = self.model.transcribe(
                audio_path,
                language=DEFAULT_LANGUAGE,
                task=DEFAULT_TASK,
                vad_filter=DEFAULT_VAD_FILTER,
                vad_parameters=vad_params,
                beam_size=self.beam_size,
                temperature=DEFAULT_TEMPERATURE,
                condition_on_previous_text=DEFAULT_CONDITION_ON_PREVIOUS_TEXT,
                hotwords=hotwords_param
            )

            audio_duration = total_duration if total_duration > 0 else (info.duration or 1.0)
            seg_count = 0
            last_log_time = time.time()

            # 5. Segment segment artımsal işleme
            for segment in segments:
                if self._cancel_requested:
                    logger.info("İşlem kullanıcı tarafından durduruldu (%d segment).", seg_count)
                    checkpoint.close_without_deletion()
                    current_text = " ".join(collected_texts).strip()
                    on_progress(0, "İşlem iptal edildi.", current_text)
                    return current_text

                text_part = segment.text.strip()
                if text_part:
                    collected_texts.append(text_part)
                    # Yerel kurtarma checkpoint'ine derhal flush et
                    checkpoint.append_segment(text_part)

                seg_count += 1
                curr_time = segment.end
                pct = min(98, max(12, int((curr_time / audio_duration) * 100)))
                current_full_text = " ".join(collected_texts)

                # UI'ı her segmentte artımsal olarak bilgilendir
                on_progress(pct, f"%{pct} tamamlandı", current_full_text)

                # Teşhis amaçlı hafif loglama (30 saniyede bir, metin içeriği yazılmadan)
                if time.time() - last_log_time > 30.0:
                    last_log_time = time.time()
                    logger.info(
                        "İlerleme: %%%d (%.1f / %.1f sn) | İşlenen segment: %d",
                        pct, curr_time, audio_duration, seg_count
                    )

            # 5. Başarılı bitiş
            elapsed_total = time.perf_counter() - transcribe_start_time
            rtf = elapsed_total / audio_duration if audio_duration > 0 else 0.0
            final_text = " ".join(collected_texts).strip()

            logger.info(
                "Transkripsiyon başarıyla tamamlandı: %s | Süre: %.2f sn (%.2f dk) | RTF: %.4f (%.2fx hız) | Segment: %d",
                file_base_name, elapsed_total, elapsed_total / 60.0, rtf, (1 / rtf if rtf > 0 else 0), seg_count
            )

            # Başarılı tamamlandığı için kurtarma dosyasını güvenle temizle
            checkpoint.cleanup()

            on_progress(100, "Transkripsiyon tamamlandı", final_text)
            return final_text

        except Exception as e:
            # Hata durumunda checkpoint dosyasını silmeden kapat (kısmi metin kurtarma)
            checkpoint.close_without_deletion()
            elapsed_err = time.perf_counter() - transcribe_start_time
            logger.exception("Transkripsiyon hatası (%.2f sn sonra): %s", elapsed_err, e)

            # Hatayı sınıflandır
            err_str = str(e).lower()
            if isinstance(e, TranskriptError):
                classified_err = e
            elif isinstance(e, (MemoryError,)) or "out of memory" in err_str:
                classified_err = InsufficientMemoryError(str(e))
            elif isinstance(e, (FileNotFoundError,)):
                classified_err = AudioFileNotFoundError(audio_path)
            elif isinstance(e, (PermissionError,)):
                classified_err = AudioAccessError(audio_path, str(e))
            else:
                has_partial = len(collected_texts) > 0
                classified_err = TranscriptionRuntimeError(str(e), partial_text_saved=has_partial)

            if on_error:
                on_error(classified_err.user_message)

            raise classified_err

        finally:
            self._current_checkpoint = None

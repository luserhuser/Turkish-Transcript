"""
engine paketi: Ses işleme ve Whisper transkripsiyon altyapısı.
"""
__version__ = "0.1.0"

from .audio import inspect_audio, AudioValidationError

from .transcriber import Transcriber, get_optimal_cpu_threads, resolve_model_path
from .exceptions import (
    TranskriptError,
    AudioError,
    AudioFileNotFoundError,
    AudioAccessError,
    UnsupportedAudioFormatError,
    AudioCorruptedError,
    AudioDurationLimitError,
    ModelError,
    ModelLoadError,
    InsufficientMemoryError,
    TranscriptionRuntimeError,
    TranscriptionCancelledError,
)
from .checkpoint import TranscriptCheckpoint, get_checkpoint_dir, detect_stale_checkpoints
from .logging_config import setup_logging, get_logger
from .hardware import HardwareProfile, detect_hardware_profile, get_hardware_cache_path
from .domain_vocabulary import (
    build_hotwords,
    build_hotwords_list,
    parse_custom_hotwords,
    get_default_pdr_terms,
    get_master_pdr_terms,
    get_targeted_pdr_terms,
    get_default_pdr_hotwords,
    get_category_breakdown,
    HIGH_PRIORITY_TERMS,
    PDR_HOTWORDS_5,
    PDR_HOTWORDS_10,
    PDR_HOTWORDS_20,
    VALID_HOTWORD_MODES,
    DEFAULT_HOTWORD_MODE,
)

__all__ = [
    "__version__",
    "inspect_audio",
    "AudioValidationError",

    "Transcriber",
    "get_optimal_cpu_threads",
    "resolve_model_path",
    "TranskriptError",
    "AudioError",
    "AudioFileNotFoundError",
    "AudioAccessError",
    "UnsupportedAudioFormatError",
    "AudioCorruptedError",
    "AudioDurationLimitError",
    "ModelError",
    "ModelLoadError",
    "InsufficientMemoryError",
    "TranscriptionRuntimeError",
    "TranscriptionCancelledError",
    "TranscriptCheckpoint",
    "get_checkpoint_dir",
    "detect_stale_checkpoints",
    "HardwareProfile",
    "detect_hardware_profile",
    "get_hardware_cache_path",
    "setup_logging",
    "get_logger",
    "build_hotwords",
    "build_hotwords_list",
    "parse_custom_hotwords",
    "get_default_pdr_terms",
    "get_master_pdr_terms",
    "get_targeted_pdr_terms",
    "get_default_pdr_hotwords",
    "get_category_breakdown",
    "HIGH_PRIORITY_TERMS",
    "PDR_HOTWORDS_5",
    "PDR_HOTWORDS_10",
    "PDR_HOTWORDS_20",
    "VALID_HOTWORD_MODES",
    "DEFAULT_HOTWORD_MODE",
]


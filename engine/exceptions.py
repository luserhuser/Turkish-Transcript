"""
engine/exceptions.py: Transkript hata sınıfları ve kullanıcı dostu hata sınıflandırması.
Son kullanıcıya teknik traceback yerine net, anlaşılır ve güven verici hata mesajları sunar.
"""

class TranskriptError(Exception):
    """Transkript temel hata sınıfı."""
    def __init__(self, user_message: str, technical_details: str = ""):
        super().__init__(user_message)
        self.user_message = user_message
        self.technical_details = technical_details

    def __str__(self):
        if self.technical_details:
            return f"{self.user_message} (Detay: {self.technical_details})"
        return self.user_message


class AudioError(TranskriptError):
    """Ses dosyası ile ilgili hataların temel sınıfı."""
    pass


class AudioFileNotFoundError(AudioError):
    def __init__(self, file_path: str = ""):
        msg = "Seçilen ses dosyası bulunamadı. Lütfen dosyanın taşınmadığından veya silinmediğinden emin olun."
        super().__init__(msg, f"Dosya yolu: {file_path}")


class AudioAccessError(AudioError):
    def __init__(self, file_path: str = "", details: str = ""):
        msg = "Ses dosyasına erişim izni yok. Dosya başka bir program tarafından kullanılıyor veya kilitli olabilir."
        super().__init__(msg, f"Dosya: {file_path} | {details}")


class UnsupportedAudioFormatError(AudioError):
    def __init__(self, extension: str = ""):
        msg = f"Desteklenmeyen dosya formatı ({extension}). Transkript şu anda MP3, WAV ve M4A formatlarını desteklemektedir."
        super().__init__(msg, f"Uzantı: {extension}")


class AudioCorruptedError(AudioError):
    def __init__(self, details: str = ""):
        msg = "Ses dosyası okunamadı veya bozuk. Dosyanın geçerli bir ses kaydı olduğundan emin olun."
        super().__init__(msg, details)


class AudioDurationLimitError(AudioError):
    def __init__(self, duration_hours: float = 0.0):
        msg = f"Dosya süresi 2 saatlik sınırı ({duration_hours:.1f} saat) aşmaktadır. V0 sürümünde en fazla 2 saatlik (7200 saniye) kayıtlar işlenebilir."
        super().__init__(msg, f"Süre: {duration_hours * 3600:.1f} saniye")


class ModelError(TranskriptError):
    """Yapay zekâ modeli yükleme ve yapılandırma hataları."""
    pass


class ModelLoadError(ModelError):
    def __init__(self, model_name: str = "", details: str = ""):
        msg = f"Transkripsiyon modeli ({model_name}) yüklenemedi. Lütfen disk alanınızı ve sistem kaynaklarınızı kontrol edin."
        super().__init__(msg, details)


class InsufficientMemoryError(ModelError):
    def __init__(self, details: str = ""):
        msg = "Sistem belleği (RAM) yetersiz. Lütfen açık olan diğer programları kapatıp tekrar deneyin."
        super().__init__(msg, details)


class TranscriptionRuntimeError(TranskriptError):
    def __init__(self, details: str = "", partial_text_saved: bool = False):
        if partial_text_saved:
            msg = "Transkripsiyon sırasında beklenmeyen bir hata oluştu. Hata anına kadar olan kısmi metin güvenle korundu."
        else:
            msg = "Transkripsiyon sırasında beklenmeyen bir hata oluştu."
        super().__init__(msg, details)


class TranscriptionCancelledError(TranskriptError):
    def __init__(self):
        super().__init__("Transkripsiyon işlemi iptal edildi.")

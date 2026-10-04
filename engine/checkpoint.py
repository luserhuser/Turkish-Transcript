r"""
engine/checkpoint.py: Uzun süreli ses kayıtlarında kısmi metin kurtarma mekanizması.

KURTARMA VERİSİ YAŞAM DÖNGÜSÜ VE GİZLİLİK POLİTİKASI:
1. Kayıt / Yazma: Transkripsiyon sırasında her konuşma segmenti tamamlandığında
   yerel diskteki oturum kurtarma dosyasına (%LOCALAPPDATA%\Transkript\recovery\recovery_<id>.txt)
   artımlı olarak yazılır ve anında diske flush edilir.
2. Silinme (Başarılı İşlem): Transkripsiyon %100 oranında tamamlandığında, kurtarma dosyası
   otomatik olarak güvenle diskten silinir (cleanup). Diskte gereksiz hassas metin bırakılmaz.
3. Saklanma (Hata / Kesinti / Çökme): Beklenmeyen elektrik kesintisi, işlem çökmesi,
   hata veya iptal durumunda kurtarma dosyası SİLİNMEZ (close_without_deletion). Kullanıcının
   dakikalarca süren görüşme metninin kaybolması önlenir.
4. Yeni Oturum Başlangıcı (Stale Recovery Tespiti): Yeni bir oturum başladığında
   detect_stale_checkpoints() fonksiyonu önceki oturumlardan kalan dosyaları güvenle tespit eder;
   ancak bu dosyaları ASLA sessizce silmez.
5. Gizlilik Koruması: Kurtarma metinleri asla log dosyalarına yazılmaz; buluta veya
   herhangi bir üçüncü taraf sunucuya aktarılmaz. Yalnızca geçerli Windows kullanıcısının
   yerel profil dizininde saklanır.
"""

import os
import time
import uuid
from typing import Optional, List, Dict, Any
from .logging_config import get_logger

logger = get_logger()

def get_checkpoint_dir() -> str:
    """Yerel kurtarma dizinini belirler ve oluşturur."""
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        recovery_dir = os.path.join(local_app_data, "Transkript", "recovery")
    else:
        recovery_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "recovery")
    
    os.makedirs(recovery_dir, exist_ok=True)
    return recovery_dir


def detect_stale_checkpoints() -> List[Dict[str, Any]]:
    """
    Önceki oturumlardan kalmış (çökme veya hata nedeniyle silinmemiş)
    kurtarma dosyalarını tespit eder.
    
    Gizlilik & Güvenlik Kuralı:
    - Kesinlikle dosya içeriklerini loglamaz.
    - Dosyaları sessizce silmez; kullanıcının kurtarılabilir verisini korur.
    
    Döner: [{'file_path': str, 'file_name': str, 'size_bytes': int, 'modified_time': float}, ...]
    """
    recovery_dir = get_checkpoint_dir()
    stale_files = []
    try:
        for fname in os.listdir(recovery_dir):
            if fname.startswith("recovery_") and fname.endswith(".txt"):
                fpath = os.path.join(recovery_dir, fname)
                try:
                    stat = os.stat(fpath)
                    stale_files.append({
                        "file_path": fpath,
                        "file_name": fname,
                        "size_bytes": stat.st_size,
                        "modified_time": stat.st_mtime
                    })
                except OSError:
                    continue
    except OSError as e:
        logger.warning("Kurtarma dizini taranamadı: %s", e)

    if stale_files:
        logger.info(
            "Önceki oturumlardan kalmış %d kurtarma dosyası tespit edildi. Dosyalar veri kaybını önlemek için saklanıyor.",
            len(stale_files)
        )
    return stale_files



class TranscriptCheckpoint:
    """
    Tek bir transkripsiyon oturumu için kurtarma checkpoint yöneticisi.
    """
    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or f"{int(time.time())}_{uuid.uuid4().hex[:8]}"
        self.checkpoint_dir = get_checkpoint_dir()
        self.file_path = os.path.join(self.checkpoint_dir, f"recovery_{self.session_id}.txt")
        self._file_handle = None
        self._segment_count = 0
        self._char_count = 0

    def start(self):
        """Kurtarma dosyasını açar."""
        try:
            self._file_handle = open(self.file_path, "w", encoding="utf-8")
            logger.info("Kurtarma checkpoint dosyası oluşturuldu: %s", os.path.basename(self.file_path))
        except Exception as e:
            logger.warning("Kurtarma dosyası açılamadı: %s", e)
            self._file_handle = None

    def append_segment(self, segment_text: str):
        """Üretilen yeni segment metnini dosyaya yazar ve diske flush eder."""
        if not self._file_handle or not segment_text:
            return

        try:
            # Segmenti tek satır olarak ekle ve boşluk bırak
            self._file_handle.write(segment_text.strip() + " ")
            self._file_handle.flush()
            self._segment_count += 1
            self._char_count += len(segment_text)
        except Exception as e:
            logger.warning("Checkpoint yazma hatası: %s", e)

    def get_recovered_text(self) -> str:
        """Dosyada birikmiş olan kurtarılmış metni okur."""
        if not os.path.isfile(self.file_path):
            return ""
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            return ""

    def cleanup(self):
        """
        Başarılı işlem sonrası geçici kurtarma dosyasını temizler.
        Kullanıcı gizliliğini korumak için diskte gereksiz hassas metin bırakmaz.
        """
        if self._file_handle:
            try:
                self._file_handle.close()
            except Exception:
                pass
            self._file_handle = None

        if os.path.isfile(self.file_path):
            try:
                os.remove(self.file_path)
                logger.info("Kurtarma checkpoint dosyası temizlendi (başarılı işlem): %s", os.path.basename(self.file_path))
            except Exception as e:
                logger.warning("Kurtarma dosyası silinirken hata: %s", e)

    def close_without_deletion(self):
        """Hata veya iptal anında dosyayı kapatır ancak diski silmez (kurtarma için bırakır)."""
        if self._file_handle:
            try:
                self._file_handle.close()
            except Exception:
                pass
            self._file_handle = None
        if os.path.isfile(self.file_path) and self._char_count > 0:
            logger.info(
                "Kısmi transkript korundu (%d segment, %d karakter): %s",
                self._segment_count, self._char_count, self.file_path
            )

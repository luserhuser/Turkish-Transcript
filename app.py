"""
app.py: Transkript Windows Masaüstü Uygulaması Giriş Noktası
pywebview (Microsoft Edge WebView2) tabanlı hafif masaüstü istemcisi.
"""

import os
import sys
import json
import threading
import webview

# Modül yolu
APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from engine import (
    inspect_audio,
    AudioValidationError,
    Transcriber,
    TranskriptError,
    detect_stale_checkpoints,
    setup_logging,
    get_logger,
    parse_custom_hotwords,
)

# Teşhis loglamasını başlat (Hassas transkript/ses verisi loglanmaz)
setup_logging()
logger = get_logger()

def _pick_file_native() -> str:
    """
    Windows üzerinde en kararlı yerel dosya seçiciyi açar.
    Topmost modunda açılarak pencerenin arkasında kalması engellenir.
    """
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.wm_attributes('-topmost', 1)
        filetypes = [
            ("Desteklenen Ses Dosyaları (*.mp3, *.wav, *.m4a)", "*.mp3 *.wav *.m4a"),
            ("MP3 Dosyaları (*.mp3)", "*.mp3"),
            ("WAV Dosyaları (*.wav)", "*.wav"),
            ("M4A Dosyaları (*.m4a)", "*.m4a"),
            ("Tüm Dosyalar (*.*)", "*.*")
        ]
        selected = filedialog.askopenfilename(
            title="Transkript — Ses Dosyası Seç",
            filetypes=filetypes
        )
        root.destroy()
        return selected or ""
    except Exception as e:
        logger.error("Dosya seçici açılamadı: %s", e)
        return ""


class DesktopApi:
    """
    Python backend ile JavaScript arayüzü arasındaki yerel API köprüsü.
    Yalnızca select_file ve start_transcription metotları JavaScript'e sunulur.
    Tüm dahili değişkenler alt çizgi (_) ile başlar.
    """
    def __init__(self):
        self._window = None
        self._selected_file_info = None
        self._transcriber = Transcriber(model_name="small")
        self._is_running = False
        self._active_custom_terms = []

        # Önceki oturumlardan kalmış kurtarma dosyalarını tespit et (güvenle koru)
        detect_stale_checkpoints()


    def _set_window(self, window):
        self._window = window

    def select_file(self):
        """
        Windows yerel dosya seçici penceresini açar ve seçilen dosyayı inceler.
        """
        logger.info("select_file çağrıldı.")
        
        # 1. En kararlı yerel dosya seçiciyi aç
        file_path = _pick_file_native()

        # 2. Tkinter seçici boş döndüyse veya iptal edildiyse, pywebview diyaloğunu dene
        if not file_path and self._window:
            try:
                file_types = (
                    "Ses Dosyalari (*.mp3;*.wav;*.m4a)",
                    "Tum Dosyalar (*.*)"
                )
                chosen = self._window.create_file_dialog(
                    webview.FileDialog.OPEN,
                    allow_multiple=False,
                    file_types=file_types
                )
                if chosen and len(chosen) > 0:
                    file_path = chosen[0]
            except Exception as e:
                logger.warning("pywebview dialog fallback hatası: %s", e)

        if not file_path:
            logger.info("Kullanıcı dosya seçmedi / iptal etti.")
            return {"success": False, "cancelled": True}

        logger.info("Seçilen dosya: %s", os.path.basename(file_path))

        try:
            info = inspect_audio(file_path)
            self._selected_file_info = info
            logger.info("Ses doğrulandı: %s (%.2f sn)", info['file_name'], info['duration_seconds'])
            return {
                "success": True,
                "info": info
            }
        except TranskriptError as e:
            logger.warning("Ses doğrulama hatası: %s", e)
            return {"success": False, "error": e.user_message}
        except Exception as e:
            logger.exception("Beklenmeyen hata: %s", e)
            return {"success": False, "error": "Ses dosyası incelenirken beklenmeyen bir hata oluştu."}

    def start_transcription(self, custom_terms: str = ""):
        """
        Transkripsiyon işlemini UI'ı dondurmamak için arka plan iş parçacığında başlatır.
        custom_terms: Kullanıcının UI'dan girdiği virgülle ayrılmış isteğe bağlı özel terimler.
        """
        if not self._selected_file_info:
            return {"success": False, "error": "Lütfen önce geçerli bir ses dosyası seçin."}

        if self._is_running:
            return {"success": False, "error": "Zaten devam eden bir işlem var."}

        # Özel terimleri temizle ve doğrula (kullanıcı girdisi gizliliği korunur)
        parsed = parse_custom_hotwords(custom_terms)
        self._active_custom_terms = parsed
        if parsed:
            logger.info("Özel terimler devrede | Terim sayısı: %d", len(parsed))
        else:
            logger.info("Özel terim girişi yok veya boş.")

        thread = threading.Thread(target=self._run_transcription_worker, daemon=True)
        thread.start()
        return {"success": True}

    def _run_transcription_worker(self):
        self._is_running = True
        audio_info = self._selected_file_info
        audio_path = audio_info["file_path"]
        duration = audio_info["duration_seconds"]

        logger.info("Transkripsiyon iş parçacığı başlatıldı: %s", audio_info['file_name'])

        def on_progress(percent: int, status: str, text: str):
            if not self._window:
                return
            js_code = (
                f"if (window.updateProgress) {{ "
                f"window.updateProgress({percent}, {json.dumps(status)}, {json.dumps(text)}); "
                f"}}"
            )
            try:
                self._window.evaluate_js(js_code)
            except Exception as js_err:
                logger.debug("updateProgress JS çağrısı başarısız: %s", js_err)

        try:
            self._transcriber.transcribe(
                audio_path=audio_path,
                total_duration=duration,
                on_progress=on_progress,
                custom_hotwords=self._active_custom_terms,
                hotword_mode="off"
            )
            logger.info("Transkripsiyon işi başarıyla tamamlandı: %s", audio_info['file_name'])
        except TranskriptError as e:
            logger.exception("Transkripsiyon hatası (sınıflandırılmış): %s", e)
            if self._window:
                err_code = (
                    f"if (window.onTranscriptionError) {{ "
                    f"window.onTranscriptionError({json.dumps(e.user_message)}); "
                    f"}}"
                )
                try:
                    self._window.evaluate_js(err_code)
                except Exception:
                    pass
        except Exception as e:
            logger.exception("Transkripsiyon hatası (beklenmeyen): %s", e)
            if self._window:
                generic_msg = "İşlem sırasında beklenmeyen bir hata oluştu. Lütfen log dosyasını inceleyin."
                err_code = (
                    f"if (window.onTranscriptionError) {{ "
                    f"window.onTranscriptionError({json.dumps(generic_msg)}); "
                    f"}}"
                )
                try:
                    self._window.evaluate_js(err_code)
                except Exception:
                    pass
        finally:
            self._is_running = False



def main():
    api = DesktopApi()
    ui_html_path = os.path.join(APP_DIR, "ui", "index.html")

    window = webview.create_window(
        title="Transkript",
        url=ui_html_path,
        js_api=api,
        width=880,
        height=720,
        min_size=(720, 500),
        background_color="#0c0f14"
    )
    api._set_window(window)

    # Windows Edge WebView2 GUI'sini başlat (debug loglaması açık)
    webview.start(debug=True)


if __name__ == "__main__":
    main()

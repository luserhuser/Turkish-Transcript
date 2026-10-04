"""
tests/test_ui_window.py:
WebView2 GUI penceresinin Windows üzerinde sorunsuz açılıp kapandığını doğrular.
"""

import os
import sys
import threading
import time
import webview

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app import DesktopApi

def test_gui_window():
    print("=" * 60)
    print("GUI PENCERE TESTİ (Edge WebView2)")
    print("=" * 60)

    api = DesktopApi()
    ui_html_path = os.path.join(ROOT_DIR, "ui", "index.html")

    window = webview.create_window(
        title="Transkript - Test",
        url=ui_html_path,
        js_api=api,
        width=880,
        height=720,
        min_size=(720, 500)
    )
    api._set_window(window)

    def close_timer():
        time.sleep(2)
        print("Pencere başarıyla açıldı, 2 sn sonra otomatik kapatılıyor...")
        window.destroy()

    threading.Thread(target=close_timer, daemon=True).start()
    webview.start(debug=False)
    print(">>> GUI PENCERESİ BAŞARIYLA BAŞLATILDI VE KAPATILDI! <<<")

if __name__ == "__main__":
    test_gui_window()

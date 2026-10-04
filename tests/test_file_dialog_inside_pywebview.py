"""
tests/test_file_dialog_inside_pywebview.py:
pywebview penceresi açıkken tkinter filedialog'un ve pywebview create_file_dialog'un
nasıl davrandığını test eder.
"""

import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog
import webview

def open_native_file_dialog():
    print("[NATIVE-DLG] Tkinter başlatılıyor...")
    root = tk.Tk()
    root.withdraw()
    root.wm_attributes('-topmost', 1)
    filetypes = [
        ("Desteklenen Ses Dosyaları", "*.mp3 *.wav *.m4a"),
        ("MP3 Dosyaları (*.mp3)", "*.mp3"),
        ("WAV Dosyaları (*.wav)", "*.wav"),
        ("M4A Dosyaları (*.m4a)", "*.m4a"),
        ("Tüm Dosyalar (*.*)", "*.*")
    ]
    print("[NATIVE-DLG] askopenfilename çağrılmaya hazır...")
    # Sadece test amaçlı, kullanıcı olmadan hemen kapatmak için timer
    def auto_close():
        time.sleep(1)
        print("[NATIVE-DLG] Test amaçlı pencere kapatılıyor...")
        root.quit()

    threading.Thread(target=auto_close, daemon=True).start()
    path = filedialog.askopenfilename(
        title="Ses Dosyası Seç",
        filetypes=filetypes
    )
    root.destroy()
    print(f"[NATIVE-DLG] Seçilen yol: {path}")
    return path

class Api:
    def __init__(self):
        self._window = None

    def test_tk(self):
        print("[API] test_tk çağrıldı!")
        p = open_native_file_dialog()
        return {"path": p}

def run():
    api = Api()
    w = webview.create_window("Dialog Test", html="<button onclick=\"window.pywebview.api.test_tk()\">Test</button>", js_api=api)
    api._window = w

    def trigger():
        time.sleep(2)
        print("[TRIGGER] JS üzerinden test_tk tetikleniyor...")
        res = w.evaluate_js("window.pywebview.api.test_tk()")
        print("[TRIGGER] evaluate_js sonucu:", res)
        time.sleep(2)
        w.destroy()

    threading.Thread(target=trigger, daemon=True).start()
    webview.start(debug=True)

if __name__ == "__main__":
    run()

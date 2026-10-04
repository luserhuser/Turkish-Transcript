"""
tests/test_direct_js_call.py:
window.pywebview.api.select_file() JavaScript çağrısını doğrudan çalıştırıp
Promise yanıtını veya hatasını yakalar.
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

def run():
    print("=" * 60)
    print("TEST: JS'den Doğrudan API Çağrısı")
    print("=" * 60)

    api = DesktopApi()
    ui_html_path = os.path.join(ROOT_DIR, "ui", "index.html")

    window = webview.create_window(
        title="Transkript - JS Test",
        url=ui_html_path,
        js_api=api,
        width=880,
        height=720
    )
    api._set_window(window)

    def tester():
        time.sleep(2)
        print("[TESTER] JS üzerinden window.pywebview.api.select_file() çağrılıyor...")
        js_code = """
        (async () => {
            try {
                console.log('[JS] Calling select_file()...');
                const p = window.pywebview.api.select_file();
                console.log('[JS] select_file() returned promise:', p);
                const res = await p;
                console.log('[JS] select_file() resolved with:', res);
                return { success: true, result: res };
            } catch (err) {
                console.error('[JS] select_file() error:', err);
                return { success: false, error: err.message, stack: err.stack };
            }
        })()
        """
        eval_res = window.evaluate_js(js_code)
        print(f"[TESTER] JS Değerlendirme Sonucu: {eval_res}")

        time.sleep(2)
        window.destroy()

    threading.Thread(target=tester, daemon=True).start()
    webview.start(debug=True)

if __name__ == "__main__":
    run()

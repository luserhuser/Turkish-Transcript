"""
tests/test_api_flow.py:
DesktopApi ve arayüz köprüsünün simüle edilmiş tam akış testi.
"""

import os
import sys
import time

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app import DesktopApi

class MockWindow:
    def __init__(self):
        self.js_calls = []
        self.file_to_pick = None

    def create_file_dialog(self, *args, **kwargs):
        return [self.file_to_pick] if self.file_to_pick else []

    def evaluate_js(self, js_code):
        self.js_calls.append(js_code)

def test_full_desktop_api_flow():
    print("=" * 60)
    print("DESKTOP API TAM AKIŞ TESTİ")
    print("=" * 60)

    api = DesktopApi()
    mock_window = MockWindow()
    api._set_window(mock_window)

    sample_counseling = os.path.join(ROOT_DIR, "tests", "sample_counseling_2m.mp3")
    mock_window.file_to_pick = sample_counseling

    # Otomatik test ortamında GUI Tkinter dosya seçici penceresinin kullanıcı tıklaması beklemesini engelle
    import app
    app._pick_file_native = lambda: sample_counseling

    # 1. Dosya seçimi çağrısı
    select_res = api.select_file()
    print("1. Dosya Seçim Yanıtı:", select_res)
    assert select_res["success"] is True
    assert select_res["info"]["duration_seconds"] > 60

    # 2. Transkripsiyonu başlat
    start_res = api.start_transcription()
    print("2. Transkripsiyon Başlatma Yanıtı:", start_res)
    assert start_res["success"] is True

    # Arka plan thread'inin bitmesini bekle
    print("3. Arka plan işlemi bekleniyor...")
    while api._is_running:
        time.sleep(0.5)

    print(f"Toplam evaluate_js çağrı sayısı: {len(mock_window.js_calls)}")
    assert len(mock_window.js_calls) > 5, "En az 5 ilerleme bildirimi gelmeli"

    # Son bildirimde %100 ve tamamlandı olmalı
    last_call = mock_window.js_calls[-1]
    print("Son evaluate_js bildirimi (kısaltılmış):", last_call[:120], "...")
    assert "100" in last_call or "tamamlandı" in last_call

    print("\n>>> DESKTOP API TAM AKIŞ TESTİ BAŞARIYLA GEÇTİ! <<<")

if __name__ == "__main__":
    test_full_desktop_api_flow()

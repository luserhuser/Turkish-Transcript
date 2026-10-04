"""
tests/test_redesign_ui.py:
Transkript V0 Yeni Sinematik Arayüz (Frontend Redesign) Doğrulama Testi.
- 32-bar dalga formu kontrolü
- Boş durum (empty state) ve görünürlük mantığı
- Bilgi ve Gizlilik çekmeceleri etkileşimi (Workflow / Privacy drawers)
- Harici bağımlılık / CDN sıfır tolerans kontrolü
- DOM kimliklerinin (ID) tam korunumu
"""

import os
import sys
import json
import time
import threading
import webview

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app import DesktopApi

def test_frontend_redesign():
    print("=" * 60)
    print("YENİ SİNEMATİK ÖN YÜZ (FRONTEND REDESIGN) ETKİLEŞİM TESTİ")
    print("=" * 60)

    # 1. Statik Dosya İncelemesi: Harici CDN / URL kontrolü
    html_file = os.path.join(ROOT_DIR, "ui", "index.html")
    with open(html_file, "r", encoding="utf-8") as f:
        html_content = f.read()

    assert "http://" not in html_content and "https://" not in html_content, "UI dosyalarında hiçbir harici CDN veya URL bulunmamalıdır! %100 yerel ve çevrimdışı olmalı."
    print("[OK] Harici CDN / Uzak URL içermeme kuralı doğrulandı (100% Yerel).")

    api = DesktopApi()
    window = webview.create_window(
        title="Transkript - Redesign Test",
        url=html_file,
        js_api=api,
        width=900,
        height=750
    )
    api._set_window(window)

    results = {}

    def worker():
        try:
            time.sleep(2.0)

            # 2. Hero Ses Sahnesi ve 32 Dalga Çubuğu
            wave_bar_count = window.evaluate_js("document.querySelectorAll('.wave-bar').length")
            print(f"[OK] Dalga formu çubuk sayısı: {wave_bar_count}")
            assert wave_bar_count == 32, f"Beklenen 32 dalga çubuğu, bulunan: {wave_bar_count}"
            results["wave_bars"] = "PASS"

            # Hero başlangıç durumu
            hero_is_idle = window.evaluate_js("document.getElementById('audioHeroCard').classList.contains('state-idle')")
            assert hero_is_idle is True, "Hero kartı başlangıçta state-idle olmalı"
            results["hero_initial_state"] = "PASS"

            # 3. Boş Durum (Empty State) Testi
            empty_state_visible = window.evaluate_js("!document.getElementById('transcriptEmptyState').classList.contains('hidden-state')")
            assert empty_state_visible is True, "Başlangıçta transkript boş durumu görünür olmalı"
            
            # Metin eklendiğinde boş durumun gizlenmesi ve sayaç testi
            window.evaluate_js("""
            (() => {
                const ta = document.getElementById('transcriptText');
                ta.value = "Danışan görüşmeye zamanında katıldı.";
                ta.dispatchEvent(new Event('input'));
            })()
            """)
            time.sleep(0.2)
            empty_state_hidden = window.evaluate_js("document.getElementById('transcriptEmptyState').classList.contains('hidden-state')")
            assert empty_state_hidden is True, "Metin varken boş durum gizlenmelidir (.hidden-state)"

            counter_text = window.evaluate_js("document.getElementById('transcriptLiveStats').textContent")
            print(f"[OK] Canlı sayaç: '{counter_text}'")
            assert "karakter" in counter_text
            results["empty_state_morph"] = "PASS"

            # Metin temizlendiğinde boş durumun geri gelmesi
            window.evaluate_js("""
            (() => {
                const ta = document.getElementById('transcriptText');
                ta.value = "";
                ta.dispatchEvent(new Event('input'));
            })()
            """)
            time.sleep(0.2)
            empty_state_restored = window.evaluate_js("!document.getElementById('transcriptEmptyState').classList.contains('hidden-state')")
            assert empty_state_restored is True, "Metin temizlenince boş durum geri gelmeli"

            # 4. Çekmeceler (Workflow & Privacy Drawers) Etkileşim Testi
            # Başlangıçta paneller kapalı olmalı
            wf_hidden = window.evaluate_js("document.getElementById('panelWorkflow').classList.contains('hidden')")
            priv_hidden = window.evaluate_js("document.getElementById('panelPrivacy').classList.contains('hidden')")
            assert wf_hidden and priv_hidden, "Başlangıçta çekmeceler kapalı olmalı"

            # Workflow butonuna tıkla
            window.evaluate_js("document.getElementById('btnToggleWorkflow').click()")
            time.sleep(0.2)
            wf_open = window.evaluate_js("!document.getElementById('panelWorkflow').classList.contains('hidden')")
            wf_btn_active = window.evaluate_js("document.getElementById('btnToggleWorkflow').classList.contains('active-pill')")
            assert wf_open and wf_btn_active, "Workflow paneli açılmalı ve butonu aktifleşmeli"
            print("[OK] 'Nasıl çalışır?' çekmecesi başarıyla açıldı.")

            # Privacy butonuna tıkla -> Workflow kapanmalı, Privacy açılmalı
            window.evaluate_js("document.getElementById('btnTogglePrivacy').click()")
            time.sleep(0.2)
            wf_closed = window.evaluate_js("document.getElementById('panelWorkflow').classList.contains('hidden')")
            priv_open = window.evaluate_js("!document.getElementById('panelPrivacy').classList.contains('hidden')")
            priv_btn_active = window.evaluate_js("document.getElementById('btnTogglePrivacy').classList.contains('active-pill')")
            assert wf_closed and priv_open and priv_btn_active, "Privacy paneli açılırken Workflow kapanmalı"
            print("[OK] 'Gizlilik ve Etik' çekmecesi başarıyla açıldı ve diğeri kapandı.")

            # Kapatma butonuyla (✕) kapat
            window.evaluate_js("document.querySelector('#panelPrivacy .drawer-close-btn').click()")
            time.sleep(0.2)
            priv_closed = window.evaluate_js("document.getElementById('panelPrivacy').classList.contains('hidden')")
            priv_btn_inactive = window.evaluate_js("!document.getElementById('btnTogglePrivacy').classList.contains('active-pill')")
            assert priv_closed and priv_btn_inactive, "Çekmece kapatma butonu çekmeceyi gizlemelidir"
            print("[OK] Cekmece kapatma butonu (X) basariyla calisti.")
            results["drawers_interaction"] = "PASS"

            # 5. Gerekli DOM ID'lerinin Eksiksiz Varlığı
            required_ids = [
                "btnSelectFile", "selectedFileName", "fileMeta",
                "customTerms", "btnTranscribe", "progressSection",
                "statusMessage", "progressPercent", "progressBar",
                "errorMessage", "transcriptText", "btnCopy"
            ]
            for elem_id in required_ids:
                exists = window.evaluate_js(f"!!document.getElementById('{elem_id}')")
                assert exists is True, f"Kritik UI ID eksik: {elem_id}"
            print("[OK] Tüm zorunlu DOM ID'leri eksiksiz korundu.")
            results["required_dom_ids"] = "PASS"

            results["status"] = "ALL_PASS"
            print("\n>>> TÜM YENİ ARAYÜZ DOĞRULAMA TESTLERİ BAŞARIYLA GEÇTİ! <<<")

        except Exception as e:
            print(f"[TEST HATA] {e}")
            import traceback
            traceback.print_exc()
            results["status"] = f"FAIL: {e}"
        finally:
            window.destroy()

    threading.Thread(target=worker, daemon=True).start()
    webview.start(debug=False)
    return results

if __name__ == "__main__":
    res = test_frontend_redesign()
    print("Sonuç:", res)
    assert res.get("status") == "ALL_PASS"

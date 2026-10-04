"""
tests/test_full_ui_interaction.py:
Gerçek WebView2 penceresi açıkken tüm UI yaşam döngüsünü ve regression adımlarını test eder:
1. Pencere açılışı ve köprü kurulumu
2. İlk dosya seçimi ve transkripsiyon (sample_counseling_2m.mp3)
3. DOM güncellemelerinin (progress bar, yüzdelik, metin alanı) doğrulanması
4. İkinci dosya seçimi ve transkripsiyon (sample_15s.mp3) - Regression testi
5. Kopyala ve temizleme durumu
"""

import os
import sys
import threading
import time
import json
import webview

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app import DesktopApi
from engine import inspect_audio

def run_regression_and_ui_test():
    print("=" * 60)
    print("GERÇEK DESKTOP UI VE REGRESSION TESTİ")
    print("=" * 60)

    api = DesktopApi()
    ui_html_path = os.path.join(ROOT_DIR, "ui", "index.html")

    window = webview.create_window(
        title="Transkript - Regression Test",
        url=ui_html_path,
        js_api=api,
        width=880,
        height=720
    )
    api._set_window(window)

    test_results = {}

    def test_worker():
        try:
            print("[TEST] 1. WebView2 ve köprü hazırlığı bekleniyor...")
            time.sleep(2.5)

            # Köprü kontrolü
            bridge_ready = window.evaluate_js("window.pywebview && !!window.pywebview.api")
            print(f"[TEST] Köprü hazır mı: {bridge_ready}")
            assert bridge_ready is True, "pywebview.api hazır değil!"
            test_results["bridge_ready"] = "PASS"

            # Özel Terimler (customTerms) DOM elemanı kontrolü
            custom_terms_info = window.evaluate_js("""
            (() => {
                const el = document.getElementById('customTerms');
                return JSON.stringify({
                    exists: !!el,
                    value: el ? el.value : null,
                    placeholder: el ? el.placeholder : null,
                    disabled: el ? el.disabled : null
                });
            })()
            """)
            terms_data = json.loads(custom_terms_info)
            print(f"[TEST] customTerms DOM: {terms_data}")
            assert terms_data["exists"] is True, "customTerms DOM elemanı bulunamadı!"
            assert terms_data["value"] == "", "customTerms varsayılan değeri boş string olmalıdır!"
            assert "Alkü" in terms_data["placeholder"], "customTerms placeholder metni doğru olmalıdır!"
            test_results["custom_terms_dom"] = "PASS"

            # 2. Aşama: İlk Dosyayı Seç (sample_counseling_2m.mp3)
            sample_2m = os.path.join(ROOT_DIR, "tests", "sample_counseling_2m.mp3")
            info_2m = inspect_audio(sample_2m)
            api._selected_file_info = info_2m

            # UI'a dosya seçimini yansıt
            inject_file_js = f"""
            (() => {{
                const info = {json.dumps(info_2m)};
                document.getElementById('selectedFileName').textContent = info.file_name;
                document.getElementById('selectedFileName').classList.add('active');
                document.getElementById('fileMeta').textContent = 'Süre: 1 dk 47 sn | Format: MP3';
                document.getElementById('btnTranscribe').disabled = false;
                return true;
            }})()
            """
            window.evaluate_js(inject_file_js)
            btn_enabled = window.evaluate_js("!document.getElementById('btnTranscribe').disabled")
            print(f"[TEST] 2. Dosya yüklendi, Dönüştür butonu aktif mi: {btn_enabled}")
            assert btn_enabled is True
            test_results["file_selection_ui"] = "PASS"

            # 3. Aşama: Transkripsiyonu Başlat (Boş özel terimler ile baseline doğrulaması)
            print("[TEST] 3. 'Metne Dönüştür' butonu tıklanıyor...")
            click_transcribe_js = """
            (() => {
                document.getElementById('btnTranscribe').click();
                return true;
            })()
            """
            window.evaluate_js(click_transcribe_js)
            time.sleep(0.5)

            # Transkripsiyon sırasında customTerms'in disabled olduğunu doğrula
            terms_disabled = window.evaluate_js("document.getElementById('customTerms').disabled")
            assert terms_disabled is True, "Transkripsiyon sırasında customTerms disabled olmalıdır!"
            test_results["custom_terms_disabled_during_run"] = "PASS"

            # Arka plan transkripsiyonunu ve DOM güncellemelerini bekle
            print("[TEST] Transkripsiyon ilerlemesi DOM üzerinden izleniyor...")
            last_pct = 0
            for _ in range(140): # Azami 70 saniye (small modeli için güvenli süre)
                time.sleep(0.5)
                dom_status = window.evaluate_js("""
                (() => {
                    return JSON.stringify({
                        percent: document.getElementById('progressPercent').textContent,
                        status: document.getElementById('statusMessage').textContent,
                        textLength: document.getElementById('transcriptText').value.length,
                        copyEnabled: !document.getElementById('btnCopy').disabled
                    });
                })()
                """)
                data = json.loads(dom_status)
                pct_str = data["percent"].replace("%", "")
                if pct_str.isdigit():
                    curr_pct = int(pct_str)
                    if curr_pct != last_pct:
                        print(f"  [DOM İlerleme] {data['percent']} - {data['status']} | Metin: {data['textLength']} kr")
                        last_pct = curr_pct

                if curr_pct >= 100:
                    break

            print("[TEST] İlk transkripsiyon bitti. DOM kontrol ediliyor...")
            final_text = window.evaluate_js("document.getElementById('transcriptText').value")
            assert len(final_text) > 100, "Transkript metni boş veya çok kısa!"
            assert "psikolojik" in final_text.lower() or "hoş geldiniz" in final_text.lower() or "ayşe" in final_text.lower()
            test_results["first_transcription"] = "PASS"

            # Model instance ID'sini kaydet
            model_id_before = id(api._transcriber.model)
            assert api._transcriber.model is not None, "Model nesnesi hafızada olmalı"

            # 4. Aşama: Regression Testi — İkinci Dosyayı Seç ve İşle (sample_15s.mp3)
            print("\n[TEST] 4. REGRESSION: İkinci dosya seçiliyor (sample_15s.mp3)...")
            sample_15s = os.path.join(ROOT_DIR, "tests", "sample_15s.mp3")
            info_15s = inspect_audio(sample_15s)
            api._selected_file_info = info_15s

            inject_second_file_js = f"""
            (() => {{
                const info = {json.dumps(info_15s)};
                document.getElementById('selectedFileName').textContent = info.file_name;
                document.getElementById('fileMeta').textContent = 'Süre: 9 sn | Format: MP3';
                document.getElementById('btnTranscribe').disabled = false;
                return true;
            }})()
            """
            window.evaluate_js(inject_second_file_js)
            # İkinci transkripsiyonda özel terim girişi simülasyonu
            window.evaluate_js("document.getElementById('customTerms').value = 'Rehberlik, Danışma Merkezi';")
            print("[TEST] İkinci transkripsiyon başlatılıyor (Özel terimler girildi)...")
            window.evaluate_js("document.getElementById('btnTranscribe').click();")
            time.sleep(0.5)
            assert api._active_custom_terms == ["Rehberlik", "Danışma Merkezi"], f"Özel terimler doğru ayrıştırılmalı, alınan: {api._active_custom_terms}"

            for _ in range(60): # 30 saniye
                time.sleep(0.5)
                dom_status = window.evaluate_js("""
                (() => {
                    return JSON.stringify({
                        percent: document.getElementById('progressPercent').textContent,
                        status: document.getElementById('statusMessage').textContent,
                        textLength: document.getElementById('transcriptText').value.length
                    });
                })()
                """)
                data = json.loads(dom_status)
                if data["percent"] == "%100":
                    break

            final_text_2 = window.evaluate_js("document.getElementById('transcriptText').value")
            print(f"[TEST] İkinci transkript tamamlandı ({len(final_text_2)} kr): \"{final_text_2}\"")
            assert "psikolojik" in final_text_2.lower()
            test_results["second_transcription_regression"] = "PASS"

            # Model Reuse doğrulaması
            model_id_after = id(api._transcriber.model)
            assert model_id_before == model_id_after, "Model yeniden yüklenmemeli, bellekten tekrar kullanılmalı!"
            print(f">>> MODEL REUSE DOĞRULANDI (Model ID: {model_id_before} == {model_id_after}) <<<")
            test_results["model_reuse"] = "PASS"

            print("\n[TEST] 5. Kopyala butonu kontrolü...")
            copy_enabled = window.evaluate_js("!document.getElementById('btnCopy').disabled")
            assert copy_enabled is True
            test_results["copy_button_state"] = "PASS"

            print("\n" + "=" * 60)
            print("TÜM REGRESSION VE UI ENTEGRASYON TESTLERİ BAŞARIYLA TAMAMLANDI!")
            print("=" * 60)
            test_results["overall"] = "PASS"

        except Exception as e:
            print(f"\n[TEST HATA] {e}")
            import traceback
            traceback.print_exc()
            test_results["overall"] = f"FAIL: {e}"
        finally:
            time.sleep(1)
            window.destroy()

    threading.Thread(target=test_worker, daemon=True).start()
    webview.start(debug=False)

    return test_results

if __name__ == "__main__":
    results = run_regression_and_ui_test()
    print("Test Sonuç Tablosu:", results)

"""
tests/test_domain_vocabulary.py: PDR Alan Sözlüğü (Hotwords) Kapsamlı Test Paketi.

Test Edilen Durumlar:
1. 5'li hedef küme terim sayısı ve içeriği
2. 10'lu hedef küme terim sayısı ve kümülatif sıralaması
3. 20'li hedef küme terim sayısı ve kümülatif sıralaması
4. 111 terimlik ana master sözlüğün korunması
5. Kümelerde Türkçe karakterlerin (ç, ğ, ı, ö, ş, ü, İ) eksiksiz korunması
6. Boş dize veya yalnızca boşluk içeren elemanların temizlenmesi
7. Tekrarlanan terimlerin ayıklanması (deduplication)
8. hotword_mode seçimi ('off', '5', '10', '20', 'full')
9. 'off' modunda varsayılan olarak boş liste / None üretilmesi
10. 'off' modunda custom_terms verildiğinde yalnızca özel terimlerin üretilmesi
11. Hedefli modlarda custom_terms verildiğinde özel terimlerin en başa eklenmesi
12. Geçersiz hotword_mode durumunda ValueError fırlatılması
13. Transcriber varsayılanlarının use_domain_hotwords=False ve hotword_mode='off' olması
"""

import sys
import os
import unittest
from typing import List

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from engine.domain_vocabulary import (
    PDR_HOTWORDS_5,
    PDR_HOTWORDS_10,
    PDR_HOTWORDS_20,
    HIGH_PRIORITY_TERMS,
    VALID_HOTWORD_MODES,
    DEFAULT_HOTWORD_MODE,
    get_default_pdr_terms,
    get_master_pdr_terms,
    get_targeted_pdr_terms,
    get_default_pdr_hotwords,
    build_hotwords,
    build_hotwords_list,
    parse_custom_hotwords,
    get_category_breakdown,
)
from engine.transcriber import Transcriber


class TestDomainVocabulary(unittest.TestCase):
    """PDR sözlük ve hedefli hotword kümesi testleri."""

    def test_01_targeted_sets_counts(self):
        """5, 10 ve 20'li hedefli kümelerin tam sayıları ve tekrarsızlığı doğrulanmalıdır."""
        self.assertEqual(len(PDR_HOTWORDS_5), 5, "5'li küme tam 5 terim içermelidir.")
        self.assertEqual(len(PDR_HOTWORDS_10), 10, "10'lu küme tam 10 terim içermelidir.")
        self.assertEqual(len(PDR_HOTWORDS_20), 20, "20'li küme tam 20 terim içermelidir.")

        # Her küme kendi içinde benzersiz olmalı
        self.assertEqual(len(PDR_HOTWORDS_5), len(set(PDR_HOTWORDS_5)))
        self.assertEqual(len(PDR_HOTWORDS_10), len(set(PDR_HOTWORDS_10)))
        self.assertEqual(len(PDR_HOTWORDS_20), len(set(PDR_HOTWORDS_20)))

    def test_02_targeted_sets_cumulative_ordering(self):
        """Kümeler kümülatif olmalıdır (5, 10'un öneki; 10, 20'nin öneki olmalıdır)."""
        # İlk 5 terim 10'luda ve 20'lide aynı sırada olmalı
        self.assertEqual(PDR_HOTWORDS_10[:5], PDR_HOTWORDS_5)
        self.assertEqual(PDR_HOTWORDS_20[:10], PDR_HOTWORDS_10)

    def test_03_master_111_vocabulary_preserved(self):
        """111 terimlik referans master PDR sözlüğü eksiksiz korunmalıdır."""
        master = get_master_pdr_terms()
        self.assertEqual(len(master), 111, "Master sözlük 111 terim içermelidir.")
        self.assertEqual(len(master), len(set(master)), "Master sözlükte tekrar bulunmamalıdır.")

    def test_04_turkish_characters_preserved_in_subsets(self):
        """Hedefli kümelerdeki Türkçe karakterler bozulmadan korunmalıdır."""
        expected_chars = ["terapötik", "psikoeğitim", "bilişsel çarpıtma", "öz şefkat", "aydınlatılmış onam", "içgörü"]
        hotwords_20 = build_hotwords(mode="20")
        for term in expected_chars:
            self.assertIn(term, hotwords_20, f"Türkçe terim eksik veya karakter bozulmuş: {term}")

    def test_05_no_empty_or_whitespace_terms(self):
        """Hedefli kümelerde boş veya yalnızca boşluk içeren terim olmamalıdır."""
        for t in PDR_HOTWORDS_20:
            self.assertTrue(t.strip())
            self.assertEqual(t, t.strip())

    def test_06_hotword_mode_selection(self):
        """get_targeted_pdr_terms modu doğru çözümlemelidir."""
        self.assertEqual(get_targeted_pdr_terms("off"), [])
        self.assertEqual(get_targeted_pdr_terms("5"), PDR_HOTWORDS_5)
        self.assertEqual(get_targeted_pdr_terms("10"), PDR_HOTWORDS_10)
        self.assertEqual(get_targeted_pdr_terms("20"), PDR_HOTWORDS_20)
        self.assertEqual(len(get_targeted_pdr_terms("full")), 111)

    def test_07_off_mode_behavior(self):
        """Varsayılan 'off' modu hiçbir PDR terimi üretmemeli ve None dönmelidir."""
        terms = build_hotwords_list(mode="off")
        self.assertEqual(terms, [])
        hw_str = build_hotwords(mode="off")
        self.assertIsNone(hw_str, "Off modunda hotwords stringi None olmalıdır.")

    def test_08_custom_terms_with_off_mode(self):
        """'off' modunda custom_terms verilirse yalnızca özel terimler dönmelidir."""
        custom = ["Dr. Ahmet Yılmaz", "RAM Rehberlik"]
        terms = build_hotwords_list(mode="off", custom_terms=custom)
        self.assertEqual(terms, custom)

        hw_str = build_hotwords(mode="off", custom_terms=custom)
        self.assertEqual(hw_str, "Dr. Ahmet Yılmaz RAM Rehberlik")
        self.assertNotIn("terapötik", hw_str)

    def test_09_custom_terms_with_targeted_modes(self):
        """Hedefli modlarda custom_terms başa eklenmeli ve PDR terimleri arkasında yer almalıdır."""
        custom = ["Hacettepe Üniversitesi", "Dr. Ayşe"]
        terms = build_hotwords_list(mode="5", custom_terms=custom)
        self.assertEqual(len(terms), 7)
        self.assertEqual(terms[0], "Hacettepe Üniversitesi")
        self.assertEqual(terms[1], "Dr. Ayşe")
        self.assertEqual(terms[2:], PDR_HOTWORDS_5)

    def test_10_custom_terms_deduplication(self):
        """Özel terimlerdeki tekrarlar ve boşluklar temizlenmelidir."""
        custom = ["terapötik", "Özel_Klinik", "Özel_Klinik", "  ", ""]
        terms = build_hotwords_list(mode="5", custom_terms=custom)
        # 'terapötik' hem custom hem 5'te var, tekilleştirilmeli
        self.assertEqual(terms.count("terapötik"), 1)
        self.assertEqual(terms.count("Özel_Klinik"), 1)
        self.assertNotIn("", terms)
        self.assertNotIn("  ", terms)

    def test_11_invalid_mode_handling(self):
        """Geçersiz mod verildiğinde ValueError fırlatılmalıdır."""
        with self.assertRaises(ValueError):
            get_targeted_pdr_terms("invalid_mode_123")

        with self.assertRaises(ValueError):
            build_hotwords_list(mode="unsupported_999")

    def test_12_transcriber_defaults(self):
        """Transcriber sınıfının varsayılan olarak hotwords kapalı (off) başladığını doğrular."""
        t_default = Transcriber(model_name="tiny")
        self.assertFalse(t_default.use_domain_hotwords, "Üretim varsayılanı False olmalı.")
        self.assertEqual(t_default.hotword_mode, "off", "Üretim varsayılan hotword_mode 'off' olmalı.")

        t_5 = Transcriber(model_name="tiny", hotword_mode="5")
        self.assertEqual(t_5.hotword_mode, "5")

    def test_13_category_breakdown_metrics(self):
        """Kategori dökümü istatistikleri ve hedef küme boyutları doğru raporlanmalıdır."""
        breakdown = get_category_breakdown()
        self.assertEqual(breakdown["TOTAL_UNIQUE_TERMS"], 111)
        self.assertEqual(breakdown["PDR_HOTWORDS_5"], 5)
        self.assertEqual(breakdown["PDR_HOTWORDS_10"], 10)
        self.assertEqual(breakdown["PDR_HOTWORDS_20"], 20)

    def test_14_parse_custom_hotwords_comprehensive(self):
        """parse_custom_hotwords fonksiyonunun tüm sınır durumları ve temizlik kuralları test edilir."""
        # CASE A: Normal virgüllü girdi
        raw_a = "Alkü, Alanya Alaaddin Keykubat Üniversitesi, terapötik ittifak, ghostlamak"
        res_a = parse_custom_hotwords(raw_a)
        self.assertEqual(res_a, [
            "Alkü",
            "Alanya Alaaddin Keykubat Üniversitesi",
            "terapötik ittifak",
            "ghostlamak"
        ])

        # CASE B: Boş, None, sadece boşluk veya geçersiz tip
        self.assertEqual(parse_custom_hotwords(""), [])
        self.assertEqual(parse_custom_hotwords("   \t  \n  "), [])
        self.assertEqual(parse_custom_hotwords(None), [])
        self.assertEqual(parse_custom_hotwords(12345), [])  # type: ignore

        # CASE C: Tekrarlanan terimler (Deduplication)
        raw_c = "terapötik, ittifak, terapötik, ittifak, empati"
        res_c = parse_custom_hotwords(raw_c)
        self.assertEqual(res_c, ["terapötik", "ittifak", "empati"])

        # CASE D: Aşırı, ardışık ve baştaki/sondaki virgüller
        raw_d = ",,,terapötik,,, ittifak,   ,"
        res_d = parse_custom_hotwords(raw_d)
        self.assertEqual(res_d, ["terapötik", "ittifak"])

        # CASE E: Türkçe karakterlerin ve büyük/küçük harf durumunun korunması
        raw_e = "Şevket, Çağdaş, İbrahim, öz şefkat, Ömer, Iğdır"
        res_e = parse_custom_hotwords(raw_e)
        self.assertEqual(res_e, ["Şevket", "Çağdaş", "İbrahim", "öz şefkat", "Ömer", "Iğdır"])

        # CASE F: Yeni satır (\n, \r) ve noktalı virgül (;) içeren çok satırlı girdi
        raw_f = "Alkü\nAlanya Alaaddin Keykubat Üniversitesi;\nterapötik ittifak\r\nghostlamak"
        res_f = parse_custom_hotwords(raw_f)
        self.assertEqual(res_f, [
            "Alkü",
            "Alanya Alaaddin Keykubat Üniversitesi",
            "terapötik ittifak",
            "ghostlamak"
        ])

        # CASE G: 20'den fazla terim (max_terms sınırı)
        raw_g = ", ".join([f"terim_{i}" for i in range(1, 35)])
        res_g = parse_custom_hotwords(raw_g)
        self.assertEqual(len(res_g), 20, "20'den fazla terim 20 ile sınırlandırılmalıdır.")
        self.assertEqual(res_g[0], "terim_1")
        self.assertEqual(res_g[-1], "terim_20")

        # CASE H: 100 karakterden uzun terim (max_term_length sınırı)
        long_term = "A" * 150
        raw_h = f"kısa terim, {long_term}, normal terim"
        res_h = parse_custom_hotwords(raw_h)
        self.assertEqual(len(res_h), 3)
        self.assertEqual(res_h[0], "kısa terim")
        self.assertEqual(len(res_h[1]), 100)
        self.assertEqual(res_h[1], "A" * 100)
        self.assertEqual(res_h[2], "normal terim")


if __name__ == "__main__":
    unittest.main()

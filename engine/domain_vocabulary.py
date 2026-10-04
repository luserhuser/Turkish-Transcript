"""
engine/domain_vocabulary.py: Türkçe PDR ve Psikolojik Danışma Alan Sözlüğü.

faster-whisper'ın `hotwords` parametresi aracılığıyla Whisper modelini
günlük konuşmada az rastlanan, telaffuzu kolay karışabilen ve mesleki/akademik
açıdan kritik PDR terimlerine karşı hassaslaştırır.

Gizlilik & Güvenlik Kuralı:
- Kesinlikle genel metin tahrifatı (rewriting) veya LLM sonrası düzeltme yapılmaz.
- Model yalnızca bilinen terimlere doğru hafifçe yönlendirilir (decoder prior biasing).
- Kişi isimleri veya kullanıcıya özel hassas kelimeler varsayılan sözlüğe yazılmaz.
"""

from typing import List, Optional, Iterable, Dict
import re

# ============================================================================
# KATEGORİSEL PDR VE PSİKOLOJİK DANIŞMA TERİMLERİ
# ============================================================================

# 1. PDR Temel Terimleri (Mesleki Çerçeve ve Etik)
PDR_CORE_TERMS: List[str] = [
    "psikolojik danışma",
    "psikolojik danışman",
    "psikolojik danışmanlık",
    "psikolojik danışma ve rehberlik",
    "PDR",
    "danışan",
    "danışman",
    "görüşme",
    "oturum",
    "seans",
    "gizlilik",
    "mahremiyet",
    "aydınlatılmış onam",
]

# 2. Terapötik Süreç ve İlişki Terimleri
THERAPEUTIC_TERMS: List[str] = [
    "terapötik",
    "terapötik ilişki",
    "terapötik ittifak",
    "terapötik bağ",
    "terapötik süreç",
    "terapötik müdahale",
]

# 3. Danışma Becerileri ve Müdahaleler
COUNSELING_SKILLS: List[str] = [
    "empati",
    "etkin dinleme",
    "aktif dinleme",
    "yansıtma",
    "duygu yansıtma",
    "içerik yansıtma",
    "özetleme",
    "yeniden çerçeveleme",
    "yüzleştirme",
    "somutlaştırma",
    "kendini açma",
    "açık uçlu soru",
    "kapalı uçlu soru",
]

# 4. Bilişsel Davranışçı Terimler (BDT / CBT)
CBT_TERMS: List[str] = [
    "biliş",
    "bilişsel",
    "bilişsel çarpıtma",
    "bilişsel yeniden yapılandırma",
    "otomatik düşünce",
    "ara inanç",
    "temel inanç",
    "işlevsel düşünce",
    "işlevsiz düşünce",
    "ruminasyon",
    "felaketleştirme",
    "genelleme",
    "zihin okuma",
    "seçici soyutlama",
]

# 5. Duygu ve Davranış Düzenleme
EMOTION_BEHAVIOR_TERMS: List[str] = [
    "duygu düzenleme",
    "öz düzenleme",
    "kaçınma",
    "pekiştirme",
    "davranışsal aktivasyon",
    "maruz bırakma",
    "duyarsızlaştırma",
    "baş etme",
    "baş etme becerileri",
]

# 6. Benlik ve Öz Algı Terimleri
SELF_CONCEPT_TERMS: List[str] = [
    "benlik",
    "benlik algısı",
    "benlik saygısı",
    "öz saygı",
    "öz yeterlik",
    "öz şefkat",
    "öz farkındalık",
    "içgörü",
]

# 7. Kaygı ve Duygudurum Terimleri
ANXIETY_MOOD_TERMS: List[str] = [
    "anksiyete",
    "depresyon",
    "depresif",
    "panik atak",
    "tükenmişlik",
    "irritabilite",
    "çökkünlük",
    "umutsuzluk",
]

# 8. Travma, Kriz ve Yas Terimleri
TRAUMA_CRISIS_TERMS: List[str] = [
    "travma",
    "travmatik",
    "travma sonrası stres",
    "tetikleyici",
    "dissosiyasyon",
    "disosiyatif",
    "kriz",
    "krize müdahale",
    "yas",
    "kayıp",
    "uyum",
]

# 9. Psikoeğitim ve Rahatlama Teknikleri
PSYCHOEDUCATION_TERMS: List[str] = [
    "psikoeğitim",
    "nefes egzersizi",
    "gevşeme egzersizi",
    "farkındalık",
    "mindfulness",
    "topraklama",
    "imgeleme",
]

# 10. İlişki ve Aile Dinamikleri
RELATIONSHIP_FAMILY_TERMS: List[str] = [
    "ebeveyn",
    "ebeveynlik",
    "bağlanma",
    "güvenli bağlanma",
    "kaygılı bağlanma",
    "kaçıngan bağlanma",
    "sınır koyma",
    "sosyal destek",
]

# 11. Eğitim, Kariyer ve Sınav Kaygısı
EDUCATION_CAREER_TERMS: List[str] = [
    "kariyer danışmanlığı",
    "mesleki rehberlik",
    "kariyer gelişimi",
    "meslek seçimi",
    "sınav kaygısı",
    "akademik kaygı",
    "performans kaygısı",
]

# 12. Değerlendirme ve Vaka Formülasyonu
ASSESSMENT_TERMS: List[str] = [
    "psikolojik değerlendirme",
    "değerlendirme görüşmesi",
    "ölçek",
    "envanter",
    "vaka",
    "vaka formülasyonu",
    "formülasyon",
]

# ============================================================================
# YÜKSEK ÖNCELİKLİ (HATA PAYI YÜKSEK) TERİMLER
# ============================================================================
# Whisper context penceresinde (223 token sınırı) daima ilk sırada yer alması
# hedeflenen, akustik olarak kolay bozulabilen özel klinik kavramlar.
HIGH_PRIORITY_TERMS: List[str] = [
    "terapötik",
    "terapötik ittifak",
    "psikoeğitim",
    "bilişsel",
    "bilişsel çarpıtma",
    "ruminasyon",
    "anksiyete",
    "dissosiyasyon",
    "duyarsızlaştırma",
    "maruz bırakma",
    "davranışsal aktivasyon",
    "öz yeterlik",
    "öz şefkat",
    "içgörü",
    "somutlaştırma",
    "yüzleştirme",
    "yeniden çerçeveleme",
    "aydınlatılmış onam",
    "vaka formülasyonu",
    "duygu düzenleme",
]

# ============================================================================
# HEDEFLENMİŞ PDR DENEYSEL HOTWORD KÜMELERİ (5 / 10 / 20 TERİM)
# ============================================================================

# 1. 5'li Hedef Küme (Yalnızca en kritik, fonetik olarak en zor klinik terimler)
PDR_HOTWORDS_5: List[str] = [
    "terapötik",
    "psikoeğitim",
    "ruminasyon",
    "dissosiyasyon",
    "vaka formülasyonu",
]

# 2. 10'lu Hedef Küme (Kümülatif: 5'li küme + 5 yeni kritik terim)
PDR_HOTWORDS_10: List[str] = PDR_HOTWORDS_5 + [
    "terapötik ittifak",
    "bilişsel çarpıtma",
    "davranışsal aktivasyon",
    "öz şefkat",
    "aydınlatılmış onam",
]

# 3. 20'li Hedef Küme (Kümülatif: 10'lu küme + 10 yeni klinik terim)
PDR_HOTWORDS_20: List[str] = PDR_HOTWORDS_10 + [
    "anksiyete",
    "duyarsızlaştırma",
    "maruz bırakma",
    "öz yeterlik",
    "içgörü",
    "somutlaştırma",
    "yüzleştirme",
    "yeniden çerçeveleme",
    "duygu düzenleme",
    "bilişsel yeniden yapılandırma",
]

# Desteklenen Hotword Modları ve Varsayılan
VALID_HOTWORD_MODES = ("off", "5", "10", "20", "full")
DEFAULT_HOTWORD_MODE = "off"

# Tüm kategorilerin listesi
ALL_CATEGORIES: List[List[str]] = [
    PDR_CORE_TERMS,
    THERAPEUTIC_TERMS,
    COUNSELING_SKILLS,
    CBT_TERMS,
    EMOTION_BEHAVIOR_TERMS,
    SELF_CONCEPT_TERMS,
    ANXIETY_MOOD_TERMS,
    TRAUMA_CRISIS_TERMS,
    PSYCHOEDUCATION_TERMS,
    RELATIONSHIP_FAMILY_TERMS,
    EDUCATION_CAREER_TERMS,
    ASSESSMENT_TERMS,
]


def get_default_pdr_terms() -> List[str]:
    """
    Tüm kategorilerden 111 terimlik ana master PDR sözlüğünü döner.
    Geriye dönük uyumluluk ve tam sözlük referansı için korunmaktadır.
    """
    seen = set()
    ordered_terms: List[str] = []

    # 1. Yüksek öncelikli terimler daima en başta
    for term in HIGH_PRIORITY_TERMS:
        cleaned = term.strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            ordered_terms.append(cleaned)

    # 2. Kategorilerdeki diğer tüm terimler
    for category in ALL_CATEGORIES:
        for term in category:
            cleaned = term.strip()
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                ordered_terms.append(cleaned)

    return ordered_terms


def get_master_pdr_terms() -> List[str]:
    """111 terimlik referans master PDR sözlüğünü döner."""
    return get_default_pdr_terms()


def get_targeted_pdr_terms(mode: str = "off") -> List[str]:
    """
    Belirtilen moda göre hedeflenmiş PDR terimleri listesini döner.
    Modlar:
    - 'off': Boş liste [] (Varsayılan üretim davranışı)
    - '5': PDR_HOTWORDS_5 (5 terim)
    - '10': PDR_HOTWORDS_10 (10 terim)
    - '20': PDR_HOTWORDS_20 (20 terim)
    - 'full': MASTER_PDR_TERMS (111 terimlik tam sözlük)
    Geçersiz mod verilirse ValueError fırlatır.
    """
    mode_str = str(mode).lower().strip()
    if mode_str in ("off", "none", "false"):
        return []
    elif mode_str == "5":
        return list(PDR_HOTWORDS_5)
    elif mode_str == "10":
        return list(PDR_HOTWORDS_10)
    elif mode_str == "20":
        return list(PDR_HOTWORDS_20)
    elif mode_str in ("full", "111", "all", "true"):
        return get_default_pdr_terms()
    else:
        raise ValueError(f"Geçersiz hotword_mode: '{mode}'. Desteklenen modlar: {VALID_HOTWORD_MODES}")


def build_hotwords_list(
    mode: str = "off",
    custom_terms: Optional[Iterable[str]] = None
) -> List[str]:
    """
    Seçilen moda ait terimleri ve isteğe bağlı custom_terms girdilerini
    tekilleştirilmiş deterministik bir liste halinde birleştirir.
    
    Kurallar:
    - Varsa özel terimleri (isimler, kurumlar vb.) en başa alır.
    - Boşlukları temizler (strip) ve boş girdileri eler.
    - Tekrarları (duplicates) kaldırır.
    - Türkçe karakterleri (`ç`, `ğ`, `ı`, `ö`, `ş`, `ü`, `İ`) eksiksiz korur.
    - mode='off' ise ve özel terim yoksa boş liste döner.
    """
    # Geriye dönük uyumluluk: Eğer mode pozisyonel olarak custom_terms yerine geçildiyse
    if isinstance(mode, (list, tuple, set)) and custom_terms is None:
        custom_terms = mode
        mode = "off"

    seen = set()
    terms: List[str] = []

    # 1. Varsa özel terimler (kullanıcı/kurum adları)
    if custom_terms:
        for ct in custom_terms:
            if ct and isinstance(ct, str):
                cleaned = ct.strip()
                if cleaned and cleaned not in seen:
                    seen.add(cleaned)
                    terms.append(cleaned)

    # 2. Seçilen moda ait PDR terimleri
    for dt in get_targeted_pdr_terms(mode=mode):
        cleaned = dt.strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            terms.append(cleaned)

    return terms


def build_hotwords(
    mode: str = "off",
    custom_terms: Optional[Iterable[str]] = None
) -> Optional[str]:
    """
    faster-whisper'ın beklediği boşlukla ayrılmış tek bir string döner.
    Eğer terim yoksa (örn. mode='off' ve custom_terms yoksa) None döner.
    """
    # Geriye dönük uyumluluk: Eğer mode pozisyonel olarak custom_terms yerine geçildiyse
    if isinstance(mode, (list, tuple, set)) and custom_terms is None:
        custom_terms = mode
        mode = "off"

    terms = build_hotwords_list(mode=mode, custom_terms=custom_terms)
    if not terms:
        return None
    return " ".join(terms)


def parse_custom_hotwords(
    raw_text: Optional[str],
    max_terms: int = 20,
    max_term_length: int = 100,
) -> List[str]:
    """
    Kullanıcının UI üzerinden girdiği virgülle ayrılmış özel terimleri ayrıştırır,
    temizler, doğrular ve tekilleştirir.

    Kurallar:
    - Boş, None veya yalnızca boşluk içeren girdiler için boş liste [] döner.
    - Virgül (,), noktalı virgül (;) veya yeni satır (\\n, \\r) karakterlerine göre böler.
    - Her terimin başındaki ve sonundaki boşlukları temizler (strip).
    - Boş terimleri (art arda gelen virgüller, son virgüller vb.) eler.
    - Türkçe karakterleri (`ş, ğ, ü, ö, ç, ı, İ`) ve büyük/küçük harf durumunu aynen korur.
    - Sırayı koruyarak tekilleştirir (deduplicate).
    - Terim uzunluğunu max_term_length (varsayılan: 100) karakter ile sınırlar.
    - Toplam terim sayısını max_terms (varsayılan: 20) ile sınırlar.
    """
    if not raw_text or not isinstance(raw_text, str):
        return []

    parts = re.split(r"[,;\n\r]+", raw_text)
    seen = set()
    cleaned_terms: List[str] = []

    for part in parts:
        term = part.strip()
        if not term:
            continue

        if len(term) > max_term_length:
            term = term[:max_term_length].strip()
            if not term:
                continue

        if term not in seen:
            seen.add(term)
            cleaned_terms.append(term)
            if len(cleaned_terms) >= max_terms:
                break

    return cleaned_terms


def get_default_pdr_hotwords(mode: str = "off") -> Optional[str]:
    """faster-whisper hotwords parametresi için hazır dize döner (varsayılan: off / None)."""
    return build_hotwords(mode=mode, custom_terms=None)


def get_category_breakdown() -> Dict[str, int]:
    """Kategori ve hedef küme bazında terim sayılarını döner."""
    return {
        "PDR_CORE_TERMS": len(PDR_CORE_TERMS),
        "THERAPEUTIC_TERMS": len(THERAPEUTIC_TERMS),
        "COUNSELING_SKILLS": len(COUNSELING_SKILLS),
        "CBT_TERMS": len(CBT_TERMS),
        "EMOTION_BEHAVIOR_TERMS": len(EMOTION_BEHAVIOR_TERMS),
        "SELF_CONCEPT_TERMS": len(SELF_CONCEPT_TERMS),
        "ANXIETY_MOOD_TERMS": len(ANXIETY_MOOD_TERMS),
        "TRAUMA_CRISIS_TERMS": len(TRAUMA_CRISIS_TERMS),
        "PSYCHOEDUCATION_TERMS": len(PSYCHOEDUCATION_TERMS),
        "RELATIONSHIP_FAMILY_TERMS": len(RELATIONSHIP_FAMILY_TERMS),
        "EDUCATION_CAREER_TERMS": len(EDUCATION_CAREER_TERMS),
        "ASSESSMENT_TERMS": len(ASSESSMENT_TERMS),
        "HIGH_PRIORITY_TERMS": len(HIGH_PRIORITY_TERMS),
        "PDR_HOTWORDS_5": len(PDR_HOTWORDS_5),
        "PDR_HOTWORDS_10": len(PDR_HOTWORDS_10),
        "PDR_HOTWORDS_20": len(PDR_HOTWORDS_20),
        "TOTAL_UNIQUE_TERMS": len(get_default_pdr_terms()),
    }

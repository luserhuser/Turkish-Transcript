"""
Test ses dosyalarını oluşturan yardımcı araç.
edge-tts kullanarak Türkçe PDR danışma görüşmesi diyaloğu ve kısa ses dosyaları üretir.
"""

import asyncio
import os
import edge_tts

SAMPLE_DIR = os.path.dirname(os.path.abspath(__file__))

VOICE_COUNSELOR = "tr-TR-AhmetNeural"  # Danışman
VOICE_CLIENT = "tr-TR-EmelNeural"     # Danışan

async def generate_short_sample():
    """15 saniyelik temiz Türkçe örnek."""
    output_path = os.path.join(SAMPLE_DIR, "sample_15s.mp3")
    text = "Merhaba, psikolojik danışma ve rehberlik merkezine hoş geldiniz. Bugün sizinle görüşme sürecimizi planlayacağız."
    communicate = edge_tts.Communicate(text, VOICE_COUNSELOR)
    await communicate.save(output_path)
    print(f"[OK] 15s ses oluşturuldu: {output_path}")

async def generate_counseling_dialogue():
    """Yaklaşık 2-3 dakikalık gerçekçi PDR danışma görüşmesi diyaloğu."""
    output_path = os.path.join(SAMPLE_DIR, "sample_counseling_2m.mp3")
    temp_files = []

    dialogue = [
        (VOICE_COUNSELOR, "Merhabalar Ayşe Hanım, hoş geldiniz. Lütfen rahat bir yere oturun."),
        (VOICE_CLIENT, "Hoş bulduk Ahmet Bey, teşekkür ederim."),
        (VOICE_COUNSELOR, "Geçen haftaki görüşmemizden bu yana günleriniz nasıl geçti? Kendinizi nasıl hissediyorsunuz?"),
        (VOICE_CLIENT, "Açıkçası biraz dalgalı geçti. Özellikle üniversitede sınavlar ve staj raporları yaklaştıkça içimde sürekli bir huzursuzluk hissediyorum."),
        (VOICE_COUNSELOR, "Anlıyorum. Sınav ve staj sorumlulukları bir araya geldiğinde bu huzursuzluk hissi daha belirgin hale geliyor gibi görünüyor."),
        (VOICE_CLIENT, "Evet, tam olarak öyle. Masanın başına oturduğumda sanki hiçbir şeyi yetiştiremeyecekmişim gibi bir duygu kaplıyor içimi."),
        (VOICE_COUNSELOR, "Bu yetiştirememe düşüncesi aklınıza geldiğinde, bedeninizde ne gibi fiziksel belirtiler fark ediyorsunuz?"),
        (VOICE_CLIENT, "Kalbim daha hızlı çarpmaya başlıyor. Omuzlarımda ve boynumda yoğun bir gerginlik hissediyorum. Bazen nefes alıp vermem bile zorlaşıyor."),
        (VOICE_COUNSELOR, "Bedeninizin verdiği bu tepkiler, zihninizin tehlike algısına karşı verdiği doğal bir alarm tepkisi aslında. Bu anlarda kendinizi sakinleştirmek için denediğiniz herhangi bir yöntem oluyor mu?"),
        (VOICE_CLIENT, "Bazen balkona çıkıp derin nefes almaya çalışıyorum ama zihnimdeki düşünceler susmuyor. Ya başaramazsam, ya stajımı tamamlayamazsam diye düşünüp duruyorum."),
        (VOICE_COUNSELOR, "Geleceğe dair bu olumsuz senaryolar şu anki odağınızı oldukça zorlaştırıyor. Bugün sizinle tam da bu anlarda kullanabileceğimiz bazı farkındalık ve nefes tekniklerini ele alalım istiyorum, ne dersiniz?"),
        (VOICE_CLIENT, "Çok iyi olur hocam, gerçekten buna çok ihtiyacım var.")
    ]

    # Her parçayı geçici mp3 olarak kaydedip birleştireceğiz
    for i, (voice, text) in enumerate(dialogue):
        part_file = os.path.join(SAMPLE_DIR, f"temp_part_{i}.mp3")
        comm = edge_tts.Communicate(text, voice)
        await comm.save(part_file)
        temp_files.append(part_file)

    # ffmpeg concat ile aralara kısa sessizlik koyarak birleştir
    concat_list_file = os.path.join(SAMPLE_DIR, "concat_list.txt")
    with open(concat_list_file, "w", encoding="utf-8") as f:
        for p in temp_files:
            # ffmpeg concat dosyasında ters slash kaçışı
            escaped_p = p.replace("\\", "/")
            f.write(f"file '{escaped_p}'\n")

    cmd = f'ffmpeg -y -f concat -safe 0 -i "{concat_list_file}" -c copy "{output_path}"'
    proc = await asyncio.create_subprocess_shell(cmd)
    await proc.wait()

    # Temizlik
    if os.path.exists(concat_list_file):
        os.remove(concat_list_file)
    for p in temp_files:
        if os.path.exists(p):
            os.remove(p)

    print(f"[OK] 2-3 dakikalık diyalog oluşturuldu: {output_path}")

async def main():
    await generate_short_sample()
    await generate_counseling_dialogue()

if __name__ == "__main__":
    asyncio.run(main())

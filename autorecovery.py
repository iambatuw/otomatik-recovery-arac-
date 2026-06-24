import os
import sys
import subprocess
import zipfile
import time
import shutil
from pathlib import Path

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    requests = None
    BeautifulSoup = None

ARAC_DIZINI = Path(__file__).parent.resolve()
TOOLS_DIZIN = ARAC_DIZINI / "tools"
TOOLS_DIZIN.mkdir(exist_ok=True)  # tools klasörü yoksa oluştur

FASTBOOT = str(TOOLS_DIZIN / "fastboot.exe")
ADB = str(TOOLS_DIZIN / "adb.exe")

def adb_fastboot_kontrol():
    """ADB ve Fastboot dosyalarının varlığını kontrol eder"""
    eksikler = []
    if not os.path.exists(FASTBOOT):
        eksikler.append("fastboot.exe")
    if not os.path.exists(ADB):
        eksikler.append("adb.exe")
    
    if eksikler:
        print("\n" + "="*60)
        print("HATA: Gerekli dosyalar bulunamadı!")
        print("="*60)
        print("\nAşağıdaki dosyalar 'tools' klasöründe bulunamadı:")
        for dosya in eksikler:
            print(f"  ✗ {dosya}")
        print(f"\nBeklenen klasör: {TOOLS_DIZIN}")
        print("\nÇözüm:")
        print("  1- https://developer.android.com/studio/releases/platform-tools adresine git")
        print("  2- Platform Tools ZIP'ini indir")
        print("  3- İçindeki adb.exe ve fastboot.exe dosyalarını 'tools' klasörüne kopyala")
        print("\n" + "="*60)
        return False
    return True

def paket_yukle(paket_adi):
    try:
        __import__(paket_adi)
    except ImportError:
        print(f"{paket_adi} kuruluyor...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", paket_adi],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

def gerekli_paketleri_kur():
    global requests, BeautifulSoup
    for paket in ["requests", "bs4"]:
        paket_yukle(paket)
    import requests as _requests
    from bs4 import BeautifulSoup as _BS
    requests = _requests
    BeautifulSoup = _BS

def komut_calistir(komut, timeout=30):
    try:
        sonuc = subprocess.run(
            komut,
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        return sonuc.stdout.strip(), sonuc.stderr.strip(), sonuc.returncode
    except subprocess.TimeoutExpired:
        return "", "Zaman aşımı.", 1
    except FileNotFoundError:
        return "", "Komut bulunamadı.", 1

def fastboot_codename_al():
    cikti, hata, kod = komut_calistir([FASTBOOT, "getvar", "product"], timeout=10)
    tum_cikti = cikti + "\n" + hata
    for satir in tum_cikti.split("\n"):
        satir = satir.strip().lower()
        if satir.startswith("product:"):
            kod_adi = satir.split(":", 1)[1].strip()
            if kod_adi and kod_adi != "unknown":
                return kod_adi
    return None

def twrp_link_bul(codename):
    try:
        yanit = requests.get(f"https://dl.twrp.me/{codename}", timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    except requests.RequestException:
        return None, None
    if yanit.status_code != 200:
        return None, None
    soup = BeautifulSoup(yanit.text, "html.parser")
    tablo = soup.find("table")
    if not tablo:
        return None, None
    for satir in tablo.find_all("tr"):
        hucreler = satir.find_all("td")
        if not hucreler:
            continue
        link_el = hucreler[0].find("a")
        if not link_el:
            continue
        dosya_adi = link_el.text.strip()
        if not dosya_adi.endswith(".img"):
            continue
        return dosya_adi, "https://dl.twrp.me" + link_el["href"]
    return None, None

def twrp_gercek_link(sayfa_url):
    try:
        yanit = requests.get(sayfa_url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    except requests.RequestException:
        return None
    if yanit.status_code != 200:
        return None
    soup = BeautifulSoup(yanit.text, "html.parser")
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.endswith(".img") and ".html" not in href:
            return href if href.startswith("http") else "https://dl.twrp.me" + href
    return None

def orangefox_link_bul(codename):
    try:
        yanit = requests.get(f"https://api.orangefox.download/devices?codename={codename}", timeout=15)
    except requests.RequestException:
        return None, None
    if yanit.status_code != 200:
        return None, None
    try:
        veri = yanit.json()
    except Exception:
        return None, None
    cihazlar = veri.get("data", [])
    if not cihazlar:
        return None, None
    device_id = cihazlar[0].get("id")
    if not device_id:
        return None, None
    try:
        yanit = requests.get(f"https://api.orangefox.download/releases?device_id={device_id}", timeout=15)
    except requests.RequestException:
        return None, None
    if yanit.status_code != 200:
        return None, None
    try:
        veri = yanit.json()
    except Exception:
        return None, None
    releases = veri.get("data", [])
    if not releases:
        return None, None
    en_yeni = None
    for r in releases:
        if r.get("type") == "stable" and not r.get("archived"):
            if not en_yeni or r.get("date", 0) > en_yeni.get("date", 0):
                en_yeni = r
    if not en_yeni:
        en_yeni = releases[0]
    if not en_yeni:
        return None, None
    dl = en_yeni.get("mirrors", {}).get("DL")
    return en_yeni.get("filename"), dl

def orangefox_img_cek(zip_yolu, hedef_dizin):
    try:
        with zipfile.ZipFile(zip_yolu, "r") as z:
            for isim in z.namelist():
                if isim.endswith("recovery.img"):
                    z.extract(isim, str(hedef_dizin))
                    cikarilan = hedef_dizin / isim
                    hedef = hedef_dizin / "recovery.img"
                    if cikarilan != hedef:
                        shutil.move(str(cikarilan), str(hedef))
                    return str(hedef)
    except Exception as e:
        print(f"Zip açılamadı: {e}")
        return None
    return None

def dosya_indir(url, hedef_yol):
    try:
        print(f"İndiriliyor: {url.split('/')[-1]}")
        yanit = requests.get(url, stream=True, timeout=120, headers={"User-Agent": "Mozilla/5.0"})
        if yanit.status_code != 200:
            print(f"İndirme başarısız (HTTP {yanit.status_code})")
            return False
        toplam = int(yanit.headers.get("content-length", 0))
        indirilen = 0
        with open(hedef_yol, "wb") as f:
            for parca in yanit.iter_content(chunk_size=1024 * 1024):
                f.write(parca)
                indirilen += len(parca)
                if toplam > 0:
                    yuzde = (indirilen / toplam) * 100
                    print(f"\r  %{yuzde:.0f} - {indirilen/1024/1024:.1f}/{toplam/1024/1024:.1f} MB", end="", flush=True)
        print()
        return True
    except Exception as e:
        print(f"İndirme hatası: {e}")
        return False

def fastboot_flash(img_yolu):
    print("Recovery flashlanıyor...")
    cikti, hata_mesaji, kod = komut_calistir([FASTBOOT, "flash", "recovery", img_yolu], timeout=60)
    if kod != 0:
        print(f"Flash hatası: {hata_mesaji or cikti}")
        return False
    print("Cihaz recovery moduna yeniden başlatılıyor...")
    komut_calistir([FASTBOOT, "reboot", "recovery"])
    time.sleep(3)
    return True

def adb_cihaz_kontrol():
    """ADB ile bağlı cihaz olup olmadığını kontrol eder"""
    if not os.path.exists(ADB):
        return False
    
    cikti, hata, kod = komut_calistir([ADB, "devices"], timeout=5)
    if kod != 0:
        return False
    
    satirlar = cikti.split("\n")
    for satir in satirlar:
        satir = satir.strip()
        if not satir or satir.startswith("List of devices attached"):
            continue
        parcalar = satir.split()
        if len(parcalar) >= 2:
            durum = parcalar[1]
            if durum == "device":
                return True
    return False

def fastboota_al_ve_bekle(max_deneme=3):
    """ADB ile fastboot'a almayı dener, başarılı olana kadar bekler"""
    for deneme in range(1, max_deneme + 1):
        print(f"\nDeneme {deneme}/{max_deneme}: Fastboot'a alınıyor...")
        
        # ADB'den reboot bootloader komutu gönder
        if os.path.exists(ADB):
            subprocess.run([ADB, "reboot", "bootloader"], capture_output=True)
        
        print("Cihaz fastboot moduna geçerken bekleniyor...")
        
        # 10 saniye bekle (cihazın fastboot'a geçmesi için)
        for i in range(10, 0, -1):
            print(f"\r  {i} saniye kaldı...", end="", flush=True)
            time.sleep(1)
        print()
        
        # Fastboot'ta cihazı kontrol et
        codename = fastboot_codename_al()
        if codename:
            print(f"✓ Cihaz fastboot modunda algılandı! Kod adı: {codename}")
            return codename
        else:
            print("✗ Cihaz fastboot'ta algılanamadı, tekrar deneniyor...")
    
    return None

def main():
    os.system("cls" if os.name == "nt" else "clear")
    print("="*60)
    print("         Xiaomi Recovery Aracı")
    print("="*60)
    print()

    # ADB ve Fastboot kontrolü
    print("Gerekli araçlar kontrol ediliyor...")
    if not adb_fastboot_kontrol():
        input("\nÇıkmak için ENTER'a basın...")
        sys.exit(1)
    print("✓ ADB ve Fastboot bulundu.")
    print()

    print("Gerekli paketler kontrol ediliyor...")
    gerekli_paketleri_kur()
    print("✓ Paketler hazır.")
    print()

    print()
    print("Kuruluma başlamadan önce:")
    print()
    print("  1- Telefonunuzda USB Hata Ayıklama (USB Debugging) açık olmalıdır.")
    print("     Ayarlar > Telefon Hakkında > MIUI Sürümü'ne 7 kere tıkla,")
    print("     Ayarlar > Ek Ayarlar > Geliştirici Seçenekleri > USB Hata Ayıklama")
    print()
    print("  2- Telefonu kapatın, Ses Kısma tuşuna basılı tutarken Güç tuşuna basın,")
    print("     ekranda FASTBOOT yazısını gördüğünüzde tuşları bırakın.")
    print("     (Cihaz fastboot modunda bekleme ekranında olacak)")
    print()
    print("  Yukarıdaki adımları uyguladıysanız ENTER'a basın. Değilse uygulayıp ENTER'a basın.")
    print()
    
    input("ENTER'a basarak devam edin...")
    print()

    # Önce fastboot kontrol et
    print("Fastboot modunda cihaz aranıyor...")
    codename = fastboot_codename_al()

    # Fastboot'ta cihaz yoksa ADB dene
    if not codename and os.path.exists(ADB):
        print("Fastboot'ta cihaz bulunamadı, ADB deneniyor...")
        
        if adb_cihaz_kontrol():
            print("ADB ile cihaz bulundu, fastboot'a alınıyor...")
            codename = fastboota_al_ve_bekle(max_deneme=3)
        else:
            print("ADB ile cihaz bulunamadı.")
    
    # Hala cihaz yoksa döngüye gir
    while not codename:
        print()
        print("="*60)
        print("CIHAZ ALGILANAMADI!")
        print("="*60)
        print()
        print("Şunları kontrol edin:")
        print()
        print("  1- Telefon fastboot modunda mı? (Kapat -> Ses Kısma + Güç)")
        print("  2- USB kablosu bağlı mı? Farklı port/kablo dene")
        print("  3- Sürücüler yüklü mü? (Windows için MiFlash sürücüleri gerekli)")
        print("  4- USB Hata Ayıklama izni verildi mi? (ADB için)")
        print("  5- Farklı bir USB kablosu dene (veri aktarımı yapan bir kablo)")
        print()
        print("Seçenekler:")
        print("  [1] Tekrar dene")
        print("  [2] ADB ile fastboot'a almayı dene")
        print("  [3] Programdan çık")
        print()
        
        secim = input("Seçiminiz (1/2/3): ").strip()
        
        if secim == "1":
            print("\nFastboot tekrar taranıyor...")
            codename = fastboot_codename_al()
        elif secim == "2":
            if os.path.exists(ADB):
                print("\nADB ile cihaz aranıyor...")
                if adb_cihaz_kontrol():
                    print("Cihaz bulundu, fastboot'a alınıyor...")
                    codename = fastboota_al_ve_bekle(max_deneme=3)
                else:
                    print("ADB ile cihaz bulunamadı. USB Hata Ayıklama'yı kontrol edin.")
            else:
                print("ADB bulunamadı!")
        elif secim == "3":
            print("Programdan çıkılıyor...")
            sys.exit(0)
        else:
            print("Geçersiz seçim!")

    print(f"\n✓ Cihaz kod adı: {codename}")
    print()

    print("Hangi recovery yüklensin?")
    print("  [1] TWRP")
    print("  [2] OrangeFox")
    print()

    while True:
        secim = input("Seçiminiz (1 veya 2): ").strip()
        if secim in ("1", "2"):
            break
        if secim:
            print("Geçersiz seçim. 1 veya 2 girin.")

    print()

    if secim == "1":
        print("TWRP aranıyor...")
        dosya_adi, sayfa_url = twrp_link_bul(codename)
        if not dosya_adi:
            print(f"Cihazınız için TWRP imajı bulunamadı. (kod adı: {codename})")
            input("Çıkmak için ENTER'a basın...")
            sys.exit(1)
        print(f"En güncel TWRP: {dosya_adi}")
        gercek_link = twrp_gercek_link(sayfa_url)
        if not gercek_link:
            print("TWRP indirme linki alınamadı.")
            input("Çıkmak için ENTER'a basın...")
            sys.exit(1)
        img_yolu = str(ARAC_DIZINI / dosya_adi)
        if not dosya_indir(gercek_link, img_yolu):
            input("Çıkmak için ENTER'a basın...")
            sys.exit(1)
        print(f"TWRP indirildi: {dosya_adi}")
    else:
        print("OrangeFox aranıyor...")
        dosya_adi, indirme_url = orangefox_link_bul(codename)
        if not dosya_adi:
            print(f"Cihazınız için OrangeFox imajı bulunamadı. (kod adı: {codename})")
            input("Çıkmak için ENTER'a basın...")
            sys.exit(1)
        print(f"En güncel OrangeFox: {dosya_adi}")
        zip_yolu = str(ARAC_DIZINI / dosya_adi)
        if not dosya_indir(indirme_url, zip_yolu):
            input("Çıkmak için ENTER'a basın...")
            sys.exit(1)
        print(f"OrangeFox indirildi: {dosya_adi}")
        print("Zip içinden recovery.img çıkarılıyor...")
        img_yolu = orangefox_img_cek(Path(zip_yolu), ARAC_DIZINI)
        if not img_yolu:
            print("recovery.img zip içinden çıkarılamadı.")
            input("Çıkmak için ENTER'a basın...")
            sys.exit(1)
        print("recovery.img hazır.")

    print()
    onay = input("Recovery flashlansın mı? (E/H): ").strip().lower()
    if onay != "e":
        print("İşlem iptal edildi.")
        input("Çıkmak için ENTER'a basın...")
        sys.exit(0)

    print()
    if not fastboot_flash(img_yolu):
        print()
        print("="*60)
        print("FLASH BAŞARISIZ!")
        print("="*60)
        print()
        print("Şunları kontrol edin:")
        print("  - Telefon hala fastboot modunda mı?")
        print("  - USB kablosu düzgün bağlı mı?")
        print("  - Başka bir USB portu deneyin")
        print("  - Bootloader kilidi açık mı? (fastboot oem unlock)")
        print("  - Bilgisayarı yeniden başlatıp tekrar deneyin")
        print()
        input("Çıkmak için ENTER'a basın...")
        sys.exit(1)

    print()
    print("="*60)
    print("✓ RECOVERY BAŞARIYLA FLASHLANDI!")
    print("="*60)
    print()
    print("Cihaz recovery moduna yönlendiriliyor...")
    print()

    input("Çıkmak için ENTER'a basın...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nİşlem iptal edildi.")
        sys.exit(0)
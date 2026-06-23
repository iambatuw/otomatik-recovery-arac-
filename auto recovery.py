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
FASTBOOT = str(TOOLS_DIZIN / "fastboot.exe")
ADB = str(TOOLS_DIZIN / "adb.exe")

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

def main():
    os.system("cls" if os.name == "nt" else "clear")
    print("Xiaomi Recovery Aracı")
    print()

    print("Gerekli paketler kontrol ediliyor...")
    gerekli_paketleri_kur()
    print("Paketler hazır.")
    print()

    if not os.path.exists(FASTBOOT):
        print(f"fastboot.exe bulunamadı: {FASTBOOT}")
        input("Çıkmak için ENTER'a basın...")
        sys.exit(1)

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

    codename = fastboot_codename_al()

    if not codename and os.path.exists(ADB):
        print("Fastboot bulunamadı, ADB deneniyor...")
        cihaz = komut_calistir([ADB, "devices"])[0]
        if "device" in cihaz and "offline" not in cihaz and "unauthorized" not in cihaz:
            print("ADB ile cihaz bulundu, bootloader'a geçiliyor...")
            subprocess.run([ADB, "reboot", "bootloader"], capture_output=True)
            time.sleep(8)
            codename = fastboot_codename_al()
        else:
            print("ADB ile cihaz bulunamadı.")

    while not codename:
        print()
        print("Cihaz hala algılanmadı. Şunları kontrol edin:")
        print()
        print("  1- Telefon fastboot modunda mı? (Kapat -> Ses Kısma + Güç)")
        print("  2- USB kablosu bağlı mı? Farklı port/kablo dene")
        print("  3- Sürücüler yüklü mü?")
        print()
        input("Hazır olunca ENTER'a basın...")
        print()
        codename = fastboot_codename_al()

    print(f"Cihaz kod adı: {codename}")
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
        print("  Flash işlemi başarısız oldu. Şunları kontrol edin:")
        print("  - Telefon hala fastboot modunda mı?")
        print("  - USB kablosu düzgün bağlı mı?")
        print("  - Başka bir USB portu deneyin")
        print("  - Bilgisayarı yeniden başlatıp tekrar deneyin")
        print()
        input("Çıkmak için ENTER'a basın...")
        sys.exit(1)

    print()
    print("Recovery başarıyla flashlandı!")
    print("Cihaz recovery moduna yönlendiriliyor...")
    print()

    input("Çıkmak için ENTER'a basın...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nİşlem iptal edildi.")
        sys.exit(0)

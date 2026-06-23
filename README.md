# Xiaomi Recovery Aracı

Xiaomi cihazlar için otomatik TWRP / OrangeFox recovery kurulum aracı.

## 📥 Kurulum

### 1. Python'u yükleyin (yoksa)

https://python.org adresinden Python 3'ü indirip kurun.
Kurulumda **"Add Python to PATH"** seçeneğini işaretleyin.

### 2. Burayı indirin

➡️ https://github.com/iambatuw/otomatik-recovery-arac-/archive/refs/heads/main.zip

### 3. Zip'ten çıkarın

Zip dosyasını masaüstüne veya istediğiniz bir klasöre çıkarın.

### 4. Çalıştırın

`auto recovery.py` dosyasına çift tıklayın veya komut satırından:

```
python "auto recovery.py"
```

## 📱 Kullanım

1. Telefonu fastboot modunda bilgisayara bağlayın
   (Kapat → Ses Kısma + Güç tuşu → FASTBOOT yazısı görünene kadar bekle)
2. `auto recovery.py` dosyasını çalıştırın
3. Ekrandaki yönergeleri takip edin

Gerekli Python paketleri (requests, bs4) otomatik kurulur.

## ⚙️ Özellikler

- Cihaz kod adını otomatik algılama (fastboot ile)
- ADB üzerinden bootloader'a geçiş (USB hata ayıklama ile)
- TWRP indirme ve flashlama
- OrangeFox indirme, zip içinden recovery.img çıkarma ve flashlama
- İnternet üzerinden en güncel recovery dosyasını bulma

## ⚠️ Gereksinimler

- Python 3 (PATH'e eklendiğinden emin olun)
- Windows işletim sistemi
- Xiaomi cihaz (bootloader kilidi açık)
- USB kablosu
- Fastboot modu veya USB hata ayıklama (ADB için)

## ❓ Sık Sorulanlar

**S: "Python bulunamadı" hatası alıyorum**
C: Python'u kurarken "Add Python to PATH" seçeneğini işaretleyin. Kuruluysa komut satırından `python` yazıp test edin.

**S: Cihaz algılanmıyor**
C: Telefon fastboot modunda mı kontrol edin. Farklı USB portu/kablo deneyin. Sürücüler yüklü mü kontrol edin.

**S: TWRP/OrangeFox bulunamadı**
C: Cihazınızın kod adı desteklenmiyor olabilir. Elle recovery indirip fastboot ile flashlamayı deneyin.

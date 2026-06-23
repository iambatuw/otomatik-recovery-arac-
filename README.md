# Xiaomi Recovery Aracı

Xiaomi cihazlar için otomatik TWRP / OrangeFox recovery kurulum aracı.

## Özellikler

- Cihaz kod adını otomatik algılama (fastboot ile)
- ADB üzerinden bootloader'a geçiş (USB hata ayıklama ile)
- TWRP indirme ve flashlama
- OrangeFox indirme, zip içinden recovery.img çıkarma ve flashlama
- İnternet üzerinden en güncel recovery dosyasını bulma

## Kullanım

1. Telefonu fastboot modunda bilgisayara bağlayın
2. `auto recovery.py` dosyasını çalıştırın
3. Ekrandaki yönergeleri takip edin

Gerekli Python paketleri (requests, bs4) otomatik kurulur.

## Gereksinimler

- Python 3
- Windows işletim sistemi
- Xiaomi cihaz (bootloader kilidi açık)
- USB kablosu
- Fastboot modu veya USB hata ayıklama (ADB için)

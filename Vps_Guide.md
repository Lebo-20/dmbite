# 🚀 Panduan Menjalankan Bot di VPS (PuTTY + PM2)

Panduan ini akan membantu Anda menjalankan bot Telegram di VPS Linux dengan sistem **PM2** agar tetap berjalan 24 jam (Background) dan memiliki jeda upload 1 jam otomatis.

---

## 1. Persiapan di PuTTY
1. Buka **PuTTY** dan masukkan **IP Address** VPS Anda.
2. Login sebagai `root` (atau username VPS Anda).
3. Pastikan sistem Anda up-to-date:
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

## 2. Instalasi Python & Node.js (untuk PM2)
Jalankan perintah berikut di terminal PuTTY:

```bash
# Install Python & Pip
sudo apt install python3 python3-pip -y

# Install Node.js & PM2 (untuk manajemen proses)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
sudo npm install pm2 -g
```

## 3. Setup Project
Masuk ke folder bot Anda (asumsi folder ada di root):
```bash
# Ganti dengan folder tempat Anda menaruh bot
cd /root/gdshort 

# Install dependencies Python
pip3 install -r requirements.txt
```

## 4. Menjalankan dengan PM2
Saya telah membuatkan file `ecosystem.config.js`. Anda bisa langsung menjalankan bot dan proxy sekaligus:

```bash
# Jalankan semua proses (Bot & Proxy)
pm2 start ecosystem.config.js

# Agar bot otomatis nyala jika VPS restart
pm2 save
pm2 startup
```

### Perintah Penting PM2:
*   **Lihat Status:** `pm2 status`
*   **Lihat Log/Error:** `pm2 logs dramabox-bot`
*   **Restart Bot:** `pm2 restart dramabox-bot`
*   **Stop Bot:** `pm2 stop dramabox-bot`

---

## 5. Fitur Jeda 1 Jam
Saya telah memodifikasi file `main.py`. Sekarang, sistem akan bekerja seperti ini:
1. Bot mencari drama baru.
2. Jika berhasil upload ke Telegram, bot akan mengirim pesan konfirmasi ke Admin.
3. Bot akan **berhenti selama 1 jam** (`asyncio.sleep(3600)`) sebelum mencari atau mengupload video berikutnya.
4. Jika upload gagal, bot hanya akan menunggu 10 detik sebelum mencoba item lain atau mengulang.

---

## 6. Konfigurasi Proxy (Telegram Local API)
Jika Anda menggunakan **Telegram Local API server** sebagai proxy:
1. Pastikan binari `telegram-bot-api` sudah terinstall di VPS.
2. Edit `ecosystem.config.js` dan sesuaikan `API_ID` serta `API_HASH` Anda.
3. Jika tidak menggunakan local API, Anda bisa mematikan proxy dengan:
   ```bash
   pm2 stop tg-proxy
   ```

> [!TIP]
> Pastikan file `.env` sudah terisi dengan benar di VPS agar bot bisa login ke Telegram tanpa kendala.

# 🚀 Panduan Instalasi di VPS via PuTTY (SSH)

Ikuti langkah-langkah di bawah ini untuk menginstal bot DramaBite di server Anda (VPS Ubuntu/Debian).

## 1. Persiapan Server
Setelah login ke PuTTY, pastikan sistem Anda up-to-date:
```bash
sudo apt update && sudo apt upgrade -y
```

## 2. Instalasi Dependensi (Python & FFmpeg)
Bot ini membutuhkan **Python 3** untuk menjalankan skrip dan **FFmpeg** untuk memproses video m3u8.
```bash
sudo apt install python3 python3-pip ffmpeg -y
```

## 3. Clone Repository
Gunakan repository GitHub yang baru saja dibuat:
```bash
git clone https://github.com/Lebo-20/dmbite.git
cd dmbite
```

## 4. Instalasi Requirements
Pastikan semua library Python terinstal:
```bash
pip3 install -r requirements.txt
```

## 5. Konfigurasi `.env`
Buat file konfigurasi `.env` dan isi dengan data Anda (Gunakan `nano` atau `vi`):
```bash
nano .env
```
Copy-paste isi berikut dan ganti dengan token Anda (Gunakan klik kanan di PuTTY untuk PASTE):
```env
API_ID=XXXXX
API_HASH=XXXXX
BOT_TOKEN=8426578835:AAH4C0i80dcfPvbhQF-Jlbhvh3Hmi7cnxO4
ADMIN_ID=5888747846
AUTO_CHANNEL=-1003805656274
DRAMABITE_TOKEN=A8D6AB170F7B89F2182561D3B32F390D
```
*Tekan `Ctrl+O`, `Enter`, lalu `Ctrl+X` untuk simpan.*

## 6. Cara Menjalankan Bot

### Opsi A: Jalankan Langsung (Untuk Test)
```bash
python3 main.py
```

### Opsi B: Jalankan 24/7 Menggunakan PM2 (Rekomendasi)
Agar bot tetap berjalan meskipun PuTTY ditutup:

1. Install Node.js & PM2:
   ```bash
   sudo apt install nodejs npm -y
   sudo npm install pm2 -g
   ```

2. Jalankan bot dengan PM2 (Pastikan ada di dalam folder `dmbite`):
   ```bash
   pm2 start main.py --name "dmbite-bot" --interpreter python3
   ```

3. Pantau log:
   ```bash
   pm2 logs dmbite-bot
   ```

---
> [!TIP]
> Jika Anda ingin mengupdate kode di masa depan, cukup masuk ke folder bot dan ketik `git pull`.

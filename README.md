# Twisight

Twisight adalah aplikasi web untuk menganalisis topik yang sedang ramai diperbincangkan di Twitter. Proyek ini dibangun menggunakan Flask dan mengandalkan Tweepy untuk mengambil data tweet, lalu menampilkannya dalam bentuk grafik interaktif menggunakan Chart.js. Pengguna dapat melakukan pencarian, melihat popularitas suatu kata kunci, serta menyambungkan dompet Solana untuk mengumpulkan "Retro Point" tiap kali melakukan pencarian.

## Fitur

- **Pencarian Tweet**: menampilkan jumlah tweet harian untuk kata kunci tertentu dan menyimpan datanya ke berkas CSV.
- **Grafik Interaktif**: dukungan grafik line, bar, dan doughnut menggunakan Chart.js.
- **Saran Pencarian**: menyediakan saran populer berdasarkan kata kunci yang sering dicari.
- **Wallet Integration**: pengguna dapat menghubungkan dompet Phantom (Solana) untuk membuka fitur pencarian dan mengumpulkan Retro Point.
- **Riwayat & Statistik**: riwayat pencarian dan statistik populer disimpan di `search_history.csv` dan `recent_searches.csv`.

## Instalasi

1. Pastikan Python 3 telah terpasang.
2. Instal dependensi dengan:
   ```bash
   pip install -r requirements.txt
   ```
3. Buat berkas `.env` di direktori proyek dengan variabel `BEARER_TOKEN` berisi Twitter API bearer token Anda.
4. Jalankan aplikasi:
   ```bash
   python app.py
   ```
5. Buka `http://localhost:5000` melalui peramban untuk menggunakan Twisight.

Data hasil pencarian akan tersimpan di folder `data/` dalam format CSV, sementara informasi dompet dan poin disimpan di `account-list/`.


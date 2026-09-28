# FRONTEND.md — Arsitektur Frontend

**Proyek:** Aplikasi Watermarking Gambar Berbasis Web (DCT)
**Status dokumen:** Perencanaan UI ringan (Vanilla).

---

## 1. Tech Stack

| Komponen | Teknologi |
|----------|-----------|
| Halaman Utama | `index.html` (satu berkas tunggal) |
| Styling | Tailwind CSS (via CDN `https://cdn.tailwindcss.com`) |
| State/Interaksi | Vanilla JavaScript (tanpa kerangka kerja eksternal) |
| HTTP Client | Fetch API standar (transmisi `FormData`) |

---

## 2. Struktur Tata Letak (Single Page, Dua Mode)

Dipecah jadi dua mode via **tab switcher** di bawah Header, karena keduanya punya alur data yang berbeda (lihat §3). Ini menjawab dua use-case terpisah di BAB I: menyisipkan watermark sebelum publikasi (Mode 1) dan membuktikan kepemilikan citra yang sudah tersebar (Mode 2).

- **Sidebar (kiri):** Logo dan nama aplikasi di bagian atas, diikuti menu navigasi. Sidebar menempel setinggi satu layar desktop sehingga tidak ikut bergulir saat konten di-scroll. Menu:
  - `Beranda` (halaman pembuka, default saat aplikasi dibuka)
  - `Sisip & Uji Serangan` (Mode 1)
  - `Verifikasi Kepemilikan` (Mode 2)
  - `Watermark di Citra AI`
- **Header:** Judul halaman yang sedang aktif, dan tombol **mode gelap/terang** di sisi kanan (ikon matahari untuk mode terang, berganti bulan saat mode gelap).

### Mode 1 — Sisip & Uji Serangan (skenario demo UTS)

- **Form Input:** Unggah Gambar + Input Teks Watermark/Logo + Input Key.
- **Workspace (Kiri):** Panel penampil citra asli (*Cover Image*).
- **Workspace (Kanan):** Panel penampil citra ter-*watermark* (*Stego-Image*) yang merespons langsung (*live-update*) pasca-serangan.
- **Action Bar (Bawah Kanan):** Deretan tombol pemicu serangan untuk demo (Tombol "JPEG 50%", "Crop Area", "Add Noise").
- **Dashboard Metrik (Footer):** Blok *sticky* yang menampilkan skor kalkulasi:
  - `PSNR: -- dB` (terisi saat gambar selesai disisipkan)
  - `NC: --` (terisi saat ekstraksi dilakukan setelah diserang)
  - `BER: -- %` (terisi saat ekstraksi dilakukan setelah diserang)

### Mode 2 — Verifikasi Kepemilikan (mandiri)

Panel independen, tidak memakai gambar dari sesi Mode 1. Ditujukan untuk kasus: jurnalis menemukan foto yang diduga miliknya beredar tanpa atribusi, lalu ingin membuktikan kepemilikan.

- **Form Input Ganda:**
  - Slot unggah 1 — **"Citra Asli (milik Anda)"**: citra asli yang disimpan sendiri sebelum dipublikasikan.
  - Slot unggah 2 — **"Citra Tersangka"**: citra yang ditemukan beredar (mis. diunduh dari media sosial, kualitasnya mungkin sudah berubah).
  - Input Key — kunci rahasia yang dipakai saat penyisipan dulu.
- **Tombol "Verifikasi Kepemilikan"** — memanggil `/api/watermark/extract` mode (b) (lihat `BACKEND.md` §3.1).
- **Panel Hasil:**
  - Watermark hasil ekstraksi ditampilkan sebagai gambar logo biner.
  - Skor `NC` dan `BER`.
  - Label ramah pengguna dari field `status_kepemilikan` (mis. "Watermark Terdeteksi Kuat"), supaya jurnalis tanpa latar belakang teknis tetap paham hasilnya — bukan cuma angka mentah.

---

## 3. Komunikasi State (Vanilla JS)

Tidak menggunakan Zustand/Redux. State dijaga dalam variabel memori lokal, **dipisah per mode** agar tidak tercampur — citra dari sesi Mode 1 tidak boleh diam-diam dipakai sebagai default di Mode 2, karena Mode 2 justru harus menerima citra dari luar sistem.

- **Mode 1:** `let currentStegoImage = null` — menyimpan gambar hasil tahap penyisipan agar bisa langsung diteruskan sebagai *payload* (*FormData blob*) saat tombol serangan di Action Bar diklik.
- **Mode 2:** `let verifikasiCitraAsli = null` dan `let verifikasiCitraTersangka = null` — diisi murni dari dua slot unggah manual di panel Verifikasi Kepemilikan, terlepas dari apa pun yang sedang aktif di Mode 1.
- Beralih tab **tidak** mereset state mode yang ditinggalkan, supaya pengguna bisa bolak-balik tanpa kehilangan pekerjaan (mis. sudah unggah citra asli di Mode 2, lalu sempat cek Mode 1, saat kembali citra tadi masih ada).

---

## 4. Skenario Demo UTS via Antarmuka (Mode 1)

UI Mode 1 dirancang spesifik untuk lulus kriteria skenario demo wajib:
1. Pengguna mengunggah foto jurnalistik via panel kiri.
2. Pengguna klik **"Sisipkan"**. Gambar muncul di panel kanan (nilai PSNR muncul).
3. Pengguna menekan salah satu tombol di Action Bar (misal: **"Serang: Kompresi JPEG 50%"**).
4. Backend akan merusak gambar, mengekstrak data dari gambar rusak tersebut secara otomatis, dan mengembalikan data.
5. Dasbor antarmuka otomatis memperbarui tampilan gambar cacat di panel kanan beserta hasil kalkulasi akhir NC dan BER.

---

## 5. Skenario Verifikasi Kepemilikan (Mode 2)

Skenario tambahan yang menunjukkan use-case dunia nyata dari BAB I (bukan bagian dari demo wajib UTS, tapi memperkuat argumen "aplikasi ini benar-benar berguna untuk jurnalis independen"):

1. Pengguna berpindah ke tab **"Verifikasi Kepemilikan"**.
2. Pengguna mengunggah **citra asli** miliknya (yang sudah disimpan sejak awal) ke slot 1.
3. Pengguna mengunggah **citra tersangka** — foto yang ditemukan beredar tanpa atribusi (untuk demo, ini boleh diambil dari citra hasil serangan di Mode 1, mensimulasikan "foto yang sudah dikompres ulang media sosial") — ke slot 2.
4. Pengguna memasukkan key yang sama dan klik **"Verifikasi Kepemilikan"**.
5. Panel hasil menampilkan watermark yang berhasil diekstraksi, skor NC/BER, dan label status kepemilikan yang mudah dipahami tanpa latar belakang teknis.

---
 
## 6. Color Palette
 
Warna utama didefinisikan sebagai CSS variable di `:root` (dan ditimpa di `html.dark` untuk mode gelap). Warna lain dipakai langsung lewat kelas Tailwind/inline style.
 
### 6.1 Warna Brand (CSS variable)
 
| Token | Terang | Gelap | Pemakaian |
|-------|--------|-------|-----------|
| `--sidebar` | `#163537` | `#0e2123` | Latar sidebar, footer metrik, tombol file |
| `--sidebar-soft` | `#1d4143` | `#17393b` | Hover menu sidebar, hover tombol file |
| `--brand` | `#2D7D59` | `#2D7D59` | Tombol utama (`.btn-primary`), logo |
| `--brand-dark` | `#1B5A45` | `#7fdcae` | Hover tombol, teks/ikon aksen, PSNR |
| `--mint` | `#E1F0E7` | `#24493f` | Menu sidebar aktif, tombol sekunder |
| `--mint-2` | `#D1EBDD` | `#2a5548` | Badge hero |
 
### 6.2 Warna Aksen per Fitur
 
| Fitur | Warna | Latar ikon kartu |
|-------|-------|------------------|
| Sisip & Uji Serangan | Hijau `#2D7D59` | `#e7f7ed` |
| Verifikasi Kepemilikan | Biru `#3B82F6` | `#eaf2fe` |
| Watermark di Citra AI / Jenis Serangan | Ungu `#5D43E2` | `#efebfd` |
 
### 6.3 Netral (Mode Terang)
 
| Peran | Warna |
|-------|-------|
| Latar halaman | `#f4f6f4` |
| Latar header | `#f8faf9` |
| Latar kartu | `#ffffff` |
| Latar kotak placeholder/hasil | `#fafbfa` |
| Gradient hero | `#E4F2EB` → `#EFF7F1` |
| Border kartu / pembatas | `#eef1ee` |
| Border input | `#e2e8e4` |
| Border putus-putus (placeholder) | `#dde5e0`, `#c7dccf` |
| Tombol bulat kecil, pill serangan | `#eef2f0` (border `#e5e9e6`) |
 
### 6.4 Teks (Mode Terang)
 
| Peran | Warna |
|-------|-------|
| Judul / teks utama | `#16241c`, `#152720` |
| Label, teks form | `#33403a`, `#334036` |
| Deskripsi | `#5b6b62`, `#6b786f` |
| Teks pudar / hint | `#8b978f`, `#9aa89f` |
| Teks sidebar | `#a9c2bd` (subjudul `#9db8b1`, hover/aktif `#eafff2`) |
| Tulisan tangan (Caveat) | `#3c584c` |
 
### 6.5 Status & Peringatan (Mode Terang)
 
| Peran | Latar | Teks | Border |
|-------|-------|------|--------|
| Pill status berhasil | `#B4CFC3` | `#163537` | — |
| Pill status gagal | `#f3b7b0` | `#7a241b` | — |
| Tombol serang "Gabungan" (danger) | `#fcebea` | `#b3392f` | `#f7d9d6` |
| Banner peringatan server | `red-100` (Tailwind) | `red-800` | `red-400` |
 
### 6.6 Mode Gelap (penimpa netral & teks)
 
| Peran | Warna |
|-------|-------|
| Latar halaman | `#0d1715` |
| Latar header / kotak placeholder | `#111e1b` |
| Latar kartu | `#15231f` |
| Latar input | `#0f1c19` |
| Gradient hero | `#132a24` → `#183229` |
| Border kartu / pembatas | `#22332e` |
| Border input / dashed | `#2a3d37` |
| Tombol bulat kecil, pill serangan | `#1c2e29` (hover `#25392f`) |
| Tombol file | `#2f6b57` |
| Teks utama | `#dbe7e1` |
| Judul | `#eaf4ef` |
| Label / deskripsi | `#c9d8d1`, `#9db3aa` |
| Teks pudar / hint | `#7f9990`, `#6f877e` (placeholder) |
| Tulisan tangan | `#a9cdbd` |
| Menu aktif (teks / ikon) | `#eafff2` / `#8fe8bd` |
| Tombol danger | latar `#3a1f1d`, teks `#f0a9a1`, border `#5a2c28` |
| Banner peringatan server | latar `#3a1f1d`, teks `#f3b7b0`, border `#7a2f2a` |
| Scrollbar thumb | terang `#cbd5e1`, gelap `#2f4740` |

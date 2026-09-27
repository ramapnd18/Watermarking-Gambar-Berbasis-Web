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

Tetap satu halaman (tanpa navigasi/reload), tapi dipecah jadi dua mode via **tab switcher** di bawah Header, karena keduanya punya alur data yang berbeda (lihat §3). Ini menjawab dua use-case terpisah di BAB I: menyisipkan watermark sebelum publikasi (Mode 1) dan membuktikan kepemilikan citra yang sudah tersebar (Mode 2).

- **Header:** Judul Aplikasi (tetap tampil di kedua mode).
- **Tab Switcher:** `[ Sisip & Uji Serangan ]` (default, aktif) · `[ Verifikasi Kepemilikan ]`

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

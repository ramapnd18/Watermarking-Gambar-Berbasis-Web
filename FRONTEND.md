# FRONTEND.md — Arsitektur Frontend

**Proyek:** Aplikasi Watermarking Gambar Berbasis Web (DCT)
**Status dokumen:** Perencanaan UI ringan (Vanilla).

---

## 1. Tech Stack

| Komponen | Teknologi |
|----------|-----------|
| Halaman Utama | `index.html` (Satu berkas tunggal) |
| Styling | Tailwind CSS (via CDN `https://cdn.tailwindcss.com`) |
| State/Interaksi | Vanilla JavaScript (tanpa kerangka kerja eksternal) |
| HTTP Client | Fetch API standar (transmisi `FormData`) |

---

## 2. Struktur Tata Letak (Single Page)

Aplikasi dirancang untuk langsung mendemonstrasikan skenario uji UTS (memasukkan citra, merusak citra, menampilkan metrik) tanpa perlu navigasi halaman.

- **Header:** Judul Aplikasi & Form Input (Unggah Gambar + Input Teks Watermark + Input Key).
- **Workspace (Kiri):** Panel penampil citra asli (*Cover Image*).
- **Workspace (Kanan):** Panel penampil citra ter-*watermark* (*Stego-Image*) yang akan merespons langsung (*live-update*) pasca-serangan.
- **Action Bar (Bawah Kanan):** Deretan tombol pemicu serangan untuk demo (Tombol "JPEG 50%", "Crop Area", "Add Noise").
- **Dashboard Metrik (Footer):** Blok *sticky* yang menampilkan skor kalkulasi secara masif:
  - `PSNR: -- dB` (Terisi saat gambar selesai disisipkan)[cite: 2].
  - `NC: --` (Terisi saat ekstraksi dilakukan setelah diserang)[cite: 2].
  - `BER: -- %` (Terisi saat ekstraksi dilakukan setelah diserang)[cite: 2].

---

## 3. Komunikasi State (Vanilla JS)

Tidak menggunakan Zustand/Redux. State dijaga dalam variabel memori lokal `let currentStegoImage = null` agar gambar hasil eksekusi tahap 1 (penyisipan) bisa langsung diteruskan sebagai *payload* (*FormData blob*) saat tombol eksekusi tahap 2 (serangan kompresi/modifikasi) diklik.

## 4. Skenario Demo UTS via Antarmuka[cite: 2]

UI ini dirancang spesifik untuk lulus kriteria *Skenario demo wajib*:
1. Pengguna mengunggah foto jurnalistik via panel kiri.
2. Pengguna klik **"Sisipkan"**. Gambar muncul di panel kanan (nilai PSNR muncul).
3. Pengguna menekan salah satu tombol di Action Bar (misal: **"Serang: Kompresi JPEG 50%"**).
4. *Backend* akan merusak gambar, mengekstrak data dari gambar rusak tersebut secara otomatis, dan mengembalikan data.
5. Dasbor antarmuka otomatis memperbarui tampilan gambar cacat di panel kanan beserta hasil kalkulasi akhir NC dan BER.
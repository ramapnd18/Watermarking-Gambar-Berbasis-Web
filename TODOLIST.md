# TODOLIST.md — Tenggat: 30 September 2026

**Proyek:** Aplikasi Watermarking Gambar Berbasis Web (DCT)
**Status:** Hari ke-1 dari 5 hari menuju tenggat waktu.

**Legenda:** `[x]` Selesai · `[ ]` Belum selesai

---

## 26 September — Arsitektur & Infrastruktur Dasar
- [x] Fiksasi judul: *Aplikasi Watermarking Gambar Berbasis Web untuk Pengamanan Aset Visual Jurnalistik Independen menggunakan DCT*.
- [x] Inisialisasi repositori Git dan penyusunan struktur folder (`backend`, `frontend`).
- [x] Menulis kerangka dasar `AI.md`, `BACKEND.md`, dan `FRONTEND.md`.

## 27 September — Logika Inti (Kriptografi & Paralelisme)
- [x] Penulisan matriks 2D-DCT & Inverse 2D-DCT dari nol tanpa *library* (`dct_core.py`, sudah diverifikasi kesetaraan matematis vs versi *naive*).
- [x] Implementasi fungsi pembangkit *pseudo-noise* dengan `secrets` (`security.py`).
- [x] Integrasi `multiprocessing.Pool` untuk memproses blok gambar 8x8 secara konkuren (`watermark_engine.py`).
- [ ] *Stress-test* CPU menggunakan foto resolusi tinggi dari zine dokumenter peternakan.

## 28 September — API Integrasi & Antarmuka UI
- [ ] Pembuatan endpoint FastAPI (`/api/watermark/embed` dan `/api/watermark/extract`).
- [ ] Pembuatan UI Frontend (HTML + Tailwind) dengan panel *split-screen*.
- [ ] Logika `fetch()` FormData dari UI ke FastAPI.

## 29 September — Simulasi Serangan & Evaluasi
- [ ] Pembuatan endpoint serangan manipulasi gambar (Crop, Resize, Noise, Kontras).
- [ ] Pengujian kompresi JPEG dengan parameter kualitas 90, 70, dan 50.
- [ ] Implementasi algoritma kalkulasi kualitas citra (PSNR).
- [ ] Implementasi algoritma perbandingan bit ekstraksi (NC dan BER).

## 30 September — Finalisasi & Pelaporan (DEADLINE)
- [ ] Penulisan dokumen PDF laporan teknis (6–12 halaman) dengan referensi format APA 7.
- [ ] Perekaman video demonstrasi skenario UTS (3–5 menit).
- [ ] Kompilasi data hasil *testing* simulasi ke dalam file XLSX.
- [ ] Penyempurnaan `README.md` dengan instruksi eksekusi agar aplikasi bisa diuji orang lain.

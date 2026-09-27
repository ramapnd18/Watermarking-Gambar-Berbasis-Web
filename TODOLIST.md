# TODOLIST.md — Tenggat: 30 September 2026

**Proyek:** Aplikasi Watermarking Gambar Berbasis Web (DCT)
**Status:** Hari ke-1 dari 5 hari menuju tenggat waktu.

**Legenda:** `[x]` Selesai · `[ ]` Belum selesai

> ⚠️ **Koreksi jadwal (hasil audit terhadap dokumen ketentuan & BAB I):** rencana lama menjejalkan laporan 6–12 halaman + video + XLSX + README semuanya ke satu hari terakhir, padahal Bab Pengujian & Analisis baru bisa ditulis SETELAH data uji selesai (jadwal lama: hari yang sama). Laporan sekarang dicicil sejak hari ini (Bab I sudah lebih dulu jadi, di luar jadwal awal), bukan ditulis dari nol di hari-H.

---

## 26 September — Arsitektur & Infrastruktur Dasar
- [x] Fiksasi judul: *Aplikasi Watermarking Gambar Berbasis Web untuk Pengamanan Aset Visual Jurnalistik Independen menggunakan DCT*.
- [x] Inisialisasi repositori Git dan penyusunan struktur folder (`backend`, `frontend`).
- [x] Menulis kerangka dasar `AI.md`, `BACKEND.md`, `FRONTEND.md`, dan `UJI.md`.
- [x] Bab I Pendahuluan laporan (Latar Belakang, Masalah, Tujuan) — selesai lebih awal dari jadwal semula.


## 27 September — Logika Inti (Kriptografi & Paralelisme)
- [x] Penulisan matriks 2D-DCT & Inverse 2D-DCT dari nol tanpa *library* (`dct_core.py`, sudah diverifikasi kesetaraan matematis vs versi *naive*).
- [x] Implementasi fungsi pembangkit *pseudo-noise* dengan `secrets` (`security.py`, sudah diverifikasi: determinisme, keunikan antar-kunci, permutasi posisi tanpa duplikat).
- [x] Integrasi `multiprocessing.Pool` untuk memproses blok gambar 8x8 secara konkuren (`watermark_engine.py` — blok/DCT paralel + sisip/ekstrak spread-spectrum, terverifikasi NC=1.0 tanpa serangan).
- [ ] *Stress-test* CPU menggunakan foto resolusi tinggi dari zine dokumenter peternakan.
- [ ] **(Baru)** Mulai draf Bab II (Dasar Teori) dan Bab III (Rancangan Sistem) laporan — materinya sudah tersedia dari `dct_core.py`, `security.py`, `BACKEND.md`, `FRONTEND.md`; tinggal disusun ulang jadi narasi laporan.

## 28 September — API Integrasi & Antarmuka UI
- [x] Pembuatan endpoint FastAPI (`/api/watermark/embed` dan `/api/watermark/extract`, termasuk dua mode ekstraksi — lihat `BACKEND.md` §3.1; terverifikasi via HTTP).
- [x] Pembuatan UI Frontend (HTML + Tailwind): Mode 1 (Sisip & Uji Serangan) dan Mode 2 (Verifikasi Kepemilikan) — lihat `FRONTEND.md` §2.
- [x] Logika `fetch()` FormData dari UI ke FastAPI, untuk kedua mode (NC/BER otomatis pasca-serangan).
- [x] **(Baru)** Membungkus self-check `dct_core.py` dan `security.py` jadi unit test resmi di `tests/` (bagian dari 5 unit test wajib, lihat `UJI.md` §4) — 10 test hijau (`pytest tests/`).

## 29 September — Simulasi Serangan & Evaluasi
- [x] Pembuatan endpoint serangan manipulasi gambar (Crop 25%, Resize, Noise, Kontras 1.2 + brightness 20 — selaras `UJI.md` §3.3).
- [x] Pengujian kompresi JPEG dengan parameter kualitas 90, 70, dan 50 (endpoint + paket `semua` hidup).
- [x] Implementasi algoritma kalkulasi kualitas citra (PSNR; null bila serangan mengubah ukuran).
- [x] Implementasi algoritma perbandingan bit ekstraksi (NC dan BER).
- [x] Jalankan seluruh matriks `UJI.md` §3 (PSNR, JPEG 90/70/50, crop/resize/noise/kontras) untuk 3 citra uji — via `tools/jalankan_matriks.py` → `hasil_pengujian.xlsx`.
- [x] Jalankan matriks trade-off `UJI.md` §6 (3 level alpha) — menjawab Tujuan #4 BAB I.
- [ ] **(Baru)** Draf Bab IV (Implementasi) dan mulai Bab V (Pengujian dan Analisis) laporan begitu data di atas keluar — jangan ditunda ke hari-H.

## 30 September — Finalisasi & Pelaporan (DEADLINE)
- [ ] Selesaikan Bab V (Pengujian dan Analisis) dan Bab VI (Kesimpulan dan Saran) laporan — bukan menulis dari nol, hanya melengkapi draf Bab I–IV yang sudah dicicil.
- [ ] **(Baru)** Susun Lampiran Penggunaan AI (wajib per Bagian 10 Ketentuan Tugas — bagian mana yang dibantu AI harus disebutkan eksplisit).
- [ ] Lengkapi Daftar Pustaka minimal 10 sumber APA 7, termasuk minimal 1 publikasi dosen pengampu yang relevan (VERITAS — sudah dirujuk di Bab I).
- [ ] Perekaman video demonstrasi skenario UTS (3–5 menit): minimal 3 serangan langsung + tampilkan NC/BER (lihat `UJI.md` §8).
- [ ] Kompilasi data hasil *testing* simulasi ke dalam file XLSX (`hasil_pengujian.xlsx`, lihat `UJI.md` §7).
- [ ] Penyempurnaan `README.md`: deskripsi, cara instalasi, cara menjalankan, contoh penggunaan, **nama anggota + NPM**.
- [x] Pastikan `pytest tests/` (5 unit test wajib) hijau semua sebelum submit — 10/10 lolos.
- [ ] **(Baru)** Nama berkas laporan sesuai format wajib: `TugasKripto_C_NPM-Ketua.pdf`.
- [ ] **(Baru)** Cek ulang Daftar Periksa resmi di dokumen ketentuan (fitur wajib jalan, pengujian lengkap, README lengkap, tidak ada kunci di repo, ≥1 rujukan dosen, demo sudah dicoba minimal sekali).

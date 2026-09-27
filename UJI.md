# UJI.md — Modul Pengujian (Topik C: Digital Watermarking)

**Proyek:** Aplikasi Watermarking Gambar Berbasis Web (DCT)
**Sumber acuan:** Bagian 3.C ("Pengujian wajib") dan Bagian 4 ("Ketentuan Teknis Umum") — *Tugas Proyek Aplikasi Kriptografi*, Keamanan Informasi, Universitas Siliwangi.
**Status dokumen:** Rencana pengujian — belum dieksekusi.

---

## 0. Asumsi yang Dipakai

Dokumen tugas memberi angka pasti hanya untuk kualitas JPEG (90/70/50); parameter serangan lain (cropping, resize, noise, kontras) tidak dipatok nilainya. Nilai default di bawah ini adalah asumsi kerja tim — sah untuk diubah di `attacker.py` selama tetap diuji dan dicatat di laporan.

| Keputusan | Nilai dipilih | Alasan |
|-----------|---------------|--------|
| Bentuk watermark | Logo biner (gambar 2 warna) | Sesuai pilihan tim; NC/BER dihitung langsung atas bit 0/1 |
| Ukuran logo default | 32×32 piksel (1024 bit) | Konservatif terhadap kapasitas blok 8x8 pada citra ≥512×512 (±4096 blok tersedia bila 1 bit/blok) |
| Jumlah citra uji utama | 3 citra | Disepakati tim; representatif bila dipilih dengan karakteristik berbeda (lihat §2) |
| Fokus pengerjaan | Fitur wajib dahulu | Pengayaan (§5) dikerjakan setelah §3–§4 selesai dan stabil |

---

## 1. Ruang Lingkup

- **Jalur:** Robust — 2D-DCT pada koefisien frekuensi menengah (bukan fragile/LSB).
- **Objek diuji:** `dct_core.py` (sudah selesai) + `watermark_engine.py`, `security.py`, `attacker.py`, `evaluator.py` (menyusul).
- **Tidak berlaku untuk topik ini:** peta area termodifikasi (itu hanya wajib untuk jalur *fragile*, bukan *robust*).
- **Di luar cakupan wajib:** semua isi §5 (pengayaan) — dikerjakan bila waktu memungkinkan.

---

## 2. Dataset Citra Uji

3 citra jurnalistik resolusi tinggi, dipilih agar karakteristik teksturnya berbeda (memengaruhi seberapa "aman" koefisien frekuensi menengah menyerap watermark tanpa terlihat):

| # | Nama file (usulan) | Karakteristik | Alasan dipilih |
|---|---------------------|----------------|-----------------|
| 1 | `citra_01_tekstur_tinggi.jpg` | Detail/tekstur padat (mis. kerumunan, tekstur kain, dedaunan) | Frekuensi tinggi banyak → biasanya lebih toleran menyembunyikan watermark |
| 2 | `citra_02_area_datar.jpg` | Area halus/flat (mis. langit, dinding polos, potret dengan latar blur) | Kasus terberat — distorsi watermark paling mudah terlihat di sini |
| 3 | `citra_03_potret_wajah.jpg` | Foto potret/wajah manusia | Representatif untuk foto jurnalistik dokumenter; sensitif secara visual terhadap distorsi |

Simpan di `/tests/assets/`. Semua citra dikonversi ke ukuran yang habis dibagi 8 (kelipatan 8 piksel di kedua sisi) sebelum diproses `dct_core.py`.

---

## 3. Skenario Pengujian Wajib

### 3.1 PSNR — Citra Ber-watermark vs Citra Asli

Fungsi: `evaluator.py :: hitung_psnr(citra_asli, citra_stego)`

$$PSNR = 10 \cdot \log_{10}\left(\frac{MAX_I^2}{MSE}\right), \quad MAX_I = 255$$

Prosedur: sisipkan logo biner ke tiap 1 dari 3 citra (kekuatan penyisipan/`alpha` default dari `watermark_engine.py`), tanpa serangan apa pun, lalu hitung PSNR.

| Citra | PSNR (dB) | Catatan |
|-------|-----------|---------|
| citra_01_tekstur_tinggi | *(diisi hasil uji)* | |
| citra_02_area_datar | | |
| citra_03_potret_wajah | | |

### 3.2 Serangan Kompresi JPEG (Kualitas 90, 70, 50)

Fungsi: `attacker.py :: serang_jpeg(citra, kualitas)` → `evaluator.py :: hitung_nc()`, `hitung_ber()`

Untuk **setiap** dari 3 citra stego, uji ketiga level kualitas (total 9 kombinasi):

| Citra | Kualitas JPEG | NC | BER (%) | Watermark hasil ekstraksi |
|-------|---------------|----|---------|-----------------------------|
| citra_01 | 90 | | | |
| citra_01 | 70 | | | |
| citra_01 | 50 | | | |
| citra_02 | 90 | | | |
| citra_02 | 70 | | | |
| citra_02 | 50 | | | |
| citra_03 | 90 | | | |
| citra_03 | 70 | | | |
| citra_03 | 50 | | | |

### 3.3 Serangan Manipulasi Geometris & Visual

Fungsi: `attacker.py :: serang_crop()`, `serang_resize()`, `serang_noise_gaussian()`, `serang_kontras_kecerahan()`

| Jenis serangan | Parameter default (§0) |
|----------------|--------------------------|
| Cropping | Potong 25% area (crop tengah, sisakan 75%) |
| Resize | Downscale ke 50% ukuran asli, lalu upscale kembali ke ukuran semula |
| Gaussian noise | σ = 10 (variansi ≈ 100), mean = 0, skala piksel 0–255 |
| Kontras & kecerahan | Kontras ±20%, kecerahan ±20 (skala piksel) |

Untuk **setiap** dari 3 citra stego, uji keempat jenis serangan (total 12 kombinasi):

| Citra | Jenis serangan | NC | BER (%) | Watermark hasil ekstraksi |
|-------|-----------------|----|---------|-----------------------------|
| citra_01 | Cropping 25% | | | |
| citra_01 | Resize 50%→100% | | | |
| citra_01 | Gaussian noise σ=10 | | | |
| citra_01 | Kontras/kecerahan ±20% | | | |
| citra_02 | Cropping 25% | | | |
| citra_02 | Resize 50%→100% | | | |
| citra_02 | Gaussian noise σ=10 | | | |
| citra_02 | Kontras/kecerahan ±20% | | | |
| citra_03 | Cropping 25% | | | |
| citra_03 | Resize 50%→100% | | | |
| citra_03 | Gaussian noise σ=10 | | | |
| citra_03 | Kontras/kecerahan ±20% | | | |

### 3.4 Definisi Metrik NC dan BER

Watermark logo biner direpresentasikan sebagai matriks bit $W(i,j) \in \{0,1\}$; $W'(i,j)$ adalah hasil ekstraksi pasca-serangan.

**Normalized Correlation (NC):**

$$NC = \frac{\sum_{i,j} W(i,j) \cdot W'(i,j)}{\sqrt{\sum_{i,j} W(i,j)^2 \cdot \sum_{i,j} W'(i,j)^2}}$$

NC = 1 berarti identik sempurna; semakin mendekati 0, semakin rusak watermark yang diekstraksi.

**Bit Error Rate (BER):**

$$BER = \frac{\text{jumlah bit berbeda antara } W \text{ dan } W'}{\text{total jumlah bit}} \times 100\%$$

---

## 4. Unit Test Wajib (Minimal 5 — Bagian 4 Ketentuan Teknis Umum)

Ditempatkan di `tests/`, dijalankan via `pytest tests/` (lihat `AI.md :: Command Penting`).

| # | Nama test | Yang diverifikasi |
|---|-----------|---------------------|
| 1 | `test_dct_idct_reconstruction` | `idct2d(dct2d(blok)) ≈ blok` (dibungkus dari self-check `dct_core.py`) |
| 2 | `test_dct_matriks_vs_naive` | `dct2d()` (versi matriks) identik dengan `dct2d_naive()` (double-sum) |
| 3 | `test_key_tidak_hardcode_dan_unik` | `security.py` menghasilkan seed/key berbeda di setiap pemanggilan, tidak ada nilai tertanam di kode sumber |
| 4 | `test_embed_extract_tanpa_serangan` | Sisip logo biner → ekstraksi tanpa serangan → NC ≈ 1.0, BER ≈ 0% |
| 5 | `test_embed_extract_setelah_jpeg50` | Sisip → serang JPEG kualitas 50 → ekstraksi → NC di atas ambang batas ketahanan yang disepakati tim (mis. > 0.7), membuktikan sifat *robust* |

*(Opsional ke-6:)* `test_psnr_nilai_dikenal` — verifikasi `hitung_psnr()` dengan kasus nilai yang sudah diketahui (mis. dua citra identik → PSNR sangat besar/`inf`).

---

## 5. Pengayaan (Prioritas Rendah): Watermark pada Citra Hasil AI-Generatif

> Dikerjakan **setelah** §3 dan §4 selesai dan stabil. Bukan bagian dari fitur wajib.

- **Tujuan:** menguji apakah algoritma DCT robust yang sama tetap tahan ketika *cover image* berasal dari citra hasil AI generatif (mis. Midjourney/Stable Diffusion), yang punya pola noise dan tekstur berbeda dari foto kamera asli.
- **Prosedur ringkas:** tambahkan 1 citra AI-generatif sebagai citra ke-4 (`/tests/assets/pengayaan/citra_ai_generatif.jpg`), ulangi skenario §3.1–§3.3 padanya, lalu bandingkan PSNR/NC/BER-nya terhadap rata-rata hasil 3 citra utama.
- **Bukan prioritas saat ini** — tidak menghambat commit fitur wajib.

---

## 6. Luaran Pengujian

Sesuai Bagian 5 dokumen tugas ("Data pengujian" wajib format XLSX):

- Seluruh tabel §3.1–§3.3 (dan §5 bila sempat) dikompilasi ke satu berkas `hasil_pengujian.xlsx`, dengan sheet terpisah: `PSNR`, `Serangan_JPEG`, `Serangan_Manipulasi`, `Unit_Test_Log`, dan (opsional) `Pengayaan_AI`.
- Berkas citra uji asli, stego, dan hasil serangan disimpan di `/tests/assets/` agar bisa direproduksi ulang oleh dosen.

---

## 7. Kaitan dengan Skenario Demo UTS

Demo wajib (Bagian 3.C): sisipkan watermark ke satu citra, lakukan **minimal tiga serangan langsung**, tampilkan watermark hasil ekstraksi beserta NC dan BER.

Rekomendasi kombinasi 3 serangan untuk demo langsung (dari tombol Action Bar di `FRONTEND.md`): **Kompresi JPEG 50**, **Cropping 25%**, **Kontras/kecerahan ±20%** — mewakili tiga kategori serangan berbeda (kompresi, geometris, fotometrik) dalam waktu presentasi yang singkat.

---

## 8. Checklist Pengujian

- [ ] §3.1 PSNR selesai untuk 3 citra
- [ ] §3.2 Serangan JPEG 90/70/50 selesai untuk 3 citra (9 kombinasi)
- [ ] §3.3 Serangan cropping/resize/noise/kontras selesai untuk 3 citra (12 kombinasi)
- [ ] 5 unit test wajib lulus (`pytest tests/`)
- [ ] Data terkompilasi ke `hasil_pengujian.xlsx`
- [ ] *(Pengayaan, prioritas rendah)* Uji watermark pada citra AI-generatif

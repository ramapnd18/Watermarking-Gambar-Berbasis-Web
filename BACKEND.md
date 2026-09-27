# BACKEND.md — Arsitektur Backend

**Proyek:** Aplikasi Watermarking Gambar Berbasis Web (DCT)
**Status dokumen:** Perencanaan struktur modul Python.

---

## 1. Tech Stack

| Komponen | Teknologi |
|----------|-----------|
| Framework Web | FastAPI + Uvicorn |
| Paralelisme | Python `multiprocessing` (bawaan) |
| Kriptografi Inti | Logika matematis murni (sesuai syarat UTS Topik C) |
| Pemroses Citra | Pillow (PIL) & NumPy (hanya untuk I/O dan manipulasi serangan) |
| Keamanan | Python `secrets` untuk CSPRNG |

Global prefix: **`/api`**.

---

## 2. Struktur Modul

`backend/`:

| Modul | Fungsi | Status |
|-------|--------|--------|
| `main.py` | Controller FastAPI, routing endpoint, integrasi UI | Belum mulai |
| `dct_core.py` | Rumus matematis 2D-DCT & Inverse DCT (manual tanpa library) | ✅ Selesai |
| `watermark_engine.py` | Memecah array NumPy menjadi blok 8x8, eksekusi `multiprocessing` | ✅ Selesai |
| `security.py` | Men-generate *pseudo-noise sequence* dari seed/key | ✅ Selesai |
| `attacker.py` | Menerapkan simulasi noise, resize, crop, kompresi JPEG | ✅ Selesai |
| `evaluator.py` | Menghitung persamaan PSNR, NC, dan BER pasca-serangan | ✅ Selesai |

---

## 3. Endpoint API (Direncanakan)

### Watermarking Engine
| Verb | Path | Keterangan |
|------|------|------------|
| POST | `/api/watermark/embed` | Menerima citra + teks/logo, mengeksekusi DCT paralel, mereturn *stego-image* + nilai awal PSNR |
| POST | `/api/watermark/extract` | Menerima *stego-image*, mengekstrak teks/logo menggunakan *pseudo-noise key* |

### Modul Simulasi Serangan (Skenario UTS)
| Verb | Path | Keterangan |
|------|------|------------|
| POST | `/api/attack/jpeg` | Menerima *stego-image*, di-*compress* ke kualitas 90/70/50, lalu dihitung NC & BER-nya |
| POST | `/api/attack/manipulation` | Simulasi *crop*, *resize*, *gaussian noise*, atau kontras, mereturn citra rusak + skor ekstraksi |

---

## 4. Logika Matematis Kritis

- **DCT-2D:** Wajib menerapkan *double summation* (sigma bersarang) pada blok matriks spasial 8x8. *(Sudah diimplementasikan di `dct_core.py`, termasuk versi matriks-basis yang efisien dan versi *naive* sebagai bukti kesetaraan matematis.)*
- **Penyisipan Spread Spectrum:** Mengganti atau memodifikasi nilai frekuensi menengah pada matriks DCT menggunakan *sequence pseudo-noise*.
- **Evaluasi Kuantitatif:**
  - **PSNR:** Rumus $10 \cdot \log_{10}(\frac{MAX_I^2}{MSE})$.
  - **BER:** Perbandingan rasio bit yang salah terhadap total bit pesan yang disisipkan.

---

## 5. Keamanan & Environment
- **WAJIB:** Kunci rahasia untuk matriks posisi *pseudo-noise* dilarang di-*hardcode* di mana pun.
- Algoritma tidak memerlukan database; operasi manipulasi gambar dan kalkulasi metrik dilakukan murni pada memori (*in-memory processing*) untuk mempercepat respons antarmuka.

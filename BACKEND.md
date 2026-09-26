# BACKEND.md — Arsitektur Backend

**Proyek:** Aplikasi Watermarking Gambar Berbasis Web (DCT)
**Status dokumen:** Perencanaan struktur modul Python.

---

## 1. Tech Stack

| Komponen | Teknologi |
|----------|-----------|
| Framework Web | FastAPI + Uvicorn |
| Paralelisme | Python `multiprocessing` (Bawaan) |
| Kriptografi Inti | Logika matematis murni (Sesuai Syarat UTS Topik C)[cite: 2] |
| Pemroses Citra | Pillow (PIL) & Numpy (Hanya untuk I/O dan manipulasi serangan) |
| Keamanan | Python `secrets` untuk CSPRNG[cite: 2] |

Global prefix: **`/api`**.

---

## 2. Struktur Modul

`backend/src/`:

| Modul | Fungsi |
|-------|--------|
| `main.py` | Controller FastAPI, *routing* endpoint, integrasi UI |
| `dct_core.py` | Rumus matematis 2D-DCT & Inverse DCT (manual tanpa *library*) |
| `engine.py` | Memecah array Numpy menjadi blok 8x8, eksekusi `multiprocessing` |
| `security.py` | Men-generate *pseudo-noise sequence* dari *seed/key*[cite: 2] |
| `attacker.py` | Menerapkan simulasi *noise*, *resize*, *crop*, kompresi JPEG[cite: 2] |
| `evaluator.py` | Menghitung persamaan PSNR, NC, dan BER pasca-serangan[cite: 2] |

---

## 3. Endpoint API (Direncanakan)

### Watermarking Engine
| Verb | Path | Keterangan |
|------|------|------------|
| POST | `/api/watermark/embed` | Menerima citra + teks/logo, mengeksekusi DCT paralel, mereturn *stego-image* + nilai awal PSNR[cite: 2] |
| POST | `/api/watermark/extract` | Menerima *stego-image*, mengekstrak teks/logo menggunakan *pseudo-noise key* |

### Modul Simulasi Serangan (Skenario UTS)[cite: 2]
| Verb | Path | Keterangan |
|------|------|------------|
| POST | `/api/attack/jpeg` | Menerima *stego-image*, di-*compress* ke kualitas 90/70/50, lalu dihitung NC & BER-nya |
| POST | `/api/attack/manipulation` | Simulasi *crop*, *resize*, *gaussian noise*, atau kontras, mereturn citra rusak + skor ekstraksi |

---

## 4. Logika Matematis Kritis

- **DCT-2D:** Wajib menerapkan *double summation* (sigma bersarang) pada blok matriks spasial 8x8.
- **Penyisipan Spread Spectrum:** Mengganti atau memodifikasi nilai frekuensi menengah pada matriks DCT menggunakan *sequence pseudo-noise*.
- **Evaluasi Kuantitatif:**
  - **PSNR:** Rumus $10 \cdot \log_{10}(\frac{MAX_I^2}{MSE})$.
  - **BER:** Perbandingan rasio bit yang salah terhadap total bit pesan yang disisipkan.

---

## 5. Keamanan & Environment
- **WAJIB:** Kunci rahasia untuk matriks posisi *pseudo-noise* dilarang di-*hardcode* di mana pun[cite: 2].
- Algoritma tidak memerlukan database; operasi manipulasi gambar dan kalkulasi metrik dilakukan murni pada memori (*in-memory processing*) untuk mempercepat respons antarmuka.
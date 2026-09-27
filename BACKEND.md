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
| `watermark_engine.py` | Memecah array NumPy menjadi blok 8x8, eksekusi `multiprocessing` | Belum mulai |
| `security.py` | Men-generate *pseudo-noise sequence* dari seed/key | Belum mulai |
| `attacker.py` | Menerapkan simulasi noise, resize, crop, kompresi JPEG | Belum mulai |
| `evaluator.py` | Menghitung persamaan PSNR, NC, dan BER pasca-serangan | Belum mulai |

---

## 3. Endpoint API (Direncanakan)

### Watermarking Engine
| Verb | Path | Keterangan |
|------|------|------------|
| POST | `/api/watermark/embed` | Menerima citra + teks/logo, mengeksekusi DCT paralel, mereturn *stego-image* + nilai awal PSNR |
| POST | `/api/watermark/extract` | Ekstraksi watermark. **Dua mode pemakaian** — lihat §3.1 |

### Modul Simulasi Serangan (Skenario UTS)
| Verb | Path | Keterangan |
|------|------|------------|
| POST | `/api/attack/jpeg` | Menerima *stego-image*, di-*compress* ke kualitas 90/70/50, lalu dihitung NC & BER-nya |
| POST | `/api/attack/manipulation` | Simulasi *crop*, *resize*, *gaussian noise*, atau kontras, mereturn citra rusak + skor ekstraksi |

### 3.1 Detail `/api/watermark/extract` — Satu Endpoint, Dua Mode Pemakaian

Ekstraksi pada cakupan fitur wajib bersifat **non-blind** (butuh citra asli sebagai pembanding). Mode *blind* (tanpa citra asli) tersedia sebagai skema cadangan terpisah — lihat §3.2.

**Request** (`multipart/form-data`):

| Field | Wajib | Keterangan |
|-------|-------|------------|
| `citra_asli` | Ya | Citra asli sebelum disisipkan watermark |
| `citra_input` | Ya | Citra yang mau diekstrak — bisa citra hasil serangan simulasi (mode a) atau citra yang diunggah manual dari luar sistem (mode b) |
| `key` | Ya | Kunci rahasia yang dipakai saat penyisipan |

**Response** (JSON):

| Field | Keterangan |
|-------|------------|
| `watermark_hasil` | Watermark hasil ekstraksi (logo biner, base64) |
| `nc` | Skor *Normalized Correlation* |
| `ber` | *Bit Error Rate* (%) |
| `status_kepemilikan` | Label ramah pengguna berdasarkan ambang NC — mis. "Watermark Terdeteksi Kuat" (NC ≥ 0.75), "Terdeteksi Sebagian" (0.4 ≤ NC < 0.75), "Tidak Terdeteksi" (NC < 0.4). Ambang ini sementara; dikalibrasi ulang setelah data `UJI.md` §3 keluar. |

**Dua mode pemanggilan endpoint yang sama:**

| Mode | Dipicu dari | `citra_asli` | `citra_input` |
|------|-------------|---------------|-----------------|
| (a) Uji Serangan (demo UTS) | Tombol Action Bar, otomatis setelah `/api/attack/*` | Citra asli sesi berjalan (di memori) | Citra hasil serangan simulasi |
| (b) Verifikasi Kepemilikan (mandiri) | Panel "Verifikasi Kepemilikan" di frontend, dipicu manual | Diunggah manual oleh pengguna | Citra "tersangka" — bisa diunduh dari media sosial, tidak berasal dari sesi yang sama |

Mode (b) inilah yang menjawab skenario riil di BAB I: jurnalis menyimpan citra aslinya sendiri, lalu suatu waktu menemukan foto yang diduga miliknya beredar tanpa atribusi — keduanya diunggah untuk dibuktikan.

### 3.2 Skema Blind (cadangan, pengayaan)

Skema terpisah yang terbaca **tanpa citra asli**: bit = tanda selisih dua
koefisien mid-freq dalam blok yang sama (`F(2,3)−F(3,2) ≥ +alpha` → 1).
Tidak saling baca dengan skema non-blind (koefisien & logika beda).

| Verb | Path | Keterangan |
|------|------|------------|
| POST | `/api/watermark/embed-blind` | Sisip blind (teks/logo) + PSNR awal |
| POST | `/api/watermark/extract-blind` | Ekstrak blind: hanya `citra_input` + `key` + `jumlah_bit` (+ pembanding untuk NC/BER) |

Konsekuensi jujur: tanpa spreading-gain, ketahanan di bawah non-blind —
cadangan saat citra asli hilang, bukan pengganti utama. Di UI: radio skema
Non-blind/Blind di Mode 1 (Sisip) dan Mode 2 (Verifikasi).

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

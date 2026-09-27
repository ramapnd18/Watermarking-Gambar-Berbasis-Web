# BACKEND.md — Arsitektur Backend (aktual, per 27 Sep 2026)

**Proyek:** Aplikasi Watermarking Gambar Berbasis Web (DCT)
**Status dokumen:** Implementasi selesai — seluruh endpoint hidup & terverifikasi HTTP.

---

## 1. Tech Stack

| Komponen | Teknologi |
|----------|-----------|
| Framework Web | FastAPI + Uvicorn (`python main.py` → `http://127.0.0.1:8000`) |
| Paralelisme | `multiprocessing.Pool`, maks 4 worker (spawn-aman Windows) |
| Kriptografi inti | DCT/IDCT manual + spread-spectrum (tanpa cv2/scipy/numpy.fft) |
| Citra | Pillow (I/O + serangan), NumPy (array & PRNG deterministik saja) |
| Kunci | `secrets` (CSPRNG, runtime saja) + SHA-256 → `numpy.default_rng` |
| Uji/XLSX | pytest (12 test), openpyxl (`tools/jalankan_matriks.py`) |

Global prefix API: **`/api`**. Semua endpoint API mengembalikan **JSON** (kecuali
yang serve berkas). Citra dalam JSON = string `base64` PNG. Komentar, pesan
`galat`, dan UI berbahasa Indonesia. Antar modul, citra dioper sebagai
`PIL.Image`/`bytes`, baru menjadi `ndarray` di titik hitung.

---

## 2. Struktur Modul (`backend/`)

| Modul | Fungsi | Status |
|-------|--------|--------|
| `main.py` | Controller FastAPI, lock antrean, serve UI + logo acuan | ✅ Selesai |
| `dct_core.py` | 2D-DCT & IDCT manual blok 8x8 (double-summation eksplisit) | ✅ Selesai |
| `watermark_engine.py` | Blok 8x8 + DCT paralel; sisip/ekstrak non-blind & blind (kanal Y) | ✅ Selesai |
| `security.py` | `generate_secure_key` (secrets), PN bipolar/biner, permutasi posisi | ✅ Selesai |
| `attacker.py` | JPEG 90/70/50, noise, crop-25 (snap grid 8), resize, kontras+cerah, gabungan | ✅ Selesai |
| `evaluator.py` | PSNR (citra 2D), NC & BER (deret bit 1D) | ✅ Selesai |

---

## 3. Referensi Endpoint

### 3.0 Utilitas

| Verb | Path | Respons |
|------|------|---------|
| GET | `/` | `frontend/index.html` (UI 3 tab) |
| GET | `/health` | `{"status": "ok"}` (health-check monitoring/tunnel) |
| GET | `/api/aset/logo-pola` | PNG logo pola 32×32 (acuan Mode 3, apel-vs-apel vs XLSX) |
| GET | `/docs` | Swagger UI interaktif |

Kontrak galat seragam: `{"galat": "<pesan Bahasa Indonesia>"}` dengan status
400 (input), 404 (berkas tak-ada), 422 (validasi tipe FastAPI).

### 3.1 Watermark Non-Blind (skema utama)

| Field | embed | extract |
|-------|-------|---------|
| Masuk | `berkas` (cover), `key`, `alpha` (def 15), **satu** dari `teks` / `logo` | `citra_asli`, `citra_input`, `key`, `alpha`, `jumlah_bit`, `lebar_logo`/`tinggi_logo` (mode logo), **satu** dari `teks_asli` / `logo_asli` (opsional, untuk NC/BER) |
| Keluar | `mode`, `jumlah_bit`, `lebar_logo`, `tinggi_logo`, `psnr`, `lebar`, `tinggi`, `stego_base64` | `jumlah_bit`, `watermark_base64` (mode logo), `teks_hasil` (bila bit % 8 == 0), + `nc`, `ber`, `status_kepemilikan` (bila pembanding diberi) |

- `POST /api/watermark/embed` — rumus `F'(3,4) = F(3,4) + alpha·s·PN(i)` di kanal Y (YCbCr); warna lestari (RGB→RGB).
- `POST /api/watermark/extract` — dua mode pemakaian, satu endpoint:
  - (a) **Uji serangan:** `citra_input` = hasil `/api/attack/*` (dipanggil otomatis UI).
  - (b) **Verifikasi kepemilikan:** `citra_input` = citra tersangka luar sistem.
- Ambang `status_kepemilikan` (sementara, kalibrasi ulang pasca-data): ≥ 0.75 Kuat,
  0.4–0.75 Sebagian, < 0.4 Tidak Terdeteksi.
- **Toleran-crop:** input lebih kecil → pencarian offset blok (skor median
  `‖delta‖−alpha‖`), erasure → 0; gagal sinkron → 400 galat (bukan angka palsu).

### 3.2 Watermark Blind (skema cadangan, pengayaan)

Skema terpisah, **tidak saling baca** dengan non-blind (diuji:
`test_blind_tidak_saling_baca_dengan_nonblind`).

| Verb | Path | Beda dari non-blind |
|------|------|---------------------|
| POST | `/api/watermark/embed-blind` | Bit = tanda `F(2,3)−F(2,3)→F(3,2)` didorong ±alpha; respons + `"skema": "blind"` |
| POST | `/api/watermark/extract-blind` | **Tanpa** `citra_asli` dan `alpha`; hanya `citra_input` + `key` + `jumlah_bit` |

Jujur: tanpa spreading-gain → di bawah non-blind; cadangan saat citra asli hilang.

### 3.3 Serangan (PSNR-only, satu-tugas)

| Verb | Path | Field | Catatan |
|------|------|-------|---------|
| POST | `/api/attack/jpeg` | `berkas`, `kualitas` (1–95; uji 90/70/50), subsampling 4:4:4 | Artefak kuantisasi riil (round-trip buffer) |
| POST | `/api/attack/manipulation` | `berkas`, `jenis` (noise/crop/resize/kontras/gabungan), `std_noise` (10), `proporsi_crop` (0.25), `skala_resize` (0.5), `faktor_kontras` (1.2), `kecerahan` (20), `seed` (1) | Default = UJI.md §3.3 |
| POST | `/api/attack/semua` | `berkas`, `seed` | 8 hasil sekaligus (`jpeg_90/70/50`, `noise_gaussian`, `crop_tengah_25`, `resize_05`, `kontras_12`, `gabungan_q50_noise_crop`) |

Respons satuan: `nama, psnr, lebar, tinggi, citra_base64`.
**Aturan PSNR-nol-semu:** bila serangan mengubah ukuran (crop/gabungan),
`psnr` = `null` ("n/a (ukuran berubah)") — perbandingan sirkular memberi inf
palsu. NC/BER diperoleh dengan meneruskan citra hasil ke endpoint extract
(otomatis di UI).

---

## 4. Konkurensi & Robustness Operasional

- `KUNCI_BERAT = asyncio.Lock()` di `main.py`: embed/extract/semua diserialkan
  (satu jalan, sisanya antre) + komputasi via `asyncio.to_thread` agar event
  loop responsif. Tanpa ini, klik beruntun menumpuk Pool → OOM →
  `ERR_CONNECTION_RESET/REFUSED` (pernah terjadi, sudah diperbaiki).
- `_tentukan_jumlah_proses`: maks 4 worker (spawn Windows memuat ulang
  interpreter + NumPy per worker; fallback import menambah `backend/` ke
  `sys.path` agar spawn aman dari cwd mana pun).
- Batas praktis: foto ≤1024px untuk demo interaktif (512px ≈ 7 dtk/embed);
  foto resolusi penuh untuk batch XLSX saja.

---

## 5. Keamanan & Environment

- **WAJIB:** kunci tidak di-hardcode di mana pun (diuji
  `test_tidak_ada_kunci_hardcode`); tidak disimpan server (in-memory only);
  kunci uji matriks (`kunci-uji-*`) fixed demi reproduksibilitas dan BUKAN kunci produksi.
- Kunci runtime: `generate_secure_key()` (secrets, UI punya tombol Acak);
  derivasi seed deterministik SHA-256 → `default_rng` (reproduksibel untuk ekstraksi).
- Tidak ada database/berkas konfigurasi kunci → syarat "tidak diunggah ke GitHub" terpenuhi.

---

## 6. Logika Matematis Kritis

- **DCT-2D/IDCT:** double-summation kosinus eksplisit per blok 8×8 (`dct_core.py`).
- **Non-blind:** satu koefisien mid-freq (3,4) per bit, posisi dari permutasi kunci.
- **Blind:** pasangan koefisien (2,3)/(3,2), tanda selisih ≥ alpha.
- **Metrik:** PSNR = 10·log10(255²/MSE) (inf bila identik); NC = Σww'/√(Σw²Σw'²);
  BER = bit-beda/total-bit.

# Aplikasi Watermarking Gambar Berbasis Web (DCT)

Aplikasi web untuk menyisipkan watermark tak kasat mata (*invisible watermark*) ke aset visual jurnalistik menggunakan **Discrete Cosine Transform (DCT)** pada koefisien frekuensi menengah, lengkap dengan **simulasi serangan** (kompresi JPEG, crop, resize, noise, kontras) dan **kalkulasi metrik** (PSNR, NC, BER).

Dibuat untuk Tugas Proyek Keamanan Informasi, Universitas Siliwangi (Topik C — Digital Watermarking, tenggat 30 September 2026).

> Status saat ini: slice **uji serangan + PSNR sudah hidup**. Endpoint sisip/ekstrak watermark (`/api/watermark/embed`, `/api/watermark/extract`) menyusul setelah logika spread-spectrum di `watermark_engine.py` selesai.

## Fitur

1. **Penyisipan robust** — watermark (logo biner/teks) disisipkan via DCT blok 8x8 + spread spectrum (*dalam pengerjaan*).
2. **Simulasi serangan** — kompresi JPEG (kualitas 90/70/50), Gaussian noise, crop tengah, resize, kontras, dan gabungan Q50+noise+crop.
3. **Kalkulasi metrik** — PSNR otomatis tiap serangan; NC & BER untuk logo hasil ekstraksi (*menyusul bersama endpoint extract*).
4. **UI demo satu halaman** — unggah citra → klik tombol serangan → lihat citra rusak + skor PSNR (dB).

## Struktur Proyek

```text
digitalWatermaking/
├── main.py               # Peluncur: uvicorn di http://127.0.0.1:8000
├── backend/
│   ├── main.py           # Controller FastAPI + serve frontend/index.html
│   ├── dct_core.py       # 2D-DCT & IDCT manual (tanpa cv2/scipy)
│   ├── watermark_engine.py
│   ├── security.py       # CSPRNG pseudo-noise via `secrets`
│   ├── attacker.py       # Simulasi serangan (Pillow)
│   ├── evaluator.py      # PSNR, NC, BER
│   └── requirements.txt
├── frontend/
│   └── index.html        # UI tunggal (Vanilla JS + Tailwind CDN)
├── AI.md / BACKEND.md / FRONTEND.md / UJI.md / TODOLIST.md
└── README.md
```

## Prasyarat

- Python 3.10+
- pip + venv (disarankan)

## Cara Instalasi

```bash
# 1. Masuk ke root proyek
cd digitalWatermaking

# 2. Buat & aktifkan virtual environment (Windows)
python -m venv venv
venv\Scripts\activate

# Linux/macOS:
# python3 -m venv venv
# source venv/bin/activate

# 3. Instal dependensi
pip install -r backend/requirements.txt
```

Isi `backend/requirements.txt`: `fastapi`, `uvicorn`, `python-multipart`, `Pillow`, `numpy`.

## Cara Menjalankan

```bash
# Dari root proyek, venv aktif:
python main.py
# atau mode development (auto-reload):
# uvicorn backend.main:app --reload
```

Lalu buka **http://127.0.0.1:8000** di browser.

> ⚠️ Jangan buka frontend via **Live Server (`:5500`)** atau `file://` langsung — API `/api/attack/...` hanya ada di server FastAPI sehingga muncul error `405 Method Not Allowed`. Halaman kini menampilkan banner merah otomatis bila dibuka dari server yang salah.

## Contoh Penggunaan

### Via UI (disarankan untuk demo)

1. Buka `http://127.0.0.1:8000`.
2. Bagian **1. Unggah Citra** — pilih file gambar (JPG/PNG).
3. Bagian **2. Serangan Satuan** — klik mis. `JPEG 50`, `Noise`, `Crop 20%`, atau `Gabungan Q50+Noise+Crop`.
4. Bagian **3. Hasil & PSNR** — citra hasil + skor `PSNR: xx.xx dB` muncul sebagai kartu. Atau klik **Jalankan Semua Serangan** untuk paket lengkap sekaligus.

### Via API (curl / docs interaktif)

Dokumentasi interaktif: `http://127.0.0.1:8000/docs`

```bash
# Kompresi JPEG kualitas 50
curl -X POST http://127.0.0.1:8000/api/attack/jpeg \
  -F "berkas=@foto.jpg" -F "kualitas=50"

# Satu manipulasi (noise / crop / resize / kontras / gabungan)
curl -X POST http://127.0.0.1:8000/api/attack/manipulation \
  -F "berkas=@foto.jpg" -F "jenis=noise"

# Seluruh paket serangan sekaligus
curl -X POST http://127.0.0.1:8000/api/attack/semua \
  -F "berkas=@foto.jpg"
```

Semua endpoint API mengembalikan JSON; citra hasil dikirim sebagai string `citra_base64` (PNG) siap dipasang di `<img src="data:image/png;base64,...">`, beserta skor `psnr` (angka dB atau `"inf"` bila identik).

| Verb | Path | Keterangan |
|------|------|------------|
| GET | `/` | Halaman UI (`frontend/index.html`) |
| POST | `/api/attack/jpeg` | Kompresi JPEG (`kualitas`: 90/70/50) + PSNR |
| POST | `/api/attack/manipulation` | Satu manipulasi (`jenis`: noise/crop/resize/kontras/gabungan) + PSNR |
| POST | `/api/attack/semua` | Seluruh paket serangan + PSNR tiap hasil |
| POST | `/api/watermark/embed`, `/api/watermark/extract` | *Menyusul* |

## Anggota Kelompok

| No | Nama | NPM |
|----|------|-----|
| 1 | Nama Anggota 1 | NPM Anggota 1 |
| 2 | Nama Anggota 2 | NPM Anggota 2 |
| 3 | Nama Anggota 3 | NPM Anggota 3 |

> Ganti tabel di atas dengan nama & NPM sebenarnya sebelum pengumpulan.

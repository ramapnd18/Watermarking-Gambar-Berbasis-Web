# Aplikasi Watermarking Gambar Berbasis Web (DCT)

Aplikasi web untuk menyisipkan watermark tak kasat mata (*invisible watermark*) ke aset visual jurnalistik menggunakan **Discrete Cosine Transform (DCT)** pada koefisien frekuensi menengah, lengkap dengan **simulasi serangan** (kompresi JPEG, crop, resize, noise, kontras) dan **kalkulasi metrik** (PSNR, NC, BER).

Dibuat untuk Tugas Proyek Keamanan Informasi, Universitas Siliwangi (Topik C — Digital Watermarking, tenggat 30 September 2026).

> Status: seluruh fitur hidup — sisip/ekstrak non-blind + blind, 8 serangan + PSNR/NC/BER, UI 3 tab, matriks uji hijau (lihat `hasil_pengujian.md`).

## Fitur

1. **Penyisipan robust** — watermark (logo biner/teks) disisipkan via DCT blok 8x8: spread spectrum non-blind + skema blind cadangan (tanda selisih koefisien, terbaca tanpa citra asli).
2. **Simulasi serangan** — kompresi JPEG (kualitas 90/70/50), Gaussian noise, crop tengah 25% (snap grid 8px), resize, kontras + kecerahan, dan gabungan Q50+noise+crop.
3. **Kalkulasi metrik** — PSNR tiap serangan; NC & BER otomatis via ekstraksi (non-blind toleran-crop / blind).
4. **UI 3 tab** — Sisip & Uji Serangan (NC/BER otomatis + dashboard), Verifikasi Kepemilikan mandiri, Watermark di Citra AI (pengayaan §5).

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

Isi `backend/requirements.txt`: `fastapi`, `uvicorn`, `python-multipart`, `Pillow`, `numpy`, `openpyxl`, `pytest`.

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
3. Bagian **2. Serang Stego** — klik mis. `JPEG 50`, `Noise`, `Crop 25%`, atau `Gabungan Q50+Noise+Crop` (NC/BER + watermark terekstrak muncul otomatis).
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
| GET | `/` | Halaman UI 3 tab (Sisip & Uji, Verifikasi, Watermark di Citra AI) |
| POST | `/api/watermark/embed` | Sisip non-blind teks/logo + PSNR awal |
| POST | `/api/watermark/extract` | Ekstrak non-blind + NC/BER bila pembanding diberi |
| POST | `/api/watermark/embed-blind` | Sisip blind (cadangan tanpa citra asli) + PSNR |
| POST | `/api/watermark/extract-blind` | Ekstrak blind + NC/BER bila pembanding diberi |
| POST | `/api/attack/jpeg` | Kompresi JPEG (`kualitas`: 90/70/50) + PSNR |
| POST | `/api/attack/manipulation` | Satu manipulasi (`jenis`: noise/crop/resize/kontras/gabungan) + PSNR |
| POST | `/api/attack/semua` | Seluruh paket serangan + PSNR tiap hasil |

## Anggota Kelompok

| No | Nama | NPM |
|----|------|-----|
| 1 | Aini Nurfadilah | 247006111021 |
| 2 | Rina Natalia | 247006111033 |
| 3 | Rama Tri Ramdhani | 247006111057 |

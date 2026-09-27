# AI.md

Panduan untuk Asisten AI (LLM) saat melakukan *vibecoding* dan bekerja di dalam repository ini.

---

## Ringkasan Proyek

**Aplikasi Watermarking Gambar Berbasis Web (Topik C — Digital Watermarking)**

Dikembangkan untuk Tugas Proyek Keamanan Informasi, Universitas Siliwangi (Tenggat: 30 September 2026). Aplikasi menyisipkan identitas/watermark tak kasat mata (*invisible*) ke aset visual jurnalistik independen (foto resolusi tinggi) menggunakan **Discrete Cosine Transform (DCT)** pada koefisien frekuensi menengah.

Tiga pilar produk:
1. **Penyisipan Robust** — menyisipkan watermark (logo biner/teks) ke gambar, tahan terhadap modifikasi visual.
2. **Simulasi Serangan** — modul pengujian interaktif yang merusak *stego-image* secara sengaja (kompresi JPEG, cropping, resize, noise, kontras) untuk menguji ketahanan algoritma.
3. **Kalkulasi Metrik** — ekstraksi watermark dan perhitungan performa otomatis (PSNR, *Normalized Correlation*/NC, *Bit Error Rate*/BER).

---

## Tech Stack

### Backend (`/backend`)
- **Python 3.10+**
- **FastAPI + Uvicorn** — framework web & server API
- **Multiprocessing (bawaan Python)** — pemrosesan matriks paralel berbasis blok 8x8 untuk mencegah *bottleneck* CPU pada gambar resolusi tinggi
- **Pillow (PIL)** — HANYA untuk membaca file citra dan simulasi serangan gambar
- **NumPy** — manipulasi array 2D dasar, BUKAN untuk fungsi DCT-nya
- **`secrets`** (bawaan Python) — CSPRNG untuk membangkitkan deret pseudo-noise (kunci rahasia) secara aman

### Frontend (`/frontend`)
- **HTML5 + Vanilla JavaScript** — tanpa framework JS (tanpa Node.js/NPM), ringan dan mudah di-*deploy*
- **Tailwind CSS (via CDN)** — styling antarmuka
- **Fetch API** — komunikasi AJAX (`FormData`) ke endpoint FastAPI

---

## Command Penting

Dijalankan dari root directory:

```bash
pip install -r requirements.txt   # Instal dependensi (FastAPI, Uvicorn, Pillow, NumPy, python-multipart)
python main.py                    # Jalankan server lokal via Uvicorn (http://127.0.0.1:8000)
uvicorn main:app --reload         # Mode development (auto-restart saat kode diubah)
pytest tests/                     # (Opsional) Jalankan unit test ekstraksi/metrik
```

---

## Struktur Modul Backend

> Path flat `backend/*.py` (bukan `backend/src/*.py`), mengikuti struktur repo yang sudah di-*push*.

| Modul | Fungsi | Status |
|-------|--------|--------|
| `main.py` | Routing API FastAPI, integrasi UI | Belum mulai |
| `dct_core.py` | Algoritma DCT & IDCT matematis (kalkulasi manual) | ✅ Selesai |
| `watermark_engine.py` | Multiprocessing: pemecahan gambar ke blok 8x8 & spread spectrum | Belum mulai |
| `security.py` | CSPRNG (`secrets`) untuk pseudo-noise sequence | ✅ Selesai |
| `attacker.py` | Simulasi serangan (Pillow/PIL) | Belum mulai |
| `evaluator.py` | Kalkulasi PSNR, NC, BER | Belum mulai |

---

## Aturan Ketat (WAJIB DIPATUHI AI)

1. **Larangan pustaka untuk logika inti** — Transformasi 2D-DCT/IDCT dan penyisipan frekuensi menengah WAJIB ditulis sendiri secara matematis (sigma/*double-summation* cosinus eksplisit). DILARANG KERAS memakai `cv2.dct()`, `scipy.fftpack.dct()`, `numpy.fft`, atau fungsi bawaan sejenis.
2. **Manajemen kunci rahasia** — Kunci, kata sandi, dan seed pseudo-noise TIDAK BOLEH di-*hardcode* di kode sumber **maupun diunggah ke GitHub** (ketentuan tugas melarang keduanya). Gunakan `secrets` atau `os.urandom` saat runtime, atau tangkap dari input antarmuka. Karena arsitektur ini *in-memory only* (lihat `BACKEND.md` §5 — tidak ada database/berkas konfigurasi yang menyimpan kunci), syarat "tidak diunggah ke GitHub" otomatis terpenuhi — tidak ada apa pun yang bisa ter-commit.
3. **Simulasi serangan wajib** — Kompresi JPEG harus diuji pada tiga level kualitas: **90, 70, dan 50**, ditambah *cropping*, *resize*, Gaussian *noise*, dan perubahan kontras.
4. **Metrik evaluasi** — PSNR membandingkan citra 2D (asli vs stego); NC dan BER membandingkan deret bit/array 1D (logo asli vs logo hasil ekstraksi).
5. **Unit test wajib** — Minimal 5 unit test untuk fungsi inti (Ketentuan Teknis Umum Bagian 4), ditaruh di `tests/` dan dijalankan via `pytest tests/`. ⚠️ **Status saat ini:** `dct_core.py` dan `security.py` baru punya self-check informal (blok `__main__`), BELUM dibungkus jadi test resmi di `tests/` — lihat `UJI.md` §4 dan `TODOLIST.md` untuk daftar 5 test yang perlu dipindahkan.

---

## Konvensi Kode

- **Bahasa Indonesia** — semua komentar, nama endpoint, deskripsi error, dan teks antarmuka (frontend) memakai Bahasa Indonesia.
- **Respons JSON** — semua endpoint API (kecuali yang serve HTML) mengembalikan response berformat JSON.
- **Tipe data gambar** — gunakan `bytes` atau objek `PIL.Image` saat mengoper gambar antar modul, sebelum diubah ke `numpy.ndarray`.

---

## Prasyarat

Dataset citra uji coba resolusi tinggi (misal: koleksi foto zine dokumenter peternakan) disiapkan di `/tests/assets/`.

---

## Integritas Akademik & Penggunaan AI (Bagian 10 Ketentuan Tugas)

⚠️ **Belum ada rencana untuk ini sebelum audit ini** — ditambahkan sekarang karena wajib menurut dokumen ketentuan:

- Dokumen ketentuan tugas menyatakan: *"Asisten AI boleh dipakai untuk membantu belajar dan menulis kode. Bagian yang dibantu AI wajib disebutkan pada lampiran laporan."*
- Karena seluruh proyek ini dikerjakan lewat *vibecoding* bersama AI, laporan **wajib** menyertakan **Lampiran Penggunaan AI** yang merinci modul mana yang dibantu AI dan sejauh mana (mis. "seluruh isi `dct_core.py` dan `security.py` ditulis berdasarkan prompt di AI.md, diverifikasi lewat self-check matematis").
- Setiap anggota tetap harus bisa menjelaskan kode yang dikumpulkan — ketidakmampuan menjelaskan mengurangi nilai individu, terlepas dari siapa yang menulis kodenya.
- Ditambahkan sebagai task baru di `TODOLIST.md`.

---

## Dokumen Terkait

- `BACKEND.md` — Arsitektur API, modul pemrosesan Python, dan formula evaluasi
- `FRONTEND.md` — Layout UI, manajemen state via Vanilla JS
- `UJI.md` — Rencana pengujian kuantitatif, unit test wajib, dan kerangka analisis trade-off
- `TODOLIST.md` — Checklist progres hingga tenggat 30 September 2026

---

## Lampiran: Kumpulan Prompt AI (Vibecoding Guide)

Contoh prompt acuan bila developer meminta AI membuat fungsi tertentu.

**Prompt 1 — Logika DCT Murni**
> "Buatkan fungsi Python murni untuk 2D-DCT dan Inverse 2D-DCT pada matriks 8x8. JANGAN gunakan `cv2.dct()` atau `scipy.fft`. Tulis rumus *double-summation* cosinusnya secara eksplisit dari awal."

**Prompt 2 — Pembangkit Kunci Aman**
> "Buatkan fungsi Python dengan modul `secrets` untuk membangkitkan deret pseudo-random biner (0/1) sepanjang N, dari seed string yang diinput pengguna, untuk menentukan posisi watermark."

**Prompt 3 — Pemrosesan Paralel**
> "Buatkan skrip yang memecah gambar (PIL/NumPy array) menjadi blok 8x8, lalu gunakan `multiprocessing.Pool` untuk menerapkan `hitung_dct_8x8` ke seluruh blok secara paralel."

**Prompt 4 — Skrip Simulasi Serangan**
> "Buatkan fungsi yang menerima PIL Image lalu mengembalikan gambar yang sudah dikenai serangan: kompresi JPEG kualitas 50, Gaussian noise, dan cropping 20% area tengah."

**Prompt 5 — Kalkulasi Metrik**
> "Tulis fungsi PSNR antara dua gambar, lalu fungsi NC dan BER antara dua array biner 1D."

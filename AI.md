# AI.md

Panduan untuk Asisten AI (LLM) saat melakukan *vibecoding* dan bekerja di dalam *repository* ini.

---

## Ringkasan Projek

**Aplikasi Watermarking Gambar Berbasis Web (Topik C - Digital Watermarking)**.

Aplikasi ini dikembangkan untuk Tugas Proyek Keamanan Informasi Universitas Siliwangi (Tenggat: 30 September 2026). Web ini berfungsi untuk menyisipkan identitas/watermark secara tak kasat mata (*invisible*) ke dalam aset visual jurnalistik independen (misal: foto resolusi tinggi) menggunakan algoritma **Discrete Cosine Transform (DCT)** pada koefisien frekuensi menengah. 

Tiga pilar produk:
1. **Penyisipan Robust** — Menyisipkan *watermark* (logo biner/teks) ke dalam gambar dan tahan terhadap modifikasi visual.
2. **Simulasi Serangan** — Modul pengujian interaktif yang merusak *stego-image* secara sengaja (Kompresi JPEG, *Cropping*, *Resize*, *Noise*, Kontras) untuk menguji ketahanan algoritma.
3. **Kalkulasi Metrik** — Ekstraksi *watermark* dan perhitungan performa secara otomatis menggunakan PSNR, Normalized Correlation (NC), dan Bit Error Rate (BER).

---

## Tech Stack

### Backend (`/backend`)
- **Python 3.10+** (Bahasa pemrograman utama).
- **FastAPI + Uvicorn** — Kerangka kerja web dan *server* API.
- **Multiprocessing (Native Python)** — Pemrosesan matriks paralel berbasis blok 8x8 untuk mencegah *bottleneck* CPU pada gambar resolusi tinggi.
- **Pillow (PIL)** — Digunakan **HANYA** untuk membaca *file* citra dan simulasi serangan gambar (JPEG, *crop*, *resize*, dll).
- **Numpy** — Digunakan untuk manipulasi *array* 2D dasar, BUKAN untuk fungsi DCT-nya.
- **`secrets` (Native Python)** — CSPRNG untuk membangkitkan deret *pseudo-noise* (kunci rahasia) secara aman.

### Frontend (`/frontend` atau `/static`)
- **HTML5 + Vanilla JavaScript** — Tanpa *framework* JS (tanpa Node.js/NPM) agar ringan dan mudah di-*deploy*.
- **Tailwind CSS (via CDN)** — *Styling* antarmuka.
- **Fetch API** — Untuk komunikasi AJAX (`FormData`) ke *endpoint* FastAPI.

---

## Command Penting

Di dalam terminal (jalankan di *root directory*):

```bash
pip install -r requirements.txt  # Menginstal dependensi (FastAPI, uvicorn, pillow, numpy, python-multipart)
python main.py                   # Menjalankan server lokal via Uvicorn (Akses di [http://127.0.0.1:8000](http://127.0.0.1:8000))
uvicorn main:app --reload        # Mode *development* (otomatis restart saat kode diubah)
pytest tests/                    # (Opsional) Jalankan unit test ekstraksi/metrik

## Arsitektur & Aturan Ketat (WAJIB DIBACA AI)
1. Larangan Penggunaan Pustaka untuk Logika Inti
    SANGAT KRITIKAL: Logika transformasi matriks 2D-DCT dan penyisipan frekuensi menengah WAJIB ditulis sendiri secara matematis.   
    TIDAK BOLEH menggunakan cv2.dct() dari OpenCV, scipy.fftpack.dct(), atau fungsi bawaan sejenis dari library kriptografi/matematika modern.   
2. Manajemen Kunci RahasiaKunci, kata sandi, dan seed pseudo-noise 
    TIDAK BOLEH ditulis langsung (hardcoded) di dalam kode sumber.   
    Gunakan pembangkit bilangan acak yang aman secara kriptografis seperti modul secrets atau os.urandom saat runtime.   
3. Struktur Modul Backendmain.py — Routing API FastAPI dan integrasi UI.dct_core.py — Algoritma DCT dan IDCT matematis (kalkulasi manual).
watermark_engine.py — Logika multiprocessing pemecahan gambar ke matriks 8x8 dan spread spectrum.attacker.py — Fungsi simulasi serangan (memanfaatkan Pillow/PIL)[cite: 2].
security.py — CSPRNG menggunakan secrets[cite: 2].
evaluator.py — Rumus kalkulasi PSNR, NC, dan BER[cite: 2].
## Konvensi KodeBahasa Indonesia: 
Semua komentar, nama endpoint, deskripsi error, dan teks antarmuka (frontend) harus menggunakan Bahasa Indonesia.
Respons JSON: Semua endpoint API (kecuali serve HTML) harus mengembalikan response dengan format JSON.
Tipe Data Gambar: Gunakan tipe data bytes atau objek PIL.Image saat mengoper gambar antar modul sebelum diubah ke numpy.ndarray.
Panduan Prompting Cepat untuk AI (Konteks Tugas) Jika developer meminta untuk membuat suatu fungsi, rujuk format perintah di bawah ini:
Jika membuat modul DCT: Ingat bahwa AI harus menjabarkan rumus sigma ganda (double summation) secara eksplisit tanpa import scipy.
Jika membuat simulasi serangan: Ingat bahwa tugas mewajibkan parameter kompresi JPEG harus menguji kualitas 90, 70, dan 50[cite: 2].
Jika membuat fungsi metrik: Ingat bahwa PSNR membandingkan citra 2D (asli vs stego), sedangkan NC dan BER membandingkan deret bit/array 1D (logo asli vs logo terekstraksi)[cite: 2].
## Prasyarat 
Dataset citra uji coba beresolusi tinggi (misal: koleksi foto zine pencarian pakan) disiapkan di /tests/assets/.
## Arsitektur & Aturan Ketat (WAJIB DIPATUHI)
LARANGAN PUSTAKA UTAMA: Logika transformasi 2D-DCT dan IDCT wajib ditulis secara matematis murni menggunakan perulangan/sigma cosinus[cite: 2]. Dilarang keras menggunakan scipy.fftpack.dct, cv2.dct, atau algoritma bawaan sejenis[cite: 2].
KREDENSIAL: Kunci rahasia (seed pseudo-noise) TIDAK BOLEH di-hardcode di dalam skrip[cite: 2]. Kunci ini di-generate saat runtime atau ditangkap dari input antarmuka.
METRIK SERANGAN: Serangan kompresi JPEG wajib diuji pada tiga level kualitas: 90, 70, dan 50[cite: 2].
## Dokumen Terkait
BACKEND.mdArsitektur API, modul pemrosesan Python, dan formula evaluasi
FRONTEND.mdLayout UI, manajemen state via Vanilla JS
TODOLIST.md Checklist progres hingga tenggat 30 September 2026
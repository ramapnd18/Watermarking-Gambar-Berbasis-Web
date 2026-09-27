# FRONTEND.md — Arsitektur Frontend (aktual, per 27 Sep 2026)

**Proyek:** Aplikasi Watermarking Gambar Berbasis Web (DCT)
**Status dokumen:** Implementasi selesai — 3 tab, terverifikasi serve + `node --check`.

---

## 1. Tech Stack

| Komponen | Teknologi |
|----------|-----------|
| Halaman | `frontend/index.html` (satu berkas, tanpa build step) |
| Styling | Tailwind CSS via CDN |
| State | Vanilla JS, variabel per-mode (isolasi antar-tab) |
| HTTP | Fetch API + `FormData` (multipart, field `berkas`/`citra_*` + blob + filename) |

**Wajib dibuka via backend** (`http://127.0.0.1:8000`). Dibuka via Live Server
`:5500`/`file://` → banner merah + error 405 yang dijelaskan (fetch relatif
`/api/...` hanya ada di FastAPI).

---

## 2. Tata Letak — 3 Tab (tanpa reload, state tidak direset saat pindah)

### Mode 1 — Sisip & Uji Serangan (demo UTS)

1. **Sisipkan:** cover + kunci (+tombol Acak, `crypto.getRandomValues` 16 byte hex)
   + radio teks/logo + radio skema Non-blind/Blind + alpha (def 15) → `POST`
   embed → panel Cover vs Stego + PSNR + status *"Catat untuk Verifikasi:
   skema, jumlah_bit, alpha, pembanding"* + tombol **Salin ke Verifikasi**.
2. **Action Bar:** JPEG 90/70/50, Noise, Crop 25%, Resize, Kontras +20%,
   Gabungan, Jalankan Semua Serangan. Beroperasi pada **stego** (bukan cover);
   aktif setelah embed.
3. **Hasil:** kartu citra + PSNR (vs stego; `n/a` bila ukuran berubah) +
   **NC/BER + status + watermark terekstrak otomatis** (extract dipanggil per
   hasil; crop beda-ukuran ikut jalur toleran-crop backend).
4. **Dashboard sticky:** PSNR embed + NC/BER/status terakhir.
5. **Tombol dikunci** selama request (`setSibukM1`) — anti double-klik
   penumpuk DCT server.

### Mode 2 — Verifikasi Kepemilikan (mandiri)

Slot: citra asli + tersangka + kunci + jumlah_bit (**bulat**, divalidasi client —
bukan PSNR) + alpha + radio skema + pembanding (teks / logo + dimensi).
Skema Blind menyembunyikan slot citra asli. Tombol → `POST` extract(-blind) →
logo/teks hasil + NC/BER + label status awam.

### Mode 3 — Watermark di Citra AI (pengayaan §5)

Alur Mode 1 yang dirampingkan (logo pola 32×32 **diunduh dari
`/api/aset/logo-pola`** agar identik dengan matriks XLSX) + **tabel banding
live**: NC AI vs rata-rata 3 citra utama (nilai acuan statis dari XLSX) +
selisih. Bukan detektor "buatan-AI-atau-bukan" — panel menulis eksplisit.

---

## 3. State & Alur Data

- **Mode 1:** `S1 = {cover, stego(Blob), nbit, wmMode, teks/logo(+W/H), key,
  alpha, stegoW/H, skema}`. `fdEkstrak()` mengembalikan `{fd, url}` sesuai
  skema (blind: tanpa `citra_asli`/`alpha`, ke `/extract-blind`).
- **Mode 2/3:** variabel/state DOM lokal per panel; `pilihTab(nomor)` hanya
  toggle `hidden` + warna tab.
- **`kirim(url, fd)`:** `fetch POST` + pesan galat ramah (405 → arahkan ke
  `:8000`; putus → suruh cek server). `base64KeBlob()` untuk rantai
  serang→ekstrak tanpa mengunduh file.
- **`kartuHasil()`:** PSNR (`fmtPsnr`: `inf`/`n/a`/dB) + NC/BER/status +
  `teks_hasil`/thumbnail logo + catatan galat server apa adanya.

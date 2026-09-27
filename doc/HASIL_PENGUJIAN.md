# Hasil Pengujian — Digital Watermarking DCT (Topik C)

**Tanggal run:** 27 September 2026 · **Runner:** `tools/jalankan_matriks.py`
**Konfigurasi:** logo pola biner 32×32 (1024 bit), alpha 15 (kecuali matriks trade-off),
kunci fixed reproduksibel `kunci-uji-<citra>`, seed noise 1.
**Sumber angka:** `hasil_pengujian.xlsx` (4 sheet) + log run matriks.
Citra uji 1024×512 RGB: `citra_01_tekstur_tinggi`, `citra_02_area_datar`,
`citra_03_potret_wajah` di `tests/assets/`; bukti citra di `tests/assets/hasil/<citra>/`.

> Konvensi: PSNR = stego vs asli (§3.1) atau hasil-serangan vs stego (§3.2–§3.3).
> `n/a (ukuran berubah)` = crop/gabungan mengubah dimensi sehingga PSNR sirkular
> (inf semu) — sengaja tidak dilaporkan. `tak-tersinkron` = sinkronisasi blok
> tak-ditemukan (dijelaskan di Insight 5).

---

## 1. §3.1 — PSNR Embed (invisibility, tanpa serangan)

| Citra | Alpha | PSNR (dB) | Waktu (s) |
|-------|-------|-----------|-----------|
| citra_01_tekstur_tinggi | 15 | 45.24 | 4.3 |
| citra_02_area_datar | 15 | 44.35 | 4.3 |
| citra_03_potret_wajah | 15 | 49.15 | 4.2 |

**Insight 1 — Syarat tak-kasatmata terpenuhi dengan margin besar.**
Ambang literatur: >40 dB = distorsi tak-terlihat, >30 dB = wajar. Ketiganya
44–49 dB. Potret wajah tertinggi (49.15 dB): area kulit yang halus membuat
perubahan ±alpha pada satu koefisien mid-freq per blok nyaris tak-berpengaruh
pada MSE — sekaligus peringatan bahwa area halus menyimpan sedikit "redundansi"
untuk ketahanan (terbukti di §3.2: JPEG70 citra_03 ambruk ke NC 0.52).

## 2. §3.2 — Kompresi JPEG 90/70/50 (NC/BER pasca-ekstraksi)

| Citra | Kualitas | PSNR (dB) | NC | BER (%) | Status |
|-------|----------|-----------|----|---------|--------|
| citra_01 | 90 | 47.52 | 1.0000 | 0.00 | Kuat |
| citra_01 | 70 | 40.73 | 0.6527 | 32.81 | Sebagian* |
| citra_01 | 50 | 36.43 | 0.5283 | 44.73 | Sebagian |
| citra_02 | 90 | 50.84 | 1.0000 | 0.00 | Kuat |
| citra_02 | 70 | 45.92 | 0.4646 | 47.95 | Sebagian |
| citra_02 | 50 | 43.77 | 0.4188 | 51.27 | Sebagian |
| citra_03 | 90 | 53.21 | 1.0000 | 0.00 | Kuat |
| citra_03 | 70 | 46.00 | 0.5201 | 46.09 | Sebagian |
| citra_03 | 50 | 41.83 | 0.4815 | 49.32 | Sebagian |

\* Ambang label: Kuat ≥ 0.75, Sebagian 0.4–0.75 (BACKEND.md §3.1, sementara).

**Insight 2 — JPEG 90 tahan sempurna; JPEG 70/50 adalah titik lemah metode.**
NC = 1.0 di semua citra pada kualitas 90 (kompresi ringan tak-menyentuh
koefisien sisipan (3,4)). Pada 70/50, kuantisasi JPEG memusnahkan koefisien
mid-freq tempat bit disisipkan → NC 0.42–0.65. Citra datar (02) paling parah:
area halus → energi AC kecil → koefisien tersisip dikuantisasi habis lebih dulu.
Implikasi demo/laporan: klaim "robust" berlaku untuk kompresi ringan–sedang
(medsos kualitas tinggi), BUKAN kompresi agresif — kecuali alpha dinaikkan
(lihat §4: alpha 30 mengangkat NC JPEG50 citra_02 ke 0.827).

## 3. §3.3 — Manipulasi Geometris & Visual

| Citra | Serangan | PSNR (dB) | NC | BER (%) | Status |
|-------|----------|-----------|----|---------|--------|
| 01 | noise_gaussian σ=10 | 28.95 | 0.9427 | 5.18 | Kuat |
| 01 | crop_tengah_25 | n/a | 0.8598 | 11.82 | Kuat |
| 01 | resize_05 | 30.97 | 0.4021 | 52.05 | Sebagian |
| 01 | kontras_12 (+20%/+20) | 25.14 | 0.8176 | 15.04 | Kuat |
| 02 | noise_gaussian σ=10 | 28.85 | 0.9171 | 7.62 | Kuat |
| 02 | crop_tengah_25 | n/a | 0.8623 | 11.62 | Kuat |
| 02 | resize_05 | 41.14 | 0.3905 | 53.12 | — (di bawah 0.4) |
| 02 | kontras_12 (+20%/+20) | 26.11 | 0.8240 | 14.55 | Kuat |
| 03 | noise_gaussian σ=10 | 30.11 | 0.8651 | 12.30 | Kuat |
| 03 | crop_tengah_25 | n/a | 0.8698 | 11.04 | Kuat |
| 03 | resize_05 | 37.73 | 0.1624 | 63.87 | — (di bawah 0.4) |
| 03 | kontras_12 (+20%/+20) | 31.63 | 0.4559 | 35.94 | Sebagian |
| 01/02/03 | gabungan_q50_noise_crop | n/a | tak-tersinkron | tak-tersinkron | — |

**Insight 3 — Noise & crop: tahan. Resize: titik lemah.**
Noise Gaussian (NC 0.87–0.94): spread-spectrum memang dirancang untuk ini —
noise tak-berkorelasi dengan PN dirata-ratakan keluar saat voting tanda.
Crop 25% (NC ≈ 0.86 konsisten di 3 citra): bukti ekstraksi toleran-crop bekerja;
11–12% BER ≈ porsi bit yang bloknya terpotong (erasure jujur → 0).
Resize 0.5→1.0 (NC 0.16–0.40, BER > 50%): resampling ganda menghancurkan
koefisien mid-freq secara sistematis (BER > 50% = pembalikan tanda, bukan acak).
Ini keterbatasan bawaan DCT-blok non-blind, bahan analisis Bab V.

**Insight 4 — Kontras berperilaku tak-seragam antar-citra (0.82/0.82/0.46).**
Scaling kontras mempertahankan TANDA delta (kunci ketahanan metode ini), tetapi
kliping 0–255 pada citra wajah (rentang nada sempit) memenggal sebagian sinyal.
Catatan metodologi: faktor 1.2 + brightness 20 adalah serangan fotometrik
"kasar" (PSNR 20–31 dB, citra sudah terlihat rusak) — NC 0.82 dalam kondisi itu
justru nilai jual.

**Insight 5 — Gabungan 3 serangan = batas ketahanan kuantitatif.**
Q50+noise+crop tak-tersinkron di SEMUA citra. Investigasi: 162 kandidat offset,
5 terbaik datar di skor ≈10.5 (median ||delta|−alpha|), tanpa pemenang —
sinyal dan beda-konten tak-terpisahkan. Upaya perbaikan diskriminator
(mean→median) dicoba dan dihentikan sadar agar tak mengarang data.
Kalimat laporan: *"metode bertahan terhadap tiap serangan tunggal, tetapi
kombinasi tiga serangan memutus sinkronisasi hingga ekstraksi mustahil."*

## 4. §6 — Trade-off Alpha (citra_02, serangan JPEG 50)

| Alpha | PSNR embed (dB) | NC pasca-JPEG50 | BER (%) |
|-------|-----------------|-----------------|---------|
| 5 (lemah) | 45.02 | 0.4183 | 51.37 |
| 15 (sedang) | 44.35 | 0.4188 | 51.27 |
| 30 (kuat) | 42.90 | 0.8270 | 15.82 |

**Insight 6 — Jawaban Tujuan #4: alpha 5→15 tidak mengubah apa pun, 30 mengubah segalanya.**
Kenaikan 5→15 hanya menurunkan PSNR 0.7 dB tanpa perbaikan NC (ambang
kuantisasi JPEG50 menelan keduanya). Alpha 30 menembus ambang kuantisasi:
NC 0.42→0.83 dengan harga PSNR 45.0→42.9 dB — masih di atas ambang
tak-kasatmata 40 dB. **Rekomendasi operasional:** default 15 untuk kanal bersih,
30 untuk kanal yang pasti dikompres ulang (medsos). Titik keseimbangan ada di
antara 15–30; pemetaan halus (mis. 20/25) diusulkan sebagai kerja lanjutan.

## 5. Unit Test (`pytest tests/` — 10/10 hijau, ~1 detik)

| Test | Verifikasi |
|------|------------|
| dct_idct_reconstruction | IDCT(DCT(blok)) ≈ blok, galat < 1e-6 |
| dct_blok_konstan_hanya_dc | blok konstan → hanya DC = 8c (jawaban dikenal) |
| dct_menolak_blok_salah_ukuran | validasi 8×8 ditegakkan |
| key_unik / deterministik / permutasi / tanpa-hardcode (4) | secrets, sensitivitas kunci, amendments Bagian 10 |
| embed_extract_tanpa_serangan | NC ≥ 0.99, BER = 0, PSNR > 30 |
| embed_extract_setelah_jpeg50 | NC > 0.7 (bukti robust, citra mungil 64×64) |
| psnr_identik_inf | PSNR citra identik = inf |

## 6. Trio Demo Video (rekomendasi berbasis data, bukan tebakan)

**JPEG 50 + Noise + Kontras** — ketiganya ber-NC terukur di semua citra
(0.42–0.83 / 0.87–0.94 / 0.46–0.82), mewakili tiga kategori (kompresi,
stokastik, fotometrik), tanpa crop (butuh penjelasan sinkronisasi) dan tanpa
resize (NC < 0.4, terlihat gagal di depan dosen).

## 7. §5 Pengayaan — Watermark pada Citra AI-Generatif (2816×1536)

| Serangan | NC (AI) | BER (AI) % | NC rata-rata 3 citra | Selisih NC |
|----------|---------|------------|----------------------|------------|
| jpeg_50 | 0.4985 | 47.66 | 0.4762 | +0.0223 |
| noise_gaussian | 0.9849 | 1.37 | 0.9083 | +0.0766 |
| crop_tengah_25 | 0.8710 | 10.94 | 0.8640 | +0.0070 |

**Insight 7 — Citra AI sedikit LEBIH tahan di semua serangan yang diuji.**
Tekstur sintetis yang merata memberi koefisien mid-freq yang "bersih" untuk
sisipan (noise +0.08 paling menonjol — sejalan dengan teori spread-spectrum).
**Caveat jujur untuk laporan:** citra AI (2816×1536, 67 ribu blok) jauh lebih
besar dari 3 citra utama (1024×512), sehingga penempatan 1024 bit lebih renggang
— selisih +0.02 pada JPEG50 bisa murni efek sparsitas, bukan sifat AI. Kerja
lanjutan yang benar: ulangi dengan citra AI yang di-resize ke 1024×512.

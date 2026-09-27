"""attacker.py — Simulasi serangan terhadap stego-image untuk uji ketahanan.

Modul ini MERUSAK citra secara sengaja memakai Pillow & NumPy (diizinkan
aturan AI.md: Pillow HANYA untuk baca citra dan simulasi serangan).
Tujuannya menguji ketahanan watermark DCT: setelah diserang, citra
diekstrak kembali lalu dihitung NC & BER-nya (lihat evaluator.py).

Jenis serangan wajib (aturan ketat AI.md no. 3):
- Kompresi JPEG pada kualitas 90, 70, dan 50.
- Cropping, resize, Gaussian noise, dan perubahan kontras.

Antar modul, citra dioper sebagai `bytes` atau `PIL.Image` sebelum
diubah ke `numpy.ndarray`.

Semua komentar dan pesan error memakai Bahasa Indonesia.
"""

import io

import numpy as np
from PIL import Image

# Kualitas JPEG wajib diuji menurut aturan proyek.
KUALITAS_JPEG_WAJIB = (90, 70, 50)

# Ukuran blok DCT (disamakan dengan watermark_engine.UKURAN_BLOK).
UKURAN_BLOK_DCT = 8


# ---------------------------------------------------------------------------
# Normalisasi masukan (bytes / PIL.Image / ndarray -> PIL.Image)
# ---------------------------------------------------------------------------

def _ke_pil(citra) -> Image.Image:
    """Mengubah citra (PIL.Image / bytes / ndarray) menjadi PIL.Image."""
    if isinstance(citra, Image.Image):
        if citra.width == 0 or citra.height == 0:
            raise ValueError("Citra PIL kosong (lebar/tinggi nol).")
        return citra
    if isinstance(citra, bytes):
        try:
            gambar = Image.open(io.BytesIO(citra))
            gambar.load()
        except Exception as eronya:
            raise ValueError(f"Bytes gambar tidak dapat dibaca: {eronya}.")
        if gambar.width == 0 or gambar.height == 0:
            raise ValueError("Citra dari bytes kosong (lebar/tinggi nol).")
        return gambar
    if isinstance(citra, np.ndarray):
        if citra.size == 0:
            raise ValueError("Array gambar kosong.")
        larik = np.clip(np.rint(citra), 0, 255).astype(np.uint8)
        if citra.ndim == 2:
            return Image.fromarray(larik, mode="L")
        if citra.ndim == 3 and larik.shape[2] in (3, 4):
            mode = "RGB" if larik.shape[2] == 3 else "RGBA"
            return Image.fromarray(larik, mode=mode)
        raise ValueError(
            "Array gambar harus 2D (grayscale) atau 3D dengan 3/4 kanal, "
            f"ditemukan bentuk {citra.shape}."
        )
    raise ValueError(
        "Citra harus berupa PIL.Image, bytes, atau numpy.ndarray, "
        f"ditemukan {type(citra).__name__}."
    )


def _validasi_kualitas(kualitas: int) -> int:
    """Validasi kualitas JPEG 1..95 (Pillow menolak di luar rentang ini)."""
    if isinstance(kualitas, bool) or not isinstance(kualitas, int):
        raise ValueError(
            f"Kualitas JPEG harus bilangan bulat, ditemukan {type(kualitas).__name__}."
        )
    if not 1 <= kualitas <= 95:
        raise ValueError(f"Kualitas JPEG harus 1..95, ditemukan {kualitas}.")
    return kualitas


# ---------------------------------------------------------------------------
# Serangan tunggal
# ---------------------------------------------------------------------------

def kompresi_jpeg(citra, kualitas: int = 50) -> Image.Image:
    """Mensimulasikan kompresi JPEG pada kualitas tertentu.

    Citra ditulis ulang ke buffer JPEG lalu dibaca kembali, sehingga
    artefak kuantisasi DCT-JPEG benar-benar terjadi (bukan sekadar
    penandaan metadata).

    Args:
        citra: PIL.Image / bytes / ndarray.
        kualitas: 1..95; wajib diuji pada 90, 70, dan 50 (aturan proyek).

    Returns:
        PIL.Image hasil dekompresi JPEG (mode sama seperti masukan,
        kecuali RGBA yang menjadi RGB karena JPEG tak mendukung alfa).
    """
    _validasi_kualitas(kualitas)
    gambar = _ke_pil(citra)
    # JPEG tidak mendukung kanal alfa / palet — samakan dulu.
    if gambar.mode in ("RGBA", "LA", "P"):
        gambar = gambar.convert("RGB")
    penyangga = io.BytesIO()
    # subsampling=0 (4:4:4) agar yang diuji murni efek kuantisasi kualitas,
    # bukan tambahan subsampling kroma bawaan Pillow.
    gambar.save(penyangga, format="JPEG", quality=kualitas, subsampling=0)
    penyangga.seek(0)
    hasil = Image.open(penyangga)
    hasil.load()
    return hasil


def serangan_noise_gaussian(citra, rata_rata: float = 0.0,
                            simpangan_baku: float = 10.0,
                            seed=None) -> Image.Image:
    """Menambahkan Gaussian noise ke citra.

    Args:
        citra: PIL.Image / bytes / ndarray.
        rata_rata: rata-rata noise (biasanya 0.0).
        simpangan_baku: kekuatan noise dalam skala 0..255 (misal 10.0).
        seed: seed opsional agar hasil reproduksibel saat pengujian.

    Returns:
        PIL.Image dengan ukuran & mode sama seperti masukan.
    """
    if simpangan_baku < 0:
        raise ValueError(
            f"Simpangan baku noise tidak boleh negatif, ditemukan {simpangan_baku}."
        )
    gambar = _ke_pil(citra)
    mode_asli = gambar.mode
    larik = np.asarray(gambar).astype(np.float64)
    generator = np.random.default_rng(seed)
    noise = generator.normal(loc=float(rata_rata),
                             scale=float(simpangan_baku),
                             size=larik.shape)
    hasil = np.clip(larik + noise, 0, 255).astype(np.uint8)
    if larik.ndim == 2:
        return Image.fromarray(hasil, mode="L")
    return Image.fromarray(hasil, mode=mode_asli)


def serangan_crop_tengah(citra, proporsi: float = 0.25) -> Image.Image:
    """Memangkas tepi citra sehingga tersisa area tengah.

    Tepi dibuang seluas `proporsi` dari luas total; yang dikembalikan
    adalah potongan tengah seluas (1 - proporsi). Contoh: proporsi=0.25
    berarti 25% luas terbuang, tersisa 75% area tengah — serangan
    cropping standar untuk uji ketahanan watermark (UJI.md §3.3).

    Kotak crop diratakan (snap) ke kelipatan 8 piksel agar selaras dengan
    grid blok DCT 8x8 — memungkinkan ekstraksi toleran-crop (pencarian
    offset blok di `watermark_engine.ekstrak_watermark`). Deviasi luas
    akibat snapping maksimal 7 piksel per sisi dan dicatat di sini,
    bukan disembunyikan.

    Args:
        citra: PIL.Image / bytes / ndarray.
        proporsi: fraksi luas yang dibuang, 0 < proporsi < 1.

    Returns:
        PIL.Image potongan tengah (lebih kecil dari aslinya).
    """
    if not isinstance(proporsi, (int, float)) or not 0 < proporsi < 1:
        raise ValueError(
            f"Proporsi crop harus di antara 0 dan 1, ditemukan {proporsi}."
        )
    gambar = _ke_pil(citra)
    lebar, tinggi = gambar.size
    # Skala sisi agar luas tersisa = (1 - proporsi) dari luas semula.
    import math
    skala = math.sqrt(1.0 - float(proporsi))
    lebar_baru = max(1, round(lebar * skala))
    tinggi_baru = max(1, round(tinggi * skala))
    kiri = (lebar - lebar_baru) // 2
    atas = (tinggi - tinggi_baru) // 2
    # Snap ke grid 8px (lihat docstring): geser kiri/atas ke bawah agar
    # blok DCT penyintas selaras dengan grid citra asli.
    kiri = (kiri // UKURAN_BLOK_DCT) * UKURAN_BLOK_DCT
    atas = (atas // UKURAN_BLOK_DCT) * UKURAN_BLOK_DCT
    return gambar.crop((kiri, atas, kiri + lebar_baru, atas + tinggi_baru))


def serangan_resize(citra, skala: float = 0.5) -> Image.Image:
    """Mensimulasikan serangan resize: kecilkan lalu kembalikan ke ukuran semula.

    Citra diperkecil ke `skala` dari ukuran asli (interpolasi BICUBIC),
    lalu diperbesar kembali ke ukuran semula (BILINEAR). Ukuran keluaran
    sama dengan masukan sehingga bisa langsung dibandingkan (PSNR) —
    yang hilang adalah detail akibat sampling ulang ganda.

    Args:
        citra: PIL.Image / bytes / ndarray.
        skala: faktor pengecilan, 0 < skala < 1.

    Returns:
        PIL.Image berukuran sama seperti masukan.
    """
    if not isinstance(skala, (int, float)) or not 0 < skala < 1:
        raise ValueError(f"Skala resize harus di antara 0 dan 1, ditemukan {skala}.")
    gambar = _ke_pil(citra)
    lebar, tinggi = gambar.size
    lebar_kecil = max(1, round(lebar * float(skala)))
    tinggi_kecil = max(1, round(tinggi * float(skala)))
    kecil = gambar.resize((lebar_kecil, tinggi_kecil), Image.BICUBIC)
    return kecil.resize((lebar, tinggi), Image.BILINEAR)


def serangan_kontras(citra, faktor: float = 1.2,
                      kecerahan: float = 20.0) -> Image.Image:
    """Mengubah kontras & kecerahan citra (UJI.md §3.3: ±20%).

    Rumus per piksel: keluar = rata-rata + faktor * (piksel - rata-rata)
    + kecerahan. faktor > 1 menaikkan kontras, 0 < faktor < 1
    menurunkannya; kecerahan dalam skala piksel 0..255 (positif
    mencerahkan, negatif menggelapkan).

    Args:
        citra: PIL.Image / bytes / ndarray.
        faktor: faktor kontras, harus > 0 (default 1.2 = +20%).
        kecerahan: pergeseran kecerahan skala piksel (default +20).

    Returns:
        PIL.Image dengan ukuran & mode sama seperti masukan.
    """
    if not isinstance(faktor, (int, float)) or float(faktor) <= 0:
        raise ValueError(f"Faktor kontras harus > 0, ditemukan {faktor}.")
    if not isinstance(kecerahan, (int, float)):
        raise ValueError(
            f"Kecerahan harus angka skala piksel, ditemukan {kecerahan}."
        )
    gambar = _ke_pil(citra)
    mode_asli = gambar.mode
    larik = np.asarray(gambar).astype(np.float64)
    if larik.ndim == 2:
        rata = larik.mean()
    else:
        # Rata-rata per kanal agar keseimbangan warna tidak bergeser.
        rata = larik.mean(axis=(0, 1), keepdims=True)
    hasil = np.clip(rata + float(faktor) * (larik - rata) + float(kecerahan),
                    0, 255).astype(np.uint8)
    if larik.ndim == 2:
        return Image.fromarray(hasil, mode="L")
    return Image.fromarray(hasil, mode=mode_asli)


# ---------------------------------------------------------------------------
# Serangan gabungan & paket uji
# ---------------------------------------------------------------------------

def serangan_q50_noise_crop(citra, simpangan_baku: float = 10.0,
                            proporsi_crop: float = 0.25,
                            seed=None) -> Image.Image:
    """Serangan gabungan uji: JPEG kualitas 50 -> Gaussian noise -> crop tengah.

    Sesuai skenario Prompt 4: menerima PIL Image lalu mengembalikan gambar
    yang sudah dikenai tiga serangan berurutan — kompresi JPEG kualitas 50,
    penambahan Gaussian noise, dan pemangkasan 25% area tengah (tersisa
    75% potongan tengah, mengikuti UJI.md §3.3).

    Args:
        citra: PIL.Image / bytes / ndarray.
        simpangan_baku: kekuatan Gaussian noise (skala 0..255).
        proporsi_crop: fraksi luas yang dibuang pada tahap crop (0..1).
        seed: seed opsional untuk reproduksibilitas noise.

    Returns:
        PIL.Image hasil tiga serangan berurutan.
    """
    tahap_jpeg = kompresi_jpeg(citra, kualitas=50)
    tahap_noise = serangan_noise_gaussian(
        tahap_jpeg, simpangan_baku=simpangan_baku, seed=seed
    )
    return serangan_crop_tengah(tahap_noise, proporsi=proporsi_crop)


def terapkan_semua_serangan_uji(citra, seed=None) -> dict:
    """Menjalankan seluruh paket serangan wajib, mengembalikan dict nama->citra.

    Paket meliputi: JPEG 90/70/50, Gaussian noise, crop tengah 25%,
    resize 0.5, kontras 1.2 + kecerahan 20, plus gabungan q50+noise+crop.
    Dipakai oleh endpoint simulasi serangan dan modul evaluator
    (NC/BER per serangan).

    Args:
        citra: PIL.Image / bytes / ndarray (stego-image).
        seed: seed opsional untuk reproduksibilitas noise.

    Returns:
        Dict {"jpeg_90": PIL.Image, "jpeg_70": ..., "gabungan_q50_noise_crop": ...}.
    """
    gambar = _ke_pil(citra)
    return {
        "jpeg_90": kompresi_jpeg(gambar, kualitas=90),
        "jpeg_70": kompresi_jpeg(gambar, kualitas=70),
        "jpeg_50": kompresi_jpeg(gambar, kualitas=50),
        "noise_gaussian": serangan_noise_gaussian(gambar, seed=seed),
        "crop_tengah_25": serangan_crop_tengah(gambar, proporsi=0.25),
        "resize_05": serangan_resize(gambar, skala=0.5),
        "kontras_12": serangan_kontras(gambar, faktor=1.2, kecerahan=20.0),
        "gabungan_q50_noise_crop": serangan_q50_noise_crop(gambar, seed=seed),
    }


# Alias Inggris agar mudah dipakai dari modul lain / pengujian.
# Nama Indonesia tetap menjadi API utama.
def jpeg_compress(citra, kualitas: int = 50) -> Image.Image:
    """Alias dari kompresi_jpeg."""
    return kompresi_jpeg(citra, kualitas)


def gaussian_noise_attack(citra, rata_rata=0.0, simpangan_baku=10.0, seed=None):
    """Alias dari serangan_noise_gaussian."""
    return serangan_noise_gaussian(citra, rata_rata, simpangan_baku, seed)


def center_crop_attack(citra, proporsi=0.25):
    """Alias dari serangan_crop_tengah."""
    return serangan_crop_tengah(citra, proporsi)


def resize_attack(citra, skala=0.5):
    """Alias dari serangan_resize."""
    return serangan_resize(citra, skala)


def contrast_attack(citra, faktor=1.2, kecerahan=20.0):
    """Alias dari serangan_kontras."""
    return serangan_kontras(citra, faktor, kecerahan)


def combined_q50_noise_crop_attack(citra, simpangan_baku=10.0,
                                   proporsi_crop=0.25, seed=None):
    """Alias dari serangan_q50_noise_crop."""
    return serangan_q50_noise_crop(citra, simpangan_baku, proporsi_crop, seed)

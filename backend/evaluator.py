"""evaluator.py — Kalkulasi metrik kualitas citra dan ketahanan watermark.

- PSNR membandingkan dua citra 2D (asli vs stego / stego vs terserang).
- NC dan BER membandingkan dua deret bit 1D (logo asli vs hasil ekstraksi).

Rumus:
    MSE  = rata-rata((I_asli - I_uji) ** 2) atas seluruh sampel
    PSNR = 10 * log10(MAX_I ** 2 / MSE), MAX_I = 255.
           MSE = 0 berarti citra identik -> PSNR tak-hingga (inf).
    NC   = sum(w * w') / sqrt(sum(w**2) * sum(w'**2)), w/w' deret biner 0/1.
           NC = 1 berarti ekstraksi sempurna; 0 berarti tak-berkorelasi.
    BER  = (jumlah bit berbeda) / (total bit). BER = 0 berarti sempurna.

Antar modul, citra dioper sebagai `bytes` atau `PIL.Image` sebelum
diubah ke `numpy.ndarray`.

Semua komentar dan pesan error memakai Bahasa Indonesia.
"""

import io
import math

import numpy as np
from PIL import Image

# Nilai piksel maksimum untuk citra 8-bit.
NILAI_MAKS_PIKSEL = 255.0


# ---------------------------------------------------------------------------
# Normalisasi masukan
# ---------------------------------------------------------------------------

def _ke_array(citra) -> np.ndarray:
    """Mengubah citra (PIL.Image / bytes / ndarray) menjadi array float64."""
    if isinstance(citra, bytes):
        try:
            citra = Image.open(io.BytesIO(citra))
        except Exception as eronya:
            raise ValueError(f"Bytes gambar tidak dapat dibaca: {eronya}.")
    if isinstance(citra, Image.Image):
        if citra.width == 0 or citra.height == 0:
            raise ValueError("Citra PIL kosong (lebar/tinggi nol).")
        return np.asarray(citra, dtype=np.float64)
    if isinstance(citra, np.ndarray):
        if citra.size == 0:
            raise ValueError("Array gambar kosong.")
        return citra.astype(np.float64)
    raise ValueError(
        "Citra harus berupa PIL.Image, bytes, atau numpy.ndarray, "
        f"ditemukan {type(citra).__name__}."
    )


def _ke_deret_biner(deret, nama: str) -> np.ndarray:
    """Validasi deret bit 1D berisi hanya 0/1, kembalikan array float64."""
    larik = np.asarray(deret)
    if larik.size == 0:
        raise ValueError(f"Deret {nama} kosong.")
    if larik.ndim != 1:
        raise ValueError(
            f"Deret {nama} harus 1 dimensi, ditemukan {larik.ndim} dimensi."
        )
    # Tolak boolean / float tanggung: harus tepat 0 atau 1.
    pipih = larik.ravel()
    for posisi, bit in enumerate(pipih):
        if bit not in (0, 1):
            raise ValueError(
                f"Deret {nama} hanya boleh berisi 0/1, "
                f"indeks ke-{posisi} bernilai {bit}."
            )
    return pipih.astype(np.float64)


# ---------------------------------------------------------------------------
# Metrik citra 2D
# ---------------------------------------------------------------------------

def hitung_mse(citra_asli, citra_uji) -> float:
    """Menghitung Mean Squared Error antara dua citra.

    Kedua citra harus berdimensi sama (bentuk array identik); bila ukuran
    berbeda (misal habis di-crop serangan), panggil dengan citra yang
    sudah disamakan ukurannya terlebih dahulu.
    """
    asli = _ke_array(citra_asli)
    uji = _ke_array(citra_uji)
    if asli.shape != uji.shape:
        raise ValueError(
            f"Ukuran citra tidak sama: asli {asli.shape} vs uji {uji.shape}. "
            "Samakan ukuran terlebih dahulu (misal via resize serangan)."
        )
    return float(np.mean((asli - uji) ** 2))


def hitung_psnr(citra_asli, citra_uji) -> float:
    """Menghitung PSNR (dB) antara citra asli dan citra uji (stego/terserang).

    Args:
        citra_asli: PIL.Image / bytes / ndarray referensi.
        citra_uji: PIL.Image / bytes / ndarray yang dinilai.

    Returns:
        Nilai PSNR dalam dB. Citra identik -> float("inf").
        Di atas ~30 dB umumnya dianggap baik untuk watermark tak-kasatmata.
    """
    mse = hitung_mse(citra_asli, citra_uji)
    if mse == 0.0:
        return float("inf")  # identik sempurna, tanpa galat
    return float(10.0 * math.log10((NILAI_MAKS_PIKSEL ** 2) / mse))


# ---------------------------------------------------------------------------
# Metrik deret bit 1D
# ---------------------------------------------------------------------------

def hitung_nc(logo_asli, logo_ekstrak) -> float:
    """Menghitung Normalized Correlation antara dua deret bit 0/1.

    Args:
        logo_asli: deret bit asli (list/tuple/ndarray 1D berisi 0/1).
        logo_ekstrak: deret bit hasil ekstraksi (format sama, panjang sama).

    Returns:
        NC dalam 0..1. 1.0 = ekstraksi sempurna.
    """
    asli = _ke_deret_biner(logo_asli, "asli")
    ekstrak = _ke_deret_biner(logo_ekstrak, "ekstraksi")
    if asli.shape != ekstrak.shape:
        raise ValueError(
            f"Panjang deret tidak sama: asli {asli.shape} vs ekstraksi {ekstrak.shape}."
        )
    pembilang = float(np.sum(asli * ekstrak))
    penyebut = float(math.sqrt(float(np.sum(asli ** 2)) * float(np.sum(ekstrak ** 2))))
    if penyebut == 0.0:
        # Kedua deret nol semua -> identik; salah satunya nol semua -> tak-berkorelasi.
        if pembilang == 0.0 and float(np.sum(asli)) == 0.0 and float(np.sum(ekstrak)) == 0.0:
            return 1.0
        return 0.0
    return pembilang / penyebut


def hitung_ber(logo_asli, logo_ekstrak) -> float:
    """Menghitung Bit Error Rate antara dua deret bit 0/1.

    Args:
        logo_asli: deret bit asli (list/tuple/ndarray 1D berisi 0/1).
        logo_ekstrak: deret bit hasil ekstraksi (format sama, panjang sama).

    Returns:
        BER dalam 0..1. 0.0 = tanpa bit salah; 1.0 = seluruh bit salah.
    """
    asli = _ke_deret_biner(logo_asli, "asli")
    ekstrak = _ke_deret_biner(logo_ekstrak, "ekstraksi")
    if asli.shape != ekstrak.shape:
        raise ValueError(
            f"Panjang deret tidak sama: asli {asli.shape} vs ekstraksi {ekstrak.shape}."
        )
    return float(np.sum(asli != ekstrak)) / float(asli.size)


def hitung_semua_metrik(citra_asli, citra_uji, logo_asli, logo_ekstrak) -> dict:
    """Menghitung PSNR, NC, dan BER sekaligus untuk satu skenario uji.

    Dipakai oleh endpoint evaluasi: satu panggilan merangkum kualitas
    citra (PSNR) dan ketahanan watermark (NC, BER).

    Returns:
        Dict {"psnr": float, "nc": float, "ber": float}.
    """
    return {
        "psnr": hitung_psnr(citra_asli, citra_uji),
        "nc": hitung_nc(logo_asli, logo_ekstrak),
        "ber": hitung_ber(logo_asli, logo_ekstrak),
    }


# Alias Inggris agar mudah dipakai dari modul lain / pengujian.
# Nama Indonesia tetap menjadi API utama.
def calculate_mse(citra_asli, citra_uji) -> float:
    """Alias dari hitung_mse."""
    return hitung_mse(citra_asli, citra_uji)


def calculate_psnr(citra_asli, citra_uji) -> float:
    """Alias dari hitung_psnr."""
    return hitung_psnr(citra_asli, citra_uji)


def calculate_nc(logo_asli, logo_ekstrak) -> float:
    """Alias dari hitung_nc."""
    return hitung_nc(logo_asli, logo_ekstrak)


def calculate_ber(logo_asli, logo_ekstrak) -> float:
    """Alias dari hitung_ber."""
    return hitung_ber(logo_asli, logo_ekstrak)

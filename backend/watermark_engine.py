"""watermark_engine.py — Pemecahan gambar ke blok 8x8 & DCT paralel via multiprocessing.

Alur modul:
    PIL.Image / bytes / numpy.ndarray
        -> array grayscale 2D (float64)
        -> pecah_ke_blok_8x8 (dengan padding tepi bila bukan kelipatan 8)
        -> terapkan_dct_paralel (multiprocessing.Pool + hitung_dct_8x8)
        -> ... (penyisipan spread-spectrum, di luar skop modul ini) ...
        -> terapkan_idct_paralel + susun_dari_blok_8x8 -> PIL.Image

Aturan ketat proyek (lihat AI.md):
- DCT/IDCT WAJIB memakai hitung_dct_8x8 / hitung_idct_8x8 dari dct_core.py
  (rumus double-summation manual). Modul ini TIDAK memanggil cv2.dct(),
  scipy.fftpack.dct(), atau numpy.fft.
- Pillow & NumPy HANYA untuk I/O citra dan manipulasi array, bukan logika inti.
- Antar modul, citra dioper sebagai `bytes` atau `PIL.Image` sebelum
  diubah ke `numpy.ndarray` (lihat fungsi bantu di bawah).

Semua komentar dan pesan error memakai Bahasa Indonesia.
"""

import io
import multiprocessing as mp
import os

try:
    # Dipakai saat diimpor sebagai paket: from backend.watermark_engine import ...
    from backend.dct_core import hitung_dct_8x8, hitung_idct_8x8
except ImportError:  # pragma: no cover — dipakai saat dijalankan langsung.
    # Dipakai saat dijalankan sebagai skrip: python backend/watermark_engine.py
    from dct_core import hitung_dct_8x8, hitung_idct_8x8

import numpy as np
from PIL import Image

# Ukuran blok standar JPEG / kebutuhan watermarking.
UKURAN_BLOK = 8


# ---------------------------------------------------------------------------
# Konversi tipe citra (bytes / PIL.Image / ndarray -> ndarray grayscale)
# ---------------------------------------------------------------------------

def pil_ke_array_grayscale(citra) -> np.ndarray:
    """Mengubah citra (PIL.Image / bytes / ndarray) menjadi array grayscale 2D.

    Args:
        citra: objek PIL.Image, bytes gambar (misal PNG/JPEG), atau ndarray
            2D (grayscale) / 3D (RGB/RGBA).

    Returns:
        Array NumPy 2D float64 berisi intensitas piksel 0..255.

    Raises:
        ValueError: bila tipe masukan tidak didukung atau gambar kosong.
    """
    if isinstance(citra, bytes):
        try:
            citra = Image.open(io.BytesIO(citra))
        except Exception as eronya:
            raise ValueError(f"Bytes gambar tidak dapat dibaca: {eronya}.")
    if isinstance(citra, Image.Image):
        if citra.width == 0 or citra.height == 0:
            raise ValueError("Citra PIL kosong (lebar/tinggi nol).")
        # Samakan ke grayscale 8-bit; kanal warna dibuang karena DCT
        # watermarking pada skop ini bekerja pada satu kanal luminansi.
        return np.asarray(citra.convert("L"), dtype=np.float64)
    if isinstance(citra, np.ndarray):
        if citra.size == 0:
            raise ValueError("Array gambar kosong.")
        if citra.ndim == 2:
            return citra.astype(np.float64)
        if citra.ndim == 3:
            # Ambil rata-rata kanal (RGB/RGBA -> grayscale sederhana).
            # Kanal alfa ikut dirata-rata; cukup untuk pra-pemrosesan blok.
            return np.mean(citra, axis=2).astype(np.float64)
        raise ValueError(
            f"Array gambar harus 2D/3D, ditemukan {citra.ndim} dimensi."
        )
    raise ValueError(
        "Citra harus berupa PIL.Image, bytes, atau numpy.ndarray, "
        f"ditemukan {type(citra).__name__}."
    )


def array_ke_pil(array: np.ndarray) -> Image.Image:
    """Mengubah array 2D float menjadi PIL.Image grayscale (klip 0..255)."""
    array = np.asarray(array, dtype=np.float64)
    if array.ndim != 2 or array.size == 0:
        raise ValueError("Array harus 2D tak-kosong untuk diubah ke PIL.Image.")
    return Image.fromarray(np.clip(np.rint(array), 0, 255).astype(np.uint8), mode="L")


# ---------------------------------------------------------------------------
# Pemecahan & penyusunan blok 8x8
# ---------------------------------------------------------------------------

def pecah_ke_blok_8x8(array: np.ndarray):
    """Memecah array 2D menjadi daftar blok 8x8 (list-of-list float).

    Bila tinggi/lebar bukan kelipatan 8, array di-padding dengan replikasi
    tepi (`edge`) agar tidak ada blok parsial.

    Args:
        array: array NumPy 2D grayscale.

    Returns:
        Tuple (daftar_blok, tinggi_asli, lebar_asli, tinggi_pad, lebar_pad).
        `daftar_blok` berisi blok 8x8 dalam urutan raster (baris-mayor),
        masing-masing berupa list berisi 8 list float (format dct_core).
    """
    array = np.asarray(array, dtype=np.float64)
    if array.ndim != 2 or array.size == 0:
        raise ValueError("Masukan harus array 2D tak-kosong.")
    tinggi_asli, lebar_asli = int(array.shape[0]), int(array.shape[1])
    # Jumlah blok per sisi (ceil division).
    blok_baris = -(-tinggi_asli // UKURAN_BLOK)
    blok_kolom = -(-lebar_asli // UKURAN_BLOK)
    tinggi_pad = blok_baris * UKURAN_BLOK
    lebar_pad = blok_kolom * UKURAN_BLOK
    if (tinggi_pad, lebar_pad) != (tinggi_asli, lebar_asli):
        array = np.pad(
            array,
            ((0, tinggi_pad - tinggi_asli), (0, lebar_pad - lebar_asli)),
            mode="edge",  # replikasi tepi: tidak memunculkan garis hitam artifisial
        )
    daftar_blok = []
    for br in range(blok_baris):
        for bk in range(blok_kolom):
            potongan = array[
                br * UKURAN_BLOK:(br + 1) * UKURAN_BLOK,
                bk * UKURAN_BLOK:(bk + 1) * UKURAN_BLOK,
            ]
            daftar_blok.append(potongan.tolist())
    return daftar_blok, tinggi_asli, lebar_asli, tinggi_pad, lebar_pad


def susun_dari_blok_8x8(daftar_blok, tinggi_asli: int, lebar_asli: int,
                        tinggi_pad: int, lebar_pad: int) -> np.ndarray:
    """Menyusun kembali daftar blok 8x8 menjadi array 2D (padding dipangkas).

    Args:
        daftar_blok: list blok 8x8 (list-of-list) urutan raster.
        tinggi_asli, lebar_asli: dimensi sebelum padding.
        tinggi_pad, lebar_pad: dimensi setelah padding.

    Returns:
        Array NumPy 2D float64 berukuran (tinggi_asli, lebar_asli).
    """
    if not daftar_blok:
        raise ValueError("Daftar blok kosong — tidak ada yang bisa disusun.")
    blok_baris = tinggi_pad // UKURAN_BLOK
    blok_kolom = lebar_pad // UKURAN_BLOK
    if len(daftar_blok) != blok_baris * blok_kolom:
        raise ValueError(
            f"Jumlah blok ({len(daftar_blok)}) tidak cocok dengan dimensi "
            f"pad {tinggi_pad}x{lebar_pad} "
            f"(harus {blok_baris * blok_kolom})."
        )
    kanvas = np.zeros((tinggi_pad, lebar_pad), dtype=np.float64)
    posisi = 0
    for br in range(blok_baris):
        for bk in range(blok_kolom):
            kanvas[
                br * UKURAN_BLOK:(br + 1) * UKURAN_BLOK,
                bk * UKURAN_BLOK:(bk + 1) * UKURAN_BLOK,
            ] = np.asarray(daftar_blok[posisi], dtype=np.float64)
            posisi += 1
    # Pangkas padding kembali ke ukuran asli.
    return kanvas[:tinggi_asli, :lebar_asli]


# ---------------------------------------------------------------------------
# Pekerja Pool (WAJIB di level modul agar bisa di-pickle oleh spawn Windows)
# ---------------------------------------------------------------------------

def _kerja_dct(blok_spasial):
    """Fungsi pekerja Pool: satu blok spasial 8x8 -> koefisien DCT."""
    return hitung_dct_8x8(blok_spasial)


def _kerja_idct(blok_frekuensi):
    """Fungsi pekerja Pool: satu blok koefisien DCT 8x8 -> spasial."""
    return hitung_idct_8x8(blok_frekuensi)


def _tentukan_jumlah_proses(jumlah_proses, jumlah_blok: int) -> int:
    """Validasi jumlah proses: minimal 1, maksimal jumlah CPU & jumlah blok."""
    maks_cpu = os.cpu_count() or 1
    if jumlah_proses is None:
        return max(1, min(maks_cpu, jumlah_blok))
    if isinstance(jumlah_proses, bool) or not isinstance(jumlah_proses, int):
        raise ValueError("Jumlah proses harus bilangan bulat atau None.")
    if jumlah_proses < 1:
        raise ValueError(f"Jumlah proses minimal 1, ditemukan {jumlah_proses}.")
    return max(1, min(jumlah_proses, maks_cpu, jumlah_blok))


# ---------------------------------------------------------------------------
# API paralel utama
# ---------------------------------------------------------------------------

def terapkan_dct_paralel(daftar_blok_spasial, jumlah_proses=None):
    """Menerapkan `hitung_dct_8x8` ke seluruh blok secara paralel.

    Args:
        daftar_blok_spasial: list blok 8x8 domain spasial (list-of-list).
        jumlah_proses: jumlah worker Pool (None = otomatis = jumlah CPU).

    Returns:
        List blok 8x8 koefisien DCT dengan urutan yang sama seperti masukan.
    """
    if not daftar_blok_spasial:
        raise ValueError("Daftar blok spasial kosong.")
    pekerja = _tentukan_jumlah_proses(jumlah_proses, len(daftar_blok_spasial))
    if pekerja == 1 or len(daftar_blok_spasial) == 1:
        # Jalur serial: hemat overhead Pool untuk citra mungil / debugging.
        return [_kerja_dct(blok) for blok in daftar_blok_spasial]
    ukuran_chunk = max(1, len(daftar_blok_spasial) // (pekerja * 4))
    # Catatan Windows: Pool memakai spawn; fungsi pekerja berada di level
    # modul sehingga bisa di-pickle. Panggil fungsi ini dari dalam
    # `if __name__ == "__main__":` bila dipakai pada skrip mandiri.
    with mp.Pool(processes=pekerja) as pool:
        return pool.map(_kerja_dct, daftar_blok_spasial, chunksize=ukuran_chunk)


def terapkan_idct_paralel(daftar_blok_frekuensi, jumlah_proses=None):
    """Menerapkan `hitung_idct_8x8` ke seluruh blok secara paralel.

    Args:
        daftar_blok_frekuensi: list blok 8x8 koefisien DCT (list-of-list).
        jumlah_proses: jumlah worker Pool (None = otomatis = jumlah CPU).

    Returns:
        List blok 8x8 domain spasial dengan urutan yang sama seperti masukan.
    """
    if not daftar_blok_frekuensi:
        raise ValueError("Daftar blok frekuensi kosong.")
    pekerja = _tentukan_jumlah_proses(jumlah_proses, len(daftar_blok_frekuensi))
    if pekerja == 1 or len(daftar_blok_frekuensi) == 1:
        return [_kerja_idct(blok) for blok in daftar_blok_frekuensi]
    ukuran_chunk = max(1, len(daftar_blok_frekuensi) // (pekerja * 4))
    with mp.Pool(processes=pekerja) as pool:
        return pool.map(_kerja_idct, daftar_blok_frekuensi, chunksize=ukuran_chunk)


def dct_gambar_paralel(citra, jumlah_proses=None):
    """Jalur lengkap: citra -> blok 8x8 -> DCT paralel.

    Args:
        citra: PIL.Image / bytes / ndarray (lihat pil_ke_array_grayscale).
        jumlah_proses: jumlah worker Pool (None = otomatis).

    Returns:
        Tuple (daftar_blok_dct, info_dimensi) dengan
        info_dimensi = dict(tinggi, lebar, tinggi_pad, lebar_pad).
    """
    array = pil_ke_array_grayscale(citra)
    daftar_blok, tinggi, lebar, tinggi_pad, lebar_pad = pecah_ke_blok_8x8(array)
    hasil_dct = terapkan_dct_paralel(daftar_blok, jumlah_proses)
    info = {"tinggi": tinggi, "lebar": lebar,
            "tinggi_pad": tinggi_pad, "lebar_pad": lebar_pad}
    return hasil_dct, info


def idct_gambar_paralel(daftar_blok_dct, info_dimensi, jumlah_proses=None) -> Image.Image:
    """Jalur lengkap: blok DCT -> IDCT paralel -> PIL.Image.

    Args:
        daftar_blok_dct: list blok 8x8 koefisien DCT.
        info_dimensi: dict dari dct_gambar_paralel.
        jumlah_proses: jumlah worker Pool (None = otomatis).

    Returns:
        PIL.Image grayscale hasil rekonstruksi.
    """
    try:
        tinggi = int(info_dimensi["tinggi"])
        lebar = int(info_dimensi["lebar"])
        tinggi_pad = int(info_dimensi["tinggi_pad"])
        lebar_pad = int(info_dimensi["lebar_pad"])
    except (KeyError, TypeError, ValueError) as eronya:
        raise ValueError(f"info_dimensi tidak valid: {eronya}.")
    daftar_spasial = terapkan_idct_paralel(daftar_blok_dct, jumlah_proses)
    array = susun_dari_blok_8x8(daftar_spasial, tinggi, lebar, tinggi_pad, lebar_pad)
    return array_ke_pil(array)


# Alias Inggris agar mudah dipakai dari modul lain / pengujian.
# Nama Indonesia tetap menjadi API utama.
def split_into_8x8_blocks(array: np.ndarray):
    """Alias dari pecah_ke_blok_8x8."""
    return pecah_ke_blok_8x8(array)


def merge_from_8x8_blocks(daftar_blok, tinggi_asli, lebar_asli, tinggi_pad, lebar_pad):
    """Alias dari susun_dari_blok_8x8."""
    return susun_dari_blok_8x8(daftar_blok, tinggi_asli, lebar_asli, tinggi_pad, lebar_pad)


def apply_dct_parallel(daftar_blok_spasial, jumlah_proses=None):
    """Alias dari terapkan_dct_paralel."""
    return terapkan_dct_paralel(daftar_blok_spasial, jumlah_proses)


def apply_idct_parallel(daftar_blok_frekuensi, jumlah_proses=None):
    """Alias dari terapkan_idct_paralel."""
    return terapkan_idct_paralel(daftar_blok_frekuensi, jumlah_proses)

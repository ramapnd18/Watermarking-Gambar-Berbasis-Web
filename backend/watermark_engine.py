"""watermark_engine.py — Pemecahan gambar ke blok 8x8 & DCT paralel via multiprocessing.

Alur modul:
    PIL.Image / bytes / numpy.ndarray
        -> kanal luminansi Y (YCbCr untuk citra berwarna, langsung untuk grayscale)
        -> pecah_ke_blok_8x8 (dengan padding tepi bila bukan kelipatan 8)
        -> terapkan_dct_paralel (multiprocessing.Pool + hitung_dct_8x8)
        -> sisip_watermark (spread-spectrum mid-frequency, warna lestari)
        -> terapkan_idct_paralel + susun_dari_blok_8x8 + gabung CbCr -> PIL.Image

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
import sys
from pathlib import Path

try:
    # Dipakai saat diimpor sebagai paket: from backend.watermark_engine import ...
    from backend.dct_core import hitung_dct_8x8, hitung_idct_8x8
except ImportError:  # pragma: no cover — dipakai saat dijalankan langsung.
    # Dipakai saat dijalankan sebagai skrip: python backend/watermark_engine.py
    # (atau worker spawn Windows yang cwd-nya bukan root proyek).
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from dct_core import hitung_dct_8x8, hitung_idct_8x8

try:
    from backend.security import (
        generate_position_permutation, generate_bipolar_sequence,
    )
except ImportError:  # pragma: no cover — dipakai saat dijalankan langsung.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from security import (
        generate_position_permutation, generate_bipolar_sequence,
    )

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


# ---------------------------------------------------------------------------
# Citra berwarna: sisipan hanya di kanal luminansi (Y) agar warna lestari
# ---------------------------------------------------------------------------

def _ke_luminansi_dan_warna(citra):
    """Memecah citra menjadi (array_Y float64, mode_asli, pita_warna).

    Watermarking DCT bekerja pada satu kanal luminansi: citra grayscale
    dipakai langsung, citra berwarna dipecah via YCbCr (kanal Y disisipi,
    Cb/Cr disimpan untuk digabung kembali). Kunci/mode/seed tidak
    terpengaruh — yang dibandingkan saat ekstraksi selalu kanal Y.
    """
    if isinstance(citra, bytes):
        try:
            citra = Image.open(io.BytesIO(citra))
        except Exception as eronya:
            raise ValueError(f"Bytes gambar tidak dapat dibaca: {eronya}.")
    if isinstance(citra, Image.Image):
        if citra.width == 0 or citra.height == 0:
            raise ValueError("Citra PIL kosong (lebar/tinggi nol).")
        if citra.mode == "L":
            return (np.asarray(citra, dtype=np.float64), "L", None)
        ycbcr = citra.convert("RGB").convert("YCbCr")
        y, cb, cr = ycbcr.split()
        return (np.asarray(y, dtype=np.float64), "RGB", (cb, cr))
    if isinstance(citra, np.ndarray):
        if citra.size == 0:
            raise ValueError("Array gambar kosong.")
        if citra.ndim == 2:
            return (citra.astype(np.float64), "L", None)
        if citra.ndim == 3:
            klip = np.clip(np.rint(citra[:, :, :3]), 0, 255).astype(np.uint8)
            ycbcr = Image.fromarray(klip, mode="RGB").convert("YCbCr")
            y, cb, cr = ycbcr.split()
            return (np.asarray(y, dtype=np.float64), "RGB", (cb, cr))
        raise ValueError(f"Array gambar harus 2D/3D, ditemukan {citra.ndim} dimensi.")
    raise ValueError(
        "Citra harus berupa PIL.Image, bytes, atau numpy.ndarray, "
        f"ditemukan {type(citra).__name__}."
    )


def _dari_luminansi(array_y, mode_asli, pita_warna) -> Image.Image:
    """Menggabung kanal Y hasil IDCT kembali menjadi PIL.Image sewarna asli."""
    kanal_y = Image.fromarray(
        np.clip(np.rint(np.asarray(array_y, dtype=np.float64)), 0, 255).astype(np.uint8),
        mode="L",
    )
    if mode_asli == "L" or pita_warna is None:
        return kanal_y
    cb, cr = pita_warna
    return Image.merge("YCbCr", (kanal_y, cb, cr)).convert("RGB")

def _kerja_dct(blok_spasial):
    """Fungsi pekerja Pool: satu blok spasial 8x8 -> koefisien DCT."""
    return hitung_dct_8x8(blok_spasial)


def _kerja_idct(blok_frekuensi):
    """Fungsi pekerja Pool: satu blok koefisien DCT 8x8 -> spasial."""
    return hitung_idct_8x8(blok_frekuensi)


def _tentukan_jumlah_proses(jumlah_proses, jumlah_blok: int) -> int:
    """Validasi jumlah proses: minimal 1, maksimal jumlah CPU & jumlah blok.

    Dibatasi maksimal 4 worker: tiap worker spawn memuat ulang interpreter
    + NumPy + daftar blok (mahal di Windows & RAM terbatas). Request berat
    juga diserialkan via lock di backend/main.py agar tidak menumpuk.
    """
    maks_cpu = min(os.cpu_count() or 1, 4)
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


# ---------------------------------------------------------------------------
# Penyisipan & ekstraksi spread-spectrum (fitur lengkap)
# ---------------------------------------------------------------------------

# Posisi koefisien frekuensi menengah yang disisipi (satu koefisien per bit).
# Dipilih di zona mid-frequency blok 8x8: cukup jauh dari DC (0,0) agar
# tidak merusak kesan visual, cukup jauh dari frekuensi tinggi agar tahan
# kompresi JPEG (yang membuang frekuensi tinggi lebih dulu).
BARIS_SISIP = 3
KOLOM_SISIP = 4

# Kekuatan penyisipan default ("Sedang" menurut UJI.md §6.1).
ALPHA_DEFAULT = 15.0


def teks_ke_bit(teks: str) -> list:
    """Mengubah string teks menjadi list bit 0/1 (UTF-8, MSB lebih dulu)."""
    if not teks:
        raise ValueError("Teks watermark kosong.")
    bit = []
    for byte in teks.encode("utf-8"):
        for geser in range(7, -1, -1):
            bit.append((byte >> geser) & 1)
    return bit


def bit_ke_teks(bit) -> str:
    """Mengubah list bit 0/1 kembali menjadi string (byte tak-lengkap dibuang)."""
    n_penuh = (len(bit) // 8) * 8
    data = bytearray()
    for i in range(0, n_penuh, 8):
        byte = 0
        for b in bit[i:i + 8]:
            byte = (byte << 1) | (1 if b else 0)
        data.append(byte)
    return bytes(data).decode("utf-8", errors="replace")


def logo_ke_bit(logo) -> tuple:
    """Mengubah citra logo menjadi (list bit 0/1, lebar, tinggi).

    Logo di-grayscale lalu diambang 128: piksel terang -> 1, gelap -> 0.
    """
    larik = pil_ke_array_grayscale(logo)
    tinggi, lebar = int(larik.shape[0]), int(larik.shape[1])
    if tinggi == 0 or lebar == 0:
        raise ValueError("Dimensi logo nol.")
    biner = (larik >= 128).astype(np.int8)
    return biner.ravel().tolist(), lebar, tinggi


def bit_ke_logo(bit, lebar: int, tinggi: int) -> Image.Image:
    """Merender list bit 0/1 menjadi PIL.Image logo (0 -> hitam, 1 -> putih)."""
    if lebar < 1 or tinggi < 1:
        raise ValueError("Lebar/tinggi logo harus >= 1.")
    if len(bit) != lebar * tinggi:
        raise ValueError(
            f"Jumlah bit ({len(bit)}) tidak cocok dengan dimensi logo "
            f"{lebar}x{tinggi} ({lebar * tinggi})."
        )
    larik = (np.asarray(bit, dtype=np.uint8).reshape(tinggi, lebar) * 255).astype(np.uint8)
    return Image.fromarray(larik, mode="L")


def sisip_watermark(citra, bit_watermark, kunci: str,
                    alpha: float = ALPHA_DEFAULT,
                    jumlah_proses=None) -> Image.Image:
    """Menyisipkan bit watermark ke citra via spread-spectrum DCT (non-blind).

    Rumus per bit ke-i (s = +1 bila bit 1, -1 bila bit 0):
        F'(u,v) = F(u,v) + alpha * s * PN(i)
    pada koefisien frekuensi menengah (BARIS_SISIP, KOLOM_SISIP) blok
    terpilih. Urutan blok dari permutasi pseudo-random `kunci`, deret
    polaritas PN juga dari `kunci` yang sama (lihat security.py).

    Args:
        citra: PIL.Image / bytes / ndarray cover (warna lestari: sisipan
            hanya di kanal luminansi Y; stego sama mode & ukuran dgn cover).
        bit_watermark: list bit 0/1 (mis. dari teks_ke_bit / logo_ke_bit).
        kunci: kunci rahasia (string tak-kosong, dari input pengguna).
        alpha: kekuatan penyisipan > 0 (lihat UJI.md §6: 5 lemah/15 sedang/30 kuat).
        jumlah_proses: worker Pool (None = otomatis).

    Returns:
        PIL.Image stego (mode & ukuran sama seperti cover).

    Catatan kapasitas: butuh 1 blok per bit; cover 512x512 menampung
    4096 bit (mis. logo 32x32 = 1024 bit).
    """
    bit = [1 if b else 0 for b in bit_watermark]
    if not bit:
        raise ValueError("Bit watermark kosong.")
    if not kunci or not isinstance(kunci, str):
        raise ValueError("Kunci harus berupa string tidak kosong.")
    if not isinstance(alpha, (int, float)) or float(alpha) <= 0:
        raise ValueError(f"Alpha harus > 0, ditemukan {alpha}.")
    alpha = float(alpha)

    luminansi, mode_asli, pita_warna = _ke_luminansi_dan_warna(citra)
    daftar_blok, tinggi, lebar, tinggi_pad, lebar_pad = pecah_ke_blok_8x8(luminansi)
    jumlah_blok = len(daftar_blok)
    if len(bit) > jumlah_blok:
        raise ValueError(
            f"Kapasitas tidak cukup: butuh {len(bit)} blok untuk {len(bit)} bit, "
            f"citra hanya punya {jumlah_blok} blok. Pakai citra lebih besar "
            "atau watermark lebih kecil."
        )
    daftar_dct = terapkan_dct_paralel(daftar_blok, jumlah_proses)
    permutasi = generate_position_permutation(kunci, jumlah_blok, n_select=len(bit))
    deret_pn = generate_bipolar_sequence(kunci, len(bit))

    for i, b in enumerate(bit):
        s = 1.0 if b else -1.0
        blok = daftar_dct[int(permutasi[i])]
        blok[BARIS_SISIP][KOLOM_SISIP] += alpha * s * float(deret_pn[i])

    daftar_spasial = terapkan_idct_paralel(daftar_dct, jumlah_proses)
    array_stego = susun_dari_blok_8x8(daftar_spasial, tinggi, lebar,
                                      tinggi_pad, lebar_pad)
    return _dari_luminansi(array_stego, mode_asli, pita_warna)


def ekstrak_watermark(citra_asli, citra_input, kunci: str,
                      jumlah_bit: int, alpha: float = ALPHA_DEFAULT,
                      jumlah_proses=None) -> list:
    """Mengekstrak bit watermark secara non-blind (butuh citra asli).

    Untuk tiap bit ke-i: delta = F_input - F_asli pada koefisien sisipan
    blok permutasi ke-i; bit = 1 bila delta * PN(i) > 0, else 0.

    Kedua citra HARUS berdimensi & berkanal sama (perbandingan selalu pada
    kanal luminansi Y; cropping mengubah ukuran sehingga sinkronisasi blok
    hilang — ekstraksi lalu ditolak dengan pesan jelas; pakai serangan
    seukuran seperti JPEG/noise/resize/kontras untuk demo NC).

    Toleran-crop: bila citra input LEBIH KECIL di kedua sisi (mis. habis
    di-crop), fungsi mencari offset blok (ox, oy) yang skornya minimal.
    Skor = median ||delta|-alpha| (median agar tahan outlier noise):
    tiap blok yang dievaluasi membawa
    tepat 1 bit tersisip dan crop tidak mengubah nilai piksel penyintas,
    sehingga offset benar memberi skor ~0 sementara offset salah memberi
    skor sebesar perbedaan konten. Diterima bila skor < alpha DAN menonjol
    dari offset lain (margin 2x) — kunci salah / grid liar memberi skor
    besar-merata sehingga ditolak. Bit yang bloknya ikut terpotong
    dianggap hilang (erasure -> 0, jujur menurunkan NC).

    Returns:
        List bit 0/1 sepanjang `jumlah_bit`.
    """
    if not kunci or not isinstance(kunci, str):
        raise ValueError("Kunci harus berupa string tidak kosong.")
    if not isinstance(jumlah_bit, int) or jumlah_bit < 1:
        raise ValueError("Jumlah bit harus bilangan bulat >= 1.")
    if not isinstance(alpha, (int, float)) or float(alpha) <= 0:
        raise ValueError(f"Alpha harus > 0, ditemukan {alpha}.")
    asli, mode_asli, _ = _ke_luminansi_dan_warna(citra_asli)
    uji, mode_uji, _ = _ke_luminansi_dan_warna(citra_input)
    if mode_asli != mode_uji:
        raise ValueError(
            f"Kanal citra beda: asli ({mode_asli}) vs input ({mode_uji}). "
            "Ekstraksi non-blind butuh kanal identik."
        )
    if asli.shape == uji.shape:
        return _ekstrak_selaras(asli, uji, kunci, jumlah_bit)
    if uji.shape[0] > asli.shape[0] or uji.shape[1] > asli.shape[1]:
        raise ValueError(
            f"Citra input ({uji.shape[1]}x{uji.shape[0]}) lebih besar dari citra "
            f"asli ({asli.shape[1]}x{asli.shape[0]}) — tidak ada blok pembanding."
        )
    return _ekstrak_toleran_crop(asli, uji, kunci, jumlah_bit, float(alpha))


def _dct_blok_dari_luminansi(luminansi, jumlah_proses=None):
    """DCT paralel + info grid blok untuk satu kanal luminansi."""
    daftar_blok, tinggi, lebar, tinggi_pad, lebar_pad = pecah_ke_blok_8x8(luminansi)
    return (terapkan_dct_paralel(daftar_blok, jumlah_proses),
            tinggi_pad // UKURAN_BLOK, lebar_pad // UKURAN_BLOK)


def _ekstrak_selaras(asli, uji, kunci: str, jumlah_bit: int,
                     jumlah_proses=None) -> list:
    """Ekstraksi bila dimensi identik (jalur cepat tanpa pencarian offset)."""
    dct_asli, _, _ = _dct_blok_dari_luminansi(asli, jumlah_proses)
    dct_uji, _, _ = _dct_blok_dari_luminansi(uji, jumlah_proses)
    if jumlah_bit > len(dct_asli):
        raise ValueError(
            f"Jumlah bit ({jumlah_bit}) melebihi kapasitas citra "
            f"({len(dct_asli)} blok)."
        )
    permutasi = generate_position_permutation(kunci, len(dct_asli), n_select=jumlah_bit)
    deret_pn = generate_bipolar_sequence(kunci, jumlah_bit)
    hasil = []
    for i in range(jumlah_bit):
        p = int(permutasi[i])
        delta = (dct_uji[p][BARIS_SISIP][KOLOM_SISIP]
                 - dct_asli[p][BARIS_SISIP][KOLOM_SISIP])
        hasil.append(1 if delta * float(deret_pn[i]) > 0 else 0)
    return hasil


def _ekstrak_toleran_crop(asli, uji, kunci: str, jumlah_bit: int,
                          alpha: float, jumlah_proses=None) -> list:
    """Ekstraksi bila input lebih kecil (crop): cari offset blok terbaik."""
    dct_asli, baris_asli, kolom_asli = _dct_blok_dari_luminansi(asli, jumlah_proses)
    dct_uji, baris_uji, kolom_uji = _dct_blok_dari_luminansi(uji, jumlah_proses)
    if jumlah_bit > len(dct_asli):
        raise ValueError(
            f"Jumlah bit ({jumlah_bit}) melebihi kapasitas citra "
            f"({len(dct_asli)} blok)."
        )
    permutasi = generate_position_permutation(kunci, len(dct_asli), n_select=jumlah_bit)
    deret_pn = generate_bipolar_sequence(kunci, jumlah_bit)
    # Posisi grid tiap blok asli (raster) agar pencarian offset murah.
    pos_asli = [(p // kolom_asli, p % kolom_asli) for p in
                (int(x) for x in permutasi)]

    def skor_dan_delta(ox: int, oy: int):
        """Skor offset kandidat + daftar delta.

        Semua blok yang dievaluasi membawa tepat 1 bit tersisip, sehingga
        pada offset yang benar |delta| ~= alpha untuk tiap bit (crop tidak
        mengubah nilai piksel penyintas). Skor = MEDIAN ||delta|-alpha|:
        median (bukan mean) agar tahan outlier — serangan gabungan
        (JPEG+noise) menyebarkan sebagian delta jauh dari alpha sementara
        mayoritas tetap di sekitarnya. Offset salah memberi skor sebesar
        perbedaan konten.
        """
        simpang, delta = [], []
        for i, (bx, by) in enumerate(pos_asli):
            ix, iy = bx - ox, by - oy
            if 0 <= ix < baris_uji and 0 <= iy < kolom_uji:
                p = int(permutasi[i])
                q = ix * kolom_uji + iy
                d = (dct_uji[q][BARIS_SISIP][KOLOM_SISIP]
                     - dct_asli[p][BARIS_SISIP][KOLOM_SISIP])
                simpang.append(abs(abs(d) - alpha))
                delta.append(d)
            else:
                delta.append(None)  # blok ikut terpotong
        if not simpang:
            return (float("inf"), delta, 0)
        simpang.sort()
        n = len(simpang)
        tengah = simpang[n // 2] if n % 2 else (simpang[n // 2 - 1] + simpang[n // 2]) / 2
        return (tengah, delta, n)

    ox_maks, oy_maks = baris_asli - baris_uji, kolom_asli - kolom_uji
    terbaik = (float("inf"), None, None, None, 0)
    kedua = float("inf")
    for ox in range(ox_maks + 1):
        for oy in range(oy_maks + 1):
            skor, delta, cacah = skor_dan_delta(ox, oy)
            if skor < terbaik[0]:
                kedua = terbaik[0]
                terbaik = (skor, ox, oy, delta, cacah)
            elif skor < kedua:
                kedua = skor
    skor, ox, oy, delta, cacah = terbaik
    # Kriteria ganda: di bawah batas absolut (sinyal masih menyerupai alpha)
    # DAN menonjol dari offset lain (margin). Kunci salah / grid liar memberi
    # skor besar-merata di semua offset sehingga marginnya kecil -> ditolak.
    margin_ok = (kedua == float("inf")) or (skor < 0.5 * kedua)
    if skor >= alpha or cacah == 0 or not margin_ok:
        raise ValueError(
            f"Sinkronisasi blok tidak ditemukan (skor {skor:.2f}). "
            "Crop tampaknya tidak selaras grid 8x8 atau kunci salah "
            "(mis. crop manual dari luar sistem) — watermark tak-tersinkron "
            "= tidak terdeteksi."
        )
    hasil = []
    for i, d in enumerate(delta):
        if d is None:
            hasil.append(0)  # erasure jujur: blok hilang -> bit hangus
        else:
            hasil.append(1 if d * float(deret_pn[i]) > 0 else 0)
    return hasil

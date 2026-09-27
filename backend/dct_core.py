"""dct_core.py — Transformasi 2D-DCT dan Inverse 2D-DCT murni untuk blok 8x8.

Aturan ketat proyek (lihat AI.md):
- WAJIB menulis rumus sigma ganda (double-summation) kosinus secara eksplisit.
- DILARANG memakai cv2.dct(), scipy.fftpack.dct(), numpy.fft, atau fungsi bawaan sejenis.
- Modul ini hanya memakai `math` bawaan Python (cos, sqrt, pi).

Rumus DCT-II 2D (ukuran N=8):

    F(u,v) = 1/4 * C(u) * C(v)
             * sum_{x=0..7} sum_{y=0..7} f(x,y)
             * cos((2x+1) * u * pi / 16)
             * cos((2y+1) * v * pi / 16)

    dengan C(0) = 1/sqrt(2), C(k) = 1 untuk k > 0.

Rumus Inverse DCT (DCT-III) 2D:

    f(x,y) = 1/4 * sum_{u=0..7} sum_{v=0..7} C(u) * C(v) * F(u,v)
             * cos((2x+1) * u * pi / 16)
             * cos((2y+1) * v * pi / 16)

Semua komentar dan pesan error memakai Bahasa Indonesia.
"""

import math

# Ukuran blok yang didukung (sesuai standar JPEG / kebutuhan watermarking).
UKURAN_BLOK = 8


def _faktor_normalisasi(k: int) -> float:
    """Faktor ortonormalisasi C(k): 1/sqrt(2) jika k=0, sonst 1."""
    if k == 0:
        return 1.0 / math.sqrt(2.0)
    return 1.0


def _validasi_blok_8x8(matriks, nama: str = "masukan") -> None:
    """Validasi bahwa matriks adalah list 8 baris x 8 kolom berisi angka."""
    if not isinstance(matriks, (list, tuple)) or len(matriks) != UKURAN_BLOK:
        raise ValueError(
            f"Blok {nama} harus berukuran 8x8: "
            f"ditemukan {len(matriks) if isinstance(matriks, (list, tuple)) else type(matriks)} baris."
        )
    for i, baris in enumerate(matriks):
        if not isinstance(baris, (list, tuple)) or len(baris) != UKURAN_BLOK:
            raise ValueError(
                f"Blok {nama} harus berukuran 8x8: "
                f"baris ke-{i} memiliki panjang "
                f"{len(baris) if isinstance(baris, (list, tuple)) else type(baris)}."
            )
        for nilai in baris:
            if not isinstance(nilai, (int, float)):
                raise ValueError(
                    f"Blok {nama} harus berisi angka, ditemukan {type(nilai).__name__}."
                )


def hitung_dct_8x8(blok_spasial):
    """Menghitung 2D-DCT (tipe II) dari blok spasial 8x8.

    Args:
        blok_spasial: matriks 8x8 (list berisi 8 list, masing-masing 8 float/int),
            berisi nilai piksel domain spasial (misal 0..255 atau sudah digeser -128).

    Returns:
        Matriks 8x8 koefisien frekuensi F(u,v) sebagai list-of-list float.

    Rumus eksplisit per koefisien (u,v):
        F(u,v) = 0.25 * C(u) * C(v)
                 * Σ_x Σ_y f(x,y) * cos((2x+1)*u*π/16) * cos((2y+1)*v*π/16)
    """
    _validasi_blok_8x8(blok_spasial, "spasial")

    N = UKURAN_BLOK
    hasil = [[0.0 for _ in range(N)] for _ in range(N)]

    # Loop luar: setiap posisi frekuensi (u, v).
    for u in range(N):
        cu = _faktor_normalisasi(u)
        for v in range(N):
            cv = _faktor_normalisasi(v)

            # Sigma ganda eksplisit atas domain spasial (x, y).
            jumlah = 0.0
            for x in range(N):
                # Sudut kosinus arah baris untuk pasangan (x, u).
                sudut_x = ((2 * x + 1) * u * math.pi) / (2 * N)
                cos_x = math.cos(sudut_x)
                for y in range(N):
                    # Sudut kosinus arah kolom untuk pasangan (y, v).
                    sudut_y = ((2 * y + 1) * v * math.pi) / (2 * N)
                    cos_y = math.cos(sudut_y)
                    jumlah += float(blok_spasial[x][y]) * cos_x * cos_y

            hasil[u][v] = 0.25 * cu * cv * jumlah

    return hasil


def hitung_idct_8x8(blok_frekuensi):
    """Menghitung Inverse 2D-DCT (tipe III) dari blok koefisien 8x8.

    Args:
        blok_frekuensi: matriks 8x8 koefisien DCT F(u,v).

    Returns:
        Matriks 8x8 domain spasial f(x,y) sebagai list-of-list float.

    Rumus eksplisit per piksel (x, y):
        f(x,y) = 0.25 * Σ_u Σ_v C(u) * C(v) * F(u,v)
                 * cos((2x+1)*u*π/16) * cos((2y+1)*v*π/16)
    """
    _validasi_blok_8x8(blok_frekuensi, "frekuensi")

    N = UKURAN_BLOK
    hasil = [[0.0 for _ in range(N)] for _ in range(N)]

    # Loop luar: setiap posisi spasial (x, y) yang direkonstruksi.
    for x in range(N):
        for y in range(N):
            # Sigma ganda eksplisit atas domain frekuensi (u, v).
            jumlah = 0.0
            for u in range(N):
                cu = _faktor_normalisasi(u)
                sudut_x = ((2 * x + 1) * u * math.pi) / (2 * N)
                cos_x = math.cos(sudut_x)
                for v in range(N):
                    cv = _faktor_normalisasi(v)
                    sudut_y = ((2 * y + 1) * v * math.pi) / (2 * N)
                    cos_y = math.cos(sudut_y)
                    jumlah += cu * cv * float(blok_frekuensi[u][v]) * cos_x * cos_y

            hasil[x][y] = 0.25 * jumlah

    return hasil


# Alias Inggris agar mudah dipakai dari modul lain / pengujian.
# Nama Indonesia tetap menjadi API utama.
def dct_2d_8x8(blok_spasial):
    """Alias dari hitung_dct_8x8 (untuk kompatibilitas penamaan Inggris)."""
    return hitung_dct_8x8(blok_spasial)


def idct_2d_8x8(blok_frekuensi):
    """Alias dari hitung_idct_8x8 (untuk kompatibilitas penamaan Inggris)."""
    return hitung_idct_8x8(blok_frekuensi)

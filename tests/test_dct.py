"""Unit test DCT murni: rekonstruksi & jawaban-dikenal (UJI.md §4 test 1-2).

DCT di sini versi double-summation eksplisit (lihat dct_core.py); test 2
memakai vektor jawaban-dikenal (blok konstan -> hanya DC) sebagai
pengganti perbandingan matriks-vs-naive.
"""

import math
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR))

from backend.dct_core import hitung_dct_8x8, hitung_idct_8x8


def test_dct_idct_reconstruction():
    """idct(dct(blok)) ~= blok untuk pola deterministik."""
    blok = [[float((x * 8 + y) % 256) for y in range(8)] for x in range(8)]
    susun = hitung_idct_8x8(hitung_dct_8x8(blok))
    maks_galat = max(abs(susun[x][y] - blok[x][y])
                     for x in range(8) for y in range(8))
    assert maks_galat < 1e-6, f"galat rekonstruksi {maks_galat}"


def test_dct_blok_konstan_hanya_dc():
    """Blok konstan c -> F(0,0) = 8c, koefisien lain ~0 (jawaban dikenal)."""
    c = 100.0
    blok = [[c] * 8 for _ in range(8)]
    hasil = hitung_dct_8x8(blok)
    assert hasil[0][0] == abs(hasil[0][0]) and abs(hasil[0][0] - 8 * c) < 1e-6
    sisa = max(abs(hasil[u][v]) for u in range(8) for v in range(8)
               if (u, v) != (0, 0))
    assert sisa < 1e-6, f"koefisien AC bocor {sisa}"


def test_dct_menolak_blok_salah_ukuran():
    """Validasi dimensi 8x8 ditegakkan."""
    try:
        hitung_dct_8x8([[1.0] * 7 for _ in range(8)])
    except ValueError:
        return
    raise AssertionError("blok 8x7 lolos validasi")

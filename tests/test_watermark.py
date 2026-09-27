"""Unit test sisip-ekstrak: bersih & pasca-JPEG50 (UJI.md §4 test 4-5 + 6).

Sengaja serial (jumlah_proses=1) dan mungil (64x64, 64 bit) agar hijau
dalam hitungan detik tanpa Pool multiprocessing.
"""

import sys
from pathlib import Path

import numpy as np
from PIL import Image

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR))

from backend.attacker import kompresi_jpeg
from backend.evaluator import hitung_psnr, hitung_nc, hitung_ber
from backend.watermark_engine import (
    sisip_watermark, ekstrak_watermark, teks_ke_bit,
)

BIT_UJI = teks_ke_bit("UNITEST!")
KUNCI = "kunci-unit-test"


def _cover_mungil():
    rng = np.random.default_rng(42)
    return Image.fromarray(
        (rng.uniform(0, 255, (64, 64, 3))).astype(np.uint8), mode="RGB")


def test_embed_extract_tanpa_serangan():
    """Sisip -> ekstrak langsung: NC ~= 1.0, BER ~= 0% (UJI §4 test 4)."""
    cover = _cover_mungil()
    stego = sisip_watermark(cover, BIT_UJI, KUNCI, alpha=15.0, jumlah_proses=1)
    assert hitung_psnr(cover, stego) > 30.0
    hasil = ekstrak_watermark(cover, stego, KUNCI, len(BIT_UJI), jumlah_proses=1)
    assert hitung_nc(BIT_UJI, hasil) >= 0.99
    assert hitung_ber(BIT_UJI, hasil) == 0.0


def test_embed_extract_setelah_jpeg50():
    """Sisip -> JPEG50 -> ekstrak: NC > 0.7 = bukti sifat robust (test 5)."""
    cover = _cover_mungil()
    stego = sisip_watermark(cover, BIT_UJI, KUNCI, alpha=15.0, jumlah_proses=1)
    uji = kompresi_jpeg(stego, kualitas=50)
    hasil = ekstrak_watermark(cover, uji, KUNCI, len(BIT_UJI), jumlah_proses=1)
    assert hitung_nc(BIT_UJI, hasil) > 0.7


def test_psnr_citra_identik_tak_hingga():
    """Dua citra identik -> PSNR inf (UJI §4 test 6 opsional)."""
    cover = _cover_mungil()
    assert hitung_psnr(cover, cover) == float("inf")

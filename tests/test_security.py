"""Unit test kunci & PN: unik, deterministik, tanpa hardcode (UJI.md §4 test 3)."""

import re
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AKAR))

from backend.security import (
    generate_secure_key, generate_binary_sequence,
    generate_position_permutation, keys_produce_different_sequences,
)


def test_key_unik_setiap_pembangkitan():
    """Dua kunci berurutan dari secrets tidak boleh sama."""
    assert generate_secure_key() != generate_secure_key()


def test_deret_deterministik_dan_sensitif_kunci():
    """Kunci sama -> deret sama; kunci beda -> deret jelas beda."""
    kunci = generate_secure_key()
    assert (generate_binary_sequence(kunci, 64) ==
            generate_binary_sequence(kunci, 64)).all()
    assert keys_produce_different_sequences(kunci, generate_secure_key(), 256)


def test_permutasi_tanpa_duplikat_dan_terbatas():
    """Permutasi posisi unik dan menghormati n_select."""
    posisi = generate_position_permutation(generate_secure_key(), 256, n_select=64)
    assert len(posisi) == 64 and len(set(posisi.tolist())) == 64


def test_tidak_ada_kunci_hardcode():
    """Kode sumber security.py tidak boleh mengandung literal kunci heks."""
    sumber = (AKAR / "backend" / "security.py").read_text(encoding="utf-8")
    literal = re.findall(r"['\"][0-9a-fA-F]{32,}['\"]", sumber)
    assert not literal, f"kandidat kunci tertanam: {literal[:3]}"

"""
security.py
============
Modul keamanan kunci & pembangkit deret pseudo-noise (PN) untuk menentukan
posisi/pola penyisipan watermark pada koefisien DCT frekuensi menengah.

Prinsip yang dipegang (sesuai AI.md & BACKEND.md):

1. Kunci rahasia TIDAK PERNAH di-hardcode di kode sumber. Kunci baru
   dibangkitkan saat runtime memakai `secrets` (CSPRNG bawaan Python),
   atau ditangkap langsung dari input pengguna di antarmuka.
2. Deret pseudo-noise (posisi blok, polaritas spread-spectrum) harus
   REPRODUCIBLE dari kunci yang sama, supaya proses ekstraksi nanti
   menghasilkan posisi yang identik dengan proses penyisipan. Karena itu,
   kunci apa pun (hasil generate ataupun ketikan manual pengguna)
   diturunkan dulu menjadi seed numerik lewat SHA-256 (`hashlib`,
   pustaka standar Python — bukan bagian dari larangan pustaka DCT),
   baru dipakai menyalakan generator NumPy `default_rng`. NumPy di sini
   murni sebagai struktur array & generator berurutan, bukan fungsi
   transformasi DCT — tidak melanggar batasan proyek.
3. `secrets` dipakai untuk MEMBANGKITKAN kunci baru (entropi tidak bisa
   ditebak). Setelah kunci itu ada, ekspansi jadi deret PN memakai PRNG
   deterministik (bukan CSPRNG lagi) — karena sifatnya justru harus bisa
   diulang persis dengan kunci yang sama saat ekstraksi berlangsung.
"""

import hashlib
import secrets

import numpy as np


def generate_secure_key(n_bytes: int = 32) -> str:
    """
    Membangkitkan kunci rahasia baru secara aman memakai CSPRNG bawaan
    Python (`secrets.token_hex`), untuk kasus pengguna belum punya kunci
    sendiri. TIDAK PERNAH dipanggil dengan nilai tertanam — entropi murni
    dari `secrets` saat runtime, ditampilkan sekali ke pengguna via UI
    agar mereka simpan sendiri (server tidak menyimpan salinan permanen).
    """
    return secrets.token_hex(n_bytes)


def _derive_seed(key: str) -> int:
    """
    Menurunkan kunci (string, boleh dari `generate_secure_key()` ataupun
    ketikan manual pengguna) menjadi seed numerik lewat SHA-256. Ini
    BUKAN pembangkit kunci — hanya konversi format supaya bisa dipakai
    menyalakan PRNG NumPy secara deterministik dan tahan tebak (hash
    kriptografis, bukan pemetaan linear yang mudah ditiru).
    """
    if not key or not isinstance(key, str):
        raise ValueError("Kunci harus berupa string tidak kosong.")
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    return int.from_bytes(digest, byteorder="big")


def _get_rng(key: str) -> np.random.Generator:
    """Generator NumPy yang deterministik terhadap `key` yang sama."""
    return np.random.default_rng(_derive_seed(key))


def generate_binary_sequence(key: str, length: int) -> np.ndarray:
    """
    Deret pseudo-random biner (0/1) sepanjang `length`, deterministik
    terhadap `key`. Dipakai bila bit watermark ditentukan langsung
    sebagai 0/1 (mis. paritas kuantisasi koefisien).
    """
    rng = _get_rng(key)
    return rng.integers(0, 2, size=length, dtype=np.int8)


def generate_bipolar_sequence(key: str, length: int) -> np.ndarray:
    """
    Deret pseudo-noise bipolar (-1/+1) sepanjang `length`, deterministik
    terhadap `key`. Bentuk PN yang lazim untuk penyisipan spread-spectrum:

        F'(u,v) = F(u,v) + alpha * PN(i)
    """
    rng = _get_rng(key)
    return rng.choice(np.array([-1, 1], dtype=np.int8), size=length)


def generate_position_permutation(key: str, total_positions: int, n_select: int | None = None) -> np.ndarray:
    """
    Permutasi pseudo-random dari indeks 0..total_positions-1, deterministik
    terhadap `key`. Dipakai untuk mengacak urutan blok 8x8 (atau koefisien
    frekuensi menengah di dalamnya) yang dipilih sebagai lokasi penyisipan,
    sehingga posisi watermark tidak bisa ditebak tanpa `key` yang benar.

    Jika `n_select` diberikan, hanya `n_select` posisi pertama dari
    permutasi yang dikembalikan (mis. sejumlah blok yang benar-benar
    dibutuhkan untuk menampung panjang watermark).
    """
    rng = _get_rng(key)
    permutasi = rng.permutation(total_positions)
    if n_select is not None:
        if n_select > total_positions:
            raise ValueError(
                "n_select tidak boleh melebihi total_positions (kapasitas citra tidak cukup untuk watermark ini)."
            )
        return permutasi[:n_select]
    return permutasi


def keys_produce_different_sequences(key_a: str, key_b: str, length: int = 256) -> bool:
    """
    Utilitas verifikasi: True jika dua kunci berbeda menghasilkan deret
    biner yang jelas berbeda (rasio bit berbeda cukup tinggi). Hanya
    dipakai untuk self-test, bukan bagian dari alur produksi.
    """
    a = generate_binary_sequence(key_a, length)
    b = generate_binary_sequence(key_b, length)
    rasio_beda = np.mean(a != b)
    # Untuk dua kunci independen, rasio bit berbeda idealnya mendekati 0.5
    return rasio_beda > 0.3


if __name__ == "__main__":
    print("[check] Membangkitkan kunci baru via secrets.token_hex() ...")
    kunci_baru = generate_secure_key()
    print(f"[check] Panjang kunci: {len(kunci_baru)} karakter hex ({len(kunci_baru) // 2} byte entropi)")

    print("\n[check] Determinisme: kunci sama -> deret sama?")
    seq1 = generate_binary_sequence(kunci_baru, 32)
    seq2 = generate_binary_sequence(kunci_baru, 32)
    sama = bool(np.array_equal(seq1, seq2))
    print(f"[check] seq1 == seq2 : {sama}")
    assert sama, "Deret biner tidak konsisten untuk kunci yang sama!"

    print("\n[check] Dua kunci berbeda -> deret berbeda signifikan?")
    kunci_lain = generate_secure_key()
    beda = keys_produce_different_sequences(kunci_baru, kunci_lain, length=1024)
    print(f"[check] kunci berbeda menghasilkan deret signifikan berbeda: {beda}")
    assert beda

    print("\n[check] Permutasi posisi blok valid (tanpa duplikat)?")
    total_blok = 4096  # misal citra 512x512 -> (512/8)^2 blok
    posisi = generate_position_permutation(kunci_baru, total_blok, n_select=1024)
    unik = len(set(posisi.tolist())) == len(posisi)
    print(f"[check] {len(posisi)} posisi terpilih, semua unik: {unik}")
    assert unik

    print("\n[check] SEMUA VERIFIKASI LULUS ✔")
"""security.py — Pembangkit deret pseudo-noise (PN) biner yang aman untuk watermarking.

Aturan ketat proyek (lihat AI.md):
- Kunci / kata sandi / seed DILARANG di-hardcode di kode sumber.
  Seed selalu diterima sebagai parameter dari input pengguna (antarmuka),
  atau dibangkitkan acak saat runtime memakai modul `secrets` (CSPRNG).
- Modul ini memakai `secrets` untuk keacakan aman dan `hashlib.sha256`
  sebagai penurun deterministik (hash-DRBG sederhana) agar deret yang
  dibangkitkan dari seed yang sama selalu identik — syarat agar ekstraksi
  watermark menghasilkan deret yang sama dengan saat penyisipan.

Semua komentar dan pesan error memakai Bahasa Indonesia.
"""

import hashlib
import secrets

# Panjang seed acak bawaan (dalam byte) bila pengguna tidak mengisi seed.
PANJANG_SEED_BYTE_BAWAN = 16


def _validasi_seed(seed: str) -> str:
    """Validasi seed string dari pengguna, kembalikan seed yang sudah dirapikan."""
    if not isinstance(seed, str):
        raise ValueError(
            f"Seed harus berupa string, ditemukan {type(seed).__name__}."
        )
    seed_bersih = seed.strip()
    if not seed_bersih:
        raise ValueError("Seed tidak boleh kosong — isi seed dari input pengguna.")
    return seed_bersih


def _validasi_panjang(panjang_n: int) -> int:
    """Validasi panjang deret N harus bilangan bulat positif."""
    if isinstance(panjang_n, bool) or not isinstance(panjang_n, int):
        raise ValueError(
            f"Panjang deret (N) harus bilangan bulat, ditemukan {type(panjang_n).__name__}."
        )
    if panjang_n <= 0:
        raise ValueError(f"Panjang deret (N) harus > 0, ditemukan {panjang_n}.")
    return panjang_n


def bangkitkan_seed_aman(panjang_byte: int = PANJANG_SEED_BYTE_BAWAN) -> str:
    """Membangkitkan seed acak yang aman memakai CSPRNG `secrets`.

    Dipakai saat pengguna tidak mengisi seed sendiri — aplikasi memanggil
    fungsi ini saat runtime (tidak ada kunci yang di-hardcode).

    Args:
        panjang_byte: jumlah byte acak (minimal 8). Makin besar makin kuat.

    Returns:
        String heksadesimal sepanjang 2 * panjang_byte karakter.
    """
    if isinstance(panjang_byte, bool) or not isinstance(panjang_byte, int):
        raise ValueError("Panjang byte seed harus bilangan bulat.")
    if panjang_byte < 8:
        raise ValueError(
            f"Panjang byte seed minimal 8 demi keamanan, ditemukan {panjang_byte}."
        )
    # secrets.token_hex memakai os.urandom di balik layar (CSPRNG sistem).
    return secrets.token_hex(panjang_byte)


def bangkitkan_deret_pn(seed: str, panjang_n: int) -> list:
    """Membangkitkan deret pseudo-random biner (0/1) sepanjang N dari seed string.

    Deterministik: seed yang sama selalu menghasilkan deret yang sama
    (dibutuhkan agar ekstraksi bisa merekonstruksi posisi watermark).
    Keacakan: tiap blok 32-byte diambil dari SHA-256(seed:counter) lalu
    dipecah per bit (MSB ke LSB), sehingga deret lolos uji sebaran bit
    untuk kebutuhan spread-spectrum.

    Args:
        seed: string rahasia dari input pengguna (tidak di-hardcode).
        panjang_n: panjang deret yang diminta (jumlah bit watermark / blok).

    Returns:
        List berisi 0/1 sepanjang `panjang_n`.

    Contoh:
        >>> bangkitkan_deret_pn("kunci-rahasia-zine", 16)
        [..., ..., ...]  # 16 bit, deterministik
    """
    seed_bersih = _validasi_seed(seed)
    _validasi_panjang(panjang_n)

    deret = []
    pencacah = 0
    # Satu hash SHA-256 menghasilkan 32 byte = 256 bit; iterasi pencacah
    # sampai seluruh N bit terpenuhi (konstruksi hash-DRBG mode counter).
    while len(deret) < panjang_n:
        bahan = f"{seed_bersih}:{pencacah}".encode("utf-8")
        cerna = hashlib.sha256(bahan).digest()
        for byte in cerna:
            # Urai byte menjadi 8 bit dari MSB ke LSB.
            for geser in range(7, -1, -1):
                if len(deret) >= panjang_n:
                    break
                deret.append((byte >> geser) & 1)
            if len(deret) >= panjang_n:
                break
        pencacah += 1
    return deret


def bangkitkan_posisi_watermark(seed: str, jumlah_blok: int, jumlah_bit: int) -> list:
    """Menentukan posisi blok 8x8 terpilih untuk tiap bit watermark.

    Pengacakan Fisher-Yates deterministik: urutan dikocok memakai angka acak
    turunan SHA-256(seed:posisi:i) sehingga embed dan extract yang memakai
    seed sama selalu sepakat pada urutan posisi yang sama, tanpa perlu
    menyimpan tabel posisi.

    Args:
        seed: string rahasia dari input pengguna.
        jumlah_blok: total blok 8x8 yang tersedia pada gambar.
        jumlah_bit: jumlah bit watermark (= jumlah blok yang dipilih).

    Returns:
        List indeks blok terpilih sepanjang `jumlah_bit` (unik, 0..jumlah_blok-1).
    """
    seed_bersih = _validasi_seed(seed)
    for nama, nilai in (("jumlah_blok", jumlah_blok), ("jumlah_bit", jumlah_bit)):
        if isinstance(nilai, bool) or not isinstance(nilai, int) or nilai <= 0:
            raise ValueError(f"{nama} harus bilangan bulat > 0, ditemukan {nilai}.")
    if jumlah_bit > jumlah_blok:
        raise ValueError(
            f"Jumlah bit ({jumlah_bit}) melebihi jumlah blok tersedia ({jumlah_blok})."
        )

    # Mulai dari urutan identitas, lalu kocok Fisher-Yates mundur.
    indeks = list(range(jumlah_blok))
    for i in range(jumlah_blok - 1, 0, -1):
        bahan = f"{seed_bersih}:posisi:{i}".encode("utf-8")
        angka_acak = int.from_bytes(hashlib.sha256(bahan).digest(), "big")
        j = angka_acak % (i + 1)
        indeks[i], indeks[j] = indeks[j], indeks[i]
    # Ambil K terdepan dalam urutan terkocok (urutan dipertahankan).
    return indeks[:jumlah_bit]


def deret_ke_bipolar(deret_biner: list) -> list:
    """Mengubah deret biner 0/1 menjadi deret bipolar -1/+1 untuk spread-spectrum.

    Args:
        deret_biner: list berisi hanya 0 dan 1.

    Returns:
        List berisi -1 (untuk 0) dan +1 (untuk 1).
    """
    if not isinstance(deret_biner, (list, tuple)) or len(deret_biner) == 0:
        raise ValueError("Deret biner harus list/tuple tak-kosong berisi 0/1.")
    hasil = []
    for posisi, bit in enumerate(deret_biner):
        if bit not in (0, 1):
            raise ValueError(
                f"Deret hanya boleh berisi 0/1, indeks ke-{posisi} bernilai {bit}."
            )
        hasil.append(1 if bit == 1 else -1)
    return hasil


# Alias Inggris agar mudah dipakai dari modul lain / pengujian.
# Nama Indonesia tetap menjadi API utama.
def generate_pn_sequence(seed: str, panjang_n: int) -> list:
    """Alias dari bangkitkan_deret_pn (untuk kompatibilitas penamaan Inggris)."""
    return bangkitkan_deret_pn(seed, panjang_n)


def generate_secure_seed(panjang_byte: int = PANJANG_SEED_BYTE_BAWAN) -> str:
    """Alias dari bangkitkan_seed_aman (untuk kompatibilitas penamaan Inggris)."""
    return bangkitkan_seed_aman(panjang_byte)


def generate_watermark_positions(seed: str, jumlah_blok: int, jumlah_bit: int) -> list:
    """Alias dari bangkitkan_posisi_watermark (untuk kompatibilitas penamaan Inggris)."""
    return bangkitkan_posisi_watermark(seed, jumlah_blok, jumlah_bit)

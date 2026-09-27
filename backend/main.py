"""main.py — Controller FastAPI: routing endpoint & integrasi UI.

Endpoint yang sudah hidup:
- GET  /                          -> halaman UI (frontend/index.html)
- POST /api/watermark/embed       -> sisip watermark teks/logo + PSNR awal
- POST /api/watermark/extract     -> ekstrak non-blind + NC/BER bila pembanding diberi
- POST /api/attack/jpeg           -> kompresi JPEG (kualitas 90/70/50) + PSNR
- POST /api/attack/manipulation   -> noise/crop/resize/kontras/gabungan + PSNR
- POST /api/attack/semua          -> seluruh paket serangan sekaligus + PSNR

Prinsip satu endpoint satu tugas: endpoint attack hanya merusak citra
(PSNR); untuk NC/BER, teruskan citra hasilnya ke /api/watermark/extract.

Semua endpoint API mengembalikan JSON (konvensi proyek). Citra hasil
dikirim sebagai string base64 PNG agar mudah ditampilkan di <img>.
Komentar dan pesan error memakai Bahasa Indonesia.
"""

import asyncio
import base64
import io
import sys
from pathlib import Path

try:
    from backend.attacker import (
        kompresi_jpeg, serangan_noise_gaussian, serangan_crop_tengah,
        serangan_resize, serangan_kontras, serangan_q50_noise_crop,
        terapkan_semua_serangan_uji,
    )
    from backend.evaluator import hitung_psnr, hitung_nc, hitung_ber
    from backend.watermark_engine import (
        sisip_watermark, ekstrak_watermark, teks_ke_bit, bit_ke_teks,
        logo_ke_bit, bit_ke_logo, ALPHA_DEFAULT,
        sisip_watermark_blind, ekstrak_watermark_blind,
    )
except ImportError:  # pragma: no cover — dijalankan sebagai skrip langsung
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from attacker import (
        kompresi_jpeg, serangan_noise_gaussian, serangan_crop_tengah,
        serangan_resize, serangan_kontras, serangan_q50_noise_crop,
        terapkan_semua_serangan_uji,
    )
    from evaluator import hitung_psnr, hitung_nc, hitung_ber
    from watermark_engine import (
        sisip_watermark, ekstrak_watermark, teks_ke_bit, bit_ke_teks,
        logo_ke_bit, bit_ke_logo, ALPHA_DEFAULT,
        sisip_watermark_blind, ekstrak_watermark_blind,
    )

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from PIL import Image

app = FastAPI(title="Aplikasi Watermarking DCT — Demo Uji Serangan")

DIREKTORI_DEPAN = Path(__file__).resolve().parent.parent / "frontend"

# Request DCT-berat (embed/extract/semua) diserialkan: satu jalan, sisanya
# antre. Tanpa ini, klik beruntun menumpuk Pool multiprocessing → RAM habis
# → proses mati (ERR_CONNECTION_RESET/REFUSED di browser). Komputasi berat
# dilempar ke thread agar event loop tetap responsif saat antrean menunggu.
KUNCI_BERAT = asyncio.Lock()


# ---------------------------------------------------------------------------
# Pembantu internal
# ---------------------------------------------------------------------------

async def _baca_unggahan(berkas: UploadFile) -> Image.Image:
    """Membaca UploadFile menjadi PIL.Image, validasi format gambar."""
    isi = await berkas.read()
    if not isi:
        raise ValueError("Berkas kosong — unggah file gambar terlebih dahulu.")
    try:
        gambar = Image.open(io.BytesIO(isi))
        gambar.load()
    except Exception as eronya:
        raise ValueError(f"Berkas bukan gambar yang valid: {eronya}.")
    if gambar.width == 0 or gambar.height == 0:
        raise ValueError("Dimensi gambar nol.")
    return gambar


def _ke_base64(gambar: Image.Image) -> str:
    """Mengubah PIL.Image menjadi string base64 PNG (siap dipasang di <img>)."""
    penyangga = io.BytesIO()
    gambar.save(penyangga, format="PNG")
    return base64.b64encode(penyangga.getvalue()).decode("ascii")


def _psnr_adil(asli: Image.Image, uji: Image.Image) -> float:
    """PSNR dengan penyamaan ukuran: bila serangan mengubah ukuran (crop),
    citra asli ikut di-crop tengah ke ukuran hasil agar perbandingan setara."""
    if uji.size != asli.size:
        lw, lh = asli.size
        uw, uh = uji.size
        kiri = max(0, (lw - uw) // 2)
        atas = max(0, (lh - uh) // 2)
        acuan = asli.crop((kiri, atas, kiri + uw, atas + uh))
    else:
        acuan = asli
    nilai = hitung_psnr(acuan, uji)
    return nilai  # inf bila identik (JSON: dikirim sebagai string "inf")


def _bungkus_hasil(nama: str, asli: Image.Image, hasil: Image.Image) -> dict:
    """Membungkus satu hasil serangan ke dict JSON.

    Bila serangan mengubah ukuran (crop/gabungan), PSNR dinyatakan null
    (tak-terdefinisi): acuan yang tersedia hanyalah citra itu sendiri
    sehingga perbandingan menjadi sirkular (inf semu). Frontend
    menampilkan "n/a (ukuran berubah)".
    """
    if hasil.size != asli.size:
        psnr = None
    else:
        psnr = hitung_psnr(asli, hasil)
    return {
        "nama": nama,
        "psnr": psnr if psnr != float("inf") else "inf",
        "lebar": hasil.width,
        "tinggi": hasil.height,
        "citra_base64": _ke_base64(hasil),
    }


def _tanggapan_galat(pesan: str, kode: int = 400) -> JSONResponse:
    """Tanggapan JSON seragam untuk kesalahan input pengguna."""
    return JSONResponse(status_code=kode, content={"galat": pesan})


# ---------------------------------------------------------------------------
# Halaman UI
# ---------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
async def halaman_utama():
    """Menyajikan halaman UI tunggal (frontend/index.html)."""
    berkas = DIREKTORI_DEPAN / "index.html"
    if not berkas.exists():
        return _tanggapan_galat("Berkas UI belum ada.", 404)
    return FileResponse(str(berkas), media_type="text/html")


@app.get("/health")
async def cek_sehat():
    """Health-check ringan untuk monitoring/tunnel (selalu 200 bila hidup)."""
    return {"status": "ok"}


@app.get("/api/aset/logo-pola")
async def unduh_logo_pola():
    """Menyajikan logo pola 32x32 acuan agar Mode 3 memakai watermark identik
    dengan matriks XLSX (perbandingan apel-vs-apel)."""
    berkas = DIREKTORI_DEPAN.parent / "assets" / "logo_pola_32x32.png"
    if not berkas.exists():
        return _tanggapan_galat("Logo acuan tidak ditemukan.", 404)
    return FileResponse(str(berkas), media_type="image/png")


# ---------------------------------------------------------------------------
# Endpoint serangan
# ---------------------------------------------------------------------------

@app.post("/api/attack/jpeg")
async def serang_jpeg(
    berkas: UploadFile = File(..., description="Citra yang diserang"),
    kualitas: int = Form(50, description="Kualitas JPEG 1..95 (uji: 90/70/50)"),
):
    """Menerapkan kompresi JPEG lalu menghitung PSNR terhadap citra asli."""
    try:
        asli = await _baca_unggahan(berkas)
        hasil = kompresi_jpeg(asli, kualitas=kualitas)
    except ValueError as eronya:
        return _tanggapan_galat(str(eronya))
    return _bungkus_hasil(f"jpeg_{kualitas}", asli, hasil)


JENIS_MANIPULASI = ("noise", "crop", "resize", "kontras", "gabungan")


@app.post("/api/attack/manipulation")
async def serang_manipulasi(
    berkas: UploadFile = File(..., description="Citra yang diserang"),
    jenis: str = Form(..., description="noise/crop/resize/kontras/gabungan"),
    std_noise: float = Form(10.0, description="Kekuatan Gaussian noise"),
    proporsi_crop: float = Form(0.25, description="Fraksi luas crop 0..1"),
    skala_resize: float = Form(0.5, description="Skala resize 0..1"),
    faktor_kontras: float = Form(1.2, description="Faktor kontras > 0"),
    kecerahan: float = Form(20.0, description="Pergeseran kecerahan skala piksel"),
    seed: int = Form(1, description="Seed noise agar reproduksibel"),
):
    """Menerapkan satu manipulasi lalu menghitung PSNR terhadap citra asli."""
    if jenis not in JENIS_MANIPULASI:
        return _tanggapan_galat(
            f"Jenis '{jenis}' tidak dikenal — pilih: {', '.join(JENIS_MANIPULASI)}."
        )
    try:
        asli = await _baca_unggahan(berkas)
        if jenis == "noise":
            hasil = serangan_noise_gaussian(asli, simpangan_baku=std_noise, seed=seed)
        elif jenis == "crop":
            hasil = serangan_crop_tengah(asli, proporsi=proporsi_crop)
        elif jenis == "resize":
            hasil = serangan_resize(asli, skala=skala_resize)
        elif jenis == "kontras":
            hasil = serangan_kontras(asli, faktor=faktor_kontras,
                                     kecerahan=kecerahan)
        else:  # gabungan: JPEG50 -> noise -> crop 20%
            hasil = serangan_q50_noise_crop(
                asli, simpangan_baku=std_noise,
                proporsi_crop=proporsi_crop, seed=seed,
            )
    except ValueError as eronya:
        return _tanggapan_galat(str(eronya))
    return _bungkus_hasil(jenis, asli, hasil)


@app.post("/api/attack/semua")
async def serang_semua(
    berkas: UploadFile = File(..., description="Citra yang diserang"),
    seed: int = Form(1, description="Seed noise agar reproduksibel"),
):
    """Menjalankan seluruh paket serangan wajib sekaligus + PSNR tiap hasil."""
    try:
        asli = await _baca_unggahan(berkas)
        async with KUNCI_BERAT:
            paket = await asyncio.to_thread(terapkan_semua_serangan_uji, asli, seed)
            hasil = await asyncio.to_thread(
                lambda: [_bungkus_hasil(n, asli, c) for n, c in paket.items()])
    except ValueError as eronya:
        return _tanggapan_galat(str(eronya))
    return {
        "lebar_asli": asli.width,
        "tinggi_asli": asli.height,
        "hasil": hasil,
    }


# Peluncur langsung: `python backend/main.py` (tanpa reload).
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000)


# ---------------------------------------------------------------------------
# Endpoint watermark: sisip & ekstrak (satu endpoint satu tugas)
# ---------------------------------------------------------------------------

def _status_kepemilikan(nc: float) -> str:
    """Label ramah pengguna dari skor NC (ambang sementara BACKEND.md §3.1)."""
    if nc >= 0.75:
        return "Watermark Terdeteksi Kuat"
    if nc >= 0.4:
        return "Terdeteksi Sebagian"
    return "Tidak Terdeteksi"


@app.post("/api/watermark/embed")
async def sisip(
    berkas: UploadFile = File(..., description="Citra cover"),
    key: str = Form(..., description="Kunci rahasia (tidak disimpan server)"),
    alpha: float = Form(ALPHA_DEFAULT, description="Kekuatan sisipan > 0"),
    teks: str = Form("", description="Teks watermark (isi salah satu: teks/logo)"),
    logo: UploadFile | None = File(None, description="Logo biner (opsional)"),
):
    """Menyisipkan watermark (teks ATAU logo) ke citra cover + PSNR awal."""
    ada_teks = bool(teks and teks.strip())
    ada_logo = logo is not None and logo.filename
    if ada_teks == bool(ada_logo):
        return _tanggapan_galat(
            "Isi tepat satu: 'teks' untuk watermark teks, atau unggah 'logo' "
            "untuk watermark logo biner."
        )
    try:
        cover = await _baca_unggahan(berkas)
        if ada_teks:
            bit = teks_ke_bit(teks.strip())
            mode, lebar_logo, tinggi_logo = "teks", 0, 0
        else:
            logo_pil = await _baca_unggahan(logo)
            bit, lebar_logo, tinggi_logo = logo_ke_bit(logo_pil)
            mode = "logo"
        async with KUNCI_BERAT:
            stego = await asyncio.to_thread(sisip_watermark, cover, bit, key, alpha)
    except ValueError as eronya:
        return _tanggapan_galat(str(eronya))
    psnr = hitung_psnr(cover, stego)
    return {
        "mode": mode,
        "jumlah_bit": len(bit),
        "lebar_logo": lebar_logo,
        "tinggi_logo": tinggi_logo,
        "psnr": psnr if psnr != float("inf") else "inf",
        "lebar": stego.width,
        "tinggi": stego.height,
        "stego_base64": _ke_base64(stego),
    }


@app.post("/api/watermark/extract")
async def ekstrak(
    citra_asli: UploadFile = File(..., description="Citra asli sebelum disisipi"),
    citra_input: UploadFile = File(..., description="Citra yang diekstrak (stego/serangan/tersangka)"),
    key: str = Form(..., description="Kunci yang dipakai saat penyisipan"),
    alpha: float = Form(ALPHA_DEFAULT, description="Alpha yang dipakai saat penyisipan"),
    jumlah_bit: int = Form(..., description="Panjang watermark dalam bit"),
    lebar_logo: int = Form(0, description="Lebar logo (0 bila mode teks)"),
    tinggi_logo: int = Form(0, description="Tinggi logo (0 bila mode teks)"),
    teks_asli: str = Form("", description="Teks asli pembanding (mode teks)"),
    logo_asli: UploadFile | None = File(None, description="Logo asli pembanding (mode logo)"),
):
    """Mengekstrak watermark secara non-blind; NC/BER bila pembanding diberi.

    Mode (a) uji serangan: citra_input = hasil /api/attack/* (seukuran asli).
    Mode (b) verifikasi: citra_input = citra tersangka dari luar sistem.
    """
    try:
        asli = await _baca_unggahan(citra_asli)
        uji = await _baca_unggahan(citra_input)
        async with KUNCI_BERAT:
            bit_hasil = await asyncio.to_thread(
                ekstrak_watermark, asli, uji, key, jumlah_bit, alpha)
    except ValueError as eronya:
        return _tanggapan_galat(str(eronya))
    bit_acuan = None
    if teks_asli:
        try:
            bit_acuan = teks_ke_bit(teks_asli)
        except ValueError as eronya:
            return _tanggapan_galat(str(eronya))
    elif logo_asli is not None and logo_asli.filename:
        try:
            bit_acuan, _, _ = logo_ke_bit(await _baca_unggahan(logo_asli))
        except ValueError as eronya:
            return _tanggapan_galat(str(eronya))
    return _tanggapan_ekstrak(bit_hasil, lebar_logo, tinggi_logo, bit_acuan)


def _tanggapan_ekstrak(bit_hasil: list, lebar_logo: int, tinggi_logo: int,
                       bit_acuan: list | None) -> dict | JSONResponse:
    """Menyusun respons ekstraksi (dipakai skema non-blind & blind)."""
    tanggapan: dict = {"jumlah_bit": len(bit_hasil)}
    if lebar_logo > 0 and tinggi_logo > 0:
        try:
            tanggapan["watermark_base64"] = _ke_base64(
                bit_ke_logo(bit_hasil, lebar_logo, tinggi_logo))
        except ValueError as eronya:
            return _tanggapan_galat(str(eronya))
    if len(bit_hasil) % 8 == 0:
        tanggapan["teks_hasil"] = bit_ke_teks(bit_hasil)
    if bit_acuan is not None:
        if len(bit_acuan) != len(bit_hasil):
            return _tanggapan_galat(
                f"Panjang pembanding ({len(bit_acuan)} bit) tidak sama dengan "
                f"jumlah_bit ({len(bit_hasil)})."
            )
        nc = hitung_nc(bit_acuan, bit_hasil)
        ber = hitung_ber(bit_acuan, bit_hasil)
        tanggapan["nc"] = nc
        tanggapan["ber"] = ber
        tanggapan["status_kepemilikan"] = _status_kepemilikan(nc)
    return tanggapan


@app.post("/api/watermark/embed-blind")
async def sisip_blind(
    berkas: UploadFile = File(..., description="Citra cover"),
    key: str = Form(..., description="Kunci rahasia (tidak disimpan server)"),
    alpha: float = Form(ALPHA_DEFAULT, description="Kekuatan sisipan > 0"),
    teks: str = Form("", description="Teks watermark (isi salah satu: teks/logo)"),
    logo: UploadFile | None = File(None, description="Logo biner (opsional)"),
):
    """Menyisipkan watermark skema BLIND (terbaca tanpa citra asli) + PSNR.

    Skema terpisah dari /embed (tidak saling baca): bit = tanda selisih dua
    koefisien dalam blok yang sama. Cadangan bila citra asli hilang.
    """
    ada_teks = bool(teks and teks.strip())
    ada_logo = logo is not None and logo.filename
    if ada_teks == bool(ada_logo):
        return _tanggapan_galat(
            "Isi tepat satu: 'teks' untuk watermark teks, atau unggah 'logo' "
            "untuk watermark logo biner."
        )
    try:
        cover = await _baca_unggahan(berkas)
        if ada_teks:
            bit = teks_ke_bit(teks.strip())
            mode, lebar_logo, tinggi_logo = "teks", 0, 0
        else:
            logo_pil = await _baca_unggahan(logo)
            bit, lebar_logo, tinggi_logo = logo_ke_bit(logo_pil)
            mode = "logo"
        async with KUNCI_BERAT:
            stego = await asyncio.to_thread(sisip_watermark_blind, cover, bit, key, alpha)
    except ValueError as eronya:
        return _tanggapan_galat(str(eronya))
    psnr = hitung_psnr(cover, stego)
    return {
        "mode": mode,
        "skema": "blind",
        "jumlah_bit": len(bit),
        "lebar_logo": lebar_logo,
        "tinggi_logo": tinggi_logo,
        "psnr": psnr if psnr != float("inf") else "inf",
        "lebar": stego.width,
        "tinggi": stego.height,
        "stego_base64": _ke_base64(stego),
    }


@app.post("/api/watermark/extract-blind")
async def ekstrak_blind(
    citra_input: UploadFile = File(..., description="Citra yang diekstrak (tanpa perlu asli)"),
    key: str = Form(..., description="Kunci yang dipakai saat penyisipan"),
    jumlah_bit: int = Form(..., description="Panjang watermark dalam bit"),
    lebar_logo: int = Form(0, description="Lebar logo (0 bila mode teks)"),
    tinggi_logo: int = Form(0, description="Tinggi logo (0 bila mode teks)"),
    teks_asli: str = Form("", description="Teks asli pembanding (mode teks)"),
    logo_asli: UploadFile | None = File(None, description="Logo asli pembanding (mode logo)"),
):
    """Mengekstrak watermark skema BLIND tanpa citra asli + NC/BER pembanding."""
    try:
        uji = await _baca_unggahan(citra_input)
        async with KUNCI_BERAT:
            bit_hasil = await asyncio.to_thread(
                ekstrak_watermark_blind, uji, key, jumlah_bit)
    except ValueError as eronya:
        return _tanggapan_galat(str(eronya))
    bit_acuan = None
    if teks_asli:
        try:
            bit_acuan = teks_ke_bit(teks_asli)
        except ValueError as eronya:
            return _tanggapan_galat(str(eronya))
    elif logo_asli is not None and logo_asli.filename:
        try:
            bit_acuan, _, _ = logo_ke_bit(await _baca_unggahan(logo_asli))
        except ValueError as eronya:
            return _tanggapan_galat(str(eronya))
    return _tanggapan_ekstrak(bit_hasil, lebar_logo, tinggi_logo, bit_acuan)

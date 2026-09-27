"""main.py — Controller FastAPI: routing endpoint & integrasi UI.

Endpoint yang sudah hidup (slice uji serangan):
- GET  /                          -> halaman UI (frontend/index.html)
- POST /api/attack/jpeg           -> kompresi JPEG (kualitas 90/70/50) + PSNR
- POST /api/attack/manipulation   -> noise/crop/resize/kontras/gabungan + PSNR
- POST /api/attack/semua          -> seluruh paket serangan sekaligus + PSNR

Belum hidup (menunggu logika spread-spectrum di watermark_engine.py):
- /api/watermark/embed, /api/watermark/extract

Semua endpoint API mengembalikan JSON (konvensi proyek). Citra hasil
dikirim sebagai string base64 PNG agar mudah ditampilkan di <img>.
Komentar dan pesan error memakai Bahasa Indonesia.
"""

import base64
import io
from pathlib import Path

try:
    from backend.attacker import (
        kompresi_jpeg, serangan_noise_gaussian, serangan_crop_tengah,
        serangan_resize, serangan_kontras, serangan_q50_noise_crop,
        terapkan_semua_serangan_uji,
    )
    from backend.evaluator import hitung_psnr
except ImportError:  # pragma: no cover — dijalankan sebagai skrip langsung
    from attacker import (
        kompresi_jpeg, serangan_noise_gaussian, serangan_crop_tengah,
        serangan_resize, serangan_kontras, serangan_q50_noise_crop,
        terapkan_semua_serangan_uji,
    )
    from evaluator import hitung_psnr

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from PIL import Image

app = FastAPI(title="Aplikasi Watermarking DCT — Demo Uji Serangan")

DIREKTORI_DEPAN = Path(__file__).resolve().parent.parent / "frontend"


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
    """Membungkus satu hasil serangan ke dict JSON."""
    psnr = _psnr_adil(asli, hasil)
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
    proporsi_crop: float = Form(0.2, description="Fraksi luas crop 0..1"),
    skala_resize: float = Form(0.5, description="Skala resize 0..1"),
    faktor_kontras: float = Form(1.5, description="Faktor kontras > 0"),
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
            hasil = serangan_kontras(asli, faktor=faktor_kontras)
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
        paket = terapkan_semua_serangan_uji(asli, seed=seed)
    except ValueError as eronya:
        return _tanggapan_galat(str(eronya))
    return {
        "lebar_asli": asli.width,
        "tinggi_asli": asli.height,
        "hasil": [_bungkus_hasil(nama, asli, citra) for nama, citra in paket.items()],
    }


# Peluncur langsung: `python backend/main.py` (tanpa reload).
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000)

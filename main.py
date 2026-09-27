"""main.py — Peluncur aplikasi dari root (sesuai AI.md: `python main.py`).

Menjalankan server Uvicorn di http://127.0.0.1:8000 dengan aplikasi
FastAPI dari backend/main.py. Mode development: uvicorn main:app --reload.
"""

import uvicorn

from backend.main import app

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)

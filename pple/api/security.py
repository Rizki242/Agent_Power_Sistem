"""Lapisan keamanan HTTP untuk FastAPI (api_server.py + router /api/v2/*).

Dua hal yang diatur di sini:

1. CORS - default lama ``allow_origins=["*"]`` membuka seluruh endpoint ke
   halaman web mana pun. Sekarang defaultnya hanya origin pengembangan
   lokal, dan daftar produksi diambil dari ``PPLE_CORS_ORIGINS``.
2. API key opsional - bila ``PPLE_API_KEY`` diisi, semua request wajib
   membawa header ``X-API-Key`` (atau ``Authorization: Bearer <key>``).
   Bila kosong, server berjalan terbuka seperti sebelumnya supaya
   pemakaian lokal/Streamlit tidak berubah.

Modul ini sengaja tidak mengimpor Streamlit maupun business logic; ia
hanya membaca environment dan menyaring request.
"""

import hmac
import os
from typing import List, Optional

from fastapi import Request
from fastapi.responses import JSONResponse

API_KEY_ENV = "PPLE_API_KEY"
CORS_ORIGINS_ENV = "PPLE_CORS_ORIGINS"

API_KEY_HEADER = "X-API-Key"

# Origin yang dipakai saat pengembangan lokal: Vite (5173, plus 5174/5175
# yang otomatis dipakai Vite saat 5173 sedang dipakai proses lain),
# Streamlit (8501), dan FastAPI itu sendiri (8000) supaya Swagger /docs
# tetap bisa mencoba API.
DEFAULT_DEV_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost:5175",
    "http://127.0.0.1:5175",
    "http://localhost:8501",
    "http://127.0.0.1:8501",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]

# Endpoint yang tetap terbuka walau API key aktif: health check dipakai
# load balancer/monitoring yang biasanya tidak bisa mengirim header.
PUBLIC_PATHS = frozenset({"/api/health"})


def resolve_api_key() -> Optional[str]:
    """API key yang sedang aktif, atau None bila autentikasi dimatikan."""
    key = os.environ.get(API_KEY_ENV, "").strip()
    return key or None


def auth_enabled() -> bool:
    return resolve_api_key() is not None


def resolve_cors_origins() -> List[str]:
    """Daftar origin dari ``PPLE_CORS_ORIGINS`` (dipisah koma).

    Kosong -> hanya origin pengembangan lokal. Nilai ``*`` tetap dihormati
    bila memang disetel secara sadar.
    """
    raw = os.environ.get(CORS_ORIGINS_ENV, "").strip()
    if not raw:
        return list(DEFAULT_DEV_ORIGINS)
    origins = [item.strip().rstrip("/") for item in raw.split(",")]
    return [item for item in origins if item] or list(DEFAULT_DEV_ORIGINS)


def cors_allow_credentials(origins: List[str]) -> bool:
    """Cookie/credential tidak boleh digabung dengan origin wildcard.

    Browser menolak ``Access-Control-Allow-Origin: *`` bersama
    ``allow_credentials=True``, jadi kombinasi itu justru membuat request
    kredensial gagal - bukan sekadar longgar.
    """
    return "*" not in origins


def extract_request_key(request: Request) -> Optional[str]:
    """Ambil API key dari header X-API-Key atau Authorization: Bearer."""
    header_key = request.headers.get(API_KEY_HEADER)
    if header_key and header_key.strip():
        return header_key.strip()

    authorization = request.headers.get("Authorization", "")
    scheme, _, value = authorization.partition(" ")
    if scheme.lower() == "bearer" and value.strip():
        return value.strip()
    return None


def is_public_path(path: str) -> bool:
    return path in PUBLIC_PATHS


async def api_key_middleware(request: Request, call_next):
    """Tolak request tanpa API key yang sah saat PPLE_API_KEY diisi.

    Dipasang sebagai middleware (bukan Depends per-route) supaya endpoint
    baru otomatis ikut terlindungi tanpa perlu diingat satu per satu.
    """
    expected = resolve_api_key()

    # Preflight CORS tidak pernah membawa header custom; penyaringan origin
    # sudah ditangani CORSMiddleware.
    if expected is None or request.method == "OPTIONS" or is_public_path(request.url.path):
        return await call_next(request)

    provided = extract_request_key(request)
    if provided is None or not hmac.compare_digest(provided, expected):
        return JSONResponse(
            status_code=401,
            content={
                "detail": (
                    "API key tidak valid atau tidak disertakan. "
                    f"Kirim header {API_KEY_HEADER}: <key>."
                )
            },
        )

    return await call_next(request)


def startup_warning() -> Optional[str]:
    """Peringatan yang layak dicetak saat server start, bila ada."""
    if auth_enabled():
        return None
    return (
        f"[PPLE] {API_KEY_ENV} kosong: API berjalan TANPA autentikasi. "
        "Aman untuk localhost, jangan dipakai untuk deployment terbuka."
    )

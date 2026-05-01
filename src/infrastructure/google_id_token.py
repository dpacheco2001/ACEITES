"""Verificación del ID token de Google Identity Services."""
from __future__ import annotations

from typing import Any, Dict

from google.auth.transport import requests
from google.oauth2 import id_token

from src.infrastructure.settings import (
    GOOGLE_CLIENT_ID,
    GOOGLE_ID_TOKEN_CLOCK_SKEW_SECONDS,
)


def verify_google_id_token(raw_token: str) -> Dict[str, Any]:
    if not GOOGLE_CLIENT_ID:
        raise RuntimeError("GOOGLE_CLIENT_ID no está configurado")
    request = requests.Request()
    info = id_token.verify_oauth2_token(
        raw_token,
        request,
        GOOGLE_CLIENT_ID,
        clock_skew_in_seconds=GOOGLE_ID_TOKEN_CLOCK_SKEW_SECONDS,
    )
    return info  # type: ignore[no-any-return]

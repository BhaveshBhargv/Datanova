"""Field-level encryption for secrets at rest (e.g. DB connection passwords)."""
import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet

from app.core.config import settings


@lru_cache
def _fernet() -> Fernet:
    if settings.FIELD_ENCRYPTION_KEY:
        key = settings.FIELD_ENCRYPTION_KEY.encode()
    else:
        # Derive a valid 32-byte urlsafe-base64 Fernet key from SECRET_KEY.
        digest = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt(plaintext: str) -> bytes:
    return _fernet().encrypt(plaintext.encode())


def decrypt(token: bytes) -> str:
    return _fernet().decrypt(bytes(token)).decode()

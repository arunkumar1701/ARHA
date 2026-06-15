from __future__ import annotations

import base64
from hashlib import sha256

from cryptography.fernet import Fernet

from .config import settings


class CryptoBox:
    def __init__(self, secret: str) -> None:
        key = base64.urlsafe_b64encode(sha256(secret.encode("utf-8")).digest())
        self._fernet = Fernet(key)

    def encrypt(self, value: str | None) -> str | None:
        if value is None:
            return None
        return self._fernet.encrypt(value.encode("utf-8")).decode("ascii")

    def decrypt(self, value: str | None) -> str | None:
        if value is None:
            return None
        return self._fernet.decrypt(value.encode("ascii")).decode("utf-8")

    @staticmethod
    def digest(value: bytes) -> str:
        return sha256(value).hexdigest()


crypto_box = CryptoBox(f"{settings.secret_key}:{settings.arha_passphrase}")

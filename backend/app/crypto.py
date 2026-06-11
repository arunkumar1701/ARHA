import base64
import os
from hashlib import sha256

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from .config import PASSPHRASE, SALT_PATH, ensure_data_dirs


class CryptoBox:
    def __init__(self) -> None:
        ensure_data_dirs()
        if SALT_PATH.exists():
            salt = SALT_PATH.read_bytes()
        else:
            salt = os.urandom(16)
            SALT_PATH.write_bytes(salt)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=390000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(PASSPHRASE.encode("utf-8")))
        self._fernet = Fernet(key)

    def encrypt(self, value: str | None) -> bytes | None:
        if value is None:
            return None
        return self._fernet.encrypt(value.encode("utf-8"))

    def decrypt(self, value: bytes | None) -> str | None:
        if value is None:
            return None
        return self._fernet.decrypt(value).decode("utf-8")

    @staticmethod
    def digest(value: bytes) -> str:
        return sha256(value).hexdigest()


crypto_box = CryptoBox()

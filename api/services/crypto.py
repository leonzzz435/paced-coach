from functools import lru_cache

from cryptography.fernet import Fernet

from api.config import get_settings


class CryptoService:
    def __init__(self):
        settings = get_settings()
        if not settings.fernet_key:
            raise ValueError("FERNET_KEY environment variable is not set")
        self._fernet = Fernet(settings.fernet_key.encode())

    def encrypt(self, plaintext: str) -> bytes:
        return self._fernet.encrypt(plaintext.encode())

    def decrypt(self, ciphertext: bytes) -> str:
        return self._fernet.decrypt(ciphertext).decode()


@lru_cache
def get_crypto_service() -> CryptoService:
    return CryptoService()

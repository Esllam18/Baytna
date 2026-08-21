from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet

from app.core.config import Settings


class IntegrationSecretBox:
    def __init__(self, settings: Settings) -> None:
        derived = hashlib.sha256(
            settings.integration_encryption_secret.encode("utf-8")
        ).digest()
        key = base64.urlsafe_b64encode(derived)
        self.fernet = Fernet(key)

    def encrypt(self, value: str) -> str:
        return self.fernet.encrypt(value.encode("utf-8")).decode("ascii")

    def decrypt(self, value: str) -> str:
        return self.fernet.decrypt(value.encode("ascii")).decode("utf-8")

    def hash(self, value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

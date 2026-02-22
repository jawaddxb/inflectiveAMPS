"""
Vault Key Store — AES-256-GCM encrypted secret management
"""
import os
import json
import base64
from typing import Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
import secrets

SECRETS_PATH = os.environ.get("VAULT_SECRETS_PATH", "/vault/secrets")

class KeyStore:
    def __init__(self, master_password: str, secrets_path: str = SECRETS_PATH):
        self.secrets_path = secrets_path
        os.makedirs(secrets_path, exist_ok=True)
        self._key = self._derive_key(master_password)

    def _derive_key(self, password: str) -> bytes:
        """Derive a 256-bit key from master password using PBKDF2"""
        salt_path = os.path.join(self.secrets_path, ".salt")
        if os.path.exists(salt_path):
            with open(salt_path, "rb") as f:
                salt = f.read()
        else:
            salt = secrets.token_bytes(32)
            with open(salt_path, "wb") as f:
                f.write(salt)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=600_000,
        )
        return kdf.derive(password.encode())

    def _secret_path(self, name: str) -> str:
        # sanitise name to safe filename
        safe = "".join(c for c in name if c.isalnum() or c in "-_.").lower()
        return os.path.join(self.secrets_path, safe + ".enc")

    def store(self, name: str, value: str) -> None:
        """Encrypt and store a secret"""
        aesgcm = AESGCM(self._key)
        nonce = secrets.token_bytes(12)
        ct = aesgcm.encrypt(nonce, value.encode(), name.encode())
        payload = json.dumps({
            "nonce": base64.b64encode(nonce).decode(),
            "ciphertext": base64.b64encode(ct).decode(),
            "name": name
        })
        with open(self._secret_path(name), "w") as f:
            f.write(payload)

    def retrieve(self, name: str) -> Optional[str]:
        """Decrypt and return a secret value"""
        path = self._secret_path(name)
        if not os.path.exists(path):
            return None
        with open(path) as f:
            payload = json.load(f)
        aesgcm = AESGCM(self._key)
        nonce = base64.b64decode(payload["nonce"])
        ct = base64.b64decode(payload["ciphertext"])
        try:
            return aesgcm.decrypt(nonce, ct, name.encode()).decode()
        except Exception:
            return None

    def delete(self, name: str) -> bool:
        path = self._secret_path(name)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    def list_secrets(self) -> list:
        """Return names of stored secrets (not values)"""
        names = []
        for f in os.listdir(self.secrets_path):
            if f.endswith(".enc"):
                names.append(f[:-4])  # strip .enc
        return sorted(names)

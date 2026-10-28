"""Local encryption for temporary credentials and optional provider refresh tokens."""

from pathlib import Path

from cryptography.fernet import Fernet

from .private_file import write_private


class Vault:
    def __init__(self, directory):
        path = Path(directory) / "vault.key"
        if not path.exists():
            try:
                write_private(path, Fernet.generate_key())
            except FileExistsError:
                pass
        self.cipher = Fernet(path.read_bytes())

    def encrypt(self, value):
        return self.cipher.encrypt(value.encode()).decode()

    def decrypt(self, value):
        return self.cipher.decrypt(value.encode()).decode()

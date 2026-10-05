"""Local encryption for temporary credentials and optional provider refresh tokens."""

import os
from pathlib import Path

from cryptography.fernet import Fernet


class Vault:
    def __init__(self, directory):
        path = Path(directory) / "vault.key"
        if not path.exists():
            try:
                with path.open("xb") as stream:
                    os.chmod(path, 0o600)
                    stream.write(Fernet.generate_key())
            except FileExistsError:
                pass
        self.cipher = Fernet(path.read_bytes())

    def encrypt(self, value):
        return self.cipher.encrypt(value.encode()).decode()

    def decrypt(self, value):
        return self.cipher.decrypt(value.encode()).decode()

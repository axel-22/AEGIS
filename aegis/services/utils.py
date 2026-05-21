# AEGIS - NowBlackout ENSIBS 2025
# Last modified: 2026-02-03
# Utils - Utility functions for AEGIS services
from cryptography.fernet import Fernet

def generate_fernet_key() -> str:
    return Fernet.generate_key().decode()

def encrypt_secret(secret_text: str, fernet: Fernet) -> str:
    encrypted_bytes = fernet.encrypt(secret_text.encode('utf-8'))
    return encrypted_bytes.decode('utf-8')
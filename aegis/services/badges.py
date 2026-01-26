# AEGIS - NowBlackout ENSIBS 2025
# Last modified: 2025-15-11
# Badges Service - Manage all badge-related operations

import base64,  os, secrets, hashlib, sys, json, datetime, os
from pathlib import Path
from dotenv import load_dotenv

import pyotp
from cryptography.fernet import Fernet

import aegis.core._database as db
from aegis.core._models import BADGES 

from aegis.services.nfc_reader import NFCReader

db.set_debug(True)

dotenv_path = os.path.join(os.path.dirname(__file__), '..', 'secrets', 'secrets.env')
load_dotenv(dotenv_path)

def generate_totp_secret() -> str:
    secret = pyotp.random_base32()
    return secret

def encrypt_totp_secret(secret_text: str, fernet: Fernet) -> str:
    encrypted_bytes = fernet.encrypt(secret_text.encode('utf-8'))
    return encrypted_bytes.decode('utf-8')

def decrypt_totp_secret(token_str: str, fernet: Fernet) -> str:
    decrypted_bytes = fernet.decrypt(token_str.encode('utf-8'))
    return decrypted_bytes.decode('utf-8')

def attach_badge_to_user(badge_id: int, user_id: int):
    db.assign_badge_to_user(badge_id, user_id)

def generate_fernet_key() -> str:
    return Fernet.generate_key().decode()

def get_header_id_from_nfc() -> str:
    nfc_reader = NFCReader()
    header_id = nfc_reader.read()
    if header_id is None:
        raise RuntimeError("Lecture NF échouée : aucun badge détecté dans le délai imparti Veuiller réessayer.")
    return header_id


def create_badge(username: str, secret: str, header_id: str) -> BADGES:
    today = datetime.datetime.now().date()
    two_years_later = datetime.datetime.now().date() + datetime.timedelta(days=730)
    print(f"Issued at: {today}, Expires at: {two_years_later}")
    totp = pyotp.TOTP(secret)
    fernet_key = os.getenv("FERNET_KEY")

    if not fernet_key:
        raise ValueError("FERNET_KEY non défini dans .env")

    fernet = Fernet(fernet_key)
    encrypted_secret = encrypt_totp_secret(secret, fernet)
    
    b = BADGES(
        the_user=None,
        header_id=header_id,
        issued_at=today,
        expires_at=two_years_later,
        is_revoked=False,
        totp_secret=encrypted_secret,
        revoked_at=None,
        revoked_reason=""
    )

    badge = db.insert_badge(b)

    return badge

if __name__ == "__main__":
    print("Création d'un badge de test pour l'utilisateur 'testuser'")
    print(get_header_id_from_nfc())
    # if totp.verify(user_code):
    #     print("Code valide !")
    # else:
    #     print("Code invalide.")
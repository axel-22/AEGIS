# AEGIS - NowBlackout ENSIBS 2025
# Last modified: 2025-15-11
# Badges Service - Manage all badge-related operations

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature, decode_dss_signature
from cryptography.exceptions import InvalidSignature, InvalidKey
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import Fernet

import pyotp
import uuid

import base64,  os, secrets, hashlib, sys, json, datetime

from pathlib import Path

import aegis.core._database as db
from aegis.core._models import BADGES 
import aegis.services.ac as ac

db.set_debug(True)

def is_keys_existing(username: str):
    USR_DIR = Path("badges/pem/usr")
    USR_PRIV_PATH = USR_DIR.joinpath(f"{username}_private.pem")

    if USR_PRIV_PATH.exists():
        raise FileExistsError("Keypair already exists for this user")
    return False

def generate_totp_secret() -> str:
    secret = pyotp.random_base32()
    return secret

def create_badge(username: str, secret: str, ac_passphrase: str) -> BADGES:
    USR_DIR = Path("badges/pem/usr")
    USR_PRIV_PATH = USR_DIR.joinpath(f"{username}_private.pem")

    header_id = str(uuid.uuid4())
    today = datetime.datetime.now().date()
    two_years_later = datetime.datetime.now().date() + datetime.timedelta(days=730)
    print(f"Issued at: {today}, Expires at: {two_years_later}")
    totp = pyotp.TOTP(secret)
    jpub= gen_keys(username, totp, header_id, USR_PRIV_PATH)
    try:

        j = ac.ac_sign_user_key(jpub, ac_passphrase)

    except InvalidKey as e:
        raise Exception("Invalid passphrase for AC private key")

    salt = os.urandom(16)
    key = derive_key_from_passphrase(ac_passphrase, salt)
    cipher = Fernet(key)
    encrypted_secret = cipher.encrypt(secret.encode())

    b = BADGES(
        the_user=None,
        header_id=header_id,
        issued_at=today,
        expires_at=two_years_later,
        json_integrity=hashlib.sha256(json.dumps(j).encode()).hexdigest(),
        json_path=f"badges/json/{username}_badge.json",
        is_revoked=False,
        totp_secret=encrypted_secret,
        totp_salt=base64.b64encode(salt).decode('ascii'),
        revoked_at=None,
        revoked_reason=""
    )

    badge = db.insert_badge(b)

    with open(f"badges/json/{username}_badge.json", 'w') as f:
        json.dump(j, f, indent=2)

    return badge


def gen_keys(username: str, totp: pyotp.TOTP, header_id: str, USR_PRIV_PATH: Path):
    priv = ec.generate_private_key(ec.SECP256R1())
    pub = priv.public_key()
    # store private key
    enc = serialization.BestAvailableEncryption(totp.now().encode())
    priv_pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=enc
    )
    pub_der = pub.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    pub_b64 = base64.b64encode(pub_der).decode('ascii')
    try:
        with open(USR_PRIV_PATH, "wb") as f:
            f.write(priv_pem)
        j = {}
        j['uuid'] = header_id
        j['pub'] = pub_b64
    except Exception as e:
        print(f"Erreur lors de l'écriture de la clé privée : {e}")
        raise e
    return j


def attach_badge_to_user(badge_id: int, user_id: int):
    db.assign_badge_to_user(badge_id, user_id)


def derive_key_from_passphrase(ac_passphrase: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=390000,
    )
    return base64.urlsafe_b64encode(kdf.derive(ac_passphrase.encode()))

if __name__ == "__main__":
    print("Création d'un badge de test pour l'utilisateur 'testuser'")
    # if totp.verify(user_code):
    #     print("Code valide !")
    # else:
    #     print("Code invalide.")
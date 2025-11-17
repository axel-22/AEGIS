# AEGIS - NowBlackout ENSIBS 2025
# Last modified: 2025-16-11
# AC Service - Manage all Access Control operations

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature, decode_dss_signature
from cryptography.exceptions import InvalidSignature, InvalidKey

import base64, os, sqlite3, datetime, secrets, hashlib
from pathlib import Path


AC_DIR = Path("badges/pem/ac")

AC_PRIV_PATH = AC_DIR.joinpath("ac_private_key.pem")
AC_PUB_PATH = AC_DIR.joinpath("ac_public_key.pem")


def is_ac_keys_existing():
    if AC_PRIV_PATH.exists() and AC_PUB_PATH.exists():
        raise FileExistsError("AC keypair already exists")
    return False

def generate_ac_keys(passphrase):
    """Generate AC ECDSA keypair."""
    priv = ec.generate_private_key(ec.SECP256R1())
    pub = priv.public_key()
    # store private key
    enc = serialization.BestAvailableEncryption(passphrase.encode())
    priv_pem = priv.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=enc
    )
    pub_pem = pub.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    with open(AC_PRIV_PATH, "wb") as f:
        f.write(priv_pem)
    with open(AC_PUB_PATH, "wb") as f:
        f.write(pub_pem)
    return priv, pub

def ac_sign_user_key(jpub: dict, passphrase: str) -> dict:
    """Sign the user's public key with the AC private key."""
    pub_b64 = jpub['pub']
    pub_bytes = base64.b64decode(pub_b64)

    with open(AC_PRIV_PATH, "rb") as f:
        ac_priv_pem = f.read()

    try:
        ac_private_key = serialization.load_pem_private_key(
            ac_priv_pem,
            password=passphrase.encode(),
        )
    except InvalidKey as e:
        raise InvalidKey("Invalid passphrase for AC private key")

    signature = ac_private_key.sign(
        pub_bytes,
        ec.ECDSA(hashes.SHA256())
    )

    jpub['cert'] = base64.b64encode(signature).decode('ascii')

    return jpub

def verify_bytes_ecdsa(pub, data_bytes: bytes, compact_b64: str) -> bool:
    try:
        compact = base64.b64decode(compact_b64)
        if len(compact) != 64:
            return False
        r = int.from_bytes(compact[:32], "big")
        s = int.from_bytes(compact[32:], "big")
        der = encode_dss_signature(r, s)
        pub.verify(der, data_bytes, ec.ECDSA(hashes.SHA256()))
        return True
    except InvalidSignature:
        return False
    except Exception as e:
        print("verify exception:", e)
        return False



if __name__ == "__main__":
    try:
        demo_flow()
    except Exception as e:
        print("Error during demo:", e)


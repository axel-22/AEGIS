# AEGIS - NowBlackout ENSIBS 2025
# Last modified: 2025-15-11
# Badges Service - Manage all badge-related operations

import base64, os, secrets, hashlib, sys, json, os
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

import pyotp
from cryptography.fernet import Fernet
from hashlib import sha256

import aegis.core._database as db
import aegis.services.utils as utils

from aegis.core._models import BADGES, USERS
from aegis.services.nfc_reader import NFCReader


db.set_debug(True)

dotenv_path = os.path.join(os.path.dirname(__file__), '..', 'secrets', 'totp.env')
load_dotenv(dotenv_path)

def generate_totp_secret() -> str:
    secret = pyotp.random_base32()
    return secret

def decrypt_totp_secret(token_str: str, fernet: Fernet) -> str:
    decrypted_bytes = fernet.decrypt(token_str.encode('utf-8'))
    return decrypted_bytes.decode('utf-8')

def attach_badge_to_user(badge_id: int, user_id: int):
    db.assign_badge_to_user(badge_id, user_id)


def get_header_id_from_nfc() -> str:
    nfc_reader = NFCReader()
    header_id = nfc_reader.read()
    if header_id is None:
        raise RuntimeError("Lecture NF échouée : aucun badge détecté dans le délai imparti Veuiller réessayer.")
    return header_id


def create_badge(username: str, secret: str, header_id: str) -> BADGES:
    today = datetime.now().date()
    two_years_later = datetime.now().date() + timedelta(days=730)
    print(f"Issued at: {today}, Expires at: {two_years_later}")
    totp = pyotp.TOTP(secret)
    fernet_totp_key = os.getenv("FERNET_TOTP_KEY")

    if not fernet_totp_key:
        raise ValueError("FERNET_TOTP_KEY non défini dans totp.env")

    fernet = Fernet(fernet_totp_key)
    encrypted_secret = utils.encrypt_secret(secret, fernet)
    header_hash = sha256(header_id.encode('utf-8')).hexdigest() 

    try:
        existing_badge = db.select_badge_by_header_id(header_hash)
        if existing_badge:
            raise ValueError("Ce badge NFC est déjà enregistré dans le système.")
    except Exception as e:
        raise e
        return

    b = BADGES(
        the_user=None,
        header_id=header_hash,
        issued_at=today,
        expires_at=two_years_later,
        is_revoked=False,
        totp_secret=encrypted_secret,
        revoked_at=None,
        revoked_reason="",
        updated_at=None
    )

    badge = db.insert_badge(b)

    return badge

def is_badge_allready_assigned(header_id: str) -> bool:
    header_hash = sha256(header_id.encode('utf-8')).hexdigest()
    badge = db.select_badge_by_header_id(header_hash)
    if badge and badge.the_user is not None:
        u = users.get_user_by_id(badge.the_user)
        db.drop_user(u.user_id)
        return True
    return False

def list_all_badges() -> list[tuple[BADGES, str]]:
    try:
        badges = db.select_all_badges()
    except Exception as e:
        raise e
    return badges

def get_badge_by_id(badge_id: int) -> BADGES:
    try:
        badge = db.select_badge_by_id(badge_id)
    except Exception as e:
        raise e
    return badge

def edit_badge(badge_id: int, badge_data: dict) -> BADGES:
    session = db.get_session()

    try:
        badge = session.query(BADGES).filter(BADGES.badge_id == badge_id).first()

        if not badge:
            raise ValueError(f"Badge {badge_id} non trouvé")

        # Mise à jour des champs autorisés
        for field, value in badge_data.items():
            if hasattr(badge, field):
                setattr(badge, field, value)

        badge.updated_at = datetime.utcnow()

        session.commit()
        session.refresh(badge)
        return badge

    except Exception as e:
        session.rollback()
        raise Exception(f"Erreur lors de la modification du badge : {e}")

    finally:
        session.close()

def list_badges(is_revoked: bool) -> list[tuple[BADGES, str]]:
    try:
        badges = db.select_badges_by_revocation_status(is_revoked)
    except Exception as e:
        raise e
    return badges

if __name__ == "__main__":
    print("Création d'un badge de test pour l'utilisateur 'testuser'")
    print(get_header_id_from_nfc())
    # if totp.verify(user_code):
    #     print("Code valide !")
    # else:
    #     print("Code invalide.")
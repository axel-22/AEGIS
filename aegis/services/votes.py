# AEGIS - NowBlackout ENSIBS 2025
# Last modified: 2026-03-02
# Users Service - Manage all votes 

from datetime import datetime
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from cryptography.fernet import Fernet
import os

import aegis.core._database as db
from aegis.core._models import USERS, BADGES, ENVELOPES, ANSWERS, VOTES, NONCES
from aegis.services import utils

dotenv_path = os.path.join(os.path.dirname(__file__), '..', 'secrets', 'answer.env')
load_dotenv(dotenv_path)


def create_vote(vote_data: dict) -> 'VOTES':
    session = db.get_session()

    try:
        now = datetime.utcnow()
        if vote_data.get("question") is None or len(vote_data.get("question")) >=500:
            session.rollback()
            raise ValueError("La question du vote doit contenir entre 1 et 500 caractères.")
        
        if vote_data.get("description_text") and len(vote_data.get("description_text")) > 1000:
            session.rollback()
            raise ValueError("La description du vote ne peut pas dépasser 1000 caractères.")

        if vote_data.get("vote_type") not in ["majorité", "unanimité","minimum_requis"]:
            session.rollback()
            raise ValueError("Type de vote invalide. Choisissez parmi : unanimité, majorité, minimum_requis.")

        if vote_data.get("vote_mode") not in ["auditable", "confidentiel"]:
            session.rollback()
            raise ValueError("Mode de vote invalide. Choisissez parmi : auditable, confidentiel.")
        
        if vote_data.get("expiration_date") < datetime.date.today():
            session.rollback()
            raise ValueError("La date d'expiration doit être une date future.")

        vote = VOTES(
            question=vote_data.get("question"),
            description_text=vote_data.get("description_text"),
            creator_user_id=vote_data.get("creator_user_id"),
            vote_type=vote_data.get("vote_type"),
            vote_mode=vote_data.get("vote_mode"),
            is_boolean=vote_data.get("is_boolean"),
            k_required=vote_data.get("k_required"),
            vote_status="open",
            is_active=True,
            opened_at=now,
            timeout_at=vote_data.get("expiration_date"),
            closed_at=None
        )
        session.commit()
        return vote

    except ValueError as ve:
        session.rollback()
        raise ve
    except Exception as e:
        session.rollback()
        raise Exception(f"Erreur lors de la création du vote : {e}")
    finally:
        session.close()

def add_answers_to_vote(vote_id: int, anwsers: list[str]):
    session = db.get_session()
    try:
        vote = session.get(VOTES, vote_id)
        if not vote:
            raise ValueError("Vote non trouvé.")

        for answer_text in anwsers:
            if len(answer_text) == 0 or len(answer_text) > 500:
                raise ValueError("Chaque réponse doit contenir entre 1 et 500 caractères.")
            cipher = answer_text
            if vote.vote_mode == "confidentiel":
                fernet = Fernet(fernet_totp_key)
                cipher = utils.encrypt_secret(answer_text, fernet)
            answer = ANSWERS(
                the_vote=vote.vote_id,
                answer_text=cipher
            )
            session.add(answer)

        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


# =========================
# LIST NONCES FOR A VOTE (debug / admin)
# =========================
def list_nonces():
    session = db.get_session()
    try:
        return session.query(NONCES).all()
    finally:
        session.close()


# =========================
# CAST VOTE WITH NONCE
# =========================
def cast_vote(nonce_value: str, vote_id: int, vote_choice: int):
    session = db.get_session()

    try:
        nonce = (
            session.query(NONCES)
            .filter(NONCES.nonce == nonce_value)
            .one_or_none()
        )

        if not nonce:
            raise ValueError("Nonce invalide")

        if nonce.used:
            raise ValueError("Nonce déjà utilisé")

        vote = session.get(VOTES, vote_id)
        if not vote or not vote.is_active:
            raise ValueError("Vote invalide ou fermé")

        envelope = ENVELOPES(
            the_vote=vote.vote_id,
            the_user=None,              # volontairement NULL
            the_badge=None,             # plus tard
            the_date=datetime.utcnow(),
            vote_choice=vote_choice,
            user_signature_valid=False, # plus tard
            entry_hash="TEMP",
            current_hash="TEMP",
            siem_loged=False,
        )

        session.add(envelope)

        nonce.used = True
        nonce.used_at = datetime.utcnow()

        session.commit()
        return envelope

    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

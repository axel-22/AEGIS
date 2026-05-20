# AEGIS - NowBlackout ENSIBS 2025
# Last modified: 2026-03-02
# Votes Service - Manage all votes

from datetime import datetime
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from cryptography.fernet import Fernet
import hashlib
import secrets
import os

import aegis.core._database as db
from aegis.core._models import USERS, BADGES, ENVELOPES, ANSWERS, VOTES, NONCES
from aegis.services import utils
from aegis.core._logger import get_logger

log = get_logger("votes")

dotenv_path = os.path.join(os.path.dirname(__file__), '..', 'secrets', 'answer.env')
load_dotenv(dotenv_path)


def create_vote(vote_data: dict) -> 'VOTES':
    session = db.get_session()

    try:
        now = datetime.now().date()
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
        
        if vote_data.get("expiration_date") < now:
            session.rollback()
            raise ValueError("La date d'expiration doit être une date future.")

        if vote_data.get("is_boolean") not in [True, False]:
            session.rollback()
            raise ValueError("La valeur de 'is_boolean' doit être True ou False, Veuillez entréer 'oui' ou 'non'.")

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
        session.add(vote)
        session.commit()
        session.refresh(vote)

        log.info(f"Vote #{vote.vote_id} créé — '{vote.question[:60]}' ({vote.vote_type}/{vote.vote_mode})")
        return vote

    except ValueError as ve:
        log.error(f"Création du vote refusée : {ve}")
        session.rollback()
        raise ve
    except Exception as e:
        log.error(f"Erreur inattendue lors de la création du vote : {e}")
        session.rollback()
        raise Exception(f"Erreur lors de la création du vote : {e}")
    finally:
        session.close()


# =========================
# ÉDITION D'UN VOTE
# =========================

def edit_vote(vote_id: int, vote_data: dict) -> 'VOTES':
    """
    Édite un vote existant.
    Refusé si le vote est fermé ou si des bulletins ont déjà été déposés.
    Champs éditables : question, description_text, vote_type, vote_mode,
                       k_required, timeout_at (date d'expiration).
    """
    EDITABLE = {"question", "description_text", "vote_type", "vote_mode",
                "k_required", "timeout_at"}

    session = db.get_session()
    try:
        vote = session.get(VOTES, vote_id)
        if not vote:
            raise ValueError(f"Vote #{vote_id} non trouvé.")
        if vote.vote_status != "open":
            raise ValueError(f"Vote #{vote_id} déjà '{vote.vote_status}' — édition impossible.")

        envelope_count = (
            session.query(ENVELOPES)
            .filter(ENVELOPES.the_vote == vote_id)
            .count()
        )
        if envelope_count > 0:
            raise ValueError(
                f"Vote #{vote_id} : {envelope_count} bulletin(s) déjà déposé(s) — "
                "édition impossible pour garantir l'intégrité."
            )

        # Validation puis application des champs
        for field, value in vote_data.items():
            if field not in EDITABLE:
                continue
            if field == "question":
                if not value or len(value) > 500:
                    raise ValueError("La question doit contenir entre 1 et 500 caractères.")
            if field == "vote_type" and value not in ["majorité", "unanimité", "minimum_requis"]:
                raise ValueError("Type de vote invalide.")
            if field == "vote_mode" and value not in ["auditable", "confidentiel"]:
                raise ValueError("Mode de vote invalide.")
            setattr(vote, field, value)

        session.commit()
        session.refresh(vote)
        log.info(f"Vote #{vote_id} modifié — champs : {list(vote_data.keys())}")
        return vote

    except Exception:
        session.rollback()
        raise
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
            answer = ANSWERS(
                the_vote=vote.vote_id,
                answer_text=answer_text
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
# AFFECTE VOTE TO USERS WITH RIGHT TO VOTE
# =========================
def assign_vote_to_user(vote_id: int, user_id: int):
    session = db.get_session()
    try:
        vote = session.get(VOTES, vote_id)
        user = session.get(USERS, user_id)

        if not vote:
            raise ValueError("Vote non trouvé.")
        if not user:
            raise ValueError("Utilisateur non trouvé.")

        if not vote.is_active:
            raise ValueError("Vote non actif.")

        # 🔒 Vérifier que l'utilisateur n'a pas déjà un nonce pour ce vote
        existing_nonce = session.query(NONCES).filter(
            NONCES.the_user == user_id,
            NONCES.the_vote == vote_id,
            NONCES.used == False,
        ).first()

        if existing_nonce:
            raise ValueError(f"L'utilisateur {user_id} est déjà assigné à ce vote.")

        # 🔐 Génération d’un nonce sécurisé
        nonce_value = secrets.token_urlsafe(32)

        new_nonce = NONCES(
            nonce=nonce_value,
            used=False,
            the_user=user_id,
            issued_at=datetime.utcnow(),
            the_vote=vote_id,     # 👈 IMPORTANT
            the_envelope=None
        )

        session.add(new_nonce)
        session.commit()
        log.info(f"Vote #{vote_id} assigné à user_id={user_id}")
        return new_nonce

    except Exception as e:
        log.error(f"Assignation vote #{vote_id} → user_id={user_id} échouée : {e}")
        session.rollback()
        raise e
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
            raise ValueError("Nonce invalide.")
        if nonce.used:
            raise ValueError("Nonce déjà utilisé : vous avez déjà voté.")
        if nonce.the_vote != vote_id:
            raise ValueError("Nonce non associé à ce vote.")

        vote = session.get(VOTES, vote_id)
        if not vote or not vote.is_active:
            raise ValueError("Vote invalide ou inactif.")
        if vote.vote_status != "open":
            raise ValueError("Ce vote n'est pas ouvert.")

        # Vérifier que le choix correspond à une réponse valide
        valid_answer = (
            session.query(ANSWERS)
            .filter(ANSWERS.the_vote == vote_id, ANSWERS.answer_id == vote_choice)
            .first()
        )
        if not valid_answer:
            raise ValueError("Choix de réponse invalide.")

        # Chaîne de hash : récupère le hash de la dernière enveloppe du vote
        last_envelope = (
            session.query(ENVELOPES)
            .filter(ENVELOPES.the_vote == vote_id)
            .order_by(ENVELOPES.envelope_id.desc())
            .first()
        )
        prev_hash = last_envelope.current_hash if last_envelope else "GENESIS"

        now = datetime.utcnow()
        raw = f"{prev_hash}{vote_id}{vote_choice}{now.isoformat()}"
        current_hash = hashlib.sha256(raw.encode()).hexdigest()

        # Mode auditable : lier le votant à l'enveloppe
        # Mode confidentiel : the_user reste NULL (anonymat)
        the_user = nonce.the_user if vote.vote_mode == "auditable" else None

        envelope = ENVELOPES(
            the_vote=vote.vote_id,
            the_user=the_user,
            the_badge=None,
            the_date=now,
            vote_choice=vote_choice,
            prev_hash=prev_hash,
            current_hash=current_hash,
            siem_loged=False,
        )

        session.add(envelope)
        # flush pour obtenir envelope_id avant le commit
        session.flush()

        nonce.used = True
        nonce.used_at = now
        nonce.the_envelope = envelope.envelope_id

        session.commit()
        session.refresh(envelope)

        log.info(
            f"Vote enregistré — vote_id={vote_id} envelope_id={envelope.envelope_id} "
            f"mode={vote.vote_mode} user={'anonyme' if the_user is None else the_user}"
        )

        # Clôture automatique si tous ont voté ou si le vote a expiré
        _auto_close_if_needed(vote_id)

        return envelope

    except Exception as e:
        log.error(f"Échec du vote — vote_id={vote_id} nonce={nonce_value[:8]}… : {e}")
        session.rollback()
        raise
    finally:
        session.close()


# =========================
# TOUS LES VOTES (admin)
# =========================
def get_all_votes() -> list['VOTES']:
    close_expired_votes()
    session = db.get_session()
    try:
        return session.query(VOTES).order_by(VOTES.vote_id.desc()).all()
    finally:
        session.close()


# =========================
# DÉPOUILLEMENT D'UN VOTE
# =========================
def count_results(vote_id: int) -> dict:
    """Calcule les résultats d'un vote selon son type (majorité / unanimité / minimum_requis)."""
    session = db.get_session()
    try:
        vote = session.get(VOTES, vote_id)
        if not vote:
            raise ValueError("Vote non trouvé.")

        envelopes = session.query(ENVELOPES).filter(ENVELOPES.the_vote == vote_id).all()
        answers   = session.query(ANSWERS).filter(ANSWERS.the_vote == vote_id).all()
        total_assigned = session.query(NONCES).filter(NONCES.the_vote == vote_id).count()
        total_votes = len(envelopes)

        counts = {a.answer_id: {"text": a.answer_text, "count": 0} for a in answers}
        for env in envelopes:
            if env.vote_choice in counts:
                counts[env.vote_choice]["count"] += 1

        if total_votes == 0:
            verdict = "EN ATTENTE DE VOTES"
        elif vote.vote_type == "unanimité":
            unique = {e.vote_choice for e in envelopes}
            if len(unique) == 1:
                winner_id = next(iter(unique))
                verdict = f"APPROUVÉ À L'UNANIMITÉ → {counts[winner_id]['text']}"
            else:
                verdict = "REJETÉ — pas d'unanimité"
        elif vote.vote_type == "majorité":
            max_count = max(c["count"] for c in counts.values())
            tops = [c for c in counts.values() if c["count"] == max_count]
            if len(tops) == 1:
                verdict = f"MAJORITÉ → {tops[0]['text']}"
            else:
                verdict = "ÉGALITÉ"
        elif vote.vote_type == "minimum_requis":
            k = vote.k_required or 0
            max_count = max((c["count"] for c in counts.values()), default=0)
            tops = [c for c in counts.values() if c["count"] == max_count]
            if max_count >= k and len(tops) == 1:
                verdict = f"APPROUVÉ ({max_count}/{k} requis) → {tops[0]['text']}"
            elif max_count >= k:
                verdict = f"ÉGALITÉ (seuil atteint : {max_count}/{k})"
            else:
                verdict = f"SEUIL NON ATTEINT ({max_count}/{k} requis)"
        else:
            verdict = "TYPE DE VOTE INCONNU"

        return {
            "vote_id":        vote.vote_id,
            "question":       vote.question,
            "vote_type":      vote.vote_type,
            "vote_mode":      vote.vote_mode,
            "vote_status":    vote.vote_status,
            "timeout_at":     vote.timeout_at,
            "total_assigned": total_assigned,
            "total_votes":    total_votes,
            "counts":         counts,
            "verdict":        verdict,
        }
    finally:
        session.close()


# =========================
# VOTES EN COURS + VOTANTS EN ATTENTE (admin)
# =========================
def get_ongoing_votes_with_pending_voters() -> list[dict]:
    """Pour chaque vote ouvert, retourne les utilisateurs n'ayant pas encore voté."""
    close_expired_votes()
    session = db.get_session()
    try:
        open_votes = session.query(VOTES).filter(
            VOTES.is_active == True,
            VOTES.vote_status == "open",
        ).all()

        result = []
        for vote in open_votes:
            pending = (
                session.query(NONCES, USERS)
                .join(USERS, NONCES.the_user == USERS.user_id)
                .filter(NONCES.the_vote == vote.vote_id, NONCES.used == False)
                .all()
            )
            voted_count = session.query(NONCES).filter(
                NONCES.the_vote == vote.vote_id, NONCES.used == True
            ).count()

            result.append({
                "vote_id":     vote.vote_id,
                "question":    vote.question,
                "vote_mode":   vote.vote_mode,
                "timeout_at":  vote.timeout_at,
                "voted_count": voted_count,
                "total":       len(pending) + voted_count,
                "pending":     [
                    (u.user_id, u.username, u.first_name, u.last_name)
                    for _, u in pending
                ],
            })
        return result
    finally:
        session.close()


# =========================
# VOTES PASSÉS D'UN UTILISATEUR + RÉSULTATS
# =========================
def get_past_votes_for_user(user_id: int) -> list[dict]:
    """Retourne les votes auxquels l'utilisateur a été assigné, avec résultats et son choix."""
    session = db.get_session()
    try:
        nonces_votes = (
            session.query(NONCES, VOTES)
            .join(VOTES, NONCES.the_vote == VOTES.vote_id)
            .filter(NONCES.the_user == user_id)
            .order_by(VOTES.vote_id.desc())
            .all()
        )

        result = []
        for nonce, vote in nonces_votes:
            answers   = session.query(ANSWERS).filter(ANSWERS.the_vote == vote.vote_id).all()
            envelopes = session.query(ENVELOPES).filter(ENVELOPES.the_vote == vote.vote_id).all()

            counts = {a.answer_id: {"text": a.answer_text, "count": 0} for a in answers}
            for env in envelopes:
                if env.vote_choice in counts:
                    counts[env.vote_choice]["count"] += 1

            user_choice_text = None
            if nonce.used and vote.vote_mode == "auditable" and nonce.the_envelope:
                env = session.get(ENVELOPES, nonce.the_envelope)
                if env and env.vote_choice in counts:
                    user_choice_text = counts[env.vote_choice]["text"]

            result.append({
                "vote_id":          vote.vote_id,
                "question":         vote.question,
                "vote_type":        vote.vote_type,
                "vote_mode":        vote.vote_mode,
                "vote_status":      vote.vote_status,
                "timeout_at":       vote.timeout_at,
                "has_voted":        nonce.used,
                "user_choice_text": user_choice_text,
                "counts":           counts,
                "total_votes":      len(envelopes),
            })
        return result
    finally:
        session.close()


# =========================
# VOTES EN ATTENTE POUR UN UTILISATEUR
# =========================
def get_pending_votes_for_user(user_id: int) -> list[tuple['NONCES', 'VOTES']]:
    """Retourne les (nonce, vote) où l'utilisateur n'a pas encore voté."""
    close_expired_votes()
    session = db.get_session()
    try:
        results = (
            session.query(NONCES, VOTES)
            .join(VOTES, NONCES.the_vote == VOTES.vote_id)
            .filter(
                NONCES.the_user == user_id,
                NONCES.used == False,
                VOTES.is_active == True,
                VOTES.vote_status == "open",
            )
            .all()
        )
        return results
    finally:
        session.close()


# =========================
# OPTIONS DE RÉPONSE D'UN VOTE
# =========================
def get_answers_for_vote(vote_id: int) -> list['ANSWERS']:
    """Retourne les options de réponse disponibles pour un vote."""
    session = db.get_session()
    try:
        return session.query(ANSWERS).filter(ANSWERS.the_vote == vote_id).all()
    finally:
        session.close()


# =========================
# CLÔTURE MANUELLE D'UN VOTE (admin)
# =========================
def close_vote(vote_id: int) -> 'VOTES':
    """Ferme manuellement un vote (admin). Lève ValueError si déjà fermé."""
    session = db.get_session()
    try:
        vote = session.get(VOTES, vote_id)
        if not vote:
            raise ValueError("Vote non trouvé.")
        if vote.vote_status != "open":
            raise ValueError(f"Ce vote est déjà '{vote.vote_status}', impossible de le fermer.")

        now = datetime.utcnow()
        vote.vote_status = "closed"
        vote.is_active   = False
        vote.closed_at   = now
        session.commit()
        session.refresh(vote)
        log.info(f"Vote #{vote_id} fermé manuellement à {now.isoformat()}")
        return vote
    except Exception as e:
        log.error(f"Fermeture du vote #{vote_id} échouée : {e}")
        session.rollback()
        raise
    finally:
        session.close()


# =========================
# CLÔTURE AUTOMATIQUE PAR EXPIRATION (bulk)
# =========================
def close_expired_votes() -> int:
    """Ferme tous les votes dont timeout_at est dépassé. Retourne le nombre fermés."""
    session = db.get_session()
    try:
        now = datetime.utcnow()
        expired = (
            session.query(VOTES)
            .filter(
                VOTES.vote_status == "open",
                VOTES.timeout_at.isnot(None),
                VOTES.timeout_at <= now,
            )
            .all()
        )
        for vote in expired:
            vote.vote_status = "closed"
            vote.is_active   = False
            vote.closed_at   = now
        if expired:
            session.commit()
        return len(expired)
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# =========================
# CHECK CLÔTURE AUTOMATIQUE APRÈS UN VOTE
# =========================
def _auto_close_if_needed(vote_id: int) -> bool:
    """Vérifie si un vote doit être fermé (expiré ou tous ont voté). Retourne True si fermé."""
    session = db.get_session()
    try:
        vote = session.get(VOTES, vote_id)
        if not vote or vote.vote_status != "open":
            return False

        now = datetime.utcnow()
        should_close = False

        # Condition 1 : expiration dépassée
        if vote.timeout_at and vote.timeout_at <= now:
            should_close = True

        # Condition 2 : tous les votants assignés ont voté
        if not should_close:
            total = session.query(NONCES).filter(NONCES.the_vote == vote_id).count()
            used  = session.query(NONCES).filter(
                NONCES.the_vote == vote_id, NONCES.used == True
            ).count()
            if total > 0 and used == total:
                should_close = True

        if should_close:
            vote.vote_status = "closed"
            vote.is_active   = False
            vote.closed_at   = now
            session.commit()
            return True

        return False
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

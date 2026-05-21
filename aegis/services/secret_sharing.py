# AEGIS - NowBlackout ENSIBS 2025
# Secret Sharing Service - Shamir's Secret Sharing (SSS) via sslib
#
# Flux :
#   split_and_store()       → admin crée un secret, le split distribue les parts aux badges
#   get_shares_for_badge()  → member voit les secrets dont il est dépositaire (sans valeur)
#   list_labels()           → admin liste les labels existants
#   delete_by_label()       → admin supprime un secret (les parts associées sont perdues)
#   collect_share()         → récupère la part d'un badge pour un secret donné
#   reconstruct()           → reconstruit le secret à partir de k parts collectées

from datetime import datetime

from sslib import shamir as sslib_shamir

import aegis.core._database as db
from aegis.core._models import SECRETS, SHARES, BADGES, USERS
from aegis.core._logger import get_logger

log = get_logger("secret_sharing")


# =========================
# SPLIT & DISTRIBUTE
# =========================

def split_and_store(
    label: str,
    secret_text: str,
    k: int,
    badge_ids: list[int],
    creator_user_id: int,
) -> "SECRETS":
    """
    Découpe secret_text en len(badge_ids) parts (seuil k).
    Stocke le secret (prime_mod) en SECRETS et chaque part en SHARES.
    L'appelant (admin) ne doit PAS conserver le secret original après cet appel.

    Raises ValueError si :
    - label déjà utilisé
    - k < 2 ou k > n
    - un badge_id est invalide
    """
    n = len(badge_ids)
    if not label or not label.strip():
        raise ValueError("Le label du secret ne peut pas être vide.")
    if not secret_text:
        raise ValueError("Le secret ne peut pas être vide.")
    if k < 2:
        raise ValueError("k (parts requises) doit être au moins 2.")
    if k > n:
        raise ValueError(f"k ({k}) ne peut pas dépasser le nombre de dépositaires ({n}).")

    session = db.get_session()
    try:
        # Unicité du label
        existing = session.query(SECRETS).filter(
            SECRETS.secret_action == label.strip()
        ).first()
        if existing:
            raise ValueError(f"Un secret avec le label '{label}' existe déjà.")

        # Vérification que tous les badges existent et ne sont pas révoqués
        for bid in badge_ids:
            badge = session.get(BADGES, bid)
            if not badge:
                raise ValueError(f"Badge ID {bid} introuvable.")
            if badge.is_revoked:
                raise ValueError(f"Badge ID {bid} est révoqué — impossible de lui confier une part.")

        # Split Shamir
        raw_split  = sslib_shamir.split_secret(secret_text.encode("utf-8"), k, n)
        b64_split  = sslib_shamir.to_base64(raw_split)
        prime_mod  = b64_split["prime_mod"]
        shares_b64 = b64_split["shares"]   # list de strings "index-base64value"

        # Enregistrement du secret (prime_mod = clé de reconstruction)
        secret = SECRETS(
            secret_action=label.strip(),
            secret_value=prime_mod,
            secret_type="shamir",
            secret_share_n=n,
            secret_share_k=k,
            used=False,
            creator_user_id=creator_user_id,
            issued_at=datetime.utcnow(),
        )
        session.add(secret)
        session.flush()  # obtenir secret_id

        # Distribution des parts (une par badge, ordre aléatoire non garanti → sslib indexe 1..n)
        for i, badge_id in enumerate(badge_ids):
            share = SHARES(
                the_secret=secret.secret_id,
                the_badge=badge_id,
                shamir_value=shares_b64[i],
            )
            session.add(share)

        session.commit()
        session.refresh(secret)

        log.info(
            f"Secret '{label}' créé — secret_id={secret.secret_id} "
            f"k={k}/{n} par user_id={creator_user_id}"
        )
        return secret

    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# =========================
# FRAGMENTS D'UN BADGE (F3)
# =========================

def get_shares_for_badge(badge_id: int) -> list[dict]:
    """
    Retourne les secrets dont ce badge est dépositaire.
    Ne retourne PAS la valeur du fragment (affichage de garde, pas de reconstruction).
    """
    session = db.get_session()
    try:
        rows = (
            session.query(SHARES, SECRETS)
            .join(SECRETS, SHARES.the_secret == SECRETS.secret_id)
            .filter(SHARES.the_badge == badge_id)
            .all()
        )
        return [
            {
                "share_id":   share.share_id,
                "secret_id":  secret.secret_id,
                "label":      secret.secret_action,
                "k":          secret.secret_share_k,
                "n":          secret.secret_share_n,
                "issued_at":  secret.issued_at,
                "secret_used": secret.used,
            }
            for share, secret in rows
        ]
    finally:
        session.close()


# =========================
# LISTE DES LABELS (admin)
# =========================

def list_labels() -> list[dict]:
    """Retourne tous les secrets (label + métadonnées, sans parts)."""
    session = db.get_session()
    try:
        all_secrets = session.query(SECRETS).filter(
            SECRETS.secret_type == "shamir"
        ).order_by(SECRETS.issued_at.desc()).all()
        return [
            {
                "secret_id":  s.secret_id,
                "label":      s.secret_action,
                "k":          s.secret_share_k,
                "n":          s.secret_share_n,
                "used":       s.used,
                "issued_at":  s.issued_at,
                "creator_id": s.creator_user_id,
            }
            for s in all_secrets
        ]
    finally:
        session.close()


# =========================
# SUPPRESSION PAR LABEL (admin)
# =========================

def delete_by_label(label: str) -> int:
    """
    Supprime le secret identifié par son label ainsi que toutes ses parts.
    Retourne le nombre de parts supprimées.
    """
    session = db.get_session()
    try:
        secret = session.query(SECRETS).filter(
            SECRETS.secret_action == label.strip()
        ).first()
        if not secret:
            raise ValueError(f"Aucun secret avec le label '{label}'.")

        n_shares = session.query(SHARES).filter(
            SHARES.the_secret == secret.secret_id
        ).delete(synchronize_session=False)

        session.delete(secret)
        session.commit()

        log.info(
            f"Secret '{label}' (secret_id={secret.secret_id}) supprimé — "
            f"{n_shares} part(s) révoquée(s)"
        )
        return n_shares

    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# =========================
# RÉCUPÉRATION D'UNE PART PAR BADGE (reconstruction)
# =========================

def collect_share(secret_id: int, badge_id: int) -> str | None:
    """
    Retourne la valeur du fragment pour ce badge et ce secret.
    Retourne None si ce badge n'a pas de part pour ce secret.
    """
    session = db.get_session()
    try:
        share = session.query(SHARES).filter(
            SHARES.the_secret == secret_id,
            SHARES.the_badge  == badge_id,
        ).first()
        return share.shamir_value if share else None
    finally:
        session.close()


# =========================
# RECONSTRUCTION DU SECRET
# =========================

def reconstruct(secret_id: int, collected_shares: list[str]) -> str:
    """
    Reconstruit le secret à partir de collected_shares (valeurs "index-base64").
    Raises ValueError si pas assez de parts ou secret introuvable.
    """
    session = db.get_session()
    try:
        secret = session.get(SECRETS, secret_id)
        if not secret:
            raise ValueError(f"Secret ID {secret_id} introuvable.")
        if len(collected_shares) < secret.secret_share_k:
            raise ValueError(
                f"Parts insuffisantes : {len(collected_shares)} collectée(s), "
                f"{secret.secret_share_k} requises."
            )

        data = {
            "required_shares": secret.secret_share_k,
            "prime_mod":       secret.secret_value,
            "shares":          collected_shares,
        }
        result_bytes = sslib_shamir.recover_secret(sslib_shamir.from_base64(data))
        result       = result_bytes.decode("utf-8")

        # Marquer comme utilisé
        secret.used    = True
        secret.used_at = datetime.utcnow()
        session.commit()

        log.info(f"Secret '{secret.secret_action}' (secret_id={secret_id}) reconstruit avec succès")
        return result

    except Exception as e:
        log.error(f"Échec de la reconstruction secret_id={secret_id} : {e}")
        raise
    finally:
        session.close()


# =========================
# HELPER : badge_id d'un user
# =========================

def get_badge_id_for_user(user_id: int) -> int | None:
    """Retourne le badge_id actif d'un utilisateur, ou None."""
    session = db.get_session()
    try:
        badge = session.query(BADGES).filter(
            BADGES.the_user   == user_id,
            BADGES.is_revoked == False,
        ).first()
        return badge.badge_id if badge else None
    finally:
        session.close()


# =========================
# HELPER : liste des dépositaires d'un secret
# =========================

def get_custodians(secret_id: int) -> list[dict]:
    """Retourne les utilisateurs détenant une part pour un secret donné."""
    session = db.get_session()
    try:
        rows = (
            session.query(SHARES, BADGES, USERS)
            .join(BADGES, SHARES.the_badge == BADGES.badge_id)
            .join(USERS,  BADGES.the_user  == USERS.user_id)
            .filter(SHARES.the_secret == secret_id)
            .all()
        )
        return [
            {
                "share_id":   share.share_id,
                "badge_id":   badge.badge_id,
                "user_id":    user.user_id,
                "username":   user.username,
                "first_name": user.first_name,
                "last_name":  user.last_name,
            }
            for share, badge, user in rows
        ]
    finally:
        session.close()

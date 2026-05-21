# AEGIS - NowBlackout ENSIBS 2025
# Maintenance Service - Sauvegarde DB et vérification de la chaîne d'intégrité

import hashlib
import shutil
from datetime import datetime
from pathlib import Path

import aegis.core._database as db
from aegis.core._models import VOTES, ENVELOPES
from aegis.core._logger import get_logger

log = get_logger("maintenance")

# Chemins relatifs à la racine du projet (où main.py est lancé)
_DB_PATH   = Path("aegis.db")
_SAVES_DIR = Path("saves")


# =========================
# SAUVEGARDE DE LA BASE
# =========================

def db_save() -> str:
    """
    Copie aegis.db dans saves/JJ-MM-AAAA_HH-MM-SS-aegis-save.db.
    Retourne le chemin absolu de la sauvegarde.
    """
    if not _DB_PATH.exists():
        log.error(f"Sauvegarde impossible : fichier introuvable ({_DB_PATH.resolve()})")
        raise FileNotFoundError(f"Base de données introuvable : {_DB_PATH.resolve()}")

    _SAVES_DIR.mkdir(parents=True, exist_ok=True)

    now      = datetime.now()
    filename = now.strftime("%d-%m-%Y_%H-%M-%S") + "-aegis-save.db"
    dest     = _SAVES_DIR / filename

    shutil.copy2(_DB_PATH, dest)
    size_kb = dest.stat().st_size / 1024
    log.info(f"Sauvegarde créée : {dest.resolve()} ({size_kb:.1f} Ko)")
    return str(dest.resolve())


# =========================
# VÉRIFICATION DE LA CHAÎNE D'INTÉGRITÉ
# =========================

def verify_chain() -> dict:
    """
    Parcourt toutes les enveloppes de chaque vote et vérifie :
      1. La cohérence des prev_hash entre enveloppes consécutives.
      2. Le recalcul du current_hash à partir de (prev_hash, vote_id, vote_choice, the_date).

    Retourne un dict :
    {
      "total_votes":    int,
      "checked_votes":  int,   # votes ayant au moins une enveloppe
      "ok":             int,
      "corrupted":      int,
      "results": [
        {
          "vote_id":           int,
          "question":          str,
          "status":            "OK" | "CORROMPU" | "VIDE",
          "envelopes_checked": int,
          "errors":            [str, ...]
        }, ...
      ]
    }
    """
    session = db.get_session()
    try:
        all_votes = session.query(VOTES).order_by(VOTES.vote_id.asc()).all()

        results      = []
        total_ok     = 0
        total_ko     = 0
        checked      = 0

        for vote in all_votes:
            envelopes = (
                session.query(ENVELOPES)
                .filter(ENVELOPES.the_vote == vote.vote_id)
                .order_by(ENVELOPES.envelope_id.asc())
                .all()
            )

            if not envelopes:
                results.append({
                    "vote_id":           vote.vote_id,
                    "question":          vote.question,
                    "status":            "VIDE",
                    "envelopes_checked": 0,
                    "errors":            [],
                })
                continue

            checked += 1
            errors: list[str] = []
            expected_prev = "GENESIS"

            for env in envelopes:
                # 1 — Vérification de la chaîne prev → current
                if env.prev_hash != expected_prev:
                    errors.append(
                        f"Enveloppe #{env.envelope_id} : rupture de chaîne — "
                        f"prev_hash attendu={expected_prev[:16]}… "
                        f"stocké={env.prev_hash[:16]}…"
                    )

                # 2 — Recalcul du hash courant
                raw           = f"{env.prev_hash}{vote.vote_id}{env.vote_choice}{env.the_date.isoformat()}"
                expected_hash = hashlib.sha256(raw.encode()).hexdigest()

                if env.current_hash != expected_hash:
                    errors.append(
                        f"Enveloppe #{env.envelope_id} : hash invalide — "
                        f"calculé={expected_hash[:16]}… "
                        f"stocké={env.current_hash[:16]}…"
                    )

                expected_prev = env.current_hash

            status = "OK" if not errors else "CORROMPU"

            if errors:
                total_ko += 1
                log.error(
                    f"Vote #{vote.vote_id} '{vote.question[:40]}' — "
                    f"CORROMPU ({len(errors)} erreur(s))"
                )
                for e in errors:
                    log.error(f"  └─ {e}")
            else:
                total_ok += 1
                log.info(
                    f"Vote #{vote.vote_id} '{vote.question[:40]}' — "
                    f"OK ({len(envelopes)} enveloppe(s))"
                )

            results.append({
                "vote_id":           vote.vote_id,
                "question":          vote.question,
                "status":            status,
                "envelopes_checked": len(envelopes),
                "errors":            errors,
            })

        summary_msg = (
            f"Vérification terminée — {len(all_votes)} vote(s), "
            f"{total_ok} OK, {total_ko} CORROMPU(s)"
        )
        if total_ko == 0:
            log.info(summary_msg)
        else:
            log.error(summary_msg)

        return {
            "total_votes":   len(all_votes),
            "checked_votes": checked,
            "ok":            total_ok,
            "corrupted":     total_ko,
            "results":       results,
        }

    finally:
        session.close()

# AEGIS - NowBlackout ENSIBS 2025
# API Interface - Flask JSON API with RBAC for the frontend
#
# Lancer : python -m aegis.interfaces.api  (depuis la racine du projet)
# Port par défaut : 5001
#
# Authentification : POST /api/login  { username, header_id, totp_code }
#   header_id = UID brut du badge NFC (l'API calcule le hash en interne)
#   La session Flask stocke user_id + role après login réussi.
#
# Tous les endpoints protégés retournent 401 si non connecté, 403 si rôle insuffisant.

import os
import secrets
from functools import wraps

from flask import Flask, jsonify, request, session

from aegis.services import users, badges, votes
from aegis.services import rbac

app = Flask(__name__)
app.secret_key = os.getenv("AEGIS_SECRET_KEY") or secrets.token_hex(32)


# ---------------------------------------------------------------------------
# Décorateurs d'accès
# ---------------------------------------------------------------------------

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Non authentifié. Veuillez vous connecter."}), 401
        return f(*args, **kwargs)
    return decorated


def permission_required(permission: str):
    """Décorateur : vérifie la permission via le service rbac."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if "user_id" not in session:
                return jsonify({"error": "Non authentifié."}), 401
            role = session.get("role", "")
            try:
                rbac.require_permission(role, permission)
            except PermissionError as e:
                return jsonify({"error": str(e)}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator


def _current_user():
    return users.get_user_by_id(session["user_id"])


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@app.post("/api/login")
def api_login():
    """
    Body JSON : { "username": "...", "header_id": "...", "totp_code": "..." }
    header_id = UID brut du badge NFC (chaîne lisible, pas le hash).
    """
    data = request.get_json(silent=True) or {}
    username  = (data.get("username") or "").strip().lower()
    header_id = (data.get("header_id") or "").strip()
    totp_code = (data.get("totp_code") or "").strip()

    if not username or not header_id or not totp_code:
        return jsonify({"error": "username, header_id et totp_code sont requis."}), 400

    user = users.get_user_by_username(username)
    if not user:
        return jsonify({"error": "Utilisateur inconnu."}), 401
    if not user.the_role:
        return jsonify({"error": "Cet utilisateur n'a pas de rôle assigné."}), 403

    ok, error = badges.verify_badge_and_totp(user.user_id, header_id, totp_code)
    if not ok:
        return jsonify({"error": f"Authentification échouée : {error}"}), 401

    session["user_id"] = user.user_id
    session["role"]    = user.the_role
    return jsonify({
        "message": "Connexion réussie.",
        "user": {
            "user_id":    user.user_id,
            "username":   user.username,
            "first_name": user.first_name,
            "last_name":  user.last_name,
            "role":       user.the_role,
        },
        "permissions": sorted(rbac.get_permissions(user.the_role)),
    })


@app.post("/api/logout")
@login_required
def api_logout():
    username = session.get("username", "")
    session.clear()
    return jsonify({"message": f"Déconnexion réussie."})


@app.get("/api/me")
@login_required
def api_me():
    user = _current_user()
    return jsonify({
        "user_id":    user.user_id,
        "username":   user.username,
        "first_name": user.first_name,
        "last_name":  user.last_name,
        "role":       user.the_role,
        "permissions": sorted(rbac.get_permissions(user.the_role)),
    })


# ---------------------------------------------------------------------------
# Utilisateurs
# ---------------------------------------------------------------------------

@app.get("/api/users")
@permission_required("users.list")
def api_list_users():
    all_users = users.list_all_users()
    return jsonify([
        {
            "user_id":    u.user_id,
            "username":   u.username,
            "first_name": u.first_name,
            "last_name":  u.last_name,
            "email":      u.email,
            "job":        u.job,
            "role":       u.the_role,
            "badge_id":   badge_id,
        }
        for u, badge_id in all_users
    ])


@app.post("/api/users")
@permission_required("users.create")
def api_create_user():
    data = request.get_json(silent=True) or {}
    try:
        user = users.create_user(data)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"message": "Utilisateur créé.", "user_id": user.user_id}), 201


@app.put("/api/users/<int:user_id>")
@permission_required("users.edit")
def api_edit_user(user_id: int):
    data = request.get_json(silent=True) or {}
    try:
        updated = users.edit_user(user_id, data)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"message": "Utilisateur mis à jour.", "user_id": updated.user_id})


@app.delete("/api/users/<int:user_id>")
@permission_required("users.delete")
def api_delete_user(user_id: int):
    try:
        users.remove_user(user_id)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"message": "Utilisateur supprimé."})


# ---------------------------------------------------------------------------
# Badges
# ---------------------------------------------------------------------------

@app.get("/api/badges")
@permission_required("badges.list")
def api_list_badges():
    all_badges = badges.list_all_badges()
    return jsonify([
        {
            "badge_id":       b.badge_id,
            "username":       username,
            "header_id":      b.header_id,
            "issued_at":      str(b.issued_at),
            "expires_at":     str(b.expires_at),
            "is_revoked":     b.is_revoked,
            "revoked_reason": b.revoked_reason,
        }
        for b, username in all_badges
    ])


@app.put("/api/badges/<int:badge_id>")
@permission_required("badges.revoke")
def api_edit_badge(badge_id: int):
    data = request.get_json(silent=True) or {}
    try:
        updated = badges.edit_badge(badge_id, data)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"message": "Badge mis à jour.", "badge_id": updated.badge_id})


# ---------------------------------------------------------------------------
# Votes
# ---------------------------------------------------------------------------

@app.get("/api/votes")
@login_required
def api_list_votes():
    """
    - superadmin / admin / manager / auditor : tous les votes
    - member : uniquement les votes qui lui sont assignés
    """
    role = session["role"]
    try:
        if rbac.has_permission(role, "votes.results.all") or rbac.has_permission(role, "votes.manage"):
            all_votes = votes.get_all_votes()
            return jsonify([_vote_to_dict(v) for v in all_votes])
        else:
            # member : ses votes assignés
            user_id = session["user_id"]
            data = votes.get_past_votes_for_user(user_id)
            return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.post("/api/votes")
@permission_required("votes.create")
def api_create_vote():
    """
    Crée un vote et l'assigne aux utilisateurs indiqués.
    Body : { vote_data fields..., "assigned_user_ids": [1, 2, 3] ou "all" }
    """
    data = request.get_json(silent=True) or {}
    user_id = session["user_id"]

    vote_data = {k: v for k, v in data.items() if k != "assigned_user_ids"}
    vote_data["creator_user_id"] = user_id

    # Conversion de la date si fournie en string "YYYY-MM-DD"
    if "expiration_date" in vote_data and isinstance(vote_data["expiration_date"], str):
        from datetime import date
        try:
            y, m, d = map(int, vote_data["expiration_date"].split("-"))
            vote_data["expiration_date"] = date(y, m, d)
        except ValueError:
            return jsonify({"error": "Format de date invalide. Utilisez YYYY-MM-DD."}), 400

    try:
        vote = votes.create_vote(vote_data)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # Ajout des réponses si fournies
    answers = data.get("answers", [])
    if vote.is_boolean:
        answers = ["OUI", "NON"]
    if answers:
        try:
            votes.add_answers_to_vote(vote.vote_id, answers)
        except Exception as e:
            return jsonify({"error": f"Vote créé mais erreur sur les réponses : {e}"}), 207

    # Assignation des utilisateurs
    assigned_ids = data.get("assigned_user_ids", [])
    if assigned_ids == "all":
        all_users = users.list_users(False)
        assigned_ids = [u.user_id for u, _ in all_users]

    errors = []
    for uid in (assigned_ids or []):
        try:
            votes.assign_vote_to_user(vote.vote_id, uid)
        except Exception as e:
            errors.append({"user_id": uid, "error": str(e)})

    response = {"message": "Vote créé.", "vote_id": vote.vote_id}
    if errors:
        response["assignment_errors"] = errors
    return jsonify(response), 201


@app.get("/api/votes/pending")
@permission_required("votes.cast")
def api_pending_votes():
    """Retourne les votes en attente pour l'utilisateur connecté."""
    user_id = session["user_id"]
    try:
        pending = votes.get_pending_votes_for_user(user_id)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify([
        {
            "nonce":       nonce.nonce,
            "vote_id":     vote.vote_id,
            "question":    vote.question,
            "description": vote.description_text,
            "vote_mode":   vote.vote_mode,
            "vote_type":   vote.vote_type,
            "timeout_at":  str(vote.timeout_at),
        }
        for nonce, vote in pending
    ])


@app.get("/api/votes/ongoing")
@permission_required("votes.manage")
def api_ongoing_votes():
    try:
        data = votes.get_ongoing_votes_with_pending_voters()
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify(data)


@app.get("/api/votes/<int:vote_id>/results")
@login_required
def api_vote_results(vote_id: int):
    """
    Résultats d'un vote.
    - votes.results.all  → accès à tous les votes
    - votes.results.own  → uniquement les votes auxquels l'utilisateur participe (member)
                           ou les votes qu'il a créés (manager)
    """
    role    = session["role"]
    user_id = session["user_id"]

    if rbac.has_permission(role, "votes.results.all"):
        pass  # accès libre
    elif rbac.has_permission(role, "votes.results.own"):
        # Vérification que l'utilisateur est bien concerné par ce vote
        try:
            past = votes.get_past_votes_for_user(user_id)
            allowed_ids = {entry["vote_id"] for entry in past}
        except Exception as e:
            return jsonify({"error": str(e)}), 500

        # Pour manager : aussi les votes qu'il a créés
        if role == "manager":
            try:
                all_v = votes.get_all_votes()
                allowed_ids |= {v.vote_id for v in all_v if v.creator_user_id == user_id}
            except Exception:
                pass

        if vote_id not in allowed_ids:
            return jsonify({"error": "Accès refusé à ce vote."}), 403
    else:
        return jsonify({"error": "Accès refusé."}), 403

    try:
        result = votes.count_results(vote_id)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify(result)


@app.get("/api/votes/<int:vote_id>/answers")
@login_required
def api_vote_answers(vote_id: int):
    """Retourne les options de réponse d'un vote (nécessaire avant de voter)."""
    try:
        answers = votes.get_answers_for_vote(vote_id)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify([{"answer_id": a.answer_id, "answer_text": a.answer_text} for a in answers])


@app.post("/api/votes/<int:vote_id>/cast")
@permission_required("votes.cast")
def api_cast_vote(vote_id: int):
    """
    Body JSON : { "nonce": "...", "answer_id": 3, "header_id": "...", "totp_code": "..." }
    La réauthentification NFC+TOTP est requise pour valider le vote.
    """
    data      = request.get_json(silent=True) or {}
    user_id   = session["user_id"]
    nonce     = (data.get("nonce") or "").strip()
    answer_id = data.get("answer_id")
    header_id = (data.get("header_id") or "").strip()
    totp_code = (data.get("totp_code") or "").strip()

    if not all([nonce, answer_id, header_id, totp_code]):
        return jsonify({"error": "nonce, answer_id, header_id et totp_code sont requis."}), 400

    # Réauthentification avant enregistrement du vote
    ok, error = badges.verify_badge_and_totp(user_id, header_id, totp_code)
    if not ok:
        return jsonify({"error": f"Authentification échouée : {error}"}), 401

    try:
        envelope = votes.cast_vote(nonce, vote_id, int(answer_id))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({
        "message":     "Vote enregistré avec succès.",
        "envelope_id": envelope.envelope_id,
        "hash":        envelope.current_hash[:20] + "...",
    })


@app.post("/api/votes/<int:vote_id>/close")
@permission_required("votes.close")
def api_close_vote(vote_id: int):
    try:
        vote = votes.close_vote(vote_id)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"message": f"Vote #{vote.vote_id} fermé.", "closed_at": str(vote.closed_at)})


# ---------------------------------------------------------------------------
# Audit (auditor uniquement)
# ---------------------------------------------------------------------------

@app.get("/api/votes/<int:vote_id>/audit")
@permission_required("votes.audit")
def api_vote_audit(vote_id: int):
    """
    Retourne la liste des votants et leurs choix pour un vote AUDITABLE.
    Permission : votes.audit (auditor + superadmin uniquement).
    """
    try:
        all_votes = votes.get_all_votes()
        vote = next((v for v in all_votes if v.vote_id == vote_id), None)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    if not vote:
        return jsonify({"error": f"Vote #{vote_id} introuvable."}), 404

    if vote.vote_mode != "auditable":
        return jsonify({"error": "Ce vote est confidentiel. L'audit n'est pas disponible."}), 403

    try:
        result = votes.count_results(vote_id)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({
        "vote_id":   vote_id,
        "question":  vote.question,
        "vote_mode": vote.vote_mode,
        "results":   result,
        "note": "Les détails individuels par votant sont dans la table ENVELOPES (the_user non null pour les votes auditables).",
    })


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _vote_to_dict(v) -> dict:
    return {
        "vote_id":      v.vote_id,
        "question":     v.question,
        "description":  v.description_text,
        "vote_type":    v.vote_type,
        "vote_mode":    v.vote_mode,
        "vote_status":  v.vote_status,
        "is_boolean":   v.is_boolean,
        "k_required":   v.k_required,
        "opened_at":    str(v.opened_at) if v.opened_at else None,
        "timeout_at":   str(v.timeout_at) if v.timeout_at else None,
        "closed_at":    str(v.closed_at) if v.closed_at else None,
        "creator_user_id": v.creator_user_id,
    }


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.getenv("AEGIS_API_PORT", 5001))
    debug = os.getenv("AEGIS_API_DEBUG", "false").lower() == "true"
    app.run(host="127.0.0.1", port=port, debug=debug)

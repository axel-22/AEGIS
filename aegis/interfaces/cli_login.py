# AEGIS - NowBlackout ENSIBS 2025
# CLI Login - Authenticated entry point with role-filtered menu

import sys
from datetime import datetime

from aegis.services import users, badges, votes
from aegis.services import rbac
import aegis.interfaces.cli as cli

# ---------------------------------------------------------------------------
# Définition du menu : (code, libellé affiché, permission requise)
# ---------------------------------------------------------------------------
MENU_ITEMS = [
    ("A1", "Lister tous les utilisateurs",          "users.list"),
    ("A2", "Lister les utilisateurs actifs",        "users.list"),
    ("A3", "Lister les utilisateurs révoqués",      "users.list"),
    ("A4", "Ajouter un utilisateur",                "users.create"),
    ("A5", "Éditer un utilisateur",                 "users.edit"),
    ("A6", "Supprimer un utilisateur",              "users.delete"),
    ("B1", "Lister tous les badges",                "badges.list"),
    ("B2", "Lister les badges actifs",              "badges.list"),
    ("B3", "Lister les badges expirés",             "badges.list"),
    ("B4", "Révoquer un badge compromis",           "badges.revoke"),
    ("C1", "Créer un nouveau vote",                 "votes.create"),
    ("C2", "Éditer un vote",                        "votes.manage"),
    ("C3", "Dépouiller un vote — voir les résultats", "votes.results.all"),
    ("C4", "Vérifier la chaîne d'intégrité",        "votes.results.all"),
    ("C5", "Votes en cours — votants en attente",   "votes.manage"),
    ("C6", "Forcer la clôture d'un vote",           "votes.close"),
    ("D1", "Générer clé Fernet TOTP",               "keys.generate"),
    ("D2", "Générer clé Fernet votes confidentiels","keys.generate"),
    ("D3", "Générer clé Fernet réponses",           "keys.generate"),
    ("E1", "Voir les logs récents",                 "logs.view"),
    ("E2", "Exporter les événements vers le SIEM",  "logs.export"),
    ("E3", "Sauvegarder la base de données",        "logs.backup"),
    ("F1", "Voir mes précédents votes",             "votes.results.own"),
    ("F2", "Voter",                                 "votes.cast"),
    ("F3", "Voir mes fragments secrets",            "secrets.view_own"),
    ("G1", "Créer un secret partagé",               "secrets.split"),
    ("G2", "Supprimer un secret",                   "secrets.delete"),
    ("G3", "Reconstruire un secret",                "secrets.reconstruct"),
]

SECTION_LABELS = {
    "A": ("👥",  "Utilisateurs"),
    "B": ("🎫",  "Badges"),
    "C": ("🗳️", "Votes"),
    "D": ("🧠",  "Sécurité & Outils"),
    "E": ("📦",  "Maintenance & Logs"),
    "F": ("📩",  "Mes Votes & Fragments"),
    "G": ("🔐",  "Secrets Partagés (SSS)"),
}


# ---------------------------------------------------------------------------
# Authentification
# ---------------------------------------------------------------------------

def login() -> users.USERS:
    """Authentifie un utilisateur via nom d'utilisateur + badge NFC + TOTP."""
    print("\n" + "═" * 60)
    print(" " * 18 + "🔐 Connexion à AEGIS CLI")
    print("═" * 60 + "\n")

    username = input("➡️  Nom d'utilisateur : ").strip().lower()
    user = users.get_user_by_username(username)
    if not user:
        raise ValueError(f"Utilisateur '{username}' non trouvé.")
    if not user.the_role:
        raise ValueError(f"L'utilisateur '{username}' n'a pas de rôle assigné.")

    print(f"\n👤 {user.first_name} {user.last_name} — rôle : {user.the_role}")
    print("🔐 Authentification par badge NFC + TOTP requise.\n")
    print("➡️  Passez votre badge NFC devant le lecteur...")

    header_id = None
    for attempt in range(2):
        try:
            header_id = badges.get_header_id_from_nfc()
            print("   ✅ Badge détecté.")
            break
        except RuntimeError as e:
            print(f"   ❌ {e}")
            if attempt == 0:
                retry = input("   Réessayer ? (oui/non) : ").strip().lower()
                if retry not in ('oui', 'o', 'yes', 'y'):
                    raise ValueError("Authentification annulée.")
            else:
                raise ValueError("Impossible de lire le badge. Connexion échouée.")

    totp_code = input("➡️  Code TOTP (Google Authenticator) : ").strip()
    ok, error = badges.verify_badge_and_totp(user.user_id, header_id, totp_code)
    if not ok:
        raise ValueError(f"Authentification échouée : {error}")

    print("✅ Connexion réussie !\n")
    return user


# ---------------------------------------------------------------------------
# Affichage du menu filtré par rôle
# ---------------------------------------------------------------------------

def _show_menu(role: str) -> list[str]:
    """Affiche uniquement les actions autorisées pour le rôle donné."""
    allowed = [(code, label) for code, label, perm in MENU_ITEMS
               if rbac.has_permission(role, perm)]

    sections: dict[str, list[tuple[str, str]]] = {}
    for code, label in allowed:
        sections.setdefault(code[0], []).append((code, label))

    print("\nVeuillez sélectionner une action (ex : A1) :\n")
    for section_key, items in sections.items():
        emoji, title = SECTION_LABELS.get(section_key, ("", section_key))
        print(f"{emoji}  {title} - {section_key}")
        for code, label in items:
            print(f"  {code[1]} →  {label}")
        print()

    print("❌  0 →  Quitter\n")
    return [code for code, _ in allowed]


# ---------------------------------------------------------------------------
# Opérations F1 / F2 contextualisées à l'utilisateur connecté
# ---------------------------------------------------------------------------

def _my_votes(current_user) -> None:
    """F1 — Affiche les votes de l'utilisateur connecté sans demander l'ID."""
    print(f"\n👤 {current_user.first_name} {current_user.last_name} ({current_user.username})\n")
    try:
        data = votes.get_past_votes_for_user(current_user.user_id)
    except Exception as e:
        print(f"❌ Erreur : {e}")
        return

    if not data:
        print("📭 Vous n'avez été assigné à aucun vote.")
        return

    for entry in data:
        status_emoji = "🟢" if entry["vote_status"] == "open" else "🔴"
        voted_emoji  = "✅" if entry["has_voted"] else "⏳"
        mode_emoji   = "🔍" if entry["vote_mode"] == "auditable" else "🔒"
        print(f"{'─' * 55}")
        print(f"  {voted_emoji} [Vote #{entry['vote_id']}] {status_emoji} {entry['question']}")
        print(f"     Type : {entry['vote_type']}  |  {mode_emoji} {entry['vote_mode']}  |  Expire : {entry['timeout_at']}")
        if entry["has_voted"]:
            if entry["vote_mode"] == "auditable" and entry.get("user_choice_text"):
                print(f"     📌 Votre choix : {entry['user_choice_text']}")
            else:
                print("     🔒 Vous avez voté (choix anonyme).")
        else:
            print("     ⏳ Vous n'avez pas encore voté.")
        if entry.get("counts"):
            print(f"     📊 Résultats courants ({entry['total_votes']} vote(s)) :")
            for d in entry["counts"].values():
                print(f"         {d['text']:20s} : {d['count']} vote(s)")
    print(f"{'─' * 55}")


def _cast_vote(current_user) -> None:
    """F2 — Vote pour l'utilisateur connecté (réauthentification NFC+TOTP au moment du vote)."""
    print(f"\n👤 {current_user.first_name} {current_user.last_name} ({current_user.username})\n")
    try:
        pending = votes.get_pending_votes_for_user(current_user.user_id)
    except Exception as e:
        print(f"❌ Erreur lors de la récupération des votes : {e}")
        return

    if not pending:
        print("✅ Vous n'avez aucun vote en attente.")
        return

    print(f"🗳️  Votes en attente ({len(pending)}) :\n")
    for i, (nonce, vote) in enumerate(pending):
        mode_emoji = "🔍" if vote.vote_mode == "auditable" else "🔒"
        print(f"  {i + 1}. [Vote #{vote.vote_id}] {mode_emoji} {vote.question}")
        if vote.description_text:
            print(f"       📝 {vote.description_text}")
        print(f"       ⏱️  Expire le : {vote.timeout_at}")

    choice_str = input("\n➡️  Sélectionnez un vote (numéro) : ").strip()
    try:
        choice_idx = int(choice_str) - 1
        if not (0 <= choice_idx < len(pending)):
            raise ValueError()
    except ValueError:
        print("❌ Sélection invalide.")
        return

    selected_nonce, selected_vote = pending[choice_idx]

    print(f"\n{'═' * 60}")
    print(f"📋 {selected_vote.question}")
    if selected_vote.description_text:
        print(f"   {selected_vote.description_text}")
    if selected_vote.vote_mode == "auditable":
        print("   🔍 Mode auditable — votre vote sera associé à votre identité.")
    else:
        print("   🔒 Mode confidentiel — votre vote est anonyme.")
    print(f"{'═' * 60}\n")

    try:
        answers = votes.get_answers_for_vote(selected_vote.vote_id)
    except Exception as e:
        print(f"❌ Erreur lors de la récupération des options : {e}")
        return

    if not answers:
        print("❌ Aucune option de réponse disponible pour ce vote.")
        return

    print("Options de réponse :")
    for a in answers:
        print(f"  [{a.answer_id}] {a.answer_text}")

    answer_id_str = input("\n➡️  Entrez l'ID de votre choix : ").strip()
    try:
        answer_id = int(answer_id_str)
        if answer_id not in [a.answer_id for a in answers]:
            raise ValueError()
    except ValueError:
        print("❌ Choix invalide.")
        return

    chosen_text = next(a.answer_text for a in answers if a.answer_id == answer_id)
    print(f"\n🔐 Authentification requise pour valider le vote « {chosen_text} ».")
    print("   Passez votre badge NFC devant le lecteur (30 secondes)...")

    header_id = None
    for attempt in range(2):
        try:
            header_id = badges.get_header_id_from_nfc()
            print("   ✅ Badge détecté.")
            break
        except RuntimeError as e:
            print(f"   ❌ {e}")
            if attempt == 0:
                retry = input("   Réessayer ? (oui/non) : ").strip().lower()
                if retry not in ('oui', 'o', 'yes', 'y'):
                    print("❌ Vote annulé.")
                    return
            else:
                print("❌ Impossible de lire le badge. Vote annulé.")
                return

    totp_code = input("➡️  Code TOTP (Google Authenticator) : ").strip()
    ok, error = badges.verify_badge_and_totp(current_user.user_id, header_id, totp_code)
    if not ok:
        print(f"❌ Authentification échouée : {error}")
        return

    print("   ✅ Identité vérifiée.\n")
    try:
        envelope = votes.cast_vote(selected_nonce.nonce, selected_vote.vote_id, answer_id)
        print("\n✅ Vote enregistré avec succès !")
        if selected_vote.vote_mode == "auditable":
            print(f"   🔍 Enveloppe #{envelope.envelope_id} liée à votre identité.")
        else:
            print(f"   🔒 Enveloppe #{envelope.envelope_id} enregistrée anonymement.")
        print(f"   🔗 Hash d'intégrité : {envelope.current_hash[:20]}...")
    except ValueError as e:
        print(f"❌ Erreur de validation : {e}")
    except Exception as e:
        print(f"❌ Erreur inattendue : {e}")


def _vote_results_manager(current_user) -> None:
    """C3 pour manager : dépouille uniquement les votes qu'il a créés."""
    try:
        all_votes = votes.get_all_votes()
    except Exception as e:
        print(f"❌ Erreur : {e}")
        return

    own_votes = [v for v in all_votes if v.creator_user_id == current_user.user_id]
    if not own_votes:
        print("📭 Vous n'avez créé aucun vote.")
        return

    print(f"\n📋 Vos votes :\n")
    for v in own_votes:
        status_emoji = "🟢" if v.vote_status == "open" else "🔴"
        print(f"  [{v.vote_id}] {status_emoji} {v.question}  ({v.vote_type} / {v.vote_mode})")

    vote_id_str = input("\n➡️  ID du vote à dépouiller : ").strip()
    try:
        vote_id = int(vote_id_str)
        if vote_id not in [v.vote_id for v in own_votes]:
            print("❌ Vote non trouvé parmi vos votes.")
            return
    except ValueError:
        print("❌ ID invalide.")
        return

    try:
        result = votes.count_results(vote_id)
    except ValueError as e:
        print(f"❌ {e}")
        return

    cli._print_vote_results(result)


# ---------------------------------------------------------------------------
# Dispatcher : code → action avec vérification de permission
# ---------------------------------------------------------------------------

def _dispatch(code: str, current_user) -> None:
    role = current_user.the_role

    # Pour manager, C3 est limité à ses propres votes
    c3_fn = (_vote_results_manager if role == "manager"
             else cli.show_vote_results_admin)

    actions: dict[str, tuple] = {
        "A1": (cli.list_all_users,               "users.list"),
        "A2": (lambda: cli.list_users(False),    "users.list"),
        "A3": (lambda: cli.list_users(True),     "users.list"),
        "A4": (cli.create_user,                  "users.create"),
        "A5": (cli.edit_user,                    "users.edit"),
        "A6": (cli.remove_user,                  "users.delete"),
        "B1": (cli.list_all_badges,              "badges.list"),
        "B2": (lambda: cli.list_badges(False),   "badges.list"),
        "B3": (lambda: cli.list_badges(True),    "badges.list"),
        "B4": (cli.edit_badge,                   "badges.revoke"),
        "C1": (cli.create_vote,                  "votes.create"),
        "C2": (cli.edit_vote,                    "votes.manage"),
        "C3": (c3_fn,                            "votes.results.all"
               if role != "manager" else "votes.results.own"),
        "C4": (cli.verify_integrity,             "votes.results.all"),
        "C5": (cli.list_ongoing_votes,           "votes.manage"),
        "C6": (cli.force_close_vote,             "votes.close"),
        "D1": (lambda: cli.fernet_key("totp.env"),   "keys.generate"),
        "D2": (lambda: cli.fernet_key("vote.env"),   "keys.generate"),
        "D3": (lambda: cli.fernet_key("answer.env"), "keys.generate"),
        "E1": (cli.show_logs,                    "logs.view"),
        "E2": (lambda: print("📊 Export SIEM — fonctionnalité à implémenter"), "logs.export"),
        "E3": (cli.backup_db,                    "logs.backup"),
        "F1": (lambda: _my_votes(current_user),                             "votes.results.own"),
        "F2": (lambda: _cast_vote(current_user),                            "votes.cast"),
        "F3": (lambda: cli.my_secret_shares(current_user),                  "secrets.view_own"),
        "G1": (lambda: cli.create_secret_split(current_user),               "secrets.split"),
        "G2": (lambda: cli.delete_secret(current_user),                     "secrets.delete"),
        "G3": (lambda: cli.reconstruct_secret_interactive(current_user),    "secrets.reconstruct"),
    }

    if code not in actions:
        print("⚠️  Action inconnue.")
        return

    fn, permission = actions[code]
    try:
        rbac.require_permission(role, permission)
    except PermissionError as e:
        print(f"🚫 {e}")
        return
    fn()


# ---------------------------------------------------------------------------
# Point d'entrée principal
# ---------------------------------------------------------------------------

def print_header() -> None:
    print("\n" + "═" * 80)
    print(" " * 25 + "🔐 AEGIS Secure Voting System")
    print(" " * 22 + "Prototype de démonstration de vote sécurisé")
    print("═" * 80)
    print(f"🕒  Démarrage à {datetime.now().strftime('%H:%M:%S')}\n")


def main(show_header: bool = True) -> None:
    if show_header:
        print_header()

    try:
        current_user = login()
    except ValueError as e:
        print(f"\n❌ {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n❌ Connexion annulée.")
        sys.exit(0)

    role = current_user.the_role
    print(f"✅ Connecté : '{current_user.username}'  [rôle : {role}]\n")

    allowed_codes = {code for code, _, perm in MENU_ITEMS
                     if rbac.has_permission(role, perm)}

    while True:
        available = _show_menu(role)

        choice = input("➡️  Votre choix : ").strip().upper()

        if choice == "0":
            print(f"\n🔐 Déconnexion de '{current_user.username}'. Au revoir !\n")
            sys.exit(0)

        if choice not in allowed_codes:
            print("⚠️  Choix invalide ou non autorisé pour votre rôle.\n")
            continue

        _dispatch(choice, current_user)
        print("\nAppuyez sur Entrée pour continuer...")
        input()


if __name__ == "__main__":
    main()

# AEGIS - NowBlackout ENSIBS 2025
# Last modified: 2025-27-10
# CLI Interface - Command Line Interface for AEGIS Application

import os
from pathlib import Path
from datetime import datetime
from datetime import date
import re

from aegis.services import users, badges, votes, utils

def create_user():
    """Interface CLI pour créer un nouvel utilisateur."""
    print("\n👤 Création d’un nouvel utilisateur...\n")
    user = None
    user_data = {}
    while True:
        name = input("➡️  Prénom : ").strip().lower()
        nom = input("➡️  Nom de famille : ").strip().lower()
        username = input("➡️  Nom d'utilisateur : ").strip().lower()
        email = input("➡️  Email : ").strip().lower()
        metier = input("➡️  Métier (par défaut) développeur: ").strip().lower()
        role = input("➡️  Rôle : (par défaut) membre : ").strip().lower()

        user_data = {
            "first_name": name,
            "last_name": nom,
            "username": username,
            "email": email,
            "job": metier if metier else "développeur",
            "the_role": role if role else "membre"
        }
    
        try:
            user = users.create_user(user_data)
            #print(f"Utilisateur créé avec l'ID {user.user_id}")
            print("✅"+"═" * 25 +f"Utilisateur '{user.username}' créé avec succès !\n"+"═" * 25)
            print("🪪 Récapitulation des informations ajoutées")
            print(f"  - Prénom : {user.first_name}")
            print(f"  - Nom de famille : {user.last_name}")
            print(f"  - Nom d'utilisateur : {user.username}")
            print(f"  - Email : {user.email}")
            print(f"  - Métier : {user.job}")
            print(f"  - Rôle : {user.the_role}\n")
            break
        except ValueError as e:
            print(f"Erreur de validation : {e}")
        except Exception as e:
            print(f"Erreur lors de la création : {e}")
            break

    try:
        new_user = users.get_user_by_username(user_data.get("username"))
    except Exception as e:
        print(f"Erreur lors de la récupération de l'utilisateur par son nom: {e}")
        return

    print("➡️  Maintenant, nous allons configurer le badge NFC pour cet utilisateur.")
    print("➡️  1 - Configuration du TOTP.")
    secret = badges.generate_totp_secret()
    print("➡️  Veuillez enregistrer ce secret dans votre application Google Authenticator :", secret)
    print("➡️  Un badge TOTP va être créé et attaché à l'utilisateur.")
    print("🚫   Ne partager ce secret à personne !")
    print("➡️  2 - Scan du badge NFC.")
    print("➡️  Veuillez scanner le badge NFC à l'aide du lecteur NFC...")
    header_id = 0
    while(header_id == 0):
        try:
            header_id = badges.get_header_id_from_nfc()
            print(f"➡️  Badge NFC scanné avec succès. Header ID : {header_id}")
        except RuntimeError as e:
            print(f"Erreur : {e}")
            return
    try:
        b = badges.create_badge(new_user.username, secret, header_id)
    except Exception as e:
        print(f"Erreur lors de la création du badge : {e}")
        return

    badges.attach_badge_to_user(b.badge_id, new_user.user_id)
    print(f"✅ Badge créé avec l'ID {b.badge_id} et attaché à l'utilisateur '{new_user.username}'.")
    print("✅ Utilisateur et badge configurés avec succès !")
    

def list_all_users():
    """Interface CLI pour lister les utilisateurs."""
    allusers = users.list_all_users()
    print(f"\n📋 Liste de tous les utilisateurs:\n")
    print("    - ID, Username, Name, Email, Job, Role, Badge ID")
    for user in allusers:
        print(f"    - {user[0].user_id}, {user[0].username}, {user[0].first_name}, {user[0].last_name}, {user[0].email}, {user[0].job}, {user[0].the_role}, {user[1]}")

    print("\n👤"+"═" * 30 +f" Total: {len(allusers)} utilisateurs dans la base "+"═" * 30)

def list_users(is_revoked: bool):
    """Interface CLI pour lister les utilisateurs."""
    allusers = users.list_users(is_revoked)
    status = "révoqués" if is_revoked else "actifs"
    emoji = "🚫" if is_revoked else "✅"
    print(f"\n {emoji} Liste des utilisateurs {status} :\n")
    print("  - ID, Username, Name, Email, Job, Role, Badge ID")
    for user in allusers:
        print(f"    - {user[0].user_id}, {user[0].username}, {user[0].first_name}, {user[0].last_name}, {user[0].email}, {user[0].job}, {user[0].the_role}, {user[1]}")

    print("\n👤"+"═" * 30 +f" Total: {len(allusers)} utilisateurs {status} dans la base "+"═" * 30)

def edit_user():
    """Interface CLI pour éditer un utilisateur."""
    list_all_users()
    username = input("➡️  Entrez le nom d'utilisateur de l'utilisateur à éditer : ").strip().lower()
    try:
        user = users.get_user_by_username(username)
        if not user:
            print(f"❌ Utilisateur '{username}' non trouvé.")
            return
    except Exception as e:
        print(f"Erreur lors de la récupération de l'utilisateur : {e}")
        return

    print(f"\n✏️  Édition de l'utilisateur '{username}'. Laissez vide pour conserver la valeur actuelle.\n")
    new_first_name = input(f"➡️  Prénom ({user.first_name}) : ").strip()
    new_last_name = input(f"➡️  Nom de famille ({user.last_name}) : ").strip()
    new_email = input(f"➡️  Email ({user.email}) : ").strip()
    new_job = input(f"➡️  Métier ({user.job}) : ").strip()
    new_role = input(f"➡️  Rôle ({user.the_role}) : ").strip()

    user_data = {
        "first_name": new_first_name if new_first_name else user.first_name,
        "last_name": new_last_name if new_last_name else user.last_name,
        "username": user.username,
        "email": new_email if new_email else user.email,
        "job": new_job if new_job else user.job,
        "the_role": new_role if new_role else user.the_role
    }

    try:
        updated_user = users.edit_user(user.user_id, user_data)
        print(f"✅ Utilisateur '{updated_user.username}' mis à jour avec succès !")
    except ValueError as e:
        print(f"Erreur de validation : {e}")
    except Exception as e:
        print(f"Erreur lors de la mise à jour : {e}")

def remove_user():
    """Interface CLI pour supprimer un utilisateur."""
    list_all_users()
    username = input("➡️  Entrez le nom d'utilisateur de l'utilisateur à supprimer : ").strip().lower()
    try:
        user = users.get_user_by_username(username)
        if not user:
            print(f"❌ Utilisateur '{username}' non trouvé.")
            return
    except Exception as e:
        print(f"Erreur lors de la récupération de l'utilisateur : {e}")
        return

    confirm = input(f"⚠️  Êtes-vous sûr de vouloir supprimer l'utilisateur '{username}' ? Cette action est irréversible. (oui/non) : ").strip().lower()
    if confirm not in ('oui', 'o', 'yes', 'y'):
        print("Abandon de la suppression de l'utilisateur.")
        return

    try:
        users.remove_user(user.user_id)
        print(f"✅ Utilisateur '{username}' supprimé avec succès !")
    except Exception as e:
        print(f"Erreur lors de la suppression de l'utilisateur : {e}")

def list_all_badges():
    """Interface CLI pour lister tous les badges."""
    allbadges = badges.list_all_badges()
    print(f"\n📋 Liste de tous les badges:\n")
    print("  - Badge ID, Username, Hash, Issued At, Expires At, Is Revoked, Reason, Updated At")
    for badge, username in allbadges:
        print(f"    - {badge.badge_id}, {username}, {badge.header_id}, {badge.issued_at}, {badge.expires_at}, {badge.is_revoked}, {badge.revoked_reason}, {badge.updated_at}")

    print("\n🪪"+"═" * 30 +f" Total: {len(allbadges)} badges dans la base "+"═" * 30)

def list_badges(is_revoked: bool):
    """Interface CLI pour lister les badges."""
    allbadges = badges.list_badges(is_revoked)
    status = "révoqués" if is_revoked else "actifs"
    emoji = "🚫" if is_revoked else "✅"
    print(f"\n {emoji} Liste des badges {status} :\n")
    print("  - Badge ID, Username, Hash, Issued At, Expires At, Is Revoked, Reason, Updated At")
    for badge, username in allbadges:
        print(f"    - {badge.badge_id}, {username}, {badge.header_id}, {badge.issued_at}, {badge.expires_at}, {badge.is_revoked}, {badge.revoked_reason}, {badge.updated_at}")

    print("\n🪪"+"═" * 30 +f" Total: {len(allbadges)} badges {status} dans la base "+"═" * 30)

def edit_badge():
    """Interface CLI pour éditer un badge."""
    list_all_badges()
    badge_id_input = input("➡️  Entrez l'ID du badge à éditer : ").strip()
    badge_id = None
    while badge_id is None:
        try:
            badge_id = int(badge_id_input)
        except ValueError:
            print("❌ ID de badge invalide.")
            return
    try:
        badge = badges.get_badge_by_id(badge_id)
        if not badge:
            print(f"❌ Badge avec l'ID '{badge_id}' non trouvé.")
            return
    except Exception as e:
        print(f"Erreur lors de la récupération du badge : {e}")
        return

    print(f"\n✏️  Édition du badge ID '{badge_id}'. Laissez vide pour conserver la valeur actuelle.\n")
    new_expires_at = input(f"➡️  Date d'expiration ({badge.expires_at}) [format YYYY-MM-DD] : ").strip()
    new_is_revoked = input(f"➡️  Est révoqué ({badge.is_revoked}) [oui/non] : ").strip().lower()
    new_revoked_reason = input(f"➡️  Raison de révocation ({badge.revoked_reason}) : ").strip()

    badge_data = {}
    if new_expires_at:
        badge_data["expires_at"] = new_expires_at
    if new_is_revoked in ('oui', 'o', 'yes', 'y'):
        badge_data["is_revoked"] = True
    elif new_is_revoked in ('non', 'n', 'no'):
        badge_data["is_revoked"] = False
    if new_revoked_reason:
        badge_data["revoked_reason"] = new_revoked_reason

    try:
        updated_badge = badges.edit_badge(badge.badge_id, badge_data)
        print(f"✅ Badge ID '{updated_badge.badge_id}' mis à jour avec succès !")
    except ValueError as e:
        print(f"Erreur de validation : {e}")
    except Exception as e:
        print(f"Erreur lors de la mise à jour : {e}")


def create_vote():
    import re
    from datetime import date
    
    while True:
        question = input("➡️ Question du vote : ").strip()
        description = input("➡️ Description (optionnel) : ").strip() or None
        vote_type = input("➡️ Type de vote (majorité / unanimité / minimum_requis) : ").strip()
        vote_mode = input("➡️ Mode de vote (auditable / confidentiel) : ").strip()
        k_required = None
        boolean = input("➡️ Est-ce que le vote est une question fermée ? (oui/non) : ").strip().lower() 
        is_boolean = boolean in ('oui', 'o', 'yes', 'y')
    
        if vote_type == "minimum_requis":
            try:
                k_required = int(input("➡️ k requis : "))
            except ValueError:
                print("⚠️ k requis doit être un nombre entier.")
                continue
    
        date_entry = ""
        regex = re.compile(r'^[0-9]{2}/[0-9]{2}/[0-9]{4}$')
        while not re.findall(regex, date_entry):
            date_entry = input("➡️ Enter une date d'expiration au format JJ/MM/AAAA (ex 27/04/2020): ").strip()
        day, month, year = map(int, date_entry.split('/'))
        try:
            expiration_date = date(year, month, day)
        except ValueError:
            print("⚠️ Date invalide. Veuillez recommencer.")
            continue
    
        vote_data = {
            "question": question,
            "description_text": description,
            "is_boolean": is_boolean,
            "creator_user_id": None,
            "vote_type": vote_type,
            "vote_mode": vote_mode,
            "is_active": True,
            "k_required": k_required,
            "expiration_date": expiration_date,
            "vote_status": "open"
        }
    
        try:
            vote = votes.create_vote(vote_data)
        except ValueError as e:
            print(f"Erreur de validation lors de la création du vote : {e}")
            print("Veuillez corriger les erreurs et recommencer.\n")
            continue  # redemande toute la saisie
        except Exception as e:
            print(f"Erreur inattendue lors de la création du vote : {e}")
            print("Veuillez réessayer.\n")
            continue
    
        # Si on arrive ici, la création a réussi
        break
    
    print("\n✅ Vote créé avec succès")
    print(f"🆔 Vote ID : {vote.vote_id}")
    
    if is_boolean:
        anwsers = []
        while True:
            answer_text = input("➡️ Entrez une option de réponse (ou tapez 'fin' pour terminer) : ").strip()
            if answer_text.lower() == 'fin':
                break
            anwsers.append(answer_text)
            print(f"✅ Option de réponse '{answer_text}' ajoutée.")
        print("📝 Options de réponse ajoutées :")
        for a in anwsers:
            print(f" - {a}")
        try:
            votes.add_answers_to_vote(vote.vote_id, anwsers)
            print("✅ Réponses enregistrées avec succès.")
        except ValueError as e:
            print(f"Erreur de validation lors de l'enregistrement des réponses : {e}")
        except Exception as e:
            print(f"Erreur lors de l'enregistrement des réponses : {e}") 
    affecte_vote(vote.vote_id)
    print("✅ Vote affecté aux utilisateurs avec droit de vote.")   

# def affecte_vote(vote_id: int):
#     """Affecte le vote à tous les utilisateurs ayant le droit de vote."""
#     try:
#         users_with_vote_right = users.get_users_who_can_vote()
#         for user in users_with_vote_right:
#             votes.assign_vote_to_user(vote_id, user.user_id)
#         print(f"✅ Vote ID {vote_id} affecté à {len(users_with_vote_right)} utilisateurs.")
#     except Exception as e:
#         print(f"Erreur lors de l'affectation du vote aux utilisateurs : {e}")

def fernet_key(the_file: str):
    """Interface CLI pour générer une clé Fernet pour les TOTP, les VOTES et les ANSWERS."""
    secrets_dir = Path("aegis/secrets")
    secrets_file = secrets_dir / the_file

    print("🔑 Génération de la clé fernet")
    key = utils.generate_fernet_key()
    

    # Crée le dossier secrets s'il n'existe pas
    secrets_dir.mkdir(parents=True, exist_ok=True)

    # Si le fichier existe déjà, avertir l'utilisateur avant d'écraser
    if secrets_file.exists():
        print(f"⚠️ Le fichier {secrets_file} existe déjà.")
        if the_file == "totp.env":
            print("⚠️ Si vous vous l'écrasez, vous ne pourrez plus badger avec les utilisateurs actuels.")
        elif the_file == "vote.env":
            print("⚠️ Vous ne pourrez plus égaller dépouiller les votes confidentiels existants.")
        elif the_file == "answer.env":
            print("⚠️ Vous ne pourrez plus déchiffrer les réponses confidentielles existantes.")

        confirm = input("Voulez-vous écraser la clé existante ? (oui/non) : ").strip().lower()
        if confirm not in ('oui', 'o', 'yes', 'y'):
            print("Abandon de la génération de la clé.")
            return

    # Écriture de la clé dans le fichier au format .env
    with secrets_file.open("w", encoding="utf-8") as f:
        if the_file == "totp.env":
            string = "# AEGIS - NowBlackout ENSIBS 2025\n# File: AEGIS/aegis/secrets/totp.env\n# ENV - Store secret key for badge encryption\n\n# CHANGE DEFAULT KEY BEFOR DEPLOYMENT\nFERNET_TOTP_KEY="
        elif the_file == "vote.env":
            string = "# AEGIS - NowBlackout ENSIBS 2025\n# File: AEGIS/aegis/secrets/vote.env\n# ENV - Store secret key for user vote choice encryption in confidental mode\n\n# CHANGE DEFAULT KEY BEFOR DEPLOYMENT\nFERNET_VOTE_KEY="
        elif the_file == "answer.env":
            string = "# AEGIS - NowBlackout ENSIBS 2025\n# File: AEGIS/aegis/secrets/answer.env\n# ENV - Store secret key for user answer encryption in confidental mode\n\n# CHANGE DEFAULT KEY BEFOR DEPLOYMENT\nFERNET_ANSWER_KEY="
        f.write(string+key+"\n")

    print(f"➡️  Clé Fernet générée et sauvegardée dans {secrets_file}.")
    print("⚠️ Veuillez sauvegarder cette clé en lieu sûr. Elle est nécessaire pour le chiffrement et le déchiffrement des données.")

if __name__ == "__main__":
    #ac_setup()
    create_user()

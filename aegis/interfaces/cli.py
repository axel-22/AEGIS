# AEGIS - NowBlackout ENSIBS 2025
# Last modified: 2025-27-10
# CLI Interface - Command Line Interface for AEGIS Application

import os
from pathlib import Path

from aegis.services import users, badges

def create_user():
    """Interface CLI pour créer un nouvel utilisateur."""
    name = input("➡️  Prénom : ").strip().lower()
    nom = input("➡️  Nom de famille : ").strip().lower()
    username = input("➡️  Nom d'utilisateur : ").strip().lower()
    email = input("➡️  Email : ").strip().lower()
    vote_input = input("➡️  Peut voter ? (oui/non) (par défaut) oui : ").strip().lower()
    metier = input("➡️  Métier (par défaut) développeur: ").strip().lower()
    role = input("➡️  Rôle : (par défaut) membre : ").strip().lower()

    user_data = {
        "first_name": name,
        "last_name": nom,
        "username": username,
        "email": email,
        "can_vote": vote_input != "non",
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
        print(f"  - Peut voter : {user.can_vote}")
        print(f"  - Métier : {user.job}")
        print(f"  - Rôle : {user.the_role}\n")
    except ValueError as e:
        print(f"Erreur de validation : {e}")
    except Exception as e:
        print(f"Erreur lors de la création : {e}")

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
    

def list_users(is_revoked: bool):
    """Interface CLI pour lister les utilisateurs."""
    allusers = users.list_users(is_revoked)
    status = "révoqués" if is_revoked else "actifs"
    print(f"\n📋 Liste des utilisateurs {status} :\n")
    for user in allusers:
        print(f"  - ID: {user.user_id}, Username: {user.username}, Name: {user.first_name} {user.last_name}, Email: {user.email}, Can Vote: {user.can_vote}, Job: {user.job}, Role: {user.the_role}")

    print("\n👤"+"═" * 30 +f" Total: {len(allusers)} utilisateurs {status} dans la base "+"═" * 30)


def fernet_key():
    """Interface CLI pour générer une clé Fernet et sauvegarder dans secrets.env"""
    secrets_dir = Path("aegis/secrets")
    secrets_file = secrets_dir / "secrets.env"

    print("🔑 Génération d'une clé Fernet")
    key = badges.generate_fernet_key()

    # Crée le dossier secrets s'il n'existe pas
    secrets_dir.mkdir(parents=True, exist_ok=True)

    # Si le fichier existe déjà, avertir l'utilisateur avant d'écraser
    if secrets_file.exists():
        print(f"⚠️ Le fichier {secrets_file} existe déjà.")
        print("⚠️ Si vous vous l'écrasez, vous ne pourrez plus badger avec les utilisateurs actuels.")
        confirm = input("Voulez-vous écraser la clé existante ? (oui/non) : ").strip().lower()
        if confirm not in ('oui', 'o', 'yes', 'y'):
            print("Abandon de la génération de la clé.")
            return

    # Écriture de la clé dans le fichier au format .env
    with secrets_file.open("w", encoding="utf-8") as f:
        f.write(f"FERNET_KEY={key}\n")

    print(f"➡️  Clé Fernet générée et sauvegardée dans {secrets_file}")
    print("⚠️ Veuillez sauvegarder cette clé en lieu sûr. Elle est nécessaire pour le chiffrement et le déchiffrement des données.")
    print("👉 Pensez à modifier la clé si vous réutilisez un ancien fichier secrets.env.")


if __name__ == "__main__":
    #ac_setup()
    create_user()

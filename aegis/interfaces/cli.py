# AEGIS - NowBlackout ENSIBS 2025
# Last modified: 2025-27-10
# CLI Interface - Command Line Interface for AEGIS Application

from aegis.services import users

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
        print(f"Utilisateur créé avec l'ID {user.id}")
    except ValueError as e:
        print(f"Erreur de validation : {e}")
    except Exception as e:
        print(f"Erreur lors de la création : {e}")
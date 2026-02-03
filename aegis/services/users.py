# AEGIS - NowBlackout ENSIBS 2025
# Last modified: 2025-27-10
# Users Service - Manage all user-related operations

import re
from datetime import datetime

import aegis.core._database as db
from aegis.core._models import USERS, BADGES, SECRETS, ENVELOPES

MAX_LEN = 50

db.set_debug(False)

def is_valid_email(email: str) -> bool:
    """Vérifie si l'email est dans un format valide."""
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    if(re.match(pattern, email) and len(email) <= MAX_LEN):
        return True
    return False

def is_valid_username(username: str) -> bool:
    """
    Vérifie si le nom d'utilisateur est valide :
    - Contient uniquement lettres (accentuées), chiffres, underscores et points
    - Pas d'espaces ou autres caractères spéciaux
    """
    pattern = r"^[A-Za-z0-9_.À-ÖØ-öø-ÿ]+$"
    if(re.match(pattern, username) and len(username) <= MAX_LEN):
        return True
    return False

def is_valid_name(name: str) -> bool:
    """
    Vérifie si le prénom est valide :
    - Contient uniquement lettres (accentuées), apostrophes et tirets
    - Pas d'espaces, chiffres ou autres caractères spéciaux
    """
    pattern = r"^[A-Za-zÀ-ÖØ-öø-ÿ'’-]+$"
    if(re.match(pattern, name) and len(name) <= MAX_LEN):
        return True
    return False
        
def create_user(user_data: dict) -> 'USERS':
    """Vérifier qu'un utilisateur contient bien toutes les données nécessaire."""

    firstname = user_data.get("first_name").capitalize()
    if not firstname or not is_valid_name(firstname):
        raise ValueError("Prénom invalide. Utilisez uniquement des lettres, apostrophes et tirets.")
        
    lastname = user_data.get("last_name").capitalize()
    if not lastname or not is_valid_name(lastname):
        raise ValueError("Nom de famille invalide. Utilisez uniquement des lettres, apostrophes et tirets.")
    
    email = user_data.get("email")
    username = user_data.get("username")
    if email and not is_valid_email(email):
        raise ValueError("Format d'email invalide.")

    the_username = db.select_user_by_username(user_data.get("username"))
    if the_username:
        raise ValueError("Nom d'utilisateur déjà existant. Veuillez en choisir un autre.")

    if verify_username := is_valid_username(username) == False:
        raise ValueError("Nom d'utilisateur invalide. Utilisez uniquement des lettres, chiffres, underscores et points.")   
    
    if user_data.get("the_role") not in ["superadmin", "admin", "member"]:
        raise ValueError("Rôle utilisateur invalide. Choisissez parmi : superadmin, admin, member.")
        
    new_user = USERS(
            first_name=user_data["first_name"],
            last_name=user_data["last_name"],
            username=user_data["username"],
            email=user_data["email"],
            job=user_data["job"],
            the_role=user_data["the_role"]
        )
    try:
        db.insert_user(new_user)
    except Exception as e:
        raise e
    return new_user

def list_users(is_revoked: bool) -> list[tuple['USERS', int]]:
    """Lister les utilisateurs actifs ou révoqués."""
    try:
        users_list = db.select_users(is_revoked)
    except Exception as e:
        raise e
    return users_list

def list_all_users() -> list[tuple['USERS', int]]:
    """Lister les utilisateurs actifs ou révoqués."""
    try:
        users_list = db.select_all_users()
    except Exception as e:
        raise e
    return users_list

def get_user_by_username(username: str) -> 'USERS':
    """Récupérer un utilisateur par son nom d'utilisateur."""
    try:
        user = db.select_user_by_username(username)
    except Exception as e:
        raise e
    return user

def get_user_by_id(user_id: int) -> 'USERS':
    """Récupérer un utilisateur par son ID."""
    try:
        user = db.select_user_by_id(user_id)
    except Exception as e:
        raise e
    return user

def edit_user(user_id: int, user_data: dict) -> 'USERS':
    """Éditer un utilisateur existant."""
    firstname = user_data.get("first_name").capitalize()
    if not firstname or not is_valid_name(firstname):
        raise ValueError("Prénom invalide. Utilisez uniquement des lettres, apostrophes et tirets.")
        
    lastname = user_data.get("last_name").capitalize()
    if not lastname or not is_valid_name(lastname):
        raise ValueError("Nom de famille invalide. Utilisez uniquement des lettres, apostrophes et tirets.")
    
    email = user_data.get("email")
    username = user_data.get("username")
    if email and not is_valid_email(email, username):
        raise ValueError("Format d'email invalide.")

    try:
        updated_user = db.update_user(user_id, user_data)
    except Exception as e:
        raise e
    return updated_user

def remove_user(user_id: int) -> None:
    """Supprimer un utilisateur en anonymisant ses données et en révoquant son badge."""
    session = db.get_session()

    user = db.select_user_with_badge_by_user_id(user_id,session=session)
    uid = user.user_id
    if not user:
        raise ValueError(f"Utilisateur {user_id} non trouvé")

    # Révoquer le badge s'il existe
    if user.BADGES:
        badge = user.BADGES
        badge.is_revoked = True
        badge.revoked_at = datetime.utcnow()
        badge.revoked_reason = "USER_DELETED"

    try:
        user.username = f"deleted_user_{user.user_id}"
        user.first_name = "Deleted"
        user.last_name = "User"
        user.email = None
        user.job = None
        user.the_role = None
        user.updated_at = datetime.utcnow()

        session.commit()
    except Exception as e:
        session.rollback()
        raise Exception(f"Erreur lors de la suppression de l'utilisateur : {e}")
    finally:
        session.close()
    try:
        db.delete_secrets(uid)
        db.delete_envelopes(uid)
    except Exception as e:
        raise Exception(f"Erreur lors de la suppression des données associées : {e}")
    

if __name__ == "__main__":
    test_user =  {
        "first_name": "Test",
        "last_name":"User",
        "username":"testuser",
        "email":"test@example.com",
        "can_vote":True,
        "job":"tester",
        "the_role":"membre"
    }
    create_user(test_user)
    #print(list_users(False))
    
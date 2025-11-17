# AEGIS - NowBlackout ENSIBS 2025
# Last modified: 2025-27-10
# Users Service - Manage all user-related operations

import re

import aegis.core._database as db
from aegis.core._models import USERS

MAX_LEN_USERNAME = 50

db.set_debug(False)

def is_valid_email(email: str, username: str) -> bool:
    """Vérifie si l'email est dans un format valide."""
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    if(re.match(pattern, email) and len(username) <= MAX_LEN_USERNAME):
        return True
    return False

def is_valid_name(name: str) -> bool:
    """
    Vérifie si le prénom est valide :
    - Contient uniquement lettres (accentuées), apostrophes et tirets
    - Pas d'espaces, chiffres ou autres caractères spéciaux
    """
    pattern = r"^[A-Za-zÀ-ÖØ-öø-ÿ'’-]+$"
    if(re.match(pattern, name) and len(name) <= MAX_LEN_USERNAME):
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
    if email and not is_valid_email(email, username):
        raise ValueError("Format d'email invalide.")

    the_username = db.select_user_by_username(user_data.get("username"))
    if the_username:
        raise ValueError("Nom d'utilisateur déjà existant. Veuillez en choisir un autre.")

    new_user = USERS(
            first_name=user_data["first_name"],
            last_name=user_data["last_name"],
            username=user_data["username"],
            email=user_data["email"],
            can_vote=user_data["can_vote"],
            job=user_data["job"],
            the_role=user_data["the_role"]
        )
    try:
        db.insert_user(new_user)
    except Exception as e:
        raise e
    return new_user

def list_users(is_revoked: bool) -> list['USERS']:
    """Lister les utilisateurs actifs ou révoqués."""
    try:
        users_list = db.select_users(is_revoked)
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
    
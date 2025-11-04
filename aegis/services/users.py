# AEGIS - NowBlackout ENSIBS 2025
# Last modified: 2025-27-10
# Users Service - Manage all user-related operations

import re

from aegis.core._database import *
from aegis.core._models import USERS

MAX_LEN_USERNAME = 50

def is_valid_email(email: str) -> bool:
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
    if not firstname or not is_valid_name(firtname):
        raise ValueError("Prénom invalide. Utilisez uniquement des lettres, apostrophes et tirets.")
        
    lastname = user_data.get("last_name").capitalize()
    if not lastname or not is_valid_name(lastname):
        raise ValueError("Nom de famille invalide. Utilisez uniquement des lettres, apostrophes et tirets.")
    
    email = user_data.get("email")
    if email and not is_valid_email(email):
        raise ValueError("Format d'email invalide.")

    new_user = USERS(
            first_name=user_data["first_name"],
            last_name=user_data["last_name"],
            username=user_data["username"],
            email=user_data["email"],
            can_vote=user_data["can_vote"],
            job=user_data.["job"],
            the_role=user_data["the_role"]
        )
    try:
        insert_user(new_user)
    except Exception as e:
        session.rollback()
        raise e
    return new_user


if __name__ == "__main__":
    test_user = USERS(
        first_name="Test",
        last_name="User",
        username="testuser",
        email="test@example.com",
        can_vote=True,
        job="tester",
        the_role="membre"
    )
    insert_user(test_user)
    
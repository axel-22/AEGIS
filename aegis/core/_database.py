# AEGIS - NowBlackout ENSIBS 2025
# Last modified: 2025-27-10
# First login to the database and testing the process

import sqlite3
from pathlib import Path
from datetime import datetime

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import joinedload

from aegis.core._models import Base, USERS, BADGES, SECRETS, ENVELOPES



DB_PATH = Path("aegis.db")

DEBUG = False  # valeur par défaut
SessionLocal = None
engine = None

def set_debug(state: bool):
    global DEBUG, engine, SessionLocal
    DEBUG = state
    engine = create_engine(f"sqlite:///{DB_PATH}", echo=DEBUG)
    SessionLocal = sessionmaker(bind=engine)
    if DEBUG:
        print(f"🔧 SQLAlchemy debug mode = {DEBUG}")

def init_db():
    """
    Crée les tables à partir des modèles SQLAlchemy.
    """
    if engine is None:
        raise RuntimeError("Engine non initialisé. Appelle init_engine() avant init_db().")

    Base.metadata.create_all(bind=engine)

    if DEBUG:
        print("🗄️  Base de données SQLite initialisée")

def get_session():
    """Renvoie une nouvelle session SQLAlchemy."""
    return SessionLocal()

# Connexion sqlite3 native
def get_sqlite3_conn():
    conn = sqlite3.connect(DB_PATH)
    return conn

def raw_query_with_sqlite3():
    conn = get_sqlite3_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM USERS;")
        results = cursor.fetchall()
    except sqlite3.OperationalError as e:
        results = f"Erreur SQL: {e}"
    conn.close()
    return results

def query_with_sqlalchemy():
    session = get_session()
    try:
        result = session.execute(text("SELECT * FROM USERS;")).fetchall()
    except Exception as e:
        result = f"Erreur SQLAlchemy: {e}"
    finally:
        session.close()
    return result

def insert_user(user: 'USERS' ) -> 'USERS':
    session = get_session()
    try:
        session.add(user)
        session.commit()
        session.refresh(user)
        session.expunge(user) 
        return user
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def select_users(is_revoked: bool) -> list[tuple['USERS', int]]:
    """
    Lister les utilisateurs avec l'id de leur badge
    (révoqué ou actif selon is_revoked)
    """
    session = get_session()
    try:
        results = (
            session.query(USERS, BADGES.badge_id)
            .join(BADGES, BADGES.the_user == USERS.user_id)
            .filter(BADGES.is_revoked == is_revoked)
            .all()
        )
        return results
    except Exception:
        raise
    finally:
        session.close()

def select_all_users() -> list[tuple['USERS', int]]:
    """
    Lister tous les utilisateurs avec leurs badges associés
    """
    session = get_session()
    try:
        results = (
            session.query(USERS, BADGES.badge_id)
            .outerjoin(BADGES, BADGES.the_user == USERS.user_id)
            .all()
        )
        return results
    except Exception as e:
        raise e
    finally:
        session.close()


def select_user_by_username(username: str) -> 'USERS':
    """Récupérer un utilisateur par son nom d'utilisateur."""
    session = get_session()
    try:
        user = session.query(USERS).filter(USERS.username == username).first()
        return user
    except Exception as e:
        raise e
    finally:
        session.close()

def select_user_with_badge_by_user_id(user_id: int, session=None) -> 'USERS':
    close_session = False
    if session is None:
        session = get_session()
        close_session = True
    try:
        user = session.query(USERS).options(joinedload(USERS.BADGES)).filter(USERS.user_id == user_id).one_or_none()
        return user
    finally:
        if close_session:
            session.close()

def delete_secrets(user_id: int):
    session = get_session()
    try:
        session.query(SECRETS).filter(SECRETS.creator_user_id == user_id).delete(synchronize_session=False)
        session.commit()
    finally:
        session.close()

def delete_envelopes(user_id: int):
    session = get_session()
    try:
        session.query(ENVELOPES).filter(ENVELOPES.the_user == user_id).delete(synchronize_session=False)
        session.commit()
    finally:
        session.close()

def insert_badge(badge: 'BADGES') -> 'BADGES':
    session = get_session()
    try:
        session.add(badge)
        session.commit()
        session.refresh(badge)
        return badge
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def assign_badge_to_user(badge_id, user_id):
    session = get_session()
    try:
        badge = session.get(BADGES, badge_id)
        badge.the_user = user_id
        session.commit()
    except:
        session.rollback()
        raise RuntimeError("Erreur lors de l'assignation du badge à l'utilisateur.")
    finally:
        session.close()

def update_user(user_id: int, user_data: dict) -> 'USERS':
    """Éditer un utilisateur existant."""
    session = get_session()
    try:
        user = session.get(USERS, user_id)
        for key, value in user_data.items():
            setattr(user, key, value)
        session.commit()
        session.refresh(user)
        return user
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

if __name__ == "__main__":
    # Initialisation DB via SQLAlchemy
    set_debug(True)
    init_db()

    # Test requête sqlite3 native
    print("Résultat sqlite3 natif:")
    print(raw_query_with_sqlite3())

    # Test requête SQLAlchemy
    print("Résultat SQLAlchemy:")
    print(query_with_sqlalchemy())

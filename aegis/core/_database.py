# AEGIS - NowBlackout ENSIBS 2025
# Last modified: 2025-27-10
# First login to the database and testing the process

import sqlite3
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from aegis.core._models import Base, USERS, BADGES


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

def get_session():
    """Renvoie une nouvelle session SQLAlchemy."""
    return SessionLocal()

# Connexion sqlite3 native
def get_sqlite3_conn():
    conn = sqlite3.connect(DB_PATH)
    return conn

# Connexion SQLAlchemy
def init_db():
    Base.metadata.create_all(bind=engine)
    print("Base de données initialisée avec SQLAlchemy.")

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

    


def select_users(is_revoked: bool) -> list['USERS']:
    """Lister les utilisateurs actifs ou révoqués."""
    session = get_session()
    try:
        if is_revoked:
            users = session.query(USERS).filter(USERS.can_vote == False ).all()
        else:
            users = session.query(USERS).filter(USERS.can_vote == True).all()
        return users
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
        badge.owner_id = user_id
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()



if __name__ == "__main__":
    # Initialisation DB via SQLAlchemy
    init_db()

    # Test requête sqlite3 native
    print("Résultat sqlite3 natif:")
    print(raw_query_with_sqlite3())

    # Test requête SQLAlchemy
    print("Résultat SQLAlchemy:")
    print(query_with_sqlalchemy())

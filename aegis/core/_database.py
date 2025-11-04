# AEGIS - NowBlackout ENSIBS 2025
# Last modified: 2025-27-10
# First login to the database and testing the process

import sqlite3
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from aegis.core._models import Base


DB_PATH = Path("aegis.db")

# Connexion sqlite3 native
def get_sqlite3_conn():
    conn = sqlite3.connect(DB_PATH)
    return conn

# Connexion SQLAlchemy
engine = create_engine(f"sqlite:///{DB_PATH}", echo=True)
SessionLocal = sessionmaker(bind=engine)

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
    session = SessionLocal()
    try:
        result = session.execute(text("SELECT * FROM USERS;")).fetchall()
    except Exception as e:
        result = f"Erreur SQLAlchemy: {e}"
    finally:
        session.close()
    return result

def insert_user(user: 'USERS' ):
    session = SessionLocal()
    try:
        session.add(user)
        session.commit()
        return user
    except Exception as e:
        session.rollback()
        raise e
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

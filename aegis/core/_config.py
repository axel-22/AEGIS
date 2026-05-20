# AEGIS - NowBlackout ENSIBS 2025
# Configuration centrale — variables d'environnement non secrètes
#
# Variables secrètes (clés Fernet) → aegis/secrets/*.env  (chargées par dotenv dans leurs services)
# Ce fichier est le seul endroit où os.getenv est appelé pour la config applicative.

import os
import secrets as _secrets

# --- API Flask ---
API_HOST         = os.getenv("AEGIS_API_HOST", "0.0.0.0")
API_PORT         = int(os.getenv("AEGIS_API_PORT", 5001))
API_DEBUG        = os.getenv("AEGIS_API_DEBUG", "false").lower() == "true"
FLASK_SECRET_KEY = os.getenv("AEGIS_SECRET_KEY") or _secrets.token_hex(32)

# --- Base de données ---
DB_PATH          = os.getenv("AEGIS_DB_PATH", "aegis.db")
SQLALCHEMY_DEBUG = os.getenv("AEGIS_SQLALCHEMY_DEBUG", "false").lower() == "true"

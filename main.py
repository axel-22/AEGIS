# AEGIS - NowBlackout ENSIBS 2025
# Point d'entrée principal — authentification NFC+TOTP + RBAC
# Pour l'accès admin sans authentification : python admin.py

import logging
import threading
import time

from aegis.interfaces.cli_login import main, print_header
from aegis.core._config import API_HOST, API_PORT, API_DEBUG


def _start_api():
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    from aegis.interfaces.api import app
    from aegis.core._logger import get_logger
    log = get_logger("api")
    try:
        app.run(host=API_HOST, port=API_PORT, debug=API_DEBUG, use_reloader=False)
    except Exception as e:
        log.error(f"API REST arrêtée de façon inattendue : {e}")


if __name__ == "__main__":
    print_header()

    print("🌐  Démarrage de l'API REST...", end="", flush=True)
    api_thread = threading.Thread(target=_start_api, daemon=True, name="aegis-api")
    api_thread.start()
    time.sleep(0.8)
    print(f"  ✅ En écoute sur le port {API_PORT}\n")

    main(show_header=False)

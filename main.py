# AEGIS - NowBlackout ENSIBS 2025
# Point d'entrée principal — authentification NFC+TOTP + RBAC
# Pour l'accès admin sans authentification : python admin.py

from aegis.interfaces.cli_login import main

if __name__ == "__main__":
    main()

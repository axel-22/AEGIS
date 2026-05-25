#!/bin/bash
set -e

REPO_DIR="/opt/aegis"
PACKAGES_FILE="$REPO_DIR/packages.txt"

echo "=== Mise à jour de l'index apt ==="
apt-get update -qq

if [ ! -f "$PACKAGES_FILE" ]; then
    echo "Pas de fichier packages.txt, rien à installer."
    exit 0
fi

echo "=== Lecture de packages.txt ==="

while IFS= read -r line || [ -n "$line" ]; do
    line=$(echo "$line" | xargs)
    [ -z "$line" ] && continue
    [[ "$line" =~ ^# ]] && continue

    echo ">>> Traitement de : $line"

    if [[ "$line" == *"="* ]]; then
        PKG_NAME="${line%%=*}"
        PKG_VERSION="${line#*=}"
        INSTALLED_VERSION=$(dpkg-query -W -f='${Version}' "$PKG_NAME" 2>/dev/null || echo "")

        if [ "$INSTALLED_VERSION" = "$PKG_VERSION" ]; then
            echo "    Déjà installé en version $PKG_VERSION, on passe."
            continue
        fi

        echo "    Installation de $PKG_NAME version $PKG_VERSION..."
        apt-get install -y --allow-downgrades "$PKG_NAME=$PKG_VERSION"
    else
        PKG_NAME="$line"
        if dpkg -s "$PKG_NAME" >/dev/null 2>&1; then
            echo "    Déjà installé, vérification d'une mise à jour..."
            apt-get install -y --only-upgrade "$PKG_NAME"
        else
            echo "    Installation de $PKG_NAME (dernière version)..."
            apt-get install -y "$PKG_NAME"
        fi
    fi
done < "$PACKAGES_FILE"

echo "=== Tous les paquets sont à jour ==="

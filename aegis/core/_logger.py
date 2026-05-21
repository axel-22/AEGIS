# AEGIS - NowBlackout ENSIBS 2025
# Logger - Système de journalisation centralisé
#
# Format : DD/MM/YYYY HH:MM:SS.cccc | LEVEL   | service      | message
# Fichier : aegis.log (racine du projet)

import logging
import os
from datetime import datetime
from pathlib import Path

_LOG_FILE = Path("aegis.log")
_initialized_loggers: set[str] = set()


class _AegisFormatter(logging.Formatter):
    LEVEL_COLORS = {
        "DEBUG":    "\033[37m",    # gris
        "INFO":     "\033[32m",    # vert
        "WARNING":  "\033[33m",    # jaune
        "ERROR":    "\033[31m",    # rouge
        "CRITICAL": "\033[35m",    # magenta
    }
    RESET = "\033[0m"

    def _timestamp(self, record: logging.LogRecord) -> str:
        dt = datetime.fromtimestamp(record.created)
        cs = dt.microsecond // 10000  # centièmes de seconde → 2 chiffres, on affiche sur 4
        return dt.strftime("%d/%m/%Y %H:%M:%S") + f".{dt.microsecond // 100:04d}"

    def format(self, record: logging.LogRecord) -> str:
        ts      = self._timestamp(record)
        level   = record.levelname.ljust(8)
        service = record.name.replace("aegis.", "").ljust(12)
        return f"{ts} | {level} | {service} | {record.getMessage()}"


class _AegisColorFormatter(_AegisFormatter):
    """Variante couleur pour la sortie console (optionnel)."""
    def format(self, record: logging.LogRecord) -> str:
        line  = super().format(record)
        color = self.LEVEL_COLORS.get(record.levelname, "")
        return f"{color}{line}{self.RESET}"


def get_logger(service_name: str) -> logging.Logger:
    """
    Retourne un logger nommé 'aegis.<service_name>'.
    Le handler fichier n'est ajouté qu'une seule fois par service.
    """
    full_name = f"aegis.{service_name}"
    logger = logging.getLogger(full_name)

    if full_name in _initialized_loggers:
        return logger

    logger.setLevel(logging.DEBUG)
    logger.propagate = False  # ne pas remonter au root logger

    # Handler fichier (toujours actif)
    fh = logging.FileHandler(_LOG_FILE, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(_AegisFormatter())
    logger.addHandler(fh)

    _initialized_loggers.add(full_name)
    return logger


def read_recent_logs(n: int = 50) -> list[str]:
    """Retourne les n dernières lignes de aegis.log."""
    if not _LOG_FILE.exists():
        return []
    with _LOG_FILE.open("r", encoding="utf-8") as f:
        lines = f.readlines()
    return [l.rstrip() for l in lines[-n:]]

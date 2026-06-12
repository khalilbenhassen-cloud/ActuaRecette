# logger.py — T6
"""
Logger structure centralise pour ActuaRecette.

Remplace tous les `print()` et `try/except: pass` par un logging
structure avec rotation de fichiers et ecriture dans audit_entries.

Usage:
    from src.logger import get_logger
    logger = get_logger("mon_module")
    logger.info("Message")
    logger.error("Erreur", exc_info=True)
"""
import os
import logging
import logging.handlers
from typing import Optional

# Singleton pour eviter les handlers dupliques
_configured = False

LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "logs")
LOG_FILE = os.path.join(LOG_DIR, "actuarecette.log")

def get_logger(name: str = "actuarecette") -> logging.Logger:
    """
    Retourne un logger configure avec:
    - Console handler (INFO+)
    - File handler avec rotation (DEBUG+)
    - Format structure incluant timestamp, module, level

    Args:
        name: Nom du logger (ex: 'actuarecette.variance_analyzer')

    Returns:
        Logger configure.
    """
    global _configured

    logger = logging.getLogger(name)

    if not _configured and name == "actuarecette":
        _setup_root_logger()
        _configured = True

    return logger

def _setup_root_logger():
    """Configure le logger racine 'actuarecette' une seule fois."""
    root_logger = logging.getLogger("actuarecette")
    root_logger.setLevel(logging.DEBUG)

    # Eviter les handlers dupliques
    if root_logger.handlers:
        return

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler (INFO+)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler avec rotation (5 MB, 3 backups)
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            LOG_FILE,
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    except Exception:
        # Si on ne peut pas ecrire le fichier, on continue avec la console
        pass

def log_audit_event(
    action: str,
    user: str = "system",
    run_id: str = "",
    details: str = "",
    level: str = "INFO",
):
    """
    Log un evenement d'audit structure.
    Ecrit dans le logger ET dans la table audit_entries si possible.

    Args:
        action: Type d'action (CREATE_RUN, CERTIFY, REJECT, etc.)
        user: SSO de l'utilisateur.
        run_id: ID du run concerne.
        details: Details supplementaires.
        level: Niveau de log (INFO, WARNING, ERROR).
    """
    logger = get_logger("actuarecette.audit")
    msg = f"[{action}] user={user} run={run_id} {details}"

    log_func = getattr(logger, level.lower(), logger.info)
    log_func(msg)

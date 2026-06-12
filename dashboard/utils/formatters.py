# formatters.py - Formatage tabular-nums pour ActuaRecette v6.0
# Conventions typographiques actuarielles (cf. Design Spec \u00a73.4)
#
# Tous les nombres, dates et devises passent par ce module
# pour garantir un rendu coh\u00e9rent en tabular figures.

from typing import Optional

def fmt_pct(value: float, decimals: int = 2) -> str:
    """
    Formate un pourcentage avec s\u00e9parateur d\u00e9cimal fran\u00e7ais.
    Ex: 97.0 \u2192 \"97,00 %\"
    """
    if value is None:
        return "\u2014"
    return f"{value:,.{decimals}f}\u00a0%".replace(",", "\u00a0").replace(".", ",")

def fmt_euro(value: float, decimals: int = 2) -> str:
    """
    Formate un montant en euros avec espace ins\u00e9cable comme s\u00e9parateur de milliers.
    Ex: 12345.67 \u2192 \"12\u00a0345,67 \u20ac\"
    """
    if value is None:
        return "\u2014"
    formatted = f"{value:,.{decimals}f}".replace(",", "\u00a0").replace(".", ",")
    return f"{formatted}\u00a0\u20ac"

def fmt_number(value: float, decimals: int = 0) -> str:
    """
    Formate un nombre entier ou d\u00e9cimal avec s\u00e9parateur de milliers.
    Ex: 1234 \u2192 \"1\u00a0234\"
    """
    if value is None:
        return "\u2014"
    return f"{value:,.{decimals}f}".replace(",", "\u00a0").replace(".", ",")

def fmt_delta(value: float, decimals: int = 2, suffix: str = "") -> str:
    """
    Formate un delta avec signe explicite et couleur implicite.
    Ex: -2.5 \u2192 \"-2,50\"  /  +3.1 \u2192 \"+3,10\"
    """
    if value is None:
        return "\u2014"
    sign = "+" if value > 0 else ""
    formatted = f"{value:,.{decimals}f}".replace(",", "\u00a0").replace(".", ",")
    return f"{sign}{formatted}{suffix}"

def fmt_date(dt_string: str) -> str:
    """
    Formate une date ISO en format fran\u00e7ais.
    Ex: \"2026-06-03T13:02:00\" \u2192 \"03/06/2026 13:02\"
    """
    if not dt_string:
        return "\u2014"
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(dt_string.replace("Z", "+00:00"))
        return dt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return dt_string

def fmt_client_id(client_id: str) -> str:
    """
    Formate un identifiant client (pas de transformation, mais s'assure du type).
    Ex: \"C070\" \u2192 \"C070\"
    """
    return str(client_id) if client_id else "\u2014"

def fmt_status(status: str) -> str:
    """
    Retourne l'\u00e9moji + label du statut visuel (cf. Design Spec \u00a73.3/\u00a73.5).
    """
    status_map = {
        "BROUILLON": "\u2b1c BROUILLON",
        "EN COURS": "\u25cf EN COURS",
        "CALCUL\u00c9": "\u25cf EN COURS",
        "CRITIQUE": "\u25cb CRITIQUE",
        "EN ATTENTE": "\u25d0 EN ATTENTE",
        "SOUMIS": "\u25d0 EN ATTENTE",
        "CERTIFI\u00c9": "\u25cf CERTIFI\u00c9",
        "REJET\u00c9": "\u2b1c BROUILLON",  # Rejet\u00e9 retourne visuellement en brouillon
    }
    return status_map.get(status.upper(), f"\u2753 {status}")

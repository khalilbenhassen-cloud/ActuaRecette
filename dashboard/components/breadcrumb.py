# breadcrumb.py — Fil d'Ariane navigable
# Phase 2a — Fixé en haut, pattern WTW
"""
Usage:
    from dashboard.components.breadcrumb import breadcrumb
    breadcrumb(["Menu Principal", "Cockpit", "LOB Auto"])
"""
import streamlit as st
from typing import List

# Mapping breadcrumb labels → sidebar page IDs
_BREADCRUMB_NAV = {
    "Tableau de bord": "cockpit",
    "Conformité": "conformite",
    "Campagnes": "espace_travail",
    "Registre d'Audit": "audit",
    "Tendances": "tendances",
    "Configuration des Règles": "admin_rules",
    "Paramètres": "parametres"
}

def breadcrumb(path: List[str]) -> None:
    """Affiche un fil d'Ariane navigable et la topbar interactive globale.
    """
    if not path:
        return

    # Retrieve user information
    user_data = st.session_state.get("user")
    user_name = ""
    user_role = ""
    if user_data:
        user_name = user_data.get("name", "")
        user_role = user_data.get("role", "")

    # Call top_bar directly to render the complete interactive top bar
    from dashboard.components.top_bar import top_bar
    top_bar(
        breadcrumb=path,
        period="",
        anomaly_count=0,
        user_name=user_name,
        user_role=user_role
    )

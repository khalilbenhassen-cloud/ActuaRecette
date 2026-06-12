# page_05_jira.py - Page 5 : Espace Tickets Jira (Phase 1 Stub)
import streamlit as st
from dashboard.components.breadcrumb import breadcrumb

def render_jira_page():
    """Affiche la page d'intégration des tickets Jira de correction."""
    from dashboard.views.page_00_login import require_auth
    if require_auth() is None:
        st.stop()
        return

    breadcrumb(["Gouvernance", "Tickets Jira"])
    st.markdown("## 🎫 Ticket de Correction Jira")
    st.markdown("Interface d'exportation de tickets Jira.")
    
    st.info("Cette interface permet de visualiser les tickets de correction automatiques générés lors de la réconciliation.")

"""
Page 06 – Registre d'Audit Réglementaire
=========================================
Grand livre d'audit centralisé contenant l'historique complet des signatures
électroniques et des visas de conformité Solvabilité II.

Extracted from streamlit_app.py (lines 2702-2744).

Entry point: render_audit_page()
"""

import os
import json
import datetime

import streamlit as st
import pandas as pd
from dashboard.components.breadcrumb import breadcrumb

# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def _fetch_audit_trail(user_headers: Optional[Dict[str, str]] = None):
    """Fetch the global audit trail from the API, with local JSON fallback."""
    import requests

    from dashboard.utils.api_client import API_BASE_URL as API_URL
    try:
        res = requests.get(f"{API_URL}/audit-trail", headers=user_headers, timeout=1.5)
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass

    # Fallback: load from local JSON
    audit_path = os.path.join(
        os.path.dirname(__file__), '..', '..', 'data', 'audit_log.json'
    )
    if os.path.exists(audit_path):
        try:
            with open(audit_path, 'r', encoding='utf-8') as f:
                trail = json.load(f)
            if user_headers:
                visible_lobs = [lob.strip() for lob in user_headers.get("X-User-LOBs", "").split(",") if lob.strip()]
                return [entry for entry in trail if entry.get("lob_id", "LOB_AUTO_PART") in visible_lobs]
            return trail
        except Exception:
            pass
    return []

# ---------------------------------------------------------------------------
# Page renderer
# ---------------------------------------------------------------------------

def render_audit_page():
    """Render the Registre d'Audit page."""

    # Defense-in-depth: vérifier l'authentification au niveau page
    from dashboard.views.page_00_login import require_auth
    if require_auth() is None:
        st.stop()
        return

    breadcrumb(["Gouvernance", "Registre d'Audit"])

    st.html(
        f"""
        <div style="margin-bottom: 24px;">
            <h2 style="margin: 0; font-size: 1.5rem; font-weight: 800; color: var(--ar-text-primary); letter-spacing: -0.03em;">Registre d'Audit Réglementaire</h2>
            <p style='color: var(--ar-text-secondary); margin-top: 4px; font-size: 0.88rem;'>Grand livre d'audit centralisé contenant l'historique complet des signatures électroniques.</p>
        </div>
        """
    )

    user_data = st.session_state.get("user", {})
    from dashboard.utils.auth import find_user_by_sso
    user_identity = find_user_by_sso(user_data.get("sso", ""))
    visible_lobs = user_identity.visible_lobs if user_identity else user_data.get("assigned_lobs", [])
    user_role = user_identity.role if user_identity else user_data.get("role", "")

    from dashboard.utils.auth import UserIdentity
    user_identity_obj = UserIdentity(
        sso=user_data.get("sso", ""),
        name=user_data.get("name", user_data.get("sso", "")),
        role=user_role,
        assigned_lobs=visible_lobs
    )
    user_headers = user_identity_obj.to_headers()

    audit_trail = _fetch_audit_trail(user_headers)


    if not audit_trail:
        st.html(
            """
            <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 60px 24px; text-align: center; background-color: var(--ar-bg-surface); border: 1px solid var(--ar-border); border-radius: 16px; margin-top: 20px;">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="width: 48px; height: 48px; color: var(--ar-text-muted); margin-bottom: 16px;">
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                    <path d="M12 8v4"/>
                    <path d="M12 16h.01"/>
                </svg>
                <h3 style="margin: 0 0 8px 0; color: var(--ar-text-primary); font-size: 1.1rem; font-weight: 700; font-family: var(--ar-font-sans);">Registre d'audit vierge</h3>
                <p style="margin: 0; color: var(--ar-text-secondary); font-size: 0.85rem; max-width: 420px; line-height: 1.5; font-family: var(--ar-font-sans);">
                    Le grand livre d'audit réglementaire <b>Solvabilité II</b> est actuellement vide. Les signatures électroniques et les visas de conformité des validateurs apparaîtront automatiquement ici dès qu'une campagne de réconciliation sera certifiée.
                </p>
            </div>
            """
        )
    else:
        audit_df = pd.DataFrame(audit_trail)
        if "timestamp" in audit_df.columns:
            audit_df["Date & Heure"] = audit_df["timestamp"].apply(
                lambda x: datetime.datetime.fromisoformat(x).strftime("%d/%m/%Y %H:%M:%S") if isinstance(x, str) else x
            )
            audit_df = audit_df.drop(columns=["timestamp"])

        cols_to_show = ["Date & Heure", "run_name", "role", "action", "validator_name", "comment"]
        existing_cols = [c for c in cols_to_show if c in audit_df.columns]

        st.dataframe(audit_df[existing_cols], use_container_width=True, hide_index=True)

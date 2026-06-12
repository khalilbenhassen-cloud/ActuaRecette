# page_02_conformite.py - Page 2 : Tableau de Conformit\u00e9 LOB
# Phase 1 \u2014 Extraction du monolithe streamlit_app.py
#
# NOTE : Dans le monolithe, le Grand Livre de Recette (conformit\u00e9) faisait partie
# du Cockpit (lignes 1233-1402). Il est maintenant une page s\u00e9par\u00e9e.
# Le contenu sera enrichi en Phase 2a avec le design system.

import os
import json
import streamlit as st
import pandas as pd
from typing import List, Dict, Any
from dashboard.components.breadcrumb import breadcrumb

def render_conformite_page():
    """Page 2 : Tableau de conformit\u00e9 consolid\u00e9 par LOB."""
    
    # Defense-in-depth: vérifier l'authentification au niveau page
    from dashboard.views.page_00_login import require_auth
    if require_auth() is None:
        st.stop()
        return

    breadcrumb(["Gouvernance", "Conformité"])
    st.markdown("## \u2261 Tableau de Conformit\u00e9")
    st.markdown("Vue consolid\u00e9e du taux de conformit\u00e9 par LOB et par p\u00e9riode.")
    st.markdown("---")
    
    # Charger l'historique des runs
    history = _load_history()
    
    # Phase 1.4: LOB Cloisonnement
    from dashboard.utils.lob_filter import filter_runs_by_lobs, classify_run_lob
    from dashboard.utils.auth import ALL_LOBS
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

    # Charger l'historique des runs
    history = _load_history(user_headers)
    history = filter_runs_by_lobs(history, visible_lobs)
    
    if not history:
        st.info("• Aucune campagne disponible pour vos portefeuilles.")
        return
    
    # Construire un DataFrame de synthèse
    rows = []
    for run in history:
        kpis = run.get("kpis", {})
        rows.append({
            "Campagne": run.get("run_name", "Sans nom"),
            "ID": run.get("run_id", ""),
            "Date": run.get("timestamp", ""),
            "Dossiers": kpis.get("total_cases", 0),
            "Conformes": kpis.get("conform_cases", 0),
            "Anomalies": kpis.get("fatal_defects", 0),
            "Taux (%)": kpis.get("success_rate_pct", 0.0),
            "Δ (€)": kpis.get("total_absolute_delta_euros", 0.0),
            "Statut": kpis.get("final_status", "Brouillon"),
        })
    
    df = pd.DataFrame(rows)
    
    if df.empty:
        st.info("• Aucune donnée de conformité disponible.")
        return
    
    # Métriques de synthèse
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Campagnes totales", len(df))
    with col2:
        total_dossiers = df["Dossiers"].sum()
        if total_dossiers > 0:
            avg_rate = (df["Conformes"].sum() / total_dossiers) * 100.0
        else:
            avg_rate = 0.0
        st.metric("Taux moyen (pondéré)", f"{avg_rate:.1f} %")
    with col3:
        total_anomalies = df["Anomalies"].sum()
        st.metric("Anomalies totales", int(total_anomalies))
    with col4:
        total_delta = df["Δ (€)"].sum()
        st.metric("Impact total", f"{total_delta:.2f} €")
    
    st.markdown("---")
    
    # Tableau interactif
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "ID": st.column_config.TextColumn("ID", width="small"),
            "Taux (%)": st.column_config.ProgressColumn(
                "Conformité",
                min_value=0,
                max_value=100,
                format="%.1f %%",
            ),
            "Δ (€)": st.column_config.NumberColumn(
                "Impact €",
                format="%.2f €",
            ),
        },
    )

def _load_history(user_headers: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
    """Charge l'historique des runs via API (WF-10) ou fallback local."""
    from dashboard.utils.api_client import API_BASE_URL
    import requests
    try:
        res = requests.get(f"{API_BASE_URL}/history", headers=user_headers, timeout=1.5)
        if res.status_code == 200:
            return res.json()
    except Exception:
        pass
    # Fallback local
    history_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "uat_runs")
    if not os.path.exists(history_dir):
        return []
    runs = []
    for filename in sorted(os.listdir(history_dir), reverse=True):
        if filename.endswith(".json"):
            try:
                filepath = os.path.join(history_dir, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    runs.append(json.load(f))
            except Exception:
                continue
    if user_headers:
        visible_lobs = [lob.strip() for lob in user_headers.get("X-User-LOBs", "").split(",") if lob.strip()]
        from dashboard.utils.lob_filter import filter_runs_by_lobs
        return filter_runs_by_lobs(runs, visible_lobs)
    return runs

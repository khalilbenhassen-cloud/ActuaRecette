# page_04_detail_run.py - Page 4 : D\u00e9tail Run & Anomalies
# Phase 1 \u2014 Extraction du monolithe streamlit_app.py
#
# NOTE : Dans le monolithe, cette page \u00e9tait l'\u00e9tape \"Analyse\" du wizard Recettes
# (lignes 1743-2211). Elle sera enrichie en Phase 2d avec le coefficient_table.

import os
import json
import streamlit as st
import pandas as pd
import plotly.express as px
from typing import List, Dict, Any, Optional
import html
from dashboard.components.breadcrumb import breadcrumb
from dashboard.components.kpi_card import kpi_card
from dashboard.utils.validators import validate_run_id

def render_detail_run_page():
    """Page 4 : D\u00e9tail d'un run avec tableau des anomalies."""
    
    # Defense-in-depth: vérifier l'authentification au niveau page
    from dashboard.views.page_00_login import require_auth
    if require_auth() is None:
        st.stop()
        return

    breadcrumb(["Opérationnel", "Campagnes", "Détail du Run"])
    col_title, col_back = st.columns([9, 3])
    with col_title:
        st.markdown("## \u2263 D\u00e9tail Campagne & Anomalies")
    with col_back:
        if st.button("← Retour aux campagnes", key="back_to_campaigns", use_container_width=True):
            st.session_state["current_page"] = "espace_travail"
            st.session_state.pop("selected_run_id", None)
            st.session_state.pop("current_run_id", None)
            st.rerun()
    
    user_data = st.session_state.get("user", {})
    from dashboard.utils.auth import find_user_by_sso
    user_identity = find_user_by_sso(user_data.get("sso", ""))
    visible_lobs = user_identity.visible_lobs if user_identity else user_data.get("assigned_lobs", [])

    run_id = st.session_state.get("current_run_id") or st.session_state.get("selected_run_id")
    
    if not run_id:
        # WF-08: Permettre la sélection d'un run directement depuis cette page
        history = _load_available_runs(visible_lobs)
        if not history:
            st.info("\u2022 Aucune campagne disponible. Créez-en une depuis l'espace Campagnes.")
            return
        run_labels = {f"{r.get('run_name', r.get('run_id','?'))} — {r.get('timestamp','')[:10]}": r.get("run_id") for r in history}
        selected_label = st.selectbox("Sélectionnez une campagne à analyser", options=list(run_labels.keys()), key="detail_run_selector")
        if selected_label:
            run_id = run_labels[selected_label]
            st.session_state["selected_run_id"] = run_id
        else:
            return
    
    # Validation anti path-traversal
    try:
        run_id = validate_run_id(run_id)
    except ValueError:
        st.error("\u2716 Identifiant de campagne invalide.")
        return
    
    # Charger le run (UI-06: skeleton pendant le chargement)
    run_data = _load_run(run_id)
    if not run_data:
        st.error(f"\u2716 Campagne introuvable : {html.escape(str(run_id))}")
        return

    # Vérification d'accès LOB
    from dashboard.utils.lob_filter import can_access_run
    current_sso = user_data.get("sso", "")
    run_maker_sso = run_data.get("maker_sso", run_data.get("metadata", {}).get("created_by", ""))
    is_own_run = current_sso and current_sso == run_maker_sso
    if not is_own_run and not can_access_run(run_data, visible_lobs):
        st.error("\u2716 Accès refusé : cette campagne appartient à un portefeuille hors de votre périmètre.")
        return
    
    # En-t\u00eate du run
    run_name = run_data.get("run_name", "Sans nom")
    timestamp = run_data.get("timestamp", "")
    kpis = run_data.get("kpis", {})
    anomalies = run_data.get("anomalies", [])
    
    st.markdown(f"**{run_name}** \u2014 `{run_id}`")
    st.markdown(f"\u2022 {timestamp}")
    st.markdown("---")
    
    # KPIs
    col1, col2, col3, col4 = st.columns(4)
    total = kpis.get("total_cases", 0)
    conform = kpis.get("conform_cases", 0)
    rate = kpis.get("success_rate_pct", 0)
    impact = kpis.get("total_absolute_delta_euros", 0)
    with col1:
        kpi_card(label="Dossiers", value=str(total), status="info")
    with col2:
        kpi_card(label="Conformes", value=str(conform), status="conforme" if conform == total else "warning")
    with col3:
        kpi_card(label="Taux", value=f"{rate:.1f} %", status="conforme" if rate == 100 else "anomalie")
    with col4:
        kpi_card(label="Impact \u20ac", value=f"{impact:.2f} \u20ac", status="anomalie" if impact > 0 else "conforme")
    
    st.markdown("---")
    
    # Tableau des anomalies
    if not anomalies:
        st.success("\u2714 Aucune anomalie d\u00e9tect\u00e9e sur cette campagne.")
        return
    
    st.markdown(f"### \u26a0 {len(anomalies)} anomalie(s) d\u00e9tect\u00e9e(s)")
    
    df_anom = pd.DataFrame(anomalies)
    
    # S\u00e9lection des colonnes pertinentes
    display_cols = []
    for col in ["ID_CLIENT", "PRIME_REF", "PRIME_DSI", "abs_deviation", "rel_deviation_pct", 
                "is_fatal_defect", "anomaly_category", "suspicion_details"]:
        if col in df_anom.columns:
            display_cols.append(col)
    
    if display_cols:
        st.dataframe(
            df_anom[display_cols],
            use_container_width=True,
            hide_index=True,
            column_config={
                "abs_deviation": st.column_config.NumberColumn("\u0394 (\u20ac)", format="%.2f"),
                "rel_deviation_pct": st.column_config.NumberColumn("\u0394 (%)", format="%.2f"),
                "is_fatal_defect": st.column_config.CheckboxColumn("Fatal"),
            },
        )
    else:
        st.dataframe(df_anom, use_container_width=True, hide_index=True)
    
    # Graphique de distribution
    if "abs_deviation" in df_anom.columns:
        st.markdown("### Distribution des \u00e9carts")
        fig = px.histogram(
            df_anom, x="abs_deviation", nbins=20,
            labels={"abs_deviation": "\u00c9cart absolu (\u20ac)"},
            title="Distribution des \u00e9carts par montant"
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    # T40: Selecteur de run de comparaison
    st.markdown("---")
    st.markdown("### Comparaison avec un autre run")
    try:
        from dashboard.components.run_comparator import run_comparator
        history_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "uat_runs")
        all_runs = []
        if os.path.isdir(history_dir):
            for fname in os.listdir(history_dir):
                if fname.endswith(".json"):
                    fpath = os.path.join(history_dir, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8") as f2:
                            rd = json.load(f2)
                        all_runs.append({
                            "run_id": rd.get("run_id", fname.replace(".json", "")),
                            "run_name": rd.get("run_name", "Sans nom"),
                            "success_rate_pct": rd.get("kpis", {}).get("success_rate_pct", 0),
                            "fatal_defects": rd.get("kpis", {}).get("fatal_defects", 0),
                            "total_absolute_delta_euros": rd.get("kpis", {}).get("total_absolute_delta_euros", 0),
                            "total_cases": rd.get("kpis", {}).get("total_cases", 0),
                        })
                    except Exception:
                        pass
        if len(all_runs) >= 2:
            run_comparator(all_runs)
        else:
            st.info("Il faut au minimum 2 campagnes sauvegard\u00e9es pour activer la comparaison.")
    except Exception as e:
        import logging
        logging.getLogger("actuarecette").exception("Comparateur non disponible")
        st.warning("Le module de comparaison n'a pas pu être chargé.")

    # T74: Root cause coefficient table integration
    st.markdown("---")
    st.markdown("### Decomposition Root Cause")
    try:
        from dashboard.components.coefficient_table import coefficient_table
        coefficient_table(run_id=run_id, anomalies=anomalies)
    except ImportError:
        st.info("Module coefficient_table non disponible.")
    except Exception as e:
        import logging
        logging.getLogger("actuarecette").exception("Erreur root cause")
        st.warning("L'analyse root cause n'a pas pu être effectuée.")

# T41: KPI drill-down navigation helper
def navigate_to_run_detail(run_id: str):
    """
    Helper appele depuis le Cockpit quand un KPI est clique.
    Stocke le run_id et navigue vers la page detail.
    """
    st.session_state["current_run_id"] = run_id
    st.session_state["current_page"] = "detail_run"

def _load_run(run_id: str) -> Optional[Dict[str, Any]]:
    """Charge un run depuis le fichier JSON local."""
    history_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "uat_runs")
    file_path = os.path.join(history_dir, f"{run_id}.json")
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None

def _load_available_runs(visible_lobs: List[str]) -> List[Dict[str, Any]]:
    """WF-08: Charge la liste des runs disponibles pour le sélecteur."""
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
    from dashboard.utils.lob_filter import filter_runs_by_lobs
    return filter_runs_by_lobs(runs, visible_lobs)

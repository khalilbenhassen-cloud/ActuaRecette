
import html
import os
import io
import json
import datetime
import requests
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from typing import Optional, Dict, Any, List
from dashboard.components.breadcrumb import breadcrumb
from dashboard.components.top_bar import top_bar
from dashboard.components.period_bar import period_bar, get_active_periods
from dashboard.components.kpi_card import kpi_card
from dashboard.components.status_badge import status_badge
from dashboard.components.validation_queue import validation_queue

from dashboard.utils.api_client import API_BASE_URL as API_URL

SVG_LOGO = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M4.5 3h15"/><path d="M6 3v16a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V3"/><path d="M6 14h12"/></svg>'
SVG_COCKPIT = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="9"/><rect x="14" y="3" width="7" height="5"/><rect x="14" y="12" width="7" height="9"/><rect x="3" y="16" width="7" height="5"/></svg>'
SVG_RECETTES = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/></svg>'
SVG_ARROW = '<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" x2="19" y1="12" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>'

SVG_KPI_SAINS = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>'
SVG_KPI_ANOMALIES = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" x2="12" y1="9" y2="13"/><line x1="12" x2="12" y1="17" y2="17"/></svg>'
SVG_KPI_CONFORMITE = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>'
SVG_KPI_DELTA = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" x2="12" y1="19" y2="5"/><polyline points="5 12 12 5 19 12"/></svg>'
SVG_KPI_DELAI = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M5 2h14M5 22h14M19 2v4c0 2.2-1.8 4-4 4h-6C6.8 10 5 8.2 5 6V2M5 22v-4c0-2.2 1.8-4 4-4h6c2.2 0 4 1.8 4 4v4"/></svg>'
SVG_KPI_REJET = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" x2="9" y1="9" y2="15"/><line x1="9" x2="15" y1="9" y2="15"/></svg>'
SVG_KPI_ATTENTE = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>'

from dashboard.views.cockpit_helpers import (

    fetch_run_history,

    fetch_audit_trail,

    load_run_by_id,

    get_campaign_status,

    get_status_html,

    render_kpi_card_html,

    render_kpi_popover_actions,

    render_campaign_track_html,

    render_top_bar,

    _render_role_section,

    _ROLE_CONFIG,

)

def render_cockpit_page():

    from dashboard.views.page_00_login import require_auth
    if require_auth() is None:
        st.stop()
        return

    from dashboard.utils.lob_filter import filter_runs_by_lobs
    user_data = st.session_state.get("user", {})
    from dashboard.utils.auth import find_user_by_sso
    user_identity = find_user_by_sso(user_data.get("sso", ""))
    visible_lobs = user_identity.visible_lobs if user_identity else user_data.get("assigned_lobs", [])
    user_role = user_identity.role if user_identity else user_data.get("role", "")
    user_sso = user_data.get("sso", "")
    user_headers = {
        "X-User-SSO": user_sso,
        "X-User-Role": user_role,
        "X-User-LOBs": ",".join(visible_lobs),
    }
    from dashboard.utils.auth import UserIdentity
    user_identity_obj = UserIdentity(
        sso=user_sso,
        name=user_data.get("name", user_sso),
        role=user_role,
        assigned_lobs=visible_lobs
    )
    user_headers = user_identity_obj.to_headers()

    with st.spinner("Chargement des données du cockpit…"):
        history = fetch_run_history(user_sso, user_headers)
        audit_trail = fetch_audit_trail(user_sso, user_headers)

    history = filter_runs_by_lobs(history, visible_lobs)

    _months_fr = ["", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",

                  "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]

    _sel_year = st.session_state.get("selected_year", "2026")

    _sel_quarter = st.session_state.get("selected_quarter")

    _sel_month = st.session_state.get("selected_month")

    if _sel_month:

        _period_label = f"{_months_fr[int(_sel_month)]} {_sel_year}"

    elif _sel_quarter:

        _period_label = f"{_sel_quarter} {_sel_year}"

    else:

        _period_label = f"Année {_sel_year}"

    _anomaly_count = sum(h.get("fatal_defects", 0) for h in history)

    top_bar(
        breadcrumb=["Opérationnel", "Tableau de bord"],
        period=_period_label,

        anomaly_count=_anomaly_count,

        user_name=user_data.get("name", ""),

        user_role=user_role,

    )

    from dashboard.components.search_modal import render_search_results

    with st.popover("\U0001f50d Rechercher une campagne, LOB\u2026", use_container_width=True, key="omnibar_popover"):

        render_search_results(history)

    st.html("""<style>
        .st-key-omnibar_popover > div[data-testid="stPopover"] > button {
            background: var(--ar-bg-elevated) !important;
            border: 1px solid var(--ar-border) !important;
            border-radius: 9999px !important;
            padding: 8px 18px !important;
            font-size: 0.82rem !important;
            color: var(--ar-text-muted) !important;
            font-weight: 400 !important;
            justify-content: flex-start !important;
            transition: var(--ar-transition) !important;
            min-height: 38px !important;
        }
        .st-key-omnibar_popover > div[data-testid="stPopover"] > button:hover {
            border-color: var(--ar-border-focus) !important;
            background: var(--ar-bg-surface) !important;
            box-shadow: var(--ar-shadow-sm) !important;
        }
    </style>""")

    _render_role_section(user_role, user_data)

    def _on_new_recette():

        st.session_state["current_page"] = "espace_travail"

        st.session_state["show_create_campaign"] = True
        st.rerun()
    _actions_placeholder = st.container()
    _period_placeholder = st.container()
    _active_year, _active_quarter, _active_month, _active_slugs = get_active_periods()
    def _is_run_in_period(run_periode: str, active_year: str, active_quarter: Optional[str], active_month: Optional[str]) -> bool:
        if not run_periode:
            return False
        p_parts = run_periode.split("-")
        if len(p_parts) != 2:
            return False
        yr, suffix = p_parts
        if yr != active_year:
            return False
        if active_month:
            if suffix.startswith("T"):
                q_months = {"T1": ["01", "02", "03"], "T2": ["04", "05", "06"], "T3": ["07", "08", "09"], "T4": ["10", "11", "12"]}
                return active_month in q_months.get(suffix, [])
            else:
                return suffix == active_month
        if active_quarter:
            if suffix.startswith("T"):
                return suffix == active_quarter
            else:
                q_months = {"T1": ["01", "02", "03"], "T2": ["04", "05", "06"], "T3": ["07", "08", "09"], "T4": ["10", "11", "12"]}
                return suffix in q_months.get(active_quarter, [])
        return True
    def _run_period_slug(h: dict) -> str:
        p_arr = h.get("periode_arrete") or h.get("metadata", {}).get("periode_arrete")
        if p_arr:
            return p_arr
        ts = h.get("timestamp", "")
        if ts and len(ts) >= 7:
            return ts[:7]  # "2026-06-03T..." → "2026-06"
        return ""
    filtered_history = [
        h for h in history
        if _is_run_in_period(_run_period_slug(h), _active_year, _active_quarter, _active_month)
    ]
    has_data = len(filtered_history) > 0

    if not history:

        st.html("""
        <div style="
            display: flex; flex-direction: column; align-items: center;
            justify-content: center; padding: 60px 20px;
            background: var(--ar-bg-surface, #FFFFFF);
            border: 2px dashed var(--ar-border, #E2E8F0);
            border-radius: var(--ar-radius-lg, 12px);
            margin: 24px 0;
        ">
            <div style="font-size: 3rem; margin-bottom: 16px;">📊</div>
            <h3 style="margin: 0 0 8px 0; color: var(--ar-text-primary, #0F172A);
                        font-weight: 700; font-size: 1.15rem;">
                Bienvenue sur ActuaRecette
            </h3>
            <p style="color: var(--ar-text-muted, #64748B); font-size: 0.88rem;
                       text-align: center; max-width: 420px; margin: 0 0 20px 0;">
                Aucune campagne de réconciliation n'a encore été exécutée.<br>
                Lancez votre première réconciliation actuarielle pour alimenter le cockpit.
            </p>
        </div>
        """)

        if st.button("🚀 Lancer ma première campagne", use_container_width=True, type="primary", key="empty_state_cta"):

            st.session_state["current_page"] = "espace_travail"

            st.session_state["show_create_campaign"] = True

            st.rerun()

        return

    if has_data:
        _tot_cases = sum(h.get("total_cases") or h.get("kpis", {}).get("total_cases") or 0 for h in filtered_history)
        _conf_cases = sum(h.get("conform_cases") or h.get("kpis", {}).get("conform_cases") or 0 for h in filtered_history)
        if _tot_cases > 0:
            avg_conformity = (_conf_cases / _tot_cases) * 100.0
        else:
            avg_conformity = sum(h.get("success_rate_pct", 0.0) or h.get("kpis", {}).get("success_rate_pct", 0.0) for h in filtered_history) / len(filtered_history)

        fatal_defects_total = sum(h.get("fatal_defects", 0) for h in filtered_history)
    else:
        avg_conformity = 0
        fatal_defects_total = 0

    _trend_anom_label = ""

    _trend_anom_color = "var(--ar-text-muted)"

    if len(filtered_history) >= 2:

        _a0 = filtered_history[0].get("fatal_defects", 0)

        _a1 = filtered_history[1].get("fatal_defects", 0)

        _diff = _a0 - _a1

        if _diff > 0:

            _trend_anom_label = f"â†‘ +{_diff} vs préc."

            _trend_anom_color = "var(--ar-anomalie)"

        elif _diff < 0:

            _trend_anom_label = f"â†“ {_diff} vs préc."

            _trend_anom_color = "var(--ar-conforme)"

        else:

            _trend_anom_label = "â†’ Stable"

    elif len(filtered_history) == 1:

        _trend_anom_label = "Premier run"

    if avg_conformity >= 95:

        _conf_color = "var(--ar-conforme)"

        _conf_label = "Conforme"

        _conf_bar_color = "#059669"

    elif avg_conformity >= 90:

        _conf_color = "var(--ar-warning)"

        _conf_label = "Attention"

        _conf_bar_color = "#D97706"

    else:

        _conf_color = "var(--ar-anomalie)"

        _conf_label = "Critique"

        _conf_bar_color = "#DC2626"

    _kpi_attente_count = 0

    _kpi_attente_urgent = 0

    _kpi_encours_count = 0

    _kpi_valides_count = 0

    _kpi_total_lobs = set()

    _kpi_done_lobs = set()

    _kpi_db_runs: list[dict] = []

    db_path = "data/actuarecette.db"

    if os.path.exists(db_path):
        try:
            from dashboard.utils.engine_proxy import sqlite_connection
            import sqlite3 as _sqlite
            with sqlite_connection(db_path) as _ckpi:
                _cursor = _ckpi.cursor()
                _cursor.execute("""
                    SELECT r.statut_validation, r.date_execution, c.id_portefeuille,
                           COALESCE(p.libelle, c.id_portefeuille) AS lob_name, c.periode
                    FROM runs_execution r
                    JOIN campagnes_recette c ON r.id_campagne = c.id_campagne
                    LEFT JOIN portefeuilles p ON c.id_portefeuille = p.id_portefeuille
                """)
                _kpi_db_runs = [dict(row) for row in _cursor.fetchall()]
                _kpi_db_runs = [r for r in _kpi_db_runs if r.get("id_portefeuille") in visible_lobs]
        except Exception:
            pass

    from datetime import datetime as _dtkpi

    _S_ENC = {"BROUILLON", "REJETÉ", "REJET", "EN_ANALYSE", ""}

    _S_ATT = {"SOUMIS", "EN_ATTENTE", "PRÊT_POUR_VALIDATION", "SUBMITTED_FOR_VALIDATION"}

    _S_VAL = {"CERTIFIÉ", "CERTIFIÉ_AVEC_RÉSERVES", "APPROUVÉ", "APPROVED"}

    for _kr in _kpi_db_runs:

        _ks = str(_kr.get("statut_validation", "")).upper().strip()

        _kp = str(_kr.get("periode", ""))

        if not _is_run_in_period(_kp, _active_year, _active_quarter, _active_month):

            continue

        _lob = _kr.get("lob_name", "") or _kr.get("id_portefeuille", "")

        if _lob:

            _kpi_total_lobs.add(_lob)

        if _ks in _S_ENC:

            _kpi_encours_count += 1

        elif _ks in _S_ATT:

            _kpi_attente_count += 1

            _kde = _kr.get("date_execution")

            if isinstance(_kde, str) and len(_kde) >= 16:

                try:

                    _kdt = _dtkpi.fromisoformat(_kde.split("+")[0].replace("Z", ""))

                    if (_dtkpi.now() - _kdt).days > 5:

                        _kpi_attente_urgent += 1

                except Exception:

                    pass

            elif hasattr(_kde, "days"):

                pass

        elif _ks in _S_VAL:

            _kpi_valides_count += 1

            if _lob:

                _kpi_done_lobs.add(_lob)

    _n_total_lobs = max(len(_kpi_total_lobs), 1)

    _n_done_lobs = len(_kpi_done_lobs)

    _pct_couverture = int((_n_done_lobs / _n_total_lobs) * 100)

    from datetime import datetime as _dt

    all_runs_rows: list[dict] = []

    db_path = "data/actuarecette.db"

    if os.path.exists(db_path):
        try:
            from dashboard.utils.engine_proxy import sqlite_connection
            import sqlite3
            with sqlite_connection(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT
                        r.id_run,
                        r.num_run,
                        r.date_execution,
                        r.taux_alignement,
                        r.prime_a_risque,
                        r.statut_validation,
                        r.maker_sso_user,
                        r.checker_sso_user,
                        c.id_campagne,
                        c.id_portefeuille,
                        c.periode,
                        c.type_testing,
                        COALESCE(p.libelle, c.id_portefeuille) AS lob_name
                    FROM runs_execution r
                    JOIN campagnes_recette c ON r.id_campagne = c.id_campagne
                    LEFT JOIN portefeuilles p ON c.id_portefeuille = p.id_portefeuille
                    ORDER BY r.date_execution DESC
                """)
                all_runs_rows = [dict(row) for row in cursor.fetchall()]
                all_runs_rows = [row for row in all_runs_rows if row.get("id_portefeuille") in visible_lobs]
        except Exception:
            pass

    _json_by_id = {h.get("run_id", ""): h for h in history}

    unified_runs: list[dict] = []

    seen_ids: set = set()

    for row in all_runs_rows:

        rid = row.get("id_run", "")

        seen_ids.add(rid)

        jh = _json_by_id.get(rid, {})

        unified_runs.append({

            "id_run": rid,

            "campagne": jh.get("run_name", row.get("id_campagne", rid)),

            "lob_name": row.get("lob_name", "") or row.get("id_portefeuille", ""),

            "periode": row.get("periode", ""),

            "statut": str(row.get("statut_validation", "BROUILLON")).upper().strip(),

            "taux_alignement": row.get("taux_alignement", jh.get("success_rate_pct", 0)),

            "prime_a_risque": row.get("prime_a_risque", jh.get("total_absolute_delta_euros", 0)),

            "fatal_defects": jh.get("fatal_defects", 0),

            "total_cases": jh.get("total_cases", 0),

            "date_execution": row.get("date_execution"),

            "maker": row.get("maker_sso_user", "") or "",

            "checker": row.get("checker_sso_user", "") or "",

            "current_step": jh.get("current_step", ""),

        })

    for h in history:

        rid = h.get("run_id", "")

        if rid and rid not in seen_ids:

            ts = h.get("timestamp", "")

            unified_runs.append({

                "id_run": rid,

                "campagne": h.get("run_name", rid),

                "lob_name": h.get("lob_id", ""),

                "periode": h.get("periode_arrete") or h.get("metadata", {}).get("periode_arrete") or (ts[:7] if len(ts) >= 7 else ""),

                "statut": str(h.get("final_status", "BROUILLON")).upper().strip(),

                "taux_alignement": h.get("success_rate_pct", 0),

                "prime_a_risque": h.get("total_absolute_delta_euros", 0),

                "fatal_defects": h.get("fatal_defects", 0),

                "total_cases": h.get("total_cases", 0),

                "date_execution": ts,

                "maker": h.get("maker_name", ""),

                "checker": h.get("checker_name", ""),

                "current_step": h.get("current_step", ""),

            })

    period_runs = [

        r for r in unified_runs

        if _is_run_in_period(r["periode"], _active_year, _active_quarter, _active_month)

    ]

    _S_ENCOURS = {"BROUILLON", "REJETÉ", "REJET", "EN_ANALYSE", ""}

    _S_ATTENTE = {"SOUMIS", "EN_ATTENTE", "PRÊT_POUR_VALIDATION", "SUBMITTED_FOR_VALIDATION"}

    _S_VALIDES = {"CERTIFIÉ", "CERTIFIÉ_AVEC_RÉSERVES", "APPROUVÉ", "APPROVED"}

    runs_encours = [r for r in period_runs if r["statut"] in _S_ENCOURS]

    runs_attente = [r for r in period_runs if r["statut"] in _S_ATTENTE]

    runs_valides = [r for r in period_runs if r["statut"] in _S_VALIDES]

    _conf_val = f"{avg_conformity:.1f}%" if has_data else "—"
    _att_val = str(_kpi_attente_count) if _kpi_attente_count > 0 else "0"
    _att_color = "var(--ar-warning)" if _kpi_attente_count > 0 else "var(--ar-conforme)"

    _urg_badge = ""
    if _kpi_attente_urgent > 0:
        _urg_badge = f'<span style="font-size:0.63rem;font-weight:600;color:var(--ar-anomalie);background:var(--ar-anomalie-bg);padding:2px 6px;border-radius:var(--ar-radius-full)">⚠ {_kpi_attente_urgent} > 5j</span>'
    elif _kpi_attente_count > 0:
        _urg_badge = '<span style="font-size:0.63rem;font-weight:600;color:var(--ar-conforme);background:var(--ar-conforme-bg);padding:2px 6px;border-radius:var(--ar-radius-full)">Aucune</span>'
    else:
        _urg_badge = '<span style="font-size:0.63rem;color:var(--ar-text-muted)">Délais normaux</span>'

    _anom_val = str(fatal_defects_total) if has_data else "—"
    _anom_color = "var(--ar-anomalie)" if fatal_defects_total > 0 else "var(--ar-conforme)"

    _couv_label = f"{_n_done_lobs}/{_n_total_lobs} LOB"
    _couv_color = "var(--ar-conforme)" if _pct_couverture == 100 else ("var(--ar-warning)" if _pct_couverture >= 50 else "var(--ar-anomalie)")
    _couv_badge = "Complet" if _pct_couverture == 100 else f"{_pct_couverture}%"

    _delays = []
    for r in period_runs:
        ts_created = r.get("timestamp", "")
        ts_locked = r.get("locked_at", "") or r.get("date_execution", "")
        if ts_created and ts_locked:
            try:
                from datetime import datetime
                dt_c = datetime.fromisoformat(ts_created.replace("Z", "+00:00"))
                dt_l = datetime.fromisoformat(ts_locked.replace("Z", "+00:00"))
                _delays.append((dt_l - dt_c).total_seconds() / 86400)
            except Exception:
                pass
    _avg_delay = sum(_delays) / len(_delays) if _delays else 0
    _delay_val = f"{_avg_delay:.1f} j" if _delays else "—"
    _delay_color = "var(--ar-conforme)" if _avg_delay <= 3 else ("var(--ar-warning)" if _avg_delay <= 5 else "var(--ar-anomalie)")
    _delay_badge = "≤ 3j" if _avg_delay <= 3 else ("≤ 5j" if _avg_delay <= 5 else "> 5j")

    _nb_submitted = sum(1 for r in period_runs if r["statut"] in _S_ATTENTE or r["statut"] in _S_VALIDES or r["statut"] in ["REJECTED", "REJETÉ"])
    _nb_rejected = sum(1 for r in period_runs if r["statut"] in ["REJECTED", "REJETÉ"])
    _rej_pct = (_nb_rejected / _nb_submitted * 100) if _nb_submitted > 0 else 0
    _rej_val = f"{_rej_pct:.0f} %" if _nb_submitted > 0 else "—"
    _rej_color = "var(--ar-conforme)" if _rej_pct <= 10 else ("var(--ar-warning)" if _rej_pct <= 25 else "var(--ar-anomalie)")
    _rej_badge = "≤ 10%" if _rej_pct <= 10 else ("≤ 25%" if _rej_pct <= 25 else "> 25%")

    _STEP_MAP = {

        "": ("Configuration initiale", 20),

        "BROUILLON": ("Analyse des écarts", 50),

        "REJETÉ": ("Correction requise (rejet)", 40),

        "EN_ANALYSE": ("Analyse en cours", 60),

    }

    def _parse_dt(val):

        if isinstance(val, _dt):

            return val

        if isinstance(val, str) and len(val) >= 16:

            try:

                return _dt.fromisoformat(val.split("+")[0].replace("Z", ""))

            except Exception:

                return None

        return None

    def _fmt_date(val) -> str:

        dt = _parse_dt(val)

        return dt.strftime("%d/%m/%Y %H:%M") if dt else "\u2014"

    def _days_since(val) -> str:

        dt = _parse_dt(val)

        if not dt:

            return "\u2014"

        d = (_dt.now() - dt).days

        if d == 0:

            h = (_dt.now() - dt).seconds // 3600

            return f"{h}h" if h > 0 else "< 1h"

        return f"{d}j"

    def _days_raw(val) -> int:

        dt = _parse_dt(val)

        return (_dt.now() - dt).days if dt else 0

    with _actions_placeholder:

      with st.container(border=True):

        st.html("""<div class="cockpit-block-title">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
            Actions rapides
        </div>""")

        if runs_encours:

            _sorted_encours = sorted(

                runs_encours,

                key=lambda r: str(r.get("date_execution", "")),

                reverse=True,

            )

            st.html("<div style='font-size:0.68rem; font-weight:600; text-transform:uppercase; letter-spacing:0.05em; color:var(--ar-text-muted); margin-bottom:6px;'>Reprendre une campagne</div>")

            _rc1, _rc2, _rc3 = st.columns([3, 1, 1])

            with _rc1:

                _encours_labels = [r["campagne"] for r in _sorted_encours]

                _sel_repr = st.selectbox(

                    "Reprendre une campagne",

                    range(len(_encours_labels)),

                    format_func=lambda i: _encours_labels[i],

                    key="sel_reprendre",

                    label_visibility="collapsed",

                )

            with _rc2:

                if st.button("Reprendre", key="btn_reprendre", type="primary", use_container_width=True):

                    st.session_state["selected_run_id"] = _sorted_encours[_sel_repr]["id_run"]

                    st.session_state["current_page"] = "espace_travail"

                    st.rerun()

            with _rc3:

                if st.button("+ Nouvelle campagne", key="btn_new_recette_bloc1", use_container_width=True):

                    st.session_state["current_page"] = "espace_travail"

                    st.session_state["show_create_campaign"] = True

                    st.rerun()

        else:

            _rc1, _rc2 = st.columns([3, 1])

            with _rc1:

                st.caption("Aucune campagne en cours")

            with _rc2:

                if st.button("+ Nouvelle campagne", key="btn_new_recette_bloc1b", use_container_width=True):

                    st.session_state["current_page"] = "espace_travail"

                    st.session_state["show_create_campaign"] = True

                    st.rerun()

    with _period_placeholder:

        with st.container(border=True):

            st.html("""<div class="cockpit-block-title">
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="18" x="3" y="4" rx="2" ry="2"/><line x1="16" x2="16" y1="2" y2="6"/><line x1="8" x2="8" y1="2" y2="6"/><line x1="3" x2="21" y1="10" y2="10"/></svg>
                Filtres de p&eacute;riode
            </div>""")

            period_bar(on_new_recette=None)

    col_kpis, col_chart = st.columns([1, 1], gap="medium")

    with col_kpis:

      with st.container(border=True):

        st.html("""<div class="cockpit-block-title">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="9"/><rect x="14" y="3" width="7" height="5"/><rect x="14" y="12" width="7" height="9"/><rect x="3" y="16" width="7" height="5"/></svg>
            Indicateurs cl&eacute;s
        </div>""")

        kpi_list = [
            {
                "title": "Conformité", "value": _conf_val, "color": _conf_color,
                "badge": _conf_label, "badge_color": _conf_color,
                "icon": SVG_KPI_CONFORMITE, "theme": "icon-bg-blue", "suffix": "conf",
                "tooltip": "Taux moyen de conformité des cas sur la période. Seuil ACPR : 95%."
            },
            {
                "title": "En attente", "value": _att_val, "color": _att_color,
                "badge": _urg_badge, "badge_color": "transparent",
                "icon": SVG_KPI_ATTENTE, "theme": "icon-bg-orange", "suffix": "att", "raw_badge": True,
                "tooltip": "Nombre de campagnes soumises en attente de certification."
            },
            {
                "title": "Anomalies", "value": _anom_val, "color": _anom_color,
                "badge": _trend_anom_label, "badge_color": _trend_anom_color,
                "icon": SVG_KPI_ANOMALIES, "theme": "icon-bg-red", "suffix": "anom",
                "tooltip": "Nombre total de défauts fataux détectés sur la période."
            },
            {
                "title": "Couverture", "value": _couv_label, "color": _couv_color,
                "badge": _couv_badge, "badge_color": _couv_color,
                "icon": SVG_KPI_SAINS, "theme": "icon-bg-green", "suffix": "couv",
                "tooltip": "LOB ayant au moins une recette validée / total des LOB actifs."
            },
            {
                "title": "Délai moyen", "value": _delay_val, "color": _delay_color,
                "badge": _delay_badge, "badge_color": _delay_color,
                "icon": SVG_KPI_DELAI, "theme": "icon-bg-blue", "suffix": "delay",
                "tooltip": "Temps moyen écoulé entre la création et la certification."
            },
            {
                "title": "Taux de rejet", "value": _rej_val, "color": _rej_color,
                "badge": _rej_badge, "badge_color": _rej_color,
                "icon": SVG_KPI_REJET, "theme": "icon-bg-red", "suffix": "rej",
                "tooltip": "Nombre de campagnes rejetées / total des campagnes soumises."
            }
        ]

        for k in kpi_list:
            col_l, col_r = st.columns([7, 1])
            with col_l:
                if k.get("raw_badge"):
                    badge_html = k["badge"]
                elif k["badge"]:
                    bg_col = f"color-mix(in srgb, {k['badge_color']} 10%, transparent)"
                    badge_html = f'<span style="font-size:0.65rem;font-weight:600;color:{k["badge_color"]};background:{bg_col};padding:2px 8px;border-radius:var(--ar-radius-full);white-space:nowrap;">{k["badge"]}</span>'
                else:
                    badge_html = ""
                
                st.markdown(f"""
                <div class="actua-kpi-row">
                  <div class="icon-square-mini {k['theme']}">{k['icon']}</div>
                  <span class="actua-kpi-row-title">
                    {k['title'].upper()}
                    <span class="ar-kpi-tip">ⓘ<span class="ar-kpi-tip-text">{k['tooltip']}</span></span>
                  </span>
                  <div class="actua-kpi-row-dots"></div>
                  <span class="actua-kpi-row-value" style="color:{k['color']} !important">{k['value']}</span>
                  <div class="actua-kpi-row-badge-container">{badge_html}</div>
                </div>
                """, unsafe_allow_html=True)
            with col_r:
                with st.popover("\u22ef", key=f"pop_kpi_{k['suffix']}"):
                    render_kpi_popover_actions(k['title'], k['value'], k['suffix'])

    with col_chart:

      with st.container(border=True):

        st.html("""<div class="cockpit-block-title">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 2a10 10 0 0 1 10 10"/><path d="M12 12V2"/><path d="M12 12h10"/></svg>
            Répartition
        </div>""")

        _chart_axis = st.radio(

            "Axe d'analyse",

            ["Par produit (LOB)", "Par statut", "Par actuaire"],

            horizontal=True,

            key="donut_axis",

            label_visibility="collapsed",

        )

        _LOB_COLORS = {

            "Auto": "#4F46E5",

            "MRH": "#059669",

            "Sant\u00e9": "#0EA5E9",

            "Incendie": "#F59E0B",

            "RC": "#8B5CF6",

            "Transport": "#EC4899",

        }

        _STATUS_COLORS = {
            "Brouillon": "#64748B",                # --ar-status-brouillon
            "En analyse": "#2563EB",               # --ar-status-analyse
            "Pr\u00eat pour validation": "#D97706",      # --ar-status-validation
            "En attente approbation": "#7C3AED",   # --ar-status-approbation
            "Certifi\u00e9": "#059669",                  # --ar-status-certifie
            "Certifi\u00e9 avec r\u00e9serves": "#EA580C",     # --ar-status-reserves
            "Rejet\u00e9": "#DC2626",                    # --ar-status-rejete
            "En cours": "#94A3B8",
            "En attente": "#F59E0B",
            "Valid\u00e9": "#059669",
        }

        if _chart_axis == "Par produit (LOB)":

            _counts: dict[str, int] = {}

            for r in period_runs:

                lob = r.get("lob_name", "") or "Non classé"

                _counts[lob] = _counts.get(lob, 0) + 1

            _labels = list(_counts.keys())

            _values = list(_counts.values())

            _colors = [_LOB_COLORS.get(l, "#64748B") for l in _labels]

        elif _chart_axis == "Par statut":

            _stat_map = {"En cours": 0, "En attente": 0, "Valid\u00e9": 0}

            for r in period_runs:

                s = r["statut"]

                if s in _S_ENCOURS:

                    _stat_map["En cours"] += 1

                elif s in _S_ATTENTE:

                    _stat_map["En attente"] += 1

                elif s in _S_VALIDES:

                    _stat_map["Valid\u00e9"] += 1

            _labels = list(_stat_map.keys())

            _values = list(_stat_map.values())

            _colors = ["#94A3B8", "#F59E0B", "#059669"]

        else:  # Par actuaire

            _counts = {}

            for r in period_runs:

                act = r.get("maker", "") or "Non assign\u00e9"

                _counts[act] = _counts.get(act, 0) + 1

            _labels = list(_counts.keys())

            _values = list(_counts.values())

            _colors = ["#4F46E5", "#059669", "#F59E0B", "#EC4899", "#8B5CF6", "#0EA5E9"][:len(_labels)]

        _total = sum(_values) if _values else 0

        if _total > 0:

            fig = go.Figure(data=[go.Pie(

                labels=_labels,

                values=_values,

                hole=0.55,

                marker=dict(colors=_colors, line=dict(color="#FFFFFF", width=2)),

                textinfo="percent+label",

                textposition="outside",

                textfont=dict(size=11, family="Inter, sans-serif"),

                hovertemplate="<b>%{label}</b><br>%{value} campagne(s)<br>%{percent}<extra></extra>",

                pull=[0.02] * len(_labels),

            )])

            fig.update_layout(

                showlegend=False,

                margin=dict(l=10, r=10, t=10, b=10),

                height=280,

                paper_bgcolor="rgba(0,0,0,0)",

                plot_bgcolor="rgba(0,0,0,0)",

                font=dict(family="Inter, sans-serif"),

                annotations=[dict(

                    text=f"<b>{_total}</b><br><span style='font-size:10px;color:#94A3B8'>campagnes</span>",

                    x=0.5, y=0.5, font_size=22, showarrow=False,

                    font=dict(family="Inter, sans-serif", color="#0F172A"),

                )],

            )

            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        else:

            st.html("""
            <div style="display:flex;align-items:center;justify-content:center;height:280px;color:var(--ar-text-muted);font-size:0.85rem">
                Aucune donn\u00e9e pour cette p\u00e9riode
            </div>""")

        st.html("<div style='height:24px'></div>")

    with st.container(border=True):

      st.html("""<div class="cockpit-block-title">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect width="8" height="4" x="8" y="2" rx="1" ry="1"/></svg>
          Suivi des campagnes
      </div>""")

      tab_encours, tab_attente, tab_valides, tab_conformite = st.tabs([

          f"En cours ({len(runs_encours)})",

          f"En attente ({len(runs_attente)})",

          f"Validées ({len(runs_valides)})",

          "☑️ Conformité Globale"

      ], key="cockpit_runs_tabs")

      with tab_encours:

          if not runs_encours:

              st.info("Aucune campagne en cours sur cette p\u00e9riode.")

          else:

              fc1, fc2, fc3 = st.columns(3)

              with fc1:

                  _lo = ["Tous"] + sorted(set(r["lob_name"] for r in runs_encours if r["lob_name"]))

                  _fl = st.selectbox("LOB", _lo, key="f_lob_encours")

              with fc2:

                  _ac = ["Tous"] + sorted(set(r["maker"] for r in runs_encours if r["maker"]))

                  _fa = st.selectbox("Actuaire", _ac, key="f_act_encours")

              with fc3:

                  _pe = ["Tous"] + sorted(set(r["periode"] for r in runs_encours if r["periode"]), reverse=True)

                  _fp = st.selectbox("P\u00e9riode", _pe, key="f_per_encours")

              filt = runs_encours

              if _fl != "Tous":

                  filt = [r for r in filt if r["lob_name"] == _fl]

              if _fa != "Tous":

                  filt = [r for r in filt if r["maker"] == _fa]

              if _fp != "Tous":

                  filt = [r for r in filt if r["periode"] == _fp]

              if not filt:

                  st.info("Aucun r\u00e9sultat avec ces filtres.")

              else:

                  rows = []

                  for r in filt:

                      if r["statut"] in _S_ENCOURS and r.get("current_step"):
                           step_label = r["current_step"]
                           _STEP_PROGRESS = {
                               "Importation": 25,
                               "Contrôles": 50,
                               "Analyse": 75,
                               "Certification": 100
                           }
                           progress = _STEP_PROGRESS.get(step_label, 50)
                      else:
                           step_label, progress = _STEP_MAP.get(r["statut"], ("En cours", 50))

                      rows.append({

                          "Campagne": r["campagne"],

                          "LOB": r["lob_name"] or "\u2014",

                          "P\u00e9riode": r["periode"],

                          "Derni\u00e8re \u00e9tape": step_label,

                          "Progression": f"{progress}%",

                          "Modifi\u00e9 le": _fmt_date(r["date_execution"]),

                          "Actuaire": r["maker"] or "\u2014",

                      })

                  st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True,

                               height=min(400, 38 + len(rows) * 35))

      with tab_attente:

          if not runs_attente:

              st.info("Aucune campagne en attente de validation.")

          else:

              fc1, fc2, fc3, fc4 = st.columns(4)

              with fc1:

                  _lo = ["Tous"] + sorted(set(r["lob_name"] for r in runs_attente if r["lob_name"]))

                  _fl = st.selectbox("LOB", _lo, key="f_lob_attente")

              with fc2:

                  _ac = ["Tous"] + sorted(set(r["maker"] for r in runs_attente if r["maker"]))

                  _fa = st.selectbox("Actuaire", _ac, key="f_act_attente")

              with fc3:

                  _pe = ["Tous"] + sorted(set(r["periode"] for r in runs_attente if r["periode"]), reverse=True)

                  _fp = st.selectbox("P\u00e9riode", _pe, key="f_per_attente")

              with fc4:

                  _fan = st.selectbox("Anciennet\u00e9", ["Tous", "> 3 jours", "> 7 jours"], key="f_anc_attente")

              filt = runs_attente

              if _fl != "Tous":

                  filt = [r for r in filt if r["lob_name"] == _fl]

              if _fa != "Tous":

                  filt = [r for r in filt if r["maker"] == _fa]

              if _fp != "Tous":

                  filt = [r for r in filt if r["periode"] == _fp]

              if _fan == "> 3 jours":

                  filt = [r for r in filt if _days_raw(r["date_execution"]) > 3]

              elif _fan == "> 7 jours":

                  filt = [r for r in filt if _days_raw(r["date_execution"]) > 7]

              if not filt:

                  st.info("Aucun r\u00e9sultat avec ces filtres.")

              else:

                  rows = []

                  for r in filt:

                      rows.append({

                          "Campagne": r["campagne"],

                          "LOB": r["lob_name"] or "\u2014",

                          "P\u00e9riode": r["periode"],

                          "Conformit\u00e9": f"{r['taux_alignement']:.2f}%" if r["taux_alignement"] else "\u2014",

                          "Anomalies": r["fatal_defects"],

                          "Soumis le": _fmt_date(r["date_execution"]),

                          "Soumis par": r["maker"] or "\u2014",

                          "Attente depuis": _days_since(r["date_execution"]),

                      })

                  st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True,

                               height=min(400, 38 + len(rows) * 35))

                  _names = [r["campagne"] for r in filt]

                  _si = st.selectbox("Campagne", range(len(_names)), format_func=lambda i: _names[i],

                                     key="sel_attente", label_visibility="collapsed")

                  if user_role in ("Validateur", "Responsable MOA"):

                      c1, c2 = st.columns(2)

                      with c1:

                          if st.button("Valider", key="btn_valider", type="primary"):

                              st.session_state["selected_run_id"] = filt[_si]["id_run"]

                              st.session_state["current_page"] = "espace_travail"

                              st.rerun()

                      with c2:

                          if st.button("Rejeter", key="btn_rejeter"):

                              st.session_state["selected_run_id"] = filt[_si]["id_run"]

                              st.session_state["current_page"] = "espace_travail"

                              st.rerun()

                  else:

                      if st.button("Voir", key="btn_voir_attente"):

                          st.session_state["selected_run_id"] = filt[_si]["id_run"]

                          st.session_state["current_page"] = "espace_travail"

                          st.rerun()

      with tab_valides:

          if not runs_valides:

              st.info("Aucune campagne valid\u00e9e sur cette p\u00e9riode.")

          else:

              fc1, fc2, fc3, fc4 = st.columns(4)

              with fc1:

                  _lo = ["Tous"] + sorted(set(r["lob_name"] for r in runs_valides if r["lob_name"]))

                  _fl = st.selectbox("LOB", _lo, key="f_lob_valides")

              with fc2:

                  _de = ["Tous"] + sorted(set(r["statut"] for r in runs_valides))

                  _fd = st.selectbox("D\u00e9cision", _de, key="f_dec_valides")

              with fc3:

                  _pe = ["Tous"] + sorted(set(r["periode"] for r in runs_valides if r["periode"]), reverse=True)

                  _fp = st.selectbox("P\u00e9riode", _pe, key="f_per_valides")

              with fc4:

                  _mg = ["Tous"] + sorted(set(r["checker"] for r in runs_valides if r["checker"]))

                  _fm = st.selectbox("Manager", _mg, key="f_mgr_valides")

              filt = runs_valides

              if _fl != "Tous":

                  filt = [r for r in filt if r["lob_name"] == _fl]

              if _fd != "Tous":

                  filt = [r for r in filt if r["statut"] == _fd]

              if _fp != "Tous":

                  filt = [r for r in filt if r["periode"] == _fp]

              if _fm != "Tous":

                  filt = [r for r in filt if r["checker"] == _fm]

              if not filt:

                  st.info("Aucun r\u00e9sultat avec ces filtres.")

              else:

                  rows = []

                  for r in filt:

                      rows.append({

                          "Campagne": r["campagne"],

                          "LOB": r["lob_name"] or "\u2014",

                          "P\u00e9riode": r["periode"],

                          "Conformit\u00e9": f"{r['taux_alignement']:.2f}%" if r["taux_alignement"] else "\u2014",

                          "Divergence": f"{r['prime_a_risque']:,.2f} \u20ac" if r["prime_a_risque"] else "\u2014",

                          "D\u00e9cision": r["statut"].replace("_", " ").title(),

                          "Valid\u00e9 par": r["checker"] or "\u2014",

                          "Valid\u00e9 le": _fmt_date(r["date_execution"]),

                      })

                  st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True,

                               height=min(400, 38 + len(rows) * 35))

                  _names = [r["campagne"] for r in filt]

                  _si = st.selectbox("Campagne", range(len(_names)), format_func=lambda i: _names[i],

                                     key="sel_valides", label_visibility="collapsed")

                  if st.button("Consulter", key="btn_consulter"):

                      st.session_state["selected_run_id"] = filt[_si]["id_run"]

                      st.session_state["current_page"] = "espace_travail"

                      st.rerun()

      with tab_conformite:
          if not history:
              st.info("Aucune campagne disponible pour vos portefeuilles.")
          else:
              rows_conf = []
              for run in history:
                  kpis_run = run.get("kpis", {})
                  total_cases = kpis_run.get("total_cases") or run.get("total_cases", 0)
                  fatal_defects = kpis_run.get("fatal_defects") or run.get("fatal_defects", 0)
                  conform_cases = kpis_run.get("conform_cases") or (total_cases - fatal_defects)
                  success_rate = kpis_run.get("success_rate_pct") or run.get("success_rate_pct", 0.0)
                  delta = kpis_run.get("total_absolute_delta_euros") or run.get("total_absolute_delta_euros", 0.0)
                  status = run.get("final_status") or kpis_run.get("final_status", "Brouillon")

                  rows_conf.append({
                      "Campagne": run.get("run_name", "Sans nom"),
                      "ID": run.get("run_id", ""),
                      "Date": _fmt_date(run.get("timestamp", "")),
                      "Dossiers": total_cases,
                      "Conformes": conform_cases,
                      "Anomalies": fatal_defects,
                      "Taux (%)": success_rate,
                      "Δ (€)": delta,
                      "Statut": status,
                  })

              df_conf = pd.DataFrame(rows_conf)

              if df_conf.empty:
                  st.info("Aucune donnée de conformité disponible.")
              else:
                  m_col1, m_col2, m_col3, m_col4 = st.columns(4)
                  with m_col1:
                      st.metric("Campagnes totales", len(df_conf))
                  with m_col2:
                      total_dossiers = df_conf["Dossiers"].sum()
                      if total_dossiers > 0:
                          avg_rate = (df_conf["Conformes"].sum() / total_dossiers) * 100.0
                      else:
                          avg_rate = 0.0
                      st.metric("Taux moyen (pondéré)", f"{avg_rate:.1f} %")
                  with m_col3:
                      total_anomalies = df_conf["Anomalies"].sum()
                      st.metric("Anomalies totales", int(total_anomalies))
                  with m_col4:
                      total_delta = df_conf["Δ (€)"].sum()
                      st.metric("Impact total", f"{total_delta:.2f} €")

                  st.markdown("---")

                  st.dataframe(
                      df_conf,
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

    # ── Section 6: Centre de Suivi des Tickets Jira ──
    st.html("<div style='height:24px'></div>")

    def _update_jira_ticket_status(run_id: str, ticket_key: str, new_status: str):
        run_file = os.path.join("data/uat_runs", f"{run_id}.json")
        if os.path.exists(run_file):
            try:
                with open(run_file, "r", encoding="utf-8") as rf:
                    run_data = json.load(rf)
                tickets = run_data.get("jira_tickets", [])
                for t in tickets:
                    if t.get("key") == ticket_key:
                        t["status"] = new_status
                run_data["jira_tickets"] = tickets
                with open(run_file, "w", encoding="utf-8") as wf:
                    json.dump(run_data, wf, indent=4, ensure_ascii=False)
            except Exception:
                pass

    all_jira_tickets = []
    for run in history:
        r_id = run.get("run_id")
        if not r_id:
            continue
        run_file = os.path.join("data/uat_runs", f"{r_id}.json")
        if os.path.exists(run_file):
            try:
                with open(run_file, "r", encoding="utf-8") as rf:
                    run_data = json.load(rf)
                tickets = run_data.get("jira_tickets", [])
                for t in tickets:
                    t["run_id"] = r_id
                    t["run_name"] = run_data.get("run_name", "Campagne sans nom")
                    t["status"] = t.get("status", "Ouvert")
                    t["description"] = t.get("description") or "Aucune description technique enregistrée."
                    t["reporter"] = t.get("reporter_name") or run_data.get("maker_name") or "Système"
                    t["lob_id"] = run_data.get("lob_id", "LOB_AUTO_PART")
                    t["domaine"] = run_data.get("domaine", "Prime")
                    t["created_at_formatted"] = _fmt_date(t.get("created_at"))
                    all_jira_tickets.append(t)
            except Exception:
                pass

    with st.container(border=True):
        st.html("""<div class="cockpit-block-title">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect width="8" height="4" x="8" y="2" rx="1" ry="1"/></svg>
            Centre de Suivi des Tickets Jira
        </div>""")

        if not all_jira_tickets:
            st.info("Aucun ticket Jira n'a été créé pour les campagnes de cette période.")
        else:
            col_list, col_detail = st.columns([2, 3])

            with col_list:
                st.markdown("##### 🔍 Sélectionnez un ticket")
                ticket_labels = [f"🎫 {t['key']} — {t['run_name']} ({t['priority']})" for t in all_jira_tickets]
                selected_idx = st.radio(
                    "Tickets actifs",
                    range(len(all_jira_tickets)),
                    format_func=lambda i: ticket_labels[i],
                    label_visibility="collapsed",
                    key="selected_jira_ticket_radio"
                )

            with col_detail:
                t = all_jira_tickets[selected_idx]
                st.markdown(f"### 🎫 Ticket {t['key']}")

                meta_col1, meta_col2, meta_col3 = st.columns(3)
                with meta_col1:
                    st.metric("Priorité", t['priority'])
                with meta_col2:
                    st.metric("Projet", t['project'].split()[0] if " " in t['project'] else t['project'])
                with meta_col3:
                    status_options = ["Ouvert", "En cours (DSI)", "Résolu", "Fermé"]
                    current_status = t.get("status", "Ouvert")
                    if current_status not in status_options:
                        status_options.append(current_status)

                    new_status = st.selectbox(
                        "Statut du ticket",
                        status_options,
                        index=status_options.index(current_status),
                        key=f"status_detail_{t['key']}"
                    )
                    if new_status != current_status:
                        _update_jira_ticket_status(t['run_id'], t['key'], new_status)
                        st.toast(f"Statut de {t['key']} mis à jour !")
                        st.rerun()

                st.markdown("##### 📋 Informations Générales :")
                st.markdown(
                    f"- **Campagne** : {t['run_name']}\n"
                    f"- **Créé par** : {t['reporter']}\n"
                    f"- **Date de création** : {t['created_at_formatted']}\n"
                    f"- **Périmètre** : {t['lob_id']} | Domaine : **{t['domaine']}**"
                )

                st.markdown("**Résumé du Bug :**")
                st.info(t['summary'])

                st.markdown("**Description technique envoyée :**")
                st.text_area(
                    "Détail de l'export",
                    value=t.get("description", "Aucune description technique enregistrée."),
                    height=150,
                    disabled=True,
                    key=f"desc_detail_{t['key']}"
                )

                st.markdown(f"[🔗 Consulter sur Jira (Simulation)](https://jira.groupe.com/browse/{t['key']})")



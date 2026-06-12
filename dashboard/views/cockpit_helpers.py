# cockpit_helpers.py — Helpers extraits de page_01_cockpit.py
# ARCH-05: Réduction du God View cockpit de 1300→~900 lignes
"""
Contient :
- Data fetching (fetch_run_history, fetch_audit_trail, load_run_by_id)
- Campaign status logic (get_campaign_status, get_status_html)
- HTML renderers (render_kpi_card_html, render_campaign_track_html, render_top_bar)
- KPI popover actions (render_kpi_popover_actions)
- Role-based views (_render_role_section, _fetch_pending_validations, etc.)
"""

import html
import os
import json
import requests
import streamlit as st
from typing import Optional, Dict, Any, List

from dashboard.utils.api_client import API_BASE_URL as API_URL
from dashboard.components.validation_queue import validation_queue

# ---------------------------------------------------------------------------
# DATA-FETCHING HELPERS
# ---------------------------------------------------------------------------

# Dual-mode API connectivity check
_api_ok = False
try:
    _res_health = requests.get(f"{API_URL}/health", timeout=1.0)
    if _res_health.status_code == 200:
        _api_ok = True
except Exception:
    pass

# Phase 3 (T83): All src/ access goes through engine_proxy
from dashboard.utils.engine_proxy import (
    load_run_history as _local_load_run_history,
    load_global_audit_trail as _local_load_audit_trail,
    is_available as _engine_available,
)
_local_modules_loaded = _engine_available()

@st.cache_data(ttl=30, show_spinner=False)
def fetch_run_history(user_sso: str = "", user_headers: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
    """Charge l'historique via API ou fallback local."""
    if _api_ok:
        try:
            res = requests.get(f"{API_URL}/history", headers=user_headers, timeout=1.5)
            if res.status_code == 200:
                return res.json()
        except Exception:
            pass
    if _local_modules_loaded:
        history = _local_load_run_history("data/uat_runs")
        if user_headers:
            visible_lobs = [lob.strip() for lob in user_headers.get("X-User-LOBs", "").split(",") if lob.strip()]
            from dashboard.utils.lob_filter import filter_runs_by_lobs
            return filter_runs_by_lobs(history, visible_lobs)
        return history
    return []

@st.cache_data(ttl=60, show_spinner=False)
def fetch_audit_trail(user_sso: str = "", user_headers: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
    """Charge l'audit trail via API ou fallback local."""
    if _api_ok:
        try:
            res = requests.get(f"{API_URL}/audit-trail", headers=user_headers, timeout=1.5)
            if res.status_code == 200:
                return res.json()
        except Exception:
            pass
    if _local_modules_loaded:
        trail = _local_load_audit_trail()
        if user_headers:
            visible_lobs = [lob.strip() for lob in user_headers.get("X-User-LOBs", "").split(",") if lob.strip()]
            return [entry for entry in trail if entry.get("lob_id", "LOB_AUTO_PART") in visible_lobs]
        return trail
    return []

def load_run_by_id(run_id: str, user_headers: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
    """Charge un run spécifique par ID."""
    if _api_ok:
        try:
            res = requests.get(f"{API_URL}/history/{run_id}", headers=user_headers, timeout=1.5)
            if res.status_code == 200:
                return res.json()
        except Exception:
            pass
    run_file = os.path.join("data", "uat_runs", f"{run_id}.json")
    if os.path.exists(run_file):
        with open(run_file, "r", encoding="utf-8") as f:
            run_data = json.load(f)
        if user_headers:
            visible_lobs = [lob.strip() for lob in user_headers.get("X-User-LOBs", "").split(",") if lob.strip()]
            from dashboard.utils.lob_filter import can_access_run
            if not can_access_run(run_data, visible_lobs):
                return None
        return run_data
    return None


# ---------------------------------------------------------------------------
# CAMPAIGN STATUS LOGIC
# ---------------------------------------------------------------------------

def get_campaign_status(run_id: str, audit_trail: List[Dict[str, Any]]) -> str:
    """Determine the status of a campaign from its audit trail."""
    for entry in audit_trail:
        if entry.get("run_id") == run_id:
            action = entry.get("action", "").upper()
            if action in ("CERTIFIED", "APPROVED"):
                return "Certifié"
            elif action == "CERTIFIED_WITH_RESERVES":
                return "Certifié avec réserves"
            elif action == "REJECTED":
                return "Rejeté"
            elif action == "SUBMITTED":
                return "Prêt pour validation"
    return "Brouillon"

def get_status_html(status: str) -> str:
    """Return an HTML badge span for a given campaign status string.
    Delegates to the centralized status_badge component."""
    from dashboard.components.status_badge import status_badge
    return status_badge(status)

# ---------------------------------------------------------------------------
# HTML RENDER HELPERS
# ---------------------------------------------------------------------------

def render_kpi_card_html(title: str, value: str, trend: str, theme_class: str,
                         svg_icon: str, formula: str = ""):
    """Render a themed KPI card as an HTML string with optional formula tooltip."""
    dot_class = "trend-dot-blue"
    if "green" in theme_class:
        dot_class = "trend-dot-green"
    elif "red" in theme_class:
        dot_class = "trend-dot-red"
    elif "orange" in theme_class:
        dot_class = "trend-dot-orange"

    if formula:
        title_block = (
            f'<div class="actua-kpi-title-row">'
            f'  <span class="actua-kpi-title" style="margin-bottom: 0px !important;">{title}</span>'
            f'  <span class="ar-kpi-tip">ⓘ</span>'
            f'</div>'
        )
    else:
        title_block = f'<span class="actua-kpi-title">{title}</span>'

    return (
        f'<div class="actua-kpi-card">'
        f'  <div class="actua-kpi-header" style="margin-bottom: 12px !important;">'
        f'    <div class="icon-square-container {theme_class}" style="margin-bottom: 0px !important;">{svg_icon}</div>'
        f'    <div style="width: 32px; height: 32px;"></div>'
        f'  </div>'
        f'  {title_block}'
        f'  <h3 class="actua-kpi-value">{value}</h3>'
        f'  <div class="actua-kpi-trend-row">'
        f'    <span class="actua-kpi-trend-dot {dot_class}"></span>'
        f'    <span class="actua-kpi-trend-text">{trend}</span>'
        f'  </div>'
        f'</div>'
    )

def render_kpi_popover_actions(title: str, value: str, key_suffix: str = ""):
    """Render interactive popover actions for a KPI card."""
    st.html(
        f"<p style='font-size: 0.72rem; font-weight: 700; color: var(--ar-text-primary); "
        f"margin: 0 0 8px 0;'>📋 Métrique : {title}</p>")

    st.html(
        "<p style='font-size: 0.65rem; color: #64748B; margin: 0 0 2px 0;'>"
        "Valeur (cliquez ci-dessous pour copier) :</p>")
    st.code(value.replace(" cas", "").replace(" %", "").replace(" €", ""), language="text")

    csv_val = value.replace(' ', '').replace('€', '').replace(',', '').replace('%', '').replace('cas', '')
    csv_data = f"KPI,Valeur\n{title},{csv_val}"
    csv_filename = f"kpi_{title.lower().replace(' ', '_')}.csv"

    st.download_button(
        label="📥 Exporter en CSV",
        data=csv_data, file_name=csv_filename, mime="text/csv",
        key=f"dl_btn_{title}_{key_suffix}", use_container_width=True,
    )

    st.html(
        "<hr style='margin: 8px 0; border: 0; border-top: 1px solid #E2E8F0;'>"
        )

    st.html(
        "<p style='font-size: 0.65rem; font-weight: 700; color: #475569; "
        "margin: 0 0 6px 0;'>🔔 Alerte de dépassement :</p>")
    col1, col2 = st.columns([2, 1])
    with col1:
        email = st.text_input(
            "E-mail de contact", value="actuaire@groupe.com",
            key=f"em_{title}_{key_suffix}", label_visibility="collapsed",
        )
    with col2:
        seuil = st.number_input(
            "Seuil", value=95.0 if "Conform" in title else 10.0,
            key=f"se_{title}_{key_suffix}", label_visibility="collapsed",
        )

    if st.button("Activer l'alerte", key=f"act_btn_{title}_{key_suffix}", use_container_width=True):
        st.toast(f"🔔 Alerte configurée à {seuil} pour {email} sur {title} !")

def render_campaign_track_html(r_name: str, r_id: str, date_formatted: str,
                                status_desc: str, success_rate: float, fatal_defects: int):
    """Render a Gantt-like campaign track card as an HTML string."""
    if status_desc in ["Certifié", "Certifié avec réserves"]:
        tag_label = "CONFORME" if status_desc == "Certifié" else "RÉSERVES"
        tag_class = "tag-priority-low" if status_desc == "Certifié" else "tag-priority-medium"
    elif status_desc == "Rejeté":
        tag_label = "CRITIQUE"
        tag_class = "tag-priority-high"
    elif status_desc == "En analyse":
        tag_label = "ANALYSE"
        tag_class = "tag-priority-medium"
    else:
        tag_label = "BROUILLON"
        tag_class = "tag-priority-low"

    assignees_html = (
        '<div style="display: flex; align-items: center; margin-right: 16px;">'
        '<div style="width: 24px; height: 24px; border-radius: 50%; background-color: #EFF6FF; '
        'color: #2563EB; border: 1.5px solid #FFFFFF; font-size: 0.65rem; font-weight: 700; '
        'display: flex; align-items: center; justify-content: center; margin-right: -8px; '
        'box-shadow: 0 1px 2px rgba(0,0,0,0.02);">KB</div>'
        '<div style="width: 24px; height: 24px; border-radius: 50%; background-color: #ECFDF5; '
        'color: #059669; border: 1.5px solid #FFFFFF; font-size: 0.65rem; font-weight: 700; '
        'display: flex; align-items: center; justify-content: center; '
        'box-shadow: 0 1px 2px rgba(0,0,0,0.02);">SM</div>'
        '</div>'
    )

    _safe_name = html.escape(str(r_name))
    _safe_id = html.escape(str(r_id))
    return (
        f'<div class="gantt-card-block"><div style="display: flex; align-items: center; gap: 16px;">'
        f'<div style="background-color: #F8FAFC; border: 1px solid #E5E7EB; border-radius: 8px; '
        f'width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; '
        f'color: #4F46E5;"><span style="font-size: 1.1rem; display: inline-flex; align-items: center;">'
        f'📋</span></div><div><h4 style="margin: 0; color: #0F172A; font-weight: 700; '
        f'font-size: 0.92rem;">{_safe_name}</h4><p style="margin: 2px 0 0 0; font-size: 0.75rem; '
        f'color: #64748B;">Date : {date_formatted} | ID : {_safe_id}</p></div></div>'
        f'<div style="display: flex; align-items: center; gap: 16px;">{assignees_html}'
        f'<span class="tag-priority {tag_class}">{tag_label}</span>'
        f'<div style="text-align: right; margin-left: 24px; min-width: 90px;">'
        f'<span style="font-size: 0.6rem; color: #64748B; text-transform: uppercase; font-weight: 600;">'
        f'Conformité</span><h4 style="margin: 0; color: #2563EB; font-weight: 800; font-size: 0.95rem; '
        f"font-family: 'Plus Jakarta Sans';\">{success_rate:.2f}%</h4></div>"
        f'<div style="text-align: right; min-width: 70px; margin-right: 12px;">'
        f'<span style="font-size: 0.6rem; color: #64748B; text-transform: uppercase; font-weight: 600;">'
        f'Anomalies</span><h4 style="margin: 0; color: #DC2626; font-weight: 800; font-size: 0.95rem; '
        f"font-family: 'Roboto Mono';\">{fatal_defects}</h4></div></div></div>"
    )

def render_top_bar(breadcrumb_path: str = "Menu Principal > Cockpit"):
    """Render a simplified top bar with breadcrumb navigation."""
    st.markdown(
        f"""
        <div style="
            background-color: var(--ar-bg-surface);
            border: 1px solid var(--ar-border);
            border-radius: 16px;
            box-shadow: var(--ar-shadow-sm);
            padding: 12px 24px;
            margin-bottom: 20px;
            margin-top: 10px;
            display: flex;
            align-items: center;
            height: 48px;
        ">
            <span style="font-size: 0.88rem; font-weight: 500; color: var(--ar-text-secondary);">{breadcrumb_path}</span>
        </div>
        """,
    )

# ---------------------------------------------------------------------------
# ROLE-BASED VIEWS
# ---------------------------------------------------------------------------

_ROLE_CONFIG = {
    "Actuaire MOA": {
        "icon": "📊", "label": "Actuaire MOA (Maker)",
        "color": "var(--ar-info)", "desc": "Créez et soumettez des campagnes de réconciliation.",
    },
    "Validateur": {
        "icon": "✅", "label": "Validateur (Checker)",
        "color": "var(--ar-conforme)", "desc": "Certifiez ou rejetez les campagnes soumises.",
    },
    "Responsable MOA": {
        "icon": "👔", "label": "Responsable MOA (Manager)",
        "color": "var(--ar-accent)", "desc": "Supervisez l'ensemble des campagnes et validations.",
    },
}

def _render_role_section(user_role: str, user_data: dict) -> None:
    """Affiche la file de validation pour Checkers/Managers."""
    if user_role in ("Validateur", "Responsable MOA"):
        pending_runs = _fetch_pending_validations(user_data)
        if pending_runs:
            with st.expander(f"📥 File de validation ({len(pending_runs)} en attente)", expanded=True):
                action_result = validation_queue(pending_runs, show_actions=True)
                if action_result:
                    _handle_validation_action(action_result)
        else:
            st.html(
                '<div style="display: flex; align-items: center; gap: 8px;'
                ' padding: 8px 14px; margin-bottom: 12px;'
                ' background-color: var(--ar-conforme-bg);'
                ' border: 1px solid color-mix(in srgb, var(--ar-conforme) 30%, transparent);'
                ' border-radius: var(--ar-radius-md);'
                ' font-size: var(--ar-font-size-sm); color: var(--ar-conforme);">'
                '✅ Aucune campagne en attente de validation'
                '</div>'
            )

    if user_role == "Responsable MOA":
        from dashboard.utils.auth import find_user_by_sso, UserIdentity
        user_identity = find_user_by_sso(user_data.get("sso", ""))
        visible_lobs = user_identity.visible_lobs if user_identity else user_data.get("assigned_lobs", [])
        user_sso = user_data.get("sso", "")
        user_identity_obj = UserIdentity(
            sso=user_sso,
            name=user_data.get("name", user_sso),
            role=user_role,
            assigned_lobs=visible_lobs
        )
        user_headers = user_identity_obj.to_headers()
        _render_team_activity_feed(user_sso, user_headers)


def _fetch_pending_validations(user_data: dict) -> List[Dict[str, Any]]:
    """Fetch pending runs from the API, with fallback to local scan."""
    try:
        from dashboard.utils.auth import UserIdentity
        user_identity_obj = UserIdentity(
            sso=user_data.get("sso", ""),
            name=user_data.get("name", user_data.get("sso", "")),
            role=user_data.get("role", ""),
            assigned_lobs=user_data.get("assigned_lobs", [])
        )
        headers = user_identity_obj.to_headers()
        resp = requests.get(f"{API_URL}/pending-validations", headers=headers, timeout=2)
        if resp.status_code == 200:
            data = resp.json()
            if data:
                return data
    except Exception:
        pass

    # WF-05: Local fallback
    _local_pending: List[Dict[str, Any]] = []
    _runs_dir = "data/uat_runs"
    if os.path.exists(_runs_dir):
        for _fname in os.listdir(_runs_dir):
            if not _fname.endswith(".json"):
                continue
            try:
                _fpath = os.path.join(_runs_dir, _fname)
                with open(_fpath, "r", encoding="utf-8") as _fp:
                    _rdata = json.load(_fp)
                _vs = str(_rdata.get("validation_status", "")).upper()
                if _vs in ("SUBMITTED_FOR_VALIDATION", "SOUMIS", "EN_ATTENTE"):
                    # Maker ≠ Checker: skip runs submitted by current user
                    _sub_by_sso = _rdata.get("submitted_by", _rdata.get("created_by_sso", _rdata.get("maker_sso", "")))
                    if _sub_by_sso == user_data.get("sso", ""):
                        continue
                    
                    # LOB filtering
                    _run_lob = _rdata.get("lob_id", _rdata.get("metadata", {}).get("lob_id", "LOB_AUTO_PART"))
                    _assigned_lobs = user_data.get("assigned_lobs", [])
                    if _assigned_lobs and _run_lob not in _assigned_lobs:
                        continue

                    _kpis = _rdata.get("kpis", {})
                    _sub_name = _rdata.get("maker_name") or _rdata.get("metadata", {}).get("maker_name") or _sub_by_sso or "?"
                    _submitted_at = _rdata.get("submitted_at") or _rdata.get("timestamp", "")

                    _local_pending.append({
                        "run_id": _rdata.get("run_id", _fname.replace(".json", "")),
                        "run_name": _rdata.get("run_name", "Sans nom"),
                        "timestamp": _rdata.get("timestamp", ""),
                        "submitted_by": _sub_name,
                        "submitted_at": _submitted_at,
                        "lob_id": _run_lob,
                        "success_rate_pct": _kpis.get("success_rate_pct", 0.0),
                        "fatal_defects": _kpis.get("fatal_defects", 0),
                        "total_delta_euros": _kpis.get("total_absolute_delta_euros", 0.0),
                        "status": _vs,
                        "_source": "local_fallback",
                    })
            except Exception:
                continue
    if _local_pending:
        st.session_state["_validation_queue_fallback"] = True
    return _local_pending

def _handle_validation_action(action_result: Dict[str, Any]) -> None:
    """Handle certify/reject action from the validation queue."""
    run_id = action_result.get("run_id", "")
    action = action_result.get("_action", "")
    comment = action_result.get("_comment", "")

    if action == "select":
        st.session_state["current_page"] = "espace_travail"
        st.session_state["selected_run_id"] = run_id
        st.session_state["campaign_step"] = "Certification"
        st.rerun()

    elif action in ("certify", "reject"):
        user_data = st.session_state.get("user", {})
        user_sso = user_data.get("sso", "")
        user_name = user_data.get("name", "Système")
        user_role = user_data.get("role", "Actuaire MOA")
        from dashboard.utils.auth import UserIdentity
        user_identity_obj = UserIdentity(
            sso=user_sso,
            name=user_name,
            role=user_role,
            assigned_lobs=user_data.get("assigned_lobs", [])
        )
        user_headers = user_identity_obj.to_headers()

        if _api_ok:
            try:
                if action == "certify":
                    payload = {"comment": comment, "with_reserves": False}
                    requests.post(f"{API_URL}/runs/{run_id}/certify", json=payload, headers=user_headers)
                elif action == "reject":
                    payload = {"reason": comment}
                    requests.post(f"{API_URL}/runs/{run_id}/reject", json=payload, headers=user_headers)
                st.cache_data.clear()
                st.toast(f"✔ Action complétée pour la campagne {run_id}.")
                st.rerun()
                return
            except Exception:
                pass

        # Local fallback execution
        from dashboard.views.page_03_espace_travail import (
            _save_checker_review,
            _update_run_checker,
            _update_run_status,
            _add_audit_entry,
            _generate_certification_number,
            _save_certification_number,
            _lock_run,
            _save_rejection_comment
        )
        
        run_name = action_result.get("run_name", "Campagne")
        lob_id = action_result.get("lob_id", "LOB_AUTO_PART")
        fatal_defects = action_result.get("fatal_defects", 0)
        needs_approver = fatal_defects > 0

        if action == "certify":
            _save_checker_review(run_id, [], [], comment)
            _update_run_checker(run_id, user_sso, user_name)
            if needs_approver:
                _update_run_status(run_id, "PENDING_APPROVAL")
                _add_audit_entry(
                    run_id=run_id, run_name=run_name,
                    role=user_role, action="PENDING_APPROVAL",
                    comment=f"Validé par Checker (direct). Escalade Approver requise ({fatal_defects} bloquant(s)). {comment}",
                    validator_name=user_name
                )
                st.toast(f"✔ Validé par {user_name}. En attente d'approbation.")
            else:
                cert_num = _generate_certification_number(lob_id)
                _save_certification_number(run_id, cert_num)
                _update_run_status(run_id, "APPROVED")
                _lock_run(run_id)
                _add_audit_entry(
                    run_id=run_id, run_name=run_name,
                    role=user_role, action="APPROVED",
                    comment=f"N° {cert_num} (direct). {comment}",
                    validator_name=user_name
                )
                st.toast(f"✔ Campagne certifiée : {cert_num}")
            st.cache_data.clear()
            st.rerun()

        elif action == "reject":
            _save_checker_review(run_id, [], [], comment)
            _save_rejection_comment(run_id, comment)
            _update_run_status(run_id, "REJECTED")
            _update_run_checker(run_id, user_sso, user_name)
            _add_audit_entry(
                run_id=run_id, run_name=run_name,
                role=user_role, action="REJECTED",
                comment=comment,
                validator_name=user_name
            )
            st.toast(f"✖ Campagne {run_id} rejetée.")
            st.cache_data.clear()
            st.rerun()

def _render_team_activity_feed(user_sso: str, user_headers: Optional[Dict[str, str]] = None) -> None:
    """Render a compact team activity feed for the Responsable MOA."""
    audit = fetch_audit_trail(user_sso, user_headers)

    if not audit:
        return

    recent = audit[:5]
    with st.expander("👥 Activité récente de l'équipe", expanded=False):
        for entry in recent:
            ts = entry.get("timestamp", "")[:16].replace("T", " ")
            name = entry.get("validator_name", "?")
            action = entry.get("action", "?")
            run_name = entry.get("run_name", "?")
            role = entry.get("role", "")

            icon_map = {
                "SUBMITTED": "📤", "CERTIFIED": "✅",
                "CERTIFIED_WITH_RESERVES": "⚠️", "REJECTED": "❌", "APPROVED": "✅",
            }
            icon = icon_map.get(action, "📝")

            _safe_name = html.escape(str(name))
            _safe_action = html.escape(str(action))
            _safe_run_name = html.escape(str(run_name))
            _safe_role = html.escape(str(role))
            st.html(
                f'<div style="'
                f'display: flex; align-items: flex-start; gap: 10px;'
                f'padding: 8px 0; border-bottom: 1px solid var(--ar-border);">'
                f'<span style="font-size: 0.9rem; margin-top: 2px;">{icon}</span>'
                f'<div>'
                f'<span style="font-weight: 500; color: var(--ar-text-primary);'
                f' font-size: var(--ar-font-size-sm);">{_safe_name}</span>'
                f'<span style="color: var(--ar-text-muted); font-size: var(--ar-font-size-xs);'
                f' margin-left: 6px;">{_safe_action} • {_safe_run_name}</span>'
                f'<div style="color: var(--ar-text-muted); font-size: var(--ar-font-size-xs);'
                f' margin-top: 2px;">{ts} • {_safe_role}</div>'
                f'</div>'
                f'</div>'
            )

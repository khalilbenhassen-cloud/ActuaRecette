# validation_queue.py \u2014 Bo\u00eete de r\u00e9ception Checker
# Phase 2b \u2014 Affiche les runs SOUMIS en attente de certification
"""
Usage:
    from dashboard.components.validation_queue import validation_queue
    validation_queue(pending_runs, on_certify=..., on_reject=...)
"""
import streamlit as st
from typing import List, Dict, Any, Optional, Callable
from dashboard.components.status_badge import status_badge
from dashboard.components.kpi_card import kpi_card

def validation_queue(
    pending_runs: List[Dict[str, Any]],
    show_actions: bool = True,
) -> Optional[Dict[str, Any]]:
    """
    Affiche la file de validation pour les Checkers.
    
    Args:
        pending_runs: Liste des runs en attente (format PendingValidationItem)
        show_actions: Afficher les boutons Certifier/Rejeter
    
    Returns:
        Le run s\u00e9lectionn\u00e9 si une action est d\u00e9clench\u00e9e, None sinon
    """
    if not pending_runs:
        _render_empty_state()
        return None

    # Header
    st.html(
        f'<div style="'
        f'display: flex; align-items: center; justify-content: space-between;'
        f'margin-bottom: 12px;'
        f'">'
        f'<span style="font-size: var(--ar-font-size-lg); font-weight: 700;'
        f' color: var(--ar-text-primary);">'
        f'\u2193 File de validation</span>'
        f'<span style="background-color: var(--ar-accent-muted);'
        f' color: var(--ar-accent-text); padding: 2px 10px;'
        f' border-radius: var(--ar-radius-full); font-size: var(--ar-font-size-sm);'
        f' font-weight: 600;">{len(pending_runs)}</span>'
        f'</div>'
    )

    selected = None
    for i, run in enumerate(pending_runs):
        action_tuple = _render_queue_item(run, i, show_actions)
        if action_tuple:
            action_type, comment = action_tuple
            selected = {**run, "_action": action_type, "_comment": comment}

    return selected

def _render_queue_item(run: Dict[str, Any], idx: int, show_actions: bool) -> Optional[tuple]:
    """Render a single item in the validation queue."""
    run_id = run.get("run_id", "")
    run_name = run.get("run_name", "Sans nom")
    submitted_by = run.get("submitted_by", "?")
    submitted_at = run.get("submitted_at", "")[:16].replace("T", " ")
    rate = run.get("success_rate_pct", 0.0)
    defects = run.get("fatal_defects", 0)
    delta = run.get("total_delta_euros", 0.0)
    lob = run.get("lob_id", "").replace("LOB_", "").replace("_", " ")

    # Status color
    rate_color = "var(--ar-conforme)" if rate == 100 else "var(--ar-anomalie)" if rate < 90 else "var(--ar-warning)"

    with st.container(border=True):
        # Interactive title button acting as a link
        if st.button(f"📋 {run_name}", key=f"select_run_{run_id}_{idx}", help="Consulter les détails de la campagne", use_container_width=True):
            return ("select", None)

        st.html(
            f'<div style="display: flex; justify-content: space-between; align-items: center; margin-top: 4px; margin-bottom: 8px;">'
            f'<div style="color: var(--ar-text-muted); font-size: var(--ar-font-size-xs);">'
            f'par {submitted_by} • {submitted_at} • {lob}</div>'
            f'<div style="display: flex; gap: 16px; align-items: center;">'
            f'<span style="font-family: var(--ar-font-mono); color: {rate_color}; font-weight: 700; font-size: var(--ar-font-size-sm);">{rate:.1f}%</span>'
            f'<span style="color: var(--ar-text-muted); font-size: var(--ar-font-size-xs);">{defects} défauts • {delta:.0f}€</span>'
            f'</div>'
            f'</div>'
        )

        if show_actions:
            comment_val = st.text_input(
                "Commentaire de validation/rejet *",
                key=f"queue_comment_{run_id}_{idx}",
                placeholder="Commentaire de certification ou motif du rejet (min 10 caractères pour le rejet)...",
                label_visibility="collapsed"
            )
            
            col_cert, col_rej = st.columns(2)
            with col_cert:
                if st.button("✔ Certifier", key=f"certify_{run_id}_{idx}", type="primary", use_container_width=True):
                    comment_clean = comment_val.strip()
                    if not comment_clean:
                        st.error("❌ Le commentaire est obligatoire pour certifier.")
                    else:
                        return ("certify", comment_clean)
            with col_rej:
                if st.button("✖ Rejeter", key=f"reject_{run_id}_{idx}", use_container_width=True):
                    comment_clean = comment_val.strip()
                    if len(comment_clean) < 10:
                        st.error("❌ Le commentaire de rejet doit faire au moins 10 caractères.")
                    elif comment_clean == "Certification de conformité accordée.":
                        st.error("❌ Veuillez modifier le commentaire par défaut.")
                    else:
                        return ("reject", comment_clean)

    return None

def _render_empty_state():
    """Render the empty queue state."""
    st.html(
        '<div style="'
        'display: flex; flex-direction: column; align-items: center;'
        ' justify-content: center; padding: 40px 24px; text-align: center;'
        ' background-color: var(--ar-bg-surface); border: 1px solid var(--ar-border);'
        ' border-radius: var(--ar-radius-lg); margin: 12px 0;'
        '">'
        '<div style="font-size: 2rem; margin-bottom: 8px;">\u2714</div>'
        '<div style="font-weight: 600; color: var(--ar-text-primary);'
        ' font-size: var(--ar-font-size-md);">Aucun run en attente</div>'
        '<div style="color: var(--ar-text-muted); font-size: var(--ar-font-size-sm);'
        ' margin-top: 4px;">Tous les runs soumis ont \u00e9t\u00e9 trait\u00e9s.</div>'
        '</div>'
    )

# dq_slider.py \u2014 Composant UI Sliders de Tol\u00e9rance DQ (Phase 2c)
"""
Affiche des sliders interactifs pour ajuster les seuils de tol\u00e9rance
du contr\u00f4le qualit\u00e9 donn\u00e9es.

Usage:
    from dashboard.components.dq_slider import dq_tolerance_sliders
    overrides = dq_tolerance_sliders()
"""
import streamlit as st
from typing import Dict, Any

def dq_tolerance_sliders(key_prefix: str = "dq") -> Dict[str, Any]:
    """
    Affiche les sliders de tol\u00e9rance DQ et retourne les valeurs actuelles.
    
    Returns:
        Dict avec les overrides de tol\u00e9rance (compatible avec generate_dq_report).
    """
    st.html(
        '<div style="'
        'font-weight: 600; color: var(--ar-text-primary);'
        ' font-size: var(--ar-font-size-sm); margin-bottom: 8px;'
        '">&#9881; Seuils de tol\u00e9rance DQ</div>'
    )

    col1, col2 = st.columns(2)

    with col1:
        null_pct = st.slider(
            "Seuil nulls max (%)",
            min_value=1, max_value=30, value=5,
            key=f"{key_prefix}_null_pct",
            help="Pourcentage maximal de valeurs NULL accept\u00e9es par colonne."
        )
        age_min = st.slider(
            "\u00c2ge minimum assur\u00e9",
            min_value=16, max_value=25, value=18,
            key=f"{key_prefix}_age_min",
            help="Borne inf\u00e9rieure de l'\u00e2ge pour les r\u00e8gles m\u00e9tier."
        )
        age_max = st.slider(
            "\u00c2ge maximum assur\u00e9",
            min_value=80, max_value=120, value=95,
            key=f"{key_prefix}_age_max",
            help="Borne sup\u00e9rieure de l'\u00e2ge pour les r\u00e8gles m\u00e9tier."
        )

    with col2:
        bm_min = st.slider(
            "Bonus-Malus minimum",
            min_value=0.30, max_value=0.60, value=0.50, step=0.05,
            key=f"{key_prefix}_bm_min",
            help="Borne inf\u00e9rieure du coefficient bonus-malus."
        )
        bm_max = st.slider(
            "Bonus-Malus maximum",
            min_value=1.20, max_value=3.50, value=1.50, step=0.10,
            key=f"{key_prefix}_bm_max",
            help="Borne sup\u00e9rieure du coefficient bonus-malus."
        )
        freshness = st.slider(
            "Fra\u00eecheur max (jours)",
            min_value=7, max_value=180, value=30,
            key=f"{key_prefix}_freshness",
            help="Nombre de jours maximum depuis la g\u00e9n\u00e9ration du fichier."
        )

    return {
        "null_pct_threshold": null_pct / 100.0,
        "age_min": age_min,
        "age_max": age_max,
        "bonus_malus_min": bm_min,
        "bonus_malus_max": bm_max,
        "freshness_max_days": freshness,
    }

def dq_score_badge(score: float, verdict: str) -> None:
    """Affiche un badge compact du score DQ."""
    if score >= 95:
        bg = "var(--ar-conforme-bg)"
        border = "var(--ar-conforme)"
        text_color = "var(--ar-conforme)"
    elif score >= 80:
        bg = "color-mix(in srgb, var(--ar-info) 15%, transparent)"
        border = "var(--ar-info)"
        text_color = "var(--ar-info)"
    elif score >= 60:
        bg = "color-mix(in srgb, var(--ar-warning) 15%, transparent)"
        border = "var(--ar-warning)"
        text_color = "var(--ar-warning)"
    else:
        bg = "var(--ar-anomalie-bg)"
        border = "var(--ar-anomalie)"
        text_color = "var(--ar-anomalie)"

    st.html(
        f'<div style="'
        f'display: inline-flex; align-items: center; gap: 8px;'
        f'padding: 6px 14px;'
        f'background-color: {bg};'
        f'border: 1px solid {border};'
        f'border-radius: var(--ar-radius-full);'
        f'font-family: var(--ar-font-mono);'
        f'font-size: var(--ar-font-size-sm);'
        f'font-weight: 700;'
        f'color: {text_color};'
        f'">'
        f'DQ {score:.0f}% \u2022 {verdict}'
        f'</div>'
    )

# kpi_card.py \u2014 Composant KPI Card actuariel
# Phase 2a \u2014 Bordure gauche color\u00e9e par statut, chiffres tnum
"""
Usage:
    from dashboard.components.kpi_card import kpi_card
    kpi_card(
        label="Taux de Conformit\u00e9",
        value="97.3%",
        delta="+2.1%",
        delta_direction="up",      # "up" | "down" | "neutral"
        status="conforme",         # "conforme" | "warning" | "anomalie" | "info" | "neutral"
        tooltip="Dossiers conformes / Dossiers totaux \u00d7 100",
        size="md"                  # "sm" | "md" | "lg"
    )
"""
import streamlit as st

_STATUS_COLORS = {
    "conforme":  "var(--ar-conforme)",
    "warning":   "var(--ar-warning)",
    "anomalie":  "var(--ar-anomalie)",
    "info":      "var(--ar-info)",
    "neutral":   "var(--ar-text-muted)",
}

_SIZE_CONFIG = {
    "sm": {"padding": "12px 16px", "value_size": "1.1rem", "label_size": "0.62rem"},
    "md": {"padding": "16px 20px", "value_size": "1.5rem", "label_size": "0.68rem"},
    "lg": {"padding": "20px 24px", "value_size": "2.0rem", "label_size": "0.75rem"},
}

_DELTA_ICONS = {
    "up":      "\u25b2",
    "down":    "\u25bc",
    "neutral": "\u25cf",
}

def kpi_card(
    label: str,
    value: str,
    delta: str = "",
    delta_direction: str = "neutral",
    status: str = "neutral",
    tooltip: str = "",
    size: str = "md",
) -> None:
    """Affiche une carte KPI actuarielle avec bordure gauche color\u00e9e."""

    color = _STATUS_COLORS.get(status, _STATUS_COLORS["neutral"])
    cfg = _SIZE_CONFIG.get(size, _SIZE_CONFIG["md"])
    icon = _DELTA_ICONS.get(delta_direction, "")

    delta_color = {
        "up": "var(--ar-conforme)",
        "down": "var(--ar-anomalie)",
        "neutral": "var(--ar-text-muted)",
    }.get(delta_direction, "var(--ar-text-muted)")

    tooltip_html = ""
    if tooltip:
        tooltip_html = (
            f'<span class="ar-kpi-tooltip" title="{tooltip}" '
            f'style="color: var(--ar-text-muted); font-size: 0.7rem; cursor: help; '
            f'margin-left: 4px;">\u24d8</span>'
        )

    delta_html = ""
    if delta:
        delta_html = (
            f'<div style="display: flex; align-items: center; gap: 4px; margin-top: 6px;">'
            f'<span style="color: {delta_color}; font-size: 0.72rem; font-weight: 600;">'
            f'{icon} {delta}</span></div>'
        )

    html = f"""
    <div style="
        background-color: var(--ar-bg-surface);
        border: 1px solid var(--ar-border);
        border-left: 3px solid {color};
        border-radius: var(--ar-radius-md);
        padding: {cfg['padding']};
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        height: 100%;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.03);
        cursor: default;
    " class="ar-kpi-card"
       onmouseover="this.style.transform='translateY(-3px)';this.style.boxShadow='0 10px 20px rgba(0,0,0,0.08), 0 4px 8px rgba(0,0,0,0.04)';this.style.borderColor='var(--ar-border-focus)'"
       onmouseout="this.style.transform='translateY(0)';this.style.boxShadow='0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.03)';this.style.borderColor='var(--ar-border)'"
    >
        <div style="display: flex; align-items: center; margin-bottom: 4px;">
            <span style="
                font-size: {cfg['label_size']};
                font-weight: 700;
                color: var(--ar-text-secondary);
                text-transform: uppercase;
                letter-spacing: 0.06em;
            ">{label}</span>
            {tooltip_html}
        </div>
        <div style="
            font-size: {cfg['value_size']};
            font-weight: 800;
            color: var(--ar-text-primary);
            font-family: var(--ar-font-mono);
            font-feature-settings: 'tnum' 1;
            letter-spacing: -0.02em;
            line-height: 1.2;
        ">{value}</div>
        {delta_html}
    </div>
    """
    st.html(html)

# status_badge.py \u2014 Badge de statut campagne
# Phase 2a \u2014 5 statuts avec fond 12% opacit\u00e9
"""
Usage:
    from dashboard.components.status_badge import status_badge
    badge_html = status_badge("Certifi\u00e9")       # Retourne le HTML
    status_badge_render("En analyse")          # Affiche directement via st.markdown
"""
import streamlit as st

_STATUS_CONFIG = {
    "Brouillon":               ("var(--ar-status-brouillon)",  "\u270f"),
    "En analyse":              ("var(--ar-status-analyse)",    "\u2699"),
    "Pr\u00eat pour validation":    ("var(--ar-status-validation)", "\u23f3"),
    "En attente approbation":  ("var(--ar-status-approbation)","\u23f3"),
    "Certifi\u00e9":                ("var(--ar-status-certifie)",   "\u2714"),
    "Certifi\u00e9 avec r\u00e9serves":   ("var(--ar-status-reserves)",  "\u26a0"),
    "Rejet\u00e9":                  ("var(--ar-status-rejete)",    "\u2716"),
}

_STATUS_MAP = {
    "BROUILLON": "Brouillon",
    "CREATED_DRAFT": "Brouillon",
    "EN_ANALYSE": "En analyse",
    "CREATED_AND_CALCULATED": "En analyse",
    "SUBMITTED_FOR_VALIDATION": "Pr\u00eat pour validation",
    "SOUMIS": "Pr\u00eat pour validation",
    "EN_ATTENTE": "Pr\u00eat pour validation",
    "PR\u00caT_POUR_VALIDATION": "Pr\u00eat pour validation",
    "PENDING_APPROVAL": "En attente approbation",
    "EN_ATTENTE_APPROBATION": "En attente approbation",
    "APPROVED": "Certifi\u00e9",
    "FINAL_APPROVED": "Certifi\u00e9",
    "CERTIFI\u00c9": "Certifi\u00e9",
    "CERTIFIED": "Certifi\u00e9",
    "CERTIFIED_WITH_RESERVES": "Certifi\u00e9 avec r\u00e9serves",
    "CERTIFI\u00c9_AVEC_R\u00c9SERVES": "Certifi\u00e9 avec r\u00e9serves",
    "REJECTED": "Rejet\u00e9",
    "REJET\u00c9": "Rejet\u00e9",
}

def status_badge(status: str, size: str = "md", with_icon: bool = True) -> str:
    """
    G\u00e9n\u00e8re le HTML d'un badge de statut.
    
    Args:
        status: Un des statuts ou codes de campagne
        size: "sm" | "md" | "lg"
        with_icon: Afficher l'\u00e9moji d'\u00e9tat
    
    Returns:
        HTML string du badge
    """
    status_upper = str(status).upper().strip()
    display_status = _STATUS_MAP.get(status_upper, status)
    color, icon = _STATUS_CONFIG.get(display_status, ("#64748B", "\u2022"))
    
    size_map = {
        "sm": ("0.62rem", "2px 8px"),
        "md": ("0.72rem", "4px 12px"),
        "lg": ("0.82rem", "6px 16px"),
    }
    font_size, padding = size_map.get(size, size_map["md"])
    
    icon_html = f"{icon} " if with_icon else ""
    
    return (
        f'<span style="'
        f'background-color: color-mix(in srgb, {color} 12%, transparent);'
        f'border: 1px solid color-mix(in srgb, {color} 30%, transparent);'
        f'border-radius: var(--ar-radius-full);'
        f'padding: {padding};'
        f'font-size: {font_size};'
        f'font-weight: 600;'
        f'color: {color};'
        f'display: inline-flex;'
        f'align-items: center;'
        f'gap: 4px;'
        f'font-family: var(--ar-font-sans);'
        f'">'
        f'<span style="'
        f'width: 6px; height: 6px; border-radius: 50%;'
        f'background-color: {color};'
        f'display: inline-block;'
        f'"></span>'
        f'{icon_html}{status}'
        f'</span>'
    )

def status_badge_render(status: str, **kwargs) -> None:
    """Affiche un badge de statut directement via st.markdown."""
    st.html(status_badge(status, **kwargs))

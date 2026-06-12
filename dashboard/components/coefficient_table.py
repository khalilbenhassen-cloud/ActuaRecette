# coefficient_table.py -- Composant UI Root Cause (Phase 2d - T73)
"""
Affiche la d\u00e9composition d'un \u00e9cart de prime par coefficient sous forme
de tableau visuel avec barres de contribution et pattern icons.

Usage:
    from dashboard.components.coefficient_table import coefficient_table
    coefficient_table(decomposition_result)
"""
import streamlit as st
from typing import Dict, Any, List, Optional

# Pattern display info
PATTERN_INFO = {
    "DOUBLE_APPLICATION": {"icon": "\u00d72", "color": "var(--ar-anomalie)", "label": "Double application"},
    "INVERSION": {"icon": "1/x", "color": "var(--ar-anomalie)", "label": "Coefficient invers\u00e9"},
    "ARRONDI_SYSTEMATIQUE": {"icon": "\u2248", "color": "var(--ar-warning)", "label": "Arrondi syst\u00e9matique"},
    "PLANCHER_IGNORE": {"icon": "\u2193", "color": "var(--ar-warning)", "label": "Plancher ignor\u00e9"},
    "ECART_COEFFICIENT": {"icon": "\u0394", "color": "var(--ar-info)", "label": "\u00c9cart coefficient"},
}

def coefficient_table(
    result: Dict[str, Any],
    title: str = "D\u00e9composition Root Cause",
    show_diagnostic: bool = True,
    max_rows: int = 10,
):
    """
    Affiche le tableau de d\u00e9composition Root Cause d'un dossier.

    Args:
        result: Dict retourn\u00e9 par `decompose_variance()`.
        title: Titre de la section.
        show_diagnostic: Afficher le diagnostic humain.
        max_rows: Nombre max de coefficients \u00e0 afficher.
    """
    decomposition = result.get("decomposition", [])
    if not decomposition:
        st.info("\u2022 Aucune donn\u00e9e de d\u00e9composition disponible.")
        return

    ecart_total = result.get("ecart_total", 0)
    ref_prime = result.get("ref_prime", 0)
    prod_prime = result.get("prod_prime", 0)

    # Header
    st.markdown(
        f'<div style="'
        f'background:var(--ar-bg-surface);'
        f'border:1px solid var(--ar-border);'
        f'border-radius:var(--ar-radius-lg);'
        f'padding:20px;'
        f'margin-bottom:16px;'
        f'">'
        f'<div style="font-weight:700; font-size:var(--ar-font-size-md);'
        f'color:var(--ar-text-primary); margin-bottom:12px;">'
        f'{title}</div>'
        f'<div style="display:flex; gap:24px; margin-bottom:16px;">'
        f'<div><span style="color:var(--ar-text-muted); font-size:var(--ar-font-size-xs);'
        f'text-transform:uppercase; letter-spacing:0.05em;">Prime R\u00e9f\u00e9rence</span>'
        f'<div style="font-family:var(--ar-font-mono); font-size:var(--ar-font-size-lg);'
        f'color:var(--ar-text-primary); font-weight:700;">{ref_prime:,.2f} \u20ac</div></div>'
        f'<div><span style="color:var(--ar-text-muted); font-size:var(--ar-font-size-xs);'
        f'text-transform:uppercase; letter-spacing:0.05em;">Prime Production</span>'
        f'<div style="font-family:var(--ar-font-mono); font-size:var(--ar-font-size-lg);'
        f'color:var(--ar-text-primary); font-weight:700;">{prod_prime:,.2f} \u20ac</div></div>'
        f'<div><span style="color:var(--ar-text-muted); font-size:var(--ar-font-size-xs);'
        f'text-transform:uppercase; letter-spacing:0.05em;">\u00c9cart Total</span>'
        f'<div style="font-family:var(--ar-font-mono); font-size:var(--ar-font-size-lg);'
        f'color:{"var(--ar-anomalie)" if ecart_total > 0 else "var(--ar-conforme)"};'
        f'font-weight:700;">{ecart_total:+,.2f} \u20ac</div></div>'
        f'</div>',
    )

    # Coefficient rows
    max_abs = max(abs(d.get("contribution_euros", 0)) for d in decomposition) if decomposition else 1
    if max_abs == 0:
        max_abs = 1

    rows_html = ""
    for item in decomposition[:max_rows]:
        coeff_name = item.get("coefficient", "")
        ref_val = item.get("ref", 0)
        prod_val = item.get("prod", 0)
        contrib_eur = item.get("contribution_euros", 0)
        contrib_pct = item.get("contribution_pct", 0)
        pattern = item.get("pattern")

        # Bar width (proportional)
        bar_width = min(abs(contrib_eur) / max_abs * 100, 100)
        bar_color = "var(--ar-anomalie)" if contrib_eur > 0 else "var(--ar-conforme)"

        # Pattern badge
        pattern_html = ""
        if pattern and pattern in PATTERN_INFO:
            pi = PATTERN_INFO[pattern]
            pattern_html = (
                f'<span style="display:inline-flex; align-items:center; gap:4px;'
                f'padding:2px 8px; border-radius:var(--ar-radius-full);'
                f'background:rgba(99,102,241,0.1); color:{pi["color"]};'
                f'font-size:0.65rem; font-weight:600;">'
                f'{pi["icon"]} {pi["label"]}</span>'
            )

        rows_html += (
            f'<div style="display:grid; grid-template-columns:160px 80px 80px 1fr 90px 140px;'
            f'align-items:center; gap:8px; padding:10px 12px;'
            f'border-bottom:1px solid var(--ar-border);">'
            # Coefficient name
            f'<div style="font-family:var(--ar-font-mono); font-size:var(--ar-font-size-sm);'
            f'color:var(--ar-text-primary); font-weight:500;">{coeff_name}</div>'
            # Ref value
            f'<div style="font-family:var(--ar-font-mono); font-size:var(--ar-font-size-xs);'
            f'color:var(--ar-text-secondary); text-align:right;">{ref_val:.4f}</div>'
            # Prod value
            f'<div style="font-family:var(--ar-font-mono); font-size:var(--ar-font-size-xs);'
            f'color:var(--ar-text-primary); text-align:right;">{prod_val:.4f}</div>'
            # Contribution bar
            f'<div style="position:relative; height:18px; background:var(--ar-bg-elevated);'
            f'border-radius:var(--ar-radius-full); overflow:hidden;">'
            f'<div style="position:absolute; top:0; left:0; height:100%;'
            f'width:{bar_width}%; background:{bar_color}; opacity:0.7;'
            f'border-radius:var(--ar-radius-full);'
            f'transition:width 0.5s cubic-bezier(0.16,1,0.3,1);"></div></div>'
            # Contribution euros
            f'<div style="font-family:var(--ar-font-mono); font-size:var(--ar-font-size-xs);'
            f'color:var(--ar-text-primary); text-align:right; font-weight:600;">'
            f'{contrib_eur:+,.2f} \u20ac</div>'
            # Pattern
            f'<div style="text-align:right;">{pattern_html}</div>'
            f'</div>'
        )

    # Table header
    header_html = (
        f'<div style="display:grid; grid-template-columns:160px 80px 80px 1fr 90px 140px;'
        f'align-items:center; gap:8px; padding:8px 12px;'
        f'border-bottom:2px solid var(--ar-border);'
        f'color:var(--ar-text-muted); font-size:0.65rem;'
        f'text-transform:uppercase; letter-spacing:0.05em; font-weight:600;">'
        f'<div>Coefficient</div>'
        f'<div style="text-align:right;">R\u00e9f.</div>'
        f'<div style="text-align:right;">Prod.</div>'
        f'<div>Contribution</div>'
        f'<div style="text-align:right;">Impact</div>'
        f'<div style="text-align:right;">Pattern</div>'
        f'</div>'
    )

    st.html(header_html + rows_html + '</div>')

    # Diagnostic
    if show_diagnostic and result.get("diagnostic"):
        diag = result["diagnostic"]
        coeff_fautif = result.get("coefficient_fautif", "")
        pattern = result.get("pattern", "")

        st.html(
            f'<div style="'
            f'background:var(--ar-warning-bg);'
            f'border:1px solid var(--ar-warning);'
            f'border-radius:var(--ar-radius-md);'
            f'padding:12px 16px; margin-top:12px;'
            f'">'
            f'<div style="font-weight:600; color:var(--ar-warning);'
            f'font-size:var(--ar-font-size-sm); margin-bottom:4px;">'
            f'\u26a0 Diagnostic automatique</div>'
            f'<div style="color:var(--ar-text-primary);'
            f'font-size:var(--ar-font-size-sm);">{diag}</div>'
            f'</div>'
        )

def patterns_summary_table(patterns: List[Dict[str, Any]]):
    """
    Affiche un r\u00e9sum\u00e9 des patterns syst\u00e9miques d\u00e9tect\u00e9s sur l'ensemble du run.

    Args:
        patterns: Liste retourn\u00e9e par `detect_systematic_patterns()`.
    """
    if not patterns:
        st.info("\u2022 Aucun pattern syst\u00e9mique d\u00e9tect\u00e9.")
        return

    st.html(
        '<div style="font-weight:700; font-size:var(--ar-font-size-md);'
        'color:var(--ar-text-primary); margin-bottom:12px;">'
        'Patterns syst\u00e9miques d\u00e9tect\u00e9s</div>'
    )

    for pat in patterns:
        coeff = pat.get("coefficient", "")
        pattern = pat.get("pattern", "")
        nb = pat.get("nb_dossiers_affectes", 0)
        impact = pat.get("impact_total_euros", 0)
        diag = pat.get("diagnostic", "")
        reco = pat.get("recommandation", "")

        pi = PATTERN_INFO.get(pattern, {"icon": "?", "color": "var(--ar-text-muted)", "label": pattern})

        st.markdown(
            f'<div style="'
            f'background:var(--ar-bg-surface);'
            f'border:1px solid var(--ar-border);'
            f'border-left:3px solid {pi["color"]};'
            f'border-radius:0 var(--ar-radius-md) var(--ar-radius-md) 0;'
            f'padding:14px 16px; margin-bottom:8px;'
            f'">'
            f'<div style="display:flex; justify-content:space-between; align-items:center;">'
            f'<div>'
            f'<span style="font-family:var(--ar-font-mono); font-weight:600;'
            f'color:var(--ar-text-primary);">{coeff}</span>'
            f'<span style="margin-left:8px; padding:2px 8px;'
            f'border-radius:var(--ar-radius-full); background:var(--ar-bg-elevated);'
            f'color:{pi["color"]}; font-size:0.65rem; font-weight:600;">'
            f'{pi["icon"]} {pi["label"]}</span>'
            f'</div>'
            f'<div style="font-family:var(--ar-font-mono); font-weight:700;'
            f'color:{"var(--ar-anomalie)" if impact > 0 else "var(--ar-conforme)"};'
            f'font-size:var(--ar-font-size-md);">{impact:+,.2f} \u20ac'
            f'<span style="color:var(--ar-text-muted); font-size:var(--ar-font-size-xs);'
            f'margin-left:8px;">{nb} dossiers</span></div>'
            f'</div>'
            f'<div style="color:var(--ar-text-secondary); font-size:var(--ar-font-size-xs);'
            f'margin-top:8px;">{diag}</div>'
            + (f'<div style="color:var(--ar-accent-text); font-size:var(--ar-font-size-xs);'
               f'margin-top:6px; font-weight:500;">\u2192 {reco}</div>' if reco else '')
            + '</div>',
        )

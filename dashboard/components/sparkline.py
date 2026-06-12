# sparkline.py — T81
"""
Mini sparkline pour le cockpit manager.

Affiche une ligne de tendance compacte (inline SVG) a cote des KPIs
pour indiquer l'evolution sur les N dernieres periodes sans prendre
de place. Alerte visuelle si degradation.

Usage:
    from dashboard.components.sparkline import sparkline, sparkline_with_alert
    sparkline(values=[95, 93, 90, 88, 85])
    sparkline_with_alert(values=[95, 93, 90, 88, 85], threshold=90.0)
"""
import streamlit as st
from typing import List, Optional

def sparkline(
    values: List[float],
    width: int = 80,
    height: int = 24,
    color: str = "var(--ar-info)",
    line_width: float = 1.5,
) -> str:
    """
    Genere un SVG sparkline inline.

    Args:
        values: Liste de valeurs numeriques.
        width: Largeur en px.
        height: Hauteur en px.
        color: Couleur de la ligne.
        line_width: Epaisseur de la ligne.

    Returns:
        HTML string du sparkline SVG.
    """
    if not values or len(values) < 2:
        return ""

    # Normalize values to fit in height
    min_val = min(values)
    max_val = max(values)
    val_range = max_val - min_val if max_val != min_val else 1.0

    padding = 2
    usable_w = width - 2 * padding
    usable_h = height - 2 * padding

    points = []
    for i, v in enumerate(values):
        x = padding + (i / (len(values) - 1)) * usable_w
        y = padding + usable_h - ((v - min_val) / val_range) * usable_h
        points.append(f"{x:.1f},{y:.1f}")

    polyline = " ".join(points)

    # Determine trend color
    if values[-1] < values[0] - 2:
        actual_color = "#EF4444"  # var(--ar-anomalie) - degradation
    elif values[-1] > values[0] + 2:
        actual_color = "#22C55E"  # var(--ar-conforme) - improvement
    else:
        actual_color = "#3B82F6" if color == "var(--ar-info)" else color  # stable


    svg = (
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'style="display:inline-block;vertical-align:middle;">'
        f'<polyline points="{polyline}" fill="none" stroke="{actual_color}" '
        f'stroke-width="{line_width}" stroke-linecap="round" stroke-linejoin="round"/>'
        f'<circle cx="{points[-1].split(",")[0]}" cy="{points[-1].split(",")[1]}" '
        f'r="2" fill="{actual_color}"/>'
        f'</svg>'
    )
    return svg

def sparkline_with_alert(
    values: List[float],
    threshold: Optional[float] = None,
    label: str = "",
    width: int = 80,
    height: int = 24,
) -> None:
    """
    Affiche un sparkline avec alerte optionnelle si le dernier point < threshold.

    Args:
        values: Valeurs de la serie.
        threshold: Seuil d'alerte (si le dernier point est en dessous).
        label: Label a afficher a gauche.
        width: Largeur du sparkline.
        height: Hauteur du sparkline.
    """
    svg = sparkline(values, width=width, height=height)
    if not svg:
        return

    # Alert badge
    alert_html = ""
    if threshold is not None and values and values[-1] < threshold:
        alert_html = (
            '<span style="background:var(--ar-anomalie);color:white;font-size:0.65rem;'
            'padding:1px 5px;border-radius:3px;margin-left:4px;">↓</span>'
        )

    label_html = f'<span style="color:var(--ar-text-muted);font-size:0.75rem;margin-right:4px;">{label}</span>' if label else ""

    st.html(
        f'<div style="display:inline-flex;align-items:center;gap:4px;">'
        f'{label_html}{svg}{alert_html}'
        f'</div>'
    )

def sparkline_html(
    values: List[float],
    width: int = 80,
    height: int = 24,
) -> str:
    """Returns raw HTML string for embedding in other components."""
    return sparkline(values, width=width, height=height)

# T81 colors: #22C55E (green), #EF4444 (red), #3B82F6 (blue)

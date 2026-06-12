# trend_chart.py -- Composant graphe de tendance (Phase 2d - T79)
"""
Affiche un graphe temporel de KPIs actuariels avec d\u00e9tection de ruptures.

Usage:
    from dashboard.components.trend_chart import trend_chart, sparkline
    trend_chart(snapshots, metric="success_rate_pct")
    sparkline(values, trend="IMPROVING")
"""
import streamlit as st
from typing import List, Dict, Any, Optional
import json

def trend_chart(
    snapshots: List[Dict[str, Any]],
    metric: str = "success_rate_pct",
    title: str = "Tendance taux de conformité",
    height: int = 300,
):
    """
    Affiche un graphe de tendance temporel avec zones colorées.

    Args:
        snapshots: Liste de dicts avec keys: periode, [metric], version_moteur.
        metric: Clé du KPI à tracer.
        title: Titre du graphe.
        height: Hauteur en pixels.
    """
    if not snapshots:
        st.info("• Aucune donnée de tendance disponible.")
        return

    is_pct = "pct" in metric.lower() or "rate" in metric.lower() or "taux" in metric.lower()

    # Prepare data
    periods = []
    values = []
    versions = []
    for s in sorted(snapshots, key=lambda x: x.get("periode", "")):
        periods.append(s.get("periode", ""))
        values.append(float(s.get(metric, 0)))
        versions.append(s.get("version_moteur", ""))

    # Compute trend line (simple linear regression)
    n = len(values)
    if n >= 2:
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n
        num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
        den = sum((i - x_mean) ** 2 for i in range(n))
        slope = num / den if den != 0 else 0
        intercept = y_mean - slope * x_mean
        trend_values = [round(intercept + slope * i, 2) for i in range(n)]
    else:
        slope = 0
        trend_values = values[:]

    # Business Logic Inversion: For percentage metrics, positive slope is IMPROVING.
    # For cost/deviation metrics (lower is better), negative slope is IMPROVING.
    if is_pct:
        trend_direction = "IMPROVING" if slope > 0.1 else ("DEGRADING" if slope < -0.1 else "STABLE")
    else:
        trend_direction = "IMPROVING" if slope < -10 else ("DEGRADING" if slope > 10 else "STABLE")

    trend_colors = {
        "IMPROVING": "var(--ar-conforme)",
        "DEGRADING": "var(--ar-anomalie)",
        "STABLE": "var(--ar-info)",
    }
    trend_labels = {
        "IMPROVING": "↗ Amélioration",
        "DEGRADING": "↘ Dégradation",
        "STABLE": "→ Stable",
    }

    # Build SVG chart inline
    chart_width = 600
    chart_height = height - 60
    padding_left = 65 if not is_pct else 50  # Give more room on left for large Euro numbers
    padding_right = 20
    padding_top = 10
    padding_bottom = 30
    plot_w = chart_width - padding_left - padding_right
    plot_h = chart_height - padding_top - padding_bottom

    # Robust min/max padding that doesn't clip negative or positive values
    if values:
        v_min, v_max = min(values), max(values)
        v_range = v_max - v_min
        if v_range == 0:
            if is_pct:
                min_val = max(0.0, v_min - 5.0)
                max_val = min(100.0, v_max + 5.0)
            else:
                min_val = v_min - 1000.0
                max_val = v_max + 1000.0
        else:
            min_val = v_min - 0.1 * v_range
            max_val = v_max + 0.1 * v_range
            if is_pct:
                min_val = max(0.0, min_val)
                max_val = min(100.0, max_val)
    else:
        min_val = 0
        max_val = 100 if is_pct else 10000

    def to_x(i):
        return padding_left + (i / max(n - 1, 1)) * plot_w

    def to_y(v):
        return padding_top + plot_h - ((v - min_val) / (max_val - min_val)) * plot_h

    # Format helpers
    def fmt_val(v):
        return f"{v:.1f}%" if is_pct else f"{v:,.0f} €"

    def fmt_val_detailed(v):
        return f"{v:.2f}%" if is_pct else f"{v:,.2f} €"

    # Data line
    points = " ".join(f"{to_x(i)},{to_y(v)}" for i, v in enumerate(values))
    # Trend line
    trend_pts = f"{to_x(0)},{to_y(trend_values[0])} {to_x(n-1)},{to_y(trend_values[-1])}"
    # Area fill
    area_pts = points + f" {to_x(n-1)},{padding_top + plot_h} {to_x(0)},{padding_top + plot_h}"

    # Y-axis labels
    y_labels = ""
    for i in range(5):
        val = min_val + (max_val - min_val) * i / 4
        y = to_y(val)
        y_labels += (
            f'<text x="{padding_left - 8}" y="{y + 4}" '
            f'text-anchor="end" fill="var(--ar-text-muted)" font-size="10" '
            f'font-family="var(--ar-font-mono)">{fmt_val(val)}</text>'
            f'<line x1="{padding_left}" y1="{y}" x2="{chart_width - padding_right}" '
            f'y2="{y}" stroke="var(--ar-bg-hover)" stroke-width="0.5" />'
        )

    # X-axis labels
    x_labels = ""
    step = max(1, n // 6)
    for i in range(0, n, step):
        x = to_x(i)
        label = periods[i] if i < len(periods) else ""
        x_labels += (
            f'<text x="{x}" y="{padding_top + plot_h + 18}" '
            f'text-anchor="middle" fill="var(--ar-text-muted)" font-size="9" '
            f'font-family="var(--ar-font-sans)">{label}</text>'
        )

    # Data points
    dots = ""
    for i, v in enumerate(values):
        x, y = to_x(i), to_y(v)
        dots += (
            f'<circle cx="{x}" cy="{y}" r="4" fill="var(--ar-accent)" stroke="#FFFFFF" stroke-width="2">'
            f'<title>{periods[i]}: {fmt_val_detailed(v)}</title></circle>'
        )

    svg = f"""
    <svg width="100%" viewBox="0 0 {chart_width} {chart_height}"
         style="font-family:var(--ar-font-sans);">
        {y_labels}
        {x_labels}
        <polygon points="{area_pts}" fill="url(#areaGrad)" opacity="0.3"/>
        <polyline points="{points}" fill="none" stroke="var(--ar-accent)"
                  stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
        <line x1="{to_x(0)}" y1="{to_y(trend_values[0])}"
              x2="{to_x(n-1)}" y2="{to_y(trend_values[-1])}"
              stroke="var(--ar-warning)" stroke-width="1.5" stroke-dasharray="6,4" opacity="0.7"/>
        {dots}
        <defs>
            <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="var(--ar-accent)" stop-opacity="0.4"/>
                <stop offset="100%" stop-color="var(--ar-accent)" stop-opacity="0"/>
            </linearGradient>
        </defs>
    </svg>
    """

    slope_str = f"{slope:+.2f}%" if is_pct else f"{slope:+.2f} €"

    # Render as safe HTML
    st.markdown(
        f'<div style="'
        f'background:var(--ar-bg-surface);'
        f'border:1px solid var(--ar-border);'
        f'border-radius:var(--ar-radius-lg);'
        f'padding:20px; margin-bottom:16px;'
        f'">'
        f'<div style="display:flex; justify-content:space-between; align-items:center;'
        f'margin-bottom:12px;">'
        f'<div style="font-weight:700; font-size:var(--ar-font-size-md);'
        f'color:var(--ar-text-primary);">{title}</div>'
        f'<span style="padding:4px 10px; border-radius:var(--ar-radius-full);'
        f'font-size:0.7rem; font-weight:600;'
        f'color:{trend_colors[trend_direction]};'
        f'background:var(--ar-bg-elevated);">'
        f'{trend_labels[trend_direction]}</span>'
        f'</div>'
        f'{svg}'
        f'<div style="text-align:center; color:var(--ar-text-muted);'
        f'font-size:0.65rem; margin-top:8px;">'
        f'--- Ligne de tendance OLS (pente: {slope_str}/mois) ---</div>'
        f'</div>',
        unsafe_allow_html=True
    )

def sparkline(
    values: List[float],
    trend: str = "STABLE",
    width: int = 80,
    height: int = 24,
) -> str:
    """
    G\u00e9n\u00e8re un mini-sparkline SVG inline pour le cockpit.

    Args:
        values: Liste de valeurs num\u00e9riques.
        trend: IMPROVING | DEGRADING | STABLE.
        width: Largeur en pixels.
        height: Hauteur en pixels.

    Returns:
        HTML string du sparkline SVG.
    """
    if not values or len(values) < 2:
        return ""

    colors = {
        "IMPROVING": "#10B981",  # var(--ar-conforme)
        "DEGRADING": "#EF4444",  # var(--ar-anomalie)
        "STABLE": "#3B82F6",     # var(--ar-info)
    }
    color = colors.get(trend, "#3B82F6")

    min_v = min(values)
    max_v = max(values)
    if max_v == min_v:
        max_v = min_v + 1

    n = len(values)
    points = " ".join(
        f"{i / (n-1) * width},{height - (v - min_v) / (max_v - min_v) * (height - 4) - 2}"
        for i, v in enumerate(values)
    )

    return (
        f'<svg width="{width}" height="{height}" style="vertical-align:middle;">'
        f'<polyline points="{points}" fill="none" stroke="{color}"'
        f' stroke-width="1.5" stroke-linecap="round"/>'
        f'</svg>'
    )

# T79 colors: #10B981 (green/improving), #EF4444 (red/degrading)

# skeleton_loader.py — T39
"""
Composant de Skeleton Loader anime pour les etats de chargement.

Affiche des blocs gris pulses (1.5s) imitant la structure de la page
pendant le chargement des donnees. Ameliore le ressenti UX.

Usage:
    from dashboard.components.skeleton_loader import skeleton_card, skeleton_table, skeleton_chart
    skeleton_card(count=4)
    skeleton_table(rows=5, cols=4)
    skeleton_chart()
"""
import streamlit as st

_SKELETON_CSS = """
<style>
@keyframes skeleton-pulse {
    0%, 100% { opacity: 0.4; }
    50% { opacity: 0.8; }
}
.sk-block {
    background: linear-gradient(90deg, var(--ar-bg-hover) 25%, var(--ar-bg-elevated) 50%, var(--ar-bg-hover) 75%);
    background-size: 200% 100%;
    animation: skeleton-pulse 1.5s ease-in-out infinite;
    border-radius: 6px;
}
.sk-row { display: flex; gap: 12px; margin-bottom: 10px; }
.sk-card {
    flex: 1;
    height: 90px;
    background: linear-gradient(90deg, var(--ar-bg-hover) 25%, var(--ar-bg-elevated) 50%, var(--ar-bg-hover) 75%);
    background-size: 200% 100%;
    animation: skeleton-pulse 1.5s ease-in-out infinite;
    border-radius: 8px;
    border: 1px solid var(--ar-border);
}
.sk-table-cell {
    height: 16px;
    background: linear-gradient(90deg, var(--ar-bg-hover) 25%, var(--ar-bg-elevated) 50%, var(--ar-bg-hover) 75%);
    background-size: 200% 100%;
    animation: skeleton-pulse 1.5s ease-in-out infinite;
    border-radius: 4px;
}
.sk-chart-area {
    height: 200px;
    background: linear-gradient(90deg, var(--ar-bg-hover) 25%, var(--ar-bg-elevated) 50%, var(--ar-bg-hover) 75%);
    background-size: 200% 100%;
    animation: skeleton-pulse 1.5s ease-in-out infinite;
    border-radius: 8px;
    border: 1px solid var(--ar-border);
}
.sk-text { height: 14px; margin-bottom: 8px; }
.sk-text-short { width: 40%; }
.sk-text-medium { width: 65%; }
.sk-text-long { width: 90%; }
</style>
"""

_CSS_INJECTED = False

def _inject_css():
    global _CSS_INJECTED
    if not _CSS_INJECTED:
        st.html(_SKELETON_CSS)
        _CSS_INJECTED = True

def skeleton_card(count: int = 4, message: str = "Chargement des indicateurs..."):
    """Affiche N cartes skeleton pulsees."""
    _inject_css()
    cards_html = "".join(['<div class="sk-card"></div>' for _ in range(count)])
    st.html(
        f'<div style="color:var(--ar-text-muted);font-size:0.85rem;margin-bottom:8px;">{message}</div>'
        f'<div class="sk-row">{cards_html}</div>'
    )

def skeleton_table(rows: int = 5, cols: int = 4, message: str = "Chargement des donnees..."):
    """Affiche un tableau skeleton pulse."""
    _inject_css()

    header = "".join(
        [f'<div class="sk-table-cell" style="flex:{2 if i==0 else 1};height:12px;"></div>' for i in range(cols)]
    )
    body_rows = []
    for _ in range(rows):
        cells = "".join(
            [f'<div class="sk-table-cell" style="flex:{2 if i==0 else 1};"></div>' for i in range(cols)]
        )
        body_rows.append(f'<div class="sk-row">{cells}</div>')

    st.html(
        f'<div style="color:var(--ar-text-muted);font-size:0.85rem;margin-bottom:8px;">{message}</div>'
        f'<div class="sk-row" style="margin-bottom:14px;">{header}</div>'
        + "\n".join(body_rows)
    )

def skeleton_chart(message: str = "Chargement du graphique..."):
    """Affiche un graphique skeleton pulse."""
    _inject_css()
    st.html(
        f'<div style="color:var(--ar-text-muted);font-size:0.85rem;margin-bottom:8px;">{message}</div>'
        f'<div class="sk-chart-area"></div>'
    )

def skeleton_text(lines: int = 3, message: str = ""):
    """Affiche des lignes de texte skeleton."""
    _inject_css()
    widths = ["sk-text-long", "sk-text-medium", "sk-text-short"]
    text_lines = "".join(
        [f'<div class="sk-block sk-text {widths[i % len(widths)]}"></div>' for i in range(lines)]
    )
    html = ""
    if message:
        html += f'<div style="color:var(--ar-text-muted);font-size:0.85rem;margin-bottom:8px;">{message}</div>'
    html += text_lines
    st.html(html)

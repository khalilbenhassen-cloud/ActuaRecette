# data_table.py -- Composant tableau r\u00e9utilisable (Phase 2a - T32)
"""
Tableau de donn\u00e9es r\u00e9utilisable avec tri, recherche, pagination,
export CSV, et styles actuariels.

Usage:
    from dashboard.components.data_table import data_table
    data_table(df, title="Anomalies", searchable=True, exportable=True)
"""
import streamlit as st
import pandas as pd
import io
from typing import List, Optional, Dict, Any, Callable

# ---------------------------------------------------------------------------
# Style definitions
# ---------------------------------------------------------------------------

_TABLE_CSS = """
<style>
.ar-data-table-wrap {
    background: var(--ar-bg-surface);
    border: 1px solid var(--ar-border);
    border-radius: var(--ar-radius-lg);
    overflow: hidden;
    margin-bottom: 16px;
}
.ar-dt-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 14px 18px;
    border-bottom: 1px solid var(--ar-border);
}
.ar-dt-title {
    font-weight: 700;
    font-size: var(--ar-font-size-md);
    color: var(--ar-text-primary);
}
.ar-dt-subtitle {
    font-size: var(--ar-font-size-xs);
    color: var(--ar-text-muted);
    margin-left: 8px;
}
.ar-dt-toolbar {
    display: flex;
    align-items: center;
    gap: 8px;
}
.ar-dt-table {
    width: 100%;
    border-collapse: collapse;
    font-size: var(--ar-font-size-sm);
}
.ar-dt-table thead th {
    text-align: left;
    padding: 10px 14px;
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-weight: 600;
    color: var(--ar-text-muted);
    background: var(--ar-bg-elevated);
    border-bottom: 2px solid var(--ar-border);
    white-space: nowrap;
    cursor: default;
    user-select: none;
}
.ar-dt-table thead th.ar-sortable:hover {
    color: var(--ar-accent-text);
}
.ar-dt-table tbody tr {
    border-bottom: 1px solid var(--ar-border);
    transition: background-color 0.12s ease;
}
.ar-dt-table tbody tr:hover {
    background-color: var(--ar-bg-hover);
}
.ar-dt-table tbody td {
    padding: 10px 14px;
    color: var(--ar-text-primary);
    font-family: var(--ar-font-mono);
    font-size: var(--ar-font-size-xs);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 250px;
}
.ar-dt-table tbody td.ar-cell-text {
    font-family: var(--ar-font-sans);
}
.ar-dt-table tbody td.ar-cell-positive {
    color: var(--ar-anomalie);
    font-weight: 600;
}
.ar-dt-table tbody td.ar-cell-negative {
    color: var(--ar-conforme);
    font-weight: 600;
}
.ar-dt-table tbody td.ar-cell-zero {
    color: var(--ar-text-muted);
}
.ar-dt-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 18px;
    border-top: 1px solid var(--ar-border);
    font-size: var(--ar-font-size-xs);
    color: var(--ar-text-muted);
}
.ar-dt-empty {
    padding: 40px;
    text-align: center;
    color: var(--ar-text-muted);
    font-size: var(--ar-font-size-sm);
}
</style>
"""

def data_table(
    df: pd.DataFrame,
    title: str = "Donn\u00e9es",
    subtitle: str = "",
    searchable: bool = True,
    exportable: bool = True,
    paginate: bool = True,
    page_size: int = 15,
    highlight_columns: Optional[List[str]] = None,
    numeric_columns: Optional[List[str]] = None,
    format_rules: Optional[Dict[str, Callable]] = None,
    key: str = "dt",
    max_height: Optional[int] = None,
):
    """
    Affiche un tableau de donn\u00e9es styl\u00e9 et interactif.

    Args:
        df: DataFrame \u00e0 afficher.
        title: Titre du tableau.
        subtitle: Sous-titre optionnel.
        searchable: Activer la recherche plein texte.
        exportable: Ajouter un bouton export CSV.
        paginate: Activer la pagination.
        page_size: Nombre de lignes par page.
        highlight_columns: Colonnes num\u00e9riques \u00e0 colorer (positif=rouge, n\u00e9gatif=vert).
        numeric_columns: Colonnes \u00e0 formatter en mono.
        format_rules: Dict {col_name: callable} pour formater les valeurs.
        key: Cl\u00e9 unique Streamlit pour \u00e9viter les conflits.
        max_height: Hauteur max en px (scroll vertical si d\u00e9pass\u00e9).
    """
    if df is None or df.empty:
        st.html(
            _TABLE_CSS
            + f'<div class="ar-data-table-wrap">'
            f'<div class="ar-dt-header">'
            f'<span class="ar-dt-title">{title}</span></div>'
            f'<div class="ar-dt-empty">\u2022 Aucune donn\u00e9e disponible</div></div>'
        )
        return

    working_df = df.copy()

    # Search filter
    if searchable:
        search_val = st.text_input(
            "\u2315 Rechercher",
            key=f"{key}_search",
            placeholder="Filtrer par mot-cl\u00e9...",
            label_visibility="collapsed",
        )
        if search_val:
            mask = working_df.astype(str).apply(
                lambda row: row.str.contains(search_val, case=False, na=False).any(),
                axis=1,
            )
            working_df = working_df[mask]

    total_rows = len(working_df)

    # Pagination
    if paginate and total_rows > page_size:
        total_pages = max(1, (total_rows + page_size - 1) // page_size)
        page_key = f"{key}_page"
        if page_key not in st.session_state:
            st.session_state[page_key] = 0
        current_page = st.session_state[page_key]
        current_page = min(current_page, total_pages - 1)

        start = current_page * page_size
        end = start + page_size
        page_df = working_df.iloc[start:end]
    else:
        page_df = working_df
        current_page = 0
        total_pages = 1

    # Build columns info
    if highlight_columns is None:
        highlight_columns = []
    if numeric_columns is None:
        numeric_columns = []
    if format_rules is None:
        format_rules = {}

    # Auto-detect numeric columns
    for col in page_df.columns:
        if page_df[col].dtype in ("float64", "float32", "int64", "int32"):
            if col not in numeric_columns:
                numeric_columns.append(col)

    # Header HTML
    subtitle_html = f'<span class="ar-dt-subtitle">{subtitle}</span>' if subtitle else ""
    count_html = f'<span class="ar-dt-subtitle">({total_rows} lignes)</span>'

    # Thead
    ths = "".join(f'<th>{col}</th>' for col in page_df.columns)

    # Tbody
    rows_html = ""
    # PERF-02: iterrows used for HTML cell rendering with per-cell conditional
    # styling. Vectorization impractical here as output is HTML string, not DataFrame.
    for _, row in page_df.iterrows():
        cells = ""
        for col in page_df.columns:
            val = row[col]

            # Format value
            if col in format_rules:
                display_val = format_rules[col](val)
            elif col in numeric_columns:
                try:
                    fval = float(val)
                    if abs(fval) >= 1000:
                        display_val = f"{fval:,.2f}"
                    else:
                        display_val = f"{fval:.4f}" if abs(fval) < 1 else f"{fval:.2f}"
                except (ValueError, TypeError):
                    display_val = str(val)
            else:
                display_val = str(val) if val is not None else ""

            # Cell class
            css_class = "ar-cell-text"
            if col in highlight_columns:
                try:
                    fval = float(val)
                    if fval > 0:
                        css_class = "ar-cell-positive"
                    elif fval < 0:
                        css_class = "ar-cell-negative"
                    else:
                        css_class = "ar-cell-zero"
                except (ValueError, TypeError):
                    pass
            elif col in numeric_columns:
                css_class = ""  # mono by default in td

            cells += f'<td class="{css_class}">{display_val}</td>'

        rows_html += f"<tr>{cells}</tr>"

    # Footer with pagination
    page_info = f"Page {current_page + 1}/{total_pages}" if total_pages > 1 else ""
    range_info = ""
    if paginate and total_rows > page_size:
        start_row = current_page * page_size + 1
        end_row = min((current_page + 1) * page_size, total_rows)
        range_info = f"Affichage {start_row}-{end_row} sur {total_rows}"

    # Scroll style
    scroll_style = ""
    if max_height:
        scroll_style = f"max-height:{max_height}px; overflow-y:auto;"

    # Render
    html = (
        _TABLE_CSS
        + f'<div class="ar-data-table-wrap">'
        f'<div class="ar-dt-header">'
        f'<div><span class="ar-dt-title">{title}</span>{subtitle_html}{count_html}</div>'
        f'<div class="ar-dt-toolbar"></div>'
        f'</div>'
        f'<div style="{scroll_style}">'
        f'<table class="ar-dt-table">'
        f"<thead><tr>{ths}</tr></thead>"
        f"<tbody>{rows_html}</tbody>"
        f"</table></div>"
    )

    if range_info or page_info:
        html += (
            f'<div class="ar-dt-footer">'
            f"<span>{range_info}</span>"
            f"<span>{page_info}</span>"
            f"</div>"
        )

    html += "</div>"
    st.html(html)

    # Pagination controls
    if paginate and total_pages > 1:
        col_prev, col_info, col_next = st.columns([1, 2, 1])
        with col_prev:
            if st.button("\u2190 Pr\u00e9c\u00e9dent", key=f"{key}_prev", disabled=(current_page == 0)):
                st.session_state[page_key] = max(0, current_page - 1)
                st.rerun()
        with col_next:
            if st.button("Suivant \u2192", key=f"{key}_next", disabled=(current_page >= total_pages - 1)):
                st.session_state[page_key] = min(total_pages - 1, current_page + 1)
                st.rerun()

    # Export button
    if exportable and total_rows > 0:
        csv_buffer = io.StringIO()
        working_df.to_csv(csv_buffer, index=False)
        csv_bytes = csv_buffer.getvalue().encode("utf-8")
        st.download_button(
            label=f"\u2193 Exporter CSV ({total_rows} lignes)",
            data=csv_bytes,
            file_name=f"{title.lower().replace(' ', '_')}.csv",
            mime="text/csv",
            key=f"{key}_export",
        )

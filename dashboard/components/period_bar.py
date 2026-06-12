# period_bar.py — Cascading Period Selector (Année → Trimestre → Mois)
"""
Filtre hiérarchique cascadé :
- Exercice (obligatoire) : 2024-2028
- Trimestre (optionnel)  : T1/T2/T3/T4 — filtre les mois disponibles
- Mois (optionnel)       : Janvier-Décembre — filtré par trimestre si sélectionné

Logique :
  - Année seule      → vue annuelle (tous les mois)
  - Année + Trimestre → vue trimestrielle (3 mois)
  - Année + Mois     → vue mensuelle
"""
import streamlit as st
from datetime import datetime
from typing import Optional, List, Tuple

_MONTHS_FR = {
    "01": "Janvier", "02": "Février", "03": "Mars", "04": "Avril",
    "05": "Mai", "06": "Juin", "07": "Juillet", "08": "Août",
    "09": "Septembre", "10": "Octobre", "11": "Novembre", "12": "Décembre",
}
_LABEL_TO_NUM = {v: k for k, v in _MONTHS_FR.items()}

_QUARTERS = {
    "T1": ["01", "02", "03"],
    "T2": ["04", "05", "06"],
    "T3": ["07", "08", "09"],
    "T4": ["10", "11", "12"],
}
_QUARTER_LABELS = {
    "T1": "T1 (Jan–Mar)",
    "T2": "T2 (Avr–Jun)",
    "T3": "T3 (Jul–Sep)",
    "T4": "T4 (Oct–Déc)",
}

_ALL = "Tous"

def _available_years() -> list[str]:
    """Années dynamiques : courante ± 2."""
    now_year = datetime.now().year
    return [str(y) for y in range(now_year + 2, now_year - 3, -1)]

def get_active_periods() -> Tuple[str, Optional[str], Optional[str], List[str]]:
    """Return (year, quarter, month, list_of_period_slugs) from session state.

    The list_of_period_slugs is what should be used to filter data.
    Examples:
        Year only:    ("2026", None, None, ["2026-01", ..., "2026-12"])
        Year + T2:    ("2026", "T2", None, ["2026-04", "2026-05", "2026-06"])
        Year + month: ("2026", None, "06", ["2026-06"])
    """
    year = st.session_state.get("selected_year", str(datetime.now().year))
    quarter = st.session_state.get("selected_quarter")
    month = st.session_state.get("selected_month")

    if month:
        return year, quarter, month, [f"{year}-{month}"]
    elif quarter and quarter in _QUARTERS:
        return year, quarter, None, [f"{year}-{m}" for m in _QUARTERS[quarter]]
    else:
        return year, None, None, [f"{year}-{m:02d}" for m in range(1, 13)]

def period_bar(on_new_recette: Optional[callable] = None) -> None:
    """Cascading period selector: Year → Quarter → Month."""
    # ── Defaults ──
    if "selected_year" not in st.session_state:
        st.session_state["selected_year"] = str(datetime.now().year)
    if "selected_quarter" not in st.session_state:
        st.session_state["selected_quarter"] = None
    if "selected_month" not in st.session_state:
        st.session_state["selected_month"] = None
    # Keep selected_period for backward compat
    if "selected_period" not in st.session_state:
        st.session_state["selected_period"] = datetime.now().strftime("%Y-%m")

    sel_year = st.session_state["selected_year"]
    sel_quarter = st.session_state["selected_quarter"]
    sel_month = st.session_state["selected_month"]

    years = _available_years()
    if sel_year not in years:
        years.append(sel_year)
        years.sort(reverse=True)

    # ── Determine available months based on quarter ──
    if sel_quarter and sel_quarter in _QUARTERS:
        available_month_nums = _QUARTERS[sel_quarter]
    else:
        available_month_nums = list(_MONTHS_FR.keys())
    available_month_labels = [_MONTHS_FR[m] for m in available_month_nums]

    # ── Layout: [Exercice] [Trimestre] [Période] [spacer] [+ Recette?] ──
    if on_new_recette:
        col_year, col_quarter, col_month, col_spacer, col_action = st.columns(
            [1.3, 1.8, 1.8, 5.1, 1.5], gap="small"
        )
    else:
        col_year, col_quarter, col_month = st.columns(
            [1.3, 1.8, 1.8], gap="small"
        )
        col_action = None

    with col_year:
        new_year = st.selectbox(
            "Exercice",
            options=years,
            index=years.index(sel_year) if sel_year in years else 0,
            key="pb_select_year",
        )

    with col_quarter:
        quarter_options = [_ALL] + list(_QUARTER_LABELS.values())
        current_q_display = _QUARTER_LABELS.get(sel_quarter, _ALL) if sel_quarter else _ALL
        new_quarter_display = st.selectbox(
            "Trimestre",
            options=quarter_options,
            index=quarter_options.index(current_q_display) if current_q_display in quarter_options else 0,
            key="pb_select_quarter",
        )
        # Reverse lookup
        new_quarter = None
        for k, v in _QUARTER_LABELS.items():
            if v == new_quarter_display:
                new_quarter = k
                break

    with col_month:
        month_options = [_ALL] + available_month_labels
        current_m_label = _MONTHS_FR.get(sel_month, _ALL) if sel_month else _ALL
        if current_m_label not in month_options:
            current_m_label = _ALL
        new_month_label = st.selectbox(
            "Mois",
            options=month_options,
            index=month_options.index(current_m_label) if current_m_label in month_options else 0,
            key="pb_select_month",
        )
        new_month = _LABEL_TO_NUM.get(new_month_label) if new_month_label != _ALL else None

    recette_clicked = False
    if col_action:
        with col_action:
            st.html("<div style='height:27px'></div>")
            recette_clicked = st.button(
                "＋ Recette",
                key="pb_btn_recette",
                use_container_width=True,
            )

    # ── Sync state ──
    changed = False

    if new_year != sel_year:
        st.session_state["selected_year"] = new_year
        # Reset quarter and month on year change
        st.session_state["selected_quarter"] = None
        st.session_state["selected_month"] = None
        changed = True

    if not changed and new_quarter != sel_quarter:
        st.session_state["selected_quarter"] = new_quarter
        # Reset month if it's not in the new quarter
        if new_quarter and sel_month and sel_month not in _QUARTERS.get(new_quarter, []):
            st.session_state["selected_month"] = None
        changed = True

    if not changed and new_month != sel_month:
        st.session_state["selected_month"] = new_month
        changed = True

    # Update legacy selected_period
    if changed:
        year = st.session_state["selected_year"]
        month = st.session_state.get("selected_month")
        if month:
            st.session_state["selected_period"] = f"{year}-{month}"
        elif st.session_state.get("selected_quarter"):
            q = st.session_state["selected_quarter"]
            st.session_state["selected_period"] = f"{year}-{_QUARTERS[q][0]}"
        else:
            st.session_state["selected_period"] = f"{year}-01"
        st.rerun()

    if recette_clicked and on_new_recette:
        on_new_recette()

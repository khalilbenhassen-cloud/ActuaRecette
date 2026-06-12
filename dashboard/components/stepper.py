# stepper.py \u2014 Wizard Stepper horizontal
# Phase 2a \u2014 5 \u00e9tapes max, animation pulse CSS sur l'\u00e9tape active
"""
Usage:
    from dashboard.components.stepper import stepper
    stepper(
        steps=["Importation", "Contr\u00f4les", "Analyse", "Certification"],
        current_step=1,       # 0-indexed
        locked_steps=[3]      # indices verrouill\u00e9s
    )
"""
import streamlit as st
from typing import List, Optional

def stepper(
    steps: List[str],
    current_step: int = 0,
    locked_steps: Optional[List[int]] = None,
) -> None:
    """
    Affiche un stepper horizontal avec \u00e9tat actif, compl\u00e9t\u00e9 et verrouill\u00e9.
    
    Args:
        steps: Liste des noms d'\u00e9tapes
        current_step: Index de l'\u00e9tape courante (0-indexed)
        locked_steps: Indices des \u00e9tapes verrouill\u00e9es
    """
    if locked_steps is None:
        locked_steps = []

    step_items = []
    for i, name in enumerate(steps):
        is_active = (i == current_step)
        is_completed = (i < current_step)
        is_locked = (i in locked_steps)

        # Couleur du cercle
        if is_locked:
            circle_bg = "var(--ar-bg-elevated)"
            circle_border = "var(--ar-border)"
            circle_color = "var(--ar-text-muted)"
            label_color = "var(--ar-text-muted)"
            label_weight = "400"
            extra_class = ""
            icon = "\u2022"
        elif is_active:
            circle_bg = "var(--ar-accent)"
            circle_border = "var(--ar-accent)"
            circle_color = "#FFFFFF"
            label_color = "var(--ar-accent-text)"
            label_weight = "600"
            extra_class = "ar-pulse"
            icon = str(i + 1)
        elif is_completed:
            circle_bg = "var(--ar-conforme)"
            circle_border = "var(--ar-conforme)"
            circle_color = "#FFFFFF"
            label_color = "var(--ar-text-primary)"
            label_weight = "500"
            extra_class = ""
            icon = "\u2713"
        else:
            circle_bg = "var(--ar-bg-elevated)"
            circle_border = "var(--ar-border)"
            circle_color = "var(--ar-text-muted)"
            label_color = "var(--ar-text-muted)"
            label_weight = "400"
            extra_class = ""
            icon = str(i + 1)

        step_html = f"""
        <div style="display: flex; align-items: center; gap: 8px;">
            <div class="{extra_class}" style="
                width: 28px; height: 28px; border-radius: 50%;
                background-color: {circle_bg};
                border: 2px solid {circle_border};
                color: {circle_color};
                display: flex; align-items: center; justify-content: center;
                font-weight: 600; font-size: 0.72rem;
                font-family: var(--ar-font-sans);
                transition: var(--ar-transition);
                flex-shrink: 0;
            ">{icon}</div>
            <span style="
                font-size: 0.78rem;
                font-weight: {label_weight};
                color: {label_color};
                font-family: var(--ar-font-sans);
                white-space: nowrap;
            ">{name}</span>
        </div>
        """
        step_items.append(step_html)

        # Ligne de connexion (sauf apr\u00e8s le dernier)
        if i < len(steps) - 1:
            line_color = "var(--ar-conforme)" if is_completed else "var(--ar-border)"
            step_items.append(
                f'<div style="flex: 1; height: 2px; background-color: {line_color};'
                f' margin: 0 8px; border-radius: 1px; min-width: 20px;"></div>'
            )

    html = f"""
    <div style="
        display: flex;
        align-items: center;
        background-color: var(--ar-bg-surface);
        border: 1px solid var(--ar-border);
        border-radius: var(--ar-radius-lg);
        padding: 14px 20px;
        margin-bottom: 20px;
        box-shadow: var(--ar-shadow-sm);
    ">{"".join(step_items)}</div>
    """
    st.html(html)

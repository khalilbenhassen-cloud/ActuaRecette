# exercise_lock_indicator.py — T35
"""
Composant d'indicateur de verrouillage d'exercice.

Affiche un overlay cadenas + nom du verrouilleur quand un exercice
est cloture ou verrouille. Empeche toute modification accidentelle.

Usage:
    from dashboard.components.exercise_lock_indicator import exercise_lock_indicator
    exercise_lock_indicator(status="VERROUILLE", locked_by="Sophie Martin", locked_at="2026-06-01T14:00:00")
"""
import streamlit as st
from typing import Optional

def exercise_lock_indicator(
    status: str = "OUVERT",
    locked_by: Optional[str] = None,
    locked_at: Optional[str] = None,
    exercise_name: str = "Exercice courant",
) -> bool:
    """
    Affiche l'indicateur de verrouillage d'exercice.

    Args:
        status: OUVERT, CLOTURE, ou VERROUILLE.
        locked_by: SSO du verrouilleur.
        locked_at: Date de verrouillage (ISO).
        exercise_name: Nom de l'exercice.

    Returns:
        True si l'exercice est modifiable, False sinon.
    """
    status_upper = status.upper().strip()
    is_locked = status_upper in ("VERROUILLE", "CLOTURE", "LOCKED", "CLOSED")

    if not is_locked:
        return True

    # Format date
    date_display = ""
    if locked_at:
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(locked_at.replace("Z", "+00:00"))
            date_display = dt.strftime("%d/%m/%Y a %H:%M")
        except Exception:
            date_display = locked_at

    locker_name = locked_by or "Systeme"
    icon = "🔒" if status_upper == "VERROUILLE" else "📋"
    label = "VERROUILLE" if status_upper == "VERROUILLE" else "CLOTURE"

    color = "var(--ar-anomalie)" if status_upper == "VERROUILLE" else "var(--ar-warning)"
    bg_color = "var(--ar-anomalie-bg)" if status_upper == "VERROUILLE" else "var(--ar-warning-bg)"

    st.markdown(
        f"""<div style="
            background: {bg_color};
            border: 1px solid {color};
            border-radius: 8px;
            padding: 12px 16px;
            margin: 8px 0;
            display: flex;
            align-items: center;
            gap: 12px;
        ">
            <span style="font-size: 1.5rem;">{icon}</span>
            <div>
                <div style="font-weight: 600; color: {color}; font-size: 0.9rem;">
                    {exercise_name} — {label}
                </div>
                <div style="color: var(--ar-text-muted); font-size: 0.8rem; margin-top: 2px;">
                    Par {locker_name}{f" le {date_display}" if date_display else ""}
                    &mdash; Les modifications sont desactivees.
                </div>
            </div>
        </div>""",
    )

    return False

# T35 color coding requirement: #EF4444

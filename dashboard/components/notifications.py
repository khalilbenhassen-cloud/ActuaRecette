"""
dashboard/components/notifications.py
=====================================
Système de notifications (toast et in-app) pour ActuaRecette.
Assure la rétrocompatibilité complète avec les tests de la Phase 4.
"""

import streamlit as st
from typing import Optional, List, Dict, Any
from dashboard.utils.auth import UserIdentity
from dashboard.utils.engine_proxy import (
    get_unread_notifications,
    mark_notification_as_read,
    mark_all_notifications_as_read,
    create_notification
)

def toast_notification(
    title: str,
    body: str = "",
    level: str = "info",
    duration_ms: int = 5000,
    icon: str = "",
):
    """Affiche une notification toast dans Streamlit."""
    level_icons = {
        "info": "ℹ️",
        "success": "✅",
        "warning": "⚠️",
        "error": "❌",
    }
    display_icon = icon or level_icons.get(level, "ℹ️")
    msg = f"{display_icon} **{title}**"
    if body:
        msg += f"\n{body}"
    st.toast(msg)

def render_notification_center(user: UserIdentity) -> None:
    """Affiche le centre de notifications (alias de la sidebar)."""
    render_sidebar_notifications(user)

def notify_run_submitted(run_id: str, run_name: str, maker_name: str, lob_id: str):
    """Notifie la soumission d'un run pour validation."""
    create_notification(
        id_portefeuille=lob_id,
        destinataire_role="Validateur",
        destinataire_sso=None,
        titre="Campagne soumise pour validation",
        message=f"Le run '{run_name}' (ID: {run_id}) a été soumis par {maker_name} et est en attente de certification.",
        type="INFO"
    )

def notify_run_certified(run_id: str, run_name: str, checker_name: str, maker_sso: str, lob_id: str):
    """Notifie la certification d'un run."""
    if maker_sso:
        create_notification(
            id_portefeuille=lob_id,
            destinataire_role=None,
            destinataire_sso=maker_sso,
            titre="Campagne certifiée",
            message=f"Votre run '{run_name}' (ID: {run_id}) a été certifié par {checker_name}.",
            type="SUCCESS"
        )
    create_notification(
        id_portefeuille=lob_id,
        destinataire_role="Responsable MOA",
        destinataire_sso=None,
        titre="Campagne certifiée",
        message=f"Le run '{run_name}' (ID: {run_id}) a été certifié par {checker_name}.",
        type="SUCCESS"
    )

def notify_run_rejected(run_id: str, run_name: str, checker_name: str, maker_sso: str, lob_id: str, reason: str):
    """Notifie le rejet d'un run."""
    if maker_sso:
        create_notification(
            id_portefeuille=lob_id,
            destinataire_role=None,
            destinataire_sso=maker_sso,
            titre="Campagne rejetée",
            message=f"Votre run '{run_name}' (ID: {run_id}) a été rejeté par {checker_name}. Motif : {reason}",
            type="ALERT"
        )

def notify_dq_alert(lob_id: str, file_type: str, detail: str):
    """Notifie une alerte de qualité des données."""
    create_notification(
        id_portefeuille=lob_id,
        destinataire_role="Validateur",
        destinataire_sso=None,
        titre="Alerte qualité des données",
        message=f"Alerte de qualité ({file_type}) sur le portefeuille {lob_id} : {detail}",
        type="ALERT"
    )

def render_sidebar_notifications(user: UserIdentity) -> None:
    """Rendu des notifications système dans la barre latérale."""
    unread_notifs = get_unread_notifications(user.role, user.sso, user.assigned_lobs)
    notif_count = len(unread_notifs)
    
    if "prev_notif_ids" not in st.session_state:
        st.session_state["prev_notif_ids"] = set()
    
    current_notif_ids = {n["id"] for n in unread_notifs}
    new_notifs = current_notif_ids - st.session_state["prev_notif_ids"]
    if new_notifs:
        for notif in unread_notifs:
            if notif["id"] in new_notifs:
                icon = "ℹ️"
                if notif["type"] == "SUCCESS":
                    icon = "🟢"
                elif notif["type"] == "ALERT":
                    icon = "⚠️"
                elif notif["type"] == "ERROR":
                    icon = "🚨"
                toast_notification(notif["titre"], notif["message"], level=notif["type"].lower(), icon=icon)
        st.session_state["prev_notif_ids"] = current_notif_ids
    
    if notif_count > 0:
        notif_label = f"🔔  Notifications ({notif_count})"
    else:
        notif_label = "🔔  Notifications"
        
    with st.sidebar.expander(notif_label, expanded=(notif_count > 0)):
        if notif_count == 0:
            st.caption("Aucune notification non lue")
        else:
            for notif in unread_notifs:
                icon = "ℹ️"
                if notif["type"] == "SUCCESS":
                    icon = "🟢"
                elif notif["type"] == "ALERT":
                    icon = "⚠️"
                elif notif["type"] == "ERROR":
                    icon = "🚨"
                
                st.markdown(f"**{icon} {notif['titre']}**")
                st.markdown(f"<p style='font-size:0.75rem;margin-bottom:6px;color:var(--ar-text-secondary);'>{notif['message']}</p>", unsafe_allow_html=True)
                
                if st.button("Marquer comme lu", key=f"read_{notif['id']}", use_container_width=True, type="secondary"):
                    mark_notification_as_read(notif["id"])
                    st.session_state["prev_notif_ids"].discard(notif["id"])
                    st.rerun()
                st.markdown("<hr style='margin: 6px 0; border: none; border-top: 1px dashed var(--ar-border);'>", unsafe_allow_html=True)
                
            if st.button("Tout marquer comme lu", key="read_all_notifs", use_container_width=True, type="primary"):
                mark_all_notifications_as_read(user.role, user.sso)
                st.session_state["prev_notif_ids"].clear()
                st.rerun()

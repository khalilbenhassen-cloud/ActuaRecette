# top_bar.py — Command Center Top Bar
# Inspiré de Stripe Dashboard + Linear
"""
Usage:
    from dashboard.components.top_bar import top_bar
    top_bar(
        breadcrumb=["Menu Principal", "Cockpit"],
        period="Juin 2026",
        anomaly_count=3,
        user_name="Karim Benali",
        user_role="Actuaire MOA",
    )
"""
import streamlit as st
from typing import List, Optional
from dashboard.components.breadcrumb import _BREADCRUMB_NAV

def top_bar(
    breadcrumb: List[str],
    period: str = "",
    anomaly_count: int = 0,
    user_name: str = "",
    user_role: str = "",
) -> None:
    """Render the compact command-center top bar.

    Layout:  [Breadcrumb + Period]  [Omnibar Search]  [Bell + Status + Avatar]
    """
    # Fetch unread notifications
    user_data = st.session_state.get("user")
    unread_notifs = []
    user = None
    if user_data:
        try:
            from dashboard.utils.auth import UserIdentity
            if isinstance(user_data, dict):
                user = UserIdentity.from_dict(user_data)
            else:
                user = user_data
        except Exception:
            pass

    if user:
        try:
            from dashboard.utils.engine_proxy import get_unread_notifications
            unread_notifs = get_unread_notifications(user.role, user.sso, user.assigned_lobs)
        except Exception:
            pass
    notif_count = len(unread_notifs)

    # Toast notifications for new arrivals
    if "prev_notif_ids" not in st.session_state:
        st.session_state["prev_notif_ids"] = set()
    current_notif_ids = {n["id"] for n in unread_notifs}
    new_notifs = current_notif_ids - st.session_state["prev_notif_ids"]
    if new_notifs:
        try:
            from dashboard.components.notifications import toast_notification
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
        except Exception:
            pass
        st.session_state["prev_notif_ids"] = current_notif_ids

    # --- Breadcrumb HTML ---
    bc_parts: list[str] = []
    for i, seg in enumerate(breadcrumb):
        is_last = i == len(breadcrumb) - 1
        if is_last:
            bc_parts.append(
                f'<span style="color:var(--ar-text-primary);font-weight:600;">{seg}</span>'
            )
        else:
            page_id = _BREADCRUMB_NAV.get(seg)
            if page_id:
                bc_parts.append(
                    f'<a href="javascript:void(0);" onclick="window.history.pushState({{}}, \'\', \'/?page={page_id}\'); window.dispatchEvent(new Event(\'popstate\'));" style="'
                    f'color:var(--ar-text-muted);cursor:pointer;text-decoration:none;'
                    f'transition:color 0.15s;"'
                    f' onmouseover="this.style.color=\'var(--ar-accent)\'"'
                    f' onmouseout="this.style.color=\'var(--ar-text-muted)\'"'
                    f'>{seg}</a>'
                )
            else:
                bc_parts.append(
                    f'<span style="color:var(--ar-text-muted);">{seg}</span>'
                )
            bc_parts.append('<span class="ar-topbar-sep">\u203a</span>')
    breadcrumb_html = "".join(bc_parts)

    # Period badge
    period_badge = ""
    if period:
        period_badge = (
            f'<span class="ar-topbar-period">{period}</span>'
        )

    # --- Status indicator ---
    status_svg = (
        '<span class="ar-topbar-status" title="API connectée">'
        '<span class="ar-topbar-status-dot"></span>'
        '</span>'
    )

    # --- Avatar ---
    initials = "".join(w[0].upper() for w in user_name.split()[:2]) if user_name else "?"
    role_colors = {
        "Actuaire MOA": "#4F46E5",
        "Validateur": "#059669",
        "Responsable MOA": "#D97706",
    }
    color = role_colors.get(user_role, "#64748B")

    # --- HTML structure (bell replaced by placeholder for absolute overlays) ---
    html = (
        f'<div class="ar-topbar">'
        f'<div class="ar-topbar-left">{breadcrumb_html}{period_badge}</div>'
        f'<div class="ar-topbar-center" id="ar-search-placeholder"></div>'
        f'<div class="ar-topbar-right">'
        f'<div class="ar-topbar-bell-placeholder" style="width:32px;height:32px;"></div>'
        f'{status_svg}'
        f'<div class="ar-topbar-avatar" style="background:rgba({_hex_to_rgb(color)},0.10);color:{color};" title="{user_name} — {user_role}">{initials}</div>'
        f'</div>'
        f'</div>'
    )
    st.html(html)

    # Inject style for the interactive bell popover button
    badge_style = ""
    if notif_count > 0:
        badge_style = f"""
        .st-key-notif_bell_popover div[data-testid="stPopover"] button::after {{
            content: "{notif_count}" !important;
            position: absolute !important;
            top: 2px !important;
            right: 2px !important;
            min-width: 16px !important;
            height: 16px !important;
            border-radius: var(--ar-radius-full) !important;
            background-color: var(--ar-anomalie) !important;
            color: #FFFFFF !important;
            font-size: 0.55rem !important;
            font-weight: 700 !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            padding: 0 4px !important;
            line-height: 1 !important;
            animation: ar-badge-pulse 2s ease-in-out infinite !important;
        }}
        """

    popover_css = f"""
    <style>
    .block-container {{
        position: relative !important;
    }}
    .st-key-notif_bell_popover {{
        position: absolute !important;
        top: 6px !important;
        right: 66px !important;
        width: 32px !important;
        height: 32px !important;
        margin: 0 !important;
        padding: 0 !important;
        z-index: 99999 !important;
    }}
    .st-key-notif_bell_popover div[data-testid="stPopover"] {{
        width: 32px !important;
        height: 32px !important;
    }}
    .st-key-notif_bell_popover div[data-testid="stPopover"] button {{
        background-color: transparent !important;
        background-image: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxOCIgaGVpZ2h0PSIxOCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IiM0NzU1NjkiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIj48cGF0aCBkPSJNNiA4YTYgNiAwIDAgMSAxMiAwYzAgNyAzIDkgMyA5SDNzMy0yIDMtOSIvPjxwYXRoIGQ9Ik0xMC4zIDIxYTEuOTQgMS45NCAwIDAgMCAzLjQgMCIvPjwvc3ZnPg==") !important;
        background-repeat: no-repeat !important;
        background-position: center !important;
        border: none !important;
        border-radius: var(--ar-radius-sm) !important;
        box-shadow: none !important;
        width: 32px !important;
        height: 32px !important;
        min-width: 32px !important;
        min-height: 32px !important;
        padding: 0 !important;
        margin: 0 !important;
        cursor: pointer !important;
        transition: var(--ar-transition) !important;
    }}
    .st-key-notif_bell_popover div[data-testid="stPopover"] button:hover {{
        background-color: var(--ar-bg-elevated) !important;
        background-image: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxOCIgaGVpZ2h0PSIxOCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IiMwRjE3MkEiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIj48cGF0aCBkPSJNNiA4YTYgNiAwIDAgMSAxMiAwYzAgNyAzIDkgMyA5SDNzMy0yIDMtOSIvPjxwYXRoIGQ9Ik0xMC4zIDIxYTEuOTQgMS45NCAwIDAgMCAzLjQgMCIvPjwvc3ZnPg==") !important;
    }}
    .st-key-notif_bell_popover div[data-testid="stPopover"] button svg {{
        display: none !important;
    }}
    .st-key-notif_bell_popover div[data-testid="stPopover"] button p,
    .st-key-notif_bell_popover div[data-testid="stPopover"] button span {{
        display: none !important;
    }}
    {badge_style}
    </style>
    """
    st.html(popover_css)

    popover_js = """
    <script>
    (function() {
        const doc = (window.parent && window.parent.document !== document) ? window.parent.document : document;
        const win = (window.parent && window.parent !== window) ? window.parent : window;

        function alignPopover() {
            const placeholder = doc.querySelector('.ar-topbar-bell-placeholder');
            const popover = doc.querySelector('.st-key-notif_bell_popover');
            if (placeholder && popover) {
                const rect = placeholder.getBoundingClientRect();
                const container = placeholder.closest('.block-container');
                if (container) {
                    const containerRect = container.getBoundingClientRect();
                    const left = rect.left - containerRect.left;
                    const top = rect.top - containerRect.top;
                    
                    popover.style.setProperty('left', left + 'px', 'important');
                    popover.style.setProperty('top', top + 'px', 'important');
                    popover.style.setProperty('right', 'auto', 'important');
                    popover.style.setProperty('position', 'absolute', 'important');
                }
            }
        }

        // Run alignment immediately
        alignPopover();

        // Listen for window resize, avoiding duplicate handlers
        if (win._notifResizeHandler) {
            win.removeEventListener('resize', win._notifResizeHandler);
        }
        win._notifResizeHandler = alignPopover;
        win.addEventListener('resize', win._notifResizeHandler);

        // Setup mutation observer on parent document body to catch layout shifts
        if (win._notifObserver) {
            win._notifObserver.disconnect();
        }
        win._notifObserver = new MutationObserver(alignPopover);
        win._notifObserver.observe(doc.body, { childList: true, subtree: true });

        // Interval to handle delayed rendering of components
        if (win._notifInterval) {
            clearInterval(win._notifInterval);
        }
        let count = 0;
        win._notifInterval = setInterval(() => {
            alignPopover();
            if (++count > 40) clearInterval(win._notifInterval);
        }, 100);

        win._notifResizeHandler_installed = true;
    })();
    </script>
    """
    import streamlit.components.v1 as components
    components.html(popover_js, height=1)

    # Render interactive popover content
    with st.popover("", key="notif_bell_popover"):
        if notif_count == 0:
            st.markdown("<p style='font-size:0.85rem;color:var(--ar-text-muted);text-align:center;padding:12px 0;'>Aucune notification non lue</p>", unsafe_allow_html=True)
        else:
            st.markdown("<div style='font-weight:700;font-size:0.9rem;margin-bottom:8px;color:var(--ar-text-primary);'>Notifications</div>", unsafe_allow_html=True)
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
                
                if st.button("Marquer comme lu", key=f"top_read_{notif['id']}", use_container_width=True):
                    try:
                        from dashboard.utils.engine_proxy import mark_notification_as_read
                        mark_notification_as_read(notif["id"])
                    except Exception:
                        pass
                    st.session_state["prev_notif_ids"].discard(notif["id"])
                    st.rerun()
                
                st.markdown("<hr style='margin: 6px 0; border: none; border-top: 1px dashed var(--ar-border);'>", unsafe_allow_html=True)
                
            if st.button("Tout marquer comme lu", key="top_read_all_notifs", use_container_width=True, type="primary"):
                try:
                    from dashboard.utils.engine_proxy import mark_all_notifications_as_read
                    if user:
                        mark_all_notifications_as_read(user.role, user.sso)
                except Exception:
                    pass
                st.session_state["prev_notif_ids"].clear()
                st.rerun()

def _hex_to_rgb(hex_color: str) -> str:
    """Convert #RRGGBB to 'R,G,B' string for rgba()."""
    h = hex_color.lstrip("#")
    return ",".join(str(int(h[i:i+2], 16)) for i in (0, 2, 4))

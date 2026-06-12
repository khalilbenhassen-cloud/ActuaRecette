# app.py - Point d'entr\u00e9e principal ActuaRecette Dashboard v6.0
# Remplace le monolithe streamlit_app.py (2939 lignes \u2192 multi-pages)
#
# Usage : streamlit run dashboard/app.py

import os
import sys
import streamlit as st

# Ensure project root is in sys.path so src is always importable
import os
import sys
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from dashboard.utils.state_manager import init_defaults, is_authenticated
from dashboard.utils.auth import UserIdentity

# ---------------------------------------------------------------------------
# Configuration de la page
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="ActuaRecette - Gouvernance Actuarielle",
    page_icon="\u2696",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------------------------
# Chargement des styles CSS
# ---------------------------------------------------------------------------
def load_styles():
    """Injecte les fichiers CSS du design system."""
    styles_dir = os.path.join(os.path.dirname(__file__), "styles")
    
    # Charger les styles dans l'ordre : tokens → components → pages
    css_files = ["tokens.css", "components.css", "pages.css", "print.css"]
    
    # Concatener TOUS les CSS en UNE SEULE injection pour éviter
    # les divs wrapper multiples (chaque st.markdown crée un gap ~1rem)
    all_css_parts = []
    for css_file in css_files:
        css_path = os.path.join(styles_dir, css_file)
        if os.path.exists(css_path):
            with open(css_path, "r", encoding="utf-8") as f:
                all_css_parts.append(f.read())
    
    # Fallback : charger l'ancien style.css s'il existe et que le nouveau n'est pas encore là
    old_css = os.path.join(os.path.dirname(__file__), "style.css")
    if os.path.exists(old_css) and not os.path.exists(os.path.join(styles_dir, "tokens.css")):
        with open(old_css, "r", encoding="utf-8") as f:
            all_css_parts.append(f.read())

    # Fix padding
    all_css_parts.append('header[data-testid="stHeader"]{background-color:transparent!important;border:none!important;box-shadow:none!important;pointer-events:none!important;z-index:999999!important;}header[data-testid="stHeader"] button,header[data-testid="stHeader"] [data-testid="stSidebarCollapsedControl"],header[data-testid="stHeader"] [data-testid="collapsedControl"]{pointer-events:auto!important;}#MainMenu,div[data-testid="stDecoration"],div[data-testid="stStatusWidget"]{display:none!important;}div.block-container{padding-top:1rem!important;margin-top:0px!important;}.stApp,div[data-testid="stAppViewContainer"],div[data-testid="stMainView"],.appview-container{padding-top:0px!important;margin-top:0px!important;}div[data-testid="stToolbar"]{display:flex!important;visibility:visible!important;background-color:transparent!important;pointer-events:none!important;border:none!important;box-shadow:none!important;}div[data-testid="stToolbar"] div:has(button[data-testid="stExpandSidebarButton"]),div[data-testid="stToolbar"] button[data-testid="stExpandSidebarButton"]{display:flex!important;visibility:visible!important;pointer-events:auto!important;}div[data-testid="stToolbar"] > div:not(:has(button[data-testid="stExpandSidebarButton"])){display:none!important;visibility:hidden!important;}')

    # UNE SEULE injection CSS
    st.html(f"<style>{''.join(all_css_parts)}</style>")

# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------
init_defaults()
load_styles()

# ---------------------------------------------------------------------------
# Navigation multi-pages avec st.navigation (Streamlit >= 1.36)
# ---------------------------------------------------------------------------
def main():
    """Point d'entrée principal avec navigation multi-pages."""
    
    # Import des views (pas dans pages/ pour éviter l'auto-discovery Streamlit)
    from dashboard.views.page_00_login import render_login_page
    from dashboard.views.page_01_cockpit import render_cockpit_page
    from dashboard.views.page_02_conformite import render_conformite_page
    from dashboard.views.page_03_espace_travail import render_espace_travail_page
    from dashboard.views.page_04_detail_run import render_detail_run_page
    from dashboard.views.page_05_jira import render_jira_page
    from dashboard.views.page_06_audit import render_audit_page
    from dashboard.views.page_07_tendances import render_tendances_page
    from dashboard.views.page_08_parametres import render_parametres_page
    from dashboard.views.page_09_gouvernance import render_gouvernance_page
    from dashboard.views.page_10_admin_rules import render_admin_rules_page

    # Gate d'authentification (defense-in-depth via require_auth)
    from dashboard.views.page_00_login import require_auth
    if not is_authenticated():
        # Masquer la sidebar sur la page de login
        st.html("""<style>
            [data-testid="stSidebar"] { display: none !important; }
            [data-testid="stSidebarCollapsedControl"] { display: none !important; }
            .stMain { margin-left: 0 !important; }
        </style>""")
        render_login_page()
        return

    # Utilisateur connecté : valider l'identité via require_auth
    user = require_auth()
    if user is None:
        st.stop()
        return

    # Détection de la navigation via les paramètres d'URL (fil d'Ariane cliquable)
    query_params = st.query_params
    import sys
    print(f"DEBUG: st.query_params={dict(query_params)}", file=sys.stderr)
    if "page" in query_params:
        target_page = query_params["page"]
        print(f"DEBUG: Found page={target_page} in query_params", file=sys.stderr)
        if target_page == "espace_travail":
            st.session_state.pop("selected_run_id", None)
            st.session_state.pop("current_run_id", None)
        st.session_state["current_page"] = target_page
        st.query_params.clear()
        st.rerun()

    # Sidebar avec navigation
    _render_sidebar(user)

    # Router vers la page active
    page = st.session_state.get("current_page", "cockpit")
    
    page_map = {
        "cockpit": render_cockpit_page,
        "conformite": render_conformite_page,
        "espace_travail": render_espace_travail_page,
        "detail_run": render_detail_run_page,
        "jira": render_jira_page,
        "audit": render_audit_page,
        "tendances": render_tendances_page,
        "login": render_login_page,
        "parametres": render_parametres_page,
        "gouvernance": render_gouvernance_page,
        "admin_rules": render_admin_rules_page,
    }

    render_fn = page_map.get(page, render_cockpit_page)
    render_fn()

    # Phase 4: Inject keyboard shortcuts for power users
    from dashboard.components.keyboard_shortcuts import inject_keyboard_shortcuts
    inject_keyboard_shortcuts()

def _render_sidebar(user: UserIdentity):
    """Affiche la sidebar avec navigation et profil utilisateur."""
    
    # Config rôle
    role_config = {
        "Actuaire MOA": {"color": "#4F46E5", "bg": "rgba(79,70,229,0.10)", "short": "Maker"},
        "Validateur": {"color": "#059669", "bg": "rgba(5,150,105,0.10)", "short": "Checker"},
        "Responsable MOA": {"color": "#D97706", "bg": "rgba(217,119,6,0.10)", "short": "Manager"},
    }
    cfg = role_config.get(user.role, {"color": "#64748B", "bg": "rgba(100,116,139,0.1)", "short": user.role})
    
    # UN SEUL markdown pour tout le header (brand + profil + separator)
    st.sidebar.html(
        f'<div style="padding:0;">'
        f'<div style="font-weight:800;font-size:1.25rem;font-family:\'Inter\',sans-serif;letter-spacing:-0.025em;padding:0 0 4px 0;">'
        f'<span style="color:#4F46E5 !important;">Actua</span><span style="color:#0F172A !important;font-weight:500;">Recette</span>'
        f'</div>'
        f'<div style="font-size:0.8rem;color:var(--ar-text-secondary);padding:0 0 10px 0;">'
        f'{user.name} '
        f'<span style="font-size:0.6rem;font-weight:600;padding:2px 7px;border-radius:9999px;'
        f'background:{cfg["bg"]};color:{cfg["color"]};vertical-align:middle;">{cfg["short"]}</span>'
        f'</div>'
        f'<hr style="border:none;border-top:1px solid var(--ar-border);margin:4px 0 12px 0;">'
        f'</div>'
    )
    
    current_page = st.session_state.get("current_page", "cockpit")

    # ── SECTION : OPÉRATIONNEL ──
    st.sidebar.markdown(
        '<div style="font-size:0.6rem;font-weight:700;color:var(--ar-text-muted);'
        'text-transform:uppercase;letter-spacing:0.08em;padding:4px 0 8px 4px;">Opérationnel</div>',
        unsafe_allow_html=True,
    )
    for page_id, label in [
        ("espace_travail", "📂  Campagnes"),
        ("cockpit", "⊞  Tableau de bord"),
        ("tendances", "↗  Tendances"),
    ]:
        is_active = (current_page == page_id)
        button_type = "primary" if is_active else "secondary"
        if st.sidebar.button(label, key=f"nav_{page_id}", use_container_width=True,
                           type=button_type):
            st.session_state["current_page"] = page_id
            st.rerun()

    # ── SECTION : GOUVERNANCE ──
    st.sidebar.markdown(
        '<div style="font-size:0.6rem;font-weight:700;color:var(--ar-text-muted);'
        'text-transform:uppercase;letter-spacing:0.08em;padding:16px 0 8px 4px;'
        'margin-top:4px;border-top:1px solid var(--ar-border);">Gouvernance</div>',
        unsafe_allow_html=True,
    )
    for page_id, label in [
        ("gouvernance", "🏛️  Gouvernance ACPR"),
        ("audit", "📑  Registre d'Audit"),
    ]:
        is_active = (current_page == page_id)
        button_type = "primary" if is_active else "secondary"
        if st.sidebar.button(label, key=f"nav_{page_id}", use_container_width=True,
                           type=button_type):
            st.session_state["current_page"] = page_id
            st.rerun()

    # ── SECTION : ADMINISTRATION ──
    st.sidebar.markdown(
        '<div style="font-size:0.6rem;font-weight:700;color:var(--ar-text-muted);'
        'text-transform:uppercase;letter-spacing:0.08em;padding:16px 0 8px 4px;'
        'margin-top:4px;border-top:1px solid var(--ar-border);">Administration</div>',
        unsafe_allow_html=True,
    )
    if user.role in ("Actuaire MOA", "Responsable MOA"):
        is_active = (current_page == "admin_rules")
        button_type = "primary" if is_active else "secondary"
        if st.sidebar.button("🛠️  Configuration des Règles", key="nav_admin_rules", use_container_width=True, type=button_type):
            st.session_state["current_page"] = "admin_rules"
            st.rerun()

    is_active = (current_page == "parametres")
    button_type = "primary" if is_active else "secondary"
    if st.sidebar.button("⚙️  Paramètres", key="nav_parametres", use_container_width=True, type=button_type):
        st.session_state["current_page"] = "parametres"
        st.rerun()
        
    if st.sidebar.button("↩️  Se déconnecter", key="nav_logout", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# ---------------------------------------------------------------------------
# Lancement
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    main()

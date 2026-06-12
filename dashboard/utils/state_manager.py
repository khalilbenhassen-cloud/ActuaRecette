# state_manager.py - Gestion centralis\u00e9e du session_state ActuaRecette v6.0
# Toutes les cl\u00e9s session_state passent par ce module.
# \u00c9limine les acc\u00e8s session_state \u00e9parpill\u00e9s dans le monolithe.

import streamlit as st
from typing import Any, Optional, List, Dict

# ---------------------------------------------------------------------------
# Cl\u00e9s de session normalis\u00e9es
# ---------------------------------------------------------------------------

# Identit\u00e9 utilisateur
KEY_USER = "user"                    # dict | None : donn\u00e9es UserIdentity.to_dict()

# Navigation
KEY_CURRENT_LOB = "current_lob"      # str : id_portefeuille du LOB courant
KEY_CURRENT_RUN = "current_run_id"   # str : id du run affich\u00e9
KEY_CURRENT_PAGE = "current_page"    # str : nom de la page active

# Donn\u00e9es de travail
KEY_REF_FILE = "ref_file"            # UploadedFile : fichier de r\u00e9f\u00e9rence actuarielle
KEY_PROD_FILE = "prod_file"          # UploadedFile : fichier de production DSI
KEY_MAPPING = "column_mapping"       # dict : mapping de colonnes
KEY_TOLERANCE = "tolerance"          # float : seuil de tol\u00e9rance
KEY_LAST_RESULT = "last_result"      # dict : r\u00e9sultat de la derni\u00e8re r\u00e9conciliation

# Historique
KEY_RUN_HISTORY = "run_history"      # list : historique des runs charg\u00e9s
KEY_SELECTED_RUNS = "selected_runs"  # list : runs s\u00e9lectionn\u00e9s pour comparaison

# ---------------------------------------------------------------------------
# Accesseurs typ\u00e9s
# ---------------------------------------------------------------------------

def init_defaults():
    """Initialise toutes les cl\u00e9s de session avec leurs valeurs par d\u00e9faut."""
    defaults = {
        KEY_USER: None,
        KEY_CURRENT_LOB: None,
        KEY_CURRENT_RUN: None,
        KEY_CURRENT_PAGE: "cockpit",
        KEY_REF_FILE: None,
        KEY_PROD_FILE: None,
        KEY_MAPPING: None,
        KEY_TOLERANCE: 0.05,
        KEY_LAST_RESULT: None,
        KEY_RUN_HISTORY: [],
        KEY_SELECTED_RUNS: [],
    }
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

def get_user() -> Optional[Dict]:
    """Retourne les donn\u00e9es utilisateur ou None si non connect\u00e9."""
    return st.session_state.get(KEY_USER)

def set_user(user_data: Optional[Dict]):
    """D\u00e9finit l'utilisateur connect\u00e9."""
    st.session_state[KEY_USER] = user_data

def is_authenticated() -> bool:
    """V\u00e9rifie si un utilisateur est connect\u00e9."""
    return get_user() is not None

def get_current_lob() -> Optional[str]:
    """Retourne le LOB courant."""
    return st.session_state.get(KEY_CURRENT_LOB)

def set_current_lob(lob_id: str):
    """D\u00e9finit le LOB courant."""
    st.session_state[KEY_CURRENT_LOB] = lob_id

def get_current_run() -> Optional[str]:
    """Retourne l'ID du run courant."""
    return st.session_state.get(KEY_CURRENT_RUN)

def set_current_run(run_id: str):
    """D\u00e9finit le run courant."""
    st.session_state[KEY_CURRENT_RUN] = run_id

def get_tolerance() -> float:
    """Retourne le seuil de tol\u00e9rance courant."""
    return st.session_state.get(KEY_TOLERANCE, 0.05)

def set_tolerance(tolerance: float):
    """D\u00e9finit le seuil de tol\u00e9rance."""
    st.session_state[KEY_TOLERANCE] = tolerance

def get_last_result() -> Optional[Dict]:
    """Retourne le r\u00e9sultat de la derni\u00e8re r\u00e9conciliation."""
    return st.session_state.get(KEY_LAST_RESULT)

def set_last_result(result: Dict):
    """Stocke le r\u00e9sultat de la derni\u00e8re r\u00e9conciliation."""
    st.session_state[KEY_LAST_RESULT] = result

def navigate_to(page: str, **kwargs):
    """
    Navigation programmatique vers une page.
    Stocke les param\u00e8tres additionnels dans le session_state.
    """
    st.session_state[KEY_CURRENT_PAGE] = page
    for key, value in kwargs.items():
        st.session_state[key] = value

# 00_login.py - Page 0 : Login & Identification
# Phase 1 — Socle multi-utilisateur ActuaRecette v6.0
#
# Cette page est le point d'entrée obligatoire.
# Sans identification, aucune autre page n'est accessible.

import streamlit as st

# ARCH-08: PYTHONPATH must be set externally (via run command or .env),
# not via sys.path manipulation in individual modules.

from dashboard.utils.auth import (
    UserIdentity,
    find_user_by_sso,
    list_all_users,
    VALID_ROLES,
    ALL_LOBS,
)

# ═══════════════════════════════════════════════════════════════════════
# PHASE 1 — Limitations de sécurité connues:
# SEC-01: Auth via dropdown sans mot de passe (acceptable en Phase 1,
#         sera remplacé par SSO/LDAP en Phase 2)
# SEC-14: Sessions Streamlit en mémoire (pertes au restart).
#         Phase 2+ : persistence Redis/DB requise.
# ═══════════════════════════════════════════════════════════════════════
#
# 📘 ARCHITECTURE DE PRODUCTION : SPÉCIFICATION D'INTÉGRATION SSO (OAuth2 / OpenID Connect)
#
# Pour le raccordement d'ActuaRecette au fournisseur d'identité d'entreprise (IdP) :
#
# 1. PARAMÈTRES ET CONFIGURATION (Variables d'environnement) :
#    - OIDC_CLIENT_ID : Identifiant unique de l'application ActuaRecette auprès de l'IdP.
#    - OIDC_CLIENT_SECRET : Secret client (sécurisé via Key Vault ou Secret Manager).
#    - OIDC_DISCOVERY_URL : Point d'entrée de découverte OpenID Connect.
#    - OIDC_REDIRECT_URI : URL de retour d'authentification (callback).
#    - OIDC_SCOPES : "openid profile email groups"
#
# 2. FLUX RECOMMANDÉ (Authorization Code Flow with PKCE) :
#    a. L'utilisateur clique sur "Se connecter via SSO".
#    b. ActuaRecette génère un challenge PKCE (S256) et redirige vers l'URL /authorize de l'IdP.
#    c. Une fois authentifié par l'IdP, l'utilisateur revient avec un code temporaire.
#    d. Le serveur d'ActuaRecette échange ce code contre un Access Token et un ID Token (JWT).
#
# 3. SÉCURITÉ DU JETON JWT (ID Token) :
#    - Validation cryptographique systématique à chaque requête à l'aide des clés publiques (JWKS).
#    - Vérification rigoureuse des claims temporels (exp, nbf, iat), de l'émetteur (iss) et de l'audience (aud).
#
# 4. MAPPING DU PROFIL UTILISATEUR :
#    - SSO / Identifiant unique : extrait de la claim `sub` ou `preferred_username`.
#    - Rôle applicatif (Maker/Checker/Manager) : extrait via le mapping des claims AD (ex: AD-ACTUARECETTE-VALIDATORS).
#    - Périmètres de LOBs : filtrés via les groupes d'entités métiers AD ou récupérés en base SQL.
# ═══════════════════════════════════════════════════════════════════════

def render_login_page():
    """
    Affiche la page de login et gère l'authentification.
    Stocke l'identité dans st.session_state["user"].
    """
    # Si déjà connecté, afficher le profil et le bouton de déconnexion
    if "user" in st.session_state and st.session_state["user"] is not None:
        _render_connected_profile()
        return

    # Page de login
    st.html(
        '<div style="font-weight:800;font-size:2.0rem;font-family:\'Inter\',sans-serif;letter-spacing:-0.025em;padding:0 0 8px 0; display:flex; align-items:center; gap:8px;">'
        '<span>🔐</span>'
        '<div>'
        '<span style="color:#4F46E5 !important;">Actua</span><span style="color:#0F172A !important;font-weight:500;">Recette</span>'
        '</div>'
        '</div>'
    )
    st.markdown("**Outil de gouvernance de la réconciliation actuarielle multi-utilisateur**")
    st.markdown("---")

    # Formulaire de connexion
    with st.form("login_form", clear_on_submit=False):
        st.markdown("### Identification")

        # Liste des utilisateurs disponibles (Phase 1 : registre local)
        users = list_all_users()
        user_options = {f"{u.name} ({u.sso}) — {u.role}": u for u in users}

        selected_label = st.selectbox(
            "Sélectionnez votre profil",
            options=list(user_options.keys()),
            help="En Phase 1, les utilisateurs sont pré-enregistrés. "
                 "En production, l'authentification se fera via SSO/LDAP.",
        )

        submitted = st.form_submit_button("Se connecter →", use_container_width=True)

        if submitted:
            if not selected_label:
                st.error("Veuillez sélectionner un profil avant de continuer.")
            else:
                user = user_options[selected_label]
                st.session_state["user"] = user.to_dict()
                st.rerun()

    # Expander de documentation SSO pour les auditeurs et l'équipe MOA/IT (Pilier 2)
    with st.expander("ℹ️ Spécifications d'intégration SSO (OAuth2 / OIDC) de Production", expanded=False):
        st.markdown(
            """
            ### 🔑 Raccordement au Fournisseur d'Identité de l'Entreprise (IdP)
            
            Cette section détaille les spécifications du raccordement SSO pour la phase de production, répondant aux exigences réglementaires de sécurité et de contrôle d'accès :
            
            - **Mécanisme d'Authentification** : Flux standard **OAuth 2.0 / OpenID Connect (OIDC)** (Authorization Code Flow avec PKCE).
            - **Paramètres Requis** :
              * *Client ID* et *Client Secret* (ce dernier devant être configuré en variable d'environnement chiffrée sur la plateforme d'hébergement).
              * *Scopes d'accès* : `openid`, `profile`, `email`, `groups`.
            - **Contrôles de Robustesse** :
              * Signature des jetons JWT validée périodiquement via l'URI JWKS exposé par l'IdP.
              * Assertions de validité temporelle (`exp`, `nbf`) et de restriction d'audience (`aud`) contrôlées à chaque appel.
            - **Attribution des Droits** :
              * Mappage automatique des rôles applicatifs (`Actuaire MOA`, `Validateur`, `Responsable MOA`) selon l'appartenance de l'utilisateur aux groupes Active Directory (AD).
              * Cloisonnement des portefeuilles (LOBs) basé sur des claims de groupes AD dédiés ou via la base de données interne.
            """
        )

    pass

def _render_connected_profile():
    """Affiche le profil de l'utilisateur connecté avec option de déconnexion."""
    user_data = st.session_state["user"]
    user = UserIdentity.from_dict(user_data)

    st.markdown("## 🔐 Profil Connecté")
    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Utilisateur** : {user.name}")
        st.markdown(f"**SSO** : `{user.sso}`")
    with col2:
        st.markdown(f"**Rôle** : {user.role}")
        lobs_display = ", ".join(user.visible_lobs) if user.visible_lobs else "Aucun"
        st.markdown(f"**LOBs visibles** : {lobs_display}")

    st.markdown("---")

    # Capacités
    st.markdown("##### Capacités")
    caps = []
    if user.is_maker:
        caps.append("📊 Créer et soumettre des campagnes")
    if user.is_checker:
        caps.append("✅ Certifier les campagnes des autres actuaires")
    if user.is_manager:
        caps.append("👑 Administrer les exercices et les utilisateurs")
    for cap in caps:
        st.markdown(f"- {cap}")

    st.markdown("---")

    if st.button("🔓 Se déconnecter", use_container_width=True):
        st.session_state.clear()
        st.rerun()

def require_auth() -> UserIdentity:
    """
    Gate d'authentification — à appeler au début de chaque page protégée.
    Redirige vers la page de login si l'utilisateur n'est pas connecté.

    Sécurité anti-tampering :
    - Vérifie que le SSO en session correspond à un utilisateur du registre
    - Utilise le rôle et les LOBs du registre (pas ceux du session_state)
    - Invalide la session si l'utilisateur n'existe plus dans le registre

    Usage dans une page:
        from dashboard.views.page_00_login import require_auth
        user = require_auth()
        if user is None:
            st.stop()
    """
    user_data = st.session_state.get("user")
    if user_data is None:
        st.warning("⚠️ Vous devez vous identifier pour accéder à cette page.")
        st.info("Rendez-vous sur la page **Login** pour vous connecter.")
        return None

    # Anti-tampering : valider le SSO contre le registre
    sso = user_data.get("sso", "")
    canonical_user = find_user_by_sso(sso)
    if canonical_user is None:
        # SSO inconnu — session potentiellement falsifiée
        import logging
        logging.getLogger("actuarecette.auth").warning(
            f"Session invalidée : SSO '{sso}' introuvable dans le registre."
        )
        st.session_state["user"] = None
        st.error("Session invalide. Veuillez vous reconnecter.")
        return None

    # Utiliser l'identité canonique du registre (pas le dict client)
    return canonical_user

# Point d'entrée Streamlit (uniquement en exécution directe)
if __name__ == "__main__":
    render_login_page()

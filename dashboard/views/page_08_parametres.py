# page_08_parametres.py — Page Paramètres
# Phase 2c — Configuration utilisateur & préférences
"""
Page de paramètres permettant de visualiser le profil utilisateur,
les LOBs assignés, et les préférences d'affichage.
"""
import streamlit as st

def render_parametres_page():
    """Render the settings/preferences page."""
    # Defense-in-depth: vérifier l'authentification au niveau page
    from dashboard.views.page_00_login import require_auth
    if require_auth() is None:
        st.stop()
        return

    from dashboard.components.breadcrumb import breadcrumb
    breadcrumb(["Administration", "Paramètres"])

    st.html(
        '<div style="font-size:1.4rem;font-weight:800;color:var(--ar-text-primary);'
        'margin-bottom:4px;">⚙️ Paramètres</div>'
        '<div style="font-size:0.78rem;color:var(--ar-text-muted);margin-bottom:24px;">'
        'Profil utilisateur et préférences d\'affichage</div>'
    )

    tab1, tab2 = st.tabs(["⚙️ Profil & Préférences", "⚡ Générateur de Scénarios"])

    with tab1:
        user_data = st.session_state.get("user", {})
        user_sso = user_data.get("sso", "—")
        from dashboard.utils.auth import find_user_by_sso
        user_identity = find_user_by_sso(user_sso)
        user_name = user_identity.name if user_identity else user_data.get("name", "—")
        user_role = user_identity.role if user_identity else user_data.get("role", "—")
        user_lobs = user_identity.assigned_lobs if user_identity else user_data.get("assigned_lobs", [])

        # ── Section 1 : Profil utilisateur ──
        with st.container(border=True):
            st.html(
                '<div style="font-size:0.72rem;font-weight:700;color:var(--ar-text-muted);'
                'text-transform:uppercase;letter-spacing:0.06em;margin-bottom:12px;">'
                '👤 Profil utilisateur</div>'
            )

            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Nom complet**")
                st.code(user_name, language=None)
                st.markdown(f"**Identifiant SSO**")
                st.code(user_sso, language=None)
            with col2:
                st.markdown(f"**Rôle**")
                st.code(user_role, language=None)
                st.markdown(f"**LOBs assignés**")
                if user_lobs:
                    for lob in user_lobs:
                        st.markdown(f"- `{lob}`")
                else:
                    st.caption("Toutes les LOBs (accès complet)")

        st.html("<div style='height:16px'></div>")

        # ── Section 2 : Préférences d'affichage ──
        with st.container(border=True):
            st.html(
                '<div style="font-size:0.72rem;font-weight:700;color:var(--ar-text-muted);'
                'text-transform:uppercase;letter-spacing:0.06em;margin-bottom:12px;">'
                '🎨 Préférences d\'affichage</div>'
            )

            col1, col2 = st.columns(2)
            with col1:
                items_per_page = st.selectbox(
                    "Éléments par page (tableaux)",
                    options=[10, 25, 50, 100],
                    index=1,
                    key="pref_items_per_page",
                )
            with col2:
                default_period = st.selectbox(
                    "Période par défaut",
                    options=["Année complète", "Trimestre en cours", "Mois en cours"],
                    index=0,
                    key="pref_default_period",
                )

        st.html("<div style='height:16px'></div>")

        # ── Section 3 : Informations système ──
        with st.container(border=True):
            st.html(
                '<div style="font-size:0.72rem;font-weight:700;color:var(--ar-text-muted);'
                'text-transform:uppercase;letter-spacing:0.06em;margin-bottom:12px;">'
                'ℹ️ Informations système</div>'
            )

            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown("**Version**")
                st.code("ActuaRecette v6.0", language=None)
            with col2:
                st.markdown("**API**")
                from dashboard.utils.api_client import API_BASE_URL
                st.code(API_BASE_URL, language=None)
            with col3:
                st.markdown("**Base de données**")
                st.code("SQLite (actuarecette.db)", language=None)

        # ── Section 4 : Administration (Responsable MOA uniquement) ──
        if user_role == "Responsable MOA":
            st.html("<div style='height:16px'></div>")

            with st.container(border=True):
                st.html(
                    '<div style="font-size:0.72rem;font-weight:700;color:var(--ar-text-muted);'
                    'text-transform:uppercase;letter-spacing:0.06em;margin-bottom:12px;">'
                    '🔧 Administration</div>'
                )

                st.html(
                    '<div style="font-size:0.82rem;color:var(--ar-text-secondary);margin-bottom:16px;">'
                    'Reinitialiser l\'environnement supprime toutes les donnees '
                    '(campagnes, audit) tout en conservant les referentiels '
                    '(categories d\'anomalies, structure tarifaire).</div>'
                )

                if st.button("⚠️ Reinitialiser l'environnement", key="admin_reset_env", type="secondary"):
                    st.session_state["confirm_reset_env"] = True

                if st.session_state.get("confirm_reset_env"):
                    st.error(
                        "ATTENTION : cette action va supprimer toutes les donnees "
                        "(campagnes, audit). Les referentiels seront conserves. "
                        "Cette action est irreversible."
                    )
                    confirm_text = st.text_input(
                        "Tapez CONFIRMER pour valider :",
                        key="reset_confirm_input"
                    )
                    col1, col2, _ = st.columns([2, 2, 8])
                    with col1:
                        if st.button("Reinitialiser", key="do_reset", type="primary",
                                     disabled=(confirm_text != "CONFIRMER")):
                            _perform_environment_reset()
                            st.session_state["confirm_reset_env"] = False
                            st.success("Environnement reinitialise avec succes.")
                            st.rerun()
                    with col2:
                        if st.button("Annuler", key="cancel_reset"):
                            st.session_state["confirm_reset_env"] = False
                            st.rerun()

    with tab2:
        st.html(
            '<div style="font-size:0.72rem;font-weight:700;color:var(--ar-text-muted);'
            'text-transform:uppercase;letter-spacing:0.06em;margin-bottom:12px;">'
            '⚡ Modèles de Recette (Scénarios) enregistrés</div>'
        )

        from dashboard.utils.engine_proxy import load_scenarios
        scenarios = load_scenarios("data/scenarios")

        if scenarios:
            for sc in scenarios:
                with st.expander(f"🎬 {sc.get('name', 'Sans nom')}"):
                    if sc.get("description"):
                        st.markdown(f"**Description :** {sc.get('description')}")
                    st.markdown("**Configurations de Recette :**")
                    st.json({
                        "mapping": sc.get("mapping", {}),
                        "rules": sc.get("rules", {})
                    })
        else:
            st.info("Aucun scénario/modèle de recette enregistré pour le moment.")

        st.html("<div style='height:24px'></div>")

        st.html(
            '<div style="font-size:0.72rem;font-weight:700;color:var(--ar-text-muted);'
            'text-transform:uppercase;letter-spacing:0.06em;margin-bottom:12px;">'
            '⚡ Portefeuille de Stress-Testing</div>'
        )
        st.write("Générez un portefeuille de stress-testing d'assurance de 1000 assurés comprenant des cas limites (jeunes conducteurs, véhicules de sport, malus sévères) pour éprouver et valider la robustesse de vos algorithmes de tarification.")

        if st.button("⚡ Générer le portefeuille de stress-test", key="btn_gen_stress", type="primary"):
            try:
                import os
                from dashboard.utils.engine_proxy import generate_stress_portfolio
                os.makedirs("data", exist_ok=True)
                csv_path = "data/stress_portfolio_edge.csv"
                generate_stress_portfolio(csv_path, num_records=1000)

                with open(csv_path, "rb") as f:
                    csv_bytes = f.read()

                st.success("Portefeuille de stress-testing (1000 assurés aux limites) généré avec succès !")
                st.download_button(
                    label="📥 Télécharger le portefeuille (CSV)",
                    data=csv_bytes,
                    file_name="portefeuille_stress_testing_1000.csv",
                    mime="text/csv",
                    key="btn_download_stress"
                )
            except Exception as e:
                st.error(f"Erreur lors de la génération du portefeuille : {e}")


def _perform_environment_reset():
    """Reinitialise l'environnement : vide les bases, supprime les runs."""
    import os
    import json
    import glob

    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # 1. Delete all run JSON files
    runs_dir = os.path.join(base_dir, "data", "uat_runs")
    if os.path.isdir(runs_dir):
        for f in glob.glob(os.path.join(runs_dir, "*.json")):
            os.remove(f)

    # 2. Delete saved datasets
    ds_dir = os.path.join(base_dir, "data", "saved_datasets")
    if os.path.isdir(ds_dir):
        for f in glob.glob(os.path.join(ds_dir, "*")):
            os.remove(f)

    # 3. Reset audit log
    audit_file = os.path.join(base_dir, "data", "audit_log.json")
    if os.path.exists(audit_file):
        with open(audit_file, "w", encoding="utf-8") as f:
            json.dump([], f)

    # 4. Purge SQLite actuarecette.db data tables
    try:
        import sqlite3
        db_path = os.path.join(base_dir, "data", "actuarecette.db")
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            for table in ["portefeuilles", "campagnes_recette", "regles_recette", "runs_execution", "audit_entries"]:
                try:
                    cur.execute(f"DELETE FROM [{table}]")
                except Exception:
                    pass
            conn.commit()
            conn.close()
    except Exception:
        pass

    # 5. Purge SQLite data tables (keep ref tables)
    try:
        import sqlite3
        db_path = os.path.join(base_dir, "data", "actuarecette_v2.db")
        if os.path.exists(db_path):
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            ref_tables = {"anomaly_categories", "tarif_structure"}
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            for (table,) in cur.fetchall():
                if table not in ref_tables:
                    try:
                        cur.execute(f"DELETE FROM [{table}]")
                    except Exception:
                        pass
            conn.commit()
            conn.close()
    except Exception:
        pass

    st.cache_data.clear()

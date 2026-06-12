# page_10_admin_rules.py — Console d'administration des Règles & Portefeuilles
# Phase 3 — Double approbation (4 yeux) & Gestion SQLite
"""
Page d'administration permettant de gérer les LOBs et les règles de recette dynamiques
avec un workflow de double approbation (Maker / Checker) et traçabilité réglementaire.
"""
import os
from dashboard.utils.engine_proxy import sqlite_connection
import json
import sqlite3
import datetime
import hashlib
import streamlit as st
import pandas as pd
from dashboard.views.page_00_login import require_auth
from dashboard.components.breadcrumb import breadcrumb
import src.formula_parser
SafeFormulaParser = src.formula_parser.SafeFormulaParser
from dashboard.utils.auth import add_lob_to_registry, _initialize_users_table_if_needed
from dashboard.utils.periods import list_all_periods, add_period_to_db, update_period_status_in_db, delete_period_from_db

def log_admin_audit(user_sso: str, user_name: str, user_role: str, action: str, comment: str, lob_id: str = None):
    """Journalise l'action d'administration dans SQLite et dans le fichier JSON d'audit legacy."""
    now = datetime.datetime.now().isoformat()
    sig = hashlib.sha256(
        f"{now}:{user_sso}:{action}:{lob_id or ''}".encode("utf-8")
    ).hexdigest()[:16]
    
    # 1. Écriture dans SQLite (les deux bases pour la cohérence totale)
    for db_path in ["data/actuarecette.db", "data/actuarecette_v2.db"]:
        if os.path.exists(db_path):
            try:
                conn = sqlite_connection(db_path)
                conn.execute(
                    """INSERT INTO audit_entries
                    (timestamp, user_sso, user_name, user_role, id_portefeuille, action, comment, signature_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (now, user_sso, user_name, user_role, lob_id, action, comment, sig)
                )
                conn.commit()
                conn.close()
            except Exception:
                pass
                
    # 2. Écriture dans le journal JSON d'audit legacy
    audit_file_path = "data/audit_log.json"
    if os.path.exists(audit_file_path):
        try:
            with open(audit_file_path, "r", encoding="utf-8") as f:
                log_data = json.load(f)
        except Exception:
            log_data = []
        log_data.append({
            "timestamp": now,
            "run_id": None,
            "run_name": f"Admin action on LOB {lob_id}" if lob_id else "Admin action",
            "role": user_role,
            "action": action,
            "comment": comment,
            "validator_name": user_name,
            "signature_hash": sig
        })
        try:
            with open(audit_file_path, "w", encoding="utf-8") as f:
                json.dump(log_data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

def render_admin_rules_page():
    """Rendu de la page de gestion des règles et des portefeuilles."""
    
    # Vérification obligatoire de l'authentification (Defense in depth)
    user = require_auth()
    if user is None:
        st.stop()
        return

    breadcrumb(["Administration", "Configuration des Règles"])

    st.html(
        '<div style="font-size:1.4rem;font-weight:800;color:var(--ar-text-primary);margin-bottom:4px;">⚙️ Configuration des Règles & Portefeuilles</div>'
        '<div style="font-size:0.78rem;color:var(--ar-text-muted);margin-bottom:24px;">'
        'Gérez dynamiquement vos LOBs, vos règles de tarification et validez-les en double approbation (Pilier 2).</div>'
    )

    # Affichage du message de succès global si disponible
    if "user_success_message" in st.session_state:
        st.success(st.session_state["user_success_message"])
        del st.session_state["user_success_message"]

    if "user_error_message" in st.session_state:
        st.error(st.session_state["user_error_message"])
        del st.session_state["user_error_message"]

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📁 Gestion des Portefeuilles (LOBs)",
        "📏 Gestion des Règles (Rule Builder)",
        "👁️ Cabinet de Validation (4 yeux)",
        "👥 Gestion des Utilisateurs",
        "📅 Périodes d'arrêté"
    ], key="admin_rules_tabs")

    # ---------------------------------------------------------------------------
    # Onglet 1 : Gestion des Portefeuilles (LOBs)
    # ---------------------------------------------------------------------------
    with tab1:
        st.markdown("### Référentiel des Lignes de Métier (LOBs)")
        
        # Affichage des LOBs existants
        conn = sqlite_connection("data/actuarecette.db")
        conn.row_factory = sqlite3.Row
        portefeuilles = conn.execute("SELECT * FROM portefeuilles").fetchall()
        conn.close()
        
        # Filtrer: Les Managers voient tout, les Makers voient leurs LOBs autorisées OU celles qu'ils ont créées en brouillon
        if user.role == "Actuaire MOA":
            portefeuilles = [p for p in portefeuilles if user.can_view_lob(p["id_portefeuille"]) or p["cree_par_sso"] == user.sso]
        
        lob_df = pd.DataFrame([dict(p) for p in portefeuilles])
        if not lob_df.empty:
            cols_rename = {
                "id_portefeuille": "ID Portefeuille",
                "code_metier": "Code Métier",
                "libelle": "Libellé LOB",
                "type_risque": "Type Risque",
                "seuil_materialite_pct": "Matérialité (%)",
                "warning_pct": "Seuil Alerte (%)",
                "critical_pct": "Seuil Bloquant (%)",
                "materiality_threshold_eur": "Seuil (€)",
                "statut": "Statut"
            }
            show_cols = [c for c in cols_rename.keys() if c in lob_df.columns]
            st.dataframe(
                lob_df[show_cols].rename(columns=cols_rename),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("Aucun portefeuille défini dans SQLite.")

        st.markdown("---")
        st.markdown("### ➕ Ajouter un nouveau portefeuille (LOB)")
        
        # Formulaire de création de LOB
        with st.form("new_lob_form"):
            col1, col2 = st.columns(2)
            with col1:
                new_id = st.text_input("ID Portefeuille (ex: LOB_TEST)", placeholder="LOB_...").strip().upper().replace(" ", "_")
                new_code = st.text_input("Code Métier (ex: TEST)", placeholder="TEST").strip().upper()
                new_libelle = st.text_input("Libellé", placeholder="Description du portefeuille...")
                new_type_risque = st.text_input("Type de Risque", value="IARD")
            with col2:
                new_seuil_pct = st.number_input(
                    "Seuil Matérialité (%)",
                    min_value=0.0, max_value=100.0, value=0.2, step=0.01,
                    help="Seuil en % de tolérance au-dessus duquel un écart individuel de réconciliation est considéré comme matériel."
                )
                new_warning_pct = st.number_input(
                    "Seuil Alerte (%)",
                    min_value=0.0, max_value=100.0, value=3.0, step=0.1,
                    help="Seuil d'écart cumulé en % déclenchant une alerte orange (informationnelle) sur la LOB."
                )
                new_critical_pct = st.number_input(
                    "Seuil Bloquant (%)",
                    min_value=0.0, max_value=100.0, value=5.0, step=0.1,
                    help="Seuil d'écart cumulé en % déclenchant une alerte rouge (bloquante) nécessitant une justification et double-approbation obligatoires."
                )
                new_threshold_eur = st.number_input(
                    "Seuil Absolu (€)",
                    min_value=0.0, value=500.0, step=50.0,
                    help="Montant minimum en euros sous lequel les écarts de réconciliation sont jugés trop faibles pour bloquer ou nécessiter une action."
                )

            submitted = st.form_submit_button("Ajouter le Portefeuille", type="primary", use_container_width=True)
            
            if submitted:
                if not new_id or not new_code or not new_libelle:
                    st.error("Veuillez remplir les champs obligatoires (ID, Code, Libellé).")
                else:
                    # Insérer dans SQLite (les deux bases)
                    inserted = False
                    status_to_set = "ACTIF" if user.role == "Responsable MOA" else "EN_ATTENTE"
                    
                    for db_path in ["data/actuarecette.db", "data/actuarecette_v2.db"]:
                        if os.path.exists(db_path):
                            try:
                                conn_db = sqlite_connection(db_path)
                                conn_db.execute(
                                    """INSERT OR IGNORE INTO portefeuilles
                                    (id_portefeuille, code_metier, libelle, type_risque, seuil_materialite_pct, warning_pct, critical_pct, materiality_threshold_eur, statut, cree_par_sso, date_creation)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
                                    (new_id, new_code, new_libelle, new_type_risque, new_seuil_pct, new_warning_pct, new_critical_pct, new_threshold_eur, status_to_set, user.sso)
                                )
                                
                                if status_to_set == "ACTIF":
                                    # Mettre à jour automatiquement les assigned_lobs pour le créateur
                                    row = conn_db.execute("SELECT assigned_lobs FROM utilisateurs WHERE sso = ?", [user.sso]).fetchone()
                                    if row:
                                        current_lobs = [l.strip() for l in row[0].split(",") if l.strip()] if row[0] else []
                                        if new_id not in current_lobs:
                                            current_lobs.append(new_id)
                                            new_assigned_lobs = ",".join(current_lobs)
                                            conn_db.execute("UPDATE utilisateurs SET assigned_lobs = ? WHERE sso = ?", [new_assigned_lobs, user.sso])
                                            
                                    # Mettre à jour automatiquement les checkers
                                    checkers = conn_db.execute("SELECT sso, assigned_lobs FROM utilisateurs WHERE role IN ('Validateur', 'Responsable MOA')").fetchall()
                                    for chk in checkers:
                                        chk_sso = chk["sso"]
                                        chk_lobs = [l.strip() for l in chk["assigned_lobs"].split(",") if l.strip()] if chk["assigned_lobs"] else []
                                        if new_id not in chk_lobs:
                                            chk_lobs.append(new_id)
                                            new_chk_assigned = ",".join(chk_lobs)
                                            conn_db.execute("UPDATE utilisateurs SET assigned_lobs = ? WHERE sso = ?", [new_chk_assigned, chk_sso])

                                conn_db.commit()
                                conn_db.close()
                                inserted = True
                            except Exception as e:
                                st.error(f"Erreur SQLite lors de l'insertion dans {db_path} : {e}")
                                inserted = False
                                break
                    
                    if inserted:
                        if status_to_set == "ACTIF":
                            add_lob_to_registry(new_id)
                            log_admin_audit(user.sso, user.name, user.role, "LOB_ADDED", f"Creation directe du portefeuille {new_id} ({new_libelle})", new_id)
                            st.session_state["user_success_message"] = f"✔ Portefeuille {new_id} créé et activé avec succès !"
                            st.rerun()
                        else:
                            log_admin_audit(user.sso, user.name, user.role, "LOB_CREATED_DRAFT", f"Creation du brouillon du portefeuille {new_id} ({new_libelle}) en attente d'approbation", new_id)
                            st.session_state["admin_rules_tabs"] = "📏 Gestion des Règles (Rule Builder)"
                            st.session_state["preselected_new_lob"] = new_id
                            st.session_state["user_success_message"] = f"✔ Brouillon de portefeuille {new_id} créé ! Veuillez vous rendre sur l'onglet 'Gestion des Règles' pour y associer des règles."
                            st.rerun()

        st.markdown("---")
        st.markdown("### ✏️ Modifier les seuils d'un portefeuille (LOB)")
        
        # Liste des LOBs modifiables (déjà actives)
        edit_lob_options = {f"{p['libelle']} ({p['id_portefeuille']})": p for p in portefeuilles if p["statut"] == "ACTIF"}
        if edit_lob_options:
            sel_edit_lob_label = st.selectbox("Sélectionner le portefeuille à modifier", options=list(edit_lob_options.keys()), key="sel_edit_lob_label_out")
            selected_lob_data = edit_lob_options[sel_edit_lob_label]
            lob_id_to_edit = selected_lob_data["id_portefeuille"]
            
            selected_domaine = st.selectbox("Sélectionner le domaine", options=["Prime", "Sinistre", "Réserve", "Contrat", "Réassurance"], key="selected_domaine_out")
            
            # Charger les seuils pour ce portefeuille et ce domaine
            conn = sqlite_connection("data/actuarecette.db")
            conn.row_factory = sqlite3.Row
            threshold_row = conn.execute(
                "SELECT * FROM portefeuilles_seuils_domaines WHERE id_portefeuille = ? AND domaine = ?",
                (lob_id_to_edit, selected_domaine)
            ).fetchone()
            conn.close()
            
            # Déterminer les valeurs par défaut
            if threshold_row:
                threshold_data = dict(threshold_row)
            else:
                # Fallback
                default_seuil_materialite_pct = 0.2
                default_warning_pct = 3.0
                default_critical_pct = 5.0
                default_materiality_threshold_eur = 500.0
                if selected_domaine == "Sinistre":
                    default_seuil_materialite_pct, default_warning_pct, default_critical_pct, default_materiality_threshold_eur = 0.5, 3.0, 5.0, 500.0
                elif selected_domaine == "Réserve":
                    default_seuil_materialite_pct, default_warning_pct, default_critical_pct, default_materiality_threshold_eur = 1.5, 4.0, 6.0, 5000.0
                elif selected_domaine == "Contrat":
                    default_seuil_materialite_pct, default_warning_pct, default_critical_pct, default_materiality_threshold_eur = 0.0, 1.0, 2.0, 0.0
                elif selected_domaine == "Réassurance":
                    default_seuil_materialite_pct, default_warning_pct, default_critical_pct, default_materiality_threshold_eur = 1.0, 3.0, 5.0, 2000.0
                
                threshold_data = {
                    "seuil_materialite_pct": default_seuil_materialite_pct,
                    "warning_pct": default_warning_pct,
                    "critical_pct": default_critical_pct,
                    "materiality_threshold_eur": default_materiality_threshold_eur,
                    "statut": "ACTIF"
                }
            
            # Vérifier s'il y a un brouillon pour ce domaine
            has_draft = threshold_row and threshold_row["statut"] == "EN_ATTENTE"
            if has_draft:
                st.warning(f"⚠️ Une proposition de modification des seuils pour le domaine **{selected_domaine}** est en attente de validation.")
                
            val_seuil_pct = threshold_row["draft_seuil_materialite_pct"] if (has_draft and threshold_row["draft_seuil_materialite_pct"] is not None) else threshold_data["seuil_materialite_pct"]
            val_warning_pct = threshold_row["draft_warning_pct"] if (has_draft and threshold_row["draft_warning_pct"] is not None) else threshold_data["warning_pct"]
            val_critical_pct = threshold_row["draft_critical_pct"] if (has_draft and threshold_row["draft_critical_pct"] is not None) else threshold_data["critical_pct"]
            val_threshold_eur = threshold_row["draft_materiality_threshold_eur"] if (has_draft and threshold_row["draft_materiality_threshold_eur"] is not None) else threshold_data["materiality_threshold_eur"]
            
            # Brouillon général du LOB
            has_lob_draft = selected_lob_data["statut"] == "EN_ATTENTE"
            if has_lob_draft:
                st.warning("⚠️ Des modifications structurelles sur ce portefeuille sont en attente de validation.")
            val_libelle = selected_lob_data["draft_libelle"] if (has_lob_draft and selected_lob_data["draft_libelle"] is not None) else selected_lob_data["libelle"]
            val_type_risque = selected_lob_data["draft_type_risque"] if (has_lob_draft and selected_lob_data["draft_type_risque"] is not None) else selected_lob_data["type_risque"]
            
            with st.form("edit_lob_form"):
                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    edit_libelle = st.text_input("Nouveau Libellé", value=val_libelle)
                    edit_type_risque = st.text_input("Nouveau Type de Risque", value=val_type_risque)
                with col_e2:
                    edit_seuil_pct = st.number_input(
                        "Nouveau Seuil Matérialité (%)",
                        min_value=0.0, max_value=100.0, value=float(val_seuil_pct), step=0.01,
                        help="Seuil en % de tolérance au-dessus duquel un écart individuel de réconciliation est considéré comme matériel."
                    )
                    edit_warning_pct = st.number_input(
                        "Nouveau Seuil Alerte (%)",
                        min_value=0.0, max_value=100.0, value=float(val_warning_pct), step=0.1,
                        help="Seuil d'écart cumulé en % déclenchant une alerte orange (informationnelle) sur la LOB."
                    )
                    edit_critical_pct = st.number_input(
                        "Nouveau Seuil Bloquant (%)",
                        min_value=0.0, max_value=100.0, value=float(val_critical_pct), step=0.1,
                        help="Seuil d'écart cumulé en % déclenchant une alerte rouge (bloquante) nécessitant une justification et double-approbation obligatoires."
                    )
                    edit_threshold_eur = st.number_input(
                        "Nouveau Seuil Absolu (€)",
                        min_value=0.0, value=float(val_threshold_eur), step=50.0,
                        help="Montant minimum en euros sous lequel les écarts de réconciliation sont jugés trop faibles pour bloquer ou nécessiter une action."
                    )
                
                edit_submitted = st.form_submit_button("Soumettre les modifications", type="primary", use_container_width=True)
                if edit_submitted:
                    if user.role == "Responsable MOA":
                        # Modification directe
                        for db_path in ["data/actuarecette.db", "data/actuarecette_v2.db"]:
                            if os.path.exists(db_path):
                                try:
                                    conn_db = sqlite_connection(db_path)
                                    conn_db.execute(
                                        """UPDATE portefeuilles SET
                                           libelle=?, type_risque=?, statut='ACTIF',
                                           draft_libelle=NULL, draft_type_risque=NULL,
                                           valide_par_sso=?, date_validation=datetime('now')
                                           WHERE id_portefeuille=?""",
                                        (edit_libelle, edit_type_risque, user.sso, lob_id_to_edit)
                                    )
                                    conn_db.execute(
                                        """INSERT OR REPLACE INTO portefeuilles_seuils_domaines
                                           (id_portefeuille, domaine, seuil_materialite_pct, warning_pct, critical_pct, materiality_threshold_eur,
                                            statut, valide_par_sso, date_validation, draft_seuil_materialite_pct, draft_warning_pct, draft_critical_pct, draft_materiality_threshold_eur)
                                           VALUES (?, ?, ?, ?, ?, ?, 'ACTIF', ?, datetime('now'), NULL, NULL, NULL, NULL)""",
                                        (lob_id_to_edit, selected_domaine, edit_seuil_pct, edit_warning_pct, edit_critical_pct, edit_threshold_eur, user.sso)
                                    )
                                    conn_db.commit()
                                    conn_db.close()
                                except Exception as e:
                                    st.error(f"Erreur SQLite lors de la modification : {e}")
                        log_admin_audit(user.sso, user.name, user.role, "LOB_MODIFIED", f"Modification directe des seuils de la LOB {lob_id_to_edit} pour le domaine {selected_domaine}", lob_id_to_edit)
                        st.session_state["user_success_message"] = f"✔ Seuils de la LOB {lob_id_to_edit} ({selected_domaine}) mis à jour avec succès !"
                        st.rerun()
                    else:
                        # Maker proposed modification
                        for db_path in ["data/actuarecette.db", "data/actuarecette_v2.db"]:
                            if os.path.exists(db_path):
                                try:
                                    conn_db = sqlite_connection(db_path)
                                    conn_db.execute(
                                        """UPDATE portefeuilles SET
                                           statut='EN_ATTENTE', cree_par_sso=?, date_creation=datetime('now'),
                                           draft_libelle=?, draft_type_risque=?
                                           WHERE id_portefeuille=?""",
                                        (user.sso, edit_libelle, edit_type_risque, lob_id_to_edit)
                                    )
                                    # Insert/update draft thresholds in portefeuilles_seuils_domaines
                                    # First read current active values in case we need to seed the row
                                    cursor = conn_db.cursor()
                                    cursor.execute("SELECT 1 FROM portefeuilles_seuils_domaines WHERE id_portefeuille = ? AND domaine = ?", (lob_id_to_edit, selected_domaine))
                                    row_exists = cursor.fetchone()
                                    if not row_exists:
                                        conn_db.execute(
                                            """INSERT INTO portefeuilles_seuils_domaines
                                               (id_portefeuille, domaine, seuil_materialite_pct, warning_pct, critical_pct, materiality_threshold_eur,
                                                statut, cree_par_sso, date_creation, draft_seuil_materialite_pct, draft_warning_pct, draft_critical_pct, draft_materiality_threshold_eur)
                                               VALUES (?, ?, ?, ?, ?, ?, 'EN_ATTENTE', ?, datetime('now'), ?, ?, ?, ?)""",
                                            (lob_id_to_edit, selected_domaine, threshold_data["seuil_materialite_pct"], threshold_data["warning_pct"],
                                             threshold_data["critical_pct"], threshold_data["materiality_threshold_eur"], user.sso,
                                             edit_seuil_pct, edit_warning_pct, edit_critical_pct, edit_threshold_eur)
                                        )
                                    else:
                                        conn_db.execute(
                                            """UPDATE portefeuilles_seuils_domaines SET
                                               statut='EN_ATTENTE', cree_par_sso=?, date_creation=datetime('now'),
                                               draft_seuil_materialite_pct=?, draft_warning_pct=?, draft_critical_pct=?, draft_materiality_threshold_eur=?
                                               WHERE id_portefeuille=? AND domaine=?""",
                                            (user.sso, edit_seuil_pct, edit_warning_pct, edit_critical_pct, edit_threshold_eur, lob_id_to_edit, selected_domaine)
                                        )
                                    conn_db.commit()
                                    conn_db.close()
                                except Exception as e:
                                    st.error(f"Erreur SQLite lors de la proposition : {e}")
                        log_admin_audit(user.sso, user.name, user.role, "LOB_MODIFICATION_PROPOSED", f"Proposition de modification de seuils pour la LOB {lob_id_to_edit} ({selected_domaine})", lob_id_to_edit)
                        st.session_state["user_success_message"] = f"✔ Proposition de modification pour la LOB {lob_id_to_edit} ({selected_domaine}) soumise au Manager !"
                        st.rerun()

    # ---------------------------------------------------------------------------
    with tab2:
        st.markdown("### Créateur de Règles de Contrôle Dynamiques")
        
        # Charger la liste des portefeuilles actifs ou créés par l'utilisateur (en attente)
        conn = sqlite_connection("data/actuarecette.db")
        conn.row_factory = sqlite3.Row
        portefeuilles = conn.execute("SELECT id_portefeuille, libelle, statut, cree_par_sso FROM portefeuilles").fetchall()
        conn.close()
        if user.role == "Actuaire MOA":
            portefeuilles = [p for p in portefeuilles if user.can_view_lob(p["id_portefeuille"]) or p["cree_par_sso"] == user.sso]
        
        lob_options = {f"{p['libelle']} ({p['id_portefeuille']})": p['id_portefeuille'] for p in portefeuilles}
        
        if not lob_options:
            st.warning("Aucun portefeuille disponible. Créez un portefeuille dans le premier onglet d'abord.")
        else:
            # Dictionnaire de configuration dynamique par domaine
            DOMAINE_CONFIGS = {
                "Prime": {
                    "tooltip_cible": "La colonne contenant la prime calculée à vérifier (ex: PRIME_DSI, COTIS_TTC).",
                    "tooltip_valeur": "La valeur cible de comparaison. Peut être une colonne de référence (ex: PRIME_REF) ou une constante numérique.",
                    "tooltip_formule": "La formule de calcul théorique utilisant des opérateurs standards (ex: BASE * COEFF_AGE * CRM).",
                    "placeholder_cible": "PRIME_DSI",
                    "placeholder_valeur": "PRIME_REF",
                    "placeholder_formule": "BASE * COEFF_AGE * CRM",
                    "default_tolerance": 0.05,
                    "default_severity": "ALERTE"
                },
                "Sinistre": {
                    "tooltip_cible": "La colonne représentant la charge ou le règlement de sinistre (ex: MONTANT_REGLEMENT, CHARGE_SINISTRE).",
                    "tooltip_valeur": "Le seuil limite ou la colonne de référence (ex: FRANCHISE_CONTRAT, PLAFOND_GARANTIE).",
                    "tooltip_formule": "Calcul théorique du coût de sinistre net (ex: COUT_BRUT - FRANCHISE).",
                    "placeholder_cible": "CHARGE_SINISTRE",
                    "placeholder_valeur": "PLAFOND_GARANTIE",
                    "placeholder_formule": "COUT_BRUT - FRANCHISE",
                    "default_tolerance": 1.00,
                    "default_severity": "ALERTE"
                },
                "Réserve": {
                    "tooltip_cible": "La provision mathématique ou le Best Estimate à auditer (ex: BEST_ESTIMATE_DSI, PROV_SINISTRES).",
                    "tooltip_valeur": "La provision de référence ou le seuil de Solvabilité II (ex: BE_REF, ROUGH_BENCHMARK).",
                    "tooltip_formule": "Formule de modélisation ou d'actualisation de la réserve (ex: BE_REF * 1.025).",
                    "placeholder_cible": "BEST_ESTIMATE_DSI",
                    "placeholder_valeur": "BE_REF",
                    "placeholder_formule": "BE_REF * 1.025",
                    "default_tolerance": 10.00,
                    "default_severity": "ALERTE"
                },
                "Contrat": {
                    "tooltip_cible": "Le paramètre contractuel ou statut à vérifier (ex: STATUT_POLICE, DATE_EFFET, AGE_CONDUCTEUR).",
                    "tooltip_valeur": "La valeur cible (ex: 'ACTIF', 'SUSPENDU', ou la date de référence DATE_EFFET_REF).",
                    "tooltip_formule": "Calcul de validation de cohérence ou d'éligibilité (ex: DATE_EFFET < DATE_ECHEANCE).",
                    "placeholder_cible": "STATUT_POLICE",
                    "placeholder_valeur": "'ACTIF'",
                    "placeholder_formule": "DATE_EFFET < DATE_ECHEANCE",
                    "default_tolerance": 0.00,
                    "default_severity": "BLOQUANT"
                },
                "Réassurance": {
                    "tooltip_cible": "La prime cédée ou la charge de sinistre cédée au traité (ex: PRIME_CEDEE, PART_REASSUREUR).",
                    "tooltip_valeur": "La limite ou la portée du traité de réassurance (ex: PRIORITE_TRAITE, PORTÉE_XL).",
                    "tooltip_formule": "Calcul du partage de risque (ex: MAX(0, CHARGE_SINISTRE - PRIORITE) * TAUX_CESSION).",
                    "placeholder_cible": "PRIME_CEDEE",
                    "placeholder_valeur": "PRIORITE_TRAITE",
                    "placeholder_formule": "MAX(0, CHARGE_SINISTRE - PRIORITE) * TAUX_CESSION",
                    "default_tolerance": 5.00,
                    "default_severity": "BLOQUANT"
                }
            }

            # Gestion de l'état du contexte (Session State)
            if "loaded_builder_lob" not in st.session_state:
                st.session_state["loaded_builder_lob"] = None
            if "loaded_builder_domaine" not in st.session_state:
                st.session_state["loaded_builder_domaine"] = None

            # Étape 1 : Choix du contexte
            if st.session_state["loaded_builder_lob"] is None or st.session_state["loaded_builder_domaine"] is None:
                st.info("💡 Veuillez sélectionner le portefeuille cible et le domaine de recette pour charger l'espace de travail réactif.")
                
                col_sel1, col_sel2 = st.columns(2)
                with col_sel1:
                    preselected_lob_id = st.session_state.pop("preselected_new_lob", None)
                    default_index = 0
                    if preselected_lob_id:
                        for idx, (label, val) in enumerate(lob_options.items()):
                            if val == preselected_lob_id:
                                default_index = idx
                                break
                    sel_lob = st.selectbox("Portefeuille cible (LOB)", options=list(lob_options.keys()), index=default_index, key="builder_select_lob")
                with col_sel2:
                    sel_domaine = st.selectbox("Domaine de recette", options=list(DOMAINE_CONFIGS.keys()), key="builder_select_domaine")
                
                if st.button("🚀 Charger le Contexte", type="primary", use_container_width=True):
                    st.session_state["loaded_builder_lob"] = lob_options[sel_lob]
                    st.session_state["loaded_builder_domaine"] = sel_domaine
                    st.rerun()

                st.markdown("---")
                st.markdown("### 📋 Liste de toutes les règles dynamiques (Toutes LOBs / Domaines)")
                
                # Récupérer toutes les règles dynamiques
                conn = sqlite_connection("data/actuarecette.db")
                conn.row_factory = sqlite3.Row
                rules = conn.execute("SELECT * FROM regles_recette_dynamiques ORDER BY date_creation DESC").fetchall()
                conn.close()
                if user.role == "Actuaire MOA":
                    rules = [r for r in rules if user.can_view_lob(r["id_portefeuille"]) or r["cree_par_sso"] == user.sso]
                
                if not rules:
                    st.info("Aucune règle de recette dynamique enregistrée pour le moment.")
                else:
                    for r in rules:
                        with st.container(border=True):
                            col1, col2, col3 = st.columns([6, 3, 3])
                            with col1:
                                st.markdown(f"**{r['id_regle']} v{r['version_regle']}** — {r['libelle']}")
                                st.caption(f"LOB: `{r['id_portefeuille']}` · Domaine: **{r['domaine']}** · Cible: `{r['colonne_cible']}` {r['operateur_logique']} `{r['valeur_seuil']}`")
                                if r['condition_application']:
                                    st.caption(f"Condition d'application: `{r['condition_application']}`")
                                st.caption(f"Formule théorique: `{r['formule_theorique']}` (Tolérance: {r['tolerance_unitaire']} €)")
                                st.caption(f"Sévérité: **{r['severite']}**")
                            with col2:
                                st.markdown(f"**Gouvernance**")
                                color = {
                                    "BROUILLON": "var(--ar-text-secondary)",
                                    "EN_ATTENTE": "#D97706",
                                    "ACTIF": "#059669",
                                    "REJETÉ": "#DC2626",
                                    "OBSOLÈTE": "var(--ar-text-muted)"
                                }.get(r['statut'], "var(--ar-text-secondary)")
                                
                                st.markdown(f"Statut: <span style='color:{color};font-weight:700;'>{r['statut']}</span>", unsafe_allow_html=True)
                                st.caption(f"Créé par: `{r['cree_par_sso']}` le {r['date_creation']}")
                                if r['valide_par_sso']:
                                    st.caption(f"Validé par: `{r['valide_par_sso']}` le {r['date_validation']}")
                            with col3:
                                st.markdown("**Actions**")
                                if r['statut'] in ("BROUILLON", "REJETÉ"):
                                    if st.button("🚀 Soumettre", key=f"submit_all_{r['id_regle']}_{r['version_regle']}", use_container_width=True):
                                        for db_path in ["data/actuarecette.db", "data/actuarecette_v2.db"]:
                                            conn_db = sqlite_connection(db_path)
                                            conn_db.execute(
                                                "UPDATE regles_recette_dynamiques SET statut = 'EN_ATTENTE' WHERE id_regle = ? AND version_regle = ?",
                                                [r['id_regle'], r['version_regle']]
                                            )
                                            conn_db.commit()
                                            conn_db.close()
                                        log_admin_audit(user.sso, user.name, user.role, "RULE_SUBMITTED", f"Soumission de la regle {r['id_regle']} v{r['version_regle']} pour validation", r['id_portefeuille'])
                                        st.session_state["user_success_message"] = f"Règle {r['id_regle']} v{r['version_regle']} soumise à la validation."
                                        st.rerun()
                                    if st.button("🗑️ Supprimer", key=f"delete_all_{r['id_regle']}_{r['version_regle']}", type="secondary", use_container_width=True):
                                        for db_path in ["data/actuarecette.db", "data/actuarecette_v2.db"]:
                                            if os.path.exists(db_path):
                                                conn_db = sqlite_connection(db_path)
                                                conn_db.execute(
                                                    "DELETE FROM regles_recette_dynamiques WHERE id_regle = ? AND version_regle = ?",
                                                    [r['id_regle'], r['version_regle']]
                                                )
                                                conn_db.commit()
                                                conn_db.close()
                                        log_admin_audit(user.sso, user.name, user.role, "RULE_DELETED", f"Suppression de la regle {r['id_regle']} v{r['version_regle']}", r['id_portefeuille'])
                                        st.session_state["user_success_message"] = f"Règle {r['id_regle']} v{r['version_regle']} supprimée."
                                        st.rerun()
                                elif r['statut'] == "EN_ATTENTE":
                                    st.info("⏳ En attente de validation")
                                elif r['statut'] == "ACTIF":
                                    st.success("🟢 Active")
                                    if user.role in ("Validateur", "Responsable MOA"):
                                        if st.button("🔒 Désactiver", key=f"deact_all_{r['id_regle']}_{r['version_regle']}", type="secondary", use_container_width=True):
                                            for db_path in ["data/actuarecette.db", "data/actuarecette_v2.db"]:
                                                if os.path.exists(db_path):
                                                    conn_db = sqlite_connection(db_path)
                                                    conn_db.execute(
                                                        "UPDATE regles_recette_dynamiques SET statut = 'OBSOLÈTE' WHERE id_regle = ? AND version_regle = ?",
                                                        [r['id_regle'], r['version_regle']]
                                                    )
                                                    conn_db.commit()
                                                    conn_db.close()
                                            log_admin_audit(user.sso, user.name, user.role, "RULE_DEACTIVATED", f"Desactivation de la regle {r['id_regle']} v{r['version_regle']}", r['id_portefeuille'])
                                            st.session_state["user_success_message"] = f"Règle {r['id_regle']} v{r['version_regle']} désactivée."
                                            st.rerun()
                                else:
                                    st.caption("—")

            # Étape 2 : Espace de travail adapté au contexte chargé
            else:
                target_lob_id = st.session_state["loaded_builder_lob"]
                rule_domaine = st.session_state["loaded_builder_domaine"]
                
                # Récupérer le libellé pour l'affichage
                lob_libelle = target_lob_id
                for label, val in lob_options.items():
                    if val == target_lob_id:
                        lob_libelle = label
                        break

                # Bannière de contexte avec bouton de réinitialisation
                st.html(
                    f'<div style="padding:12px; border-radius:8px; background-color:rgba(0,100,255,0.08); border:1px solid rgba(0,100,255,0.2); margin-bottom:16px; display:flex; justify-content:space-between; align-items:center;">'
                    f'<div>🎯 Contexte chargé — Portefeuille : <strong>{lob_libelle}</strong> | Domaine : <strong>{rule_domaine}</strong></div>'
                    f'</div>'
                )
                
                if st.button("🔄 Changer de contexte", key="btn_reset_context", use_container_width=True):
                    st.session_state["loaded_builder_lob"] = None
                    st.session_state["loaded_builder_domaine"] = None
                    st.rerun()

                # Séparation en deux colonnes
                col_left, col_right = st.columns(2)

                # Colonne de gauche : Règles existantes dans ce contexte
                with col_left:
                    st.markdown("#### 📋 Règles existantes dans ce contexte")
                    
                    conn = sqlite_connection("data/actuarecette.db")
                    conn.row_factory = sqlite3.Row
                    context_rules = conn.execute(
                        "SELECT * FROM regles_recette_dynamiques WHERE id_portefeuille = ? AND domaine = ? ORDER BY date_creation DESC",
                        (target_lob_id, rule_domaine)
                    ).fetchall()
                    conn.close()
                    
                    if user.role == "Actuaire MOA":
                        context_rules = [r for r in context_rules if user.can_view_lob(r["id_portefeuille"]) or r["cree_par_sso"] == user.sso]
                    
                    if not context_rules:
                        st.info("Aucune règle de recette dynamique n'existe pour le moment dans ce contexte (LOB & Domaine).")
                    else:
                        for r in context_rules:
                            with st.container(border=True):
                                st.markdown(f"**{r['id_regle']} v{r['version_regle']}** — {r['libelle']}")
                                st.caption(f"Cible: `{r['colonne_cible']}` {r['operateur_logique']} `{r['valeur_seuil']}`")
                                if r['condition_application']:
                                    st.caption(f"Condition d'application: `{r['condition_application']}`")
                                st.caption(f"Formule: `{r['formule_theorique']}` (Tolérance: {r['tolerance_unitaire']} €)")
                                st.caption(f"Sévérité: **{r['severite']}**")
                                
                                color = {
                                    "BROUILLON": "var(--ar-text-secondary)",
                                    "EN_ATTENTE": "#D97706",
                                    "ACTIF": "#059669",
                                    "REJETÉ": "#DC2626",
                                    "OBSOLÈTE": "var(--ar-text-muted)"
                                }.get(r['statut'], "var(--ar-text-secondary)")
                                
                                st.markdown(f"Statut: <span style='color:{color};font-weight:700;'>{r['statut']}</span>", unsafe_allow_html=True)
                                
                                if r['statut'] in ("BROUILLON", "REJETÉ"):
                                    if st.button("🚀 Soumettre", key=f"submit_context_{r['id_regle']}_{r['version_regle']}", use_container_width=True):
                                        for db_path in ["data/actuarecette.db", "data/actuarecette_v2.db"]:
                                            conn_db = sqlite_connection(db_path)
                                            conn_db.execute(
                                                "UPDATE regles_recette_dynamiques SET statut = 'EN_ATTENTE' WHERE id_regle = ? AND version_regle = ?",
                                                [r['id_regle'], r['version_regle']]
                                            )
                                            conn_db.commit()
                                            conn_db.close()
                                        log_admin_audit(user.sso, user.name, user.role, "RULE_SUBMITTED", f"Soumission de la regle {r['id_regle']} v{r['version_regle']} pour validation", r['id_portefeuille'])
                                        st.session_state["user_success_message"] = f"Règle {r['id_regle']} v{r['version_regle']} soumise à la validation."
                                        st.rerun()
                                    if st.button("🗑️ Supprimer", key=f"delete_context_{r['id_regle']}_{r['version_regle']}", type="secondary", use_container_width=True):
                                        for db_path in ["data/actuarecette.db", "data/actuarecette_v2.db"]:
                                            if os.path.exists(db_path):
                                                conn_db = sqlite_connection(db_path)
                                                conn_db.execute(
                                                    "DELETE FROM regles_recette_dynamiques WHERE id_regle = ? AND version_regle = ?",
                                                    [r['id_regle'], r['version_regle']]
                                                )
                                                conn_db.commit()
                                                conn_db.close()
                                        log_admin_audit(user.sso, user.name, user.role, "RULE_DELETED", f"Suppression de la regle {r['id_regle']} v{r['version_regle']}", r['id_portefeuille'])
                                        st.session_state["user_success_message"] = f"Règle {r['id_regle']} v{r['version_regle']} supprimée."
                                        st.rerun()
                                elif r['statut'] == "EN_ATTENTE":
                                    st.info("⏳ En attente de validation")
                                elif r['statut'] == "ACTIF":
                                    st.success("🟢 Active")
                                    if user.role in ("Validateur", "Responsable MOA"):
                                        if st.button("🔒 Désactiver", key=f"deact_context_{r['id_regle']}_{r['version_regle']}", type="secondary", use_container_width=True):
                                            for db_path in ["data/actuarecette.db", "data/actuarecette_v2.db"]:
                                                if os.path.exists(db_path):
                                                    conn_db = sqlite_connection(db_path)
                                                    conn_db.execute(
                                                        "UPDATE regles_recette_dynamiques SET statut = 'OBSOLÈTE' WHERE id_regle = ? AND version_regle = ?",
                                                        [r['id_regle'], r['version_regle']]
                                                    )
                                                    conn_db.commit()
                                                    conn_db.close()
                                            log_admin_audit(user.sso, user.name, user.role, "RULE_DEACTIVATED", f"Desactivation de la regle {r['id_regle']} v{r['version_regle']}", r['id_portefeuille'])
                                            st.session_state["user_success_message"] = f"Règle {r['id_regle']} v{r['version_regle']} désactivée."
                                            st.rerun()

                # Colonne de droite : Formulaire de création
                with col_right:
                    st.markdown("#### ➕ Créer une nouvelle règle")
                    
                    config = DOMAINE_CONFIGS[rule_domaine]
                    
                    with st.form("new_rule_form"):
                        rule_id = st.text_input("Identifiant Règle (ex: CTRL-006)", placeholder="CTRL-...").strip().upper()
                        rule_libelle = st.text_input("Libellé de la règle", placeholder="Ex: Cohérence des dates de contrat...")
                        
                        rule_col = st.text_input(
                            "Colonne à contrôler",
                            placeholder=config["placeholder_cible"],
                            help=config["tooltip_cible"]
                        )
                        
                        rule_op = st.selectbox("Opérateur logique de conformité", options=["==", ">=", "<="])
                        
                        rule_val = st.text_input(
                            "Valeur attendue (seuil ou colonne)",
                            placeholder=config["placeholder_valeur"],
                            help=config["tooltip_valeur"]
                        )
                        
                        rule_formula = st.text_input(
                            "Formule théorique",
                            placeholder=config["placeholder_formule"],
                            help=config["tooltip_formule"]
                        )
                        
                        rule_tol = st.number_input(
                            "Tolérance unitaire (€)",
                            min_value=0.0,
                            value=config["default_tolerance"],
                            step=0.01
                        )
                        
                        severity_options = ["ALERTE", "BLOQUANT"]
                        try:
                            sev_default_idx = severity_options.index(config["default_severity"])
                        except ValueError:
                            sev_default_idx = 0
                        rule_sev = st.selectbox("Sévérité en cas d'écart", options=severity_options, index=sev_default_idx)
                        
                        rule_cond = st.text_input("Condition d'application (facultative)", placeholder="Ex: age_conducteur < 25")

                        submitted = st.form_submit_button("Enregistrer en Brouillon", type="primary", use_container_width=True)
                        
                        if submitted:
                            if not rule_id or not rule_libelle or not rule_col or not rule_formula or not rule_val:
                                st.error("Veuillez remplir tous les champs obligatoires.")
                            else:
                                # 1. Validation syntaxique de la formule théorique via AST
                                formula_ok = False
                                try:
                                    SafeFormulaParser(rule_formula)
                                    formula_ok = True
                                except Exception as e:
                                    st.error(f"❌ La formule théorique contient une erreur syntaxique ou un nœud non autorisé : {e}")

                                # 2. Validation de la condition d'application (si présente)
                                cond_ok = True
                                if rule_cond.strip():
                                    try:
                                        SafeFormulaParser(rule_cond)
                                    except Exception as e:
                                        st.error(f"❌ La condition d'application contient une erreur syntaxique ou un nœud non autorisé : {e}")
                                        cond_ok = False

                                if formula_ok and cond_ok:
                                    # Calculer la prochaine version de la règle
                                    conn = sqlite_connection("data/actuarecette.db")
                                    cursor = conn.cursor()
                                    cursor.execute("SELECT MAX(CAST(version_regle AS REAL)) FROM regles_recette_dynamiques WHERE id_regle = ?", [rule_id])
                                    max_v = cursor.fetchone()[0]
                                    next_v = f"{max_v + 1.0:.1f}" if max_v is not None else "1.0"
                                    conn.close()

                                    # Insérer la règle en statut BROUILLON (les deux bases)
                                    inserted = False
                                    for db_path in ["data/actuarecette.db", "data/actuarecette_v2.db"]:
                                        if os.path.exists(db_path):
                                            try:
                                                conn_db = sqlite_connection(db_path)
                                                conn_db.execute(
                                                    """INSERT INTO regles_recette_dynamiques
                                                    (id_regle, id_portefeuille, version_regle, libelle, colonne_cible, operateur_logique,
                                                     valeur_seuil, formule_theorique, tolerance_unitaire, statut, severite, condition_application, cree_par_sso, domaine)
                                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'BROUILLON', ?, ?, ?, ?)""",
                                                    (rule_id, target_lob_id, next_v, rule_libelle, rule_col, rule_op,
                                                     rule_val, rule_formula, rule_tol, rule_sev, rule_cond.strip() or None, user.sso, rule_domaine)
                                                )
                                                conn_db.commit()
                                                conn_db.close()
                                                inserted = True
                                            except Exception as e:
                                                st.error(f"Erreur SQLite lors de la création de la règle dans {db_path} : {e}")
                                                inserted = False
                                                break
                                    
                                    if inserted:
                                        log_admin_audit(user.sso, user.name, user.role, "RULE_CREATED", f"Creation de la regle {rule_id} v{next_v} en statut BROUILLON pour le domaine {rule_domaine}", target_lob_id)
                                        st.session_state["user_success_message"] = f"✔ Règle {rule_id} v{next_v} créée en Brouillon avec succès !"
                                        st.rerun()

    # ---------------------------------------------------------------------------
    # Onglet 3 : Cabinet de Validation (4 yeux)
    # ---------------------------------------------------------------------------
    with tab3:
        st.markdown("### 📁 Validation des Portefeuilles (LOBs)")
        
        # Charger les LOBs EN_ATTENTE et les seuils de domaine EN_ATTENTE
        conn = sqlite_connection("data/actuarecette.db")
        conn.row_factory = sqlite3.Row
        pending_lobs = conn.execute("SELECT * FROM portefeuilles WHERE statut = 'EN_ATTENTE'").fetchall()
        pending_seuils = conn.execute(
            """SELECT s.*, p.libelle 
               FROM portefeuilles_seuils_domaines s
               JOIN portefeuilles p ON s.id_portefeuille = p.id_portefeuille
               WHERE s.statut = 'EN_ATTENTE'"""
        ).fetchall()
        conn.close()
        
        if not pending_lobs and not pending_seuils:
            st.info("Aucun portefeuille (LOB) ou seuil de domaine en attente de validation.")
        else:
            if pending_lobs:
                st.markdown("#### 📁 Créations / Modifications Structurelles de Portefeuilles")
                for p in pending_lobs:
                    is_creation = p["draft_libelle"] is None and p["draft_type_risque"] is None
                    with st.container(border=True):
                        col1, col2 = st.columns([8, 4])
                        with col1:
                            if is_creation:
                                st.markdown(f"##### 📁 Création de LOB : `{p['id_portefeuille']}`")
                                st.markdown(f"**Code Métier :** `{p['code_metier']}` · **Libellé :** {p['libelle']} · **Type Risque :** `{p['type_risque']}`")
                            else:
                                st.markdown(f"##### ✏️ Modification de structure de LOB : `{p['id_portefeuille']}`")
                                col_diff_1, col_diff_2 = st.columns(2)
                                with col_diff_1:
                                    st.markdown("**Valeurs Actuelles**")
                                    st.markdown(f"- **Libellé :** {p['libelle']}")
                                    st.markdown(f"- **Type Risque :** `{p['type_risque']}`")
                                with col_diff_2:
                                    st.markdown("**Valeurs Proposées**")
                                    st.markdown(f"- **Libellé :** {p['draft_libelle']}")
                                    st.markdown(f"- **Type Risque :** `{p['draft_type_risque']}`")
                            st.caption(f"Soumis par: `{p['cree_par_sso']}` le {p['date_creation']}")
                        with col2:
                            st.markdown("##### ⚖ Décision de Validation")
                            if not user.is_checker:
                                st.warning("🔒 Validation réservée aux validateurs et responsables.")
                            elif user.sso == p['cree_par_sso']:
                                st.warning("🔒 Validation par un pair requise. Vous ne pouvez pas valider votre propre proposition.")
                            else:
                                col_btn1, col_btn2 = st.columns(2)
                                with col_btn1:
                                    if st.button("✅ Approuver", key=f"app_lob_{p['id_portefeuille']}", type="primary", use_container_width=True):
                                        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                        # Mettre à jour SQLite (les deux bases)
                                        for db_path in ["data/actuarecette.db", "data/actuarecette_v2.db"]:
                                            if os.path.exists(db_path):
                                                conn_db = sqlite_connection(db_path)
                                                if is_creation:
                                                    conn_db.execute(
                                                        "UPDATE portefeuilles SET statut = 'ACTIF', valide_par_sso = ?, date_validation = ? WHERE id_portefeuille = ?",
                                                        [user.sso, now_str, p['id_portefeuille']]
                                                    )
                                                    
                                                    # Mettre à jour automatiquement les assigned_lobs pour le créateur dans utilisateurs table
                                                    row = conn_db.execute("SELECT assigned_lobs FROM utilisateurs WHERE sso = ?", [p['cree_par_sso']]).fetchone()
                                                    if row:
                                                        current_lobs = [l.strip() for l in row[0].split(",") if l.strip()] if row[0] else []
                                                        if p['id_portefeuille'] not in current_lobs:
                                                            current_lobs.append(p['id_portefeuille'])
                                                            new_assigned_lobs = ",".join(current_lobs)
                                                            conn_db.execute("UPDATE utilisateurs SET assigned_lobs = ? WHERE sso = ?", [new_assigned_lobs, p['cree_par_sso']])
                                                    
                                                    # Mettre à jour automatiquement les checkers (Validateur & Responsable MOA)
                                                    checkers = conn_db.execute("SELECT sso, assigned_lobs FROM utilisateurs WHERE role IN ('Validateur', 'Responsable MOA')").fetchall()
                                                    for chk in checkers:
                                                        chk_sso = chk["sso"]
                                                        chk_lobs = [l.strip() for l in chk["assigned_lobs"].split(",") if l.strip()] if chk["assigned_lobs"] else []
                                                        if p['id_portefeuille'] not in chk_lobs:
                                                            chk_lobs.append(p['id_portefeuille'])
                                                            new_chk_assigned = ",".join(chk_lobs)
                                                            conn_db.execute("UPDATE utilisateurs SET assigned_lobs = ? WHERE sso = ?", [new_chk_assigned, chk_sso])
                                                else:
                                                    conn_db.execute(
                                                        """UPDATE portefeuilles SET
                                                           libelle = draft_libelle,
                                                           type_risque = draft_type_risque,
                                                           statut = 'ACTIF',
                                                           valide_par_sso = ?,
                                                           date_validation = ?,
                                                           draft_libelle = NULL,
                                                           draft_type_risque = NULL
                                                           WHERE id_portefeuille = ?""",
                                                        [user.sso, now_str, p['id_portefeuille']]
                                                    )
                                                conn_db.commit()
                                                conn_db.close()
                                        
                                        if is_creation:
                                            add_lob_to_registry(p['id_portefeuille'])
                                            log_admin_audit(user.sso, user.name, user.role, "LOB_APPROVED", f"Approbation de la creation de la LOB {p['id_portefeuille']}", p['id_portefeuille'])
                                            st.session_state["user_success_message"] = f"✔ Portefeuille {p['id_portefeuille']} approuvé et activé !"
                                        else:
                                            log_admin_audit(user.sso, user.name, user.role, "LOB_MODIFICATION_APPROVED", f"Approbation de la modification de la LOB {p['id_portefeuille']}", p['id_portefeuille'])
                                            st.session_state["user_success_message"] = f"✔ Modification du portefeuille {p['id_portefeuille']} approuvée !"
                                        st.rerun()
                                        
                                with col_btn2:
                                    if st.button("❌ Rejeter", key=f"rej_lob_{p['id_portefeuille']}", type="secondary", use_container_width=True):
                                        for db_path in ["data/actuarecette.db", "data/actuarecette_v2.db"]:
                                            if os.path.exists(db_path):
                                                conn_db = sqlite_connection(db_path)
                                                if is_creation:
                                                    conn_db.execute("DELETE FROM portefeuilles WHERE id_portefeuille = ?", [p['id_portefeuille']])
                                                else:
                                                    conn_db.execute(
                                                        """UPDATE portefeuilles SET
                                                           statut = 'ACTIF',
                                                           draft_libelle = NULL,
                                                           draft_type_risque = NULL
                                                           WHERE id_portefeuille = ?""",
                                                        [p['id_portefeuille']]
                                                    )
                                                conn_db.commit()
                                                conn_db.close()
                                                
                                        if is_creation:
                                            log_admin_audit(user.sso, user.name, user.role, "LOB_REJECTED", f"Rejet de la creation de la LOB {p['id_portefeuille']}", p['id_portefeuille'])
                                            st.session_state["user_error_message"] = f"Création du portefeuille {p['id_portefeuille']} rejetée."
                                        else:
                                            log_admin_audit(user.sso, user.name, user.role, "LOB_MODIFICATION_REJECTED", f"Rejet de la modification de la LOB {p['id_portefeuille']}", p['id_portefeuille'])
                                            st.session_state["user_error_message"] = f"Modification du portefeuille {p['id_portefeuille']} rejetée."
                                        st.rerun()
            
            if pending_seuils:
                st.markdown("#### 📏 Modifications de Seuils de Tolérance par Domaine")
                for s in pending_seuils:
                    with st.container(border=True):
                        col1, col2 = st.columns([8, 4])
                        with col1:
                            st.markdown(f"##### ✏️ Seuils LOB : `{s['id_portefeuille']}` ({s['libelle']}) — Domaine : **{s['domaine']}**")
                            col_diff_1, col_diff_2 = st.columns(2)
                            with col_diff_1:
                                st.markdown("**Valeurs Actuelles**")
                                st.markdown(f"- **Matérialité :** {s['seuil_materialite_pct']}%")
                                st.markdown(f"- **Alerte :** {s['warning_pct']}%")
                                st.markdown(f"- **Bloquant :** {s['critical_pct']}%")
                                st.markdown(f"- **Absolu :** {s['materiality_threshold_eur']} €")
                            with col_diff_2:
                                st.markdown("**Valeurs Proposées**")
                                st.markdown(f"- **Matérialité :** {s['draft_seuil_materialite_pct']}%")
                                st.markdown(f"- **Alerte :** {s['draft_warning_pct']}%")
                                st.markdown(f"- **Bloquant :** {s['draft_critical_pct']}%")
                                st.markdown(f"- **Absolu :** {s['draft_materiality_threshold_eur']} €")
                            st.caption(f"Soumis par: `{s['cree_par_sso']}` le {s['date_creation']}")
                        with col2:
                            st.markdown("##### ⚖ Décision de Validation")
                            if not user.is_checker:
                                st.warning("🔒 Validation réservée aux validateurs et responsables.")
                            elif user.sso == s['cree_par_sso']:
                                st.warning("🔒 Validation par un pair requise. Vous ne pouvez pas valider votre propre proposition.")
                            else:
                                col_btn1, col_btn2 = st.columns(2)
                                with col_btn1:
                                    if st.button("✅ Approuver", key=f"app_seuil_{s['id_portefeuille']}_{s['domaine']}", type="primary", use_container_width=True):
                                        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                        # Mettre à jour SQLite (les deux bases)
                                        for db_path in ["data/actuarecette.db", "data/actuarecette_v2.db"]:
                                            if os.path.exists(db_path):
                                                conn_db = sqlite_connection(db_path)
                                                conn_db.execute(
                                                    """UPDATE portefeuilles_seuils_domaines SET
                                                       seuil_materialite_pct = draft_seuil_materialite_pct,
                                                       warning_pct = draft_warning_pct,
                                                       critical_pct = draft_critical_pct,
                                                       materiality_threshold_eur = draft_materiality_threshold_eur,
                                                       statut = 'ACTIF',
                                                       valide_par_sso = ?,
                                                       date_validation = ?,
                                                       draft_seuil_materialite_pct = NULL,
                                                       draft_warning_pct = NULL,
                                                       draft_critical_pct = NULL,
                                                       draft_materiality_threshold_eur = NULL
                                                       WHERE id_portefeuille = ? AND domaine = ?""",
                                                    [user.sso, now_str, s['id_portefeuille'], s['domaine']]
                                                )
                                                conn_db.commit()
                                                conn_db.close()
                                        log_admin_audit(user.sso, user.name, user.role, "LOB_THRESHOLD_APPROVED", f"Approbation des seuils {s['domaine']} pour la LOB {s['id_portefeuille']}", s['id_portefeuille'])
                                        st.session_state["user_success_message"] = f"✔ Seuils {s['domaine']} pour {s['id_portefeuille']} approuvés !"
                                        st.rerun()
                                        
                                with col_btn2:
                                    if st.button("❌ Rejeter", key=f"rej_seuil_{s['id_portefeuille']}_{s['domaine']}", type="secondary", use_container_width=True):
                                        for db_path in ["data/actuarecette.db", "data/actuarecette_v2.db"]:
                                            if os.path.exists(db_path):
                                                conn_db = sqlite_connection(db_path)
                                                conn_db.execute(
                                                    """UPDATE portefeuilles_seuils_domaines SET
                                                       statut = 'ACTIF',
                                                       draft_seuil_materialite_pct = NULL,
                                                       draft_warning_pct = NULL,
                                                       draft_critical_pct = NULL,
                                                       draft_materiality_threshold_eur = NULL
                                                       WHERE id_portefeuille = ? AND domaine = ?""",
                                                    [s['id_portefeuille'], s['domaine']]
                                                )
                                                conn_db.commit()
                                                conn_db.close()
                                        log_admin_audit(user.sso, user.name, user.role, "LOB_THRESHOLD_REJECTED", f"Rejet des seuils {s['domaine']} pour la LOB {s['id_portefeuille']}", s['id_portefeuille'])
                                        st.session_state["user_error_message"] = f"Modification des seuils {s['domaine']} pour {s['id_portefeuille']} rejetée."
                                        st.rerun()
                                    
        st.markdown("---")
        st.markdown("### 📏 Double Approbation des Règles (Règle des 4 Yeux)")
        
        # Récupérer uniquement les règles EN_ATTENTE
        conn = sqlite_connection("data/actuarecette.db")
        conn.row_factory = sqlite3.Row
        pending_rules = conn.execute("SELECT * FROM regles_recette_dynamiques WHERE statut = 'EN_ATTENTE'").fetchall()
        conn.close()
        if user.role == "Actuaire MOA":
            pending_rules = [r for r in pending_rules if user.can_view_lob(r["id_portefeuille"])]
        
        if not pending_rules:
            st.html(
                """
                <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 40px 24px; text-align: center; background-color: var(--ar-bg-surface); border: 1px solid var(--ar-border); border-radius: 12px; margin-top: 10px;">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="width: 36px; height: 36px; color: var(--ar-text-muted); margin-bottom: 12px;">
                        <circle cx="12" cy="12" r="10"/>
                        <path d="m9 12 2 2 4-4"/>
                    </svg>
                    <h4 style="margin: 0 0 4px 0; color: var(--ar-text-primary); font-size: 1.0rem; font-weight: 700;">Aucune règle en attente</h4>
                    <p style="margin: 0; color: var(--ar-text-secondary); font-size: 0.8rem; max-width: 360px;">
                        Toutes les règles dynamiques soumises ont été arbitrées ou sont conformes.
                    </p>
                </div>
                """
            )
        else:
            st.caption(f"{len(pending_rules)} règle(s) en attente de validation.")
            
            for r in pending_rules:
                with st.container(border=True):
                    col1, col2 = st.columns([8, 4])
                    with col1:
                        st.markdown(f"#### Règle : `{r['id_regle']}` (v{r['version_regle']})")
                        st.markdown(f"**Libellé :** {r['libelle']}")
                        st.markdown(f"**LOB cible :** `{r['id_portefeuille']}` · **Colonne contrôlée :** `{r['colonne_cible']}`")
                        st.markdown(f"**Opérateur :** `{r['operateur_logique']}` · **Seuil de validation :** `{r['valeur_seuil']}`")
                        st.markdown(f"**Formule théorique :** `{r['formule_theorique']}` (Tolérance : {r['tolerance_unitaire']} €)")
                        if r['condition_application']:
                            st.markdown(f"**Condition d'application :** `{r['condition_application']}`")
                        st.caption(f"Soumise par: `{r['cree_par_sso']}` le {r['date_creation']}")
                    with col2:
                        st.markdown("##### ⚖ Décision de Validation")
                        
                        # Règle des 4 yeux Solvabilité II : le créateur ne peut pas valider lui-même
                        if user.sso == r['cree_par_sso']:
                            st.warning("🔒 Validation par un pair requise. Vous ne pouvez pas valider votre propre règle.")
                        else:
                            col_btn1, col_btn2 = st.columns(2)
                            with col_btn1:
                                if st.button("✅ Approuver", key=f"app_{r['id_regle']}_{r['version_regle']}", type="primary", use_container_width=True):
                                    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    # Mettre à jour SQLite (les deux bases)
                                    for db_path in ["data/actuarecette.db", "data/actuarecette_v2.db"]:
                                        if os.path.exists(db_path):
                                            conn_db = sqlite_connection(db_path)
                                            # Mettre l'ancienne version active en OBSOLETE
                                            conn_db.execute(
                                                "UPDATE regles_recette_dynamiques SET statut = 'OBSOLÈTE' WHERE id_regle = ? AND version_regle != ? AND id_portefeuille = ? AND statut = 'ACTIF'",
                                                [r['id_regle'], r['version_regle'], r['id_portefeuille']]
                                            )
                                            # Activer la nouvelle
                                            conn_db.execute(
                                                "UPDATE regles_recette_dynamiques SET statut = 'ACTIF', valide_par_sso = ?, date_validation = ? WHERE id_regle = ? AND version_regle = ?",
                                                [user.sso, now_str, r['id_regle'], r['version_regle']]
                                            )
                                            conn_db.commit()
                                            conn_db.close()
                                    log_admin_audit(user.sso, user.name, user.role, "RULE_APPROVED", f"Approbation de la regle {r['id_regle']} v{r['version_regle']}", r['id_portefeuille'])
                                    st.session_state["user_success_message"] = f"✔ Règle {r['id_regle']} v{r['version_regle']} approuvée et activée !"
                                    st.rerun()
                            with col_btn2:
                                if st.button("❌ Rejeter", key=f"rej_{r['id_regle']}_{r['version_regle']}", type="secondary", use_container_width=True):
                                    # Mettre à jour SQLite (les deux bases)
                                    for db_path in ["data/actuarecette.db", "data/actuarecette_v2.db"]:
                                        if os.path.exists(db_path):
                                            conn_db = sqlite_connection(db_path)
                                            conn_db.execute(
                                                "UPDATE regles_recette_dynamiques SET statut = 'REJETÉ' WHERE id_regle = ? AND version_regle = ?",
                                                [r['id_regle'], r['version_regle']]
                                            )
                                            conn_db.commit()
                                            conn_db.close()
                                    log_admin_audit(user.sso, user.name, user.role, "RULE_REJECTED", f"Rejet de la regle {r['id_regle']} v{r['version_regle']}", r['id_portefeuille'])
                                    st.session_state["user_error_message"] = f"Règle {r['id_regle']} v{r['version_regle']} rejetée."
                                    st.rerun()

    # ---------------------------------------------------------------------------
    # Onglet 4 : Gestion des Utilisateurs (SSO/IAM)
    # ---------------------------------------------------------------------------
    with tab4:
        st.markdown("### 👥 Gestion des Profils Utilisateurs (SSO/IAM)")
        if user.role != "Responsable MOA":
            st.warning("🔒 Accès restreint. Seuls les utilisateurs avec le rôle **Responsable MOA** peuvent gérer les profils.")
        else:
            # 1. Liste des utilisateurs existants
            st.markdown("#### Liste des Profils Actifs & Suspendus")
            
            conn = sqlite_connection("data/actuarecette.db")
            conn.row_factory = sqlite3.Row
            users_db = conn.execute("SELECT sso, name, role, assigned_lobs, statut, date_creation, cree_par FROM utilisateurs").fetchall()
            conn.close()
            
            users_list = []
            for u in users_db:
                users_list.append(dict(u))
                
            if users_list:
                df_users = pd.DataFrame(users_list)
                st.dataframe(
                    df_users.rename(columns={
                        "sso": "SSO ID",
                        "name": "Nom Complet",
                        "role": "Rôle Habilité",
                        "assigned_lobs": "Portefeuilles (LOBs)",
                        "statut": "Statut",
                        "date_creation": "Date Création",
                        "cree_par": "Créé Par"
                    }),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("Aucun utilisateur dans la base SQLite.")
                
            st.markdown("---")
            
            # 2. Formulaire de création de nouvel utilisateur
            st.markdown("#### ➕ Créer un nouvel utilisateur")
            
            # Charger les LOBs pour la sélection
            conn = sqlite_connection("data/actuarecette.db")
            conn.row_factory = sqlite3.Row
            portefeuilles_db = conn.execute("SELECT id_portefeuille FROM portefeuilles").fetchall()
            conn.close()
            all_lobs_list = [p['id_portefeuille'] for p in portefeuilles_db]
            
            import re
            
            with st.form("new_user_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    new_user_sso = st.text_input("Identifiant SSO unique (ex: antoine.dupont)", placeholder="prenom.nom", key="new_user_sso_val").strip().lower()
                    new_user_name = st.text_input("Nom Complet (ex: Antoine Dupont)", placeholder="Prénom Nom", key="new_user_name_val").strip()
                with col2:
                    new_user_role = st.selectbox("Rôle réglementaire", options=["Actuaire MOA", "Validateur", "Responsable MOA"], key="new_user_role_val")
                    new_user_lobs = st.multiselect("Portefeuilles (LOBs) autorisés", options=all_lobs_list, default=all_lobs_list[:1], key="new_user_lobs_val")
                    
                submitted_user = st.form_submit_button("Créer le Profil Utilisateur", type="primary", use_container_width=True)
                
                if submitted_user:
                    if not new_user_sso or not new_user_name:
                        st.error("Veuillez remplir les champs obligatoires (SSO et Nom).")
                    elif not re.match(r'^[a-zA-Z0-9._-]+$', new_user_sso):
                        st.error("L'identifiant SSO contient des caractères invalides (lettres, chiffres, '.', '_', '-' uniquement).")
                    else:
                        lobs_str = ",".join(new_user_lobs)
                        inserted = False
                        # Insérer dans SQLite (les deux bases pour cohérence)
                        for db_path in ["data/actuarecette.db", "data/actuarecette_v2.db"]:
                            _initialize_users_table_if_needed(db_path)
                            try:
                                conn_db = sqlite_connection(db_path)
                                conn_db.execute(
                                    """INSERT OR REPLACE INTO utilisateurs (sso, name, role, assigned_lobs, statut, cree_par)
                                       VALUES (?, ?, ?, ?, 'ACTIF', ?)""",
                                    (new_user_sso, new_user_name, new_user_role, lobs_str, user.sso)
                                )
                                conn_db.commit()
                                conn_db.close()
                                inserted = True
                            except Exception as e:
                                st.error(f"Erreur lors de la création de l'utilisateur dans {db_path} : {e}")
                                inserted = False
                                break
                                    
                        if inserted:
                            log_admin_audit(user.sso, user.name, user.role, "USER_CREATED", f"Création de l'utilisateur {new_user_sso} (Rôle: {new_user_role})")
                            st.session_state["user_success_message"] = f"L'utilisateur {new_user_name} ({new_user_sso}) a été créé avec succès."
                            st.session_state["new_user_sso_val"] = ""
                            st.session_state["new_user_name_val"] = ""
                            st.session_state["new_user_role_val"] = "Actuaire MOA"
                            st.session_state["new_user_lobs_val"] = all_lobs_list[:1] if all_lobs_list else []
                            st.rerun()

                            
            st.markdown("---")
            
            # 3. Actions sur les utilisateurs (Activer/Désactiver/Supprimer)
            st.markdown("#### ⚙️ Gérer les actions rapides")
            
            for u in users_list:
                # Ne pas s'auto-supprimer ou s'auto-désactiver
                if u["sso"] == user.sso:
                    continue
                with st.container(border=True):
                    if st.session_state.get("editing_user_sso") == u["sso"]:
                        st.markdown(f"✏️ **Modifier le profil de {u['name']}** (`{u['sso']}`)")
                        with st.form(f"edit_user_form_{u['sso']}", clear_on_submit=False):
                            col_ed1, col_ed2 = st.columns(2)
                            with col_ed1:
                                edit_name = st.text_input("Nom Complet", value=u["name"]).strip()
                                edit_role = st.selectbox("Rôle réglementaire", options=["Actuaire MOA", "Validateur", "Responsable MOA"], index=["Actuaire MOA", "Validateur", "Responsable MOA"].index(u["role"]))
                            with col_ed2:
                                current_lobs = [l.strip() for l in u["assigned_lobs"].split(",") if l.strip()] if u["assigned_lobs"] else []
                                edit_lobs = st.multiselect("Portefeuilles (LOBs) autorisés", options=all_lobs_list, default=[l for l in current_lobs if l in all_lobs_list])
                            
                            c_btn1, c_btn2 = st.columns(2)
                            with c_btn1:
                                submit_edit = st.form_submit_button("Enregistrer les modifications", type="primary", use_container_width=True)
                            with c_btn2:
                                cancel_edit = st.form_submit_button("Annuler", use_container_width=True)
                                
                            if submit_edit:
                                if not edit_name:
                                    st.error("Le nom complet ne peut pas être vide.")
                                else:
                                    edit_lobs_str = ",".join(edit_lobs)
                                    for db_path in ["data/actuarecette.db", "data/actuarecette_v2.db"]:
                                        _initialize_users_table_if_needed(db_path)
                                        conn_db = sqlite_connection(db_path)
                                        conn_db.execute(
                                            "UPDATE utilisateurs SET name = ?, role = ?, assigned_lobs = ? WHERE sso = ?",
                                            (edit_name, edit_role, edit_lobs_str, u["sso"])
                                        )
                                        conn_db.commit()
                                        conn_db.close()
                                    log_admin_audit(user.sso, user.name, user.role, "USER_MODIFIED", f"Modification de l'utilisateur {u['sso']} (Nom: {edit_name}, Rôle: {edit_role}, LOBs: {edit_lobs_str})")
                                    st.session_state["user_success_message"] = f"Profil de {u['name']} mis à jour avec succès."
                                    st.session_state.pop("editing_user_sso", None)
                                    st.rerun()
                            elif cancel_edit:
                                st.session_state.pop("editing_user_sso", None)
                                st.rerun()
                    else:
                        col1, col2, col3, col4 = st.columns([5, 2.3, 2.3, 2.4])
                        with col1:
                            st.markdown(f"👤 **{u['name']}** (`{u['sso']}`)")
                            st.caption(f"Rôle : **{u['role']}** · LOBs : `{u['assigned_lobs']}`")
                            status_color = "#059669" if u["statut"] == "ACTIF" else "#DC2626"
                            st.markdown(f"Statut : <span style='color:{status_color};font-weight:700;'>{u['statut']}</span>", unsafe_allow_html=True)
                        with col2:
                            if st.button("✏️ Modifier", key=f"edit_usr_btn_{u['sso']}", use_container_width=True):
                                st.session_state["editing_user_sso"] = u["sso"]
                                st.rerun()
                        with col3:
                            btn_label = "🔒 Suspendre" if u["statut"] == "ACTIF" else "🔓 Réactiver"
                            new_statut = "INACTIF" if u["statut"] == "ACTIF" else "ACTIF"
                            if st.button(btn_label, key=f"toggle_stat_{u['sso']}", use_container_width=True):
                                for db_path in ["data/actuarecette.db", "data/actuarecette_v2.db"]:
                                    _initialize_users_table_if_needed(db_path)
                                    conn_db = sqlite_connection(db_path)
                                    conn_db.execute(
                                        "UPDATE utilisateurs SET statut = ? WHERE sso = ?",
                                        (new_statut, u["sso"])
                                    )
                                    conn_db.commit()
                                    conn_db.close()
                                log_admin_audit(user.sso, user.name, user.role, "USER_STATUS_UPDATED", f"Statut de l'utilisateur {u['sso']} changé en {new_statut}")
                                st.session_state["user_success_message"] = f"Statut de {u['name']} mis à jour en {new_statut}."
                                st.rerun()
                        with col4:
                            if st.button("🗑️ Supprimer", key=f"delete_user_{u['sso']}", type="secondary", use_container_width=True):
                                for db_path in ["data/actuarecette.db", "data/actuarecette_v2.db"]:
                                    _initialize_users_table_if_needed(db_path)
                                    conn_db = sqlite_connection(db_path)
                                    conn_db.execute(
                                        "DELETE FROM utilisateurs WHERE sso = ?",
                                        (u["sso"],)
                                    )
                                    conn_db.commit()
                                    conn_db.close()
                                log_admin_audit(user.sso, user.name, user.role, "USER_DELETED", f"Suppression de l'utilisateur {u['sso']}")
                                st.session_state["user_success_message"] = f"Utilisateur {u['name']} supprimé définitivement."
                                st.rerun()

    # ---------------------------------------------------------------------------
    # Onglet 5 : Gestion des Périodes d'arrêté
    # ---------------------------------------------------------------------------
    with tab5:
        st.markdown("### 📅 Gestion des Périodes d'arrêté (SSO/IAM)")
        if user.role != "Responsable MOA":
            st.warning("🔒 Accès restreint. Seuls les utilisateurs avec le rôle **Responsable MOA** peuvent gérer les périodes d'arrêté.")
        else:
            # 1. Liste des périodes existantes
            st.markdown("#### Périodes d'arrêté configurées")
            periods_list = list_all_periods()
            if periods_list:
                df_periods = pd.DataFrame(periods_list)
                st.dataframe(
                    df_periods.rename(columns={
                        "code_periode": "Code Période",
                        "libelle": "Libellé de la période",
                        "statut": "Statut",
                        "cree_par": "Créé Par",
                        "date_creation": "Date de Création"
                    }),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("Aucune période d'arrêté configurée dans la base.")

            st.markdown("---")

            # 2. Formulaire d'ajout de nouvelle période
            st.markdown("#### ➕ Ajouter une nouvelle période d'arrêté")
            with st.form("new_period_form", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    new_code = st.text_input("Code unique de la période (ex: 2026-T3, 2026-M06)", placeholder="AAAA-TX ou AAAA-MXX").strip()
                with col2:
                    new_label = st.text_input("Libellé descriptif (ex: 3ème Trimestre 2026)", placeholder="Libellé complet").strip()
                
                submitted_period = st.form_submit_button("Ajouter la Période", type="primary", use_container_width=True)
                if submitted_period:
                    if not new_code or not new_label:
                        st.error("Veuillez remplir le code et le libellé.")
                    else:
                        success = add_period_to_db(new_code, new_label, user.sso)
                        if success:
                            log_admin_audit(user.sso, user.name, user.role, "PERIOD_CREATED", f"Création de la période d'arrêté {new_code} ({new_label})")
                            st.session_state["user_success_message"] = f"La période {new_code} a été ajoutée avec succès."
                            st.rerun()
                        else:
                            st.error("Une erreur s'est produite lors de l'ajout de la période.")

            st.markdown("---")

            # 3. Actions rapides sur les périodes
            st.markdown("#### ⚙️ Gérer les actions rapides")
            for p in periods_list:
                with st.container(border=True):
                    col1, col2, col3 = st.columns([6, 3, 3])
                    with col1:
                        st.markdown(f"📅 **{p['libelle']}** (`{p['code_periode']}`)")
                        status_color = "#059669" if p["statut"] == "OUVERT" else "#DC2626"
                        st.markdown(f"Statut : <span style='color:{status_color};font-weight:700;'>{p['statut']}</span>", unsafe_allow_html=True)
                    with col2:
                        btn_lbl = "🔒 Verrouiller" if p["statut"] == "OUVERT" else "🔓 Ouvrir"
                        new_st = "VERROUILLÉ" if p["statut"] == "OUVERT" else "OUVERT"
                        if st.button(btn_lbl, key=f"toggle_period_{p['code_periode']}", use_container_width=True):
                            update_period_status_in_db(p['code_periode'], new_st)
                            log_admin_audit(user.sso, user.name, user.role, "PERIOD_STATUS_UPDATED", f"Statut de la période {p['code_periode']} changé en {new_st}")
                            st.session_state["user_success_message"] = f"Statut de la période {p['code_periode']} mis à jour."
                            st.rerun()
                    with col3:
                        if st.button("🗑️ Supprimer", key=f"delete_period_{p['code_periode']}", type="secondary", use_container_width=True):
                            delete_period_from_db(p['code_periode'])
                            log_admin_audit(user.sso, user.name, user.role, "PERIOD_DELETED", f"Suppression de la période {p['code_periode']}")
                            st.session_state["user_success_message"] = f"Période {p['code_periode']} supprimée."
                            st.rerun()

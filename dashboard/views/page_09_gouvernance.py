# page_09_gouvernance.py — Page Gouvernance ACPR
# Vague 4 — Cadre de gouvernance des données actuarielles
"""
Page de gouvernance regroupant les 5 piliers exigés par le cadre
Solvabilité II (Art. 82) pour la certification ACPR :
1. Politique des données
2. Politique de matérialité
3. Cartographie des rôles
4. Registre des règles de contrôle
5. Cycle de révision
"""
import os
import json
import datetime
import streamlit as st


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------

def _load_json(path: str, default=None):
    """Charge un fichier JSON avec fallback."""
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return default if default is not None else {}


def _save_json(path: str, data):
    """Sauvegarde un fichier JSON."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _load_materiality_policy():
    """Charge la politique de matérialité en fusionnant les seuils SQLite avec les justifications JSON."""
    from dashboard.utils.engine_proxy import sqlite_connection
    # 1. Charger les métadonnées historiques du JSON (versioning, fréquence de révision, historique)
    json_data = _load_json("data/materiality_policy.json", {})
    json_lobs = {lob["lob_id"]: lob for lob in json_data.get("lobs", [])}
    
    db_path = "data/actuarecette.db"
    if not os.path.exists(db_path):
        return json_data
        
    try:
        with sqlite_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT id_portefeuille, libelle, seuil_materialite_pct, 
                          warning_pct, critical_pct, materiality_threshold_eur 
                   FROM portefeuilles 
                   ORDER BY id_portefeuille"""
            )
            db_rows = cursor.fetchall()
        
        import streamlit as st
        user_data = st.session_state.get("user")
        visible_lobs = []
        if user_data:
            from dashboard.utils.auth import find_user_by_sso
            user = find_user_by_sso(user_data.get("sso", ""))
            if user:
                visible_lobs = user.visible_lobs
            else:
                visible_lobs = user_data.get("assigned_lobs", [])
        db_rows = [row for row in db_rows if row["id_portefeuille"] in visible_lobs]
        
        merged_lobs = []
        for row in db_rows:
            lob_id = row["id_portefeuille"]
            libelle = row["libelle"]
            
            # Récupérer les informations existantes du JSON pour cette LOB
            json_lob = json_lobs.get(lob_id, {})
            
            # Fusionner les valeurs de la base de données (source de vérité) avec les métadonnées textuelles du JSON
            merged_lobs.append({
                "lob_id": lob_id,
                "lob_label": libelle,
                "tolerance_pct": float(row["seuil_materialite_pct"]),
                "warning_pct": float(row["warning_pct"]) if row["warning_pct"] is not None else 1.5,
                "critical_pct": float(row["critical_pct"]) if row["critical_pct"] is not None else 3.0,
                "materiality_threshold_eur": float(row["materiality_threshold_eur"]) if row["materiality_threshold_eur"] is not None else 1000.0,
                "justification": json_lob.get("justification", "Seuil défini lors de la création du portefeuille dans la console d'administration."),
                "approved_by": json_lob.get("approved_by", "Responsable Actuariat"),
                "approved_at": json_lob.get("approved_at", datetime.date.today().strftime("%Y-%m-%d"))
            })
            
        json_data["lobs"] = merged_lobs
        return json_data
    except Exception as e:
        # Fallback en cas d'erreur de base de données
        return json_data


def _load_control_rules():
    """Charge les règles de contrôle en temps réel depuis SQLite."""
    from dashboard.utils.engine_proxy import sqlite_connection
    db_path = "data/actuarecette.db"
    if not os.path.exists(db_path):
        return _load_json("data/control_rules.json", [])
    try:
        with sqlite_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM regles_recette_dynamiques ORDER BY date_creation DESC")
            rows = cursor.fetchall()
        
        import streamlit as st
        user_data = st.session_state.get("user")
        visible_lobs = []
        if user_data:
            from dashboard.utils.auth import find_user_by_sso
            user = find_user_by_sso(user_data.get("sso", ""))
            if user:
                visible_lobs = user.visible_lobs
            else:
                visible_lobs = user_data.get("assigned_lobs", [])
        rows = [row for row in rows if row["id_portefeuille"] in visible_lobs]
        
        rules = []
        for row in rows:
            r = dict(row)
            rule_id = r['id_regle']
            libelle = r['libelle']
            col_cible = r['colonne_cible'] or ""
            cond = r['condition_application'] or ""
            sev = r['severite'] or "ALERTE"
            
            # Domain mapping
            domain = "Transverse"
            col_upper = col_cible.upper()
            lib_upper = libelle.upper()
            cond_upper = cond.upper()
            if "INTÉGRITÉ" in lib_upper or "INTEGRITE" in lib_upper or "SOURCE" in lib_upper or rule_id.endswith("-005") or rule_id.endswith("_005") or rule_id.endswith("005"):
                domain = "Transverse"
            elif "PRIME" in col_upper or "COTISATION" in col_upper or "PROVISIONS" in col_upper or "SINISTRE" in col_upper:
                if "CONDUCTEUR" in cond_upper or "VEHICULE" in cond_upper or "AGE" in cond_upper:
                    domain = "Contrat"
                else:
                    domain = "Prime"
            elif "CONTRAT" in col_upper or "CLIENT" in col_upper or "POLICE" in col_upper:
                domain = "Contrat"
            else:
                domain = "Contrat"
            
            # Formulate dynamic description
            desc = f"Règle de contrôle pour la colonne '{col_cible}' de la LOB '{r['id_portefeuille']}'."
            if r['formule_theorique']:
                desc += f" Formule attendue : {r['formule_theorique']}."
            if cond:
                desc += f" Applicable sous condition : {cond}."
            if r['tolerance_unitaire'] is not None:
                desc += f" Tolérance : {r['tolerance_unitaire']} €."
                
            rules.append({
                "rule_id": rule_id,
                "label": libelle,
                "severity": sev,
                "domain": domain,
                "category": "Règle dynamique" if not rule_id.endswith("-001") else "Réconciliation",
                "description": desc,
                "regulatory_ref": "Art. 82 Directive 2009/138/CE (Solvabilité II)",
                "is_mandatory": sev == "BLOQUANT",
                "status": r['statut'],
                "version": r['version_regle'],
                "approved_by": r['valide_par_sso'] or "—",
                "approved_at": r['date_validation'] or "—"
            })
        return rules
    except Exception as e:
        return _load_json("data/control_rules.json", [])


def _load_governance_review():
    return _load_json("data/governance_review.json", {})


def _save_governance_review(data):
    _save_json("data/governance_review.json", data)


def _load_users():
    """Charge les utilisateurs depuis le registre auth."""
    try:
        from dashboard.utils.auth import list_all_users
        return list_all_users()
    except ImportError:
        return []


# ---------------------------------------------------------------------------
# Section renderers
# ---------------------------------------------------------------------------

def _section_header(icon: str, title: str, subtitle: str):
    """Render a consistent section header."""
    st.html(
        f'<div style="font-size:0.72rem;font-weight:700;color:var(--ar-text-muted);'
        f'text-transform:uppercase;letter-spacing:0.06em;margin-bottom:12px;">'
        f'{icon} {title}</div>'
    )
    if subtitle:
        st.caption(subtitle)


# ── Section 1 : Politique des données (Art. 82) ──

def _render_data_policy():
    """Section 1 : Politique des données Solvabilité II."""
    with st.container(border=True):
        _section_header("📜", "Politique des données (Art. 82 Solvabilité II)",
                         "Cadre de gouvernance des données utilisées pour le calcul des provisions techniques.")

        st.markdown("""
**Périmètre des données couvertes par ActuaRecette :**
- Données actuarielles de référence MOA (primes, sinistres, réserves, contrats)
- Données de production calculées par le SI DSI
- Métadonnées de provenance (système source, date extraction, référence)
- Résultats de réconciliation et anomalies
        """)

        st.markdown("---")
        st.markdown("**Sources de données — Référentiel des systèmes**")

        sources = [
            ["MOA / Actuariat", "Fichier CSV de référence actuarielle", "Upload manuel par le Maker", "SHA-256 à l'import"],
            ["DSI / Production", "Fichier CSV d'extraction système", "Upload manuel + déclaration provenance", "SHA-256 + accusé DSI"],
            ["Règles de contrôle", "Fichier JSON versionné", "Configuration par Responsable MOA", "Versioning + audit trail"],
        ]

        # Afficher sous forme de tableau
        col_h = st.columns([2, 3, 3, 2])
        headers = ["Source", "Nature", "Mode d'acquisition", "Contrôle intégrité"]
        for i, h in enumerate(headers):
            col_h[i].markdown(f"**{h}**")

        for row in sources:
            cols = st.columns([2, 3, 3, 2])
            for i, val in enumerate(row):
                cols[i].markdown(val)

        st.markdown("---")
        st.markdown("**Critères de qualité attendus :**")
        st.markdown("""
- **Complétude** : Aucun champ obligatoire manquant (NULL/NaN)
- **Cohérence** : Montants positifs, identifiants uniques, dates valides
- **Exactitude** : Écart ≤ seuil de matérialité défini par LOB
- **Traçabilité** : Chaque fichier dispose d'un fingerprint SHA-256 et d'une déclaration de provenance
        """)

        st.markdown("---")
        st.markdown("**Processus de correction des défauts :**")
        st.markdown("""
1. **Détection** : Anomalies identifiées automatiquement lors de la réconciliation
2. **Classification** : Sévérité BLOQUANT / ALERTE assignée par les règles
3. **Justification** : Maker documente la cause + action corrective
4. **Validation** : Checker vérifie la checklist, Approver valide si bloquant
5. **Correction** : DSI corrige et soumet un nouveau fichier (nouvelle campagne)
        """)

        # Date d'approbation
        mat_policy = _load_materiality_policy()
        if mat_policy.get("approved_by"):
            st.caption(f"Politique approuvée par : {mat_policy['approved_by']} — "
                       f"Dernière mise à jour : {mat_policy.get('last_updated', '—')}")


# ── Section 2 : Politique de matérialité ──

def _render_materiality_policy():
    """Section 2 : Seuils de matérialité par LOB."""
    mat_data = _load_materiality_policy()
    with st.container(border=True):
        _section_header("📏", "Politique de matérialité",
                         "Seuils d'écart acceptables par ligne de métier (LOB) pour la réconciliation.")

        lobs = mat_data.get("lobs", [])
        if lobs:
            # En-têtes
            col_h = st.columns([2, 1.2, 1.2, 1.2, 1.2, 3.2])
            col_h[0].markdown("**LOB**")
            col_h[1].markdown("**Tolérance**")
            col_h[2].markdown("**Alerte ≥**")
            col_h[3].markdown("**Bloquant ≥**")
            col_h[4].markdown("**Seuil (€)**")
            col_h[5].markdown("**Justification**")

            for lob in lobs:
                cols = st.columns([2, 1.2, 1.2, 1.2, 1.2, 3.2])
                cols[0].markdown(f"`{lob['lob_id']}`\n\n{lob.get('lob_label', '')}")
                cols[1].markdown(f"**{lob['tolerance_pct']}%**")
                cols[2].markdown(f"🟡 {lob.get('warning_pct', '—')}%")
                cols[3].markdown(f"🔴 {lob.get('critical_pct', '—')}%")
                cols[4].markdown(f"{lob['materiality_threshold_eur']:,.0f} €")
                cols[5].markdown(lob.get("justification", "—"))
                approved = lob.get("approved_by", "")
                if approved:
                    cols[5].caption(f"Approuvé par {approved} le {lob.get('approved_at', '—')}")

            st.markdown("---")
            st.markdown("**Classification automatique des écarts :**")
            st.markdown("""
- Écart < seuil **Alerte** → ✅ **Information** (conforme)
- Seuil **Alerte** ≤ écart < seuil **Bloquant** → 🟡 **Alerte** (à surveiller)
- Écart ≥ seuil **Bloquant** → 🔴 **Bloquant** (justification obligatoire)
            """)
        else:
            st.info("Aucun seuil de matérialité défini. Configurez les portefeuilles dans l'onglet d'administration.")

        st.markdown("---")
        st.markdown("**Processus de révision :**")
        freq = mat_data.get("revision_frequency", "Annuelle")
        st.markdown(f"- Fréquence de révision : **{freq}** (minimum)")
        st.markdown("- Toute modification de seuil nécessite l'approbation du Responsable MOA")
        st.markdown("- L'historique des versions est conservé ci-dessous")

        # Historique des versions
        versions = mat_data.get("version_history", [])
        if versions:
            with st.expander(f"📋 Historique des versions ({len(versions)})"):
                for v in versions:
                    st.markdown(f"**v{v['version']}** — {v['date']} par {v['author']}")
                    st.caption(v.get("changes", ""))


# ── Section 3 : Cartographie des rôles ──

def _render_roles_map():
    """Section 3 : Cartographie des rôles et matrice de séparation."""
    with st.container(border=True):
        _section_header("👥", "Cartographie des rôles et habilitations",
                         "Matrice de séparation des tâches conforme Solvabilité II.")

        # Tableau des rôles et droits
        st.markdown("**Rôles et droits d'accès**")

        roles_data = [
            {
                "role": "Actuaire MOA (Maker)",
                "droits": "Créer des campagnes, importer des fichiers, configurer le mapping, soumettre pour validation",
                "restrictions": "Ne peut pas certifier ses propres campagnes. Accès limité aux LOBs assignés."
            },
            {
                "role": "Validateur (Checker)",
                "droits": "Certifier/rejeter les campagnes, compléter la checklist, commenter les écarts",
                "restrictions": "Ne peut pas certifier une campagne où il est Maker. Accès à toutes les LOBs."
            },
            {
                "role": "Responsable MOA (Approver)",
                "droits": "Approuver les campagnes avec anomalies bloquantes, gérer les règles, administrer les paramètres",
                "restrictions": "Ne peut pas approuver une campagne où il est Maker ou Checker."
            },
        ]

        col_h = st.columns([2.5, 4, 3.5])
        col_h[0].markdown("**Rôle**")
        col_h[1].markdown("**Droits**")
        col_h[2].markdown("**Restrictions**")

        for rd in roles_data:
            cols = st.columns([2.5, 4, 3.5])
            cols[0].markdown(f"**{rd['role']}**")
            cols[1].markdown(rd["droits"])
            cols[2].markdown(rd["restrictions"])

        st.markdown("---")

        # Matrice de séparation des tâches
        st.markdown("**Matrice de séparation des tâches (Maker ≠ Checker ≠ Approver)**")
        sep_matrix = [
            ["", "**Créer une campagne**", "**Certifier**", "**Approuver**"],
            ["**Maker de la campagne**", "✅", "❌", "❌"],
            ["**Checker de la campagne**", "—", "✅", "❌"],
            ["**Approver**", "—", "—", "✅"],
        ]
        for row in sep_matrix:
            cols = st.columns(4)
            for i, val in enumerate(row):
                cols[i].markdown(val)

        st.markdown("---")

        # Utilisateurs actuels
        st.markdown("**Utilisateurs assignés**")
        users = _load_users()
        if users:
            for u in users:
                lobs_str = ", ".join(u.assigned_lobs) if u.assigned_lobs else "Toutes"
                st.markdown(f"- **{u.name}** (`{u.sso}`) — {u.role} — LOBs : {lobs_str}")
        else:
            st.caption("Registre utilisateurs non disponible.")


# ── Section 4 : Registre des règles de contrôle ──

def _render_rules_registry():
    """Section 4 : Registre complet des règles avec filtrage."""
    rules = _load_control_rules()
    with st.container(border=True):
        _section_header("📖", "Registre des règles de contrôle",
                         "Catalogue versionné des règles appliquées lors des campagnes de réconciliation.")

        if not rules:
            st.info("Aucune règle de contrôle définie. Configurez-les dans l'onglet d'administration.")
            return

        # Filtres
        all_statuses = sorted(set(r.get("status", "ACTIVE") for r in rules))
        all_severities = sorted(set(r.get("severity", "") for r in rules))
        all_domains = sorted(set(r.get("domain", "—") for r in rules))

        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            filter_status = st.multiselect(
                "Filtrer par statut", all_statuses,
                default=all_statuses, key="gov_rules_status"
            )
        with col_f2:
            filter_sev = st.multiselect(
                "Filtrer par sévérité", all_severities,
                default=all_severities, key="gov_rules_severity"
            )
        with col_f3:
            filter_domain = st.multiselect(
                "Filtrer par domaine", all_domains,
                default=all_domains, key="gov_rules_domain"
            )

        filtered = [r for r in rules
                     if r.get("status", "ACTIVE") in filter_status
                     and r.get("severity", "") in filter_sev
                     and r.get("domain", "—") in filter_domain]

        st.caption(f"{len(filtered)} règle(s) affichée(s) sur {len(rules)}")

        # Tableau des règles
        for rule in filtered:
            sev = rule.get("severity", "")
            sev_icon = "🔴" if sev == "BLOQUANT" else "🟡"
            status = rule.get("status", "ACTIVE")
            domain = rule.get("domain", "")
            mandatory = " — **Obligatoire**" if rule.get("is_mandatory") else ""
            domain_tag = f" · {domain}" if domain else ""

            with st.expander(f"{sev_icon} {rule['rule_id']} — {rule.get('label', '')} [{status}]{mandatory}{domain_tag}"):
                st.markdown(f"**Domaine métier :** {domain or '—'}")
                st.markdown(f"**Description :** {rule.get('description', '—')}")
                st.markdown(f"**Catégorie :** {rule.get('category', '—')}")
                st.markdown(f"**Sévérité :** {sev}")
                st.markdown(f"**Référence réglementaire :** {rule.get('regulatory_ref', '—')}")
                st.markdown(f"**Version :** {rule.get('version', '1.0')}")
                st.markdown(f"**Statut :** {status}")
                if rule.get("approved_by"):
                    st.caption(f"Approuvée par {rule['approved_by']} le {rule.get('approved_at', '—')}")


# ── Section 5 : Cycle de révision ──

def _render_review_cycle():
    """Section 5 : Cycle de révision et traçabilité."""
    review_data = _load_governance_review()
    user_data = st.session_state.get("user", {})
    user_role = user_data.get("role", "")
    user_name = user_data.get("name", "")

    with st.container(border=True):
        _section_header("🔄", "Cycle de révision",
                         "Suivi des revues de gouvernance conformément aux exigences ACPR.")

        # Dernière revue
        last = review_data.get("last_review", {})
        if last:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Dernière revue**")
                st.markdown(f"- Date : **{last.get('date', '—')}**")
                st.markdown(f"- Responsable : {last.get('reviewer', '—')} ({last.get('role', '—')})")
            with col2:
                st.markdown("**Prochaine revue**")
                next_rev = review_data.get("next_review", {})
                st.markdown(f"- Date programmée : **{next_rev.get('scheduled_date', '—')}**")
                st.markdown(f"- Responsable : {next_rev.get('responsible', '—')}")
                st.markdown(f"- Périmètre : {next_rev.get('scope', '—')}")

            if last.get("comments"):
                st.info(f"**Commentaires :** {last['comments']}")
        else:
            st.warning("Aucune revue de gouvernance enregistrée.")

        # Historique
        history = review_data.get("review_history", [])
        if history:
            with st.expander(f"📋 Historique des revues ({len(history)})"):
                for entry in history:
                    outcome_icon = "✅" if entry.get("outcome") == "Conforme" else "⚠️"
                    st.markdown(f"{outcome_icon} **{entry.get('date', '')}** — {entry.get('type', '')} "
                                f"par {entry.get('reviewer', '')} — {entry.get('outcome', '')}")
                    if entry.get("comments"):
                        st.caption(entry["comments"])

        # Action : Enregistrer une nouvelle revue (Responsable MOA uniquement)
        if user_role == "Responsable MOA":
            st.markdown("---")
            st.markdown("**📝 Enregistrer une nouvelle revue**")
            with st.form("governance_review_form"):
                review_type = st.selectbox("Type de revue", [
                    "Revue annuelle", "Revue semestrielle", "Revue exceptionnelle", "Audit interne"
                ], key="gov_review_type")
                review_outcome = st.selectbox("Résultat", [
                    "Conforme", "Conforme avec réserves", "Non conforme"
                ], key="gov_review_outcome")
                review_comments = st.text_area("Commentaires", key="gov_review_comments",
                                                placeholder="Résumé des constats de la revue...")
                next_date = st.date_input("Prochaine revue programmée", key="gov_next_date",
                                           value=datetime.date.today() + datetime.timedelta(days=365))

                submitted = st.form_submit_button("Enregistrer la revue", type="primary")
                if submitted:
                    now_str = datetime.datetime.now().strftime("%Y-%m-%d")
                    # Mettre à jour les données
                    review_data["last_review"] = {
                        "date": now_str,
                        "reviewer": user_name,
                        "role": user_role,
                        "comments": review_comments,
                    }
                    review_data["next_review"] = {
                        "scheduled_date": next_date.isoformat(),
                        "responsible": user_name,
                        "scope": "Revue complète : politique des données, seuils de matérialité, "
                                 "cartographie des rôles, registre des règles",
                    }
                    # Ajouter à l'historique
                    if "review_history" not in review_data:
                        review_data["review_history"] = []
                    review_data["review_history"].insert(0, {
                        "date": now_str,
                        "reviewer": user_name,
                        "type": review_type,
                        "outcome": review_outcome,
                        "comments": review_comments,
                    })
                    _save_governance_review(review_data)
                    st.success("✔ Revue enregistrée avec succès.")
                    st.rerun()


# ---------------------------------------------------------------------------
# MAIN ENTRY POINT
# ---------------------------------------------------------------------------

def render_gouvernance_page():
    """Page 9 : Gouvernance ACPR — Cadre de gouvernance des données actuarielles."""
    # Defense-in-depth: vérifier l'authentification au niveau page
    from dashboard.views.page_00_login import require_auth
    if require_auth() is None:
        st.stop()
        return

    from dashboard.components.breadcrumb import breadcrumb
    breadcrumb(["Gouvernance", "Gouvernance ACPR"])

    st.html(
        '<div style="font-size:1.4rem;font-weight:800;color:var(--ar-text-primary);'
        'margin-bottom:4px;">🏛 Gouvernance ACPR</div>'
        '<div style="font-size:0.78rem;color:var(--ar-text-muted);margin-bottom:24px;">'
        'Cadre de gouvernance des données actuarielles — Solvabilité II (Art. 82)</div>'
    )

    # Tabs pour les 5 sections
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📜 Politique des données",
        "📏 Matérialité",
        "👥 Rôles",
        "📖 Règles de contrôle",
        "🔄 Cycle de révision",
    ], key="gouvernance_tabs")

    with tab1:
        _render_data_policy()

    with tab2:
        _render_materiality_policy()

    with tab3:
        _render_roles_map()

    with tab4:
        _render_rules_registry()

    with tab5:
        _render_review_cycle()

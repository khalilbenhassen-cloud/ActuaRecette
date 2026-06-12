-- schema.sql - ActuaRecette Relational Schema v6.0.0
-- Moteur de Persistance SQLite (WAL) pour le SI Actuariat & UAT
-- Migration v5 → v6 : DuckDB → SQLite, ajout audit_entries, active_sessions

-- =============================================================================
-- 1. Tables métier existantes (inchangées)
-- =============================================================================

-- 1a. Table Portefeuille (L'axe LOB / Produit Métier)
CREATE TABLE IF NOT EXISTS portefeuilles (
    id_portefeuille VARCHAR PRIMARY KEY,
    code_metier VARCHAR NOT NULL,
    libelle VARCHAR NOT NULL,
    type_risque VARCHAR NOT NULL,
    seuil_materialite_pct DOUBLE DEFAULT 0.2, -- DEPRECATED: use portefeuilles_seuils_domaines
    warning_pct DOUBLE DEFAULT 3.0, -- DEPRECATED: use portefeuilles_seuils_domaines
    critical_pct DOUBLE DEFAULT 5.0, -- DEPRECATED: use portefeuilles_seuils_domaines
    materiality_threshold_eur DOUBLE DEFAULT 500.0, -- DEPRECATED: use portefeuilles_seuils_domaines
    statut VARCHAR DEFAULT 'ACTIF',
    cree_par_sso VARCHAR DEFAULT 'systeme',
    valide_par_sso VARCHAR DEFAULT 'systeme',
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date_validation TIMESTAMP,
    draft_seuil_materialite_pct DOUBLE, -- DEPRECATED: use portefeuilles_seuils_domaines
    draft_warning_pct DOUBLE, -- DEPRECATED: use portefeuilles_seuils_domaines
    draft_critical_pct DOUBLE, -- DEPRECATED: use portefeuilles_seuils_domaines
    draft_materiality_threshold_eur DOUBLE, -- DEPRECATED: use portefeuilles_seuils_domaines
    draft_libelle VARCHAR,
    draft_type_risque VARCHAR
);

-- Table des Seuils par Domaine (Maker-Checker - Solvabilité II)
CREATE TABLE IF NOT EXISTS portefeuilles_seuils_domaines (
    id_portefeuille VARCHAR NOT NULL REFERENCES portefeuilles(id_portefeuille),
    domaine VARCHAR NOT NULL,                -- Prime, Sinistre, Réserve, Contrat, Réassurance
    seuil_materialite_pct DOUBLE DEFAULT 0.2,
    warning_pct DOUBLE DEFAULT 3.0,
    critical_pct DOUBLE DEFAULT 5.0,
    materiality_threshold_eur DOUBLE DEFAULT 500.0,
    statut VARCHAR DEFAULT 'ACTIF',
    cree_par_sso VARCHAR DEFAULT 'systeme',
    valide_par_sso VARCHAR DEFAULT 'systeme',
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date_validation TIMESTAMP,
    draft_seuil_materialite_pct DOUBLE,
    draft_warning_pct DOUBLE,
    draft_critical_pct DOUBLE,
    draft_materiality_threshold_eur DOUBLE,
    PRIMARY KEY (id_portefeuille, domaine)
);

-- 1b. Table Regles_Recette (Historique / Statique)
CREATE TABLE IF NOT EXISTS regles_recette (
    id_regle VARCHAR PRIMARY KEY,
    id_portefeuille VARCHAR REFERENCES portefeuilles(id_portefeuille),
    version_regle VARCHAR NOT NULL,
    titre VARCHAR NOT NULL,
    formule_theorique VARCHAR NOT NULL,
    tolerance_unitaire DOUBLE DEFAULT 0.05,
    statut VARCHAR DEFAULT 'ACTIF'
);

-- Table des Règles de Recette Dynamiques (Solvabilité II - Phase 2c)
CREATE TABLE IF NOT EXISTS regles_recette_dynamiques (
    id_regle VARCHAR NOT NULL,
    id_portefeuille VARCHAR REFERENCES portefeuilles(id_portefeuille),
    version_regle VARCHAR NOT NULL,          -- ex: "1.0", "1.1"
    libelle VARCHAR NOT NULL,
    colonne_cible VARCHAR NOT NULL,          -- ex: "age_conducteur"
    operateur_logique VARCHAR NOT NULL,      -- ex: "<", ">", "==", "between"
    valeur_seuil VARCHAR NOT NULL,           -- ex: "25", "150"
    formule_theorique VARCHAR NOT NULL,      -- ex: "250.0 * bonus_malus * 1.5"
    tolerance_unitaire DOUBLE DEFAULT 0.05,
    statut VARCHAR DEFAULT 'BROUILLON',      -- BROUILLON, EN_ATTENTE, ACTIF, OBSOLÈTE
    severite VARCHAR DEFAULT 'ALERTE',       -- ALERTE, BLOQUANT
    condition_application VARCHAR,           -- ex: "age_conducteur < 25"
    cree_par_sso VARCHAR NOT NULL,
    valide_par_sso VARCHAR,
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date_validation TIMESTAMP,
    domaine VARCHAR DEFAULT 'Prime',
    PRIMARY KEY (id_regle, version_regle)
);

-- 1c. Table Campagnes_Recette (L'axe Temporel / Clôture)
CREATE TABLE IF NOT EXISTS campagnes_recette (
    id_campagne VARCHAR PRIMARY KEY,
    id_portefeuille VARCHAR REFERENCES portefeuilles(id_portefeuille),
    periode VARCHAR NOT NULL,                -- ex: '2026-05' (Période de clôture)
    type_testing VARCHAR DEFAULT 'CLOTURE',  -- CLOTURE, STRESS_TEST, BATCH_HEBDO
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 1d. Table Runs_Execution (L'axe Correctif & Piste d'Audit réglementaire)
CREATE TABLE IF NOT EXISTS runs_execution (
    id_run VARCHAR PRIMARY KEY,
    id_campagne VARCHAR REFERENCES campagnes_recette(id_campagne),
    num_run INTEGER NOT NULL,
    version_moteur_dsi VARCHAR NOT NULL,
    date_execution TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    taux_alignement DOUBLE NOT NULL,
    prime_a_risque DOUBLE NOT NULL,
    statut_validation VARCHAR NOT NULL,      -- BROUILLON, CALCULÉ, SOUMIS, REJETÉ, CERTIFIÉ (cf. R6)
    maker_sso_user VARCHAR NOT NULL,         -- Actuaire (Maker)
    checker_sso_user VARCHAR,                -- Validateur (Checker)
    signature_hash VARCHAR,                  -- Signature SHA-256 de non-répudiation
    created_by_sso VARCHAR,                  -- SSO de l'utilisateur ayant créé le run (v6.0)
    rapport_dq TEXT,                         -- Rapport Data Quality archivé en JSON (Phase 2c)
    nb_patterns_detectes INTEGER DEFAULT 0,           -- Nombre de patterns root cause détectés (Phase 2d)
    coefficient_principal_fautif VARCHAR,              -- Coefficient le plus impactant (Phase 2d)
    root_cause_disponible BOOLEAN DEFAULT 0,            -- Root cause calculée ? (Phase 2d)
    version_ruleset VARCHAR DEFAULT '1.0'               -- Référence de version de ruleset pour reproductibilité
);

-- =============================================================================
-- 2. Nouvelles tables multi-utilisateur (v6.0 — Phase 1)
-- =============================================================================

-- 2a. Table d'audit centralisée (remplace audit_log.json)
-- Chaque action est horodatée, signée, et irréversible (append-only).
CREATE TABLE IF NOT EXISTS audit_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_sso VARCHAR NOT NULL,
    user_name VARCHAR NOT NULL,
    user_role VARCHAR NOT NULL,              -- Actuaire MOA, Validateur, Responsable MOA
    run_id VARCHAR,                          -- Nullable : certaines actions ne concernent pas un run
    id_portefeuille VARCHAR,                 -- LOB concerné
    action VARCHAR NOT NULL,                 -- CREATED, CALCULATED, SUBMITTED, APPROVED, REJECTED, DELETED
    comment TEXT,
    signature_hash VARCHAR
);

-- 2b. Table des sessions actives (présence multi-utilisateur en temps réel)
-- Nettoyée automatiquement : les sessions sans heartbeat > 2 min sont supprimées.
CREATE TABLE IF NOT EXISTS active_sessions (
    session_id VARCHAR PRIMARY KEY,
    user_sso VARCHAR NOT NULL,
    user_name VARCHAR NOT NULL,
    user_role VARCHAR NOT NULL,
    current_lob VARCHAR,                     -- LOB sur lequel l'actuaire travaille actuellement
    current_page VARCHAR,                    -- Page active (cockpit, espace_travail, etc.)
    last_heartbeat TIMESTAMP NOT NULL,
    connected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2c. Table des utilisateurs (Phase 1/2 — Gestion dynamique des profils)
CREATE TABLE IF NOT EXISTS utilisateurs (
    sso VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    role VARCHAR NOT NULL,               -- Actuaire MOA, Validateur, Responsable MOA
    assigned_lobs TEXT NOT NULL,         -- Liste de LOBs séparés par des virgules (ex: "LOB_AUTO_PART,LOB_INCENDIE_RD")
    statut VARCHAR NOT NULL DEFAULT 'ACTIF',  -- ACTIF, INACTIF
    cree_par VARCHAR,
    date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Seed data — Utilisateurs par défaut
INSERT OR IGNORE INTO utilisateurs (sso, name, role, assigned_lobs, statut, cree_par)
VALUES ('maker.junior', 'Actuaire junior (Maker)', 'Actuaire MOA', 'LOB_AUTO_PART', 'ACTIF', 'systeme');

INSERT OR IGNORE INTO utilisateurs (sso, name, role, assigned_lobs, statut, cree_par)
VALUES ('maker.senior', 'Actuaire senior', 'Actuaire MOA', 'LOB_INCENDIE_RD', 'ACTIF', 'systeme');

INSERT OR IGNORE INTO utilisateurs (sso, name, role, assigned_lobs, statut, cree_par)
VALUES ('checker', 'Validateur Technique (Checker)', 'Validateur', 'LOB_AUTO_PART,LOB_INCENDIE_RD,LOB_MRH_HAB', 'ACTIF', 'systeme');

INSERT OR IGNORE INTO utilisateurs (sso, name, role, assigned_lobs, statut, cree_par)
VALUES ('manager', 'Responsable Métier (Manager)', 'Responsable MOA', 'LOB_AUTO_PART,LOB_INCENDIE_RD,LOB_MRH_HAB', 'ACTIF', 'systeme');

-- =============================================================================
-- 3. Index pour les performances (v6.0)
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_runs_campagne ON runs_execution(id_campagne);
CREATE INDEX IF NOT EXISTS idx_runs_portefeuille ON runs_execution(id_campagne, statut_validation);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_entries(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_audit_run ON audit_entries(run_id);
CREATE INDEX IF NOT EXISTS idx_sessions_heartbeat ON active_sessions(last_heartbeat);

-- =============================================================================
-- 4. Données de référence (Portefeuilles IARD par défaut)
-- =============================================================================

INSERT OR IGNORE INTO portefeuilles (id_portefeuille, code_metier, libelle, type_risque, seuil_materialite_pct, warning_pct, critical_pct, materiality_threshold_eur) 
VALUES ('LOB_AUTO_PART', 'AUTO', 'Automobile Particuliers', 'IARD', 0.2, 3.0, 5.0, 500.0);

INSERT OR IGNORE INTO portefeuilles (id_portefeuille, code_metier, libelle, type_risque, seuil_materialite_pct, warning_pct, critical_pct, materiality_threshold_eur) 
VALUES ('LOB_INCENDIE_RD', 'INCENDIE', 'Incendie & Risques Divers', 'IARD', 0.5, 1.5, 3.0, 1000.0);

INSERT OR IGNORE INTO portefeuilles (id_portefeuille, code_metier, libelle, type_risque, seuil_materialite_pct, warning_pct, critical_pct, materiality_threshold_eur) 
VALUES ('LOB_MRH_HAB', 'MRH', 'Habitation (MRH)', 'IARD', 0.2, 3.0, 5.0, 500.0);

-- =============================================================================
-- 5. Référentiel d'anomalies (Phase 2b.4)
-- =============================================================================

-- 5a. Table des catégories d'anomalies actuarielles
-- Chaque catégorie a une sévérité (1=critique, 2=majeure, 3=mineure) et une action corrective type.
CREATE TABLE IF NOT EXISTS anomaly_categories (
    id_category VARCHAR PRIMARY KEY,
    libelle VARCHAR NOT NULL,
    description TEXT NOT NULL,
    severite INTEGER NOT NULL DEFAULT 2,        -- 1=CRITIQUE, 2=MAJEURE, 3=MINEURE
    action_corrective TEXT,                      -- Recommandation de correction pour la DSI
    pattern_detection TEXT,                       -- Expression de détection automatique (JSON)
    est_bloquant BOOLEAN DEFAULT 1,              -- Bloque la certification si TRUE
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5b. Seed data — Catégories d'anomalies connues
INSERT OR IGNORE INTO anomaly_categories (id_category, libelle, description, severite, action_corrective, est_bloquant)
VALUES (
    'ARRONDI_DECIMAL',
    'Bruit d''arrondi décimal',
    'Divergence d''arrondis mineure. L''écart est extrêmement faible et correspond à des écarts de précision lors du stockage des floats en base de données de production.',
    3,  -- MINEURE
    'Aligner la précision des calculs décimaux (DECIMAL(18,6) au lieu de FLOAT).',
    0   -- Non-bloquant
);

INSERT OR IGNORE INTO anomaly_categories (id_category, libelle, description, severite, action_corrective, est_bloquant)
VALUES (
    'SEUIL_PLANCHER',
    'Oubli de Seuil Minimal (Plancher)',
    'Le système de production de la DSI omet d''appliquer la règle réglementaire du seuil minimal de tarification fixé à 150.00 € par dossier.',
    1,  -- CRITIQUE
    'Implémenter la vérification MAX(prime_calculee, seuil_plancher) dans le moteur de tarification.',
    1   -- Bloquant
);

INSERT OR IGNORE INTO anomaly_categories (id_category, libelle, description, severite, action_corrective, est_bloquant)
VALUES (
    'FORMULE_JEUNE_CONDUCTEUR',
    'Erreur de Formule Jeune Conducteur',
    'Divergence sur le coefficient de surprime Jeune Conducteur (< 25 ans). La DSI applique un facteur de majoration erroné de 1.60 au lieu de 1.50.',
    1,  -- CRITIQUE
    'Corriger le coefficient JC dans la table de paramétrage : 1.50 au lieu de 1.60.',
    1   -- Bloquant
);

INSERT OR IGNORE INTO anomaly_categories (id_category, libelle, description, severite, action_corrective, est_bloquant)
VALUES (
    'COEFF_PUISSANCE',
    'Écart de Coefficient Puissance',
    'Divergence sur le facteur multiplicateur de puissance véhicule (> 150 ch). La DSI applique un coefficient de 1.50 au lieu de 1.30.',
    1,  -- CRITIQUE
    'Corriger le coefficient puissance dans la table de paramétrage : 1.30 au lieu de 1.50.',
    1   -- Bloquant
);

INSERT OR IGNORE INTO anomaly_categories (id_category, libelle, description, severite, action_corrective, est_bloquant)
VALUES (
    'ECART_NON_REPERTORIE',
    'Écart fonctionnel non répertorié',
    'Divergence non classifiée automatiquement. Requiert une investigation manuelle par l''actuaire.',
    2,  -- MAJEURE
    'Investiguer la formule métier concernée et ajouter une nouvelle règle de détection.',
    1   -- Bloquant
);

INSERT OR IGNORE INTO anomaly_categories (id_category, libelle, description, severite, action_corrective, est_bloquant)
VALUES (
    'DONNEE_CORROMPUE',
    'Donnée corrompue ou manquante',
    'Le dossier contient des valeurs NULL, NaN, négatives aberrantes ou des champs manquants qui empêchent le calcul actuariel.',
    1,  -- CRITIQUE
    'Valider l''intégrité des données en amont : contrôle NOT NULL, bornes acceptables, cohérence référentielle.',
    1   -- Bloquant
);

-- =============================================================================
-- 6. Cycle de vie des exercices (Phase 2b.4)
-- =============================================================================

-- 6a. Table des exercices comptables
-- Un exercice regroupe les campagnes d'une période. Il traverse le cycle :
--   OUVERT → CLOTURE → VERROUILLE
CREATE TABLE IF NOT EXISTS exercices (
    id_exercice VARCHAR PRIMARY KEY,
    annee INTEGER NOT NULL,
    mois INTEGER NOT NULL,                       -- 1-12
    libelle VARCHAR NOT NULL,                    -- ex: "Clôture Juin 2026"
    statut VARCHAR NOT NULL DEFAULT 'OUVERT',    -- OUVERT, CLOTURE, VERROUILLE
    date_ouverture TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date_cloture TIMESTAMP,
    date_verrouillage TIMESTAMP,
    cloture_par_sso VARCHAR,                     -- SSO du Manager qui clôture
    verrouille_par_sso VARCHAR,                  -- SSO du Manager qui verrouille
    commentaire TEXT
);

-- 6b. Index performance exercices
CREATE INDEX IF NOT EXISTS idx_exercices_annee_mois ON exercices(annee, mois);
CREATE INDEX IF NOT EXISTS idx_exercices_statut ON exercices(statut);
CREATE INDEX IF NOT EXISTS idx_anomaly_cat_severite ON anomaly_categories(severite);

-- =============================================================================
-- 7. Intelligence actuarielle (Phase 2d)
-- =============================================================================

-- 7a. Structure tarifaire — décomposition des coefficients par LOB
CREATE TABLE IF NOT EXISTS tarif_structure (
    id_portefeuille VARCHAR NOT NULL REFERENCES portefeuilles(id_portefeuille),
    nom_coefficient  VARCHAR NOT NULL,
    type_application VARCHAR NOT NULL DEFAULT 'MULTIPLICATIF',  -- MULTIPLICATIF ou ADDITIF
    ordre_application INTEGER NOT NULL,
    description      VARCHAR,
    PRIMARY KEY (id_portefeuille, nom_coefficient)
);

-- Seed data — Auto Particuliers
INSERT OR IGNORE INTO tarif_structure VALUES ('LOB_AUTO_PART', 'COEFF_AGE',       'MULTIPLICATIF', 1, 'Coefficient âge conducteur');
INSERT OR IGNORE INTO tarif_structure VALUES ('LOB_AUTO_PART', 'COEFF_CRM',       'MULTIPLICATIF', 2, 'Coefficient Bonus-Malus');
INSERT OR IGNORE INTO tarif_structure VALUES ('LOB_AUTO_PART', 'COEFF_PUISSANCE', 'MULTIPLICATIF', 3, 'Coefficient puissance véhicule');
INSERT OR IGNORE INTO tarif_structure VALUES ('LOB_AUTO_PART', 'COEFF_ZONE',      'MULTIPLICATIF', 4, 'Coefficient zone tarifaire');

-- 7b. Snapshots de tendance — série temporelle des KPIs par LOB/période
CREATE TABLE IF NOT EXISTS trend_snapshots (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    id_portefeuille    VARCHAR NOT NULL REFERENCES portefeuilles(id_portefeuille),
    periode            VARCHAR NOT NULL,
    id_run             VARCHAR NOT NULL,
    date_snapshot      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    version_moteur_dsi VARCHAR,

    -- KPIs agrégés
    total_dossiers     INTEGER NOT NULL,
    dossiers_conformes INTEGER NOT NULL,
    taux_conformite    DOUBLE NOT NULL,
    nb_anomalies       INTEGER NOT NULL,
    prime_a_risque     DOUBLE NOT NULL,

    -- Ventilation JSON
    anomalies_par_categorie TEXT,
    impact_par_coefficient  TEXT,

    UNIQUE(id_portefeuille, periode, id_run)
);

-- 7c. Index performance Phase 2d
CREATE INDEX IF NOT EXISTS idx_trend_lob_periode ON trend_snapshots(id_portefeuille, periode);
CREATE INDEX IF NOT EXISTS idx_trend_date ON trend_snapshots(date_snapshot DESC);
CREATE INDEX IF NOT EXISTS idx_tarif_lob ON tarif_structure(id_portefeuille);

-- =============================================================================
-- 8. Notifications système (v6.0)
-- =============================================================================

CREATE TABLE IF NOT EXISTS notifications (
    id VARCHAR PRIMARY KEY,
    destinataire_sso VARCHAR,         -- Ciblage par utilisateur précis
    destinataire_role VARCHAR,        -- Ciblage par rôle (Actuaire MOA, Validateur, Responsable MOA)
    id_portefeuille VARCHAR,          -- Filtrage optionnel par LOB
    titre VARCHAR NOT NULL,
    message TEXT NOT NULL,
    type VARCHAR DEFAULT 'INFO',      -- INFO, ALERT, SUCCESS, ERROR
    is_read BOOLEAN DEFAULT FALSE,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_notifications_dest ON notifications(destinataire_role, is_read, timestamp DESC);


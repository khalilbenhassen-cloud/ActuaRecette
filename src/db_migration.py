# db_migration.py - ActuaRecette Relational Data Migration Engine v6.0
# Migration DuckDB → SQLite (WAL mode) — Phase 1 : Socle Multi-Utilisateur
#
# Ce module :
# 1. Initialise la base SQLite avec le schéma v6.0
# 2. Active WAL mode + busy_timeout pour la concurrence
# 3. Migre les anciens runs JSON (data/uat_runs/) vers SQLite
# 4. Migre l'ancien audit_log.json vers la table audit_entries
# 5. Peuple les règles métier par défaut

import os
import json
import sqlite3
import hashlib
import logging
import argparse
from datetime import datetime

# ---------------------------------------------------------------------------
# Logger structuré (remplace les print() — cf. Plan §6.1b #10)
# ---------------------------------------------------------------------------
logger = logging.getLogger("actuarecette.migration")

def setup_logging(verbose: bool = False):
    """Configure le logger structuré pour la migration."""
    level = logging.DEBUG if verbose else logging.INFO
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        "[%(asctime)s] %(levelname)-7s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))
    logger.setLevel(level)
    logger.addHandler(handler)

# ---------------------------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------------------------

def get_hash(run_id: str, success_rate: float, prime_at_risk: float,
             validator: str, timestamp: str) -> str:
    """Génère un hash SHA-256 de non-répudiation pour sécuriser l'audit."""
    payload = f"{run_id}|{success_rate}|{prime_at_risk}|{validator}|{timestamp}"
    # Sel de non-répudiation : empêche les rainbow table attacks
    _HASH_SALT = "ActuaRecette_v6_audit_2024"
    salted = f"{_HASH_SALT}:{payload}"
    return hashlib.sha256(salted.encode('utf-8')).hexdigest()

def classify_portfolio(run_name: str) -> str:
    """Classifie la campagne vers le bon Portefeuille IARD."""
    name_lower = run_name.lower()
    if any(kw in name_lower for kw in ["auto", "car", "véhicule", "voiture"]):
        return "LOB_AUTO_PART"
    elif any(kw in name_lower for kw in ["incendie", "fire", "rd", "entreprise"]):
        return "LOB_INCENDIE_RD"
    elif any(kw in name_lower for kw in ["mrh", "habitation", "home", "maison"]):
        return "LOB_MRH_HAB"
    else:
        return "LOB_AUTO_PART"  # Safe default fallback

# ---------------------------------------------------------------------------
# Connexion SQLite avec WAL + busy_timeout
# ---------------------------------------------------------------------------

def get_connection(db_path: str, in_memory: bool = False) -> sqlite3.Connection:
    """
    Ouvre une connexion SQLite configurée pour le multi-utilisateur :
    - WAL mode : permet des lectures concurrentes pendant les écritures
    - busy_timeout : attend 5s si la DB est verrouillée (au lieu de crasher)
    - foreign_keys : active les contraintes d'intégrité référentielle
    """
    if in_memory:
        conn = sqlite3.connect(":memory:")
    else:
        conn = sqlite3.connect(db_path)

    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.row_factory = sqlite3.Row
    logger.info(f"Connexion SQLite établie : {db_path if not in_memory else ':memory:'} (WAL mode)")
    return conn

# ---------------------------------------------------------------------------
# Initialisation du schéma
# ---------------------------------------------------------------------------

def init_schema(conn: sqlite3.Connection, schema_sql_path: str) -> bool:
    """Exécute le schéma SQL v6.0 pour créer/vérifier toutes les tables."""
    if not os.path.exists(schema_sql_path):
        logger.error(f"Fichier de schéma introuvable : {schema_sql_path}")
        return False

    with open(schema_sql_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()

    try:
        conn.executescript(schema_sql)
        logger.info("Schéma relationnel v6.0 initialisé avec succès.")
        return True
    except sqlite3.Error as e:
        logger.error(f"Erreur lors de l'initialisation du schéma : {e}")
        return False

# ---------------------------------------------------------------------------
# Peuplement des règles métier par défaut
# ---------------------------------------------------------------------------

def seed_default_rules(conn: sqlite3.Connection):
    """Insère les règles de recette par défaut pour chaque LOB."""
    default_rules = [
        # Portefeuille Auto
        ("RULE_AUTO_SAINS", "LOB_AUTO_PART", "v1.0", "Dossiers Sains",
         "Sains = Total des dossiers - Anomalies critiques", 0.0, "ACTIF"),
        ("RULE_AUTO_ANOM", "LOB_AUTO_PART", "v1.0", "Anomalies",
         "Anomalies = Écarts supérieurs aux tolérances", 0.0, "ACTIF"),
        ("RULE_AUTO_CONF", "LOB_AUTO_PART", "v1.0", "Conformité globale",
         "Taux = 1 - (Anomalies fatales / Total)", 0.02, "ACTIF"),
        ("RULE_AUTO_DIV", "LOB_AUTO_PART", "v1.0", "Divergence pure",
         "Impact = Somme absolue des écarts", 10.0, "ACTIF"),
        # Portefeuille Incendie
        ("RULE_INC_SAINS", "LOB_INCENDIE_RD", "v1.0", "Dossiers Sains",
         "Sains = Total des dossiers - Anomalies critiques", 0.0, "ACTIF"),
        ("RULE_INC_ANOM", "LOB_INCENDIE_RD", "v1.0", "Anomalies",
         "Anomalies = Écarts supérieurs aux tolérances", 0.0, "ACTIF"),
        ("RULE_INC_CONF", "LOB_INCENDIE_RD", "v1.0", "Conformité globale",
         "Taux = 1 - (Anomalies fatales / Total)", 0.05, "ACTIF"),
        ("RULE_INC_DIV", "LOB_INCENDIE_RD", "v1.0", "Divergence pure",
         "Impact = Somme absolue des écarts", 50.0, "ACTIF"),
        # Portefeuille MRH
        ("RULE_MRH_SAINS", "LOB_MRH_HAB", "v1.0", "Dossiers Sains",
         "Sains = Total des dossiers - Anomalies critiques", 0.0, "ACTIF"),
        ("RULE_MRH_ANOM", "LOB_MRH_HAB", "v1.0", "Anomalies",
         "Anomalies = Écarts supérieurs aux tolérances", 0.0, "ACTIF"),
        ("RULE_MRH_CONF", "LOB_MRH_HAB", "v1.0", "Conformité globale",
         "Taux = 1 - (Anomalies fatales / Total)", 0.02, "ACTIF"),
        ("RULE_MRH_DIV", "LOB_MRH_HAB", "v1.0", "Divergence pure",
         "Impact = Somme absolue des écarts", 10.0, "ACTIF"),
    ]
    try:
        for rule in default_rules:
            conn.execute(
                """INSERT OR IGNORE INTO regles_recette 
                   (id_regle, id_portefeuille, version_regle, titre, 
                    formule_theorique, tolerance_unitaire, statut) 
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                rule
            )
        conn.commit()
        logger.info(f"Bibliothèque de formules mathématiques peuplée ({len(default_rules)} règles).")
    except sqlite3.Error as e:
        logger.warning(f"Avertissement lors du peuplement des règles : {e}")

def seed_dynamic_default_rules(conn: sqlite3.Connection):
    """Insère les règles de recette dynamiques par défaut pour chaque LOB."""
    default_rules = [
        # Portefeuille Auto
        ("CTRL-001", "LOB_AUTO_PART", "1.0", "Cohérence prime référence vs production",
         "PRIME_DSI", "==", "PRIME_DSI", "PRIME_REF", 0.05, "ACTIF", "BLOQUANT", None, "systeme", "systeme"),
        ("CTRL-002", "LOB_AUTO_PART", "1.0", "Seuil plancher de tarification",
         "PRIME_DSI", ">=", "150.00", "150.00", 0.01, "ACTIF", "BLOQUANT", "PRIME_REF == 150.00", "systeme", "systeme"),
        ("CTRL-003", "LOB_AUTO_PART", "1.0", "Coefficient jeune conducteur",
         "PRIME_DSI", "==", "PRIME_REF", "PRIME_REF", 10.0, "ACTIF", "ALERTE", "age_conducteur < 25", "systeme", "systeme"),
        ("CTRL-004", "LOB_AUTO_PART", "1.0", "Coefficient puissance véhicule",
         "PRIME_DSI", "==", "PRIME_REF", "PRIME_REF", 10.0, "ACTIF", "ALERTE", "puissance_vehicule > 150", "systeme", "systeme"),
        ("CTRL-005", "LOB_AUTO_PART", "1.0", "Intégrité des données sources",
         "PRIME_REF", ">=", "0.0", "0.0", 0.01, "ACTIF", "BLOQUANT", None, "systeme", "systeme"),

        # Portefeuille Incendie
        ("CTRL-INC-001", "LOB_INCENDIE_RD", "1.0", "Cohérence prime référence vs production",
         "PRIME_PROD", "==", "PRIME_PROD", "PRIME_ACTU", 0.05, "ACTIF", "BLOQUANT", None, "systeme", "systeme"),
        ("CTRL-INC-005", "LOB_INCENDIE_RD", "1.0", "Intégrité des données sources",
         "PRIME_ACTU", ">=", "0.0", "0.0", 0.01, "ACTIF", "BLOQUANT", None, "systeme", "systeme"),

        # Portefeuille MRH
        ("CTRL-MRH-001", "LOB_MRH_HAB", "1.0", "Cohérence prime référence vs production",
         "PRIME_DSI", "==", "PRIME_DSI", "PRIME_REF", 0.05, "ACTIF", "BLOQUANT", None, "systeme", "systeme"),
        ("CTRL-MRH-005", "LOB_MRH_HAB", "1.0", "Intégrité des données sources",
         "PRIME_REF", ">=", "0.0", "0.0", 0.01, "ACTIF", "BLOQUANT", None, "systeme", "systeme"),
    ]
    try:
        for rule in default_rules:
            conn.execute(
                """INSERT OR IGNORE INTO regles_recette_dynamiques 
                   (id_regle, id_portefeuille, version_regle, libelle, 
                    colonne_cible, operateur_logique, valeur_seuil, formule_theorique, 
                    tolerance_unitaire, statut, severite, condition_application, cree_par_sso, valide_par_sso, date_validation) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
                rule
            )
        conn.commit()
        logger.info(f"Bibliothèque de règles dynamiques peuplée ({len(default_rules)} règles).")
    except sqlite3.Error as e:
        logger.warning(f"Avertissement lors du peuplement des règles dynamiques : {e}")

# ---------------------------------------------------------------------------
# Migration des runs JSON → SQLite
# ---------------------------------------------------------------------------

def migrate_json_runs(conn: sqlite3.Connection, runs_dir: str,
                      dry_run: bool = False) -> dict:
    """
    Migre les fichiers JSON de data/uat_runs/ vers les tables SQLite.
    Retourne un dictionnaire de statistiques.
    """
    stats = {"migrated_campaigns": 0, "migrated_runs": 0, "failed": 0, "total": 0}

    if not os.path.exists(runs_dir):
        logger.error(f"Dossier source introuvable : {runs_dir}")
        return stats

    json_files = sorted(f for f in os.listdir(runs_dir) if f.endswith(".json"))
    stats["total"] = len(json_files)
    logger.info(f"{len(json_files)} fichiers JSON trouvés dans {runs_dir}")

    for json_file in json_files:
        file_path = os.path.join(runs_dir, json_file)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Validation du schéma JSON
            required_keys = ["run_id", "run_name", "timestamp", "kpis"]
            if not all(k in data for k in required_keys):
                logger.warning(f"Fichier ignoré (schéma invalide) : {json_file}")
                stats["failed"] += 1
                continue

            run_id = data["run_id"]
            run_name = data["run_name"]
            timestamp_str = data["timestamp"]
            kpis = data["kpis"]

            # Parse de la date
            try:
                date_execution = datetime.fromisoformat(timestamp_str)
            except Exception:
                date_execution = datetime.now()

            # Classification LOB
            id_portefeuille = classify_portfolio(run_name)
            periode = date_execution.strftime("%Y-%m")

            # Campagne temporelle (upsert)
            id_campagne = f"CAMP_{id_portefeuille}_{periode.replace('-', '_')}"

            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM campagnes_recette WHERE id_campagne = ?",
                [id_campagne]
            ).fetchone()

            if row["cnt"] == 0:
                if not dry_run:
                    conn.execute(
                        """INSERT INTO campagnes_recette 
                           (id_campagne, id_portefeuille, periode, type_testing) 
                           VALUES (?, ?, ?, ?)""",
                        [id_campagne, id_portefeuille, periode, "CLOTURE"]
                    )
                stats["migrated_campaigns"] += 1
                logger.debug(f"  [NEW] Campagne {id_campagne} ({periode}) → {id_portefeuille}")

            # KPIs
            taux_alignement = kpis.get("success_rate_pct", 100.0)

            # Prime à risque
            prime_a_risque = 0.0
            anomalies = data.get("anomalies", [])
            for anom in anomalies:
                if anom.get("is_fatal_defect", False):
                    prime_a_risque += abs(anom.get("abs_deviation", 0.0))

            # Statut de validation
            raw_status = kpis.get("final_status", "Brouillon").upper()
            if "CONFORME" in raw_status and "NON" not in raw_status:
                statut_validation = "CERTIFIÉ"
            elif "REJET" in raw_status or "NON" in raw_status:
                statut_validation = "BROUILLON"  # v6.0 : REJETÉ retourne visuellement en BROUILLON
            else:
                statut_validation = "BROUILLON"

            # Visas
            maker_sso_user = "maker.junior"
            checker_sso_user = None
            if statut_validation == "CERTIFIÉ":
                checker_sso_user = "checker"

            # Numéro séquentiel atomique
            row = conn.execute(
                "SELECT COALESCE(MAX(num_run), 0) as max_num FROM runs_execution WHERE id_campagne = ?",
                [id_campagne]
            ).fetchone()
            num_run = row["max_num"] + 1

            # Version du moteur
            version_moteur_dsi = data.get("metadata", {}).get("engine_version", "v1.0.0")

            # Signature cryptographique
            signature_hash = get_hash(
                run_id=run_id,
                success_rate=taux_alignement,
                prime_at_risk=prime_a_risque,
                validator=checker_sso_user or maker_sso_user,
                timestamp=timestamp_str
            )

            # Insertion du run
            if not dry_run:
                conn.execute(
                    """INSERT OR IGNORE INTO runs_execution (
                        id_run, id_campagne, num_run, version_moteur_dsi, date_execution, 
                        taux_alignement, prime_a_risque, statut_validation, maker_sso_user, 
                        checker_sso_user, signature_hash, created_by_sso
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    [
                        run_id, id_campagne, num_run, version_moteur_dsi, date_execution,
                        taux_alignement, prime_a_risque, statut_validation, maker_sso_user,
                        checker_sso_user, signature_hash, maker_sso_user
                    ]
                )
            stats["migrated_runs"] += 1
            logger.info(f"  [OK] Run {run_id} ({run_name}) — Taux: {taux_alignement}% — Statut: {statut_validation}")

        except Exception as e:
            logger.error(f"Erreur migration fichier {json_file} : {e}", exc_info=True)
            stats["failed"] += 1

    if not dry_run:
        conn.commit()

    return stats

# ---------------------------------------------------------------------------
# Migration de l'audit_log.json → table audit_entries
# ---------------------------------------------------------------------------

def migrate_audit_log(conn: sqlite3.Connection, audit_log_path: str,
                      dry_run: bool = False) -> int:
    """Migre les entrées de audit_log.json vers la table audit_entries."""
    if not os.path.exists(audit_log_path):
        logger.warning(f"Fichier audit_log.json introuvable : {audit_log_path} — ignoré.")
        return 0

    try:
        with open(audit_log_path, "r", encoding="utf-8") as f:
            entries = json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Impossible de lire audit_log.json : {e}")
        return 0

    if not isinstance(entries, list):
        logger.error("audit_log.json n'est pas un tableau JSON.")
        return 0

    migrated = 0
    for entry in entries:
        try:
            # Mapping des champs existants vers le nouveau schéma
            timestamp = entry.get("timestamp", datetime.now().isoformat())
            run_id = entry.get("run_id", "")
            action = entry.get("action", "UNKNOWN")
            comment = entry.get("comment", "")
            validator_name = entry.get("validator_name", "inconnu")
            role = entry.get("role", "Analyste Actuariel")

            # Déduction du SSO à partir du nom (données historiques)
            sso_map = {
                "Sophie Martin": "checker",
                "Karim Benali": "maker.junior",
                "Jean Dupont": "maker.senior",
                "Marie Leroux": "manager",
                "Validateur Technique (Checker)": "checker",
                "Actuaire junior (Maker)": "maker.junior",
                "Actuaire senior": "maker.senior",
                "Responsable Métier (Manager)": "manager",
            }
            user_sso = sso_map.get(validator_name, validator_name.lower().replace(" ", "."))

            if not dry_run:
                conn.execute(
                    """INSERT INTO audit_entries 
                       (timestamp, user_sso, user_name, user_role, run_id, action, comment)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    [timestamp, user_sso, validator_name, role, run_id, action, comment]
                )
            migrated += 1
            logger.debug(f"  [AUDIT] {action} par {validator_name} sur {run_id}")

        except Exception as e:
            logger.error(f"Erreur migration entrée audit : {e}")

    if not dry_run:
        conn.commit()

    logger.info(f"Audit log migré : {migrated}/{len(entries)} entrées.")
    return migrated

# ---------------------------------------------------------------------------
# Point d'entrée principal
# ---------------------------------------------------------------------------

def run_migration(db_path: str, runs_dir: str, schema_sql_path: str,
                  audit_log_path: str = None, dry_run: bool = False) -> bool:
    """
    Point d'entrée principal de la migration.
    1. Crée/vérifie le schéma SQLite v6.0
    2. Peuple les règles métier par défaut
    3. Migre les runs JSON → SQLite
    4. Migre l'audit_log.json → table audit_entries
    """
    logger.info("=" * 74)
    logger.info("DÉMARRAGE DE LA MIGRATION RELATIONNELLE — ActuaRecette v6.0")
    logger.info(f"  Dossier Runs   : {runs_dir}")
    logger.info(f"  Base cible     : {db_path} {'(DRY-RUN)' if dry_run else ''}")
    logger.info(f"  Audit log      : {audit_log_path or 'non spécifié'}")
    logger.info("=" * 74)

    # 1. Connexion SQLite (WAL + busy_timeout)
    try:
        conn = get_connection(db_path, in_memory=dry_run)
    except sqlite3.Error as e:
        logger.error(f"Impossible d'ouvrir la base SQLite : {e}")
        return False

    # 2. Schéma
    if not init_schema(conn, schema_sql_path):
        conn.close()
        return False

    # 3. Règles métier
    if not dry_run:
        seed_default_rules(conn)
        seed_dynamic_default_rules(conn)

    # 4. Migration des runs JSON
    stats = migrate_json_runs(conn, runs_dir, dry_run=dry_run)

    # 5. Migration de l'audit log
    audit_count = 0
    if audit_log_path:
        audit_count = migrate_audit_log(conn, audit_log_path, dry_run=dry_run)

    # 6. Bilan
    conn.close()
    logger.info("=" * 74)
    logger.info("BILAN DE LA MIGRATION")
    logger.info(f"  Runs migrés      : {stats['migrated_runs']}/{stats['total']}")
    logger.info(f"  Campagnes créées  : {stats['migrated_campaigns']}")
    logger.info(f"  Runs en échec     : {stats['failed']}")
    logger.info(f"  Entrées d'audit   : {audit_count}")
    logger.info(f"  Mode              : {'Simulation (Dry-Run)' if dry_run else 'Données persistées'}")
    logger.info("=" * 74)

    return stats["failed"] == 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Moteur de migration SQLite (WAL) pour ActuaRecette v6.0."
    )
    parser.add_argument("--db-path", default="data/actuarecette.db",
                        help="Chemin vers le fichier SQLite de destination.")
    parser.add_argument("--runs-dir", default="data/uat_runs",
                        help="Dossier contenant les anciens fichiers JSON.")
    parser.add_argument("--schema-sql", default="data/schema.sql",
                        help="Fichier de schéma SQL d'initialisation.")
    parser.add_argument("--audit-log", default="data/audit_log.json",
                        help="Fichier audit_log.json à migrer.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Si activé, simule la migration en mémoire sans écrire sur le disque.")
    parser.add_argument("--verbose", action="store_true",
                        help="Active les logs de niveau DEBUG.")

    args = parser.parse_args()

    setup_logging(verbose=args.verbose)

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_abs_path = os.path.join(base_dir, args.db_path)
    runs_abs_dir = os.path.join(base_dir, args.runs_dir)
    schema_abs_sql = os.path.join(base_dir, args.schema_sql)
    audit_abs_path = os.path.join(base_dir, args.audit_log)

    success = run_migration(
        db_path=db_abs_path,
        runs_dir=runs_abs_dir,
        schema_sql_path=schema_abs_sql,
        audit_log_path=audit_abs_path,
        dry_run=args.dry_run
    )

    exit(0 if success else 1)

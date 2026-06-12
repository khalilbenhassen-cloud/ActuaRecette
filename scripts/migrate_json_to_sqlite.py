#!/usr/bin/env python3
# migrate_json_to_sqlite.py -- Migration one-shot JSON -> SQLite (Phase 3 - T3)
"""
Migre les donnees historiques des fichiers JSON vers la base SQLite.

Sources:
  - data/uat_runs/*.json     -> runs_execution + campagnes_recette
  - data/audit_log.json      -> audit_entries

Ce script est IDEMPOTENT : il peut etre relance sans risque (INSERT OR IGNORE).

Usage:
    python scripts/migrate_json_to_sqlite.py [--dry-run] [--db-path data/actuarecette.db]
"""
import os
import sys
import json
import glob
import sqlite3
import hashlib
import argparse
import datetime

# Add project root to path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

DB_PATH_DEFAULT = os.path.join(ROOT, "data", "actuarecette.db")
SCHEMA_PATH = os.path.join(ROOT, "data", "schema.sql")
UAT_RUNS_DIR = os.path.join(ROOT, "data", "uat_runs")
AUDIT_LOG_PATH = os.path.join(ROOT, "data", "audit_log.json")


def init_schema(conn: sqlite3.Connection):
    """Apply schema.sql to initialize tables."""
    if os.path.exists(SCHEMA_PATH):
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        print(f"  [OK] Schema applique depuis {SCHEMA_PATH}")
    else:
        print(f"  [WARN] Schema introuvable : {SCHEMA_PATH}")


def migrate_runs(conn: sqlite3.Connection, dry_run: bool = False) -> int:
    """Migrate data/uat_runs/*.json -> runs_execution + campagnes_recette."""
    pattern = os.path.join(UAT_RUNS_DIR, "*.json")
    files = sorted(glob.glob(pattern))

    if not files:
        print("  [INFO] Aucun fichier JSON dans data/uat_runs/")
        return 0

    migrated = 0
    for filepath in files:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                run = json.load(f)

            run_id = run.get("run_id", os.path.basename(filepath).replace(".json", ""))
            run_name = run.get("run_name", "Sans nom")
            timestamp = run.get("timestamp", "")
            metadata = run.get("metadata", {})
            kpis = run.get("kpis", {})

            # Extract LOB from metadata or run name
            lob_id = metadata.get("lob_id", "LOB_AUTO_PART")

            # Extract period from timestamp (YYYY-MM)
            try:
                dt = datetime.datetime.fromisoformat(timestamp)
                periode = dt.strftime("%Y-%m")
            except Exception:
                periode = "2026-01"

            # Compute signature hash
            # Sel de non-répudiation : empêche les rainbow table attacks
            _HASH_SALT = "ActuaRecette_v6_audit_2024"
            _hash_payload = f"{_HASH_SALT}:{json.dumps(run, sort_keys=True, default=str)}"
            sig = hashlib.sha256(
                _hash_payload.encode("utf-8")
            ).hexdigest()[:16]

            # Ensure campagne exists
            campagne_id = f"camp_{lob_id}_{periode}"

            if not dry_run:
                conn.execute(
                    "INSERT OR IGNORE INTO campagnes_recette "
                    "(id_campagne, id_portefeuille, periode, type_testing) "
                    "VALUES (?, ?, ?, 'CLOTURE')",
                    (campagne_id, lob_id, periode),
                )

                # Determine num_run (auto-increment within campagne)
                row = conn.execute(
                    "SELECT COALESCE(MAX(num_run), 0) + 1 FROM runs_execution WHERE id_campagne = ?",
                    (campagne_id,),
                ).fetchone()
                num_run = row[0] if row else 1

                # Map final_status to validation status
                final_status = kpis.get("final_status", "Brouillon")
                status_map = {
                    "CONFORME": "CERTIFIE",
                    "NON CONFORME": "CALCULE",
                    "Brouillon": "BROUILLON",
                    "Certifie": "CERTIFIE",
                }
                statut = status_map.get(final_status, "BROUILLON")

                conn.execute(
                    "INSERT OR IGNORE INTO runs_execution "
                    "(id_run, id_campagne, num_run, version_moteur_dsi, "
                    "date_execution, taux_alignement, prime_a_risque, "
                    "statut_validation, maker_sso_user, signature_hash, created_by_sso) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        run_id, campagne_id, num_run,
                        metadata.get("engine_version", "ActuaRecette-v6.0"),
                        timestamp,
                        kpis.get("success_rate_pct", 0.0),
                        kpis.get("total_absolute_delta_euros", 0.0),
                        statut,
                        metadata.get("created_by", "system"),
                        sig,
                        metadata.get("created_by", "system"),
                    ),
                )

            migrated += 1
            print(f"  [{'DRY' if dry_run else 'OK'}] {run_id} -> {campagne_id} ({lob_id})")

        except Exception as e:
            print(f"  [ERR] {filepath}: {e}")

    return migrated


def migrate_audit_trail(conn: sqlite3.Connection, dry_run: bool = False) -> int:
    """Migrate data/audit_log.json -> audit_entries."""
    if not os.path.exists(AUDIT_LOG_PATH):
        print("  [INFO] audit_log.json introuvable")
        return 0

    try:
        with open(AUDIT_LOG_PATH, "r", encoding="utf-8") as f:
            entries = json.load(f)
    except Exception as e:
        print(f"  [ERR] Lecture audit_log.json : {e}")
        return 0

    if not isinstance(entries, list):
        print("  [ERR] audit_log.json n'est pas une liste")
        return 0

    migrated = 0
    for entry in entries:
        try:
            timestamp = entry.get("timestamp", "")
            user_sso = entry.get("validator_sso", entry.get("user_sso", "system"))
            user_name = entry.get("validator_name", entry.get("user_name", "Systeme"))
            user_role = entry.get("role", "Actuaire MOA")
            run_id = entry.get("run_id", "")
            action = entry.get("action", "UNKNOWN")
            comment = entry.get("comment", "")

            # Sel de non-répudiation : empêche les rainbow table attacks
            _HASH_SALT = "ActuaRecette_v6_audit_2024"
            _hash_input = f"{_HASH_SALT}:{timestamp}:{user_sso}:{run_id}:{action}"
            sig = hashlib.sha256(
                _hash_input.encode("utf-8")
            ).hexdigest()[:16]

            if not dry_run:
                conn.execute(
                    "INSERT OR IGNORE INTO audit_entries "
                    "(timestamp, user_sso, user_name, user_role, run_id, action, comment, signature_hash) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (timestamp, user_sso, user_name, user_role, run_id, action, comment, sig),
                )

            migrated += 1
        except Exception as e:
            print(f"  [ERR] Audit entry: {e}")

    print(f"  [{'DRY' if dry_run else 'OK'}] {migrated} entrees d'audit migrees")
    return migrated


def main():
    parser = argparse.ArgumentParser(description="Migration JSON -> SQLite")
    parser.add_argument("--dry-run", action="store_true", help="Simulation sans ecriture")
    parser.add_argument("--db-path", default=DB_PATH_DEFAULT, help="Chemin de la DB SQLite")
    args = parser.parse_args()

    print("=" * 60)
    print("  ActuaRecette - Migration JSON -> SQLite (T3)")
    print("=" * 60)
    print(f"  DB : {args.db_path}")
    print(f"  Mode : {'DRY RUN' if args.dry_run else 'PRODUCTION'}")
    print()

    # Create DB directory if needed
    os.makedirs(os.path.dirname(args.db_path), exist_ok=True)

    conn = sqlite3.connect(args.db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")

    try:
        # 1. Schema
        print("[1/3] Application du schema...")
        init_schema(conn)

        # 2. Runs
        print("\n[2/3] Migration des runs JSON...")
        runs_count = migrate_runs(conn, args.dry_run)

        # 3. Audit
        print("\n[3/3] Migration du journal d'audit...")
        audit_count = migrate_audit_trail(conn, args.dry_run)

        if not args.dry_run:
            conn.commit()

        print()
        print("=" * 60)
        print(f"  Runs migres  : {runs_count}")
        print(f"  Audit migres : {audit_count}")
        print(f"  Statut       : {'SIMULATION' if args.dry_run else 'TERMINE'}")
        print("=" * 60)

    except Exception as e:
        print(f"\n  [FATAL] {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()

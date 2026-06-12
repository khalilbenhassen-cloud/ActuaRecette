"""Test suite for Maker-Checker (double approbation) governance on LOBs and thresholds."""
import sys
sys.stdout.reconfigure(encoding="utf-8")
import os
import sqlite3

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

passed = 0
failed = 0

def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  [OK] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name} -- {detail}")

print("=== LOB Maker-Checker Governance Tests ===")

from dashboard.utils.auth import load_lob_registry, find_user_by_sso, add_lob_to_registry, remove_lob_from_registry

db_paths = ["data/actuarecette.db", "data/actuarecette_v2.db"]

# Ensure clean starting state
for db_path in db_paths:
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        conn.execute("DELETE FROM portefeuilles WHERE id_portefeuille = 'LOB_GOUV_TEST'")
        conn.commit()
        conn.close()

# Remove from json registry if present
remove_lob_from_registry("LOB_GOUV_TEST")

# 1. Simulate Maker creating LOB draft (EN_ATTENTE)
print("\n--- 1. LOB Draft Creation by Maker ---")
for db_path in db_paths:
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        conn.execute(
            """INSERT INTO portefeuilles 
            (id_portefeuille, code_metier, libelle, type_risque, seuil_materialite_pct, warning_pct, critical_pct, materiality_threshold_eur, statut, cree_par_sso, date_creation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'EN_ATTENTE', 'maker.junior', datetime('now'))""",
            ('LOB_GOUV_TEST', 'GOUV', 'Gouvernance Test LOB', 'IARD', 0.2, 3.0, 5.0, 500.0)
        )
        conn.commit()
        conn.close()

# Verify that load_lob_registry does not return the pending LOB by default (include_pending=False)
lobs_active = load_lob_registry(include_pending=False)
check("Pending LOB not returned by default registry load", "LOB_GOUV_TEST" not in lobs_active)

lobs_all = load_lob_registry(include_pending=True)
check("Pending LOB returned when include_pending=True", "LOB_GOUV_TEST" in lobs_all)

# Verify Maker can_view_lob logic for their pending LOB
maker = find_user_by_sso("maker.junior")
# The Maker can view it if it is assigned or if they are the creator (which page_10_admin_rules handles in selectboxes)
check("Maker found in SQLite", maker is not None)
check("Maker does not have the LOB assigned yet", "LOB_GOUV_TEST" not in maker.assigned_lobs)

# 2. Simulate Manager Approving the LOB creation
print("\n--- 2. LOB Creation Approval by Manager ---")
for db_path in db_paths:
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        # 1. Update LOB status
        conn.execute(
            "UPDATE portefeuilles SET statut = 'ACTIF', valide_par_sso = 'manager', date_validation = datetime('now') WHERE id_portefeuille = 'LOB_GOUV_TEST'"
        )
        # 2. Automatically assign LOB to the creator
        row = conn.execute("SELECT assigned_lobs FROM utilisateurs WHERE sso = 'maker.junior'").fetchone()
        if row:
            current_lobs = [l.strip() for l in row[0].split(",") if l.strip()] if row[0] else []
            if "LOB_GOUV_TEST" not in current_lobs:
                current_lobs.append("LOB_GOUV_TEST")
                new_assigned = ",".join(current_lobs)
                conn.execute("UPDATE utilisateurs SET assigned_lobs = ? WHERE sso = 'maker.junior'", [new_assigned])
        conn.commit()
        conn.close()

# Update the legacy JSON registry as done in the UI
add_lob_to_registry("LOB_GOUV_TEST")

# Verify that the LOB is now active and returned by default registry load
lobs_active_after = load_lob_registry(include_pending=False)
check("Approved LOB now returned by default registry load", "LOB_GOUV_TEST" in lobs_active_after)

# Verify that the LOB is now assigned to the Maker
maker_after = find_user_by_sso("maker.junior")
check("Maker now has the LOB assigned", "LOB_GOUV_TEST" in maker_after.assigned_lobs)

# 3. Simulate Maker proposing threshold changes
print("\n--- 3. Threshold Modification Proposal by Maker ---")
for db_path in db_paths:
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        conn.execute(
            """UPDATE portefeuilles SET
               statut='EN_ATTENTE', cree_par_sso='maker.junior', date_creation=datetime('now'),
               draft_libelle='Gouvernance Test LOB Modifié', draft_type_risque='IARD',
               draft_seuil_materialite_pct=0.45, draft_warning_pct=4.0, draft_critical_pct=6.0, draft_materiality_threshold_eur=600.0
               WHERE id_portefeuille='LOB_GOUV_TEST'"""
        )
        conn.commit()
        conn.close()

# Verify that active values are unchanged but draft values are stored and status is EN_ATTENTE
for db_path in db_paths:
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM portefeuilles WHERE id_portefeuille='LOB_GOUV_TEST'").fetchone()
        conn.close()
        check(f"[{db_path}] Status is EN_ATTENTE", row["statut"] == "EN_ATTENTE")
        check(f"[{db_path}] Active seuil_materialite_pct is still 0.2", row["seuil_materialite_pct"] == 0.2)
        check(f"[{db_path}] Draft seuil_materialite_pct is 0.45", row["draft_seuil_materialite_pct"] == 0.45)

# 4. Simulate Manager Approving the modification
print("\n--- 4. Threshold Modification Approval by Manager ---")
for db_path in db_paths:
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        conn.execute(
            """UPDATE portefeuilles SET
               libelle = draft_libelle,
               type_risque = draft_type_risque,
               seuil_materialite_pct = draft_seuil_materialite_pct,
               warning_pct = draft_warning_pct,
               critical_pct = draft_critical_pct,
               materiality_threshold_eur = draft_materiality_threshold_eur,
               statut = 'ACTIF',
               valide_par_sso = 'manager',
               date_validation = datetime('now'),
               draft_libelle = NULL,
               draft_type_risque = NULL,
               draft_seuil_materialite_pct = NULL,
               draft_warning_pct = NULL,
               draft_critical_pct = NULL,
               draft_materiality_threshold_eur = NULL
               WHERE id_portefeuille = 'LOB_GOUV_TEST'"""
        )
        conn.commit()
        conn.close()

# Verify that active values are updated, status is ACTIF, and draft values are NULL
for db_path in db_paths:
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM portefeuilles WHERE id_portefeuille='LOB_GOUV_TEST'").fetchone()
        conn.close()
        check(f"[{db_path}] Status is ACTIF after approval", row["statut"] == "ACTIF")
        check(f"[{db_path}] Active seuil_materialite_pct is now 0.45", row["seuil_materialite_pct"] == 0.45)
        check(f"[{db_path}] Draft seuil_materialite_pct is NULL after approval", row["draft_seuil_materialite_pct"] is None)

# Clean up test database entries and restore Maker assigned_lobs
print("\n--- Cleanup ---")
for db_path in db_paths:
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        conn.execute("DELETE FROM portefeuilles WHERE id_portefeuille = 'LOB_GOUV_TEST'")
        # Restore Maker assigned_lobs by removing LOB_GOUV_TEST
        row = conn.execute("SELECT assigned_lobs FROM utilisateurs WHERE sso = 'maker.junior'").fetchone()
        if row:
            current_lobs = [l.strip() for l in row[0].split(",") if l.strip()] if row[0] else []
            if "LOB_GOUV_TEST" in current_lobs:
                current_lobs.remove("LOB_GOUV_TEST")
                new_assigned = ",".join(current_lobs)
                conn.execute("UPDATE utilisateurs SET assigned_lobs = ? WHERE sso = 'maker.junior'", [new_assigned])
        conn.commit()
        conn.close()

remove_lob_from_registry("LOB_GOUV_TEST")

print(f"\n{'='*50}")
total = passed + failed
print(f"  Total: {total} | Pass: {passed} | Fail: {failed}")
if failed == 0:
    print("  >>> LOB GOUVERNANCE MAKER-CHECKER VALIDATED <<<")
print(f"{'='*50}")
sys.exit(0 if failed == 0 else 1)

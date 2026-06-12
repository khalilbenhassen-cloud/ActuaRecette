"""Test Rule Lifecycle: Verify deactivation and deletion of dynamic rules in SQLite databases."""
import sys
sys.stdout.reconfigure(encoding="utf-8")
import os
import sqlite3
import datetime

ROOT = "c:/Users/hp/Documents/ActuaRecette"
sys.path.insert(0, ROOT)

passed = 0
failed = 0

def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  [OK] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name} -- {detail}")

print("=== Test Rule Lifecycle ===")

dbs = ["data/actuarecette.db", "data/actuarecette_v2.db"]

# Cleanup existing mock rules if any
for db in dbs:
    if os.path.exists(db):
        conn = sqlite3.connect(db)
        conn.execute("DELETE FROM regles_recette_dynamiques WHERE id_regle LIKE 'TEST-LIFE-%'")
        conn.execute("DELETE FROM audit_entries WHERE id_portefeuille = 'LOB_TEST_LIFE'")
        conn.commit()
        conn.close()

# Test 1: Deleting a rule in BROUILLON/REJETÉ status
for db in dbs:
    if os.path.exists(db):
        conn = sqlite3.connect(db)
        # 1. Insert BROUILLON rule
        conn.execute("""
            INSERT INTO regles_recette_dynamiques 
            (id_regle, id_portefeuille, version_regle, libelle, colonne_cible, operateur_logique, valeur_seuil, formule_theorique, tolerance_unitaire, statut, severite, domaine, cree_par_sso)
            VALUES ('TEST-LIFE-001', 'LOB_TEST_LIFE', '1.0', 'Test Draft Rule', 'PRIME_DSI', '>=', '100', 'PRIME_REF * 0.9', 0.05, 'BROUILLON', 'ALERTE', 'Prime', 'test_user')
        """)
        conn.commit()
        
        # Verify insertion
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM regles_recette_dynamiques WHERE id_regle = 'TEST-LIFE-001'")
        count = cursor.fetchone()[0]
        check(f"TEST-LIFE-001 inserted in {os.path.basename(db)}", count == 1)
        
        # 2. Simulate deletion action
        conn.execute("DELETE FROM regles_recette_dynamiques WHERE id_regle = ? AND version_regle = ?", ['TEST-LIFE-001', '1.0'])
        conn.commit()
        
        # Verify deletion
        cursor.execute("SELECT COUNT(*) FROM regles_recette_dynamiques WHERE id_regle = 'TEST-LIFE-001'")
        count = cursor.fetchone()[0]
        check(f"TEST-LIFE-001 deleted from {os.path.basename(db)}", count == 0)
        
        conn.close()

# Test 2: Deactivating a rule in ACTIF status (Soft-delete/OBSOLÈTE)
for db in dbs:
    if os.path.exists(db):
        conn = sqlite3.connect(db)
        # 1. Insert ACTIF rule
        conn.execute("""
            INSERT INTO regles_recette_dynamiques 
            (id_regle, id_portefeuille, version_regle, libelle, colonne_cible, operateur_logique, valeur_seuil, formule_theorique, tolerance_unitaire, statut, severite, domaine, cree_par_sso)
            VALUES ('TEST-LIFE-002', 'LOB_TEST_LIFE', '1.0', 'Test Active Rule', 'SINISTRE_DSI', '>=', '200', 'SINISTRE_REF * 0.9', 0.05, 'ACTIF', 'ALERTE', 'Sinistre', 'test_user')
        """)
        conn.commit()
        
        # Verify insertion
        cursor = conn.cursor()
        cursor.execute("SELECT statut FROM regles_recette_dynamiques WHERE id_regle = 'TEST-LIFE-002'")
        statut = cursor.fetchone()[0]
        check(f"TEST-LIFE-002 inserted as ACTIF in {os.path.basename(db)}", statut == "ACTIF")
        
        # 2. Simulate deactivation action
        conn.execute("UPDATE regles_recette_dynamiques SET statut = 'OBSOLÈTE' WHERE id_regle = ? AND version_regle = ?", ['TEST-LIFE-002', '1.0'])
        conn.commit()
        
        # Verify deactivation
        cursor.execute("SELECT statut FROM regles_recette_dynamiques WHERE id_regle = 'TEST-LIFE-002'")
        statut = cursor.fetchone()[0]
        check(f"TEST-LIFE-002 status is OBSOLÈTE in {os.path.basename(db)}", statut == "OBSOLÈTE")
        
        conn.close()

# Test 3: Verify audit log entries are registered correctly
for db in dbs:
    if os.path.exists(db):
        conn = sqlite3.connect(db)
        # Simulate admin audit logging
        now = datetime.datetime.now().isoformat()
        conn.execute(
            """INSERT INTO audit_entries
            (timestamp, user_sso, user_name, user_role, id_portefeuille, action, comment, signature_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (now, 'test_user', 'Test User', 'Responsable MOA', 'LOB_TEST_LIFE', 'RULE_DEACTIVATED', 'Desactivation de la regle TEST-LIFE-002 v1.0', 'sig_test')
        )
        conn.commit()
        
        # Verify audit log entry exists
        cursor = conn.cursor()
        cursor.execute("SELECT action, comment FROM audit_entries WHERE id_portefeuille = 'LOB_TEST_LIFE'")
        row = cursor.fetchone()
        check(f"Audit log registered correctly in {os.path.basename(db)}", row is not None)
        check(f"Audit action matches in {os.path.basename(db)}", row[0] == "RULE_DEACTIVATED")
        check(f"Audit comment matches in {os.path.basename(db)}", "TEST-LIFE-002" in row[1])
        
        conn.close()

# Final cleanup
for db in dbs:
    if os.path.exists(db):
        conn = sqlite3.connect(db)
        conn.execute("DELETE FROM regles_recette_dynamiques WHERE id_regle LIKE 'TEST-LIFE-%'")
        conn.execute("DELETE FROM audit_entries WHERE id_portefeuille = 'LOB_TEST_LIFE'")
        conn.commit()
        conn.close()

print("==================================================")
print(f"  Total: {passed + failed} | Pass: {passed} | Fail: {failed}")
print("==================================================")
sys.exit(0 if failed == 0 else 1)

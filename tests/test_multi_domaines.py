"""Test Multi-Domaines: verify multi-domain dynamic rules, thresholds, and SQL loading."""
import sys
sys.stdout.reconfigure(encoding="utf-8")
import os
import sqlite3

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

print("=== Test Multi-Domaines ===")

# Test 1: SQLite schema verification
db_path = "data/actuarecette.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Verify domaine column in regles_recette_dynamiques
cursor.execute("PRAGMA table_info(regles_recette_dynamiques)")
cols = [col[1] for col in cursor.fetchall()]
check("domaine column in regles_recette_dynamiques", "domaine" in cols)

# Verify table portefeuilles_seuils_domaines structure
cursor.execute("PRAGMA table_info(portefeuilles_seuils_domaines)")
seuils_cols = [col[1] for col in cursor.fetchall()]
check("portefeuilles_seuils_domaines table exists", len(seuils_cols) > 0)
check("id_portefeuille column in seuils table", "id_portefeuille" in seuils_cols)
check("domaine column in seuils table", "domaine" in seuils_cols)
check("seuil_materialite_pct column in seuils table", "seuil_materialite_pct" in seuils_cols)
check("warning_pct column in seuils table", "warning_pct" in seuils_cols)
check("critical_pct column in seuils table", "critical_pct" in seuils_cols)
check("materiality_threshold_eur column in seuils table", "materiality_threshold_eur" in seuils_cols)
check("statut column in seuils table", "statut" in seuils_cols)

conn.close()

# Test 2: Rules domain-filtering logic
from dashboard.views.page_03_espace_travail import _load_control_rules, _get_lob_tolerance

# Insert mock rule for Sinistre and Prime domains to verify filter
db_path = "data/actuarecette.db"
for db in ["data/actuarecette.db", "data/actuarecette_v2.db"]:
    if os.path.exists(db):
        conn = sqlite3.connect(db)
        # Clean up any potential leftover mock rules
        conn.execute("DELETE FROM regles_recette_dynamiques WHERE id_regle LIKE 'MOCK-%'")
        # Insert Prime rule
        conn.execute("""
            INSERT INTO regles_recette_dynamiques 
            (id_regle, id_portefeuille, version_regle, libelle, colonne_cible, operateur_logique, valeur_seuil, formule_theorique, tolerance_unitaire, statut, severite, domaine, cree_par_sso)
            VALUES ('MOCK-001', 'LOB_AUTO_PART', '1.0', 'Mock Prime Rule', 'PRIME_DSI', '>=', '100', 'PRIME_REF * 0.9', 0.05, 'ACTIF', 'ALERTE', 'Prime', 'systeme')
        """)
        # Insert Sinistre rule
        conn.execute("""
            INSERT INTO regles_recette_dynamiques 
            (id_regle, id_portefeuille, version_regle, libelle, colonne_cible, operateur_logique, valeur_seuil, formule_theorique, tolerance_unitaire, statut, severite, domaine, cree_par_sso)
            VALUES ('MOCK-002', 'LOB_AUTO_PART', '1.0', 'Mock Sinistre Rule', 'SINISTRE_DSI', '>=', '200', 'SINISTRE_REF * 0.9', 0.05, 'ACTIF', 'ALERTE', 'Sinistre', 'systeme')
        """)
        conn.commit()
        conn.close()

prime_rules = _load_control_rules('LOB_AUTO_PART', 'Prime')
prime_rule_ids = [r['rule_id'] for r in prime_rules]
check("Mock Prime rule loaded under Prime domain", "MOCK-001" in prime_rule_ids)
check("Mock Sinistre rule NOT loaded under Prime domain", "MOCK-002" not in prime_rule_ids)

sinistre_rules = _load_control_rules('LOB_AUTO_PART', 'Sinistre')
sinistre_rule_ids = [r['rule_id'] for r in sinistre_rules]
check("Mock Sinistre rule loaded under Sinistre domain", "MOCK-002" in sinistre_rule_ids)
check("Mock Prime rule NOT loaded under Sinistre domain", "MOCK-001" not in sinistre_rule_ids)

# Test 3: Threshold loading logic per domain
# Set custom thresholds for MRH in Réserve domain
for db in ["data/actuarecette.db", "data/actuarecette_v2.db"]:
    if os.path.exists(db):
        conn = sqlite3.connect(db)
        conn.execute("DELETE FROM portefeuilles_seuils_domaines WHERE id_portefeuille='LOB_MRH_HAB' AND domaine='Réserve'")
        conn.execute("""
            INSERT INTO portefeuilles_seuils_domaines 
            (id_portefeuille, domaine, seuil_materialite_pct, warning_pct, critical_pct, materiality_threshold_eur, statut)
            VALUES ('LOB_MRH_HAB', 'Réserve', 1.8, 4.5, 7.5, 6000.0, 'ACTIF')
        """)
        conn.commit()
        conn.close()

reserve_tols = _get_lob_tolerance('LOB_MRH_HAB', 'Réserve')
check("Custom warning percentage loaded correctly", reserve_tols["warning_pct"] == 4.5)
check("Custom critical percentage loaded correctly", reserve_tols["critical_pct"] == 7.5)

# Clean up
for db in ["data/actuarecette.db", "data/actuarecette_v2.db"]:
    if os.path.exists(db):
        conn = sqlite3.connect(db)
        conn.execute("DELETE FROM regles_recette_dynamiques WHERE id_regle LIKE 'MOCK-%'")
        conn.execute("DELETE FROM portefeuilles_seuils_domaines WHERE id_portefeuille='LOB_MRH_HAB' AND domaine='Réserve'")
        conn.commit()
        conn.close()

# Summary
print(f"\n{'='*50}")
total = passed + failed
print(f"  Total: {total} | Pass: {passed} | Fail: {failed}")
if failed == 0:
    print("  >>> MULTI-DOMAINES VALIDATED <<<")
else:
    print(f"  WARNING: {failed} test(s) failed")
print(f"{'='*50}")
sys.exit(0 if failed == 0 else 1)

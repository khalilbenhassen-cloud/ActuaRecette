"""Test Phase 2b.4 \u2014 R\u00e9f\u00e9rentiel anomalies + Cycle de vie exercices."""
import sys
sys.stdout.reconfigure(encoding="utf-8")

import os
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

# 1. Schema SQL integrity
print("\n=== 1. Schema SQL ===")
schema = open("data/schema.sql", "r", encoding="utf-8").read()
check("anomaly_categories table", "CREATE TABLE IF NOT EXISTS anomaly_categories" in schema)
check("exercices table", "CREATE TABLE IF NOT EXISTS exercices" in schema)
check("ARRONDI_DECIMAL seed", "ARRONDI_DECIMAL" in schema)
check("SEUIL_PLANCHER seed", "SEUIL_PLANCHER" in schema)
check("FORMULE_JEUNE_CONDUCTEUR seed", "FORMULE_JEUNE_CONDUCTEUR" in schema)
check("COEFF_PUISSANCE seed", "COEFF_PUISSANCE" in schema)
check("ECART_NON_REPERTORIE seed", "ECART_NON_REPERTORIE" in schema)
check("DONNEE_CORROMPUE seed", "DONNEE_CORROMPUE" in schema)
check("exercice statut column", "OUVERT, CLOTURE, VERROUILLE" in schema)
check("idx_exercices_annee_mois index", "idx_exercices_annee_mois" in schema)
check("idx_anomaly_cat_severite index", "idx_anomaly_cat_severite" in schema)

# 2. Schema executes in SQLite
print("\n=== 2. SQLite Execution ===")
import sqlite3
import tempfile
db_file = os.path.join(tempfile.gettempdir(), "test_schema_2b4.db")
try:
    conn = sqlite3.connect(db_file)
    conn.executescript(schema)
    
    # Verify tables
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    check("anomaly_categories exists in DB", "anomaly_categories" in tables)
    check("exercices exists in DB", "exercices" in tables)
    
    # Verify seed data
    cats = conn.execute("SELECT COUNT(*) FROM anomaly_categories").fetchone()[0]
    check(f"6 anomaly categories seeded (got {cats})", cats == 6)
    
    # Verify exercice lifecycle
    conn.execute("INSERT INTO exercices (id_exercice, annee, mois, libelle, statut) VALUES ('EX_TEST', 2026, 6, 'Test', 'OUVERT')")
    conn.execute("UPDATE exercices SET statut = 'CLOTURE' WHERE id_exercice = 'EX_TEST'")
    conn.execute("UPDATE exercices SET statut = 'VERROUILLE' WHERE id_exercice = 'EX_TEST'")
    row = conn.execute("SELECT statut FROM exercices WHERE id_exercice = 'EX_TEST'").fetchone()
    check("Exercice lifecycle OUVERT->CLOTURE->VERROUILLE", row[0] == "VERROUILLE")
    
    conn.close()
    os.remove(db_file)
except Exception as e:
    check(f"SQLite execution", False, str(e))

# 3. DONNEE_CORROMPUE detection in variance_analyzer
print("\n=== 3. DONNEE_CORROMPUE Detection ===")
import pandas as pd
import numpy as np
from src.variance_analyzer import calculate_variances

# Create test data with corrupt entries
test_df = pd.DataFrame({
    "ID_CLIENT": ["C001", "C002", "C003", "C004"],
    "PRIME_ACTU": [100.0, np.nan, -50.0, 200.0],
    "PRIME_DSI": [100.01, 150.0, 100.0, 0.0],
})

result = calculate_variances(test_df, "PRIME_ACTU", "PRIME_DSI", tolerance=0.10)
cats = result["anomaly_category"].tolist()

check("C001 normal (arrondi)", "arrondi" in cats[0].lower())
check("C002 NaN detected as CORROMPUE", "corrompue" in cats[1].lower() or "manquante" in cats[1].lower())
check("C003 negative detected as CORROMPUE", "corrompue" in cats[2].lower() or "manquante" in cats[2].lower())
# C004 has ref=200, prod=0 -> large deviation, should be a normal anomaly
check("C004 normal deviation", "corrompue" not in cats[3].lower())

# 4. API endpoints registered
print("\n=== 4. API Endpoints ===")
from api.main import app
routes = [r.path for r in app.routes]
check("GET /anomaly-categories", "/anomaly-categories" in routes)
check("GET /exercices", "/exercices" in routes)
check("POST /exercices", "/exercices" in routes)
check("POST /exercices/{id_exercice}/close", "/exercices/{id_exercice}/close" in routes)
check("POST /exercices/{id_exercice}/lock", "/exercices/{id_exercice}/lock" in routes)

# Bilan
print(f"\n{'='*50}")
total = passed + failed
print(f"  Total: {total} tests | Pass: {passed} | Fail: {failed}")
if failed == 0:
    print("  >>> PHASE 2b.4 VALIDATED <<<")
else:
    print(f"  WARNING: {failed} test(s) failed")
print(f"{'='*50}")
sys.exit(0 if failed == 0 else 1)

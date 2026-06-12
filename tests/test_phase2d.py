"""Test Phase 2d \u2014 Intelligence actuarielle (Root cause + Tendances)."""
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

# ====================================================================
# 1. Root Cause Engine
# ====================================================================
print("\n=== 1. Root Cause Engine \u2014 Imports ===")
from src.root_cause_engine import (
    decompose_variance, detect_systematic_patterns,
    PATTERN_THRESHOLDS
)
check("decompose_variance importable", callable(decompose_variance))
check("detect_systematic_patterns importable", callable(detect_systematic_patterns))
check("PATTERN_THRESHOLDS has entries", len(PATTERN_THRESHOLDS) >= 3)

# 2. Decomposition test \u2014 normal case
print("\n=== 2. Decomposition \u2014 Normal ===")
ref_row = {"PRIME_BASE": 200.0, "COEFF_AGE": 1.50, "COEFF_CRM": 1.00, "COEFF_PUISSANCE": 1.30, "COEFF_ZONE": 1.50}
prod_row = {"PRIME_BASE": 200.0, "COEFF_AGE": 1.50, "COEFF_CRM": 1.00, "COEFF_PUISSANCE": 1.30, "COEFF_ZONE": 1.50}
coefficients = ["COEFF_AGE", "COEFF_CRM", "COEFF_PUISSANCE", "COEFF_ZONE"]

result = decompose_variance(ref_row, prod_row, coefficients)
check("Zero ecart when identical", abs(result["ecart_total"]) < 0.01)
check("Has decomposition", len(result["decomposition"]) == 4)
check("Has diagnostic", len(result["diagnostic"]) > 0)

# 3. Decomposition test \u2014 DOUBLE_APPLICATION pattern
print("\n=== 3. Decomposition \u2014 Double Application ===")
prod_double = {"PRIME_BASE": 200.0, "COEFF_AGE": 1.50, "COEFF_CRM": 1.00, "COEFF_PUISSANCE": 1.69, "COEFF_ZONE": 1.50}
# 1.69 \u2248 1.30\u00b2 = 1.69 -> DOUBLE_APPLICATION

result = decompose_variance(ref_row, prod_double, coefficients)
check(f"Ecart detected: {result['ecart_total']}\u20ac", abs(result["ecart_total"]) > 1.0)
check(f"Coefficient fautif = COEFF_PUISSANCE", result["coefficient_fautif"] == "COEFF_PUISSANCE")
check(f"Pattern = DOUBLE_APPLICATION", result["pattern"] == "DOUBLE_APPLICATION")
check("Diagnostic mentions double", "double" in result["diagnostic"].lower() or "1.69" in result["diagnostic"])

# 4. Systematic patterns
print("\n=== 4. Systematic Patterns ===")
import pandas as pd

anomalies_df = pd.DataFrame({
    "coefficient_fautif": ["COEFF_PUISSANCE"] * 5 + ["COEFF_AGE"] * 2,
    "ecart_total": [18.5, 19.2, 17.8, 18.9, 20.1, 5.0, 4.5],
    "pattern": ["DOUBLE_APPLICATION"] * 5 + ["ECART_COEFFICIENT"] * 2,
})

patterns = detect_systematic_patterns(anomalies_df)
check("Detected 2 pattern groups", len(patterns) == 2)
check("COEFF_PUISSANCE is #1 by impact", patterns[0]["coefficient"] == "COEFF_PUISSANCE")
check(f"5 dossiers affect\u00e9s", patterns[0]["nb_dossiers_affectes"] == 5)
check("Has recommendation", len(patterns[0]["recommandation"]) > 0)

# ====================================================================
# 5. Trend Analyzer
# ====================================================================
print("\n=== 5. Trend Analyzer \u2014 Imports ===")
from src.trend_analyzer import compute_trend, detect_deployment_correlation, compute_coefficient_impact
check("compute_trend importable", callable(compute_trend))
check("detect_deployment_correlation importable", callable(detect_deployment_correlation))
check("compute_coefficient_impact importable", callable(compute_coefficient_impact))

# 6. Trend computation
print("\n=== 6. Trend Computation ===")
# Improving trend
snapshots = [
    {"periode": "2026-01", "taux_conformite": 90.0, "version_moteur_dsi": "v3.0"},
    {"periode": "2026-02", "taux_conformite": 92.0, "version_moteur_dsi": "v3.0"},
    {"periode": "2026-03", "taux_conformite": 94.0, "version_moteur_dsi": "v3.0"},
    {"periode": "2026-04", "taux_conformite": 95.5, "version_moteur_dsi": "v3.1"},
    {"periode": "2026-05", "taux_conformite": 97.0, "version_moteur_dsi": "v3.1"},
    {"periode": "2026-06", "taux_conformite": 98.5, "version_moteur_dsi": "v3.1"},
]

trend = compute_trend(snapshots, "taux_conformite")
check(f"Trend = {trend['trend']}", trend["trend"] == "IMPROVING")
check(f"Slope > 0 ({trend['slope']})", trend["slope"] > 0)
check(f"R\u00b2 > 0.9 ({trend['r_squared']})", trend["r_squared"] > 0.9)
check(f"Current = 98.5", trend["current_value"] == 98.5)
check(f"Projection M+3 > 98.5", trend["projection_m3"] > 98.5)

# Degrading trend
degrading = [
    {"periode": "2026-01", "taux_conformite": 99.0, "version_moteur_dsi": "v3.0"},
    {"periode": "2026-02", "taux_conformite": 98.0, "version_moteur_dsi": "v3.0"},
    {"periode": "2026-03", "taux_conformite": 96.0, "version_moteur_dsi": "v3.1"},
    {"periode": "2026-04", "taux_conformite": 93.0, "version_moteur_dsi": "v3.2"},
    {"periode": "2026-05", "taux_conformite": 89.0, "version_moteur_dsi": "v3.2"},
]
trend_d = compute_trend(degrading, "taux_conformite")
check(f"Degrading trend = {trend_d['trend']}", trend_d["trend"] == "DEGRADING")
check(f"Slope < 0 ({trend_d['slope']})", trend_d["slope"] < 0)
check("Alert triggered", trend_d["alert"] is not None)

# 7. Deployment correlation
print("\n=== 7. Deployment Correlation ===")
corrs = detect_deployment_correlation(degrading, "taux_conformite", degradation_threshold=2.0)
check(f"Correlations detected: {len(corrs)}", len(corrs) >= 1)
if corrs:
    check("First corr has version_apres", "version_apres" in corrs[0])
    check("Delta is negative", corrs[0]["delta"] < 0)
    check("Has diagnostic", len(corrs[0]["diagnostic"]) > 0)

# 8. Coefficient impact
print("\n=== 8. Coefficient Impact ===")
impact_snapshots = [
    {"impact_par_coefficient": '{"COEFF_PUISSANCE": 500, "COEFF_AGE": 100}'},
    {"impact_par_coefficient": '{"COEFF_PUISSANCE": 369.50, "COEFF_AGE": 110}'},
]
impacts = compute_coefficient_impact(impact_snapshots)
check(f"2 coefficients", len(impacts) == 2)
check("COEFF_PUISSANCE is #1", impacts[0]["coefficient"] == "COEFF_PUISSANCE")
check(f"Total impact PUISS = {impacts[0]['impact_euros']}", impacts[0]["impact_euros"] == 869.50)

# ====================================================================
# 9. Schema SQL
# ====================================================================
print("\n=== 9. Schema SQL ===")
import sqlite3, tempfile
schema = open("data/schema.sql", "r", encoding="utf-8").read()
check("tarif_structure table", "CREATE TABLE IF NOT EXISTS tarif_structure" in schema)
check("trend_snapshots table", "CREATE TABLE IF NOT EXISTS trend_snapshots" in schema)
check("COEFF_AGE seed", "COEFF_AGE" in schema)
check("COEFF_PUISSANCE seed", "COEFF_PUISSANCE" in schema)

db_file = os.path.join(tempfile.gettempdir(), "test_schema_2d.db")
conn = sqlite3.connect(db_file)
conn.executescript(schema)
tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
check("tarif_structure exists in DB", "tarif_structure" in tables)
check("trend_snapshots exists in DB", "trend_snapshots" in tables)

coeffs = conn.execute("SELECT COUNT(*) FROM tarif_structure WHERE id_portefeuille='LOB_AUTO_PART'").fetchone()[0]
check(f"4 coefficients for AUTO_PART (got {coeffs})", coeffs == 4)
conn.close()
os.remove(db_file)

# Bilan
print(f"\n{'='*50}")
total = passed + failed
print(f"  Total: {total} tests | Pass: {passed} | Fail: {failed}")
if failed == 0:
    print("  >>> PHASE 2d VALIDATED <<<")
else:
    print(f"  WARNING: {failed} test(s) failed")
print(f"{'='*50}")
sys.exit(0 if failed == 0 else 1)

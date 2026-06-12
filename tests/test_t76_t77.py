"""Test T76+T77: Trend snapshot hook + Trend analyzer complete."""
import sys
sys.stdout.reconfigure(encoding="utf-8")
import os

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


# ============================================================
# T77: trend_analyzer.py complete
# ============================================================
print("=== T77: trend_analyzer.py ===")

from src.trend_analyzer import (
    compute_trend,
    detect_deployment_correlation,
    compute_coefficient_impact,
    save_trend_snapshot,
    get_trend_data,
    get_coefficient_trends,
)

check("compute_trend importable", callable(compute_trend))
check("detect_deployment_correlation importable", callable(detect_deployment_correlation))
check("compute_coefficient_impact importable", callable(compute_coefficient_impact))
check("save_trend_snapshot importable", callable(save_trend_snapshot))
check("get_trend_data importable", callable(get_trend_data))
check("get_coefficient_trends importable", callable(get_coefficient_trends))

# Test compute_trend with mock data
mock_snapshots = [
    {"taux_conformite": 95.0, "nb_anomalies": 5, "version_moteur_dsi": "v1.0", "periode": "2025-01"},
    {"taux_conformite": 93.0, "nb_anomalies": 7, "version_moteur_dsi": "v1.0", "periode": "2025-02"},
    {"taux_conformite": 90.0, "nb_anomalies": 10, "version_moteur_dsi": "v1.1", "periode": "2025-03"},
    {"taux_conformite": 88.0, "nb_anomalies": 12, "version_moteur_dsi": "v1.1", "periode": "2025-04"},
    {"taux_conformite": 85.0, "nb_anomalies": 15, "version_moteur_dsi": "v1.2", "periode": "2025-05"},
    {"taux_conformite": 80.0, "nb_anomalies": 20, "version_moteur_dsi": "v1.3", "periode": "2025-06"},
]

trend = compute_trend(mock_snapshots)
check("trend has metric", "metric" in trend)
check("trend has current_value", "current_value" in trend)
check("trend has trend direction", "trend" in trend)
check("trend has slope", "slope" in trend)
check("trend has r_squared", "r_squared" in trend)
check("trend direction is DEGRADING", trend["trend"] == "DEGRADING")
check("slope is negative", trend["slope"] < 0)
check("current_value is 80.0", trend["current_value"] == 80.0)

# Test empty snapshots
empty_trend = compute_trend([])
check("empty trend is STABLE", empty_trend["trend"] == "STABLE")

# Test detect_deployment_correlation
correlations = detect_deployment_correlation(mock_snapshots, degradation_threshold=2.0)
check("correlations is list", isinstance(correlations, list))
check("detected v1.0->v1.1 degradation", len(correlations) >= 1)

# Test compute_coefficient_impact
mock_snap_with_impact = [
    {"impact_par_coefficient": {"COEFF_AGE": 100.0, "COEFF_ZONE": 50.0}},
    {"impact_par_coefficient": '{"COEFF_AGE": 200.0, "COEFF_CRM": 75.0}'},
]
impacts = compute_coefficient_impact(mock_snap_with_impact)
check("impacts is list", isinstance(impacts, list))
check("COEFF_AGE first (highest)", impacts[0]["coefficient"] == "COEFF_AGE" if impacts else False)
check("COEFF_AGE total 300", impacts[0]["impact_euros"] == 300.0 if impacts else False)

# Test get_coefficient_trends
coeff_trends = get_coefficient_trends([
    {"periode": "2025-01", "impact_par_coefficient": {"COEFF_AGE": 100.0}},
    {"periode": "2025-02", "impact_par_coefficient": {"COEFF_AGE": 150.0, "COEFF_CRM": 50.0}},
])
check("coeff_trends returns dict", isinstance(coeff_trends, dict))
check("COEFF_AGE in trends", "COEFF_AGE" in coeff_trends)
check("COEFF_AGE has 2 entries", len(coeff_trends.get("COEFF_AGE", [])) == 2)

# ============================================================
# T76: Hook snapshot in certify endpoint
# ============================================================
print("\n=== T76: Certification snapshot hook ===")

api_path = os.path.join(ROOT, "api", "routes", "workflow.py")
with open(api_path, "r", encoding="utf-8") as f:
    api = f.read()

certify_block = api.split("def certify_run")[1].split("def reject_run")[0]

check("save_trend_snapshot in certify", "save_trend_snapshot" in certify_block)
check("import trend_analyzer in certify", "from src.trend_analyzer import" in api)
check("lob_id extraction", "lob_id" in certify_block)
check("periode extraction", "periode" in certify_block)
check("version_moteur passed", "version_moteur" in certify_block)
check("try/except for robustness", "snap_err" in certify_block)
check("non-blocking if error", "Trend snapshot skipped" in certify_block)

# Source code checks
ta_path = os.path.join(ROOT, "src", "trend_analyzer.py")
with open(ta_path, "r", encoding="utf-8") as f:
    ta_src = f.read()

check("has _get_conn()", "def _get_conn" in ta_src)
check("has save_trend_snapshot()", "def save_trend_snapshot" in ta_src)
check("has get_trend_data()", "def get_trend_data" in ta_src)
check("uses sqlite3", "sqlite3" in ta_src)
check("INSERT OR REPLACE", "INSERT OR REPLACE" in ta_src)
check("WAL mode", "PRAGMA journal_mode=WAL" in ta_src)

# Summary
print(f"\n{'='*50}")
total = passed + failed
print(f"  Total: {total} | Pass: {passed} | Fail: {failed}")
if failed == 0:
    print("  >>> T76+T77 VALIDATED <<<")
else:
    print(f"  WARNING: {failed} test(s) failed")
print(f"{'='*50}")
sys.exit(0 if failed == 0 else 1)

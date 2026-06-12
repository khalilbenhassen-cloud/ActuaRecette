"""Test T65+T66: Tolerance par LOB + Detection runs parasites."""
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
# T65: Tolerance Manager
# ============================================================
print("=== T65: Tolerance Manager ===")

from src.tolerance_manager import (
    get_lob_tolerance,
    get_all_tolerances,
    update_lob_tolerance,
    DEFAULT_TOLERANCES,
)

check("get_lob_tolerance importable", callable(get_lob_tolerance))
check("get_all_tolerances importable", callable(get_all_tolerances))
check("update_lob_tolerance importable", callable(update_lob_tolerance))
check("DEFAULT_TOLERANCES has entries", len(DEFAULT_TOLERANCES) >= 3)

# Test default fallback
tol = get_lob_tolerance("LOB_AUTO_PART")
check("LOB_AUTO_PART has seuil_materialite_pct", "seuil_materialite_pct" in tol)
check("LOB_AUTO_PART has tolerance_unitaire", "tolerance_unitaire" in tol)
check("seuil_materialite_pct is float", isinstance(tol["seuil_materialite_pct"], float))
check("tolerance_unitaire is float", isinstance(tol["tolerance_unitaire"], float))

# Unknown LOB returns defaults
tol_unknown = get_lob_tolerance("LOB_UNKNOWN_XYZ")
check("unknown LOB returns defaults", "seuil_materialite_pct" in tol_unknown)

# get_all_tolerances returns list
all_tol = get_all_tolerances()
check("get_all_tolerances returns list", isinstance(all_tol, list))
check("list has entries", len(all_tol) >= 1)

# API endpoints
api_path = os.path.join(ROOT, "api", "main.py")
with open(api_path, "r", encoding="utf-8") as f:
    api = f.read()
routes_dir = os.path.join(ROOT, "api", "routes")
for _rf in os.listdir(routes_dir):
    if _rf.endswith(".py") and _rf != "__init__.py":
        with open(os.path.join(routes_dir, _rf), "r", encoding="utf-8") as f:
            api += "\n" + f.read()

check("GET /tolerances route", 'get("/tolerances")' in api)
check("GET /tolerances/{lob_id}", 'get("/tolerances/{lob_id}")' in api)
check("PUT /tolerances/{lob_id}", 'put("/tolerances/{lob_id}")' in api)
check("Manager-only guard on PUT", "Responsable MOA" in api)

# ============================================================
# T66: Parasitic Runs Detection
# ============================================================
print("\n=== T66: Parasitic Runs Detection ===")

from src.tolerance_manager import detect_parasitic_runs

check("detect_parasitic_runs importable", callable(detect_parasitic_runs))

# Test empty run detection
test_runs = [
    {"run_id": "r1", "run_name": "Test Run 1", "total_cases": 0, "success_rate_pct": 0, "timestamp": "2026-01-01T10:00:00"},
    {"run_id": "r2", "run_name": "Test Run 2", "total_cases": 5, "success_rate_pct": 80.0, "timestamp": "2026-01-01T11:00:00"},
    {"run_id": "r3", "run_name": "Test Run 3", "total_cases": 200, "success_rate_pct": 100.0, "timestamp": "2026-01-01T12:00:00"},
    {"run_id": "r4", "run_name": "Test Run 2", "total_cases": 50, "success_rate_pct": 95.0, "timestamp": "2026-01-01T11:05:00"},
    {"run_id": "r5", "run_name": "Good Run", "total_cases": 100, "success_rate_pct": 97.5, "timestamp": "2026-01-02T09:00:00"},
]

suspects = detect_parasitic_runs(test_runs)
check("returns list", isinstance(suspects, list))

# r1 should be detected (0 cases)
r1_suspects = [s for s in suspects if s["run_id"] == "r1"]
check("r1 detected (empty)", len(r1_suspects) == 1)
check("r1 has VIDE reason", any("VIDE" in r for r in r1_suspects[0]["reasons"]) if r1_suspects else False)
check("r1 severity CRITICAL", r1_suspects[0]["severity"] == "CRITICAL" if r1_suspects else False)

# r2 should be detected (too few cases)
r2_suspects = [s for s in suspects if s["run_id"] == "r2"]
check("r2 detected (insufficient)", len(r2_suspects) == 1)

# r3 should be detected (100% on 200 cases)
r3_suspects = [s for s in suspects if s["run_id"] == "r3"]
check("r3 detected (100% suspect)", len(r3_suspects) == 1)

# r4 should be detected (duplicate of r2 within 10 min)
r4_suspects = [s for s in suspects if s["run_id"] == "r4"]
check("r4 detected (duplicate)", len(r4_suspects) == 1)
check("r4 has DOUBLON reason", any("DOUBLON" in r for r in r4_suspects[0]["reasons"]) if r4_suspects else False)

# r5 should NOT be detected
r5_suspects = [s for s in suspects if s["run_id"] == "r5"]
check("r5 not detected (clean)", len(r5_suspects) == 0)

# API endpoint
check("GET /runs/parasitic route", 'get("/runs/parasitic")' in api)
check("detect_parasitic_runs used in API", "detect_parasitic_runs" in api)

# Summary
print(f"\n{'='*50}")
total = passed + failed
print(f"  Total: {total} | Pass: {passed} | Fail: {failed}")
if failed == 0:
    print("  >>> T65+T66 VALIDATED <<<")
else:
    print(f"  WARNING: {failed} test(s) failed")
print(f"{'='*50}")
sys.exit(0 if failed == 0 else 1)

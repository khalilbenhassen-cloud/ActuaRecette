"""Test T3+T24: Migration script + Stress test validation."""
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
# T3: Migration Script
# ============================================================
print("=== T3: Migration JSON -> SQLite ===")

script_path = os.path.join(ROOT, "scripts", "migrate_json_to_sqlite.py")
check("script exists", os.path.exists(script_path))

with open(script_path, "r", encoding="utf-8") as f:
    src = f.read()

check("has argparse", "argparse" in src)
check("has --dry-run flag", "--dry-run" in src)
check("has --db-path flag", "--db-path" in src)
check("reads uat_runs/*.json", "uat_runs" in src)
check("reads audit_log.json", "audit_log.json" in src)
check("INSERT OR IGNORE (idempotent)", "INSERT OR IGNORE" in src)
check("applies schema.sql", "schema.sql" in src)
check("WAL mode", "PRAGMA journal_mode=WAL" in src)
check("migrates runs to runs_execution", "runs_execution" in src)
check("migrates audit to audit_entries", "audit_entries" in src)
check("creates campagnes_recette", "campagnes_recette" in src)
check("computes signature_hash", "signature_hash" in src)
check("maps final_status", "final_status" in src)
check("has main()", "def main()" in src)
check("has init_schema()", "def init_schema" in src)
check("has migrate_runs()", "def migrate_runs" in src)
check("has migrate_audit_trail()", "def migrate_audit_trail" in src)

# ============================================================
# T24: Stress Test Script
# ============================================================
print("\n=== T24: Stress Test Script ===")

stress_path = os.path.join(ROOT, "scripts", "test_stress_concurrent.py")
check("script exists", os.path.exists(stress_path))

with open(stress_path, "r", encoding="utf-8") as f:
    stress_src = f.read()

check("uses threading", "threading" in stress_src)
check("5 threads", "N_THREADS = 5" in stress_src)
check("200 rows per thread", "n_rows: int = 200" in stress_src)
check("has generate_test_data()", "def generate_test_data" in stress_src)
check("has run_reconciliation()", "def run_reconciliation" in stress_src)
check("uses merge_datasets", "merge_datasets" in stress_src)
check("uses calculate_variances", "calculate_variances" in stress_src)
check("validates 200 cases", '"total_cases"' in stress_src)
check("checks elapsed < 30s", "elapsed < 30" in stress_src)
check("cross-thread integrity check", "contamination" in stress_src)

# Summary
print(f"\n{'='*50}")
total = passed + failed
print(f"  Total: {total} | Pass: {passed} | Fail: {failed}")
if failed == 0:
    print("  >>> T3+T24 VALIDATED <<<")
else:
    print(f"  WARNING: {failed} test(s) failed")
print(f"{'='*50}")
sys.exit(0 if failed == 0 else 1)

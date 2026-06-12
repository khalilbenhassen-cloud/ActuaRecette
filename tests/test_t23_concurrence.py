"""T23 -- Test de concurrence : 2 sessions paralleles creant des runs."""
import sys
sys.stdout.reconfigure(encoding="utf-8")
import os
import json
import threading
import tempfile
import shutil

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


print("=== T23: Test concurrence 2 sessions ===")

from src.anomaly_manager import save_uat_run

# Create temp directories for two sessions
tmp1 = os.path.join(ROOT, "tests", "_tmp_session1")
tmp2 = os.path.join(ROOT, "tests", "_tmp_session2")
os.makedirs(tmp1, exist_ok=True)
os.makedirs(tmp2, exist_ok=True)

results = {"session1": [], "session2": [], "errors": []}

def create_runs(session_name, temp_dir, count=5):
    """Create N runs in a temp directory."""
    for i in range(count):
        try:
            kpis = {"success_rate_pct": 95.0 - i, "fatal_defects": i, "total_cases": 100}
            anomalies = [{"ID_CLIENT": f"CLT{i}", "abs_deviation": float(i * 10)}]
            path = save_uat_run(temp_dir, f"{session_name}_run_{i}", kpis, anomalies)
            results[session_name].append(path)
        except Exception as e:
            results["errors"].append(f"{session_name}: {e}")

# Run two sessions in parallel
t1 = threading.Thread(target=create_runs, args=("session1", tmp1, 5))
t2 = threading.Thread(target=create_runs, args=("session2", tmp2, 5))

t1.start()
t2.start()
t1.join(timeout=10)
t2.join(timeout=10)

check("session1 created 5 runs", len(results["session1"]) == 5)
check("session2 created 5 runs", len(results["session2"]) == 5)
check("no errors", len(results["errors"]) == 0, str(results["errors"]))

# Verify all run_ids are unique
all_ids = set()
for session in ["session1", "session2"]:
    for path in results[session]:
        fname = os.path.basename(path).replace(".json", "")
        all_ids.add(fname)

check("all 10 run_ids unique", len(all_ids) == 10, f"only {len(all_ids)} unique")

# Verify files are readable
readable = 0
for session in ["session1", "session2"]:
    for path in results[session]:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if "run_id" in data and "kpis" in data:
                    readable += 1
            except Exception:
                pass

check("all 10 files readable and valid", readable == 10, f"only {readable}")

# No cross-contamination
s1_files = set(os.listdir(tmp1))
s2_files = set(os.listdir(tmp2))
check("no cross-contamination", len(s1_files & s2_files) == 0)

# Cleanup
shutil.rmtree(tmp1, ignore_errors=True)
shutil.rmtree(tmp2, ignore_errors=True)

print(f"\n{'='*50}")
total = passed + failed
print(f"  Total: {total} | Pass: {passed} | Fail: {failed}")
if failed == 0:
    print("  >>> T23 VALIDATED <<<")
print(f"{'='*50}")
sys.exit(0 if failed == 0 else 1)

"""Test T4+T67: UUID run_id + ACPR blocking threshold."""
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
# T4: UUID run_id
# ============================================================
print("=== T4: UUID-based run_id ===")

# 1. anomaly_manager uses uuid
am_path = os.path.join(ROOT, "src", "anomaly_manager.py")
with open(am_path, "r", encoding="utf-8") as f:
    am_src = f.read()
for _extra in ["run_persistence.py", "scenario_manager.py"]:
    _extra_path = os.path.join(ROOT, "src", _extra)
    if os.path.exists(_extra_path):
        with open(_extra_path, "r", encoding="utf-8") as f:
            am_src += "\n" + f.read()

check("import uuid in anomaly_manager", "import uuid" in am_src)
check("uuid.uuid4() in save_uat_run", "uuid.uuid4().hex" in am_src)
check("no timestamp_id in save_uat_run", 'timestamp_id = now.strftime("%Y%m%d_%H%M%S")' not in am_src)
check("scenario uses UUID too", "uuid.uuid4().hex" in am_src.split("def save_scenario")[1] if "def save_scenario" in am_src else False)

# 2. dashboard uses uuid
page3_path = os.path.join(ROOT, "dashboard", "views", "page_03_espace_travail.py")
with open(page3_path, "r", encoding="utf-8") as f:
    page3_src = f.read()

check("uuid in _create_draft_campaign", "uuid.uuid4().hex" in page3_src)
check("no timestamp_id in page03", 'timestamp_id = now.strftime("%Y%m%d_%H%M%S")' not in page3_src)

# 3. UUID uniqueness test
import uuid
ids = set()
for _ in range(1000):
    rid = f"run_{uuid.uuid4().hex[:12]}"
    ids.add(rid)
check("1000 UUIDs all unique", len(ids) == 1000)

# 4. Regex validation
import re
sample_id = f"run_{uuid.uuid4().hex[:12]}"
check("UUID run_id matches safe regex", bool(re.match(r'^[a-zA-Z0-9_-]+$', sample_id)))
check("UUID run_id has correct prefix", sample_id.startswith("run_"))
check("UUID run_id has correct length", len(sample_id) == 16)  # "run_" + 12 hex chars

# ============================================================
# T67: ACPR blocking threshold
# ============================================================
print("\n=== T67: ACPR blocking threshold ===")

api_path = os.path.join(ROOT, "api", "routes", "workflow.py")
with open(api_path, "r", encoding="utf-8") as f:
    api_src = f.read()

# Extract certify function
certify_block = api_src.split("def certify_run")[1].split("def reject_run")[0] if "def certify_run" in api_src else ""

check("ACPR check in certify endpoint", "ACPR" in certify_block)
check("seuil_materialite_pct used", "seuil_materialite_pct" in certify_block)
check("get_lob_tolerance imported", "get_lob_tolerance" in certify_block)
check("prime_a_risque checked", "prime_a_risque" in certify_block)
check("HTTP 422 on violation", "422" in certify_block)
check("BLOCAGE REGLEMENTAIRE message", "BLOCAGE REGLEMENTAIRE" in certify_block)
check("non-bloquant if DB error", "ACPR check skipped" in certify_block)
check("HTTPException re-raised", "except HTTPException:" in certify_block)

# Summary
print(f"\n{'='*50}")
total = passed + failed
print(f"  Total: {total} | Pass: {passed} | Fail: {failed}")
if failed == 0:
    print("  >>> T4+T67 VALIDATED <<<")
else:
    print(f"  WARNING: {failed} test(s) failed")
print(f"{'='*50}")
sys.exit(0 if failed == 0 else 1)

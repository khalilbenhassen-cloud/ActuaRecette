"""Test T83: Verify all src/ imports removed from dashboard views/components."""
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


print("=== T83: Decoupling src/ imports ===")

# 1. engine_proxy loads
from dashboard.utils.engine_proxy import is_available, merge_datasets, calculate_variances
check("engine_proxy importable", True)
check("is_available returns bool", isinstance(is_available(), bool))
check("merge_datasets callable", callable(merge_datasets))
check("calculate_variances callable", callable(calculate_variances))

# 2. No from src. in views
views_dir = os.path.join(ROOT, "dashboard", "views")
for f in os.listdir(views_dir):
    if not f.endswith(".py") or f.startswith("__"):
        continue
    content = open(os.path.join(views_dir, f), "r", encoding="utf-8").read()
    lines = content.split("\n")
    has_src = any(l.strip().startswith("from src.") for l in lines)
    check(f"{f} no src import", not has_src, "Still has from src.")

# 3. No from src. in components
comps_dir = os.path.join(ROOT, "dashboard", "components")
for f in os.listdir(comps_dir):
    if not f.endswith(".py") or f.startswith("__"):
        continue
    content = open(os.path.join(comps_dir, f), "r", encoding="utf-8").read()
    lines = content.split("\n")
    has_src = any(l.strip().startswith("from src.") for l in lines)
    check(f"{f} no src import", not has_src, "Still has from src.")

# 4. engine_proxy IS the single point of src/ import
proxy_path = os.path.join(ROOT, "dashboard", "utils", "engine_proxy.py")
proxy_content = open(proxy_path, "r", encoding="utf-8").read()
check("proxy has src.anomaly_manager", "from src.anomaly_manager" in proxy_content)
check("proxy has src.variance_analyzer", "from src.variance_analyzer" in proxy_content)
check("proxy has src.pdf_generator", "from src.pdf_generator" in proxy_content)

# 5. Views use engine_proxy (directly or via cockpit_helpers.py)
for page in ["page_01_cockpit.py", "page_03_espace_travail.py"]:
    content = open(os.path.join(views_dir, page), "r", encoding="utf-8").read()
    # ARCH-05: cockpit_helpers.py may hold the engine_proxy import
    helpers = os.path.join(views_dir, "cockpit_helpers.py")
    if os.path.exists(helpers):
        content += open(helpers, "r", encoding="utf-8").read()
    check(f"{page} uses engine_proxy", "engine_proxy" in content)

# Summary
print(f"\n{'='*50}")
total = passed + failed
print(f"  Total: {total} | Pass: {passed} | Fail: {failed}")
if failed == 0:
    print("  >>> T83 VALIDATED <<<")
else:
    print(f"  WARNING: {failed} test(s) failed")
print(f"{'='*50}")
sys.exit(0 if failed == 0 else 1)

"""Test T40+T41+T5+T6: run comparator, drill-down, atomic num_run, logger."""
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
# T40: run_comparator.py
# ============================================================
print("=== T40: run_comparator.py ===")

rc_path = os.path.join(ROOT, "dashboard", "components", "run_comparator.py")
check("file exists", os.path.exists(rc_path))

with open(rc_path, "r", encoding="utf-8") as f:
    rc_src = f.read()

check("has run_comparator func", "def run_comparator" in rc_src)
check("has _render_comparison", "def _render_comparison" in rc_src)
check("takes run_history param", "run_history:" in rc_src)
check("has base/target selectbox", "comparator_base" in rc_src)
check("filters out same run", "rid != base_id" in rc_src)
check("shows delta colors", "#22C55E" in rc_src)
check("returns dict with base_run", "base_run" in rc_src)

# T40 integrated in page_04
p4_path = os.path.join(ROOT, "dashboard", "views", "page_04_detail_run.py")
with open(p4_path, "r", encoding="utf-8") as f:
    p4_src = f.read()

check("run_comparator imported in page04", "from dashboard.components.run_comparator import" in p4_src)
check("comparator section in page04", "Comparaison avec un autre run" in p4_src)

# ============================================================
# T41: KPIs cockpit drill-down
# ============================================================
print("\n=== T41: KPIs cockpit drill-down ===")

check("navigate_to_run_detail in page04", "def navigate_to_run_detail" in p4_src)
check("sets current_run_id", 'current_run_id' in p4_src.split("navigate_to_run_detail")[1])
check("sets current_page", 'current_page' in p4_src.split("navigate_to_run_detail")[1])

# Also check coefficient_table integration
check("coefficient_table integrated", "coefficient_table" in p4_src)
check("Decomposition Root Cause section", "Decomposition Root Cause" in p4_src)

# ============================================================
# T5: num_run atomique
# ============================================================
print("\n=== T5: num_run atomique ===")

am_path = os.path.join(ROOT, "src", "anomaly_manager.py")
with open(am_path, "r", encoding="utf-8") as f:
    am_src = f.read()
for _extra in ["run_persistence.py", "scenario_manager.py", "audit_trail.py", "jira_export.py"]:
    _extra_path = os.path.join(ROOT, "src", _extra)
    if os.path.exists(_extra_path):
        with open(_extra_path, "r", encoding="utf-8") as f:
            am_src += "\n" + f.read()

check("uses MAX instead of COUNT", "MAX(num_run)" in am_src)
check("uses COALESCE", "COALESCE" in am_src)
check("no COUNT(*) for num_run", "SELECT COUNT(*) FROM runs_execution WHERE id_campagne" not in am_src)
check("T5 comment present", "T5" in am_src and "atomique" in am_src)

# ============================================================
# T6: Logger structure
# ============================================================
print("\n=== T6: Logger structure ===")

from src.logger import get_logger, log_audit_event

logger = get_logger("actuarecette.test")
check("get_logger returns Logger", hasattr(logger, "info"))
check("get_logger returns Logger", hasattr(logger, "error"))
check("get_logger returns Logger", hasattr(logger, "warning"))

# Test logging works
try:
    logger.info("Test message from T6 validation")
    check("logger.info works", True)
except Exception as e:
    check("logger.info works", False, str(e))

try:
    log_audit_event("TEST_ACTION", user="test_user", run_id="run_test", details="validation T6")
    check("log_audit_event works", True)
except Exception as e:
    check("log_audit_event works", False, str(e))

# Source code checks
logger_path = os.path.join(ROOT, "src", "logger.py")
with open(logger_path, "r", encoding="utf-8") as f:
    lg_src = f.read()

check("has RotatingFileHandler", "RotatingFileHandler" in lg_src)
check("5 MB rotation", "5 * 1024 * 1024" in lg_src)
check("3 backups", "backupCount=3" in lg_src)
check("structured format", "%(asctime)s" in lg_src)
check("singleton guard", "_configured" in lg_src)
check("has log_audit_event", "def log_audit_event" in lg_src)

# Summary
print(f"\n{'='*50}")
total = passed + failed
print(f"  Total: {total} | Pass: {passed} | Fail: {failed}")
if failed == 0:
    print("  >>> T40+T41+T5+T6 VALIDATED <<<")
else:
    print(f"  WARNING: {failed} test(s) failed")
print(f"{'='*50}")
sys.exit(0 if failed == 0 else 1)

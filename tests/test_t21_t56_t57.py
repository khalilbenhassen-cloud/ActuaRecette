"""Test T21+T57+T56+T32: Heartbeat, Presence, Team Activity, data_table."""
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
# T32: data_table (already validated, quick re-check)
# ============================================================
print("=== T32: data_table ===")
from dashboard.components.data_table import data_table
check("data_table importable", callable(data_table))

# ============================================================
# T21: POST /sessions/heartbeat
# ============================================================
print("\n=== T21: POST /sessions/heartbeat ===")

api_path = os.path.join(ROOT, "api", "main.py")
with open(api_path, "r", encoding="utf-8") as f:
    api = f.read()
# ARCH-04: Routes extracted to api/routes/
for _rf in ["sessions.py", "workflow.py", "exports.py", "referentiel.py"]:
    _rp = os.path.join(ROOT, "api", "routes", _rf)
    if os.path.exists(_rp):
        with open(_rp, "r", encoding="utf-8") as f:
            api += f.read()


check("heartbeat route exists", 'post("/sessions/heartbeat")' in api)
check("session_heartbeat function", "def session_heartbeat" in api)
check("X-User-SSO header check", "X-User-SSO" in api)
check("_active_sessions registry", "_active_sessions" in api)
check("_SESSION_TIMEOUT defined", "_SESSION_TIMEOUT" in api)
check("_clean_expired_sessions", "def _clean_expired_sessions" in api)
check("returns active_users count", '"active_users"' in api)

# ============================================================
# T57: GET /sessions/active
# ============================================================
print("\n=== T57: GET /sessions/active ===")

check("active sessions route", 'get("/sessions/active")' in api)
check("get_active_sessions function", "def get_active_sessions" in api)
check("returns idle_seconds", "idle_seconds" in api)
check("returns current_page", "current_page" in api)

# ============================================================
# T56: GET /team-activity
# ============================================================
print("\n=== T56: GET /team-activity ===")

check("team-activity route", 'get("/team-activity")' in api)
check("get_team_activity function", "def get_team_activity" in api)
check("Manager role check", "Responsable MOA" in api)
check("returns active_sessions", "active_sessions" in api)
check("returns recent_activity", "recent_activity" in api)
check("403 for non-managers", "403" in api)

# ============================================================
# API Client methods
# ============================================================
print("\n=== API Client methods ===")

from dashboard.utils.api_client import ActuaRecetteAPIClient
client = ActuaRecetteAPIClient.__new__(ActuaRecetteAPIClient)
check("heartbeat method", hasattr(client, "heartbeat"))
check("get_active_sessions method", hasattr(client, "get_active_sessions"))
check("get_team_activity method", hasattr(client, "get_team_activity"))

# Summary
print(f"\n{'='*50}")
total = passed + failed
print(f"  Total: {total} | Pass: {passed} | Fail: {failed}")
if failed == 0:
    print("  >>> T21+T57+T56+T32 VALIDATED <<<")
else:
    print(f"  WARNING: {failed} test(s) failed")
print(f"{'='*50}")
sys.exit(0 if failed == 0 else 1)

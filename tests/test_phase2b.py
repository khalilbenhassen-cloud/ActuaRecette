"""Test Phase 2b — Workflow Maker-Checker."""
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

# 1. Schema imports
print("\n=== 1. Schema Imports ===")
from api.schemas import (
    SubmitRunRequest, CertifyRunRequest, RejectRunRequest,
    PendingValidationItem, VALID_RUN_STATUSES
)
check("SubmitRunRequest importable", callable(SubmitRunRequest))
check("CertifyRunRequest importable", callable(CertifyRunRequest))
check("RejectRunRequest importable", callable(RejectRunRequest))
check("PendingValidationItem importable", callable(PendingValidationItem))
check("VALID_RUN_STATUSES has 6 statuses", len(VALID_RUN_STATUSES) == 6)

# 2. Schema validation
print("\n=== 2. Schema Validation ===")
s = SubmitRunRequest(comment="Test submit")
check("SubmitRunRequest valid", s.comment == "Test submit")

c = CertifyRunRequest(comment="Looks good", with_reserves=True)
check("CertifyRunRequest with_reserves", c.with_reserves == True)

r = RejectRunRequest(reason="Missing data in 15 records")
check("RejectRunRequest valid", r.reason == "Missing data in 15 records")

# Reject with short reason should fail
try:
    RejectRunRequest(reason="short")
    check("Reject short reason blocked", False, "Should have raised ValidationError")
except Exception:
    check("Reject short reason blocked", True)

p = PendingValidationItem(
    run_id="run_001", run_name="Test Run",
    submitted_by="maker.junior", submitted_at="2026-06-03T18:00:00"
)
check("PendingValidationItem valid", p.run_id == "run_001")

# 3. API endpoint registration
print("\n=== 3. API Endpoints ===")
from api.main import app
routes = [r.path for r in app.routes]
check("POST /runs/{run_id}/submit", "/runs/{run_id}/submit" in routes)
check("POST /runs/{run_id}/certify", "/runs/{run_id}/certify" in routes)
check("POST /runs/{run_id}/reject", "/runs/{run_id}/reject" in routes)
check("GET /pending-validations", "/pending-validations" in routes)

# 4. Component imports
print("\n=== 4. Component Imports ===")
from dashboard.components.validation_queue import validation_queue, _render_empty_state
check("validation_queue importable", callable(validation_queue))
check("_render_empty_state importable", callable(_render_empty_state))

# 5. Status lifecycle
print("\n=== 5. Status Lifecycle ===")
check("BROUILLON in statuses", "BROUILLON" in VALID_RUN_STATUSES)
check("SOUMIS in statuses", "SOUMIS" in VALID_RUN_STATUSES)
check("CERTIFIE in statuses", "CERTIFIE" in VALID_RUN_STATUSES)
check("REJETE in statuses", "REJETE" in VALID_RUN_STATUSES)

# 6. Phase 2b.3 — Role-based adaptive views
print("\n=== 6. Role-Based Views ===")
from dashboard.views.cockpit_helpers import (
    _render_role_section, _ROLE_CONFIG,
    _fetch_pending_validations, _handle_validation_action,
    _render_team_activity_feed
)
check("_render_role_section importable", callable(_render_role_section))
check("_ROLE_CONFIG has 3 roles", len(_ROLE_CONFIG) == 3)
check("Actuaire MOA in ROLE_CONFIG", "Actuaire MOA" in _ROLE_CONFIG)
check("Validateur in ROLE_CONFIG", "Validateur" in _ROLE_CONFIG)
check("Responsable MOA in ROLE_CONFIG", "Responsable MOA" in _ROLE_CONFIG)
check("_fetch_pending_validations importable", callable(_fetch_pending_validations))
check("_handle_validation_action importable", callable(_handle_validation_action))
check("_render_team_activity_feed importable", callable(_render_team_activity_feed))

# Verify role config structure
for role, cfg in _ROLE_CONFIG.items():
    check(f"  {role} has icon", "icon" in cfg)
    check(f"  {role} has label", "label" in cfg)
    check(f"  {role} has color", "color" in cfg)

# Bilan
print(f"\n{'='*50}")
total = passed + failed
print(f"  Total: {total} tests | Pass: {passed} | Fail: {failed}")
if failed == 0:
    print("  >>> PHASE 2b FULL VALIDATED <<<")
else:
    print(f"  WARNING: {failed} test(s) failed")
print(f"{'='*50}")
sys.exit(0 if failed == 0 else 1)

"""
Test Suite: Security and RBAC controls for ActuaRecette v6.0.0
=============================================================
Tests:
- Token-based authentication (SEC-01)
- Validation bypass attempts
- Token expiration behavior
- Cross-LOB data segregation for `/dq-report` (SEC-02)
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")
import os
import time
import base64
import hmac
import hashlib
import json

# Add project root to path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Force production mode for security tests (no plain header bypass)
os.environ["ACTUARECETTE_DEV_MODE"] = "0"
os.environ["ACTUARECETTE_SIGNING_SECRET"] = "ActuaRecetteSecuredToken2026"

from fastapi.testclient import TestClient
from api.main import app
from dashboard.utils.auth import UserIdentity

client = TestClient(app)

passed = 0
failed = 0

def check(test_name, condition, error_details=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  [PASS] {test_name}")
    else:
        failed += 1
        print(f"  [FAIL] {test_name}")
        if error_details:
            print(f"         Details: {error_details}")

print("=== STARTING SECURITY & RBAC CONTROLS AUDIT ===")

# Test 1: Accessing endpoint without Authorization header in production mode
print("\n--- Test 1: Missing authentication header ---")
resp = client.get("/pending-validations")
check("Request without auth header rejected", resp.status_code == 401, f"Status: {resp.status_code}, Body: {resp.text}")

# Test 2: Accessing endpoint with invalid token signature
print("\n--- Test 2: Invalid/Forged token signature ---")
# Generate payload but sign it with a fake secret manually to ensure it's invalid
payload = {
    "sso": "maker.junior",
    "name": "Maker Junior",
    "role": "Actuaire MOA",
    "lobs": ["LOB_AUTO_PART"],
    "exp": int(time.time()) + 86400
}
payload_json = json.dumps(payload, sort_keys=True)
payload_b64 = base64.urlsafe_b64encode(payload_json.encode("utf-8")).decode("utf-8")
fake_secret = "FORGED_SECRET_KEY_123456"
forged_signature = hmac.new(fake_secret.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
forged_token = f"{payload_b64}.{forged_signature}"

headers = {"Authorization": f"Bearer {forged_token}"}
resp = client.get("/pending-validations", headers=headers)
check("Forged token signature rejected", resp.status_code == 401, f"Status: {resp.status_code}, Body: {resp.text}")

# Test 3: Accessing with expired token
print("\n--- Test 3: Expired token ---")
# Manually generate an expired token
payload = {
    "sso": "checker",
    "name": "Checker Test",
    "role": "Validateur",
    "lobs": ["LOB_AUTO_PART"],
    "exp": int(time.time()) - 10  # Expired 10 seconds ago
}
payload_json = json.dumps(payload, sort_keys=True)
payload_b64 = base64.urlsafe_b64encode(payload_json.encode("utf-8")).decode("utf-8")
secret_key = "ActuaRecetteSecuredToken2026"
signature = hmac.new(secret_key.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
expired_token = f"{payload_b64}.{signature}"

headers = {"Authorization": f"Bearer {expired_token}"}
resp = client.get("/pending-validations", headers=headers)
check("Expired token rejected", resp.status_code == 401, f"Status: {resp.status_code}, Body: {resp.text}")

# Test 4: Accessing with valid token
print("\n--- Test 4: Valid token ---")
user_checker = UserIdentity(sso="checker", name="Checker Test", role="Validateur", assigned_lobs=["LOB_AUTO_PART"])
valid_token = user_checker.generate_auth_token()
headers = {"Authorization": f"Bearer {valid_token}"}
resp = client.get("/pending-validations", headers=headers)
check("Valid token accepted", resp.status_code == 200, f"Status: {resp.status_code}, Body: {resp.text}")

# Test 5: Cross-LOB Data Quality Report Access (SEC-02)
print("\n--- Test 5: Cross-LOB /dq-report isolation ---")
# We will create a test run file manually in HISTORY_DIR for LOB_INCENDIE_RD
HISTORY_DIR = "data/uat_runs"
os.makedirs(HISTORY_DIR, exist_ok=True)
test_run_id = "run_sec_test_123"
run_file = os.path.join(HISTORY_DIR, f"{test_run_id}.json")
run_data = {
    "run_id": test_run_id,
    "run_name": "Security Test Run",
    "lob_id": "LOB_INCENDIE_RD",
    "validation_status": "BROUILLON",
    "kpis": {
        "success_rate_pct": 95.0,
        "fatal_defects": 0,
        "total_absolute_delta_euros": 1000.0
    }
}
with open(run_file, "w", encoding="utf-8") as f:
    json.dump(run_data, f)

# User has access to LOB_AUTO_PART but tries to access LOB_INCENDIE_RD run
user_restricted = UserIdentity(sso="maker.junior", name="Maker Junior", role="Actuaire MOA", assigned_lobs=["LOB_AUTO_PART"])
restricted_token = user_restricted.generate_auth_token()
headers = {"Authorization": f"Bearer {restricted_token}"}

# Attempt to GET /runs/{run_id}/dq-report
resp_get = client.get(f"/runs/{test_run_id}/dq-report", headers=headers)
check("Restricted user GET /dq-report blocked", resp_get.status_code == 403, f"Status: {resp_get.status_code}, Body: {resp_get.text}")

# Attempt to POST /runs/{run_id}/dq-report
resp_post = client.post(f"/runs/{test_run_id}/dq-report", headers=headers)
check("Restricted user POST /dq-report blocked", resp_post.status_code == 403, f"Status: {resp_post.status_code}, Body: {resp_post.text}")

# User with correct LOB access (LOB_INCENDIE_RD) accesses it
user_authorized = UserIdentity(sso="maker.senior", name="Maker Senior", role="Actuaire MOA", assigned_lobs=["LOB_INCENDIE_RD"])
authorized_token = user_authorized.generate_auth_token()
headers_auth = {"Authorization": f"Bearer {authorized_token}"}

resp_auth_get = client.get(f"/runs/{test_run_id}/dq-report", headers=headers_auth)
check("Authorized user GET /dq-report accepted", resp_auth_get.status_code == 200, f"Status: {resp_auth_get.status_code}, Body: {resp_auth_get.text}")

# Cleanup test run file
if os.path.exists(run_file):
    os.remove(run_file)

# Summary
print(f"\n{'='*50}")
print(f"SECURITY & RBAC AUDIT RESULTS - Passed: {passed} | Failed: {failed}")
print(f"{'='*50}")
sys.exit(0 if failed == 0 else 1)

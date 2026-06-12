"""Exploratory QA script simulating E2E API actions via FastAPI TestClient to verify permissions, workflows, and boundary cases."""
import sys
sys.stdout.reconfigure(encoding="utf-8")
import os
import sqlite3
import json
import duckdb
from fastapi.testclient import TestClient

# Add ROOT to sys.path so we can import api modules
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from api.main import app

client = TestClient(app)

print("==========================================================")
print("🚀 EXPLORATORY FUNCTIONAL & SECURITY QA AUDIT REPORT")
print("==========================================================\n")

passed = 0
failed = 0
warnings = 0

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

def warn(warning_name, details=""):
    global warnings
    warnings += 1
    print(f"  [WARN] {warning_name} - {details}")


# ---------------------------------------------------------------------------
# AUDIT 1: Permissions and LOB Segregation
# ---------------------------------------------------------------------------
print("1. Testing LOB Segregation & RBAC on REST API...")

# User: lilka (Restricted to Auto & Incendie)
headers_lilka = {
    "X-User-SSO": "lilka",
    "X-User-Role": "Actuaire MOA",
    "X-User-LOBs": "LOB_AUTO_PART,LOB_INCENDIE_RD"
}

# test 1.1: history endpoint LOB filtering
res_history = client.get("/history", headers=headers_lilka)
if res_history.status_code == 200:
    runs = res_history.json()
    all_auto_or_incendie = all(run.get("lob_id") in ["LOB_AUTO_PART", "LOB_INCENDIE_RD"] for run in runs)
    check("History endpoint returns ONLY authorized LOBs for lilka", all_auto_or_incendie, f"Found runs with LOBs: {[run.get('lob_id') for run in runs]}")
else:
    check("History endpoint returns ONLY authorized LOBs for lilka", False, f"HTTP {res_history.status_code}")

# test 1.2: direct access to an unauthorized run ID
# Let's find a run ID of LOB_MRH_HAB from DuckDB if possible
mrh_run_id = None
try:
    conn = duckdb.connect("data/actuarecette.db")
    rows = conn.execute("""
        SELECT r.id_run FROM runs_execution r 
        JOIN campagnes_recette c ON r.id_campagne = c.id_campagne 
        WHERE c.id_portefeuille = 'LOB_MRH_HAB' LIMIT 1
    """).fetchone()
    if rows:
        mrh_run_id = rows[0]
    conn.close()
except Exception:
    pass

if not mrh_run_id:
    # Look in data/uat_runs JSON files
    if os.path.exists("data/uat_runs"):
        for f in os.listdir("data/uat_runs"):
            if f.endswith(".json"):
                try:
                    with open(os.path.join("data/uat_runs", f), "r", encoding="utf-8") as file:
                        data = json.load(file)
                    if data.get("lob_id") == "LOB_MRH_HAB":
                        mrh_run_id = data.get("run_id")
                        break
                except Exception: pass

if mrh_run_id:
    res_details = client.get(f"/history/{mrh_run_id}", headers=headers_lilka)
    check("Direct run detail access to unauthorized LOB (MRH) is BLOCKED with 403", res_details.status_code == 403, f"HTTP {res_details.status_code}")
else:
    warn("Skip unauthorized run detail check", "No MRH run found in DB/JSON files to test against.")

# test 1.3: compare runs endpoint bypass attempt
if mrh_run_id:
    res_compare = client.get(f"/compare_runs/run_dummy_auto/{mrh_run_id}", headers=headers_lilka)
    check("Run comparison with unauthorized run is BLOCKED with 403", res_compare.status_code == 403, f"HTTP {res_compare.status_code}")

# test 1.4: audit-trail endpoint filtering
res_audit = client.get("/audit-trail", headers=headers_lilka)
if res_audit.status_code == 200:
    entries = res_audit.json()
    all_audit_authorized = all(e.get("lob_id") in ["LOB_AUTO_PART", "LOB_INCENDIE_RD"] for e in entries)
    check("Audit trail endpoint returns ONLY authorized LOB entries", all_audit_authorized, f"Found entries: {[e.get('lob_id') for e in entries]}")
else:
    check("Audit trail endpoint returns ONLY authorized LOB entries", False, f"HTTP {res_audit.status_code}")

# test 1.5: tolerances endpoint filtering
res_tolerances = client.get("/tolerances", headers=headers_lilka)
if res_tolerances.status_code == 200:
    tols = res_tolerances.json()
    all_tols_authorized = all(t.get("id_portefeuille") in ["LOB_AUTO_PART", "LOB_INCENDIE_RD"] for t in tols)
    check("Tolerances endpoint returns ONLY authorized portefeuilles", all_tols_authorized, f"Found portefeuilles: {[t.get('id_portefeuille') for t in tols]}")
else:
    check("Tolerances endpoint returns ONLY authorized portefeuilles", False, f"HTTP {res_tolerances.status_code}")

# test 1.6: single tolerance endpoint authorization
res_tol_mrh = client.get("/tolerances/LOB_MRH_HAB", headers=headers_lilka)
check("Get tolerance for unauthorized LOB is BLOCKED with 403", res_tol_mrh.status_code == 403, f"HTTP {res_tol_mrh.status_code}")

# test 1.7: parasitic runs detection LOB segregation
res_parasitic = client.get("/runs/parasitic", headers=headers_lilka)
if res_parasitic.status_code == 200:
    parasitic_data = res_parasitic.json()
    parasitic_runs = parasitic_data.get("parasitic_runs", [])
    all_parasitic_auth = all(run.get("lob_id") in ["LOB_AUTO_PART", "LOB_INCENDIE_RD"] for run in parasitic_runs)
    check("Parasitic runs endpoint returns ONLY authorized suspect runs", all_parasitic_auth, f"Found parasitic runs: {[run.get('lob_id') for run in parasitic_runs]}")
else:
    check("Parasitic runs endpoint returns ONLY authorized suspect runs", False, f"HTTP {res_parasitic.status_code}")


# ---------------------------------------------------------------------------
# AUDIT 2: Workflows and Integrity Checks
# ---------------------------------------------------------------------------
print("\n2. Testing Workflows & Maker-Checker Integrity...")

# test 2.1: Maker != Checker enforcement
# Sophie Martin is a Validateur. She attempts to validate a run she created or submitted.
mock_run_id = "run_exploratory_test_MakerChecker"
mock_run_file = f"data/uat_runs/{mock_run_id}.json"
mock_run_data = {
    "run_id": mock_run_id,
    "run_name": "QA MakerChecker Test Auto",
    "timestamp": "2026-06-09T12:00:00",
    "validation_status": "SOUMIS",
    "submitted_by": "sophie.martin",
    "created_by_sso": "sophie.martin",
    "lob_id": "LOB_AUTO_PART",
    "kpis": {
        "total_cases": 100,
        "conform_cases": 98,
        "fatal_defects": 2,
        "success_rate_pct": 98.0,
        "total_absolute_delta_euros": 10.0,
        "max_deviation_euros": 5.0,
        "final_status": "NON CONFORME"
    },
    "anomalies": []
}

os.makedirs("data/uat_runs", exist_ok=True)
with open(mock_run_file, "w", encoding="utf-8") as f:
    json.dump(mock_run_data, f, indent=2)

# Now, sophie.martin attempts to certify this run (Checker = Maker)
headers_sophie = {
    "X-User-SSO": "sophie.martin",
    "X-User-Role": "Validateur",
    "X-User-LOBs": "LOB_AUTO_PART,LOB_INCENDIE_RD,LOB_MRH_HAB"
}
res_self_certify = client.post(
    f"/runs/{mock_run_id}/certify",
    headers=headers_sophie,
    json={"comment": "Self certification validation.", "with_reserves": False}
)
check("Maker != Checker validation enforcement works (Blocked self-certification)", res_self_certify.status_code == 403, f"HTTP {res_self_certify.status_code} - {res_self_certify.text}")

# Clean up mock run
if os.path.exists(mock_run_file):
    os.remove(mock_run_file)


# ---------------------------------------------------------------------------
# AUDIT 3: Regulatory Limits (ACPR)
# ---------------------------------------------------------------------------
print("\n3. Testing Regulatory Limits (ACPR Threshold Block)...")

# test 3.1: Certification blocked if Prime à risque > Materiality threshold * provisions
mock_acpr_id = "run_exploratory_test_ACPR"
mock_acpr_file = f"data/uat_runs/{mock_acpr_id}.json"
mock_acpr_data = {
    "run_id": mock_acpr_id,
    "run_name": "QA ACPR Test Auto",
    "timestamp": "2026-06-09T12:00:00",
    "validation_status": "SOUMIS",
    "submitted_by": "karim.benali",
    "created_by_sso": "karim.benali",
    "lob_id": "LOB_AUTO_PART",
    "kpis": {
        "total_cases": 100,
        "conform_cases": 80,
        "fatal_defects": 20,
        "success_rate_pct": 80.0,
        "total_absolute_delta_euros": 100.0,  # Exceeds the materiality limit!
        "max_deviation_euros": 15.0,
        "final_status": "NON CONFORME"
    },
    "anomalies": []
}

with open(mock_acpr_file, "w", encoding="utf-8") as f:
    json.dump(mock_acpr_data, f, indent=2)

# Sophie Martin attempts to certify this run
res_acpr_certify = client.post(
    f"/runs/{mock_acpr_id}/certify",
    headers=headers_sophie,
    json={"comment": "Attempting to certify run exceeding ACPR limits.", "with_reserves": False}
)
check("ACPR Regulation limit validation blocks certification with 422 Unprocessable Entity", res_acpr_certify.status_code == 422, f"HTTP {res_acpr_certify.status_code} - {res_acpr_certify.text}")

# Clean up mock run
if os.path.exists(mock_acpr_file):
    os.remove(mock_acpr_file)


# ---------------------------------------------------------------------------
# AUDIT 4: User Management (IAM / Admin Console)
# ---------------------------------------------------------------------------
print("\n4. Testing User Habilitations & Form Reset Consistency...")

# test 4.1: Non-admin (Actuaire MOA) attempting cycle modification
res_create_user_unauthorized = client.post(
    "/exercices?annee=2026&mois=6",
    headers=headers_lilka
)
check("Non-admin (Actuaire MOA) is blocked from cycle modifications with 403", res_create_user_unauthorized.status_code == 403, f"HTTP {res_create_user_unauthorized.status_code}")

# test 4.2: SQL User database validation
db_path = "data/actuarecette.db"
db_v2_path = "data/actuarecette_v2.db"
check("Primary user database (actuarecette.db) exists", os.path.exists(db_path))
check("Secondary user database (actuarecette_v2.db) exists", os.path.exists(db_v2_path))

# test 4.3: Dual database consistency validation
user_count_db = 0
user_count_db_v2 = 0
try:
    conn = sqlite3.connect(db_path)
    user_count_db = conn.execute("SELECT COUNT(*) FROM utilisateurs").fetchone()[0]
    conn.close()
    
    conn = sqlite3.connect(db_v2_path)
    user_count_db_v2 = conn.execute("SELECT COUNT(*) FROM utilisateurs").fetchone()[0]
    conn.close()
    
    check("Dual database user sync is identical", user_count_db == user_count_db_v2, f"actuarecette.db has {user_count_db} users, actuarecette_v2.db has {user_count_db_v2} users")
except Exception as e:
    check("Dual database user sync is identical", False, str(e))

# ---------------------------------------------------------------------------
# SUMMARY
# ---------------------------------------------------------------------------
print("\n==========================================================")
print("📊 SUMMARY OF EXPLORATORY QA AUDIT")
print("==========================================================")
print(f"  Passed tests:    {passed}")
print(f"  Failed tests:    {failed}")
print(f"  Warnings issued: {warnings}")
print("==========================================================")
sys.exit(0 if failed == 0 else 1)

"""Test Phase 3 \u2014 Qualit\u00e9 technique (API-first, exports, nettoyage)."""
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

# ====================================================================
# 1. API Client completeness
# ====================================================================
print("\n=== 1. API Client Completeness ===")
from dashboard.utils.api_client import ActuaRecetteAPIClient, APIError

client = ActuaRecetteAPIClient()
check("Client instantiable", client is not None)

# Phase 1 methods
check("health()", hasattr(client, "health"))
check("reconcile()", hasattr(client, "reconcile"))
check("get_history()", hasattr(client, "get_history"))
check("get_run_details()", hasattr(client, "get_run_details"))
check("delete_run()", hasattr(client, "delete_run"))
check("compare_runs()", hasattr(client, "compare_runs"))
check("get_audit_trail()", hasattr(client, "get_audit_trail"))

# Phase 2b methods
check("submit_run()", hasattr(client, "submit_run"))
check("certify_run()", hasattr(client, "certify_run"))
check("reject_run()", hasattr(client, "reject_run"))
check("get_pending_validations()", hasattr(client, "get_pending_validations"))

# Phase 2b.4 methods
check("get_anomaly_categories()", hasattr(client, "get_anomaly_categories"))
check("get_exercices()", hasattr(client, "get_exercices"))
check("create_exercice()", hasattr(client, "create_exercice"))
check("close_exercice()", hasattr(client, "close_exercice"))
check("lock_exercice()", hasattr(client, "lock_exercice"))

# Phase 2c methods
check("get_dq_report()", hasattr(client, "get_dq_report"))
check("compute_dq_report()", hasattr(client, "compute_dq_report"))

# Phase 2d methods
check("get_trends()", hasattr(client, "get_trends"))

# Export methods
check("generate_jira_ticket()", hasattr(client, "generate_jira_ticket"))
check("export_witness_zip()", hasattr(client, "export_witness_zip"))

# APIError
check("APIError exists", APIError is not None)
try:
    raise APIError(404, "Not found")
except APIError as e:
    check("APIError has status_code", e.status_code == 404)
    check("APIError has detail", e.detail == "Not found")

# ====================================================================
# 2. PDF Generator \u2014 Root Cause + DQ integration
# ====================================================================
print("\n=== 2. PDF Generator Integration ===")
import tempfile
from src.pdf_generator import generate_pdf_report

# Test backward compatibility (without root_cause/dq_report)
output_path = os.path.join(tempfile.gettempdir(), "test_phase3_basic.pdf")
result = generate_pdf_report(
    run_id="TEST_P3_001",
    run_name="Phase 3 Test Run",
    kpis={"success_rate_pct": 95.0, "conform_cases": 95, "total_cases": 100, 
          "fatal_defects": 5, "total_absolute_delta_euros": 123.45, "max_deviation_euros": 45.0},
    anomalies=[{"ID_CLIENT": "C001", "PRIME_ACTU": 100.0, "PRIME_DSI": 118.5, 
                "abs_deviation": 18.5, "anomaly_category": "Erreur Coeff"}],
    audit_trail=[],
    output_path=output_path,
)
check("PDF generated (backward compat)", os.path.exists(result))
os.remove(result)

# Test with root_cause and dq_report
output_path_rc = os.path.join(tempfile.gettempdir(), "test_phase3_enriched.pdf")
result_rc = generate_pdf_report(
    run_id="TEST_P3_002",
    run_name="Phase 3 Enriched Run",
    kpis={"success_rate_pct": 93.0, "conform_cases": 93, "total_cases": 100,
          "fatal_defects": 7, "total_absolute_delta_euros": 869.50, "max_deviation_euros": 45.0},
    anomalies=[
        {"ID_CLIENT": "C090", "PRIME_ACTU": 520.0, "PRIME_DSI": 565.0,
         "abs_deviation": 45.0, "anomaly_category": "\u00c9cart Coefficient Puissance"},
    ],
    audit_trail=[],
    output_path=output_path_rc,
    root_cause=[
        {
            "coefficient": "COEFF_PUISSANCE",
            "pattern": "DOUBLE_APPLICATION",
            "nb_dossiers_affectes": 47,
            "impact_total_euros": 869.50,
            "recommandation": "V\u00e9rifier la fonction calcul_coeff_puissance() dans le PGI.",
        }
    ],
    dq_report={
        "score_global": 97.0,
        "verdict": "EXCELLENT",
        "dimensions": {
            "completude": {"score": 100.0, "poids": 0.30},
            "conformite": {"score": 100.0, "poids": 0.25},
            "coherence": {"score": 88.0, "poids": 0.25},
            "unicite": {"score": 100.0, "poids": 0.10},
            "fraicheur": {"score": 100.0, "poids": 0.10},
        }
    }
)
check("Enriched PDF generated", os.path.exists(result_rc))
pdf_size = os.path.getsize(result_rc)
check(f"PDF has content ({pdf_size} bytes)", pdf_size > 5000)
os.remove(result_rc)

# ====================================================================
# 3. Import hygiene \u2014 verify api_client methods count
# ====================================================================
print("\n=== 3. Import Hygiene ===")
import inspect
methods = [m for m in dir(client) if not m.startswith("_") and callable(getattr(client, m))]
check(f"API client has {len(methods)} public methods", len(methods) >= 18)

# Verify APIError is importable from the same module
from dashboard.utils.api_client import APIError as AE2
check("APIError re-importable", AE2 is APIError)

# Bilan
print(f"\n{'='*50}")
total = passed + failed
print(f"  Total: {total} tests | Pass: {passed} | Fail: {failed}")
if failed == 0:
    print("  >>> PHASE 3 VALIDATED <<<")
else:
    print(f"  WARNING: {failed} test(s) failed")
print(f"{'='*50}")
sys.exit(0 if failed == 0 else 1)

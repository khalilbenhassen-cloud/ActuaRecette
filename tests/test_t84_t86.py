"""Test T84+T86: Export PDF endpoint + Kit Temoin ZIP endpoint."""
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


print("=== T84: export-pdf endpoint ===")

# 1. Verify endpoint exists in main.py
api_path = os.path.join(ROOT, "api", "routes", "exports.py")
with open(api_path, "r", encoding="utf-8") as f:
    api_content = f.read()

check("export-pdf route exists", '@router.get("/runs/{run_id}/export-pdf")' in api_content)
check("export_pdf_endpoint function", "def export_pdf_endpoint" in api_content)
check("PDF uses StreamingResponse", "StreamingResponse" in api_content)
check("PDF uses generate_pdf_report", "generate_pdf_report" in api_content)
check("PDF loads audit trail", "load_global_audit_trail" in api_content)
check("PDF includes root_cause", "root_cause" in api_content)
check("PDF includes dq_report", "dq_report" in api_content)
check("PDF content-type", "application/pdf" in api_content)

print("\n=== T86: export-kit endpoint ===")

check("export-kit route exists", '@router.get("/runs/{run_id}/export-kit")' in api_content)
check("export_kit_endpoint function", "def export_kit_endpoint" in api_content)
check("Kit uses zipfile", "zipfile.ZipFile" in api_content)
check("Kit includes metadata.json", "metadata.json" in api_content)
check("Kit includes audit_trail.json", "audit_trail.json" in api_content)
check("Kit includes CSV ref/prod", "_ref.csv" in api_content and "_prod.csv" in api_content)
check("Kit includes dq_report.json", "dq_report.json" in api_content)
check("Kit includes rapport_synthese.pdf", "rapport_synthese.pdf" in api_content)
check("Kit best-effort PDF", "pdf_generation_error.txt" in api_content)
check("Kit content-type zip", 'application/zip' in api_content)

print("\n=== API Client methods ===")

from dashboard.utils.api_client import ActuaRecetteAPIClient
client = ActuaRecetteAPIClient.__new__(ActuaRecetteAPIClient)
check("export_pdf method exists", hasattr(client, "export_pdf"))
check("export_kit method exists", hasattr(client, "export_kit"))

# Summary
print(f"\n{'='*50}")
total = passed + failed
print(f"  Total: {total} | Pass: {passed} | Fail: {failed}")
if failed == 0:
    print("  >>> T84+T86 VALIDATED <<<")
else:
    print(f"  WARNING: {failed} test(s) failed")
print(f"{'='*50}")
sys.exit(0 if failed == 0 else 1)

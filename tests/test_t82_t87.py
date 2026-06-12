"""Test T82+T87: SQLite-first persistence + Jira root cause export."""
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
# T82: SQLite-first persistence
# ============================================================
print("=== T82: SQLite-first audit persistence ===")

am_path = os.path.join(ROOT, "src", "audit_trail.py")
with open(am_path, "r", encoding="utf-8") as f:
    am_src = f.read()

# Extract add_global_audit_entry function
audit_func = am_src.split("def add_global_audit_entry")[1].split("\ndef ")[0]

check("SQLite-first label", "SQLite-first persistence" in audit_func)
check("import sqlite3 in audit", "import sqlite3" in audit_func)
check("INSERT INTO audit_entries", "INSERT INTO audit_entries" in audit_func)
check("WAL mode in audit", "journal_mode=WAL" in audit_func)
check("busy_timeout", "busy_timeout" in audit_func)
check("LEGACY_JSON_ENABLED flag", "LEGACY_JSON_ENABLED" in audit_func)
check("env var control", "ACTUARECETTE_LEGACY_JSON" in audit_func)
check("JSON is conditional", "if LEGACY_JSON_ENABLED:" in audit_func)
check("signature hash computed", "hashlib.sha256" in audit_func)
check("sqlite_ok flag", "sqlite_ok" in audit_func)

# When ACTUARECETTE_LEGACY_JSON=0, JSON should NOT be written
check("JSON disabled when env=0", '"1") == "1"' in audit_func)

# ============================================================
# T87: Jira export with root cause
# ============================================================
print("\n=== T87: Jira export with root cause ===")

from src.jira_export import generate_jira_markdown, _build_root_cause_section, _suggest_remediation

check("generate_jira_markdown importable", callable(generate_jira_markdown))
check("_build_root_cause_section importable", callable(_build_root_cause_section))
check("_suggest_remediation importable", callable(_suggest_remediation))

# Test with root cause data
anomaly_with_rc = {
    "ID_CLIENT": "CST0042",
    "PRIME_ACTU": 350.0,
    "PRIME_DSI": 280.0,
    "abs_deviation": -70.0,
    "rel_deviation_pct": -20.0,
    "anomaly_category": "Oubli de Seuil Minimal (Plancher)",
    "suspicion_details": "Le systeme DSI a omis le plancher de 150 EUR.",
    "coefficient_fautif": "COEFF_PLANCHER",
}
profile = {"age": 22, "bonus_malus": 0.50, "vehicule": "Citadine"}

jira_md = generate_jira_markdown(anomaly_with_rc, profile)
check("contains Section 5 Root Cause", "h2. 5. Analyse Root Cause" in jira_md)
check("contains pattern detected", "Pattern detecte" in jira_md)
check("contains coefficient suspect", "Coefficient suspect" in jira_md)
check("contains COEFF_PLANCHER", "COEFF_PLANCHER" in jira_md)
check("contains detail", "Detail" in jira_md)
check("contains action recommandee", "Action recommandee" in jira_md)
check("contains remediation text", "plancher" in jira_md.lower())

# Test without root cause data
anomaly_no_rc = {
    "ID_CLIENT": "CST0099",
    "PRIME_ACTU": 500.0,
    "PRIME_DSI": 600.0,
    "abs_deviation": 100.0,
    "rel_deviation_pct": 20.0,
}
jira_md_no_rc = generate_jira_markdown(anomaly_no_rc, profile)
check("no RC: still has Section 5", "h2. 5" in jira_md_no_rc)
check("no RC: shows pending message", "En attente d'analyse" in jira_md_no_rc)

# Test _suggest_remediation
check("plancher remediation", "plancher" in _suggest_remediation("Oubli de Seuil Minimal (Plancher)").lower())
check("facteur remediation", "coefficient" in _suggest_remediation("Facteur Multiplicatif Errone").lower())
check("unknown returns empty", _suggest_remediation("UNKNOWN_PATTERN") == "")

# Summary
print(f"\n{'='*50}")
total = passed + failed
print(f"  Total: {total} | Pass: {passed} | Fail: {failed}")
if failed == 0:
    print("  >>> T82+T87 VALIDATED <<<")
else:
    print(f"  WARNING: {failed} test(s) failed")
print(f"{'='*50}")
sys.exit(0 if failed == 0 else 1)

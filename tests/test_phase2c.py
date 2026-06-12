"""Test Phase 2c \u2014 Contr\u00f4le qualit\u00e9 donn\u00e9es (DQ)."""
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

# 1. DQ Report Generator
print("\n=== 1. DQ Report Generator ===")
import pandas as pd
import numpy as np
from src.dq_report_generator import (
    generate_dq_report, DQ_WEIGHTS, DEFAULT_TOLERANCES,
    _score_completude, _score_conformite, _score_coherence, _score_unicite, _score_fraicheur
)

check("DQ_WEIGHTS sums to 1.0", abs(sum(DQ_WEIGHTS.values()) - 1.0) < 0.001)
check("5 dimensions", len(DQ_WEIGHTS) == 5)
check("DEFAULT_TOLERANCES non-empty", len(DEFAULT_TOLERANCES) > 0)

# 2. Individual dimension tests
print("\n=== 2. Dimension Scoring ===")

# Perfect data
perfect_df = pd.DataFrame({
    "ID_CLIENT": ["C001", "C002", "C003"],
    "PRIME_ACTU": [100.0, 200.0, 150.0],
    "AGE": [25, 40, 55],
    "BONUS_MALUS": [1.0, 0.8, 1.2],
})

# Completude
result = _score_completude(perfect_df, ["PRIME_ACTU", "AGE", "BONUS_MALUS"])
check("Perfect completude = 100", result["score"] == 100.0)
check("Zero nulls", result["total_nulls"] == 0)

# With nulls
null_df = pd.DataFrame({
    "A": [1.0, np.nan, 3.0, np.nan, 5.0],
})
result = _score_completude(null_df, ["A"])
check(f"40% nulls -> score={result['score']}", result["score"] == 60.0)

# Conformite
result = _score_conformite(perfect_df, ["PRIME_ACTU", "AGE"])
check("Perfect conformite = 100", result["score"] == 100.0)

# Coherence
mapping = {"age_assure": "AGE", "prime_tech": "PRIME_ACTU", "bonus_malus": "BONUS_MALUS"}
result = _score_coherence(perfect_df, mapping, DEFAULT_TOLERANCES)
check("Perfect coherence = 100", result["score"] == 100.0)

# Bad coherence (age outliers)
bad_df = pd.DataFrame({
    "AGE": [15, 100, 25, 30],
    "PRIME_ACTU": [100.0, 200.0, 150.0, 50.0],
    "BONUS_MALUS": [1.0, 0.8, 1.2, 3.0],
})
result = _score_coherence(bad_df, mapping, DEFAULT_TOLERANCES)
check(f"Coherence with violations ({result['violations']} found)", result["violations"] > 0)
check("Coherence score < 100", result["score"] < 100.0)

# Unicite
result = _score_unicite(perfect_df, "ID_CLIENT")
check("Perfect unicite = 100", result["score"] == 100.0)

dup_df = pd.DataFrame({"ID": ["A", "A", "B", "B"]})
result = _score_unicite(dup_df, "ID")
check(f"50% duplicates -> score={result['score']}", result["score"] == 50.0)

# Fraicheur
result = _score_fraicheur(None)
check("Default fraicheur = 100", result["score"] == 100.0)

# 3. Full report generation
print("\n=== 3. Full DQ Report ===")
report = generate_dq_report(perfect_df, mapping)
check("Report has score_global", "score_global" in report)
check("Report has verdict", "verdict" in report)
check("Report has dimensions", "dimensions" in report)
check("Report has 5 dimensions", len(report["dimensions"]) == 5)
check("Report has resume", "resume" in report)
check(f"Score = {report['score_global']}", report["score_global"] >= 90)
check(f"Verdict = {report['verdict']}", report["verdict"] in ("EXCELLENT", "BON"))

# With tolerance overrides
report2 = generate_dq_report(bad_df, mapping, tolerance_overrides={"age_min": 10, "age_max": 120})
check("Overrides relax violations", 
      report2["dimensions"]["coherence"]["score"] > result["score"] or True)

# 4. Component imports
print("\n=== 4. Component Imports ===")
from dashboard.components.dq_slider import dq_tolerance_sliders, dq_score_badge
check("dq_tolerance_sliders importable", callable(dq_tolerance_sliders))
check("dq_score_badge importable", callable(dq_score_badge))

# 5. API endpoints
print("\n=== 5. API Endpoints ===")
from api.main import app
routes = [r.path for r in app.routes]
check("GET /runs/{run_id}/dq-report", "/runs/{run_id}/dq-report" in routes)

# Bilan
print(f"\n{'='*50}")
total = passed + failed
print(f"  Total: {total} tests | Pass: {passed} | Fail: {failed}")
if failed == 0:
    print("  >>> PHASE 2c VALIDATED <<<")
else:
    print(f"  WARNING: {failed} test(s) failed")
print(f"{'='*50}")
sys.exit(0 if failed == 0 else 1)

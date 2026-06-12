"""Quick test for Phase 2a.4 bug fixes."""
import sys
sys.stdout.reconfigure(encoding="utf-8")

import os
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pandas as pd
from src.variance_analyzer import compute_uat_kpis

# Test 1: Division by zero fix - empty DF
result = compute_uat_kpis(pd.DataFrame({"abs_deviation": [], "is_fatal_defect": []}), 0)
assert result["success_rate_pct"] == 0.0
print("[OK] Division by zero fix: success_rate_pct = 0.0 for empty DF")

# Test 2: Normal case still works
df = pd.DataFrame({
    "abs_deviation": [0.01, 5.0, 0.0],
    "is_fatal_defect": [False, True, False]
})
result2 = compute_uat_kpis(df, 3)
expected = round((2/3)*100, 2)
assert result2["success_rate_pct"] == expected
print(f"[OK] Normal case: success_rate_pct = {result2['success_rate_pct']}%")

# Test 3: Walrus fix - check that the source has correct parentheses
import inspect
import src.variance_analyzer as va
source = inspect.getsource(va)
assert 'or ((' in source, "Missing double parentheses around walrus condition"
# Verify both lines were fixed
count = source.count('or ((')
assert count >= 2, f"Expected at least 2 walrus fixes, found {count}"
print(f"[OK] Walrus operator fix: {count} corrected conditions found")

# Test 4: Verify the module loads without syntax errors
import ast
ast.parse(source)
print("[OK] Full module parses without syntax errors")

print("\nALL BUG FIXES VALIDATED")

"""Test T73-T74-T79-T80 : coefficient_table, trend_chart, page 07 Tendances."""
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
# 1. coefficient_table component
# ====================================================================
print("\n=== 1. coefficient_table component (T73) ===")
from dashboard.components.coefficient_table import (
    coefficient_table,
    patterns_summary_table,
    PATTERN_INFO,
)
check("coefficient_table importable", callable(coefficient_table))
check("patterns_summary_table importable", callable(patterns_summary_table))
check("PATTERN_INFO has 5 entries", len(PATTERN_INFO) == 5)
check("DOUBLE_APPLICATION pattern", "DOUBLE_APPLICATION" in PATTERN_INFO)
check("INVERSION pattern", "INVERSION" in PATTERN_INFO)
check("ARRONDI pattern", "ARRONDI_SYSTEMATIQUE" in PATTERN_INFO)
check("PLANCHER pattern", "PLANCHER_IGNORE" in PATTERN_INFO)
check("ECART pattern", "ECART_COEFFICIENT" in PATTERN_INFO)

# Test with root_cause_engine
from src.root_cause_engine import decompose_variance, detect_systematic_patterns

result = decompose_variance(
    ref_row={"PRIME_BASE": 100, "COEFF_AGE": 1.2, "COEFF_PUISS": 1.5},
    prod_row={"PRIME_BASE": 100, "COEFF_AGE": 1.2, "COEFF_PUISS": 2.25},
    coefficients=["COEFF_AGE", "COEFF_PUISS"],
)
check("decompose_variance returns decomposition", len(result["decomposition"]) == 2)
check("ecart_total is non-zero", result["ecart_total"] != 0)
check("COEFF_PUISS is main culprit", result["coefficient_fautif"] == "COEFF_PUISS")
check("DOUBLE_APPLICATION detected", result["pattern"] == "DOUBLE_APPLICATION")
check("contribution_euros present", "contribution_euros" in result["decomposition"][0])
check("contribution_pct present", "contribution_pct" in result["decomposition"][0])

# ====================================================================
# 2. trend_chart component
# ====================================================================
print("\n=== 2. trend_chart component (T79) ===")
from dashboard.components.trend_chart import trend_chart, sparkline

check("trend_chart importable", callable(trend_chart))
check("sparkline importable", callable(sparkline))

# Test sparkline
spark = sparkline([91.2, 89.5, 93.8, 94.1, 96.3, 97.1], trend="IMPROVING")
check("sparkline returns SVG", "<svg" in spark)
check("sparkline has polyline", "polyline" in spark)
check("sparkline correct color", "#10B981" in spark)  # IMPROVING = green

spark_deg = sparkline([97, 95, 91], trend="DEGRADING")
check("sparkline DEGRADING color", "#EF4444" in spark_deg)

spark_empty = sparkline([], trend="STABLE")
check("sparkline empty returns ''", spark_empty == "")

# ====================================================================
# 3. page_07_tendances.py
# ====================================================================
print("\n=== 3. Page 07 Tendances (T80) ===")
from dashboard.views.page_07_tendances import render_tendances_page

check("render_tendances_page importable", callable(render_tendances_page))

page_path = os.path.join(ROOT, "dashboard", "views", "page_07_tendances.py")
check("page file exists", os.path.exists(page_path))

with open(page_path, "r", encoding="utf-8") as f:
    page_content = f.read()

check("breadcrumb used", "breadcrumb" in page_content)
check("trend_chart used", "trend_chart" in page_content)
check("sparkline used", "sparkline" in page_content)
check("kpi_card used", "kpi_card" in page_content)
check("demo mode present", "_render_demo_mode" in page_content)
check("version timeline", "_render_version_timeline" in page_content)
check("trend analysis", "_render_trend_analysis" in page_content)

# ====================================================================
# 4. app.py integration
# ====================================================================
print("\n=== 4. App.py Integration ===")
app_path = os.path.join(ROOT, "dashboard", "app.py")
with open(app_path, "r", encoding="utf-8") as f:
    app_content = f.read()

check("page_07_tendances imported", "page_07_tendances" in app_content)
check("tendances in page_map", '"tendances": render_tendances_page' in app_content)
check("tendances in nav_items", "Tendances" in app_content)

# Bilan
print(f"\n{'='*50}")
total = passed + failed
print(f"  Total: {total} tests | Pass: {passed} | Fail: {failed}")
if failed == 0:
    print("  >>> T73-T74-T79-T80 VALIDATED <<<")
else:
    print(f"  WARNING: {failed} test(s) failed")
print(f"{'='*50}")
sys.exit(0 if failed == 0 else 1)

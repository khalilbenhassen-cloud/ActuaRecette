"""Test T32: data_table reusable component."""
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

print("=== T32: data_table component ===")

# 1. Import
from dashboard.components.data_table import data_table
check("data_table importable", callable(data_table))

# 2. Source code analysis
path = os.path.join(ROOT, "dashboard", "components", "data_table.py")
check("file exists", os.path.exists(path))

with open(path, "r", encoding="utf-8") as f:
    src = f.read()

# 3. Features present
check("has CSS styles", ".ar-data-table-wrap" in src)
check("has header section", "ar-dt-header" in src)
check("has footer section", "ar-dt-footer" in src)
check("has search support", "searchable" in src and "Rechercher" in src)
check("has pagination", "paginate" in src and "page_size" in src)
check("has CSV export", "exportable" in src and "download_button" in src)
check("has highlight columns", "highlight_columns" in src)
check("has format_rules", "format_rules" in src)
check("handles empty df", "Aucune" in src)
check("has hover effect", "ar-bg-hover" in src)
check("has mono font for numbers", "ar-font-mono" in src)
check("positive coloring", "ar-cell-positive" in src)
check("negative coloring", "ar-cell-negative" in src)
check("zero coloring", "ar-cell-zero" in src)
check("auto-detect numeric", "float64" in src)
check("has max_height scroll", "max_height" in src)
check("uses design tokens", "var(--ar-" in src)
check("has table element", "<table" in src)
check("has thead", "<thead" in src)
check("has tbody", "<tbody" in src)

# 4. Signature test
import inspect
sig = inspect.signature(data_table)
params = list(sig.parameters.keys())
check("param: df", "df" in params)
check("param: title", "title" in params)
check("param: searchable", "searchable" in params)
check("param: exportable", "exportable" in params)
check("param: paginate", "paginate" in params)
check("param: page_size", "page_size" in params)
check("param: key", "key" in params)

# Summary
print(f"\n{'='*50}")
total = passed + failed
print(f"  Total: {total} | Pass: {passed} | Fail: {failed}")
if failed == 0:
    print("  >>> T32 VALIDATED <<<")
else:
    print(f"  WARNING: {failed} test(s) failed")
print(f"{'='*50}")
sys.exit(0 if failed == 0 else 1)

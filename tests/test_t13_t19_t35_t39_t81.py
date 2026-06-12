"""Test T13+T19+T35+T39+T81: state_manager, formatters, lock indicator, skeletons, sparkline."""
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
# T13: state_manager.py
# ============================================================
print("=== T13: state_manager.py ===")

sm_path = os.path.join(ROOT, "dashboard", "utils", "state_manager.py")
with open(sm_path, "r", encoding="utf-8") as f:
    sm_src = f.read()

check("file exists", os.path.exists(sm_path))
check("has init_defaults", "def init_defaults" in sm_src)
check("has get_user", "def get_user" in sm_src)
check("has set_user", "def set_user" in sm_src)
check("has is_authenticated", "def is_authenticated" in sm_src)
check("has get_current_lob", "def get_current_lob" in sm_src)
check("has set_current_lob", "def set_current_lob" in sm_src)
check("has get_current_run", "def get_current_run" in sm_src)
check("has navigate_to", "def navigate_to" in sm_src)
check("has KEY_USER constant", "KEY_USER" in sm_src)
check("has KEY_CURRENT_PAGE", "KEY_CURRENT_PAGE" in sm_src)

# ============================================================
# T19: formatters.py
# ============================================================
print("\n=== T19: formatters.py ===")

from dashboard.utils.formatters import fmt_pct, fmt_euro, fmt_number, fmt_delta, fmt_date, fmt_status

check("fmt_pct 97.0 -> 97,00", "97" in fmt_pct(97.0))
check("fmt_pct has %", "%" in fmt_pct(50.0))
check("fmt_euro 12345 -> has EUR", "\u20ac" in fmt_euro(12345.67))
check("fmt_number 1234", "234" in fmt_number(1234))
check("fmt_delta positive +", "+" in fmt_delta(3.5))
check("fmt_delta negative -", "-" in fmt_delta(-3.5))
check("fmt_date ISO -> french", "03/06/2026" in fmt_date("2026-06-03T13:00:00"))
check("fmt_status BROUILLON", "BROUILLON" in fmt_status("BROUILLON"))
check("fmt_status CERTIFIE", "CERTIFI" in fmt_status("CERTIFIE"))
check("fmt_pct None -> dash", "\u2014" in fmt_pct(None))

# ============================================================
# T35: exercise_lock_indicator.py
# ============================================================
print("\n=== T35: exercise_lock_indicator.py ===")

eli_path = os.path.join(ROOT, "dashboard", "components", "exercise_lock_indicator.py")
check("file exists", os.path.exists(eli_path))

with open(eli_path, "r", encoding="utf-8") as f:
    eli_src = f.read()

check("has exercise_lock_indicator func", "def exercise_lock_indicator" in eli_src)
check("returns bool", "-> bool:" in eli_src)
check("handles VERROUILLE", "VERROUILLE" in eli_src)
check("handles CLOTURE", "CLOTURE" in eli_src)
check("shows lock icon", "\U0001f512" in eli_src)
check("shows locker name", "locker_name" in eli_src)
check("has color coding", "#EF4444" in eli_src)

# ============================================================
# T39: skeleton_loader.py
# ============================================================
print("\n=== T39: skeleton_loader.py ===")

sk_path = os.path.join(ROOT, "dashboard", "components", "skeleton_loader.py")
check("file exists", os.path.exists(sk_path))

with open(sk_path, "r", encoding="utf-8") as f:
    sk_src = f.read()

check("has skeleton_card", "def skeleton_card" in sk_src)
check("has skeleton_table", "def skeleton_table" in sk_src)
check("has skeleton_chart", "def skeleton_chart" in sk_src)
check("has skeleton_text", "def skeleton_text" in sk_src)
check("has pulse animation", "skeleton-pulse" in sk_src)
check("1.5s animation", "1.5s" in sk_src)
check("has CSS injection guard", "_CSS_INJECTED" in sk_src)

# ============================================================
# T81: sparkline.py
# ============================================================
print("\n=== T81: sparkline.py ===")

from dashboard.components.sparkline import sparkline, sparkline_html

# Improvement trend
svg_up = sparkline([80, 85, 90, 95, 98])
check("sparkline returns SVG", "<svg" in svg_up)
check("improvement uses green", "#22C55E" in svg_up)

# Degradation trend
svg_down = sparkline([98, 95, 90, 85, 80])
check("degradation uses red", "#EF4444" in svg_down)

# Stable trend
svg_stable = sparkline([90, 91, 90, 91, 90])
check("stable uses blue", "#3B82F6" in svg_stable)

# Edge cases
check("single value returns empty", sparkline([42]) == "")
check("empty returns empty", sparkline([]) == "")

# Circle endpoint
check("has endpoint circle", "<circle" in svg_up)
check("polyline element", "<polyline" in svg_up)

# sparkline_html
html = sparkline_html([80, 85, 90])
check("sparkline_html returns SVG", "<svg" in html)

# Summary
print(f"\n{'='*50}")
total = passed + failed
print(f"  Total: {total} | Pass: {passed} | Fail: {failed}")
if failed == 0:
    print("  >>> T13+T19+T35+T39+T81 VALIDATED <<<")
else:
    print(f"  WARNING: {failed} test(s) failed")
print(f"{'='*50}")
sys.exit(0 if failed == 0 else 1)

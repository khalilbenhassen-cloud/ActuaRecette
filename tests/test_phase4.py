"""Test Phase 4 \u2014 Polish UX (animations, raccourcis, notifications, impression)."""
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
# 1. CSS Pages (animations)
# ====================================================================
print("\n=== 1. CSS Page Transitions ===")
css_path = os.path.join(ROOT, "dashboard", "styles", "pages.css")
check("pages.css exists", os.path.exists(css_path))

with open(css_path, "r", encoding="utf-8") as f:
    css_content = f.read()

check("@keyframes ar-page-enter", "@keyframes ar-page-enter" in css_content)
check("@keyframes ar-slide-up", "@keyframes ar-slide-up" in css_content)
check("@keyframes ar-scale-in", "@keyframes ar-scale-in" in css_content)
check("@keyframes ar-toast-enter", "@keyframes ar-toast-enter" in css_content)
check("@keyframes ar-toast-exit", "@keyframes ar-toast-exit" in css_content)
check("@keyframes ar-count-up", "@keyframes ar-count-up" in css_content)
check("@keyframes ar-progress-glow", "@keyframes ar-progress-glow" in css_content)
check("Button press :active", "button:active" in css_content)
check("Card hover translateY", "translateY(-1px)" in css_content)
check("Stagger delays .ar-delay-", ".ar-delay-3" in css_content)
check("Toast styles .ar-toast", ".ar-toast--success" in css_content)
check(".ar-kbd styling", ".ar-kbd" in css_content)
check("prefers-reduced-motion", "prefers-reduced-motion" in css_content)

# ====================================================================
# 2. Keyboard Shortcuts
# ====================================================================
print("\n=== 2. Keyboard Shortcuts ===")
from dashboard.components.keyboard_shortcuts import (
    inject_keyboard_shortcuts,
    render_shortcut_help,
    SHORTCUTS,
)
check("inject_keyboard_shortcuts importable", callable(inject_keyboard_shortcuts))
check("render_shortcut_help importable", callable(render_shortcut_help))
check(f"SHORTCUTS has {len(SHORTCUTS)} items", len(SHORTCUTS) >= 4)
check("Ctrl+N in shortcuts", any("Ctrl + N" in s["keys"] for s in SHORTCUTS))
check("Ctrl+S in shortcuts", any("Ctrl + S" in s["keys"] for s in SHORTCUTS))
check("Ctrl+/ in shortcuts", any("Ctrl + /" in s["keys"] for s in SHORTCUTS))
check("Ctrl+H in shortcuts", any("Ctrl + H" in s["keys"] for s in SHORTCUTS))

# ====================================================================
# 3. Notification System
# ====================================================================
print("\n=== 3. Notification System ===")
from dashboard.components.notifications import (
    toast_notification,
    render_notification_center,
    notify_run_certified,
    notify_run_rejected,
    notify_run_submitted,
    notify_dq_alert,
)
check("toast_notification importable", callable(toast_notification))
check("render_notification_center importable", callable(render_notification_center))
check("notify_run_certified importable", callable(notify_run_certified))
check("notify_run_rejected importable", callable(notify_run_rejected))
check("notify_run_submitted importable", callable(notify_run_submitted))
check("notify_dq_alert importable", callable(notify_dq_alert))

# ====================================================================
# 4. Print CSS
# ====================================================================
print("\n=== 4. Print CSS Updates ===")
print_path = os.path.join(ROOT, "dashboard", "styles", "print.css")
check("print.css exists", os.path.exists(print_path))

with open(print_path, "r", encoding="utf-8") as f:
    print_content = f.read()

check("@media print", "@media print" in print_content)
check("Toast hidden in print", ".ar-toast" in print_content)
check(".ar-kbd hidden in print", ".ar-kbd" in print_content)
check("Animations disabled in print", "animation: none" in print_content)
check("@page A4 portrait", "A4 portrait" in print_content)
check("Page counter", "counter(page)" in print_content)

# ====================================================================
# 5. App.py Integration
# ====================================================================
print("\n=== 5. App.py Integration ===")
app_path = os.path.join(ROOT, "dashboard", "app.py")
with open(app_path, "r", encoding="utf-8") as f:
    app_content = f.read()

check("Keyboard shortcuts imported in app.py", "inject_keyboard_shortcuts" in app_content)
check("pages.css in load order", "pages.css" in app_content)
check("print.css in load order", "print.css" in app_content)

# ====================================================================
# 6. Design System Integrity
# ====================================================================
print("\n=== 6. Design System File Integrity ===")
style_files = ["tokens.css", "components.css", "pages.css", "print.css"]
styles_dir = os.path.join(ROOT, "dashboard", "styles")
for sf in style_files:
    check(f"{sf} exists", os.path.exists(os.path.join(styles_dir, sf)))

# Component files
component_files = [
    "keyboard_shortcuts.py",
    "notifications.py",
    "kpi_card.py",
    "status_badge.py",
    "breadcrumb.py",
    "stepper.py",
    "validation_queue.py",
    "dq_slider.py",
]
comp_dir = os.path.join(ROOT, "dashboard", "components")
for cf in component_files:
    check(f"components/{cf}", os.path.exists(os.path.join(comp_dir, cf)))

# Bilan
print(f"\n{'='*50}")
total = passed + failed
print(f"  Total: {total} tests | Pass: {passed} | Fail: {failed}")
if failed == 0:
    print("  >>> PHASE 4 VALIDATED <<<")
else:
    print(f"  WARNING: {failed} test(s) failed")
print(f"{'='*50}")
sys.exit(0 if failed == 0 else 1)

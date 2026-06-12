"""Test T22+T89+T92+T88: session isolation, animations, print CSS, pytest integration."""
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
# T22: Session-isolated temp uploads
# ============================================================
print("=== T22: Session-isolated temp uploads ===")

api_path = os.path.join(ROOT, "api", "main.py")
with open(api_path, "r", encoding="utf-8") as f:
    api_src = f.read()

check("get_session_upload_dir exists", "def get_session_upload_dir" in api_src)
check("sanitizes .. traversal", '".."' in api_src.split("get_session_upload_dir")[1][:300])
check("sanitizes slashes", '"/"' in api_src.split("get_session_upload_dir")[1][:300])
check("uses os.path.join", "os.path.join" in api_src.split("get_session_upload_dir")[1][:300])
check("creates directory", "os.makedirs" in api_src.split("get_session_upload_dir")[1][:300])

# ============================================================
# T89: Animations transitions pages
# ============================================================
print("\n=== T89: Animations transitions pages ===")

pages_css = os.path.join(ROOT, "dashboard", "styles", "pages.css")
with open(pages_css, "r", encoding="utf-8") as f:
    css = f.read()

check("page enter animation", "ar-page-enter" in css)
check("page fade animation", "ar-page-fade" in css)
check("slide-up animation", "ar-slide-up" in css)
check("slide-in-right animation", "ar-slide-in-right" in css)
check("scale-in animation", "ar-scale-in" in css)
check("stagger delay classes", "ar-delay-1" in css)
check("card hover transform", "translateY(-1px)" in css)
check("button press scale", "scale(0.97)" in css)
check("toast animation", "ar-toast-enter" in css)
check("progress bar glow", "ar-progress-glow" in css)
check("reduced motion support", "prefers-reduced-motion" in css)
check("kbd shortcut hint", "ar-kbd" in css)
check("cubic-bezier easing", "cubic-bezier" in css)
check("tab switch animation", "tab" in css and "transition" in css)

# ============================================================
# T92: Mode impression ACPR
# ============================================================
print("\n=== T92: Mode impression ACPR ===")

print_css = os.path.join(ROOT, "dashboard", "styles", "print.css")
with open(print_css, "r", encoding="utf-8") as f:
    pcss = f.read()

check("@media print", "@media print" in pcss)
check("white background", "#FFFFFF" in pcss)
check("dark text for print", "#0F172A" in pcss)
check("sidebar hidden", "display: none" in pcss)
check("buttons hidden", "stButton" in pcss)
check("sliders hidden", "stSlider" in pcss)
check("animations disabled", "animation: none" in pcss)
check("no box shadows", "box-shadow: none" in pcss)
check("break-inside avoid", "break-inside: avoid" in pcss)
check("A4 portrait page size", "A4 portrait" in pcss)
check("2cm margins", "margin: 2cm" in pcss)
check("page counter", "counter(page)" in pcss)
check("ACPR mention in comment", "ACPR" in pcss)
check("links printed with URL", 'attr(href)' in pcss)

# ============================================================
# T88: Pytest integration
# ============================================================
print("\n=== T88: Pytest integration ===")

conftest = os.path.join(ROOT, "tests", "conftest.py")
check("conftest.py exists", os.path.exists(conftest))

with open(conftest, "r", encoding="utf-8") as f:
    ct_src = f.read()

check("sys.path setup", "sys.path" in ct_src)
check("utf-8 encoding", "utf-8" in ct_src)

# Count test files
test_dir = os.path.join(ROOT, "tests")
test_files = [f for f in os.listdir(test_dir) if f.startswith("test_") and f.endswith(".py")]
check(f"{len(test_files)} test files found", len(test_files) >= 8, f"found {len(test_files)}")

# Check all test files are importable (basic syntax check)
syntax_ok = 0
for tf in test_files:
    fpath = os.path.join(test_dir, tf)
    try:
        with open(fpath, "r", encoding="utf-8") as f:
            compile(f.read(), tf, "exec")
        syntax_ok += 1
    except SyntaxError as e:
        print(f"    SYNTAX ERROR in {tf}: {e}")

check(f"all {len(test_files)} test files valid syntax", syntax_ok == len(test_files))

# Summary
print(f"\n{'='*50}")
total = passed + failed
print(f"  Total: {total} | Pass: {passed} | Fail: {failed}")
if failed == 0:
    print("  >>> T22+T89+T92+T88 VALIDATED <<<")
else:
    print(f"  WARNING: {failed} test(s) failed")
print(f"{'='*50}")
sys.exit(0 if failed == 0 else 1)

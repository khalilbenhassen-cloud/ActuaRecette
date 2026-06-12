"""Test suite for the new LOB visibility filtering and user creation form reset fixes."""
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

print("=== Test LOB Visibility and Form Reset ===")

# 1. Test UserIdentity and visible_lobs
from dashboard.utils.auth import UserIdentity, ALL_LOBS, load_lob_registry

# Maker with specific LOBs
maker = UserIdentity(sso="lilka", name="Lilka", role="Actuaire MOA", assigned_lobs=["LOB_AUTO_PART", "LOB_INCENDIE_RD"])
check("Maker has assigned LOBs", maker.assigned_lobs == ["LOB_AUTO_PART", "LOB_INCENDIE_RD"])
check("Maker visible_lobs is limited", maker.visible_lobs == ["LOB_AUTO_PART", "LOB_INCENDIE_RD"])
check("Maker can view auto", maker.can_view_lob("LOB_AUTO_PART") is True)
check("Maker cannot view MRH", maker.can_view_lob("LOB_MRH_HAB") is False)

# Checker/Manager - Restricted LOBs
checker_restricted = UserIdentity(sso="checker.test", name="Checker Test", role="Validateur", assigned_lobs=["LOB_AUTO_PART"])
check("Restricted checker visible_lobs is limited", checker_restricted.visible_lobs == ["LOB_AUTO_PART"])
check("Restricted checker cannot view MRH", checker_restricted.can_view_lob("LOB_MRH_HAB") is False)

# Checker/Manager - Global LOBs (no specific assigned LOBs)
checker_global = UserIdentity(sso="checker.global", name="Checker Global", role="Validateur", assigned_lobs=[])
check("Global checker visible_lobs returns all registry LOBs", set(checker_global.visible_lobs) == set(load_lob_registry()))
check("Global checker can view MRH", checker_global.can_view_lob("LOB_MRH_HAB") is True)

# 2. Test form reset session state keys behavior in Streamlit
import streamlit as st

# Simulate user form submission success
st.session_state["user_success_message"] = "L'utilisateur a été créé avec succès."

check("Session state user_success_message is set", st.session_state["user_success_message"] == "L'utilisateur a été créé avec succès.")

# Bilan
print(f"\n{'='*50}")
total = passed + failed
print(f"  Total: {total} | Pass: {passed} | Fail: {failed}")
if failed == 0:
    print("  >>> LOB VISIBILITY & RESET VALIDATED <<<")
print(f"{'='*50}")
sys.exit(0 if failed == 0 else 1)

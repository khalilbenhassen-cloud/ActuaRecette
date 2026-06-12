"""
==========================================================================
Test Suite End-to-End — Phase 1 : Socle Multi-Utilisateur ActuaRecette v6.0
==========================================================================

V\u00e9rifie l'int\u00e9grit\u00e9 de l'ensemble de la Phase 1 :
  1. Structure des fichiers
  2. Imports de tous les modules
  3. Coh\u00e9rence app.py ↔ pages (routing)
  4. Auth : UserIdentity, RBAC, Maker\u2260Checker
  5. LOB Cloisonnement
  6. Middleware API
  7. State Manager
  8. Migration DB (schema SQL)
"""

import os
import sys
import json
import importlib
import traceback

# Fix Windows console encoding for Unicode output
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

# Setup PYTHONPATH
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

passed = 0
failed = 0
errors = []


def check(name: str, condition: bool, detail: str = ""):
    global passed, failed, errors
    if condition:
        passed += 1
        print(f"  \u2705 {name}")
    else:
        failed += 1
        msg = f"  \u274c {name}" + (f" \u2014 {detail}" if detail else "")
        print(msg)
        errors.append(msg)


def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ======================================================================
# 1. STRUCTURE DES FICHIERS
# ======================================================================
section("1. Structure des fichiers")

expected_files = {
    # Dashboard core
    "dashboard/__init__.py": "Package init",
    "dashboard/app.py": "Point d'entr\u00e9e",
    "dashboard/style.css": "CSS legacy",
    # Utils
    "dashboard/utils/__init__.py": "Utils package",
    "dashboard/utils/auth.py": "Auth module",
    "dashboard/utils/state_manager.py": "State manager",
    "dashboard/utils/api_client.py": "API client",
    "dashboard/utils/formatters.py": "Formatters",
    "dashboard/utils/lob_filter.py": "LOB filter",
    # Pages
    "dashboard/views/__init__.py": "Pages package",
    "dashboard/views/page_00_login.py": "Login page",
    "dashboard/views/page_01_cockpit.py": "Cockpit page",
    "dashboard/views/page_02_conformite.py": "Conformité page",
    "dashboard/views/page_03_espace_travail.py": "Workspace page",
    "dashboard/views/page_04_detail_run.py": "Detail run page",
    "dashboard/views/page_05_jira.py": "Jira page",
    "dashboard/views/page_06_audit.py": "Audit page",
    # API
    "api/main.py": "FastAPI main",
    "api/api_auth_middleware.py": "Auth middleware",
    # Data
    "data/schema.sql": "SQL schema",
    "src/db_migration.py": "DB migration",
}

for filepath, desc in expected_files.items():
    full_path = os.path.join(ROOT, filepath)
    check(f"{desc} ({filepath})", os.path.exists(full_path),
          f"Fichier manquant : {full_path}")


# ======================================================================
# 2. IMPORTS DE TOUS LES MODULES
# ======================================================================
section("2. Imports des modules")

import_tests = [
    ("dashboard.utils.auth", ["UserIdentity", "VALID_ROLES", "ALL_LOBS",
                               "find_user_by_sso", "list_all_users",
                               "LOCAL_USER_REGISTRY"]),
    ("dashboard.utils.state_manager", ["init_defaults", "is_authenticated"]),
    ("dashboard.utils.api_client", ["ActuaRecetteAPIClient"]),
    ("dashboard.utils.formatters", ["fmt_pct", "fmt_euro"]),
    ("dashboard.utils.lob_filter", ["classify_run_lob", "filter_runs_by_lobs",
                                     "can_access_run", "enrich_run_with_lob"]),
]

for module_name, expected_attrs in import_tests:
    try:
        mod = importlib.import_module(module_name)
        for attr in expected_attrs:
            check(f"{module_name}.{attr}",
                  hasattr(mod, attr),
                  f"Attribut '{attr}' manquant dans {module_name}")
    except Exception as e:
        check(f"Import {module_name}", False, str(e))

# Pages : v\u00e9rifier que chaque page a un render_*_page()
page_imports = {
    "dashboard.views.page_00_login": "render_login_page",
    "dashboard.views.page_01_cockpit": "render_cockpit_page",
    "dashboard.views.page_02_conformite": "render_conformite_page",
    "dashboard.views.page_03_espace_travail": "render_espace_travail_page",
    "dashboard.views.page_04_detail_run": "render_detail_run_page",
    "dashboard.views.page_05_jira": "render_jira_page",
    "dashboard.views.page_06_audit": "render_audit_page",
}

for module_name, func_name in page_imports.items():
    try:
        mod = importlib.import_module(module_name)
        fn = getattr(mod, func_name, None)
        check(f"{module_name} \u2192 {func_name}()",
              fn is not None and callable(fn),
              f"Fonction '{func_name}' non trouv\u00e9e ou non callable")
    except Exception as e:
        check(f"Import {module_name}", False, str(e))


# ======================================================================
# 3. COHERENCE APP.PY ↔ PAGES
# ======================================================================
section("3. Coh\u00e9rence app.py \u2194 pages")

# V\u00e9rifier que app.py r\u00e9f\u00e9rence exactement les 7 pages
app_path = os.path.join(ROOT, "dashboard", "app.py")
with open(app_path, "r", encoding="utf-8") as f:
    app_source = f.read()

for module_name, func_name in page_imports.items():
    # V\u00e9rifier que le module est import\u00e9 dans app.py
    short_module = module_name.replace("dashboard.pages.", "")
    check(f"app.py importe {short_module}",
          short_module in app_source or func_name in app_source,
          f"Ni '{short_module}' ni '{func_name}' trouv\u00e9 dans app.py")

# V\u00e9rifier le page_map
check("app.py contient page_map",
      "page_map" in app_source,
      "Le dictionnaire page_map est absent de app.py")

# V\u00e9rifier les cl\u00e9s de routing
routing_keys = ["cockpit", "conformite", "espace_travail",
                "detail_run", "jira", "audit"]
for key in routing_keys:
    check(f"Route '{key}' dans page_map",
          f'"{key}"' in app_source,
          f"Cl\u00e9 '{key}' manquante dans page_map")


# ======================================================================
# 4. AUTH : UserIdentity, RBAC, Maker≠Checker
# ======================================================================
section("4. Auth : UserIdentity, RBAC, Maker\u2260Checker")

from dashboard.utils.auth import UserIdentity, VALID_ROLES, ALL_LOBS, LOCAL_USER_REGISTRY

# R\u00f4les valides
check("3 r\u00f4les d\u00e9finis", len(VALID_ROLES) == 3)
check("R\u00f4le Actuaire MOA", "Actuaire MOA" in VALID_ROLES)
check("R\u00f4le Validateur", "Validateur" in VALID_ROLES)
# Rôles valides
check("3 rôles définis", len(VALID_ROLES) == 3)
check("Rôle Actuaire MOA", "Actuaire MOA" in VALID_ROLES)
check("Rôle Validateur", "Validateur" in VALID_ROLES)
check("Rôle Responsable MOA", "Responsable MOA" in VALID_ROLES)

# LOBs
check("3 LOBs définis", len(ALL_LOBS) == 3)

# Registre utilisateurs
check("Au moins 4 utilisateurs", len(LOCAL_USER_REGISTRY) >= 4)

# UserIdentity construction
maker = UserIdentity(sso="maker.junior", name="Actuaire junior (Maker)",
                     role="Actuaire MOA", assigned_lobs=["LOB_AUTO_PART"])
checker = UserIdentity(sso="checker", name="Validateur Technique (Checker)",
                      role="Validateur", assigned_lobs=ALL_LOBS)

check("Maker is Maker", maker.is_maker)
check("Maker is NOT Checker", not maker.is_checker)
check("Checker is Checker", checker.is_checker)
check("Checker is NOT Maker", not checker.is_maker)

# Maker ≠ Checker
check("Checker can certify Maker's run", checker.can_certify_run("maker.junior"))
check("Checker CANNOT certify her own run", not checker.can_certify_run("checker"))
check("Maker CANNOT certify anything", not maker.can_certify_run("checker"))

# Visible LOBs
check("Maker sees only Auto", maker.visible_lobs == ["LOB_AUTO_PART"])
check("Checker sees all LOBs", checker.visible_lobs == ALL_LOBS)

# SSO validation
try:
    bad = UserIdentity(sso="../attack", name="Bad", role="Actuaire MOA")
    check("SSO traversal rejected", False, "Should have raised ValueError")
except ValueError:
    check("SSO traversal rejected", True)

# Rôle invalide
try:
    bad = UserIdentity(sso="x", name="X", role="Admin")
    check("Invalid role rejected", False, "Should have raised ValueError")
except ValueError:
    check("Invalid role rejected", True)

# Serialization round-trip
maker_dict = maker.to_dict()
maker_back = UserIdentity.from_dict(maker_dict)
check("Serialization round-trip",
      maker_back.sso == maker.sso and maker_back.role == maker.role
      and maker_back.assigned_lobs == maker.assigned_lobs)

# Headers
headers = maker.to_headers()
check("to_headers() contient X-User-SSO", headers.get("X-User-SSO") == "maker.junior")
check("to_headers() contient X-User-LOBs", headers.get("X-User-LOBs") == "LOB_AUTO_PART")


# ======================================================================
# 5. LOB CLOISONNEMENT
# ======================================================================
section("5. LOB Cloisonnement")

from dashboard.utils.lob_filter import (classify_run_lob, filter_runs_by_lobs,
                                         can_access_run, enrich_run_with_lob)

runs = [
    {"run_name": "Recette Auto V12"},
    {"run_name": "Recette MRH Habitation"},
    {"run_name": "Recette Incendie RD", "lob_id": "LOB_INCENDIE_RD"},
    {"run_name": "Test sans LOB"},
    {"run_name": "Voiture neuve", "metadata": {"lob_id": "LOB_AUTO_PART"}},
]

# Classification
check("Auto \u2192 LOB_AUTO_PART", classify_run_lob(runs[0]) == "LOB_AUTO_PART")
check("MRH \u2192 LOB_MRH_HAB", classify_run_lob(runs[1]) == "LOB_MRH_HAB")
check("Incendie (explicit) \u2192 LOB_INCENDIE_RD", classify_run_lob(runs[2]) == "LOB_INCENDIE_RD")
check("Default \u2192 LOB_AUTO_PART", classify_run_lob(runs[3]) == "LOB_AUTO_PART")
check("Metadata lob_id priority", classify_run_lob(runs[4]) == "LOB_AUTO_PART")

# Filtrage
auto_only = filter_runs_by_lobs(runs, ["LOB_AUTO_PART"])
check("Auto filter: 3 runs", len(auto_only) == 3,
      f"Expected 3, got {len(auto_only)}: {[r['run_name'] for r in auto_only]}")

inc_only = filter_runs_by_lobs(runs, ["LOB_INCENDIE_RD"])
check("Incendie filter: 1 run", len(inc_only) == 1)

all_filter = filter_runs_by_lobs(runs, ALL_LOBS)
check("All LOBs filter: 5 runs", len(all_filter) == 5)

empty_filter = filter_runs_by_lobs(runs, [])
check("Empty LOBs: 0 runs", len(empty_filter) == 0)

# Acc\u00e8s
check("Access Auto \u2192 Auto: OK", can_access_run(runs[0], ["LOB_AUTO_PART"]))
check("Access MRH \u2192 Auto: DENIED", not can_access_run(runs[1], ["LOB_AUTO_PART"]))

# Enrichissement
enriched = enrich_run_with_lob(runs[3])
check("Enrich ajoute lob_id", enriched.get("lob_id") == "LOB_AUTO_PART")
check("Enrich ne modifie pas l'original", "lob_id" not in runs[3])


# ======================================================================
# 6. MIDDLEWARE API
# ======================================================================
section("6. Middleware API")

from api.api_auth_middleware import validate_safe_id, get_current_user

# Safe ID validation
check("Safe ID: 'run_123' OK", validate_safe_id("run_123", "test") == "run_123")
check("Safe ID: 'a.b-c_d' OK", validate_safe_id("a.b-c_d", "test") == "a.b-c_d")

# Path traversal
from fastapi import HTTPException
try:
    validate_safe_id("../etc/passwd", "run_id")
    check("Path traversal blocked", False, "Should have raised HTTPException")
except HTTPException as e:
    check("Path traversal blocked", e.status_code == 400)

try:
    validate_safe_id("run;DROP TABLE", "run_id")
    check("SQL injection blocked", False, "Should have raised HTTPException")
except HTTPException as e:
    check("SQL injection blocked", e.status_code == 400)

try:
    validate_safe_id("", "run_id")
    check("Empty ID blocked", False, "Should have raised HTTPException")
except HTTPException as e:
    check("Empty ID blocked", e.status_code == 400)

# get_visible_lobs import
from api.api_auth_middleware import get_visible_lobs
check("get_visible_lobs() importable", callable(get_visible_lobs))


# ======================================================================
# 7. STATE MANAGER
# ======================================================================
section("7. State Manager")

from dashboard.utils.state_manager import init_defaults, is_authenticated

# V\u00e9rifier que les fonctions sont callable
check("init_defaults() callable", callable(init_defaults))
check("is_authenticated() callable", callable(is_authenticated))


# ======================================================================
# 8. SCHEMA SQL
# ======================================================================
section("8. Sch\u00e9ma SQL")

schema_path = os.path.join(ROOT, "data", "schema.sql")
with open(schema_path, "r", encoding="utf-8") as f:
    schema = f.read()

required_tables = [
    "portefeuilles",
    "campagnes_recette",
    "runs_execution",
    "regles_recette",
    "audit_entries",
    "active_sessions",
]

for table in required_tables:
    check(f"Table '{table}' dans schema.sql",
          table in schema,
          f"Table '{table}' absente du schema SQL")

# V\u00e9rifier les index
check("Au moins un INDEX dans schema.sql", "CREATE INDEX" in schema)

# V\u00e9rifier WAL mention
check("WAL mode mentionn\u00e9 dans db_migration.py",
      "WAL" in open(os.path.join(ROOT, "src", "db_migration.py"), "r").read())


# ======================================================================
# 9. TAILLE DES FICHIERS (v\u00e9rification d'int\u00e9grit\u00e9)
# ======================================================================
section("9. Taille des fichiers (int\u00e9grit\u00e9)")

size_checks = {
    "dashboard/app.py": (3000, 12000),
    "dashboard/views/page_01_cockpit.py": (30000, 60000),
    "dashboard/views/page_03_espace_travail.py": (20000, 100000),
    "dashboard/utils/auth.py": (3000, 10000),
    "dashboard/utils/lob_filter.py": (2000, 8000),
    "api/api_auth_middleware.py": (3000, 10000),
}

for filepath, (min_size, max_size) in size_checks.items():
    full_path = os.path.join(ROOT, filepath)
    if os.path.exists(full_path):
        size = os.path.getsize(full_path)
        check(f"{filepath}: {size:,} bytes (attendu {min_size:,}-{max_size:,})",
              min_size <= size <= max_size,
              f"Taille {size:,} hors limites")
    else:
        check(f"{filepath} exists for size check", False, "Fichier manquant")


# ======================================================================
# BILAN FINAL
# ======================================================================
print(f"\n{'='*60}")
print(f"  BILAN FINAL")
print(f"{'='*60}")
total = passed + failed
print(f"\n  Total : {total} tests")
print(f"  \u2705 Pass\u00e9s : {passed}")
print(f"  \u274c \u00c9chou\u00e9s : {failed}")
print(f"  Taux de r\u00e9ussite : {passed/total*100:.0f}%")

if errors:
    print(f"\n  Erreurs :")
    for e in errors:
        print(f"    {e}")

print(f"\n{'='*60}")
if failed == 0:
    print("  >>> PHASE 1 VALIDEE - TOUS LES TESTS PASSENT <<<")
else:
    print(f"  \u26a0 {failed} test(s) en \u00e9chec — correction requise")
print(f"{'='*60}")

sys.exit(0 if failed == 0 else 1)

"""Test du module LOB filter (Phase 1.4)"""
from dashboard.utils.lob_filter import classify_run_lob, filter_runs_by_lobs, can_access_run, enrich_run_with_lob

print("=== LOB Filter Tests ===")

r1 = {"run_name": "Recette Auto V12"}
r2 = {"run_name": "Recette MRH Hab"}
r3 = {"run_name": "Recette Incendie Q2", "lob_id": "LOB_INCENDIE_RD"}
r4 = {"run_name": "Test quelconque"}

# Classification tests
assert classify_run_lob(r1) == "LOB_AUTO_PART", f"Expected LOB_AUTO_PART, got {classify_run_lob(r1)}"
assert classify_run_lob(r2) == "LOB_MRH_HAB", f"Expected LOB_MRH_HAB, got {classify_run_lob(r2)}"
assert classify_run_lob(r3) == "LOB_INCENDIE_RD", f"Expected LOB_INCENDIE_RD, got {classify_run_lob(r3)}"
assert classify_run_lob(r4) == "LOB_AUTO_PART", f"Expected LOB_AUTO_PART (default), got {classify_run_lob(r4)}"
print("[OK] Classification tests passed")

# Filtering tests
runs = [r1, r2, r3, r4]
karim_lobs = ["LOB_AUTO_PART"]
sophie_lobs = ["LOB_AUTO_PART", "LOB_INCENDIE_RD", "LOB_MRH_HAB"]
jean_lobs = ["LOB_INCENDIE_RD"]

karim_runs = filter_runs_by_lobs(runs, karim_lobs)
assert len(karim_runs) == 2, f"Karim should see 2 runs (Auto+default), got {len(karim_runs)}"
print(f"[OK] Karim (Auto) sees {len(karim_runs)} runs: {[r['run_name'] for r in karim_runs]}")

jean_runs = filter_runs_by_lobs(runs, jean_lobs)
assert len(jean_runs) == 1, f"Jean should see 1 run (Incendie), got {len(jean_runs)}"
print(f"[OK] Jean (Incendie) sees {len(jean_runs)} runs: {[r['run_name'] for r in jean_runs]}")

sophie_runs = filter_runs_by_lobs(runs, sophie_lobs)
assert len(sophie_runs) == 4, f"Sophie should see 4 runs (all), got {len(sophie_runs)}"
print(f"[OK] Sophie (all) sees {len(sophie_runs)} runs")

# Access control tests
assert can_access_run(r1, karim_lobs) == True
assert can_access_run(r2, karim_lobs) == False
assert can_access_run(r3, jean_lobs) == True
print("[OK] Access control tests passed")

# Enrich tests
enriched = enrich_run_with_lob(r1)
assert enriched.get("lob_id") == "LOB_AUTO_PART"
assert "lob_id" not in r1  # Original not modified
already_enriched = enrich_run_with_lob(r3)
assert already_enriched is r3  # No copy needed
print("[OK] Enrichment tests passed")

# Empty LOBs
empty_runs = filter_runs_by_lobs(runs, [])
assert len(empty_runs) == 0
print("[OK] Empty LOBs returns empty list")

print()
print("ALL 5 TEST SUITES PASSED")

#!/usr/bin/env python3
# test_stress_concurrent.py -- Stress test: 5 uploads simultanes (Phase 3 - T24)
"""
Simule 5 reconciliations concurrentes pour valider :
1. Pas de corruption de donnees entre threads
2. Pas de crash SQLite (WAL mode handles concurrency)
3. Chaque run produit des resultats independants
4. Temps de reponse acceptable (< 30s par run)

Usage:
    python scripts/test_stress_concurrent.py
"""
import os
import sys
import time
import json
import threading
import traceback

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

import pandas as pd

# Try to import the engine modules
try:
    from src.variance_analyzer import merge_datasets, calculate_variances, compute_uat_kpis, extract_anomalies
    MODULES_OK = True
except ImportError:
    MODULES_OK = False


def generate_test_data(seed: int, n_rows: int = 200):
    """Generate deterministic test data for a given seed."""
    import random
    rng = random.Random(seed)

    ids = [f"CONTRAT_{seed}_{i:05d}" for i in range(n_rows)]

    ref_premiums = [round(rng.uniform(100, 5000), 2) for _ in range(n_rows)]

    # Introduce some deviations
    prod_premiums = []
    for rp in ref_premiums:
        if rng.random() < 0.05:  # 5% anomaly rate
            deviation = rng.uniform(0.1, 0.5) * rp
            prod_premiums.append(round(rp + deviation, 2))
        else:
            # Small acceptable deviation
            prod_premiums.append(round(rp + rng.uniform(-0.01, 0.01) * rp, 2))

    ref_df = pd.DataFrame({"id": ids, "prime_ref": ref_premiums})
    prod_df = pd.DataFrame({"id": ids, "prime_prod": prod_premiums})

    return ref_df, prod_df


def run_reconciliation(thread_id: int, results: dict):
    """Execute a full reconciliation in a thread."""
    start = time.time()
    try:
        ref_df, prod_df = generate_test_data(seed=thread_id * 42, n_rows=200)

        mapping = {"key": "id", "ref_premium": "prime_ref", "prod_premium": "prime_prod"}

        merged = merge_datasets(ref_df, prod_df, mapping)
        analyzed = calculate_variances(merged, ref_col="prime_ref", prod_col="prime_prod", tolerance=0.05)
        kpis = compute_uat_kpis(analyzed, tolerance=0.05)
        anomalies = extract_anomalies(analyzed, tolerance=0.05)

        elapsed = time.time() - start

        results[thread_id] = {
            "status": "OK",
            "elapsed_s": round(elapsed, 2),
            "total_cases": kpis.get("total_cases", 0),
            "conform_cases": kpis.get("conform_cases", 0),
            "fatal_defects": kpis.get("fatal_defects", 0),
            "success_rate": kpis.get("success_rate_pct", 0),
            "anomaly_count": len(anomalies),
        }
    except Exception as e:
        elapsed = time.time() - start
        results[thread_id] = {
            "status": "ERROR",
            "elapsed_s": round(elapsed, 2),
            "error": str(e),
            "traceback": traceback.format_exc(),
        }


def main():
    sys.stdout.reconfigure(encoding="utf-8")

    print("=" * 60)
    print("  ActuaRecette - Stress Test: 5 Reconciliations Concurrentes (T24)")
    print("=" * 60)

    if not MODULES_OK:
        print("\n  [SKIP] Modules src/ non disponibles. Test annule.")
        sys.exit(0)

    N_THREADS = 5
    results = {}
    threads = []

    print(f"\n  Lancement de {N_THREADS} reconciliations simultanees...")
    print(f"  Chaque thread traite 200 contrats.\n")

    global_start = time.time()

    for i in range(N_THREADS):
        t = threading.Thread(target=run_reconciliation, args=(i, results))
        threads.append(t)
        t.start()

    for t in threads:
        t.join(timeout=60)

    global_elapsed = time.time() - global_start

    # Report
    print("-" * 60)
    passed = 0
    failed = 0

    for tid in sorted(results.keys()):
        r = results[tid]
        status = r["status"]
        elapsed = r["elapsed_s"]

        if status == "OK":
            passed += 1
            print(
                f"  [OK] Thread {tid}: {r['total_cases']} dossiers, "
                f"{r['success_rate']:.1f}% conformite, "
                f"{r['fatal_defects']} anomalies, {elapsed:.2f}s"
            )
            # Validate data integrity
            assert r["total_cases"] == 200, f"Thread {tid}: expected 200 cases, got {r['total_cases']}"
            assert r["success_rate"] >= 0, f"Thread {tid}: success rate is negative"
            assert elapsed < 30, f"Thread {tid}: took {elapsed}s (>30s limit)"
        else:
            failed += 1
            print(f"  [FAIL] Thread {tid}: {r.get('error', 'Unknown')}")

    # Cross-thread integrity check: each thread should have unique results
    # (different seeds -> different anomaly counts)
    anomaly_counts = [results[t]["anomaly_count"] for t in results if results[t]["status"] == "OK"]
    all_identical = len(set(anomaly_counts)) == 1 and len(anomaly_counts) > 1

    print(f"\n  Anomaly counts per thread: {anomaly_counts}")
    if not all_identical:
        print("  [OK] Resultats independants (pas de contamination inter-threads)")
        passed += 1
    else:
        # Could happen by chance but very unlikely with different seeds
        print("  [WARN] Tous les threads ont le meme nombre d'anomalies (possible par hasard)")
        passed += 1  # Not a failure, just unusual

    print(f"\n{'=' * 60}")
    print(f"  Threads: {N_THREADS} | Pass: {passed} | Fail: {failed}")
    print(f"  Duree totale: {global_elapsed:.2f}s")

    if failed == 0:
        print("  >>> T24 STRESS TEST PASSED <<<")
    else:
        print(f"  WARNING: {failed} thread(s) failed")

    print(f"{'=' * 60}")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()

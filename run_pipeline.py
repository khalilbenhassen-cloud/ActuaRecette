"""
ActuaRecette - Pipeline Orchestrator & Initialization Script
=============================================================

This script is the main orchestrator for the ActuaRecette platform.
It automatically sets up the environment by:
1. Creating the required directories (data/ and data/uat_runs/).
2. Generating a realistic Actuarial Reference CSV (data/actuarial_ref.csv) with 100 client profiles.
3. Generating a Production DSI CSV (data/dsi_prod.csv) with minor rounding noises, 
   specific mathematical defects, and an ETL data quality outlier.
4. Executing an in-memory reconciliation with a 0.05 EUR tolerance (giving a 97% UAT success rate)
   and persisting this run in history as the initial UAT Baseline campaign.
5. Printing a detailed summary of the generation and validation metrics.

Author: Senior MLOps / DevOps Engineer & Software Quality Expert
Version: 1.0.0
"""

import os
import json
import datetime
import numpy as np
import pandas as pd

# Core business logic imports
from src.data_profiler import load_csv, validate_column_mapping, check_data_quality
from src.variance_analyzer import merge_datasets, calculate_variances, compute_uat_kpis, extract_anomalies
from src.anomaly_manager import save_uat_run

def main():
    print("=" * 80)
    print("[INITIALIZATION] STARTING ACTUARECETTE INITIALIZATION PIPELINE")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # STEP 1: Directory Setup
    # -------------------------------------------------------------------------
    print("\n[STEP 1/5] Setting up project directories...")
    data_dir = "data"
    runs_dir = os.path.join(data_dir, "uat_runs")
    
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(runs_dir, exist_ok=True)
    print(f"      [OK] Directory '{data_dir}' is ready.")
    print(f"      [OK] Directory '{runs_dir}' is ready.")

    # -------------------------------------------------------------------------
    # STEP 2: Actuarial Reference Generation (data/actuarial_ref.csv)
    # -------------------------------------------------------------------------
    print("\n[STEP 2/5] Generating Actuarial Reference dataset (100 profiles)...")
    
    # Fixed seed for perfect reproducibility
    np.random.seed(42)
    
    # ID_CLIENT from C001 to C100
    ids = [f"C{i:03d}" for i in range(1, 101)]
    
    # Driver Age: Normally distributed around 45, clipped to [18, 80]
    ages = np.random.normal(loc=45, scale=15, size=100)
    ages = np.clip(ages, 18, 80).astype(int)
    
    # Enforce C070 to be a young driver of 20 years old
    ages[69] = 20  # C070 (index 69)
    
    # License Experience: Age - 18, minimum 0
    experience = ages - 18
    experience = np.clip(experience, 0, None)
    
    # Enforce C070 driver experience
    experience[69] = 2
    
    # Vehicle Type
    vehicle_types_choices = ["Citadine", "Berline", "SUV", "Sportive"]
    vehicle_types = np.random.choice(vehicle_types_choices, size=100)
    
    # Enforce C090 to be an SUV
    vehicle_types[89] = "SUV"  # C090 (index 89)
    
    # Horsepower (puissance_vehicule) between 60 and 250 ch
    horsepower = np.random.randint(60, 250, size=100)
    
    # Enforce C090 power to be high (> 150 ch)
    horsepower[89] = 180
    
    # Geographical Zone
    zones_choices = ["Urbain Dense", "Urbain Standard", "Rural"]
    zones = np.random.choice(zones_choices, size=100)
    
    # Usage
    usages_choices = ["Prive", "Prive-Trajet", "Professionnel"]
    usages = np.random.choice(usages_choices, size=100)
    
    # Annual Kilometrage
    kilometrage = np.random.randint(5, 36, size=100) * 1000
    
    # Bonus-Malus CRM
    crm_choices = [0.50, 0.68, 0.76, 0.85, 0.95, 1.00, 1.10, 1.25, 1.50]
    bonus_malus = np.random.choice(crm_choices, size=100)
    
    # Enforce C080 to have a high bonus (0.50)
    bonus_malus[79] = 0.50  # C080 (index 79)
    
    # Calculate realist PRIME_REF based on multiplicative rules
    prime_ref = []
    for i in range(100):
        bm = bonus_malus[i]
        age = ages[i]
        pwr = horsepower[i]
        zone = zones[i]
        
        # Factor rules
        factor_age = 1.5 if age < 25 else 1.0
        factor_power = 1.3 if pwr > 150 else 1.0
        factor_zone = 1.2 if zone == "Urbain Dense" else 1.0
        
        calculated_premium = 250.0 * bm * factor_age * factor_power * factor_zone
        prime_ref.append(round(calculated_premium, 2))
        
    # Build Reference DataFrame
    ref_df = pd.DataFrame({
        "ID_CLIENT": ids,
        "age_conducteur": ages,
        "experience_permis": experience,
        "type_vehicule": vehicle_types,
        "puissance_vehicule": horsepower,
        "zone_geographique": zones,
        "usage": usages,
        "kilometrage_annuel": kilometrage,
        "bonus_malus": bonus_malus,
        "PRIME_REF": prime_ref
    })
    
    # Enforce ETL quality outlier for C099 (index 98): set age_conducteur to "non_renseigne"
    # We do this after calculating PRIME_REF to prevent type conversion crashes in calculation loop
    ref_df["age_conducteur"] = ref_df["age_conducteur"].astype(object)
    ref_df.loc[98, "age_conducteur"] = "non_renseigne"
    
    # Write to CSV
    ref_path = os.path.join(data_dir, "actuarial_ref.csv")
    ref_df.to_csv(ref_path, index=False, encoding="utf-8")
    print(f"      [OK] Reference CSV written to '{ref_path}' successfully.")

    # -------------------------------------------------------------------------
    # STEP 3: Production DSI Generation (data/dsi_prod.csv)
    # -------------------------------------------------------------------------
    print("\n[STEP 3/5] Generating DSI Production dataset (100 profiles with UAT variances)...")
    
    # Copy profiles
    prod_df = ref_df.copy()
    
    # Remove PRIME_REF and replace it with PRIME_DSI containing UAT anomalies
    prime_dsi = list(prime_ref)
    
    # 1. Dossiers with micro-rounding differences (0.01 - 0.03 EUR)
    # C010 (index 9), C020 (index 19), C030 (index 29), C040 (index 39), C050 (index 49)
    prime_dsi[9] = round(prime_ref[9] + 0.01, 2)
    prime_dsi[19] = round(prime_ref[19] + 0.02, 2)
    prime_dsi[29] = round(prime_ref[29] + 0.03, 2)
    prime_dsi[39] = round(prime_ref[39] + 0.01, 2)
    prime_dsi[49] = round(prime_ref[49] + 0.02, 2)
    
    # 2. Dossiers with fatal mathematical bugs
    # C070 (index 69): Young driver (age 20) with DSI mapping mistake (+18.50 EUR)
    prime_dsi[69] = round(prime_ref[69] + 18.50, 2)
    
    # C080 (index 79): High bonus driver (CRM 0.50) missing premium minimum floor (-25.00 EUR)
    prime_dsi[79] = round(prime_ref[79] - 25.00, 2)
    
    # C090 (index 89): Powerful SUV driver (180 ch) with wrong calculation coefficient (+45.00 EUR)
    prime_dsi[89] = round(prime_ref[89] + 45.00, 2)
    
    # Add PRIME_DSI to DataFrame and drop PRIME_REF
    prod_df["PRIME_DSI"] = prime_dsi
    prod_df = prod_df.drop(columns=["PRIME_REF"])
    
    # Write to CSV
    prod_path = os.path.join(data_dir, "dsi_prod.csv")
    prod_df.to_csv(prod_path, index=False, encoding="utf-8")
    print(f"      [OK] DSI Production CSV written to '{prod_path}' successfully.")

    # -------------------------------------------------------------------------
    # STEP 4: Reconciliation and Persistence of the Baseline MVP Campaign
    # -------------------------------------------------------------------------
    print("\n[STEP 4/5] Running baseline actuarial reconciliation (tolerance 0.05 EUR)...")
    
    # 1. Load CSVs internally via the robust data profiler
    df_ref_loaded = load_csv(ref_path)
    df_prod_loaded = load_csv(prod_path)
    
    # 2. Validate structural mapping
    ref_map = {"id_assure": "ID_CLIENT", "prime_technique": "PRIME_REF"}
    prod_map = {"id_assure": "ID_CLIENT", "prime_technique": "PRIME_DSI"}
    
    ref_map_status = validate_column_mapping(df_ref_loaded, ref_map)
    prod_map_status = validate_column_mapping(df_prod_loaded, prod_map)
    
    if not ref_map_status["is_valid"] or not prod_map_status["is_valid"]:
        raise ValueError("Error: Column mapping validation failed for baseline datasets.")
        
    print("      [OK] Column mappings validated successfully.")
    
    # 3. Check Data Quality (ETL audit validation)
    ref_quality_map = {
        "id_assure": "ID_CLIENT",
        "prime_technique": "PRIME_REF",
        "age_assure": "age_conducteur",
        "bonus_malus": "bonus_malus",
        "type_vehicule": "type_vehicule"
    }
    quality_status = check_data_quality(df_ref_loaded, ref_quality_map)
    print(f"      [INFO] Data quality audit triggered. Warnings found: {len(quality_status['warnings'])}")
    for w in quality_status["warnings"]:
        print(f"             - {w}")
        
    # 4. Math Reconciliation and Variance computation
    key_mapping_analyzer = {
        "key": "ID_CLIENT",
        "ref_premium": "PRIME_REF",
        "prod_premium": "PRIME_DSI"
    }
    
    # Join on ID_CLIENT
    merged_df = merge_datasets(df_ref_loaded, df_prod_loaded, key_mapping_analyzer)
    
    # Calculate variances at 0.05 EUR tolerance
    tolerance = 0.05
    analyzed_df = calculate_variances(
        merged_df,
        ref_col="PRIME_REF",
        prod_col="PRIME_DSI",
        tolerance=tolerance
    )
    
    # Compute baseline KPIs (expected 97% success rate since 97 conform cases out of 100)
    kpis = compute_uat_kpis(analyzed_df, tolerance)
    
    # Extract detailed fatal defects list
    anomalies_df = extract_anomalies(analyzed_df, tolerance)
    anomalies_list = anomalies_df.to_dict(orient="records")
    
    # 5. Persist this UAT Run in data/uat_runs/
    baseline_run_name = "Recette Initiale - Baseline MVP"
    run_file_path = save_uat_run(
        history_dir=runs_dir,
        run_name=baseline_run_name,
        kpis=kpis,
        anomalies=anomalies_list
    )
    
    print(f"      [OK] Baseline UAT Run saved to: '{run_file_path}'")
    print(f"      [INFO] Baseline Success Rate: {kpis['success_rate_pct']}%")
    print(f"      [INFO] Baseline Fatal Defects: {kpis['fatal_defects']} (C070, C080, C090)")
    print(f"      [INFO] Baseline Status: {kpis['final_status']}")

    # -------------------------------------------------------------------------
    # STEP 5: Success Summary and Action Plan
    # -------------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("[SUCCESS] ACTUARECETTE INITIALIZATION PIPELINE EXECUTED SUCCESSFULLY!")
    print("=" * 80)
    print("\nSummary of accomplishments:")
    print(" 1. Directory Tree: Configured 'data/' and 'data/uat_runs/' paths.")
    print(" 2. Actuarial Reference: Generated 100 profiles under 'data/actuarial_ref.csv'.")
    print(" 3. Production calcul: Generated 100 entries under 'data/dsi_prod.csv'.")
    print("    - 91 profiles with perfect matching premium.")
    print("    - 5 profiles containing minor micro-rounding deviations.")
    print("    - 3 profiles containing critical financial bugs (C070, C080, C090).")
    print("    - 1 profile containing a non-numeric driver age quality alert (C099).")
    print(" 4. Baseline UAT Campaign: Run and stored inside history archive.")
    print("\nYour demo environment is now rich in data and completely ready for exploration.")
    print("To explore the interactive Web UI and review UAT and history metrics, run:")
    print("    python -m streamlit run dashboard/app.py")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    main()

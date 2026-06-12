import os
import json
import sqlite3

print("--- Checking uat_runs directory ---")
runs_dir = "data/uat_runs"
if os.path.exists(runs_dir):
    files = os.listdir(runs_dir)
    print(f"Total files in uat_runs: {len(files)}")
    for f in sorted(files)[:10]:
        print(f" - {f}")
        try:
            with open(os.path.join(runs_dir, f), "r", encoding="utf-8") as file:
                data = json.load(file)
                print(f"   Name: {data.get('run_name')}, LOB: {data.get('lob_id')}, Status: {data.get('kpis', {}).get('final_status')}")
        except Exception as e:
            print(f"   Error reading: {e}")
else:
    print("uat_runs directory does not exist.")

print("\n--- Checking SQLite DBs ---")
for db_path in ["data/actuarecette.db", "data/actuarecette_v2.db"]:
    if os.path.exists(db_path):
        print(f"\nDB: {db_path}")
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            
            cur.execute("SELECT id_run, id_campagne, num_run, statut_validation, maker_sso_user FROM runs_execution")
            rows = cur.fetchall()
            print(f"Total runs in runs_execution: {len(rows)}")
            for r in rows:
                print(f" - {r}")
                
            cur.execute("SELECT id_campagne, id_portefeuille, periode, type_testing FROM campagnes_recette")
            camps = cur.fetchall()
            print(f"Total campaigns: {len(camps)}")
            for c in camps:
                print(f" - {c}")
                
            conn.close()
        except Exception as e:
            print(f"Error checking DB: {e}")
    else:
        print(f"{db_path} does not exist.")

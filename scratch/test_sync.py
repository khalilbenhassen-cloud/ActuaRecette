import sys
import os
sys.path.append(os.path.abspath("."))

import sqlite3
from src.run_persistence import sync_run_to_db

run_id = "run_ba1df967bc7a"
print(f"Triggering sync for {run_id}...")
sync_run_to_db(run_id)

print("Checking databases...")
db_paths = ["data/actuarecette.db", "data/actuarecette_v2.db"]
for db_path in db_paths:
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        row = conn.execute("SELECT id_run, statut_validation, maker_sso_user FROM runs_execution WHERE id_run = ?", [run_id]).fetchone()
        if row:
            print(f"{db_path}: found run {row[0]}, status: {row[1]}, maker: {row[2]}")
        else:
            print(f"{db_path}: run {run_id} NOT found")
        conn.close()
    else:
        print(f"{db_path} does not exist")

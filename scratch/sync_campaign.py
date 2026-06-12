import sys
import os

sys.path.insert(0, os.path.abspath("."))

from src.run_persistence import sync_run_to_db

runs_dir = "data/uat_runs"
if os.path.exists(runs_dir):
    for f in os.listdir(runs_dir):
        if f.endswith(".json"):
            run_id = f.replace(".json", "")
            print(f"Syncing {run_id}...")
            try:
                sync_run_to_db(run_id, runs_dir)
            except Exception as e:
                print(f"Failed to sync {run_id}: {e}")
print("All syncs finished.")

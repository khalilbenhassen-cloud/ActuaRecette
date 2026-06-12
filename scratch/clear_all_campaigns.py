import os
import sqlite3
import json

def clear_campaigns():
    print("Starting cleanup of all campaigns and history...")
    
    # 1. Delete files in data/uat_runs
    runs_dir = "data/uat_runs"
    if os.path.exists(runs_dir):
        for f in os.listdir(runs_dir):
            if f.endswith((".json", ".pdf", ".zip")):
                path = os.path.join(runs_dir, f)
                os.remove(path)
                print(f"Deleted file: {f}")
                
    # 2. Delete files in data/saved_datasets
    datasets_dir = "data/saved_datasets"
    if os.path.exists(datasets_dir):
        for f in os.listdir(datasets_dir):
            if f.endswith(".csv"):
                path = os.path.join(datasets_dir, f)
                os.remove(path)
                print(f"Deleted dataset: {f}")
                
    # 3. Reset audit_log.json
    audit_file = "data/audit_log.json"
    if os.path.exists(audit_file):
        with open(audit_file, "w", encoding="utf-8") as f:
            json.dump([], f)
        print("Reset audit_log.json to empty list.")
        
    # 4. Clear audit_entries table in databases
    for db in ["data/actuarecette.db", "data/actuarecette_v2.db"]:
        if os.path.exists(db):
            try:
                conn = sqlite3.connect(db)
                cursor = conn.cursor()
                # Clear campaigns/runs tables just in case
                cursor.execute("DELETE FROM campagnes_recette")
                cursor.execute("DELETE FROM runs_execution")
                cursor.execute("DELETE FROM trend_snapshots")
                # Clear audit logs
                cursor.execute("DELETE FROM audit_entries")
                # Clear notifications
                cursor.execute("DELETE FROM notifications")
                # Commit and vacuum
                conn.commit()
                cursor.execute("VACUUM")
                conn.close()
                print(f"Cleared SQLite tables in {db}")
            except Exception as e:
                print(f"Error clearing {db}: {e}")
                
    print("Cleanup completed successfully. The application is now virgin of all campaigns!")

if __name__ == "__main__":
    clear_campaigns()

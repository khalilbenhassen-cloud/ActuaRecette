import sqlite3
import os

db_paths = ["data/actuarecette.db", "data/actuarecette_v2.db"]
for db_path in db_paths:
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM runs_execution").fetchall()
        print(f"{db_path}: {len(rows)} runs in runs_execution")
        for r in rows:
            print(dict(r))
        conn.close()
    else:
        print(f"{db_path} does not exist")
        
# Let's also check data/uat_runs/ folder
print("data/uat_runs contents:")
if os.path.exists("data/uat_runs"):
    print(os.listdir("data/uat_runs"))
else:
    print("directory data/uat_runs does not exist")

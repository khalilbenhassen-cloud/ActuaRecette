import os
import json

runs_dir = "data/uat_runs"
files = sorted(os.listdir(runs_dir))
if files:
    last_file = files[-1]
    print(f"Viewing last file: {last_file}")
    with open(os.path.join(runs_dir, last_file), "r", encoding="utf-8") as f:
        print(json.dumps(json.load(f), indent=2))
else:
    print("No run files found")

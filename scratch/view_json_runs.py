import os
import json

runs_dir = "data/uat_runs"
if os.path.exists(runs_dir):
    print("Files in", runs_dir)
    for f in os.listdir(runs_dir):
        if f.endswith(".json"):
            filepath = os.path.join(runs_dir, f)
            with open(filepath, "r", encoding="utf-8") as file:
                try:
                    data = json.load(file)
                    print(f"File: {f}")
                    print(f"  run_id: {data.get('run_id')}")
                    print(f"  run_name: {data.get('run_name')}")
                    print(f"  lob_id: {data.get('lob_id')}")
                    print(f"  maker_sso: {data.get('maker_sso')}")
                except Exception as e:
                    print(f"Error reading {f}: {e}")
else:
    print("Directory does not exist!")

import os
import json

runs_dir = "data/uat_runs"
if os.path.exists(runs_dir):
    print("Files in", runs_dir, ":")
    for f in os.listdir(runs_dir):
        path = os.path.join(runs_dir, f)
        print(" -", f, f"({os.path.getsize(path)} bytes)")
        if f.endswith(".json"):
            try:
                with open(path, "r", encoding="utf-8") as file:
                    data = json.load(file)
                print("   Run ID:", data.get("run_id"))
                print("   Run Name:", data.get("run_name"))
                print("   LOB ID:", data.get("lob_id"))
                print("   Status:", data.get("kpis", {}).get("final_status"))
            except Exception as e:
                print("   Error reading:", e)
else:
    print(runs_dir, "does not exist")

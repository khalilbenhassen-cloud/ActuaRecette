import os

for root, dirs, files in os.walk("dashboard"):
    for file in files:
        if file.endswith(".py"):
            path = os.path.join(root, file)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            if "load_run_history" in content or "run_history" in content:
                print("Found in:", path)
                lines = content.splitlines()
                for idx, line in enumerate(lines):
                    if "load_run_history" in line or "run_history" in line:
                        print(f"  Line {idx+1}: {line.strip()}")

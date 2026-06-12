import os

for root, dirs, files in os.walk("."):
    if any(p in root for p in [".git", ".pytest_cache", "__pycache__", "venv"]):
        continue
    for file in files:
        if file.endswith(".py"):
            path = os.path.join(root, file)
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            if "duckdb.connect" in content:
                lines = content.splitlines()
                for idx, line in enumerate(lines):
                    if "duckdb.connect" in line:
                        print(f"{path}:{idx+1}: {line.strip()}")

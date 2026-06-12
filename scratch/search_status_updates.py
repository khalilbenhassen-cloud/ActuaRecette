import os

for root, dirs, files in os.walk("."):
    # skip venv, .git, etc.
    if any(p in root for p in [".git", ".pytest_cache", "__pycache__", "venv"]):
        continue
    for file in files:
        if file.endswith(".py"):
            path = os.path.join(root, file)
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            if "statut_validation" in content or "validation_status" in content:
                if "UPDATE" in content or "=" in content:
                    lines = content.splitlines()
                    for idx, line in enumerate(lines):
                        if ("statut_validation" in line or "validation_status" in line) and ("UPDATE" in line or "=" in line or "insert" in line.lower()):
                            print(f"{path}:{idx+1}: {line.strip()}")

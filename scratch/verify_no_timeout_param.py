import os
import re

for root, dirs, files in os.walk("."):
    if any(p in root for p in [".git", ".pytest_cache", "__pycache__", "venv"]):
        continue
    for file in files:
        if file.endswith(".py"):
            path = os.path.join(root, file)
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            if re.search(r'sqlite_connection\s*\([^)]*timeout', content):
                print(f"ACTUAL CALL WITH TIMEOUT IN: {path}")
                # print the matching line
                lines = content.splitlines()
                for idx, line in enumerate(lines):
                    if re.search(r'sqlite_connection\s*\([^)]*timeout', line):
                        print(f"  Line {idx+1}: {line.strip()}")

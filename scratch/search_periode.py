import os

search_dir = "."
query = "periode_arrete"
for root, dirs, files in os.walk(search_dir):
    # skip venv, .git, etc.
    if any(p in root for p in [".git", ".pytest_cache", "__pycache__", "temp_uploads"]):
        continue
    for f in files:
        if f.endswith(".py") or f.endswith(".md"):
            path = os.path.join(root, f)
            try:
                with open(path, "r", encoding="utf-8") as file:
                    for idx, line in enumerate(file, 1):
                        if query in line:
                            print(f"{path}:{idx}: {line.strip()}")
            except Exception:
                pass

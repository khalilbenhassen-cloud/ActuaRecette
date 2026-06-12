import os

search_dir = "dashboard"
query = "revenir"
for root, dirs, files in os.walk(search_dir):
    for f in files:
        if f.endswith(".py"):
            path = os.path.join(root, f)
            with open(path, "r", encoding="utf-8") as file:
                for idx, line in enumerate(file, 1):
                    if query in line.lower():
                        print(f"{path}:{idx}: {line.strip()}")

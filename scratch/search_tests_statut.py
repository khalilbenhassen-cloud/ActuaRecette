import os

for root, dirs, files in os.walk("tests"):
    for file in files:
        if file.endswith(".py"):
            path = os.path.join(root, file)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            if "statut_validation" in content or "statut" in content:
                print("Found in:", path)
                lines = content.splitlines()
                for idx, line in enumerate(lines):
                    if "statut_validation" in line or "statut" in line:
                        print(f"  Line {idx+1}: {line.strip()}")

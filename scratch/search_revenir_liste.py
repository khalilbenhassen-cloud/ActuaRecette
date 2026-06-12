with open("dashboard/views/page_03_espace_travail.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if "revenir" in line.lower() or "retour" in line.lower():
        safe_line = line.strip().encode("ascii", "replace").decode("ascii")
        print(f"Line {idx+1}: {safe_line}")

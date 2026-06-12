with open("dashboard/views/page_01_cockpit.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if "runs_encours" in line or "runs_attente" in line or "runs_valides" in line:
        print(f"Line {idx+1}: {line.strip()}")

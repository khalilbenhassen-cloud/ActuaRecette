with open("dashboard/views/page_01_cockpit.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for idx, line in enumerate(lines, 1):
    if "_S_ENCOURS" in line or "_S_ATTENTE" in line or "_S_VALIDES" in line:
        print(f"page_01_cockpit.py:{idx}: {line.strip()}")

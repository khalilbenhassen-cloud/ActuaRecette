with open("dashboard/views/page_01_cockpit.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
for idx, line in enumerate(lines, 1):
    if "visible_lobs" in line or "filter_runs_by_lobs" in line or "history" in line:
        if "import" not in line:
            print(f"L{idx}: {line.strip()}")

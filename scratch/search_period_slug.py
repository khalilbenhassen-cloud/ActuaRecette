with open("dashboard/views/page_01_cockpit.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for idx, line in enumerate(lines, 1):
    if "_run_period_slug" in line:
        print(f"page_01_cockpit.py:{idx}: {line.strip()}")

with open("dashboard/views/page_01_cockpit.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if "get_active_periods" in line or "active_slugs" in line:
        print(f"Line {idx+1}: {line.strip()}")

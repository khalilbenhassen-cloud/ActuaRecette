with open("dashboard/views/page_03_espace_travail.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if "def _update_run_status" in line:
        print(f"Line {idx+1}: {line.strip()}")

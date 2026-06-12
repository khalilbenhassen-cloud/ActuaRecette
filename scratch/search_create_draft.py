with open("dashboard/views/page_03_espace_travail.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for idx, line in enumerate(lines):
    if "def _create_draft_campaign" in line or "_create_draft_campaign(" in line:
        print(f"Line {idx+1}: {line.strip()}")

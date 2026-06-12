import sys
import os
sys.path.append(os.path.abspath("."))

with open("dashboard/views/page_01_cockpit.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

for idx, line in enumerate(lines, 1):
    if "Aucune campagne" in line or "Bienvenue" in line:
        print(f"page_01_cockpit.py:{idx}: {line.strip()}")
        # Print surrounding lines
        for j in range(max(0, idx-10), min(len(lines), idx+10)):
            print(f"  {j+1}: {lines[j].strip()}")

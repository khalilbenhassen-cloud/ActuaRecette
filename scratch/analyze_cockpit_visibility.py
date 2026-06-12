import sys
import os
sys.path.append(os.path.abspath("."))

with open("dashboard/views/page_01_cockpit.py", "r", encoding="utf-8") as f:
    cockpit_src = f.read()

# Check how runs are displayed in Cockpit page
print("Does cockpit show draft runs or only certified ones?")
print("Is final_status or statut_validation filtered?")
for line in cockpit_src.split("\n"):
    if "final_status" in line or "statut_validation" in line or "Brouillon" in line:
        print(line.strip())

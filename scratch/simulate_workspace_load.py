import sys
import os

# Put current directory on path
sys.path.insert(0, os.path.abspath("."))

from dashboard.utils.auth import find_user_by_sso
from dashboard.views.page_03_espace_travail import _fetch_run_history, _get_campaign_status
from dashboard.utils.lob_filter import filter_runs_by_lobs

user = find_user_by_sso("karim.benali")
print("User visible LOBs:", user.visible_lobs)
print("User role:", user.role)

user_headers = {
    "X-User-SSO": user.sso,
    "X-User-Role": user.role,
    "X-User-LOBs": ",".join(user.visible_lobs),
}

history = _fetch_run_history(user_headers)
print("Fetched history length:", len(history))
for r in history:
    print("Run raw:", r)

filtered_history = filter_runs_by_lobs(history, user.visible_lobs)
print("Filtered history length:", len(filtered_history))
for r in filtered_history:
    status = _get_campaign_status(r.get("run_id"), user_headers)
    print("Run ID:", r.get("run_id"), "Name:", r.get("run_name"), "Status:", status)

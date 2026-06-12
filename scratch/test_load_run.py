import os
import json
import requests
from typing import Optional, Dict, Any

API_URL = "http://127.0.0.1:8000"

# Check if API is running
_api_ok = False
try:
    _res_health = requests.get(f"{API_URL}/health", timeout=1.0)
    if _res_health.status_code == 200:
        _api_ok = True
except Exception as e:
    print(f"API health check failed: {e}")

print(f"_api_ok state: {_api_ok}")

def _load_run_by_id(run_id: str, user_headers: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
    if _api_ok:
        try:
            url = f"{API_URL}/history/{run_id}"
            print(f"Calling API: {url} with headers {user_headers}")
            res = requests.get(url, headers=user_headers, timeout=1.5)
            print(f"API status code: {res.status_code}")
            if res.status_code == 200:
                return res.json()
        except Exception as e:
            print(f"API call failed: {e}")
            pass
    run_file = os.path.join("data", "uat_runs", f"{run_id}.json")
    print(f"Checking local file: {run_file}")
    if os.path.exists(run_file):
        with open(run_file, "r", encoding="utf-8") as f:
            run_data = json.load(f)
        if user_headers:
            visible_lobs = [lob.strip() for lob in user_headers.get("X-User-LOBs", "").split(",") if lob.strip()]
            print(f"Checking visibility with LOBs: {visible_lobs}")
            # simple mock of can_access_run
            lob_id = run_data.get("lob_id")
            if visible_lobs and lob_id not in visible_lobs:
                print(f"Access denied locally for LOB: {lob_id}")
                return None
        return run_data
    print("Local file does not exist")
    return None

# Test with one of our runs
run_id = "run_922dedd80ef5"
user_headers = {
    "X-User-SSO": "karim.benali",
    "X-User-Role": "Actuaire MOA",
    "X-User-LOBs": "LOB_AUTO_PART,LOB_INCENDIE_RD,LOB_MRH_HAB"
}

print("\n--- Testing WITH headers ---")
data_with = _load_run_by_id(run_id, user_headers)
print(f"Loaded: {data_with is not None}")

print("\n--- Testing WITHOUT headers ---")
data_without = _load_run_by_id(run_id)
print(f"Loaded: {data_without is not None}")

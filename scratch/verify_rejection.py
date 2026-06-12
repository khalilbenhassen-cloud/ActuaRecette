import os
import json
import shutil

def run_test():
    run_id = "test_rejection_dummy"
    run_file = os.path.join("data", "uat_runs", f"{run_id}.json")
    
    # 1. Create a dummy run file
    dummy_data = {
        "run_id": run_id,
        "run_name": "Test dummy run for rejection",
        "validation_status": "SOUMIS",
        "kpis": {
            "final_status": "SOUMIS"
        }
    }
    
    os.makedirs(os.path.dirname(run_file), exist_ok=True)
    with open(run_file, "w", encoding="utf-8") as f:
        json.dump(dummy_data, f, indent=2, ensure_ascii=False)
        
    print("[OK] Created dummy run JSON.")
    
    # 2. Emulate the _save_rejection_comment logic
    comment = "This is a rejection comment with more than 10 characters."
    
    try:
        with open(run_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["rejection_comment"] = comment
        data["rejection_reason"] = comment
        with open(run_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print("[OK] Executed rejection comment save.")
    except Exception as e:
        print(f"[FAIL] Error writing comment: {e}")
        
    # 3. Read back and verify
    with open(run_file, "r", encoding="utf-8") as f:
        saved_data = json.load(f)
        
    assert saved_data.get("rejection_comment") == comment, "rejection_comment mismatch"
    assert saved_data.get("rejection_reason") == comment, "rejection_reason mismatch"
    print("[OK] Verified comment matches exactly in JSON.")
    
    # 4. Clean up
    if os.path.exists(run_file):
        os.remove(run_file)
    print("[OK] Cleaned up dummy run JSON.")

if __name__ == "__main__":
    run_test()

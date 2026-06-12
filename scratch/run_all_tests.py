import os
import sys
import subprocess

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

ROOT = r"c:\Users\hp\Documents\ActuaRecette"
tests_dir = os.path.join(ROOT, "tests")

# Setup environment
env = os.environ.copy()
env["PYTHONPATH"] = ROOT + os.pathsep + env.get("PYTHONPATH", "")

test_files = [
    f for f in sorted(os.listdir(tests_dir))
    if f.startswith("test_") and f.endswith(".py")
]

passed_count = 0
failed_files = []

print(f"Discovered {len(test_files)} test files to run.\n")

for f in test_files:
    test_path = os.path.join(tests_dir, f)
    print(f"Running {f}...", flush=True)
    
    # Run the test file as a separate python process
    res = subprocess.run(
        [sys.executable, test_path],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    
    if res.returncode == 0:
        print(f"  --> PASSED\n")
        passed_count += 1
    else:
        print(f"  --> FAILED (exit code {res.returncode})")
        print("--- STDOUT ---")
        print(res.stdout)
        print("--- STDERR ---")
        print(res.stderr)
        print("--------------\n")
        failed_files.append(f)

print("========================================")
print(f"Tests execution summary:")
print(f"  Total run: {len(test_files)}")
print(f"  Passed: {passed_count}")
print(f"  Failed: {len(failed_files)}")
if failed_files:
    print(f"  Failed test suites: {failed_files}")
print("========================================")

sys.exit(0 if len(failed_files) == 0 else 1)

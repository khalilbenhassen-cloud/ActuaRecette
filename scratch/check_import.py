import sys
import subprocess

print("Current sys.path:")
for p in sys.path:
    print(" ", p)

print("\nTrying to import src from root:")
try:
    import src
    print("  Success!")
except ImportError as e:
    print("  Failed:", e)

print("\nRunning python from dashboard/ to simulate streamlit execution environment:")
res = subprocess.run(
    ["python", "-c", "import sys; print(sys.path); import src"],
    cwd="dashboard",
    capture_output=True,
    text=True
)
print("Stdout:", res.stdout)
print("Stderr:", res.stderr)

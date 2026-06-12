import os
import subprocess
import sys
import threading
import time

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

cwd = r"c:\Users\hp\Documents\ActuaRecette"

# Set up environment
env = os.environ.copy()
env["PYTHONPATH"] = cwd + os.pathsep + env.get("PYTHONPATH", "")
env["PYTHONUNBUFFERED"] = "1"

print("Starting FastAPI backend (unbuffered)...", flush=True)
api_proc = subprocess.Popen(
    [sys.executable, "-u", "api/main.py"],
    cwd=cwd,
    env=env,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    encoding="utf-8",
    errors="replace"
)

# Wait a couple of seconds for the backend to start up
time.sleep(2)

print("Starting Streamlit frontend (unbuffered)...", flush=True)
streamlit_proc = subprocess.Popen(
    [sys.executable, "-u", "-m", "streamlit", "run", "dashboard/app.py"],
    cwd=cwd,
    env=env,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    encoding="utf-8",
    errors="replace"
)

def stream_reader(pipe, prefix):
    for line in iter(pipe.readline, ''):
        print(f"[{prefix}] {line.strip()}", flush=True)

# Start background threads to read stdout without blocking
t1 = threading.Thread(target=stream_reader, args=(api_proc.stdout, "API"), daemon=True)
t2 = threading.Thread(target=stream_reader, args=(streamlit_proc.stdout, "Streamlit"), daemon=True)
t1.start()
t2.start()

print("Servers are running in background. Monitoring...", flush=True)

try:
    while True:
        # Check if either died
        if api_proc.poll() is not None:
            print(f"API backend exited with code {api_proc.poll()}", flush=True)
            break
        if streamlit_proc.poll() is not None:
            print(f"Streamlit frontend exited with code {streamlit_proc.poll()}", flush=True)
            break
            
        time.sleep(0.5)
except KeyboardInterrupt:
    print("Stopping servers...", flush=True)
finally:
    api_proc.terminate()
    streamlit_proc.terminate()

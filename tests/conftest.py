"""conftest.py -- T88: Configuration pytest globale pour ActuaRecette."""
import sys
import os

# Ensure project root is in PYTHONPATH
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Force UTF-8 (and patch reconfigure if missing, e.g. under pytest capture)
if not hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure = lambda *args, **kwargs: None
else:
    sys.stdout.reconfigure(encoding="utf-8")

if not hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure = lambda *args, **kwargs: None
else:
    sys.stderr.reconfigure(encoding="utf-8")

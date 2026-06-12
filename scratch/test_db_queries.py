import sqlite3
import os
import duckdb
from src.run_persistence import load_run_history

print("--- Testing load_run_history ---")
history = load_run_history("data/uat_runs")
print("History length:", len(history))
for h in history:
    print(h)

print("\n--- Direct Query on data/actuarecette.db using sqlite3 ---")
conn = sqlite3.connect("data/actuarecette.db")
conn.row_factory = sqlite3.Row
rows = conn.execute("SELECT * FROM runs_execution").fetchall()
print("Runs count:", len(rows))
for r in rows:
    print(dict(r))
conn.close()

print("\n--- Direct Query on data/actuarecette.db using duckdb ---")
try:
    conn = duckdb.connect("data/actuarecette.db", read_only=True)
    rows = conn.execute("SELECT r.id_run, r.statut_validation, c.id_portefeuille FROM runs_execution r JOIN campagnes_recette c ON r.id_campagne = c.id_campagne").fetchall()
    print("DuckDB query count:", len(rows))
    for r in rows:
        print(r)
    conn.close()
except Exception as e:
    print("DuckDB Error:", e)

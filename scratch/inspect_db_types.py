import sqlite3
import os

for db in ["data/actuarecette.db", "data/actuarecette_v2.db"]:
    if not os.path.exists(db):
        print(f"Database {db} does not exist.")
        continue
    try:
        conn = sqlite3.connect(db)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        print(f"Database {db} is SQLite. Tables: {tables}")
        conn.close()
    except Exception as e:
        print(f"Database {db} error under sqlite3: {e}")
        
    try:
        import duckdb
        conn = duckdb.connect(db, read_only=True)
        tables = conn.execute("SHOW TABLES").fetchall()
        print(f"Database {db} is DuckDB. Tables: {tables}")
        conn.close()
    except Exception as e:
        print(f"Database {db} error under DuckDB: {e}")

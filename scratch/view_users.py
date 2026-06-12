import sqlite3
import os

for db in ['data/actuarecette.db', 'data/actuarecette_v2.db']:
    print('='*40)
    print('DB:', db)
    print('='*40)
    if not os.path.exists(db):
        print('  File does not exist!')
        continue
    try:
        conn = sqlite3.connect(db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='utilisateurs'")
        if not cursor.fetchone():
            print("  Table 'utilisateurs' does not exist!")
            conn.close()
            continue
        
        cursor.execute("SELECT * FROM utilisateurs")
        rows = cursor.fetchall()
        for r in rows:
            print(dict(r))
        conn.close()
    except Exception as e:
        print('  Error:', e)

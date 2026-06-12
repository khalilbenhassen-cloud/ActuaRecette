import sqlite3
import os

for db_path in ["data/actuarecette.db", "data/actuarecette_v2.db"]:
    if os.path.exists(db_path):
        print(f"\nDB: {db_path}")
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("SELECT code_periode, libelle, statut FROM periodes_arrete")
            rows = cur.fetchall()
            print(f"Total periods: {len(rows)}")
            for r in rows:
                print(f" - {r}")
            conn.close()
        except Exception as e:
            print(f"Error: {e}")

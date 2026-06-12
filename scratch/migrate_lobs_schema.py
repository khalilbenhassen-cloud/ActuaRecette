import sqlite3
import os

dbs = ["data/actuarecette.db", "data/actuarecette_v2.db"]
for db in dbs:
    if os.path.exists(db):
        conn = sqlite3.connect(db)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(portefeuilles)")
        existing_cols = [row[1] for row in cursor.fetchall()]
        
        if "date_creation" not in existing_cols:
            try:
                cursor.execute("ALTER TABLE portefeuilles ADD COLUMN date_creation TIMESTAMP")
                print(f"Added column date_creation to {db}")
            except Exception as e:
                print(f"Error adding date_creation to {db}: {e}")
        conn.commit()
        conn.close()
print("Migration of date_creation completed.")

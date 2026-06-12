import sqlite3

for db in ["data/actuarecette.db", "data/actuarecette_v2.db"]:
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM portefeuilles WHERE id_portefeuille='TEST_LOB'").fetchone()
    if row:
        print(db, "TEST_LOB details:")
        for k in row.keys():
            print(f"  {k}: {row[k]}")
    else:
        print(db, "TEST_LOB not found")
    conn.close()

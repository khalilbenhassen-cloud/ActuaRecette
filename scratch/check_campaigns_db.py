import sqlite3

for db in ['data/actuarecette.db', 'data/actuarecette_v2.db']:
    print('DB:', db)
    try:
        conn = sqlite3.connect(db)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cur.fetchall()]
        print("Tables:", tables)
        
        if 'campagnes_recette' in tables:
            cur.execute("SELECT * FROM campagnes_recette LIMIT 5")
            print("  Campagnes:")
            for r in cur.fetchall():
                print("   ", dict(r))
                
        if 'portefeuilles' in tables:
            cur.execute("SELECT * FROM portefeuilles LIMIT 5")
            print("  Portefeuilles:")
            for r in cur.fetchall():
                print("   ", dict(r))
                
        conn.close()
    except Exception as e:
        print('  Error:', e)

"""Test Notifications: Verify creation, filtering, and marking notifications as read in SQLite databases."""
import sys
sys.stdout.reconfigure(encoding="utf-8")
import os
import sqlite3
import datetime

ROOT = "c:/Users/hp/Documents/ActuaRecette"
sys.path.insert(0, ROOT)

from src.notification_manager import (
    create_notification,
    get_unread_notifications,
    mark_as_read,
    mark_all_as_read
)

passed = 0
failed = 0

def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  [OK] {name}")
    else:
        failed += 1
        print(f"  [FAIL] {name} -- {detail}")

print("=== Test Notifications Lifecycle ===")

dbs = ["data/actuarecette.db", "data/actuarecette_v2.db"]

# Ensure directories exist and schema is applied
for db in dbs:
    if os.path.exists(db):
        conn = sqlite3.connect(db)
        # Apply table creation manually just in case schema migration hasn't run yet
        conn.execute(
            """CREATE TABLE IF NOT EXISTS notifications (
                id VARCHAR PRIMARY KEY,
                destinataire_sso VARCHAR,
                destinataire_role VARCHAR,
                id_portefeuille VARCHAR,
                titre VARCHAR NOT NULL,
                message TEXT NOT NULL,
                type VARCHAR DEFAULT 'INFO',
                is_read BOOLEAN DEFAULT FALSE,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        conn.execute("DELETE FROM notifications WHERE id LIKE 'NOTIF-TEST-%' OR titre LIKE 'TEST_NOTIF_%'")
        conn.commit()
        conn.close()

# Test 1: Create notifications and check SQLite insertion
notif_id_1 = create_notification(
    id_portefeuille="LOB_AUTO_PART",
    destinataire_role="Validateur",
    destinataire_sso=None,
    titre="TEST_NOTIF_1",
    message="Notification for Auto Validateur",
    type="INFO"
)

notif_id_2 = create_notification(
    id_portefeuille="LOB_INCENDIE_RD",
    destinataire_role=None,
    destinataire_sso="maker.senior",
    titre="TEST_NOTIF_2",
    message="Notification for Maker Senior",
    type="SUCCESS"
)

# Verify they exist in both databases
for db in dbs:
    if os.path.exists(db):
        conn = sqlite3.connect(db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM notifications WHERE id IN (?, ?)", (notif_id_1, notif_id_2))
        count = cursor.fetchone()[0]
        check(f"Notifications inserted in {os.path.basename(db)}", count == 2)
        conn.close()

# Test 2: Filter notifications (get_unread_notifications)
# A: User role is 'Validateur' with LOB_AUTO_PART access
notifs_val = get_unread_notifications(
    user_role="Validateur",
    user_sso="checker",
    visible_lobs=["LOB_AUTO_PART"]
)
check("Validateur gets TEST_NOTIF_1", len(notifs_val) == 1 and notifs_val[0]["id"] == notif_id_1)

# B: User role is 'Validateur' but has no access to LOB_AUTO_PART
notifs_val_no_lob = get_unread_notifications(
    user_role="Validateur",
    user_sso="checker",
    visible_lobs=["LOB_INCENDIE_RD"]
)
check("Validateur with different LOB gets nothing", len(notifs_val_no_lob) == 0)

# C: User SSO is 'maker.senior'
notifs_maker_senior = get_unread_notifications(
    user_role="Actuaire MOA",
    user_sso="maker.senior",
    visible_lobs=["LOB_INCENDIE_RD"]
)
check("maker.senior gets TEST_NOTIF_2", len(notifs_maker_senior) == 1 and notifs_maker_senior[0]["id"] == notif_id_2)

# Test 3: Mark as read
success_mark = mark_as_read(notif_id_1)
check("mark_as_read returns success", success_mark is True)

# Verify it is no longer retrieved as unread
notifs_val_post = get_unread_notifications(
    user_role="Validateur",
    user_sso="checker",
    visible_lobs=["LOB_AUTO_PART"]
)
check("TEST_NOTIF_1 no longer retrieved after being marked read", len(notifs_val_post) == 0)

# Test 4: Mark all as read
count_marked = mark_all_as_read(
    user_role="Actuaire MOA",
    user_sso="maker.senior"
)
check("mark_all_as_read returns 1 updated row", count_marked == 1)

# Verify TEST_NOTIF_2 is no longer unread
notifs_maker_senior_post = get_unread_notifications(
    user_role="Actuaire MOA",
    user_sso="maker.senior",
    visible_lobs=["LOB_INCENDIE_RD"]
)
check("TEST_NOTIF_2 marked read via mark_all_as_read", len(notifs_maker_senior_post) == 0)

# Final Cleanup
for db in dbs:
    if os.path.exists(db):
        conn = sqlite3.connect(db)
        conn.execute("DELETE FROM notifications WHERE id IN (?, ?)", (notif_id_1, notif_id_2))
        conn.commit()
        conn.close()

print("==================================================")
print(f"  Total: {passed + failed} | Pass: {passed} | Fail: {failed}")
print("==================================================")
sys.exit(0 if failed == 0 else 1)

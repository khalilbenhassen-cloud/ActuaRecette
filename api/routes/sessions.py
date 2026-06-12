"""
api/routes/sessions.py — Session heartbeat & user presence
===========================================================

Endpoints:
  POST /sessions/heartbeat
  GET  /sessions/active
  GET  /team-activity
"""

import os
import time as _time
from typing import Dict, Any

from fastapi import APIRouter, Request, HTTPException

from src.anomaly_manager import load_global_audit_trail

router = APIRouter(tags=["Sessions"])

# In-memory session registry: {sso: {name, role, last_seen, current_page, lobs}}
_active_sessions: Dict[str, Dict[str, Any]] = {}
_SESSION_TIMEOUT = 90  # seconds before a session is considered expired

def _clean_expired_sessions():
    """Remove sessions older than _SESSION_TIMEOUT from database and memory."""
    now = _time.time()
    expired = [k for k, v in _active_sessions.items() if now - v.get("last_seen", 0) > _SESSION_TIMEOUT]
    for k in expired:
        del _active_sessions[k]

    from src.db_adapter import sqlite_connection
    DBS = ["data/actuarecette.db", "data/actuarecette_v2.db"]
    for db_path in DBS:
        if not os.path.exists(db_path):
            continue
        try:
            with sqlite_connection(db_path) as conn:
                conn.execute(
                    "DELETE FROM active_sessions WHERE last_heartbeat < datetime('now', '-' || ? || ' seconds')",
                    (_SESSION_TIMEOUT,)
                )
        except Exception as e:
            import logging
            logging.getLogger("actuarecette.sessions").warning(f"Error cleaning expired sessions in {db_path}: {e}")

@router.post("/sessions/heartbeat")
def session_heartbeat(request: Request):
    """
    T21 -- Heartbeat de presence utilisateur.
    Le dashboard appelle ce endpoint toutes les 30 secondes.
    """
    _clean_expired_sessions()

    sso = getattr(request.state, "user_sso", None) or request.headers.get("X-User-SSO", "")
    if not sso:
        raise HTTPException(status_code=400, detail="Header X-User-SSO requis.")

    name = getattr(request.state, "user_name", None) or request.headers.get("X-User-Name", sso)
    role = getattr(request.state, "user_role", None) or request.headers.get("X-User-Role", "")
    lobs = getattr(request.state, "user_lobs", None)
    if lobs is None:
        lobs_header = request.headers.get("X-User-LOBs", "")
        lobs = [l.strip() for l in lobs_header.split(",") if l.strip()]
    lobs_str = ",".join(lobs)
    current_page = request.headers.get("X-Current-Page", "")

    # Update memory
    _active_sessions[sso] = {
        "name": name,
        "role": role,
        "lobs": lobs_str,
        "current_page": current_page,
        "last_seen": _time.time(),
    }

    # Update database
    from src.db_adapter import sqlite_connection
    DBS = ["data/actuarecette.db", "data/actuarecette_v2.db"]
    for db_path in DBS:
        if not os.path.exists(db_path):
            continue
        try:
            with sqlite_connection(db_path) as conn:
                conn.execute(
                    """INSERT OR REPLACE INTO active_sessions 
                    (session_id, user_sso, user_name, user_role, current_lob, current_page, last_heartbeat)
                    VALUES (?, ?, ?, ?, ?, ?, datetime('now'))""",
                    (sso, sso, name, role, lobs_str, current_page)
                )
        except Exception as e:
            import logging
            logging.getLogger("actuarecette.sessions").warning(f"Error updating heartbeat in {db_path}: {e}")

    return {
        "status": "ok",
        "active_users": len(_active_sessions),
    }

@router.get("/sessions/active")
def get_active_sessions():
    """
    T57 -- Liste des utilisateurs actifs (pour le composant user_presence).
    """
    _clean_expired_sessions()

    from src.db_adapter import sqlite_connection
    db_path = "data/actuarecette.db"
    users = []

    if os.path.exists(db_path):
        try:
            with sqlite_connection(db_path) as conn:
                rows = conn.execute(
                    """SELECT user_sso, user_name, user_role, current_page, 
                    (strftime('%s', 'now') - strftime('%s', last_heartbeat)) AS idle_seconds 
                    FROM active_sessions"""
                ).fetchall()
                for row in rows:
                    users.append({
                        "sso": row["user_sso"],
                        "name": row["user_name"],
                        "role": row["user_role"],
                        "current_page": row["current_page"] or "",
                        "idle_seconds": max(0, int(row["idle_seconds"] or 0)),
                    })
        except Exception as e:
            import logging
            logging.getLogger("actuarecette.sessions").warning(f"Error reading active sessions from DB: {e}")

    if not users:
        # Fallback to in-memory dictionary
        for sso, info in _active_sessions.items():
            users.append({
                "sso": sso,
                "name": info.get("name", sso),
                "role": info.get("role", ""),
                "current_page": info.get("current_page", ""),
                "idle_seconds": int(_time.time() - info.get("last_seen", _time.time())),
            })

    return {"active_users": users, "count": len(users)}

@router.get("/team-activity")
def get_team_activity(request: Request):
    """
    T56 -- Vue Manager : activite recente de l'equipe.
    Combine audit trail + sessions actives.
    """
    role = request.headers.get("X-User-Role", "")
    if role not in ("Responsable MOA", "Validateur"):
        raise HTTPException(status_code=403, detail="Acces reserve aux Managers et Validateurs.")

    _clean_expired_sessions()
    
    active_data = get_active_sessions()
    active = active_data["active_users"]

    audit = load_global_audit_trail("data/audit_log.json")
    recent_audit = audit[:20] if audit else []

    return {
        "active_sessions": active,
        "active_count": len(active),
        "recent_activity": recent_audit,
    }

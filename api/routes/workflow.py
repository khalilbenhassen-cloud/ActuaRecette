"""
api/routes/workflow.py — Maker-Checker workflow
================================================

Endpoints:
  POST /runs/{run_id}/submit
  POST /runs/{run_id}/certify
  POST /runs/{run_id}/reject
  GET  /pending-validations
"""

import os
import json
import datetime
from typing import List

from fastapi import APIRouter, Request, HTTPException

from api.api_auth_middleware import get_current_user, get_visible_lobs
from api.schemas import (
    SubmitRunRequest,
    CertifyRunRequest,
    RejectRunRequest,
    PendingValidationItem,
)
from src.anomaly_manager import add_global_audit_entry

HISTORY_DIR = "data/uat_runs"

router = APIRouter(tags=["Workflow"])

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_run_json(run_id: str) -> dict:
    """Helper: load a run JSON file or raise 404."""
    from api.api_auth_middleware import validate_safe_id
    safe_id = validate_safe_id(run_id, "run_id")
    run_file = os.path.join(HISTORY_DIR, f"{safe_id}.json")
    if not os.path.exists(run_file):
        raise HTTPException(status_code=404, detail=f"Run introuvable : {safe_id}")
    with open(run_file, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_run_json(run_id: str, data: dict) -> None:
    """Helper: save a run JSON file."""
    run_file = os.path.join(HISTORY_DIR, f"{run_id}.json")
    with open(run_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def _audit_and_transition(run_data: dict, run_id: str, action: str,
                          user_sso: str, user_name: str, user_role: str,
                          new_status: str, comment: str = "") -> dict:
    """Apply status transition, append audit trail, persist."""
    run_data["validation_status"] = new_status
    if "audit_trail" not in run_data:
        run_data["audit_trail"] = []
    entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "action": action,
        "user_sso": user_sso,
        "user_name": user_name,
        "role": user_role,
        "comment": comment,
        "from_status": run_data.get("_prev_status", ""),
        "to_status": new_status,
    }
    run_data["audit_trail"].append(entry)
    run_data.pop("_prev_status", None)

    # Global audit
    add_global_audit_entry(
        run_id=run_id,
        run_name=run_data.get("run_name", "?"),
        role=user_role,
        action=action,
        comment=comment,
        validator_name=user_name,
    )
    _save_run_json(run_id, run_data)
    return entry

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/runs/{run_id}/submit", tags=["Workflow"])
def submit_run(run_id: str, payload: SubmitRunRequest, request: Request):
    """
    Transition CALCULÉ → SOUMIS.
    Only the maker (creator) can submit their own run.
    """
    user = get_current_user(request)
    run_data = _load_run_json(run_id)

    # LOB access check
    visible_lobs = get_visible_lobs(request)
    run_lob = run_data.get("lob_id", "LOB_AUTO_PART")
    if run_lob not in visible_lobs:
        raise HTTPException(
            status_code=403,
            detail=f"Accès refusé : vous n'êtes pas autorisé sur le portefeuille {run_lob}."
        )

    current_status = run_data.get("validation_status", "BROUILLON")
    if current_status not in ("BROUILLON", "CALCULE", "REJETE", "REJECTED"):
        raise HTTPException(
            status_code=409,
            detail=f"Transition impossible : statut actuel '{current_status}'. "
                   f"Seuls les runs BROUILLON, CALCULÉ ou REJETÉ/REJECTED peuvent être soumis."
        )

    # Only maker (creator) can submit
    creator = run_data.get("created_by_sso") or run_data.get("maker_sso") or run_data.get("metadata", {}).get("created_by", "")
    if creator and creator != user.get("sso", ""):
        raise HTTPException(
            status_code=403,
            detail="Seul le créateur du run peut le soumettre."
        )

    run_data["_prev_status"] = current_status
    run_data["submitted_by"] = user.get("sso", "unknown")
    run_data["submitted_at"] = datetime.datetime.now().isoformat()

    entry = _audit_and_transition(
        run_data, run_id,
        action="SUBMITTED",
        user_sso=user.get("sso", ""),
        user_name=user.get("name", ""),
        user_role=user.get("role", ""),
        new_status="SOUMIS",
        comment=payload.comment or "Run soumis pour validation.",
    )
    
    # Notifications (v6.0)
    try:
        from src.notification_manager import create_notification
        run_name = run_data.get("run_name", f"Run {run_id}")
        create_notification(
            id_portefeuille=run_lob,
            destinataire_role="Validateur",
            destinataire_sso=None,
            titre="Campagne soumise pour validation",
            message=f"Le run '{run_name}' (ID: {run_id}) a été soumis par {user.get('name', '?')} et est en attente de certification.",
            type="INFO"
        )
    except Exception as notif_err:
        import logging
        logging.getLogger("actuarecette").warning(f"Notification creation failed: {notif_err}")
        
    return {"status": "SUCCESS", "new_status": "SOUMIS", "audit": entry}

@router.post("/runs/{run_id}/certify", tags=["Workflow"])
def certify_run(run_id: str, payload: CertifyRunRequest, request: Request):
    """
    Transition SOUMIS → CERTIFIÉ (ou CERTIFIÉ_RESERVES).
    Enforces Checker ≠ Maker rule.
    """
    user = get_current_user(request)
    run_data = _load_run_json(run_id)

    # LOB access check
    visible_lobs = get_visible_lobs(request)
    run_lob = run_data.get("lob_id", "LOB_AUTO_PART")
    if run_lob not in visible_lobs:
        raise HTTPException(
            status_code=403,
            detail=f"Accès refusé : vous n'êtes pas autorisé sur le portefeuille {run_lob}."
        )

    current_status = run_data.get("validation_status", "BROUILLON")
    if current_status not in ("SOUMIS", "SUBMITTED_FOR_VALIDATION"):
        raise HTTPException(
            status_code=409,
            detail=f"Seuls les runs SOUMIS ou SUBMITTED_FOR_VALIDATION peuvent être certifiés. Statut actuel : '{current_status}'."
        )

    # Role check: only Validateur or Responsable MOA can certify
    user_role = user.get("role", "")
    if user_role not in ("Validateur", "Responsable MOA"):
        raise HTTPException(
            status_code=403,
            detail=f"Le rôle '{user_role}' n'a pas la permission de certifier un run."
        )

    # Maker ≠ Checker enforcement
    submitted_by = run_data.get("submitted_by") or run_data.get("created_by_sso") or run_data.get("maker_sso") or run_data.get("metadata", {}).get("created_by", "")
    if submitted_by == user.get("sso", ""):
        raise HTTPException(
            status_code=403,
            detail="Maker ≠ Checker : vous ne pouvez pas certifier votre propre run."
        )

    # T67 — Seuil ACPR bloquant : interdire la certification si prime à risque > seuil × provisions
    try:
        from src.tolerance_manager import get_lob_tolerance
        kpis = run_data.get("kpis", {})
        prime_a_risque = kpis.get("total_absolute_delta_euros", 0.0)
        total_premium = kpis.get("total_cases", 0) * 250.0  # proxy provisions
        if total_premium <= 0:
            total_premium = 1.0  # avoid division by zero

        lob_id = run_data.get("metadata", {}).get("lob_id", "LOB_AUTO_PART")
        lob_tol = get_lob_tolerance(lob_id)
        seuil_pct = lob_tol.get("seuil_materialite_pct", 0.20) / 100.0
        seuil_abs = total_premium * seuil_pct

        if prime_a_risque > seuil_abs and seuil_abs > 0:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"BLOCAGE REGLEMENTAIRE ACPR : la prime a risque ({prime_a_risque:,.2f} EUR) "
                    f"depasse le seuil de materialite du portefeuille {lob_id} "
                    f"({seuil_pct*100:.2f}% x {total_premium:,.2f} EUR = {seuil_abs:,.2f} EUR). "
                    f"La certification est interdite. Corrigez les anomalies ou augmentez le seuil."
                ),
            )
    except HTTPException:
        raise
    except Exception as e:
        # Non-bloquant en cas d'erreur DB — log et continue
        import logging
        logging.getLogger("actuarecette").warning(f"ACPR check skipped: {e}")

    new_status = "CERTIFIE_RESERVES" if payload.with_reserves else "CERTIFIE"
    run_data["_prev_status"] = current_status
    run_data["certified_by"] = user.get("sso", "")
    run_data["certified_at"] = datetime.datetime.now().isoformat()

    entry = _audit_and_transition(
        run_data, run_id,
        action="CERTIFIED" if not payload.with_reserves else "CERTIFIED_WITH_RESERVES",
        user_sso=user.get("sso", ""),
        user_name=user.get("name", ""),
        user_role=user_role,
        new_status=new_status,
        comment=payload.comment or f"Run certifié par {user.get('name', '?')}.",
    )

    # Notifications (v6.0)
    try:
        from src.notification_manager import create_notification
        run_name = run_data.get("run_name", f"Run {run_id}")
        creator = run_data.get("created_by_sso") or run_data.get("maker_sso") or run_data.get("metadata", {}).get("created_by", "")
        if creator:
            create_notification(
                id_portefeuille=run_lob,
                destinataire_role=None,
                destinataire_sso=creator,
                titre="Campagne certifiée",
                message=f"Votre run '{run_name}' (ID: {run_id}) a été certifié par {user.get('name', '?')}.",
                type="SUCCESS"
            )
        create_notification(
            id_portefeuille=run_lob,
            destinataire_role="Responsable MOA",
            destinataire_sso=None,
            titre="Campagne certifiée",
            message=f"Le run '{run_name}' (ID: {run_id}) a été certifié par {user.get('name', '?')}.",
            type="SUCCESS"
        )
    except Exception as notif_err:
        import logging
        logging.getLogger("actuarecette").warning(f"Notification creation failed: {notif_err}")

    # T76 -- Hook snapshot automatique a la certification
    try:
        from src.trend_analyzer import save_trend_snapshot
        kpis = run_data.get("kpis", {})
        anomalies = run_data.get("anomalies", [])
        lob_id = run_data.get("metadata", {}).get("lob_id", "LOB_AUTO_PART")
        ts = run_data.get("timestamp", datetime.datetime.now().isoformat())
        periode = ts[:7] if len(ts) >= 7 else datetime.datetime.now().strftime("%Y-%m")
        save_trend_snapshot(
            run_id=run_id,
            lob_id=lob_id,
            periode=periode,
            kpis=kpis,
            anomalies=anomalies,
            version_moteur=run_data.get("metadata", {}).get("engine_version", "ActuaRecette-v6.0"),
        )
    except Exception as snap_err:
        import logging
        logging.getLogger("actuarecette").warning(f"Trend snapshot skipped: {snap_err}")

    return {"status": "SUCCESS", "new_status": new_status, "audit": entry}

@router.post("/runs/{run_id}/reject", tags=["Workflow"])
def reject_run(run_id: str, payload: RejectRunRequest, request: Request):
    """
    Transition SOUMIS → BROUILLON.
    Mandatory rejection reason. Checker ≠ Maker enforced.
    """
    user = get_current_user(request)
    run_data = _load_run_json(run_id)

    # LOB access check
    visible_lobs = get_visible_lobs(request)
    run_lob = run_data.get("lob_id", "LOB_AUTO_PART")
    if run_lob not in visible_lobs:
        raise HTTPException(
            status_code=403,
            detail=f"Accès refusé : vous n'êtes pas autorisé sur le portefeuille {run_lob}."
        )

    current_status = run_data.get("validation_status", "BROUILLON")
    if current_status not in ("SOUMIS", "SUBMITTED_FOR_VALIDATION"):
        raise HTTPException(
            status_code=409,
            detail=f"Seuls les runs SOUMIS ou SUBMITTED_FOR_VALIDATION peuvent être rejetés. Statut actuel : '{current_status}'."
        )

    user_role = user.get("role", "")
    if user_role not in ("Validateur", "Responsable MOA"):
        raise HTTPException(
            status_code=403,
            detail=f"Le rôle '{user_role}' n'a pas la permission de rejeter un run."
        )

    # Maker ≠ Checker enforcement
    submitted_by = run_data.get("submitted_by", run_data.get("created_by_sso", ""))
    if submitted_by == user.get("sso", ""):
        raise HTTPException(
            status_code=403,
            detail="Maker ≠ Checker : vous ne pouvez pas rejeter votre propre run."
        )

    run_data["_prev_status"] = current_status
    run_data["rejected_by"] = user.get("sso", "")
    run_data["rejected_at"] = datetime.datetime.now().isoformat()
    run_data["rejection_reason"] = payload.reason

    entry = _audit_and_transition(
        run_data, run_id,
        action="REJECTED",
        user_sso=user.get("sso", ""),
        user_name=user.get("name", ""),
        user_role=user_role,
        new_status="BROUILLON",
        comment=payload.reason,
    )
    
    # Notifications (v6.0)
    try:
        from src.notification_manager import create_notification
        run_name = run_data.get("run_name", f"Run {run_id}")
        creator = run_data.get("created_by_sso") or run_data.get("maker_sso") or run_data.get("metadata", {}).get("created_by", "")
        if creator:
            create_notification(
                id_portefeuille=run_lob,
                destinataire_role=None,
                destinataire_sso=creator,
                titre="Campagne rejetée",
                message=f"Votre run '{run_name}' (ID: {run_id}) a été rejeté par {user.get('name', '?')}. Motif : {payload.reason}",
                type="ALERT"
            )
    except Exception as notif_err:
        import logging
        logging.getLogger("actuarecette").warning(f"Notification creation failed: {notif_err}")
        
    return {"status": "SUCCESS", "new_status": "BROUILLON", "audit": entry}

@router.get("/pending-validations", tags=["Workflow"], response_model=List[PendingValidationItem])
def get_pending_validations(request: Request):
    """
    Returns all runs with status SOUMIS that the current user can certify.
    Filters: checker ≠ maker, and LOB visibility.
    """
    try:
        from api.routes.sessions import _clean_expired_sessions
        _clean_expired_sessions()
    except Exception as e:
        import logging
        logging.getLogger("actuarecette").warning(f"Failed to clean expired sessions: {e}")

    user = get_current_user(request)
    user_role = user.get("role", "")

    # Only Validateur and Responsable MOA see the queue
    if user_role not in ("Validateur", "Responsable MOA"):
        return []

    visible_lobs = get_visible_lobs(request)
    pending = []

    if not os.path.isdir(HISTORY_DIR):
        return []

    for filename in os.listdir(HISTORY_DIR):
        if not filename.endswith(".json"):
            continue
        filepath = os.path.join(HISTORY_DIR, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                run = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        if run.get("validation_status") not in ("SOUMIS", "SUBMITTED_FOR_VALIDATION"):
            continue

        # Maker ≠ Checker: skip runs submitted by current user
        submitted_by = run.get("submitted_by") or run.get("created_by_sso") or run.get("maker_sso") or run.get("metadata", {}).get("created_by", "")
        if submitted_by == user.get("sso", ""):
            continue

        # LOB filtering
        run_lob = run.get("lob_id", "LOB_AUTO_PART")
        if run_lob not in visible_lobs:
            continue

        kpis = run.get("kpis", {})
        pending.append(PendingValidationItem(
            run_id=filename.replace(".json", ""),
            run_name=run.get("run_name", "Sans nom"),
            submitted_by=submitted_by,
            submitted_at=run.get("submitted_at", ""),
            lob_id=run_lob,
            success_rate_pct=kpis.get("success_rate_pct", 0.0),
            fatal_defects=kpis.get("fatal_defects", 0),
            total_delta_euros=kpis.get("total_absolute_delta_euros", 0.0),
        ))

    # Sort by submission date (newest first)
    pending.sort(key=lambda x: x.submitted_at, reverse=True)
    return pending

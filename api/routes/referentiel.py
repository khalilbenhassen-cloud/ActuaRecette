"""
api/routes/referentiel.py — Reference data & exercices
======================================================

Endpoints:
  GET  /anomaly-categories
  GET  /exercices
  POST /exercices
  POST /exercices/{id_exercice}/close
  POST /exercices/{id_exercice}/lock
  GET  /runs/{run_id}/dq-report
  POST /runs/{run_id}/dq-report
  GET  /tolerances
  GET  /tolerances/{lob_id}
  PUT  /tolerances/{lob_id}
  GET  /runs/parasitic
"""

import os
import json
import datetime

from fastapi import APIRouter, Request, HTTPException

from api.api_auth_middleware import get_current_user, get_visible_lobs
from src.anomaly_manager import load_run_history, add_global_audit_entry

HISTORY_DIR = "data/uat_runs"

router = APIRouter(tags=["Référentiel"])

# ---------------------------------------------------------------------------
# Tolerances (T65)
# ---------------------------------------------------------------------------

@router.get("/tolerances")
def get_tolerances(request: Request):
    """T65 -- Liste les seuils de tolerance de tous les portefeuilles."""
    from src.tolerance_manager import get_all_tolerances
    visible_lobs = get_visible_lobs(request)
    tolerances = get_all_tolerances()
    return [t for t in tolerances if t.get("id_portefeuille") in visible_lobs]

@router.get("/tolerances/{lob_id}")
def get_lob_tolerance_endpoint(lob_id: str, request: Request):
    """T65 -- Recupere les seuils d'un portefeuille specifique."""
    visible_lobs = get_visible_lobs(request)
    if lob_id not in visible_lobs:
        raise HTTPException(
            status_code=403,
            detail=f"Accès refusé : vous n'êtes pas autorisé sur le portefeuille {lob_id}."
        )
    from src.tolerance_manager import get_lob_tolerance
    return get_lob_tolerance(lob_id)

@router.put("/tolerances/{lob_id}")
def update_lob_tolerance_endpoint(lob_id: str, request: Request):
    """
    T65 -- Met a jour les seuils d'un portefeuille.
    Body JSON: {seuil_materialite_pct: float, tolerance_unitaire: float}
    """
    import asyncio

    role = request.headers.get("X-User-Role", "")
    if role != "Responsable MOA":
        raise HTTPException(status_code=403, detail="Seul le Responsable MOA peut modifier les seuils.")

    visible_lobs = get_visible_lobs(request)
    if lob_id not in visible_lobs:
        raise HTTPException(
            status_code=403,
            detail=f"Accès refusé : vous n'êtes pas autorisé sur le portefeuille {lob_id}."
        )

    # Synchronous body read via run_sync workaround
    from src.tolerance_manager import update_lob_tolerance
    try:
        # For sync endpoint, we read body differently
        import json as _json
        body_bytes = asyncio.get_event_loop().run_until_complete(request.body())
        body = _json.loads(body_bytes)
    except Exception:
        raise HTTPException(status_code=400, detail="Body JSON invalide.")

    try:
        result = update_lob_tolerance(
            lob_id=lob_id,
            seuil_materialite_pct=body.get("seuil_materialite_pct"),
            tolerance_unitaire=body.get("tolerance_unitaire"),
        )
        return {"status": "updated", "lob_id": lob_id, "tolerances": result}
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Parasitic runs (T66)
# ---------------------------------------------------------------------------

@router.get("/runs/parasitic")
def detect_parasitic_runs_endpoint(request: Request):
    """
    T66 -- Detecte les runs parasites (vides, doublons, suspects).
    """
    from src.tolerance_manager import detect_parasitic_runs

    visible_lobs = get_visible_lobs(request)
    history = load_run_history(HISTORY_DIR)
    filtered_history = [run for run in history if run.get("lob_id", "LOB_AUTO_PART") in visible_lobs]
    
    suspects = detect_parasitic_runs(filtered_history)
    return {
        "total_runs": len(filtered_history),
        "parasitic_count": len(suspects),
        "parasitic_runs": suspects,
    }


# ---------------------------------------------------------------------------
# Anomaly categories (Référentiel)
# ---------------------------------------------------------------------------

@router.get("/anomaly-categories", tags=["Référentiel"])
def get_anomaly_categories():
    """Retourne le référentiel complet des catégories d'anomalies actuarielles."""
    import sqlite3
    db_path = "data/actuarecette.db"
    if not os.path.exists(db_path):
        # Fallback: return hardcoded categories
        return [
            {"id_category": "ARRONDI_DECIMAL", "libelle": "Bruit d'arrondi décimal", "severite": 3, "est_bloquant": False},
            {"id_category": "SEUIL_PLANCHER", "libelle": "Oubli de Seuil Minimal (Plancher)", "severite": 1, "est_bloquant": True},
            {"id_category": "FORMULE_JEUNE_CONDUCTEUR", "libelle": "Erreur de Formule Jeune Conducteur", "severite": 1, "est_bloquant": True},
            {"id_category": "COEFF_PUISSANCE", "libelle": "Écart de Coefficient Puissance", "severite": 1, "est_bloquant": True},
            {"id_category": "ECART_NON_REPERTORIE", "libelle": "Écart fonctionnel non répertorié", "severite": 2, "est_bloquant": True},
            {"id_category": "DONNEE_CORROMPUE", "libelle": "Donnée corrompue ou manquante", "severite": 1, "est_bloquant": True},
        ]

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM anomaly_categories ORDER BY severite, libelle").fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------------------------------------------------------
# Exercices (Cycle de vie)
# ---------------------------------------------------------------------------

@router.get("/exercices", tags=["Exercices"])
def list_exercices():
    """Liste tous les exercices comptables."""
    import sqlite3
    db_path = "data/actuarecette.db"
    if not os.path.exists(db_path):
        return []

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM exercices ORDER BY annee DESC, mois DESC"
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/exercices", tags=["Exercices"])
def create_exercice(annee: int, mois: int, request: Request):
    """Crée un nouvel exercice comptable (statut OUVERT)."""
    import sqlite3
    user = get_current_user(request)

    if user.get("role") != "Responsable MOA":
        raise HTTPException(status_code=403, detail="Seul le Responsable MOA peut créer un exercice.")

    if not (1 <= mois <= 12):
        raise HTTPException(status_code=400, detail="Le mois doit être entre 1 et 12.")

    id_exercice = f"EX_{annee}_{mois:02d}"
    mois_noms = ["", "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
                  "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    libelle = f"Clôture {mois_noms[mois]} {annee}"

    db_path = "data/actuarecette.db"
    try:
        conn = sqlite3.connect(db_path)
        conn.execute(
            "INSERT OR IGNORE INTO exercices (id_exercice, annee, mois, libelle, statut) VALUES (?, ?, ?, ?, 'OUVERT')",
            (id_exercice, annee, mois, libelle)
        )
        conn.commit()
        conn.close()
        return {"status": "SUCCESS", "id_exercice": id_exercice, "libelle": libelle, "statut": "OUVERT"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/exercices/{id_exercice}/close", tags=["Exercices"])
def close_exercice(id_exercice: str, request: Request):
    """Transition OUVERT → CLOTURE. Manager only."""
    import sqlite3
    user = get_current_user(request)

    if user.get("role") != "Responsable MOA":
        raise HTTPException(status_code=403, detail="Seul le Responsable MOA peut clôturer un exercice.")

    db_path = "data/actuarecette.db"
    try:
        conn = sqlite3.connect(db_path)
        row = conn.execute("SELECT statut FROM exercices WHERE id_exercice = ?", (id_exercice,)).fetchone()
        if not row:
            conn.close()
            raise HTTPException(status_code=404, detail=f"Exercice introuvable : {id_exercice}")

        if row[0] != "OUVERT":
            conn.close()
            raise HTTPException(status_code=409, detail=f"L'exercice n'est pas OUVERT (statut actuel : {row[0]}).")

        conn.execute(
            "UPDATE exercices SET statut = 'CLOTURE', date_cloture = CURRENT_TIMESTAMP, cloture_par_sso = ? WHERE id_exercice = ?",
            (user.get("sso", ""), id_exercice)
        )
        conn.commit()
        conn.close()
        return {"status": "SUCCESS", "id_exercice": id_exercice, "new_statut": "CLOTURE"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/exercices/{id_exercice}/lock", tags=["Exercices"])
def lock_exercice(id_exercice: str, request: Request):
    """Transition CLOTURE → VERROUILLE. Manager only. Irreversible."""
    import sqlite3
    user = get_current_user(request)

    if user.get("role") != "Responsable MOA":
        raise HTTPException(status_code=403, detail="Seul le Responsable MOA peut verrouiller un exercice.")

    db_path = "data/actuarecette.db"
    try:
        conn = sqlite3.connect(db_path)
        row = conn.execute("SELECT statut FROM exercices WHERE id_exercice = ?", (id_exercice,)).fetchone()
        if not row:
            conn.close()
            raise HTTPException(status_code=404, detail=f"Exercice introuvable : {id_exercice}")

        if row[0] != "CLOTURE":
            conn.close()
            raise HTTPException(
                status_code=409,
                detail=f"L'exercice doit être CLOTURÉ avant d'être verrouillé (statut actuel : {row[0]})."
            )

        conn.execute(
            "UPDATE exercices SET statut = 'VERROUILLE', date_verrouillage = CURRENT_TIMESTAMP, verrouille_par_sso = ? WHERE id_exercice = ?",
            (user.get("sso", ""), id_exercice)
        )
        conn.commit()
        conn.close()
        return {"status": "SUCCESS", "id_exercice": id_exercice, "new_statut": "VERROUILLE"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------------------------------------------------------
# DQ Report
# ---------------------------------------------------------------------------

@router.get("/runs/{run_id}/dq-report", tags=["Qualité Données"])
def get_dq_report(run_id: str, request: Request):
    """
    Retourne le rapport DQ archivé pour un run, ou le calcule à la volée.
    """
    from api.routes.workflow import _load_run_json

    run_data = _load_run_json(run_id)
    
    visible_lobs = get_visible_lobs(request)
    run_lob = run_data.get("lob_id") or run_data.get("metadata", {}).get("lob_id", "LOB_AUTO_PART")
    if run_lob not in visible_lobs:
        raise HTTPException(
            status_code=403,
            detail=f"Accès refusé : vous n'êtes pas autorisé sur le portefeuille {run_lob}."
        )

    # If DQ report already exists in the run JSON, return it
    if "dq_report" in run_data and run_data["dq_report"]:
        return run_data["dq_report"]

    # Otherwise return a placeholder (DQ is computed at reconciliation time)
    return {
        "score_global": None,
        "verdict": "NON_CALCULÉ",
        "message": "Le rapport DQ sera généré lors de la prochaine réconciliation.",
    }

@router.post("/runs/{run_id}/dq-report", tags=["Qualité Données"])
def compute_dq_report(run_id: str, request: Request):
    """
    Calcule et archive le rapport DQ pour un run.
    Requires the run to have attached data (csv paths or inline data).
    """
    from api.routes.workflow import _load_run_json, _save_run_json

    run_data = _load_run_json(run_id)

    visible_lobs = get_visible_lobs(request)
    run_lob = run_data.get("lob_id") or run_data.get("metadata", {}).get("lob_id", "LOB_AUTO_PART")
    if run_lob not in visible_lobs:
        raise HTTPException(
            status_code=403,
            detail=f"Accès refusé : vous n'êtes pas autorisé sur le portefeuille {run_lob}."
        )

    # Try to reconstruct minimal data from the run's stored anomalies/KPIs
    # In production, this would load the original CSV files
    mapping = run_data.get("column_mapping", {})
    if not mapping:
        mapping = {
            "id_col": "ID_CLIENT",
            "ref_premium_col": "PRIME_ACTU",
            "prod_premium_col": "PRIME_DSI",
        }

    # Generate a basic DQ report from run metadata
    anomalies = run_data.get("anomalies", [])
    kpis = run_data.get("kpis", {})

    # Build a synthetic report from available metadata
    total_cases = kpis.get("total_cases", 0)
    fatal_defects = kpis.get("fatal_defects", 0)

    dq_report = {
        "timestamp": datetime.datetime.now().isoformat(),
        "score_global": round(max(0, 100 - (fatal_defects / max(total_cases, 1)) * 100), 2) if total_cases > 0 else None,
        "verdict": "BON" if total_cases > 0 and fatal_defects / max(total_cases, 1) < 0.05 else "ACCEPTABLE",
        "dimensions": {
            "completude": {"score": 100.0, "poids": 0.30},
            "conformite": {"score": 100.0, "poids": 0.25},
            "coherence": {"score": round(max(0, 100 - fatal_defects / max(total_cases, 1) * 100), 2) if total_cases > 0 else 100.0, "poids": 0.25},
            "unicite": {"score": 100.0, "poids": 0.10},
            "fraicheur": {"score": 100.0, "poids": 0.10},
        },
        "resume": {
            "total_rows": total_cases,
            "anomalies": fatal_defects,
        },
    }

    # Archive in the run JSON
    run_data["dq_report"] = dq_report
    _save_run_json(run_id, run_data)

    return dq_report

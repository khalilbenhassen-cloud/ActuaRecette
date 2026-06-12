# tolerance_manager.py -- Seuils de tolerance par LOB (Phase 2c - T65)
"""
Gere les seuils de tolerance actuariels par portefeuille (LOB).
Les seuils sont stockes en base SQLite et servent de reference
pour la reconciliation et la certification.

Usage:
    from src.tolerance_manager import get_lob_tolerance, update_lob_tolerance
"""
import os
import sqlite3
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger("actuarecette.tolerance_manager")

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "actuarecette.db")

# Default tolerances (fallback if DB unavailable)
DEFAULT_TOLERANCES = {
    "LOB_AUTO_PART": {"seuil_materialite_pct": 0.20, "tolerance_unitaire": 0.05},
    "LOB_INCENDIE_RD": {"seuil_materialite_pct": 0.50, "tolerance_unitaire": 0.10},
    "LOB_MRH_HAB": {"seuil_materialite_pct": 0.20, "tolerance_unitaire": 0.05},
    "LOB_SANTE_IND": {"seuil_materialite_pct": 0.15, "tolerance_unitaire": 0.03},
    "LOB_PREV_COLL": {"seuil_materialite_pct": 0.30, "tolerance_unitaire": 0.08},
}

def _get_conn() -> Optional[sqlite3.Connection]:
    """Get a SQLite connection with WAL mode."""
    db = os.path.abspath(DB_PATH)
    if not os.path.exists(db):
        return None
    conn = sqlite3.connect(db, timeout=5)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=3000")
    conn.row_factory = sqlite3.Row
    return conn

def get_lob_tolerance(lob_id: str) -> Dict[str, float]:
    """
    Recupere les seuils de tolerance pour un portefeuille.

    Returns:
        Dict avec seuil_materialite_pct et tolerance_unitaire.
    """
    try:
        conn = _get_conn()
        if conn:
            # From portefeuilles table
            row = conn.execute(
                "SELECT seuil_materialite_pct FROM portefeuilles WHERE id_portefeuille = ?",
                (lob_id,),
            ).fetchone()

            tolerance_unitaire = 0.05  # default
            rule = conn.execute(
                "SELECT tolerance_unitaire FROM regles_recette "
                "WHERE id_portefeuille = ? AND statut = 'ACTIF' "
                "ORDER BY version_regle DESC LIMIT 1",
                (lob_id,),
            ).fetchone()

            conn.close()

            if row:
                return {
                    "seuil_materialite_pct": float(row["seuil_materialite_pct"]),
                    "tolerance_unitaire": float(rule["tolerance_unitaire"]) if rule else tolerance_unitaire,
                }
    except Exception as e:
        logger.warning(f"DB read error for LOB {lob_id}: {e}")

    # Fallback to defaults
    return DEFAULT_TOLERANCES.get(lob_id, {
        "seuil_materialite_pct": 0.20,
        "tolerance_unitaire": 0.05,
    })

def get_all_tolerances() -> List[Dict[str, Any]]:
    """
    Recupere les seuils de tous les portefeuilles.
    """
    result = []
    try:
        conn = _get_conn()
        if conn:
            rows = conn.execute(
                "SELECT id_portefeuille, code_metier, libelle, type_risque, "
                "seuil_materialite_pct FROM portefeuilles ORDER BY id_portefeuille"
            ).fetchall()
            conn.close()

            for row in rows:
                lob_id = row["id_portefeuille"]
                tol = get_lob_tolerance(lob_id)
                result.append({
                    "id_portefeuille": lob_id,
                    "code_metier": row["code_metier"],
                    "libelle": row["libelle"],
                    "type_risque": row["type_risque"],
                    "seuil_materialite_pct": tol["seuil_materialite_pct"],
                    "tolerance_unitaire": tol["tolerance_unitaire"],
                })
            return result
    except Exception as e:
        logger.warning(f"DB read error: {e}")

    # Fallback
    for lob_id, vals in DEFAULT_TOLERANCES.items():
        result.append({
            "id_portefeuille": lob_id,
            "code_metier": lob_id,
            "libelle": lob_id,
            "type_risque": "IARD",
            **vals,
        })
    return result

def update_lob_tolerance(
    lob_id: str,
    seuil_materialite_pct: Optional[float] = None,
    tolerance_unitaire: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Met a jour les seuils de tolerance pour un portefeuille.
    Retourne les nouvelles valeurs.
    """
    conn = _get_conn()
    if not conn:
        raise RuntimeError("Base de donnees non disponible.")

    try:
        if seuil_materialite_pct is not None:
            conn.execute(
                "UPDATE portefeuilles SET seuil_materialite_pct = ? WHERE id_portefeuille = ?",
                (seuil_materialite_pct, lob_id),
            )

        if tolerance_unitaire is not None:
            # Update the active rule for this LOB
            conn.execute(
                "UPDATE regles_recette SET tolerance_unitaire = ? "
                "WHERE id_portefeuille = ? AND statut = 'ACTIF'",
                (tolerance_unitaire, lob_id),
            )

        conn.commit()
        conn.close()
    except Exception as e:
        conn.close()
        raise RuntimeError(f"Erreur mise a jour seuils: {e}")

    return get_lob_tolerance(lob_id)

# ---------------------------------------------------------------------------
# T66 -- Detection runs parasites
# ---------------------------------------------------------------------------

def detect_parasitic_runs(
    runs: List[Dict[str, Any]],
    max_duration_seconds: int = 5,
    min_cases: int = 10,
) -> List[Dict[str, Any]]:
    """
    Detecte les runs parasites (runs anormalement courts ou vides).

    Criteres de detection :
    1. Runs avec 0 dossiers traites
    2. Runs avec duree < max_duration_seconds (calcul trop rapide = donnees manquantes)
    3. Runs dont le taux de conformite est exactement 0% ou 100% sur un grand volume
    4. Runs en double (meme nom + meme periode a quelques minutes d'ecart)

    Args:
        runs: Liste de dicts de runs.
        max_duration_seconds: Duree max pour suspecter un run parasite.
        min_cases: Nombre minimum de dossiers attendu.

    Returns:
        Liste de runs suspects avec raison.
    """
    suspects = []
    seen_names = {}

    for run in runs:
        run_id = run.get("run_id", "")
        run_name = run.get("run_name", "")
        total_cases = run.get("total_cases", run.get("kpis", {}).get("total_cases", 0))
        success_rate = run.get("success_rate_pct", run.get("kpis", {}).get("success_rate_pct", 0))
        timestamp = run.get("timestamp", "")

        reasons = []

        # 1. Empty runs
        if total_cases == 0:
            reasons.append("VIDE: 0 dossier traite")

        # 2. Too few cases
        elif total_cases < min_cases:
            reasons.append(f"INSUFFISANT: seulement {total_cases} dossiers (min={min_cases})")

        # 3. Suspicious 100% on large volume
        if total_cases > 100 and success_rate == 100.0:
            reasons.append(f"SUSPECT: 100% de conformite sur {total_cases} dossiers")

        # 4. Duplicate runs (same name within 10 minutes)
        name_key = run_name.strip().lower()
        if name_key in seen_names:
            prev_ts = seen_names[name_key]
            try:
                import datetime
                t1 = datetime.datetime.fromisoformat(prev_ts)
                t2 = datetime.datetime.fromisoformat(timestamp)
                delta = abs((t2 - t1).total_seconds())
                if delta < 600:  # 10 minutes
                    reasons.append(f"DOUBLON: meme nom que run precedent ({delta:.0f}s d'ecart)")
            except Exception:
                pass
        seen_names[name_key] = timestamp

        if reasons:
            suspects.append({
                "run_id": run_id,
                "run_name": run_name,
                "total_cases": total_cases,
                "success_rate_pct": success_rate,
                "timestamp": timestamp,
                "reasons": reasons,
                "severity": "CRITICAL" if any("VIDE" in r for r in reasons) else "WARNING",
            })

    return suspects

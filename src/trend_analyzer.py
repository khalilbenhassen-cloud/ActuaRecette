"""
Trend Analyzer \u2014 Phase 2d
=========================

Analyse les tendances multi-mois des KPIs de recette,
d\u00e9tecte les d\u00e9gradations et les corr\u00e9lations avec les d\u00e9ploiements IT.

M\u00e9thode : R\u00e9gression lin\u00e9aire simple (OLS) sur les N derniers snapshots.

Usage:
    from src.trend_analyzer import compute_trend, detect_deployment_correlation
"""

from typing import Dict, Any, List, Optional
import numpy as np
import os
import json
import sqlite3
import logging
import datetime

logger = logging.getLogger("actuarecette.trend_analyzer")

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "actuarecette.db")

def _get_conn() -> Optional[sqlite3.Connection]:
    """Get a SQLite connection."""
    db = os.path.abspath(DB_PATH)
    if not os.path.exists(db):
        return None
    conn = sqlite3.connect(db, timeout=5)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=3000")
    conn.row_factory = sqlite3.Row
    return conn

# ===========================================================================
# T76 -- Hook snapshot a la certification
# ===========================================================================

def save_trend_snapshot(
    run_id: str,
    lob_id: str,
    periode: str,
    kpis: Dict[str, Any],
    anomalies: List[Dict[str, Any]],
    version_moteur: str = "ActuaRecette-v6.0",
) -> bool:
    """
    Enregistre un snapshot de tendance dans la table trend_snapshots.
    Appele automatiquement lors de la certification d'un run (T76).
    """
    conn = _get_conn()
    if not conn:
        logger.warning("DB non disponible pour snapshot tendance.")
        return False

    try:
        total = kpis.get("total_cases", 0)
        conformes = kpis.get("conform_cases", 0)
        taux = kpis.get("success_rate_pct", 0.0)
        nb_anomalies = kpis.get("fatal_defects", 0)
        prime_risque = kpis.get("total_absolute_delta_euros", 0.0)

        cat_counts = {}
        coeff_impact = {}
        for anom in anomalies:
            cat = anom.get("anomaly_category", "Autre")
            cat_counts[cat] = cat_counts.get(cat, 0) + 1
            coeff = anom.get("coefficient_fautif", "")
            if coeff:
                impact = abs(anom.get("abs_deviation", 0.0))
                coeff_impact[coeff] = coeff_impact.get(coeff, 0.0) + impact

        conn.execute(
            """INSERT OR REPLACE INTO trend_snapshots
            (id_portefeuille, periode, id_run, version_moteur_dsi,
             total_dossiers, dossiers_conformes, taux_conformite,
             nb_anomalies, prime_a_risque,
             anomalies_par_categorie, impact_par_coefficient)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                lob_id, periode, run_id, version_moteur,
                total, conformes, taux,
                nb_anomalies, prime_risque,
                json.dumps(cat_counts, ensure_ascii=False),
                json.dumps(coeff_impact, ensure_ascii=False),
            ),
        )
        conn.commit()
        conn.close()
        logger.info(f"Snapshot tendance enregistre: {lob_id}/{periode}/{run_id}")
        return True
    except Exception as e:
        logger.error(f"Erreur snapshot tendance: {e}")
        try:
            conn.close()
        except Exception:
            pass
        return False

def get_trend_data(lob_id: str, limit: int = 12) -> List[Dict[str, Any]]:
    """Recupere les snapshots de tendance pour un portefeuille."""
    conn = _get_conn()
    if not conn:
        return []
    try:
        rows = conn.execute(
            """SELECT id_portefeuille, periode, id_run, date_snapshot,
                      version_moteur_dsi, total_dossiers, dossiers_conformes,
                      taux_conformite, nb_anomalies, prime_a_risque,
                      anomalies_par_categorie, impact_par_coefficient
               FROM trend_snapshots
               WHERE id_portefeuille = ?
               ORDER BY date_snapshot ASC
               LIMIT ?""",
            (lob_id, limit),
        ).fetchall()
        conn.close()
        result = []
        for row in rows:
            snap = dict(row)
            try:
                snap["anomalies_par_categorie"] = json.loads(snap.get("anomalies_par_categorie") or "{}")
            except Exception:
                snap["anomalies_par_categorie"] = {}
            try:
                snap["impact_par_coefficient"] = json.loads(snap.get("impact_par_coefficient") or "{}")
            except Exception:
                snap["impact_par_coefficient"] = {}
            result.append(snap)
        return result
    except Exception as e:
        logger.error(f"Erreur lecture tendances: {e}")
        return []

def get_coefficient_trends(snapshots: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Extrait l'evolution de l'impact par coefficient sur les periodes."""
    coeff_history: Dict[str, List[Dict[str, Any]]] = {}
    for snap in snapshots:
        periode = snap.get("periode", "")
        impacts = snap.get("impact_par_coefficient", {})
        if isinstance(impacts, str):
            try:
                impacts = json.loads(impacts)
            except Exception:
                impacts = {}
        for coeff, impact in impacts.items():
            if coeff not in coeff_history:
                coeff_history[coeff] = []
            coeff_history[coeff].append({"periode": periode, "impact": round(float(impact), 2)})
    return coeff_history

def compute_trend(
    snapshots: List[Dict[str, Any]],
    metric: str = "taux_conformite",
    window: int = 6,
) -> Dict[str, Any]:
    """
    Calcule la tendance d'une m\u00e9trique sur les N derniers snapshots.
    
    Args:
        snapshots: Historique des snapshots tri\u00e9s par date (ancien \u2192 r\u00e9cent).
        metric: Nom de la m\u00e9trique \u00e0 analyser.
        window: Nombre de snapshots pour la r\u00e9gression.
    
    Returns:
        Dict avec current_value, previous_value, trend, slope, r_squared, projection_m3, alert.
    """
    if not snapshots:
        return _empty_trend(metric)
    
    # Use last N snapshots
    recent = snapshots[-window:]
    values = [s.get(metric, 0.0) for s in recent]
    
    if len(values) < 2:
        return {
            "metric": metric,
            "current_value": values[-1] if values else 0,
            "previous_value": None,
            "trend": "STABLE",
            "slope": 0.0,
            "r_squared": 0.0,
            "projection_m3": values[-1] if values else 0,
            "alert": None,
            "data_points": len(values),
        }
    
    # Simple linear regression (OLS)
    x = np.arange(len(values), dtype=float)
    y = np.array(values, dtype=float)
    
    # Filter out NaN
    mask = ~np.isnan(y)
    x_clean = x[mask]
    y_clean = y[mask]
    
    if len(x_clean) < 2:
        return _empty_trend(metric)
    
    # Linear regression: y = slope * x + intercept
    n = len(x_clean)
    sum_x = x_clean.sum()
    sum_y = y_clean.sum()
    sum_xy = (x_clean * y_clean).sum()
    sum_xx = (x_clean * x_clean).sum()
    
    denom = n * sum_xx - sum_x * sum_x
    if abs(denom) < 1e-10:
        slope = 0.0
        intercept = y_clean.mean()
    else:
        slope = (n * sum_xy - sum_x * sum_y) / denom
        intercept = (sum_y - slope * sum_x) / n
    
    # R-squared
    y_pred = slope * x_clean + intercept
    ss_res = ((y_clean - y_pred) ** 2).sum()
    ss_tot = ((y_clean - y_clean.mean()) ** 2).sum()
    r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
    
    # Trend classification
    if abs(slope) < 0.5:
        trend = "STABLE"
    elif slope > 0:
        trend = "IMPROVING"
    else:
        trend = "DEGRADING"
    
    # Projection at M+3
    projection_m3 = slope * (len(values) + 2) + intercept
    
    # Alert if degrading significantly
    alert = None
    if slope < -2.0 and r_squared > 0.5:
        alert = "DEGRADATION_CRITIQUE"
    elif slope < -1.0 and r_squared > 0.3:
        alert = "DEGRADATION_MODEREE"
    
    return {
        "metric": metric,
        "current_value": round(float(values[-1]), 2),
        "previous_value": round(float(values[-2]), 2) if len(values) >= 2 else None,
        "trend": trend,
        "slope": round(float(slope), 4),
        "r_squared": round(float(r_squared), 4),
        "projection_m3": round(float(np.clip(projection_m3, 0, 100)), 2) if "pct" in metric or "taux" in metric else round(float(projection_m3), 2),
        "alert": alert,
        "data_points": len(values),
    }

def detect_deployment_correlation(
    snapshots: List[Dict[str, Any]],
    metric: str = "taux_conformite",
    degradation_threshold: float = 2.0,
) -> List[Dict[str, Any]]:
    """
    Identifie les ruptures de tendance corr\u00e9l\u00e9es aux changements de version IT.
    
    Args:
        snapshots: Historique tri\u00e9 par date.
        metric: M\u00e9trique \u00e0 surveiller.
        degradation_threshold: Seuil de d\u00e9gradation en points pour d\u00e9clencher une alerte.
    
    Returns:
        Liste de corr\u00e9lations d\u00e9tect\u00e9es.
    """
    if len(snapshots) < 2:
        return []
    
    correlations = []
    
    for i in range(1, len(snapshots)):
        prev = snapshots[i - 1]
        curr = snapshots[i]
        
        prev_version = prev.get("version_moteur_dsi", "")
        curr_version = curr.get("version_moteur_dsi", "")
        
        # Skip if same version or no version info
        if not prev_version or not curr_version or prev_version == curr_version:
            continue
        
        prev_value = prev.get(metric, 0)
        curr_value = curr.get(metric, 0)
        delta = curr_value - prev_value
        
        if delta < -degradation_threshold:
            correlations.append({
                "periode": curr.get("periode", "?"),
                "version_avant": prev_version,
                "version_apres": curr_version,
                "metric_avant": round(float(prev_value), 2),
                "metric_apres": round(float(curr_value), 2),
                "delta": round(float(delta), 2),
                "diagnostic": (
                    f"D\u00e9gradation de {abs(delta):.1f} points du {metric} "
                    f"corr\u00e9l\u00e9e au d\u00e9ploiement {curr_version} "
                    f"(p\u00e9riode {curr.get('periode', '?')})."
                ),
            })
    
    return correlations

def compute_coefficient_impact(
    snapshots: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Agr\u00e8ge l'impact par coefficient fautif sur l'ensemble des snapshots.
    
    Args:
        snapshots: Historique avec champ impact_par_coefficient (JSON dict).
    
    Returns:
        Liste tri\u00e9e par impact d\u00e9croissant.
    """
    import json
    
    total_impact = {}
    
    for snap in snapshots:
        impact_raw = snap.get("impact_par_coefficient", "{}")
        if isinstance(impact_raw, str):
            try:
                impact = json.loads(impact_raw)
            except json.JSONDecodeError:
                continue
        elif isinstance(impact_raw, dict):
            impact = impact_raw
        else:
            continue
        
        for coeff, amount in impact.items():
            total_impact[coeff] = total_impact.get(coeff, 0.0) + float(amount)
    
    grand_total = sum(abs(v) for v in total_impact.values()) or 1.0
    
    result = []
    for coeff, amount in sorted(total_impact.items(), key=lambda x: abs(x[1]), reverse=True):
        result.append({
            "coefficient": coeff,
            "impact_euros": round(amount, 2),
            "pct_total": round(abs(amount) / grand_total * 100, 1),
        })
    
    return result

def _empty_trend(metric: str) -> Dict[str, Any]:
    """Return an empty trend result."""
    return {
        "metric": metric,
        "current_value": 0,
        "previous_value": None,
        "trend": "STABLE",
        "slope": 0.0,
        "r_squared": 0.0,
        "projection_m3": 0,
        "alert": None,
        "data_points": 0,
    }

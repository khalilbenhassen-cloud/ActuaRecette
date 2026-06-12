"""
Module Data Quality Report Generator (Phase 2c)
================================================

G\u00e9n\u00e8re un rapport structur\u00e9 de qualit\u00e9 de donn\u00e9es multidimensionnel.
Chaque dimension est not\u00e9e sur 100 ; le score global est la moyenne pond\u00e9r\u00e9e.

Dimensions :
  1. Compl\u00e9tude   (30%) \u2014 Taux de valeurs non-NULL
  2. Conformit\u00e9   (25%) \u2014 Types corrects et formats valides
  3. Coh\u00e9rence    (25%) \u2014 R\u00e8gles m\u00e9tier (bornes \u00e2ge, primes, bonus-malus)
  4. Unicit\u00e9      (10%) \u2014 Taux de doublons sur la cl\u00e9 primaire
  5. Fraicheur    (10%) \u2014 \u00c2ge du fichier (optionnel)

Usage:
    from src.dq_report_generator import generate_dq_report
    report = generate_dq_report(df, mapping, tolerance_overrides={})
"""

import datetime
from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np

# ---------------------------------------------------------------------------
# Weights for each dimension (sum = 1.0)
# ---------------------------------------------------------------------------
DQ_WEIGHTS = {
    "completude": 0.30,
    "conformite": 0.25,
    "coherence": 0.25,
    "unicite": 0.10,
    "fraicheur": 0.10,
}

# Default tolerance thresholds (adjustable via UI sliders)
DEFAULT_TOLERANCES = {
    "null_pct_threshold": 0.05,       # >5% nulls = warning
    "age_min": 18,
    "age_max": 95,
    "prime_min": 0.01,                # Prime > 0
    "bonus_malus_min": 0.50,
    "bonus_malus_max": 1.50,
    "duplicate_threshold": 0.01,      # >1% duplicates = warning
    "freshness_max_days": 30,         # Data older than 30 days = stale
}

def _score_completude(df: pd.DataFrame, mapped_cols: List[str]) -> Dict[str, Any]:
    """Score de compl\u00e9tude : taux de valeurs non-NULL sur les colonnes mapp\u00e9es."""
    if not mapped_cols or df.empty:
        return {"score": 100.0, "details": [], "total_nulls": 0, "total_cells": 0}

    total_cells = len(df) * len(mapped_cols)
    total_nulls = 0
    details = []

    for col in mapped_cols:
        if col not in df.columns:
            continue
        null_count = int(df[col].isnull().sum())
        total_nulls += null_count
        null_pct = null_count / len(df) if len(df) > 0 else 0
        details.append({
            "colonne": col,
            "null_count": null_count,
            "null_pct": round(null_pct * 100, 2),
            "statut": "OK" if null_pct <= 0.05 else "ALERTE",
        })

    score = max(0.0, (1 - total_nulls / total_cells) * 100) if total_cells > 0 else 100.0
    return {"score": round(score, 2), "details": details, "total_nulls": total_nulls, "total_cells": total_cells}

def _score_conformite(df: pd.DataFrame, mapped_cols: List[str]) -> Dict[str, Any]:
    """Score de conformit\u00e9 : types corrects et formats valides."""
    if not mapped_cols or df.empty:
        return {"score": 100.0, "details": [], "non_numeric_count": 0}

    non_numeric_total = 0
    details = []

    for col in mapped_cols:
        if col not in df.columns:
            continue
        col_series = df[col]
        coerced = pd.to_numeric(col_series, errors='coerce')
        non_numeric = int(coerced.isnull().sum() - col_series.isnull().sum())
        non_numeric_total += max(0, non_numeric)
        details.append({
            "colonne": col,
            "dtype": str(df[col].dtype),
            "non_numeric": max(0, non_numeric),
            "statut": "OK" if non_numeric <= 0 else "ALERTE",
        })

    total_cells = len(df) * len(mapped_cols) if mapped_cols else 1
    score = max(0.0, (1 - non_numeric_total / total_cells) * 100)
    return {"score": round(score, 2), "details": details, "non_numeric_count": non_numeric_total}

def _find_col(mapping: Dict[str, str], keywords: List[str]) -> Optional[str]:
    """Find column by fuzzy keyword match on mapping keys."""
    for key, col_name in mapping.items():
        if any(kw in key.lower() for kw in keywords):
            return col_name
    return None

def _score_coherence(
    df: pd.DataFrame,
    mapping: Dict[str, str],
    tolerances: Dict[str, Any],
) -> Dict[str, Any]:
    """Score de coh\u00e9rence : r\u00e8gles m\u00e9tier (bornes, plages)."""
    violations = 0
    checks = 0
    details = []

    age_col = _find_col(mapping, ["age", "\u00e2ge"])
    prime_col = _find_col(mapping, ["prime", "premium", "cotisation", "prm"])
    crm_col = _find_col(mapping, ["bonus", "malus", "crm", "coef"])

    def check_bounds(col, label, lo, hi):
        nonlocal violations, checks
        if not col or col not in df.columns:
            return
        coerced = pd.to_numeric(df[col], errors='coerce').dropna()
        n_total = len(coerced)
        if n_total == 0:
            return
        checks += n_total
        outliers = coerced[(coerced < lo) | (coerced > hi)]
        n_out = len(outliers)
        violations += n_out
        details.append({
            "regle": f"{label} dans [{lo}, {hi}]",
            "colonne": col,
            "violations": n_out,
            "total": n_total,
            "pct_ok": round((1 - n_out / n_total) * 100, 2),
        })

    check_bounds(age_col, "\u00c2ge", tolerances.get("age_min", 18), tolerances.get("age_max", 95))
    check_bounds(prime_col, "Prime", tolerances.get("prime_min", 0.01), 1e9)
    check_bounds(crm_col, "Bonus-Malus", tolerances.get("bonus_malus_min", 0.50), tolerances.get("bonus_malus_max", 1.50))

    score = max(0.0, (1 - violations / checks) * 100) if checks > 0 else 100.0
    return {"score": round(score, 2), "details": details, "violations": violations, "checks": checks}

def _score_unicite(df: pd.DataFrame, id_col: Optional[str]) -> Dict[str, Any]:
    """Score d'unicit\u00e9 : taux de doublons sur la cl\u00e9 primaire."""
    if not id_col or id_col not in df.columns or df.empty:
        return {"score": 100.0, "duplicates": 0, "total": 0, "pct_duplicates": 0.0}

    total = len(df)
    unique = df[id_col].nunique()
    duplicates = total - unique
    pct = duplicates / total * 100 if total > 0 else 0
    score = max(0.0, 100 - pct)
    return {"score": round(score, 2), "duplicates": duplicates, "total": total, "pct_duplicates": round(pct, 2)}

def _score_fraicheur(file_date: Optional[datetime.datetime] = None) -> Dict[str, Any]:
    """Score de fraicheur : \u00e2ge du fichier (d\u00e9faut : aujourd'hui = 100%)."""
    if file_date is None:
        return {"score": 100.0, "age_days": 0, "date_fichier": datetime.datetime.now().isoformat()}

    age_days = (datetime.datetime.now() - file_date).days
    # Linear decay: 100% at 0 days, 0% at 90 days
    score = max(0.0, min(100.0, 100 - (age_days / 90 * 100)))
    return {"score": round(score, 2), "age_days": age_days, "date_fichier": file_date.isoformat()}

def generate_dq_report(
    df: pd.DataFrame,
    mapping: Dict[str, str],
    tolerance_overrides: Optional[Dict[str, Any]] = None,
    file_date: Optional[datetime.datetime] = None,
) -> Dict[str, Any]:
    """
    G\u00e9n\u00e8re un rapport DQ structur\u00e9 multidimensionnel.
    
    Args:
        df: Le DataFrame \u00e0 auditer.
        mapping: Le mapping de colonnes fonctionnelles.
        tolerance_overrides: Surcharges des seuils de tol\u00e9rance (depuis UI sliders).
        file_date: Date du fichier source (pour la fraicheur).
    
    Returns:
        Rapport DQ complet avec score global et d\u00e9tails par dimension.
    """
    tolerances = {**DEFAULT_TOLERANCES, **(tolerance_overrides or {})}

    # Colonnes mapp\u00e9es (num\u00e9riques uniquement pour certains checks)
    mapped_cols = [v for v in mapping.values() if v in df.columns]
    id_col = mapping.get("id_col") or mapping.get("id_assure") or _find_col(mapping, ["id", "client", "assur\u00e9"])

    # Compute each dimension
    completude = _score_completude(df, mapped_cols)
    conformite = _score_conformite(df, mapped_cols)
    coherence = _score_coherence(df, mapping, tolerances)
    unicite = _score_unicite(df, id_col)
    fraicheur = _score_fraicheur(file_date)

    # Weighted global score
    global_score = (
        completude["score"] * DQ_WEIGHTS["completude"]
        + conformite["score"] * DQ_WEIGHTS["conformite"]
        + coherence["score"] * DQ_WEIGHTS["coherence"]
        + unicite["score"] * DQ_WEIGHTS["unicite"]
        + fraicheur["score"] * DQ_WEIGHTS["fraicheur"]
    )

    # DQ verdict
    if global_score >= 95:
        verdict = "EXCELLENT"
        verdict_color = "var(--ar-conforme)"
    elif global_score >= 80:
        verdict = "BON"
        verdict_color = "var(--ar-info)"
    elif global_score >= 60:
        verdict = "ACCEPTABLE"
        verdict_color = "var(--ar-warning)"
    else:
        verdict = "INSUFFISANT"
        verdict_color = "var(--ar-anomalie)"

    return {
        "timestamp": datetime.datetime.now().isoformat(),
        "score_global": round(global_score, 2),
        "verdict": verdict,
        "verdict_color": verdict_color,
        "tolerances_used": tolerances,
        "dimensions": {
            "completude": {**completude, "poids": DQ_WEIGHTS["completude"]},
            "conformite": {**conformite, "poids": DQ_WEIGHTS["conformite"]},
            "coherence": {**coherence, "poids": DQ_WEIGHTS["coherence"]},
            "unicite": {**unicite, "poids": DQ_WEIGHTS["unicite"]},
            "fraicheur": {**fraicheur, "poids": DQ_WEIGHTS["fraicheur"]},
        },
        "resume": {
            "total_rows": len(df),
            "total_cols": len(mapped_cols),
            "total_nulls": completude["total_nulls"],
            "total_type_errors": conformite["non_numeric_count"],
            "total_business_violations": coherence["violations"],
            "total_duplicates": unicite["duplicates"],
        }
    }

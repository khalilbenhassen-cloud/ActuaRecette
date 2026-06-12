"""
Root Cause Engine \u2014 Phase 2d
==============================

D\u00e9compose les \u00e9carts de prime en contributions marginales par coefficient
et d\u00e9tecte les patterns syst\u00e9miques (double application, inversion, bar\u00e8me obsol\u00e8te...).

M\u00e9thode : D\u00e9composition log-lin\u00e9aire (Shapley simplifi\u00e9) pour coefficients multiplicatifs.

Usage:
    from src.root_cause_engine import decompose_variance, detect_systematic_patterns
"""

import math
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np

# ---------------------------------------------------------------------------
# Pattern detection thresholds
# ---------------------------------------------------------------------------
PATTERN_THRESHOLDS = {
    "DOUBLE_APPLICATION": 0.01,     # |prod - ref^2| < threshold * ref^2
    "INVERSION": 0.01,              # |prod - 1/ref| < threshold * 1/ref
    "ARRONDI_SYSTEMATIQUE": 0.005,  # All diffs match rounding to 1 decimal
}

def decompose_variance(
    ref_row: Dict[str, Any],
    prod_row: Dict[str, Any],
    coefficients: List[str],
    base_col: str = "PRIME_BASE",
) -> Dict[str, Any]:
    """
    D\u00e9compose l'\u00e9cart de prime en contribution de chaque coefficient.
    
    M\u00e9thode : D\u00e9composition log-lin\u00e9aire.
    Pour coefficients multiplicatifs : Prime = Base \u00d7 \u03a0(C_i)
    
    log(Prime) = log(Base) + \u03a3 log(C_i)
    \u00e9cart_log_i = log(prod_C_i) - log(ref_C_i)
    contribution_i = \u00e9cart_log_i / \u03a3|\u00e9cart_log_j| \u00d7 \u00e9cart_total
    
    Args:
        ref_row: Ligne du fichier r\u00e9f\u00e9rence (avec coefficients).
        prod_row: Ligne du fichier production (avec coefficients).
        coefficients: Liste des noms de colonnes coefficients.
        base_col: Nom de la colonne prime de base.
    
    Returns:
        Dict avec ecart_total, decomposition[], diagnostic, pattern, coefficient_fautif.
    """
    ref_base = _safe_float(ref_row.get(base_col, 0))
    prod_base = _safe_float(prod_row.get(base_col, 0))
    
    # Calculate total primes
    ref_prime = ref_base
    prod_prime = prod_base
    
    decomposition = []
    log_diffs = []
    
    for coeff_name in coefficients:
        ref_c = _safe_float(ref_row.get(coeff_name, 1.0))
        prod_c = _safe_float(prod_row.get(coeff_name, 1.0))
        
        ref_prime *= ref_c
        prod_prime *= prod_c
        
        # Log decomposition (guard against 0 or negative)
        ref_log = math.log(max(ref_c, 1e-10))
        prod_log = math.log(max(prod_c, 1e-10))
        log_diff = prod_log - ref_log
        log_diffs.append(log_diff)
        
        # Detect pattern for this coefficient
        pattern = _detect_coefficient_pattern(ref_c, prod_c)
        
        decomposition.append({
            "coefficient": coeff_name,
            "ref": round(ref_c, 6),
            "prod": round(prod_c, 6),
            "ecart": round(prod_c - ref_c, 6),
            "log_diff": round(log_diff, 6),
            "pattern": pattern,
        })
    
    ecart_total = prod_prime - ref_prime
    
    # Distribute the total deviation proportionally to log contributions
    total_abs_log_diff = sum(abs(ld) for ld in log_diffs)
    if total_abs_log_diff > 0:
        for i, item in enumerate(decomposition):
            weight = abs(log_diffs[i]) / total_abs_log_diff
            item["contribution_euros"] = round(ecart_total * weight, 2)
            item["contribution_pct"] = round(weight * 100, 2)
    else:
        for item in decomposition:
            item["contribution_euros"] = 0.0
            item["contribution_pct"] = 0.0
    
    # Sort by absolute contribution
    decomposition.sort(key=lambda x: abs(x.get("contribution_euros", 0)), reverse=True)
    
    # Identify the main culprit
    main_culprit = decomposition[0] if decomposition else None
    coefficient_fautif = main_culprit["coefficient"] if main_culprit else None
    pattern = main_culprit.get("pattern") if main_culprit else None
    
    # Generate diagnostic text
    diagnostic = _generate_diagnostic(main_culprit, ecart_total) if main_culprit else "Aucun \u00e9cart d\u00e9tect\u00e9."
    
    return {
        "ecart_total": round(ecart_total, 2),
        "ref_prime": round(ref_prime, 2),
        "prod_prime": round(prod_prime, 2),
        "decomposition": decomposition,
        "diagnostic": diagnostic,
        "pattern": pattern,
        "coefficient_fautif": coefficient_fautif,
    }

def detect_systematic_patterns(
    anomalies_df: pd.DataFrame,
    coefficient_fautif_col: str = "coefficient_fautif",
    impact_col: str = "ecart_total",
) -> List[Dict[str, Any]]:
    """
    Regroupe les anomalies par coefficient fautif et d\u00e9tecte les patterns r\u00e9currents.
    
    Args:
        anomalies_df: DataFrame avec colonnes coefficient_fautif, ecart_total, pattern.
        coefficient_fautif_col: Nom de la colonne contenant le coefficient fautif.
        impact_col: Nom de la colonne contenant l'impact financier.
    
    Returns:
        Liste de patterns syst\u00e9miques d\u00e9tect\u00e9s.
    """
    if anomalies_df.empty or coefficient_fautif_col not in anomalies_df.columns:
        return []
    
    patterns = []
    
    for coeff, group in anomalies_df.groupby(coefficient_fautif_col):
        if pd.isna(coeff) or not coeff:
            continue
            
        nb_dossiers = len(group)
        impact_total = group[impact_col].sum() if impact_col in group.columns else 0.0
        
        # Determine the dominant pattern
        pattern_counts = group["pattern"].value_counts() if "pattern" in group.columns else pd.Series()
        dominant_pattern = pattern_counts.index[0] if not pattern_counts.empty else "INCONNU"
        
        # Generate recommendation
        recommendation = _pattern_recommendation(dominant_pattern, str(coeff))
        
        patterns.append({
            "coefficient": str(coeff),
            "pattern": dominant_pattern,
            "nb_dossiers_affectes": nb_dossiers,
            "impact_total_euros": round(float(impact_total), 2),
            "diagnostic": _pattern_diagnostic(dominant_pattern, str(coeff), nb_dossiers, float(impact_total)),
            "recommandation": recommendation,
        })
    
    # Sort by impact
    patterns.sort(key=lambda x: abs(x["impact_total_euros"]), reverse=True)
    return patterns

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_float(val) -> float:
    """Safe conversion to float."""
    try:
        return float(val) if val is not None else 1.0
    except (ValueError, TypeError):
        return 1.0

def _detect_coefficient_pattern(ref: float, prod: float) -> Optional[str]:
    """Detect the pattern for a single coefficient comparison."""
    if ref <= 0 or prod <= 0:
        return None
    
    # DOUBLE_APPLICATION: prod \u2248 ref\u00b2
    ref_squared = ref * ref
    if ref > 1.01 and abs(prod - ref_squared) / max(ref_squared, 1e-10) < PATTERN_THRESHOLDS["DOUBLE_APPLICATION"]:
        return "DOUBLE_APPLICATION"
    
    # INVERSION: prod \u2248 1/ref
    ref_inv = 1.0 / ref
    if ref > 1.01 and abs(prod - ref_inv) / max(ref_inv, 1e-10) < PATTERN_THRESHOLDS["INVERSION"]:
        return "INVERSION"
    
    # ARRONDI: prod = round(ref, 1) and they differ
    rounded = round(ref, 1)
    if abs(prod - rounded) < 1e-6 and abs(ref - rounded) > 1e-4:
        return "ARRONDI_SYSTEMATIQUE"
    
    # PLANCHER_IGNORE: prod < ref when ref is exactly at a round threshold
    if ref == 150.0 and prod < ref:
        return "PLANCHER_IGNORE"
    
    # Generic deviation
    if abs(prod - ref) > 0.01:
        return "ECART_COEFFICIENT"
    
    return None

def _generate_diagnostic(culprit: Dict[str, Any], ecart_total: float) -> str:
    """Generate human-readable diagnostic text for the main culprit."""
    coeff = culprit["coefficient"]
    ref = culprit["ref"]
    prod = culprit["prod"]
    pattern = culprit.get("pattern", "")
    contrib = culprit.get("contribution_pct", 0)
    
    diag_parts = [f"Le coefficient {coeff} est {prod} en production vs {ref} en r\u00e9f\u00e9rence."]
    
    if pattern == "DOUBLE_APPLICATION":
        diag_parts.append(f"{prod} \u2248 {ref}\u00b2 ({ref*ref:.4f}) \u2192 Application en double d\u00e9tect\u00e9e.")
    elif pattern == "INVERSION":
        diag_parts.append(f"{prod} \u2248 1/{ref} ({1/ref:.4f}) \u2192 Coefficient invers\u00e9 (division au lieu de multiplication).")
    elif pattern == "ARRONDI_SYSTEMATIQUE":
        diag_parts.append(f"Arrondi syst\u00e9matique d\u00e9tect\u00e9 : {ref} \u2192 {round(ref, 1)}")
    elif pattern == "PLANCHER_IGNORE":
        diag_parts.append(f"R\u00e8gle de plancher non appliqu\u00e9e en production.")
    
    diag_parts.append(f"Contribution : {contrib:.0f}% de l'\u00e9cart total ({ecart_total:.2f} \u20ac).")
    
    return " ".join(diag_parts)

def _pattern_diagnostic(pattern: str, coeff: str, nb: int, impact: float) -> str:
    """Generate diagnostic for a systematic pattern."""
    diagnostics = {
        "DOUBLE_APPLICATION": f"Le coefficient {coeff} est syst\u00e9matiquement appliqu\u00e9 deux fois. {nb} dossiers touch\u00e9s. Impact : {impact:.2f} \u20ac.",
        "INVERSION": f"Le coefficient {coeff} est invers\u00e9 (division au lieu de multiplication). {nb} dossiers touch\u00e9s. Impact : {impact:.2f} \u20ac.",
        "ARRONDI_SYSTEMATIQUE": f"Perte de pr\u00e9cision syst\u00e9matique sur {coeff} (arrondi \u00e0 1 d\u00e9cimale). {nb} dossiers touch\u00e9s. Impact : {impact:.2f} \u20ac.",
        "PLANCHER_IGNORE": f"La r\u00e8gle de plancher n'est pas appliqu\u00e9e pour {coeff}. {nb} dossiers touch\u00e9s. Impact : {impact:.2f} \u20ac.",
        "ECART_COEFFICIENT": f"\u00c9cart syst\u00e9matique sur le coefficient {coeff}. {nb} dossiers touch\u00e9s. Impact : {impact:.2f} \u20ac.",
    }
    return diagnostics.get(pattern, f"Pattern {pattern} d\u00e9tect\u00e9 sur {coeff}. {nb} dossiers, {impact:.2f} \u20ac.")

def _pattern_recommendation(pattern: str, coeff: str) -> str:
    """Generate corrective action recommendation."""
    recommendations = {
        "DOUBLE_APPLICATION": f"V\u00e9rifier la fonction d'application de {coeff} dans le moteur de tarification. Supprimer l'appel dupliqu\u00e9.",
        "INVERSION": f"Corriger la formule de {coeff} : utiliser la multiplication au lieu de la division.",
        "ARRONDI_SYSTEMATIQUE": f"Aligner la pr\u00e9cision de {coeff} sur DECIMAL(18,6) au lieu de FLOAT dans le PGI.",
        "PLANCHER_IGNORE": f"Impl\u00e9menter MAX(valeur_calcul\u00e9e, seuil_plancher) pour {coeff} dans le moteur.",
        "ECART_COEFFICIENT": f"Investiguer la table de param\u00e9trage de {coeff} et comparer avec le bar\u00e8me actuariel.",
    }
    return recommendations.get(pattern, f"Investiguer le coefficient {coeff} dans le module de tarification.")

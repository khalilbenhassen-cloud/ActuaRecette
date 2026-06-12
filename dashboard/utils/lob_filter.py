# lob_filter.py - Cloisonnement LOB (Line of Business)
# Phase 1.4 \u2014 Assure que chaque utilisateur ne voit que les runs de ses LOBs
#
# Ce module centralise :
# 1. La classification d'un run vers un LOB (d\u00e9duit du nom ou du champ lob_id)
# 2. Le filtrage d'une liste de runs selon les droits de l'utilisateur
# 3. La validation qu'un utilisateur peut acc\u00e9der \u00e0 un run sp\u00e9cifique

from typing import List, Dict, Any, Optional

# ---------------------------------------------------------------------------
# Classification de portefeuille
# ---------------------------------------------------------------------------
# R\u00e9plique de classify_portfolio() de db_migration.py pour \u00e9viter
# une d\u00e9pendance circulaire (dashboard \u2192 src/).
# En Phase 3, cette fonction sera remplac\u00e9e par une lecture du champ lob_id
# directement dans le JSON du run.

LOB_KEYWORDS = {
    "LOB_AUTO_PART": ["auto", "car", "v\u00e9hicule", "voiture", "vehicule"],
    "LOB_INCENDIE_RD": ["incendie", "fire", "rd", "entreprise"],
    "LOB_MRH_HAB": ["mrh", "habitation", "home", "maison"],
}

# LOB par d\u00e9faut quand aucun mot-cl\u00e9 ne correspond
DEFAULT_LOB = "LOB_AUTO_PART"

def classify_run_lob(run: Dict[str, Any]) -> str:
    """
    D\u00e9termine le LOB d'un run.
    
    Strat\u00e9gie (pr\u00e9c\u00e9dence d\u00e9croissante) :
    1. Champ explicit `lob_id` dans le JSON (v6.0+)
    2. Champ `lob_id` dans metadata
    3. D\u00e9duction depuis le run_name via mots-cl\u00e9s
    """
    # 1. Champ racine lob_id (futur standard v6.0+)
    if run.get("lob_id"):
        return run["lob_id"]
    
    # 2. metadata.lob_id
    metadata = run.get("metadata", {})
    if metadata.get("lob_id"):
        return metadata["lob_id"]
    
    # 3. Heuristique par mot-cl\u00e9 dans le nom
    run_name = run.get("run_name", "").lower()
    for lob_id, keywords in LOB_KEYWORDS.items():
        if any(kw in run_name for kw in keywords):
            return lob_id
    
    return DEFAULT_LOB

def filter_runs_by_lobs(runs: List[Dict[str, Any]], 
                         visible_lobs: List[str]) -> List[Dict[str, Any]]:
    """
    Filtre une liste de runs pour ne garder que ceux accessibles
    par un utilisateur ayant acc\u00e8s aux LOBs sp\u00e9cifi\u00e9s.
    
    Args:
        runs: Liste de runs (dicts JSON)
        visible_lobs: LOBs auxquels l'utilisateur a acc\u00e8s
    
    Returns:
        Sous-liste des runs dont le LOB est dans visible_lobs
    """
    if not visible_lobs:
        import logging
        logging.getLogger("actuarecette.security").warning(
            "filter_runs_by_lobs appelé avec visible_lobs vide — aucun run ne sera visible."
        )
        return []
    
    # Optimisation : si tous les LOBs sont visibles, pas de filtrage
    all_known_lobs = set(LOB_KEYWORDS.keys())
    if set(visible_lobs) >= all_known_lobs:
        return runs
    
    visible_set = set(visible_lobs)
    return [r for r in runs if classify_run_lob(r) in visible_set]

def can_access_run(run: Dict[str, Any], visible_lobs: List[str]) -> bool:
    """
    V\u00e9rifie si un utilisateur peut acc\u00e9der \u00e0 un run sp\u00e9cifique.
    
    Args:
        run: Donn\u00e9es du run (dict JSON)
        visible_lobs: LOBs auxquels l'utilisateur a acc\u00e8s
    
    Returns:
        True si le LOB du run est dans visible_lobs
    """
    return classify_run_lob(run) in visible_lobs

def enrich_run_with_lob(run: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ajoute le champ lob_id au run s'il n'existe pas d\u00e9j\u00e0.
    Utile pour normaliser les anciens runs qui n'ont pas de lob_id.
    
    Ne modifie PAS le run original, retourne une copie enrichie.
    """
    if run.get("lob_id"):
        return run
    
    enriched = run.copy()
    enriched["lob_id"] = classify_run_lob(run)
    return enriched

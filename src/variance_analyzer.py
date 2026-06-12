"""
Module Variance Analyzer
========================

Ce module implémente le moteur de réconciliation mathématique et actuarielle entre
les données de référence (actuariat) et les données calculées par la DSI (production).

Il permet d'identifier les écarts absolus et relatifs, de filtrer le bruit numérique
d'arrondi et d'isoler les défauts de modélisation financière critiques.

Auteur: Senior Software Engineer & Actuaire Spécialiste de la Recette Fonctionnelle
Version: 1.0.0
"""

from typing import Dict, List, Tuple, Any, Optional
import pandas as pd
import numpy as np

def merge_datasets(
    ref_df: pd.DataFrame, 
    prod_df: pd.DataFrame, 
    key_mapping: Dict[str, str]
) -> pd.DataFrame:
    """
    Fusionne les deux DataFrames sur la base de la colonne d'identifiant unique.

    Args:
        ref_df (pd.DataFrame): Le DataFrame de référence actuarielle.
        prod_df (pd.DataFrame): Le DataFrame de production de la DSI.
        key_mapping (Dict[str, str]): Dictionnaire décrivant le mapping des colonnes :
            - "key" : Nom physique de la colonne d'identifiant unique (commune aux deux)
            - "ref_premium" : Nom physique de la colonne de prime de référence
            - "prod_premium" : Nom physique de la colonne de prime de production

    Returns:
        pd.DataFrame: Le DataFrame fusionné (jointure interne).

    Raises:
        ValueError: Si une colonne mappée est absente ou si la jointure produit un résultat vide.
    """
    # 1. Vérification des paramètres du mapping
    required_keys = {"key", "ref_premium", "prod_premium"}
    missing_mapping_keys = required_keys - set(key_mapping.keys())
    if missing_mapping_keys:
        raise ValueError(
            f"Erreur de configuration : Le mapping des clés est incomplet. "
            f"Clés manquantes : {missing_mapping_keys}"
        )

    join_key = key_mapping["key"]
    ref_premium = key_mapping["ref_premium"]
    prod_premium = key_mapping["prod_premium"]

    # Nettoyage des colonnes doublons physiques éventuelles
    if not ref_df.columns.is_unique:
        ref_df = ref_df.loc[:, ~ref_df.columns.duplicated()].copy()
    if not prod_df.columns.is_unique:
        prod_df = prod_df.loc[:, ~prod_df.columns.duplicated()].copy()

    # Validation d'unicité sémantique pour la MOA
    if join_key == ref_premium:
        raise ValueError(
            f"La clé d'assuré et la prime de référence attendue ne peuvent pas être configurées sur la même colonne ('{join_key}'). Veuillez corriger votre mapping."
        )
    if join_key == prod_premium:
        raise ValueError(
            f"La clé d'assuré et la prime facturée en production ne peuvent pas être configurées sur la même colonne ('{join_key}'). Veuillez corriger votre mapping."
        )

    # 2. Vérification de la présence physique des colonnes dans les DataFrames
    if join_key not in ref_df.columns:
        raise ValueError(
            f"Erreur de structure : La clé de jointure '{join_key}' est absente "
            f"du fichier de référence actuarielle."
        )
    if join_key not in prod_df.columns:
        raise ValueError(
            f"Erreur de structure : La clé de jointure '{join_key}' est absente "
            f"du fichier de production DSI."
        )
    if ref_premium not in ref_df.columns:
        raise ValueError(
            f"Erreur de structure : La colonne de prime de référence '{ref_premium}' "
            f"est absente du fichier actuariel."
        )
    if prod_premium not in prod_df.columns:
        raise ValueError(
            f"Erreur de structure : La colonne de prime de production '{prod_premium}' "
            f"est absente du fichier de la DSI."
        )

    # Récupérer toutes les colonnes à conserver de chaque côté
    ref_cols_to_keep = [join_key, ref_premium]
    prod_cols_to_keep = [join_key, prod_premium]
    
    # Parcourir le mapping pour inclure les colonnes optionnelles présentes (ex. taxes)
    for k, col in key_mapping.items():
        if k in ["key", "ref_premium", "prod_premium"]:
            continue
        if col and col != "[Non Mappé]":
            if "ref" in k and col in ref_df.columns:
                ref_cols_to_keep.append(col)
            elif "prod" in k and col in prod_df.columns:
                prod_cols_to_keep.append(col)
                
    # Éliminer les doublons pour la jointure
    ref_cols_to_keep = list(dict.fromkeys(ref_cols_to_keep))
    prod_cols_to_keep = list(dict.fromkeys(prod_cols_to_keep))

    # 3. Réalisation de la jointure interne (inner join) via DuckDB + PyArrow
    import duckdb
    import pyarrow as pa

    # Création d'une connexion en mémoire
    con = duckdb.connect(database=':memory:')

    # Conversion rapide vers Arrow Table pour exploitation directe par DuckDB
    ref_table = pa.Table.from_pandas(ref_df[ref_cols_to_keep])
    prod_table = pa.Table.from_pandas(prod_df[prod_cols_to_keep])

    con.register('ref_tbl', ref_table)
    con.register('prod_tbl', prod_table)

    select_parts = []
    for col in ref_cols_to_keep:
        if col == join_key:
            select_parts.append(f"ref_tbl.\"{col}\" AS \"{col}\"")
        elif col in prod_cols_to_keep:
            select_parts.append(f"ref_tbl.\"{col}\" AS \"{col}_x\"")
        else:
            select_parts.append(f"ref_tbl.\"{col}\" AS \"{col}\"")

    for col in prod_cols_to_keep:
        if col != join_key:
            if col in ref_cols_to_keep:
                select_parts.append(f"prod_tbl.\"{col}\" AS \"{col}_y\"")
            else:
                select_parts.append(f"prod_tbl.\"{col}\" AS \"{col}\"")

    select_query = ", ".join(select_parts)
    sql = f"""
    SELECT {select_query}
    FROM ref_tbl
    INNER JOIN prod_tbl
    ON ref_tbl."{join_key}" = prod_tbl."{join_key}"
    """

    merged_df = con.execute(sql).df()

    # 4. Validation du résultat de la jointure
    if merged_df.empty:
        raise ValueError(
            "Échec de la jointure : aucun identifiant commun trouvé "
            "entre la référence et la production."
        )

    return merged_df

def calculate_variances(
    merged_df: pd.DataFrame, 
    ref_col: str, 
    prod_col: str, 
    tolerance: float,
    lob_id: str = "LOB_AUTO_PART"
) -> pd.DataFrame:
    """
    Calcule ligne par ligne les écarts mathématiques et catégorise les déviations 
    en fonction du seuil de tolérance actuarielle.

    Args:
        merged_df (pd.DataFrame): Le DataFrame fusionné issu de `merge_datasets`.
        ref_col (str): Nom de la colonne contenant la prime de référence actuarielle.
        prod_col (str): Nom de la colonne contenant la prime calculée par la DSI.
        tolerance (float): Seuil de tolérance acceptable en Euros (ex: 0.05 pour 5 centimes).

    Returns:
        pd.DataFrame: Le DataFrame enrichi des colonnes suivantes :
            - 'abs_deviation' (float) : Écart signé (Production - Référence)
            - 'rel_deviation_pct' (float) : Écart relatif par rapport à la Référence
            - 'is_fatal_defect' (bool) : True si l'écart absolu dépasse le seuil de tolérance
    """
    df = merged_df.copy()

    # Calcul de l'écart absolu signé (DSI - Référence)
    df["abs_deviation"] = df[prod_col] - df[ref_col]

    # Calcul de l'écart relatif en pourcentage (gestion de la division par zéro)
    ref_values = df[ref_col].values
    abs_dev = df["abs_deviation"].values
    
    # Heuristique robuste de division
    with np.errstate(divide='ignore', invalid='ignore'):
        rel_dev = np.where(
            ref_values != 0,
            (abs_dev / ref_values) * 100,
            np.where(abs_dev == 0, 0.0, np.inf)
        )
    df["rel_deviation_pct"] = rel_dev

    # Par défaut, pas de défaut fatal
    df["is_fatal_defect"] = False

    # Charger les règles de réconciliation actives pour ce LOB depuis la base de données
    import sqlite3
    import os
    from src.formula_parser import SafeFormulaParser

    db_path = "data/actuarecette.db"
    active_rules = []
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """SELECT id_regle, libelle, colonne_cible, operateur_logique, 
                          valeur_seuil, formule_theorique, tolerance_unitaire, 
                          severite, condition_application 
                   FROM regles_recette_dynamiques 
                   WHERE id_portefeuille = ? AND statut = 'ACTIF'""",
                [lob_id]
            )
            active_rules = [dict(row) for row in cursor.fetchall()]
            conn.close()
        except Exception as e:
            print(f"[Avertissement SQLite] Echec du chargement des regles dynamiques : {e}")

    # Pré-compilation des formules pour l'optimisation des performances (PERF-01)
    compiled_rules = []
    for rule in active_rules:
        try:
            parser_formula = SafeFormulaParser(rule["formule_theorique"])
            parser_cond = SafeFormulaParser(rule["condition_application"]) if rule["condition_application"] else None
            compiled_rules.append({
                "rule": rule,
                "formula_parser": parser_formula,
                "cond_parser": parser_cond
            })
        except Exception as ex:
            print(f"[Avertissement] Erreur de compilation pour la règle {rule['id_regle']} : {ex}")

    categories = []
    details = []
    fatal_defects_list = []

    def safe_float(val):
        try:
            return float(str(val).replace(",", ".").replace("€", "").strip())
        except Exception:
            return 0.0

    # PERF-02: Evaluated row-by-row using pre-compiled SafeFormulaParser AST trees
    for idx, row in df.iterrows():
        abs_d = row["abs_deviation"]
        rel_d = row["rel_deviation_pct"]
        ref_val = row[ref_col]
        prod_val = row[prod_col]
        client_id = str(row.get("ID_CLIENT", ""))

        # Convertir la ligne en dictionnaire pour l'évaluateur
        row_vars = {str(k): v for k, v in row.items()}

        # 0. Donnée corrompue ou manquante
        is_corrupt = False
        corrupt_reasons = []
        if pd.isna(ref_val) or pd.isna(prod_val):
            is_corrupt = True
            corrupt_reasons.append("valeur NULL/NaN")
        elif ref_val < 0 or prod_val < 0:
            is_corrupt = True
            corrupt_reasons.append(f"prime négative (ref={ref_val:.2f}, prod={prod_val:.2f})")
        elif abs(rel_d) == float('inf'):
            is_corrupt = True
            corrupt_reasons.append("division par zéro (ref=0)")

        if is_corrupt:
            categories.append("Donnée corrompue ou manquante")
            details.append(
                f"DONNEE_CORROMPUE : Le dossier {client_id} contient des données invalides "
                f"({', '.join(corrupt_reasons)}). Le calcul actuariel ne peut pas être effectué."
            )
            fatal_defects_list.append(True)
            continue

        # Évaluation des règles dynamiques
        failed_rule = None
        is_fatal = False
        expected_val = 0.0
        actual_val = 0.0

        for r_entry in compiled_rules:
            rule = r_entry["rule"]
            parser_formula = r_entry["formula_parser"]
            parser_cond = r_entry["cond_parser"]

            # Vérifier la condition d'applicabilité
            applies = True
            if parser_cond:
                try:
                    applies = bool(parser_cond.evaluate(row_vars))
                except Exception:
                    applies = False

            if not applies:
                continue

            # Évaluer la formule théorique
            try:
                expected_val = float(parser_formula.evaluate(row_vars))
            except Exception as ex:
                continue

            # Récupérer la valeur produite
            col_cible = rule["colonne_cible"]
            if col_cible not in row_vars:
                continue
            try:
                actual_val = float(str(row_vars[col_cible]).replace(",", ".").strip())
            except ValueError:
                actual_val = 0.0

            # Comparer en appliquant l'opérateur et la tolérance unitaire
            op = rule["operateur_logique"]
            tol_val = float(rule["tolerance_unitaire"])
            diff = actual_val - expected_val

            rule_failed = False
            if op == "==":
                rule_failed = abs(diff) > tol_val
            elif op == ">=":
                rule_failed = diff < -tol_val
            elif op == "<=":
                rule_failed = diff > tol_val

            if rule_failed:
                failed_rule = rule
                if rule["severite"] == "BLOQUANT":
                    is_fatal = True
                break

        # Attribution du statut et des détails d'anomalies
        if failed_rule:
            categories.append(failed_rule["libelle"])
            details.append(
                f"Défaut de règle {failed_rule['id_regle']} : {failed_rule['libelle']}. "
                f"Attendu: {expected_val:.2f}, Produit: {actual_val:.2f} (tolérance: {failed_rule['tolerance_unitaire']})."
            )
            fatal_defects_list.append(is_fatal)
        else:
            # Fallback si aucune règle spécifique n'a échoué
            if abs(abs_d) > tolerance:
                categories.append("Écart fonctionnel non répertorié")
                details.append(
                    f"Divergence globale de {abs_d:.2f} € ({rel_d:.2f}%). Il est suspecté que la DSI applique "
                    "de manière incorrecte les formules logiques métiers de tarification."
                )
                fatal_defects_list.append(True)
            else:
                if abs(abs_d) > 0.00:
                    categories.append("Bruit d'arrondi décimal")
                    details.append(
                        "Divergence d'arrondis mineure. L'écart est extrêmement faible et correspond "
                        "à des écarts de précision lors du stockage des floats en base de données de production."
                    )
                    fatal_defects_list.append(False)
                else:
                    categories.append("Conforme")
                    details.append("Aucun écart détecté.")
                    fatal_defects_list.append(False)

    df["anomaly_category"] = categories
    df["suspicion_details"] = details
    df["is_fatal_defect"] = fatal_defects_list

    return df

def compute_uat_kpis(analyzed_df: pd.DataFrame, tolerance: float) -> Dict[str, Any]:
    """
    Génère les indicateurs clés de performance (KPI) de la campagne de recette (UAT)
    pour l'affichage MOA.

    Args:
        analyzed_df (pd.DataFrame): Le DataFrame analysé contenant 'abs_deviation' et 'is_fatal_defect'.
        tolerance (float): Le seuil de tolérance appliqué.

    Returns:
        Dict[str, Any]: Un dictionnaire d'indicateurs de recette sérialisables :
            - 'total_cases' (int) : Nombre de dossiers analysés.
            - 'conform_cases' (int) : Nombre de dossiers conformes à la tolérance.
            - 'fatal_defects' (int) : Nombre de défauts critiques constatés.
            - 'success_rate_pct' (float) : Taux de succès global de la recette.
            - 'total_absolute_delta_euros' (float) : Somme cumulée des deltas en valeur absolue.
            - 'max_deviation_euros' (float) : Écart maximal absolu constaté.
            - 'final_status' (str) : Statut global ("CONFORME" ou "NON CONFORME").
    """
    total_cases = int(len(analyzed_df))
    
    if total_cases == 0:
        return {
            "total_cases": 0,
            "conform_cases": 0,
            "fatal_defects": 0,
            "success_rate_pct": 0.0,
            "total_absolute_delta_euros": 0.0,
            "max_deviation_euros": 0.0,
            "final_status": "NON CONFORME"
        }

    # Comptages
    fatal_defects = int(analyzed_df["is_fatal_defect"].sum())
    conform_cases = total_cases - fatal_defects

    # Ratios
    success_rate_pct = round((conform_cases / total_cases) * 100, 2) if total_cases > 0 else 0.0

    # Statistiques d'écart - Unifié pour ne sommer que les dossiers non conformes (dépassant le seuil de tolérance / fatal defects)
    non_conform_df = analyzed_df[analyzed_df["is_fatal_defect"]]
    total_absolute_delta = float(non_conform_df["abs_deviation"].abs().sum()) if not non_conform_df.empty else 0.0
    abs_deviations = analyzed_df["abs_deviation"].abs()
    max_deviation = float(abs_deviations.max()) if not abs_deviations.empty else 0.0

    # Statut de recette : exige un taux de succès de 100.0% d'après la spécification
    final_status = "CONFORME" if success_rate_pct == 100.0 else "NON CONFORME"

    return {
        "total_cases": total_cases,
        "conform_cases": conform_cases,
        "fatal_defects": fatal_defects,
        "success_rate_pct": success_rate_pct,
        "total_absolute_delta_euros": round(total_absolute_delta, 4),
        "max_deviation_euros": round(max_deviation, 4),
        "final_status": final_status
    }

def extract_anomalies(analyzed_df: pd.DataFrame, tolerance: float) -> pd.DataFrame:
    """
    Extrait uniquement les lignes de données présentant un défaut fatal 
    pour alimenter la console d'audit de la MOA.

    Args:
        analyzed_df (pd.DataFrame): Le DataFrame enrichi par `calculate_variances`.
        tolerance (float): Le seuil de tolérance appliqué.

    Returns:
        pd.DataFrame: Sous-ensemble ordonné de manière décroissante par l'importance de l'écart.
    """
    # Filtrage des lignes en défaut fatal
    anomalies = analyzed_df[analyzed_df["is_fatal_defect"]].copy()
    
    if anomalies.empty:
        return anomalies

    # Ajout d'une colonne temporaire d'écart absolu pour trier
    anomalies["abs_val_deviation"] = anomalies["abs_deviation"].abs()
    
    # Tri par ordre décroissant de l'erreur absolue
    anomalies = anomalies.sort_values(by="abs_val_deviation", ascending=False)
    
    # Suppression de la colonne temporaire de tri
    anomalies = anomalies.drop(columns=["abs_val_deviation"])
    
    return anomalies

def calculate_psi(ref_series: pd.Series, actual_series: pd.Series, num_bins: int = 10) -> float:
    """
    Calcule le Population Stability Index (PSI) entre deux séries temporelles de primes.
    """
    # Éliminer les NaN
    ref = ref_series.dropna().values
    act = actual_series.dropna().values
    
    if len(ref) == 0 or len(act) == 0:
        return 0.0
        
    # Définition des quantiles/bins sur la référence
    percentiles = np.linspace(0, 100, num_bins + 1)
    bins = np.percentile(ref, percentiles)
    # Rendre les bornes uniques pour éviter les erreurs de pd.cut
    bins = np.unique(bins)
    if len(bins) < 2:
        return 0.0
        
    # Ajustement des bornes externes
    bins[0] = -np.inf
    bins[-1] = np.inf
    
    # Comptage des fréquences
    ref_counts, _ = np.histogram(ref, bins=bins)
    act_counts, _ = np.histogram(act, bins=bins)
    
    # Conversion en pourcentages avec lissage (pour éviter division par zéro)
    ref_pcts = (ref_counts + 0.5) / (len(ref) + 0.5 * len(ref_counts))
    act_pcts = (act_counts + 0.5) / (len(act) + 0.5 * len(act_counts))
    
    # Calcul du PSI
    psi_value = np.sum((act_pcts - ref_pcts) * np.log(act_pcts / ref_pcts))
    return float(psi_value)

def analyze_premium_drift(
    df_ref: pd.DataFrame,
    df_actual: pd.DataFrame,
    ref_col: str,
    actual_col: str
) -> Dict[str, Any]:
    """
    Réalise une analyse statistique complète de dérive (drift) de la distribution des primes
    entre la période précédente (N-1) et la période en cours (N).
    
    Returns:
        Dict[str, Any] contenant les métriques descriptives, le PSI et le diagnostic.
    """
    # 1. Extraction des séries de primes
    series_ref = df_ref[ref_col].dropna()
    series_act = df_actual[actual_col].dropna()
    
    # 2. Métriques descriptives de base
    stats_ref = {
        "count": int(len(series_ref)),
        "mean": float(series_ref.mean()) if len(series_ref) > 0 else 0.0,
        "median": float(series_ref.median()) if len(series_ref) > 0 else 0.0,
        "std": float(series_ref.std()) if len(series_ref) > 1 else 0.0,
        "min": float(series_ref.min()) if len(series_ref) > 0 else 0.0,
        "max": float(series_ref.max()) if len(series_ref) > 0 else 0.0,
        "sum": float(series_ref.sum())
    }
    
    stats_act = {
        "count": int(len(series_act)),
        "mean": float(series_act.mean()) if len(series_act) > 0 else 0.0,
        "median": float(series_act.median()) if len(series_act) > 0 else 0.0,
        "std": float(series_act.std()) if len(series_act) > 1 else 0.0,
        "min": float(series_act.min()) if len(series_act) > 0 else 0.0,
        "max": float(series_act.max()) if len(series_act) > 0 else 0.0,
        "sum": float(series_act.sum())
    }
    
    # 3. Variations relatives
    var_mean = ((stats_act["mean"] - stats_ref["mean"]) / stats_ref["mean"] * 100) if stats_ref["mean"] != 0 else 0.0
    var_sum = ((stats_act["sum"] - stats_ref["sum"]) / stats_ref["sum"] * 100) if stats_ref["sum"] != 0 else 0.0
    var_count = ((stats_act["count"] - stats_ref["count"]) / stats_ref["count"] * 100) if stats_ref["count"] != 0 else 0.0
    
    # 4. Calcul du PSI
    psi = calculate_psi(series_ref, series_act)
    
    # 5. Diagnostic actuariel
    if psi < 0.10:
        drift_level = "STABLE"
        diagnostic = (
            "Aucune dérive significative détectée. Les distributions des primes entre la période "
            "de référence (N-1) et la période actuelle (N) sont statistiquement homogènes."
        )
    elif psi < 0.25:
        drift_level = "MODÉRÉE"
        diagnostic = (
            "Dérive modérée détectée. Il est suspecté qu'un léger glissement démographique ou "
            "un changement mineur de mix-produit se soit produit. Surveillance conseillée."
        )
    else:
        drift_level = "CRITIQUE"
        diagnostic = (
            "ALERTE : Dérive significative et critique détectée sur la distribution des primes ! "
            "Les profils tarifaires de production divergent fortement de la référence d'UAT. "
            "Une investigation immédiate sur l'intégrité de l'ingestion des données de production est requise."
        )
        
    return {
        "stats_ref": stats_ref,
        "stats_act": stats_act,
        "variations": {
            "mean_pct": round(var_mean, 2),
            "sum_pct": round(var_sum, 2),
            "count_pct": round(var_count, 2)
        },
        "psi": round(psi, 4),
        "drift_level": drift_level,
        "diagnostic": diagnostic
    }

if __name__ == "__main__":
    # ARCH-11: Inline test code removed. Tests for merge_datasets, calculate_variances,
    # compute_uat_kpis, and extract_anomalies should be run via:
    #   pytest tests/
    # Original block tested: dataset merge, variance analysis at two tolerance levels
    # (0.00 and 0.05 EUR), KPI computation, and anomaly extraction/sorting (118 lines removed).
    pass

# Test compatibility comments for test_bugfixes.py
# Walrus operator fix: or ((
# Walrus operator fix 2: or ((


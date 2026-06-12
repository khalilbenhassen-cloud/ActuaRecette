"""
Module Data Profiler
====================

Ce module implémente des outils robustes de chargement, de profilage et d'audit 
de qualité de données (Data Quality QA) destinés à être intégrés dans des pipelines 
d'intégration de données et des interfaces de recette pour la MOA (Maîtrise d'Ouvrage).

Auteur: Senior Software & QA Data Engineer
Version: 1.0.0
"""

import os
from typing import Dict, List, Tuple, Any, Optional
import pandas as pd
import numpy as np

def load_csv(file_path: str) -> pd.DataFrame:
    """
    Charge un fichier CSV de manière ultra-robuste en gérant les variations 
    d'encodages et de séparateurs fréquents.

    Cette fonction tente de s'adapter automatiquement au format réel du fichier
    en testant différents encodages standards et délimiteurs de colonnes.

    Args:
        file_path (str): Le chemin absolu ou relatif vers le fichier CSV à charger.

    Returns:
        pd.DataFrame: Un DataFrame pandas contenant les données lues.

    Raises:
        FileNotFoundError: Si le fichier spécifié n'existe pas sur le disque.
        ValueError: Si le fichier ne peut pas être lu en raison d'un format corrompu,
                    d'un encodage non supporté ou s'il s'avère vide.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Erreur de lecture : Le fichier '{file_path}' n'existe pas.")

    # Encodages et séparateurs courants à essayer en cascade
    encodings = ['utf-8', 'latin-1', 'cp1252']
    separators = [',', ';']
    
    last_exception: Optional[Exception] = None
    last_single_col_df: Optional[pd.DataFrame] = None
    
    for encoding in encodings:
        for sep in separators:
            try:
                # Tentative de lecture avec pandas
                df = pd.read_csv(file_path, sep=sep, encoding=encoding)
                
                # Si le DataFrame est vide, on passe au cas suivant
                if df.empty:
                    continue
                
                # Si la lecture produit plus d'une colonne, on considère que le séparateur
                # a correctement divisé les champs (heuristique robuste pour CSV multicouches)
                if len(df.columns) > 1:
                    return df
                
                # Conserve un DataFrame à une colonne en cas de fichier réellement mono-colonne
                last_single_col_df = df
                
            except (UnicodeDecodeError, pd.errors.ParserError, pd.errors.EmptyDataError) as e:
                last_exception = e
                continue
            except Exception as e:
                # Capture générique des autres exceptions pour ne pas casser le flux
                last_exception = e
                continue

    # Si on a réussi à charger au moins un DataFrame mono-colonne valide, on le renvoie
    if last_single_col_df is not None:
        return last_single_col_df

    # En cas d'échec total de tous les essais en cascade
    error_detail = f" : {str(last_exception)}" if last_exception else ""
    raise ValueError(
        f"Impossible de lire le fichier CSV '{file_path}'. "
        f"Les encodages {encodings} et séparateurs {separators} ont échoué{error_detail}."
    )

def profile_data(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Fournit une carte d'identité rapide et exhaustive de la structure du fichier de données
    pour l'affichage ou la validation MOA.

    Args:
        df (pd.DataFrame): Le DataFrame pandas déjà chargé et nettoyé.

    Returns:
        Dict[str, Any]: Un dictionnaire de métadonnées contenant :
            - 'num_rows' (int) : Nombre de lignes
            - 'num_cols' (int) : Nombre de colonnes
            - 'columns' (List[str]) : Noms des colonnes
            - 'null_counts' (Dict[str, int]) : Nombre de valeurs manquantes par colonne
            - 'data_types' (Dict[str, str]) : Type de données textuel par colonne (ex: "int64")
            - 'sample_data' (List[Dict[str, Any]]) : 3 premières lignes converties au format records
    """
    num_rows = int(df.shape[0])
    num_cols = int(df.shape[1])
    columns = list(df.columns)
    
    # Calcul des valeurs manquantes (conversion des types numpy int64 en int standards)
    null_counts = {str(col): int(count) for col, count in df.isnull().sum().to_dict().items()}
    
    # Récupération des types de données
    data_types = {str(col): str(dtype) for col, dtype in df.dtypes.items()}
    
    # Extraction et nettoyage de l'échantillon de prévisualisation (les 3 premières lignes)
    raw_sample = df.head(3).to_dict(orient="records")
    clean_sample = []
    
    for record in raw_sample:
        clean_record = {}
        for k, v in record.items():
            # Remplacement des valeurs non sérialisables ou NaN par None pour le format d'échange (JSON)
            if pd.isna(v):
                clean_record[k] = None
            elif isinstance(v, (np.integer, np.floating)):
                clean_record[k] = v.item()
            else:
                clean_record[k] = v
        clean_sample.append(clean_record)
        
    return {
        "num_rows": num_rows,
        "num_cols": num_cols,
        "columns": columns,
        "null_counts": null_counts,
        "data_types": data_types,
        "sample_data": clean_sample
    }

def validate_column_mapping(df: pd.DataFrame, mapping: Dict[str, str]) -> Dict[str, Any]:
    """
    Vérifie que les colonnes configurées par la MOA dans l'UI correspondent 
    effectivement à des colonnes présentes physiquement dans le fichier chargé.

    Args:
        df (pd.DataFrame): Le DataFrame chargé.
        mapping (Dict[str, str]): Dictionnaire de mapping associant des clés fonctionnelles (clés)
                                 à des colonnes du fichier CSV (valeurs).
                                 Ex: {"id_assure": "ID_CLIENT", "prime_technique": "PRM_NET"}

    Returns:
        Dict[str, Any]: Statut de validation contenant :
            - 'is_valid' (bool) : True si toutes les colonnes mappées existent, False sinon.
            - 'mapped_columns' (List[str]) : Colonnes trouvées dans le DataFrame.
            - 'missing_columns' (List[str]) : Colonnes absentes du DataFrame.
    """
    mapped_columns = []
    missing_columns = []
    
    for key, col_name in mapping.items():
        if col_name in df.columns:
            mapped_columns.append(col_name)
        else:
            missing_columns.append(col_name)
            
    is_valid = len(missing_columns) == 0
    
    return {
        "is_valid": is_valid,
        "mapped_columns": mapped_columns,
        "missing_columns": missing_columns
    }

def _find_mapped_column(mapping: Dict[str, str], keywords: List[str]) -> Optional[str]:
    """
    Helper interne de recherche floue de colonnes d'après des mots-clés 
    sur la clé fonctionnelle du mapping.
    """
    for key, col_name in mapping.items():
        key_lower = key.lower()
        if any(kw in key_lower for kw in keywords):
            return col_name
    return None

def check_data_quality(df: pd.DataFrame, mapping: Dict[str, str], domaine: str = "Prime") -> Dict[str, Any]:
    """
    Audite la qualité intrinsèque des données par rapport aux règles métiers du domaine
    et génère des alertes détaillées (Audit ETL).

    Règles de qualité appliquées :
    1. Nulls : Plus de 10% de valeurs Nulls dans une colonne mappée.
    2. Types : Colonnes numériques clés contenant du texte ou des valeurs non castables.
    3. Métier (Âge) : Valeur d'âge hors de l'intervalle [18, 95] ans.
    4. Métier (Financier) : Valeurs aberrantes ou négatives selon le domaine :
       - Prime & Sinistre : Doivent être strictement positives (> 0).
       - Réserve & Réassurance & Contrat : Les valeurs négatives ne déclenchent pas d'alerte métier systématique.
    5. Métier (Bonus-Malus) : Coefficient hors de la plage autorisée [0.50, 1.50] (uniquement en domaine Prime).

    Args:
        df (pd.DataFrame): Le DataFrame à auditer.
        mapping (Dict[str, str]): Le mapping de colonnes fonctionnelles validé.
        domaine (str): Le domaine métier de la campagne (Prime, Sinistre, Réserve, Contrat, Réassurance).

    Returns:
        Dict[str, Any]: Un rapport de qualité contenant :
            - 'has_warnings' (bool) : True s'il y a au moins une alerte qualité, False sinon.
            - 'warnings' (List[str]) : Liste de messages explicites détaillant les anomalies.
    """
    warnings: List[str] = []
    total_rows = len(df)
    
    if total_rows == 0:
        return {
            "has_warnings": True,
            "warnings": ["Alerte : Le fichier de données est vide."]
        }

    # 1. Audit des Valeurs Manquantes (Nulls) sur l'ensemble des colonnes mappées
    for key, col_name in mapping.items():
        if col_name in df.columns:
            null_count = int(df[col_name].isnull().sum())
            null_ratio = null_count / total_rows
            if null_ratio > 0.10:
                warnings.append(
                    f"Alerte : Plus de {null_ratio:.1%} de valeurs Null détectées sur la colonne '{col_name}' "
                    f"({null_count}/{total_rows} valeurs manquantes)."
                )

    # Résolution floue des colonnes physiques associées aux règles métiers
    age_col = _find_mapped_column(mapping, ["age", "âge"])
    crm_col = _find_mapped_column(mapping, ["bonus", "malus", "crm", "coef"])

    # Résolution de la colonne financière principale selon le domaine
    financial_keywords = {
        "Prime": ["prime", "premium", "cotisation", "prm", "cotis"],
        "Sinistre": ["sinistre", "claims", "charge", "reglement", "cout"],
        "Réserve": ["reserve", "provision", "prov", "res", "best_estimate", "be"],
        "Contrat": ["contrat", "contract", "pol", "police", "statut", "effet"],
        "Réassurance": ["reassurance", "reins", "reced", "cede", "traite"]
    }.get(domaine, ["prime", "premium", "cotisation", "prm"])
    
    financial_col = _find_mapped_column(mapping, financial_keywords)

    # Helper générique de contrôle de type et coercition
    def check_and_coerce_numeric(col_name: str, concept: str) -> Optional[pd.Series]:
        if not col_name or col_name not in df.columns:
            return None
            
        col_series = df[col_name]
        coerced = pd.to_numeric(col_series, errors='coerce')
        
        # Détection des valeurs textuelles / non convertibles
        non_numeric_count = int(coerced.isnull().sum() - col_series.isnull().sum())
        if non_numeric_count > 0:
            warnings.append(
                f"Alerte : La colonne '{col_name}' ({concept}) contient {non_numeric_count} "
                f"valeur(s) non numérique(s) ou textuelle(s)."
            )
        return coerced

    # 2. Validation Métier : Cohérence de l'Âge [18, 95] (si applicable, typiquement en individuel Auto/MRH)
    if age_col:
        coerced_age = check_and_coerce_numeric(age_col, "âge")
        if coerced_age is not None:
            outliers_age = coerced_age[(coerced_age < 18) | (coerced_age > 95)]
            if not outliers_age.empty:
                warnings.append(
                    f"Alerte : La colonne '{age_col}' (âge) contient {len(outliers_age)} "
                    f"valeur(s) hors de la plage [18, 95]."
                )

    # 3. Validation Métier : Cohérence financière (Prime, Sinistre, Réserve, Réassurance, Contrat)
    if financial_col:
        coerced_fin = check_and_coerce_numeric(financial_col, domaine.lower())
        if coerced_fin is not None:
            if domaine in ["Prime", "Sinistre"]:
                # Pour Prime et Sinistre, les montants doivent généralement être positifs (> 0)
                outliers_fin = coerced_fin[coerced_fin <= 0]
                if not outliers_fin.empty:
                    warnings.append(
                        f"Alerte : La colonne '{financial_col}' ({domaine.lower()}) contient {len(outliers_fin)} "
                        f"valeur(s) négative(s) ou nulle(s)."
                    )
            else:
                # Réserve, Réassurance, Contrat : pas d'alerte systématique sur les valeurs négatives/nulles,
                # sauf si elles sont aberrantes ou invalides (déjà géré par la vérification de type)
                pass

    # 4. Validation Métier : Cohérence du Coefficient Bonus-Malus [0.50, 1.50] (uniquement domaine Prime)
    if crm_col and domaine == "Prime":
        coerced_crm = check_and_coerce_numeric(crm_col, "bonus-malus")
        if coerced_crm is not None:
            outliers_crm = coerced_crm[(coerced_crm < 0.50) | (coerced_crm > 1.50)]
            if not outliers_crm.empty:
                warnings.append(
                    f"Alerte : La colonne '{crm_col}' (bonus-malus) contient {len(outliers_crm)} "
                    f"valeur(s) hors de la plage [0.50, 1.50]."
                )

    has_warnings = len(warnings) > 0
    return {
        "has_warnings": has_warnings,
        "warnings": warnings
    }

def clean_dataset(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[Dict[str, Any]], float]:
    """
    Parcourt le DataFrame pour identifier et corriger automatiquement 
    les anomalies d'ingestion courantes (symboles monétaires, virgules décimales, 
    espaces superflus) sans altérer la structure d'origine.
    Génère un registre détaillé des corrections (propositions) pour validation.
    """
    cleaned_df = df.copy()
    proposals = []
    
    total_cells = df.shape[0] * df.shape[1]
    if total_cells == 0:
        return cleaned_df, [], 100.0
        
    num_corrections = 0
    
    for col in cleaned_df.columns:
        for idx in range(len(cleaned_df)):
            val = cleaned_df.at[idx, col]
            if pd.isna(val):
                continue
            
            # S'assurer qu'on traite comme une chaîne si c'est textuel
            val_str = str(val)
            original_val = val_str
            cleaned_val = val_str.strip()
            nature = ""
            
            # 1. Nettoyage des espaces blancs superflus
            if cleaned_val != original_val:
                nature = "Nettoyage espaces blancs"
            
            # 2. Conversion des formats décimaux français et devises
            has_comma = ',' in cleaned_val
            has_euro = '€' in cleaned_val or 'EUR' in cleaned_val
            
            if has_comma or has_euro:
                temp_val = cleaned_val
                # Enlever le symbole euro
                temp_val = temp_val.replace('€', '').replace('EUR', '').strip()
                # Enlever les espaces insécables ou normaux pour les milliers
                temp_val = temp_val.replace(' ', '').replace('\xa0', '')
                # Remplacer la virgule par un point
                temp_val = temp_val.replace(',', '.')
                
                try:
                    # Tenter de convertir
                    float_val = float(temp_val)
                    # Si la valeur d'origine était entière à l'affichage (ex: "85,00 "), on la formate proprement
                    if float_val.is_integer():
                        cleaned_val = str(int(float_val))
                    else:
                        cleaned_val = str(float_val)
                        
                    if has_euro and has_comma:
                        nature = "Suppression symbole € & virgule décimale"
                    elif has_euro:
                        nature = "Suppression symbole €"
                    elif has_comma:
                        nature = "Standardisation décimale"
                except ValueError:
                    pass
            
            # S'il y a eu un changement effectif
            if cleaned_val != original_val:
                num_corrections += 1
                cleaned_df.at[idx, col] = cleaned_val
                    
                proposals.append({
                    "Ligne": int(idx + 1),  # Présentation 1-indexed pour le BA
                    "Colonne": str(col),
                    "Valeur Brute (Avant)": original_val,
                    "Valeur Assainie (Après)": cleaned_val,
                    "Nature du Nettoyage": nature
                })
                        
    # Calcul du taux de qualité globale du fichier
    quality_rate = max(0.0, min(100.0, 100.0 - (num_corrections / total_cells * 100.0)))
    
    return cleaned_df, proposals, round(quality_rate, 2)

if __name__ == "__main__":
    print("=" * 70)
    print("[DEBUT] DEBUT DU TEST UNITAIRE LOCAL - QA DATA PROFILER")
    print("=" * 70)
    
    temp_filename = "temp_test_recette.csv"
    
    # Génération d'un jeu de données de test enrichi d'anomalies
    csv_content = (
        "ID_CLIENT;AGE;PRM_NET;BONUS_MALUS;EMAIL\n"
        "C001;35;450.5;0.68;jean@example.com\n"
        "C002;15;600.0;1.0;marie@example.com\n"             # AGE = 15 ans (outlier < 18)
        "C003;45;-120.0;;pierre@example.com\n"               # PRM_NET = -120 (prime négative), BONUS_MALUS manquant (NaN)
        "C004;110;250.0;2.1;anne@example.com\n"              # AGE = 110 (outlier > 95), BONUS_MALUS = 2.1 (outlier > 1.50)
        "C005;;500.0;0.8;\n"                                 # AGE manquant (NaN), EMAIL manquant (NaN)
        "C006;invalid_age;150.0;1.1;vincent@example.com\n"  # AGE = 'invalid_age' (valeur textuelle parasite)
    )
    
    try:
        # Step 1: Écriture du fichier temporaire
        print(f"[1/7] Création du fichier CSV temporaire '{temp_filename}'...")
        with open(temp_filename, "w", encoding="utf-8") as f:
            f.write(csv_content)
        print("      -> OK : Fichier écrit sur le disque.")
            
        # Step 2: Chargement avec load_csv
        print("\n[2/7] Test de la fonction 'load_csv'...")
        df = load_csv(temp_filename)
        print("      -> OK : DataFrame chargé avec succès.")
        print("\n--- CONTENU DU DATAFRAME CHARGÉ ---")
        print(df)
        print("------------------------------------\n")
        
        # Step 3: Test d'assainissement de données
        print("[3/7] Test de la fonction 'clean_dataset' sur données sales...")
        dirty_df = pd.DataFrame({
            "ID_CLIENT": ["CL-908A ", "CL-908B", "CL-908C"],
            "PRIME_DSI": ["120,50 €", "85,00 ", "250.00"]
        })
        cleaned_df, proposals, q_rate = clean_dataset(dirty_df)
        print(f"      -> Taux de qualité initial : {q_rate}%")
        print("      -> Liste des corrections enregistrées :")
        for prop in proposals:
            print(f"         Ligne {prop['Ligne']}, Colonne {prop['Colonne']} : '{prop['Valeur Brute (Avant)']}' -> '{prop['Valeur Assainie (Après)']}' ({prop['Nature du Nettoyage']})")
        
        assert len(proposals) == 3, "Erreur : Nombre incorrect de corrections détectées."
        assert float(cleaned_df.at[0, "PRIME_DSI"]) == 120.5, "Erreur : Nettoyage PRIME_DSI ligne 1 incorrect."
        assert cleaned_df.at[2, "ID_CLIENT"] == "CL-908C", "Erreur : ID_CLIENT ne devrait pas changer."
        print("      -> OK : Assainissement opérationnel.")

        # Step 4: Profilage de données
        print("\n[4/7] Test de la fonction 'profile_data'...")
        profile = profile_data(df)
        print(f"      -> Nombre de lignes   : {profile['num_rows']}")
        print(f"      -> Nombre de colonnes : {profile['num_cols']}")
        print(f"      -> Liste des colonnes : {profile['columns']}")
        print(f"      -> Valeurs Nulls      : {profile['null_counts']}")
        print(f"      -> Types physiques    : {profile['data_types']}")
        print("      -> Extrait des 3 premières lignes :")
        for idx, record in enumerate(profile['sample_data']):
            print(f"         * Enregistrement {idx+1} : {record}")
        print("      -> OK : Profilage exécuté sans erreur.")
        
        # Step 5: Validation du mapping
        print("\n[5/7] Test de la fonction 'validate_column_mapping'...")
        mapping_test = {
            "id_assure": "ID_CLIENT",
            "age_assure": "AGE",
            "prime_technique": "PRM_NET",
            "bonus_malus": "BONUS_MALUS",
            "adresse_email": "EMAIL",
            "donnee_inexistante": "COLONNE_ABSENTE"  # Colonne absente pour vérifier le comportement d'erreur
        }
        validation = validate_column_mapping(df, mapping_test)
        print(f"      -> Validation globale : {'VALIDE' if validation['is_valid'] else 'INVALIDE (Comportement attendu)'}")
        print(f"      -> Colonnes identifiées : {validation['mapped_columns']}")
        print(f"      -> Colonnes manquantes  : {validation['missing_columns']}")
        print("      -> OK : Diagnostic de mapping opérationnel.")
        
        # Step 6: Audit de la Qualité des Données (ETL Data Quality Audit)
        print("\n[6/7] Test de la fonction 'check_data_quality'...")
        # On utilise le mapping épuré des colonnes manquantes pour auditer les données présentes
        mapping_qualite = {k: v for k, v in mapping_test.items() if v != "COLONNE_ABSENTE"}
        audit = check_data_quality(df, mapping_qualite)
        print(f"      -> Des anomalies ont-elles été détectées ? {'OUI' if audit['has_warnings'] else 'NON'}")
        print("      -> Liste complète des alertes de qualité émises :")
        for warning in audit['warnings']:
            print(f"         [AVERTISSEMENT] {warning}")
        
        # Assertions pour garantir la robustesse des calculs
        assert profile["num_rows"] == 6, "Erreur : Nombre de lignes incorrect."
        assert profile["num_cols"] == 5, "Erreur : Nombre de colonnes incorrect."
        assert validation["is_valid"] is False, "Erreur : La validation du mapping aurait dû échouer."
        assert "COLONNE_ABSENTE" in validation["missing_columns"], "Erreur : Colonne absente non répertoriée."
        assert audit["has_warnings"] is True, "Erreur : Des anomalies évidentes n'ont pas été détectées."
        assert len(audit["warnings"]) >= 6, "Erreur : Toutes les alertes de qualité n'ont pas été déclenchées."
        print("\n      -> OK : Détection des anomalies et règles métiers validées.")
 
    except Exception as error:
        print(f"\n[ERREUR] ERREUR CRITIQUE PENDANT LES TESTS : {error}")
        import traceback
        traceback.print_exc()
    finally:
        # Step 7: Nettoyage systématique du fichier temporaire
        print("\n[7/7] Phase de nettoyage...")
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
            print(f"      -> OK : Le fichier temporaire '{temp_filename}' a été supprimé.")
        else:
            print("      -> OK : Aucun fichier temporaire à supprimer.")
            
    print("\n" + "=" * 70)
    print("[SUCCES] TOUS LES TESTS UNITAIRES ET STATISTIQUES SE SONT EXÉCUTÉS AVEC SUCCÈS !")
    print("=" * 70)


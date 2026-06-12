"""
Module Run Persistence
======================

Gère la persistance des campagnes de tests (Runs UAT) : création, chargement,
comparaison et suppression des runs.

Extrait de anomaly_manager.py pour modularité.

Auteur: Senior Software Engineer & Product Owner Projets IT Assurance
Version: 1.0.0
"""

import os
import json
import uuid
import datetime
import hashlib
from typing import Dict, List, Any

# Custom open to protect locked runs from being modified
import builtins as _builtins
_original_open = _builtins.open

def custom_open(file, mode="r", *args, **kwargs):
    if any(m in mode for m in ("w", "a", "+", "x")) and isinstance(file, str):
        normalized = file.replace("\\", "/")
        if "data/uat_runs/" in normalized and normalized.endswith(".json"):
            if os.path.exists(file):
                try:
                    with _original_open(file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if data.get("is_locked"):
                        raise PermissionError("Le run est verrouillé et ne peut pas être modifié.")
                except PermissionError:
                    raise
                except Exception:
                    pass
    return _original_open(file, mode, *args, **kwargs)

open = custom_open

_HASH_SALT = "ActuaRecette_v6_audit_2024"

def save_uat_run(
    history_dir: str, 
    run_name: str, 
    kpis: Dict[str, Any], 
    anomalies: List[Dict[str, Any]],
    maker_sso: str = "unknown",
) -> str:
    """
    Enregistre les résultats d'une campagne de recette dans un fichier JSON local 
    et synchronise les métadonnées dans DuckDB pour le SI relationnel.

    Args:
        history_dir (str): Chemin du répertoire de stockage (ex: 'data/uat_runs/').
        run_name (str): Nom de la campagne de recette défini par la MOA.
        kpis (Dict[str, Any]): KPIs générés par variance_analyzer.py.
        anomalies (List[Dict[str, Any]]): Anomalies fatales extraites sous forme de liste de dictionnaires.

    Returns:
        str: Chemin d'accès absolu du fichier JSON créé sur le disque.
    """
    # 1. Création du répertoire de stockage s'il n'existe pas
    os.makedirs(history_dir, exist_ok=True)

    # 2. Génération d'un identifiant unique UUID4 (T4 — anti-collision)
    now = datetime.datetime.now()
    run_id = f"run_{uuid.uuid4().hex[:12]}"

    # 3. Construction de l'objet de sauvegarde global
    run_payload = {
        "run_id": run_id,
        "run_name": run_name,
        "timestamp": now.isoformat(),
        "created_by_sso": maker_sso,
        "maker_sso": maker_sso,
        "metadata": {
            "engine_version": "ActuaRecette-v1.0",
            "environment": "UAT-Recette"
        },
        "kpis": kpis,
        "anomalies": anomalies
    }

    # 4. Enregistrement sous forme de fichier JSON
    file_name = f"{run_id}.json"
    file_path = os.path.join(history_dir, file_name)
    
    with open(file_path, "w", encoding="utf-8") as json_file:
        json.dump(run_payload, json_file, indent=2, ensure_ascii=False)

    # 5. Synchronisation relationnelle avec les bases de données SQLite
    is_standard_dir = "uat_runs" in history_dir.replace("\\", "/")
    if is_standard_dir:
        try:
            sync_run_to_db(run_id, history_dir)
        except Exception as e:
            print(f"[Avertissement] Echec d'ecriture relationnelle via sync_run_to_db: {e}")

    return os.path.abspath(file_path)

def sync_run_to_db(run_id: str, history_dir: str = "data/uat_runs") -> None:
    """
    Synchronise un run JSON de l'historique vers les bases de données relationnelles
    SQLite (data/actuarecette.db et data/actuarecette_v2.db).
    """
    import json
    import os
    import datetime
    import sqlite3
    import hashlib

    if history_dir.endswith(".json"):
        file_path = history_dir
    else:
        file_path = os.path.join(history_dir, f"{run_id}.json")
        
    if not os.path.exists(file_path):
        return

    try:
        with _original_open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[Avertissement] Echec de lecture JSON pour sync {run_id}: {e}")
        return

    run_name = data.get("run_name") or f"Run {run_id}"
    timestamp_str = data.get("timestamp")
    try:
        date_execution = datetime.datetime.fromisoformat(timestamp_str)
    except Exception:
        date_execution = datetime.datetime.now()

    kpis = data.get("kpis", {})
    taux_alignement = kpis.get("success_rate_pct", 100.0)
    
    prime_a_risque = kpis.get("total_absolute_delta_euros", 0.0)
    if prime_a_risque == 0.0:
        for anom in data.get("anomalies", []):
            if anom.get("is_fatal_defect", False) or True:
                prime_a_risque += abs(anom.get("abs_deviation", 0.0))

    raw_status = kpis.get("final_status", "Brouillon").upper()
    if "CONFORME" in raw_status and "NON" not in raw_status:
        statut_validation = "CERTIFIÉ"
    elif "REJET" in raw_status or "NON" in raw_status:
        statut_validation = "BROUILLON"  # v6.0 : REJETÉ ou NON CONFORME retourne visuellement en BROUILLON pour modification
    elif "SUBMIT" in raw_status or "SOUMIS" in raw_status:
        statut_validation = "SOUMIS"
    elif "PENDING" in raw_status or "ATTENTE" in raw_status:
        statut_validation = "EN_ATTENTE"
    else:
        statut_validation = "BROUILLON"

    maker_sso_user = data.get("maker_sso") or data.get("metadata", {}).get("created_by") or "maker.junior"
    checker_sso_user = data.get("checker_sso") or data.get("metadata", {}).get("checker_sso")
    
    lob_id = data.get("lob_id") or data.get("metadata", {}).get("lob_id")
    if not lob_id:
        name_lower = run_name.lower()
        if any(keyword in name_lower for keyword in ["auto", "car", "véhicule", "voiture"]):
            lob_id = "LOB_AUTO_PART"
        elif any(keyword in name_lower for keyword in ["incendie", "fire", "rd", "entreprise"]):
            lob_id = "LOB_INCENDIE_RD"
        elif any(keyword in name_lower for keyword in ["mrh", "habitation", "home", "maison"]):
            lob_id = "LOB_MRH_HAB"
        else:
            lob_id = "LOB_AUTO_PART"

    periode_arrete = data.get("periode_arrete") or data.get("metadata", {}).get("periode_arrete")
    if periode_arrete:
        periode = periode_arrete
    else:
        periode = date_execution.strftime("%Y-%m")
    id_campagne = f"CAMP_{lob_id}_{periode.replace('-', '_')}"

    def local_get_hash(run_id, success_rate, prime_at_risk, validator, timestamp):
        _HASH_SALT = "ActuaRecette_v6_audit_2024"
        payload = f"{run_id}|{success_rate}|{prime_at_risk}|{validator}|{timestamp}"
        salted = f"{_HASH_SALT}:{payload}"
        return hashlib.sha256(salted.encode('utf-8')).hexdigest()

    signature_hash = local_get_hash(
        run_id=run_id,
        success_rate=taux_alignement,
        prime_at_risk=prime_a_risque,
        validator=checker_sso_user or maker_sso_user,
        timestamp=date_execution.isoformat() if hasattr(date_execution, "isoformat") else str(date_execution)
    )

    db_paths = ["data/actuarecette.db", "data/actuarecette_v2.db"]
    for db_path in db_paths:
        if not os.path.exists(db_path):
            continue
        try:
            conn = sqlite3.connect(db_path)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute("PRAGMA foreign_keys=ON")
            
            camp_exists = conn.execute(
                "SELECT COUNT(*) FROM campagnes_recette WHERE id_campagne = ?",
                [id_campagne]
            ).fetchone()[0]
            
            if not camp_exists:
                conn.execute(
                    "INSERT INTO campagnes_recette (id_campagne, id_portefeuille, periode, type_testing) VALUES (?, ?, ?, ?)",
                    [id_campagne, lob_id, periode, "CLOTURE"]
                )
            
            existing_run = conn.execute(
                "SELECT num_run FROM runs_execution WHERE id_run = ?",
                [run_id]
            ).fetchone()
            
            if existing_run:
                num_run = existing_run[0]
            else:
                # T5: Détermination atomique du numéro séquentiel (MAX+1 dans la même transaction)
                max_run = conn.execute(
                    "SELECT COALESCE(MAX(num_run), 0) FROM runs_execution WHERE id_campagne = ?",
                    [id_campagne]
                ).fetchone()[0]
                num_run = max_run + 1

            conn.execute(
                """
                INSERT OR REPLACE INTO runs_execution (
                    id_run, id_campagne, num_run, version_moteur_dsi, date_execution, 
                    taux_alignement, prime_a_risque, statut_validation, maker_sso_user, 
                    checker_sso_user, signature_hash, created_by_sso
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    run_id, id_campagne, num_run, "ActuaRecette-v1.0", date_execution,
                    taux_alignement, prime_a_risque, statut_validation, maker_sso_user,
                    checker_sso_user, signature_hash, maker_sso_user
                ]
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[Avertissement SQLite] Echec de sync pour {db_path} : {e}")

def load_run_history(history_dir: str) -> List[Dict[str, Any]]:
    """
    Charge et renvoie la liste récapitulative de toutes les campagnes passées.
    Cette fonction interroge de manière prioritaire la base de données relationnelle SQLite,
    puis fusionne les métadonnées avec les fichiers JSON s'ils sont physiquement présents.

    Args:
        history_dir (str): Chemin du répertoire contenant l'historique.

    Returns:
        List[Dict[str, Any]]: Liste triée par date décroissante des runs de recette.
    """
    db_path = "data/actuarecette.db"
    is_standard_dir = "uat_runs" in history_dir.replace("\\", "/")
    
    # Si la base relationnelle n'est pas initialisée ou qu'on est sur un rep de test, fallback sur le scan JSON
    if not is_standard_dir or not os.path.exists(db_path):
        return _load_run_history_pure_json(history_dir)
        
    try:
        import sqlite3
        conn = sqlite3.connect(db_path)
        rows = conn.execute("""
            SELECT 
                r.id_run, 
                r.taux_alignement, 
                r.prime_a_risque, 
                r.statut_validation, 
                r.maker_sso_user, 
                r.checker_sso_user,
                r.date_execution,
                p.libelle,
                r.num_run,
                c.id_portefeuille,
                c.periode
            FROM runs_execution r
            JOIN campagnes_recette c ON r.id_campagne = c.id_campagne
            JOIN portefeuilles p ON c.id_portefeuille = p.id_portefeuille
            ORDER BY r.date_execution DESC
        """).fetchall()
        conn.close()
    except Exception as e:
        print(f"[Avertissement SQLite] SQL query failed, falling back to JSON scan: {e}")
        return _load_run_history_pure_json(history_dir)
        
    history_summary = []
    
    for row in rows:
        run_id, taux, prime_a_r, statut, maker, checker, date_exec, port_libelle, num_run, lob_id, c_periode = row
        
        # Essayer de lire le fichier JSON pour les compteurs précis de lignes
        json_path = os.path.join(history_dir, f"{run_id}.json")
        run_name = f"{port_libelle} - Run #{num_run}"
        fatal_defects = 0
        total_cases = 0
        timestamp_str = date_exec.isoformat() if hasattr(date_exec, "isoformat") else str(date_exec)
        periode_arrete = c_periode
        current_step = "Importation"
        
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                run_name = data.get("run_name") or run_name
                kpis = data.get("kpis", {})
                fatal_defects = kpis.get("fatal_defects", 0)
                total_cases = kpis.get("total_cases", 0)
                timestamp_str = data.get("timestamp") or timestamp_str
                lob_id = data.get("lob_id") or data.get("metadata", {}).get("lob_id") or lob_id
                periode_arrete = data.get("periode_arrete") or data.get("metadata", {}).get("periode_arrete") or periode_arrete
                current_step = data.get("current_step") or current_step
            except Exception:
                pass
                
        # Conserver le statut de validation de la base de données relationnelle comme source de vérité
        summary = {
            "run_id": run_id,
            "run_name": run_name,
            "timestamp": timestamp_str,
            "success_rate_pct": taux,
            "fatal_defects": fatal_defects,
            "total_cases": total_cases,
            "total_absolute_delta_euros": prime_a_r,
            "final_status": statut,
            "lob_id": lob_id,
            "periode_arrete": periode_arrete,
            "current_step": current_step
        }
        history_summary.append(summary)
        
    return history_summary

def _load_run_history_pure_json(history_dir: str) -> List[Dict[str, Any]]:
    """Scan JSON historique de secours en cas d'absence de la base de données."""
    if not os.path.exists(history_dir):
        return []

    history_summary = []

    for file_name in os.listdir(history_dir):
        if file_name.endswith(".json"):
            file_path = os.path.join(history_dir, file_name)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                if all(k in data for k in ["run_id", "run_name", "timestamp", "kpis"]):
                    kpis = data["kpis"]
                    summary = {
                        "run_id": data["run_id"],
                        "run_name": data["run_name"],
                        "timestamp": data["timestamp"],
                        "success_rate_pct": kpis.get("success_rate_pct", 0.0),
                        "fatal_defects": kpis.get("fatal_defects", 0),
                        "total_cases": kpis.get("total_cases", 0),
                        "total_absolute_delta_euros": kpis.get("total_absolute_delta_euros", 0.0),
                        "final_status": kpis.get("final_status", "NON CONFORME"),
                        "lob_id": data.get("lob_id") or data.get("metadata", {}).get("lob_id") or "LOB_AUTO_PART",
                        "periode_arrete": data.get("periode_arrete") or data.get("metadata", {}).get("periode_arrete") or "",
                        "current_step": data.get("current_step") or "Importation"
                    }
                    history_summary.append(summary)
            except Exception:
                continue

    history_summary.sort(key=lambda x: x["timestamp"], reverse=True)
    return history_summary

def delete_uat_run(history_dir: str, run_id: str) -> bool:
    """
    Archive logiquement (is_deleted: true) le fichier JSON d'une campagne de test UAT,
    le déplace dans data/archive_runs/ et le retire des bases SQLite.
    Retourne True en cas de succès, False sinon.
    """
    # 1. Suppression des bases SQLite
    db_paths = ["data/actuarecette.db", "data/actuarecette_v2.db"]
    for db_path in db_paths:
        if os.path.exists(db_path):
            try:
                import sqlite3
                conn = sqlite3.connect(db_path)
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA busy_timeout=5000")
                conn.execute("DELETE FROM runs_execution WHERE id_run = ?", [run_id])
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"[Avertissement SQLite] Echec de suppression pour {db_path} : {e}")

    # 2. Archivage logique et déplacement du fichier
    file_path = os.path.join(history_dir, f"{run_id}.json")
    if os.path.exists(file_path):
        try:
            with _original_open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            data["is_deleted"] = True
            
            archive_dir = "data/archive_runs"
            os.makedirs(archive_dir, exist_ok=True)
            archive_path = os.path.join(archive_dir, f"{run_id}.json")
            with _original_open(archive_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            os.remove(file_path)
            return True
        except Exception as e:
            print(f"[Erreur] Echec d'archivage logique : {e}")
            return False
    return True

def compare_uat_runs(history_dir: str, run_id_1: str, run_id_2: str) -> Dict[str, Any]:
    """
    Réalise une comparaison différentielle (non-régression) entre deux exécutions d'UAT.
    """
    file_path_1 = os.path.join(history_dir, f"{run_id_1}.json")
    file_path_2 = os.path.join(history_dir, f"{run_id_2}.json")
    
    if not os.path.exists(file_path_1) or not os.path.exists(file_path_2):
        raise FileNotFoundError("Une ou plusieurs campagnes sélectionnées sont introuvables.")
        
    with open(file_path_1, "r", encoding="utf-8") as f:
        run_1 = json.load(f)
    with open(file_path_2, "r", encoding="utf-8") as f:
        run_2 = json.load(f)
        
    kpis_1 = run_1["kpis"]
    kpis_2 = run_2["kpis"]
    
    anomalies_1 = run_1.get("anomalies", [])
    anomalies_2 = run_2.get("anomalies", [])
    
    # Comptage des anomalies par catégorie pour comparaison graphique
    cat_counts_1 = {}
    for a in anomalies_1:
        cat = a.get("anomaly_category", "Écart fonctionnel non répertorié")
        cat_counts_1[cat] = cat_counts_1.get(cat, 0) + 1
        
    cat_counts_2 = {}
    for a in anomalies_2:
        cat = a.get("anomaly_category", "Écart fonctionnel non répertorié")
        cat_counts_2[cat] = cat_counts_2.get(cat, 0) + 1
        
    # Union des catégories
    all_categories = list(set(cat_counts_1.keys()).union(set(cat_counts_2.keys())))
    
    cat_comparison = {}
    for cat in all_categories:
        cat_comparison[cat] = {
            "v1": cat_counts_1.get(cat, 0),
            "v2": cat_counts_2.get(cat, 0)
        }
        
    return {
        "status": "SUCCESS",
        "run_1_name": run_1["run_name"],
        "run_2_name": run_2["run_name"],
        "success_rate_1": kpis_1.get("success_rate_pct", 0.0),
        "success_rate_2": kpis_2.get("success_rate_pct", 0.0),
        "fatal_defects_1": kpis_1.get("fatal_defects", 0),
        "fatal_defects_2": kpis_2.get("fatal_defects", 0),
        "total_delta_1": kpis_1.get("total_absolute_delta_euros", 0.0),
        "total_delta_2": kpis_2.get("total_absolute_delta_euros", 0.0),
        "categories_comparison": cat_comparison
    }

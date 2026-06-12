"""
Module Audit Trail
==================

Gère le journal centralisé d'audit (ajout d'entrées, chargement) et la génération
de kits témoins au format ZIP.

Extrait de anomaly_manager.py pour modularité.

Auteur: Senior Software Engineer & Product Owner Projets IT Assurance
Version: 1.0.0
"""

import os
from src.db_adapter import sqlite_connection
import json
import hashlib
import datetime
from typing import Dict, List, Any

_HASH_SALT = "ActuaRecette_v6_audit_2024"

def add_global_audit_entry(
    run_id: str,
    run_name: str,
    role: str,
    action: str,
    comment: str,
    validator_name: str,
    audit_file_path: str = "data/audit_log.json"
) -> Dict[str, Any]:
    """
    Ajoute une entree d'audit dans le journal centralise.
    T82: Ecrit PRIORITAIREMENT en SQLite (audit_entries), puis en JSON (legacy).
    """
    now = datetime.datetime.now()
    sig = hashlib.sha256(
        f"{now.isoformat()}:{validator_name}:{run_id}:{action}".encode("utf-8")
    ).hexdigest()[:16]

    # Resolve LOB ID
    lob_id = None
    if run_id:
        try:
            run_file = os.path.join("data/uat_runs", f"{run_id}.json")
            if os.path.exists(run_file):
                with open(run_file, "r", encoding="utf-8") as f:
                    run_data = json.load(f)
                lob_id = run_data.get("lob_id") or run_data.get("metadata", {}).get("lob_id")
            if not lob_id:
                from dashboard.utils.lob_filter import classify_run_lob
                lob_id = classify_run_lob({"run_name": run_name, "run_id": run_id})
        except Exception:
            pass
    if not lob_id:
        lob_id = "LOB_AUTO_PART"

    entry = {
        "timestamp": now.isoformat(),
        "run_id": run_id,
        "run_name": run_name,
        "role": role,
        "action": action,
        "comment": comment,
        "validator_name": validator_name,
        "signature_hash": sig,
        "lob_id": lob_id,
    }

    # ── T82: SQLite-first persistence ──
    db_path_sqlite = "data/actuarecette_v2.db"
    sqlite_ok = False
    if os.path.exists(db_path_sqlite):
        try:
            import sqlite3
            conn = sqlite_connection(db_path_sqlite)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=3000")
            conn.execute(
                """INSERT INTO audit_entries
                (timestamp, user_sso, user_name, user_role, run_id, id_portefeuille, action, comment, signature_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (now.isoformat(), validator_name, validator_name, role, run_id, lob_id, action, comment, sig),
            )
            conn.commit()
            conn.close()
            sqlite_ok = True
        except Exception as e:
            import logging
            logging.getLogger("actuarecette").warning(f"SQLite audit write failed: {e}")

    # ── SQLite status update (replacing legacy DuckDB) ──
    status_map = {
        "APPROVED": "CERTIFIÉ",
        "CERTIFIED": "CERTIFIÉ",
        "CERTIFIED_WITH_RESERVES": "CERTIFIÉ",
        "REJECTED": "REJETÉ",
        "SUBMITTED": "SOUMIS"
    }
    new_signature = None
    if action in status_map:
        for db_file in ["data/actuarecette.db", "data/actuarecette_v2.db"]:
            if os.path.exists(db_file):
                try:
                    import sqlite3
                    def local_get_hash(run_id, success_rate, prime_at_risk, validator, timestamp):
                        _HASH_SALT = "ActuaRecette_v6_audit_2024"
                        payload = f"{run_id}|{success_rate}|{prime_at_risk}|{validator}|{timestamp}"
                        salted = f"{_HASH_SALT}:{payload}"
                        import hashlib
                        return hashlib.sha256(salted.encode('utf-8')).hexdigest()

                    conn = sqlite3.connect(db_file)
                    conn.execute("PRAGMA journal_mode=WAL")
                    conn.execute("PRAGMA busy_timeout=5000")
                    run_info = conn.execute(
                        "SELECT taux_alignement, prime_a_risque, date_execution, maker_sso_user FROM runs_execution WHERE id_run = ?",
                        [run_id]
                    ).fetchone()

                    if run_info:
                        taux, prime_a_r, date_exec, maker = run_info
                        new_signature = local_get_hash(
                            run_id=run_id,
                            success_rate=taux,
                            prime_at_risk=prime_a_r,
                            validator=validator_name,
                            timestamp=str(date_exec)
                        )
                        entry["signature_hash"] = new_signature
                        conn.execute(
                            "UPDATE runs_execution SET statut_validation = ?, checker_sso_user = ?, signature_hash = ? WHERE id_run = ?",
                            [status_map[action], validator_name, new_signature, run_id]
                        )
                        conn.commit()
                    conn.close()
                except Exception as db_err:
                    import logging
                    logging.getLogger("actuarecette").warning(f"SQLite status update failed for {db_file}: {db_err}")

    # ── T82: JSON legacy (deprecated, kept for backward compat) ──
    LEGACY_JSON_ENABLED = os.environ.get("ACTUARECETTE_LEGACY_JSON", "1") == "1"
    if LEGACY_JSON_ENABLED:
        os.makedirs(os.path.dirname(audit_file_path), exist_ok=True)
        log_data = []
        if os.path.exists(audit_file_path):
            try:
                with open(audit_file_path, "r", encoding="utf-8") as f:
                    log_data = json.load(f)
            except Exception:
                log_data = []
        log_data.append(entry)
        try:
            with open(audit_file_path, "w", encoding="utf-8") as f:
                json.dump(log_data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

        # Update JSON run file (legacy)
        run_file_path = f"data/uat_runs/{run_id}.json"
        if os.path.exists(run_file_path):
            try:
                with open(run_file_path, "r", encoding="utf-8") as f:
                    run_data = json.load(f)
                run_data["validation_status"] = action
                if new_signature:
                    run_data["signature_hash"] = new_signature
                if "audit_trail" not in run_data:
                    run_data["audit_trail"] = []
                run_data["audit_trail"].append(entry)
                with open(run_file_path, "w", encoding="utf-8") as f:
                    json.dump(run_data, f, indent=2, ensure_ascii=False)
            except Exception:
                pass

    return entry

def load_global_audit_trail(audit_file_path: str = "data/audit_log.json") -> List[Dict[str, Any]]:
    """
    Charge l'intégralité du journal centralisé d'audit et le renvoie trié par date décroissante.
    """
    db_path_sqlite = "data/actuarecette_v2.db"
    if os.path.exists(db_path_sqlite):
        try:
            import sqlite3
            conn = sqlite_connection(db_path_sqlite)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM audit_entries ORDER BY timestamp DESC")
            rows = cursor.fetchall()
            conn.close()
            trail = []
            for r in rows:
                run_id = r["run_id"]
                run_name = "Action Admin"
                if run_id:
                    try:
                        run_file = os.path.join("data/uat_runs", f"{run_id}.json")
                        if os.path.exists(run_file):
                            with open(run_file, "r", encoding="utf-8") as f:
                                rd = json.load(f)
                            run_name = rd.get("run_name", run_id)
                    except Exception:
                        run_name = run_id
                trail.append({
                    "timestamp": r["timestamp"],
                    "run_id": r["run_id"] or "",
                    "run_name": run_name,
                    "role": r["user_role"],
                    "action": r["action"],
                    "comment": r["comment"],
                    "validator_name": r["user_name"],
                    "signature_hash": r["signature_hash"],
                    "lob_id": r["id_portefeuille"] or "LOB_AUTO_PART"
                })
            return trail
        except Exception as e:
            import logging
            logging.getLogger("actuarecette").warning(f"SQLite audit load failed: {e}")

    if not os.path.exists(audit_file_path):
        return []
    try:
        with open(audit_file_path, "r", encoding="utf-8") as f:
            log_data = json.load(f)
        for entry in log_data:
            if "lob_id" not in entry:
                entry["lob_id"] = "LOB_AUTO_PART"
        # Tri chronologique décroissant
        log_data.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return log_data
    except Exception:
        return []

def generate_witness_zip(history_dir: str, run_id: str, audit_file_path: str = "data/audit_log.json") -> bytes:
    """
    Génère un kit témoin au format ZIP en mémoire, contenant max 5 CSV témoins
    et le bilan de validation au format Markdown.
    Chaque CSV témoin contient 2 lignes (Ligne 1 = Attendu MOA, Ligne 2 = Réel DSI).
    """
    import zipfile
    import io
    import pandas as pd
    
    file_path = os.path.join(history_dir, f"{run_id}.json")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"La campagne de recette {run_id} est introuvable.")
        
    with open(file_path, "r", encoding="utf-8") as f:
        run_data = json.load(f)
        
    kpis = run_data["kpis"]
    anomalies = run_data.get("anomalies", [])
    
    # Récupérer les statuts de validation et logs d'audit pour ce run_id
    validation_status = "PENDING"
    run_audit_trail = []
    if os.path.exists(audit_file_path):
        try:
            with open(audit_file_path, "r", encoding="utf-8") as f:
                logs = json.load(f)
            # Filtrer pour ce run
            for l in logs:
                if l.get("run_id") == run_id:
                    run_audit_trail.append(l)
                    # La validation la plus récente l'emporte
                    if l.get("action") in ["APPROVED", "REJECTED"]:
                        validation_status = l["action"]
        except Exception:
            pass
            
    # Trier les anomalies par gravité absolue décroissante
    anomalies_sorted = sorted(
        anomalies, 
        key=lambda x: abs(x.get("abs_deviation", 0)), 
        reverse=True
    )
    
    # Limiter à 5 anomalies maximum pour le kit témoin
    top_anomalies = anomalies_sorted[:5]
    
    # Création du ZIP en mémoire
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        
        # 1. Génération des fichiers CSV témoins (2 lignes par CSV)
        for idx, a in enumerate(top_anomalies):
            client_id = a.get("ID_CLIENT") or a.get("id_assure") or f"client_{idx+1}"
            
            # Reconstruction du profil 2 lignes
            row1 = a.copy()
            row1["PRIME_DSI"] = "N/A"
            row1["abs_deviation"] = "N/A"
            row1["rel_deviation_pct"] = "N/A"
            row1["is_fatal_defect"] = "N/A"
            row1["TYPE_LIGNE"] = "ATTENDU (MOA RÉFÉRENCE)"
            
            row2 = a.copy()
            row2["PRIME_REF"] = "N/A"
            row2["PRIME_ACTU"] = "N/A"
            row2["TYPE_LIGNE"] = "RÉEL (DSI PRODUCTION)"
            
            # Nettoyer les clés
            all_cols = ["ID_CLIENT", "TYPE_LIGNE"]
            for k in a.keys():
                if k not in all_cols:
                    all_cols.append(k)
                    
            df_witness = pd.DataFrame([row1, row2])
            df_witness = df_witness[all_cols]
            
            # Export compatible Windows Excel (utf-8-sig, point-virgule)
            csv_str = df_witness.to_csv(index=False, sep=";", encoding="utf-8-sig")
            
            csv_filename = f"temoin_{idx+1}_{client_id}.csv"
            zip_file.writestr(csv_filename, csv_str)
            
        # 2. Génération du fichier bilan Markdown
        audit_trail_lines = []
        for audit in sorted(run_audit_trail, key=lambda x: x.get("timestamp", "")):
            act_emoji = "🟢 APPROBATION" if audit["action"] == "APPROVED" else ("🔴 REJET" if audit["action"] == "REJECTED" else "💬 COMMENTAIRE")
            audit_trail_lines.append(
                f"* **{audit['timestamp']}** | {act_emoji} par **{audit['validator_name']}** ({audit['role']}) :\n"
                f"  > *\"{audit['comment']}\"*"
            )
            
        audit_trail_md = "\n".join(audit_trail_lines) if audit_trail_lines else "*Aucune action enregistrée pour le moment.*"
        
        status_label = "🟢 CONFORME & APPROUVÉ" if validation_status == "APPROVED" else ("🔴 CRITIQUE & REJETÉ" if validation_status == "REJECTED" else "⏳ EN ATTENTE DE SIGNATURE")
        
        bilan_md = f"""# 🧪 KIT TÉMOIN DE RÉCONCILIATION ACTUARIELLE - ACTUARECETTE
========================================================================

## 📋 Informations Générales
*   **Nom de la campagne :** {run_data['run_name']}
*   **Identifiant unique :** {run_id}
*   **Date d'exécution :** {run_data['timestamp']}
*   **Statut de Validation :** **{status_label}**

## 📈 Indicateurs Clés de Recette (KPIs)
*   **Taux de conformité :** **{kpis['success_rate_pct']:.2f} %**
*   **Dossiers sains :** {kpis['conform_cases']} / {kpis['total_cases']}
*   **Anomalies critiques :** **{kpis['fatal_defects']}** dossiers hors tolérance
*   **Divergence financière cumulée :** **{kpis['total_absolute_delta_euros']:.2f} €**
*   **Écart maximal constaté :** {kpis['max_deviation_euros']:.2f} €

## 👥 Journal d'Audit & Signatures
{audit_trail_md}

## 🚨 Top {len(top_anomalies)} des anomalies témoins incluses dans ce kit
Veuillez vous référer aux fichiers CSV joints pour reproduire chirurgicalement ces bugs dans le tarificateur de production.

"""
        for idx, a in enumerate(top_anomalies):
            client_id = a.get("ID_CLIENT") or a.get("id_assure") or f"client_{idx+1}"
            ref_val = a.get("PRIME_ACTU") or a.get("PRIME_REF") or 0.0
            prod_val = a.get("PRIME_DSI") or a.get("prime_dsi") or 0.0
            abs_dev = a.get("abs_deviation") or 0.0
            rel_dev = a.get("rel_deviation_pct") or 0.0
            cat = a.get("anomaly_category", "Écart fonctionnel non répertorié")
            dtl = a.get("suspicion_details", "Suspicion de divergence de formules.")
            
            bilan_md += f"""### {idx+1}. Dossier {client_id}
*   **Catégorie de l'écart :** {cat}
*   **Prime Attendue (MOA) :** {ref_val:.2f} €
*   **Prime Production (DSI) :** {prod_val:.2f} €
*   **Écart absolu :** {abs_dev:+.2f} €
*   **Écart relatif :** {rel_dev:+.2f} %
*   **Diagnostic de Recette :** {dtl}
*   **Fichier de reproduction joint :** `temoin_{idx+1}_{client_id}.csv`

"""
            
        zip_file.writestr("bilan_recette.md", bilan_md)
        
    return zip_buffer.getvalue()

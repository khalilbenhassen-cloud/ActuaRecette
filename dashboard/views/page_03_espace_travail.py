
import html
import hashlib
import os
from dashboard.utils.engine_proxy import sqlite_connection
import sys
import json
import datetime
import streamlit as st
import pandas as pd
import requests
from typing import Optional, Dict, Any, List

# Intercepter open pour empêcher d'écrire dans les runs verrouillés
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
            f = _original_open(file, mode, *args, **kwargs)
            from dashboard.utils.engine_proxy import SyncOnCloseFileWrapper
            return SyncOnCloseFileWrapper(f, file)
    return _original_open(file, mode, *args, **kwargs)

open = custom_open

from dashboard.components.stepper import stepper as render_stepper
from dashboard.utils.validators import validate_run_id

from dashboard.utils.engine_proxy import (
    load_run_history as _local_load_run_history,
    load_global_audit_trail as _local_load_audit_trail,
    add_audit_entry as _add_audit_entry,
    merge_datasets,
    calculate_variances,
    compute_uat_kpis,
    extract_anomalies,
    generate_pdf_bytes,
    generate_witness_zip,
    is_available as _engine_available,
)
_local_modules = _engine_available()

from dashboard.utils.api_client import API_BASE_URL as API_URL

_api_ok = False
try:
    _res_health = requests.get(f"{API_URL}/health", timeout=0.3)
    if _res_health.status_code == 200:
        _api_ok = True
except Exception:
    pass

def _fetch_run_history(user_headers: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
    if _api_ok:
        try:
            res = requests.get(f"{API_URL}/history", headers=user_headers, timeout=1.5)
            if res.status_code == 200:
                return res.json()
        except Exception:
            pass
    if _local_modules:
        history = _local_load_run_history("data/uat_runs")
        if user_headers:
            visible_lobs = [lob.strip() for lob in user_headers.get("X-User-LOBs", "").split(",") if lob.strip()]
            from dashboard.utils.lob_filter import filter_runs_by_lobs
            return filter_runs_by_lobs(history, visible_lobs)
        return history
    return []

def _fetch_audit_trail(user_headers: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
    if _api_ok:
        try:
            res = requests.get(f"{API_URL}/audit-trail", headers=user_headers, timeout=1.5)
            if res.status_code == 200:
                return res.json()
        except Exception:
            pass
    trail = _local_load_audit_trail("data/audit_log.json")
    if user_headers:
        visible_lobs = [lob.strip() for lob in user_headers.get("X-User-LOBs", "").split(",") if lob.strip()]
        return [entry for entry in trail if entry.get("lob_id", "LOB_AUTO_PART") in visible_lobs]
    return trail

def _load_run_by_id(run_id: str, user_headers: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
    if _api_ok:
        try:
            res = requests.get(f"{API_URL}/history/{run_id}", headers=user_headers, timeout=1.5)
            if res.status_code == 200:
                return res.json()
        except Exception:
            pass
    run_file = os.path.join("data", "uat_runs", f"{run_id}.json")
    if os.path.exists(run_file):
        with open(run_file, "r", encoding="utf-8") as f:
            run_data = json.load(f)
        if user_headers:
            visible_lobs = [lob.strip() for lob in user_headers.get("X-User-LOBs", "").split(",") if lob.strip()]
            from dashboard.utils.lob_filter import can_access_run
            if not can_access_run(run_data, visible_lobs):
                return None
        return run_data
    return None

def _get_campaign_status(run_id: str, user_headers: Optional[Dict[str, str]] = None, audit_trail: Optional[List[Dict[str, Any]]] = None) -> str:
    if audit_trail is None:
        audit_trail = _fetch_audit_trail(user_headers)
    run_trail = [t for t in audit_trail if t.get("run_id") == run_id]
    if not run_trail:
        run_data = _load_run_by_id(run_id, user_headers)

        if run_data and "kpis" in run_data:
            fs = run_data["kpis"].get("final_status", "")
            fs_upper = fs.upper().strip() if fs else ""
            if fs_upper == "CONFORME":
                return "Certifi\u00e9"
            elif fs_upper == "NON CONFORME":
                return "En analyse"
            elif fs_upper == "SUBMITTED_FOR_VALIDATION":
                return "Pr\u00eat pour validation"
            elif fs_upper in ("APPROVED", "FINAL_APPROVED"):
                return "Certifi\u00e9"
            elif fs_upper == "PENDING_APPROVAL":
                return "En attente approbation"
            elif fs_upper == "REJECTED":
                return "Rejet\u00e9"
            elif fs_upper in ("CREATED_AND_CALCULATED", "EN_ANALYSE"):
                return "En analyse"
        return "Brouillon"
    latest = run_trail[0]
    action = latest.get("action")
    if action in ("APPROVED", "FINAL_APPROVED"):
        comment = latest.get("comment", "").lower()
        if "r\u00e9serve" in comment or "reserve" in comment:
            return "Certifi\u00e9 avec r\u00e9serves"
        return "Certifi\u00e9"
    elif action == "REJECTED":
        return "Rejet\u00e9"
    elif action == "PENDING_APPROVAL":
        return "En attente approbation"
    elif action == "SUBMITTED_FOR_VALIDATION":
        return "Pr\u00eat pour validation"
    elif action == "CREATED_AND_CALCULATED":
        return "En analyse"
    elif action == "CREATED_DRAFT":
        return "Brouillon"
    return "Brouillon"

def _get_status_html(status: str) -> str:
    from dashboard.components.status_badge import status_badge as _sb
    return _sb(status)

def _compute_file_fingerprint(uploaded_file) -> dict:
    content = uploaded_file.getvalue()
    sha256 = hashlib.sha256(content).hexdigest()
    user_data = st.session_state.get("user", {})
    return {
        "filename": uploaded_file.name,
        "sha256": sha256,
        "size_bytes": len(content),
        "uploaded_by": user_data.get("name", ""),
        "uploaded_at": datetime.datetime.now().isoformat()
    }

def _compute_local_file_fingerprint(filepath: str) -> dict:
    with open(filepath, "rb") as f:
        content = f.read()
    sha256 = hashlib.sha256(content).hexdigest()
    user_data = st.session_state.get("user", {})
    return {
        "filename": os.path.basename(filepath),
        "sha256": sha256,
        "size_bytes": len(content),
        "uploaded_by": user_data.get("name", "Systeme"),
        "uploaded_at": datetime.datetime.now().isoformat()
    }

def _save_uploaded_dataset(run_id: str, uploaded_file, df, prefix: str) -> dict:
    os.makedirs("data/saved_datasets", exist_ok=True)
    dest_path = os.path.join("data/saved_datasets", f"{run_id}_{prefix}.csv")
    _, ext = os.path.splitext(uploaded_file.name)
    if ext.lower() == ".csv":
        raw_bytes = uploaded_file.getvalue()
        with open(dest_path, "wb") as f:
            f.write(raw_bytes)
        fp = _compute_file_fingerprint(uploaded_file)
    else:
        raw_bytes = df.to_csv(index=False).encode("utf-8")
        with open(dest_path, "wb") as f:
            f.write(raw_bytes)
        sha256 = hashlib.sha256(raw_bytes).hexdigest()
        fp = {
            "filename": uploaded_file.name,
            "sha256": sha256,
            "size_bytes": len(raw_bytes),
            "uploaded_by": st.session_state.get("user", {}).get("name", ""),
            "uploaded_at": datetime.datetime.now().isoformat()
        }
    fp["rows"] = len(df)
    return fp

def _load_control_rules(lob_id: str = "LOB_AUTO_PART", domaine: str = "Prime") -> list:
    import sqlite3
    db_path = "data/actuarecette.db"
    if not os.path.exists(db_path):
        return []
    try:
        conn = sqlite_connection(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """SELECT id_regle as rule_id, libelle as label, colonne_cible, 
                      operateur_logique, valeur_seuil, formule_theorique, 
                      tolerance_unitaire, statut, severite as severity, 
                      condition_application, COALESCE(valide_par_sso, cree_par_sso) as approved_by, 
                      version_regle as version,
                      domaine as domain, 'Contrôle réglementaire' as description,
                      'Art. 82 Directive 2009/138/CE (Solvabilité II)' as regulatory_ref,
                      1 as is_mandatory
               FROM regles_recette_dynamiques
               WHERE id_portefeuille = ? AND domaine = ? AND statut = 'ACTIF'""",
            [lob_id, domaine]
        )
        rules = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return rules
    except Exception as e:
        print(f"[Avertissement] Echec chargement regles : {e}")
        return []

def _find_previous_ref_hash(lob_id: str, current_run_id: str) -> str:
    runs_dir = "data/uat_runs"
    if not os.path.exists(runs_dir):
        return ""
    best_ts, best_hash = "", ""
    try:
        for f in os.listdir(runs_dir):
            if f.endswith(".json") and not f.startswith(current_run_id):
                with open(os.path.join(runs_dir, f), "r", encoding="utf-8") as file:
                    data = json.load(file)
                if data.get("lob_id") == lob_id:
                    ts = data.get("timestamp", "")
                    if ts > best_ts:
                        best_ts = ts
                        best_hash = data.get("ref_file_hash", "")
    except Exception:
        pass
    return best_hash

def _create_draft_campaign(run_name: str, lob_id: str, periode_arrete: str = "", domaine: str = "Prime") -> str:
    import uuid
    now = datetime.datetime.now()
    run_id = f"run_{uuid.uuid4().hex[:12]}"

    user_data = st.session_state.get("user", {})
    run_payload = {
        "run_id": run_id,
        "run_name": run_name,
        "lob_id": lob_id,
        "domaine": domaine,
        "periode_arrete": periode_arrete,
        "maker_sso": user_data.get("sso", ""),
        "maker_name": user_data.get("name", ""),
        "timestamp": now.isoformat(),
        "files": {},
        "dsi_declaration": {},
        "applied_rules": [],
        "justification": {},
        "metadata": {
            "engine_version": "ActuaRecette-v6.0",
            "environment": "UAT-Recette",
            "created_by": user_data.get("sso", ""),
            "maker_name": user_data.get("name", ""),
            "lob_id": lob_id,
        },
        "kpis": {
            "total_cases": 0, "conform_cases": 0, "fatal_defects": 0,
            "success_rate_pct": 0.0, "total_absolute_delta_euros": 0.0,
            "max_deviation_euros": 0.0, "final_status": "Brouillon"
        },
        "anomalies": []
    }

    os.makedirs("data/uat_runs", exist_ok=True)
    file_path = os.path.join("data/uat_runs", f"{run_id}.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(run_payload, f, indent=2, ensure_ascii=False)

    if _local_modules:
        try:
            _add_audit_entry(
                run_id=run_id,
                run_name=run_name,
                role=user_data.get("role", "Actuaire MOA"),
                action="CREATED_DRAFT",
                comment=f"Brouillon créé par {user_data.get('name', 'Système')} | LOB: {lob_id}",
                validator_name=user_data.get("name", "Système")
            )
        except Exception:
            pass

    st.cache_data.clear()
    return run_id

def _save_import_metadata(run_id: str):
    file_path = os.path.join("data/uat_runs", f"{run_id}.json")
    if not os.path.exists(file_path):
        return
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["files"] = {
            "reference": st.session_state.get("wizard_ref_fingerprint", {}),
            "production": st.session_state.get("wizard_prod_fingerprint", {}),
        }
        dsi_date = st.session_state.get("dsi_date")
        data["dsi_declaration"] = {
            "systeme_source": st.session_state.get("dsi_systeme", ""),
            "date_extraction": str(dsi_date) if dsi_date else "",
            "reference_export": st.session_state.get("dsi_ref", ""),
            "declared_at": datetime.datetime.now().isoformat(),
            "declared_by": st.session_state.get("user", {}).get("name", ""),
        }
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

def _save_applied_rules(run_id: str):
    file_path = os.path.join("data/uat_runs", f"{run_id}.json")
    if not os.path.exists(file_path):
        return
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        lob_id = data.get("lob_id", "LOB_AUTO_PART")
        domaine = data.get("domaine", "Prime")
        rules = _load_control_rules(lob_id, domaine)
        snapshot = [{"rule_id": r["rule_id"], "version": r.get("version", "1.0"),
                     "severity": r.get("severity", ""), "label": r.get("label", ""),
                     "domain": r.get("domain", ""),
                     "formule_theorique": r.get("formule_theorique", ""),
                     "condition_application": r.get("condition_application", ""),
                     "regulatory_ref": r.get("regulatory_ref", "")} for r in rules]
        data["applied_rules"] = snapshot
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

def _get_lob_tolerance(lob_id: str, domaine: str = "Prime") -> dict:
    import sqlite3
    db_path = "data/actuarecette.db"
    
    default_seuils = {
        "Prime": {"tolerance_pct": 3.0, "warning_pct": 3.0, "critical_pct": 5.0},
        "Sinistre": {"tolerance_pct": 3.0, "warning_pct": 3.0, "critical_pct": 5.0},
        "Réserve": {"tolerance_pct": 4.0, "warning_pct": 4.0, "critical_pct": 6.0},
        "Contrat": {"tolerance_pct": 1.0, "warning_pct": 1.0, "critical_pct": 2.0},
        "Réassurance": {"tolerance_pct": 3.0, "warning_pct": 3.0, "critical_pct": 5.0}
    }.get(domaine, {"tolerance_pct": 5.0, "warning_pct": 3.0, "critical_pct": 5.0})
    
    if os.path.exists(db_path):
        try:
            conn = sqlite_connection(db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(
                """SELECT p.libelle, s.seuil_materialite_pct, s.warning_pct, 
                          s.critical_pct, s.materiality_threshold_eur 
                   FROM portefeuilles p
                   LEFT JOIN portefeuilles_seuils_domaines s 
                     ON p.id_portefeuille = s.id_portefeuille AND s.domaine = ?
                   WHERE p.id_portefeuille = ?""",
                [domaine, lob_id]
            )
            row = cursor.fetchone()
            conn.close()
            if row:
                r = dict(row)
                if r.get("warning_pct") is not None:
                    return {
                        "tolerance_pct": r.get("warning_pct"),
                        "warning_pct": r.get("warning_pct"),
                        "critical_pct": r.get("critical_pct"),
                        "lob_label": r.get("libelle", lob_id),
                    }
                else:
                    return {
                        "tolerance_pct": default_seuils["tolerance_pct"],
                        "warning_pct": default_seuils["warning_pct"],
                        "critical_pct": default_seuils["critical_pct"],
                        "lob_label": r.get("libelle", lob_id),
                    }
        except Exception as e:
            print(f"[Avertissement] Echec chargement tolerance : {e}")
            pass
            
    return {
        "tolerance_pct": default_seuils["tolerance_pct"],
        "warning_pct": default_seuils["warning_pct"],
        "critical_pct": default_seuils["critical_pct"],
        "lob_label": lob_id
    }

def _save_justification(run_id: str, text: str):
    file_path = os.path.join("data/uat_runs", f"{run_id}.json")
    if not os.path.exists(file_path):
        return
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["justification"] = {
            "text": text,
            "author": st.session_state.get("user", {}).get("name", ""),
            "timestamp": datetime.datetime.now().isoformat()
        }
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

def _save_anomaly_justifications(run_id: str, justifications: dict):
    file_path = os.path.join("data/uat_runs", f"{run_id}.json")
    if not os.path.exists(file_path):
        return
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["anomaly_justifications"] = justifications
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

def _save_rejection_comment(run_id: str, comment: str):
    file_path = os.path.join("data/uat_runs", f"{run_id}.json")
    if not os.path.exists(file_path):
        return
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["rejection_comment"] = comment
        data["rejection_reason"] = comment
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

def _update_uat_run_results(run_id: str, run_name: str, kpis: dict,
                            anomalies: list, ref_df=None, prod_df=None):
    file_path = os.path.join("data/uat_runs", f"{run_id}.json")
    existing = {}
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            pass
    existing["run_id"] = run_id
    existing["run_name"] = run_name
    existing["timestamp"] = datetime.datetime.now().isoformat()
    existing.setdefault("metadata", {}).update({"engine_version": "ActuaRecette-v6.0", "environment": "UAT-Recette"})
    existing["kpis"] = kpis
    existing["anomalies"] = anomalies
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)

    if ref_df is not None and prod_df is not None:
        os.makedirs("data/saved_datasets", exist_ok=True)
        ref_df.to_csv(os.path.join("data/saved_datasets", f"{run_id}_ref.csv"), index=False)
        prod_df.to_csv(os.path.join("data/saved_datasets", f"{run_id}_prod.csv"), index=False)
    st.cache_data.clear()

def _update_run_status(run_id: str, new_status: str):
    file_path = os.path.join("data/uat_runs", f"{run_id}.json")
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "kpis" not in data:
                data["kpis"] = {}
            data["kpis"]["final_status"] = new_status
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass
    st.cache_data.clear()

def _delete_run(run_id: str):
    if _local_modules:
        try:
            from dashboard.utils.engine_proxy import delete_uat_run
            delete_uat_run("data/uat_runs", run_id)
        except Exception as e:
            print(f"[Avertissement] Echec suppression relationnelle: {e}")
            run_file = os.path.join("data/uat_runs", f"{run_id}.json")
            if os.path.exists(run_file):
                os.remove(run_file)
    else:
        run_file = os.path.join("data/uat_runs", f"{run_id}.json")
        if os.path.exists(run_file):
            os.remove(run_file)
    for suffix in ["_ref.csv", "_prod.csv"]:
        ds_file = os.path.join("data/saved_datasets", f"{run_id}{suffix}")
        if os.path.exists(ds_file):
            os.remove(ds_file)
    if _local_modules:
        try:
            user_data = st.session_state.get("user", {})
            _add_audit_entry(
                run_id=run_id,
                run_name=run_id,
                role=user_data.get("role", "Actuaire MOA"),
                action="DELETED",
                comment=f"Run supprime par {user_data.get('name', 'Systeme')}.",
                validator_name=user_data.get("name", "Systeme")
            )
        except Exception:
            pass
    st.cache_data.clear()

def _lazy_load_workspace_datasets(run_id: str):
    if st.session_state.get("wizard_ref_df") is None:
        ref_file = os.path.join("data/saved_datasets", f"{run_id}_ref.csv")
        if os.path.exists(ref_file):
            try:
                st.session_state["wizard_ref_df"] = pd.read_csv(ref_file)
                run_file = os.path.join("data/uat_runs", f"{run_id}.json")
                orig_name = "actuarial_ref.csv"
                if os.path.exists(run_file):
                    with open(run_file, "r", encoding="utf-8") as rf:
                        orig_name = json.load(rf).get("files", {}).get("reference", {}).get("filename", "actuarial_ref.csv")
                st.session_state["wizard_ref_name"] = orig_name
            except Exception:
                pass
    if st.session_state.get("wizard_prod_df") is None:
        prod_file = os.path.join("data/saved_datasets", f"{run_id}_prod.csv")
        if os.path.exists(prod_file):
            try:
                st.session_state["wizard_prod_df"] = pd.read_csv(prod_file)
                run_file = os.path.join("data/uat_runs", f"{run_id}.json")
                orig_name = "dsi_prod.csv"
                if os.path.exists(run_file):
                    with open(run_file, "r", encoding="utf-8") as rf:
                        orig_name = json.load(rf).get("files", {}).get("production", {}).get("filename", "dsi_prod.csv")
                st.session_state["wizard_prod_name"] = orig_name
            except Exception:
                pass

def _clear_workspace_state():
    st.session_state["selected_run_id"] = None
    st.session_state["campaign_step"] = "Importation"
    st.session_state.pop("step_restored_for_run", None)
    st.session_state.pop("last_loaded_run_id", None)
    for key in ["wizard_ref_df", "wizard_prod_df", "wizard_ref_name",
                "wizard_prod_name", "pdf_export_bytes", "zip_export_bytes",
                "pdf_export_run_id", "zip_export_run_id",
                "saved_mapping_id_col", "saved_mapping_ref_premium",
                "saved_mapping_prod_premium", "saved_mapping_tolerance",
                "wizard_ref_fingerprint", "wizard_prod_fingerprint",
                "dsi_systeme", "dsi_ref", "dsi_date",
                "ecart_justification"]:
        st.session_state.pop(key, None)

def _get_pdf_report_bytes(run_id, run_name, kpis, anomalies, audit_trail, governance_data=None) -> bytes:
    return generate_pdf_bytes(run_id, run_name, kpis, anomalies, audit_trail, governance_data=governance_data)

def _update_run_checker(run_id: str, checker_sso: str, checker_name: str):
    file_path = os.path.join("data/uat_runs", f"{run_id}.json")
    if not os.path.exists(file_path):
        return
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["checker_sso"] = checker_sso
        data["checker_name"] = checker_name
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

def _load_checker_checklist(lob_id: str = "") -> list:
    path = os.path.join("data", "checker_checklists.json")
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get(lob_id, data.get("_default", []))
    except Exception:
        return []

def _save_checker_review(run_id: str, checklist_items: list, checked: list, comment: str):
    file_path = os.path.join("data/uat_runs", f"{run_id}.json")
    if not os.path.exists(file_path):
        return
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        user_data = st.session_state.get("user", {})
        data["checker_review"] = {
            "items": [{"label": it, "checked": (i in checked)} for i, it in enumerate(checklist_items)],
            "all_checked": len(checked) == len(checklist_items),
            "comment": comment,
            "reviewer": user_data.get("name", ""),
            "reviewer_sso": user_data.get("sso", ""),
            "timestamp": datetime.datetime.now().isoformat()
        }
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

def _update_run_approver(run_id: str, approver_sso: str, approver_name: str):
    file_path = os.path.join("data/uat_runs", f"{run_id}.json")
    if not os.path.exists(file_path):
        return
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["approver_sso"] = approver_sso
        data["approver_name"] = approver_name
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

def _lock_run(run_id: str):
    file_path = os.path.join("data/uat_runs", f"{run_id}.json")
    if not os.path.exists(file_path):
        return
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            raw = f.read()
        data = json.loads(raw)
        integrity_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        data["is_locked"] = True
        data["locked_at"] = datetime.datetime.now().isoformat()
        data["integrity_hash"] = integrity_hash
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

DOMAINES_METIER = ["Prime", "Sinistre", "Réserve", "Contrat", "Réassurance"]

LIMITATION_CATEGORIES = [
    "Données manquantes (dossiers absents du périmètre)",
    "Données incomplètes (champs non renseignés)",
    "Données approximées (estimations utilisées)",
    "Périmètre restreint (LOB partiellement couvert)",
    "Autre limitation",
]

def _generate_certification_number(lob_id: str) -> str:
    now = datetime.datetime.now()
    prefix = f"CERT-{lob_id}-{now.strftime('%Y%m')}"
    runs_dir = "data/uat_runs"
    seq = 1
    if os.path.exists(runs_dir):
        for fn in os.listdir(runs_dir):
            if not fn.endswith(".json"):
                continue
            try:
                with open(os.path.join(runs_dir, fn), "r", encoding="utf-8") as f:
                    rd = json.load(f)
                cert_num = rd.get("certification_number", "")
                if cert_num.startswith(prefix):
                    existing_seq = int(cert_num.split("-")[-1])
                    if existing_seq >= seq:
                        seq = existing_seq + 1
            except Exception:
                continue
    return f"{prefix}-{seq:03d}"

def _save_certification_number(run_id: str, cert_number: str):
    file_path = os.path.join("data/uat_runs", f"{run_id}.json")
    if not os.path.exists(file_path):
        return
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["certification_number"] = cert_number
        data["certified_at"] = datetime.datetime.now().isoformat()
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

def _save_limitations(run_id: str, selected_categories: list, comment: str):
    file_path = os.path.join("data/uat_runs", f"{run_id}.json")
    if not os.path.exists(file_path):
        return
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        limitations = []
        for cat in selected_categories:
            limitations.append({"category": cat, "comment": ""})
        if comment.strip():
            for lim in limitations:
                lim["comment"] = comment.strip()
        data["limitations"] = limitations
        data["limitations_comment"] = comment.strip()
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

def _render_campaign_track(r_name, r_id, date_formatted, status_desc, success_rate, fatal_defects, maker_name="", lob_id=""):
    from dashboard.components.status_badge import status_badge as _sb

    with st.container(border=True):
        col_info, col_tag, col_conf, col_anom = st.columns([5, 1.5, 2, 1.5])
        with col_info:
            st.markdown(f"**{html.escape(str(r_name))}**")
            meta_parts = [f"Date : {date_formatted}"]
            if lob_id:
                meta_parts.append(f"LOB : {html.escape(str(lob_id))}")
            if maker_name:
                meta_parts.append(f"Par : {html.escape(str(maker_name))}")
            st.caption(" | ".join(meta_parts))
        with col_tag:
            st.html(_sb(status_desc, size="sm"))
        with col_conf:
            st.metric("Taux", f"{success_rate:.1f}%")
        with col_anom:
            st.metric("Ecarts", fatal_defects)

def _render_jira_dialog_popover(run_id: str, run_name: str, anomalies: list, key_prefix: str = "workspace_jira"):
    run_file = os.path.join("data/uat_runs", f"{run_id}.json")
    
    jira_tickets = []
    if os.path.exists(run_file):
        try:
            with open(run_file, "r", encoding="utf-8") as rf:
                data = json.load(rf)
                jira_tickets = data.get("jira_tickets", [])
        except Exception:
            pass

    if jira_tickets:
        st.markdown("##### 🎫 Tickets Jira associés")
        for ticket in jira_tickets:
            st.markdown(f"- [🔗 {ticket['key']}](https://jira.groupe.com/browse/{ticket['key']}) \u2014 **{ticket['summary']}** ({ticket['type']})")

    with st.popover("🎫 Exporter/Créer un ticket Jira", use_container_width=True, key=f"{key_prefix}_popover"):
        st.markdown("### 🎫 Créer un ticket Jira de correction")
        st.caption("Cette interface simule l'intégration Jira de production pour l'export des anomalies actuarielles.")
        
        project = st.selectbox("Projet Jira", ["ACT (Actuariat)", "DSI (Systèmes d'Information)", "RISK (Gestion des Risques)"], key=f"{key_prefix}_project")
        issue_type = st.selectbox("Type de ticket", ["Bug / Anomalie de Réconciliation", "Tâche", "Amélioration"], key=f"{key_prefix}_type")
        
        default_summary = f"[ActuaRecette] Anomalies détectées - Campagne: {run_name} ({run_id[:8]})"
        summary = st.text_input("Résumé", value=default_summary, key=f"{key_prefix}_summary")
        
        num_anoms = len(anomalies)
        desc_lines = [
            f"Campagne: {run_name}",
            f"ID de Run: {run_id}",
            f"Nombre d'anomalies bloquantes: {num_anoms}",
            "",
            "Détail des anomalies détectées :"
        ]
        for aidx, a in enumerate(anomalies[:5], 1):
            policy_id = a.get("policy_id", a.get("id", f"anomaly_{aidx}"))
            deviation = a.get("abs_deviation", a.get("delta_euros", 0.0))
            desc_lines.append(f"- Dossier: {policy_id} | Écart: {deviation:.2f} € | Message: {a.get('message', 'Non conforme')}")
        if num_anoms > 5:
            desc_lines.append(f"- ... et {num_anoms - 5} anomalies supplémentaires.")
            
        description = st.text_area("Description", value="\n".join([str(l) for l in desc_lines]), height=150, key=f"{key_prefix}_desc")
        priority = st.selectbox("Priorité", ["Haute", "Moyenne", "Basse", "Critique"], key=f"{key_prefix}_priority")
        
        if st.button("🚀 Créer le ticket Jira", key=f"{key_prefix}_submit", type="primary", use_container_width=True):
            import random
            jira_key = f"ACT-{random.randint(1000, 9999)}"
            st.success(f"✔ Ticket Jira {jira_key} créé avec succès !")
            st.markdown(f"[🔗 Consulter le ticket {jira_key} sur Jira](https://jira.groupe.com/browse/{jira_key})")
            
            if os.path.exists(run_file):
                try:
                    with open(run_file, "r", encoding="utf-8") as rf:
                        data = json.load(rf)
                    tickets = data.get("jira_tickets", [])
                    tickets.append({
                        "key": jira_key,
                        "project": project,
                        "type": issue_type,
                        "summary": summary,
                        "priority": priority,
                        "created_at": datetime.datetime.now().isoformat(),
                        "reporter_name": st.session_state.get("user", {}).get("name", "Système"),
                        "reporter_sso": st.session_state.get("user", {}).get("sso", "unknown")
                    })
                    data["jira_tickets"] = tickets
                    with open(run_file, "w", encoding="utf-8") as wf:
                        json.dump(data, wf, indent=4)
                    st.session_state["wizard_run_data"] = data
                except Exception:
                    pass
            st.rerun()

def render_espace_travail_page():

    from dashboard.views.page_00_login import require_auth
    if require_auth() is None:
        st.stop()
        return

    from dashboard.utils.lob_filter import filter_runs_by_lobs, can_access_run
    from dashboard.utils.auth import ALL_LOBS
    user_data = st.session_state.get("user", {})
    from dashboard.utils.auth import find_user_by_sso
    user_identity = find_user_by_sso(user_data.get("sso", ""))
    visible_lobs = user_identity.visible_lobs if user_identity else user_data.get("assigned_lobs", [])
    user_role = user_identity.role if user_identity else user_data.get("role", "")
    
    from dashboard.utils.auth import UserIdentity
    user_identity_obj = UserIdentity(
        sso=user_data.get("sso", ""),
        name=user_data.get("name", user_data.get("sso", "")),
        role=user_role,
        assigned_lobs=visible_lobs
    )
    user_headers = user_identity_obj.to_headers()

    run_id = st.session_state.get("selected_run_id")
    if run_id is not None:
        try:
            run_id = validate_run_id(run_id)
        except ValueError:
            st.error("Identifiant de campagne invalide.")
            st.session_state["selected_run_id"] = None
            return

    from dashboard.components.breadcrumb import breadcrumb
    run_data = None
    if run_id is not None:
        run_data = _load_run_by_id(run_id, user_headers)
        run_name = run_data.get("run_name", "Détail") if run_data else "Détail"
        breadcrumb(["Opérationnel", "Campagnes", run_name])
    else:
        breadcrumb(["Opérationnel", "Campagnes"])
        
    st.markdown("## ⚙ Campagnes")

    if run_id is not None:
        if run_data is None:
            st.error("Campagne introuvable.")
            if st.button("Revenir \u00e0 la liste"):
                st.session_state["selected_run_id"] = None
                st.rerun()
            return

        # Restauration de l'étape du wizard sauvegardée pour cette campagne
        if st.session_state.get("step_restored_for_run") != run_id:
            saved_step = run_data.get("current_step")
            if saved_step in ["Importation", "Contrôles", "Analyse", "Certification"]:
                st.session_state["campaign_step"] = saved_step
            else:
                campaign_status = _get_campaign_status(run_id, user_headers)
                if campaign_status == "Brouillon":
                    st.session_state["campaign_step"] = "Importation"
                elif campaign_status == "En analyse":
                    st.session_state["campaign_step"] = "Analyse"
                else:
                    st.session_state["campaign_step"] = "Certification"
            
            dsi_decl = run_data.get("dsi_declaration", {})
            if dsi_decl:
                st.session_state["dsi_systeme"] = dsi_decl.get("systeme_source", "")
                st.session_state["dsi_ref"] = dsi_decl.get("reference_export", "")
                dsi_date_str = dsi_decl.get("date_extraction", "")
                if dsi_date_str:
                    try:
                        st.session_state["dsi_date"] = datetime.date.fromisoformat(dsi_date_str)
                    except Exception:
                        pass
            
            files_metadata = run_data.get("files", {})
            if files_metadata:
                if "reference" in files_metadata:
                    st.session_state["wizard_ref_fingerprint"] = files_metadata["reference"]
                if "production" in files_metadata:
                    st.session_state["wizard_prod_fingerprint"] = files_metadata["production"]

            st.session_state["step_restored_for_run"] = run_id
            st.session_state["last_loaded_run_id"] = run_id

        # Sauvegarde automatique de l'étape active dans le JSON si elle a changé
        current_step = st.session_state.get("campaign_step", "Importation")
        if current_step != run_data.get("current_step"):
            run_data["current_step"] = current_step
            run_file = os.path.join("data", "uat_runs", f"{run_id}.json")
            if os.path.exists(run_file):
                try:
                    with open(run_file, "r", encoding="utf-8") as rf:
                        latest_data = json.load(rf)
                    latest_data["current_step"] = current_step
                    with open(run_file, "w", encoding="utf-8") as wf:
                        json.dump(latest_data, wf, indent=2, ensure_ascii=False)
                except Exception:
                    pass

        _lazy_load_workspace_datasets(run_id)

        current_sso = st.session_state.get("user", {}).get("sso", "")
        run_maker_sso = run_data.get("maker_sso", run_data.get("metadata", {}).get("created_by", ""))
        is_own_run = current_sso and current_sso == run_maker_sso

        if not is_own_run and not can_access_run(run_data, visible_lobs):
            st.error("\u2716 Acc\u00e8s refus\u00e9 : cette campagne appartient \u00e0 un portefeuille hors de votre p\u00e9rim\u00e8tre.")
            if st.button("Revenir \u00e0 la liste"):
                st.session_state["selected_run_id"] = None
                st.rerun()
            return

        kpis = run_data.get("kpis", {})
        anomalies = run_data.get("anomalies", [])
        run_name = run_data.get("run_name", "Campagne")
        timestamp_iso = run_data.get("timestamp", "")
        campaign_status = _get_campaign_status(run_id, user_headers)

        try:
            dt = datetime.datetime.fromisoformat(timestamp_iso)
            date_str = dt.strftime("%d/%m/%Y \u00e0 %H:%M")
        except Exception:
            date_str = timestamp_iso

        run_maker = run_data.get("maker_name", "")
        run_lob = run_data.get("lob_id", "")
        run_periode = run_data.get("periode_arrete", "")
        meta_line = f"Ex\u00e9cut\u00e9e le {date_str}"
        if run_periode:
            meta_line += f" | Arr\u00eat\u00e9 : {html.escape(str(run_periode))}"
        if run_lob:
            meta_line += f" | {html.escape(str(run_lob))}"
        if run_maker:
            meta_line += f" | Par {html.escape(str(run_maker))}"
        cert_num = run_data.get("certification_number", "")
        if cert_num:
            meta_line += f" | N\u00b0 {html.escape(str(cert_num))}"

        status_badge = _get_status_html(campaign_status)
        st.html(
            f'<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">'
            f'<div><h3 style="margin:0; color: #0F172A;">{html.escape(str(run_name))}</h3>'
            f'<p style="color: #64748B; font-size: 0.8rem; margin: 2px 0 0 0;">{meta_line}</p></div>'
            f'<div>{status_badge}</div></div>'
        )

        if campaign_status == "Rejeté":
            rejection_comment = run_data.get("rejection_comment") or run_data.get("rejection_reason") or ""
            if rejection_comment:
                st.error(f"❌ **Cette campagne a été rejetée par le Validateur / Responsable MOA.**\n\n💬 **Motif du rejet :** {rejection_comment}")
            else:
                st.error("❌ **Cette campagne a été rejetée par le Validateur / Responsable MOA.**")

        col_back, col_spacer = st.columns([3, 9])
        with col_back:
            if st.button("\u2b05 Quitter", key="quit_ws"):
                _clear_workspace_state()
                st.rerun()

        st.markdown("---")

        steps = ["Importation", "Contr\u00f4les", "Analyse", "Certification"]
        if "campaign_step" not in st.session_state:
            st.session_state["campaign_step"] = "Importation"
        active_idx = steps.index(st.session_state["campaign_step"])

        locked_steps = []
        readonly_steps = []
        if campaign_status == "Brouillon":
            locked_steps = ["Analyse", "Certification"]
        elif campaign_status == "En analyse":
            locked_steps = ["Certification"]
        elif campaign_status in ["Pr\u00eat pour validation", "En attente approbation"]:
            locked_steps = ["Importation"]
            readonly_steps = ["Contr\u00f4les", "Analyse"]
        elif campaign_status in ["Certifi\u00e9", "Certifi\u00e9 avec r\u00e9serves"]:
            locked_steps = ["Importation"]
            readonly_steps = ["Contr\u00f4les", "Analyse", "Certification"]
        elif campaign_status == "Rejet\u00e9":
            locked_steps = ["Analyse", "Certification"]

        if campaign_status in ["Brouillon", "En analyse", "Rejet\u00e9"]:
            ref_ok = st.session_state.get("wizard_ref_df") is not None
            prod_ok = st.session_state.get("wizard_prod_df") is not None
            
            dsi_systeme_val = st.session_state.get("dsi_systeme", "").strip() or run_data.get("dsi_declaration", {}).get("systeme_source", "").strip()
            dsi_ref_val = st.session_state.get("dsi_ref", "").strip() or run_data.get("dsi_declaration", {}).get("reference_export", "").strip()
            dsi_date_val = st.session_state.get("dsi_date") or run_data.get("dsi_declaration", {}).get("date_extraction")
            
            dsi_ok = bool(dsi_systeme_val and dsi_ref_val and dsi_date_val)
            import_complete = ref_ok and prod_ok and dsi_ok
            
            if not import_complete:
                for step in ["Contr\u00f4les", "Analyse", "Certification"]:
                    if step not in locked_steps:
                        locked_steps.append(step)

        is_readonly = st.session_state.get("campaign_step", "") in readonly_steps

        stepper_cols = st.columns(4)
        for idx, step_name in enumerate(steps):
            with stepper_cols[idx]:
                is_active = (step_name == st.session_state["campaign_step"])
                is_locked = (step_name in locked_steps)
                is_ro = (step_name in readonly_steps)
                label = f"\u25cf {step_name}" if is_active else step_name
                if is_locked:
                    label += " [x]"
                elif is_ro:
                    label += " [=]"
                if st.button(label, key=f"step_{step_name}", use_container_width=True, disabled=is_locked):
                    if st.session_state.get("campaign_step") == "Importation":
                        _save_import_metadata(run_id)
                    st.session_state["campaign_step"] = step_name
                    st.rerun()

        st.markdown("---")

        if st.session_state["campaign_step"] == "Importation":
            st.markdown("### \u2750 Ingestion des flux de donn\u00e9es")

            dsi_decl = run_data.get("dsi_declaration", {})
            if "dsi_systeme" not in st.session_state and dsi_decl.get("systeme_source"):
                st.session_state["dsi_systeme"] = dsi_decl["systeme_source"]
            if "dsi_ref" not in st.session_state and dsi_decl.get("reference_export"):
                st.session_state["dsi_ref"] = dsi_decl["reference_export"]
            if "dsi_date" not in st.session_state and dsi_decl.get("date_extraction"):
                try:
                    st.session_state["dsi_date"] = datetime.date.fromisoformat(dsi_decl["date_extraction"])
                except Exception:
                    pass

            is_locked = campaign_status in ["Certifi\u00e9", "Certifi\u00e9 avec r\u00e9serves", "Pr\u00eat pour validation"]
            if is_locked:
                st.info("\u2139 Cette campagne est verrouill\u00e9e. L'importation n'est plus modifiable.")

            if not is_locked:
                if st.button("\u2696 Charger les donn\u00e9es de d\u00e9monstration", key="demo_load", use_container_width=True):
                    try:
                        ref_df = pd.read_csv("data/actuarial_ref.csv")
                        prod_df = pd.read_csv("data/dsi_prod.csv")
                        st.session_state["wizard_ref_df"] = ref_df
                        st.session_state["wizard_prod_df"] = prod_df
                        st.session_state["wizard_ref_name"] = "actuarial_ref.csv"
                        st.session_state["wizard_prod_name"] = "dsi_prod.csv"
                        
                        os.makedirs("data/saved_datasets", exist_ok=True)
                        import shutil
                        shutil.copy("data/actuarial_ref.csv", os.path.join("data/saved_datasets", f"{run_id}_ref.csv"))
                        shutil.copy("data/dsi_prod.csv", os.path.join("data/saved_datasets", f"{run_id}_prod.csv"))
                        st.session_state["wizard_ref_fingerprint"] = _compute_local_file_fingerprint("data/actuarial_ref.csv")
                        st.session_state["wizard_prod_fingerprint"] = _compute_local_file_fingerprint("data/dsi_prod.csv")
                        
                        _save_import_metadata(run_id)
                        st.success("\u2713 Portefeuilles de d\u00e9monstration charg\u00e9s !")
                    except Exception as e:
                        import logging
                        logging.getLogger("actuarecette").exception("Erreur chargement démo")
                        st.error("Impossible de charger les données de démonstration. Vérifiez que les fichiers data/ existent.")

            up1, up2 = st.columns(2)
            with up1:
                st.markdown("##### Source Actuariat (Référence MOA)")
                if not is_locked:
                    ref_file = st.file_uploader("CSV Référence", type=["csv", "xlsx"], key="ref_upload")
                    if ref_file:
                        try:
                            from dashboard.utils.validators import validate_uploaded_file
                            ref_df = validate_uploaded_file(ref_file)
                            st.session_state["wizard_ref_df"] = ref_df
                            st.session_state["wizard_ref_name"] = ref_file.name
                            fp = _save_uploaded_dataset(run_id, ref_file, ref_df, "ref")
                            st.session_state["wizard_ref_fingerprint"] = fp
                            _save_import_metadata(run_id)
                        except ValueError as e:
                            st.error(f"⚠ Source Actuariat rejetée : {e}")
                if st.session_state.get("wizard_ref_df") is not None:
                    fp_ref = st.session_state.get("wizard_ref_fingerprint", {})
                    st.success(f"✓ {st.session_state.get('wizard_ref_name', 'Fichier')} ({len(st.session_state['wizard_ref_df'])} lignes)")
                    if fp_ref.get("sha256"):
                        st.caption(f"🔒 SHA-256 : `{fp_ref['sha256'][:16]}...`")
                        prev_hash = _find_previous_ref_hash(run_data.get("lob_id", ""), run_id)
                        if prev_hash and prev_hash != fp_ref["sha256"]:
                            st.warning("⚠ La source Actuariat a changé depuis la dernière campagne sur ce LOB. Vérifiez que c'est intentionnel.")
                        elif prev_hash and prev_hash == fp_ref["sha256"]:
                            st.info("ℹ Source Actuariat identique à la dernière campagne.")
                    st.dataframe(st.session_state["wizard_ref_df"].head(5), use_container_width=True, hide_index=True)

            with up2:
                st.markdown("##### Source DSI (Production)")
                if not is_locked:
                    prod_file = st.file_uploader("CSV Production", type=["csv", "xlsx"], key="prod_upload")
                    if prod_file:
                        try:
                            from dashboard.utils.validators import validate_uploaded_file
                            prod_df = validate_uploaded_file(prod_file)
                            st.session_state["wizard_prod_df"] = prod_df
                            st.session_state["wizard_prod_name"] = prod_file.name
                            fp = _save_uploaded_dataset(run_id, prod_file, prod_df, "prod")
                            st.session_state["wizard_prod_fingerprint"] = fp
                            _save_import_metadata(run_id)
                        except ValueError as e:
                            st.error(f"⚠ Source DSI rejetée : {e}")
                if st.session_state.get("wizard_prod_df") is not None:
                    fp_prod = st.session_state.get("wizard_prod_fingerprint", {})
                    st.success(f"✓ {st.session_state.get('wizard_prod_name', 'Fichier')} ({len(st.session_state['wizard_prod_df'])} lignes)")
                    if fp_prod.get("sha256"):
                        st.caption(f"🔒 SHA-256 : `{fp_prod['sha256'][:16]}...`")
                    st.dataframe(st.session_state["wizard_prod_df"].head(5), use_container_width=True, hide_index=True)

            if st.session_state.get("wizard_prod_df") is not None and not is_locked:
                st.markdown("---")
                st.markdown("##### 📋 Déclaration de provenance DSI")
                st.caption("Ces informations sont obligatoires pour la traçabilité de la chaîne de custody.")
                dsi_c1, dsi_c2 = st.columns(2)
                with dsi_c1:
                    dsi_systeme = st.text_input("Système source DSI *", key="dsi_systeme",
                                                placeholder="Ex: PASS / SinPro / Réf extraction")
                    dsi_ref = st.text_input("Référence export DSI *", key="dsi_ref",
                                            placeholder="Ex: EXT-2026-0042 validé par J. Martin")
                with dsi_c2:
                    dsi_date = st.date_input("Date d'extraction DSI *", key="dsi_date")

            if st.session_state.get("wizard_ref_df") is not None and st.session_state.get("wizard_prod_df") is not None:
                dsi_ok = (st.session_state.get("dsi_systeme", "").strip()
                          and st.session_state.get("dsi_ref", "").strip())
                if not dsi_ok and not is_locked:
                    st.warning("⚠ La déclaration de provenance DSI est obligatoire pour continuer.")
                btn_disabled = not dsi_ok and not is_locked
                if st.button("➡ Passer aux Contrôles", use_container_width=True, type="primary", disabled=btn_disabled):
                    _save_import_metadata(run_id)
                    st.session_state["campaign_step"] = "Contrôles"
                    st.rerun()

        elif st.session_state["campaign_step"] == "Contr\u00f4les":
            st.markdown("### \u2699 Configuration du mapping et des r\u00e8gles")

            if is_readonly:
                st.info("Mode lecture seule \u2014 la campagne a \u00e9t\u00e9 soumise pour validation.")

                saved_id = st.session_state.get("saved_mapping_id_col", "\u2014")
                saved_ref = st.session_state.get("saved_mapping_ref_premium", "\u2014")
                saved_prod = st.session_state.get("saved_mapping_prod_premium", "\u2014")
                saved_tol = st.session_state.get("saved_mapping_tolerance", 5.0)

                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    st.text_input("Colonne cl\u00e9 (ID)", value=saved_id, disabled=True)
                    ro_domain = run_data.get("domaine", "Prime")
                    st.text_input(f"{ro_domain} Référence", value=saved_ref, disabled=True)
                with col_m2:
                    st.text_input(f"{ro_domain} Production", value=saved_prod, disabled=True)
                    st.slider("Tol\u00e9rance (%)", min_value=0.0, max_value=20.0, value=float(saved_tol), step=0.5, disabled=True, key="ws_tolerance_ro")

                st.caption("\u2139 La r\u00e9conciliation a d\u00e9j\u00e0 \u00e9t\u00e9 ex\u00e9cut\u00e9e. Passage en lecture seule.")

                applied = run_data.get("applied_rules", [])
                if applied:
                    with st.expander(f"\U0001f4cb R\u00e8gles de contr\u00f4le appliqu\u00e9es \u2014 Snapshot ({len(applied)})"):
                        if len(applied) > 10:
                            num_pages = (len(applied) - 1) // 10 + 1
                            selected_page = st.selectbox(
                                "Page des r\u00e8gles",
                                range(1, num_pages + 1),
                                format_func=lambda x: f"Page {x} / {num_pages}",
                                key="page_rules_applied_ro"
                            )
                            start_idx = (selected_page - 1) * 10
                            end_idx = start_idx + 10
                            page_applied = applied[start_idx:end_idx]
                        else:
                            page_applied = applied

                        for rule in page_applied:
                            sev_icon = "\U0001f534" if rule.get("severity") == "BLOQUANT" else "\U0001f7e1"
                            domain_tag = f" \u00b7 {rule.get('domain', '')}" if rule.get("domain") else ""
                            st.markdown(f"{sev_icon} **{rule['rule_id']}** \u2014 {rule.get('label', '')} [{rule.get('severity', '')}]{domain_tag}")
                            st.caption(f"   R\u00e9f. : {rule.get('regulatory_ref', '')} | v{rule.get('version', '1.0')}")
                else:
                    rules = _load_control_rules(run_data.get("lob_id", "LOB_AUTO_PART"), run_data.get("domaine", "Prime"))
                    if rules:
                        with st.expander(f"\U0001f4cb R\u00e8gles de contr\u00f4le ({len(rules)})"):
                            if len(rules) > 10:
                                num_pages = (len(rules) - 1) // 10 + 1
                                selected_page = st.selectbox(
                                    "Page des r\u00e8gles",
                                    range(1, num_pages + 1),
                                    format_func=lambda x: f"Page {x} / {num_pages}",
                                    key="page_rules_fallback_ro"
                                )
                                start_idx = (selected_page - 1) * 10
                                end_idx = start_idx + 10
                                page_rules = rules[start_idx:end_idx]
                            else:
                                page_rules = rules

                            for rule in page_rules:
                                sev_icon = "\U0001f534" if rule.get("severity") == "BLOQUANT" else "\U0001f7e1"
                                mandatory_tag = " \u2014 **Obligatoire**" if rule.get("is_mandatory") else ""
                                st.markdown(f"{sev_icon} **{rule['rule_id']}** \u2014 {rule['label']} [{rule.get('severity', '')}]{mandatory_tag}")
                                st.caption(f"   R\u00e9f. : {rule.get('regulatory_ref', '')} | v{rule.get('version', '1.0')}")
            else:
                ref_df = st.session_state.get("wizard_ref_df")
                prod_df = st.session_state.get("wizard_prod_df")

                if ref_df is None or prod_df is None:
                    st.warning("\u26a0 Veuillez d'abord charger les fichiers dans l'\u00e9tape Importation.")
                    return

                ref_cols = list(ref_df.columns)
                prod_cols = list(prod_df.columns)

                if "map_id_col" not in st.session_state and "saved_mapping_id_col" in st.session_state:
                    saved = st.session_state["saved_mapping_id_col"]
                    if saved in ref_cols:
                        st.session_state["map_id_col"] = saved
                if "map_ref_premium" not in st.session_state and "saved_mapping_ref_premium" in st.session_state:
                    saved = st.session_state["saved_mapping_ref_premium"]
                    if saved in ref_cols:
                        st.session_state["map_ref_premium"] = saved
                if "map_prod_premium" not in st.session_state and "saved_mapping_prod_premium" in st.session_state:
                    saved = st.session_state["saved_mapping_prod_premium"]
                    if saved in prod_cols:
                        st.session_state["map_prod_premium"] = saved
                if "ws_tolerance" not in st.session_state and "saved_mapping_tolerance" in st.session_state:
                    st.session_state["ws_tolerance"] = st.session_state["saved_mapping_tolerance"]

                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    id_col = st.selectbox("Colonne cl\u00e9 (ID)", options=ref_cols, key="map_id_col")
                    run_domaine = run_data.get("domaine", "Prime")
                    ref_premium_col = st.selectbox(f"{run_domaine} Référence", options=ref_cols, key="map_ref_premium")
                with col_m2:
                    prod_premium_col = st.selectbox(f"{run_domaine} Production", options=prod_cols, key="map_prod_premium")
                    lob_thresholds = _get_lob_tolerance(run_data.get("lob_id", ""), run_domaine)
                    policy_tol = lob_thresholds["tolerance_pct"]
                    tol_kwargs = {"label": "Tol\u00e9rance (%)", "min_value": 0.0, "max_value": 20.0, "step": 0.5, "key": "ws_tolerance"}
                    if "ws_tolerance" not in st.session_state:
                        tol_kwargs["value"] = policy_tol
                    tolerance = st.slider(**tol_kwargs)
                    st.caption(f"📏 Politique de mat\u00e9rialit\u00e9 ({lob_thresholds['lob_label']}) : "
                               f"Alerte \u2265 {lob_thresholds['warning_pct']}% \u00b7 Bloquant \u2265 {lob_thresholds['critical_pct']}%")

                rules = _load_control_rules(run_data.get("lob_id", "LOB_AUTO_PART"), run_domaine)
                if rules:
                    with st.expander(f"\U0001f4cb R\u00e8gles de contr\u00f4le ({len(rules)} actives)", expanded=False):
                        if len(rules) > 10:
                            num_pages = (len(rules) - 1) // 10 + 1
                            selected_page = st.selectbox(
                                "Page des r\u00e8gles",
                                range(1, num_pages + 1),
                                format_func=lambda x: f"Page {x} / {num_pages}",
                                key="page_rules_active"
                            )
                            start_idx = (selected_page - 1) * 10
                            end_idx = start_idx + 10
                            page_rules = rules[start_idx:end_idx]
                        else:
                            page_rules = rules

                        for rule in page_rules:
                            sev_icon = "\U0001f534" if rule.get("severity") == "BLOQUANT" else "\U0001f7e1"
                            mandatory_tag = " \u2014 **Obligatoire**" if rule.get("is_mandatory") else ""
                            domain_tag = f" \u00b7 {rule.get('domain', '')}" if rule.get('domain') else ""
                            st.markdown(f"{sev_icon} **{rule['rule_id']}** \u2014 {rule['label']} [{rule.get('severity', '')}]{mandatory_tag}{domain_tag}")
                            st.caption(f"   {rule.get('description', '')}")
                            st.caption(f"   R\u00e9f. : {rule.get('regulatory_ref', '')} | v{rule.get('version', '1.0')} | Approuv\u00e9e par {rule.get('approved_by', '')}")

                tolerance_decimal = tolerance / 100.0

                if st.button("\u21d2 Lancer la R\u00e9conciliation", use_container_width=True, type="primary"):
                    with st.spinner("Calculs actuariels en cours..."):
                        try:
                            ref_df_path = os.path.join("data/saved_datasets", f"{run_id}_ref.csv")
                            prod_df_path = os.path.join("data/saved_datasets", f"{run_id}_prod.csv")
                            if not os.path.exists(ref_df_path) or not os.path.exists(prod_df_path):
                                raise ValueError("Fichiers de données introuvables sur le disque. Veuillez ré-importer les fichiers à l'étape Importation.")
                                
                            run_file = os.path.join("data/uat_runs", f"{run_id}.json")
                            if not os.path.exists(run_file):
                                raise ValueError("Campagne introuvable (fichier JSON inexistant).")
                            with open(run_file, "r", encoding="utf-8") as rf:
                                run_meta = json.load(rf)
                            expected_ref_hash = run_meta.get("files", {}).get("reference", {}).get("sha256")
                            expected_prod_hash = run_meta.get("files", {}).get("production", {}).get("sha256")
                            
                            with open(ref_df_path, "rb") as f:
                                current_ref_hash = hashlib.sha256(f.read()).hexdigest()
                            with open(prod_df_path, "rb") as f:
                                current_prod_hash = hashlib.sha256(f.read()).hexdigest()
                                
                            if current_ref_hash != expected_ref_hash or current_prod_hash != expected_prod_hash:
                                raise ValueError("🚨 ÉCHEC DU CONTRÔLE D'INTÉGRITÉ : Les fichiers de données sur le disque ont été altérés depuis l'importation. Le calcul de réconciliation est bloqué par mesure de gouvernance Pilier 2.")
                                
                            ref_df = pd.read_csv(ref_df_path)
                            prod_df = pd.read_csv(prod_df_path)

                            mapping = {
                                "key": id_col,
                                "ref_premium": ref_premium_col,
                                "prod_premium": prod_premium_col
                            }
                            merged_df = merge_datasets(ref_df, prod_df, mapping)
                            analyzed_df = calculate_variances(
                                merged_df,
                                ref_col=ref_premium_col,
                                prod_col=prod_premium_col,
                                tolerance=tolerance_decimal,
                                lob_id=run_data.get("lob_id", "LOB_AUTO_PART")
                            )
                            kpis_result = compute_uat_kpis(analyzed_df, tolerance_decimal)
                            anomalies_df = extract_anomalies(analyzed_df, tolerance_decimal)
                            anomalies_list = anomalies_df.to_dict(orient="records")

                            _update_uat_run_results(
                                run_id, run_name, kpis_result, anomalies_list,
                                ref_df=ref_df, prod_df=prod_df
                            )

                            _save_applied_rules(run_id)

                            st.session_state["saved_mapping_id_col"] = id_col
                            st.session_state["saved_mapping_ref_premium"] = ref_premium_col
                            st.session_state["saved_mapping_prod_premium"] = prod_premium_col
                            st.session_state["saved_mapping_tolerance"] = tolerance

                            if _local_modules:
                                _add_audit_entry(
                                    run_id=run_id, run_name=run_name,
                                    role=st.session_state.get("user", {}).get("role", "Actuaire MOA"),
                                    action="CREATED_AND_CALCULATED",
                                    comment=f"Campagne calcul\u00e9e. Taux : {kpis_result.get('success_rate_pct', 0):.2f}%.",
                                    validator_name=st.session_state.get("user", {}).get("name", "Syst\u00e8me")
                                )

                            st.session_state["campaign_step"] = "Analyse"
                            st.success(f"\u2713 R\u00e9conciliation termin\u00e9e ! Taux : {kpis_result.get('success_rate_pct', 0):.2f}%")
                            st.rerun()
                        except Exception as e:
                            import logging
                            logging.getLogger("actuarecette").exception("Erreur r\u00e9conciliation")
                            st.error("Une erreur est survenue lors de la r\u00e9conciliation. V\u00e9rifiez le mapping des colonnes et la qualit\u00e9 des donn\u00e9es.")

        elif st.session_state["campaign_step"] == "Analyse":
            st.markdown("### \u2261 Analyse des r\u00e9sultats")

            if is_readonly:
                st.info("Mode lecture seule \u2014 la campagne a \u00e9t\u00e9 soumise pour validation.")

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Dossiers totaux", kpis.get("total_cases", 0))
            with col2:
                st.metric("Conformes", kpis.get("conform_cases", 0))
            with col3:
                st.metric("Taux", f"{kpis.get('success_rate_pct', 0):.1f} %")
            with col4:
                st.metric("Impact \u20ac", f"{kpis.get('total_absolute_delta_euros', 0):.2f} \u20ac")

            if anomalies:
                st.markdown(f"#### \u26a0 {len(anomalies)} anomalie(s)")
                df_anom = pd.DataFrame(anomalies)
                st.dataframe(df_anom, use_container_width=True, hide_index=True)

                if "abs_deviation" in df_anom.columns:
                    import plotly.express as px
                    fig = px.histogram(df_anom, x="abs_deviation", nbins=20,
                                       labels={"abs_deviation": "\u00c9cart absolu (\u20ac)"},
                                       title="Distribution des \u00e9carts")
                    fig.update_layout(showlegend=False, height=300)
                    st.plotly_chart(fig, use_container_width=True)

                st.markdown("---")
                _render_jira_dialog_popover(run_id, run_name, anomalies, "step3_jira")
            else:
                st.success("\u2714 Aucune anomalie d\u00e9tect\u00e9e.")

            if anomalies and not is_readonly:
                blocking = [a for a in anomalies if a.get("status") == "NON CONFORME"]
                if blocking:
                    st.markdown("---")
                    st.markdown(f"##### \u26a0 Justification par anomalie bloquante ({len(blocking)})")
                    st.caption("Chaque anomalie bloquante doit \u00eatre justifi\u00e9e individuellement.")
                    existing_anom_justifs = run_data.get("anomaly_justifications", {})
                    for idx_b, bl in enumerate(blocking):
                        bl_id = str(bl.get("policy_id", bl.get("id", f"anomaly_{idx_b}")))
                        bl_label = f"{bl_id} \u2014 \u00c9cart: {bl.get('abs_deviation', 'N/A')}\u20ac"
                        st.text_input(
                            bl_label,
                            value=existing_anom_justifs.get(bl_id, ""),
                            key=f"anom_justif_{bl_id}",
                            placeholder="Cause identifi\u00e9e et action corrective...",
                        )
            elif anomalies and is_readonly:
                existing_anom_justifs = run_data.get("anomaly_justifications", {})
                if existing_anom_justifs:
                    st.markdown("---")
                    st.markdown("##### \u26a0 Justifications par anomalie bloquante")
                    for anom_id, justif_text in existing_anom_justifs.items():
                        if justif_text.strip():
                            st.markdown(f"**{anom_id}** : {justif_text}")

            if not is_readonly:
                st.markdown("---")
                st.markdown("##### \u270d Justification des \u00e9carts constat\u00e9s")
                existing_justif = run_data.get("justification", {}).get("text", "")
                justif_text = st.text_area(
                    "Documentez les causes identifi\u00e9es et les actions correctives :",
                    value=existing_justif, key="ecart_justification",
                    help="Ce champ sera inclus dans le rapport de certification ACPR.",
                    height=120
                )
            else:
                saved_justif = run_data.get("justification", {}).get("text", "")
                if saved_justif:
                    st.markdown("---")
                    st.markdown("##### \u270d Justification des \u00e9carts")
                    st.info(saved_justif)
                    justif_author = run_data.get("justification", {}).get("author", "")
                    if justif_author:
                        st.caption(f"Par {justif_author}")

            if not is_readonly:
                st.markdown("---")
                st.markdown("##### \u26a0 Limites et insuffisances identifi\u00e9es")
                st.caption("S\u00e9lectionnez les cat\u00e9gories applicables \u00e0 cette campagne.")
                existing_lims = run_data.get("limitations", [])
                existing_cats = [l.get("category", "") for l in existing_lims]
                selected_lim_cats = []
                for idx_lc, cat in enumerate(LIMITATION_CATEGORIES):
                    checked = cat in existing_cats
                    val = st.checkbox(cat, value=checked, key=f"lim_cat_{idx_lc}")
                    if val:
                        selected_lim_cats.append(cat)
                existing_lim_comment = run_data.get("limitations_comment", "")
                lim_comment = st.text_input(
                    "Commentaire suppl\u00e9mentaire :",
                    value=existing_lim_comment,
                    key="lim_comment",
                    placeholder="Pr\u00e9cisez les limitations si n\u00e9cessaire..."
                )
            else:
                saved_lims = run_data.get("limitations", [])
                if saved_lims:
                    st.markdown("---")
                    st.markdown("##### \u26a0 Limites et insuffisances identifi\u00e9es")
                    for lim in saved_lims:
                        cat = lim.get("category", "")
                        comment = lim.get("comment", "")
                        text = f"\u2022 **{cat}**"
                        if comment:
                            text += f" \u2014 {comment}"
                        st.markdown(text)

            if campaign_status in ["Brouillon", "En analyse", "Rejet\u00e9"] and not is_readonly:
                if st.button("\u2714 Soumettre pour Validation (Maker \u2192 Checker)", use_container_width=True, type="primary"):
                    if anomalies:
                        blocking = [a for a in anomalies if a.get("status") == "NON CONFORME"]
                        if blocking:
                            anom_justifs = {}
                            for idx_b, bl in enumerate(blocking):
                                bl_id = str(bl.get("policy_id", bl.get("id", f"anomaly_{idx_b}")))
                                val = st.session_state.get(f"anom_justif_{bl_id}", "")
                                if val.strip():
                                    anom_justifs[bl_id] = val.strip()
                            if anom_justifs:
                                _save_anomaly_justifications(run_id, anom_justifs)
                    justif_val = st.session_state.get("ecart_justification", "")
                    if justif_val.strip():
                        _save_justification(run_id, justif_val)
                    if selected_lim_cats:
                        _save_limitations(run_id, selected_lim_cats,
                                          st.session_state.get("lim_comment", ""))
                    _update_run_status(run_id, "SUBMITTED_FOR_VALIDATION")
                    if _local_modules:
                        _add_audit_entry(
                            run_id=run_id, run_name=run_name,
                            role=st.session_state.get("user", {}).get("role", "Actuaire MOA"),
                            action="SUBMITTED_FOR_VALIDATION",
                            comment="Campagne soumise pour certification Maker→Checker.",
                            validator_name=st.session_state.get("user", {}).get("name", "Système")
                        )
                    st.session_state["campaign_step"] = "Certification"
                    st.rerun()

        elif st.session_state["campaign_step"] == "Certification":
            st.markdown("### ✔ Certification Maker-Checker")

            user_data = st.session_state.get("user", {})
            user_role = user_data.get("role", "Actuaire MOA")
            user_name = user_data.get("name", "Système")
            user_sso = user_data.get("sso", "")
            maker_sso = run_data.get("maker_sso", run_data.get("metadata", {}).get("created_by", ""))
            fatal_count = kpis.get("fatal_defects", 0)
            needs_approver = fatal_count > 0

            if campaign_status == "Prêt pour validation":
                if user_role in ("Validateur", "Responsable MOA") and user_sso != maker_sso:
                    st.markdown("#### 📋 Checklist de vérification")
                    checklist_items = _load_checker_checklist(run_data.get("lob_id", ""))
                    checked_items = []
                    if checklist_items:
                        for idx_ck, item_label in enumerate(checklist_items):
                            val = st.checkbox(item_label, key=f"checker_ck_{idx_ck}")
                            if val:
                                checked_items.append(idx_ck)
                        all_checked = len(checked_items) == len(checklist_items)
                        if not all_checked:
                            st.warning(f"⚠ {len(checklist_items) - len(checked_items)} point(s) non validé(s). La checklist doit être complète.")
                    else:
                        all_checked = True

                    st.markdown("---")
                    if anomalies:
                        st.markdown("---")
                        _render_jira_dialog_popover(run_id, run_name, anomalies, "step4_checker_jira")
                    st.markdown("---")
                    cert_comment = st.text_area("Commentaire de certification", key="cert_comment",
                                                value="Certification de conformité accordée.")

                    if needs_approver:
                        st.info(f"ℹ Cette campagne contient {fatal_count} anomalie(s) bloquante(s). "
                                "Après votre validation, elle sera transmise au Responsable MOA pour approbation finale.")

                    col_a, col_r = st.columns(2)
                    with col_a:
                        certify_label = "✔ Valider (Checker)" if needs_approver else "✔ Certifier"
                        if st.button(certify_label, type="primary", use_container_width=True,
                                     key="certify_btn", disabled=not all_checked):
                            comment = st.session_state.get("cert_comment", "Certification de conformité accordée.")
                            _save_checker_review(run_id, checklist_items, checked_items, comment)
                            _update_run_checker(run_id, user_sso, user_name)
                            if needs_approver:
                                _update_run_status(run_id, "PENDING_APPROVAL")
                                if _local_modules:
                                    _add_audit_entry(
                                        run_id=run_id, run_name=run_name,
                                        role=user_role, action="PENDING_APPROVAL",
                                        comment=f"Validé par Checker. Escalade Approver requise ({fatal_count} bloquant(s)). {comment}",
                                        validator_name=user_name
                                    )
                                st.toast(f"✔ Validé par {user_name}. En attente d'approbation.")
                            else:
                                cert_num = _generate_certification_number(run_data.get("lob_id", ""))
                                _save_certification_number(run_id, cert_num)
                                _update_run_status(run_id, "APPROVED")
                                _lock_run(run_id)
                                if _local_modules:
                                    _add_audit_entry(
                                        run_id=run_id, run_name=run_name,
                                        role=user_role, action="APPROVED",
                                        comment=f"N° {cert_num}. {comment}", validator_name=user_name
                                    )
                                st.toast(f"✔ Campagne certifiée : {cert_num}")
                            _clear_workspace_state()
                            st.cache_data.clear()
                            st.rerun()
                    with col_r:
                        if st.button("✖ Rejeter", type="secondary", use_container_width=True, key="reject_btn"):
                            rejection_reason = st.session_state.get("cert_comment", "").strip()
                            if len(rejection_reason) < 10:
                                st.error("❌ Le commentaire de rejet doit contenir au moins 10 caractères.")
                            elif rejection_reason == "Certification de conformité accordée.":
                                st.error("❌ Veuillez modifier le commentaire par défaut pour indiquer la raison du rejet.")
                            else:
                                _save_checker_review(run_id, checklist_items, checked_items, rejection_reason)
                                _save_rejection_comment(run_id, rejection_reason)
                                _update_run_status(run_id, "REJECTED")
                                _update_run_checker(run_id, user_sso, user_name)
                                if _local_modules:
                                    _add_audit_entry(
                                        run_id=run_id, run_name=run_name,
                                        role=user_role, action="REJECTED",
                                        comment=rejection_reason, validator_name=user_name
                                    )
                                st.toast(f"✖ Campagne {run_id} rejetée.", icon="❌")
                                _clear_workspace_state()
                                st.cache_data.clear()
                                st.rerun()

                elif user_sso == maker_sso:
                    st.info("ℹ Vous êtes le Maker de cette campagne. Règle Maker≠Checker : "
                            "vous ne pouvez pas certifier votre propre campagne.")
                else:
                    st.info(f"ℹ Votre rôle ({user_role}) ne permet pas la certification. "
                            "Seuls les Validateurs et Responsables MOA peuvent certifier.")

            elif campaign_status == "En attente approbation":
                st.markdown("#### 🛡 Approbation Responsable MOA requise")
                st.warning(f"Cette campagne contient {fatal_count} anomalie(s) bloquante(s). "
                           "Le Checker a validé — l'approbation finale du Responsable MOA est nécessaire.")

                checker_review = run_data.get("checker_review", {})
                if checker_review:
                    with st.expander("📋 Revue Checker", expanded=True):
                        for item in checker_review.get("items", []):
                            icon = "✅" if item.get("checked") else "❌"
                            st.markdown(f"{icon} {item.get('label', '')}")
                        st.caption(f"Par {checker_review.get('reviewer', '')} le "
                                   f"{checker_review.get('timestamp', '')[:10]}")
                        if checker_review.get("comment"):
                            st.info(f"Commentaire : {checker_review['comment']}")

                checker_sso = run_data.get("checker_sso", "")
                if user_role == "Responsable MOA" and user_sso != maker_sso and user_sso != checker_sso:
                    if anomalies:
                        st.markdown("---")
                        _render_jira_dialog_popover(run_id, run_name, anomalies, "step4_approver_jira")
                        st.markdown("---")
                    approver_comment = st.text_area("Commentaire d'approbation", key="approver_comment",
                                                    value="Approbation accordée après examen des anomalies bloquantes.")
                    col_ap, col_rj = st.columns(2)
                    with col_ap:
                        if st.button("✔ Approuver (Final)", type="primary", use_container_width=True, key="approve_final_btn"):
                            comment = st.session_state.get("approver_comment", "")
                            cert_num = _generate_certification_number(run_data.get("lob_id", ""))
                            _save_certification_number(run_id, cert_num)
                            _update_run_status(run_id, "FINAL_APPROVED")
                            _update_run_approver(run_id, user_sso, user_name)
                            _lock_run(run_id)
                            if _local_modules:
                                _add_audit_entry(
                                    run_id=run_id, run_name=run_name,
                                    role=user_role, action="FINAL_APPROVED",
                                    comment=f"N° {cert_num}. Approbation finale. {comment}", validator_name=user_name
                                )
                            st.toast(f"✔ Campagne approuvée : {cert_num}")
                            _clear_workspace_state()
                            st.cache_data.clear()
                            st.rerun()
                    with col_rj:
                        if st.button("↩ Renvoyer au Checker", type="secondary", use_container_width=True, key="renvoi_btn"):
                            _update_run_status(run_id, "SUBMITTED_FOR_VALIDATION")
                            if _local_modules:
                                _add_audit_entry(
                                    run_id=run_id, run_name=run_name,
                                    role=user_role, action="SUBMITTED_FOR_VALIDATION",
                                    comment=f"Renvoyé au Checker par {user_name}.", validator_name=user_name
                                )
                            st.toast("↩ Campagne renvoyée au Checker.", icon="ℹ")
                            _clear_workspace_state()
                            st.cache_data.clear()
                            st.rerun()
                elif user_sso == maker_sso:
                    st.info("ℹ Vous êtes le Maker. Vous ne pouvez pas approuver votre propre campagne.")
                elif user_sso == checker_sso:
                    st.info("ℹ Vous êtes le Checker. Règle Checker≠Approver : "
                            "l'approbation doit être faite par un autre Responsable MOA.")
                else:
                    st.info(f"ℹ Votre rôle ({user_role}) ne permet pas l'approbation finale. "
                            "Seul le Responsable MOA peut approuver.")

            elif campaign_status in ["Certifié", "Certifié avec réserves", "Rejeté"]:
                if campaign_status == "Rejeté":
                    st.error(f"✖ Cette campagne a été rejetée.")
                else:
                    st.success(f"✔ Campagne certifiée.")
                    if run_data.get("certification_number"):
                        st.markdown(f"**N\u00b0 de certification : `{run_data['certification_number']}`**")
                    if run_data.get("is_locked"):
                        st.caption(f"🔒 Campagne verrouillée le {run_data.get('locked_at', '')[:10]} "
                                   f"| Hash : `{run_data.get('integrity_hash', '')[:16]}...`")

                checker_review = run_data.get("checker_review", {})
                if checker_review:
                    with st.expander("📋 Revue Checker"):
                        for item in checker_review.get("items", []):
                            icon = "✅" if item.get("checked") else "❌"
                            st.markdown(f"{icon} {item.get('label', '')}")
                        st.caption(f"Par {checker_review.get('reviewer', '')} le "
                                   f"{checker_review.get('timestamp', '')[:10]}")

                if run_data.get("approver_name"):
                    st.caption(f"Approuvé par : {run_data['approver_name']}")
            else:
                st.info("ℹ Cette campagne n'est pas encore prête pour la certification. "
                        "Soumettez-la depuis l'étape Analyse.")

            st.markdown("---")
            st.markdown("#### ⬆ Exports")
            col_e1, col_e2 = st.columns(2)
            with col_e1:
                if st.button("☐ Préparer le rapport PDF", use_container_width=True, key="prep_pdf"):
                    try:
                        audit_entries = _fetch_audit_trail(user_headers)

                        gov_data = {
                            "certification_number": run_data.get("certification_number", ""),
                            "periode_arrete": run_data.get("periode_arrete", ""),
                            "applied_rules": run_data.get("applied_rules", []),
                            "limitations": run_data.get("limitations", []),
                            "integrity_hash": run_data.get("integrity_hash", ""),
                            "checker_name": run_data.get("checker_name", ""),
                            "approver_name": run_data.get("approver_name", ""),
                            "maker_name": run_data.get("maker_name", ""),
                        }
                        pdf_bytes = _get_pdf_report_bytes(run_id, run_name, kpis, anomalies, audit_entries, governance_data=gov_data)
                        st.session_state["pdf_export_bytes"] = pdf_bytes
                        st.session_state["pdf_export_run_id"] = run_id
                    except Exception as e:
                        import logging
                        logging.getLogger("actuarecette").exception("Erreur export PDF")
                        st.error("Impossible de générer le rapport PDF. Réessayez ultérieurement.")
                if st.session_state.get("pdf_export_bytes") and st.session_state.get("pdf_export_run_id") == run_id:
                    st.download_button(
                        "⬇ Télécharger le PDF",
                        data=st.session_state["pdf_export_bytes"],
                        file_name=f"rapport_{run_id}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        key="dl_pdf",
                    )
            with col_e2:
                if _local_modules:
                    if st.button("☰ Préparer le Kit Témoin ZIP", use_container_width=True, key="prep_zip"):
                        try:
                            zip_bytes = generate_witness_zip("data/uat_runs", run_id)
                            st.session_state["zip_export_bytes"] = zip_bytes
                            st.session_state["zip_export_run_id"] = run_id
                        except Exception as e:
                            import logging
                            logging.getLogger("actuarecette").exception("Erreur export ZIP")
                            st.error("Impossible de générer le kit témoin ZIP. Réessayez ultérieurement.")
                    if st.session_state.get("zip_export_bytes") and st.session_state.get("zip_export_run_id") == run_id:
                        st.download_button(
                            "⬇ Télécharger le ZIP",
                            data=st.session_state["zip_export_bytes"],
                            file_name=f"kit_temoin_{run_id}.zip",
                            mime="application/zip",
                            use_container_width=True,
                            key="dl_zip",
                        )

    else:
        st.html(
            '<h3 style="margin: 0; color: #0F172A;">Portefeuille des Campagnes</h3>'
            '<p style="color: #64748B; font-size: 0.88rem;">Explorez et g\u00e9rez vos campagnes de validation.</p>'
        )

        user_data = st.session_state.get("user", {})
        if user_data.get("role") == "Actuaire MOA":
            if st.button("\u2795 Nouvelle Campagne", key="new_campaign_btn", use_container_width=True):
                st.session_state["show_create_campaign"] = True

            if st.session_state.get("show_create_campaign"):
                from dashboard.utils.auth import load_lob_registry
                from dashboard.utils.periods import list_all_periods
                
                lob_list = [l for l in load_lob_registry() if l in visible_lobs]
                periods_list = list_all_periods()
                open_periods = [p["code_periode"] for p in periods_list if p["statut"] == "OUVERT"]
                
                with st.form("create_campaign_form"):
                    name_input = st.text_input("Nom de la campagne :", placeholder="Ex: Réconciliation Auto T2 2026")
                    col_lob, col_dom = st.columns(2)
                    with col_lob:
                        lob_input = st.selectbox("Produit (LOB) :", options=lob_list,
                                                 help="Sélection obligatoire. Si votre produit n'est pas dans la liste, contactez un administrateur.")
                    with col_dom:
                        domaine_input = st.selectbox("Domaine m\u00e9tier :", options=DOMAINES_METIER,
                                                      help="Type de donn\u00e9es r\u00e9concili\u00e9es : Prime, Sinistre, R\u00e9serve, Contrat ou R\u00e9assurance.")
                    
                    if not open_periods:
                        st.warning("🔒 Aucune période d'arrêté n'est actuellement ouverte dans le référentiel. Contactez votre Responsable MOA.")
                        periode_input = None
                    else:
                        periode_input = st.selectbox("Période d'arrêté * :", options=open_periods,
                                                     help="Période comptable officielle couverte par cette campagne.")
                    
                    submit = st.form_submit_button("Initialiser le Brouillon")
                    if submit:
                        if not name_input:
                            st.error("Le nom de la campagne est obligatoire.")
                        elif not lob_input:
                            st.error("Le produit (LOB) est obligatoire.")
                        elif not periode_input:
                            st.error("La p\u00e9riode d'arr\u00eat\u00e9 est obligatoire (aucune période ouverte disponible).")
                        else:
                            new_id = _create_draft_campaign(name_input, lob_input, periode_input, domaine=domaine_input)
                            st.session_state["selected_run_id"] = new_id
                            st.session_state["campaign_step"] = "Importation"
                            st.session_state["show_create_campaign"] = False
                            st.success("\u2713 Brouillon cr\u00e9\u00e9 !")
                            st.rerun()

        st.markdown("---")

        history = _fetch_run_history(user_headers)
        history = filter_runs_by_lobs(history, visible_lobs)

        audit_trail = _fetch_audit_trail(user_headers)

        if history and user_data.get("role") == "Actuaire MOA":
            brouillons = [r for r in history if _get_campaign_status(r.get("run_id", ""), user_headers, audit_trail) == "Brouillon"]
            if brouillons:
                if st.button(f"🧹 Purger les {len(brouillons)} brouillon(s)", key="purge_drafts_btn"):
                    st.session_state["confirm_purge_drafts"] = True
                if st.session_state.get("confirm_purge_drafts"):
                    st.warning(f"Supprimer {len(brouillons)} brouillon(s) ? Cette action est irreversible.")
                    col_yes, col_no = st.columns(2)
                    with col_yes:
                        if st.button("Confirmer la purge", key="confirm_purge_yes", type="primary"):
                            for r in brouillons:
                                _delete_run(r.get("run_id", ""))
                            st.session_state["confirm_purge_drafts"] = False
                            st.success(f"{len(brouillons)} brouillon(s) supprime(s).")
                            st.rerun()
                    with col_no:
                        if st.button("Annuler", key="confirm_purge_no"):
                            st.session_state["confirm_purge_drafts"] = False
                            st.rerun()

        if not history:
            st.info("Aucune campagne disponible pour vos portefeuilles.")
        else:
            for r in history:
                r_id = r.get("run_id", "")
                r_name = r.get("run_name", "Sans nom")
                success_rate = r.get("success_rate_pct", 0.0)
                fatal_defects = r.get("fatal_defects", 0)
                timestamp_str = r.get("timestamp", "")
                status_desc = _get_campaign_status(r_id, user_headers, audit_trail)

                r_maker = r.get("maker_name", "")
                r_lob = r.get("lob_id", "")

                try:
                    dt = datetime.datetime.fromisoformat(timestamp_str)
                    date_formatted = dt.strftime("%d/%m/%Y")
                except Exception:
                    date_formatted = timestamp_str

                _render_campaign_track(r_name, r_id, date_formatted, status_desc, success_rate, fatal_defects,
                                       maker_name=r_maker, lob_id=r_lob)

                can_delete = status_desc in ["Brouillon", "En analyse"] and user_data.get("role") == "Actuaire MOA"
                if can_delete:
                    _, col_open, col_del = st.columns([7, 3, 2])
                else:
                    _, col_open = st.columns([9, 3])
                    col_del = None

                with col_open:
                    if st.button("\u25ce Ouvrir", key=f"open_{r_id}", use_container_width=True):
                        st.session_state["selected_run_id"] = r_id
                        st.session_state["campaign_step"] = "Importation" if status_desc == "Brouillon" else "Analyse"
                        st.rerun()

                if col_del is not None:
                    with col_del:
                        if st.button("\U0001f5d1\ufe0f", key=f"del_{r_id}", use_container_width=True, help="Supprimer cette campagne"):
                            st.session_state[f"confirm_delete_{r_id}"] = True

                if st.session_state.get(f"confirm_delete_{r_id}"):
                    st.warning(f"Supprimer la campagne '{r_name}' ? Cette action est irréversible.")
                    col_y, col_n, _ = st.columns([2, 2, 8])
                    with col_y:
                        if st.button("Oui, supprimer", key=f"yes_del_{r_id}", type="primary"):
                            _delete_run(r_id)
                            st.session_state.pop(f"confirm_delete_{r_id}", None)
                            st.success(f"Campagne '{r_name}' supprimée.")
                            st.rerun()
                    with col_n:
                        if st.button("Annuler", key=f"no_del_{r_id}"):
                            st.session_state.pop(f"confirm_delete_{r_id}", None)
                            st.rerun()

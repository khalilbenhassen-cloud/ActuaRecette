"""
Serveur FastAPI ActuaRecette
============================

Ce module configure et démarre le serveur d'API REST d'ActuaRecette.
Il expose les routes clés pour l'ingestion, le profilage, la réconciliation actuarielle,
la persistance d'historique, et l'exportation vers Jira.

Auteur: Senior Backend Engineer & Expert en Architecture API REST (FastAPI)
Version: 1.0.0
"""

import os
import sys
import json
import shutil
import datetime
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from pydantic import ValidationError

# Middleware d'identité SSO (Phase 1 — v6.0)
from api.api_auth_middleware import IdentityMiddleware, get_current_user

# ARCH-08: Keep sys.path manipulation here — needed for API server entry point
# when launched directly (e.g. uvicorn api.main:app). Dashboard modules should
# NOT duplicate this; they should rely on PYTHONPATH set externally.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Importations des modules cœurs
from src.data_profiler import load_csv, validate_column_mapping, check_data_quality
from src.variance_analyzer import merge_datasets, calculate_variances, compute_uat_kpis, extract_anomalies
from src.anomaly_manager import (
    save_uat_run, 
    load_run_history, 
    generate_jira_markdown,
    save_scenario,
    load_scenarios,
    generate_stress_portfolio,
    compare_uat_runs,
    add_global_audit_entry,
    load_global_audit_trail,
    translate_technical_error,
    generate_witness_zip,
    delete_uat_run
)

# Importations des schémas Pydantic
from api.schemas import (
    ColumnMappingSchema, 
    JiraBugReportRequestSchema, 
    JiraBugReportResponseSchema, 
    RunHistorySummarySchema,
    ScenarioSchema,
    ComparisonResponseSchema,
    RunValidationRequestSchema,
    AuditEntrySchema,
    # Phase 2b — Workflow Maker-Checker
    SubmitRunRequest,
    CertifyRunRequest,
    RejectRunRequest,
    PendingValidationItem,
    VALID_RUN_STATUSES,
)
from api.api_auth_middleware import get_visible_lobs

# Route modules
from api.routes.sessions import router as sessions_router
from api.routes.workflow import router as workflow_router
from api.routes.exports import router as exports_router
from api.routes.referentiel import router as referentiel_router

# Répertoire de persistance des runs UAT par défaut
HISTORY_DIR = "data/uat_runs"
SCENARIOS_DIR = "data/scenarios"
TEMP_UPLOAD_DIR = "temp_uploads"

# DATA-06: Replaced deprecated @app.on_event("startup") with lifespan pattern
# (deprecated since FastAPI 0.93)
@asynccontextmanager
async def lifespan(app):
    # Startup: configure data directories and purge temp files
    os.makedirs(HISTORY_DIR, exist_ok=True)
    os.makedirs(SCENARIOS_DIR, exist_ok=True)
    os.makedirs(TEMP_UPLOAD_DIR, exist_ok=True)

    # Purge des reliquats de crashs ou d'arrêts brutaux précédents
    for filename in os.listdir(TEMP_UPLOAD_DIR):
        file_path = os.path.join(TEMP_UPLOAD_DIR, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception:
            pass

    yield
    # Shutdown (cleanup if needed)

# Initialisation de l'application FastAPI
app = FastAPI(
    title="ActuaRecette API",
    description="Moteur d'ingestion et de réconciliation financière pour les audits actuariels (MOA & DSI).",
    version="6.0.0",
    lifespan=lifespan,
)

# Middleware d'identité : extrait X-User-SSO, valide les path params (cf. §6.1b #8)
app.add_middleware(IdentityMiddleware)

# CORS: restrict to same-origin by default (dashboard runs on same host)
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["X-User-SSO", "X-User-Name", "X-User-Role", "X-User-LOBs"],
)

# (HISTORY_DIR, SCENARIOS_DIR, TEMP_UPLOAD_DIR defined above, before lifespan)

def get_session_upload_dir(session_id: str) -> str:
    """T22: Return a session-isolated temp upload directory."""
    import uuid as _uuid
    safe_id = session_id.replace("..", "").replace("/", "").replace("\\", "")[:32]
    path = os.path.join(TEMP_UPLOAD_DIR, safe_id)
    os.makedirs(path, exist_ok=True)
    return path

# DATA-06: startup_event() logic has been migrated to the lifespan() context
# manager above (see FastAPI init). The @app.on_event("startup") decorator
# is deprecated since FastAPI 0.93.

def _extract_quality_mapping(columns: List[str], id_col: str, premium_col: str) -> Dict[str, str]:
    """
    Détecte automatiquement d'autres colonnes d'intérêt (âge, crm, email) 
    présentes physiquement dans le fichier pour l'audit de qualité du profiler.
    """
    mapping = {
        "id_assure": id_col,
        "prime_technique": premium_col
    }
    for col in columns:
        col_lower = col.lower()
        if "age" in col_lower or "âge" in col_lower:
            mapping["age_assure"] = col
        elif any(kw in col_lower for kw in ["bonus", "malus", "crm", "coef"]):
            mapping["bonus_malus"] = col
        elif "email" in col_lower or "mail" in col_lower:
            mapping["email"] = col
    return mapping

@app.get("/health")
def health_check():
    """
    Endpoint DevOps pour la surveillance de l'état de santé du serveur.
    """
    return {"status": "HEALTHY", "version": "1.0.0"}

@app.post("/reconcile")
async def reconcile_campaign(
    request: Request,
    ref_file: UploadFile = File(...),
    prod_file: UploadFile = File(...),
    mapping_json: str = Form(...),
    tolerance: float = Form(0.05),
    run_name: str = Form("Campagne de Recette"),
    domaine: str = Form("Prime")
):
    """
     endpoint principal de réconciliation :
    1. Reçoit les fichiers chargés (référence actuarielle et production DSI).
    2. Valide le dictionnaire de mapping fourni.
    3. Exécute l'audit de qualité (Data Profiler).
    4. Réalise la fusion et calcule les écarts actuariels (Variance Analyzer).
    5. Sauvegarde la campagne de recette dans l'historique local (Anomaly Manager).
    6. Retourne le bilan global avec KPIs, anomalies et alertes de qualité.
    """
    # Génération d'identifiants d'horodatage pour éviter les collisions de fichiers temporaires
    now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    ref_temp_path = os.path.join(TEMP_UPLOAD_DIR, f"temp_{now_str}_ref.csv")
    prod_temp_path = os.path.join(TEMP_UPLOAD_DIR, f"temp_{now_str}_prod.csv")

    try:
        # 1. Sauvegarde des fichiers UploadFile sur le disque pour lecture pandas
        with open(ref_temp_path, "wb") as buffer:
            shutil.copyfileobj(ref_file.file, buffer)
            
        with open(prod_temp_path, "wb") as buffer:
            shutil.copyfileobj(prod_file.file, buffer)

        # 2. Chargement des fichiers CSV via le profiler ultra-robuste
        try:
            ref_df = load_csv(ref_temp_path)
            prod_df = load_csv(prod_temp_path)
        except Exception as csv_error:
            raise HTTPException(
                status_code=400, 
                detail=f"Erreur de lecture d'un fichier CSV : {str(csv_error)}"
            )

        # 3. Parsing et validation du mapping de colonnes avec le schéma Pydantic
        try:
            mapping_dict = json.loads(mapping_json)
            mapping_validated = ColumnMappingSchema(**mapping_dict)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=400, 
                detail="Erreur de format : Le paramètre 'mapping_json' n'est pas un JSON valide."
            )
        except ValidationError as validation_error:
            raise HTTPException(
                status_code=400, 
                detail=f"Validation du mapping échouée : {validation_error.errors()}"
            )

        # 4. Vérification physique des colonnes requises avec validate_column_mapping()
        # Validation pour le fichier de référence actuarielle
        ref_mapping_verify = {
            "id_assure": mapping_validated.id_col,
            "prime_technique": mapping_validated.ref_premium_col
        }
        if mapping_validated.tsca_ref_col and mapping_validated.tsca_ref_col != "[Non Mappé]":
            ref_mapping_verify["tsca_ref"] = mapping_validated.tsca_ref_col
        if mapping_validated.catnat_ref_col and mapping_validated.catnat_ref_col != "[Non Mappé]":
            ref_mapping_verify["catnat_ref"] = mapping_validated.catnat_ref_col

        ref_val = validate_column_mapping(ref_df, ref_mapping_verify)
        if not ref_val["is_valid"]:
            raise HTTPException(
                status_code=400,
                detail=f"Colonnes absentes dans le fichier de référence actuarielle : {ref_val['missing_columns']}"
            )

        # Validation pour le fichier de production DSI
        prod_mapping_verify = {
            "id_assure": mapping_validated.id_col,
            "prime_technique": mapping_validated.prod_premium_col
        }
        if mapping_validated.tsca_prod_col and mapping_validated.tsca_prod_col != "[Non Mappé]":
            prod_mapping_verify["tsca_prod"] = mapping_validated.tsca_prod_col
        if mapping_validated.catnat_prod_col and mapping_validated.catnat_prod_col != "[Non Mappé]":
            prod_mapping_verify["catnat_prod"] = mapping_validated.catnat_prod_col

        prod_val = validate_column_mapping(prod_df, prod_mapping_verify)
        if not prod_val["is_valid"]:
            raise HTTPException(
                status_code=400,
                detail=f"Colonnes absentes dans le fichier de production DSI : {prod_val['missing_columns']}"
            )

        # 5. Audit de la qualité des données (ETL Quality Audit)
        ref_quality_mapping = _extract_quality_mapping(
            list(ref_df.columns), 
            mapping_validated.id_col, 
            mapping_validated.ref_premium_col
        )
        prod_quality_mapping = _extract_quality_mapping(
            list(prod_df.columns), 
            mapping_validated.id_col, 
            mapping_validated.prod_premium_col
        )

        ref_quality = check_data_quality(ref_df, ref_quality_mapping, domaine=domaine)
        prod_quality = check_data_quality(prod_df, prod_quality_mapping, domaine=domaine)

        # Consolidation des alertes qualité
        all_warnings = []
        if ref_quality["has_warnings"]:
            all_warnings.extend([f"[RÉFÉRENCE ACTUARIELLE] {w}" for w in ref_quality["warnings"]])
        if prod_quality["has_warnings"]:
            all_warnings.extend([f"[PRODUCTION DSI] {w}" for w in prod_quality["warnings"]])

        # 6. Jointure et calculs mathématiques
        key_mapping_analyzer = {
            "key": mapping_validated.id_col,
            "ref_premium": mapping_validated.ref_premium_col,
            "prod_premium": mapping_validated.prod_premium_col
        }
        if mapping_validated.tsca_ref_col and mapping_validated.tsca_ref_col != "[Non Mappé]":
            key_mapping_analyzer["tsca_ref"] = mapping_validated.tsca_ref_col
        if mapping_validated.tsca_prod_col and mapping_validated.tsca_prod_col != "[Non Mappé]":
            key_mapping_analyzer["tsca_prod"] = mapping_validated.tsca_prod_col
        if mapping_validated.catnat_ref_col and mapping_validated.catnat_ref_col != "[Non Mappé]":
            key_mapping_analyzer["catnat_ref"] = mapping_validated.catnat_ref_col
        if mapping_validated.catnat_prod_col and mapping_validated.catnat_prod_col != "[Non Mappé]":
            key_mapping_analyzer["catnat_prod"] = mapping_validated.catnat_prod_col

        try:
            merged_df = merge_datasets(ref_df, prod_df, key_mapping_analyzer)
            analyzed_df = calculate_variances(
                merged_df, 
                ref_col=mapping_validated.ref_premium_col, 
                prod_col=mapping_validated.prod_premium_col, 
                tolerance=tolerance
            )
            kpis = compute_uat_kpis(analyzed_df, tolerance)
            anomalies_df = extract_anomalies(analyzed_df, tolerance)
            anomalies_list = anomalies_df.to_dict(orient="records")
        except ValueError as calc_error:
            raise HTTPException(status_code=400, detail=str(calc_error))
        except Exception as error:
            raise HTTPException(
                status_code=500, 
                detail=f"Erreur lors des calculs financiers : {str(error)}"
            )

        # 7. Persistance de la campagne de recette dans l'historique JSON
        try:
            save_uat_run(
                history_dir=HISTORY_DIR,
                run_name=run_name,
                kpis=kpis,
                anomalies=anomalies_list,
                maker_sso=getattr(request.state, "user_sso", "unknown"),
            )
        except Exception as save_error:
            # On loggue l'erreur mais on ne bloque pas le retour de la réponse à la MOA
            print(f"[ERREUR] Échec de la persistance historique : {save_error}")

        # 8. Retour de la réponse complète
        return {
            "status": "SUCCESS",
            "run_name": run_name,
            "kpis": kpis,
            "anomalies": anomalies_list,
            "warnings": all_warnings
        }

    finally:
        # Nettoyage méticuleux des fichiers temporaires
        if os.path.exists(ref_temp_path):
            os.remove(ref_temp_path)
        if os.path.exists(prod_temp_path):
            os.remove(prod_temp_path)

@app.post("/recette/jira", response_model=JiraBugReportResponseSchema)
def generate_jira_bug_report(payload: JiraBugReportRequestSchema):
    """
     endpoint de traduction d'un écart fonctionnel en ticket Jira Markdown.
    """
    try:
        anomaly = payload.anomaly
        input_profile = payload.input_profile

        client_id = anomaly.get("ID_CLIENT") or anomaly.get("id_assure") or "INCONNU"
        bug_title = f"[BUG ACTUARIEL] Écart de tarification détecté sur le client {client_id}"

        # Appel du générateur de ticket Jira
        jira_markdown = generate_jira_markdown(anomaly, input_profile)

        return {
            "status": "SUCCESS",
            "bug_title": bug_title,
            "jira_markdown": jira_markdown
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Erreur lors de la génération du ticket Jira : {str(e)}"
        )

@app.get("/history", response_model=List[RunHistorySummarySchema])
def get_campaign_history(request: Request):
    """
     endpoint pour charger la liste résumé de toutes les campagnes passées.
    """
    try:
        visible_lobs = get_visible_lobs(request)
        history_list = load_run_history(HISTORY_DIR)
        filtered_history = [run for run in history_list if run.get("lob_id", "LOB_AUTO_PART") in visible_lobs]
        return filtered_history
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Erreur lors de la récupération de l'historique : {str(e)}"
        )


@app.get("/history/{run_id}")
def get_campaign_details(run_id: str, request: Request):
    """
     endpoint de consultation détaillée d'une campagne passée.
    """
    file_path = os.path.join(HISTORY_DIR, f"{run_id}.json")
    
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404, 
            detail="Campagne de test introuvable."
        )

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            run_details = json.load(f)
        
        # LOB access check
        visible_lobs = get_visible_lobs(request)
        run_lob = run_details.get("lob_id", "LOB_AUTO_PART")
        if run_lob not in visible_lobs:
            raise HTTPException(
                status_code=403,
                detail=f"Accès refusé : vous n'êtes pas autorisé sur le portefeuille {run_lob}."
            )

        # Recompute signature to check for tampering
        is_signature_valid = True
        try:
            from src.db_adapter import sqlite_connection
            db_path = "data/actuarecette.db"
            if os.path.exists(db_path):
                with sqlite_connection(db_path) as conn:
                    row = conn.execute(
                        "SELECT taux_alignement, prime_a_risque, maker_sso_user, checker_sso_user, date_execution, signature_hash FROM runs_execution WHERE id_run = ?",
                        (run_id,)
                    ).fetchone()
                    if row:
                        stored_sig = row["signature_hash"]
                        if stored_sig:
                            import hashlib
                            def local_get_hash(run_id, success_rate, prime_at_risk, validator, timestamp):
                                _HASH_SALT = "ActuaRecette_v6_audit_2024"
                                payload = f"{run_id}|{success_rate}|{prime_at_risk}|{validator}|{timestamp}"
                                salted = f"{_HASH_SALT}:{payload}"
                                return hashlib.sha256(salted.encode('utf-8')).hexdigest()
                            
                            validator = row["checker_sso_user"] or row["maker_sso_user"]
                            ts_str = str(row["date_execution"])
                            
                            sigs_to_try = [
                                local_get_hash(run_id, row["taux_alignement"], row["prime_a_risque"], validator, ts_str),
                                local_get_hash(run_id, row["taux_alignement"], row["prime_a_risque"], validator, ts_str.replace(" ", "T")),
                                local_get_hash(run_id, row["taux_alignement"], row["prime_a_risque"], validator, ts_str.replace("T", " ")),
                            ]
                            
                            if stored_sig not in sigs_to_try:
                                is_signature_valid = False
        except Exception as sig_err:
            import logging
            logging.getLogger("actuarecette").warning(f"Signature recomputation failed: {sig_err}")

        run_details["is_signature_valid"] = is_signature_valid
            
        return run_details
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Erreur lors de la lecture de la campagne de test : {str(e)}"
        )

@app.delete("/history/{run_id}")
def delete_campaign(run_id: str, request: Request, role: str = "N/A", validator_name: str = "Système"):
    """
    Endpoint pour supprimer définitivement une campagne passée et consigner l'action.
    """
    file_path = os.path.join(HISTORY_DIR, f"{run_id}.json")
    
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404, 
            detail="Campagne de test introuvable."
        )

    # 1. Lire le nom du run avant suppression pour enregistrer dans le registre d'audit
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            run_data = json.load(f)
            run_name = run_data.get("run_name", "Campagne Inconnue")
            
        # LOB access check
        visible_lobs = get_visible_lobs(request)
        run_lob = run_data.get("lob_id", "LOB_AUTO_PART")
        if run_lob not in visible_lobs:
            raise HTTPException(
                status_code=403,
                detail=f"Accès refusé : vous n'êtes pas autorisé sur le portefeuille {run_lob}."
            )
    except HTTPException:
        raise
    except Exception:
        run_name = "Campagne Inconnue"

    # 2. Effectuer la suppression physique
    success = delete_uat_run(HISTORY_DIR, run_id)
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Impossible de supprimer le fichier de la campagne."
        )

    # 3. Consigner la suppression dans le registre d'audit indépendant
    try:
        add_global_audit_entry(
            run_id=run_id,
            run_name=run_name,
            role=role,
            action="DELETED",
            comment="Campagne de recette UAT supprimée définitivement.",
            validator_name=validator_name
        )
    except Exception:
        pass # Ne pas bloquer la suppression en cas de problème de log d'audit

    return {"status": "success", "message": f"Campagne {run_id} supprimée avec succès."}

@app.get("/scenarios", response_model=List[ScenarioSchema])
def get_scenarios():
    """
    Endpoint pour charger tous les modèles de recette enregistrés localement.
    """
    try:
        return load_scenarios(SCENARIOS_DIR)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du chargement des modèles de recette : {str(e)}"
        )

@app.post("/scenarios")
def create_scenario(payload: ScenarioSchema):
    """
    Endpoint pour sauvegarder un nouveau modèle de recette.
    """
    try:
        file_path = save_scenario(
            scenarios_dir=SCENARIOS_DIR,
            name=payload.name,
            description=payload.description,
            mapping=payload.mapping.model_dump(),
            rules=payload.rules
        )
        return {"status": "SUCCESS", "file_path": file_path}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la sauvegarde du modèle de recette : {str(e)}"
        )

@app.get("/compare_runs/{run_id_1}/{run_id_2}", response_model=ComparisonResponseSchema)
def compare_runs_endpoint(run_id_1: str, run_id_2: str, request: Request):
    """
    Endpoint effectuant une comparaison de non-régression différentielle entre deux runs passés.
    """
    try:
        visible_lobs = get_visible_lobs(request)
        for r_id in [run_id_1, run_id_2]:
            file_path = os.path.join(HISTORY_DIR, f"{r_id}.json")
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    run_data = json.load(f)
                run_lob = run_data.get("lob_id", "LOB_AUTO_PART")
                if run_lob not in visible_lobs:
                    raise HTTPException(
                        status_code=403,
                        detail=f"Accès refusé : vous n'êtes pas autorisé sur le portefeuille {run_lob} du run {r_id}."
                    )
        comparison = compare_uat_runs(HISTORY_DIR, run_id_1, run_id_2)
        return comparison
    except HTTPException:
        raise
    except FileNotFoundError as fnf:
        raise HTTPException(status_code=404, detail=str(fnf))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du calcul différentiel de non-régression : {str(e)}"
        )


@app.get("/stress-test/generate")
def generate_stress_portfolio_endpoint():
    """
    Endpoint générant un portefeuille d'assurés aux limites (stress-testing) à 1000 lignes.
    """
    try:
        output_path = "data/stress_portfolio_edge.csv"
        generate_stress_portfolio(output_path, num_records=1000)
        return FileResponse(
            path=output_path,
            filename="portefeuille_stress_testing_1000.csv",
            media_type="text/csv"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la génération du portefeuille de stress-testing : {str(e)}"
        )

@app.post("/runs/{run_id}/validate")
def validate_run_endpoint(run_id: str, payload: RunValidationRequestSchema):
    """
    Endpoint de certification de la campagne de recette (Maker-Checker).
    Enregistre la validation dans le journal d'audit centralisé indépendant et met à jour le run local.
    """
    run_file_path = os.path.join(HISTORY_DIR, f"{run_id}.json")
    if not os.path.exists(run_file_path):
        raise HTTPException(
            status_code=404, 
            detail="La campagne de recette spécifiée est introuvable."
        )
        
    try:
        # 1. Charger le run JSON pour récupérer son nom
        with open(run_file_path, "r", encoding="utf-8") as f:
            run_data = json.load(f)
            
        run_name = run_data.get("run_name", "Campagne de Recette")
        
        # 2. Enregistrer l'entrée dans le journal centralisé
        add_global_audit_entry(
            run_id=run_id,
            run_name=run_name,
            role=payload.role,
            action=payload.action,
            comment=payload.comment,
            validator_name=payload.validator_name
        )
        
        # 3. Mettre à jour l'état de validation dans le fichier JSON du run (pour cohérence locale)
        run_data["validation_status"] = payload.action
        if "audit_trail" not in run_data:
            run_data["audit_trail"] = []
            
        run_data["audit_trail"].append({
            "timestamp": datetime.datetime.now().isoformat(),
            "role": payload.role,
            "action": payload.action,
            "comment": payload.comment,
            "validator_name": payload.validator_name
        })
        
        with open(run_file_path, "w", encoding="utf-8") as f:
            json.dump(run_data, f, indent=2, ensure_ascii=False)
            
        return {"status": "SUCCESS", "message": f"Campagne {run_id} certifiée avec succès : {payload.action}"}
        
    except Exception as e:
        translated = translate_technical_error(e)
        raise HTTPException(
            status_code=500,
            detail=translated
        )

@app.get("/audit-trail", response_model=List[AuditEntrySchema])
def get_audit_trail_endpoint(request: Request):
    """
    Endpoint récupérant l'historique complet du journal centralisé d'audit.
    """
    try:
        visible_lobs = get_visible_lobs(request)
        trail = load_global_audit_trail()
        filtered_trail = [entry for entry in trail if entry.get("lob_id", "LOB_AUTO_PART") in visible_lobs]
        return filtered_trail
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du chargement du journal d'audit : {str(e)}"
        )

@app.get("/api/notifications")
def get_notifications_endpoint(request: Request):
    """
    Récupère les notifications non lues pour l'utilisateur actuellement connecté,
    filtrées par rôle, SSO et cloisonnement LOB.
    """
    try:
        user = get_current_user(request)
        visible_lobs = get_visible_lobs(request)
        from src.notification_manager import get_unread_notifications
        notifs = get_unread_notifications(
            user_role=user.get("role", ""),
            user_sso=user.get("sso", ""),
            visible_lobs=visible_lobs
        )
        return notifs
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du chargement des notifications : {str(e)}"
        )

@app.post("/api/notifications/{notification_id}/read")
def read_notification_endpoint(notification_id: str, request: Request):
    """
    Marque une notification comme lue.
    """
    try:
        from src.notification_manager import mark_as_read
        success = mark_as_read(notification_id)
        if not success:
            raise HTTPException(status_code=404, detail="Notification introuvable")
        return {"status": "SUCCESS"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du marquage de la notification : {str(e)}"
        )

@app.post("/api/notifications/read-all")
def read_all_notifications_endpoint(request: Request):
    """
    Marque toutes les notifications destinées à l'utilisateur comme lues.
    """
    try:
        user = get_current_user(request)
        from src.notification_manager import mark_all_as_read
        count = mark_all_as_read(
            user_role=user.get("role", ""),
            user_sso=user.get("sso", "")
        )
        return {"status": "SUCCESS", "count": count}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors du marquage de toutes les notifications : {str(e)}"
        )

# ===========================================================================
# Include route modules
# ===========================================================================
app.include_router(sessions_router, prefix="")
app.include_router(workflow_router, prefix="")
app.include_router(exports_router, prefix="")
app.include_router(referentiel_router, prefix="")

# Servir les maquettes de tableau de bord de façon statique
from fastapi.staticfiles import StaticFiles
os.makedirs("dashboard/static", exist_ok=True)
app.mount("/static", StaticFiles(directory="dashboard/static"), name="static")
if __name__ == "__main__":
    import uvicorn
    # Lancement du serveur uvicorn de développement
    print("Démarrage du serveur uvicorn pour ActuaRecette...")
    uvicorn.run("api.main:app", host="127.0.0.1", port=8000, reload=True, reload_dirs=["api", "src"])

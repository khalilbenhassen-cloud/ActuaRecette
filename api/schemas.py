"""
Module API Schemas
==================

Ce module définit tous les schémas de validation de données Pydantic (Pydantic v2) 
pour l'API REST de la plateforme de recette actuarielle (ActuaRecette).

Il garantit la validation stricte des structures de requêtes, des configurations de mapping,
des formats de reporting (KPIs), et des payloads de tickets de bug Jira.

Auteur: Senior Software Engineer & API Architect
Version: 1.0.0
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, ValidationError

class ColumnMappingSchema(BaseModel):
    """
    Validation du dictionnaire de mapping fourni par le MOA lors de l'alignement
    des colonnes physiques du fichier avec les concepts métiers.
    """
    id_col: str = Field(
        ..., 
        description="Le nom de la colonne d'identifiant unique d'assuré dans le fichier DSI.",
        min_length=1
    )
    ref_premium_col: str = Field(
        ..., 
        description="Le nom de la colonne représentant la prime de référence actuarielle.",
        min_length=1
    )
    prod_premium_col: str = Field(
        ..., 
        description="Le nom de la colonne représentant la prime calculée par la production DSI.",
        min_length=1
    )
    tsca_ref_col: Optional[str] = Field(
        None,
        description="La colonne facultative de la taxe TSCA dans le fichier de référence actuarielle."
    )
    tsca_prod_col: Optional[str] = Field(
        None,
        description="La colonne facultative de la taxe TSCA dans le fichier de production DSI."
    )
    catnat_ref_col: Optional[str] = Field(
        None,
        description="La colonne facultative de la taxe CatNat dans le fichier de référence actuarielle."
    )
    catnat_prod_col: Optional[str] = Field(
        None,
        description="La colonne facultative de la taxe CatNat dans le fichier de production DSI."
    )

class UATKPIsSchema(BaseModel):
    """
    Validation des indicateurs de performance (KPI) de la campagne de recette
    destinés à être affichés dans l'UI de la MOA.
    """
    total_cases: int = Field(
        ..., 
        description="Nombre de dossiers clients testés au total.", 
        ge=0
    )
    conform_cases: int = Field(
        ..., 
        description="Nombre de dossiers jugés conformes (sous le seuil de tolérance).", 
        ge=0
    )
    fatal_defects: int = Field(
        ..., 
        description="Nombre d'anomalies critiques (au-dessus du seuil de tolérance).", 
        ge=0
    )
    success_rate_pct: float = Field(
        ..., 
        description="Le taux de succès global de la campagne en pourcentage.", 
        ge=0.0, 
        le=100.0
    )
    total_absolute_delta_euros: float = Field(
        ..., 
        description="La somme cumulée en valeur absolue de tous les écarts financiers en Euros.",
        ge=0.0
    )
    max_deviation_euros: float = Field(
        ..., 
        description="L'écart maximal unitaire absolu constaté sur l'ensemble de la campagne.",
        ge=0.0
    )
    final_status: str = Field(
        ..., 
        description="Le statut final prononcé de la recette (CONFORME ou NON CONFORME).",
        min_length=1
    )

class AnomalyRecordSchema(BaseModel):
    """
    Validation des détails d'un dossier client déclaré en anomalie fatale (écart > tolérance).
    """
    ID_CLIENT: Any = Field(
        ..., 
        description="L'identifiant unique de l'assuré (chaîne ou numérique)."
    )
    PRIME_ACTU: float = Field(
        ..., 
        description="La prime de référence attendue par l'actuaire."
    )
    PRIME_DSI: float = Field(
        ..., 
        description="La prime calculée et facturée par le système d'information."
    )
    abs_deviation: float = Field(
        ..., 
        description="L'écart absolu signé (PRIME_DSI - PRIME_ACTU) constaté en Euros."
    )
    rel_deviation_pct: float = Field(
        ..., 
        description="L'écart relatif en pourcentage par rapport à la prime actuarielle de référence."
    )
    anomaly_category: Optional[str] = Field(
        None,
        description="La catégorie actuarielle de l'anomalie détectée."
    )
    suspicion_details: Optional[str] = Field(
        None,
        description="L'explication détaillée ou suspicion du bug actuariel."
    )

class RunHistorySummarySchema(BaseModel):
    """
    Validation de la fiche résumée d'un run pour le listing de l'historique UI.
    Cette structure évite de charger les données détaillées d'anomalies volumineuses.
    """
    run_id: str = Field(
        ..., 
        description="Identifiant unique du run de recette.",
        min_length=1
    )
    run_name: str = Field(
        ..., 
        description="Nom personnalisé attribué par la MOA à cette campagne.",
        min_length=1
    )
    timestamp: str = Field(
        ..., 
        description="Date et heure ISO du déclenchement de la campagne.",
        min_length=1
    )
    success_rate_pct: float = Field(
        ..., 
        description="Taux de succès de la campagne de recette.",
        ge=0.0,
        le=100.0
    )
    fatal_defects: int = Field(
        ..., 
        description="Nombre total d'anomalies critiques survenues pendant le run.",
        ge=0
    )
    total_absolute_delta_euros: float = Field(
        ..., 
        description="Le delta financier d'écart cumulé absolu engendré.",
        ge=0.0
    )
    lob_id: str = Field(
        "LOB_AUTO_PART",
        description="L'identifiant du portefeuille (LOB) associé.",
        min_length=1
    )
    periode_arrete: Optional[str] = Field(
        None,
        description="La période d'arrêté ciblée par cette campagne."
    )
    current_step: Optional[str] = Field(
        None,
        description="L'étape courante du wizard."
    )
    total_cases: Optional[int] = Field(
        0,
        description="Le nombre total de dossiers reconciliés."
    )
    final_status: Optional[str] = Field(
        "Brouillon",
        description="Le statut final de la campagne."
    )

class JiraBugReportRequestSchema(BaseModel):
    """
    Validation du payload envoyé au service d'exportation pour générer un bug Jira.
    """
    anomaly: Dict[str, Any] = Field(
        ..., 
        description="Détails de l'anomalie extraite de variance_analyzer.py."
    )
    input_profile: Dict[str, Any] = Field(
        ..., 
        description="Le payload brut complet des caractéristiques d'assuré."
    )

class JiraBugReportResponseSchema(BaseModel):
    """
    Validation de la réponse contenant la description Jira du bug formatée.
    """
    status: str = Field(
        ..., 
        description="Le statut de l'opération (SUCCESS ou ERROR).",
        min_length=1
    )
    bug_title: str = Field(
        ..., 
        description="Le titre normalisé et explicite suggéré pour le ticket Jira.",
        min_length=1
    )
    jira_markdown: str = Field(
        ..., 
        description="La description complète du bug au format Jira Markdown prêt à être exportée.",
        min_length=1
    )

class ScenarioSchema(BaseModel):
    """
    Validation de la configuration d'un scénario de recette enregistré localement par la MOA.
    """
    scenario_id: Optional[str] = Field(
        None, 
        description="Identifiant unique du scénario/modèle de règles."
    )
    name: str = Field(
        ..., 
        description="Nom convivial donné au scénario de recette.",
        min_length=1
    )
    description: Optional[str] = Field(
        None, 
        description="Description facultative des règles associées."
    )
    mapping: ColumnMappingSchema = Field(
        ..., 
        description="Configuration du mapping des colonnes."
    )
    rules: Dict[str, Any] = Field(
        ..., 
        description="Dictionnaire des seuils de tolérance et interrupteurs configurés."
    )

class ComparisonResponseSchema(BaseModel):
    """
    Validation du rapport différentiel de non-régression entre deux campagnes de recette.
    """
    status: str = Field(
        ..., 
        description="Statut du calcul différentiel."
    )
    run_1_name: str = Field(
        ..., 
        description="Nom de la campagne de référence V1."
    )
    run_2_name: str = Field(
        ..., 
        description="Nom de la campagne de comparaison V2."
    )
    success_rate_1: float = Field(
        ..., 
        description="Taux de conformité de la campagne V1."
    )
    success_rate_2: float = Field(
        ..., 
        description="Taux de conformité de la campagne V2."
    )
    fatal_defects_1: int = Field(
        ..., 
        description="Nombre d'anomalies de la campagne V1."
    )
    fatal_defects_2: int = Field(
        ..., 
        description="Nombre d'anomalies de la campagne V2."
    )
    total_delta_1: float = Field(
        ..., 
        description="Divergence financière cumulée de la campagne V1."
    )
    total_delta_2: float = Field(
        ..., 
        description="Divergence financière cumulée de la campagne V2."
    )
    categories_comparison: Dict[str, Dict[str, int]] = Field(
        ..., 
        description="Comparatif de distribution des anomalies par catégorie."
    )

class RunValidationRequestSchema(BaseModel):
    role: str = Field(..., description="Rôle du validateur (Maker/Checker)")
    action: str = Field(..., description="Action de validation (APPROVED/REJECTED/COMMENT)")
    comment: str = Field(..., description="Commentaire de validation")
    validator_name: str = Field(..., description="Nom du validateur")

class AuditEntrySchema(BaseModel):
    timestamp: str
    run_id: str
    run_name: str
    role: str
    action: str
    comment: str
    validator_name: str
    lob_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Phase 2b — Workflow Maker-Checker schemas
# ---------------------------------------------------------------------------

# Valid run statuses (lifecycle)
VALID_RUN_STATUSES = [
    "BROUILLON",      # Initial state after creation
    "CALCULE",        # After variance analysis
    "SOUMIS",         # Maker submitted for review
    "CERTIFIE",       # Checker approved
    "REJETE",         # Checker rejected (returns to BROUILLON)
    "CERTIFIE_RESERVES",  # Certified with reserves
]

class SubmitRunRequest(BaseModel):
    """Request to submit a run for validation (CALCULE → SOUMIS)."""
    comment: Optional[str] = Field(
        None,
        description="Optional comment from the maker when submitting."
    )

class CertifyRunRequest(BaseModel):
    """Request to certify a run (SOUMIS → CERTIFIE). Checker ≠ Maker enforced server-side."""
    comment: Optional[str] = Field(
        None,
        description="Optional comment from the checker."
    )
    with_reserves: bool = Field(
        False,
        description="True if certifying with reserves (non-blocking anomalies noted)."
    )

class RejectRunRequest(BaseModel):
    """Request to reject a run (SOUMIS → BROUILLON). Reason is mandatory."""
    reason: str = Field(
        ...,
        description="Mandatory rejection reason.",
        min_length=10,
        max_length=2000
    )

class PendingValidationItem(BaseModel):
    """Summary of a run pending validation, shown in the Checker's queue."""
    run_id: str
    run_name: str
    submitted_by: str
    submitted_at: str
    lob_id: str = "LOB_AUTO_PART"
    success_rate_pct: float = 0.0
    fatal_defects: int = 0
    total_delta_euros: float = 0.0

if __name__ == "__main__":
    print("=" * 70)
    print("[DEBUT] DEBUT DU TEST UNITAIRE LOCAL - API SCHEMAS VALIDATOR")
    print("=" * 70)

    try:
        # 1. Test de ColumnMappingSchema
        print("[1/5] Test de ColumnMappingSchema...")
        mapping_data = {
            "id_col": "ID_CLIENT",
            "ref_premium_col": "PRIME_ACTU",
            "prod_premium_col": "PRIME_DSI"
        }
        mapping_instance = ColumnMappingSchema(**mapping_data)
        print("      -> OK : Mapping validé.")
        print(f"      -> Payload sérialisé : {mapping_instance.model_dump()}")
        print("------------------------------------\n")

        # 2. Test de UATKPIsSchema
        print("[2/5] Test de UATKPIsSchema...")
        kpi_data = {
            "total_cases": 120,
            "conform_cases": 118,
            "fatal_defects": 2,
            "success_rate_pct": 98.33,
            "total_absolute_delta_euros": 30.50,
            "max_deviation_euros": 15.20,
            "final_status": "NON CONFORME"
        }
        kpi_instance = UATKPIsSchema(**kpi_data)
        print("      -> OK : KPIs de recette validés.")
        print(f"      -> JSON généré : {kpi_instance.model_dump_json(indent=2)}")
        print("------------------------------------\n")

        # 3. Test de AnomalyRecordSchema & RunHistorySummarySchema
        print("[3/5] Test de AnomalyRecordSchema et RunHistorySummarySchema...")
        anomaly_data = {
            "ID_CLIENT": "C999",
            "PRIME_ACTU": 150.00,
            "PRIME_DSI": 185.50,
            "abs_deviation": 35.50,
            "rel_deviation_pct": 23.67
        }
        anomaly_instance = AnomalyRecordSchema(**anomaly_data)
        print("      -> OK : Enregistrement d'anomalie validé.")
        
        history_data = {
            "run_id": "run_20260529_185000",
            "run_name": "Recette Sprint 5 - Final",
            "timestamp": "2026-05-29T18:50:00",
            "success_rate_pct": 100.00,
            "fatal_defects": 0,
            "total_absolute_delta_euros": 0.00
        }
        history_instance = RunHistorySummarySchema(**history_data)
        print("      -> OK : Fiche historique validée.")
        print("------------------------------------\n")

        # 4. Test des payloads Jira Request/Response
        print("[4/5] Test des payloads Jira Request et Response...")
        jira_request_data = {
            "anomaly": anomaly_instance.model_dump(),
            "input_profile": {
                "age": 22,
                "bonus_malus": 1.0,
                "vehicule": "Citadine"
            }
        }
        jira_req_instance = JiraBugReportRequestSchema(**jira_request_data)
        print("      -> OK : Requête de bug Jira validée.")
        
        jira_resp_data = {
            "status": "SUCCESS",
            "bug_title": "[BUG ACTUARIEL] Écart de tarification détecté sur le client C999",
            "jira_markdown": "h1. Bug Actuariel C999\n\n*Écart de prime de +35.50 €*"
        }
        jira_resp_instance = JiraBugReportResponseSchema(**jira_resp_data)
        print("      -> OK : Réponse de génération Jira validée.")
        print("------------------------------------\n")

        # 5. Simulation volontaire d'une erreur de validation
        print("[5/5] Simulation volontaire d'une ValidationError...")
        bad_kpi_data = {
            "total_cases": "invalid_number_here",  # Devrait être un entier
            "conform_cases": -5,                    # Devrait être positif ou nul (ge=0)
            "fatal_defects": 2,
            "success_rate_pct": 105.00,             # Devrait être <= 100.00
            "total_absolute_delta_euros": 30.50,
            "max_deviation_euros": 15.20,
            "final_status": "NON CONFORME"
        }
        
        try:
            UATKPIsSchema(**bad_kpi_data)
            # Si le code arrive ici, la validation a échoué car elle aurait dû jeter une exception
            raise RuntimeError("La validation a laissé passer un payload invalide à tort.")
        except ValidationError as e:
            print("      -> OK : ValidationError capturée avec succès comme attendu !")
            print("      -> Liste des champs en erreur d'après Pydantic :")
            for error in e.errors():
                print(f"         * Champ '{error['loc'][0]}' : {error['msg']} (valeur reçue : {error.get('input')})")
        
        print("\n[SUCCES] TOUTES LES INSTANCES ET VALIDATIONS DE SCHEMAS ONT ETE EPROUVEES AVEC SUCCES !")

    except Exception as error:
        print(f"\n[ERREUR] ERREUR CRITIQUE PENDANT LES TESTS : {error}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 70)

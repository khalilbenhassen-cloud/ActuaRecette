# api_client.py - Client HTTP centralis\u00e9 pour l'API FastAPI ActuaRecette v6.0
# Remplace les imports directs src/ dans le dashboard (cf. Plan \u00a75.2)
#
# TOUTES les interactions dashboard \u2192 backend passent par ce module.
# Le dashboard ne doit JAMAIS importer directement src/*.

import os
import json
import logging
import requests
from typing import List, Dict, Any, Optional

logger = logging.getLogger("actuarecette.api_client")

# URL de base de l'API (configurable via variable d'environnement)
API_BASE_URL = os.environ.get("ACTUARECETTE_API_URL", "http://127.0.0.1:8000")

class ActuaRecetteAPIClient:
    """
    Client HTTP pour l'API FastAPI d'ActuaRecette.
    Injecte automatiquement les headers d'identit\u00e9 SSO.
    """

    def __init__(self, user_headers: Optional[Dict[str, str]] = None):
        """
        Args:
            user_headers: Headers d'identit\u00e9 SSO (g\u00e9n\u00e9r\u00e9s par UserIdentity.to_headers())
        """
        self._base_url = API_BASE_URL
        self._user_headers = user_headers or {}
        self._session = requests.Session()
        self._session.headers.update(self._user_headers)

    def _url(self, path: str) -> str:
        """Construit l'URL compl\u00e8te."""
        return f"{self._base_url}{path}"

    def _handle_response(self, response: requests.Response) -> Any:
        """Traitement standard des r\u00e9ponses API."""
        if response.status_code >= 400:
            try:
                detail = response.json().get("detail", response.text)
            except Exception:
                detail = response.text
            logger.error(f"API Error {response.status_code}: {detail}")
            raise APIError(response.status_code, detail)
        return response.json()

    # ----- Health -----

    def health(self) -> dict:
        """V\u00e9rifie l'\u00e9tat de sant\u00e9 de l'API."""
        resp = self._session.get(self._url("/health"))
        return self._handle_response(resp)

    # ----- R\u00e9conciliation -----

    def reconcile(self, ref_file_path: str, prod_file_path: str,
                  mapping: dict, tolerance: float = 0.05,
                  run_name: str = "Campagne de Recette") -> dict:
        """
        Lance une r\u00e9conciliation compl\u00e8te.
        Envoie les fichiers CSV et le mapping au moteur.
        """
        with open(ref_file_path, "rb") as ref_f, open(prod_file_path, "rb") as prod_f:
            files = {
                "ref_file": ("ref.csv", ref_f, "text/csv"),
                "prod_file": ("prod.csv", prod_f, "text/csv"),
            }
            data = {
                "mapping_json": json.dumps(mapping),
                "tolerance": str(tolerance),
                "run_name": run_name,
            }
            resp = self._session.post(self._url("/reconcile"), files=files, data=data)
        return self._handle_response(resp)

    # ----- Historique -----

    def get_history(self) -> List[dict]:
        """R\u00e9cup\u00e8re l'historique de toutes les campagnes."""
        resp = self._session.get(self._url("/history"))
        return self._handle_response(resp)

    def get_run_details(self, run_id: str) -> dict:
        """R\u00e9cup\u00e8re le d\u00e9tail complet d'un run."""
        resp = self._session.get(self._url(f"/history/{run_id}"))
        return self._handle_response(resp)

    def delete_run(self, run_id: str) -> dict:
        """Supprime un run."""
        resp = self._session.delete(self._url(f"/history/{run_id}"))
        return self._handle_response(resp)

    # ----- Comparaison -----

    def compare_runs(self, run_id_1: str, run_id_2: str) -> dict:
        """Compare deux runs (non-r\u00e9gression)."""
        resp = self._session.get(self._url(f"/compare_runs/{run_id_1}/{run_id_2}"))
        return self._handle_response(resp)

    # ----- Jira -----

    def generate_jira_ticket(self, anomaly: dict, input_profile: dict) -> dict:
        """G\u00e9n\u00e8re un ticket Jira pour une anomalie."""
        payload = {"anomaly": anomaly, "input_profile": input_profile}
        resp = self._session.post(self._url("/recette/jira"), json=payload)
        return self._handle_response(resp)

    # ----- Sc\u00e9narios -----

    def get_scenarios(self) -> List[dict]:
        """R\u00e9cup\u00e8re tous les mod\u00e8les de recette."""
        resp = self._session.get(self._url("/scenarios"))
        return self._handle_response(resp)

    def save_scenario(self, scenario: dict) -> dict:
        """Sauvegarde un mod\u00e8le de recette."""
        resp = self._session.post(self._url("/scenarios"), json=scenario)
        return self._handle_response(resp)

    # ----- Validation (Maker-Checker) -----

    def validate_run(self, run_id: str, action: str, role: str,
                     comment: str, validator_name: str) -> dict:
        """Certifie ou rejette un run."""
        payload = {
            "action": action,
            "role": role,
            "comment": comment,
            "validator_name": validator_name,
        }
        resp = self._session.post(self._url(f"/runs/{run_id}/validate"), json=payload)
        return self._handle_response(resp)

    # ----- Audit -----

    def get_audit_trail(self) -> List[dict]:
        """R\u00e9cup\u00e8re le journal d'audit complet."""
        resp = self._session.get(self._url("/audit-trail"))
        return self._handle_response(resp)

    # ----- Export -----

    def export_witness_zip(self, run_id: str) -> bytes:
        """T\u00e9l\u00e9charge le kit t\u00e9moin ZIP."""
        resp = self._session.get(self._url(f"/runs/{run_id}/export-witness"))
        if resp.status_code >= 400:
            raise APIError(resp.status_code, "Erreur lors de l'export du kit témoin.")
        return resp.content

    # ----- Stress Test -----

    def generate_stress_portfolio(self) -> bytes:
        """Génère un portefeuille de stress testing."""
        resp = self._session.get(self._url("/stress-test/generate"))
        if resp.status_code >= 400:
            raise APIError(resp.status_code, "Erreur lors de la génération du stress test.")
        return resp.content

    # ----- Phase 2b : Workflow Maker-Checker -----

    def submit_run(self, run_id: str, comment: str = "") -> dict:
        """Soumet un run pour validation (BROUILLON/CALCULÉ → SOUMIS)."""
        payload = {"comment": comment}
        resp = self._session.post(self._url(f"/runs/{run_id}/submit"), json=payload)
        return self._handle_response(resp)

    def certify_run(self, run_id: str, comment: str = "", with_reserves: bool = False) -> dict:
        """Certifie un run (SOUMIS → CERTIFIÉ, Maker≠Checker)."""
        payload = {"comment": comment, "with_reserves": with_reserves}
        resp = self._session.post(self._url(f"/runs/{run_id}/certify"), json=payload)
        return self._handle_response(resp)

    def reject_run(self, run_id: str, reason: str = "") -> dict:
        """Rejette un run (SOUMIS → BROUILLON, motif ≥10 chars)."""
        payload = {"reason": reason}
        resp = self._session.post(self._url(f"/runs/{run_id}/reject"), json=payload)
        return self._handle_response(resp)

    def get_pending_validations(self) -> List[dict]:
        """Retourne la file de validation (runs SOUMIS)."""
        resp = self._session.get(self._url("/pending-validations"))
        return self._handle_response(resp)

    # ----- Phase 2b.4 : Anomaly Categories + Exercices -----

    def get_anomaly_categories(self) -> List[dict]:
        """Retourne le référentiel d'anomalies."""
        resp = self._session.get(self._url("/anomaly-categories"))
        return self._handle_response(resp)

    def get_exercices(self) -> List[dict]:
        """Liste les exercices comptables."""
        resp = self._session.get(self._url("/exercices"))
        return self._handle_response(resp)

    def create_exercice(self, annee: int, mois: int) -> dict:
        """Crée un nouvel exercice (OUVERT)."""
        resp = self._session.post(self._url(f"/exercices?annee={annee}&mois={mois}"))
        return self._handle_response(resp)

    def close_exercice(self, id_exercice: str) -> dict:
        """Transition OUVERT → CLOTURE (Manager only)."""
        resp = self._session.post(self._url(f"/exercices/{id_exercice}/close"))
        return self._handle_response(resp)

    def lock_exercice(self, id_exercice: str) -> dict:
        """Transition CLOTURE → VERROUILLE (Manager only, irréversible)."""
        resp = self._session.post(self._url(f"/exercices/{id_exercice}/lock"))
        return self._handle_response(resp)

    # ----- Phase 2c : Data Quality -----

    def get_dq_report(self, run_id: str) -> dict:
        """Retourne le rapport DQ archivé pour un run."""
        resp = self._session.get(self._url(f"/runs/{run_id}/dq-report"))
        return self._handle_response(resp)

    def compute_dq_report(self, run_id: str) -> dict:
        """Calcule et archive le rapport DQ pour un run."""
        resp = self._session.post(self._url(f"/runs/{run_id}/dq-report"))
        return self._handle_response(resp)

    # ----- Phase 2d : Trends -----

    def get_trends(self, lob_id: str = "all", metric: str = "taux_conformite",
                   from_period: str = "", to_period: str = "") -> dict:
        """Récupère les tendances multi-mois pour un LOB."""
        params = {"metric": metric}
        if from_period:
            params["from"] = from_period
        if to_period:
            params["to"] = to_period
        resp = self._session.get(self._url(f"/trends/{lob_id}"), params=params)
        return self._handle_response(resp)

    # ----- Phase 3 : Export PDF + Kit (T84, T86) -----

    def export_pdf(self, run_id: str) -> bytes:
        """Telecharge le rapport PDF genere cote serveur."""
        resp = self._session.get(self._url(f"/runs/{run_id}/export-pdf"))
        if resp.status_code >= 400:
            raise APIError(resp.status_code, "Erreur lors de l'export PDF.")
        return resp.content

    def export_kit(self, run_id: str) -> bytes:
        """Telecharge le Kit Temoin consolide (ZIP)."""
        resp = self._session.get(self._url(f"/runs/{run_id}/export-kit"))
        if resp.status_code >= 400:
            raise APIError(resp.status_code, "Erreur lors de l'export du kit temoin.")
        return resp.content

    # ----- Phase 3 : Session Heartbeat + Presence (T21, T57, T56) -----

    def heartbeat(self, current_page: str = "") -> dict:
        """Envoie un heartbeat de presence utilisateur."""
        headers = {"X-Current-Page": current_page}
        resp = self._session.post(self._url("/sessions/heartbeat"), headers=headers)
        return self._handle_response(resp)

    def get_active_sessions(self) -> dict:
        """Liste les utilisateurs actuellement connectes."""
        resp = self._session.get(self._url("/sessions/active"))
        return self._handle_response(resp)

    def get_team_activity(self) -> dict:
        """Vue Manager : sessions actives + activite recente."""
        resp = self._session.get(self._url("/team-activity"))
        return self._handle_response(resp)

class APIError(Exception):
    """Exception levée quand l'API retourne une erreur."""
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"API {status_code}: {detail}")

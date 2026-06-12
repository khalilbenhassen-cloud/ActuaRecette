# engine_proxy.py -- Proxy vers les moteurs src/ (Phase 3 - T83)
"""
Ce module centralise TOUS les appels aux moteurs `src/` depuis le dashboard.
Les views importent UNIQUEMENT depuis ce module, jamais directement depuis src/.

Architecture:
    dashboard/views/* -> dashboard/utils/engine_proxy.py -> src/*

En Phase 3+, ce proxy sera remplac\u00e9 par des appels API via api_client.py,
rendant le dashboard compl\u00e8tement d\u00e9coupl\u00e9 du backend.
"""
import os
import sys
import json
import logging
import tempfile
from typing import List, Dict, Any, Optional

import pandas as pd

logger = logging.getLogger("actuarecette.engine_proxy")

from src.db_adapter import sqlite_connection

# ARCH-08: PYTHONPATH must be set externally (via run command or .env),
# not via sys.path manipulation in individual modules.

# ---------------------------------------------------------------------------
# Lazy imports from src/ (fail gracefully if unavailable)
# ---------------------------------------------------------------------------
_modules_loaded = False
try:
    from src.anomaly_manager import (
        save_uat_run,
        load_run_history as _load_run_history,
        load_global_audit_trail as _load_global_audit_trail,
        generate_jira_markdown,
        add_global_audit_entry as _add_audit_entry,
        compare_uat_runs,
        generate_witness_zip as _generate_witness_zip,
        delete_uat_run as _delete_uat_run,
        sync_run_to_db as _sync_run_to_db,
    )
    from src.variance_analyzer import (
        merge_datasets as _merge_datasets,
        calculate_variances as _calculate_variances,
        analyze_premium_drift,
        compute_uat_kpis as _compute_uat_kpis,
        extract_anomalies as _extract_anomalies,
    )
    from src.pdf_generator import generate_pdf_report as _generate_pdf_report
    from src.scenario_manager import (
        load_scenarios as _load_scenarios,
        generate_stress_portfolio as _generate_stress_portfolio,
    )
    from src.notification_manager import (
        create_notification as _create_notification,
        get_unread_notifications as _get_unread_notifications,
        mark_as_read as _mark_as_read,
        mark_all_as_read as _mark_all_as_read,
    )
    _modules_loaded = True
except ImportError as e:
    logger.warning(f"src/ modules unavailable: {e}. API-only mode.")
    _modules_loaded = False

def is_available() -> bool:
    """Check if local engine modules are loaded."""
    return _modules_loaded

# ---------------------------------------------------------------------------
# Sync Wrapper & SQLite synchronization
# ---------------------------------------------------------------------------

class SyncOnCloseFileWrapper:
    """Wrapper de fichier JSON de run UAT pour synchronisation SQL automatique à la fermeture."""
    def __init__(self, file_obj, filepath):
        self._file_obj = file_obj
        self._filepath = filepath

    def __getattr__(self, name):
        return getattr(self._file_obj, name)

    def write(self, *args, **kwargs):
        return self._file_obj.write(*args, **kwargs)

    def close(self):
        self._file_obj.close()
        try:
            run_id = os.path.basename(self._filepath).replace(".json", "")
            sync_run_to_db(run_id)
        except Exception as e:
            logger.warning(f"Echec sync automatique close: {e}")

    def __enter__(self):
        self._file_obj.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        res = self._file_obj.__exit__(exc_type, exc_val, exc_tb)
        try:
            run_id = os.path.basename(self._filepath).replace(".json", "")
            sync_run_to_db(run_id)
        except Exception as e:
            logger.warning(f"Echec sync automatique exit: {e}")
        return res

def sync_run_to_db(run_id: str, data_dir: str = "data/uat_runs") -> None:
    """Synchronise un run JSON de l'historique vers les bases de données SQLite."""
    if _modules_loaded:
        try:
            _sync_run_to_db(run_id, data_dir)
        except Exception as e:
            logger.warning(f"Echec de synchronisation pour {run_id}: {e}")

def delete_uat_run(data_dir: str, run_id: str) -> bool:
    """Supprime un run de l'historique et des bases de données SQLite."""
    if _modules_loaded:
        try:
            return _delete_uat_run(data_dir, run_id)
        except Exception as e:
            logger.warning(f"Echec de suppression de {run_id}: {e}")
    return False

# ---------------------------------------------------------------------------
# Run History
# ---------------------------------------------------------------------------

def load_run_history(data_dir: str = "data/uat_runs") -> List[Dict[str, Any]]:
    """Load run history from local files."""
    if _modules_loaded:
        return _load_run_history(data_dir)
    return []

def load_global_audit_trail(path: str = "data/audit_log.json") -> List[Dict[str, Any]]:
    """Load the global audit trail."""
    if _modules_loaded:
        return _load_global_audit_trail(path)
    return []

def add_audit_entry(
    run_id: str, run_name: str, role: str,
    action: str, comment: str, validator_name: str
) -> None:
    """Add an entry to the global audit trail."""
    if _modules_loaded:
        _add_audit_entry(
            run_id=run_id, run_name=run_name, role=role,
            action=action, comment=comment, validator_name=validator_name,
        )

# ---------------------------------------------------------------------------
# Variance Analysis
# ---------------------------------------------------------------------------

def merge_datasets(ref_df: pd.DataFrame, prod_df: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    """Merge reference and production datasets."""
    if _modules_loaded:
        return _merge_datasets(ref_df, prod_df, mapping)
    raise RuntimeError("Engine modules not loaded. Cannot merge datasets.")

def calculate_variances(
    merged_df: pd.DataFrame,
    ref_col: str, prod_col: str,
    tolerance: float = 0.05,
    lob_id: str = "LOB_AUTO_PART"
) -> pd.DataFrame:
    """Calculate variances between ref and prod."""
    if _modules_loaded:
        return _calculate_variances(merged_df, ref_col=ref_col, prod_col=prod_col, tolerance=tolerance, lob_id=lob_id)
    raise RuntimeError("Engine modules not loaded.")

def compute_uat_kpis(analyzed_df: pd.DataFrame, tolerance: float) -> dict:
    """Compute UAT KPIs from analyzed dataframe."""
    if _modules_loaded:
        return _compute_uat_kpis(analyzed_df, tolerance)
    raise RuntimeError("Engine modules not loaded.")

def extract_anomalies(analyzed_df: pd.DataFrame, tolerance: float) -> pd.DataFrame:
    """Extract anomalies from analyzed dataframe."""
    if _modules_loaded:
        return _extract_anomalies(analyzed_df, tolerance)
    raise RuntimeError("Engine modules not loaded.")

# ---------------------------------------------------------------------------
# PDF Generation
# ---------------------------------------------------------------------------

def generate_pdf_bytes(
    run_id: str, run_name: str, kpis: dict,
    anomalies: list, audit_trail: list,
    governance_data: dict = None
) -> bytes:
    """Generate a PDF report and return it as bytes."""
    if not _modules_loaded:
        raise RuntimeError("Engine modules not loaded.")

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        _generate_pdf_report(run_id, run_name, kpis, anomalies, audit_trail, tmp_path, governance_data=governance_data)
        with open(tmp_path, "rb") as f:
            return f.read()
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

# ---------------------------------------------------------------------------
# Witness Kit
# ---------------------------------------------------------------------------

def generate_witness_zip(data_dir: str, run_id: str) -> bytes:
    """Generate the witness kit ZIP."""
    if _modules_loaded:
        return _generate_witness_zip(data_dir, run_id)
    raise RuntimeError("Engine modules not loaded.")

# ---------------------------------------------------------------------------
# Run Comparison
# ---------------------------------------------------------------------------

def compare_runs(data_dir: str, run_id_1: str, run_id_2: str) -> dict:
    """Compare two UAT runs and return delta metrics."""
    if _modules_loaded:
        return compare_uat_runs(data_dir, run_id_1, run_id_2)
    raise RuntimeError("Engine modules not loaded.")

# ---------------------------------------------------------------------------
# Scenarios & Stress Testing
# ---------------------------------------------------------------------------

def load_scenarios(scenarios_dir: str) -> List[Dict[str, Any]]:
    """Load scenarios from settings."""
    if _modules_loaded:
        return _load_scenarios(scenarios_dir)
    return []

def generate_stress_portfolio(output_path: str, num_records: int = 1000) -> str:
    """Generate a stress test portfolio."""
    if _modules_loaded:
        return _generate_stress_portfolio(output_path, num_records)
    raise RuntimeError("Engine modules not loaded.")

# ---------------------------------------------------------------------------
# Notifications (v6.0)
# ---------------------------------------------------------------------------

def create_notification(
    id_portefeuille: Optional[str],
    destinataire_role: Optional[str],
    destinataire_sso: Optional[str],
    titre: str,
    message: str,
    type: str = "INFO"
) -> str:
    """Create a system notification."""
    if _modules_loaded:
        return _create_notification(id_portefeuille, destinataire_role, destinataire_sso, titre, message, type)
    return ""

def get_unread_notifications(
    user_role: str,
    user_sso: str,
    visible_lobs: List[str]
) -> List[Dict[str, Any]]:
    """Retrieve unread notifications."""
    if _modules_loaded:
        return _get_unread_notifications(user_role, user_sso, visible_lobs)
    return []

def mark_notification_as_read(notification_id: str) -> bool:
    """Mark a notification as read."""
    if _modules_loaded:
        return _mark_as_read(notification_id)
    return False

def mark_all_notifications_as_read(user_role: str, user_sso: str) -> int:
    """Mark all notifications as read for a user."""
    if _modules_loaded:
        return _mark_all_as_read(user_role, user_sso)
    return 0


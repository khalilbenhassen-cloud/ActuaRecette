# models.py — Modèles de données typés pour ActuaRecette
# DATA-04: Remplace les dict non-typés par des dataclasses
"""
Modèles de domaine pour les entités clés d'ActuaRecette.

Usage:
    from src.models import RunKPIs, RunSummary, AuditEntry

    kpis = RunKPIs.from_dict(run_data.get("kpis", {}))
    summary = RunSummary.from_dict(run_data)
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime

@dataclass
class RunKPIs:
    """KPIs d'un run de recette actuarielle."""
    total_cases: int = 0
    conform_cases: int = 0
    success_rate_pct: float = 0.0
    total_absolute_delta_euros: float = 0.0
    fatal_defects: int = 0
    final_status: str = "Brouillon"

    @classmethod
    def from_dict(cls, data: dict) -> "RunKPIs":
        return cls(
            total_cases=int(data.get("total_cases", 0)),
            conform_cases=int(data.get("conform_cases", 0)),
            success_rate_pct=float(data.get("success_rate_pct", 0.0)),
            total_absolute_delta_euros=float(data.get("total_absolute_delta_euros", 0.0)),
            fatal_defects=int(data.get("fatal_defects", 0)),
            final_status=str(data.get("final_status", "Brouillon")),
        )

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def is_conforme(self) -> bool:
        return self.fatal_defects == 0 and self.success_rate_pct == 100.0

@dataclass
class Anomaly:
    """Une anomalie détectée dans un run."""
    id: str = ""
    category: str = ""
    description: str = ""
    field_name: str = ""
    expected_value: Any = None
    actual_value: Any = None
    delta: float = 0.0
    severity: str = "warning"  # "warning", "critical", "info"

    @classmethod
    def from_dict(cls, data: dict) -> "Anomaly":
        return cls(
            id=str(data.get("id", data.get("anomaly_id", ""))),
            category=str(data.get("category", "")),
            description=str(data.get("description", "")),
            field_name=str(data.get("field_name", data.get("champ", ""))),
            expected_value=data.get("expected_value", data.get("valeur_attendue")),
            actual_value=data.get("actual_value", data.get("valeur_produite")),
            delta=float(data.get("delta", data.get("ecart", 0.0))),
            severity=str(data.get("severity", "warning")),
        )

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class RunSummary:
    """Résumé d'un run de recette (vue liste / cockpit)."""
    run_id: str = ""
    run_name: str = "Sans nom"
    timestamp: str = ""
    lob_id: str = ""
    validation_status: str = "BROUILLON"
    kpis: RunKPIs = field(default_factory=RunKPIs)

    @classmethod
    def from_dict(cls, data: dict) -> "RunSummary":
        return cls(
            run_id=str(data.get("run_id", "")),
            run_name=str(data.get("run_name", "Sans nom")),
            timestamp=str(data.get("timestamp", "")),
            lob_id=str(data.get("lob_id", data.get("id_portefeuille", ""))),
            validation_status=str(data.get("validation_status", "BROUILLON")),
            kpis=RunKPIs.from_dict(data.get("kpis", {})),
        )

    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    @property
    def date_short(self) -> str:
        """Retourne la date tronquée (YYYY-MM-DD)."""
        return self.timestamp[:10] if self.timestamp else ""

@dataclass
class AuditEntry:
    """Entrée du journal d'audit."""
    timestamp: str = ""
    action: str = ""
    run_id: str = ""
    run_name: str = ""
    validator_name: str = ""
    validator_sso: str = ""
    role: str = ""
    comment: str = ""
    signature: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "AuditEntry":
        return cls(
            timestamp=str(data.get("timestamp", "")),
            action=str(data.get("action", "")),
            run_id=str(data.get("run_id", "")),
            run_name=str(data.get("run_name", "")),
            validator_name=str(data.get("validator_name", "")),
            validator_sso=str(data.get("validator_sso", "")),
            role=str(data.get("role", "")),
            comment=str(data.get("comment", "")),
            signature=str(data.get("signature", "")),
        )

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class UserIdentity:
    """Identité d'un utilisateur authentifié."""
    sso: str = ""
    name: str = ""
    role: str = ""
    assigned_lobs: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "UserIdentity":
        return cls(
            sso=str(data.get("sso", "")),
            name=str(data.get("name", "")),
            role=str(data.get("role", "")),
            assigned_lobs=list(data.get("assigned_lobs", [])),
        )

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def is_checker(self) -> bool:
        return self.role in ("Validateur", "Responsable MOA")

    @property
    def is_maker(self) -> bool:
        return self.role == "Actuaire MOA"

@dataclass
class TrendSnapshot:
    """Snapshot de tendance pour la page Tendances."""
    periode: str = ""
    id_portefeuille: str = "Global"
    success_rate_pct: float = 0.0
    total_delta_euros: float = 0.0
    total_cases: int = 0
    fatal_defects: int = 0
    version_moteur: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "TrendSnapshot":
        return cls(
            periode=str(data.get("periode", "")),
            id_portefeuille=str(data.get("id_portefeuille", "Global")),
            success_rate_pct=float(data.get("success_rate_pct", 0.0)),
            total_delta_euros=float(data.get("total_delta_euros", 0.0)),
            total_cases=int(data.get("total_cases", 0)),
            fatal_defects=int(data.get("fatal_defects", 0)),
            version_moteur=str(data.get("version_moteur", "")),
        )

    def to_dict(self) -> dict:
        return asdict(self)

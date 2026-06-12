# db_adapter.py — Couche d'abstraction base de données
# ARCH-06 + DATA-01 + DATA-07: Unifie l'accès DuckDB/JSON en une seule interface
"""
Abstraction de la couche de persistance pour ActuaRecette.

Phase 1 : DuckDB en priorité, fallback JSON.
Phase 2+ : Migration possible vers PostgreSQL/SQLite sans changer l'interface.

Usage:
    from src.db_adapter import get_db

    db = get_db()
    db.save_run(run_data)
    history = db.load_history()
"""

import os
import json
import logging
import sqlite3
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
from contextlib import contextmanager

logger = logging.getLogger("actuarecette.db")

class SafeSQLiteConnection:
    """
    Wrapper de connexion SQLite sécurisé.
    Garantit l'activation du mode WAL, des clés étrangères et du busy_timeout (10s).
    Fournit un support contextuel (with) et un destructeur (__del__) pour éviter les fuites.
    """
    def __init__(self, db_path: str):
        self._conn = sqlite3.connect(db_path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA busy_timeout=10000")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.row_factory = sqlite3.Row
        self._closed = False

    def __getattr__(self, name):
        return getattr(self._conn, name)

    def __setattr__(self, name, value):
        if name in ("_conn", "_closed"):
            super().__setattr__(name, value)
        else:
            setattr(self._conn, name, value)

    def close(self):
        if not self._closed:
            try:
                self._conn.close()
            except Exception:
                pass
            self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            try:
                self._conn.rollback()
            except Exception:
                pass
        else:
            try:
                self._conn.commit()
            except Exception:
                pass
        self.close()
        return False

    def __del__(self):
        self.close()

def sqlite_connection(db_path: str) -> SafeSQLiteConnection:
    """Retourne une connexion SQLite sécurisée."""
    return SafeSQLiteConnection(db_path)

# ---------------------------------------------------------------------------
# Interface abstraite (Strategy pattern)
# ---------------------------------------------------------------------------

class RunStore(ABC):
    """Interface abstraite pour la persistance des runs."""

    @abstractmethod
    def save_run(self, run_data: dict, history_dir: str) -> str:
        """Sauvegarde un run et retourne le run_id."""
        ...

    @abstractmethod
    def load_history(self, history_dir: str) -> List[Dict[str, Any]]:
        """Charge l'historique des runs."""
        ...

    @abstractmethod
    def load_run(self, run_id: str, history_dir: str) -> Optional[Dict[str, Any]]:
        """Charge un run spécifique par ID."""
        ...

    @abstractmethod
    def delete_run(self, run_id: str, history_dir: str) -> bool:
        """Supprime un run. Retourne True si supprimé."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Vérifie si le backend est disponible."""
        ...

# ---------------------------------------------------------------------------
# Implémentation JSON (toujours disponible)
# ---------------------------------------------------------------------------

class JsonRunStore(RunStore):
    """Persistance via fichiers JSON (fallback garanti)."""

    def save_run(self, run_data: dict, history_dir: str) -> str:
        run_id = run_data.get("run_id", "unknown")
        os.makedirs(history_dir, exist_ok=True)
        file_path = os.path.join(history_dir, f"{run_id}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(run_data, f, ensure_ascii=False, indent=2, default=str)
        return run_id

    def load_history(self, history_dir: str) -> List[Dict[str, Any]]:
        if not os.path.exists(history_dir):
            return []
        runs = []
        for filename in sorted(os.listdir(history_dir), reverse=True):
            if filename.endswith(".json"):
                try:
                    with open(os.path.join(history_dir, filename), "r", encoding="utf-8") as f:
                        runs.append(json.load(f))
                except Exception:
                    continue
        return runs

    def load_run(self, run_id: str, history_dir: str) -> Optional[Dict[str, Any]]:
        file_path = os.path.join(history_dir, f"{run_id}.json")
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def delete_run(self, run_id: str, history_dir: str) -> bool:
        file_path = os.path.join(history_dir, f"{run_id}.json")
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False

    def is_available(self) -> bool:
        return True

# ---------------------------------------------------------------------------
# Implémentation DuckDB (optionnelle)
# ---------------------------------------------------------------------------

class DuckDBRunStore(RunStore):
    """Persistance via DuckDB (optionnel, enrichit les queries relationnelles).
    
    Délègue toujours au JSON pour l'écriture primaire, et synchronise dans DuckDB
    pour les requêtes analytiques.
    """

    def __init__(self, db_path: str = "data/actuarecette.db"):
        self._db_path = db_path
        self._json_store = JsonRunStore()  # Delegate écriture primaire
        self._duckdb = None
        try:
            import duckdb
            self._duckdb = duckdb
        except ImportError:
            logger.warning("DuckDB non disponible — fallback JSON uniquement")

    def save_run(self, run_data: dict, history_dir: str) -> str:
        # Écriture primaire en JSON (source of truth)
        run_id = self._json_store.save_run(run_data, history_dir)
        # Synchronisation DuckDB (best-effort)
        if self._duckdb:
            try:
                self._sync_to_duckdb(run_data)
            except Exception as e:
                logger.warning(f"Sync DuckDB échouée pour {run_id}: {e}")
        return run_id

    def load_history(self, history_dir: str) -> List[Dict[str, Any]]:
        # Priorité DuckDB pour les queries analytiques
        if self._duckdb:
            try:
                return self._load_history_duckdb()
            except Exception as e:
                logger.warning(f"DuckDB query failed, fallback JSON: {e}")
        return self._json_store.load_history(history_dir)

    def load_run(self, run_id: str, history_dir: str) -> Optional[Dict[str, Any]]:
        return self._json_store.load_run(run_id, history_dir)

    def delete_run(self, run_id: str, history_dir: str) -> bool:
        # Supprimer de DuckDB d'abord
        if self._duckdb:
            try:
                conn = self._duckdb.connect(database=self._db_path)
                conn.execute("DELETE FROM runs WHERE run_id = ?", [run_id])
                conn.close()
            except Exception as e:
                logger.warning(f"DuckDB delete failed for {run_id}: {e}")
        return self._json_store.delete_run(run_id, history_dir)

    def is_available(self) -> bool:
        return self._duckdb is not None

    def _sync_to_duckdb(self, run_data: dict):
        """Synchronise un run dans DuckDB (best-effort)."""
        conn = self._duckdb.connect(database=self._db_path)
        kpis = run_data.get("kpis", {})
        conn.execute("""
            INSERT OR REPLACE INTO runs (
                run_id, run_name, date_execution,
                total_cases, conform_cases, success_rate_pct,
                total_absolute_delta_euros, fatal_defects, final_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            run_data.get("run_id"),
            run_data.get("run_name"),
            run_data.get("timestamp"),
            kpis.get("total_cases", 0),
            kpis.get("conform_cases", 0),
            kpis.get("success_rate_pct", 0.0),
            kpis.get("total_absolute_delta_euros", 0.0),
            kpis.get("fatal_defects", 0),
            kpis.get("final_status", "Brouillon"),
        ])
        conn.close()

    def _load_history_duckdb(self) -> List[Dict[str, Any]]:
        """Charge l'historique depuis DuckDB."""
        conn = self._duckdb.connect(database=self._db_path, read_only=True)
        result = conn.execute("""
            SELECT run_id, run_name, date_execution as timestamp,
                   total_cases, conform_cases, success_rate_pct,
                   total_absolute_delta_euros, fatal_defects, final_status
            FROM runs
            ORDER BY date_execution DESC
        """).fetchall()
        columns = ["run_id", "run_name", "timestamp", "total_cases", "conform_cases",
                    "success_rate_pct", "total_absolute_delta_euros", "fatal_defects", "final_status"]
        conn.close()
        return [
            {"kpis": {k: row[i] for i, k in enumerate(columns) if i >= 3},
             **{k: row[i] for i, k in enumerate(columns) if i < 3}}
            for row in result
        ]

# ---------------------------------------------------------------------------
# Factory — point d'entrée unique
# ---------------------------------------------------------------------------

_default_store: Optional[RunStore] = None

def get_db(db_path: str = "data/actuarecette.db") -> RunStore:
    """Retourne l'instance de RunStore (singleton).
    
    Utilise DuckDB si disponible, sinon fallback JSON.
    Configurable via variable d'env ACTUARECETTE_DB_BACKEND:
      - "json" : Force le backend JSON
      - "duckdb" : Utilise DuckDB (fallback JSON si indisponible)
      - (défaut) : Auto-détection
    """
    global _default_store
    if _default_store is not None:
        return _default_store

    backend = os.environ.get("ACTUARECETTE_DB_BACKEND", "auto").lower()

    if backend == "json":
        _default_store = JsonRunStore()
    elif backend == "duckdb":
        _default_store = DuckDBRunStore(db_path)
    else:
        # Auto : tente DuckDB, sinon JSON
        store = DuckDBRunStore(db_path)
        _default_store = store if store.is_available() else JsonRunStore()

    logger.info(f"DB backend: {_default_store.__class__.__name__}")
    return _default_store

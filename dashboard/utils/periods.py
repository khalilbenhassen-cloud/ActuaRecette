# periods.py - Gestion des périodes d'arrêté ActuaRecette
import os
from src.db_adapter import sqlite_connection
import json
import sqlite3
from typing import List

def _initialize_periods_table_if_needed(db_path: str = "data/actuarecette.db"):
    """Initialise la table periodes_arrete dans SQLite si elle n'existe pas."""
    if not os.path.exists(os.path.dirname(db_path)):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
    try:
        conn = sqlite_connection(db_path)
        cursor = conn.cursor()
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS periodes_arrete (
                code_periode VARCHAR PRIMARY KEY,
                libelle VARCHAR NOT NULL,
                statut VARCHAR NOT NULL DEFAULT 'OUVERT',
                cree_par VARCHAR,
                date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        cursor.execute("SELECT COUNT(*) FROM periodes_arrete")
        if cursor.fetchone()[0] == 0:
            # 1. Valeurs par défaut
            default_periods = [
                ('2025-T4', '4ème Trimestre 2025', 'OUVERT', 'systeme'),
                ('2026-T1', '1er Trimestre 2026', 'OUVERT', 'systeme'),
                ('2026-T2', '2ème Trimestre 2026', 'OUVERT', 'systeme'),
                ('2026-T3', '3ème Trimestre 2026', 'OUVERT', 'systeme'),
                ('2026-T4', '4ème Trimestre 2026', 'OUVERT', 'systeme')
            ]
            
            # 2. Scanner les fichiers JSON de uat_runs pour préserver l'historique
            runs_dir = "data/uat_runs"
            if os.path.exists(runs_dir):
                for f in os.listdir(runs_dir):
                    if f.endswith(".json"):
                        try:
                            with open(os.path.join(runs_dir, f), "r", encoding="utf-8") as file:
                                data = json.load(file)
                            p = data.get("periode_arrete", "").strip()
                            if p and p not in [x[0] for x in default_periods]:
                                default_periods.append((p, f"Période {p}", 'OUVERT', 'import_systeme'))
                        except Exception:
                            pass
            
            cursor.executemany(
                """INSERT OR IGNORE INTO periodes_arrete (code_periode, libelle, statut, cree_par)
                   VALUES (?, ?, ?, ?)""",
                default_periods
            )
            conn.commit()
        conn.close()
    except Exception as e:
        import logging
        logging.getLogger("actuarecette.periods").warning(f"DB period init error: {e}")

def list_all_periods(db_path: str = "data/actuarecette.db") -> List[dict]:
    _initialize_periods_table_if_needed(db_path)
    if not os.path.exists(db_path):
        return []
    try:
        conn = sqlite_connection(db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT code_periode, libelle, statut, cree_par, date_creation FROM periodes_arrete ORDER BY code_periode DESC").fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []

def add_period_to_db(code: str, libelle: str, user_sso: str) -> bool:
    code = code.strip()
    libelle = libelle.strip()
    if not code or not libelle:
        return False
    success = False
    for db_path in ["data/actuarecette.db", "data/actuarecette_v2.db"]:
        _initialize_periods_table_if_needed(db_path)
        try:
            conn = sqlite_connection(db_path)
            conn.execute(
                """INSERT OR REPLACE INTO periodes_arrete (code_periode, libelle, statut, cree_par)
                   VALUES (?, ?, 'OUVERT', ?)""",
                (code, libelle, user_sso)
            )
            conn.commit()
            conn.close()
            success = True
        except Exception:
            pass
    return success

def update_period_status_in_db(code: str, status: str) -> bool:
    success = False
    for db_path in ["data/actuarecette.db", "data/actuarecette_v2.db"]:
        _initialize_periods_table_if_needed(db_path)
        try:
            conn = sqlite_connection(db_path)
            conn.execute(
                "UPDATE periodes_arrete SET statut = ? WHERE code_periode = ?",
                (status, code)
            )
            conn.commit()
            conn.close()
            success = True
        except Exception:
            pass
    return success

def delete_period_from_db(code: str) -> bool:
    success = False
    for db_path in ["data/actuarecette.db", "data/actuarecette_v2.db"]:
        _initialize_periods_table_if_needed(db_path)
        try:
            conn = sqlite_connection(db_path)
            conn.execute("DELETE FROM periodes_arrete WHERE code_periode = ?", (code,))
            conn.commit()
            conn.close()
            success = True
        except Exception:
            pass
    return success

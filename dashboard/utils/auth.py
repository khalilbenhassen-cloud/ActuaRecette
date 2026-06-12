import re
import os
import hmac
import hashlib
import base64
import time
from src.db_adapter import sqlite_connection
import json
from dataclasses import dataclass, field
from typing import List, Optional

VALID_ROLES = ("Actuaire MOA", "Validateur", "Responsable MOA")
_LOB_REGISTRY_PATH = os.path.join("data", "lob_registry.json")
_DEFAULT_LOBS = ["LOB_AUTO_PART", "LOB_INCENDIE_RD", "LOB_MRH_HAB"]

def load_lob_registry(include_pending: bool = False) -> List[str]:
    # 1. Try SQLite first (source of truth)
    db_path = os.path.join("data", "actuarecette.db")
    if os.path.exists(db_path):
        try:
            import sqlite3
            conn = sqlite_connection(db_path)
            if include_pending:
                cursor = conn.execute("SELECT id_portefeuille FROM portefeuilles")
            else:
                cursor = conn.execute("SELECT id_portefeuille FROM portefeuilles WHERE statut = 'ACTIF'")
            lobs = [row[0] for row in cursor.fetchall()]
            conn.close()
            if lobs:
                return lobs
        except Exception:
            pass

    # 2. Fallback to JSON
    if os.path.exists(_LOB_REGISTRY_PATH):
        try:
            with open(_LOB_REGISTRY_PATH, "r", encoding="utf-8") as f:
                lobs = json.load(f)
            if isinstance(lobs, list) and len(lobs) > 0:
                return lobs
        except Exception: pass
    return _DEFAULT_LOBS.copy()

def add_lob_to_registry(lob_name: str) -> bool:
    lob_name = lob_name.strip().upper().replace(" ", "_")
    if not lob_name: return False
    lobs = load_lob_registry(include_pending=True)
    if lob_name in lobs: return False
    lobs.append(lob_name)
    os.makedirs(os.path.dirname(_LOB_REGISTRY_PATH), exist_ok=True)
    with open(_LOB_REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(lobs, f, indent=2, ensure_ascii=False)
    return True

def remove_lob_from_registry(lob_name: str) -> bool:
    lobs = load_lob_registry(include_pending=True)
    if lob_name not in lobs: return False
    lobs.remove(lob_name)
    with open(_LOB_REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(lobs, f, indent=2, ensure_ascii=False)
    return True

class DynamicLobList(list):
    def _get_list(self):
        return load_lob_registry(include_pending=True)
    def __iter__(self):
        return iter(self._get_list())
    def __len__(self):
        return len(self._get_list())
    def __contains__(self, item):
        return item in self._get_list()
    def __repr__(self):
        return repr(self._get_list())
    def __eq__(self, other):
        if isinstance(other, list):
            return self._get_list() == other
        return super().__eq__(other)
    def __ne__(self, other):
        if isinstance(other, list):
            return self._get_list() != other
        return super().__ne__(other)
    def copy(self):
        return self._get_list()

ALL_LOBS = DynamicLobList()

@dataclass
class UserIdentity:
    sso: str
    name: str
    role: str
    assigned_lobs: List[str] = field(default_factory=list)

    def __post_init__(self):
        if self.role not in VALID_ROLES:
            raise ValueError(f"Rôle invalide : '{self.role}'")
        if not self.sso or not re.match(r'^[a-zA-Z0-9._-]+$', self.sso):
            raise ValueError(f"SSO invalide : '{self.sso}'")

    @property
    def is_maker(self) -> bool:
        return self.role == "Actuaire MOA"

    @property
    def is_checker(self) -> bool:
        return self.role in ("Validateur", "Responsable MOA")

    @property
    def is_manager(self) -> bool:
        return self.role == "Responsable MOA"

    @property
    def visible_lobs(self) -> List[str]:
        if self.is_checker and (not self.assigned_lobs or set(self.assigned_lobs) == set(ALL_LOBS)):
            return load_lob_registry()
        if self.assigned_lobs:
            return self.assigned_lobs
        return []

    def can_view_lob(self, lob_id: str) -> bool:
        return lob_id in self.visible_lobs

    def can_certify_run(self, maker_sso: str) -> bool:
        if not self.is_checker: return False
        return self.sso != maker_sso

    def generate_auth_token(self, secret: str = "ActuaRecetteSecuredToken2026") -> str:
        secret_key = os.environ.get("ACTUARECETTE_SIGNING_SECRET", secret)
        payload = {
            "sso": self.sso,
            "name": self.name,
            "role": self.role,
            "lobs": self.visible_lobs,
            "exp": int(time.time()) + 86400
        }
        payload_json = json.dumps(payload, sort_keys=True)
        payload_b64 = base64.urlsafe_b64encode(payload_json.encode("utf-8")).decode("utf-8")
        signature = hmac.new(secret_key.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
        return f"{payload_b64}.{signature}"

    def to_headers(self) -> dict:
        token = self.generate_auth_token()
        return {
            "Authorization": f"Bearer {token}",
            "X-User-SSO": self.sso,
            "X-User-Name": self.name,
            "X-User-Role": self.role,
            "X-User-LOBs": ",".join(self.visible_lobs),
        }

    def to_dict(self) -> dict:
        return {
            "sso": self.sso, "name": self.name, "role": self.role, "assigned_lobs": self.assigned_lobs
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UserIdentity":
        return cls(
            sso=data["sso"], name=data["name"], role=data["role"], assigned_lobs=data.get("assigned_lobs", [])
        )

LOCAL_USER_REGISTRY = [
    UserIdentity(sso="maker.junior", name="Actuaire junior (Maker)", role="Actuaire MOA", assigned_lobs=["LOB_AUTO_PART"]),
    UserIdentity(sso="maker.senior", name="Actuaire senior", role="Actuaire MOA", assigned_lobs=["LOB_INCENDIE_RD"]),
    UserIdentity(sso="checker", name="Validateur Technique (Checker)", role="Validateur", assigned_lobs=ALL_LOBS),
    UserIdentity(sso="manager", name="Responsable Métier (Manager)", role="Responsable MOA", assigned_lobs=ALL_LOBS),
]

def _initialize_users_table_if_needed(db_path: str = "data/actuarecette.db"):
    """Initialise la table utilisateurs dans SQLite si elle n'existe pas."""
    import sqlite3
    if not os.path.exists(os.path.dirname(db_path)):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
    try:
        conn = sqlite_connection(db_path)
        cursor = conn.cursor()
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS utilisateurs (
                sso VARCHAR PRIMARY KEY,
                name VARCHAR NOT NULL,
                role VARCHAR NOT NULL,
                assigned_lobs TEXT NOT NULL,
                statut VARCHAR NOT NULL DEFAULT 'ACTIF',
                cree_par VARCHAR,
                date_creation TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        cursor.execute("SELECT COUNT(*) FROM utilisateurs")
        if cursor.fetchone()[0] == 0:
            default_users = [
                ('maker.junior', 'Actuaire junior (Maker)', 'Actuaire MOA', 'LOB_AUTO_PART', 'ACTIF', 'systeme'),
                ('maker.senior', 'Actuaire senior', 'Actuaire MOA', 'LOB_INCENDIE_RD', 'ACTIF', 'systeme'),
                ('checker', 'Validateur Technique (Checker)', 'Validateur', 'LOB_AUTO_PART,LOB_INCENDIE_RD,LOB_MRH_HAB', 'ACTIF', 'systeme'),
                ('manager', 'Responsable Métier (Manager)', 'Responsable MOA', 'LOB_AUTO_PART,LOB_INCENDIE_RD,LOB_MRH_HAB', 'ACTIF', 'systeme')
            ]
            cursor.executemany(
                """INSERT INTO utilisateurs (sso, name, role, assigned_lobs, statut, cree_par)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                default_users
            )
            conn.commit()
        conn.close()
    except Exception as e:
        import logging
        logging.getLogger("actuarecette.auth").warning(f"DB user init error: {e}")

def find_user_by_sso(sso: str) -> Optional[UserIdentity]:
    _initialize_users_table_if_needed()
    import sqlite3
    db_path = "data/actuarecette.db"
    if not os.path.exists(db_path):
        for u in LOCAL_USER_REGISTRY:
            if u.sso == sso: return u
        return None
    try:
        conn = sqlite_connection(db_path)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT sso, name, role, assigned_lobs, statut FROM utilisateurs WHERE sso = ?", (sso,)).fetchone()
        conn.close()
        if row:
            if row["statut"] == "INACTIF": return None
            lobs = [l.strip() for l in row["assigned_lobs"].split(",") if l.strip()] if row["assigned_lobs"] else []
            return UserIdentity(sso=row["sso"], name=row["name"], role=row["role"], assigned_lobs=lobs)
    except Exception: pass
    for u in LOCAL_USER_REGISTRY:
        if u.sso == sso: return u
    return None

def list_all_users() -> List[UserIdentity]:
    _initialize_users_table_if_needed()
    import sqlite3
    db_path = "data/actuarecette.db"
    if not os.path.exists(db_path):
        return LOCAL_USER_REGISTRY.copy()
    try:
        conn = sqlite_connection(db_path)
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT sso, name, role, assigned_lobs FROM utilisateurs").fetchall()
        conn.close()
        users = []
        for r in rows:
            lobs = [l.strip() for l in r["assigned_lobs"].split(",") if l.strip()] if r["assigned_lobs"] else []
            users.append(UserIdentity(sso=r["sso"], name=r["name"], role=r["role"], assigned_lobs=lobs))
        return users
    except Exception:
        return LOCAL_USER_REGISTRY.copy()

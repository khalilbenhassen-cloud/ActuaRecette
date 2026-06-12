# api_auth_middleware.py - Middleware d'identité FastAPI pour ActuaRecette v6.0
# Extrait l'identité de chaque requête via les headers X-User-*
# et rejette les requêtes sans identité (sauf /health et /docs).
#
# Utilisé par : api/main.py

import re
import logging
from typing import Optional

from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

logger = logging.getLogger("actuarecette.api.auth")

# ---------------------------------------------------------------------------
# Regex de validation des identifiants (cf. Plan §6.1b #8)
# ---------------------------------------------------------------------------
SAFE_ID_REGEX = re.compile(r'^[a-zA-Z0-9_.-]+$')

# Endpoints exemptés d'authentification
PUBLIC_ENDPOINTS = {"/health", "/docs", "/openapi.json", "/redoc"}

def validate_safe_id(value: str, param_name: str) -> str:
    """
    Valide qu'un identifiant (run_id, scenario_id, id_portefeuille)
    ne contient que des caractères sûrs — bloque le path traversal.
    
    Rejette : ../  , ;  |  \\ et tout caractère spécial.
    """
    if not value or not SAFE_ID_REGEX.match(value):
        raise HTTPException(
            status_code=400,
            detail=f"Paramètre '{param_name}' invalide : '{value}'. "
                   f"Seuls les caractères alphanumériques, _, -, et . sont autorisés."
        )
    return value

# ---------------------------------------------------------------------------
# Middleware d'identité
# ---------------------------------------------------------------------------

def verify_auth_token(token: str, secret: str = "ActuaRecetteSecuredToken2026") -> Optional[dict]:
    import hmac
    import hashlib
    import base64
    import json
    import time
    import os
    try:
        if not token or "." not in token:
            return None
        parts = token.split(".")
        if len(parts) != 2:
            return None
        payload_b64, signature = parts
        
        # Verify signature
        secret_key = os.environ.get("ACTUARECETTE_SIGNING_SECRET", secret)
        expected_sig = hmac.new(secret_key.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_sig, signature):
            return None
            
        # Decode payload
        payload_json = base64.urlsafe_b64decode(payload_b64.encode("utf-8")).decode("utf-8")
        payload = json.loads(payload_json)
        
        # Check expiration
        if int(time.time()) > payload.get("exp", 0):
            return None
            
        return payload
    except Exception:
        return None

# ---------------------------------------------------------------------------
# Middleware d'identité
# ---------------------------------------------------------------------------

class IdentityMiddleware(BaseHTTPMiddleware):
    """
    Middleware qui extrait l'identité de l'utilisateur.
    En production, exige un jeton Authorization: Bearer <token> signé par HMAC-SHA256.
    En mode développement (ACTUARECETTE_DEV_MODE=1), tolère les en-têtes X-User-* en clair.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        from fastapi.responses import JSONResponse

        # Endpoints publics ou ressources statiques : pas besoin d'authentification
        if request.url.path in PUBLIC_ENDPOINTS or request.url.path.startswith("/static"):
            try:
                return await call_next(request)
            except Exception as e:
                logger.error(f"Unhandled error in public endpoint {request.url.path}: {e}")
                return JSONResponse(
                    status_code=500,
                    content={"detail": f"Erreur interne du serveur : {str(e)}"}
                )

        # Extraction du token d'autorisation
        auth_header = request.headers.get("Authorization")
        token_payload = None
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            token_payload = verify_auth_token(token)
            if not token_payload:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Jeton d'authentification invalide ou expiré."}
                )

        if token_payload:
            user_sso = token_payload["sso"]
            try:
                validate_safe_id(user_sso, "X-User-SSO")
            except HTTPException as e:
                return JSONResponse(
                    status_code=e.status_code,
                    content={"detail": e.detail}
                )
            request.state.user_sso = user_sso
            request.state.user_name = token_payload.get("name", user_sso)
            request.state.user_role = token_payload.get("role", "Actuaire MOA")
            request.state.user_lobs = token_payload.get("lobs", [])
        else:
            # Si pas de token valide, on vérifie si on est en mode DEV
            import os
            is_dev = os.environ.get("ACTUARECETTE_DEV_MODE") == "1"
            
            user_sso = request.headers.get("X-User-SSO")
            if is_dev:
                if not user_sso:
                    user_sso = "dev.user"
                    request.state.user_sso = user_sso
                    request.state.user_name = "Dev User"
                    request.state.user_role = "Responsable MOA"
                    request.state.user_lobs = []
                    logger.debug("Requête sans auth → utilisateur dev par défaut (DEV_MODE)")
                else:
                    try:
                        validate_safe_id(user_sso, "X-User-SSO")
                    except HTTPException as e:
                        return JSONResponse(
                            status_code=e.status_code,
                            content={"detail": e.detail}
                        )
                    request.state.user_sso = user_sso
                    request.state.user_name = request.headers.get("X-User-Name", user_sso)
                    request.state.user_role = request.headers.get("X-User-Role", "Actuaire MOA")
                    lobs_header = request.headers.get("X-User-LOBs", "")
                    request.state.user_lobs = [l.strip() for l in lobs_header.split(",") if l.strip()]
            else:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Header Authorization Bearer manquant ou invalide. Authentification requise."}
                )

        # Validation des path parameters sensibles (run_id, scenario_id, etc.)
        path_params = request.path_params
        for param_name in ("run_id", "scenario_id", "id_portefeuille", "run_id_1", "run_id_2"):
            if param_name in path_params:
                try:
                    validate_safe_id(path_params[param_name], param_name)
                except HTTPException as e:
                    return JSONResponse(
                        status_code=e.status_code,
                        content={"detail": e.detail}
                    )

        try:
            return await call_next(request)
        except Exception as e:
            logger.error(f"Unhandled error in protected endpoint {request.url.path}: {e}")
            return JSONResponse(
                status_code=500,
                content={"detail": f"Erreur interne du serveur : {str(e)}"}
            )

# ---------------------------------------------------------------------------
# Helper pour extraire l'identité dans les endpoints
# ---------------------------------------------------------------------------

def get_current_user(request: Request) -> dict:
    """
    Extrait l'identité de l'utilisateur depuis request.state.
    À appeler dans n'importe quel endpoint FastAPI.
    
    Usage:
        @app.get("/example")
        def my_endpoint(request: Request):
            user = get_current_user(request)
            print(user["sso"])  # "karim.benali"
    """
    return {
        "sso": getattr(request.state, "user_sso", "unknown"),
        "name": getattr(request.state, "user_name", "Unknown"),
        "role": getattr(request.state, "user_role", "Actuaire MOA"),
        "lobs": getattr(request.state, "user_lobs", []),
    }

# Phase 1.4: LOBs visibles par l'utilisateur courant
ALL_LOBS = ["LOB_AUTO_PART", "LOB_INCENDIE_RD", "LOB_MRH_HAB"]

def get_visible_lobs(request: Request) -> list:
    """
    Retourne la liste des LOBs visibles par l'utilisateur courant.
    
    - Si des LOBs spécifiques sont explicitement assignés, ils sont prioritaires pour TOUS les rôles (loi du moindre privilège)
    - Si aucun LOB n'est assigné mais que le rôle est Validateur ou Responsable MOA, accès global (ALL_LOBS)
    - Par défaut (Actuaire MOA sans LOB assigné), accès nul
    """
    user_role = getattr(request.state, "user_role", "")
    user_lobs = getattr(request.state, "user_lobs", [])
    
    if user_lobs:
        return user_lobs
    
    if user_role in ("Validateur", "Responsable MOA"):
        return ALL_LOBS
    
    return []

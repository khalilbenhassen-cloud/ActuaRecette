# validators.py — Validation et sanitisation des entrées utilisateur
# Bloque les path traversal, injections, et IDs malformés
"""
Usage:
    from dashboard.utils.validators import validate_run_id
    safe_id = validate_run_id(user_input)  # raises ValueError if invalid
"""
import re

# Regex stricte : uniquement alphanum, underscore, tiret, point
# Correspond à la regex côté API (api_auth_middleware.py)
SAFE_ID_REGEX = re.compile(r'^[a-zA-Z0-9_.-]+$')

def validate_run_id(run_id: str) -> str:
    """
    Valide qu'un run_id ne contient que des caractères sûrs.
    Bloque : ../ , ; | \\ et tout caractère spécial.
    
    Args:
        run_id: Identifiant de run à valider.
    
    Returns:
        Le run_id validé (inchangé).
    
    Raises:
        ValueError: Si le run_id contient des caractères non-autorisés.
    """
    if not run_id or not isinstance(run_id, str):
        raise ValueError("run_id invalide : valeur vide ou non-string.")
    
    if not SAFE_ID_REGEX.match(run_id):
        raise ValueError(
            f"run_id invalide : '{run_id}'. "
            "Seuls les caractères alphanumériques, _, -, et . sont autorisés."
        )
    
    # Double-check : pas de traversal même si la regex devrait bloquer
    if ".." in run_id or "/" in run_id or "\\" in run_id:
        raise ValueError(f"run_id suspect de path traversal : '{run_id}'.")
    
    return run_id

# ── Validation fichiers uploadés ──

# Taille max par défaut : 50 Mo
MAX_UPLOAD_SIZE_BYTES = 50 * 1024 * 1024
ALLOWED_EXTENSIONS = {".csv", ".xlsx"}
# Préfixes dangereux dans les cellules CSV (injection de formules Excel)
_FORMULA_PREFIXES = ("=", "+", "-", "@")

def validate_uploaded_file(
    uploaded_file,
    max_size: int = MAX_UPLOAD_SIZE_BYTES,
    allowed_extensions: set = ALLOWED_EXTENSIONS,
) -> "pd.DataFrame":
    """
    Valide et lit un fichier uploadé via st.file_uploader.

    Vérifications :
    - Taille maximale
    - Extension autorisée
    - Lecture CSV ou XLSX selon extension
    - Détection de formules Excel malicieuses

    Args:
        uploaded_file: Objet UploadedFile de Streamlit.
        max_size: Taille maximale en octets.
        allowed_extensions: Extensions autorisées (avec le point).

    Returns:
        pd.DataFrame du fichier validé.

    Raises:
        ValueError: Si le fichier est invalide.
    """
    import pandas as pd
    import os

    if uploaded_file is None:
        raise ValueError("Aucun fichier fourni.")

    # 1. Vérifier la taille
    file_size = uploaded_file.size
    if file_size > max_size:
        max_mb = max_size / (1024 * 1024)
        file_mb = file_size / (1024 * 1024)
        raise ValueError(
            f"Fichier trop volumineux : {file_mb:.1f} Mo "
            f"(limite : {max_mb:.0f} Mo)."
        )

    # 2. Vérifier l'extension
    _, ext = os.path.splitext(uploaded_file.name)
    ext = ext.lower()
    if ext not in allowed_extensions:
        raise ValueError(
            f"Extension '{ext}' non autorisée. "
            f"Extensions acceptées : {', '.join(sorted(allowed_extensions))}."
        )

    # 3. Lire le fichier selon l'extension
    try:
        uploaded_file.seek(0)
        if ext == ".csv":
            df = pd.read_csv(uploaded_file)
        elif ext == ".xlsx":
            df = pd.read_excel(uploaded_file, engine="openpyxl")
        else:
            raise ValueError(f"Format non supporté : {ext}")
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Impossible de lire le fichier : {e}")

    # 4. Vérifications de base
    if df.empty:
        raise ValueError("Le fichier est vide (aucune ligne de données).")

    if len(df.columns) < 2:
        raise ValueError(
            f"Le fichier ne contient que {len(df.columns)} colonne(s). "
            "Un minimum de 2 colonnes est requis (ID + prime)."
        )

    # 5. Détection de formules Excel malicieuses
    formula_cells = []
    for col in df.select_dtypes(include=["object"]).columns:
        mask = df[col].astype(str).str.startswith(_FORMULA_PREFIXES)
        if mask.any():
            examples = df[col][mask].head(3).tolist()
            formula_cells.append((col, examples))

    if formula_cells:
        details = "; ".join(
            f"colonne '{col}': {exs}" for col, exs in formula_cells[:3]
        )
        raise ValueError(
            f"Formules Excel suspectes détectées ({details}). "
            "Veuillez nettoyer le fichier avant import."
        )

    return df

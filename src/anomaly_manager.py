"""
Module Anomaly Manager
======================

Ce module pilote la persistance des campagnes de tests (Runs UAT) sous forme d'historique
au format JSON et automatise la traduction des écarts en rapports de bugs formatés pour
Jira (Jira Markdown Export).

Auteur: Senior Software Engineer & Product Owner Projets IT Assurance
Version: 1.0.0

NOTE: Ce module a été refactorisé. Les fonctions ont été déplacées dans des sous-modules
dédiés (run_persistence, jira_export, audit_trail, scenario_manager).
Toutes les fonctions sont ré-exportées ici pour rétrocompatibilité.
"""

# Backward compatibility — all functions re-exported from sub-modules
from src.run_persistence import save_uat_run, load_run_history, delete_uat_run, compare_uat_runs, sync_run_to_db
from src.jira_export import generate_jira_markdown
from src.audit_trail import add_global_audit_entry, load_global_audit_trail, generate_witness_zip
from src.scenario_manager import save_scenario, load_scenarios, generate_stress_portfolio

def translate_technical_error(exception: Exception) -> str:
    """
    Intercepteur et traducteur d'erreurs DSI en français d'assurance (Zero Jargon).
    """
    err_msg = str(exception)
    
    if "ParserError" in err_msg or "tokenizing" in err_msg or "Expected" in err_msg:
        return (
            "Format de fichier non conforme : Le fichier contient un nombre de colonnes incohérent "
            "ou des délimiteurs mal placés. Veuillez vérifier s'il s'agit de séparateurs virgules "
            "ou points-virgules, ou de caractères spéciaux inattendus."
        )
    elif "FileNotFoundError" in err_msg:
        return "Fichier introuvable : Le fichier de données requis est inaccessible ou n'existe plus."
    elif "KeyError" in err_msg:
        key_name = err_msg.replace("KeyError:", "").strip()
        return (
            f"Structure du fichier incorrecte : La colonne obligatoire {key_name} est introuvable. "
            "Veuillez vérifier votre mapping déclaratif et l'orthographe exacte des en-têtes."
        )
    elif "ZeroDivisionError" in err_msg:
        return (
            "Incohérence financière : Une division par zéro est survenue lors de l'établissement "
            "du taux de succès. Assurez-vous qu'aucun assuré ne possède de prime de référence nulle."
        )
    elif "ValueError" in err_msg:
        clean_msg = err_msg.replace("ValueError:", "").strip()
        if "jointure" in clean_msg.lower() or "commun" in clean_msg.lower():
            return (
                "Aucun assuré commun trouvé : La jointure sémantique a échoué car les identifiants "
                "uniques (ID_CLIENT) ne correspondent dans aucun des deux fichiers de test."
            )
        return f"Incohérence des données : {clean_msg}"
    elif "DuckDB" in err_msg or "duckdb" in err_msg.lower():
        return (
            "Échec de l'alignement : Une incohérence technique DuckDB/Arrow empêche la jointure "
            "vectorielle. Veuillez vérifier la cohérence des formats d'identifiants clients."
        )
    elif "ValidationError" in err_msg:
        return (
            "Contrôle de conformité technique : Les structures de requêtes ou les schémas de recette "
            "transmis ne respectent pas le protocole d'échange d'assurance d'ActuaRecette."
        )
    else:
        return (
            f"Divergence technique non répertoriée : Le moteur a rencontré une anomalie lors "
            f"du traitement ({err_msg}). Veuillez contacter le support technique DSI."
        )

if __name__ == "__main__":
    # ARCH-11: Inline test code removed. Tests for save_uat_run, load_run_history,
    # generate_jira_markdown, and delete_uat_run should be run via:
    #   pytest tests/
    # Original block tested: save/load/delete UAT runs, Jira markdown generation,
    # assertions on KPIs and anomaly sorting (113 lines removed).
    pass

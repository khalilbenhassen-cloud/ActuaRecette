"""
Module Jira Export
==================

Génère des descriptions de bugs normalisées au format Jira Markdown
à partir des anomalies actuarielles détectées.

Extrait de anomaly_manager.py pour modularité.

Auteur: Senior Software Engineer & Product Owner Projets IT Assurance
Version: 1.0.0
"""

import json
from typing import Dict, Any

def generate_jira_markdown(anomaly: Dict[str, Any], input_profile: Dict[str, Any]) -> str:
    """
    Traduit une anomalie actuarielle en description de bug normalisée au format Jira Markdown.

    Args:
        anomaly (Dict[str, Any]): Données d'anomalie (ID_CLIENT, attendu, calculé, écarts).
        input_profile (Dict[str, Any]): Variables d'entrée du profil de l'assuré (âge, crm, etc.).

    Returns:
        str: Fiche de bug rédigée en Markdown pour copier-coller dans Jira.
    """
    # 1. Résolution des variables
    client_id = anomaly.get("ID_CLIENT") or anomaly.get("id_assure") or "INCONNU"
    ref_premium = anomaly.get("PRIME_ACTU") or anomaly.get("PRIME_REF") or 0.0
    prod_premium = anomaly.get("PRIME_DSI") or anomaly.get("prime_dsi") or 0.0
    abs_dev = anomaly.get("abs_deviation") or (prod_premium - ref_premium)
    rel_dev_pct = anomaly.get("rel_deviation_pct") or 0.0
    
    # Correction en pourcentage propre
    if ref_premium != 0.0 and "rel_deviation_pct" not in anomaly:
        rel_dev_pct = (abs_dev / ref_premium) * 100

    # 2. Catégorisation automatique du bug selon les critères réglementaires et financiers
    if abs(rel_dev_pct) > 30.0:
        if abs_dev > 0.0:
            bug_category = "BUG LOGIQUE CRITIQUE - SURPRIME COMPAGNIE (Risque Commercial d'érosion d'image)"
        else:
            bug_category = "BUG LOGIQUE CRITIQUE - SOUS-TARIFICATION (Risque Technique de Perte / Non-rentabilité)"
    elif abs_dev > 0.0:
        bug_category = "SURPRIME COMPAGNIE (Risque Commercial d'érosion d'image)"
    else:
        bug_category = "SOUS-TARIFICATION (Risque Technique de Perte / Non-rentabilité)"

    # 3. Diagnostic automatique (Analyse heuristique de suspects)
    diagnostic_suspects = []
    
    # Règle d'Âge (Jeune Conducteur ou Senior)
    age = input_profile.get("age") or input_profile.get("AGE") or input_profile.get("age_assure")
    if age is not None:
        try:
            val_age = float(age)
            if val_age < 25:
                diagnostic_suspects.append(
                    f"-> Suspect [Classe Âge] : Âge de l'assuré inférieur à 25 ans ({val_age} ans). "
                    "Vérifier l'application ou l'alignement de la surprime Jeune Conducteur."
                )
            elif val_age > 75:
                diagnostic_suspects.append(
                    f"-> Suspect [Classe Âge] : Assuré sénior ({val_age} ans). "
                    "Vérifier si le coefficient de surprime lié à l'âge avancé a été correctement implémenté."
                )
        except ValueError:
            pass

    # Règle de Véhicule SUV / Luxe
    vehicule = (
        input_profile.get("vehicule") 
        or input_profile.get("VEHICULE") 
        or input_profile.get("type_vehicule")
    )
    if vehicule is not None:
        val_vehicule = str(vehicule).upper()
        if any(kw in val_vehicule for kw in ["SUV", "SPORT", "LUXE", "CABRIOLET"]):
            diagnostic_suspects.append(
                f"-> Suspect [Classe Véhicule] : Le véhicule possède une catégorie à risque élevé ({vehicule}). "
                "Vérifier si la grille tarifaire DSI a correctement corrélé la classe d'équivalence."
            )

    # Règle de Coefficient de Réduction / Majoration (CRM)
    crm = (
        input_profile.get("bonus_malus") 
        or input_profile.get("BONUS_MALUS") 
        or input_profile.get("crm")
    )
    if crm is not None:
        try:
            val_crm = float(crm)
            if val_crm != 1.0:
                diagnostic_suspects.append(
                    f"-> Suspect [CRM / Bonus-Malus] : Coefficient CRM non neutre ({val_crm}). "
                    "Vérifier la précision de la multiplication ou l'ordre des réductions."
                )
        except ValueError:
            pass

    # Si aucun suspect détecté
    if not diagnostic_suspects:
        diagnostic_paragraph = (
            "Aucun suspect évident identifié sur les variables standards d'âge, CRM ou véhicule. "
            "Il est suggéré de vérifier la formule mathématique globale."
        )
    else:
        diagnostic_paragraph = "\n".join(diagnostic_suspects)

    # 4. Génération de la description en Jira Markdown (double accolades pour échapper le f-string)
    jira_md = f"""h1. [BUG ACTUARIEL] Écart de tarification détecté sur le client {client_id}

h2. 1. Synthese de l'Anomalie
|| Caractéristique || Détail ||
| *Statut* | {{color:red}}*DÉFAUT ACTUARIEL*{{color}} |
| *Catégorie de Risque* | *{bug_category}* |
| *Écart Absolu constaté* | {abs_dev:+.2f} € |
| *Écart Relatif constaté* | {rel_dev_pct:+.2f} % |

h2. 2. Tableau de Réconciliation des Primes
|| Composante Tarifaire || Prime Attendue (Réf Actu) || Prime Calculée (DSI) || Delta Constaté ||
| Prime Technique Annuelle | {ref_premium:.2f} € | {prod_premium:.2f} € | *{abs_dev:+.2f} €* |

h2. 3. Payload d'Entrée (Jeu de Données Assuré)
{{code:json}}
{json.dumps(input_profile, indent=2, ensure_ascii=False)}
{{code}}

h2. 4. Diagnostic Provisoire de Recette
{diagnostic_paragraph}

h2. 5. Analyse Root Cause (Moteur ActuaRecette)
{_build_root_cause_section(anomaly)}
"""
    return jira_md

def _build_root_cause_section(anomaly: Dict[str, Any]) -> str:
    """T87 -- Genere la section root cause pour le ticket Jira."""
    category = anomaly.get("anomaly_category", "")
    details = anomaly.get("suspicion_details", "")
    coeff = anomaly.get("coefficient_fautif", "")

    if not category and not details:
        return (
            "|| Statut || Diagnostic ||\n"
            "| Root Cause | _En attente d'analyse. "
            "Lancez l'analyse Root Cause depuis ActuaRecette pour pre-remplir ce champ._ |"
        )

    lines = ["|| Champ || Valeur ||"]
    if category:
        lines.append(f"| *Pattern detecte* | {category} |")
    if coeff:
        lines.append(f"| *Coefficient suspect* | {{color:red}}{coeff}{{color}} |")
    if details:
        lines.append(f"| *Detail* | {details} |")

    # Remediation suggestions based on pattern
    remediation = _suggest_remediation(category)
    if remediation:
        lines.append(f"| *Action recommandee* | {remediation} |")

    return "\n".join(lines)

def _suggest_remediation(category: str) -> str:
    """Genere une recommandation de correction basee sur le pattern."""
    remediations = {
        "Oubli de Seuil Minimal (Plancher)": (
            "Verifier l'application de la regle min(plancher, prime_calculee) "
            "dans le code de production DSI."
        ),
        "Facteur Multiplicatif Errone": (
            "Comparer le coefficient applique dans le code DSI avec la valeur "
            "de reference du bareme actuariel. Corriger et relancer le batch."
        ),
        "Inversion de Colonnes": (
            "Verifier le mapping des colonnes d'entree dans le flux ETL. "
            "Une permutation de colonnes est suspectee."
        ),
        "Bug d'Arrondi Systematique": (
            "Verifier la precision des calculs intermediaires (float64 vs float32) "
            "et l'ordre des arrondis dans la chaine de calcul."
        ),
        "Ecart Fonctionnel": (
            "Ecart fonctionnel non categorise. Analyser manuellement la formule "
            "de calcul pour ce profil specifique."
        ),
    }
    for key, msg in remediations.items():
        if key.lower() in category.lower():
            return msg
    return ""

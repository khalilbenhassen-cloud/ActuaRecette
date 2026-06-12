"""
Module Scenario Manager
========================

Gère la sauvegarde et le chargement des modèles de recette (scénarios)
et la génération de portefeuilles de stress-testing.

Extrait de anomaly_manager.py pour modularité.

Auteur: Senior Software Engineer & Product Owner Projets IT Assurance
Version: 1.0.0
"""

import os
import json
import uuid
from typing import Dict, List, Any, Optional

def save_scenario(
    scenarios_dir: str,
    name: str,
    description: Optional[str],
    mapping: Dict[str, Any],
    rules: Dict[str, Any]
) -> str:
    """
    Sauvegarde un modèle de recette (mapping et règles de qualité) localement sur le serveur.
    """
    os.makedirs(scenarios_dir, exist_ok=True)
    scenario_id = f"scenario_{uuid.uuid4().hex[:12]}"
    
    payload = {
        "scenario_id": scenario_id,
        "name": name,
        "description": description,
        "mapping": mapping,
        "rules": rules
    }
    
    file_path = os.path.join(scenarios_dir, f"{scenario_id}.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        
    return os.path.abspath(file_path)

def load_scenarios(scenarios_dir: str) -> List[Dict[str, Any]]:
    """
    Charge tous les modèles de recette enregistrés localement sur le serveur.
    """
    if not os.path.exists(scenarios_dir):
        return []
        
    scenarios = []
    for file_name in os.listdir(scenarios_dir):
        if file_name.endswith(".json"):
            file_path = os.path.join(scenarios_dir, file_name)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if all(k in data for k in ["scenario_id", "name", "mapping", "rules"]):
                    scenarios.append(data)
            except Exception:
                continue
                
    scenarios.sort(key=lambda x: x.get("scenario_id", ""), reverse=True)
    return scenarios

def generate_stress_portfolio(output_path: str, num_records: int = 1000) -> str:
    """
    Génère un portefeuille de stress-testing d'assurance de 1000 assurés comprenant des cas limites.
    """
    import numpy as np
    import pandas as pd
    
    # Configuration du seed pour la reproductibilité partielle
    np.random.seed(1337)
    
    ids = [f"CST{i:04d}" for i in range(1, num_records + 1)]
    
    # Génération d'âges avec 15% de jeunes conducteurs (< 25 ans) et 15% de seniors (> 75 ans)
    rand_selector = np.random.rand(num_records)
    ages = []
    for r in rand_selector:
        if r < 0.15:
            ages.append(int(np.random.randint(18, 25)))
        elif r < 0.30:
            ages.append(int(np.random.randint(75, 96)))
        else:
            ages.append(int(np.random.randint(25, 75)))
            
    # Génération d'expérience de permis cohérente
    experience = []
    for age in ages:
        exp = age - 18 - int(np.random.randint(0, 3))
        experience.append(max(0, exp))
        
    # Catégories de véhicules
    vehicle_types_choices = ["Citadine", "Berline", "SUV", "Sportive", "Prestige"]
    vehicle_types = np.random.choice(vehicle_types_choices, size=num_records)
    
    # Puissance du véhicule (chevaux) avec 10% de véhicules surpuissants (> 250 ch)
    horsepower = []
    for r in rand_selector:
        if r < 0.10:
            horsepower.append(int(np.random.randint(250, 350)))
        else:
            horsepower.append(int(np.random.randint(50, 250)))
            
    # Zones géographiques
    zones_choices = ["Urbain Dense", "Urbain Standard", "Rural"]
    zones = np.random.choice(zones_choices, size=num_records)
    
    usages_choices = ["Prive", "Prive-Trajet", "Professionnel"]
    usages = np.random.choice(usages_choices, size=num_records)
    
    kilometrage = np.random.randint(2, 46, size=num_records) * 1000
    
    # Génération Bonus-Malus (CRM) avec 10% de malus sévères (> 1.5) et 10% de bonus extrêmes (< 0.5)
    bonus_malus = []
    for r in rand_selector:
        if r < 0.10:
            bonus_malus.append(round(float(np.random.uniform(1.5, 2.0)), 2))
        elif r < 0.20:
            bonus_malus.append(round(float(np.random.uniform(0.40, 0.50)), 2))
        else:
            bonus_malus.append(round(float(np.random.choice([0.50, 0.68, 0.76, 0.85, 0.95, 1.00, 1.10, 1.25])), 2))
            
    # Calcul théorique rigoureux de la PRIME_REF (avec Seuil Plancher à 150.00 EUR)
    prime_ref = []
    for i in range(num_records):
        bm = bonus_malus[i]
        age = ages[i]
        pwr = horsepower[i]
        zone = zones[i]
        
        factor_age = 1.5 if age < 25 else 1.0
        factor_power = 1.3 if pwr > 150 else 1.0
        factor_zone = 1.2 if zone == "Urbain Dense" else 1.0
        
        calc = 250.0 * bm * factor_age * factor_power * factor_zone
        
        # Application de la règle métier du Seuil Plancher (150.00 EUR)
        final_p = max(150.00, calc)
        prime_ref.append(round(final_p, 2))
        
    # Constitution des Primes de production DSI contenant des bugs d'intégration calibrés
    prime_dsi = []
    for i in range(num_records):
        ref_p = prime_ref[i]
        age = ages[i]
        pwr = horsepower[i]
        bm = bonus_malus[i]
        zone = zones[i]
        
        bug_selector = np.random.rand()
        
        # 1. Bug 1 : Oubli de Seuil Plancher (3% de cas)
        if bug_selector < 0.03:
            # Calcul sans le max(150.00, calc)
            factor_age = 1.5 if age < 25 else 1.0
            factor_power = 1.3 if pwr > 150 else 1.0
            factor_zone = 1.2 if zone == "Urbain Dense" else 1.0
            raw_calc = 250.0 * bm * factor_age * factor_power * factor_zone
            if raw_calc < 150.00:
                prime_dsi.append(round(raw_calc, 2))
                continue
                
        # 2. Bug 2 : Facteur Jeune Conducteur erroné à 1.60 au lieu de 1.50 (3% de cas)
        if bug_selector >= 0.03 and bug_selector < 0.06 and age < 25:
            factor_power = 1.3 if pwr > 150 else 1.0
            factor_zone = 1.2 if zone == "Urbain Dense" else 1.0
            buggy_calc = 250.0 * bm * 1.60 * factor_power * factor_zone
            prime_dsi.append(round(max(150.00, buggy_calc), 2))
            continue
            
        # 3. Bug 3 : Facteur de Puissance erroné à 1.50 au lieu de 1.30 (3% de cas)
        if bug_selector >= 0.06 and bug_selector < 0.09 and pwr > 150:
            factor_age = 1.5 if age < 25 else 1.0
            factor_zone = 1.2 if zone == "Urbain Dense" else 1.0
            buggy_calc = 250.0 * bm * factor_age * 1.50 * factor_zone
            prime_dsi.append(round(max(150.00, buggy_calc), 2))
            continue
            
        # 4. Micro-bruit d'arrondi (2% de cas)
        if bug_selector >= 0.09 and bug_selector < 0.11:
            prime_dsi.append(round(ref_p + np.random.choice([0.01, 0.02, -0.01, -0.02]), 2))
            continue
            
        # Reste : Parfaite adéquation
        prime_dsi.append(ref_p)
        
    df = pd.DataFrame({
        "ID_CLIENT": ids,
        "age_conducteur": ages,
        "experience_permis": experience,
        "type_vehicule": vehicle_types,
        "puissance_vehicule": horsepower,
        "zone_geographique": zones,
        "usage": usages,
        "kilometrage_annuel": kilometrage,
        "bonus_malus": bonus_malus,
        "PRIME_REF": prime_ref,
        "PRIME_DSI": prime_dsi
    })
    
    # Injection volontaire de 2% de valeurs manquantes (NaNs) dans les variables d'âge pour tester la robustesse ETL
    mask_nan = np.random.rand(num_records) < 0.02
    df.loc[mask_nan, "age_conducteur"] = np.nan
    
    # Sauvegarde au format compatible Windows Excel (avec BOM UTF-8-SIG et séparateur point-virgule)
    df.to_csv(output_path, index=False, sep=";", encoding="utf-8-sig")
    return os.path.abspath(output_path)

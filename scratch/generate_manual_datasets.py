# scripts/generate_manual_datasets.py
import os
import pandas as pd
import numpy as np

# Configurer la reproductibilité
np.random.seed(42)

# Répertoire de sortie
output_root = "data/test_datasets"
os.makedirs(output_root, exist_ok=True)

# ---------------------------------------------------------------------------
# INDEX.md
# ---------------------------------------------------------------------------
index_content = """# Index des Jeux de Données de Validation Manuelle

Ce répertoire contient une bibliothèque complète de jeux de données Excel appairés pour valider manuellement l'ensemble des fonctionnalités de la plateforme **ActuaRecette**.

Chaque dossier contient :
- `source_actuariat.xlsx` : Fichier de référence actuarielle (MOA).
- `source_dsi.xlsx` : Fichier de production calculé par la DSI.
- `README.md` : Guide pas-à-pas avec l'objectif du test, les anomalies attendues et le résultat ciblé.

## Table des Scénarios

| N° | Dossier | LOB / Périmètre | Nb Lignes | Objectif principal |
|---|---|---|---|---|
| **01** | `scenario_01_nominal` | LOB_AUTO_PART | 100 | Cas nominal parfait (sans écart). Taux de conformité = 100%. |
| **02** | `scenario_02_arrondi` | LOB_AUTO_PART | 100 | Écarts mineurs sous forme de bruit d'arrondi décimal (non-bloquants si tolérance >= 0.05 €). |
| **03** | `scenario_03_ecarts_majeurs` | LOB_AUTO_PART | 100 | Détection d'anomalies de tarification (Seuil Plancher, Jeune Conducteur, Puissance). |
| **04** | `scenario_04_donnees_manquantes` | LOB_AUTO_PART | 100 | Robustesse ETL face aux champs vides (NaN) et dossiers incomplets. |
| **05** | `scenario_05_doublons` | LOB_AUTO_PART | 102 | Détection et gestion des identifiants clients dupliqués (`ID_CLIENT`). |
| **06** | `scenario_06_donnees_incoherentes` | LOB_AUTO_PART | 100 | Détection des valeurs impossibles (âges/primes négatives, expérience > âge). |
| **07A** | `scenario_07a_volumetrie_5k` | LOB_AUTO_PART | 5 000 | Palier 1 : Fluidité des calculs et réconciliation sur volume modéré. |
| **07B** | `scenario_07b_volumetrie_15k` | LOB_AUTO_PART | 15 000 | Palier 2 : Robustesse de l'affichage graphique sur volume intermédiaire. |
| **07C** | `scenario_07c_volumetrie_50k` | LOB_AUTO_PART | 50 000 | Palier 3 : Test de charge et pagination des tableaux sur volume extrême. |
| **08A** | `scenario_08a_lob_incendie` | LOB_INCENDIE_RD | 100 | Validation multi-périmètre. Colonnes différentes (`ID_CONTRAT`, `PRIME_ACTU`/`PRIME_PROD`). |
| **08B** | `scenario_08b_lob_sante` | LOB_SANTE_IND | 100 | Validation multi-périmètre. Colonnes spécifiques (`ID_ADHERENT`, `PRIME_SANTE_REF`/`DSI`). |
| **09** | `scenario_09_multi_periodes` | LOB_AUTO_PART | 100/mois | 3 mois successifs pour alimenter l'historique et tester les courbes de tendance. |
| **10** | `scenario_10_workflow` | LOB_AUTO_PART | 100 | Parcours métier complet : Ingest → Justification (Maker) → Validation (Checker) → Certif. |
| **11** | `scenario_11_gouvernance` | LOB_AUTO_PART | 100 | Validation de la traçabilité Pilier 2 (Registre d'Audit, signatures cryptographiques). |
| **12** | `scenario_12_certif_reserves` | LOB_AUTO_PART | 100 | Scénario d'anomalies justifiées pour forcer le statut "Certifié avec réserves". |
"""

with open(os.path.join(output_root, "INDEX.md"), "w", encoding="utf-8") as f:
    f.write(index_content)

# ---------------------------------------------------------------------------
# GÉNERATEUR DE BASE DE DONNÉES
# ---------------------------------------------------------------------------
def generate_base_data(n=100):
    ids = [f"C{i:05d}" for i in range(1, n + 1)]
    ages = np.random.randint(18, 85, size=n)
    experience = [max(0, age - 18 - int(np.random.randint(0, 3))) for age in ages]
    veh_types = np.random.choice(["Citadine", "Berline", "SUV", "Sportive", "Prestige"], size=n)
    powers = np.random.randint(50, 280, size=n)
    zones = np.random.choice(["Urbain Dense", "Urbain Standard", "Rural"], size=n)
    usages = np.random.choice(["Prive", "Prive-Trajet", "Professionnel"], size=n)
    kms = np.random.randint(5, 45, size=n) * 1000
    bm = np.random.choice([0.50, 0.68, 0.76, 0.85, 0.95, 1.00, 1.10, 1.25], size=n)
    
    df = pd.DataFrame({
        "ID_CLIENT": ids,
        "age_conducteur": ages,
        "experience_permis": experience,
        "type_vehicule": veh_types,
        "puissance_vehicule": powers,
        "zone_geographique": zones,
        "usage": usages,
        "kilometrage_annuel": kms,
        "bonus_malus": bm
    })
    
    # Formule théorique de tarification validée
    primes = []
    for idx, row in df.iterrows():
        age = row["age_conducteur"]
        pwr = row["puissance_vehicule"]
        zone = row["zone_geographique"]
        b = row["bonus_malus"]
        
        factor_age = 1.5 if age < 25 else 1.0
        factor_power = 1.3 if pwr > 150 else 1.0
        factor_zone = 1.2 if zone == "Urbain Dense" else 1.0
        
        calc = 250.0 * b * factor_age * factor_power * factor_zone
        primes.append(max(150.00, round(calc, 2)))
        
    df["PRIME_REF"] = primes
    return df

def write_scenario(scenario_name, ref_df, prod_df, readme_text):
    path = os.path.join(output_root, scenario_name)
    os.makedirs(path, exist_ok=True)
    ref_df.to_excel(os.path.join(path, "source_actuariat.xlsx"), index=False)
    prod_df.to_excel(os.path.join(path, "source_dsi.xlsx"), index=False)
    with open(os.path.join(path, "README.md"), "w", encoding="utf-8") as f:
        f.write(readme_text)
    print(f"Scénario {scenario_name} généré.")

# ---------------------------------------------------------------------------
# SCÉNARIO 1 : NOMINAL
# ---------------------------------------------------------------------------
df_s1_ref = generate_base_data(100)
df_s1_prod = df_s1_ref.copy().rename(columns={"PRIME_REF": "PRIME_DSI"})
readme_s1 = """# Scénario 1 : Cas nominal (Sans écart)

## Objectif
Valider que la plateforme de réconciliation déclare une conformité parfaite lorsque les calculs de la DSI correspondent en tout point à la référence actuarielle.

## Contexte
- Périmètre : Automobile Particuliers
- Volume : 100 assurés
- Données saines sans écarts de tarification ni erreurs d'ingestion.

## Comportement attendu dans ActuaRecette
1. L'import des deux fichiers se fait sans erreur.
2. La réconciliation calcule un taux de conformité de **100 %**.
3. Aucun écart n'est mis en évidence dans le tableau d'analyse.
4. La campagne obtient le statut initial "CONFORME" et peut être certifiée immédiatement sans réserve.
"""
write_scenario("scenario_01_nominal", df_s1_ref, df_s1_prod, readme_s1)

# ---------------------------------------------------------------------------
# SCÉNARIO 2 : ÉCARTS MINEURS
# ---------------------------------------------------------------------------
df_s2_ref = generate_base_data(100)
df_s2_prod = df_s2_ref.copy().rename(columns={"PRIME_REF": "PRIME_DSI"})
# Ajouter des micro-écarts de moins de 0.05
deltas = [0.01, -0.02, 0.03, -0.01, 0.02, 0.04, -0.03, 0.01, -0.01, 0.00]
for i in range(100):
    df_s2_prod.at[i, "PRIME_DSI"] = round(df_s2_prod.at[i, "PRIME_DSI"] + deltas[i % len(deltas)], 2)

readme_s2 = """# Scénario 2 : Écarts mineurs (Bruit d'arrondi)

## Objectif
Tester le fonctionnement du seuil de tolérance unitaire (bruit numérique).

## Contexte
- Périmètre : Automobile Particuliers
- Volume : 100 assurés
- Des écarts de précision numérique de 1 à 4 centimes d'euro existent sur plusieurs lignes (différences de calcul FLOAT en base DSI).

## Comportement attendu dans ActuaRecette
1. Si le seuil unitaire de tolérance configuré à l'étape 2 est de **0.00 €** :
   - Le taux d'alignement tombe à **10%** (car 90% des lignes ont des micro-centimes d'écart).
   - Les écarts apparaissent classés comme **"Bruit d'arrondi décimal"** (statut Non Conforme car supérieur à 0.00).
2. Si le seuil unitaire de tolérance configuré est relevé à **0.05 €** :
   - Le taux de conformité remonte à **100%**.
   - Le statut passe à **Conforme** (le bruit numérique est filtré).
"""
write_scenario("scenario_02_arrondi", df_s2_ref, df_s2_prod, readme_s2)

# ---------------------------------------------------------------------------
# SCÉNARIO 3 : ÉCARTS MAJEURS
# ---------------------------------------------------------------------------
df_s3_ref = generate_base_data(100)
df_s3_prod = df_s3_ref.copy().rename(columns={"PRIME_REF": "PRIME_DSI"})

# Injecter anomalies
# 1. Seuil plancher non appliqué (3 cas)
plancher_indices = []
for idx, r in df_s3_ref.iterrows():
    if r["PRIME_REF"] == 150.00:
        plancher_indices.append(idx)
        if len(plancher_indices) == 3:
            break
for idx in plancher_indices:
    df_s3_prod.at[idx, "PRIME_DSI"] = 120.00 # DSI omet le max(150.00, calc)

# 2. Erreur Jeune Conducteur (3 cas)
jc_indices = []
for idx, r in df_s3_ref.iterrows():
    if r["age_conducteur"] < 25 and idx not in plancher_indices:
        jc_indices.append(idx)
        if len(jc_indices) == 3:
            break
for idx in jc_indices:
    # recompute JC factor at 1.6 instead of 1.5
    row = df_s3_ref.loc[idx]
    calc = 250.0 * row["bonus_malus"] * 1.60 * (1.3 if row["puissance_vehicule"] > 150 else 1.0) * (1.2 if row["zone_geographique"] == "Urbain Dense" else 1.0)
    df_s3_prod.at[idx, "PRIME_DSI"] = round(calc, 2)

# 3. Coefficient Puissance (3 cas)
pwr_indices = []
for idx, r in df_s3_ref.iterrows():
    if r["puissance_vehicule"] > 150 and idx not in plancher_indices and idx not in jc_indices:
        pwr_indices.append(idx)
        if len(pwr_indices) == 3:
            break
for idx in pwr_indices:
    # recompute Power factor at 1.5 instead of 1.3
    row = df_s3_ref.loc[idx]
    calc = 250.0 * row["bonus_malus"] * (1.5 if row["age_conducteur"] < 25 else 1.0) * 1.50 * (1.2 if row["zone_geographique"] == "Urbain Dense" else 1.0)
    df_s3_prod.at[idx, "PRIME_DSI"] = round(calc, 2)

readme_s3 = """# Scénario 3 : Écarts majeurs (Anomalies fonctionnelles)

## Objectif
Valider la détection et la classification automatique des bugs financiers dans le moteur DSI.

## Contexte
Contient 9 anomalies significatives :
1. **Oubli de Seuil Plancher** (3 dossiers) : la production applique des primes inférieures à 150 € (ex: 120 €) au lieu du plancher réglementaire de 150 €.
2. **Erreur de Formule Jeune Conducteur** (3 dossiers) : surprime appliquée à 1.60 au lieu de 1.50 pour les jeunes conducteurs.
3. **Écart de Coefficient Puissance** (3 dossiers) : facteur puissance appliqué à 1.50 au lieu de 1.30 pour les véhicules de plus de 150 ch.

## Comportement attendu dans ActuaRecette
- Taux de conformité = **91.0 %**.
- 9 anomalies critiques détectées.
- Le moteur de classification catégorise automatiquement :
  - 3 anomalies de type `"Oubli de Seuil Minimal (Plancher)"`
  - 3 anomalies de type `"Erreur de Formule Jeune Conducteur"`
  - 3 anomalies de type `"Écart de Coefficient Puissance"`
- Statut de la campagne : **NON CONFORME** (les anomalies sont bloquantes car sévérité Critique / Bloquant).
"""
write_scenario("scenario_03_ecarts_majeurs", df_s3_ref, df_s3_prod, readme_s3)

# ---------------------------------------------------------------------------
# SCÉNARIO 4 : DONNÉES MANQUANTES
# ---------------------------------------------------------------------------
df_s4_ref = generate_base_data(100)
df_s4_prod = df_s4_ref.copy().rename(columns={"PRIME_REF": "PRIME_DSI"})

# Injecter valeurs manquantes
df_s4_ref.at[10, "age_conducteur"] = np.nan
df_s4_ref.at[20, "PRIME_REF"] = np.nan
df_s4_prod.at[30, "PRIME_DSI"] = np.nan
df_s4_ref.at[40, "puissance_vehicule"] = np.nan

readme_s4 = """# Scénario 4 : Données manquantes (Incomplètes)

## Objectif
Vérifier que le module de qualité des données (ETL/Data Quality) isole et alerte sur les dossiers incomplets.

## Contexte
Introduction de champs vides (NaN) dans les colonnes clés (`age_conducteur`, `PRIME_REF`, `PRIME_DSI`, `puissance_vehicule`).

## Comportement attendu dans ActuaRecette
- Les lignes avec des NaN sont détectées à l'étape 3.
- Anomalies classées dans : **"Donnée corrompue ou manquante"**.
- La présence de ces données manquantes bloque le calcul ou génère des défauts fataux à hauteur de 4 dossiers.
- Statut final : **NON CONFORME** avec alerte de qualité des données.
"""
write_scenario("scenario_04_donnees_manquantes", df_s4_ref, df_s4_prod, readme_s4)

# ---------------------------------------------------------------------------
# SCÉNARIO 5 : DOUBLONS
# ---------------------------------------------------------------------------
df_s5_ref = generate_base_data(100)
df_s5_prod = df_s5_ref.copy().rename(columns={"PRIME_REF": "PRIME_DSI"})

# Ajouter des doublons
dup_row_ref1 = df_s5_ref.iloc[10].copy()
dup_row_prod1 = df_s5_prod.iloc[10].copy()
dup_row_ref2 = df_s5_ref.iloc[50].copy()
dup_row_prod2 = df_s5_prod.iloc[50].copy()

df_s5_ref = pd.concat([df_s5_ref, pd.DataFrame([dup_row_ref1, dup_row_ref2])], ignore_index=True)
df_s5_prod = pd.concat([df_s5_prod, pd.DataFrame([dup_row_prod1, dup_row_prod2])], ignore_index=True)

readme_s5 = """# Scénario 5 : Doublons (Clé non unique)

## Objectif
Tester le comportement du pivot de réconciliation face à des doublons dans le fichier d'ingestion.

## Contexte
Deux assurés (`ID_CLIENT` identiques) sont enregistrés deux fois dans les fichiers sources.

## Comportement attendu dans ActuaRecette
- Lors de l'ingestion ou de la jointure, le système détecte des lignes dupliquées pour le même identifiant.
- Une alerte technique est levée pour indiquer que la clé d'assuré n'est pas unique.
- Cela permet de tester la résilience et les messages d'avertissement de l'application sur la cohérence des bases.
"""
write_scenario("scenario_05_doublons", df_s5_ref, df_s5_prod, readme_s5)

# ---------------------------------------------------------------------------
# SCÉNARIO 6 : DONNÉES INCOHÉRENTES
# ---------------------------------------------------------------------------
df_s6_ref = generate_base_data(100)
df_s6_prod = df_s6_ref.copy().rename(columns={"PRIME_REF": "PRIME_DSI"})

# Valeurs incohérentes
df_s6_ref.at[15, "age_conducteur"] = -10
df_s6_prod.at[25, "PRIME_DSI"] = -500.00
df_s6_ref.at[35, "experience_permis"] = 60
df_s6_ref.at[35, "age_conducteur"] = 20

readme_s6 = """# Scénario 6 : Données incohérentes (Invalides)

## Objectif
Valider la détection d'incohérences logiques et physiques dans les données.

## Contexte
- Un assuré a un âge négatif (`-10` ans).
- Un assuré a une prime calculée négative (`-500 €`).
- Un assuré a `60` ans d'expérience de permis mais n'est âgé que de `20` ans (physiquement impossible).

## Comportement attendu dans ActuaRecette
- Détection des anomalies critiques à l'analyse.
- La prime négative est classée dans **"Donnée corrompue ou manquante"** car une prime d'assurance à risque ne peut être négative.
- L'incohérence âge/permis déclenche une anomalie de tarification ou d'intégrité.
"""
write_scenario("scenario_06_donnees_incoherentes", df_s6_ref, df_s6_prod, readme_s6)

# ---------------------------------------------------------------------------
# SCÉNARIOS 7 : VOLUMÉTRIE
# ---------------------------------------------------------------------------
def generate_volume_scenario(n, filename_suffix):
    ref = generate_base_data(n)
    prod = ref.copy().rename(columns={"PRIME_REF": "PRIME_DSI"})
    
    # Injecter 2% d'anomalies variées
    n_anom = int(n * 0.02)
    indices = np.random.choice(n, size=n_anom, replace=False)
    
    for count, idx in enumerate(indices):
        if count % 3 == 0:
            # Plancher bug
            prod.at[idx, "PRIME_DSI"] = 100.00
            ref.at[idx, "PRIME_REF"] = 150.00
        elif count % 3 == 1:
            # Rounding bug
            prod.at[idx, "PRIME_DSI"] = round(ref.at[idx, "PRIME_REF"] + 0.10, 2)
        else:
            # Young driver bug
            ref.at[idx, "age_conducteur"] = 20
            prod.at[idx, "PRIME_DSI"] = round(ref.at[idx, "PRIME_REF"] * 1.1, 2)
            
    readme_vol = f"""# Scénario 7{filename_suffix} : Volumétrie - {n} lignes

## Objectif
Tester la robustesse technique de l'application, l'impact sur la mémoire du serveur, et la fluidité d'affichage graphique Plotly sur un grand nombre d'assurés.

## Contexte
- Volume : {n} lignes
- Proportion d'anomalies : ~2%

## Comportement attendu dans ActuaRecette
- La jointure DuckDB s'exécute en moins de 2 secondes.
- La pagination des tables d'anomalies de l'application s'affiche de manière fluide.
- Les graphiques Plotly affichent correctement les densités et la distribution de dérive.
"""
    write_scenario(f"scenario_07{filename_suffix.lower()}_volumetrie_{n // 1000}k", ref, prod, readme_vol)

generate_volume_scenario(5000, "A")
generate_volume_scenario(15000, "B")
generate_volume_scenario(50000, "C")

# ---------------------------------------------------------------------------
# SCÉNARIOS 8 : MULTI-PÉRIMÈTRES
# ---------------------------------------------------------------------------
# 8A: INCENDIE
# Columns: ID_CONTRAT, code_risque, type_construction, surface_m2, valeur_assuree, franchise, PRIME_ACTU
n_inc = 100
ids_inc = [f"INC-{i:03d}" for i in range(1, n_inc + 1)]
valeurs = np.random.randint(100, 1500, size=n_inc) * 1000
types = np.random.choice(["Habitation", "Commercial", "Industriel"], size=n_inc)
prime_ref_inc = [round(v * 0.001 * (1.5 if t == "Industriel" else 1.0), 2) for v, t in zip(valeurs, types)]
df_s8a_ref = pd.DataFrame({
    "ID_CONTRAT": ids_inc,
    "type_construction": types,
    "valeur_assuree": valeurs,
    "PRIME_ACTU": prime_ref_inc
})
df_s8a_prod = df_s8a_ref.copy().rename(columns={"PRIME_ACTU": "PRIME_PROD"})
# Injecter 3 anomalies > seuil tolérance incendie (3.0% ou 1000€)
df_s8a_prod.at[15, "PRIME_PROD"] = df_s8a_prod.at[15, "PRIME_PROD"] + 1500.00
df_s8a_prod.at[35, "PRIME_PROD"] = df_s8a_prod.at[35, "PRIME_PROD"] * 1.20
df_s8a_prod.at[55, "PRIME_PROD"] = df_s8a_prod.at[55, "PRIME_PROD"] * 0.85

readme_s8a = """# Scénario 8A : LOB Incendie & Risques Divers

## Objectif
Tester la flexibilité du wizard d'importation (column mapping) et la réconciliation sur un autre type de risque.

## Contexte
- Portefeuille : Incendie & Risques Divers (`LOB_INCENDIE_RD`)
- Seuil de tolérance du LOB : **3.0 %**
- Seuil de matérialité global : **1 000.00 €**
- Noms de colonnes : `ID_CONTRAT` (clé), `PRIME_ACTU` (référence), `PRIME_PROD` (production).

## Comportement attendu dans ActuaRecette
1. Sélectionner le LOB **"Incendie & Risques Divers"** lors de la création de la campagne.
2. À l'étape 1 (Ingestion) :
   - Mappez la clé sur : `ID_CONTRAT`
   - Mappez la prime actuarielle sur : `PRIME_ACTU`
   - Mappez la prime de production sur : `PRIME_PROD`
3. À l'étape 3 (Analyse) :
   - Observez le calcul des écarts basé sur la tolérance de 3.0 % spécifique au LOB.
   - Les 3 anomalies injectées apparaissent comme critiques.
"""
write_scenario("scenario_08a_lob_incendie", df_s8a_ref, df_s8a_prod, readme_s8a)

# 8B: SANTE
# Columns: ID_ADHERENT, type_formule, age_assure, PRIME_SANTE_REF
n_san = 100
ids_san = [f"SAN-{i:03d}" for i in range(1, n_san + 1)]
ages_san = np.random.randint(1, 90, size=n_san)
types_san = np.random.choice(["Basique", "Medium", "Premium"], size=n_san)
prime_ref_san = [round(50.0 + (age * 1.2) * (2.0 if t == "Premium" else 1.0), 2) for age, t in zip(ages_san, types_san)]
df_s8b_ref = pd.DataFrame({
    "ID_ADHERENT": ids_san,
    "age_assure": ages_san,
    "type_formule": types_san,
    "PRIME_SANTE_REF": prime_ref_san
})
df_s8b_prod = df_s8b_ref.copy().rename(columns={"PRIME_SANTE_REF": "PRIME_SANTE_DSI"})
# Injecter 3 anomalies
df_s8b_prod.at[10, "PRIME_SANTE_DSI"] = df_s8b_prod.at[10, "PRIME_SANTE_DSI"] + 50.00
df_s8b_prod.at[20, "PRIME_SANTE_DSI"] = df_s8b_prod.at[20, "PRIME_SANTE_DSI"] - 30.00

readme_s8b = """# Scénario 8B : LOB Santé Individuelle

## Objectif
Valider la flexibilité de réconciliation sur le LOB Santé avec ses propres règles et colonnes.

## Contexte
- Portefeuille : Santé Individuelle (`LOB_SANTE_IND`)
- Seuil de tolérance du LOB : **2.0 %**
- Noms de colonnes : `ID_ADHERENT` (clé), `PRIME_SANTE_REF` (référence), `PRIME_SANTE_DSI` (production).

## Comportement attendu dans ActuaRecette
- Créer une campagne sous le portefeuille **"Santé Individuelle"**.
- Effectuer la réconciliation en associant les colonnes correspondantes.
- Les déviations de 30 € et 50 € sont identifiées comme des anomalies significatives (>2.0%).
"""
write_scenario("scenario_08b_lob_sante", df_s8b_ref, df_s8b_prod, readme_s8b)

# ---------------------------------------------------------------------------
# SCÉNARIOS 9 : MULTI-PÉRIODES
# ---------------------------------------------------------------------------
# Générer 3 mois successifs pour LOB_AUTO_PART
def write_period(period_name, success_rate_mode):
    ref = generate_base_data(100)
    prod = ref.copy().rename(columns={"PRIME_REF": "PRIME_DSI"})
    
    if success_rate_mode == "low":
        # beaucoup de planchers non appliqués (10 cas)
        for i in range(10):
            prod.at[i*8, "PRIME_DSI"] = 100.00
    elif success_rate_mode == "medium":
        # quelques planchers non appliqués (3 cas)
        for i in range(3):
            prod.at[i*12, "PRIME_DSI"] = 100.00
            
    readme_period = f"""# Scénario 9 : Période {period_name}

## Objectif
Alimenter les séries temporelles de l'application.

## Mode
Taux de conformité configuré en mode: **{success_rate_mode}**.
"""
    os.makedirs(os.path.join(output_root, "scenario_09_multi_periodes", period_name), exist_ok=True)
    ref.to_excel(os.path.join(output_root, "scenario_09_multi_periodes", period_name, "source_actuariat.xlsx"), index=False)
    prod.to_excel(os.path.join(output_root, "scenario_09_multi_periodes", period_name, "source_dsi.xlsx"), index=False)

write_period("2026-03", "low")
write_period("2026-04", "medium")
write_period("2026-05", "high")

with open(os.path.join(output_root, "scenario_09_multi_periodes", "README.md"), "w", encoding="utf-8") as f:
    f.write("""# Scénario 9 : Multi-Périodes (Série Temporelle)

## Objectif
Tester les graphiques d'analyse de tendance et le Population Stability Index (PSI) de la page *Tendances*.

## Organisation
Contient trois sous-dossiers :
- `2026-03` : Taux de conformité bas (~90%).
- `2026-04` : Taux de conformité moyen (~97%).
- `2026-05` : Taux de conformité parfait (100%).

## Comportement attendu dans ActuaRecette
Importez successivement ces trois mois sous forme de campagnes consécutives. 
Naviguez vers la page **Tendances** pour voir la courbe de performance s'améliorer de mars à mai.
""")
print("Scénario 9 généré.")

# ---------------------------------------------------------------------------
# SCÉNARIOS 10 : WORKFLOW
# ---------------------------------------------------------------------------
df_s10_ref = generate_base_data(100)
df_s10_prod = df_s10_ref.copy().rename(columns={"PRIME_REF": "PRIME_DSI"})
# Injecter 2 planchers non appliqués
plancher_idx_10 = []
for idx, r in df_s10_ref.iterrows():
    if r["PRIME_REF"] == 150.00:
        plancher_idx_10.append(idx)
        if len(plancher_idx_10) == 2:
            break
for idx in plancher_idx_10:
    df_s10_prod.at[idx, "PRIME_DSI"] = 120.00

readme_s10 = """# Scénario 10 : Workflow complet (Maker → Checker → Approver)

## Objectif
Parcourir le workflow métier complet et réglementaire imposé par la gouvernance Pilier 2.

## Contexte
- Portefeuille : Automobile Particuliers
- Contient exactement **2 anomalies critiques** d'oubli de seuil plancher.

## Guide de test pas-à-pas
1. Connectez-vous en tant que **Maker** (Actuaire MOA).
2. Créez une nouvelle campagne de réconciliation dans l'Espace de travail.
3. Importez les fichiers `source_actuariat.xlsx` et `source_dsi.xlsx` de ce dossier.
4. Exécutez l'analyse. Notez les 2 anomalies.
5. Saisissez des commentaires de justification pour chaque anomalie (ex: "Écart de paramétrage de la DSI sur l'arrondi, validé temporairement pour clôture").
6. Soumettez la campagne pour validation.
7. Connectez-vous en tant que **Checker** (Validateur).
8. Ouvrez la campagne, vérifiez la checklist de conformité réglementaire, saisissez votre commentaire de validation et approuvez.
9. Connectez-vous en tant que **Approver** (Responsable MOA).
10. Certifiez la campagne de réconciliation et téléchargez le rapport d'audit PDF.
"""
write_scenario("scenario_10_workflow", df_s10_ref, df_s10_prod, readme_s10)

# ---------------------------------------------------------------------------
# SCÉNARIOS 11 : GOUVERNANCE
# ---------------------------------------------------------------------------
df_s11_ref = generate_base_data(100)
df_s11_prod = df_s11_ref.copy().rename(columns={"PRIME_REF": "PRIME_DSI"})
# Injecter anomalies
df_s11_prod.at[5, "PRIME_DSI"] = df_s11_prod.at[5, "PRIME_DSI"] * 1.5

readme_s11 = """# Scénario 11 : Gouvernance & Registre d'Audit

## Objectif
Valider la traçabilité Solvabilité II (Pilier 2) à chaque action utilisateur.

## Contexte
Ce jeu de données comporte 1 anomalie majeure de tarification.

## Comportement attendu dans ActuaRecette
1. Créez et importez cette campagne.
2. À chaque étape franchie (Brouillon -> Analyse -> Soumission), ouvrez la page **Registre d'Audit**.
3. Vérifiez qu'une ligne d'audit est générée, contenant :
   - L'horodatage précis.
   - L'identifiant SSO de l'utilisateur actif.
   - L'action effectuée.
   - La signature cryptographique (SHA-256) garantissant l'intégrité de la trace.
4. Les résultats agrégés doivent remonter dans la page **Gouvernance ACPR**.
"""
write_scenario("scenario_11_gouvernance", df_s11_ref, df_s11_prod, readme_s11)

# ---------------------------------------------------------------------------
# SCÉNARIOS 12 : CERTIF AVEC RÉSERVES
# ---------------------------------------------------------------------------
df_s12_ref = generate_base_data(100)
df_s12_prod = df_s12_ref.copy().rename(columns={"PRIME_REF": "PRIME_DSI"})
# Injecter 3 anomalies d'arrondi ou écarts modérés
df_s12_prod.at[12, "PRIME_DSI"] = df_s12_prod.at[12, "PRIME_DSI"] + 15.00
df_s12_prod.at[24, "PRIME_DSI"] = df_s12_prod.at[24, "PRIME_DSI"] - 25.00

readme_s12 = """# Scénario 12 : Certification avec réserves

## Objectif
Tester et valider l'attribution du statut réglementaire "Certifié avec réserves".

## Contexte
Contient 2 anomalies de tarification modérées (15 € et 25 €).

## Comportement attendu dans ActuaRecette
1. Importez et analysez cette campagne.
2. En tant que **Checker**, examinez les anomalies.
3. Remplissez la checklist. Dans le champ de commentaire de révision, saisissez un texte contenant le mot **"réserve"** ou **"reserve"** (déclencheur logique du statut). Exemple: *"Validation accordée avec réserve en attente du correctif DSI sur la formule de taxe."*
4. Approuvez le run.
5. Constatez sur le tableau de bord et dans la liste que le statut est passé à **"Certifié avec réserves"** (couleur Orange).
"""
write_scenario("scenario_12_certif_reserves", df_s12_ref, df_s12_prod, readme_s12)

print("Tous les scénarios ont été générés avec succès !")

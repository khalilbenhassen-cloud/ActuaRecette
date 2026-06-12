# Index des Jeux de Données de Validation Manuelle

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
| **13** | `scenario_13_contrat_nominal` | LOB_AUTO_PART / Contrat | 100 | Cas nominal pour domaine Contrat (sans écart). Taux de conformité = 100%. |
| **14** | `scenario_14_contrat_ecarts` | LOB_AUTO_PART / Contrat | 100 | Écarts financiers majeurs injectés pour domaine Contrat. |
| **15** | `scenario_15_sinistre_nominal` | LOB_AUTO_PART / Sinistre | 100 | Cas nominal pour domaine Sinistre (sans écart). Taux de conformité = 100%. |
| **16** | `scenario_16_sinistre_ecarts` | LOB_AUTO_PART / Sinistre | 100 | Écarts financiers majeurs injectés pour domaine Sinistre. |
| **17** | `scenario_17_sinistre_regle_nominal` | LOB_AUTO_PART / Sinistre (Mécanisme A) | 100 | Cas nominal pour règle de somme (sans écart). Taux de conformité = 100%. |
| **18** | `scenario_18_sinistre_regle_ecarts` | LOB_AUTO_PART / Sinistre (Mécanisme A) | 100 | Écarts de somme dynamiques injectés. |

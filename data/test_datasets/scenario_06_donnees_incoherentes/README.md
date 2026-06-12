# Scénario 6 : Données incohérentes (Invalides)

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

# Scénario 4 : Données manquantes (Incomplètes)

## Objectif
Vérifier que le module de qualité des données (ETL/Data Quality) isole et alerte sur les dossiers incomplets.

## Contexte
Introduction de champs vides (NaN) dans les colonnes clés (`age_conducteur`, `PRIME_REF`, `PRIME_DSI`, `puissance_vehicule`).

## Comportement attendu dans ActuaRecette
- Les lignes avec des NaN sont détectées à l'étape 3.
- Anomalies classées dans : **"Donnée corrompue ou manquante"**.
- La présence de ces données manquantes bloque le calcul ou génère des défauts fataux à hauteur de 4 dossiers.
- Statut final : **NON CONFORME** avec alerte de qualité des données.

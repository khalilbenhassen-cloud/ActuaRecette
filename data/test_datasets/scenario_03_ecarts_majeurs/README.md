# Scénario 3 : Écarts majeurs (Anomalies fonctionnelles)

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

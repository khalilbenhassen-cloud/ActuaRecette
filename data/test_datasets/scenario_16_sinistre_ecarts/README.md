# Scénario 16 : Domaine Sinistre - Écarts majeurs

## Objectif
Valider la détection des anomalies sur le coût de sinistre règlementaire.

## Contexte
- Portefeuille : Automobile Particuliers (`LOB_AUTO_PART`)
- Domaine : Sinistre
- Seuil de tolérance du domaine : **3.0 %**
- Contient **5 anomalies critiques** (déviations financières majeures supérieures au seuil de 3.0%).

## Comportement attendu dans ActuaRecette
- Taux de conformité = **95.0 %**.
- 5 anomalies critiques identifiées pour les sinistres `SIN-00006`, `SIN-00019`, `SIN-00040`, `SIN-00058`, et `SIN-00075`.
- Statut final : **NON CONFORME**.

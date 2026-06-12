# Scénario 14 : Domaine Contrat - Écarts majeurs

## Objectif
Valider la détection des anomalies de calcul fonctionnelles spécifiques au domaine **Contrat**.

## Contexte
- Portefeuille : Automobile Particuliers (`LOB_AUTO_PART`)
- Domaine : Contrat
- Seuil de tolérance du domaine : **1.0 %**
- Contient **5 anomalies critiques** (déviations financières majeures supérieures au seuil de 1.0%).

## Comportement attendu dans ActuaRecette
- Taux de conformité = **95.0 %**.
- 5 anomalies critiques identifiées pour les contrats `POL-00011`, `POL-00026`, `POL-00043`, `POL-00069`, et `POL-00088`.
- Statut final : **NON CONFORME**.

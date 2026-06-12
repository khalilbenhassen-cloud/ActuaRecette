# Scénario 12 : Certification avec réserves

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

# Scénario 2 : Écarts mineurs (Bruit d'arrondi)

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

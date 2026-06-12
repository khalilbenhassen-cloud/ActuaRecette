# Scénario 8A : LOB Incendie & Risques Divers

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

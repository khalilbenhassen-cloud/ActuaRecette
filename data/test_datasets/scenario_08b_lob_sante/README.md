# Scénario 8B : LOB Santé Individuelle

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
